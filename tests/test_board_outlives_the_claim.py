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


class TestTheClosedVocabularyIsInTheSchemaNotOnlyThePrompt:
    """2026-09-14. `vision` reached `claim.capability` and ended a second run.

    The 09-10 fix above made the FK survivable. It did not stop the key
    ARRIVING, because `capability` is a bare `str` in the pydantic model and the
    closure was one line of system prompt - "CLOSED, use these and no others".
    An instruction a model may decline is not a constraint, and it declined.
    """

    @staticmethod
    def _schema(keys=None):
        from judge.extract.client import tool_schema_for
        from judge.extract.schema import ExtractionResult

        if keys is None:
            from judge.config import capabilities

            keys = list(capabilities())
        return tool_schema_for(ExtractionResult, capability_keys=keys)

    def test_the_capability_field_carries_the_ratified_keys_as_an_enum(self):
        from judge.config import capabilities

        node = self._schema()["properties"]["claims"]["items"]["properties"]["legacy_score_key"]
        assert node.get("enum") == list(capabilities()), (
            "the closed vocabulary must reach the provider as an enum, not only "
            "as prose in the system prompt"
        )

    def test_an_unratified_key_is_not_in_the_enum(self):
        node = self._schema()["properties"]["claims"]["items"]["properties"]["legacy_score_key"]
        for slug in ("vision", "multimodal", "long-context"):
            assert slug not in node["enum"]

    def test_the_extractor_passes_the_same_list_to_prompt_and_schema(self):
        # One list, two consumers. Passing the vocabulary to `build_system_prompt`
        # and NOT to the schema is the defect this closes, and it reads as fixed
        # from either call site alone.
        src = pathlib.Path("judge/extract/runner.py").read_text(encoding="utf-8")
        assert "build_system_prompt(capability_keys)" in src
        assert "tool_schema_for(ExtractionResult, capability_keys=capability_keys)" in src

    def test_a_moved_schema_shape_refuses_rather_than_silently_not_closing(self):
        # The injection walks to a known path. If the model changes shape, an
        # unclosed schema that LOOKS closed is worse than no change at all.
        from judge.extract.client import _close_capability

        with pytest.raises(ValueError, match=r"exactly one string .*`legacy_score_key`"):
            _close_capability({"properties": {}}, ["a.b"])

    def test_the_field_is_optional_and_the_schema_says_so(self):
        """2026-09-22. The prompt tells the model to leave this empty.

        A `required` still naming it would make the schema contradict the
        prompt, and the model would resolve that by inventing a value - which
        is the whole defect being fixed. The closure was prose until
        2026-09-14 and cost two runs; optionality must not be prose either.
        """
        items = self._schema()["properties"]["claims"]["items"]
        assert "legacy_score_key" not in items.get("required", [])
        # Flattened rather than left as pydantic's anyOf(string, null): a
        # construct some backends validate and others ignore presents as an
        # intermittent provider outage, which is what `prefixItems` taught.
        node = items["properties"]["legacy_score_key"]
        assert node.get("type") == "string" and "anyOf" not in node

    def test_a_required_key_refuses_rather_than_contradicting_the_prompt(self):
        from judge.extract.client import _close_capability

        schema = {
            "properties": {"claims": {"items": {
                "properties": {"legacy_score_key": {"type": "string"}},
                "required": ["legacy_score_key"],
            }}}
        }
        with pytest.raises(ValueError, match="the prompt tells the model to omit"):
            _close_capability(schema, ["a.b"])

    def test_an_empty_vocabulary_is_refused(self):
        from judge.extract.client import _close_capability

        with pytest.raises(ValueError, match="no capability keys"):
            _close_capability({"properties": {}}, [])


class TestAnUnratifiedKeyCostsOneCellNotTheBatch:
    """The second half: the enum prevents it, this makes it survivable.

    Both sites that read the legacy closed key raise on one they do not know,
    and before 2026-09-14 neither was guarded - so one non-compliant claim took
    every remaining claim AND every remaining board entry in the thread.
    """

    def test_both_readers_of_the_closed_key_still_raise(self):
        """The guard is needed because these two genuinely refuse. Not a mock."""
        from judge.config import bucket_for

        with pytest.raises(KeyError):
            bucket_for("vision", {})

        src = pathlib.Path("judge/vet/weight.py").read_text(encoding="utf-8")
        assert "unknown capability" in src, "compute() still asserts the vocabulary"

    def test_the_cell_half_is_guarded_as_one_region(self):
        # Wrapping `compute()` alone would leave `bucket_for` - called inside the
        # StoredClaim construction - to raise KeyError two statements later.
        src = pathlib.Path("judge/pipeline.py").read_text(encoding="utf-8")
        guard = src.index("stored: StoredClaim | None = None")
        compute_at = src.index("weights = compute(")
        bucket_at = src.index("condition_bucket=bucket_for(")
        handler = src.index("except (ValueError, KeyError, LookupError) as exc:")
        assert guard < compute_at < bucket_at < handler, (
            "compute() and bucket_for() must be inside ONE guarded region; "
            "guarding only the first leaves the second to end the batch"
        )

    def test_the_guard_does_not_skip_the_board(self):
        # `continue` here would reintroduce 2026-09-10 in a new place: the cell
        # is lost AND the board entry with it. Control must fall through.
        src = pathlib.Path("judge/pipeline.py").read_text(encoding="utf-8")
        handler = src.index("except (ValueError, KeyError, LookupError) as exc:")
        board = src.index("for _entry in claim.board_entries:")
        between = src[handler:board]
        assert "continue" not in between, (
            "the cell refusal must fall through to the board write, not skip it"
        )

    def test_a_cell_refusal_is_named_not_counted(self):
        from judge.pipeline import PipelineResult

        assert "cell_refusals" in PipelineResult.__dataclass_fields__
        # Three parts: which document, which key, and why. A bare count cannot
        # tell an unratified capability from a missing tier.
        src = pathlib.Path("judge/pipeline.py").read_text(encoding="utf-8")
        assert "result.cell_refusals.append(" in src
        assert "claim.legacy_score_key," in src[src.index("result.cell_refusals.append("):][:400]

    def test_a_refusal_is_not_double_counted_in_both_tallies(self):
        # One loss in two denominators is how a denominator stops meaning
        # anything. `_CellRefused` leaves through its own handler.
        src = pathlib.Path("judge/pipeline.py").read_text(encoding="utf-8")
        assert "except _CellRefused:" in src
        block = src[src.index("except _CellRefused:"):]
        block = block[:block.index("except Exception as exc:")]
        # The CALL, not the word - the handler's comment names the other tally
        # to explain why it is not used, and matching prose would fail on that.
        assert "result.claim_write_failures.append(" not in block


class TestAnEmptyKeyKeepsTheClaim:
    """2026-09-22. `legacy_score_key` became optional, and that alone would
    have silently deleted most of the corpus.

    The extractor used to be told to "pick the closest key", and did: measured
    over 1,385 stored claims, a 60-claim read found the chosen key did not name
    what the quote described in 38 of them
    (`docs/measurements/the-key-that-takes-anything-2026-09-22.md`). Making the
    field optional is the fix. But BOTH readers of the key refuse an absent one
    - `compute()` with a ValueError, `bucket_for()` with a KeyError - and the
    handler around them sets the claim aside, which writes no claim row at all.

    So "the extractor may say it does not know" would have become "the pipeline
    discards every claim it does not know": rule 4 at the worst possible stage,
    in the table every count comes from, looking exactly like an absence we
    found rather than one we caused. These pin the branch that prevents it.
    """

    def test_the_field_is_optional_on_the_model(self):
        from judge.extract.schema import ExtractedClaim

        field = ExtractedClaim.model_fields["legacy_score_key"]
        assert not field.is_required()
        assert field.default is None

    def test_an_empty_key_takes_the_keep_the_claim_branch(self):
        src = pathlib.Path("judge/pipeline.py").read_text(encoding="utf-8")
        assert "if claim.legacy_score_key is None:" in src
        branch = src[src.index("if claim.legacy_score_key is None:"):]
        branch = branch[:branch.index("            else:")]
        # A StoredClaim is still built, so the claim row is still written.
        assert "stored = StoredClaim(" in branch
        assert "weights=None," in branch
        # And it never reaches the two readers that refuse an absent key.
        assert "compute(" not in branch and "bucket_for(" not in branch

    def test_no_weight_rather_than_a_defaulted_one(self):
        """Rule 6. `half_life_for` returns the SLOW default for an unknown key -
        the most generous decay there is - so a defaulted weight would hand the
        claims we know least about the gentlest treatment, via a fallback that
        cannot fail (rule 12). No cell means nothing to rank within.
        """
        from judge.store.claims import StoredClaim

        assert StoredClaim.__dataclass_fields__["weights"].type == "WeightFactors | None"
        src = pathlib.Path("judge/store/claims.py").read_text(encoding="utf-8")
        assert "if stored.weights is None:" in src
        # The early return must come BEFORE the claim_weight insert and AFTER
        # the claim insert, or the claim is lost again.
        assert src.index("INSERT INTO claim (") < src.index("if stored.weights is None:")
        assert src.index("if stored.weights is None:") < src.index("INSERT INTO claim_weight (")

    def test_an_unweighted_claim_cannot_become_a_voice(self):
        """The other end: `n_eff` turns the gate, so a weightless claim must be
        excluded rather than counted at zero. Two independent guards.
        """
        src = pathlib.Path("judge/store/cells.py").read_text(encoding="utf-8")
        agg = src[src.index("FROM claim c"):src.index("FROM claim c") + 600]
        assert "JOIN claim_weight w ON w.claim_id = c.id" in agg
        assert "LEFT JOIN claim_weight" not in agg
        # And the cell key itself cannot be NULL, so a keyless claim is not
        # merely unweighted - it belongs to no cell at all.
        assert "c.capability_key = %s" in agg

    def test_the_skip_is_counted_apart_from_a_refusal(self):
        """They argue opposite things. `cell_refusals` rising means our
        vocabulary could not resolve a key the extractor supplied; this rising
        means the extractor honestly reported that no key applies. One number
        for both would climb when the pipeline breaks AND when it starts
        telling the truth.
        """
        from judge.pipeline import PipelineResult

        assert "cell_skipped_no_key" in PipelineResult.__dataclass_fields__
        assert PipelineResult.__dataclass_fields__["cell_skipped_no_key"].default == 0
        src = pathlib.Path("judge/pipeline.py").read_text(encoding="utf-8")
        skip = src.index("result.cell_skipped_no_key += 1")
        block = src[skip:skip + 400]
        assert "result.cell_refusals.append(" not in block

    def test_the_bucket_names_the_absence_rather_than_borrowing_a_dimension(self):
        """`condition_bucket` is NOT NULL and reads `<dimension>:<band>` for a
        capability. With no capability there is no dominant dimension, so
        borrowing one would render as a real slice of nothing (rule 6).
        """
        src = pathlib.Path("judge/pipeline.py").read_text(encoding="utf-8")
        assert 'condition_bucket="none:no_ratified_key",' in src

    def test_the_prompt_no_longer_asks_for_the_closest_key(self):
        """The contradiction, as a test. Three instructions mandated picking the
        closest and one forbade it, and the mandating one closed the prompt.
        """
        from judge.config import capabilities
        from judge.extract.prompt import build_system_prompt

        prompt = build_system_prompt(list(capabilities()))
        assert "pick the closest key and move on" not in prompt
        assert "still pick the closest one" not in prompt
        # The prohibition survives, and so does the permission it needed.
        assert "Do not stretch a quote to fit a key." in prompt
        assert "LEAVE IT EMPTY" in prompt

    def test_the_definitions_reach_the_model(self):
        """They never did until 2026-09-22, and it was never intended:
        `capabilities.yaml` carries a description and `sounds_like` for all
        twelve and `build_system_prompt` appended bare keys. Recorded as "the
        single largest confound" in the-vocabulary-hypothesis.md §2.
        """
        from judge.config import capabilities
        from judge.extract.prompt import build_system_prompt

        caps = capabilities()
        prompt = build_system_prompt(list(caps))
        extraction = caps["extraction.faithfulness"]
        # The definition is the thing that excludes reading names off a photo,
        # and the model had never seen it.
        assert "Null discipline" in extraction.description
        assert " ".join(extraction.description.split())[:60] in " ".join(prompt.split())
        assert extraction.sounds_like[0] in prompt

    def test_the_bare_key_prompt_is_still_reproducible(self):
        """Round 3's pool was built against it and its frozen sidecar still
        measures that extractor. A re-run scores against the same gold, so the
        old prompt has to remain constructible or the pair is not a measurement.
        """
        from judge.config import capabilities
        from judge.extract.prompt import build_system_prompt

        bare = build_system_prompt(list(capabilities()), definitions={})
        assert "Null discipline" not in bare
        assert "  - extraction.faithfulness" in bare
