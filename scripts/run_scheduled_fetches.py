#!/usr/bin/env python
"""Run the per-model fetches that are due, one at a time, within the daily cap.

⚠ DISABLED BY DEFAULT, AND THAT IS THE POINT. It refuses to harvest unless
  `SCHEDULER_ENABLED` is set to a truthy value. Nothing here runs on a schedule
  until a person sets that variable on the service - which is deliberate while
  `contract/sources.yaml`'s undertaking is being made honest again (a public
  repo held a Reddit-derived article, so `derived_publication: false` reads true
  while being false, and the seven non-GitHub rulings rest on it). Until the
  basis is honest, this stays off.

  TWO INDEPENDENT GUARDS, so neither alone is load-bearing:
    - this switch (off), which stops the scheduler running at all;
    - the terms gate inside `fetch_model`, which refuses a source whose ruling
      does not hold - once the undertaking is flipped to void, every non-GitHub
      arm skips itself with its reason (#491), whatever this switch says.

WHAT IS CODE (here) AND WHAT IS THE SERVICE'S (a person's):
    code    : the selector (judge/scheduler.rank_due), this runner, the
              per-source scope, the host-free summary.
    service : the GitHub Action .github/workflows/scheduled-fetches.yml
              (daily, 02:00 IST; Railway was the plan until 2026-10-06), with
              its secrets and variables, SCHEDULER_ISSUE naming the issue it
              posts to, and SCHEDULER_ENABLED. Documented in
              docs/ops-scheduled-fetches.md.

READS read-only to PLAN; the WRITES are `fetch_model`'s, which carries the
fixture gate (#485). This process opens no write transaction of its own.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TRUTHY = {"1", "true", "yes", "on"}


def enabled() -> bool:
    return (os.getenv("SCHEDULER_ENABLED") or "").strip().lower() in TRUTHY


def _read_only_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is not set; refusing rather than planning against nothing")
    sep = "&" if "?" in dsn else "?"
    return dsn + sep + "options=-c%20default_transaction_read_only%3Don"


def due_rows(conn) -> list[dict]:
    """The tracked, in-window models with their last SUCCESSFUL fetch.

    Tracked comes from `contract/tracked_models.yaml`; the last success comes
    from `fetch_log` (an `end` record with status ok). Matching the registry row
    by canonical id OR row id, as the models page does.
    """
    from judge.tracked import all_tracked

    # Hand-written entries plus new arrivals the `auto_track` rule admits, so a
    # model the poll inserts is due for a first fetch with no PR in between.
    tracked = [m for m in all_tracked(conn) if m.registry]
    ids = [m.registry for m in tracked]
    reg = {r[0]: r for r in conn.execute(
        "SELECT canonical_id, id, display_name, in_window FROM model_version "
        "WHERE canonical_id = ANY(%s) OR id = ANY(%s)", (ids, ids)).fetchall()}
    # last successful fetch per model_version_id
    last = {r[0]: r[1] for r in conn.execute(
        "SELECT r.model_version_id, max(e.at) "
        "FROM fetch_log r JOIN fetch_log e ON e.run_id = r.run_id AND e.kind = 'end' "
        "WHERE r.kind = 'run' AND (e.payload->>'status') = 'ok' "
        "GROUP BY r.model_version_id").fetchall()}
    rows = []
    for m in tracked:
        hit = reg.get(m.registry)
        if hit is None:
            continue  # tracked but not yet a registry row - nothing to fetch
        canonical, mv_id, display, in_window = hit
        rows.append({
            "model_version_id": mv_id,
            "display_name": display or m.name,
            "tracked": True,
            "in_window": bool(in_window),
            "last_success": last.get(mv_id),
        })
    return rows


def run_one(due, *, sources: str | None, development_write: bool) -> dict:
    """Launch one `fetch_model` and return its host-free end record.

    A subprocess, not an import, so one model's crash cannot end the batch and
    each run gets a clean process - the same isolation the admin page's button
    uses. FETCH_MAX_THREADS carries the model's cap.
    """
    from judge import scheduler

    env = dict(os.environ, FETCH_MAX_THREADS=str(due.thread_cap), FETCH_QUIET="1")
    # THE RUNNER NAMES THE RUN, THE SAME WAY THE ADMIN BUTTON DOES (#494 fix,
    # 2026-10-05). This read the id back from the child's first stdout line,
    # and `fetch_model` stopped printing it (its own comment says nothing else
    # invoked the script - this did). The read then took whatever the child
    # printed first, `_end_record` found no such log, and EVERY model reported
    # "no end record" in the public summary while its fetch ran normally.
    # Minting the id here leaves nothing to parse.
    run_id = f"{due.model_version_id}-{uuid.uuid4().hex[:8]}"
    cmd = [sys.executable, "-m", "scripts.fetch_model", due.model_version_id,
           "--run-id", run_id]
    if sources:
        cmd += ["--sources", sources]
    if development_write:
        cmd += ["--development-write"]
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    return {"model_version_id": due.model_version_id, "display_name": due.display_name,
            "run_id": run_id, "returncode": proc.returncode,
            "_end": _end_record(run_id), "_scheduler": scheduler}


def _end_record(run_id: str) -> dict | None:
    """The run's `end` line from its local file, or None. Host-free fields only
    are kept by the caller via `scheduler.safe_record`."""
    import json

    if not run_id:
        return None
    path = ROOT / "var" / "fetch" / f"{run_id}.jsonl"
    try:
        for line in reversed(path.read_text(encoding="utf-8").splitlines()):
            rec = json.loads(line)
            if rec.get("kind") == "end":
                return rec
    except (OSError, ValueError):
        return None
    return None


def post_summary(records: list[dict]) -> None:
    from judge import scheduler

    issue = os.getenv("SCHEDULER_ISSUE")
    body = scheduler.summarise_runs(records)
    if not issue:
        print("SCHEDULER_ISSUE not set; summary not posted:\n" + body)
        return
    subprocess.run(["gh", "issue", "comment", issue, "--body", body], cwd=ROOT, check=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sources", default=None,
                    help="scope every fetch to these sources (see fetch_model --sources). "
                         "Use `github` for the safe end-to-end test.")
    ap.add_argument("--max-models", type=int, default=None,
                    help="stop after this many models, whatever else is due")
    ap.add_argument("--deadline-minutes", type=float, default=None,
                    help="stop LAUNCHING models once this many minutes have passed. "
                         "A model already running finishes. For a CI job with a hard "
                         "time limit; unset means no deadline.")
    ap.add_argument("--development-write", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what is due and exit; harvests nothing")
    args = ap.parse_args(argv)

    if not args.dry_run and not enabled():
        print("scheduler disabled: SCHEDULER_ENABLED is not set. Nothing harvested.")
        return 0

    import psycopg

    from judge import scheduler

    with psycopg.connect(_read_only_dsn(), connect_timeout=20) as conn:
        rows = due_rows(conn)
    due = scheduler.rank_due(rows, datetime.now(UTC))
    if args.max_models is not None:
        due = due[: args.max_models]

    print(f"due: {len(due)} model(s)")
    for d in due:
        print(f"  {d.display_name}  [{d.reason}, cap {d.thread_cap}]")
    if args.dry_run:
        return 0
    if not due:
        return 0

    # THE DAILY BUDGET IS ONE TEAM-WIDE FIGURE, so the runner checks it before
    # each model rather than letting fetch_model find out at E5. Once spent,
    # a further model would still HARVEST - using platform quota - and then
    # extract nothing, and the summary would show it as an ordinary run with
    # zero quotes. So the runner stops launching and names every model it did
    # not run, with the reason (rule 4: an absence we caused says so).
    # An unset budget refuses (rule 6): fetch_model would run uncapped-by-cap.
    from judge import spend_ledger

    raw_cap = os.getenv("EXTRACTION_DAILY_BUDGET_USD")
    if raw_cap is None or not raw_cap.strip():
        raise SystemExit(
            "EXTRACTION_DAILY_BUDGET_USD is not set; refusing to run a batch whose "
            "spend nothing caps (docs/ops-scheduled-fetches.md, step 2)"
        )
    cap = float(raw_cap)

    records = []
    started = time.monotonic()
    for i, d in enumerate(due):
        # A JOB WITH A HARD TIME LIMIT (GitHub Actions: 6 h) kills a fetch
        # mid-run, and the reaper then records it `abandoned`. So the runner
        # stops LAUNCHING at the deadline and names every model it did not run;
        # one already running is allowed to finish. Measured 2026-10-06: a first
        # fetch at the 100-thread cap took about 2-2.5 h (median 28 s, mean 85 s
        # per thread over 26 threads), so the workflow sets the deadline well
        # short of the job limit.
        elapsed = (time.monotonic() - started) / 60
        if args.deadline_minutes is not None and elapsed >= args.deadline_minutes:
            for rest in due[i:]:
                records.append({"model": rest.display_name,
                                "status": "not run: this job's time budget is spent"})
            print(f"deadline reached after {elapsed:.0f} min; {len(due) - i} model(s) not run")
            break
        spent = spend_ledger.spent_today()
        if spent >= cap:
            for rest in due[i:]:
                records.append({"model": rest.display_name,
                                "status": "not run: daily budget spent"})
            print(f"daily budget spent (${spent:.4f} of ${cap:.2f}); "
                  f"{len(due) - i} model(s) not run")
            break
        result = run_one(d, sources=args.sources, development_write=args.development_write)
        end = result["_end"]
        rec = scheduler.safe_record(end) if end else {"status": "no end record"}
        rec.setdefault("model", d.display_name)
        records.append(rec)
    post_summary(records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
