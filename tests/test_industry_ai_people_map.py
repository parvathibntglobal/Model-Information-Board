"""The people map (`watch.people`, 2026-11-24): one person, several handles.

Measured 2026-11-20 over one 7-day window of the X, Bluesky and Hacker News watch
lists: a person counted as one author PER PLATFORM (Ethan Mollick 2, Simon Willison
3), and of 3 same-text cross-posts the dedupe caught 1. These pin:
  * the map is read strictly - never a handle outside the watch lists, never one
    handle for two people, never a person on one platform;
  * how each platform's post finds its handle, and that nothing is guessed;
  * a person's same text on two platforms is folded as `cross_post`;
  * a person is ONE author in `counts` and on the page.
All pure except the last, which uses the disposable test database.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

import pytest
import yaml

from collect.industry_ai import config as iai_config
from collect.industry_ai.config import CONTRACT, IndustryAIConfigError
from collect.industry_ai.pipeline import evaluate
from collect.industry_ai.rules import (
    Item,
    cross_post_text,
    first_link,
    handle_of,
    person_of,
)

NOW = datetime(2026, 11, 24, tzinfo=UTC)
SINCE = NOW - timedelta(days=365)
NEWS = ("A new open LLM was released today with a longer context window and faster "
        "inference for everyone who runs it locally.")
OTHER = ("Spent the afternoon comparing two LLM coding assistants on a real refactor; "
         "the slower one made fewer mistakes overall.")


@pytest.fixture(scope="module")
def raw():
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cfg(raw):
    """The real contract, with a watch window wide enough that a post's age never
    decides these tests: they are about folding a person's posts, not about the
    window. With the contract's own 2 days (2026-11-25) a 100-hour copy would be
    dropped for its age, and "not a cross-post" would pass without being tested."""
    r = copy.deepcopy(raw)
    r["watch"]["lookback_days"] = 30
    return iai_config.parse(r)


def post(platform, iid, text, *, url="", author="a1", keys=(), hours=48):
    # `link` as the harvest sets it for X and Bluesky: the first URL in the text.
    return Item(id=f"{platform}:{iid}", platform=platform, external_id=iid, url=url,
                title="", body=text, created_at=NOW - timedelta(hours=hours),
                author_id=author, engagement={"likes": 10, "points": 10},
                link=first_link(text), domain_hints=set(), query_keys=set(keys))


def x_post(handle, iid, text, **kw):
    return post("x", iid, text, url=f"https://x.com/{handle}/status/{iid}",
                author=kw.pop("author", f"x-{handle}"),
                keys=[f"watch:x:(from:{handle} OR from:someone)"], **kw)


#: Each mapped Bluesky handle's DID, as the contract writes it: a real post by that
#: account carries it as `author_id` (and a `from:` post by ANOTHER DID links no one).
_DIDS = {e["bluesky"]: e["bluesky_did"]
         for e in yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))["watch"]["people"].values()
         if "bluesky_did" in e}


def bsky_post(handle, iid, text, **kw):
    return post("bluesky", iid, text, url=f"https://bsky.app/profile/did:plc:{iid}/post/{iid}",
                author=kw.pop("author", _DIDS.get(handle, f"did:plc:{handle}")),
                keys=[f"watch:bluesky:from:{handle}"], **kw)


# ── the contract ─────────────────────────────────────────────────────────────


def test_the_map_loads_and_every_handle_is_a_watched_one(cfg):
    people = cfg.watch["people"]
    assert len(people) >= 1
    by_handle = cfg.person_by_handle()
    lists = {"x": cfg.watch["x"], "bluesky": cfg.watch["bluesky"],
             "hackernews": cfg.watch["hackernews"]["authors"]}
    for (platform, handle), person in by_handle.items():
        assert handle in {h.lower() for h in lists[platform]}, (platform, handle)
        assert person in people
    assert all(len(hs) >= 2 for hs in people.values())


@pytest.mark.parametrize("mutate, says", [
    (lambda p: p.update(ghost={"x": "nobody_watched", "bluesky": "emollick.bsky.social"}),
     "not in the x watch list"),
    (lambda p: p.update(solo={"x": "karpathy"}), "at least two platforms"),
    (lambda p: p.update(twin={"x": "simonw", "hackernews": "minimaxir"}), "already belongs"),
    (lambda p: p.update(sub={"reddit": "LocalLLaMA", "x": "karpathy"}), "unknown key"),
    (lambda p: p.update({"Bad Key": {"x": "karpathy", "hackernews": "karpathy"}}),
     "person key"),
])
def test_the_map_is_strict(raw, mutate, says):
    bad = copy.deepcopy(raw)
    mutate(bad["watch"]["people"])
    with pytest.raises(IndustryAIConfigError, match=says):
        iai_config.parse(bad)


# ── which handle, which person ───────────────────────────────────────────────


def test_each_platform_names_its_handle_its_own_way(cfg):
    assert handle_of(x_post("EMollick", "1", NEWS)) == "emollick", "from the URL, folded"
    anon = post("x", "2", NEWS, url="https://x.com/i/status/2")
    assert handle_of(anon) is None, "the anonymous URL names nobody"
    assert handle_of(bsky_post("emollick.bsky.social", "3", NEWS)) == "emollick.bsky.social"
    keyword_only = post("bluesky", "4", NEWS, author="did:plc:x", keys=["iai:marketing:bluesky:q"])
    assert handle_of(keyword_only) is None, "a DID is not a handle: no link, never a guess"
    assert handle_of(post("hackernews", "5", NEWS, author="SimonW")) == "simonw"
    assert handle_of(post("reddit", "6", NEWS, author="t2_x")) is None
    assert person_of(x_post("emollick", "7", NEWS), cfg) == "ethan_mollick"
    assert person_of(x_post("not_mapped", "8", NEWS), cfg) is None


def test_mentions_tags_and_links_do_not_stop_a_cross_post_matching():
    a = cross_post_text("New post with @simonw on #LLM evals https://t.co/abc - worth a read")
    b = cross_post_text("New post with @simonwillison.net on evals https://bsky.app/x "
                        "- worth a read")
    assert a == b and a is not None
    assert cross_post_text("thanks @simonw!") is None, "too short to say two posts are one"


# ── dedupe and counts ────────────────────────────────────────────────────────


def test_a_persons_same_text_on_two_platforms_is_one_item(cfg):
    x = x_post("emollick", "10", NEWS + " https://t.co/zz", hours=50)
    b = bsky_post("emollick.bsky.social", "11", NEWS + " https://example.org/post", hours=49)
    results, _ = evaluate([x, b], cfg, since=SINCE, now=NOW)
    kept, copy_ = results[x.id], results[b.id]
    assert kept.verdict == "kept", kept.reason
    assert (copy_.verdict, copy_.reason, copy_.canonical_of) == ("dropped", "cross_post", x.id)
    assert "cross_post" in kept.flags and kept.share_count == 1
    assert "person:ethan_mollick" in kept.flags and "person:ethan_mollick" in copy_.flags


def test_the_same_intro_with_different_links_is_two_posts(cfg):
    """#653 review: one person's template intro for two different papers. When both
    posts carry an article link, the links must match for pass 3 to fold them."""
    x = x_post("emollick", "12", NEWS + " https://example.org/paper-a", hours=50)
    b = bsky_post("emollick.bsky.social", "13", NEWS + " https://example.org/paper-b", hours=49)
    results, _ = evaluate([x, b], cfg, since=SINCE, now=NOW)
    assert "cross_post" not in {results[x.id].reason, results[b.id].reason}


def test_a_same_platform_repeat_is_left_to_pass_two(cfg):
    """#653 review: pass 3 folds across platforms only; a repeat on one platform
    is the same author repeating themselves (pass 2)."""
    a = x_post("emollick", "14", NEWS, hours=50)
    b = x_post("emollick", "15", NEWS, hours=49)
    results, _ = evaluate([a, b], cfg, since=SINCE, now=NOW)
    assert results[b.id].reason == "repeat_post"
    assert "cross_post" not in results[a.id].flags


def test_a_copy_outside_the_window_is_not_a_cross_post(cfg):
    hours = int(cfg.watch["cross_post_hours"])
    x = x_post("emollick", "16", NEWS, hours=100)
    b = bsky_post("emollick.bsky.social", "17", NEWS, hours=100 - hours - 1)
    results, _ = evaluate([x, b], cfg, since=SINCE, now=NOW)
    assert "cross_post" not in {results[x.id].reason, results[b.id].reason}
    # Decided on their text and dates, not aged out of the watch window.
    assert "outside_watch_window" not in {results[x.id].reason, results[b.id].reason}


def test_an_undated_post_is_never_folded_as_a_cross_post(cfg):
    """Rule 6: with no date there is no saying it was posted at the same time."""
    x = x_post("emollick", "18", NEWS)
    b = bsky_post("emollick.bsky.social", "19", NEWS)
    b.created_at = None
    results, _ = evaluate([x, b], cfg, since=SINCE, now=NOW)
    assert "cross_post" not in {results[x.id].reason, results[b.id].reason}


@pytest.mark.parametrize("value", [None, 0, -1, "6", True])
def test_the_cross_post_window_is_required_and_whole(raw, value):
    bad = copy.deepcopy(raw)
    if value is None:
        del bad["watch"]["cross_post_hours"]
    else:
        bad["watch"]["cross_post_hours"] = value
    with pytest.raises(IndustryAIConfigError):
        iai_config.parse(bad)


def test_two_people_saying_the_same_thing_are_not_a_cross_post(cfg):
    a = x_post("emollick", "20", NEWS)
    b = x_post("karpathy", "21", NEWS)
    results, _ = evaluate([a, b], cfg, since=SINCE, now=NOW)
    assert "cross_post" not in {results[a.id].reason, results[b.id].reason}


def test_a_person_is_one_author_however_many_platforms(cfg):
    x = x_post("emollick", "30", NEWS)
    b = bsky_post("emollick.bsky.social", "31", OTHER)
    _, c = evaluate([x, b], cfg, since=SINCE, now=NOW)
    assert c["domains"]["general"]["kept"] == 2
    assert c["domains"]["general"]["authors"] == 1

    u1 = x_post("someone_else", "32", NEWS)
    u2 = bsky_post("someone.bsky.social", "33", OTHER)
    _, c = evaluate([u1, u2], cfg, since=SINCE, now=NOW)
    assert c["domains"]["general"]["authors"] == 2, "an unmapped account is its own author"


# ── through the store and the page ───────────────────────────────────────────


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


def test_the_page_counts_a_person_once_after_a_relabel(conn, cfg):
    """Stored, loaded back (`--relabel`'s path), labelled and read by the page: the
    person flag survives the round trip and the page counts like `counts`."""
    from collect.industry_ai import store
    from judge.industry_ai.view import ai_watch_view

    store.start_run(conn, "iai-people", mode="harvest", domains=[], platforms=["x", "bluesky"],
                    pipeline_version=cfg.pipeline_version)
    items = [x_post("emollick", "40", NEWS), bsky_post("emollick.bsky.social", "41", OTHER),
             x_post("someone_else", "42", OTHER + " Different words here entirely, though.")]
    store.upsert_items(conn, items, run_id="iai-people")
    results, counts_ = evaluate(store.load_items(conn), cfg, since=SINCE, now=NOW)
    store.write_labels(conn, results, pipeline_version=cfg.pipeline_version)
    conn.commit()

    assert counts_["domains"]["general"] == {**counts_["domains"]["general"], "kept": 3,
                                             "authors": 2}
    # General AI is on AI Watch since 2026-11-25; every post here is General AI.
    view = ai_watch_view(conn)
    assert view["general"] == 3 and view["authors"] == 2
