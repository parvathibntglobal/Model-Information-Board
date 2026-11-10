"""Kite Pulse outreach, dev.to Finder. No network, no database."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

OUTREACH = Path(__file__).resolve().parent.parent / "web" / "src" / "kitepulse" / "outreach"
DT_CONFIG = OUTREACH / "devto" / "config"
if str(OUTREACH) not in sys.path:
    sys.path.insert(0, str(OUTREACH))

from common import config  # noqa: E402
from common import thread as t  # noqa: E402
from common.config import Community, Pace, Query  # noqa: E402
from devto import client as devto_client  # noqa: E402
from devto.client import DevtoClient, DevtoError  # noqa: E402
from devto.finder import find_devto  # noqa: E402

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
UA = "kitepulse-outreach-test/0 (+https://example.invalid)"
ROBOTS = "User-agent: *\nDisallow: /search?q=*\n"


def _iso(hours_ago: float) -> str:
    return (NOW - timedelta(hours=hours_ago)).isoformat().replace("+00:00", "Z")


def article(aid, title, *, tags=("claude",), hours_ago=2, description="", comments=0):
    return {"id": aid, "title": title, "description": description, "tag_list": list(tags),
            "published_at": _iso(hours_ago), "url": f"https://dev.to/someone/post-{aid}",
            "path": f"/someone/post-{aid}", "comments_count": comments,
            "user": {"username": "writer"}}


class FakeDevto:
    """MockTransport handler: robots.txt, tag listings by (tag, page), comments."""

    def __init__(self, pages_by_tag, *, comments=None, status=200, robots=ROBOTS):
        self.pages_by_tag = pages_by_tag
        self.comments = comments or {}
        self.status = status
        self.robots = robots
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path, params = request.url.path, request.url.params
        if path == "/robots.txt":
            return httpx.Response(200, text=self.robots)
        if self.status != 200:
            return httpx.Response(self.status, text="nope")
        if path == "/api/articles":
            pages = self.pages_by_tag.get(params["tag"], [])
            page = int(params["page"])
            return httpx.Response(200, json=pages[page - 1] if page <= len(pages) else [])
        if path == "/api/comments":
            return httpx.Response(200, json=self.comments.get(params["a_id"], []))
        return httpx.Response(404, text="not found")


def client_for(fake: FakeDevto) -> DevtoClient:
    return DevtoClient(UA, http=httpx.Client(transport=httpx.MockTransport(fake)),
                       sleep=lambda _s: None)


ALLOWED = Community("dev.to", "DEV", "allowed", "https://x.invalid")
PENDING = Community("dev.to", "DEV", "pending_review", "https://x.invalid")
NO_TEAM = Pace(max_thread_age_days=7, team_accounts=())
LIMITS = (Query("claude-limits", "usage limit"),)


def run(fake, *, tags=("claude",), queries=LIMITS, pace=NO_TEAM, community=ALLOWED,
        max_pages=3):
    return find_devto(client_for(fake), tags=list(tags), queries=list(queries), pace=pace,
                      community=community, now=NOW, max_pages=max_pages)


# --- finder ----------------------------------------------------------------

def test_matches_title_or_description_and_builds_the_thread():
    fake = FakeDevto({"claude": [[
        article(1, "My week with Claude", description="I hit the usage limit daily"),
        article(2, "Unrelated post"),
    ]]})
    result = run(fake)
    assert result.articles_read == 2
    [th] = result.kept
    assert (th.ext_id, th.kind, th.community, th.author) == ("1", "article", "dev.to", "writer")
    assert th.url == "https://dev.to/someone/post-1"
    assert th.body == "I hit the usage limit daily"


def test_the_request_asks_for_the_week_of_one_tag_at_the_maximum_page_size():
    fake = FakeDevto({"claude": [[]]})
    run(fake)
    req = next(c for c in fake.calls if c.url.path == "/api/articles")
    assert dict(req.url.params) == {"tag": "claude", "top": "7", "per_page": "1000",
                                    "page": "1"}
    assert req.headers["User-Agent"] == UA


def test_an_article_in_two_tags_is_read_once():
    a = article(1, "usage limit again", tags=("claude", "agents"))
    result = run(FakeDevto({"claude": [[a]], "agents": [[a]]}), tags=("claude", "agents"))
    assert result.articles_read == 1 and len(result.threads) == 1


def test_a_full_page_is_followed_by_the_next(monkeypatch):
    monkeypatch.setattr(devto_client, "PER_PAGE", 2)
    pages = [[article(1, "usage limit a"), article(2, "b")], [article(3, "usage limit c")]]
    fake = FakeDevto({"claude": pages})
    result = run(fake)
    assert result.tags[0].complete and result.articles_read == 3
    assert {th.ext_id for th in result.kept} == {"1", "3"}


def test_hitting_the_page_limit_is_named(monkeypatch):
    monkeypatch.setattr(devto_client, "PER_PAGE", 1)
    fake = FakeDevto({"claude": [[article(1, "a")], [article(2, "b")]]})
    result = run(fake, max_pages=1)
    assert not result.tags[0].complete
    assert any("stopped at the page limit" in line for line in result.checks_not_run)


def test_an_ignored_tag_filter_fails_the_tag_instead_of_returning_the_wrong_list():
    fake = FakeDevto({"claude": [[article(1, "usage limit", tags=("javascript",))]]})
    result = run(fake)
    assert result.threads == [] and "tag filter was not applied" in result.errors[0]


def test_an_ignored_date_filter_fails_the_tag():
    fake = FakeDevto({"claude": [[article(1, "usage limit", hours_ago=24 * 30)]]})
    result = run(fake)
    assert result.threads == [] and "date filter was not applied" in result.errors[0]


def test_one_failed_tag_does_not_hide_the_others():
    fake = FakeDevto({"claude": [[article(1, "usage limit", tags=("x",))]],
                      "agents": [[article(2, "usage limit", tags=("agents",))]]})
    result = run(fake, tags=("claude", "agents"))
    assert [th.ext_id for th in result.kept] == ["2"]
    assert len(result.errors) == 1 and result.errors[0].startswith("tag claude")


def test_an_http_error_is_a_failure_not_an_empty_week():
    result = run(FakeDevto({}, status=503))
    assert result.threads == [] and "HTTP 503" in result.errors[0]


def test_a_pending_community_keeps_and_flags():
    result = run(FakeDevto({"claude": [[article(1, "usage limit")]]}), community=PENDING)
    assert result.kept[0].flags == [t.COMMUNITY_PENDING_REVIEW]


def test_team_check_reads_comments_only_where_there_are_some():
    fake = FakeDevto({"claude": [[article(1, "usage limit a", comments=2),
                                  article(2, "usage limit b", comments=0)]]},
                     comments={"1": [{"user": {"username": "someone"},
                                      "children": [{"user": {"username": "Our_Team"},
                                                    "children": []}]}]})
    result = run(fake, pace=Pace(max_thread_age_days=7, team_accounts=("our_team",)))
    reasons = {th.ext_id: th.drop_reason for th in result.threads}
    assert reasons == {"1": t.ALREADY_ANSWERED, "2": None}
    comment_calls = [c for c in fake.calls if c.url.path == "/api/comments"]
    assert [c.url.params["a_id"] for c in comment_calls] == ["1"]


def test_no_team_accounts_means_the_check_is_named_and_no_comments_are_read():
    fake = FakeDevto({"claude": [[article(1, "usage limit", comments=5)]]})
    result = run(fake)
    assert any(line.startswith("already_answered") for line in result.checks_not_run)
    assert not any(c.url.path == "/api/comments" for c in fake.calls)


def test_a_robots_disallowed_api_is_never_requested():
    fake = FakeDevto({"claude": [[article(1, "usage limit")]]},
                     robots="User-agent: *\nDisallow: /api/\n")
    result = run(fake)
    assert result.threads == [] and "disallows /api/articles" in result.errors[0]
    assert [c.url.path for c in fake.calls] == ["/robots.txt"]


def test_an_empty_user_agent_is_refused():
    with pytest.raises(DevtoError):
        DevtoClient("")


# --- config ----------------------------------------------------------------

def test_the_shipped_config_loads():
    tags = config.names("tags.yaml", "tags", DT_CONFIG)
    assert "claude" in tags and len(tags) == len(set(tags))
    assert config.queries("devto", DT_CONFIG)
    assert config.community("dev.to", DT_CONFIG).vendor_replies in config.VENDOR_REPLY_STATES
    assert config.pace("devto", DT_CONFIG).max_thread_age_days >= 1


def test_an_empty_tag_list_is_an_error(tmp_path):
    (tmp_path / "tags.yaml").write_text("tags: []\n", encoding="utf-8")
    with pytest.raises(config.ConfigError):
        config.names("tags.yaml", "tags", tmp_path)
