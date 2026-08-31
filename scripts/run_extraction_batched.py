"""Extraction in committed batches, so a stop costs the batch and not the run.

WHAT THIS FIXES, AND IT IS NOT SPEED

`judge/cli.py:_extract_from_export` calls `conn.commit()` exactly once, after
`run_all` returns. There is no `commit()` anywhere in `judge/pipeline.py` or
`judge/store/*.py`. So a 1,512-thread run holds one transaction for its whole
life, and a crash, a budget trip or a Ctrl-C discards **every claim, every cell
and every ledger row** - including the rows that would let a restart skip the
threads already paid for.

That last part is the expensive half. `ExtractionLedger.should_skip` exists
precisely so a resumed run does not re-pay, and `self._ledger.record(...)` is
deliberately in the same transaction as the claims:

    "A ledger row that survived a rolled-back extraction would mark a thread
     read that produced nothing readable, and the next run would skip it -
     evidence lost silently and permanently."

That reasoning is right, and it is exactly why the commit boundary has to move
rather than the ledger. **Claims and their ledger rows commit together, every
`--batch-size` threads.** Tonight's kill at position 90 cost the position as well
as the claims; this makes a stop a real option instead of a loss.

WHY IT IS A CALLER AND NOT AN EDIT TO `judge/`

`run_all` takes the whole thread list and loops. Batching means calling it once
per slice with the same wiring, which is a composition concern - the same reason
`scripts/run_extraction.py` exists at all. It reuses that file's resolver so
there is one place the lane boundary is crossed.

WHAT IT DOES NOT DO. It does not touch the budget. `Budget` is constructed per
`run_all` call, so a fresh one per batch would multiply the cap by the number of
batches - **one Budget is threaded through every batch**, which is what makes
`--budget` mean what it says.

    python scripts/run_extraction_batched.py --from-export DIR --budget 0.79
    python scripts/run_extraction_batched.py --from-export DIR --batch-size 50
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from collect.surface_resolver import RegistrySurfaceResolver  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-export", required=True)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument(
        "--budget", type=float, default=None,
        help="cap for the WHOLE run, threaded through every batch. Overrides "
             "EXTRACTION_DAILY_BUDGET_USD, which despite its name is enforced "
             "per-run rather than per-day - Budget.from_env starts spent_usd at "
             "0.0 and never reads spend_ledger.",
    )
    parser.add_argument("--driver", default="new-evidence")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    from judge.config import capabilities
    from judge.curate.labels import Driver
    from judge.extract import export_source
    from judge.extract.budget import Budget, BudgetExhausted
    from judge.extract.client import OpenRouterClient
    from judge.pipeline import Pipeline
    from judge.store.extractions import ExtractionLedger
    from judge.writeguard import check as writeguard_check

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit(
            "DATABASE_URL is unset. Refusing to guess at a connection: a default "
            "that quietly reaches localhost is how a batch writes to a real "
            "database once."
        )
    writeguard_check(database_url, command="run_extraction_batched.py")

    limit = args.budget if args.budget is not None else None
    if limit is None:
        budget = Budget.from_env()
        if budget is None:
            raise SystemExit(
                "No cap. Pass --budget, or set EXTRACTION_DAILY_BUDGET_USD. An "
                "unset cap is nobody having decided, not a decision to spend "
                "freely."
            )
    else:
        budget = Budget(limit_usd=limit)
    print(f"budget      : ${budget.limit_usd:.2f} for the whole run, one Budget "
          f"threaded through every batch")

    loaded = export_source.load(pathlib.Path(args.from_export))
    for name, why in loaded.skipped:
        print(f"  SKIPPED {name}: {why}")
    threads = loaded.threads[: args.limit] if args.limit else loaded.threads
    if not threads:
        raise SystemExit("no thread in that export carried usable text; nothing to run")

    from collect.db import connect
    from judge.cli import _document_facts

    conn = connect()
    resolver = RegistrySurfaceResolver.from_connection(conn)
    # E6's input, from the export. See `_document_facts`: `text` is the
    # substrate every quote was verified against, and the database cannot supply
    # it because `text_ref` is a store location this lane may not read.
    text_of = {
        doc_id: text
        for thread in loaded.threads
        for doc_id, text in thread.raw_text_of.items()
    }
    facts, undatable = _document_facts(conn, loaded.document_ids, text_of)
    model_version_of = {
        r[0]: r[2]
        for r in conn.execute(
            "SELECT canonical_id, display_name, id FROM model_version"
        ).fetchall()
    }
    ledger = ExtractionLedger(conn)
    seen = ledger.already_extracted()

    print(f"threads     : {len(threads)}  ({len(seen)} already extracted, skipped)")
    print(f"documents   : {len(facts)} resolved"
          + (f", {len(undatable)} undatable" if undatable else ""))
    print(f"registry    : {len(model_version_of)} model_version rows")
    print(f"batch size  : {args.batch_size} threads per commit")
    print()

    pipeline = Pipeline(
        conn,
        client=OpenRouterClient.from_env(),
        capability_keys=list(capabilities().keys()),
        extractor_model=os.getenv("EXTRACTOR_MODEL", "google/gemini-2.5-flash"),
    )

    totals = {"verified": 0, "rejected": 0, "unclassified": 0, "stored": 0,
              "unsalvaged": 0, "threads": 0, "batches": 0}
    started = time.perf_counter()
    stopped_by_budget = False
    # THE SURFACES WE DECLINED TO GUESS. 347 of 450 verified claims were dropped
    # here on 2026-08-28 and the only trace was a log.info the default level does
    # not emit. Collected so the run REPORTS them rather than losing them.
    unresolved: list[str] = []
    unvetted = 0

    for start in range(0, len(threads), args.batch_size):
        slice_ = threads[start : start + args.batch_size]
        try:
            results = pipeline.run_all(
                slice_,
                facts=facts,
                model_version_of=model_version_of,
                budget=budget,
                already_extracted=seen,
                # DRIVER WITHHELD UNTIL THE LAST BATCH. `close_the_night` writes
                # labels and the changelog; running it per batch would record
                # nine "nights" in one evening and make the changelog's own
                # counts meaningless.
                driver=None,
                resolve_surface=resolver,
            )
        except BudgetExhausted as exc:
            # THE BATCH IS LOST, NOT THE RUN. Everything before this commit
            # boundary is already durable. `check_before_call` refuses the next
            # call rather than overshooting, so nothing was half-charged.
            print(f"\nBUDGET REACHED mid-batch: {exc}")
            print("  this batch is discarded; every earlier batch is committed.")
            conn.rollback()
            stopped_by_budget = True
            break

        # ONE COMMIT PER BATCH. Claims, cells and ledger rows together - the
        # ledger row must not outlive a rolled-back extraction, and must not die
        # with a successful one.
        conn.commit()
        totals["batches"] += 1
        totals["threads"] += len(slice_)
        for r in results:
            totals["verified"] += len(r.extraction.verified)
            totals["rejected"] += len(r.extraction.rejected)
            totals["unclassified"] += len(r.extraction.unclassified)
            totals["unsalvaged"] += len(r.extraction.unsalvaged)
            totals["stored"] += len(r.stored_claim_ids)
            unresolved.extend(r.unresolved_surfaces)
            unvetted += len(r.unvetted_documents)
        seen = ledger.already_extracted()

        elapsed = time.perf_counter() - started
        done = min(start + args.batch_size, len(threads))
        print(
            f"batch {totals['batches']:3d} committed · position {done}/{len(threads)}"
            f" · verified {totals['verified']} stored {totals['stored']}"
            f" · ${budget.spent_usd:.4f} of ${budget.limit_usd:.2f}"
            f" · {elapsed/60:.1f} min"
        )

    # THE NIGHTLY CLOSE, ONCE, AFTER THE LAST BATCH THAT RAN.
    if totals["stored"]:
        from judge.curate.nightly import close_the_night

        cells = pipeline._cells.rebuild_all()
        close_the_night(conn, driver=Driver(args.driver), as_of_cells=cells)
        conn.commit()
        print(f"\ncells rebuilt once: {len(cells)}, "
              f"{sum(1 for c in cells if c.publishes)} publish")

    print()
    print(f"threads processed : {totals['threads']} of {len(threads)}")
    print(f"proposed {totals['verified'] + totals['rejected'] + totals['unclassified']}"
          f" = verified {totals['verified']} + rejected {totals['rejected']}"
          f" + unclassified {totals['unclassified']}")
    print(f"unsalvaged        : {totals['unsalvaged']} (proposed and unbuildable)")
    print(f"stored            : {totals['stored']}")
    if unresolved:
        import collections as _c

        tally = _c.Counter(unresolved)
        print(f"unresolved surface: {len(unresolved)} claim(s) dropped at model "
              f"resolution, {len(tally)} distinct surface(s)")
        print("  Each is a REFUSAL TO INVENT SPECIFICITY, not a failure: a "
              "family name, an ambiguous codename or a range cannot name one "
              "model version. Named here because rule 4 says an absence we "
              "caused must not read as an absence we found.")
        for surface, n in tally.most_common(15):
            print(f"    {n:5d}  {surface!r}")
    if unvetted:
        print(f"unvetted documents: {unvetted} (E6 could not run - no text)")
    if totals["verified"] and not totals["stored"]:
        print("  VERIFIED BUT NOT STORED: either the documents could not be "
              "weighted or the models resolved to no tracked row.")
    print(f"batches committed : {totals['batches']}")
    print(f"spend             : {budget.summary()}")
    if stopped_by_budget:
        remaining = len(threads) - totals["threads"]
        print(f"\nSTOPPED BY THE CAP with {remaining} thread(s) unread. A resumed "
              f"run skips the {totals['threads']} already recorded in "
              f"thread_extraction and pays only for the rest.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
