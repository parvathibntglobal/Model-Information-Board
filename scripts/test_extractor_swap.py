#!/usr/bin/env python
"""Test a candidate extractor model against the Gemini claims already on the board.

Runs the candidate (default deepseek-v4-flash) IN MEMORY over the exact threads
that produced a model's stored claims, and diffs against those stored (Gemini)
claims. The threads are held fixed, so any difference is the MODEL, not the
corpus. Rule 1 verification runs here exactly as in production.

WRITES NOTHING. The database connection is forced READ ONLY at the server, so no
code path in this process can write to it. Only the candidate extractor makes
network calls — one per thread, plus up to one schema retry.

    python scripts/test_extractor_swap.py --model-name "deepseek r1" --dry-run
    OPENROUTER_API_KEY=... python scripts/test_extractor_swap.py \
        --model-name "deepseek r1" --candidate deepseek/deepseek-v4-flash --limit 15
"""
from __future__ import annotations

import argparse
import contextlib
import re
import sys
import time
import urllib.parse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    import os
    for line in env.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
        if m:
            os.environ.setdefault(m.group(1), m.group(2))


def read_only_dsn(dsn: str) -> str:
    """Force default_transaction_read_only=on — a Postgres guarantee, not a promise."""
    sep = "&" if "?" in dsn else "?"
    ro = urllib.parse.quote("-c default_transaction_read_only=on")
    return f"{dsn}{sep}options={ro}"


def load_threads(conn, store, thread_ids):
    from judge.extract.runner import ThreadInput
    from judge.extract.verify import OffsetMapping
    inputs, unresolved = [], 0
    for tc in thread_ids:
        row = conn.execute(
            "SELECT flattened_text_ref, offset_map, member_document_ids "
            "FROM thread_context WHERE id=%s", (tc,)
        ).fetchone()
        if not row:
            unresolved += 1
            continue
        flat_ref, omap, members = row
        try:
            flattened = store.get_text(flat_ref)
        except Exception:
            unresolved += 1
            continue
        raw_text_of = {}
        for did, tref in conn.execute(
            "SELECT id, text_ref FROM document WHERE id = ANY(%s)", (list(members or []),)
        ).fetchall():
            if tref:
                with contextlib.suppress(Exception):
                    raw_text_of[did] = store.get_text(tref)
        if not raw_text_of:
            unresolved += 1
            continue
        inputs.append(ThreadInput(
            thread_context_id=tc, flattened_text=flattened,
            offset_map=tuple(OffsetMapping(**s) for s in (omap or ())),
            raw_text_of=raw_text_of,
        ))
    return inputs, unresolved


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model-name", required=True, help="display name to match, e.g. 'deepseek r1'")
    ap.add_argument("--candidate", default="deepseek/deepseek-v4-flash", help="OpenRouter model id")
    ap.add_argument("--baseline-like", default="%gemini%",
                    help="stored extractor_model to compare against")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_env()
    import os

    import psycopg

    from collect.config import settings
    from collect.rawstore import RawStore
    from judge.config import capabilities

    s = settings()
    store = RawStore(Path(s.raw_store_path))

    with psycopg.connect(read_only_dsn(s.database_url), connect_timeout=25) as conn:
        # separator-flexible: "deepseek r1" matches "DeepSeek-R1", "deepseek_r1", …
        pat = "%" + re.sub(r"\s+", "%", args.model_name.strip()) + "%"
        mv = conn.execute(
            "SELECT id, display_name FROM model_version "
            "WHERE display_name ILIKE %s ORDER BY display_name",
            (pat,),
        ).fetchall()
        if not mv:
            print(f"no model_version matches {args.model_name!r}.")
            return 1
        print("model matches:")
        for i, n in mv:
            print(f"   {n}   [{i}]")
        ids = [i for i, _ in mv]

        by_extractor = conn.execute(
            "SELECT extractor_model, count(*) FROM claim WHERE model_version_id = ANY(%s) "
            "GROUP BY extractor_model", (ids,)
        ).fetchall()
        print("\nstored claims about it, by extractor:")
        for em, c in by_extractor:
            print(f"   {em or '(null)'}: {c}")

        thread_ids = [r[0] for r in conn.execute(
            "SELECT DISTINCT thread_context_id FROM claim WHERE model_version_id = ANY(%s) "
            "AND thread_context_id IS NOT NULL", (ids,)
        ).fetchall()]
        threads, unresolved = load_threads(conn, store, thread_ids)
        if args.limit:
            threads = threads[: args.limit]
        print(f"\nthreads with a stored claim: {len(thread_ids)}   "
              f"resolvable locally: {len(threads) + 0}   unresolved: {unresolved}")

        if not threads:
            print("no threads resolvable on this machine — the payloads were harvested elsewhere. "
                  "Can't run the in-memory test here.")
            return 1

        if args.dry_run:
            print(f"\nDRY RUN — would make ~{len(threads)} candidate calls "
                  f"(~${len(threads) * 0.002:.2f} at ~$0.002/thread). No network, no spend.")
            return 0

        if not os.getenv("OPENROUTER_API_KEY"):
            print("\nOPENROUTER_API_KEY is unset — the paid stage refuses to start.")
            return 1

        # baseline: the stored claims for exactly these threads
        tids = [t.thread_context_id for t in threads]
        base = conn.execute(
            "SELECT thread_context_id, quote, capability_key, speaking, polarity FROM claim "
            "WHERE thread_context_id = ANY(%s) AND extractor_model ILIKE %s",
            (tids, args.baseline_like),
        ).fetchall()

    # ── run the candidate in memory ────────────────────────────────────────
    from judge.extract.client import OpenRouterClient
    from judge.extract.runner import ExtractionRefused, extract
    keys = list(capabilities().keys())
    client = OpenRouterClient(model=args.candidate, api_key=os.environ["OPENROUTER_API_KEY"])

    cand_claims, agg = [], Counter()
    print(f"\nrunning {args.candidate} over {len(threads)} threads…")
    t0 = time.perf_counter()
    for i, th in enumerate(threads, 1):
        try:
            run = extract(th, client=client, capability_keys=keys)
        except ExtractionRefused:
            agg["refused"] += 1
            continue
        except Exception as exc:  # provider errors: bad model id, outage, etc.
            print(f"  thread {i}: extractor error — {str(exc).splitlines()[0][:120]}")
            agg["errors"] += 1
            continue
        agg["verified"] += len(run.verified)
        agg["rejected"] += len(run.rejected)
        agg["fabricated"] += run.fabricated
        agg["proposed"] += run.proposed
        agg["retries"] += run.schema_retries
        agg["in_tok"] += run.input_tokens
        agg["out_tok"] += run.output_tokens
        for c, _ in run.verified:
            cand_claims.append((th.thread_context_id, c))
        print(f"  thread {i}/{len(threads)}: {len(run.verified)} verified", end="\r")
    secs = time.perf_counter() - t0
    print()

    # ── report ─────────────────────────────────────────────────────────────
    def dist(items, get):
        return ", ".join(f"{k}:{n}" for k, n in Counter(get(x) for x in items).most_common(8))

    print("\n" + "=" * 64)
    print(f"BASELINE (stored, {args.baseline_like})     vs     CANDIDATE ({args.candidate})")
    print("=" * 64)
    print(f"threads compared:            {len(threads)}")
    print(f"claims:            baseline {len(base):>4}      candidate {agg['verified']:>4}")
    pass_rate = f"{agg['verified'] / agg['proposed']:.0%}" if agg["proposed"] else "—"
    print(f"candidate quote-verify pass: {pass_rate}   "
          f"(fabricated {agg['fabricated']}, retries {agg['retries']})")
    print(f"candidate tokens:            {agg['in_tok']} in / {agg['out_tok']} out"
          f"   |  wall {secs:.1f}s  |  refused {agg['refused']}  errors {agg['errors']}")

    print("\ncapability   baseline:", dist(base, lambda r: r[2]))
    print("capability  candidate:", dist(cand_claims, lambda x: x[1].legacy_score_key))
    print("\nspeaking     baseline:", dist(base, lambda r: r[3]))
    print("speaking    candidate:", dist(cand_claims, lambda x: x[1].model_ref.speaking))

    # quote-level agreement on sentences BOTH extracted verbatim
    b_idx = {}
    for tc, q, cap, spk, _pol in base:
        b_idx.setdefault(tc, {})[q] = (cap, spk)
    shared = cap_ok = spk_ok = 0
    for tc, c in cand_claims:
        hit = b_idx.get(tc, {}).get(c.quote)
        if hit:
            shared += 1
            cap_ok += hit[0] == c.legacy_score_key
            spk_ok += hit[1] == c.model_ref.speaking
    print(f"\nverbatim-quote overlap (same sentence both extracted): {shared}")
    if shared:
        print(f"   same capability {cap_ok}/{shared} ({cap_ok / shared:.0%})   "
              f"same speaking {spk_ok}/{shared} ({spk_ok / shared:.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
