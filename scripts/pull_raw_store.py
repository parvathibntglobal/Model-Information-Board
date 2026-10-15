#!/usr/bin/env python
"""Fetch the raw payloads this machine is missing from the shared store. Idempotent.

THE OTHER HALF OF `scripts/sync_raw_store.py`. That script SENDS a machine's
raw files to the shared `raw_blob` table; nothing brought them back, so a
payload fetched on one machine stayed unreadable on every other - 7,425 of the
44,812 refs the local copy holds were missing from this machine's store on
2026-10-15, which is why a fetch reported threads "unreadable here" and the
blog generator skipped documents.

WHAT IT PULLS: every ref the refs database names (`document.text_ref`,
`thread_context.flattened_text_ref`) that is not a file in the local store and
is a row in the shared table.

WHAT IT CHECKS BEFORE WRITING (rule 12 - a payload that does not match its
name is refused and counted, never written): a `.../sha256/ab/cd/<hash>` key's
bytes must hash to `<hash>`. Content addressing is what makes "present" mean
"identical", so a mismatch is a corrupt row, not a newer version.

WHAT IT NEVER DOES: overwrite a local file, pull a payload that carries a
takedown marker here or in the shared store, or write to either database. It
only READS the shared table.

    python scripts/pull_raw_store.py              # count what is missing, write nothing
    python scripts/pull_raw_store.py --apply      # fetch it

The shared database is STAGING_DATABASE_URL, the refs database DATABASE_URL,
the store RAW_STORE_PATH - all required, none defaulted (rule 12).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TOMBSTONE = ".tombstone"
#: Both connections refuse writes at the server, not only by convention here.
READ_ONLY = "-c default_transaction_read_only=on"
BATCH = 500


def _need(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise SystemExit(f"{name} is not set; refusing rather than guessing which one was meant")
    return value


def hash_ok(key: str, data: bytes) -> bool:
    """A content-addressed key's bytes hash to the name it is stored under."""
    parts = key.split("/")
    if "sha256" not in parts:
        return False
    want = parts[-1]
    return hashlib.sha256(data).hexdigest() == want


def missing_refs(refs_conn, store: Path) -> list[str]:
    refs = {r[0] for r in refs_conn.execute("SELECT text_ref FROM document").fetchall()}
    refs |= {
        r[0] for r in refs_conn.execute("SELECT flattened_text_ref FROM thread_context").fetchall()
    }
    return sorted(
        r for r in refs if r and not (store / r).exists() and not (store / (r + TOMBSTONE)).exists()
    )


def pull(shared_conn, store: Path, refs: list[str], *, apply: bool) -> dict[str, int]:
    out = {
        "missing_here": len(refs),
        "held_shared": 0,
        "taken_down": 0,
        "written": 0,
        "refused_hash": 0,
    }
    for i in range(0, len(refs), BATCH):
        chunk = refs[i : i + BATCH]
        downs = {
            r[0][: -len(TOMBSTONE)]
            for r in shared_conn.execute(
                "SELECT key FROM raw_blob WHERE key = ANY(%s)", ([k + TOMBSTONE for k in chunk],)
            ).fetchall()
        }
        out["taken_down"] += len(downs)
        rows = shared_conn.execute(
            "SELECT key, data FROM raw_blob WHERE key = ANY(%s)", (chunk,)
        ).fetchall()
        for key, data in rows:
            if key in downs:
                continue
            out["held_shared"] += 1
            payload = zlib.decompress(bytes(data))
            if not hash_ok(key, payload):
                out["refused_hash"] += 1
                continue
            if not apply:
                continue
            path = store / key
            if path.exists():
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_bytes(payload)
            tmp.replace(path)
            out["written"] += 1
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write; without it, only count")
    args = ap.parse_args(argv)
    import psycopg

    store = Path(_need("RAW_STORE_PATH"))
    with psycopg.connect(_need("DATABASE_URL"), options=READ_ONLY) as refs_conn:
        refs = missing_refs(refs_conn, store)
    print(f"{len(refs):,} refs are named in the database and missing from {store}")
    if not refs:
        return 0
    with psycopg.connect(
        _need("STAGING_DATABASE_URL"), connect_timeout=45, options=READ_ONLY
    ) as shared_conn:
        out = pull(shared_conn, store, refs, apply=args.apply)
    print(
        f"shared store holds {out['held_shared']:,} of them; "
        f"{out['taken_down']:,} carry a takedown and are skipped; "
        f"{out['refused_hash']:,} refused (bytes do not match their name); "
        + (f"{out['written']:,} written." if args.apply else "nothing written (dry run).")
    )
    still = out["missing_here"] - out["held_shared"] - out["taken_down"]
    if still > 0:
        print(
            f"{still:,} are in no shared store yet: the machine that fetched them has not run "
            "scripts/sync_raw_store.py --apply."
        )
    return 1 if out["refused_hash"] else 0


if __name__ == "__main__":
    sys.exit(main())
