#!/usr/bin/env python
"""Seat search aliases for the new models `auto_track` admits to the page.

`judge/tracked.py` puts a new arrival from a provider already on the page onto
the models page and into the scheduler's due list. A model with no live alias
row harvests nothing, so this gives each one the aliases a fetch searches for -
the step a person did by hand with `registry seat-alias` until 2026-10-06.

WHAT IT SEATS, AND WHAT IT REFUSES
----------------------------------
Surfaces come from `collect/registry/propose.py` `mechanical_variants` and
`rule_variants` - the same deterministic generators a reviewed entry starts
from. Then three refusals, each named in the report rather than skipped quietly:

    no version number   a surface without a digit is a word, not a name
                        (rule 10: `sol`, `luna`, `astra`); such surfaces are
                        dropped, and a model left with none is not seated
    collision           `check_against_table` - any surface another model holds
                        over an overlapping window refuses the WHOLE model
    already seated      a model with any live alias row is left alone; aliases
                        a person reviewed are never overwritten by generated ones

Rows go through `collect.registry.load._sync_alias`, the writer `seat()` uses,
so a re-run is a no-op.

STAGING WRITE. Run by the registry-poll Action after each poll, which posts the
report to #450 - that comment is the announcement. `--apply` takes the
writeguard; without it this only reports.

    python scripts/auto_seat.py                 # report, write nothing
    python scripts/auto_seat.py --apply --out auto_seat.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_HAS_VERSION = re.compile(r"\d")


def surfaces_for(canonical_id: str, display_name: str | None) -> list[str]:
    """Generated surfaces that carry a version number, in generator order."""
    from collect.registry.propose import mechanical_variants, rule_variants

    out: list[str] = []
    for s in [*mechanical_variants(canonical_id, display_name),
              *rule_variants(canonical_id, display_name)]:
        if _HAS_VERSION.search(s) and s not in out:
            out.append(s)
    return out


def plan(conn) -> list[dict]:
    """One record per admitted model: what would be seated, or why not."""
    from collect.registry.aliases import AliasCollisionError
    from collect.registry.seat import (
        ReviewedEntry,
        SeatRefused,
        check_against_table,
        rows_for,
    )
    from judge.tracked import auto_tracked

    records = []
    for model in auto_tracked(conn):
        cid = model.registry
        rec = {"canonical_id": cid, "name": model.name}
        live = conn.execute(
            "SELECT count(*) FROM model_alias a JOIN model_version v "
            "ON v.id = a.model_version_id WHERE v.canonical_id = %s "
            "AND a.valid_until IS NULL", (cid,)).fetchone()[0]
        if live:
            rec["outcome"] = f"already seated ({live} live alias row(s)); left alone"
            records.append(rec)
            continue
        display = conn.execute(
            "SELECT display_name FROM model_version WHERE canonical_id = %s", (cid,)
        ).fetchone()[0]
        surfaces = surfaces_for(cid, display)
        if not surfaces:
            rec["outcome"] = "NOT SEATED: no generated surface carries a version number"
            records.append(rec)
            continue
        entry = ReviewedEntry(canonical_id=cid, surface=surfaces[0],
                              variants=tuple(surfaces), incomplete=())
        try:
            rows = rows_for(conn, entry)
            check_against_table(conn, rows)
        except (AliasCollisionError, SeatRefused) as why:
            rec["outcome"] = f"NOT SEATED: {str(why).splitlines()[0][:200]}"
            records.append(rec)
            continue
        rec.update(outcome="to seat", surface=surfaces[0], surfaces=surfaces, _rows=rows)
        records.append(rec)
    return records


def report(records: list[dict], *, applied: bool) -> str:
    seated = [r for r in records if r["outcome"] in ("to seat", "seated")]
    lines = [f"**Auto-seat after this poll** ({'applied' if applied else 'dry run'}). "
             f"{len(records)} model(s) admitted by `auto_track`; "
             f"{len(seated)} {'seated' if applied else 'would be seated'}.", ""]
    for r in records:
        if r["outcome"] in ("to seat", "seated"):
            lines.append(f"- `{r['canonical_id']}`: {'seated' if applied else 'would seat'} "
                         + ", ".join(f"`{s}`" for s in r["surfaces"]))
        else:
            lines.append(f"- `{r['canonical_id']}`: {r['outcome']}")
    if not records:
        lines.append("- nothing new: no arrival matched the rule.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write the alias rows")
    ap.add_argument("--out", default=None, help="also write the markdown report here")
    args = ap.parse_args(argv)

    from collect.config import settings
    from collect.db import connect

    if args.apply:
        from judge.writeguard import check as writeguard_check

        writeguard_check(settings().database_url, command="auto_seat.py")

    with connect() as conn:
        records = plan(conn)
        if args.apply:
            from collect.registry.load import _sync_alias

            for r in records:
                if r["outcome"] != "to seat":
                    continue
                with conn.transaction():
                    for row in r["_rows"]:
                        _sync_alias(conn, row)
                r["outcome"] = "seated"
            conn.commit()

    text = report(records, applied=args.apply)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
