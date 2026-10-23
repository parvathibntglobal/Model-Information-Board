"""Which pages are worth indexing (judge/seo.py, contract/indexing.yaml) - SEO item 5.

What is pinned:
  1. a page's evidence is counted on the PUBLIC view even when the server runs
     the internal one. The first version of this got it wrong: board_sections'
     new parameter was shadowed by a local of the same name, so an internal
     server counted withheld sources and would have indexed a page whose only
     public evidence was one person. 816 section pages counted as 966.
  2. a page needs `min_voices` DISTINCT voices: one person twice is one voice;
  3. section pages and model pages appear at the PUBLIC paths the frontend
     writes as their canonical (web/src/seo/pages.js) - /reviews/... and
     /ai-models/... - never at the signed-in /board or /models (2026-10-20);
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
        # The catalogue lists it, so it has an /ai-models page (judge/seo.py).
        c.execute("INSERT INTO model_catalog (canonical_id, provider, name, input_modalities, "
                  "output_modalities, pricing, last_seen_at) "
                  "VALUES ('acme/model-t', 'acme', 'Model T', '{text}', '{text}', '{}', now())")
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
        assert "/reviews/capabilities/long-context" not in paths

    def test_the_public_server_agrees(self, conn):
        assert "/reviews/capabilities/long-context" not in _paths(conn)


class TestTheThreshold:
    def test_two_public_voices_is_indexable(self, conn):
        paths = _paths(conn)
        assert paths["/reviews/capabilities/tool-use"]["voices"] == 2

    def test_no_drill_down_is_listed(self, conn):
        """One model inside one section has no public page; it is tallied, not listed."""
        paths = _paths(conn)
        assert not any(p.count("/") > 3 and p.startswith("/reviews/capabilities/") for p in paths)
        assert seo.indexable_pages(conn)["tallies"]["model_in_section"]["indexable"] == 1

    def test_an_indexable_section_page_carries_its_lastmod(self, conn):
        """Every indexable section path carries when its newest public entry was
        added, for the sitemap's <lastmod>."""
        assert _paths(conn)["/reviews/capabilities/tool-use"].get("lastmod")

    def test_one_person_twice_is_one_voice(self, conn):
        assert "/reviews/capabilities/code-review" not in _paths(conn)

    def test_the_model_has_its_two_public_pages(self, conn):
        # Public voices across the whole model: a1, a2, a3, a6 = 4.
        paths = _paths(conn)
        assert paths["/ai-models/acme/model-t"]["voices"] == 4
        assert paths["/reviews/models/acme/model-t"]["voices"] == 4

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
        assert {"/", "/blogs", "/tools", "/ai-models", "/ai-models/latest", "/compare", "/reviews",
                "/reviews/jobs", "/token-counter", "/best-ai-model",
                "/ai-model-pricing"} <= set(paths)
        assert not {"/login", "/admin", "/board", "/models", "/seo-keywords"} & set(paths)

    def test_the_contract_lists_match_the_sitemap_lists(self):
        """contract/indexing.yaml `always` and web/seo-build.js STRUCTURAL_PATHS
        name the same pages, so the sitemap and the noindex rule cannot disagree."""
        import re
        web = pathlib.Path(__file__).resolve().parents[1] / "web"
        src = (web / "seo-build.js").read_text(encoding="utf-8")
        block = src.split("export const STRUCTURAL_PATHS = [", 1)[1].split("]", 1)[0]
        assert set(re.findall(r"'([^']+)'", block)) == set(seo.rules()["always"])

    def test_the_glossary_and_every_term_are_listed(self, conn):
        """The glossary is reviewed copy (glossary.yaml): its index and each term
        page are indexable, with no evidence threshold (2026-10-20)."""
        from judge import glossary

        paths = _paths(conn)
        assert "/glossary" in paths
        slugs = [t["slug"] for t in glossary.load()]
        assert slugs and all(f"/glossary/{s}" in paths for s in slugs)
        assert all(paths[f"/glossary/{s}"]["kind"] == "glossary_term" for s in slugs)

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


def _cached_endpoint(monkeypatch, fake):
    import contextlib

    from judge import app

    monkeypatch.setattr(seo, "indexable_pages", fake)
    monkeypatch.setattr(app, "_conn", lambda: contextlib.nullcontext(None))
    monkeypatch.setattr(app, "_indexable_cache", [])
    monkeypatch.setattr(app, "_indexable_refresh", [])
    clock = [1000.0]
    monkeypatch.setattr(app.time, "monotonic", lambda: clock[0])
    return app, clock


def _wait_for_refresh(app):
    for thread in list(app._indexable_refresh):
        thread.join(timeout=5)


def test_the_indexable_list_is_worked_out_once_for_a_few_minutes(monkeypatch):
    """Every public page asks for /seo/indexable on load, and working it out is
    slow (one evidence query per model). The endpoint keeps its answer for
    _INDEXABLE_TTL_S. Once that has passed, the next call still answers at once
    with the old list and ONE background refresh replaces it (review of #552,
    item 4) - nobody waits on a refresh."""
    calls = []

    def fake(conn):
        calls.append(1)
        return {"paths": [{"path": f"/p{len(calls)}"}]}

    app, clock = _cached_endpoint(monkeypatch, fake)
    assert app.seo_indexable() == {"paths": ["/p1"]}
    assert app.seo_indexable() == {"paths": ["/p1"]}
    assert len(calls) == 1
    clock[0] += app._INDEXABLE_TTL_S + 1
    assert app.seo_indexable() == {"paths": ["/p1"]}   # old list, at once
    _wait_for_refresh(app)
    assert len(calls) == 2
    assert app.seo_indexable() == {"paths": ["/p2"]}   # the refreshed one


def test_a_failed_refresh_keeps_the_old_list(monkeypatch):
    """A refresh that raises leaves the previous list in place, and the next
    call past the deadline tries again."""
    calls = []

    def flaky(conn):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("database away")
        return {"paths": [{"path": f"/p{len(calls)}"}]}

    app, clock = _cached_endpoint(monkeypatch, flaky)
    assert app.seo_indexable() == {"paths": ["/p1"]}
    clock[0] += app._INDEXABLE_TTL_S + 1
    assert app.seo_indexable() == {"paths": ["/p1"]}
    _wait_for_refresh(app)
    # the refresh failed: the old list is kept, and this call started a retry
    assert app.seo_indexable() == {"paths": ["/p1"]}
    _wait_for_refresh(app)
    assert app.seo_indexable() == {"paths": ["/p3"]}


def test_a_model_type_page_is_listed_once_it_shows_enough_reported_models(conn, monkeypatch):
    """/ai-models/<type> is listed when catalog_view counts at least
    `model_types.min_reported_models` reported models of that type - the
    number the page's own type chip shows - and an empty type is not."""
    from judge import catalog

    need = seo.rules()["model_type_min_models"]
    monkeypatch.setattr(catalog, "catalog_view",
                        lambda c: {"types_voiced": {"text": need, "image": need - 1, "video": 0}})
    paths = {p["path"]: p["kind"] for p in seo.indexable_pages(conn)["paths"]}
    assert paths.get("/ai-models/text") == "model_type"
    assert "/ai-models/image" not in paths and "/ai-models/video" not in paths


def test_the_type_threshold_is_required(monkeypatch):
    from judge import config

    real = config._read

    def without(name):
        data = dict(real(name) or {})
        if name == "indexing.yaml":
            data.pop("model_types", None)
        return data

    monkeypatch.setattr(config, "_read", without)
    with pytest.raises(seo.IndexingContractError):
        seo.rules()


def test_a_job_page_brings_its_picker_page_and_a_capability_does_not(conn, monkeypatch):
    """A job section that is worth indexing is also listed as the picker on that
    job (/best-ai-model/<slug>): the same evidence, asked as "which model". A
    capability or metric has no picker page."""
    from judge.store import board_entries

    sections = {"best_for": [{"slug": "coding-agent", "voices": 5, "models": []},
                             {"slug": "thin-job", "voices": 1, "models": []}],
                "capability": [{"slug": "tool-use", "voices": 5, "models": []}]}
    monkeypatch.setattr(board_entries, "board_sections", lambda c, hide_source=None: sections)
    paths = {p["path"] for p in seo.indexable_pages(conn)["paths"]}
    assert {"/reviews/jobs/coding-agent", "/best-ai-model/coding-agent"} <= paths
    assert "/best-ai-model/thin-job" not in paths and "/reviews/jobs/thin-job" not in paths
    assert "/best-ai-model/tool-use" not in paths


def test_an_indexable_model_brings_its_alternatives_page(conn):
    """A model page worth indexing also lists the picker's alternatives to it,
    named by the model's own name (`model-t`), as the picker's canonical is."""
    paths = {p["path"]: p for p in seo.indexable_pages(conn)["paths"]}
    assert paths["/alternatives/model-t"]["kind"] == "model"
    assert paths["/alternatives/model-t"]["voices"] == paths["/ai-models/acme/model-t"]["voices"]


def test_a_model_the_catalogue_does_not_list_has_no_ai_models_page(conn):
    """/ai-models/<id> is the catalogue's page, a 404 for anything it does not
    list; such a model with reports keeps its reviews page and alternatives."""
    conn.execute("DELETE FROM model_catalog")
    conn.commit()
    paths = {p["path"] for p in seo.indexable_pages(conn)["paths"]}
    assert "/ai-models/acme/model-t" not in paths
    assert {"/reviews/models/acme/model-t", "/alternatives/model-t"} <= paths


def test_a_model_reported_only_on_metrics_has_no_alternatives_page(conn, monkeypatch):
    """The picker reads jobs and capabilities, never metrics, so a model whose
    only entries are metrics would open /alternatives/<it> as "not found"."""
    from judge.store import board_entries

    model = {"model_canonical": "acme/model-t", "model_key": "mv_t", "voices": 4}
    only_metric = {"metric": [{"slug": "latency", "voices": 4, "models": [model]}]}
    monkeypatch.setattr(board_entries, "board_sections", lambda c, hide_source=None: only_metric)
    paths = {p["path"] for p in seo.indexable_pages(conn)["paths"]}
    assert "/alternatives/model-t" not in paths


def test_the_export_is_the_scripts_file_from_the_same_cached_list(monkeypatch):
    """`?export=1` (2026-10-21) is what web/Dockerfile fetches for an open
    build: the fields of scripts/export_indexable_paths.py's file that the
    build reads, a lastmod only where a real date exists, and `generated_at`
    from when the list was worked out -
    not when the cache was read."""
    import contextlib

    from judge import app

    def fake(conn):
        return {"paths": [{"path": "/a", "lastmod": "2026-10-20T00:00:00+00:00"}, {"path": "/b"}],
                "tallies": {"model": {"pages": 2, "indexable": 1}}}

    monkeypatch.setattr(seo, "indexable_pages", fake)
    monkeypatch.setattr(app, "_conn", lambda: contextlib.nullcontext(None))
    monkeypatch.setattr(app, "_indexable_cache", [])
    clock = [1000.0]
    monkeypatch.setattr(app.time, "monotonic", lambda: clock[0])

    first = app.seo_indexable(export=True)
    assert first["paths"] == ["/a", "/b"]
    assert first["lastmod"] == {"/a": "2026-10-20T00:00:00+00:00"}
    assert set(first) == {"generated_at", "paths", "lastmod"}
    clock[0] += 10
    assert app.seo_indexable(export=True)["generated_at"] == first["generated_at"]
    assert app.seo_indexable() == {"paths": ["/a", "/b"]}


def test_one_query_counts_the_voices_evidence_for_model_counts(conn):
    """#552 item 12: `voices_by_model` replaced one `evidence_for_model` call
    per model. They must agree model by model, on every gate that decides a
    voice: withheld source, declined row, a metric figure withheld by
    `metric_withholding`, a row with no author, and a second model."""
    from judge.store.board_entries import evidence_for_model, voices_by_model

    conn.execute("INSERT INTO model_version (id, canonical_id, provider, sources, provenance) "
                 "VALUES ('mv_u', 'acme/model-u', 'acme', '{}', 'polled')")
    conn.execute(_AUTHOR, ("a9", "devto", "a9"))
    for doc, author in (("d9", "a9"), ("d10", None)):
        conn.execute(_DOC, (doc, "devto", doc, f"https://example.test/{doc}", f"r{doc}",
                            f"h{doc}", author))
    entry = ("INSERT INTO board_entry (id, section, slug, name, definition, model_version_id, "
             "document_id, quote, quote_verified, polarity, proposer_model, pipeline_version, "
             "unit, value_verbatim, basis, ruling, reviewed_at) VALUES "
             "(%s, %s, %s, 'N', 'Def.', %s, %s, %s, true, 'positive', 'm', 'v1', "
             "%s, %s, %s, %s, %s)")
    rows = [
        ("x1", "capability", "tool-use", "mv_u", "d9", "works", None, None, None, None),
        ("x2", "capability", "tool-use", "mv_t", "d9", "declined", None, None, "declined", "now"),
        ("x3", "metric", "latency", "mv_t", "d9", "fast enough", "ms", "120", None, None),
        ("x4", "capability", "tool-use", "mv_t", "d10", "no author", None, None, None, None),
    ]
    for r in rows:
        basis = "reported" if r[1] == "metric" else None
        conn.execute(entry, (*r[:8], basis, r[8], None if r[9] is None else "2026-10-21T00:00:00Z"))
    for hidden in (list(publication.withheld_sources()), []):
        batched = voices_by_model(conn, hidden=hidden)
        for mv in ("mv_t", "mv_u"):
            one = evidence_for_model(conn, mv, hidden=hidden, with_voices=True)["voices"]
            assert batched.get(mv, 0) == one, (mv, hidden)


def test_a_comparison_is_listed_when_both_models_share_enough_voices(conn, monkeypatch):
    """compare_pairs (review of #552, item 9, option A): /compare/<a>-vs-<b> is
    listed when both models have `compare_pairs.min_voices` public voices in
    one shared section, both catalogued and registered - by the canonical the
    page names (names sorted). A model below the line, or one the catalogue
    does not list, forms no pair."""
    from judge import catalog
    from judge.store import board_entries

    for mv, canon in (("mv_b", "zeta/model-b"), ("mv_c", "acme/model-c"), ("mv_d", "acme/model-d")):
        conn.execute("INSERT INTO model_version (id, canonical_id, provider, sources, provenance) "
                     "VALUES (%s, %s, 'x', '{}', 'polled')", (mv, canon))
    conn.commit()
    need = seo.rules()["compare_min_voices"]

    def m(canon, voices):
        return {"model_canonical": canon, "model_key": canon, "voices": voices}

    sections = {"capability": [{"slug": "tool-use", "voices": 9, "models": [
        m("acme/model-t", need), m("zeta/model-b", need + 3),
        m("acme/model-c", need - 1),    # below the line
        m("acme/model-d", need)]}]}     # not catalogued
    monkeypatch.setattr(board_entries, "board_sections", lambda c, hide_source=None: sections)
    catalogued = [{"id": "acme/model-t"}, {"id": "zeta/model-b"}, {"id": "acme/model-c"}]
    monkeypatch.setattr(catalog, "catalog_view",
                        lambda c: {"models": catalogued, "types_voiced": {}})
    listed = seo.indexable_pages(conn)["paths"]
    pairs = sorted(p["path"] for p in listed if p["kind"] == "compare_pair")
    assert pairs == ["/compare/model-b-vs-model-t"]


def test_the_comparison_threshold_is_required(monkeypatch):
    from judge import config

    real = config._read

    def without(name):
        data = dict(real(name) or {})
        if name == "indexing.yaml":
            data.pop("compare_pairs", None)
        return data

    monkeypatch.setattr(config, "_read", without)
    with pytest.raises(seo.IndexingContractError):
        seo.rules()


def test_a_provider_with_enough_alternatives_pages_gets_its_own(conn, monkeypatch):
    """/alternatives/<provider> (2026-10-22) is listed once the provider has
    `provider_alternatives.min_models` models whose own alternatives page is
    listed; a provider with fewer is not."""
    from judge.store import board_entries

    need = seo.rules()["provider_alt_min_models"]
    rows = [("mv_t", "acme/model-t")] + [(f"mv_a{i}", f"acme/model-{i}") for i in range(need)] \
        + [("mv_z", "zeta/model-z")]
    for mv, canon in rows[1:]:
        conn.execute("INSERT INTO model_version (id, canonical_id, provider, sources, provenance) "
                     "VALUES (%s, %s, 'x', '{}', 'polled')", (mv, canon))
        # one board entry each: the model loop only weighs models with entries
        conn.execute(_ENTRY.replace("'mv_t'", "%s"),
                     (f"be_{mv}", "tool-use", "Tool use", mv, "d1", f"quote for {mv}"))
    conn.commit()
    models = [{"model_canonical": c, "model_key": mv, "voices": 9} for mv, c in rows]
    sections = {"capability": [{"slug": "tool-use", "voices": 9, "models": models}]}
    monkeypatch.setattr(board_entries, "board_sections", lambda c, hide_source=None: sections)
    monkeypatch.setattr(board_entries, "voices_by_model", lambda c, **kw: {mv: 9 for mv, _ in rows},
                        raising=False)
    paths = {p["path"]: p["kind"] for p in seo.indexable_pages(conn)["paths"]}
    assert paths["/alternatives/model-z"] == "model"      # zeta's one model has its own
    assert paths.get("/alternatives/acme") == "provider_alt"
    assert "/alternatives/zeta" not in paths               # one model: below the line


def test_the_provider_alternatives_threshold_is_required(monkeypatch):
    from judge import config

    real = config._read

    def without(name):
        data = dict(real(name) or {})
        if name == "indexing.yaml":
            data.pop("provider_alternatives", None)
        return data

    monkeypatch.setattr(config, "_read", without)
    with pytest.raises(seo.IndexingContractError):
        seo.rules()
