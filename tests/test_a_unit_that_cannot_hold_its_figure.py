"""A figure filed under an axis that measures something else (#400 follow-up).

WHERE THIS CAME FROM. A reviewer read all 56 quotes that had produced two or
more entries in one board section and ruled on each. Sixteen carried at least
one entry naming something its quote does not support, and they split into two
kinds that want two different fixes:

  ELEVEN needed a person. "Haiku for routing, Sonnet for reasoning, Opus for
  long chains" credited Haiku with three capabilities; only one of the three
  clauses is about Haiku. No check can read whose clause a comma introduces,
  so that one is a prompt rule and a ruling.

  FIVE were MECHANICAL, and this is them. The extractor matched the axis by
  vocabulary rather than by measurement:

      "about 75 minutes"   -> time-to-first-token, unit milliseconds
      "8.566 seconds"      -> time-to-first-token, unit milliseconds
      "118K per task"      -> tokens-per-second,   unit tokens/second
      "10.59M tokens"      -> cost-per-token,      unit tokens

  Every figure is real, every figure is in its own quote, and every one of them
  renders as a number nobody measured on the page it lands on. A 75-minute task
  duration beside figures around 300ms is not an outlier; it is a different
  measurement wearing the column's heading.

⚠ THESE WITHHOLD A LABEL, NOT A FIGURE. The row stays exactly as stored and
  comes back the moment the unit or the axis is corrected, which is why the
  reason is phrased as a disagreement between two of the row's own columns
  rather than as a verdict on the evidence.

RULE 8, MEASURED BEFORE SHIPPING AS A GATE: run over all 519 metric rows in the
shared database on 2026-09-22, `shown` went 402 -> 392. Eleven rows left it and
all eleven are wrong rows; one came back, because measuring the old money check
on the same population found it withholding `2%` under "percent of input cost".
A twelfth was a false positive - `2 minutes 54 seconds` under a unit of minutes
- and it is fixed rather than tolerated, in `_time_families`.
"""

from __future__ import annotations

import pytest

from judge.store.board_entries import _time_families, metric_withholding


def metric(value, quote=None, *, unit, slug):
    return {
        "section": "metric",
        "slug": slug,
        "unit": unit,
        "value_verbatim": value,
        "quote": quote if quote is not None else f"it took {value} to finish",
    }


class TestATimeUnitIsTheOneTheFigureIsWrittenIn:
    @pytest.mark.parametrize(
        "value,unit",
        [
            ("about 40 minutes per task", "milliseconds"),
            ("about 75 minutes", "milliseconds"),
            ("21 minutes", "milliseconds"),
            ("8.566 seconds", "milliseconds"),
            ("1.2 seconds", "milliseconds"),
        ],
    )
    def test_a_duration_under_the_wrong_duration_is_withheld(self, value, unit):
        held = metric_withholding(
            metric(value, unit=unit, slug="time-to-first-token")
        )
        assert held is not None
        assert "the figure is written in" in held

    @pytest.mark.parametrize(
        "value,unit",
        [
            ("300ms", "milliseconds"),
            ("~190 ms (streaming)", "milliseconds"),
            ("roughly 40 minutes per task", "minutes"),
            ("10h 37m", "hours"),
        ],
    )
    def test_a_figure_that_agrees_with_its_unit_is_shown(self, value, unit):
        slug = "task-duration" if "minute" in unit or "hour" in unit else "ttft"
        assert metric_withholding(metric(value, unit=unit, slug=slug)) is None

    def test_a_bare_number_is_not_checked(self):
        """⚠ RULE 6, AND IT IS THE REASON THIS CHECK IS SAFE. `280` under
        `milliseconds` names no unit of its own, so nothing here knows whether
        it agrees. An unknown stays an unknown; it does not become a mismatch
        and take a sound figure off the page."""
        assert metric_withholding(
            metric("280", "latency was 280", unit="milliseconds", slug="ttft")
        ) is None

    def test_a_compound_duration_agrees_with_either_half(self):
        """⚠ THE ONE FALSE POSITIVE THE MEASUREMENT FOUND. `2 minutes 54
        seconds` names two families; the first version took the first match,
        read `second`, and withheld a row whose unit is right there in the
        value. A figure is only in conflict with its unit when the unit is
        nowhere in it."""
        assert metric_withholding(
            metric("2 minutes 54 seconds", unit="minutes", slug="time-to-completion")
        ) is None


class TestTheAbbreviationsAttachToAFigureRatherThanToAWordEnding:
    def test_ms_after_a_digit_is_milliseconds(self):
        """A leading `\\b` cannot do this: there is no word boundary between
        `0` and `m`, so the first version read `300ms` as naming no unit."""
        assert _time_families("300ms") == {"millisecond"}

    @pytest.mark.parametrize("text", ["items", "forms", "minimum", "seconds/min"])
    def test_a_letter_before_the_abbreviation_is_not_a_unit(self, text):
        """Mention versus use, the seventh time this repository has met it:
        `ms` ends `items`, and `min` opens `minimum`."""
        families = _time_families(text)
        assert "millisecond" not in families or text == "seconds/min"
        if text in {"items", "forms", "minimum"}:
            assert families == set()

    def test_milliseconds_is_not_also_seconds(self):
        """Both patterns can fire on one word - `milliseconds` contains
        `second` - and a unit that disagreed with itself would withhold the
        whole latency page."""
        assert _time_families("milliseconds") == {"millisecond"}


class TestARatePerSecondIsNotARatePerTask:
    def test_a_per_task_figure_under_a_per_second_unit_is_withheld(self):
        held = metric_withholding(
            metric("118K per task",
                   "Claude Code + Opus 4.7 xhigh: 90 tasks, 10.59M tokens, "
                   "118K per task, 10h 37m",
                   unit="tokens/second", slug="tokens-per-second")
        )
        assert held == "the unit is per second and the figure is per something else"

    @pytest.mark.parametrize(
        "value", ["~60 tokens/second", "58 tokens per second", "145 tok/s"]
    )
    def test_a_real_throughput_reading_is_shown(self, value):
        assert metric_withholding(
            metric(value, f"it runs at {value}",
                   unit="tokens/second", slug="tokens-per-second")
        ) is None


class TestAnAxisThatPromisesMoneyIsDeclaredInMoney:
    def test_a_token_total_under_a_cost_axis_is_withheld(self):
        """⚠ THE CASE NEITHER OTHER CHECK SEES. The value agrees with the unit
        perfectly - `10.59M tokens` really is tokens - and neither is a price.
        Only the SLUG disagrees, so only a slug-against-unit check finds it."""
        held = metric_withholding(
            metric("10.59M tokens",
                   "Claude Code + Opus 4.7 xhigh: 90 tasks, 10.59M tokens, "
                   "118K per task, 10h 37m",
                   unit="tokens", slug="cost-per-token")
        )
        assert held == "the axis is a cost and the unit is not money"

    def test_a_price_axis_declared_in_money_is_shown(self):
        assert metric_withholding(
            metric("$0.25 per million output tokens",
                   "V4 Flash runs $0.25 per million output tokens.",
                   unit="USD per 1M tokens", slug="cost-per-token")
        ) is None

    def test_a_share_of_a_price_is_still_about_price(self):
        """`cache-read-cost` is declared in "percent of input cost", and the
        2% in it is a real figure on a real axis. The unit names a price even
        though the value is a percentage, which is what keeps it."""
        assert metric_withholding(
            metric("2%",
                   "That 2% cache read really pays off",
                   unit="percent of input cost", slug="cache-read-cost")
        ) is None

    def test_a_euro_price_is_money(self):
        """⚠ A CURRENCY CHECK THAT KNOWS ONE CURRENCY DELETES THE OTHER'S ROWS,
        which this repository has already done once with cents. `EUR` is the
        declared unit on `cost-per-generation`."""
        assert metric_withholding(
            metric("€1.20", "about €1.20 a go", unit="EUR", slug="cost-per-generation")
        ) is None

    def test_a_non_money_axis_is_not_asked_for_money(self):
        assert metric_withholding(
            metric("57", "57 Intelligence Index", unit="points",
                   slug="intelligence-index")
        ) is None
