"""Start the daily workflows on time, and stand down late duplicates.

GitHub's `schedule` trigger starts our workflows 3 to 10 hours late (measured
2026-11-13; contract/dispatch_schedule.yaml has the figures). A
`workflow_dispatch` start is not delayed. So:

    python scripts/dispatch_workflows.py dispatch [--dry-run]
        Run every 10 minutes by a cron WE host (docs/ops-dispatcher.md). Starts
        each workflow whose `dispatch_at_utc` has passed (within
        `catch_up_minutes`) unless it already did real work within
        `skip_if_ran_within_hours`. Needs GITHUB_DISPATCH_TOKEN (allowed to start
        workflows) and GITHUB_REPOSITORY ("owner/name").

    python scripts/dispatch_workflows.py guard --workflow <file>
        The first job of each workflow in the schedule. For a trigger listed in
        `guard_events`, writes `run=false` to $GITHUB_OUTPUT when the workflow
        already did real work in the window, so the main job is skipped. Uses
        the run's own GH_TOKEN, GITHUB_REPOSITORY, GITHUB_EVENT_NAME, GITHUB_RUN_ID.

"Real work" = a run started by one of `counts_events` whose main `job` did not
end skipped. A run the guard stood down does not count. A run whose main job has
not started yet counts only if it is OLDER than this one, so two runs that start
together cannot both stand down.

Standard library plus PyYAML only, so the guard job installs one package.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

SCHEDULE = Path(__file__).resolve().parents[1] / "contract" / "dispatch_schedule.yaml"
API = "https://api.github.com"
EVENTS = frozenset({"schedule", "workflow_dispatch", "workflow_run"})


class ScheduleError(ValueError):
    """contract/dispatch_schedule.yaml is missing a key or carries a wrong value."""


@dataclass(frozen=True)
class Entry:
    file: str
    job: str
    dispatch_at: tuple[int, int] | None
    window_hours: int
    guard_events: frozenset[str]
    counts_events: frozenset[str]


@dataclass(frozen=True)
class Schedule:
    catch_up_minutes: int
    entries: dict[str, Entry]


def _positive_int(v, where):
    if isinstance(v, bool) or not isinstance(v, int) or v < 1:
        raise ScheduleError(f"{where} must be a positive integer, not {v!r}")
    return v


def _events(v, where):
    if not isinstance(v, list) or not v or not set(v) <= EVENTS:
        raise ScheduleError(f"{where} must be a non-empty list from {sorted(EVENTS)}, not {v!r}")
    return frozenset(v)


def parse_schedule(raw) -> Schedule:
    """Every key required, nothing defaulted (rule 12)."""
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("workflows"), dict)
        or not raw["workflows"]
    ):
        raise ScheduleError("dispatch_schedule.yaml needs a non-empty `workflows` mapping")
    catch_up = _positive_int(raw.get("catch_up_minutes"), "`catch_up_minutes`")
    entries = {}
    for file, e in raw["workflows"].items():
        where = f"workflows.{file}"
        if not isinstance(e, dict):
            raise ScheduleError(f"{where} must be a mapping")
        for key in (
            "job",
            "dispatch_at_utc",
            "skip_if_ran_within_hours",
            "guard_events",
            "counts_events",
        ):
            if key not in e:
                raise ScheduleError(
                    f"{where}: `{key}` is required (dispatch_at_utc: null for never)"
                )
        if not isinstance(e["job"], str) or not e["job"]:
            raise ScheduleError(f"{where}.job must name the workflow's main job")
        at = e["dispatch_at_utc"]
        if at is not None:
            try:
                h, m = (int(x) for x in str(at).split(":"))
                if not (0 <= h < 24 and 0 <= m < 60) or len(str(at)) != 5:
                    raise ValueError
            except ValueError:
                raise ScheduleError(
                    f'{where}.dispatch_at_utc must be "HH:MM" or null, not {at!r}'
                ) from None
            at = (h, m)
        entries[file] = Entry(
            file=file,
            job=e["job"],
            dispatch_at=at,
            window_hours=_positive_int(
                e["skip_if_ran_within_hours"], f"{where}.skip_if_ran_within_hours"
            ),
            guard_events=_events(e["guard_events"], f"{where}.guard_events"),
            counts_events=_events(e["counts_events"], f"{where}.counts_events"),
        )
    return Schedule(catch_up_minutes=catch_up, entries=entries)


def load_schedule(path: Path = SCHEDULE) -> Schedule:
    return parse_schedule(yaml.safe_load(path.read_text(encoding="utf-8")))


def latest_slot(now: datetime, at: tuple[int, int]) -> datetime:
    """The most recent `at` (UTC) at or before `now`."""
    slot = now.replace(hour=at[0], minute=at[1], second=0, microsecond=0)
    return slot if slot <= now else slot - timedelta(days=1)


def to_dispatch(
    schedule: Schedule, now: datetime, did_real_work: Callable[[Entry, datetime], bool]
) -> list[tuple[str, str]]:
    """[(file, reason)] to start now. `did_real_work(entry, since)` asks GitHub."""
    out = []
    for e in schedule.entries.values():
        if e.dispatch_at is None:
            continue
        slot = latest_slot(now, e.dispatch_at)
        if now - slot > timedelta(minutes=schedule.catch_up_minutes):
            continue
        since = now - timedelta(hours=e.window_hours)
        if did_real_work(e, since):
            continue
        out.append(
            (
                e.file,
                f"slot {slot:%H:%M}Z passed {int((now - slot).total_seconds() // 60)} min ago; "
                f"no real run since {since:%Y-%m-%d %H:%M}Z",
            )
        )
    return out


def guard_decision(
    entry: Entry, event: str, now: datetime, did_real_work: Callable[[Entry, datetime], bool]
) -> tuple[bool, str]:
    """(run?, why) for one run of `entry`'s workflow started by `event`."""
    if event not in entry.guard_events:
        return True, f"`{event}` is not a guarded trigger for {entry.file}"
    since = now - timedelta(hours=entry.window_hours)
    if did_real_work(entry, since):
        return False, (
            f"{entry.file} already did real work since {since:%Y-%m-%d %H:%M}Z; "
            f"this `{event}` run stands down (contract/dispatch_schedule.yaml)"
        )
    return True, f"no real run of {entry.file} since {since:%Y-%m-%d %H:%M}Z"


# ── GitHub ──────────────────────────────────────────────────────────────────


class GitHub:
    def __init__(self, token: str, repo: str):
        if not token or not repo or "/" not in repo:
            raise SystemExit(
                "a token and GITHUB_REPOSITORY (owner/name) are required; refusing to guess"
            )
        self.token, self.repo = token, repo

    def _req(self, method: str, path: str, body: dict | None = None):
        req = urllib.request.Request(
            API + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "mib-dispatcher",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        return json.loads(data) if data else None

    def get(self, path: str):
        return self._req("GET", path)

    def dispatch(self, file: str, ref: str = "main") -> None:
        self._req("POST", f"/repos/{self.repo}/actions/workflows/{file}/dispatches", {"ref": ref})


def real_work_checker(gh: GitHub, *, this_run_id: int | None = None):
    def did_real_work(entry: Entry, since: datetime) -> bool:
        created = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        runs = gh.get(
            f"/repos/{gh.repo}/actions/workflows/{entry.file}/runs"
            f"?created=%3E%3D{created}&per_page=50"
        )["workflow_runs"]
        for r in runs:
            if r["id"] == this_run_id or r["event"] not in entry.counts_events:
                continue
            jobs = gh.get(f"/repos/{gh.repo}/actions/runs/{r['id']}/jobs?per_page=50")["jobs"]
            main = [j for j in jobs if j["name"] == entry.job]
            if not main:
                # The main job not created yet: the run is still in its guard
                # job. It counts only if it is older than this run.
                if this_run_id is not None and r["id"] < this_run_id:
                    return True
                continue
            job = main[0]
            if job["status"] == "completed":
                if job["conclusion"] != "skipped":
                    return True
            elif this_run_id is None or r["id"] < this_run_id or job["status"] == "in_progress":
                return True
        return False

    return did_real_work


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dispatch")
    d.add_argument("--dry-run", action="store_true")
    g = sub.add_parser("guard")
    g.add_argument("--workflow", required=True)
    args = ap.parse_args(argv)
    schedule = load_schedule()
    now = datetime.now(UTC)
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if args.cmd == "dispatch":
        gh = GitHub(os.environ.get("GITHUB_DISPATCH_TOKEN", ""), repo)
        due = to_dispatch(schedule, now, real_work_checker(gh))
        if not due:
            print(f"{now:%Y-%m-%d %H:%M}Z nothing due")
        for file, why in due:
            if args.dry_run:
                print(f"would start {file}: {why}")
                continue
            try:
                gh.dispatch(file)
                print(f"started {file}: {why}")
            except urllib.error.HTTPError as e:
                print(f"FAILED to start {file}: HTTP {e.code}", file=sys.stderr)
                return 1
        return 0

    entry = schedule.entries.get(args.workflow)
    if entry is None:
        raise SystemExit(
            f"{args.workflow} is not in contract/dispatch_schedule.yaml; refusing to guess"
        )
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    run_id = int(os.environ.get("GITHUB_RUN_ID", "0")) or None
    gh = GitHub(os.environ.get("GH_TOKEN", ""), repo)
    run, why = guard_decision(entry, event, now, real_work_checker(gh, this_run_id=run_id))
    print(("::notice::" if not run else "") + why)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"run={'true' if run else 'false'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
