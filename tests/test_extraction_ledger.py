"""The ledger, and the distinction it exists to make.

    row absent          nobody has read this thread   -> a job
    claims_written = 0  read it, found nothing        -> a finding

No database. The interesting behaviour is which threads come back as already
read, and a fake connection answers that as well as Postgres would.
"""

from __future__ import annotations

import pytest

from judge.store.claims import PIPELINE_VERSION
from judge.store.extractions import (
    ExtractionLedger,
    ExtractionRecord,
    fingerprint_of,
)


class Conn:
    """Remembers rows the way the table would, keyed as the primary key is."""

    def __init__(self, rows: dict[tuple[str, str], tuple] | None = None) -> None:
        self.rows = dict(rows or {})
        self.sql: list[str] = []

    def execute(self, sql: str, params: tuple = ()):
        self.sql.append(sql)
        rows = self.rows
        if sql.strip().upper().startswith("INSERT"):
            tc, version, claims, inp, out, retries, fingerprint = params
            rows[(tc, version)] = (claims, inp, out, retries, fingerprint)

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
                return [(tc, v[4]) for tc, v in matching]

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
        assert ExtractionLedger(Conn()).already_extracted() == {}

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

        assert set(ledger.already_extracted(pipeline_version="e5.1")) == {"tc1"}
        assert ledger.already_extracted(pipeline_version="e5.2") == {}

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
        read that produced nothing readable, and the next run would skip it.

        ⚠ MATCHES THE CALL, NOT THE WORD. This read `"commit" not in source` and
          went red the moment `run_all` grew a comment explaining why it does not
          commit — the prose was the match, and the assertion had drifted from
          "this code does not commit" to "nobody may write the word down". That
          is the sixth time a check in this suite has matched a mention rather
          than a use, so: comments are stripped, and the test looks for the CALL.
        """
        import inspect
        import re

        from judge.pipeline import Pipeline

        source = inspect.getsource(Pipeline.run_all)
        code = "\n".join(
            re.sub(r"#.*$", "", line) for line in source.splitlines()
        )
        assert "self._ledger.record(" in code
        assert ".commit(" not in code, (
            "the batch must not commit; the caller owns the transaction. A caller "
            "that wants a commit per thread passes `after_thread`."
        )


class TestTheIdDoesNotIdentifyTheText:
    """E1's finding, and it breaks the skip in the expensive direction.

    `thread_context.id` is stable_id("thread_context", root_id, version) and
    IGNORES CONTENT, so a thread re-assembled with different children keeps its
    id. E1 found it through specificity.py changing the child scorer while
    PIPELINE_VERSION stayed put - the path the "over-identifies, never
    under-identifies" proviso does not cover, because it is about the scorer
    rather than the flattener.
    """

    TEXT = "the flattened text the extractor was given"

    def test_the_same_text_is_skipped(self):
        seen = {"tc1": fingerprint_of(self.TEXT)}
        assert ExtractionLedger.should_skip(seen, "tc1", self.TEXT)

    def test_changed_children_under_a_stable_id_are_RE_READ(self):
        """The case that costs most to get wrong. Skipping it means evidence
        silently never extracted, which is worse than paying twice."""
        seen = {"tc1": fingerprint_of(self.TEXT)}
        assert not ExtractionLedger.should_skip(seen, "tc1", self.TEXT + " plus a reply")

    def test_a_null_fingerprint_is_unknown_rather_than_a_match(self):
        """Rows written before the column existed were not measured at "no
        content" (rule 6). Unknown means re-read."""
        assert not ExtractionLedger.should_skip({"tc1": None}, "tc1", self.TEXT)

    def test_an_absent_thread_is_not_skipped(self):
        assert not ExtractionLedger.should_skip({}, "tc1", self.TEXT)

    def test_the_fingerprint_is_of_the_exact_bytes_given_to_the_extractor(self):
        assert fingerprint_of("a") != fingerprint_of("a ")
        assert fingerprint_of("a") == fingerprint_of("a")

    def test_the_record_carries_it(self):
        conn = Conn()
        ExtractionLedger(conn).record(
            ExtractionRecord("tc1", 1, content_fingerprint=fingerprint_of(self.TEXT))
        )
        assert conn.rows[("tc1", PIPELINE_VERSION)][4] == fingerprint_of(self.TEXT)

    def test_the_pipeline_compares_content_not_only_the_id(self):
        import inspect

        from judge.pipeline import Pipeline

        source = inspect.getsource(Pipeline.run_all)
        assert "should_skip(" in source
        assert "thread.flattened_text" in source
