"""An arXiv request that fails says why, and one that may pass is asked once more.

From 2026-10-25 to 2026-10-30 the scheduled fetch's arXiv stage failed for 29
model runs, every one reading only "2 request(s) failed": throttling and refusal
could not be told apart. No network, no database: the client is a fake.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx

from collect.adapters import arxiv


class FakeClient:
    """Answers each request with the next item: a status code, or an exception."""

    def __init__(self, *answers, headers=None):
        self.answers, self.headers, self.calls = list(answers), headers or {}, 0

    def get(self, url, params=None):
        self.calls += 1
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        request = httpx.Request("GET", url, params=params)
        return httpx.Response(answer, headers=self.headers, request=request)


def _get(client):
    waits = []
    h = arxiv.ArxivHarvester(client=client, store=None,
                             limiter=SimpleNamespace(wait=lambda url: None),
                             sleeper=waits.append)
    run = arxiv.ArxivRun(query="q", started_at=datetime.now(UTC))
    return h._get({"search_query": "q"}, run), run, waits


def test_a_503_that_passes_on_the_retry_is_not_a_failure():
    response, run, waits = _get(FakeClient(503, 200))
    assert response is not None and response.status_code == 200
    assert run.http_errors == 0 and run.failures == [] and run.retried == 1
    assert waits == [arxiv.RETRY_WAIT_SECONDS]


def test_a_failure_that_stays_failed_is_recorded_with_its_status():
    response, run, _ = _get(FakeClient(503, 503))
    assert response is None
    assert run.http_errors == 1 and run.failures == ["HTTP 503"] and run.retried == 1


def test_a_403_is_a_refusal_and_is_not_asked_again():
    client = FakeClient(403)
    response, run, waits = _get(client)
    assert response is None and client.calls == 1 and waits == []
    assert run.failures == ["HTTP 403"] and run.retried == 0


def test_retry_after_is_honoured_when_short_and_left_to_another_night_when_long():
    _, run, waits = _get(FakeClient(429, 200, headers={"Retry-After": "20"}))
    assert waits == [20.0] and run.failures == []
    client = FakeClient(429, headers={"Retry-After": "3600"})
    _, run, waits = _get(client)
    assert client.calls == 1 and waits == [] and run.failures == ["HTTP 429"]


def test_a_timeout_is_retried_and_named_by_its_kind():
    _, run, _ = _get(FakeClient(httpx.ReadTimeout("slow"), httpx.ReadTimeout("slow")))
    assert run.failures == ["ReadTimeout"] and run.retried == 1 and run.http_errors == 1


def test_the_stage_says_which_kind_of_failure(monkeypatch):
    import scripts.fetch_model as fm

    class Harvester:
        def harvest(self, query, terms=None, *, max_fetch=None):
            return SimpleNamespace(papers=[], stored=[], http_errors=1,
                                   failures=["HTTP 503"], retried=1)

        def write_documents(self, conn, run, retrieval_provenance):
            return SimpleNamespace(inserted=0)

    monkeypatch.setattr(fm, "_gated_harvester", lambda *a, **k: (Harvester(), None))
    monkeypatch.setattr(fm, "build_client", lambda **k: None)
    monkeypatch.setattr(fm, "RawStore", lambda *a, **k: None)
    stages = []
    prog = SimpleNamespace(stage=lambda *a, **k: stages.append((a, k)))
    fm.harvest_arxiv(SimpleNamespace(commit=lambda: None), prog, ["A", "B"], max_queries=2)
    final = stages[-1][1]
    assert final["failures"] == ["HTTP 503", "HTTP 503"] and final["retried"] == 2
    assert "2 request(s) failed (HTTP 503 x2); 2 retried" in final["detail"]


def test_retry_after_as_an_http_date_is_honoured_or_left_to_another_night():
    from email.utils import format_datetime

    soon = format_datetime(datetime.now(UTC) + timedelta(seconds=20), usegmt=True)
    _, run, waits = _get(FakeClient(503, 200, headers={"Retry-After": soon}))
    assert run.failures == [] and len(waits) == 1 and 0 < waits[0] <= 20
    later = format_datetime(datetime.now(UTC) + timedelta(hours=1), usegmt=True)
    client = FakeClient(503, headers={"Retry-After": later})
    _, run, waits = _get(client)
    assert client.calls == 1 and waits == [] and run.failures == ["HTTP 503"]
    _, run, waits = _get(FakeClient(503, 200, headers={"Retry-After": "not a date"}))
    assert waits == [arxiv.RETRY_WAIT_SECONDS]
