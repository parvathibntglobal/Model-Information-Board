"""Kite Pulse outreach, Discourse Finder. No network, no database."""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

OUTREACH = Path(__file__).resolve().parent.parent / "web" / "src" / "kitepulse" / "outreach"
DC_CONFIG = OUTREACH / "discourse" / "config"
if str(OUTREACH) not in sys.path:
    sys.path.insert(0, str(OUTREACH))

from common import config  # noqa: E402
from common import thread as t  # noqa: E402
from common.config import Community, Pace, Query  # noqa: E402
from common.match import matches  # noqa: E402
from discourse.client import DiscourseClient, DiscourseError  # noqa: E402
from discourse.finder import find_discourse  # noqa: E402

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
UA = "kitepulse-outreach-test/0 (+https://example.invalid)"
HOST = "forum.example"
ROBOTS = "User-agent: *\nDisallow: /search\nDisallow: /admin/\n"


def _iso(hours_ago: float) -> str:
    return (NOW - timedelta(hours=hours_ago)).isoformat().replace("+00:00", "Z")


def topic(tid, title, *, hours_ago=2, excerpt=None, closed=False, pinned=False, op=7):
    out = {"id": tid, "slug": f"topic-{tid}", "title": title, "created_at": _iso(hours_ago),
           "closed": closed, "archived": False, "pinned": pinned,
           "posters": [{"description": "Original Poster", "user_id": op}]}
    if excerpt is not None:
        out["excerpt"] = excerpt
    return out


class FakeForum:
    """MockTransport handler: robots.txt, listing pages, topic JSON."""

    def __init__(self, pages, *, robots=(200, ROBOTS), topics=None, latest_status=200):
        self.pages = pages
        self.robots = robots
        self.topics = topics or {}
        self.latest_status = latest_status
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(self.robots[0], text=self.robots[1])
        if path == "/latest.json":
            if self.latest_status != 200:
                return httpx.Response(self.latest_status, text="slow down")
            page = int(request.url.params.get("page", 0))
            topics = self.pages[page] if page < len(self.pages) else []
            more = f"/latest?page={page + 1}" if page + 1 < len(self.pages) else None
            return httpx.Response(200, json={
                "users": [{"id": 7, "username": "asker"}],
                "topic_list": {"topics": topics, "more_topics_url": more}})
        m = re.fullmatch(r"/t/(\d+)\.json", path)
        if m and m.group(1) in self.topics:
            return httpx.Response(200, json=self.topics[m.group(1)])
        return httpx.Response(404, text="not found")


def client_for(fake: FakeForum) -> DiscourseClient:
    return DiscourseClient(f"https://{HOST}", UA,
                           http=httpx.Client(transport=httpx.MockTransport(fake)),
                           sleep=lambda _s: None)


ALLOWED = Community(HOST, "Example", "allowed", "https://x.invalid")
PENDING = Community(HOST, "Example", "pending_review", "https://x.invalid")
BLOCKED = Community(HOST, "Example", "not_allowed", "https://x.invalid")
NO_TEAM = Pace(max_thread_age_days=7, team_accounts=())
USAGE_LIMIT = (Query("claude-limits", "usage limit"),)


def run(fake, *, queries=USAGE_LIMIT, pace=NO_TEAM, forum=ALLOWED, max_pages=10):
    return find_discourse({HOST: client_for(fake)}, forums=[forum], queries=list(queries),
                          pace=pace, now=NOW, max_pages=max_pages)


# --- matching --------------------------------------------------------------

@pytest.mark.parametrize(("phrase", "text", "expected"), [
    ("usage limit", "Hit my usage limits again", True),
    ("usage limit", "Limited usage on the free plan", True),
    ("usage limit", "Usage dashboard is slow", False),
    ("agent stuck", "Agent is STUCK in a loop", True),
    ("team cost", "AI costs for my team", True),
    ("team cost", "Costume ideas for the team", False),  # a prefix is not the word
    ("claude usage", "claude-code usage spike", True),
])
def test_every_word_must_appear_as_a_whole_word(phrase, text, expected):
    assert matches(phrase, text) is expected


# --- finder ----------------------------------------------------------------

def test_matches_title_and_excerpt_and_builds_the_thread():
    fake = FakeForum([[topic(1, "Help please", excerpt="I hit my usage limit &amp; stopped"),
                       topic(2, "Unrelated question")]])
    result = run(fake)
    assert [th.ext_id for th in result.kept] == [f"{HOST}/t/1"]
    th = result.kept[0]
    assert th.url == f"https://{HOST}/t/topic-1/1"
    assert (th.kind, th.community, th.author) == ("topic", HOST, "asker")
    assert th.body == "I hit my usage limit & stopped"
    assert result.forums[0].topics_in_window == 2


def test_paging_stops_once_the_listing_passes_the_age_window():
    fake = FakeForum([[topic(1, "usage limit A", hours_ago=1)],
                      [topic(2, "usage limit B", hours_ago=24 * 6),
                       topic(3, "usage limit C", hours_ago=24 * 8)],
                      [topic(4, "usage limit D", hours_ago=24 * 9)]])
    result = run(fake)
    assert [th.ext_id.split("/")[-1] for th in result.threads] == ["1", "2"]
    assert result.forums[0].reached_window_end
    assert not any(c.url.params.get("page") == "2" for c in fake.calls)


def test_a_pinned_old_topic_does_not_end_the_window():
    fake = FakeForum([[topic(9, "Welcome", hours_ago=24 * 400, pinned=True),
                       topic(1, "usage limit A")],
                      [topic(2, "usage limit B", hours_ago=24 * 2)]])
    result = run(fake)
    assert {th.ext_id.split("/")[-1] for th in result.threads} == {"1", "2"}


def test_hitting_the_page_limit_inside_the_window_is_named():
    fake = FakeForum([[topic(1, "usage limit A")], [topic(2, "usage limit B")]])
    result = run(fake, max_pages=1)
    assert not result.forums[0].reached_window_end
    assert any("stopped at the page limit" in line for line in result.checks_not_run)


def test_title_only_matching_is_named_per_forum():
    result = run(FakeForum([[topic(1, "usage limit A"), topic(2, "other", excerpt="x")]]))
    assert any("1 of 2 topics had no excerpt" in line for line in result.checks_not_run)


def test_closed_topics_and_blocked_forums_are_dropped_with_their_reason():
    fake = FakeForum([[topic(1, "usage limit A", closed=True), topic(2, "usage limit B")]])
    reasons = {th.ext_id[-1]: th.drop_reason for th in run(fake).threads}
    assert reasons == {"1": t.CLOSED, "2": None}
    blocked = run(FakeForum([[topic(2, "usage limit B")]]), forum=BLOCKED)
    assert [th.drop_reason for th in blocked.threads] == [t.COMMUNITY_NOT_ALLOWED]


def test_a_pending_forum_keeps_and_flags():
    result = run(FakeForum([[topic(1, "usage limit A")]]), forum=PENDING)
    assert result.kept[0].flags == [t.COMMUNITY_PENDING_REVIEW]


def test_team_check_drops_answered_topics_and_flags_partial_reads():
    fake = FakeForum([[topic(1, "usage limit A"), topic(2, "usage limit B")]], topics={
        "1": {"posts_count": 2, "post_stream": {"posts": [{"username": "asker"},
                                                          {"username": "Our_Team"}]}},
        "2": {"posts_count": 40, "post_stream": {"posts": [{"username": "asker"}]},
              "details": {"participants": [{"username": "someone"}]}},
    })
    result = run(fake, pace=Pace(max_thread_age_days=7, team_accounts=("our_team",)))
    by_id = {th.ext_id[-1]: th for th in result.threads}
    assert by_id["1"].drop_reason == t.ALREADY_ANSWERED
    assert by_id["2"].status == t.STATUS_FOUND
    assert by_id["2"].flags == [t.TEAM_CHECK_PARTIAL]


def test_no_team_accounts_means_no_topic_is_read_and_the_check_is_named():
    fake = FakeForum([[topic(1, "usage limit A")]])
    result = run(fake)
    assert any(line.startswith("already_answered") for line in result.checks_not_run)
    assert not any(c.url.path.startswith("/t/") for c in fake.calls)


# --- client and robots.txt -------------------------------------------------

def test_a_disallowed_listing_is_never_requested_and_the_forum_is_reported_failed():
    fake = FakeForum([[topic(1, "usage limit A")]],
                     robots=(200, "User-agent: *\nDisallow: /latest\n"))
    result = run(fake)
    assert result.threads == []
    assert result.errors and "disallows /latest.json" in result.errors[0]
    assert [c.url.path for c in fake.calls] == ["/robots.txt"]


def test_robots_404_means_no_rules_and_5xx_is_an_error():
    assert run(FakeForum([[topic(1, "usage limit A")]], robots=(404, ""))).kept
    failed = run(FakeForum([[topic(1, "usage limit A")]], robots=(503, "")))
    assert failed.threads == [] and "robots.txt" in failed.errors[0]


def test_an_http_error_fails_the_forum_rather_than_reading_as_empty():
    result = run(FakeForum([[topic(1, "usage limit A")]], latest_status=429))
    assert result.threads == []
    assert "HTTP 429" in result.errors[0]


def test_every_request_carries_the_user_agent_and_no_search_is_requested():
    fake = FakeForum([[topic(1, "usage limit A")]])
    run(fake)
    assert all(c.headers["User-Agent"] == UA for c in fake.calls)
    assert all(c.method == "GET" for c in fake.calls)
    assert not any("search" in c.url.path for c in fake.calls)
    assert fake.calls[1].url.params["order"] == "created"


def test_an_empty_user_agent_is_refused():
    with pytest.raises(DiscourseError):
        DiscourseClient(f"https://{HOST}", " ")


# --- config ----------------------------------------------------------------

def test_the_shipped_config_loads():
    forums = config.communities(DC_CONFIG)
    assert [f.key for f in forums] == [
        "forum.cursor.com", "community.openai.com", "discuss.ai.google.dev"]
    assert all(f.vendor_replies in config.VENDOR_REPLY_STATES for f in forums)
    queries = config.queries("discourse", DC_CONFIG)
    assert queries and all(matches(q.phrase, q.phrase) for q in queries)
    assert config.pace("discourse", DC_CONFIG).max_thread_age_days >= 1
