"""`speaking` reaches the board (20261112T0900_board_entry_speaking.sql).

The extractor answers `model_ref.speaking` (own-experience / vendor-about-own-
product / relayed-from-elsewhere) on every call. Before this column the answer
was stored only on `claim`, which LEGACY_CELLS=off never writes, so it was paid
for and discarded (rule 9). These tests pin the three things that make the
column trustworthy:

  - the pipeline carries it onto every board row AND every held row;
  - the store writes it, and a row with no speaker stays NULL (rule 6), never a
    guessed value;
  - a held entry keeps its speaker when it is filed onto the board, and one held
    before the column existed arrives as NULL.

The first test needs no database; the rest use a disposable Postgres
(`TEST_DATABASE_URL`).
"""
from __future__ import annotations

import contextlib
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest

from judge import pipeline as pipeline_mod
from judge.extract.runner import ExtractionRun
from judge.extract.schema import ExtractedClaim

SCHEMA = Path(__file__).resolve().parent.parent / "contract" / "tables.sql"


def _claim(surface: str, version_id: str, quote: str, speaking: str) -> ExtractedClaim:
    return ExtractedClaim.model_validate({
        "source_comment_id": "d",
        "model_ref": {"surface": surface, "resolved_version_id": version_id,
                      "specificity": "version", "resolution_confidence": 0.9,
                      "speaking": speaking},
        "board_entries": [{"section": "best_for", "slug": "invoice-reconciliation",
                           "name": "Invoice reconciliation",
                           "definition": "Matches invoices to payments."}],
        "polarity": "positive", "quote": quote, "quote_offset": [0, len(quote)],
        "relevance": "central",
    })


class _Conn:
    def transaction(self):
        return contextlib.nullcontext()


def test_the_pipeline_carries_speaking_onto_board_and_held_rows(monkeypatch):
    monkeypatch.setenv("LEGACY_CELLS", "off")
    run = ExtractionRun(thread_context_id="t")
    run.verified = [
        (_claim("GPT-5.5", "gpt-5.5", "we reconcile invoices with it", "own-experience"),
         SimpleNamespace(document_id="d", display_text="we reconcile invoices with it")),
        (_claim("Imaginary 9", "imaginary-9", "the vendor says it reconciles",
                "relayed-from-elsewhere"),
         SimpleNamespace(document_id="d", display_text="the vendor says it reconciles")),
    ]
    monkeypatch.setattr(pipeline_mod, "extract", lambda *a, **k: run)
    boards: list = []
    held: list = []

    def store(_conn, rows, **_kw):
        boards.extend(rows)
        return {"proposed": len(rows), "stored": len(rows), "skipped_unverified": 0}

    def hold(_conn, rows, **_kw):
        held.extend(rows)
        return len(rows)

    import judge.store.board_entries as board_store
    import judge.store.unresolved_entries as held_store

    monkeypatch.setattr(board_store, "store_entries", store)
    monkeypatch.setattr(held_store, "hold_entries", hold)
    p = pipeline_mod.Pipeline(conn=_Conn(), client=None, capability_keys=[], extractor_model="m")
    monkeypatch.setattr(p, "_vet", lambda *a, **k: set())
    facts = {"d": SimpleNamespace(has_numbers=False, has_conditions=False, platform="devto",
                                  created_at=date(2026, 11, 12), author_id="a1")}
    p.run(SimpleNamespace(thread_context_id="t"), facts=facts,
          model_version_of={"gpt-5.5": "mv_gpt"}, rebuild_cells=False)

    assert [b["speaking"] for b in boards] == ["own-experience"]
    assert [h["speaking"] for h in held] == ["relayed-from-elsewhere"]


# ── database ────────────────────────────────────────────────────────────────


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
        connection.execute(
            "INSERT INTO model_version (id, canonical_id, provider, display_name, sources, "
            "provenance) VALUES ('mv_1', 'acme/model-1', 'acme', 'Model 1', '{}'::jsonb, "
            "'unpolled')")
        connection.commit()
        yield connection


def _entry(quote: str, **extra) -> dict:
    return {"section": "best_for", "slug": "invoice-reconciliation",
            "name": "Invoice reconciliation", "definition": "Matches invoices to payments.",
            "model_version_id": "mv_1", "document_id": "devto:1", "quote": quote,
            "quote_verified": True, "polarity": "positive", **extra}


def test_store_writes_speaking_and_leaves_an_absent_one_null(conn):
    from judge.store.board_entries import store_entries

    store_entries(conn, [_entry("we reconcile with it daily", speaking="own-experience"),
                         _entry("a row from a caller with no speaker")],
                  proposer_model="m")
    got = dict(conn.execute("SELECT quote, speaking FROM board_entry").fetchall())
    assert got == {"we reconcile with it daily": "own-experience",
                   "a row from a caller with no speaker": None}


def test_an_unknown_speaker_is_refused_by_the_schema(conn):
    from judge.store.board_entries import store_entries

    with pytest.raises(psycopg.errors.CheckViolation):
        store_entries(conn, [_entry("x", speaking="my-cousin")], proposer_model="m")


def test_a_held_entry_keeps_its_speaker_on_the_board(conn):
    from judge.store.unresolved_entries import attribute_held, hold_entries

    base = {"surface": "model one", "document_id": "devto:1", "thread_context_id": "tc",
            "section": "best_for", "slug": "invoice-reconciliation",
            "name": "Invoice reconciliation", "definition": "Matches invoices to payments.",
            "unit": None, "value_verbatim": None, "basis": None, "parent_proposed": None,
            "axis_verbatim": None, "subject_verbatim": None, "polarity": "positive"}
    hold_entries(conn, [{**base, "quote": "I ran month-end on it", "speaking": "own-experience"},
                        # held before the column existed: no speaker at all
                        {**base, "quote": "an older held row"}],
                 proposer_model="m")
    attribute_held(conn, {"model one": "mv_1"}.get, dry_run=False)
    got = dict(conn.execute("SELECT quote, speaking FROM board_entry").fetchall())
    assert got == {"I ran month-end on it": "own-experience", "an older held row": None}
