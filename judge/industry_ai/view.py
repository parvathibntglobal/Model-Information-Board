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
#: THE TWO AGENTS' POPULATIONS (2026-11-25, Parvathi; anooj's proposal on #667).
#: A row's `query_keys` say which agent found it: `iai:<domain>:...` is a keyword
#: query, `watch:<platform>:<source>` a watch list. Each page counts ONE of them:
#:   KEYWORD_ARM  /ai-in-industries - a keyword query found it (a watch list may
#:                have found it too: it keeps the keyword agent's labels, #650);
#:   WATCH_ARM    /ai-watch - ONLY watch lists found it (`rules.is_watch_only`),
#:                or it is General AI, kept only because a watch list found it.
#: The two never overlap, so no post is counted on both pages (rule 7).
_GENERAL_FLAG = "coalesce('general_ai' = ANY(flags), false)"
_KEYWORD_FOUND = "EXISTS (SELECT 1 FROM unnest(query_keys) AS qk WHERE left(qk, 6) <> 'watch:')"
KEYWORD_ARM = f"({_KEYWORD_FOUND} AND NOT {_GENERAL_FLAG})"
WATCH_ARM = (f"({_GENERAL_FLAG} OR (cardinality(query_keys) > 0 AND NOT {_KEYWORD_FOUND}))")
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


def _count_by(conn, column: str, where: str = f"verdict = 'kept' AND {KEYWORD_ARM}"
              ) -> dict[str, dict[str, int]]:
    """domain -> value -> kept items, with "general" or "unconfirmed" for an empty
    `domains` (the bucket expression; see GENERAL)."""
    out: dict[str, dict[str, int]] = {}
    for domain, value, n in conn.execute(
        "SELECT d, v, count(*) FROM ("
        "  SELECT CASE WHEN cardinality(domains) = 0 AND 'general_ai' = ANY(flags) "
        "THEN ARRAY['general'] WHEN cardinality(domains) = 0 THEN ARRAY['unconfirmed'] "
        f"ELSE domains END AS ds, flags AS fl, {column} AS v FROM iai_item WHERE {where}"
        ") x, unnest(ds) AS d "
        # A post a WATCH LIST filed under this domain by its terms is never in the
        # domain's own figures (anooj, 2026-11-20, (a)); it is on /ai-watch.
        "WHERE NOT ('domain_from_terms:' || d = ANY(fl)) GROUP BY 1, 2"
    ).fetchall():
        if value is not None:
            out.setdefault(domain, {})[str(value)] = int(n)
    return out


def industry_ai_view(conn) -> dict[str, Any]:
    contract = _contract()
    try:
        total, kept = conn.execute(
            "SELECT count(*), count(*) FILTER (WHERE verdict = 'kept') FROM iai_item "
            f"WHERE {KEYWORD_ARM}"
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
        f"  FROM iai_item WHERE verdict = 'kept' AND {KEYWORD_ARM}"
        ") x, unnest(ds) AS d WHERE NOT ('domain_from_terms:' || d = ANY(fl)) GROUP BY 1"
    ).fetchall()
    stats = {
        d: {"kept": int(n), "authors": int(a), "reach": int(r), "undated": int(u)}
        for d, n, a, r, u in rows
    }
    # THE WATCH LISTS' POSTS ARE NOT COUNTED HERE (2026-11-25): a watched post filed
    # under a domain by its words, and General AI, are on /ai-watch (`ai_watch_view`).
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
    # dropped something (rules 4 and 6). NOT READABLE IS NOT "FILTERED OUT" EITHER
    # (2026-11-25, iai-5): a picture or video with too few words to judge (drop_stage
    # 'unread') was not read, so it is counted apart too.
    # collected = kept + dropped + pending + unread.
    dropped = [
        {"stage": s, "reason": r, "items": int(n)}
        for s, r, n in conn.execute(
            "SELECT drop_stage, drop_reason, count(*) FROM iai_item WHERE verdict = 'dropped' "
            f"AND drop_stage NOT IN ('pending', 'unread') AND {KEYWORD_ARM} "
            "GROUP BY 1, 2 ORDER BY 3 DESC"
        ).fetchall()
    ]
    pending, unread = conn.execute(
        "SELECT count(*) FILTER (WHERE drop_stage = 'pending'), "
        "count(*) FILTER (WHERE drop_stage = 'unread') FROM iai_item "
        f"WHERE verdict = 'dropped' AND {KEYWORD_ARM}"
    ).fetchone()
    # KEPT ITEMS PER GROUP, "<domain>/<group>" (#644 review, point 3).
    by_group: dict[str, dict[str, int]] = {}
    for g, n in conn.execute(
        "SELECT g, count(*) FROM iai_item, unnest(groups) AS g WHERE verdict = 'kept' "
        f"AND {KEYWORD_ARM} "
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
        "collected": int(total),
        "kept": int(kept),
        "dropped": dropped,
        # Saved, waiting to be labelled (a run's labelling failed): read by
        # web/src/routes/IndustryAI.jsx, the totals row and its note.
        "pending": int(pending),
        # A picture or video with too few words to judge (iai-5): read by
        # web/src/routes/IndustryAI.jsx, the totals row.
        "unread": int(unread),
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
            # iai-7 (2026-11-26 kept-post review): what matching ignores, and the
            # settings of the three flags that are not patterns.
            "match_strip": list(run.get("match_strip") or []),
            "ai_near_industry_words": run.get("ai_near_industry_words"),
            "reply_min_own_words": run.get("reply_min_own_words"),
            "heavy_poster_min_posts": run.get("heavy_poster_min_posts"),
            "long_post_words": run.get("long_post_words"),
            "weak_ai_terms": list(run.get("weak_ai_terms") or []),
        },
        # The flags set by a pattern (iai-7), each with the platforms it applies on
        # (None: all), for the Info view's patterns list.
        "flag_patterns": {
            k: {"platforms": None if (b or {}).get("platforms") == "all"
                else list((b or {}).get("platforms") or []),
                "patterns": list((b or {}).get("patterns") or [])}
            for k, b in (c.get("flag_patterns") or {}).items()
        },
        # TEXT RETENTION (contract `retention:`), shown on the Info view
        # (2026-11-25): when a post's words are emptied, and for which posts.
        "retention": {
            "clear_text_after_days": (c.get("retention") or {}).get("clear_text_after_days"),
            "dropped": (c.get("retention") or {}).get("dropped"),
            # Whether a "not readable" post (#676) is cleared with the dropped ones.
            "unread": (c.get("retention") or {}).get("unread"),
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


def _admin_run(r) -> dict[str, Any]:
    return {
        "started_at": r[0].isoformat(), "finished_at": r[1].isoformat() if r[1] else None,
        "mode": r[2], "status": r[3], "rules_version": r[4],
        # REQUESTS BY AGENT (#668 review, point 6, rule 7): `iai_run.requests` is the
        # run's total per platform, keyword and watch together, while each agent has
        # its own cap. Each figure is shown against its own cap.
        **_requests_by_agent(r[5] or {}, r[7] or []),
        "detail": _run_detail(r[3], r[6]),
    }


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
            "unread": ret.get("unread"),
            "kept_domains": list(ret.get("kept_domains") or []),
        },
    }
    try:
        total, kept, pending, cleared = conn.execute(
            "SELECT count(*), count(*) FILTER (WHERE verdict = 'kept'), "
            "count(*) FILTER (WHERE drop_stage = 'pending'), "
            "count(*) FILTER (WHERE text_cleared_at IS NOT NULL) FROM iai_item"
        ).fetchone()
        # EACH AGENT'S OWN POSTS (2026-11-25): Admin shows AI in industries and AI Watch
        # as two sections, each with the population its page counts (KEYWORD_ARM /
        # WATCH_ARM); `items` above stays the table's total, both together.
        # `unread` (#676 review, point 3): posts whose content is a picture or video
        # with too few words to judge, counted apart as the two pages count them.
        arms = {
            arm: {"stored": int(s), "kept": int(k), "pending": int(p), "unread": int(u)}
            for arm, (s, k, p, u) in (
                (arm, conn.execute(
                    "SELECT count(*), count(*) FILTER (WHERE verdict = 'kept'), "
                    "count(*) FILTER (WHERE drop_stage = 'pending'), "
                    f"count(*) FILTER (WHERE drop_stage = 'unread') FROM iai_item WHERE {where}"
                ).fetchone())
                for arm, where in (("keyword", KEYWORD_ARM), ("watch", WATCH_ARM))
            )
        }
        versions = {
            v: int(n) for v, n in conn.execute(
                "SELECT pipeline_version, count(*) FROM iai_item "
                "WHERE drop_stage IS DISTINCT FROM 'pending' GROUP BY 1 ORDER BY 1"
            ).fetchall()
        }
        due = None
        if ret.get("clear_text_after_days") is not None:
            # The same rows collect/industry_ai/store.py clear_text would empty now:
            # its RETENTION_DUE, copied because judge/ never imports collect/
            # (tests/test_lane_boundary.py). tests/test_industry_ai_media.py holds the
            # two to the same rows.
            (due,) = conn.execute(
                "SELECT count(*) FROM iai_item WHERE text_cleared_at IS NULL "
                "AND first_seen_at < now() - make_interval(days => %(d)s) "
                "AND ((%(dropped)s AND verdict = 'dropped' "
                "      AND (drop_stage IS DISTINCT FROM 'unread' OR %(unread)s)) "
                "     OR (verdict = 'kept' AND domains && %(kept)s::text[]))",
                {"d": int(ret["clear_text_after_days"]), "dropped": bool(ret.get("dropped")),
                 "unread": bool(ret.get("unread")),
                 "kept": list(ret.get("kept_domains") or [])},
            ).fetchone()
        runs = conn.execute(
            "SELECT started_at, finished_at, mode, status, pipeline_version, requests, detail, "
            "queries "
            "FROM iai_run ORDER BY started_at DESC LIMIT %s", (ADMIN_RUNS,)
        ).fetchall()
        # Admin -> AI Watch lists the observer's runs only (#673 review, point 1).
        watch_runs = conn.execute(
            "SELECT started_at, finished_at, mode, status, pipeline_version, requests, detail, "
            f"queries FROM iai_run WHERE {WATCH_RUN} ORDER BY started_at DESC LIMIT %s",
            (ADMIN_RUNS,),
        ).fetchall()
    except Exception as e:  # noqa: BLE001 - an unmigrated database is a state, not a crash
        conn.rollback()
        out["unreadable"] = (f"the Industry AI tables could not be read ({type(e).__name__}) "
                             "- run `python -m collect.cli db migrate`")
        return out
    out.update(
        items={"stored": int(total), "kept": int(kept), "pending": int(pending),
               "text_cleared": int(cleared), "text_due": None if due is None else int(due)},
        arms=arms,
        # Labelled rows by the rules version that labelled them; `pending` rows
        # carry none yet and are counted apart.
        versions=versions,
        runs=[_admin_run(r) for r in runs],
        watch_runs=[_admin_run(r) for r in watch_runs],
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
#: Two tabs since 2026-11-25: the watch lists' posts filed here by their words
#: (`from_watch`) moved to /ai-watch with the rest of the observer's posts.
SCOPES = ("kept", "dropped")
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
    """The rows a domain page lists, by the same rules the summary counts with.
    The keyword agent's posts only: General AI is on /ai-watch."""
    if key == UNCONFIRMED:
        if scope != "kept":
            raise BadFilter(f"'{key}' holds kept items only")
        return (
            "verdict = 'kept' AND cardinality(domains) = 0 AND NOT ('general_ai' = ANY(flags)) "
            f"AND {KEYWORD_ARM}",
            {},
        )
    if scope == "kept":
        return (
            "verdict = 'kept' AND %(d)s = ANY(domains) "
            "AND NOT ('domain_from_terms:' || %(d)s = ANY(flags))",
            {"d": key},
        )
    # NOT A POST WAITING FOR ITS LABELS (#665 review, point 2): since #663 a post
    # saved before a labelling failure is stored as verdict 'dropped', drop_stage
    # 'pending'. It was never filtered out, so it is never counted or listed here; nor
    # is a post not readable (drop_stage 'unread', iai-5), which was never read.
    return (
        "verdict = 'dropped' AND drop_stage NOT IN ('pending', 'unread') "
        "AND %(d)s = ANY(domain_hints)",
        {"d": key},
    )


def _like(text: str) -> str:
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


#: The orders a list of posts can take (SORTS).
_ORDER = {
    "newest": "created_at DESC NULLS LAST, id",
    "oldest": "created_at ASC NULLS LAST, id",
    "engaged": f"{_ENGAGED} DESC, created_at DESC NULLS LAST, id",
    "first_seen": "first_seen_at DESC, id",
}


def _items(conn, w: str, params: dict, *, sort: str, offset: int, limit: int,
           key: str | None) -> list[dict[str, Any]]:
    """A page of posts, each as both pages list it. `key` is the domain whose matched
    words and groups are shown; None (the AI Watch page) shows a post's groups under
    every domain it names and no matched words."""
    # ONE STRING LITERAL from SELECT to FROM iai_item (adjacent pieces only, no `+`):
    # scripts/audit_columns.py finds each column's reader by reading it whole (rule 9).
    terms = "matched_terms -> %(d)s -> 'terms'" if key else "NULL::jsonb"
    rows = conn.execute(
        f"SELECT id, platform, ({_KIND}), url, title, "
        f"left(coalesce(body, ''), {EXCERPT_CHARS + 1}), created_at, author_id, lang, "
        "engagement, link, canonical_url, share_count, content_type, matched_pattern, "
        f"stage_guess, flags, domains, groups, {terms}, "
        "ai_terms, query_keys, domain_hints, verdict, drop_stage, drop_reason, "
        "first_seen_at, text_cleared_at, canonical_of, media_text_from "
        f"FROM iai_item WHERE {w} ORDER BY {_ORDER[sort]} OFFSET %(off)s LIMIT %(lim)s",
        {**params, **({"d": key} if key else {}), "off": offset, "lim": limit},
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
                "groups": [g.partition("/")[2] for g in (r[18] or [])
                           if key is None or g.startswith(f"{key}/")],
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
                # WHICH TEXT THAT CAME WITH THE MEDIA was matched (#679 step 1): the
                # post card says so on a post flagged `terms_from_media_text`, whose
                # own words may show no AI term (#680 review, point 2). Read by
                # web/src/industry-ai/posts.jsx `MatchedInMedia`. [] = none recorded.
                "media_text_from": list(r[29] or []),
            }
        )
    return items


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
    if key not in domains and key != UNCONFIRMED:
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

    items = _items(conn, w, params, sort=sort, offset=offset, limit=limit, key=key)

    def iso(t):
        return t.isoformat() if t else None

    bucket_names = {UNCONFIRMED: "Domain unconfirmed"}
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


# ── AI WATCH: THE OBSERVER AGENT'S PAGE (2026-11-25, Parvathi; anooj's proposal on #667)
#
# /ai-watch, signed in. The posts only the watch lists found (WATCH_ARM): the newest
# posts of the watched communities, accounts and lists, which mostly name no industry
# (686 of 849 watch-only kept posts on 2026-11-25, two runs, anooj's count on #667).
# /ai-in-industries counts the keyword agent's posts only, so no post is on both.
#
#   ai_watch_view    counts: totals, by type and platform, every watched source's
#                    yield, mapped people, the industries watched posts name, drops
#   ai_watch_posts   a page of posts in one of WATCH_SCOPES, with its filters
#
# A SOURCE'S YIELD COUNTS EVERY POST THAT SOURCE FOUND, whichever page shows it: a post
# a keyword query also found is in its source's `found`, and `also_keyword` says how
# many, so the figure is the source's own and is never added to the page's totals.
# X watch queries club several accounts each, so an X account's yield is read from the
# handle in each post's link (`/<handle>/status/`), the way `rules.handle_of` reads it.

#: The AI Watch page's post lists.
WATCH_SCOPES = ("general", "mentions", "kept", "dropped", "unread")
#: `/i/status/` is X's anonymous form and names nobody (`rules.handle_of`; #673
#: review, point 6), so it is NULL - "no account in the link" - never an account "i".
_X_HANDLE_SQL = (
    r"nullif(lower(substring(url from "
    r"'^https://(?:x|twitter)\.com/([A-Za-z0-9_]{1,15})/status/')), 'i')"
)
#: A run that read at least one watch list (the observer's), from its own queries
#: (#673 review, point 1): since #670 the keyword run, a relabel or a keyword-only
#: run by hand is often the newest, and must not date the observer.
WATCH_RUN = ("EXISTS (SELECT 1 FROM jsonb_array_elements(coalesce(queries, '[]'::jsonb)) "
             "AS wq WHERE wq->>'domain' = 'watch')")
_DOMAIN_FLAG = "domain_from_terms:"


def _watch_scope(scope: str) -> str:
    if scope == "general":
        return "verdict = 'kept' AND 'general_ai' = ANY(flags)"
    if scope == "mentions":
        return f"verdict = 'kept' AND cardinality(domains) > 0 AND {WATCH_ARM}"
    if scope == "kept":
        return f"verdict = 'kept' AND {WATCH_ARM}"
    if scope == "unread":
        # A picture or video with too few words to judge (iai-5): listed with its link
        # so a person can look at it; never among what was filtered out.
        return f"verdict = 'dropped' AND drop_stage = 'unread' AND {WATCH_ARM}"
    # Not a post waiting for its labels (#663), nor one not readable: neither was judged.
    return f"verdict = 'dropped' AND drop_stage NOT IN ('pending', 'unread') AND {WATCH_ARM}"


def _watched_sources(watch: dict) -> list[dict[str, Any]]:
    """Every source the contract lists today, as the query key the harvest records
    (collect/industry_ai/config.py `watch_queries`), in the contract's order. X is
    listed per account; its posts are matched by handle, not by key."""
    out: list[dict[str, Any]] = []
    for s in watch.get("reddit") or []:
        out.append({"platform": "reddit", "source": f"r/{s}", "key": f"watch:reddit:r/{s}"})
    for h in watch.get("x") or []:
        out.append({"platform": "x", "source": f"@{h}", "account": str(h).lower()})
    for h in watch.get("bluesky") or []:
        out.append({"platform": "bluesky", "source": h, "key": f"watch:bluesky:from:{h}"})
    hn = watch.get("hackernews") or {}
    for t in hn.get("lists") or []:
        out.append({"platform": "hackernews", "source": t,
                    "key": f"watch:hackernews:hn:list:{t}"})
    for a in hn.get("authors") or []:
        out.append({"platform": "hackernews", "source": f"by {a}",
                    "key": f"watch:hackernews:hn:author:{a}"})
    for e in watch.get("instagram") or []:
        h = e[0] if isinstance(e, (list, tuple)) else e
        out.append({"platform": "instagram", "source": f"@{h}",
                    "key": f"watch:instagram:ig:{h}"})
    return out


def ai_watch_view(conn) -> dict[str, Any]:
    c = _contract()
    watch = c.get("watch") or {}
    try:
        # collected = kept + filtered + pending + unread (iai-5: a picture or video with
        # too few words to judge is not readable, counted apart from filtered out).
        total, kept, filtered, pending, unread = conn.execute(
            "SELECT count(*), count(*) FILTER (WHERE verdict = 'kept'), "
            "count(*) FILTER (WHERE verdict = 'dropped' "
            "AND drop_stage NOT IN ('pending', 'unread')), "
            "count(*) FILTER (WHERE drop_stage = 'pending'), "
            f"count(*) FILTER (WHERE drop_stage = 'unread') FROM iai_item WHERE {WATCH_ARM}"
        ).fetchone()
    except Exception as e:  # noqa: BLE001 - an unmigrated database is a state, not a crash
        conn.rollback()
        return {"reason": f"the Industry AI tables could not be read ({type(e).__name__}) "
                          "- run `python -m collect.cli db migrate`"}

    def counts(sql: str) -> dict[str, int]:
        return {str(k): int(n) for k, n in conn.execute(sql).fetchall() if k is not None}

    kept_w = f"verdict = 'kept' AND {WATCH_ARM}"
    # AUTHORS as the summary counts them: a mapped person (`person:<key>`) is one
    # author on every platform; anyone else is one per (platform, account).
    general, mentions_n, authors = conn.execute(
        "SELECT count(*) FILTER (WHERE 'general_ai' = ANY(flags)), "
        "count(*) FILTER (WHERE cardinality(domains) > 0), "
        "count(DISTINCT coalesce(person, platform || ':' || author_id)) "
        "  FILTER (WHERE person IS NOT NULL OR author_id IS NOT NULL) FROM ("
        "  SELECT flags, domains, platform, author_id, "
        "  (SELECT min(f) FROM unnest(flags) AS f WHERE left(f, 7) = 'person:') AS person "
        f"  FROM iai_item WHERE {kept_w}) x"
    ).fetchone()
    by_type = counts(f"SELECT content_type, count(*) FROM iai_item WHERE {kept_w} GROUP BY 1")
    by_platform = counts(f"SELECT platform, count(*) FROM iai_item WHERE {kept_w} GROUP BY 1")
    general_by_type = counts(
        "SELECT content_type, count(*) FROM iai_item "
        "WHERE verdict = 'kept' AND 'general_ai' = ANY(flags) GROUP BY 1")
    mentioned = counts(
        f"SELECT substr(f, {len(_DOMAIN_FLAG) + 1}), count(*) FROM iai_item, unnest(flags) AS f "
        f"WHERE {kept_w} AND left(f, {len(_DOMAIN_FLAG)}) = '{_DOMAIN_FLAG}' GROUP BY 1")
    dropped = [
        {"reason": r, "items": int(n)}
        for r, n in conn.execute(
            "SELECT drop_reason, count(*) FROM iai_item WHERE verdict = 'dropped' "
            f"AND drop_stage NOT IN ('pending', 'unread') AND {WATCH_ARM} "
            "GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall()
    ]
    # NOT READABLE, by what the media was (`media_kind`): which kind of content the
    # observer is missing most.
    unread_by_media = counts(
        "SELECT media_kind, count(*) FROM iai_item WHERE verdict = 'dropped' "
        f"AND drop_stage = 'unread' AND {WATCH_ARM} GROUP BY 1")

    # EVERY SOURCE'S YIELD: what it found (kept or not), what was kept and filtered
    # out, how many a keyword query also found, and its newest post.
    # `waiting` (saved, not yet labelled, #663) so found = kept + filtered + waiting
    # (#673 review, point 5); `kept_keyword`: kept posts a keyword query also found,
    # which the Feed does not list (they are the keyword agent's; point 4).
    tally = (
        "count(*), count(*) FILTER (WHERE verdict = 'kept'), "
        "count(*) FILTER (WHERE verdict = 'dropped' AND drop_stage NOT IN ('pending', 'unread')), "
        f"count(*) FILTER (WHERE {_KEYWORD_FOUND}), max(created_at), "
        "count(*) FILTER (WHERE drop_stage = 'pending'), "
        f"count(*) FILTER (WHERE verdict = 'kept' AND NOT ({WATCH_ARM})), "
        # Not readable (iai-5), so found = kept + filtered + waiting + unread.
        "count(*) FILTER (WHERE drop_stage = 'unread')"
    )
    by_key = {
        r[0]: r[1:]
        for r in conn.execute(
            f"SELECT qk_w, {tally} FROM iai_item, unnest(query_keys) AS qk_w "
            "WHERE left(qk_w, 6) = 'watch:' AND left(qk_w, 8) <> 'watch:x:' GROUP BY 1"
        ).fetchall()
    }
    by_account = {
        r[0]: r[1:]
        for r in conn.execute(
            f"SELECT {_X_HANDLE_SQL}, {tally} FROM iai_item WHERE platform = 'x' "
            "AND EXISTS (SELECT 1 FROM unnest(query_keys) AS k WHERE left(k, 8) = 'watch:x:') "
            "GROUP BY 1"
        ).fetchall()
    }

    def yield_of(row) -> dict[str, Any]:
        if row is None:
            return {"found": 0, "kept": 0, "filtered": 0, "waiting": 0, "unread": 0,
                    "also_keyword": 0, "kept_keyword": 0, "newest": None}
        f, k, d, a, newest, p, kk, u = row
        return {"found": int(f), "kept": int(k), "filtered": int(d), "waiting": int(p),
                "unread": int(u), "also_keyword": int(a), "kept_keyword": int(kk),
                "newest": newest.isoformat() if newest else None}

    sources = []
    for s in _watched_sources(watch):
        row = by_account.pop(s["account"], None) if "account" in s else by_key.pop(s["key"], None)
        sources.append({**s, "listed": True, **yield_of(row)})
    # Posts from a source the contract no longer lists: still counted, and named (rule 4).
    for k, row in sorted(by_key.items()):
        _, platform, q = k.split(":", 2)
        # Named as a listed source is (`_watched_sources`): "from:a" -> "a", "ig:a" -> "@a".
        source = (q.removeprefix("from:").removeprefix("hn:list:")
                  .replace("hn:author:", "by ", 1).replace("ig:", "@", 1))
        sources.append({"platform": platform, "source": source, "key": k, "listed": False,
                        **yield_of(row)})
    for h, row in sorted(by_account.items(), key=lambda x: x[0] or ""):
        sources.append({"platform": "x", "source": f"@{h}" if h else "no account in the link",
                        "account": h, "listed": False, **yield_of(row)})

    # ONE PERSON, SEVERAL HANDLES (`watch.people`): their kept posts here, by platform.
    person_rows: dict[str, dict[str, int]] = {}
    for key, platform, n in conn.execute(
        "SELECT substr(f, 8), platform, count(*) FROM iai_item, unnest(flags) AS f "
        f"WHERE {kept_w} AND left(f, 7) = 'person:' GROUP BY 1, 2"
    ).fetchall():
        person_rows.setdefault(key, {})[platform] = int(n)
    people = [
        {"key": k, "handles": {p: h for p, h in (hs or {}).items() if p != "bluesky_did"},
         "kept": sum(person_rows.get(k, {}).values()), "by_platform": person_rows.get(k, {})}
        for k, hs in (watch.get("people") or {}).items()
    ]

    last = conn.execute(
        "SELECT mode, status, started_at, finished_at FROM iai_run "
        f"WHERE {WATCH_RUN} ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    return {
        "enabled": watch.get("enabled"),
        "collected": int(total),
        "kept": int(kept),
        "filtered": int(filtered),
        "pending": int(pending),
        # Not readable (iai-5): a picture or video with too few words to judge, and the
        # media kinds those were. Read by web/src/routes/AIWatch.jsx.
        "unread": int(unread),
        "unread_by_media": unread_by_media,
        "general": int(general),
        "mentions": int(mentions_n),
        "authors": int(authors),
        "by_type": by_type,
        "general_by_type": general_by_type,
        "by_platform": by_platform,
        "dropped": dropped,
        # The industries watched posts name, each a count of kept posts; a post naming
        # two is counted under both, so these do not add up to `mentions`.
        "mentioned": [
            {"key": k, "name": (c["domains"].get(k) or {}).get("name", k), "items": n}
            for k, n in sorted(mentioned.items(), key=lambda x: -x[1])
        ],
        "sources": sources,
        "people": people,
        "last_run": None if last is None else {
            "mode": last[0], "status": last[1],
            "started_at": last[2].isoformat() if last[2] else None,
            "finished_at": last[3].isoformat() if last[3] else None,
        },
    }


def ai_watch_posts(
    conn,
    *,
    scope: str = "general",
    filters: dict | None = None,
    sort: str = "newest",
    offset: int = 0,
    limit: int = 25,
) -> dict[str, Any]:
    """A page of the observer's posts in one scope, with each filter's values."""
    if scope not in WATCH_SCOPES:
        raise BadFilter(f"scope must be one of {', '.join(WATCH_SCOPES)}")
    if sort not in SORTS:
        raise BadFilter(f"sort must be one of {', '.join(SORTS)}")
    if offset < 0 or not 1 <= limit <= PAGE_MAX:
        raise BadFilter(f"offset must be 0 or more, and limit 1 to {PAGE_MAX}")
    f = {k: str(v) for k, v in (filters or {}).items() if v not in (None, "")}
    clauses, params = [_watch_scope(scope)], {}
    for name, column in (("type", "content_type"), ("platform", "platform"),
                         ("reason", "drop_reason")):
        if name in f:
            clauses.append(f"{column} = %({name})s")
            params[name] = f[name]
    if "kind" in f:
        clauses.append(f"({_KIND}) = %(kind)s")
        params["kind"] = f["kind"]
    if "domain" in f:
        clauses.append("%(domain)s = ANY(flags)")
        params["domain"] = _DOMAIN_FLAG + f["domain"]
    if "source" in f:
        clauses.append("%(source)s = ANY(query_keys)")
        params["source"] = f["source"]
    if "account" in f:
        clauses.append(f"platform = 'x' AND {_X_HANDLE_SQL} = lower(%(account)s)")
        params["account"] = f["account"]
    if "person" in f:
        clauses.append("%(person)s = ANY(flags)")
        params["person"] = "person:" + f["person"]
    if "q" in f:
        clauses.append("(coalesce(title, '') || ' ' || coalesce(body, '')) ILIKE %(q)s")
        params["q"] = _like(f["q"])
    w = " AND ".join(f"({c})" for c in clauses)

    def facet(expr: str) -> list:
        return [{"value": None if v is None else str(v), "items": int(n)}
                for v, n in conn.execute(
                    f"SELECT {expr}, count(*) FROM iai_item WHERE {w} "
                    "GROUP BY 1 ORDER BY 2 DESC, 1", params).fetchall()]

    (matching,) = conn.execute(f"SELECT count(*) FROM iai_item WHERE {w}", params).fetchone()
    # Each scope's unfiltered size is in `ai_watch_view` (the page's tab counts).
    contract = _contract()
    return {
        "matching": int(matching),
        "facets": {
            "type": facet("content_type"),
            "platform": facet("platform"),
            "kind": facet(_KIND),
            "reason": facet("drop_reason") if scope == "dropped" else [],
            "domain": [
                {"value": v, "items": int(n)}
                for v, n in conn.execute(
                    f"SELECT substr(fl, {len(_DOMAIN_FLAG) + 1}), count(*) FROM iai_item, "
                    f"unnest(flags) AS fl WHERE {w} AND left(fl, {len(_DOMAIN_FLAG)}) = "
                    f"'{_DOMAIN_FLAG}' GROUP BY 1 ORDER BY 2 DESC, 1", params,
                ).fetchall()
            ],
        },
        "domain_names": {k: (d or {}).get("name", k) for k, d in contract["domains"].items()},
        "excerpt_chars": EXCERPT_CHARS,
        "items": _items(conn, w, params, sort=sort, offset=offset, limit=limit, key=None),
        "rules_version": contract.get("pipeline_version"),
    }
