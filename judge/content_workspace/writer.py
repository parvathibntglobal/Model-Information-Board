"""The AI writer (phase 2): a model PROPOSES a post; code checks it; a person
decides.

Runs only for a platform whose `ai_writer_allowed` is true (seeded for X and
LinkedIn). The governing rule is the board's: an LLM may propose, it may never
decide. So:

- The model sees MATERIAL (the draft's suggestion and its evidence, the topic's
  angle, the person's own text and instructions), the platform's philosophy
  and rules as they are in the workspace now (edits included), and LINKS.
- Code checks the answer and stores a failing one as `refused`, with reasons,
  never corrected: every number in digits must appear in MATERIAL; any URL or
  bare domain must be one of LINKS; no handle.
- A proposal that passes is fit-checked like any draft and shown beside the
  draft. Nothing reaches the draft until a person uses it (`use`), and the
  draft is then marked AI-assisted. Posting stays a person's act, by hand.

Every call is a `cw_writer_run` row, written before the answer is judged (an
unusable answer is still paid for), at the cost OpenRouter reports. A cost
that is not reported is NULL, and the day's total says how many calls that was
(rule 6). Calls stop once `writer.daily_budget_usd` is spent today (UTC).

Not checked: whether the prose is faithful to MATERIAL beyond its numbers and
links. That is what the person reading it is for.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from psycopg.types.json import Jsonb

from judge.content_workspace import checks, settings, store

PROMPT_FILE = Path(__file__).parent / "config" / "writer_prompt.md"
# One playbook per platform that allows the writer, appended to the shared
# prompt: X and LinkedIn are written differently (config/writer_playbooks/).
PLAYBOOKS = Path(__file__).parent / "config" / "writer_playbooks"
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
# A period's post counts by polarity, as recommend._counts_line writes them.
POST_SPLIT = re.compile(r"posts with a positive report (\d[\d,]*), negative (\d[\d,]*), "
                        r"neutral (\d[\d,]*)")
BARE_DOMAIN = re.compile(r"(?<![\w@/.-])[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|ai|io|net|org|dev|"
                         r"app|co|xyz|news|tech)\b", re.I)

TOOL = {
    "type": "function",
    "function": {
        "name": "write_post",
        "description": "Propose the post's text for a person to edit.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The post. Parts separated by a "
                                                          "line holding only ---."},
                "title": {"type": ["string", "null"],
                          "description": "An article's headline, or the short post that goes "
                                         "with a document carousel; otherwise null."},
                "first_comment": {"type": ["string", "null"],
                                  "description": "The first comment (LinkedIn) or first reply "
                                                 "(X): where the model page link goes. Null "
                                                 "if none."},
                "editor_note": {"type": "string",
                                "description": "One or two sentences for the editor."},
            },
            "required": ["text", "title", "first_comment", "editor_note"],
        },
    },
}


class WriterUnavailable(RuntimeError):
    """The call could not be made or its answer could not be read."""


# ── material ─────────────────────────────────────────────────────────────────


def _site_url(path: str, s: dict[str, Any]) -> str:
    base = (os.environ.get(s["site"]["hosts_env"]) or "").strip().rstrip("/")
    return f"{base}{path}" if base else path


def material(d: dict[str, Any], p: dict[str, Any], s: dict[str, Any],
             instructions: str | None) -> dict[str, Any]:
    sug = d.get("suggestion") or {}
    kind = s["topic_kinds"].get(d.get("topic_kind") or "", {})
    links = []
    for link in sug.get("links") or []:
        links.append({"label": link["label"],
                      "href": link.get("url") or _site_url(link["path"], s)})
    return {
        "topic": {"kind": d.get("topic_kind"), "label": kind.get("label"),
                  "angle": " ".join((kind.get("angle") or "").split()) or None},
        "suggestion": {k: sug.get(k) for k in ("headline", "detail", "date", "evidence",
                                                "price", "sample")}
                      if sug else None,
        # The board's paraphrased reports, with no source link (recommend._proof).
        "proof": sug.get("proof") or [],
        "persons_text": {"title": d.get("title"), "body": d.get("body") or None},
        "instructions": (instructions or "").strip() or None,
        "links": links,
    }


def _source_text(m: dict[str, Any]) -> str:
    """Everything a number or a link in the proposal may be copied from."""
    return json.dumps(m, ensure_ascii=False)


def _numbers(text: str) -> set[str]:
    """Numbers as values: thousands commas dropped, and an integer's leading
    zeros dropped, so a date written 2026-10-05 in MATERIAL allows "Oct 5".
    A decimal keeps its digits ("0.40" is not "0.4": a shortened decimal is
    a different figure as written)."""
    out = set()
    for n in NUMBER.findall(text):
        n = n.replace(",", "")
        if "." not in n:
            n = n.lstrip("0") or "0"
        out.add(n)
    return out


def check(proposal: dict[str, Any], m: dict[str, Any]) -> list[str]:
    """Reasons to refuse the proposal; empty when it passes."""
    reasons = []
    text = (f"{proposal.get('title') or ''}\n{proposal.get('text') or ''}\n"
            f"{proposal.get('first_comment') or ''}")
    if not (proposal.get("text") or "").strip():
        return ["the proposal has no text"]
    source = _source_text(m)
    # A hashtag's digits are part of a tag (#ClaudeOpus55), not a figure; the
    # platform's hashtags rule judges the tags themselves.
    unknown = sorted(_numbers(checks.HASHTAG.sub(" ", text)) - _numbers(source),
                     key=lambda n: (len(n), n))
    if unknown:
        reasons.append(f"numbers not in the material: {', '.join(unknown[:8])}")
    allowed = [link["href"] for link in m["links"]]
    urls = checks.URL.findall(text)
    stray = [u for u in urls if not any(u.rstrip(".,)") == a or u.startswith(a) for a in allowed)]
    if stray:
        reasons.append(f"links not given to it: {', '.join(stray[:4])}")
    no_urls = checks.URL.sub(" ", text)
    domains = [m_.group(0) for m_ in BARE_DOMAIN.finditer(no_urls)
               if m_.group(0).lower() not in source.lower()]
    if domains:
        reasons.append(f"domains not in the material: {', '.join(domains[:4])}")
    handles = sorted(set(checks.HANDLE.findall(text)))
    if handles:
        reasons.append(f"names handles: {', '.join(handles[:4])}")
    # Proof is restated, never quoted: a quoted span taken from a report reads
    # as the author's own words, which it is not (the board's paraphrase is).
    proof_text = " ".join(p.get("text") or "" for p in m.get("proof") or []).lower()
    quoted = [q for q in checks.QUOTED.findall(text)
              if len(q.split()) >= 3 and q.strip().lower() in proof_text]
    if quoted:
        reasons.append(f"quotes a report instead of restating it: \"{quoted[0][:60]}\"")
    # A period's polarity counts are posts WITH such a report (one post can
    # carry two), so "70 positive reports" or "positive 70" misstates them as
    # reports or as a split of the total. Only those exact counts, next to
    # their own polarity word, are refused: a topic's report counts in the
    # material ("Reasoning (15 positive, 4 negative)") are reports and pass.
    split = _post_split_misread(text, source)
    if split:
        reasons.append(f"post counts written as reports or a split: \"{split}\" "
                       "(write \"70 of the 85 posts had a positive report\")")
    return reasons


WEEK = re.compile(r"\bweek\s*(\d+)\b", re.I)


def shape(proposal: dict[str, Any], platform_key: str, fmt: str,
          s: dict[str, Any]) -> list[str]:
    """Reasons a proposal has the wrong SHAPE for its platform and format
    (config `writer.shape`). A platform/format with no entry has no shape
    rule, which is a choice, not a default."""
    rule = ((s["writer"]["shape"].get(platform_key) or {}).get(fmt)) or {}
    reasons = []
    if "max_weeks_named" in rule:
        weeks = sorted({int(n) for n in WEEK.findall(proposal.get("text") or "")})
        if len(weeks) > rule["max_weeks_named"]:
            reasons.append(
                f"walks through weeks {', '.join(map(str, weeks))} like a report; tell one "
                f"story with at most {rule['max_weeks_named']} of them (the rest is for the "
                "carousel and the model page)")
    return reasons


def _post_split_misread(text: str, source: str) -> str | None:
    for m_ in POST_SPLIT.finditer(source):
        for pol, n in zip(("positive", "negative", "neutral"), m_.groups(), strict=True):
            n = re.escape(n)
            hit = re.search(rf"\b{n}\s+{pol}\b|\b{pol}\s*:?\s*{n}\b", text, re.I)
            if hit:
                return hit.group(0)
    return None


# ── the call ─────────────────────────────────────────────────────────────────


def call_model(*, model: str, system: str, user: str, max_tokens: int, temperature: float,
               reasoning_effort: str) -> tuple[dict | None, dict[str, Any]]:
    """One forced tool call. Returns (tool arguments or None, call facts). The
    facts (served model, tokens, cost, error) are returned even when the answer
    is unusable, so the call is recorded either way."""
    import httpx

    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    base = os.getenv("OPENROUTER_BASE_URL", "").strip().rstrip("/")
    if not key or not base:
        raise WriterUnavailable("OPENROUTER_API_KEY and OPENROUTER_BASE_URL must both be set")
    try:
        r = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "tools": [TOOL],
                "tool_choice": {"type": "function", "function": {"name": "write_post"}},
                "usage": {"include": True},
                "temperature": temperature,
                "max_tokens": max_tokens,
                "reasoning": {"effort": reasoning_effort},
            },
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
    except httpx.HTTPError as e:
        raise WriterUnavailable(f"OpenRouter could not be reached: {e}") from e
    if r.status_code != 200:
        raise WriterUnavailable(f"OpenRouter HTTP {r.status_code}: {r.text[:300]!r}")
    body = r.json()
    usage = body.get("usage") or {}
    facts = {"served": body.get("model") or None, "input_tokens": usage.get("prompt_tokens"),
             "output_tokens": usage.get("completion_tokens"), "cost": usage.get("cost"),
             "error": None}
    if not (facts["served"] or "").startswith(model):
        facts["error"] = f"asked for {model}, OpenRouter served {facts['served']!r}"
        return None, facts
    calls = ((body.get("choices") or [{}])[0].get("message") or {}).get("tool_calls") or []
    try:
        args = json.loads(calls[0]["function"]["arguments"])
    except (IndexError, KeyError, ValueError) as e:
        facts["error"] = f"no usable write_post answer: {e}"
        return None, facts
    if not isinstance(args, dict):
        facts["error"] = "the tool arguments were not an object"
        return None, facts
    return args, facts


def prompt(platform_key: str) -> str:
    """The shared prompt, then the platform's playbook. A platform that allows
    the writer but has no playbook is refused rather than written for with
    the shared rules alone (rule 12: a missing playbook is not a default)."""
    book = PLAYBOOKS / f"{platform_key}.md"
    if not book.exists():
        raise store.WorkspaceRequestError(
            f"no writer playbook for {platform_key!r} (config/writer_playbooks/"
            f"{platform_key}.md); add one before the writer drafts for it", 409)
    return (PROMPT_FILE.read_text(encoding="utf-8").rstrip() + "\n\n"
            + book.read_text(encoding="utf-8"))


# ── spend ────────────────────────────────────────────────────────────────────


#: Proposals written in a Claude Code session and ingested (`ingest`) carry
#: this prefix on their model. They are not metered per call (the session is
#: billed as a whole), so they are counted apart, never as "cost not reported".
CLAUDE_CODE = "claude-code/"


def spent_today(conn: Any) -> dict[str, Any]:
    usd, calls, unreported, by_hand = conn.execute(
        "SELECT coalesce(sum(cost_usd), 0),"
        " count(*) FILTER (WHERE model_asked NOT LIKE %s),"
        " count(*) FILTER (WHERE cost_usd IS NULL AND model_served IS NOT NULL"
        "                  AND model_asked NOT LIKE %s),"
        " count(*) FILTER (WHERE model_asked LIKE %s)"
        " FROM cw_writer_run"
        " WHERE created_at >= (date_trunc('day', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC')",
        (CLAUDE_CODE + "%",) * 3,
    ).fetchone()
    return {"usd": float(usd), "calls": calls, "unreported_cost_calls": unreported,
            "claude_code_proposals": by_hand}


def status(conn: Any, s: dict[str, Any]) -> dict[str, Any]:
    w = s["writer"]
    platforms = [p["key"] for p in store.platforms(conn) if p["ai_writer_allowed"]]
    return {"api_enabled": w["api_enabled"], "model": w["model"],
            "models": {k: model_for(k, s) for k in platforms},
            "daily_budget_usd": w["daily_budget_usd"],
            "today": spent_today(conn), "platforms": platforms}


def model_for(platform_key: str, s: dict[str, Any]) -> str:
    """The platform's own model when config names one, else the writer's."""
    w = s["writer"]
    return w["model_by_platform"].get(platform_key) or w["model"]


# ── propose, list, use ───────────────────────────────────────────────────────


RUN_COLUMNS = ("id", "draft_id", "platform_key", "format", "instructions", "model_asked",
               "model_served", "input_tokens", "output_tokens", "cost_usd", "state", "reasons",
               "proposal", "fit", "requested_by", "created_at", "used_at", "used_by")


def _run(row: tuple) -> dict[str, Any]:
    r = dict(zip(RUN_COLUMNS, row, strict=True))
    r["cost_usd"] = float(r["cost_usd"]) if r["cost_usd"] is not None else None
    for k in ("created_at", "used_at"):
        r[k] = r[k].isoformat() if r[k] else None
    return r


def runs(conn: Any, draft_id: int) -> list[dict[str, Any]]:
    store.draft(conn, draft_id)
    return [_run(r) for r in conn.execute(
        f"SELECT {', '.join(RUN_COLUMNS)} FROM cw_writer_run WHERE draft_id = %s"
        " ORDER BY created_at DESC, id DESC", (draft_id,)).fetchall()]


def propose(conn: Any, draft_id: int, *, instructions: str | None, by: str | None,
            s: dict[str, Any] | None = None,
            call: Callable[..., tuple[dict | None, dict]] = call_model) -> dict[str, Any]:
    s = s or settings.load()
    w = s["writer"]
    if not w["api_enabled"]:
        raise store.WorkspaceRequestError(
            "The API writer is off for now: proposals are written in Claude Code. Ask "
            f"Claude to draft draft {draft_id} (python -m judge.content_workspace material "
            f"{draft_id}, then ingest).", 409)
    d, p, notes, m, system, request = _prepare(conn, draft_id, instructions, s)
    today = spent_today(conn)
    if today["usd"] >= w["daily_budget_usd"]:
        raise store.WorkspaceRequestError(
            f"today's writer budget of ${w['daily_budget_usd']:.2f} is spent "
            f"(${today['usd']:.4f} over {today['calls']} calls)", 429)
    run = None
    for attempt in range(w["attempts"]):
        if attempt and spent_today(conn)["usd"] >= w["daily_budget_usd"]:
            break  # the retry would start past today's budget
        run = _attempt(conn, d, p, s, notes, m, system, request, call, by)
        if run["state"] != "refused":
            break
        # One more try, told exactly what code refused and nothing else.
        request = {**request, "PREVIOUS_ATTEMPT": {
            "text": run["proposal"]["text"], "first_comment": run["proposal"]["first_comment"],
            "refused_because": run["reasons"],
            "instruction": "Rewrite it fixing only what was refused; keep everything else.",
        }}
    return run


def _prepare(conn: Any, draft_id: int, instructions: str | None,
             s: dict[str, Any]) -> tuple:
    """Everything a writer is given for one draft: the shared prompt and the
    platform's playbook (`system`), and the request (philosophy, rules,
    limits, MATERIAL, LINKS). The same for the API writer and Claude Code."""
    d = store.draft(conn, draft_id)
    p = store.platform(conn, d["platform_key"])
    if not p["ai_writer_allowed"]:
        raise store.WorkspaceRequestError(
            f"{p['name']} does not allow an AI writer; posts there are written by a person")
    notes = store.notes(conn, p["key"])
    m = material(d, p, s, instructions)
    system = prompt(p["key"])
    rules = [n for n in notes["rule"] if checks.applies(n, d["format"])]
    request = {
        "platform": p["name"], "format": d["format"],
        "philosophy": [n["body"] for n in notes["philosophy"]],
        "rules": [n["body"] for n in rules],
        # The rules' own limits, as numbers, so a part's length is not a guess.
        "limits": [{"check": n["check_id"], **n["params"],
                    **({"formats": n["formats"]} if n["formats"] else {})}
                   for n in rules if n["params"]],
        "MATERIAL": {k: v for k, v in m.items() if k != "links"},
        "LINKS": m["links"],
    }
    return d, p, notes, m, system, request


def _sha(system: str, request: dict) -> str:
    user = json.dumps(request, ensure_ascii=False, indent=1)
    return hashlib.sha256((system + "\n" + user).encode()).hexdigest()[:16]


def export(conn: Any, draft_id: int, instructions: str | None = None,
           s: dict[str, Any] | None = None) -> dict[str, Any]:
    """The writer's whole input for one draft, for a proposal written in
    Claude Code: the same system text, request and answer shape the API
    writer gets. `prompt_sha` ties an ingested proposal to what it was
    written from."""
    s = s or settings.load()
    d, p, _, _, system, request = _prepare(conn, draft_id, instructions, s)
    return {"draft_id": d["id"], "platform": p["key"], "format": d["format"],
            "instructions": (instructions or "").strip() or None,
            "prompt_sha": _sha(system, request), "system": system, "request": request,
            "answer_shape": TOOL["function"]["parameters"]}


def ingest(conn: Any, draft_id: int, answer: dict[str, Any], *, author: str,
           instructions: str | None = None, by: str | None = None,
           s: dict[str, Any] | None = None) -> dict[str, Any]:
    """A proposal written in Claude Code from `export`'s material, run through
    exactly the checks an API proposal gets (numbers, links, handles, quotes,
    shape, then the fit check) and recorded as a run. `author` names the model
    that wrote it (e.g. "claude-opus-5-5"). Not metered per call: cost NULL."""
    s = s or settings.load()
    d, p, notes, m, system, request = _prepare(conn, draft_id, instructions, s)
    if not isinstance(answer, dict) or not isinstance(answer.get("text"), str):
        raise store.WorkspaceRequestError("the answer is an object with at least `text`")
    label = CLAUDE_CODE + author.strip()
    facts = {"served": label, "input_tokens": None, "output_tokens": None, "cost": None,
             "error": None}
    return _judge_and_record(conn, d, p, s, notes, m, answer, facts, label,
                             _sha(system, request), by)


def _attempt(conn: Any, d: dict, p: dict, s: dict, notes: dict, m: dict, system: str,
             request: dict, call: Callable[..., tuple[dict | None, dict]],
             by: str | None) -> dict[str, Any]:
    """One model call, checked and recorded as its own run."""
    w = s["writer"]
    model = model_for(p["key"], s)
    user = json.dumps(request, ensure_ascii=False, indent=1)
    try:
        args, facts = call(model=model, system=system, user=user,
                           max_tokens=w["max_tokens"], temperature=w["temperature"],
                           reasoning_effort=w["reasoning_effort"])
    except WriterUnavailable as e:
        args, facts = None, {"served": None, "input_tokens": None, "output_tokens": None,
                             "cost": None, "error": str(e)}
    return _judge_and_record(conn, d, p, s, notes, m, args, facts, model,
                             _sha(system, request), by)


def _judge_and_record(conn: Any, d: dict, p: dict, s: dict, notes: dict, m: dict,
                      args: dict | None, facts: dict, model: str, prompt_sha: str,
                      by: str | None) -> dict[str, Any]:
    """Code decides: check a proposal, fit-check it if it passes, record it."""
    w = s["writer"]
    proposal, fit, reasons = None, None, []
    if args is None:
        state, reasons = "failed", [facts["error"]]
    else:
        def opt(key: str) -> str | None:
            return (str(args[key]).strip() or None) if args.get(key) else None

        proposal = {"text": str(args.get("text") or "").strip(), "title": opt("title"),
                    "first_comment": opt("first_comment"),
                    "editor_note": str(args.get("editor_note") or "")[: w["editor_note_max_chars"]]}
        reasons = check(proposal, m) + shape(proposal, p["key"], d["format"], s)
        state = "refused" if reasons else "proposed"
        if state == "proposed":
            as_draft = {**d, "body": proposal["text"], "title": proposal["title"] or d["title"],
                        "first_comment": proposal["first_comment"], "ai_assisted": True}
            fit = checks.run(as_draft, notes["rule"], s)
    cost = facts.get("cost")
    row = conn.execute(
        "INSERT INTO cw_writer_run (draft_id, platform_key, format, instructions, model_asked,"
        " model_served, input_tokens, output_tokens, cost_usd, state, reasons, proposal, fit,"
        " prompt_sha, requested_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        f" RETURNING {', '.join(RUN_COLUMNS)}",
        (d["id"], p["key"], d["format"], m["instructions"], model, facts.get("served"),
         facts.get("input_tokens"), facts.get("output_tokens"),
         cost if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None,
         state, Jsonb(reasons), Jsonb(proposal) if proposal else None,
         Jsonb(fit) if fit else None, prompt_sha, by),
    ).fetchone()
    return _run(row)


def use(conn: Any, run_id: int, by: str | None) -> dict[str, Any]:
    """Put a proposal into its draft, marked AI-assisted. Only a proposal that
    passed the checks can be used. The draft's previous text is kept on the
    run, so using a proposal never loses what the person wrote."""
    row = conn.execute(
        f"SELECT {', '.join(RUN_COLUMNS)} FROM cw_writer_run WHERE id = %s", (run_id,)).fetchone()
    if row is None:
        raise store.WorkspaceRequestError(f"no proposal {run_id}", 404)
    r = _run(row)
    if r["state"] != "proposed":
        raise store.WorkspaceRequestError(f"proposal {run_id} was {r['state']}; it cannot be used",
                                          409)
    before = store.draft(conn, r["draft_id"])
    changes = {"body": r["proposal"]["text"], "ai_assisted": True,
               "first_comment": r["proposal"].get("first_comment")}
    if r["proposal"].get("title"):
        changes["title"] = r["proposal"]["title"]
    d = store.update_draft(conn, r["draft_id"], changes, by)
    conn.execute(
        "UPDATE cw_writer_run SET used_at = now(), used_by = %s, replaced = %s WHERE id = %s",
        (by, Jsonb({"title": before["title"], "body": before["body"],
                    "first_comment": before["first_comment"]}), run_id))
    return d
