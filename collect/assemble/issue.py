"""Assemble a stored GitHub issue into a `thread_context`.

THE THIRD SHAPE IS NOT YET IN THE DATA, AND SAYING SO IS THE POINT
------------------------------------------------------------------
The assembler was built for two shapes: a Reddit tree (`assemble`, ranked
children) and a blog article (`assemble_article`, one member, `whole_document`).
A GitHub issue *with its comments* would be a third — a shallow tree with a body
and n replies, ranked differently from Reddit because there are no votes.

**It is not what is stored.** `GitHubHarvester` records `comment_count` into
`engagement` and never fetches a comment: all 27 rows on staging carry
`parent_id IS NULL` and `thread_root_id IS NULL`. So each document is the issue
body alone, and that is structurally the blog case — one member, no children.

Building a tree assembler now would be building it against no data. What this
does instead is assemble the one member honestly, and **record the comments it did
not read**, which is exactly what the coverage columns are for.

WHY `observed_children = 0` AND `hidden_children_min = comment_count`
---------------------------------------------------------------------
`coverage_ratio` is `observed / (observed + hidden_min)`. An issue with 12
comments assembled from its body alone is:

    observed_children 0, hidden_children_min 12  ->  coverage_ratio 0.0

which says we read the root and none of the thread. Writing `hidden_children_min
= 0` instead would produce `NULL` — *"an empty tree"* — and an issue with twelve
comments is not an empty tree. That is the difference between a coverage figure
that is low and one that is wrong, and E5's extraction is entitled to know which
it is looking at.

An issue with genuinely no comments gives `0 / 0` -> NULL, which the migration's
own comment calls the empty-tree case and refuses to call 1.0.

`selection_method` is `issue_body_only` rather than `whole_document`. The blog
value is true — the article *is* the whole document — and here it would not be:
the body is one member of a thread that exists and was not fetched. A reader
grouping by `selection_method` must be able to find these again the day comments
are harvested.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from collect.assemble.flatten import FlatteningRules, flatten
from collect.assemble.thread import AssembledThread
from collect.config import settings
from collect.ids import stable_id
from collect.rawstore import FLATTENED

#: `decode_entities=False`, and named rather than borrowed from `BLOG_RULES`.
#: The GitHub API returns an issue body as markdown TEXT in JSON, so an `&amp;`
#: in it is an `&amp;` the author typed — decoding would rewrite the author's
#: characters and every quote offset measured against them. Same value as the
#: blog rules and a different reason, so it gets its own name: a shared constant
#: would make the two look like one decision.
GITHUB_RULES = FlatteningRules(decode_entities=False)

#: Not `whole_document`. See the module docstring.
ISSUE_BODY_ONLY = "issue_body_only"


def assemble_issue(
    document_id: str,
    text: str,
    *,
    comment_count: int,
    store,
    pipeline_version: str | None = None,
) -> AssembledThread:
    """One `thread_context` for one issue body. Touches no database."""
    if not text or not text.strip():
        raise ValueError(
            f"{document_id}: no stored text. A thread_context over an empty "
            f"string verifies every quote against nothing and rejects them all, "
            f"which reads as a fabricating extractor rather than as a missing "
            f"body. Do not assemble it."
        )

    version = pipeline_version or settings().pipeline_version
    flattened = flatten([(document_id, text)], rules=GITHUB_RULES)
    stored = store.put(flattened.text, namespace=FLATTENED)

    return AssembledThread(
        id=stable_id("thread_context", document_id, version),
        thread_root_id=document_id,
        member_document_ids=flattened.member_document_ids,
        flattened=flattened,
        flattened_text_ref=stored.ref,
        observed_children=0,
        # The comments exist and were not fetched. A floor, not a guess.
        hidden_children_min=max(0, int(comment_count or 0)),
        hidden_branches_unsized=0,
        pipeline_version=version,
        selection_method=ISSUE_BODY_ONLY,
    )


@dataclass
class IssueAssemblyReport:
    """What assembled, what refused, and how much of each thread went unread."""

    candidates: int = 0
    already_assembled: int = 0
    assembled: int = 0
    refusals: list[str] = field(default_factory=list)
    comments_unread: int = 0
    issues_with_comments: int = 0

    def summary(self) -> str:
        lines = [
            f"assemble : {self.assembled} of {self.candidates} github document(s) "
            f"assembled, {self.already_assembled} already had a thread_context, "
            f"{len(self.refusals)} refused"
        ]
        if self.assembled:
            lines.append(
                f"coverage : {self.issues_with_comments} issue(s) carry comments we "
                f"did not fetch — {self.comments_unread} comment(s) recorded as "
                f"hidden_children_min, so coverage_ratio reads 0.0 rather than NULL"
            )
        for reason in self.refusals:
            lines.append(f"  REFUSED  {reason}")
        return "\n".join(lines)


def assemble_github_documents(conn, *, store, limit: int | None = None) -> IssueAssemblyReport:
    """Assemble every stored GitHub document that has no `thread_context` yet.

    Selected by the ABSENCE of a context rather than by a flag on the document,
    so a re-run is a no-op and a document assembled by some other path is not
    assembled twice. `write_thread_context` is `ON CONFLICT DO NOTHING` as well,
    which makes this safe rather than merely tidy.
    """
    from collect.assemble.thread import write_thread_context
    from collect.rawstore_reader import RawStoreReader

    reader = RawStoreReader(store)
    report = IssueAssemblyReport()

    rows = conn.execute(
        "SELECT d.id, d.text_ref, d.engagement "
        "FROM document d "
        "WHERE d.source = 'github' "
        "  AND NOT EXISTS (SELECT 1 FROM thread_context tc WHERE tc.thread_root_id = d.id) "
        "ORDER BY d.id"
        + (f" LIMIT {int(limit)}" if limit else "")
    ).fetchall()
    report.candidates = len(rows)

    for document_id, text_ref, engagement in rows:
        if not text_ref:
            report.refusals.append(
                f"{document_id}: no text_ref, so there is no body to flatten. The "
                f"document row exists and its text does not."
            )
            continue

        outcome = reader.resolve(text_ref)
        if not outcome.found:
            report.refusals.append(
                f"{document_id}: {text_ref} did not resolve in the store "
                f"({outcome.outcome}). Reprocessing reads from the store, so a "
                f"missing payload is a missing document rather than a slow one."
            )
            continue

        comment_count = int((engagement or {}).get("comments") or 0)
        try:
            assembled = assemble_issue(
                document_id, outcome.require(), comment_count=comment_count, store=store
            )
        except ValueError as refusal:
            report.refusals.append(str(refusal))
            continue

        write_thread_context(conn, assembled)
        report.assembled += 1
        if comment_count:
            report.issues_with_comments += 1
            report.comments_unread += comment_count

    return report
