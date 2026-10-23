"""The feed's read path: the reports behind a count, newest first.

THE POPULATION IS THE COUNT'S, OR THE FEED IS NOT EVIDENCE FOR IT. A reader
arrives from a number - "20 voices" on a model card, "3 negative" on Compare,
a bar on Most reported - and the list must be the reports that number counted,
under the same rules:

    model-wide          every non-declined `board_entry` about the model, either
                        id shape, every source: the population of the model
                        card's voices (judge/catalog.py `_engineer_voices`).
    section + slug      the same, narrowed to one job, capability or metric by
                        `spelling_key` on `COALESCE(ruling_target, slug)`, with
                        `metric_withholding` applied - exactly what
                        `board_sections` counts for that page.
    polarity            a REPORT is positive if any of its entries is, and can
                        be positive and negative at once; neutral means
                        neither. The board's split (judge/reports.py), in
                        reports, so "3 negative" opens 3 reports.

Counts are returned beside the items in BOTH units the site uses - entries
(Compare's head-to-head) and reports (everywhere else) - so a reader who came
from either number finds it on the page.

WHAT REACHES THE PAGE (contract/publication.yaml `evidence_feed`): the
paraphrase, the extractor's tags, the date, and the source - an official embed
for a source in `embed_only`, a link otherwise. NEVER a quote, from any source.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from judge import publication
from judge.store.board_entries import metric_withholding, spelling_key

#: `document.source` -> the name a reader knows. An unknown source shows its
#: stored value rather than a guess.
PLATFORMS = {
    "devto": "dev.to",
    "hackernews": "Hacker News",
    "github": "GitHub",
    "blog": "Blog",
    "huggingface": "Hugging Face",
    "arxiv": "arXiv",
    "reddit": "Reddit",
    "x": "X",
}

SECTIONS = ("best_for", "capability", "metric")
POLARITIES = ("positive", "negative", "neutral")


class UnknownModel(LookupError):
    """No registry row carries this id in either shape."""


def resolve_model(conn, model_id: str) -> dict:
    row = conn.execute(
        "SELECT id, canonical_id, coalesce(display_name, canonical_id, id) "
        "FROM model_version WHERE id = %s OR canonical_id = %s "
        "ORDER BY (canonical_id = %s) DESC LIMIT 1",
        (model_id, model_id, model_id),
    ).fetchone()
    if row is None:
        raise UnknownModel(model_id)
    return {"key": row[0], "canonical": row[1], "label": row[2]}


# STORED FOR EVERY MODEL, SHOWN FOR THE SEATED ONES (2026-10-23). Paraphrases
# are written for every model with reports - 130 on the local copy that day, 26
# of them seated - but the public feed shows only the models the models page
# lists. "Seated" is that page's own rule (judge/tracked.py `all_tracked`), read
# here rather than copied, so seating a model in contract/tracked_models.yaml
# opens its feed with nothing else to change.
#
# ⚠ EITHER ID SHAPE. A tracked entry names a row by `id` OR `canonical_id`:
#   Fable 5.1 is `anthropic/claude-fable-5-1` in the file and
#   `anthropic/claude-fable-5.1` as its canonical id. Comparing one shape found
#   it unseated with 194 paraphrased reports.


class NotSeated(LookupError):
    """The model has a registry row but is not on the models page."""


def _seated_names(conn) -> list[str]:
    from judge.tracked import all_tracked

    return [t.registry for t in all_tracked(conn) if t.registry]


def seated_keys(conn) -> set[str]:
    """Every id, in both shapes, of a model the models page lists."""
    names = _seated_names(conn)
    rows = conn.execute(
        "SELECT id, canonical_id FROM model_version WHERE id = ANY(%s) OR canonical_id = ANY(%s)",
        (names, names),
    ).fetchall()
    return {key for row in rows for key in row if key}


def require_seated(conn, model: dict) -> None:
    if not {model["key"], model["canonical"]} & seated_keys(conn):
        raise NotSeated(model["label"])


def model_entries(conn, model: dict) -> list[dict]:
    """Every non-declined entry about the model, with its document."""
    rows = conn.execute(
        "SELECT be.id, be.section, COALESCE(be.ruling_target, be.slug), be.name, "
        "       be.unit, be.value_verbatim, be.quote, be.polarity, be.document_id, "
        "       d.source, d.url, d.author_id, d.created_at, be.parent_proposed "
        "FROM board_entry be LEFT JOIN document d ON d.id = be.document_id "
        "WHERE (be.model_version_id = %s OR be.model_version_id = %s) "
        "  AND be.ruling IS DISTINCT FROM 'declined'",
        (model["key"], model["canonical"]),
    ).fetchall()
    return [
        {
            "id": r[0],
            "section": r[1],
            "slug": r[2],
            "name": r[3],
            "unit": r[4],
            "value_verbatim": r[5],
            "quote": r[6],
            "polarity": r[7],
            "document_id": r[8],
            "source": r[9],
            "url": r[10],
            "author_id": r[11],
            "posted_at": r[12],
            "parent_proposed": r[13],
        }
        for r in rows
    ]


def excerpts_digest(entries: list[dict]) -> str:
    """What a paraphrase was written from, as one hash. Order-free: the same
    excerpts in another order are the same report."""
    lines = sorted(
        f"{e['section']}\x1f{e['slug']}\x1f{e['polarity']}\x1f{e['quote']}" for e in entries
    )
    return hashlib.sha256("\x1e".join(lines).encode("utf-8")).hexdigest()


def by_report(entries: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for e in entries:
        out.setdefault(e["document_id"], []).append(e)
    return out


def report_polarity(entries: list[dict]) -> str:
    """positive | negative | both | neutral, counted the board's way."""
    pols = {e["polarity"] for e in entries}
    pos, neg = "positive" in pols, "negative" in pols
    return "both" if pos and neg else "positive" if pos else "negative" if neg else "neutral"


def _narrow(entries: list[dict], section: str | None, slug: str | None) -> list[dict]:
    if not section:
        return entries
    key = spelling_key(slug) if slug else None
    out = []
    for e in entries:
        if e["section"] != section or (key is not None and spelling_key(e["slug"]) != key):
            continue
        # THE SECTION PAGE'S RULE, applied only where a section page is the
        # count the reader came from. The model card counts every entry.
        if metric_withholding(
            {
                "section": e["section"],
                "slug": e["slug"],
                "unit": e["unit"],
                "value_verbatim": e["value_verbatim"],
                "quote": e["quote"],
            }
        ):
            continue
        out.append(e)
    return out


def _in_category(entries: list[dict], category: str) -> tuple[list[dict], str]:
    """Entries filed under one Compare category, with the polarity that
    category counts them with, and its name. The SAME functions the score
    uses (judge/category_scores.py `filer`, `counted_polarity`)."""
    from judge.category_scores import counted_polarity, filer
    from judge.config import category_scores, slug_parents

    cfg = category_scores()
    names = {c["key"]: c["name"] for c in cfg["categories"]}
    if category not in names:
        raise ValueError(f"category must be one of {', '.join(names)}")
    file = filer(cfg, slug_parents())
    out = [
        {**e, "polarity": counted_polarity(e["section"], e["polarity"], cfg)}
        for e in entries
        if file(e["section"], e["slug"], e.get("parent_proposed")) == category
    ]
    return out, names[category]


def _matches(polarity: str | None, report_pol: str) -> bool:
    if not polarity:
        return True
    if polarity == "neutral":
        return report_pol == "neutral"
    return report_pol in (polarity, "both")


def _counts(reports: dict[str, list[dict]]) -> dict[str, Any]:
    entries = [e for es in reports.values() for e in es]
    split = {"positive": 0, "negative": 0, "neutral": 0, "both": 0}
    for es in reports.values():
        pol = report_polarity(es)
        if pol == "both":
            split["both"] += 1
            split["positive"] += 1
            split["negative"] += 1
        else:
            split[pol] += 1
    return {
        "reports": len(reports),
        "voices": len({e["author_id"] for e in entries if e["author_id"]}),
        "entries": len(entries),
        "entries_by_polarity": {
            p: sum(1 for e in entries if e["polarity"] == p) for p in POLARITIES
        },
        "reports_by_polarity": split,
    }


def cite_source(entry: dict, embed: dict | None) -> dict:
    """How an item cites where it came from. Never the quote."""
    source = entry["source"]
    platform = PLATFORMS.get(source, source or "source not recorded")
    if source in publication.evidence_feed_terms()["embed_only"]:
        if embed is None:
            return {"kind": "pending", "platform": platform}
        if embed["outcome"] != "embeddable":
            return {"kind": "unavailable", "platform": platform, "reason": embed["outcome"]}
        return {
            "kind": "embed",
            "platform": source,
            "url": embed["url"],
            "title": embed["title"],
            "author": embed["author"],
            "community": embed["community"],
        }
    url = (
        entry["url"]
        if isinstance(entry["url"], str) and entry["url"].startswith("https://")
        else None
    )
    out = {"kind": "link" if url else "unavailable", "platform": platform}
    if url:
        out["url"] = url
    else:
        out["reason"] = "no_link"
    if source == "arxiv":
        out["acknowledgement"] = publication.arxiv_acknowledgement()
    return out


def _iso(at: datetime | None) -> str | None:
    return at.isoformat() if at else None


def feed(
    conn,
    model_id: str,
    *,
    section: str | None = None,
    slug: str | None = None,
    category: str | None = None,
    polarity: str | None = None,
    page: int = 1,
    per_page: int,
    prompt_version: str,
) -> dict:
    """One page of the feed. Raises `UnknownModel` and `ValueError` on a bad filter.

    `category` is one of Compare's category scores (contract/category_scores.yaml):
    the reports filed under it by `category_scores.filer`, polarity counted
    as that score counts it - a metric entry is neutral there - so "Coding:
    3 negative" on Compare opens exactly those 3 reports.
    """
    if category is not None and (section or slug):
        raise ValueError("a category is its own filter; give it without a section or slug")
    if section is not None and section not in SECTIONS:
        raise ValueError(f"section must be one of {', '.join(SECTIONS)}")
    if slug and not section:
        raise ValueError("a slug needs its section")
    if polarity is not None and polarity not in POLARITIES:
        raise ValueError(f"polarity must be one of {', '.join(POLARITIES)}")
    if page < 1:
        raise ValueError("page starts at 1")

    terms = publication.evidence_feed_terms()
    model = resolve_model(conn, model_id)
    require_seated(conn, model)
    category_name = None
    if category is not None:
        narrowed, category_name = _in_category(model_entries(conn, model), category)
    else:
        narrowed = _narrow(model_entries(conn, model), section, slug)
    reports = by_report(narrowed)
    counts = _counts(reports)

    matching = {d: es for d, es in reports.items() if _matches(polarity, report_polarity(es))}
    # NEWEST POSTED FIRST. A report with no recorded date sorts last and says
    # so on the page rather than taking a date it does not have (rule 6).
    ordered = sorted(
        matching.items(),
        key=lambda kv: (
            kv[1][0]["posted_at"] is None,
            -(kv[1][0]["posted_at"].timestamp() if kv[1][0]["posted_at"] else 0),
            kv[0],
        ),
    )
    start = (page - 1) * per_page
    shown = ordered[start : start + per_page]
    doc_ids = [d for d, _ in shown]

    # A PARAPHRASE IS CURRENT ONLY FOR THE EXCERPTS IT WAS WRITTEN FROM. It
    # describes the whole report (every entry of the document about this
    # model), not the narrowed slice, so its digest is over the full set.
    full = by_report(model_entries(conn, model)) if (section or category) else reports
    paraphrases = {}
    embeds = {}
    if doc_ids:
        paraphrases = {
            d: (text, digest, at)
            for d, text, digest, at in conn.execute(
                "SELECT document_id, text, excerpts_digest, generated_at FROM feed_paraphrase "
                "WHERE model_version_id = %s AND prompt_version = %s AND document_id = ANY(%s)",
                (model["key"], prompt_version, doc_ids),
            ).fetchall()
        }
        embeds = {
            d: {"outcome": o, "url": u, "title": t, "author": a, "community": c}
            for d, o, u, t, a, c in conn.execute(
                "SELECT document_id, outcome, url, title, author, community FROM feed_embed "
                "WHERE document_id = ANY(%s)",
                (doc_ids,),
            ).fetchall()
        }

    items = []
    for doc_id, es in shown:
        first = es[0]
        # LISTED EVEN WHEN NOT SHOWN (rule 4). If the terms ever stop the feed
        # drawing on a withheld source, its reports stay in the list - they are
        # in the count - and say why they carry no text, never just vanish.
        hidden = (
            publication.withheld_publicly(first["source"]) and not terms["may_draw_on_withheld"]
        )
        found = None if hidden else paraphrases.get(doc_id)
        current = found is not None and found[1] == excerpts_digest(full.get(doc_id, es))
        # ONE TAG PER NAME AS THE READER SEES IT. Two slugs, or two sections,
        # filed under one heading read as the same word twice on the item
        # (seen on the first live render, 2026-10-21). The first keeps its link.
        tags = {}
        for e in es:
            name = e["name"] or e["slug"]
            tags.setdefault(
                name.strip().lower(),
                {"section": e["section"], "slug": e["slug"], "name": name, "polarities": set()},
            )["polarities"].add(e["polarity"])
        items.append(
            {
                "id": doc_id,
                "posted_at": _iso(first["posted_at"]),
                "polarity": report_polarity(es),
                "tags": [{**t, "polarities": sorted(t["polarities"])} for t in tags.values()],
                # None when not written yet, or written from different excerpts:
                # the page says "not paraphrased yet" and the source is still there.
                "paraphrase": found[0] if current else None,
                "source": (
                    {"kind": "withheld"} if hidden else cite_source(first, embeds.get(doc_id))
                ),
            }
        )

    paraphrased = 0
    if reports:
        current_digests = {d: excerpts_digest(full.get(d, es)) for d, es in reports.items()}
        stored = conn.execute(
            "SELECT document_id, excerpts_digest FROM feed_paraphrase "
            "WHERE model_version_id = %s AND prompt_version = %s AND document_id = ANY(%s)",
            (model["key"], prompt_version, list(reports)),
        ).fetchall()
        paraphrased = sum(1 for d, digest in stored if current_digests.get(d) == digest)

    name = (category_name if category else
            next((e["name"] for e in narrowed if e["name"]), slug) if section else None)
    return {
        "model": model,
        "filter": {"section": section, "slug": slug, "category": category, "name": name,
                   "polarity": polarity},
        "counts": counts,
        # RULE 4: how many of these reports have no current paraphrase, so a
        # thin page reads as "not written yet", never as "not reported".
        "paraphrased": paraphrased,
        "matching": len(matching),
        "page": {
            "page": page,
            "per_page": per_page,
            "pages": max(1, -(-len(matching) // per_page)),
        },
        "items": items,
    }
