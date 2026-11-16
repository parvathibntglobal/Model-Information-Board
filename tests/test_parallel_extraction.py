"""E5 with model calls in parallel (contract/scheduler.yaml `extract_concurrency`).

No database and no network: `extract` is a slow fake that records how many calls
overlap, and the per-thread store step (`Pipeline.run`) is a fake that records
where and in what order it ran. What these pin:

* up to `concurrency` calls overlap, never more, and more than one does;
* storing stays on the calling thread, one thread at a time, in thread order;
* `on_thread` and the budget check still come before each call is sent;
* when the cap binds, the calls already in flight are stored and the batch then
  raises BudgetExhausted where the serial loop would have;
* a failed parallel call is retried serially, and a refused one is skipped;
* concurrency 1 makes the calls one at a time, as before;
* the setting is read strictly from the contract.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import pytest

from judge import pipeline as pipeline_mod
from judge import scheduler
from judge.extract.budget import BudgetExhausted
from judge.extract.client import ExtractorUnavailable
from judge.extract.runner import ExtractionRefused


def _thread(i):
    return SimpleNamespace(thread_context_id=f"t{i}", flattened_text=f"text {i}", raw_text_of={})


def _extraction(tid):
    return SimpleNamespace(
        thread=tid,
        reported_costs=[],
        input_tokens=10,
        output_tokens=5,
        cached_input_tokens=0,
        schema_retries=0,
    )


class _Ledger:
    def __init__(self):
        self.recorded = []

    def record(self, rec):
        self.recorded.append(rec.thread_context_id)

    def already_extracted(self):
        return {}


def _pipeline(monkeypatch, *, fail=None, refuse=(), delay=0.05):
    """A Pipeline whose model call and store step are fakes. Returns it and a log."""
    monkeypatch.setenv("LEGACY_CELLS", "off")
    log = {
        "in_flight": 0,
        "max_in_flight": 0,
        "calls": [],
        "stored": [],
        "store_threads": set(),
        "lock": threading.Lock(),
        "fail_left": dict(fail or {}),
    }

    def fake_extract(thread, *, client, capability_keys, legacy):
        tid = thread.thread_context_id
        with log["lock"]:
            log["in_flight"] += 1
            log["max_in_flight"] = max(log["max_in_flight"], log["in_flight"])
            log["calls"].append(tid)
        time.sleep(delay)
        with log["lock"]:
            log["in_flight"] -= 1
            if tid in refuse:
                raise ExtractionRefused(f"{tid} refused")
            if log["fail_left"].get(tid, 0) > 0:
                log["fail_left"][tid] -= 1
                raise ExtractorUnavailable(f"{tid} 502", transient=True)
        return _extraction(tid)

    monkeypatch.setattr(pipeline_mod, "extract", fake_extract)
    p = pipeline_mod.Pipeline(
        conn=SimpleNamespace(), client=None, capability_keys=[], extractor_model="m"
    )
    p._ledger = _Ledger()
    real_run = pipeline_mod.Pipeline.run

    def fake_run(self, thread, *, extraction=None, **kw):
        if extraction is None:  # the serial path: the call is made here, as before
            extraction = self._extract(thread)
        log["stored"].append(thread.thread_context_id)
        log["store_threads"].add(threading.current_thread().name)
        return SimpleNamespace(
            extraction=extraction, stored_claims=0, stored_claim_ids=[], cells=[]
        )

    monkeypatch.setattr(pipeline_mod.Pipeline, "run", fake_run)
    assert real_run is not fake_run
    return p, log


def _run(p, threads, **kw):
    return p.run_all(threads, facts={}, model_version_of={}, already_extracted={}, **kw)


def test_up_to_n_calls_overlap_and_storing_stays_in_order_on_this_thread(monkeypatch):
    p, log = _pipeline(monkeypatch)
    threads = [_thread(i) for i in range(10)]
    results = _run(p, threads, concurrency=4)
    assert 1 < log["max_in_flight"] <= 4
    assert log["stored"] == [t.thread_context_id for t in threads]  # thread order
    assert [r.extraction.thread for r in results] == log["stored"]
    assert log["store_threads"] == {threading.current_thread().name}
    assert p._ledger.recorded == log["stored"]
    assert p._prefetch is None  # the pool is shut down after the batch


def test_concurrency_one_is_serial(monkeypatch):
    p, log = _pipeline(monkeypatch)
    _run(p, [_thread(i) for i in range(4)], concurrency=1)
    assert log["max_in_flight"] == 1
    assert log["stored"] == ["t0", "t1", "t2", "t3"]


def test_on_thread_and_the_budget_check_come_before_each_call(monkeypatch):
    p, log = _pipeline(monkeypatch)
    seen = []

    class _Budget:
        def check_before_call(self):
            seen.append(("check", len(log["calls"])))

        def charge(self, completion):
            pass

    _run(
        p,
        [_thread(i) for i in range(5)],
        concurrency=3,
        budget=_Budget(),
        on_thread=lambda tid: seen.append(("on_thread", tid)),
    )
    on_threads = [x for x in seen if x[0] == "on_thread"]
    checks = [x for x in seen if x[0] == "check"]
    assert [t for _, t in on_threads] == ["t0", "t1", "t2", "t3", "t4"]
    assert len(checks) == 5
    # each check happened before that thread's call was counted
    assert [n for _, n in checks] == sorted(n for _, n in checks)
    assert all(n <= i for i, (_, n) in enumerate(checks))


def test_when_the_cap_binds_in_flight_calls_are_stored_then_the_batch_stops(monkeypatch):
    p, log = _pipeline(monkeypatch)
    sent = {"n": 0}

    class _Budget:
        def check_before_call(self):
            if sent["n"] >= 3:
                raise BudgetExhausted(spent_usd=0.4, limit_usd=0.4, completed=3)
            sent["n"] += 1

        def charge(self, completion):
            pass

    with pytest.raises(BudgetExhausted):
        _run(p, [_thread(i) for i in range(8)], concurrency=4, budget=_Budget())
    assert log["calls"] == ["t0", "t1", "t2"] or sorted(log["calls"]) == ["t0", "t1", "t2"]
    assert log["stored"] == ["t0", "t1", "t2"]  # paid for, so kept
    assert p._prefetch is None


def test_a_failed_parallel_call_is_retried_serially_and_a_refused_one_skipped(monkeypatch):
    p, log = _pipeline(monkeypatch, fail={"t1": 1}, refuse=("t2",))
    results = _run(p, [_thread(i) for i in range(4)], concurrency=4)
    assert log["stored"] == ["t0", "t1", "t3"]  # t2 refused, t1 read on its retry
    assert log["calls"].count("t1") == 2
    assert p.retried_threads == 1
    assert [r.extraction.thread for r in results] == ["t0", "t1", "t3"]


def test_concurrency_must_be_a_positive_integer(monkeypatch):
    p, _ = _pipeline(monkeypatch)
    for bad in (0, -1, True, 2.0):
        with pytest.raises(ValueError, match="positive integer"):
            _run(p, [_thread(0)], concurrency=bad)


def test_the_setting_is_read_strictly_from_the_contract(monkeypatch):
    import judge.config as config

    scheduler.extract_concurrency.cache_clear()
    assert scheduler.extract_concurrency() == 4
    for bad in (None, 0, "4", True):
        monkeypatch.setattr(config, "_read", lambda name, b=bad: {"extract_concurrency": b})
        scheduler.extract_concurrency.cache_clear()
        with pytest.raises(scheduler.SchedulerPolicyError, match="extract_concurrency"):
            scheduler.extract_concurrency()
    scheduler.extract_concurrency.cache_clear()
