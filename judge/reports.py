"""The Reports page: the board's evidence COUNTED, never quoted (2026-10-14).

What the demo `model-information-board-home-demo.html` shows under Reports, read
live: for every job, capability and metric, each model's voices, reports,
platforms and positive / negative / neutral split.

ALWAYS THE PUBLIC VIEW. `board_sections` runs with `withheld_publicly`, whatever
view this deployment serves, so a source that is never shown publicly (Reddit,
arXiv, X) adds nothing to any count here. The page says how many entries that
left out.

COUNTS ONLY, BY CONSTRUCTION. Nothing leaves this module that could identify a
statement: no quote, no URL, no document id, no author, and no platform NAME -
a model carries how many platforms its reports came from, not which. The
threshold (3 / 5 / 10 voices, two platforms) is applied on the page, from the
counts sent here, so changing it needs no second request.

THE NUMBERS ARE THE BOARD'S. `voices`, `reports`, `report_split` and `group`
come from `board_sections` unchanged, and the model order within a job or
capability is its order (groups, then the Wilson lower bound it never emits).
The only things computed here are what the board does not carry: platforms and
newest report date per model, and the split for metric rows, which the board
leaves out because its metric page is a figure table.
"""

from __future__ import annotations

from typing import Any

from judge import publication

#: board section -> the kind the page names it by
KINDS = {"best_for": "job", "capability": "capability", "metric": "metric"}


def _metric_split(quotes: list[dict], model_key: str) -> dict[str, int]:
    """A metric row's split, counted in REPORTS like `_split`: one document is
    positive if any of its statements about the model is, and can be both."""
    per_doc: dict[Any, set] = {}
    for q in quotes:
        if q.get("model_key") == model_key:
            per_doc.setdefault(q.get("document_id"), set()).add(q.get("polarity"))
    out = {"positive": 0, "negative": 0, "neutral": 0, "both": 0}
    for pols in per_doc.values():
        pos, neg = "positive" in pols, "negative" in pols
        out["positive"] += pos
        out["negative"] += neg
        out["both"] += pos and neg
        out["neutral"] += not pos and not neg
    return out


def reports_view(conn: Any) -> dict:
    from judge.board_grouping import parent_of
    from judge.config import parent_heading
    from judge.store.board_entries import board_sections

    # TOTALS COUNT EVERY SOURCE (contract/publication.yaml, 2026-10-15). This
    # page shows counts only, so nothing here can name a withheld platform -
    # except the number of platforms, which counts named ones only (below).
    counted = set(publication.hidden_from_counts())
    sections = board_sections(conn, hide_source=lambda src: src in counted)
    named = set(publication.withheld_sources())

    doc_ids = {
        q["document_id"]
        for sec in KINDS
        for item in sections.get(sec, [])
        for q in item.get("quotes", [])
        if q.get("document_id") is not None
    }
    meta: dict[Any, tuple[str | None, Any]] = {}
    if doc_ids:
        rows = conn.execute(
            "SELECT id, source, created_at FROM document WHERE id = ANY(%s)",
            (list(doc_ids),),
        ).fetchall()
        meta = {did: (source, created) for did, source, created in rows}

    axes = []
    parents: dict[str, str] = {}
    for sec, kind in KINDS.items():
        for item in sections.get(sec, []):
            quotes = item.get("quotes", [])
            docs_by_model: dict[str, set] = {}
            for q in quotes:
                docs_by_model.setdefault(q.get("model_key"), set()).add(q.get("document_id"))
            models = []
            for m in item.get("models", []):
                key = m["model_key"]
                docs = docs_by_model.get(key, set())
                platforms = {meta[d][0] for d in docs
                             if d in meta and meta[d][0] and meta[d][0] not in named}
                dates = [meta[d][1] for d in docs if d in meta and meta[d][1]]
                split = m.get("report_split") or _metric_split(quotes, key)
                models.append({
                    "key": key,
                    "label": m.get("model_label") or m.get("model_canonical") or key,
                    "canonical": m.get("model_canonical"),
                    "voices": m["voices"],
                    "reports": m["reports"],
                    "platforms": len(platforms),
                    "split": {k: int(split.get(k, 0))
                              for k in ("positive", "negative", "neutral", "both")},
                    "group": m.get("group"),
                    "newest": max(dates).date().isoformat() if dates else None,
                    "figures": sum(1 for f in item.get("figures", []) if f.get("model_key") == key),
                })
            # THE GROUP A CAPABILITY OR METRIC IS FILED UNDER, from
            # contract/slug_parents.yaml: a heading for reading, never a merge -
            # counts are not added across a group, since one post can sit under
            # two names. None when the slug is not filed (jobs have no groups).
            parent = parent_of(item["slug"], section=sec)
            if parent:
                parents[parent] = parent_heading(parent)
            axes.append({
                "kind": kind,
                "slug": item["slug"],
                "name": item.get("name") or item["slug"],
                "parent": parent,
                "definition": item.get("definition"),
                "voices": item["voices"],
                "reports": item["reports"],
                "models": models,
            })

    newest = max((m["newest"] for a in axes for m in a["models"] if m["newest"]), default=None)
    return {
        "view": "public",
        "newest_report": newest,
        # HOW MANY ENTRIES THE PUBLIC VIEW LEFT OUT, and nothing else: the
        # board's notice also states this deployment's own view, which is not
        # the view this page counts with.
        "withheld_entries": int((sections.get("_withheld_sources") or {}).get("entries") or 0),
        "parents": parents,
        "axes": axes,
    }
