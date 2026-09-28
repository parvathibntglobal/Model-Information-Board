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
        assert d.reason == "first fetch" and d.thread_cap == scheduler.FIRST_FETCH_THREAD_CAP

    def test_a_recent_success_is_not_due(self):
        assert scheduler.rank_due([_row("a", "A", last=NOW - timedelta(days=3))], NOW) == []

    def test_a_stale_success_is_a_refresh_at_the_smaller_cap(self):
        (d,) = scheduler.rank_due([_row("a", "A", last=NOW - timedelta(days=9))], NOW)
        assert d.reason.startswith("refresh") and d.thread_cap == scheduler.REFRESH_THREAD_CAP

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
               "threads_read": 20, "claims_stored": 7, "harvest_arms_errored": ["E2R"]}
        summary = scheduler.summarise_runs([scheduler.safe_record(rec)])
        assert "| 12 |" in summary and "| 20 |" in summary and "| 7 |" in summary
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
