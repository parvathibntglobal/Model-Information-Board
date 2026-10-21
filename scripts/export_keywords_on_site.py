#!/usr/bin/env python3
"""Write the keyword inventory (which keywords sit on which public page, and where)
from its workbook into `seo/keywords_on_site.json`, for Admin's Keywords dashboard.

THE WORKBOOK IS THE SOURCE: `model-board-keywords-on-site.xlsx`, built on
2026-10-19 by rendering every public tab of the site and matching each keyword
of the SEO workbook (model-board-seo-category-selection.xlsx) against the text
that is actually on it. Its sheets `Tabs` and `Keywords by tab` are copied here
as they are, with two columns left out on purpose:

  Found in SEO workbook sheet(s)                  bookkeeping, not a page fact
  Demand estimate (SEO workbook, not measured)    a guess, and the dashboard
                                                  shows measured volumes only

Search volumes are the Google Keyword Planner bands already in that workbook;
this script adds or estimates nothing.

    py scripts/export_keywords_on_site.py --xlsx "<path to model-board-keywords-on-site.xlsx>"
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import openpyxl  # noqa: E402

from judge.keywords_on_site import EXCLUDED_COLUMNS, PATH  # noqa: E402

PLACEMENTS = ["Title", "Meta description", "H1", "H2", "H3", "Link text", "Button", "Image alt",
              "Body text", "Navigation", "Footer", "Structured data"]
# workbook header -> JSON key
ROW_KEYS = {
    "Keyword": "keyword",
    "Tab": "tab",
    "URL path": "path",
    "Times in body text": "body_count",
    "Combo code": "combo",
    "Categories (master matrix)": "categories",
    "Sub-categories (master matrix)": "subcategories",
    "Slot roles": "slots",
    "Legality": "legality",
    "Target page (SEO workbook)": "target",
    "Search volume / month (Keyword Planner band)": "volume",
    "Volume band floor": "volume_floor",
    "Volume source": "volume_source",
}
TAB_KEYS = {"Tab": "tab", "URL path": "path", "Title": "title", "Meta description": "description",
            "H1": "h1", "H2 count": "h2_count", "H3 count": "h3_count", "Note": "note"}


def _rows(ws):
    it = ws.iter_rows(values_only=True)
    head = [str(h).strip() if h is not None else "" for h in next(it)]
    for r in it:
        if any(v not in (None, "") for v in r):
            yield dict(zip(head, r, strict=False))


def build(xlsx: Path) -> dict:
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    rows = []
    for r in _rows(wb["Keywords by tab"]):
        for col in EXCLUDED_COLUMNS:
            r.pop(col, None)
        out = {key: r.get(col) for col, key in ROW_KEYS.items()}
        out["placements"] = [p for p in PLACEMENTS if r.get(p) == "Yes"]
        rows.append(out)
    tabs = []
    for t in _rows(wb["Tabs"]):
        out = {key: t.get(col) for col, key in TAB_KEYS.items()}
        out["keywords"] = sum(1 for r in rows if r["path"] == out["path"])
        tabs.append(out)
    return {
        "source": xlsx.name,
        "built": "2026-10-19",
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "placements": PLACEMENTS,
        "tabs": tabs,
        "rows": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", required=True, type=Path, help="model-board-keywords-on-site.xlsx")
    ap.add_argument("--out", type=Path, default=PATH)
    args = ap.parse_args(argv)
    data = build(args.xlsx)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {args.out} - {len(data['tabs'])} pages, {len(data['rows'])} keyword placements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
