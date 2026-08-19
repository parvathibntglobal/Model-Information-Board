"""FR-31: the context limit engineers report, never the one the provider prints.

THIS IS THE ONE FIGURE ON THE BOARD THAT REMOVES CANDIDATES SILENTLY

Every other number here argues its case in front of a reader and can be
disagreed with. `reported_low` is a HARD FILTER. The schema says why, and it is
worth repeating where the code lives:

    "a wrong `cell` shows up as a phrase somebody can read, a wrong
     `reported_low` shows up as an ABSENCE, and nobody audits a model that was
     never in the list."

judge/ has already made this exact mistake once. A hard filter read an absent
`supports_tools` as "cannot" and took a candidate list from eleven models to
one, and it surfaced as an absence with nothing on the page to disagree with.
Rule 6 was written from that incident. This module is the same hazard with a
different column, so the three-state result below is not defensive style - it
is the specific repair for a defect this lane has already shipped.

THREE STATES, AND ONLY ONE OF THEM MAY EXCLUDE

    MEETS     somebody reported working at or above the requirement
    FAILS     somebody reported it breaking below the requirement
    UNKNOWN   nobody has reported. NOT a failure, and it must not filter.

An unknown model stays in the list carrying a caveat, because excluding it
makes the board conservative in a way that quietly costs money - the cheap and
obscure models are exactly the ones nobody has posted about.

ONE VOICE IS NOT A REPORTED LIMIT

A single person saying "it fell over at 100k" is a data point, not a
threshold, and promoting it to a hard filter would let one bad afternoon
remove a model from every long-context recommendation. `MIN_VOICES_FOR_LIMIT`
is the floor, and below it the answer is UNKNOWN rather than a limit nobody
corroborated.

PROVENANCE IS NOT DECORATION

`assert_no_fixtures` refuses startup outside development while any row here is
`hand_seeded` - wired in `collect/ops/preflight.py` and verified firing. A
derived row is `harvested`. Nothing in this module writes `hand_seeded`; a
human typing a threshold is the only thing that should, and it should stop
production from booting.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

#: Distinct people who must have reported a limit before it filters anything.
#:
#: Three, matching the publication gate's spirit rather than its arithmetic:
#: the gate weighs `n_eff` because a cell is a claim about quality, and this is
#: a count of PEOPLE because a limit is a claim about a number. One voice is an
#: anecdote; the cost of treating it as a threshold is a model silently absent
#: from every long-context answer.
MIN_VOICES_FOR_LIMIT = 3


class Verdict(StrEnum):
    MEETS = "meets"
    FAILS = "fails"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ReportedContext:
    """What people say a model actually handles."""

    model_version_id: str
    advertised: int | None = None
    reported_low: int | None = None
    reported_high: int | None = None
    voices: int = 0
    quote_ids: tuple[str, ...] = ()
    provenance: str = "harvested"

    @property
    def is_corroborated(self) -> bool:
        """Whether this is a limit or somebody's afternoon."""
        return self.voices >= MIN_VOICES_FOR_LIMIT and self.reported_low is not None

    @property
    def hand_seeded(self) -> bool:
        return self.provenance == "hand_seeded"

    @property
    def gap_to_advertised(self) -> int | None:
        """How far short of the printed number people report, or None.

        `None` when either figure is missing, rather than 0. A missing
        advertised window is not a model that advertises nothing.
        """
        if self.advertised is None or self.reported_low is None:
            return None
        return self.advertised - self.reported_low

    def check(self, required_tokens: int) -> Verdict:
        """The filter. UNKNOWN never excludes.

        Deliberately not a bool. A boolean forces every caller to choose which
        way "we do not know" collapses, and the incident that produced rule 6
        was exactly that collapse made silently.
        """
        if not self.is_corroborated:
            return Verdict.UNKNOWN
        assert self.reported_low is not None  # is_corroborated guarantees it
        return Verdict.MEETS if self.reported_low >= required_tokens else Verdict.FAILS

    def caveat(self, required_tokens: int) -> str | None:
        """What must be said beside a verdict, or None when nothing need be."""
        verdict = self.check(required_tokens)
        if verdict is Verdict.UNKNOWN:
            if self.reported_low is not None and self.voices:
                return (
                    f"{self.voices} "
                    f"{'person has' if self.voices == 1 else 'people have'} "
                    f"reported an effective limit, which is fewer than the "
                    f"{MIN_VOICES_FOR_LIMIT} needed to filter on. Not excluded, "
                    f"and not confirmed."
                )
            return (
                "Nobody has reported an effective context limit for this model. "
                "It is not excluded — an absence of reports is not a reported "
                "failure — but the advertised window is unverified."
            )
        if verdict is Verdict.FAILS:
            gap = self.gap_to_advertised
            body = (
                f"{self.voices} people report an effective limit around "
                f"{self.reported_low:,} tokens, below the {required_tokens:,} "
                f"this task needs."
            )
            if gap is not None and gap > 0:
                body += f" The advertised window is {self.advertised:,}."
            return body
        if self.hand_seeded:
            return (
                "This threshold was hand-seeded rather than harvested, so it is "
                "a development value and not evidence."
            )
        return None


class ReportedContextStore:
    """Reads and writes `reported_context`. Never commits."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def for_model(self, model_version_id: str) -> ReportedContext:
        """Always returns a row-shaped answer, never None.

        A missing row becomes a `ReportedContext` with no figures, which
        `check` reports as UNKNOWN. Returning None would make every caller
        write the absent case themselves, and one of them would get it wrong in
        the direction that excludes.
        """
        row = self._conn.execute(
            "SELECT advertised, reported_low, reported_high, quote_ids, provenance "
            "FROM reported_context WHERE model_version_id = %s",
            (model_version_id,),
        ).fetchone()
        if row is None:
            return ReportedContext(model_version_id=model_version_id)
        quote_ids = tuple(row[3] or ())
        return ReportedContext(
            model_version_id=model_version_id,
            advertised=row[0],
            reported_low=row[1],
            reported_high=row[2],
            voices=len(quote_ids),
            quote_ids=quote_ids,
            provenance=row[4],
        )

    def derive(self, model_version_id: str) -> ReportedContext:
        """Compute a limit from claims that stated a context size.

        THE LOW IS THE LOWEST CORROBORATED FAILURE, not the mean. Averaging
        "worked at 200k" with "broke at 30k" produces 115k, a number nobody
        reported and which would pass a task that the 30k report says fails.
        Rule 3 forbids the synthesis; this is where it would be tempting.

        Counted over DISTINCT AUTHORS rather than claims, so one person
        posting three times is one voice - the same rule the publication gate
        applies, for the same reason.
        """
        row = self._conn.execute(
            """
            SELECT min((c.conditions->>'context_size')::int),
                   max((c.conditions->>'context_size')::int),
                   count(DISTINCT coalesce(c.author_id, c.id)),
                   array_agg(c.id)
            FROM claim c
            WHERE c.model_version_id = %s
              AND c.polarity = 'negative'
              AND c.quote_verified
              AND c.conditions->>'context_size' IS NOT NULL
            """,
            (model_version_id,),
        ).fetchone()
        if row is None or row[0] is None:
            return ReportedContext(model_version_id=model_version_id)
        return ReportedContext(
            model_version_id=model_version_id,
            reported_low=row[0],
            reported_high=row[1],
            voices=row[2] or 0,
            quote_ids=tuple(row[3] or ()),
            provenance="harvested",
        )

    def write(self, reported: ReportedContext) -> None:
        """Only ever `harvested`.

        A `hand_seeded` row stops production booting, and nothing here should
        be able to produce one by accident - a human typing a threshold is the
        only thing that should, deliberately and visibly.
        """
        if reported.provenance != "harvested":
            raise ValueError(
                f"refusing to write provenance={reported.provenance!r}. This "
                f"module derives from claims, so anything it writes is "
                f"harvested; a hand-seeded threshold must be entered "
                f"deliberately, because it refuses production startup."
            )
        self._conn.execute(
            """
            INSERT INTO reported_context (model_version_id, advertised,
                                          reported_low, reported_high, quote_ids,
                                          provenance)
            VALUES (%s, %s, %s, %s, %s, 'harvested')
            ON CONFLICT (model_version_id) DO UPDATE SET
                advertised    = EXCLUDED.advertised,
                reported_low  = EXCLUDED.reported_low,
                reported_high = EXCLUDED.reported_high,
                quote_ids     = EXCLUDED.quote_ids,
                provenance    = 'harvested',
                computed_at   = now()
            """,
            (
                reported.model_version_id,
                reported.advertised,
                reported.reported_low,
                reported.reported_high,
                list(reported.quote_ids),
            ),
        )
