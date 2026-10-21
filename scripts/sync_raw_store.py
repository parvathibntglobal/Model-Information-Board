#!/usr/bin/env python
"""Send this machine's raw store to the shared store. Idempotent.

THE SHARED STORE is whichever RAW_STORE_REMOTE names (collect/rawstore_remote.py):
the `raw_blob` table in the shared database (`postgres`, chosen 2026-10-07), or
an S3-compatible bucket (`s3`). "The bucket" below means either.

Payloads written before the shared store existed live only on the machine that
fetched them - that is why the first scheduled Action could read none of them.
Every machine that has fetched runs this once; from then on `RawStore.put`
shares as it writes, and this only re-sends what an upload failure missed.

WHAT IT SENDS: every blob under `raw/` and `flattened/`, keyed by its path,
which is its ref. A key the bucket already holds is skipped - content
addressing makes "present" mean "identical". Tombstone markers are sent too,
and the blob they mark is deleted from the bucket, so a takedown made here
before the bucket existed still reaches every machine.

WHAT IT NEVER DOES: delete anything locally, or overwrite a key the bucket has.

    python scripts/sync_raw_store.py                # count what is local, send nothing
    python scripts/sync_raw_store.py --apply        # send it
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

NAMESPACES = ("raw", "flattened")


def local_items(root: Path) -> tuple[list[str], list[str]]:
    """(blob refs, tombstone refs) under the store's namespaces."""
    blobs, markers = [], []
    for ns in NAMESPACES:
        base = root / ns
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix == ".tmp":
                continue
            ref = path.relative_to(root).as_posix()
            (markers if ref.endswith(".tombstone") else blobs).append(ref)
    return blobs, markers


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="upload; without it, only count")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args(argv)

    from collect.config import settings
    from collect.rawstore_remote import remote_from_env

    root = Path(settings().raw_store_path)
    blobs, markers = local_items(root)
    print(f"local store {root}: {len(blobs)} blob(s), {len(markers)} tombstone marker(s)")
    if not args.apply:
        print("dry run: nothing sent. Re-run with --apply.")
        return 0

    remote = remote_from_env()
    if remote is None:
        print("no shared raw store is configured (set RAW_STORE_REMOTE=postgres, or the "
              "four RAW_STORE_S3_* variables); nothing to send to.")
        return 1
    # THE WRITE GATE when the target is the shared DATABASE: it refuses
    # ENVIRONMENT=development pointed at a database that is not this machine
    # (tests/test_every_write_path_takes_the_gate.py).
    from collect.rawstore_remote import PgBlobs
    from judge.writeguard import UnsafeWriteRefused, check

    if isinstance(remote, PgBlobs):
        try:
            check(remote.dsn, command="sync_raw_store.py --apply")
        except UnsafeWriteRefused as error:
            print(error)
            return 1

    counts = {"uploaded": 0, "already": 0, "failed": 0}
    started = time.monotonic()

    def send(ref: str) -> str:
        try:
            return "uploaded" if remote.put_if_absent(ref, (root / ref).read_bytes()) else "already"
        except Exception as error:  # noqa: BLE001 - counted and named
            print(f"  FAILED {ref}: {type(error).__name__}: {error}")
            return "failed"

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, outcome in enumerate(pool.map(send, blobs), 1):
            counts[outcome] += 1
            if i % 1000 == 0:
                print(f"  {i}/{len(blobs)} {counts} ({time.monotonic() - started:.0f}s)",
                      flush=True)
    for marker in markers:
        blob = marker.removesuffix(".tombstone")
        remote.upload(marker, (root / marker).read_bytes())
        remote.delete(blob)
    print(f"done in {time.monotonic() - started:.0f}s: {counts}; "
          f"{len(markers)} tombstone(s) sent and their blobs removed from the bucket")
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
