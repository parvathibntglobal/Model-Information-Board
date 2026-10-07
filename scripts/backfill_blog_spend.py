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

THE POPULATION IS THIS MACHINE'S RECORDS (rule 7). A teammate's runs are in
their own `_blog_synthesis/`, so each machine that generated posts runs this
once. A record deleted from disk is a call this cannot see.

    python scripts/backfill_blog_spend.py            # report, change nothing
    python scripts/backfill_blog_spend.py --apply
    ... --runs-dir PATH    records from another checkout's _blog_synthesis/

Needs migration 20261007T0900 on the target database; without it the table
refuses 'blog' rows and they stay in the local file (var/spend-ledger.jsonl).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

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
    have = {c.id for c in spend_ledger.read_everywhere()[0]}

    def key(kw: dict) -> str:
        # The id `record` will give this call on this machine (Call.id's parts).
        return spend_ledger.Call(at=kw["at"], stage=kw["stage"], model=kw["model"],
                                 input_tokens=kw["input_tokens"], output_tokens=kw["output_tokens"],
                                 usd=0.0, unmetered=False, machine=here, run_id=kw["run_id"]).id

    new = [kw for kw in found if key(kw) not in have]
    months = Counter((kw["at"].strftime("%Y-%m"), kw["model"]) for kw in new)
    unpriced = sum(1 for kw in new if kw["reported_usd"] is None)
    usd = sum(float(kw["reported_usd"]) for kw in new if kw["reported_usd"] is not None)

    print(f"records read      {n_records}  (in {runs_dir})")
    print(f"calls in them     {len(found)}")
    print(f"already recorded  {len(found) - len(new)}")
    print(f"to record         {len(new)}  - ${usd:.4f} reported"
          + (f", {unpriced} with no reported cost (a floor)" if unpriced else ""))
    for (month, model), n in sorted(months.items()):
        print(f"  {month}  {model:40} {n} call(s)")
    for u in unreadable:
        print(f"  could not read: {u}")
    if not args.apply:
        print("\nDRY RUN - nothing written. Re-run with --apply.")
        return
    for kw in new:
        spend_ledger.record(**kw)
    print(f"\nrecorded {len(new)} call(s): the local file always, "
          "the shared table where it accepts them.")


if __name__ == "__main__":
    main()
