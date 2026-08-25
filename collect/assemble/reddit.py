"""E3 for Reddit: assemble a stored comment tree into a `thread_context`.

WHY THIS IS ITS OWN ENTRY POINT, AND NOT `assemble` OR `assemble_issue`
----------------------------------------------------------------------
`assemble` (the generic path) takes a freshly-PARSED `ParsedThread` — comments
plus a `ThreadCoverage` computed from the payload's `more` markers. `assemble_issue`
takes a single body and records the comments it did not fetch. Reddit here is
neither: the comments are ALREADY STORED as `document` rows, one per voice, and
this reassembles them without fetching anything.

The shape is a tree — one post (`t3_`) and its comments (`t1_`), which is why
`offset_map` was designed for this platform in the first place. Ranking selects
the 3-5 specific children `judge/` will read; the other ~190 comments stay as
`document` rows, because `judge/curate/gate.py` counts PEOPLE and Reddit is the
only source that is structurally many voices.

THE COVERAGE LIMITATION, STATED RATHER THAN PAPERED OVER
--------------------------------------------------------
`ThreadCoverage`'s hidden-comment numbers come from the `more` markers in the
original `getPostComments` payload. **That payload is not stored** — the harvest
path (`scripts/write_reddit_thread.py`) stores individual comment BODIES, not the
tree, so the markers exist only in a fixture on disk. Reassembling from stored
documents therefore cannot recover them.

So this writes the coverage it can honestly measure and NULL for the rest:

    observed_children       count of stored comment documents. A MEASUREMENT —
                            these are the comments we have.
    hidden_children_min     None. The markers are gone, so the FLOOR is
                            unmeasured. NOT 0: a thread that had `more` markers
                            did hide comments, and 0 would assert it did not
                            (rule 6).
    hidden_branches_unsized None, and for the same reason — not 0. 0 is a
                            measurement blogs can make ("we looked, no markers");
                            here we cannot look, because the markers were never
                            stored.

`coverage_ratio` is GENERATED from `observed + hidden_children_min`, and a NULL
`hidden_children_min` makes it NULL too, which is the honest result: we know how
many comments we hold and cannot bound how many the tree hid.

**The durable fix is upstream** — store the raw `getPostComments` payload at
harvest time so a reassembly reads the markers back, exactly as
`conventions` in root `CLAUDE.md` intends ("reprocess from the raw store rather
than re-fetching"). Logged for the harvester; not solvable from stored documents.

`selection_method` IS `@observed`, AND THAT IS CORRECT HERE
----------------------------------------------------------
The children were ranked over what we OBSERVED (the stored comments), which is
exactly what the `@observed` suffix asserts. Unlike the coverage floor, the
ranking is honest: it ranked everything it had.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from collect.adapters.reddit import reddit_document_id
from collect.assemble.flatten import flatten
from collect.assemble.thread import MAX_CHILDREN, SELECTION_METHOD, AssembledThread, rank_children
from collect.config import settings
from collect.ids import stable_id
from collect.rawstore import FLATTENED

#: `document.source` for Reddit. What `judge/store/cells.py` counts as a
#: platform, so it must be the bare source and never a subreddit.
REDDIT_SOURCE = "reddit"


@dataclass(frozen=True)
class StoredComment:
    """A comment reconstructed from its `document` row and stored body.

    Three fields, structurally satisfying `thread.ThreadMember` so `rank_children`
    can score it. `external_id` is the bare fullname (`t1_…`); `reddit_document_id`
    turns it into the `document.id` the flattener and the member list use.
    """

    external_id: str
    body: str
    score: int | None


def assemble_reddit_thread(
    *,
    root_document_id: str,
    root_text: str,
    comments: list[StoredComment],
    store,
    version_aliases,
    max_children: int = MAX_CHILDREN,
    pipeline_version: str | None = None,
) -> AssembledThread:
    """Build one `thread_context` from a stored post and its stored comments.

    Ranks the comments, selects the top `max_children`, flattens root + selected
    into the `offset_map`, and returns the row. Writes the flattened text to the
    store's regenerable `flattened/` namespace; touches no database.

    `observed_children` is the FULL comment count, not the selected count: it is
    how many voices we hold, which is what the coverage annotation is about. The
    selected 3-5 are what the extractor reads, and `member_document_ids` names
    exactly those.
    """
    if not root_text or not root_text.strip():
        raise ValueError(
            f"{root_document_id}: no stored root text. A thread_context over an "
            f"empty string verifies every quote against nothing and rejects them "
            f"all, which reads as a fabricating extractor rather than a missing "
            f"post. Do not assemble it."
        )

    version = pipeline_version or settings().pipeline_version

    # Rank over what we OBSERVED. `rank_children` scores body specificity times
    # log(1+score); a comment whose body did not resolve is excluded upstream, so
    # everything here has text to score.
    ranked = rank_children(tuple(comments), version_aliases=version_aliases)
    selected = [comment for _score, comment in ranked[:max_children]]

    documents: list[tuple[str, str]] = [(root_document_id, root_text)]
    documents.extend((reddit_document_id(c.external_id), c.body) for c in selected)

    flattened = flatten(documents)
    stored = store.put(flattened.text, namespace=FLATTENED)

    return AssembledThread(
        id=stable_id("thread_context", root_document_id, version),
        thread_root_id=root_document_id,
        member_document_ids=flattened.member_document_ids,
        flattened=flattened,
        flattened_text_ref=stored.ref,
        # A MEASUREMENT: the comments we hold. See the module docstring.
        observed_children=len(comments),
        # UNMEASURED, not zero — the `more` markers were never stored.
        hidden_children_min=None,
        hidden_branches_unsized=None,
        pipeline_version=version,
        selection_method=SELECTION_METHOD,
    )


@dataclass
class RedditAssemblyReport:
    """What assembled, what refused, and why."""

    threads: int = 0
    already_assembled: int = 0
    assembled: int = 0
    comments_selected: int = 0
    comments_held: int = 0
    refusals: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"assemble : {self.assembled} of {self.threads} reddit thread(s) "
            f"assembled, {self.already_assembled} already had a thread_context, "
            f"{len(self.refusals)} refused"
        ]
        if self.assembled:
            lines.append(
                f"voices   : {self.comments_held} comment(s) held across the "
                f"assembled threads, {self.comments_selected} selected for "
                f"flattening; hidden-comment coverage is NULL because the tree "
                f"markers were never stored (see module docstring)"
            )
        for reason in self.refusals:
            lines.append(f"  REFUSED  {reason}")
        return "\n".join(lines)


def _score_of(engagement) -> int | None:
    """`document.engagement.score`, parsed from the JSONB column.

    `None` stays `None` — a comment with no recorded score is unpopular-unknown,
    not zero, and `rank_children` already floors the engagement multiplier at 0.
    """
    if isinstance(engagement, str):
        try:
            engagement = json.loads(engagement)
        except (ValueError, TypeError):
            return None
    if isinstance(engagement, dict):
        value = engagement.get("score")
        if isinstance(value, (int, float)):
            return int(value)
    return None


def assemble_reddit_documents(conn, *, store, limit: int | None = None) -> RedditAssemblyReport:
    """Assemble every stored Reddit thread that has no `thread_context` yet.

    A thread is a post (`thread_root_id IS NULL`) plus every comment whose
    `thread_root_id` is that post's `external_id`. Selected by the ABSENCE of a
    context on the ROOT, so a re-run is a no-op and `write_thread_context`'s
    `ON CONFLICT DO NOTHING` makes it safe rather than merely tidy.
    """
    from collect.assemble.thread import write_thread_context
    from collect.rawstore_reader import RawStoreReader

    reader = RawStoreReader(store)
    report = RedditAssemblyReport()

    roots = conn.execute(
        "SELECT d.id, d.external_id, d.text_ref "
        "FROM document d "
        "WHERE d.source = %s "
        "  AND d.thread_root_id IS NULL "
        "  AND NOT EXISTS (SELECT 1 FROM thread_context tc WHERE tc.thread_root_id = d.id) "
        "ORDER BY d.id"
        + (f" LIMIT {int(limit)}" if limit else ""),
        (REDDIT_SOURCE,),
    ).fetchall()
    report.threads = len(roots)

    # The version's aliases are what `rank_children` scores specificity against —
    # a version token in a comment is the specificity signal. Read once, not
    # per thread.
    version_aliases = _version_aliases(conn)

    for root_document_id, root_external_id, root_text_ref in roots:
        if not root_text_ref:
            report.refusals.append(
                f"{root_document_id}: the post has no text_ref, so there is no "
                f"root body to flatten. The row exists and its text does not."
            )
            continue

        root_outcome = reader.resolve(root_text_ref)
        if not root_outcome.found:
            report.refusals.append(
                f"{root_document_id}: root body {root_text_ref} did not resolve "
                f"in the store ({root_outcome.outcome}). Reassembly reads from "
                f"the store, so a missing payload is a missing document."
            )
            continue

        comment_rows = conn.execute(
            "SELECT external_id, text_ref, engagement "
            "FROM document "
            "WHERE source = %s AND thread_root_id = %s "
            "ORDER BY external_id",
            (REDDIT_SOURCE, root_external_id),
        ).fetchall()

        comments: list[StoredComment] = []
        for external_id, text_ref, engagement in comment_rows:
            if not text_ref:
                continue
            body_outcome = reader.resolve(text_ref)
            if not body_outcome.found:
                # NAMED, not silently dropped: a comment whose body is missing is
                # a voice we can count but not read, and the two facts differ.
                report.refusals.append(
                    f"{root_document_id}: comment {external_id} body {text_ref} "
                    f"did not resolve ({body_outcome.outcome}); it was excluded "
                    f"from flattening."
                )
                continue
            comments.append(
                StoredComment(
                    external_id=external_id,
                    body=body_outcome.require(),
                    score=_score_of(engagement),
                )
            )

        if not comments:
            report.refusals.append(
                f"{root_document_id}: no comment bodies resolved, so this would "
                f"assemble a post with no children — which is the blog shape, not "
                f"a Reddit thread. Not assembled."
            )
            continue

        try:
            assembled = assemble_reddit_thread(
                root_document_id=root_document_id,
                root_text=root_outcome.require(),
                comments=comments,
                store=store,
                version_aliases=version_aliases,
            )
        except ValueError as refusal:
            report.refusals.append(str(refusal))
            continue

        write_thread_context(conn, assembled)
        report.assembled += 1
        report.comments_held += len(comments)
        report.comments_selected += assembled.child_count

    return report


def _version_aliases(conn):
    """The registry's VERSION and SNAPSHOT surfaces, which `names_version` counts.

    Filtered on `model_alias.specificity`, not all aliases: `names_version` asks
    whether a comment names a specific version (`sonnet 4`, `opus 4.6`), and a
    family bare (`sonnet`) is precisely what it must NOT count — a comment saying
    only `sonnet` is the low-specificity case ranking exists to sink. Reading all
    aliases would score every family mention as version-specific, the same
    over-broadening `specificity.py`'s own comment records costing weeks.
    """
    rows = conn.execute(
        "SELECT DISTINCT normalized FROM model_alias "
        "WHERE normalized IS NOT NULL AND specificity IN ('version', 'snapshot')"
    ).fetchall()
    return {r[0] for r in rows if r[0]}
