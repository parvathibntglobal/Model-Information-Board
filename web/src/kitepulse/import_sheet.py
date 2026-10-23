"""Import the Kite Pulse keyword sheet into the admin's Kite Pulse section.

    py -3.12 web/src/kitepulse/import_sheet.py
    py -3.12 web/src/kitepulse/import_sheet.py --sheet "path/to/another copy.xlsx"

Reads the five data tabs of the sheet (Keywords, Page Map, AEO Tracking,
Competitors, Keywords to Avoid) and writes them to `data/sheet.json` beside
this file, which `site.js` loads for the admin panel and the site preview.

The sheet stays the place people edit. Re-run this after every change to it;
the JSON records the sheet's sha256 and the import date, so the admin can say
which copy of the sheet it is showing.

An empty cell is written as null, never as 0 or "": Monthly Volume and KD are
empty on rows nobody has researched yet, and a 0 there would read as "nobody
searches for this" (rule 6).

Stdlib only - an .xlsx is a zip of XML, and openpyxl is not a dependency here.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # web/src/kitepulse -> the repository
DEFAULT_SHEET = HERE / "docs" / "Kite Pulse - Keyword Research.xlsx"
OUT = HERE / "data" / "sheet.json"

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# Header text in the sheet -> field name in the JSON. A tab whose header row is
# missing one of these fails loudly rather than importing a column of nulls
# (rule 12): a renamed header is the sheet changing shape, and the panel would
# otherwise show an empty column that looks like missing research.
TABS = {
    "Keywords": {
        "ID": "id",
        "Keyword / Question": "keyword",
        "Type": "type",
        "Keyword Group": "group",
        "Monthly Volume": "volume",
        "Difficulty (KD)": "kd",
        "Trend": "trend",
        "Search Intent": "intent",
        "Relevance (1-3)": "relevance",
        "Priority": "priority",
        "Main / Secondary": "role",
        "Target Page URL": "url",
        "Page Type": "page_type",
        "Currently Ranking (Google)": "ranking",
        "AI Cites": "ai_cites",
        "Content Gap / Angle": "gap",
        "Status": "status",
        "Notes": "notes",
    },
    "Page Map": {
        "Page URL": "url",
        "Page Type": "type",
        "Main Keyword": "main",
        "Priority (P1/P2/P3)": "priority",
        "Status": "status",
        "Publish Date": "published",
        "Notes": "notes",
    },
    "AEO Tracking": {
        "Question": "question",
        "Target Page": "page",
        "ChatGPT": "chatgpt",
        "Perplexity": "perplexity",
        "Claude": "claude",
        "Gemini": "gemini",
        "Google AI Overview": "google_ai",
        "Competitors Cited": "competitors_cited",
        "Test Date": "tested",
    },
    "Competitors": {
        "Competitor": "name",
        "Website": "site",
        "Main Keywords They Rank For": "ranks_for",
        "What They Do Well": "strengths",
        "What They Miss": "gaps",
        "Our Compare Page": "compare_page",
    },
    "Keywords to Avoid": {
        "Keyword": "keyword",
        "Why Avoid": "why",
    },
}


def _col(ref: str) -> str:
    return "".join(ch for ch in ref if ch.isalpha())


def read_tabs(path: Path) -> dict[str, list[list[str | None]]]:
    """Every tab as a list of rows; each row a list of cell strings or None."""
    with zipfile.ZipFile(path) as z:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(NS + "si"):
                shared.append("".join(t.text or "" for t in si.iter(NS + "t")))

        rels = {
            r.get("Id"): r.get("Target")
            for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        }
        book = ET.fromstring(z.read("xl/workbook.xml"))
        tabs: dict[str, list[list[str | None]]] = {}
        for sheet in book.find(NS + "sheets"):
            target = rels[sheet.get(REL + "id")].lstrip("/")
            target = target if target.startswith("xl/") else "xl/" + target
            parsed: list[dict[str, str | None]] = []
            cols: set[str] = set()
            for row in ET.fromstring(z.read(target)).iter(NS + "row"):
                cells: dict[str, str | None] = {}
                for c in row.findall(NS + "c"):
                    kind, v = c.get("t"), c.find(NS + "v")
                    if kind == "s":
                        val = shared[int(v.text)]
                    elif kind == "inlineStr":
                        val = "".join(t.text or "" for t in c.iter(NS + "t"))
                    else:
                        val = v.text if v is not None else None
                    col = _col(c.get("r"))
                    cells[col] = val.strip() if isinstance(val, str) and val.strip() else None
                    cols.add(col)
                parsed.append(cells)
            order = sorted(cols, key=lambda s: (len(s), s))
            tabs[sheet.get("name")] = [[cells.get(k) for k in order] for cells in parsed]
    return tabs


def records(rows: list[list[str | None]], fields: dict[str, str], tab: str) -> list[dict]:
    header = [h or "" for h in rows[0]]
    missing = [h for h in fields if h not in header]
    if missing:
        sys.exit(f"{tab}: header row has no column named {missing}. Found: {header}")
    idx = {fields[h]: header.index(h) for h in fields}
    out = []
    for row in rows[1:]:
        rec = {name: (row[i] if i < len(row) else None) for name, i in idx.items()}
        if any(v is not None for v in rec.values()):
            out.append(rec)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sheet", type=Path, default=DEFAULT_SHEET)
    args = ap.parse_args()
    sheet = args.sheet.resolve()

    tabs = read_tabs(sheet)
    absent = [t for t in TABS if t not in tabs]
    if absent:
        sys.exit(f"{sheet.name}: no tab named {absent}. Found: {list(tabs)}")

    shown = sheet.relative_to(ROOT).as_posix() if sheet.is_relative_to(ROOT) else sheet.name
    data = {
        "source": {
            "file": shown,
            "sha256": hashlib.sha256(sheet.read_bytes()).hexdigest(),
            "imported_on": dt.date.today().isoformat(),
        },
        "keywords": records(tabs["Keywords"], TABS["Keywords"], "Keywords"),
        "pages": [p for p in records(tabs["Page Map"], TABS["Page Map"], "Page Map")
                  if (p["url"] or "").startswith("/")],
        "aeo": records(tabs["AEO Tracking"], TABS["AEO Tracking"], "AEO Tracking"),
        "competitors": records(tabs["Competitors"], TABS["Competitors"], "Competitors"),
        "avoid": records(tabs["Keywords to Avoid"], TABS["Keywords to Avoid"], "Keywords to Avoid"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()}: {len(data['keywords'])} keywords, "
          f"{len(data['pages'])} pages, {len(data['aeo'])} AEO questions, "
          f"{len(data['competitors'])} competitors, {len(data['avoid'])} avoided")


if __name__ == "__main__":
    main()
