"""The blog's live pages, rendered from the board in code (2026-10-15).

    claim walls            one model on one job or capability: the reports of it
                           working beside the reports of problems
    where they disagree    every (model, topic) pair with engineers on both sides
    this week in models    listings, new reports, prices and retirements, per week
    the daily quiz         general questions about the models, answered by
                           figures this site publishes
    hover previews         a small card for a model or a topic

NO MODEL CALL, NO REVIEW PER PAGE. These re-render board rows; nothing here
writes a sentence about a model. Every figure is a count (engineers, reports,
days) or a measured price (rule 3).

TOTALS COUNT EVERY SOURCE; QUOTES SHOW PUBLIC SOURCES ONLY (contract/
publication.yaml, amended 2026-10-15). "20 engineers" counts every source we
read, and nothing on these pages says how many came from which platform. A
quote, a link or a platform name comes only from sources the contract does not
withhold, whatever view the deployment runs - so a wall can count more reports
than it quotes, and it says so in words (rule 4) without naming a platform.

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
    "forum": "Developer forum",
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
    """For QUOTES, links and platform names: the contract's withheld list."""
    return list(publication.withheld_sources())


def _hidden_counts() -> list[str]:
    """For TOTALS: empty while totals include every source."""
    return list(publication.hidden_from_counts())


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
    """Rows whose source a public page does not QUOTE, under the same filter as
    the page (rule 4). Since 2026-10-15 they are still COUNTED in its totals;
    this is how many of those reports have no quote shown. Unknown provenance
    counts here too. Pass the QUOTE list (`_hidden()`), never the counts one."""
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


def catalog_entry(conn, cid: str) -> dict[str, Any] | None:
    """One model as today's catalogue lists it, with its advertised features
    as the catalogue module derives them (True / False / None = not published).
    For the Q&A pages (judge/blog_reference.py), which must not read the
    catalogue table themselves (tests/test_model_catalog.py)."""
    from judge.catalog import _features

    row = conn.execute(
        "SELECT name, input_modalities, supported_parameters, price_cached_read "
        "FROM model_catalog WHERE canonical_id = %s "
        "AND last_seen_at = (SELECT max(last_seen_at) FROM model_catalog)",
        (cid,),
    ).fetchone()
    if row is None:
        return None
    name, ins, params, p_cache = row
    return {"name": name, "features": _features(list(params or []), ins, p_cache)}


# ── where engineers disagree ────────────────────────────────────────────────


def contested(conn) -> dict[str, Any]:
    """Every (model, job or capability) pair with at least one engineer
    reporting it working AND at least one reporting problems.

    THE ORDER IS SAID IN WORDS ON THE PAGE AND IS MADE OF SHOWN COUNTS: most
    engineers on the smaller side first, then on the larger side. There is no
    "controversy" figure; each row shows both counts, so a reader can check
    any row's place against its neighbours (rule 3)."""
    hidden = _hidden_counts()
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
            {"hidden": _hidden(), "sections": list(SECTIONS)},
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
    pc = {**p, "hidden": _hidden_counts()}
    # THE COUNTS, from every source. A pair with no row at all is a 404.
    counted = _pair_rows(
        conn, pc["hidden"],
        f"AND be.section = %(section)s AND {_SLUG} = %(slug)s AND v.canonical_id = %(model)s",
        pc,
    )
    if not counted:
        return None
    _s, _sl, _cid, model_name, c_pos, c_neg, c_neu = counted[0]
    # THE QUOTES, from the sources a public page may quote.
    rows = conn.execute(
        f"SELECT be.polarity, be.quote, be.document_id, d.url, d.source, d.created_at, "
        f"       d.author_id, v.display_name, be.name "
        f"{_FROM} AND be.section = %(section)s AND {_SLUG} = %(slug)s "
        f"AND v.canonical_id = %(model)s "
        f"ORDER BY d.created_at DESC NULLS LAST, be.document_id",
        p,
    ).fetchall()
    sides: dict[str, list[dict]] = {"positive": [], "negative": [], "neutral": []}
    seen: set[tuple[str, str]] = set()
    no_author = 0
    for pol, quote, doc, url, source, written, author, _mname, _tname in rows:
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
    names = _topic_names(conn, pc["hidden"])
    about = (job_about() if section == "best_for" else capability_about()).get(slug)

    # THE RAILS: the same topic for other models, and this model's other
    # topics where engineers disagree. Plain joins, ordered by shown counts.
    same_topic = [
        {"model": _model(cid, name, listed), "working": wp, "problems": wn, "neutral": wz}
        for _s, _slug, cid, name, wp, wn, wz in _pair_rows(
            conn,
            pc["hidden"],
            f"AND be.section = %(section)s AND {_SLUG} = %(slug)s AND v.canonical_id <> %(model)s",
            pc,
        )
    ]
    same_topic.sort(
        key=lambda r: (-(r["working"] + r["problems"] + r["neutral"]), r["model"]["name"])
    )
    other_topics = [
        {"section": s, "slug": sl, "topic": names.get((s, sl), sl), "working": wp, "problems": wn}
        for s, sl, _cid, _n, wp, wn, _wz in _pair_rows(
            conn, pc["hidden"], "AND v.canonical_id = %(model)s", pc
        )
        if wp >= 1 and wn >= 1 and not (s == section and sl == slug)
    ]
    other_topics.sort(key=lambda r: (-min(r["working"], r["problems"]), r["topic"]))
    return {
        "section": section,
        "slug": slug,
        "topic": names.get((section, slug), slug),
        "about": about,
        "model": _model(model_id, model_name, listed),
        "working": c_pos,
        "problems": c_neg,
        "neutral": c_neu,
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
    hidden = _hidden_counts()  # this page shows totals and dates, never a quote
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
    }


# ── the daily quiz ──────────────────────────────────────────────────────────
#
# GENERAL QUESTIONS, NOT QUOTES (reworked 2026-10-15). The first version showed
# an engineer's quote and asked which model it was about - a reader cannot know
# who wrote it, about what, or where, so it was a guess and not a question. Now
# every question is about the models themselves and is answered by a figure we
# PUBLISH: a measured price or context window, a listing or retirement date,
# what a model reads and writes, a feature it advertises, its maker, or how
# many engineers wrote about it. Every choice's figure is shown once answered,
# so the reader learns the answer rather than being told it (rule 3: counts and
# measurements only; rule 6: a choice whose figure is unknown is never used).


def _short(name: str) -> str:
    """What a model is called, without the maker: "MoonshotAI: Kimi K2.5" -> "Kimi K2.5"."""
    return (name or "").split(":", 1)[-1].strip()


#: A listing that would make a confusing choice beside its own sibling.
_VARIANT = re.compile(r"\((batch|free|beta|preview|thinking|extended|self-moderated)\)", re.I)

_FEATURES = {
    "tools": "tool calling",
    "structured_outputs": "structured output",
    "reasoning": "a reasoning mode",
}
_READS = {"image": "images", "audio": "audio", "video": "video", "file": "files such as PDFs"}
_WRITES = {
    "image": "images",
    "speech": "speech",
    "video": "video",
    "audio": "audio",
    "embeddings": "embeddings",
    "transcription": "transcripts",
}


def _quiz_models(conn, hidden: list[str]) -> list[dict[str, Any]]:
    """The models a question may draw on: today's catalogue, one listing per
    model (no `~` aliases, no `:variant` ids, no "(batch)"-style siblings)."""
    voices = dict(
        conn.execute(
            f"SELECT v.canonical_id, count(DISTINCT d.author_id) {_FROM} GROUP BY 1",
            {"hidden": hidden},
        ).fetchall()
    )
    registry = {r[0] for r in conn.execute("SELECT canonical_id FROM model_version").fetchall()}
    out = []
    for cid, name, ins, outs, ctx, pi, po, listed, expires, params in conn.execute(
        "SELECT canonical_id, name, input_modalities, output_modalities, context_length, "
        "       price_in, price_out, listed_at, expiration_date, supported_parameters "
        "FROM model_catalog WHERE last_seen_at = (SELECT max(last_seen_at) FROM model_catalog) "
        "AND canonical_id NOT LIKE '~%%' AND canonical_id NOT LIKE '%%:%%'",
        {},
    ).fetchall():
        if _VARIANT.search(name or "") or ":" not in (name or ""):
            continue
        out.append(
            {
                "id": cid,
                "name": _short(name),
                "maker": name.split(":", 1)[0].strip(),
                "ins": list(ins or []),
                "outs": list(outs or []),
                "context": ctx,
                "price_in": _per_token(cid, pi),
                "price_out": _per_token(cid, po),
                "listed": listed.date() if listed else None,
                "expires": expires,
                "params": list(params) if params else None,
                "voices": voices.get(cid, 0),
                "known": cid in registry or voices.get(cid, 0) > 0,
            }
        )
    return out


def _ranked(rng, pool, n, key, *, high: bool, margin: float):
    """n models whose `key` is known, with ONE clear winner: it beats the
    runner-up by `margin` (a ratio), so the answer is not a rounding error."""
    pool = [m for m in pool if key(m) is not None]
    if len(pool) < n:
        return None
    for _ in range(40):
        opts = rng.sample(pool, n)
        vals = sorted((key(m) for m in opts), reverse=high)
        best, second = vals[0], vals[1]
        clear = best >= second * margin if high else best * margin <= second
        if best != second and clear:
            win = max(opts, key=key) if high else min(opts, key=key)
            return opts, win
    return None


def _odd_one(rng, pool, n, has):
    """n models where EXACTLY ONE has the property. `has` returns None when
    the property is not published for a model, which leaves it out (rule 6)."""
    yes = [m for m in pool if has(m) is True]
    no = [m for m in pool if has(m) is False]
    if not yes or len(no) < n - 1:
        return None
    win = rng.choice(yes)
    return [win, *rng.sample(no, n - 1)], win


def _opt(m: dict, value: Any, unit: str) -> dict[str, Any]:
    return {"id": m["id"], "name": m["name"], "value": value, "unit": unit}


def _question(kind: str, rng: random.Random, models: list[dict], cfg: dict, today: date):
    n = cfg["options"]
    margin = 1 + cfg["margin_percent"] / 100
    known = [m for m in models if m["known"]]
    text = [m for m in known if "text" in m["outs"]]

    if kind == "longest_input":
        got = _ranked(rng, text, n, lambda m: m["context"], high=True, margin=margin)
        if not got:
            return None
        opts, win = got
        return {
            "prompt": "Which of these can take the longest input?",
            "options": [_opt(m, m["context"], "tokens") for m in opts],
            "answer": win["id"],
            "explain": "The context window each model advertises, in tokens.",
            "source": "OpenRouter's catalogue",
            "links": [["Check what fits in the token counter", "/token-counter"]],
        }
    if kind == "cheapest_input":
        got = _ranked(rng, text, n, lambda m: m["price_in"], high=False, margin=margin)
        if not got:
            return None
        opts, win = got
        return {
            "prompt": "Which of these is cheapest per million input tokens?",
            "options": [_opt(m, m["price_in"], "usd_per_m") for m in opts],
            "answer": win["id"],
            "explain": "List price per million input tokens. A real bill also depends on "
            "output, caching and volume.",
            "source": "OpenRouter's catalogue",
            "links": [["Price a whole workload in the token counter", "/token-counter"]],
        }
    if kind == "dearest_output":
        got = _ranked(rng, text, n, lambda m: m["price_out"], high=True, margin=margin)
        if not got:
            return None
        opts, win = got
        return {
            "prompt": "Which of these costs the most per million output tokens?",
            "options": [_opt(m, m["price_out"], "usd_per_m") for m in opts],
            "answer": win["id"],
            "explain": "List price per million output tokens.",
            "source": "OpenRouter's catalogue",
            "links": [["Compare models side by side", "/compare"]],
        }
    if kind == "newest":
        got = _ranked(
            rng,
            known,
            n,
            lambda m: m["listed"].toordinal() if m["listed"] else None,
            high=True,
            margin=1,
        )
        if not got:
            return None
        opts, win = got
        dates = sorted((m["listed"] for m in opts), reverse=True)
        if (dates[0] - dates[1]).days < cfg["gap_days"]:
            return None
        return {
            "prompt": "Which of these was listed on OpenRouter most recently?",
            "options": [_opt(m, m["listed"].isoformat(), "date") for m in opts],
            "answer": win["id"],
            "explain": "The date each model first appeared on OpenRouter - not always "
            "the day it was released.",
            "source": "OpenRouter's catalogue",
            "links": [["See every new listing", "/ai-models/latest"]],
        }
    if kind == "reads":
        what = rng.choice(sorted(_READS))
        got = _odd_one(rng, known, n, lambda m: (what in m["ins"]) if m["ins"] else None)
        if not got:
            return None
        opts, win = got
        return {
            "prompt": f"Which of these can take {_READS[what]} as input?",
            "options": [_opt(m, m["ins"], "list") for m in opts],
            "answer": win["id"],
            "explain": "What each model is listed as reading.",
            "source": "OpenRouter's catalogue",
            "links": [["Find models by what they read and write", "/ai-model-pricing"]],
        }
    if kind == "writes":
        what = rng.choice(sorted(_WRITES))
        got = _odd_one(rng, models, n, lambda m: (what in m["outs"]) if m["outs"] else None)
        if not got:
            return None
        opts, win = got
        return {
            "prompt": f"Which of these makes {_WRITES[what]}?",
            "options": [_opt(m, m["outs"], "list") for m in opts],
            "answer": win["id"],
            "explain": "What each model is listed as producing.",
            "source": "OpenRouter's catalogue",
            "links": [["Find models by what they read and write", "/ai-model-pricing"]],
        }
    if kind == "missing_feature":
        key = rng.choice(sorted(_FEATURES))
        # THE ODD ONE OUT LACKS IT. Only models that publish a parameter list
        # take part: an unpublished list is unknown, not "does not support".
        got = _odd_one(rng, text, n, lambda m: (key not in m["params"]) if m["params"] else None)
        if not got:
            return None
        opts, win = got
        return {
            "prompt": f"Which of these does not advertise {_FEATURES[key]}?",
            "options": [_opt(m, key in m["params"], "yesno") for m in opts],
            "answer": win["id"],
            "explain": f"Whether each model lists {_FEATURES[key]} among its supported "
            "parameters. Advertised, not tested.",
            "source": "OpenRouter's catalogue",
            "links": [["Filter by feature in the spec finder", "/ai-model-pricing"]],
        }
    if kind == "retires_first":
        dated = [m for m in models if m["expires"] and m["expires"] >= today]
        got = _ranked(rng, dated, n, lambda m: m["expires"].toordinal(), high=False, margin=1)
        if not got:
            return None
        opts, win = got
        return {
            "prompt": "Which of these is scheduled to retire first?",
            "options": [_opt(m, m["expires"].isoformat(), "date") for m in opts],
            "answer": win["id"],
            "explain": "The date OpenRouter says it stops serving each model.",
            "source": "OpenRouter's catalogue",
            "links": [["See what changed this week", "/blogs/this-week"]],
        }
    if kind == "maker":
        if not known:
            return None
        win = rng.choice(known)
        others = sorted({m["maker"] for m in models if m["maker"] != win["maker"]})
        if len(others) < n - 1:
            return None
        makers = [win["maker"], *rng.sample(others, n - 1)]
        return {
            "prompt": f"Who makes {win['name']}?",
            "options": [{"id": mk, "name": mk, "value": None, "unit": "none"} for mk in makers],
            "answer": win["maker"],
            "explain": "The maker as OpenRouter lists it.",
            "source": "OpenRouter's catalogue",
            "links": [[f"{win['name']}'s page", f"model:{win['id']}"]],
        }
    if kind == "most_discussed":
        voiced = [m for m in known if m["voices"] > 0]
        got = _ranked(rng, voiced, n, lambda m: m["voices"], high=True, margin=margin)
        if not got:
            return None
        opts, win = got
        return {
            "prompt": "Engineers have written about which of these the most?",
            "options": [_opt(m, m["voices"], "engineers") for m in opts],
            "answer": win["id"],
            "explain": "Distinct engineers whose public posts report on each model. Most "
            "discussed is not the same as best.",
            "source": "The board's public reports",
            "links": [["See where engineers disagree", "/blogs/disagree"]],
        }
    return None


QUESTION_KINDS = (
    "longest_input",
    "cheapest_input",
    "dearest_output",
    "newest",
    "reads",
    "writes",
    "missing_feature",
    "retires_first",
    "maker",
    "most_discussed",
)


def quiz(conn, day: str | None = None, today: date | None = None) -> dict[str, Any] | None:
    """One day's quiz: the same questions for every reader on that day.

    THE CHOICE IS RANDOM AND SEEDED BY THE DATE. Code draws which kinds of
    question, and which models, from the catalogue; nothing ranks a model.
    The catalogue changes, so a past day's quiz can differ when reopened.

    None for a day after today, or one that is not a date."""
    cfg = blog_live_settings()["quiz"]
    today = today or datetime.now(UTC).date()
    try:
        d = date.fromisoformat(day) if day else today
    except ValueError:
        return None
    if d > today:
        return None
    rng = random.Random(f"mib-quiz:{d.isoformat()}")

    # GENERAL QUESTIONS FIRST: approved ones only, one per topic where the bank
    # allows, so a day is not five questions on tokenization.
    from judge import quiz_bank

    bank = quiz_bank.approved(conn)
    rng.shuffle(bank)
    general, topics_used = [], set()
    for pass_ in (0, 1):
        for g in bank:
            if len(general) == cfg["general_per_day"]:
                break
            if g in general or (pass_ == 0 and g["topic"] in topics_used):
                continue
            general.append(g)
            topics_used.add(g["topic"])
    questions = [
        {
            "id": g["id"],
            "kind": "general",
            "prompt": g["question"],
            "options": [
                {"id": str(i), "name": text, "value": None, "unit": "none"}
                for i, text in enumerate(g["options"])
            ],
            "answer": str(g["answer_index"]),
            "explain": g["explanation"],
            "source": f"{g['topic']} · {g['difficulty']}",
            "links": [],
        }
        for g in general
    ]
    for q in questions:
        rng.shuffle(q["options"])

    # FROM THE BOARD: the rest. A shortfall of approved general questions is
    # filled here and SAID (rule 4) - never filled with an unapproved draft.
    shortfall = cfg["general_per_day"] - len(general)
    models = _quiz_models(conn, _hidden_counts())
    kinds = list(QUESTION_KINDS)
    rng.shuffle(kinds)
    board = []
    for kind in kinds:
        if len(board) == cfg["board_per_day"] + shortfall:
            break
        q = _question(kind, rng, models, cfg, today)
        if q:
            rng.shuffle(q["options"])
            board.append({"id": f"{d.isoformat()}:{kind}", "kind": kind, **q})
    questions += board
    read = conn.execute("SELECT max(last_seen_at) FROM model_catalog").fetchone()[0]
    return {
        "day": d.isoformat(),
        "latest_day": today.isoformat(),
        "questions": questions,
        "approved_in_bank": len(bank),
        "general_shortfall": shortfall,
        "catalogue_read": _iso(read.date()) if read else None,
    }


# ── hover previews ──────────────────────────────────────────────────────────


def preview(conn, kind: str, ident: str) -> dict[str, Any] | None:
    """A small card. `kind` is `model` (a canonical id), `job` or `cap` (a
    slug). None when there is nothing public to show."""
    hidden = _hidden_counts()
    quote_hidden = _hidden()
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
            {**p, "pol": pol, "hidden": quote_hidden},
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
