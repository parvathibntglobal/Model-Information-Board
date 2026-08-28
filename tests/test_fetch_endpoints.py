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
