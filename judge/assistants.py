"""The AI assistants page (PROPOSED, 2026-11-12): the registry's personal agents
and coding builders, grouped by `contract/assistant_groups.yaml`, with what
people report about each COUNTED, and on an assistant's own page the
reports behind its jobs and problems shown under the publication rules.

NOTHING NEW IS COUNTED HERE. Every figure comes from a function the board
already uses, so this page cannot disagree with it:

    evidence_for_model   a model's jobs and capabilities, its distinct voices
                         (people) and distinct documents (reports); `declined`
                         rulings excluded, `merged` rows under their target
    reports_view         per job / capability / metric, each model's voices,
                         reports and positive / negative / neutral split
    issues_for           capabilities with problems from at least N people
    board_freshness      when the board last changed for a model

ALWAYS THE PUBLIC VIEW. Totals count every source
(`publication.hidden_from_counts`), as `/reports` does. The list endpoint is
counts only. The DETAIL endpoint also carries, under each job and problem, the
reports behind its counts, by `_treatment` (contract/publication.yaml
`assistants_page`, PROPOSED; citations through the feed's `cite_source`):

    embed-only source (reddit, x)   NO text, no link, no handle: the ids the
                                    platform's official embed needs, loaded by
                                    the reader's click (`cite_source`)
    withheld source (arxiv, bluesky, no recorded source), or held
                                    nothing at all - counted in `omitted`
    any other source                the verified quote, its platform name and
                                    an https link to the source; with no such
                                    link, nothing - counted in `unlinked`

No document id, author or handle leaves this module. A paraphrase is not
available (the feed's paraphraser runs for seated models and costs money).

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

from datetime import UTC, datetime

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
        # NO MAKER IS SHOWN, NOT "unknown": a registry-only row whose maker is
        # not known carries provider 'unknown', which is a placeholder, not a
        # company (reviewer point, 2026-11-12). Absent stays absent (rule 6).
        cid: {"id": mid, "canonical_id": cid,
              "provider": None if (provider or "").strip().lower() in ("", "unknown") else provider,
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


def _documents(conn, doc_ids: set) -> tuple[int, str | None, dict]:
    """(platforms, newest report date, {document id: (source, posted_at)}) over
    a model's documents. The platform count names no platform and leaves out
    the withheld ones, as the Reports page does."""
    if not doc_ids:
        return 0, None, {}
    named = set(publication.withheld_sources())
    rows = conn.execute(
        "SELECT id, source, created_at FROM document WHERE id = ANY(%s)", (list(doc_ids),)
    ).fetchall()
    platforms = {s for _, s, _ in rows if s and s not in named}
    dates = [c for _, _, c in rows if c]
    return (len(platforms), (max(dates).date().isoformat() if dates else None),
            {d: (s, c) for d, s, c in rows})


def _treatment(source: str | None) -> str:
    """How a report from `source` may appear on this PUBLIC page, by
    contract/publication.yaml `assistants_page` (its own block, #625 review:
    the feed's rule is paraphrase-only, and this page quotes):

        omit    `held` (bluesky), or withheld from the public with no embed
                (arxiv, no recorded source): no text, no embed, no link -
                COUNTED by the caller
        embed   `embed_only` (reddit, x): the platform's official embed,
                never our copy of its text
        quote   every other source: the verified quote with its platform
                credit and an https link, or not shown at all (`_support`)
    """
    terms = publication.assistants_page_terms()
    if source in terms["held"]:
        return "omit"
    if source in terms["embed_only"]:
        return "embed"
    if publication.withheld_publicly(source):
        return "omit"
    return "quote"


def _support(conn, items: list[dict], info: dict, *, polarity: str | None = None) -> dict:
    """The reports behind one job's or problem's counts, for the public page:
    {"items": [...], "omitted": N, "unlinked": N, "total": N}. `total` counts
    every report (never truncated); `omitted` is how many came from a source we
    do not show publicly, and `unlinked` how many quotes have no https link to
    their source (rule 4: counted and said, never silently dropped). An item
    carries NO text for an embed-only source.

    ⚠ A QUOTE IS SHOWN ONLY WITH ITS LINK (#625 review, Parvathi). Its text
      without a link is the undertaking's second `voided_by` case ("a quote
      from any other source shown publicly without its platform credit and
      link"), so a quote whose cite has no `url` is counted in `unlinked` and
      its text never leaves this module."""
    from judge.feed.items import cite_source

    quotes = [q for it in items for q in it["quotes"]
              if polarity is None or q.get("polarity") == polarity]
    embed_docs = [q["document_id"] for q in quotes
                  if _treatment((info.get(q["document_id"]) or (None,))[0]) == "embed"]
    embeds = {}
    if embed_docs:
        embeds = {d: {"outcome": o, "url": u} for d, o, u in conn.execute(
            "SELECT document_id, outcome, url FROM feed_embed WHERE document_id = ANY(%s)",
            (embed_docs,)).fetchall()}
    epoch = datetime.min.replace(tzinfo=UTC)
    quotes.sort(key=lambda q: (info.get(q["document_id"]) or (None, None))[1] or epoch,
                reverse=True)
    out, omitted, unlinked, seen_embeds = [], 0, 0, set()
    for q in quotes:
        source, at = info.get(q["document_id"]) or (None, None)
        how = _treatment(source)
        if how == "omit":
            omitted += 1
            continue
        if how == "embed":
            if q["document_id"] in seen_embeds:
                continue
            seen_embeds.add(q["document_id"])
        cite = cite_source({"source": source, "url": q.get("url")},
                           embeds.get(q["document_id"]))
        if how == "quote" and not cite.get("url"):
            unlinked += 1
            continue
        out.append({"polarity": q.get("polarity"),
                    "posted_at": at.isoformat() if at else None,
                    "text": q["quote"] if how == "quote" else None,
                    "source": cite})
    return {"items": out, "omitted": omitted, "unlinked": unlinked, "total": len(quotes)}


def _evidence(conn, cid: str, hidden: list[str]) -> dict:
    """One assistant's counts: people, reports, platforms, newest, and the
    per-job / per-capability rows (people and reports; the split is added by
    the caller from the Reports page's index)."""
    from judge.store.board_entries import evidence_for_model

    ev = evidence_for_model(conn, cid, hidden=hidden, with_voices=True)
    docs = {q["document_id"] for sec in ("best_for", "capabilities", "metrics")
            for item in ev[sec] for q in item["quotes"] if q.get("document_id") is not None}
    platforms, newest, info = _documents(conn, docs)
    return {"ev": ev, "people": ev["voices"], "reports": len(docs),
            "platforms": platforms, "newest": newest, "info": info}


def _rows(items: list[dict], kind: str, cid: str, axes: dict, support=None) -> list[dict]:
    """`support(item)` adds the reports behind a row (detail page only)."""
    out = []
    for it in items:
        a = axes.get((kind, it["slug"], cid)) or {}
        split = a.get("split") or {}
        row = {
            "slug": it["slug"], "name": it.get("name") or it["slug"],
            "people": it["voices"], "reports": it["reports"],
            "working": int(split.get("positive", 0)),
            "neutral": int(split.get("neutral", 0)),
            "problems": int(split.get("negative", 0)),
        }
        if support is not None:
            row["evidence"] = support(it)
        out.append(row)
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
            # ONLY ASSISTANTS WITH REPORTS are columns of the table (reviewer
            # point B): a row of "No reports" per silent assistant is a wall.
            # They are listed, by name, under the cards (the page).
            for c in (c for c in cards if c["state"] == "reports"):
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
            "Each person is counted once, however often they posted; a report is one "
            "post or article. In the comparison tables, each cell counts reports that "
            "say a job worked, was neutral, or had problems, and one report can say "
            "more than one. Counts, not a ranking."
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
    info = e["info"]
    jobs = _rows(e["ev"]["best_for"], "job", cid, axes,
                 support=lambda it: _support(conn, [it], info))
    caps = _rows(e["ev"]["capabilities"], "capability", cid, axes)
    issues = issues_for(conn, cid)
    by_cap = {it["slug"]: it for it in e["ev"]["capabilities"]}
    problems = [
        {"slug": i["slug"], "name": i["name"], "people_with_problems": i["problems"],
         "people_it_works_for": i["working"], "latest": i["latest"],
         "evidence": _support(conn, [by_cap[i["slug"]]] if i["slug"] in by_cap else [],
                              info, polarity="negative")}
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
        # The publication rules, in the reader's words (contract/publication.yaml):
        # verified quotes with platform and link; Reddit/X only as the platform's
        # embed on click; withheld sources counted, never shown.
        "quotes_note": (
            "Under each job are the reports themselves: quotes linked to their source, "
            "Reddit and X posts as the platform's own embed (loaded when you click), and "
            "reports from sources we don't show publicly, counted but not shown."
        ),
        # Empty because nothing links a how-to post to an assistant yet; a reader
        # needs only the fact (the page shows this when the list is empty).
        "guides": [],
        "guides_note": "No how-to guides for this assistant yet.",
    }
