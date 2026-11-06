"""Entries of verified claims whose model is not in the registry: held, then filed.

#602. A 2026-11-05 local fetch verified 50 claims and kept 3: the rest named a
model the registry did not hold yet (GPT-Image 2.6, released the day before)
and were dropped. They are now held in `unresolved_entry` and filed onto the
board by `attribute_held` once the model is seated, with no second model call.

Disposable Postgres only (`TEST_DATABASE_URL`).
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from judge.store.unresolved_entries import attribute_held, held_surfaces, hold_entries

SCHEMA = Path(__file__).resolve().parent.parent / "contract" / "tables.sql"


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        connection.execute(
            "INSERT INTO document (id, source, external_id, url, text_ref, content_hash, "
            "created_at, retrieval_provenance) VALUES ('devto:1', 'devto', '1', "
            "'https://dev.to/x', 'raw/x', 'x', %s, 'not_recorded')",
            (datetime.now(UTC),),
        )
        connection.commit()
        yield connection


def _row(surface, quote="2.6 Sunburst outputs SVG, which 2.5 cannot"):
    return {
        "surface": surface, "document_id": "devto:1", "thread_context_id": "tc_1",
        "section": "capability", "slug": "svg-generation", "name": "SVG generation",
        "definition": "Emits a valid SVG image.", "unit": None, "value_verbatim": None,
        "basis": None, "parent_proposed": None, "axis_verbatim": None,
        "subject_verbatim": None, "polarity": "positive", "quote": quote,
    }


def test_held_once_and_a_rerun_does_not_double_it(conn):
    rows = [_row("gpt-image-2.6 sunburst")]
    assert hold_entries(conn, rows, proposer_model="m") == 1
    assert hold_entries(conn, rows, proposer_model="m") == 0
    assert held_surfaces(conn) == {"gpt-image-2.6 sunburst": 1}


def test_filed_once_seated_and_an_unknown_name_stays_held(conn):
    hold_entries(conn, [_row("gpt-image-2.6 sunburst"),
                        _row("Qwen", quote="Qwen does this too, sometimes")], proposer_model="m")
    conn.execute(
        "INSERT INTO model_version (id, canonical_id, provider, display_name, sources, "
        "provenance) VALUES ('mv_26', 'openai/gpt-image-2.6-sunburst', 'openai', "
        "'GPT Image 2.6 Sunburst', '{}'::jsonb, 'unpolled')")
    resolve = {"gpt-image-2.6 sunburst": "mv_26"}.get

    dry = attribute_held(conn, resolve, dry_run=True)
    assert dry["resolvable"] == 1 and dry["filed"] == 0
    assert conn.execute("SELECT count(*) FROM board_entry").fetchone()[0] == 0

    out = attribute_held(conn, resolve, dry_run=False)
    assert out["filed"] == 1 and out["still_held"] == {"Qwen": 1}
    row = conn.execute(
        "SELECT model_version_id, quote, quote_verified FROM board_entry").fetchone()
    assert row == ("mv_26", "2.6 Sunburst outputs SVG, which 2.5 cannot", True)
    assert held_surfaces(conn) == {"Qwen": 1}
    # A second pass files nothing again.
    assert attribute_held(conn, resolve, dry_run=False)["filed"] == 0


def test_held_by_name_counts_entries_and_distinct_authors(conn):
    from judge.store.unresolved_entries import held_by_name

    hold_entries(conn, [_row("gpt-image-2.6 sunburst"),
                        _row("gpt-image-2.6 sunburst", quote="2.6 also writes GIFs now")],
                 proposer_model="m")
    assert held_by_name(conn) == {"gpt-image-2.6 sunburst": (2, 0)}, (
        "the test document has no author: entries count, authors do not")
