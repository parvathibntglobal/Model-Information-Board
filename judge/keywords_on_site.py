"""Admin -> Keywords: which SEO keywords sit on which public page, and where.

READS ONE FILE, `seo/keywords_on_site.json`, written by
`scripts/export_keywords_on_site.py` from the keyword inventory workbook. The
inventory was made by rendering every public tab and matching each keyword of
the SEO workbook against the text actually on it (2026-10-19), so the
dashboard shows a dated snapshot, not a live crawl.

SIGNED-IN ONLY: served at `/admin/seo-keywords`, which is not a public read
(judge/gate.py). Nothing here touches the database.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "seo" / "keywords_on_site.json"

#: Workbook columns the dashboard leaves out (decided 2026-10-19).
EXCLUDED_COLUMNS = ("Found in SEO workbook sheet(s)", "Demand estimate (SEO workbook, not measured)")


def load(path: Path = PATH) -> dict[str, Any]:
    """The snapshot, or `{"available": False}` when the file has not been made."""
    if not path.exists():
        return {"available": False, "tabs": [], "rows": [], "placements": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["available"] = True
    return data
