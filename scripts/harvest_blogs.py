"""A measured blog harvest across every seeded feed. The instrument, not the pipeline.

Companion to `harvest_github.py`, and the more important of the two: blogs are
the only positive-evidence channel, and the first two-feed run produced 40
documents against GitHub's 1 from a full sweep.

Every feed goes through `fetcher_for_source`, so the NFR-5 gate runs per feed
with this run's own robots observations, and a class B ruling refuses article
fetches in code rather than by convention.

WHAT IT REPORTS, AND WHY EACH ONE
---------------------------------
    per feed        fetched, kept, errors, articles stored, and the feed-only
                    distinction — `items_kept` counts feed bodies where the
                    ruling permits no article fetch, because counting stored
                    articles there reported zero yield on a feed delivering
                    ten full posts
    sieve           each group counted INDEPENDENTLY over all documents. The
                    GitHub run's "77% topic" was topic measured only among
                    subject-matching documents, which is bounded by the
                    subject rate and measures nothing
    distinct        documents, not passes. One post found by two entries is
                    one voice
    bylines         resolved against the seeded measurement, because
                    `resolves_to_voices` is what corroboration counts

Writes to `modelboard_harvest_test`, not `TEST_DATABASE_URL` — see
`harvest_github.py` on why a runner that drops a schema uses its own database.

    python scripts/harvest_blogs.py --out blogs.json
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from collect.adapters.blog.fetch import fetcher_for_source
from collect.adapters.blog.parse import extract_article_text, parse_feed
from collect.adapters.blog.robots import RobotsGate
from collect.adapters.queries import load_queries
from collect.adapters.queries.sieve import sieve_any
from collect.db import apply_schema, connect
from collect.http import build_client
from collect.limiter import HostLimiter
from collect.rawstore import RawStore
from collect.registry.aliases import alias_rows
from collect.registry.seed import seed_models
from collect.registry.sources import load_source_rows, load_sources

DEFAULT_DSN = "postgresql://postgres@localhost:5433/modelboard_harvest_test"


def checked_dsn(dsn: str) -> str:
    from tests.conftest import assert_disposable, assert_safe_target

    assert_safe_target(dsn)
    with connect(dsn) as probe:
        assert_disposable(probe, dsn)
    return dsn


def searchable_aliases() -> dict[str, list[str]]:
    """canonical_id -> the alias spellings, for sieving document text.

    Every spelling, not the one a query used: blogs have no retrieval step, so
    a document is sieved against the whole registry rather than against the
    query that found it.
    """
    return {
        model.canonical_id: sorted(
            {v for row in alias_rows(model) for v in row.variants}
        )
        for model in seed_models()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--store", default="./_blog_harvest_store")
    parser.add_argument("--out", default="blog-run-report.json")
    parser.add_argument("--feed", action="append", dest="feeds")
    args = parser.parse_args(argv)

    contract = load_sources()
    feeds = [f for f in contract.feeds if not args.feeds or f["id"] in args.feeds]

    conn = connect(checked_dsn(args.dsn))
    conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    apply_schema(conn)
    report_rows = load_source_rows(conn)
    conn.commit()
    print(report_rows.summary())
    print()

    client = build_client(timeout=30.0)
    gate = RobotsGate(client, user_agent=client.headers["User-Agent"])
    store = RawStore(Path(args.store))
    limiter = HostLimiter()

    queries = load_queries()
    entries = list(queries.capability_queries)
    aliases = searchable_aliases()

    started = time.monotonic()
    per_feed, documents = [], []
    for feed in feeds:
        source_id = feed["id"]
        try:
            fetcher = fetcher_for_source(
                feed, client=client, store=store, robots=gate, limiter=limiter,
                rulings=contract.rulings,
            )
        except Exception as exc:  # noqa: BLE001 - a refusal is a result
            print(f"  {source_id:<38} REFUSED  {type(exc).__name__}: {str(exc)[:80]}")
            per_feed.append({"source_id": source_id, "outcome": "refused",
                             "detail": f"{type(exc).__name__}: {exc}"})
            continue

        run = fetcher.harvest_feed(feed["endpoint"])
        fields = run.harvest_run_fields()
        feed_only = not run.fetch_articles

        # Where the text comes from depends on the ruling: a feed-only host
        # gives us the body in the feed, everything else in the article.
        texts: list[tuple[str, str, str]] = []   # (external_id, url, text)
        extraction_misses = 0
        if run.feed.artifact:
            parsed = parse_feed(
                store.get(run.feed.artifact.ref), feed_url=feed["endpoint"]
            )
            bodies = {e.entry_id: (e.content_html or e.summary_html or "")
                      for e in parsed.entries}
            urls = {e.entry_id: e.url for e in parsed.entries}
            if feed_only:
                texts = [(eid, urls.get(eid) or "", body)
                         for eid, body in bodies.items() if body.strip()]
            else:
                for article in run.articles:
                    if not article.stored:
                        continue
                    # Bytes, not str: `extract_article_text` refuses a string
                    # because trafilatura would treat one as a URL and fetch it
                    # with its own HTTP layer, around the User-Agent gate.
                    # None means nothing was extracted — a navigation page, a
                    # paywall stub, a JS shell — and must not become an empty
                    # document. Counted as an extraction miss instead.
                    extracted = extract_article_text(
                        store.get(article.artifact.ref), url=article.url
                    )
                    if extracted is None:
                        extraction_misses += 1
                        continue
                    texts.append(
                        (article.entry.entry_id, article.url or "", extracted)
                    )

        kept = []
        for external_id, url, text in texts:
            # Every entry against every model, and each model against EVERY
            # spelling — `sieve_any` exists so a document cannot be judged on
            # the one form a query happened to use. Blogs have no retrieval
            # step, so there is no query form to privilege in the first place.
            hit = None
            furthest = None
            for entry in entries:
                for canonical_id, spellings in aliases.items():
                    verdict = sieve_any(
                        [entry.terms.substitute(s) for s in spellings], text
                    )
                    if verdict.passed:
                        hit = (entry.label, canonical_id, verdict)
                        break
                    if furthest is None or len(verdict.missing) < len(furthest.missing):
                        furthest = verdict
                if hit:
                    break

            verdict = hit[2] if hit else furthest
            documents.append({
                "source_id": source_id, "external_id": external_id, "url": url,
                "chars": len(text), "passed": bool(hit),
                "entry": hit[0] if hit else None,
                "model": hit[1] if hit else None,
                "subject": list(verdict.subject) if verdict else [],
                "topic": list(verdict.topic) if verdict else [],
                "signal": list(verdict.signal) if verdict else [],
                "signal_in_excluded": list(verdict.signal_in_excluded) if verdict else [],
            })
            if hit:
                kept.append(external_id)

        per_feed.append({
            "source_id": source_id,
            "ruling": feed["terms_ruling"],
            "feed_only": feed_only,
            "outcome": run.outcome,
            "items_fetched": fields["items_fetched"],
            "items_kept": fields["items_kept"],
            "http_errors": fields["http_errors"],
            "robots_blocked": run.robots_blocked,
            "articles_stored": sum(1 for a in run.articles if a.stored),
            "extraction_misses": extraction_misses,
            "texts_sieved": len(texts),
            "sieve_passed": len(kept),
            "byline_source": feed["measured"]["byline_source"],
            "resolves_to_voices": feed["measured"]["resolves_to_voices"],
        })
        row = per_feed[-1]
        print(
            f"  {source_id:<38} {run.outcome:<13} "
            f"fetched={row['items_fetched']:3} kept={row['items_kept']:3} "
            f"articles={row['articles_stored']:3} "
            f"sieved={row['texts_sieved']:3} passed={row['sieve_passed']:3} "
            f"err={row['http_errors']}"
        )
    wall = time.monotonic() - started

    # Each group counted INDEPENDENTLY over every document, for the reason the
    # GitHub run's "77% topic" turned out to be measuring nothing: counted only
    # among subject-matching documents it is bounded by the subject rate.
    groups: Counter[str] = Counter()
    for document in documents:
        if document["passed"]:
            groups["passed"] += 1
        for name in ("subject", "topic", "signal"):
            if document[name]:
                groups[name] += 1
        if document["signal_in_excluded"]:
            groups["signal_in_excluded"] += 1

    report = {
        "feeds": len(feeds),
        "wall_clock_seconds": round(wall, 1),
        "documents_sieved": len(documents),
        "documents_passed": groups["passed"],
        "distinct_documents": len({(d["source_id"], d["external_id"]) for d in documents}),
        "group_hits": {k: groups[k] for k in
                       ("subject", "topic", "signal", "signal_in_excluded")},
        "per_feed": per_feed,
        "documents": documents,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    Path(args.out).write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")

    print("\n=== totals ===")
    print(f"feeds            : {len(feeds)}")
    print(f"wall clock       : {report['wall_clock_seconds']}s")
    print(f"documents sieved : {report['documents_sieved']}")
    print(f"distinct         : {report['distinct_documents']}")
    print(f"passed the sieve : {report['documents_passed']}")

    total = len(documents)
    if total:
        print(f"\n=== group membership over all {total} documents, independently ===")
        for name in ("subject", "topic", "signal"):
            print(f"  {name:<8} {groups[name]:4}/{total}  {groups[name] / total:6.1%}")
        print(f"  signal only in quoted/fenced text: {groups['signal_in_excluded']}")

    passed = [d for d in documents if d["passed"]]
    if passed:
        print(f"\n=== {len(passed)} passed ===")
        for d in passed:
            print(f"  {d['source_id']:<34} {d['entry']}  [{d['model']}]")
            print(f"    {d['url'][:100]}")
            print(f"    signal={d['signal']}")

    print(f"\nwrote {args.out}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
