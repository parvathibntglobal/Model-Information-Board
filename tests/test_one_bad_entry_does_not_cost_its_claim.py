"""One invalid board entry is dropped; the claim and its valid entries are kept (#411).

THE DEFECT. A claim carries a LIST of board entries - one quote filed under a
job, a capability and a metric - and the schema check sat on each element. One
metric entry missing `basis` failed the whole claim, so every valid entry beside
it was lost too. Measured on #411: the seven threads lost every entry on every
claim that carried one faulty metric, not seven metric entries.

THE RULING (#411): drop the entry, keep the claim, and COUNT what was dropped.
These tests pin all three halves, plus the edge where nothing valid is left.
"""

from __future__ import annotations

import json

from judge.extract.runner import DroppedEntry, dropped_entry_shapes, salvage_claims

GOOD_CAPABILITY = {
    "section": "capability",
    "slug": "summarization-fidelity",
    "name": "Summarization fidelity",
    "definition": "Condenses long text without dropping a detail.",
}
GOOD_JOB = {
    "section": "best_for",
    "slug": "coding-agent",
    "name": "Coding agent",
    "definition": "An agent that writes and edits code on its own.",
}
#: A metric with no unit, figure or basis - the #411 case.
BAD_METRIC = {
    "section": "metric",
    "slug": "ttft",
    "name": "Time to first token",
    "definition": "How long until the first token arrives.",
}


def claim(entries, **overrides) -> dict:
    c = {
        "source_comment_id": "d1",
        "model_ref": {
            "surface": "Flash",
            "resolved_version_id": "google/gemini-2.5-flash",
            "specificity": "family",
            "resolution_confidence": 0.8,
            "speaking": "own-experience",
        },
        "capability": "summarization.fidelity",
        "board_entries": entries,
        "polarity": "negative",
        "quote": "it drops the second paragraph every time",
        "quote_offset": [0, 40],
        "relevance": "central",
    }
    c.update(overrides)
    return c


def salvage(*claims):
    return salvage_claims(json.dumps({"claims": list(claims)}))


class TestTheClaimSurvivesABadEntry:
    def test_the_valid_entries_are_kept_and_the_bad_one_dropped(self):
        built, lost, envelope_error, dropped = salvage(
            claim([GOOD_CAPABILITY, BAD_METRIC, GOOD_JOB])
        )

        assert envelope_error is None
        assert lost == [], "the claim was lost for one bad entry - #411 is back"
        assert len(built) == 1
        kept = [(e.section, e.slug) for e in built[0].board_entries]
        assert kept == [("capability", "summarization-fidelity"), ("best_for", "coding-agent")]

    def test_the_dropped_entry_is_counted_not_silent(self):
        _, _, _, dropped = salvage(claim([GOOD_CAPABILITY, BAD_METRIC]))

        assert len(dropped) == 1
        d = dropped[0]
        assert isinstance(d, DroppedEntry)
        assert (d.claim_index, d.entry_index) == (0, 1)
        assert d.errors and all(e.startswith("board_entries.") for e in d.errors)

    def test_the_drop_reasons_fold_into_shapes_like_lost_claims(self):
        _, _, _, dropped = salvage(
            claim([GOOD_CAPABILITY, BAD_METRIC]),
            claim([GOOD_JOB, BAD_METRIC]),
        )
        shapes, overflow = dropped_entry_shapes(dropped)

        assert overflow == 0
        # Two entries failed the same way: one shape, counted twice.
        assert sum(shapes.values()) >= 2
        assert all(k.startswith("board_entries") for k in shapes)


class TestNothingChangesWhereThereIsNothingToDrop:
    def test_a_fully_valid_claim_drops_nothing(self):
        built, lost, _, dropped = salvage(claim([GOOD_CAPABILITY, GOOD_JOB]))

        assert len(built) == 1 and lost == [] and dropped == []
        assert len(built[0].board_entries) == 2

    def test_a_claim_with_no_valid_entry_is_lost_as_before_and_not_double_counted(self):
        """No valid entry left is a lost claim, not a partial one. It goes to
        `Unsalvaged` exactly as before, and its entries are NOT also reported as
        dropped - one failure, counted once."""
        built, lost, _, dropped = salvage(claim([BAD_METRIC]))

        assert built == []
        assert len(lost) == 1
        assert dropped == []

    def test_a_claim_that_fails_for_another_reason_is_still_lost(self):
        """Dropping a bad entry must not rescue a claim whose own fields are
        wrong: an over-long quote still loses the claim."""
        built, lost, _, dropped = salvage(
            claim([GOOD_CAPABILITY, BAD_METRIC], quote="x" * 5000)
        )

        assert built == []
        assert len(lost) == 1
        assert dropped == [], "a drop was recorded for a claim that was lost anyway"

    def test_an_unreadable_envelope_returns_four_empty_values(self):
        built, lost, envelope_error, dropped = salvage_claims("not json")

        assert envelope_error is not None
        assert built == [] and lost == [] and dropped == []
