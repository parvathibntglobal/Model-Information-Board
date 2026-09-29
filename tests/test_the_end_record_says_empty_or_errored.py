"""The end record says what the harvest found, as fields - so "empty" and
"errored" stop being the same record.

A run's `end` line carried a status, a sentence, and (since 2026-09-22) what
extraction sent and stored. How many documents the harvest appended lived only
in each arm's detail string. Measured 2026-09-28 over 80 harvesting runs: 29
appended nothing, and 7 of those 29 were harvest errors rather than exhausted
pools. A selection rule reading "empty" off the old record would have treated a
broken harvest as a dry one - which is the premise the withdrawn yield backoff
was built on.

Absent is unknown, never 0 (rule 6).
"""

from __future__ import annotations

import json

import pytest

import scripts.fetch_model as fm


@pytest.fixture()
def prog(monkeypatch, tmp_path):
    monkeypatch.setattr(fm, "FETCH_DIR", tmp_path)
    monkeypatch.setenv("FETCH_QUIET", "1")
    p = fm.Progress("run-under-test", "mv_1")
    p._mirror = False
    return p


def _end(prog) -> dict:
    records = [json.loads(line) for line in prog.path.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    ends = [r for r in records if r.get("kind") == "end"]
    assert len(ends) == 1
    return ends[0]


class TestEmptyAndErroredAreDifferentRecords:
    def test_a_dry_harvest(self, prog):
        prog.stage("E2", "Harvest", "ok", documents_inserted=0, http_errors=0)
        prog.stage("E2R", "Harvest · Reddit", "ok", documents_inserted=0, http_errors=0)
        prog.done("ok", "fetch complete")
        end = _end(prog)
        assert end["documents_appended"] == 0
        assert end["harvest_arms_errored"] == []
        assert end["harvest_arms"] == ["E2", "E2R"]

    def test_a_broken_harvest(self, prog):
        prog.stage("E2", "Harvest", "error", documents_inserted=0, http_errors=24)
        prog.stage("E2R", "Harvest · Reddit", "error", detail="RAPIDAPI_KEY is not set")
        prog.done("ok", "fetch complete")
        end = _end(prog)
        assert end["harvest_arms_errored"] == ["E2", "E2R"]
        assert end["harvest_http_errors"] == 24
        assert end["status"] == "error", "#327: ok is earned"

    def test_the_two_are_told_apart_by_fields_alone(self, prog, tmp_path, monkeypatch):
        prog.stage("E2", "Harvest", "ok", documents_inserted=0, http_errors=0)
        prog.done("ok", "fetch complete")
        dry = _end(prog)
        monkeypatch.setattr(fm, "FETCH_DIR", tmp_path / "b")
        (tmp_path / "b").mkdir()
        other = fm.Progress("run-b", "mv_1")
        other._mirror = False
        other.stage("E2", "Harvest", "error", documents_inserted=0, http_errors=24)
        other.done("ok", "fetch complete")
        broken = _end(other)
        assert dry["documents_appended"] == broken["documents_appended"] == 0
        assert dry["harvest_arms_errored"] != broken["harvest_arms_errored"]


class TestAbsentIsUnknown:
    def test_no_arm_reporting_a_count_means_no_count(self, prog):
        prog.stage("E2B", "Harvest · Blogs", "skipped", detail="feed-based")
        prog.done("ok", "fetch complete")
        end = _end(prog)
        assert "documents_appended" not in end, "not written as 0"
        assert end["harvest_arms_skipped"] == ["E2B"]

    def test_a_run_that_never_harvested_carries_no_harvest_fields(self, prog):
        prog.done("error", "refused: unsafe write target")
        end = _end(prog)
        assert not any(k.startswith("harvest") or k == "documents_appended" for k in end)

    def test_counts_sum_over_the_arms_that_reported_them(self, prog):
        prog.stage("E2", "Harvest", "ok", documents_inserted=4, http_errors=0)
        prog.stage("E2X", "Harvest · X", "ok", documents_inserted=5, http_errors=1)
        prog.stage("E2B", "Harvest · Blogs", "skipped", detail="feed-based")
        prog.done("ok", "fetch complete")
        end = _end(prog)
        assert end["documents_appended"] == 9 and end["harvest_http_errors"] == 1


class TestTheLastLinePerArmCounts:
    def test_mains_error_line_after_an_arm_raised_is_its_verdict(self, prog):
        """An arm can write its own verdict and then raise, and `main` writes
        an error line for it. The later line is what happened."""
        prog.stage("E2A", "Harvest · arXiv", "ok", documents_inserted=2, http_errors=0)
        prog.stage("E2A", "Harvest · arXiv", "error", detail="raised after writing")
        prog.done("ok", "fetch complete")
        end = _end(prog)
        assert end["harvest_arms_errored"] == ["E2A"]
        assert "documents_appended" not in end

    def test_running_lines_are_not_verdicts(self, prog):
        prog.stage("E2", "Harvest", "running", planned_requests=24)
        prog.done("stopped", "stopped by request")
        assert "harvest_arms" not in _end(prog)


def test_threads_read_sits_beside_threads_sent():
    import inspect

    src = inspect.getsource(fm)
    block = src[src.index("prog.record_summary(\n        llm=extractor_model(),"):][:400]
    assert "sent_threads=len(threads)," in block and "threads_read=len(results)," in block


class TestTheClosingBoxReadsThem:
    """Rule 9: the fields have a reader today, not only the selector they are
    for. The console's closing box is the one a person running a fetch sees."""

    def _box(self, **end):
        from judge import fetch_console

        lines = fetch_console.render({"kind": "end", "status": "ok", **end},
                                     model_version_id="mv_1")
        return "\n".join(lines)

    def test_a_dry_and_a_broken_harvest_render_differently(self):
        dry = self._box(harvest_arms=["E2"], harvest_arms_errored=[], documents_appended=0)
        broken = self._box(harvest_arms=["E2"], harvest_arms_errored=["E2"],
                           documents_appended=0, harvest_http_errors=24)
        assert "0 document(s) appended" in dry and "ERRORED" not in dry
        assert "ERRORED: E2" in broken and "24 HTTP error(s)" in broken

    def test_a_missing_count_is_said(self):
        assert "no arm reported a document count" in self._box(harvest_arms=["E2B"])

    def test_threads_read_beside_threads_sent(self):
        assert "12 came back" in self._box(sent_threads=14, threads_read=12)
