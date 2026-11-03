"""The launch verdict (/verdict): what engineers reported about a model in each
window after it launched, and (/verdict/week) in any one week.

A PROTOTYPE (feat/hooks-prototype, 2026-11-03, anooj), from the master-idea
research: the pain people name is not "which model is best" but not knowing -
"I can't tell if it's real or not - I don't have the data". The page shows the
reports in each window after release (contract/verdict.yaml), counted and
quoted. The launch claim is the model page's own description; what engineers
say in short is the evidence feed's approved summary (/feed/summary), which the
page reads itself - neither is repeated here (2026-11-03 review: the listing's
words appeared twice on one page).

COUNTS ONLY (rule 3): per window, posts and people by polarity, the most-named
capabilities and jobs, and the newest verified quotes. Nothing is scored, and
the windows are never compared with a number.

WHEN A REPORT WAS MADE is the post's own date (document.created_at). A model
with no release date has no windows, and the payload says why (rule 6). A
window that has not begun is `not_yet`; one still running is `open`.

PUBLIC SURFACE RULES, from judge/publication.py: counts include every source
(`sql_counted_document`). What people said is shown as the EVIDENCE FEED'S
PARAPHRASE, never a quote (2026-11-03 review): the feed's derived-post terms
(contract/publication.yaml `evidence_feed`) let a paraphrase come from every
source, Reddit and X included, cited by platform only - so a window reads the
whole field rather than the half a quote may show. A held source, or a report
with no current paraphrase, is left out of the examples, never shown raw; the
counts still include it.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from judge import publication


class VerdictRequestError(ValueError):
    """A request the page should not have sent (no model id, a bad week)."""


def rules() -> dict[str, Any]:
    """contract/verdict.yaml, validated. Every key required; nothing defaulted."""
    from judge.config import _read

    raw = _read("verdict.yaml") or {}
    try:
        out: dict[str, Any] = {k: int(raw[k]) for k in ("top_topics", "quotes_per_side")}
        windows = [
            {"key": str(w["key"]), "label": str(w["label"]),
             "from_day": int(w["from_day"]), "to_day": int(w["to_day"])}
            for w in raw["windows"]
        ]
        sections = list(raw["sections"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"contract/verdict.yaml: missing or malformed {exc}") from exc
    if min(out.values()) < 1 or not windows or not sections:
        raise ValueError("contract/verdict.yaml: counts must be at least 1, lists non-empty")
    last = -1
    for w in windows:
        if w["from_day"] <= last or w["to_day"] < w["from_day"]:
            raise ValueError("contract/verdict.yaml: windows must run in order without overlap")
        last = w["to_day"]
    out["windows"], out["sections"] = windows, sections
    return out


MODEL_SQL = """
SELECT v.id, v.canonical_id, v.display_name, v.provider, v.release_date
FROM model_version v WHERE v.canonical_id = %s
"""


def _counts_sql() -> tuple[str, tuple]:
    clause, params = publication.sql_counted_document("be.document_id")
    sql = f"""
SELECT be.polarity, count(DISTINCT d.id), count(DISTINCT d.author_id)
FROM board_entry be JOIN document d ON d.id = be.document_id
WHERE be.model_version_id = %s AND be.ruling IS DISTINCT FROM 'declined'
  AND be.section = ANY(%s) AND d.created_at::date BETWEEN %s AND %s {clause}
GROUP BY 1"""
    return sql, params


def _people_sql() -> tuple[str, tuple]:
    clause, params = publication.sql_counted_document("be.document_id")
    sql = f"""
SELECT count(DISTINCT d.id), count(DISTINCT d.author_id)
FROM board_entry be JOIN document d ON d.id = be.document_id
WHERE be.model_version_id = %s AND be.ruling IS DISTINCT FROM 'declined'
  AND be.section = ANY(%s) AND d.created_at::date BETWEEN %s AND %s {clause}"""
    return sql, params


def _topics_sql() -> tuple[str, tuple]:
    clause, params = publication.sql_counted_document("be.document_id")
    sql = f"""
SELECT be.name, be.section, be.polarity, count(DISTINCT d.id)
FROM board_entry be JOIN document d ON d.id = be.document_id
WHERE be.model_version_id = %s AND be.ruling IS DISTINCT FROM 'declined'
  AND be.section = ANY(%s) AND d.created_at::date BETWEEN %s AND %s {clause}
GROUP BY 1, 2, 3"""
    return sql, params


def _first_problem_sql() -> tuple[str, tuple]:
    clause, params = publication.sql_counted_document("be.document_id")
    sql = f"""
SELECT min(d.created_at) FROM board_entry be JOIN document d ON d.id = be.document_id
WHERE be.model_version_id = %s AND be.ruling IS DISTINCT FROM 'declined'
  AND be.polarity = 'negative' AND be.section = ANY(%s) AND d.created_at::date >= %s {clause}"""
    return sql, params


def _iso(v: Any) -> str | None:
    return v.isoformat() if isinstance(v, (date, datetime)) else None


def _state(start: date, end: date, today: date) -> str:
    if today < start:
        return "not_yet"
    return "open" if today <= end else "closed"


def verdict(conn, model_id: str, *, today: date | None = None) -> dict[str, Any]:
    if not model_id or not model_id.strip():
        raise VerdictRequestError("name one model")
    r = rules()
    today = today or datetime.now(UTC).date()
    row = conn.execute(MODEL_SQL, (model_id.strip(),)).fetchone()
    if row is None:
        return {"model": None, "unknown": model_id.strip()}
    mv, cid, name, provider, released = row
    out: dict[str, Any] = {
        "model": {"id": cid, "name": name or cid, "provider": provider,
                  "release_date": _iso(released)},
        "sections": r["sections"],
    }
    if released is None:
        out["windows"] = None
        out["reason"] = "no release date is recorded for this model, so no window can start"
        return out
    out["days_since_release"] = (today - released).days
    reports = _feed_reports(conn, cid)
    windows = []
    for w in r["windows"]:
        start = released + timedelta(days=w["from_day"])
        end = released + timedelta(days=w["to_day"])
        block: dict[str, Any] = {
            "key": w["key"], "label": w["label"], "from": start.isoformat(), "to": end.isoformat(),
            "state": _state(start, end, today),
        }
        if block["state"] != "not_yet":
            block.update(_period(conn, mv, r, start, min(end, today), reports))
        windows.append(block)
    out["windows"] = windows
    fp_sql, fpp = _first_problem_sql()
    first = conn.execute(fp_sql, (mv, r["sections"], released, *fpp)).fetchone()[0]
    out["first_problem_report"] = _iso(first)
    return out


def _period(conn, mv: str, r: dict[str, Any], start: date, end: date,
            reports: dict[str, list[dict]] | None = None) -> dict[str, Any]:
    """Posts and people by polarity, the most-named topics and the newest
    paraphrased reports for one model between two dates (the post's own date,
    inclusive). `reports` is the feed's view of the model (`_feed_reports`)."""
    counts_sql, cp = _counts_sql()
    people_sql, pp = _people_sql()
    topics_sql, tp = _topics_sql()
    args = (mv, r["sections"], start, end)
    by = {pol: {"posts": n, "people": p}
          for pol, n, p in conn.execute(counts_sql, (*args, *cp)).fetchall()}
    posts, people = conn.execute(people_sql, (*args, *pp)).fetchone()
    # ONE TOPIC PER NAME AS THE READER SEES IT: "Code review" and "Code Review"
    # are one heading on the page, as the evidence feed's tags already treat
    # them (judge/feed/items.py). The first spelling seen is the one shown.
    topics: dict[str, dict[str, Any]] = {}
    for tname, section, pol, n in conn.execute(topics_sql, (*args, *tp)).fetchall():
        t = topics.setdefault(tname.strip().lower(), {"name": tname, "section": section,
                                                      "positive": 0, "negative": 0, "neutral": 0})
        t[pol] += n
    ranked = sorted(topics.values(), key=lambda t: (-(t["positive"] + t["negative"]
                                                      + t["neutral"]), t["name"].lower()))
    return {
        "posts": posts, "people": people,
        "by_polarity": {k: by.get(k, {"posts": 0, "people": 0})
                        for k in ("positive", "negative", "neutral")},
        "topics": ranked[:r["top_topics"]],
        "said": _said(conn, mv, reports or {}, r, start, end),
    }


def _feed_reports(conn, model_id: str) -> dict[str, list[dict]]:
    """The evidence feed's reports for a model (every source a public total
    counts), so the examples here are the feed's own items."""
    from judge.feed import items

    return items.by_report(items.model_entries(conn, items.resolve_model(conn, model_id)))


def _said(conn, mv: str, reports: dict[str, list[dict]], r: dict[str, Any], start: date,
          end: date) -> dict[str, list[dict]]:
    """The newest paraphrased reports on each side in the window - one per post,
    the feed's paraphrase and citation, never a quote."""
    from judge.config import evidence_feed_settings
    from judge.feed import items

    def posted(es: list[dict]) -> date | None:
        at = es[0]["posted_at"]
        return at.date() if at else None

    in_window = {d: es for d, es in reports.items()
                 if posted(es) and start <= posted(es) <= end
                 and any(e["section"] in r["sections"] for e in es)
                 and not publication.feed_hides(es[0]["source"])}
    if not in_window:
        return {"positive": [], "negative": []}
    version = evidence_feed_settings()["paraphrase"]["prompt_version"]
    ids = list(in_window)
    texts = {d: (t, dig) for d, t, dig in conn.execute(
        "SELECT document_id, text, excerpts_digest FROM feed_paraphrase "
        "WHERE model_version_id = %s AND prompt_version = %s AND document_id = ANY(%s)",
        (mv, version, ids)).fetchall()}
    embeds = {d: {"outcome": o, "url": u} for d, o, u in conn.execute(
        "SELECT document_id, outcome, url FROM feed_embed WHERE document_id = ANY(%s)",
        (ids,)).fetchall()}
    out: dict[str, list[dict]] = {"positive": [], "negative": []}
    newest = sorted(in_window.items(), key=lambda kv: (-kv[1][0]["posted_at"].timestamp(), kv[0]))
    for doc_id, es in newest:
        found = texts.get(doc_id)
        if found is None or found[1] != items.excerpts_digest(es):
            continue  # not paraphrased yet, or written from other excerpts
        pol = items.report_polarity(es)
        for side in ("positive", "negative"):
            if pol in (side, "both") and len(out[side]) < r["quotes_per_side"]:
                names: dict[str, str] = {}
                for e in es:
                    n = e["name"] or e["slug"]
                    names.setdefault(n.strip().lower(), n)
                out[side].append({
                    "id": doc_id, "text": found[0], "on": list(names.values())[:3],
                    "at": _iso(es[0]["posted_at"]),
                    "source": items.cite_source(es[0], embeds.get(doc_id)),
                })
    return out


def week(conn, model_id: str, start: date, *, today: date | None = None) -> dict[str, Any]:
    """One week of a model's reports, for the trend on its page: the same
    counts, topics and quotes as a verdict window, over `start` .. `start` + 6
    days (cut at today while it is still running)."""
    if not model_id or not model_id.strip():
        raise VerdictRequestError("name one model")
    r = rules()
    today = today or datetime.now(UTC).date()
    row = conn.execute(MODEL_SQL, (model_id.strip(),)).fetchone()
    if row is None:
        return {"model": None, "unknown": model_id.strip()}
    end = start + timedelta(days=6)
    out: dict[str, Any] = {"model": {"id": row[1]}, "from": start.isoformat(),
                           "to": end.isoformat(), "state": _state(start, end, today)}
    if out["state"] != "not_yet":
        reports = _feed_reports(conn, row[1])
        out.update(_period(conn, row[0], r, start, min(end, today), reports))
    return out


def parse_week(raw: str | None) -> date:
    """A week's first day as YYYY-MM-DD, or a refusal - never a guessed week."""
    try:
        return date.fromisoformat((raw or "").strip())
    except ValueError as exc:
        raise VerdictRequestError("week must be a date, YYYY-MM-DD") from exc
