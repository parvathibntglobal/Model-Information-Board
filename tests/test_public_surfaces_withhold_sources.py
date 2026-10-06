"""A public surface shows nothing from a withheld source, and says so.

Agreed 2026-10-05: nothing from Reddit, arXiv or X is published on our public
platform (`contract/publication.yaml`, proposed; argument in
`docs/proposals/public-surfaces-withhold-reddit-arxiv-x.md`). These tests pin
the three properties that matter:

  1. the list is read from the contract, and an absent list refuses rather
     than publishing everything (rule 6, rule 12);
  2. on the public view a withheld row is gone from the board and the model
     page, and the payload counts what was withheld (rule 4) without naming
     the platform;
  3. the internal view still shows everything - the team's own board loses
     nothing.
"""
from __future__ import annotations

import pathlib

import psycopg
import pytest

from judge import publication
from judge.store.board_entries import board_sections, evidence_for_model

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    publication.withheld_sources.cache_clear()
    monkeypatch.delenv("PUBLICATION_VIEW", raising=False)
    yield
    publication.withheld_sources.cache_clear()


class TestTheList:
    def test_the_contract_withholds_reddit_arxiv_and_x(self):
        assert set(publication.withheld_sources()) == {"reddit", "arxiv", "x"}

    def test_an_empty_list_refuses_rather_than_publishing_everything(self, monkeypatch):
        import judge.config as config

        monkeypatch.setattr(config, "_read", lambda name: {"withheld_from_public": {"sources": []}})
        with pytest.raises(publication.PublicationConfigError):
            publication.withheld_sources()


class TestTheView:
    def test_unset_is_public(self):
        assert publication.view() == "public"
        assert publication.hidden_here() == publication.withheld_sources()

    def test_internal_hides_nothing(self, monkeypatch):
        monkeypatch.setenv("PUBLICATION_VIEW", "internal")
        assert publication.hidden_here() == ()
        assert not publication.withheld("reddit")

    def test_a_typo_raises_instead_of_picking_a_side(self, monkeypatch):
        monkeypatch.setenv("PUBLICATION_VIEW", "intrenal")
        with pytest.raises(publication.PublicationConfigError):
            publication.view()

    def test_unknown_provenance_is_withheld_on_a_public_view(self):
        assert publication.withheld(None)
        assert publication.withheld("reddit")
        assert not publication.withheld("devto")

    def test_the_notice_names_no_platform(self):
        note = publication.notice(4)
        assert note == {"view": "public", "sources_withheld": 3, "entries": 4}
        assert not any(p in str(note) for p in ("reddit", "arxiv", "x'"))


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
        for doc, source in (("d_dev", "devto"), ("d_red", "reddit"), ("d_x", "x")):
            connection.execute(
                "INSERT INTO document (id, source, external_id, url, text_ref, "
                "content_hash, status) VALUES (%s, %s, %s, %s, %s, %s, 'kept')",
                (doc, source, doc, f"https://example.test/{doc}", f"r{doc}", f"h{doc}"),
            )
            connection.execute(
                "INSERT INTO board_entry (id, section, slug, name, definition, model_version_id, "
                "document_id, quote, quote_verified, polarity, proposer_model, pipeline_version) "
                "VALUES (%s, 'capability', 'tool-use', 'Tool use', 'Calls tools.', 'mv_t', %s, "
                "%s, true, 'positive', 'm', 'v1')",
                (f"be_{doc}", doc, f"quote from {doc}"),
            )
        connection.commit()
        yield connection


def _board_quotes(conn):
    board = board_sections(conn)
    items = board.get("capability") or []
    items = items if isinstance(items, list) else list(items.values())
    return board, {q.get("quote") if isinstance(q, dict) else q
                   for item in items for q in item.get("quotes", [])}


class TestTheBoard:
    def test_public_shows_only_the_published_source_and_counts_the_rest(self, conn):
        board, quotes = _board_quotes(conn)
        assert "quote from d_dev" in str(quotes)
        assert "d_red" not in str(quotes) and "d_x" not in str(quotes)
        assert board["_withheld_sources"]["entries"] == 2

    def test_internal_shows_everything(self, conn, monkeypatch):
        monkeypatch.setenv("PUBLICATION_VIEW", "internal")
        board, quotes = _board_quotes(conn)
        assert all(f"quote from {d}" in str(quotes) for d in ("d_dev", "d_red", "d_x"))
        assert board["_withheld_sources"]["entries"] == 0


class TestTheModelPage:
    def test_public_evidence_excludes_withheld_sources(self, conn):
        page = evidence_for_model(conn, "mv_t")
        text = str(page["capabilities"])
        assert "quote from d_dev" in text
        assert "d_red" not in text and "d_x" not in text
        assert page["withheld_sources"]["entries"] == 2

    def test_internal_evidence_is_whole(self, conn, monkeypatch):
        monkeypatch.setenv("PUBLICATION_VIEW", "internal")
        page = evidence_for_model(conn, "mv_t")
        text = str(page["capabilities"])
        assert all(f"quote from {d}" in text for d in ("d_dev", "d_red", "d_x"))
        assert page["withheld_sources"]["entries"] == 0


class TestDerivedPosts:
    """Blog drafts may draw on withheld sources (anooj, 2026-10-05), and the
    flag is read strictly - a missing or non-boolean value never decides."""

    @pytest.fixture(autouse=True)
    def _clear(self):
        publication.derived_posts_may_draw_on_withheld.cache_clear()
        yield
        publication.derived_posts_may_draw_on_withheld.cache_clear()

    def test_the_contract_allows_derived_posts(self):
        assert publication.derived_posts_may_draw_on_withheld() is True

    @pytest.mark.parametrize("block", [{}, {"may_draw_on_withheld": "yes"}, None])
    def test_absent_or_non_boolean_raises(self, monkeypatch, block):
        import judge.config as config

        monkeypatch.setattr(config, "_read", lambda name: {"derived_posts": block})
        with pytest.raises(publication.PublicationConfigError):
            publication.derived_posts_may_draw_on_withheld()

    def test_the_generator_selects_everything_when_allowed(self):
        import generate_sample_blogs as g

        assert g._public_thread_sql("tc.id") == "TRUE"

    def test_the_generator_excludes_withheld_threads_when_not(self, monkeypatch):
        import generate_sample_blogs as g

        monkeypatch.setattr(g, "derived_posts_may_draw_on_withheld", lambda: False)
        sql = g._public_thread_sql("tc.id")
        assert "NOT EXISTS" in sql and "'reddit'" in sql and "'x'" in sql
