"""The "AI in industries" page: how much data the Industry AI agent holds.

COUNTS ONLY, BY CONSTRUCTION. Nothing leaves this module that could identify a
post: no title, no text, no URL, no author. Every figure is a count over
`iai_item` (rule 3), computed live when the page asks (rule 11), and each comes
with its denominator - items collected and items filtered out by reason - so
"few kept" never reads as "nothing found" (rules 4 and 7).

Reads `iai_item` and `iai_run`, which collect/industry_ai/ writes; never
imports collect/ (tests/test_lane_boundary.py), so the domain names and
definitions are read from contract/industry_ai.yaml directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contract" / "industry_ai.yaml"

#: The page's type order, the contract's precedence order.
UNCONFIRMED = "unconfirmed"
#: A kept post the OBSERVER found (a watched community, account or list) that names
#: no industry at all: general AI news and opinion (anooj, 2026-11-20). A different
#: absence from UNCONFIRMED - a keyword query's own domain not confirmed - so the
#: two are counted apart (rule 4). Flagged `general_ai` by the labeller.
GENERAL = "general"
#: THE BUCKET EXPRESSION is written out IN EACH QUERY below, identically, rather
#: than held in one constant: scripts/audit_columns.py finds a column's reader by
#: reading SQL literals that name the table and the column together (rule 9), and
#: a constant without `FROM iai_item` hid `domains` and `flags` from it (found by
#: tests/test_column_states.py, 2026-11-20). tests/test_industry_ai_observer.py
#: checks the two copies stay identical, so the buckets cannot disagree.


def _contract() -> dict:
    raw = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "domains" not in raw or "type_order" not in raw:
        raise ValueError("contract/industry_ai.yaml needs `domains` and `type_order`")
    return raw


def _count_by(conn, column: str, where: str = "verdict = 'kept'") -> dict[str, dict[str, int]]:
    """domain -> value -> kept items, with "general" or "unconfirmed" for an empty
    `domains` (the bucket expression; see GENERAL)."""
    out: dict[str, dict[str, int]] = {}
    for domain, value, n in conn.execute(
        "SELECT d, v, count(*) FROM ("
        "  SELECT CASE WHEN cardinality(domains) = 0 AND 'general_ai' = ANY(flags) "
        "THEN ARRAY['general'] WHEN cardinality(domains) = 0 THEN ARRAY['unconfirmed'] "
        f"ELSE domains END AS ds, {column} AS v FROM iai_item WHERE {where}"
        ") x, unnest(ds) AS d GROUP BY 1, 2"
    ).fetchall():
        if value is not None:
            out.setdefault(domain, {})[str(value)] = int(n)
    return out


def industry_ai_view(conn) -> dict[str, Any]:
    contract = _contract()
    try:
        total, kept = conn.execute(
            "SELECT count(*), count(*) FILTER (WHERE verdict = 'kept') FROM iai_item"
        ).fetchone()
    except Exception as e:  # noqa: BLE001 - an unmigrated database is a state, not a crash
        conn.rollback()
        return {
            "domains": [],
            "reason": f"the Industry AI tables could not be read "
            f"({type(e).__name__}) - run `python -m collect.cli db migrate`",
        }

    by_type = _count_by(conn, "content_type")
    by_platform = _count_by(conn, "platform")
    by_stage = _count_by(conn, "stage_guess")
    by_month = _count_by(conn, "to_char(date_trunc('month', created_at), 'YYYY-MM')")
    rows = conn.execute(
        "SELECT d, count(*), count(DISTINCT (platform, author_id)) "
        "  FILTER (WHERE author_id IS NOT NULL), coalesce(sum(share_count), 0), "
        "  count(*) FILTER (WHERE created_at IS NULL) FROM ("
        "  SELECT CASE WHEN cardinality(domains) = 0 AND 'general_ai' = ANY(flags) "
        "THEN ARRAY['general'] WHEN cardinality(domains) = 0 THEN ARRAY['unconfirmed'] "
        "ELSE domains END AS ds, platform, author_id, share_count, created_at "
        "  FROM iai_item WHERE verdict = 'kept'"
        ") x, unnest(ds) AS d GROUP BY 1"
    ).fetchall()
    stats = {
        d: {"kept": int(n), "authors": int(a), "reach": int(r), "undated": int(u)}
        for d, n, a, r, u in rows
    }
    found = {
        d: int(n)
        for d, n in conn.execute(
            "SELECT d, count(*) FROM iai_item, unnest(domain_hints) AS d GROUP BY 1"
        ).fetchall()
    }
    dropped = [
        {"stage": s, "reason": r, "items": int(n)}
        for s, r, n in conn.execute(
            "SELECT drop_stage, drop_reason, count(*) FROM iai_item WHERE verdict = 'dropped' "
            "GROUP BY 1, 2 ORDER BY 3 DESC"
        ).fetchall()
    ]
    # KEPT ITEMS PER GROUP, "<domain>/<group>" (#644 review, point 3).
    by_group: dict[str, dict[str, int]] = {}
    for g, n in conn.execute(
        "SELECT g, count(*) FROM iai_item, unnest(groups) AS g WHERE verdict = 'kept' GROUP BY 1"
    ).fetchall():
        d, _, gk = g.partition("/")
        by_group.setdefault(d, {})[gk] = int(n)
    last = conn.execute(
        "SELECT id, mode, status, started_at, finished_at, requests FROM iai_run "
        "ORDER BY started_at DESC LIMIT 1"
    ).fetchone()

    def block(
        key: str,
        name: str,
        definition: str | None,
        kind: str | None = None,
        active: bool | None = None,
        groups: dict | None = None,
    ) -> dict:
        s = stats.get(key, {"kept": 0, "authors": 0, "reach": 0, "undated": 0})
        return {
            "key": key,
            "name": name,
            "definition": definition,
            "kind": kind,
            "active": active,
            # Each group's kept items, in the contract's order (0 when none).
            "groups": [
                {
                    "key": gk,
                    "name": (g or {}).get("name", gk),
                    "kept": by_group.get(key, {}).get(gk, 0),
                }
                for gk, g in (groups or {}).items()
            ],
            # How many items its queries found (before any rule), and how many
            # were kept under it: the denominator beside the count (rule 7).
            "found": found.get(key),
            **s,
            "by_type": by_type.get(key, {}),
            "by_platform": by_platform.get(key, {}),
            "by_stage": by_stage.get(key, {}),
            "by_month": dict(sorted(by_month.get(key, {}).items())),
        }

    domains = [
        block(
            k,
            d.get("name", k),
            d.get("definition"),
            d.get("kind"),
            d.get("active"),
            d.get("groups"),
        )
        for k, d in contract["domains"].items()
    ]
    return {
        "domains": domains,
        # Kept, but no finding domain's terms confirmed it: counted here, never
        # in a domain's total (rule 6).
        "unconfirmed": block(UNCONFIRMED, "Domain unconfirmed", None),
        # Kept from a watched source, naming no industry: general AI news and
        # opinion, counted apart from "unconfirmed" (rule 4).
        "general": block(GENERAL, "General AI", None),
        "collected": int(total),
        "kept": int(kept),
        "dropped": dropped,
        "types": list(contract["type_order"]),
        "pipeline_version": contract.get("pipeline_version"),
        "last_run": None
        if last is None
        else {
            "id": last[0],
            "mode": last[1],
            "status": last[2],
            "started_at": last[3].isoformat() if last[3] else None,
            "finished_at": last[4].isoformat() if last[4] else None,
            "requests": last[5] or {},
        },
    }
