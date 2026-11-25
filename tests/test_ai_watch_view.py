"""AI Watch (judge/industry_ai/view.py `ai_watch_view`, `ai_watch_posts`; 2026-11-25),
on the disposable test database (TEST_DATABASE_URL).

Labels are written straight into `iai_item`, so these pin the PAGES' SQL, not the rules
that would have chosen the labels. What they pin:
  * every stored post is on exactly one page: AI in industries when a keyword query
    found it, AI Watch when only watch lists did or it is General AI (rule 7);
  * a watched source's yield counts every post it found, says how many a keyword query
    also found, and lists a source the contract no longer names apart;
  * an X account's yield is read from the handle in each post's link;
  * the post lists' scopes never overlap, filters narrow them, a post waiting for its
    labels (#663) is in none, and a bad scope is refused.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from collect.industry_ai.rules import Item

NOW = datetime.now(UTC)
REDDIT_KEY = "watch:reddit:r/ClaudeAI"  # in contract/industry_ai.yaml watch.reddit
GONE_KEY = "watch:reddit:r/no_longer_watched_here"


@pytest.fixture
def conn(test_dsn):
    from collect.db import apply_schema, connect
    from tests.conftest import assert_disposable, assert_safe_target

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _item(iid, keys, *, url=None, hints=()):
    platform, external = iid.split(":", 1)
    return Item(
        id=iid, platform=platform, external_id=external, url=url or f"https://e.x/{iid}",
        title="", body=f"A post about ChatGPT ({iid}).", created_at=NOW - timedelta(days=1),
        author_id=f"a-{iid}", engagement={"likes": 2}, domain_hints=set(hints),
        query_keys=set(keys),
    )


def _label(conn, iid, *, verdict="kept", stage=None, reason=None, domains=(), flags=()):
    conn.execute(
        "UPDATE iai_item SET verdict = %s, drop_stage = %s, drop_reason = %s, domains = %s, "
        "flags = %s, content_type = 'discussion' WHERE id = %s",
        (verdict, stage, reason, list(domains), list(flags), iid),
    )


@pytest.fixture
def page(conn):
    from collect.industry_ai import store

    store.start_run(conn, "iai-aw", mode="harvest", domains=["marketing"],
                    platforms=["reddit", "x"], pipeline_version="test")
    store.upsert_items(conn, [
        # The keyword agent's: found by a keyword query (and one by a watch list too).
        _item("reddit:t3_k1", ["iai:marketing:reddit:q"], hints=["marketing"]),
        _item("reddit:t3_k2", ["iai:marketing:reddit:q", REDDIT_KEY], hints=["marketing"]),
        # The observer's: General AI, a mention, a drop, a waiting post, a gone source.
        _item("reddit:t3_g1", [REDDIT_KEY]),
        _item("reddit:t3_m1", [REDDIT_KEY]),
        _item("reddit:t3_d1", [REDDIT_KEY]),
        _item("reddit:t3_p1", [REDDIT_KEY]),
        _item("reddit:t3_o1", [GONE_KEY]),
        # An X post from a clubbed watch query, read by the handle in its link.
        _item("x:1", ["watch:x:(from:karpathy OR from:simonw)"],
              url="https://x.com/Karpathy/status/1"),
    ], run_id="iai-aw")
    _label(conn, "reddit:t3_k1", domains=["marketing"])
    _label(conn, "reddit:t3_k2", domains=["marketing"])
    _label(conn, "reddit:t3_g1", flags=["general_ai"])
    _label(conn, "reddit:t3_m1", domains=["marketing"], flags=["domain_from_terms:marketing"])
    _label(conn, "reddit:t3_d1", verdict="dropped", stage="sieve", reason="no_ai_term")
    _label(conn, "reddit:t3_p1", verdict="dropped", stage="pending", reason="not_labelled")
    _label(conn, "reddit:t3_o1", flags=["general_ai"])
    _label(conn, "x:1", flags=["general_ai"])
    conn.commit()
    return conn


def test_every_post_is_on_exactly_one_page(page):
    from judge.industry_ai.view import ai_watch_view, industry_ai_view

    iai, watch = industry_ai_view(page), ai_watch_view(page)
    (total,) = page.execute("SELECT count(*) FROM iai_item").fetchone()
    assert iai["collected"] + watch["collected"] == total == 8
    assert (iai["collected"], iai["kept"]) == (2, 2)
    assert (watch["kept"], watch["general"], watch["mentions"]) == (4, 3, 1)
    assert (watch["filtered"], watch["pending"]) == (1, 1)
    assert watch["mentioned"][0]["key"] == "marketing" and watch["mentioned"][0]["items"] == 1
    assert {d["key"]: d["kept"] for d in iai["domains"]}["marketing"] == 2


def test_a_sources_yield_counts_what_it_found_and_names_a_gone_source(page):
    from judge.industry_ai.view import ai_watch_view

    src = ai_watch_view(page)["sources"]
    claude = next(s for s in src if s.get("key") == REDDIT_KEY)
    # k2 (also found by keyword), g1, m1, d1 and the waiting p1.
    assert (claude["found"], claude["kept"], claude["filtered"], claude["also_keyword"]) == (
        5, 3, 1, 1)
    assert claude["listed"] and claude["source"] == "r/ClaudeAI"
    gone = next(s for s in src if s.get("key") == GONE_KEY)
    assert not gone["listed"] and gone["found"] == 1
    karpathy = next(s for s in src if s.get("account") == "karpathy")
    assert karpathy["listed"] and karpathy["kept"] == 1, "read from the link's handle"
    simonw = next(s for s in src if s.get("account") == "simonw")
    assert simonw["found"] == 0 and simonw["newest"] is None


def test_the_post_lists_never_overlap_and_filters_narrow_them(page):
    from judge.industry_ai.view import WATCH_SCOPES, ai_watch_posts

    ids = {s: {it["id"] for it in ai_watch_posts(page, scope=s)["items"]} for s in WATCH_SCOPES}
    assert ids["general"] == {"reddit:t3_g1", "reddit:t3_o1", "x:1"}
    assert ids["mentions"] == {"reddit:t3_m1"}
    assert ids["kept"] == ids["general"] | ids["mentions"]
    assert ids["dropped"] == {"reddit:t3_d1"}, "a post waiting for its labels is never listed"
    assert not ids["kept"] & ids["dropped"]

    assert ai_watch_posts(page, scope="kept", filters={"platform": "x"})["matching"] == 1
    assert ai_watch_posts(page, scope="kept", filters={"account": "KARPATHY"})["matching"] == 1
    assert ai_watch_posts(page, scope="kept", filters={"source": GONE_KEY})["matching"] == 1
    m = ai_watch_posts(page, scope="mentions", filters={"domain": "marketing"})
    assert m["matching"] == 1 and m["facets"]["domain"] == [{"value": "marketing", "items": 1}]
    assert {s: ai_watch_posts(page, scope=s)["matching"] for s in WATCH_SCOPES} == {
        "general": 3, "mentions": 1, "kept": 4, "dropped": 1}


def test_a_bad_scope_is_refused(page):
    from judge.industry_ai.view import BadFilter, ai_watch_posts

    with pytest.raises(BadFilter):
        ai_watch_posts(page, scope="everything")


def test_admin_counts_each_agents_posts_as_its_page_does(page):
    """Admin's two sections (AI in industries, AI Watch) show each agent's own posts."""
    from judge.industry_ai.view import industry_ai_admin

    arms = industry_ai_admin(page)["arms"]
    assert arms == {"keyword": {"stored": 2, "kept": 2, "pending": 0},
                    "watch": {"stored": 6, "kept": 4, "pending": 1}}
