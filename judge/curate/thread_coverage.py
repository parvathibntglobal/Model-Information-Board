"""How much of each thread a cell's evidence was actually drawn from.

THE PROBLEM THIS EXISTS FOR

Engineer 1's first real `thread_context` row reads `coverage_ratio = 0.238`.
195 comments observed against a known minimum of 818, so that thread was seen
at AT MOST 24%. A cell built from claims in it would otherwise publish

    "four engineers report schema failures above 6 tools"

with nothing anywhere saying the four were counted in a quarter of a
conversation. That is rule 7 exactly: a real figure silently answering a
question it was not asked. "Four engineers" invites the reading "four out of
the people who discussed it", and the honest statement is "four out of the
people we read, which was at most a quarter of them".

NOT A GATE, AND DELIBERATELY NOT

Low coverage does not block publication. A thread seen at 24% is still four
people saying a thing, and refusing it would delete real evidence to protect a
number - which is the opposite failure and a more expensive one, because it
would show up as silence and rule 4 says silence is not criticism. The gate
decides whether there is enough evidence; this decides what has to be said
alongside it.

COMPUTED, NEVER STORED

`cell` gets no coverage column. `coverage_ratio` is GENERATED on
`thread_context` precisely because a derived value written beside its inputs
drifts - Engineer 1 counted that as the fifth instance of one bug on this
project. Copying it onto `cell` would be the sixth, and it would drift in the
direction that flatters coverage, because a backfill correcting
`hidden_children_min` would leave the copy behind. So this reads through
`claim -> thread_context` every time and stores nothing.

THREE THINGS THAT LOOK LIKE PEDANTRY AND ARE NOT

1. `ratio is None` means NOT MEASURED. It is never 0.0. A `thread_context`
   written before #54 has no coverage, and "we saw none of it" is a different
   and much worse statement than "nobody has measured this". Rule 6.
2. Every ratio is an UPPER BOUND. `hidden_children_min` is a floor, so the
   denominator is understated and the ratio is correspondingly overstated. The
   phrasing says "at most" and never "we saw 24%".
3. The caveat is TEMPLATE-ASSEMBLED from counts. No model writes it (rule 2),
   and no synthesised number appears in it (rule 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from judge.curate.gate import N_EFF_MINIMUM

#: Below this, the thread was mostly unread and the caveat is stated. Not a
#: gate - nothing is withheld at any value - only the wording changes.
#:
#: 0.5 because it is where "most of the thread" stops being true, not because
#: anything measured says quality falls off there. Nothing does.
MOSTLY_UNREAD = 0.5

#: The `selection_method` prefixes under which children were actually RANKED.
#:
#: Matched by prefix because the Reddit value carries an `@observed` suffix
#: asserting what the ranking ranked over, and a new suffix on the same method
#: must not silently become "not ranked". `issue_with_comments` ranks too -
#: `collect/assemble/issue.py` ranks an issue's replies without votes.
#:
#: EVERY OTHER METHOD FETCHED NO CHILDREN, so there is nothing a ranking could
#: have been applied to.
RANKED_METHODS = ("specificity_x_log_engagement", "issue_with_comments")

#: How much margin over the publication gate counts as comfortable.
#:
#: ENGINEER 1'S CORRECTION, ADOPTED. The first version keyed the caveat's
#: strength to coverage alone, and E1's objection was right: the question is
#: not "did we read most of the thread", it is "could the unread part overturn
#: this". Those come apart hard - 24% coverage with eight independent voices is
#: stronger evidence than 80% with two. So strength keys to margin over
#: `N_EFF_MINIMUM`, which has a real basis (our own gate) rather than being a
#: round number.
#:
#: AND THE LIMIT OF THAT, WHICH NEITHER OF US HAD RAISED. Margin protects
#: against SAMPLING NOISE - the risk that a small read sample happened to
#: over-represent one view. It does NOT protect against SELECTION BIAS, and our
#: gap is a biased gap by construction - though NOT always in the way this
#: comment used to say. Where `selection_method` is
#: `specificity_x_log_engagement@observed`, the comments we read are the
#: high-engagement, high-specificity ones and the 623 we did not are
#: systematically the quieter ones; no amount of `n_eff` cures that, because
#: every voice in it was drawn from the same ranked top slice. Where it is
#: `post_body_only` or `issue_body_only` the bias is larger and of a different
#: kind: no comment was fetched at all, so every voice counted is the ROOT
#: AUTHOR and the discussion is absent entire. `_not_a_random_sample` says
#: which, per cell.
#:
#: So margin softens the wording and never removes the caveat, and every
#: low-coverage caveat says the unread part is not a random sample. A cell that
#: said "plenty of evidence, coverage fine" would be claiming a calibration
#: nobody has done.
COMFORTABLE_MARGIN = 2.0


@dataclass(frozen=True)
class ThreadCoverage:
    """One thread a cell's claims came from."""

    thread_context_id: str

    #: NULL means NOT MEASURED, and never 0.0. Kept as `None` all the way
    #: through so no layer can accidentally average it as a zero.
    ratio: float | None
    observed_children: int | None
    hidden_children_min: int | None

    #: `thread_context.selection_method`, because the caveat below said WHY the
    #: unread part is not a random sample and was wrong about it for four
    #: contexts in five.
    #:
    #: Only `specificity_x_log_engagement@observed` ranks anything. The other
    #: methods fetched no children at all, so there was no ranking and no
    #: remainder - the unread part is the WHOLE discussion. Counted 2026-09-15:
    #:
    #:     post_body_only                          1,536   nothing ranked
    #:     issue_body_only                         1,360   nothing ranked
    #:     issue_with_comments                       584   ranked
    #:     whole_document                            318   nothing to rank
    #:     specificity_x_log_engagement@observed      232   ranked
    #:
    #: None where the method was not read, which `ranked` treats as unknown
    #: rather than as either answer (rule 6).
    selection_method: str | None = None

    @property
    def measured(self) -> bool:
        return self.ratio is not None

    @property
    def ranked(self) -> bool | None:
        """Were the comments we DID read chosen by a ranking?

        True, False, or None for "the method was not recorded". Three states
        rather than two, because the caveat says a different sentence for each
        of the first two and must say neither on a guess.
        """
        if self.selection_method is None:
            return None
        return self.selection_method.startswith(RANKED_METHODS)

    @property
    def population(self) -> str:
        """Rule 7 in one string: the figure with its denominator.

        A bare "24%" is not a claim. "195 of at least 818 comments" is, and it
        is visibly a bound rather than a measurement.
        """
        if self.observed_children is None or self.hidden_children_min is None:
            return "population not recorded"
        total = self.observed_children + self.hidden_children_min
        return f"{self.observed_children} of at least {total} comments"


#: The claim these two sentences share, and the only one both can make.
_NOT_EVERYONE = (
    "The counts are of people we read, not of everyone who spoke, and the part "
    "we did not read is not a random sample"
)


def _not_a_random_sample(threads) -> str:
    """WHY the unread part is not a random sample — which differs by method.

    THIS SENTENCE WAS WRONG ON FOUR CONTEXTS IN FIVE AND IT WAS ON A PAGE.
    It read, for every thread:

        "...comments were ranked before selection, so the unread ones are the
         quieter ones."

    True of `specificity_x_log_engagement@observed` and `issue_with_comments`.
    FALSE of `post_body_only`, `issue_body_only` and `whole_document` — 3,214 of
    4,030 contexts counted 2026-09-15 — where NOTHING WAS RANKED because nothing
    was fetched. There is no remainder in those; the unread part is the entire
    discussion, which for 2,077 contexts is known to exist upstream
    (`hidden_children_min > 0`).

    The conclusion survived either way and the REASON did not, which is the
    thing worth naming: a caveat that gives a false mechanism is not a softer
    version of a true one. A reader who believes we ranked and skipped the
    quiet comments will picture a thread we sampled; the truth on a
    `post_body_only` row is a thread we did not open. Those imply different
    follow-up work, and the second is rule 7's shape — a true statement
    answering a question it was not asked.

    So: one sentence per case, and a third that claims neither when
    `selection_method` was not recorded (rule 6 — not measured is not a licence
    to pick the likelier one).
    """
    kinds = {t.ranked for t in threads}

    if kinds == {True}:
        return (
            f"{_NOT_EVERYONE}: comments were ranked before selection, so the "
            f"unread ones are the quieter ones."
        )
    if kinds == {False}:
        return (
            f"{_NOT_EVERYONE}: no comments were fetched for these threads at "
            f"all, so what is missing is the discussion itself rather than its "
            f"quieter half."
        )
    if kinds == {None}:
        return (
            f"{_NOT_EVERYONE}, and how the part we read was chosen is not "
            f"recorded for these threads."
        )
    # MIXED, OR PARTLY UNRECORDED. Naming both is the honest form: collapsing to
    # whichever is commoner would put one of the two false sentences back on the
    # page, which is the defect this function exists for.
    said = []
    if True in kinds:
        said.append(
            "on some, comments were ranked and the unread ones are the quieter ones"
        )
    if False in kinds:
        said.append(
            "on others, no comments were fetched at all, so the discussion itself "
            "is missing"
        )
    if None in kinds:
        said.append(
            "and on the rest it is not recorded which of those applies"
        )
    return f"{_NOT_EVERYONE}: " + "; ".join(said) + "."


@dataclass(frozen=True)
class CellCoverage:
    """The coverage of every thread behind one cell."""

    threads: tuple[ThreadCoverage, ...] = ()

    @property
    def measured(self) -> tuple[ThreadCoverage, ...]:
        return tuple(t for t in self.threads if t.measured)

    @property
    def unmeasured(self) -> tuple[ThreadCoverage, ...]:
        return tuple(t for t in self.threads if not t.measured)

    @property
    def worst_ratio(self) -> float | None:
        """The lowest MEASURED ratio, or None if nothing was measured.

        `min()` over a list containing None would either raise or, worse,
        silently order None first in some Python versions and treat unmeasured
        as the worst case. Filtered explicitly.
        """
        ratios = [t.ratio for t in self.measured if t.ratio is not None]
        return min(ratios) if ratios else None

    def caveat(self, n_eff: float | None = None) -> str | None:
        """What must be said beside this cell's counts, or None if nothing need be.

        `n_eff` softens the WORDING and never removes the caveat. Passing None
        keeps the strong form, because not knowing the margin is not a reason
        to sound confident.
        """
        if not self.threads:
            return None

        if not self.measured:
            n = len(self.unmeasured)
            threads = "thread" if n == 1 else "threads"
            return (
                f"How much of the source {threads} this was drawn from is not "
                f"recorded ({n} {threads}). The counts are of what we read, and "
                f"we do not know what fraction of the discussion that was."
            )

        worst = self.worst_ratio
        assert worst is not None  # guaranteed by `self.measured` being non-empty
        parts: list[str] = []

        if worst < MOSTLY_UNREAD:
            thinnest = min(self.measured, key=lambda t: t.ratio or 1.0)
            comfortable = n_eff is not None and n_eff >= N_EFF_MINIMUM * COMFORTABLE_MARGIN
            if comfortable:
                parts.append(
                    f"Drawn from threads we read at most {worst:.0%} of "
                    f"({thinnest.population}), though on more voices than the "
                    f"publication bar needs."
                )
            else:
                parts.append(
                    f"Drawn from threads we read at most {worst:.0%} of "
                    f"({thinnest.population}), on barely more evidence than the "
                    f"publication bar needs. The unread part could plausibly "
                    f"change this."
                )
            # Both sentences are said at EVERY margin, because margin touches
            # neither of them.
            #
            # The first is the specific misreading this module exists to
            # prevent: "four engineers" invites "four of the people who
            # discussed it", and the true statement is "four of the people we
            # read". Dropping it while rewording for margin was caught by the
            # test that asserts it, which is what that test is for.
            #
            # The second is the selection bias. The read comments were ranked
            # by specificity and engagement, so the unread ones are
            # systematically the quieter ones rather than a random remainder -
            # and no number of voices drawn from the same top slice corrects
            # for that.
            parts.append(_not_a_random_sample(self.measured))
        if self.unmeasured:
            n = len(self.unmeasured)
            parts.append(
                f"{n} further {'thread' if n == 1 else 'threads'} have no "
                f"coverage recorded, so this is not the whole picture either."
            )
        return " ".join(parts) if parts else None


class CoverageReader:
    """Reads `thread_context` coverage for the claims behind a cell.

    Read-only, like everything else this lane does with `collect/`'s tables.
    """

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def for_cell(
        self, *, model_version_id: str, capability_key: str, condition_bucket: str
    ) -> CellCoverage:
        rows = self._conn.execute(
            """
            SELECT DISTINCT tc.id, tc.coverage_ratio,
                   tc.observed_children, tc.hidden_children_min,
                   tc.selection_method
            FROM claim c
            JOIN thread_context tc ON tc.id = c.thread_context_id
            WHERE c.model_version_id = %s
              AND c.capability_key = %s
              AND c.condition_bucket = %s
            ORDER BY tc.id
            """,
            (model_version_id, capability_key, condition_bucket),
        ).fetchall()
        return CellCoverage(
            threads=tuple(
                ThreadCoverage(
                    thread_context_id=r[0],
                    ratio=r[1],
                    observed_children=r[2],
                    hidden_children_min=r[3],
                    selection_method=r[4],
                )
                for r in rows
            )
        )
