"""Coverage behind a cell, and the two states it must never merge.

No database. `CoverageReader` takes anything with `.execute`, and the
interesting behaviour is entirely in what the caveat says.
"""

from __future__ import annotations

import re

from judge.curate.thread_coverage import (
    CellCoverage,
    CoverageReader,
    ThreadCoverage,
)


def thread(tc_id="tc1", ratio=None, observed=None, hidden=None) -> ThreadCoverage:
    return ThreadCoverage(
        thread_context_id=tc_id,
        ratio=ratio,
        observed_children=observed,
        hidden_children_min=hidden,
    )


#: Engineer 1's first real row, verbatim. Coverage work that only ever runs
#: against invented numbers tends to be correct about invented numbers.
REAL_ROW = thread("tc:1u1b22l", ratio=0.2383863, observed=195, hidden=623)


class TestNotMeasuredIsNotZero:
    """Rule 6, on the column most likely to break it.

    `coverage_ratio` is NULL on every row written before #54. "We saw none of
    it" and "nobody measured this" are different statements and the second is
    the true one.
    """

    def test_an_unmeasured_thread_is_not_reported_as_zero_coverage(self):
        coverage = CellCoverage(threads=(thread("tc1"),))

        assert coverage.worst_ratio is None
        caveat = coverage.caveat()
        assert caveat is not None
        assert "not recorded" in caveat
        assert not re.search(r"\b0%", caveat), "unmeasured rendered as zero coverage"

    def test_worst_ratio_ignores_unmeasured_rather_than_ranking_it_worst(self):
        """A None sorting first would make every unmeasured thread the worst
        case, which is a definite claim invented out of an absence."""
        coverage = CellCoverage(
            threads=(thread("tc1"), thread("tc2", ratio=0.4, observed=4, hidden=6))
        )
        assert coverage.worst_ratio == 0.4

    def test_an_unmeasured_thread_is_still_mentioned_when_others_are_measured(self):
        """Silently dropping it would report the measured coverage as the whole
        story, which is the flattering direction."""
        coverage = CellCoverage(threads=(REAL_ROW, thread("tc2")))
        caveat = coverage.caveat()
        assert caveat is not None
        assert "1 further thread" in caveat
        assert "no coverage recorded" in caveat


class TestTheFigureCarriesItsDenominator:
    """Rule 7. A bare percentage is not a claim."""

    def test_the_population_is_stated_beside_the_ratio(self):
        assert REAL_ROW.population == "195 of at least 818 comments"

    def test_the_caveat_names_the_population_not_only_the_percentage(self):
        caveat = CellCoverage(threads=(REAL_ROW,)).caveat()
        assert caveat is not None
        assert "195 of at least 818 comments" in caveat

    def test_it_is_phrased_as_an_upper_bound_never_as_a_measurement(self):
        """`hidden_children_min` is a FLOOR, so the denominator is understated
        and the ratio is overstated. The wording has to lean the other way."""
        caveat = CellCoverage(threads=(REAL_ROW,)).caveat()
        assert caveat is not None
        assert "at most" in caveat
        for measured_phrasing in ("we saw 24%", "coverage of 24%", "covered 24%"):
            assert measured_phrasing not in caveat.lower()

    def test_a_thread_with_no_population_recorded_says_so(self):
        assert thread("tc1", ratio=0.5).population == "population not recorded"


class TestWhatTheCaveatSays:
    def test_full_coverage_needs_no_caveat(self):
        coverage = CellCoverage(threads=(thread("tc1", ratio=1.0, observed=10, hidden=0),))
        assert coverage.caveat() is None

    def test_no_threads_at_all_needs_no_caveat(self):
        """A cell with no claims is the gate's business, not this module's."""
        assert CellCoverage().caveat() is None

    def test_the_counts_are_described_as_of_people_we_read(self):
        """The specific misreading this module exists to prevent.

        "Four engineers report X" invites "four of the people who discussed
        it". The true statement is "four of the people we read".
        """
        caveat = CellCoverage(threads=(REAL_ROW,)).caveat()
        assert caveat is not None
        assert "people we read" in caveat
        assert "not of everyone who spoke" in caveat

    def test_good_coverage_does_not_produce_a_warning(self):
        """The caveat must mean something. If it appeared on every cell it
        would be furniture and get read as such."""
        coverage = CellCoverage(threads=(thread("tc1", ratio=0.9, observed=90, hidden=10),))
        assert coverage.caveat() is None


class TestItIsNotAGate:
    """Low coverage withholds nothing. Deleting real evidence to protect a
    number would surface as silence, and rule 4 says silence is not criticism.
    """

    def test_the_module_exposes_no_way_to_refuse_a_cell(self):
        public = {n for n in dir(CellCoverage) if not n.startswith("_")}
        for refusing in ("publishes", "blocks", "gate", "allowed", "refuse"):
            assert refusing not in public, (
                f"CellCoverage.{refusing} exists — coverage decides what is SAID, "
                f"never whether a cell may be said at all"
            )


class TestTheQuery:
    def test_it_reads_and_never_writes(self):
        class Conn:
            def __init__(self):
                self.sql = []

            def execute(self, sql, params=()):
                self.sql.append(sql)

                class R:
                    @staticmethod
                    def fetchall():
                        return [("tc:1u1b22l", 0.2383863, 195, 623)]

                return R()

        conn = Conn()
        coverage = CoverageReader(conn).for_cell(
            model_version_id="mv1",
            capability_key="tool_calling.schema_adherence",
            condition_bucket="tools:6-15",
        )

        assert len(conn.sql) == 1
        assert conn.sql[0].strip().upper().startswith("SELECT")
        assert coverage.threads[0].ratio == 0.2383863
        assert coverage.threads[0].population == "195 of at least 818 comments"


class TestItIsActuallyCalled:
    """The pattern this project has now found five times: a check with no caller.

    `assert_no_fixtures` and `assert_contract_backed` have none outside tests,
    and the root CLAUDE.md entry claiming they were wired was wrong twice
    before it was counted. A coverage caveat nothing computes is the same
    defect with a friendlier face - it would read as "coverage is handled"
    while every cell shipped without it.

    So this drives `CellStore.compute` end to end, with no database, and
    asserts the caveat arrives on the outcome.
    """

    def test_compute_populates_the_caveat_without_being_asked(self):
        from datetime import UTC, datetime

        from judge.store.cells import CellKey, CellStore

        now = datetime.now(UTC)

        class Conn:
            """Answers the claim query and the coverage query differently."""

            def __init__(self):
                self.queries = []

            def execute(self, sql, params=()):
                self.queries.append(sql)
                claim_rows = [
                    (
                        f"clm{i}",
                        f"t2_author{i}",
                        platform,
                        0.9,
                        "negative",
                        "moderate",
                        now,
                        "tools:6-15",
                    )
                    for i, platform in enumerate(("reddit", "github", "reddit", "blog"))
                ]
                coverage_rows = [("tc:1u1b22l", 0.2383863, 195, 623)]
                rows = coverage_rows if "thread_context" in sql else claim_rows

                class R:
                    @staticmethod
                    def fetchall():
                        return rows

                return R()

        outcome = CellStore(Conn()).compute(
            CellKey(
                model_version_id="mv1",
                capability_key="tool_calling.schema_adherence",
                condition_bucket="tools:6-15",
            )
        )

        assert outcome.coverage.threads, "compute() did not read coverage at all"
        caveat = outcome.coverage_caveat
        assert caveat is not None, "four claims from a thread read at 24% produced no caveat"
        assert "at most 24%" in caveat
        assert "195 of at least 818 comments" in caveat

    def test_the_caveat_does_not_change_whether_the_cell_publishes(self):
        """Coverage decides what is SAID, never whether it may be said."""
        from datetime import UTC, datetime

        from judge.store.cells import CellKey, CellStore

        now = datetime.now(UTC)

        def outcome_with(coverage_rows):
            class Conn:
                def execute(self, sql, params=()):
                    claim_rows = [
                        (f"clm{i}", f"t2_a{i}", p, 0.9, "negative", "moderate", now, "tools:6-15")
                        for i, p in enumerate(("reddit", "github", "reddit", "blog"))
                    ]
                    rows = coverage_rows if "thread_context" in sql else claim_rows

                    class R:
                        @staticmethod
                        def fetchall():
                            return rows

                    return R()

            return CellStore(Conn()).compute(
                CellKey(
                    model_version_id="mv1",
                    capability_key="tool_calling.schema_adherence",
                    condition_bucket="tools:6-15",
                )
            )

        thin = outcome_with([("tc1", 0.05, 5, 95)])
        full = outcome_with([("tc1", 1.0, 100, 0)])

        assert thin.status is full.status
        assert thin.publishes == full.publishes
        assert thin.coverage_caveat is not None
        assert full.coverage_caveat is None


class TestMarginSoftensTheWordingAndNeverRemovesIt:
    """Engineer 1's correction, and the limit of it.

    Their objection was right: "could the unread part overturn this" is the
    real question, not "did we read most of the thread", and 24% with eight
    voices beats 80% with two. So strength keys to margin over the gate.

    The limit is selection bias. Margin protects against sampling NOISE; our
    gap is a biased gap by construction, because `selection_method` is
    `specificity_x_log_engagement@observed`. Every voice counted came from the
    same ranked top slice, so more of them does not cure it.
    """

    def test_a_cell_scraping_the_gate_gets_the_strong_form(self):
        caveat = CellCoverage(threads=(REAL_ROW,)).caveat(n_eff=3.1)
        assert caveat is not None
        assert "barely more evidence" in caveat
        assert "could plausibly change this" in caveat

    def test_a_cell_with_margin_gets_the_softer_form(self):
        caveat = CellCoverage(threads=(REAL_ROW,)).caveat(n_eff=12.0)
        assert caveat is not None
        assert "more voices than the publication bar needs" in caveat
        assert "barely more evidence" not in caveat

    def test_margin_never_removes_the_caveat(self):
        """The whole point of the correction's correction."""
        caveat = CellCoverage(threads=(REAL_ROW,)).caveat(n_eff=1000.0)
        assert caveat is not None
        assert "at most 24%" in caveat

    def test_the_selection_bias_is_stated_at_every_margin(self):
        """Said in BOTH forms, because n_eff does not touch it."""
        for n_eff in (3.1, 12.0, 1000.0):
            caveat = CellCoverage(threads=(REAL_ROW,)).caveat(n_eff=n_eff)
            assert caveat is not None
            assert "not a random sample" in caveat, n_eff
            assert "ranked before selection" in caveat, n_eff

    def test_an_unknown_margin_keeps_the_strong_form(self):
        """Not knowing the margin is not a reason to sound confident."""
        caveat = CellCoverage(threads=(REAL_ROW,)).caveat(n_eff=None)
        assert caveat is not None
        assert "barely more evidence" in caveat

    def test_the_boundary_is_the_gate_rather_than_a_round_number(self):
        from judge.curate.gate import N_EFF_MINIMUM
        from judge.curate.thread_coverage import COMFORTABLE_MARGIN

        boundary = N_EFF_MINIMUM * COMFORTABLE_MARGIN
        below = CellCoverage(threads=(REAL_ROW,)).caveat(n_eff=boundary - 0.01)
        at = CellCoverage(threads=(REAL_ROW,)).caveat(n_eff=boundary)
        assert below is not None and at is not None
        assert "barely more evidence" in below
        assert "barely more evidence" not in at
