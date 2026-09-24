"""A read we stopped must not read as a document that said nothing.

MEASURED, 2026-09-14. Two draws of the same request against `devto:4586450`,
same text, temperature 0, twenty minutes apart:

    draw A     90.4s    8,963 completion tokens   40 claims   $0.00186
    draw B    670.6s   65,536 completion tokens   `{}`        $0.01204

65,536 is 2**16, the provider's own ceiling, reached because `max_tokens` was
unset. Draw B's tool call was two characters. Downstream, that is byte-identical
to a document the model read and found nothing in — which is rule 4 applied to
an absence the pipeline itself created.

So there are three tests' worth of behaviour here and they are different claims:

  1. the request carries a bound at all, and it is the measured one;
  2. a length stop is CARRIED - `finish_reason` survives into the `Completion`,
     and `None` does not become "stop";
  3. a length stop is not retried, and is labelled `ZERO_TRUNCATED` rather than
     joining either of the two zeros that already existed.
"""
from __future__ import annotations

import contextlib
import json
from pathlib import Path

from judge.extract.client import Completion, OpenRouterClient
from judge.extract.runner import (
    ZERO_SILENT,
    ZERO_TRUNCATED,
    ZERO_UNSALVAGED,
    ThreadInput,
    extract,
)
from judge.extract.verify import OffsetMapping

SCHEMA: dict[str, object] = {"type": "object", "properties": {}}
CAPABILITIES = ["reasoning.multistep", "code.generation"]


def _sse(**event) -> str:
    return "data: " + json.dumps(event)


class _Canned:
    """A streamed response built from whole SSE frames."""

    status_code = 200
    #: A real httpx.Response always has headers; the client reads
    #: `X-Generation-Id` from them.
    headers: dict = {}

    def __init__(self, lines):
        self._lines = lines

    def iter_lines(self):
        yield from self._lines

    def read(self):
        return b""


def _patch_stream(monkeypatch, response):
    import httpx

    captured: dict = {}

    @contextlib.contextmanager
    def _stream(*args, **kwargs):
        captured.update(kwargs.get("json") or {})
        yield response

    monkeypatch.setattr(httpx, "stream", _stream)
    return captured


def _thread(text: str = "the model is fast") -> ThreadInput:
    return ThreadInput(
        thread_context_id="thread_context_test",
        flattened_text=text,
        offset_map=(
            OffsetMapping(
                document_id="d1", raw_start=0, raw_end=len(text),
                flat_start=0, flat_end=len(text),
            ),
        ),
        raw_text_of={"d1": text},
    )


class _ScriptedClient:
    """Completions with a `finish_reason`, which `FakeClient` cannot express.

    Deliberately NOT a change to `FakeClient`: its scripted responses are
    strings, and every existing test depends on that. A truncation test needs a
    field, so it brings its own double rather than widening one 75 tests share.
    """

    def __init__(self, completions: list[Completion]) -> None:
        self.completions = completions
        self.calls = 0

    def complete(self, *, system, user, tool_schema) -> Completion:
        self.calls += 1
        if not self.completions:
            raise AssertionError("scripted client ran out of completions")
        return self.completions.pop(0)


class TestTheRequestCarriesABound:
    def test_max_tokens_is_sent(self, monkeypatch):
        client = OpenRouterClient(api_key="k")
        sent = _patch_stream(monkeypatch, _Canned(["data: [DONE]"]))

        client.complete(system="s", user="u", tool_schema=SCHEMA)

        assert sent["max_tokens"] == 16_384, (
            "unbounded output is what produced a 65,536-token call; the bound "
            "is the fix and it has to reach the provider"
        )

    def test_the_stream_is_asked_for_not_just_read(self, monkeypatch):
        """The old code used `httpx.stream` on a NON-streamed request.

        That bought the deadline check and nothing else: the body arrived in one
        burst at the end, so a degenerate loop and a correct answer were
        indistinguishable for as long as they ran.
        """
        client = OpenRouterClient(api_key="k")
        sent = _patch_stream(monkeypatch, _Canned(["data: [DONE]"]))

        client.complete(system="s", user="u", tool_schema=SCHEMA)

        assert sent["stream"] is True
        assert sent["stream_options"] == {"include_usage": True}, (
            "without this a streamed response carries no usage block and the "
            "spend ledger records 0 tokens for every call (rule 6)"
        )

    def test_the_bound_is_configurable(self):
        """Settable per client, and read from the environment by name.

        NOT tested by `importlib.reload`, deliberately. The field default is
        evaluated at import, so an env test has to reload the module - and a
        reload rebinds `ExtractorUnavailable`, after which the copy already
        imported by `runner.py` and by the timeout tests is a DIFFERENT class
        and `pytest.raises` stops matching it. That cost three green tests in
        this file's first version, and the failure appeared only when the two
        files ran together, which is the worst way to find it.

        So: the override is tested by construction, and the env wiring by the
        same source check `tests/test_fetch_model.py` uses for its constants.
        """
        assert OpenRouterClient(api_key="k", max_output_tokens=999).max_output_tokens == 999

        source = Path("judge/extract/client.py").read_text(encoding="utf-8")
        assert 'os.getenv("EXTRACT_MAX_OUTPUT_TOKENS", "16384")' in source


class TestTheFinishReasonSurvives:
    def test_openrouter_normalises_finish_reason_and_we_read_past_it(self, monkeypatch):
        """THE DEFECT THIS CLASS EXISTS FOR, captured from the wire 2026-09-15.

        `tool_choice` is FORCED on this path, so OpenRouter reports every answer
        as `finish_reason: "tool_calls"` - including one it cut at `max_tokens`.
        The truth is in `native_finish_reason`. A check reading only the first
        field cannot fire at all here, and the first version of this fix did
        exactly that: a 16,384-token truncation was retried and filed as
        `unsalvaged`.
        """
        client = OpenRouterClient(api_key="k")
        _patch_stream(monkeypatch, _Canned([
            _sse(choices=[{"delta": {"tool_calls": [
                {"function": {"arguments": '{"claims": [{"quo'}}]}}]),
            _sse(choices=[{"delta": {}, "finish_reason": "tool_calls",
                           "native_finish_reason": "length"}],
                 usage={"prompt_tokens": 13142, "completion_tokens": 16384}),
            "data: [DONE]",
        ]))

        completion = client.complete(system="s", user="u", tool_schema=SCHEMA)

        assert completion.finish_reason == "tool_calls"
        assert completion.native_finish_reason == "length"
        assert completion.stopped_at_ceiling is True, (
            "the normalised field says tool_calls; reading only that reports a "
            "cut-off answer as a clean stop"
        )

    def test_the_token_count_alone_is_enough(self):
        """The signal that needs no cooperation from any vendor.

        Both labels absent - a provider that reports neither - and the answer is
        still known to be cut, because we asked for at most N and got N.
        """
        completion = Completion(
            raw_arguments='{"claims": [{"quo', output_tokens=16_384,
            finish_reason="tool_calls", native_finish_reason=None,
            ceiling_tokens=16_384,
        )
        assert completion.stopped_at_ceiling is True

    def test_arithmetic_does_not_fire_below_the_ceiling(self):
        completion = Completion(
            raw_arguments='{"claims": []}', output_tokens=8_963,
            finish_reason="tool_calls", ceiling_tokens=16_384,
        )
        assert completion.stopped_at_ceiling is False

    def test_no_ceiling_means_no_arithmetic_claim(self):
        """Rule 6. With nothing asked for, a token count proves nothing."""
        completion = Completion(
            raw_arguments="{}", output_tokens=65_536, ceiling_tokens=None,
        )
        assert completion.stopped_at_ceiling is False

    def test_a_length_stop_is_carried_into_the_completion(self, monkeypatch):
        client = OpenRouterClient(api_key="k")
        _patch_stream(monkeypatch, _Canned([
            _sse(choices=[{"delta": {"tool_calls": [
                {"function": {"arguments": '{"claims": [{"quote"'}}]}}]),
            _sse(choices=[{"delta": {}, "finish_reason": "length"}],
                 usage={"prompt_tokens": 13142, "completion_tokens": 16384}),
            "data: [DONE]",
        ]))

        completion = client.complete(system="s", user="u", tool_schema=SCHEMA)

        assert completion.finish_reason == "length"
        assert completion.stopped_at_ceiling is True
        assert completion.output_tokens == 16_384

    def test_fragments_are_accumulated_in_order(self, monkeypatch):
        client = OpenRouterClient(api_key="k")
        _patch_stream(monkeypatch, _Canned([
            _sse(choices=[{"delta": {"tool_calls": [{"function": {"arguments": '{"cla'}}]}}]),
            _sse(choices=[{"delta": {"tool_calls": [{"function": {"arguments": 'ims":'}}]}}]),
            _sse(choices=[{"delta": {"tool_calls": [{"function": {"arguments": ' []}'}}]},
                           "finish_reason": "tool_calls"}]),
            "data: [DONE]",
        ]))

        completion = client.complete(system="s", user="u", tool_schema=SCHEMA)

        assert completion.raw_arguments == '{"claims": []}'
        assert completion.stopped_at_ceiling is False

    def test_a_silent_provider_is_not_recorded_as_a_clean_stop(self, monkeypatch):
        """Rule 6. Nothing said is not the same as "it finished"."""
        client = OpenRouterClient(api_key="k")
        _patch_stream(monkeypatch, _Canned([
            _sse(choices=[{"delta": {"tool_calls": [
                {"function": {"arguments": '{"claims": []}'}}]}}]),
            "data: [DONE]",
        ]))

        completion = client.complete(system="s", user="u", tool_schema=SCHEMA)

        assert completion.finish_reason is None
        assert completion.stopped_at_ceiling is False

    def test_keepalive_comments_are_not_mistaken_for_content(self, monkeypatch):
        client = OpenRouterClient(api_key="k")
        _patch_stream(monkeypatch, _Canned([
            ": OPENROUTER PROCESSING",
            "",
            ": OPENROUTER PROCESSING",
            _sse(choices=[{"delta": {"tool_calls": [
                {"function": {"arguments": '{"claims": []}'}}]},
                           "finish_reason": "tool_calls"}]),
            "data: [DONE]",
        ]))

        completion = client.complete(system="s", user="u", tool_schema=SCHEMA)

        assert completion.raw_arguments == '{"claims": []}'


class TestALengthStopIsNotRetried:
    def test_one_call_not_two(self):
        """A retry truncates identically and bills twice for the same nothing."""
        truncated = Completion(
            raw_arguments='{"claims": [{"quote": "the model is',
            input_tokens=13_142, output_tokens=16_384, finish_reason="length",
        )
        client = _ScriptedClient([truncated])

        run = extract(_thread(), client=client, capability_keys=CAPABILITIES)

        assert client.calls == 1, (
            f"retried a length stop {client.calls} times; before `max_tokens` "
            "existed that was 65,536 tokens twice for the same result"
        )
        assert run.schema_retries == 0

    def test_a_real_schema_violation_is_still_retried(self):
        """The no-retry rule is about the CEILING, not about bad JSON."""
        client = _ScriptedClient([
            Completion(raw_arguments="not json at all", finish_reason="tool_calls"),
            Completion(raw_arguments='{"claims": [], "no_claim_reason": "nothing"}',
                       finish_reason="tool_calls"),
        ])

        run = extract(_thread(), client=client, capability_keys=CAPABILITIES)

        assert client.calls == 2
        assert run.schema_retries == 1


class TestATruncatedReadIsLabelledAsOne:
    def test_zero_kind_is_truncated_not_silent(self):
        client = _ScriptedClient([
            Completion(raw_arguments='{"claims": [{"quote": "the model is',
                       output_tokens=16_384, finish_reason="length"),
        ])

        run = extract(_thread(), client=client, capability_keys=CAPABILITIES)

        assert run.truncated is True
        assert run.zero_kind == ZERO_TRUNCATED
        assert run.zero_kind != ZERO_SILENT, "this is not a document that said nothing"
        assert run.zero_kind != ZERO_UNSALVAGED, "this is not a schema failure"

    def test_the_reason_says_we_stopped_it(self):
        client = _ScriptedClient([
            Completion(raw_arguments='{"claims": [{"quote": "the model is',
                       output_tokens=16_384, finish_reason="length"),
        ])

        run = extract(_thread(), client=client, capability_keys=CAPABILITIES)

        assert run.no_claim_reason is not None
        assert "ceiling" in run.no_claim_reason
        assert "16384" in run.no_claim_reason

    def test_an_ordinary_empty_answer_is_still_silent(self):
        """The label has to separate two things, so it must not swallow both."""
        client = _ScriptedClient([
            Completion(
                raw_arguments=json.dumps(
                    {"claims": [], "no_claim_reason": "the document is about cats"}
                ),
                finish_reason="tool_calls",
            ),
        ])

        run = extract(_thread(), client=client, capability_keys=CAPABILITIES)

        assert run.truncated is False
        assert run.zero_kind == ZERO_SILENT

    def test_truncation_is_flagged_even_when_claims_survived(self):
        """A partial read that produced claims is the one that looks finished.

        Counted off `truncated` rather than off `zero_kind` for exactly this
        case: `zero_kind` is only set when nothing verified, so a truncated
        thread carrying a good claim would otherwise report as a clean read.
        """
        from tests.test_extract_runner import claim_json
        from tests.test_extract_runner import thread as good_thread

        client = _ScriptedClient([
            Completion(
                raw_arguments=claim_json("Flash dropped the cancellation clause", 0, 37),
                output_tokens=16_384, finish_reason="length",
            ),
        ])

        run = extract(good_thread(), client=client, capability_keys=["summarization.fidelity"])

        assert len(run.verified) == 1, (
            f"fixture must actually verify a claim or this tests nothing; "
            f"zero_kind={run.zero_kind} unsalvaged={len(run.unsalvaged)}"
        )
        assert run.zero_kind is None, "claims were verified, so there is no zero"
        assert run.truncated is True, (
            "a truncated thread that still produced claims must say so - it is "
            "the case that most looks like a complete read"
        )
