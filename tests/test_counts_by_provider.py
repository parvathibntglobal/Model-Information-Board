"""Threads and quotes by OpenRouter provider, in the nightly summary and the feed (#671).

From 14 Nov one provider of deepseek-v4-flash, DeepInfra, answered "no claim" to
nearly every thread (14-24 Nov: 1,518 threads, 125 verified quotes; the other
providers, 2,351 threads, 5,453), and the summary, which gave totals only, showed
nothing for 11 days. These pin:
  * a thread counts under the provider of its FINAL call (the answer that was checked);
  * the counts ride on the end record and are summed into one summary line;
  * a provider name reaches the public issue only in its counted shape;
  * the feed's paraphrase run counts reports sent and passed per provider.
"""

from __future__ import annotations

import contextlib
import pathlib

from judge import scheduler
from judge.feed import llm, paraphrase

ROOT = pathlib.Path(__file__).resolve().parents[1]


# ── the extractor ─────────────────────────────────────────────────────────────


def test_a_thread_counts_under_its_final_calls_provider():
    by = scheduler.count_by_provider([
        (["Wafer"], 4),
        (["DeepInfra"], 0),
        (["DeepInfra", "Wafer"], 2),   # retried elsewhere: the retry's answer was checked
        ([None], 1),                   # the stream named no provider
        ([], 0),
        (None, 0),
    ])
    assert by == {
        "Wafer": {"threads": 2, "verified": 6},
        "DeepInfra": {"threads": 1, "verified": 0},
        "not reported": {"threads": 3, "verified": 1},
    }


def test_the_end_record_carries_it_and_the_threads_add_up():
    """Source check, as tests/test_a_run_narrates_itself.py does for the other
    totals: the field is on the record summary, built from the same `results`
    that `threads_read` counts."""
    src = (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
    block = src[src.index("prog.record_summary(\n        llm="):]
    block = block[: block.index("\n    )\n")]
    assert "threads_read=len(results)" in block
    assert "threads_by_provider=count_by_provider(" in block
    assert "for r in results" in block[block.index("threads_by_provider="):]


def _end(model, by, **more):
    read = sum(r["threads"] for r in by.values()) if by else 0
    return scheduler.safe_record({"kind": "end", "status": "ok", "model": model,
                                  "threads_read": read, "threads_by_provider": by, **more})


def test_the_summary_sums_the_night_per_provider():
    body = scheduler.summarise_runs([
        _end("A", {"Wafer": {"threads": 300, "verified": 1200},
                   "DeepInfra": {"threads": 40, "verified": 3}}),
        _end("B", {"Wafer": {"threads": 74, "verified": 445},
                   "Azure": {"threads": 80, "verified": 140}}),
    ])
    (line,) = [ln for ln in body.splitlines() if ln.startswith(scheduler.PROVIDER_LINE)]
    # Most threads first; both counts beside each name, no ratio.
    assert line.endswith(
        "Wafer 374 / 1,645 · Azure 80 / 140 · DeepInfra 40 / 3 (threads / quotes).")


def test_a_run_that_did_not_report_it_is_said_not_folded_in():
    body = scheduler.summarise_runs([
        _end("A", {"Wafer": {"threads": 5, "verified": 9}}),
        scheduler.safe_record({"kind": "end", "status": "ok", "model": "old", "threads_read": 7}),
        scheduler.safe_record({"kind": "end", "status": "ok", "model": "collect",
                               "threads_read": 0, "extract_skipped": True}),
    ])
    (line,) = [ln for ln in body.splitlines() if ln.startswith(scheduler.PROVIDER_LINE)]
    assert "Wafer 5 / 9" in line
    assert "1 run(s) read threads and did not report their providers" in line


def test_no_run_reported_it_no_line():
    body = scheduler.summarise_runs([
        scheduler.safe_record({"kind": "end", "status": "ok", "model": "old", "threads_read": 7}),
    ])
    assert scheduler.PROVIDER_LINE not in body


def test_only_the_counted_shape_reaches_the_public_issue():
    ok = scheduler.safe_record({"threads_by_provider": {
        "Google AI Studio": {"threads": 1, "verified": 2},
        "not reported": {"threads": 3, "verified": 0},
        "10.0.0.5:5432 postgres://x": {"threads": 2, "verified": 1},
        "Wafer (fp8)": {"threads": 1, "verified": 1},
    }})["threads_by_provider"]
    assert ok == {
        "Google AI Studio": {"threads": 1, "verified": 2},
        "not reported": {"threads": 3, "verified": 0},
        scheduler.PROVIDER_UNRECOGNISED: {"threads": 2, "verified": 1},
        "Wafer (fp8)": {"threads": 1, "verified": 1},
    }
    for bad in ({"Wafer": {"threads": "3", "verified": 1}},
                {"Wafer": {"threads": True, "verified": 1}},
                {"Wafer": {"threads": -1, "verified": 1}},
                {"Wafer": 3},
                ["Wafer"]):
        assert "threads_by_provider" not in scheduler.safe_record({"threads_by_provider": bad}), bad


# ── the evidence feed ─────────────────────────────────────────────────────────


class _Resp:
    status_code = 200

    def __init__(self, provider, args):
        self._provider, self._args = provider, args

    def json(self):
        body = {"model": "deepseek/deepseek-v4-flash", "usage": {"cost": 0.0},
                "choices": [{"message": {"tool_calls": [
                    {"function": {"arguments": self._args}}]}}]}
        if self._provider is not None:
            body["provider"] = self._provider
        return body


def _call_kwargs():
    return dict(model="deepseek/deepseek-v4-flash", system="s", user="u", tool=paraphrase.TOOL,
                run_id="r", max_tokens=10, reasoning_effort="none")


def test_the_feed_client_records_who_served_each_call(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.test/api/v1")
    monkeypatch.setattr(llm.spend_ledger, "record", lambda **kw: None)
    answers = iter([_Resp("Wafer", '{"paraphrases": []}'),
                    _Resp(None, '{"paraphrases": []}'),
                    _Resp("DeepInfra", "not json")])
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: next(answers))

    llm.call_tool(**_call_kwargs())
    assert llm.last_provider() == "Wafer"
    llm.call_tool(**_call_kwargs())
    assert llm.last_provider() == "not reported"  # never the previous call's
    with contextlib.suppress(llm.FeedModelUnavailable):
        llm.call_tool(**_call_kwargs())
    # A provider whose answer is refused is still the one that served it.
    assert llm.last_provider() == "DeepInfra"
    llm.clear_last_provider()
    assert llm.last_provider() == "not reported"


def test_the_feed_line_puts_both_counts_side_by_side():
    line = paraphrase.provider_line({
        "Wafer": {"calls": 4, "asked": 80, "passed": 41, "failed_calls": 0},
        "DeepInfra": {"calls": 4, "asked": 80, "passed": 22, "failed_calls": 1},
        "Azure": {"calls": 1, "asked": 3, "passed": 3, "failed_calls": 0},
    })
    assert line == ("paraphrase by OpenRouter provider: "
                    "DeepInfra: 22 passed of 80 sent over 4 call(s), 1 call(s) failed; "
                    "Wafer: 41 passed of 80 sent over 4 call(s); "
                    "Azure: 3 passed of 3 sent over 1 call(s).")
    assert paraphrase.provider_line({}) is None
