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
    from collect.ops.chain import Journal, default_stages, run_chain
    from collect.registry.policy import load_registry_policy

    conn = None
    if not args.no_database:
        try:
            conn = connect()
        except Exception as error:  # noqa: BLE001
            print(f"no database connection: {type(error).__name__}: {error}")

    journal = Journal(Path(args.journal) if args.journal else None)
    context = {
        "conn": conn,
        "environment": settings().environment,
        "policy": load_registry_policy(),
    }
    try:
        run = run_chain(default_stages(), context, journal)
    finally:
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
        Path(args.out).write_text(
            to_yaml(proposals, seated_by=grounds, policy=set_policy), encoding="utf-8"
        )
        print(f"wrote {args.out} — review required, not loadable as-is")
    return 0


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
        "--mention-floor", type=int,
        help="narrow to the tracked set: attested mentions to qualify by count. "
        "Requires --launch-window-days and --surfaces.")
    propose_aliases.add_argument(
        "--launch-window-days", type=int,
        help="days since release inside which a model qualifies regardless of "
        "mentions. Requires --mention-floor.")
    propose_aliases.set_defaults(func=_cmd_registry_propose_aliases)

    ops = sub.add_parser("ops", help="the nightly chain and its checks")
    ops_sub = ops.add_subparsers(dest="ops_command", required=True)
    ops_pre = ops_sub.add_parser(
        "preflight", help="the startup checks, without running the chain")
    ops_pre.set_defaults(func=_cmd_ops_preflight)
    ops_run = ops_sub.add_parser("run", help="run the nightly chain")
    ops_run.add_argument("--journal", help="append-only JSONL record of every stage")
    ops_run.add_argument(
        "--no-database", action="store_true",
        help="run without a connection; every stage that needs one refuses and says so")
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
