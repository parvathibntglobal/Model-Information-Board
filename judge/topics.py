"""The blog's topics: what the field is writing about, and what to write next
(2026-10-16). Code only - no model decides anything here.

    config()          blog_topics.yaml, validated; no defaults (rule 12)
    match(text)       the topic keys whose terms appear in a text, on whole words
    overview(conn)    per topic: items in the window, this week against the weeks
                      before (a count, never a score), and the newest items
    emerging(conn)    phrases recurring in recent titles that NO topic covers -
                      proposals for a person to adopt as topics (rule 10)
    sources(conn, k)  the items a post on topic k may be written from (posts:)
    plan(conn)        what each active topic can become: a combined article when
                      several sources share it, an explainer with a quiz when one does

Reads `topic_item` (scripts/harvest_topics.py writes it). Nothing here touches the
evidence pipeline or the board.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "blog_topics.yaml"

_STOP = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "into",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "our",
        "the",
        "their",
        "this",
        "to",
        "towards",
        "toward",
        "via",
        "vs",
        "we",
        "what",
        "when",
        "which",
        "with",
        "without",
        "your",
        "using",
        "based",
        "new",
        "can",
        "do",
        "does",
        "large",
        "language",
        "model",
        "models",
        "llm",
        "llms",
        "ai",
        "learning",
        "neural",
        "network",
        "networks",
        "data",
    ]
)
_WORD = re.compile(r"[a-z0-9][a-z0-9-]*")
# A possessive ("Netflix's") is not a word of the phrase.
_POSSESSIVE = re.compile(r"['\u2019]s(?![a-z0-9])")


@lru_cache(maxsize=1)
def config() -> dict[str, Any]:
    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    for key in ("arxiv", "window_days", "synthesis_min_items", "emerging", "posts", "topics"):
        if key not in raw:
            raise ValueError(f"blog_topics.yaml: `{key}` is missing")
    posts = raw["posts"] or {}
    if not isinstance(posts.get("arxiv_as_source"), bool):
        raise ValueError("blog_topics.yaml: posts.arxiv_as_source must be true or false")
    for key in ("source_window_days", "max_sources"):
        if not isinstance(posts.get(key), int):
            raise ValueError(f"blog_topics.yaml: posts.{key} must be a whole number")
    seen = set()
    for t in raw["topics"]:
        if not all(t.get(k) for k in ("key", "name", "short", "search", "terms")):
            raise ValueError(
                f"blog_topics.yaml: every topic needs key, name, short, search and terms: {t!r}"
            )
        if t["key"] in seen:
            raise ValueError(f"blog_topics.yaml: topic {t['key']!r} is listed twice")
        seen.add(t["key"])
    return raw


@lru_cache(maxsize=1)
def _patterns() -> list[tuple[str, re.Pattern]]:
    out = []
    for t in config()["topics"]:
        alts = "|".join(re.escape(str(term)) for term in t["terms"])
        out.append((t["key"], re.compile(rf"(?<![\w-])(?:{alts})(?![\w-])", re.IGNORECASE)))
    return out


def match(title: str, summary: str | None = None) -> list[str]:
    """Topic keys an item is ABOUT: a term in its title, or a term at least
    twice in its summary. A single passing mention in an abstract is not what a
    paper is about - measured 2026-10-16 on the first harvest, "benchmark" in
    nearly every abstract put 45 of 148 recent items under one topic."""
    out = []
    for key, rx in _patterns():
        if rx.search(title or "") or len(rx.findall(summary or "")) >= 2:
            out.append(key)
    return out


def _names() -> dict[str, str]:
    return {t["key"]: t["name"] for t in config()["topics"]}


def overview(conn, today: datetime | None = None) -> dict[str, Any]:
    """Per topic: items in the window, this week's count beside the weekly
    average of the three weeks before (both shown; no ratio is computed), and
    the newest items."""
    now = today or datetime.now(UTC)
    window = config()["window_days"]
    since = now - timedelta(days=window)
    total, newest_harvest, first_harvest = conn.execute(
        "SELECT count(*), max(harvested_at), min(harvested_at) FROM topic_item"
    ).fetchone()
    rows = conn.execute(
        "SELECT t.topic, count(*) FILTER (WHERE i.published_at >= %(week)s), "
        "       count(*) FILTER (WHERE i.published_at >= %(month)s AND i.published_at < %(week)s), "
        "       count(*) FILTER (WHERE i.published_at >= %(since)s) "
        "FROM topic_item i, unnest(i.topics) AS t(topic) GROUP BY 1",
        {"week": now - timedelta(days=7), "month": now - timedelta(days=28), "since": since},
    ).fetchall()
    names = _names()
    topics = []
    for key, this_week, prior_three, in_window in rows:
        if key not in names:
            continue
        items = [
            {
                "title": t,
                "url": u,
                "source": s,
                "kind": k,
                "published": p.date().isoformat() if p else None,
            }
            for t, u, s, k, p in conn.execute(
                "SELECT title, url, source, kind, published_at FROM topic_item "
                "WHERE %(k)s = ANY(topics) AND published_at >= %(since)s "
                "ORDER BY published_at DESC LIMIT 6",
                {"k": key, "since": since},
            ).fetchall()
        ]
        topics.append(
            {
                "key": key,
                "name": names[key],
                "in_window": in_window,
                "this_week": this_week,
                "prior_three_weeks": prior_three,
                "items": items,
            }
        )
    topics.sort(key=lambda t: (-t["in_window"], t["name"]))
    unmatched = conn.execute(
        "SELECT count(*) FROM topic_item WHERE topics = '{}' AND published_at >= %s", (since,)
    ).fetchone()[0]
    return {
        "window_days": window,
        "items": total,
        "last_harvest": newest_harvest.isoformat() if newest_harvest else None,
        # RULE 7: WHAT A WEEKLY COUNT COVERS. The first harvest takes only the
        # newest papers, so the weeks before it are under-collected and a
        # "this week against the weeks before" comparison is meaningful only
        # from four weeks after collection began.
        "collecting_since": first_harvest.date().isoformat() if first_harvest else None,
        "trend_meaningful_from": (first_harvest + timedelta(days=28)).date().isoformat()
        if first_harvest
        else None,
        "topics": topics,
        "unmatched_in_window": unmatched,
        "silent": sorted(set(names) - {t["key"] for t in topics if t["in_window"]}),
    }


def _ngrams(title: str) -> set[str]:
    words = _WORD.findall(_POSSESSIVE.sub("", (title or "").lower()))
    grams = set()
    for n in (2, 3):
        for i in range(len(words) - n + 1):
            g = words[i : i + n]
            if g[0] in _STOP or g[-1] in _STOP or any(w.isdigit() for w in g):
                continue
            grams.add(" ".join(g))
    return grams


def emerging(conn, today: datetime | None = None) -> list[dict[str, Any]]:
    """Phrases recurring in recent titles that no topic's terms cover - a list
    for a person to read, never adopted by code."""
    cfg = config()["emerging"]
    now = today or datetime.now(UTC)
    titles = [
        r[0]
        for r in conn.execute(
            "SELECT title FROM topic_item WHERE published_at >= %s",
            (now - timedelta(days=cfg["window_days"]),),
        ).fetchall()
    ]
    counts: Counter = Counter()
    for title in titles:
        counts.update(_ngrams(title))
    covered = [rx for _key, rx in _patterns()]
    out = []
    # DETERMINISTIC, LONGEST FIRST: ties were in set order (string hashing
    # varies per process), and the shorter-inside-longer rule below then kept
    # whichever came first - so the list changed between runs.
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0].split()), kv[0]))
    for gram, n in ranked:
        if n < cfg["min_items"]:
            break
        if any(rx.search(gram) for rx in covered):
            continue
        # A shorter phrase inside a longer one counted the same is the same signal.
        if any(gram in o["phrase"] and o["titles"] == n for o in out):
            continue
        out.append({"phrase": gram, "titles": n})
        if len(out) == cfg["max_terms"]:
            break
    return out


ARXIV_ONLY = "every item is on arXiv, which is not a post source while its ruling is internal-only"


def topic(key: str) -> dict[str, Any]:
    for t in config()["topics"]:
        if t["key"] == key:
            return t
    raise KeyError(f"blog_topics.yaml has no topic {key!r}")


def sources(conn, key: str, today: datetime | None = None) -> list[dict[str, Any]]:
    """The items a post on `key` may be written from, newest first: in the
    source window, and not from arXiv while `posts.arxiv_as_source` is false.
    Not capped here - the pack takes `max_sources` of those whose text it can
    read."""
    cfg = config()["posts"]
    now = today or datetime.now(UTC)
    rows = conn.execute(
        "SELECT id, source, kind, title, url, published_at, summary FROM topic_item "
        "WHERE %(k)s = ANY(topics) AND published_at >= %(since)s "
        "  AND (%(arxiv)s OR source <> 'arxiv') "
        "ORDER BY published_at DESC, id",
        {
            "k": key,
            "since": now - timedelta(days=cfg["source_window_days"]),
            "arxiv": cfg["arxiv_as_source"],
        },
    ).fetchall()
    cols = ("id", "source", "kind", "title", "url", "published_at", "summary")
    return [dict(zip(cols, r, strict=True)) for r in rows]


def shape_for(n_sources: int) -> str | None:
    """Several sources make a COMBINED article; one makes an EXPLAINER WITH A
    QUIZ; none makes nothing."""
    if n_sources >= config()["synthesis_min_items"]:
        return "combined article"
    return "explainer with a quiz" if n_sources == 1 else None


def plan(conn, today: datetime | None = None) -> list[dict[str, Any]]:
    """What each topic active in the window can become, from the sources a post
    may use. A topic active only on arXiv says so (rule 4) rather than vanishing:
    its trend is real, and the reason it cannot be written yet is the ruling."""
    ov = overview(conn, today)
    max_sources = config()["posts"]["max_sources"]
    arxiv_ok = config()["posts"]["arxiv_as_source"]
    out = []
    for t in ov["topics"]:
        if t["in_window"] <= 0:
            continue
        n = min(len(sources(conn, t["key"], today)), max_sources)
        shape = shape_for(n)
        out.append(
            {
                "key": t["key"],
                "name": t["name"],
                "items": t["in_window"],
                "sources": n,
                "shape": shape,
                "why_not": None
                if shape
                else (ARXIV_ONLY if not arxiv_ok else "no item in the source window"),
            }
        )
    return out
