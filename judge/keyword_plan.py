"""Admin -> SEO keywords -> Keyword plan: which keywords to use on which page.

READS ONE FILE, `seo/keyword_plan.json`, written by
`scripts/build_keyword_plan.py` from `seo/keyword_plan.yaml` and the board SEO
workbook's Combinations and Planner volumes. A dated plan, not a live figure:
every volume is a Google Keyword Planner band from that workbook or an
estimate made from one, and the file says which.

SIGNED-IN ONLY: served at `/admin/seo-keyword-plan`, which is not a public
read (judge/gate.py). Nothing here touches the database.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "seo" / "keyword_plan.json"


def load(path: Path = PATH) -> dict[str, Any]:
    """The plan, or `{"available": False}` when it has not been built."""
    if not path.exists():
        return {"available": False, "pages": [], "keywords": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["available"] = True
    return data
