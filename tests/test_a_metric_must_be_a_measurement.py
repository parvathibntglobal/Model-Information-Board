"""Two gates on a metric figure, and what each was found by.

⚠ THE PAGE THAT PROMPTED THEM WAS CONFIDENTLY WRONG (#368). Under a heading
  reading *SWE-bench Verified*, Gemini 3.8 Flash showed eight figures, seven
  from one document, and not one of them was SWE-bench Verified — OSWorld-2.0,
  Terminal-bench 4.0, DeepSWE v1.1 and "the hard biology set", presented side by
  side as one axis.

Five defects sit behind that page. Three are classification and need somewhere
to record a harness and a variant. TWO ARE MECHANICAL, and mechanical is the
half worth a test: a prompt asks, a check enforces.

Run against every stored figure on 2026-09-18, these two refuse **19.8%**:

    440 metric figures
    353  pass                      80.2%
     44  figure not in its quote    10.0%
     43  no quantity                 9.8%
"""

from __future__ import annotations

import pytest

from judge.store.board_entries import metric_refusal


def entry(**kw):
    base = {
        "section": "metric",
        "value_verbatim": "43.5%",
        "quote": "it scores 43.5% on the verified set",
    }
    return {**base, **kw}


class TestTheFigureMustBeInItsOwnQuote:
    """⚠ `quote_verified` does NOT check this, and the name suggests it does.

    `judge/extract/runner.py:383` is `p.quote in thread.flattened_text` — the
    quote really is in the document. That is provenance, and it says nothing
    about whether the quote supports the figure attached to it.

    Both of these are real rows that passed it:

        61.4%  <-  "It tops the chart on finance, legal, long video and chart
                    reasoning"
        160M   <-  "the amount of token generation needed, since it defaults to
                    xhigh reasoning, was so high"
    """

    def test_a_figure_taken_from_its_quote_passes(self):
        assert metric_refusal(entry()) is None

    def test_a_figure_that_is_nowhere_in_its_quote_is_refused(self):
        assert metric_refusal(entry(
            value_verbatim="61.4%",
            quote="It tops the chart on finance, legal, long video and chart reasoning",
        )) == "figure not in its quote"

    def test_the_real_row_that_found_this(self):
        assert metric_refusal(entry(
            value_verbatim="160M",
            quote=(
                "the amount of token generation needed, since it defaults to "
                "xhigh reasoning, was so high"
            ),
        )) == "figure not in its quote"

    def test_a_quote_broken_across_lines_still_holds_its_figure(self):
        """A rendered quote wraps; a wrapped figure is not a different figure.

        Whitespace-insensitive on both sides, or every multi-word value in a
        flattened thread would be refused for having a newline in it.
        """
        assert metric_refusal(entry(
            value_verbatim="$0.50 per million",
            quote="priced at\n$0.50   per\nmillion input tokens",
        )) is None


class TestAValueWithNoQuantityIsNotAMeasurement:
    """43 of 440 stored figures carry no digit at all.

    These are real things somebody said, and they belong in a capability or a
    best-for entry. Rendered in a column headed FIGURE with a unit beside them,
    they are a measurement the board never took.
    """

    @pytest.mark.parametrize("value", [
        "twice as expensive",
        "slowest",
        "one or two euros",
        "volume",
        "massive gap in token pricing",
        "token hungry",
        "expensive",
    ])
    def test_a_judgement_is_not_a_figure(self, value):
        assert metric_refusal(entry(
            value_verbatim=value, quote=f"it is {value} compared to the others",
        )) == "no quantity"

    @pytest.mark.parametrize("value", [
        "43.5%", "84 tasks", "$0.50", "2.3x", "160M", "1,000,000 tokens", "0",
    ])
    def test_anything_carrying_a_digit_is_let_through(self, value):
        """⚠ DELIBERATELY CRUDE, and the alternative is worse.

        A stricter parser would have to decide which units are real, and that is
        a vocabulary decision this function has no standing to make — it would
        start refusing figures for being in a unit nobody had listed yet, which
        is rule 8's "an unmeasured check ships as a weight not a gate" in the
        one place it is being used AS a gate.

        `0` is in this list on purpose: zero is a measurement.
        """
        assert metric_refusal(entry(
            value_verbatim=value, quote=f"it reached {value} in our run",
        )) is None


class TestWhatTheGateDoesNotTouch:
    def test_a_capability_entry_is_not_a_metric_and_is_never_refused(self):
        """The gate is scoped to `metric`. A capability entry saying "it is slow"
        is a real report and this has no opinion about it."""
        assert metric_refusal({
            "section": "capability",
            "value_verbatim": "twice as expensive",
            "quote": "it is twice as expensive",
        }) is None

    def test_a_metric_entry_carrying_no_figure_at_all_is_kept(self):
        """⚠ RULE 6. An entry ABOUT a metric that quotes no number — "they
        publish latency figures" — is evidence, and it is not a measurement
        claiming to be one. Refusing it would delete a fact to enforce a rule
        about a different fact."""
        assert metric_refusal(entry(value_verbatim=None)) is None
        assert metric_refusal(entry(value_verbatim="")) is None
        assert metric_refusal(entry(value_verbatim="   ")) is None


class TestTheRefusalIsCountedByReason:
    """⚠ RULE 4. A refusal that does not say which kind it was sends every
    reader to the same place, and the two have different fixes: "no quantity"
    is a classification problem and "figure not in its quote" is a fabrication
    one."""

    def test_the_two_reasons_are_distinguishable(self):
        no_quantity = metric_refusal(entry(
            value_verbatim="slowest", quote="it is the slowest of the three"))
        unsupported = metric_refusal(entry(
            value_verbatim="61.4%", quote="it tops the chart"))
        assert no_quantity != unsupported
        assert no_quantity and unsupported

    def test_a_value_with_no_quantity_reports_that_rather_than_the_other(self):
        """Order matters: "slowest" is also not in its quote in the literal
        sense a reader would check second. The more specific reason wins, so a
        judgement is never reported as a fabrication."""
        assert metric_refusal(entry(
            value_verbatim="much cheaper", quote="a totally unrelated sentence",
        )) == "no quantity"
