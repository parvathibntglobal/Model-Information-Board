"""The three re-weights, chained, inside ONE transaction that is rolled back.

WHY CHAINED RATHER THAN THREE COMMANDS. Each step re-prices the fork the
previous one wrote, so `judge reweight --from-version e5.2` needs e5.2 rows to
exist. A dry run rolls its writes back, which means three separate dry runs
cannot be chained: the second would read a version that no longer exists and
report zero claims as though the fork were empty.

WHY NOT JUST APPLY THEM. `judge/writeguard.py` refuses
`ENVIRONMENT=development` pointed at a remote database, which is this
configuration and is the guard working. Applying is a coordinated staging write
session under `CLAUDE.md`'s conventions - announced, not incidental to a
measurement. Every figure a decision needs is available without committing
anything, so this takes the figures and leaves the decision.

WHAT IT COMMITS: nothing. One transaction, rolled back at the end, whatever
happens. The pattern is `judge reweight`'s own dry run extended across three
steps - cells can only be priced from claims that are IN the table, so the rows
have to exist for the duration and must not survive it.

    python scripts/reweight_chain_dry_run.py [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import pathlib

from judge.curate.gate import N_EFF_MINIMUM, PLATFORM_MINIMUM
from judge.reweight import (
    CURRENT,
    FROZEN,
    LEGACY,
    READ,
    cell_deltas,
    plan,
    quieter_cells,
    summarise,
)
from judge.reweight import (
    apply as apply_reweight,
)

#: The three steps, in the order a person runs them. Each names the ONE ruling
#: it measures, because a step whose cause is not attached to it produces
#: numbers nobody can attribute.
STEPS = (
    ("e5.1", "e5.2", FROZEN, LEGACY, "the tier ruling alone"),
    ("e5.2", "e5.3", READ, LEGACY, "document facts reaching the path"),
    ("e5.3", "e5.4", READ, CURRENT, "Option 1, the double count removed"),
)


class _RolledBack(Exception):
    """Ends the chain without committing. Never escapes `main`."""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="docs/measurements/reweight-chain-dry-run.json")
    args = ap.parse_args()

    from collect.db import connect

    conn = connect()
    record: list[dict] = []
    try:
        try:
            with conn.transaction():
                names = dict(
                    conn.execute("SELECT id, canonical_id FROM model_version").fetchall()
                )
                for frm, to, facts, spec, what in STEPS:
                    print("=" * 78)
                    print(f"{frm} -> {to}   {what}")
                    print("=" * 78)
                    report = plan(
                        conn,
                        from_version=frm,
                        to_version=to,
                        document_facts=facts,
                        specificity=spec,
                    )
                    print(summarise(report))
                    written = apply_reweight(conn, report)

                    pairs = cell_deltas(conn, report)
                    losses = quieter_cells(pairs)
                    _print_cells(pairs, losses, names)

                    record.append(
                        {
                            "from": frm,
                            "to": to,
                            "measures": what,
                            "read": report.read,
                            "written": written,
                            "drift": dict(report.factor_drift),
                            "refusals": dict(report.refusals),
                            "unconfirmed": dict(report.unconfirmed),
                            "tier_moves": dict(report.tier_moves()),
                            "f_specificity_moves": len(report.specificity_moves()),
                            "provider_domain_promotions": [
                                d.model_version_id
                                for d in report.provider_domain_promotions()
                            ],
                            "cells": _cell_rows(pairs, names),
                            "quieter": [
                                {
                                    "model": names.get(c.model_version_id,
                                                       c.model_version_id),
                                    "capability": c.capability_key,
                                    "bucket": c.condition_bucket,
                                    "voices": [c.voices_before, c.voices_after],
                                    "platforms": [c.platforms_before, c.platforms_after],
                                    "lost_publishability": c.lost_publishability,
                                    "gone": c.gone,
                                }
                                for c in losses
                            ],
                        }
                    )
                    print()
                raise _RolledBack
        except _RolledBack:
            print("=" * 78)
            print("ROLLED BACK. Nothing was committed to staging.")
            print("=" * 78)
    finally:
        conn.close()

    path = pathlib.Path(args.json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(f"\nwritten to {path}")
    return 0


def _cell_rows(pairs, names):
    rows = []
    for before, after in pairs:
        if after is None:
            continue
        rows.append(
            {
                "model": names.get(after.key.model_version_id, after.key.model_version_id),
                "capability": after.key.capability_key,
                "bucket": after.key.condition_bucket,
                "n_eff_before": before.counts.n_eff if before else 0.0,
                "n_eff_after": after.counts.n_eff,
                "voices": after.counts.independent_voices,
                "platforms": after.counts.platform_count,
                "publishes": after.counts.n_eff >= N_EFF_MINIMUM
                and after.counts.platform_count >= PLATFORM_MINIMUM,
            }
        )
    return rows


def _print_cells(pairs, losses, names):
    """The best cell, what publishes, and what the board lost."""
    live = [(b, a) for b, a in pairs if a is not None]
    publishing = [
        a for _b, a in live
        if a.counts.n_eff >= N_EFF_MINIMUM and a.counts.platform_count >= PLATFORM_MINIMUM
    ]
    print(f"\n  cells: {len(live)}   PUBLISHING: {len(publishing)}")
    if not publishing:
        print("  NOTHING PUBLISHES.")
    ranked = sorted(live, key=lambda p: -p[1].counts.n_eff)[:3]
    print(f"  closest three, gate n_eff >= {N_EFF_MINIMUM} AND platforms >= {PLATFORM_MINIMUM}:")
    for before, after in ranked:
        was = before.counts.n_eff if before else 0.0
        short_by = N_EFF_MINIMUM - after.counts.n_eff
        per_voice = (
            after.counts.n_eff / after.counts.independent_voices
            if after.counts.independent_voices else 0.0
        )
        needs = short_by / per_voice if per_voice > 0 else float("inf")
        print(
            f"    {names.get(after.key.model_version_id, after.key.model_version_id):30s} "
            f"{after.key.capability_key:24s} "
            f"n_eff {was:.4f} -> {after.counts.n_eff:.4f}  "
            f"voices={after.counts.independent_voices} "
            f"platforms={after.counts.platform_count}"
        )
        print(
            f"      short by {short_by:.4f} = {needs:.0f} more voices at its own "
            f"per-voice weight ({per_voice:.4f})"
        )

    if not losses:
        print("\n  THE BOARD GOT NO QUIETER. 0 cells lost voices or platforms.")
        return
    lost_gate = sum(1 for c in losses if c.lost_publishability)
    gone = sum(1 for c in losses if c.gone)
    print(f"\n  !! THE BOARD GOT QUIETER: {len(losses)} cells lost evidence, "
          f"{gone} lost all of it, {lost_gate} fell below PLATFORM_MINIMUM.")
    for c in losses[:25]:
        marks = []
        if c.gone:
            marks.append("GONE")
        if c.lost_publishability:
            marks.append("NO LONGER PUBLISHABLE")
        print(
            f"     {names.get(c.model_version_id, c.model_version_id):30s} "
            f"{c.capability_key:24s} {c.condition_bucket:14s} "
            f"voices {c.voices_before}->{c.voices_after}  "
            f"platforms {c.platforms_before}->{c.platforms_after}"
            + (f"   {' | '.join(marks)}" if marks else "")
        )
    if len(losses) > 25:
        print(f"     ... and {len(losses) - 25} more, all in the JSON")


if __name__ == "__main__":
    raise SystemExit(main())
