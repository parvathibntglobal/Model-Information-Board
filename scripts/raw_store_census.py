#!/usr/bin/env python
"""Where the corpus's payloads physically are, per source. Read-only (#321).

    python scripts/raw_store_census.py                  # DATABASE_URL, RAW_STORE_PATH
    python scripts/raw_store_census.py --dsn URL --store PATH

For every `document.text_ref` and every `thread_context.flattened_text_ref`,
by source, it counts refs whose payload is

    on disk      in this machine's raw store folder
    in raw_blob  in the shared `raw_blob` table of the database it reads
    readable     either of the two (they overlap; both are shown)
    missing      on neither
    tombstoned   a marker on disk or a `<ref>.tombstone` key in raw_blob
    malformed    not a store ref at all (`parse_ref` refuses it - #303's
                 `flattened/inline-see-json` is one)

so that readable + missing + tombstoned + malformed = rows, on every line.

WHY IT EXISTS. Every reading of #321 so far was a hand-run scan pasted into a
comment - 30.8% missing on one machine and 76.2% on another, both 2026-09-16, over
denominators that had already moved by the time they were compared. Reading 1
(the gap widens against a growing denominator) and reading 2 (blobs counted
present go missing) only separate across repeated, comparable runs, and this
is the comparable run. It prints the date, the host and every denominator.

⚠ IT PERSISTS NOTHING. One row per run in a table is what #321 asks for and is
  a `contract/` change, proposed rather than taken; until then the output is
  the record and somebody keeps it.

⚠ IT NEVER CALLS `RawStore.get`. That falls back to the shared store and CACHES
  what it downloads, so a census through it would write to the disk it is
  measuring and change its own answer. Presence is checked by path and by key.

READ-ONLY BY CONSTRUCTION: the connection is opened with
`default_transaction_read_only=on` and `read_only = True`; there is no write
verb in this file, and the raw store is only stat'ed.
"""
from __future__ import annotations

import argparse
import socket
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STATES = ("readable", "missing", "tombstoned", "malformed")
#: Keys asked of raw_blob per query. `= ANY(%s)` over a few thousand keys is one
#: index probe each; the batch only bounds the parameter size.
BATCH = 5000
#: A thread_context whose members resolve to no `document` row. Named, not
#: dropped and not folded into a real source (rule 6).
UNRESOLVED = "(no member document)"


def connect_read_only(dsn: str):
    import psycopg

    conn = psycopg.connect(dsn, connect_timeout=15,
                           options="-c default_transaction_read_only=on")
    conn.read_only = True
    return conn


def shared_keys(conn, keys: set[str]) -> set[str] | None:
    """The subset of `keys` the `raw_blob` table holds - or None when there is
    no such table, which is "not measured", never "holds none" (rule 6)."""
    if conn.execute("SELECT to_regclass('raw_blob')").fetchone()[0] is None:
        return None
    wanted = sorted(keys)
    found: set[str] = set()
    for i in range(0, len(wanted), BATCH):
        found.update(
            row[0] for row in conn.execute(
                "SELECT key FROM raw_blob WHERE key = ANY(%s)", (wanted[i:i + BATCH],)
            ).fetchall()
        )
    return found


def classify(ref: str, store: Path, shared: set[str] | None) -> tuple[str, bool, bool]:
    """`(state, on_disk, in_raw_blob)` for one ref. Stats only; reads no bytes."""
    from collect.rawstore import parse_ref

    try:
        parse_ref(ref)
    except ValueError:
        return "malformed", False, False
    path = store / ref
    in_shared = shared is not None and ref in shared
    if (path.with_name(path.name + ".tombstone").exists()
            or (shared is not None and ref + ".tombstone" in shared)):
        return "tombstoned", path.is_file(), in_shared
    on_disk = path.is_file()
    return ("readable" if on_disk or in_shared else "missing"), on_disk, in_shared


def tally(rows: list[tuple[str, str]], store: Path,
          shared: set[str] | None) -> dict[str, Counter]:
    """Per source: rows, each state, and the on_disk / in_raw_blob overlap."""
    out: dict[str, Counter] = {}
    for source, ref in rows:
        state, on_disk, in_shared = classify(ref, store, shared)
        c = out.setdefault(source, Counter())
        c["rows"] += 1
        c[state] += 1
        c["on_disk"] += on_disk
        c["in_raw_blob"] += in_shared
    return out


def census(conn, store: Path) -> dict:
    """Both populations, read once each. Returns plain data for `render`."""
    docs = [
        (str(source), str(ref)) for source, ref in conn.execute(
            "SELECT source, text_ref FROM document WHERE text_ref IS NOT NULL"
        ).fetchall()
    ]
    contexts = [
        (str(source) if source is not None else UNRESOLVED, str(ref))
        for ref, source in conn.execute(
            "SELECT tc.flattened_text_ref, "
            "       (SELECT min(d.source) FROM document d "
            "         WHERE d.id = ANY(tc.member_document_ids)) "
            "FROM thread_context tc"
        ).fetchall()
    ]
    document_rows = conn.execute("SELECT count(*) FROM document").fetchone()[0]
    refs = {ref for _s, ref in docs + contexts}
    shared = shared_keys(conn, refs | {r + ".tombstone" for r in refs})
    return {
        "measured_at": datetime.now(UTC),
        "host": socket.gethostname(),
        "store": store,
        "store_exists": store.is_dir(),
        "raw_blob_measured": shared is not None,
        "document_rows": int(document_rows),
        "document": tally(docs, store, shared),
        "thread_context": tally(contexts, store, shared),
    }


def _table(title: str, by_source: dict[str, Counter]) -> list[str]:
    cols = ("rows", "on_disk", "in_raw_blob", *STATES)
    total = Counter()
    for c in by_source.values():
        total.update(c)
    lines = [title, "  " + f"{'source':<22}" + "".join(f"{h:>12}" for h in cols)]
    ordered = sorted(by_source.items(), key=lambda kv: (-kv[1]["rows"], kv[0]))
    for source, c in [*ordered, ("ALL", total)]:
        lines.append("  " + f"{source:<22}" + "".join(f"{c[h]:>12,}" for h in cols))
    return lines


def render(result: dict) -> str:
    out = [
        f"raw-store census  {result['measured_at'].strftime('%Y-%m-%dT%H:%M:%SZ')}  "
        f"host {result['host']}",
        f"  raw store   {result['store']}"
        + ("" if result["store_exists"] else "   (NO SUCH FOLDER: on_disk is 0 by absence)"),
        "  raw_blob    " + ("the table in the database read"
                            if result["raw_blob_measured"] else
                            "NO raw_blob TABLE in this database - in_raw_blob NOT MEASURED, "
                            "so `missing` means only 'not on disk'"),
        "",
    ]
    docs = result["document"]
    with_ref = sum(c["rows"] for c in docs.values())
    out += _table(f"document.text_ref - {with_ref:,} of {result['document_rows']:,} "
                  f"document rows carry a ref", docs)
    out.append("")
    contexts = result["thread_context"]
    out += _table(f"thread_context.flattened_text_ref - "
                  f"{sum(c['rows'] for c in contexts.values()):,} rows, source of "
                  f"their member documents", contexts)
    out += [
        "",
        "on_disk and in_raw_blob overlap; readable + missing + tombstoned + "
        "malformed = rows. Nothing was written.",
    ]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dsn", help="database to read (default: DATABASE_URL)")
    ap.add_argument("--store", type=Path, help="raw store folder (default: RAW_STORE_PATH)")
    args = ap.parse_args(argv)

    import os

    from collect.config import settings

    # `settings()` loads .env, so it runs only when a default is needed.
    configured = settings() if args.dsn is None or args.store is None else None
    dsn = args.dsn or os.getenv("DATABASE_URL")
    if not dsn:
        print("no database: pass --dsn or set DATABASE_URL", file=sys.stderr)
        return 2
    store = args.store or configured.raw_store_path
    conn = connect_read_only(dsn)
    try:
        result = census(conn, Path(store))
    finally:
        conn.close()
    print(render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
