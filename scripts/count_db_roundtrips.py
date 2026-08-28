"""How many database round trips one claim-bearing thread costs, and to what.

THE FINDING THIS EXISTS TO PIN DOWN. Timing said a thread yielding 0 claims
costs 2.2s (all of it the model call) and a thread yielding claims costs 21s,
with only ~5s in the API. So ~16s is post-extraction work. `select 1` against
the shared database measures 167ms, and 16 / 0.167 is ~96 round trips.

This counts them and groups by statement shape, so the fix is visible rather
than inferred: a per-claim INSERT loop and a per-claim SELECT are different
repairs.

Writes are ROLLED BACK.

    python scripts/count_db_roundtrips.py --thread thread_context_00ce9a186b340888
"""

from __future__ import annotations

import argparse
import collections
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

_WS = re.compile(r"\s+")


def shape(sql: str) -> str:
    """A statement's shape: verb plus target, so 96 calls group into a few rows."""
    s = _WS.sub(" ", sql.strip())[:400]
    m = re.match(
        r"(?is)\b(select|insert into|update|delete from|with)\b\s+([a-z_.\"]+)", s
    )
    if m:
        return f"{m.group(1).lower()} {m.group(2)}"
    return s[:60]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread", required=True)
    parser.add_argument("--export", default="_export_extract/threads")
    args = parser.parse_args()

    from collect.db import connect
    from collect.surface_resolver import RegistrySurfaceResolver
    from judge.cli import _document_facts
    from judge.config import capabilities
    from judge.extract import export_source
    from judge.extract.client import OpenRouterClient
    from judge.pipeline import Pipeline

    loaded = export_source.load(pathlib.Path(args.export))
    threads = [t for t in loaded.threads if t.thread_context_id == args.thread]
    if not threads:
        raise SystemExit(f"{args.thread} not in {args.export}")
    thread = threads[0]

    conn = connect()
    resolver = RegistrySurfaceResolver.from_connection(conn)
    facts, _ = _document_facts(conn, set(thread.raw_text_of))
    model_version_of = {
        r[0]: r[2]
        for r in conn.execute(
            "SELECT canonical_id, display_name, id FROM model_version"
        ).fetchall()
    }

    # ── the instrument ──────────────────────────────────────────────────────
    # Wrapping the CURSOR, because psycopg executes through it and both
    # `conn.execute` and `with conn.cursor()` funnel here. Counting at the
    # connection would miss executemany and cursor reuse.
    counts: collections.Counter = collections.Counter()
    seconds: collections.Counter = collections.Counter()
    order: list[str] = []

    # A CURSOR SUBCLASS, not a wrapped instance: psycopg3 `Cursor.execute` is a
    # read-only attribute, so assigning over it raises. `cursor_factory` is the
    # supported seam and `conn.execute()` goes through it too.
    import psycopg

    class CountingCursor(psycopg.Cursor):
        def execute(self, query, params=None, **kwargs):  # type: ignore[override]
            key = shape(query if isinstance(query, str) else str(query))
            t0 = time.perf_counter()
            try:
                return super().execute(query, params, **kwargs)
            finally:
                dt = time.perf_counter() - t0
                counts[key] += 1
                seconds[key] += dt
                order.append(key)

        def executemany(self, query, params_seq, **kwargs):  # type: ignore[override]
            key = shape(query if isinstance(query, str) else str(query)) + " [many]"
            t0 = time.perf_counter()
            try:
                return super().executemany(query, params_seq, **kwargs)
            finally:
                dt = time.perf_counter() - t0
                counts[key] += 1
                seconds[key] += dt
                order.append(key)

    conn.cursor_factory = CountingCursor

    client = OpenRouterClient.from_env()
    api = [0.0]
    original = client.complete

    def timed(*, system, user, tool_schema):
        t0 = time.perf_counter()
        try:
            return original(system=system, user=user, tool_schema=tool_schema)
        finally:
            api[0] += time.perf_counter() - t0

    client.complete = timed  # type: ignore[method-assign]

    import os

    pipeline = Pipeline(
        conn,
        client=client,
        capability_keys=list(capabilities().keys()),
        extractor_model=os.getenv("EXTRACTOR_MODEL", "google/gemini-2.5-flash"),
    )

    counts.clear(); seconds.clear(); order.clear()   # exclude setup queries
    t0 = time.perf_counter()
    result = pipeline.run(
        thread,
        facts=facts,
        model_version_of=model_version_of,
        resolve_surface=resolver,
    )
    total = time.perf_counter() - t0
    conn.rollback()

    print(f"thread            {thread.thread_context_id}")
    print(f"verified claims   {len(result.extraction.verified)}")
    print(f"stored claims     {len(result.stored_claim_ids)}")
    print(f"cells touched     {len(result.cells)}")
    print()
    print(f"wall clock        {total:7.2f}s")
    print(f"  model call      {api[0]:7.2f}s   ({100*api[0]/total:.1f}%)")
    print(f"  database        {sum(seconds.values()):7.2f}s   "
          f"({100*sum(seconds.values())/total:.1f}%) in "
          f"{sum(counts.values())} statements")
    print(f"  neither         {total - api[0] - sum(seconds.values()):7.2f}s")
    print()
    print(f"{'statements':>6}  {'seconds':>8}  {'ms each':>8}  shape")
    for key, n in counts.most_common():
        print(f"{n:6d}  {seconds[key]:8.2f}  {1000*seconds[key]/n:8.1f}  {key}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
