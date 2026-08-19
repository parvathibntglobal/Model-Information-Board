"""The spend cap, and the three things it has to keep apart.

`EXTRACTION_DAILY_BUDGET_USD` was a name in two comments and nothing else, so
these are the first assertions that a budget binds at all.
"""

from __future__ import annotations

import pytest

from judge.ask.cost import Pricing
from judge.extract.budget import (
    DEFAULT_PRICING,
    Budget,
    BudgetExhausted,
)
from judge.extract.client import Completion


def completion(inp=1292, out=500, model="google/gemini-2.5-flash") -> Completion:
    return Completion(raw_arguments="{}", input_tokens=inp, output_tokens=out, model=model)


class TestItActuallyStops:
    """The whole point. A budget you cannot enforce is not a budget."""

    def test_a_run_stops_when_the_cap_is_reached(self):
        budget = Budget(limit_usd=0.01)
        calls = 0
        with pytest.raises(BudgetExhausted):
            while True:
                budget.check_before_call()
                budget.charge(completion())
                calls += 1
                assert calls < 1000, "the cap never bound"

        assert budget.spent_usd <= 0.01

    def test_it_refuses_BEFORE_the_call_rather_than_reporting_after(self):
        """Spend cannot be undone, so a check after the call is a report."""
        budget = Budget(limit_usd=0.001)  # smaller than one estimated call
        with pytest.raises(BudgetExhausted):
            budget.check_before_call()
        assert budget.calls == 0
        assert budget.spent_usd == 0.0

    def test_a_dollar_buys_roughly_six_hundred_threads(self):
        """The figure the budget decision was made on, asserted so a pricing
        or prompt change that moves it fails here rather than on a bill."""
        budget = Budget(limit_usd=1.00)
        n = 0
        with pytest.raises(BudgetExhausted):
            while True:
                budget.check_before_call()
                budget.charge(completion())
                n += 1
        assert 550 <= n <= 700, f"a dollar now buys {n} threads, not ~610"


class TestABudgetStopIsNotAFailureAndNotAnEmptyBatch:
    """Engineer 1's condition. From outside, three nights look identical:
    stopped on budget, found nothing, broke. Only the first is a decision
    somebody can revisit by raising a number."""

    def test_the_refusal_carries_what_a_job_run_row_needs(self):
        budget = Budget(limit_usd=0.005)
        with pytest.raises(BudgetExhausted) as caught:
            while True:
                budget.check_before_call()
                budget.charge(completion())

        exc = caught.value
        assert exc.limit_usd == 0.005
        assert exc.completed >= 1, "how many threads were done is what makes it a stop"
        assert exc.spent_usd > 0

    def test_the_message_says_it_is_a_choice_rather_than_an_error(self):
        budget = Budget(limit_usd=0.0001)
        with pytest.raises(BudgetExhausted) as caught:
            budget.check_before_call()

        message = str(caught.value)
        assert "extraction-budget" in message
        assert "not a failure" in message
        assert "not an empty corpus" in message


class TestNoCapIsADecision:
    """Rule 6 on our own configuration."""

    def test_a_missing_env_var_yields_no_budget_rather_than_an_unlimited_one(self, monkeypatch):
        monkeypatch.delenv("EXTRACTION_DAILY_BUDGET_USD", raising=False)
        assert Budget.from_env() is None

    def test_an_empty_env_var_is_also_not_a_configured_budget(self, monkeypatch):
        monkeypatch.setenv("EXTRACTION_DAILY_BUDGET_USD", "   ")
        assert Budget.from_env() is None

    def test_a_set_value_is_read(self, monkeypatch):
        monkeypatch.setenv("EXTRACTION_DAILY_BUDGET_USD", "1.00")
        budget = Budget.from_env()
        assert budget is not None
        assert budget.limit_usd == 1.00
        assert budget.uncapped is False

    def test_an_uncapped_budget_never_raises(self):
        budget = Budget(limit_usd=None)
        assert budget.uncapped is True
        assert budget.remaining_usd is None
        for _ in range(100):
            budget.check_before_call()
            budget.charge(completion())
        assert budget.calls == 100


class TestTheEstimateAndTheMeasurementStaySeparate:
    """Rule 7. Enforcing on an estimate while reporting it as measured is the
    two halves swapped."""

    def test_spend_is_charged_from_reported_tokens_not_from_the_estimate(self):
        budget = Budget(limit_usd=None)
        budget.charge(completion(inp=100, out=10))
        expected = (100 * 0.30 + 10 * 2.50) / 1_000_000
        assert budget.spent_usd == pytest.approx(expected)
        assert budget.spent_usd != budget.estimated_next_call_usd

    def test_a_completion_reporting_no_usage_is_charged_zero_and_counted(self):
        """A provider that stops reporting usage silently disables this cap.
        The symptom is a suspiciously low total, which looks like good news."""
        budget = Budget(limit_usd=1.0)
        budget.charge(completion(inp=0, out=0))

        assert budget.spent_usd == 0.0
        assert budget.unmetered_calls == 1
        assert "this total is a floor" in budget.summary()

    def test_spend_is_broken_down_by_model(self):
        """A single total cannot say the extractor changed mid-run."""
        budget = Budget(limit_usd=None)
        budget.charge(completion(model="google/gemini-2.5-flash"))
        budget.charge(completion(model="something/else"))

        assert set(budget.spend_by_model) == {"google/gemini-2.5-flash", "something/else"}

    def test_pricing_is_injectable_so_the_seeded_constant_can_go(self):
        """`DEFAULT_PRICING` is a build fixture from `seed_models.yaml`. When
        the poller lands, prices come from `model_version`."""
        budget = Budget(limit_usd=None, pricing=Pricing(price_in=1.0, price_out=1.0))
        budget.charge(completion(inp=1_000_000, out=0))
        assert budget.spent_usd == pytest.approx(1.0)
        assert DEFAULT_PRICING.price_in == 0.30
