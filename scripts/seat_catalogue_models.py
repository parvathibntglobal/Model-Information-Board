#!/usr/bin/env python
"""Seat a `catalogued` registry row for each in-scope catalogue model that has none (#616).

    python scripts/seat_catalogue_models.py --dry-run [--out report.md]
    python scripts/seat_catalogue_models.py --apply   [--out report.md] [--list-aside]

A dry run always lists what is set aside for a person; an apply lists it only with
`--list-aside`, because the registry-poll workflow posts the apply report twice a day and
the same set-aside names on every post would bury the rows that are new. The counts by
reason are in every report.

A REGISTRY ROW, NEVER A TRACKED MODEL: claims about the model found in threads we already read
are filed instead of held, and no daily fetch starts. What is seated, what is set aside and
why: collect/ops/catalogue_seat.py.

THE WRITE GATE GUARDS WRITES ONLY: `--dry-run` reads and rolls back; `--apply` passes
judge/writeguard first. A shared-database `--apply` is announced before it runs.

AFTER AN APPLY, two steps the writer does not take itself (the #602 order):
  - `scripts/attribute_unresolved_entries.py --apply` files the claims held for these names;
  - `scripts/retriage_seated_models.py --dry-run` (#613) re-reads documents dropped as naming
    no model before these rows existed. It spends extraction, so it runs on its owner's word.
The "Held, not seated" admin panel shrinks once held claims file. That is expected: the claims
moved to their rows; nothing was lost.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NOTHING_WRITTEN = "nothing written: no new catalogue model to seat"
sys.path.insert(0, str(ROOT))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    ap.add_argument("--out", type=pathlib.Path, default=None,
                    help="also write the report as markdown (for a workflow to post)")
    ap.add_argument("--list-aside", action="store_true",
                    help="on --apply, also list what is set aside for a person")
    args = ap.parse_args(argv)

    from collect.config import settings

    dsn = settings().database_url
    if not dsn:
        raise SystemExit("DATABASE_URL is not set; nothing to read or write")
    if args.apply:
        from judge.writeguard import check as writeguard_check
        writeguard_check(dsn, command="seat_catalogue_models.py --apply")

    import psycopg

    from collect.ops import catalogue_seat

    with psycopg.connect(dsn, connect_timeout=20) as conn:
        plan = catalogue_seat.plan(conn)
        lines = [f"Catalogue seating ({'apply' if args.apply else 'dry run'}): {plan.summary()}"]
        if args.apply:
            out = catalogue_seat.apply(conn, plan)
            conn.commit()
            if out["inserted"] == 0:
                # The workflow keys on this line to post nothing.
                lines.append(f"{NOTHING_WRITTEN}; skipped because a row already existed: "
                             f"{out['skipped_existing']}")
            else:
                lines.append(f"written: {out['inserted']} row(s) {out['by_kind']}, aliases "
                             f"{out['aliases']}; skipped because a row already existed: "
                             f"{out['skipped_existing']}")
        else:
            conn.rollback()
            lines.append("dry run: nothing written.")
        aside = sorted(plan.set_aside.items())
        mechanical = ("listing variant", "router", "latest pointer", "out of scope")
        human = [(cid, why) for cid, why in aside if not why.startswith(mechanical)]
        if human and (args.dry_run or args.list_aside):
            lines.append(f"set aside for a person ({len(human)}):")
            lines += [f"  - {cid}: {why}" for cid, why in human]
    text = "\n".join(lines)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
