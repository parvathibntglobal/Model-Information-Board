"""collect/ command line.

    py -3 -m collect.cli db init
    py -3 -m collect.cli registry check-sources
    py -3 -m collect.cli registry aliases
    py -3 -m collect.cli registry load-seed --dry-run
    py -3 -m collect.cli registry load-seed --allow-unsourced
    py -3 -m collect.cli registry tracked-set --surfaces F --mention-floor N \
        --launch-window-days D

Cron calls these. There is no scheduler here and there will not be one — a
jobs table and cron is enough for eight scheduled jobs.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from collect.config import settings
from collect.registry.aliases import all_alias_rows, find_collisions
from collect.registry.seed import (
    gaps_by_model,
    load_seed_file,
    source_gaps,
    sourced_field_total,
)


def _cmd_db_init(args: argparse.Namespace) -> int:
    from collect.db import apply_schema, reset_schema, transaction
    from collect.migrate import stamp_at_head

    with transaction() as conn:
        _gate(conn)
        if args.reset:
            reset_schema(conn, environment=settings().environment)
            print("schema reset and applied from contract/tables.sql")
        else:
            apply_schema(conn)
            print("schema applied from contract/tables.sql")
        # A schema built from tables.sql is BY DEFINITION at the head of the
        # chain - that is the whole content of the equivalence test. Recording
        # it is what stops `db migrate` then trying to create objects
        # tables.sql has already made. Without this, the first migration breaks
        # every new database rather than a corner case.
        stamped = stamp_at_head(conn)
        if stamped:
            print(
                f"ledger stamped at head: {len(stamped)} migration(s) recorded "
                "as applied without running - tables.sql already contains them"
            )
    return 0



def _cmd_db_check(args: argparse.Namespace) -> int:
    """Report pending migrations. Applies nothing, writes nothing.

    Exit 0 when the database is current, 1 when work is pending, 2 on a ledger
    mismatch — three states rather than two, because "pending" is a normal
    condition and "the ledger disagrees with the files" is not.
    """
    from collect.db import connect
    from collect.migrate import check

    conn = connect()
    try:
        status = check(conn)
        print(status.describe())
        if status.mismatched:
            return 2
        return 0 if status.is_current else 1
    finally:
        conn.close()


def _cmd_db_migrate(args: argparse.Namespace) -> int:
    """Apply pending migrations. Never runs automatically - see collect/migrate.py."""
    from collect.db import connect
    from collect.migrate import MigrationError, check, ensure_ledger, migrate

    conn = connect()
    try:
        _gate(conn)
        before = check(conn)
        if before.mismatched:
            print(before.describe())
            return 2
        if not before.pending_filenames:
            if not before.ledger_present:
                # A database predating the ledger is not current even with
                # nothing pending, and this is the sanctioned command for
                # convergence — so it creates the ledger rather than waiting for
                # a first migration to do it as a side effect.
                ensure_ledger(conn)
                conn.commit()
                print("created schema_migration; nothing else pending")
                return 0
            print("nothing pending")
            return 0
        try:
            applied = migrate(conn)
        except MigrationError as exc:
            print(str(exc))
            return 2
        conn.commit()
        for name in applied:
            print(f"applied {name}")
        print(check(conn).describe())
        return 0
    finally:
        conn.close()



def _gate(conn=None) -> None:
    """The startup checks, on WRITE commands only. Issue #27.

    Read-only commands are deliberately not gated: the state these checks refuse
    is exactly the state somebody needs `registry check-sources` to diagnose.
    """
    from collect.ops.preflight import preflight
    from collect.registry.policy import load_registry_policy

    report = preflight(
        conn, environment=settings().environment, policy=load_registry_policy()
    )
    print(report.summary())


def _cmd_ops_preflight(args: argparse.Namespace) -> int:
    """Run the startup checks and report, without running the chain."""
    from collect.db import connect
    from collect.ops.preflight import PreflightRefused

    conn = None
    try:
        conn = connect()
    except Exception as error:  # noqa: BLE001 - a refusal reports, it does not raise
        print(f"no database connection: {type(error).__name__}: {error}")
    try:
        _gate(conn)
    except PreflightRefused as refusal:
        print(str(refusal))
        return 1
    finally:
        if conn is not None:
            conn.close()
    return 0


def _cmd_ops_run(args: argparse.Namespace) -> int:
    """The nightly chain. Runs what exists and says what does not."""
    from collect.db import connect
    from collect.http import build_client
    from collect.ops.chain import Journal, default_stages, run_chain
    from collect.registry.policy import load_registry_policy

    conn = None
    if not args.no_database:
        try:
            conn = connect()
        except Exception as error:  # noqa: BLE001
            print(f"no database connection: {type(error).__name__}: {error}")

    # THE OVERLAP GUARD, WHICH IS WHAT A SCHEDULER NEEDS AND NOTHING ASKED FOR.
    # `ops/ledger.py:unfinished()` was written for exactly this question — rows
    # that started and never concluded — and had no caller, so two cron runs
    # could interleave and `job_run` would hold both with nothing saying so.
    #
    # It REPORTS AND REFUSES rather than waiting or killing, and it does not
    # invent a staleness threshold. An unfinished row means one of two things and
    # only the operator can tell them apart: a run still going, or a run that was
    # killed. Both are worth seeing; neither should be guessed at. `--force`
    # proceeds, so a stale row cannot block the chain forever — which is the
    # failure mode a silent lock would have.
    if conn is not None and not args.force:
        from collect.ops.ledger import unfinished

        stalled = unfinished(conn)
        if stalled:
            print(
                f"refusing: {len(stalled)} job_run row(s) started and never "
                f"finished. Either a run is still going, or one was killed - "
                f"finished_at IS NULL cannot tell those apart, and they need "
                f"opposite repairs."
            )
            for run_id, stage, started in stalled:
                print(f"  {stage:<22} started {started:%Y-%m-%d %H:%M:%S}  {run_id}")
            print("  Re-run with --force to proceed anyway.")
            return 1

    journal = Journal(Path(args.journal) if args.journal else None)
    context = {
        "conn": conn,
        "environment": settings().environment,
        "policy": load_registry_policy(),
    }

    # THE CLIENT NOTHING SUPPLIED. `_poll_registry_stage` reads
    # `context["client"]` and refuses with "no HTTP client supplied" when it is
    # absent — and `"client"` was set NOWHERE in this file, so `poll-registry`
    # refused on every invocation the chain has ever had. The stage was wired,
    # correct, and could not run: the registry's 340 rows were put there by a
    # hand-run, the same way `author`'s 4,391 were.
    #
    # Third instance of one shape this week. `load_source_rows` had no caller;
    # `undeclared_models` had no route check; this had no dependency. All three are
    # correct code that nothing reaches, and all three read as a considered
    # state from the outside — a refusal that names its reason is especially
    # good at that.
    #
    # NO CREDENTIAL. Verified live 2026-08-20 with the key removed from the
    # environment: no Authorization header, HTTP 200, 679,318 bytes, 414 feed
    # entries folding to 340 models, and no rate-limit headers. So a client is
    # free to supply and there is no reason to withhold it by default.
    client = None
    if not args.no_network:
        client = build_client()
        context["client"] = client

    try:
        run = run_chain(default_stages(), context, journal)
    finally:
        if client is not None:
            client.close()
        if conn is not None:
            conn.close()
    print(run.summary())
    return 0 if run.ok else 1


def _cmd_registry_propose_aliases(args: argparse.Namespace) -> int:
    """Propose alias surfaces for review. Writes a skeleton, decides nothing.

    Three inputs: mechanical variants derived from the registry, vendor-drop
    variants derived from a rule the corpus measured, and attested surfaces
    counted from stored documents when a surface file is supplied. Without one it
    still runs and every entry reads `mechanical-only`, which is "recall
    unmeasured" rather than "nobody discusses this model".

    Over the whole registry by default. `--mention-floor` and
    `--launch-window-days` narrow it to the tracked set (#33) — both required
    together, because a floor without a window silently drops every model too new
    to have been discussed, and a window without a floor is a date sort.
    """
    import json

    from collect.db import connect
    from collect.registry.propose import propose, summarise, to_yaml
    from collect.registry.tracked import (
        BY_MENTIONS,
        TrackedSetPolicy,
        attributable,
        select,
    )
    from collect.registry.tracked import summarise as summarise_selection

    observed = (
        attributable(json.loads(Path(args.surfaces).read_text(encoding="utf-8")))
        if args.surfaces
        else {}
    )

    conn = connect()
    try:
        rows = conn.execute(
            "SELECT canonical_id, display_name, release_date FROM model_version "
            "ORDER BY canonical_id"
        ).fetchall()
    finally:
        conn.close()

    scoped = args.mention_floor is not None or args.launch_window_days is not None
    if scoped:
        if args.mention_floor is None or args.launch_window_days is None:
            print(
                "--mention-floor and --launch-window-days must be given together. "
                "A floor alone drops every model released too recently to have "
                "been discussed; a window alone is a date sort, and the feed "
                "carries routing entries whose release_date is when a pointer "
                "moved rather than when anything launched.",
                file=sys.stderr,
            )
            return 2
        if not args.surfaces:
            print(
                "--mention-floor needs --surfaces. Without an extract every model "
                "is unmeasured, so a floor would select nothing by count and the "
                "set would be the launch window alone.",
                file=sys.stderr,
            )
            return 2
        # Named rather than inlined so the SAME object reaches both the selection
        # and the artifact. Two constructions from the same args would drift the
        # moment one gained a default.
        set_policy = TrackedSetPolicy(
            mention_floor=args.mention_floor,
            launch_window_days=args.launch_window_days,
        )
        selection = select(
            rows,
            observed,
            policy=set_policy,
            as_of=date.today(),
            basis={"surfaces": args.surfaces},
        )
        print(summarise_selection(selection))
        print()
        models = [(m.canonical_id, m.display_name) for m in selection.tracked]
        # Grounds travel into the artifact, AND SO DOES THE POLICY. `launch-window`
        # means "did not clear the mention floor" - which is not "unobserved" - so
        # a reader who cannot see the floor cannot tell those apart, and neither
        # can a check. Rule 7 at the top of the generated file.
        grounds = {
            m.canonical_id: ("attested" if BY_MENTIONS in m.grounds else "launch-window")
            for m in selection.tracked
        }
    else:
        models = [(r[0], r[1]) for r in rows]
        grounds = {}
        set_policy = None

    proposals = propose(models, observed)
    print(summarise(proposals))
    if args.out:
        refusal = _refuse_to_discard_review(Path(args.out), force=args.force)
        if refusal is not None:
            print(refusal, file=sys.stderr)
            return 2
        Path(args.out).write_text(
            to_yaml(proposals, seated_by=grounds, policy=set_policy), encoding="utf-8"
        )
        print(f"wrote {args.out} — review required, not loadable as-is")
    return 0


#: Words a REVIEWER writes into the artifact and the generator cannot produce.
#: Used only to make a refusal specific, never to decide whether to refuse — the
#: refusal is on the file EXISTING, because an absence of these words is not
#: evidence that nobody edited it (rule 6, and habit 11: a name match tells you a
#: string exists, not that a thing does).
REVIEW_MARKERS = ("reseated", "DEMOTED", "accepted", "rejected", "reviewed")


def _refuse_to_discard_review(out: Path, *, force: bool) -> str | None:
    """Refuse to overwrite an artifact a human may have ruled on. None to proceed.

    **THE PROPERTY: running the generator cannot SILENTLY discard a decision.**
    Before this, `--out` overwrote whatever was there. Two deepseek reseats and
    six dropped `(free)` forms lived only in the written file, and the only thing
    preventing their loss was that nobody had re-run the command.

    REFUSE-TO-OVERWRITE RATHER THAN AN OVERRIDES FILE, and it is the smaller of
    the two by a wide margin. An overrides file needs a location (`contract/` is
    shared, so it needs flagging), a schema, apply-order semantics, a rule for an
    override naming a model no longer in the tracked set, and tests for each. This
    needs a flag and a stat. It also composes: if overrides are wanted later, this
    refusal is still the correct behaviour for an un-overridden hand edit.

    What it costs is that regenerating counts now takes a deliberate `--force` and
    a re-application of the rulings by hand. That is the honest price of the
    artifact being the authority, and it is paid loudly instead of quietly.
    """
    if force or not out.exists():
        return None
    try:
        existing = out.read_text(encoding="utf-8")
    except OSError:
        existing = ""
    found = sorted({m for m in REVIEW_MARKERS if m in existing})
    detail = (
        f"It contains review markers ({', '.join(found)}), so at least some of it "
        "is a human decision."
        if found
        else "No review markers were found, which is NOT evidence that nobody "
             "edited it — a reviewer accepting an entry leaves no word behind."
    )
    return (
        f"refusing to overwrite {out}: it already exists and this generator "
        f"cannot reproduce a review.\n  {detail}\n"
        "  Regenerating discards every hand-applied ruling in it — reseats, "
        "dropped surfaces, accepted entries.\n"
        "  Diff the two before choosing: write elsewhere with --out <newpath>, "
        "compare, then re-apply.\n"
        "  Pass --force to overwrite anyway."
    )


def _cmd_registry_tracked_set(args: argparse.Namespace) -> int:
    """Report the tracked set and the mention curve it was cut from (#33).

    Prints rather than writes. The count is a contract decision, so this shows
    where the curve flattens and leaves the number to a person.
    """
    import json

    from collect.db import connect
    from collect.registry.tracked import (
        TrackedSetPolicy,
        attributable,
        distribution,
        select,
        summarise,
    )

    observed = attributable(
        json.loads(Path(args.surfaces).read_text(encoding="utf-8"))
    )

    conn = connect()
    try:
        rows = conn.execute(
            "SELECT canonical_id, display_name, release_date FROM model_version "
            "ORDER BY canonical_id"
        ).fetchall()
    finally:
        conn.close()

    selection = select(
        rows,
        observed,
        policy=TrackedSetPolicy(
            mention_floor=args.mention_floor,
            launch_window_days=args.launch_window_days,
        ),
        as_of=date.today(),
        basis={
            "platform": args.platform,
            "documents": args.documents,
            "surfaces": args.surfaces,
        },
    )
    print(summarise(selection))
    print()
    print(distribution(selection))
    if args.verbose:
        print()
        print("  rank  mentions  surfaces  seated by            model")
        for i, m in enumerate(selection.tracked, 1):
            mentions = "unmeasured" if m.mentions is None else str(m.mentions)
            surfaces = "-" if m.surfaces is None else str(m.surfaces)
            print(
                f"  {i:>4}  {mentions:>10}  {surfaces:>8}  "
                f"{'+'.join(m.grounds):<20} {m.canonical_id}"
            )
    return 0


def _cmd_triage_population(args: argparse.Namespace) -> int:
    """Print the surface population the entity gate would resolve against.

    Prints the fingerprint, which is the point: a triage verdict is reproducible
    from (document, population), and this is where the second half of that pair
    gets a name somebody can write down.
    """
    from collect.db import connect
    from collect.triage.entity import build_population

    declared: list[str] = []
    if not args.no_declared:
        for model in load_seed_file().models:
            declared.append(model.aliases.surface)
            declared.extend(model.aliases.variants)

    conn = connect()
    try:
        models = conn.execute(
            "SELECT canonical_id, display_name FROM model_version ORDER BY canonical_id"
        ).fetchall()
    finally:
        conn.close()

    population = build_population(models, declared)
    print(population.basis)
    if args.verbose:
        for surface in sorted(population.surfaces):
            owners = population.owners.get(surface, ())
            print(f"  {surface:<40} {','.join(owners) or '(declared; owner not recorded)'}")
    return 0


def _cmd_registry_check_sources(args: argparse.Namespace) -> int:
    """FR-2, checkable without a database."""
    seed = load_seed_file()
    gaps = source_gaps(seed)
    total_fields = sourced_field_total(seed)
    sourced = total_fields - len(gaps)

    flat = sum(len(m.populated_sourced_fields()) for m in seed.models)
    tiered = total_fields - flat

    print(f"seed file : {len(seed.models)} models, version {seed.version}")
    print(f"FR-2      : {sourced}/{total_fields} populated fields carry a source")
    print(f"            ({flat} model_version fields + {tiered} price_tier fields)")
    if not gaps:
        print("            complete")
        return 0
    for canonical_id, fields in sorted(gaps_by_model(seed).items()):
        print(f"  unsourced {canonical_id}: {', '.join(fields)}")
    return 1


def _cmd_registry_aliases(args: argparse.Namespace) -> int:
    seed = load_seed_file()
    rows = all_alias_rows(seed.models)
    by_specificity: dict[str, int] = {}
    for row in rows:
        by_specificity[row.specificity] = by_specificity.get(row.specificity, 0) + 1
        if args.verbose:
            print(f"  {row.specificity:<8} {row.normalized:<28} {row.canonical_id}")
    print(f"aliases   : {len(rows)} across {len(seed.models)} models")
    for specificity, count in sorted(by_specificity.items()):
        print(f"            {specificity}: {count}")
    collisions = find_collisions(rows)
    if collisions:
        for key, owners in sorted(collisions.items()):
            print(f"  COLLISION {key!r} → {owners}")
        return 1
    print("            no collisions")
    return 0


def _cmd_registry_recompute_window(args: argparse.Namespace) -> int:
    """Nightly. The sole writer of `model_version.in_window`."""
    from collect.db import transaction
    from collect.registry.load import recompute_window

    with transaction() as conn:
        # The chain runs preflight as stage 1, so this was covered THERE and
        # not here. A stage that is safe inside the chain and unguarded when
        # somebody runs it by hand is guarded by the schedule rather than by
        # the code.
        _gate(conn)
        counts = recompute_window(conn)
    computed = counts["in_window"] - counts["assumed_in_window"]
    print(
        f"window   : {counts['changed']} changed, {counts['in_window']} in window "
        f"({computed} computed, {counts['assumed_in_window']} assumed from a missing "
        f"release date), {counts['out_of_window']} outside"
    )
    return 0


def _cmd_registry_load_seed(args: argparse.Namespace) -> int:
    from collect.registry.load import model_row

    seed = load_seed_file()

    if args.dry_run:
        rows = [model_row(m) for m in seed.models]
        aliases = all_alias_rows(seed.models)
        print(f"dry run   : {len(rows)} model rows, {len(aliases)} alias rows")
        for row in rows:
            print(f"  {row['id']}  {row['canonical_id']:<38} provenance={row['provenance']}")
        gaps = source_gaps(seed)
        if gaps:
            print(f"FR-2 gap  : {len(gaps)} populated field(s) with no source")
        return 0

    from collect.db import transaction
    from collect.registry.load import load_seed

    with transaction() as conn:
        # GATED, AND THIS IS THE COMMAND THAT MOST NEEDED IT. `load_seed`
        # inserts `model_version.provenance = 'seed'` rows — the exact fixture
        # `assert_no_fixtures` refuses. Ungated, the guard could only ever catch
        # rows some *other* path had already written, which is the state it is
        # supposed to prevent rather than report.
        #
        # Inside the transaction and before the write, so a refusal rolls back
        # and nothing lands. Same order as `db init`.
        _gate(conn)
        report = load_seed(
            conn,
            strict_sources=not args.allow_unsourced,
            strict_spelling=not args.allow_missing_spellings,
        )
    print(report.summary())
    return 0


def _cmd_registry_load_sources(args: argparse.Namespace) -> int:
    """Load `contract/sources.yaml` into `source`. The caller it never had.

    `load_source_rows` has been correct and tested since it was written and had
    NO CALLER — no command, no script, no chain stage. So `source` holds 0 rows,
    and `harvest_run.source_id` is a FOREIGN KEY to `source(id)`: no harvest run
    can be recorded for any platform, GitHub included, until this has run.

    `ops/ledger.py:open_harvest_run` already refuses with a sentence naming this
    loader rather than surfacing a `23503`, which is the right behaviour and is
    also why nothing forced the gap into the open — a legible refusal is easy to
    read as a considered state.

    NOT a fixture. `assert_no_fixtures` does not look at `source` and must not
    be taught to: a seeded feed is a curation decision, not a stand-in for
    machinery that does not exist yet. So unlike `load-seed` this writes rows
    that belong in production.
    """
    from collect.db import transaction
    from collect.registry.sources import load_source_rows, load_sources

    contract = load_sources()

    if args.dry_run:
        rows = contract.source_rows()
        print(f"dry run   : {len(rows)} source row(s) from contract/sources.yaml")
        for row in rows:
            ruling = row.get("terms_ruling") or "NO RULING"
            print(f"  {row['id']:<32} platform={row['platform']:<8} {ruling}")
        return 0

    with transaction() as conn:
        # Gated inside the transaction and before the write, same order as
        # `load-seed` and `db init`, so a refusal rolls back and nothing lands.
        _gate(conn)
        report = load_source_rows(conn, contract)
    print(report.summary())
    return 0


def _cmd_registry_load_capabilities(args: argparse.Namespace) -> int:
    """Load `contract/capabilities.yaml` into `capability`.

    The table that blocks `claim`: `capability_key` is NOT NULL and REFERENCES
    it, and it holds 0 rows, so no claim can be inserted for any model from any
    platform however good the extraction. Twelve keys, no loader, since the
    scaffold.
    """
    from collect.db import transaction
    from collect.registry.capabilities import load_capabilities, load_capability_file

    if args.dry_run:
        version, rows = load_capability_file()
        print(f"dry run   : {len(rows)} capability key(s) at version {version}")
        for row in rows:
            print(f"  {row.key:<38} {row.failure_mode}")
        return 0

    with transaction() as conn:
        _gate(conn)
        report = load_capabilities(conn)
    print(report.summary())
    return 0


def _cmd_ops_sweep_github(args: argparse.Namespace) -> int:
    """The GitHub sweep, planned from `model_alias` and recorded in `harvest_run`.

    The stage `chain.py` has carried as `run=None` since `ops/` was built. See
    `collect/ops/sweep.py` for the three gaps it closes and the one guard it
    deliberately does not import.
    """
    from collect.adapters.queries import load_queries
    from collect.adapters.queries.cadence import split_by_cadence
    from collect.db import transaction
    from collect.http import build_client
    from collect.ops.sweep import seated_variants, sweep_budget, sweep_github
    from collect.rawstore import RawStore
    from collect.registry.assertions import assert_terms_reviewed
    from collect.registry.sources import load_sources

    contract = load_sources()
    github = next(s for s in contract.platforms if s["id"] == "github")
    # NFR-5, before a single request: a known unexpired ruling, evidence that has
    # not gone stale, and this run's own observation of the access path.
    assert_terms_reviewed(
        [github],
        rulings=contract.rulings,
        observations={"github": {"access_path": "api"}},
        today=date.today(),
    )
    print("gate     : github terms reviewed and re-verified, harvest permitted")

    queries = load_queries()
    entries = list(queries.all_entries)
    cadence = split_by_cadence(entries)
    selected = cadence[args.cadence] if args.cadence != "all" else entries
    budget_cadence = args.cadence if args.cadence != "all" else "daily"
    contract_cap, contract_minutes = sweep_budget(budget_cadence)
    cap = args.cap if args.cap is not None else contract_cap
    scope = tuple(args.scope or ())

    if args.dry_run:
        from collect.adapters.queries import plan_searches
        from collect.db import connect

        conn = connect()
        try:
            by_model = seated_variants(conn)
        finally:
            conn.close()
        planned = {
            model: plan_searches(selected, list(v), scope=scope).request_count
            for model, v in by_model.items()
        }
        total = sum(planned.values())
        fits = [m for m in planned if sum(
            planned[x] for x in list(planned)[: list(planned).index(m) + 1]
        ) <= cap]
        print(f"plan     : {len(by_model)} seated model(s), {len(selected)} entr(ies), "
              f"{total} request(s) planned against a cap of {cap} request(s) / "
              f"{contract_minutes} minute(s)")
        # A PLAN IS NOT A CLEARANCE. `_gate` is not called here and the terms gate
        # above covers NFR-5 only, so this output says what a sweep would cost and
        # nothing about whether one may run. Saying so, because two days of
        # readiness readings came off this path.
        print("           (plan only — `_gate` not run, so this is not a clearance)")
        print(f"           {len(fits)} model(s) fit the cap, "
              f"{len(by_model) - len(fits)} would be unreached")
        return 0

    # AN UNAUTHENTICATED SWEEP IS NOT A SWEEP, AND IT DOES NOT LOOK LIKE A
    # FAILURE. This path called `build_client()` with no headers, so every
    # request went out anonymous, against GitHub's anonymous ceilings:
    #
    #                       anonymous      authenticated
    #     search            10 / minute    30 / minute
    #     core (REST)       60 / HOUR      5,000 / hour
    #
    # `SEARCH_INTERVAL` is computed from 30/minute, so the sweep was 2.7x over
    # the anonymous search limit from its first request, and it exhausted the
    # whole 60/hour core budget in about a minute of fetching — after which
    # EVERY fetch 403s. Measured: 407 runs, 18,801 candidates retrieved,
    # 59 passed the sieve, **0 documents stored**.
    #
    # And the shape is the reason for the refusal below rather than a warning:
    # a starved sweep reports zero documents, which is indistinguishable on a
    # page from "nobody has discussed this". Rule 4, arriving through the
    # credential rather than through the corpus.
    #
    # `scripts/harvest_github.py` has always passed the header. Only this path
    # did not, which is why the harness produced 2,887 items and the CLI
    # produced nothing.
    token = settings().github_token
    if not token:
        print(
            "GITHUB_TOKEN is not set, so this sweep would run anonymous: 10 "
            "search requests a minute against a limiter built for 30, and 60 "
            "REST calls an HOUR. It would retrieve candidates, pass some, and "
            "store nothing — which reads as 'nobody discussed this' rather "
            "than as a failure. Refusing instead.",
            file=sys.stderr,
        )
        return 2

    with build_client(
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    ) as client, transaction() as conn:
        _gate(conn)
        from collect.adapters.github import GitHubHarvester

        harvester = GitHubHarvester(
            client=client,
            store=RawStore(Path(args.store)),
            max_fetch_per_query=args.max_fetch_per_query,
        )
        report = sweep_github(
            conn, harvester, entries=selected, scope=scope, cap=cap,
            max_minutes=args.max_minutes, cadence=budget_cadence,
        )
    print(report.summary())
    return 0


def _cmd_assemble_github(args: argparse.Namespace) -> int:
    """Assemble stored GitHub issues into `thread_context` rows.

    The stage `chain.py` carries as `assemble-flatten` with `run=None`. 27
    documents have been sitting on staging with no context, and `judge/` reads
    `thread_context` — so an unassembled document is a document the extractor
    cannot see.
    """
    from collect.assemble.issue import assemble_github_documents
    from collect.db import transaction
    from collect.rawstore import RawStore

    with transaction() as conn:
        _gate(conn)
        report = assemble_github_documents(
            conn, store=RawStore(Path(args.store)), limit=args.limit
        )
    print(report.summary())
    return 0


def _cmd_assemble_reddit(args: argparse.Namespace) -> int:
    """Assemble stored Reddit comment trees into `thread_context` rows.

    190 of 196 Reddit documents have no context, and `judge/` reads
    `thread_context` — so an unassembled thread is nearly half the corpus the
    extractor cannot see, on the platform that carries the most distinct voices.
    No fetching and no model call: it reassembles what harvest already stored.
    """
    from collect.assemble.reddit import assemble_reddit_documents
    from collect.db import transaction
    from collect.rawstore import RawStore

    with transaction() as conn:
        _gate(conn)
        report = assemble_reddit_documents(
            conn, store=RawStore(Path(args.store)), limit=args.limit
        )
    print(report.summary())
    return 0


def _cmd_registry_attest_seats(args: argparse.Namespace) -> int:
    """Write the manifest that records a review. No database, no rows.

    **Nothing in the artifact records that a human read an entry.** `status`,
    `seated_by` and `incomplete` are all `to_yaml` output — the generator's
    measurements. So a bulk loader keyed on them would admit every future entry
    the generator labels attested, with no person in the path, and the review
    would become optional. This writes the missing fact down instead.

    Yes, this can be run without reviewing anything. The guarantee was never *"a
    human read it"* — it cannot be. It is *"a human took a deliberate act naming
    this exact content, and any later change to that content revokes it"*, which
    is strictly more than typing an id gives, because typing an id pins no
    content at all.
    """
    import re
    from datetime import UTC, datetime

    import yaml as _yaml

    from collect.registry.seat import DEFAULT_ARTIFACT
    from collect.registry.tracked_load import (
        DEFAULT_MANIFEST,
        entry_fingerprint,
        read_entry,
    )

    text = DEFAULT_ARTIFACT.read_text(encoding="utf-8")
    blocks = re.split(r"\n  - canonical_id: ", text)[1:]
    if not blocks:
        print(f"parsed 0 entries out of {DEFAULT_ARTIFACT.name}", file=sys.stderr)
        return 2

    seats: dict[str, str] = {}
    skipped: list[str] = []
    for block in blocks:
        canonical_id = block.split("\n")[0].strip()
        ground = re.search(r"seated_by:\s*(\S+)", block)
        if not ground or ground.group(1) != args.seated_by:
            skipped.append(canonical_id)
            continue
        entry = read_entry(canonical_id)
        if entry.blocking_incomplete:
            skipped.append(canonical_id)
            continue
        seats[canonical_id] = entry_fingerprint(entry)

    out = Path(args.out) if args.out else DEFAULT_MANIFEST
    payload = {
        "artifact": DEFAULT_ARTIFACT.name,
        "reviewed_at": datetime.now(UTC).date().isoformat(),
        "reviewed_by": args.reviewed_by,
        "population": len(seats),
        "finding": args.finding,
        "seats": seats,
    }
    out.write_text(_yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    print(f"attested : {len(seats)} seat(s) on ground {args.seated_by!r} -> {out}")
    print(f"skipped  : {len(skipped)} entr(ies) on other grounds or still incomplete")
    return 0


def _cmd_registry_load_tracked_set(args: argparse.Namespace) -> int:
    """Load the reviewed seats into `model_alias`. The bulk path, with its guards.

    `--dry-run` prints the plan and is what replaces the generator's `--force`:
    an append-only table has no undo, so the only reversal available is not
    writing the wrong thing. See `registry/tracked_load.py`.
    """
    from collect.db import connect, transaction
    from collect.registry.tracked_load import LoadRefused, load, plan, read_manifest

    manifest_path = Path(args.manifest) if args.manifest else None
    try:
        manifest = read_manifest(manifest_path)
    except LoadRefused as refusal:
        print(str(refusal), file=sys.stderr)
        return 2

    print(
        f"manifest : {manifest.population} seat(s), reviewed "
        f"{manifest.reviewed_at} by {manifest.reviewed_by}"
    )

    if args.dry_run:
        # No transaction and no gate: this reads the registry and prints. The
        # plan is the diagnostic somebody needs when the gate would refuse.
        conn = connect()
        try:
            prepared = plan(conn, manifest)
        finally:
            conn.close()
        print(prepared.summary())
        for entry in prepared.entries:
            counts = entry.counts
            print(f"  {entry.canonical_id:<40} {counts['insert']} insert, "
                  f"{counts['unchanged']} unchanged, {counts['replace']} supersede")
        for reason in prepared.refusals:
            print(f"  REFUSED  {reason}")
        return 1 if prepared.refusals else 0

    with transaction() as conn:
        # Gated inside the transaction and before the write, so a refusal rolls
        # back and nothing lands — same order as `load-seed` and `db init`.
        _gate(conn)
        try:
            report = load(conn, manifest, allow_supersede=args.allow_supersede)
        except LoadRefused as refusal:
            print(str(refusal), file=sys.stderr)
            return 2
    print(report.summary())
    return 0


def _cmd_registry_seat_alias(args: argparse.Namespace) -> int:
    """Seat one reviewed model's surfaces from the tracked-set artifact.

    The consumer that artifact never had. One model at a time, named by a
    person, because a bulk loader would defeat the `INCOMPLETE` markers the
    format exists for.
    """
    from collect.db import transaction
    from collect.registry.seat import SeatRefused, read_entry, seat

    if args.dry_run:
        try:
            entry = read_entry(args.canonical_id)
        except SeatRefused as refusal:
            print(str(refusal))
            return 1
        print(f"dry run   : {entry.canonical_id}")
        print(f"  surface : {entry.surface}")
        for v in entry.variants:
            print(f"  variant : {v}")
        print(f"  incomplete: {list(entry.incomplete) or 'none'}"
              f"   blocking: {list(entry.blocking_incomplete) or 'none'}")
        return 0

    with transaction() as conn:
        _gate(conn)
        try:
            report = seat(conn, args.canonical_id)
        except SeatRefused as refusal:
            print(str(refusal))
            return 1
    print(
        f"seated {report['canonical_id']}: {report['rows']} alias row(s), "
        f"{report['searchable']} search-eligible, primary {report['surface']!r}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="collect", description=__doc__)
    sub = parser.add_subparsers(dest="group", required=True)

    db = sub.add_parser("db", help="schema management")
    db_sub = db.add_subparsers(dest="command", required=True)
    db_init = db_sub.add_parser("init", help="apply contract/tables.sql")
    db_init.add_argument(
        "--reset",
        action="store_true",
        help="drop and recreate the public schema first (development only)",
    )
    db_init.set_defaults(func=_cmd_db_init)

    db_check = db_sub.add_parser(
        "check", help="report pending migrations without applying them")
    db_check.set_defaults(func=_cmd_db_check)

    db_migrate = db_sub.add_parser(
        "migrate", help="apply pending migrations from contract/migrations/")
    db_migrate.set_defaults(func=_cmd_db_migrate)

    registry = sub.add_parser("registry", help="the model registry")
    reg_sub = registry.add_subparsers(dest="command", required=True)

    check = reg_sub.add_parser("check-sources", help="FR-2 source coverage")
    check.set_defaults(func=_cmd_registry_check_sources)

    propose_aliases = reg_sub.add_parser(
        "propose-aliases",
        help="propose alias surfaces from the registry and observed documents")
    propose_aliases.add_argument(
        "--surfaces", help="surface-extract JSON; omitted means recall unmeasured")
    propose_aliases.add_argument("--out", help="write the reviewable skeleton here")
    propose_aliases.add_argument(
        "--force", action="store_true",
        help="overwrite an existing --out. Refused by default: the artifact is the "
             "authority and this generator cannot reproduce a review")
    propose_aliases.add_argument(
        "--mention-floor", type=int,
        help="narrow to the tracked set: attested mentions to qualify by count. "
        "Requires --launch-window-days and --surfaces.")
    propose_aliases.add_argument(
        "--launch-window-days", type=int,
        help="days since release inside which a model qualifies regardless of "
        "mentions. Requires --mention-floor.")
    propose_aliases.set_defaults(func=_cmd_registry_propose_aliases)

    assemble = sub.add_parser("assemble", help="E3 — turn documents into thread_context")
    assemble_sub = assemble.add_subparsers(dest="assemble_command", required=True)
    asm_gh = assemble_sub.add_parser(
        "github", help="assemble stored GitHub issues into thread_context rows")
    asm_gh.add_argument("--store", default="./raw_store")
    asm_gh.add_argument("--limit", type=int, default=None)
    asm_gh.set_defaults(func=_cmd_assemble_github)

    asm_reddit = assemble_sub.add_parser(
        "reddit", help="assemble stored Reddit comment trees into thread_context rows")
    asm_reddit.add_argument("--store", default="./raw_store")
    asm_reddit.add_argument("--limit", type=int, default=None)
    asm_reddit.set_defaults(func=_cmd_assemble_reddit)

    ops = sub.add_parser("ops", help="the nightly chain and its checks")
    ops_sub = ops.add_subparsers(dest="ops_command", required=True)
    ops_pre = ops_sub.add_parser(
        "preflight", help="the startup checks, without running the chain")
    ops_pre.set_defaults(func=_cmd_ops_preflight)
    ops_sweep = ops_sub.add_parser(
        "sweep-github",
        help="sweep GitHub for every seated model, recording each query in harvest_run",
    )
    ops_sweep.add_argument(
        "--cadence", default="daily", choices=("daily", "weekly", "all"),
        help="which query entries to issue (default daily)")
    ops_sweep.add_argument(
        "--cap", type=int, default=None,
        help="request budget; defaults to contract/harvest.yaml max_requests")
    ops_sweep.add_argument("--scope", action="append", help="repeatable repo: qualifier")
    ops_sweep.add_argument("--store", default="./_sweep_store")
    ops_sweep.add_argument("--max-fetch-per-query", type=int, default=15)
    ops_sweep.add_argument(
        "--max-minutes", type=int, default=None,
        help="wall-clock ceiling; defaults to contract/harvest.yaml max_minutes "
             "for this cadence. Checked as well as the request count, because a "
             "throttle moves one and not the other")
    ops_sweep.add_argument(
        "--dry-run", action="store_true",
        help="print the plan and the models the cap would not reach")
    ops_sweep.set_defaults(func=_cmd_ops_sweep_github)

    ops_run = ops_sub.add_parser("run", help="run the nightly chain")
    ops_run.add_argument("--journal", help="append-only JSONL record of every stage")
    ops_run.add_argument(
        "--no-database", action="store_true",
        help="run without a connection; every stage that needs one refuses and says so")
    ops_run.add_argument(
        "--no-network", action="store_true",
        help="run without an HTTP client; poll-registry refuses and says so. "
             "The OpenRouter feed needs no credential, so the default is on.")
    ops_run.add_argument(
        "--force", action="store_true",
        help="proceed even though a previous run never finished. Without this, "
             "an unfinished job_run row refuses the chain and names it.")
    ops_run.set_defaults(func=_cmd_ops_run)

    tracked = reg_sub.add_parser(
        "tracked-set",
        help="which models get swept, and the mention curve it was cut from (#33)")
    tracked.add_argument("--surfaces", required=True, help="surface-extract JSON")
    tracked.add_argument(
        "--mention-floor", type=int, required=True,
        help="attested mentions at or above which a model qualifies by count")
    tracked.add_argument(
        "--launch-window-days", type=int, required=True,
        help="days since release inside which a model qualifies regardless")
    # Rule 7: the extract's denominator is not derivable from the extract, so
    # the caller states it and it is printed beside every figure.
    tracked.add_argument(
        "--documents", type=int, help="documents the extract was drawn from")
    tracked.add_argument("--platform", help="platform the extract was drawn from")
    tracked.add_argument("-v", "--verbose", action="store_true", help="list the set")
    tracked.set_defaults(func=_cmd_registry_tracked_set)

    aliases = reg_sub.add_parser("aliases", help="alias rows and collisions")
    aliases.add_argument("-v", "--verbose", action="store_true")
    aliases.set_defaults(func=_cmd_registry_aliases)

    recompute = reg_sub.add_parser(
        "recompute-window",
        help="refresh model_version.in_window (nightly; sole writer of that column)",
    )
    recompute.set_defaults(func=_cmd_registry_recompute_window)

    load = reg_sub.add_parser("load-seed", help="load contract/seed_models.yaml")
    load.add_argument("--dry-run", action="store_true", help="build rows, touch nothing")
    load.add_argument(
        "--allow-unsourced",
        action="store_true",
        help="load fields that cite no source. Records the gap in the report.",
    )
    load.add_argument(
        "--allow-missing-spellings",
        action="store_true",
        help="load models missing a spaced, hyphenated or concatenated form. "
        "Records the gap in the report.",
    )
    load.set_defaults(func=_cmd_registry_load_seed)

    load_src = reg_sub.add_parser(
        "load-sources",
        help="load contract/sources.yaml into `source`. harvest_run FKs to it.",
    )
    load_src.add_argument(
        "--dry-run", action="store_true", help="build rows, touch nothing"
    )
    load_src.set_defaults(func=_cmd_registry_load_sources)

    load_caps = reg_sub.add_parser(
        "load-capabilities",
        help="load contract/capabilities.yaml into `capability`. claim FKs to it.",
    )
    load_caps.add_argument(
        "--dry-run", action="store_true", help="parse and report, touch nothing"
    )
    load_caps.set_defaults(func=_cmd_registry_load_capabilities)

    seat_alias = reg_sub.add_parser(
        "seat-alias",
        help="seat one reviewed model's surfaces from the tracked-set artifact",
    )
    seat_alias.add_argument("canonical_id", help="e.g. anthropic/claude-opus-4.8")
    seat_alias.add_argument(
        "--dry-run", action="store_true", help="show the reviewed entry, write nothing"
    )
    seat_alias.set_defaults(func=_cmd_registry_seat_alias)

    attest = reg_sub.add_parser(
        "attest-seats",
        help="write a reviewed-seats manifest for the entries you have reviewed",
    )
    attest.add_argument(
        "--seated-by", default="attested",
        help="which grounds to attest (default attested; launch-window entries are "
             "Engineer 2's to rule on)",
    )
    attest.add_argument("--reviewed-by", required=True, help="who reviewed them")
    attest.add_argument("--finding", default="", help="what the review concluded")
    attest.add_argument("--out", default=None, help="default docs/proposals/reviewed-seats.yaml")
    attest.set_defaults(func=_cmd_registry_attest_seats)

    load_tracked = reg_sub.add_parser(
        "load-tracked-set",
        help="load the reviewed seats from a manifest into model_alias",
    )
    load_tracked.add_argument(
        "--manifest", default=None, help="default docs/proposals/reviewed-seats.yaml"
    )
    load_tracked.add_argument(
        "--dry-run", action="store_true", help="print the plan and write nothing"
    )
    load_tracked.add_argument(
        "--allow-supersede", action="store_true",
        help="permit closing a live alias row's validity window",
    )
    load_tracked.set_defaults(func=_cmd_registry_load_tracked_set)

    triage = sub.add_parser("triage", help="E4 — the hard gates")
    triage_sub = triage.add_subparsers(dest="command", required=True)

    pop = triage_sub.add_parser(
        "population",
        help="the alias surfaces the entity gate resolves against, and their "
        "fingerprint",
    )
    pop.add_argument(
        "--no-declared",
        action="store_true",
        help="derivations only, without contract/seed_models.yaml. Narrower by "
        "27 surfaces no derivation reaches, e.g. `deepseek r1`.",
    )
    pop.add_argument("-v", "--verbose", action="store_true", help="list every surface")
    pop.set_defaults(func=_cmd_triage_population)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch, with a preflight refusal reported rather than raised.

    `_gate` raises `PreflightRefused` on a write command in an unfit
    environment. That is an expected outcome — the whole point of the check —
    and a stack trace reads as a bug in the tool rather than as a refusal by
    it. Caught here rather than in each command so a newly gated command cannot
    forget to.
    """
    from collect.ops.preflight import PreflightRefused

    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except PreflightRefused as refusal:
        print(str(refusal), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
