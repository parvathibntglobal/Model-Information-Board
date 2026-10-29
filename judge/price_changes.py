"""The price changelog: OpenRouter list-price changes, with fixed flags (2026-10-27).

Signed-in only (GET /admin/price-changes). It reads `pricing_history`, which
collect/registry/events.py appends to only when a registry model's price moves
between two polls, and `model_version` for names and when each model was last
polled. Nothing here writes.

ONE SOURCE. Every price is OpenRouter's list price as we observed it; a change
is "seen on OpenRouter", never "the provider's price" (contract/price_changes.yaml
says why). `confirmed` is false on every row: no step confirms a change against
the provider's own page yet, and the page says so.

EVERY FLAG IS A FIXED RULE over two observed prices (rule 3: nothing scored,
nothing guessed). The thresholds are contract/price_changes.yaml's, never
defaulted here (rule 12):

    cut / rise   the largest of the input and output moves is at least
                 `big_change_pct`, down / up
    free         both prices went to 0 from something above 0
    wave         `wave_min_models` or more of one provider's models changed
                 the same UTC day. A LABEL, never a trigger (review on #579,
                 2026-10-28): it mostly measures OpenRouter repricing in bulk.
                 `wave_size` says how many.
    settling     not yet held `hold_hours`: the model changed again within that
                 time, or has not been polled that long since
    unpolled     the model's newest change could not settle because the poll
                 stopped seeing the model: its last poll is more than
                 `unpolled_hours` older than the newest poll of any model. Not
                 "settling", which would say we are waiting for something.
    bounced      the model's next change, within `bounce_days`, put it back to
                 the price it had before
    unstable     `unstable_changes` or more changes inside `unstable_days`:
                 a price flipping between hosts or promotions
    reverted     a later price inside `settle_days` came back near the
                 SETTLED price (below) - the move did not last
    superseded   a later change that has held moved on from the same settled
                 price: one move in two steps, told by the later one

    newsworthy   held (not settling, unpolled or bounced), not unstable,
                 reverted or superseded, and a move of at least
                 `big_change_pct` FROM THE SETTLED PRICE, or now free.

THE SETTLED PRICE (2026-10-29, Parvathi). A move used to be measured from the
price just before it, so a router's price flipping $0.15 -> $0.045 -> $0.15 made
the last step "+233%" and newsworthy, though over the week nothing changed.
Now `settled_before` is the price that held `settle_days` before the change
(or the first price seen), `settled_pct` the move from it, and `newsworthy` is
decided on that. cut / rise still describe the step itself, as before.

"LAST POLLED" IS `model_version.updated_at`, read for `unpolled` and as the
newest poll of any model. The registry poll is not its only writer: the loaders'
upsert (collect/registry/load.py, `updated_at = now()`) and recompute-window
(when a model's `in_window` flips) set it too, so a delisted model whose
`in_window` flipped would look freshly polled. The catalogue's `last_seen_at`
(collect/registry/catalog.py: "the latest poll that listed it", written by the
poll alone) is the exact signal. Moving to it is a follow-up, and it adds this
module to the list of catalogue readers its tests allow.

A percentage is the plain change between the two observed prices, shown beside
both of them; a price that was 0 or not stated has none (rule 6).
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

FIELDS = ("price_in", "price_out", "price_cached_read")


class PriceChangesContractError(RuntimeError):
    """contract/price_changes.yaml is missing something this refuses to default."""


def rules() -> dict[str, Any]:
    """The contract, validated. Every key required; nothing defaulted."""
    from judge.config import _read

    raw = _read("price_changes.yaml") or {}
    try:
        out = {
            "big_change_pct": float(raw["big_change_pct"]),
            "hold_hours": float(raw["hold_hours"]),
            "bounce_days": float(raw["bounce_days"]),
            "wave_min_models": int(raw["wave_min_models"]),
            "unpolled_hours": float(raw["unpolled_hours"]),
            "settle_days": float(raw["settle_days"]),
            "unstable_changes": int(raw["unstable_changes"]),
            "unstable_days": float(raw["unstable_days"]),
            "near_zero_price": float(raw["near_zero_price"]),
            "default_window_days": int(raw["default_window_days"]),
            "max_window_days": int(raw["max_window_days"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise PriceChangesContractError(
            f"contract/price_changes.yaml is missing or malformed at {exc}. Every "
            "threshold is required; a defaulted one would flag changes on a number "
            "nobody chose.") from exc
    if out["big_change_pct"] <= 0:
        raise PriceChangesContractError("need big_change_pct > 0")
    if out["hold_hours"] <= 0 or out["bounce_days"] <= 0 or out["wave_min_models"] < 2:
        raise PriceChangesContractError(
            "hold_hours and bounce_days must be positive, wave_min_models at least 2")
    if out["settle_days"] <= 0 or out["unstable_days"] <= 0 or out["unstable_changes"] < 2:
        raise PriceChangesContractError(
            "settle_days and unstable_days must be positive, unstable_changes at least 2")
    if out["near_zero_price"] <= 0:
        raise PriceChangesContractError("need near_zero_price > 0")
    if out["unpolled_hours"] < out["hold_hours"]:
        raise PriceChangesContractError("need unpolled_hours >= hold_hours")
    if not 0 < out["default_window_days"] <= out["max_window_days"]:
        raise PriceChangesContractError("need 0 < default_window_days <= max_window_days")
    return out


def _num(v: Any) -> float | None:
    return None if v is None else float(v if not isinstance(v, Decimal) else v)


def pct(old: float | None, new: float | None) -> float | None:
    """The change from `old` to `new` in percent; None when either is unknown
    or `old` is 0 (no percentage of nothing)."""
    if old is None or new is None or old == 0:
        return None
    return round((new - old) / old * 100, 1)


def _largest(moves: list[float | None]) -> float | None:
    known = [m for m in moves if m is not None]
    return max(known, key=abs) if known else None


HISTORY_SQL = (
    "SELECT ph.model_version_id, ph.observed_at, ph.price_in, ph.price_out, "
    "       ph.price_cached_read, mv.canonical_id, mv.display_name, mv.provider, "
    "       mv.updated_at "
    "FROM pricing_history ph JOIN model_version mv ON mv.id = ph.model_version_id "
    "ORDER BY ph.model_version_id, ph.observed_at"
)

# The population (rule 7) and the newest poll of any model, which "unpolled" is
# measured from - so a late or skipped poll run never makes every model unpolled.
REGISTRY_SQL = "SELECT count(*), max(updated_at) FROM model_version"


def changes(conn: Any, *, days: int | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Every price change seen in the window, newest first, with its flags."""
    r = rules()
    window = (r["default_window_days"] if days is None
              else max(1, min(int(days), r["max_window_days"])))
    now = now or datetime.now(UTC)
    since = now - timedelta(days=window)

    by_model: dict[str, list[tuple]] = {}
    for row in conn.execute(HISTORY_SQL).fetchall():
        by_model.setdefault(row[0], []).append(row)
    registry_models, newest_poll = conn.execute(REGISTRY_SQL).fetchone()

    out: list[dict[str, Any]] = []
    for rows in by_model.values():
        for i in range(1, len(rows)):
            prev, cur = rows[i - 1], rows[i]
            nxt = rows[i + 1] if i + 1 < len(rows) else None
            seen = cur[1]
            if seen < since:
                continue
            before = {f: _num(prev[2 + k]) for k, f in enumerate(FIELDS)}
            after = {f: _num(cur[2 + k]) for k, f in enumerate(FIELDS)}
            moves = {f: pct(before[f], after[f]) for f in FIELDS}
            largest = _largest([moves["price_in"], moves["price_out"]])

            # Held: no further change within hold_hours, and (for the newest change)
            # the model has been polled at least that long since.
            held_until = nxt[1] if nxt is not None else (cur[8] or seen)
            settled = (held_until - seen) >= timedelta(hours=r["hold_hours"])
            bounced = bool(
                nxt is not None
                and (nxt[1] - seen) <= timedelta(days=r["bounce_days"])
                and all(_num(nxt[2 + k]) == before[f] for k, f in enumerate(FIELDS)))
            free = (after["price_in"] == 0 and after["price_out"] == 0
                    and ((before["price_in"] or 0) > 0 or (before["price_out"] or 0) > 0))

            flags = []
            if largest is not None and largest <= -r["big_change_pct"]:
                flags.append("cut")
            if largest is not None and largest >= r["big_change_pct"]:
                flags.append("rise")
            if free:
                flags.append("free")
            unpolled = bool(
                not settled and nxt is None and cur[8] is not None and newest_poll is not None
                and (newest_poll - cur[8]) > timedelta(hours=r["unpolled_hours"]))
            if unpolled:
                flags.append("unpolled")
            elif not settled:
                flags.append("settling")
            if bounced:
                flags.append("bounced")

            # The settled price: what held settle_days before this change, or
            # the first price seen. The move that decides `newsworthy`.
            settle = timedelta(days=r["settle_days"])
            prior = [row for row in rows[:i] if row[1] <= seen - settle]
            base = prior[-1] if prior else rows[0]
            settled_before = {f: _num(base[2 + k]) for k, f in enumerate(FIELDS)}
            settled_moves = {f: pct(settled_before[f], after[f]) for f in FIELDS}
            main = max(
                (f for f in ("price_in", "price_out") if settled_moves[f]),
                key=lambda f: abs(settled_moves[f]),
                default=None,
            )
            recent = [
                row for row in rows[1:i + 1] if row[1] > seen - timedelta(days=r["unstable_days"])
            ]
            if len(recent) >= r["unstable_changes"]:
                flags.append("unstable")
            if main is not None:
                k_main = FIELDS.index(main)
                for later in rows[i + 1:]:
                    if later[1] > seen + settle:
                        break
                    back = pct(settled_before[main], _num(later[2 + k_main]))
                    if back is None or abs(back) < r["big_change_pct"]:
                        flags.append("reverted")
                        break
            out.append({
                "model_version_id": cur[0],
                "canonical_id": cur[5],
                "name": cur[6] or cur[5] or cur[0],
                "provider": cur[7],
                "seen_at": seen.isoformat(),
                "before": before,
                "after": after,
                "change_pct": moves,
                "largest_pct": largest,
                "settled_before": settled_before,
                "settled_pct": settled_moves,
                "settled_field": main,
                "settled_largest_pct": settled_moves[main] if main else None,
                "flags": flags,
                "wave_size": None,
                "source": "openrouter",
                "confirmed": False,
            })

    # A provider wave: enough of one provider's models moved the same UTC day.
    day_of = lambda c: (c["provider"], c["seen_at"][:10])  # noqa: E731
    waves = Counter(day_of(c) for c in out)
    for c in out:
        if c["provider"] and waves[day_of(c)] >= r["wave_min_models"]:
            c["flags"].append("wave")
            c["wave_size"] = waves[day_of(c)]

    # One move in two steps ($0.14 -> $0.03 -> $0.021 from the same settled
    # price) is told once, by its latest step that has HELD - a newer step still
    # settling does not hide the move that already held.
    latest: dict[tuple, str] = {}
    for c in out:
        if {"settling", "unpolled", "bounced"} & set(c["flags"]):
            continue
        same = (c["model_version_id"], tuple(c["settled_before"].values()))
        latest[same] = max(latest.get(same, ""), c["seen_at"])
    for c in out:
        if c["seen_at"] < latest.get(
                (c["model_version_id"], tuple(c["settled_before"].values())), ""):
            c["flags"].append("superseded")

    for c in out:
        held = not {"settling", "unpolled", "bounced", "unstable", "reverted", "superseded"} & set(
            c["flags"])
        big = c["settled_largest_pct"] is not None and abs(c["settled_largest_pct"]) >= r[
            "big_change_pct"]
        c["newsworthy"] = held and (big or "free" in c["flags"])

    out.sort(key=lambda c: c["seen_at"], reverse=True)
    return {
        "window_days": window,
        "rules": r,
        "changes": out,
        "counts": {
            "changes": len(out),
            "newsworthy": sum(c["newsworthy"] for c in out),
            "models": len({c["model_version_id"] for c in out}),
        },
        # Rule 7: what the counts are counted over. Registry models only; the
        # wider catalogue keeps current prices, no history (phase 2).
        "population": {
            "models_with_history": len(by_model),
            "registry_models": registry_models,
        },
        "source": "OpenRouter list prices, as observed by the registry poll",
        "newest_poll_at": newest_poll.isoformat() if newest_poll else None,
        "newest_seen_at": out[0]["seen_at"] if out else None,
    }
