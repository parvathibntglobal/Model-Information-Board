"""THE UPDATES PAGE (2026-10-29, Parvathi): signed in. Short headlines about
what changed - launches, price cuts and rises, retirements, benchmark results -
each with a one-line detail, built from data the board already holds.

TWO SECTIONS, ONE LIST. News headlines shows every update that is not
declined; Manage lists the same updates with what people decided about them.
An update is published as soon as it is built (auto-publish); approving it
records that a person checked it, declining it hides it.

AN UPDATE IS NEVER STORED. `build()` rebuilds every update from its sources on
each read:
  launch      model_event 'new-model' + its model_version row
  price       judge/price_changes.changes(), `newsworthy` only (its contract
              holds the 20% rule, the hold and the bounce check)
  retiring    model_version.retirement_date
  benchmark   judge/benchmarks.changelog() news tags
Only a person's decisions are stored (update_review, migration 20261029T1200),
by the update's `key`. A key names the update's facts - the model, the poll that
saw a price, the benchmark change - so a new fact is a new update, and a
decision is never carried onto words it was not made about.

CODE TEMPLATES, NO WRITER. Headlines and details are contract/updates.yaml
templates filled with str.format from the facts below. A style that needs a
fact the update does not have is not offered for it.

AN EDIT IS CHECKED FOR NUMBERS. A person's own words may not bring in a number
the update's facts do not hold unless they confirm it (`EditNeedsConfirm`).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import string
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from psycopg import errors

KINDS = ("launch", "price_cut", "price_rise", "price_change", "retiring", "benchmark", "roundup")

#: The facts each template set may name. A template naming anything else is a
#: contract error (rules(); tests/test_updates.py).
FACTS: dict[str, frozenset[str]] = {
    "launch": frozenset({"name", "provider", "date", "context", "pricing", "unlisted"}),
    "launch_group": frozenset({"provider", "count", "names", "names_short", "date"}),
    "price_cut": frozenset(
        {
            "name",
            "provider",
            "date",
            "main_field",
            "main_before",
            "main_after",
            "before_in",
            "after_in",
            "before_out",
            "after_out",
        }
    ),
    "price_free": frozenset({"name", "provider", "date", "before_in", "before_out"}),
    # One price down and the other up: never called cheaper or pricier.
    "price_mixed": frozenset(
        {
            "name",
            "provider",
            "date",
            "in_word",
            "out_word",
            "before_in",
            "after_in",
            "before_out",
            "after_out",
        }
    ),
    "price_cut_group": frozenset(
        {"provider", "count", "names", "names_short", "date", "price_list"}
    ),
    "retiring": frozenset({"name", "provider", "date", "date_full", "when"}),
    "retiring_group": frozenset(
        {"provider", "count", "names", "names_short", "date", "date_full", "when"}
    ),
    "bench_debut": frozenset({"name", "board", "score", "date", "timing"}),
    "bench_debut_group": frozenset({"name", "count", "boards", "date", "timing"}),
    "bench_top": frozenset({"name", "board", "old_rank", "out_of", "date"}),
    "bench_mover": frozenset({"name", "board", "moves", "old", "new", "delta", "date"}),
    "bench_fresh": frozenset({"name", "board", "score", "source_date", "date"}),
    "roundup_launch": frozenset({"week", "count", "long_context", "providers", "names"}),
    "roundup_price": frozenset(
        {"week", "count", "cuts", "rises", "cheaper", "pricier", "providers"}
    ),
}
FACTS["price_rise"] = FACTS["price_cut"]
FACTS["price_rise_group"] = FACTS["price_cut_group"]
FACTS["retired"] = FACTS["retiring"]
FACTS["retired_group"] = FACTS["retiring_group"]

STATUSES = ("pending", "approved", "declined")
ACTIONS = ("approve", "decline", "restore", "style", "edit", "publish", "unpublish")
#: What can still be done to an update that is no longer in the data (its facts
#: changed, so it is no longer built): take it off the home page, or hide it.
GONE_ACTIONS = ("unpublish", "decline")
HEADLINE_MAX = 160
DETAIL_MAX = 300


class UpdatesContractError(RuntimeError):
    """contract/updates.yaml is missing something, or a template names a fact
    its set does not have."""


class ReviewRefused(ValueError):
    """A review that cannot be applied: unknown update, style or action."""

    def __init__(self, detail: str, status: int = 422):
        super().__init__(detail)
        self.status = status


class EditNeedsConfirm(ValueError):
    """An edit brings in numbers the update's facts do not hold."""

    def __init__(self, numbers: list[str]):
        super().__init__(
            "These numbers are not in this update's facts: "
            + ", ".join(numbers)
            + ". Check them, then save again to confirm."
        )
        self.numbers = numbers


class SavingUnavailable(RuntimeError):
    """The review tables are not in this database, or it is read-only here."""


# ── the contract ─────────────────────────────────────────────────────────────


def _fields(text: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


def rules() -> dict[str, Any]:
    """contract/updates.yaml, validated. Every key required; nothing defaulted."""
    from judge.config import _read

    raw = _read("updates.yaml") or {}
    try:
        out = {
            "window_days": int(raw["window_days"]),
            "max_window_days": int(raw["max_window_days"]),
            "home_days": int(raw["home_days"]),
            "home_limit": int(raw["home_limit"]),
            "home_cache_seconds": int(raw["home_cache_seconds"]),
            "second_check_pct": float(raw["second_check_pct"]),
            "mixed_move_pct": float(raw["mixed_move_pct"]),
            "retiring_ahead_days": int(raw["retiring_ahead_days"]),
            "retired_back_days": int(raw["retired_back_days"]),
            "group_min": int(raw["group_min"]),
            "names_shown": int(raw["names_shown"]),
            "why_by_set": {str(k): str(v) for k, v in raw["why_by_set"].items()},
            "set_labels": {name: str(raw["set_labels"][name]) for name in FACTS},
            "roundups": {
                "min_items": int(raw["roundups"]["min_items"]),
                "providers_shown": int(raw["roundups"]["providers_shown"]),
                "long_context_tokens": int(raw["roundups"]["long_context_tokens"]),
            },
            "kinds": {
                k: {f: str(raw["kinds"][k][f]) for f in ("label", "why", "source")} for k in KINDS
            },
            "templates": {
                name: [
                    {f: str(s[f]) for f in ("id", "label", "headline", "detail")}
                    for s in raw["templates"][name]
                ]
                for name in FACTS
            },
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise UpdatesContractError(
            f"contract/updates.yaml is missing or malformed at {exc}. Every key is "
            "required; a defaulted one would publish words nobody chose."
        ) from exc
    if not 0 < out["window_days"] <= out["max_window_days"]:
        raise UpdatesContractError("need 0 < window_days <= max_window_days")
    if out["home_days"] < 1 or out["home_limit"] < 1 or out["home_cache_seconds"] < 0:
        raise UpdatesContractError(
            "need home_days >= 1, home_limit >= 1 and home_cache_seconds >= 0"
        )
    if out["group_min"] < 2 or out["names_shown"] < 1:
        raise UpdatesContractError("need group_min >= 2 and names_shown >= 1")
    unknown = set(out["why_by_set"]) - set(FACTS)
    if unknown:
        raise UpdatesContractError(f"why_by_set names sets that do not exist: {sorted(unknown)}")
    for name, styles in out["templates"].items():
        if not styles:
            raise UpdatesContractError(f"templates.{name} has no style")
        ids = [s["id"] for s in styles]
        if len(set(ids)) != len(ids):
            raise UpdatesContractError(f"templates.{name} repeats a style id")
        for s in styles:
            extra = (_fields(s["headline"]) | _fields(s["detail"])) - FACTS[name]
            if extra:
                raise UpdatesContractError(
                    f"templates.{name}.{s['id']} names {sorted(extra)}, which that set "
                    "does not have (judge/updates.py FACTS)"
                )
    return out


# ── how facts are written ───────────────────────────────────────────────────


def _num(v: Any) -> float | None:
    return None if v is None else float(v if not isinstance(v, Decimal) else v)


def money(v: Any) -> str | None:
    """A price per million tokens: "$0.25", "$0.889", "free". None stays None."""
    v = _num(v)
    if v is None:
        return None
    if v == 0:
        return "free"
    if 0 < v < 0.01:
        return f"${v:.2g}"
    if round(v, 2) == v:
        return f"${v:.2f}"
    return "$" + f"{v:.4f}".rstrip("0")


def context(n: Any) -> str | None:
    """A context window: 1048576 -> "1M", 262144 -> "256K", 1050000 -> "1.05M"."""
    if not n:
        return None
    n = int(n)
    if n % 1024 == 0 and n >= 1024:
        k = n // 1024
        return f"{k // 1024}M" if k % 1024 == 0 else f"{k}K"
    if n >= 1_000_000:
        return f"{round(n / 1_000_000, 2):g}M"
    return f"{round(n / 1000):g}K"


def day(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"


def day_full(d: date) -> str:
    return f"{d.day} {d.strftime('%b %Y')}"


def when(d: date, today: date) -> str:
    gap = (d - today).days
    if gap == 0:
        return "today"
    if gap == 1:
        return "tomorrow"
    if gap == -1:
        return "yesterday"
    return f"in {gap} days" if gap > 0 else f"{-gap} days ago"


def _direction_word(before: Any, after: Any) -> str | None:
    """ "down", "up" or "unchanged" for one price; None when either is unknown."""
    before, after = _num(before), _num(after)
    if before is None or after is None:
        return None
    return "down" if after < before else "up" if after > before else "unchanged"


def _unlisted(price: str | None, ctx: str | None) -> str | None:
    """What a new listing is missing, in words; None when it has both."""
    gaps = [w for w, v in (("price", price), ("context window", ctx)) if v is None]
    return f"no {' or '.join(gaps)} listed yet" if gaps else None


def launch_pricing(p_in: Any, p_out: Any) -> str | None:
    """A new model's list price as a sentence; None when either is not listed."""
    p_in, p_out = _num(p_in), _num(p_out)
    if p_in is None or p_out is None:
        return None
    if p_in == 0 and p_out == 0:
        return "It is free to use"
    return (
        f"It costs {money(p_in)} per million input tokens "
        f"and {money(p_out)} per million output tokens"
    )


def names(items: list[str], shown: int) -> str:
    if len(items) <= shown:
        return ", ".join(items[:-1]) + (" and " if len(items) > 1 else "") + items[-1]
    return ", ".join(items[:shown]) + f" and {len(items) - shown} more"


def split_name(display: str | None, canonical_id: str, provider: str | None) -> tuple[str, str]:
    """`OpenAI: GPT-6.1 Sol` -> ("OpenAI", "GPT-6.1 Sol"). Without the prefix the
    provider is its registry slug and the name the display name or the id."""
    text = (display or "").strip()
    if ": " in text:
        who, _, name = text.partition(": ")
        return who.strip(), name.strip()
    return (provider or canonical_id.split("/")[0]), (text or canonical_id)


def _digest(parts: list[str]) -> str:
    return hashlib.sha1("|".join(sorted(parts)).encode()).hexdigest()[:10]


# ── building the updates ────────────────────────────────────────────────────


def _story(
    *,
    key: str,
    kind: str,
    template: str,
    on: date,
    facts: dict[str, Any],
    models: list[str],
    second_check: bool = False,
    seen_at: str | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "kind": kind,
        "template": template,
        "date": on.isoformat(),
        "seen_at": seen_at,
        "facts": {k: v for k, v in facts.items() if v is not None},
        "models": models,
        "second_check": second_check,
    }


LAUNCH_SQL = (
    "SELECT DISTINCT ON (mv.id) mv.id, mv.canonical_id, mv.display_name, mv.provider, "
    "       COALESCE(mv.release_date, e.occurred_at::date), e.detected_at, "
    "       mv.advertised_context, mv.price_in, mv.price_out "
    "FROM model_event e JOIN model_version mv ON mv.id = e.model_version_id "
    "WHERE e.type = 'new-model' AND COALESCE(mv.release_date, e.occurred_at::date) >= %s "
    "ORDER BY mv.id, e.detected_at"
)


def _launches(rows: list[tuple], r: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, date], list[tuple]] = {}
    for row in rows:
        who, _ = split_name(row[2], row[1], row[3])
        groups.setdefault((who, row[4]), []).append(row)
    out = []
    for (who, on), members in groups.items():
        members.sort(key=lambda m: m[2] or m[1])
        ids = [m[1] for m in members]
        if len(members) >= r["group_min"]:
            labels = [split_name(m[2], m[1], m[3])[1] for m in members]
            out.append(
                _story(
                    key=f"launch-group:{who}:{on}:{_digest(ids)}",
                    kind="launch",
                    template="launch_group",
                    on=on,
                    facts={
                        "provider": who,
                        "count": len(members),
                        "names": names(labels, r["names_shown"]),
                        "names_short": names(labels, min(2, r["names_shown"])),
                        "date": day(on),
                    },
                    models=ids,
                    seen_at=max(m[5] for m in members).isoformat(),
                )
            )
            continue
        (_, cid, display, provider, _, seen, ctx, p_in, p_out) = members[0]
        out.append(
            _story(
                key=f"launch:{cid}",
                kind="launch",
                template="launch",
                on=on,
                facts={
                    "name": split_name(display, cid, provider)[1],
                    "provider": who,
                    "date": day(on),
                    "context": context(ctx),
                    "pricing": launch_pricing(p_in, p_out),
                    "unlisted": _unlisted(launch_pricing(p_in, p_out), context(ctx)),
                },
                models=[cid],
                seen_at=seen.isoformat(),
            )
        )
    return out


def _prices(
    conn, days: int, r: dict[str, Any], now: datetime
) -> tuple[list[dict[str, Any]], list[tuple[str, str, date, dict[str, Any]]]]:
    """The price updates, and each one as (kind, provider, day, change) for the
    weekly round-up. Prices are shown, never percentages: the settled price
    and the new one."""
    from judge import price_changes

    # The changelog decides what is news, measured from the SETTLED price
    # (judge/price_changes.py: unstable, reverted and superseded changes are
    # never newsworthy). Updates tells it in prices.
    data = price_changes.changes(conn, days=days, now=now)
    latest = []
    for c in data["changes"]:
        if not c["newsworthy"]:
            continue
        before = c["settled_before"]
        if "free" in c["flags"]:
            move = (
                "price_cut",
                "price_free",
                before["price_in"],
                before["price_out"],
                None,
                -100.0,
            )
        else:
            moved = c["settled_pct"]
            mixed = r["mixed_move_pct"]
            if (moved["price_in"] or 0) * (moved["price_out"] or 0) < 0 and min(
                abs(moved["price_in"]), abs(moved["price_out"])
            ) >= mixed:
                # Input down and output up (or the reverse), both by mixed_move_pct
                # or more: a price CHANGE, its own update, never "cheaper".
                kind, template = "price_change", "price_mixed"
            else:
                kind = "price_cut" if c["settled_largest_pct"] < 0 else "price_rise"
                template = kind
            move = (
                kind,
                template,
                before["price_in"],
                before["price_out"],
                c["settled_field"],
                c["settled_largest_pct"],
            )
        latest.append((c, move))
    groups: dict[tuple[str, str, date], list[tuple[dict[str, Any], tuple]]] = {}
    moves_seen: list[tuple[str, str, date, dict[str, Any]]] = []
    for c, move in latest:
        kind = move[0]
        on = datetime.fromisoformat(c["seen_at"]).astimezone(UTC).date()
        who, _ = split_name(c["name"], c["canonical_id"] or c["model_version_id"], c["provider"])
        # A model that became free is its own update, never folded into a group.
        # A model that became free, or whose prices moved apart, is its own
        # update; only plain cuts and rises are grouped.
        alone = move[1] in ("price_free", "price_mixed")
        group = (kind if not alone else f"{move[1]}:{c['model_version_id']}", who, on)
        groups.setdefault(group, []).append((c, move))
        moves_seen.append((kind, who, on, c))
    out = []
    for (_, who, on), members in groups.items():
        members.sort(key=lambda m: m[0]["name"] or "")
        kind = members[0][1][0]
        check = any(abs(m[1][5]) >= r["second_check_pct"] for m in members)
        seen = max(m[0]["seen_at"] for m in members)
        ids = [m[0]["canonical_id"] or m[0]["model_version_id"] for m in members]
        labels = [
            split_name(m[0]["name"], i, m[0]["provider"])[1]
            for m, i in zip(members, ids, strict=True)
        ]
        field = {"price_in": "input", "price_out": "output"}
        if len(members) >= r["group_min"]:
            lines = [
                f"{label}: input {money(m[1][2])} → {money(m[0]['after']['price_in'])}, "
                f"output {money(m[1][3])} → {money(m[0]['after']['price_out'])}"
                for m, label in zip(members, labels, strict=True)
            ]
            shown = r["names_shown"]
            price_list = "; ".join(lines[:shown]) + (
                f"; and {len(lines) - shown} more" if len(lines) > shown else ""
            )
            polls = [i + "@" + m[0]["seen_at"] for m, i in zip(members, ids, strict=True)]
            out.append(
                _story(
                    key=f"price-group:{kind}:{who}:{on}:{_digest(polls)}",
                    kind=kind,
                    template=f"{kind}_group",
                    on=on,
                    facts={
                        "provider": who,
                        "count": len(members),
                        "names": names(labels, r["names_shown"]),
                        "names_short": names(labels, min(2, r["names_shown"])),
                        "date": day(on),
                        "price_list": price_list,
                    },
                    models=ids,
                    second_check=check,
                    seen_at=seen,
                )
            )
            continue
        c, (_, template, base_in, base_out, main, _) = members[0]
        out.append(
            _story(
                key=f"price:{c['model_version_id']}:{c['seen_at']}",
                kind=kind,
                template=template,
                on=on,
                facts={
                    "name": labels[0],
                    "provider": who,
                    "date": day(on),
                    "main_field": field.get(main),
                    "main_before": money(base_in if main == "price_in" else base_out)
                    if main
                    else None,
                    "main_after": money(c["after"][main]) if main else None,
                    "in_word": _direction_word(base_in, c["after"]["price_in"]),
                    "out_word": _direction_word(base_out, c["after"]["price_out"]),
                    "before_in": money(base_in),
                    "after_in": money(c["after"]["price_in"]),
                    "before_out": money(base_out),
                    "after_out": money(c["after"]["price_out"]),
                },
                models=ids,
                second_check=check,
                seen_at=seen,
            )
        )
    return out, moves_seen


RETIRING_SQL = (
    "SELECT canonical_id, display_name, provider, retirement_date FROM model_version "
    "WHERE retirement_date BETWEEN %s AND %s"
)


def _retiring(conn, today: date, r: dict[str, Any]) -> list[dict[str, Any]]:
    rows = conn.execute(
        RETIRING_SQL,
        (
            today - timedelta(days=r["retired_back_days"]),
            today + timedelta(days=r["retiring_ahead_days"]),
        ),
    ).fetchall()
    groups: dict[tuple[str, date], list[tuple]] = {}
    for row in rows:
        who, _ = split_name(row[1], row[0], row[2])
        groups.setdefault((who, row[3]), []).append(row)
    out = []
    for (who, on), members in groups.items():
        members.sort(key=lambda m: m[1] or m[0])
        ids = [m[0] for m in members]
        past = on < today
        base = "retired" if past else "retiring"
        if len(members) >= r["group_min"]:
            labels = [split_name(m[1], m[0], m[2])[1] for m in members]
            out.append(
                _story(
                    key=f"retiring-group:{who}:{on}:{_digest(ids)}",
                    kind="retiring",
                    template=f"{base}_group",
                    on=on,
                    facts={
                        "provider": who,
                        "count": len(members),
                        "names": names(labels, r["names_shown"]),
                        "names_short": names(labels, min(2, r["names_shown"])),
                        "date": day(on),
                        "when": when(on, today),
                        "date_full": day_full(on),
                    },
                    models=ids,
                )
            )
            continue
        cid, display, provider, _ = members[0]
        out.append(
            _story(
                key=f"retiring:{cid}:{on}",
                kind="retiring",
                template=base,
                on=on,
                facts={
                    "name": split_name(display, cid, provider)[1],
                    "provider": who,
                    "date": day(on),
                    "when": when(on, today),
                    "date_full": day_full(on),
                },
                models=[cid],
            )
        )
    return out


def _model_of(row_id: str) -> str:
    return row_id.split(":")[0].split("@")[0]


def _rank(text: Any) -> int | None:
    m = re.search(r"\d+", str(text or ""))
    return int(m.group()) if m else None


def _score(text: Any) -> float | None:
    try:
        return float(str(text).replace(",", "").rstrip("%"))
    except (TypeError, ValueError):
        return None


def bench_news(bench_conn, since: date) -> list[dict[str, Any]]:
    """Every benchmarks changelog entry tagged as news on or after `since`,
    newest first, reading older runs until they fall out of the window."""
    from judge import benchmarks

    out, before = [], None
    while True:
        page = benchmarks.changelog(bench_conn, kind="news", before_run=before)
        if not page["entries"] and not page["more"]:
            break
        fresh = [e for e in page["entries"] if (benchmarks._day(e["changed_at"]) or since) >= since]
        out.extend(fresh)
        if not page["more"] or len(fresh) < len(page["entries"]) or page["older_than"] is None:
            break
        before = page["older_than"]
    return out


def _row_name(e: dict[str, Any], display: dict[str, str]) -> str:
    """The row's label; for a row the board has no label for (its label is the
    row id, "x-ai/grok-4.5:xhigh"), the registry's name and the setting."""
    if "/" not in e["row"]:
        return e["row"]
    model = _model_of(e["row_id"])
    setting = e["row_id"][len(model) :].lstrip(":@")
    name = (
        split_name(display.get(model), model, None)[1] if model in display else model.split("/")[-1]
    )
    return f"{name} ({setting})" if setting else name


def _is_rank(e: dict[str, Any]) -> bool:
    return e.get("old_out_of") is not None or e.get("new_out_of") is not None


def _benchmarks(
    entries: list[dict[str, Any]],
    released: dict[str, date],
    display: dict[str, str],
    r: dict[str, Any],
) -> list[dict[str, Any]]:
    from judge import benchmarks

    out = []
    debuts: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for e in entries:
        on = benchmarks._day(e["changed_at"])
        if on is None or not e["column"]:
            continue
        # A MODEL LEAVING A BOARD IS NEVER AN UPDATE (Parvathi, 2026-10-29). A
        # board stops listing a model for reasons that say nothing about the
        # model - a page or filter change, pagination, a renamed entry, our own
        # name matching - and it stays in the Benchmarks changelog to check. A
        # real retirement is an update from the registry's retirement date.
        if e["news"] == "dropped":
            continue
        # A RANK IS AN UPDATE ONLY WHEN IT IS A NEW #1. Every other place change
        # is mostly a model entering above (one new #2 moves everything below
        # it down a place); a real move shows in the score, which is a mover.
        # A first score's rank is told by the score.
        if _is_rank(e):
            old, new = _rank(e["old"]), _rank(e["new"])
            if e["news"] != "mover" or new != 1 or old in (None, 1):
                continue
        e = {**e, "row": _row_name(e, display)}
        model = _model_of(e["row_id"])
        base = {"name": e["row"], "board": e["column"], "date": day(on)}
        if e["news"] == "debut":
            debuts.setdefault((e["row_id"], e["run_id"]), []).append(e)
            continue
        if e["news"] == "fresh":
            src = benchmarks._day(e["source_date"])
            out.append(
                _story(
                    key=f"bench:{e['id']}",
                    kind="benchmark",
                    template="bench_fresh",
                    on=on,
                    facts={**base, "score": e["new"], "source_date": day(src) if src else None},
                    models=[model],
                    seen_at=e["changed_at"],
                )
            )
        elif e["news"] == "mover" and _is_rank(e):
            out.append(
                _story(
                    key=f"bench:{e['id']}",
                    kind="benchmark",
                    template="bench_top",
                    on=on,
                    facts={**base, "old_rank": f"#{old}", "out_of": e["new_out_of"]},
                    models=[model],
                    seen_at=e["changed_at"],
                )
            )
        elif e["news"] == "mover":
            old, new = _score(e["old"]), _score(e["new"])
            if old is None or new is None or old == new:
                continue
            out.append(
                _story(
                    key=f"bench:{e['id']}",
                    kind="benchmark",
                    template="bench_mover",
                    on=on,
                    facts={
                        **base,
                        "moves": "rises" if new > old else "falls",
                        "delta": f"{new - old:+.1f}".replace("-", "−"),
                        "old": e["old"],
                        "new": e["new"],
                    },
                    models=[model],
                    seen_at=e["changed_at"],
                )
            )
    for (row_id, run_id), members in debuts.items():
        members.sort(key=lambda m: m["column"])
        on = benchmarks._day(members[0]["changed_at"])
        model = _model_of(row_id)
        after = (on - released[model]).days if model in released else None
        timing = (
            None
            if after is None
            else (
                "on release day"
                if after == 0
                else f"{after} day{'s' if after != 1 else ''} after release"
            )
        )
        if len(members) >= r["group_min"]:
            out.append(
                _story(
                    key=f"bench-debut:{row_id}:{run_id}:{_digest([str(m['id']) for m in members])}",
                    kind="benchmark",
                    template="bench_debut_group",
                    on=on,
                    facts={
                        "name": members[0]["row"],
                        "count": len(members),
                        "boards": ", ".join(f"{m['column']} {m['new']}" for m in members),
                        "date": day(on),
                        "timing": timing,
                    },
                    models=[model],
                    seen_at=members[0]["changed_at"],
                )
            )
            continue
        e = members[0]
        out.append(
            _story(
                key=f"bench:{e['id']}",
                kind="benchmark",
                template="bench_debut",
                on=on,
                facts={
                    "name": e["row"],
                    "board": e["column"],
                    "score": e["new"],
                    "date": day(on),
                    "timing": timing,
                },
                models=[model],
                seen_at=e["changed_at"],
            )
        )
    return out


def _counted(n: int, word: str) -> str:
    """ "1 cut", "7 cuts"."""
    return f"{n} {word}{'' if n == 1 else 's'}"


def _top_providers(providers: list[str], shown: int) -> str:
    """ "OpenAI (4), Qwen (3) and Google (2)": the most frequent first."""
    counts: dict[str, int] = {}
    for who in providers:
        counts[who] = counts.get(who, 0) + 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:shown]
    return names([f"{who} ({n})" for who, n in top], shown)


def _roundups(
    launch_rows: list[tuple],
    price_moves: list[tuple[str, str, date, dict[str, Any]]],
    since: date,
    today: date,
    r: dict[str, Any],
) -> list[dict[str, Any]]:
    """One launch and one price round-up per COMPLETED week (Monday to Sunday,
    UTC) inside the window, when the week had at least `min_items` of them."""
    rule = r["roundups"]
    first = since + timedelta(days=(7 - since.weekday()) % 7)  # the first Monday in the window
    out = []
    monday = first
    while monday + timedelta(days=6) < today:
        sunday = monday + timedelta(days=6)
        week = day(monday)
        launched = [row for row in launch_rows if monday <= row[4] <= sunday]
        if len(launched) >= rule["min_items"]:
            launched.sort(key=lambda m: m[2] or m[1])
            out.append(
                _story(
                    key=f"roundup:launch:{monday}",
                    kind="roundup",
                    template="roundup_launch",
                    on=sunday,
                    facts={
                        "week": week,
                        "count": len(launched),
                        "long_context": sum(
                            1 for m in launched if (m[6] or 0) >= rule["long_context_tokens"]
                        ),
                        "providers": _top_providers(
                            [split_name(m[2], m[1], m[3])[0] for m in launched],
                            rule["providers_shown"],
                        ),
                        "names": names(
                            [split_name(m[2], m[1], m[3])[1] for m in launched], r["names_shown"]
                        ),
                    },
                    models=[m[1] for m in launched],
                )
            )
        moved = [m for m in price_moves if monday <= m[2] <= sunday]
        if len(moved) >= rule["min_items"]:
            n_cut = sum(1 for k, *_ in moved if k == "price_cut")
            n_rise = sum(1 for k, *_ in moved if k == "price_rise")
            out.append(
                _story(
                    key=f"roundup:price:{monday}",
                    kind="roundup",
                    template="roundup_price",
                    on=sunday,
                    facts={
                        "week": week,
                        "count": len({c["model_version_id"] for *_, c in moved}),
                        "cuts": _counted(n_cut, "cut"),
                        "rises": _counted(n_rise, "rise"),
                        "cheaper": f"{n_cut} got cheaper",
                        "pricier": f"{n_rise} got pricier",
                        "providers": _top_providers(
                            [who for _, who, _, _ in moved], rule["providers_shown"]
                        ),
                    },
                    models=[c["canonical_id"] or c["model_version_id"] for *_, c in moved],
                )
            )
        monday += timedelta(days=7)
    return out


def render(story: dict[str, Any], r: dict[str, Any]) -> list[dict[str, str]]:
    """Every style of the story's set that its facts can fill, in contract order."""
    facts = story["facts"]
    out = []
    for s in r["templates"][story["template"]]:
        need = _fields(s["headline"]) | _fields(s["detail"])
        if need <= facts.keys():
            out.append(
                {
                    "id": s["id"],
                    "label": s["label"],
                    "headline": s["headline"].format_map(facts),
                    "detail": s["detail"].format_map(facts),
                }
            )
    return out


def build(
    conn,
    *,
    bench_conn=None,
    days: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Every update in the window, newest first, rendered in each style it can
    take. Upcoming retirements are dated on their retirement day."""
    r = rules()
    window = r["window_days"] if days is None else max(1, min(int(days), r["max_window_days"]))
    now = now or datetime.now(UTC)
    today = now.date()
    since = today - timedelta(days=window)

    notes: list[str] = []
    launch_rows = conn.execute(LAUNCH_SQL, (since,)).fetchall()
    prices, price_moves = _prices(conn, window, r, now)
    stories = (
        _launches(launch_rows, r)
        + prices
        + _retiring(conn, today, r)
        + _roundups(launch_rows, price_moves, since, today, r)
    )
    if bench_conn is None:
        notes.append("Benchmark updates are not shown: the benchmarks data is not readable here.")
    else:
        from judge import benchmarks

        stories += _benchmarks(
            bench_news(bench_conn, since),
            benchmarks._release_dates(bench_conn),
            dict(
                bench_conn.execute(
                    "SELECT canonical_id, display_name FROM model_version"
                ).fetchall()
            ),
            r,
        )

    try:
        from judge.tracked import all_tracked

        tracked = {m.registry for m in all_tracked(conn, today=today) if m.registry}
    except Exception:  # noqa: BLE001 - the toggle is a filter; without it, nothing is "tracked"
        conn.rollback()
        tracked = set()
        notes.append("The tracked-models list could not be read, so no update is marked tracked.")

    out = []
    for s in stories:
        styles = render(s, r)
        if not styles:
            continue  # no style its facts can fill: nothing true to say in words
        kind = r["kinds"][s["kind"]]
        s.update(
            styles=styles,
            label=kind["label"],
            why=r["why_by_set"].get(s["template"], kind["why"]),
            source=kind["source"],
            tracked=any(m in tracked for m in s["models"]),
            upcoming=s["date"] > today.isoformat(),
        )
        out.append(s)
    out.sort(key=lambda s: (s["date"], s["seen_at"] or "", s["key"]), reverse=True)
    return {
        "window_days": window,
        # When this list was built: every read rebuilds it, so Refresh is a re-read.
        "built_at": now.isoformat(),
        "updates": out,
        "notes": notes,
        "rules": r,
    }


# ── people's decisions ───────────────────────────────────────────────────────

REVIEW_COLUMNS = (
    "update_key",
    "kind",
    "status",
    "style",
    "headline",
    "detail",
    "reviewed_by",
    "reviewed_at",
    "home_headline",
    "home_detail",
    "home_published_by",
    "home_published_at",
)
REVIEW_SQL = (
    "SELECT update_key, kind, status, style, headline, detail, reviewed_by, reviewed_at, "
    "home_headline, home_detail, home_published_by, home_published_at "
    "FROM update_review"
)
#: What a decision sets, and what an undo puts back.
STATE = (
    "status",
    "style",
    "headline",
    "detail",
    "home_headline",
    "home_detail",
    "home_published_by",
    "home_published_at",
)
UNPUBLISHED = {
    "home_headline": None,
    "home_detail": None,
    "home_published_by": None,
    "home_published_at": None,
}


def _state(before: dict[str, Any] | None) -> dict[str, Any]:
    """A decision's state to change: the stored one, or a fresh not-reviewed one."""
    return {f: (before or {}).get(f, "pending" if f == "status" else None) for f in STATE}


def _words(update: dict[str, Any], state: dict[str, Any]) -> tuple[str, str, str]:
    """The style shown, and the headline and detail as the page shows them."""
    ids = [s["id"] for s in update["styles"]]
    style = state.get("style") if state.get("style") in ids else ids[0]
    chosen = update["styles"][ids.index(style)]
    return (
        style,
        state.get("headline") or chosen["headline"],
        state.get("detail") or chosen["detail"],
    )


def _reviews(conn) -> dict[str, dict[str, Any]] | None:
    """Every stored decision by key, with its last undoable change; None when the
    tables are not in this database."""
    try:
        rows = conn.execute(REVIEW_SQL).fetchall()
        undoable = {
            k: (a, by, at)
            for k, a, by, at in conn.execute(
                "SELECT DISTINCT ON (update_key) update_key, action, acted_by, acted_at "
                "FROM update_review_log WHERE undone_at IS NULL ORDER BY update_key, id DESC"
            ).fetchall()
        }
    except errors.UndefinedTable:
        conn.rollback()
        return None
    out = {row[0]: dict(zip(REVIEW_COLUMNS, row, strict=True)) for row in rows}
    for k, (action, by, at) in undoable.items():
        out.setdefault(k, {"update_key": k, "status": "pending"})["undo"] = {
            "action": action,
            "by": by,
            "at": at.isoformat(),
        }
    return out


class Live:
    """The keys of every update still built over the longest window (#585
    follow-up: every kind, not only prices). A published update not among them
    is no longer in the data - a cut that did not last, a retirement whose date
    changed, a benchmark result that was corrected - and comes off the home
    page. Benchmark keys are only known when the benchmarks data was readable;
    when it was not, a benchmark update is given the benefit of the doubt."""

    def __init__(self, keys: set[str], benchmarks_known: bool):
        self.keys = keys
        self.benchmarks_known = benchmarks_known

    def __contains__(self, key_and_kind: tuple[str, str]) -> bool:
        key, kind = key_and_kind
        return key in self.keys or (kind == "benchmark" and not self.benchmarks_known)


def live_keys(conn, *, bench_conn=None, now: datetime | None = None) -> Live:
    r = rules()
    built = build(conn, bench_conn=bench_conn, days=r["max_window_days"], now=now)
    return Live({u["key"] for u in built["updates"]}, bench_conn is not None)


def _home(
    rv: dict[str, Any],
    kind: str,
    words: tuple[str, str] | None,
    live: Live,
    r: dict[str, Any],
    now: datetime,
    *,
    gone: bool = False,
) -> dict[str, Any] | None:
    """A published update's home-page state, or None when it was never
    published. `on_home` is what published() serves; `removed` says why not."""
    at = rv.get("home_published_at")
    if not at:
        return None
    removed = None
    if rv.get("status") != "approved":
        removed = "not_approved"
    elif now - at > timedelta(days=r["home_days"]):
        removed = "expired"
    elif gone or (rv["update_key"], kind) not in live:
        removed = "not_in_data"
    return {
        "headline": rv["home_headline"],
        "detail": rv["home_detail"],
        "by": _who(rv["home_published_by"]),
        "at": at.isoformat(),
        "current": words is not None and (rv["home_headline"], rv["home_detail"]) == words,
        "on_home": removed is None,
        "removed": removed,
    }


def _who(email: str | None) -> str | None:
    """What the page shows for a person: the part of their email before the @."""
    return email.split("@")[0] if email else None


def listing(
    conn, *, bench_conn=None, days: int | None = None, now: datetime | None = None
) -> dict[str, Any]:
    """Both sections' data: each update with its final words and its review."""
    now = now or datetime.now(UTC)
    built = build(conn, bench_conn=bench_conn, days=days, now=now)
    reviews = _reviews(conn)
    saving = reviews is not None
    reviews = reviews or {}
    r = built["rules"]
    live = live_keys(conn, bench_conn=bench_conn, now=now)
    examples: dict[str, dict[str, Any]] = {}
    for u in built["updates"]:
        examples.setdefault(u["template"], u)
        rv = reviews.get(u["key"], {})
        style, headline, detail = _words(u, rv)
        status = rv.get("status", "pending")
        u.update(
            status=status,
            # On News headlines: not declined, and a round-up only once approved.
            published=status != "declined" and (u["kind"] != "roundup" or status == "approved"),
            # The home page: the words as they were when a person published
            # them, fixed, so a later template change or edit never changes a
            # published headline. `current` is false when the card's words have
            # changed since (the page offers Republish); `removed` says why it
            # is no longer on the home page.
            home=_home(rv, u["kind"], (headline, detail), live, r, now),
            style=style,
            headline=headline,
            detail=detail,
            edited=bool(rv.get("headline") or rv.get("detail")),
            reviewed_by=_who(rv.get("reviewed_by")),
            reviewed_at=rv["reviewed_at"].isoformat() if rv.get("reviewed_at") else None,
            undo=({**rv["undo"], "by": _who(rv["undo"]["by"])} if rv.get("undo") else None),
        )
        # Read by the templates, the number check and the filters here, not by
        # the page (rule 9).
        for internal in ("facts", "models", "seen_at", "template"):
            del u[internal]
    built.pop("rules")
    # PUBLISHED, NO LONGER BUILT (#585 review). An update's key names its facts,
    # so a published one stops being built when they change: a cut that did not
    # last, a launch that became part of a group, or one older than the window.
    # It is still listed here, in its published words, so it can be taken off
    # the home page.
    shown = {u["key"] for u in built["updates"]}
    for key, rv in reviews.items():
        if key in shown or not rv.get("home_published_at"):
            continue
        at = rv["home_published_at"]
        built["updates"].append(
            {
                "key": key,
                "kind": rv["kind"],
                "date": at.astimezone(UTC).date().isoformat(),
                "label": r["kinds"][rv["kind"]]["label"],
                "why": "No longer in the data",
                "source": r["kinds"][rv["kind"]]["source"],
                "styles": [],
                "second_check": False,
                "tracked": False,
                "upcoming": False,
                "gone": True,
                "status": rv["status"],
                "published": False,
                "home": _home(rv, rv["kind"], None, live, r, now, gone=True),
                "style": None,
                "headline": rv["home_headline"],
                "detail": rv["home_detail"],
                "edited": False,
                "reviewed_by": _who(rv.get("reviewed_by")),
                "reviewed_at": rv["reviewed_at"].isoformat() if rv.get("reviewed_at") else None,
                "undo": ({**rv["undo"], "by": _who(rv["undo"]["by"])} if rv.get("undo") else None),
            }
        )
    return {
        **built,
        "home_days": r["home_days"],
        "saving": saving,
        "second_check_pct": r["second_check_pct"],
        "max_window_days": r["max_window_days"],
        "edit_limits": {"headline": HEADLINE_MAX, "detail": DETAIL_MAX},
        "style_catalog": style_catalog(r, examples),
    }


def _kind_of(template: str) -> str:
    """The kind of update a template set belongs to."""
    for prefix, kind in (
        ("price_rise", "price_rise"),
        ("price_mixed", "price_change"),
        ("price_", "price_cut"),
        ("retir", "retiring"),
        ("bench_", "benchmark"),
        ("roundup_", "roundup"),
        ("launch", "launch"),
    ):
        if template.startswith(prefix):
            return kind
    raise UpdatesContractError(f"template set {template!r} belongs to no kind")


def style_catalog(r: dict[str, Any], examples: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Every template set and its styles, for the Info tab: the template as
    written, and the same style filled from an update in this list when there
    is one (a style its facts cannot fill has no example)."""
    out = []
    for name, styles in r["templates"].items():
        example = examples.get(name)
        filled = {s["id"]: s for s in example["styles"]} if example else {}
        out.append(
            {
                "set": name,
                "kind": _kind_of(name),
                "label": r["set_labels"][name],
                "styles": [
                    {
                        "id": s["id"],
                        "label": s["label"],
                        "headline": s["headline"],
                        "detail": s["detail"],
                        "example": (
                            {
                                "headline": filled[s["id"]]["headline"],
                                "detail": filled[s["id"]]["detail"],
                            }
                            if s["id"] in filled
                            else None
                        ),
                    }
                    for s in styles
                ],
            }
        )
    return out


NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def _value(number: str) -> str:
    """A number as a value, so "$0.40" in a style and "0.4" in an edit match."""
    return f"{float(number.replace(',', '')):g}"


def _numbers(text: str) -> set[str]:
    return {_value(n) for n in NUMBER.findall(text or "")}


def unknown_numbers(update: dict[str, Any], *texts: str) -> list[str]:
    """Numbers in `texts` that are in none of the update's facts or styles."""
    known: set[str] = set()
    for v in update["facts"].values():
        known |= _numbers(str(v))
    for s in update["styles"]:
        known |= _numbers(s["headline"]) | _numbers(s["detail"])
    seen: list[str] = []
    for t in texts:
        for n in NUMBER.findall(t or ""):
            if _value(n) not in known and n not in seen:
                seen.append(n)
    return seen


def _refuse_unsafe_write() -> None:
    from judge import writeguard

    try:
        writeguard.check(os.environ.get("DATABASE_URL"), command="updates review")
    except writeguard.UnsafeWriteRefused as e:
        raise SavingUnavailable(
            "Saving is off on this backend: it is a development backend reading a "
            "shared database. Decisions are saved on the local database or the site."
        ) from e


def _current(conn, key: str) -> dict[str, Any] | None:
    try:
        row = conn.execute(REVIEW_SQL + " WHERE update_key = %s", (key,)).fetchone()
    except errors.UndefinedTable as e:
        conn.rollback()
        raise SavingUnavailable(
            "Saving needs the update_review table (migration 20261029T1200), "
            "which is not in this database yet."
        ) from e
    return dict(zip(REVIEW_COLUMNS, row, strict=True)) if row else None


def _jsonable(row: dict[str, Any] | None) -> str | None:
    if row is None:
        return None
    return json.dumps(
        {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in row.items()}
    )


def _write(
    conn,
    key: str,
    kind: str,
    action: str,
    by: str,
    before: dict[str, Any] | None,
    after: dict[str, Any],
) -> None:
    try:
        conn.execute(
            "INSERT INTO update_review "
            "(update_key, kind, status, style, headline, detail, reviewed_by, reviewed_at, "
            "home_headline, home_detail, home_published_by, home_published_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, now(), %s, %s, %s, %s) "
            "ON CONFLICT (update_key) DO UPDATE SET "
            "status = EXCLUDED.status, style = EXCLUDED.style, "
            "headline = EXCLUDED.headline, detail = EXCLUDED.detail, "
            "reviewed_by = EXCLUDED.reviewed_by, reviewed_at = now(), "
            "home_headline = EXCLUDED.home_headline, home_detail = EXCLUDED.home_detail, "
            "home_published_by = EXCLUDED.home_published_by, "
            "home_published_at = EXCLUDED.home_published_at",
            (
                key,
                kind,
                after["status"],
                after["style"],
                after["headline"],
                after["detail"],
                by,
                after["home_headline"],
                after["home_detail"],
                after["home_published_by"],
                after["home_published_at"],
            ),
        )
        conn.execute(
            "INSERT INTO update_review_log (update_key, action, before, after, acted_by) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s)",
            (key, action, _jsonable(before), _jsonable({**after, "kind": kind}), by),
        )
    except errors.ReadOnlySqlTransaction as e:
        conn.rollback()
        raise SavingUnavailable(
            "This backend reads its database read-only, so nothing can be saved here."
        ) from e


def review(
    conn,
    update: dict[str, Any],
    *,
    action: str,
    by: str,
    style: str | None = None,
    headline: str | None = None,
    detail: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Apply one decision to one built update (from build(), facts included)."""
    if action not in ACTIONS:
        raise ReviewRefused(f"action must be one of {', '.join(ACTIONS)}")
    if update.get("gone") and action not in GONE_ACTIONS:
        raise ReviewRefused(
            "this update is no longer in the data: it can only be unpublished or declined"
        )
    _refuse_unsafe_write()
    before = _current(conn, update["key"])
    after = _state(before)
    if action == "approve":
        after["status"] = "approved"
    elif action == "decline":
        # A hidden update comes off the home page too.
        after.update(status="declined", **UNPUBLISHED)
    elif action == "publish":
        # Only an update a person approved in Manage goes to the home page
        # (Parvathi, 2026-10-29). The words are kept as they are now; only a
        # republish changes them.
        if after["status"] != "approved":
            raise ReviewRefused(
                "only an approved update can be published; approve it in Manage first"
            )
        _, headline_now, detail_now = _words(update, after)
        after.update(
            home_headline=headline_now,
            home_detail=detail_now,
            home_published_by=by,
            home_published_at=datetime.now(UTC),
        )
    elif action == "unpublish":
        after.update(**UNPUBLISHED)
    elif action == "restore":
        after["status"] = "pending"
    elif action == "style":
        if style not in {s["id"] for s in update["styles"]}:
            raise ReviewRefused(f"style {style!r} is not offered for this update")
        # A new style replaces the person's own words: they were written over
        # the old style's, and keeping them would hide the choice just made.
        after.update(style=style, headline=None, detail=None)
    elif action == "edit":
        headline = (headline or "").strip() or None
        detail = (detail or "").strip() or None
        if headline and len(headline) > HEADLINE_MAX:
            raise ReviewRefused(f"a headline is at most {HEADLINE_MAX} characters")
        if detail and len(detail) > DETAIL_MAX:
            raise ReviewRefused(f"a detail is at most {DETAIL_MAX} characters")
        if not confirm:
            unknown = unknown_numbers(update, headline or "", detail or "")
            if unknown:
                raise EditNeedsConfirm(unknown)
        after.update(headline=headline, detail=detail)
    _write(conn, update["key"], update["kind"], action, by, before, after)
    clear_published_cache()
    return {
        "key": update["key"],
        "status": after["status"],
        "published": bool(after["home_published_at"]),
    }


def stored_update(conn, key: str) -> dict[str, Any] | None:
    """A published update that is no longer built, from its stored review row,
    so Manage can still take it off the home page (#585 review). None when
    there is no such row."""
    row = _current(conn, key)
    if row is None or not row.get("home_published_at"):
        return None
    return {"key": key, "kind": row["kind"], "styles": [], "facts": {}, "gone": True}


def approve_all(conn, updates: list[dict[str, Any]], *, by: str) -> dict[str, Any]:
    """Approve every given update not yet reviewed; declined ones are left as
    they are, so "approve all shown" never brings back what someone hid."""
    _refuse_unsafe_write()
    done = 0
    for u in updates:
        before = _current(conn, u["key"])
        if before and before["status"] != "pending":
            continue
        after = {**_state(before), "status": "approved"}
        _write(conn, u["key"], u["kind"], "approve", by, before, after)
        done += 1
    clear_published_cache()
    return {"approved": done}


def is_gone(conn, key: str, *, bench_conn=None) -> bool:
    """Whether a stored update is no longer among the updates built."""
    row = _current(conn, key) or {}
    return (key, row.get("kind", "")) not in live_keys(conn, bench_conn=bench_conn)


def undo(conn, key: str, *, by: str, gone: bool = False) -> dict[str, Any]:
    """Put back the update's state before its last change not yet undone.

    NOT ONTO THE HOME PAGE FOR AN UPDATE NO LONGER IN THE DATA (#585
    follow-up): undoing an Unpublish there would republish its old words, now
    wrong. `gone` is the caller's: the key is not among the updates built."""
    _refuse_unsafe_write()
    _current(conn, key)  # the tables exist
    row = conn.execute(
        "SELECT id, before, action FROM update_review_log "
        "WHERE update_key = %s AND undone_at IS NULL ORDER BY id DESC LIMIT 1",
        (key,),
    ).fetchone()
    if row is None:
        raise ReviewRefused("nothing to undo for this update", status=404)
    log_id, before, action = row
    if gone and before and before.get("home_published_at"):
        raise ReviewRefused(
            "this update is no longer in the data, so undoing this would put its old words "
            "back on the home page"
        )
    try:
        if before is None:
            conn.execute("DELETE FROM update_review WHERE update_key = %s", (key,))
        else:
            conn.execute(
                "UPDATE update_review SET status = %s, style = %s, headline = %s, detail = %s, "
                "reviewed_by = %s, reviewed_at = %s, home_headline = %s, home_detail = %s, "
                "home_published_by = %s, home_published_at = %s WHERE update_key = %s",
                (
                    before["status"],
                    before["style"],
                    before["headline"],
                    before["detail"],
                    before["reviewed_by"],
                    before["reviewed_at"],
                    before.get("home_headline"),
                    before.get("home_detail"),
                    before.get("home_published_by"),
                    before.get("home_published_at"),
                    key,
                ),
            )
        conn.execute(
            "UPDATE update_review_log SET undone_by = %s, undone_at = now() WHERE id = %s",
            (by, log_id),
        )
    except errors.ReadOnlySqlTransaction as e:
        conn.rollback()
        raise SavingUnavailable(
            "This backend reads its database read-only, so nothing can be saved here."
        ) from e
    clear_published_cache()
    return {"key": key, "undid": action}


# ── the home page's updates strip ───────────────────────────────────────────────

PUBLISHED_SQL = (
    "SELECT update_key, kind, home_headline, home_detail, home_published_at "
    "FROM update_review "
    "WHERE home_published_at IS NOT NULL AND status = 'approved' AND home_published_at >= %s "
    "ORDER BY home_published_at DESC"
)


#: The home page's read, kept `home_cache_seconds` (#585 follow-up): it
#: rebuilds the updates, which reads the whole price history. Cleared by every
#: save in Manage, so a publish shows at once on this process. One entry,
#: (answer, until, generation), read with a single get: requests run on a thread
#: pool and a save can clear it between two reads (#586 review).
_published_cache: dict[str, tuple[dict[str, Any], datetime, int]] = {}
#: Bumped by every clear, so a rebuild that began before a save does not store
#: the answer from before it.
_published_generation = [0]


def clear_published_cache() -> None:
    _published_generation[0] += 1
    _published_cache.clear()


def _kept(name: str, now: datetime | None) -> dict[str, Any] | None:
    """A public read's kept answer, or None when there is none, it has run out,
    or a save came after it was stored (#586 review: the generation is compared
    on read too, so a clear between check and store cannot leave it served)."""
    hit = _published_cache.get(name)
    if (
        hit is not None
        and hit[2] == _published_generation[0]
        and (now or datetime.now(UTC)) < hit[1]
    ):
        return hit[0]
    return None


def stale(name: str) -> dict[str, Any] | None:
    """A public read's last answer even when its time has run out, or None when
    there is none or a save came after it (a save must show at once, so only an
    answer no save has overtaken is served while a fresh one is built). `name`
    is "v" (the home page) or "approved" (the AI updates page)."""
    hit = _published_cache.get(name)
    return hit[0] if hit is not None and hit[2] == _published_generation[0] else None


#: An answer built while the benchmarks data was not readable is kept this
#: long at most, so the page asks again soon instead of saying "unavailable"
#: for the whole `home_cache_seconds` (#592 review).
UNREAD_KEEP_SECONDS = 60


def _keep(
    name: str, out: dict[str, Any], clock: datetime, generation: int, *, short: bool = False
) -> None:
    seconds = rules()["home_cache_seconds"]
    if short:
        seconds = min(seconds, UNREAD_KEEP_SECONDS)
    if generation == _published_generation[0]:
        _published_cache[name] = (out, clock + timedelta(seconds=seconds), generation)


def cached_published(now: datetime | None = None) -> dict[str, Any] | None:
    """The home page's kept answer, or None when there is none or it has run
    out. Needs no database, so the endpoint checks it before connecting."""
    return _kept("v", now)


def published(conn, *, bench_conn=None, now: datetime | None = None) -> dict[str, Any]:
    """What the home page shows: the updates a person published in the last
    `home_days`, newest first, at most `home_limit`, in the words they were
    published with (contract/updates.yaml). One that is no longer in the data -
    a cut that did not last, a retirement whose date changed - comes off by
    itself. PUBLIC (judge/gate.py): it sends those words, the kind and the
    publish time, and nothing from Manage - no reviewer, no style, no draft, no
    update that was not published."""
    r = rules()
    clock = now or datetime.now(UTC)
    if now is None and (kept := cached_published(clock)) is not None:
        return kept
    generation = _published_generation[0]
    try:
        rows = conn.execute(PUBLISHED_SQL, (clock - timedelta(days=r["home_days"]),)).fetchall()
    except errors.UndefinedTable:
        conn.rollback()
        rows = []
    if rows:
        live = live_keys(conn, bench_conn=bench_conn, now=clock)
        rows = [row for row in rows if (row[0], row[1]) in live]
    rows = rows[: r["home_limit"]]
    out = {
        "updates": [
            {
                "key": key,
                "kind": kind,
                "label": r["kinds"][kind]["label"],
                "headline": headline,
                "detail": detail,
                "published_at": at.astimezone(UTC).isoformat(),
                # A listed price can be the provider's change or only the
                # router's: the strip says so on every price headline.
                "verify": kind.startswith("price"),
            }
            for key, kind, headline, detail, at in rows
        ]
    }
    if now is None:
        _keep("v", out, clock, generation)
    return out


# ── the public AI updates page (/ai-news-headlines) ───────────────────────────────

APPROVED_SQL = (
    "SELECT update_key, status, style, headline, detail FROM update_review "
    "WHERE status = 'approved'"
)


def cached_approved(now: datetime | None = None) -> dict[str, Any] | None:
    """The AI updates page's kept answer; as cached_published()."""
    return _kept("approved", now)


def approved(conn, *, bench_conn=None, now: datetime | None = None) -> dict[str, Any]:
    """What the public AI updates page shows (Parvathi, 2026-10-30): every update
    a person APPROVED in Manage, over `max_window_days`, newest first, in its
    words as Manage shows them now - the chosen style, or the person's edit.

    Not the home page's rule: publishing fixes words for the home page's few
    days; this page is the longer record, so it follows Manage. Only updates
    still built are listed, so one no longer in the data leaves by itself.

    AN OUTAGE IS SAID, NEVER READ AS "NONE" (rule 6, #592 review): when the
    benchmarks data is not readable, benchmark updates cannot be worded, so
    `benchmarks_unread` is true and the page says the results are unavailable
    rather than "nothing in this section". Such an answer is kept only
    UNREAD_KEEP_SECONDS. PUBLIC (judge/gate.py): words, kind, label, date, the
    verify mark, the models' public ids and that flag only - no reviewer, no
    style, no status, no draft."""
    r = rules()
    clock = now or datetime.now(UTC)
    if now is None and (kept := cached_approved(clock)) is not None:
        return kept
    generation = _published_generation[0]
    try:
        rows = conn.execute(APPROVED_SQL).fetchall()
    except errors.UndefinedTable:
        conn.rollback()
        rows = []
    reviews = {
        key: {"status": status, "style": style, "headline": headline, "detail": detail}
        for key, status, style, headline, detail in rows
    }
    items = []
    if reviews:
        built = build(conn, bench_conn=bench_conn, days=r["max_window_days"], now=clock)
        for u in built["updates"]:
            rv = reviews.get(u["key"])
            if rv is None:
                continue
            _, headline, detail = _words(u, rv)
            items.append(
                {
                    "key": u["key"],
                    "kind": u["kind"],
                    "label": u["label"],
                    "headline": headline,
                    "detail": detail,
                    "date": u["date"],
                    "upcoming": u["upcoming"],
                    "verify": u["kind"].startswith("price"),
                    # The models it is about, by their public ids, so each
                    # headline can link to the model's own page.
                    "models": list(u["models"]),
                }
            )
    unread = bench_conn is None
    out = {"updates": items, "window_days": r["max_window_days"], "benchmarks_unread": unread}
    if now is None:
        _keep("approved", out, clock, generation, short=unread)
    return out
