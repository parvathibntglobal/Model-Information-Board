"""#384: `weight.py`'s refusal told a reader the fix was cosmetic. It was not.

The message on the `has_conditions` gap read:

    to close it: build DocumentFacts from the document table - AND note the
    column is False on all 7 populated rows and NULL on 57, so carrying it
    changes nothing until something sets it True.

⚠ THE PARENTHETICAL WAS THE LOAD-BEARING HALF. A reader who hits this refusal
  is told the work is cosmetic and can be deferred. Measured against staging:

      2026-09-21   has_conditions True  1,005
      2026-09-24   has_conditions True  1,260     and still climbing

  Carrying the column moves weights on every one of them. `has_numbers` sat
  behind the same message with the same defect — *"True on 6 of 7 non-NULL
  rows"* against 9,349 True today.

  It stopped a blog extraction at batch 2 of 21 (#377). The guard was right to
  refuse; the message was the only thing wrong, and it was wrong in the
  direction that tells you not to bother.

⚠ AND THE FIX IS NOT TO UPDATE THE NUMBERS. 1,005 rotted into 1,260 in three
  days, and 7 rotted into 18,651 over a month. A count written into a string
  is a measurement with no date and no way to re-take it (rule 11), so the
  numbers come OUT and the structural fact goes in — plus the query, so a
  reader can take the measurement themselves at the moment they need it.

This test is what makes it the fifth instance rather than the fifth of many.
"""

from __future__ import annotations

import re

from judge.vet.weight import INPUT_GAPS

#: Things that legitimately carry digits and cannot rot, because they name a
#: fixed thing rather than counting a population.
#:
#: ⚠ EACH ONE IS A HOLE, so each is narrow and listed rather than covered by a
#:   loose "any number in a date-ish context". A rule broad enough to be
#:   comfortable is a rule that lets the next count through.
_CANNOT_ROT = (
    r"\d{4}-\d{2}-\d{2}",        # an ISO date: fixed by definition
    r"#\d+",                      # an issue reference
    r"rule \d+",                  # a numbered rule in CLAUDE.md
    r"\bE\d\b",                   # a pipeline stage
    r"\b\d+x\b",                  # a ratio, e.g. "a 6x over-weight"
    r"[a-z]-\d+\.\d+\.\d+",      # a version string
    # ⚠ SQL ORDINALS, caught by the first run of this test on the very fix
    #   it was written for: `GROUP BY 1` names a column position, not a
    #   row count. Left in rather than reworded around, because the next
    #   message that hands over a query will hit the same thing.
    r"(?i)\b(?:GROUP|ORDER)\s+BY\s+\d+",
)


def _countable_digits(text: str) -> list[str]:
    """Every number in `text` that is not one of the fixed forms above.

    Returns the surrounding words rather than the bare digits, because
    `['7']` in a failure message tells a reader nothing about where to look.
    """
    masked = text
    for pattern in _CANNOT_ROT:
        masked = re.sub(pattern, " ", masked)
    return [
        m.group(0)
        for m in re.finditer(r"[\w.]*\b\d[\d,]*\b[\w.]*(?:\s+\w+){0,3}", masked)
    ]


class TestNoGapMessageCountsAPopulation:
    def test_no_fix_string_carries_a_bare_count(self):
        """⚠ THE WHOLE CLASS, NOT THE TWO INSTANCES. `has_conditions` and
        `has_numbers` are the ones that rotted; this fails on the next one
        before it is written, which is the only thing that makes the class
        counted rather than merely named."""
        offenders = {}
        for name, gap in INPUT_GAPS.items():
            found = _countable_digits(gap.fix)
            if found:
                offenders[name] = found
        assert not offenders, (
            "a refusal message counts a population, and a count in a string is "
            "a measurement with no date and no way to re-take it (rule 11):\n  "
            + "\n  ".join(f"{k}: {v}" for k, v in offenders.items())
            + "\nState the structural fact and give the query instead."
        )

    def test_the_two_that_rotted_say_the_opposite_now(self):
        """`has_conditions` told a reader the work was cosmetic. It must now
        tell them the opposite, because the opposite is what is true."""
        fix = INPUT_GAPS["has_conditions"].fix
        assert "changes nothing" not in fix
        assert "MOVES" in fix or "moves" in fix

    def test_it_hands_over_the_query_rather_than_the_answer(self):
        """A reader who needs the figure can take it; a message that holds one
        is stale from the day it is written."""
        fix = INPUT_GAPS["has_conditions"].fix
        assert "SELECT" in fix and "GROUP BY" in fix

    def test_the_rule_2_prohibition_survived_the_edit(self):
        """⚠ THE PART THAT MUST NOT BE LOST WHILE FIXING THE PART THAT WAS
        WRONG. Both messages carry a prohibition — `has_numbers` may not be
        derived from the claim (rule 2), `has_conditions` may not be derived
        from `claim.conditions` (rule 6) — and those are the sentences that
        stop somebody closing the gap the cheap and wrong way."""
        assert "rule 2" in INPUT_GAPS["has_numbers"].fix
        assert "rule 6" in INPUT_GAPS["has_conditions"].fix
        assert "may NOT be derived" in INPUT_GAPS["has_numbers"].fix
        assert "may NOT be derived" in INPUT_GAPS["has_conditions"].fix


class TestTheDetectorItself:
    def test_a_date_is_not_a_count(self):
        assert not _countable_digits("keyed on speaking alone until 2026-08-30")

    def test_an_issue_reference_is_not_a_count(self):
        assert not _countable_digits("carved out of #397 and #399")

    def test_a_population_count_is_caught(self):
        assert _countable_digits("False on all 7 populated rows and NULL on 57")

    def test_a_thousands_separator_does_not_hide_one(self):
        """`1,005` must not read as `1` followed by punctuation."""
        assert _countable_digits("True on 1,005 documents")
