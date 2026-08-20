"""Ask-path spend, accumulated across requests so the cap can actually bind.

WHY THIS FILE EXISTS

`judge/app.py` checked a budget on every `/ask/understand` request and its
docstring said, correctly, that an uncapped ask box is *"a bill somebody
discovers monthly"*. Then it built the check one layer short of the defect it
had just named:

    budget = Budget.from_env()      # a NEW Budget, spent_usd = 0.0
    budget.check_before_call()      # 0.0 + 0.00208 > limit  ->  never true

Nothing called `charge()` on the ask path - `grep '[.]charge('` returned exactly
one hit, in `pipeline.py`, the extraction path. So the object was reconstructed
per request, the running total was always zero, and the 429 branch was
**unreachable for any limit above one call's estimate**. A cap with a status
code, a message and a test, that could not fire.

This is defect 4.4 in `docs/engineer-2-handover.md` - a check positioned where
it cannot fire - and it is the second time on this endpoint. The first version
had no check at all.

WHAT THIS GUARANTEES, AND WHAT IT DOES NOT

The total lives in a module-level object, so it survives across requests
**within one process**. That is the whole of the claim, and rule 7 applies to
it: the denominator is one worker.

    uvicorn judge.app:app                  1 process   -> the cap is the cap
    uvicorn judge.app:app --workers 4      4 processes -> 4 independent caps,
                                                          so up to 4x the limit

Running multiple workers therefore multiplies the ceiling rather than sharing
it, and no amount of care in this file changes that - a process-local total
cannot see another process. A true cap needs a shared store, which means a
column somebody else's lane owns, so it is named in
`docs/engineer-2-handover.md` §7 rather than implied here. **Deploying with
`--workers N` without that is a decision to raise the cap N-fold**, and this
paragraph exists so it is a decision rather than a surprise.

It is also in-memory: a restart resets the total. For a daily cap on a service
that restarts rarely that is a smaller error than no cap at all, and it is
stated rather than papered over.

NO CAP CONFIGURED IS NOT A CAP

`Budget.from_env()` returns `None` when `EXTRACTION_DAILY_BUDGET_USD` is
unset, deliberately, so a caller "must decide" rather than inherit an
unlimited budget from a forgotten variable (rule 6 on our own config).

`judge/cli.py` may reasonably read that as an operator's choice - a person
typed the command. **An anonymous HTTP request is not a person who decided.**
There is no authentication on this API, so an unconfigured cap on a public LLM
endpoint is an open spend surface, and the two callers must answer the same
`None` differently. `is_configured` exists so the HTTP layer can refuse
instead of running uncapped.
"""

from __future__ import annotations

from judge.extract.budget import Budget, BudgetExhausted


class _Unset:
    """Distinct from `None`, which already means "configured as uncapped"."""


#: The process-local total. Rebuilt only by `reset_for_test`, so ordinary
#: request handling cannot accidentally zero it - which is the bug this module
#: was written to fix, and re-introducing it would look like ordinary code.
_BUDGET: Budget | None | type[_Unset] = _Unset
_CONFIGURED: bool | None = None


def _ensure() -> None:
    """Read the environment on FIRST USE, not at import.

    Not a style preference. `run-backend.py` populates `os.environ` and only
    then imports uvicorn, precisely so the app sees it - but
    `docs/frontend-handoff.md` also documents starting this service as plain
    `uvicorn judge.app:app`, and `collect/config.py` loads `.env` lazily from
    its own entry points. An import-time read makes the cap depend on which
    module got imported first, and that is not a property anybody can see when
    it goes wrong: the endpoint would answer 503 forever on a machine where the
    cap IS configured, and the message would say the cap is missing.

    It fails closed rather than open, which is the right direction, and closed
    with a misleading reason is still a defect. Reading on first use removes
    the ordering question entirely.
    """
    global _BUDGET, _CONFIGURED
    if _BUDGET is _Unset:
        _BUDGET = Budget.from_env()
        _CONFIGURED = _BUDGET is not None


def is_configured() -> bool:
    """True when a cap is configured. Callers decide what `False` means.

    The CLI treats it as an operator's choice - a person typed the command; the
    HTTP layer refuses, because an anonymous request is not a person who
    decided. Same fact, different authority behind it.
    """
    _ensure()
    return bool(_CONFIGURED)


def check_before_call() -> None:
    """Raise `BudgetExhausted` rather than overshoot. Spend cannot be undone.

    A no-op when no cap is configured - the refusal for that case belongs to
    the caller, which knows whether a person chose it.
    """
    _ensure()
    if _BUDGET is None:
        return
    _BUDGET.check_before_call()


def charge(*, input_tokens: int, output_tokens: int, model: str) -> float:
    """Record what a call ACTUALLY cost, from the tokens it reported.

    **This is the half that was missing.** Without it every check above reads a
    total of zero forever.
    """
    _ensure()
    if _BUDGET is None:
        return 0.0
    from judge.extract.client import Completion

    return _BUDGET.charge(
        Completion(
            raw_arguments="{}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
        )
    )


def summary() -> str:
    """What has been spent, or that nothing is capping it. Never a bare zero.

    A caller rendering "$0.0000 spent" for an unconfigured cap would state the
    most reassuring of the two possible readings, which is rule 6's display
    side on our own telemetry.
    """
    _ensure()
    if _BUDGET is None:
        return "no ask-path cap configured; nothing is counting this endpoint's spend"
    return f"ask path: {_BUDGET.summary()} (one process; see judge/ask/spend.py)"


def spent_usd() -> float | None:
    """`None` when uncapped - not `0.0`, which would read as "nothing spent"."""
    _ensure()
    return None if _BUDGET is None else _BUDGET.spent_usd


def reset_for_test(*, limit_usd: float | None, configured: bool = True) -> None:
    """Rebuild the module total. Tests only.

    Named so it cannot be mistaken for request-path code: the bug this module
    fixes was a fresh Budget per request, and a plausibly-named reset helper is
    exactly how that returns.
    """
    global _BUDGET, _CONFIGURED
    _BUDGET = None if not configured else Budget(limit_usd=limit_usd)
    _CONFIGURED = configured


__all__ = [
    "BudgetExhausted",
    "charge",
    "check_before_call",
    "is_configured",
    "reset_for_test",
    "spent_usd",
    "summary",
]
