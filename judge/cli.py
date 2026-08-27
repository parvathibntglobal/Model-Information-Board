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


def _connect(*, writing: str | None = None) -> Any:
    """A connection, and for a WRITE command one refusal before it opens.

    `writing` names the command. Passing it turns on the check in
    `judge/writeguard.py`, which refuses ENVIRONMENT=development pointed at a
    remote database - the flag switches the build-fixture guard off, and this
    lane's write commands had no gate of any kind. `collect/cli.py` runs
    `_gate()` on its writes; nothing here did.

    Read commands do not pass it, deliberately: the state this refuses is
    exactly the state somebody needs to read the board to diagnose.
    """
    import psycopg

    from judge.store.claims import CONNECT_TIMEOUT_SECONDS

    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit(
            "DATABASE_URL is unset. Refusing to guess at a connection: a "
            "default that quietly reaches localhost is how a batch writes to a "
            "real database once."
        )

    if writing:
        from judge.writeguard import UnsafeWriteRefused, check

        try:
            check(url, command=writing)
        except UnsafeWriteRefused as refusal:
            raise SystemExit(str(refusal)) from refusal

    return psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT_SECONDS)


def _cmd_extract(args: argparse.Namespace, *, resolver_factory=None) -> int:
    """Run E5-E7 over pending threads, then close the night.

    `resolver_factory` IS HOW MODEL IDENTITY CROSSES THE LANE BOUNDARY. This
    lane may not import `collect/`, so it cannot build the surface resolver
    itself — the composition root does (`scripts/run_extraction.py`), and passes
    `RegistrySurfaceResolver.from_connection` here. Built inside the connection
    below, because the resolver reads `model_version` off the same `conn`.

    Default `None` keeps `judge extract` lane-clean and reproduces the previous
    behaviour exactly: with no resolver, claims resolve only through
    `resolved_version_id`, which nothing populates, so every claim is skipped.
    That was the whole "stores nothing" symptom, and it is a missing composition
    root rather than a defect — see `judge.pipeline.SurfaceResolver`.
    """
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

    with _connect(writing="judge extract") as conn:
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
        if getattr(args, "from_export", None):
            resolve_surface = resolver_factory(conn) if resolver_factory is not None else None
            return _extract_from_export(
                args, conn, ledger, seen, budget, driver, resolve_surface=resolve_surface
            )

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



def _document_facts(conn: Any, document_ids: set[str]) -> tuple[dict[str, Any], set[str]]:
    """`DocumentFacts` for the documents an export refers to, read from the DB.

    Read rather than taken from the export: `platform` and `created_at` decide
    weighting, and a figure the input supplies is a figure the run cannot check.
    A document the database does not have is OMITTED, never defaulted - the
    pipeline already skips a claim whose document it knows nothing about rather
    than weighting it from defaults, and inventing a platform here would silently
    change `f_platform`.
    """
    from judge.pipeline import DocumentFacts

    if not document_ids:
        return {}, set()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, source, created_at, author_id FROM document WHERE id = ANY(%s)",
            (list(document_ids),),
        )
        rows = cur.fetchall()

    facts: dict[str, Any] = {}
    undatable: list[str] = []
    for doc_id, source, created_at, author_id in rows:
        if created_at is None:
            undatable.append(doc_id)
            # OMITTED, NOT DATED FROM A DEFAULT. `recency_factor` subtracts this
            # from `as_of`, so a missing date crashes weighting - and the only
            # defaults available are wrong in a direction that matters: today
            # makes an old document look fresh and inflates its weight, and a
            # floor date makes a new one look stale. Rule 6: a missing value does
            # not become a definite one. Omitting sends the claim down the
            # already-designed "no document facts" path, which skips and names it.
            #
            # This bites on `_handoff/load.sql`, which carries no `created_at` -
            # 0 of 7 locally against 57 of 57 on staging.
            continue
        facts[doc_id] = DocumentFacts(
            document_id=doc_id,
            platform=source,
            created_at=created_at.date() if hasattr(created_at, "date") else created_at,
            # THE FIX FOR THE PUBLISH BLOCKER. Read from the document so the
            # claim carries its author and distinct people count as distinct
            # voices. NULL stays NULL — an unknown author becomes the anonymous
            # per-platform fallback in cells.py, never an invented identity.
            author_id=author_id,
            # THE EXTRACTOR PROPOSES THESE AND THE COUNT DECIDES (pipeline.py:161).
            # None is "not established here" rather than False, so a disagreement
            # gets recorded instead of resolved by a default.
            names_version=None,
            has_conditions=None,
            has_numbers=None,
        )
    if undatable:
        # NAMED SEPARATELY from documents the database does not have. "Not in
        # this database" and "here but carrying no date" are different repairs -
        # one is a missing row, the other is a missing column value - and the
        # first version of this reported both as absence, which is the same
        # conflation this whole pipeline exists to refuse.
        print(
            f"  {len(undatable)} document(s) present but carrying no created_at, "
            f"so unweightable:"
        )
        for doc_id in undatable[:5]:
            print(f"      {doc_id}")
    return facts, set(undatable)


def _model_version_map(conn: Any) -> dict[str, str]:
    """`canonical_id -> model_version.id`, the map `pipeline.py:150` looks in.

    A claim whose resolved id is absent here is skipped and logged, never
    guessed. So the size of this map caps what a run can store, which is why the
    caller prints it: low yield is a registry question before it is a prompt one.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT canonical_id, id FROM model_version WHERE canonical_id IS NOT NULL")
        return {canonical: mv_id for canonical, mv_id in cur.fetchall()}


def _extract_from_export(
    args: argparse.Namespace,
    conn: Any,
    ledger: Any,
    seen: Any,
    budget: Any,
    driver: Any,
    *,
    resolve_surface: Any = None,
) -> int:
    """Run E5-E7 over an export that carries its own text.

    THE FIRST PRODUCTION CALLER `Pipeline` HAS EVER HAD. It was constructed in
    exactly one place in the repository - `tests/test_pipeline_db.py` - so the
    whole write path was real, covered against a live database, and unreachable
    from outside the suite. `claim` and `cell` being empty is partly that.
    """
    from pathlib import Path

    from judge.config import capabilities
    from judge.extract import export_source
    from judge.extract.client import OpenRouterClient
    from judge.pipeline import Pipeline

    loaded = export_source.load(Path(args.from_export))
    for name, why in loaded.skipped:
        print(f"  SKIPPED {name}: {why}")
    if not loaded.threads:
        raise SystemExit("no thread in that export carried usable text; nothing to run")

    facts, undatable = _document_facts(conn, loaded.document_ids)
    # UNDATABLE SUBTRACTED, because they are not missing. A document present but
    # carrying no created_at was already reported with that reason; counting it
    # again as "no row in this database" would state the wrong repair twice.
    missing = sorted(loaded.document_ids - set(facts) - undatable)
    if missing:
        # Named, because a claim on one of these is dropped downstream and the
        # run would otherwise report a yield without saying what it could not
        # weigh.
        print(f"  {len(missing)} document(s) in the export have no row in this database:")
        for doc_id in missing[:5]:
            print(f"      {doc_id}")

    model_version_of = _model_version_map(conn)
    print(f"  {len(loaded.threads)} thread(s) with text, {len(facts)} document(s) resolved")
    print(f"  {len(model_version_of)} model_version rows to resolve claims against")
    if resolve_surface is None:
        # STATED, NOT SILENT. Without a resolver the model's SURFACE ("sonnet 4")
        # never maps to a model_version, and claims resolve only through
        # `resolved_version_id`, which nothing populates — so every claim is
        # skipped. That is the "stores nothing" symptom, and printing it here
        # stops the next run reading a zero as "the corpus said nothing".
        print(
            "  NO SURFACE RESOLVER: claims will resolve only via resolved_version_id "
            "(unpopulated), so all will be skipped. Run via scripts/run_extraction.py "
            "to wire the registry resolver."
        )
    else:
        print("  surface resolver wired (registry): claims resolve by the surface written")

    results = Pipeline(
        conn,
        client=OpenRouterClient.from_env(),
        capability_keys=list(capabilities().keys()),
        extractor_model=os.getenv("EXTRACTOR_MODEL", "google/gemini-2.5-flash"),
    ).run_all(
        loaded.threads,
        facts=facts,
        model_version_of=model_version_of,
        budget=budget,
        already_extracted=seen,
        driver=driver,
        resolve_surface=resolve_surface,
    )

    verified = sum(len(r.extraction.verified) for r in results)
    rejected = sum(len(r.extraction.rejected) for r in results)
    unclassified = sum(len(r.extraction.unclassified) for r in results)
    proposed = verified + rejected + unclassified
    stored = sum(len(r.stored_claim_ids) for r in results)
    cells = sum(len(r.cells) for r in results)
    retries = sum(r.extraction.schema_retries for r in results)

    conn.commit()

    # EVERY STAGE'S COUNT, not a single figure. The first live run proposed 8,
    # verified 8 and stored 0 - each one dropped at model resolution - and
    # "eight claims" then travelled for two days with neither "verified" nor
    # "stored zero" attached, until it had been read as eight claims held by the
    # board. A count that cannot say which stage it describes is the defect,
    # not the number.
    print(
        f"  proposed {proposed} = verified {verified} + rejected {rejected} "
        f"+ unclassified {unclassified}"
    )
    print(f"  stored {stored} · cells {cells} · schema retries {retries}")
    if verified and not stored:
        # TWO CAUSES, AND THIS MUST NOT PICK ONE. `pipeline.run` drops a verified
        # claim either because the document has no facts (unweightable) or
        # because its model resolves to no tracked row. An earlier version
        # asserted the second, and the first run it met was the first - stating a
        # registry gap while the real repair was a missing created_at. Both are
        # printed above with their own reasons; this line says the outcome and
        # points at them rather than choosing.
        print(
            f"  VERIFIED BUT NOT STORED: {verified} claim(s) passed verification and "
            f"none reached the database. Either their documents could not be weighted "
            f"or their models resolved to no tracked row - both are reported above. "
            f"Neither is recorded anywhere but this output; see the "
            f"claims_unresolved proposal."
        )
    for result in results:
        if result.extraction.no_claim_reason:
            print(
                f"      {result.extraction.thread_context_id}: "
                f"{result.extraction.no_claim_reason}"
            )
    if budget is not None:
        print(f"  {budget.summary()}")
    return 0


def _cmd_rebuild_cells(args: argparse.Namespace) -> int:
    """Recompute every cell from existing claims. Spends nothing."""
    from judge.curate.labels import Driver
    from judge.curate.nightly import close_the_night
    from judge.store.cells import CellStore

    with _connect(writing="judge rebuild-cells") as conn, conn.transaction():
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
    extract.add_argument(
        "--from-export",
        metavar="DIR",
        help="threads exported with inlined text; a stopgap, see export_source.py",
    )
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
