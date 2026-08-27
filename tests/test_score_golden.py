"""The golden-set scorer (#17): the numbers it must get right, and the ones it
must refuse to invent.

No files, no DB — the point is the arithmetic and the honesty rules:
  - kappa corrects for chance, and is None (not 0 or 1) when there is no chance
    floor to correct against;
  - a null from one labeller is EXCLUDED, never counted as a disagreement;
  - the gold is agreed rows plus reconciled rows, keyed by the stable quote, and
    an unsettled disagreement is not gold.
"""

from __future__ import annotations

from scripts.score_golden import (
    answers_of,
    build_round2_gold,
    cohen_kappa,
    extractor_accuracy,
    inter_labeller,
)


class TestCohenKappa:
    def test_perfect_agreement_is_one(self):
        assert cohen_kappa([("a", "a"), ("b", "b"), ("a", "a")]) == 1.0

    def test_one_category_for_everything_is_undefined_not_perfect(self):
        # pe == 1: both raters said "a" for all, so there is no chance floor. That
        # is perfect skew, not a kappa of 1.0 — reported as None and named.
        assert cohen_kappa([("a", "a"), ("a", "a")]) is None

    def test_chance_level_agreement_is_near_zero(self):
        # Two raters each split 50/50 but never actually agree on an item beyond
        # chance -> kappa around 0, and importantly not the flattering raw rate.
        pairs = [("a", "a"), ("a", "b"), ("b", "a"), ("b", "b")]
        k = cohen_kappa(pairs)
        assert k is not None and abs(k) < 1e-9

    def test_empty_is_none_not_zero(self):
        assert cohen_kappa([]) is None


class TestInterLabellerExcludesNulls:
    def _rows(self, *vals):
        return [{"row_index": i, "answers": {"q": v}} for i, v in enumerate(vals)]

    def test_a_null_on_either_side_is_excluded_not_a_miss(self):
        a = self._rows("x", "x", "x")
        b = self._rows("x", None, "y")   # row1 unfinished, row2 real disagreement
        r = inter_labeller(a, b)["q"]
        assert r["n"] == 2                 # row1 excluded
        assert r["skipped_unlabelled"] == 1
        assert r["agree"] == 1             # only row0 agrees; row2 differs
        assert r["agreement"] == 0.5

    def test_only_shared_row_indices_are_compared(self):
        a = [{"row_index": 0, "answers": {"q": "x"}}]
        b = [{"row_index": 9, "answers": {"q": "x"}}]
        assert inter_labeller(a, b)["q"]["n"] == 0


class TestExtractorAccuracy:
    def test_accuracy_and_mismatches(self):
        gold = {0: "code.generation", 1: "reasoning.multistep", 2: None}
        extractor = {0: "code.generation", 1: "code.generation", 2: "over_refusal"}
        acc = extractor_accuracy(gold, extractor)
        assert acc["n"] == 2                    # row2 has no gold, excluded
        assert acc["ungraded_no_gold"] == 1
        assert acc["correct"] == 1
        assert acc["accuracy"] == 0.5
        assert acc["mismatches"] == [
            {"row_index": 1, "gold": "reasoning.multistep", "extractor": "code.generation"}
        ]


class TestBuildRound2Gold:
    def test_agreed_plus_reconciled_keyed_by_quote(self):
        a = [
            {"row_index": 0, "quote": "Q1", "answers": {"s": "own"}},
            {"row_index": 1, "quote": "Q2", "answers": {"s": "own"}},
        ]
        b = [
            {"row_index": 0, "quote": "Q1", "answers": {"s": "own"}},   # agree
            {"row_index": 1, "quote": "Q2", "answers": {"s": "vendor"}},  # disagree
        ]
        # reconcile uses its OWN indexing; only the quote pairs it correctly.
        reconciled = [{"row_index": 0, "quote": "Q2", "reconciled": {"s": "own"}}]
        gold = build_round2_gold(a, b, reconciled)
        assert gold["Q1"] == {"s": "own"}       # agreed
        assert gold["Q2"] == {"s": "own"}       # reconciled

    def test_an_unsettled_disagreement_is_not_gold(self):
        a = [{"row_index": 0, "quote": "Q", "answers": {"s": "own"}}]
        b = [{"row_index": 0, "quote": "Q", "answers": {"s": "vendor"}}]
        assert build_round2_gold(a, b, []) == {}


class TestAnswersOf:
    def test_prefers_answers_then_reconciled_then_label(self):
        assert answers_of({"answers": {"q": 1}}) == {"q": 1}
        assert answers_of({"reconciled": {"q": 2}}) == {"q": 2}
        assert answers_of({"label": "x"}) == {"label": "x"}
        assert answers_of({}) == {}
