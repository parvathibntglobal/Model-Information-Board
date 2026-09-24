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

**In the meantime `pipeline_version` carries it**, and the sentence that stood
here was wrong in the direction it called safe. It read: `pipeline_version`
changes for ANY change to `collect/`, so it over-identifies — two flattenings
under different versions may be byte-identical — but *never* under-identifies,
**provided `PIPELINE_VERSION` is bumped when the flattener changes.**

It under-identified the same day. `PIPELINE_VERSION` was not bumped, and what
changed was not the flattener: it was `collect/triage/specificity.py`, the
scorer that picks WHICH children get flattened. One id, two different
selections, and `ON CONFLICT DO NOTHING` kept the stale row
(`docs/measurements/first-thread-context.md` §4).

The proviso named one path and was read as ranging over all of them. **A proviso
is evidence about the path it names and about nothing else** — the shape is
recorded in `docs/measurements/README.md`, because two people accepted this one
without asking what it ranged over. What `pipeline_version` actually offers here
is over-identification and no lower bound, until an identifier covers what the
row asserts rather than when it was written.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, NamedTuple, Protocol, runtime_checkable

from collect.assemble.flatten import Flattened, flatten
from collect.config import settings
from collect.ids import stable_id
from collect.rawstore import FLATTENED, RawStore
from collect.triage.specificity import (
    names_version,
    score_document,
    score_if_version_inherited,
)


@runtime_checkable
class ThreadMember(Protocol):
    """What ranking and flattening actually touch on a child.

    Three attributes, not a platform type. `RedditComment` satisfies this
    structurally and is no longer imported here — assembly ranked Reddit
    comments because Reddit was the only platform, which is not the same as
    assembly being about Reddit.

    Written as a Protocol rather than left implicit because the previous
    signature said `ParsedThread` and MEANT these three fields; a reader had to
    open the Reddit module to find out which.
    """

    external_id: str
    body: str
    score: int | None


@runtime_checkable
class ThreadInput(Protocol):
    """What `assemble` needs of a fetched thread. `ParsedThread` satisfies it."""

    root_post_id: str | None
    comments: tuple
    coverage: Any

#: What `selection_method` records. The `@observed` suffix is load-bearing: the
#: bare value asserts a global ranking, and 200 of 4,833 comments is not one.
SELECTION_METHOD = "specificity_x_log_engagement@observed"

#: What a ONE-MEMBER thread records. Ruled 2026-08-18.
#:
#: A blog article is a thread of one, so nothing is ranked and nothing is
#: selected: `rank_children(())` returns `[]` and `child_count` is 0. Writing
#: `specificity_x_log_engagement@observed` there would describe a ranking that
#: did not happen, which is the exact failure the `@observed` suffix was added
#: to prevent, one level further out.
#:
#: NOT NULL and not the schema default. The column is `NOT NULL`, and NULL
#: would say "unrecorded" where the truth is "not applicable" (rule 6). The
#: schema DEFAULT is the bare `specificity_x_log_engagement`, which asserts a
#: global ranking and is the one value this module must never write.
WHOLE_DOCUMENT = "whole_document"

#: Blog coverage, ruled 2026-08-18 with `WHOLE_DOCUMENT`. Written here because
#: the blog assemble path does not exist yet and the reasoning must not be
#: rediscovered when it does.
#:
#:   observed_children       0     A MEASUREMENT. We looked and stored none.
#:   hidden_children_min     None  NOT 0. `include_comments=False` means WE
#:                                 withheld the comment section — see
#:                                 `collect/adapters/blog/options.py`. "Nothing
#:                                 was withheld" is true of the platform and
#:                                 false of us, and a post with 400 comments
#:                                 and one with none would both write 0. Rule 6,
#:                                 leaning towards flattering our own coverage.
#:   hidden_branches_unsized 0     A MEASUREMENT. There are no `more` markers.
#:
#: `coverage_ratio` is NULL either way — `COALESCE(0,0) + COALESCE(None,0)` is
#: 0, and the generated CASE has no ELSE — so honesty here costs nothing. What
#: it buys is that `observed_children = 0` still separates a blog row from a
#: pre-#54 row, where all three are NULL.
#:
#: FLAGGED TO ENGINEER 2, NOT SOLVED HERE: a NULL `coverage_ratio` now means
#: both "no children exist" and "never measured", separable only by reading the
#: inputs. That is her display side and rule 4's territory.
BLOG_COVERAGE_HIDDEN_CHILDREN_MIN = None

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
    #: `int | None`, and the None is a real value rather than a gap. A blog
    #: article writes NULL here because `include_comments=False` means we
    #: withheld the comment section — see `BLOG_COVERAGE_HIDDEN_CHILDREN_MIN`.
    #: All four coverage columns are nullable in the schema for the same class
    #: of reason: a row that has not been measured must not read as 0.
    hidden_children_min: int | None
    hidden_branches_unsized: int
    pipeline_version: str
    selection_method: str = SELECTION_METHOD
    #: How many SELECTED children scored on the root's version token rather
    #: than their own text (#307). Not a column - `as_row()` does not carry it,
    #: for the same reason `flattened` is not carried.
    #:
    #: ⚠ `None`, NOT 0, WHERE NOTHING ASKED (rule 6). A GitHub issue ranks with
    #:   `_rank_issue_comments`, which does not inherit at all, and an article
    #:   has no children - so "0 inherited" there would answer a question the
    #:   path never put. A reader summing these must skip None rather than
    #:   coalesce it.
    subject_inherited_children: int | None = None

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


class RankedChild(NamedTuple):
    """One scored comment, and the two facts a caller needs about its score.

    ⚠ THREE FIELDS RATHER THAN A `(score, member)` PAIR, WHICH IS WHY EVERY
      CALLER CHANGED. `subject_inherited` has to travel with the row it
      describes: a count of inherited children recomputed anywhere else would
      be a second implementation of the same rule, and rule 9 wants the value
      to have a named consumer rather than a place it could be derived.
    """

    #: `specificity x log1p(engagement)` — what the ranking sorts on.
    score: float
    member: ThreadMember
    #: WOULD this comment reach its subject through the ROOT's version token
    #: rather than its own text? Derived, never set independently — true when
    #: the root names a version and the comment does not. Same shape and the
    #: same reason as `TriageRun.subject_was_inherited`.
    #:
    #: ⚠ IT DOES NOT AFFECT `score`. See `rank_children` for the measurement
    #:   that stopped it being spent. Consumer named, per rule 9:
    #:   `RedditAssemblyReport.comments_inherited_subject`.
    subject_inherited: bool
    #: The specificity term alone, before engagement multiplies it. Consumer
    #: named: the tie-break below, which is the whole of #307's option 1.
    specificity: float
    #: What `score` would have been built from had the inheritance been spent —
    #: `specificity` plus the `names_version` weight, or `specificity` where the
    #: comment names it already. Carried so the size of the change can be read
    #: off a real sweep rather than argued about (#307, option 3).
    would_score: float


def rank_children(
    comments: tuple[ThreadMember, ...], *, version_aliases, root_text: str
) -> list[RankedChild]:
    """`specificity_score x log(1 + engagement)`, highest first.

    Engagement is `max(score, 0)`: a comment at -3 is not negatively relevant,
    it is unpopular, and a negative multiplier would invert the specificity term
    it multiplies. `log1p` so one very popular joke cannot outrank several
    specific corrections.

    ⚠ `root_text` IS REQUIRED AND IS DELIBERATELY NOT IN THE SCORE (#307).
      Option 4 on that issue was to let a child inherit its thread's version
      token — "it still drops the tool call at 40k" is about whatever the root
      was about — and implementing it regressed the acceptance case that
      justifies this ranking existing at all:

          claude sonnet 4 throws JSONDecodeError at 6 tools, tool_choice=auto
              own 0.800   x log1p(1)   = 0.555        1 vote

          same lol
              own 0.000   x log1p(500) = 0.000        500 votes
              INHERITED 0.150 x log1p(500) = 0.932    outranks the correction

      The reason is general and not a tuning accident. Inheritance adds a flat
      `names_version` weight to every child that does not name the version, so
      a comment whose specificity was zero becomes `0.15 x log1p(votes)` — and
      the whole zero tail is then ranked BY VOTES ALONE. That is precisely the
      "one very popular joke outranks several specific corrections" failure
      `log1p` is here to damp, arriving through the term meant to fix it.

      `names_version` does double duty: it identifies the SUBJECT and it earns
      SPECIFICITY weight. A reply inherits the first and has not earned the
      second, and nothing in the composite can separate them. That separation
      is #307's option 3, deferred.

      So inheritance is MEASURED and NOT SPENT: `subject_inherited` records
      which children would inherit, `RedditAssemblyReport` reports the share,
      and the score is untouched until there is a number to decide on.

      No default, for the reason `child_document_id` has none: a default of
      `""` would silently report that no thread names anything.

    ⚠ TIES BREAK ON SPECIFICITY BEFORE `external_id` (#307, option 1). The
      product is zero for every comment with no votes, and on the measured
      population that is 84% of them — so the previous `(-score, external_id)`
      ordered the overwhelming majority of the corpus ALPHABETICALLY and called
      it a relevance ranking. `external_id` remains the final key, because a
      re-run must still produce the same row.
    """
    #: Scored once for the thread rather than once per comment: the root's text
    #: does not change between children, and `names_version` walks every alias.
    root_names_version = names_version(root_text, version_aliases)

    ranked = []
    for comment in comments:
        own = score_document(comment.body, version_aliases=version_aliases)
        engagement = math.log1p(max(comment.score or 0, 0))
        ranked.append(RankedChild(
            score=own.score * engagement,
            member=comment,
            #: OBSERVED, NOT APPLIED. See the note above: spending this raises
            #: the zero tail off zero and hands the ranking to vote count.
            subject_inherited=root_names_version and not own.names_version,
            specificity=own.score,
            would_score=score_if_version_inherited(own),
        ))
    ranked.sort(key=lambda r: (-r.score, -r.specificity, r.member.external_id))
    return ranked


def assemble(
    thread: ThreadInput,
    *,
    root_text: str,
    root_document_id: str,
    child_document_id: Callable[[ThreadMember], str],
    store: RawStore,
    version_aliases,
    max_children: int = MAX_CHILDREN,
    pipeline_version: str | None = None,
) -> AssembledThread:
    """Build the row. Writes the flattened text to the store; touches no database.

    `root_text` is passed rather than read from the payload because the root is
    a `document` the caller already has — assembly does not re-parse what
    harvest already stored.

    `child_document_id` IS REQUIRED AND HAS NO DEFAULT. This function used to
    build child ids itself as `f"reddit:{c.external_id}"` while taking
    `root_document_id` from the caller — so one of the two ids in the same row
    followed a convention the caller chose and the other followed one assembly
    chose, and only a cross-lane comparison could notice they disagreed. That
    is how Engineer 2's fixture came to strip the `t1_`/`t3_` prefixes
    `collect/` stores. Both ids now come from the same place.

    No default, rather than a Reddit default: a default would let a second
    platform inherit `reddit:` silently, which is the failure this widening
    exists to prevent and not a convenience worth keeping.
    """
    version = pipeline_version or settings().pipeline_version

    ranked = rank_children(
        thread.comments, version_aliases=version_aliases, root_text=root_text
    )[:max_children]
    selected = [r.member for r in ranked]

    documents: list[tuple[str, str]] = [(root_document_id, root_text)]
    documents.extend((child_document_id(c), c.body) for c in selected)

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
        subject_inherited_children=sum(r.subject_inherited for r in ranked),
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
