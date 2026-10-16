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
    _item(conn, "1", "Graph RAG at scale", 2)
    _item(conn, "2", "Retrieval-augmented generation for code", 5)
    _item(conn, "3", "Mixture of experts routing", 3)

    shapes = {p["key"]: p["shape"] for p in topics.plan(conn, NOW)}
    assert shapes == {"rag": "combined article", "moe": "explainer with a quiz"}


def test_emerging_lists_only_phrases_no_topic_covers(conn):
    for i in range(3):
        _item(conn, f"s{i}", f"Speculative sampling trick {i}", 2)
        _item(conn, f"r{i}", f"Retrieval augmented generation variant {i}", 2)
        _item(conn, f"w{i}", f"Weight averaging recipes part {i}", 2)

    phrases = {e["phrase"] for e in topics.emerging(conn, NOW)}
    assert "weight averaging" in phrases
    assert not any("retrieval augmented" in p for p in phrases)  # covered by `rag`


def test_the_admin_routes_exist():
    from judge.app import app

    paths = {(r.path, m) for r in app.routes for m in getattr(r, "methods", ())}
    assert ("/blog-topics", "GET") in paths and ("/blog-topics/harvest", "POST") in paths
