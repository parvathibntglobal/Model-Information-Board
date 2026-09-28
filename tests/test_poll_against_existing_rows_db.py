"""The poll against a registry it did not build, against a real Postgres.

Every other registry test builds its rows through `write_model_versions`, so
every row id is `stable_id("mv", canonical_id)` and the poll's computed id and
the row's id always agree. The shared database is not like that: hand-entered
models carry ids a person typed. The first scheduled poll, 2026-09-24, met one
(`anthropic/claude-fable-5-1`, canonical `anthropic/claude-fable-5.1`) and died
writing `pricing_history` for a computed id that had no row.

The tombstone stage had only unit tests and a source-order check, so nothing
ran a tombstoned model through the stage against a database either. That case
is here too, although it was not the cause.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from psycopg.types.json import Json

from collect.ids import stable_id
from collect.registry.openrouter import parse_models, write_model_versions
from tests.conftest import assert_disposable, assert_safe_target

HAND_ID = "anthropic/claude-fable-5-1"
CANONICAL = "anthropic/claude-fable-5.1"


@pytest.fixture
def conn(test_dsn):
    from collect.db import apply_schema, connect

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _entry(model_id: str) -> dict:
    return {"id": model_id, "name": model_id, "created": 1780000000,
            "pricing": {"prompt": "0.000001", "completion": "0.000002"},
            "context_length": 8192}


def _feed(*ids: str):
    return parse_models({"data": [_entry(i) for i in ids]}, retrieved_at=datetime.now(UTC))


def _hand_entered(conn, row_id: str, canonical_id: str) -> None:
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, display_name, provenance, "
        "sources) VALUES (%s, %s, 'anthropic', 'Claude Fable 5.1', 'unpolled', %s)",
        (row_id, canonical_id, Json({})),
    )
    conn.commit()


class TestAHandEnteredRowTheCatalogueNowLists:
    def test_the_poll_writes_history_under_the_rows_own_id(self, conn):
        _hand_entered(conn, HAND_ID, CANONICAL)

        write_model_versions(conn, _feed(CANONICAL))
        conn.commit()

        history = conn.execute("SELECT model_version_id FROM pricing_history").fetchall()
        assert history == [(HAND_ID,)]
        assert stable_id("mv", CANONICAL) != HAND_ID, "the case this test exists for"

    def test_no_second_row_is_created(self, conn):
        _hand_entered(conn, HAND_ID, CANONICAL)
        counts = write_model_versions(conn, _feed(CANONICAL, "openai/gpt-6"))
        conn.commit()

        assert (counts["inserted"], counts["updated"]) == (1, 1)
        ids = {r[0] for r in conn.execute("SELECT id FROM model_version").fetchall()}
        assert ids == {HAND_ID, stable_id("mv", "openai/gpt-6")}

    def test_events_are_keyed_on_the_rows_id_too(self, conn):
        _hand_entered(conn, HAND_ID, CANONICAL)
        write_model_versions(conn, _feed(CANONICAL))
        conn.commit()

        orphans = conn.execute(
            "SELECT count(*) FROM model_event e LEFT JOIN model_version m "
            "ON m.id = e.model_version_id WHERE m.id IS NULL"
        ).fetchone()[0]
        assert orphans == 0


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class TestATombstonedModelThroughTheStage:
    def test_nothing_is_written_for_it_in_any_table(self, conn, monkeypatch):
        from collect.ops import chain
        from collect.registry import openrouter, tombstones

        payload = {"data": [_entry("openai/gpt-4o"), _entry("openai/gpt-4o:batch"),
                            _entry("openai/gpt-6")]}
        monkeypatch.setattr(openrouter, "fetch_models", lambda _client: _Response(payload))
        monkeypatch.setattr(tombstones, "load_tombstones", lambda: frozenset({"openai/gpt-4o"}))

        result = chain._poll_registry_stage({"conn": conn, "client": object()})
        conn.commit()

        assert result.outcome == chain.OK, result.detail
        assert result.counts["tombstoned_skipped"] == 1
        stone = stable_id("mv", "openai/gpt-4o")
        for table, column in (("model_version", "id"), ("pricing_history", "model_version_id"),
                              ("model_event", "model_version_id")):
            n = conn.execute(f"SELECT count(*) FROM {table} WHERE {column} = %s",
                             (stone,)).fetchone()[0]
            assert n == 0, f"{table} has a row for a tombstoned model"


class TestAFailedStageDoesNotTakeTheNextOneWithIt:
    def test_an_independent_stage_runs_after_one_that_aborted_the_transaction(self, conn):
        from collect.ops.chain import ERROR, OK, Stage, StageResult, run_chain

        def aborts(context):
            context["conn"].execute("SELECT 1/0")

        def reads(context):
            context["conn"].execute("SELECT count(*) FROM model_version").fetchone()
            return StageResult(OK)

        run = run_chain([Stage("poll", run=aborts), Stage("window", run=reads)], {"conn": conn})

        assert run.results["poll"].outcome == ERROR
        assert run.results["window"].outcome == OK, run.results["window"].detail
