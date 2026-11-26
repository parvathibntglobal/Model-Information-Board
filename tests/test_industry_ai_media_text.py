"""The text that comes with a post's media (#679 step 1, anooj, 2026-11-26; iai-6).

Words the provider already sends beside a post that are not the author's own: a
picture's alt text, the text of a quoted post, a Reddit crosspost's original. These pin:
  * each platform's reader takes exactly those fields, and finding nothing is None,
    never "" (rule 6);
  * the AI-term and industry-term matching and the "too little to read" check read
    them (`judged_text`); the filters, the label, the duplicate keys and the pages
    keep the author's own words (`Item.text`);
  * a post that passes ONLY because of them is flagged `terms_from_media_text`, so a
    reader can count and check those (rule 8: a weight, not a gate);
  * the store keeps them, fills a NULL on a later sighting, never overwrites, and
    retention clears them with the title and body and never brings them back;
  * the table and the migration accept exactly the three kinds.
The store tests use the disposable test database.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta

import pytest
import yaml

from collect.industry_ai import config as iai_config
from collect.industry_ai import media
from collect.industry_ai.config import CONTRACT
from collect.industry_ai.pipeline import evaluate
from collect.industry_ai.rules import (
    MEDIA_TEXT_FLAG,
    Item,
    judged_text,
    media_text_changed_filing,
    needed_media_text,
    sieve,
    too_little_to_read,
)

NOW = datetime.now(UTC)
REDDIT_KEY = "watch:reddit:r/ClaudeAI"  # in contract/industry_ai.yaml watch.reddit

#: Plain English with no AI term, long enough to be read on its own.
NO_AI = ("Sharing this one from earlier in the week, worth a read for anyone who runs "
         "an operations team and plans the rota by hand every month")
#: The same length of English that names an AI tool and what it was used for.
WITH_AI = ("I used ChatGPT to draft the monthly rota for our operations team and it got "
           "the weekend cover wrong twice before it settled")


@pytest.fixture(scope="module")
def cfg():
    return iai_config.parse(yaml.safe_load(CONTRACT.read_text(encoding="utf-8")))


# ── the readers ──────────────────────────────────────────────────────────────


def _tweet(alts=(), quoted=None, long_quote=None, wrap=False):
    t: dict = {"legacy": {"full_text": "own words"}}
    if alts:
        t["legacy"]["extended_entities"] = {
            "media": [{"type": "photo", **({"ext_alt_text": a} if a is not None else {})}
                      for a in alts]}
    if quoted is not None or long_quote is not None:
        q: dict = {"legacy": {"full_text": quoted}}
        if long_quote:
            q["note_tweet"] = {"note_tweet_results": {"result": {"text": long_quote}}}
        t["quoted_status_result"] = {"result": {"__typename": "TweetWithVisibilityResults",
                                                "tweet": q} if wrap else q}
    return json.dumps(t)


@pytest.mark.parametrize("payload, found", [
    (_tweet(), (None, [])),
    (_tweet(alts=["A chart of  token\ncosts"]), ("A chart of token costs", ["alt_text"])),
    # An empty or absent alt text is nothing found, not an empty finding.
    (_tweet(alts=["", None, "   "]), (None, [])),
    (_tweet(quoted="the quoted post"), ("the quoted post", ["quoted_post"])),
    # A long quoted post is read whole from note_tweet, not its cut-off full_text.
    (_tweet(quoted="cut off…", long_quote="the whole long post"),
     ("the whole long post", ["quoted_post"])),
    (_tweet(quoted="wrapped quote", wrap=True), ("wrapped quote", ["quoted_post"])),
    (_tweet(alts=["alt"], quoted="quote"), ("alt\nquote", ["alt_text", "quoted_post"])),
    ("not json", (None, [])),
    (None, (None, [])),
])
def test_x_reads_alt_text_and_the_quoted_post(payload, found):
    assert media.x_text(payload) == found


def test_x_does_not_read_its_own_words_as_media_text():
    assert media.x_text(json.dumps({"legacy": {"full_text": "own words only"}})) == (None, [])


@pytest.mark.parametrize("post, found", [
    ({}, (None, [])),
    ({"embed": None}, (None, [])),
    ({"embed": {"$type": "app.bsky.embed.images#view",
                "images": [{"alt": "a diagram"}, {"alt": ""}]}},
     ("a diagram", ["alt_text"])),
    ({"embed": {"$type": "app.bsky.embed.record#view",
                "record": {"value": {"text": "the quoted skeet"}}}},
     ("the quoted skeet", ["quoted_post"])),
    ({"embed": {"$type": "app.bsky.embed.recordWithMedia#view",
                "media": {"$type": "app.bsky.embed.images#view", "images": [{"alt": "pic"}]},
                "record": {"record": {"value": {"text": "quoted"}}}}},
     ("pic\nquoted", ["alt_text", "quoted_post"])),
    # A quote of something that is not a post (a list, a feed) carries no `value`.
    ({"embed": {"$type": "app.bsky.embed.record#view", "record": {"name": "a list"}}},
     (None, [])),
    ({"embed": {"$type": "app.bsky.embed.video#view", "alt": None}}, (None, [])),
])
def test_bluesky_reads_alt_text_and_the_quoted_post(post, found):
    assert media.bluesky_text(post) == found


@pytest.mark.parametrize("raw_post, found", [
    ({}, (None, [])),
    ({"selftext": "own body"}, (None, [])),
    ({"crosspost_parent_list": [{"title": "Parent title", "selftext": "parent body"}]},
     ("Parent title parent body", ["crosspost_parent"])),
    ({"crosspost_parent_list": [{"title": "Only a title", "selftext": ""}]},
     ("Only a title", ["crosspost_parent"])),
    ({"crosspost_parent_list": [{"title": "", "selftext": ""}]}, (None, [])),
    ({"crosspost_parent_list": ["not a dict"]}, (None, [])),
])
def test_reddit_reads_a_crossposts_parent(raw_post, found):
    assert media.reddit_text(raw_post) == found


def test_the_harvest_builders_carry_none_when_nothing_was_found():
    from collect.industry_ai.harvest import _with_media_text

    assert _with_media_text((None, [])) == {"media_text": None, "media_text_from": ()}
    got = _with_media_text(("an alt text", ["alt_text"]))
    assert got == {"media_text": "an alt text", "media_text_from": ("alt_text",)}


def test_the_table_and_the_migration_accept_exactly_these_kinds():
    for path in (CONTRACT.parent / "tables.sql",
                 CONTRACT.parent / "migrations" / "20261126T0900_iai_item_media_text.sql"):
        sql = path.read_text(encoding="utf-8")
        check = re.search(r"iai_item_media_text_from_ck\s+CHECK \(media_text_from IS NULL\s+"
                          r"OR media_text_from <@ ARRAY\[([^\]]*)\]", sql)
        assert check, path.name
        assert tuple(re.findall(r"'([a-z_]+)'", check.group(1))) == media.MEDIA_TEXT_KINDS, \
            path.name


# ── what reads it ────────────────────────────────────────────────────────────


def post(text, *, media_text=None, kinds=(), kind=None, iid="1"):
    return Item(id=f"reddit:{iid}", platform="reddit", external_id=iid,
                url=f"https://www.reddit.com/{iid}", title="", body=text,
                created_at=NOW - timedelta(hours=12), author_id=f"t2_{iid}",
                engagement={"score": 50}, query_keys={REDDIT_KEY}, media_kind=kind,
                media_text=media_text, media_text_from=tuple(kinds))


def test_the_author_words_stay_apart_from_the_media_text():
    it = post("own words", media_text="quoted words", kinds=["quoted_post"])
    assert it.text == "own words"
    assert judged_text(it) == "own words\nquoted words"
    assert judged_text(post("own words")) == "own words"


def test_terms_in_the_media_text_reach_the_sieve(cfg):
    alone = post(NO_AI)
    with_quote = post(NO_AI, media_text=WITH_AI, kinds=["quoted_post"])
    assert sieve(alone, cfg)[0] == "no_ai_term"
    assert sieve(with_quote, cfg)[0] is None
    assert needed_media_text(with_quote, cfg)
    # Its own words already pass: the media text was not needed.
    assert not needed_media_text(post(WITH_AI, media_text=NO_AI, kinds=["alt_text"]), cfg)
    assert not needed_media_text(alone, cfg)


def test_a_post_through_on_its_media_text_is_flagged_and_others_are_not(cfg):
    through = post(NO_AI, media_text=WITH_AI, kinds=["quoted_post"], iid="q")
    own = post(WITH_AI.replace("monthly", "weekly"), iid="o")
    dropped = post(NO_AI, iid="d")
    results, _ = evaluate([through, own, dropped], cfg, since=NOW - timedelta(days=90), now=NOW)
    assert results[through.id].reason != "no_ai_term"
    assert MEDIA_TEXT_FLAG in results[through.id].flags
    assert MEDIA_TEXT_FLAG not in results[own.id].flags
    assert (results[dropped.id].stage, results[dropped.id].reason) == ("sieve", "no_ai_term")


def test_a_picture_with_an_alt_text_has_something_to_read(cfg):
    caption = "New one up 🔥 #tech"
    assert too_little_to_read(post(caption, kind="image"), cfg)
    assert not too_little_to_read(
        post(caption, kind="image", media_text=WITH_AI, kinds=["alt_text"]), cfg)


# ── stored ───────────────────────────────────────────────────────────────────


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


def _stored(conn):
    return dict((r[0], (r[1], r[2])) for r in conn.execute(
        "SELECT id, media_text, media_text_from FROM iai_item ORDER BY id").fetchall())


def test_the_media_text_is_stored_filled_later_and_never_overwritten(conn):
    from collect.industry_ai import store

    store.start_run(conn, "iai-mt", mode="harvest", domains=[], platforms=["reddit"],
                    pipeline_version="test")
    store.upsert_items(conn, [post("a", media_text="first", kinds=["quoted_post"], iid="1"),
                              post("b", iid="2")], run_id="iai-mt")
    store.upsert_items(conn, [post("a", media_text="second", kinds=["alt_text"], iid="1"),
                              post("b", media_text="found later", kinds=["crosspost_parent"],
                                   iid="2")], run_id="iai-mt")
    conn.commit()
    assert _stored(conn) == {"reddit:1": ("first", ["quoted_post"]),
                             "reddit:2": ("found later", ["crosspost_parent"])}
    loaded = {it.id: (it.media_text, it.media_text_from) for it in store.load_items(conn)}
    assert loaded == {"reddit:1": ("first", ("quoted_post",)),
                      "reddit:2": ("found later", ("crosspost_parent",))}
    with pytest.raises(Exception, match="media_text_from"):
        conn.execute("UPDATE iai_item SET media_text_from = ARRAY['caption']")


def test_retention_clears_it_and_a_reharvest_does_not_bring_it_back(conn, cfg):
    from collect.industry_ai import store

    store.start_run(conn, "iai-mt", mode="harvest", domains=[], platforms=["reddit"],
                    pipeline_version="test")
    store.upsert_items(conn, [post("a", media_text="words", kinds=["alt_text"], iid="1"),
                              post("b", iid="2")], run_id="iai-mt")
    old = NOW - timedelta(days=int(cfg.retention["clear_text_after_days"]) + 1)
    conn.execute("UPDATE iai_item SET verdict = 'dropped', drop_stage = 'filter', "
                 "drop_reason = 'spam', first_seen_at = %s", (old,))
    conn.commit()
    assert store.clear_text(conn, cfg.retention, now=NOW) == 2
    conn.commit()
    # Cleared is '' and not-found stays NULL: the two never read as one (rule 6).
    assert _stored(conn) == {"reddit:1": ("", ["alt_text"]), "reddit:2": (None, None)}

    store.upsert_items(conn, [post("a", media_text="words", kinds=["alt_text"], iid="1"),
                              post("b", media_text="new", kinds=["quoted_post"], iid="2")],
                       run_id="iai-mt")
    conn.commit()
    assert _stored(conn) == {"reddit:1": ("", ["alt_text"]), "reddit:2": (None, None)}


# ── filed elsewhere, and what the page says (#680 review, 2026-11-26) ───────────

HOSPITAL = ("I use ChatGPT to draft patient discharge summaries at our hospital every "
            "shift now")
BANK = ("Our bank uses it for loan underwriting and fraud detection on every credit card "
        "application")


def _filed(keys, hints=frozenset()):
    return Item(id="reddit:f", platform="reddit", external_id="f",
                url="https://www.reddit.com/f", title="", body=HOSPITAL,
                created_at=NOW - timedelta(hours=12), author_id="t2_f",
                engagement={"score": 50}, query_keys=set(keys), domain_hints=set(hints),
                media_text=BANK, media_text_from=("quoted_post",))


def test_a_watched_post_filed_under_a_domain_only_its_quote_names_is_flagged(cfg):
    it = _filed({REDDIT_KEY})
    why, matched, _ = sieve(it, cfg)
    assert why is None and {"healthcare", "finance"} <= set(matched)
    # Its own words pass, so the "let through" check cannot see it ...
    assert not needed_media_text(it, cfg)
    # ... but the quoted post files it under finance as well, and that is flagged.
    assert media_text_changed_filing(it, matched, cfg)
    results, _ = evaluate([it], cfg, since=NOW - timedelta(days=90), now=NOW)
    r = results[it.id]
    assert "finance" in r.domains and MEDIA_TEXT_FLAG in r.flags


def test_a_keyword_post_whose_filing_does_not_change_is_not_flagged(cfg):
    """A keyword post is filed under the domain its query was for, confirmed by its own
    words; the quote's domain is only an `also_matches` note, so nothing moved."""
    it = _filed({"iai:healthcare:reddit:discharge summaries"}, {"healthcare"})
    _, matched, _ = sieve(it, cfg)
    assert not media_text_changed_filing(it, matched, cfg)
    results, _ = evaluate([it], cfg, since=NOW - timedelta(days=90), now=NOW)
    assert results[it.id].domains == ["healthcare"]
    assert MEDIA_TEXT_FLAG not in results[it.id].flags


def test_no_media_text_changes_nothing(cfg):
    it = post(WITH_AI)
    assert not media_text_changed_filing(it, sieve(it, cfg)[1], cfg)


def test_the_post_card_names_the_flag_and_every_kind():
    """The page explains a flagged post in words (posts.jsx MatchedInMedia). Its copy of
    the flag name and its labels must follow the rules' (judge never imports collect)."""
    src = (CONTRACT.parent.parent / "web" / "src" / "industry-ai" / "posts.jsx").read_text(
        encoding="utf-8")
    assert f"export const MEDIA_TEXT_FLAG = '{MEDIA_TEXT_FLAG}'" in src
    block = src[src.index("const MEDIA_TEXT_LABEL = {"):]
    block = block[:block.index("}")]
    assert tuple(re.findall(r"^\s*([a-z_]+):", block, re.M)) == media.MEDIA_TEXT_KINDS
    assert "<MatchedInMedia it={it} />" in src


def test_the_page_payload_carries_which_text_was_matched(conn):
    from collect.industry_ai import store
    from judge.industry_ai.view import ai_watch_posts

    store.start_run(conn, "iai-mt", mode="harvest", domains=[], platforms=["reddit"],
                    pipeline_version="test")
    store.upsert_items(conn, [post("a", media_text="words", kinds=["quoted_post"], iid="1"),
                              post("b", iid="2")], run_id="iai-mt")
    kept = "verdict = 'kept', drop_stage = NULL, drop_reason = NULL"
    conn.execute(f"UPDATE iai_item SET {kept}, flags = %s WHERE id = 'reddit:1'",
                 ([MEDIA_TEXT_FLAG],))
    conn.execute(f"UPDATE iai_item SET {kept}, flags = '{{}}' WHERE id = 'reddit:2'")
    conn.commit()
    got = {i["id"]: (i["flags"], i["media_text_from"])
           for i in ai_watch_posts(conn, scope="kept")["items"]}
    assert got == {"reddit:1": ([MEDIA_TEXT_FLAG], ["quoted_post"]), "reddit:2": ([], [])}
