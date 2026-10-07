"""Put this machine's past blog-generation calls into the spend ledger.

WHAT THIS IS FOR. Until 2026-10-07 the blog generator's model calls reached no
ledger: Admin-started runs had a per-run cost in `blog_generation_run`, and a
run started from a terminal had nothing. Every call is in the synthesis record
the generator saved (`_blog_synthesis/<post>/<started>.json`, one `attempts`
entry per call, with OpenRouter's reported tokens and cost). This sends those
calls to `spend_ledger` as stage 'blog' - outside the daily cap - so Admin ->
API usage can show blog spend by month.

IDEMPOTENT. Each row is built by `generate_sample_blogs.ledger_kwargs`, the
same function the generator now calls live, so a call already recorded - live
or by an earlier backfill - has the same id and is skipped. Running it twice,
or on two machines, changes nothing.

THE SHARED TABLE DECIDES WHAT IS NEW. The first version read the merged view
(`read_everywhere`) and never loaded .env, so on 2026-10-07 it wrote 78 rows to
the local file only and then counted them "already recorded" from that same
file, with the shared table empty. It now loads .env, compares against the
table, refuses --apply when the table cannot be read, and checks afterwards
that every row landed.

THE POPULATION IS THIS MACHINE'S RECORDS (rule 7). A teammate's runs are in
their own `_blog_synthesis/`, so each machine that generated posts runs this
once. A record deleted from disk is a call this cannot see.

    python scripts/backfill_blog_spend.py            # report, change nothing
    python scripts/backfill_blog_spend.py --apply
    ... --runs-dir PATH    records from another checkout's _blog_synthesis/

Needs migration 20261007T0900 on the target database; without it the table
refuses 'blog' rows, and --apply says so rather than reporting success.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

# .env FIRST: the ledger reads DATABASE_URL from the environment, and without it
# every read and write silently uses this machine's file alone.
load_dotenv(ROOT / ".env", override=False)

import generate_sample_blogs as gen  # noqa: E402
from judge import spend_ledger  # noqa: E402


def candidates(runs_dir: pathlib.Path) -> tuple[list[dict], int, list[str]]:
    """Ledger kwargs for every recorded call, the number of records read, and
    the files that could not be read (named, never dropped)."""
    out, n_records, unreadable = [], 0, []
    for f in sorted(runs_dir.glob("*/*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            unreadable.append(f"{f.relative_to(runs_dir)} ({type(e).__name__})")
            continue
        if not isinstance(rec, dict) or not rec.get("started") or "attempts" not in rec:
            continue
        n_records += 1
        out += [gen.ledger_kwargs(rec, i) for i in range(len(rec["attempts"]))]
    return out, n_records, unreadable


def as_call(kw: dict, machine: str) -> spend_ledger.Call:
    """The row `spend_ledger.record(**kw)` would write on this machine."""
    usd = kw["reported_usd"]
    return spend_ledger.Call(
        at=kw["at"], stage=kw["stage"], model=kw["model"],
        input_tokens=kw["input_tokens"], output_tokens=kw["output_tokens"],
        usd=float(usd) if usd is not None else 0.0,
        unmetered=kw["input_tokens"] == 0 and kw["output_tokens"] == 0,
        unpriced=usd is None, machine=machine, run_id=kw["run_id"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="write the new calls (default: report only)")
    ap.add_argument("--runs-dir", type=pathlib.Path, default=gen.RUNS,
                    help="the _blog_synthesis folder to read (default: this checkout's)")
    args = ap.parse_args()
    runs_dir = args.runs_dir.resolve()
    if not runs_dir.is_dir():
        # A folder that is not there is not "no calls" - say which (rule 6).
        sys.exit(f"{runs_dir} does not exist; pass --runs-dir to the folder the generator wrote")

    found, n_records, unreadable = candidates(runs_dir)
    here = spend_ledger.machine()
    calls = [as_call(kw, here) for kw in found]

    shared = spend_ledger.read_database()
    local = {c.id for c in spend_ledger.read_all()}
    in_db = {c.id for c in shared} if shared is not None else set()
    new = [c for c in calls if c.id not in in_db]
    months = Counter((c.at.strftime("%Y-%m"), c.model) for c in new)
    unpriced = sum(1 for c in new if c.unpriced)

    print("shared table      " + ("readable" if shared is not None
                                  else "NOT READABLE - this run sees this machine's file only"))
    print(f"records read      {n_records}  (in {runs_dir})")
    print(f"calls in them     {len(calls)}")
    print(f"in shared table   {len(calls) - len(new)}")
    print(f"to record         {len(new)}  - ${sum(c.usd for c in new):.4f} reported"
          + (f", {unpriced} with no reported cost (a floor)" if unpriced else ""))
    for (month, model), n in sorted(months.items()):
        print(f"  {month}  {model:40} {n} call(s)")
    for u in unreadable:
        print(f"  could not read: {u}")
    if not args.apply:
        print()
        print("DRY RUN - nothing written. Re-run with --apply.")
        return
    if shared is None:
        # Writing to the file alone would look like a backfill and be none.
        sys.exit("refusing --apply: the shared table could not be read (is DATABASE_URL set?)")
    # THE WRITE GATE (tests/test_every_write_path_takes_the_gate.py). It refuses
    # ENVIRONMENT=development pointed at a database that is not this machine.
    # The first run of this script, 2026-10-07, wrote 78 rows to the shared
    # table from exactly that pairing, because it had no gate.
    from judge.writeguard import UnsafeWriteRefused
    from judge.writeguard import check as writeguard_check

    try:
        writeguard_check(os.environ.get("DATABASE_URL"), command="backfill_blog_spend.py --apply")
    except UnsafeWriteRefused as e:
        sys.exit(str(e))

    # The local file gets a row only where it has none, so a re-run never
    # duplicates it; the table is ON CONFLICT DO NOTHING on the same id.
    path = spend_ledger.ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        for c in new:
            if c.id not in local:
                handle.write(c.as_row() + "\n")
    spend_ledger.append_to_database(new)
    after = {c.id for c in spend_ledger.read_database() or []}
    landed = sum(1 for c in new if c.id in after)
    print()
    print(f"recorded {landed} of {len(new)} call(s) in the shared table.")
    if landed < len(new):
        sys.exit("some rows did not reach the shared table - has migration 20261007T0900 run?")


if __name__ == "__main__":
    main()
