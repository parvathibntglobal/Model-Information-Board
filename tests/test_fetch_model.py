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

    def fetchone(self):
        """Needed since the gated-out COUNT arrived. Returns None on no rows,
        like psycopg, rather than raising - a fake that is stricter than the
        real driver fails tests for the wrong reason."""
        return self._rows[0] if self._rows else None


class _Conn:
    """Answers the three queries build_thread_inputs makes, and nothing else.

    The third arrived with the triage gate: the thread query now asks only for
    contexts with a surviving member, and a second counts the ones held back.
    Both are answered here rather than stubbed loosely, because the ORDER of the
    checks matters - the count query also selects `FROM thread_context`, so a
    fake that matched on that substring alone would answer the wrong one.
    """

    def __init__(self, thread_rows, doc_text_refs, gated_out=0, doc_sources=None):
        self._threads = thread_rows
        self._docs = doc_text_refs  # document_id -> text_ref
        self._gated_out = gated_out
        #: document_id -> source. The document query started selecting it on
        #: 2026-09-14: `raw_text_of` must hold the PROSE the offset map indexes,
        #: and picking the prose extractor needs to know the platform.
        self._sources = doc_sources or {}

    def execute(self, sql, params=()):
        # Checked FIRST: the gated-out count is also a thread_context query, and
        # it is distinguished by counting rather than by selecting columns.
        if "count(*)" in sql and "NOT EXISTS" in sql:
            return _Cursor([(self._gated_out,)])
        if "FROM thread_context" in sql:
            assert "status = 'kept'" in sql, (
                "the thread query must require a surviving member, or a filtered "
                "document still reaches the model. "
                "It checks `status` and NOT `triage_verdict`, deliberately. E4 "
                "writes the verdict as a RECORDED FIELD rather than a gate - two "
                "of its six checks cannot run and its error rate is unmeasured, "
                "so rule 8 keeps it a weight. `status` is what judge/ filters on "
                "and what carries the index. Gating on the verdict was tried and "
                "reverted: a wrong gate's false positives are invisible, because "
                "it drops the document and an absence we caused reads as one we "
                "found."
            )
            assert "triage_verdict" not in sql, (
                "extraction must NOT gate on triage_verdict until its error rate "
                "has been measured - rule 8, and the chain's own docstring says so"
            )
            return _Cursor(self._threads)
        if "FROM document" in sql:
            assert "source" in sql, (
                "the document query must select `source`. `raw_text_of` feeds "
                "verify() step 3, which renders raw[raw_start:raw_end] as the "
                "PUBLISHED quote, and those offsets index the prose the "
                "assembler flattened - so the payload has to be run through "
                "that platform's prose extractor, and choosing it needs the "
                "source. Reading text_ref verbatim published a slice of a JSON "
                "envelope as somebody's sentence on ten of ten claims."
            )
            members = params[0]
            return _Cursor([
                (did, self._docs.get(did), self._sources.get(did, "reddit"))
                for did in members
            ])
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
    # `rawA` IS A PAYLOAD, because `document.text_ref` has pointed at the
    # payload since the ruling of 2026-08-28. `raw_text_of` must carry the
    # PROSE extracted from it - what the offset map indexes and what step 3
    # publishes - so the fixture stores what the store really holds.
    raw_a_payload = json.dumps({"title": "Opus 4.8 truncates", "selftext": "Reproduced twice."})
    store_texts = {"flatA": "flattened A", "flatD": "flattened D", "rawA": raw_a_payload}

    monkeypatch.setattr(fetch_model, "RawStore", _fake_store(store_texts))
    monkeypatch.setattr(fetch_model, "settings", lambda: SimpleNamespace(raw_store_path="unused"))

    conn = _Conn(thread_rows, doc_text_refs)
    # 4-tuple since 2026-09-10: the oversized list is RETURNED rather than
    # recomputed by the caller, because the size ceiling now runs inside
    # selection - a cap that counted threads it then discarded delivered 6
    # of 25.
    inputs, doc_ids, gated_out, _oversized = fetch_model.build_thread_inputs(
        conn, seen={"tcC"}, limit=200
    )
    # The gate's cost is reported, not inferred: a thin corpus because the
    # gates worked and a thin corpus because the harvest was thin read the
    # same downstream, and only one of them is good news.
    assert gated_out == 0

    assert [ti.thread_context_id for ti in inputs] == ["tcA"]
    assert doc_ids == {"dA"}
    kept = inputs[0]
    assert kept.flattened_text == "flattened A"
    # THE PROSE, NOT THE PAYLOAD. `verify()` step 3 renders this as the quote a
    # reader sees, so an envelope here is an envelope on the board — which is
    # what happened on 2026-09-14 to ten of ten claims, each with
    # `quote_verified = true`, because the check ran on the flattened prose and
    # the display step then sliced something else.
    assert kept.raw_text_of == {"dA": "Opus 4.8 truncates\n\nReproduced twice."}
    assert "selftext" not in kept.raw_text_of["dA"], "the envelope reached the display text"
    assert kept.offset_map == ()   # empty offset_map round-trips to an empty tuple


def test_build_thread_inputs_is_empty_when_nothing_resolves(monkeypatch):
    thread_rows = [("tcB", "flatB", None, ["dB"])]
    monkeypatch.setattr(fetch_model, "RawStore", _fake_store({}))  # store has nothing
    monkeypatch.setattr(fetch_model, "settings", lambda: SimpleNamespace(raw_store_path="unused"))

    inputs, doc_ids, _gated, _oversized = fetch_model.build_thread_inputs(
        _Conn(thread_rows, {"dB": "rawB"}), seen=set(), limit=200
    )
    assert inputs == [] and doc_ids == set()


class TestTheArtifactGuard:
    """`raw_text_of` must be the artifact `offset_map` indexes, checked not assumed.

    2026-09-14. Pointing the loader at the prose fixes the artifact; it does not
    PROVE it, and this defect was invisible for exactly that reason. `verify()`
    step 3 slices `raw[raw_start:raw_end]` and its only check is
    `raw_end > len(raw)` - the payload is LONGER than the prose it wraps, so
    every offset fitted and the slice landed silently in the wrong place, on ten
    of ten claims, each with `quote_verified = true`.

    So the check is on the artifact, before any model call, and it costs one
    subtraction per member.
    """

    @staticmethod
    def _inputs(monkeypatch, member_text, raw_end):
        """One thread, one member, an offset_map claiming `raw_end` characters."""
        payload = json.dumps({"title": "", "selftext": member_text})
        thread_rows = [("tc", "flat", [{
            "flat_start": 0, "flat_end": raw_end,
            "raw_start": 0, "raw_end": raw_end,
            "document_id": "dA",
        }], ["dA"])]
        monkeypatch.setattr(
            fetch_model, "RawStore",
            _fake_store({"flat": "flattened", "rawA": payload}),
        )
        monkeypatch.setattr(
            fetch_model, "settings", lambda: SimpleNamespace(raw_store_path="unused")
        )
        conn = _Conn(thread_rows, {"dA": "rawA"})
        inputs, _docs, _gated, _over = fetch_model.build_thread_inputs(
            conn, seen=set(), limit=200
        )
        return inputs

    def test_a_member_matching_its_map_is_kept(self, monkeypatch):
        body = "x" * 100
        # reddit_prose returns title + "\n\n" + selftext, and the title is empty.
        expected = len("" + "\n\n" + body)
        inputs = self._inputs(monkeypatch, body, expected)
        assert inputs, "a member whose prose matches its map must be kept"
        assert inputs[0].raw_text_of["dA"].endswith(body)

    def test_the_github_two_character_drift_is_tolerated(self, monkeypatch):
        """1,285 real documents drift by +2 and every one of them is fine.

        `github_issue_prose` joins title and body with a separator the assembled
        text did not carry. Equality here would refuse them all - which is why
        the guard has a tolerance and why that tolerance is measured rather than
        chosen.
        """
        body = "y" * 100
        expected = len("\n\n" + body) - 2
        inputs = self._inputs(monkeypatch, body, expected)
        assert inputs and "dA" in inputs[0].raw_text_of

    def test_the_payload_sized_gap_is_refused(self, monkeypatch):
        """The real one: the map said 749 and the payload was 1,988.

        The thread is dropped here rather than the member, because this fixture
        has exactly one member - which is the existing "no raw_text_of, so step 3
        could not render" path, reached for a new reason.
        """
        body = "z" * 2000
        inputs = self._inputs(monkeypatch, body, 749)
        assert inputs == [], (
            "a member whose prose is 1,200 characters longer than its offset map "
            "describes must not be sliced; that is the 2026-09-14 defect"
        )

    def test_the_tolerance_is_small_enough_to_be_worth_having(self):
        # A guard that tolerates a large gap catches nothing. The smallest real
        # failure measured was +1,239; the largest benign drift was +2.
        assert fetch_model._MAX_PROSE_DRIFT <= 10
