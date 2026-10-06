"""What Admin -> Scheduler shows: how the scheduled fetches are set up, who is
due next, and what the last scheduled runs did. READ-ONLY throughout.

THE SCHEDULER IS A GITHUB ACTION (`.github/workflows/scheduled-fetches.yml`,
2026-10-06). It runs `scripts/run_scheduled_fetches.py`, which picks the due
models with `judge.scheduler.rank_due` under `contract/scheduler.yaml` and runs
`fetch_model` for each. So the facts live in four places, and this module reads
each where it lives rather than restating it:

  setup     the workflow file - its cron line, its limits, the secret and
            variable NAMES it reads (names only: values never leave GitHub)
  policy    contract/scheduler.yaml through `judge.scheduler.policy()`
  queue     the runner's own `due_rows` + `rank_due`, against this database
  runs      GitHub's Actions API for that workflow - the scheduled runs' log.
            `fetch_log` cannot tell a scheduled fetch from a button fetch (both
            get `<model>-<8 hex>` run ids), so the workflow's run list is the
            record of what the SCHEDULE did.

THE ON/OFF SWITCH IS NOT SHOWN (decided 2026-10-06). It is the repository
variable `SCHEDULER_ENABLED`; reading it needs a token with variable access, and
the panel does without it - `next_run` is the next time the cron FIRES.

NOTHING HERE STARTS OR CHANGES ANYTHING. Turning it on and running it now are
GitHub actions taken on GitHub; the panel links to the exact pages.
"""
from __future__ import annotations

import os
import re
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "scheduled-fetches.yml"
WORKFLOW_FILE = WORKFLOW.name
API = "https://api.github.com"
CACHE_S = 60

_cache: dict[str, tuple[float, Any]] = {}


def repo_slug() -> str | None:
    """owner/name of this checkout's origin, from GITHUB_REPOSITORY or .git/config."""
    env = os.getenv("GITHUB_REPOSITORY", "").strip()
    if env:
        return env
    try:
        text = (ROOT / ".git" / "config").read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r'\[remote "origin"\][^\[]*?url\s*=\s*(\S+)', text)
    if not m:
        return None
    hit = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?$", m.group(1))
    return hit.group(1) if hit else None


# ── setup, from the workflow file ───────────────────────────────────────────

def _cron_words(expr: str) -> str:
    """'30 20 * * *' -> 'daily at 20:30 UTC (02:00 IST)'. Other shapes are
    shown as the expression itself rather than guessed at."""
    parts = expr.split()
    daily = len(parts) == 5 and parts[2:] == ["*", "*", "*"]
    if daily and parts[0].isdigit() and parts[1].isdigit():
        utc = datetime(2000, 1, 1, int(parts[1]), int(parts[0]), tzinfo=UTC)
        ist = utc + timedelta(hours=5, minutes=30)
        return f"daily at {utc:%H:%M} UTC ({ist:%H:%M} IST)"
    return expr


def next_cron(expr: str, now: datetime) -> str | None:
    """The next daily firing of 'M H * * *', ISO. None for other shapes."""
    parts = expr.split()
    if not (len(parts) == 5 and parts[2:] == ["*", "*", "*"]
            and parts[0].isdigit() and parts[1].isdigit()):
        return None
    nxt = now.replace(hour=int(parts[1]), minute=int(parts[0]), second=0, microsecond=0)
    if nxt <= now:
        nxt += timedelta(days=1)
    return nxt.isoformat()


def setup() -> dict:
    try:
        wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        return {"unreadable": f"{WORKFLOW_FILE}: {type(e).__name__}"}
    # PyYAML reads the bare key `on:` as boolean True.
    on = wf.get("on", wf.get(True)) or {}
    crons = [c.get("cron") for c in (on.get("schedule") or []) if c.get("cron")]
    job = next(iter((wf.get("jobs") or {}).values()), {}) or {}
    raw = WORKFLOW.read_text(encoding="utf-8")
    deadline = re.search(r"--deadline-minutes\s+(\d+)", raw)
    secrets = sorted(set(re.findall(r"secrets\.([A-Z0-9_]+)", raw)))
    variables = sorted(set(re.findall(r"vars\.([A-Z0-9_]+)", raw)))
    dispatch = on.get("workflow_dispatch") or {}
    return {
        "workflow": wf.get("name"),
        "file": f".github/workflows/{WORKFLOW_FILE}",
        "crons": [{"expr": c, "words": _cron_words(c)} for c in crons],
        "manual_run": "workflow_dispatch" in on,
        "manual_inputs": sorted((dispatch.get("inputs") or {}).keys()),
        "runs_on": job.get("runs-on"),
        "timeout_minutes": job.get("timeout-minutes"),
        "deadline_minutes": int(deadline.group(1)) if deadline else None,
        "one_at_a_time": bool((wf.get("concurrency") or {}).get("group")),
        "secrets": [s for s in secrets if s != "GITHUB_TOKEN"],
        "variables": variables,
    }


def policy() -> dict:
    from judge import scheduler

    try:
        p = scheduler.policy()
    except scheduler.SchedulerPolicyError as e:
        return {"unreadable": str(e)}
    try:
        status = (yaml.safe_load((ROOT / "contract" / "scheduler.yaml").read_text(
            encoding="utf-8")) or {}).get("status")
    except (OSError, yaml.YAMLError):
        status = None
    return {"cadence_days": p.cadence_days, "first_fetch_thread_cap": p.first_fetch_thread_cap,
            "refresh_thread_cap": p.refresh_thread_cap, "status": status}


# ── the queue, with the runner's own selection ─────────────────────────────

def queue(conn) -> dict:
    from judge import scheduler
    from scripts.run_scheduled_fetches import due_rows

    rows = due_rows(conn)
    due = scheduler.rank_due(rows, datetime.now(UTC))
    due_ids = {d.model_version_id for d in due}
    return {
        "due": [{"model_version_id": d.model_version_id, "name": d.display_name,
                 "reason": d.reason, "thread_cap": d.thread_cap,
                 "last_success": d.last_success.isoformat() if d.last_success else None}
                for d in due],
        "not_due": [{"model_version_id": r["model_version_id"], "name": r["display_name"],
                     "last_success": r["last_success"].isoformat() if r["last_success"] else None}
                    for r in rows if r["model_version_id"] not in due_ids and r.get("in_window")],
        "tracked": len(rows),
    }


# ── GitHub: the switch and the scheduled runs ──────────────────────────────

def _gh(path: str) -> tuple[int, Any]:
    import httpx

    hit = _cache.get(path)
    if hit and time.monotonic() - hit[0] < CACHE_S:
        return hit[1]
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = httpx.get(f"{API}{path}", headers=headers, timeout=10)
        out = (r.status_code, r.json() if r.content else None)
    except (httpx.HTTPError, ValueError) as e:
        out = (0, {"message": type(e).__name__})
    _cache[path] = (time.monotonic(), out)
    return out


def runs(slug: str, limit: int = 15) -> dict:
    code, body = _gh(f"/repos/{slug}/actions/workflows/{WORKFLOW_FILE}/runs?per_page={limit}")
    if code != 200:
        return {"runs": [], "unreadable": f"GitHub answered {code or 'nothing'}"}
    out = []
    for r in (body or {}).get("workflow_runs", [])[:limit]:
        start = r.get("run_started_at") or r.get("created_at")
        end = r.get("updated_at") if r.get("status") == "completed" else None
        mins = None
        if start and end:
            try:
                t0 = datetime.fromisoformat(start.replace("Z", "+00:00"))
                t1 = datetime.fromisoformat(end.replace("Z", "+00:00"))
                mins = round((t1 - t0).total_seconds() / 60, 1)
            except ValueError:
                mins = None
        out.append({"id": r.get("id"), "number": r.get("run_number"), "event": r.get("event"),
                    "status": r.get("status"), "conclusion": r.get("conclusion"),
                    "started_at": start, "minutes": mins, "url": r.get("html_url")})
    return {"runs": out}


def overview(conn) -> dict:
    slug = repo_slug()
    s = setup()
    out: dict[str, Any] = {"setup": s, "policy": policy(), "repo": slug}
    try:
        out["queue"] = queue(conn)
    except Exception as e:  # noqa: BLE001 - the rest of the panel still answers
        out["queue"] = {"unreadable": type(e).__name__}
    if slug:
        out["github"] = runs(slug)
        out["links"] = {
            "workflow": f"https://github.com/{slug}/actions/workflows/{WORKFLOW_FILE}",
            "secrets": f"https://github.com/{slug}/settings/secrets/actions",
        }
    else:
        out["github"] = {"runs": [], "unreadable": "no GitHub remote found"}
    crons = (s.get("crons") or []) if isinstance(s, dict) else []
    out["next_run"] = next_cron(crons[0]["expr"], datetime.now(UTC)) if crons else None
    return out
