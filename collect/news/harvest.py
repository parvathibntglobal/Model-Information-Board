"""Read the news feeds into `news_item` (contract/news_sources.yaml, 2026-10-28).

One read per source per run, robots.txt asked first for the URL and for every
redirect hop (collect/adapters/blog/robots.py, which matches `*` and `$`). The
response is kept in the raw store before anything is parsed, so a parser fix
reprocesses what was read instead of reading again.

WHAT IS KEPT. What the feed gives: title, link, date, author, categories and
a summary written by code from the feed's own words (`feed_summary`), and the
feed's own picture when it gives one. The article's PAGE is read only by
collect/news/preview.py - its <head>, once, for a story whose feed gives no
picture (CLAUDE.md's second scraping exception); with no picture found there
either, the page draws a card (anooj, 2026-10-28).
A news item is never evidence - nothing here writes a claim, a quote or a
board entry, and no model reads it.

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
    summary_max_words: int
    summary_min_words: int
    keywords: re.Pattern
    sources: tuple[Source, ...]
    #: collect/news/preview.py's settings: enabled, groups, skip, max_per_run,
    #: max_attempts, look_back_days, max_head_bytes (contract `link_preview`).
    link_preview: dict[str, Any]
    #: Sources shown exactly as their feed gives them (contract `as_given`):
    #: the feed's summary whole, never cut or swapped, and no link preview.
    as_given: frozenset[str]


def _positive_int(raw: dict, key: str, problems: list[str]) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        problems.append(f"{key} must be a positive integer")
        return 0
    return value


def load_contract(path: Path = CONTRACT) -> Contract:
    """Every value the harvest uses, refused when absent - no defaults here."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    problems: list[str] = []
    max_words = _positive_int(raw, "summary_max_words", problems)
    min_words = _positive_int(raw, "summary_min_words", problems)
    if max_words and min_words and min_words >= max_words:
        problems.append("summary_min_words must be below summary_max_words")
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
    lp = raw.get("link_preview") or {}
    if not isinstance(lp.get("enabled"), bool):
        problems.append("link_preview.enabled must be true or false")
    if not isinstance(lp.get("groups"), list) or not set(lp.get("groups") or []) <= set(GROUPS):
        problems.append(f"link_preview.groups must be a list drawn from {GROUPS}")
    for key in ("max_per_run", "max_attempts", "look_back_days", "max_head_bytes"):
        _positive_int(lp, key, problems)
    as_given = raw.get("as_given")
    keys = {src.key for src in sources}
    if not isinstance(as_given, dict) or not all(isinstance(v, str) and v
                                                 for v in as_given.values()):
        problems.append("as_given must map each source key to why ({} for none)")
    elif set(as_given) - keys:
        problems.append(f"as_given names unknown sources: {sorted(set(as_given) - keys)}")
    skip = lp.get("skip")
    if not isinstance(skip, dict) or not all(isinstance(v, str) and v for v in skip.values()):
        problems.append("link_preview.skip must map each skipped source key to why ({} for none)")
    if problems:
        raise NewsContractError("contract/news_sources.yaml: " + "; ".join(problems))
    return Contract(max_words, min_words, pattern, tuple(sources),
                    {k: lp[k] for k in ("enabled", "groups", "skip", "max_per_run",
                                        "max_attempts", "look_back_days", "max_head_bytes")},
                    frozenset(as_given))


# ── the summary, written by code ─────────────────────────────────────────────
#
# NO MODEL WRITES A SUMMARY (anooj, 2026-10-28: writing our own is too costly).
# A summary is the source's own words, cut by code: its HTML removed, the
# boilerplate feeds append dropped, then whole sentences up to
# `summary_max_words`. A feed whose summary is missing, shorter than
# `summary_min_words` or only repeats the title falls back to the article
# content the feed itself carries. Nothing is reworded, and a source that gives
# neither has no summary - the page shows none rather than an invented one.

_TAGS = re.compile(r"<[^>]+>")
_BOILERPLATE = [
    re.compile(r"\bThe post\b.{1,300}?\bappeared first on\b.{1,200}?(?:\.|$)", re.I | re.S),
    re.compile(r"\b(?:Continue reading|Read more|Read the full (?:story|post|article))\b.*$",
               re.I | re.S),
    re.compile(r"\s*(?:\[(?:…|\.\.\.)\]|\[&#8230;\])\s*$"),
    # Newsletter and podcast lead-ins that open the article content a feed
    # carries: "Watch the full episode on YouTube As we learned..." (Latent
    # Space, 2026-10-28). Only at the very start, where they stand alone.
    re.compile(r"^\s*(?:(?:Watch|Listen to) the full (?:episode|interview|video)(?: on \w+)?"
               r"|Listen now|Subscribe now|Share this post)\s*[.:!]?\s*", re.I),
]
_SENTENCE = re.compile(r"(?<=[.!?…])[\"'”’)]*\s+(?=[\"'“‘(]?[A-Z0-9])")


def flatten(text: str | None) -> str:
    """HTML removed, entities decoded, whitespace collapsed."""
    if not text:
        return ""
    return " ".join(html.unescape(_TAGS.sub(" ", text)).split())


def summarise(text: str | None, max_words: int) -> str | None:
    """Whole sentences up to `max_words`; a first sentence longer than that is cut
    at a word and ends with an ellipsis. None when nothing is left.

    A LAST SENTENCE THE PUBLISHER CUT OFF IS DROPPED when a complete one comes
    before it: Latent Space's feed ends "...the first profitable quarter in
    Anthropic..." (2026-10-28), and a brief that stops mid-thought reads broken."""
    flat = flatten(text)
    for pattern in _BOILERPLATE:
        flat = pattern.sub("", flat).strip()
    if not flat:
        return None
    kept: list[str] = []
    count = 0
    for sentence in _SENTENCE.split(flat):
        words = sentence.split()
        if count + len(words) > max_words:
            if not kept:
                return " ".join(words[:max_words]).rstrip(",;:-") + "…"
            break
        kept.append(sentence)
        count += len(words)
    if len(kept) > 1 and is_cut(kept[-1]):
        kept.pop()
    return " ".join(kept) or None


_CUT = re.compile(r"(?:…|\.\.\.|\[…\]|\[\.\.\.\])\s*$")
_ENDED = re.compile(r"[.!?][\"'”’)\]]*\s*$")


def is_cut(text: str | None) -> bool:
    """Does this stop mid-thought - an ellipsis, or no closing punctuation?"""
    return bool(text) and (bool(_CUT.search(text)) or not _ENDED.search(text))


def _same_as_title(summary: str | None, title: str) -> bool:
    norm = lambda s: re.sub(r"\W+", " ", s or "").strip().lower()  # noqa: E731
    return bool(summary) and norm(summary) in (norm(title), "")


def choose_brief(candidates: list[tuple[str | None, str]], title: str,
                 contract: Contract) -> tuple[str | None, str | None]:
    """(the brief, where it came from) - the best of the source's own words.

    Every candidate is the publisher's text: the feed's summary, the article
    content the feed carries, or the page's own description tag (preview.py).
    A complete sentence beats one cut off; among those, the fuller one wins.

    BELOW `summary_min_words` IT IS NOT A SUMMARY. Google Research's feed puts a
    topic label where the summary goes ("Generative AI", "Health & Bioscience":
    130 of 1,824 items under 8 words, 2026-10-28). Shown under a headline, a
    label reads as the story's gist, so with nothing longer the item has none
    (rule 12: a stand-in that looks right is worse than none)."""
    usable = [(text, source) for text, source in candidates
              if text and len(text.split()) >= contract.summary_min_words
              and not _same_as_title(text, title)]
    if not usable:
        return None, None
    complete = [c for c in usable if not is_cut(c[0])]
    return max(complete or usable, key=lambda c: len(c[0].split()))


def feed_summary(summary_html: str | None, content_html: str | None, title: str,
                 contract: Contract) -> tuple[str | None, str | None]:
    """The feed's own brief: its summary, or the article content it carries."""
    return choose_brief([(summarise(summary_html, contract.summary_max_words), "feed"),
                         (summarise(content_html, contract.summary_max_words), "feed_content")],
                        title, contract)


_MD_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_MD_NOISE = re.compile(r"[*_`>#]+")
_URL = re.compile(r"https?://\S+")


def release_summary(body: str | None, max_words: int) -> str | None:
    """Release notes are markdown: the first changes listed, joined, up to
    `max_words`. Headings ("What's Changed") and bare links are dropped."""
    if not body:
        return None
    points = []
    for line in body.splitlines():
        line = line.strip()
        if (not line or line.startswith("#")
                or line.lower().startswith(("full changelog", "**full"))):
            continue
        # Release notes mix HTML into the markdown (<details>, <summary>).
        line = _URL.sub("", _MD_LINK.sub(r"\1", _TAGS.sub(" ", line)))
        # The "by @user in #123" credit, before `#` and `@` are stripped as noise.
        line = re.sub(r"\s+by\s+@[\w-]+(?:\s+in\s+\S*)?\s*$", "", line)
        line = _MD_NOISE.sub("", line)
        line = re.sub(r"^[-+]\s*|^\d+\.\s*", "", line).strip(" -:")
        if len(line.split()) >= 2:
            points.append(line.rstrip("."))
    if not points:
        return None
    return summarise("; ".join(points) + ".", max_words)


def matched_keywords(pattern: re.Pattern, *texts: str | None) -> list[str]:
    found = {m.group(1).lower() for t in texts if t for m in pattern.finditer(t)}
    return sorted(found)


def parse_feed(body: bytes, contract: Contract, *, feed_url: str | None = None,
               content_type: str | None = None, as_given: bool = False) -> list[dict[str, Any]]:
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
        if as_given:
            # SHOWN AS THE FEED GIVES IT: the summary whole - HTML removed for
            # display, nothing cut, reworded or swapped (contract `as_given`).
            whole = flatten(e.summary_html) or None
            summary, summary_source = whole, ("feed" if whole else None)
        else:
            summary, summary_source = feed_summary(e.summary_html, e.content_html, title,
                                                   contract)
        items.append({
            "url": e.url, "title": title, "published_at": e.published_at, "summary": summary,
            "summary_source": summary_source,
            "author": e.author, "categories": list(e.categories), "image_url": e.image_url,
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
        summary = release_summary(r.get("body"), contract.summary_max_words)
        items.append({
            "url": r["html_url"], "title": title,
            "published_at": datetime.fromisoformat(when.replace("Z", "+00:00")) if when else None,
            "summary": summary, "summary_source": "feed" if summary else None,
            "author": (r.get("author") or {}).get("login"), "image_url": None,
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
            # NO SUMMARY FOR A DAY OF BUILDS. llama.cpp's notes are a list of the
            # files each build ships ("macOS Apple Silicon (arm64)..."), which as
            # a summary says nothing; the title says how many builds there were.
            "summary": None, "author": None, "categories": [], "image_url": None,
            "llm_keywords": sorted({k for it in group for k in it["llm_keywords"]}),
            "daily_day": day, "daily_count": n,
        })
    return out


# ── writing ──────────────────────────────────────────────────────────────────

_INSERT = """
INSERT INTO news_item (id, slug, source_key, url, title, published_at, summary, summary_source,
                       feed_summary, feed_summary_source, author, categories,
                       image_url, image_source, llm_keywords, daily_count, raw_ref,
                       first_seen_at, updated_at,
                       pipeline_version)
VALUES (%(id)s, %(slug)s, %(source_key)s, %(url)s, %(title)s, %(published_at)s, %(summary)s,
        %(summary_source)s, %(summary)s, %(summary_source)s, %(author)s,
        %(categories)s, %(image_url)s, %(image_source)s, %(llm_keywords)s, %(daily_count)s,
        %(raw_ref)s, %(now)s,
        %(now)s, %(pipeline_version)s)
ON CONFLICT (id) DO NOTHING
RETURNING id
"""

# A daily entry grows with its day and never shrinks: a later read that sees
# fewer of the day's items (the API lists the newest 30) leaves it as it was.
_UPSERT_DAILY = """
INSERT INTO news_item (id, slug, source_key, url, title, published_at, summary, summary_source,
                       feed_summary, feed_summary_source, author, categories,
                       image_url, image_source, llm_keywords, daily_count, raw_ref,
                       first_seen_at, updated_at,
                       pipeline_version)
VALUES (%(id)s, %(slug)s, %(source_key)s, %(url)s, %(title)s, %(published_at)s, %(summary)s,
        %(summary_source)s, %(summary)s, %(summary_source)s, %(author)s,
        %(categories)s, %(image_url)s, %(image_source)s, %(llm_keywords)s, %(daily_count)s,
        %(raw_ref)s, %(now)s,
        %(now)s, %(pipeline_version)s)
ON CONFLICT (id) DO UPDATE SET
  url = EXCLUDED.url, title = EXCLUDED.title, published_at = EXCLUDED.published_at,
  summary = EXCLUDED.summary, llm_keywords = EXCLUDED.llm_keywords,
  daily_count = EXCLUDED.daily_count,
  raw_ref = EXCLUDED.raw_ref, updated_at = EXCLUDED.updated_at,
  pipeline_version = EXCLUDED.pipeline_version
WHERE news_item.daily_count < EXCLUDED.daily_count
RETURNING (xmax = 0) AS inserted
"""


# ── the story's address ──────────────────────────────────────────────────────
#
# A READABLE ADDRESS FROM THE HEADLINE (anooj, 2026-10-28): /news/<slug>, the
# headline's key words - "VCs will make billions on Anthropic's IPO, but Amazon
# is set to make much (much) more" is `vcs-make-billions-anthropics-ipo-amazon`.
# Set once, when the story is first stored, and never changed, so a link stays
# good. Unique: a second story with the same words gets `-2`, `-3`.

_SLUG_STOP = frozenset("""a an the of to in on for and or but with is are was were be been by at as
from into its it this that these those how why what when who will can could would should
your you our we us they their new now has have had just about after more much set get gets
via vs than then so if not no do does did here there""".split())  # noqa: SIM905
_SLUG_PREFIX = re.compile(r"^\s*\[[^\]]{1,30}\]\s*")


def slug_base(title: str, max_words: int = 6) -> str:
    """The headline's key words, lowercase, joined by hyphens."""
    import unicodedata

    text = unicodedata.normalize("NFKD", _SLUG_PREFIX.sub("", title or ""))
    text = text.encode("ascii", "ignore").decode().lower().replace("'", "").replace("’", "")
    words = re.findall(r"[a-z0-9]+", text)
    keep = [w for w in words if w not in _SLUG_STOP] or words
    return "-".join(keep[:max_words])[:60].strip("-") or "story"


def unique_slug(conn, base: str, item_id: str) -> str:
    """`base`, or `base-2`, `base-3`... - the first no other story holds."""
    taken = {r[0] for r in conn.execute(
        "SELECT slug FROM news_item WHERE (slug = %s OR slug LIKE %s) AND id <> %s",
        (base, base + "-%", item_id)).fetchall()}
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def write_items(conn, source: Source, items: list[dict[str, Any]], raw_ref: str,
                now: datetime) -> int:
    """Rows this read added. A daily entry that grew is an update, not an addition."""
    added = 0
    version = settings().pipeline_version
    for it in items:
        daily = it.get("daily_count") is not None
        item_id = (stable_id("news", source.key, it["daily_day"]) if daily
                   else stable_id("news", it["url"]))
        # A daily entry's address names its day, not its growing count.
        base = slug_base(f"{source.label} releases {it['daily_day']}" if daily else it["title"],
                         max_words=8 if daily else 6)
        row = {
            "id": item_id, "slug": unique_slug(conn, base, item_id),
            "source_key": source.key, "url": it["url"], "title": it["title"],
            "published_at": it["published_at"], "summary": it["summary"],
            "summary_source": it.get("summary_source"), "author": it["author"],
            "categories": it["categories"], "image_url": it.get("image_url"),
            "image_source": "feed" if it.get("image_url") else None,
            "llm_keywords": it["llm_keywords"],
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
    """GET with every redirect hop asked of robots.txt. Returns (response, refusal).

    THE CREDENTIAL STAYS ON ITS OWN HOST. Redirects are followed by hand (so
    each hop meets robots.txt), which bypasses httpx's own stripping of
    `Authorization` on a cross-host redirect - so it is dropped here the moment
    a hop leaves the host it was meant for (#583 review)."""
    from urllib.parse import urlsplit

    home = urlsplit(url).hostname
    for _ in range(MAX_REDIRECTS + 1):
        decision = gate.allows(url)
        if not decision.allowed:
            return None, f"robots.txt: {decision.reason} ({url})"
        hop_headers = (headers if urlsplit(url).hostname == home
                       else {k: v for k, v in headers.items() if k.lower() != "authorization"})
        response = client.get(url, headers=hop_headers)
        if not response.is_redirect:
            return response, None
        url = str(response.next_request.url)
    raise RuntimeError(f"more than {MAX_REDIRECTS} redirects")


def harvest(conn, client, *, gate=None, store=None, contract: Contract | None = None,
            only: set[str] | None = None, clock=lambda: datetime.now(UTC)) -> dict[str, Any]:
    """Read every source once (or only those named), store and record each read.

    COMMITTED AS IT GOES (#583 review): after each source, and after each link
    preview. A failure late in a run then costs only what it was doing, and
    "every read is recorded" stays true for every read before it."""
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
            conn.commit()
            counts["failed"] += 1
            counts["by_source"][source.key] = "error"
            continue
        last_at[host] = time.monotonic()
        if refusal:
            record_fetch(conn, run_id, source, at, "robots_refused", detail=refusal[:300])
            conn.commit()
            counts["refused"] += 1
            counts["by_source"][source.key] = "robots refused"
            continue
        if response.status_code != 200:
            record_fetch(conn, run_id, source, at, "http_error", status=response.status_code,
                         detail=f"HTTP {response.status_code}")
            conn.commit()
            counts["failed"] += 1
            counts["by_source"][source.key] = f"HTTP {response.status_code}"
            continue
        raw_ref = store.put(response.content).ref
        try:
            items = (parse_feed(response.content, contract, feed_url=str(response.url),
                                content_type=response.headers.get("content-type"),
                                as_given=source.key in contract.as_given)
                     if source.kind == "feed"
                     else parse_github_releases(response.json(), contract))
        except ValueError as exc:
            record_fetch(conn, run_id, source, at, "error", status=200,
                         detail=f"unreadable response: {exc}"[:300])
            conn.commit()
            counts["failed"] += 1
            counts["by_source"][source.key] = "unreadable"
            continue
        seen = len(items)
        if source.daily:
            items = fold_daily(items, source, window_full=_window_full(source.url, seen))
        new = write_items(conn, source, items, raw_ref, at)
        record_fetch(conn, run_id, source, at, "ok", status=200, seen=seen, new=new)
        conn.commit()
        counts["ok"] += 1
        counts["items_new"] += new
        counts["by_source"][source.key] = f"{seen} seen, {new} new"
    # LINK-PREVIEW PICTURES for the stories whose feed gave none (preview.py:
    # the recorded exception, with its conditions). After every feed, so a
    # source failing above never costs another source its pictures.
    from collect.news.preview import fill_pictures

    groups = set(contract.link_preview["groups"])
    counts["previews"] = fill_pictures(
        conn, client, gate, store, settings_=contract.link_preview, contract=contract,
        source_keys=[s.key for s in contract.sources
                     if s.group in groups and s.key not in contract.link_preview["skip"]
                     and s.key not in contract.as_given and (not only or s.key in only)],
        now=clock())
    return counts
