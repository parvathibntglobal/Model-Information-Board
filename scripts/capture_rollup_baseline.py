"""Capture the BEFORE state `scripts/report_rollup_delta.py` compares against.

WHY THIS EXISTS AS A SCRIPT AND NOT AS A HABIT. `_before_rollup.json` was
written by hand and then sat on disk for two days while the corpus tripled. It
recorded `claims_total: 51` against a table holding 197, so the delta report run
against it would have announced **+146 claims** as though the run being measured
had produced them — correct arithmetic answering a question it was not asked,
which is rule 7 in the form that survives inspection.

A stale baseline is worse than no baseline, and worse in a specific way: the
delta report says so loudly when the file is ABSENT ("NO BASELINE ... absolute
figures only") and cannot tell when it is merely old. So the file carries
`captured_at` as a real timestamp and `pipeline_version`, and this script
refuses to overwrite a capture from a different version without `--force` —
because that is the case where somebody is about to compare across a fork and
call the fork's contents a change.

    python scripts/capture_rollup_baseline.py [--out _before_rollup.json]
                                              [--pipeline-version V] [--force]
"""

from __future__ import annotations

import argparse
import json
import pathlib
from datetime import UTC, datetime


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="_before_rollup.json")
    ap.add_argument(
        "--pipeline-version",
        help="which fork to count. Defaults to judge's current PIPELINE_VERSION.",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="overwrite a baseline captured at a different pipeline_version",
    )
    args = ap.parse_args()

    from collect.db import connect
    from judge.store.claims import PIPELINE_VERSION

    version = args.pipeline_version or PIPELINE_VERSION
    path = pathlib.Path(args.out)

    if path.exists():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            previous = {}
        was = previous.get("pipeline_version")
        if was and was != version and not args.force:
            print(
                f"REFUSING to overwrite: {path} was captured at {was!r} and this "
                f"run counts {version!r}.\n"
                "  Comparing a rollup against a baseline from a different fork "
                "reports the fork\n"
                "  as the run's own result. Pass --force if that is genuinely "
                "what you want,\n"
                "  or --out a different file and keep both."
            )
            return 1
        if not was:
            print(
                f"  {path} exists and carries NO pipeline_version - it predates "
                "this script.\n"
                "  Overwriting it, which is the point: an undated baseline cannot "
                "be checked for staleness."
            )

    conn = connect()
    try:
        claims_total = conn.execute(
            "SELECT count(*) FROM claim WHERE pipeline_version = %s", (version,)
        ).fetchone()[0]
        cells_total = conn.execute("SELECT count(*) FROM cell").fetchone()[0]
        by_model = dict(
            conn.execute(
                "SELECT mv.canonical_id, count(DISTINCT c.id) FROM claim c "
                "JOIN model_version mv ON mv.id = c.model_version_id "
                "WHERE c.pipeline_version = %s GROUP BY 1",
                (version,),
            ).fetchall()
        )
        by_platform = dict(
            conn.execute(
                "SELECT d.source, count(*) FROM claim c "
                "JOIN document d ON d.id = c.document_id "
                "WHERE c.pipeline_version = %s GROUP BY 1",
                (version,),
            ).fetchall()
        )
        cells_by_model = dict(
            conn.execute(
                "SELECT mv.canonical_id, count(*) FROM cell ce "
                "JOIN model_version mv ON mv.id = ce.model_version_id GROUP BY 1"
            ).fetchall()
        )
        published = conn.execute(
            "SELECT count(*) FROM cell WHERE status = 'published'"
        ).fetchone()[0]
        # PER-CELL VOICES AND PLATFORMS, because the board getting QUIETER is the
        # direction nobody checks and the delta report cannot see it without a
        # before-state. `cell` is keyed without pipeline_version, so a rebuild
        # overwrites these and they are unrecoverable after the fact.
        cells = {
            f"{model}|{cap}|{bucket}": {
                "n_eff": float(n_eff or 0.0),
                "voices": voices,
                "platforms": platforms,
                "status": status,
            }
            for model, cap, bucket, n_eff, voices, platforms, status in conn.execute(
                "SELECT mv.canonical_id, ce.capability_key, ce.condition_bucket, "
                "ce.n_eff, ce.independent_voices, ce.platform_count, ce.status "
                "FROM cell ce JOIN model_version mv ON mv.id = ce.model_version_id"
            ).fetchall()
        }
    finally:
        conn.close()

    baseline = {
        "pipeline_version": version,
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "captured_by": "scripts/capture_rollup_baseline.py",
        "claims_total": claims_total,
        "cells_total": cells_total,
        "published_cells": published,
        "claims_by_model": by_model,
        "claims_by_platform": by_platform,
        "cells_by_model": cells_by_model,
        "cells": cells,
    }
    path.write_text(json.dumps(baseline, indent=1, sort_keys=True), encoding="utf-8")

    print(f"baseline captured at pipeline_version={version!r} -> {path}")
    print(f"  claims {claims_total}   cells {cells_total}   published {published}")
    print(f"  per-cell voices and platforms recorded for {len(cells)} cells, so a")
    print("  later run can report what the board LOST as well as what it gained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
