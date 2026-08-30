"""How many stored claims change once `document.has_numbers`/`has_conditions`
actually reach the weighting path. Read-only; writes nothing.

WHAT WENT WRONG, IN ONE SENTENCE. `judge/cli.py:_document_facts` passed a
literal `None` for both columns, `compute()`'s refusal tested
`value is UNSUPPLIED` and did not catch `None`, and `specificity_factor` then
read it as falsy — so **every claim in the table was weighted as though both
were False**, on a check whose entire purpose was to make that impossible.

WHY A SEPARATE SCRIPT AND NOT `judge reweight --document-facts read`.
That command answers the same question and writes a fork to do it. This one
answers it against the rows as they stand, before anything is decided, because
the repaired check turns a NULL column into a REFUSED claim and refusing is
dropping. Nobody should learn how many claims that is by running the migration
that does it.

WHAT IT REPORTS

    would refuse       claims whose document has NULL in either column. Under
                       the repaired check these are not weighted at all, so
                       they leave the board. Broken out by which column,
                       because the repair is different for each.
    f_specificity      claims whose factor MOVES because the real value differs
                       from the False they were priced at. Only upward: the
                       old value was the minimum.
    unchanged          the columns are present and genuinely False.

Every figure carries its denominator. The population is the claims stored at
`--pipeline-version`, which is the corpus, not a sample of it.

    python scripts/measure_document_facts_gap.py [--pipeline-version e5.1]
                                                 [--json OUT]
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib

from judge.vet.weight import specificity_factor

_SQL = """
SELECT c.id, mv.canonical_id, d.source, c.specificity,
       d.has_numbers, d.has_conditions, c.has_repro_steps,
       w.f_specificity
FROM claim c
JOIN claim_weight w ON w.claim_id = c.id
JOIN document d ON d.id = c.document_id
LEFT JOIN model_version mv ON mv.id = c.model_version_id
WHERE c.pipeline_version = %s
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline-version", default="e5.1")
    ap.add_argument("--json", default="docs/measurements/document-facts-gap.json")
    args = ap.parse_args()

    from collect.db import connect

    conn = connect()
    try:
        rows = conn.execute(_SQL, (args.pipeline_version,)).fetchall()
    finally:
        conn.close()

    total = len(rows)
    if not total:
        print(f"NO CLAIMS at pipeline_version={args.pipeline_version!r}. "
              "An empty result is not a measured zero - check the version.")
        return 1

    refuse_reasons: collections.Counter = collections.Counter()
    refused_by_platform: collections.Counter = collections.Counter()
    refused_by_model: collections.Counter = collections.Counter()
    moved: list[tuple] = []
    unchanged = 0
    stale_before = 0

    for (claim_id, model, platform, specificity, doc_numbers, doc_conditions,
         repro, was_specificity) in rows:
        missing = [
            name
            for name, value in (("has_numbers", doc_numbers),
                                ("has_conditions", doc_conditions))
            if value is None
        ]
        if missing:
            refuse_reasons["+".join(missing)] += 1
            refused_by_platform[platform] += 1
            refused_by_model[model or "?"] += 1
            continue

        version_named = specificity in ("snapshot", "version")
        now = specificity_factor(
            version_named=version_named,
            has_numbers=bool(doc_numbers),
            has_conditions=bool(doc_conditions),
            has_repro_steps=bool(repro),
        )
        # What the row was ACTUALLY priced at, recomputed the way e5.1 priced
        # it - both document booleans read as False. Compared against the
        # stored column too, so a row that does not reproduce is reported
        # rather than assumed away.
        was = specificity_factor(
            version_named=version_named,
            has_numbers=False,
            has_conditions=False,
            has_repro_steps=bool(repro),
        )
        if was_specificity is not None and abs(float(was_specificity) - was) > 1e-4:
            stale_before += 1
        if abs(now - was) > 1e-4:
            moved.append((claim_id, model, platform, was, now))
        else:
            unchanged += 1

    refused = sum(refuse_reasons.values())
    print("=" * 74)
    print("DOCUMENT FACTS REACHING THE WEIGHTING PATH")
    print(f"population: {total} claims stored at pipeline_version="
          f"{args.pipeline_version!r} - the corpus, not a sample")
    print("=" * 74)
    print(f"  would REFUSE (a NULL column is not a False)   {refused:5d}"
          f"   {refused / total:6.1%}")
    for reason, n in refuse_reasons.most_common():
        print(f"      NULL in {reason:34s} {n:5d}")
    if refused_by_platform:
        print("    by platform:")
        for platform, n in refused_by_platform.most_common():
            print(f"      {platform:12s} {n:5d}")
        print("    by model, worst five:")
        for model, n in refused_by_model.most_common(5):
            print(f"      {model:34s} {n:5d}")
    print()
    print(f"  f_specificity MOVES                           {len(moved):5d}"
          f"   {len(moved) / total:6.1%}")
    by_pair: collections.Counter = collections.Counter()
    for _, _, _, was, now in moved:
        by_pair[f"{was:.2f} -> {now:.2f}"] += 1
    for pair, n in by_pair.most_common():
        print(f"      {pair:20s} {n:5d}")
    print()
    print(f"  columns present and genuinely False           {unchanged:5d}"
          f"   {unchanged / total:6.1%}")

    if stale_before:
        print()
        print(f"  ⚠ {stale_before} rows do NOT reproduce their stored f_specificity")
        print("    from (version_named, False, False, has_repro_steps). Something")
        print("    other than the None-slip moved them, so the 'was' column above")
        print("    is not the whole story for those rows. Reported rather than")
        print("    smoothed over - an unexplained row is the finding.")

    out = {
        "as_of_pipeline_version": args.pipeline_version,
        "population": total,
        "population_note": "claims stored at this pipeline_version - the corpus",
        "would_refuse": refused,
        "would_refuse_by_reason": dict(refuse_reasons),
        "would_refuse_by_platform": dict(refused_by_platform),
        "would_refuse_by_model": dict(refused_by_model),
        "f_specificity_moves": len(moved),
        "f_specificity_moves_by_pair": dict(by_pair),
        "unchanged": unchanged,
        "rows_not_reproducing_stored_f_specificity": stale_before,
    }
    path = pathlib.Path(args.json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwritten to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
