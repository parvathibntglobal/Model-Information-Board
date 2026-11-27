"""The Industry AI observer (watch lists; anooj, 2026-11-20): the keyword agent's twin.

No network. All but the last are pure; the last uses the disposable test database
(TEST_DATABASE_URL), like test_industry_ai.py's page test. What each one pins:
  * the `watch:` block is read strictly (an unread list is refused, never ignored);
  * the watch queries' shape, and X pages for an account query;
  * a WATCHED post needs an AI term only: naming no industry it is kept as General AI,
    naming several it is filed under each (option A), flagged either way;
  * a keyword post with no industry term is still dropped (the twin changes nothing
    for the keyword agent);
  * harvest runs watch sources under their own caps, keyed `watch:<platform>:<source>`,
    with no domain hint;
  * an X account query carries `since:` and both suffixes.
"""

from __future__ import annotations

import copy
import dataclasses
from datetime import UTC, datetime, timedelta

import pytest
import yaml

from collect.industry_ai import config as iai_config
from collect.industry_ai.config import CONTRACT, IndustryAIConfigError
from collect.industry_ai.pipeline import counts, evaluate
from collect.industry_ai.rules import Item

NOW = datetime(2026, 11, 20, tzinfo=UTC)
SINCE = NOW - timedelta(days=365)


@pytest.fixture(scope="module")
def raw():
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cfg(raw):
    return iai_config.parse(copy.deepcopy(raw))


def watched(text, *, key="watch:x:(from:karpathy)", platform="x", iid=None):
    iid = iid or f"{platform}:{abs(hash((text, key))) % 10**8}"
    return Item(
        id=iid,
        platform=platform,
        external_id=iid.split(":", 1)[1],
        url=f"https://e.x/{iid}",
        title="",
        body=text,
        created_at=NOW - timedelta(days=2),
        author_id="a1",
        engagement={"likes": 10},
        domain_hints=set(),
        query_keys={key},
    )


def one(cfg, it):
    results, c = evaluate([it], cfg, since=SINCE, now=NOW)
    return results[it.id], c


# ── the contract ─────────────────────────────────────────────────────────────


def test_the_watch_lists_load_on_daily_and_within_their_caps(cfg):
    w = cfg.watch
    # ON since 2026-11-25 (anooj): it runs daily in its own run, reading back two days.
    assert w["enabled"] is True
    assert w["lookback_days"] == 2
    assert 0 < len(w["bluesky"]) <= 20
    # Raised on 2026-11-25 (anooj): X to 200 (its accounts are clubbed, so 150 accounts
    # cost 15 queries, not 150) and Reddit to 60 (one listing page per subreddit).
    assert 0 < len(w["x"]) <= 200
    assert 0 < len(w["reddit"]) <= 60
    assert len(w["hackernews"]["lists"]) + len(w["hackernews"]["authors"]) <= 20


def test_the_x_watch_cap_reads_every_club_over_the_window(cfg):
    """A cap below clubs x pages leaves the LAST clubs unread, and the list's order
    decides which accounts those are. The run log says "capped", but nothing would
    say which accounts went unread - so the cap must cover them all."""
    w = cfg.watch
    clubs = -(-len(w["x"]) // w["x_club_max"])
    assert w["max_requests"]["x"] >= clubs * w["x_pages"]


def test_the_reddit_watch_cap_reads_every_subreddit(cfg):
    """Each watched subreddit costs run.pages_per_query.reddit listing pages; a cap
    below that leaves the last subreddits in the list unread every run."""
    w = cfg.watch
    assert w["max_requests"]["reddit"] >= len(w["reddit"]) * cfg.run["pages_per_query"]["reddit"]


@pytest.mark.parametrize(
    "mutate, says",
    [
        (lambda w: w.update(devto=["llm"]), "unknown key"),  # not built: refused, not ignored
        (lambda w: w.pop("x_suffix"), "x_suffix"),
        (lambda w: w["x"].append("not a handle!"), "not a valid name"),
        (lambda w: w["reddit"].append(w["reddit"][0]), "listed twice"),
        (lambda w: w["hackernews"].update(lists=["best_hn"]), "unknown"),
        (lambda w: w["max_requests"].pop("bluesky"), "max_requests"),
        (lambda w: w.update(enabled="yes"), "enabled"),
    ],
)
def test_the_watch_block_is_strict(raw, mutate, says):
    r = copy.deepcopy(raw)
    mutate(r["watch"])
    with pytest.raises(IndustryAIConfigError, match=says):
        iai_config.parse(r)


def test_a_clubbed_account_query_too_long_for_x_is_refused(raw):
    r = copy.deepcopy(raw)
    r["watch"]["x"] = [f"account_{i:02d}xyzw" for i in range(20)]  # 15 characters each
    r["watch"]["x_club_max"] = 20
    with pytest.raises(IndustryAIConfigError, match="lower watch.x_club_max"):
        iai_config.parse(r)


def test_watch_queries_and_x_pages(cfg):
    q = cfg.watch_queries()
    by = {}
    for p, s in q:
        by.setdefault(p, []).append(s)
    assert all(s.startswith("r/") for s in by["reddit"])
    n = cfg.watch["x_club_max"]
    assert len(by["x"]) == -(-len(cfg.watch["x"]) // n)
    assert all(s.startswith("(from:") and s.endswith(")") for s in by["x"])
    assert all(s.startswith("from:") for s in by["bluesky"])
    assert set(by["hackernews"]) >= {"hn:list:show_hn", "hn:author:simonw"}
    # An account query is paged over the window; a keyword query is unchanged.
    assert cfg.x_pages(by["x"][0]) == cfg.watch["x_pages"]
    assert cfg.x_pages('("a" OR "b") (AI OR LLM)') == cfg.run["pages_per_query"]["x"]


# ── the sieve and the label ──────────────────────────────────────────────────


def test_a_watched_post_naming_no_industry_is_general_ai(cfg):
    r, c = one(cfg, watched("A new open LLM was released today with a longer context window "
                            "and faster inference for everyone who runs it locally."))
    assert r.verdict == "kept", r.reason
    assert r.domains == [] and "general_ai" in r.flags
    assert "general" in c["domains"] and "unconfirmed" not in c["domains"]


def test_a_watched_post_is_filed_under_every_domain_it_names(cfg):
    r, _ = one(cfg, watched("I used Claude to write our ad copy this week, and it also helped "
                            "with incident response notes for the security team."))
    assert r.verdict == "kept", r.reason
    assert {"marketing", "security_it"} <= set(r.domains)
    assert "domain_from_terms:marketing" in r.flags
    assert "general_ai" not in r.flags


def test_a_keyword_post_with_no_industry_term_is_still_dropped(cfg):
    it = watched("A new open LLM was released today with a longer context window and faster "
                 "inference for everyone who runs it locally.", key="iai:marketing:x:q")
    it.domain_hints = {"marketing"}
    r, _ = one(cfg, it)
    assert r.verdict == "dropped" and r.reason == "no_domain_term"


def test_a_watched_post_with_no_ai_term_is_dropped(cfg):
    r, _ = one(cfg, watched("Great dinner with friends tonight, the pasta was excellent and the "
                            "wine even better."))
    assert r.verdict == "dropped" and r.reason == "no_ai_term"


def test_general_and_unconfirmed_are_counted_apart(cfg):
    gen = watched("A new open LLM was released today with a longer context window and faster "
                  "inference for everyone who runs it locally.", iid="x:g1")
    kw = watched("I used ChatGPT to draft our ad copy for the spring sale and it saved hours.",
                 key="iai:retail:x:q", iid="x:k1")
    kw.domain_hints = {"retail"}  # found by a retail query; names marketing's term only
    results, c = evaluate([gen, kw], cfg, since=SINCE, now=NOW)
    assert results["x:g1"].verdict == "kept" and "general_ai" in results["x:g1"].flags
    assert c["domains"]["general"]["kept"] == 1
    if results["x:k1"].verdict == "kept" and not results["x:k1"].domains:
        assert c["domains"]["unconfirmed"]["kept"] == 1
    assert counts([gen, kw], results)["domains"]["general"]["kept"] == 1


def test_watched_posts_filed_by_terms_are_counted_apart_from_a_domains_own(cfg):
    """Option (a), anooj 2026-11-20: a domain's `kept` counts what its keyword queries
    found; a watched post filed there by its terms goes to `from_watch`, beside it."""
    w = watched("I used Claude to write our ad copy this week, and it also helped with "
                "incident response notes for the security team.", iid="x:w1")
    k = watched("I used ChatGPT to write our ad copy for the spring launch and it saved hours.",
                key="iai:marketing:x:q", iid="x:k2")
    k.domain_hints = {"marketing"}
    results, c = evaluate([w, k], cfg, since=SINCE, now=NOW)
    assert "domain_from_terms:marketing" in results["x:w1"].flags
    mk = c["domains"]["marketing"]
    assert mk["kept"] == 1 and mk["from_watch"] == 1  # the keyword post, and the watched one
    assert sum(mk["by_type"].values()) == 1  # breakdowns count the domain's own only
    assert c["domains"]["security_it"] == {**c["domains"]["security_it"], "kept": 0,
                                           "from_watch": 1}


# ── the watch window (#650 review, point 1) ──────────────────────────────────

AI_SEO = ("I used Claude to write our SEO content and ad copy for the launch, and it saved our "
          "small team a full day of work.")


def test_a_watched_post_older_than_the_lookback_is_dropped(cfg):
    """Reddit's newest page and Bluesky's from: feed return posts of any age."""
    it = watched(AI_SEO, key="watch:reddit:r/ChatGPTPro", platform="reddit")
    it.created_at = NOW - timedelta(days=30)  # inside the run window, outside the watch's
    r, c = one(cfg, it)
    assert r.verdict == "dropped" and r.stage == "window" and r.reason == "outside_watch_window"
    assert c["dropped"] == {"window:outside_watch_window": 1}


def test_the_watch_window_is_measured_from_first_sight_not_from_now(cfg):
    """A --relabel weeks later must not drop a watched post just because time passed."""
    it = watched(AI_SEO, key="watch:reddit:r/ChatGPTPro", platform="reddit")
    it.created_at = NOW - timedelta(days=30)
    it.first_seen_at = NOW - timedelta(days=28)  # stored two days after it was posted
    r, _ = one(cfg, it)
    assert r.verdict == "kept", r.reason


def test_a_post_a_keyword_query_also_found_keeps_the_run_window_and_its_label(cfg):
    it = watched(AI_SEO, key="watch:reddit:r/ChatGPTPro", platform="reddit")
    it.query_keys.add("iai:marketing:reddit:SEO content AI")
    it.domain_hints = {"marketing"}
    it.created_at = NOW - timedelta(days=30)
    r, _ = one(cfg, it)
    assert r.verdict == "kept", r.reason  # the run window (365 days), not the watch's 7
    assert r.domains == ["marketing"]  # the keyword agent's label: confirmed hints only
    assert not [f for f in r.flags if f.startswith("domain_from_terms:")]


# ── harvest ──────────────────────────────────────────────────────────────────


def test_watch_sources_run_under_their_own_caps_with_no_domain_hint(cfg, monkeypatch):
    from collect.industry_ai import harvest as h

    calls = []

    class Fake(h._Runner):
        def __init__(self, *a, **k):
            pass

        def run(self, query):
            calls.append(query)
            it = watched(f"post for {query}", key="placeholder",
                         platform="hackernews", iid=f"hackernews:{len(calls)}")
            it.query_keys = set()
            return [it], 1, "", None, False

    monkeypatch.setitem(h._RUNNERS, "hackernews", Fake)
    w = {**cfg.watch, "max_requests": {**cfg.watch["max_requests"], "hackernews": 3}}
    small = dataclasses.replace(cfg, watch=w)

    class Contract:
        platforms = [{"id": "hackernews"}]
        feeds = []
        rulings = {}

    out = h.harvest(small, domains=[], platforms=["hackernews"], contract=Contract(), store=None,
                    client_factory=lambda **k: None, since=SINCE, log=lambda s: None,
                    watch_since=NOW - timedelta(days=7))
    watch_stats = [s for s in out.queries if s.domain == "watch"]
    n = len(cfg.watch["hackernews"]["lists"]) + len(cfg.watch["hackernews"]["authors"])
    assert [s.status for s in watch_stats] == ["ok"] * 3 + ["capped"] * (n - 3)
    assert all(s.key.startswith("watch:hackernews:hn:") for s in watch_stats)
    for it in out.items.values():
        assert it.domain_hints == set()
        assert all(k.startswith("watch:") for k in it.query_keys)


def test_without_watch_since_no_watch_source_runs(cfg, monkeypatch):
    from collect.industry_ai import harvest as h

    class Fake(h._Runner):
        def __init__(self, *a, **k):
            pass

        def run(self, query):
            raise AssertionError("no watch source should run")

    monkeypatch.setitem(h._RUNNERS, "hackernews", Fake)

    class Contract:
        platforms = [{"id": "hackernews"}]
        feeds = []
        rulings = {}

    out = h.harvest(cfg, domains=[], platforms=["hackernews"], contract=Contract(), store=None,
                    client_factory=lambda **k: None, since=SINCE, log=lambda s: None)
    assert not [s for s in out.queries if s.domain == "watch"]


def test_an_x_account_query_carries_since_and_both_suffixes(cfg):
    from collect.industry_ai.harvest import _X

    runner = _X.__new__(_X)  # no network: only the query builder is exercised
    runner.cfg, runner.since = cfg, NOW - timedelta(days=7)
    runner.suffix = cfg.query_suffix.get("x", "")
    q = runner._full("(from:karpathy OR from:simonw)")
    assert q.startswith("(from:karpathy OR from:simonw) since:2026-11-13")
    assert cfg.watch["x_suffix"] in q and runner.suffix in q
    # a keyword query gets no since: and no watch suffix
    kq = runner._full('("ad copy" OR "SEO content") (AI OR LLM)')
    assert "since:" not in kq and cfg.watch["x_suffix"] not in kq


# ── the page ─────────────────────────────────────────────────────────────────


def test_the_page_buckets_are_one_expression_written_twice():
    """judge/industry_ai/view.py writes the bucket CASE out in each query (the column
    audit reads SQL literals, so a shared constant hid `flags` and `domains` from it).
    Both copies must be identical, or two figures on the page could disagree."""
    import ast
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "judge" / "industry_ai" / "view.py").read_text(
        encoding="utf-8"
    )
    # Every string literal, adjacent pieces already joined by the parser.
    tree = ast.parse(src)
    inside_fstring = {id(v) for n in ast.walk(tree) if isinstance(n, ast.JoinedStr)
                      for v in n.values}
    texts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            texts.append("".join(v.value for v in node.values if isinstance(v, ast.Constant)))
        elif (isinstance(node, ast.Constant) and isinstance(node.value, str)
              and id(node) not in inside_fstring):
            texts.append(node.value)
    start, end = "CASE WHEN cardinality(domains)", "ELSE domains END"
    cases = [t[t.index(start):t.index(end) + len(end)] for t in texts if start in t and end in t]
    assert len(cases) == 2, cases
    assert cases[0] == cases[1]
    assert "'general_ai' = ANY(flags)" in cases[0] and "ARRAY['general']" in cases[0]


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


def test_the_page_counts_watched_posts_apart_and_general_ai_on_its_own(conn, cfg):
    """Through the real store and the page builders: no watched post inside a domain's own
    figures, and since 2026-11-25 the watch lists' posts on AI Watch, not AI in industries."""
    from collect.industry_ai import store
    from judge.industry_ai.view import ai_watch_view, industry_ai_view

    store.start_run(conn, "iai-obs", mode="harvest", domains=["marketing"],
                    platforms=["x"], pipeline_version=cfg.pipeline_version)
    w = watched("I used Claude to write our ad copy this week, and it also helped with "
                "incident response notes for the security team.", iid="x:w1")
    k = watched("I used ChatGPT to write our ad copy for the spring launch and it saved hours.",
                key="iai:marketing:x:q", iid="x:k2")
    k.domain_hints = {"marketing"}
    g = watched("A new open LLM was released today with a longer context window and faster "
                "inference for everyone who runs it locally.", iid="x:g3")
    store.upsert_items(conn, [w, k, g], run_id="iai-obs")
    # THE STORE STAMPS first_seen_at WITH THE DATABASE CLOCK, while these posts are dated
    # from the fixed NOW. The watch window (`watch.lookback_days`) is measured from
    # first_seen_at, so from 2026-11-25 the real clock put these posts outside it and
    # this test failed on every branch. Pin first_seen_at to the test's own clock.
    conn.execute("UPDATE iai_item SET first_seen_at = %s", (NOW,))
    results, counts_ = evaluate(store.load_items(conn), cfg, since=SINCE)
    store.write_labels(conn, results, pipeline_version=cfg.pipeline_version)
    conn.commit()

    view = industry_ai_view(conn)
    by = {d["key"]: d for d in view["domains"]}
    assert by["marketing"]["kept"] == 1 and "from_watch" not in by["marketing"]
    assert sum(by["marketing"]["by_type"].values()) == 1
    assert by["security_it"]["kept"] == 0
    assert "general" not in view and view["unconfirmed"]["kept"] == 0
    assert (view["collected"], view["kept"]) == (1, 1), "the keyword post only"

    watch = ai_watch_view(conn)
    assert (watch["kept"], watch["general"], watch["mentions"]) == (2, 1, 1)
    assert {m["key"]: m["items"] for m in watch["mentioned"]} == {"marketing": 1,
                                                                   "security_it": 1}
