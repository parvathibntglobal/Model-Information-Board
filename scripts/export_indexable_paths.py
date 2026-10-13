#!/usr/bin/env python3
"""Write the pages worth indexing to a JSON file, for the sitemap (SEO item 8).

`web/vite.config.js` reads this file (named by `SEO_PATHS_FILE`) when the site
is OPEN (`SITE_URL` set and `PUBLIC_SITE=1`) and lists every path in
sitemap.xml. The paths come from `judge/seo.py` - the same function that
decides each page's `noindex` - so the sitemap and the pages cannot disagree.

A SNAPSHOT. Indexability changes as evidence arrives, so the file records
when it was made, and a deploy should run this just before `vite build`.

Read-only at the database. Writes a FILE: site paths only, no quotes, no
sources. It is a build input, not something to commit.

    py scripts/export_indexable_paths.py --out <file>     # needs DATABASE_URL
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import psycopg  # noqa: E402

from judge import seo  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="where to write the JSON")
    args = ap.parse_args(argv)
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is not set. Nothing was read or written.")
    # READ-ONLY at the database (tests/test_every_write_path_takes_the_gate.py READ_ONLY).
    with psycopg.connect(dsn, connect_timeout=10,
                         options="-c default_transaction_read_only=on") as conn:
        result = seo.indexable_pages(conn)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "rule": "contract/indexing.yaml",
        "paths": [p["path"] for p in result["paths"]],
        # LASTMOD PER PATH, only where a real date exists (sitemap <lastmod>).
        "lastmod": {p["path"]: p["lastmod"] for p in result["paths"] if p.get("lastmod")},
        "tallies": result["tallies"],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    t = result["tallies"]
    print(f"wrote {len(payload['paths'])} paths to {out}")
    for kind, n in t.items():
        print(f"  {kind:<17} {n['indexable']:>5} indexable of {n['pages']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
