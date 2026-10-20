"""Which pages are worth indexing (judge/seo.py, contract/indexing.yaml) - SEO item 5.

What is pinned:
  1. a page's evidence is counted on the PUBLIC view even when the server runs
     the internal one. The first version of this got it wrong: board_sections'
     new parameter was shadowed by a local of the same name, so an internal
     server counted withheld sources and would have indexed a page whose only
     public evidence was one person. 816 section pages counted as 966.
  2. a page needs `min_voices` DISTINCT voices: one person twice is one voice;
  3. section pages and model pages appear at the PUBLIC paths the frontend
     writes as their canonical (web/src/seo/pages.js) - /reports/... and
     /catalog/model/... - never at the signed-in /board or /models (2026-10-20);
  4. structural pages are always listed, never-pages never are, and only
     approved blog posts count;
  5. a missing threshold raises instead of defaulting (rule 12).
"""
from __future__ import annotations

import json
import pathlib

import psycopg
import pytest

from judge import publication, seo

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    publication.withheld_sources.cache_clear()
    monkeypatch.delenv("PUBLICATION_VIEW", raising=False)
    yield
    publication.withheld_sources.cache_clear()


#: (document id, source, author, section slug)
DOCS = [
    # tool-use: two public voices -> indexable
    ("d1", "devto", "a1", "tool-use"),
    ("d2", "hackernews", "a2", "tool-use"),
    # long-context: one public voice, plus two WITHHELD voices -> not indexable
    ("d3", "devto", "a3", "long-context"),
    ("d4", "reddit", "a4", "long-context"),
    ("d5", "x", "a5", "long-context"),
    # code-review: one person, twice -> one voice -> not indexable
    ("d6", "devto", "a6", "code-review"),
    ("d7", "devto", "a6", "code-review"),
]


_AUTHOR = ("INSERT INTO author (id, source, external_id) VALUES (%s, %s, %s) "
           "ON CONFLICT DO NOTHING")
_DOC = ("INSERT INTO document (id, source, external_id, url, text_ref, content_hash, "
        "status, author_id) VALUES (%s, %s, %s, %s, %s, %s, 'kept', %s)")
_ENTRY = ("INSERT INTO board_entry (id, section, slug, name, definition, model_version_id, "
          "document_id, quote, quote_verified, polarity, proposer_model, pipeline_version) "
          "VALUES (%s, 'capability', %s, %s, 'Def.', 'mv_t', %s, %s, true, 'positive', "
          "'m', 'v1')")
_POST = "INSERT INTO blog_post (slug, state, doc, stored_at) VALUES (%s, %s, %s, now())"


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.execute(SCHEMA.read_text(encoding="utf-8"))
        c.execute("INSERT INTO model_version (id, canonical_id, provider, sources, provenance) "
                  "VALUES ('mv_t', 'acme/model-t', 'acme', '{}', 'polled')")
        for doc, source, author, slug in DOCS:
            c.execute(_AUTHOR, (author, source, author))
            c.execute(_DOC, (doc, source, doc, f"https://example.test/{doc}",
                             f"r{doc}", f"h{doc}", author))
            c.execute(_ENTRY, (f"be_{doc}", slug, slug.replace("-", " ").title(), doc,
                               f"quote from {doc}"))
        for slug, state in (("approved-post", "approved"), ("pending-post", "pending")):
            c.execute(_POST, (slug, state, json.dumps({"slug": slug, "title": slug})))
        c.commit()
        yield c


def _paths(conn):
    return {p["path"]: p for p in seo.indexable_pages(conn)["paths"]}


class TestCountedOnThePublicView:
    def test_an_internal_server_still_counts_only_public_voices(self, conn, monkeypatch):
        monkeypatch.setenv("PUBLICATION_VIEW", "internal")
        paths = _paths(conn)
        # three voices internally, one publicly: NOT indexable
        assert "/reports/capabilities/long-context" not in paths

    def test_the_public_server_agrees(self, conn):
        assert "/reports/capabilities/long-context" not in _paths(conn)


class TestTheThreshold:
    def test_two_public_voices_is_indexable(self, conn):
        paths = _paths(conn)
        assert paths["/reports/capabilities/tool-use"]["voices"] == 2

    def test_no_drill_down_is_listed(self, conn):
        """One model inside one section has no public page; it is tallied, not listed."""
        paths = _paths(conn)
        assert not any(p.count("/") > 3 and p.startswith("/reports/capabilities/") for p in paths)
        assert seo.indexable_pages(conn)["tallies"]["model_in_section"]["indexable"] == 1

    def test_an_indexable_section_page_carries_its_lastmod(self, conn):
        """Every indexable section path carries when its newest public entry was
        added, for the sitemap's <lastmod>."""
        assert _paths(conn)["/reports/capabilities/tool-use"].get("lastmod")

    def test_one_person_twice_is_one_voice(self, conn):
        assert "/reports/capabilities/code-review" not in _paths(conn)

    def test_the_model_has_its_two_public_pages(self, conn):
        # Public voices across the whole model: a1, a2, a3, a6 = 4.
        paths = _paths(conn)
        assert paths["/catalog/model/acme/model-t"]["voices"] == 4
        assert paths["/reports/models/acme/model-t"]["voices"] == 4

    def test_no_signed_in_page_is_listed(self, conn):
        """/board and /models are behind the sign-in since 2026-10-15."""
        assert not any(p.startswith(("/board", "/models")) for p in _paths(conn))

    def test_tallies_carry_their_denominator(self, conn):
        t = seo.indexable_pages(conn)["tallies"]
        assert t["section"] == {"pages": 3, "indexable": 1}
        assert t["model"] == {"pages": 1, "indexable": 1}


class TestTheLists:
    def test_structural_pages_always_and_never_pages_never(self, conn):
        paths = _paths(conn)
        assert {"/", "/blogs", "/tools", "/catalog", "/catalog/new", "/compare", "/reports",
                "/reports/jobs", "/token-counter", "/model-picker", "/model-finder"} <= set(paths)
        assert not {"/login", "/admin", "/board", "/models", "/seo-keywords"} & set(paths)

    def test_the_contract_lists_match_the_sitemap_lists(self):
        """contract/indexing.yaml `always` and web/seo-build.js STRUCTURAL_PATHS
        name the same pages, so the sitemap and the noindex rule cannot disagree."""
        import re
        web = pathlib.Path(__file__).resolve().parents[1] / "web"
        src = (web / "seo-build.js").read_text(encoding="utf-8")
        block = src.split("export const STRUCTURAL_PATHS = [", 1)[1].split("]", 1)[0]
        assert set(re.findall(r"'([^']+)'", block)) == set(seo.rules()["always"])

    def test_only_approved_posts(self, conn):
        paths = _paths(conn)
        assert "/blogs/approved-post" in paths
        assert "/blogs/pending-post" not in paths


class TestTheContract:
    def test_the_shipped_contract_loads(self):
        r = seo.rules()
        assert r["min_voices"] == {"section": 2, "model_in_section": 2, "model": 2}

    def test_a_missing_threshold_raises(self, monkeypatch):
        import judge.config as config
        monkeypatch.setattr(config, "_read", lambda name: {
            "pages": {"section": {"min_voices": 2}, "model": {"min_voices": 2}},
            "always": [], "never": [], "blog_posts": "approved_only"})
        with pytest.raises(seo.IndexingContractError):
            seo.rules()
