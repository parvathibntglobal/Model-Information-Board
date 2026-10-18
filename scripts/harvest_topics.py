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

    arXiv   collect.adapters.arxiv.harvester_for_source, one query per category
            in blog_topics.yaml
    feeds   collect.adapters.blog.fetch.fetcher_for_source, every feed
            contract/sources.yaml reviews; feed metadata only, no article fetch
    Hacker News, dev.to, Hugging Face daily papers (2026-10-18): each topic's
            own `terms` as queries (Hugging Face: the day's featured papers),
            through the same gated harvester_for_source the model fetch uses
            (blog_topics.yaml `platforms`). Stories, articles
            and papers inside the window; title, summary, author, date, link.

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

from collect.adapters import arxiv, devto, hackernews, huggingface  # noqa: E402
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
            max_pages=int(cfg["pages_per_category"]),
        )
    except Exception as e:  # noqa: BLE001 - a refusal is reported, not raised
        return [], f"refused: {type(e).__name__}: {e}"
    papers, notes = {}, []
    # ONE QUERY PER CATEGORY: a paper cross-listed in two is kept once.
    for cat in cfg["categories"]:
        run = harvester.search(f"cat:{cat}")
        for p in run.papers:
            papers.setdefault(p.external_id, p)
        cut = f" (truncated: {run.truncated_by})" if run.truncated_by else ""
        notes.append(f"{cat} {len(run.papers)}{cut}")
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
        for p in papers.values()
    ]
    return items, f"{len(items)} distinct papers ({'; '.join(notes)})"


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


def _queries(topic: dict, n: int) -> list[str]:
    """A topic's first `n` terms, the list order being the priority."""
    return [str(t) for t in topic["terms"]][:n]


def _platform_cfg() -> dict:
    from judge.topics import config

    cfg = config().get("platforms")
    need = ("queries_per_topic", "window_days", "hackernews", "devto", "huggingface_papers")
    if not cfg or any(k not in cfg for k in need):
        raise SystemExit(f"blog_topics.yaml `platforms` needs {need}; "
                         "refusing rather than guessing")
    return cfg


def harvest_platforms(contract, client, store, topics: list[dict]) -> tuple[list[dict], list[str]]:
    """Hacker News stories, dev.to articles and Hugging Face papers, by topic.

    Each platform is built through its own `harvester_for_source`, so the terms
    gate refuses exactly as it does for the model fetch; a refusal is reported
    and the other platforms still run. Every item is matched against ALL topics
    when stored (store_items), so the query only decides what is fetched.
    """
    from datetime import UTC, timedelta

    cfg = _platform_cfg()
    since = datetime.now(UTC) - timedelta(days=int(cfg["window_days"]))
    nq = int(cfg["queries_per_topic"])
    rows = {p.get("id"): p for p in contract.platforms}
    items: dict[str, dict] = {}
    notes: list[str] = []

    def gated(name, module, **kw):
        if name not in rows:
            notes.append(f"{name}: no `{name}` source row in contract/sources.yaml")
            return None
        try:
            return module.harvester_for_source(rows[name], rulings=contract.rulings,
                                               client=client, store=store, **kw)
        except Exception as e:  # noqa: BLE001 - a refusal is reported, not raised
            notes.append(f"{name}: refused: {type(e).__name__}: {e}")
            return None

    def count(prefix):
        return sum(1 for k in items if k.startswith(prefix))

    hn = gated("hackernews", hackernews)
    if hn:
        per = int(cfg["hackernews"]["per_query"])
        floor = int(cfg["hackernews"].get("min_points", 0))
        hits = 0
        for t in topics:
            for q in _queries(t, nq):
                for h in hn.search_stories(q, since_ts=int(since.timestamp()), per_page=per):
                    hits += 1
                    if (h.get("points") or 0) < floor or not h.get("title"):
                        continue
                    iid = f"hackernews:{h['objectID']}"
                    link = h.get("url")
                    parts = [plain(h.get("story_text")) or "",
                             f"Links to {link}." if link else "",
                             f"{h.get('points') or 0} points, "
                             f"{h.get('num_comments') or 0} comments on Hacker News."]
                    items.setdefault(iid, {
                        "id": iid, "source": "hackernews", "kind": "post",
                        "title": plain(h["title"]),
                        "summary": plain(" ".join(x for x in parts if x)),
                        "url": f"https://news.ycombinator.com/item?id={h['objectID']}",
                        "authors": [h["author"]] if h.get("author") else [],
                        "published_at": _when(h.get("created_at")),
                    })
        notes.append(f"hackernews: {count('hackernews:')} stories kept of {hits} hits")

    dv = gated("devto", devto, max_pages=1, per_page=int(cfg["devto"]["per_query"]))
    if dv:
        hits = 0
        for t in topics:
            for q in _queries(t, nq):
                # dev.to's search answers HTTP 500 to a hyphenated query
                # ("multi-agent system", 2026-10-18); a space finds the same posts.
                for hit in dv.search(q.replace("-", " ")).hits:
                    hits += 1
                    when = _when(hit.published_at)
                    if not hit.url or not hit.title or (when and when < since):
                        continue
                    iid = f"devto:{hit.article_id}"
                    items.setdefault(iid, {
                        "id": iid, "source": "devto", "kind": "post",
                        "title": plain(hit.title), "summary": plain(hit.description),
                        "url": hit.url,
                        "authors": [hit.author_handle] if hit.author_handle else [],
                        "published_at": when,
                    })
        notes.append(f"devto: {count('devto:')} articles kept of {hits} hits")

    hf = gated("huggingface", huggingface)
    if hf:
        hits, days = 0, int(cfg["window_days"])
        for back in range(days):
            day = (datetime.now(UTC) - timedelta(days=back)).date().isoformat()
            for x in hf.daily_papers(day):
                hits += 1
                paper = x["paper"]
                pid = str(paper.get("id") or "")
                if not pid or not paper.get("title"):
                    continue
                # THE SAME PAPER ONCE: Hugging Face lists arXiv papers, so a
                # paper the arXiv arm already stored is skipped in store_items.
                iid = f"hfpapers:{pid}"
                authors = [a.get("name") for a in (paper.get("authors") or [])
                           if isinstance(a, dict) and a.get("name")]
                parts = [paper.get("summary") or "",
                         f"{paper.get('upvotes') or 0} upvotes on Hugging Face Papers."]
                items.setdefault(iid, {
                    "id": iid, "source": "huggingface", "kind": "paper",
                    "title": plain(paper["title"]),
                    "summary": plain(" ".join(x for x in parts if x)),
                    "url": f"https://huggingface.co/papers/{pid}", "authors": authors,
                    "published_at": _when(paper.get("publishedAt") or x.get("publishedAt")),
                })
        notes.append(f"huggingface daily papers: {count('hfpapers:')} papers over {days} days "
                     f"({hits} listed)")
    return list(items.values()), notes


def store_items(conn, items: list[dict]) -> int:
    from judge.topics import match

    new = 0
    for it in items:
        # ONE PAPER, ONE ROW. Hugging Face lists arXiv papers by bare id
        # ("2610.22080"); the arXiv arm stores the versioned id
        # ("arxiv:2610.22080v1"). Compared on the bare id, or the check never
        # matches - it did not, 2026-10-18, and 25 papers were stored twice.
        # arXiv is the paper's own source, so it wins whichever arrives first.
        if it["id"].startswith("hfpapers:"):
            bare = it["id"].split(":", 1)[1]
            if conn.execute("SELECT 1 FROM topic_item WHERE id = %s OR id LIKE %s",
                            (f"arxiv:{bare}", f"arxiv:{bare}v%")).fetchone():
                continue
        elif it["id"].startswith("arxiv:"):
            bare = re.sub(r"v\d+$", "", it["id"].split(":", 1)[1])
            conn.execute("DELETE FROM topic_item WHERE id = %s", (f"hfpapers:{bare}",))
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
    ap.add_argument("--only", choices=("arxiv", "feeds", "platforms"), action="append",
                    help="run only these arms (repeatable); default all")
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
    arms = set(args.only or ("arxiv", "feeds", "platforms"))
    papers, posts, found = [], [], []
    arxiv_note, feed_notes, plat_notes = "not run", [], []
    with build_client() as client:
        if "arxiv" in arms:
            papers, arxiv_note = harvest_arxiv(contract, client, store, config()["arxiv"])
        if "feeds" in arms:
            posts, feed_notes = harvest_feeds(contract, client, store)
        if "platforms" in arms:
            found, plat_notes = harvest_platforms(contract, client, store, config()["topics"])
    print(f"arxiv: {arxiv_note}")
    for n in feed_notes + plat_notes:
        print(f"  {n}")
    print(f"fetched {len(papers)} paper(s), {len(posts)} feed post(s), "
          f"{len(found)} platform item(s)")
    if args.dry_run:
        return 0
    with psycopg.connect(dsn) as conn:
        new = store_items(conn, papers + posts + found)
        changed = rematch(conn)
        conn.commit()
    print(f"stored {new} new item(s); re-labelled {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
