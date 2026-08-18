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

#: Below this, a cell's evidence came from threads we mostly did not read, and
#: the caveat is stated in the strong form. Not a gate - nothing is withheld at
#: any value - only the wording changes.
#:
#: 0.5 because it is the point where "most of the thread" stops being true, not
#: because anything measured says 0.5 is where quality falls off. Nothing does,
#: and inventing a threshold that sounds evidence-based would itself be rule 7.
MOSTLY_UNREAD = 0.5


@dataclass(frozen=True)
class ThreadCoverage:
    """One thread a cell's claims came from."""

    thread_context_id: str

    #: NULL means NOT MEASURED, and never 0.0. Kept as `None` all the way
    #: through so no layer can accidentally average it as a zero.
    ratio: float | None
    observed_children: int | None
    hidden_children_min: int | None

    @property
    def measured(self) -> bool:
        return self.ratio is not None

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

    @property
    def caveat(self) -> str | None:
        """What must be said beside this cell's counts, or None if nothing need be.

        Returns None ONLY when every thread was measured and every one was
        well covered. Any other state produces a sentence, because every other
        state is one a reader would want and could not infer from the counts.
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
            parts.append(
                f"Drawn from threads we read at most {worst:.0%} of "
                f"({thinnest.population}). The counts below are of people we "
                f"read, not of everyone who spoke."
            )
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
                   tc.observed_children, tc.hidden_children_min
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
                )
                for r in rows
            )
        )
