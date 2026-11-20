"""The lane's only writer: `iai_item` and `iai_run`, and nothing else.

APPEND, THEN LABEL. A harvested item is inserted once; when a later run finds it
again only `last_seen_at`, its domain hints, query keys and engagement change.
The LABEL columns are rewritten by every run and every `--relabel`, because they
are the current rules' answer about a stored item, not evidence. No row is ever
deleted - a dropped item stays, with its stage and reason.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from collect.industry_ai.pipeline import Result
from collect.industry_ai.rules import Item

_COLUMNS = (
    "id",
    "platform",
    "external_id",
    "url",
    "title",
    "body",
    "created_at",
    "author_id",
    "lang",
    "engagement",
    "link",
    "discovery_ref",
    "domain_hints",
    "query_keys",
    "first_run_id",
)


def start_run(
    conn, run_id: str, *, mode: str, domains: list[str], platforms: list[str], pipeline_version: str
) -> None:
    conn.execute(
        "INSERT INTO iai_run (id, started_at, mode, status, domains, platforms, pipeline_version) "
        "VALUES (%s, %s, %s, 'running', %s, %s, %s)",
        (run_id, datetime.now(UTC), mode, domains, platforms, pipeline_version),
    )


def finish_run(
    conn,
    run_id: str,
    *,
    status: str,
    requests: dict,
    quota: dict,
    queries: list[dict],
    counts: dict,
    detail: str | None,
) -> None:
    conn.execute(
        "UPDATE iai_run SET finished_at = %s, status = %s, requests = %s, quota = %s, "
        "queries = %s, counts = %s, detail = %s WHERE id = %s",
        (
            datetime.now(UTC),
            status,
            json.dumps(requests),
            json.dumps(quota),
            json.dumps(queries),
            json.dumps(counts),
            detail,
            run_id,
        ),
    )


def upsert_items(conn, items: list[Item], *, run_id: str) -> int:
    """Insert new items; for known ones, widen hints and keys and refresh the
    seen time and engagement. Returns how many were new."""
    new = 0
    for it in items:
        row = {
            "id": it.id,
            "platform": it.platform,
            "external_id": it.external_id,
            "url": it.url,
            "title": it.title or "",
            "body": it.body or "",
            "created_at": it.created_at,
            "author_id": it.author_id,
            "lang": it.lang,
            "engagement": json.dumps(it.engagement or {}),
            "link": it.link,
            "discovery_ref": it.discovery_ref,
            "domain_hints": sorted(it.domain_hints),
            "query_keys": sorted(it.query_keys),
            "first_run_id": run_id,
        }
        cur = conn.execute(
            f"INSERT INTO iai_item ({', '.join(_COLUMNS)}, verdict, drop_stage, drop_reason, "
            "pipeline_version) "
            f"VALUES ({', '.join(f'%({c})s' for c in _COLUMNS)}, 'dropped', 'pending', "
            "'not_labelled', '') "
            "ON CONFLICT (id) DO UPDATE SET "
            "  last_seen_at = now(), engagement = EXCLUDED.engagement, "
            "  domain_hints = ARRAY(SELECT DISTINCT unnest(iai_item.domain_hints || "
            "EXCLUDED.domain_hints) ORDER BY 1), "
            "  query_keys = ARRAY(SELECT DISTINCT unnest(iai_item.query_keys || "
            "EXCLUDED.query_keys) ORDER BY 1) "
            "RETURNING (xmax = 0)",
            row,
        )
        new += bool(cur.fetchone()[0])
    return new


def load_items(conn) -> list[Item]:
    """Every stored item, for labelling over the whole collection."""
    out = []
    for r in conn.execute(
        "SELECT id, platform, external_id, url, title, body, created_at, author_id, lang, "
        "engagement, link, discovery_ref, domain_hints, query_keys FROM iai_item"
    ).fetchall():
        out.append(
            Item(
                id=r[0],
                platform=r[1],
                external_id=r[2],
                url=r[3],
                title=r[4],
                body=r[5],
                created_at=r[6],
                author_id=r[7],
                lang=r[8],
                engagement=r[9] or {},
                link=r[10],
                discovery_ref=r[11],
                domain_hints=set(r[12] or []),
                query_keys=set(r[13] or []),
            )
        )
    return out


def write_labels(conn, results: dict[str, Result], *, pipeline_version: str) -> int:
    """The rules' current answer for every item. Returns rows written."""
    now = datetime.now(UTC)
    n = 0
    for item_id, r in results.items():
        conn.execute(
            "UPDATE iai_item SET verdict = %s, drop_stage = %s, drop_reason = %s, flags = %s, "
            "domains = %s, groups = %s, matched_terms = %s, ai_terms = %s, "
            "content_type = %s, matched_pattern = %s, stage_guess = %s, "
            "canonical_of = %s, share_count = %s, canonical_url = %s, pipeline_version = %s, "
            "labelled_at = %s WHERE id = %s",
            (
                r.verdict,
                r.stage,
                r.reason,
                r.flags,
                r.domains,
                r.groups,
                json.dumps(r.matched_terms),
                r.ai_terms,
                r.content_type,
                r.matched_pattern,
                r.stage_guess,
                r.canonical_of,
                r.share_count,
                r.canonical_url,
                pipeline_version,
                now,
                item_id,
            ),
        )
        n += 1
    return n
