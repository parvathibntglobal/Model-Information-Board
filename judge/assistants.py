"""The AI assistants page (PROPOSED, 2026-11-12): the registry's personal agents
and coding builders, grouped by `contract/assistant_groups.yaml`, with what
engineers report about each COUNTED and never quoted.

NOTHING NEW IS COUNTED HERE. Every figure comes from a function the board
already uses, so this page cannot disagree with it:

    evidence_for_model   a model's jobs and capabilities, its distinct voices
                         (people) and distinct documents (reports); `declined`
                         rulings excluded, `merged` rows under their target
    reports_view         per job / capability / metric, each model's voices,
                         reports and positive / negative / neutral split
    issues_for           capabilities with problems from at least N people
    board_freshness      when the board last changed for a model

ALWAYS THE PUBLIC VIEW, COUNTS ONLY. Totals count every source
(`publication.hidden_from_counts`), as `/reports` does. No quote, URL, handle,
document id or platform NAME leaves this module: a quote stays behind the
sign-in on `/models/<id>`, and Reddit / X text may reach a public page only as
an official embed (CLAUDE.md, publication).

NO SCORE, NO RANK (rule 3). A card carries counts. The members of a group keep
the order of the contract file, which is not a ranking, and a comparison cell is
three counts of REPORTS (working / neutral / problems): a document is "working"
when it has a positive statement about the model on that job or capability, and
may be both. The people counts are per card and per issue, where the board
counts people; the comparison table is in reports because that is the unit the
board's split is held in.

ABSENCE IS NOT A VERDICT (rules 4 and 6). An assistant with no reports is
`state: "no_reports"`, distinct from one with problems reported, and a member of
the grouping file the registry does not hold is COUNTED (`not_in_registry`)
rather than dropped or rendered empty.
"""

from __future__ import annotations

from judge import publication
from judge.config import agent_canonical_ids, assistant_groups, board_vocabulary

#: board section name by the kind the page uses
_SECTION_OF_KIND = {"job": "best_for", "capability": "capability"}
_TOP_JOBS = 3


def _registry(conn, canonical_ids: list[str]) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT id, canonical_id, provider, display_name FROM model_version "
        "WHERE canonical_id = ANY(%s)",
        (canonical_ids,),
    ).fetchall()
    return {
        cid: {"id": mid, "canonical_id": cid, "provider": provider,
              "display_name": name or cid}
        for mid, cid, provider, name in rows
    }


def _vocab_names() -> dict[tuple[str, str], str]:
    out = {}
    for kind, section in _SECTION_OF_KIND.items():
        for items in (board_vocabulary().get(section) or {}).values():
            for it in items or []:
                out[(kind, it["slug"])] = it["name"]
    return out


def _axis_index(conn) -> dict[tuple[str, str, str], dict]:
    """{(kind, slug, canonical id): the model's counts on that axis}, from the
    Reports page's own view."""
    from judge.reports import reports_view

    index: dict[tuple[str, str, str], dict] = {}
    for axis in reports_view(conn)["axes"]:
        for m in axis["models"]:
            if m.get("canonical"):
                index[(axis["kind"], axis["slug"], m["canonical"])] = {
                    "name": axis["name"], **m}
    return index


def _documents(conn, doc_ids: set) -> tuple[int, str | None]:
    """(platforms, newest report date) over a model's documents. The platform
    count names no platform and leaves out the withheld ones, as the Reports
    page does."""
    if not doc_ids:
        return 0, None
    named = set(publication.withheld_sources())
    rows = conn.execute(
        "SELECT source, created_at FROM document WHERE id = ANY(%s)", (list(doc_ids),)
    ).fetchall()
    platforms = {s for s, _ in rows if s and s not in named}
    dates = [c for _, c in rows if c]
    return len(platforms), (max(dates).date().isoformat() if dates else None)


def _evidence(conn, cid: str, hidden: list[str]) -> dict:
    """One assistant's counts: people, reports, platforms, newest, and the
    per-job / per-capability rows (people and reports; the split is added by
    the caller from the Reports page's index)."""
    from judge.store.board_entries import evidence_for_model

    ev = evidence_for_model(conn, cid, hidden=hidden, with_voices=True)
    docs = {q["document_id"] for sec in ("best_for", "capabilities", "metrics")
            for item in ev[sec] for q in item["quotes"] if q.get("document_id") is not None}
    platforms, newest = _documents(conn, docs)
    return {"ev": ev, "people": ev["voices"], "reports": len(docs),
            "platforms": platforms, "newest": newest}


def _rows(items: list[dict], kind: str, cid: str, axes: dict) -> list[dict]:
    out = []
    for it in items:
        a = axes.get((kind, it["slug"], cid)) or {}
        split = a.get("split") or {}
        out.append({
            "slug": it["slug"], "name": it.get("name") or it["slug"],
            "people": it["voices"], "reports": it["reports"],
            "working": int(split.get("positive", 0)),
            "neutral": int(split.get("neutral", 0)),
            "problems": int(split.get("negative", 0)),
        })
    out.sort(key=lambda r: (-r["people"], -r["reports"], r["slug"]))
    return out


def _tags(cid: str, cfg: dict) -> list[dict]:
    return [{"key": k, "label": cfg["tag_labels"][k]} for k in cfg["tags"].get(cid, [])]


def assistants_view(conn) -> dict:
    cfg = assistant_groups()
    hidden = list(publication.hidden_from_counts())
    in_group = {m for g in cfg["groups"] for m in g["members"]}
    registry = _registry(conn, sorted(in_group | set(agent_canonical_ids())))
    axes = _axis_index(conn)
    names = _vocab_names()

    groups = []
    for g in cfg["groups"]:
        cards = []
        for cid in g["members"]:
            reg = registry.get(cid)
            if reg is None:
                continue
            e = _evidence(conn, cid, hidden)
            jobs = _rows(e["ev"]["best_for"], "job", cid, axes)
            cards.append({
                "id": reg["id"], "canonical_id": cid, "name": reg["display_name"],
                "provider": reg["provider"], "tags": _tags(cid, cfg),
                "state": "reports" if e["reports"] else "no_reports",
                "people": e["people"], "reports": e["reports"], "newest": e["newest"],
                "top_jobs": [{k: j[k] for k in ("slug", "name", "people", "reports")}
                             for j in jobs[:_TOP_JOBS]],
            })
        compare = []
        for row in g["compare"]:
            cells = []
            for c in cards:
                a = axes.get((row["kind"], row["slug"], c["canonical_id"])) or {}
                split = a.get("split") or {}
                cells.append({
                    "canonical_id": c["canonical_id"],
                    "people": a.get("voices", 0), "reports": a.get("reports", 0),
                    "working": int(split.get("positive", 0)),
                    "neutral": int(split.get("neutral", 0)),
                    "problems": int(split.get("negative", 0)),
                })
            compare.append({"kind": row["kind"], "slug": row["slug"],
                            "name": names[(row["kind"], row["slug"])], "cells": cells})
        groups.append({
            "key": g["key"], "title": g["title"], "what": g["what"],
            "members": len(g["members"]),
            "not_in_registry": sum(1 for cid in g["members"] if cid not in registry),
            "assistants": cards, "compare": compare,
        })

    unclassified = [
        {k: registry[cid][k] for k in ("id", "canonical_id", "provider")}
        | {"name": registry[cid]["display_name"]}
        for cid in agent_canonical_ids() if cid in registry and cid not in in_group
    ]
    return {
        "groups": groups,
        "unclassified": unclassified,
        "view": "public",
        "unit_note": (
            "People are distinct authors and reports are distinct documents. In the "
            "comparison tables each cell counts reports: working is a report with a "
            "positive statement, problems one with a negative statement. A report can "
            "be both. Counts only; nothing is scored or ranked."
        ),
    }


def assistant_detail(conn, ident: str) -> dict | None:
    """One assistant, or None when `ident` (canonical id or registry id) is not
    in the grouping file or the registry - the route answers 404."""
    from judge.blog_reference import issues_for
    from judge.freshness import board_freshness

    cfg = assistant_groups()
    row = conn.execute(
        "SELECT canonical_id FROM model_version WHERE id = %s OR canonical_id = %s",
        (ident, ident),
    ).fetchone()
    cid = row[0] if row else None
    group = next((g for g in cfg["groups"] if cid in g["members"]), None)
    if group is None:
        return None
    reg = _registry(conn, [cid])[cid]
    hidden = list(publication.hidden_from_counts())
    axes = _axis_index(conn)
    e = _evidence(conn, cid, hidden)
    jobs = _rows(e["ev"]["best_for"], "job", cid, axes)
    caps = _rows(e["ev"]["capabilities"], "capability", cid, axes)
    issues = issues_for(conn, cid)
    problems = [
        {"slug": i["slug"], "name": i["name"], "people_with_problems": i["problems"],
         "people_it_works_for": i["working"], "latest": i["latest"]}
        for i in (issues or {"issues": []})["issues"]
    ]
    fresh = board_freshness(conn)["models"].get(cid) or {}
    return {
        "assistant": {"id": reg["id"], "canonical_id": cid, "name": reg["display_name"],
                      "provider": reg["provider"]},
        "group": {"key": group["key"], "title": group["title"], "what": group["what"]},
        "tags": _tags(cid, cfg),
        "freshness": {"updated_at": fresh.get("updated_at"),
                      "newest_report_at": fresh.get("newest_report_at")},
        "state": "reports" if e["reports"] else "no_reports",
        "evidence": {"people": e["people"], "reports": e["reports"],
                     "platforms": e["platforms"], "newest": e["newest"]},
        "best_for": jobs,
        "problems": problems,
        "problems_min_people": (issues or {}).get("min_engineers"),
        "capabilities": caps,
        "guides": [],
        "guides_note": (
            "No guides yet: nothing links a how-to post to an assistant today, so this "
            "list is empty because the link does not exist, not because none are wanted."
        ),
    }
