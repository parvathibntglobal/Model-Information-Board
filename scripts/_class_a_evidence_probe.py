"""`terms_evidence` + `measured` + `template_block` for a class A candidate.

WHAT THIS IS FOR

`contract/sources.yaml` needs three blocks per feed before a row can be written,
and two of the three cannot be filled without fetching:

    terms_evidence   feed_type, article_http, paywall_observed, login_required
    measured         entries .. resolves_to_voices, all from the feed
    template_block   status, pages_examined, headings - and this one needs
                     MANY articles, not one, because a template block is what
                     REPEATS across them

All nine seated feeds carry `article_http: 200` from 2026-08-14, so a sample
fetch before the ruling is the established practice. This does the same thing,
politely and once, and writes down what it saw.

THE TEMPLATE BLOCK IS NOT THE SAME FETCH AS THE SAMPLE, and that is the point
worth reading. One article answers `article_http`, `paywall_observed` and
`login_required`. It cannot answer "what boilerplate does this host append to
every post", because one page has no repetition to detect. `hamel.dev` is
recorded at 12 pages examined and `simonwillison.net` at 62. So this fetches
`--pages` articles per host and reports lines appearing in at least
`--threshold` of them.

POLITENESS. One request per second or slower, the project User-Agent on every
request, robots re-read per host before anything else. Refuses to run against a
host whose robots disallows the article path.

    python scripts/_class_a_evidence_probe.py --host eugeneyan.com \
        --feed https://eugeneyan.com/rss/ --pages 10
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys
import time
import urllib.parse

import feedparser
import httpx
import trafilatura
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from urllib.robotparser import RobotFileParser  # noqa: E402

from collect.adapters.blog.rules import allowance_for  # noqa: E402


def _ua() -> str:
    ua = os.getenv("USER_AGENT", "")
    if not ua:
        raise SystemExit(
            "USER_AGENT is unset. NFR-5 requires an identifying User-Agent with a "
            "contact URL on every request; there is no default, deliberately."
        )
    return ua


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--feed", required=True)
    parser.add_argument("--pages", type=int, default=10)
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--out", default="_class_a_evidence")
    parser.add_argument("--delay", type=float, default=1.1)
    args = parser.parse_args()

    ua = _ua()
    out = ROOT / args.out / args.host
    out.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": ua}
    report: dict[str, object] = {"host": args.host, "feed": args.feed}

    with httpx.Client(timeout=45, headers=headers, follow_redirects=True) as client:
        # ── robots first, every time ────────────────────────────────────────
        robots_url = f"https://{args.host}/robots.txt"
        robots_response = client.get(robots_url)
        report["robots_http"] = robots_response.status_code
        # THE PROJECT'S OWN RFC 9309 MATCHER, not a reimplementation.
        # `urllib.robotparser` gets wildcards and most-specific-match wrong, and
        # `rules.py` exists to replace exactly that decision.
        parser_rp = RobotFileParser()
        parser_rp.parse(
            (robots_response.text if robots_response.status_code == 200 else "").splitlines()
        )
        report["robots_status"] = "rules" if robots_response.status_code == 200 else "no-rules"
        report["feed_path_allowed"] = allowance_for(parser_rp, ua, args.feed).allowed
        if not report["feed_path_allowed"]:
            raise SystemExit(f"robots disallows the feed path on {args.host}. Nothing fetched.")
        time.sleep(args.delay)

        # ── the feed ────────────────────────────────────────────────────────
        feed_response = client.get(args.feed)
        (out / "feed.xml").write_bytes(feed_response.content)
        parsed = feedparser.parse(feed_response.content)
        report["feed_http"] = feed_response.status_code
        report["feed_type"] = parsed.version or "unknown"
        report["malformed"] = bool(parsed.bozo)
        entries = parsed.entries
        report["entries"] = len(entries)
        report["declared_author"] = (parsed.feed.get("author") or None)
        bylines = [e.get("author") for e in entries if e.get("author")]
        report["entry_bylines_present"] = len(bylines)
        report["distinct_entry_bylines"] = len(set(bylines))

        # ⚠ SAME-HOST GUARD, ADDED AFTER IT BIT. sebastianraschka.com's feed
        #   carries entries whose links are on magazine.sebastianraschka.com,
        #   which is Substack. robots permits /p/*; the Substack TERMS do not,
        #   and this probe followed three of them before the guard existed.
        #
        #   A ruling is made about a HOST. An entry link on another host is
        #   outside the ruling that authorised the feed, whatever that host's
        #   robots says - robots is a crawl policy and the ruling is the
        #   permission. Recorded per entry rather than dropped, because
        #   "this feed syndicates elsewhere" is a fact about the feed.
        feed_host = urllib.parse.urlparse(args.feed).hostname or ""
        all_links = [e.get("link") for e in entries if e.get("link")]
        offhost = [
            u for u in all_links
            if (urllib.parse.urlparse(u).hostname or "") != feed_host
        ]
        report["offhost_entry_links"] = offhost
        report["offhost_hosts"] = sorted(
            {urllib.parse.urlparse(u).hostname or "" for u in offhost}
        )
        links = [u for u in all_links if u not in offhost][: args.pages]
        report["articles_requested"] = len(links)
        if offhost:
            print(f"  WARNING: {len(offhost)} entry link(s) on another host, NOT fetched: "
                  f"{', '.join(report['offhost_hosts'])}")

        # ── the articles ────────────────────────────────────────────────────
        texts: dict[str, str] = {}
        statuses: list[int] = []
        refused: list[str] = []
        for i, link in enumerate(links, 1):
            if not allowance_for(parser_rp, ua, link).allowed:
                # NAMED, not skipped silently: a path robots refuses is a fact
                # about the host, not a gap in the sample.
                refused.append(link)
                print(f"  {i:2d}. ROBOTS REFUSES {link}")
                continue
            time.sleep(args.delay)
            try:
                article = client.get(link)
            except Exception as exc:                          # noqa: BLE001
                print(f"  {i:2d}. FAILED {link} ({type(exc).__name__})")
                continue
            statuses.append(article.status_code)
            text = trafilatura.extract(article.text) or ""
            texts[link] = text
            (out / f"a{i:02d}.html").write_text(article.text, encoding="utf-8")
            print(f"  {i:2d}. {article.status_code}  {len(text):6d} chars  {link}")

    report["robots_refused_article_paths"] = refused
    report["article_http"] = sorted(set(statuses))
    report["articles_fetched"] = len(texts)
    body_lengths = sorted(len(t) for t in texts.values())
    report["median_body_chars"] = (
        body_lengths[len(body_lengths) // 2] if body_lengths else None
    )
    # PAYWALL IS REPORTED AS EVIDENCE, NEVER AS A VERDICT - rule 8, learned on
    # this probe's first run. "shortest body < 500 chars" fired on
    # eugeneyan.com and the page was an HTML meta-refresh REDIRECT STUB, not a
    # paywall. An unmeasured check ships as a flag, so this lists the short
    # bodies by URL and leaves the determination to a person.
    report["paywall_observed"] = "unknown - see short_bodies"
    report["short_bodies"] = sorted(
        ({"url": u, "chars": len(x)} for u, x in texts.items() if len(x) < 500),
        key=lambda r: r["chars"],
    )

    # ── the template block ──────────────────────────────────────────────────
    counts: collections.Counter[str] = collections.Counter()
    for text in texts.values():
        for line in {ln.strip() for ln in text.splitlines() if len(ln.strip()) > 15}:
            counts[line] += 1
    n = len(texts)
    repeated = [
        (line, c) for line, c in counts.most_common() if n and c / n >= args.threshold
    ]
    report["pages_examined"] = n
    report["template_threshold"] = args.threshold
    report["repeated_lines"] = [{"line": ln, "in_pages": c} for ln, c in repeated]
    report["template_block_status"] = "clean" if not repeated else "block-found"

    print(f"\n  {n} pages examined, {len(repeated)} line(s) in >= {args.threshold:.0%}")
    for line, c in repeated[:20]:
        print(f"    {c}/{n}  {line[:100]}")

    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"  -> {out}/report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
