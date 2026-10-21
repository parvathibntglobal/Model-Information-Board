"""A scheduled run that ended `ok` having read nothing it could read is not a fetch.

2026-10-06: the first scheduled Action read none of 6,087 unread threads because
their payloads lived on a laptop, ended `ok`, and that `ok` took DeepSeek V4 Pro
0423 off the due list for 7 days. `LAST_SUCCESS` now counts a run only if it read
a thread, or found nothing it could not read. Disposable Postgres only.
"""
from __future__ import annotations

import json
import pathlib

import psycopg
import pytest

from scripts.run_scheduled_fetches import LAST_SUCCESS

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        connection.commit()
        yield connection


def _run(conn, run_id, mv, end):
    for seq, (kind, payload) in enumerate([("run", {"kind": "run"}), ("end", end)]):
        conn.execute(
            "INSERT INTO fetch_log (id, run_id, seq, at, machine, payload, kind, "
            "model_version_id) VALUES (%s, %s, %s, now(), 'test', %s, %s, %s)",
            (f"{run_id}-{seq}", run_id, seq, json.dumps(payload), kind, mv),
        )
    conn.commit()


def _successes(conn):
    return {r[0] for r in conn.execute(LAST_SUCCESS).fetchall()}


def test_an_ok_that_could_read_nothing_does_not_count(conn):
    _run(conn, "r1", "mv_blind", {"kind": "end", "status": "ok",
                                  "threads_unreadable_here": 6087})
    assert "mv_blind" not in _successes(conn)


def test_an_ok_that_read_threads_counts_even_with_some_unreadable(conn):
    _run(conn, "r2", "mv_read", {"kind": "end", "status": "ok", "threads_read": 31,
                                 "threads_unreadable_here": 12})
    assert "mv_read" in _successes(conn)


def test_nothing_new_and_nothing_unreadable_is_a_real_success(conn):
    _run(conn, "r3", "mv_quiet", {"kind": "end", "status": "ok",
                                  "threads_unreadable_here": 0})
    assert "mv_quiet" in _successes(conn)


def test_runs_from_before_the_field_are_judged_as_before(conn):
    _run(conn, "r4", "mv_old", {"kind": "end", "status": "ok"})
    _run(conn, "r5", "mv_err", {"kind": "end", "status": "error"})
    assert _successes(conn) == {"mv_old"}
