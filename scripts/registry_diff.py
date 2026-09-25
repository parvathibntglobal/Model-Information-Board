#!/usr/bin/env python
"""What the next registry poll will change: arrivals, departures, expiration dates.

READ-ONLY. Fetches OpenRouter's public catalogue (no key) and reads the
registry, then prints a markdown report. The scheduled workflow posts it as an
issue comment BEFORE the poll writes, so a person sees what arrived.

    python scripts/registry_diff.py [--out report.md]

WHY A DIFF AGAINST THE REGISTRY AND NOT AGAINST THE LAST POLL: the poll upserts
and never deletes, so `model_version` is the union of every poll there has
been. Catalogue minus registry is what is new; registry minus catalogue is what
the catalogue stopped listing. No snapshot table is needed.

WHAT IT CANNOT SAY: an announced retirement the catalogue does not carry.
GPT-4.1's API retires in October 2026 and its `expiration_date` is null. That
still needs a person, and the report says so every time rather than implying
the list of expirations is complete.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

#: The catalogue's "never expires" value. Real on the wire, meaningless as a date,
#: so it is listed apart rather than mixed into announced retirements. One
#: definition, the parser's: the poll now stores it as NULL (#460).
from collect.registry.openrouter import NEVER_EXPIRES  # noqa: E402

SENTINEL = NEVER_EXPIRES.isoformat()


def _filtered_out(model_id: str) -> bool:
    """`:batch`-style service tiers fold into their base id; `-pro` is dropped.

    `-pro` is dropped because it is asked for, and it is a real loss: some -pro
    ids are distinct models (openai/gpt-6-astra-pro). They are counted, not hidden.
    """
    return model_id.endswith("-pro")


def compute_diff(catalogue: list[dict], registry: dict[str, dict], tombstoned: frozenset[str],
                 base_id) -> dict:
    """Pure: catalogue entries, registry rows keyed by canonical_id, tombstones."""
    by_base: dict[str, dict] = {}
    for m in catalogue:
        if m.get("alias_target"):   # a ~...-latest pointer, not a model; the poll skips it too
            continue
        by_base.setdefault(base_id(m["id"]), m)
    pro_dropped = sorted(b for b in by_base if _filtered_out(b) and b not in registry)
    arrivals = sorted(
        (b for b in by_base
         if b not in registry and b not in tombstoned and not _filtered_out(b)),
        key=lambda b: -(by_base[b].get("created") or 0),
    )
    departures = sorted(cid for cid, row in registry.items()
                        if row.get("provenance") == "polled" and cid not in by_base)
    expiring, sentinel = [], []
    for b, m in by_base.items():
        exp = m.get("expiration_date")
        if not exp or b not in registry:
            continue
        current = registry[b].get("retirement_date")
        if str(current or "") == str(exp):
            continue
        (sentinel if exp == SENTINEL else expiring).append((b, exp, current))
    return {"arrivals": [(b, by_base[b]) for b in arrivals], "departures": departures,
            "expiring": sorted(expiring), "sentinel": sorted(sentinel),
            "pro_dropped": pro_dropped, "tombstoned_in_catalogue":
                sorted(b for b in by_base if b in tombstoned)}


def render(d: dict, *, catalogue_size: int, registry_size: int) -> str:
    def day(m):
        c = m.get("created")
        return date.fromtimestamp(c).isoformat() if c else "no date"

    out = [f"**Registry diff, before this poll writes.** Catalogue {catalogue_size} entries; "
           f"registry {registry_size} models.", ""]
    out.append(f"### Arrivals: {len(d['arrivals'])}")
    out.append("The poll inserts these. **Seating stays manual**: `seat()`, with its collision "
               "check, gives a model the aliases it needs to be searched.")
    out += [f"- `{b}` - {m.get('name') or ''} (created {day(m)})" for b, m in d["arrivals"][:60]]
    if len(d["arrivals"]) > 60:
        out.append(f"- ... and {len(d['arrivals']) - 60} more")
    out.append(f"\n{len(d['pro_dropped'])} `-pro` id(s) filtered out as asked, not hidden: "
               + (", ".join(f"`{x}`" for x in d["pro_dropped"][:20]) or "none"))
    out.append(f"{len(d['tombstoned_in_catalogue'])} tombstoned id(s) still in the catalogue, "
               "which the poll skips.")
    out.append(f"\n### Departures: {len(d['departures'])}")
    out.append("Polled models the catalogue no longer lists. **Nothing is deleted automatically.**")
    out += [f"- `{x}`" for x in d["departures"]]
    out.append(f"\n### Expiration dates, new or changed: {len(d['expiring'])}")
    out += [f"- `{b}`: {exp} (registry had {cur or 'none'})" for b, exp, cur in d["expiring"]]
    out.append(f"\n{len(d['sentinel'])} use the `{SENTINEL}` \"never expires\" sentinel; "
               "not listed.")
    out.append("\n**Not in this list, by construction:** retirements announced by a vendor but "
               "absent from the catalogue (GPT-4.1's October retirement has `expiration_date` "
               "null). Those still need a person.")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args()

    import psycopg

    from collect.http import build_client
    from collect.registry.openrouter import MODELS_URL, base_id, fetch_models
    from collect.registry.tombstones import load_tombstones

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is not set; refusing rather than diffing against nothing")
    sep = "&" if "?" in dsn else "?"
    dsn += sep + "options=-c%20default_transaction_read_only%3Don"
    with build_client() as client:
        catalogue = fetch_models(client, url=MODELS_URL).json()["data"]
    with psycopg.connect(dsn, connect_timeout=20) as conn:
        registry = {r[0]: {"provenance": r[1], "retirement_date": r[2]} for r in conn.execute(
            "SELECT canonical_id, provenance, retirement_date FROM model_version").fetchall()}
    d = compute_diff(catalogue, registry, load_tombstones(), base_id)
    report = render(d, catalogue_size=len(catalogue), registry_size=len(registry))
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
