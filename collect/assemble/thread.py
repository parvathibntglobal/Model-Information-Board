"""E3 — assemble a fetched thread into a `thread_context` row.

The last refusal reason is gone. `assemble_thread` refused for eighteen days
because a selection that cannot state what it saw would write *"the top 5
children"* when it means *"the top 5 of the 4% we happened to fetch"*. #54
landed the four coverage columns on 2026-08-18, so it can now state it.

WHAT THE SELECTION IS, AND WHAT IT IS NOT
------------------------------------------
Children ranked by `specificity_score x log(1 + engagement)`, per
`collect/CLAUDE.md`. The top-voted replies are agreement and jokes; the two-line
correction — *"you had `tool_choice` misconfigured"* — sits at +2 and is the one
that carries the condition.

**But that ranking is over WHAT WE OBSERVED, and the data cannot support a
global one.** One `getPostComments` call returned 200 of 4,833 comments; Reddit
orders SIBLINGS rather than the tree, with 30% of adjacent pairs score
inversions and a depth-2 comment scoring 610 sitting under top-level comments
scoring 6. So the last-seen score bounds nothing unseen.

`selection_method` therefore carries the qualifier rather than the bare value:

    specificity_x_log_engagement            asserts a global ranking
    specificity_x_log_engagement@observed   asserts what actually happened

The schema's DEFAULT is the bare form and this never writes it. A row reading
the default would be claiming the thing the refusal spent eighteen days
protecting against.

`coverage_ratio` IS NOT WRITTEN
-------------------------------
It is `GENERATED ALWAYS AS ... STORED`, so Postgres computes it and rejects an
explicit value — including an explicit NULL. The insert omits the column
entirely. That is not a workaround: it is the point of generating it, and the
reason it is generated is that a derived value stored beside its inputs drifts
the first time somebody corrects `hidden_children_min` in a backfill.

`extraction_version` DOES NOT EXIST YET
----------------------------------------
Proposed on #5 (comment 7, item A4) and not ruled. A `thread_context` written
without it is a flattening nobody can identify later, which is the argument that
got it proposed.

**In the meantime `pipeline_version` carries it**, which is weaker in one
specific way worth writing down: it changes for ANY change to `collect/`, so it
over-identifies — two flattenings under different `pipeline_version`s may be
byte-identical. It never under-identifies, which is the direction that matters,
**provided `PIPELINE_VERSION` is bumped when the flattener changes.** That
proviso is the whole guarantee, and it is a convention rather than a check.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from collect.adapters.reddit_comments import ParsedThread, RedditComment
from collect.assemble.flatten import Flattened, flatten
from collect.config import settings
from collect.ids import stable_id
from collect.rawstore import FLATTENED, RawStore
from collect.triage.specificity import score_document

#: What `selection_method` records. The `@observed` suffix is load-bearing: the
#: bare value asserts a global ranking, and 200 of 4,833 comments is not one.
SELECTION_METHOD = "specificity_x_log_engagement@observed"

#: `thread_context.member_document_ids` is "root + the 3-5 selected children".
MAX_CHILDREN = 5


@dataclass(frozen=True)
class AssembledThread:
    """One `thread_context` row, plus what it took to build it.

    Returned as a value rather than written directly so a caller can inspect
    what is about to be stored — the same arrangement as `StoredClaim` in the
    other lane, and for the same reason.
    """

    id: str
    thread_root_id: str
    member_document_ids: tuple[str, ...]
    flattened: Flattened
    flattened_text_ref: str
    observed_children: int
    hidden_children_min: int
    hidden_branches_unsized: int
    pipeline_version: str
    selection_method: str = SELECTION_METHOD

    @property
    def child_count(self) -> int:
        """Selected children, not observed ones. `observed_children` is that."""
        return len(self.member_document_ids) - 1

    def as_row(self) -> dict[str, Any]:
        """The insert payload. **`coverage_ratio` is absent, deliberately.**

        It is GENERATED ALWAYS, so Postgres rejects an explicit value — passing
        NULL is an error, not a no-op. Omitting the key is how a generated
        column is written.
        """
        return {
            "id": self.id,
            "thread_root_id": self.thread_root_id,
            "member_document_ids": list(self.member_document_ids),
            "flattened_text_ref": self.flattened_text_ref,
            "offset_map": self.flattened.as_offset_map(),
            "child_count": self.child_count,
            "selection_method": self.selection_method,
            "observed_children": self.observed_children,
            "hidden_children_min": self.hidden_children_min,
            "hidden_branches_unsized": self.hidden_branches_unsized,
            "pipeline_version": self.pipeline_version,
        }


def rank_children(
    comments: tuple[RedditComment, ...], *, version_aliases
) -> list[tuple[float, RedditComment]]:
    """`specificity_score x log(1 + engagement)`, highest first.

    Engagement is `max(score, 0)`: a comment at -3 is not negatively relevant,
    it is unpopular, and a negative multiplier would invert the specificity term
    it multiplies. `log1p` so one very popular joke cannot outrank several
    specific corrections.

    Ties break on `external_id`, so two comments with identical scores select
    deterministically and a re-run produces the same row.
    """
    ranked = []
    for comment in comments:
        specificity = score_document(comment.body, version_aliases=version_aliases)
        engagement = math.log1p(max(comment.score or 0, 0))
        ranked.append((specificity.score * engagement, comment))
    ranked.sort(key=lambda pair: (-pair[0], pair[1].external_id))
    return ranked


def assemble(
    thread: ParsedThread,
    *,
    root_text: str,
    root_document_id: str,
    store: RawStore,
    version_aliases,
    max_children: int = MAX_CHILDREN,
    pipeline_version: str | None = None,
) -> AssembledThread:
    """Build the row. Writes the flattened text to the store; touches no database.

    `root_text` is passed rather than read from the payload because the root is
    a `document` the caller already has — assembly does not re-parse what
    harvest already stored.
    """
    version = pipeline_version or settings().pipeline_version

    selected = [comment for _score, comment in rank_children(
        thread.comments, version_aliases=version_aliases
    )[:max_children]]

    documents: list[tuple[str, str]] = [(root_document_id, root_text)]
    documents.extend((f"reddit:{c.external_id}", c.body) for c in selected)

    flattened = flatten(documents)
    stored = store.put(flattened.text, namespace=FLATTENED)

    root_id = thread.root_post_id or root_document_id
    return AssembledThread(
        # The flattening is part of what the row asserts, so the version is in
        # the id: a re-flattening under changed rules is a different row rather
        # than an overwrite of one nobody can tell changed.
        id=stable_id("thread_context", root_id, version),
        thread_root_id=root_id,
        member_document_ids=flattened.member_document_ids,
        flattened=flattened,
        flattened_text_ref=stored.ref,
        observed_children=thread.coverage.observed_children,
        hidden_children_min=thread.coverage.hidden_children_min,
        hidden_branches_unsized=thread.coverage.hidden_branches_unsized,
        pipeline_version=version,
    )


def write_thread_context(conn, assembled: AssembledThread) -> str:
    """Insert the row. Returns its id.

    ON CONFLICT DO NOTHING rather than an upsert: `offset_map` is what every
    stored quote resolves against, so replacing one in place would silently
    invalidate claims already written against it. A re-flattening under changed
    rules gets a different id and a new row — see `assemble`.
    """
    import json

    row = assembled.as_row()
    conn.execute(
        """
        INSERT INTO thread_context (
            id, thread_root_id, member_document_ids, flattened_text_ref,
            offset_map, child_count, selection_method, observed_children,
            hidden_children_min, hidden_branches_unsized, assembled_at,
            pipeline_version
        ) VALUES (
            %(id)s, %(thread_root_id)s, %(member_document_ids)s,
            %(flattened_text_ref)s, %(offset_map)s, %(child_count)s,
            %(selection_method)s, %(observed_children)s,
            %(hidden_children_min)s, %(hidden_branches_unsized)s, %(assembled_at)s,
            %(pipeline_version)s
        )
        ON CONFLICT (id) DO NOTHING
        """,
        {**row, "offset_map": json.dumps(row["offset_map"]),
         "assembled_at": datetime.now(UTC)},
    )
    return assembled.id
