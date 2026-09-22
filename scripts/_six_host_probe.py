"""Robots, feed discovery, and the two deciding numbers, for six unseated hosts.

WHAT THIS IS FOR

Six candidate blog hosts need the evidence a class A ruling wants before any of
them can be proposed for `contract/sources.yaml`. It probes, it writes down what
it saw, and it rules on nothing. Seating a feed is a contract change and gets
two eyes; this produces the evidence that argument would be made from.

FOUR STAGES, IN THIS ORDER, AND THE ORDER IS THE POINT

    1. robots.txt, and a PLATFORM CLASSIFICATION MADE BY PROBE. The hand
       classification of these six was wrong on three of them. So the label
       here is derived from fetched evidence - the `generator` meta tag, CDN
       hostnames in the homepage HTML, response headers, robots.txt body
       fingerprints - and every label is published WITH the evidence strings
       that produced it. The classifier's error rate is unmeasured, so under
       rule 8 it is a recorded field, never a gate: a host classified
       `unknown` is still probed.

    2. FEED DISCOVERY at nine conventional paths, plus whatever the homepage
       DECLARES in `<link rel=alternate>`. Both are reported, separately. A
       host with no feed is not a class A candidate, and the nine paths are
       what makes that a finding rather than a guess - "we looked in nine
       conventional places and in the page's own declaration" is a denominator
       (rule 7). A 200 that does not parse into entries is NOT a feed; many
       hosts serve their 404 page with a 200.

    3. TEN ENTRIES where robots permits: on-host ratio, median body length,
       template block, byline presence.

    4. THE TWO DECIDING NUMBERS, over ARTICLE TEXT: how many of ten name a
       tracked model, and how many resolve to exactly one. Measured with
       `RegistrySurfaceFinder` and `RegistrySurfaceResolver` - the registry's
       own population, not a regex written here, so the number means the same
       thing it means in `_blog_corpus_census.py`.

       MEASURED OVER ARTICLE TEXT AND NOT OVER THE FEED, and the probe reports
       the feed-only figure beside it to show why. Lil'Log and Eugene Yan
       publish SUMMARIES in their feeds - 817 and 95 median characters - and
       the feed-only measurement on a summary feed returns zero while the
       articles are full of model names. A zero that is an artefact of where
       you measured is rule 4 one stage before the page.

POLITENESS. One request per second or slower, the project User-Agent on every
request, robots read first per host and re-checked per URL. A path robots
refuses is NAMED, never silently skipped.

    python scripts/_six_host_probe.py
    python scripts/_six_host_probe.py --hosts swyx.io --pages 10
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import re
import statistics
import sys
import time
import urllib.parse

import feedparser
import httpx
import psycopg
import trafilatura
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from urllib.robotparser import RobotFileParser  # noqa: E402

from collect.adapters.blog.rules import allowance_for  # noqa: E402
from collect.surface_resolver import (  # noqa: E402
    RegistrySurfaceFinder,
    RegistrySurfaceResolver,
)

HOSTS = [
    "minimaxir.com",
    "fast.ai",
    "matt-rickard.com",
    "thorstenball.com",
    "maggieappleton.com",
    "swyx.io",
]

#: The nine. Chosen to cover the shapes the nine SEATED feeds actually use
#: (`/index.xml`, `/feed/`, `/feed.xml`, `/feed`) plus the common remainder.
#: Nine is the denominator this probe's "no feed" finding is drawn from, so it
#: is a fixed list rather than a search that stops when it succeeds.
CONVENTIONAL_PATHS = [
    "/feed",
    "/feed/",
    "/feed.xml",
    "/rss",
    "/rss.xml",
    "/index.xml",
    "/atom.xml",
    "/blog/feed",
    "/blog/index.xml",
]

#: Evidence -> platform. Each entry is (label, where, needle). Every matching
#: rule is recorded, so a host that trips two fingerprints shows both rather
#: than only the first.
FINGERPRINTS = [
    ("substack", "html", "substackcdn.com"),
    ("substack", "html", "substack.com/api"),
    ("substack", "robots", "/api/v1/archive"),
    ("substack", "header:x-served-by", "substack"),
    ("ghost", "html", 'content="Ghost'),
    ("ghost", "header:x-ghost-cache-status", ""),
    ("wordpress", "html", "/wp-content/"),
    ("wordpress", "html", 'content="WordPress'),
    ("medium", "html", "cdn-client.medium.com"),
    ("hugo", "html", 'content="Hugo'),
    ("jekyll", "html", 'content="Jekyll'),
    ("gatsby", "html", "gatsby-"),
    ("next.js", "html", "/_next/static"),
    ("astro", "html", 'content="Astro'),
    ("eleventy", "html", 'content="Eleventy'),
    ("quarto", "html", 'content="quarto'),
    ("netlify", "header:server", "netlify"),
    ("vercel", "header:server", "vercel"),
    ("cloudflare", "header:server", "cloudflare"),
    ("github-pages", "header:server", "github.com"),
]

GENERATOR_RE = re.compile(
    r'<meta[^>]+name=["\']generator["\'][^>]*content=["\']([^"\']+)', re.I
)
ALT_FEED_RE = re.compile(r'<link[^>]+rel=["\']alternate["\'][^>]*>', re.I)
HREF_RE = re.compile(r'href=["\']([^"\']+)', re.I)
FEED_TYPE_RE = re.compile(r'type=["\']([^"\']*(?:rss|atom|xml)[^"\']*)', re.I)
AUTHOR_META_RE = re.compile(
    r'(?:name|property)=["\'](?:author|article:author)["\']', re.I
)
CANONICAL_RE = re.compile(
    r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', re.I
)


def _ua() -> str:
    ua = os.getenv("USER_AGENT", "")
    if not ua:
        raise SystemExit(
            "USER_AGENT is unset. NFR-5 requires an identifying User-Agent with a "
            "contact URL on every request; there is no default, deliberately."
        )
    return ua


def _classify(html: str, robots_text: str, headers) -> dict:
    """Platform label DERIVED FROM FETCHED EVIDENCE, published with the evidence.

    Never a gate (rule 8). The evidence fields are the finding; `label` is a
    convenience over them, and a reader who disagrees has what they need.
    """
    hits: list[dict] = []
    low_html, low_robots = html.lower(), robots_text.lower()
    for label, where, needle in FINGERPRINTS:
        if where == "html":
            if needle.lower() in low_html:
                hits.append({"platform": label, "evidence": "html contains " + repr(needle)})
        elif where == "robots":
            if needle.lower() in low_robots:
                hits.append(
                    {"platform": label, "evidence": "robots.txt contains " + repr(needle)}
                )
        elif where.startswith("header:"):
            key = where.split(":", 1)[1]
            val = headers.get(key) if headers else None
            if val is not None and needle.lower() in val.lower():
                hits.append({"platform": label, "evidence": key + ": " + val})
    generator = None
    m = GENERATOR_RE.search(html)
    if m:
        generator = m.group(1).strip()
    platforms = sorted({h["platform"] for h in hits})
    return {
        "generator_meta": generator,
        "fingerprint_hits": hits,
        "platforms_matched": platforms,
        "label": (generator or (platforms[0] if platforms else "unknown")),
        # The question this probe exists to answer. A custom domain in front of
        # a hosted platform is invisible in the URL and loud in the HTML.
        "hosted_platform_detected": bool(
            {"substack", "medium", "ghost", "wordpress"} & set(platforms)
        ),
    }


def _declared_feeds(html: str, base: str) -> list[str]:
    out = []
    for tag in ALT_FEED_RE.findall(html):
        if not FEED_TYPE_RE.search(tag):
            continue
        href = HREF_RE.search(tag)
        if href:
            out.append(urllib.parse.urljoin(base, href.group(1)))
    return sorted(set(out))


def _is_feed(content: bytes):
    """A feed is a thing that PARSES INTO ENTRIES, not a thing that 200s.

    ⚠ `version` IS NOT ALWAYS PRESENT, AND ASSUMING IT ABORTED A WHOLE PROBE.
      `feedparser.parse(b"")` returns a `FeedParserDict` with **no** `version`
      attribute at all — unlike HTML or JSON input, which return one set to
      `""`. So `parsed.version` raises `AttributeError` on exactly one input:
      an empty body.

      `danluu.com` serves one, on a conventional feed path, and the probe died
      with `AttributeError: object has no attribute 'version'` before it
      reached robots-permitted articles, feed discovery or the two deciding
      numbers. The six hosts probed on 2026-09-21 happened not to serve an
      empty body anywhere, which is why this survived that run.

      Rule 12: a permissive attribute access that works on every input except
      the one that matters. `getattr` with a default makes the empty body what
      it actually is — not a feed — instead of an exception.
    """
    parsed = feedparser.parse(content)
    version = getattr(parsed, "version", "") or ""
    return parsed, bool(version) and len(parsed.entries) > 0


def probe_host(host, client, ua, pages, delay, threshold, finder, resolver,
               canonical, out_root) -> dict:
    out = out_root / host
    out.mkdir(parents=True, exist_ok=True)
    r: dict = {"host": host}
    print("\n=== " + host + " " + "=" * max(0, 58 - len(host)))

    # -- 1. robots first -----------------------------------------------------
    robots_url = "https://" + host + "/robots.txt"
    robots_text = ""
    try:
        rr = client.get(robots_url)
        robots_text = rr.text if rr.status_code == 200 else ""
        r["robots_http"] = rr.status_code
        # ⚠ THE REDIRECT IS RECORDED BECAUSE IT CHANGES WHICH HOST IS THE
        #   CANDIDATE. `matt-rickard.com` 308s to `mattrickard.com`; the robots
        #   obeyed and the articles fetched are the TARGET's, so a ruling
        #   naming the requested host would name a host that serves nothing.
        #   Following is correct, silently following is not.
        r["robots_final_url"] = str(rr.url)
        r["robots_redirect_chain"] = [str(h.url) for h in rr.history]
        final_host = urllib.parse.urlparse(str(rr.url)).hostname or host
        r["canonical_host"] = final_host
        r["host_redirects"] = final_host != host
    except Exception as exc:                                    # noqa: BLE001
        r["robots_http"] = None
        r["robots_error"] = type(exc).__name__
        r["canonical_host"] = host
        r["host_redirects"] = None
    # A 404 is a DEFINITE value - the server answered, and the answer is that
    # there are no rules - and is not the same as no answer. The mapping is
    # collect/adapters/blog/robots.py's; mirrored here rather than re-decided.
    if r["robots_http"] == 200:
        r["robots_status"] = "rules"
    elif r["robots_http"] in (404, 410):
        r["robots_status"] = "no-rules"
    elif r["robots_http"] in (401, 403):
        r["robots_status"] = "refused"
    else:
        r["robots_status"] = "no-answer"
    (out / "robots.txt").write_text(robots_text, encoding="utf-8")
    rp = RobotFileParser()
    rp.parse(robots_text.splitlines())
    # A `Content-signal` line is the publisher speaking about AI use IN the
    # crawl policy - closer to terms than robots usually gets, and the class A
    # ruling records that no terms page has been read. Captured verbatim; it is
    # evidence for that reading, not a substitute for it.
    r["content_signal"] = [
        ln.strip() for ln in robots_text.splitlines()
        if ln.strip().lower().startswith("content-signal")
    ]
    print("  robots " + str(r["robots_http"]) + "  -> " + r["robots_status"]
          + ("  REDIRECTS TO " + str(r.get("canonical_host")) if r.get("host_redirects") else "")
          + ("  " + str(r["content_signal"]) if r["content_signal"] else ""))
    time.sleep(delay)

    # -- homepage: classification evidence + declared feeds ------------------
    home = "https://" + host + "/"
    r["homepage_allowed"] = allowance_for(rp, ua, home).allowed
    html, headers = "", {}
    if r["homepage_allowed"] and r["robots_status"] != "refused":
        try:
            hr = client.get(home)
            html, headers = hr.text, hr.headers
            r["homepage_http"] = hr.status_code
            r["final_homepage_url"] = str(hr.url)
        except Exception as exc:                                # noqa: BLE001
            r["homepage_http"] = None
            r["homepage_error"] = type(exc).__name__
        time.sleep(delay)
    r["classification"] = _classify(html, robots_text, headers)
    r["declared_feeds"] = _declared_feeds(html, home)
    c = r["classification"]
    print("  platform: " + repr(c["label"]) + "  hosted="
          + str(c["hosted_platform_detected"]) + "  matched=" + str(c["platforms_matched"]))
    for h in c["fingerprint_hits"][:6]:
        print("      " + h["platform"].ljust(12) + " " + h["evidence"][:70])
    print("  declared feeds in homepage HTML: " + str(r["declared_feeds"] or "none"))

    # -- 2. the nine conventional paths --------------------------------------
    conventional: list[dict] = []
    if r["robots_status"] == "refused":
        print("  robots refuses this user-agent entirely. No paths probed.")
    else:
        for path in CONVENTIONAL_PATHS:
            url = "https://" + host + path
            if not allowance_for(rp, ua, url).allowed:
                conventional.append({"path": path, "robots": "disallowed"})
                print("    " + path.ljust(18) + " ROBOTS DISALLOWS")
                continue
            time.sleep(delay)
            try:
                resp = client.get(url)
            except Exception as exc:                            # noqa: BLE001
                conventional.append({"path": path, "error": type(exc).__name__})
                print("    " + path.ljust(18) + " FAILED " + type(exc).__name__)
                continue
            parsed, ok = _is_feed(resp.content)
            conventional.append({
                "path": path, "robots": "allowed", "http": resp.status_code,
                "content_type": resp.headers.get("content-type"),
                "parses_as_feed": ok,
                "feed_type": getattr(parsed, "version", "") or None,
                "entries": len(parsed.entries),
                "final_url": str(resp.url),
            })
            print("    " + path.ljust(18) + " " + str(resp.status_code) + "  "
                  + ("FEED" if ok else "    ") + "  "
                  + (getattr(parsed, "version", "") or "-").ljust(8)
                  + str(len(parsed.entries)).rjust(3) + " entries")
    r["conventional_paths"] = conventional
    hits = [x for x in conventional if x.get("parses_as_feed")]
    r["conventional_feed_hits"] = [h["path"] for h in hits]
    r["feed_found"] = bool(hits) or bool(r["declared_feeds"])
    # A feed found ONLY by declaration is a different fact from one at a
    # conventional path, and the class A question is "is there a public feed",
    # so both count - separately, and labelled.
    r["feed_discovery"] = (
        "conventional" if hits else ("declared-only" if r["declared_feeds"] else "none")
    )
    if not r["feed_found"]:
        print("  NO FEED at " + str(len(CONVENTIONAL_PATHS)) + " conventional paths or "
              "in the homepage declaration. NOT A CLASS A CANDIDATE.")
        (out / "report.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
        return r

    chosen = (
        max(hits, key=lambda h: h["entries"])["final_url"]
        if hits else r["declared_feeds"][0]
    )
    r["feed_chosen"] = chosen
    print("  feed chosen: " + chosen)

    # -- 3. the feed and ten entries -----------------------------------------
    time.sleep(delay)
    fr = client.get(chosen)
    (out / "feed.xml").write_bytes(fr.content)
    parsed = feedparser.parse(fr.content)
    r["feed_http"] = fr.status_code
    r["feed_type"] = getattr(parsed, "version", "") or "unknown"
    r["feed_malformed"] = bool(parsed.bozo)
    entries = parsed.entries
    r["feed_entries"] = len(entries)

    # BYLINES. A feed-level `author` is the publication saying who it is; an
    # ENTRY-level author is the entry carrying one. Different facts, and a
    # single-author blog usually has only the first. voice_id needs the second.
    r["feed_declared_author"] = parsed.feed.get("author") or None
    entry_bylines = [e.get("author") for e in entries if e.get("author")]
    r["entry_bylines_present"] = len(entry_bylines)
    r["distinct_entry_bylines"] = len(set(entry_bylines))
    r["entries_unbylined"] = len(entries) - len(entry_bylines)

    feed_host = urllib.parse.urlparse(chosen).hostname or ""
    all_links = [e.get("link") for e in entries if e.get("link")]
    offhost = [u for u in all_links
               if (urllib.parse.urlparse(u).hostname or "") != feed_host]
    r["offhost_entry_links"] = offhost
    r["offhost_hosts"] = sorted({urllib.parse.urlparse(u).hostname or "" for u in offhost})
    r["onhost_ratio"] = (
        round((len(all_links) - len(offhost)) / len(all_links), 3) if all_links else None
    )
    if offhost:
        print("  WARNING: " + str(len(offhost)) + "/" + str(len(all_links))
              + " entry links are OFF-HOST (" + ", ".join(r["offhost_hosts"])
              + "). NOT FETCHED.")

    onhost_entries = [e for e in entries
                      if e.get("link") and e["link"] not in offhost][:pages]
    links = [e["link"] for e in onhost_entries]
    r["articles_requested"] = len(links)

    # The feed-side summary lengths, which is what makes the article-vs-feed
    # point measurable rather than asserted.
    summaries = [(e.get("summary") or e.get("description") or "") for e in onhost_entries]
    summary_text = [re.sub(r"<[^>]+>", " ", s) for s in summaries]
    r["median_feed_summary_chars"] = (
        int(statistics.median([len(s) for s in summary_text])) if summary_text else None
    )

    texts: dict[str, str] = {}
    html_by_url: dict[str, str] = {}
    statuses, refused = [], []
    for i, link in enumerate(links, 1):
        if not allowance_for(rp, ua, link).allowed:
            refused.append(link)
            print("   " + str(i).rjust(2) + ". ROBOTS REFUSES " + link)
            continue
        time.sleep(delay)
        try:
            art = client.get(link)
        except Exception as exc:                                # noqa: BLE001
            print("   " + str(i).rjust(2) + ". FAILED " + link + " (" + type(exc).__name__ + ")")
            continue
        statuses.append(art.status_code)
        text = trafilatura.extract(art.text) or ""
        texts[link] = text
        html_by_url[link] = art.text
        (out / ("a" + str(i).zfill(2) + ".html")).write_text(art.text, encoding="utf-8")
        print("   " + str(i).rjust(2) + ". " + str(art.status_code) + "  "
              + str(len(text)).rjust(6) + " chars  " + link[:78])

    r["robots_refused_article_paths"] = refused
    r["article_http"] = sorted(set(statuses))
    r["articles_fetched"] = len(texts)
    lens = sorted(len(t) for t in texts.values())
    r["median_body_chars"] = int(statistics.median(lens)) if lens else None
    # Rule 8: reported as evidence, never as a verdict. A short body was a
    # meta-refresh stub on eugeneyan.com, not a paywall.
    r["paywall_observed"] = "unknown - see short_bodies"
    r["short_bodies"] = sorted(
        ({"url": u, "chars": len(x)} for u, x in texts.items() if len(x) < 500),
        key=lambda x: x["chars"],
    )
    # A byline in the ARTICLE is a different question from one in the feed,
    # and it is the one a future author extractor would read.
    r["articles_with_author_meta"] = sum(
        1 for h in html_by_url.values() if AUTHOR_META_RE.search(h)
    )

    # ── CLASSIFY AGAIN, OVER THE ARTICLE PAGES ──────────────────────────────
    # ⚠ THE HOMEPAGE IS THE WRONG PAGE TO ASK, and this is the probe's own
    #   near-miss. A hosted platform behind a custom domain shows itself on
    #   the ARTICLE - its canonical tag, its embed scripts, its CDN - and a
    #   marketing homepage can be a hand-built page in front of it. swyx.io's
    #   homepage carried no platform marker at all, and the articles carry
    #   'substack' 134 times; 132 of them are in ONE post that is ABOUT
    #   Substack, the canonicals all point at swyx.io and there are no embeds.
    #   Counting per page rather than over a concatenation is what separates
    #   those two readings, so the per-page counts are the finding.
    marker_pages: dict[str, int] = {}
    for h in html_by_url.values():
        low = h.lower()
        for _label, where, needle in FINGERPRINTS:
            if where == "html" and needle.lower() in low:
                marker_pages[needle] = marker_pages.get(needle, 0) + 1
        for needle in ("substack", "medium.com", "ghost.io", "beehiiv"):
            if needle in low:
                marker_pages[needle] = marker_pages.get(needle, 0) + 1
    r["article_markers_in_pages"] = marker_pages
    canon = [m.group(1) for h in html_by_url.values()
             for m in [CANONICAL_RE.search(h)] if m]
    r["article_canonical_hosts"] = sorted(
        {urllib.parse.urlparse(u).hostname or "" for u in canon}
    )
    r["articles_with_canonical"] = len(canon)
    embeds = sorted({
        re.sub(r"^(https?://[^/]+).*", r"\1", m.group(1))
        for h in html_by_url.values()
        for m in re.finditer(r'<(?:script|iframe)[^>]+src=["\']([^"\']+)', h, re.I)
        if m.group(1).startswith("http")
    })
    r["article_embed_origins"] = embeds
    # The ruling-relevant conclusion, stated as the conjunction it actually is.
    r["self_served_articles"] = (
        r["article_canonical_hosts"] in ([], [feed_host])
        and not any(("substack" in e or "medium.com" in e) for e in embeds)
    )
    print("  article canonicals: " + str(r["article_canonical_hosts"])
          + "  embeds: " + str(embeds or "none")
          + "  self-served=" + str(r["self_served_articles"]))

    # -- template block ------------------------------------------------------
    counts: collections.Counter[str] = collections.Counter()
    for text in texts.values():
        for line in {ln.strip() for ln in text.splitlines() if len(ln.strip()) > 15}:
            counts[line] += 1
    n = len(texts)
    repeated = [(ln, c2) for ln, c2 in counts.most_common() if n and c2 / n >= threshold]
    r["pages_examined"] = n
    r["template_threshold"] = threshold
    r["repeated_lines"] = [{"line": ln, "in_pages": c2} for ln, c2 in repeated]
    r["template_block_status"] = "clean" if not repeated else "block-found"

    # -- 4. the two deciding numbers, over ARTICLE TEXT ----------------------
    per_entry = []
    for u, text in texts.items():
        surfaces = tuple(finder(text))
        ids = {resolver(s) for s in surfaces}
        ids.discard(None)
        models = sorted({canonical.get(i, i) for i in ids})
        per_entry.append({
            "url": u, "chars": len(text),
            "surfaces": sorted(set(surfaces)), "models": models,
            "names_model": bool(models), "resolves_to_one": len(models) == 1,
        })
    r["per_entry"] = per_entry
    r["names_a_tracked_model"] = sum(1 for e in per_entry if e["names_model"])
    r["resolves_to_exactly_one"] = sum(1 for e in per_entry if e["resolves_to_one"])

    # The same two numbers over the FEED SUMMARY, for contrast only.
    feed_names = feed_one = 0
    for s in summary_text:
        surfaces = tuple(finder(s))
        ids = {resolver(x) for x in surfaces}
        ids.discard(None)
        models = sorted({canonical.get(i, i) for i in ids})
        feed_names += bool(models)
        feed_one += len(models) == 1
    r["names_a_tracked_model_FEED_ONLY"] = feed_names
    r["resolves_to_exactly_one_FEED_ONLY"] = feed_one

    print("\n  " + str(n) + " pages examined, " + str(len(repeated))
          + " line(s) in >= " + format(threshold, ".0%"))
    for line, c2 in repeated[:8]:
        print("      " + str(c2) + "/" + str(n) + "  " + line[:92])
    print("  median body " + str(r["median_body_chars"]) + " chars   median feed summary "
          + str(r["median_feed_summary_chars"]) + " chars")
    print("  NAMES A TRACKED MODEL   " + str(r["names_a_tracked_model"]) + "/" + str(n)
          + "   (feed-only would say " + str(feed_names) + "/" + str(n) + ")")
    print("  RESOLVES TO EXACTLY ONE " + str(r["resolves_to_exactly_one"]) + "/" + str(n)
          + "   (feed-only would say " + str(feed_one) + "/" + str(n) + ")")
    if r["entry_bylines_present"] == 0:
        print("  ** UNBYLINED: 0 of " + str(len(entries))
              + " feed entries carry an author. **")

    (out / "report.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hosts", nargs="*", default=HOSTS)
    ap.add_argument("--pages", type=int, default=10)
    ap.add_argument("--threshold", type=float, default=0.8)
    ap.add_argument("--delay", type=float, default=1.1)
    ap.add_argument("--out", default="_six_host_probe")
    args = ap.parse_args()

    ua = _ua()
    out_root = ROOT / args.out
    out_root.mkdir(exist_ok=True)

    # READ-ONLY. The registry is the population for both deciding numbers, and
    # this probe has no business writing to it.
    dsn = os.environ["DATABASE_URL"]
    sep = "&" if "?" in dsn else "?"
    dsn = dsn + sep + "options=" + urllib.parse.quote("-c default_transaction_read_only=on")
    with psycopg.connect(dsn, connect_timeout=15) as conn:
        finder = RegistrySurfaceFinder.from_connection(conn)
        resolver = RegistrySurfaceResolver.from_connection(conn)
        canonical = dict(conn.execute("SELECT id, canonical_id FROM model_version").fetchall())
    print("  registry: " + str(len(canonical)) + " model_version rows (read-only)")

    reports = []
    with httpx.Client(timeout=45, headers={"User-Agent": ua}, follow_redirects=True) as client:
        for host in args.hosts:
            try:
                reports.append(probe_host(host, client, ua, args.pages, args.delay,
                                          args.threshold, finder, resolver, canonical,
                                          out_root))
            except Exception as exc:                            # noqa: BLE001
                print("  " + host + ": ABORTED " + type(exc).__name__ + ": " + str(exc))
                reports.append({"host": host, "aborted": type(exc).__name__ + ": " + str(exc)})

    (out_root / "summary.json").write_text(json.dumps(reports, indent=1), encoding="utf-8")
    print("\n  -> " + str(out_root) + "/summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
