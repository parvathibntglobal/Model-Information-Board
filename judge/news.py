"""Admin -> News: the fresh headlines collect/news/harvest.py stored (2026-10-28).

Read-only. Every source in contract/news_sources.yaml is listed with what its
last read did - ok, refused by robots.txt, or failed - so a quiet source and a
broken one never look the same (rule 4). Items come newest first by the
source's own date; an item without one is placed by when we first saw it, and
says so (rule 6).

AN UNDATED ITEM NEVER SORTS AS FRESH. Ordering by "first seen" would put every
undated item at the top on the day a source is first read - Google
Developers' 20 posts, which carry no date at all, led the list on 2026-10-28
and may be months old. So dated items come first, newest first, and undated
ones follow, each saying when we first saw it (rule 12: a stand-in date that
looks right is the wrong kind of fallback).

NOTHING IS FILTERED HERE. The LLM badge (`llm_keywords`) travels on every item
and the page lets a reader filter on it; the server never does, because nobody
has measured what the keyword list misses (rule 8).

The judge does not import collect/, so the contract is read here directly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

CONTRACT = Path(__file__).resolve().parents[1] / "contract" / "news_sources.yaml"


class NewsRequestError(ValueError):
    """A request the page should not have sent (a window outside the contract's)."""


def _contract() -> dict[str, Any]:
    raw = yaml.safe_load(CONTRACT.read_text(encoding="utf-8")) or {}
    page = raw.get("page") or {}
    for key in ("default_days", "max_days", "max_items"):
        if not isinstance(page.get(key), int) or page[key] <= 0:
            raise ValueError(f"contract/news_sources.yaml: page.{key} must be a positive integer")
    return raw


ITEMS_SQL = """
SELECT id, source_key, title, url, published_at, first_seen_at, summary, author,
       categories, llm_keywords, daily_count
FROM news_item
WHERE coalesce(published_at, first_seen_at) >= %s
ORDER BY (published_at IS NULL), coalesce(published_at, first_seen_at) DESC, id
LIMIT %s
"""

# Each source's newest read, whatever it did.
LAST_READ_SQL = """
SELECT DISTINCT ON (source_key) source_key, fetched_at, outcome, http_status, detail,
       items_seen, items_new
FROM news_fetch
ORDER BY source_key, fetched_at DESC
"""

COUNTS_SQL = """
SELECT source_key,
       count(*),
       count(*) FILTER (WHERE coalesce(published_at, first_seen_at) >= %s),
       count(*) FILTER (WHERE coalesce(published_at, first_seen_at) >= %s AND published_at IS NULL)
FROM news_item GROUP BY source_key
"""


def news_view(conn, *, days: int | None = None, now: datetime | None = None) -> dict[str, Any]:
    contract = _contract()
    page = contract["page"]
    days = page["default_days"] if days is None else days
    if not 1 <= days <= page["max_days"]:
        raise NewsRequestError(f"days must be between 1 and {page['max_days']}")
    now = now or datetime.now(UTC)
    since = now - timedelta(days=days)

    rows = conn.execute(ITEMS_SQL, (since, page["max_items"] + 1)).fetchall()
    capped = len(rows) > page["max_items"]
    items = [
        {
            "id": r[0], "source_key": r[1], "title": r[2], "url": r[3],
            "published_at": r[4].isoformat() if r[4] else None,
            "first_seen_at": r[5].isoformat(),
            "summary": r[6], "author": r[7], "categories": list(r[8] or []),
            "llm_keywords": list(r[9] or []), "daily_count": r[10],
        }
        for r in rows[: page["max_items"]]
    ]

    last = {r[0]: r for r in conn.execute(LAST_READ_SQL).fetchall()}
    counts = {r[0]: r[1:] for r in conn.execute(COUNTS_SQL, (since, since)).fetchall()}
    sources = []
    for s in contract.get("sources") or []:
        read = last.get(s["key"])
        total, in_window, undated = counts.get(s["key"], (0, 0, 0))
        sources.append({
            "key": s["key"], "label": s["label"], "group": s["group"], "terms": s.get("terms"),
            "one_entry_a_day": bool(s.get("daily")),
            # None: never read on this database - not the same as read and empty.
            "last_read": None if read is None else {
                "at": read[1].isoformat(), "outcome": read[2], "http_status": read[3],
                "detail": read[4], "items_seen": read[5], "items_new": read[6],
            },
            "items_total": total, "items_in_window": in_window, "undated_in_window": undated,
        })
    in_window = sum(s["items_in_window"] for s in sources)
    return {
        "days": days,
        "max_days": page["max_days"],
        "generated_at": now.isoformat(),
        "items": items,
        "sources": sources,
        # Rule 7: what every count on the page is counted over.
        "population": {
            "items_in_window": in_window,
            "items_shown": len(items),
            "capped_at": page["max_items"] if capped else None,
            "items_stored": sum(s["items_total"] for s in sources),
            "sources_listed": len(sources),
        },
    }
