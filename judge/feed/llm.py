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
            },
            timeout=httpx.Timeout(180.0, connect=10.0),
        )
    except httpx.HTTPError as e:
        raise FeedModelUnavailable(f"OpenRouter could not be reached: {e}") from e
    if r.status_code != 200:
        raise FeedModelUnavailable(f"OpenRouter HTTP {r.status_code}: {r.text[:300]!r}")
    body = r.json()
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
