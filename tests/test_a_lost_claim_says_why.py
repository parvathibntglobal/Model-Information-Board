"""97 claims failed the schema and the log wrote only the number (#409).

MEASURED. ElevenLabs v3, 2026-09-23,
`var/fetch/mv_9a53a616c98d9f6b-54be7210.jsonl`:

    proposed 158 · unsalvaged 97 (61%) · verified 51 · rejected 10

    thread  3   unsalvaged 21   verified 0   retried
    thread  5   unsalvaged 40   verified 0   retried
    thread 13   unsalvaged  3   verified 0   retried
    thread 15   unsalvaged 17   verified 0   retried
    thread 18   unsalvaged 16   verified 0   retried

`Unsalvaged` carries `errors` and `raw`. Neither was written down —
`scripts/fetch_model.py` recorded `len(run.unsalvaged)` and nothing else, and
this machine's `backend.log` was a fortnight stale, so the `log.info` lines were
gone too. Ninety-seven claims died and the only surviving fact was the number.

⚠ THE TWO CASES THAT WANT OPPOSITE FIXES PRINT THE SAME LINE.

    40 claims lost to ONE repeated error      -> a prompt or schema change
    40 claims lost to FORTY different errors  -> possibly a retry, possibly a
                                                 different model

    Both render as `40 unsalvaged`.

THREE CONSTRAINTS, agreed with @anoojntglobal-sudo on #409 before this was
built, and each is a test below:

  1  SHAPES, NOT INSTANCES. `board_entries.3.slug` and `board_entries.7.slug`
     are one defect. Counting instances answers "how many times did something
     fail" when the question is "how many things are wrong".
  2  COUNTS, NEVER THE CLAIM TEXT. `raw` holds the model's dict, quote
     included. A quote is a passage from a harvested document with no ruling
     and no attribution at that point, and the terminal is the one surface here
     with no quote-plus-attribution contract on it.
  3  A CAP THAT SAYS WHEN IT BINDS. A truncated list with nothing marking the
     truncation reads as a complete one.

#411 is blocked on this: until the shapes exist, any change to the validation
retry is a gate tuned before its error rate was measured.
"""

from __future__ import annotations

import pathlib

from judge.extract.runner import (
    UNSALVAGED_SHAPES_SHOWN,
    Unsalvaged,
    _shape_of,
    unsalvaged_shapes,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]


def lost(*errors: str) -> list[Unsalvaged]:
    return [
        Unsalvaged(index=i, errors=(e,), raw={"quote": "a writer's sentence"})
        for i, e in enumerate(errors)
    ]


class TestAShapeIsNotAnInstance:
    def test_a_list_index_is_dropped(self):
        a = _shape_of("board_entries.3.slug: String should have at most 60 characters")
        b = _shape_of("board_entries.7.slug: String should have at most 60 characters")
        assert a == b == "board_entries.slug: String should have at most 60 characters"

    def test_one_defect_repeated_reads_as_one_defect(self):
        """Thread 5's shape: 40 claims, and the question is whether that is one
        problem or forty."""
        shapes, overflow = unsalvaged_shapes(
            lost(*[f"board_entries.{i}.quote_offset.1: Input should be a "
                   "valid integer" for i in range(40)])
        )
        assert shapes == {
            "board_entries.quote_offset: Input should be a valid integer": 40
        }
        assert overflow == 0

    def test_the_numbers_inside_a_message_are_kept(self):
        """⚠ `at most 300 characters` is part of the RULE, not part of the
        instance. Stripping digits from the message would fold two different
        length limits into one shape and lose which constraint fired."""
        a = _shape_of("quote: String should have at most 300 characters")
        b = _shape_of("quote: String should have at most 60 characters")
        assert a != b

    def test_an_error_with_no_location_survives(self):
        assert _shape_of("claim was not an object") == "claim was not an object"


class TestItCarriesCountsAndNeverAQuote:
    def test_the_writers_words_do_not_reach_the_record(self):
        """Constraint 2. `raw` is right there on every item and must not leak:
        the terminal has no ruling, no attribution and no way to decline."""
        shapes, _ = unsalvaged_shapes(lost("quote: too long", "quote: too long"))
        blob = repr(shapes)
        assert "a writer's sentence" not in blob
        assert shapes == {"quote: too long": 2}

    def test_every_value_is_a_count(self):
        shapes, overflow = unsalvaged_shapes(lost("a: b", "a: b", "c: d"))
        assert all(isinstance(v, int) for v in shapes.values())
        assert isinstance(overflow, int)


class TestTheCapSaysWhenItBinds:
    def test_a_long_tail_is_capped_and_the_remainder_counted(self):
        shapes, overflow = unsalvaged_shapes(
            lost(*[f"field{i}: message {i}" for i in range(8)])
        )
        assert len(shapes) == UNSALVAGED_SHAPES_SHOWN
        assert overflow == 3, "the three that did not fit must still be counted"

    def test_nothing_overflows_when_everything_fits(self):
        shapes, overflow = unsalvaged_shapes(lost("a: b", "c: d"))
        assert overflow == 0
        assert len(shapes) == 2

    def test_the_commonest_shapes_are_the_ones_kept(self):
        """A cap that kept an arbitrary five would hide the repeated defect,
        which is the single thing this field exists to surface."""
        items = lost(*(["big: one"] * 9 + [f"small{i}: x" for i in range(9)]))
        shapes, _ = unsalvaged_shapes(items)
        assert shapes["big: one"] == 9


class TestItReachesTheRecordAndTheTerminal:
    def test_the_thread_record_carries_the_shapes(self):
        src = (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
        assert "_unsalvaged_shapes(run.unsalvaged)" in src

    def test_a_healthy_thread_carries_no_empty_key(self):
        """`unsalvaged_by_error: {}` on eighteen healthy lines would bury the
        two that matter."""
        src = (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
        body = src[src.index("def _unsalvaged_shapes"):]
        body = body[:body.index("def _on_result")]
        assert "if not lost:" in body
        assert "return {}" in body

    def test_the_terminal_prints_a_shape_per_line_with_its_count(self):
        from judge import fetch_console

        out = "\n".join(fetch_console.render({
            "kind": "thread", "index": 5, "total": 20,
            "thread_context_id": "thread_context_abc", "posts": 1,
            "verified": 0, "unsalvaged": 40,
            "unsalvaged_by_error": {"board_entries.quote_offset: not an integer": 38},
            "unsalvaged_other": 3,
        }, model_version_id="mv_x"))
        assert "x38" in out
        assert "board_entries.quote_offset: not an integer" in out
        assert "+3 more in other shapes" in out

    def test_the_terminal_says_nothing_when_nothing_was_lost(self):
        from judge import fetch_console

        out = "\n".join(fetch_console.render({
            "kind": "thread", "index": 1, "total": 20,
            "thread_context_id": "thread_context_abc", "posts": 1,
            "verified": 11, "unsalvaged": 0,
        }, model_version_id="mv_x"))
        assert "more in other shapes" not in out
