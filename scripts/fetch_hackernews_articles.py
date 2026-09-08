"""Fetch Hacker News discussion of a model for the Articles page. Standalone.

    py -3 scripts/fetch_hackernews_articles.py

CONTAINMENT. This imports nothing from `collect/` or `judge/`, opens no
database connection, and writes only under `var/` (gitignored) plus the report
under `articles/`. That is deliberate and it is the same containment the arXiv
path has: an unverified scrape must not be able to reach `document`, `claim` or
`cell`. The consequence is stated rather than worked around - because this does
not route through `harvester_for_source()`, the `assert_terms_reviewed()` gate
did not run, and `contract/sources.yaml` carries no ruling for Algolia/HN at
all. So this data is publishable on the Articles page and is NOT admissible to
the pipeline until somebody writes that ruling. See §9 of the report.

WHY COMMENTS, NOT STORIES. On HN the substance for this model sits in replies,
not submissions: the DeepClaude thread (id=48002136) is a bare GitHub link at
678 points whose evidence - a quoted price, the pricing URL, an expiry date, a
routing claim - is entirely in its comments. A story-only fetch returns the link
and loses the argument. So `tags` is left off the search (Algolia then returns
stories and comments both), and every comment match pulls its whole thread.

TWO ALGOLIA TRAPS, both handled here because both fail silently.

1. It prefix-matches query tokens, so `pro` matches *problem* and *production*.
   Raw hit counts are therefore not match counts, and every record is
   re-verified locally against the attested surfaces before it counts.
2. Pagination is capped at 1000 hits per query. A query with `nbHits` of 2016
   still reports `nbPages: 1` and hands back 1000 records with no error. Any
   window at or over the cap is bisected by `created_at_i` until it is under.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import re
import sys
import time
from datetime import UTC, datetime, timedelta

import httpx

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "var" / "hackernews"

API = "https://hn.algolia.com/api/v1"
HITS_CAP = 1000          # Algolia's paginationLimitedTo for this index
REQUEST_DELAY = 0.05     # 50ms; the API is free and unauthenticated, be polite
MONTHS_BACK = 6

#: The model's attested spellings. Not guesses - the Reddit sweep measured the
#: spaced form at roughly half of all mentions and the hyphenated dated form at
#: 59 occurrences, so both earn a query of their own. The bare `deepseek v4`
#: is included because Pro is routinely discussed under the family name.
KEYWORDS = [
    "DeepSeek V4 Pro",
    "deepseek v4 pro",
    "deepseek-v4-pro",
    "deepseek-v4-pro-0813",
    "deepseek v4",
]

#: Literal-match test, applied to every record the API returns. Separator-
#: insensitive so all four Pro surfaces collapse to one pattern; the optional
#: trailing digits catch the dated `-0813` build.
PRO_SURFACE = re.compile(r"deepseek[\s\-_]*v?4[\s\-_]*pro(?:[\s\-_]*\d{3,4})?", re.I)
#: Family-level match. A comment inside a thread about the model does not
#: repeat the full name, so thread context decides subject-hood, not this.
V4_SURFACE = re.compile(r"(deepseek[\s\-_]*v?4|\bds4\b|\bdsv4\b)", re.I)

FIELDS = (
    "objectID", "created_at", "created_at_i", "author", "title", "url",
    "story_text", "comment_text", "points", "num_comments", "story_id",
    "story_title", "story_url", "parent_id", "_tags",
)


# ── artifacts ───────────────────────────────────────────────────────────────
# The HN-specific finding: post length does not separate a checkable claim from
# an opinion. Carrying an artifact does. These four are each independently
# falsifiable by a reader - a link resolves or 404s, a number is right or wrong,
# a version string names a build that shipped or did not, a code fence runs.

ARTIFACT_LINK = re.compile(r"https?://[^\s<>\"')]+")
ARTIFACT_NUMBER = re.compile(
    r"(\$\s?\d|\b\d+(?:\.\d+)?\s*%|\b\d+(?:\.\d+)?\s*(?:tok(?:ens?)?/s|t/s|tps)\b"
    r"|\b\d+(?:\.\d+)?\s*[BTMK]\b|\bper\s+(?:million|1M|M)\b"
    r"|\b\d+(?:\.\d+)?\s*(?:GB|TB|GiB|MB|kWh|W)\b|\b\d+(?:\.\d+)?x\b)",
    re.I,
)
#: A version string BEYOND the bare model name - a dated build, or a rival's
#: version. The model's own surface is stripped before this runs, and that
#: matters: the naive detector that included `v4 pro` fired on 601 of 623
#: matched comments, because a keyword-matched corpus contains the keyword. A
#: figure that is 96% by construction measures the query, not the comment. What
#: is informative is whether the author was specific about a DIFFERENT build.
ARTIFACT_VERSION = re.compile(
    r"(\b0813\b|\b0731\b|\bV4[\s\-]?Flash\b|\bGPT-?5(?:\.\d)?\b"
    r"|\bOpus\s?4(?:\.\d)?\b|\bGLM-?5(?:\.\d)?\b|\bKimi\s?K[23](?:\.\d)?\b"
    r"|\bQwen\s?3(?:\.\d)?\b|\bMiMo[\s\-]?v?2(?:\.\d)?\b|\bGemini\s?3(?:\.\d)?\b"
    r"|\bFable\s?5\b|\bSonnet\s?[45](?:\.\d)?\b|\bV3\.\d\b|\bComposer\s?2(?:\.\d)?\b)",
    re.I,
)
#: Checked against the RAW HTML, not the stripped text. Algolia returns comment
#: bodies with `<pre><code>` intact and the stripper removes them, so running
#: this after stripping found 2 code blocks in the whole corpus and missed the
#: `#!/bin/sh` block in the DeepClaude thread that prompted this fetch.
ARTIFACT_CODE = re.compile(
    r"(<pre>|<code>|```|#!/|\bnpm\s+install\b|\bpip\s+install\b|\bcurl\s+-|"
    r"\bexport\s+[A-Z_]{3,}=|\bANTHROPIC_[A-Z_]+\b|\bpython\s+-m\b)")


def artifacts_of(text: str, raw: str | None = None) -> list[str]:
    """Which independently-checkable artifacts this comment carries.

    `text` is stripped plain text; `raw` is the original HTML when available,
    used only for code detection. Each artifact is falsifiable by a reader on
    its own: a link resolves or 404s, a number is right or wrong, a build string
    names something that shipped or did not, a code block runs or does not.
    """
    found = []
    if ARTIFACT_LINK.search(text):
        found.append("link")
    if ARTIFACT_NUMBER.search(text):
        found.append("number")
    if ARTIFACT_VERSION.search(PRO_SURFACE.sub(" ", text)):
        found.append("version")
    if ARTIFACT_CODE.search(raw if raw is not None else text):
        found.append("code")
    return found


def strip_html(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"<p>", "\n\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&#x27;", "'"), ("&quot;", '"'), ("&amp;", "&"),
                 ("&lt;", "<"), ("&gt;", ">"), ("&#x2F;", "/"), ("&nbsp;", " ")):
        s = s.replace(a, b)
    return re.sub(r"[ \t]+", " ", s).strip()


def slim(hit: dict) -> dict:
    return {k: hit.get(k) for k in FIELDS}


def text_of(rec: dict) -> str:
    return " ".join(str(rec.get(k) or "") for k in
                    ("title", "story_title", "url", "story_text", "comment_text"))


def is_comment(rec: dict) -> bool:
    return "comment" in (rec.get("_tags") or [])


# ── fetch ───────────────────────────────────────────────────────────────────

class Fetcher:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.calls = 0
        self.queries = 0
        self.bisections = 0

    async def _get(self, endpoint: str, params: dict) -> dict:
        await asyncio.sleep(REQUEST_DELAY)
        r = await self.client.get(f"{API}/{endpoint}", params=params, timeout=30)
        self.calls += 1
        r.raise_for_status()
        return r.json()

    async def window(self, endpoint: str, params: dict, lo: int, hi: int,
                     out: dict, depth: int = 0) -> None:
        """Fetch [lo, hi), bisecting when Algolia reports the window is capped."""
        p = dict(params, numericFilters=f"created_at_i>={lo},created_at_i<{hi}",
                 hitsPerPage=HITS_CAP, page=0)
        d = await self._get(endpoint, p)
        nb = d.get("nbHits") or 0

        if nb >= HITS_CAP and hi - lo > 3600:
            mid = lo + (hi - lo) // 2
            self.bisections += 1
            await self.window(endpoint, params, lo, mid, out, depth + 1)
            await self.window(endpoint, params, mid, hi, out, depth + 1)
            return

        for h in d.get("hits") or []:
            out[h["objectID"]] = slim(h)
        for page in range(1, d.get("nbPages") or 1):
            p["page"] = page
            d2 = await self._get(endpoint, p)
            for h in d2.get("hits") or []:
                out[h["objectID"]] = slim(h)

    async def thread_comments(self, story_id: str) -> dict:
        """Every comment on one story, so a matched reply arrives with its thread."""
        out: dict = {}
        page = 0
        while True:
            d = await self._get("search_by_date", {
                "tags": f"comment,story_{story_id}", "hitsPerPage": HITS_CAP, "page": page})
            hits = d.get("hits") or []
            for h in hits:
                out[h["objectID"]] = slim(h)
            page += 1
            if page >= (d.get("nbPages") or 1) or not hits:
                return out

    async def story(self, story_id: str) -> dict | None:
        d = await self._get("search", {"tags": f"story_{story_id}", "hitsPerPage": 5})
        for h in d.get("hits") or []:
            if h.get("objectID") == story_id:
                return slim(h)
        return None


async def run(months: int) -> dict:
    since = datetime.now(UTC) - timedelta(days=months * 30.5)
    t0, t1 = int(since.timestamp()), int(time.time()) + 3600

    async with httpx.AsyncClient(
        headers={"User-Agent": "model-information-board/articles (research)"},
        follow_redirects=True,
    ) as client:
        f = Fetcher(client)

        # ── pass 1: keyword sweeps, both endpoints, stories AND comments ──
        # `tags` is omitted on purpose: with no tag filter Algolia returns both,
        # which is the point. `search` and `search_by_date` rank differently, so
        # both run and the union is taken.
        records: dict[str, dict] = {}
        per_query: list[dict] = []
        for kw in KEYWORDS:
            for endpoint in ("search", "search_by_date"):
                got: dict = {}
                await f.window(endpoint, {"query": kw}, t0, t1, got)
                f.queries += 1
                matched = sum(1 for r in got.values() if PRO_SURFACE.search(text_of(r)))
                per_query.append({
                    "keyword": kw, "endpoint": endpoint,
                    "returned": len(got), "literal_pro_matches": matched,
                })
                print(f"  [{endpoint:15}] {kw!r:24} returned={len(got):5} "
                      f"literal={matched:5}", file=sys.stderr)
                records.update(got)

        # ── verify locally; the API's prefix matching cannot be trusted ──
        matched_ids = {oid for oid, r in records.items()
                       if PRO_SURFACE.search(text_of(r))}
        matched_comments = {oid for oid in matched_ids if is_comment(records[oid])}
        print(f"  union={len(records)} literal_pro={len(matched_ids)} "
              f"(comments={len(matched_comments)})", file=sys.stderr)

        # ── pass 2: follow every matched comment's thread ──
        story_ids: set[str] = set()
        for oid in matched_ids:
            r = records[oid]
            sid = str(r.get("story_id") or "") or (oid if not is_comment(r) else "")
            if sid:
                story_ids.add(sid)

        threads: dict[str, dict] = {}
        for n, sid in enumerate(sorted(story_ids), 1):
            st = await f.story(sid)
            comments = await f.thread_comments(sid)
            threads[sid] = {"story": st, "comments": list(comments.values())}
            if n % 10 == 0 or n == len(story_ids):
                print(f"  threads {n}/{len(story_ids)}", file=sys.stderr)

        return {
            "fetched_at": datetime.now(UTC).isoformat(),
            "api": API,
            "endpoints": ["search", "search_by_date", "search_by_date?tags=comment,story_<id>"],
            "auth": "none — Algolia's HN Search API is public and unauthenticated",
            "window": {"from": since.date().isoformat(),
                       "to": datetime.now(UTC).date().isoformat(),
                       "months": months},
            "keywords": KEYWORDS,
            "per_query": per_query,
            "stats": {"api_calls": f.calls, "queries": f.queries,
                      "bisections": f.bisections,
                      "records_returned": len(records),
                      "literal_pro_matches": len(matched_ids),
                      "literal_pro_comments": len(matched_comments),
                      "threads_followed": len(threads)},
            "records": records,
            "matched_ids": sorted(matched_ids),
            "threads": threads,
        }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--months", type=int, default=MONTHS_BACK)
    args = ap.parse_args()

    payload = asyncio.run(run(args.months))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"hn-deepseek-v4-pro-{stamp}.json"
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")

    s = payload["stats"]
    print(f"\n{s['api_calls']} API calls over {s['queries']} queries "
          f"({s['bisections']} bisections)")
    print(f"{s['records_returned']} records -> {s['literal_pro_matches']} literal matches "
          f"({s['literal_pro_comments']} of them comments)")
    print(f"{s['threads_followed']} threads followed")
    print(f"-> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
