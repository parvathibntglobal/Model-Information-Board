"""Total spent on the OpenRouter key, by anyone, straight from the provider.

Everything else on the usage page comes from `judge/spend_ledger.py`, which is a
local file. The API key is not local. So the rest of that page is one machine's
share of a key several people spend from - measured 2026-08-20, our ledger held
$0.000000 while the key reported $0.0089013.

This module reads USAGE and nothing else. It deliberately does not read or report
the provider's limits: their account credit and per-key cap are different
ceilings on a different schedule, ours is `EXTRACTION_DAILY_BUDGET_USD`, and
restating theirs was tried and removed. Usage answers who spent it, which is the
question. Limits are not ours to state.

It returns TOTALS ONLY - no stage split, no per-model split, no series. So it
answers a different question from the ledger rather than replacing it: this is
the whole-key denominator, the ledger is the detail for this machine.

A metadata call: zero tokens, no inference, $0.00.

UNREACHABLE IS NOT ZERO. A provider we cannot reach must never render as a key
nobody has spent on - that is the most reassuring of the available readings, and
rule 6 forbids the conversion. `unavailable_because` carries the reason so a
caller has something to show instead of inventing one.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from judge.extract.client import DEFAULT_BASE_URL


@dataclass(frozen=True)
class KeyUsage:
    """Spend on the whole key. `None` anywhere means unknown, never zero."""

    total_usd: float | None
    today_usd: float | None
    unavailable_because: str | None = None

    @property
    def available(self) -> bool:
        return self.unavailable_because is None


def _unavailable(reason: str) -> KeyUsage:
    return KeyUsage(None, None, unavailable_because=reason)


def _num(data: dict, name: str) -> float | None:
    value = data.get(name)
    return float(value) if isinstance(value, (int, float)) else None


def fetch(*, api_key: str | None = None, base_url: str | None = None) -> KeyUsage:
    """Ask the provider what the key has spent in total. Metadata only, $0.00."""
    key = api_key if api_key is not None else os.getenv("OPENROUTER_API_KEY")
    if not key or not key.strip():
        return _unavailable(
            "OPENROUTER_API_KEY is not set, so the key's own usage cannot be read. "
            "This is not a statement that nothing has been spent."
        )

    url = base_url or os.getenv("OPENROUTER_BASE_URL", DEFAULT_BASE_URL)
    try:
        with httpx.Client() as client:
            response = client.get(
                f"{url}/key",
                headers={"Authorization": f"Bearer {key}"},
                timeout=15.0,
            )
            if response.status_code == 401:
                return _unavailable(
                    "the provider rejected the key, so total spend is unknown rather than zero."
                )
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return _unavailable(f"could not reach the provider: {exc}")

    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        return _unavailable("the provider returned a shape this code does not understand")

    return KeyUsage(total_usd=_num(data, "usage"), today_usd=_num(data, "usage_daily"))
