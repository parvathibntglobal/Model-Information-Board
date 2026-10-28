"""Link-preview pictures for the News page: the second exception to "no scraping".

anooj, 2026-10-28, recorded in CLAUDE.md beside the Benchmarks exception. Most
news feeds carry no picture (TechCrunch, AIWire, OpenAI, OpenRouter, Mistral,
TLDR AI: none, measured 2026-10-28), and TechCrunch's API is disallowed by its
robots.txt (`Disallow: /wp-json/`). So for a story whose feed has no picture,
the article's own page is asked once for the picture its publisher sets for link
previews - `og:image`, else `twitter:image` - the tag Slack, X and LinkedIn read.

ITS CONDITIONS ARE NOT SETTINGS:
  1. Only the links the listed feeds themselves give, only for a story with no
     feed picture, at most once per story (`preview_checked_at`); nothing is
     crawled or discovered.
  2. robots.txt is asked for the article and for every redirect hop; there is
     no switch to turn it off. Identifying User-Agent.
  3. Only the page's <head> is read: the response is streamed and closed at
     </head> or `max_head_bytes`. The article's text is never read, kept or
     shown. What is kept is the picture's link; the picture itself is never
     downloaded - the reader's browser loads it from the publisher, as any link
     preview does. https only.
  4. No logins, paywalls, keys or models.
  5. The <head> read is kept in the raw store, so a parser fix reprocesses it
     instead of asking again.
Switched off as a whole by `link_preview.enabled: false` in
contract/news_sources.yaml.
"""

from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urljoin

MAX_REDIRECTS = 5
_META = re.compile(r"<meta\b[^>]*>", re.I)
_ATTR = re.compile(r"""\b(property|name|content)\s*=\s*(["'])(.*?)\2""", re.I | re.S)
_HEAD_END = re.compile(rb"</head\s*>", re.I)
_PREFERRED = ("og:image:secure_url", "og:image", "og:image:url", "twitter:image",
              "twitter:image:src")


_DESCRIPTIONS = ("og:description", "twitter:description", "description")


def _meta_tags(head: str, wanted: tuple[str, ...]) -> dict[str, str]:
    """The first value of each wanted <meta property|name=...> in the <head>."""
    found: dict[str, str] = {}
    for tag in _META.findall(head):
        attrs = {k.lower(): v for k, _, v in _ATTR.findall(tag)}
        key = (attrs.get("property") or attrs.get("name") or "").strip().lower()
        if key in wanted and attrs.get("content") and key not in found:
            found[key] = html.unescape(attrs["content"].strip())
    return found


def description_from_head(head: str) -> str | None:
    """The page's own description of itself - the sentence its publisher wrote
    for link previews and search results. Read from the same <head>; never the
    article's text."""
    found = _meta_tags(head, _DESCRIPTIONS)
    return next((found[k] for k in _DESCRIPTIONS if found.get(k)), None)


def picture_from_head(head: str, base_url: str) -> str | None:
    """The link-preview picture a page's <head> declares, made absolute; https only."""
    found = _meta_tags(head, _PREFERRED)
    for key in _PREFERRED:
        if key in found:
            url = urljoin(base_url, found[key])
            return url if url.startswith("https://") else None
    return None


@dataclass(frozen=True)
class HeadRead:
    """One article page's <head>, as the publisher served it.

    `content` is the platform's own bytes - the start of the response, cut at
    </head> - and is what the raw store keeps (tests/test_writers_store_the_
    payload.py). None when nothing was read; `outcome` says why."""

    content: bytes | None
    url: str | None
    outcome: str


def read_head(client, gate, url: str, max_bytes: int) -> HeadRead:
    """Stream the page and stop at </head>; robots.txt asked for every hop."""
    for _ in range(MAX_REDIRECTS + 1):
        decision = gate.allows(url)
        if not decision.allowed:
            return HeadRead(None, None, f"robots.txt: {decision.reason}")
        with client.stream("GET", url, headers={"Accept": "text/html"}) as response:
            if response.is_redirect:
                url = str(response.next_request.url)
                continue
            if response.status_code != 200:
                return HeadRead(None, None, f"HTTP {response.status_code}")
            if "html" not in response.headers.get("content-type", ""):
                return HeadRead(None, None, "not an HTML page")
            got = b""
            for chunk in response.iter_bytes():
                got += chunk
                end = _HEAD_END.search(got)
                if end:
                    return HeadRead(got[: end.end()], str(response.url), "ok")
                if len(got) >= max_bytes:
                    return HeadRead(got[:max_bytes], str(response.url),
                                    "ok (no </head> within the limit)")
            return HeadRead(got, str(response.url), "ok")
    return HeadRead(None, None, f"more than {MAX_REDIRECTS} redirects")


# RECENT BY THE STORY'S OWN DATE, not by when we first saw it: on a source's
# first read every item is "first seen" today, and OpenAI's feed alone holds
# 1,330 posts going back years (2026-10-28) - asked by first_seen_at, the run's
# budget went on its archive.
_CANDIDATES = """
SELECT id, url, title, summary, summary_source FROM news_item
WHERE image_url IS NULL AND preview_checked_at IS NULL AND daily_count IS NULL
  AND source_key = ANY(%s) AND coalesce(published_at, first_seen_at) >= %s
ORDER BY coalesce(published_at, first_seen_at) DESC
LIMIT %s
"""


def better_brief(head: str, title: str, summary: str | None, summary_source: str | None,
                 contract) -> tuple[str | None, str | None]:
    """The page's own description when it makes a fuller, complete brief than the
    feed's (harvest.choose_brief); otherwise what the story already has."""
    from collect.news.harvest import choose_brief, summarise

    page = summarise(description_from_head(head), contract.summary_max_words)
    return choose_brief([(summary, summary_source), (page, "page_description")], title, contract)


def fill_pictures(conn, client, gate, store, *, settings_: dict[str, Any],
                  source_keys: list[str], now: datetime, contract=None) -> dict[str, int]:
    """Ask the newest picture-less stories for their link-preview picture, once each.

    THE SAME <head> ALSO GIVES THE PAGE'S OWN DESCRIPTION (anooj, 2026-10-28):
    feed summaries are often a teaser, cut off with an ellipsis, or missing, and
    the publisher's description tag is usually one complete sentence. It is
    used when it makes the fuller complete brief. No extra request is made."""
    counts = {"asked": 0, "found": 0, "none": 0, "refused": 0, "failed": 0}
    if not settings_["enabled"] or not source_keys:
        return counts
    since = now - timedelta(days=settings_["look_back_days"])
    rows = conn.execute(_CANDIDATES, (source_keys, since, settings_["max_per_run"])).fetchall()
    last_at: dict[str, float] = {}
    for item_id, url, title, summary, summary_source in rows:
        host = url.split("/")[2] if "//" in url else ""
        wait = gate.min_interval(url) - (time.monotonic() - last_at.get(host, -1e9))
        if wait > 0:
            time.sleep(wait)
        counts["asked"] += 1
        picture, raw_ref = None, None
        try:
            read = read_head(client, gate, url, settings_["max_head_bytes"])
        except Exception:  # noqa: BLE001 - one page failing never stops the others
            read = HeadRead(None, None, "error")
        last_at[host] = time.monotonic()
        if read.content is not None:
            raw_ref = store.put(read.content).ref
            head = read.content.decode("utf-8", errors="replace")
            picture = picture_from_head(head, read.url or url)
            counts["found" if picture else "none"] += 1
            if contract is not None:
                brief, source = better_brief(head, title, summary, summary_source, contract)
                if brief != summary:
                    counts["briefs"] = counts.get("briefs", 0) + 1
                    conn.execute("UPDATE news_item SET summary = %s, summary_source = %s "
                                 "WHERE id = %s", (brief, source, item_id))
        else:
            counts["refused" if read.outcome.startswith("robots") else "failed"] += 1
        conn.execute(
            "UPDATE news_item SET image_url = %s, image_source = %s, preview_checked_at = %s, "
            "preview_raw_ref = %s WHERE id = %s AND image_url IS NULL",
            (picture, "link_preview" if picture else None, now, raw_ref, item_id),
        )
    return counts


def rebrief_from_stored_heads(conn, store, contract) -> int:
    """Apply `better_brief` to every story whose <head> is already in the raw
    store - no request is made. For a parser change, and for stories read before
    descriptions were used (2026-10-28)."""
    changed = 0
    for item_id, title, summary, summary_source, ref in conn.execute(
            "SELECT id, title, summary, summary_source, preview_raw_ref FROM news_item "
            "WHERE preview_raw_ref IS NOT NULL").fetchall():
        head = store.get(ref).decode("utf-8", errors="replace")
        brief, source = better_brief(head, title, summary, summary_source, contract)
        if brief != summary:
            conn.execute("UPDATE news_item SET summary = %s, summary_source = %s WHERE id = %s",
                         (brief, source, item_id))
            changed += 1
    return changed
