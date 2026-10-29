"""Admin -> News (2026-10-28): contract, parsing, the daily fold, the harvest and the view.

The harvest and view tests need Postgres (the `test_dsn` fixture); the rest do not.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import psycopg
import pytest

from collect.http import build_client
from collect.news import harvest as news
from judge import news as view

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"
UA = "modelboard/0.1 (+https://modelboard.invalid/about)"

CONTRACT_YAML = """
version: 1
summary_max_words: 12
summary_min_words: 4
llm_keywords: [llm, claude, tokens, "language model"]
page: {default_days: 7, max_days: 30, max_items: 600}
link_preview: {enabled: false, groups: [selected, lab, writer], skip: {}, max_per_run: 10,
               max_attempts: 3, look_back_days: 7, max_head_bytes: 4096, generic_min_stories: 2}
as_given: {}
sources:
  - {key: wire, group: selected, label: Wire, kind: feed, url: "https://wire.example/feed.xml",
     terms: "test", daily: false}
  - {key: rel, group: release, label: Rel, kind: github_releases,
     url: "https://api.github.example/repos/o/r/releases?per_page=3", terms: "test", daily: true}
  - {key: shut, group: lab, label: Shut, kind: feed, url: "https://shut.example/rss", terms: "test",
     daily: false}
  - {key: down, group: writer, label: Down, kind: feed, url: "https://down.example/rss",
     terms: "test", daily: false}
"""

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Wire</title>
<item><title>Claude gets cheaper</title><link>https://wire.example/a</link>
<pubDate>Tue, 27 Oct 2026 10:00:00 GMT</pubDate><author>Ann</author><category>pricing</category>
<description>&lt;p&gt;Fewer &lt;b&gt;tokens&lt;/b&gt; per answer &amp;amp; less waste. A second
sentence runs on well past the word limit here.&lt;/p&gt; The post Claude gets cheaper
appeared first on Wire.</description>
<enclosure url="https://wire.example/a.jpg" type="image/jpeg" length="1"/></item>
<item><title>Undated note</title><link>https://wire.example/b</link>
<description>Detokenize is not a match</description></item>
<item><title>No link here</title><pubDate>Tue, 27 Oct 2026 09:00:00 GMT</pubDate></item>
</channel></rss>"""

def _release(tag, when, **extra):
    return {"name": tag, "tag_name": tag, "html_url": f"https://gh.example/{tag}",
            "published_at": when, **extra}


RELEASES = [
    _release("b3", "2026-10-28T09:00:00Z"),
    _release("b2", "2026-10-28T08:00:00Z"),
    _release("b1", "2026-10-27T23:00:00Z"),
    _release("draft", None, draft=True),
]


@pytest.fixture
def contract(tmp_path):
    p = tmp_path / "news_sources.yaml"
    p.write_text(CONTRACT_YAML, encoding="utf-8")
    return news.load_contract(p)


# ── the contract ─────────────────────────────────────────────────────────────

def test_the_real_contract_loads_and_llamacpp_is_the_one_daily_source():
    c = news.load_contract()
    # openai.com challenges bots: never asked for link previews, and says why.
    assert "openai" in c.link_preview["skip"] and c.link_preview["skip"]["openai"]
    assert {s.key for s in c.sources if s.daily} == {"gh_llamacpp"}
    assert all(s.url.startswith("https://") for s in c.sources)
    assert "gdelt" not in {s.key for s in c.sources}  # dropped 2026-10-28


@pytest.mark.parametrize("bad, says", [
    ("summary_max_words: 12", "summary_max_words"),
    ("daily: false}", "daily must be"),
    ("kind: feed, url: \"https://wire", "kind must be"),
])
def test_a_missing_or_wrong_value_is_refused_not_defaulted(tmp_path, bad, says):
    broken = {"summary_max_words: 12": "",
              "daily: false}": "daily: maybe}",
              "kind: feed, url: \"https://wire": "kind: page, url: \"https://wire"}
    text = CONTRACT_YAML.replace(bad, broken[bad], 1)
    p = tmp_path / "c.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(news.NewsContractError, match=says):
        news.load_contract(p)


# ── parsing ──────────────────────────────────────────────────────────────────

def test_a_feed_keeps_what_it_gives_and_invents_nothing(contract):
    items = news.parse_feed(RSS, contract)
    # The item with no link is dropped: it cannot be opened.
    assert [i["url"] for i in items] == ["https://wire.example/a", "https://wire.example/b"]
    a, b = items
    assert a["published_at"] == datetime(2026, 10, 27, 10, tzinfo=UTC)
    assert a["author"] == "Ann" and a["categories"] == ["pricing"]
    # Code-written: whole sentences up to the word limit, boilerplate gone.
    assert a["summary"] == "Fewer tokens per answer & less waste."
    assert a["image_url"] == "https://wire.example/a.jpg"
    assert a["llm_keywords"] == ["claude", "tokens"]
    # A missing date stays missing (rule 6); a word inside a word is no match.
    assert b["published_at"] is None and b["llm_keywords"] == []
    assert b["image_url"] is None  # no picture in the feed: the page draws a card


def test_the_summary_is_whole_sentences_cut_by_code():
    s = news.summarise
    kept = s("One two three. Four five six seven. Eight.", 7)
    assert kept == "One two three. Four five six seven."
    # A first sentence longer than the limit is cut at a word, never mid-word.
    assert s("<p>alpha beta gamma delta epsilon</p>", 3) == "alpha beta gamma…"
    assert s("Real text. Continue reading the rest of it", 10) == "Real text."
    assert s("   ", 10) is None and s(None, 10) is None


def test_a_thin_summary_falls_back_to_the_feeds_own_content(contract):
    long = "<p>The content says more. It has several full sentences in it.</p>"
    assert news.feed_summary("Short.", long, "T", contract) == (
        "The content says more. It has several full sentences in it.", "feed_content")
    # A summary that only repeats the title is no summary.
    assert news.feed_summary("Claude gets cheaper", None, "Claude gets cheaper",
                             contract) == (None, None)
    # Nor is a topic label where the summary goes, with nothing longer to use.
    assert news.feed_summary("Generative AI", None, "TB screening", contract) == (None, None)


def test_release_notes_become_their_first_changes():
    body = "\n".join(["## What's Changed",
                      "* Fix the CUDA build by @dev in #12",
                      "* Add a Vulkan backend by @dev2 in #13",
                      "**Full Changelog**: https://x"])
    assert news.release_summary(body, 20) == "Fix the CUDA build; Add a Vulkan backend."
    assert news.release_summary("## Notes only", 20) is None


def test_an_image_comes_only_from_the_feed_and_only_over_https():
    from collect.adapters.blog.parse import _entry_image
    assert _entry_image({"media_content": [{"url": "https://x/p.png", "medium": "image"}]}) == "https://x/p.png"
    assert _entry_image({"summary": '<p><img src="http://x/p.jpg"></p>'}) is None  # http: dropped
    assert _entry_image({"content": [{"value": '<img alt="" src="https://x/q.webp">'}]}) == "https://x/q.webp"
    assert _entry_image({}) is None


def test_releases_skip_drafts(contract):
    items = news.parse_github_releases(RELEASES, contract)
    assert [i["tag"] for i in items] == ["b3", "b2", "b1"]
    with pytest.raises(ValueError):
        news.parse_github_releases({"message": "rate limited"}, contract)


def test_a_daily_source_folds_each_utc_day_and_a_cut_day_says_at_least(contract):
    rel = next(s for s in contract.sources if s.key == "rel")
    items = news.parse_github_releases(RELEASES, contract)
    folded = {f["daily_day"]: f for f in news.fold_daily(items, rel, window_full=True)}
    assert folded["2026-10-28"]["daily_count"] == 2
    assert folded["2026-10-28"]["url"] == "https://gh.example/b3"  # the day's newest
    assert folded["2026-10-28"]["title"] == "Rel: 2 releases on 2026-10-28 (b2 - b3)"
    # The window was full, so its oldest day may have had more (rule 7).
    assert folded["2026-10-27"]["title"].startswith("Rel: at least 1 releases on 2026-10-27")
    whole = {f["daily_day"]: f for f in news.fold_daily(items, rel, window_full=False)}
    assert whole["2026-10-27"]["title"] == "Rel: b1"


def test_the_window_is_full_only_when_the_read_returned_per_page():
    assert news._window_full("https://x/releases?per_page=30", 30)
    assert not news._window_full("https://x/releases?per_page=30", 12)
    assert not news._window_full("https://x/feed.xml", 500)


# ── the harvest and the view (Postgres) ──────────────────────────────────────

@dataclass
class _Decision:
    allowed: bool
    reason: str


class _Gate:
    def __init__(self, refuse=()):
        self.refuse = set(refuse)

    def allows(self, url):
        host = url.split("/")[2]
        refused = host in self.refuse
        return _Decision(not refused, "disallowed by test" if refused else "ok")

    def min_interval(self, url):
        return 0.0


class _Store:
    def put(self, data):
        return type("P", (), {"ref": f"raw/test/{len(data)}"})()


def _handler(request: httpx.Request) -> httpx.Response:
    host = request.url.host
    if host == "wire.example":
        return httpx.Response(200, content=RSS)
    if host == "api.github.example":
        return httpx.Response(200, content=json.dumps(RELEASES).encode())
    if host == "down.example":
        return httpx.Response(503)
    raise AssertionError(f"unexpected request to {host}")


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.execute(SCHEMA.read_text(encoding="utf-8"))
        c.commit()
        yield c


def _run(conn, contract):
    with build_client(user_agent=UA, transport=httpx.MockTransport(_handler)) as client:
        return news.harvest(conn, client, gate=_Gate(refuse={"shut.example"}), store=_Store(),
                            contract=contract,
                            clock=lambda: datetime(2026, 10, 28, 12, tzinfo=UTC))


def test_every_read_is_recorded_and_a_rerun_adds_nothing(conn, contract):
    first = _run(conn, contract)
    assert (first["ok"], first["refused"], first["failed"]) == (2, 1, 1)
    assert first["items_new"] == 2 + 2  # two feed items; two release days
    reads = dict(conn.execute("SELECT source_key, outcome FROM news_fetch").fetchall())
    assert reads == {"wire": "ok", "rel": "ok", "shut": "robots_refused", "down": "http_error"}
    again = _run(conn, contract)
    assert again["items_new"] == 0
    assert conn.execute("SELECT count(*) FROM news_item").fetchone()[0] == 4


def test_a_daily_entry_grows_and_never_shrinks(conn, contract):
    _run(conn, contract)
    rel = next(s for s in contract.sources if s.key == "rel")
    day = {"url": "https://gh.example/b9", "title": "Rel: 5 releases on 2026-10-28 (b2 - b9)",
           "published_at": datetime(2026, 10, 28, 11, tzinfo=UTC), "summary": None, "author": None,
           "categories": [], "llm_keywords": [], "daily_day": "2026-10-28", "daily_count": 5}
    now = datetime(2026, 10, 28, 13, tzinfo=UTC)
    assert news.write_items(conn, rel, [day], "raw/x", now) == 0  # grew: an update, not an addition
    smaller = day | {"daily_count": 1, "title": "smaller"}
    assert news.write_items(conn, rel, [smaller], "raw/y", now) == 0
    # By id, not by `published_at::date`: that casts in the session's time zone,
    # and a UTC day is what the fold groups by.
    row = conn.execute("SELECT daily_count, title FROM news_item WHERE id = %s",
                       (news.stable_id("news", "rel", "2026-10-28"),)).fetchone()
    assert row == (5, "Rel: 5 releases on 2026-10-28 (b2 - b9)")


def test_the_view_lists_dated_items_first_and_every_source_with_its_last_read(
        conn, contract, monkeypatch, tmp_path):
    p = tmp_path / "news_sources.yaml"
    p.write_text(CONTRACT_YAML, encoding="utf-8")
    monkeypatch.setattr(view, "CONTRACT", p)
    _run(conn, contract)
    out = view.news_view(conn, days=7, now=datetime(2026, 10, 28, 12, tzinfo=UTC))
    dated = [i for i in out["items"] if i["published_at"]]
    assert out["items"][: len(dated)] == dated  # an undated item never sorts as fresh
    assert out["items"][-1]["published_at"] is None
    by_key = {s["key"]: s for s in out["sources"]}
    assert by_key["shut"]["last_read"]["outcome"] == "robots_refused"
    assert by_key["down"]["last_read"]["http_status"] == 503
    assert out["population"]["items_in_window"] == 4 and out["population"]["sources_listed"] == 4
    with pytest.raises(view.NewsRequestError):
        view.news_view(conn, days=31)


# ── link-preview pictures (collect/news/preview.py: the recorded exception) ───

from collect.news import preview  # noqa: E402

HEAD = (b'<html><head><title>x</title>'
        b'<meta property="og:image" content="/img/cover.jpg">'
        b'<meta name="twitter:image" content="https://cdn.example/tw.jpg"></head>'
        b'<body>' + b'article text that must never be read ' * 400 + b'</body></html>')


def test_the_preview_picture_is_read_from_the_head_and_made_absolute():
    head = HEAD.decode()
    assert preview.picture_from_head(head, "https://wire.example/a") == "https://wire.example/img/cover.jpg"
    secure = '<meta property="og:image:secure_url" content="https://s.example/p.png">' + head
    assert preview.picture_from_head(secure, "https://wire.example/a") == "https://s.example/p.png"
    twitter_only = '<meta name="twitter:image" content="https://cdn.example/tw.jpg">'
    assert preview.picture_from_head(twitter_only, "https://x.example/") == "https://cdn.example/tw.jpg"
    plain_http = '<meta property="og:image" content="http://x/p.jpg">'
    assert preview.picture_from_head(plain_http, "https://x/") is None
    assert preview.picture_from_head("<title>no picture</title>", "https://x/") is None


def test_only_the_head_is_read():
    seen = []

    def handler(request):
        seen.append(request.url.path)
        return httpx.Response(200, headers={"content-type": "text/html"}, content=HEAD)
    with build_client(user_agent=UA, transport=httpx.MockTransport(handler)) as client:
        read = preview.read_head(client, _Gate(), "https://wire.example/a", 100_000)
    assert read.outcome == "ok" and read.content.endswith(b"</head>")
    assert b"article text" not in read.content
    with build_client(user_agent=UA, transport=httpx.MockTransport(handler)) as client:
        refused = preview.read_head(client, _Gate(refuse={"wire.example"}),
                                    "https://wire.example/a", 1)
    assert refused.content is None and refused.outcome.startswith("robots.txt")
    assert seen == ["/a"]  # the refused read never reached the page


def test_a_story_without_a_feed_picture_is_asked_once(conn, contract):
    _run(conn, contract)  # previews off in the fixture: nothing asked yet
    no_pic = conn.execute("SELECT id, url FROM news_item WHERE source_key = 'wire' "
                          "AND image_url IS NULL").fetchall()
    assert [u for _, u in no_pic] == ["https://wire.example/b"]
    asked = []

    def handler(request):
        asked.append(str(request.url))
        return httpx.Response(200, headers={"content-type": "text/html"}, content=HEAD)
    settings_ = {"enabled": True, "groups": ["selected"], "skip": {}, "max_per_run": 10,
                 "max_attempts": 3, "look_back_days": 30, "max_head_bytes": 100_000}
    now = datetime(2026, 10, 28, 12, tzinfo=UTC)
    for _ in range(2):
        with build_client(user_agent=UA, transport=httpx.MockTransport(handler)) as client:
            preview.fill_pictures(conn, client, _Gate(), _Store(), settings_=settings_,
                                  source_keys=["wire"], now=now)
    assert asked == ["https://wire.example/b"]  # once, however many runs
    row = conn.execute("SELECT image_url, image_source, preview_checked_at IS NOT NULL "
                       "FROM news_item WHERE url = 'https://wire.example/b'").fetchone()
    assert row == ("https://wire.example/img/cover.jpg", "link_preview", True)
    # The story whose feed gave a picture keeps it, marked as the feed's.
    assert conn.execute("SELECT image_source FROM news_item WHERE url = 'https://wire.example/a'"
                        ).fetchone() == ("feed",)


# ── a story's page: models named, matched by code (judge/news.py) ───────────

NAMES = {"claude opus 5": "anthropic/claude-opus-5", "claude opus 5.5": "anthropic/claude-opus-5.5",
         "gpt-6.1 terra": "openai/gpt-6.1-terra", "gpt-6.1": "openai/gpt-6.1"}


def test_a_model_is_matched_by_its_whole_name_longest_first():
    found = view.mentioned_models
    assert found("Claude Opus 5.5 beats Claude Opus 5", NAMES, 6) == [
        "anthropic/claude-opus-5.5", "anthropic/claude-opus-5"]
    # "GPT-6.1" is never found inside "GPT-6.1 Terra", nor a name inside a longer version.
    assert found("Introducing GPT-6.1 Terra", NAMES, 6) == ["openai/gpt-6.1-terra"]
    assert found("claude opus 5.55 and claude opus 5x", NAMES, 6) == []
    assert found("Why GPT-6.1 matters", NAMES, 6) == ["openai/gpt-6.1"]
    assert found("Nothing named here", NAMES, 6) == [] and found("", NAMES, 6) == []


def test_a_name_naming_two_models_is_dropped_and_a_free_listing_is_its_model(conn):
    rows = [("acme/m-2", "Acme: M 2"), ("acme/m-2:free", "Acme: M 2 (free)"),
            ("acme/x-1", "Acme: Twin 1"), ("other/x-1", "Other: Twin 1"),
            ("acme/plain", "Acme: Plain")]
    for cid, name in rows:
        conn.execute("INSERT INTO model_catalog (canonical_id, provider, name, input_modalities, "
                     "output_modalities, pricing, last_seen_at) "
                     "VALUES (%s, 'acme', %s, '{text}', '{text}', '{}', now())", (cid, name))
    names, labels = view.model_names(conn, min_chars=3)
    assert names["m 2"] == "acme/m-2"      # the :free listing folds into the model
    assert "twin 1" not in names           # two models, one name: dropped, never guessed
    assert "plain" not in names            # no version digit: could be a word
    assert labels["acme/m-2"] == "M 2"


def test_a_story_page_lists_its_models_and_says_so_when_it_has_none(conn, contract, monkeypatch,
                                                                   tmp_path):
    p = tmp_path / "news_sources.yaml"
    p.write_text(CONTRACT_YAML + "story: {min_name_chars: 4, max_models: 6, related_days: 14, "
                 "related_max: 4}\n", encoding="utf-8")
    monkeypatch.setattr(view, "CONTRACT", p)
    _run(conn, contract)
    conn.execute("INSERT INTO model_catalog (canonical_id, provider, name, input_modalities, "
                 "output_modalities, pricing, last_seen_at) VALUES ('anthropic/claude-x-1', "
                 "'anthropic', 'Anthropic: Claude X 1', '{text}', '{text}', '{}', now())")
    conn.execute("UPDATE news_item SET title = 'Claude X 1 is out' "
                 "WHERE url = 'https://wire.example/a'")
    item = conn.execute("SELECT id FROM news_item WHERE url = 'https://wire.example/a'").fetchone()[0]
    out = view.story_view(conn, item, now=datetime(2026, 10, 28, 12, tzinfo=UTC))
    assert out["source"]["label"] == "Wire"
    assert out["models"] == [{"id": "anthropic/claude-x-1", "name": "Claude X 1", "voices": 0,
                              "reports": 0, "has_page": True}]
    with pytest.raises(view.NewsNotFound):
        view.story_view(conn, "news_nope")



def test_a_sources_one_picture_for_every_story_is_withheld(conn, contract, monkeypatch, tmp_path):
    p = tmp_path / "news_sources.yaml"
    p.write_text(CONTRACT_YAML, encoding="utf-8")
    monkeypatch.setattr(view, "CONTRACT", p)
    _run(conn, contract)
    # Both wire stories get the site banner, as AIWire's og:image does.
    conn.execute("UPDATE news_item SET image_url = 'https://wire.example/og.png', "
                 "image_source = 'link_preview' WHERE source_key = 'wire'")
    out = view.news_view(conn, days=7, now=datetime(2026, 10, 28, 12, tzinfo=UTC))
    wire = [i for i in out["items"] if i["source_key"] == "wire"]
    assert wire and all(i["image_url"] is None and i["image_generic"] for i in wire)



# ── fuller briefs and readable addresses (anooj, 2026-10-28) ────────────────

def test_a_sentence_the_publisher_cut_off_is_dropped():
    text = "Today is a hard day to cover. Better visualized: the first quarter in Anthropic..."
    assert news.summarise(text, 40) == "Today is a hard day to cover."
    assert news.is_cut("in Anthropic...") and news.is_cut("no closing mark")
    assert not news.is_cut("Why code for the job?")


def test_a_complete_page_description_beats_a_teaser(contract):
    from collect.news.preview import better_brief, description_from_head
    head = ('<meta property="og:description" content="Anthropic&#39;s board has three '
            'share classes and a trust.">')
    assert description_from_head(head).startswith("Anthropic's board")
    brief, source = better_brief(head, "Who runs Anthropic?", "Here is a clear explanation...",
                                 "feed", contract)
    assert source == "page_description" and brief.endswith("and a trust.")
    # A page with no description leaves the story's brief as it was.
    assert better_brief("<title>x</title>", "T", "One full sentence of the feed here.",
                        "feed", contract) == ("One full sentence of the feed here.", "feed")


def test_the_address_is_the_headlines_key_words():
    assert news.slug_base("VCs will make billions on Anthropic’s IPO, but Amazon is set") == (
        "vcs-make-billions-anthropics-ipo-amazon")
    assert news.slug_base('[AINews] Anthropic ends Coding Interviews') == (
        "anthropic-ends-coding-interviews")
    assert news.slug_base("Introducing GPT-6.1 Terra") == "introducing-gpt-6-1-terra"
    assert news.slug_base("!!!") == "story"


def test_two_stories_with_the_same_words_get_different_addresses(conn, contract):
    _run(conn, contract)
    base = news.slug_base("Claude gets cheaper")  # "gets" is a stop word: claude-cheaper
    assert news.unique_slug(conn, base, "news_other") == f"{base}-2"
    # A story keeps its own address.
    own = conn.execute("SELECT id FROM news_item WHERE slug = %s", (base,)).fetchone()[0]
    assert news.unique_slug(conn, base, own) == base


def test_a_story_opens_by_its_address_and_by_its_old_id(conn, contract, monkeypatch, tmp_path):
    p = tmp_path / "news_sources.yaml"
    p.write_text(CONTRACT_YAML + "story: {min_name_chars: 4, max_models: 6, related_days: 14, "
                 "related_max: 4}\n", encoding="utf-8")
    monkeypatch.setattr(view, "CONTRACT", p)
    _run(conn, contract)
    item_id, slug = conn.execute("SELECT id, slug FROM news_item "
                                 "WHERE url = 'https://wire.example/a'").fetchone()
    now = datetime(2026, 10, 28, 12, tzinfo=UTC)
    by_slug = view.story_view(conn, slug, now=now)
    assert by_slug["story"]["id"] == item_id and by_slug["story"]["slug"] == slug
    assert view.story_view(conn, item_id, now=now)["story"]["slug"] == slug



# ── #583 review: the exception's conditions, each tested ─────────────────────

PREVIEW = {"enabled": True, "groups": ["selected"], "skip": {}, "max_per_run": 10,
           "max_attempts": 3, "look_back_days": 30, "max_head_bytes": 100_000}
NOW = datetime(2026, 10, 28, 12, tzinfo=UTC)


def _preview(conn, handler, gate=None, contract=None):
    with build_client(user_agent=UA, transport=httpx.MockTransport(handler)) as client:
        return preview.fill_pictures(conn, client, gate or _Gate(), _Store(), settings_=PREVIEW,
                                     source_keys=["wire"], now=NOW, contract=contract)


def _row(conn):
    return conn.execute("SELECT image_url, preview_outcome, preview_attempts, "
                        "preview_checked_at IS NOT NULL FROM news_item "
                        "WHERE url = 'https://wire.example/b'").fetchone()


def test_a_redirect_hop_robots_refuses_is_never_requested():
    seen = []

    def handler(request):
        seen.append(request.url.host)
        return httpx.Response(301, headers={"location": "https://blocked.example/page"})
    with build_client(user_agent=UA, transport=httpx.MockTransport(handler)) as client:
        read = preview.read_head(client, _Gate(refuse={"blocked.example"}),
                                 "https://wire.example/b", 10_000)
    assert read.content is None and read.outcome.startswith("robots.txt")
    assert seen == ["wire.example"]  # the refused hop was never asked


def test_a_hop_to_plain_http_is_refused():
    def handler(request):
        return httpx.Response(302, headers={"location": "http://wire.example/b"})
    with build_client(user_agent=UA, transport=httpx.MockTransport(handler)) as client:
        read = preview.read_head(client, _Gate(), "https://wire.example/b", 10_000)
    assert read.content is None and read.outcome.startswith("not https")


def test_a_failure_that_may_pass_is_retried_then_given_up(conn, contract):
    _run(conn, contract)

    def busy(request):
        return httpx.Response(503)
    _preview(conn, busy)
    assert _row(conn) == (None, "http_error", 1, False)   # recorded, not final: asked again
    _preview(conn, busy)
    _preview(conn, busy)
    assert _row(conn) == (None, "http_error", 3, True)    # max_attempts reached: given up
    asked = []
    _preview(conn, lambda r: asked.append(1) or httpx.Response(200))
    assert asked == []                                     # and never asked again


def test_a_definite_answer_is_final_at_once(conn, contract):
    _run(conn, contract)
    _preview(conn, lambda request: httpx.Response(404))
    assert _row(conn) == (None, "http_error", 1, True)


def test_the_feeds_own_brief_is_kept_when_the_page_description_wins(conn, contract):
    _run(conn, contract)
    head = (b'<html><head><meta property="og:description" content="The page says more than '
            b'the feed did here."></head><body>x</body></html>')
    _preview(conn, lambda r: httpx.Response(200, headers={"content-type": "text/html"},
                                            content=head), contract=contract)
    summary, source, feed, feed_source = conn.execute(
        "SELECT summary, summary_source, feed_summary, feed_summary_source FROM news_item "
        "WHERE url = 'https://wire.example/b'").fetchone()
    assert source == "page_description" and summary.startswith("The page says more")
    assert feed == "Detokenize is not a match" and feed_source == "feed"  # never overwritten


def test_the_token_never_leaves_its_own_host():
    sent = {}

    def handler(request):
        sent[request.url.host] = request.headers.get("authorization")
        if request.url.host == "api.github.example":
            return httpx.Response(302, headers={"location": "https://elsewhere.example/x"})
        return httpx.Response(200, content=b"[]")
    with build_client(user_agent=UA, transport=httpx.MockTransport(handler)) as client:
        news._get(client, _Gate(), "https://api.github.example/repos/o/r/releases",
                  {"Authorization": "Bearer t0ken"})
    assert sent == {"api.github.example": "Bearer t0ken", "elsewhere.example": None}


def test_a_generic_picture_is_withheld_for_its_own_source_only(conn, contract, monkeypatch,
                                                                tmp_path):
    p = tmp_path / "news_sources.yaml"
    p.write_text(CONTRACT_YAML, encoding="utf-8")
    monkeypatch.setattr(view, "CONTRACT", p)
    _run(conn, contract)
    conn.execute("UPDATE news_item SET image_url = 'https://cdn.example/same.png', "
                 "image_source = 'link_preview'")  # wire uses it twice, rel once per day
    out = view.news_view(conn, days=7, now=NOW)
    by_source = {}
    for i in out["items"]:
        by_source.setdefault(i["source_key"], set()).add(i["image_generic"])
    assert by_source["wire"] == {True}
    # rel's two daily entries share it too (2 >= generic_min_stories) - so make
    # one source use it once to see it kept:
    conn.execute("UPDATE news_item SET image_url = NULL, image_source = NULL "
                 "WHERE source_key = 'rel' AND published_at < '2026-10-28T00:00:00Z'")
    out = view.news_view(conn, days=7, now=NOW)
    rel = [i for i in out["items"] if i["source_key"] == "rel" and i["image_url"]]
    assert rel and not any(i["image_generic"] for i in rel)


def test_a_source_shown_as_given_keeps_its_summary_whole(tmp_path):
    text = CONTRACT_YAML.replace("as_given: {}", "as_given: {wire: test terms}", 1)
    p = tmp_path / "c.yaml"
    p.write_text(text, encoding="utf-8")
    c = news.load_contract(p)
    assert c.as_given == frozenset({"wire"})
    a = news.parse_feed(RSS, c, as_given=True)[0]
    assert a["summary"].startswith("Fewer tokens per answer & less waste. A second")
    assert "past the word limit here." in a["summary"]          # nothing cut
    bad = tmp_path / "bad.yaml"
    bad.write_text(CONTRACT_YAML.replace("as_given: {}", "as_given: {nope: x}", 1),
                   encoding="utf-8")
    with pytest.raises(news.NewsContractError, match="unknown sources"):
        news.load_contract(bad)
