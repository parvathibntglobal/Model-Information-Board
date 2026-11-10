"""One model's pulse (/watch): what is new on its page, and its weekly trend.

A PROTOTYPE (feat/hooks-prototype, 2026-11-02, anooj). The team found the site
has no hook that brings a person back. The research behind it
(docs/measurements/hooks-feasibility-2026-11-02) found 125 of 146 models with
board entries had something to show in 30 days.

WHAT IT SENDS IS WHAT THE PAGE READS (#597 review, rule 9): per model, reports
in the window by polarity, what is new since the browser's last look, the
release date and a weekly trend; and the window's length. The prices, events,
quotes and suggestions a separate watch page once used are gone with that
page - and with them every verbatim quote this public read used to carry.

COUNTED AS THE VERDICT COUNTS (judge/verdict.py `COUNTED`): an entry no person
declined, in the sections contract/verdict.yaml names, every source
(`publication.sql_counted_document`) - so a week's bar here and the week it
opens there count the same reports. Days and weeks are the post's own, in UTC
(`POST_WEEK`).

TWO CLOCKS. A report's place in the window and the trend is the post's own date
(document.created_at). "New since your last look" is when the entry reached the
board (board_entry.created_at), whatever the post's date - a post written in
July and extracted today IS new to the reader.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from judge import publication
from judge.verdict import COUNTED, POST_WEEK, counted_sections


class WatchRequestError(ValueError):
    """A request the page should not have sent (too many models, a bad date)."""


def rules() -> dict[str, Any]:
    """contract/watch.yaml, validated. Every key required; nothing defaulted."""
    from judge.config import _read

    raw = _read("watch.yaml") or {}
    try:
        out: dict[str, Any] = {k: int(raw[k])
                               for k in ("window_days", "max_models", "trend_weeks")}
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"contract/watch.yaml: missing or non-integer {exc}") from exc
    if min(out.values()) < 1:
        raise ValueError("contract/watch.yaml: every number must be at least 1")
    return out


def _iso(v: Any) -> str | None:
    return v.isoformat() if isinstance(v, (date, datetime)) else None


MODELS_SQL = "SELECT id, canonical_id, release_date FROM model_version WHERE canonical_id = ANY(%s)"


def _counts_sql() -> tuple[str, tuple]:
    clause, params = publication.sql_counted_document("be.document_id")
    sql = f"""
SELECT be.model_version_id, be.polarity, count(DISTINCT d.id)
FROM board_entry be JOIN document d ON d.id = be.document_id
WHERE be.model_version_id = ANY(%s) AND {COUNTED} AND d.created_at >= %s {clause}
GROUP BY 1, 2"""
    return sql, params


def _new_sql() -> tuple[str, tuple]:
    clause, params = publication.sql_counted_document("be.document_id")
    sql = f"""
SELECT be.model_version_id, be.polarity, count(DISTINCT d.id)
FROM board_entry be JOIN document d ON d.id = be.document_id
WHERE be.model_version_id = ANY(%s) AND {COUNTED} AND be.created_at >= %s {clause}
GROUP BY 1, 2"""
    return sql, params


def _trend_sql() -> tuple[str, tuple]:
    clause, params = publication.sql_counted_document("be.document_id")
    sql = f"""
SELECT be.model_version_id, {POST_WEEK} AS wk, be.polarity, count(DISTINCT d.id)
FROM board_entry be JOIN document d ON d.id = be.document_id
WHERE be.model_version_id = ANY(%s) AND {COUNTED} AND d.created_at >= %s {clause}
GROUP BY 1, 2, 3"""
    return sql, params


def _sides(by: dict[str, int]) -> dict[str, int]:
    return {k: by.get(k, 0) for k in ("positive", "negative", "neutral")}


def watch(conn, ids: list[str], *, since: datetime | None = None,
          now: datetime | None = None) -> dict[str, Any]:
    """One entry per asked model that is in the registry, in the order asked.
    `ids` are canonical ids (openai/gpt-6-sol); `since` is the browser's last
    look, or None. A model not in the registry has no entry, and the page
    reads its absence as "not in the registry"."""
    r = rules()
    ids = list(dict.fromkeys(i.strip() for i in ids if i and i.strip()))
    if len(ids) > r["max_models"]:
        raise WatchRequestError(f"at most {r['max_models']} models in one request")
    clock = now or datetime.now(UTC)
    window = clock - timedelta(days=r["window_days"])
    # The trend: the last `trend_weeks` calendar weeks, Monday to Monday in UTC
    # (as POST_WEEK counts them), the current one last.
    monday = clock.date() - timedelta(days=clock.weekday())
    weeks = [monday - timedelta(weeks=k) for k in range(r["trend_weeks"] - 1, -1, -1)]
    trend_from = datetime.combine(weeks[0], time.min, UTC)
    out: dict[str, Any] = {"models": [], "window_days": r["window_days"]}
    if not ids:
        return out
    rows = {row[1]: row for row in conn.execute(MODELS_SQL, (ids,)).fetchall()}
    mv_ids = [rows[i][0] for i in ids if i in rows]
    sections = counted_sections()

    sql, params = _counts_sql()
    counts: dict[str, dict] = {}
    for mv, pol, n in conn.execute(sql, (mv_ids, sections, window, *params)).fetchall():
        counts.setdefault(mv, {})[pol] = n

    new: dict[str, dict] = {}
    if since is not None:
        sql, params = _new_sql()
        for mv, pol, n in conn.execute(sql, (mv_ids, sections, since, *params)).fetchall():
            new.setdefault(mv, {})[pol] = n

    sql, params = _trend_sql()
    trend: dict[str, dict] = {}
    for mv, wk, pol, n in conn.execute(sql, (mv_ids, sections, trend_from, *params)).fetchall():
        trend.setdefault(mv, {}).setdefault(wk, {})[pol] = n

    for cid in ids:
        if cid not in rows:
            continue
        mv, _cid, released = rows[cid]
        out["models"].append({
            "id": cid,
            "release_date": _iso(released),
            # Distinct posts dated in the window, by polarity, every source.
            "reports": _sides(counts.get(mv, {})),
            # None when the browser sent no last look: "nothing new" and "we do
            # not know when you last looked" are different (rule 6).
            "new_since": None if since is None else _sides(new.get(mv, {})),
            "trend": _weeks(trend.get(mv, {}), weeks),
        })
    return out


def _weeks(by_week: dict, weeks: list[date]) -> list[dict]:
    """Every week in the trend, an empty week as zeros - a week with no reports
    is shown as such, not skipped."""
    return [{"week": wk.isoformat(), **_sides(by_week.get(wk, {}))} for wk in weeks]


def parse_since(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        got = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WatchRequestError("since must be an ISO date-time") from exc
    return got if got.tzinfo else got.replace(tzinfo=UTC)
