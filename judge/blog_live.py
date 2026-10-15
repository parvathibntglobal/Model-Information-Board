"""The blog's live pages, rendered from the board in code (2026-10-15).

    claim walls            one model on one job or capability: the reports of it
                           working beside the reports of problems
    where they disagree    every (model, topic) pair with engineers on both sides
    this week in models    listings, new reports, prices and retirements, per week
    the daily quiz         a real quote; which model was it about?
    hover previews         a small card for a model or a topic

NO MODEL CALL, NO REVIEW PER PAGE. These re-render board rows; nothing here
writes a sentence about a model. Every figure is a count (engineers, reports,
days) or a measured price (rule 3).

PUBLIC SOURCES ONLY, WHATEVER VIEW THE DEPLOYMENT RUNS. `contract/publication.yaml`
withholds some sources from public pages, and these pages are built to be
public, so they filter with the contract's list even on an internal deployment.
What that leaves out is COUNTED and said (rule 4), never named.

A VOICE IS A DISTINCT `document.author_id`. A row whose document has no author
still shows its quote and adds no voice.

THE BOARD'S RULINGS APPLY: a declined row is left out and a merged row counts
under the slug it was merged into, as on the board itself.
"""

from __future__ import annotations

import random
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from judge import publication
from judge.config import blog_live_settings, capability_about, job_about

#: Metrics carry no polarity on the board (2026-10-15), so walls, the
#: disagreement list and the quiz read jobs and capabilities only.
SECTIONS = ("best_for", "capability")

#: What a source is called beside its quote. Public sources only; a withheld
#: one never reaches a payload here.
SOURCE_LABEL = {
    "devto": "dev.to",
    "hackernews": "Hacker News",
    "github": "GitHub",
    "blog": "Blog",
    "huggingface": "Hugging Face",
}

_SLUG = "COALESCE(be.ruling_target, be.slug)"
_FROM = (
    "FROM board_entry be JOIN document d ON d.id = be.document_id "
    "JOIN model_version v ON v.id = be.model_version_id OR v.canonical_id = be.model_version_id "
    "WHERE be.ruling IS DISTINCT FROM 'declined' "
    "AND d.source IS NOT NULL AND NOT d.source = ANY(%(hidden)s) "
)
_VOICES = (
    "count(DISTINCT d.author_id) FILTER (WHERE be.polarity = 'positive'), "
    "count(DISTINCT d.author_id) FILTER (WHERE be.polarity = 'negative'), "
    "count(DISTINCT d.author_id) FILTER (WHERE be.polarity = 'neutral') "
)


def _per_token(cid: str, v) -> float | None:
    """A per-token list price, or None. A 0 is a price only on a `:free`
    variant: a speech or image model publishes 0 for a token side it does not
    charge by, and "$0/M" would read as free (rule 6; judge/catalog.py
    `_price_state` reads a 0 the same way)."""
    if v is None:
        return None
    v = float(v)
    return v if v > 0 or cid.endswith(":free") else None


def _hidden() -> list[str]:
    return list(publication.withheld_sources())


def _iso(v: Any) -> str | None:
    return v.isoformat() if v is not None else None


def _in_catalog(conn) -> set[str]:
    return {
        r[0]
        for r in conn.execute(
            "SELECT canonical_id FROM model_catalog "
            "WHERE last_seen_at = (SELECT max(last_seen_at) FROM model_catalog)"
        ).fetchall()
    }


def _model(cid: str, name: str | None, listed: set[str]) -> dict[str, Any]:
    """A model as these pages link it: its catalogue page where the catalogue
    lists it, its registry page otherwise."""
    return {"id": cid, "name": name or cid, "page": "catalog" if cid in listed else "registry"}


def _topic_names(conn, hidden: list[str]) -> dict[tuple[str, str], str]:
    """The commonest name among a topic's public rows."""
    return {
        (s, slug): name
        for s, slug, name in conn.execute(
            f"SELECT be.section, {_SLUG}, mode() WITHIN GROUP (ORDER BY be.name) "
            f"{_FROM} AND be.section = ANY(%(sections)s) GROUP BY 1, 2",
            {"hidden": hidden, "sections": list(SECTIONS)},
        ).fetchall()
    }


def _withheld(conn, where: str, params: dict) -> int:
    """Rows a public page leaves out because of their source, under the same
    filter as the page (rule 4). Unknown provenance counts as withheld."""
    return conn.execute(
        "SELECT count(*) FROM board_entry be JOIN document d ON d.id = be.document_id "
        "JOIN model_version v "
        "  ON v.id = be.model_version_id OR v.canonical_id = be.model_version_id "
        "WHERE be.ruling IS DISTINCT FROM 'declined' "
        "AND (d.source IS NULL OR d.source = ANY(%(hidden)s)) " + where,
        params,
    ).fetchone()[0]


def _pair_rows(conn, hidden: list[str], where: str = "", params: dict | None = None) -> list[tuple]:
    """(section, slug, canonical id, name, working, problems, neutral) per pair."""
    return conn.execute(
        f"SELECT be.section, {_SLUG}, v.canonical_id, v.display_name, {_VOICES}"
        f"{_FROM} AND be.section = ANY(%(sections)s) {where} GROUP BY 1, 2, 3, 4",
        {"hidden": hidden, "sections": list(SECTIONS), **(params or {})},
    ).fetchall()


# ── where engineers disagree ────────────────────────────────────────────────


def contested(conn) -> dict[str, Any]:
    """Every (model, job or capability) pair with at least one engineer
    reporting it working AND at least one reporting problems.

    THE ORDER IS SAID IN WORDS ON THE PAGE AND IS MADE OF SHOWN COUNTS: most
    engineers on the smaller side first, then on the larger side. There is no
    "controversy" figure; each row shows both counts, so a reader can check
    any row's place against its neighbours (rule 3)."""
    hidden = _hidden()
    names = _topic_names(conn, hidden)
    listed = _in_catalog(conn)
    pairs = [
        {
            "section": s,
            "slug": slug,
            "topic": names.get((s, slug), slug),
            "model": _model(cid, name, listed),
            "working": p,
            "problems": n,
            "neutral": z,
        }
        for s, slug, cid, name, p, n, z in _pair_rows(conn, hidden)
        if p >= 1 and n >= 1
    ]
    pairs.sort(
        key=lambda r: (
            -min(r["working"], r["problems"]),
            -max(r["working"], r["problems"]),
            r["topic"],
            r["model"]["name"],
        )
    )
    return {
        "pairs": pairs,
        "two_or_more_each_side": sum(1 for r in pairs if min(r["working"], r["problems"]) >= 2),
        "withheld_entries": _withheld(
            conn,
            "AND be.section = ANY(%(sections)s)",
            {"hidden": hidden, "sections": list(SECTIONS)},
        ),
    }


# ── one claim wall ──────────────────────────────────────────────────────────


def wall(conn, section: str, slug: str, model_id: str) -> dict[str, Any] | None:
    """One model on one job or capability, every public quote, by side.

    None when there is no public row for the pair (the route answers 404).
    An EMPTY SIDE is returned empty and the page says "nobody has reported
    problems" in words, distinct from a side with quotes (rule 4)."""
    if section not in SECTIONS:
        return None
    hidden = _hidden()
    p = {"hidden": hidden, "section": section, "slug": slug, "model": model_id}
    rows = conn.execute(
        f"SELECT be.polarity, be.quote, be.document_id, d.url, d.source, d.created_at, "
        f"       d.author_id, v.display_name, be.name "
        f"{_FROM} AND be.section = %(section)s AND {_SLUG} = %(slug)s "
        f"AND v.canonical_id = %(model)s "
        f"ORDER BY d.created_at DESC NULLS LAST, be.document_id",
        p,
    ).fetchall()
    if not rows:
        return None
    sides: dict[str, list[dict]] = {"positive": [], "negative": [], "neutral": []}
    authors: dict[str, set[str]] = {"positive": set(), "negative": set(), "neutral": set()}
    seen: set[tuple[str, str]] = set()
    no_author = 0
    for pol, quote, doc, url, source, written, author, _mname, _tname in rows:
        if author:
            authors[pol].add(author)
        # ONE QUOTE ONCE. The same words from the same document can be stored
        # under two pipeline versions; the reader should see them once.
        if (doc, quote) in seen:
            continue
        seen.add((doc, quote))
        if not author:
            no_author += 1
        sides[pol].append(
            {
                "quote": quote,
                "url": url,
                "source": SOURCE_LABEL.get(source, source),
                "written": _iso(written.date()) if written else None,
            }
        )
    listed = _in_catalog(conn)
    names = _topic_names(conn, hidden)
    about = (job_about() if section == "best_for" else capability_about()).get(slug)

    # THE RAILS: the same topic for other models, and this model's other
    # topics where engineers disagree. Plain joins, ordered by shown counts.
    same_topic = [
        {"model": _model(cid, name, listed), "working": wp, "problems": wn, "neutral": wz}
        for _s, _slug, cid, name, wp, wn, wz in _pair_rows(
            conn,
            hidden,
            f"AND be.section = %(section)s AND {_SLUG} = %(slug)s AND v.canonical_id <> %(model)s",
            p,
        )
    ]
    same_topic.sort(
        key=lambda r: (-(r["working"] + r["problems"] + r["neutral"]), r["model"]["name"])
    )
    other_topics = [
        {"section": s, "slug": sl, "topic": names.get((s, sl), sl), "working": wp, "problems": wn}
        for s, sl, _cid, _n, wp, wn, _wz in _pair_rows(
            conn, hidden, "AND v.canonical_id = %(model)s", p
        )
        if wp >= 1 and wn >= 1 and not (s == section and sl == slug)
    ]
    other_topics.sort(key=lambda r: (-min(r["working"], r["problems"]), r["topic"]))
    return {
        "section": section,
        "slug": slug,
        "topic": names.get((section, slug), slug),
        "about": about,
        "model": _model(model_id, rows[0][7], listed),
        "working": len(authors["positive"]),
        "problems": len(authors["negative"]),
        "neutral": len(authors["neutral"]),
        "quotes": sides,
        "quotes_without_author": no_author,
        "withheld_entries": _withheld(
            conn,
            f"AND be.section = %(section)s AND {_SLUG} = %(slug)s AND v.canonical_id = %(model)s",
            p,
        ),
        "same_topic": same_topic[:8],
        "other_topics": other_topics[:8],
    }


# ── this week in models ─────────────────────────────────────────────────────


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def weeks(today: date | None = None) -> list[str]:
    """The weeks the page offers, newest first: Mondays, as ISO dates."""
    n = blog_live_settings()["this_week"]["weeks_shown"]
    start = _monday(today or datetime.now(UTC).date())
    return [(start - timedelta(weeks=i)).isoformat() for i in range(n)]


def week(conn, start: str | None = None, today: date | None = None) -> dict[str, Any] | None:
    """What changed in one week (Monday to Sunday, UTC). None for a week the
    page does not offer.

    ⚠ REPORTS ARE COUNTED BY WHEN THE POST WAS WRITTEN, never by when we
      stored it. Stored rows follow our fetch runs, so a busy fetch week would
      otherwise read as a busy week for a model (rule 7). The price of that is
      that a past week's count GROWS when a later fetch finds an older post,
      and the page says so.
    """
    cfg = blog_live_settings()["this_week"]
    today = today or datetime.now(UTC).date()
    offered = weeks(today)
    start = start or offered[0]
    if start not in offered:
        return None
    w0 = date.fromisoformat(start)
    w1 = w0 + timedelta(days=7)
    hidden = _hidden()
    listed = _in_catalog(conn)
    p = {"hidden": hidden, "w0": w0, "w1": w1, "sections": list(SECTIONS)}

    listings = [
        {
            "id": cid,
            "name": name,
            "provider": prov,
            "outputs": list(outs or []),
            "context": ctx,
            "price_in": _per_token(cid, pi),
            "price_out": _per_token(cid, po),
            "listed": _iso(at.date()),
        }
        for cid, name, prov, outs, ctx, pi, po, at in conn.execute(
            "SELECT canonical_id, name, provider, output_modalities, context_length, "
            "       price_in, price_out, listed_at FROM model_catalog "
            "WHERE last_seen_at = (SELECT max(last_seen_at) FROM model_catalog) "
            "AND canonical_id NOT LIKE '~%%' AND listed_at >= %(w0)s AND listed_at < %(w1)s "
            "ORDER BY listed_at DESC, name",
            p,
        ).fetchall()
    ]

    totals = conn.execute(
        f"SELECT count(*), count(DISTINCT d.author_id), count(DISTINCT v.canonical_id) "
        f"{_FROM} AND d.created_at >= %(w0)s AND d.created_at < %(w1)s",
        p,
    ).fetchone()
    busiest = [
        {
            "model": _model(cid, name, listed),
            "voices": total,
            "working": wp,
            "problems": wn,
            "neutral": wz,
        }
        for cid, name, total, wp, wn, wz in conn.execute(
            f"SELECT v.canonical_id, v.display_name, count(DISTINCT d.author_id), {_VOICES}"
            f"{_FROM} AND d.created_at >= %(w0)s AND d.created_at < %(w1)s "
            f"AND be.section = ANY(%(sections)s) "
            f"GROUP BY 1, 2 HAVING count(DISTINCT d.author_id) > 0 "
            f"ORDER BY 3 DESC, 2 LIMIT %(lim)s",
            {**p, "lim": cfg["models_listed"]},
        ).fetchall()
    ]
    names = _topic_names(conn, hidden)
    first_voices = [
        {
            "section": s,
            "slug": slug,
            "topic": names.get((s, slug), slug),
            "first": _iso(first.date()),
            "voices": v,
            "models": m,
        }
        for s, slug, first, v, m in conn.execute(
            f"SELECT be.section, {_SLUG}, min(d.created_at), count(DISTINCT d.author_id), "
            f"       count(DISTINCT v.canonical_id) "
            f"{_FROM} AND be.section = ANY(%(sections)s) GROUP BY 1, 2 "
            f"HAVING min(d.created_at) >= %(w0)s AND min(d.created_at) < %(w1)s "
            f"ORDER BY 4 DESC, 2",
            p,
        ).fetchall()
    ]

    retiring = [
        {"id": cid, "name": name, "date": _iso(exp), "page": "catalog"}
        for cid, name, exp in conn.execute(
            "SELECT canonical_id, name, expiration_date FROM model_catalog "
            "WHERE last_seen_at = (SELECT max(last_seen_at) FROM model_catalog) "
            "AND expiration_date >= %(w0)s AND expiration_date < %(until)s "
            "ORDER BY expiration_date, name",
            {**p, "until": w1 + timedelta(days=cfg["retiring_within_days"])},
        ).fetchall()
    ]

    # PRICE CHANGES: a history row WITH A PREDECESSOR. The first row for a model
    # is when the registry first saw it, not a change - 186 rows in the week of
    # 2026-08-17 were the first load.
    changes = conn.execute(
        "WITH h AS (SELECT model_version_id, price_in, price_out, price_cached_read, observed_at, "
        "  lag(price_in) OVER w AS was_in, lag(price_out) OVER w AS was_out, "
        "  lag(price_cached_read) OVER w AS was_cached, lag(observed_at) OVER w AS prev "
        "  FROM pricing_history WINDOW w AS (PARTITION BY model_version_id ORDER BY observed_at)) "
        "SELECT v.canonical_id, v.display_name, h.was_in, h.price_in, h.was_out, h.price_out, "
        "       h.was_cached, h.price_cached_read, h.observed_at "
        "FROM h JOIN model_version v ON v.id = h.model_version_id "
        "WHERE h.prev IS NOT NULL AND h.observed_at >= %(w0)s AND h.observed_at < %(w1)s "
        "ORDER BY h.observed_at DESC, v.display_name",
        p,
    ).fetchall()

    def _f(x):
        return float(x) if x is not None else None

    prices = [
        {
            "model": _model(cid, name, listed),
            "was_in": _f(a),
            "now_in": _f(b),
            "was_out": _f(c),
            "now_out": _f(d),
            "was_cached": _f(e),
            "now_cached": _f(f),
            "on": _iso(at.date()),
        }
        for cid, name, a, b, c, d, e, f, at in changes
    ]
    last_change = conn.execute(
        "SELECT max(observed_at) FROM (SELECT observed_at, "
        "  lag(observed_at) OVER (PARTITION BY model_version_id ORDER BY observed_at) prev "
        "  FROM pricing_history) t WHERE prev IS NOT NULL"
    ).fetchone()[0]
    # WHETHER THE HISTORY HAS STOPPED, measured rather than guessed: models
    # whose price in TODAY's catalogue differs from the last price the history
    # recorded for them. A history row is written only on a change, so a
    # stopped poller and a quiet market look the same from the history alone.
    drift = conn.execute(
        "WITH last AS (SELECT DISTINCT ON (model_version_id) model_version_id, price_in, price_out "
        "  FROM pricing_history ORDER BY model_version_id, observed_at DESC) "
        "SELECT count(*) FILTER (WHERE c.price_in IS DISTINCT FROM l.price_in "
        "                        OR c.price_out IS DISTINCT FROM l.price_out), count(*), "
        "       max(c.last_seen_at) "
        "FROM last l JOIN model_version v ON v.id = l.model_version_id "
        "JOIN model_catalog c ON c.canonical_id = v.canonical_id "
        "WHERE c.last_seen_at = (SELECT max(last_seen_at) FROM model_catalog) "
        "AND c.price_in IS NOT NULL AND c.price_out IS NOT NULL"
    ).fetchone()

    return {
        "week": start,
        "weeks": offered,
        "in_progress": w0 <= today < w1,
        "through": _iso(min(today, w1 - timedelta(days=1))),
        "listings": listings,
        "reports": {"entries": totals[0], "voices": totals[1], "models": totals[2]},
        "busiest": busiest,
        "first_voices": first_voices,
        "retiring": retiring,
        "retiring_within_days": cfg["retiring_within_days"],
        "prices": prices,
        "price_history": {
            "last_change": _iso(last_change.date()) if last_change else None,
            "differs_now": drift[0],
            "compared": drift[1],
            "catalogue_read": _iso(drift[2].date()) if drift[2] else None,
        },
        "withheld_entries": _withheld(
            conn, "AND d.created_at >= %(w0)s AND d.created_at < %(w1)s", p
        ),
    }


# ── the daily quiz ──────────────────────────────────────────────────────────

_FOLD = re.compile(r"[^a-z0-9]+")
_WORD = re.compile(r"[a-z0-9]+")
_STARTS = re.compile(r"[^\W_]|[\"'“`(]")

#: Words in model names that say nothing about WHICH model: matching them as
#: tells would drop half the pool and catch nothing. Matched as whole words,
#: so "pro" is never found inside "problem" either way.
_GENERIC = frozenset(
    {
        "pro",
        "max",
        "mini",
        "flash",
        "lite",
        "turbo",
        "preview",
        "fast",
        "ultra",
        "ultrafast",
        "plus",
        "nano",
        "free",
        "instruct",
        "chat",
        "base",
        "large",
        "small",
        "medium",
        "thinking",
        "reasoning",
        "code",
        "coder",
        "vision",
        "beta",
        "experimental",
        "latest",
        "model",
        "batch",
        "voice",
        "open",
        "the",
        "and",
        "with",
    }
)


def _fold(s: str) -> str:
    return _FOLD.sub("", (s or "").lower())


def _tells(conn) -> dict[str, set[str]]:
    """Every string that would give a model away, folded: its aliases, its
    names, its family and its maker. Keyed by `model_version.id`.

    A quote containing ANY of its model's tells is not used, so the quiz shows
    quotes UNCHANGED - nothing is blanked out. The list is only as good as the
    alias table, and the page says so."""
    tells: dict[str, set[str]] = {}
    for mv, cid, name, family, provider in conn.execute(
        "SELECT id, canonical_id, display_name, family, provider FROM model_version"
    ).fetchall():
        t = tells.setdefault(mv, set())
        short = (name or "").split(":", 1)[-1].strip()
        tail = (cid or "").rsplit("/", 1)[-1]
        for s in (
            name,
            short,
            tail,
            family,
            provider,
            short.split(" ")[0] if short else "",
            tail.split("-")[0],
        ):
            if s:
                t.add(_fold(s))
    for mv, surface, variants in conn.execute(
        "SELECT model_version_id, surface, variants FROM model_alias"
    ).fetchall():
        t = tells.setdefault(mv, set())
        for s in [surface, *(variants or [])]:
            if s:
                t.add(_fold(s))
    for t in tells.values():
        t.discard("")
    return tells


def _name_words(conn) -> dict[str, set[str]]:
    """The DISTINCTIVE words of each model's name, for whole-word matching:
    "Sol" in "GPT-6.1 Sol", "Astra", "Opus". The folded tells above catch a
    full name run together; a single short word needs word boundaries, or
    "sol" would be found inside "solution". Words with a digit are versions,
    already covered by the folded tells."""
    words: dict[str, set[str]] = {}
    for mv, name in conn.execute("SELECT id, display_name FROM model_version").fetchall():
        short = (name or "").split(":", 1)[-1]
        words[mv] = {
            w
            for w in _WORD.findall(short.lower())
            if len(w) >= 3 and not any(ch.isdigit() for ch in w) and w not in _GENERIC
        }
    return words


def _names(quote: str, mv: str, tells: dict[str, set[str]], words: dict[str, set[str]]) -> bool:
    """Does this quote give model `mv` away?"""
    folded = _fold(quote)
    if any(t in folded for t in tells.get(mv, ())):
        return True
    return bool(words.get(mv, set()) & set(_WORD.findall(quote.lower())))


def quiz(conn, day: str | None = None, today: date | None = None) -> dict[str, Any] | None:
    """One day's quiz: the same questions for every reader on that day.

    THE CHOICE IS RANDOM AND SEEDED BY THE DATE. Nothing ranks a quote or a
    model; code draws from the pool. The pool changes as evidence arrives, so a
    past day's quiz can differ when reopened later.

    None for a day after today, or one that is not a date."""
    cfg = blog_live_settings()["quiz"]
    today = today or datetime.now(UTC).date()
    try:
        d = date.fromisoformat(day) if day else today
    except ValueError:
        return None
    if d > today:
        return None
    hidden = _hidden()
    tells = _tells(conn)
    words = _name_words(conn)
    listed = _in_catalog(conn)
    names = _topic_names(conn, hidden)
    rows = conn.execute(
        f"SELECT be.id, be.section, {_SLUG}, be.polarity, be.quote, d.url, d.source, d.created_at, "
        f"       v.id, v.canonical_id, v.display_name "
        f"{_FROM} AND be.section = ANY(%(sections)s) AND be.polarity IN ('positive', 'negative') "
        f"AND length(be.quote) BETWEEN %(lo)s AND %(hi)s "
        f"ORDER BY be.id",
        {
            "hidden": hidden,
            "sections": list(SECTIONS),
            "lo": cfg["min_chars"],
            "hi": cfg["max_chars"],
        },
    ).fetchall()
    # A QUOTE CUT MID-SENTENCE reads as noise in a question: one that opens
    # on punctuation (". On a 4-page file...") is left out. 30 of 1,626
    # candidates on 2026-10-15. A cut mid-WORD cannot be seen from the text.
    pool = [r for r in rows if _STARTS.match(r[4]) and not _names(r[4], r[8], tells, words)]
    by_topic: dict[tuple[str, str], set[str]] = {}
    model_of: dict[str, tuple[str, str]] = {}
    for r in pool:
        by_topic.setdefault((r[1], r[2]), set()).add(r[8])
        model_of[r[8]] = (r[9], r[10])
    everyone = sorted(model_of)

    rng = random.Random(f"mib-quiz:{d.isoformat()}")
    order = pool[:]
    rng.shuffle(order)
    questions, used = [], set()
    for r in order:
        if len(questions) == cfg["questions_per_day"]:
            break
        eid, section, slug, pol, quote, url, source, written, mv, cid, name = r
        if mv in used:
            continue
        # A DISTRACTOR THE QUOTE NAMES would be a trick, not a guess.
        ok = [m for m in everyone if m != mv and not _names(quote, m, tells, words)]
        near = sorted(m for m in by_topic[(section, slug)] if m in ok)
        rng.shuffle(near)
        rest = [m for m in ok if m not in near]
        rng.shuffle(rest)
        picks = (near + rest)[: cfg["options"] - 1]
        if len(picks) < cfg["options"] - 1:
            continue
        options = [mv, *picks]
        rng.shuffle(options)
        used.add(mv)
        questions.append(
            {
                "id": eid,
                "quote": quote,
                "url": url,
                "source": SOURCE_LABEL.get(source, source),
                "written": _iso(written.date()) if written else None,
                "section": section,
                "slug": slug,
                "topic": names.get((section, slug), slug),
                "polarity": pol,
                "options": [{"id": model_of[m][0], "name": model_of[m][1]} for m in options],
                "answer": _model(cid, name, listed),
            }
        )
    return {
        "day": d.isoformat(),
        "latest_day": today.isoformat(),
        "questions": questions,
        "pool": {"quotes": len(pool), "models": len(everyone), "considered": len(rows)},
    }


# ── hover previews ──────────────────────────────────────────────────────────


def preview(conn, kind: str, ident: str) -> dict[str, Any] | None:
    """A small card. `kind` is `model` (a canonical id), `job` or `cap` (a
    slug). None when there is nothing public to show."""
    hidden = _hidden()
    if kind == "model":
        cat = conn.execute(
            "SELECT name, provider, context_length, price_in, price_out FROM model_catalog "
            "WHERE canonical_id = %s "
            "AND last_seen_at = (SELECT max(last_seen_at) FROM model_catalog)",
            (ident,),
        ).fetchone()
        reg = conn.execute(
            "SELECT display_name, provider, advertised_context, price_in, price_out "
            "FROM model_version WHERE canonical_id = %s",
            (ident,),
        ).fetchone()
        src = cat or reg
        if src is None:
            return None
        v = conn.execute(
            f"SELECT {_VOICES}, count(DISTINCT ({_SLUG}, be.section)) {_FROM} "
            f"AND be.section = ANY(%(sections)s) AND v.canonical_id = %(m)s",
            {"hidden": hidden, "sections": list(SECTIONS), "m": ident},
        ).fetchone()
        return {
            "kind": "model",
            "id": ident,
            "name": src[0],
            "provider": src[1],
            "context": src[2],
            "price_in": _per_token(ident, src[3]),
            "price_out": _per_token(ident, src[4]),
            "working": v[0],
            "problems": v[1],
            "neutral": v[2],
            "topics": v[3],
        }
    section = {"job": "best_for", "cap": "capability"}.get(kind)
    if section is None:
        return None
    p = {"hidden": hidden, "section": section, "slug": ident}
    head = conn.execute(
        f"SELECT mode() WITHIN GROUP (ORDER BY be.name), {_VOICES}, count(DISTINCT v.canonical_id) "
        f"{_FROM} AND be.section = %(section)s AND {_SLUG} = %(slug)s",
        p,
    ).fetchone()
    if head is None or head[0] is None:
        return None
    sample = {}
    for pol in ("positive", "negative"):
        r = conn.execute(
            f"SELECT be.quote, v.display_name {_FROM} AND be.section = %(section)s "
            f"AND {_SLUG} = %(slug)s AND be.polarity = %(pol)s AND length(be.quote) <= 220 "
            f"ORDER BY d.created_at DESC NULLS LAST, be.id LIMIT 1",
            {**p, "pol": pol},
        ).fetchone()
        sample[pol] = {"quote": r[0], "model": r[1]} if r else None
    about = (job_about() if section == "best_for" else capability_about()).get(ident)
    return {
        "kind": kind,
        "id": ident,
        "name": head[0],
        "about": about,
        "working": head[1],
        "problems": head[2],
        "neutral": head[3],
        "models": head[4],
        "sample_working": sample["positive"],
        "sample_problems": sample["negative"],
    }
