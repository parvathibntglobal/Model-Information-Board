#!/usr/bin/env python
"""Load LiteLLM's community price list into `unit_price`, as a fallback.

    python scripts/load_litellm_prices.py --dry-run
    python scripts/load_litellm_prices.py --apply
    python scripts/load_litellm_prices.py --dry-run --file <local copy of the JSON>

#602 items 3 and 4; `contract/litellm_prices.yaml` holds every decision and
`collect/registry/litellm.py` applies it. This script only reads which models
OpenRouter leaves unpriced, fetches the file (free: a public GitHub file, no
metered API), and writes.

APPEND-ONLY. Each `--apply` adds one snapshot stamped with this run's time; the
Models pages read the newest. Nothing is updated or deleted.

It writes to whatever DATABASE_URL names, through the same write guard as
`scripts/load_unpolled_models.py`. A shared-database write is announced before
it runs.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from datetime import UTC, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
    if m:
        os.environ.setdefault(m.group(1), m.group(2))

import psycopg  # noqa: E402

from collect.registry.litellm import load_contract, rows_from  # noqa: E402
from judge.catalog import _price_state  # noqa: E402

LATEST = (
    "SELECT canonical_id, price_in, price_out, pricing FROM model_catalog "
    "WHERE last_seen_at = (SELECT max(last_seen_at) FROM model_catalog)"
)
INSERT = (
    "INSERT INTO unit_price (canonical_id, unit, direction, variant, usd, source, "
    "source_key, source_url, retrieved_at) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
)


def _fetch(url: str) -> dict:
    import httpx

    response = httpx.get(url, timeout=60, follow_redirects=True)
    response.raise_for_status()
    return response.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    ap.add_argument("--file", default=None, help="read a local copy instead of fetching")
    args = ap.parse_args()

    contract = load_contract()
    prices = (json.loads(pathlib.Path(args.file).read_text(encoding="utf-8"))
              if args.file else _fetch(contract.source_url))
    retrieved_at = datetime.now(UTC)

    from judge.writeguard import check as writeguard_check
    writeguard_check(os.environ.get("DATABASE_URL"), command="load_litellm_prices.py")

    conn = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=15)
    state = {cid: _price_state(cid, p_in, p_out, pricing)
             for cid, p_in, p_out, pricing in conn.execute(LATEST).fetchall()}
    if not state:
        print("model_catalog is empty: run `python -m collect.cli registry poll-catalog` first.")
        conn.close()
        return 1
    report = rows_from(
        prices, contract,
        unpriced={k for k, v in state.items() if v == "not_published"},
        priced={k for k, v in state.items() if v != "not_published"},
        retrieved_at=retrieved_at,
    )
    print(report.summary())

    before = conn.execute("SELECT count(*) FROM unit_price").fetchone()[0]
    for r in report.rows:
        conn.execute(INSERT, (r.canonical_id, r.unit, r.direction, r.variant, r.usd,
                              r.source, r.source_key, r.source_url, r.retrieved_at))
    # READ BACK INSIDE THE TRANSACTION before deciding to keep it.
    landed = conn.execute(
        "SELECT count(*) FROM unit_price WHERE retrieved_at = %s", (retrieved_at,),
    ).fetchone()[0]
    after = conn.execute("SELECT count(*) FROM unit_price").fetchone()[0]
    print(f"\n  unit_price {before} -> {after}; this snapshot {landed} row(s)")

    failures = []
    if landed != len(report.rows):
        failures.append(f"{len(report.rows)} row(s) meant, {landed} landed")
    if after - before != len(report.rows):
        failures.append(f"unit_price moved by {after - before}, expected {len(report.rows)}")

    if args.dry_run:
        conn.rollback()
        conn.close()
        print("\n--dry-run: rolled back, nothing written.")
        return 0
    if failures:
        conn.rollback()
        conn.close()
        print("\nROLLED BACK: " + "; ".join(failures))
        return 1
    conn.commit()
    conn.close()
    print("\nCOMMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
