"""One forced tool call to a model through OpenRouter. Outreach's only model client.

Deliberately small and separate from judge/extract/client.py: outreach must not
import the board's code, and it needs none of the extractor's streaming
machinery, because an answer here is four short fields.

What it guarantees to its caller:

- FORCED TOOL CALL. `tool_choice` names the one tool, so the model has no
  free-text channel; an instruction hidden in a post cannot produce output
  that acts on anything (judge/CLAUDE.md, "extraction hardening").
- COST AS REPORTED, OR NONE. `usd` is OpenRouter's `usage.cost`. Absent, it is
  None - never 0, an unpriced call is not a free one (rule 6) - and
  common/spend.py then stops the day.
- TOKENS AS REPORTED, OR NONE. Same rule.
- An HTTP or provider failure RAISES `CallFailed` and nothing is recorded as
  an answer. Whether it cost anything is unknown, and the caller says so.

`OPENROUTER_API_KEY` and `USER_AGENT` (the one the Finders send) have no
fallback; `OPENROUTER_BASE_URL` defaults to OpenRouter's documented URL, the
same default MIB's extractor uses.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
TIMEOUT_SECONDS = 60.0


class CallFailed(RuntimeError):
    """No usable response came back. Whether it was billed is unknown."""


@dataclass(frozen=True)
class Answer:
    arguments: dict[str, Any] | None    # the tool call's arguments; None = no tool call
    problem: str | None                 # why `arguments` is None or unparseable
    model: str                          # the model that served it, as reported
    input_tokens: int | None
    output_tokens: int | None
    usd: Decimal | None
    hit_output_ceiling: bool


class Client(Protocol):
    def call(self, *, system: str, user: str, tool: dict[str, Any],
             max_output_tokens: int) -> Answer: ...


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def parse_response(body: dict[str, Any], *, tool_name: str, asked_model: str) -> Answer:
    """An OpenRouter chat completion body -> Answer. Pure; tested without a network."""
    if body.get("error"):
        raise CallFailed(f"provider error: {str(body['error'])[:300]}")
    usage = body.get("usage") or {}
    cost = usage.get("cost")
    usd = (Decimal(str(cost)) if isinstance(cost, (int, float)) and not isinstance(cost, bool)
           and cost >= 0 else None)
    choices = body.get("choices") or []
    if not choices:
        raise CallFailed("the response had no choices")
    choice = choices[0]
    msg = choice.get("message") or {}
    calls = [c for c in (msg.get("tool_calls") or [])
             if (c.get("function") or {}).get("name") == tool_name]
    arguments, problem = None, None
    if not calls:
        problem = "the model made no shortlist tool call"
    else:
        raw = calls[0]["function"].get("arguments")
        try:
            arguments = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            problem = f"the tool call's arguments are not JSON: {str(raw)[:200]}"
        if arguments is not None and not isinstance(arguments, dict):
            arguments, problem = None, "the tool call's arguments are not an object"
    return Answer(
        arguments=arguments, problem=problem,
        model=body.get("model") or asked_model,
        input_tokens=_int_or_none(usage.get("prompt_tokens")),
        output_tokens=_int_or_none(usage.get("completion_tokens")),
        usd=usd,
        hit_output_ceiling=choice.get("finish_reason") == "length",
    )


@dataclass
class OpenRouter:
    model: str
    api_key: str
    user_agent: str
    base_url: str = DEFAULT_BASE_URL

    @classmethod
    def from_env(cls, model: str) -> OpenRouter:
        key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
        if not key:
            raise CallFailed("OPENROUTER_API_KEY is not set in .env; no call was made")
        ua = (os.environ.get("USER_AGENT") or "").strip()
        if not ua:
            raise CallFailed("USER_AGENT is not set in .env; no call was made")
        return cls(model=model, api_key=key, user_agent=ua,
                   base_url=(os.environ.get("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"))

    def call(self, *, system: str, user: str, tool: dict[str, Any],
             max_output_tokens: int) -> Answer:
        import httpx

        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "tools": [{"type": "function", "function": tool}],
            "tool_choice": {"type": "function", "function": {"name": tool["name"]}},
            "temperature": 0,
            "max_tokens": max_output_tokens,
            "usage": {"include": True},      # without it there is no cost to record
        }
        try:
            r = httpx.post(f"{self.base_url}/chat/completions", json=payload,
                           headers={"Authorization": f"Bearer {self.api_key}",
                                    "User-Agent": self.user_agent},
                           timeout=httpx.Timeout(TIMEOUT_SECONDS, connect=10.0))
        except httpx.HTTPError as exc:
            raise CallFailed(f"{type(exc).__name__}: {exc}") from None
        if r.status_code != 200:
            raise CallFailed(f"HTTP {r.status_code}: {r.text[:300]}")
        try:
            body = r.json()
        except ValueError:
            raise CallFailed(f"the response is not JSON: {r.text[:200]}") from None
        return parse_response(body, tool_name=tool["name"], asked_model=self.model)
