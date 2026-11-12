"""Admin -> Scheduler's reading of the workflow: cron words, next firing, and
the setup it parses. No database and no network."""
from __future__ import annotations

from datetime import UTC, datetime

from judge import scheduler_status as ss


def test_a_daily_cron_reads_in_utc_and_ist():
    assert ss._cron_words("30 20 * * *") == "daily at 20:30 UTC (02:00 IST)"


def test_an_unusual_cron_is_shown_as_itself_not_guessed():
    assert ss._cron_words("0 */6 * * 1-5") == "0 */6 * * 1-5"
    assert ss.next_cron("0 */6 * * 1-5", datetime.now(UTC)) is None


def test_next_firing_is_today_or_tomorrow():
    before = datetime(2026, 10, 6, 10, 0, tzinfo=UTC)
    after = datetime(2026, 10, 6, 21, 0, tzinfo=UTC)
    assert ss.next_cron("30 20 * * *", before).startswith("2026-10-06T20:30")
    assert ss.next_cron("30 20 * * *", after).startswith("2026-10-07T20:30")


def test_the_setup_is_read_from_the_workflow_file():
    s = ss.setup()
    assert not s.get("unreadable"), s
    assert s["crons"] and s["crons"][0]["expr"]
    assert s["timeout_minutes"] and s["deadline_minutes"]
    # names only, never values
    assert all(n.isupper() for n in s["secrets"] + s["variables"])
    assert "GITHUB_TOKEN" not in s["secrets"]


# ── the switch and what each run fetched (2026-10-21) ──────────────────────


SUMMARY = "\n".join([
    "**Scheduled fetch: 2 model(s).** Counts only; no quotes, authors or hosts.",
    "",
    "| Model | Outcome | Docs appended | Threads read | Quotes verified (count) "
    "| Unreadable here | Harvest errors |",
    "|---|---|---|---|---|---|---|",
    "| Jev 1.13 | ok | 220 | 18 | 63 | 1650 | - |",
    "| GPT-6 Sol | error | - | 0 | - | - | reddit |",
    "",
    "1 of 2 ended ok.",
])


def test_a_summary_parses_and_a_dash_is_not_zero():
    from judge import scheduler_status as s

    rows = s.parse_summary(SUMMARY)
    assert [r["model"] for r in rows] == ["Jev 1.13", "GPT-6 Sol"]
    assert rows[0]["documents_appended"] == 220 and rows[0]["unreadable_here"] == 1650
    assert rows[1]["documents_appended"] is None and rows[1]["harvest_errors"] == "reddit"


def test_the_summary_carries_e6_and_an_older_one_still_parses():
    """E6's counts reach the public summary (#608 review); a summary posted
    before those columns reads them as unreported, never as zero."""
    from judge import scheduler
    from judge import scheduler_status as s

    body = scheduler.summarise_runs([scheduler.safe_record({
        "model": "Seedance 2.0", "status": "ok", "e6_rejected": 2, "e6_unvetted": 0,
        "detail": "the database is 203.0.113.5"})])
    assert "| E6 rejected | E6 unvetted |" in body and "203.0.113.5" not in body
    new_row = s.parse_summary(body)[0]
    assert new_row["e6_rejected"] == 2 and new_row["e6_unvetted"] == 0
    old_row = s.parse_summary(SUMMARY)[0]
    assert old_row["e6_rejected"] is None and old_row["e6_unvetted"] is None


def test_unreadable_here_is_one_line_per_scan_window_not_a_column():
    """2026-11-12, both runners' real shape. In a per-model column the agent night
    showed 1,323 on all six rows and read as six counts (#610 review). And the
    model night's 1,323 then 0 was not drift (#628 review): its first run was a
    first fetch, which scans every unread thread ever stored; the eleven after it
    were refreshes, which scan only the last 14 days."""
    from judge import scheduler
    from judge import scheduler_status as s

    runs = [{"model": "Gemini 4 Carbon", "status": "ok", "first_fetch": True,
             "threads_unreadable_here": 1323},
            {"model": "DeepSeek V4 Pro", "status": "ok", "first_fetch": False,
             "threads_unreadable_here": 0},
            {"model": "Claude Opus 5", "status": "ok", "first_fetch": False,
             "threads_unreadable_here": 0},
            {"model": "Claude Duet", "status": "not run: this job's time budget is spent"}]
    body = scheduler.summarise_runs([scheduler.safe_record(r) for r in runs])
    assert "Unreadable here" not in body and "| 1323 |" not in body
    days = scheduler.policy().extraction_window_days
    assert (f"{scheduler.UNREADABLE_LINE} first fetches, which scan every unread thread "
            "ever stored: 1,323 (1 run); refreshes, which scan threads with a post in "
            f"the last {days} days: 0 (2 runs). These are not any one model's") in body
    assert "0 to 1,323" not in body  # never one range across two windows
    rows = s.parse_summary(body)
    assert [r["model"] for r in rows] == ["Gemini 4 Carbon", "DeepSeek V4 Pro",
                                          "Claude Opus 5", "Claude Duet"]
    assert all("unreadable_here" not in r for r in rows)
    assert s.parse_unreadable(body, rows).startswith(scheduler.UNREADABLE_LINE + " first")


def test_a_run_with_no_window_recorded_is_said_so_and_an_unreported_figure_is_no_line():
    from judge import scheduler

    older = scheduler.summarise_runs([{"model": "A", "status": "ok",
                                       "threads_unreadable_here": 12}])
    assert f"{scheduler.UNREADABLE_LINE} window not recorded: 12 (1 run)." in older
    silent = scheduler.summarise_runs([{"model": "A", "status": "ok"}])
    assert scheduler.UNREADABLE_LINE not in silent  # never a 0 (rule 6)


def test_first_fetch_is_a_safe_field_and_detail_is_still_not():
    from judge import scheduler

    safe = scheduler.safe_record({"model": "A", "first_fetch": True, "detail": "203.0.113.5"})
    assert safe == {"model": "A", "first_fetch": True}


def test_an_older_summary_gives_its_column_figure_and_says_where_from():
    """Summaries posted before 2026-11-12 carried it per row, with no window."""
    from judge import scheduler_status as s

    rows = s.parse_summary(SUMMARY)
    said = s.parse_unreadable(SUMMARY, rows)
    assert said.startswith("Unread threads this runner could not open: 1,650, from this "
                           "older summary's per-model column")
    assert s.parse_unreadable("no table here", []) is None


def test_admin_shows_the_line_once_and_no_row_carries_it():
    from judge import scheduler_status as s

    rows = s.parse_summary(SUMMARY)
    run = {"status": "completed", "started_at": "2026-10-21T20:30:00Z", "minutes": 60}
    s.attach_summaries([run], [{"at": "2026-10-21T21:00:00Z", "url": "u", "rows": rows,
                                "unreadable": s.parse_unreadable(SUMMARY, rows)}])
    assert run["summary"]["unreadable"].startswith("Unread threads this runner could not open")
    assert all("unreadable_here" not in r for r in run["summary"]["rows"])


def test_the_media_line_counts_media_kinds_only():
    """`decision` keeps the text arms and `agent` has its own run: neither is media
    (#618/#620 review). An image run is."""
    from judge import scheduler

    runs = [{"model": "Jev 1.13", "status": "ok", "model_kind": "decision", "threads_read": 4},
            {"model": "Claude Code", "status": "ok", "model_kind": "agent", "threads_read": 6},
            {"model": "GPT Image 2.6", "status": "ok", "model_kind": "image", "threads_read": 3},
            {"model": "GPT-6 Sol", "status": "ok", "model_kind": "text", "threads_read": 9}]
    body = scheduler.summarise_runs([scheduler.safe_record(r) for r in runs])
    assert "Media models: 1 of 4 run(s), 3 of 22 thread(s) read." in body
    only_agents = scheduler.summarise_runs([scheduler.safe_record(runs[1])])
    assert "Media models" not in only_agents


def test_the_summary_media_kinds_follow_the_fetch_media_kinds():
    """Every fetch media kind but `agent` (a search path, not a model kind) is
    counted as media in the summary - a new one cannot go uncounted silently."""
    import importlib.util
    from pathlib import Path

    from judge import scheduler

    spec = importlib.util.spec_from_file_location(
        "fetch_model_kinds", Path(__file__).resolve().parents[1] / "scripts" / "fetch_model.py")
    fetch_model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch_model)
    assert fetch_model.MEDIA_KINDS - {"agent"} == scheduler.MEDIA_SUMMARY_KINDS


def test_a_run_gets_the_summary_posted_while_it_ran_and_none_otherwise():
    from judge import scheduler_status as s

    runs = [
        {"status": "completed", "started_at": "2026-10-21T11:03:28Z", "minutes": 36.7},
        {"status": "completed", "started_at": "2026-10-20T23:14:44Z", "minutes": 0.1},
        {"status": "in_progress", "started_at": "2026-10-21T20:30:00Z", "minutes": None},
    ]
    posted = [{"at": "2026-10-21T11:40:08Z", "url": "u", "rows": s.parse_summary(SUMMARY)}]
    s.attach_summaries(runs, posted)
    assert runs[0]["summary"]["models"] == 2 and runs[0]["summary"]["ok"] == 1
    assert runs[0]["summary"]["documents_appended"] == 220
    assert runs[1]["summary"] is None            # finished, nothing posted
    assert "summary" not in runs[2]              # still running: not judged


def test_an_unreadable_switch_is_never_off(monkeypatch):
    from judge import scheduler_status as s

    monkeypatch.setattr(s, "_gh", lambda path: (403, {"message": "forbidden"}))
    out = s.switch("o/r")
    assert "state" not in out and "unreadable" in out


def test_the_next_due_is_the_cadence_after_the_last_success():
    from datetime import UTC, datetime, timedelta

    from judge import scheduler_status as s

    last = datetime(2026, 10, 21, 11, 40, tzinfo=UTC)
    assert s._next_due(last, timedelta(hours=60)) == "2026-10-23T23:40:00+00:00"
    taken_by = s.first_firing_after("30 20 * * *", last + timedelta(hours=60))
    assert taken_by == "2026-10-24T20:30:00+00:00"
    assert s._next_due(None, timedelta(hours=60)) is None
