"""The weekly revision of an approved summary: point by point, never a rewrite.

Agreed with anooj, 2026-10-27, before this was built: the summary page should
improve slowly, not churn. So once a model has an approved summary, the
schedule never drafts a new one (judge/feed/summary.py `models_due`). Once a
week, if reports were posted since, a model is shown the approved summary
sentence by sentence and ONLY the new reports, and may propose a few edits:

    replace   a point the new reports contradict, or now state more clearly
    add       a point the new reports make evident, into the paragraph it fits
    new_paragraph   a theme the summary lacks - only within the page's limits

or none at all, which is the expected answer most weeks. An edit is worth
making only when a point has become more evident and relevant; "it doesn't
mean to rewrite the whole 2 para". A point stays until newer evidence replaces
or contradicts it - nothing is retired for its age (rule 4: silence is not
criticism).

CODE APPLIES THE EDITS, NOT THE MODEL. The model names a sentence and supplies
the new text; this module splices it in. So every sentence not edited is the
approved sentence byte for byte - a property of the construction, not a check
that could be talked round. Every edit must cite at least one of the new
reports, so an edit is always new evidence rather than restyling, and every
changed paragraph goes through the same checks as a draft (judge/feed/checks.py):
numbers only from what it cites, no copied wording, no count of people, the
same word and paragraph limits - so the page never grows past them.

A PERSON APPROVES EVERY REVISION (rule 2: a model may propose, never decide).
It is stored `pending` with its `changes` - each point before and after, the
reports it adds, and why - and Admin shows them side by side. A revision of a
summary that is no longer the live one cannot be approved (summary.review).

EVERY ATTEMPT IS REMEMBERED (`feed_summary_attempt`): stored, refused, or no
change. A model is not asked again until the weekly interval has passed AND a
report newer than the last attempt considered has arrived - so neither a
refusal nor a quiet week is paid for twice (Parvathi's #558 condition).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from psycopg.types.json import Jsonb

from judge.feed import checks
from judge.feed.items import resolve_model, seated_keys
from judge.feed.llm import BudgetSpent, FeedModelUnavailable, call_tool
from judge.feed.summary import _paraphrased_reports, record_attempt

SYSTEM = """\
You keep a one-page summary of what engineers have reported about {model} up to
date. A person approved the summary below. Since then, new reports have been
posted. Your job is to decide whether any of them make a point MORE EVIDENT or
add a RELEVANT point the summary lacks - and if so, to propose the smallest
edits that put it on the page.

WORK IN THIS ORDER.
1. Read the summary sentence by sentence. Then list in `uncovered` every theme
   the new reports raise that NO sentence of the summary states - a theme is
   covered only if a sentence on the page says it, not if it is merely nearby.
   Give each theme the ids of the new reports that raise it.
2. A theme raised by more than one new report has become evident: add it, with
   `add` into the paragraph it fits or `new_paragraph` if none fits.
3. A new report that contradicts a sentence, or states its point more clearly,
   is a `replace` of that one sentence.
4. Only if nothing in steps 2 and 3 applies, change nothing and say why in one
   sentence. That is a normal answer when the new reports repeat the page.
Never restyle, reorder, shorten or polish a sentence the new reports do not
bear on. Never retire a point because it is old: a point stays until newer
reports replace or contradict it.

You may make at most {max_changes} changes, each one of these:
- replace P<n>.<s>: swap that one sentence for a better-supported version,
  because the new reports contradict it or state it more clearly.
- add P<n>.<s>: insert a new point after that sentence, in the paragraph whose
  theme it belongs to. P<n>.0 inserts it at the start of paragraph <n>.
- new_paragraph P<n>: a new paragraph after paragraph <n> (P0 for the start),
  only for a theme the summary does not cover at all. The page may have at most
  {max_paragraphs} paragraphs.
A change's text is one point: at most {max_sentences} sentences. Every change
cites the ids of the NEW reports it rests on (N1 to N{last}) - at least one,
and only new ones. Ids go ONLY in `cites`, never in the text. Give each change
a short reason for the reviewer: what the new reports show, and why it belongs.

The whole page must stay under {max_words} words; it has {current_words} now.

The same rules as the summary itself:
- Do not say how many reports or people said something, and avoid words that
  claim a quantity (most, many, few, majority, everyone, nobody).
- Write no measured figures: no prices, speeds, scores, sizes, percentages,
  context lengths or counts. Describe them in words ("faster", "a long context").
- Model names and version numbers are fine, written exactly as the reports
  write them. Any other digit must appear in a report you cite for that change.
- No dates, months or years ("earlier", "more recently" instead), and no number
  words (two, three, dozens, hundreds, thousands).
- Never reuse more than five words in a row from any report.
- Report, do not judge. No authors, handles, communities, websites, platforms,
  links, quotation marks, headings, bullet points or recommendations.

Return your answer through the submit_revision tool.
"""

TOOL = {
    "type": "function",
    "function": {
        "name": "submit_revision",
        "description": "The proposed edits to the approved summary, or none.",
        "parameters": {
            "type": "object",
            "properties": {
                "uncovered": {
                    "type": "array",
                    "description": "Themes the new reports raise that no sentence of the "
                    "summary states, each with the new report ids that raise it.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "theme": {"type": "string"},
                            "reports": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["theme", "reports"],
                    },
                },
                "changes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "op": {"type": "string", "enum": ["replace", "add", "new_paragraph"]},
                            "at": {"type": "string", "description": 'e.g. "P2.3", "P1.0" or "P2"'},
                            "text": {"type": "string"},
                            "cites": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": 'New report ids, e.g. ["N2"]',
                            },
                            "reason": {"type": "string"},
                        },
                        "required": ["op", "at", "text", "cites", "reason"],
                    },
                },
                "no_change_reason": {
                    "type": "string",
                    "description": "When changes is empty: why the new reports change nothing.",
                },
            },
            "required": ["uncovered", "changes"],
        },
    },
}


def _evident(uncovered: Any, nid: dict) -> list[str]:
    """Themes the model itself listed as missing from the page AND raised by
    more than one real new report - the ones step 2 says must be added.

    A CONSISTENCY CHECK ON THE MODEL'S OWN ANSWER, not a judgement of content
    (rule 2): code counts the valid ids under each theme the model named. The
    first live runs (2026-10-27) answered "no change" for a summary trimmed to
    one paragraph, claiming cost and speed were covered when no sentence said
    so; listing first, then being held to the list, is what this enforces."""
    out = []
    for u in uncovered if isinstance(uncovered, list) else []:
        if not isinstance(u, dict):
            continue
        ids = {_new_id(r) for r in (u.get("reports") or [])} & set(nid)
        if len(ids) > 1:
            out.append(" ".join(str(u.get("theme") or "").split()) or "unnamed theme")
    return out

#: The sentence split judge/glossary.py uses: a full stop, question or
#: exclamation mark, a space, then a capital, digit or opening quote - so
#: "e.g. a" and "v1.5" stay inside a sentence.
_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
_POINT = re.compile(r"^P(\d+)\.(\d+)$")
_PARA = re.compile(r"^P(\d+)$")


def sentences(text: str) -> list[str]:
    t = re.sub(r"\b(e\.g|i\.e|vs|etc)\.", lambda m: m.group(0).replace(".", "․"), text.strip())
    return [s.replace("․", ".") for s in _SPLIT.split(t) if s.strip()]


def _new_id(c: Any) -> str:
    """`3`, `n3` and `N3` are the same citation - a formatting slip, as
    summary._with_ids says of R-ids. Anything else is left for the check."""
    t = str(c).strip()
    if t.isdigit():
        return f"N{t}"
    if t[:1] == "n" and t[1:].isdigit():
        return f"N{t[1:]}"
    return t


def _live(conn, model_key: str):
    return conn.execute(
        "SELECT id, paragraphs, reports_used, newest_report_at, reviewed_at FROM feed_summary "
        "WHERE model_version_id = %s AND state = 'approved' ORDER BY reviewed_at DESC LIMIT 1",
        (model_key,),
    ).fetchone()


def _cut(conn, live) -> datetime | None:
    """Reports posted after this are new: the approved summary's newest, or a
    later revision attempt's on the same summary (stored, refused or no change),
    so the same reports are not shown to the model twice."""
    sid, _, _, newest, _ = live
    row = conn.execute(
        "SELECT max(newest_report_at) FROM feed_summary_attempt "
        "WHERE kind = 'revision' AND parent_id = %s",
        (sid,),
    ).fetchone()
    seen = [t for t in (newest, row[0] if row else None) if t is not None]
    return max(seen) if seen else None


def revisions_due(
    conn, paraphrase_version: str, rev: dict, *, now: datetime | None = None
) -> tuple[list[dict], list[dict]]:
    """`(models due a revision, models skipped with the reason)`.

    Due: seated, an approved summary and no waiting one, no attempt of any kind
    in the last `revision.every_days`, and at least `revision.min_new_reports`
    paraphrased reports posted since the cut. Skipped models are listed, not
    dropped, so a run report says why a model was not revised (rule 4)."""
    now = now or datetime.now(UTC)
    seated = seated_keys(conn)
    approved = [
        k
        for (k,) in conn.execute(
            "SELECT DISTINCT model_version_id FROM feed_summary WHERE state = 'approved'"
        ).fetchall()
    ]
    waiting = {
        k
        for (k,) in conn.execute(
            "SELECT DISTINCT model_version_id FROM feed_summary WHERE state = 'pending'"
        ).fetchall()
    }
    last = dict(
        conn.execute(
            "SELECT model_version_id, max(attempted_at) FROM feed_summary_attempt GROUP BY 1"
        ).fetchall()
    )
    due, skipped = [], []
    for key in sorted(approved):
        if key not in seated:
            continue
        if key in waiting:
            skipped.append({"model_key": key, "why": "a summary is waiting for review"})
            continue
        # HALF A DAY OF SLACK: a weekly cron starts when GitHub gets to it (the
        # nightly fetch began 3.5 h late on 2026-10-26), so "exactly 7 days" read
        # strictly would skip a model every other week.
        if last.get(key) and now - last[key] < timedelta(days=rev["every_days"], hours=-12):
            skipped.append(
                {"model_key": key, "why": f"attempted within the last {rev['every_days']} days"}
            )
            continue
        live = _live(conn, key)
        cut = _cut(conn, live)
        if cut is None:
            # RULE 6: no date to count from is not "everything is new".
            skipped.append(
                {
                    "model_key": key,
                    "why": "the approved summary records no newest report date; redraft it by hand",
                }
            )
            continue
        (n,) = conn.execute(
            "SELECT count(*) FROM feed_paraphrase fp JOIN document d ON d.id = fp.document_id "
            "WHERE fp.model_version_id = %s AND fp.prompt_version = %s AND d.created_at > %s",
            (key, paraphrase_version, cut),
        ).fetchone()
        if n < rev["min_new_reports"]:
            skipped.append(
                {
                    "model_key": key,
                    "why": f"{n} new paraphrased reports since the "
                    f"last look; {rev['min_new_reports']} needed",
                }
            )
            continue
        due.append({"model_key": key, "new_reports": n})
    return due, skipped


def _user_message(
    label: str,
    paragraphs: list[list[str]],
    para_cites: list[list[str]],
    reports_by_doc: dict[str, dict],
    new: list[dict],
    approved_on,
) -> str:
    out = [
        f"Model: {label}",
        "",
        f"THE APPROVED SUMMARY (approved {approved_on.date().isoformat()}), sentence by sentence:",
    ]
    for i, (sents, cites) in enumerate(zip(paragraphs, para_cites, strict=True), 1):
        dated = [
            reports_by_doc[c]["posted_at"]
            for c in cites
            if c in reports_by_doc and reports_by_doc[c]["posted_at"]
        ]
        newest = max(dated).date().isoformat() if dated else "not recorded"
        out.append(f"P{i} (rests on {len(cites)} reports, the newest posted {newest}):")
        out.extend(f"  P{i}.{j} {s}" for j, s in enumerate(sents, 1))
    out += ["", f"NEW REPORTS posted since, N1 to N{len(new)}, newest first:", ""]
    for k, r in enumerate(new, 1):
        when = r["posted_at"].date().isoformat() if r["posted_at"] else "date not recorded"
        out.append(
            f"[N{k}] {when} · {', '.join(r['tags'])} · reaction: {r['polarity']}\n"
            f"{r['paraphrase']}\n"
        )
    return "\n".join(out)


class _Refused(ValueError):
    pass


def _apply(
    changes: list[dict],
    paragraphs: list[list[str]],
    para_texts: list[str],
    para_cites: list[list[str]],
    nid: dict[str, dict],
    rev: dict,
    max_paragraphs: int,
) -> tuple[list[dict], list[dict], set[int]]:
    """`(new paragraphs, the change records, which new paragraphs changed)`.
    Raises _Refused naming the first problem."""
    if len(changes) > rev["max_changes"]:
        raise _Refused(f"{len(changes)} changes; at most {rev['max_changes']}")
    replace: dict[tuple[int, int], dict] = {}
    add: dict[tuple[int, int], list[dict]] = {}
    new_par: dict[int, list[dict]] = {}
    records = []
    for n, ch in enumerate(changes, 1):
        op, at = ch.get("op"), str(ch.get("at") or "").strip().upper()
        text = " ".join(str(ch.get("text") or "").split())
        reason = " ".join(str(ch.get("reason") or "").split())
        cites = list(dict.fromkeys(_new_id(c) for c in (ch.get("cites") or [])))
        if not text:
            raise _Refused(f"change {n} has no text")
        if not reason:
            raise _Refused(f"change {n} gives no reason")
        if len(sentences(text)) > rev["max_point_sentences"]:
            raise _Refused(
                f"change {n} is {len(sentences(text))} sentences; a point is at most "
                f"{rev['max_point_sentences']}"
            )
        if not cites:
            raise _Refused(f"change {n} cites no new report")
        unknown = [c for c in cites if c not in nid]
        if unknown:
            raise _Refused(f"change {n} cites {', '.join(unknown[:3])}, which is not a new report")
        docs = [nid[c]["id"] for c in cites]
        if op in ("replace", "add"):
            m = _POINT.match(at)
            if not m:
                raise _Refused(f"change {n}: {op} needs a sentence like P2.3, not {at!r}")
            i, j = int(m.group(1)), int(m.group(2))
            if not 1 <= i <= len(paragraphs) or not (0 if op == "add" else 1) <= j <= len(
                paragraphs[i - 1]
            ):
                raise _Refused(f"change {n}: there is no {at}")
            if op == "replace":
                if (i, j) in replace:
                    raise _Refused(f"change {n} replaces {at} a second time")
                replace[(i, j)] = {"text": text, "docs": docs}
                before = paragraphs[i - 1][j - 1]
            else:
                add.setdefault((i, j), []).append({"text": text, "docs": docs})
                before = None
        elif op == "new_paragraph":
            m = _PARA.match(at)
            if not m or not 0 <= int(m.group(1)) <= len(paragraphs):
                raise _Refused(
                    f"change {n}: new_paragraph needs P0 to P{len(paragraphs)}, not {at!r}"
                )
            new_par.setdefault(int(m.group(1)), []).append({"text": text, "docs": docs})
            before = None
        else:
            raise _Refused(f"change {n}: {op!r} is not replace, add or new_paragraph")
        records.append(
            {"op": op, "at": at, "before": before, "after": text, "cites": docs, "reason": reason}
        )

    out: list[dict] = []
    changed: set[int] = set()

    def emit_new(after: int) -> None:
        for p in new_par.get(after, []):
            changed.add(len(out))
            out.append({"text": p["text"], "cites": list(p["docs"])})

    emit_new(0)
    for i, sents in enumerate(paragraphs, 1):
        touched = any(k[0] == i for k in replace) or any(k[0] == i for k in add)
        if not touched:
            # BYTE FOR BYTE: an untouched paragraph is the approved text itself.
            out.append({"text": para_texts[i - 1], "cites": list(para_cites[i - 1])})
        else:
            parts, docs = [], list(para_cites[i - 1])
            for a in add.get((i, 0), []):
                parts.append(a["text"])
                docs += a["docs"]
            for j, s in enumerate(sents, 1):
                r = replace.get((i, j))
                parts.append(r["text"] if r else s)
                if r:
                    docs += r["docs"]
                for a in add.get((i, j), []):
                    parts.append(a["text"])
                    docs += a["docs"]
            changed.add(len(out))
            out.append({"text": " ".join(parts), "cites": list(dict.fromkeys(docs))})
        emit_new(i)
    if len(out) > max_paragraphs:
        raise _Refused(f"{len(out)} paragraphs; at most {max_paragraphs}")
    return out, records, changed


def revise(
    conn,
    model_id: str,
    s_cfg: dict,
    rev: dict,
    paraphrase_version: str,
    *,
    call: Callable = call_tool,
    commit: bool = True,
) -> dict:
    """Propose a revision of the model's approved summary. Returns
    `{"outcome": "stored" | "refused" | "no_change" | "not_due", ...}`."""
    model = resolve_model(conn, model_id)
    live = _live(conn, model["key"])
    if live is None:
        return {"outcome": "not_due", "model": model, "why": "no approved summary to revise"}
    if conn.execute(
        "SELECT 1 FROM feed_summary WHERE model_version_id = %s AND state = 'pending'",
        (model["key"],),
    ).fetchone():
        return {"outcome": "not_due", "model": model, "why": "a summary is waiting for review"}
    parent_id, approved_paragraphs, parent_used, _, approved_on = live
    cut = _cut(conn, live)
    if cut is None:
        return {
            "outcome": "not_due",
            "model": model,
            "why": "the approved summary records no newest report date",
        }
    reports = _paraphrased_reports(conn, model, paraphrase_version)
    new = [r for r in reports if r["posted_at"] and r["posted_at"] > cut][: s_cfg["max_reports"]]
    if len(new) < rev["min_new_reports"]:
        return {
            "outcome": "not_due",
            "model": model,
            "why": f"{len(new)} new paraphrased reports; {rev['min_new_reports']} needed",
        }

    by_doc = {r["id"]: r for r in reports}
    para_texts = [p["text"] for p in approved_paragraphs]
    para_cites = [list(p["cites"]) for p in approved_paragraphs]
    paragraphs = [sentences(t) for t in para_texts]
    nid = {f"N{k}": r for k, r in enumerate(new, 1)}
    # What a changed paragraph's numbers and wording are checked against: every
    # report it cites, old or new. An old citation whose paraphrase is no
    # longer current is checked against the paraphrase it was approved with.
    sources: dict[str, list[str]] = {d: [r["paraphrase"]] for d, r in by_doc.items()}
    excerpts: dict[str, list[str]] = {
        d: [e["quote"] or "" for e in r["entries"]] for d, r in by_doc.items()
    }
    stale = [c for cites in para_cites for c in cites if c not in sources]
    if stale:
        for d, text in conn.execute(
            "SELECT DISTINCT ON (document_id) document_id, text FROM feed_paraphrase "
            "WHERE model_version_id = %s AND document_id = ANY(%s) "
            "ORDER BY document_id, generated_at DESC",
            (model["key"], stale),
        ).fetchall():
            sources[d] = [text]
        for d in stale:
            sources.setdefault(d, [])

    current_words = sum(len(checks.words(t)) for t in para_texts)
    system = SYSTEM.format(
        model=model["label"],
        max_changes=rev["max_changes"],
        max_paragraphs=s_cfg["max_paragraphs"],
        max_sentences=rev["max_point_sentences"],
        last=len(new),
        max_words=s_cfg["max_words"],
        current_words=current_words,
    )
    user = _user_message(model["label"], paragraphs, para_cites, by_doc, new, approved_on)
    run_id = f"feed_r_{uuid.uuid4().hex[:12]}"
    newest = max(r["posted_at"] for r in new)
    reason, reasons, answered = None, [], False
    result = None
    for _ in range(rev["attempts"]):
        message = (
            user
            if reason is None
            else (
                user
                + f"\n\nYour previous answer was refused: {reason}. Answer again within the rules."
            )
        )
        try:
            args, served = call(
                model=s_cfg["model"],
                system=system,
                user=message,
                tool=TOOL,
                run_id=run_id,
                max_tokens=4 * s_cfg["max_words"] + 800,
                reasoning_effort=s_cfg["reasoning_effort"],
            )
        except BudgetSpent as e:
            reasons.append(str(e))
            reason = str(e)
            break
        except FeedModelUnavailable as e:
            reason = str(e)
            reasons.append(reason)
            continue
        answered = True
        changes = [c for c in (args.get("changes") or []) if isinstance(c, dict)]
        evident = _evident(args.get("uncovered"), nid)
        if not changes and evident:
            # HELD TO ITS OWN LIST (`_evident`): asked again, with the themes.
            reason = (
                "you listed themes no sentence covers, each raised by more than one new "
                f"report ({'; '.join(evident[:4])}), and proposed no change - add the "
                "strongest of them"
            )
            reasons.append(reason)
            continue
        if not changes:
            why = " ".join(str(args.get("no_change_reason") or "").split()) or "no reason given"
            record_attempt(
                conn,
                model["key"],
                "revision",
                "no_change",
                parent_id=parent_id,
                summary_id=None,
                newest=newest,
                considered=len(new),
                detail=why,
                prompt_version=rev["prompt_version"],
                run_id=run_id,
            )
            if commit:
                conn.commit()
            return {
                "outcome": "no_change",
                "model": model,
                "why": why,
                "run_id": run_id,
                "new_reports": len(new),
            }
        try:
            body, records, changed = _apply(
                changes, paragraphs, para_texts, para_cites, nid, rev, s_cfg["max_paragraphs"]
            )
            total = sum(len(checks.words(p["text"])) for p in body)
            if total > s_cfg["max_words"]:
                raise _Refused(f"{total} words, over the {s_cfg['max_words']}-word page")
            # The checks a draft passes, on every paragraph the edits touched.
            idx = sorted(changed)
            problem, flags = checks.summary_problems(
                [body[i] for i in idx],
                sources,
                model["label"],
                excerpts=excerpts,
                max_words=s_cfg["max_words"],
                max_paragraphs=s_cfg["max_paragraphs"],
                max_copied_words=s_cfg["max_copied_words"],
                quantity_words=s_cfg["quantity_words"],
            )
            if problem:
                n = re.match(r"paragraph (\d+)", problem)
                raise _Refused(
                    re.sub(r"^paragraph \d+", f"paragraph {idx[int(n.group(1)) - 1] + 1}", problem)
                    if n
                    else problem
                )
        except _Refused as e:
            reason = str(e)
            reasons.append(reason)
            continue
        for f in flags:
            f["paragraph"] = idx[f["paragraph"] - 1] + 1
        result = (body, records, flags, served)
        break

    if result is None:
        if answered:
            record_attempt(
                conn,
                model["key"],
                "revision",
                "refused",
                parent_id=parent_id,
                summary_id=None,
                newest=newest,
                considered=len(new),
                detail="; then ".join(reasons),
                prompt_version=rev["prompt_version"],
                run_id=run_id,
            )
            if commit:
                conn.commit()
        return {
            "outcome": "refused",
            "model": model,
            "refused": "; then ".join(reasons),
            "run_id": run_id,
            "recorded": answered,
        }

    body, records, flags, served = result
    summary_id = f"fs_{uuid.uuid4().hex}"
    # THE DENOMINATOR (rule 7): the parent's newest `reports_used`, plus the new
    # reports, which are all newer than any of them.
    used = min(parent_used + len(new), len(reports))
    conn.execute(
        "INSERT INTO feed_summary (id, model_version_id, prompt_version, paragraphs, flags, "
        "  reports_used, reports_available, newest_report_at, proposer_model, run_id, "
        "  parent_id, changes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            summary_id,
            model["key"],
            rev["prompt_version"],
            Jsonb(body),
            Jsonb(flags),
            used,
            len(reports),
            newest,
            served,
            run_id,
            parent_id,
            Jsonb(records),
        ),
    )
    record_attempt(
        conn,
        model["key"],
        "revision",
        "stored",
        parent_id=parent_id,
        summary_id=summary_id,
        newest=newest,
        considered=len(new),
        detail=None,
        prompt_version=rev["prompt_version"],
        run_id=run_id,
    )
    if commit:
        conn.commit()
    return {
        "outcome": "stored",
        "id": summary_id,
        "model": model,
        "changes": records,
        "flags": flags,
        "run_id": run_id,
        "new_reports": len(new),
    }
