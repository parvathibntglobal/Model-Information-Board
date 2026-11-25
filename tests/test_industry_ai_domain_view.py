"""One domain's page (judge/industry_ai/view.py `industry_ai_domain_view`; #665 review,
point 4), on the disposable test database (TEST_DATABASE_URL).

The labels are written straight into `iai_item`, so these tests pin the PAGE's SQL,
not the rules that would have chosen the labels. What they pin:
  * the two tabs (kept, filtered out) never overlap, "kept" matches the summary card,
    and a watch-list post filed here by its words is in neither (it is on AI Watch);
  * a post waiting for its labels (#663: verdict 'dropped', drop_stage 'pending') is
    in no tab, and never counted as filtered out;
  * a filter narrows both the posts and the breakdowns;
  * a post whose text retention cleared comes back with no excerpt and its date, and
    a Hacker News item with no title left is "unknown", never guessed a comment;
  * a long post is cut at EXCERPT_CHARS, a short one is shown whole;
  * an unknown domain or a bad tab is refused.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from collect.industry_ai.rules import Item

NOW = datetime.now(UTC)
D = "marketing"


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


def _item(iid, *, title="", body="", hints=(D,), days=1):
    platform, external = iid.split(":", 1)
    return Item(
        id=iid,
        platform=platform,
        external_id=external,
        url=f"https://e.x/{iid}",
        title=title,
        body=body,
        created_at=NOW - timedelta(days=days),
        author_id=f"a-{iid}",
        engagement={"likes": 3},
        domain_hints=set(hints),
        query_keys={f"iai:{D}:{platform}:q"},
    )


def _label(
    conn,
    iid,
    *,
    verdict="kept",
    stage=None,
    reason=None,
    domains=(D,),
    flags=(),
    content_type="discussion",
    terms=("ad copy",),
    ai=("ChatGPT",),
):
    conn.execute(
        "UPDATE iai_item SET verdict = %s, drop_stage = %s, drop_reason = %s, domains = %s, "
        "flags = %s, content_type = %s, matched_terms = %s, ai_terms = %s WHERE id = %s",
        (
            verdict,
            stage,
            reason,
            list(domains),
            list(flags),
            content_type,
            json.dumps({D: {"terms": list(terms), "groups": {}}}),
            list(ai),
            iid,
        ),
    )


@pytest.fixture
def page(conn):
    """Six posts under one domain, one of each case the page must keep apart."""
    from collect.industry_ai import store

    store.start_run(
        conn, "iai-dv", mode="harvest", domains=[D], platforms=["reddit"], pipeline_version="test"
    )
    long_body = "We used ChatGPT to draft our ad copy. " * 40  # well over EXCERPT_CHARS
    store.upsert_items(
        conn,
        [
            _item("reddit:t3_k1", title="Ad copy with ChatGPT", body=long_body),
            _item("x:k2", body="Short post: ChatGPT wrote our ad copy."),
            _item("hackernews:c1", title="", body="An old post about ad copy and ChatGPT."),
            _item("bluesky:w1", body="Watched: ChatGPT for ad copy.", hints=()),
            _item("reddit:t3_d1", title="Ad copy tips", body="No AI named here at all."),
            _item("reddit:t3_p1", title="Saved, not yet labelled", body="ChatGPT ad copy."),
        ],
        run_id="iai-dv",
    )
    _label(conn, "reddit:t3_k1")
    _label(conn, "x:k2", content_type="how_to")
    _label(conn, "hackernews:c1")
    _label(conn, "bluesky:w1", flags=(f"domain_from_terms:{D}",))
    _label(
        conn,
        "reddit:t3_d1",
        verdict="dropped",
        stage="sieve",
        reason="no_ai_term",
        domains=(),
        content_type=None,
        ai=(),
    )
    # What #663 leaves behind when labelling fails: never filtered out.
    _label(
        conn,
        "reddit:t3_p1",
        verdict="dropped",
        stage="pending",
        reason="not_labelled",
        domains=(),
        content_type=None,
        ai=(),
    )
    conn.execute(
        "UPDATE iai_item SET title = '', body = '', text_cleared_at = now() "
        "WHERE id = 'hackernews:c1'"
    )
    conn.commit()
    return conn


def _view(conn, **kw):
    from judge.industry_ai.view import industry_ai_domain_view

    return industry_ai_domain_view(conn, D, **kw)


def _ids(view):
    return {it["id"] for it in view["items"]}


def test_the_tabs_never_overlap_and_match_the_card(page):
    from judge.industry_ai.view import industry_ai_view

    kept, dropped = (_view(page, scope=s) for s in ("kept", "dropped"))
    assert kept["scopes"] == {"kept": 3, "dropped": 1}
    assert _ids(kept) == {"reddit:t3_k1", "x:k2", "hackernews:c1"}
    assert _ids(dropped) == {"reddit:t3_d1"}
    assert not _ids(kept) & _ids(dropped)
    assert "bluesky:w1" not in _ids(kept) | _ids(dropped), "filed by its words: on AI Watch"

    card = {d["key"]: d for d in industry_ai_view(page)["domains"]}[D]
    assert card["kept"] == kept["scopes"]["kept"]


def test_a_post_waiting_for_its_labels_is_never_filtered_out(page):
    dropped = _view(page, scope="dropped")
    assert "reddit:t3_p1" not in _ids(dropped)
    assert [r["value"] for r in dropped["facets"]["reason"]] == ["no_ai_term"]
    assert dropped["matching"] == 1


def test_a_filter_narrows_the_posts_and_the_breakdowns(page):
    view = _view(page, filters={"platform": "reddit"})
    assert _ids(view) == {"reddit:t3_k1"} and view["matching"] == 1
    assert [r["value"] for r in view["facets"]["platform"]] == ["reddit"]
    assert [r["value"] for r in view["facets"]["type"]] == ["discussion"]
    assert _view(page, filters={"type": "how_to"})["matching"] == 1
    assert _view(page, filters={"term": "ad copy"})["matching"] == 3
    assert _view(page, filters={"q": "100%_off"})["matching"] == 0, "% and _ are literal"


def test_a_cleared_post_has_no_text_and_an_untitled_hn_item_is_unknown(page):
    c1 = {it["id"]: it for it in _view(page)["items"]}["hackernews:c1"]
    assert c1["text_cleared_at"] and c1["excerpt"] == "" and c1["title"] == ""
    assert c1["kind"] == "unknown", "no title left: never guessed a comment (rule 6)"
    assert _view(page)["text_cleared"] == 1


def test_a_long_post_is_cut_and_a_short_one_shown_whole(page):
    from judge.industry_ai.view import EXCERPT_CHARS

    items = {it["id"]: it for it in _view(page)["items"]}
    assert (
        len(items["reddit:t3_k1"]["excerpt"]) == EXCERPT_CHARS
        and items["reddit:t3_k1"]["excerpt_cut"]
    )
    assert items["x:k2"]["excerpt"] == "Short post: ChatGPT wrote our ad copy."
    assert not items["x:k2"]["excerpt_cut"]
    assert items["reddit:t3_k1"]["kind"] == "post" and items["x:k2"]["kind"] == "post"


def test_an_unknown_domain_or_a_bad_tab_is_refused(page):
    from judge.industry_ai.view import BadFilter, DomainNotFound, industry_ai_domain_view

    with pytest.raises(DomainNotFound):
        industry_ai_domain_view(page, "no_such_domain")
    with pytest.raises(BadFilter):
        _view(page, scope="everything")
    with pytest.raises(BadFilter):
        _view(page, scope="from_watch")
    with pytest.raises(DomainNotFound):
        industry_ai_domain_view(page, "general")  # General AI is on AI Watch (2026-11-25)
