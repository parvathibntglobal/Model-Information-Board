"""The per-model fetch endpoints — `POST /fetch/start` and `GET /fetch/log`.

These never touch the pipeline in the test: `/fetch/start` spawns the
orchestrator as a subprocess, so the spawn is stubbed and we assert the WIRING
(a slash-free run id, the right argv, no inline pipeline run). `/fetch/log`
reads a local JSONL, so it is tested against a temp file — including the two
non-error silences it must keep apart: "run not started yet" vs "run finished".
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

import judge.app as app_module
from judge.app import app

client = TestClient(app, raise_server_exceptions=False)


class TestRoutesExist:
    def test_both_fetch_routes_are_registered(self):
        paths = {getattr(r, "path", "") for r in app.routes}
        assert "/fetch/start" in paths
        assert "/fetch/log" in paths


class TestStartSpawnsWithoutRunningInline:
    def test_start_returns_a_slash_free_run_id_and_spawns_the_script(self, monkeypatch):
        calls = {}

        def fake_popen(argv, **kwargs):
            calls["argv"] = argv
            calls["kwargs"] = kwargs
            return object()  # we never wait on it

        monkeypatch.setattr(app_module.subprocess, "Popen", fake_popen)

        res = client.post("/fetch/start", json={"model_version_id": "google/gemini-2.5-flash"})
        assert res.status_code == 200
        run_id = res.json()["run_id"]

        # The run id is a filename and a query value, so it must not carry a slash.
        assert "/" not in run_id and "\\" not in run_id
        assert run_id.startswith("google_gemini-2.5-flash-")
        # It spawned the orchestrator as a subprocess, passing the model id + run id —
        # it did NOT run the pipeline inline in the request.
        argv = calls["argv"]
        assert argv[1].endswith("fetch_model.py")
        assert "google/gemini-2.5-flash" in argv
        assert "--run-id" in argv and run_id in argv

    def test_empty_model_id_is_refused(self, monkeypatch):
        monkeypatch.setattr(app_module.subprocess, "Popen", lambda *a, **k: object())
        res = client.post("/fetch/start", json={"model_version_id": "   "})
        assert res.status_code == 422


class TestLogReadsProgress:
    def test_a_bad_run_id_is_refused(self):
        for bad in ("../secret", "a/b", "a\\b"):
            res = client.get("/fetch/log", params={"run_id": bad})
            assert res.status_code == 422, bad

    def test_a_run_that_has_not_started_is_not_an_error(self, monkeypatch, tmp_path):
        # No file yet: started=false, done=false, no records — NOT a 404/500.
        monkeypatch.setattr(app_module, "_FETCH_DIR", tmp_path)
        res = client.get("/fetch/log", params={"run_id": "nope-abc123"})
        assert res.status_code == 200
        body = res.json()
        assert body["started"] is False and body["done"] is False and body["records"] == []

    def test_a_written_log_is_parsed_and_done_flips_on_the_end_record(self, monkeypatch, tmp_path):
        monkeypatch.setattr(app_module, "_FETCH_DIR", tmp_path)
        run_id = "mv_x-deadbeef"
        (tmp_path / f"{run_id}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in [
                {"kind": "run", "run_id": run_id},
                {"kind": "stage", "id": "E2", "name": "Harvest", "status": "ok",
                 "documents_inserted": 3},
                {"kind": "end", "status": "ok", "detail": "fetch complete"},
            ]) + "\n",
            encoding="utf-8",
        )
        body = client.get("/fetch/log", params={"run_id": run_id}).json()
        assert body["started"] is True
        assert body["done"] is True                       # end record present
        assert any(r.get("id") == "E2" for r in body["records"])

    def test_started_but_not_done_while_still_running(self, monkeypatch, tmp_path):
        monkeypatch.setattr(app_module, "_FETCH_DIR", tmp_path)
        run_id = "mv_y-cafe"
        (tmp_path / f"{run_id}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in [
                {"kind": "run", "run_id": run_id},
                {"kind": "stage", "id": "E2", "name": "Harvest", "status": "running"},
            ]) + "\n",
            encoding="utf-8",
        )
        body = client.get("/fetch/log", params={"run_id": run_id}).json()
        assert body["started"] is True and body["done"] is False


class TestADeadRunStopsReadingAsRunning:
    """The reaper wrote to the table; both readers read a file.

    `fetch_reaper.reap` appends its `abandoned` record to `fetch_log` and
    touches no file. `/fetch/log` and `/fetch/runs` prefer the local file. So on
    the machine that STARTED a run, the reaper's verdict was invisible and the
    UI polled forever.

    Measured on machine-B 2026-09-16, five days after the reaper had ruled:

        GET /fetch/log?run_id=anthropic_claude-fable-5-1-fcb1e17b
          source : local file
          done   : False
          records: 77

    with an `abandoned` end record sitting in `fetch_log` for that same run.
    Three other runs had read as `running` for ~16 hours, because `reap` had
    exactly one caller - `/fetch/start` - so nothing was reaped unless somebody
    happened to begin another fetch.
    """

    #: Older than `DEFAULT_SILENT_FOR` (45 min) by a wide margin.
    LONG_AGO = "2020-01-01T00:00:00Z"

    @staticmethod
    def _quiet_run(tmp_path, monkeypatch, run_id, at):
        monkeypatch.setattr(app_module, "_FETCH_DIR", tmp_path)
        (tmp_path / f"{run_id}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in [
                {"kind": "run", "run_id": run_id, "at": at},
                {"kind": "stage", "id": "E5", "name": "Extract",
                 "status": "running", "at": at},
            ]) + "\n",
            encoding="utf-8",
        )

    def test_the_tables_end_record_settles_a_file_that_never_got_one(
        self, monkeypatch, tmp_path,
    ):
        run_id = "mv_dead-abcd1234"
        self._quiet_run(tmp_path, monkeypatch, run_id, self.LONG_AGO)
        monkeypatch.setattr(
            app_module, "_fetch_log_from_db",
            lambda rid: [({"kind": "end", "status": "abandoned",
                           "detail": "no progress recorded for 45 minutes"}, "OTHER")],
        )
        body = client.get("/fetch/log", params={"run_id": run_id}).json()
        assert body["done"] is True, (
            "a run the reaper already marked abandoned must stop reading as running"
        )
        assert body["records"][-1]["status"] == "abandoned"

    def test_the_adoption_is_declared_rather_than_passed_off_as_the_runs_own_words(
        self, monkeypatch, tmp_path,
    ):
        """The last record is then another process's verdict, not the run's."""
        run_id = "mv_dead-abcd5678"
        self._quiet_run(tmp_path, monkeypatch, run_id, self.LONG_AGO)
        monkeypatch.setattr(
            app_module, "_fetch_log_from_db",
            lambda rid: [({"kind": "end", "status": "abandoned"}, "OTHER")],
        )
        body = client.get("/fetch/log", params={"run_id": run_id}).json()
        assert body.get("end_adopted_from") == "shared table"

    def test_a_run_inside_the_silence_window_is_left_alone(self, monkeypatch, tmp_path):
        """LOCAL FILE FIRST still holds where it was always meant to.

        A live run polls this endpoint every second. Asking the database about
        one that spoke moments ago would be both wrong and exactly the round
        trip that rule exists to avoid, so the table is not consulted at all.
        """
        from datetime import UTC, datetime

        run_id = "mv_live-abcd9999"
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._quiet_run(tmp_path, monkeypatch, run_id, now)

        asked = []
        monkeypatch.setattr(
            app_module, "_fetch_log_from_db",
            lambda rid: asked.append(rid) or [
                ({"kind": "end", "status": "abandoned"}, "OTHER")],
        )
        body = client.get("/fetch/log", params={"run_id": run_id}).json()
        assert body["done"] is False, "a run that just spoke is not abandoned"
        assert asked == [], (
            "the shared table must not be consulted for a run inside the "
            "silence window - that is the per-second round trip `/fetch/log` "
            "documents itself as avoiding"
        )

    def test_listing_runs_reaps_first(self, monkeypatch, tmp_path):
        """The caller `fetch_reaper` always named and nobody wired.

        Its docstring: "The caller is a fetch about to start OR A PAGE ABOUT TO
        RENDER." Only the first existed.
        """
        import contextlib

        monkeypatch.setattr(app_module, "_FETCH_DIR", tmp_path)
        called = []
        # `_conn` raises without a DATABASE_URL, and the guard below swallows
        # that - correctly, but it would also hide a missing reap call. Stubbed
        # so this test measures the WIRING and not the environment.
        monkeypatch.setattr(app_module, "_conn",
                            lambda: contextlib.nullcontext(object()))
        monkeypatch.setattr(app_module.fetch_reaper, "reap",
                            lambda conn, **kw: called.append(True) or [])
        monkeypatch.setattr(app_module, "_fetch_runs_from_db", lambda *a, **k: [])
        res = client.get("/fetch/runs", params={"model_version_id": "mv/x"})
        assert res.status_code == 200
        assert called, "listing runs must reap before rendering"
        assert "reaped_runs" in res.json(), (
            "a page-render write to shared history must be named in the "
            "response, the way /fetch/start names it"
        )

    def test_a_reaper_failure_never_takes_the_history_down(self, monkeypatch, tmp_path):
        """A history that will not load is worse than the stale row it tidies."""
        monkeypatch.setattr(app_module, "_FETCH_DIR", tmp_path)

        def boom(*a, **k):
            raise RuntimeError("database unreachable")

        monkeypatch.setattr(app_module, "_conn", boom)
        monkeypatch.setattr(app_module, "_fetch_runs_from_db", lambda *a, **k: [])
        res = client.get("/fetch/runs", params={"model_version_id": "mv/x"})
        assert res.status_code == 200
        assert res.json()["reaped_runs"] == []
