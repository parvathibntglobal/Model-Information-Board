"""The one model call the feed makes, for both the paraphraser and the summariser.

The quiz drafter's shape (judge/quiz_bank.py): OpenRouter, one forced tool
call, spend recorded BEFORE the answer is judged - an unusable answer is still
billed - at the cost OpenRouter reports, under the `feed` stage, outside the
daily extraction cap. A response from a model other than the one asked for is
refused: a substituted model is a different proposer than the one the contract
names (tests/test_the_served_model_is_not_the_asked_one.py says why).
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from judge import spend_ledger


class FeedModelUnavailable(RuntimeError):
    """The call could not be made, or its answer could not be read."""


class BudgetSpent(FeedModelUnavailable):
    """The run's spend cap was reached; this call was not made."""


#: What this process has spent on feed calls, in dollars at the cost OpenRouter
#: reported - what `capped` holds a scheduled run to. A call that reported no
#: cost adds nothing, so the figure is a floor and the run report says how many
#: calls that was (rule 6: an unreported cost is not a zero).
_spent = {"usd": 0.0, "calls": 0, "unreported": 0}


def spent() -> dict:
    return dict(_spent)


def count_spend(cost) -> None:
    """Add one call to the total; `call_tool` does this after each call."""
    _spent["calls"] += 1
    if isinstance(cost, (int, float)) and not isinstance(cost, bool):
        _spent["usd"] += float(cost)
    else:
        _spent["unreported"] += 1


def reset_spent() -> None:
    _spent.update(usd=0.0, calls=0, unreported=0)


#: A call whose response named no OpenRouter provider is counted under this,
#: never dropped and never given a name (rule 6). The extractor's summary uses
#: the same words (judge/scheduler.py PROVIDER_NOT_REPORTED).
PROVIDER_NOT_REPORTED = "not reported"

#: The OpenRouter provider that served the LAST `call_tool` call, read by
#: `paraphrase.run` to count reports per provider (#671). Reset at the start of
#: every call, so a call that failed before a response says "not reported"
#: rather than the previous call's provider. The feed's calls are serial.
_last = {"provider": None}


def last_provider() -> str:
    """The provider of the last call, or `PROVIDER_NOT_REPORTED`."""
    return _last["provider"] or PROVIDER_NOT_REPORTED


def clear_last_provider() -> None:
    """Forget it before a call that may not go through `call_tool` (a test's
    stand-in, or a cap that refuses first), so it is never the one before."""
    _last["provider"] = None


def capped(cap_usd: float, call=None):
    """`call_tool`, refusing to START a call once `cap_usd` has been spent.

    Checked before each call, not after, so a run can overshoot by the one call
    in flight (contract/evidence_feed.yaml `schedule`). The refusal is a
    FeedModelUnavailable, so every caller already treats it as a call that did
    not happen - and a BudgetSpent, so the run can stop rather than try the
    next batch and be refused again."""
    inner = call or call_tool

    def call_within_cap(**kwargs):
        if _spent["usd"] >= cap_usd:
            raise BudgetSpent(f"the run's ${cap_usd:.2f} cap is spent (${_spent['usd']:.4f})")
        return inner(**kwargs)

    return call_within_cap


def call_tool(
    *,
    model: str,
    system: str,
    user: str,
    tool: dict,
    run_id: str,
    max_tokens: int,
    reasoning_effort: str,
    temperature: float = 0.2,
) -> tuple[dict, str]:
    """`(the tool's arguments, the model that served it)`."""
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    base = os.getenv("OPENROUTER_BASE_URL", "").strip().rstrip("/")
    if not key or not base:
        raise FeedModelUnavailable("OPENROUTER_API_KEY and OPENROUTER_BASE_URL must both be set")
    name = tool["function"]["name"]
    # WHICH OPENROUTER HOST SERVES IT (2026-11-25): the extractor's preference, the
    # same EXTRACTOR_PROVIDER_SORT / _IGNORE variables, because it is the same model
    # and the same bad host. Replayed 2026-11-25, 4 batches of 20 reports each sent
    # to both: DeepInfra returned no paraphrase at all for 2 of the 4 batches and 22
    # of 80 passed the checks on the first attempt; Wafer, 41 of 80. Unset, OpenRouter
    # chooses, as before. An unknown sort is refused there (rule 12).
    from judge.extract.client import extractor_provider

    provider = extractor_provider()
    _last["provider"] = None
    try:
        r = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "tools": [tool],
                "tool_choice": {"type": "function", "function": {"name": name}},
                "usage": {"include": True},
                "temperature": temperature,
                "max_tokens": max_tokens,
                # contract/evidence_feed.yaml `reasoning_effort`; `none` turns thinking
                # off rather than hiding it (judge/extract/client.py says why).
                "reasoning": {"effort": reasoning_effort},
                **({"provider": provider} if provider else {}),
            },
            timeout=httpx.Timeout(180.0, connect=10.0),
        )
    except httpx.HTTPError as e:
        raise FeedModelUnavailable(f"OpenRouter could not be reached: {e}") from e
    if r.status_code != 200:
        raise FeedModelUnavailable(f"OpenRouter HTTP {r.status_code}: {r.text[:300]!r}")
    body = r.json()
    # WHO SERVED IT (#671): OpenRouter names the provider in the response body.
    # Set before any refusal below, so a provider that answers without the tool
    # is counted against itself.
    _last["provider"] = body.get("provider") if isinstance(body.get("provider"), str) else None
    usage = body.get("usage") or {}
    served = body.get("model") or ""
    spend_ledger.record(
        stage=spend_ledger.STAGE_FEED,
        model=served,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        reported=True,
        reported_usd=usage.get("cost"),
        run_id=run_id,
    )
    count_spend(usage.get("cost"))
    if not served.startswith(model):
        raise FeedModelUnavailable(
            f"asked for {model}, OpenRouter served {served!r}; refusing the answer"
        )
    calls = ((body.get("choices") or [{}])[0].get("message") or {}).get("tool_calls") or []
    if not calls:
        raise FeedModelUnavailable(f"the model answered without the {name} tool")
    try:
        args: Any = json.loads(calls[0]["function"]["arguments"])
    except (KeyError, ValueError) as e:
        raise FeedModelUnavailable(f"the tool arguments were not JSON: {e}") from e
    if not isinstance(args, dict):
        raise FeedModelUnavailable("the tool arguments were not an object")
    return args, served
