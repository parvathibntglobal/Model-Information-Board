"""A call that never stops arriving is ended, which an idle timeout cannot do.

MEASURED, NOT IMAGINED. 2026-09-14, a live run on `minimax/minimax-m3`: thread
27 of 71 announced at 10:55:57Z, one LLM call, **39 minutes**, no timeout raised.
The 26 threads before it averaged 46 seconds, so this was not a slow run — it was
one call that never came back, and the process had to be killed by pid.

`httpx.Timeout(60.0)` bounds IDLE time per phase. A response that keeps trickling
bytes never goes idle for 60 consecutive seconds, so the read window never
expires. Idleness and elapsed time are different measurements, and only one of
them was being taken.

TIME IS DRIVEN, NOT WAITED ON. A test that actually slept past a cap would take
as long as the cap to prove anything, so the clock is supplied. What is under
test is the deadline arithmetic and where it is checked — not httpx.
"""
from __future__ import annotations

import contextlib
import json

import pytest

from judge.extract.client import ExtractorUnavailable, OpenRouterClient

SCHEMA: dict[str, object] = {"type": "object", "properties": {}}
GOOD_BODY = {
    "model": "deepseek/deepseek-v4-flash",
    "usage": {"prompt_tokens": 10, "completion_tokens": 2},
    "choices": [
        {"message": {"tool_calls": [{"function": {"arguments": '{"claims": []}'}}]}}
    ],
}


class _Trickle:
    """A response that keeps sending, one byte at a time, for ever."""

    status_code = 200

    def __init__(self, chunks, clock):
        self._chunks = chunks
        self._clock = clock

    def iter_bytes(self):
        for chunk in self._chunks:
            # Every chunk costs 30 seconds of wall clock and none of idle time,
            # which is exactly the shape that defeats a read timeout.
            self._clock.advance(30)
            yield chunk

    def raise_for_status(self):
        return None


class _Clock:
    def __init__(self):
        self.t = 1000.0

    def advance(self, seconds):
        self.t += seconds

    def __call__(self):
        return self.t


@pytest.fixture
def clock(monkeypatch):
    import time

    c = _Clock()
    monkeypatch.setattr(time, "monotonic", c)
    return c


def _patch_stream(monkeypatch, response):
    import httpx

    @contextlib.contextmanager
    def _stream(*args, **kwargs):
        yield response

    monkeypatch.setattr(httpx, "stream", _stream)


class TestATricklingResponseIsEnded:
    def test_it_raises_once_the_cap_is_passed(self, monkeypatch, clock):
        client = OpenRouterClient(api_key="k", total_timeout_seconds=120)
        # Five chunks at 30s each = 150s against a 120s cap, so the deadline
        # falls mid-stream with room to spare. NOT four: four lands exactly on
        # the cap, and a test that turns on whether `>` should be `>=` is
        # testing float equality rather than the behaviour.
        _patch_stream(monkeypatch, _Trickle([b"{", b'"a"', b":1", b"}", b" "], clock))

        with pytest.raises(ExtractorUnavailable) as caught:
            client.complete(system="s", user="u", tool_schema=SCHEMA)

        message = str(caught.value)
        assert "120s" in message
        assert "trickling" in message or "still sending" in message

    def test_the_message_does_not_guess_why(self, monkeypatch, clock):
        """Slow, wedged, or streaming something enormous — it cannot tell."""
        client = OpenRouterClient(api_key="k", total_timeout_seconds=60)
        _patch_stream(monkeypatch, _Trickle([b"x"] * 10, clock))

        with pytest.raises(ExtractorUnavailable) as caught:
            client.complete(system="s", user="u", tool_schema=SCHEMA)

        blob = str(caught.value).lower()
        for word in ("crashed", "hung", "dead", "broken", "failed"):
            assert word not in blob, f"asserts {word!r}, which nothing measured"

    def test_an_idle_timeout_alone_would_not_have_caught_it(self, monkeypatch, clock):
        """The point of the fix, stated as a test.

        Every chunk arrives within the 60s read window, so httpx is satisfied
        throughout. Only elapsed time distinguishes this from a healthy call.
        """
        client = OpenRouterClient(
            api_key="k", timeout_seconds=60, total_timeout_seconds=90
        )
        _patch_stream(monkeypatch, _Trickle([b"."] * 20, clock))

        with pytest.raises(ExtractorUnavailable):
            client.complete(system="s", user="u", tool_schema=SCHEMA)


class TestANormalCallIsUntouched:
    def test_a_response_inside_the_cap_parses(self, monkeypatch, clock):
        client = OpenRouterClient(api_key="k", total_timeout_seconds=300)
        body = json.dumps(GOOD_BODY).encode()
        # Two chunks, 60s total, well inside the cap.
        _patch_stream(monkeypatch, _Trickle([body[:20], body[20:]], clock))

        completion = client.complete(system="s", user="u", tool_schema=SCHEMA)

        assert completion.raw_arguments == '{"claims": []}'
        assert completion.input_tokens == 10

    def test_the_cap_is_configurable(self, monkeypatch):
        monkeypatch.setenv("EXTRACT_TOTAL_TIMEOUT_SECONDS", "42")
        import importlib

        from judge.extract import client as module

        importlib.reload(module)
        try:
            assert module.OpenRouterClient(api_key="k").total_timeout_seconds == 42
        finally:
            monkeypatch.delenv("EXTRACT_TOTAL_TIMEOUT_SECONDS", raising=False)
            importlib.reload(module)


class TestAStopReachesInsideTheCall:
    """The defect Anooj measured: Stop reported success and did nothing.

    `Progress.checkpoint()` raises `RunStopped`, and it is called from
    `stage()` — so during E5 the next check is the progress line for the NEXT
    thread. A call that hangs never reaches one. On 2026-09-14 `POST /fetch/stop`
    answered `{"stop_requested": true, "was_running": true}` and the run
    continued for 39 minutes until it was killed by pid.
    """

    def test_a_raising_hook_leaves_the_call(self, monkeypatch, clock):
        class Stopped(Exception):
            pass

        def _stop():
            raise Stopped

        client = OpenRouterClient(
            api_key="k", total_timeout_seconds=10_000, on_progress=_stop
        )
        _patch_stream(monkeypatch, _Trickle([b"x"] * 5, clock))

        # The cap is far away, so nothing but the hook can end this call.
        with pytest.raises(Stopped):
            client.complete(system="s", user="u", tool_schema=SCHEMA)

    def test_the_hook_is_throttled_not_called_per_chunk(self, monkeypatch, clock):
        """`checkpoint()` reads a file; per-chunk would stat the disk endlessly."""
        calls = []
        client = OpenRouterClient(
            api_key="k",
            total_timeout_seconds=10_000,
            on_progress=lambda: calls.append(1),
        )
        # 100 chunks, each advancing the clock 30s — so every chunk is more than
        # a second apart and each one legitimately gets a check.
        _patch_stream(monkeypatch, _Trickle([b"x"] * 100, clock))
        with contextlib.suppress(Exception):
            client.complete(system="s", user="u", tool_schema=SCHEMA)
        many = len(calls)

        calls.clear()
        # Same 100 chunks with no time passing: one check, not a hundred.
        still = _Clock()
        _patch_stream(monkeypatch, _Trickle([b"x"] * 100, _Clock()))
        monkeypatch.setattr(__import__("time"), "monotonic", still)
        with contextlib.suppress(Exception):
            client.complete(system="s", user="u", tool_schema=SCHEMA)

        assert many == 100, "a chunk 30s after the last one must be checked"
        assert len(calls) == 1, f"no time passed, so one check — got {len(calls)}"

    def test_no_hook_means_no_behaviour_change(self, monkeypatch, clock):
        client = OpenRouterClient(api_key="k", total_timeout_seconds=300)
        body = json.dumps(GOOD_BODY).encode()
        _patch_stream(monkeypatch, _Trickle([body[:20], body[20:]], clock))

        assert client.complete(
            system="s", user="u", tool_schema=SCHEMA
        ).raw_arguments == '{"claims": []}'


class TestTheCapSitsAboveTheSuccesses:
    """A ceiling among the successes is a ceiling that fires on healthy calls.

    This shipped at 300s, picked against one run's average. @anoojntglobal-sudo
    measured the distribution over 161 consecutive-thread intervals across 6
    fetch logs — every one a thread that COMPLETED:

        min 9s   p50 14s   mean 44s   p90 70s   max 917s
        exceeding 300s: 4 of 161 (2.5%) — 337s, 580s, 843s, 917s

    So 300s would have abandoned four calls that did come back, the largest at
    three times the cap. Pinned here so the number cannot drift back under the
    evidence without a test saying why.
    """

    #: The four successful calls that the old default would have killed.
    OBSERVED_SLOW_SUCCESSES = (337, 580, 843, 917)

    def test_the_default_clears_every_success_ever_measured(self):
        cap = OpenRouterClient(api_key="k").total_timeout_seconds

        assert cap > max(self.OBSERVED_SLOW_SUCCESSES), (
            f"a cap of {cap}s would abandon a call measured at "
            f"{max(self.OBSERVED_SLOW_SUCCESSES)}s that returned normally"
        )

    def test_it_still_bounds_the_hang_that_was_measured(self):
        """39 minutes, thread 27 of 71, killed by pid."""
        cap = OpenRouterClient(api_key="k").total_timeout_seconds

        assert cap < 39 * 60, (
            f"a cap of {cap}s would not have ended the one hang whose duration "
            f"is actually known"
        )
