"""What attempt 1 failed on is recorded when a retry ran. Issue #411 (b).

`unsalvaged_by_error` describes the answer salvaged FROM, so a retry that
rescued a thread left no record of what it rescued it from - which is the
number #411 (c), "should a validation failure retry at all?", needs. This
records attempt 1's strict-parse errors as `first_attempt_errors` and the
thread record's `retried_on_by_error`. Retry behaviour itself is unchanged.

(#411 (a), drop the entry and keep the claim, landed in #522.)
"""
from __future__ import annotations

import json
from pathlib import Path

from judge.extract.client import FakeClient
from judge.extract.runner import (
    ThreadInput,
    error_shapes,
    extract,
    unsalvaged_shapes,
)
from judge.extract.verify import OffsetMapping

ROOT = Path(__file__).resolve().parents[1]

TEXT = "switched our agent to Flash, ttft went from 900ms to 300ms"
QUOTE = "ttft went from 900ms to 300ms"

BEST_FOR = {"section": "best_for", "slug": "coding-agent", "name": "Coding agent",
            "definition": "Runs a coding agent."}
CAPABILITY = {"section": "capability", "slug": "speed", "name": "Speed",
              "definition": "How fast it answers."}
METRIC_NO_BASIS = {"section": "metric", "slug": "time-to-first-token",
                   "name": "Time to first token", "definition": "Latency to first token.",
                   "unit": "ms", "value_verbatim": "300ms", "basis": None}


def _claim(entries, **over) -> dict:
    claim = {
        "source_comment_id": "d1",
        "model_ref": {"surface": "Flash", "resolved_version_id": "google/gemini-2.5-flash",
                      "specificity": "family", "resolution_confidence": 0.8,
                      "speaking": "own-experience"},
        "board_entries": entries,
        "polarity": "positive",
        "quote": QUOTE,
        "quote_offset": [TEXT.index(QUOTE), TEXT.index(QUOTE) + len(QUOTE)],
        "relevance": "central",
    }
    claim.update(over)
    return claim


def _envelope(*claims) -> str:
    return json.dumps({"claims": list(claims)})


def _thread() -> ThreadInput:
    return ThreadInput(
        thread_context_id="tc1",
        flattened_text=TEXT,
        offset_map=(OffsetMapping(flat_start=0, flat_end=len(TEXT), document_id="d1",
                                  raw_start=0, raw_end=len(TEXT)),),
        raw_text_of={"d1": TEXT},
    )


def _run(*responses):
    client = FakeClient(responses=list(responses))
    return extract(_thread(), client=client, capability_keys=["a.b"], legacy=False), client


class TestAttemptOneIsRecorded:
    def test_a_rescued_thread_says_what_it_was_rescued_from(self):
        run, client = _run(
            _envelope(_claim([BEST_FOR, METRIC_NO_BASIS])),
            _envelope(_claim([BEST_FOR])),
        )
        assert len(client.calls) == 2 and run.schema_retries == 1
        assert run.unsalvaged == []
        shapes, _ = error_shapes(run.first_attempt_errors)
        assert any(s.startswith("board_entries") for s in shapes), shapes

    def test_no_retry_records_nothing(self):
        run, client = _run(_envelope(_claim([BEST_FOR, CAPABILITY])))
        assert len(client.calls) == 1
        assert run.first_attempt_errors == ()

    def test_attempt_one_shapes_compare_with_unsalvaged_shapes(self):
        """The `claims.<n>.` prefix is stripped so both read alike."""
        bad = _envelope(_claim([BEST_FOR], quote="q" * 400))
        run, _ = _run(bad, bad)
        first, _ = error_shapes(run.first_attempt_errors)
        final, _ = unsalvaged_shapes(run.unsalvaged)
        assert first == final

    def test_an_unreadable_first_answer_is_recorded_too(self):
        run, _ = _run("not json", _envelope(_claim([BEST_FOR])))
        assert run.first_attempt_errors
        assert run.unsalvaged == []


class TestItReachesTheRecordAndTheTerminal:
    def test_the_thread_record_carries_it(self):
        src = (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
        assert '"retried_on_by_error"' in src
        assert '_retried_on(getattr(run, "first_attempt_errors"' in src

    def test_the_terminal_prints_both_headed(self):
        from judge import fetch_console

        out = "\n".join(fetch_console.render({
            "kind": "thread", "index": 1, "total": 2,
            "thread_context_id": "thread_context_abc", "posts": 1, "verified": 1,
            "entries_dropped": 1,
            "dropped_entries_by_error": {"board_entries.basis: missing": 1},
            "retried_on_by_error": {"quote: too long": 2},
            "retried_on_other": 3,
        }, model_version_id="mv_x"))
        assert "entries dropped from kept claims: 1" in out
        assert "attempt 1 failed on (then retried)" in out
        assert "x2" in out and "+3 more in other shapes" in out
