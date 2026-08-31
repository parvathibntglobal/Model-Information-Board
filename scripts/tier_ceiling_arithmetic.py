"""What the tier re-key can and cannot do, computed rather than estimated.

WHY THIS EXISTS. The re-weight itself needs the staging database, which was
unreachable on 2026-08-30 (TCP timeout to 52.17.75.29:5432, three probes over
twenty minutes, and a watcher that never saw it open). The claim-level output of
the 150-thread run was never persisted - only the DB has it - so the empirical
before/after cannot be produced from this checkout.

The substantive question survives that, because the headline result is a BOUND
and a bound does not need the rows. Every claim's `f_evidence` is multiplied by
at most `TIER_WEIGHT[B] / TIER_WEIGHT[D]`, `n_eff` is a sum of per-voice maxima,
and each voice's maximum can therefore rise by at most that same factor. So

    n_eff_after  <=  (0.65 / 0.12) * n_eff_before

holds for every cell whatever the split of the two booleans turns out to be.

WHAT IS MEASURED AND WHAT IS ASSUMED, because rule 7 applies to this file too:

    n_eff 0.1409, 7 voices, 2 platforms     MEASURED, on the 197 stored claims,
                                            2026-08-28. It is the best cell on
                                            the board, not a typical one.
    tier counts 157 D / 29 E / 11 F         MEASURED, same population
    the ladder's multipliers                CONTRACT, contract/harvest.yaml
    "every voice promotes to B"             ASSUMED, and it is the CEILING
                                            assumption - it cannot be exceeded
                                            and is very unlikely to be reached

The local extraction runs at the bottom are a DIFFERENT POPULATION - 186 blog
claims from three persisted runs, not the 197 stored across three platforms -
and are reported as such. They do not stand in for the corpus.

    python scripts/tier_ceiling_arithmetic.py [--json OUT]
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import pathlib

from judge.curate.gate import N_EFF_MINIMUM
from judge.vet.weight import TIER_WEIGHT

#: docs/measurements/first-multi-platform-extraction-150-threads.md §4.
BEST_CELL = {
    "cell": "anthropic/claude-sonnet-5 · reasoning.multistep",
    "n_eff": 0.1409,
    "voices": 7,
    "platforms": 2,
}

#: docs/proposals/for-engineer-2-tier-a-is-unreachable-by-construction.md §1.
STORED_TIERS = {
    "reddit": {"D": 134, "E": 16, "F": 10},
    "blog": {"D": 16, "E": 3, "F": 1},
    "github": {"D": 7, "E": 10, "F": 0},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="docs/measurements/tier-ceiling-arithmetic.json")
    args = ap.parse_args()

    lift = TIER_WEIGHT["B"] / TIER_WEIGHT["D"]
    lift_a = TIER_WEIGHT["A"] / TIER_WEIGHT["D"]

    totals: collections.Counter = collections.Counter()
    for counts in STORED_TIERS.values():
        totals.update(counts)
    stored = sum(totals.values())

    n_eff = BEST_CELL["n_eff"]
    voices = BEST_CELL["voices"]
    per_voice = n_eff / voices

    ceiling_b = n_eff * lift
    ceiling_a = n_eff * lift_a
    voices_needed_b = N_EFF_MINIMUM / (per_voice * lift)
    voices_needed_unmoved = N_EFF_MINIMUM / per_voice

    out = {
        "as_of": "2026-08-30",
        "why_not_the_database": (
            "staging unreachable (TCP timeout, 52.17.75.29:5432); the 150-thread "
            "run's per-claim output was never persisted, so the empirical "
            "before/after cannot be produced from this checkout"
        ),
        "gate": N_EFF_MINIMUM,
        "lift_D_to_B": lift,
        "lift_D_to_A": lift_a,
        "stored_claims": stored,
        "stored_tiers": dict(totals),
        "promotable_at_most": totals["D"],
        "unmovable": totals["E"] + totals["F"],
        "best_cell": BEST_CELL,
        "best_cell_ceiling_at_B": ceiling_b,
        "best_cell_ceiling_at_A": ceiling_a,
        "voices_needed_if_every_voice_reaches_B": voices_needed_b,
        "voices_needed_if_none_promote": voices_needed_unmoved,
    }

    print("=" * 74)
    print("THE CEILING. n_eff_after <= (B/D) * n_eff_before, for every cell.")
    print("=" * 74)
    print(f"  tier D -> B multiplies f_evidence by {lift:.4f}")
    print(f"  gate is {N_EFF_MINIMUM}")
    print()
    print(f"  best cell on the board:  {BEST_CELL['cell']}")
    print(f"    measured 2026-08-28    n_eff {n_eff:.4f}  "
          f"voices {voices}  platforms {BEST_CELL['platforms']}")
    print(f"    ceiling at tier B      {ceiling_b:.4f}   "
          f"{'PUBLISHES' if ceiling_b >= N_EFF_MINIMUM else 'DOES NOT PUBLISH'}"
          f"  ({ceiling_b / N_EFF_MINIMUM:.1%} of the gate)")
    print(f"    ceiling at tier A      {ceiling_a:.4f}   "
          f"{'PUBLISHES' if ceiling_a >= N_EFF_MINIMUM else 'DOES NOT PUBLISH'}"
          "   <- even the rung we refused")
    print()
    print("  So NOTHING publishes, and that conclusion does not depend on how the")
    print("  two booleans fall - it is an upper bound over every possible split.")
    print()
    print("  voices that cell would need, at its own measured per-voice weight:")
    print(f"    if every voice reaches B   {voices_needed_b:6.1f}  -> "
          f"{int(voices_needed_b) + 1} people")
    print(f"    if none of them promote    {voices_needed_unmoved:6.1f}  -> "
          f"{int(voices_needed_unmoved) + 1} people")
    print(f"    it has                     {voices}")
    print()
    print("=" * 74)
    print(f"WHAT IS EVEN ELIGIBLE, of the {stored} stored claims")
    print("=" * 74)
    for tier in ("D", "E", "F"):
        note = "can move" if tier == "D" else "no rungs - cannot move"
        print(f"  tier {tier}   {totals[tier]:4d}   {note}")
    print(f"  so at most {totals['D']} of {stored} claims move at all, and "
          f"{totals['E'] + totals['F']} cannot.")

    local = _local_runs()
    if local:
        out["local_blog_runs"] = local
        print()
        print("=" * 74)
        print("A DIFFERENT POPULATION, reported as one")
        print("=" * 74)
        print(f"  {local['claims']} claims from {len(local['files'])} persisted blog")
        print("  extraction runs. NOT the 197 stored across three platforms, and not")
        print("  a sample of them - blog only, and every one is in this checkout")
        print("  because its run happened to be saved.")
        print()
        for row, n in sorted(local["by_key"].items(), key=lambda kv: -kv[1]):
            print(f"    {n:4d}  {row}")
        print()
        print(f"  own-experience claims that would promote: {local['would_promote']}")
        print(f"  has_repro_steps true anywhere:            {local['repro_true']}")
        print(f"  has_numbers true on an own-experience:    {local['own_with_numbers']}")
        print()
        print("  On THIS population the re-key is a no-op. That is a fact about")
        print("  these runs and evidence about nothing else - and if the stored 197")
        print("  resemble it, the measured lift will be near zero, well under the")
        print("  ceiling above.")

    path = pathlib.Path(args.json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwritten to {path}")
    return 0


def _local_runs() -> dict | None:
    """Every persisted extraction run in the repo, keyed the way the ladder is."""
    by_key: collections.Counter = collections.Counter()
    files = []
    total = 0
    for name in sorted(glob.glob("docs/measurements/*.json")):
        try:
            blob = json.loads(pathlib.Path(name).read_text(encoding="utf-8"))
        except Exception:
            continue
        for claims in _claim_lists(blob):
            files.append(name)
            for claim in claims:
                total += 1
                by_key[
                    f"{claim.get('speaking')}  repro={bool(claim.get('has_repro_steps'))}"
                    f"  numbers={bool(claim.get('has_numbers'))}"
                ] += 1
    if not total:
        return None
    would_promote = sum(
        n for k, n in by_key.items()
        if k.startswith("own-experience") and ("repro=True" in k or "numbers=True" in k)
    )
    return {
        "files": sorted(set(files)),
        "claims": total,
        "by_key": dict(by_key),
        "would_promote": would_promote,
        "repro_true": sum(n for k, n in by_key.items() if "repro=True" in k),
        "own_with_numbers": sum(
            n for k, n in by_key.items()
            if k.startswith("own-experience") and "numbers=True" in k
        ),
    }


def _claim_lists(obj):
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "speaking" in obj[0]:
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _claim_lists(value)


if __name__ == "__main__":
    raise SystemExit(main())
