"""Is a terms document reachable on this host? Two places, and neither is 'the site'.

`blog-class-a-self-hosted` records `terms_document_read: false` on every feed,
and #372 established the check that makes that a FINDING rather than a shrug:
look in the two places a terms page is normally reachable from, and say which
two you looked in.

    1. the sitemap robots.txt advertises
    2. the front page's own markup

WHAT THIS CAN AND CANNOT CONCLUDE, because the gap is the whole point. Zero
matches in both places means ABSENT FROM TWO PLACES A TERMS PAGE IS NORMALLY
REACHABLE. It does not mean the site has no terms. That is as far as this goes
without a lawyer, and the row's `tos_notes` must say so in those words rather
than rounding it to "no terms" - which would be rule 6 pointed outward, an
absence read as a definite permission.

Politeness: project User-Agent, robots honoured, one request per second.

    python scripts/_terms_page_check.py --hosts swyx.io minimaxir.com
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time
import urllib.parse

import httpx
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from urllib.robotparser import RobotFileParser  # noqa: E402

from collect.adapters.blog.rules import allowance_for  # noqa: E402

#: The words a terms document is reachable under. Matched against href AND
#: link text, because a footer link often says "Legal" and points at /policies.
TERMS_WORDS = [
    "terms", "legal", "privacy", "copyright", "licence", "license",
    "tos", "disclaimer", "imprint", "policies", "policy",
]
LINK_RE = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


def hits_in(html: str, base: str) -> list[dict]:
    out = []
    for href, text in LINK_RE.findall(html):
        label = TAG_RE.sub(" ", text).strip()[:60]
        hay = (href + " " + label).lower()
        for w in TERMS_WORDS:
            if w in hay:
                out.append({"href": urllib.parse.urljoin(base, href),
                            "text": label, "matched": w})
                break
    # dedupe on resolved href, keep order
    seen, uniq = set(), []
    for h in out:
        if h["href"] not in seen:
            seen.add(h["href"])
            uniq.append(h)
    return uniq


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hosts", nargs="+", required=True)
    ap.add_argument("--delay", type=float, default=1.1)
    ap.add_argument("--out", default="_terms_page_check")
    args = ap.parse_args()

    ua = os.getenv("USER_AGENT", "")
    if not ua:
        raise SystemExit("USER_AGENT is unset; NFR-5 requires one on every request.")
    out = ROOT / args.out
    out.mkdir(exist_ok=True)
    report = []

    with httpx.Client(timeout=45, headers={"User-Agent": ua}, follow_redirects=True) as c:
        for host in args.hosts:
            r: dict = {"host": host}
            print("\n=== " + host)
            rr = c.get("https://" + host + "/robots.txt")
            robots_text = rr.text if rr.status_code == 200 else ""
            rp = RobotFileParser()
            rp.parse(robots_text.splitlines())
            r["robots_http"] = rr.status_code
            r["final_host"] = urllib.parse.urlparse(str(rr.url)).hostname
            time.sleep(args.delay)

            # ── place 1: the sitemap robots advertises ──────────────────────
            sitemaps = [ln.split(":", 1)[1].strip()
                        for ln in robots_text.splitlines()
                        if ln.strip().lower().startswith("sitemap:")]
            r["sitemaps_advertised"] = sitemaps
            sitemap_hits = []
            for sm in sitemaps[:1]:
                if not allowance_for(rp, ua, sm).allowed:
                    r["sitemap_note"] = "robots disallows its own sitemap path"
                    continue
                time.sleep(args.delay)
                try:
                    sr = c.get(sm)
                except Exception as exc:                        # noqa: BLE001
                    r["sitemap_error"] = type(exc).__name__
                    continue
                r["sitemap_http"] = sr.status_code
                urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sr.text, re.I)
                r["sitemap_urls"] = len(urls)
                sitemap_hits = [u for u in urls
                                if any(w in u.lower() for w in TERMS_WORDS)]
            r["sitemap_terms_hits"] = sitemap_hits

            # ── place 2: the front page's own markup ────────────────────────
            home = "https://" + host + "/"
            time.sleep(args.delay)
            hr = c.get(home)
            r["home_http"] = hr.status_code
            r["home_terms_hits"] = hits_in(hr.text, home)

            r["terms_document_found"] = bool(sitemap_hits or r["home_terms_hits"])
            # ⚠ THE CONCLUSION IS ABOUT TWO PLACES, NOT ABOUT THE SITE.
            r["conclusion"] = (
                "terms-like link found - READ IT before writing terms_document_read"
                if r["terms_document_found"] else
                "absent from both places checked; NOT established as absent from the site"
            )
            print(f"  sitemap: {r.get('sitemap_http')} "
                  f"({r.get('sitemap_urls', 0)} urls, {len(sitemap_hits)} terms-like)")
            print(f"  front page: {r['home_http']}, "
                  f"{len(r['home_terms_hits'])} terms-like link(s)")
            for h in r["home_terms_hits"][:6]:
                print(f"      {h['matched']:<10} {h['text'][:34]:<34} {h['href'][:60]}")
            for u in sitemap_hits[:6]:
                print(f"      sitemap    {u[:80]}")
            print("  -> " + r["conclusion"])
            report.append(r)

    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\n  -> {out}/report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
