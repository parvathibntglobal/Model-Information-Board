"""The first page this lane has ever built, and the assertion it exists for.

No database. `CoveragePage` takes anything with `.execute(...)`, so the
interesting behaviour - what an empty table renders as - is testable without
Postgres, and it is the behaviour most likely to be wrong in the direction
nobody notices.
"""

from __future__ import annotations

import re

from judge.pages.coverage import KNOWN_KINDS, CoveragePage, CoverageReport, KindReport


class FakeResult:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class FakeConn:
    """Scripted responses, and it RAISES when it runs out.

    Same shape as `FakeClient` in `judge/extract/client.py`, for the same
    reason: a fake that returns a default when it runs out of script turns an
    unexpected extra query into a passing test.
    """

    def __init__(self, *responses: list[tuple]) -> None:
        self._responses = list(responses)
        self.queries: list[str] = []

    def execute(self, sql: str, params: tuple = ()) -> FakeResult:
        self.queries.append(sql)
        if not self._responses:
            raise AssertionError(f"unscripted query: {sql[:60]}")
        return FakeResult(self._responses.pop(0))


class TestTheEmptyTable:
    """The whole reason this module is written the way it is."""

    def test_no_measurement_ever_does_not_render_as_no_gaps(self):
        """An empty table must never produce a reassuring sentence.

        This is the state TODAY: `coverage_gaps()` builds the objects and
        nothing inserts them, so this is not a hypothetical edge case, it is
        what the page does on every run until the writer is wired.
        """
        report = CoveragePage(FakeConn([])).report()

        assert report.pipeline_version is None
        assert report.measured_at_all is False
        summary = report.summary.lower()
        assert "no coverage measurement has ever run" in summary
        assert "must not be read as completeness" in summary
        # The words that would make it wrong, matched on WORD BOUNDARIES.
        # A bare substring check failed this on "completeness" - the sentence
        # "must not be read as completeness" is the correct prose and contains
        # the banned word, so the assertion was rejecting the very phrasing it
        # exists to require.
        for reassuring in ("no gaps", "complete", "full coverage", "all clear"):
            assert not re.search(rf"\b{reassuring}\b", summary), (
                f"summary reads as reassurance: {reassuring!r}"
            )

    def test_every_known_kind_reports_unmeasured_rather_than_clear(self):
        report = CoveragePage(FakeConn([])).report()

        assert len(report.kinds) == len(KNOWN_KINDS)
        for kind in report.kinds:
            assert kind.measured is False
            assert "not measured" in kind.headline

    def test_each_kind_says_something_different_about_its_own_silence(self):
        """Four kinds printing one word four times is not a report on four things.

        A single shared "none" would pass any count-based assertion, so the
        assertion is on DISTINCTNESS.
        """
        report = CoveragePage(FakeConn([])).report()
        headlines = {k.headline for k in report.kinds}
        assert len(headlines) == len(report.kinds), (
            f"kinds share a silence message, so the page is not reporting on "
            f"{len(report.kinds)} things: {headlines}"
        )

    def test_a_run_that_found_nothing_is_not_four_measurements(self):
        """One writer running and finding nothing does not measure the other three."""
        report = CoverageReport(
            pipeline_version="e2.1",
            kinds=tuple(KindReport(kind=k, rows=0, subjects=0) for k in sorted(KNOWN_KINDS)),
        )
        assert report.measured_at_all is False
        assert "one measurement finding zero gaps" in report.summary


class TestFiguresCarryTheirPopulation:
    def test_the_summary_names_the_pipeline_version(self):
        """Rule 7. A gap count without the run it came from is not a claim."""
        conn = FakeConn(
            [("e2.1",)],
            [("unsourced-field", 3, 2, ["price cites no source"])],
        )
        report = CoveragePage(conn).report()

        assert report.pipeline_version == "e2.1"
        assert "e2.1" in report.summary
        assert "3 gaps" in report.summary

    def test_unmeasured_kinds_are_named_in_the_summary_not_omitted(self):
        """Reporting 3 gaps while silently dropping three unmeasured kinds is
        the under-reporting this page must not do."""
        conn = FakeConn(
            [("e2.1",)],
            [("unsourced-field", 3, 2, ["price cites no source"])],
        )
        summary = CoveragePage(conn).report().summary

        assert "1 of 4 kinds" in summary
        assert "3 were" in summary and "not measured" in summary
        assert "not the same as clear" in summary


class TestTheFifthKind:
    """The schema comment predicted this and Engineer 1's proposal adds two."""

    def test_an_unrecognised_kind_is_surfaced_rather_than_dropped(self):
        conn = FakeConn(
            [("e2.1",)],
            [
                ("unsourced-field", 1, 1, ["x"]),
                ("mention-resolves-to-route", 7, 4, ["openrouter/auto"]),
            ],
        )
        report = CoveragePage(conn).report()

        kinds = {k.kind for k in report.kinds}
        assert "mention-resolves-to-route" in kinds, (
            "a kind the CHECK permits and this module has not heard of was "
            "filtered out — the exact failure the schema comment predicted"
        )
        unrecognised = report.unrecognised
        assert len(unrecognised) == 1
        assert unrecognised[0].kind == "mention-resolves-to-route"
        assert unrecognised[0].rows == 7

    def test_its_rows_count_towards_the_total(self):
        """Surfacing it while excluding it from the count would be worse than
        dropping it: the page would name the kind and under-report the board."""
        conn = FakeConn(
            [("e2.1",)],
            [
                ("unsourced-field", 1, 1, ["x"]),
                ("mention-resolves-to-route", 7, 4, ["openrouter/auto"]),
            ],
        )
        assert "8 gaps" in CoveragePage(conn).report().summary


class TestItNeverWrites:
    def test_only_select_statements_reach_the_connection(self):
        """`collect/` owns this table. This lane's whole relationship is a SELECT."""
        conn = FakeConn([("e2.1",)], [("unsourced-field", 1, 1, ["x"])])
        CoveragePage(conn).report()

        assert conn.queries
        for sql in conn.queries:
            assert sql.strip().upper().startswith("SELECT"), sql
