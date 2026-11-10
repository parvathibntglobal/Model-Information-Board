"""Kite Pulse outreach, GitHub Discussions Finder. No network, no database."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

OUTREACH = Path(__file__).resolve().parent.parent / "web" / "src" / "kitepulse" / "outreach"
GH_CONFIG = OUTREACH / "github" / "config"
if str(OUTREACH) not in sys.path:
    sys.path.insert(0, str(OUTREACH))

from common import config  # noqa: E402
from common import thread as t  # noqa: E402
from common.config import Community, Pace, Query  # noqa: E402
from common.match import matches  # noqa: E402
from github import client as gh_client  # noqa: E402
from github.client import GithubClient, GithubError, search_string, token_from_env  # noqa: E402
from github.finder import find_github  # noqa: E402

NOW = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
UA = "kitepulse-outreach-test/0 (+https://example.invalid)"
TOKEN = "test-token"


def _iso(hours_ago: float) -> str:
    return (NOW - timedelta(hours=hours_ago)).isoformat().replace("+00:00", "Z")


def disc(n, title, *, body="", repo="someone/tool", author="asker", hours_ago=2,
         closed=False, locked=False, archived=False, answered=None, comments=0):
    return {"id": f"D_{n}", "number": n, "title": title, "bodyText": body,
            "url": f"https://github.com/{repo}/discussions/{n}", "createdAt": _iso(hours_ago),
            "closed": closed, "locked": locked, "isAnswered": answered,
            "repository": {"nameWithOwner": repo, "isArchived": archived},
            "category": {"name": "Q&A"}, "author": {"login": author},
            "comments": {"totalCount": comments}}


class FakeGitHub:
    """MockTransport: robots.txt (404), GraphQL search and comment authors.

    `results` maps a phrase to its pages of discussions; `status` overrides the
    HTTP status of the next GraphQL responses, one per call."""

    def __init__(self, results=None, *, comments=None, status=None, errors=None,
                 robots=(404, "")):
        self.results = results or {}
        self.comments = comments or {}
        self.status = list(status or [])
        self.errors = errors
        self.robots = robots
        self.calls: list[httpx.Request] = []
        self.bodies: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(self.robots[0], text=self.robots[1])
        assert request.url.path == "/graphql"
        body = json.loads(request.content)
        self.bodies.append(body)
        if self.status:
            code = self.status.pop(0)
            if code != 200:
                return httpx.Response(code, text="bad gateway")
        if self.errors:
            return httpx.Response(200, json={"data": {"search": None}, "errors": self.errors})
        v = body["variables"]
        if "ids" in v:
            return httpx.Response(200, json={"data": {"nodes": [
                {"id": i, "comments": self.comments[i]} for i in v["ids"]]}})
        phrase = v["q"].split('"')[1]
        pages = self.results.get(phrase, [[]])
        page = int(v["after"] or 0)
        more = page + 1 < len(pages)
        return httpx.Response(200, json={"data": {"search": {
            "discussionCount": sum(len(p) for p in pages),
            "pageInfo": {"hasNextPage": more, "endCursor": str(page + 1) if more else None},
            "nodes": pages[page]}}})


def client_for(fake: FakeGitHub) -> GithubClient:
    return GithubClient(UA, TOKEN, http=httpx.Client(transport=httpx.MockTransport(fake)),
                        sleep=lambda _s: None)


PENDING = Community("github", "GitHub Discussions", "pending_review", "https://x.invalid")
ALLOWED = Community("github", "GitHub Discussions", "allowed", "https://x.invalid")
BLOCKED = Community("github", "GitHub Discussions", "not_allowed", "https://x.invalid")
NO_TEAM = Pace(max_thread_age_days=7, team_accounts=())
TEAM = Pace(max_thread_age_days=7, team_accounts=("Our_Team",))
USAGE_LIMIT = (Query("claude-limits", "usage limit"),)


def run(fake, *, queries=USAGE_LIMIT, pace=NO_TEAM, community=ALLOWED, max_pages=8):
    return find_github(client_for(fake), queries=list(queries), pace=pace,
                       community=community, now=NOW, max_pages=max_pages)


# --- the search string -----------------------------------------------------

def test_the_phrase_is_quoted_scoped_to_title_and_body_and_dated():
    assert search_string("usage limit", since=NOW - timedelta(days=7)) == (
        '"usage limit" in:title,body created:>=2026-10-30 sort:created-desc')
    with pytest.raises(GithubError):
        search_string('say "hi"', since=NOW)


# --- finder ----------------------------------------------------------------

def test_a_confirmed_hit_becomes_a_thread():
    fake = FakeGitHub({"usage limit": [[disc(1, "Hit the usage limit again", body="Help")]]})
    result = run(fake)
    th = result.kept[0]
    assert (th.source, th.kind, th.ext_id, th.community) == (
        "github", "discussion", "someone/tool#1", "someone/tool")
    assert th.url == "https://github.com/someone/tool/discussions/1"
    assert (th.author, th.body, th.matched_phrases) == ("asker", "Help", ["usage limit"])
    assert (result.phrases[0].reported, result.phrases[0].confirmed) == (1, 1)


def test_a_hit_the_matcher_does_not_confirm_is_counted_not_kept():
    fake = FakeGitHub({"usage limit": [[disc(1, "Limited usage", body="ok"),
                                        disc(2, "Usage dashboards", body="no limits here",
                                             repo="a/b"),
                                        disc(3, "Something else", body="unrelated")]]})
    result = run(fake)
    assert {th.ext_id for th in result.threads} == {"someone/tool#1", "a/b#2"}
    assert (result.phrases[0].retrieved, result.phrases[0].confirmed) == (3, 2)


def test_one_discussion_found_by_two_phrases_is_one_thread():
    d = disc(1, "Claude usage limit and token cost", body="")
    fake = FakeGitHub({"usage limit": [[d]], "token cost": [[d]]})
    result = run(fake, queries=(Query("claude-limits", "usage limit"),
                                Query("ai-cost-per-developer", "token cost")))
    assert len(result.threads) == 1
    assert result.threads[0].matched_problems == ["claude-limits", "ai-cost-per-developer"]


def test_pages_are_followed_and_the_page_limit_is_named():
    pages = [[disc(1, "usage limit A")], [disc(2, "usage limit B")], [disc(3, "usage limit C")]]
    assert len(run(FakeGitHub({"usage limit": pages})).threads) == 3
    short = run(FakeGitHub({"usage limit": pages}), max_pages=2)
    assert len(short.threads) == 2 and not short.phrases[0].complete
    assert any("1 of 3 results GitHub reported were NOT read" in line
               for line in short.checks_not_run)


def test_closed_locked_archived_and_blocked_are_dropped_with_their_reason():
    fake = FakeGitHub({"usage limit": [[
        disc(1, "usage limit A", closed=True), disc(2, "usage limit B", locked=True),
        disc(3, "usage limit C", archived=True), disc(4, "usage limit D"),
        disc(5, "usage limit E", hours_ago=24 * 7 + 2)]]})
    reasons = {th.ext_id[-1]: th.drop_reason for th in run(fake).threads}
    assert reasons == {"1": t.CLOSED, "2": t.CLOSED, "3": t.CLOSED, "4": None, "5": t.TOO_OLD}
    blocked = run(FakeGitHub({"usage limit": [[disc(4, "usage limit D")]]}), community=BLOCKED)
    assert [th.drop_reason for th in blocked.threads] == [t.COMMUNITY_NOT_ALLOWED]


def test_flags_pending_answered_and_posted_by_the_repo_owner():
    fake = FakeGitHub({"usage limit": [[
        disc(1, "usage limit A", answered=True),
        disc(2, "usage limit B", repo="Maker/tool", author="maker"),
        disc(3, "usage limit C", answered=None)]]})
    flags = {th.ext_id[-1]: th.flags for th in run(fake, community=PENDING).threads}
    assert flags == {"1": [t.COMMUNITY_PENDING_REVIEW, t.ANSWERED],
                     "2": [t.COMMUNITY_PENDING_REVIEW, t.POSTED_BY_REPO_OWNER],
                     "3": [t.COMMUNITY_PENDING_REVIEW]}


def test_team_check_reads_only_discussions_with_comments_and_flags_partial_reads():
    fake = FakeGitHub(
        {"usage limit": [[disc(1, "usage limit A", comments=2),
                          disc(2, "usage limit B", comments=60),
                          disc(3, "usage limit C", comments=0)]]},
        comments={
            "D_1": {"totalCount": 2, "nodes": [
                {"author": {"login": "x"}, "replies": {"totalCount": 1, "nodes": [
                    {"author": {"login": "our_team"}}]}}]},
            "D_2": {"totalCount": 60, "nodes": [
                {"author": {"login": "y"}, "replies": {"totalCount": 0, "nodes": []}}]},
        })
    result = run(fake, pace=TEAM)
    by = {th.ext_id[-1]: th for th in result.threads}
    assert by["1"].drop_reason == t.ALREADY_ANSWERED   # a team reply, case-insensitive
    assert by["2"].flags == [t.TEAM_CHECK_PARTIAL]
    assert by["3"].status == t.STATUS_FOUND
    asked = [b["variables"]["ids"] for b in fake.bodies if "ids" in b["variables"]]
    assert asked == [["D_1", "D_2"]]


def test_no_team_accounts_means_no_comment_query_and_the_check_is_named():
    fake = FakeGitHub({"usage limit": [[disc(1, "usage limit A", comments=4)]]})
    result = run(fake)
    assert any(line.startswith("already_answered") for line in result.checks_not_run)
    assert not any("ids" in b["variables"] for b in fake.bodies)


# --- failures ---------------------------------------------------------------

def test_errors_beside_partial_data_fail_the_phrase():
    fake = FakeGitHub({"usage limit": [[disc(1, "usage limit A")]]},
                      errors=[{"type": "RESOURCE_LIMITS_EXCEEDED", "message": "too big"}])
    result = run(fake)
    assert result.threads == []
    assert "RESOURCE_LIMITS_EXCEEDED" in result.errors[0]


def test_a_502_is_retried_once_and_a_second_fails_only_that_phrase():
    ok = run(FakeGitHub({"usage limit": [[disc(1, "usage limit A")]]}, status=[502]))
    assert len(ok.kept) == 1
    fake = FakeGitHub({"usage limit": [[disc(1, "usage limit A")]],
                       "token cost": [[disc(2, "token cost B")]]}, status=[502, 502])
    result = run(fake, queries=(Query("a", "usage limit"), Query("b", "token cost")))
    assert [th.ext_id[-1] for th in result.threads] == ["2"]
    assert "HTTP 502" in result.errors[0]
    assert any("1 of 2 phrases failed" in line for line in result.checks_not_run)


def test_a_result_older_than_the_date_qualifier_fails_the_phrase():
    fake = FakeGitHub({"usage limit": [[disc(1, "usage limit A", hours_ago=24 * 30)]]})
    result = run(fake)
    assert result.threads == [] and "date qualifier was ignored" in result.errors[0]


def test_robots_disallowing_graphql_sends_nothing():
    fake = FakeGitHub({"usage limit": [[disc(1, "usage limit A")]]},
                      robots=(200, "User-agent: *\nDisallow: /graphql\n"))
    result = run(fake)
    assert result.threads == [] and "disallows /graphql" in result.errors[0]
    assert [c.url.path for c in fake.calls] == ["/robots.txt"]


# --- the client -------------------------------------------------------------

def test_every_request_carries_the_user_agent_and_token_and_only_queries_are_sent():
    fake = FakeGitHub({"usage limit": [[disc(1, "usage limit A")]]})
    run(fake)
    gql = [c for c in fake.calls if c.url.path == "/graphql"]
    assert all(c.headers["User-Agent"] == UA for c in fake.calls)
    assert all(c.headers["Authorization"] == f"Bearer {TOKEN}" for c in gql)
    assert all(b["query"].lstrip().startswith("query") for b in fake.bodies)
    with pytest.raises(GithubError, match="only GraphQL queries"):
        client_for(fake).graphql("subscription { x }", {})


def test_the_token_is_kite_pulses_own_with_no_fallback(monkeypatch):
    monkeypatch.delenv(gh_client.TOKEN_ENV, raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "mibs-token")
    with pytest.raises(GithubError, match="KP_GITHUB_TOKEN is not set"):
        token_from_env()
    monkeypatch.setenv(gh_client.TOKEN_ENV, " kp-token ")
    assert token_from_env() == "kp-token"
    with pytest.raises(GithubError):
        GithubClient(UA, " ")


# --- config ----------------------------------------------------------------

def test_the_shipped_config_loads():
    c = config.community("github", GH_CONFIG)
    assert c.vendor_replies in config.VENDOR_REPLY_STATES
    queries = config.queries("github", GH_CONFIG)
    assert queries and all(matches(q.phrase, q.phrase) for q in queries)
    assert all(len(search_string(q.phrase, since=NOW)) <= gh_client.MAX_QUERY_CHARS
               for q in queries)
    assert config.pace("github", GH_CONFIG).max_thread_age_days >= 1
