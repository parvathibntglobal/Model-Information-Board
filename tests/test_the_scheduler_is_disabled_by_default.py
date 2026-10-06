"""The scheduler: what is due, a host-free summary, source scope, and OFF by default.

Built so it is ready for a person to enable on the Railway service once the
undertaking in contract/sources.yaml is honest again. Until SCHEDULER_ENABLED is
set it harvests nothing, and even enabled, a source whose ruling does not hold
skips itself (the fetch_model terms gate). Nothing here runs a fetch.
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime, timedelta

import pytest

import scripts.fetch_model as fm
import scripts.run_scheduled_fetches as runner
from judge import scheduler

ROOT = pathlib.Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)


def _row(mv, name, *, tracked=True, in_window=True, last=None):
    return {"model_version_id": mv, "display_name": name, "tracked": tracked,
            "in_window": in_window, "last_success": last}


class TestWhatIsDue:
    def test_a_never_fetched_model_is_a_first_fetch_at_the_larger_cap(self):
        (d,) = scheduler.rank_due([_row("a", "A")], NOW)
        assert d.reason == "first fetch"
        assert d.thread_cap == scheduler.policy().first_fetch_thread_cap

    def test_a_recent_success_is_not_due(self):
        assert scheduler.rank_due([_row("a", "A", last=NOW - timedelta(days=3))], NOW) == []

    def test_a_stale_success_is_a_refresh_at_the_smaller_cap(self):
        (d,) = scheduler.rank_due([_row("a", "A", last=NOW - timedelta(days=9))], NOW)
        assert d.reason.startswith("refresh")
        assert d.thread_cap == scheduler.policy().refresh_thread_cap

    def test_out_of_window_and_untracked_are_left_out(self):
        rows = [_row("a", "A", in_window=False), _row("b", "B", tracked=False)]
        assert scheduler.rank_due(rows, NOW) == []

    def test_first_fetches_lead_then_the_oldest_success(self):
        rows = [_row("recent", "Recent", last=NOW - timedelta(days=8)),
                _row("new", "New"),
                _row("ancient", "Ancient", last=NOW - timedelta(days=40))]
        ranked = [d.display_name for d in scheduler.rank_due(rows, NOW)]
        assert ranked == ["New", "Ancient", "Recent"]

    def test_a_missing_window_is_not_treated_as_in_window(self):
        assert scheduler.rank_due([{"model_version_id": "a", "display_name": "A",
                                    "tracked": True, "last_success": None}], NOW) == []


class TestTheSummaryIsHostFree:
    def test_a_detail_with_a_host_never_reaches_the_summary(self):
        raw = {"model": "GPT-6 Astra", "status": "error", "documents_appended": 0,
               "detail": "refusing: the database is 203.0.113.5, which is not this machine"}
        safe = scheduler.safe_record(raw)
        assert "detail" not in safe
        summary = scheduler.summarise_runs([safe])
        assert "203.0.113.5" not in summary and "database is" not in summary

    def test_an_absent_count_is_a_dash_not_zero(self):
        summary = scheduler.summarise_runs([{"model": "A", "status": "ok"}])
        assert "| - |" in summary and "not the same as zero" in summary

    def test_counts_that_exist_are_shown(self):
        rec = {"model": "A", "status": "ok", "documents_appended": 12,
               "threads_read": 20, "claims_verified": 7, "claims_stored": 0,
               "harvest_arms_errored": ["E2R"]}
        summary = scheduler.summarise_runs([scheduler.safe_record(rec)])
        assert "| 12 |" in summary and "| 20 |" in summary and "| 7 |" in summary
        assert "| 0 |" not in summary, "claims_stored (0 since #502) reached the table"
        assert "E2R" in summary

    def test_safe_record_keeps_no_field_outside_the_allowlist(self):
        raw = {"model": "A", "status": "ok", "run_id": "r-1", "machine": "LAPTOP-X",
               "detail": "host 203.0.113.7", "documents_appended": 3}
        safe = scheduler.safe_record(raw)
        allowed = set(scheduler._SAFE_FIELDS) | {"model", "model_version_id", "display_name"}
        assert set(safe) <= allowed
        assert "machine" not in safe and "run_id" not in safe


class TestTheSourceScope:
    def test_default_is_every_source(self):
        assert fm.selected_sources(None) == set(fm.ALL_SOURCES)

    def test_github_alone_is_a_valid_scope(self):
        assert fm.selected_sources("github") == {"github"}

    def test_an_unknown_source_is_refused_not_ignored(self):
        with pytest.raises(SystemExit):
            fm.selected_sources("gihtub")

    def test_the_harvest_block_gates_every_arm_on_the_scope(self):
        src = (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
        start = src.index("sources = selected_sources(args.sources)")
        block = src[start:src.index("ASSEMBLE THEN TRIAGE")]
        for arm in ('"github" in sources', '"reddit" in sources', '"arxiv" in sources',
                    '"x" in sources', "_pid not in sources"):
            assert arm in block, arm
        assert block.count('"skipped"') >= 5, "a source out of scope is skipped, not absent"


class TestOffByDefault:
    def test_it_refuses_to_run_without_the_switch(self, monkeypatch, capsys):
        monkeypatch.delenv("SCHEDULER_ENABLED", raising=False)

        def no_connect(*a, **k):
            raise AssertionError("the runner connected to the database while disabled")

        monkeypatch.setattr("psycopg.connect", no_connect, raising=False)
        assert runner.main([]) == 0
        assert "scheduler disabled" in capsys.readouterr().out

    @pytest.mark.parametrize("value,on", [("1", True), ("true", True), ("on", True),
                                          ("", False), ("no", False), ("0", False)])
    def test_the_switch_reads_only_truthy_values_as_on(self, monkeypatch, value, on):
        monkeypatch.setenv("SCHEDULER_ENABLED", value)
        assert runner.enabled() is on

    def test_dry_run_plans_without_the_switch_and_harvests_nothing(self, monkeypatch):
        monkeypatch.delenv("SCHEDULER_ENABLED", raising=False)
        monkeypatch.setattr(runner, "_read_only_dsn", lambda: "postgresql://x@h/db")

        class _Conn:
            def __enter__(self): return self
            def __exit__(self, *a): return False
        monkeypatch.setattr("psycopg.connect", lambda *a, **k: _Conn())
        monkeypatch.setattr(runner, "due_rows", lambda conn: [_row("a", "A")])
        launched = []
        monkeypatch.setattr(runner, "run_one", lambda *a, **k: launched.append(1))
        assert runner.main(["--dry-run"]) == 0
        assert launched == [], "dry-run launched a fetch"


class TestTheRunnerNamesTheRun:
    """The runner passes `--run-id` and reads the end record under that id.

    It used to read the id back from the child's first stdout line. `fetch_model`
    stopped printing it, so every scheduled model reported "no end record" while
    its fetch ran - a summary that was wrong in exactly the direction nobody
    reads (rule 4: an absence we caused, rendered as one we found).
    """

    def test_the_id_on_the_command_line_is_the_id_whose_log_is_read(self, monkeypatch):
        seen = {}

        class _Proc:
            returncode = 0
            stdout = "something else entirely\n"

        def fake_run(cmd, **kw):
            seen["cmd"] = cmd
            return _Proc()

        monkeypatch.setattr(runner.subprocess, "run", fake_run)
        monkeypatch.setattr(runner, "_end_record",
                            lambda rid: {"kind": "end", "status": "ok", "rid": rid})
        due = scheduler.rank_due([_row("mv_a", "A")], datetime.now(UTC))[0]

        result = runner.run_one(due, sources=None, development_write=False)

        cmd = seen["cmd"]
        assert "--run-id" in cmd
        named = cmd[cmd.index("--run-id") + 1]
        assert named.startswith("mv_a-")
        assert result["run_id"] == named
        assert result["_end"]["rid"] == named, "the log read is not the run launched"


class TestTheBudgetStopsTheBatch:
    """Once the shared daily budget is spent, no further model is launched -
    a launched model would harvest (spending quota) and extract nothing - and
    every model not run is named with the reason."""

    def _setup(self, monkeypatch, spent_seq, *, cap="2.00"):
        import judge.spend_ledger as ledger

        monkeypatch.setenv("SCHEDULER_ENABLED", "1")
        if cap is None:
            monkeypatch.delenv("EXTRACTION_DAILY_BUDGET_USD", raising=False)
        else:
            monkeypatch.setenv("EXTRACTION_DAILY_BUDGET_USD", cap)
        monkeypatch.setattr(runner, "_read_only_dsn", lambda: "postgresql://x@h/db")

        class _Conn:
            def __enter__(self): return self
            def __exit__(self, *a): return False
        monkeypatch.setattr("psycopg.connect", lambda *a, **k: _Conn())
        monkeypatch.setattr(runner, "due_rows",
                            lambda conn: [_row("a", "A"), _row("b", "B"), _row("c", "C")])
        spent = iter(spent_seq)
        monkeypatch.setattr(ledger, "spent_today", lambda *a, **k: next(spent))
        launched, posted = [], []
        monkeypatch.setattr(runner, "run_one", lambda d, **k: launched.append(d.display_name)
                            or {"_end": {"kind": "end", "status": "ok"}})
        monkeypatch.setattr(runner, "post_summary", lambda recs: posted.extend(recs))
        monkeypatch.setattr(runner, "in_progress", lambda conn, now: set())
        return launched, posted

    def test_a_model_already_being_fetched_is_named_not_launched(self, monkeypatch):
        """One fetch per model at a time: a second would pay to extract the
        same unread threads again."""
        launched, posted = self._setup(monkeypatch, [0.0, 0.0, 0.0])
        monkeypatch.setattr(runner, "in_progress", lambda conn, now: {"b"})
        assert runner.main([]) == 0
        assert launched == ["A", "C"]
        assert [r["model"] for r in posted
                if r["status"] == "not run: a fetch of this model is already running"] == ["B"]

    def test_models_after_the_budget_is_spent_are_named_not_launched(self, monkeypatch):
        launched, posted = self._setup(monkeypatch, [0.10, 2.05, 9.99])
        assert runner.main([]) == 0
        assert launched == ["A"]
        skipped = [r for r in posted if r["status"] == "not run: daily budget spent"]
        assert [r["model"] for r in skipped] == ["B", "C"]

    def test_an_unset_budget_refuses_the_batch(self, monkeypatch):
        launched, _ = self._setup(monkeypatch, [0.0], cap=None)
        with pytest.raises(SystemExit):
            runner.main([])
        assert launched == []


class TestThePolicyIsContract:
    """Cadence and caps come from contract/scheduler.yaml (rule 5); a missing
    or bad value refuses (rule 12)."""

    def test_the_values_moved_unchanged(self):
        scheduler.policy.cache_clear()
        p = scheduler.policy()
        assert (p.cadence_days, p.first_fetch_thread_cap, p.refresh_thread_cap) == (7, 100, 25)

    @pytest.mark.parametrize("bad", [None, 0, -3, "7", True])
    def test_a_missing_or_bad_value_refuses(self, monkeypatch, bad):
        import judge.config as config

        doc = {"cadence_days": bad, "first_fetch_thread_cap": 100, "refresh_thread_cap": 25}
        monkeypatch.setattr(config, "_read", lambda name: doc)
        scheduler.policy.cache_clear()
        try:
            with pytest.raises(scheduler.SchedulerPolicyError):
                scheduler.policy()
        finally:
            scheduler.policy.cache_clear()


class TestTheDeadlineStopsLaunching:
    """A CI job has a hard time limit; past --deadline-minutes the runner
    launches no further model and names each one it did not run."""

    def test_models_after_the_deadline_are_named_not_launched(self, monkeypatch):
        launched, posted = TestTheBudgetStopsTheBatch()._setup(monkeypatch, [0.0, 0.0, 0.0])
        clock = iter([0.0, 0.0, 61 * 60.0, 62 * 60.0])     # start, A, B, C
        monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))
        assert runner.main(["--deadline-minutes", "60"]) == 0
        assert launched == ["A"]
        skipped = [r["model"] for r in posted
                   if r["status"] == "not run: this job's time budget is spent"]
        assert skipped == ["B", "C"]


def test_the_summary_shows_threads_a_run_could_not_read():
    rec = {"model": "A", "status": "ok", "documents_appended": 0,
           "threads_unreadable_here": 6087}
    summary = scheduler.summarise_runs([scheduler.safe_record(rec)])
    assert "Unreadable here" in summary and "| 6087 |" in summary


class TestTheJobLimitStopsAFetchNotTheRunner:
    """A fetch still running near the job's hard limit is stopped by the
    runner, which records it and still posts the summary."""

    def test_a_timed_out_fetch_is_recorded_and_the_summary_posts(self, monkeypatch):
        launched, posted = TestTheBudgetStopsTheBatch()._setup(monkeypatch, [0.0, 0.0, 0.0])
        timeouts = []

        def run_one(d, **kw):
            timeouts.append(kw.get("timeout_s"))
            if d.display_name == "A":
                return {"_end": None, "timed_out": True}
            return {"_end": {"kind": "end", "status": "ok"}}

        monkeypatch.setattr(runner, "run_one", run_one)
        assert runner.main(["--job-limit-minutes", "355"]) == 0
        assert posted, "the summary was not posted"
        a = next(r for r in posted if r["model"] == "A")
        assert a["status"].startswith("stopped at the job time limit")
        assert all(t is not None and t <= 345 * 60 for t in timeouts)

    def test_without_a_limit_there_is_no_timeout(self, monkeypatch):
        TestTheBudgetStopsTheBatch()._setup(monkeypatch, [0.0, 0.0, 0.0])
        timeouts = []
        monkeypatch.setattr(runner, "run_one", lambda d, **kw: timeouts.append(
            kw.get("timeout_s")) or {"_end": {"kind": "end", "status": "ok"}})
        runner.main([])
        assert timeouts == [None, None, None]
