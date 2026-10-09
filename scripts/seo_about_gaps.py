#!/usr/bin/env python3
"""Which INDEXABLE job and capability pages have no hand-written "about" text.

SEO item 4 (2026-10-09). A page's unique text is its `about` entry
(contract/job_about.yaml, contract/capability_about.yaml) - hand-written by a
person, on purpose, never generated. Where a page has none, it shows only the
extractor's definition, and every such page reads like its neighbours. This
lists the gaps that matter for search first: the pages `judge/seo.py` would let
a search engine index (contract/indexing.yaml).

Read-only. Prints names and slugs only - no quotes, no sources.

    py scripts/seo_about_gaps.py            # needs DATABASE_URL
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import psycopg  # noqa: E402

from judge import seo  # noqa: E402
from judge.config import capability_about, job_about  # noqa: E402

#: URL segment -> (contract file, its reader).
ABOUT = {"jobs": ("contract/job_about.yaml", job_about),
         "capabilities": ("contract/capability_about.yaml", capability_about)}


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is not set. Nothing was read.")
    # READ-ONLY at the database, not just by intent: the server refuses a write
    # on this session (tests/test_every_write_path_takes_the_gate.py READ_ONLY).
    with psycopg.connect(dsn, connect_timeout=10,
                         options="-c default_transaction_read_only=on") as conn:
        result = seo.indexable_pages(conn)
    sections = [p for p in result["paths"] if p["kind"] == "section"]
    for seg, (path, read) in ABOUT.items():
        about = read()
        pages = [p for p in sections if p["path"].startswith(f"/board/{seg}/")]
        missing = sorted((p for p in pages if p["path"].rsplit("/", 1)[1] not in about),
                         key=lambda p: -p["voices"])
        print(f"\n{seg}: {len(pages)} indexable, {len(missing)} with no entry in {path}")
        for p in missing:
            print(f"  {p['voices']:>3} voices  {p['path'].rsplit('/', 1)[1]}")
    print("\nMetric pages have no about file; their unique text is the axis definition and unit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
