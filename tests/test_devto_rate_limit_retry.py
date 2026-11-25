"""dev.to: an HTTP 429 is tried once more, and every failed attempt is still recorded.

The Industry AI agent's first real run lost 3 dev.to queries to 429s (2026-11-24),
its second 1 of 18 (2026-11-25), and the rotation runs ten domains at a time. Only a
429 is retried: this platform answers a zero-match query with a 500 or a hang
(collect/adapters/devto.py), so retrying those would learn nothing. No network:
requests are answered by `httpx.MockTransport`.
"""
from __future__ import annotations

import httpx
import pytest

from collect.adapters.devto import RATE_LIMIT_RETRY_WAIT_SECONDS, DevtoHarvester
from collect.industry_ai.harvest import failure_of


class _Stored:
    ref = "raw:test"


class _Store:
    def put(self, content, namespace=None):
        return _Stored()


class _NoWait:
    def wait(self, url):
        return None


def _harvester(answers):
    """Requests get `answers` in order: a status code, or an exception class."""
    queue, seen, sleeps = list(answers), [], []

    def handler(request):
        seen.append(request)
        answer = queue.pop(0)
        if isinstance(answer, type):
            raise answer("boom", request=request)
        return httpx.Response(answer, json=[] if answer == 200 else {"error": "x"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    h = DevtoHarvester(client=client, store=_Store(), limiter=_NoWait(), sleeper=sleeps.append)
    return h, seen, sleeps


def test_a_429_is_tried_once_more_and_the_recovery_is_recorded():
    h, seen, sleeps = _harvester([429, 200])
    run = h.search("AI code review")
    assert len(seen) == 2 and sleeps == [RATE_LIMIT_RETRY_WAIT_SECONDS]
    assert run.pages_stored == 1, "the retry's answer is used"
    # Still recorded: counted, and named as recovered rather than as a failure.
    assert run.http_errors == 1 and run.recovered == 1
    assert run.recovered_failures == ["HTTP 429"] and run.failures == []
    assert failure_of(run) is None, "a recovered attempt is not a failed query"


def test_two_429s_stand_and_both_are_named():
    h, seen, sleeps = _harvester([429, 429])
    run = h.search("AI code review")
    assert len(seen) == 2 and sleeps == [RATE_LIMIT_RETRY_WAIT_SECONDS]
    assert run.http_errors == 2 and run.recovered == 0
    assert run.failures == ["HTTP 429", "HTTP 429"]
    assert "2 request(s) failed (HTTP 429)" in failure_of(run)


@pytest.mark.parametrize("answer", [500, 404, httpx.ReadTimeout, httpx.ConnectError])
def test_anything_but_a_429_is_not_retried(answer):
    """A 500 or a hang is this platform's answer to a zero-match query."""
    h, seen, sleeps = _harvester([answer])
    run = h.search("AI code review")
    assert len(seen) == 1 and sleeps == []
    assert run.recovered == 0 and run.recovered_failures == []
    if answer is httpx.ReadTimeout:
        assert run.timeouts == 1, "a timeout is counted apart, as before"
    else:
        assert run.http_errors == 1 and len(run.failures) == 1
