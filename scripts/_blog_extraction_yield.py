"""Per-feed yield of the blog extraction, against the historical 11 of 51.

READ-ONLY AND FREE. No model call, no write, no spend.

WHY PER FEED, AND WHY AGAINST A NAMED BASELINE

The 51 blog extractions that existed before this run were all `e5.1`, and the
prompt tripled at `e5.4` (2,697 -> 9,932 tokens of fixed overhead). So the
historical "11 of 51 produced a claim" is a figure from a different extractor
and is a BASELINE TO BEAT OR MISS, not a prediction. Both are printed side by
side rather than one being called the number.

Eighteen feeds went in. They differ in length, byline, template block and
naming rate, and a single corpus-level yield would hide that - the point of
splitting by feed is that "blogs work" and "one blog works" look identical in
a total.

RETRY RATE IS REPORTED PER FEED FOR THE SAME REASON. 15.8% was borrowed from
other sources because no blog context had ever run at e5.4; this is the first
measurement of it, so it is reported with its denominator and never as "the"
retry rate.

    python scripts/_blog_extraction_yield.py
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.parse

import psycopg
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="e5.4")
    ap.add_argument("--out", default="_blog_extraction_yield")
    args = ap.parse_args()
    out = ROOT / args.out
    out.mkdir(exist_ok=True)

    dsn = os.environ["DATABASE_URL"]
    sep = "&" if "?" in dsn else "?"
    dsn = dsn + sep + "options=" + urllib.parse.quote("-c default_transaction_read_only=on")

    with psycopg.connect(dsn, connect_timeout=15) as conn:
        rows = conn.execute(
            """
            SELECT split_part(split_part(d.url, '//', 2), '/', 1) AS host,
                   count(*)                                        AS threads,
                   count(*) FILTER (WHERE te.claims_written > 0)   AS productive,
                   coalesce(sum(te.claims_written), 0)             AS claims,
                   count(*) FILTER (WHERE te.schema_retries > 0)   AS retried,
                   coalesce(sum(te.input_tokens), 0)               AS in_tok,
                   coalesce(sum(te.output_tokens), 0)              AS out_tok
            FROM thread_extraction te
            JOIN thread_context tc ON tc.id = te.thread_context_id
            JOIN document d        ON d.id  = tc.thread_root_id
            WHERE d.source = 'blog' AND te.pipeline_version = %s
            GROUP BY 1 ORDER BY 2 DESC
            """,
            (args.version,),
        ).fetchall()

        # The baseline, named and dated rather than quoted from memory.
        base = conn.execute(
            """
            SELECT count(*), count(*) FILTER (WHERE te.claims_written > 0)
            FROM thread_extraction te
            JOIN thread_context tc ON tc.id = te.thread_context_id
            JOIN document d        ON d.id  = tc.thread_root_id
            WHERE d.source = 'blog' AND te.pipeline_version = 'e5.1'
            """
        ).fetchone()

        spend = conn.execute(
            """
            SELECT count(*), coalesce(sum(usd), 0), count(*) FILTER (WHERE unpriced)
            FROM spend_ledger WHERE stage = 'extract' AND at::date = current_date
            """
        ).fetchone()

        boards = conn.execute(
            """
            SELECT count(DISTINCT be.id) FROM board_entry be
            JOIN claim cl ON cl.id = be.claim_id
            JOIN document d ON d.id = cl.document_id
            WHERE d.source = 'blog'
            """
        ).fetchone()[0] if _has(conn, "board_entry", "claim_id") else None

        cells = conn.execute("SELECT count(*) FROM cell").fetchone()[0]

    print(f"BLOG EXTRACTION YIELD, pipeline_version={args.version}\n")
    print(f"   {'feed':<26}{'threads':>8}{'claims':>8}{'productive':>12}{'retry':>9}")
    tot = [0, 0, 0, 0]
    report = []
    for host, threads, productive, claims, retried, itok, otok in rows:
        tot[0] += threads
        tot[1] += claims
        tot[2] += productive
        tot[3] += retried
        report.append(dict(host=host, threads=threads, claims=claims,
                           productive=productive, retried=retried,
                           input_tokens=itok, output_tokens=otok))
        print(f"   {host:<26}{threads:>8}{claims:>8}"
              f"{productive:>7} ({productive/threads*100:>3.0f}%)"
              f"{retried:>5} ({retried/threads*100:>3.0f}%)")
    if tot[0]:
        print(f"   {'TOTAL':<26}{tot[0]:>8}{tot[1]:>8}"
              f"{tot[2]:>7} ({tot[2]/tot[0]*100:>3.0f}%)"
              f"{tot[3]:>5} ({tot[3]/tot[0]*100:>3.0f}%)")

    print("\nAGAINST THE BASELINE")
    print(f"   e5.1 (all blog, before today): {base[1]} of {base[0]} produced a claim"
          f"  ({base[1]/base[0]*100:.0f}%)" if base[0] else "   e5.1: none")
    if tot[0]:
        print(f"   {args.version} (this run)          : {tot[2]} of {tot[0]} "
              f"({tot[2]/tot[0]*100:.0f}%)")
        print("   ⚠ different prompt, different corpus: e5.1 was 3 hosts and mostly")
        print("     simonwillison link posts; this is 18 feeds. A baseline to compare")
        print("     against, not a prediction that was tested.")

    print("\nRETRY RATE - the borrowed figure was 15.8%, from other sources")
    if tot[0]:
        print(f"   measured here: {tot[3]} of {tot[0]} = {tot[3]/tot[0]*100:.1f}%")

    print("\nSPEND TODAY (stage=extract, as the ledger computes it - see #381)")
    print(f"   {spend[0]} calls, ${float(spend[1]):.4f}, {spend[2]} unpriced")
    print("   ⚠ the ledger prices DeepSeek at $0.14/$0.28 while the cap uses")
    print("     $0.065/$0.14; neither is validated against an invoice (#381).")

    print(f"\ncells total: {cells}" + (f"   board entries from blog claims: {boards}"
                                       if boards is not None else ""))
    (out / "yield.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\n  -> {out}/yield.json")
    return 0


def _has(conn, table: str, column: str) -> bool:
    return bool(
        conn.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = %s",
            (table, column),
        ).fetchone()
    )


if __name__ == "__main__":
    sys.exit(main())
