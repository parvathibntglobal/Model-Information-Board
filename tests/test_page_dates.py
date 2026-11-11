"""Dates on pages (2026-11-11): one clock, calendar days, live figures.

- Every page date is a UTC calendar date, and "today" is a calendar day, not
  "within 24 hours" (web/src/dates.js).
- The landing's report figures are read live from `/reports`, not fixed "as
  of 12 Oct" (web/src/components/reportPicks.js).
- The benchmarks "Updated" date is the last run that changed the table.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

import psycopg
import pytest

from tests.conftest import assert_disposable, assert_safe_target

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def js():
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is required to run web/src/dates.js and reportPicks.js")
    run = subprocess.run([node, str(ROOT / "tests" / "js" / "page_dates.mjs")],
                         capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if run.returncode:
        pytest.fail(f"page_dates.mjs failed:\n{run.stderr}")
    return json.loads(run.stdout)


# ── one clock ────────────────────────────────────────────────────────────────

def test_yesterday_late_is_one_day_ago_not_today(js):
    """A fetch at 23:00 UTC on 9 Nov, read at 19:00 UTC on 10 Nov, is 20 hours
    old. It used to read "today (2026-11-09)"."""
    assert js["late_yesterday"] == "1 day ago"
    assert js["earlier_today"] == "today"
    assert js["eight_days"] == "8 days ago"
    assert js["unreadable"] is None


def test_dates_are_utc_calendar_dates(js):
    """23:30 UTC on 9 Nov is 9 Nov for every reader, never 10 Nov."""
    assert "9" in js["utc_day"] and "10" not in js["utc_day"]
    assert js["no_day"] is None


def test_hours_are_whole_never_rounded_up(js):
    assert js["h23_30"] == "23 h ago"
    assert js["m59"] == "59 min ago"
    assert js["past_a_day"] is None


def test_every_formatter_that_showed_a_local_date_now_says_utc():
    for rel in ("web/src/components/Freshness.jsx", "web/src/board/views.js"):
        assert "fmtDayUtc" in (ROOT / rel).read_text(encoding="utf-8"), rel
    updates = (ROOT / "web/src/routes/AiUpdates.jsx").read_text(encoding="utf-8")
    assert "year: 'numeric', timeZone: 'UTC'" in updates


# ── live report figures ──────────────────────────────────────────────────────

def test_the_picker_shows_the_top_three_for_coding_agents_live(js):
    picks = js["picks"]
    assert [p["name"] for p in picks] == ["Model B", "Model A", "Model C"]
    assert picks[0] == {"name": "Model B", "by": "Beta", "people": 12, "pos": 10, "neg": 1}
    assert js["picks_no_job"] == []


def test_the_examples_are_one_of_each_kind_live(js):
    ex = {e["label"]: e for e in js["examples"]}
    assert set(ex) == {"Working", "Disputed", "Problems"}
    assert ex["Working"]["model"] == "Model B"   # most people among working, all three bars
    assert ex["Disputed"]["model"] == "Model D"
    assert ex["Problems"]["model"] == "Model E"  # a metric row is never an example
    assert len({e["model"] for e in js["examples"]}) == 3


def test_no_hard_coded_as_of_date_is_left():
    for rel in ("web/src/components/ToolsShowcase.jsx", "web/src/components/ReportExamples.jsx"):
        assert "as of 12 Oct" not in (ROOT / rel).read_text(encoding="utf-8"), rel


# ── the database side ────────────────────────────────────────────────────────

@pytest.fixture
def conn(test_dsn):
    from collect.db import apply_schema

    assert_safe_target(test_dsn)
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        assert_disposable(c, test_dsn)
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        apply_schema(c)
        c.commit()
        yield c


def _bench_run(conn, status, finished):
    conn.execute(
        "INSERT INTO bench_run (trigger, scope, status, finished_at) VALUES "
        "('manual_run', 'all', %s, %s)", (status, finished))


def test_benchmarks_updated_skips_failed_and_running_runs(conn):
    from judge.benchmarks import _last_update

    assert _last_update(conn) is None
    _bench_run(conn, "ok", "2026-10-28T01:40:00Z")
    _bench_run(conn, "partial", "2026-11-01T01:40:00Z")
    _bench_run(conn, "error", "2026-11-09T01:40:00Z")
    _bench_run(conn, "running", None)
    assert _last_update(conn).startswith("2026-11-01")

