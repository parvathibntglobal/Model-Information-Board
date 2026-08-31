"""What the rollup changed, against a snapshot taken before it ran.

WHY A SNAPSHOT RATHER THAN A QUERY

"Which models gain a cell for the first time" is not answerable after the fact.
`cell` carries no first-seen column, and `created_at` is rewritten by
`rebuild-cells` at each pipeline version - so a cell that existed yesterday and
one built five minutes ago are indistinguishable in the table. The comparison has
to be made against a state captured BEFORE, or it is a recollection.

`_before_rollup.json` is that capture. If it is absent this script says so and
reports absolute figures only, rather than inventing a baseline.

WHAT IT REPORTS, AND THE ONE THING IT REFUSES TO COLLAPSE

    claims       total, new, and by model
    resolution   how many of the extractor's claims REACHED the table. An
                 unresolved claim leaves NO ROW - `claim.model_version_id` is
                 NOT NULL - so this number cannot come from `claim`. It comes
                 from the run report, and this script says so rather than
                 printing a resolution rate it cannot compute.
    cells        published / contested / insufficient per model, plus the GATE
                 FAILURE for each cell that did not publish. A cell that failed
                 on one platform and a cell that failed on weight are different
                 findings and a single "insufficient" count hides which.

    python scripts/report_rollup_delta.py [--before _before_rollup.json]
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib


#: Why a baseline on disk was not used. Each of these is a case where the file
#: EXISTS and comparing against it would produce arithmetic that is correct and
#: about the wrong question - the failure mode a missing file does not have,
#: because a missing file announces itself.
def baseline_refusal(
    before: dict, version: str, live_at_version: int | None = None
) -> str | None:
    """Why this baseline may not be compared against, or None if it may be.

    FOUR REFUSALS, AND THE FIRST TWO ARE THE SAME DEFECT SEEN TWICE. A stale
    baseline is worse than no baseline: the "NO BASELINE" path below is loud,
    and a two-day-old file is silent. `_before_rollup.json` sat on disk
    recording `claims_total: 51` while the table held 197, so a run against it
    would have announced **+146 claims** as the run's own result.

    ⚠ THE FOURTH WAS ADDED 2026-08-31 BECAUSE THE OTHER THREE MISSED THE CASE
      IN FRONT OF THEM. They catch staleness ACROSS a fork - a baseline at a
      different `pipeline_version`. They cannot see staleness WITHIN one:

          _before_rollup.json   e5.1, 197 claims, 94 cells, captured 04:17Z
          the table             e5.1, 211 claims, 105 cells, four hours later

      All three refusals returned None. A delta run would have announced
      **+14 claims and +11 cells** as the ruling's own result, when they are a
      teammate's extraction that landed in between - the identical defect the
      paragraph above describes, recurring inside a version rather than across
      one, and invisible to a guard built for the crossing.

      THE INVARIANT: a reweight FORKS rather than updates, so the old version's
      rows do not change. Its live count must therefore still equal what the
      baseline recorded. If it does not, work landed at that version after the
      capture and the baseline is describing a board that no longer existed
      when it was written.

      `live_at_version` is optional so the three original refusals stay callable
      without a database - they are pure functions of the file - and the fourth
      is skipped rather than guessed at when nobody supplied the count.
    """
    if before.get("stale"):
        return (
            "the file marks itself stale: "
            + str(before.get("stale_reason") or "no reason recorded")
        )
    if not before.get("pipeline_version"):
        return (
            "it carries no `pipeline_version`, so it predates "
            "scripts/capture_rollup_baseline.py and CANNOT BE CHECKED for "
            "staleness. An undated baseline is not a baseline - it is a number "
            "that will be believed"
        )
    if before["pipeline_version"] != version:
        return (
            f"it was captured at {before['pipeline_version']!r} and this run "
            f"counts {version!r}. Comparing across a fork reports the fork's "
            "contents as the run's own result"
        )
    recorded = before.get("claims_total")
    if live_at_version is not None and recorded is not None and recorded != live_at_version:
        drift = live_at_version - recorded
        return (
            f"it recorded {recorded} claims at {version!r} and the table now "
            f"holds {live_at_version} - a drift of {drift:+d} that landed AFTER "
            f"the capture and BEFORE this run. A reweight forks rather than "
            f"updates, so the old version's count cannot move on its own: this "
            f"is somebody else's work, and comparing against it would report "
            f"{drift:+d} claims as this run's own result"
        )
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", default="_before_rollup.json")
    parser.add_argument(
        "--pipeline-version",
        help="which fork to count. Defaults to judge's PIPELINE_VERSION.",
    )
    args = parser.parse_args()

    from collect.db import connect
    from judge.store.claims import PIPELINE_VERSION

    # ⚠ FILTERED BY VERSION SINCE 2026-08-30, and it was not before. A bump
    #   FORKS `claim` rather than updating it, so after the tier and
    #   document-facts re-weights the table holds four copies of every claim.
    #   `select count(*) from claim` would have reported roughly 4x and called
    #   the forks new evidence.
    version = args.pipeline_version or PIPELINE_VERSION

    # THE LIVE COUNT IS READ BEFORE THE BASELINE IS JUDGED, because the fourth
    # refusal needs it. Opening the connection earlier costs nothing and keeps
    # the refusal a single decision rather than one taken twice.
    conn = connect()
    try:
        live_at_version = conn.execute(
            "select count(*) from claim where pipeline_version = %s", (version,)
        ).fetchone()[0]
    finally:
        conn.close()

    before = None
    path = pathlib.Path(args.before)
    if path.exists():
        candidate = json.loads(path.read_text(encoding="utf-8"))
        refusal = baseline_refusal(candidate, version, live_at_version)
        if refusal is None:
            before = candidate
        else:
            print(f"BASELINE AT {path} REFUSED: {refusal}.")
            print("  Absolute figures only, and no first-time-cell comparison.")
            print("  Re-capture with scripts/capture_rollup_baseline.py.")
    else:
        print(f"NO BASELINE at {path}: absolute figures only, no first-time-cell "
              f"comparison. A missing baseline is not an empty one.")
    print(f"  counting claims at pipeline_version={version!r}")

    conn = connect()
    try:
        claims_total = conn.execute(
            "select count(*) from claim where pipeline_version = %s", (version,)
        ).fetchone()[0]
        cells_total = conn.execute("select count(*) from cell").fetchone()[0]

        print("=" * 74)
        print("CLAIMS")
        print("=" * 74)
        if before:
            print(f"  total       {before['claims_total']:5d} -> {claims_total:5d}"
                  f"   (+{claims_total - before['claims_total']})")
        else:
            print(f"  total       {claims_total}")

        by_platform = dict(conn.execute(
            "select d.source, count(*) from claim cl "
            "join document d on d.id = cl.document_id "
            "where cl.pipeline_version = %s group by 1 order by 2 desc",
            (version,),
        ).fetchall())
        print("\n  by platform (the field PLATFORM_MINIMUM = 2 counts):")
        for src, n in by_platform.items():
            was = (before or {}).get("claims_by_platform", {}).get(src, 0)
            print(f"    {src:10s} {n:5d}   (was {was})")

        print("\n  by model, models with claims:")
        rows = conn.execute(
            "select mv.canonical_id, count(distinct cl.id) from claim cl "
            "join model_version mv on mv.id = cl.model_version_id "
            "where cl.pipeline_version = %s group by 1 order by 2 desc",
            (version,),
        ).fetchall()
        prev_claims = (before or {}).get("claims_by_model", {})
        for cid, n in rows:
            was = prev_claims.get(cid, 0)
            flag = "  NEW" if was == 0 else ""
            print(f"    {cid:34s} {n:5d}   (was {was}){flag}")

        print()
        print("=" * 74)
        print("CELLS - what each model page renders")
        print("=" * 74)
        if before:
            print(f"  total       {before['cells_total']:5d} -> {cells_total:5d}"
                  f"   (+{cells_total - before['cells_total']})")

        cols = {r[0] for r in conn.execute(
            "select column_name from information_schema.columns "
            "where table_name = 'cell'"
        ).fetchall()}
        status_col = next((c for c in ("status", "cell_status") if c in cols), None)
        if status_col is None:
            print("  `cell` has no status column; cannot report render state.")
            print(f"  columns: {sorted(cols)}")
            return 0

        # `cell` PERSISTS THE COUNTS AND NOT THE FAILURES. There is no
        # `gate_failures` column, so "why did this cell not publish" has to be
        # recomputed from the three columns the gate reads. That is counting from
        # stored values against thresholds in `judge/curate/gate.py` - not a
        # second opinion about the cell, and it cannot disagree with `status`
        # unless the thresholds moved since the rollup, which is worth knowing.
        select = (
            f"select mv.canonical_id, ce.capability_key, ce.condition_bucket, "
            f"ce.{status_col}, ce.n_eff, ce.independent_voices, ce.platform_count, "
            f"ce.max_author_share "
            "from cell ce join model_version mv on mv.id = ce.model_version_id "
            "order by 1, 2, 3"
        )
        cells = conn.execute(select).fetchall()

        per_model: dict[str, collections.Counter] = collections.defaultdict(
            collections.Counter
        )
        failures: collections.Counter = collections.Counter()
        published: list[tuple] = []
        from judge.curate.gate import (
            N_EFF_MINIMUM,
            PLATFORM_MINIMUM,
            author_cap_for,
        )

        # PER-CELL, KEYED THE WAY THE BASELINE KEYS IT. `cells_by_model` counts
        # cells per model and cannot see a cell that KEPT its row and LOST a
        # voice - the model still has the same number of cells. Only the
        # per-cell map records that, which is why capture_rollup_baseline.py
        # writes one.
        baseline_cells = (before or {}).get("cells", {})
        quieter: list[tuple] = []

        for row in cells:
            cid, cap, bucket, status = row[0], row[1], row[2], row[3]
            n_eff, voices, platforms, share = row[4], row[5], row[6], row[7]
            per_model[cid][status] += 1

            was = baseline_cells.get(f"{cid}|{cap}|{bucket}")
            if was is not None and (
                (voices or 0) < was.get("voices", 0)
                or (platforms or 0) < was.get("platforms", 0)
            ):
                quieter.append(
                    (cid, cap, bucket, was.get("voices", 0), voices or 0,
                     was.get("platforms", 0), platforms or 0)
                )

            if status == "published":
                published.append(row)
                continue
            why = []
            if (n_eff or 0) < N_EFF_MINIMUM:
                why.append("not_enough_weight")
            if (platforms or 0) < PLATFORM_MINIMUM:
                why.append("one_platform_only")
            if (share or 0) > author_cap_for(voices or 0):
                why.append("single_author_dominates")
            for f in why or ["status is not published and no threshold explains it"]:
                failures[f] += 1

        prev_cells = (before or {}).get("cells_by_model", {})
        print(f"\n  {'model':34s} {'pub':>4s} {'cont':>5s} {'insuf':>6s}   was")
        for cid in sorted(per_model, key=lambda k: -sum(per_model[k].values())):
            c = per_model[cid]
            was = prev_cells.get(cid, 0)
            flag = "   FIRST CELL" if was == 0 else ""
            print(f"  {cid:34s} {c['published']:4d} {c['contested']:5d} "
                  f"{c['insufficient']:6d}   {was}{flag}")

        print(f"\n  PUBLISHED cells: {len(published)}")
        for row in published:
            print(f"    {row[0]:30s} {row[1]:22s} {row[2]:14s} "
                  f"n_eff={row[4]:.2f} voices={row[5]} platforms={row[6]}")

        if failures:
            print("\n  gate failures across every non-publishing cell:")
            for f, n in failures.most_common():
                print(f"    {n:5d}  {f}")
            print("\n  READ THIS AS THE BINDING CONSTRAINT, not as a total: a cell")
            print("  can fail two conditions at once, so these sum above the cell count.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
