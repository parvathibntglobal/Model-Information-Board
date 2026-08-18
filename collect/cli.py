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

    with transaction() as conn:
        if args.reset:
            reset_schema(conn, environment=settings().environment)
            print("schema reset and applied from contract/tables.sql")
        else:
            apply_schema(conn)
            print("schema applied from contract/tables.sql")
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
        selection = select(
            rows,
            observed,
            policy=TrackedSetPolicy(
                mention_floor=args.mention_floor,
                launch_window_days=args.launch_window_days,
            ),
            as_of=date.today(),
            basis={"surfaces": args.surfaces},
        )
        print(summarise_selection(selection))
        print()
        models = [(m.canonical_id, m.display_name) for m in selection.tracked]
        # Grounds travel into the artifact: a model seated only by the launch
        # window has no attested surface, and its INCOMPLETE slots are the whole
        # of what a reviewer can act on.
        grounds = {
            m.canonical_id: ("attested" if BY_MENTIONS in m.grounds else "launch-window")
            for m in selection.tracked
        }
    else:
        models = [(r[0], r[1]) for r in rows]
        grounds = {}

    proposals = propose(models, observed)
    print(summarise(proposals))
    if args.out:
        Path(args.out).write_text(to_yaml(proposals, seated_by=grounds), encoding="utf-8")
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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
