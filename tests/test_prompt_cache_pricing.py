"""Cached prompt tokens are billed at the cache-read rate, not the input rate.

DeepSeek caches the prompt prefix automatically, and the extraction prefix -
system prompt, then tool schema - is identical on every call of a run. Until
2026-09-24 nothing read `usage.prompt_tokens_details.cached_tokens`, so every
input token was charged at full rate in the cap, the ledger and the fetch log.

Three claims, tested separately because each has its own way to go wrong:

  1. the client READS the cached count and carries it on the `Completion`;
  2. cached tokens are MOVED to the cheaper rate, never added on top of
     `prompt_tokens`, which already includes them;
  3. a row that never recorded a cached count reads back as None, not 0.
"""
from __future__ import annotations

import contextlib
import json

import pytest

from judge import spend_ledger
from judge.ask.cost import Pricing
from judge.extract.budget import (
    DEFAULT_PRICING,
    MODEL_PRICING,
    Budget,
    cost_of_tokens,
)
from judge.extract.client import Completion, OpenRouterClient

SCHEMA: dict[str, object] = {"type": "object", "properties": {}}
RATE = Pricing(price_in=0.03, price_out=0.32, price_cached_read=0.016)


def _sse(**event) -> str:
    return "data: " + json.dumps(event)


class _Canned:
    status_code = 200

    def __init__(self, lines):
        self._lines = lines

    def iter_lines(self):
        yield from self._lines

    def read(self):
        return b""


def _patch(monkeypatch, lines) -> list[dict]:
    import httpx

    @contextlib.contextmanager
    def _stream(*args, **kwargs):
        yield _Canned(lines)

    monkeypatch.setattr(httpx, "stream", _stream)
    recorded: list[dict] = []
    monkeypatch.setattr(spend_ledger, "record", lambda **kw: recorded.append(kw))
    return recorded


class TestTheClientReadsTheCachedCount:
    def test_cached_tokens_reach_the_completion_and_the_ledger(self, monkeypatch):
        recorded = _patch(monkeypatch, [
            _sse(choices=[{"delta": {"tool_calls": [
                {"function": {"arguments": '{"claims": []}'}}]},
                "finish_reason": "tool_calls"}],
                 usage={"prompt_tokens": 5000, "completion_tokens": 600,
                        "prompt_tokens_details": {"cached_tokens": 3800,
                                                  "cache_write_tokens": 0}}),
            "data: [DONE]",
        ])

        completion = OpenRouterClient(api_key="k").complete(
            system="s", user="u", tool_schema=SCHEMA
        )

        assert completion.input_tokens == 5000
        assert completion.cached_input_tokens == 3800
        assert recorded[0]["cached_input_tokens"] == 3800

    def test_no_cache_detail_means_zero_cached_which_prices_at_full_rate(self, monkeypatch):
        """The over-stating direction: an absent detail never invents a discount."""
        recorded = _patch(monkeypatch, [
            _sse(choices=[], usage={"prompt_tokens": 10, "completion_tokens": 2}),
            "data: [DONE]",
        ])

        completion = OpenRouterClient(api_key="k").complete(
            system="s", user="u", tool_schema=SCHEMA
        )

        assert completion.cached_input_tokens == 0
        assert recorded[0]["cached_input_tokens"] == 0


class TestCachedTokensAreMovedNotAdded:
    def test_the_cached_part_is_billed_at_the_cache_rate(self):
        cost = cost_of_tokens(RATE, 5000, 600, cached_input_tokens=3800)
        expected = (1200 * 0.03 + 3800 * 0.016 + 600 * 0.32) / 1_000_000
        assert cost == pytest.approx(expected)

    def test_a_cache_hit_is_cheaper_than_the_same_call_uncached(self):
        assert cost_of_tokens(RATE, 5000, 600, 3800) < cost_of_tokens(RATE, 5000, 600)

    def test_cached_cannot_exceed_input(self):
        """A provider over-reporting cached tokens must not produce a credit."""
        assert cost_of_tokens(RATE, 100, 0, cached_input_tokens=999) == pytest.approx(
            100 * 0.016 / 1_000_000
        )

    def test_no_published_cache_rate_prices_cached_tokens_at_full_input(self):
        """Rule 6: a missing cache rate is not a discount."""
        bare = Pricing(price_in=0.03, price_out=0.32)
        assert cost_of_tokens(bare, 5000, 600, 3800) == cost_of_tokens(bare, 5000, 600)

    def test_the_budget_charges_the_discounted_figure(self):
        budget = Budget(limit_usd=None)
        charged = budget.charge(Completion(
            raw_arguments="{}", input_tokens=5000, output_tokens=600,
            cached_input_tokens=3800,
        ))
        assert charged == pytest.approx(cost_of_tokens(DEFAULT_PRICING, 5000, 600, 3800))

    def test_the_pre_call_estimate_still_assumes_no_cache_hit(self):
        """The guard must stop early rather than late: a cold cache pays full rate."""
        budget = Budget(limit_usd=1.0)
        from judge.extract.budget import ESTIMATED_INPUT_TOKENS, ESTIMATED_OUTPUT_TOKENS

        assert budget.estimated_next_call_usd == pytest.approx(
            cost_of_tokens(DEFAULT_PRICING, ESTIMATED_INPUT_TOKENS, ESTIMATED_OUTPUT_TOKENS)
        )

    def test_the_extractor_and_the_default_carry_a_cache_rate(self):
        assert DEFAULT_PRICING.price_cached_read == 0.016
        assert MODEL_PRICING["deepseek/deepseek-v4-flash-0731"].price_cached_read == 0.016


class TestTheLedgerRow:
    def test_the_file_row_carries_the_count_and_the_discounted_usd(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        call = spend_ledger.record(
            stage=spend_ledger.STAGE_EXTRACT,
            model="deepseek/deepseek-v4-flash-0731",
            input_tokens=5000, output_tokens=600, cached_input_tokens=3800,
            path=path, to_database=False,
        )

        assert call.usd == pytest.approx(cost_of_tokens(RATE, 5000, 600, 3800))
        (back,) = spend_ledger.read_all(path)
        assert back.cached_input_tokens == 3800
        assert back.usd == pytest.approx(call.usd)

    def test_a_row_written_before_the_field_existed_reads_as_unrecorded(self, tmp_path):
        """None, not 0: an old row never said whether the cache was hit."""
        path = tmp_path / "ledger.jsonl"
        path.write_text(json.dumps({
            "at": "2026-09-20T10:00:00+00:00", "stage": "extract",
            "model": "deepseek/deepseek-v4-flash", "in": 2010, "out": 589,
            "usd": 0.0004, "unpriced": False, "machine": "m", "run_id": None,
        }) + "\n", encoding="utf-8")

        (back,) = spend_ledger.read_all(path)
        assert back.cached_input_tokens is None


class TestReasoningTokensAreRecorded:
    """`completion_tokens_details.reasoning_tokens`, recorded 2026-09-24 after a
    16,384-token truncation on a 10,859-char post. None when unreported."""

    def test_the_client_reads_them(self, monkeypatch):
        _patch(monkeypatch, [
            _sse(choices=[], usage={"prompt_tokens": 12048, "completion_tokens": 16384,
                                    "completion_tokens_details": {"reasoning_tokens": 15900}}),
            "data: [DONE]",
        ])
        completion = OpenRouterClient(api_key="k").complete(
            system="s", user="u", tool_schema=SCHEMA
        )
        assert completion.reasoning_tokens == 15900

    def test_unreported_is_none_not_zero(self, monkeypatch):
        _patch(monkeypatch, [
            _sse(choices=[], usage={"prompt_tokens": 10, "completion_tokens": 2}),
            "data: [DONE]",
        ])
        completion = OpenRouterClient(api_key="k").complete(
            system="s", user="u", tool_schema=SCHEMA
        )
        assert completion.reasoning_tokens is None

    def test_the_run_sums_only_the_calls_that_reported(self):
        from judge.extract.client import FakeClient
        from judge.extract.runner import ThreadInput, extract

        class Two(FakeClient):
            def complete(self, **kw):
                done = super().complete(**kw)
                reasoning = 700 if len(self.calls) == 1 else None
                return Completion(raw_arguments=done.raw_arguments, reasoning_tokens=reasoning,
                                  input_tokens=5, output_tokens=900)

        client = Two(responses=["not json", '{"claims": [], "no_claim_reason": "none"}'])
        thread = ThreadInput(thread_context_id="t", flattened_text="some text",
                             offset_map=(), raw_text_of={"d": "some text"})
        run = extract(thread, client=client, capability_keys=["k"])
        assert run.reasoning_tokens == 700, "the retry reported nothing and adds nothing"


class TestReasoningIsOffUnlessAskedFor:
    """`deepseek-v4-flash-0731` reasons by default (`default_enabled: True`,
    effort `high`), and reasoning tokens count against `max_tokens`."""

    def _sent(self, monkeypatch, client) -> dict:
        import httpx

        sent: dict = {}

        @contextlib.contextmanager
        def _stream(*args, **kwargs):
            sent.update(kwargs.get("json") or {})
            yield _Canned(["data: [DONE]"])

        monkeypatch.setattr(httpx, "stream", _stream)
        monkeypatch.setattr(spend_ledger, "record", lambda **kw: None)
        client.complete(system="s", user="u", tool_schema=SCHEMA)
        return sent

    def test_the_default_request_disables_reasoning(self, monkeypatch):
        sent = self._sent(monkeypatch, OpenRouterClient(api_key="k"))
        assert sent["reasoning"] == {"effort": "none"}, "not `exclude`, which still bills"

    def test_default_sends_nothing_and_takes_the_models_own(self, monkeypatch):
        sent = self._sent(monkeypatch, OpenRouterClient(api_key="k", reasoning_effort="default"))
        assert "reasoning" not in sent

    def test_an_explicit_effort_is_sent_as_given(self, monkeypatch):
        sent = self._sent(monkeypatch, OpenRouterClient(api_key="k", reasoning_effort="Low"))
        assert sent["reasoning"] == {"effort": "low"}

    def test_the_env_name_is_wired(self):
        from pathlib import Path

        source = Path("judge/extract/client.py").read_text(encoding="utf-8")
        assert 'os.getenv("EXTRACT_REASONING_EFFORT", "none")' in source
