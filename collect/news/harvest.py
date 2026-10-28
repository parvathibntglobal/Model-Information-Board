"""Read the news feeds into `news_item` (contract/news_sources.yaml, 2026-10-28).

One read per source per run, robots.txt asked first for the URL and for every
redirect hop (collect/adapters/blog/robots.py, which matches `*` and `$`). The
response is kept in the raw store before anything is parsed, so a parser fix
reprocesses what was read instead of reading again.

WHAT IS KEPT. What the feed gives: title, link, date, author, categories and
the summary with its HTML removed, cut to `summary_max_chars`. No article page
is fetched. A news item is never evidence - nothing here writes a claim, a
quote or a board entry, and no model reads it.

A MISSING DATE STAYS MISSING. `published_at` is the source's own date or NULL;
the time we read it is `first_seen_at`, a different fact (rule 6).

DAILY SOURCES. A source marked `daily` publishes automated builds many times a
day (llama.cpp), so each UTC day's items become one entry that grows as the day
goes on. Everything else is append-only: a link already stored is left alone.

EVERY READ IS RECORDED in `news_fetch`, refused and failed ones included, so a
quiet source and a broken one never look the same on the page (rule 4).
"""

from __future__ import annotations

import html
import re
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from collect.config import settings
from collect.ids import stable_id

CONTRACT = Path(__file__).resolve().parents[2] / "contract" / "news_sources.yaml"
KINDS = ("feed", "github_releases")
GROUPS = ("selected", "lab", "writer", "release")
MAX_REDIRECTS = 5


class NewsContractError(ValueError):
    """contract/news_sources.yaml is missing something a read needs (rule 12)."""


@dataclass(frozen=True)
class Source:
    key: str
    group: str
    label: str
    kind: str
    url: str
    daily: bool


@dataclass(frozen=True)
class Contract:
    summary_max_chars: int
    keywords: re.Pattern
    sources: tuple[Source, ...]


def load_contract(path: Path = CONTRACT) -> Contract:
    """Every value the harvest uses, refused when absent - no defaults here."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    problems: list[str] = []
    cap = raw.get("summary_max_chars")
    if not isinstance(cap, int) or isinstance(cap, bool) or cap <= 0:
        problems.append("summary_max_chars must be a positive integer")
    words = raw.get("llm_keywords")
    if not isinstance(words, list) or not words or not all(isinstance(w, str) and w for w in words):
        problems.append("llm_keywords must be a non-empty list of words")
    sources: list[Source] = []
    seen: set[str] = set()
    for i, s in enumerate(raw.get("sources") or []):
        where = f"sources[{i}]"
        for field in ("key", "group", "label", "kind", "url", "terms", "daily"):
            if field not in s or s[field] in (None, ""):
                problems.append(f"{where}: {field} is required")
        if s.get("group") not in GROUPS:
            problems.append(f"{where}: group must be one of {GROUPS}")
        if s.get("kind") not in KINDS:
            problems.append(f"{where}: kind must be one of {KINDS}")
        if not isinstance(s.get("daily"), bool):
            problems.append(f"{where}: daily must be true or false")
        if not str(s.get("url", "")).startswith("https://"):
            problems.append(f"{where}: url must be https://")
        if s.get("key") in seen:
            problems.append(f"{where}: key {s.get('key')!r} is listed twice")
        seen.add(s.get("key"))
        if not problems:
            sources.append(Source(s["key"], s["group"], s["label"], s["kind"], s["url"],
                                  s["daily"]))
    if not sources and not problems:
        problems.append("sources is empty")
    if problems:
        raise NewsContractError("contract/news_sources.yaml: " + "; ".join(problems))
    longest_first = sorted(words, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(w) for w in longest_first) + r")\b", re.I)
    return Contract(cap, pattern, tuple(sources))


# ── parsing ──────────────────────────────────────────────────────────────────

_TAGS = re.compile(r"<[^>]+>")


def clean(text: str | None, cap: int) -> str | None:
    """HTML removed, entities decoded, whitespace collapsed, cut to `cap`. None for empty."""
    if not text:
        return None
    flat = " ".join(html.unescape(_TAGS.sub(" ", text)).split())
    if not flat:
        return None
    return flat if len(flat) <= cap else flat[: cap - 1].rstrip() + "…"


def matched_keywords(pattern: re.Pattern, *texts: str | None) -> list[str]:
    found = {m.group(1).lower() for t in texts if t for m in pattern.finditer(t)}
    return sorted(found)


def parse_feed(body: bytes, contract: Contract, *, feed_url: str | None = None,
               content_type: str | None = None) -> list[dict[str, Any]]:
    """RSS or Atom items, through the lane's one feed parser (blog/parse.py), which
    never fetches. An item with no link or title is dropped: it cannot be shown.

    The date is the entry's PUBLISHED date only. A feed that gives only an
    "updated" time leaves it undated rather than dated by its last edit (rule 6)."""
    from collect.adapters.blog.parse import parse_feed as parse_bytes

    items = []
    for e in parse_bytes(body, feed_url=feed_url, content_type=content_type).entries:
        title = " ".join((e.title or "").split())
        if not e.url or not title:
            continue
        summary = clean(e.summary_html, contract.summary_max_chars)
        items.append({
            "url": e.url, "title": title, "published_at": e.published_at, "summary": summary,
            "author": e.author, "categories": list(e.categories),
            "llm_keywords": matched_keywords(contract.keywords, title, summary),
        })
    return items


def parse_github_releases(data: Any, contract: Contract) -> list[dict[str, Any]]:
    """Published releases from GitHub's REST API. Drafts have no public link."""
    if not isinstance(data, list):
        raise ValueError(f"expected a list of releases, got {type(data).__name__}")
    items = []
    for r in data:
        if not isinstance(r, dict) or r.get("draft") or not r.get("html_url"):
            continue
        title = (r.get("name") or "").strip() or r.get("tag_name") or ""
        when = r.get("published_at")
        summary = clean(r.get("body"), contract.summary_max_chars)
        items.append({
            "url": r["html_url"], "title": title,
            "published_at": datetime.fromisoformat(when.replace("Z", "+00:00")) if when else None,
            "summary": summary, "author": (r.get("author") or {}).get("login"),
            "categories": ["pre-release"] if r.get("prerelease") else [],
            "llm_keywords": matched_keywords(contract.keywords, title, summary),
            "tag": r.get("tag_name"),
        })
    return items


def fold_daily(items: list[dict[str, Any]], source: Source, *,
               window_full: bool) -> list[dict[str, Any]]:
    """One entry per UTC day: its newest item's link and date, and how many it holds.

    An undated item cannot be placed in a day, so it stays its own entry rather
    than being filed under a day it may not belong to (rule 6).

    THE OLDEST DAY OF A FULL WINDOW IS CUT SHORT. The API lists the newest 30
    releases, so when it returned 30 the earliest day in them may have had more
    than it shows: "6 releases on 2026-10-26" was a floor on 2026-10-28, not a
    count. That day's title says "at least" (rule 7); a later read can only grow
    it, never claim it complete."""
    days: dict[str, list[dict[str, Any]]] = {}
    out = []
    for it in items:
        if it["published_at"] is None:
            out.append(it)
        else:
            days.setdefault(it["published_at"].date().isoformat(), []).append(it)
    first_day = min(days) if days else None
    for day, group in days.items():
        group.sort(key=lambda it: it["published_at"])
        newest, oldest = group[-1], group[0]
        n = len(group)
        names = [it.get("tag") or it["title"] for it in (oldest, newest)]
        floor = "at least " if window_full and day == first_day else ""
        title = (f"{source.label}: {floor}{n} releases on {day} ({names[0]} - {names[1]})"
                 if n > 1 or floor else f"{source.label}: {names[1]}")
        out.append({
            "url": newest["url"], "title": title, "published_at": newest["published_at"],
            "summary": None, "author": None, "categories": [],
            "llm_keywords": sorted({k for it in group for k in it["llm_keywords"]}),
            "daily_day": day, "daily_count": n,
        })
    return out


# ── writing ──────────────────────────────────────────────────────────────────

_INSERT = """
INSERT INTO news_item (id, source_key, url, title, published_at, summary, author, categories,
                       llm_keywords, daily_count, raw_ref, first_seen_at, updated_at,
                       pipeline_version)
VALUES (%(id)s, %(source_key)s, %(url)s, %(title)s, %(published_at)s, %(summary)s, %(author)s,
        %(categories)s, %(llm_keywords)s, %(daily_count)s, %(raw_ref)s, %(now)s, %(now)s,
        %(pipeline_version)s)
ON CONFLICT (id) DO NOTHING
RETURNING id
"""

# A daily entry grows with its day and never shrinks: a later read that sees
# fewer of the day's items (the API lists the newest 30) leaves it as it was.
_UPSERT_DAILY = """
INSERT INTO news_item (id, source_key, url, title, published_at, summary, author, categories,
                       llm_keywords, daily_count, raw_ref, first_seen_at, updated_at,
                       pipeline_version)
VALUES (%(id)s, %(source_key)s, %(url)s, %(title)s, %(published_at)s, %(summary)s, %(author)s,
        %(categories)s, %(llm_keywords)s, %(daily_count)s, %(raw_ref)s, %(now)s, %(now)s,
        %(pipeline_version)s)
ON CONFLICT (id) DO UPDATE SET
  url = EXCLUDED.url, title = EXCLUDED.title, published_at = EXCLUDED.published_at,
  llm_keywords = EXCLUDED.llm_keywords, daily_count = EXCLUDED.daily_count,
  raw_ref = EXCLUDED.raw_ref, updated_at = EXCLUDED.updated_at,
  pipeline_version = EXCLUDED.pipeline_version
WHERE news_item.daily_count < EXCLUDED.daily_count
RETURNING (xmax = 0) AS inserted
"""


def write_items(conn, source: Source, items: list[dict[str, Any]], raw_ref: str,
                now: datetime) -> int:
    """Rows this read added. A daily entry that grew is an update, not an addition."""
    added = 0
    version = settings().pipeline_version
    for it in items:
        daily = it.get("daily_count") is not None
        row = {
            "id": (stable_id("news", source.key, it["daily_day"]) if daily
                   else stable_id("news", it["url"])),
            "source_key": source.key, "url": it["url"], "title": it["title"],
            "published_at": it["published_at"], "summary": it["summary"], "author": it["author"],
            "categories": it["categories"], "llm_keywords": it["llm_keywords"],
            "daily_count": it.get("daily_count"), "raw_ref": raw_ref, "now": now,
            "pipeline_version": version,
        }
        got = conn.execute(_UPSERT_DAILY if daily else _INSERT, row).fetchone()
        if got is not None and (not daily or got[0]):
            added += 1
    return added


def record_fetch(conn, run_id: str, source: Source, at: datetime, outcome: str, *,
                 status: int | None = None, detail: str | None = None,
                 seen: int | None = None, new: int | None = None) -> None:
    conn.execute(
        "INSERT INTO news_fetch (run_id, source_key, fetched_at, outcome, http_status, detail, "
        "items_seen, items_new) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (run_id, source.key, at, outcome, status, detail, seen, new),
    )


# ── one run ──────────────────────────────────────────────────────────────────

def _window_full(url: str, seen: int) -> bool:
    """Did the read return as many items as it asked for (`per_page`)? Then older
    items exist that this read did not see."""
    m = re.search(r"[?&]per_page=(\d+)", url)
    return bool(m) and seen >= int(m.group(1))


def _get(client, gate, url: str, headers: dict[str, str]):
    """GET with every redirect hop asked of robots.txt. Returns (response, refusal)."""
    for _ in range(MAX_REDIRECTS + 1):
        decision = gate.allows(url)
        if not decision.allowed:
            return None, f"robots.txt: {decision.reason} ({url})"
        response = client.get(url, headers=headers)
        if not response.is_redirect:
            return response, None
        url = str(response.next_request.url)
    raise RuntimeError(f"more than {MAX_REDIRECTS} redirects")


def harvest(conn, client, *, gate=None, store=None, contract: Contract | None = None,
            only: set[str] | None = None, clock=lambda: datetime.now(UTC)) -> dict[str, Any]:
    """Read every source once (or only those named), store and record each read."""
    from collect.adapters.blog.robots import RobotsGate
    from collect.rawstore import RawStore

    contract = contract or load_contract()
    agent = settings().user_agent
    gate = gate or RobotsGate(client, user_agent=agent)
    store = store or RawStore()
    run_id = f"news_{uuid.uuid4().hex[:12]}"
    token = settings().github_token
    counts: dict[str, Any] = {"run_id": run_id, "sources": 0, "ok": 0, "refused": 0,
                              "failed": 0, "items_new": 0, "by_source": {}}
    last_at: dict[str, float] = {}
    for source in contract.sources:
        if only and source.key not in only:
            continue
        counts["sources"] += 1
        host = source.url.split("/")[2]
        wait = gate.min_interval(source.url) - (time.monotonic() - last_at.get(host, -1e9))
        if wait > 0:
            time.sleep(wait)
        headers = {}
        if source.kind == "github_releases":
            headers["Accept"] = "application/vnd.github+json"
            if token:
                headers["Authorization"] = f"Bearer {token}"
        at = clock()
        try:
            response, refusal = _get(client, gate, source.url, headers)
        except Exception as exc:  # noqa: BLE001 - one source failing never stops the others
            record_fetch(conn, run_id, source, at, "error",
                         detail=f"{type(exc).__name__}: {exc}"[:300])
            counts["failed"] += 1
            counts["by_source"][source.key] = "error"
            continue
        last_at[host] = time.monotonic()
        if refusal:
            record_fetch(conn, run_id, source, at, "robots_refused", detail=refusal[:300])
            counts["refused"] += 1
            counts["by_source"][source.key] = "robots refused"
            continue
        if response.status_code != 200:
            record_fetch(conn, run_id, source, at, "http_error", status=response.status_code,
                         detail=f"HTTP {response.status_code}")
            counts["failed"] += 1
            counts["by_source"][source.key] = f"HTTP {response.status_code}"
            continue
        raw_ref = store.put(response.content).ref
        try:
            items = (parse_feed(response.content, contract, feed_url=str(response.url),
                                content_type=response.headers.get("content-type"))
                     if source.kind == "feed"
                     else parse_github_releases(response.json(), contract))
        except ValueError as exc:
            record_fetch(conn, run_id, source, at, "error", status=200,
                         detail=f"unreadable response: {exc}"[:300])
            counts["failed"] += 1
            counts["by_source"][source.key] = "unreadable"
            continue
        seen = len(items)
        if source.daily:
            items = fold_daily(items, source, window_full=_window_full(source.url, seen))
        new = write_items(conn, source, items, raw_ref, at)
        record_fetch(conn, run_id, source, at, "ok", status=200, seen=seen, new=new)
        counts["ok"] += 1
        counts["items_new"] += new
        counts["by_source"][source.key] = f"{seen} seen, {new} new"
    return counts
