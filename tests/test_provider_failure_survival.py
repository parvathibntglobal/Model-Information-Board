"""A provider failure costs one thread, and the spend is recorded anyway.

Two defects, 2026-09-24, and they compound:

  1. `OpenRouterClient.complete` wrote its `spend_ledger` row AFTER the
     mid-stream error raise, so a 502/504 left no row for tokens already
     generated and billed. The deadline abandon and a Stop had the same gap.
  2. `Pipeline.run_all` let `ExtractorUnavailable` propagate, so one provider
     failure ended the batch and every thread after it went unread.

No database: `Pipeline.run` is stubbed, and the stores only hold the
connection until a method is called on them.
"""
from __future__ import annotations

import contextlib
import json
from types import SimpleNamespace

import pytest

from judge import pipeline as pipeline_mod
from judge import spend_ledger
from judge.extract.budget import Budget, BudgetExhausted
from judge.extract.client import ExtractorUnavailable, OpenRouterClient
from judge.extract.runner import ThreadInput

SCHEMA: dict[str, object] = {"type": "object", "properties": {}}


# ── 1 · the client ────────────────────────────────────────────────────────


def _sse(**event) -> str:
    return "data: " + json.dumps(event)


class _Canned:
    status_code = 200
    #: The client reads `X-Generation-Id` before the stream (#481); a real
    #: response always carries headers, and none are needed here.
    headers: dict = {}

    def __init__(self, lines):
        self._lines = lines

    def iter_lines(self):
        yield from self._lines

    def read(self):
        return b""


@pytest.fixture
def recorded(monkeypatch) -> list[dict]:
    rows: list[dict] = []
    monkeypatch.setattr(spend_ledger, "record", lambda **kw: rows.append(kw))
    return rows


def _stream(monkeypatch, lines) -> None:
    import httpx

    @contextlib.contextmanager
    def _fake(*args, **kwargs):
        yield _Canned(lines)

    monkeypatch.setattr(httpx, "stream", _fake)


def _live_unavailable():
    """The class the client raises NOW, looked up at call time.

    `tests/test_extract_client_total_timeout.py` reloads `judge.extract.client`,
    which rebinds `ExtractorUnavailable`; the name imported at the top of this
    file is then a different class and `pytest.raises` stops matching it - the
    trap `tests/test_extract_truncation.py` records. Passes alone, fails only
    when the two files run together.
    """
    import judge.extract.client as client_module

    return client_module.ExtractorUnavailable


class TestTheClientRecordsSpendOnEveryExit:
    def test_a_mid_stream_error_still_writes_the_row_with_its_usage(
        self, monkeypatch, recorded
    ):
        _stream(monkeypatch, [
            _sse(choices=[{"delta": {"tool_calls": [
                {"function": {"arguments": '{"claims": [{"q'}}]}}]),
            _sse(choices=[], usage={"prompt_tokens": 4000, "completion_tokens": 900}),
            _sse(error={"code": 502, "message": "upstream went away"}),
            "data: [DONE]",
        ])

        with pytest.raises(_live_unavailable(), match="mid-stream"):
            OpenRouterClient(api_key="k").complete(system="s", user="u", tool_schema=SCHEMA)

        assert len(recorded) == 1
        assert recorded[0]["input_tokens"] == 4000
        assert recorded[0]["output_tokens"] == 900

    def test_an_error_before_any_usage_records_zeros_which_read_as_unmetered(
        self, monkeypatch, recorded
    ):
        _stream(monkeypatch, [_sse(error={"code": 504, "message": "timeout"})])

        with pytest.raises(_live_unavailable()):
            OpenRouterClient(api_key="k").complete(system="s", user="u", tool_schema=SCHEMA)

        assert len(recorded) == 1
        assert recorded[0]["input_tokens"] == 0 and recorded[0]["output_tokens"] == 0

    def test_a_stop_mid_call_still_writes_the_row(self, monkeypatch, recorded):
        class Stopped(Exception):
            pass

        def stop():
            raise Stopped

        _stream(monkeypatch, [_sse(choices=[{"delta": {}}])])
        client = OpenRouterClient(api_key="k", on_progress=stop)

        with pytest.raises(Stopped):
            client.complete(system="s", user="u", tool_schema=SCHEMA)

        assert len(recorded) == 1

    def test_a_clean_call_writes_exactly_one_row(self, monkeypatch, recorded):
        _stream(monkeypatch, [
            _sse(choices=[{"delta": {"tool_calls": [
                {"function": {"arguments": '{"claims": []}'}}]},
                "finish_reason": "tool_calls"}],
                 usage={"prompt_tokens": 10, "completion_tokens": 2}),
            "data: [DONE]",
        ])

        OpenRouterClient(api_key="k").complete(system="s", user="u", tool_schema=SCHEMA)

        assert len(recorded) == 1


# ── 2 · the batch ─────────────────────────────────────────────────────────


def _thread(tc_id: str) -> ThreadInput:
    return ThreadInput(
        thread_context_id=tc_id, flattened_text=f"text of {tc_id}",
        offset_map=(), raw_text_of={},
    )


def _result():
    return SimpleNamespace(
        stored_claim_ids=[], cells=[],
        extraction=SimpleNamespace(
            input_tokens=10, output_tokens=2, cached_input_tokens=0, schema_retries=0,
        ),
    )


@pytest.fixture
def pipe(monkeypatch, recorded):
    p = pipeline_mod.Pipeline(
        conn=None, client=None, capability_keys=["k"], extractor_model="m",
    )
    written: list[str] = []
    monkeypatch.setattr(
        p._ledger, "record", lambda record: written.append(record.thread_context_id)
    )
    p.written = written
    return p


def _script(monkeypatch, outcomes: dict[str, list]):
    """`Pipeline.run` returns or raises per thread, one outcome per call."""
    calls: list[str] = []

    def run(self, thread, **kwargs):
        calls.append(thread.thread_context_id)
        outcome = outcomes[thread.thread_context_id].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(pipeline_mod.Pipeline, "run", run)
    return calls


class TestTheBatchSurvivesAProviderFailure:
    """The batch-level half is main's #399 bounded retry, not this branch's.

    This branch built the same fix with a `Pipeline.unattempted` list; main
    built it with `ThreadResult.failed_attempts`, and the merge kept main's.
    Its skip, retry and refusal cases are pinned in
    `test_a_dead_stream_is_a_thread_not_a_run.py` and its siblings, so only
    the case they do not cover stays here.
    """

    def test_the_retry_is_checked_against_the_budget(self, monkeypatch, pipe):
        """The retry is a second paid call; a spent cap stops the batch before it."""
        _script(monkeypatch, {"a": [ExtractorUnavailable("502"), _result()]})
        budget = Budget(limit_usd=1.0)
        budget.spent_usd = 1.0 - budget.estimated_next_call_usd / 2

        with pytest.raises(BudgetExhausted):
            pipe.run_all(
                [_thread("a")], facts={}, model_version_of={}, already_extracted={},
                budget=budget,
            )
