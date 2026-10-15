"""The model page gets every board entry for its model, not the first 200.

`evidence_for_model` read `LIMIT 200` over rows ordered by section, so a model
past 200 entries lost whole sections from the end of the alphabet: GLM 5.3's
metrics (2026-10-13, 242 entries) arrived as 12 of 54, and the page said
"200 quotes" as though that were all. Seeded here as 210 best_for entries and
3 capability entries: under the old cap the capability section vanished.
"""
from __future__ import annotations

import pathlib

import psycopg
import pytest

from judge import publication
from judge.store.board_entries import evidence_for_model

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"


@pytest.fixture
def conn(test_dsn, monkeypatch):
    publication.withheld_sources.cache_clear()
    monkeypatch.setenv("PUBLICATION_VIEW", "internal")
    with psycopg.connect(test_dsn, connect_timeout=10) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        connection.execute(
            "INSERT INTO model_version (id, canonical_id, provider, sources, provenance) "
            "VALUES ('mv_big', 'acme/big', 'acme', '{}', 'polled')")
        rows = [("best_for", "coding-agent", "Coding agent", i) for i in range(210)]
        rows += [("capability", "tool-use", "Tool use", 300 + i) for i in range(3)]
        for section, slug, name, i in rows:
            doc = f"d{i}"
            connection.execute(
                "INSERT INTO document (id, source, external_id, url, text_ref, content_hash, "
                "status) VALUES (%s, 'devto', %s, %s, %s, %s, 'kept')",
                (doc, doc, f"https://example.test/{doc}", f"r{doc}", f"h{doc}"))
            connection.execute(
                "INSERT INTO board_entry (id, section, slug, name, definition, model_version_id, "
                "document_id, quote, quote_verified, polarity, proposer_model, pipeline_version) "
                "VALUES (%s, %s, %s, %s, 'd', 'mv_big', %s, %s, true, 'positive', 'm', 'v1')",
                (f"be{i}", section, slug, name, doc, f"quote {i}"))
        connection.commit()
        yield connection
    publication.withheld_sources.cache_clear()


def test_a_model_past_200_entries_keeps_every_section(conn):
    page = evidence_for_model(conn, "mv_big")
    assert page["totals"]["quotes"] == 213
    assert [c["slug"] for c in page["capabilities"]] == ["tool-use"]
    assert page["capabilities"][0]["quote_count"] == 3


def test_an_explicit_cap_still_caps(conn):
    assert evidence_for_model(conn, "mv_big", limit=5)["totals"]["quotes"] == 5
