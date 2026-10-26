"""Harvest V2EX's AI boards - newest topics with their replies - into `document`.

    .venv/Scripts/python.exe scripts/harvest_v2ex.py --max-topics 50

NIGHTLY, LIKE THE FEEDS (2026-10-26). V2EX's v1 API lists a board's newest
topics and has no search, so the boards named on the `v2ex` row of
contract/sources.yaml are read once a night and each model's fetch reads the
threads that name it. Topics already stored are skipped; replies come with the
topic the first night it is read (collect/adapters/v2ex.py says why that is
the limit). Writes are append-only, and preflight runs first because this
writes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.adapters.v2ex import (  # noqa: E402
    DOCUMENT_SOURCE,
    SOURCE_ID,
    harvester_for_source,
    observe_v2ex_use,
)
from collect.config import settings  # noqa: E402
from collect.http import build_client  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.registry.sources import load_sources  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max-topics", type=int, default=50,
                        help="new topics read per run across all boards; the rest are "
                             "counted as deferred")
    parser.add_argument("--dry-run", action="store_true",
                        help="read the boards into a store, write nothing to the database")
    args = parser.parse_args(argv)

    contract = load_sources()
    source = next((s for s in contract.platforms if s.get("id") == SOURCE_ID), None)
    if source is None:
        print("no `v2ex` row in contract/sources.yaml; nothing to read")
        return 0
    nodes = list(source.get("nodes") or [])
    if not nodes:
        # A row with no boards is a contract defect, not a quiet night (rule 12).
        print("the `v2ex` row names no `nodes`; refusing", file=sys.stderr)
        return 1

    conn = None
    held: frozenset[str] = frozenset()
    if not args.dry_run:
        from collect.db import connect
        from collect.ops.preflight import PreflightRefused, preflight
        from collect.registry.policy import load_registry_policy

        conn = connect()
        try:
            print(preflight(conn, environment=settings().environment,
                            policy=load_registry_policy(), sources=[source],
                            rulings=contract.rulings,
                            observations={SOURCE_ID: observe_v2ex_use()}).summary())
        except PreflightRefused as refusal:
            print(str(refusal), file=sys.stderr)
            conn.close()
            return 1
        if not conn.execute("SELECT 1 FROM source WHERE id = %s", (SOURCE_ID,)).fetchone():
            print("v2ex: REFUSED - no `source` row; run "
                  "`python -m collect.cli registry load-sources` first", file=sys.stderr)
            conn.close()
            return 1
        held = frozenset(r[0] for r in conn.execute(
            "SELECT external_id FROM document WHERE source = %s", (DOCUMENT_SOURCE,)))

    try:
        with build_client(timeout=30.0) as client:
            harvester = harvester_for_source(source, rulings=contract.rulings, client=client,
                                             store=RawStore(Path(settings().raw_store_path)))
            run = harvester.harvest(nodes, held=held, max_topics=args.max_topics)
        line = (f"v2ex: {len(nodes)} board(s), {run.listed} topic(s) listed, "
                f"{run.already_stored} already stored, {len(run.topics)} topic(s) and "
                f"{len(run.replies)} repl(ies) read, {run.deferred} deferred, "
                f"{run.requests} request(s), {run.http_errors} error(s)")
        if conn is not None:
            report = harvester.write_documents(conn, run)
            conn.commit()
            line += f"; {report.inserted} document(s) inserted"
        print(line)
    finally:
        if conn is not None:
            conn.close()
    # Every request failing is not a quiet night.
    return 1 if run.http_errors and not run.topics else 0


if __name__ == "__main__":
    raise SystemExit(main())
