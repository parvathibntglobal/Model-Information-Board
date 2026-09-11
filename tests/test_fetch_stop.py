"""Stopping a fetch is cooperative, recorded, and not a failure.

WHAT THIS IS FOR. A fetch run is a long pipeline, and the log shows each stage
as it lands. When a stage reports an error the rest of the run is usually
wasted — metered Reddit and X requests, and LLM calls at E5 — so there has to
be a way to say "stop, I have seen enough".

WHY NOT KILL THE PROCESS. Three reasons, each already paid for once here:

  * a metered request already spent is recorded by `record_rapidapi_quota`
    INSIDE `_get`. Killing mid-request spends the quota and loses the reading,
    which is the exact gap `collect/usage.py` was written to close.
  * a kill mid-transaction leaves the rollback to libpq's timeout rather than
    to `_safe_rollback`. That is how the 2026-09-09 run ended.
  * the PID is not ours to hold. `start_fetch` discards the `Popen` handle and
    the backend restarts freely, so a signal-based Stop would fail on exactly
    the runs somebody most wants to stop.

So the request is a FILE beside the log — same reasoning as the log itself
being a file: it has to work when the database does not.

THE CHECK LIVES IN `Progress.stage()`. Every transition goes through it,
including the per-query updates inside the harvest arms, so a run notices a
stop at the next thing it was going to report rather than only between the big
stages — and the arms are the slow part.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from fastapi.testclient import TestClient

from judge.app import app

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "fetch_model.py"


def _fetch_model():
    """Load `scripts/fetch_model.py` as a module. It is a script, not a package."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("fetch_model_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def prog(tmp_path, monkeypatch):
    fm = _fetch_model()
    monkeypatch.setattr(fm, "FETCH_DIR", tmp_path)
    return fm, fm.Progress("run-under-test", "acme/model-1")


class TestTheSentinelPassesThroughTheArmsHandlers:
    def test_it_is_not_an_exception(self):
        fm = _fetch_model()
        assert issubclass(fm.RunStopped, BaseException)
        assert not issubclass(fm.RunStopped, Exception), (
            "every harvest arm is wrapped in `except Exception` that turns a "
            "failure into a stage row reading `error`. A stop travelling "
            "through those would be recorded as the arm failing."
        )

    def test_an_except_exception_does_not_catch_it(self, prog):
        fm, p = prog
        p.stop_path.write_text("now", encoding="utf-8")
        caught_as_exception = False
        try:
            try:
                p.stage("E2R", "Harvest · Reddit", "running")
            except Exception:            # noqa: BLE001 - the point of the test
                caught_as_exception = True
        except fm.RunStopped:
            pass
        assert not caught_as_exception


class TestTheStageLineSurvivesTheStop:
    def test_the_line_is_written_before_the_checkpoint(self, prog):
        # The stage that just finished is a real finding and belongs in the log
        # whether or not the run continues.
        fm, p = prog
        p.stop_path.write_text("now", encoding="utf-8")
        with pytest.raises(fm.RunStopped):
            p.stage("E2", "Harvest", "running", detail="still recorded")
        raw = p.path.read_text(encoding="utf-8").splitlines()
        lines = [json.loads(x) for x in raw if x.strip()]
        assert any(r.get("detail") == "still recorded" for r in lines)

    def test_a_stage_before_any_request_is_untouched(self, prog):
        _fm, p = prog
        p.stage("E1", "Registry", "ok")          # must not raise
        assert p.stop_requested() is False

    def test_done_never_checkpoints(self, prog):
        # `done` is HOW a stop is recorded. If it could raise RunStopped the
        # run would end with no end record, and the UI polls until it sees one.
        _fm, p = prog
        p.stop_path.write_text("now", encoding="utf-8")
        p.done("stopped", "stopped by request")   # must not raise
        lines = p.path.read_text(encoding="utf-8").splitlines()
        assert any('"kind": "end"' in x or '"kind":"end"' in x for x in lines)

    def test_an_unreadable_var_does_not_stop_a_healthy_run(self, prog, monkeypatch):
        # Instrumentation must not be able to end a run that was going fine.
        _fm, p = prog

        def boom(*_a, **_k):
            raise OSError("var is gone")

        monkeypatch.setattr(type(p.stop_path), "exists", boom, raising=False)
        assert p.stop_requested() is False


class TestAStopIsNotAFailure:
    def test_main_records_stopped_rather_than_error(self):
        src = SCRIPT.read_text(encoding="utf-8")
        assert "except RunStopped:" in src
        block = src[src.index("except RunStopped:"):]
        block = block[: block.index("except Exception")]
        assert 'prog.done("stopped"' in block
        # CODE ONLY. The comment in that block quotes "error" to explain what
        # a stop is NOT, and a check that cannot tell a mention from a use
        # fails on its own documentation - the third time that has caught me
        # in this codebase, so it is written down rather than rediscovered.
        code = [
            line for line in block.splitlines() if not line.lstrip().startswith("#")
        ]
        code = " ".join(code)
        assert '"error"' not in code, (
            "a run somebody chose to abandon and a run that broke are "
            "different facts; the end record must not conflate them"
        )

    def test_it_says_what_happened_to_the_rows(self):
        # Rule 4: a caused absence has to say it was caused. Whatever did not
        # run is genuinely absent, and the reader needs to know the rows that
        # DID land are kept.
        src = SCRIPT.read_text(encoding="utf-8")
        block = src[src.index("except RunStopped:"):]
        block = block[: block.index("except Exception")]
        assert "append" in block

    def test_the_handlers_own_stop_row_does_not_raise_again(self, prog):
        """The bug this nearly shipped with.

        `main`'s RunStopped handler writes a STOP stage row before the end
        record, and that row goes through `stage()` like any other - so it
        raised RunStopped a second time, escaped `main`, and `prog.done()`
        never ran. The log then had no `end` record, and `done` is exactly
        what the UI polls for: it would have sat on "Fetching..." forever over
        a run that had already stopped.
        """
        fm, p = prog
        p.stop_path.write_text("now", encoding="utf-8")
        with pytest.raises(fm.RunStopped):
            p.stage("E2", "Harvest", "running")
        # Everything from here is the shutdown path and must not raise.
        p.stage("STOP", "Stopped by request", "skipped", detail="rows kept")
        p.done("stopped", "stopped by request")
        recs = [json.loads(x) for x in p.path.read_text(encoding="utf-8").splitlines() if x.strip()]
        assert recs[-1]["kind"] == "end"
        assert recs[-1]["status"] == "stopped"

    def test_the_latch_is_what_makes_that_safe(self):
        src = SCRIPT.read_text(encoding="utf-8")
        assert "self._stop_raised" in src
        assert "if self._stop_raised:" in src

    def test_the_ui_does_not_colour_it_as_a_failure(self):
        js = (ROOT / "web" / "src" / "components" / "FetchPanel.jsx").read_text(encoding="utf-8")
        assert "stopped: 'warn'" in js
        assert "r.status === 'stopped') return 'warn'" in js


class TestTheEndpoint:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        from judge import app as app_module

        monkeypatch.setattr(app_module, "_FETCH_DIR", tmp_path)
        return TestClient(app), tmp_path

    def test_it_writes_the_request_file(self, client):
        c, d = client
        (d / "r1.jsonl").write_text('{"kind": "run"}\n', encoding="utf-8")
        r = c.post("/fetch/stop", json={"run_id": "r1"})
        assert r.status_code == 200, r.text
        assert (d / "r1.stop").exists()
        assert r.json()["stop_requested"] is True

    def test_a_live_run_reports_was_running(self, client):
        c, d = client
        (d / "r2.jsonl").write_text('{"kind": "stage", "status": "running"}\n', encoding="utf-8")
        assert c.post("/fetch/stop", json={"run_id": "r2"}).json()["was_running"] is True

    def test_a_finished_run_says_nothing_will_read_it(self, client):
        # Otherwise the UI sits on "Stopping…" over a run that ended a minute
        # ago, which is a claim about the present that is simply false.
        c, d = client
        (d / "r3.jsonl").write_text(
            '{"kind": "stage", "status": "ok"}\n{"kind": "end", "status": "ok"}\n',
            encoding="utf-8",
        )
        assert c.post("/fetch/stop", json={"run_id": "r3"}).json()["was_running"] is False

    def test_a_run_that_has_written_nothing_yet_is_not_called_running(self, client):
        c, _d = client
        r = c.post("/fetch/stop", json={"run_id": "never-started"})
        assert r.json()["was_running"] is False

    @pytest.mark.parametrize("bad", ["../escape", "a/b", "a\\b", "..", ""])
    def test_a_run_id_that_could_escape_the_directory_is_refused(self, client, bad):
        c, _d = client
        assert c.post("/fetch/stop", json={"run_id": bad}).status_code == 422

    def test_it_is_idempotent(self, client):
        c, d = client
        (d / "r4.jsonl").write_text('{"kind": "run"}\n', encoding="utf-8")
        for _ in range(3):
            assert c.post("/fetch/stop", json={"run_id": "r4"}).status_code == 200
        assert (d / "r4.stop").exists()

    def test_it_does_not_signal_or_kill_anything(self):
        # The whole design. A kill loses a spent quota reading, abandons a
        # transaction mid-statement, and needs a PID this process does not hold.
        src = (ROOT / "judge" / "app.py").read_text(encoding="utf-8")
        block = src[src.index("def stop_fetch("):src.index("def fetch_log(")]
        for forbidden in ("os.kill", "terminate()", "SIGTERM", "SIGKILL", "taskkill"):
            assert forbidden not in block, forbidden


class TestTheButton:
    @staticmethod
    def _jsx() -> str:
        return (ROOT / "web" / "src" / "components" / "FetchPanel.jsx").read_text(encoding="utf-8")

    def test_it_is_next_to_fetch(self):
        js = self._jsx()
        fetch_at = js.index(">Fetch'")  if ">Fetch'" in js else js.index("'Fetch'")
        stop_at = js.index("'Stop'")
        assert 0 < stop_at - fetch_at < 1400, "the two buttons belong in one row"

    def test_it_only_appears_while_a_run_is_live(self):
        # A permanently visible Stop over an idle panel is a control that does
        # nothing, which is how a reader learns to distrust the others.
        assert "{running && runId && (" in self._jsx()

    def test_clicking_it_does_not_claim_the_run_has_ended(self):
        # The run is still going until it writes its end record, and the poll
        # is what notices that. Flipping `running` false on the click would
        # assert an ending that has not happened.
        js = self._jsx()
        stop_fn = js[js.index("async function stop()"):]
        stop_fn = stop_fn[: stop_fn.index("\n  }")]
        assert "setRunning(false)" in stop_fn, "only on the already-finished path"
        assert "was_running === false" in stop_fn

    def test_the_panel_says_what_stopping_costs(self):
        js = self._jsx()
        assert "Rows already written are kept" in js
