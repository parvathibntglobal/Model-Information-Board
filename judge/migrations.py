"""Migration guides: the verified-facts box inside each one (2026-10-30, anooj).

PHASE 1 OF THE GUIDES PAGE (scoping report, 2026-10-30): what changes when a
team moves from one model to another, from the facts the board already holds.
Every row and every checklist line is filled from the registry
(`model_version`) and worded by contract/migrations.yaml with str.format. No
model is called (rule 2) and no figure is synthesised (rule 3): a price, a
context window and a date are shown as published, side by side.

A VALUE NOBODY PUBLISHED STAYS UNPUBLISHED (rule 6). Either side NULL makes a
row's change `unknown`, never `same`; a NULL flag is "not published", never
"no".

WHAT IT DOES NOT COVER, and the page says so: API, SDK, parameter and prompt
changes. Those need the providers' own documentation, which the board does
not collect yet.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

CONTRACT = Path(__file__).resolve().parents[1] / "contract" / "migrations.yaml"
KINDS = ("price", "share", "tokens", "date", "flag")
CHANGES = ("up", "down", "same", "gained", "lost", "unknown", "from_set", "to_set", "both_set")

FACTS_SQL = (
    "SELECT id, canonical_id, provider, display_name, release_date, retirement_date, "
    "       knowledge_cutoff, advertised_context, max_output_tokens, price_in, price_out, "
    "       price_cached_read, batch_discount, supports_tools, supports_structured_output, "
    "       supports_vision, supports_caching, supports_batch, updated_at "
    "FROM model_version"
)
COLUMNS = (
    "id",
    "canonical_id",
    "provider",
    "display_name",
    "release_date",
    "retirement_date",
    "knowledge_cutoff",
    "advertised_context",
    "max_output_tokens",
    "price_in",
    "price_out",
    "price_cached_read",
    "batch_discount",
    "supports_tools",
    "supports_structured_output",
    "supports_vision",
    "supports_caching",
    "supports_batch", "updated_at"
)


class MigrationsContractError(RuntimeError):
    """contract/migrations.yaml is missing something this refuses to default."""


def rules(path: Path = CONTRACT) -> dict[str, Any]:
    """The contract, validated. Every key required (rule 12)."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        rows = [
            {"field": str(r["field"]), "label": str(r["label"]), "kind": str(r["kind"])}
            for r in raw["rows"]
        ]
        checklist = {
            str(f): {str(c): str(t) for c, t in (lines or {}).items()}
            for f, lines in raw["checklist"].items()
        }
        out = {
            "rows": rows,
            "checklist": checklist,
            "other_provider": str(raw["other_provider"]),
            "always": str(raw["always"]),
        }
    except (KeyError, TypeError) as exc:
        raise MigrationsContractError(
            f"contract/migrations.yaml is missing or malformed at {exc}"
        ) from exc
    fields = {r["field"] for r in rows}
    for r in rows:
        if r["kind"] not in KINDS:
            raise MigrationsContractError(
                f"row {r['field']!r}: kind {r['kind']!r} is not one of {KINDS}"
            )
        if r["field"] not in COLUMNS:
            raise MigrationsContractError(
                f"row {r['field']!r} is not a model_version column read here"
            )
    for f, lines in checklist.items():
        if f not in fields:
            raise MigrationsContractError(f"checklist names {f!r}, which is not a row")
        bad = set(lines) - set(CHANGES)
        if bad:
            raise MigrationsContractError(
                f"checklist {f!r}: {sorted(bad)} are not changes {CHANGES}"
            )
    return out


# ── reading the registry ─────────────────────────────────────────────────────


def _models(conn) -> list[dict[str, Any]]:
    return [dict(zip(COLUMNS, row, strict=True)) for row in conn.execute(FACTS_SQL).fetchall()]


def _resolve(models: list[dict], ident: str) -> dict | None:
    """A model by its registry id, its readable id (`anthropic/claude-opus-5.5`),
    or its ADDRESS NAME - the readable id after the provider (`claude-opus-5.5`),
    or `provider--name`, as a comparison address writes it. A bare name
    two providers share matches nothing rather than one of them (rule 12)."""
    for m in models:
        if ident in (m["id"], m["canonical_id"]):
            return m
    if "--" in ident:
        full = ident.replace("--", "/", 1)
        return next((m for m in models if m["canonical_id"] == full), None)
    named = [m for m in models if (m["canonical_id"] or "").split("/", 1)[-1] == ident]
    return named[0] if len(named) == 1 else None


def provider_of(m: dict) -> str:
    """The provider as the readable id spells it: `provider` is not one
    spelling ("Anthropic" and "anthropic" both occur, 2026-10-30)."""
    cid = m.get("canonical_id") or ""
    return cid.split("/", 1)[0] if "/" in cid else (m.get("provider") or "").lower()


def provider_name(m: dict) -> str:
    """The provider as people write it: the display name's prefix
    ("Anthropic: Claude Opus 5.5" -> "Anthropic"), else the id's."""
    name = m.get("display_name") or ""
    return name.split(": ", 1)[0] if ": " in name else provider_of(m)


def _name(m: dict) -> str:
    """`Anthropic: Claude Opus 5.5` -> `Claude Opus 5.5`: the page names the provider once."""
    name = m.get("display_name") or m.get("canonical_id") or m["id"]
    return name.split(": ", 1)[1] if ": " in name else name


# ── one change ───────────────────────────────────────────────────────────────


def _num(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    return float(v) if isinstance(v, (int, float, Decimal)) else None


def show(kind: str, v: Any) -> str | None:
    """A value as the page shows it; None stays None ("not published")."""
    if v is None:
        return None
    if kind == "price":
        # AS PUBLISHED, up to four decimals and never fewer than two, at every
        # size: $2.625 stays $2.625 (#590 review), $0.2 reads $0.20.
        whole, cents = f"{float(v):,.4f}".split(".")
        cents = cents.rstrip("0")
        return f"${whole}.{cents + '0' * (2 - len(cents))}"
    if kind == "share":
        return f"{float(v) * 100:g}%"
    if kind == "tokens":
        return f"{int(v):,}"
    if kind == "date":
        return v.isoformat() if isinstance(v, date) else str(v)
    if kind == "flag":
        return "Yes" if v else "No"
    raise ValueError(kind)


def change(kind: str, field: str, a: Any, b: Any) -> str:
    """How `field` moves from model a to model b.

    Retirement is the one row where each side means something on its own: a
    date on either side is news (`from_set`, `to_set`, or `both_set` when both
    retire - the model you move to retiring is the warning that matters most,
    #590 review), and the two dates are never compared."""
    if field == "retirement_date":
        if a is not None and b is not None:
            return "both_set"
        return "from_set" if a is not None else "to_set" if b is not None else "same"
    if a is None or b is None:
        return "unknown"
    if kind == "flag":
        return "same" if bool(a) == bool(b) else ("gained" if b else "lost")
    if kind == "date":
        return "same" if a == b else ("up" if b > a else "down")
    x, y = _num(a), _num(b)
    if x is None or y is None:
        return "unknown"
    return "same" if x == y else ("up" if y > x else "down")


def diff(a: dict, b: dict, r: dict) -> list[dict[str, Any]]:
    """The "What changes" table, one row per contract row."""
    out = []
    for row in r["rows"]:
        f, k = row["field"], row["kind"]
        out.append(
            {
                "field": f,
                "label": row["label"],
                "kind": k,
                "from": show(k, a.get(f)),
                "to": show(k, b.get(f)),
                "change": change(k, f, a.get(f), b.get(f)),
            }
        )
    return out


def checklist(a: dict, b: dict, rows: list[dict], r: dict) -> list[str]:
    """ "Before you switch": the contract's line for each change the pair shows,
    then the other-provider line, then the line that is always shown."""
    names = {"from_name": _name(a), "to_name": _name(b), "to_provider": provider_name(b)}
    out = []
    for row in rows:
        lines = r["checklist"].get(row["field"], {})
        keys = ("from_set", "to_set") if row["change"] == "both_set" else (row["change"],)
        for key in keys:
            if lines.get(key):
                out.append(lines[key].format(**names, **{"from": row["from"], "to": row["to"]}))
    if provider_of(a) != provider_of(b):
        out.append(r["other_provider"].format(**names))
    out.append(r["always"].format(**names))
    return out


def _brief(m: dict) -> dict[str, Any]:
    return {
        "id": m["canonical_id"] or m["id"],
        "name": _name(m),
        "provider": provider_of(m),
        "provider_name": provider_name(m),
        "released": show("date", m["release_date"]),
    }


def _reports(conn, ids: list[str]) -> dict[str, int]:
    """Board entries per model, declined rulings left out: COUNTED, the same
    rows the model's own pages count (totals include every source)."""
    rows = conn.execute(
        "SELECT model_version_id, count(*) FROM board_entry "
        "WHERE model_version_id = ANY(%s) AND ruling IS DISTINCT FROM 'declined' GROUP BY 1",
        (ids,),
    ).fetchall()
    return {mid: n for mid, n in rows}


def migration(conn, from_id: str, to_id: str, *, models: list[dict] | None = None
              ) -> dict[str, Any] | None:
    """Both models' facts, what changes, and what to check. None when either id
    is not in the registry; a model moved to itself is no migration. `models`
    lets a caller that has read the registry pass it through (one read, not two)."""
    r = rules()
    models = _models(conn) if models is None else models
    a, b = _resolve(models, from_id), _resolve(models, to_id)
    if a is None or b is None or a["id"] == b["id"]:
        return None
    rows = diff(a, b, r)
    counts = _reports(conn, [a["id"], b["id"]])
    polled = [m["updated_at"] for m in (a, b) if m.get("updated_at")]
    return {
        "from": _brief(a),
        "to": _brief(b),
        "same_provider": provider_of(a) == provider_of(b),
        "rows": rows,
        "checklist": checklist(a, b, rows, r),
        # COUNTED, never weighed: how many board entries each model has, so a
        # reader knows how much the linked comparison rests on. Zero is shown as
        # zero - a model nobody has reported on is not a model that failed.
        "reports": {"from": counts.get(a["id"], 0), "to": counts.get(b["id"], 0)},
        # WHEN THE REGISTRY LAST READ THESE TWO (#590 review): the older of the
        # two models' polls, so "read on" is a fact about the data, never the
        # reader's clock. None when neither poll is recorded (rule 6).
        "registry_read": show("date", min(polled).date()) if polled else None,
        "not_covered": ["API and SDK changes", "parameter names and defaults", "prompt changes"],
    }


def _at(title: str, m: dict) -> int | None:
    """Where a model is named in a title: its full name, or without the family
    word ("Opus 5.5" for "Claude Opus 5.5"), as titles write it."""
    low = title.lower()
    name = _name(m).lower()
    for n in (name, name.split(" ", 1)[-1]):
        # THE WHOLE NAME (rule 10): "claude opus 5" is not inside "claude opus 5.5".
        hit = re.search(rf"(?<![\w.]){re.escape(n)}(?![\w]|\.\d)", low) if n else None
        if hit:
            return hit.start()
    return None


def direction(title: str, a: dict, b: dict) -> tuple[dict, dict, str]:
    """(from, to, how it was decided). THE TITLE'S ORDER when it says "A to B";
    otherwise older to newer by release date - never a guess presented as the
    post's own, so `how` travels to the page."""
    ia, ib = _at(title, a), _at(title, b)
    # "TO" BETWEEN THE TWO NAMES (#590 review): "which to pick", "when to
    # switch" and "How to move" carry a "to" that names no order.
    if ia is not None and ib is not None and ia != ib \
            and " to " in title.lower()[min(ia, ib):max(ia, ib)]:
        return (a, b, "title") if ia < ib else (b, a, "title")
    first, second = sorted((a, b), key=lambda m: (m["release_date"] or date.max, m["id"]))
    return first, second, "release"


def guide(conn, slug: str) -> dict[str, Any] | None:
    """The verified facts for one approved migration guide (2026-10-30, anooj).

    The pair is the post's plan key (`migration-guide:<a>+<b>`, sorted ids).
    None when the slug is not an approved migration guide, or a model in its
    plan key is no longer in the registry."""
    from judge import blog_store

    found = blog_store.approved_plan(conn, slug)
    if not found or not (found[0] or "").startswith("migration-guide:"):
        return None
    plan_key, title = found
    ids = plan_key.split(":", 1)[1].split("+")
    if len(ids) != 2:
        return None
    models = _models(conn)
    a, b = _resolve(models, ids[0]), _resolve(models, ids[1])
    if a is None or b is None:
        return None
    first, second, how = direction(title, a, b)
    out = migration(conn, first["id"], second["id"], models=models)
    return {**out, "order": how} if out else None
