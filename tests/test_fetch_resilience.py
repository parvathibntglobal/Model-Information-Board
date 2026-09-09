"""The three ways the 2026-09-09 fetch run failed, pinned so they cannot recur.

That run harvested seven platforms and reached the board with nothing. Reading
its log, three separate defects — none of them in the pipeline's judgement, all
three in the plumbing around it:

  1. `E2X · ok · 0 post(s) seen` for two X searches that never resolved DNS.
     Every adapter swallows `httpx.HTTPError` into a counter, and no stage read
     the counter, so "asked and answered nothing" and "never got through"
     rendered identically.

  2. `E2R · error · [Errno 11001] getaddrinfo failed` — one failed lookup on
     the first of three variants ended the whole Reddit arm. Reddit's `_get` is
     the one adapter that lets transport errors out, which is the honest choice;
     the arm above it treated the platform as lost.

  3. `? · fetch · error — the connection is lost`, with E3 stuck on "running"
     and E3b, E4 and E5 absent. The socket died during the harvest phase; E3
     found out; E3's handler called `conn.rollback()` for cleanup and that
     raised on the same dead socket, escaping past three stages that had not
     run yet.

These are unit tests over the plumbing, not a fetch: no database and no network.
"""

from __future__ import annotations

import httpx
import pytest

import scripts.fetch_model as fm
from collect.http import DEFAULT_CONNECT_RETRIES, build_client

REAL_UA = "modelboard/0.1 (+https://modelboard.invalid/contact)"


class TestAStageThatOnlyFailedIsNotOk:
    """`_harvest_verdict` — the distinction the X tab could not draw."""

    def test_requests_failed_and_nothing_came_back_is_an_error(self):
        assert fm._harvest_verdict(2, 0) == "error"

    def test_an_empty_platform_with_no_errors_stays_ok(self):
        # A model released last week genuinely has nothing written about it.
        # Calling that a failure would make the log cry wolf on the normal case.
        assert fm._harvest_verdict(0, 0) == "ok"

    def test_some_failed_but_the_platform_answered_is_ok(self):
        # Partial is not failure: the successful queries produced real evidence
        # and the count of failures still travels in the stage row.
        assert fm._harvest_verdict(1, 12) == "ok"


class TestCleanupThatCannotFail:
    """`_safe_rollback` — the line that ended the run."""

    def test_a_rollback_on_a_dead_connection_does_not_raise(self):
        class DeadConn:
            def rollback(self):
                raise RuntimeError("the connection is lost")

        fm._safe_rollback(DeadConn())  # must return, not raise

    def test_it_does_roll_back_when_it_can(self):
        class LiveConn:
            rolled = False

            def rollback(self):
                self.rolled = True

        conn = LiveConn()
        fm._safe_rollback(conn)
        assert conn.rolled is True


class _FakeConn:
    """Enough of psycopg's surface for the liveness check."""

    def __init__(self, *, alive: bool = True) -> None:
        self.closed = False
        self._alive = alive
        self.rollbacks = 0
        self.pings = 0

    def rollback(self):
        self.rollbacks += 1
        if not self._alive:
            raise RuntimeError("the connection is lost")

    def execute(self, sql, params=None):
        self.pings += 1
        if not self._alive:
            raise RuntimeError("the connection is lost")

        class _Cur:
            @staticmethod
            def fetchone():
                return (1,)

        return _Cur()

    def close(self):
        self.closed = True


@pytest.fixture
def opened(monkeypatch):
    """Hand out fake connections in order, recording how many were opened."""
    made: list[_FakeConn] = []

    def _connect(dsn, **kwargs):
        conn = _FakeConn(alive=True)
        made.append(conn)
        return conn

    monkeypatch.setattr(fm, "connect", _connect)
    return made


class TestTheConnectionSurvivesTheHarvestPhase:
    """`_Db` — one connection per run, re-opened when the server drops it."""

    def test_a_live_connection_is_reused_and_not_reopened(self, opened, monkeypatch, tmp_path):
        monkeypatch.setattr(fm, "FETCH_DIR", tmp_path)
        db = fm._Db("postgres://x")
        prog = fm.Progress("run-1", "mv_1")
        assert db.live(prog) is opened[0]
        assert len(opened) == 1 and db.reconnects == 0

    def test_a_closed_connection_is_reopened(self, opened, monkeypatch, tmp_path):
        monkeypatch.setattr(fm, "FETCH_DIR", tmp_path)
        db = fm._Db("postgres://x")
        prog = fm.Progress("run-2", "mv_1")
        opened[0].closed = True

        fresh = db.live(prog)
        assert fresh is opened[1] and db.reconnects == 1

    def test_a_dropped_socket_is_found_by_the_ping_not_by_the_next_stage(
        self, opened, monkeypatch, tmp_path
    ):
        # The failure mode exactly: the socket is gone but nothing has queried
        # it, so `closed` is still False. Only a round trip finds out.
        monkeypatch.setattr(fm, "FETCH_DIR", tmp_path)
        db = fm._Db("postgres://x")
        prog = fm.Progress("run-3", "mv_1")
        opened[0]._alive = False

        fresh = db.live(prog)
        assert fresh is opened[1] and db.reconnects == 1
        assert opened[0].closed is True  # the dead one is not left open

    def test_a_reconnect_is_reported_as_its_own_stage_row(
        self, opened, monkeypatch, tmp_path
    ):
        # A run that silently reconnected four times reads exactly like one that
        # never lost the database, and those are different afternoons.
        monkeypatch.setattr(fm, "FETCH_DIR", tmp_path)
        db = fm._Db("postgres://x")
        prog = fm.Progress("run-4", "mv_1")
        opened[0]._alive = False
        db.live(prog)

        log = (tmp_path / "run-4.jsonl").read_text(encoding="utf-8")
        # `json.dumps` escapes the separator in the stage name, so match the
        # parts that are plainly ASCII rather than the rendered label.
        assert '"id": "DB"' in log and "reconnect" in log
        assert '"reconnects": 1' in log

    def test_an_aborted_transaction_is_cleared_rather_than_reconnected(
        self, opened, monkeypatch, tmp_path
    ):
        # A stage that failed can leave the transaction aborted, which makes
        # every later query raise and the connection LOOK dead when it is only
        # dirty. The rollback in `live()` is what tells the two apart.
        monkeypatch.setattr(fm, "FETCH_DIR", tmp_path)
        db = fm._Db("postgres://x")
        prog = fm.Progress("run-5", "mv_1")

        db.live(prog)
        assert opened[0].rollbacks == 1 and db.reconnects == 0


class TestOneFailedLookupCostsARetryNotAPlatform:
    """`collect/http.build_client` — connect retries for every adapter."""

    def test_the_default_client_retries_connection_failures(self):
        with build_client(user_agent=REAL_UA) as client:
            assert client._transport._pool._retries == DEFAULT_CONNECT_RETRIES
            assert DEFAULT_CONNECT_RETRIES >= 1

    def test_a_caller_that_brings_its_own_transport_keeps_it(self):
        # This is how the suite injects `MockTransport`. A default that
        # overrode it would put the real network back under a test.
        mock = httpx.MockTransport(lambda request: httpx.Response(200))
        with build_client(user_agent=REAL_UA, transport=mock) as client:
            assert client._transport is mock
