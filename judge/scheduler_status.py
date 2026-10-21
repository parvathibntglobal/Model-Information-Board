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
    """owner/name of the repository, or None.

    GITHUB_REPOSITORY first: THE DEPLOYED BACKEND HAS NO `.git` (.dockerignore
    leaves it out), so on Railway this setting is the only way the panel knows
    which repository's runs to read - without it the log said "no GitHub
    remote found" while the schedule ran (found 2026-10-21). Then git itself,
    which also works in a worktree, whose `.git` is a file, not a directory.
    """
    env = os.getenv("GITHUB_REPOSITORY", "").strip()
    if env:
        return env
    import subprocess

    try:
        url = subprocess.run(["git", "-C", str(ROOT), "config", "--get", "remote.origin.url"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    hit = re.search(r"github\.com[:/]([^/\s]+/[^/\s]+?)(?:\.git)?$", url)
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


def first_firing_after(expr: str, after: datetime) -> str | None:
    """The first daily firing of 'M H * * *' at or after `after`, ISO."""
    parts = expr.split()
    if not (len(parts) == 5 and parts[2:] == ["*", "*", "*"]
            and parts[0].isdigit() and parts[1].isdigit()):
        return None
    nxt = after.replace(hour=int(parts[1]), minute=int(parts[0]), second=0, microsecond=0)
    if nxt < after:
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
    return {"cadence_hours": p.cadence_hours, "first_fetch_thread_cap": p.first_fetch_thread_cap,
            "refresh_thread_cap": p.refresh_thread_cap, "status": status}


# ── the queue, with the runner's own selection ─────────────────────────────

def queue(conn) -> dict:
    from judge import scheduler
    from scripts.run_scheduled_fetches import due_rows

    rows = due_rows(conn)
    due = scheduler.rank_due(rows, datetime.now(UTC))
    due_ids = {d.model_version_id for d in due}
    cadence = timedelta(hours=scheduler.policy().cadence_hours)
    crons = setup().get("crons") or []
    cron = crons[0]["expr"] if crons else None
    return {
        "due": [{"model_version_id": d.model_version_id, "name": d.display_name,
                 "reason": d.reason, "thread_cap": d.thread_cap,
                 "last_success": d.last_success.isoformat() if d.last_success else None}
                for d in due],
        # WHEN EACH IS NEXT DUE, and the first scheduled run at or after that -
        # the cadence from the contract, the cron from the workflow file, so the
        # panel restates neither. None where either is unknown, never a guess.
        "not_due": [{"model_version_id": r["model_version_id"], "name": r["display_name"],
                     "last_success": r["last_success"].isoformat() if r["last_success"] else None,
                     "next_due": _next_due(r["last_success"], cadence),
                     "next_run": (first_firing_after(cron, _next_due_dt(r["last_success"], cadence))
                                  if cron and r["last_success"] else None)}
                    for r in rows if r["model_version_id"] not in due_ids and r.get("in_window")],
        "tracked": len(rows),
    }


def _next_due_dt(last: datetime | None, cadence: timedelta) -> datetime | None:
    return last + cadence if last else None


def _next_due(last: datetime | None, cadence: timedelta) -> str | None:
    d = _next_due_dt(last, cadence)
    return d.isoformat() if d else None


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


def switch(slug: str) -> dict:
    """The repository variable SCHEDULER_ENABLED: what actually turns the
    nightly run on (the workflow's gate wants exactly `1`).

    SHOWN SINCE 2026-10-21 - it was left out on 2026-10-06 because reading it
    needs a token allowed to read repository variables. Where the backend's
    GITHUB_TOKEN is not, this says so: "unreadable" is never shown as "off"
    (rule 6), because a switch nobody can read is not a switch that is off.
    """
    code, body = _gh(f"/repos/{slug}/actions/variables/SCHEDULER_ENABLED")
    if code == 200 and isinstance(body, dict):
        value = str(body.get("value") or "")
        return {"state": "on" if value.strip() == "1" else "off", "value": value,
                "updated_at": body.get("updated_at")}
    return {"unreadable": f"GitHub answered {code or 'nothing'}: the backend's GITHUB_TOKEN "
                          "is missing or may not read repository variables"}


#: The runner's summary comment (judge/scheduler.summarise_runs) starts with this.
SUMMARY_HEAD = "**Scheduled fetch:"
SUMMARY_COLUMNS = ("model", "outcome", "documents_appended", "threads_read",
                   "quotes_verified", "unreadable_here", "harvest_errors")


def parse_summary(body: str) -> list[dict]:
    """The rows of one summary table. A `-` cell is None: the run did not
    report it, which is not zero (the summary's own footnote says the same)."""
    rows = []
    for line in (body or "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.startswith("|") or len(cells) != len(SUMMARY_COLUMNS):
            continue
        if cells[0] in ("Model", "") or set(cells[0]) <= {"-"}:
            continue
        row = {}
        for key, cell in zip(SUMMARY_COLUMNS, cells, strict=True):
            if cell == "-":
                row[key] = None
            elif key in ("model", "outcome", "harvest_errors"):
                row[key] = cell
            else:
                row[key] = int(cell) if cell.isdigit() else cell
        rows.append(row)
    return rows


def summaries(slug: str, issue: str) -> list[dict]:
    """The runner's summary comments on SCHEDULER_ISSUE, newest page, parsed.
    The issue is public, so these need no token."""
    code, meta = _gh(f"/repos/{slug}/issues/{issue}")
    if code != 200 or not isinstance(meta, dict):
        return []
    per = 50
    last_page = max(1, -(-int(meta.get("comments") or 0) // per))
    out = []
    for page in sorted({max(1, last_page - 1), last_page}):
        code, body = _gh(f"/repos/{slug}/issues/{issue}/comments?per_page={per}&page={page}")
        if code != 200 or not isinstance(body, list):
            continue
        for c in body:
            text = c.get("body") or ""
            if text.startswith(SUMMARY_HEAD):
                out.append({"at": c.get("created_at"), "url": c.get("html_url"),
                            "rows": parse_summary(text)})
    return out


def attach_summaries(run_list: list[dict], posted: list[dict]) -> None:
    """Give each finished run the summary its runner posted while it ran.

    MATCHED BY TIME: a comment created after the run started and no later than
    15 minutes after it ended. A finished run with none gets `summary: None` -
    it fetched nothing it reported (a run with the switch off ends in under a
    minute and posts nothing), which the panel says in those words rather than
    showing the bare "success" GitHub gives every such run.
    """
    def ts(v):
        return datetime.fromisoformat(v.replace("Z", "+00:00")) if v else None

    for r in run_list:
        if r.get("status") != "completed":
            continue
        start = ts(r.get("started_at"))
        end = start + timedelta(minutes=(r.get("minutes") or 0) + 15) if start else None
        hit = next((p for p in posted
                    if start and ts(p["at"]) and start <= ts(p["at"]) <= end), None)
        if hit is None:
            r["summary"] = None
            continue
        rows = hit["rows"]
        r["summary"] = {
            "url": hit["url"], "models": len(rows),
            "ok": sum(1 for x in rows if x.get("outcome") == "ok"),
            "documents_appended": sum(x.get("documents_appended") or 0 for x in rows
                                      if isinstance(x.get("documents_appended"), int)),
            "quotes_verified": sum(x.get("quotes_verified") or 0 for x in rows
                                   if isinstance(x.get("quotes_verified"), int)),
            "rows": rows,
        }


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
        out["switch"] = switch(slug)
        issue = os.getenv("SCHEDULER_ISSUE", "").strip()
        if issue and out["github"].get("runs"):
            attach_summaries(out["github"]["runs"], summaries(slug, issue))
        elif not issue:
            # Said, not hidden: without the issue a run's results cannot be read.
            out["github"]["summaries_unreadable"] = "SCHEDULER_ISSUE is not set on this backend"
        out["links"] = {
            "workflow": f"https://github.com/{slug}/actions/workflows/{WORKFLOW_FILE}",
            "secrets": f"https://github.com/{slug}/settings/secrets/actions",
        }
    else:
        out["github"] = {"runs": [], "unreadable": "no repository known: set GITHUB_REPOSITORY "
                                                   "on this backend (owner/name)"}
        out["switch"] = {"unreadable": "no repository known"}
    crons = (s.get("crons") or []) if isinstance(s, dict) else []
    out["next_run"] = next_cron(crons[0]["expr"], datetime.now(UTC)) if crons else None
    return out
