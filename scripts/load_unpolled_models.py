#!/usr/bin/env python
"""Load `contract/unpolled_models.yaml` through the seed loader.

WHY A SCRIPT AND NOT `registry load-seed`

`load-seed` reads one hardcoded file and has no `--path`. Pointing it at a
second contract would be a CLI change to the collect lane; this is a one-file
caller of the same library function, which `load_seed(path=...)` already
supports.

It is the SAME code path in every respect that matters: the same pydantic
validation, the same FR-2 source check, the same spelling check, the same
collision check, the same upsert, the same FR-4 alias append. Only the file
differs.

WHY THE FILE DIFFERS AT ALL

`registry load-seed` refuses against this database and is right to:

    Refusing to load: 7 row(s) already carry provenance='polled' and this load
    would downgrade them to 'seed'. Seeded models are a build fixture that
    polling replaces; reversing that would make assert_no_fixtures refuse to
    start.

Seven of `seed_models.yaml`'s eleven have since been polled. That refusal is the
mechanism working, and it is also the reason these three cannot live in that
file: adding them would make the whole file unloadable for a reason that has
nothing to do with them, and would label them a fixture awaiting replacement
when nothing will ever replace them.

WHAT PROVENANCE IT WRITES, AND WHY THAT CHANGED

`unpolled`, since #382. It wrote `seed` until then, and that was the defect:
`provenance` had no value for "a real model no poll carries", so the third
state got labelled with the word that means fixture. `assert_no_fixtures` then
refused four real models - carrying 65 claims and 11 cells - correctly by its
own definition and wrongly by intent.

The migration `20260923T0500_model_version_unpolled_provenance.sql` converts
the four rows already written. This is the writer, so nothing new arrives
mislabelled.

WHAT IT DOES NOT TOUCH

Only the three rows named in the file. `_refuse_provenance_downgrade` still runs
and still refuses if any of them is ever polled later - which is the correct
outcome, because at that point the poll owns the row and this file should stop
asserting it.

    python scripts/load_unpolled_models.py --dry-run
    python scripts/load_unpolled_models.py --apply
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

from collect.registry.load import load_seed  # noqa: E402

CONTRACT = ROOT / "contract" / "unpolled_models.yaml"


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    # ONE LOADER, TWO CONTRACTS. `contract/awaiting_poll_models.yaml` has the
    # same shape and a different CLAIM - models the poll WILL bring and has not
    # yet, against ones it never will. Keeping them in separate files is what
    # stops the first kind, once polled, making the second kind's file
    # unloadable under `_refuse_provenance_downgrade`; keeping them on one
    # loader is what stops the two drifting into two slightly different loads.
    ap.add_argument(
        "--path", default=None,
        help="contract to load (default: contract/unpolled_models.yaml)",
    )
    args = ap.parse_args()
    contract = pathlib.Path(args.path).resolve() if args.path else CONTRACT

    conn = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=15)
    before = conn.execute("SELECT count(*) FROM model_version").fetchone()[0]
    aliases_before = conn.execute("SELECT count(*) FROM model_alias").fetchone()[0]

    # `unpolled`, NOT `seed`. Both files here hold REAL models - a person typed
    # the row because no poll carries it, not because the build needed a stand-in.
    # Until #382 this loader wrote `seed`, which made `assert_no_fixtures` refuse
    # four real models correctly by its own definition and wrongly by intent.
    report = load_seed(conn, path=contract, provenance="unpolled")
    print(report.summary())

    after = conn.execute("SELECT count(*) FROM model_version").fetchone()[0]
    aliases_after = conn.execute("SELECT count(*) FROM model_alias").fetchone()[0]
    print(f"\n  model_version {before} -> {after}")
    print(f"  model_alias   {aliases_before} -> {aliases_after}")

    # READ BACK INSIDE THE TRANSACTION, before deciding to keep it. The loader
    # reports what it intended; this is what the database actually holds.
    import yaml

    wanted = [m["canonical_id"] for m in yaml.safe_load(
        contract.read_text(encoding="utf-8"))["models"]]
    rows = conn.execute(
        "SELECT canonical_id, provenance, display_name, price_in "
        "FROM model_version WHERE canonical_id = ANY(%s) ORDER BY canonical_id",
        (wanted,),
    ).fetchall()
    print()
    for cid, prov, name, price in rows:
        print(f"  {cid:<30} provenance={prov:<7} {name!r:<24} price_in={price!r}")

    failures = []
    if len(rows) != len(wanted):
        failures.append(f"{len(wanted) - len(rows)} of the models did not land")
    for cid, prov, _n, price in rows:
        if price is not None:
            failures.append(f"{cid} has a price, and nothing measured one")
        if prov != "unpolled":
            failures.append(f"{cid} landed as {prov!r}, expected 'unpolled'")
    # The rest of the registry must be untouched: this file names three models
    # and the loader has no business moving anything else.
    if after - before not in (0, len(wanted)):
        failures.append(f"model_version moved by {after - before}, expected 0 or {len(wanted)}")

    if args.dry_run:
        conn.rollback()
        print("\n--dry-run: rolled back, nothing written.")
        conn.close()
        return 0
    if failures:
        conn.rollback()
        print(f"\nROLLED BACK. {len(failures)} check(s) failed:")
        for f in failures:
            print("   ", f)
        conn.close()
        return 1

    conn.commit()
    conn.close()
    print("\nCOMMITTED. Every check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
