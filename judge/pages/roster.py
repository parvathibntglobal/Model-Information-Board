"""The registry as a list, with what the provider advertises about each model.

WHY THIS IS SEPARATE FROM EVERY OTHER PAGE IN THIS PACKAGE.

Nothing here is evidence. Price, context window and feature flags are what a
vendor publishes about itself. They pass through no gate, they have no voices
behind them, and no amount of them makes a model recommendable. A capability
page answers "what have people found out"; this answers "what is on the tin",
and the two must never be shown as though they were the same kind of claim.

It exists because the board had no way to list models at all - `/models/{id}`
answers about one model you already know the id of, so the frontend was
reconstructing the roster from a capability page and taking twelve round trips
to do it.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# Ordered by display_name rather than by price. A default sort by cost would
# be this module quietly making the recommendation the rest of the system
# refuses to make without evidence.
SQL = """
    SELECT id,
           display_name,
           provider,
           canonical_id,
           price_in,
           price_out,
           price_cached_read,
           advertised_context,
           max_output_tokens,
           supports_tools,
           supports_vision,
           supports_structured_output,
           supports_caching,
           lifecycle
      FROM model_version
     ORDER BY display_name
"""

PRICED_AT_SQL = "SELECT max(observed_at) FROM pricing_history"


def _num(v: Decimal | None) -> float | None:
    """NULL survives as None. It is not zero.

    Five models in the registry are routers - Auto Router, OpenRouter: Fusion -
    which dispatch to other models and therefore have no rate of their own.
    Ten others are genuinely free. Collapsing NULL to 0.0 here would tell a
    reader those fifteen are the same thing, and would put the word "free" on
    five models that will bill them.
    """
    return None if v is None else float(v)


@dataclass(frozen=True)
class Roster:
    models: list[dict]
    priced_at: str | None
    summary: str


class RosterReader:
    def __init__(self, conn) -> None:
        self._conn = conn

    def all(self) -> Roster:
        rows = self._conn.execute(SQL).fetchall()
        models = [
            {
                "model_version_id": r[0],
                "display_name": r[1],
                "provider": r[2],
                "canonical_id": r[3],
                "price_in": _num(r[4]),
                "price_out": _num(r[5]),
                "price_cached_read": _num(r[6]),
                "advertised_context": r[7],
                "max_output_tokens": r[8],
                "supports_tools": r[9],
                "supports_vision": r[10],
                "supports_structured_output": r[11],
                "supports_caching": r[12],
                "lifecycle": r[13],
            }
            for r in rows
        ]

        observed = self._conn.execute(PRICED_AT_SQL).fetchone()[0]
        priced_at = observed.isoformat() if observed else None

        unpriced = sum(1 for m in models if m["price_in"] is None)
        summary = (
            f"{len(models)} models in the registry. Price and context are advertised "
            f"by the provider, not measured by us, and are not evidence of anything."
        )
        if unpriced:
            summary += (
                f" {unpriced} publish no rate at all - routers, which dispatch to "
                f"other models - and are shown as unpriced rather than as free."
            )

        return Roster(models=models, priced_at=priced_at, summary=summary)
