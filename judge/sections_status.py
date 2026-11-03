"""What Admin shows about the two public sections, AI benchmarks and AI updates
(Parvathi, 2026-11-02). READ-ONLY throughout; nothing here starts a run.

TWO READS.

  schedules()  Admin -> Scheduler, under the nightly fetches: the GitHub
               Actions that feed the two sections. AI benchmarks has its own
               (`benchmarks.yml`, behind BENCHMARKS_SCHEDULE_ENABLED). AI
               updates has none: judge/updates.py rebuilds it on every read
               from what other jobs wrote - launches and prices from the
               registry poll (`registry-poll.yml`), benchmark results from the
               benchmarks runs - so its block shows those feeds. The workflow
               file, its runs and its switch are read through
               judge/scheduler_status.py, as the nightly block reads them.

  sections()   Admin -> Board & content: what each public page holds now. AI
               benchmarks from the kept charts copy (no build is started from
               here); AI updates from the decisions in update_review plus the
               public page's kept copy. Counts the data does not hold - how
               many updates are waiting for a person - are not guessed: that
               needs the full build, which Manage runs.

Every timing value shown is read from its contract, never restated here.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

import yaml

from judge import scheduler_status as ss

#: The workflows that feed the two sections. `variable` is the repository
#: switch a scheduled run obeys; None when the workflow has none (the registry
#: poll runs on every firing).
FEEDS: tuple[dict[str, Any], ...] = (
    {
        "key": "benchmarks",
        "file": "benchmarks.yml",
        "variable": "BENCHMARKS_SCHEDULE_ENABLED",
        "feeds": (
            "AI benchmarks (every score and position) and the benchmark headlines on AI updates"
        ),
    },
    {
        "key": "registry-poll",
        "file": "registry-poll.yml",
        "variable": None,
        "feeds": "AI updates: new models and price changes",
    },
)

_DAYS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")


def _parse(expr: str) -> tuple[int, int, set[int] | None] | None:
    """(minute, hour, weekdays or None for every day) for 'M H * * D[,D]';
    None for any other shape - shown as the expression, never guessed at."""
    parts = expr.split()
    if (
        len(parts) != 5
        or parts[2:4] != ["*", "*"]
        or not (parts[0].isdigit() and parts[1].isdigit())
    ):
        return None
    if parts[4] == "*":
        return int(parts[0]), int(parts[1]), None
    try:
        days = {int(d) % 7 for d in parts[4].split(",")}
    except ValueError:
        return None
    return int(parts[0]), int(parts[1]), days


def cron_words(expr: str) -> str:
    """'30 1 * * 2,5' -> 'Tue, Fri at 01:30 UTC (07:00 IST)'."""
    p = _parse(expr)
    if p is None:
        return expr
    minute, hour, days = p
    utc = datetime(2000, 1, 1, hour, minute, tzinfo=UTC)
    ist = utc + timedelta(hours=5, minutes=30)
    when = "daily" if days is None else ", ".join(_DAYS[d] for d in sorted(days))
    return f"{when} at {utc:%H:%M} UTC ({ist:%H:%M} IST)"


def next_firing(crons: list[str], now: datetime) -> str | None:
    """The next time any of `crons` fires, ISO; None when none has a known shape."""
    best = None
    for expr in crons:
        p = _parse(expr)
        if p is None:
            continue
        minute, hour, days = p
        for ahead in range(8):
            day = now + timedelta(days=ahead)
            at = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # cron counts Sunday as 0; Python's weekday() counts Monday as 0.
            if at > now and (days is None or (at.weekday() + 1) % 7 in days):
                best = at if best is None or at < best else best
                break
    return best.isoformat() if best else None


def workflow_setup(file: str) -> dict[str, Any]:
    path = ss.ROOT / ".github" / "workflows" / file
    try:
        raw = path.read_text(encoding="utf-8")
        wf = yaml.safe_load(raw) or {}
    except (OSError, yaml.YAMLError) as e:
        return {"unreadable": f"{file}: {type(e).__name__}"}
    # PyYAML reads the bare key `on:` as boolean True.
    on = wf.get("on", wf.get(True)) or {}
    crons = [c.get("cron") for c in (on.get("schedule") or []) if c.get("cron")]
    job = next(iter((wf.get("jobs") or {}).values()), {}) or {}
    return {
        "workflow": wf.get("name"),
        "file": f".github/workflows/{file}",
        "crons": [{"expr": c, "words": cron_words(c)} for c in crons],
        "manual_run": "workflow_dispatch" in on,
        "timeout_minutes": job.get("timeout-minutes"),
        "one_at_a_time": bool((wf.get("concurrency") or {}).get("group")),
    }


def _bench_runs(limit: int) -> dict[str, Any]:
    """What the last benchmarks runs did, from bench_run - the run's own record,
    which GitHub's "success" does not carry."""
    from judge import benchmarks

    try:
        with benchmarks.connection() as conn:
            got = benchmarks.runs(conn, limit=limit)
    except Exception as e:  # noqa: BLE001 - the rest of the block still answers
        return {"runs": [], "unreadable": type(e).__name__}
    return {
        "runs": [
            {
                "id": r["id"],
                "trigger": r["trigger"],
                "status": r["status"],
                "dry_run": r["dry_run"],
                "started_at": r["started_at"],
                "finished_at": r["finished_at"],
                "totals": r["totals"],
                "sources_failed": sorted(
                    # OK | BLOCK | FAIL | SKIP (collect/benchmarks/runner.py); a
                    # skipped source was not asked, which is not a failure.
                    k
                    for k, v in (r["sources"] or {}).items()
                    if v.get("status") in ("BLOCK", "FAIL")
                ),
                "sources_read": len(r["sources"] or {}),
            }
            for r in got["runs"]
        ]
    }


def schedules(now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    slug = ss.repo_slug()
    out = []
    for feed in FEEDS:
        s = workflow_setup(feed["file"])
        block: dict[str, Any] = {
            "key": feed["key"],
            "feeds": feed["feeds"],
            "setup": s,
            "variable": feed["variable"],
            "next_run": next_firing([c["expr"] for c in s.get("crons") or []], now),
        }
        if slug:
            block["github"] = ss.runs(slug, limit=8, workflow_file=feed["file"])
            if feed["variable"]:
                block["switch"] = ss.switch(slug, variable=feed["variable"])
            block["link"] = f"https://github.com/{slug}/actions/workflows/{feed['file']}"
        else:
            block["github"] = {
                "runs": [],
                "unreadable": "no repository known: set GITHUB_REPOSITORY on this backend",
            }
            if feed["variable"]:
                block["switch"] = {"unreadable": "no repository known"}
        if feed["key"] == "benchmarks":
            block["bench_runs"] = _bench_runs(5)
        out.append(block)
    return {"feeds": out, "repo": slug}


# ── what the two public pages hold ─────────────────────────────────────────


def _benchmarks_page() -> dict[str, Any]:
    from judge import benchmarks

    out: dict[str, Any] = {
        "path": "/ai-benchmarks",
        "recheck_seconds": benchmarks.charts_recheck_seconds(),
        "setting": "contract/benchmarks/module_settings.yaml charts.recheck_seconds",
    }
    kept = benchmarks._charts_kept
    if kept is None or kept.key[0] != benchmarks.database_url():
        # Not built on this process yet: the first visit builds it. Not built
        # from here - Admin opening must not cost the public page a build.
        out["kept"] = None
        return out
    b = kept.built
    out["kept"] = {
        "models": len(b["models"]),
        "tracked_models": sum(1 for m in b["models"] if m["tracked"]),
        "benchmarks_listed": b["benchmarks_listed"],
        "withheld_for_review": b["withheld_for_review"],
        "last_run": b["last_run"],
        "checked_seconds_ago": round(time.monotonic() - kept.checked),
    }
    return out


_REVIEW_COUNTS_SQL = (
    "SELECT kind, status, count(*), count(*) FILTER (WHERE home_published_at IS NOT NULL) "
    "FROM update_review GROUP BY kind, status"
)


def _updates_page(conn) -> dict[str, Any]:
    from psycopg import errors

    from judge import updates

    r = updates.rules()
    out: dict[str, Any] = {
        "path": "/ai-news-headlines",
        "timing": {
            k: r[k]
            for k in (
                "window_days",
                "max_window_days",
                "home_days",
                "home_limit",
                "home_cache_seconds",
                "unread_cache_seconds",
                "cold_wait_seconds",
            )
        },
        "setting": "contract/updates.yaml",
        "kinds": {k: v["label"] for k, v in r["kinds"].items()},
    }
    try:
        rows = conn.execute(_REVIEW_COUNTS_SQL).fetchall()
    except errors.UndefinedTable:
        conn.rollback()
        out["decisions"] = None  # the review tables are not in this database
    else:
        by_kind: dict[str, dict[str, int]] = {}
        for kind, status, n, on_home in rows:
            k = by_kind.setdefault(kind, {"approved": 0, "declined": 0, "pending": 0, "on_home": 0})
            k[status] = k.get(status, 0) + n
            k["on_home"] += on_home
        out["decisions"] = by_kind
    kept = updates.stale("approved")
    out["public_kept"] = None if kept is None else {"updates": len(kept.get("updates") or [])}
    return out


def sections(conn) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        out["benchmarks"] = _benchmarks_page()
    except Exception as e:  # noqa: BLE001 - the other section still answers
        out["benchmarks"] = {"unreadable": type(e).__name__}
    try:
        out["updates"] = _updates_page(conn)
    except Exception as e:  # noqa: BLE001
        out["updates"] = {"unreadable": type(e).__name__}
    return out
