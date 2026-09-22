#!/usr/bin/env python
"""A/B two extraction models over the SAME threads, in memory, no DB writes.

Answers the only question a model swap actually raises: does the new extractor
find the same claims, verify them at the same rate, and classify them the same
way — at what token cost? Rule 1 (quote verification) is model-agnostic and runs
here exactly as in production, so a weaker model yields FEWER verified claims,
never wrong ones; that is why this diffs recall/agreement/cost, not correctness.

    OPENROUTER_API_KEY=... python scripts/ab_extractors.py _handoff/threads \
        --models google/gemini-2.5-flash deepseek/deepseek-v4-flash \
        --price deepseek/deepseek-v4-flash=0.28,0.42

  --dry-run       load the threads and report how many calls it WOULD make; no
                  network, no spend. Run this first.
  --limit N       cap the number of threads (default: all in the directory).
  --price M=IN,OUT   $/1M tokens for model M (input,output), to turn tokens into $.
  --out FILE      also write one JSONL row per verified claim, for deeper diffing.

NOTHING is written to any database. A real run spends money: one call per
(thread, model), plus up to one schema-retry each. The default deepseek slug is
a guess — pass --models with the exact OpenRouter id.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from judge.config import capabilities  # noqa: E402
from judge.extract.client import OpenRouterClient  # noqa: E402
from judge.extract.export_source import load as load_threads  # noqa: E402
from judge.extract.runner import ExtractionRefused, extract  # noqa: E402

# Rough public $/1M-token prices (input, output). Only used for the cost line,
# and only when known — override or fill with --price. An unknown price prints
# as "—" rather than a fabricated zero.
PRICES: dict[str, tuple[float, float]] = {
    "google/gemini-2.5-flash": (0.30, 2.50),
}


def run_model(model: str, threads: list, keys: list[str], api_key: str) -> dict:
    client = OpenRouterClient(model=model, api_key=api_key)
    agg = Counter()
    per_thread: dict[str, int] = {}
    claims: list[tuple[str, object]] = []  # (thread_id, ExtractedClaim)
    t0 = time.perf_counter()
    for th in threads:
        try:
            run = extract(th, client=client, capability_keys=keys)
        except ExtractionRefused:
            agg["refused"] += 1
            per_thread[th.thread_context_id] = 0
            continue
        agg["verified"] += len(run.verified)
        agg["rejected"] += len(run.rejected)
        agg["fabricated"] += run.fabricated
        agg["encoding_mismatch"] += run.encoding_mismatches
        agg["unsalvaged"] += len(run.unsalvaged)
        agg["proposed"] += run.proposed
        agg["schema_retries"] += run.schema_retries
        agg["input_tokens"] += run.input_tokens
        agg["output_tokens"] += run.output_tokens
        agg["unclassified"] += len(run.unclassified)
        agg["proposed_capabilities"] += len(run.proposed_capabilities)
        agg["zero_threads"] += 0 if run.verified else 1
        per_thread[th.thread_context_id] = len(run.verified)
        claims.extend((th.thread_context_id, c) for c, _ in run.verified)
    return {
        "model": model,
        "seconds": time.perf_counter() - t0,
        "agg": agg,
        "per_thread": per_thread,
        "claims": claims,
    }


def _dist(claims: list[tuple[str, object]], field: str) -> Counter:
    on_ref = field in ("speaking", "specificity")

    def get(claim):
        return getattr(claim.model_ref, field) if on_ref else getattr(claim, field)
    return Counter(get(c) for _, c in claims)


def _cost(agg: Counter, price: tuple[float, float] | None) -> str:
    if not price:
        return "—"
    dollars = agg["input_tokens"] / 1e6 * price[0] + agg["output_tokens"] / 1e6 * price[1]
    return f"${dollars:.4f}"


def _pass_rate(agg: Counter) -> str:
    return f"{agg['verified'] / agg['proposed']:.1%}" if agg["proposed"] else "—"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("directory", type=Path, help="a threads export dir (e.g. _handoff/threads)")
    ap.add_argument("--models", nargs="+",
                    default=["google/gemini-2.5-flash", "deepseek/deepseek-v4-flash"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--price", action="append", default=[], metavar="M=IN,OUT")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    prices = dict(PRICES)
    for spec in args.price:
        m, io = spec.split("=", 1)
        pin, pout = io.split(",")
        prices[m] = (float(pin), float(pout))

    loaded = load_threads(args.directory)
    threads = loaded.threads[: args.limit] if args.limit else loaded.threads
    keys = list(capabilities().keys())

    print(f"threads: {len(threads)}   skipped: {len(loaded.skipped)}   models: {len(args.models)}")
    for name, reason in loaded.skipped:
        print(f"  skipped {name}: {reason}")
    if not threads:
        print("no usable threads — nothing to run.")
        return 1

    if args.dry_run:
        print(f"\nDRY RUN — would make ~{len(threads) * len(args.models)} calls "
              f"({len(threads)} threads × {len(args.models)} models), plus up to one retry each. "
              "No network, no spend.")
        return 0

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        print("\nOPENROUTER_API_KEY is unset — the paid stage refuses to start without it.")
        return 1

    results = [run_model(m, threads, keys, api_key) for m in args.models]

    # ── side-by-side headline ──────────────────────────────────────────────
    rows = [
        ("verified claims", lambda r: r["agg"]["verified"]),
        ("quote-verify pass rate", lambda r: _pass_rate(r["agg"])),
        ("fabricated (invented quotes)", lambda r: r["agg"]["fabricated"]),
        ("encoding mismatches", lambda r: r["agg"]["encoding_mismatch"]),
        ("unsalvaged (no-build)", lambda r: r["agg"]["unsalvaged"]),
        ("zero-claim threads", lambda r: r["agg"]["zero_threads"]),
        ("schema retries", lambda r: r["agg"]["schema_retries"]),
        ("refused (unsafe input)", lambda r: r["agg"]["refused"]),
        ("unclassified quotes", lambda r: r["agg"]["unclassified"]),
        ("new capabilities proposed", lambda r: r["agg"]["proposed_capabilities"]),
        ("input tokens", lambda r: r["agg"]["input_tokens"]),
        ("output tokens", lambda r: r["agg"]["output_tokens"]),
        ("est. cost", lambda r: _cost(r["agg"], prices.get(r["model"]))),
        ("wall time", lambda r: f"{r['seconds']:.1f}s"),
    ]
    w = 30
    print("\n" + "metric".ljust(w) + "".join(str(r["model"])[:24].ljust(26) for r in results))
    print("-" * (w + 26 * len(results)))
    for label, fn in rows:
        print(label.ljust(w) + "".join(str(fn(r)).ljust(26) for r in results))

    # ── classification distributions ───────────────────────────────────────
    for field in ("legacy_score_key", "speaking", "specificity", "polarity"):
        print(f"\n{field} distribution (of verified claims):")
        for r in results:
            top = ", ".join(f"{k}:{n}" for k, n in _dist(r["claims"], field).most_common(6))
            print(f"  {str(r['model'])[:34]:36} {top or '—'}")

    # ── quote-level agreement, where both models verified the same sentence ─
    if len(results) == 2:
        idx = [{} for _ in results]
        for i, r in enumerate(results):
            for tid, c in r["claims"]:
                idx[i].setdefault(tid, {})[c.quote] = c
        shared, cap_agree, spk_agree = 0, 0, 0
        for tid in set(idx[0]) & set(idx[1]):
            for q in set(idx[0][tid]) & set(idx[1][tid]):
                a, b = idx[0][tid][q], idx[1][tid][q]
                shared += 1
                cap_agree += a.legacy_score_key == b.legacy_score_key
                spk_agree += a.model_ref.speaking == b.model_ref.speaking
        print(f"\nagreement on the {shared} quote(s) BOTH models verified verbatim:")
        if shared:
            print(f"  same capability: {cap_agree}/{shared} ({cap_agree / shared:.0%})   "
                  f"same speaking-role: {spk_agree}/{shared} ({spk_agree / shared:.0%})")
        else:
            print("  none — the two models did not quote the same sentence on any thread.")

    if args.out:
        import json
        with args.out.open("w", encoding="utf-8") as f:
            for r in results:
                for tid, c in r["claims"]:
                    f.write(json.dumps({
                        "model": r["model"], "thread": tid, "capability": c.legacy_score_key,
                        "speaking": c.model_ref.speaking, "specificity": c.model_ref.specificity,
                        "polarity": c.polarity, "quote": c.quote,
                    }, ensure_ascii=False) + "\n")
        print(f"\nper-claim rows -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
