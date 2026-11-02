"""Watch my models (/watch): what changed for the models a visitor runs.

A PROTOTYPE (feat/hooks-prototype, 2026-11-02, anooj). The team found the site
has no hook that brings a person back. The research behind this page
(docs/measurements/hooks-feasibility-2026-11-02) found the one thing every
persona needs and only this board can show: for MY models, did a price move,
is a retirement coming, and what are engineers reporting - and that the data
fills it: 125 of 146 models with board entries had something in 30 days.

EACH CARD carries, for one model, only what can be counted or measured
(rule 3): the listed prices now; the price moves and lifecycle events in the
window (model_event, with the before and after as listed); retirement and
deprecation dates; reports in the window counted by polarity; the newest
verified quotes; and a weekly trend of report counts. No score, no flag.

WHEN A REPORT WAS MADE is the document's own date (document.created_at),
never when we extracted it. "New since your last look" is the other clock:
when the entry reached the board (board_entry.created_at) - a post written in
July and extracted today IS new to the reader.

PUBLIC SURFACE RULES, from judge/publication.py and not restated here: counts
include every source (`sql_counted_document`); a quote, a link or a platform
name comes only from a source the publication contract lets a public page show
(`sql_shown_document`).

AN UNKNOWN MODEL ID IS SAID, never dropped: the payload lists it (rule 6).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from judge import publication


class WatchRequestError(ValueError):
    """A request the page should not have sent (too many models, a bad date)."""


SOURCE_LABEL = {"devto": "dev.to", "hackernews": "Hacker News", "github": "GitHub",
                "huggingface": "Hugging Face", "blog": "Blog", "forum": "Forum"}


def rules() -> dict[str, Any]:
    """contract/watch.yaml, validated. Every key required; nothing defaulted."""
    from judge.config import _read

    raw = _read("watch.yaml") or {}
    try:
        keys = ("window_days", "max_models", "quotes_per_model", "trend_weeks")
        out: dict[str, Any] = {k: int(raw[k]) for k in keys}
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"contract/watch.yaml: missing or non-integer {exc}") from exc
    if min(out.values()) < 1:
        raise ValueError("contract/watch.yaml: every number must be at least 1")
    sections = raw.get("quote_sections")
    if not (isinstance(sections, list) and sections and all(isinstance(x, str) for x in sections)):
        raise ValueError("contract/watch.yaml: quote_sections must list board sections")
    out["quote_sections"] = sections
    return out


def _price(v: Any) -> str | None:
    """A listed price per million tokens, as the page shows it; None stays None
    ("not published", never $0 - rule 6). Up to four decimals, never fewer than
    two, so a stored 0.7505999999999999 reads $0.7506."""
    if v is None or v == "":
        return None
    try:
        d = Decimal(str(v))
    except InvalidOperation:
        return None
    whole, cents = f"{float(d):,.4f}".split(".")
    cents = cents.rstrip("0")
    return f"${whole}.{cents + '0' * (2 - len(cents))}"


def _iso(v: Any) -> str | None:
    return v.isoformat() if isinstance(v, (date, datetime)) else None


MODELS_SQL = """
SELECT id, canonical_id, display_name, provider, price_in, price_out, release_date,
       deprecation_date, retirement_date, lifecycle
FROM model_version WHERE canonical_id = ANY(%s)
"""

EVENTS_SQL = """
SELECT model_version_id, type, coalesce(occurred_at, detected_at) AS at, payload
FROM model_event
WHERE model_version_id = ANY(%s) AND coalesce(occurred_at, detected_at) >= %s
ORDER BY at DESC
"""


def _counts_sql() -> tuple[str, tuple]:
    clause, params = publication.sql_counted_document("be.document_id")
    sql = f"""
SELECT be.model_version_id, be.polarity, count(DISTINCT d.id)
FROM board_entry be JOIN document d ON d.id = be.document_id
WHERE be.model_version_id = ANY(%s) AND d.created_at >= %s {clause}
GROUP BY 1, 2"""
    return sql, params


def _new_sql() -> tuple[str, tuple]:
    clause, params = publication.sql_counted_document("be.document_id")
    sql = f"""
SELECT be.model_version_id, be.polarity, count(DISTINCT d.id)
FROM board_entry be JOIN document d ON d.id = be.document_id
WHERE be.model_version_id = ANY(%s) AND be.created_at >= %s AND d.created_at >= %s {clause}
GROUP BY 1, 2"""
    return sql, params


def _trend_sql() -> tuple[str, tuple]:
    clause, params = publication.sql_counted_document("be.document_id")
    sql = f"""
SELECT be.model_version_id, date_trunc('week', d.created_at)::date AS wk, be.polarity,
       count(DISTINCT d.id)
FROM board_entry be JOIN document d ON d.id = be.document_id
WHERE be.model_version_id = ANY(%s) AND d.created_at >= %s {clause}
GROUP BY 1, 2, 3"""
    return sql, params


def _quotes_sql() -> tuple[str, tuple]:
    clause, params = publication.sql_shown_document("be.document_id")
    sql = f"""
SELECT model_version_id, quote, polarity, name, section, source, url, at FROM (
  SELECT be.model_version_id, be.quote, be.polarity, be.name, be.section, d.source, d.url,
         d.created_at AS at,
         row_number() OVER (PARTITION BY be.model_version_id
                            ORDER BY d.created_at DESC, be.id) AS rn
  FROM board_entry be JOIN document d ON d.id = be.document_id
  WHERE be.model_version_id = ANY(%s) AND be.quote_verified AND d.created_at >= %s
    AND d.url IS NOT NULL AND be.section = ANY(%s) {clause}
) q WHERE rn <= %s
ORDER BY model_version_id, at DESC"""
    return sql, params


def watch(conn, ids: list[str], *, since: datetime | None = None,
          now: datetime | None = None) -> dict[str, Any]:
    """One card per watched model, in the order asked. `ids` are canonical ids
    (openai/gpt-6-sol); `since` is the browser's last look, or None."""
    r = rules()
    ids = [i.strip() for i in ids if i and i.strip()]
    ids = list(dict.fromkeys(ids))
    if len(ids) > r["max_models"]:
        raise WatchRequestError(f"at most {r['max_models']} models can be watched on one page")
    clock = now or datetime.now(UTC)
    window = clock - timedelta(days=r["window_days"])
    # The trend: the last `trend_weeks` calendar weeks, Monday to Monday (as
    # Postgres date_trunc('week') counts them), the current one last.
    monday = clock.date() - timedelta(days=clock.weekday())
    weeks = [monday - timedelta(weeks=k) for k in range(r["trend_weeks"] - 1, -1, -1)]
    trend_from = datetime.combine(weeks[0], time.min, UTC)
    if not ids:
        return {"models": [], "unknown": [], "window_days": r["window_days"],
                "trend_weeks": r["trend_weeks"], "since": None,
                "suggestions": suggestions(conn, window)}

    rows = {row[1]: row for row in conn.execute(MODELS_SQL, (ids,)).fetchall()}
    unknown = [i for i in ids if i not in rows]
    mv_ids = [rows[i][0] for i in ids if i in rows]

    events: dict[str, list] = {}
    for mv, typ, at, payload in conn.execute(EVENTS_SQL, (mv_ids, window)).fetchall():
        events.setdefault(mv, []).append(_event(typ, at, payload or {}))

    sql, params = _counts_sql()
    counts: dict[str, dict] = {}
    for mv, pol, n in conn.execute(sql, (mv_ids, window, *params)).fetchall():
        counts.setdefault(mv, {})[pol] = n

    new: dict[str, dict] = {}
    if since is not None:
        sql, params = _new_sql()
        for mv, pol, n in conn.execute(sql, (mv_ids, since, window, *params)).fetchall():
            new.setdefault(mv, {})[pol] = n

    sql, params = _trend_sql()
    trend: dict[str, dict] = {}
    for mv, wk, pol, n in conn.execute(sql, (mv_ids, trend_from, *params)).fetchall():
        trend.setdefault(mv, {}).setdefault(wk, {})[pol] = n

    sql, params = _quotes_sql()
    quotes: dict[str, list] = {}
    seen: set[tuple[str, str]] = set()
    # Three times the cap, then the same sentence once: one post can carry the
    # quote under two board entries.
    for mv, q, pol, name, section, source, url, at in conn.execute(
            sql, (mv_ids, window, r["quote_sections"], *params,
                  3 * r["quotes_per_model"])).fetchall():
        key = (mv, " ".join((q or "").split()).lower())
        if key in seen or len(quotes.get(mv, [])) >= r["quotes_per_model"]:
            continue
        seen.add(key)
        quotes.setdefault(mv, []).append({
            "quote": q, "polarity": pol, "about": name, "section": section,
            "source": SOURCE_LABEL.get(source, source), "url": url, "date": _iso(at)})

    models = []
    for cid in ids:
        if cid not in rows:
            continue
        mv, _cid, name, provider, p_in, p_out, released, deprecated, retires, lifecycle = rows[cid]
        c = counts.get(mv, {})
        models.append({
            "id": cid,
            "name": name,
            "provider": provider,
            "price_in": _price(p_in),
            "price_out": _price(p_out),
            "release_date": _iso(released),
            "deprecation_date": _iso(deprecated),
            "retirement_date": _iso(retires),
            "lifecycle": lifecycle,
            "events": events.get(mv, []),
            # Distinct documents dated in the window, by polarity. Every source
            # counts (publication.totals_include_withheld); no platform split.
            "reports": {"positive": c.get("positive", 0), "negative": c.get("negative", 0),
                        "neutral": c.get("neutral", 0)},
            # None when the browser sent no last look: "nothing new" and "we do
            # not know when you last looked" are different (rule 6).
            "new_since": None if since is None else {
                "positive": new.get(mv, {}).get("positive", 0),
                "negative": new.get(mv, {}).get("negative", 0),
                "neutral": new.get(mv, {}).get("neutral", 0)},
            "trend": _weeks(trend.get(mv, {}), weeks),
            "quotes": quotes.get(mv, []),
        })
    return {"models": models, "unknown": unknown, "window_days": r["window_days"],
            "trend_weeks": r["trend_weeks"], "since": _iso(since), "suggestions": []}


def _event(typ: str, at: Any, payload: dict) -> dict:
    out = {"type": typ, "date": _iso(at)}
    if typ == "price-change":
        before, after = payload.get("from") or {}, payload.get("to") or {}
        out["changes"] = [
            {"field": f, "from": _price(before.get(f)), "to": _price(after.get(f))}
            for f in (payload.get("changed") or [])
            if f in ("price_in", "price_out", "price_cached_read")
        ]
    return out


def _weeks(by_week: dict, weeks: list[date]) -> list[dict]:
    """Every week in the trend, an empty week as zeros - a week with no reports
    is shown as such, not skipped."""
    return [{"week": wk.isoformat(), "negative": by_week.get(wk, {}).get("negative", 0),
             "positive": by_week.get(wk, {}).get("positive", 0),
             "neutral": by_week.get(wk, {}).get("neutral", 0)} for wk in weeks]


def suggestions(conn, window: datetime, limit: int = 8) -> list[dict]:
    """For an empty page: the models with the most reports in the window - a
    place to start, ordered by a count the page can show beside each name."""
    clause, params = publication.sql_counted_document("be.document_id")
    rows = conn.execute(f"""
        SELECT mv.canonical_id, mv.display_name, count(DISTINCT d.id) AS n
        FROM board_entry be JOIN document d ON d.id = be.document_id
        JOIN model_version mv ON mv.id = be.model_version_id
        WHERE d.created_at >= %s {clause}
        GROUP BY 1, 2 ORDER BY n DESC, 1 LIMIT %s""", (window, *params, limit)).fetchall()
    return [{"id": cid, "name": name, "reports": n} for cid, name, n in rows]


def parse_since(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        got = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WatchRequestError("since must be an ISO date-time") from exc
    return got if got.tzinfo else got.replace(tzinfo=UTC)
