"""collect/ command line.

    py -3 -m collect.cli db init
    py -3 -m collect.cli registry check-sources
    py -3 -m collect.cli registry aliases
    py -3 -m collect.cli registry load-seed --dry-run
    py -3 -m collect.cli registry load-seed --allow-unsourced

Cron calls these. There is no scheduler here and there will not be one — a
jobs table and cron is enough for eight scheduled jobs.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
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
    """
    import json

    from collect.db import connect
    from collect.registry.propose import Attested, propose, summarise, to_yaml

    observed: dict[str, list[Attested]] = {}
    if args.surfaces:
        for row in json.loads(Path(args.surfaces).read_text(encoding="utf-8")):
            if row.get("verdict") in ("resolved", "attested-gap") and len(row["models"]) == 1:
                observed.setdefault(row["models"][0], []).append(
                    Attested(row["surface"], row["mentions"], row.get("documents", 0))
                )

    conn = connect()
    try:
        models = conn.execute(
            "SELECT canonical_id, display_name FROM model_version ORDER BY canonical_id"
        ).fetchall()
    finally:
        conn.close()

    proposals = propose(models, observed)
    print(summarise(proposals))
    if args.out:
        Path(args.out).write_text(to_yaml(proposals), encoding="utf-8")
        print(f"wrote {args.out} — review required, not loadable as-is")
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
    propose_aliases.set_defaults(func=_cmd_registry_propose_aliases)

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
