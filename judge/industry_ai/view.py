"""The "AI in industries" page: how much data the Industry AI agent holds.

`industry_ai_view` (the summary) is COUNTS ONLY, BY CONSTRUCTION: nothing it
returns could identify a post - no title, no text, no URL, no author.
`industry_ai_domain_view` (one domain's page, 2026-11-24) is the one that DOES
list posts, as excerpts with their links; see its section below. Every figure is a count over
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
    # No by-month counts here since 2026-11-24: the summary's cards dropped the month
    # chart (one spike, the harvest window), and the domain page counts its own months.
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
    # SAVED BUT NOT YET LABELLED IS NOT "FILTERED OUT" (#663 review, Parvathi). The store
    # inserts every new row as verdict 'dropped', drop_stage 'pending', and labelling
    # overwrites both. A run whose labelling failed leaves its harvest in that state:
    # nothing judged those posts, so they are counted apart, never as a reason our rules
    # dropped something (rules 4 and 6). collected = kept + dropped + pending.
    dropped = [
        {"stage": s, "reason": r, "items": int(n)}
        for s, r, n in conn.execute(
            "SELECT drop_stage, drop_reason, count(*) FROM iai_item WHERE verdict = 'dropped' "
            "AND drop_stage IS DISTINCT FROM 'pending' GROUP BY 1, 2 ORDER BY 3 DESC"
        ).fetchall()
    ]
    (pending,) = conn.execute(
        "SELECT count(*) FROM iai_item WHERE verdict = 'dropped' AND drop_stage = 'pending'"
    ).fetchone()
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
        # Saved, waiting to be labelled (a run's labelling failed): read by
        # web/src/routes/IndustryAI.jsx, the totals row and its note.
        "pending": int(pending),
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
        # `rules_version`, not `pipeline_version` (#668 review): the field-name audit
        # matches names across payloads, and /coverage's own field has no reader.
        "rules_version": c.get("pipeline_version"),
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
        # A domain's page shows each post's text up to this many characters (#665),
        # so the Info view can say so without writing the number (#668 review, 3).
        "excerpt_chars": EXCERPT_CHARS,
        # What each rules version changed (contract `versions:`, #668 review Q2).
        "versions": {str(k): str(v) for k, v in (c.get("versions") or {}).items()},
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
            "sources": {
                **{p: watch[p] for p in ("reddit", "x", "bluesky", "hackernews") if p in watch},
                # INSTAGRAM (#667): `[handle, "id"]` pairs; the handle only, as the
                # Bluesky DID is left out of `people` - the id is for the code.
                **({"instagram": [e[0] if isinstance(e, (list, tuple)) else e
                                  for e in watch["instagram"]]}
                   if watch.get("instagram") else {}),
            },
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


def _requests_by_agent(total: dict, queries: list) -> dict[str, dict[str, int]]:
    """A run's requests per platform, split: the observer's are its queries with
    domain "watch" (collect/industry_ai/harvest.py); the keyword agent's are the
    rest of the run's total, so the two always add up to what the run spent."""
    watch: dict[str, int] = {}
    for q in queries:
        if isinstance(q, dict) and q.get("domain") == "watch":
            p = q.get("platform")
            watch[p] = watch.get(p, 0) + int(q.get("requests") or 0)
    # Not clamped at 0 (#668 review): watch queries summing past the run's total
    # would be an inconsistency, and a negative figure shows it where 0 would hide it.
    keyword = {p: int(n or 0) - watch.get(p, 0) for p, n in total.items()}
    return {"requests_keyword": {p: n for p, n in keyword.items() if n},
            "requests_watch": {p: n for p, n in watch.items() if n}}


def industry_ai_admin(conn) -> dict[str, Any]:
    c = _contract()
    run = c.get("run") or {}
    watch = c.get("watch") or {}
    ret = c.get("retention") or {}
    out: dict[str, Any] = {
        # `rules_version`, not `pipeline_version` (#668 review): the field-name audit
        # matches names across payloads, and this one is read here only.
        "rules_version": c.get("pipeline_version"),
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
            "SELECT started_at, finished_at, mode, status, pipeline_version, requests, detail, "
            "queries "
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
             "mode": r[2], "status": r[3], "rules_version": r[4],
             # REQUESTS BY AGENT (#668 review, point 6, rule 7): `iai_run.requests` is
             # the run's total per platform, keyword and watch together, while each
             # agent has its own cap. Each figure is shown against its own cap.
             **_requests_by_agent(r[5] or {}, r[7] or []),
             "detail": _run_detail(r[3], r[6])}
            for r in runs
        ],
    )
    return out
# ── ONE DOMAIN, IN DETAIL (2026-11-24, Parvathi) ──────────────────────────────
#
# The page a domain card opens (/ai-in-industries/<key>): the same counts as the
# card, every breakdown the stored labels allow, and the posts themselves - each
# post's text UP TO ITS FIRST `EXCERPT_CHARS` CHARACTERS, with its link, author id,
# date, engagement and every label the rules gave it. MOST POSTS ARE SHORTER, SO
# ARE SHOWN WHOLE (#665 review: on 2026-11-25, 5,476 of the 7,693 stored posts with
# text were 600 characters or fewer - every Bluesky and dev.to post, most X posts).
# SIGNED-IN ONLY, like the summary (judge/gate.py), and unlike the summary it does
# carry post text: the summary above stays counts-only.
#
# WHAT A ROW IS - post, comment, issue, article - is not a stored column. It is
# read from the platform's own id and link, exactly, where they say it:
#   reddit      t3_ = post, t1_ = comment
#   github      /issues/ = issue, /pull/ = pull request, /discussions/ = discussion
#   hackernews  a title = story; no title = a comment (a watched author's),
#               unless retention cleared the text: then "unknown" (rule 6)
#   devto, feeds  article
#   x, bluesky  post: a reply is NOT told apart from a post (nothing stored says)
#   instagram   post: an account's own feed, read by the observer only

EXCERPT_CHARS = 600
PAGE_MAX = 100
SCOPES = ("kept", "from_watch", "dropped")
SORTS = ("newest", "oldest", "engaged", "first_seen")

#: The row kind, from the platform's own id and link (see above).
_KIND = (
    "CASE platform "
    "WHEN 'reddit' THEN CASE WHEN left(external_id, 3) = 't1_' THEN 'comment' "
    "  WHEN left(external_id, 3) = 't3_' THEN 'post' ELSE 'unknown' END "
    "WHEN 'github' THEN CASE WHEN url LIKE '%%/pull/%%' THEN 'pull_request' "
    "  WHEN url LIKE '%%/discussions/%%' THEN 'discussion' "
    "  WHEN url LIKE '%%/issues/%%' THEN 'issue' ELSE 'unknown' END "
    "WHEN 'hackernews' THEN CASE WHEN coalesce(title, '') <> '' THEN 'story' "
    "  WHEN text_cleared_at IS NOT NULL THEN 'unknown' ELSE 'comment' END "
    "WHEN 'devto' THEN 'article' WHEN 'feeds' THEN 'article' "
    "WHEN 'x' THEN 'post' WHEN 'bluesky' THEN 'post' WHEN 'instagram' THEN 'post' "
    "ELSE 'unknown' END"
)
#: Engagement summed into one number to SORT by, and never shown (rule 3, first
#: exception): the page says in words that "most engaged" orders by the
#: platform's own counts added together.
_ENGAGED = (
    "(SELECT coalesce(sum(v::numeric), 0) FROM jsonb_each_text(engagement) AS e(k, v) "
    "WHERE k <> 'upvote_ratio' AND v ~ '^[0-9]+$')"
)


class DomainNotFound(LookupError):
    pass


class BadFilter(ValueError):
    pass


def _scope_where(key: str, scope: str) -> tuple[str, dict]:
    """The rows a domain page lists, by the same rules the summary counts with."""
    if key in (GENERAL, UNCONFIRMED):
        if scope != "kept":
            raise BadFilter(f"'{key}' holds kept items only")
        neg = "" if key == GENERAL else "NOT "
        return (
            f"verdict = 'kept' AND cardinality(domains) = 0 AND {neg}('general_ai' = ANY(flags))",
            {},
        )
    if scope == "kept":
        return (
            "verdict = 'kept' AND %(d)s = ANY(domains) "
            "AND NOT ('domain_from_terms:' || %(d)s = ANY(flags))",
            {"d": key},
        )
    if scope == "from_watch":
        return (
            "verdict = 'kept' AND %(d)s = ANY(domains) "
            "AND 'domain_from_terms:' || %(d)s = ANY(flags)",
            {"d": key},
        )
    # NOT A POST WAITING FOR ITS LABELS (#665 review, point 2): since #663 a post
    # saved before a labelling failure is stored as verdict 'dropped', drop_stage
    # 'pending'. It was never filtered out, so it is never counted or listed here.
    return (
        "verdict = 'dropped' AND drop_stage IS DISTINCT FROM 'pending' "
        "AND %(d)s = ANY(domain_hints)",
        {"d": key},
    )


def _like(text: str) -> str:
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def industry_ai_domain_view(
    conn,
    key: str,
    *,
    scope: str = "kept",
    filters: dict | None = None,
    sort: str = "newest",
    offset: int = 0,
    limit: int = 25,
) -> dict[str, Any]:
    """One domain's page: its counts, every breakdown, and a page of its posts."""
    contract = _contract()
    domains = contract["domains"]
    if key not in domains and key not in (GENERAL, UNCONFIRMED):
        raise DomainNotFound(key)
    if scope not in SCOPES:
        raise BadFilter(f"scope must be one of {', '.join(SCOPES)}")
    if sort not in SORTS:
        raise BadFilter(f"sort must be one of {', '.join(SORTS)}")
    if offset < 0 or not 1 <= limit <= PAGE_MAX:
        raise BadFilter(f"offset must be 0 or more, and limit 1 to {PAGE_MAX}")
    d = domains.get(key) or {}
    f = {k: str(v) for k, v in (filters or {}).items() if v not in (None, "")}

    where, params = _scope_where(key, scope)
    params = {**params, "d": key}
    clauses = [where]
    for name, column in (
        ("type", "content_type"),
        ("platform", "platform"),
        ("stage", "stage_guess"),
        ("reason", "drop_reason"),
    ):
        if name in f:
            clauses.append(f"{column} = %({name})s")
            params[name] = f[name]
    if "kind" in f:
        clauses.append(f"({_KIND}) = %(kind)s")
        params["kind"] = f["kind"]
    if "flag" in f:
        clauses.append("%(flag)s = ANY(flags)")
        params["flag"] = f["flag"]
    if "group" in f:
        clauses.append("%(group)s = ANY(groups)")
        params["group"] = f"{key}/{f['group']}"
    if "term" in f:
        clauses.append("matched_terms -> %(d)s -> 'terms' ? %(term)s")
        params["term"] = f["term"]
    if "ai_term" in f:
        clauses.append("%(ai_term)s = ANY(ai_terms)")
        params["ai_term"] = f["ai_term"]
    if "query" in f:
        clauses.append("%(query)s = ANY(query_keys)")
        params["query"] = f["query"]
    if "month" in f:
        clauses.append("to_char(created_at, 'YYYY-MM') = %(month)s")
        params["month"] = f["month"]
    if "q" in f:
        clauses.append("(coalesce(title, '') || ' ' || coalesce(body, '')) ILIKE %(q)s")
        params["q"] = _like(f["q"])
    w = " AND ".join(f"({c})" for c in clauses)

    def facet(expr: str = "", *, unnest: str | None = None, top: int | None = None) -> list:
        if unnest:
            sql = (
                f"SELECT v, count(*) FROM iai_item, unnest({unnest}) AS v WHERE {w} "
                "GROUP BY 1 ORDER BY 2 DESC, 1"
            )
        else:
            sql = f"SELECT {expr}, count(*) FROM iai_item WHERE {w} GROUP BY 1 ORDER BY 2 DESC, 1"
        if top:
            sql += f" LIMIT {int(top)}"
        return [
            {"value": None if v is None else str(v), "items": int(n)}
            for v, n in conn.execute(sql, params).fetchall()
        ]

    head = conn.execute(
        "SELECT count(*), count(DISTINCT platform || ':' || author_id) "
        "FILTER (WHERE author_id IS NOT NULL), "
        "count(*) FILTER (WHERE created_at IS NULL), "
        "count(*) FILTER (WHERE link IS NOT NULL), "
        "count(*) FILTER (WHERE text_cleared_at IS NOT NULL), "
        f"min(created_at), max(created_at) FROM iai_item WHERE {w}",
        params,
    ).fetchone()

    all_flags = facet(unnest="flags")
    flags = [x for x in all_flags if not x["value"].startswith("person:")]
    people = sum(x["items"] for x in all_flags if x["value"].startswith("person:"))
    terms = [
        {"value": t, "items": int(n)}
        for t, n in conn.execute(
            "SELECT t, count(*) FROM iai_item, jsonb_array_elements_text("
            "coalesce(matched_terms -> %(d)s -> 'terms', '[]'::jsonb)) AS t "
            f"WHERE {w} GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 30",
            params,
        ).fetchall()
    ]
    groups = [
        {"value": g.partition("/")[2], "items": int(n)}
        for g, n in conn.execute(
            f"SELECT g, count(*) FROM iai_item, unnest(groups) AS g WHERE {w} "
            "AND split_part(g, '/', 1) = %(d)s GROUP BY 1 ORDER BY 2 DESC",
            params,
        ).fetchall()
    ]
    engagement = {
        k: int(n)
        for k, n in conn.execute(
            "SELECT k, sum(v::numeric) FROM iai_item, jsonb_each_text(engagement) AS e(k, v) "
            f"WHERE {w} AND k <> 'upvote_ratio' AND v ~ '^[0-9]+$' GROUP BY 1 ORDER BY 2 DESC",
            params,
        ).fetchall()
    }

    # Every scope's size, unfiltered, so each tab carries its denominator (rule 7).
    sizes: dict[str, int] = {}
    for s in SCOPES:
        try:
            sw, sp = _scope_where(key, s)
        except BadFilter:
            continue
        sizes[s] = int(
            conn.execute(f"SELECT count(*) FROM iai_item WHERE {sw}", {**sp, "d": key}).fetchone()[
                0
            ]
        )
    found = None
    if key in domains:
        found = int(
            conn.execute(
                "SELECT count(*) FROM iai_item WHERE %(d)s = ANY(domain_hints)", {"d": key}
            ).fetchone()[0]
        )

    order = {
        "newest": "created_at DESC NULLS LAST, id",
        "oldest": "created_at ASC NULLS LAST, id",
        "engaged": f"{_ENGAGED} DESC, created_at DESC NULLS LAST, id",
        "first_seen": "first_seen_at DESC, id",
    }[sort]
    rows = conn.execute(
        f"SELECT id, platform, ({_KIND}), url, title, "
        f"left(coalesce(body, ''), {EXCERPT_CHARS + 1}), created_at, author_id, lang, "
        "engagement, link, canonical_url, share_count, content_type, matched_pattern, "
        "stage_guess, flags, domains, groups, matched_terms -> %(d)s -> 'terms', "
        "ai_terms, query_keys, domain_hints, verdict, drop_stage, drop_reason, "
        "first_seen_at, text_cleared_at, canonical_of "
        f"FROM iai_item WHERE {w} ORDER BY {order} OFFSET %(off)s LIMIT %(lim)s",
        {**params, "off": offset, "lim": limit},
    ).fetchall()

    def iso(t):
        return t.isoformat() if t else None

    items = []
    for r in rows:
        body = r[5] or ""
        items.append(
            {
                "id": r[0],
                "platform": r[1],
                "kind": r[2],
                "url": r[3],
                "title": r[4] or "",
                "excerpt": body[:EXCERPT_CHARS],
                "excerpt_cut": len(body) > EXCERPT_CHARS,
                "created_at": iso(r[6]),
                "author_id": r[7],
                "lang": r[8],
                "engagement": {k: v for k, v in (r[9] or {}).items() if v is not None},
                "link": r[10],
                "canonical_url": r[11],
                "share_count": r[12] or 0,
                "content_type": r[13],
                "matched_pattern": r[14],
                "stage": r[15],
                "flags": list(r[16] or []),
                "domains": list(r[17] or []),
                "groups": [g.partition("/")[2] for g in (r[18] or []) if g.startswith(f"{key}/")],
                "terms": list(r[19] or []),
                "ai_terms": list(r[20] or []),
                "queries": list(r[21] or []),
                "domain_hints": list(r[22] or []),
                "verdict": r[23],
                "drop_stage": r[24],
                "drop_reason": r[25],
                "first_seen_at": iso(r[26]),
                "text_cleared_at": iso(r[27]),
                "duplicate_of": r[28],
            }
        )

    bucket_names = {GENERAL: "General AI", UNCONFIRMED: "Domain unconfirmed"}
    return {
        "name": d.get("name") or bucket_names.get(key, key),
        "definition": d.get("definition"),
        "kind": d.get("kind"),
        "active": d.get("active"),
        "group_names": {gk: (g or {}).get("name", gk) for gk, g in (d.get("groups") or {}).items()},
        "domain_terms": list(d.get("domain_terms") or []),
        "found": found,
        "scopes": sizes,
        "matching": int(head[0]),
        "authors": int(head[1]),
        "undated": int(head[2]),
        "with_link": int(head[3]),
        "text_cleared": int(head[4]),
        "first_posted": iso(head[5]),
        "last_posted": iso(head[6]),
        "mapped_people_items": people,
        "engagement": engagement,
        "facets": {
            "type": facet("content_type"),
            "kind": facet(_KIND),
            "platform": facet("platform"),
            "stage": facet("stage_guess"),
            "reason": facet("drop_reason") if scope == "dropped" else [],
            "month": sorted(
                facet("to_char(created_at, 'YYYY-MM')"), key=lambda x: x["value"] or ""
            ),
            "flag": flags,
            "term": terms,
            "ai_term": facet(unnest="ai_terms", top=30),
            "group": groups,
            "query": facet(unnest="query_keys", top=25),
        },
        "excerpt_chars": EXCERPT_CHARS,
        "items": items,
        # The contract's pipeline_version, named apart from /coverage's unread
        # `pipeline_version` field (contract/api_fields.yaml declares by name).
        "rules_version": contract.get("pipeline_version"),
    }
