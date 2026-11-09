"""A held-entries failure can never take the board rows with it (#612 review, point 1).

Held rows (claims about a model the registry does not hold, #602) used to be
written BEFORE the board rows and unguarded. On a database where the
`unresolved_entry` migration had not run, the insert raised `UndefinedTable`
and aborted the transaction after the extraction had been paid for, so the
night's board rows were lost too. Now held rows are written after the board
rows, in their own savepoint, and an unmigrated database is named instead.
No database: the pipeline's writers are faked.
"""
from __future__ import annotations

import contextlib
from datetime import date
from types import SimpleNamespace

import psycopg
import pytest

from judge import pipeline as pipeline_mod
from judge.extract.runner import ExtractionRun
from judge.extract.schema import ExtractedClaim


@pytest.fixture
def off(monkeypatch):
    monkeypatch.setenv("LEGACY_CELLS", "off")


def _claim(surface: str, version_id: str, quote: str) -> ExtractedClaim:
    return ExtractedClaim.model_validate({
        "source_comment_id": "d",
        "model_ref": {"surface": surface, "resolved_version_id": version_id,
                      "specificity": "version", "resolution_confidence": 0.9,
                      "speaking": "own-experience"},
        "board_entries": [{"section": "capability", "slug": "development-speed",
                           "name": "Development speed",
                           "definition": "Whether it shortens implementation time."}],
        "polarity": "positive", "quote": quote, "quote_offset": [0, len(quote)],
        "relevance": "central",
    })


class _Conn:
    """Enough of a connection for a savepoint around the held write."""

    def transaction(self):
        return contextlib.nullcontext()


FACTS = {"d": SimpleNamespace(has_numbers=False, has_conditions=False, platform="devto",
                              created_at=date(2026, 9, 20), author_id="a1")}


def test_an_unmigrated_database_keeps_the_board_rows_and_says_why(off, monkeypatch):
    run = ExtractionRun(thread_context_id="t")
    run.verified = [
        (_claim("GPT-5.5", "gpt-5.5", "it was fast"),
         SimpleNamespace(document_id="d", display_text="it was fast")),
        (_claim("Imaginary 9", "imaginary-9", "it was slow"),
         SimpleNamespace(document_id="d", display_text="it was slow")),
    ]
    monkeypatch.setattr(pipeline_mod, "extract", lambda *a, **k: run)

    boards: list = []

    def store(_conn, rows, **_kw):
        boards.extend(rows)
        return {"proposed": len(rows), "stored": len(rows), "skipped_unverified": 0}

    def unmigrated(*_a, **_k):
        raise psycopg.errors.UndefinedTable('relation "unresolved_entry" does not exist')

    import judge.store.board_entries as board_store
    import judge.store.unresolved_entries as held_store

    monkeypatch.setattr(board_store, "store_entries", store)
    monkeypatch.setattr(held_store, "hold_entries", unmigrated)
    p = pipeline_mod.Pipeline(conn=_Conn(), client=None, capability_keys=[],
                              extractor_model="m")
    monkeypatch.setattr(p, "_vet", lambda *a, **k: set())

    result = p.run(SimpleNamespace(thread_context_id="t"), facts=FACTS,
                   model_version_of={"gpt-5.5": "mv_gpt"}, rebuild_cells=False)

    assert [b["model_version_id"] for b in boards] == ["mv_gpt"]
    assert result.board_entries_stored == 1
    assert result.unresolved_held == 0
    assert "migration" in (result.unresolved_held_unavailable or "")
