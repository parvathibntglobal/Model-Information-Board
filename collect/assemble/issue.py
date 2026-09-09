"""Assemble a stored GitHub issue into a `thread_context`. Two shapes now.

THE THIRD SHAPE ARRIVED ON 2026-08-30
--------------------------------------
The assembler was built for two: a Reddit tree (`assemble`, ranked children) and
a blog article (`assemble_article`, one member, `whole_document`). A GitHub issue
*with its comments* is a third — a shallow tree with a body and n replies, ranked
differently from Reddit because there are no votes.

This module now holds both GitHub cases:

    assemble_issue          the body alone. `issue_body_only`.
    assemble_issue_thread   body + fetched comments. `issue_with_comments`.

**The body-only path is not deprecated and must not be.** 25 of the 71 stored
issues carry comments that were counted and never fetched, and an issue with no
comments at all is genuinely one member. Which function to call is a fact about
what was fetched, not a preference — and `selection_method` records the answer
so the two never have to be told apart by inference.

WHY THE SPLIT SURVIVED THE COMMENTS LANDING. The paragraph that used to sit here
said building a tree assembler "would be building it against no data", and that
was right at the time. What made it right was the absence of comments, not the
absence of a need — so when 148 comments landed, the argument expired rather
than being overturned. Recorded because the two read identically from a diff.

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

from collections.abc import Sequence
from dataclasses import dataclass, field

from collect.assemble.flatten import FlatteningRules, flatten
from collect.assemble.prose import github_issue_prose
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
    """One `thread_context` for one issue body. Touches no database.

    `text` IS THE ISSUE PAYLOAD, not prose. `document.text_ref` for github points
    at the raw API response - deliberately, so `content_hash` identifies one
    document - and the prose is extracted HERE, per the ruling in
    `docs/engineer-1/ruling-what-content-hash-identifies.md`.

    Until 2026-08-28 this flattened the payload VERBATIM, so all 80 github
    thread_contexts hold `{"url":"https://api.github.com/repos/...`. The prose
    sits inside the JSON as `"body": "..."`, so a quote of it verified by exact
    substring and `quote_verified` reported true - rule 1 returning true for the
    wrong reason, with no symptom anywhere. Those 80 contexts need rebuilding.
    """
    if not text or not text.strip():
        raise ValueError(
            f"{document_id}: no stored text. A thread_context over an empty "
            f"string verifies every quote against nothing and rejects them all, "
            f"which reads as a fabricating extractor rather than as a missing "
            f"body. Do not assemble it."
        )

    # RAISES `NotAPayload` rather than falling back to `text`. Falling back is
    # the defect this line exists to fix.
    text = github_issue_prose(text)

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


#: The third shape, and it is NOT `issue_body_only`. A reader grouping by
#: `selection_method` must be able to tell an issue we read the body of from an
#: issue we read the thread of - the module docstring above promised exactly
#: that ("must be able to find these again the day comments are harvested"), and
#: this is that day.
ISSUE_WITH_COMMENTS = "issue_with_comments"

#: How many comments reach the flattened text. Same value and same reason as
#: Reddit's cap: the extractor reads the root plus a handful of children, and
#: more children is more tokens against a per-call budget rather than more
#: signal. Named separately because a shared constant would make two independent
#: judgements look like one decision.
MAX_ISSUE_COMMENTS = 5


@dataclass(frozen=True)
class AssemblyComment:
    """What the assembler needs from one fetched comment.

    A PROTOCOL-SHAPED VALUE RATHER THAN `StoredComment` ITSELF, because
    `collect/assemble/` must not import an adapter: the assembler serves three
    platforms and depending on one of them inverts that. The caller builds these.
    """

    document_id: str
    body: str
    external_id: str
    #: GitHub declares it, `StoredComment.is_bot` reads it. Carried here so the
    #: refusal below is a property of the assembler rather than a rule the
    #: caller is trusted to have applied.
    is_bot: bool = False
    #: There are no votes on a GitHub comment. See `_rank_issue_comments`.
    score: int | None = None


def assemble_issue_thread(
    *,
    root_document_id: str,
    root_text: str,
    comments: Sequence[AssemblyComment],
    comment_count: int,
    store,
    version_aliases,
    max_children: int = MAX_ISSUE_COMMENTS,
    pipeline_version: str | None = None,
) -> AssembledThread:
    """One `thread_context` over an issue body AND its fetched comments.

    THE THIRD SHAPE, BUILT NOW BECAUSE THE DATA FINALLY EXISTS. The module
    docstring above says a tree assembler "would be building it against no
    data"; 148 comments across 30 issues is data, and 25 of the 71 issues carry
    comments that were counted and never fetched.

    ⚠ BOTS ARE REFUSED AS MEMBERS, AND THIS IS THE GUARD THAT MATTERS.
      `github-actions[bot]` is the busiest commenter in the corpus. Writing its
      document with `author_id` NULL is not enough on its own: `cells.py` maps a
      NULL author to `ANONYMOUS_VOICE:platform`, so a bot left in the flattened
      text could be quoted by the extractor and contribute that shared voice.
      Excluding it from `member_document_ids` is what stops it being read at all.

      Refused here rather than only in the caller because this function decides
      what the extractor sees. A rule applied by whoever remembers is a rule
      that holds until somebody writes a second caller.

    ⚠ `hidden_children_min` IS THE COUNT WE DID NOT FETCH, NOT ZERO. GitHub's
      `comment_count` is the thread's true size, so an issue reporting 12
      comments of which we hold 8 is `observed 8, hidden_min 4` and
      `coverage_ratio 0.667`. Setting hidden to 0 because we fetched "the
      comments" would claim 1.0 coverage of a thread we read two thirds of -
      and the bots we refuse are part of what we did not read, deliberately:
      they are excluded from `observed` too, so the ratio describes human
      coverage rather than API coverage.
    """
    if not root_text or not root_text.strip():
        raise ValueError(
            f"{root_document_id}: no stored root text. A thread_context over an "
            f"empty string verifies every quote against nothing and rejects them "
            f"all, which reads as a fabricating extractor rather than a missing "
            f"issue. Do not assemble it."
        )

    version = pipeline_version or settings().pipeline_version

    usable = [
        c for c in comments if not c.is_bot and c.body and c.body.strip()
    ]
    selected = [c for _score, c in _rank_issue_comments(usable, version_aliases)][
        :max_children
    ]

    documents: list[tuple[str, str]] = [(root_document_id, root_text)]
    documents.extend((c.document_id, c.body) for c in selected)

    flattened = flatten(documents, rules=GITHUB_RULES)
    stored = store.put(flattened.text, namespace=FLATTENED)

    # WHAT WE HOLD, not what we selected. `observed_children` answers "how many
    # voices do we have" and `member_document_ids` answers "which did the
    # extractor read" - the same split Reddit's assembler makes, and conflating
    # them would report a five-comment cap as a five-comment thread.
    observed = len(usable)
    hidden = max(0, int(comment_count or 0) - observed)

    return AssembledThread(
        id=stable_id("thread_context", root_document_id, version),
        thread_root_id=root_document_id,
        member_document_ids=flattened.member_document_ids,
        flattened=flattened,
        flattened_text_ref=stored.ref,
        observed_children=observed,
        hidden_children_min=hidden,
        # GitHub issue comments are a flat list, not a tree. There are no
        # collapsed branches to be unsized, so 0 is a measurement here where on
        # Reddit it would be a guess.
        hidden_branches_unsized=0,
        pipeline_version=version,
        selection_method=ISSUE_WITH_COMMENTS,
    )


def _rank_issue_comments(comments, version_aliases):
    """Rank by specificity alone. There are no votes on a GitHub comment.

    ⚠ NOT `thread.rank_children`, AND THE DIFFERENCE IS NOT AN OVERSIGHT.
      That function scores `specificity x log1p(max(score, 0))`, and a GitHub
      issue comment has no score - reactions exist but are not returned on the
      comment list endpoint. Passing score=None through `log1p(max(None or 0,0))`
      gives `log1p(0) = 0.0`, which multiplies EVERY comment to zero and makes
      the ranking a tie broken on `external_id` - a selection by comment id,
      which is arrival order, presented as a relevance ranking.

      That is the failure this project keeps finding: a computation that runs,
      produces a number, and ranks on something nobody chose. So the engagement
      term is dropped rather than defaulted, and specificity stands alone.

    Ties break on `external_id` so a re-run selects the same comments and
    produces the same `offset_map`.
    """
    from collect.triage.specificity import score_document

    ranked = []
    for comment in comments:
        specificity = score_document(comment.body, version_aliases=version_aliases)
        ranked.append((specificity.score, comment))
    ranked.sort(key=lambda pair: (-pair[0], pair[1].external_id))
    return ranked


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
    """Assemble every stored GitHub ISSUE BODY that has no `thread_context` yet.

    Selected by the ABSENCE of a context rather than by a flag on the document,
    so a re-run is a no-op and a document assembled by some other path is not
    assembled twice. `write_thread_context` is `ON CONFLICT DO NOTHING` as well,
    which makes this safe rather than merely tidy.

    ⚠ `parent_id IS NULL` AND `status <> 'filtered'` ADDED 2026-08-31, AND THE
      QUERY WAS CORRECT UNTIL THE DAY BEFORE. It selected every github document
      without a context, which was exactly the issue bodies for as long as
      `document` held nothing else - every github row had `parent_id IS NULL`
      because no comment had ever been written. `write_comments` landed 148 of
      them, and the premise expired without the query changing.

      What it would have built: **148 single-comment thread_contexts, each one a
      "thread" whose root is a reply.** 99 of those comments are already members
      of the 30 `issue_with_comments` contexts, so the same text would reach the
      extractor twice under two ids - and a second claim from a re-read of one
      comment is a second VOICE from one author, which is the over-clustering
      `collect/CLAUDE.md` calls the worse of the two failures.

      **And 23 of them are bots.** `assemble_issue_thread` refuses bots as
      members precisely so `github-actions[bot]` cannot be quoted; assembling
      one as a ROOT would walk around that refusal from the other side.

    ⚠ THE TWO CHECKS LOOK REDUNDANT AND ARE NOT. DO NOT DELETE EITHER.
      Both would have stopped the instance that prompted them - every one of the
      148 comments is a non-root AND 23 of them are filtered - so a reviewer
      reading the incident finds one check doing the work twice. They guard
      different things and each has a case the other misses:

        parent_id IS NULL      a KEPT comment. 125 of the 148, none filtered.
                               The status check passes them straight through.
        status <> 'filtered'   a filtered ISSUE BODY. `github.py`'s comment
                               writer is not the only thing that sets
                               `status='filtered'`; the triage gates will, on
                               roots, the moment that stage is wired. The parent
                               check passes them straight through.

      The overlap is a property of THIS corpus on THIS day, not of the checks.
      Deleting the one that "did nothing" leaves a gate that is correct until a
      filtered root exists, and `triage` is a `run=None` stage waiting to create
      exactly those - so the redundancy expires in the direction that matters.

      Recorded here because the next reader will see two conditions and one
      incident and reasonably reach for the simplification. Both are asserted
      separately in `tests/test_assemble_github_selection_db.py`, on inputs the
      other check cannot catch, which is what makes the tests independent rather
      than duplicated.

    THE SHAPE, SO IT IS RECOGNISABLE NEXT TIME: correct code, correct comment,
    and a premise that quietly stopped holding. Nothing about this function
    changed - the corpus did.
    """
    from collect.assemble.thread import write_thread_context
    from collect.rawstore_reader import RawStoreReader

    reader = RawStoreReader(store)
    report = IssueAssemblyReport()

    rows = conn.execute(
        "SELECT d.id, d.text_ref, d.engagement "
        "FROM document d "
        "WHERE d.source = 'github' "
        # An issue BODY. A comment is a member of its issue's thread, never the
        # root of its own - see the docstring.
        "  AND d.parent_id IS NULL "
        # A filtered document is one a gate rejected. Assembling it would put
        # text the pipeline refused in front of the extractor.
        "  AND d.status <> 'filtered' "
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
