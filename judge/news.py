"""The News page (/news, signed in): the headlines collect/news/harvest.py stored.

2026-10-28. Each story carries its code-written summary and the feed's own
picture when there is one; the page draws a card for the rest.

Read-only. Every source in contract/news_sources.yaml is listed with what its
last read did - ok, refused by robots.txt, or failed - so a quiet source and a
broken one never look the same (rule 4). Items come newest first by the
source's own date; an item without one is placed by when we first saw it, and
says so (rule 6).

AN UNDATED ITEM NEVER SORTS AS FRESH. Ordering by "first seen" would put every
undated item at the top on the day a source is first read - Google
Developers' 20 posts, which carry no date at all, led the list on 2026-10-28
and may be months old. So dated items come first, newest first, and undated
ones follow, each saying when we first saw it (rule 12: a stand-in date that
looks right is the wrong kind of fallback).

NOTHING IS FILTERED HERE. The LLM badge (`llm_keywords`) travels on every item
and the page lets a reader filter on it; the server never does, because nobody
has measured what the keyword list misses (rule 8).

The judge does not import collect/, so the contract is read here directly.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

CONTRACT = Path(__file__).resolve().parents[1] / "contract" / "news_sources.yaml"


class NewsRequestError(ValueError):
    """A request the page should not have sent (a window outside the contract's)."""


def _contract() -> dict[str, Any]:
    raw = yaml.safe_load(CONTRACT.read_text(encoding="utf-8")) or {}
    page = raw.get("page") or {}
    for key in ("default_days", "max_days", "max_items"):
        if not isinstance(page.get(key), int) or page[key] <= 0:
            raise ValueError(f"contract/news_sources.yaml: page.{key} must be a positive integer")
    generic = (raw.get("link_preview") or {}).get("generic_min_stories")
    if not isinstance(generic, int) or generic < 2:
        raise ValueError("contract/news_sources.yaml: link_preview.generic_min_stories must be "
                         "an integer of 2 or more")
    return raw


# A SOURCE'S ONE-PICTURE-FOR-EVERYTHING IS NOT A STORY'S PICTURE. AIWire's
# preview tag is its site banner on all 47 stories, TLDR AI's its logo
# (2026-10-28): shown, a grid of identical banners says nothing about any
# story. A picture used by `generic_min_stories` or more stories of one source
# is withheld here and the page draws a card, saying why.
_GENERIC_SQL = """
SELECT source_key, image_url FROM news_item WHERE image_url IS NOT NULL
GROUP BY source_key, image_url HAVING count(*) >= %s
"""


def _generic_pictures(conn, contract: dict[str, Any]) -> set[tuple[str, str]]:
    """{(source, picture)}: PER SOURCE (#583 review). A picture one source uses on
    every story is generic for that source only; another source's story that
    happens to use it once keeps it."""
    n = contract["link_preview"]["generic_min_stories"]
    return {(k, u) for k, u in conn.execute(_GENERIC_SQL, (n,)).fetchall()}


ITEMS_SQL = """
SELECT id, source_key, title, url, published_at, first_seen_at, summary, author,
       categories, llm_keywords, daily_count, image_url, image_source, slug
FROM news_item
WHERE coalesce(published_at, first_seen_at) >= %s
ORDER BY (published_at IS NULL), coalesce(published_at, first_seen_at) DESC, id
LIMIT %s
"""

# Each source's newest read, whatever it did.
LAST_READ_SQL = """
SELECT DISTINCT ON (source_key) source_key, fetched_at, outcome, http_status, detail,
       items_seen, items_new
FROM news_fetch
ORDER BY source_key, fetched_at DESC
"""

COUNTS_SQL = """
SELECT source_key,
       count(*),
       count(*) FILTER (WHERE coalesce(published_at, first_seen_at) >= %s),
       count(*) FILTER (WHERE coalesce(published_at, first_seen_at) >= %s AND published_at IS NULL)
FROM news_item GROUP BY source_key
"""


def news_view(conn, *, days: int | None = None, now: datetime | None = None) -> dict[str, Any]:
    contract = _contract()
    page = contract["page"]
    days = page["default_days"] if days is None else days
    if not 1 <= days <= page["max_days"]:
        raise NewsRequestError(f"days must be between 1 and {page['max_days']}")
    now = now or datetime.now(UTC)
    since = now - timedelta(days=days)

    rows = conn.execute(ITEMS_SQL, (since, page["max_items"] + 1)).fetchall()
    capped = len(rows) > page["max_items"]
    generic = _generic_pictures(conn, contract)
    items = [
        {
            "id": r[0], "source_key": r[1], "title": r[2], "url": r[3],
            "published_at": r[4].isoformat() if r[4] else None,
            "first_seen_at": r[5].isoformat(),
            "summary": r[6], "author": r[7], "categories": list(r[8] or []),
            "llm_keywords": list(r[9] or []), "daily_count": r[10],
            # The story's picture; None means the page draws a card - also for
            # a source's generic site image (`image_generic`).
            "image_url": None if (r[1], r[11]) in generic else r[11],
            "image_generic": (r[1], r[11]) in generic,
            # feed | link_preview: where the picture came from (the page says so).
            "image_source": r[12],
            # The story's address on this site, /news/<slug>.
            "slug": r[13],
        }
        for r in rows[: page["max_items"]]
    ]

    last = {r[0]: r for r in conn.execute(LAST_READ_SQL).fetchall()}
    counts = {r[0]: r[1:] for r in conn.execute(COUNTS_SQL, (since, since)).fetchall()}
    sources = []
    for s in contract.get("sources") or []:
        read = last.get(s["key"])
        total, in_window, undated = counts.get(s["key"], (0, 0, 0))
        sources.append({
            "key": s["key"], "label": s["label"], "group": s["group"], "terms": s.get("terms"),
            "one_entry_a_day": bool(s.get("daily")),
            # None: never read on this database - not the same as read and empty.
            "last_read": None if read is None else {
                "at": read[1].isoformat(), "outcome": read[2], "http_status": read[3],
                "detail": read[4], "items_seen": read[5], "items_new": read[6],
            },
            "items_total": total, "items_in_window": in_window, "undated_in_window": undated,
        })
    in_window = sum(s["items_in_window"] for s in sources)
    return {
        "days": days,
        "max_days": page["max_days"],
        "generated_at": now.isoformat(),
        "items": items,
        "sources": sources,
        # Rule 7: what every count on the page is counted over.
        "population": {
            "items_in_window": in_window,
            "items_shown": len(items),
            "capped_at": page["max_items"] if capped else None,
            "items_stored": sum(s["items_total"] for s in sources),
            "sources_listed": len(sources),
        },
    }


# ── one story's page (/news/<id>) ────────────────────────────────────────────

class NewsNotFound(LookupError):
    """No stored story has this id."""


_PROVIDER_PREFIX = re.compile(r"^[^:]{1,40}:\s+")
_FREE_SUFFIX = re.compile(r"\s*\(free\)\s*$", re.I)


def _clean_name(name: str) -> str:
    """'Anthropic: Claude Sonnet 5.5 (free)' -> 'Claude Sonnet 5.5'."""
    return _FREE_SUFFIX.sub("", _PROVIDER_PREFIX.sub("", name or "")).strip()


def model_names(conn, *, min_chars: int) -> tuple[dict[str, str], dict[str, str]]:
    """({lowercase name: canonical id}, {canonical id: display name}).

    From OpenRouter's catalogue, the registry and its aliases. A name is kept
    only when it carries a version digit, is at least `min_chars` long, and
    names ONE model - a `:free` listing counts as the model it is free of. A
    name naming two models is dropped, never guessed between (rule 12)."""
    catalog = {cid: _clean_name(name) for cid, name in
               conn.execute("SELECT canonical_id, name FROM model_catalog").fetchall()}
    registry = conn.execute("SELECT canonical_id, display_name FROM model_version").fetchall()

    def base(cid: str) -> str:
        return cid[:-5] if cid.endswith(":free") and cid[:-5] in catalog else cid

    found: dict[str, set[str]] = {}

    def add(name: str | None, cid: str | None) -> None:
        name = " ".join((name or "").split())
        if cid and len(name) >= min_chars and re.search(r"\d", name):
            found.setdefault(name.lower(), set()).add(base(cid))

    for cid, name in catalog.items():
        add(name, cid)
    for cid, display in registry:
        add(_clean_name(display), cid)
    # SNAPSHOT ALIASES ONLY. A 'version' alias is a shorthand - "GPT 6",
    # "opus 4.5" - and "GPT 6" points at GPT-6 Astra though GPT-6 is a family
    # (Astra, Sol, Luna): a story saying "with GPT-6" was linked to Astra
    # (2026-10-28). A shorthand left unmatched costs a missing link; a wrong one
    # puts a model's counts under a story that is not about it.
    for surface, variants, cid in conn.execute(
            "SELECT a.surface, a.variants, v.canonical_id FROM model_alias a "
            "JOIN model_version v ON v.id = a.model_version_id "
            "WHERE a.specificity = 'snapshot'").fetchall():
        for name in [surface, *(variants or [])]:
            if "/" not in (name or ""):  # an API id is not how a story names a model
                add(name, cid)
    names = {n: next(iter(ids)) for n, ids in found.items() if len(ids) == 1}
    labels = dict(catalog)
    for cid, display in registry:
        labels.setdefault(cid, _clean_name(display))
    return names, labels


def name_pattern(names: dict[str, str]) -> re.Pattern:
    """One pattern for every name: whole names only, longest first. Built once
    per request - rebuilt for each of 600 related stories it took 395 ms of a
    story page (#583 review, timed 2026-10-29 on the shared DB's size)."""
    alternation = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(rf"(?<![\w.\-])({alternation})(?![\w]|[.\-]\w)", re.I)


def mentioned_models(text: str, names: dict[str, str], limit: int,
                     pattern: re.Pattern | None = None) -> list[str]:
    """Canonical ids the text names, in order of first mention.

    Whole names only, longest first: "Claude Opus 5" is never found inside
    "Claude Opus 5.5", nor "GPT-6" inside "GPT-6.1"."""
    if not text or not names:
        return []
    pattern = pattern or name_pattern(names)
    out: list[str] = []
    for m in pattern.finditer(text):
        cid = names.get(" ".join(m.group(1).split()).lower())
        if cid and cid not in out:
            out.append(cid)
            if len(out) >= limit:
                break
    return out


# By its address, or by its id - the first story links used ids, and a link
# somebody kept should still open.
_STORY_SQL = """
SELECT id, source_key, title, url, published_at, first_seen_at, summary, author,
       categories, llm_keywords, daily_count, image_url, image_source, slug, summary_source
FROM news_item WHERE slug = %s OR id = %s
ORDER BY (slug = %s) DESC LIMIT 1
"""

_RECENT_SQL = """
SELECT id, source_key, title, url, published_at, first_seen_at, summary, image_url, slug
FROM news_item
WHERE id <> %s AND coalesce(published_at, first_seen_at) >= %s
ORDER BY coalesce(published_at, first_seen_at) DESC
LIMIT 600
"""


def _card(r, generic: set[tuple[str, str]]) -> dict[str, Any]:
    return {"id": r[0], "source_key": r[1], "title": r[2], "url": r[3],
            "published_at": r[4].isoformat() if r[4] else None,
            "first_seen_at": r[5].isoformat(), "summary": r[6],
            "image_url": None if (r[1], r[7]) in generic else r[7], "slug": r[8]}


def story_view(conn, item_id: str, *, now: datetime | None = None) -> dict[str, Any]:
    """One story: what its source gave, the models it names with their engineer
    counts, and related stories. Nothing here is written by a model."""
    from judge import catalog

    contract = _contract()
    rules = contract.get("story") or {}
    for key in ("min_name_chars", "max_models", "related_days", "related_max"):
        if not isinstance(rules.get(key), int) or rules[key] <= 0:
            raise ValueError(f"contract/news_sources.yaml: story.{key} must be a positive integer")
    row = conn.execute(_STORY_SQL, (item_id, item_id, item_id)).fetchone()
    if row is None:
        raise NewsNotFound(item_id)
    generic = _generic_pictures(conn, contract)
    now = now or datetime.now(UTC)
    sources = {s["key"]: s for s in contract.get("sources") or []}
    source = sources.get(row[1], {})

    names, labels = model_names(conn, min_chars=rules["min_name_chars"])
    pattern = name_pattern(names)
    ids = mentioned_models(f"{row[2]}. {row[6] or ''}", names, rules["max_models"], pattern)
    # THE SITE'S OWN COUNTS, from the function the model pages use: distinct
    # voices and distinct reports over the public view (judge/catalog.py).
    voices, reports = catalog._engineer_voices(conn)
    in_catalog = {cid for (cid,) in conn.execute(
        "SELECT canonical_id FROM model_catalog WHERE canonical_id = ANY(%s)", (ids,)).fetchall()}
    models = [{"id": cid, "name": labels.get(cid, cid), "voices": voices.get(cid, 0),
               "reports": reports.get(cid, 0), "has_page": cid in in_catalog} for cid in ids]

    since = now - timedelta(days=rules["related_days"])
    wanted = set(ids)
    same_model: list[dict[str, Any]] = []
    same_source: list[dict[str, Any]] = []
    for r in conn.execute(_RECENT_SQL, (row[0], since)).fetchall():
        if wanted and len(same_model) < rules["related_max"]:
            shared = set(mentioned_models(f"{r[2]}. {r[6] or ''}", names, rules["max_models"],
                                          pattern))
            if shared & wanted:
                shares = [labels.get(c, c) for c in shared & wanted]
                same_model.append(_card(r, generic) | {"shares": shares})
                continue
        if r[1] == row[1] and len(same_source) < rules["related_max"]:
            same_source.append(_card(r, generic))
    return {
        "story": {
            "id": row[0], "source_key": row[1], "title": row[2], "url": row[3],
            "published_at": row[4].isoformat() if row[4] else None,
            "first_seen_at": row[5].isoformat(), "summary": row[6], "author": row[7],
            "categories": list(row[8] or []), "llm_keywords": list(row[9] or []),
            "daily_count": row[10],
            "image_url": None if (row[1], row[11]) in generic else row[11],
            "image_generic": (row[1], row[11]) in generic, "image_source": row[12],
            "slug": row[13],
            # feed | feed_content | page_description: which of the source's own
            # texts the brief was cut from (the page says so under "In brief").
            "summary_source": row[14],
        },
        "source": {"key": row[1], "label": source.get("label", row[1]),
                   "group": source.get("group"), "terms": source.get("terms")},
        # Every name came from our registry or OpenRouter's catalogue by exact
        # whole-name match (`mentioned_models`); none is inferred.
        "models": models,
        "related": {"same_model": same_model, "same_source": same_source},
        "sources": {k: {"label": v.get("label", k), "group": v.get("group")}
                    for k, v in sources.items()},
    }
