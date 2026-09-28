"""#444: E5 reported claims "stored" that the table never received.

Measured by @anoojntglobal-sudo across today's batch (#432), against `claim`
counts taken by the batch driver immediately before and after each run:

    run  model             E5 "stored"   claim delta   gap
    1    Sonnet 5              154          +100        54   35%
    3    Sonnet 4.6            166           +84        82   49%
    4    Gemini 2.5 Flash       89           +50        39   44%

No other machine wrote during any run, and nothing downstream of E5 deletes:
`judge/vet/reject.py` opens *"REJECTED IS NOT DELETED"* and there is no
`DELETE FROM claim` in `judge/vet`, `judge/store` or `judge/pipeline.py`.

⚠ THE COUNTER COUNTS WRITES AND THE TABLE HOLDS ROWS. `stored_claim_ids`
  appends once per upsert, and `claim_id_for` is a content hash of
  `(thread_context_id, source_comment_id, capability_key, quote_flat_offset,
  pipeline_version)` written with `ON CONFLICT ... DO UPDATE`. Two claims
  hashing the same way are two appends and one row.

⚠ AND e5.5 MADE COLLISIONS COMMON RATHER THAN RARE. `capability_key` is empty
  on 306 of 308 e5.5 claims, so two claims on one span that used to differ by
  key now hash identically. Under e5.4 the same gap was measured at 14%
  (#386: 114 written, 98 rows, 16 collided). The counter did not change; the
  id's discriminating input did.

⚠ THE OVERWRITE LOSES A CLAIM, NOT JUST A COUNT. The upsert is
  `DO UPDATE SET quote = EXCLUDED.quote, polarity = …, conditions = …`, so the
  second claim on a span replaces the first one's polarity and conditions, and
  **which one survives depends on extraction order**.

WHAT THIS FIXES AND WHAT IT DOES NOT. The count: a run now says "154 written,
100 stored, 54 merged" rather than "154 stored" about a table that gained 100.
The collision itself is a decision — what distinguishes two claims on one span
once the capability key is gone — and #434 decides whether the key comes back
at all. Reporting it is what makes that decision arguable on a number.
"""

from __future__ import annotations

from judge.pipeline import PipelineResult


class _Extraction:
    proposed = 0
    verified: list = []
    unclassified: list = []
    fabricated = 0
    encoding_mismatches = 0
    schema_retries = 0


def _result(ids):
    r = PipelineResult(extraction=_Extraction())
    r.stored_claim_ids.extend(ids)
    return r


class TestStoredIsRowsAndMergedIsTheDifference:
    def test_distinct_ids_are_the_rows(self):
        assert _result(["a", "b", "c"]).stored_claims == 3

    def test_a_repeated_id_is_one_row(self):
        """⚠ THE DEFECT ITSELF. Two writes, one row — and the old counter said
        two."""
        assert _result(["a", "a"]).stored_claims == 1

    def test_the_merged_count_is_what_the_table_did_not_gain(self):
        assert _result(["a", "a"]).merged_claims == 1
        assert _result(["a", "a", "a", "b"]).merged_claims == 2

    def test_no_collision_reports_zero_merged(self):
        """Zero is a measurement here: every write landed on its own row."""
        assert _result(["a", "b"]).merged_claims == 0

    def test_the_two_always_sum_to_the_writes(self):
        """⚠ THE INVARIANT THAT KEEPS THE THREE NUMBERS HONEST. "154 written,
        100 stored, 54 merged" is only meaningful if the last two account for
        the first — otherwise it is three figures that happen to appear
        together."""
        for ids in (["a"], ["a", "a"], ["a", "b", "a", "c", "c"], []):
            r = _result(ids)
            assert r.stored_claims + r.merged_claims == len(r.stored_claim_ids)

    def test_an_empty_thread_is_zero_and_zero(self):
        r = _result([])
        assert (r.stored_claims, r.merged_claims) == (0, 0)


class TestTheOrderIsKept:
    def test_the_raw_list_is_not_deduplicated_in_place(self):
        """⚠ THE ORDER IS THE EVIDENCE AND A SET WOULD DESTROY IT. Which of two
        colliding claims survives depends on extraction order, so the list
        stays a list — the properties derive the counts without flattening
        what produced them."""
        r = _result(["a", "b", "a"])
        assert r.stored_claim_ids == ["a", "b", "a"]


class TestEveryReporterCountsRows:
    def test_no_summary_still_lengths_the_raw_list(self):
        """⚠ FOUR CALL SITES SUMMED `len(r.stored_claim_ids)` AND ALL FOUR WERE
        WRONG THE SAME WAY — the pipeline's own log line, `judge/cli.py`,
        `scripts/fetch_model.py` and `scripts/count_db_roundtrips.py`. Fixing
        three of four would leave a run whose stage line and closing box
        disagree, which is harder to notice than either being wrong."""
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[1]
        offenders = []
        for rel in ("judge/pipeline.py", "judge/cli.py",
                    "scripts/fetch_model.py", "scripts/count_db_roundtrips.py"):
            text = (root / rel).read_text(encoding="utf-8")
            # ⚠ THE COMMENTS IN ALL FOUR FILES QUOTE THE OLD EXPRESSION while
            #   explaining why it was wrong, so a plain substring search reports
            #   the explanation as the defect. Comment lines are dropped first.
            code = "\n".join(
                ln for ln in text.splitlines() if not ln.strip().startswith(("#", "#:"))
            )
            if "len(r.stored_claim_ids)" in code or "len(result.stored_claim_ids)" in code:
                offenders.append(rel)
        assert not offenders, (
            f"these still count writes rather than rows: {offenders}"
        )

    def test_merged_has_a_reader_in_every_file_that_computes_it(self):
        """Rule 9. A `merged` summed and never printed is the same defect one
        layer along — a produced value nobody would notice going wrong."""
        import pathlib
        import re

        root = pathlib.Path(__file__).resolve().parents[1]
        for rel in ("judge/cli.py", "scripts/fetch_model.py",
                    "scripts/count_db_roundtrips.py"):
            text = (root / rel).read_text(encoding="utf-8")
            assert re.search(r"^\s*merged = sum\(", text, re.M), rel
            uses = len(re.findall(r"(?<![\w.])merged(?![\w(])", text))
            assert uses >= 2, f"{rel} computes `merged` and never reads it"
