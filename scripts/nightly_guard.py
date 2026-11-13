"""Run each nightly workflow once, in order, and stand down late duplicates.

    python scripts/nightly_guard.py --workflow <file>

The first job (`guard`) of each workflow in contract/nightly_guard.yaml. For a
start listed in `guard_events` it writes `run=false` to $GITHUB_OUTPUT, so the
workflow's main job is skipped, when:

* a `workflow_run` start: the run that finished ($GITHUB_EVENT_PATH) was not real
  nightly work for its own workflow;
* `waits_for` names a workflow whose nightly run is still going;
* this workflow already did real work tonight.

Otherwise `run=true`. A start not listed in `guard_events` (a hand start) always
runs. Uses the run's own GH_TOKEN, GITHUB_REPOSITORY, GITHUB_EVENT_NAME,
GITHUB_RUN_ID and GITHUB_EVENT_PATH; refuses rather than guesses when one is missing.

"Real work" = a run started by one of `counts_events` whose main `job` did not
end skipped; `nightly_dispatch` is a hand start whose run name ends
NIGHTLY_SUFFIX. A run the guard stood down does not count. A run whose main job
has not started yet counts only if it is OLDER than this one, so two runs that
start together cannot both stand down.

GitHub's `schedule` starts our runs 3 to 10 hours late (measured 2026-11-13; the
contract has the figures). anooj decided on 2026-11-13 against a timer outside
GitHub for now, so this orders the late runs rather than making them on time.

Standard library plus PyYAML only, so the guard job installs one package.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

CONTRACT = Path(__file__).resolve().parents[1] / "contract" / "nightly_guard.yaml"
API = "https://api.github.com"

# A hand start with this input stands in for the night's run; each workflow that
# counts `nightly_dispatch` declares the input and turns it into this run-name
# suffix. tests/test_nightly_guard.py pins the workflows to both.
NIGHTLY_INPUT = ("slot", "nightly")
NIGHTLY_SUFFIX = " (nightly)"

GUARDABLE = frozenset({"schedule", "workflow_run"})
COUNTABLE = frozenset({"schedule", "workflow_run", "nightly_dispatch"})


class GuardConfigError(ValueError):
    """contract/nightly_guard.yaml is missing a key or carries a wrong value."""


@dataclass(frozen=True)
class Entry:
    file: str
    job: str
    window_opens: tuple[int, int]
    waits_for: str | None
    guard_events: frozenset[str]
    counts_events: frozenset[str]


@dataclass(frozen=True)
class Trigger:
    """The verdict on the run that finished, for a `workflow_run` start."""

    ok: bool
    why: str
    created: datetime


def _events(v, allowed, where):
    if not isinstance(v, list) or not v or not set(v) <= allowed:
        raise GuardConfigError(
            f"{where} must be a non-empty list from {sorted(allowed)}, not {v!r}"
        )
    return frozenset(v)


def _hhmm(v, where) -> tuple[int, int]:
    try:
        if not isinstance(v, str) or len(v) != 5 or v[2] != ":":
            raise ValueError
        h, m = int(v[:2]), int(v[3:])
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError
    except ValueError:
        raise GuardConfigError(f'{where} must be "HH:MM" (UTC), not {v!r}') from None
    return h, m


REQUIRED = ("job", "window_opens_utc", "waits_for", "guard_events", "counts_events")


def parse_contract(raw) -> dict[str, Entry]:
    """Every key required, nothing defaulted (rule 12)."""
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("workflows"), dict)
        or not raw["workflows"]
    ):
        raise GuardConfigError("nightly_guard.yaml needs a non-empty `workflows` mapping")
    files = set(raw["workflows"])
    entries = {}
    for file, e in raw["workflows"].items():
        where = f"workflows.{file}"
        if not isinstance(e, dict):
            raise GuardConfigError(f"{where} must be a mapping")
        for key in REQUIRED:
            if key not in e:
                raise GuardConfigError(f"{where}: `{key}` is required (waits_for: null for none)")
        if not isinstance(e["job"], str) or not e["job"]:
            raise GuardConfigError(f"{where}.job must name the workflow's main job")
        waits = e["waits_for"]
        if waits is not None and (waits not in files or waits == file):
            raise GuardConfigError(
                f"{where}.waits_for must be null or another workflow listed here, not {waits!r}"
            )
        entries[file] = Entry(
            file=file,
            job=e["job"],
            window_opens=_hhmm(e["window_opens_utc"], f"{where}.window_opens_utc"),
            waits_for=waits,
            guard_events=_events(e["guard_events"], GUARDABLE, f"{where}.guard_events"),
            counts_events=_events(e["counts_events"], COUNTABLE, f"{where}.counts_events"),
        )
    return entries


def load_contract(path: Path = CONTRACT) -> dict[str, Entry]:
    return parse_contract(yaml.safe_load(path.read_text(encoding="utf-8")))


def window_start(entry: Entry, now: datetime) -> datetime:
    """The most recent `window_opens_utc` at or before `now`: never a rolling span."""
    h, m = entry.window_opens
    start = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return start if start <= now else start - timedelta(days=1)


def counted_start(entry: Entry, run: dict) -> bool:
    """Was `run` started in a way `entry.counts_events` counts? (Not: did it do work.)"""
    event = run.get("event")
    if event == "workflow_dispatch":
        title = str(run.get("display_title") or "")
        return "nightly_dispatch" in entry.counts_events and title.endswith(NIGHTLY_SUFFIX)
    return event in entry.counts_events


def _when(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(UTC)


def guard_decision(
    entry: Entry,
    event: str,
    now: datetime,
    did_real_work: Callable[[Entry, datetime], bool],
    *,
    trigger: Trigger | None = None,
    still_running: Callable[[str], tuple[bool, str]] | None = None,
) -> tuple[bool, str]:
    """(run?, why) for one run of `entry`'s workflow started by `event`."""
    if event not in entry.guard_events:
        return True, f"`{event}` is not a guarded start for {entry.file}"
    since = window_start(entry, now)
    if event == "workflow_run":
        if trigger is None:
            raise ValueError("a guarded workflow_run start needs the finished run's verdict")
        if not trigger.ok:
            return False, f"{trigger.why}; this `workflow_run` start of {entry.file} stands down"
        since = trigger.created
    if entry.waits_for is not None:
        if still_running is None:
            raise ValueError(
                f"{entry.file} waits for {entry.waits_for}; nothing asked whether it runs"
            )
        busy, why = still_running(entry.waits_for)
        if busy:
            return False, (
                f"{why}; its finish starts {entry.file}, so this `{event}` run stands down"
            )
    if did_real_work(entry, since):
        return False, (
            f"{entry.file} already did real work since {since:%Y-%m-%d %H:%M}Z; "
            f"this `{event}` run stands down (contract/nightly_guard.yaml)"
        )
    return True, f"no real run of {entry.file} since {since:%Y-%m-%d %H:%M}Z"


def trigger_verdict(
    entries: dict[str, Entry], finished: dict, main_job: Callable[[int, str], dict | None]
) -> Trigger:
    """Did the run that finished (the `workflow_run` payload) do real nightly work?

    Judged by ITS OWN workflow's `counts_events` and main job.
    """
    file = Path(str(finished.get("path") or "").split("@")[0]).name
    source = entries.get(file)
    if source is None:
        raise SystemExit(
            f"the finished run's workflow {file!r} is not in contract/nightly_guard.yaml; "
            "refusing to guess whether it was the night's run"
        )
    created = _when(finished["created_at"])
    label = f"{file} run {finished.get('id')} ({finished.get('display_title')!r})"
    if not counted_start(source, finished):
        return Trigger(
            False,
            f"{label} was started by `{finished.get('event')}` and is not a nightly start "
            "(a test run holds nothing off and starts nothing)",
            created,
        )
    job = main_job(int(finished["id"]), source.job)
    if job is None or job.get("conclusion") == "skipped":
        return Trigger(False, f"{label} stood down without running `{source.job}`", created)
    return Trigger(True, f"{label} ran `{source.job}` ({job.get('conclusion')})", created)


# ── GitHub ──────────────────────────────────────────────────────────────────


class GitHub:
    def __init__(self, token: str, repo: str):
        if not token or not repo or "/" not in repo:
            raise SystemExit(
                "a token and GITHUB_REPOSITORY (owner/name) are required; refusing to guess"
            )
        self.token, self.repo = token, repo

    def get(self, path: str):
        req = urllib.request.Request(
            API + path,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "mib-nightly-guard",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())


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


def running_checker(gh, entries: dict[str, Entry]) -> Callable[[str], tuple[bool, str]]:
    """Is a nightly run of `file` still going? A run still in its own guard counts:
    if it is about to stand down, the night's real run of it already started us."""
    main_job = main_job_reader(gh)

    def still_running(file: str) -> tuple[bool, str]:
        other = entries[file]
        runs = gh.get(f"/repos/{gh.repo}/actions/workflows/{file}/runs?per_page=20")[
            "workflow_runs"
        ]
        for r in runs:
            if r["status"] == "completed" or not counted_start(other, r):
                continue
            job = main_job(r["id"], other.job)
            if job is not None and job["status"] == "completed" and job["conclusion"] == "skipped":
                continue
            return True, f"{file} run {r['id']} ({r.get('display_title')!r}) is still going"
        return False, f"no nightly run of {file} is going"

    return still_running


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--workflow", required=True)
    args = ap.parse_args(argv)
    entries = load_contract()
    entry = entries.get(args.workflow)
    if entry is None:
        raise SystemExit(
            f"{args.workflow} is not in contract/nightly_guard.yaml; refusing to guess"
        )
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    run_id = int(os.environ.get("GITHUB_RUN_ID", "0")) or None
    gh = GitHub(os.environ.get("GH_TOKEN", ""), os.environ.get("GITHUB_REPOSITORY", ""))
    trigger = None
    if event == "workflow_run" and event in entry.guard_events:
        payload_path = os.environ.get("GITHUB_EVENT_PATH", "")
        if not payload_path:
            raise SystemExit("a workflow_run start without GITHUB_EVENT_PATH; refusing to guess")
        finished = json.loads(Path(payload_path).read_text(encoding="utf-8"))["workflow_run"]
        trigger = trigger_verdict(entries, finished, main_job_reader(gh))
    run, why = guard_decision(
        entry,
        event,
        datetime.now(UTC),
        real_work_checker(gh, this_run_id=run_id),
        trigger=trigger,
        still_running=running_checker(gh, entries),
    )
    print(("::notice::" if not run else "") + why)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"run={'true' if run else 'false'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
