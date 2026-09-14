#!/usr/bin/env python
"""What the sieve keeps now that signal weighs rather than refuses.

READ-ONLY, OFFLINE, ZERO REQUESTS. Two populations, both already on disk:

  1,925 posts  `_unfiltered_sweep/posts.jsonl` - the r/* listing sweep of
               2026-08-18, title+selftext, the population the nightly Reddit
               sweep actually sieves. This is the number that decides whether
               Reddit is a thin source or whether we made it one.
     75 posts  `docs/measurements/reddit-sort-and-sieve.json` - the three-sort
               probe of 2026-09-11, kept 0 of 75 under the gate.

BOTH GATES ARE REPORTED, on the same documents, so the delta is a comparison
and not two runs. `signal_score` is reported beside `kept`, because the whole
claim of the demotion is that the information survives as a weight.
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from collect.adapters.queries.contract import load_queries  # noqa: E402
from collect.adapters.queries.sieve import (  # noqa: E402
    GATING_GROUPS,
    normalize,
    sieve,
)


def surfaces():
    """Every seeded model's alias variants. The listing sweep's own population."""
    d = yaml.safe_load((ROOT / "contract" / "seed_models.yaml").read_text(encoding="utf-8"))
    out = []
    for m in d.get("models") or []:
        for v in ((m.get("aliases") or {}).get("variants") or []):
            out.append(v)
    return sorted(set(out))


def main() -> int:
    entries = [e for e in load_queries().all_entries if not e.direction_from_extraction]
    surf = surfaces()
    print(f"entries {len(entries)}  surfaces {len(surf)}  (contract/seed_models.yaml)\n")

    sweep = (ROOT / "_unfiltered_sweep" / "posts.jsonl").open(encoding="utf-8")
    posts = [json.loads(line) for line in sweep]
    texts = [((p.get("title") or "") + "\n" + (p.get("selftext") or "")) for p in posts]

    kept_new = kept_old = 0
    scores = Counter()
    for text in texts:
        hay = normalize(text)
        # Subject first, exactly as sweep_reddit groups it: a surface whose
        # alias is absent cannot produce a passing verdict for any entry.
        live = [s for s in surf if normalize(s) in hay]
        if not live:
            continue
        best_new = best_old = False
        best_score = 0
        for s in live:
            for e in entries:
                v = sieve(e.terms.substitute(s), text)
                if v.passed:
                    best_new = True
                    best_score = max(best_score, v.signal_score)
                if not v.missing:          # the OLD gate: all three groups
                    best_old = True
            if best_new and best_old:
                break
        kept_new += best_new
        kept_old += best_old
        if best_new:
            scores[best_score] += 1

    n = len(texts)
    print("=== 1,925-post listing sweep ===")
    print(f"  population                         {n}")
    print(f"  kept, signal as a GATE   (before)  {kept_old:>5}  = {kept_old/n*100:6.2f}%")
    print(f"  kept, signal as a WEIGHT (after)   {kept_new:>5}  = {kept_new/n*100:6.2f}%")
    if kept_old:
        print(f"  multiple                           x{kept_new/kept_old:.1f}")
    print(f"  of those kept, signal_score > 0    {sum(v for k,v in scores.items() if k)}"
          f"  ({sum(v for k,v in scores.items() if k)/kept_new*100:.1f}%)" if kept_new else "")
    print(f"  score distribution                 {dict(sorted(scores.items()))}")

    # ── the 75-post probe, recomputed from its stored verdicts ──────────────
    probe_path = ROOT / "docs" / "measurements" / "reddit-sort-and-sieve.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    rows = [p for r in probe["runs"].values() for p in r["posts"]]
    passes = [p for p in rows if not [m for m in p["missing"] if m in GATING_GROUPS]]
    print("\n=== 75-post three-sort probe (same posts, recomputed) ===")
    print(f"  population                         {len(rows)}")
    print(f"  kept under the gate                {sum(1 for p in rows if p['passed'])}")
    print(f"  kept under the weight              {len(passes)}  = {len(passes)/len(rows)*100:.1f}%")
    print("  !! A LOWER BOUND. The stored verdict is `sieve_any`'s FURTHEST one,")
    print("    chosen by fewest-missing under the old rule; where a term set")
    print("    missing only `signal` tied with one missing `subject`, the tie")
    print("    broke on matched terms and may have stored the wrong one. It")
    print("    cannot overcount, only undercount.")
    for sort in probe["runs"]:
        rr = probe["runs"][sort]["posts"]
        pp = [p for p in rr if not [m for m in p["missing"] if m in GATING_GROUPS]]
        print(f"    {sort:<10} {len(pp):>2}/{len(rr)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
