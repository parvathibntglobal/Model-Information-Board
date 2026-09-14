#!/usr/bin/env python
"""The signal demotion on GitHub and blogs. `sieve()` is shared; Reddit was not the change.

Every figure in `docs/measurements/signal-as-weight-2026-09-11.md` is Reddit-only
and that document says so. This closes it on the other two platforms that carry
a real corpus, on the stored documents themselves rather than on an inference
from two rates measured over different populations.

Reads staging READ-ONLY, resolves text from the local raw store, writes nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import statistics as st
import sys
import urllib.parse
from datetime import UTC, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
    if m:
        os.environ.setdefault(m.group(1), m.group(2))

import psycopg  # noqa: E402
import yaml  # noqa: E402

from collect.adapters.queries.contract import load_queries  # noqa: E402
from collect.adapters.queries.sieve import normalize, sieve  # noqa: E402
from collect.config import settings  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.rawstore_reader import RawStoreReader  # noqa: E402

OUT = ROOT / "docs" / "measurements" / "signal-as-weight-platforms-2026-09-11.json"
PIN, POUT = 0.30, 2.50          # contract/seed_models.yaml, per 1M tokens


def cost(chars: int) -> float:
    """Measured regression, n=195 (comments-shapes-and-the-legacy-weights.md §4)."""
    return (2683 + 0.6016 * chars) / 1e6 * PIN + 636 / 1e6 * POUT


def surfaces():
    d = yaml.safe_load((ROOT / "contract" / "seed_models.yaml").read_text(encoding="utf-8"))
    return sorted({v for m in d.get("models") or []
                   for v in ((m.get("aliases") or {}).get("variants") or [])})


def text_of(payload: dict) -> str:
    """One reader for three envelopes. An unknown shape yields '' and is counted."""
    for a, b in (("title", "selftext"), ("title", "body"), ("title", "text")):
        if a in payload or b in payload:
            return (payload.get(a) or "") + "\n\n" + (payload.get(b) or "")
    return payload.get("body") or payload.get("text") or ""


def read_only_dsn() -> str:
    dsn = os.environ["DATABASE_URL"]
    sep = "&" if "?" in dsn else "?"
    return f"{dsn}{sep}options={urllib.parse.quote('-c default_transaction_read_only=on')}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="github,blog")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    entries = [e for e in load_queries().all_entries if not e.direction_from_extraction]
    surf = surfaces()
    reader = RawStoreReader(RawStore(settings().raw_store_path))
    report = {"ran_at": datetime.now(UTC).isoformat(),
              "entries": len(entries), "surfaces": len(surf),
              "cost_model": ("input=2683+0.6016*chars, output=636, "
                             "$0.30/$2.50 per 1M (seeded price)"),
              "sources": {}}

    with psycopg.connect(read_only_dsn(), connect_timeout=10) as conn:
        for source in args.sources.split(","):
            cur = conn.cursor()
            q = ("SELECT id, text_ref FROM document WHERE source=%s "
                 "AND text_ref IS NOT NULL ORDER BY id")
            if args.limit:
                q += f" LIMIT {int(args.limit)}"
            cur.execute(q, (source,))
            rows = cur.fetchall()

            unresolved = empty = 0
            new_chars, old_chars = [], []
            scored = 0
            for _did, ref in rows:
                o = reader.resolve(ref)
                if o is None or not o.found:
                    unresolved += 1
                    continue
                raw = o.require()
                try:
                    text = text_of(json.loads(raw))
                except ValueError:
                    text = raw if isinstance(raw, str) else raw.decode("utf-8", "replace")
                if not text.strip():
                    empty += 1
                    continue
                hay = normalize(text)
                live = [s for s in surf if normalize(s) in hay]
                if not live:
                    continue
                new = old = False
                best = 0
                for s in live:
                    for e in entries:
                        v = sieve(e.terms.substitute(s), text)
                        if v.passed:
                            new = True
                            best = max(best, v.signal_score)
                        if not v.missing:
                            old = True
                    if new and old:
                        break
                if new:
                    new_chars.append(len(text))
                    scored += bool(best)
                if old:
                    old_chars.append(len(text))

            n = len(rows)
            c_old, c_new = sum(map(cost, old_chars)), sum(map(cost, new_chars))
            report["sources"][source] = {
                "documents": n, "unresolved": unresolved, "empty_text": empty,
                "kept_gate": len(old_chars), "kept_weight": len(new_chars),
                "rate_gate": round(len(old_chars) / n * 100, 3) if n else None,
                "rate_weight": round(len(new_chars) / n * 100, 3) if n else None,
                "multiple": round(len(new_chars) / len(old_chars), 2) if old_chars else None,
                "kept_with_signal": scored,
                "median_chars_kept": int(st.median(new_chars)) if new_chars else None,
                "cost_gate_usd": round(c_old, 4), "cost_weight_usd": round(c_new, 4),
                "cost_delta_usd": round(c_new - c_old, 4),
            }
            r = report["sources"][source]
            print(f"\n=== {source} ===")
            print(f"  documents                {n}  (unresolved {unresolved}, empty {empty})")
            print(f"  kept, signal as GATE     {r['kept_gate']:>6}  = {r['rate_gate']}%")
            print(f"  kept, signal as WEIGHT   {r['kept_weight']:>6}  = {r['rate_weight']}%")
            print(f"  multiple                 x{r['multiple']}")
            print(f"  of those, signal_score>0 {r['kept_with_signal']}")
            print(f"  extraction cost  gate ${r['cost_gate_usd']}  weight ${r['cost_weight_usd']}"
                  f"  delta +${r['cost_delta_usd']}")

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
