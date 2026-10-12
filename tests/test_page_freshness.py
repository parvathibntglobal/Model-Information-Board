"""Page freshness: when the board last changed, and how new its evidence is.

Pinned here:
- the two dates stay two (added vs written), overall and per model;
- the population is the board's own: declined entries out, and the public
  view's withheld sources out, so no date describes evidence a page hides;
- a model with no entry gets no dates (rule 6), not a placeholder;
- the route exists, and the pages render the line.
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime

from judge.app import app
from judge.freshness import board_freshness

WEB = pathlib.Path(__file__).resolve().parents[1] / "web" / "src"

ADDED = datetime(2026, 10, 6, 7, 35, tzinfo=UTC)
WRITTEN = datetime(2026, 10, 5, 9, 30, tzinfo=UTC)


class FakeConn:
    """Answers the three queries in order and keeps the SQL it was sent."""

    def __init__(self, overall, per_model, canonical):
        self.answers = [overall, per_model, canonical]
        self.sql: list[str] = []

    def execute(self, sql, params=None):
        self.sql.append(sql)
        answer = self.answers.pop(0)

        class _R:
            def fetchone(self):
                return answer

            def fetchall(self):
                return answer

        return _R()


def run(**kw):
    conn = FakeConn(
        overall=kw.get("overall", (ADDED, WRITTEN, 3)),
        per_model=kw.get("per_model", [("mv_1", ADDED, WRITTEN)]),
        canonical=kw.get("canonical", [("mv_1", "anthropic/claude-opus-4.6")]),
    )
    return board_freshness(conn), conn


class TestTwoDatesNotOne:
    def test_overall_carries_both_dates(self):
        f, _ = run()
        assert f["updated_at"] == ADDED.isoformat()
        assert f["newest_report_at"] == WRITTEN.isoformat()
        assert f["entries"] == 3

    def test_each_model_is_findable_by_either_id(self):
        f, _ = run()
        assert f["models"]["mv_1"] == f["models"]["anthropic/claude-opus-4.6"]
        assert f["models"]["mv_1"]["newest_report_at"] == WRITTEN.isoformat()


class TestTheSamePopulationAsTheBoard:
    def test_declined_entries_are_excluded(self):
        _, conn = run()
        assert all("ruling IS DISTINCT FROM 'declined'" in s for s in conn.sql[:2])

    def test_the_public_withholding_clause_is_applied(self):
        """Without it a public page could say "newest report written" about a
        withheld Reddit post it does not show."""
        _, conn = run()
        assert all("pub_d.source" in s for s in conn.sql[:2])


class TestAbsentIsNotADate:
    def test_an_empty_board_has_no_dates_rather_than_a_placeholder(self):
        f, _ = run(overall=(None, None, 0), per_model=[], canonical=[])
        assert f["updated_at"] is None and f["newest_report_at"] is None
        assert f["models"] == {}


def test_the_route_exists():
    assert "/freshness" in {getattr(r, "path", "") for r in app.routes}


def test_the_pages_render_the_line():
    for page in ("Models.jsx", "ModelDetail.jsx", "Compare.jsx"):
        assert "<Freshness" in (WEB / "routes" / page).read_text(encoding="utf-8"), page
    assert "freshLine()" in (WEB / "board" / "views.js").read_text(encoding="utf-8")
