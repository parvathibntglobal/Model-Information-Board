"""The ledger, and the distinction it exists to make.

    row absent          nobody has read this thread   -> a job
    claims_written = 0  read it, found nothing        -> a finding

No database. The interesting behaviour is which threads come back as already
read, and a fake connection answers that as well as Postgres would.
"""

from __future__ import annotations

import pytest

from judge.store.claims import PIPELINE_VERSION
from judge.store.extractions import ExtractionLedger, ExtractionRecord


class Conn:
    """Remembers rows the way the table would, keyed as the primary key is."""

    def __init__(self, rows: dict[tuple[str, str], tuple] | None = None) -> None:
        self.rows = dict(rows or {})
        self.sql: list[str] = []

    def execute(self, sql: str, params: tuple = ()):
        self.sql.append(sql)
        rows = self.rows
        if sql.strip().upper().startswith("INSERT"):
            tc, version, claims, inp, out, retries = params
            rows[(tc, version)] = (claims, inp, out, retries)

            class R:
                @staticmethod
                def fetchall():
                    return []

                @staticmethod
                def fetchone():
                    return None

            return R()

        version = params[0]
        matching = [(k[0], v) for k, v in rows.items() if k[1] == version]

        class R:
            @staticmethod
            def fetchall():
                return [(tc,) for tc, _ in matching]

            @staticmethod
            def fetchone():
                if "FILTER (WHERE claims_written = 0)" in sql:
                    return (sum(1 for _, v in matching if v[0] == 0), len(matching))
                return (
                    sum(v[1] or 0 for _, v in matching),
                    sum(v[2] or 0 for _, v in matching),
                    sum(1 for _, v in matching if v[1] is None and v[2] is None),
                )

        return R()


class TestZeroIsAResultNotAnAbsence:
    """The whole reason the table exists.

    `claim` cannot say "we read this and there was nothing in it". Without the
    ledger, a zero-yield thread looks unextracted forever and is re-paid for
    every night - and those are exactly the threads that cost the most and
    return the least.
    """

    def test_a_thread_that_produced_nothing_counts_as_extracted(self):
        conn = Conn()
        ledger = ExtractionLedger(conn)
        ledger.record(ExtractionRecord(thread_context_id="tc1", claims_written=0))

        assert "tc1" in ledger.already_extracted(), (
            "a zero-yield thread reads as unextracted, so it is re-paid for "
            "every night - the defect this table exists to prevent"
        )

    def test_an_unrecorded_thread_is_not_extracted(self):
        assert ExtractionLedger(Conn()).already_extracted() == frozenset()

    def test_a_negative_count_is_refused(self):
        """0 already means "read it, found nothing", so nothing below it is
        meaningful."""
        with pytest.raises(ValueError, match="cannot be negative"):
            ExtractionRecord(thread_context_id="tc1", claims_written=-1)


class TestTheVersionIsPartOfTheKey:
    """A re-extraction under a changed prompt is new work on old text, and must
    not be skipped - the same reason `claim_id` hashes the version."""

    def test_a_version_bump_makes_a_thread_unextracted_again(self):
        conn = Conn()
        ledger = ExtractionLedger(conn)
        ledger.record(ExtractionRecord("tc1", 3), pipeline_version="e5.1")

        assert ledger.already_extracted(pipeline_version="e5.1") == {"tc1"}
        assert ledger.already_extracted(pipeline_version="e5.2") == frozenset()

    def test_the_default_version_is_the_one_claims_are_written_at(self):
        """Two constants disagreeing here would skip threads whose claims were
        never written, which loses evidence silently."""
        conn = Conn()
        ExtractionLedger(conn).record(ExtractionRecord("tc1", 1))
        assert ("tc1", PIPELINE_VERSION) in conn.rows


class TestRerunningReplacesRatherThanAccumulates:
    def test_a_second_read_at_the_same_version_overwrites(self):
        """Summing would invent a thread that produced twice what it did."""
        conn = Conn()
        ledger = ExtractionLedger(conn)
        ledger.record(ExtractionRecord("tc1", claims_written=2))
        ledger.record(ExtractionRecord("tc1", claims_written=5))

        assert conn.rows[("tc1", PIPELINE_VERSION)][0] == 5
        assert len(conn.rows) == 1

    def test_the_write_is_an_upsert_so_a_crashed_rerun_does_not_fail(self):
        conn = Conn()
        ExtractionLedger(conn).record(ExtractionRecord("tc1", 1))
        assert "ON CONFLICT" in conn.sql[0]


class TestTheFiguresCarryTheirPopulation:
    """Rule 7. How much the skip is worth depends entirely on the zero-yield
    rate, and nobody has it until a run happens."""

    def test_yield_rate_returns_a_pair_rather_than_a_percentage(self):
        conn = Conn()
        ledger = ExtractionLedger(conn)
        for i, written in enumerate((0, 0, 3, 0, 7)):
            ledger.record(ExtractionRecord(f"tc{i}", written))

        assert ledger.yield_rate() == (3, 5), (
            "a caller must not be able to quote a rate without its population"
        )

    def test_unmetered_threads_are_counted_so_the_totals_are_known_to_be_a_floor(self):
        """A provider that stops reporting usage makes these totals a floor,
        and the symptom is a low number that reads as good news."""
        conn = Conn()
        ledger = ExtractionLedger(conn)
        ledger.record(ExtractionRecord("tc1", 1, input_tokens=1000, output_tokens=200))
        ledger.record(ExtractionRecord("tc2", 1))

        inp, out, unmetered = ledger.token_totals()
        assert (inp, out) == (1000, 200)
        assert unmetered == 1


class TestThePipelineUsesIt:
    def test_run_all_derives_the_skip_set_rather_than_defaulting_to_none(self):
        """Before the ledger, `already_extracted=None` meant "extract
        everything" because nothing could work the set out. Now it means "ask",
        so the default is the correct answer rather than the safe one."""
        import inspect

        from judge.pipeline import Pipeline

        source = inspect.getsource(Pipeline.run_all)
        assert "self._ledger.already_extracted()" in source
        assert "if already_extracted is None" in source

    def test_the_ledger_row_is_written_beside_the_claims(self):
        """A ledger row surviving a rolled-back extraction would mark a thread
        read that produced nothing readable, and the next run would skip it."""
        import inspect

        from judge.pipeline import Pipeline

        source = inspect.getsource(Pipeline.run_all)
        assert "self._ledger.record(" in source
        assert "commit" not in source, "the batch must not commit; the caller owns that"
