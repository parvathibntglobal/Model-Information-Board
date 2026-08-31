"""The composition-root orchestrator, `scripts/fetch_model.py`.

Two pieces are testable without a database, an LLM, or the network:

  - `Progress` — the per-stage JSONL the fetch view tails. Its SHAPE is a
    contract with the `/fetch/log` reader and the UI, so it is pinned here.
  - `build_thread_inputs` — the stand-in for the deferred RawTextResolver. Its
    whole job is to SKIP: a thread already extracted, a thread whose flattened
    payload is not on this machine (harvested elsewhere), and a thread with no
    resolvable raw member text (unrenderable). Those skips are what scope a
    fetch to the model it just harvested, so each is exercised directly.
"""

from __future__ import annotations

import inspect
import json
from types import SimpleNamespace

import scripts.fetch_model as fetch_model


class TestRedditWriteCall:
    def test_it_passes_retrieval_provenance(self):
        """reddit_write.write_documents requires retrieval_provenance (it merged
        as required), and the model-name arm is 'not_recorded' per reddit_write.py.
        A call without it crashes the whole Reddit stage — invisible until a live
        fetch, which is how it shipped once."""
        src = inspect.getsource(fetch_model.harvest_reddit)
        assert 'retrieval_provenance="not_recorded"' in src


class TestExtractionIsObservableAndBounded:
    """E5 ran silently for ~13 min on 5 large threads and looked hung. These
    pin the fixes: per-thread progress, and an oversized-thread cap."""

    def test_run_all_accepts_a_progress_callback(self):
        import inspect as _inspect

        from judge.pipeline import Pipeline
        assert "on_thread" in _inspect.signature(Pipeline.run_all).parameters

    def test_the_fetch_wires_progress_and_caps_oversized_threads(self):
        src = inspect.getsource(fetch_model.extract_and_curate)
        assert "on_thread=" in src                 # per-thread progress wired
        assert "MAX_FETCH_THREAD_CHARS" in src     # oversized threads deferred
        assert isinstance(fetch_model.MAX_FETCH_THREAD_CHARS, int)


class TestProgressLog:
    def test_run_stage_end_records_have_the_shape_the_reader_expects(self, monkeypatch, tmp_path):
        monkeypatch.setattr(fetch_model, "FETCH_DIR", tmp_path)

        prog = fetch_model.Progress("run-1", "google/gemini-2.5-flash")
        prog.stage("E2", "Harvest", "ok", documents_inserted=3)
        prog.done("ok", "fetch complete")

        recs = [
            json.loads(line)
            for line in (tmp_path / "run-1.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        # First: the run header, carrying the model id back for the log.
        assert recs[0]["kind"] == "run"
        assert recs[0]["run_id"] == "run-1"
        assert recs[0]["model_version_id"] == "google/gemini-2.5-flash"
        # Middle: a stage line is a FINDING — id, name, status, and its counts.
        stage = recs[1]
        assert stage["kind"] == "stage"
        assert (stage["id"], stage["name"], stage["status"]) == ("E2", "Harvest", "ok")
        assert stage["documents_inserted"] == 3
        # Last: the end record is what flips `done` true for the poller.
        assert recs[-1]["kind"] == "end" and recs[-1]["status"] == "ok"

    def test_each_record_carries_a_timestamp(self, monkeypatch, tmp_path):
        monkeypatch.setattr(fetch_model, "FETCH_DIR", tmp_path)
        prog = fetch_model.Progress("run-2", "mv_x")
        prog.stage("E1", "Registry", "running")
        prog.done("ok")
        recs = [
            json.loads(line)
            for line in (tmp_path / "run-2.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        assert all(r.get("at") for r in recs)


# ---------------------------------------------------------------- build_thread_inputs

class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _Conn:
    """Answers the two queries build_thread_inputs makes, and nothing else."""

    def __init__(self, thread_rows, doc_text_refs):
        self._threads = thread_rows
        self._docs = doc_text_refs  # document_id -> text_ref

    def execute(self, sql, params=()):
        if "FROM thread_context" in sql:
            return _Cursor(self._threads)
        if "FROM document" in sql:
            members = params[0]
            return _Cursor([(did, self._docs.get(did)) for did in members])
        raise AssertionError(f"unexpected query: {sql}")


def _fake_store(texts):
    """A RawStore stand-in: get_text returns known text, raises for anything else
    (exactly how a payload harvested on another machine behaves here)."""

    class _Store:
        def __init__(self, *a, **k):
            pass

        def get_text(self, ref):
            if ref not in texts:
                raise KeyError(ref)
            return texts[ref]

    return _Store


def test_build_thread_inputs_keeps_only_locally_resolvable_unseen_threads(monkeypatch):
    # Four threads, one usable:
    #   tcA — flattened + member text both local        → KEPT
    #   tcB — flattened payload missing (elsewhere)     → skipped
    #   tcC — already extracted (in `seen`)             → skipped before any read
    #   tcD — flattened local, but member text missing  → skipped (unrenderable)
    thread_rows = [
        ("tcA", "flatA", None, ["dA"]),
        ("tcB", "flatB", None, ["dB"]),
        ("tcC", "flatC", None, ["dC"]),
        ("tcD", "flatD", None, ["dD"]),
    ]
    doc_text_refs = {"dA": "rawA", "dB": "rawB", "dD": "rawD"}  # note: no "flatB"/"rawD" in store
    store_texts = {"flatA": "flattened A", "flatD": "flattened D", "rawA": "raw A"}

    monkeypatch.setattr(fetch_model, "RawStore", _fake_store(store_texts))
    monkeypatch.setattr(fetch_model, "settings", lambda: SimpleNamespace(raw_store_path="unused"))

    conn = _Conn(thread_rows, doc_text_refs)
    inputs, doc_ids = fetch_model.build_thread_inputs(conn, seen={"tcC"}, limit=200)

    assert [ti.thread_context_id for ti in inputs] == ["tcA"]
    assert doc_ids == {"dA"}
    kept = inputs[0]
    assert kept.flattened_text == "flattened A"
    assert kept.raw_text_of == {"dA": "raw A"}
    assert kept.offset_map == ()   # empty offset_map round-trips to an empty tuple


def test_build_thread_inputs_is_empty_when_nothing_resolves(monkeypatch):
    thread_rows = [("tcB", "flatB", None, ["dB"])]
    monkeypatch.setattr(fetch_model, "RawStore", _fake_store({}))  # store has nothing
    monkeypatch.setattr(fetch_model, "settings", lambda: SimpleNamespace(raw_store_path="unused"))

    inputs, doc_ids = fetch_model.build_thread_inputs(
        _Conn(thread_rows, {"dB": "rawB"}), seen=set(), limit=200
    )
    assert inputs == [] and doc_ids == set()
