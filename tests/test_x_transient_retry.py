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
    """A harvester whose requests get `answers` in order: a status code, or an
    exception class to raise. Returns (harvester, requests made, sleeps)."""
    monkeypatch.setattr(x_module, "record_rapidapi_quota", lambda **kw: None)
    queue, seen, sleeps = list(answers), [], []

    def handler(request):
        seen.append(request)
        answer = queue.pop(0)
        if isinstance(answer, type):
            raise answer("boom", request=request)
        return httpx.Response(answer, json={}, headers={
            "x-ratelimit-requests-remaining": "98000", "x-ratelimit-requests-limit": "100000"})

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
    assert run.failures == [f"HTTP {first}"], "a recovered failure is never hidden"
    assert (run.http_errors, run.retries, run.recovered) == (1, 1, 1)
    assert run.truncated_by is None, "a 429 the retry got past truncated nothing"


def test_a_timeout_is_tried_once_more(monkeypatch):
    h, seen, _ = _harvester([httpx.ReadTimeout, 200], monkeypatch)
    run = h.search("Claude Code")
    assert len(seen) == 2 and run.failures == ["ReadTimeout"] and run.recovered == 1


def test_only_once_more_and_then_it_stands(monkeypatch):
    h, seen, sleeps = _harvester([503, 503], monkeypatch)
    run = h.search("Claude Code")
    assert len(seen) == 2 and len(sleeps) == 1
    assert run.failures == ["HTTP 503", "HTTP 503"]
    assert (run.http_errors, run.recovered, run.pages_stored) == (2, 0, 0)


def test_a_rate_limit_that_stays_marks_the_run_truncated(monkeypatch):
    h, _, _ = _harvester([429, 429], monkeypatch)
    assert h.search("Claude Code").truncated_by == "rate-limit"


@pytest.mark.parametrize("answer", [401, 403, 404, 400, httpx.ConnectError])
def test_a_failure_waiting_cannot_cure_is_not_retried(answer, monkeypatch):
    """A wrong key, a wrong endpoint or a bad request does not pass with time;
    a connection failure already had its retries in the transport."""
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
