"""#393: a spend row that does not reach the shared table says so.

`append_to_database` had three silent `return 0` paths and the connection
helper a fourth (the 30s backoff). On 2026-09-21, 61 of one run's 203 file rows
(one machine, e5.5 run 1) never reached `spend_ledger` and nothing in the log said
so - and every other machine's cap reads the table. These pin the split:

    not configured / test guard / nothing to send   not a loss, not counted
    connect failed / insert failed / backing off    counted and logged

and that none of it ever raises, because `record()` runs inside
`OpenRouterClient.complete()`'s `finally`.
"""

from __future__ import annotations

import logging
import pathlib
from datetime import UTC, datetime

import psycopg
import pytest

from judge import spend_ledger

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"
DEAD = "postgresql://nobody@127.0.0.1:1/none"


def _call(**kw) -> spend_ledger.Call:
    base = dict(
        at=datetime(2026, 10, 12, 10, 0, tzinfo=UTC),
        stage="extract",
        model="deepseek/deepseek-v4-flash",
        input_tokens=100,
        output_tokens=10,
        usd=0.001,
        unmetered=False,
        machine="host-a",
    )
    base.update(kw)
    return spend_ledger.Call(**base)


@pytest.fixture
def opted_in(monkeypatch):
    """Past the pytest guard and the conftest backoff, counter at zero."""
    monkeypatch.setenv("MODELBOARD_ALLOW_TEST_TELEMETRY", "1")
    spend_ledger.reset_telemetry_backoff()
    monkeypatch.setattr(spend_ledger, "_unmirrored_rows", 0)
    yield
    spend_ledger.reset_telemetry_backoff()


class TestADeadTableIsCountedAndLogged:
    def test_a_failed_connect_is_failed_not_zero(self, opted_in, caplog):
        with caplog.at_level(logging.WARNING, logger="judge.spend_ledger"):
            result = spend_ledger.append_to_database([_call(), _call(model="m2")], dsn=DEAD)
        assert result.status == spend_ledger.MIRROR_FAILED
        assert result.unmirrored == 2
        assert result.reason and "connection" in result.reason.lower()
        assert spend_ledger.unmirrored_count() == 2
        errors = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert errors, "a configured table that did not get its rows must be logged"
        assert "backfill_telemetry.py" in errors[0].getMessage()
        # The DSN never reaches a log line.
        assert "nobody@" not in caplog.text

    def test_rows_skipped_during_the_backoff_are_counted_too(self, opted_in, caplog):
        # THE SILENT 30 SECONDS. One failure backs the mirror off, and every
        # row recorded in that window used to vanish without a word.
        spend_ledger.append_to_database([_call()], dsn=DEAD)
        with caplog.at_level(logging.WARNING, logger="judge.spend_ledger"):
            result = spend_ledger.append_to_database([_call(model="m2")], dsn=DEAD)
        assert result.status == spend_ledger.MIRROR_BACKING_OFF
        assert result.unmirrored == 1
        first = spend_ledger._unreachable_reason
        assert first and first in (result.reason or ""), "says WHY it backed off"
        assert spend_ledger.unmirrored_count() == 2
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_record_still_writes_the_file_and_does_not_raise(
        self, opted_in, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("DATABASE_URL", DEAD)
        ledger = tmp_path / "spend.jsonl"
        spend_ledger.record(stage="extract", model="deepseek/deepseek-v4-flash",
                            input_tokens=10, output_tokens=2, path=ledger)
        assert ledger.read_text(encoding="utf-8").strip()
        assert spend_ledger.unmirrored_count() == 1

    def test_an_unexpected_error_is_still_swallowed(self, opted_in, monkeypatch):
        def boom(_dsn):
            raise RuntimeError("not a database error at all")
        monkeypatch.setattr(spend_ledger, "_telemetry_connect", boom)
        result = spend_ledger.append_to_database([_call()], dsn=DEAD)
        assert result.status == spend_ledger.MIRROR_FAILED


class TestNotAskedIsNotALoss:
    def test_no_dsn_is_not_configured(self, opted_in, monkeypatch, caplog):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with caplog.at_level(logging.WARNING, logger="judge.spend_ledger"):
            result = spend_ledger.append_to_database([_call()])
        assert result.status == spend_ledger.MIRROR_NOT_CONFIGURED
        assert result.unmirrored == 0
        assert spend_ledger.unmirrored_count() == 0
        assert not caplog.records

    def test_the_test_guard_is_its_own_answer(self, monkeypatch):
        monkeypatch.delenv("MODELBOARD_ALLOW_TEST_TELEMETRY", raising=False)
        monkeypatch.setattr(spend_ledger, "_unmirrored_rows", 0)
        result = spend_ledger.append_to_database([_call()], dsn=DEAD)
        assert result.status == spend_ledger.MIRROR_TEST_GUARD
        assert spend_ledger.unmirrored_count() == 0

    def test_nothing_to_send(self, opted_in):
        assert spend_ledger.append_to_database([]).status == (
            spend_ledger.MIRROR_NOTHING_TO_SEND
        )


class TestTheSuccessControl:
    """The same path against a real (disposable) table: written, not counted."""

    @pytest.fixture
    def dsn(self, test_dsn):
        with psycopg.connect(test_dsn, connect_timeout=10) as conn:
            conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
            conn.execute("CREATE SCHEMA public")
            conn.execute(SCHEMA.read_text(encoding="utf-8"))
            conn.commit()
        return test_dsn

    def test_a_reachable_table_gets_the_rows(self, opted_in, dsn):
        result = spend_ledger.append_to_database([_call(), _call(model="m2")], dsn=dsn)
        assert result.status == spend_ledger.MIRROR_WRITTEN
        assert (result.sent, result.written, result.unmirrored) == (2, 2, 0)
        assert spend_ledger.unmirrored_count() == 0
        with psycopg.connect(dsn) as conn:
            assert conn.execute("select count(*) from spend_ledger").fetchone()[0] == 2


class TestTheFileIsReconciledAgainstTheTable:
    def _ledger(self, tmp_path, *calls):
        path = tmp_path / "spend.jsonl"
        path.write_text("".join(c.as_row() + "\n" for c in calls), encoding="utf-8")
        return path

    def test_the_report_counts_file_rows_the_table_lacks(self, monkeypatch, tmp_path):
        a, b, c = _call(), _call(model="m2"), _call(model="m3")
        path = self._ledger(tmp_path, a, b, c)
        monkeypatch.setattr(spend_ledger, "read_database", lambda dsn=None: [a])
        report = spend_ledger.report(daily_cap_usd=1.0, estimated_call_usd=0.001,
                                     path=path, now=datetime(2026, 10, 12, 12, tzinfo=UTC))
        assert (report.unmirrored_rows, report.local_rows) == (2, 3)
        # The union already holds them, so this report is NOT short by them.
        assert report.calls_today == 3

    def test_an_unreadable_table_is_unknown_not_zero(self, monkeypatch, tmp_path):
        path = self._ledger(tmp_path, _call())
        monkeypatch.setattr(spend_ledger, "read_database", lambda dsn=None: None)
        report = spend_ledger.report(daily_cap_usd=1.0, estimated_call_usd=0.001, path=path)
        assert report.unmirrored_rows is None
        assert report.local_rows == 1

    def test_the_endpoint_carries_it_with_its_denominator(self, monkeypatch, tmp_path):
        from fastapi.testclient import TestClient

        from judge.app import app

        a, b = _call(), _call(model="m2")
        monkeypatch.setenv(spend_ledger.LEDGER_PATH_ENV,
                           str(self._ledger(tmp_path, a, b)))
        monkeypatch.setattr(spend_ledger, "read_database", lambda dsn=None: [a])
        basis = TestClient(app).get("/admin/usage").json()["basis"]
        assert (basis["unmirrored_rows"], basis["local_rows"]) == (1, 2)


def test_the_panel_renders_it():
    src = (pathlib.Path(__file__).resolve().parents[1] / "web" / "src" / "components"
           / "UsagePanel.jsx").read_text(encoding="utf-8")
    assert "basis?.unmirrored_rows > 0" in src
    assert "basis.local_rows" in src
