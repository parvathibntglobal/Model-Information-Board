"""A stored metric figure is shown only if it can support itself (#379).

WHAT THIS REPLACED, AND WHY THE REPLACEMENT IS A DIFFERENT KIND OF THING.

The first attempt withheld every metric row written before a cutoff date, on
the reasoning that a row recorded after the checks existed had been through
them. A date is a proxy, and it failed in both directions a proxy always does:

  - it hid 269 figures that are perfectly sound, because of WHEN they were
    written rather than anything about them;
  - it would have published an unchecked figure written tomorrow, because the
    extractor that writes it does not have to have run any check.

`metric_withholding` asks each row the question directly. Every input is a
column the row already carries, so no migration and no re-extraction - which
is what the ruling on #379 required: *"No re-extraction, no deletion... The 440
keep their figures and stop claiming to be verified."*

MEASURED OVER THE 447 STORED ROWS, 2026-09-21:

    447  stored
     75  already declined by a reviewer
     82  refused by the two mechanical gates
     21  refused as a relative claim or an incoherent unit
    ---
    269  shown

⚠ NOTHING IS DELETED. This is a read filter over rows that stay exactly as
  stored. A row that starts passing - because a reviewer rules on it, or
  because the axis work lands - appears with no migration and no backfill.
"""

from __future__ import annotations

import pytest

from judge.store.board_entries import metric_withholding


def metric(value, quote, unit=None, slug="cost-per-token"):
    return {
        "section": "metric",
        "slug": slug,
        "value_verbatim": value,
        "quote": quote,
        "unit": unit,
    }


class TestTheTwoMechanicalGatesStillApply:
    """`metric_withholding` starts with `metric_refusal`, so a row stored before
    those gates existed is now held to them on the way out."""

    def test_a_figure_that_is_not_in_its_quote_is_withheld(self):
        # The defect in its original form: `quote_verified` checks the QUOTE is
        # in the document and says nothing about whether the FIGURE is in the
        # quote. This row passed that check and is still wrong.
        held = metric_withholding(
            metric("61.4%", "It tops the chart on finance, legal and long video")
        )
        assert held == "figure not in its quote"

    def test_a_value_with_no_quantity_is_withheld(self):
        assert metric_withholding(
            metric("twice as expensive", "twice as expensive")
        ) is not None

    def test_a_figure_that_is_in_its_quote_is_shown(self):
        assert metric_withholding(
            metric("$0.87/M", "DeepSeek V4 Pro  @ $0.87/M", "USD per 1M tokens")
        ) is None


class TestARelativeClaimIsNotAValueOnTheAxis:
    """"3x cheaper" measures the gap to another model, not the axis the column
    is headed with. Rendered under USD PER 1M TOKENS it is not an imprecise
    price - it is not a price."""

    @pytest.mark.parametrize(
        "value,quote",
        [
            ("70% lower cost", "70% lower cost"),
            ("3x cheaper", "Better than V4 Pro while being 3x cheaper"),
            ("~50x fewer FLOPs", "We match V4 Pro Base using ~50x fewer FLOPs"),
            ("about 25% less", "it would cost about 25% less than Fable 5"),
            ("6x jump on Terminal-Bench", "post-training delivers 6x jump on Terminal-Bench"),
        ],
    )
    def test_comparatives_and_multipliers_are_withheld(self, value, quote):
        held = metric_withholding(metric(value, quote, "USD per 1M tokens"))
        assert held == "a relative claim, not a value on this axis"

    @pytest.mark.parametrize(
        "value,unit,slug",
        [
            ("~60 tokens/second", "tokens/second", "tokens-per-second"),
            ("~190 ms (streaming)", "milliseconds", "time-to-first-token"),
            ("around $1.20", "USD per 1M tokens", "cost-per-token"),
            ("~145 tokens / second", "tokens/second", "tokens-per-second"),
            ("about 40 minutes per task", "minutes", "task-duration"),
        ],
    )
    def test_an_approximate_reading_is_kept(self, value, unit, slug):
        """⚠ APPROXIMATION IS NOT COMPARISON, and an earlier version of this
        conflated them and refused 14 real measurements. `~60 tokens/second` is
        a reading somebody took and rounded; `3x faster` is not a reading at
        all. Refusing the first deletes a fact to enforce a rule about the
        second (rule 6)."""
        # ⚠ THE SLUG IS PART OF THE CASE NOW, and giving them all the default
        #   `cost-per-token` is what made four of these fail when the axis/unit
        #   check landed. `~60 tokens/second` really is withheld under a
        #   cost axis - correctly - so a fixture that files a throughput
        #   reading under a price would have tested the wrong thing.
        assert metric_withholding(
            metric(value, f"it does {value}", unit, slug=slug)
        ) is None


class TestTheUnitHasToBeAbleToHoldTheValue:
    def test_a_percentage_under_a_currency_unit_is_withheld(self):
        held = metric_withholding(
            metric("80%", "GPT-5.6 costs drop 80%", "USD per 1M tokens")
        )
        assert held is not None

    def test_cents_count_as_money(self):
        """⚠ AN EARLIER PASS REFUSED THIS ROW for not starting with a dollar
        sign. `8.7¢ per task` is money, and a currency check that only knows
        one currency's symbol deletes the rows written in the other."""
        assert metric_withholding(
            metric("8.7¢ per task", "cheapest at 8.7¢ per task", "USD per task")
        ) is None

    def test_a_non_money_unit_is_not_asked_for_money(self):
        assert metric_withholding(
            metric("38.8%", "it scores 38.8% on the set", "percent",
                   slug="swe-bench")
        ) is None


class TestItLeavesEverythingElseAlone:
    def test_a_capability_entry_is_never_withheld(self):
        # The gate is about figures. A `capability` or `best_for` entry makes no
        # claim about an axis, so there is nothing here for it to fail.
        assert metric_withholding({
            "section": "capability", "slug": "reasoning",
            "value_verbatim": "3x cheaper", "quote": "q",
        }) is None

    def test_a_metric_entry_with_no_figure_is_kept(self):
        """A metric row with no value is a section entry ABOUT a metric -
        "they publish latency numbers" - and the page can show it as evidence
        without showing it as a measurement."""
        assert metric_withholding(metric(None, "they publish latency numbers")) is None


class TestTheDateProxyIsGone:
    def test_no_cutoff_constant_survives(self):
        """The constant was a stopgap and its own docstring said so. Leaving it
        in place beside the real check would give a future reader two rules to
        reconcile, one of which is a date somebody would eventually move."""
        from pathlib import Path

        src = Path(__file__).resolve().parents[1] / "judge" / "store" / "board_entries.py"
        text = src.read_text(encoding="utf-8")
        assert "METRICS_CHECKED_SINCE" not in text
        assert "be.created_at < %s" not in text
