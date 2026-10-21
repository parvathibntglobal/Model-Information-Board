"""The quiz's question bank: general questions about how language models work,
DRAFTED by a model and APPROVED by a person (2026-10-15).

    draft()     one call per topic; each question is checked in code and
                stored `pending`
    review()    a person approves or rejects one question
    pending() / counts()    what Admin -> Quiz shows
    approved()  what the daily quiz draws from (judge/blog_live.py `quiz`)

AN LLM MAY PROPOSE, IT MAY NEVER DECIDE. Nothing drafted here reaches a page
until a person approves it - the blog's pattern (rule 2's third caller,
agreed 2026-10-06). This drafter is a fourth caller of the same shape and
records its spend as its own stage, `quiz`, outside the extraction cap.

WHAT CODE CHECKS, AND WHAT IT CANNOT. Code refuses a draft with the wrong
SHAPE: not four distinct options, an answer that is not one of them, "all of
the above", a price, a question too short or too long, or one already in the
bank. Whether the answer is RIGHT is the reviewer's job - code cannot tell,
and a model checking a model is what rule 1 refuses. So the Admin list shows
the explanation beside each question: it is what the reviewer checks against.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from typing import Any

import httpx

from judge import spend_ledger
from judge.config import quiz_drafter_settings

DIFFICULTIES = ("easy", "medium", "hard")

SYSTEM = """\
You write multiple-choice questions that teach how large language models work,
in the style of Google's Machine Learning Crash Course LLM quiz and common LLM
engineering interview quizzes.

Rules for every question:
- It tests a CONCEPT an engineer should understand: what something is, why it
  is done, what it trades off, or what happens if it is changed.
- It is true for language models in general. Do not ask about one vendor's
  product, prices, release dates, benchmark scores or anything that changes
  month to month. Naming a well-known technique or paper (LoRA, RLHF, BERT,
  "Attention Is All You Need") is fine.
- Exactly four options. Exactly one is correct. The three wrong options are
  plausible to someone who half-knows the topic - a common misconception, a
  neighbouring concept, or a reversed effect - and are about the same length
  and style as the right one.
- Never "all of the above", "none of the above" or "both A and B".
- The explanation says in one or two sentences why the right answer is right
  and why the most tempting wrong one is wrong.
- Vary difficulty: some easy, some medium, some hard.
"""

TOOL = {
    "type": "function",
    "function": {
        "name": "submit_questions",
        "description": "Submit the drafted questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "options": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 4,
                                "maxItems": 4,
                            },
                            "answer_index": {"type": "integer", "minimum": 0, "maximum": 3},
                            "explanation": {"type": "string"},
                            "difficulty": {"type": "string", "enum": list(DIFFICULTIES)},
                        },
                        "required": [
                            "question",
                            "options",
                            "answer_index",
                            "explanation",
                            "difficulty",
                        ],
                    },
                }
            },
            "required": ["questions"],
        },
    },
}

_BANNED = re.compile(r"\b(all|none) of the above\b|\bboth [a-d] and [a-d]\b", re.I)
_PRICE = re.compile(r"\$\s?\d")
_NORM = re.compile(r"[^a-z0-9]+")


class DrafterUnavailable(RuntimeError):
    """The model could not be called, or answered with something unusable."""


def _norm(s: str) -> str:
    return _NORM.sub(" ", (s or "").lower()).strip()


def question_id(question: str) -> str:
    return "qq_" + hashlib.sha256(_norm(question).encode("utf-8")).hexdigest()[:24]


def problem(q: Any) -> str | None:
    """Why a drafted question cannot be stored, or None. Shape only - never
    whether the answer is right; a person decides that."""
    if not isinstance(q, dict):
        return "not an object"
    text, opts = q.get("question"), q.get("options")
    ans, why, diff = q.get("answer_index"), q.get("explanation"), q.get("difficulty")
    if not isinstance(text, str) or not 15 <= len(text.strip()) <= 300:
        return "question missing or not 15-300 characters"
    if (
        not isinstance(opts, list)
        or len(opts) != 4
        or not all(isinstance(o, str) and o.strip() for o in opts)
    ):
        return "not exactly four non-empty options"
    if len({_norm(o) for o in opts}) != 4:
        return "two options say the same thing"
    if any(len(o) > 200 for o in opts):
        return "an option is over 200 characters"
    if isinstance(ans, bool) or not isinstance(ans, int) or not 0 <= ans <= 3:
        return "answer is not one of the four options"
    if not isinstance(why, str) or not 10 <= len(why.strip()) <= 600:
        return "explanation missing or not 10-600 characters"
    if diff not in DIFFICULTIES:
        return "difficulty is not easy, medium or hard"
    if any(_BANNED.search(s) for s in [text, *opts]):
        return "uses 'all/none of the above'"
    if any(_PRICE.search(s) for s in [text, *opts]):
        return "names a price, which changes"
    return None


def _call(model: str, topic: str, n: int, avoid: list[str]) -> tuple[list[Any], dict]:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    base = os.getenv("OPENROUTER_BASE_URL", "").strip().rstrip("/")
    if not key or not base:
        raise DrafterUnavailable("OPENROUTER_API_KEY and OPENROUTER_BASE_URL must both be set")
    user = f"Topic: {topic}\n\nWrite {n} questions on this topic." + (
        "\n\nThe bank already has these questions on it; do not repeat or reword them:\n- "
        + "\n- ".join(avoid)
        if avoid
        else ""
    )
    try:
        r = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user},
                ],
                "tools": [TOOL],
                "tool_choice": {"type": "function", "function": {"name": "submit_questions"}},
                "usage": {"include": True},
                "temperature": 0.7,
                "max_tokens": 6000,
            },
            timeout=httpx.Timeout(150.0, connect=10.0),
        )
    except httpx.HTTPError as e:
        raise DrafterUnavailable(f"OpenRouter could not be reached: {e}") from e
    if r.status_code != 200:
        raise DrafterUnavailable(f"OpenRouter HTTP {r.status_code}: {r.text[:300]!r}")
    body = r.json()
    usage = body.get("usage") or {}
    served = body.get("model") or ""
    # THE SPEND IS RECORDED BEFORE THE ANSWER IS JUDGED: an unusable answer is
    # still billed. OpenRouter's reported cost, not a rate held here.
    spend_ledger.record(
        stage=spend_ledger.STAGE_QUIZ,
        model=served,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        reported=True,
        reported_usd=usage.get("cost"),
    )
    if not served.startswith(model):
        raise DrafterUnavailable(
            f"asked for {model}, OpenRouter served {served!r}; refusing the draft"
        )
    calls = ((body.get("choices") or [{}])[0].get("message") or {}).get("tool_calls") or []
    if not calls:
        raise DrafterUnavailable("the model answered without the question tool")
    try:
        args = json.loads(calls[0]["function"]["arguments"])
    except (KeyError, ValueError) as e:
        raise DrafterUnavailable(f"the tool arguments were not JSON: {e}") from e
    return list(args.get("questions") or []), {"served": served, "usage": usage}


def draft(conn, topic: str, n: int | None = None) -> dict[str, Any]:
    """Draft questions on one topic and store the usable ones as `pending`.

    Returns what happened, counted: proposed, stored, already in the bank, and
    refused by reason (rule 4: a refusal is reported, not dropped quietly)."""
    cfg = quiz_drafter_settings()
    if topic not in cfg["topics"]:
        raise ValueError(f"{topic!r} is not one of the topics in contract/blog_live.yaml")
    n = n or cfg["per_call"]
    avoid = [
        r[0]
        for r in conn.execute(
            "SELECT question FROM quiz_question WHERE topic = %s AND state <> 'rejected' "
            "ORDER BY generated_at DESC LIMIT 40",
            (topic,),
        ).fetchall()
    ]
    drafted, meta = _call(cfg["model"], topic, n, avoid)
    run_id = f"qr_{uuid.uuid4().hex[:12]}"
    stored, duplicate, refused = 0, 0, {}
    for q in drafted:
        why = problem(q)
        if why:
            refused[why] = refused.get(why, 0) + 1
            continue
        cur = conn.execute(
            "INSERT INTO quiz_question (id, topic, difficulty, question, options, answer_index, "
            " explanation, proposer_model, run_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (id) DO NOTHING",
            (
                question_id(q["question"]),
                topic,
                q["difficulty"],
                q["question"].strip(),
                json.dumps([o.strip() for o in q["options"]]),
                q["answer_index"],
                q["explanation"].strip(),
                meta["served"],
                run_id,
            ),
        )
        if cur.rowcount:
            stored += 1
        else:
            duplicate += 1
    conn.commit()
    return {
        "run_id": run_id,
        "topic": topic,
        "model": meta["served"],
        "proposed": len(drafted),
        "stored": stored,
        "already_in_bank": duplicate,
        "refused": refused,
        "cost_usd": (meta["usage"] or {}).get("cost"),
    }


def review(conn, qid: str, decision: str, note: str | None = None) -> dict[str, Any] | None:
    """A person's decision on one question. Approving or rejecting again is
    allowed - a misclick is undone by deciding again. None for an unknown id."""
    if decision not in ("approved", "rejected", "pending"):
        raise ValueError("decision must be approved, rejected or pending")
    row = conn.execute(
        "UPDATE quiz_question SET state = %s, review_note = %s, "
        " reviewed_at = CASE WHEN %s = 'pending' THEN NULL ELSE now() END "
        "WHERE id = %s RETURNING id, state",
        (decision, (note or "").strip() or None, decision, qid),
    ).fetchone()
    conn.commit()
    return {"id": row[0], "state": row[1]} if row else None


def _row(r) -> dict[str, Any]:
    qid, topic, diff, question, options, ans, why, state, model, gen, note = r
    return {
        "id": qid,
        "topic": topic,
        "difficulty": diff,
        "question": question,
        "options": options if isinstance(options, list) else json.loads(options),
        "answer_index": ans,
        "explanation": why,
        "state": state,
        "model": model,
        "generated_at": gen.isoformat() if gen else None,
        "review_note": note,
    }


# THE COLUMNS ARE WRITTEN OUT IN EACH QUERY, not shared through a constant:
# the column audit (tests/test_column_states.py) reads SQL literals, and a
# column list it cannot see reads as columns nobody reads.


def listing(conn, state: str = "pending", limit: int = 200) -> list[dict[str, Any]]:
    return [
        _row(r)
        for r in conn.execute(
            "SELECT id, topic, difficulty, question, options, answer_index, explanation, state, "
            "       proposer_model, generated_at, review_note "
            "FROM quiz_question WHERE state = %s "
            "ORDER BY generated_at DESC, id LIMIT %s",
            (state, limit),
        ).fetchall()
    ]


def counts(conn) -> dict[str, Any]:
    by_state = dict(conn.execute("SELECT state, count(*) FROM quiz_question GROUP BY 1").fetchall())
    by_topic = {
        t: dict(zip(("approved", "pending"), (a, p), strict=True))
        for t, a, p in conn.execute(
            "SELECT topic, count(*) FILTER (WHERE state = 'approved'), "
            "       count(*) FILTER (WHERE state = 'pending') FROM quiz_question GROUP BY 1"
        ).fetchall()
    }
    spent = conn.execute(
        "SELECT count(*), coalesce(sum(usd), 0), count(*) FILTER (WHERE unpriced) "
        "FROM spend_ledger WHERE stage = 'quiz'"
    ).fetchone()
    return {
        "approved": by_state.get("approved", 0),
        "pending": by_state.get("pending", 0),
        "rejected": by_state.get("rejected", 0),
        "by_topic": by_topic,
        "topics": quiz_drafter_settings()["topics"],
        "model": quiz_drafter_settings()["model"],
        "spend": {"calls": spent[0], "usd": float(spent[1]), "unpriced_calls": spent[2]},
    }


def approved(conn) -> list[dict[str, Any]]:
    return [
        _row(r)
        for r in conn.execute(
            "SELECT id, topic, difficulty, question, options, answer_index, explanation, state, "
            "       proposer_model, generated_at, review_note "
            "FROM quiz_question WHERE state = 'approved' ORDER BY id"
        ).fetchall()
    ]
