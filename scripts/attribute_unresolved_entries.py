#!/usr/bin/env python
"""File held board entries onto the board once their model is in the registry.

    python scripts/attribute_unresolved_entries.py --dry-run
    python scripts/attribute_unresolved_entries.py --apply

#602. Extraction holds the entries of a verified claim whose model name
resolved to no registry row in `unresolved_entry` (judge/pipeline.py). Run this
after seating a model - `scripts/load_unpolled_models.py`, or a registry poll
that brought it - and every held row whose name NOW resolves is written to
`board_entry` through `store_entries`, the same path extraction uses.

THE SAME RESOLVER, SO THE SAME REFUSALS. Names are resolved by
`RegistrySurfaceResolver`, exactly as extraction resolved them, so a family
name, an ambiguous codename or a range stays held. No model is called: the
quote was verified at extraction, and that is the quote that is filed.

It writes to whatever DATABASE_URL names, through the same write guard as the
other loaders. A shared-database write is announced before it runs.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
    if m:
        os.environ.setdefault(m.group(1), m.group(2))

import psycopg  # noqa: E402

from collect.surface_resolver import RegistrySurfaceResolver  # noqa: E402
from judge.store.unresolved_entries import attribute_held, held_by_name  # noqa: E402


def seating_bar() -> tuple[int, int]:
    """(held_entries, distinct_authors) from contract/tracked_models.yaml, strictly."""
    import yaml

    raw = yaml.safe_load((ROOT / "contract" / "tracked_models.yaml").read_text(encoding="utf-8"))
    bar = raw.get("seating_bar") or {}
    entries, authors = bar.get("held_entries"), bar.get("distinct_authors")
    if not isinstance(entries, int) or not isinstance(authors, int):
        raise SystemExit("contract/tracked_models.yaml needs `seating_bar:` with integer "
                         "`held_entries` and `distinct_authors`")
    return entries, authors


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    from judge.writeguard import check as writeguard_check
    writeguard_check(os.environ.get("DATABASE_URL"), command="attribute_unresolved_entries.py")

    conn = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=15)
    resolver = RegistrySurfaceResolver.from_connection(conn)
    out = attribute_held(conn, resolver, dry_run=args.dry_run)
    print(f"held {out['held']}, now resolvable {out['resolvable']}, filed {out['filed']}")
    for model, n in sorted(out["by_model"].items(), key=lambda kv: -kv[1]):
        print(f"  {model}: {n}")
    for why, n in sorted(out.get("not_filed", {}).items(), key=lambda kv: -kv[1]):
        print(f"  resolved but not filed - {why}: {n}")
    if out["still_held"]:
        top = sorted(out["still_held"].items(), key=lambda kv: -kv[1])[:15]
        print("  still held (no registry model yet): "
              + ", ".join(f"{s!r} x{n}" for s, n in top))
        # THE SEATING BAR (contract/tracked_models.yaml): which unseated names
        # have reached it, so seating is a stated threshold and not a feeling.
        need_entries, need_authors = seating_bar()
        counts = held_by_name(conn)
        met = sorted((s for s in out["still_held"]
                      if counts.get(s, (0, 0))[0] >= need_entries
                      and counts.get(s, (0, 0))[1] >= need_authors),
                     key=lambda s: -counts[s][0])
        print(f"  seating bar ({need_entries} held entries, {need_authors} distinct authors): "
              + (", ".join(f"{s!r} ({counts[s][0]} entries, {counts[s][1]} authors)"
                           for s in met) if met else "no held name meets it yet")
              + " - a LOWER BOUND: unseated models are not searched for")
    if args.dry_run:
        conn.rollback()
        conn.close()
        print("\n--dry-run: rolled back, nothing written.")
        return 0
    conn.commit()
    conn.close()
    print("\nCOMMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
