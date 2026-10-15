"""The Reports page (`/reports`, judge/reports.py, 2026-10-14).

Three properties the page promises and these pin:

* ALWAYS THE PUBLIC VIEW. A withheld source (Reddit, X) adds nothing to any
  count, even on a deployment whose own view is internal.
* COUNTS ONLY. No quote, URL, document id, author or platform NAME leaves the
  module; a model carries how many platforms, never which.
* THE BOARD'S NUMBERS. `voices`, `reports`, the split and the group are the
  board's own, so the page and the board never disagree.
"""

from __future__ import annotations

import json
import pathlib

import psycopg
import pytest

from judge import publication
from judge.reports import reports_view

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    publication.withheld_sources.cache_clear()
    monkeypatch.delenv("PUBLICATION_VIEW", raising=False)
    yield
    publication.withheld_sources.cache_clear()


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        connection.execute(
            "INSERT INTO model_version (id, canonical_id, provider, sources, provenance) "
            "VALUES ('mv_t', 'acme/model-t', 'acme', '{}', 'polled')"
        )
        rows = (
            ("d_dev", "devto", "capability", "positive"),
            ("d_hn", "hackernews", "capability", "negative"),
            ("d_red", "reddit", "capability", "positive"),
            ("d_x", "x", "capability", "positive"),
            ("d_m", "devto", "metric", "negative"),
        )
        for doc, source, section, polarity in rows:
            connection.execute(
                "INSERT INTO document (id, source, external_id, url, text_ref, "
                "content_hash, status, created_at) VALUES (%s, %s, %s, %s, %s, %s, 'kept', %s)",
                (doc, source, doc, f"https://example.test/{doc}", f"r{doc}", f"h{doc}",
                 "2026-10-01T00:00:00Z" if source in ("reddit", "x") else "2026-09-01T00:00:00Z"),
            )
            slug, name = (("tool-use", "Tool use") if section == "capability"
                          else ("latency", "Latency"))
            metric = section == "metric"
            connection.execute(
                "INSERT INTO board_entry (id, section, slug, name, definition, model_version_id, "
                "document_id, quote, quote_verified, polarity, proposer_model, pipeline_version, "
                "unit, value_verbatim, basis) "
                "VALUES (%s, %s, %s, %s, 'Def.', 'mv_t', %s, %s, true, %s, 'm', 'v1', %s, %s, %s)",
                (f"be_{doc}", section, slug, name, doc,
                 f"quote from {doc}" + (": latency was 900ms" if metric else ""), polarity,
                 *(("ms", "900ms", "reported") if metric else (None, None, None))),
            )
        connection.commit()
        yield connection


def _axis(view, kind, slug):
    return next(a for a in view["axes"] if a["kind"] == kind and a["slug"] == slug)


def test_totals_count_every_source_and_name_none_of_the_withheld(conn, monkeypatch):
    """contract/publication.yaml, amended 2026-10-15: a TOTAL counts every
    source ("20 voices" includes Reddit), and nothing splits it by platform. The
    number of platforms counts only the ones a public page may name, on any
    deployment view."""
    for view_name in ("internal", "public"):
        monkeypatch.setenv("PUBLICATION_VIEW", view_name)
        view = reports_view(conn)
        m = _axis(view, "capability", "tool-use")["models"][0]
        assert m["reports"] == 4  # devto, hackernews, reddit and x
        assert m["platforms"] == 2  # devto, hackernews: withheld ones never counted as named
        assert m["split"] == {"positive": 3, "negative": 1, "neutral": 0, "both": 0}
        assert m["newest"] == "2026-10-01"  # the newest counted post
        assert view["withheld_entries"] == 0  # nothing left out of a total


def test_nothing_that_identifies_a_statement_leaves(conn):
    blob = json.dumps(reports_view(conn)).lower()
    for bad in ("quote from", "example.test", "d_dev", "document_id", "author",
                "devto", "hackernews", "reddit", "url"):
        assert bad not in blob, bad


def test_an_axis_carries_its_group_and_the_group_its_heading(conn, monkeypatch):
    import judge.reports as reports

    monkeypatch.setattr("judge.board_grouping.parent_of",
                        lambda slug, section: "agentic" if slug == "tool-use" else None)
    monkeypatch.setattr("judge.config.parent_heading", lambda pid: "Agentic and tool use")
    view = reports.reports_view(conn)
    assert _axis(view, "capability", "tool-use")["parent"] == "agentic"
    assert _axis(view, "metric", "latency")["parent"] is None
    assert view["parents"] == {"agentic": "Agentic and tool use"}


def test_a_metric_row_is_split_per_report(conn):
    m = _axis(reports_view(conn), "metric", "latency")["models"][0]
    assert m["reports"] == 1
    assert m["split"] == {"positive": 0, "negative": 1, "neutral": 0, "both": 0}


def test_the_numbers_are_the_boards(conn):
    from judge.store.board_entries import board_sections

    board = board_sections(conn, hide_source=lambda src: src in publication.hidden_from_counts())
    b = next(i for i in board["capability"] if i["slug"] == "tool-use")["models"][0]
    r = _axis(reports_view(conn), "capability", "tool-use")["models"][0]
    assert (r["voices"], r["reports"], r["group"]) == (b["voices"], b["reports"], b["group"])
    assert r["split"] == {k: b["report_split"].get(k, 0) for k in r["split"]}
