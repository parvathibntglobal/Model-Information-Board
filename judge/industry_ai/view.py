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

import re
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
        f"ELSE domains END AS ds, flags AS fl, {column} AS v FROM iai_item WHERE {where}"
        ") x, unnest(ds) AS d "
        # A post a WATCH LIST filed under this domain by its terms is counted apart
        # (`from_watch`), never in the domain's own figures (anooj, 2026-11-20, (a)).
        "WHERE NOT ('domain_from_terms:' || d = ANY(fl)) GROUP BY 1, 2"
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
    # AUTHORS: a person mapped in `watch.people` is ONE author on every platform -
    # their `person:<key>` flag, set by collect/industry_ai/pipeline.py, which counts
    # the same way. Anyone else is one author per (platform, account).
    rows = conn.execute(
        "SELECT d, count(*), count(DISTINCT coalesce(person, platform || ':' || author_id)) "
        "  FILTER (WHERE person IS NOT NULL OR author_id IS NOT NULL), "
        "  coalesce(sum(share_count), 0), "
        "  count(*) FILTER (WHERE created_at IS NULL) FROM ("
        "  SELECT CASE WHEN cardinality(domains) = 0 AND 'general_ai' = ANY(flags) "
        "THEN ARRAY['general'] WHEN cardinality(domains) = 0 THEN ARRAY['unconfirmed'] "
        "ELSE domains END AS ds, flags AS fl, platform, author_id, share_count, created_at, "
        "(SELECT min(f) FROM unnest(flags) AS f WHERE left(f, 7) = 'person:') AS person "
        "  FROM iai_item WHERE verdict = 'kept'"
        ") x, unnest(ds) AS d WHERE NOT ('domain_from_terms:' || d = ANY(fl)) GROUP BY 1"
    ).fetchall()
    stats = {
        d: {"kept": int(n), "authors": int(a), "reach": int(r), "undated": int(u)}
        for d, n, a, r, u in rows
    }
    # FROM THE WATCH LISTS, COUNTED APART (anooj, 2026-11-20, option (a)): a domain's
    # own figures count what ITS keyword queries found and confirmed; a watched post
    # filed there by its terms (option A) is a different population, shown beside them.
    from_watch = {
        d: int(n)
        for d, n in conn.execute(
            "SELECT d, count(*) FROM iai_item, unnest(domains) AS d WHERE verdict = 'kept' "
            "AND 'domain_from_terms:' || d = ANY(flags) GROUP BY 1"
        ).fetchall()
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
        "SELECT g, count(*) FROM iai_item, unnest(groups) AS g WHERE verdict = 'kept' "
        "AND NOT ('domain_from_terms:' || split_part(g, '/', 1) = ANY(flags)) GROUP BY 1"
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
            # Kept posts the watch lists filed here by their terms: NOT in `kept` or in
            # any breakdown above, shown beside them (option (a)).
            "from_watch": from_watch.get(key, 0),
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


# ── THE INFO PAGE (2026-11-24, Parvathi) ─────────────────────────────────────
# What the agent searches for and how it decides, read from the contract as it
# stands: every domain's keywords, ambiguous terms and their context words,
# exclusions and queries; the AI terms; the run and watch settings; the filter
# and type patterns. Nothing here is read from the database and nothing is a
# count of stored items, so it renders before any run has happened. Values are
# passed through as the contract writes them: a number in this payload is a
# setting, never a measurement (rule 3).

#: The contract's pattern lists, in the order the page shows them.
_PATTERN_LISTS = ("spam_patterns", "ad_patterns", "hiring_patterns", "promo_patterns",
                  "teach_patterns")


def _terms_block(b: dict) -> dict[str, Any]:
    """One domain's or group's own terms, ambiguous terms, exclusions and queries."""
    queries = b.get("queries") or {}
    return {
        "terms": list(b.get("domain_terms") or []),
        "ambiguous": [{"term": t, "context": list(ctx or [])}
                      for t, ctx in (b.get("ambiguous_terms") or {}).items()],
        "exclude_phrases": list(b.get("exclude_phrases") or []),
        # platform -> {"search": [...], "subreddits": [...]}; feeds is a plain list.
        "queries": {
            p: ({"search": list(q)} if isinstance(q, list)
                else {k: list(v or []) for k, v in (q or {}).items()})
            for p, q in queries.items()
        },
    }


def industry_ai_info() -> dict[str, Any]:
    c = _contract()
    run = c.get("run") or {}
    watch = c.get("watch") or {}
    domains = []
    for k, d in c["domains"].items():
        domains.append({
            "key": k,
            "name": d.get("name", k),
            "kind": d.get("kind"),
            "active": d.get("active"),
            "definition": d.get("definition"),
            **_terms_block(d),
            "groups": [{"key": gk, "name": (g or {}).get("name", gk),
                        "definition": (g or {}).get("definition"), **_terms_block(g or {})}
                       for gk, g in (d.get("groups") or {}).items()],
        })
    return {
        "pipeline_version": c.get("pipeline_version"),
        "run": {
            "enabled": run.get("enabled"),
            "cadence": run.get("cadence"),
            "window_days": run.get("window_days"),
            "max_requests": run.get("max_requests") or {},
            "pages_per_query": run.get("pages_per_query") or {},
            "min_text_chars": run.get("min_text_chars"),
            "context_window_words": run.get("context_window_words"),
            # 2026-11-25: the smaller settings that explain some drops and flags.
            "low_engagement_max": run.get("low_engagement_max"),
            "x_clubbed_min_keywords": run.get("x_clubbed_min_keywords"),
        },
        # TEXT RETENTION (contract `retention:`), shown on the Info view
        # (2026-11-25): when a post's words are emptied, and for which posts.
        "retention": {
            "clear_text_after_days": (c.get("retention") or {}).get("clear_text_after_days"),
            "dropped": (c.get("retention") or {}).get("dropped"),
            "kept_domains": list((c.get("retention") or {}).get("kept_domains") or []),
        },
        "query_suffix": c.get("query_suffix") or {},
        "ai_terms": list(c.get("ai_terms") or []),
        "global_exclude_phrases": list(c.get("global_exclude_phrases") or []),
        "patterns": {k: list(c.get(k) or []) for k in _PATTERN_LISTS},
        "type_patterns": {t: list(v or []) for t, v in (c.get("type_patterns") or {}).items()},
        "stage_patterns": {s: list(v or []) for s, v in (c.get("stage_patterns") or {}).items()},
        "types": list(c["type_order"]),
        "watch": {
            "enabled": watch.get("enabled"),
            "lookback_days": watch.get("lookback_days"),
            "max_requests": watch.get("max_requests") or {},
            "sources": {p: watch[p] for p in ("reddit", "x", "bluesky", "hackernews")
                        if p in watch},
            # ONE PERSON, SEVERAL HANDLES (`watch.people`, #653): who is counted as
            # one author across platforms. Handles only; the Bluesky DID is an id the
            # code matches on, not something a reader needs.
            "people": [
                {"key": k, "handles": {p: h for p, h in (hs or {}).items() if p != "bluesky_did"}}
                for k, hs in (watch.get("people") or {}).items()
            ],
            "cross_post_hours": watch.get("cross_post_hours"),
            "x_pages": watch.get("x_pages"),
            "x_club_max": watch.get("x_club_max"),
            "x_suffix": watch.get("x_suffix"),
        },
        "domains": domains,
    }


# ── Admin -> Board & content -> AI in industries (2026-11-25, Parvathi) ────────
# The state of the Industry AI data, for the team: which rules the stored labels
# were made with against the contract's, the last runs and their requests
# against the caps, posts saved but not labelled, and text retention. Counts and
# settings only - no post text, link or author. The on/off switch for scheduled
# runs (INDUSTRY_AI_ENABLED) is not read here: Admin -> Scheduler reads it.

#: Runs listed, newest first.
ADMIN_RUNS = 5


def _run_detail(status: str, detail: str | None) -> str | None:
    """An ok run's detail is the script's own summary ("N new item(s); ...").
    An error's detail can carry anything the failure printed - a host name, a
    path - so only what the script itself wrote (what was saved) and the
    exception's type name are sent; the rest stays in the run log."""
    if not detail:
        return None
    if status == "ok":
        return detail
    m = _RUN_ERROR.match(detail)
    if m:
        return f"{m.group(1)} {m.group(2)}" if m.group(1) else m.group(2)
    return "error (the run log has the details)"


#: scripts/run_industry_ai.py's error detail: an optional "what was saved." then
#: "<ExceptionType>: <message>".
_RUN_ERROR = re.compile(
    r"^((?:\d+ new item\(s\) SAVED before the error;[^.]*?(?:\([^)]*\))?\.|nothing saved\.)?)\s*"
    r"([A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt|Warning)):"
)


def industry_ai_admin(conn) -> dict[str, Any]:
    c = _contract()
    run = c.get("run") or {}
    watch = c.get("watch") or {}
    ret = c.get("retention") or {}
    out: dict[str, Any] = {
        "pipeline_version": c.get("pipeline_version"),
        "harvest_enabled": run.get("enabled"),
        "watch_enabled": watch.get("enabled"),
        "caps": run.get("max_requests") or {},
        "watch_caps": watch.get("max_requests") or {},
        "retention": {
            "clear_text_after_days": ret.get("clear_text_after_days"),
            "dropped": ret.get("dropped"),
            "kept_domains": list(ret.get("kept_domains") or []),
        },
    }
    try:
        total, kept, pending, cleared = conn.execute(
            "SELECT count(*), count(*) FILTER (WHERE verdict = 'kept'), "
            "count(*) FILTER (WHERE drop_stage = 'pending'), "
            "count(*) FILTER (WHERE text_cleared_at IS NOT NULL) FROM iai_item"
        ).fetchone()
        versions = {
            v: int(n) for v, n in conn.execute(
                "SELECT pipeline_version, count(*) FROM iai_item "
                "WHERE drop_stage IS DISTINCT FROM 'pending' GROUP BY 1 ORDER BY 1"
            ).fetchall()
        }
        due = None
        if ret.get("clear_text_after_days") is not None:
            # The same rows collect/industry_ai/store.py clear_text would empty now.
            (due,) = conn.execute(
                "SELECT count(*) FROM iai_item WHERE text_cleared_at IS NULL "
                "AND first_seen_at < now() - make_interval(days => %(d)s) "
                "AND ((%(dropped)s AND verdict = 'dropped') "
                "     OR (verdict = 'kept' AND domains && %(kept)s::text[]))",
                {"d": int(ret["clear_text_after_days"]), "dropped": bool(ret.get("dropped")),
                 "kept": list(ret.get("kept_domains") or [])},
            ).fetchone()
        runs = conn.execute(
            "SELECT started_at, finished_at, mode, status, pipeline_version, requests, detail "
            "FROM iai_run ORDER BY started_at DESC LIMIT %s", (ADMIN_RUNS,)
        ).fetchall()
    except Exception as e:  # noqa: BLE001 - an unmigrated database is a state, not a crash
        conn.rollback()
        out["unreadable"] = (f"the Industry AI tables could not be read ({type(e).__name__}) "
                             "- run `python -m collect.cli db migrate`")
        return out
    out.update(
        items={"stored": int(total), "kept": int(kept), "pending": int(pending),
               "text_cleared": int(cleared), "text_due": None if due is None else int(due)},
        # Labelled rows by the rules version that labelled them; `pending` rows
        # carry none yet and are counted apart.
        versions=versions,
        runs=[
            {"started_at": r[0].isoformat(), "finished_at": r[1].isoformat() if r[1] else None,
             "mode": r[2], "status": r[3], "pipeline_version": r[4],
             "requests": r[5] or {}, "detail": _run_detail(r[3], r[6])}
            for r in runs
        ],
    )
    return out
