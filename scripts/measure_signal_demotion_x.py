#!/usr/bin/env python
"""The signal demotion on X, on the only X posts this repo has ever captured.

WHY THIS POPULATION AND WHAT IT IS NOT

X has **zero rows in `document`** - the adapter has never completed a write -
so there is no stored corpus to measure, the way there is for GitHub and blogs.
What exists is the post text captured by the two retrieval probes of
2026-09-11, run to answer a different question (does boolean OR reach the
index, and does clubbing surfaces save requests).

So the population is **the posts two probe runs happened to return for five
seeded Fable 5.1 surfaces**. It is NOT a sample of X, and no rate computed here
is an X retrieval rate. It answers exactly one question, which is the one that
matters before spending quota on pagination:

    of the X posts we have actually seen, how many would the sieve keep?

Reads two committed JSON files. No network, no database, writes one JSON.
"""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import UTC, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from collect.adapters.queries.contract import load_queries  # noqa: E402
from collect.adapters.queries.sieve import normalize, sieve  # noqa: E402

PROBES = ("x-clubbed-surfaces.json", "x-boolean-operator-probe.json")
OUT = ROOT / "docs" / "measurements" / "signal-as-weight-x-2026-09-14.json"


def surfaces() -> list[str]:
    d = yaml.safe_load((ROOT / "contract" / "seed_models.yaml").read_text(encoding="utf-8"))
    return sorted({v for m in d.get("models") or []
                   for v in ((m.get("aliases") or {}).get("variants") or [])})


def harvest(node, out: dict[str, str]) -> None:
    """Every post object in a probe file, keyed by id so reruns dedupe.

    twitter241 nests the text under `legacy` on some shapes and at the top
    level on others; both are read rather than assuming one.
    """
    if isinstance(node, dict):
        text = None
        if isinstance(node.get("legacy"), dict):
            text = node["legacy"].get("full_text") or node["legacy"].get("text")
        text = text or node.get("full_text") or node.get("text")
        pid = node.get("id") or node.get("rest_id") or node.get("id_str")
        if isinstance(text, str) and text.strip() and pid:
            out.setdefault(str(pid), text)
        for value in node.values():
            harvest(value, out)
    elif isinstance(node, list):
        for value in node:
            harvest(value, out)


def main() -> int:
    posts: dict[str, str] = {}
    for name in PROBES:
        blob = (ROOT / "docs" / "measurements" / name).read_text(encoding="utf-8")
        harvest(json.loads(blob), posts)

    surf = surfaces()
    entries = [e for e in load_queries().all_entries if not e.direction_from_extraction]

    kept_gate = kept_weight = named_a_surface = scored = 0
    for text in posts.values():
        hay = normalize(text)
        live = [s for s in surf if normalize(s) in hay]
        if not live:
            continue
        named_a_surface += 1
        new = old = False
        best = 0
        for s in live:
            for e in entries:
                verdict = sieve(e.terms.substitute(s), text)
                if verdict.passed:
                    new = True
                    best = max(best, verdict.signal_score)
                if not verdict.missing:
                    old = True
            if new and old:
                break
        kept_weight += new
        kept_gate += old
        scored += bool(new and best)

    report = {
        "ran_at": datetime.now(UTC).isoformat(),
        "population": (
            "every post captured by the two 2026-09-11 X retrieval probes; NOT a "
            "sample of X and no rate here is an X retrieval rate"
        ),
        "sources_read": list(PROBES),
        "x_rows_in_document_table": 0,
        "posts": len(posts),
        "posts_naming_a_seeded_surface": named_a_surface,
        "entries": len(entries),
        "surfaces": len(surf),
        "kept_gate": kept_gate,
        "kept_weight": kept_weight,
        "kept_with_signal_score": scored,
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"X posts captured by the two probes     : {len(posts)}")
    print(f"  naming a seeded surface              : {named_a_surface}")
    print(f"  kept by the OLD gate (signal gating) : {kept_gate}")
    print(f"  kept by the NEW gate (signal a weight): {kept_weight}")
    print(f"  of those, signal_score >= 1          : {scored}")
    print(f"\nwritten: {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
