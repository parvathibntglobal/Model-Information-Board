"""Compute `document`'s five specificity components and write them.

WHY THIS EXISTS: THERE IS NO WRITER, NOT A BROKEN ONE. The computing code has
been in `collect/triage/specificity.py` since it was built and is tested. What
does not exist is any path that stores what it computes. All three document
INSERTs name the same eleven columns and none of the six specificity columns is
among them:

    collect/adapters/blog/write.py:89
    collect/adapters/github.py:814, :971
    collect/adapters/reddit_write.py:72

`collect/assemble/article.py:document_row` does not build them either. So the
handful of rows on staging that DO carry values did not come from a writer -
they came from `scripts/export_thread_contexts.py`, which hand-builds INSERT
text for one thread and one article. That is why the count is seven and why it
will stay seven no matter how many documents are harvested.

THE ANSWER IS THEREFORE BOTH, AND THIS SCRIPT IS THE OPERATOR HALF. A backfill
lifts the stored corpus; something has to write it forward or the next harvest
re-creates the gap. That forward half is the `score-documents` stage in
`collect/ops/chain.py`, wired 2026-08-31, and BOTH CALL THE SAME FUNCTION -
`collect/triage/store.py:score_unscored`. This script exists so the sweep can be
run and reported on by hand without waiting for a night; it is not a second
implementation, and it must never become one.

WHAT IT WRITES, AND WHAT IT REFUSES TO WRITE. Only rows where all six columns
are NULL, and only rows whose text can be read from the local raw store. A
document whose payload is not on this machine is COUNTED AND NAMED as
unreadable, never written as False - the whole reason these columns matter is
that `judge/`'s weighting read a NULL as a False once already, and a backfill
that invented Falses for unreadable text would do the same thing one layer
earlier (rule 6).

DEFAULT IS A DRY RUN. `--write` is required to touch the database, and it
writes inside one transaction per batch with `WHERE has_numbers IS NULL`, so a
second run is a no-op rather than a rewrite.

    python scripts/backfill_document_facts.py            # measure only
    python scripts/backfill_document_facts.py --write
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib

from collect.db import connect
from collect.rawstore import RawStore
from collect.triage.specificity import COMPONENTS
from collect.triage.store import score_unscored


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="actually update rows")
    ap.add_argument("--batch", type=int, default=100)
    ap.add_argument("--json", default="docs/measurements/document-facts-backfill.json")
    args = ap.parse_args()

    store = RawStore()
    conn = connect()
    try:
        already = conn.execute(
            "SELECT count(*) FROM document WHERE has_numbers IS NOT NULL"
        ).fetchone()[0]
        total = conn.execute("SELECT count(*) FROM document").fetchone()[0]
    finally:
        conn.close()

    # RESUMED ACROSS DROPPED CONNECTIONS, BECAUSE THE LINK IS REMOTE AND THIS
    # RUN IS LONG. Two attempts died mid-sweep with "server closed the
    # connection unexpectedly" - once at 0 rows and once at 907 of 3,061.
    #
    # Resuming is safe ONLY because `score_unscored` selects on all-six-NULL
    # and its UPDATE re-checks `has_numbers IS NULL`: a resumed pass re-reads
    # what is still unscored and cannot rewrite a committed row. If either
    # guard is ever removed, this loop becomes a way to score a document twice
    # under two different registry populations, which is worse than the crash.
    #
    # The loop stops when a pass makes NO progress, not after a fixed count - a
    # pass that writes nothing is either finished or failing the same way twice,
    # and both mean stop.
    run = None
    attempts = 0
    while True:
        attempts += 1
        conn = connect()
        try:
            attempt = score_unscored(
                conn, store, batch=args.batch, dry_run=not args.write
            )
        except Exception as error:  # noqa: BLE001
            print(f"  attempt {attempts} lost the connection: "
                  f"{type(error).__name__}. Committed rows are kept; resuming.")
            attempt = None
        finally:
            conn.close()

        if attempt is not None:
            if run is None:
                run = attempt
            else:
                # WHAT MERGES AND WHAT DOES NOT, because getting this wrong
                # printed "1,048 readable of 1,106 eligible" beside "1,106 not
                # on this machine" - three figures that cannot all be true, in
                # a report whose whole job is that they are (rule 7).
                #
                #   eligible    the FIRST attempt's. It is the size of the job,
                #               and a resumed pass sees only what is left.
                #   scored /    accumulate. Each pass did its own work.
                #   written
                #   unreadable  the LAST attempt's. The unreadable set does not
                #               shrink between passes, so every pass re-counts
                #               the SAME rows - summing them multiplies one
                #               finding by the number of crashes.
                run.scored += attempt.scored
                run.written += attempt.written
                run.unreadable = attempt.unreadable
                run.unreadable_by_source = attempt.unreadable_by_source
                for name, count in attempt.true_counts.items():
                    run.true_counts[name] = run.true_counts.get(name, 0) + count
            if not args.write or attempt.written == 0:
                break
        elif run is not None and attempts > 1:
            continue
        if attempts > 40:
            print("  STOPPING after 40 attempts. Reporting what landed.")
            break

    if run is None:
        print("NOTHING RAN. Every attempt lost the connection before scoring.")
        return 1

    conn = connect()
    try:
        # THE TABLE AS IT NOW STANDS, read back rather than derived from the
        # run. `already + written` is wrong across separate invocations - this
        # backfill took three, after two lost connections - and a figure that is
        # right only when nothing went wrong is the wrong figure to print in a
        # report about something that went wrong.
        populated_now = conn.execute(
            "SELECT count(*) FROM document WHERE has_numbers IS NOT NULL"
        ).fetchone()[0]
        still_null = conn.execute(
            "SELECT count(*) FROM document WHERE has_numbers IS NULL"
        ).fetchone()[0]
        # The per-source breakdown is the script's own, because it is a
        # reporting concern rather than something the nightly stage needs.
        pairs = conn.execute(
            "SELECT source, has_numbers, has_conditions FROM document "
            "WHERE has_numbers IS NOT NULL"
        ).fetchall() if args.write else []
    finally:
        conn.close()

    scored = run.scored
    skipped = run.unreadable
    unreadable = collections.Counter(run.unreadable_by_source)
    true_counts = collections.Counter(run.true_counts)
    by_source: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    both = either = 0
    for source, numbers, conditions in pairs:
        by_source[source]["scored"] += 1
        if numbers:
            by_source[source]["has_numbers"] += 1
        if conditions:
            by_source[source]["has_conditions"] += 1
        if numbers and conditions:
            both += 1
        if numbers or conditions:
            either += 1
    written = run.written

    print("=" * 78)
    print("DOCUMENT FACTS - COMPUTED" + (" AND WRITTEN" if args.write else " ONLY (dry run)"))
    print("=" * 78)
    print("  THE TABLE, read back after the run:")
    print(f"    documents in `document`                     {total:6d}")
    print(f"    carrying the columns now                    {populated_now:6d}")
    print(f"    still NULL                                  {still_null:6d}")
    print()
    print(f"  THIS INVOCATION ({attempts} pass(es)):")
    print(f"    carried the columns before it started       {already:6d}")
    print(f"    eligible when it started (all six NULL)     {run.eligible:6d}")
    print(f"    scored                                      {scored:6d}")
    print(f"    written                                     {written:6d}")
    print(f"    payload NOT on this machine, LEFT NULL      {skipped:6d}")
    for source, n in unreadable.most_common():
        print(f"        {source:12s} {n:6d}")
    print()
    if not scored:
        # TWO REASONS FOR ZERO AND THEY ARE OPPOSITE FINDINGS. Everything
        # readable is already done - which is what a second run looks like and
        # is a pass - or nothing here could be read, which is a broken store.
        # One exit code for both would make a successful no-op indistinguishable
        # from a host with no raw store at all.
        if run.eligible and run.eligible == skipped:
            print(f"  NOTHING LEFT TO DO. All {run.eligible} remaining rows are")
            print("  unreadable on this host and stay NULL. Run the backfill from")
            print("  a host holding those payloads to finish them.")
            return 0
        print("  NOTHING SCORED. An empty result is not a measured zero.")
        return 1

    print(f"  THE RATE, over the {scored} documents scored here:")
    for name in COMPONENTS:
        n = true_counts[name]
        print(f"    {name:22s} true {n:6d}   {n / scored:6.1%}")
    print()
    neither = 0
    if pairs:
        # OVER EVERY POPULATED ROW, not only this run's. The denominator is
        # named beside the figure because after a second run the two differ.
        populated = len(pairs)
        neither = populated - either
        print(f"  THE PAIR THE WEIGHTING PATH READS, over {populated} populated rows:")
        print(f"    has_numbers AND has_conditions   {both:6d}   {both / populated:6.1%}")
        print(f"    exactly one of the two           {either - both:6d}"
              f"   {(either - both) / populated:6.1%}")
        print(f"    neither                          {neither:6d}   {neither / populated:6.1%}")
        print()
        print("  by source (denominator is that source's populated documents):")
        for source, counts in sorted(by_source.items()):
            n = counts["scored"]
            print(f"    {source:8s} n={n:5d}   "
                  f"numbers={counts['has_numbers'] / n:.0%}  "
                  f"conditions={counts['has_conditions'] / n:.0%}")
        print()
    if not args.write:
        print("  DRY RUN. Nothing was written. Re-run with --write.")

    out = {
        "documents_total_at_run": total,
        "populated_after_run": populated_now,
        "still_null_after_run": still_null,
        "passes": attempts,
        "already_populated_before_run": already,
        "eligible_all_six_null": run.eligible,
        "scored": scored,
        "scored_population_note": (
            "documents with all six specificity columns NULL whose text_ref "
            "resolves in the local raw store"
        ),
        "unreadable_here": dict(unreadable),
        "unreadable_note": (
            "payload absent from THIS machine's raw store. Left NULL - an "
            "unreadable document is not a document with no numbers (rule 6)."
        ),
        "true_counts": dict(true_counts),
        "has_numbers_and_has_conditions": both,
        "has_numbers_or_has_conditions": either,
        "neither": neither,
        "by_source": {s: dict(c) for s, c in by_source.items()},
        "written": written if args.write else 0,
        "dry_run": not args.write,
    }
    path = pathlib.Path(args.json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwritten to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
