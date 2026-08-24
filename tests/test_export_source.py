"""Threads loaded from an export, and the three defects that only running found.

`judge/extract/export_source.py` was written, read, linted and reviewed, and
then failed three times in a row against a real database - each failure after
the point where a live run would already have paid for the model call:

    1. `offset_map` handed over as raw dicts. `verify()` calls
       `.overlaps(start, end)` on each entry, so step 2 raised AttributeError
       mid-run. `ThreadInput` annotates `tuple[OffsetMapping, ...]` and nothing
       enforced it; the existing test built proper objects, so it passed while
       this loader did not.
    2. `created_at` absent, so `recency_factor` subtracted a date from None.
    3. the run summary read `extraction.claims`, which does not exist.

All three are the same shape: a value the caller supplies is a value the caller
cannot check. These tests fix the boundary rather than the symptoms, so the next
loader cannot hand over an untyped map.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from judge.extract import export_source
from judge.extract.verify import OffsetMapping

#: The real shape, taken from `_handoff/threads/*.json` rather than invented.
#: My first version added an `author_id` that `OffsetMapping` does not have, and
#: every test in this file failed on my own fixture while the code was right -
#: which is the same defect as the one below, pointed at the test.
SPAN = {
    "flat_start": 0,
    "flat_end": 12,
    "document_id": "reddit:t1_abc",
    "raw_start": 0,
    "raw_end": 12,
}


def write(directory: Path, name: str, payload: dict) -> None:
    (directory / name).write_text(json.dumps(payload), encoding="utf-8")


def good(**overrides) -> dict:
    payload = {
        "thread_context_id": "tc_1",
        "member_document_ids": ["reddit:t1_abc"],
        "flattened_text": "hello there, world",
        "offset_map": [SPAN],
        "raw_text_of": {"reddit:t1_abc": "hello there, world"},
    }
    payload.update(overrides)
    return payload


class TestTheOffsetMapIsTypedNotDicts:
    """DEFECT 1, and the one that cost a run.

    A live extraction would have paid for the model call, verified the quote,
    and then raised inside step 2 on `dict.overlaps`.
    """

    def test_spans_come_back_as_OffsetMapping(self, tmp_path):
        write(tmp_path, "a.json", good())
        loaded = export_source.load(tmp_path)

        assert len(loaded.threads) == 1
        spans = loaded.threads[0].offset_map
        assert spans and all(isinstance(s, OffsetMapping) for s in spans), (
            "raw dicts reach verify() and raise AttributeError on .overlaps"
        )

    def test_the_thing_verify_actually_calls_works(self, tmp_path):
        """Asserting the type is weaker than asserting the behaviour it exists for."""
        write(tmp_path, "a.json", good())
        span = export_source.load(tmp_path).threads[0].offset_map[0]

        assert span.overlaps(0, 5) is True
        assert span.overlaps(50, 60) is False

    def test_a_malformed_span_skips_the_thread_rather_than_loading_it(self, tmp_path):
        """A span missing a field would raise later, further from the cause."""
        write(tmp_path, "a.json", good(offset_map=[{"nonsense": 1}]))
        loaded = export_source.load(tmp_path)

        assert loaded.threads == []
        assert "OffsetMapping" in loaded.skipped[0][1]


class TestAMissingInputIsNotAnEmptyThread:
    """The distinction `claims_written = 0` versus no row at all, one layer up.

    An empty flattened text extracts to nothing, which is indistinguishable from
    a thread that genuinely says nothing - and one is a broken input while the
    other is a finding.
    """

    @pytest.mark.parametrize(
        "payload,expected",
        [
            (good(flattened_text=""), "no flattened_text"),
            (good(flattened_text="   "), "no flattened_text"),
            (good(raw_text_of={}), "no raw_text_of"),
            (good(thread_context_id=""), "no thread_context_id"),
        ],
    )
    def test_it_is_skipped_and_named(self, tmp_path, payload, expected):
        write(tmp_path, "a.json", payload)
        loaded = export_source.load(tmp_path)

        assert loaded.threads == []
        assert len(loaded.skipped) == 1
        assert expected in loaded.skipped[0][1]

    def test_no_raw_text_means_a_quote_could_verify_and_never_render(self, tmp_path):
        """Step 3 renders the RAW span. Without it the claim passes verification
        and cannot be displayed, which is worse than being skipped."""
        write(tmp_path, "a.json", good(raw_text_of={}))
        assert "never displayed" in export_source.load(tmp_path).skipped[0][1]

    def test_unreadable_json_is_skipped_not_fatal(self, tmp_path):
        (tmp_path / "a.json").write_text("{not json", encoding="utf-8")
        loaded = export_source.load(tmp_path)

        assert loaded.threads == []
        assert "unreadable" in loaded.skipped[0][1]


class TestTheDenominatorTravels:
    def test_document_ids_are_collected_for_the_caller(self, tmp_path):
        """The caller builds `DocumentFacts` from these, so deriving them here
        keeps the two in step rather than having each side guess."""
        write(tmp_path, "a.json", good())
        write(tmp_path, "b.json", good(thread_context_id="tc_2",
                                       member_document_ids=["reddit:t1_def"]))
        loaded = export_source.load(tmp_path)

        assert loaded.document_ids == {"reddit:t1_abc", "reddit:t1_def"}

    def test_a_partial_load_reports_both_halves(self, tmp_path):
        """A run over 1 of 2 threads that says "2" is a yield with the wrong
        denominator, so `skipped` is returned rather than counted."""
        write(tmp_path, "ok.json", good())
        write(tmp_path, "bad.json", good(thread_context_id="tc_2", flattened_text=""))
        loaded = export_source.load(tmp_path)

        assert len(loaded.threads) == 1
        assert len(loaded.skipped) == 1

    def test_a_missing_directory_refuses_rather_than_returning_nothing(self, tmp_path):
        """Empty and absent are different, and an empty load reads as "nothing
        to extract" rather than "you pointed at the wrong path"."""
        with pytest.raises(SystemExit, match="not a directory"):
            export_source.load(tmp_path / "does-not-exist")


class TestItLoadsTheRealExport:
    """Against `_handoff/`, because a fixture I wrote proves only that I am
    consistent with myself - and defect 1 survived exactly that."""

    def test_the_handoff_export_loads_with_typed_spans(self):
        directory = Path("_handoff/threads")
        if not directory.is_dir():
            pytest.skip("_handoff/ is not present in this checkout")

        loaded = export_source.load(directory)

        assert loaded.threads, "the real export must load"
        assert loaded.skipped == []
        assert len(loaded.document_ids) == 7, "1 + 6 documents across two threads"
        for thread in loaded.threads:
            assert thread.flattened_text.strip()
            assert all(isinstance(s, OffsetMapping) for s in thread.offset_map)
