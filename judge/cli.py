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

  --dry-run         reports the ledger and the budget, spends nothing, and
                    TAKES NO WRITE GATE - `writing=` is None on this path, so
                    it runs from a development laptop pointed at the shared
                    database, which is where the question is usually asked.

                    It does NOT report pending threads and does not open the
                    export. Both need something this command does not have,
                    and saying "what WOULD be extracted" claimed otherwise.

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

    # `writing=` ON A REAL RUN ONLY. It turns on `judge/writeguard.py`, which
    # refuses ENVIRONMENT=development against a database that is not this
    # machine - correct for a run that spends money and writes claims, and
    # wrong for one that returns before it opens a transaction. `judge
    # reweight` already spells it this way, and its dry run is the weaker case:
    # that one writes inside a transaction and rolls it back, while everything
    # this path touches below is a SELECT.
    with _connect(writing=None if args.dry_run else "judge extract") as conn:
        ledger = ExtractionLedger(conn)
        seen = ledger.already_extracted()
        zero_yield, read = ledger.yield_rate()
        print(
            f"  {read} threads read at this pipeline version, {zero_yield} of them yielding nothing"
        )
        # ABOVE THE DRY-RUN RETURN, so both paths report it. Below, `seen` was
        # a query the dry run paid for and nothing read - and it is the count a
        # dry run is being asked for.
        print(f"  {len(seen)} threads already extracted and will be skipped")

        if args.dry_run:
            # Reports and spends nothing. Deliberately does NOT report a count
            # of pending threads, because that needs the thread list `collect/`
            # owns and inventing one here would be a figure with no population.
            # The line above is ALREADY-EXTRACTED, read from `thread_extraction`
            # at this pipeline version; it is not pending and must not be read
            # as pending.
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



#: `collect/registry/propose.py:150`'s ROUTE_PREFIX, restated rather than
#: imported: `tests/test_lane_boundary.py` forbids judge/ importing collect/ in
#: either direction, with no allowlist. One character, one ruling, and the
#: ruling is named below so a reader can find the original.
_ROUTE_PREFIX = "~"


def _assert_model_is_registered(conn: Any, model: str) -> None:
    """Refuse an extractor id the registry has never polled, before paying.

    WHAT THIS CATCHES. A typo, a renamed slug, or a model the vendor withdrew.
    All three currently fail at the first API call, after the run has started,
    the budget has been seeded and the ledger has an open row - and the error
    that comes back is a provider 404 about a model id, which reads as an
    outage rather than as a configuration mistake.

    THREE OUTCOMES AND THEY ARE DISTINCT, because collapsing them is the defect
    (rule 6). An empty registry is SKIPPED AND NAMED rather than counted as a
    pass: a fresh database has no `model_version` rows, and refusing there would
    block a legitimate first run on the absence of a poller.

        registry has no rows      skipped, and says so
        id present and a ROUTE    refused - routes are not models
        id absent                 refused
        id present                proceeds, and says which

    A ROUTE IS REFUSED ON PURPOSE. `~vendor/model-latest` points at whatever the
    vendor currently ships, so the model that served the request is unknown BY
    CONSTRUCTION - which is precisely what `claim.extractor_model` exists to
    record. Ruled 2026-08-18, `collect/registry/propose.py`: routes are not
    models.
    """
    total = conn.execute("SELECT count(*) FROM model_version").fetchone()[0]
    if not total:
        print(
            "  extractor not checked against the registry: model_version has 0 "
            "rows on this database. SKIPPED, not passed - seed or poll it and "
            "this check becomes real."
        )
        return

    row = conn.execute(
        "SELECT canonical_id FROM model_version WHERE canonical_id = %s", (model,)
    ).fetchone()
    if row is None:
        raise SystemExit(
            f"EXTRACTOR_MODEL is {model!r} and no row in `model_version` has that "
            f"canonical_id, across {total} polled models. Refusing before the "
            f"first call rather than taking a provider 404 mid-run.\n\n"
            f"Check the spelling against the registry. If the id is right and the "
            f"registry is stale, poll it - do not edit this check."
        )
    if model.startswith(_ROUTE_PREFIX):
        raise SystemExit(
            f"EXTRACTOR_MODEL is {model!r}, which is a ROUTE rather than a model: "
            f"it points at whatever the vendor currently ships, so the model that "
            f"served each request is unknown by construction.\n\n"
            f"`claim.extractor_model` exists to record what produced a row, and a "
            f"route makes that unanswerable. Name the model instead. "
            f"(Routes are not models - ruled 2026-08-18.)"
        )
    print(f"  extractor {model} is in the registry ({total} polled models)")


def _document_facts(
    conn: Any,
    document_ids: set[str],
    text_of: dict[str, str] | None = None,
) -> tuple[dict[str, Any], set[str]]:
    """`DocumentFacts` for the documents an export refers to, read from the DB.

    Read rather than taken from the export: `platform` and `created_at` decide
    weighting, and a figure the input supplies is a figure the run cannot check.
    A document the database does not have is OMITTED, never defaulted - the
    pipeline already skips a claim whose document it knows nothing about rather
    than weighting it from defaults, and inventing a platform here would silently
    change `f_platform`.

    `text_of` IS THE ONE THING TAKEN FROM THE EXPORT, and the reasoning above is
    why it has to be. E6 hard rejection had NEVER RUN on this path: `text` was
    never populated, so `pipeline.py`'s vet step took the `unvetted` branch for
    every document in every run. `unvetted` is correctly designed - it is not
    counted as `kept` - but nothing persists it, so a claim no rule ran against
    was indistinguishable from one that passed every rule.

    The rule above does not extend to `text`. `platform` and `created_at` are
    FIGURES that feed a weight and the export could lie about them undetectably.
    `text` is the SUBSTRATE: it is what the model was shown and what every quote
    was verified against by exact substring. There is nothing to check it
    against because it is the thing everything else is checked against - and the
    database cannot supply it anyway, since `document.text_ref` is a store
    location and this lane may not read the store.
    """
    from judge.pipeline import DocumentFacts

    if not document_ids:
        return {}, set()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, source, created_at, author_id, has_numbers, has_conditions, "
            "       dedup_cluster_id, is_canonical_in_cluster "
            "FROM document WHERE id = ANY(%s)",
            (list(document_ids),),
        )
        rows = cur.fetchall()

    facts: dict[str, Any] = {}
    undatable: list[str] = []
    for (doc_id, source, created_at, author_id, has_numbers, has_conditions,
         dedup_cluster_id, is_canonical_in_cluster) in rows:
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
            # ⚠ READ SINCE 2026-09-11, AND THE SECOND HALF OF THE SAME GAP.
            #   `judge/vet/reject.py:check` has always taken these and defaulted
            #   to "not clustered, is canonical" — so a syndicated copy counted
            #   as an independent voice. Wiring the WRITER
            #   (`collect/assemble/dedupe_write.py`) was not enough on its own:
            #   this SELECT did not read the columns, so `DocumentFacts` kept
            #   its dataclass defaults and the check still saw every copy as
            #   canonical. A writer and a reader, or neither does anything.
            #
            #   `contract/column_states.yaml` is what caught it — the columns
            #   were "written, UNREAD" and the manifest refused the claim that
            #   anything read them.
            dedup_cluster_id=dedup_cluster_id,
            # NULL means "clustering has not looked at this document", not "it
            # is an original". True is the right reading of an unclustered
            # document and the wrong reading of an unexamined one; they are
            # only distinguishable through `dedup_cluster_id` being NULL too,
            # which is why both travel together.
            is_canonical_in_cluster=(
                True if is_canonical_in_cluster is None else is_canonical_in_cluster
            ),
            # THE EXTRACTOR PROPOSES THESE AND THE COUNT DECIDES (pipeline.py:161).
            #
            # ⚠ READ FROM THE TABLE SINCE 2026-08-30. These were literal `None`,
            #   and the comment here said `None` was "not established here rather
            #   than False, so a disagreement gets recorded instead of resolved
            #   by a default". The first half was true and the second was not:
            #   `compute()`'s refusal tested `value is UNSUPPLIED`, so the `None`
            #   went straight through and `specificity_factor` read it as falsy.
            #   Every claim this pipeline has ever written was weighted as though
            #   both were False, on a path whose whole purpose was to make that
            #   impossible. `compute()` now refuses `None` as well, so a document
            #   that HAS the value must supply it or its claims are dropped -
            #   which is why these are read rather than left as a sentinel.
            #
            #   ⚠ THE COLUMNS ARE NULL ON MOST DOCUMENTS AND THAT IS NOW A
            #     REFUSAL, NOT A ZERO. `collect/triage/specificity.py` computes
            #     both and nothing writes them - `contract/column_states.yaml`
            #     carries them as `unwired` with the gap named. So this fix moves
            #     the failure from a silent wrong weight to a loud dropped claim,
            #     and the remaining repair is in the other lane: write the
            #     columns. `scripts/measure_document_facts_gap.py` is what says
            #     how many claims that is.
            names_version=None,
            has_conditions=has_conditions,
            has_numbers=has_numbers,
            # E6'S INPUT. None keeps the honest `unvetted` branch for a document
            # the export did not carry; it no longer means "every document".
            text=(text_of or {}).get(doc_id),
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
    from judge.extract.client import OpenRouterClient, extractor_model
    from judge.pipeline import Pipeline

    loaded = export_source.load(Path(args.from_export))
    for name, why in loaded.skipped:
        print(f"  SKIPPED {name}: {why}")
    if not loaded.threads:
        raise SystemExit("no thread in that export carried usable text; nothing to run")

    # `raw_text_of` is keyed by member document id and carries the prose each
    # quote was verified against - exactly what `reject_check` needs.
    text_of = {
        doc_id: text
        for thread in loaded.threads
        for doc_id, text in thread.raw_text_of.items()
    }
    facts, undatable = _document_facts(conn, loaded.document_ids, text_of)
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

    # ONE RESOLUTION, USED TWICE. `from_env()` calls the same function, so the
    # model we CALL and the model we RECORD cannot diverge. They used to be two
    # `os.getenv` reads with two separately-hardcoded fallbacks that agreed by
    # coincidence.
    model = extractor_model()
    _assert_model_is_registered(conn, model)

    results = Pipeline(
        conn,
        client=OpenRouterClient.from_env(),
        capability_keys=list(capabilities().keys()),
        extractor_model=model,
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
    fabricated = sum(r.extraction.fabricated for r in results)
    encoding = sum(r.extraction.encoding_mismatches for r in results)
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
    if rejected:
        # SPLIT THE REJECTIONS, because fabrication and a re-encoded quote are
        # opposite findings and this print is the only place the count lives -
        # `claim_verified_ck` forbids storing a failed quote. Folding them was
        # the difference between the real fabrication rate and one twice as high.
        other = rejected - fabricated - encoding
        print(
            f"    of which fabricated {fabricated} (absent even normalised) · "
            f"encoding {encoding} (present re-encoded, recoverable) · other {other}"
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


class _RolledBack(Exception):
    """Ends the dry run's transaction without committing. Never escapes."""


def _print_cell_deltas(pairs, names: dict[str, str] | None = None) -> int:
    """n_eff before and after per cell, how many crossed the gate, and what was lost.

    `names` maps `model_version.id` to `canonical_id`. Cells are keyed on the
    internal id, and `mv1` on a line that is supposed to answer "which model
    publishes first" is a row a reader has to go and look up.
    """
    from judge.curate.gate import N_EFF_MINIMUM
    from judge.reweight import quieter_cells, summarise_losses

    names = names or {}

    crossed = 0
    moved = 0
    print(f"\n  CELLS - n_eff before -> after, gate at {N_EFF_MINIMUM}")
    for before, after in pairs:
        if after is None:
            print(f"    {names.get(before.key.model_version_id, before.key.model_version_id):32s} "
                  f"{before.key.capability_key:26s} GONE - every claim refused")
            continue
        was = before.counts.n_eff if before else 0.0
        now = after.counts.n_eff
        if now >= N_EFF_MINIMUM > was:
            crossed += 1
        shrank = before is not None and (
            after.counts.independent_voices < before.counts.independent_voices
            or after.counts.platform_count < before.counts.platform_count
        )
        if abs(now - was) > 1e-9 or shrank:
            moved += 1
            print(f"    {names.get(after.key.model_version_id, after.key.model_version_id):32s} "
                  f"{after.key.capability_key:26s} "
                  f"{was:.4f} -> {now:.4f}  "
                  f"voices={after.counts.independent_voices} "
                  f"platforms={after.counts.platform_count}"
                  f"{'   CROSSES' if now >= N_EFF_MINIMUM else ''}")
    print(f"\n  {moved} cells moved, {crossed} crossed {N_EFF_MINIMUM}")
    if not crossed:
        # THE NUMBER THAT MATTERS AS MUCH AS THE OTHER ONE. A re-weight that
        # publishes nothing is a result, and printing only the movers would let
        # it read as a run that had not finished.
        print("  NOTHING NEW PUBLISHES. The gate is unchanged and unmet.")

    # ITS OWN SECTION, PRINTED WHETHER OR NOT ANYTHING WAS LOST. A quieter board
    # is the direction nobody checks: every other line here notices evidence
    # arriving, and a section that appears only on bad news teaches the reader
    # that its absence means nothing was looked at.
    print()
    print(summarise_losses(quieter_cells(pairs), names))
    return crossed


def _cmd_reweight(args: argparse.Namespace) -> int:
    """Re-price stored claims under the current PIPELINE_VERSION. Spends nothing.

    A DRY RUN BY DEFAULT, and that is not a nicety. A re-weight moves every
    number on the board, so the arithmetic is the argument for making the
    change and has to be readable before a row exists. Both paths write inside
    one transaction - the cells can only be priced from claims that are IN the
    table - and the dry run rolls that transaction back.
    """
    from judge.curate.labels import Driver
    from judge.curate.nightly import close_the_night
    from judge.reweight import apply as apply_reweight
    from judge.reweight import cell_deltas, plan, summarise
    from judge.store.cells import CellStore
    from judge.store.claims import PIPELINE_VERSION

    to_version = args.to_version or PIPELINE_VERSION
    with _connect(writing="judge reweight" if args.apply else None) as conn:
        report = plan(
            conn,
            from_version=args.from_version,
            to_version=to_version,
            document_facts=args.document_facts,
            specificity=args.specificity,
        )
        print(summarise(report))

        try:
            with conn.transaction():
                written = apply_reweight(conn, report)
                names = dict(
                    conn.execute("SELECT id, canonical_id FROM model_version").fetchall()
                )
                _print_cell_deltas(cell_deltas(conn, report), names)
                if not args.apply:
                    raise _RolledBack
                print(f"\n  wrote {written} claims at {to_version}")
        except _RolledBack:
            print(
                "\n  DRY RUN - rolled back, nothing written. The figures above "
                "are what --apply would produce."
            )
            return 0

        with conn.transaction():
            # AT `to_version`, NOT AT PIPELINE_VERSION. A run producing the
            # e5.2 intermediate must rebuild cells from the claims it just
            # wrote; the default constant points at e5.3 and would have
            # rebuilt from a version with no rows - "0 cells, 0 publish",
            # which reads as a finished run that found nothing.
            outcomes = CellStore(conn, pipeline_version=to_version).rebuild_all()
            published = sum(1 for o in outcomes if o.publishes)
            print(f"  {len(outcomes)} cells rebuilt, {published} publish")
            if args.driver:
                result = close_the_night(
                    conn, driver=Driver(args.driver), as_of_cells=outcomes
                )
                print(f"  {result.summary()}")
            else:
                print(
                    "  no --driver given, so labels and the changelog are NOT "
                    "updated. A re-weight is a config-change and saying so is "
                    "the whole point of the column."
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

    # RE-WEIGHT IS NOT RE-EXTRACT AND NOT REBUILD-CELLS. It re-prices stored
    # claims under the current PIPELINE_VERSION, which is the only way a change
    # to contract/harvest.yaml reaches rows that already exist. No model call.
    reweight = sub.add_parser(
        "reweight", help="re-price stored claims at the current pipeline version"
    )
    reweight.add_argument(
        "--from-version",
        required=True,
        metavar="V",
        help="the pipeline version to re-price FROM, e.g. e5.1. Required rather "
        "than inferred: guessing which fork is the baseline is how a diff gets "
        "computed against the wrong one.",
    )
    reweight.add_argument(
        "--to-version",
        metavar="V",
        help="the version to write. Defaults to PIPELINE_VERSION. Given "
        "explicitly to produce an INTERMEDIATE fork - e5.2 exists only so the "
        "tier ruling and the document-facts ruling get one diff each.",
    )
    reweight.add_argument(
        "--document-facts",
        choices=("frozen", "read"),
        default="read",
        help="frozen: hold has_numbers/has_conditions at the values e5.1 "
        "effectively used (both False), so only f_evidence moves. read: take "
        "them from the document, which is the 2026-08-30 ruling and refuses a "
        "NULL. One ruling per run.",
    )
    reweight.add_argument(
        "--specificity",
        choices=("legacy", "current"),
        default="current",
        help="legacy: the four-signal f_specificity, in force until 2026-08-30. "
        "current: Option 1's two signals. Needed to reproduce the BEFORE side of "
        "a version that predates Option 1 - a diff against a formula that never "
        "applied is a diff about nothing.",
    )
    reweight.add_argument(
        "--apply", action="store_true", help="write. Without it, a dry run."
    )
    reweight.add_argument("--driver", choices=drivers, help="why labels may change")
    reweight.set_defaults(fn=_cmd_reweight)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    return int(args.fn(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
