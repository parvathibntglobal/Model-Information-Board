"""The model page says when the model was last fetched, from the shared log.

This has to exist before a schedule can decide not to fetch something: a model a
schedule stopped fetching reads exactly like a model nobody discusses (rule 4)
unless the page says when it was last looked at.

Two facts kept apart - the last fetch that ended ok, and a LATER attempt that
did not - because 34 of 87 runs ended ok on 2026-09-28. A model with no run
says "No per-model fetch recorded", never "0 days". A log that cannot be read
says so, never "none recorded" (rule 12).
"""

from __future__ import annotations

import json
import pathlib
from datetime import UTC, datetime, timedelta

import pytest

from judge.fetch_history import NO_END, RunLine, read, summarise
from tests.conftest import assert_disposable, assert_safe_target

ROOT = pathlib.Path(__file__).resolve().parents[1]
T0 = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)


def _run(rid, day, status, *, minutes=10, detail=None):
    start = T0 + timedelta(days=day)
    end = start + timedelta(minutes=minutes) if status is not None else None
    return RunLine(rid, start, status, detail, end)


class TestTheSummary:
    def test_no_run_is_its_own_answer_not_zero(self):
        assert summarise([]) == {"succeeded": None, "later_attempt": None, "runs_recorded": 0}

    def test_the_last_success_and_a_later_failure_are_both_said(self):
        s = summarise([_run("a", 0, "ok"), _run("b", 3, "error", detail="E5 error")])
        assert s["succeeded"]["run_id"] == "a"
        assert s["later_attempt"]["run_id"] == "b" and s["later_attempt"]["outcome"] == "error"

    def test_an_earlier_failure_is_not_a_later_attempt(self):
        s = summarise([_run("a", 0, "abandoned"), _run("b", 3, "ok")])
        assert s["succeeded"]["run_id"] == "b" and s["later_attempt"] is None

    def test_no_success_at_all_still_names_the_last_attempt(self):
        s = summarise([_run("a", 0, "stopped"), _run("b", 2, "abandoned")])
        assert s["succeeded"] is None
        assert s["later_attempt"]["outcome"] == "abandoned" and s["runs_recorded"] == 2

    def test_a_run_with_no_end_is_not_called_a_failure(self):
        s = summarise([_run("a", 0, None)])
        assert s["later_attempt"]["outcome"] == NO_END

    def test_success_is_dated_by_when_it_ended(self):
        s = summarise([_run("a", 0, "ok", minutes=40)])
        assert s["succeeded"]["at"] == (T0 + timedelta(minutes=40)).isoformat()


class TestThePayloadAndThePage:
    def test_a_read_failure_is_none_not_an_empty_summary(self):
        app = (ROOT / "judge" / "app.py").read_text(encoding="utf-8")
        block = app[app.index("last_fetch = fetch_history.read(conn, mv_id)"):][:200]
        assert "except Exception:\n            last_fetch = None" in block
        assert '"last_fetch": last_fetch,' in app

    def test_the_page_renders_every_state_in_words(self):
        jsx = (ROOT / "web" / "src" / "routes" / "ModelDetail.jsx").read_text(encoding="utf-8")
        assert "No per-model fetch recorded" in jsx
        assert "as recorded in the shared log" in jsx
        assert "could not be read from the shared log" in jsx
        assert "<LastFetched value={page.last_fetch} />" in jsx
        assert "'0 days" not in jsx and "`0 days" not in jsx, "a model today reads 'today'"

    def test_it_does_not_read_swept_at(self):
        src = (ROOT / "judge" / "fetch_history.py").read_text(encoding="utf-8")
        assert "last_swept_at" not in src.split('"""', 2)[2]


@pytest.fixture
def db(test_dsn):
    from collect.db import apply_schema, connect

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        yield connection
    finally:
        connection.close()


def _line(conn, run_id, seq, at, kind, payload, mv="mv_x"):
    conn.execute(
        "INSERT INTO fetch_log (id, run_id, seq, at, machine, payload, kind, model_version_id) "
        "VALUES (%s, %s, %s, %s, 'test-host', %s, %s, %s)",
        (f"{run_id}-{seq}", run_id, seq, at, json.dumps(payload), kind, mv),
    )


class TestAgainstTheTable:
    def test_it_reads_the_latest_end_record_per_run(self, db):
        """94 end records against 87 runs on 2026-09-28: a run can carry two,
        and the later one is its outcome."""
        _line(db, "r1", 0, T0, "run", {"kind": "run"})
        _line(db, "r1", 5, T0 + timedelta(minutes=5), "end", {"status": "abandoned"})
        _line(db, "r1", 6, T0 + timedelta(minutes=9), "end", {"status": "ok"})
        _line(db, "r2", 0, T0 + timedelta(days=2), "run", {"kind": "run"})
        _line(db, "r2", 3, T0 + timedelta(days=2, minutes=3), "end",
              {"status": "error", "detail": "refused: unsafe write target"})
        _line(db, "r3", 0, T0, "run", {"kind": "run"}, mv="mv_other")
        s = read(db, "mv_x")
        assert s["runs_recorded"] == 2
        assert s["succeeded"]["run_id"] == "r1"
        assert s["later_attempt"]["outcome"] == "error"
        assert s["later_attempt"]["detail"] == "refused: unsafe write target"

    def test_a_model_with_no_run_reads_as_none_recorded(self, db):
        assert read(db, "mv_never")["runs_recorded"] == 0
