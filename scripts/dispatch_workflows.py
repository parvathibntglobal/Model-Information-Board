"""Start the daily workflows on time, and stand down late duplicates.

GitHub's `schedule` trigger starts our workflows 3 to 10 hours late (measured
2026-11-13; contract/dispatch_schedule.yaml has the figures). A
`workflow_dispatch` start is not delayed. So:

    python scripts/dispatch_workflows.py dispatch [--dry-run]
        Run every 10 minutes by a cron WE host (docs/ops-dispatcher.md). Starts
        each workflow whose `dispatch_at_utc` has passed (within
        `catch_up_minutes`) unless it already did real work since its most
        recent `window_opens_utc`. Starts it with `slot: nightly`, which the
        workflow puts in its run name. Needs GITHUB_DISPATCH_TOKEN (allowed to
        start workflows) and GITHUB_REPOSITORY ("owner/name").

    python scripts/dispatch_workflows.py guard --workflow <file>
        The first job of each workflow in the schedule. For a trigger listed in
        `guard_events`, writes `run=false` to $GITHUB_OUTPUT when the workflow
        already did real work in the window, so the main job is skipped. On a
        `workflow_run` start it first reads the run that finished
        ($GITHUB_EVENT_PATH) and stands down unless that run was real nightly
        work for its own workflow. Uses the run's own GH_TOKEN,
        GITHUB_REPOSITORY, GITHUB_EVENT_NAME, GITHUB_RUN_ID.

"Real work" = a run started by one of `counts_events` whose main `job` did not
end skipped; `nightly_dispatch` is a `workflow_dispatch` start whose run name
ends NIGHTLY_SUFFIX. A run the guard stood down does not count. A run whose main
job has not started yet counts only if it is OLDER than this one, so two runs
that start together cannot both stand down.

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

# The input the dispatcher sends, and what each dispatched workflow's `run-name`
# turns it into. tests/test_dispatch_workflows.py pins the workflows to both.
NIGHTLY_INPUTS = {"slot": "nightly"}
NIGHTLY_SUFFIX = " (nightly)"

GUARDABLE = frozenset({"schedule", "workflow_run"})
COUNTABLE = frozenset({"schedule", "workflow_run", "nightly_dispatch"})


class ScheduleError(ValueError):
    """contract/dispatch_schedule.yaml is missing a key or carries a wrong value."""


@dataclass(frozen=True)
class Entry:
    file: str
    job: str
    dispatch_at: tuple[int, int] | None
    window_opens: tuple[int, int]
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


def _events(v, allowed, where):
    if not isinstance(v, list) or not v or not set(v) <= allowed:
        raise ScheduleError(f"{where} must be a non-empty list from {sorted(allowed)}, not {v!r}")
    return frozenset(v)


def _hhmm(v, where) -> tuple[int, int]:
    try:
        if not isinstance(v, str) or len(v) != 5 or v[2] != ":":
            raise ValueError
        h, m = int(v[:2]), int(v[3:])
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError
    except ValueError:
        raise ScheduleError(f'{where} must be "HH:MM" (UTC), not {v!r}') from None
    return h, m


def _minutes_after(later: tuple[int, int], earlier: tuple[int, int]) -> int:
    """Minutes from `earlier` forward to `later`, on a 24-hour clock."""
    return ((later[0] - earlier[0]) * 60 + later[1] - earlier[1]) % (24 * 60)


REQUIRED = ("job", "dispatch_at_utc", "window_opens_utc", "guard_events", "counts_events")


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
        for key in REQUIRED:
            if key not in e:
                raise ScheduleError(
                    f"{where}: `{key}` is required (dispatch_at_utc: null for never)"
                )
        if not isinstance(e["job"], str) or not e["job"]:
            raise ScheduleError(f"{where}.job must name the workflow's main job")
        at = e["dispatch_at_utc"]
        if at is not None:
            at = _hhmm(at, f"{where}.dispatch_at_utc")
        opens = _hhmm(e["window_opens_utc"], f"{where}.window_opens_utc")
        if at is not None and _minutes_after(at, opens) + catch_up >= 24 * 60:
            raise ScheduleError(
                f"{where}: window_opens_utc {e['window_opens_utc']} opens too long before "
                f"dispatch_at_utc {e['dispatch_at_utc']}: a dispatch late in its "
                f"{catch_up}-minute catch-up would look back into the previous day's window"
            )
        entries[file] = Entry(
            file=file,
            job=e["job"],
            dispatch_at=at,
            window_opens=opens,
            guard_events=_events(e["guard_events"], GUARDABLE, f"{where}.guard_events"),
            counts_events=_events(e["counts_events"], COUNTABLE, f"{where}.counts_events"),
        )
    return Schedule(catch_up_minutes=catch_up, entries=entries)


def load_schedule(path: Path = SCHEDULE) -> Schedule:
    return parse_schedule(yaml.safe_load(path.read_text(encoding="utf-8")))


def latest_slot(now: datetime, at: tuple[int, int]) -> datetime:
    """The most recent `at` (UTC) at or before `now`."""
    slot = now.replace(hour=at[0], minute=at[1], second=0, microsecond=0)
    return slot if slot <= now else slot - timedelta(days=1)


def window_start(entry: Entry, now: datetime) -> datetime:
    """Real work counts from here: the most recent `window_opens_utc`, never a rolling span."""
    return latest_slot(now, entry.window_opens)


def counted_start(entry: Entry, run: dict) -> bool:
    """Was `run` started in a way `entry.counts_events` counts? (Not: did it do work.)"""
    event = run.get("event")
    if event == "workflow_dispatch":
        title = str(run.get("display_title") or "")
        return "nightly_dispatch" in entry.counts_events and title.endswith(NIGHTLY_SUFFIX)
    return event in entry.counts_events


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
        since = window_start(e, now)
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
    entry: Entry,
    event: str,
    now: datetime,
    did_real_work: Callable[[Entry, datetime], bool],
    trigger: tuple[bool, str] | None = None,
) -> tuple[bool, str]:
    """(run?, why) for one run of `entry`'s workflow started by `event`.

    `trigger` is the verdict on the run that finished, for a `workflow_run`
    start (trigger_verdict); a guarded `workflow_run` without one is refused.
    """
    if event not in entry.guard_events:
        return True, f"`{event}` is not a guarded trigger for {entry.file}"
    if event == "workflow_run":
        if trigger is None:
            raise ValueError("a guarded workflow_run start needs the finished run's verdict")
        ok, why = trigger
        if not ok:
            return False, f"{why}; this `workflow_run` start of {entry.file} stands down"
    since = window_start(entry, now)
    if did_real_work(entry, since):
        return False, (
            f"{entry.file} already did real work since {since:%Y-%m-%d %H:%M}Z; "
            f"this `{event}` run stands down (contract/dispatch_schedule.yaml)"
        )
    return True, f"no real run of {entry.file} since {since:%Y-%m-%d %H:%M}Z"


def trigger_verdict(
    schedule: Schedule, finished: dict, main_job: Callable[[int, str], dict | None]
) -> tuple[bool, str]:
    """Did the run that finished (the `workflow_run` payload) do real nightly work?

    `main_job(run_id, job_name)` returns that run's job, or None. The finished
    run is judged by ITS OWN workflow's `counts_events` and main job.
    """
    file = Path(str(finished.get("path") or "").split("@")[0]).name
    source = schedule.entries.get(file)
    if source is None:
        raise SystemExit(
            f"the finished run's workflow {file!r} is not in contract/dispatch_schedule.yaml; "
            "refusing to guess whether it was the night's run"
        )
    label = f"{file} run {finished.get('id')} ({finished.get('display_title')!r})"
    if not counted_start(source, finished):
        return False, (
            f"{label} was started by `{finished.get('event')}` and is not a nightly start "
            "(a test run holds nothing off and starts nothing)"
        )
    job = main_job(int(finished["id"]), source.job)
    if job is None or job.get("conclusion") == "skipped":
        return False, f"{label} stood down without running `{source.job}`"
    return True, f"{label} ran `{source.job}` ({job.get('conclusion')})"


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
        self._req(
            "POST",
            f"/repos/{self.repo}/actions/workflows/{file}/dispatches",
            {"ref": ref, "inputs": dict(NIGHTLY_INPUTS)},
        )


def main_job_reader(gh) -> Callable[[int, str], dict | None]:
    def main_job(run_id: int, name: str) -> dict | None:
        jobs = gh.get(f"/repos/{gh.repo}/actions/runs/{run_id}/jobs?per_page=50")["jobs"]
        return next((j for j in jobs if j["name"] == name), None)

    return main_job


def real_work_checker(gh, *, this_run_id: int | None = None):
    main_job = main_job_reader(gh)

    def did_real_work(entry: Entry, since: datetime) -> bool:
        created = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        runs = gh.get(
            f"/repos/{gh.repo}/actions/workflows/{entry.file}/runs"
            f"?created=%3E%3D{created}&per_page=50"
        )["workflow_runs"]
        for r in runs:
            if r["id"] == this_run_id or not counted_start(entry, r):
                continue
            job = main_job(r["id"], entry.job)
            if job is None:
                # The main job not created yet: the run is still in its guard
                # job. It counts only if it is older than this run.
                if this_run_id is not None and r["id"] < this_run_id:
                    return True
                continue
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
    trigger = None
    if event == "workflow_run" and event in entry.guard_events:
        payload_path = os.environ.get("GITHUB_EVENT_PATH", "")
        if not payload_path:
            raise SystemExit("a workflow_run start without GITHUB_EVENT_PATH; refusing to guess")
        finished = json.loads(Path(payload_path).read_text(encoding="utf-8"))["workflow_run"]
        trigger = trigger_verdict(schedule, finished, main_job_reader(gh))
    run, why = guard_decision(entry, event, now, real_work_checker(gh, this_run_id=run_id), trigger)
    print(("::notice::" if not run else "") + why)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"run={'true' if run else 'false'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
