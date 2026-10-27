"""Spend the shared table missed during a run is sent at its end (2026-10-26).

Measured that day: a feed run from a laptop made 92 paid calls and the shared
`spend_ledger` got 35. Every call was in the local file; the table - which
every machine's daily cap reads - was short, because Railway's proxy often
takes longer than the 2-second per-call connect and each miss pauses the
mirror for 30 seconds. These pin the repair: the missed calls are kept, one
patient attempt at the end sends them, and what still cannot be sent is said.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest

from judge import spend_ledger

DEAD = "postgresql://nobody@127.0.0.1:1/none"


def _call(model="deepseek/deepseek-v4-flash") -> spend_ledger.Call:
    return spend_ledger.Call(
        at=datetime(2026, 10, 26, 9, 0, tzinfo=UTC), stage="feed", model=model,
        input_tokens=100, output_tokens=10, usd=0.0005, unmetered=False, machine="host-a")


class _FakeConn:
    def __init__(self, sink):
        self.sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def cursor(self):
        sink = self.sink

        class _Cur:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def executemany(self, sql, rows):
                sink.extend(rows)

        return _Cur()

    def close(self):
        pass


@pytest.fixture
def fresh(monkeypatch):
    monkeypatch.setenv("MODELBOARD_ALLOW_TEST_TELEMETRY", "1")
    spend_ledger.reset_telemetry_backoff()
    monkeypatch.setattr(spend_ledger, "_unmirrored_rows", 0)
    monkeypatch.setattr(spend_ledger, "_unmirrored_calls", [])
    yield
    spend_ledger.reset_telemetry_backoff()


def test_a_missed_call_is_kept_and_the_flush_sends_it(fresh, monkeypatch):
    spend_ledger.append_to_database([_call(), _call(model="m2")], dsn=DEAD)
    spend_ledger.append_to_database([_call(model="m3")], dsn=DEAD)  # during the pause
    assert spend_ledger.unmirrored_count() == 3

    sent: list = []
    timeouts: list = []

    def connect(dsn, *, timeout=spend_ledger.TELEMETRY_CONNECT_TIMEOUT):
        timeouts.append(timeout)
        return _FakeConn(sent), spend_ledger.MIRROR_WRITTEN, None

    monkeypatch.setattr(spend_ledger, "_telemetry_connect", connect)
    result = spend_ledger.flush_unmirrored()
    assert (result.status, result.written) == (spend_ledger.MIRROR_WRITTEN, 3)
    assert [row[3] for row in sent] == ["deepseek/deepseek-v4-flash", "m2", "m3"]
    assert timeouts == [spend_ledger.FLUSH_CONNECT_TIMEOUT], "patient, not the per-call 2s"
    assert spend_ledger.unmirrored_count() == 0
    assert spend_ledger.flush_unmirrored().status == spend_ledger.MIRROR_NOTHING_TO_SEND


def test_what_the_flush_cannot_send_stays_pending_and_counted(fresh):
    spend_ledger.append_to_database([_call()], dsn=DEAD)
    result = spend_ledger.flush_unmirrored(dsn=DEAD)
    assert result.written == 0 and result.status == spend_ledger.MIRROR_FAILED
    assert spend_ledger.unmirrored_count() == 1, "never read as sent"


def test_the_flush_never_raises(fresh, monkeypatch):
    spend_ledger.append_to_database([_call()], dsn=DEAD)

    class _Broken(_FakeConn):
        def cursor(self):
            raise RuntimeError("insert failed")

    monkeypatch.setattr(spend_ledger, "_telemetry_connect",
                        lambda dsn, timeout=0: (_Broken([]), spend_ledger.MIRROR_WRITTEN, None))
    result = spend_ledger.flush_unmirrored()
    assert result.status == spend_ledger.MIRROR_FAILED and spend_ledger.unmirrored_count() == 1


def test_the_feed_script_says_so_and_exits_1_when_rows_are_left(monkeypatch, capsys):
    import scripts.build_evidence_feed as feed

    monkeypatch.setattr(spend_ledger, "flush_unmirrored",
                        lambda dsn=None: spend_ledger.Mirrored(
                            spend_ledger.MIRROR_FAILED, 4, 0, "timeout"))
    monkeypatch.setattr(spend_ledger, "unmirrored_count", lambda: 4)
    assert feed._flush_spend() == 1
    err = capsys.readouterr().err
    assert "4 call(s) are NOT in the shared ledger" in err and "backfill_telemetry.py" in err


def test_both_paid_scripts_flush_at_the_end():
    import scripts.build_evidence_feed as feed
    import scripts.fetch_model as fm

    assert "return _flush_spend() if args.apply else 0" in inspect.getsource(feed.main)
    assert "spend_ledger.flush_unmirrored()" in inspect.getsource(fm)


def test_a_hand_run_id_carries_no_slash():
    """`fetch_model.py deepseek/deepseek-v4-flash` named its log file through a
    directory nobody created, and died before starting (2026-10-26)."""
    import scripts.fetch_model as fm

    assert ".replace('/', '_')" in inspect.getsource(fm.main)
