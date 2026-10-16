#!/usr/bin/env python
"""Harvest the blog's topic feed: newest AI papers and reviewed blog feeds.

THE BLOG'S OWN HARVEST (2026-10-16). The evidence harvest reads what engineers
say about MODELS; this one reads what the field is writing about AI in general,
so the blog can answer "what is RAG?" or "what is a System 1 model?" too.

    python scripts/harvest_topics.py              # harvest and store
    python scripts/harvest_topics.py --dry-run    # fetch and count, store nothing
    python scripts/harvest_topics.py --rematch    # re-label stored items only

Sources, both through the gated entry points the evidence harvest uses, so the
terms rulings, robots.txt and rate limits apply exactly as there:

    arXiv   collect.adapters.arxiv.harvester_for_source, the query and page count
            in blog_topics.yaml
    feeds   collect.adapters.blog.fetch.fetcher_for_source, every feed
            contract/sources.yaml reviews; feed metadata only, no article fetch

What is stored is what the publisher syndicates: a title, the abstract or the
feed summary as plain text, the authors, the date and the link. Every item is
re-matched against blog_topics.yaml's topics on every run. No model is called.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collect.adapters import arxiv  # noqa: E402
from collect.adapters.blog.fetch import NotAFetchTargetError, fetcher_for_source  # noqa: E402
from collect.adapters.blog.robots import RobotsGate  # noqa: E402
from collect.config import settings  # noqa: E402
from collect.http import build_client  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.registry.sources import load_sources  # noqa: E402

SUMMARY_MAX = 2000
_TAG = re.compile(r"<[^>]+>")


def plain(text: str | None) -> str | None:
    if not text:
        return None
    t = html.unescape(_TAG.sub(" ", text))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:SUMMARY_MAX] or None


def _when(value) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def harvest_arxiv(contract, client, store, cfg) -> tuple[list[dict], str]:
    source = next((p for p in contract.platforms if p.get("id") == "arxiv"), None)
    if source is None:
        return [], "no `arxiv` source row in contract/sources.yaml"
    try:
        harvester = arxiv.harvester_for_source(
            source,
            rulings=contract.rulings,
            client=client,
            store=store,
            max_pages=int(cfg["max_pages"]),
        )
    except Exception as e:  # noqa: BLE001 - a refusal is reported, not raised
        return [], f"refused: {type(e).__name__}: {e}"
    run = harvester.search(cfg["query"])
    items = [
        {
            "id": f"arxiv:{p.external_id}",
            "source": "arxiv",
            "kind": "paper",
            "title": plain(p.title) or p.external_id,
            "summary": plain(p.summary),
            "url": p.abs_url,
            "authors": list(p.authors),
            "published_at": _when(p.published),
        }
        for p in run.papers
    ]
    note = f"{len(items)} papers"
    if run.truncated_by:
        note += f" (truncated: {run.truncated_by})"
    return items, note


def harvest_feeds(contract, client, store) -> tuple[list[dict], list[str]]:
    items, notes = [], []
    robots = RobotsGate(client, user_agent=settings().user_agent)
    for feed in contract.feeds:
        fid = feed["id"]
        try:
            fetcher = fetcher_for_source(
                feed, robots=robots, rulings=contract.rulings, client=client, store=store
            )
        except NotAFetchTargetError:
            continue
        except Exception as e:  # noqa: BLE001 - one refused feed must not stop the rest
            notes.append(f"{fid}: refused ({type(e).__name__})")
            continue
        got = fetcher.fetch_feed(feed["endpoint"])
        for e in got.entries:
            if not e.url or not e.title:
                continue
            items.append(
                {
                    "id": f"{fid}|{e.entry_id}",
                    "source": fid,
                    "kind": "post",
                    "title": plain(e.title),
                    "summary": plain(e.summary_html or e.content_html),
                    "url": e.url,
                    "authors": [e.author] if e.author else [],
                    "published_at": e.published_at,
                }
            )
        notes.append(f"{fid}: {got.outcome} {len(got.entries)} entries")
    return items, notes


def store_items(conn, items: list[dict]) -> int:
    from judge.topics import match

    new = 0
    for it in items:
        cur = conn.execute(
            "INSERT INTO topic_item "
            "(id, source, kind, title, summary, url, authors, published_at, topics) "
            "VALUES (%(id)s, %(source)s, %(kind)s, %(title)s, %(summary)s, %(url)s, %(authors)s, "
            "        %(published_at)s, %(topics)s) "
            "ON CONFLICT (id) DO NOTHING",
            {**it, "topics": match(it["title"], it.get("summary"))},
        )
        new += cur.rowcount
    return new


def rematch(conn) -> int:
    """Re-label every stored item with today's topics. Returns rows changed."""
    from judge.topics import match

    changed = 0
    for iid, title, summary, topics in conn.execute(
        "SELECT id, title, summary, topics FROM topic_item"
    ).fetchall():
        now = match(title, summary)
        if sorted(now) != sorted(topics or []):
            conn.execute("UPDATE topic_item SET topics = %s WHERE id = %s", (now, iid))
            changed += 1
    return changed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="fetch and count; store nothing")
    ap.add_argument("--rematch", action="store_true", help="only re-label stored items")
    args = ap.parse_args(argv)

    import psycopg

    from judge.topics import config
    from judge.writeguard import check as writeguard_check

    dsn = settings().database_url
    if not args.dry_run:
        writeguard_check(dsn, command="harvest_topics.py")
    if args.rematch:
        with psycopg.connect(dsn) as conn:
            n = rematch(conn)
            conn.commit()
        print(f"re-labelled {n} item(s)")
        return 0

    contract = load_sources()
    store = RawStore(Path(settings().raw_store_path))
    with build_client() as client:
        papers, arxiv_note = harvest_arxiv(contract, client, store, config()["arxiv"])
        posts, feed_notes = harvest_feeds(contract, client, store)
    print(f"arxiv: {arxiv_note}")
    for n in feed_notes:
        print(f"  {n}")
    print(f"fetched {len(papers)} paper(s) and {len(posts)} post(s)")
    if args.dry_run:
        return 0
    with psycopg.connect(dsn) as conn:
        new = store_items(conn, papers + posts)
        changed = rematch(conn)
        conn.commit()
    print(f"stored {new} new item(s); re-labelled {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
