"""One failed `fetch_log` write must not lose the rest of the run, or its end.

Until 2026-10-05 the mirror stopped for the whole run after its first failure.
Staging drops connections and comes back, so two button runs that day mirrored
7 of 205 and 17 of 193 lines, never sent their `ok` end record, and the reaper
recorded both as `abandoned` - the scheduler then listed GPT-6 Luna as never
fetched. Now a failure only pauses the mirror, and `done` replays the file so
the gaps fill (ids are content-derived, so a replay adds only what is missing).

The database is a fake: `_mirror_fetch_line` is replaced by a recorder.
"""
from __future__ import annotations

import pytest

import scripts.fetch_model as fm


@pytest.fixture()
def sent(monkeypatch, tmp_path):
    monkeypatch.setattr(fm, "FETCH_DIR", tmp_path)
    monkeypatch.setenv("FETCH_QUIET", "1")
    monkeypatch.setattr(fm, "MIRROR_BACKOFF_S", 0.0)
    calls = {"n": 0, "rows": {}}

    def fake(*, run_id, seq, rec, model_version_id):
        calls["n"] += 1
        if calls["n"] == 2:          # the second write fails: a dropped connection
            return False
        calls["rows"][seq] = rec.get("kind")   # keyed like the real id: idempotent
        return True

    monkeypatch.setattr(fm, "_mirror_fetch_line", fake)
    return calls


def test_a_failure_pauses_the_mirror_and_the_end_still_arrives(sent):
    prog = fm.Progress("run-drop", "mv_1")
    prog.stage("E1", "Registry", "ok", detail="x")
    prog.stage("E2", "Harvest", "ok", detail="x")     # this write fails
    prog.stage("E3", "Assemble", "ok", detail="x")
    prog.done("ok", "fetch complete")

    lines = prog.path.read_text(encoding="utf-8").splitlines()
    assert set(sent["rows"]) == set(range(len(lines))), "a line never reached fetch_log"
    assert "end" in sent["rows"].values()


def test_the_switch_still_turns_mirroring_off(sent):
    prog = fm.Progress("run-off", "mv_1")   # its opening line mirrors as usual
    prog._mirror = False
    before = sent["n"]
    prog.stage("E1", "Registry", "ok", detail="x")
    prog.done("ok", "fetch complete")
    assert sent["n"] == before, "a switched-off mirror still wrote, or replayed"
