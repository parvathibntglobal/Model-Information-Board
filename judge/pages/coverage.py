"""The coverage page: what the board does not know, and what it has not checked.

THE TWO STATES THIS PAGE EXISTS TO KEEP APART

    no gap recorded  ->  we looked and found nothing
    nothing recorded ->  nobody looked

They render identically from an empty table and they mean opposite things.
Rule 4 is usually about a capability nobody discussed; this is the same rule one
level up, about a whole surface nobody measured. A coverage page that reads zero
rows and prints "no gaps" is not a neutral bug - it is the most flattering thing
this system could say about itself, and it would say it with no measurement
behind it at all.

WHICH IS THE STATE TODAY

`collect/registry/load.py:coverage_gaps()` builds the objects. Nothing inserts
them: a search for `INSERT INTO coverage_gap` returns nothing anywhere in the
repository, and `collect/ops/chain.py` names the consequence in its own
starvation note - "coverage_gap stays empty, so the four kinds". So every kind
below is UNMEASURED today, and this page's job right now is to say so loudly
rather than render an encouraging blank.

That is not a defect in `collect/`. The writer is queued behind the chain that
would call it. It becomes a defect only if this page hides it, which is what
this module is written to prevent - and it is the same shape as the four
assertion functions with no callers, found twice before on this project.

RULE 7 HERE

A count of gaps means nothing without the population it was drawn from. "Three
unsourced fields" is not a claim; "three unsourced fields across the 10 models
in the registry, from the load of 2026-08-18" is. Every figure returned here
therefore carries its `pipeline_version`, and the report refuses to total across
versions - two runs of different code are two populations, and a gap that was
found, fixed and re-reported would count twice into a figure about neither.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: The four kinds in `coverage_gap_kind_ck`, and what SILENCE means for each.
#:
#: The second half of each pair is the load-bearing part. Every kind's absence
#: has an innocent explanation and a guilty one, and they are different per
#: kind. A page that prints the same "none" for all four is not reporting on
#: four things - it is printing one word four times.
KNOWN_KINDS: dict[str, tuple[str, str]] = {
    "unsourced-field": (
        "a registry field that cites no source",
        "either every field is sourced, or the loader never reported",
    ),
    "missing-spelling": (
        "a model a search API cannot find by one of its three renderings",
        "either every model is fully spelled, or nothing checked the spellings",
    ),
    "out-of-window": (
        "evidence that fell outside the collection window",
        "either the window caught everything, or no window was applied",
    ),
    "unknown-release-date": (
        "a model whose release date could not be established",
        "either every date is known, or dates were never sought",
    ),
}


@dataclass(frozen=True)
class KindReport:
    """One gap kind, and whether we are entitled to say anything about it."""

    kind: str
    rows: int
    subjects: int
    examples: tuple[str, ...] = ()

    #: A kind absent from `KNOWN_KINDS`. The schema comment predicted this
    #: exactly - "an unconstrained `kind` is how a fifth gap type gets added
    #: later without the coverage page knowing it exists" - so an unrecognised
    #: kind is surfaced rather than filtered out. Dropping it would make this
    #: page quietly wrong in the direction of under-reporting, which is the
    #: direction that flatters us. Engineer 1's proposal adds two.
    recognised: bool = True

    @property
    def measured(self) -> bool:
        """Rule 6 as a property rather than a comment.

        Zero rows is NOT zero gaps. It is an unmeasured kind, and the only
        thing separating the two is whether a writer ran - which this table
        cannot tell us, so the honest answer is the weaker one.
        """
        return self.rows > 0

    @property
    def headline(self) -> str:
        if not self.measured:
            silence_means = KNOWN_KINDS.get(self.kind, ("", "nothing has reported it"))[1]
            return f"not measured - {silence_means}"
        return f"{self.rows} recorded across {self.subjects} subjects"


@dataclass(frozen=True)
class CoverageReport:
    """The board's blind spots, for ONE pipeline version.

    Scoped to one version on purpose. `coverage_gap` carries `pipeline_version`
    on every row, and summing across versions counts a gap that was found,
    fixed and re-reported as two - a figure about no population at all.
    """

    pipeline_version: str | None
    kinds: tuple[KindReport, ...] = ()

    @property
    def measured_at_all(self) -> bool:
        """False means no gap writer has ever run against this database.

        This is a statement about OUR INSTRUMENT rather than about the world,
        and it has to reach the page as one.
        """
        return any(k.measured for k in self.kinds)

    @property
    def unrecognised(self) -> tuple[KindReport, ...]:
        return tuple(k for k in self.kinds if not k.recognised)

    @property
    def summary(self) -> str:
        """The first sentence a reader sees. It must not be reassuring by default."""
        if self.pipeline_version is None:
            return (
                "No coverage measurement has ever run. Nothing below is a finding "
                "about the board's coverage - it is the absence of any check, and "
                "it must not be read as completeness."
            )
        if not self.measured_at_all:
            return (
                f"A run is recorded for {self.pipeline_version}, but no gap of any "
                f"kind was written. That is one measurement finding zero gaps, not "
                f"{len(self.kinds)}."
            )
        measured = sum(1 for k in self.kinds if k.measured)
        total = sum(k.rows for k in self.kinds)
        unmeasured = len(self.kinds) - measured
        return (
            f"{total} gaps across {measured} of {len(self.kinds)} kinds, from "
            f"pipeline {self.pipeline_version}. The remaining {unmeasured} were "
            f"not measured, which is not the same as clear."
        )


class CoveragePage:
    """Reads `coverage_gap`. Writes nothing, ever.

    `collect/` owns this table - its schema header says so - and this lane's
    entire relationship to it is a SELECT.
    """

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def latest_pipeline_version(self) -> str | None:
        """The most recent version that wrote anything, or None if none has.

        `None` rather than a default. A default here would fabricate a
        population for every figure downstream - rule 6, with rule 7 landing
        on top of it.
        """
        row = self._conn.execute(
            "SELECT pipeline_version FROM coverage_gap ORDER BY observed_at DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None

    def report(self, *, pipeline_version: str | None = None) -> CoverageReport:
        version = pipeline_version or self.latest_pipeline_version()
        if version is None:
            # Never measured. Every known kind reports as unmeasured rather than
            # as clear, and the caller gets no version to attribute figures to,
            # because there is no population to attribute them to.
            return CoverageReport(
                pipeline_version=None,
                kinds=tuple(KindReport(kind=k, rows=0, subjects=0) for k in sorted(KNOWN_KINDS)),
            )

        rows = self._conn.execute(
            "SELECT kind, count(*), count(DISTINCT subject), "
            "(array_agg(detail ORDER BY observed_at DESC))[1:3] "
            "FROM coverage_gap WHERE pipeline_version = %s GROUP BY kind",
            (version,),
        ).fetchall()
        seen = {r[0]: (r[1], r[2], tuple(r[3] or ())) for r in rows}

        reports: list[KindReport] = [
            KindReport(
                kind=kind,
                rows=seen.get(kind, (0, 0, ()))[0],
                subjects=seen.get(kind, (0, 0, ()))[1],
                examples=seen.get(kind, (0, 0, ()))[2],
            )
            for kind in sorted(KNOWN_KINDS)
        ]
        # A kind the CHECK now permits and this module has never heard of.
        # Appended rather than dropped - see KindReport.recognised.
        reports.extend(
            KindReport(
                kind=kind, rows=count, subjects=subjects, examples=examples, recognised=False
            )
            for kind, (count, subjects, examples) in sorted(seen.items())
            if kind not in KNOWN_KINDS
        )
        return CoverageReport(pipeline_version=version, kinds=tuple(reports))
