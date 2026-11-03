"""Admin's view of the two public sections (judge/sections_status.py): the
Scheduler's Benchmarks and AI updates feeds tabs, and the Board & content
status of /ai-benchmarks and /ai-news-headlines. Read-only throughout."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from psycopg import errors

from judge import benchmarks, scheduler_status, sections_status, updates

MONDAY = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)


def test_cron_words_name_the_days_and_both_clocks():
    assert sections_status.cron_words("30 1 * * 2,5") == "Tue, Fri at 01:30 UTC (07:00 IST)"
    assert sections_status.cron_words("23 5 * * *") == "daily at 05:23 UTC (10:53 IST)"
    # A shape it does not know is shown as written, never guessed at.
    assert sections_status.cron_words("17 */6 * * *") == "17 */6 * * *"


def test_next_firing_follows_the_weekdays_and_takes_the_soonest_cron():
    assert sections_status.next_firing(["30 1 * * 2,5"], MONDAY) == "2026-11-03T01:30:00+00:00"
    # Friday after Tuesday's slot has passed.
    tuesday_late = datetime(2026, 11, 3, 2, 0, tzinfo=UTC)
    assert (
        sections_status.next_firing(["30 1 * * 2,5"], tuesday_late) == "2026-11-06T01:30:00+00:00"
    )
    assert (
        sections_status.next_firing(["23 5 * * *", "23 17 * * *"], MONDAY)
        == "2026-11-02T17:23:00+00:00"
    )
    assert sections_status.next_firing(["30 1 * * 0"], MONDAY) == "2026-11-08T01:30:00+00:00"
    assert sections_status.next_firing(["17 */6 * * *"], MONDAY) is None


def test_the_real_workflow_files_are_read_for_each_feed():
    for feed in sections_status.FEEDS:
        s = sections_status.workflow_setup(feed["file"])
        assert "unreadable" not in s, s
        assert s["crons"], f"{feed['file']} has no schedule"
        assert s["manual_run"] is True
    bench = sections_status.workflow_setup("benchmarks.yml")
    assert [c["words"] for c in bench["crons"]] == ["Tue, Fri at 01:30 UTC (07:00 IST)"]


def test_the_benchmarks_switch_is_the_one_its_workflow_obeys():
    """The variable named here must be the one benchmarks.yml gates on, or the
    tab would show a switch that controls nothing."""
    text = (scheduler_status.ROOT / ".github" / "workflows" / "benchmarks.yml").read_text(
        encoding="utf-8"
    )
    feed = next(f for f in sections_status.FEEDS if f["key"] == "benchmarks")
    assert f"vars.{feed['variable']}" in text


def test_a_missing_workflow_file_is_said_not_raised():
    assert "unreadable" in sections_status.workflow_setup("no-such-workflow.yml")


def test_schedules_reads_each_workflows_own_runs_and_switch(monkeypatch):
    asked = []
    monkeypatch.setattr(scheduler_status, "repo_slug", lambda: "o/r")
    monkeypatch.setattr(
        scheduler_status,
        "runs",
        lambda slug, limit=15, *, workflow_file: asked.append(workflow_file) or {"runs": []},
    )
    monkeypatch.setattr(
        scheduler_status,
        "switch",
        lambda slug, *, variable: {"state": "off", "value": "0", "v": variable},
    )
    monkeypatch.setattr(sections_status, "_bench_runs", lambda limit: {"runs": []})
    out = sections_status.schedules(MONDAY)
    by = {f["key"]: f for f in out["feeds"]}
    assert asked == ["benchmarks.yml", "registry-poll.yml"]
    assert by["benchmarks"]["switch"]["v"] == "BENCHMARKS_SCHEDULE_ENABLED"
    # The registry poll has no switch, and none is invented for it.
    assert "switch" not in by["registry-poll"]
    assert by["benchmarks"]["next_run"] == "2026-11-03T01:30:00+00:00"
    assert by["benchmarks"]["link"].endswith("/actions/workflows/benchmarks.yml")
    assert "bench_runs" in by["benchmarks"] and "bench_runs" not in by["registry-poll"]


def test_without_a_repository_each_feed_says_so(monkeypatch):
    monkeypatch.setattr(scheduler_status, "repo_slug", lambda: None)
    monkeypatch.setattr(sections_status, "_bench_runs", lambda limit: {"runs": []})
    by = {f["key"]: f for f in sections_status.schedules(MONDAY)["feeds"]}
    assert "GITHUB_REPOSITORY" in by["benchmarks"]["github"]["unreadable"]
    assert by["benchmarks"]["switch"] == {"unreadable": "no repository known"}


def test_bench_runs_count_only_blocked_and_failed_sources(monkeypatch):
    class _C:
        def __enter__(self):
            return object()

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(benchmarks, "connection", lambda: _C())
    monkeypatch.setattr(
        benchmarks,
        "runs",
        lambda conn, limit: {
            "runs": [
                {
                    "id": 7,
                    "trigger": "scheduled",
                    "status": "partial",
                    "dry_run": False,
                    "started_at": "a",
                    "finished_at": "b",
                    "totals": {"cells": 3},
                    "sources": {
                        "x": {"status": "OK"},
                        "y": {"status": "FAIL"},
                        "z": {"status": "SKIP"},
                        "w": {"status": "BLOCK"},
                    },
                    "error": None,
                    "request_id": None,
                    "scope": None,
                }
            ]
        },
    )
    got = sections_status._bench_runs(5)["runs"][0]
    assert got["sources_failed"] == ["w", "y"]
    assert got["sources_read"] == 4


def test_bench_runs_unreadable_is_said(monkeypatch):
    def boom():
        raise benchmarks.BenchmarksUnavailable("no")

    monkeypatch.setattr(benchmarks, "connection", boom)
    assert sections_status._bench_runs(5) == {"runs": [], "unreadable": "BenchmarksUnavailable"}


# ── the two public pages ───────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _no_kept_copies(monkeypatch):
    monkeypatch.setattr(benchmarks, "_charts_kept", None)
    updates.clear_published_cache()
    yield
    updates.clear_published_cache()


def test_benchmarks_page_before_any_build_is_not_built_from_here(monkeypatch):
    called = []
    monkeypatch.setattr(benchmarks, "charts", lambda *a, **k: called.append(1))
    b = sections_status._benchmarks_page()
    assert b["kept"] is None and not called
    assert b["recheck_seconds"] == benchmarks.charts_recheck_seconds()


def test_benchmarks_page_reports_the_kept_copy(monkeypatch):
    built = {
        "models": [{"tracked": True}, {"tracked": False}],
        "benchmarks_listed": 21,
        "withheld_for_review": 2,
        "last_run": {"finished_at": "t", "status": "ok"},
    }
    monkeypatch.setattr(
        benchmarks, "_charts_kept", benchmarks._Kept((benchmarks.database_url(),), built, 0.0)
    )
    k = sections_status._benchmarks_page()["kept"]
    assert (k["models"], k["tracked_models"], k["benchmarks_listed"], k["withheld_for_review"]) == (
        2,
        1,
        21,
        2,
    )


def test_a_copy_kept_for_another_database_is_not_reported(monkeypatch):
    # benchmarks' own reader decides (#596 review): Admin no longer reads the key.
    monkeypatch.setattr(
        benchmarks,
        "_charts_kept",
        benchmarks._Kept(("postgresql://elsewhere/x",), {"models": []}, 0.0),
    )
    assert benchmarks.charts_kept_state() is None
    assert sections_status._benchmarks_page()["kept"] is None


def test_the_kept_charts_state_says_how_long_ago_the_table_was_checked(monkeypatch):
    built = {"models": []}
    monkeypatch.setattr(
        benchmarks, "_charts_kept", benchmarks._Kept((benchmarks.database_url(),), built, 100.0)
    )
    assert benchmarks.charts_kept_state(now=130.4) == (built, 30)


class _Conn:
    def __init__(self, rows=None, missing=False):
        self.rows, self.missing, self.rolled = rows or [], missing, False

    def execute(self, sql, *a):
        if self.missing:
            raise errors.UndefinedTable("update_review")
        return self

    def fetchall(self):
        return self.rows

    def rollback(self):
        self.rolled = True


def test_updates_page_counts_decisions_by_kind_and_sends_the_contract_timing():
    conn = _Conn(
        [
            ("launch", "approved", 4, 2),
            ("launch", "declined", 1, 0),
            ("price_cut", "approved", 3, 1),
        ]
    )
    u = sections_status._updates_page(conn)
    assert u["decisions"]["launch"] == {"approved": 4, "declined": 1, "pending": 0, "on_home": 2}
    assert u["decisions"]["price_cut"]["approved"] == 3
    r = updates.rules()
    assert u["timing"]["home_cache_seconds"] == r["home_cache_seconds"]
    assert u["timing"]["cold_wait_seconds"] == r["cold_wait_seconds"]
    assert u["public_kept"] is None


def test_without_the_review_tables_no_decision_is_counted_as_zero():
    conn = _Conn(missing=True)
    u = sections_status._updates_page(conn)
    assert u["decisions"] is None and conn.rolled


def test_one_section_failing_leaves_the_other(monkeypatch):
    def boom():
        raise RuntimeError("x")

    monkeypatch.setattr(sections_status, "_benchmarks_page", boom)
    out = sections_status.sections(_Conn())
    assert out["benchmarks"] == {"unreadable": "RuntimeError"}
    assert "decisions" in out["updates"]
