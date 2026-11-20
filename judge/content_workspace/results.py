"""Phase 3: a draft's tracked link, and the results log of what it did.

The tracked link is the draft's model page (or the site's front page) with
UTM tags naming the platform, the topic and the draft. The results log holds
what a person reads off the platform's own analytics, each reading dated: a
later reading is a new row. Nothing is fetched from any platform, and nothing
is scored or turned into a rate here (rule 3): counts with their dates.

Visits to our site from a tracked link are NOT measured: the site has no
analytics yet (config `tracking.site_visits_why`). They are reported as not
measured, never as zero (rule 6).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from judge.content_workspace import store


def tracked_link(d: dict[str, Any], s: dict[str, Any]) -> dict[str, Any]:
    t = s["tracking"]
    sug = d.get("suggestion") or {}
    path = next((link["path"] for link in sug.get("links") or [] if link.get("path")), "/")
    query = urlencode({
        "utm_source": d["platform_key"],
        "utm_medium": t["utm_medium"],
        "utm_campaign": d.get("topic_kind") or t["campaign_without_topic"],
        "utm_content": f"draft-{d['id']}",
    })
    base = (os.environ.get(s["site"]["hosts_env"]) or "").strip().rstrip("/")
    return {
        "url": f"{base}{path}?{query}",
        "complete": bool(base),
        "note": None if base else (
            f"the site address is not set ({s['site']['hosts_env']}), so this is the path "
            "only; put the site's address in front of it"),
    }


def metrics_for(platform_key: str, s: dict[str, Any]) -> list[dict[str, str]]:
    r = s["results"]
    return [{"key": k, "label": r["metrics"][k]} for k in r["by_platform"][platform_key]]


RESULT_COLUMNS = ("id", "draft_id", "metric", "value", "observed_at", "source", "note",
                  "recorded_at", "recorded_by")


def _row(row: tuple) -> dict[str, Any]:
    r = dict(zip(RESULT_COLUMNS, row, strict=True))
    for k in ("observed_at", "recorded_at"):
        r[k] = r[k].isoformat()
    return r


def add(conn: Any, draft_id: int, *, metric: str, value: int, source: str,
        observed_at: datetime | None, note: str | None, by: str | None,
        s: dict[str, Any]) -> dict[str, Any]:
    d = store.draft(conn, draft_id)
    allowed = {m["key"] for m in metrics_for(d["platform_key"], s)}
    if metric not in allowed:
        raise store.WorkspaceRequestError(
            f"{metric!r} is not recorded for {d['platform_key']}; one of "
            f"{', '.join(sorted(allowed))}")
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise store.WorkspaceRequestError("value is a count: a whole number, 0 or more")
    if not (source or "").strip():
        raise store.WorkspaceRequestError("say where the number was read (the source)")
    if d["status"] != "posted":
        raise store.WorkspaceRequestError("results are recorded for a posted draft", 409)
    observed_at = observed_at or datetime.now(UTC)
    if observed_at > datetime.now(UTC):
        raise store.WorkspaceRequestError("a reading cannot be from the future")
    row = conn.execute(
        "INSERT INTO cw_result (draft_id, metric, value, observed_at, source, note, recorded_by)"
        f" VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING {', '.join(RESULT_COLUMNS)}",
        (draft_id, metric, value, observed_at, source.strip(), (note or "").strip() or None, by),
    ).fetchone()
    return _row(row)


def overview(conn: Any, platform_key: str, s: dict[str, Any]) -> dict[str, Any]:
    """Every posted draft on one platform with its latest reading per metric.
    Counts with their dates, side by side; no rate, total or ranking across
    posts (rule 3), and a metric nobody recorded stays empty (rule 6)."""
    p = store.platform(conn, platform_key)
    metrics = metrics_for(platform_key, s)
    posted = [d for d in store.drafts(conn, platform_key) if d["status"] == "posted"]
    latest: dict[int, dict[str, dict]] = {}
    if posted:
        for draft_id, metric, value, at, source in conn.execute(
                "SELECT DISTINCT ON (draft_id, metric) draft_id, metric, value, observed_at,"
                " source FROM cw_result WHERE draft_id = ANY(%s)"
                " ORDER BY draft_id, metric, observed_at DESC, id DESC",
                ([d["id"] for d in posted],)).fetchall():
            latest.setdefault(draft_id, {})[metric] = {
                "value": value, "observed_at": at.isoformat(), "source": source}
    rows = []
    for d in posted:
        sug = d.get("suggestion") or {}
        rows.append({
            "draft_id": d["id"], "format": d["format"], "topic_kind": d["topic_kind"],
            "headline": d["title"] or sug.get("headline") or (d["body"] or "").split("\n")[0][:120],
            "posted_at": d["posted_at"], "posted_url": d["posted_url"],
            "ai_assisted": d["ai_assisted"],
            "latest": latest.get(d["id"], {}),
            "recorded": len(latest.get(d["id"], {})),
        })
    rows.sort(key=lambda r: r["posted_at"] or "", reverse=True)
    t = s["tracking"]
    return {
        "platform": {"key": p["key"], "name": p["name"]},
        "metrics": metrics,
        "posts": rows,
        "counts": {"posted": len(rows),
                   "with_any_reading": sum(1 for r in rows if r["recorded"])},
        "site_visits": {"measured": t["site_visits_measured"],
                        "why": " ".join(t["site_visits_why"].split())},
        "order": "Newest post first. Each figure is the latest reading for that post, with "
                 "its date; posts are not ranked or added up.",
    }


def view(conn: Any, draft_id: int, s: dict[str, Any]) -> dict[str, Any]:
    """The draft's tracked link, every reading, and the latest per metric.
    A metric with no reading is listed as not recorded."""
    d = store.draft(conn, draft_id)
    rows = [_row(r) for r in conn.execute(
        f"SELECT {', '.join(RESULT_COLUMNS)} FROM cw_result WHERE draft_id = %s"
        " ORDER BY observed_at DESC, id DESC", (draft_id,)).fetchall()]
    latest: dict[str, dict] = {}
    for r in rows:
        latest.setdefault(r["metric"], r)
    t = s["tracking"]
    return {
        "link": tracked_link(d, s),
        "metrics": [{**m, "latest": latest.get(m["key"])}
                    for m in metrics_for(d["platform_key"], s)],
        "site_visits": {"measured": t["site_visits_measured"],
                        "why": " ".join(t["site_visits_why"].split())},
        "readings": rows,
    }
