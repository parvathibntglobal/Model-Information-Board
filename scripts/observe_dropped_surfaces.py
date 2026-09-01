"""Observe the surfaces that fail model resolution, instead of inferring them.

WHY RE-RUNNING A PAID BATCH IS NOT FREE, WHICH IS THE POINT WORTH CORRECTING

The ledger makes a re-run cheap by SKIPPING threads it has already read. That is
exactly why it cannot answer this question: a skipped thread makes no model call,
so nothing is proposed, so nothing is dropped, so there is nothing to observe. The
free path and the observable path are the same mechanism pointing in opposite
directions.

So this pays again, deliberately, on a small N. It bypasses the ledger
(`already_extracted={}`), raises `judge.pipeline` to INFO so the drop line is
actually emitted, and ROLLS BACK - it is a measurement, not a second write.

WHAT IT CONVERTS. 347 of 450 verified claims did not reach the table on the last
run, and every other exit in the storing loop is a `log.warning` reporting zero.
Resolution is the only silent one and it logs at INFO:

    "claim references %r which resolves to no tracked model"

`judge/cli.py` says of these drops: *"Neither is recorded anywhere but this
output."* This is that output, captured.

    python scripts/observe_dropped_surfaces.py --threads 10
"""

from __future__ import annotations

import argparse
import collections
import logging
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")


class _CaptureDrops(logging.Handler):
    """Collects the resolution-drop line rather than printing 200 of them."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.surfaces: list[str] = []
        self.other: collections.Counter = collections.Counter()

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if "resolves to no tracked model" in message:
            # The surface is the only quoted value on the line.
            start = message.find("'")
            end = message.rfind("'")
            self.surfaces.append(message[start + 1 : end] if start >= 0 else message)
        elif record.levelno >= logging.WARNING:
            self.other[message.split(":")[0][:70]] += 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=10)
    parser.add_argument("--export", default="_export_extract/threads")
    args = parser.parse_args()

    from collect.db import connect
    from collect.surface_resolver import RegistrySurfaceResolver
    from judge.cli import _document_facts
    from judge.config import capabilities
    from judge.extract import export_source
    from judge.extract.client import OpenRouterClient
    from judge.pipeline import Pipeline

    capture = _CaptureDrops()
    logging.getLogger("judge").setLevel(logging.INFO)
    logging.getLogger("judge").addHandler(capture)

    loaded = export_source.load(pathlib.Path(args.export))
    threads = loaded.threads[: args.threads]

    conn = connect()
    resolver = RegistrySurfaceResolver.from_connection(conn)
    facts, _ = _document_facts(conn, loaded.document_ids)
    model_version_of = {
        r[0]: r[2]
        for r in conn.execute(
            "SELECT canonical_id, display_name, id FROM model_version"
        ).fetchall()
    }

    pipeline = Pipeline(
        conn,
        client=OpenRouterClient.from_env(),
        capability_keys=list(capabilities().keys()),
        extractor_model=os.getenv("EXTRACTOR_MODEL", "deepseek/deepseek-v4-flash"),
    )

    verified = stored = 0
    for thread in threads:
        result = pipeline.run(
            thread,
            facts=facts,
            model_version_of=model_version_of,
            resolve_surface=resolver,
            # ONCE-PER-THREAD REBUILD OFF. This measures resolution, and a board
            # rebuild per thread is 90 round trips of noise.
            rebuild_cells=False,
        )
        verified += len(result.extraction.verified)
        stored += len(result.stored_claim_ids)

    # MEASUREMENT, NOT A WRITE.
    conn.rollback()
    conn.close()

    print(f"threads          : {len(threads)}")
    print(f"verified         : {verified}")
    print(f"stored           : {stored}")
    print(f"dropped          : {verified - stored}")
    print(f"  of which resolution failures OBSERVED: {len(capture.surfaces)}")
    print()

    tally = collections.Counter(capture.surfaces)
    print(f"{'count':>5}  surface the extractor proposed (unresolvable)")
    for surface, n in tally.most_common(40):
        print(f"{n:5d}  {surface!r}")

    if capture.other:
        print("\nother warnings seen:")
        for message, n in capture.other.most_common(6):
            print(f"  {n:4d}  {message}")

    unexplained = (verified - stored) - len(capture.surfaces)
    print(f"\nunexplained drops (verified - stored - observed resolution failures)"
          f": {unexplained}")
    if unexplained:
        print("  NOT ZERO, so resolution is not the whole story and the rest is "
              "still unaccounted for.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
