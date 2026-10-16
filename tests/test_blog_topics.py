"""The blog's topic harvest (2026-10-16): judge/topics.py, read by Admin -> Blogs.

What is guarded:
    - a topic is what an item is ABOUT: a term in its title, or twice in its
      summary - never one passing mention, never inside another word;
    - blog_topics.yaml has no defaults (rule 12);
    - a topic with nothing in the window is NAMED, not dropped (rule 4);
    - several items make a combined article, one makes an explainer;
    - an emerging phrase is one no topic covers, and code adopts none.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from judge import topics
from tests.conftest import assert_disposable, assert_safe_target

NOW = datetime(2026, 10, 16, 12, tzinfo=UTC)


# ── matching ──────────────────────────────────────────────────────────────


def test_a_term_in_the_title_files_the_item():
    assert "rag" in topics.match("A survey of RAG pipelines")
    assert "reasoning-models" in topics.match("System 1 and System 2 thinking in language models")


def test_one_passing_mention_in_a_summary_does_not():
    assert "evals" not in topics.match("A new optimiser", "We report results on one benchmark.")
    assert "evals" in topics.match("A new optimiser", "A benchmark, then a second benchmark.")


def test_a_term_inside_another_word_is_not_a_match():
    assert topics.match("Dragging fragments in a basic masked encoder") == []


def test_the_config_has_no_defaults(tmp_path, monkeypatch):
    bad = tmp_path / "blog_topics.yaml"
    bad.write_text("arxiv: {query: x, max_pages: 1}\ntopics: []\n", encoding="utf-8")
    monkeypatch.setattr(topics, "CONFIG", bad)
    topics.config.cache_clear()
    try:
        with pytest.raises(ValueError, match="window_days"):
            topics.config()
    finally:
        topics.config.cache_clear()


def test_every_shipped_topic_has_a_key_a_name_and_terms():
    cfg = topics.config()
    assert cfg["topics"] and all(t["key"] and t["name"] and t["terms"] for t in cfg["topics"])


def test_a_possessive_and_a_stopword_are_not_phrases():
    assert topics._ngrams("Netflix's new Model’s data stack") == set()
    assert "speculative decoding" in topics._ngrams("Faster speculative decoding for agents")


# ── against the database ──────────────────────────────────────────────────


@pytest.fixture
def conn(test_dsn):
    from collect.db import apply_schema, connect

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _item(conn, iid, title, days_ago, summary=None):
    conn.execute(
        "INSERT INTO topic_item (id, source, kind, title, summary, url, published_at, topics) "
        "VALUES (%s, 'arxiv', 'paper', %s, %s, %s, %s, %s)",
        (iid, title, summary, f"https://arxiv.org/abs/{iid}", NOW - timedelta(days=days_ago),
         topics.match(title, summary)),
    )


def test_overview_counts_and_names_the_silent_topics(conn):
    _item(conn, "1", "Graph RAG at scale", 2)
    _item(conn, "2", "Retrieval-augmented generation for code", 10)
    _item(conn, "3", "Mixture of experts routing", 3)
    _item(conn, "4", "Old RAG paper", 40)  # outside the window
    _item(conn, "5", "A note on optimisers", 1)  # matches nothing

    ov = topics.overview(conn, NOW)
    by = {t["key"]: t for t in ov["topics"]}
    assert by["rag"]["in_window"] == 2 and by["rag"]["this_week"] == 1
    assert by["moe"]["in_window"] == 1
    assert "superintelligence" in ov["silent"] and "rag" not in ov["silent"]
    assert ov["unmatched_in_window"] == 1
    assert ov["items"] == 5


def test_the_plan_gives_each_active_topic_a_shape(conn):
    _src(conn, "1", "blog:example.org", "Graph RAG at scale", 2)
    _src(conn, "2", "blog:example.org", "Retrieval-augmented generation for code", 5)
    _src(conn, "3", "blog:example.org", "Mixture of experts routing", 3)

    shapes = {p["key"]: p["shape"] for p in topics.plan(conn, NOW)}
    assert shapes == {"rag": "combined article", "moe": "explainer with a quiz"}


def test_emerging_lists_only_phrases_no_topic_covers(conn):
    for i in range(3):
        _item(conn, f"s{i}", f"Speculative sampling trick {i}", 2)
        _item(conn, f"r{i}", f"Retrieval augmented generation variant {i}", 2)
        _item(conn, f"w{i}", f"Weight averaging recipes part {i}", 2)

    phrases = {e["phrase"] for e in topics.emerging(conn, NOW)}
    assert any("weight averaging" in p for p in phrases)
    assert not any("retrieval augmented" in p for p in phrases)  # covered by `rag`


def test_the_admin_routes_exist():
    from judge.app import app

    paths = {(r.path, m) for r in app.routes for m in getattr(r, "methods", ())}
    assert ("/blog-topics", "GET") in paths and ("/blog-topics/harvest", "POST") in paths


# ── topic posts (Phase C): sources, shapes, the quiz ──────────────────────


def _src(conn, iid, source, title, days_ago):
    conn.execute(
        "INSERT INTO topic_item (id, source, kind, title, url, published_at, topics) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (iid, source, "paper" if source == "arxiv" else "post", title, f"https://example.org/{iid}",
         NOW - timedelta(days=days_ago), topics.match(title)),
    )


def _arxiv_off(monkeypatch):
    import copy

    cfg = copy.deepcopy(topics.config())
    cfg["posts"]["arxiv_as_source"] = False
    monkeypatch.setattr(topics, "config", lambda: cfg)


def test_arxiv_is_a_source_with_its_acknowledgement(conn):
    # 2026-10-16: the team read arXiv's terms; publishing needs the acknowledgement.
    posts = topics.config()["posts"]
    assert posts["arxiv_as_source"] is True and "arXiv" in posts["arxiv_acknowledgement"]
    _src(conn, "a1", "arxiv", "A RAG paper", 2)
    _src(conn, "b1", "blog:example.org", "RAG in a support desk", 3)
    assert {s["id"] for s in topics.sources(conn, "rag", NOW)} == {"a1", "b1"}


def test_with_arxiv_switched_off_it_is_not_a_source(conn, monkeypatch):
    _arxiv_off(monkeypatch)
    _src(conn, "a1", "arxiv", "A RAG paper", 2)
    _src(conn, "b1", "blog:example.org", "RAG in a support desk", 3)
    assert [s["id"] for s in topics.sources(conn, "rag", NOW)] == ["b1"]


def test_an_arxiv_only_topic_says_why_when_arxiv_is_off(conn, monkeypatch):
    _arxiv_off(monkeypatch)
    _src(conn, "a1", "arxiv", "Mixture of experts routing", 2)
    plan = {p["key"]: p for p in topics.plan(conn, NOW)}
    assert plan["moe"]["shape"] is None and "arXiv" in plan["moe"]["why_not"]


def test_a_model_is_counted_by_its_whole_name_and_never_by_an_ordinary_word(conn):
    conn.execute(
        "INSERT INTO model_version "
        "  (id, canonical_id, provider, family, display_name, provenance, sources) VALUES "
        "('x/gpt-5', 'x/gpt-5', 'x', 'gpt', 'X: GPT-5', 'polled', '{}'), "
        "('x/gpt-5.4', 'x/gpt-5.4', 'x', 'gpt', 'X: GPT-5.4', 'polled', '{}'), "
        "('x/fusion', 'x/fusion', 'x', 'fusion', 'X: Fusion', 'polled', '{}')"
    )
    _src(conn, "p1", "arxiv", "Fusion of experts with GPT-5.4", 2)
    by = {m["model"]: m["items"] for m in topics.model_mentions(conn, NOW)}
    assert by == {"x/gpt-5.4": 1}  # not GPT-5 inside GPT-5.4; not the word "Fusion"


def test_shapes_follow_the_number_of_sources():
    assert topics.shape_for(0) is None
    assert topics.shape_for(1) == "explainer with a quiz"
    assert topics.shape_for(topics.config()["synthesis_min_items"]) == "combined article"


def _gsb():
    import importlib.util
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("gsb_topics", root / "generate_sample_blogs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_quiz_answer_must_point_at_an_option():
    g = _gsb()
    ok = {"question": "q?", "options": ["a", "b", "c"], "answer": 2, "explanation": "e"}
    assert g.quiz_violations([ok]) == []
    assert g.quiz_violations([{**ok, "answer": 3}])
    assert g.quiz_violations([{**ok, "answer": True}])  # a bool is not an index
    assert g.quiz_violations([{**ok, "options": ["a", "A", "c"]}])  # not distinct
    assert g.quiz_violations([{**ok, "options": ["a", "b"]}])  # too few


def test_topic_formats_load_and_are_not_board_planned():
    g = _gsb()
    fmts = {f["key"]: f for f in g.load_formats()["formats"]}
    assert fmts["topic-explainer"]["special"] == "quiz"
    assert fmts["topic-synthesis"]["special"] == "glossary"
    assert fmts["topic-explainer"]["blocks"]["voices"] == 1
    assert all(isinstance(f["blocks"]["voices"], int) for f in fmts.values())
    # the topic prompt replaces the practitioner one, and keeps its grounding rules
    sys_prompt = g.system_for(fmts["topic-explainer"])
    assert "learning about AI" in sys_prompt and "GROUNDING" in sys_prompt and "QUIZ:" in sys_prompt


def test_quiz_options_are_checked_as_prose():
    g = _gsb()
    item = {"question": "q?", "options": ["fine", "it rose 97%"], "answer": 0, "explanation": "e"}
    essay = {"quiz": [item]}
    paths = dict(g.prose_fields(essay))
    assert paths["quiz[0].options[1]"] == "it rose 97%"  # so the number check sees it


def test_every_topic_format_states_its_source_range_and_block():
    g = _gsb()
    fmts = [f for f in g.load_formats()["formats"] if f["subject"] == "concept"]
    assert len({f["special"] for f in fmts}) == len(fmts)  # one block per style
    assert sum(f["special"] == "quiz" for f in fmts) == 1  # the quiz is one style of many
    for f in fmts:
        lo, hi = f["sources"]
        assert 1 <= lo <= hi and f["blocks"]["voices"] <= hi, f["key"]


def test_a_special_items_source_must_be_a_source_in_the_pack():
    g = _gsb()
    fmt = next(f for f in g.load_formats()["formats"] if f["key"] == "research-radar")
    rules = g.rules_for(fmt, "x") | {"n_sources": 2}
    item = {"item": "a", "what": "b", "why": "c", "stage": "new idea", "source": 3}
    v = g._distinctiveness({"sections": [], "radar": [item]}, rules)
    assert any("radar[0].source" in x for x in v)
    v = g._distinctiveness({"sections": [], "radar": [item | {"source": 2}]}, rules)
    assert not any("radar[0].source" in x for x in v)


def test_export_links_a_special_item_to_its_source():
    g = _gsb()
    post = {"format_cfg": {"special": "results"}}
    docs = [{"source": "arxiv", "url": "https://arxiv.org/abs/1", "title": "Paper one"}]
    essay = {"results": [{"result": "r", "setup": "s", "source": 1}]}
    sp = g._export_special(post, essay, lambda t: t, docs)
    ref = {"title": "Paper one", "url": "https://arxiv.org/abs/1", "platform": "arXiv"}
    assert sp["items"][0]["ref"] == ref
