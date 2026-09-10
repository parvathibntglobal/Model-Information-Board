"""The board's open vocabulary must not be gated behind the closed twelve.

WHAT HAPPENED ON 2026-09-10. A real fetch harvested 200 documents, triaged 86
through, sent 14 threads to the classifier — and stored NOTHING. E5 died on

    insert or update on table "claim" violates foreign key constraint
    "claim_capability_key_fkey"

`claim.capability_key` was `NOT NULL REFERENCES capability(key)` — the ratified
twelve — and `judge/pipeline.py` built board rows inside the claim-write loop.
So every discovered section in the batch was lost to one FK violation on a
column the board does not even read.

The twelve cannot express the board. Of the eight capability sections on the
reference board the classifier is calibrated against, SIX have no ratified key:
function-calling, agentic-tool-use, long-context, instruction-following, vision,
multimodal. `judge/extract/prompt.py` says so itself — restricting the
classifier to that list "would have dropped a third of the board, or forced
those quotes into the nearest ratified key, which manufactures agreement about
something nobody said."

These tests are over the seams, not the database: what the writer does with a
key it does not recognise, and what the pipeline does when a claim will not
write.
"""

from __future__ import annotations

import pathlib

import pytest


class TestAnUnratifiedKeyRecordsAsNone:
    """Nullability alone does not fix the FK — a bad non-null key still violates it."""

    @staticmethod
    def _writer():
        from judge.store.claims import ClaimStore

        return ClaimStore.__new__(ClaimStore)   # no connection needed for this helper

    def test_a_ratified_key_is_kept(self):
        from judge.config import capabilities

        key = next(iter(capabilities()))
        assert self._writer()._ratified_or_none(key) == key

    def test_a_key_outside_the_vocabulary_becomes_none(self):
        # `vision` is a real section on the reference board and is NOT one of
        # the twelve. Before this it was an FK violation that ended the run.
        assert self._writer()._ratified_or_none("vision") is None
        assert self._writer()._ratified_or_none("multimodal") is None
        assert self._writer()._ratified_or_none("function-calling") is None

    def test_an_absent_key_is_none_rather_than_empty_string(self):
        assert self._writer()._ratified_or_none(None) is None
        assert self._writer()._ratified_or_none("") is None

    def test_the_vocabulary_is_read_from_the_contract_not_the_database(self):
        # An unloaded `capability` table is an empty table. Coercing every key
        # to NULL because nobody ran the loader would hide a setup mistake as a
        # modelling outcome, so the check reads contract/capabilities.yaml.
        import inspect

        from judge.store.claims import ClaimStore

        src = inspect.getsource(ClaimStore._ratified_or_none)
        assert "from judge.config import capabilities" in src


class TestTheSchemaLetsTheBoardStandAlone:
    """Read from the contract files, so no database is needed."""

    @staticmethod
    def _tables() -> str:
        return pathlib.Path("contract/tables.sql").read_text(encoding="utf-8")

    def test_capability_key_is_nullable(self):
        sql = self._tables()
        assert "capability_key        text REFERENCES capability(key)," in sql
        assert "capability_key        text NOT NULL REFERENCES capability(key)" not in sql

    def test_the_foreign_key_survives(self):
        # Not dropped: a claim that genuinely IS about `format.structured_output`
        # still references the row and still prices a cell. Only the compulsion
        # is gone.
        assert "REFERENCES capability(key)" in self._tables()

    def test_board_entry_claim_id_is_nullable(self):
        # The table was BUILT for an entry that stands alone. The pipeline was
        # what tied it to a claim, not the schema.
        sql = self._tables()
        assert "claim_id          text REFERENCES claim(id)," in sql

    def test_the_migration_exists_and_explains_itself(self):
        m = pathlib.Path(
            "contract/migrations/20260910T1300_claim_capability_key_nullable.sql"
        )
        assert m.exists()
        body = m.read_text(encoding="utf-8")
        assert "DROP NOT NULL" in body
        # A migration that changes a constraint has to say what it unblocks,
        # or the next reader restores it.
        assert "board" in body.lower() and "discover" in body.lower()


class TestAFailedClaimCostsACellNotTheBoard:
    def test_the_claim_write_is_wrapped_in_a_savepoint(self):
        # A try/except ALONE IS NOT ENOUGH. A failed INSERT aborts the whole
        # transaction in Postgres, so every later statement — including the
        # board_entry insert this protects — fails with InFailedSqlTransaction.
        # Without a savepoint the fix just moves the failure one statement later.
        src = pathlib.Path("judge/pipeline.py").read_text(encoding="utf-8")
        assert "with self._conn.transaction():" in src
        assert "self._claims.write(stored)" in src

    def test_board_rows_are_built_after_the_claim_write_not_inside_it(self):
        src = pathlib.Path("judge/pipeline.py").read_text(encoding="utf-8")
        write = src.index("with self._conn.transaction():")
        rows = src.index("for _entry in claim.board_entries:")
        assert rows > write, "board rows must come after the guarded write"
        # And they must not read the tail of the id list, which is the LAST id
        # any iteration wrote — a quote whose own claim failed would have
        # attached the previous quote's claim id and mis-attributed the evidence.
        assert "result.stored_claim_ids[-1]" not in src

    def test_a_claim_failure_is_reported_rather_than_swallowed(self):
        from judge.pipeline import PipelineResult

        r = PipelineResult.__new__(PipelineResult)
        assert "claim_write_failures" in PipelineResult.__dataclass_fields__, (
            "a claim lost to a schema constraint is a finding about our own "
            "machinery; swallowing it is the caused-absence rule 4 forbids"
        )
        del r

    def test_the_claim_id_is_captured_per_iteration(self):
        src = pathlib.Path("judge/pipeline.py").read_text(encoding="utf-8")
        assert '"claim_id": _claim_id,' in src


@pytest.mark.parametrize(
    "slug",
    ["function-calling", "agentic-tool-use", "long-context",
     "instruction-following", "vision", "multimodal"],
)
def test_the_reference_board_sections_the_twelve_cannot_express(slug):
    """The measurement behind the migration, kept as a test.

    Six of the eight capability sections on the reference board have no ratified
    key. If somebody adds one to `capabilities.yaml`, this fails and they can
    delete the line — which is the point: the claim is checkable.
    """
    import yaml

    from judge.config import capabilities

    board = yaml.safe_load(
        pathlib.Path("contract/board_surfaces.yaml").read_text(encoding="utf-8")
    )
    exemplars = {e["slug"] for e in (board.get("capabilities") or {}).get("exemplars", [])}
    assert slug in exemplars, f"{slug} is no longer a reference-board section"

    ratified = set(capabilities())
    tails = {k.split(".")[-1].replace("_", "-") for k in ratified}
    assert slug not in ratified and slug not in tails, (
        f"{slug} now HAS a ratified key — delete it from this list"
    )
