"""Link-preview pictures for the News page: the second exception to "no scraping".

anooj, 2026-10-28, recorded in CLAUDE.md beside the Benchmarks exception. Most
news feeds carry no picture (TechCrunch, AIWire, OpenAI, OpenRouter, Mistral,
TLDR AI: none, measured 2026-10-28), and TechCrunch's API is disallowed by its
robots.txt (`Disallow: /wp-json/`). So for a story whose feed has no picture,
the article's own page is asked once for the picture its publisher sets for link
previews - `og:image`, else `twitter:image` - the tag Slack, X and LinkedIn read.

ITS CONDITIONS ARE NOT SETTINGS:
  1. Only the links the listed feeds themselves give, only for a story with no
     feed picture, until it gets an answer (`preview_checked_at`): a definite
     one - a picture, none, a refusal, a 4xx - is final; a failure that may pass
     (a timeout, a 5xx, a 429) is asked again, at most `max_attempts` times in
     all. Every outcome is kept (`preview_outcome`). Nothing is crawled or
     discovered.
  2. robots.txt is asked for the article and for every redirect hop; there is
     no switch to turn it off. Identifying User-Agent.
  3. Only the page's <head> is read: the response is streamed and closed at
     </head> or `max_head_bytes`. The article's text is never read, kept or
     shown. Two things are taken from the <head>: the picture's LINK (the
     picture itself is never downloaded - the reader's browser loads it from
     the publisher, as any link preview does), and the page's own DESCRIPTION
     tag, which becomes the story's brief when it is the fuller complete one
     (`summary_source = 'page_description'`; the feed's brief is kept beside it
     in `feed_summary`). https only, for the page and every hop.
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
        # HTTPS ONLY, the article and every hop (#583 review: the condition said
        # so and only the picture's URL was checked).
        if not url.startswith("https://"):
            return HeadRead(None, None, f"not https: {url[:120]}")
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
SELECT id, url, title, feed_summary, feed_summary_source, preview_attempts FROM news_item
WHERE image_url IS NULL AND preview_checked_at IS NULL AND daily_count IS NULL
  AND preview_attempts < %s
  AND source_key = ANY(%s) AND coalesce(published_at, first_seen_at) >= %s
ORDER BY coalesce(published_at, first_seen_at) DESC
LIMIT %s
"""


def outcome_of(read: HeadRead, picture: str | None) -> tuple[str, bool]:
    """(what happened, is it final). A CAUSED ABSENCE IS NOT A FOUND ONE (#583
    review): a timeout and "this page sets no picture" were the same row and
    neither was asked again. Now a definite answer is final, and a failure that
    may pass - a timeout, a 5xx, a 429, a 408 - is asked again."""
    if read.content is not None:
        return ("found" if picture else "none"), True
    why = read.outcome
    if why.startswith("robots"):
        return "robots_refused", True
    if why.startswith("not https"):
        return "not_https", True
    if why.startswith("not an HTML page"):
        return "not_html", True
    if why.startswith("HTTP "):
        code = int(why.split()[1])
        return "http_error", not (code >= 500 or code in (408, 429))
    return "error", False  # a timeout, a dropped connection, too many redirects


def better_brief(head: str, title: str, feed_summary: str | None,
                 feed_summary_source: str | None, contract) -> tuple[str | None, str | None]:
    """The page's own description when it makes a fuller, complete brief than the
    feed's (harvest.choose_brief); otherwise the feed's own. Always chosen from
    the FEED'S brief, kept unchanged in `feed_summary`, so re-choosing is
    repeatable and nothing the feed gave is lost (#583 review)."""
    from collect.news.harvest import choose_brief, summarise

    page = summarise(description_from_head(head), contract.summary_max_words)
    return choose_brief([(feed_summary, feed_summary_source), (page, "page_description")],
                        title, contract)


def fill_pictures(conn, client, gate, store, *, settings_: dict[str, Any],
                  source_keys: list[str], now: datetime, contract=None) -> dict[str, int]:
    """Ask the newest picture-less stories for their link-preview picture.

    THE SAME <head> ALSO GIVES THE PAGE'S OWN DESCRIPTION (anooj, 2026-10-28):
    feed summaries are often a teaser, cut off with an ellipsis, or missing, and
    the publisher's description tag is usually one complete sentence. It is
    used when it makes the fuller complete brief. No extra request is made.

    Each story's outcome is committed as soon as it is known (#583 review), so
    an error later in the run never takes earlier outcomes with it."""
    counts = {"asked": 0, "found": 0, "none": 0, "refused": 0, "failed": 0, "retry": 0}
    if not settings_["enabled"] or not source_keys:
        return counts
    since = now - timedelta(days=settings_["look_back_days"])
    rows = conn.execute(_CANDIDATES, (settings_["max_attempts"], source_keys, since,
                                      settings_["max_per_run"])).fetchall()
    last_at: dict[str, float] = {}
    for item_id, url, title, feed_summary, feed_source, attempts in rows:
        host = url.split("/")[2] if "//" in url else ""
        wait = gate.min_interval(url) - (time.monotonic() - last_at.get(host, -1e9))
        if wait > 0:
            time.sleep(wait)
        counts["asked"] += 1
        picture, raw_ref = None, None
        try:
            read = read_head(client, gate, url, settings_["max_head_bytes"])
        except Exception as exc:  # noqa: BLE001 - one page failing never stops the others
            read = HeadRead(None, None, f"error: {type(exc).__name__}")
        last_at[host] = time.monotonic()
        if read.content is not None:
            raw_ref = store.put(read.content).ref
            head = read.content.decode("utf-8", errors="replace")
            picture = picture_from_head(head, read.url or url)
            if contract is not None:
                brief, source = better_brief(head, title, feed_summary, feed_source, contract)
                if source == "page_description":
                    counts["briefs"] = counts.get("briefs", 0) + 1
                    conn.execute("UPDATE news_item SET summary = %s, summary_source = %s "
                                 "WHERE id = %s", (brief, source, item_id))
        outcome, final = outcome_of(read, picture)
        tried = attempts + 1
        # Given up after `max_attempts` transient failures: final, and it says so.
        final = final or tried >= settings_["max_attempts"]
        key = {"found": "found", "none": "none", "robots_refused": "refused"}.get(outcome, "failed")
        counts[key] += 1
        if not final:
            counts["retry"] += 1
        conn.execute(
            "UPDATE news_item SET image_url = coalesce(image_url, %s), "
            "image_source = coalesce(image_source, %s), preview_outcome = %s, "
            "preview_attempts = %s, preview_checked_at = %s, "
            "preview_raw_ref = coalesce(%s, preview_raw_ref) WHERE id = %s",
            (picture, "link_preview" if picture else None, outcome, tried,
             now if final else None, raw_ref, item_id),
        )
        conn.commit()
    return counts


def rebrief_from_stored_heads(conn, store, contract) -> int:
    """Apply `better_brief` to every story whose <head> is already in the raw
    store - no request is made. For a parser change, and for stories read before
    descriptions were used (2026-10-28). Chosen from the kept `feed_summary`, so
    running it twice changes nothing the second time."""
    changed = 0
    for item_id, title, feed_summary, feed_source, summary, ref in conn.execute(
            "SELECT id, title, feed_summary, feed_summary_source, summary, preview_raw_ref "
            "FROM news_item WHERE preview_raw_ref IS NOT NULL").fetchall():
        head = store.get(ref).decode("utf-8", errors="replace")
        brief, source = better_brief(head, title, feed_summary, feed_source, contract)
        if brief != summary:
            conn.execute("UPDATE news_item SET summary = %s, summary_source = %s WHERE id = %s",
                         (brief, source, item_id))
            changed += 1
    conn.commit()
    return changed
