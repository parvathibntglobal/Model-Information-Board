"""`harvest_run` has a writer. Three adapters build the row; one thing inserts it.

No database: the connection is a double, because what is under test is the
writer's own rules — which keys it accepts, which it drops by name, and what it
refuses. The insert itself is one statement and `tests/test_harvest_schema.py`
already covers the columns against a real Postgres.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from collect.ops.ledger import (
    UnknownSource,
    close_harvest_run,
    open_harvest_run,
)


class FakeConn:
    """Records statements. `SELECT 1 FROM source` answers from `known`."""

    def __init__(self, known: set[str] | None = None) -> None:
        self.known = known if known is not None else {"github"}
        self.statements: list[tuple[str, object]] = []

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        if "FROM source" in sql:
            wanted = params[0] if isinstance(params, tuple) else params
            return _Result((1,) if wanted in self.known else None)
        return _Result(None)


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


def fields(**over):
    base = {
        "id": "hr_abc123",
        "source_id": "github",
        "query_key": "repo:openai/openai-python|tools",
        "started_at": datetime(2026, 8, 19, 6, tzinfo=UTC),
        "finished_at": datetime(2026, 8, 19, 6, 1, tzinfo=UTC),
        "items_fetched": 100,
        "items_kept": 12,
        "http_errors": 0,
        "exhausted": True,
        "truncated_by": None,
        "pipeline_version": "collect-0.1.0",
        # Both proposed, neither a column. See _PROPOSED_NOT_IN_SCHEMA.
        "outcome": "ok",
        "sieve_pass_rate": 0.12,
    }
    base.update(over)
    return base


def test_the_row_exists_before_the_fetch_with_no_finish_time():
    """Phase one. The record of an ATTEMPT, which is what a killed sweep leaves.

    A single statement at the end can only record sweeps that finished, so the
    two states FR-10 most needs apart — attempted-and-died, attempted-and-refused
    — would both be absence.
    """
    conn = FakeConn()

    opened = open_harvest_run(conn, fields())

    assert opened.id == "hr_abc123"
    insert = next(s for s, _ in conn.statements if "INSERT INTO harvest_run" in s)
    assert "finished_at" not in insert, "phase one must leave finished_at NULL"
    assert "items_fetched" not in insert
    assert "ON CONFLICT (id) DO NOTHING" in insert
    assert "outcome" not in insert and "sieve_pass_rate" not in insert


def test_closing_sets_the_counts_and_the_finish_time_together():
    """Phase two. They move together, as `job_run_finish_ck` makes them there."""
    conn = FakeConn()
    opened = open_harvest_run(conn, fields())

    close_harvest_run(conn, opened, fields())

    update = next(s for s, _ in conn.statements if s.startswith("UPDATE harvest_run"))
    for column in ("finished_at", "items_fetched", "items_kept", "http_errors",
                   "exhausted", "truncated_by"):
        assert column in update
    assert "outcome" not in update and "sieve_pass_rate" not in update


def test_a_sweep_that_fetched_nothing_records_zero_rather_than_null():
    """Zero is a measurement; NULL is reserved for the sweep that never returned."""
    conn = FakeConn()
    opened = open_harvest_run(conn, fields())

    close_harvest_run(conn, opened, fields(items_fetched=0, items_kept=0))

    _sql, params = next(
        (s, p) for s, p in conn.statements if s.startswith("UPDATE harvest_run")
    )
    assert params["items_fetched"] == 0
    assert params["items_kept"] == 0
    assert params["finished_at"] is not None


def test_it_refuses_when_the_source_row_is_absent():
    """Upstream of the foreign key, because 23503 sends the reader to this writer.

    `source` holds 0 rows on staging: `load_source_rows` has no caller. Until it
    does, every harvest is unrecordable, and the message has to say which loader
    rather than which constraint.
    """
    conn = FakeConn(known=set())

    with pytest.raises(UnknownSource) as refusal:
        open_harvest_run(conn, fields())

    assert "load_source_rows" in str(refusal.value)
    assert not any("INSERT INTO harvest_run" in s for s, _ in conn.statements)


def test_a_key_that_is_neither_a_column_nor_a_known_proposal_fails():
    """A third homeless field must not be silently discarded.

    Dropping unknown keys permissively is how `sieve_pass_rate` would have
    vanished without anyone deciding it had nowhere to live. Named sets, not a
    filter.
    """
    with pytest.raises(ValueError, match="neither a column"):
        open_harvest_run(FakeConn(), fields(surprise_metric=1))


def test_every_column_the_contract_declares_is_set_by_this_writer():
    """The writer's column list against the schema's, so a new column is visible.

    A column added to `harvest_run` that this writer does not populate takes its
    default silently — which is how `in_window` came to sit at its schema default
    on 340 rows and read like a computed answer.
    """
    import re
    from pathlib import Path

    from collect.ops.ledger import _HARVEST_RUN_COLUMNS

    sql = (Path(__file__).resolve().parents[1] / "contract" / "tables.sql").read_text(
        encoding="utf-8"
    )
    body = sql[sql.index("CREATE TABLE harvest_run") :]
    body = body[: body.index("\n);")]
    declared = {
        m.group(1)
        for m in re.finditer(r"^  ([a-z_]+)\s+(?:text|int|timestamptz|boolean)", body, re.M)
    }

    missing = declared - set(_HARVEST_RUN_COLUMNS)
    assert not missing, (
        f"harvest_run declares {sorted(missing)} and write_harvest_run does not "
        "set them; they would take their schema default silently"
    )
