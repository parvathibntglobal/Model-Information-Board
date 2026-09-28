"""Does extraction split a comparison post into per-model claims, or produce nothing?

Issue #375. READ-ONLY AND FREE: no model call, no write, no spend. The question
looks like it needs an experiment and does not - the corpus already ran it, by
accident, and this counts the result.

TWO TABLES, AND THE DIFFERENCE BETWEEN THEM IS THE WHOLE METHOD

    table 1   documents that HAVE claims, banded by how many models the text
              names -> how many distinct models their claims cover.
              Answers "does it SPLIT".

    table 2   every thread that REACHED THE EXTRACTOR, whether it wrote
              anything or not -> what fraction wrote >= 1 claim.
              Answers "does it produce NOTHING".

Table 1 alone cannot answer the second question and it is the tempting one to
stop at. A comparison post that produced zero claims has no row in `claim`, so
joining through `claim` makes the failure mode invisible BY CONSTRUCTION - the
population would be selected on the outcome. `thread_extraction` is the
non-survivorship population: it has a row per extraction attempt, with
`claims_written` including zero. 501 of 791 wrote zero.

THREE LIMITS, PRINTED WITH THE RESULT RATHER THAN LEFT TO A READER

  - flattened texts missing from THIS machine's raw store are counted and
    named, never silently dropped. Their missingness is not known to be
    independent of breadth (rule 6).
  - the population is POST-SIEVE. Every thread here was chosen by the sieve,
    which is upstream of the extractor - rule 8's upstream clause. This is not
    an estimate of what would happen to an unseated feed.
  - the blog slice is reported separately because it is thin (52 threads, 3
    hosts) and the cross-platform tables are dominated by dev.to and Reddit,
    while every candidate this decides is a blog.

Cost comes from `spend_ledger`, which is BILLED ROWS, not the n=3 estimate in
`docs/measurements/extraction-token-counts.md`. Unpriced calls are counted
separately and never treated as free (rule 6).

    python scripts/_comparison_post_extraction.py
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import statistics
import sys
import urllib.parse

import psycopg
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from collect.config import settings  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.surface_resolver import (  # noqa: E402
    RegistrySurfaceFinder,
    RegistrySurfaceResolver,
)


def band_of(n: int) -> str:
    if n <= 1:
        return "0-1"
    if n <= 4:
        return "2-4"
    if n <= 9:
        return "5-9"
    return "10+"


BANDS = ["0-1", "2-4", "5-9", "10+"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="_comparison_post_extraction")
    args = ap.parse_args()
    out = ROOT / args.out
    out.mkdir(exist_ok=True)

    # READ-ONLY. Enforced in Postgres rather than promised in a comment.
    dsn = os.environ["DATABASE_URL"]
    sep = "&" if "?" in dsn else "?"
    dsn = dsn + sep + "options=" + urllib.parse.quote("-c default_transaction_read_only=on")
    store = RawStore(pathlib.Path(settings().raw_store_path))
    report: dict = {}

    with psycopg.connect(dsn, connect_timeout=15) as conn:
        finder = RegistrySurfaceFinder.from_connection(conn)
        resolver = RegistrySurfaceResolver.from_connection(conn)
        canonical = dict(conn.execute("SELECT id, canonical_id FROM model_version").fetchall())
        report["registry_model_versions"] = len(canonical)

        def models_in(ref) -> int | None:
            """Distinct canonical models named in the text, or None if unreadable."""
            try:
                text = store.get_text(ref)
            except Exception:                                   # noqa: BLE001
                return None
            if not text:
                return None
            ids = {resolver(s) for s in finder(text)}
            ids.discard(None)
            return len({canonical.get(i, i) for i in ids})

        # ── TABLE 1: does it SPLIT ──────────────────────────────────────────
        rows = conn.execute("""
            SELECT d.text_ref, COUNT(*) n_claims,
                   COUNT(DISTINCT cl.model_version_id) n_claim_models
            FROM claim cl JOIN document d ON d.id = cl.document_id
            GROUP BY 1
        """).fetchall()
        split = {b: {"docs": 0, "sum_claim_models": 0, "docs_2plus": 0} for b in BANDS}
        unreadable_t1 = 0
        for ref, _n, nm in rows:
            k = models_in(ref)
            if k is None:
                unreadable_t1 += 1
                continue
            b = split[band_of(k)]
            b["docs"] += 1
            b["sum_claim_models"] += nm
            b["docs_2plus"] += 1 if nm >= 2 else 0
        report["table1"] = {"bands": split, "documents_with_claims": len(rows),
                            "unreadable": unreadable_t1}

        print("\nTABLE 1 - documents WITH claims (survivorship: cannot see a zero)")
        print(f"  {len(rows)} documents, {unreadable_t1} unreadable on this machine\n")
        print(f"  {'models named':<14}{'docs':>6}{'mean distinct claim models':>29}"
              f"{'docs w/ 2+':>13}")
        for b in BANDS:
            v = split[b]
            if v["docs"]:
                print(f"  {b:<14}{v['docs']:>6}"
                      f"{v['sum_claim_models'] / v['docs']:>29.2f}"
                      f"{v['docs_2plus']:>9} ({v['docs_2plus'] / v['docs'] * 100:.0f}%)")

        # ── TABLE 2: does it produce NOTHING ────────────────────────────────
        # ⚠ THE POPULATION IS `thread_extraction`, NOT `claim`. A row exists per
        #   ATTEMPT, so a comparison post that produced nothing is visible here
        #   and nowhere else.
        rows = conn.execute("""
            SELECT te.claims_written, tc.flattened_text_ref, d.source
            FROM thread_extraction te
            JOIN thread_context tc ON tc.id = te.thread_context_id
            JOIN document d ON d.id = tc.thread_root_id
        """).fetchall()
        grid = collections.Counter()
        unreadable_t2 = 0
        for cw, ref, _src in rows:
            k = models_in(ref)
            if k is None:
                unreadable_t2 += 1
                continue
            grid[(band_of(k), cw > 0)] += 1
        zero_total = conn.execute(
            "SELECT count(*) FROM thread_extraction WHERE claims_written = 0"
        ).fetchone()[0]
        report["table2"] = {
            "attempts": len(rows), "unreadable": unreadable_t2,
            "wrote_zero_overall": zero_total,
            "bands": {b: {"productive": grid[(b, True)], "zero": grid[(b, False)]}
                      for b in BANDS},
        }

        print("\nTABLE 2 - every thread that REACHED the extractor")
        print(f"  {len(rows)} attempts, {unreadable_t2} unreadable, "
              f"{zero_total} wrote zero claims overall\n")
        print(f"  {'models named':<14}{'wrote >=1':>11}{'wrote 0':>9}"
              f"{'total':>7}{'productive':>12}")
        for b in BANDS:
            y, n = grid[(b, True)], grid[(b, False)]
            if y + n:
                print(f"  {b:<14}{y:>11}{n:>9}{y + n:>7}{y / (y + n) * 100:>11.0f}%")

        # ── the blog slice, separately, because it is what this decides ─────
        blog = conn.execute("""
            SELECT te.claims_written, tc.flattened_text_ref, d.url
            FROM thread_extraction te
            JOIN thread_context tc ON tc.id = te.thread_context_id
            JOIN document d ON d.id = tc.thread_root_id
            WHERE d.source = 'blog'
        """).fetchall()
        blog_rows = []
        for cw, ref, url in blog:
            k = models_in(ref)
            blog_rows.append({"url": url, "models_named": k, "claims_written": cw})
        report["blog_slice"] = blog_rows
        hosts = conn.execute("""
            SELECT split_part(split_part(url,'//',2),'/',1) h, count(*)
            FROM document WHERE source='blog' GROUP BY 1 ORDER BY 2 DESC
        """).fetchall()
        report["blog_documents_by_host"] = dict(hosts)
        # ⚠ TWO DIFFERENT HOST COUNTS AND THEY MUST NOT BE SWAPPED. Hosts with
        #   blog DOCUMENTS is 9; hosts whose threads ever reached the EXTRACTOR
        #   is 3. Printing the first beside "threads ever extracted" is a real
        #   value answering a question it was not asked - rule 7 - and it reads
        #   as three times the coverage that exists.
        extracted_hosts = {
            (urllib.parse.urlparse(r["url"]).hostname or "") for r in blog_rows
        }
        report["blog_hosts_with_documents"] = len(hosts)
        report["blog_hosts_ever_extracted"] = sorted(extracted_hosts)
        print(f"\nBLOG SLICE - {len(blog)} threads ever extracted, from "
              f"{len(extracted_hosts)} host(s): {', '.join(sorted(extracted_hosts))}"
              f"   ({len(hosts)} hosts have blog documents)")
        for r in sorted(blog_rows, key=lambda r: -(r["models_named"] or 0))[:6]:
            print(f"    names {str(r['models_named']):>4} models -> "
                  f"{r['claims_written']:>2} claims  {r['url'][:66]}")

        # ── cost, from BILLED ROWS ──────────────────────────────────────────
        # Not `docs/measurements/extraction-token-counts.md`'s $0.00208: that is
        # n=3 calls on ONE thread and the document says so itself.
        spend = conn.execute("""
            SELECT model, count(*), count(*) FILTER (WHERE unpriced), sum(usd)
            FROM spend_ledger WHERE stage='extract' GROUP BY 1 ORDER BY 2 DESC
        """).fetchall()
        report["spend_by_model"] = [
            {"model": m, "calls": c, "unpriced": u, "usd": float(s or 0)}
            for m, c, u, s in spend
        ]
        print("\nCOST - `spend_ledger`, stage=extract (billed rows, not an estimate)")
        for m, c, u, s in spend:
            print(f"    {m:<28}{c:>6} calls  {u:>3} unpriced  ${float(s or 0):.4f}")
        for model, _c, _u, _s in spend[:1]:
            vals = sorted(float(r[0]) for r in conn.execute(
                "SELECT usd FROM spend_ledger WHERE stage='extract' "
                "AND model=%s AND NOT unpriced", (model,)).fetchall())
            if vals:
                p90 = vals[int(0.9 * len(vals))]
                report["cost_per_call"] = {
                    "model": model, "n": len(vals),
                    "mean": statistics.mean(vals), "median": statistics.median(vals),
                    "p90": p90, "max": vals[-1],
                }
                print(f"    {model}: n={len(vals)} priced   "
                      f"mean ${statistics.mean(vals):.5f}  "
                      f"median ${statistics.median(vals):.5f}  p90 ${p90:.5f}")
                for n in (20, 30):
                    print(f"      {n} posts -> ${statistics.mean(vals) * n:.3f} mean, "
                          f"${p90 * n:.3f} at p90")

    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\n  -> {out}/report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
