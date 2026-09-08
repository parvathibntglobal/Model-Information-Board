"""Run E4's six gates over the stored corpus and report the distribution.

THE FIRST TIME TRIAGE HAS TOUCHED THE DATABASE. `document.triage_verdict` was
NULL on all 6,502 rows and `collect/ops/chain.py` carried
`Stage('triage', run=None)`, so every survival figure this project has quoted
came from a script building `Document`s by hand off a JSONL export - including
the 82.8% in `collect/triage/gates.py`'s own docstring, which is a real figure
about a hand-built population and never was one about the corpus.

    .venv\\Scripts\\python.exe scripts/triage_stored_corpus.py
    .venv\\Scripts\\python.exe scripts/triage_stored_corpus.py --write

DRY RUN BY DEFAULT, AND THE DEFAULT IS THE POINT. `DATABASE_URL` is the SHARED
staging database, and CLAUDE.md's convention is that a staging write session is
announced before it happens. `--write` is the announcement in code form.

⚠  IT WRITES `triage_verdict` AND `filter_reasons`, NEVER `document.status`.
   Two of the six gates cannot run - no language detector is installed and
   `contract/bots.yaml` does not exist - so rule 8 makes this a recorded field
   rather than a gate. `status` is the column `judge/` filters on, and dropping
   rows out of its view on four gates of six would make a false positive
   invisible. `collect/triage/run.py`'s docstring carries the argument.

THE REPORT IS PERSISTED, because a run that enters an argument and was not
saved is gone: the extractor is not involved here and the gates are
deterministic, but the CORPUS is not - it grows every sweep, so tonight's
distribution is unreproducible tomorrow.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collect.config import settings  # noqa: E402
from collect.db import connect  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.triage.run import (  # noqa: E402
    SUBJECT_FROM_THREAD_ROOT,
    gate_availability,
    triage_stored,
)

DEFAULT_OUT = "docs/measurements/triage-first-run-2026-09-08.json"


def _root_reachability(conn) -> list[dict]:
    """Per source: can the subject gate reach a thread root at all?

    Reported for EVERY source and not only the ones in
    `SUBJECT_FROM_THREAD_ROOT`, because the question "would this platform's
    roots be reachable if the ruling were widened to it" is the one the
    widening decision turns on - and on Reddit the answer today is no, for a
    reason that is a defect rather than a property.
    """
    rows = conn.execute(
        """
        SELECT d.source,
               count(*)                                        AS docs,
               count(*) FILTER (WHERE d.parent_id IS NOT NULL)  AS children,
               count(*) FILTER (WHERE d.thread_root_id IS NOT NULL
                                 AND d.thread_root_id <> d.id)  AS root_id_set,
               count(*) FILTER (WHERE r.id IS NOT NULL)         AS root_row_resolves,
               count(DISTINCT d.thread_root_id)                 AS distinct_roots
        FROM document d
        LEFT JOIN document r
               ON r.id = d.thread_root_id AND d.thread_root_id <> d.id
        GROUP BY d.source
        ORDER BY docs DESC
        """
    ).fetchall()
    out = []
    for source, docs, children, root_id_set, resolves, distinct in rows:
        out.append(
            {
                "source": source,
                "documents": docs,
                "children": children,
                "thread_root_id_set": root_id_set,
                "root_row_resolves": resolves,
                "root_dangling": root_id_set - resolves,
                "distinct_roots": distinct,
                "reads_per_child": (
                    round(distinct / children, 3) if children else None
                ),
                "in_subject_ruling": source in SUBJECT_FROM_THREAD_ROOT,
            }
        )
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="write triage_verdict and filter_reasons. NOT document.status.",
    )
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--sources", default=None, help="comma-separated subset")
    parser.add_argument(
        "--subject-sources",
        default=None,
        help=(
            "MEASURE A COUNTERFACTUAL, do not widen the ruling. Comma-separated "
            "platforms whose subject gate reads the thread root; defaults to the "
            "ruling's own scope (hackernews). `--subject-sources "
            "hackernews,github` answers what widening to GitHub's 2,016 "
            "comments would do, as a number rather than an argument. Refuses to "
            "combine with --write."
        ),
    )
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    sources = (
        tuple(s.strip() for s in args.sources.split(",") if s.strip())
        if args.sources
        else None
    )
    subject_sources = (
        frozenset(s.strip() for s in args.subject_sources.split(",") if s.strip())
        if args.subject_sources
        else None
    )
    if subject_sources is not None and args.write:
        # A counterfactual's verdicts are not the ruling's verdicts, and a
        # column cannot say which run wrote it.
        parser.error(
            "--subject-sources measures a counterfactual and --write stores "
            "verdicts. Storing a counterfactual's verdicts would put rows in "
            "`triage_verdict` that no ruling produced, and nothing on the row "
            "would say so. Run them separately."
        )
    store = RawStore(Path(settings().raw_store_path))
    conn = connect(args.database_url)
    try:
        reachability = _root_reachability(conn)
        run = triage_stored(
            conn,
            store,
            dry_run=not args.write,
            sources=sources,
            subject_sources=subject_sources,
        )
    finally:
        conn.close()

    print()
    print("PER SOURCE")
    print(run.per_source_table())
    print()
    print(gate_availability(run))
    print()
    print(run.describe())
    print()
    print("THREAD-ROOT REACHABILITY (the subject gate's input)")
    header = (
        f"{'source':<12}{'children':>9}{'rootIdSet':>11}{'resolves':>9}"
        f"{'dangling':>9}{'distinct':>9}  in-ruling"
    )
    print(header)
    print("-" * len(header))
    for row in reachability:
        print(
            f"{row['source']:<12}{row['children']:>9}{row['thread_root_id_set']:>11}"
            f"{row['root_row_resolves']:>9}{row['root_dangling']:>9}"
            f"{row['distinct_roots']:>9}  {row['in_subject_ruling']}"
        )

    payload = {
        "ran_at": datetime.now(UTC).isoformat(),
        "what": (
            "E4's six gates over every stored document with no triage_verdict. "
            "THE FIRST RUN OF TRIAGE AGAINST THE DATABASE: the stage was "
            "run=None and triage_verdict was NULL on every row."
        ),
        "wrote": bool(args.write),
        "columns_written": (
            ["triage_verdict", "filter_reasons"] if args.write else []
        ),
        "columns_deliberately_not_written": ["status"],
        "why_not_status": (
            "Two of six gates cannot run (no language detector installed, "
            "contract/bots.yaml absent), so rule 8 keeps this a recorded field "
            "rather than a gate. `status` is what judge/ filters on."
        ),
        "population_fingerprint": run.population_fingerprint,
        "subject_from_thread_root": sorted(subject_sources or SUBJECT_FROM_THREAD_ROOT),
        "is_counterfactual": subject_sources is not None,
        "ruling_scope": sorted(SUBJECT_FROM_THREAD_ROOT),
        "eligible": run.eligible,
        "triaged": run.triaged,
        "kept": run.kept,
        "dropped": run.dropped,
        "written": run.written,
        "survival_over_triaged": (
            round(run.survival, 4) if run.survival is not None else None
        ),
        "denominator_note": (
            "Every rate is over TRIAGED, never over eligible. A document whose "
            "payload this host could not read, or whose payload is not prose, "
            "was never gated - putting it in a survival denominator reports our "
            "coverage as the corpus's quality (rule 7)."
        ),
        "not_gated": {
            "unreadable_payload": run.unreadable,
            "present_but_not_prose": run.not_prose,
            "unmapped_source": run.unmapped_source,
        },
        "dropped_by_gate": run.by_reason,
        "flagged_not_dropped": run.by_flag,
        "gates_that_could_not_run": run.never_ran,
        "gates_with_nothing_to_run_on": run.not_applicable,
        "subject_inherited": run.subject_inherited,
        "root_unresolvable": run.root_unresolvable,
        "root_unreadable": run.root_unreadable,
        "by_source": run.by_source,
        "thread_root_reachability": reachability,
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print()
    print(f"written: {args.out}")
    if not args.write:
        print(
            "DRY RUN. No column was written. `--write` sets triage_verdict and "
            "filter_reasons on the shared staging database - announce it first."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
