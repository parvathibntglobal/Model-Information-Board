"""Kite Pulse outreach, Hacker News Finder. No network, no database.

The last two tests guard the design rather than the behaviour:
  * the package never sends a write request to any platform (no posting);
  * it imports nothing from collect/ except collect.config (no evidence writes).
"""

from __future__ import annotations

import ast
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

OUTREACH = Path(__file__).resolve().parent.parent / "web" / "src" / "kitepulse" / "outreach"
PACKAGE = OUTREACH / "hackernews"
if str(OUTREACH) not in sys.path:
    sys.path.insert(0, str(OUTREACH))

from hackernews import config  # noqa: E402
from hackernews import thread as t  # noqa: E402
from hackernews.client import HackerNewsClient, HackerNewsError  # noqa: E402
from hackernews.config import Community, Pace, Query  # noqa: E402
from hackernews.finder import find_hackernews  # noqa: E402
from hackernews.parse import plain_text, thread_of  # noqa: E402

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
UA = "kitepulse-outreach-test/0 (+https://example.invalid)"


def _epoch(hours_ago: float) -> int:
    return int((NOW - timedelta(hours=hours_ago)).timestamp())


def story(oid, *, hours_ago=2, title="Ask HN: Claude Code usage limit?", text=None, author="alice"):
    return {"objectID": oid, "_tags": ["story", "ask_hn"], "title": title,
            "story_text": text, "author": author, "created_at_i": _epoch(hours_ago)}


def comment(oid, *, story_id="100", hours_ago=1, text="<p>I keep hitting the limit</p>",
            author="bob"):
    return {"objectID": oid, "_tags": ["comment"], "comment_text": text,
            "story_id": int(story_id), "story_title": "Claude Code thread", "author": author,
            "created_at_i": _epoch(hours_ago)}


class FakeHN:
    """MockTransport handler: search results by query, thread trees by id."""

    def __init__(self, hits_by_query, items=None):
        self.hits_by_query = hits_by_query
        self.items = items or {}
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if request.url.path.endswith("/search_by_date"):
            hits = self.hits_by_query.get(request.url.params["query"], [])
            return httpx.Response(200, json={"hits": hits, "nbPages": 1})
        m = re.search(r"/items/(\d+)$", request.url.path)
        if m and m.group(1) in self.items:
            return httpx.Response(200, json=self.items[m.group(1)])
        return httpx.Response(404, text="not found")


def client_for(fake: FakeHN) -> HackerNewsClient:
    return HackerNewsClient(UA, http=httpx.Client(transport=httpx.MockTransport(fake)),
                            sleep=lambda _s: None)


PENDING = Community("hackernews", "Hacker News", "pending_review", "https://x.invalid")
ALLOWED = Community("hackernews", "Hacker News", "allowed", "https://x.invalid")
BLOCKED = Community("hackernews", "Hacker News", "not_allowed", "https://x.invalid")
NO_TEAM = Pace(max_thread_age_days=7, team_accounts=())


def run(fake, *, queries, pace=NO_TEAM, community=ALLOWED):
    return find_hackernews(client_for(fake), queries=queries, pace=pace, community=community,
                           now=NOW)


# --- parsing ---------------------------------------------------------------

def test_plain_text_unescapes_and_keeps_paragraphs():
    assert plain_text("it&#x27;s <i>slow</i><p>second") == "it's slow\n\nsecond"
    assert plain_text("  ") is None
    assert plain_text(None) is None


def test_comment_hit_points_at_its_story():
    th = thread_of(comment("201", story_id="100"), fetched_at=NOW)
    assert (th.kind, th.root_id, th.url) == (
        "comment", "100", "https://news.ycombinator.com/item?id=201")
    assert th.body == "I keep hitting the limit"


def test_story_hit_is_its_own_root():
    th = thread_of(story("100"), fetched_at=NOW)
    assert (th.kind, th.root_id, th.title) == ("story", "100", "Ask HN: Claude Code usage limit?")


# --- finder and filters ----------------------------------------------------

def test_one_item_found_by_two_phrases_is_one_thread_with_both():
    fake = FakeHN({"a": [story("100")], "b": [story("100")]})
    result = run(fake, queries=[Query("claude-limits", "a"), Query("agent-stuck", "b")])
    assert len(result.threads) == 1
    th = result.threads[0]
    assert th.matched_problems == ["claude-limits", "agent-stuck"]
    assert th.matched_phrases == ["a", "b"]


def test_old_and_empty_items_are_dropped_with_their_reason():
    fake = FakeHN({"q": [story("1", hours_ago=24 * 8), comment("2", text=""), story("3")]})
    result = run(fake, queries=[Query("p", "q")])
    reasons = {th.ext_id: th.drop_reason for th in result.threads}
    assert reasons == {"1": t.TOO_OLD, "2": t.NO_TEXT, "3": None}
    assert [th.ext_id for th in result.kept] == ["3"]


def test_a_blocked_community_drops_everything_but_keeps_the_rows():
    result = run(FakeHN({"q": [story("1"), story("2")]}), queries=[Query("p", "q")],
                 community=BLOCKED)
    assert result.kept == []
    assert {th.drop_reason for th in result.threads} == {t.COMMUNITY_NOT_ALLOWED}


def test_a_pending_community_keeps_and_flags():
    result = run(FakeHN({"q": [story("1")]}), queries=[Query("p", "q")], community=PENDING)
    assert result.kept[0].flags == [t.COMMUNITY_PENDING_REVIEW]


def test_no_team_accounts_means_the_check_is_named_as_not_run_and_no_thread_is_read():
    fake = FakeHN({"q": [story("1")]})
    result = run(fake, queries=[Query("p", "q")])
    assert any(line.startswith("already_answered") for line in result.checks_not_run)
    assert not any("/items/" in c.url.path for c in fake.calls)


def test_a_thread_the_team_already_replied_in_is_dropped():
    tree = {"author": "alice", "children": [{"author": "Our_Teammate", "children": []}]}
    fake = FakeHN({"q": [story("100"), comment("201", story_id="100"), story("300")]},
                  items={"100": tree, "300": {"author": "carol", "children": []}})
    result = run(fake, queries=[Query("p", "q")],
                 pace=Pace(max_thread_age_days=7, team_accounts=("our_teammate",)))
    reasons = {th.ext_id: th.drop_reason for th in result.threads}
    assert reasons == {"100": t.ALREADY_ANSWERED, "201": t.ALREADY_ANSWERED, "300": None}
    # story 100 is read once for both items in it
    assert sum(c.url.path.endswith("/items/100") for c in fake.calls) == 1
    assert not any(line.startswith("already_answered") for line in result.checks_not_run)


# --- client ----------------------------------------------------------------

def test_every_request_carries_the_user_agent_and_the_age_window():
    fake = FakeHN({"q": []})
    run(fake, queries=[Query("p", "q")])
    req = fake.calls[0]
    assert req.headers["User-Agent"] == UA
    assert req.url.params["numericFilters"] == f"created_at_i>{_epoch(24 * 7)}"
    assert req.url.params["tags"] == "(story,comment)"


def test_an_empty_user_agent_is_refused():
    with pytest.raises(HackerNewsError):
        HackerNewsClient("  ")


def test_an_http_error_is_raised_not_read_as_no_results():
    def fail(_request):
        return httpx.Response(503, text="down")
    client = HackerNewsClient(UA, http=httpx.Client(transport=httpx.MockTransport(fail)),
                              sleep=lambda _s: None)
    with pytest.raises(HackerNewsError):
        client.search_recent("q", since_epoch=0)


# --- config ----------------------------------------------------------------

def test_the_shipped_config_loads():
    assert config.queries("hackernews")
    assert config.community("hackernews").vendor_replies in config.VENDOR_REPLY_STATES
    assert config.pace("hackernews").max_thread_age_days >= 1


def test_a_missing_config_key_raises(tmp_path):
    (tmp_path / "pace.yaml").write_text("team_accounts: {hackernews: []}\n", encoding="utf-8")
    with pytest.raises(config.ConfigError):
        config.pace("hackernews", config_dir=tmp_path)


# --- design guards ---------------------------------------------------------

_WRITE_CALL = re.compile(
    r"\.(post|put|patch|delete)\s*\(|method\s*=\s*[\"'](POST|PUT|PATCH|DELETE)",
    re.I,
)


def _sources():
    return sorted(PACKAGE.rglob("*.py"))


def test_the_package_sends_no_write_request_to_any_platform():
    offenders = [f"{p.relative_to(PACKAGE)}:{n}"
                 for p in _sources()
                 for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
                 if _WRITE_CALL.search(line)]
    assert offenders == [], f"outreach must only read from forums: {offenders}"


def test_the_package_imports_nothing_from_collect_but_config():
    allowed = {"collect.config"}
    found = set()
    for p in _sources():
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module and (
                    node.module == "collect" or node.module.startswith("collect.")):
                found.add(node.module)
            elif isinstance(node, ast.Import):
                found |= {a.name for a in node.names if a.name.split(".")[0] == "collect"}
    assert found <= allowed, f"unexpected collect/ imports: {found - allowed}"
