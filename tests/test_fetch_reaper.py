"""A run that stopped reporting is marked so — and a live one is not.

THE TEST THAT MATTERS IS `test_spares_a_run_that_spoke_recently`. Everything
else here guards the write; that one guards against the reaper being wrong in
the only direction that costs anything. When this was written, five runs on
staging qualified as dead and a sixth had last spoken nine minutes earlier from
ANOTHER machine — almost certainly mid-extract. A reaper keyed on "has no end
record" rather than on silence would have declared that one dead, on a shared
database, while it was still writing to it.
"""
from __future__ import annotations

import datetime
import json
import pathlib

import psycopg
import pytest

from judge import fetch_reaper

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"
NOW = datetime.datetime(2026, 9, 14, 12, 0, tzinfo=datetime.UTC)


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        connection.commit()
        yield connection


def _line(conn, run_id, seq, *, minutes_ago, kind="stage", status="running",
          machine="TESTBOX", name="Harvest"):
    rec = {"kind": kind, "id": "E2", "name": name, "status": status,
           "at": (NOW - datetime.timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")}
    conn.execute(
        "INSERT INTO fetch_log (id, run_id, seq, at, machine, payload, kind, "
        "model_version_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (f"fl_{run_id}_{seq}", run_id, seq,
         NOW - datetime.timedelta(minutes=minutes_ago), machine,
         json.dumps(rec, sort_keys=True), kind, "anthropic/claude-fable-5-1"),
    )
    conn.commit()


def _end_records(conn, run_id):
    rows = conn.execute(
        "SELECT payload FROM fetch_log WHERE run_id = %s AND kind = 'end' ORDER BY seq",
        (run_id,),
    ).fetchall()
    return [r[0] if isinstance(r[0], dict) else json.loads(r[0]) for r in rows]


class TestWhatItSpares:
    def test_spares_a_run_that_spoke_recently(self, conn):
        """THE ONE THAT MATTERS. Silence, not the absence of an end record."""
        _line(conn, "live-run", 0, minutes_ago=9)

        marked = fetch_reaper.reap(conn, now=NOW)

        assert marked == []
        assert _end_records(conn, "live-run") == []

    def test_spares_a_run_that_already_ended(self, conn):
        _line(conn, "done-run", 0, minutes_ago=600)
        _line(conn, "done-run", 1, minutes_ago=599, kind="end", status="ok")

        assert fetch_reaper.reap(conn, now=NOW) == []
        # Still exactly one end record: its own.
        assert [r["status"] for r in _end_records(conn, "done-run")] == ["ok"]

    def test_spares_a_stopped_run(self, conn):
        """`stopped` is an end record. A person already answered this one."""
        _line(conn, "stopped-run", 0, minutes_ago=900)
        _line(conn, "stopped-run", 1, minutes_ago=899, kind="end", status="stopped")

        assert fetch_reaper.reap(conn, now=NOW) == []
        assert [r["status"] for r in _end_records(conn, "stopped-run")] == ["stopped"]


class TestWhatItMarks:
    def test_marks_a_silent_run_abandoned(self, conn):
        _line(conn, "dead-run", 0, minutes_ago=4200)

        marked = fetch_reaper.reap(conn, now=NOW)

        assert [m.run_id for m in marked] == ["dead-run"]
        ends = _end_records(conn, "dead-run")
        assert len(ends) == 1
        assert ends[0]["status"] == "abandoned"

    def test_never_says_it_failed(self, conn):
        """We know it stopped reporting. We do not know that it broke."""
        _line(conn, "dead-run", 0, minutes_ago=4200)

        fetch_reaper.reap(conn, now=NOW)

        rec = _end_records(conn, "dead-run")[0]
        assert rec["status"] != "error"
        blob = json.dumps(rec).lower()
        for word in ("failed", "failure", "crashed", "timed out", "timeout"):
            assert word not in blob, f"the record asserts {word!r}, which nothing observed"

    def test_says_what_it_last_heard_and_when(self, conn):
        _line(conn, "dead-run", 0, minutes_ago=4200, name="Harvest · Reddit")

        fetch_reaper.reap(conn, now=NOW)

        detail = _end_records(conn, "dead-run")[0]["detail"]
        assert "Harvest · Reddit" in detail
        assert "no progress recorded" in detail

    def test_records_which_machine_reaped_it(self, conn):
        """An end record on another host's run must say who added it — #267."""
        _line(conn, "dead-run", 0, minutes_ago=4200, machine="SOMEONE_ELSE")

        fetch_reaper.reap(conn, now=NOW)

        rec = _end_records(conn, "dead-run")[0]
        assert rec["reaped"] is True
        assert rec["reaped_by"]
        # The ROW still belongs to the run's own machine, because the history
        # groups by it and this record is about that run.
        row = conn.execute(
            "SELECT machine FROM fetch_log WHERE run_id='dead-run' AND kind='end'"
        ).fetchone()
        assert row[0] == "SOMEONE_ELSE"

    def test_sorts_last(self, conn):
        """The log is a sequence. An end record must not land mid-run."""
        _line(conn, "dead-run", 0, minutes_ago=4200)
        _line(conn, "dead-run", 7, minutes_ago=4100)

        fetch_reaper.reap(conn, now=NOW)

        rows = conn.execute(
            "SELECT seq, kind FROM fetch_log WHERE run_id='dead-run' ORDER BY seq"
        ).fetchall()
        assert rows[-1][1] == "end"
        assert rows[-1][0] > 7


class TestItDoesNotDisturbWhatIsThere:
    def test_is_idempotent(self, conn):
        _line(conn, "dead-run", 0, minutes_ago=4200)

        first = fetch_reaper.reap(conn, now=NOW)
        before = conn.execute("SELECT count(*) FROM fetch_log").fetchone()[0]
        second = fetch_reaper.reap(conn, now=NOW)
        after = conn.execute("SELECT count(*) FROM fetch_log").fetchone()[0]

        assert [m.run_id for m in first] == ["dead-run"]
        assert second == []          # it now has an end record
        assert before == after

    def test_appends_only(self, conn):
        """Every pre-existing row is byte-identical afterwards."""
        _line(conn, "dead-run", 0, minutes_ago=4200)
        _line(conn, "live-run", 0, minutes_ago=5)
        before = conn.execute(
            "SELECT id, run_id, seq, payload, kind FROM fetch_log ORDER BY id"
        ).fetchall()

        fetch_reaper.reap(conn, now=NOW)

        after = conn.execute(
            "SELECT id, run_id, seq, payload, kind FROM fetch_log WHERE id = ANY(%s) ORDER BY id",
            ([r[0] for r in before],),
        ).fetchall()
        assert after == before

    def test_dry_run_writes_nothing(self, conn):
        _line(conn, "dead-run", 0, minutes_ago=4200)
        before = conn.execute("SELECT count(*) FROM fetch_log").fetchone()[0]

        found = fetch_reaper.reap(conn, now=NOW, dry_run=True)

        assert [f.run_id for f in found] == ["dead-run"]
        assert conn.execute("SELECT count(*) FROM fetch_log").fetchone()[0] == before


class TestTheThresholdIsTheWholeDesign:
    @pytest.mark.parametrize("minutes,reaped", [(44, False), (46, True)])
    def test_the_boundary_is_silence(self, conn, minutes, reaped):
        _line(conn, "edge-run", 0, minutes_ago=minutes)

        marked = fetch_reaper.reap(
            conn, now=NOW, silent_for=datetime.timedelta(minutes=45)
        )

        assert bool(marked) is reaped
