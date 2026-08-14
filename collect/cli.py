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

    registry = sub.add_parser("registry", help="the model registry")
    reg_sub = registry.add_subparsers(dest="command", required=True)

    check = reg_sub.add_parser("check-sources", help="FR-2 source coverage")
    check.set_defaults(func=_cmd_registry_check_sources)

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
