""""Refused" and "never sieved" are different states. #365 defect 2.

A term set's `subject` is `{alias}`. A document naming no tracked model has
nothing to render, so no `SieveVerdict` is ever built for it — it was not
refused by `subject`, `topic` or `locality`, it was never tested. A total that
merges the two reads as "the sieve rejected N", which points at tuning the
sieve, when the actionable split pointed at the registry:

     30  named a model and were refused
    123  named nothing, never sieved
    ---
    153  the number that was reported

`SieveVerdict.signal_score` already draws this line one level down — *"0 is a
MEASUREMENT here... different from a document nobody sieved, which has no
verdict at all"* — and the tally had nowhere to put it.
"""

from __future__ import annotations

import pytest

from collect.adapters.queries.sieve import SieveVerdict, tally


def _passed() -> SieveVerdict:
    return SieveVerdict(passed=True, subject=("gpt-5",), topic=("latency",))


def _refused() -> SieveVerdict:
    return SieveVerdict(passed=False, subject=("gpt-5",), missing=("topic",))


def test_untestable_defaults_to_zero_and_that_is_a_real_answer():
    """Unlike `phrase_present`, 0 here is a finding rather than an absence.

    A per-query sweep renders a subject by construction, so "every candidate
    was testable" is true of github and reddit and should not be dressed up as
    "not measured".
    """
    y = tally("q", [_passed(), _refused()])
    assert y.untestable == 0
    assert y.examined == y.candidates == 2


def test_untestable_sits_beside_candidates_and_does_not_move_pass_rate():
    """⚠ THE REGRESSION THAT WOULD MATTER.

    `pass_rate` is kept/candidates and has meant that since it was written.
    Folding never-sieved documents into the denominator would silently restate
    every historical yield figure.
    """
    without = tally("q", [_passed(), _refused()])
    with_untestable = tally("q", [_passed(), _refused()], untestable=123)

    assert without.pass_rate == with_untestable.pass_rate == 0.5
    assert with_untestable.candidates == 2
    assert with_untestable.examined == 125


def test_refused_is_not_examined_minus_kept():
    """The arithmetic that was wrong before the field existed.

    `candidates - kept` is right only while nothing untestable is in scope,
    which is exactly why the blog census reported 153.
    """
    y = tally("q", [_passed(), _refused()], untestable=123)
    assert y.refused == 1
    assert y.examined - y.kept == 124  # the merged number, and it is not `refused`


def test_the_census_split_renders_as_two_facts():
    """The 30/123 shape, which is the whole point of the field."""
    verdicts = [_passed()] * 26 + [_refused()] * 30
    y = tally("blog-census", verdicts, untestable=123)

    assert y.candidates == 56
    assert y.refused == 30
    assert y.untestable == 123
    assert y.examined == 179
    assert y.split() == (
        "30 refused of 56 sieved, 123 never sieved (no tracked model named)"
    )


def test_the_split_says_nothing_about_never_sieved_when_there_is_none():
    """A sweep line must not grow a clause reporting zero of something."""
    y = tally("q", [_passed(), _refused()])
    assert y.split() == "1 refused of 2 sieved"
    assert "never" not in y.split()


def test_a_negative_untestable_is_refused_rather_than_stored():
    """It is a count of documents. A caller computing it by subtraction and
    getting it backwards should hear about it here, not in a report."""
    with pytest.raises(ValueError, match="cannot be negative"):
        tally("q", [_passed()], untestable=-1)
