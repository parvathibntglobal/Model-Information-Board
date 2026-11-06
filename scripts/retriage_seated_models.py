#!/usr/bin/env python
"""Re-triage stale "no model" verdicts for models just seated (#602, option b).

    python scripts/retriage_seated_models.py --models minimax/hailuo-3-max --dry-run
    python scripts/retriage_seated_models.py --models <ids> --apply

Run it after seating models (`scripts/load_unpolled_models.py --apply`, or a
registry poll that brought them). `collect/triage/retriage.py` says what it
reads, what it misses and why adult threads stay dropped.

RECORDED BEFORE IT WRITES. `--apply` saves the id list, the population
fingerprint and the counts to `docs/measurements/retriage-<date>-<models>.json`
first, then clears exactly those verdicts and triages exactly those documents,
then adds what each came back as to the same file - so the change can be
undone from the list and the before/after reported.

It writes to whatever DATABASE_URL names, through the same write guard as the
other loaders. A shared-database write is announced before it runs.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from datetime import UTC, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
    if m:
        os.environ.setdefault(m.group(1), m.group(2))

import psycopg  # noqa: E402

from collect.config import settings  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.triage.retriage import apply, plan  # noqa: E402

MEASUREMENTS = ROOT / "docs" / "measurements"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True,
                    help="comma-separated model ids (row id or canonical id)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    from judge.writeguard import check as writeguard_check
    writeguard_check(os.environ.get("DATABASE_URL"), command="retriage_seated_models.py")

    store = RawStore(pathlib.Path(settings().raw_store_path))
    conn = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=15)
    p = plan(conn, store, models=models)
    print(p.summary())
    if p.by_subreddit:
        print("  by subreddit:", dict(p.by_subreddit.most_common()))
    if args.dry_run or not p.ids:
        conn.rollback()
        conn.close()
        print("\n--dry-run: nothing written." if args.dry_run else "\nnothing to re-triage.")
        return 0

    slug = re.sub(r"[^a-z0-9]+", "-", "-".join(m.split("/")[-1] for m in models).lower())[:60]
    record_path = MEASUREMENTS / f"retriage-{datetime.now(UTC):%Y-%m-%d}-{slug}.json"
    record = {
        "models": models,
        "at": datetime.now(UTC).isoformat(),
        "population_fingerprint": p.population_fingerprint,
        "candidates": p.candidates,
        "adult_left_dropped": p.adult_left_dropped,
        "unreadable": p.unreadable,
        "by_source": dict(p.by_source),
        "by_subreddit": dict(p.by_subreddit),
        "ids": p.ids,
        "before": "dropped / no-resolvable-entity, every id",
    }
    record_path.write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(f"\nid list saved before writing: {record_path.relative_to(ROOT)}")

    out = apply(conn, store, p)
    conn.commit()
    conn.close()
    record["after"] = out
    record_path.write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(f"re-triaged {out['triaged']}: {out['kept']} kept, {out['dropped']} dropped; "
          f"kept by subreddit {out.get('kept_by_subreddit')}")
    print("COMMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
