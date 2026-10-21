"""One paraphrase per report: what its author said about the model, in our words.

A REPORT IS ONE DOCUMENT ABOUT ONE MODEL - the unit every count on the site
calls "reports". Its paraphrase is written from all of that document's
excerpts about the model, whatever section they were filed under, and is
re-drafted whenever that set changes (`excerpts_digest`).

STORED ONCE CODE HAS CHECKED ITS SHAPE (judge/feed/checks.py), with no person
reading each one - which is what makes this rule 2's first caller whose text
reaches a page unreviewed, and why the PROPOSED rule-2 amendment
(docs/proposals/evidence-feed.md) has to land before it reaches main. A
refused paraphrase is asked for once more, with the reason; refused twice, the
report stays in the feed with its source and "not paraphrased yet" (rule 4).

NEWEST FIRST, so a partial run fills the top of every feed - the part a reader
sees - before the archive.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from typing import Any

from judge import publication
from judge.feed import checks
from judge.feed.items import excerpts_digest
from judge.feed.llm import FeedModelUnavailable, call_tool

#: The longest excerpt text sent per report. Measured 2026-10-21 over 4,122
#: reports on the shared DB: 208 characters on average, 464 at the 90th
#: percentile - so this trims only the long tail, and says so in the prompt.
MAX_EXCERPT_CHARS = 1500

SYSTEM = """\
You write entries for a public evidence feed about AI models. For each report,
restate in your own words what its author said about {model}.

A report is one post or comment by one person. You are given the excerpts our
pipeline took from it, each tagged with the topic it was filed under and the
reaction (positive, negative or neutral) it was filed with.

For every report write ONE or TWO plain sentences, at most 45 words:
- Say what the author reported about {model}: what they used it for, what
  happened, and any condition they named (task, setup, version, size, cost).
- Keep the reaction as the excerpts show it. Do not soften a complaint or
  inflate praise. If the excerpts are mixed, say both sides.
- Use your own words. Never copy more than four consecutive words from an
  excerpt, and do not use quotation marks.
- Write it as a report, not as fact: "The author found...", "Reports that...",
  "Describes...". Never say whether the author is right.
- Keep every number exactly as written in the excerpts. Add no number of your
  own: no percentages, no counts, no prices that are not in the excerpts.
- Do not name the author, any handle, community, forum, website or platform,
  and include no links.
- Mention another model only where the excerpts compare it.

Return exactly one paraphrase per report id through the submit_paraphrases tool.
"""

TOOL = {
    "type": "function",
    "function": {
        "name": "submit_paraphrases",
        "description": "One paraphrase per report id.",
        "parameters": {
            "type": "object",
            "properties": {
                "paraphrases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "The report id, e.g. R3"},
                            "text": {"type": "string"},
                        },
                        "required": ["id", "text"],
                    },
                }
            },
            "required": ["paraphrases"],
        },
    },
}

SECTION_WORDS = {"best_for": "used for", "capability": "capability", "metric": "measured"}


def pending(conn, prompt_version: str, *, model_key: str | None = None) -> tuple[list[dict], int]:
    """`(reports whose current paraphrase is missing or stale, newest first;
    how many were left out because the terms do not allow their source)`."""
    terms = publication.evidence_feed_terms()
    rows = conn.execute(
        "SELECT v.id, coalesce(v.display_name, v.canonical_id, v.id), be.document_id, "
        "       be.section, COALESCE(be.ruling_target, be.slug), be.name, be.polarity, be.quote, "
        "       d.source, d.created_at "
        "FROM board_entry be "
        "JOIN model_version v "
        "  ON v.id = be.model_version_id OR v.canonical_id = be.model_version_id "
        "LEFT JOIN document d ON d.id = be.document_id "
        "WHERE be.ruling IS DISTINCT FROM 'declined'" + (" AND v.id = %s" if model_key else ""),
        (model_key,) if model_key else (),
    ).fetchall()
    units: dict[tuple[str, str], dict] = {}
    for key, label, doc, section, slug, name, polarity, quote, source, posted in rows:
        u = units.setdefault(
            (key, doc),
            {
                "model_key": key,
                "model_label": label,
                "document_id": doc,
                "source": source,
                "posted_at": posted,
                "entries": [],
            },
        )
        u["entries"].append(
            {"section": section, "slug": slug, "name": name, "polarity": polarity, "quote": quote}
        )
    stored = {
        (m, d): digest
        for d, m, digest in conn.execute(
            "SELECT document_id, model_version_id, excerpts_digest FROM feed_paraphrase "
            "WHERE prompt_version = %s" + (" AND model_version_id = %s" if model_key else ""),
            (prompt_version, model_key) if model_key else (prompt_version,),
        ).fetchall()
    }
    out, not_allowed = [], 0
    for k, u in units.items():
        if publication.withheld_publicly(u["source"]) and not terms["may_draw_on_withheld"]:
            not_allowed += 1
            continue
        u["digest"] = excerpts_digest(u["entries"])
        if stored.get(k) != u["digest"]:
            out.append(u)
    out.sort(
        key=lambda u: (
            u["posted_at"] is None,
            -(u["posted_at"].timestamp() if u["posted_at"] else 0),
        )
    )
    return out, not_allowed


def _report_block(rid: str, unit: dict) -> str:
    lines, used = [f"[{rid}]"], 0
    for e in unit["entries"]:
        quote = (e["quote"] or "").strip()
        room = MAX_EXCERPT_CHARS - used
        if room <= 0:
            lines.append("- (further excerpts left out for length)")
            break
        if len(quote) > room:
            quote = quote[:room].rstrip() + " ..."
        used += len(quote)
        topic = f"{SECTION_WORDS.get(e['section'], e['section'])}: {e['name'] or e['slug']}"
        lines.append(f"- ({topic}; reaction: {e['polarity']}) {quote}")
    return "\n".join(lines)


def _ask(units: list[dict], settings: dict, run_id: str, call: Callable, retry_reasons=None):
    label = units[0]["model_label"]
    ids = {f"R{i}": u for i, u in enumerate(units, 1)}
    blocks = []
    for rid, u in ids.items():
        block = _report_block(rid, u)
        if retry_reasons and rid in retry_reasons:
            block += (
                f"\n(Your previous paraphrase of {rid} was refused: {retry_reasons[rid]}. "
                "Write it again within the rules.)"
            )
        blocks.append(block)
    user = f"Model: {label}\n\n" + "\n\n".join(blocks)
    args, served = call(
        model=settings["model"],
        system=SYSTEM.format(model=label),
        user=user,
        tool=TOOL,
        run_id=run_id,
        max_tokens=120 * len(units) + 400,
        reasoning_effort=settings["reasoning_effort"],
    )
    got = {}
    for p in args.get("paraphrases") or []:
        if isinstance(p, dict) and p.get("id") in ids and isinstance(p.get("text"), str):
            got.setdefault(p["id"], p["text"].strip())
    return ids, got, served


def _store(conn, unit: dict, text: str, served: str, settings: dict, run_id: str) -> None:
    conn.execute(
        "INSERT INTO feed_paraphrase (document_id, model_version_id, prompt_version, "
        "  excerpts_digest, text, proposer_model, run_id) VALUES (%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (document_id, model_version_id, prompt_version) DO UPDATE SET "
        "  excerpts_digest = EXCLUDED.excerpts_digest, text = EXCLUDED.text, "
        "  proposer_model = EXCLUDED.proposer_model, run_id = EXCLUDED.run_id, "
        "  generated_at = now()",
        (
            unit["document_id"],
            unit["model_key"],
            settings["prompt_version"],
            unit["digest"],
            text,
            served,
            run_id,
        ),
    )


def run(
    conn,
    units: list[dict],
    settings: dict,
    *,
    call: Callable = call_tool,
    commit: bool = True,
    log: Callable[[str], Any] = lambda s: None,
) -> dict:
    """Paraphrase `units`, a batch per call, one model per batch. Counted:
    stored, refused by reason, and calls that failed outright (rule 4)."""
    run_id = f"feed_p_{uuid.uuid4().hex[:12]}"
    report = {
        "run_id": run_id,
        "asked": len(units),
        "stored": 0,
        "calls": 0,
        "asked_again": 0,
        "refused": {},
        "failed_calls": [],
    }
    by_model: dict[str, list[dict]] = {}
    for u in units:
        by_model.setdefault(u["model_key"], []).append(u)
    for model_key, mine in by_model.items():
        for start in range(0, len(mine), settings["per_call"]):
            batch = mine[start : start + settings["per_call"]]
            reasons: dict[str, str] = {}
            todo = batch
            for attempt in (1, 2):
                try:
                    report["calls"] += 1
                    ids, got, served = _ask(
                        todo, settings, run_id, call, reasons if attempt == 2 else None
                    )
                except FeedModelUnavailable as e:
                    report["failed_calls"].append(f"{model_key}: {e}")
                    break
                retry, next_reasons = [], {}
                for rid, unit in ids.items():
                    text = got.get(rid)
                    problem = (
                        "no paraphrase returned"
                        if text is None
                        else checks.paraphrase_problem(
                            text,
                            [e["quote"] or "" for e in unit["entries"]],
                            unit["model_label"],
                            max_chars=settings["max_chars"],
                            max_copied_words=settings["max_copied_words"],
                        )
                    )
                    if problem is None:
                        _store(conn, unit, text, served, settings, run_id)
                        report["stored"] += 1
                    elif attempt == 1:
                        retry.append(unit)
                        report["asked_again"] += 1
                    else:
                        # GROUPED BY KIND: "copies 7 ..." and "copies 9 ..." are
                        # one reason, counted once per report.
                        reason = re.sub(r"\d+", "N", problem.split(" (")[0])
                        report["refused"][reason] = report["refused"].get(reason, 0) + 1
                    if problem is not None and attempt == 1:
                        next_reasons[f"R{len(retry)}"] = problem
                if commit:
                    conn.commit()
                if not retry:
                    break
                todo, reasons = retry, next_reasons
            log(f"{model_key}: {report['stored']} stored so far, {report['calls']} calls")
    return report
