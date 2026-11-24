"""X: a failure that may pass is tried once more, and every failure names its cause.

21-23 Nov 2026: 40 scheduled runs lost their whole X harvest to one failed first
request, recorded only as a count. These pin the retry (which failures, how many
times, the wait) and that a recovered failure is still recorded, never hidden.
No network: requests are answered by `httpx.MockTransport`.
"""
from __future__ import annotations

import httpx
import pytest

from collect.adapters import x as x_module
from collect.adapters.x import TRANSIENT_RETRY_WAIT_SECONDS, XHarvester
from collect.industry_ai.harvest import failure_of


class _Stored:
    ref = "raw:test"


class _Store:
    def put(self, content, namespace=None):
        return _Stored()


class _NoWait:
    def wait(self, url):
        return None


def _harvester(answers, monkeypatch):
    """A harvester whose requests get `answers` in order: a status code, a
    (status, quota remaining) pair, or an exception class to raise. Returns
    (harvester, requests made, sleeps)."""
    monkeypatch.setattr(x_module, "record_rapidapi_quota", lambda **kw: None)
    queue, seen, sleeps = list(answers), [], []

    def handler(request):
        seen.append(request)
        answer = queue.pop(0)
        if isinstance(answer, type):
            raise answer("boom", request=request)
        status, remaining = answer if isinstance(answer, tuple) else (answer, 98000)
        return httpx.Response(status, json={}, headers={
            "x-ratelimit-requests-remaining": str(remaining),
            "x-ratelimit-requests-limit": "100000"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    h = XHarvester(client=client, store=_Store(), api_key="k", provider="twitter241",
                   limiter=_NoWait(), max_pages=1, sleeper=sleeps.append)
    return h, seen, sleeps


@pytest.mark.parametrize("first", [500, 502, 503, 504, 429])
def test_a_status_that_may_pass_is_tried_once_more_and_still_recorded(first, monkeypatch):
    h, seen, sleeps = _harvester([first, 200], monkeypatch)
    run = h.search("Claude Code")
    assert len(seen) == 2 and sleeps == [TRANSIENT_RETRY_WAIT_SECONDS]
    assert run.pages_stored == 1, "the retry's answer is used"
    assert run.recovered_failures == [f"HTTP {first}"], "a recovered failure is never hidden"
    assert run.failures == [], "...and never listed as one that stood"
    assert (run.http_errors, run.retries, run.recovered) == (1, 1, 1)
    assert run.truncated_by is None, "a 429 the retry got past truncated nothing"


@pytest.mark.parametrize("timeout", [httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout])
def test_a_timeout_is_tried_once_more(timeout, monkeypatch):
    h, seen, _ = _harvester([timeout, 200], monkeypatch)
    run = h.search("Claude Code")
    assert len(seen) == 2 and run.recovered_failures == [timeout.__name__]
    assert run.recovered == 1


def test_a_429_with_the_quota_spent_is_not_retried(monkeypatch):
    """#652 review: waiting 5 s does not refill a quota, and the retry is metered."""
    h, seen, sleeps = _harvester([(429, 0)], monkeypatch)
    run = h.search("Claude Code")
    assert len(seen) == 1 and sleeps == []
    assert run.failures == ["HTTP 429"] and run.truncated_by == "rate-limit"
    assert run.quota_exhausted


def test_only_once_more_and_then_it_stands(monkeypatch):
    h, seen, sleeps = _harvester([503, 503], monkeypatch)
    run = h.search("Claude Code")
    assert len(seen) == 2 and len(sleeps) == 1
    assert run.failures == ["HTTP 503", "HTTP 503"]
    assert (run.http_errors, run.recovered, run.pages_stored) == (2, 0, 0)


def test_a_rate_limit_that_stays_marks_the_run_truncated(monkeypatch):
    h, _, _ = _harvester([429, 429], monkeypatch)
    assert h.search("Claude Code").truncated_by == "rate-limit"


@pytest.mark.parametrize("answer",
                         [401, 403, 404, 400, httpx.ConnectError, httpx.ConnectTimeout])
def test_a_failure_waiting_cannot_cure_is_not_retried(answer, monkeypatch):
    """A wrong key, a wrong endpoint or a bad request does not pass with time; a
    connection failure or connect timeout already had its retries in the
    transport, so each kind is retried in one place only (#652 review)."""
    h, seen, sleeps = _harvester([answer], monkeypatch)
    run = h.search("Claude Code")
    assert len(seen) == 1 and sleeps == []
    assert run.failures == [answer.__name__ if isinstance(answer, type) else f"HTTP {answer}"]


def test_the_industry_ai_agent_reads_a_recovered_query_as_ok(monkeypatch):
    """`failure_of` marks a query `error`; one that answered on its retry is not."""
    h, _, _ = _harvester([503, 200], monkeypatch)
    assert failure_of(h.search("q")) is None
    h, _, _ = _harvester([503, 503], monkeypatch)
    assert failure_of(h.search("q")) == "2 request(s) failed (HTTP 503)"


def test_a_recovered_cause_is_not_named_among_the_failures(monkeypatch):
    """#652 review: one request recovers from a 503, another fails 504 twice. Only
    the 504s stood, so only they are named."""
    h, _, _ = _harvester([503, 200, 504, 504], monkeypatch)
    run = h.search("q")
    h.search("q", run=run)
    assert run.failures == ["HTTP 504", "HTTP 504"]
    assert run.recovered_failures == ["HTTP 503"]
    assert failure_of(run) == "2 request(s) failed (HTTP 504)"
