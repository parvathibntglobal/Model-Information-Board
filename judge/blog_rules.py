"""The newsroom rules, as Admin -> Blogs shows them (blog_rules.yaml).

The same file is the writer's brief and the checker's thresholds
(generate_sample_blogs.py `newsroom`, `reported_violations`); this module only
reads it for the page, with every rule's thresholds filled into its wording,
so the page and the checks cannot say different numbers.

A rule is `checked: code` (refused at ingest when broken), `editor` (a
reviewer's rule) or `process` (how the team works). Nothing here is defaulted:
an unreadable file is reported, not replaced with a list (rule 12).
"""

from __future__ import annotations

from pathlib import Path

import yaml

PATH = Path(__file__).resolve().parents[1] / "blog_rules.yaml"
CHECKED = {"code": "Checked by code", "editor": "Editor's rule", "process": "Process"}


def rules(path: Path = PATH) -> dict:
    """The rules for the page.

    {"style", "limits", "counts",
     "sections": [{"name", "rules": [{id, rule, detail, checked, label}]}]}
    """
    if not path.exists():
        return {"available": False, "reason": f"{path.name} is missing"}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    limits = raw.get("limits") or {}
    sections, counts = [], {k: 0 for k in CHECKED}
    for sec in raw.get("sections") or []:
        out = []
        for r in sec.get("rules") or []:
            checked = str(r.get("checked") or "")
            if checked not in CHECKED:
                raise ValueError(
                    f"{path.name}: rule {r.get('id')!r} has checked={checked!r}; "
                    f"one of {', '.join(CHECKED)}"
                )
            counts[checked] += 1
            out.append(
                {
                    "id": r["id"],
                    "rule": r["rule"],
                    "detail": " ".join(str(r.get("detail") or "").split()).format(**limits),
                    "checked": checked,
                    "label": CHECKED[checked],
                }
            )
        sections.append({"name": sec["name"], "rules": out})
    return {
        "available": True,
        "style": raw.get("style"),
        "limits": limits,
        "sections": sections,
        "counts": counts,
    }
