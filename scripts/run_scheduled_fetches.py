#!/usr/bin/env python
"""Run the per-model fetches that are due, one at a time, within the daily cap.

⚠ DISABLED BY DEFAULT, AND THAT IS THE POINT. It refuses to harvest unless
  `SCHEDULER_ENABLED` is set to a truthy value, so turning it on is a person's
  decision, made on the repository variable. It was off while
  `contract/sources.yaml`'s undertaking described a basis that no longer held;
  #535 re-asserted it on 2026-10-19 and it was switched on 2026-10-21. It was
  re-asserted again on 2026-11-12 and has had no expiry since
  (docs/ops-scheduled-fetches.md).

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


#: The last SUCCESSFUL fetch per model version - what makes a model not due.
#:
#: ⚠ AN `ok` THAT READ NOTHING BECAUSE IT COULD NOT READ IS NOT A SUCCESS
#:   (2026-10-06). The first scheduled Action ended `ok` having read none of
#:   6,087 unread threads (their payloads were on a laptop), and that `ok` took
#:   DeepSeek V4 Pro 0423 off the due list for 7 days. So a run counts only if
#:   it read at least one thread, or found nothing it could not read. A run
#:   with no unreadable threads and nothing new is a real "nothing to do", and
#:   still counts. Runs before `threads_unreadable_here` existed carry no field
#:   and are judged as before.
#:
#: ⚠ A COLLECT-ONLY RUN COUNTS ON ITS HARVEST (2026-10-26). It reads no thread
#:   by design (`FETCH_EXTRACT=off`), and 1,648 threads were unreadable on the
#:   runner, so neither clause above could ever hold: from 2026-10-22 no
#:   scheduled run counted, every model was due every night, and 12-15 models
#:   at the tail went unfetched on each of 10-23, 10-24 and 10-25 when the
#:   time budget ran out. An `ok` collect-only run did what it was for -
#:   `ok` already means no stage errored (#327) - so it counts.
LAST_SUCCESS = """
    SELECT r.model_version_id, max(e.at)
      FROM fetch_log r
      JOIN fetch_log e ON e.run_id = r.run_id AND e.kind = 'end'
     WHERE r.kind = 'run'
       AND (e.payload->>'status') = 'ok'
       AND (coalesce((e.payload->>'threads_read')::int, 0) > 0
            OR coalesce((e.payload->>'threads_unreadable_here')::int, 0) = 0
            OR (e.payload->>'extract_skipped') = 'true')
     GROUP BY r.model_version_id
"""


def due_rows(conn, which: str = "models") -> list[dict]:
    """The tracked, in-window models (or agents) with their last SUCCESSFUL fetch.

    `which` picks the list: `models` is `contract/tracked_models.yaml` plus
    `auto_track` arrivals; `agents` is `contract/tracked_agents.yaml`, the agent
    fetch's own list (#609-#611) - the two never mix. The last success comes
    from `fetch_log` (an `end` record with status ok). Matching the registry row
    by canonical id OR row id, as the models page does.

    A tracked entry that matches no row comes back as a row carrying
    `registry_row_missing` instead of being dropped, so `main` can name it.
    """
    if which == "agents":
        from judge.config import tracked_agents

        tracked = list(tracked_agents())
    elif which == "models":
        from judge.tracked import all_tracked

        # Hand-written entries plus new arrivals the `auto_track` rule admits, so
        # a model the poll inserts is due for a first fetch with no PR between.
        tracked = [m for m in all_tracked(conn) if m.registry]
    else:
        raise ValueError(f"which must be 'models' or 'agents', not {which!r}")
    ids = [m.registry for m in tracked]
    # KEYED BY BOTH IDS. The query matched either column, and this was keyed
    # by `canonical_id` alone, so an entry naming the row id found its row in
    # SQL and lost it here. Claude Fable 5.1 (`anthropic/claude-fable-5-1`,
    # canonical `anthropic/claude-fable-5.1`) was dropped that way, without a
    # word, for as long as those two differed; this keying dates from b42fc02
    # (2026-09-28). Its last fetch of any kind was 2026-10-18 (fetch_log, read
    # 2026-11-05).
    reg = {}
    for r in conn.execute(
            "SELECT canonical_id, id, display_name, in_window FROM model_version "
            "WHERE canonical_id = ANY(%s) OR id = ANY(%s)", (ids, ids)).fetchall():
        reg[r[0]] = reg[r[1]] = r
    # last successful fetch per model_version_id
    last = {r[0]: r[1] for r in conn.execute(LAST_SUCCESS).fetchall()}
    rows = []
    for m in tracked:
        hit = reg.get(m.registry)
        if hit is None:
            # Tracked but no registry row has that id: not polled yet, or the
            # id moved. Nothing to fetch either way, and the run says so.
            rows.append({"display_name": m.name, "registry": m.registry,
                         "registry_row_missing": True})
            continue
        canonical, mv_id, display, in_window = hit
        rows.append({
            "model_version_id": mv_id,
            "display_name": display or m.name,
            "tracked": True,
            "in_window": bool(in_window),
            "last_success": last.get(mv_id),
            # The agent run's turn-taking reads it; a model has none.
            **({"group": m.group} if which == "agents" else {}),
        })
    return rows


IN_PROGRESS = """
    SELECT DISTINCT r.model_version_id
      FROM fetch_log r
     WHERE r.kind = 'run'
       AND NOT EXISTS (SELECT 1 FROM fetch_log e WHERE e.run_id = r.run_id AND e.kind = 'end')
       AND (SELECT max(x.at) FROM fetch_log x WHERE x.run_id = r.run_id) > %s
"""


def in_progress(conn, now: datetime) -> set[str]:
    """Model versions with a fetch still running anywhere, by the shared log.

    "Running" is the reaper's definition (judge/fetch_reaper.py): no end record,
    and a line within DEFAULT_SILENT_FOR. Reusing it means this and the reaper
    cannot disagree about whether a run is alive.
    """
    from judge.fetch_reaper import DEFAULT_SILENT_FOR

    return {r[0] for r in conn.execute(IN_PROGRESS, (now - DEFAULT_SILENT_FOR,)).fetchall()}


def run_one(due, *, sources: str | None, development_write: bool,
            timeout_s: float | None = None, budget_usd: float | None = None) -> dict:
    """Launch one `fetch_model` and return its host-free end record.

    A subprocess, not an import, so one model's crash cannot end the batch and
    each run gets a clean process - the same isolation the admin page's button
    uses. FETCH_MAX_THREADS carries the model's cap.

    `budget_usd`, when given, replaces the child's EXTRACTION_DAILY_BUDGET_USD.
    `Budget.from_env` reads it and checks it before EVERY call against today's
    team-wide ledger total, so the fetch stops itself between threads at that
    figure. The agent run passes its ceiling here; the model run passes nothing.
    """
    from judge import scheduler

    env = dict(os.environ, FETCH_MAX_THREADS=str(due.thread_cap), FETCH_QUIET="1")
    if budget_usd is not None:
        env["EXTRACTION_DAILY_BUDGET_USD"] = f"{budget_usd:.6f}"
    # THE RUNNER NAMES THE RUN, THE SAME WAY THE ADMIN BUTTON DOES (#494 fix,
    # 2026-10-05). This read the id back from the child's first stdout line,
    # and `fetch_model` stopped printing it (its own comment says nothing else
    # invoked the script - this did). The read then took whatever the child
    # printed first, `_end_record` found no such log, and EVERY model reported
    # "no end record" in the public summary while its fetch ran normally.
    # Minting the id here leaves nothing to parse.
    #
    # NO SLASH IN THE ID (2026-10-26). A registry row id can be a canonical id
    # (`openai/gpt-6-astra`), and the id names the local log file, so the slash
    # made a directory nobody created: GPT-6 Astra reported "no end record"
    # every night and was never fetched by this runner. The admin's Fetch
    # button has always replaced it (judge/app.py).
    run_id = f"{due.model_version_id.replace('/', '_')}-{uuid.uuid4().hex[:8]}"
    cmd = [sys.executable, "-m", "scripts.fetch_model", due.model_version_id,
           "--run-id", run_id]
    if sources:
        cmd += ["--sources", sources]
    if development_write:
        cmd += ["--development-write"]
    # A TIMEOUT, so a job with a hard limit stops the fetch ITSELF and still
    # posts its summary. Killed from outside, the runner dies with the fetch and
    # the night says nothing. Progress is not lost: each thread commits as it
    # finishes (`after_thread=conn.commit`), the run is reaped as abandoned, and
    # the model stays due for the next night.
    try:
        # UTF-8 EXPLICITLY. On Windows `text=True` decodes as cp1252 and the
        # reader thread crashed on a model's output (2026-10-06, byte 0x9d);
        # harmless - the end record is read from the log file - but noisy.
        proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"model_version_id": due.model_version_id, "display_name": due.display_name,
                "run_id": run_id, "returncode": None, "timed_out": True,
                "_end": None, "_scheduler": scheduler}
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
    ap.add_argument("--job-limit-minutes", type=float, default=None,
                    help="the hard limit of the job this runs in. A running fetch is "
                         "stopped 10 minutes before it, so the summary still posts. "
                         "Unset means no limit.")
    ap.add_argument("--deadline-minutes", type=float, default=None,
                    help="stop LAUNCHING models once this many minutes have passed. "
                         "A model already running finishes. For a CI job with a hard "
                         "time limit; unset means no deadline.")
    ap.add_argument("--development-write", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what is due and exit; harvests nothing")
    ap.add_argument("--list", choices=("models", "agents"), default="models",
                    help="which tracked list to fetch: models (tracked_models.yaml + "
                         "auto_track) or agents (tracked_agents.yaml). Never both.")
    args = ap.parse_args(argv)

    if not args.dry_run and not enabled():
        print("scheduler disabled: SCHEDULER_ENABLED is not set. Nothing harvested.")
        return 0

    # THE AGENT RUN'S OWN SETTINGS (contract/tracked_agents.yaml `run`). Its spend
    # ceiling keeps it from using the team-wide daily cap before the model fetch.
    run_ceiling = None
    if args.list == "agents":
        from judge.config import agent_run_rule

        rule = agent_run_rule()
        if not rule.enabled:
            print("agent fetch disabled: tracked_agents.yaml `run.enabled` is false. "
                  "Nothing harvested.")
            return 0
        run_ceiling = rule.run_spend_ceiling_usd

    import psycopg

    from judge import scheduler

    with psycopg.connect(_read_only_dsn(), connect_timeout=20) as conn:
        # The model path calls `due_rows(conn)` exactly as before, so nothing that
        # reads or stands in for it changes; only the agent run names its list.
        rows = due_rows(conn) if args.list == "models" else due_rows(conn, "agents")
    # A TRACKED MODEL WITH NO REGISTRY ROW IS NAMED, NOT DROPPED (rule 4). It
    # used to vanish here, so a model stopped being fetched and nothing said so.
    missing = [r for r in rows if r.get("registry_row_missing")]
    rows = [r for r in rows if not r.get("registry_row_missing")]
    due = scheduler.rank_due(rows, datetime.now(UTC))
    group_of = {}
    if args.list == "agents":
        # THE GROUPS TAKE TURNS (tracked_agents.yaml `run.group_turns`), so the
        # deadline, the ceiling or --max-models cannot fall on one group alone.
        # Before `--max-models`, which then keeps a share of every group.
        group_of = {r["model_version_id"]: r["group"] for r in rows}
        due = scheduler.take_turns(due, group_of, rule.group_turns)
    if args.max_models is not None:
        due = due[: args.max_models]

    print(f"due: {len(due)} model(s)")
    for d in due:
        group = f", {group_of[d.model_version_id]}" if group_of else ""
        print(f"  {d.display_name}  [{d.reason}, cap {d.thread_cap}{group}]")
    for m in missing:
        print(f"  not due: {m['display_name']} is tracked as {m['registry']}, "
              "and no registry row has that id")
    if args.dry_run:
        return 0
    records = [{"model": m["display_name"],
                "status": f"not run: tracked as `{m['registry']}`, which no registry row has"}
               for m in missing]
    if not due:
        if records:
            post_summary(records)
        return 0

    # THE DAILY BUDGET IS ONE TEAM-WIDE FIGURE, so the runner checks it before
    # each model rather than letting fetch_model find out at E5. Once spent,
    # a further model would still HARVEST - using platform quota - and then
    # extract nothing, and the summary would show it as an ordinary run with
    # zero quotes. So the runner stops launching and names every model it did
    # not run, with the reason (rule 4: an absence we caused says so).
    # An unset budget refuses (rule 6): fetch_model would run uncapped-by-cap.
    from judge import spend_ledger

    # A COLLECT-ONLY BATCH SPENDS NOTHING, so it needs no cap and checks none.
    # Read with the same function `fetch_model` uses, so the two cannot
    # disagree about whether this batch extracts.
    extracting = scheduler.extract_enabled(os.getenv("FETCH_EXTRACT"))
    cap = None
    if extracting:
        raw_cap = os.getenv("EXTRACTION_DAILY_BUDGET_USD")
        if raw_cap is None or not raw_cap.strip():
            raise SystemExit(
                "EXTRACTION_DAILY_BUDGET_USD is not set; refusing to run a batch whose "
                "spend nothing caps (docs/ops-scheduled-fetches.md, step 2)"
            )
        cap = float(raw_cap)

    # `records` already names any tracked model with no registry row.
    started = time.monotonic()
    spent_at_start = spend_ledger.spent_today() if (extracting and run_ceiling) else 0.0
    for i, d in enumerate(due):
        # ONE FETCH PER MODEL AT A TIME (2026-10-06). A manual run of the same
        # model and this batch would both select the same unread threads and
        # pay twice to extract them; nothing prevented it. Checked per model,
        # just before launch, against the shared log.
        with psycopg.connect(_read_only_dsn(), connect_timeout=20) as conn:
            busy = in_progress(conn, datetime.now(UTC))
        if d.model_version_id in busy:
            records.append({"model": d.display_name,
                            "status": "not run: a fetch of this model is already running"})
            print(f"skipped {d.display_name}: a fetch of it is already running")
            continue
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
        spent = spend_ledger.spent_today() if extracting else 0.0
        if extracting and spent >= cap:
            for rest in due[i:]:
                records.append({"model": rest.display_name,
                                "status": "not run: daily budget spent"})
            print(f"daily budget spent (${spent:.4f} of ${cap:.2f}); "
                  f"{len(due) - i} model(s) not run")
            break
        # THE AGENT RUN'S OWN CEILING: what has been spent SINCE THIS RUN STARTED
        # (team-wide, so an Admin fetch meanwhile counts too - the safe side), so
        # the agents cannot use up the shared daily cap before the model fetch.
        # Checked here before each launch, AND inside each fetch through the
        # child's lowered budget (below), so a running fetch stops at it too.
        if extracting and run_ceiling is not None and spent - spent_at_start >= run_ceiling:
            for rest in due[i:]:
                records.append({"model": rest.display_name,
                                "status": "not run: this run's spend ceiling is reached"})
            print(f"run spend ceiling reached (${spent - spent_at_start:.4f} of "
                  f"${run_ceiling:.2f}); {len(due) - i} agent(s) not run")
            break
        timeout_s = None
        if args.job_limit_minutes is not None:
            left = args.job_limit_minutes - 10 - (time.monotonic() - started) / 60
            timeout_s = max(60.0, left * 60)
        # THE CEILING HOLDS INSIDE A FETCH TOO (#618 review, Parvathi). Checked only
        # before each launch, it let one fetch run past it to the team-wide daily
        # cap - and an agent's FIRST fetch reads its whole backlog (Claude Code's
        # is the largest), so one agent fetch could spend what the model fetch
        # after it needs. The child's own cap is lowered to where this run's ceiling
        # falls on today's ledger, never above the daily cap. The model run's
        # children keep the daily cap exactly as before.
        budget_usd = None
        if extracting and run_ceiling is not None:
            budget_usd = min(cap, spent_at_start + run_ceiling)
        result = run_one(d, sources=args.sources, development_write=args.development_write,
                         timeout_s=timeout_s, budget_usd=budget_usd)
        end = result["_end"]
        if result.get("timed_out"):
            rec = {"status": "stopped at the job time limit; threads read so far are "
                             "saved, and the model stays due"}
        else:
            rec = scheduler.safe_record(end) if end else {"status": "no end record"}
        rec.setdefault("model", d.display_name)
        records.append(rec)
    post_summary(records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
