"""The admin pipeline panel: counts per stage, and the run ledger.

Stub connection, no DB — the point of these tests is the RULES the panel has to
keep, and every one of them is visible on an EMPTY database, which is the state
the panel spends its first weeks in:

- rule 4: an empty stage is NOT-YET-RUN (`measured is False`), never a clean zero.
- rule 6: NULL is its own bucket, and `job_run` unreadable is not `job_run` empty.
- rule 3/7: every bucket is a count carrying its stage total; nothing synthesised.
"""

from __future__ import annotations

from judge.pages.pipeline_status import PipelineStatus


class _R:
    def __init__(self, one=None, all_=None):
        self._one, self._all = one, all_

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all or []


class EmptyConn:
    """Every count returns zeros; `job_run` returns no rows (table present, empty)."""

    def execute(self, sql):
        s = sql.lower()
        if "distinct on (stage)" in s:
            return _R(all_=[])
        if "from job_run" in s:
            return _R(one=None)
        return _R(one=(0, 0, 0, 0, 0))


class PopulatedConn:
    def execute(self, sql):
        s = sql.lower()
        if "distinct on (stage)" in s:
            return _R(all_=[
                ("harvest", "2026-08-24 03:00", "2026-08-24 03:12", "ok", 120, 120),
                ("extract", "2026-08-24 03:15", None, None, 90, None),   # running/killed
                ("curate", "2026-08-24 02:00", "2026-08-24 02:01", "refused", None, None),
            ])
        if "from job_run order by started_at desc limit 1" in s:
            return _R(one=("pv-test",))
        if "from model_version" in s and "in_window" in s:
            return _R(one=(10, 8, 2, 3, 7))
        if "from document" in s and "retrieval_provenance" in s:
            return _R(one=(120, 100, 15, 5))
        if "from thread_context" in s and "observed_children" in s:
            return _R(one=(90, 60, 30))
        if "from document" in s and "'kept'" in s:
            return _R(one=(120, 90, 20, 10, 0))
        if "from thread_context)," in s:  # E5 multi-subselect
            return _R(one=(90, 70, 55, 15, 210))
        if "(select count(*) from claim)," in s:  # E6
            return _R(one=(210, 180))
        if "from cell" in s:
            return _R(one=(40, 25, 5, 10))
        if "from label_change" in s:
            return _R(one=(12, 9, 3))
        if "from model_version" in s and "last_swept_at" in s:
            return _R(one=(10, 6, 1, 3))
        return _R(one=(0, 0, 0, 0, 0))


class OneStageUnreadableConn(PopulatedConn):
    """Triage's query raises; the panel must degrade THAT stage, not the page."""

    def execute(self, sql):
        if "from document" in sql.lower() and "'kept'" in sql.lower():
            raise RuntimeError("column document.status does not exist")
        return super().execute(sql)


class TestEmptyDatabaseNeverReadsAsAllClear:
    def test_every_stage_is_not_yet_run(self):
        rep = PipelineStatus(EmptyConn()).report()
        assert len(rep.stages) == 9
        assert all(s.measured is False for s in rep.stages)
        # rule 4 in the summary: it names "has not run", not "0 problems".
        assert "has not run" in rep.summary.lower()

    def test_an_empty_stage_carries_no_caveat(self):
        # The discard caveat is true but noise on a stage with nothing in it.
        rep = PipelineStatus(EmptyConn()).report()
        assert all(s.caveat is None for s in rep.stages)

    def test_empty_job_run_is_measured_but_carries_no_rows(self):
        # "the ledger is there and nothing ran" — distinct from unreadable.
        rep = PipelineStatus(EmptyConn()).report()
        assert rep.runs_measured is True
        assert rep.runs == ()


class TestPopulatedCountsArePartitions:
    def test_triage_buckets_sum_to_the_document_total(self):
        rep = PipelineStatus(PopulatedConn()).report()
        e4 = next(s for s in rep.stages if s.id == "E4")
        assert e4.total == 120
        assert sum(b.n for b in e4.buckets) == e4.total

    def test_summary_carries_its_denominators(self):
        rep = PipelineStatus(PopulatedConn()).report()
        assert "120 documents harvested" in rep.summary
        assert "90 survived triage" in rep.summary
        assert "25 cells published" in rep.summary

    def test_never_swept_is_its_own_bucket_not_folded_into_zero(self):
        rep = PipelineStatus(PopulatedConn()).report()
        e9 = next(s for s in rep.stages if s.id == "E9")
        never = next(b for b in e9.buckets if b.key == "never")
        assert never.n == 3  # rule 6: NULL last_swept_at counted, not dropped

    def test_extract_reports_claims_written_in_its_caveat(self):
        rep = PipelineStatus(PopulatedConn()).report()
        e5 = next(s for s in rep.stages if s.id == "E5")
        assert "210 claims written" in e5.caveat
        # and it must SAY it cannot count its own discards, not imply zero.
        assert "cannot count" in e5.caveat


class TestTheRunLedgerKeepsRunningApartFromFailed:
    def test_a_finished_ok_run_is_not_running(self):
        rep = PipelineStatus(PopulatedConn()).report()
        harvest = next(r for r in rep.runs if r.stage == "harvest")
        assert harvest.running is False
        assert harvest.outcome == "ok"

    def test_an_unfinished_run_is_running_not_a_failure(self):
        # rule 6 at the ops layer: finished_at NULL + outcome NULL = running/killed,
        # which must NOT be read as an error.
        rep = PipelineStatus(PopulatedConn()).report()
        extract = next(r for r in rep.runs if r.stage == "extract")
        assert extract.running is True
        assert extract.outcome is None

    def test_refused_is_recorded_as_its_own_outcome(self):
        rep = PipelineStatus(PopulatedConn()).report()
        curate = next(r for r in rep.runs if r.stage == "curate")
        assert curate.running is False
        assert curate.outcome == "refused"


class TestOneUnreadableStageDoesNotBlankThePage:
    def test_the_bad_stage_is_flagged_and_the_rest_still_count(self):
        rep = PipelineStatus(OneStageUnreadableConn()).report()
        e4 = next(s for s in rep.stages if s.id == "E4")
        assert e4.unreadable is not None
        assert e4.measured is False
        # a sibling stage still reports its counts.
        e2 = next(s for s in rep.stages if s.id == "E2")
        assert e2.measured is True and e2.total == 120
