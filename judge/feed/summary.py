"""One page per model: what the reports say, drafted by a model, approved by a person.

The blog's and the quiz's guard (rule 2 as agreed 2026-10-06): a draft is
checked in code (judge/feed/checks.py) and stored `pending`; nobody outside
Admin sees it until a person approves it. A new approval supersedes the last,
so a model has at most one live summary.

WRITTEN FROM OUR PARAPHRASES, NOT FROM THE SOURCES. Every report it may cite
has already passed the paraphrase checks, so the summary never sees a Reddit
or X post's own words. It is checked against those words anyway: a summary
may reuse our phrasing, not the author's.

NO NUMBERS AGAIN AND AGAIN. The counts are on every other page; this one says
what was reported. So it states no count of reports or people - code refuses
any number its citations do not carry, and flags quantity words ("most",
"many") for the reviewer - and every paragraph cites the reports it rests on,
so a reader can check each claim against them.

THE DENOMINATOR TRAVELS WITH IT (rule 7): written from the newest
`reports_used` of `reports_available` paraphrased reports, and the page counts
how many have been posted since.

DRAFTED ONCE, THEN REVISED (2026-10-27, judge/feed/revise.py). The schedule
drafts a model's first summary here and never redrafts an approved one: each
week it proposes point-level edits to it instead. Every attempt, stored or
refused, is a `feed_summary_attempt` row, so a refused draft is not paid for
again until a newer report arrives (Parvathi's #558 condition).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

from psycopg.types.json import Jsonb

from judge import publication
from judge.feed import checks
from judge.feed.items import (
    by_report,
    cite_source,
    excerpts_digest,
    model_entries,
    report_polarity,
    require_seated,
    resolve_model,
    seated_keys,
)
from judge.feed.llm import BudgetSpent, FeedModelUnavailable, call_tool

SYSTEM = """\
You write a one-page summary of what engineers have reported about {model},
for readers who want to know what lies behind the counts on our site. You are
given the reports, newest first, each already restated in our own words, with
the date it was posted, the topics it was filed under and its reaction.

Write {min_p} to {max_p} short paragraphs. Aim for about {target} words; more than
{max_words} words in all is refused, so stay well under it.
- Organise by theme: what people used it for and found working, what they
  found failing, the conditions that made the difference, where reports
  disagree, and anything that changed over time.
- Do not say how many reports or people said something, and avoid words that
  claim a quantity (most, many, few, majority, everyone, nobody). Describe what
  was reported; the citations show who reported it.
- Every paragraph cites the ids of the reports it rests on, and only those.
  The ids run from R1 to R{last}; there are no others. Ids go ONLY in the
  `cites` list - never in the paragraph's text, not even in brackets.

- Write no measured figures: no prices, speeds, scores, sizes, percentages,
  context lengths or counts - the feed beside this page carries every one
  with its source. Describe them in words instead ("faster", "cheaper",
  "a long context").
- Model names and version numbers are fine, written exactly as the reports
  write them. Any other digit must appear in a report cited IN THAT SAME
  PARAGRAPH; when in doubt, leave the number out.
- Never reuse more than five words in a row from any report.
- Report, do not judge. Never say whether a report is right.
- Do not name authors, handles, communities, websites or platforms; no links,
  no quotation marks, no headings, no bullet points, no recommendation.

BEFORE YOU SUBMIT, read every sentence once more for numbers. A draft is
refused for any of these, even used loosely as a figure of speech:
- a report id in the text ("(R12)", "R4 and R9") - ids belong in `cites`;
- a date, month or year ("in October", "2026") - write "earlier" or "more
  recently" instead;
- a number word: two, three, four, ten, twenty, dozens, hundreds, thousands,
  millions. Common slips and what to write instead:
    "hundreds of lines" -> "large files"
    "thousands of tokens" -> "long inputs"
    "three times" / "a few times" -> "more than once"
    "two models" -> "both models"
    "dozens of steps" -> "long multi-step tasks"

Return the paragraphs through the submit_summary tool.
"""

TOOL = {
    "type": "function",
    "function": {
        "name": "submit_summary",
        "description": "The summary as paragraphs, each with the report ids it cites.",
        "parameters": {
            "type": "object",
            "properties": {
                "paragraphs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "cites": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": 'Report ids, e.g. ["R2", "R7"]',
                            },
                        },
                        "required": ["text", "cites"],
                    },
                }
            },
            "required": ["paragraphs"],
        },
    },
}


class NotEnoughReports(ValueError):
    """Fewer paraphrased reports than the contract's minimum."""


def _paraphrased_reports(conn, model: dict, paraphrase_version: str) -> list[dict]:
    """The model's reports with a CURRENT paraphrase, newest posted first."""
    reports = by_report(model_entries(conn, model))
    if not reports:
        return []
    stored = {
        d: (text, digest)
        for d, text, digest in conn.execute(
            "SELECT document_id, text, excerpts_digest FROM feed_paraphrase "
            "WHERE model_version_id = %s AND prompt_version = %s AND document_id = ANY(%s)",
            (model["key"], paraphrase_version, list(reports)),
        ).fetchall()
    }
    out = []
    for doc, es in reports.items():
        found = stored.get(doc)
        if found is None or found[1] != excerpts_digest(es):
            continue
        tags = sorted({e["name"] or e["slug"] for e in es})
        out.append(
            {
                "id": doc,
                "posted_at": es[0]["posted_at"],
                "polarity": report_polarity(es),
                "tags": tags,
                "paraphrase": found[0],
                "entries": es,
            }
        )
    out.sort(
        key=lambda r: (
            r["posted_at"] is None,
            -(r["posted_at"].timestamp() if r["posted_at"] else 0),
        )
    )
    return out


def _user_message(label: str, reports: list[dict]) -> str:
    blocks = []
    for i, r in enumerate(reports, 1):
        when = r["posted_at"].date().isoformat() if r["posted_at"] else "date not recorded"
        blocks.append(
            f"[R{i}] {when} · {', '.join(r['tags'])} · reaction: {r['polarity']}\n{r['paraphrase']}"
        )
    return f"Model: {label}\n\n{len(reports)} reports, R1 to R{len(reports)}:\n\n" + "\n\n".join(
        blocks
    )


def _with_ids(paragraph: dict) -> dict:
    """A citation written `19` or `r19` is the report `R19` - a formatting
    slip, not a different claim (2026-10-21: 6 of 17 refused drafts cited bare
    numbers). Anything else is left as written for the check to judge: an id
    that names no report it was given is still refused."""
    cites = paragraph.get("cites")
    if not isinstance(cites, list):
        return paragraph
    fixed = []
    for c in cites:
        text = str(c).strip()
        if text.isdigit():
            text = f"R{text}"
        elif text[:1] == "r" and text[1:].isdigit():
            text = f"R{text[1:]}"
        fixed.append(text)
    return {**paragraph, "cites": fixed}


def draft(
    conn,
    model_id: str,
    settings: dict,
    paraphrase_version: str,
    *,
    call: Callable = call_tool,
    commit: bool = True,
) -> dict:
    """Draft one summary and store it `pending`, or say why not."""
    model = resolve_model(conn, model_id)
    reports = _paraphrased_reports(conn, model, paraphrase_version)
    if len(reports) < settings["min_reports"]:
        raise NotEnoughReports(
            f"{model['label']} has {len(reports)} paraphrased reports; a summary needs "
            f"{settings['min_reports']} (contract/evidence_feed.yaml summary.min_reports)"
        )
    used = reports[: settings["max_reports"]]
    rid = {f"R{i}": r for i, r in enumerate(used, 1)}
    sources = {k: [r["paraphrase"]] for k, r in rid.items()}
    excerpts = {k: [e["quote"] or "" for e in r["entries"]] for k, r in rid.items()}
    run_id = f"feed_s_{uuid.uuid4().hex[:12]}"
    # A TARGET BELOW THE LIMIT: asked for "at most 450", the first live run
    # (2026-10-21) wrote 516 twice. The limit is still what the check enforces.
    # HALF THE LIMIT since prompt s3 (2026-10-26): asked for 70% (420 of 600),
    # drafts still ran to 602-657 words and were refused.
    system = SYSTEM.format(
        model=model["label"],
        min_p=min(3, settings["max_paragraphs"]),
        max_p=settings["max_paragraphs"],
        max_words=settings["max_words"],
        target=round(settings["max_words"] * 0.5),
        last=len(used),
    )
    user = _user_message(model["label"], used)
    reason, reasons, answered = None, [], False
    for _attempt in range(settings["attempts"]):
        message = (
            user
            if reason is None
            else (
                user
                + f"\n\nYour previous summary was refused: {reason}. "
                "Write it again within the rules."
            )
        )
        try:
            args, served = call(
                model=settings["model"],
                system=system,
                user=message,
                tool=TOOL,
                run_id=run_id,
                max_tokens=4 * settings["max_words"] + 800,
                reasoning_effort=settings["reasoning_effort"],
            )
        except BudgetSpent as e:
            # NOT AN ATTEMPT: the cap stopped the run before the call.
            reason = str(e)
            reasons.append(reason)
            break
        except FeedModelUnavailable as e:
            # AN ATTEMPT THAT FAILED, not a run that did: counted like a refusal.
            reason = str(e)
            reasons.append(reason)
            continue
        answered = True
        paragraphs = [_with_ids(p) for p in (args.get("paragraphs") or []) if isinstance(p, dict)]
        reason, flags = checks.summary_problems(
            paragraphs,
            sources,
            model["label"],
            excerpts=excerpts,
            max_words=settings["max_words"],
            max_paragraphs=settings["max_paragraphs"],
            max_copied_words=settings["max_copied_words"],
            quantity_words=settings["quantity_words"],
        )
        if reason is None:
            break
        reasons.append(reason)
    newest = max((r["posted_at"] for r in used if r["posted_at"]), default=None)
    if reason is not None:
        # REMEMBERED, so the schedule does not pay for it again until a newer
        # report arrives - unless no call was made at all (a spend cap, a dead
        # key), which is not a verdict on these reports.
        if answered:
            record_attempt(conn, model["key"], "draft", "refused", parent_id=None,
                           summary_id=None, newest=newest, considered=len(used),
                           detail="; then ".join(reasons),
                           prompt_version=settings["prompt_version"], run_id=run_id)
            if commit:
                conn.commit()
        # EVERY attempt's reason: the last alone hides what the first got wrong.
        return {
            "stored": False,
            "model": model,
            "refused": "; then ".join(reasons),
            "run_id": run_id,
        }

    body = [
        {"text": p["text"].strip(), "cites": [rid[c]["id"] for c in dict.fromkeys(p["cites"])]}
        for p in paragraphs
    ]
    summary_id = f"fs_{uuid.uuid4().hex}"
    # ONE PENDING DRAFT PER MODEL: an older one is superseded, with the time.
    conn.execute(
        "UPDATE feed_summary SET state = 'superseded', reviewed_at = now(), "
        "  review_note = 'replaced by a newer draft' "
        "WHERE model_version_id = %s AND state = 'pending'",
        (model["key"],),
    )
    conn.execute(
        "INSERT INTO feed_summary (id, model_version_id, prompt_version, paragraphs, flags, "
        "  reports_used, reports_available, newest_report_at, proposer_model, run_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            summary_id,
            model["key"],
            settings["prompt_version"],
            Jsonb(body),
            Jsonb(flags),
            len(used),
            len(reports),
            newest,
            served,
            run_id,
        ),
    )
    record_attempt(conn, model["key"], "draft", "stored", parent_id=None, summary_id=summary_id,
                   newest=newest, considered=len(used), detail=None,
                   prompt_version=settings["prompt_version"], run_id=run_id)
    if commit:
        conn.commit()
    return {
        "stored": True,
        "id": summary_id,
        "model": model,
        "flags": flags,
        "reports_used": len(used),
        "reports_available": len(reports),
        "run_id": run_id,
    }


def review(conn, summary_id: str, decision: str, note: str | None = None) -> dict | None:
    """Approve or reject a pending draft. Approval supersedes the live summary."""
    if decision not in ("approve", "reject"):
        raise ValueError("decision must be approve or reject")
    row = conn.execute(
        "SELECT model_version_id, state, parent_id FROM feed_summary WHERE id = %s", (summary_id,)
    ).fetchone()
    if row is None:
        return None
    if row[1] != "pending":
        raise ValueError(f"this summary is {row[1]}, not pending")
    if decision == "approve" and row[2] is not None:
        # A REVISION EDITS ONE APPROVED SUMMARY. If another has been approved
        # since, approving this would silently undo it: refused, so the
        # reviewer rejects it and the next weekly run revises the live one.
        live = conn.execute(
            "SELECT id FROM feed_summary WHERE model_version_id = %s AND state = 'approved' "
            "ORDER BY reviewed_at DESC LIMIT 1",
            (row[0],),
        ).fetchone()
        if live is None or live[0] != row[2]:
            raise ValueError(
                "this revision edits a summary that is no longer the live one; reject it, "
                "and the next weekly run will revise the summary now shown"
            )
    if decision == "approve":
        conn.execute(
            "UPDATE feed_summary SET state = 'superseded' "
            "WHERE model_version_id = %s AND state = 'approved'",
            (row[0],),
        )
    conn.execute(
        "UPDATE feed_summary SET state = %s, reviewed_at = now(), review_note = %s WHERE id = %s",
        ("approved" if decision == "approve" else "rejected", note, summary_id),
    )
    conn.commit()
    return {"id": summary_id, "state": "approved" if decision == "approve" else "rejected"}


def _cited(conn, model: dict, ids: list[str]) -> dict[str, dict]:
    """Each cited report as the page shows it: date, paraphrase, source."""
    if not ids:
        return {}
    from judge.config import evidence_feed_settings

    reports = {d: es for d, es in by_report(model_entries(conn, model)).items() if d in set(ids)}
    embeds = {
        d: {"outcome": o, "url": u}
        for d, o, u in conn.execute(
            "SELECT document_id, outcome, url FROM feed_embed WHERE document_id = ANY(%s)",
            (ids,),
        ).fetchall()
    }
    # THE FEED'S RULE FOR A CURRENT PARAPHRASE (2026-10-23, #558 review): the
    # current prompt version, written from the excerpts the report has now. An
    # approved summary's citation shows "not paraphrased yet" rather than a
    # paraphrase the feed itself has stopped showing.
    version = evidence_feed_settings()["paraphrase"]["prompt_version"]
    texts = {
        d: text
        for d, text, digest in conn.execute(
            "SELECT document_id, text, excerpts_digest FROM feed_paraphrase "
            "WHERE model_version_id = %s AND prompt_version = %s AND document_id = ANY(%s)",
            (model["key"], version, ids),
        ).fetchall()
        if d in reports and digest == excerpts_digest(reports[d])
    }
    # THE FEED'S WITHHELD RULE TOO (2026-10-23, #558 second review): if the
    # terms ever stop the feed drawing on a withheld source, an approved
    # summary's citation of it shows no text and no source either - the feed
    # (items.feed) and its summary must never disagree about what is shown.
    out = {}
    for d in ids:
        es = reports.get(d)
        if es is None:
            # Cited when drafted, since declined or removed: said, not hidden.
            out[d] = {"id": d, "gone": True}
            continue
        hidden = publication.feed_hides(es[0]["source"])
        out[d] = {
            "id": d,
            "gone": False,
            "posted_at": es[0]["posted_at"].isoformat() if es[0]["posted_at"] else None,
            "polarity": report_polarity(es),
            "paraphrase": None if hidden else texts.get(d),
            "source": {"kind": "withheld"} if hidden else cite_source(es[0], embeds.get(d)),
        }
    return out


def _shape(conn, model: dict, row) -> dict:
    (sid, paragraphs, flags, used, available, newest, served, generated, reviewed, note, state,
     parent_id, changes) = row
    ids = list(dict.fromkeys(c for p in paragraphs for c in p["cites"]))
    return {
        "id": sid,
        "state": state,
        # A REVISION'S EDITS, for Admin to show before against after
        # (FeedSummaryPanel.jsx); None for a first draft.
        "parent_id": parent_id,
        "changes": changes,
        "paragraphs": paragraphs,
        "flags": flags,
        "reports_used": used,
        "reports_available": available,
        "newest_report_at": newest.isoformat() if newest else None,
        "proposer_model": served,
        "generated_at": generated.isoformat(),
        "reviewed_at": reviewed.isoformat() if reviewed else None,
        "review_note": note,
        "cited": _cited(conn, model, ids),
    }


def current(conn, model_id: str) -> dict:
    """What the public Summary tab shows: the approved summary, or only its state.
    Refuses an unseated model (items.NotSeated), as the feed does."""
    model = resolve_model(conn, model_id)
    require_seated(conn, model)
    row = conn.execute(
        "SELECT id, paragraphs, flags, reports_used, reports_available, newest_report_at, "
        "       proposer_model, generated_at, reviewed_at, review_note, state, parent_id, changes "
        "FROM feed_summary WHERE model_version_id = %s AND state = 'approved' "
        "ORDER BY reviewed_at DESC LIMIT 1",
        (model["key"],),
    ).fetchone()
    if row is None:
        waiting = conn.execute(
            "SELECT count(*) FROM feed_summary WHERE model_version_id = %s AND state = 'pending'",
            (model["key"],),
        ).fetchone()[0]
        return {"model": model, "summary": None, "state": "awaiting_review" if waiting else "none"}
    out = _shape(conn, model, row)
    # NEWER THAN THE SUMMARY: reports posted after the newest one it was written
    # from, counted now - so a reader knows what it does not cover.
    newest = row[5]
    since = 0
    if newest is not None:
        since = sum(
            1
            for es in by_report(model_entries(conn, model)).values()
            if es[0]["posted_at"] and es[0]["posted_at"] > newest
        )
    # THE PUBLIC TAB'S FIELDS ONLY (rule 9, #558 review). Flags and the review
    # note are the reviewer's; the proposer model, when it was drafted and the
    # row id are Admin's (listing()) - the tab says "drafted by a language model
    # and approved by a person on <reviewed_at>" and reads none of them.
    # A REVISION SAYS SO (2026-10-27): "revised and approved by a person on
    # <reviewed_at>" (Evidence.jsx). Which points changed is Admin's.
    out["revised"] = out["parent_id"] is not None
    for admin_only in ("flags", "review_note", "proposer_model", "generated_at", "id",
                       "parent_id", "changes"):
        out.pop(admin_only, None)
    return {"model": model, "summary": out, "state": "approved", "reports_since": since}


def listing(conn, state: str = "pending") -> list[dict]:
    """Admin: drafts in one state, each with what it cites, flags first."""
    if state not in ("pending", "approved", "rejected", "superseded"):
        raise ValueError("state must be pending, approved, rejected or superseded")
    rows = conn.execute(
        "SELECT model_version_id, id, paragraphs, flags, reports_used, reports_available, "
        "       newest_report_at, proposer_model, generated_at, reviewed_at, review_note, state, "
        "       parent_id, changes "
        "FROM feed_summary WHERE state = %s "
        "ORDER BY generated_at DESC LIMIT 100",
        (state,),
    ).fetchall()
    out = []
    for r in rows:
        model = resolve_model(conn, r[0])
        out.append({"model": model, **_shape(conn, model, r[1:])})
    return out


def counts(conn) -> dict[str, int]:
    return dict(conn.execute("SELECT state, count(*) FROM feed_summary GROUP BY 1").fetchall())


def models_due(conn, paraphrase_version: str, min_reports: int) -> list[dict[str, Any]]:
    """Models with enough paraphrased reports and nothing newer than their last
    draft: no draft yet, or a report posted after the newest one drafted from.

    A REJECTED DRAFT COUNTS AS DRAFTED (2026-10-23, #558 review). Counting only
    pending and approved meant a rejected model was drafted again on every
    `--summaries --apply` run, up to `summary.attempts` paid calls each time,
    from the same reports a person had just turned down. It is drafted again
    once a newer report arrives.

    A REFUSED DRAFT COUNTS TOO (2026-10-27): it is a `feed_summary_attempt`
    row, so the schedule does not pay for the same refusal every week.

    AN APPROVED OR WAITING SUMMARY IS NEVER REDRAFTED HERE (2026-10-27). An
    approved one is revised point by point (judge/feed/revise.py); a waiting one
    waits for its reviewer. A full redraft of a live summary is a person's
    choice: `build_evidence_feed.py --summaries --model <id> --apply`.

    SEATED MODELS ONLY (2026-10-23, #558 second review). The public summary
    refuses a model the models page does not list (`require_seated`), so a
    draft for one could never be shown - only paid for and queued in Admin."""
    seated = seated_keys(conn)
    rows = conn.execute(
        "SELECT fp.model_version_id, count(*), max(d.created_at) FROM feed_paraphrase fp "
        "JOIN document d ON d.id = fp.document_id WHERE fp.prompt_version = %s "
        "GROUP BY 1 HAVING count(*) >= %s",
        (paraphrase_version, min_reports),
    ).fetchall()
    live = {
        k
        for (k,) in conn.execute(
            "SELECT DISTINCT model_version_id FROM feed_summary "
            "WHERE state IN ('pending', 'approved')"
        ).fetchall()
    }
    last = dict(
        conn.execute(
            "SELECT model_version_id, max(newest_report_at) FROM ("
            "  SELECT model_version_id, newest_report_at FROM feed_summary "
            "  UNION ALL "
            "  SELECT model_version_id, newest_report_at FROM feed_summary_attempt "
            "  WHERE kind = 'draft') t GROUP BY 1"
        ).fetchall()
    )
    due = []
    for key, n, newest in rows:
        if key not in seated or key in live:
            continue
        drafted: datetime | None = last.get(key)
        if drafted is None or (newest is not None and newest > drafted):
            due.append({"model_key": key, "paraphrased": n})
    return due


def record_attempt(conn, model_key: str, kind: str, outcome: str, *, parent_id: str | None,
                   summary_id: str | None, newest: datetime | None, considered: int,
                   detail: str | None, prompt_version: str, run_id: str) -> None:
    """One `feed_summary_attempt` row: what was tried, on what, and how it ended."""
    conn.execute(
        "INSERT INTO feed_summary_attempt (model_version_id, kind, outcome, parent_id, "
        "  summary_id, newest_report_at, reports_considered, detail, prompt_version, run_id) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (model_key, kind, outcome, parent_id, summary_id, newest, considered, detail,
         prompt_version, run_id),
    )


def attempts(conn, limit: int = 40) -> list[dict]:
    """Admin: the newest attempts, so a refused draft or a week with nothing
    to change is visible, not just absent (rule 4)."""
    rows = conn.execute(
        "SELECT a.model_version_id, coalesce(v.display_name, v.canonical_id, v.id), a.kind, "
        "       a.outcome, a.summary_id, a.reports_considered, a.detail, a.attempted_at "
        "FROM feed_summary_attempt a JOIN model_version v ON v.id = a.model_version_id "
        "ORDER BY a.attempted_at DESC, a.id DESC LIMIT %s",
        (limit,),
    ).fetchall()
    return [
        {"model_key": k, "model_label": label, "kind": kind, "outcome": outcome,
         "summary_id": sid, "reports_considered": n, "detail": detail,
         "attempted_at": at.isoformat()}
        for k, label, kind, outcome, sid, n, detail, at in rows
    ]
