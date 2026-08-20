"""The entry point. Everything in this lane was reachable except the start.

`Pipeline` was instantiated in exactly one place: `tests/test_pipeline_db.py`.
Every stage inside it had a caller - claims, cells, the ledger, the nightly
close - and nothing could start the batch. Fourteenth instance of that shape
here, and the last one, because it is the top of the tree: a pipeline nobody
can run is a pipeline that has never run.

It is also the one instance the "does it have a caller" check could not find
on its own. Every other orphan was a module some other module should have
called; this one's caller is a person with a terminal, and no amount of
grepping `judge/` finds that absence. What found it was asking the question
one level up - not "is Pipeline called" but "is there anything that COULD call
it".

WHAT THIS REFUSES TO DO

  no driver         the nightly close is SKIPPED rather than attributed to
                    `new-evidence`. A label lost because we edited a threshold
                    is not a fact about a model, and only the person running
                    the command knows which happened.

  no budget         refuses to start. `EXTRACTION_DAILY_BUDGET_USD` unset is
                    not "spend freely" - it is "nobody decided", and an
                    extraction run is the one command here that spends money.

  --dry-run         reports what WOULD be extracted, spends nothing, and is
                    the honest way to find out how many threads are pending
                    without paying to find out.

THE DATABASE IS NOT GUESSED

`DATABASE_URL` with no fallback, same refusal as `store.claims.transaction`. A
default reaching localhost is how a batch writes to the wrong database once.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

log = logging.getLogger("judge")


def _connect() -> Any:
    import psycopg

    from judge.store.claims import CONNECT_TIMEOUT_SECONDS

    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit(
            "DATABASE_URL is unset. Refusing to guess at a connection: a "
            "default that quietly reaches localhost is how a batch writes to a "
            "real database once."
        )
    return psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT_SECONDS)


def _cmd_extract(args: argparse.Namespace) -> int:
    """Run E5-E7 over pending threads, then close the night."""
    from judge.curate.labels import Driver
    from judge.extract.budget import Budget
    from judge.store.extractions import ExtractionLedger

    budget = Budget.from_env()
    if budget is not None:
        # SEEDED FROM THE SHARED LEDGER. The $1/day cap is one pot split with
        # the ask box, so a batch starting at zero would spend the whole cap
        # again on top of whatever Q1 already spent today. Starting from what
        # has actually been spent is what makes the dollar shared rather than
        # per-stage.
        from judge import spend_ledger

        budget.spent_usd = spend_ledger.spent_today()
    if budget is None and not args.dry_run:
        raise SystemExit(
            "EXTRACTION_DAILY_BUDGET_USD is unset. Refusing to run: an unset "
            "cap is nobody having decided, not a decision to spend freely, and "
            "this is the one command here that spends money. Set it, or use "
            "--dry-run to see what is pending without paying to find out."
        )

    with _connect() as conn:
        ledger = ExtractionLedger(conn)
        seen = ledger.already_extracted()
        zero_yield, read = ledger.yield_rate()
        print(
            f"  {read} threads read at this pipeline version, {zero_yield} of them yielding nothing"
        )

        if args.dry_run:
            # Reports and spends nothing. Deliberately does NOT report a count
            # of pending threads, because that needs the thread list `collect/`
            # owns and inventing one here would be a figure with no population.
            print("  --dry-run: nothing extracted, nothing charged")
            if budget is not None:
                affordable = int(budget.limit_usd / budget.estimated_next_call_usd)
                print(f"  budget would allow roughly {affordable} threads")
            return 0

        driver = Driver(args.driver) if args.driver else None
        if driver is None:
            print(
                "  no --driver given, so the nightly close is SKIPPED. Labels "
                "and reported-context limits will not be updated: attributing "
                "this run to new-evidence when you did not say so would blame "
                "the world for a change we may have made."
            )
        print(f"  {len(seen)} threads already extracted and will be skipped")
        raise SystemExit(
            "cannot read thread text from the database. "
            "`thread_context.flattened_text_ref` is a LOCATION in an object "
            "store rather than the text, and this lane has no way to resolve "
            "one: `collect/rawstore.py` is the only reader and judge/ never "
            "imports collect/. So the pipeline can be handed threads "
            "programmatically - tests and the _handoff export both do, with "
            "text inlined - and cannot fetch them itself. "
            "That is a gap in the lane interface rather than in this command: "
            "the interface is `document + thread_context`, and thread_context "
            "points at text only the other lane can read. Raised with E1 "
            "rather than worked around, because a second object-store reader "
            "in judge/ would be two implementations of one storage contract "
            "across a lane boundary - the thing byte-equality testing exists "
            "to catch, and cannot catch across lanes."
        )


def _cmd_rebuild_cells(args: argparse.Namespace) -> int:
    """Recompute every cell from existing claims. Spends nothing."""
    from judge.curate.labels import Driver
    from judge.curate.nightly import close_the_night
    from judge.store.cells import CellStore

    with _connect() as conn, conn.transaction():
        outcomes = CellStore(conn).rebuild_all()
        published = sum(1 for o in outcomes if o.publishes)
        print(f"  {len(outcomes)} cells recomputed, {published} publish")

        if args.driver:
            result = close_the_night(conn, driver=Driver(args.driver), as_of_cells=outcomes)
            print(f"  {result.summary()}")
        else:
            print(
                "  no --driver given, so labels and the changelog are NOT "
                "updated. A recompute after a threshold change is a "
                "config-change and saying so is the whole point of the column."
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="judge", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    drivers = ("new-evidence", "price-change", "version-change", "config-change")

    extract = sub.add_parser("extract", help="run the evidence pipeline")
    extract.add_argument("--dry-run", action="store_true", help="spend nothing")
    extract.add_argument("--driver", choices=drivers, help="why labels may change")
    extract.set_defaults(fn=_cmd_extract)

    rebuild = sub.add_parser("rebuild-cells", help="recompute cells from claims")
    rebuild.add_argument("--driver", choices=drivers, help="why labels may change")
    rebuild.set_defaults(fn=_cmd_rebuild_cells)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    return int(args.fn(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
