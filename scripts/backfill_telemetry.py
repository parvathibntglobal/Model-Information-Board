"""Push this machine's var/ telemetry into the shared tables.

WHAT THIS IS FOR. Spend, fetch logs and quota readings were per-machine files
until 2026-09-11. The writers now mirror into `spend_ledger`, `fetch_log` and
`rapidapi_quota` as they go, but everything recorded BEFORE that is still only
on the machine that recorded it. This sends it.

IDEMPOTENT, AND THAT IS THE WHOLE DESIGN. Every id is derived from content:

    spend      sha256(machine|run|at|stage|model|tokens)
    fetch log  sha256(run_id|seq|payload)

so running it twice changes nothing, and running it on two machines merges
rather than collides. THAT MATTERS MOST FOR SPEND: the ledger had no primary
key, so a backfill without one would have inflated the team's dollar total on
every re-run — the one direction a money figure must never drift.

EVERY TEAMMATE SHOULD RUN THIS ONCE on their own machine, which is the point:
the total is only a team total once each machine has sent its own history.

    python scripts/backfill_telemetry.py            # report, change nothing
    python scripts/backfill_telemetry.py --apply

THE FILES ARE NOT DELETED. They stay as the local survivor — the thing a run
still has when the database is unreachable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from collect import db, usage  # noqa: E402
from judge import spend_ledger  # noqa: E402

FETCH_DIR = pathlib.Path("var") / "fetch"


def backfill_spend(conn, *, apply: bool) -> tuple[int, int]:
    """Every call in this machine's ledger file. Returns (read, inserted)."""
    calls = spend_ledger.read_all()
    if not calls:
        return 0, 0
    rows = [
        (c.id, c.at, c.stage, c.model, c.input_tokens, c.output_tokens,
         c.usd, c.unpriced, c.machine or spend_ledger.machine(), c.run_id)
        for c in calls
    ]
    if not apply:
        ids = [r[0] for r in rows]
        have = conn.execute(
            "select count(*) from spend_ledger where id = any(%s)", (ids,)
        ).fetchone()[0]
        return len(rows), len(rows) - have
    before = conn.execute("select count(*) from spend_ledger").fetchone()[0]
    with conn.cursor() as cur:
        cur.executemany(
            "insert into spend_ledger (id, at, stage, model, input_tokens, "
            "output_tokens, usd, unpriced, machine, run_id) "
            "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict (id) do nothing",
            rows,
        )
    after = conn.execute("select count(*) from spend_ledger").fetchone()[0]
    return len(rows), after - before


def backfill_fetch_logs(conn, *, apply: bool) -> tuple[int, int, int]:
    """Every line of every run log. Returns (runs, lines_read, inserted)."""
    if not FETCH_DIR.exists():
        return 0, 0, 0
    machine = usage.machine()
    rows: list[tuple] = []
    runs = sorted(FETCH_DIR.glob("*.jsonl"))
    for log in runs:
        run_id = log.stem
        model_version_id = None
        for seq, raw in enumerate(log.read_text(encoding="utf-8").splitlines()):
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except ValueError:
                # A truncated last line is normal for a run that was killed.
                # Skipping it loses one line; refusing the file loses the run.
                continue
            if not isinstance(rec, dict):
                continue
            # The `run` line names the model; later lines inherit it, so a
            # listing can name a run without reading all of it.
            model_version_id = rec.get("model_version_id") or model_version_id
            payload = json.dumps(rec, sort_keys=True)
            line_id = "fl_" + hashlib.sha256(
                f"{run_id}|{seq}|{payload}".encode()
            ).hexdigest()[:24]
            rows.append((line_id, run_id, seq, rec.get("at"), machine,
                         payload, rec.get("kind"), model_version_id))
    if not rows:
        return len(runs), 0, 0
    if not apply:
        ids = [r[0] for r in rows]
        have = conn.execute(
            "select count(*) from fetch_log where id = any(%s)", (ids,)
        ).fetchone()[0]
        return len(runs), len(rows), len(rows) - have
    before = conn.execute("select count(*) from fetch_log").fetchone()[0]
    with conn.cursor() as cur:
        cur.executemany(
            "insert into fetch_log (id, run_id, seq, at, machine, payload, "
            "kind, model_version_id) values (%s,%s,%s,%s,%s,%s,%s,%s) "
            "on conflict (id) do nothing",
            rows,
        )
    after = conn.execute("select count(*) from fetch_log").fetchone()[0]
    return len(runs), len(rows), after - before


def backfill_quota(conn, *, apply: bool) -> list[str]:
    """Each meter's stored reading. Newest READING wins, as at write time."""
    notes: list[str] = []
    for meter, rec in usage.read_rapidapi_meters().items():
        remaining, limit = rec.get("quota_remaining"), rec.get("quota_limit")
        if remaining is None and limit is None:
            notes.append(f"  {meter:10} skipped — reading carries no figure")
            continue
        notes.append(
            f"  {meter:10} remaining={remaining} limit={limit} at={rec.get('at')}"
        )
        if apply:
            conn.execute(
                "insert into rapidapi_quota (meter, quota_remaining, quota_limit, "
                "read_at, read_by, source_run_id, machine) "
                "values (%s,%s,%s,%s,%s,%s,%s) on conflict (meter) do update set "
                "  quota_remaining = excluded.quota_remaining, "
                "  quota_limit = excluded.quota_limit, "
                "  read_at = excluded.read_at, read_by = excluded.read_by, "
                "  source_run_id = excluded.source_run_id, "
                "  machine = excluded.machine, recorded_at = now() "
                "where excluded.read_at > rapidapi_quota.read_at",
                (meter, remaining, limit, rec.get("at"),
                 rec.get("read_by") or "unrecorded", rec.get("source_run_id"),
                 usage.machine()),
            )
    return notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="write. Without it, report what would be written.")
    args = ap.parse_args()

    print(f"machine: {usage.machine()}\n")
    with db.transaction() as conn:
        read, new = backfill_spend(conn, apply=args.apply)
        print(f"spend_ledger   {read:>5} calls in the local file, "
              f"{new:>4} {'inserted' if args.apply else 'would be new'}")

        runs, lines, newl = backfill_fetch_logs(conn, apply=args.apply)
        print(f"fetch_log      {lines:>5} lines across {runs} runs, "
              f"{newl:>4} {'inserted' if args.apply else 'would be new'}")

        print("rapidapi_quota")
        for note in backfill_quota(conn, apply=args.apply) or ["  (no readings)"]:
            print(note)

        if not args.apply:
            conn.rollback()
            print("\nDRY RUN — nothing written. Re-run with --apply.")
        else:
            print("\nwritten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
