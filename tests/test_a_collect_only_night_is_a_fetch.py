"""A collect-only scheduled night: harvested, nothing extracted, and counted.

2026-10-26: with no working OpenRouter key, every scheduled run sent its threads,
got no answer, and ended `ok` with 0 read. `LAST_SUCCESS` counted none of them,
so every model was due every night and the tail of the list never ran inside the
time budget. `FETCH_EXTRACT=off` makes the run collect-only on purpose, and an
`ok` collect-only run counts. The same night showed GPT-6 Astra never fetched,
because its row id has a slash and the runner put it in a file name.
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime

import pytest

import scripts.run_scheduled_fetches as runner
from judge import scheduler

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _row(mv, name):
    return {"model_version_id": mv, "display_name": name, "tracked": True,
            "in_window": True, "last_success": None}


class TestTheSwitch:
    @pytest.mark.parametrize("raw,on", [(None, True), ("on", True), (" ON ", True),
                                        ("off", False), ("Off", False)])
    def test_on_unless_off(self, raw, on):
        assert scheduler.extract_enabled(raw) is on

    @pytest.mark.parametrize("raw", ["", "0", "no", "false", "of"])
    def test_anything_else_refuses(self, raw):
        with pytest.raises(SystemExit):
            scheduler.extract_enabled(raw)


class TestACollectOnlyBatch:
    def _setup(self, monkeypatch):
        import judge.spend_ledger as ledger

        monkeypatch.setenv("SCHEDULER_ENABLED", "1")
        monkeypatch.setenv("FETCH_EXTRACT", "off")
        monkeypatch.delenv("EXTRACTION_DAILY_BUDGET_USD", raising=False)
        monkeypatch.setattr(runner, "_read_only_dsn", lambda: "postgresql://x@h/db")

        class _Conn:
            def __enter__(self): return self
            def __exit__(self, *a): return False
        monkeypatch.setattr("psycopg.connect", lambda *a, **k: _Conn())
        monkeypatch.setattr(runner, "due_rows", lambda conn: [_row("a", "A"), _row("b", "B")])

        def no_spend(*a, **k):
            raise AssertionError("a collect-only batch read the spend ledger")

        monkeypatch.setattr(ledger, "spent_today", no_spend)
        launched, posted = [], []
        monkeypatch.setattr(runner, "run_one", lambda d, **k: launched.append(d.display_name)
                            or {"_end": {"kind": "end", "status": "ok", "extract_skipped": True}})
        monkeypatch.setattr(runner, "post_summary", lambda recs: posted.extend(recs))
        monkeypatch.setattr(runner, "in_progress", lambda conn, now: set())
        return launched, posted

    def test_it_needs_no_budget_and_reads_no_ledger(self, monkeypatch):
        launched, posted = self._setup(monkeypatch)
        assert runner.main([]) == 0
        assert launched == ["A", "B"]
        assert all(r.get("extract_skipped") for r in posted)

    def test_an_extracting_batch_still_refuses_without_a_budget(self, monkeypatch):
        self._setup(monkeypatch)
        monkeypatch.setenv("FETCH_EXTRACT", "on")
        with pytest.raises(SystemExit):
            runner.main([])


def test_the_summary_says_collect_only_rather_than_read_zero():
    rec = {"model": "A", "status": "ok", "documents_appended": 40, "threads_read": 0,
           "threads_unreadable_here": 1648, "extract_skipped": True}
    summary = scheduler.summarise_runs([scheduler.safe_record(rec)])
    assert "| not run: collect-only |" in summary
    assert "1 of 1 ran collect-only" in summary


def test_a_night_with_extraction_says_nothing_about_collect_only():
    rec = {"model": "A", "status": "ok", "threads_read": 3}
    assert "collect-only" not in scheduler.summarise_runs([scheduler.safe_record(rec)])


def test_a_slash_in_the_row_id_never_reaches_the_run_id(monkeypatch):
    seen = {}

    class _Proc:
        returncode = 0
        stdout = ""

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return _Proc()

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(runner, "_end_record", lambda rid: None)
    due = scheduler.rank_due([_row("openai/gpt-6-astra", "GPT-6 Astra")], datetime.now(UTC))[0]
    result = runner.run_one(due, sources=None, development_write=False)
    assert "/" not in result["run_id"] and result["run_id"].startswith("openai_gpt-6-astra-")
    # The model id itself still goes to fetch_model unchanged.
    assert seen["cmd"][seen["cmd"].index("scripts.fetch_model") + 1] == "openai/gpt-6-astra"


def test_the_workflow_runs_collect_only_and_asks_for_the_key_only_when_extracting():
    wf = (ROOT / ".github" / "workflows" / "scheduled-fetches.yml").read_text(encoding="utf-8")
    assert 'FETCH_EXTRACT: "off"' in wf
    gate = wf[wf.index('if [ "$FETCH_EXTRACT" != "off" ]'):]
    assert "OPENROUTER_API_KEY" in gate.split("fi", 1)[0]


def test_fetch_model_skips_e5_by_name_when_collect_only():
    src = (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
    block = src[src.index("if not FETCH_EXTRACT:"):src.index("extract_and_curate(db.live(prog)")]
    assert "record_summary(extract_skipped=True)" in block
    assert '"E5", "Extract", "skipped"' in block
