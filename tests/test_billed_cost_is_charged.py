"""The billed cost is what the cap and the ledger count (#381 step 2).

Measured 2026-11-09 on the GPT Image 2.5 Sunburst fetch, 95 extraction calls:

    tokens x rate, cache discount applied   $0.0521   <- what the cap counted
    tokens x rate, no discount              $0.0670   <- the per-thread lines
    what OpenRouter billed                  $0.0646

The cache discount the rate assumes mostly did not land on the upstreams that
served the calls, so the cap ran about 19% under real spend. The provider's
own figure is used whenever it arrives; token pricing is the fallback.
"""

from __future__ import annotations

from judge.ask.cost import Pricing
from judge.extract import client as client_mod
from judge.extract.budget import Budget
from judge.extract.client import Completion

PRICING = Pricing(price_in=1e-6, price_out=2e-6)


def _completion(reported: float | None) -> Completion:
    return Completion(raw_arguments="{}", input_tokens=1_000, output_tokens=500,
                      model="m", reported_cost_usd=reported)


def test_the_billed_figure_is_charged_when_it_is_reported():
    budget = Budget(limit_usd=None, pricing=PRICING)
    assert budget.charge(_completion(0.0123)) == 0.0123
    assert budget.spent_usd == 0.0123


def test_tokens_are_priced_only_when_nothing_was_reported():
    budget = Budget(limit_usd=None, pricing=PRICING)
    cost = budget.charge(_completion(None))
    # The price table, never zero: an unreported cost is not a free call.
    assert cost == budget.cost_of(1_000, 500) and cost > 0


def _ledger_kwargs(monkeypatch, usage: dict) -> dict:
    from judge import spend_ledger

    seen: dict = {}
    monkeypatch.setattr(spend_ledger, "record", lambda **kw: seen.update(kw))
    client_mod._record_spend(usage, served="served/model", asked="deepseek/deepseek-v4-flash")
    return seen


def test_the_ledger_row_records_the_billed_figure(monkeypatch):
    kw = _ledger_kwargs(monkeypatch, {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.0042})
    assert kw["reported"] is True and kw["reported_usd"] == 0.0042
    assert kw["input_tokens"] == 10 and kw["output_tokens"] == 5


def test_a_call_with_no_billed_figure_is_still_priced_from_tokens(monkeypatch):
    kw = _ledger_kwargs(monkeypatch, {"prompt_tokens": 10, "completion_tokens": 5})
    assert "reported" not in kw and "reported_usd" not in kw
    assert kw["input_tokens"] == 10 and kw["output_tokens"] == 5
