"""Each watch adapter tells "the provider answered: that is wrong or gone" from "the
provider failed" (#688 review, point 1), so the observer's stop-after-failures counts
only a provider that is down. A failure in `collect.http.ANSWERED_STATUSES` is counted
in the run record's `answered_errors`; X's 404 is a wrong endpoint, so it is not.
`provider_failed` (collect/industry_ai/harvest.py) reads the record. No network.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from collect.adapters import bluesky, hackernews, instagram, reddit
from collect.adapters import x as x_module
from collect.industry_ai.harvest import provider_failed
from collect.rawstore import RawStore

NOW = datetime(2026, 11, 27, tzinfo=UTC)
NO_WAIT = SimpleNamespace(wait=lambda url: None)


def _transport(status):
    return httpx.MockTransport(lambda request: httpx.Response(status, json={}))


@pytest.mark.parametrize("status, answered", [(400, 1), (404, 1), (500, 0), (429, 0),
                                              (403, 0)])
def test_bluesky(tmp_path, status, answered):
    h = bluesky.BlueskyHarvester(client=httpx.Client(transport=_transport(status)),
                                 store=RawStore(tmp_path, remote=None), limiter=NO_WAIT)
    run = bluesky.BlueskyRun(query="from:a.bsky.social", started_at=NOW)
    assert h.search(run) is None
    assert (run.http_errors, run.answered_errors) == (1, answered)
    assert provider_failed(run) is (answered == 0)


@pytest.mark.parametrize("status, answered", [(404, 1), (410, 1), (503, 0)])
def test_hackernews(tmp_path, status, answered):
    h = hackernews.HackerNewsHarvester(client=httpx.Client(transport=_transport(status)),
                                       store=RawStore(tmp_path, remote=None), limiter=NO_WAIT)
    run = hackernews.HnRun(query="hn:author:someone", started_at=NOW)
    assert h.search_stories("", since_ts=0, per_page=30, run=run, tags="author_someone") == []
    assert (run.http_errors, run.answered_errors) == (1, answered)
    assert provider_failed(run) is (answered == 0)


def test_hackernews_timeout_is_the_provider_failing(tmp_path):
    def boom(request):
        raise httpx.ReadTimeout("slow", request=request)

    h = hackernews.HackerNewsHarvester(client=httpx.Client(transport=httpx.MockTransport(boom)),
                                       store=RawStore(tmp_path, remote=None), limiter=NO_WAIT)
    run = hackernews.HnRun(query="hn:list:show_hn", started_at=NOW)
    h.search_stories("", since_ts=0, per_page=30, run=run, tags="show_hn")
    assert (run.http_errors, run.answered_errors) == (1, 0)
    assert provider_failed(run) is True


class _IgClient:
    def __init__(self, status):
        self.status = status

    def get(self, url, params=None, headers=None):
        return httpx.Response(self.status, content=json.dumps({}).encode(),
                              request=httpx.Request("GET", url))


@pytest.mark.parametrize("status, answered", [(404, 1), (400, 1), (500, 0), (401, 0)])
def test_instagram(monkeypatch, status, answered):
    monkeypatch.setattr(instagram, "settings", lambda: SimpleNamespace(
        instagram_provider="instagram-looter2", instagram_rapidapi_key=None, rapidapi_key="k"))
    monkeypatch.setattr(instagram, "record_rapidapi_quota", lambda **kw: True)
    h = instagram.InstagramHarvester(client=_IgClient(status), store=SimpleNamespace(),
                                     limiter=NO_WAIT, clock=lambda: NOW, sleeper=lambda s: None)
    run = h.user_feed("123", query="ig:gone.account")
    assert run.answered_errors == answered
    assert provider_failed(run) is (answered == 0)


def _x(monkeypatch, status):
    monkeypatch.setattr(x_module, "record_rapidapi_quota", lambda **kw: None)
    client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(status, json={}, headers={
            "x-ratelimit-requests-remaining": "9", "x-ratelimit-requests-limit": "10"})))
    return x_module.XHarvester(client=client, store=SimpleNamespace(put=None), api_key="k",
                               provider="twitter241", limiter=NO_WAIT, max_pages=1,
                               sleeper=lambda s: None)


def test_x_404_is_a_wrong_endpoint_not_an_answer(monkeypatch):
    run = _x(monkeypatch, 404).search("from:someone")
    assert (run.http_errors, run.answered_errors) == (1, 0)
    assert provider_failed(run) is True


def test_x_400_is_an_answer(monkeypatch):
    run = _x(monkeypatch, 400).search("from:someone")
    assert run.answered_errors == 1
    assert provider_failed(run) is False


@pytest.fixture
def reddit_host(monkeypatch):
    from collect import config

    monkeypatch.setenv("RAPIDAPI_HOST", "https://reddit34.p.rapidapi.com/getPopularPosts?sort=new")
    monkeypatch.setenv("RAPIDAPI_KEY", "test")
    monkeypatch.setattr(reddit, "record_rapidapi_quota", lambda **kw: None)
    config.settings.cache_clear()
    yield
    config.settings.cache_clear()


@pytest.mark.parametrize("status, body, answered", [
    (404, {}, 1),
    (502, {}, 0),
    # #691 review: a PRIVATE or QUARANTINED subreddit is Reddit answering (403 with a
    # reason), as Reddit sends it or wrapped by the provider; a 403 without one is the
    # gateway refusing the key, which fails every query alike.
    (403, {"reason": "private", "message": "Forbidden", "error": 403}, 1),
    (403, {"success": False, "data": {"reason": "quarantined"}}, 1),
    (403, {"message": "You are not subscribed to this API."}, 0),
    (403, ["not", "an", "object"], 0),
])
def test_reddit(tmp_path, reddit_host, status, body, answered):
    from collect.limiter import HostLimiter

    h = reddit.RedditHarvester(
        client=httpx.Client(transport=httpx.MockTransport(
            lambda request: httpx.Response(status, json=body))),
        store=RawStore(tmp_path / "raw_store"),
        limiter=HostLimiter(min_interval=0.0, clock=lambda: 0.0, sleeper=lambda _s: None),
        clock=lambda: NOW, sleeper=lambda _s: None,
    )
    run = h.list_subreddit("GoneSubreddit", pages=1)
    assert run.answered_errors == answered
    assert provider_failed(run) is (answered == 0)


def test_a_reddit_thread_fetch_absorbs_the_field():
    """`_get` writes `answered_errors`; a comment fetch goes through `_quota_sink`,
    which has no use for it and must not fail on it."""
    sink = reddit._quota_sink(reddit.ThreadFetch(thread_url="u", started_at=NOW))
    sink.answered_errors += 1
