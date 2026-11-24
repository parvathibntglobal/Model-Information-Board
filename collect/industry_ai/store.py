"""The lane's only writer: `iai_item` and `iai_run`, and nothing else.

APPEND, THEN LABEL. A harvested item is inserted once; when a later run finds it
again only `last_seen_at`, its domain hints, query keys and engagement change.
The LABEL columns are rewritten by every run and every `--relabel`, because they
are the current rules' answer about a stored item, not evidence. No row is ever
deleted - a dropped item stays, with its stage and reason.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

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


#: The upsert, one row's worth. Sent for every item in ONE batched `executemany`.
_UPSERT = (
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
    "RETURNING (xmax = 0)"
)


def upsert_items(conn, items: list[Item], *, run_id: str) -> int:
    """Insert new items; for known ones, widen hints and keys and refresh the
    seen time and engagement. Returns how many were new.

    ONE BATCHED `executemany`, NOT A STATEMENT PER ITEM (2026-11-24). The first real
    run, from a GitHub runner to the shared database, stored and labelled one round
    trip per item for over 30 minutes and ran up against the job's 45-minute limit.
    psycopg sends an `executemany` in pipeline mode: the statements go out together
    and the answers come back together, so the time no longer grows with the round
    trip."""
    rows = []
    for it in items:
        rows.append({
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
        })
    if not rows:
        return 0
    new = 0
    with conn.cursor() as cur:
        cur.executemany(_UPSERT, rows, returning=True)
        while True:  # one result per row: true where the row was inserted, not updated
            got = cur.fetchone()
            new += bool(got and got[0])
            if not cur.nextset():
                break
    return new


def load_items(conn) -> list[Item]:
    """Every stored item whose text is still held, for labelling over the whole
    collection.

    A row whose text RETENTION cleared (`text_cleared_at`) is left out: its empty
    text would be re-judged ("no AI term") and the drop counts would shift, so it
    keeps the labels it had. Its counts stay on the page, which reads `iai_item`."""
    out = []
    for r in conn.execute(
        "SELECT id, platform, external_id, url, title, body, created_at, author_id, lang, "
        "engagement, link, discovery_ref, domain_hints, query_keys, first_seen_at FROM iai_item "
        "WHERE text_cleared_at IS NULL"
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
                # The watch window is measured from first sight (pipeline.evaluate).
                first_seen_at=r[14],
            )
        )
    return out


def clear_text(conn, retention: dict, *, now: datetime | None = None) -> int:
    """Empty the title and body of every row `retention` says is due; return how many.

    Due: first stored more than `clear_text_after_days` ago, text not cleared yet,
    and either dropped (when `retention.dropped`) or kept under one of
    `retention.kept_domains`. The ROW stays - id, platform, dates, verdict, reason,
    labels, flags - because the page's counts are counted from it. Run after
    labelling, so a row is cleared with the labels its text earned.
    """
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=int(retention["clear_text_after_days"]))
    # WHICH ROWS, THEN THE WRITE: a SELECT that READS first_seen_at, verdict and
    # domains, and an UPDATE that writes only what it writes. One UPDATE with
    # that WHERE read to scripts/audit_columns.py as a WRITE of first_seen_at,
    # which the database sets and no code does (contract/column_states.yaml).
    due = [r[0] for r in conn.execute(
        "SELECT id FROM iai_item "
        "WHERE text_cleared_at IS NULL AND first_seen_at < %(cutoff)s "
        "AND ((%(dropped)s AND verdict = 'dropped') "
        "     OR (verdict = 'kept' AND domains && %(kept)s::text[]))",
        {"cutoff": cutoff, "dropped": bool(retention["dropped"]),
         "kept": list(retention["kept_domains"])},
    ).fetchall()]
    if due:
        conn.execute(
            "UPDATE iai_item SET title = '', body = '', text_cleared_at = %s "
            "WHERE id = ANY(%s)", (now, due))
    return len(due)


def write_labels(conn, results: dict[str, Result], *, pipeline_version: str) -> int:
    """The rules' current answer for every item. Returns rows written.

    One batched `executemany`, like `upsert_items` (2026-11-24): every run re-labels
    the whole collection, so a round trip per item grows with everything ever stored."""
    now = datetime.now(UTC)
    params = [
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
        )
        for item_id, r in results.items()
    ]
    if params:
        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE iai_item SET verdict = %s, drop_stage = %s, drop_reason = %s, "
                "flags = %s, domains = %s, groups = %s, matched_terms = %s, ai_terms = %s, "
                "content_type = %s, matched_pattern = %s, stage_guess = %s, "
                "canonical_of = %s, share_count = %s, canonical_url = %s, "
                "pipeline_version = %s, labelled_at = %s WHERE id = %s",
                params,
            )
    return len(params)
