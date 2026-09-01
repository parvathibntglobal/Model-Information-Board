"""The extraction spend cap, wired to something that actually stops.

WHY THIS FILE EXISTS

`EXTRACTION_DAILY_BUDGET_USD` appeared twice in `client.py`, both times in a
comment reasoning ABOUT a budget cap, and nowhere in code. Nothing counted
spend and nothing stopped a run. It was the sixth guard on this project living
in prose rather than in code, and it is the shape that would have been agreed
in conversation, written into `.env`, and bound nothing at all.

A budget you cannot enforce is not a budget. This is the enforcement.

A STOP IS NOT AN EMPTY BATCH AND NOT A FAILURE

Engineer 1's condition, and it is the useful half. From outside, three nights
look identical:

    stopped on budget   we decided not to look further  -> raise the cap
    found nothing       we looked and there was nothing -> nothing to do
    broke               something raised                -> fix it

`harvest_run.truncated_by` already carries `extraction-budget` for exactly
this, and its comment says why: caps we chose and walls we hit are opposite
statements about the same missing data. That column is `collect/`'s, so this
lane records the equivalent on `job_run` - `outcome = 'refused'`, which the
schema defines as "the stage declined deliberately, NOT an error, and it must
not render as one".

`BudgetExhausted` therefore carries what was spent and what was skipped, so
the caller writes a row that says which of the three happened.

NO CAP IS A DECISION, NOT A DEFAULT

`limit_usd=None` means uncapped, and `uncapped` is a property callers must
read deliberately rather than a state they fall into by forgetting to set an
environment variable. `from_env()` returns None for the whole budget when the
variable is absent, so a caller cannot mistake "no limit configured" for "a
limit that happens to be generous". Rule 6 on our own configuration.

THE CHECK RUNS BEFORE THE CALL, AND THE ESTIMATE IS LABELLED

Spend cannot be undone, so the guard has to run first, and a pre-call figure
is necessarily an estimate. `charge()` then records what the completion
ACTUALLY reported, so `spent_usd` is measured even though the guard is not.
Both numbers are exposed separately rather than blended, because a cap
enforced on estimates and reported as measured is rule 7 with the two swapped.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from judge.ask.cost import Pricing
from judge.extract.client import Completion

#: ⚠ STALE SINCE THE 2026-09-01 EXTRACTOR SWITCH. These are Gemini 2.5 Flash
#: prices (per 1M tokens, `contract/seed_models.yaml`, Google's pricing page,
#: retrieved 2026-08-13). The extractor is now `deepseek/deepseek-v4-flash`,
#: whose price is not sourced here — so every cost figure this produces is a
#: Gemini-priced estimate carrying the wrong basis (rule 7). Left as the wrong
#: number rather than a guessed one: replace with DeepSeek's sourced price, or
#: let the OpenRouter poller supply it from `model_version`.
#:
#: A BUILD FIXTURE, like the seed registry it comes from - a hardcoded price is
#: exactly the seeded row `assert_no_fixtures` exists to refuse.
DEFAULT_PRICING = Pricing(price_in=0.30, price_out=2.50)

#: What one call is assumed to cost before it is made, in tokens.
#:
#: **MEASURED 2026-08-19, on the first live extraction run.** Both figures are
#: means over **n = 3 calls against ONE thread** (rule 7: that is the whole
#: population, and it is not a sample of the corpus).
#:
#:     input    2,010  against 1,300 estimated   -  55% HIGH
#:     output     589  against   800 estimated   -  26% LOW
#:
#: **THE OLD ESTIMATE WAS RIGHT FOR THE WRONG REASON, AND THAT IS THE POINT OF
#: THIS COMMENT.** Per-thread cost came out at $0.00208 against $0.00239
#: estimated - a 13% overshoot that looks like a validated method. It is not.
#: The two errors ran in opposite directions and partly cancelled: input was
#: half again as large as assumed, output a quarter smaller, and the product
#: landed close by arithmetic accident. The `4 characters per token` conversion
#: the estimate was built on (`docs/proposals/extraction-budget.md` §4, which
#: flagged it as an approximation and not this tokenizer's) is simply wrong for
#: this input, and the near-match is evidence about nothing.
#:
#: So: do not read the agreement as confirmation that estimating this way works.
#: The next figure derived by chars/4 has no support from this one.
#:
#: **THESE ARE MEANS, SO THE FILE'S OLD "DELIBERATELY GENEROUS" CLAIM NO LONGER
#: HOLDS.** The guard wants a pre-call figure at or above a typical call, because
#: too low lets a run overshoot the cap while too high only stops slightly early.
#: A mean sits at neither: roughly half of calls will exceed it. n=3 on one
#: thread measures no spread at all, so there is no p95 to use instead. What
#: would restore the property is a spread over threads of differing length -
#: until then this is the best point estimate available and knowingly not a
#: bound.
ESTIMATED_INPUT_TOKENS = 2010
ESTIMATED_OUTPUT_TOKENS = 589


class BudgetExhausted(Exception):
    """The cap bound. A refusal, never an error.

    Carries the numbers a `job_run` row needs so a budget stop is
    distinguishable from a batch that found nothing.
    """

    def __init__(self, *, spent_usd: float, limit_usd: float, completed: int) -> None:
        self.spent_usd = spent_usd
        self.limit_usd = limit_usd
        self.completed = completed
        super().__init__(
            f"extraction-budget: ${spent_usd:.4f} of ${limit_usd:.2f} after "
            f"{completed} threads. This is a cap we chose, not a failure and "
            f"not an empty corpus."
        )


@dataclass
class Budget:
    """Tracks spend against a cap, and refuses before overshooting it."""

    limit_usd: float | None
    pricing: Pricing = DEFAULT_PRICING
    spent_usd: float = 0.0
    calls: int = 0

    #: Calls whose completion reported no token usage at all. Counted rather
    #: than ignored: a provider that stops reporting usage silently disables
    #: this cap, and the symptom is a suspiciously low total that looks like
    #: good news.
    unmetered_calls: int = 0
    _by_model: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_env(cls, pricing: Pricing = DEFAULT_PRICING) -> Budget | None:
        """`None` when nothing is configured, so a caller must decide.

        Returning an uncapped Budget here would let a missing environment
        variable read as a deliberate choice to run uncapped, which is the
        same conversion rule 6 forbids everywhere else.
        """
        raw = os.getenv("EXTRACTION_DAILY_BUDGET_USD")
        if raw is None or not raw.strip():
            return None
        return cls(limit_usd=float(raw), pricing=pricing)

    @property
    def uncapped(self) -> bool:
        return self.limit_usd is None

    @property
    def remaining_usd(self) -> float | None:
        if self.limit_usd is None:
            return None
        return max(0.0, self.limit_usd - self.spent_usd)

    def cost_of(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self.pricing.price_in + output_tokens * self.pricing.price_out
        ) / 1_000_000

    @property
    def estimated_next_call_usd(self) -> float:
        """LABELLED AN ESTIMATE, and the name says so.

        Kept separate from `spent_usd`, which is measured from what the
        completions reported. Enforcing on estimates while reporting them as
        measurements is rule 7 with the halves swapped.
        """
        return self.cost_of(ESTIMATED_INPUT_TOKENS, ESTIMATED_OUTPUT_TOKENS)

    def check_before_call(self) -> None:
        """Raise rather than overshoot. Spend cannot be undone."""
        if self.limit_usd is None:
            return
        if self.spent_usd + self.estimated_next_call_usd > self.limit_usd:
            raise BudgetExhausted(
                spent_usd=self.spent_usd,
                limit_usd=self.limit_usd,
                completed=self.calls,
            )

    def charge(self, completion: Completion) -> float:
        """Record what the call ACTUALLY cost, from the tokens it reported.

        A completion reporting zero tokens is charged zero rather than the
        estimate. That is honest - we do not know what it cost - and it is
        also the case worth watching, because a provider that stops reporting
        usage silently disables this cap. `unmetered_calls` counts them so the
        condition is visible instead of inferred from a suspiciously low total.
        """
        cost = self.cost_of(completion.input_tokens, completion.output_tokens)
        self.spent_usd += cost
        self.calls += 1
        self._by_model[completion.model] = self._by_model.get(completion.model, 0.0) + cost
        if completion.input_tokens == 0 and completion.output_tokens == 0:
            self.unmetered_calls += 1
        return cost

    @property
    def spend_by_model(self) -> dict[str, float]:
        """Rule 7: a total with no breakdown hides a model swap.

        If `extractor_model` changed mid-run, one figure cannot say so.
        """
        return dict(self._by_model)

    def summary(self) -> str:
        if self.limit_usd is None:
            body = f"${self.spent_usd:.4f} over {self.calls} calls, no cap configured"
        else:
            body = f"${self.spent_usd:.4f} of ${self.limit_usd:.2f} over {self.calls} calls"
        if self.unmetered_calls:
            body += (
                f"; {self.unmetered_calls} call(s) reported no token usage and "
                f"are charged as zero, so this total is a floor"
            )
        return body
