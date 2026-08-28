"""Where the 20 seconds per thread actually goes. API, verification, store.

WHY MEASURE RATHER THAN REASON

At $0.00208 a thread the model call looked too cheap to be slow, so the 20s
had to be a sleep, a per-document round trip, or something sequential. It is
none of those: `grep -rn "sleep\|backoff\|rate_limit"` over the extract path
returns one comment and no code, and `_complete_with_retries` makes ONE call
per thread plus at most two schema retries - not one per claim.

So the remaining candidates are the API call itself and the two phases nobody
has timed. This times all three on the same threads, with the prompt size
beside them, because a 15-second "flash" call usually means a large context
rather than a slow model.

WHAT IT COSTS. `--threads N` model calls, about $0.002 each. Default 5, so
roughly one cent. It writes NOTHING: the connection is opened read-only for
`DocumentFacts` and the pipeline's store writes are rolled back.

    python scripts/time_extraction_phases.py --threads 5
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=5)
    parser.add_argument("--export", default="_export_extract/threads")
    args = parser.parse_args()

    from collect.db import connect
    from collect.surface_resolver import RegistrySurfaceResolver
    from judge.config import capabilities
    from judge.extract import export_source
    from judge.extract.client import OpenRouterClient
    from judge.pipeline import Pipeline

    loaded = export_source.load(pathlib.Path(args.export))
    threads = loaded.threads[: args.threads]
    print(f"threads to time : {len(threads)} of {len(loaded.threads)} in the export")

    conn = connect()
    resolver = RegistrySurfaceResolver.from_connection(conn)

    # DocumentFacts, the same way `judge/cli.py` builds them, so the timing is
    # of the real path and not a lighter one.
    from judge.cli import _document_facts

    doc_ids = {m for t in threads for m in t.raw_text_of}
    facts, _ = _document_facts(conn, doc_ids)
    model_version_of = {
        r[0]: r[2]
        for r in conn.execute(
            "SELECT canonical_id, display_name, id FROM model_version"
        ).fetchall()
    }

    client = OpenRouterClient.from_env()

    # ── the instrument ──────────────────────────────────────────────────────
    # Wrapping `complete` rather than editing the client: the measurement must
    # not change the thing measured, and a timer inside `client.py` would be a
    # judge/ edit for a collect/ question.
    api_seconds: list[float] = []
    prompt_chars: list[int] = []
    original = client.complete

    def timed_complete(*, system, user, tool_schema):
        prompt_chars.append(len(system) + len(user))
        t0 = time.perf_counter()
        try:
            return original(system=system, user=user, tool_schema=tool_schema)
        finally:
            api_seconds.append(time.perf_counter() - t0)

    client.complete = timed_complete  # type: ignore[method-assign]

    pipeline = Pipeline(
        conn,
        client=client,
        capability_keys=list(capabilities().keys()),
        extractor_model=__import__("os").getenv("EXTRACTOR_MODEL", "google/gemini-2.5-flash"),
    )

    rows = []
    for thread in threads:
        calls_before = len(api_seconds)
        t0 = time.perf_counter()
        result = pipeline.run(
            thread,
            facts=facts,
            model_version_of=model_version_of,
            resolve_surface=resolver,
        )
        total = time.perf_counter() - t0
        calls = len(api_seconds) - calls_before
        api = sum(api_seconds[calls_before:])
        rows.append(
            {
                "thread": thread.thread_context_id,
                "flattened_chars": len(thread.flattened_text),
                "total_s": total,
                "api_s": api,
                "other_s": total - api,
                "api_calls": calls,
                "verified": len(result.extraction.verified),
                "stored": len(result.stored_claim_ids),
            }
        )
        r = rows[-1]
        print(
            f"  {r['thread'][:34]:34s} total={r['total_s']:6.2f}s  "
            f"api={r['api_s']:6.2f}s ({r['api_calls']} call)  "
            f"rest={r['other_s']:5.2f}s  text={r['flattened_chars']:6d}ch  "
            f"verified={r['verified']:2d} stored={r['stored']:2d}"
        )

    # ROLLED BACK. This script measures; it must not be a write path.
    conn.rollback()
    conn.close()

    print()
    print("=" * 70)
    tot = [r["total_s"] for r in rows]
    api = [r["api_s"] for r in rows]
    rest = [r["other_s"] for r in rows]
    print(f"per-thread total   median {statistics.median(tot):6.2f}s   "
          f"min {min(tot):6.2f}  max {max(tot):6.2f}")
    print(f"  API call         median {statistics.median(api):6.2f}s   "
          f"= {100*sum(api)/sum(tot):.1f}% of wall clock")
    print(f"  everything else  median {statistics.median(rest):6.2f}s   "
          f"= {100*sum(rest)/sum(tot):.1f}%  (verification + weighting + store)")
    print()
    print(f"prompt size        median {statistics.median(prompt_chars):,} chars "
          f"({statistics.median(prompt_chars)//4:,} tokens approx)")
    print(f"flattened text     median "
          f"{statistics.median([r['flattened_chars'] for r in rows]):,} chars")
    print()
    print(f"projected 1,512 threads at this rate: "
          f"{1512*statistics.median(tot)/3600:.1f} hours")

    out = pathlib.Path("_timing_extraction.json")
    out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"\nper-thread rows written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
