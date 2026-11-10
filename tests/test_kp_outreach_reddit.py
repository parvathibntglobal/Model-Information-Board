"""Kite Pulse outreach, Reddit Finder. No network, no database."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

OUTREACH = Path(__file__).resolve().parent.parent / "web" / "src" / "kitepulse" / "outreach"
RD_CONFIG = OUTREACH / "reddit" / "config"
if str(OUTREACH) not in sys.path:
    sys.path.insert(0, str(OUTREACH))

from common import config  # noqa: E402
from common import thread as t  # noqa: E402
from common.config import Community, Pace, Query  # noqa: E402
from reddit import client as reddit_client  # noqa: E402
from reddit.client import RedditClient, RedditError, host_for  # noqa: E402
from reddit.finder import find_reddit  # noqa: E402
from reddit.parse import thread_of  # noqa: E402

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
UA = "kitepulse-outreach-test/0 (+https://example.invalid)"
HOST = "reddit34.p.rapidapi.com"
SUB = "ClaudeCode"


def post(pid, title, *, hours_ago=2, selftext=None, author="asker", **extra):
    out = {"id": pid, "name": f"t3_{pid}", "title": title, "author": author,
           "subreddit": SUB, "permalink": f"/r/{SUB}/comments/{pid}/slug/",
           "url": "https://i.redd.it/image.png",
           "created_utc": (NOW - timedelta(hours=hours_ago)).timestamp(), **extra}
    if selftext is not None:
        out["selftext"] = selftext
    return out


class FakeApi:
    """MockTransport handler for /getPostsBySubreddit, paged by cursor."""

    def __init__(self, pages, *, script=None, headers=None):
        self.pages = pages
        self.script = list(script or ())  # responses served before the pages
        self.headers = headers or {}
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        assert request.method == "GET"
        assert request.headers["x-rapidapi-host"] == HOST
        assert request.headers["x-rapidapi-key"] == "k"
        if self.script:
            return self.script.pop(0)
        assert request.url.path == "/getPostsBySubreddit"
        assert request.url.params["sort"] == "new"
        page = int(request.url.params.get("cursor") or 0)
        posts = self.pages[page] if page < len(self.pages) else []
        cursor = str(page + 1) if page + 1 < len(self.pages) else None
        return httpx.Response(200, headers=self.headers, json={
            "success": True,
            "data": {"cursor": cursor, "posts": [{"kind": "t3", "data": p} for p in posts]}})


def client_for(fake: FakeApi) -> RedditClient:
    return RedditClient("k", HOST, UA,
                        http=httpx.Client(transport=httpx.MockTransport(fake)),
                        sleep=lambda _s: None)


ALLOWED = Community(SUB, "r/ClaudeCode", "allowed", "https://x.invalid")
PENDING = Community(SUB, "r/ClaudeCode", "pending_review", "https://x.invalid")
BLOCKED = Community(SUB, "r/ClaudeCode", "not_allowed", "https://x.invalid")
NO_TEAM = Pace(max_thread_age_days=7, team_accounts=())
USAGE_LIMIT = (Query("claude-limits", "usage limit"),)


def run(fake, *, queries=USAGE_LIMIT, pace=NO_TEAM, sub=ALLOWED, max_pages=10):
    return find_reddit(client_for(fake), subreddits=[sub], queries=list(queries),
                       pace=pace, now=NOW, max_pages=max_pages)


def test_a_matching_title_is_kept_with_the_thread_link_not_the_linked_image():
    result = run(FakeApi([[post("a1", "Hit my usage limits again"),
                           post("a2", "Fable 5.2 is great")]]))
    [th] = result.threads
    assert th.status == t.STATUS_FOUND
    assert th.url == f"https://www.reddit.com/r/{SUB}/comments/a1/slug/"
    assert (th.source, th.ext_id, th.root_id, th.community, th.kind) == (
        "reddit", "t3_a1", "a1", "r/ClaudeCode", "post")
    assert th.matched_problems == ["claude-limits"]
    assert result.subreddits[0].posts_in_window == 2


def test_paging_stops_at_the_first_post_older_than_the_window():
    fake = FakeApi([[post("a1", "usage limit", hours_ago=1)],
                    [post("a2", "usage limit", hours_ago=24 * 8)],
                    [post("a3", "usage limit", hours_ago=24 * 9)]])
    result = run(fake)
    assert len(fake.calls) == 2
    assert [th.ext_id for th in result.threads] == ["t3_a1"]
    assert result.subreddits[0].reached_window_end


def test_a_page_limit_that_cuts_the_week_short_is_named():
    fake = FakeApi([[post("a1", "x")], [post("a2", "x")], [post("a3", "x")]])
    result = run(fake, max_pages=2)
    assert len(fake.calls) == 2
    assert any("stopped at the page limit" in line for line in result.checks_not_run)


def test_title_only_matching_is_said_not_hidden():
    result = run(FakeApi([[post("a1", "usage limit"), post("a2", "x", selftext="body")]]))
    assert any("1 of 2 posts came without body text" in line
               for line in result.checks_not_run)


@pytest.mark.parametrize("sub, status, flag", [
    (PENDING, t.STATUS_FOUND, t.COMMUNITY_PENDING_REVIEW),
    (BLOCKED, t.STATUS_DROPPED, None),
])
def test_the_communities_rule_is_applied(sub, status, flag):
    [th] = run(FakeApi([[post("a1", "usage limit")]]), sub=sub).threads
    assert th.status == status
    assert (flag in th.flags) if flag else th.drop_reason == t.COMMUNITY_NOT_ALLOWED


def test_a_locked_post_is_dropped_only_when_the_field_says_so():
    result = run(FakeApi([[post("a1", "usage limit", locked=True),
                           post("a2", "usage limit")]]))
    by_id = {th.ext_id: th for th in result.threads}
    assert by_id["t3_a1"].drop_reason == t.CLOSED
    assert by_id["t3_a2"].status == t.STATUS_FOUND
    assert any(line.startswith("closed:") for line in result.checks_not_run)


def test_a_deleted_author_is_none_not_the_placeholder():
    assert thread_of(post("a1", "x", author="[deleted]"), fetched_at=NOW).author is None


def test_data_not_found_is_retried_and_then_recovers():
    empty = httpx.Response(200, json={"success": False, "data": "data not found"})
    fake = FakeApi([[post("a1", "usage limit")]], script=[empty])
    result = run(fake)
    assert len(result.kept) == 1 and not result.errors
    assert len(fake.calls) == 2


def test_data_not_found_that_persists_fails_the_subreddit_never_reads_as_empty():
    empty = httpx.Response(200, json={"success": False, "data": "data not found"})
    fake = FakeApi([[post("a1", "usage limit")]], script=[empty] * 3)
    result = run(fake)
    assert result.threads == []
    assert result.errors and "NOT read as zero posts" in result.errors[0]
    assert len(fake.calls) == 3


def test_a_refused_request_is_not_retried():
    refused = httpx.Response(200, json={"success": False, "data": "bad sort"})
    fake = FakeApi([[post("a1", "usage limit")]], script=[refused])
    result = run(fake)
    assert "refused" in result.errors[0] and len(fake.calls) == 1


def test_a_429_is_waited_out_once_then_fails():
    slow = httpx.Response(429, text="exceeded the rate limit per minute for your plan")
    ok = run(FakeApi([[post("a1", "usage limit")]], script=[slow]))
    assert len(ok.kept) == 1
    failed = run(FakeApi([[post("a1", "usage limit")]], script=[slow, slow]))
    assert "HTTP 429" in failed.errors[0]


def test_a_body_without_a_posts_key_is_an_error_not_an_empty_week():
    fake = FakeApi([], script=[httpx.Response(200, json={"success": True, "data": {}})])
    assert "no 'posts' key" in run(fake).errors[0]


def test_quota_headers_are_read_and_absent_ones_stay_none():
    fake = FakeApi([[post("a1", "x")]], headers={"x-ratelimit-requests-remaining": "999994"})
    client = client_for(fake)
    client.newest_posts(SUB)
    assert client.quota_remaining == 999994
    assert client.quota_limit is None


def test_requests_are_paced_for_the_shared_subscription():
    waits: list[float] = []
    clock = iter([0.0, 0.5, 0.5, 5.0])
    fake = FakeApi([[post("a1", "x")], [post("a2", "x")]])
    client = RedditClient("k", HOST, UA, http=httpx.Client(transport=httpx.MockTransport(fake)),
                          sleep=waits.append, clock=lambda: next(clock))
    client.newest_posts(SUB)
    client.newest_posts(SUB, "1")
    assert waits == [pytest.approx(reddit_client.MIN_INTERVAL_SECONDS - 0.5)]


@pytest.mark.parametrize("provider, shared, expected", [
    ("reddit34", None, "reddit34.p.rapidapi.com"),
    ("reddit34", "twitter241.p.rapidapi.com", "reddit34.p.rapidapi.com"),
    (None, "reddit34.p.rapidapi.com", "reddit34.p.rapidapi.com"),
])
def test_the_host_is_the_reddit_provider(provider, shared, expected):
    assert host_for(provider, shared) == expected


@pytest.mark.parametrize("provider, shared", [(None, "twitter241.p.rapidapi.com"),
                                              (None, None), ("  ", "")])
def test_no_reddit_host_is_refused_not_defaulted(provider, shared):
    with pytest.raises(RedditError):
        host_for(provider, shared)


def test_an_empty_key_is_refused():
    with pytest.raises(RedditError, match="RAPIDAPI_KEY"):
        RedditClient("", HOST, UA)


def test_the_shipped_config_loads():
    assert config.queries("reddit", RD_CONFIG)
    subs = config.communities(RD_CONFIG)
    assert subs and all(s.vendor_replies in config.VENDOR_REPLY_STATES for s in subs)
    assert config.pace("reddit", RD_CONFIG).max_thread_age_days >= 1
