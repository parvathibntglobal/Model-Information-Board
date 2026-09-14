#!/usr/bin/env python
"""Cluster the proposed capability keys. CODE ONLY - rule 2.

An LLM may PROPOSE a key; it may never decide that two keys are the same one.
That is a merge, and a merge is a decision. So every rule below is a string
operation somebody can read and disagree with, and the script MERGES NOTHING -
it reports what each rule would collapse, at five granularities, because the
answer depends on the rule and a single number would hide that.

WHY FIVE. "528 becomes 30" and "528 becomes 300" are different products, and
the honest finding is the RANGE plus which rule produces which end of it.
Quoting one figure would repeat the error `docs/capability-key-normalisation`
warns about.
"""
from __future__ import annotations

import ast
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SRC = ROOT / "docs" / "measurements" / "model-only-classification-withheld.jsonl"
OUT = ROOT / "docs" / "measurements" / "capability-key-clusters-2026-09-11.json"

MODEL_WORDS = re.compile(
    r"\b(claude|opus|sonnet|haiku|gpt|gemini|qwen|deepseek|mistral|llama|glm|kimi|"
    r"grok|colibri|audeta|anthropic|openai|google|fable|codex|copilot|cursor|"
    r"v\d+|\d+_\d+|\d+\.\d+|\d+b)\b", re.I)

#: Prefixes that carry no meaning - every key is about a model's behaviour.
GENERIC = {"model", "models", "model_behavior", "model_behaviour", "model_performance",
           "model_usage", "model_understanding", "model_comparison", "performance",
           "behavior", "behaviour", "capability", "capabilities", "llm", "ai"}

STOP = {"the", "of", "a", "and", "to", "for", "in", "on", "with"}


def key_name(pk):
    if not pk or str(pk).lower() in ("none", "null", ""):
        return None
    s = str(pk)
    if s.startswith("{"):
        try:
            return ast.literal_eval(s).get("name")
        except Exception:
            return None
    return s


def strip_models(key: str) -> str:
    out = MODEL_WORDS.sub("", key)
    return re.sub(r"[._]{2,}", ".", out).strip("._")


def segments(key: str) -> list[str]:
    return [s for s in re.split(r"[.]", key) if s]


def tokens(key: str) -> frozenset[str]:
    raw = re.split(r"[._\s]+", strip_models(key).lower())
    return frozenset(t for t in raw if t and t not in STOP and t not in GENERIC)


def jaccard_cluster(keys, threshold: float):
    """Single-link agglomeration on token Jaccard. Deterministic: sorted input."""
    items = [(k, tokens(k)) for k in sorted(keys)]
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i][1], items[j][1]
            if not a or not b:
                continue
            inter = len(a & b)
            if inter and inter / len(a | b) >= threshold:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj
    groups = collections.defaultdict(list)
    for idx, (k, _) in enumerate(items):
        groups[find(idx)].append(k)
    return list(groups.values())


def report(name, groups, total_keys, detail=None):
    sizes = sorted((len(g) for g in groups), reverse=True)
    singles = sum(1 for s in sizes if s == 1)
    print(f"\n  {name}")
    print(f"    clusters {len(groups):>4}   singletons {singles:>4} "
          f"({singles/len(groups)*100:4.1f}% of clusters)   largest {sizes[0] if sizes else 0}")
    if detail:
        for g in sorted(groups, key=len, reverse=True)[:detail]:
            label = collections.Counter(g).most_common(1)[0][0]
            print(f"      {len(g):>3}  {label[:62]}")
    return {"clusters": len(groups), "singletons": singles,
            "largest": sizes[0] if sizes else 0, "sizes": sizes[:25]}


def main() -> int:
    with SRC.open(encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    keys = [key_name(r.get("proposed_key")) for r in rows]
    keys = [k for k in keys if k]
    distinct = sorted(set(keys))
    print(f"population: {len(rows)} documents, {len(keys)} proposals, "
          f"{len(distinct)} distinct keys")
    print("            one prompt, one proposer model, Reddit only (rule 7)")

    out = {"proposals": len(keys), "distinct_keys": len(distinct), "rules": {}}

    out["rules"]["0_exact"] = report(
        "RULE 0  exact key match (the baseline, no rule applied)",
        [[k] * 1 for k in distinct], len(distinct))

    g1 = collections.defaultdict(list)
    for k in distinct:
        g1[strip_models(k).lower()].append(k)
    out["rules"]["1_strip_models"] = report(
        "RULE 1  lowercase + strip model/vendor/version tokens",
        list(g1.values()), len(distinct), detail=6)

    g2 = collections.defaultdict(list)
    for k in distinct:
        segs = [s for s in segments(strip_models(k).lower()) if s not in GENERIC]
        g2[segs[-1] if segs else "(empty)"].append(k)
    out["rules"]["2_final_segment"] = report(
        "RULE 2  + cluster on the FINAL segment", list(g2.values()), len(distinct), detail=10)

    g3 = collections.defaultdict(list)
    for k in distinct:
        segs = [s for s in segments(strip_models(k).lower()) if s not in GENERIC]
        g3[".".join(segs[-2:]) if segs else "(empty)"].append(k)
    out["rules"]["3_last_two_segments"] = report(
        "RULE 3  + cluster on the LAST TWO segments", list(g3.values()), len(distinct), detail=6)

    for th in (0.5, 0.34):
        gj = jaccard_cluster(distinct, th)
        out["rules"][f"4_jaccard_{th}"] = report(
            f"RULE 4  token Jaccard single-link, threshold {th}",
            gj, len(distinct), detail=8)

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
