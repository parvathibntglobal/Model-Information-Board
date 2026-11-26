"""Media a post carries, and "not readable" (2026-11-25, iai-5).

The lane reads words only. These pin:
  * each platform's media kind is read from the provider's own fields, as measured on
    2026-11-25 (collect/industry_ai/media.py), and an unknown shape is None, never
    "none" (rule 6);
  * a picture or video with too few words to judge is stored as drop_stage `unread`,
    not dropped as "no AI term" / "too short"; a post with no recorded media is judged
    on its text as before;
  * the store keeps the kind, fills it on a later sighting and never overwrites it;
  * the pages count `unread` apart from "filtered out" (rule 4), and AI Watch lists it.
The last two use the disposable test database.
"""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta

import pytest
import yaml

from collect.industry_ai import config as iai_config
from collect.industry_ai import media
from collect.industry_ai.config import CONTRACT, IndustryAIConfigError
from collect.industry_ai.pipeline import evaluate
from collect.industry_ai.rules import Item, too_little_to_read

NOW = datetime.now(UTC)
REDDIT_KEY = "watch:reddit:r/ClaudeAI"  # in contract/industry_ai.yaml watch.reddit


@pytest.fixture(scope="module")
def raw():
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cfg(raw):
    return iai_config.parse(raw)


# ── what each platform says it carries ───────────────────────────────────────


@pytest.mark.parametrize("node, kind", [
    ({"__typename": "GraphVideo", "is_video": True, "product_type": "clips"}, "video"),
    ({"__typename": "GraphSidecar", "is_video": False}, "gallery"),
    ({"__typename": "GraphImage", "is_video": False}, "image"),
    ({"__typename": "GraphSomethingNew"}, None),
])
def test_instagram_reads_the_node_type(node, kind):
    assert media.instagram(node) == kind


@pytest.mark.parametrize("raw_post, kind", [
    ({"is_self": True, "post_hint": "self"}, "none"),
    ({"post_hint": "image", "url": "https://i.redd.it/a.jpg"}, "image"),
    ({"is_gallery": True, "url": "https://www.reddit.com/gallery/x"}, "gallery"),
    ({"is_video": True, "post_hint": "hosted:video"}, "video"),
    ({"post_hint": "rich:video", "url": "https://youtu.be/x"}, "video"),
    ({"post_hint": "link", "url": "https://example.org/a"}, "link"),
    # A crosspost carries its parent's media: the child reads as a bare link.
    ({"url": "/r/a/comments/1", "crosspost_parent_list": [{"is_video": True}]}, "video"),
    ({}, None),
])
def test_reddit_reads_its_hints_and_a_crossposts_parent(raw_post, kind):
    assert media.reddit(raw_post) == kind


def _tweet(media_types=(), card=False, wrap=False, quoted_media=False):
    t = {"legacy": {"full_text": "x", "extended_entities": {
        "media": [{"type": m} for m in media_types]}} if media_types else {"full_text": "x"}}
    if card:
        t["card"] = {"legacy": {}}
    if quoted_media:
        t["quoted_status_result"] = {"result": {"legacy": {"extended_entities": {
            "media": [{"type": "video"}]}}}}
    return json.dumps({"__typename": "TweetWithVisibilityResults", "tweet": t} if wrap else t)


@pytest.mark.parametrize("payload, kind", [
    (_tweet(), "none"),
    (_tweet(["photo"]), "image"),
    (_tweet(["photo", "photo"]), "gallery"),
    (_tweet(["photo", "video"]), "video"),
    (_tweet(["animated_gif"]), "video"),
    (_tweet(card=True), "link"),
    (_tweet(["photo"], wrap=True), "image"),
    # A quoted post's media is that post's, not this one's.
    (_tweet(quoted_media=True), "none"),
    ("not json", None),
    (json.dumps({"rest_id": "1"}), None),
])
def test_x_reads_its_own_media_from_the_payload(payload, kind):
    assert media.x(payload) == kind


@pytest.mark.parametrize("post, kind", [
    ({}, None),
    ({"embed": None, "uri": "at://x"}, "none"),
    ({"embed": {"$type": "app.bsky.embed.images#view", "images": [{"alt": "a"}]}}, "image"),
    ({"embed": {"$type": "app.bsky.embed.images#view", "images": [{}, {}]}}, "gallery"),
    ({"embed": {"$type": "app.bsky.embed.video#view"}}, "video"),
    ({"embed": {"$type": "app.bsky.embed.external#view"}}, "link"),
    ({"embed": {"$type": "app.bsky.embed.record#view"}}, "none"),
    ({"embed": {"$type": "app.bsky.embed.recordWithMedia#view",
                "media": {"$type": "app.bsky.embed.video#view"}}}, "video"),
    ({"embed": {"$type": "app.bsky.embed.somethingNew#view"}}, None),
])
def test_bluesky_reads_the_embed_type(post, kind):
    assert media.bluesky(post) == kind


def test_hacker_news_is_a_link_or_text():
    assert media.hackernews({"title": "t", "url": "https://e.org"}) == "link"
    assert media.hackernews({"title": "Ask HN", "story_text": "body"}) == "none"
    assert media.hackernews({"comment_text": "c"}) == "none"


def test_the_table_and_the_migration_accept_exactly_these_kinds():
    import re

    for path in (CONTRACT.parent / "tables.sql",
                 CONTRACT.parent / "migrations" / "20261125T1600_iai_item_media_kind.sql"):
        sql = path.read_text(encoding="utf-8")
        check = re.search(r"iai_item_media_kind_ck\s+CHECK \(media_kind IS NULL OR media_kind IN "
                          r"\(([^)]*)\)\)", sql)
        assert check, path.name
        assert re.findall(r"'([a-z]+)'", check.group(1)) == list(media.MEDIA_KINDS), path.name


# ── not readable ─────────────────────────────────────────────────────────────


def post(text, kind, *, keys=(REDDIT_KEY,), iid="1"):
    return Item(id=f"instagram:{iid}", platform="instagram", external_id=iid,
                url=f"https://www.instagram.com/p/{iid}/", title="", body=text,
                created_at=NOW - timedelta(hours=12), author_id="a", engagement={"likes": 50},
                query_keys=set(keys), media_kind=kind)


def test_a_short_caption_on_a_video_is_too_little_to_read(cfg):
    limit = int(cfg.run["unread_media_max_chars"])
    assert too_little_to_read(post("Watch this one 🔥 #tech #reels @someone", "video"), cfg)
    assert not too_little_to_read(post("x" * (limit + 5), "video"), cfg)
    # Links, handles and tags are not words about anything.
    assert too_little_to_read(post("https://example.org/a-very-long-link-to-somewhere "
                                   "#one #two #three #four #five @a @b", "image"), cfg)
    # Only a picture or a video: a link card and an unknown are judged on their text.
    assert not too_little_to_read(post("short", "link"), cfg)
    assert not too_little_to_read(post("short", "none"), cfg)
    assert not too_little_to_read(post("short", None), cfg)


def test_a_video_with_no_ai_term_is_not_readable_not_filtered(cfg):
    it = post("New edit is up, link in bio", "video", iid="v")
    plain = post("New edit is up, link in bio", None, iid="n")
    results, counts = evaluate([it, plain], cfg, since=NOW - timedelta(days=90), now=NOW)
    r = results[it.id]
    assert (r.verdict, r.stage, r.reason) == ("dropped", "unread", "media_unread")
    p = results[plain.id]
    assert (p.verdict, p.stage, p.reason) == ("dropped", "sieve", "no_ai_term")
    # The run log names the stage, so "not readable" is never read as a filter's drop.
    assert counts["dropped"]["unread:media_unread"] == 1
    assert counts["dropped"]["sieve:no_ai_term"] == 1


def test_a_video_whose_caption_names_ai_is_judged_as_before(cfg):
    it = post("Testing ChatGPT on a real brief for my agency clients this week, full run "
              "through of the prompts and what it got wrong", "video", iid="w")
    results, _ = evaluate([it], cfg, since=NOW - timedelta(days=90), now=NOW)
    assert results[it.id].stage != "unread"


def test_the_limit_is_required_and_whole(raw):
    for value in (None, 0, "80", True):
        bad = copy.deepcopy(raw)
        if value is None:
            del bad["run"]["unread_media_max_chars"]
        else:
            bad["run"]["unread_media_max_chars"] = value
        with pytest.raises(IndustryAIConfigError):
            iai_config.parse(bad)


# ── stored, and counted apart ────────────────────────────────────────────────


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


def test_the_kind_is_stored_filled_later_and_never_overwritten(conn):
    from collect.industry_ai import store

    store.start_run(conn, "iai-m", mode="harvest", domains=[], platforms=["instagram"],
                    pipeline_version="test")
    store.upsert_items(conn, [post("a", "video", iid="1"), post("b", None, iid="2")],
                       run_id="iai-m")
    # Seen again: the unknown is filled, the recorded kind kept.
    store.upsert_items(conn, [post("a", "image", iid="1"), post("b", "gallery", iid="2")],
                       run_id="iai-m")
    conn.commit()
    kinds = dict(conn.execute("SELECT id, media_kind FROM iai_item").fetchall())
    assert kinds == {"instagram:1": "video", "instagram:2": "gallery"}
    assert {it.id: it.media_kind for it in store.load_items(conn)} == kinds
    with pytest.raises(Exception, match="media_kind"):
        conn.execute("UPDATE iai_item SET media_kind = 'audio'")


def test_the_pages_count_not_readable_apart_from_filtered_out(conn):
    from collect.industry_ai import store
    from judge.industry_ai.view import ai_watch_posts, ai_watch_view

    store.start_run(conn, "iai-m", mode="harvest", domains=[], platforms=["reddit"],
                    pipeline_version="test")
    items = [post("a", "video", iid="u"), post("b", None, iid="d"), post("c", None, iid="k")]
    for it in items:
        it.platform, it.id = "reddit", it.id.replace("instagram:", "reddit:")
    store.upsert_items(conn, items, run_id="iai-m")
    for iid, verdict, stage, reason, flags in (
        ("reddit:u", "dropped", "unread", "media_unread", []),
        ("reddit:d", "dropped", "sieve", "no_ai_term", []),
        ("reddit:k", "kept", None, None, ["general_ai"]),
    ):
        conn.execute("UPDATE iai_item SET verdict = %s, drop_stage = %s, drop_reason = %s, "
                     "flags = %s WHERE id = %s", (verdict, stage, reason, flags, iid))
    conn.commit()

    w = ai_watch_view(conn)
    assert (w["collected"], w["kept"], w["filtered"], w["unread"]) == (3, 1, 1, 1)
    assert w["unread_by_media"] == {"video": 1}
    assert [d["reason"] for d in w["dropped"]] == ["no_ai_term"]
    src = next(s for s in w["sources"] if s.get("key") == REDDIT_KEY)
    assert src["found"] == src["kept"] + src["filtered"] + src["waiting"] + src["unread"] == 3
    assert [i["id"] for i in ai_watch_posts(conn, scope="unread")["items"]] == ["reddit:u"]
    assert "reddit:u" not in {i["id"] for i in ai_watch_posts(conn, scope="dropped")["items"]}
