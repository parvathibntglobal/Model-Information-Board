"""Kite Pulse outreach: the Finder -> kp_outreach_thread writer. No database.

The SQL's conflict rule is checked as text; the counting and the reporting are
checked against a fake connection that behaves like ON CONFLICT DO NOTHING.
"""

from __future__ import annotations

import contextlib
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

OUTREACH = Path(__file__).resolve().parent.parent / "web" / "src" / "kitepulse" / "outreach"
if str(OUTREACH) not in sys.path:
    sys.path.insert(0, str(OUTREACH))

from common import db, store  # noqa: E402
from common import thread as t  # noqa: E402

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def thread(ext_id, *, status=t.STATUS_FOUND, reason=None):
    th = t.Thread(source="hackernews", ext_id=ext_id, kind="story", community="hackernews",
                  url=f"https://news.ycombinator.com/item?id={ext_id}", root_id=None,
                  title="Hit my Claude usage limit", body=None, author="a",
                  created_at=NOW, fetched_at=NOW, matched_problems=["claude-limits"],
                  matched_phrases=["usage limit"], flags=["community_pending_review"])
    if status == t.STATUS_DROPPED:
        th.drop(reason)
    return th


class FakeConn:
    """Keeps (source, ext_id) like the table's unique key: a second insert of
    the same key returns no row, as ON CONFLICT DO NOTHING RETURNING does."""

    class info:
        dbname = "kite_pulse_outreach_local"

    def __init__(self, present=()):
        self.keys = set(present)
        self.rows: list[dict] = []
        self.transactions = 0

    @contextlib.contextmanager
    def transaction(self):
        self.transactions += 1
        yield

    def execute(self, sql, row):
        assert "ON CONFLICT (source, ext_id) DO NOTHING" in sql
        key = (row["source"], row["ext_id"])
        new = key not in self.keys
        if new:
            self.keys.add(key)
            self.rows.append(row)

        class _R:
            def fetchone(_self):
                return (len(self.rows),) if new else None
        return _R()


def test_new_threads_are_inserted_and_known_ones_left_alone():
    conn = FakeConn(present={("hackernews", "1")})
    saved = store.save(conn, [thread("1"), thread("2"), thread("3", status=t.STATUS_DROPPED,
                                                                reason=t.TOO_OLD)])
    assert (saved.inserted, saved.already_present) == (2, 1)
    assert conn.transactions == 1
    assert [r["ext_id"] for r in conn.rows] == ["2", "3"]
    dropped = conn.rows[1]
    assert (dropped["status"], dropped["drop_reason"]) == ("dropped", "too_old")


def test_every_column_of_the_row_comes_from_the_record():
    row = store._row(thread("9"))
    assert set(row) == set(t.Thread.__dataclass_fields__)
    assert all(f"%({k})s" in store.INSERT for k in row)
    assert row["matched_problems"] == ["claude-limits"] and row["created_at"] == NOW


def test_the_insert_never_updates_an_existing_row():
    sql = store.INSERT.upper()
    assert "ON CONFLICT (SOURCE, EXT_ID) DO NOTHING" in sql and "UPDATE" not in sql


# --- what a run prints and returns ---------------------------------------------

def test_a_phrase_run_or_no_db_skips_the_write_and_says_so(capsys):
    assert store.skip_reason(no_db=False, phrase=None) is None
    assert store.skip_reason(no_db=True, phrase=None) == "--no-db"
    reason = store.skip_reason(no_db=False, phrase="usage limit")
    assert "review queue" in reason
    assert store.save_and_report([thread("1")], skip_reason=reason) is True
    assert "Database: NOT written" in capsys.readouterr().out


def test_a_failed_write_is_reported_and_fails_the_run(monkeypatch, capsys):
    def refuse(*_a, **_k):
        raise db.OutreachDbError("KP_OUTREACH_DATABASE_URL is not set")
    monkeypatch.setattr(db, "connect", refuse)
    assert store.save_and_report([thread("1")], skip_reason=None) is False
    out = capsys.readouterr().out
    assert "Database: FAILED" in out and "JSONL only" in out


@pytest.mark.parametrize("folder", ["hackernews", "discourse", "devto", "github", "reddit"])
def test_every_finder_writes_through_the_store_and_fails_when_it_does(folder):
    src = (OUTREACH / folder / "find.py").read_text(encoding="utf-8")
    assert "store.save_and_report(result.threads" in src
    assert '"--no-db"' in src
    assert "not saved" in src or "if saved else 1" in src
