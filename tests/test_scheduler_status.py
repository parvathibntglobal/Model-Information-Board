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
