"""Which upstream served a call, recorded instead of dropped (#397, #381).

OpenRouter routes one model across ~15 endpoints and names the one it used on
every streamed chunk (`"provider"`), with a generation id on each chunk and on
the `X-Generation-Id` header. The client read `model` and dropped both, so on
2026-09-24 seven NextBit failures - five of them unread after a retry - could
not say whether the retry had gone back to NextBit or somewhere else.

Four claims, each a separate test class:

  1. a successful call carries `provider` and `generation_id` on `Completion`;
  2. a failed call NAMES its upstream in the `ExtractorUnavailable` message,
     because a failure never becomes a `Completion` and the message is the only
     thing the retry loop logs;
  3. absent stays absent: a stream that names no upstream says "not reported",
     never a blank and never a guess (rule 6);
  4. the per-thread console line prints it.
"""
from __future__ import annotations

import contextlib
import json

import pytest

from judge import fetch_console


def _client():
    """Resolved when a test RUNS, not when the file is collected.

    ⚠ `tests/test_extract_client_total_timeout.py` calls `importlib.reload` on
      this module, which replaces `ExtractorUnavailable` with a new class. A
      name imported at collection time then no longer matches what the client
      raises, and `pytest.raises` misses it - but only when that file happens to
      run first. Looking the classes up at call time is immune to that.
    """
    import importlib

    return importlib.import_module("judge.extract.client")


def _call():
    return _client().OpenRouterClient(api_key="k").complete(
        system="s", user="u", tool_schema=SCHEMA)

SCHEMA: dict[str, object] = {"type": "object", "properties": {}}


def _sse(**event) -> str:
    return "data: " + json.dumps(event)


class _Canned:
    status_code = 200

    def __init__(self, lines, headers=None, status_code=200, text=""):
        self._lines = lines
        self.headers = headers or {}
        self.status_code = status_code
        self.text = text

    def iter_lines(self):
        yield from self._lines

    def read(self):
        return b""


def _patch_stream(monkeypatch, response):
    import httpx

    @contextlib.contextmanager
    def _stream(*args, **kwargs):
        yield response

    monkeypatch.setattr(httpx, "stream", _stream)


def _answer(provider="DeepInfra", gen="gen-abc123"):
    return [
        _sse(id=gen, provider=provider, model="deepseek/deepseek-v4-flash",
             choices=[{"delta": {"tool_calls": [{"function": {"arguments": "{}"}}]}}]),
        _sse(id=gen, provider=provider, choices=[{"finish_reason": "tool_calls", "delta": {}}],
             usage={"prompt_tokens": 10, "completion_tokens": 2}),
        "data: [DONE]",
    ]


class TestASuccessfulCallCarriesItsUpstream:
    def test_provider_and_generation_id_reach_the_completion(self, monkeypatch):
        _patch_stream(monkeypatch, _Canned(_answer("DeepInfra", "gen-abc123")))

        c = _call()

        assert c.provider == "DeepInfra"
        assert c.generation_id == "gen-abc123"

    def test_the_header_supplies_the_id_when_no_chunk_does(self, monkeypatch):
        lines = [
            _sse(provider="NextBit", choices=[{"delta": {}, "finish_reason": "tool_calls"}]),
            "data: [DONE]",
        ]
        _patch_stream(monkeypatch, _Canned(lines, headers={"X-Generation-Id": "gen-hdr"}))

        c = _call()

        assert c.generation_id == "gen-hdr"


class TestAFailedCallNamesItsUpstream:
    def test_a_mid_stream_error_says_which_upstream_failed(self, monkeypatch):
        # The exact shape of 2026-09-24's NextBit failures: an error event
        # carrying the provider, and no choices.
        lines = [
            _sse(id="gen-nb1", provider="NextBit",
                 error={"code": 502, "message": "Upstream error from NextBit: upstream model "
                        "did not return a valid tool call for the requested tool_choice"}),
            "data: [DONE]",
        ]
        _patch_stream(monkeypatch, _Canned(lines))

        with pytest.raises(_client().ExtractorUnavailable) as exc:
            _call()

        assert "[upstream NextBit, generation gen-nb1]" in str(exc.value)
        assert exc.value.transient, "the classification must not change with the message"

    def test_an_http_refusal_carries_the_header_id(self, monkeypatch):
        _patch_stream(monkeypatch, _Canned([], headers={"X-Generation-Id": "gen-503"},
                                           status_code=503, text="busy"))

        with pytest.raises(_client().ExtractorUnavailable) as exc:
            _call()

        assert "generation gen-503" in str(exc.value)
        assert "upstream not reported" in str(exc.value)


class TestAbsentStaysAbsent:
    def test_a_stream_that_names_no_upstream_leaves_it_none(self, monkeypatch):
        lines = [_sse(choices=[{"delta": {}, "finish_reason": "tool_calls"}]), "data: [DONE]"]
        _patch_stream(monkeypatch, _Canned(lines))

        c = _call()

        assert c.provider is None and c.generation_id is None

    def test_a_failure_with_no_upstream_says_not_reported(self, monkeypatch):
        err = {"code": 504, "message": "Upstream idle timeout exceeded"}
        lines = [_sse(error=err), "data: [DONE]"]
        _patch_stream(monkeypatch, _Canned(lines))

        with pytest.raises(_client().ExtractorUnavailable) as exc:
            _call()

        assert "[upstream not reported, generation not reported]" in str(exc.value)


class TestTheThreadLinePrintsIt:
    def _line(self, **extra):
        rec = {"kind": "thread", "index": 1, "total": 1, "thread_context_id": "tc",
               "posts": 1, "verified": 0, "rejected": 0, "unsalvaged": 0,
               "unclassified": 0, "proposed": 0, "tokens_in": 10, "tokens_out": 2, **extra}
        return "\n".join(fetch_console.render(rec, model_version_id="mv"))

    def test_each_call_is_named_in_order(self):
        assert "via NextBit, DeepInfra" in self._line(upstreams=["NextBit", "DeepInfra"])

    def test_an_unnamed_call_prints_as_not_reported(self):
        assert "via not reported" in self._line(upstreams=[None])

    def test_nothing_is_printed_when_nothing_was_recorded(self):
        assert "via" not in self._line()


class TestTheBilledCostIsRecordedNotComputed:
    """The streamed `usage` chunk carries `cost` in USD. Recorded as reported,
    and absent stays absent: None, never 0, which would read as free."""

    def test_a_reported_cost_reaches_the_completion(self, monkeypatch):
        lines = [
            _sse(provider="NextBit", choices=[{"delta": {}, "finish_reason": "tool_calls"}],
                 usage={"prompt_tokens": 9210, "completion_tokens": 512, "cost": 0.0005047}),
            "data: [DONE]",
        ]
        _patch_stream(monkeypatch, _Canned(lines))

        c = _call()

        assert c.reported_cost_usd == pytest.approx(0.0005047)

    def test_no_reported_cost_is_none_not_zero(self, monkeypatch):
        _patch_stream(monkeypatch, _Canned(_answer()))

        c = _call()

        assert c.reported_cost_usd is None

    def test_the_line_prints_billed_only_when_every_call_reported(self):
        line = TestTheThreadLinePrintsIt()._line
        assert "billed $0.002010" in line(reported_costs=[0.00151, 0.0005])
        partial = line(reported_costs=[0.00151, None])
        assert "billed $" not in partial
        assert "not reported for every call" in partial


class TestAFailedAttemptIsNotHiddenInsideTheBill:
    """A retried attempt (#399) never becomes a Completion, so it is ABSENT
    from `reported_costs`, not None in it - and `all(...)` cannot see an
    element that was never appended. The line names what it leaves out."""

    def test_a_recovered_thread_says_its_failed_attempts_are_not_in_the_sum(self):
        line = TestTheThreadLinePrintsIt()._line(reported_costs=[0.00119], failed_attempts=1)
        assert "billed $0.001190 + 1 failed attempt(s) not reported" in line

    def test_a_clean_thread_prints_the_bill_alone(self):
        line = TestTheThreadLinePrintsIt()._line(reported_costs=[0.00119])
        assert "failed attempt" not in line

    def test_the_pipeline_result_carries_the_count(self):
        from judge.pipeline import PipelineResult

        assert "failed_attempts" in PipelineResult.__dataclass_fields__
        assert PipelineResult.__dataclass_fields__["failed_attempts"].default == 0

    def test_the_retry_loop_sets_it_from_the_attempt_that_succeeded(self):
        """Source-level, in the style of test_one_bad_response_ends_a_thread:
        the count is taken inside the retry loop, from the attempt number, on
        the success path - so attempt 2 succeeding records 1 failure."""
        import pathlib

        src = (pathlib.Path(__file__).resolve().parents[1] / "judge" / "pipeline.py").read_text(
            encoding="utf-8")
        loop = src[src.index("for attempt in range(1, EXTRACT_ATTEMPTS + 1):"):]
        success = loop[:loop.index("except ExtractionRefused")]
        assert "result.failed_attempts = attempt - 1" in success
        assert success.index("result.failed_attempts") < success.index("break")
