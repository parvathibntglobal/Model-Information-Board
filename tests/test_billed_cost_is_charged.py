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


# ── #617 review, point 2: a bring-your-own-key call can report cost 0 ────────

def test_a_byok_call_charges_the_upstream_cost_not_the_zero():
    usage = {"cost": 0, "is_byok": True,
             "cost_details": {"upstream_inference_cost": 0.0031}}
    assert client_mod._billed_cost(usage) == 0.0031


def test_a_byok_call_counts_the_fee_as_well_as_the_upstream_cost():
    """#617 review, note 1: `cost` is OpenRouter's BYOK fee, also spend."""
    usage = {"cost": 0.0002, "is_byok": True,
             "cost_details": {"upstream_inference_cost": 0.0031}}
    assert abs(client_mod._billed_cost(usage) - 0.0033) < 1e-12


def test_a_byok_call_with_no_upstream_cost_falls_back_to_tokens(monkeypatch):
    usage = {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0, "is_byok": True}
    assert client_mod._billed_cost(usage) is None
    kw = _ledger_kwargs(monkeypatch, usage)
    assert "reported" not in kw  # priced from tokens, never recorded at $0


def test_an_ordinary_call_takes_its_cost_as_billed():
    assert client_mod._billed_cost({"cost": 0.002, "is_byok": False}) == 0.002
    assert client_mod._billed_cost({}) is None


# ── #617 review, points 1 and 3: the cost says what it is made of ────────────

def test_the_budget_counts_how_each_charge_was_priced():
    budget = Budget(limit_usd=None, pricing=PRICING)
    budget.charge(_completion(0.01))
    budget.charge(_completion(None))
    assert (budget.billed_charges, budget.token_charges) == (1, 1)


def test_cost_basis():
    from judge.extract.budget import cost_basis

    assert cost_basis(0, 0, 0) is None
    assert cost_basis(95, 0, 0) == "billed"
    assert cost_basis(0, 3, 0) == "tokens"
    assert cost_basis(2, 1, 0) == "mixed"
    # a partly billed thread is charged at the token price while its ledger
    # rows are billed - the two totals differ, so the run is mixed
    assert cost_basis(0, 1, 1) == "mixed"


def _cost_line(record: dict) -> str:
    from judge import fetch_console

    body = fetch_console.ending({"kind": "end", "status": "ok", "cost_usd": 0.0646, **record},
                                model_version_id="mv_x")
    return next(line for line in body if line.strip().startswith("cost"))


def test_the_cost_line_says_billed_tokens_or_mixed():
    assert "billed by OpenRouter" in _cost_line({"cost_basis": "billed"})
    assert "not an invoice" not in _cost_line({"cost_basis": "billed"})
    assert "no billed figure" in _cost_line({"cost_basis": "tokens"})
    assert "mixed" in _cost_line({"cost_basis": "mixed"})
    # a record from before #617 was always token-priced, and keeps its label
    assert "not an invoice" in _cost_line({})


def test_a_partly_billed_thread_is_token_priced_and_counted(monkeypatch):
    """#617 review, note 3: run the pipeline's own charge path. A thread whose
    calls reported `[0.01, None]` is charged at the token price and counted in
    `partly_billed` - the one thing that makes such a run read "mixed"."""
    from types import SimpleNamespace

    from judge import pipeline as pipeline_mod
    from judge.extract.runner import ThreadInput

    def run(self, thread, **kwargs):
        return SimpleNamespace(
            stored_claim_ids=[], cells=[], stored_claims=0,
            extraction=SimpleNamespace(
                input_tokens=1_000, output_tokens=500, cached_input_tokens=0,
                schema_retries=0, reported_costs=costs[thread.thread_context_id],
            ),
        )

    costs = {"part": [0.01, None], "whole": [0.02, 0.03]}
    monkeypatch.setattr(pipeline_mod.Pipeline, "run", run)
    pipe = pipeline_mod.Pipeline(conn=None, client=None, capability_keys=["k"],
                                 extractor_model="m")
    monkeypatch.setattr(pipe._ledger, "record", lambda record: None)
    budget = Budget(limit_usd=None, pricing=PRICING)
    threads = [ThreadInput(thread_context_id=t, flattened_text=f"text of {t}",
                           offset_map=(), raw_text_of={}) for t in costs]
    pipe.run_all(threads, facts={}, model_version_of={}, already_extracted={},
                 budget=budget)

    assert budget.partly_billed == 1
    assert (budget.billed_charges, budget.token_charges) == (1, 1)
    assert abs(budget.spent_usd - (0.05 + budget.cost_of(1_000, 500))) < 1e-12
