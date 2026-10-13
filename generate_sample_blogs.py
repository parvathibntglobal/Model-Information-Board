#!/usr/bin/env python3
"""Document-level synthesis: long-form essays written from full source threads.

Writes three essays and a hub into ``sample_blogs/``.

PIPELINE
--------
1. SELECT (read-only, STAGING_DATABASE_URL from ``.env``). For each post, rank
   the thread contexts behind verified, non-declined ``board_entry`` rows for
   the post's subject — by how many target models a thread covers, then how
   many distinct themes, then how many entries — and keep the first
   ``MAX_DOCS`` whose full text resolves in the local object store. A thread
   whose payload is not on this machine is SKIPPED AND NAMED in the run record,
   never replaced by an empty string.
2. SYNTHESISE. The full texts go to ``GEN_MODEL`` on OpenRouter in one call,
   with a forced ``publish_essay`` tool, so the reply is structured data and
   never free HTML.
3. CHECK, in code (rule 1: the proposer and the checker are different things):
   * every «fragment» and pull quote is an exact substring of the text the
     model was shown (whitespace collapsed, typographic quotes folded — nothing
     else);
   * any other quotation-marked span of three or more words is refused;
   * every number in the prose appears in the source text or the fact sheet;
   * no telemetry, no counting of people or reports, no reference to "the
     sources", no score out of 10 or 100.
   A failing draft goes back to the model with the violations, at most
   ``MAX_REPAIRS`` times. Still failing = the build stops (rule 12).
4. RENDER. HTML, the price table and every structural element are built here
   from the checked fields; the model never writes markup.

Every response — passing or not — is saved under ``_blog_synthesis/`` (the
model is nondeterministic and an unsaved draw is gone). ``--reuse`` re-renders
the latest passing draw without calling anything.

⚠ RULE 2. This script calls a language model outside ``judge/extract/`` and
``judge/ask/``, and the model writes prose about model capability. That is a
local experimental draft, not a pipeline stage, and it cannot reach a public
page without that being agreed in ``contract/`` first. Pages carry ``noindex``.
Never touches git.
"""

from __future__ import annotations

import argparse
import copy
import html
import json
import math
import os
import re
import sys
import unicodedata
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import psycopg
import yaml
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from collect.rawstore import RawStore  # noqa: E402
from collect.rawstore_reader import RawStoreReader  # noqa: E402
from judge.publication import (  # noqa: E402
    derived_posts_may_draw_on_withheld,
    withheld_sources,
)

OUT = ROOT / "sample_blogs"
RUNS = ROOT / "_blog_synthesis"
TODAY = date.today()
ORG = "Model Information Board"

#: The generation models this script may call, and for each the names
#: OpenRouter may report as having served it, EXACTLY. A prefix test would also
#: pass `-0731` and `-vision-exp`, which are different models. Not read from the
#: environment: the model is chosen with --model, from this table only.
#:
#: deepseek: the dated form is what OpenRouter's generation record showed on
#:   2026-10-01; the bare slug is what the stream's `model` field carried.
#: gemini-2.5-flash-lite: compared on one post 2026-10-01 and retired the same
#:   day (no pass; best draft 3 violations). Its records stay in _blog_synthesis/.
#: gpt-6-luna: the generator since 2026-10-01, after a one-post comparison
#:   (reasoning post: passed in 2 calls; Flash and Gemini did not pass). Served
#:   name observed as `openai/gpt-6-luna` on every call that day.
GEN_MODELS = {
    "deepseek/deepseek-v4-flash": {"deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-flash-20260423"},
    "openai/gpt-6-luna": {"openai/gpt-6-luna"},
}
GEN_MODEL = "openai/gpt-6-luna"
#: Models that do not accept `temperature` (OpenRouter's supported_parameters,
#: read 2026-10-01). Sent to them it is either refused or silently dropped, and
#: neither should be how we find out - the Claude 5 sampling break is the same
#: shape. So the request omits it rather than relying on the router.
NO_TEMPERATURE = {"openai/gpt-6-luna"}
TEMPERATURE = 0.4
MAX_DOCS = 10
#: Per-document ceiling. The largest thread measured while writing this was
#: 18,177 characters (2026-10-01), so this truncates nothing seen so far; a
#: truncation is recorded in the run file when it happens.
MAX_DOC_CHARS = 24_000
MAX_REPAIRS = 5
MIN_WORDS = 1_800

OPUS, SONNET = "anthropic/claude-opus-5", "anthropic/claude-sonnet-5"

POSTS = [
    {
        "key": "opus",
        "file": "anthropic-claude-opus-5-report.html",
        "kicker": "Model deep dive",
        "subject": [OPUS],
        "where": "mv.canonical_id = ANY(%(subject)s)",
        "facts": [OPUS, SONNET, "anthropic/claude-opus-4.8"],
        "tags": ["Claude Opus 5", "Agents", "Migration", "Cost"],
        "brief": (
            "SUBJECT: Claude Opus 5 in production.\n"
            "ANGLE: what it is actually like to build on Opus 5 — the integration and migration "
            "breakages, how it behaves as an agent and orchestrator, where its judgement earns its "
            "price and where it does not, and what the economics mean for architecture.\n"
            "SCENARIO MATRIX: title it along the lines of 'Where Opus 5 fits'. Each row is a "
            "production scenario, the behavioural trade-off Opus 5 shows there, the mitigation, and "
            "the route (which model or configuration to use).\n"
            "DECISION TREE: the question an architect asks before routing a task to Opus 5; each "
            "branch is a condition and the resulting choice."
        ),
    },
    {
        "key": "compare",
        "file": "anthropic-claude-sonnet-5-vs-anthropic-claude-opus-5.html",
        "kicker": "Routing guide",
        "subject": [SONNET, OPUS],
        "where": "mv.canonical_id = ANY(%(subject)s)",
        "facts": [SONNET, OPUS, "anthropic/claude-haiku-4.5"],
        "tags": ["Claude Sonnet 5", "Claude Opus 5", "Routing", "Cost"],
        "brief": (
            "SUBJECT: Claude Sonnet 5 versus Claude Opus 5 — a routing guide.\n"
            "ANGLE: when the cheaper tier is the right engineering choice, where it fails and why, "
            "what the two share (so switching does not fix it), and how to build a router with "
            "escalation between them.\n"
            "SCENARIO MATRIX: title it 'When to use Sonnet 5 vs Opus 5'. Each row is a production "
            "scenario, the behavioural trade-off between the two, the mitigation, and the route "
            "('Sonnet 5', 'Opus 5', or a conditional route).\n"
            "DECISION TREE: the routing decision for an incoming task; each branch is a condition "
            "and the model it routes to."
        ),
    },
    {
        "key": "reasoning",
        "file": "capability-reasoning.html",
        "kicker": "Capability analysis",
        "subject": None,
        "where": ("be.section = 'capability' AND "
                  "coalesce(nullif(be.ruling_target,''), be.slug) = 'reasoning'"),
        "facts": [],
        "tags": ["Reasoning", "Effort settings", "Latency", "Cost"],
        "brief": (
            "SUBJECT: reasoning in production across current models.\n"
            "ANGLE: how reasoning depth and effort settings behave in real systems — where more "
            "thinking helps, where it hurts, what it costs in latency and tokens, and how to set an "
            "effort policy.\n"
            "SCENARIO MATRIX: title it along the lines of 'Choosing a reasoning budget'. Each row is "
            "a production scenario, the behavioural trade-off of more or less reasoning there, the "
            "mitigation, and the route (model and/or effort level).\n"
            "DECISION TREE: how to choose an effort level for a task; each branch is a condition and "
            "the resulting setting."
        ),
    },
]


class BuildError(RuntimeError):
    pass


class ProviderTransient(BuildError):
    """The router or an upstream having a bad minute - 429, 5xx, a dropped
    stream. Retried with the SAME request; never counted as a repair round.
    Measured 2026-10-01: Azure returned 504 'Upstream idle timeout exceeded'
    mid-stream and, before this existed, failed a whole post."""


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def clean(name: str) -> str:
    return name.split(": ", 1)[1] if ": " in (name or "") else (name or "")


def env() -> dict[str, str]:
    vals = {}
    for raw in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = raw.lstrip("﻿").strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    # THE PROCESS ENVIRONMENT WINS, as it does for `collect.config` (dotenv
    # never overrides a set variable). Until 2026-10-05 this read the file
    # only, so a launcher that pointed RAW_STORE_PATH at the shared store was
    # ignored and a worktree's `.env` (`./raw_store`, relative) opened an
    # almost-empty local store: the planner resolved nothing and planned
    # 0 posts with no error - the Blogs page button included.
    vals.update({k: os.environ[k] for k in vals if k in os.environ})
    for k in ("RAW_STORE_PATH", "BLOG_POSTS_DIR", "DATABASE_URL", "STAGING_DATABASE_URL"):
        if k in os.environ:
            vals[k] = os.environ[k]
    return vals


# ── 1 · selection (read-only) ────────────────────────────────────────────────

def _public_thread_sql(thread_col: str) -> str:
    """A SQL condition on `thread_col`: may a draft draw on this thread?

    DECIDED BY `contract/publication.yaml` `derived_posts.may_draw_on_withheld`.
    True (anooj, 2026-10-05): derived posts may be written from Reddit, X and
    arXiv threads like any other, so this returns `TRUE` and selects nothing
    out. A draft still carries no link, handle or platform name - the export and
    banned-phrase checks refuse those whatever this says.

    False: a thread with ANY member from a withheld source - or of unknown
    source - is excluded whole, because its replies are the same platform's
    material as its post. Applies whatever PUBLICATION_VIEW says, because blogs
    are public by design. The sources are then embedded as literals, so each
    must be a plain identifier; anything else raises rather than reaching SQL.
    """
    if derived_posts_may_draw_on_withheld():
        return "TRUE"
    names = withheld_sources()
    for n in names:
        if not re.fullmatch(r"[a-z0-9_-]+", n):
            raise BuildError(f"contract/publication.yaml: {n!r} is not a plain source id")
    listed = ", ".join(f"'{n}'" for n in names)
    return (f"NOT EXISTS (SELECT 1 FROM thread_context ptc "
            f"JOIN document pd ON pd.id = ANY(ptc.member_document_ids) "
            f"WHERE ptc.id = {thread_col} AND (pd.source IS NULL OR pd.source IN ({listed})))")


SELECT_THREADS = """
SELECT tc.id, tc.flattened_text_ref, max(d.source) AS source,
       count(DISTINCT be.model_version_id) AS models,
       count(DISTINCT coalesce(nullif(be.ruling_target,''), be.slug)) AS themes,
       count(DISTINCT be.id) AS entries,
       count(DISTINCT be.id) FILTER (WHERE be.polarity = 'negative') AS negatives,
       count(DISTINCT be.id) FILTER (WHERE be.polarity = 'positive') AS positives,
       max(d.created_at) AS newest
  FROM board_entry be
  JOIN claim c          ON c.id = be.claim_id
  JOIN thread_context tc ON tc.id = c.thread_context_id
  JOIN document d       ON d.id = c.document_id
  JOIN model_version mv ON mv.id = be.model_version_id
 WHERE be.quote_verified AND coalesce(be.ruling,'') <> 'declined' AND {where}
   AND {public}
 GROUP BY tc.id, tc.flattened_text_ref
 ORDER BY models DESC, entries DESC, themes DESC, newest DESC NULLS LAST, tc.id
 LIMIT 500"""

FACT_MODELS = """
SELECT mv.canonical_id
  FROM board_entry be JOIN claim c ON c.id = be.claim_id
  JOIN model_version mv ON mv.id = be.model_version_id
 WHERE c.thread_context_id = ANY(%s) AND be.quote_verified
   AND coalesce(be.ruling,'') <> 'declined'
 GROUP BY mv.canonical_id ORDER BY count(*) DESC, mv.canonical_id LIMIT 8"""


def _selection_cfg() -> dict:
    sel = load_formats()["planner"].get("doc_selection")
    if not sel:
        raise BuildError("blog_formats.yaml planner.doc_selection is missing")
    return sel


def rank_threads(rows: list[dict], sel: dict) -> tuple[list[dict], dict]:
    """Candidate threads in relevance order, and what was set aside.

    RELEVANCE, NOT BREADTH (2026-10-13). The order used to put a thread's
    count of distinct THEMES ahead of its count of entries about the subject,
    so two Hacker News threads with 2 entries each - passing mentions - beat
    single-model articles with 8 to 14. Now: threads naming more of the
    subject's models first (both, for a head-to-head), then the most entries
    about the subject, then themes, then the most recent. A thread with fewer
    than `min_entries` is a passing mention and is set aside - unless that
    leaves fewer than `min_threads`, which relaxes the floor and says so.
    """
    floor = int(sel["min_entries"])
    strong = [r for r in rows if r["entries"] >= floor]
    relaxed = len(strong) < int(sel["min_threads"])
    pool = rows if relaxed else strong

    def key(r):
        newest = r.get("newest")
        return (-r["models"], -r["entries"], -r["themes"],
                -(newest.timestamp() if newest else 0), r["id"])

    return sorted(pool, key=key), {"candidates": len(rows), "passing_mentions_set_aside":
                                   0 if relaxed else len(rows) - len(strong),
                                   "min_entries": floor, "floor_relaxed": relaxed}


def select_documents(cur, post, reader) -> tuple[list[dict], list[dict]]:
    sel = _selection_cfg()
    cur.execute(SELECT_THREADS.format(where=post["where"],
                                      public=_public_thread_sql("tc.id")),
                {"subject": post.get("subject"), **post.get("params", {})})
    ranked, summary = rank_threads(cur.fetchall(), sel)
    per_post, need_neg = int(sel["per_post"]), int(sel["disagreement_threads"])
    chosen, skipped, spare_neg = [], [], []

    def take(r):
        got = reader.resolve(r["flattened_text_ref"])
        if not got.text:
            skipped.append({"thread_context_id": r["id"], "outcome": str(got.outcome)})
            return None
        text = got.text
        return {"thread_context_id": r["id"], "source": r["source"], "chars": len(text),
                "truncated": len(text) > MAX_DOC_CHARS, "text": text[:MAX_DOC_CHARS],
                "why": {k: r[k] for k in ("models", "entries", "themes", "negatives", "positives")}}

    for r in ranked:
        if len(chosen) == per_post:
            if r["negatives"]:
                spare_neg.append(r)
            continue
        if (d := take(r)):
            chosen.append(d)
    # BOTH SIDES. Disagreement needs a thread where somebody reported a
    # problem; if too few chosen threads carry one, the lowest-ranked chosen
    # thread with none gives way to the best-ranked spare that has one.
    have = sum(1 for d in chosen if d["why"]["negatives"])
    for r in spare_neg:
        if have >= need_neg:
            break
        drop = next((k for k in range(len(chosen) - 1, -1, -1) if not chosen[k]["why"]["negatives"]), None)
        if drop is None or not (d := take(r)):
            continue
        chosen[drop] = d
        have += 1
    if len(chosen) < 5:
        raise BuildError(f"{post['key']}: only {len(chosen)} documents resolved locally; "
                         f"skipped {len(skipped)}. Refusing to synthesise from so little.")
    post["_selection"] = summary | {"chosen": len(chosen), "with_negatives": have}
    return chosen, skipped

def agreement_map(cur, post, docs) -> str:
    """Where engineers agree and where they split, per theme and model, from our
    own board entries for the chosen threads. Counts DISTINCT discussions by
    polarity. For the writer's planning only: prose never counts people."""
    ids = [d["thread_context_id"] for d in docs]
    cur.execute(
        "SELECT coalesce(nullif(be.ruling_target,''), be.slug) AS theme, max(be.name) AS name, "
        "       mv.display_name AS model, be.polarity, count(DISTINCT c.document_id) AS n "
        "  FROM board_entry be JOIN claim c ON c.id = be.claim_id "
        "  JOIN model_version mv ON mv.id = be.model_version_id "
        " WHERE c.thread_context_id = ANY(%(ids)s) AND be.quote_verified "
        "   AND coalesce(be.ruling,'') <> 'declined' AND " + post["where"] + " "
        " GROUP BY 1, 3, 4", {"ids": ids, "subject": post.get("subject"), **post.get("params", {})})
    themes: dict[str, dict] = {}
    for r in cur.fetchall():
        t = themes.setdefault(r["theme"], {"name": r["name"], "models": {}, "total": 0})
        m = t["models"].setdefault(clean(r["model"]), {"positive": 0, "negative": 0, "neutral": 0})
        m[r["polarity"] if r["polarity"] in m else "neutral"] += r["n"]
        t["total"] += r["n"]
    lines = []
    for _theme, t in sorted(themes.items(), key=lambda kv: -kv[1]["total"])[:8]:
        if t["total"] < 2:
            continue
        # NEUTRAL IS ITS OWN STATE (2026-10-13): a theme with only neutral
        # reports read "AGREE - 0 positive, 0 negative", a missing signal shown
        # as a definite one (rule 6).
        signs = {(m["positive"] > 0, m["negative"] > 0) for m in t["models"].values()}
        polar = signs - {(False, False)}
        if not polar:
            label = "NEUTRAL"
        elif any(p and n for p, n in polar) or {(True, False), (False, True)} <= polar:
            label = "SPLIT"
        else:
            label = "AGREE"
        parts = "; ".join(f"{name}: {m['positive']} positive, {m['negative']} negative, "
                          f"{m['neutral']} neutral" for name, m in t["models"].items())
        lines.append(f"- {t['name']} - {label} - {parts}")
    return "\n".join(lines)


def fact_sheet(cur, post, docs) -> list[dict]:
    cur.execute(FACT_MODELS, ([d["thread_context_id"] for d in docs],))
    ids = list(dict.fromkeys(post["facts"] + [r["canonical_id"] for r in cur.fetchall()]))
    cur.execute("""SELECT canonical_id, display_name, price_in, price_out, price_cached_read,
                          advertised_context FROM model_version WHERE canonical_id = ANY(%s)""", (ids,))
    rows = {r["canonical_id"]: r for r in cur.fetchall()}
    return [rows[i] for i in ids if i in rows]


def money(v) -> str | None:
    """A registry price as published, never rounded into a different figure.

    Was `f"${v:,.2f}"`, which turned DeepSeek V4 Flash's $0.042 into "$0.04"
    and its $0.0084 cached-input rate into "$0.01" - 19% high (2026-10-05).
    The fact sheet the model reads uses this too, so the rounding reached the
    prose. Sub-dollar prices keep up to four decimals; at least two always.
    """
    if v is None:
        return None
    x = float(v)
    if x >= 1 or x == 0:
        return f"${x:,.2f}"
    s = f"{x:.4f}".rstrip("0")
    if len(s.split(".")[1]) < 2:
        s = f"{x:.2f}"
    return "$" + s


def fact_lines(facts) -> str:
    out = []
    for f in facts:
        cached = money(f["price_cached_read"]) or "not published"
        ctx = f"{f['advertised_context']:,}" if f["advertised_context"] else "not published"
        out.append(f"- {clean(f['display_name'])}: input {money(f['price_in']) or 'not published'} "
                   f"and output {money(f['price_out']) or 'not published'} per million tokens; "
                   f"cached input {cached}; advertised context {ctx} tokens.")
    return "\n".join(out)


# ── 2 · synthesis ────────────────────────────────────────────────────────────

SYSTEM = """You are a technical blogger writing for engineers who run language models in production. You write for the Model Information Board team, as "we", and you talk to the reader as "you".

You are given full engineering discussions — issue threads, forum threads, blog posts — written by practitioners. Read every one of them completely before writing. Work out the architecture each writer was building, what they tried, what broke, why it broke, what they changed, and what they concluded. Then synthesise that into one authoritative analysis of how things actually behave, and what an architect should do about it.

VOICE
- Write like a good tech blogger, not a report generator: conversational, confident and specific, with a point of view. Short sentences: most under 15 words, none over 30. One idea per sentence. Concrete nouns and verbs. Open sections with a hook - a concrete moment, the question the reader is asking, or a claim you are about to test. No throat-clearing ("It is worth noting", "In practice", "Ultimately", "When it comes to"), and never restate the heading. No bullet points inside paragraphs.
- Take positions. Say where you agree with what engineers report and where you do not, and why: "We agree with the engineer who wrote «...», but only for ...", or "We are not convinced by «...»: the failures point the other way." Every disagreement gives its reason from the evidence. Disagree with claims, never mock people.
- Make every paragraph lively. Open many of them on a concrete moment - what a team ran, what broke, what they changed - rather than on a general claim. Vary the rhythm: put a short, punchy sentence of eight words or fewer beside the longer ones. Use active verbs and named actors (the model, the team, the harness). Prefer a fresh, exact word over the stock one; do not lean on "rather", "while" or "whether".
- Do not recite list prices in prose: the page shows them in a rate card. Mention a price only where the argument turns on it, once.
- Never refer to your inputs. Do not write "according to the sources", "the documents", "the threads", "the posts", "the material", "I read", "we read", "we reviewed", or anything that reveals a reading list. You may refer to practitioners generically ("teams migrating from earlier Claude models", "one engineer running a document pipeline").
- Never count people, reports, posts, threads or quotes ("72 developers", "a dozen reports", "most users"). No scores or ratings out of 10 or 100. No sentiment percentages.

ENGINEERS AGREE AND DISAGREE
- Use the WHERE ENGINEERS AGREE AND SPLIT map in the brief. Give at least one section to a SPLIT: set engineers' «words» from different discussions against each other, say which side the evidence favours, and where we stand. Where they AGREE, say so and whether we agree too. Quote engineers from at least 3 different discussions across the post.

FIRST PERSON
- Opinions in the first person are welcome: "we think", "we would", "we disagree", "in our view".
- First-person EXPERIENCE - "we tried", "we ran", "we tested", "we measured", "we switched", "we saw" - is allowed ONLY to retell a WHAT WE TRIED note in the brief, and the sentence must carry a figure or the wording of that note. Retell a note in plain words, never inside «». Then set an engineer's words beside it: "An engineer running a document pipeline saw the same thing: «...»." If the brief has no WHAT WE TRIED notes, write no first-person experience at all. Never invent something we did.

SEARCH - write to be found and to answer
- The brief names a PRIMARY KEYWORD. Use it naturally in the title, in the description, and in the tldr or the first paragraph, and list it first in `keywords`. Use the SECONDARY KEYWORDS where they genuinely fit. Never stuff keywords.
- The tldr is a direct answer a searcher would want quoted.
- The `faq` answers EXACTLY 3 questions people actually type into Google about this subject, phrased as they would type them; at least one names the subject (the model or the topic). The FAQ is one section at the end - the rest of the post is not written as questions and answers. Each answer opens with a one-sentence direct answer, then 1 to 3 sentences of support: 40 to 90 words in all, held to the same grounding rules as the essay.
- If the brief lists TRENDING IN RECENT REPORTS, mention the ones that genuinely belong in this post; skip the rest.

GROUNDING — checked by code; a violation rejects the essay
- Verbatim fragments: when you quote a practitioner, wrap their exact words in «guillemets». The text inside «» must be copied character for character from one discussion — a fragment of a sentence is fine, 4 to 30 words. Use no other quotation marks around any phrase of three or more words.
- Numbers: every number in prose (prices, percentages, token counts, latencies, benchmark results, versions) must appear in the discussions, in the FACT SHEET or in a WHAT WE TRIED note. Do not compute, estimate or round new figures.
- Write every figure above ten in digits, never in words, and do not compute ratios or multiples ("five times", "tripling") - state the figures a discussion gives.
- Any sentence that credits practitioners ("one team found", "engineers report", "a postmortem showed") must contain a «verbatim» fragment of what they said. If you cannot quote it, do not attribute it.
- Do not attribute intent or strategy to any vendor, and do not state what an API can or cannot do unless a discussion says so.
- Do not invent behaviour, API parameters, benchmarks, anecdotes or prices the discussions do not contain. Where a failure is recorded but its cause is not, say the cause is not established and present your explanation as analysis.
- Code examples are illustrative patterns implementing a mitigation the discussions motivate. They must not present invented parameters as a vendor's official API.

STRUCTURE (call publish_essay exactly once)
- 5 to 7 thematic sections with specific, architectural headings (for example "The API contract migration trap", "The economics of prefix caching"). Each section has 3 to 5 substantial paragraphs. Total length 1,800 to 2,800 words.
- At most one pull quote per section, verbatim as above.
- 1 to 3 code or configuration examples, attached to the section they belong to.
- One scenario matrix (5 to 8 rows) and one decision tree (3 to 5 branches), as the brief describes.
- A `faq` of exactly 3 questions, as SEARCH describes."""

TOOL = {
    "type": "function",
    "function": {
        "name": "publish_essay",
        "description": "Publish the finished essay as structured fields.",
        "parameters": {
            "type": "object",
            "required": ["title", "dek", "description", "keywords", "tldr", "sections",
                         "scenario_matrix", "decision_tree", "decisions", "faq"],
            "properties": {
                "title": {"type": "string", "description": "Headline, at most 80 characters."},
                "dek": {"type": "string", "description": "One or two sentences under the headline."},
                "description": {"type": "string", "description": "Meta description, at most 160 characters."},
                "keywords": {"type": "array", "items": {"type": "string"},
                             "description": "4 to 8 SEO keywords, the brief's PRIMARY KEYWORD first."},
                "tldr": {"type": "string", "description": "One line, at most 40 words: the single thing a reader should leave with."},
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["heading", "paragraphs"],
                        "properties": {
                            "heading": {"type": "string"},
                            "paragraphs": {"type": "array", "items": {"type": "string"},
                                           "description": "Plain text. `backticks` for code, **bold** sparingly, «…» for verbatim fragments."},
                            "pull_quote": {"type": "string", "description": "Optional. One verbatim passage, copied exactly."},
                            "code": {
                                "type": "object",
                                "required": ["label", "language", "source"],
                                "properties": {"label": {"type": "string"}, "language": {"type": "string"},
                                               "source": {"type": "string"}},
                            },
                        },
                    },
                },
                "scenario_matrix": {
                    "type": "object",
                    "required": ["title", "rows"],
                    "properties": {
                        "title": {"type": "string"},
                        "rows": {"type": "array", "items": {
                            "type": "object",
                            "required": ["scenario", "tradeoff", "mitigation", "route"],
                            "properties": {"scenario": {"type": "string"}, "tradeoff": {"type": "string"},
                                           "mitigation": {"type": "string"}, "route": {"type": "string"}}}},
                    },
                },
                "decision_tree": {
                    "type": "object",
                    "required": ["question", "branches"],
                    "properties": {
                        "question": {"type": "string"},
                        "branches": {"type": "array", "items": {
                            "type": "object",
                            "required": ["condition", "outcome", "route"],
                            "properties": {"condition": {"type": "string"}, "outcome": {"type": "string"},
                                           "route": {"type": "string"}}}},
                    },
                },
                "decisions": {"type": "array", "items": {"type": "string"},
                              "description": "3 to 5 short sidebar lines: the decisions this essay supports."},
                "visuals": {
                    "type": "array",
                    "description": "2 to 5 tables, charts or diagrams for the WHOLE post - not one per section. Only the sections that cannot do without one.",
                    "items": {
                        "type": "object",
                        "required": ["section", "kind", "caption"],
                        "properties": {
                            "section": {"type": "integer", "description": "Index of the section it belongs to (0-based); one visual per section at most."},
                                    "kind": {"type": "string", "enum": ["table", "chart", "diagram"]},
                                    "caption": {"type": "string", "description": "What it shows, one sentence; a chart names its unit."},
                                    "columns": {"type": "array", "items": {"type": "string"}, "description": "table: 2 to 6 column headings."},
                                    "rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}},
                                             "description": "table: 2 to 12 rows, one cell per column."},
                                    "unit": {"type": "string", "description": "chart: the unit every bar shares, e.g. 'USD per 1M input tokens'."},
                                    "bars": {"type": "array", "description": "chart: 2 to 10 bars on one scale.",
                                             "items": {"type": "object", "required": ["label", "value"],
                                                       "properties": {"label": {"type": "string"}, "value": {"type": "number"}}}},
                                    "steps": {"type": "array", "items": {"type": "string"},
                                              "description": "diagram: 3 to 8 steps of a flow or sequence, each at most 12 words."},
                                },
                            }
                },
                "illustrations": {
                    "type": "array",
                    "description": "1 or 2 AI-generated illustrations, each picturing the situation one section describes.",
                    "items": {"type": "object", "required": ["section", "scene", "alt", "caption"],
                              "properties": {
                                  "section": {"type": "integer", "description": "Index of the section it illustrates (0-based)."},
                                  "scene": {"type": "string", "description": "What the picture shows, 15 to 80 words: a concrete scene or visual metaphor. No text, numbers, logos, brands, product names, real people, screenshots or charts."},
                                  "alt": {"type": "string", "description": "Alt text, at most 125 characters, describing the picture."},
                                  "caption": {"type": "string", "description": "One short sentence tying the picture to the section."}}}},
                "faq": {"type": "array", "description": "Exactly 3 questions people type into Google about this subject, each answered directly.",
                        "items": {"type": "object", "required": ["question", "answer"],
                                  "properties": {"question": {"type": "string", "description": "As a searcher would type it, ending with '?'."},
                                                 "answer": {"type": "string", "description": "40 to 90 words: a one-sentence direct answer, then support."}}}},
            },
        },
    },
}


def user_message(post, docs, facts) -> str:
    parts = [post["brief"], "", "FACT SHEET (registry list prices, as last polled from OpenRouter):",
             fact_lines(facts) or "- none", "", "DISCUSSIONS:"]
    for i, d in enumerate(docs, 1):
        # NO PLATFORM LABEL: the board names no source platform, so the model
        # is not told one to name. (A platform can still appear inside a
        # discussion's own text; the banned-phrase check refuses it in prose.)
        parts += [f"\n<<<DISCUSSION {i}>>>", d["text"],
                  f"<<<END DISCUSSION {i}>>>"]
    parts.append("\nWrite the essay now by calling publish_essay.")
    return "\n".join(parts)


#: Wall-clock ceiling for one call. STREAMED, because a buffered OpenRouter
#: response sends keep-alive whitespace while it waits, which resets httpx's
#: read timeout - so a stalled call never times out. That happened to the first
#: run of this script (14 minutes, no answer, 2026-10-01) and is the same defect
#: `judge/extract/client.py` documents and fixes the same way.
#:
#: Raised to 1200 after the second run: OpenRouter routed Flash to a provider
#: generating ~20 tokens/s, and the call spent all 600s on 12,172 reasoning
#: tokens without writing a word (gen-1790831572-i5PfBK6kf3xuXT5sTLzO, $0.0010).
CALL_DEADLINE_S = 1200
MAX_OUTPUT_TOKENS = 24_000
#: The essay is the output; the reading is in the prompt. Low effort keeps the
#: reasoning phase from eating the deadline. Same model either way.
REASONING = {"effort": "low"}
#: Fastest provider serving the SAME model. The served-model check below still
#: refuses anything that is not GEN_MODEL.
PROVIDER = {"sort": "throughput"}


def call_model(key: str, base: str, messages: list[dict], tool: dict | None = None) -> dict:
    tool = tool or TOOL
    import time

    deadline = time.monotonic() + CALL_DEADLINE_S
    args, content, reasoning_chars = [], [], 0
    call_id = name = finish = served = provider = usage = None
    gen_id = None
    last_beat = 0
    with httpx.stream(
        "POST", f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": GEN_MODEL, "messages": messages, "tools": [tool],
              "tool_choice": {"type": "function", "function": {"name": "publish_essay"}},
              "max_tokens": MAX_OUTPUT_TOKENS, "stream": True,
              "stream_options": {"include_usage": True}, "usage": {"include": True},
              "reasoning": REASONING, "provider": PROVIDER,
              **({} if GEN_MODEL in NO_TEMPERATURE else {"temperature": TEMPERATURE})},
        timeout=httpx.Timeout(120.0, connect=10.0),
    ) as r:
        gen_id = r.headers.get("X-Generation-Id")
        if r.status_code != 200:
            r.read()
            err = ProviderTransient if r.status_code == 429 or r.status_code >= 500 else BuildError
            raise err(f"OpenRouter HTTP {r.status_code}: {r.text[:300]!r}")
        for line in r.iter_lines():
            if time.monotonic() > deadline:
                raise BuildError(f"no complete answer within {CALL_DEADLINE_S}s "
                                 f"(generation {gen_id}); abandoned")
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            if "error" in chunk:
                code = (chunk["error"] or {}).get("code") if isinstance(chunk["error"], dict) else None
                err = ProviderTransient if isinstance(code, int) and (code == 429 or code >= 500) else BuildError
                raise err(f"provider error mid-stream: {str(chunk['error'])[:300]}")
            gen_id = chunk.get("id") or gen_id
            served = chunk.get("model") or served
            provider = chunk.get("provider") or provider
            usage = chunk.get("usage") or usage
            for ch in chunk.get("choices") or []:
                d = ch.get("delta") or {}
                reasoning_chars += len(d.get("reasoning") or "")
                content.append(d.get("content") or "")
                for tc in d.get("tool_calls") or []:
                    call_id = tc.get("id") or call_id
                    fn = tc.get("function") or {}
                    name = fn.get("name") or name
                    args.append(fn.get("arguments") or "")
                finish = ch.get("finish_reason") or finish
            got = sum(map(len, args))
            # Reasoning counts as progress too: a long think is not a stall,
            # and the first run could not tell them apart.
            if got + reasoning_chars - last_beat >= 6000:
                last_beat = got + reasoning_chars
                print(f"    … {got:,} chars of essay, {reasoning_chars:,} chars of reasoning "
                      f"({provider or 'provider not yet named'})", flush=True)
    # The instruction was "call DeepSeek V4 Flash". A response from anything
    # else is refused rather than rendered.
    if served not in GEN_MODELS[GEN_MODEL]:
        raise BuildError(f"asked for {GEN_MODEL}, OpenRouter served {served!r}; refusing the draw")
    if finish == "length":
        raise BuildError("generation stopped at max_tokens; the essay is truncated")
    if not args:
        raise BuildError(f"no tool call (finish_reason={finish!r})")
    call = {"id": call_id or "call_0", "type": "function",
            "function": {"name": name or "publish_essay", "arguments": "".join(args)}}
    return {"message": {"role": "assistant", "content": "".join(content)}, "call": call,
            "served": served, "provider": provider, "usage": usage, "generation_id": gen_id}


# ── 3 · checks (code, never a model) ─────────────────────────────────────────

_FOLD = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                       "–": "-", "—": "-", " ": " "})


def norm(s: str) -> str:
    # `**` and `__` are Markdown emphasis, not words. Measured 2026-10-01: a
    # migration guide failed six rounds quoting "all of the tokens ..." exactly,
    # because the source reads "**all** of the tokens ...". Folded on BOTH sides,
    # like whitespace and typographic quotes; a single `*` stays significant.
    s = s.replace("**", "").replace("__", "")
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s).translate(_FOLD)).strip()


GUILLEMET = re.compile(r"«([^»]+)»")
OTHER_QUOTE = re.compile(r"[\"“]([^\"“”]+)[\"”]")
NUMBER = re.compile(r"(?<![\w.$])\$?\d+(?:[.,]\d+)*%?")
BANNED = [
    # NARROWED 2026-10-01. The bare phrase failed a correct sentence six rounds
    # running ("handled according to the system's data policy"), and a check
    # that refuses correct text cannot be satisfied - the model had nothing to
    # fix. It now fires only when the object is an input or a reporter.
    (r"\baccording to (the |these |those |our |some |many |most )?(sources?|documents?|threads?|"
     r"discussions?|posts?|reports?|material|data|practitioners|engineers|developers|users|teams|"
     r"commenters|benchmarks?)\b", "refers to its inputs ('according to …')"),
    # "(?! of)" added 2026-10-01: "obscure the source of failure" failed five
    # rounds running. An input is referred to as a thing, not "the source of X".
    (r"\b(the|these|those|our|this) (sources?|documents?|threads?|discussions?|posts?|material|excerpts?)\b"
     r"(?! of\b)", "refers to its inputs"),
    (r"\b(I|we) (read|reviewed|analy[sz]ed|examined)\b", "first-person reading"),
    # Found 2026-10-01 in the first GPT-6 Luna pass: "though the fact sheet
    # gives list rates" - the prompt's own section name, leaked into prose.
    # NOT "the prompt" or "the brief": in an essay about models those mean a
    # user's request, and the rule failed a correct sentence five rounds running
    # ("even when the prompt and model remain fixed", 2026-10-01).
    (r"\b(fact sheet|price sheet|supplied (sheet|list|data|figures|material|context|facts|prices)|"
     r"provided (text|context|material|sheet|facts)|(values|prices|figures|facts) provided here)\b",
     "refers to its inputs"),
    # Found 2026-10-01 in the first planned posts: "the registry list prices
    # supplied for Sonnet 5", "the supplied examples do not provide ...", "no hit
    # rate or cache semantics are supplied". Narrow on purpose: "users supplied
    # non-default settings" and "how much context is supplied" are ordinary
    # engineering prose and stay legal.
    (r"\bthe supplied \w+|\b(prices|figures|examples|values|rates|numbers|data) supplied\b"
     r"|\b(are|were) supplied\s*[.;,]", "refers to its inputs ('supplied')"),
    (r"\b(\d+|several|dozens of|a dozen|hundreds of|many|most|few) "
     r"(developers|engineers|users|people|reports|quotes|posts|threads|respondents|teams|discussions|"
     r"articles|comments)\b",
     "counts people or reports"),
    (r"\b(corpus|dataset|polarity|sentiment|telemetry|board entr)", "internal telemetry vocabulary"),
    (r"\b\d+(\.\d+)?\s*(/|out of)\s*(10|100)\b", "a score out of 10 or 100"),
    (r"\bdiscussion \d+\b", "names a discussion by number"),
    # NO PLATFORM NAMES ON THE BOARD (team decision, terms position). A source
    # platform named in prose is a citation the page is not allowed to make.
    # "GitHub" alone is a product the essays discuss (MCP servers, Copilot), so
    # only its use AS A SOURCE is refused; "Medium" is an effort level.
    (r"\b(reddit|r/\w+|subreddit|hacker news|dev\.to|dev community|arxiv|hugging ?face|twitter|x\.com|"
     r"tweets?|discord|linkedin|youtube|stack overflow|substack|lobste\.rs)\b"
     r"|\b(on|from|in) github\b|\bgithub (issue|thread|discussion|comment)s?\b|\bmedium (post|article)s?\b",
     "names a source platform - the board shows none"),
    # FIGURES IN WORDS BYPASS THE NUMBER CHECK. The first passing Opus draft
    # (2026-10-01) wrote "eleven percent", "forty-three percent" and "tripling
    # the effective cost" - the last one invented. Digits only, so every figure
    # is checkable; one to ten stay legal as ordinary prose.
    (r"\b(eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
     r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)\b", "a figure written in words - use digits"),
    (r"\b(one|two|three|four|five|six|seven|eight|nine|ten)[- ](percent|times)\b",
     "a figure written in words - use digits"),
    (r"\b(doubl|tripl|quadrupl)(e|es|ed|ing)\b|\b\d+(\.\d+)?\s*[x×](?![\w])",
     "a ratio or multiple - state the figures the discussion gives instead of computing one"),
    # NARROWED 2026-10-01: the bare adverb failed "deliberately" used of the
    # reader's own design choices. Intent is only a defect when a vendor holds it.
    (r"\b(anthropic|openai|deepseek|google|moonshot|alibaba|qwen)\b[^.]{0,60}\b(consciously|deliberately|"
     r"intentionally|on purpose)\b|\b(anthropic|openai|deepseek|google) (intended|decided|chose|wanted|"
     r"appears to have (made|chosen|decided))\b", "attributes intent to a vendor"),
]

#: A sentence that credits practitioners must carry their words. The first Opus
#: draft invented "one team's postmortem found that a single refused request
#: could burn through multiple retries ... tripling the effective cost"; under
#: this rule that sentence needs a «verbatim» fragment, and there is none.
ATTRIBUTION = re.compile(
    r"\b(one|another|some|several) (engineer|team|user|developer|practitioner|partner|builder)s?\b"
    r"|\b(practitioners|users|teams|engineers|developers|builders) (report|reported|describe|described|"
    r"found|note|noted|say|said|observe|observed|complain|complained|put it)\b|\bpostmortem\b"
    # Added 2026-10-01: the first Luna compare draft wrote "A practitioner
    # described using Opus at high effort ..." and "Another used Opus to plan
    # ..." with no quote. "a team" alone stays out (it failed "the change a
    # team can make"), so the singular forms need a reporting verb nearby.
    r"|\b(a|an|another) (practitioner|engineer|developer|builder|commenter)\b[^.]{0,50}"
    r"\b(described|reported|found|noted|said|wrote|observed|complained|used|recommended)\b"
    r"|\bAnother (used|described|reported|found|noted|said|wrote|recommended)\b", re.I)
_QMARK = "\u2063Q\u2063"


def prose_fields(essay: dict):
    """(path, text) for every field a reader sees as prose. Code is excluded."""
    for k in ("title", "dek", "description", "tldr"):
        yield k, essay.get(k, "")
    for i, kw in enumerate(essay.get("keywords", [])):
        yield f"keywords[{i}]", kw
    for i, s in enumerate(essay.get("sections", [])):
        yield f"sections[{i}].heading", s.get("heading", "")
        for j, p in enumerate(s.get("paragraphs", [])):
            yield f"sections[{i}].paragraphs[{j}]", p
        if has_code(s):
            yield f"sections[{i}].code.label", s["code"].get("label", "")
    m = essay.get("scenario_matrix", {})
    yield "scenario_matrix.title", m.get("title", "")
    for i, r in enumerate(m.get("rows", [])):
        for k in ("scenario", "tradeoff", "mitigation", "route"):
            yield f"scenario_matrix.rows[{i}].{k}", r.get(k, "")
    t = essay.get("decision_tree", {})
    yield "decision_tree.question", t.get("question", "")
    for i, b in enumerate(t.get("branches", [])):
        for k in ("condition", "outcome", "route"):
            yield f"decision_tree.branches[{i}].{k}", b.get(k, "")
    for i, d in enumerate(essay.get("decisions", [])):
        yield f"decisions[{i}]", d
    for i, vis in enumerate(essay.get("visuals") or []):
        vis = vis or {}
        yield f"visuals[{i}].caption", vis.get("caption", "")
        for c, col in enumerate(vis.get("columns") or []):
            yield f"visuals[{i}].columns[{c}]", col
        for r, row in enumerate(vis.get("rows") or []):
            for c, cell in enumerate(row or []):
                yield f"visuals[{i}].rows[{r}][{c}]", cell
        for b, bar in enumerate(vis.get("bars") or []):
            yield f"visuals[{i}].bars[{b}].label", (bar or {}).get("label", "")
        for st, step in enumerate(vis.get("steps") or []):
            yield f"visuals[{i}].steps[{st}]", step
    for i, il in enumerate(essay.get("illustrations") or []):
        yield f"illustrations[{i}].caption", (il or {}).get("caption", "")
        yield f"illustrations[{i}].alt", (il or {}).get("alt", "")
    for i, qa in enumerate(essay.get("faq") or []):
        yield f"faq[{i}].question", (qa or {}).get("question", "")
        yield f"faq[{i}].answer", (qa or {}).get("answer", "")
    for key, sp in SPECIALS.items():
        for i, it in enumerate(essay.get(key) or []):
            for f in sp["prose"]:
                yield f"{key}[{i}].{f}", (it or {}).get(f, "")


def has_code(section: dict) -> bool:
    """A section carries an example only if the example has code in it.

    Measured 2026-10-01: GPT-6 Luna fills the optional `code` field with an
    empty object on most sections, and three pages shipped 5 empty
    "Illustrative" boxes each. An empty object is the model saying "no example
    here"; the requirement that SOME section has a real one is still checked.
    """
    return bool((section.get("code") or {}).get("source", "").strip())


def words_in(essay: dict) -> int:
    return sum(len(GUILLEMET.sub(r"\1", p).split())
               for s in essay.get("sections", []) for p in s.get("paragraphs", []))


#: The three original posts' structure. A planned post carries its format's.
LEGACY_RULES = {"sections": (5, 7), "matrix": True, "tree": True, "code": (1, 99), "words": (MIN_WORDS, 2800)}


def check(essay: dict, context: str, rules: dict | None = None, experiences: str = "",
          seo: dict | None = None, doc_texts: list[str] | None = None) -> list[str]:
    rules = rules or LEGACY_RULES
    ctx = norm(context)
    # FIGURES MAY COME FROM OUR OWN NOTES; QUOTES MAY NOT. A WHAT WE TRIED note is
    # our record, not an engineer's words, so it joins the number check and never
    # the «verbatim» check - a quote must still be found in a discussion.
    exp = norm(experiences)
    ctx_nums = re.sub(r"(?<=\d),(?=\d{3})", "", ctx + "\n" + exp)
    v: list[str] = []

    def verbatim(path, frag):
        f = norm(frag)
        if f in ctx:
            return
        # THE RULE DOES NOT LOOSEN; THE REFUSAL GETS PRECISE. Measured
        # 2026-10-01: Flash missed the same quote three rounds running because
        # it wrote "it has" for the source's "It has", and "not verbatim" gave
        # it nothing to correct. Each hint names the source's exact text.
        hint = "copy it exactly or drop it"
        if exp and f.lower().rstrip(".,;:!?") in exp.lower():
            # OUR OWN NOTE, QUOTED AS IF AN ENGINEER SAID IT (2026-10-13): held
            # a draft for five repairs under the generic hint.
            hint = ("that is a WHAT WE TRIED note - our own record, not an engineer's words; "
                    "retell it in plain words without «»")
        elif f.rstrip(".,;:!?") in ctx:
            hint = "the source has no trailing punctuation there — end the fragment where the source does"
        elif (i := ctx.lower().find(f.lower())) >= 0:
            hint = f"capitalisation differs — the source reads «{ctx[i:i + len(f)]}»"
        else:
            words = f.split()
            for n in range(len(words) - 1, 3, -1):
                head = " ".join(words[:n])
                if head in ctx:
                    hint = f"the source diverges after «{head}» — end the fragment there or copy what follows exactly"
                    break
        v.append(f"{path}: «{frag[:90]}» is not verbatim in any discussion — {hint}")

    for path, text in prose_fields(essay):
        for frag in GUILLEMET.findall(text):
            verbatim(path, frag)
        for span in OTHER_QUOTE.findall(GUILLEMET.sub("", text)):
            if len(span.split()) >= 3:
                v.append(f"{path}: quotation marks around \"{span[:70]}\" — use «» with exact words, or remove the marks")
        for num in NUMBER.findall(GUILLEMET.sub("", text)):
            bare = num.strip("$%").replace(",", "")
            if not re.search(rf"(?<![\d.]){re.escape(bare)}(?![\d])", ctx_nums):
                v.append(f"{path}: the number {num} appears in no discussion and not in the fact sheet")
        for pat, why in BANNED:
            if why.startswith("a ratio or multiple"):
                # A MULTIPLE THE SOURCES STATE IS A FIGURE, NOT ARITHMETIC.
                # Measured 2026-10-05: a cost teardown failed six rounds on
                # "0.1×" and "1.25×", which the source states verbatim ("Cache
                # read tokens - 0.1×"). Only a multiple absent from the sources
                # is refused - the same test every other number gets.
                for m in re.finditer(pat, text, re.I):
                    num = re.match(r"\s*([\d.]+)", m.group(0))
                    if num and re.search(rf"(?<![\d.]){re.escape(num.group(1))}\s*[x×]", ctx_nums, re.I):
                        continue
                    v.append(f"{path}: {why}: {m.group(0)!r}")
                continue
            m = re.search(pat, text, re.I)
            if m:
                v.append(f"{path}: {why}: {m.group(0)!r}")
        for sent in re.split(r"(?<=[.!?])\s+", GUILLEMET.sub(_QMARK, text)):
            m = ATTRIBUTION.search(sent)
            if m and _QMARK not in sent:
                v.append(f"{path}: credits practitioners ({m.group(0)!r}) without a «verbatim» fragment "
                         f"in the same sentence: {sent[:110]!r}")
            if (e := experience_unanchored(sent, exp)):
                v.append(f"{path}: {e}: {sent[:110]!r}")
    secs = essay.get("sections", [])
    for i, s in enumerate(secs):
        if s.get("pull_quote"):
            verbatim(f"sections[{i}].pull_quote", s["pull_quote"])
        plo, phi = rules.get("per_section", (3, 99))
        n_par = len(s.get("paragraphs", []))
        if not plo <= n_par <= phi:
            v.append(f"sections[{i}]: needs {plo} to {phi} paragraphs, has {n_par}")
    lo, hi = rules["sections"]
    if not lo <= len(secs) <= hi:
        v.append(f"needs {lo} to {hi} sections, has {len(secs)}")
    if rules["matrix"] and not 5 <= len(essay.get("scenario_matrix", {}).get("rows", [])) <= 8:
        v.append("scenario_matrix needs 5 to 8 rows")
    if rules["tree"] and not 3 <= len(essay.get("decision_tree", {}).get("branches", [])) <= 5:
        v.append("decision_tree needs 3 to 5 branches")
    n_code = sum(has_code(s) for s in secs)
    clo, chi = rules["code"]
    if n_code < clo:
        v.append(f"needs at least {clo} code or configuration example(s), has {n_code}")
    if n_code > chi:
        v.append(f"at most {chi} code example(s) for this format, has {n_code}")
    for i, s in enumerate(secs):
        if has_code(s) and not (s["code"].get("label") or "").strip():
            v.append(f"sections[{i}].code: needs a label saying what the example shows")
    wlo, whi = rules["words"]
    # READING LENGTH, AS THE PAGE COUNTS IT (2026-10-13): body, short answer,
    # FAQ and the words in tables, charts and diagrams - everything views.js
    # counts for "N min read". The ask was an 8 to 15 minute read, not a body
    # of 1,850 words; counting the body alone held a 9-minute post at "1,531".
    if (w := reading_words(essay)) < wlo:
        v.append(f"the post reads as {w} words (~{max(1, round(w / 230))} min); write {wlo:,} to {whi:,} "
                 "- mostly by deepening the sections, not by adding visuals")
    if "para_words" in rules:
        v += _distinctiveness(essay, rules)
    if "visuals" in rules:
        v += visual_violations(essay, rules["visuals"], ctx_nums)
        v += illustration_violations(essay, len(essay.get("sections") or []))
    if seo:
        v += seo_violations(essay, seo)
    if doc_texts:
        v += voices_violations(essay, doc_texts)
    return v


def voices_violations(essay: dict, doc_texts: list[str], need: int = 3) -> list[str]:
    """Engineers' «words» from at least `need` different discussions - so
    agreement and disagreement come from more than one voice."""
    docs = [norm(t) for t in doc_texts]
    found = set()
    for _p, t in prose_fields(essay):
        for frag in GUILLEMET.findall(t):
            f = norm(frag)
            found |= {i for i, d in enumerate(docs) if f in d}
    for s in essay.get("sections") or []:
        if s.get("pull_quote"):
            f = norm(s["pull_quote"])
            found |= {i for i, d in enumerate(docs) if f in d}
    if len(found) < need:
        return [f"voices: engineers are quoted from {len(found)} discussion(s); quote «exact words» from at "
                f"least {need} different discussions, setting agreeing and disagreeing voices side by side"]
    return []


#: How many generated illustrations a planned post carries, and how they are
#: drawn. Configuration, kept here beside the prompt that names it until the
#: blog configuration moves to contract/ (see blog_formats.yaml's header).
ILLUSTRATIONS_PER_POST = (1, 2)
IMAGE_MODEL = os.environ.get("BLOG_IMAGE_MODEL", "google/gemini-2.5-flash-image")
IMAGE_MAX_WIDTH = 1200
IMAGE_JPEG_QUALITY = 78
#: Every picture shares one look, so a post's illustrations read as a set and
#: as illustrations - never as a photograph of something that happened.
IMAGE_STYLE = ("Editorial illustration for a technical blog about AI models. Flat vector style with soft "
               "gradients, a muted dark navy background with blue and violet accents, clean geometric "
               "shapes, generous negative space, wide 16:9 composition. Absolutely no text, letters, "
               "numbers, logos, brand marks, user-interface screenshots, charts or real people's likenesses.")

#: What a generated picture must not depict - each is either data that belongs
#: in a checked visual, or something a picture would falsely assert.
SCENE_REFUSED = re.compile(
    r"\d|\b(logo|logos|brand|trademark|screenshot|screen ?shot|dashboard|chart|graph|plot|table|"
    r"text|words|letters|label|caption|headline|sign|signage|watermark|photo of|photograph of|"
    r"anthropic|openai|google|gemini|deepseek|claude|gpt|chatgpt|llama|meta|mistral|qwen|kimi|glm|grok|"
    r"microsoft|nvidia|amazon|apple|openrouter|hugging ?face|github|reddit|twitter)\b", re.I)


def illustration_violations(essay: dict, n_sections: int) -> list[str]:
    """The pictures the essay proposes: how many, which section, and a scene
    that depicts no data, brand, product, real person or text."""
    v: list[str] = []
    ills = essay.get("illustrations") or []
    lo, hi = ILLUSTRATIONS_PER_POST
    if not lo <= len(ills) <= hi:
        v.append(f"illustrations: {len(ills)}; propose {lo} to {hi}")
    for k, il in enumerate(ills):
        p = f"illustrations[{k}]"
        sec = (il or {}).get("section")
        if not isinstance(sec, int) or not 0 <= sec < n_sections:
            v.append(f"{p}.section: must be a section index from 0 to {n_sections - 1}")
        scene = (il or {}).get("scene", "")
        if not 15 <= len(scene.split()) <= 80:
            v.append(f"{p}.scene: {len(scene.split())} words; describe the picture in 15 to 80")
        if (m := SCENE_REFUSED.search(scene)):
            v.append(f"{p}.scene: {m.group(0)!r} - a generated picture shows no text, numbers, brands, products, "
                     "real people, screens or charts; describe the situation as a scene or metaphor")
        if not (il or {}).get("alt", "").strip() or len(il.get("alt", "")) > 125:
            v.append(f"{p}.alt: alt text of 1 to 125 characters describing the picture")
        if not (il or {}).get("caption", "").strip():
            v.append(f"{p}.caption: one short sentence")
    return v


def render_illustration(scene: str, key: str, base: str) -> tuple[str, dict]:
    """(data URL, usage) for one picture. RAISES on any failure - the caller
    decides what an unrendered picture means; this never returns a blank."""
    import base64
    import io

    from PIL import Image

    r = httpx.post(f"{base}/chat/completions", headers={"Authorization": f"Bearer {key}"},
                   timeout=180, json={"model": IMAGE_MODEL, "modalities": ["image", "text"],
                                      "messages": [{"role": "user", "content": f"{IMAGE_STYLE}\n\nScene: {scene}"}],
                                      "usage": {"include": True}})
    r.raise_for_status()
    body = r.json()
    msg = (body.get("choices") or [{}])[0].get("message") or {}
    images = msg.get("images") or []
    if not images:
        raise BuildError(f"the image model returned no image ({str(msg.get('content'))[:120]!r})")
    url = (images[0].get("image_url") or {}).get("url", "")
    if not url.startswith("data:image/") or ";base64," not in url:
        raise BuildError("the image model returned an image that is not an inline base64 picture")
    raw = base64.b64decode(url.split(";base64,", 1)[1])
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    if img.width > IMAGE_MAX_WIDTH:
        img = img.resize((IMAGE_MAX_WIDTH, round(img.height * IMAGE_MAX_WIDTH / img.width)))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=IMAGE_JPEG_QUALITY, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode("ascii"), body.get("usage") or {}


def illustrate(post: dict, essay: dict, key: str, base: str, started: str) -> list[dict]:
    """Render the essay's proposed pictures. Each paid call is recorded in the
    spend ledger (stage 'blog'). A picture that fails to render is LEFT OUT AND
    SAID: the post is still worth reviewing without it, and the run log names it."""
    out = []
    for k, il in enumerate(essay.get("illustrations") or []):
        try:
            src, usage = render_illustration(il["scene"], key, base)
        except Exception as e:  # noqa: BLE001
            print(f"  [{post['key']}] illustration {k + 1} not rendered: {type(e).__name__}: {e}", flush=True)
            continue
        try:
            from judge import spend_ledger

            call = spend_ledger.record(stage="blog", model=IMAGE_MODEL,
                                       input_tokens=int(usage.get("prompt_tokens") or 0),
                                       output_tokens=int(usage.get("completion_tokens") or 0),
                                       at=datetime.fromisoformat(started),
                                       run_id=f"blog-image:{post['key']}@{started}#{k + 1}",
                                       reported=True, reported_usd=usage.get("cost"), to_database=False)
            if (dsn := env().get("DATABASE_URL")):
                spend_ledger.append_to_database([call], dsn=dsn)
        except Exception as e:  # noqa: BLE001
            print(f"  [{post['key']}] illustration {k + 1} spend not recorded: {e}", flush=True)
        out.append({"section": il["section"], "src": src, "alt": il["alt"], "caption": il["caption"],
                    "model": IMAGE_MODEL, "usd": usage.get("cost")})
        print(f"  [{post['key']}] illustration {k + 1} rendered by {IMAGE_MODEL}"
              f" ({len(src) // 1024} KB, ${usage.get('cost') or 0:.4f})", flush=True)
    return out


def reading_words(essay: dict) -> int:
    """Words a reader reads: section paragraphs, the short answer, the FAQ, and
    the text of every table, chart and diagram."""
    n = words_in(essay)
    n += len(GUILLEMET.sub(r"\1", essay.get("tldr", "")).split())
    for qa in essay.get("faq") or []:
        n += len(((qa or {}).get("question", "") + " " + (qa or {}).get("answer", "")).split())
    for vis in essay.get("visuals") or []:
        vis = vis or {}
        bits = [vis.get("caption", "")] + list(vis.get("columns") or []) + list(vis.get("steps") or [])
        bits += [c for r in vis.get("rows") or [] for c in (r or [])]
        bits += [(b or {}).get("label", "") for b in vis.get("bars") or []]
        n += sum(len(str(b).split()) for b in bits)
    return n


def _num_text(x) -> str:
    """A chart value as the sources would write it: 16384, 0.0205, 2.5."""
    f = float(x)
    return str(int(f)) if f.is_integer() else f"{f:.10f}".rstrip("0").rstrip(".")


def visual_violations(essay: dict, span: tuple, ctx_nums: str) -> list[str]:
    """Tables, charts and diagrams (2026-10-13): how many, one per section, and
    well-formed. A chart's VALUES are figures like any other: each must appear
    in the discussions, the fact sheet or a WHAT WE TRIED note (rule 3 - nothing
    plotted is computed). Text in a visual is checked with the prose."""
    v: list[str] = []
    secs = essay.get("sections") or []
    vis = list(enumerate(essay.get("visuals") or []))
    lo, hi = span
    if len(vis) < lo:
        v.append(f"visuals: {len(vis)} in the post; add {lo - len(vis)} more (a table, chart or diagram) "
                 "to sections that need one")
    elif len(vis) > hi:
        # NAMES THEM (2026-10-13): "add 2 to 5" held a draft at 8 - one per
        # section - for two repairs; it never said to remove any.
        where = ", ".join(f"visuals[{i}] ({(x or {}).get('kind')}, section {(x or {}).get('section')})"
                          for i, x in vis)
        v.append(f"visuals: {len(vis)} in the post, at most {hi}; REMOVE {len(vis) - hi} - keep only those a "
                 f"section cannot do without. They are in: {where}")
    used: set = set()
    for i, x in vis:
        x = x or {}
        p = f"visuals[{i}]"
        sec = x.get("section")
        if not isinstance(sec, int) or not 0 <= sec < len(secs):
            v.append(f"{p}.section: must be a section index from 0 to {len(secs) - 1}")
        elif sec in used:
            v.append(f"{p}.section: section {sec} already has a visual - at most one per section")
        else:
            used.add(sec)
        kind = x.get("kind")
        if not (x.get("caption") or "").strip():
            v.append(f"{p}: needs a caption saying what it shows")
        if kind == "table":
            cols, rows = x.get("columns") or [], x.get("rows") or []
            if not 2 <= len(cols) <= 6 or not 2 <= len(rows) <= 12:
                v.append(f"{p}: a table needs 2 to 6 columns and 2 to 12 rows")
            if any(len(r or []) != len(cols) for r in rows):
                v.append(f"{p}: every table row needs one cell per column")
        elif kind == "chart":
            bars = x.get("bars") or []
            if not 2 <= len(bars) <= 10:
                v.append(f"{p}: a chart needs 2 to 10 bars")
            if not (x.get("unit") or "").strip():
                v.append(f"{p}: a chart names the unit its bars share")
            for b, bar in enumerate(bars):
                try:
                    val = _num_text((bar or {}).get("value"))
                except (TypeError, ValueError):
                    v.append(f"{p}.bars[{b}]: value must be a number")
                    continue
                if float(val) < 0:
                    v.append(f"{p}.bars[{b}]: a bar cannot be negative")
                if not re.search(rf"(?<![\d.]){re.escape(val)}(?![\d])", ctx_nums):
                    v.append(f"{p}.bars[{b}]: the value {val} appears in no discussion, the fact sheet or a "
                             "WHAT WE TRIED note - chart only stated figures")
        elif kind == "diagram":
            steps = x.get("steps") or []
            if not 3 <= len(steps) <= 8:
                v.append(f"{p}: a diagram needs 3 to 8 steps")
            for st, step in enumerate(steps):
                if len(str(step).split()) > 12:
                    v.append(f"{p}.steps[{st}]: at most 12 words per step")
        else:
            v.append(f"{p}: kind must be table, chart or diagram")
    return v


#: A first-person EXPERIENCE: something this team did or saw. Opinions ("we
#: think", "we disagree") are not matched - they need no record.
EXPERIENCE = re.compile(
    r"\bwe(?:'ve| have| had)? (tried|ran|run|tested|measured|benchmarked|switched|moved|deployed|swapped|"
    r"migrated|built|compared|watched|saw|hit|pinned|turned|fed|gave|asked|used)\b"
    r"|\bour (test|tests|run|runs|pipeline|extractor|benchmark|experiment|experiments)\b", re.I)


def experience_unanchored(sentence: str, notes: str) -> str | None:
    """Why a first-person experience sentence is refused, or None.

    "We tried X and got Y" must retell a WHAT WE TRIED note (blog_experiences.yaml):
    the sentence carries a figure from a note, or four consecutive words of one.
    With no notes for this post, any first-person experience is refused - the
    post states an opinion or quotes an engineer instead. Never an invented one.
    """
    m = EXPERIENCE.search(sentence)
    if not m:
        return None
    if not notes:
        return f"first-person experience ({m.group(0)!r}) but this post has no WHAT WE TRIED note to retell"
    body = norm(sentence)
    nums = re.sub(r"(?<=\d),(?=\d{3})", "", notes)
    for num in NUMBER.findall(body):
        bare = num.strip("$%").replace(",", "")
        if len(bare) >= 2 and re.search(rf"(?<![\d.]){re.escape(bare)}(?![\d])", nums):
            return None
    words = re.findall(r"[a-z0-9.$'-]+", body.lower())
    low = " ".join(re.findall(r"[a-z0-9.$'-]+", notes.lower()))
    if any(" ".join(words[i:i + 4]) in low for i in range(len(words) - 3)):
        return None
    return (f"first-person experience ({m.group(0)!r}) that retells no WHAT WE TRIED note - "
            "carry the note's figure or wording, or make it an opinion")


def _kw_in(text: str, kw: str) -> bool:
    """Every word of the keyword appears in the text, in order (case and
    punctuation ignored): 'Claude Opus 5 vs GPT-6 Sol' reads 'claude opus 5 vs gpt 6 sol'."""
    toks = re.findall(r"[a-z0-9]+", norm(text).lower())
    want = re.findall(r"[a-z0-9]+", kw.lower())
    it = iter(toks)
    return bool(want) and all(w in it for w in want)


def seo_violations(essay: dict, seo: dict) -> list[str]:
    """The primary keyword where search reads it, and a FAQ that answers."""
    v: list[str] = []
    kw = seo.get("primary") or ""
    if kw:
        if not _kw_in(essay.get("title", ""), kw):
            v.append(f"title: must contain the primary keyword {kw!r}")
        if not _kw_in(essay.get("description", ""), kw):
            v.append(f"description: must contain the primary keyword {kw!r}")
        secs = essay.get("sections") or [{}]
        first_par = (secs[0].get("paragraphs") or [""])[0]
        if not (_kw_in(essay.get("tldr", ""), kw) or _kw_in(first_par, kw)):
            v.append(f"tldr or first paragraph: must contain the primary keyword {kw!r}")
        kws = essay.get("keywords") or []
        if not kws or not _kw_in(kws[0], kw):
            v.append(f"keywords: list the primary keyword {kw!r} first")
    faq = essay.get("faq") or []
    if len(faq) != 3:
        v.append(f"faq: needs exactly 3 questions, has {len(faq)}")
    for i, qa in enumerate(faq):
        q, a = (qa or {}).get("question", ""), (qa or {}).get("answer", "")
        if not q.strip().endswith("?"):
            v.append(f"faq[{i}].question: phrase it as the question a searcher types, ending with '?'")
        n = len(GUILLEMET.sub(r"\1", a).split())
        if not 40 <= n <= 90:
            v.append(f"faq[{i}].answer: {n} words; answer in 40 to 90")
        first = sentences(a)[:1]
        if first and len(first[0].split()) > 30:
            v.append(f"faq[{i}].answer: open with a direct one-sentence answer of at most 30 words")
    names = seo.get("subject") or ([kw] if kw else [])
    if names and faq and not any(_kw_in((qa or {}).get("question", ""), n) for qa in faq for n in names):
        v.append(f"faq: at least one question must name {' or '.join(map(repr, names))}")
    # TAKING POSITIONS (2026-10-13). The first sample under the blogger voice
    # agreed or disagreed with nobody: a format's own voice overrode it. Two
    # stance sentences is the floor, not a style - a post may hold many more.
    stances = sum(1 for _p, t in prose_fields(essay) for snt in sentences(GUILLEMET.sub("", t))
                  if STANCE.search(snt))
    if stances < 2:
        v.append(f"voice: {stances} sentence(s) take a position; write at least 2 where we agree, "
                 "disagree or give our view (\"we agree with ...\", \"we are not convinced ...\", \"in our view ...\")")
    return v


#: A sentence where WE take a position on a claim or a choice.
STANCE = re.compile(
    r"\bwe(?:'d| would| do| don't| do not| are| aren't)? (agree|disagree|think|believe|doubt|recommend|"
    r"prefer|suspect|would not|wouldn't|push back|side with|are not convinced|aren't convinced)\b"
    r"|\bwe(?:'re| are) (not )?(convinced|skeptical|sceptical|wary)\b|\bin our (view|experience|reading)\b"
    r"|\bour (take|view|verdict|advice)\b", re.I)


def _distinctiveness(essay: dict, rules: dict) -> list[str]:
    """The checks that keep one format's posts from reading like another's
    (2026-10-05): paragraph size and rhythm, heading rules, headings already
    used elsewhere, and the format's signature block."""
    v: list[str] = []
    secs = essay.get("sections", [])
    paras = [p for s in secs for p in s.get("paragraphs", [])]
    lo, hi = rules["para_words"]
    sizes = [len(GUILLEMET.sub(r"\1", p).split()) for p in paras]
    if sizes:
        med = sorted(sizes)[len(sizes) // 2]
        if not lo <= med <= hi:
            v.append(f"paragraphs: median length is {med} words; this format wants {lo} to {hi}")
        for i, n in enumerate(sizes):
            if n > hi * 1.5:
                v.append(f"paragraph {i + 1}: {n} words is far longer than this format's {lo}-{hi}; split it")
        firsts = [re.sub(r"[^a-z]", "", (p.split() or [""])[0].lower()) for p in paras]
        top = max(set(firsts), key=firsts.count) if firsts else ""
        if top and firsts.count(top) >= 3 and firsts.count(top) > len(firsts) / 3:
            v.append(f"paragraphs: {firsts.count(top)} of {len(firsts)} open with '{top}'; vary the openings")
    heads = [s.get("heading", "") for s in secs]
    taken = rules.get("taken_headings") or set()
    for i, h in enumerate(heads):
        if rules.get("heading_question") and not h.strip().endswith("?"):
            v.append(f"sections[{i}].heading: this format's headings are questions ending with '?': {h!r}")
        if rules.get("heading_no_wh") and _WH.match(h):
            v.append(f"sections[{i}].heading: must not start with What/Why/How: {h!r}")
        if norm_heading(h) in taken:
            v.append(f"sections[{i}].heading: another post already uses {h!r}; write a different one")
    firstw = [norm_heading(h).split(" ")[0] for h in heads if norm_heading(h)]
    for w in set(firstw):
        if firstw.count(w) > 2:
            v.append(f"headings: {firstw.count(w)} start with '{w}'; vary them")
    key = rules.get("special")
    if key:
        sp = SPECIALS[key]
        items = essay.get(key) or []
        ilo, ihi = sp["items"]
        if not ilo <= len(items) <= ihi:
            v.append(f"{key}: needs {ilo} to {ihi} items, has {len(items)}")
        for i, it in enumerate(items):
            for f in sp["fields"]:
                if not str((it or {}).get(f, "")).strip():
                    v.append(f"{key}[{i}].{f}: empty")
        names = rules.get("pick_names") or []
        if key == "picks" and names:
            norm_names = {norm_heading(n): n for n in names}
            for i, it in enumerate(items):
                if norm_heading((it or {}).get("pick", "")) not in norm_names:
                    v.append(f"picks[{i}].pick must be exactly one of {names}")
            for n in names:
                if sum(norm_heading((it or {}).get("pick", "")) == norm_heading(n) for it in items) < 2:
                    v.append(f"picks: needs at least two items for {n}")
    v += _pace(essay, heads, paras, rules.get("prose"))
    return v


#: A LAST HEADING THAT IS A CHOICE. Was, on 2026-10-06, the last section of 11
#: of the 12 drafts ("When to use...", "Should your team adopt...", "How should
#: an incoming task be routed?"). The closing is the format's own
#: (blog_formats.yaml `closing`).
CHOICE_HEADING = re.compile(
    r"\b(choos\w*|choice|select\w*|which\b|when to use|should (you|your|teams?)\b|pick\w*|adopt\w*|"
    r"rout(e|es|ed|ing)\b)", re.I)


def sentences(text: str) -> list[str]:
    """Sentences of a paragraph. A «fragment»'s own full stops do not end one."""
    flat = GUILLEMET.sub(lambda m: "\u00ab" + re.sub(r"[.!?]", "", m.group(1)) + "\u00bb", text)
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\u00ab`(\d])", flat) if s.strip()]


def _pace(essay: dict, heads: list[str], paras: list[str], prose: dict | None) -> list[str]:
    """FAST PROSE, CHECKED (2026-10-06): sentence length, lead length, and a
    last section that is the format's closing rather than a choice."""
    if not prose:
        return []
    v: list[str] = []
    sents = [s for p in paras for s in sentences(p)]
    lens = [len(GUILLEMET.sub(r"\1", s).split()) for s in sents]
    if lens:
        med = sorted(lens)[len(lens) // 2]
        if med > prose["sentence_median_max"]:
            # NAMES THE LONGEST (2026-10-13): "split the long ones" alone held a
            # draft at a median of 16 for four repairs running.
            longest = sorted(zip(lens, sents, strict=True), key=lambda t: -t[0])[:4]
            shown = "; ".join(f"({n} words) {snt[:80]!r}" for n, snt in longest)
            v.append(f"sentences: the median is {med} words; keep it at {prose['sentence_median_max']} "
                     f"or under - split the long ones, starting with: {shown}")
        for s, n in [(s, n) for s, n in zip(sents, lens, strict=True) if n > prose["sentence_max"]][:5]:
            v.append(f"a sentence of {n} words (limit {prose['sentence_max']}); split it: {s[:90]!r}")
    lw = len(GUILLEMET.sub(r"\1", essay.get("tldr", "")).split())
    if lw > prose["lead_words_max"]:
        v.append(f"tldr: {lw} words; the lead is one line of at most {prose['lead_words_max']} words")
    if heads and CHOICE_HEADING.search(heads[-1]):
        v.append(f"sections[{len(heads) - 1}].heading: the last section is this format's closing, "
                 f"not a choice between options: {heads[-1]!r}")
    v += _lively(paras, lens, prose)
    return v


_LEANS_BACK = re.compile(r"^\s*(this|that|it|these|those|such)\b", re.I)
_CONTENT_WORD = re.compile(r"[A-Za-z][A-Za-z0-9\-.]{4,}")


def _lively(paras: list[str], lens: list[int], prose: dict) -> list[str]:
    """LIVELIER AND LESS ALIKE (blog_formats.yaml `prose`, measured 2026-10-08):
    a short sentence in most long paragraphs, stock words capped, set phrases
    refused, and prices left to the rate card. Rhythm is NOT here: it is a
    recorded reading (`rhythm_cv`), not a gate - see blog_formats.yaml."""
    v: list[str] = []
    multi = [p for p in paras if len(sentences(p)) >= 3]
    if multi:
        short_n = prose["short_sentence_words"]
        with_short = sum(1 for p in multi
                         if any(len(GUILLEMET.sub(r"\1", s).split()) <= short_n for s in sentences(p)))
        share = with_short / len(multi)
        if share < prose["short_sentence_paragraph_share_min"]:
            # NAMES THE PARAGRAPHS (2026-10-13): the count alone held a draft for
            # two repairs. Each is shown by its opening words.
            lacking = [p for p in multi
                       if not any(len(GUILLEMET.sub(r"", s).split()) <= short_n for s in sentences(p))]
            shown = "; ".join(repr(" ".join(p.split()[:8]) + " ...") for p in lacking[:4])
            v.append(f"rhythm: {with_short} of {len(multi)} longer paragraphs have a sentence of {short_n} "
                     f"words or fewer; want at least {int(prose['short_sentence_paragraph_share_min'] * 100)}% - "
                     f"add a short sentence to: {shown}")
    body = GUILLEMET.sub(" ", " ".join(paras)).lower()
    words = re.findall(r"[a-z]+", body)
    for w, cap in prose["word_caps"].items():
        n = words.count(w)
        if n > cap:
            # THE REFUSAL NAMES THE SENTENCES (2026-10-13). A count alone left the
            # model with nothing to act on: the DeepSeek V4 Flash field report
            # held at 'whether' x3 for three repairs running and the build
            # stopped. Same fix as the verbatim hints: say exactly where.
            where = [snt for p in paras for snt in sentences(GUILLEMET.sub(" ", p))
                     if re.search(rf"\b{re.escape(w)}\b", snt, re.I)]
            shown = "; ".join(f"{snt[:90]!r}" for snt in where[:4])
            v.append(f"vocabulary: '{w}' used {n} times (at most {cap}); rewrite {n - cap} of these "
                     f"without it: {shown}")
    for phrase in prose["avoid_phrases"]:
        if phrase.lower() in body:
            v.append(f"vocabulary: the stock phrase '{phrase}' is refused; say it another way")
    n_price = body.count("per million")
    if n_price > prose["price_recital_max"]:
        v.append(f"prices recited {n_price} times in prose ('per million'); the rate card shows them - "
                 f"keep at most {prose['price_recital_max']}")
    return v


def rhythm_cv(essay: dict | None) -> float | None:
    """Sentence-length spread / mean over the essay's paragraphs, RECORDED on
    each attempt beside `prose.rhythm_cv_target` (rule 8: unmeasured, so not a
    gate). Read by the attempt line below and kept in the run record, which is
    where a later calibration reads it. None when there are too few sentences
    to say - not 0, which would read as perfectly even."""
    import statistics

    paras = [p for s in (essay or {}).get("sections") or [] for p in s.get("paragraphs") or []]
    lens = [len(GUILLEMET.sub(r"\1", s).split()) for p in paras for s in sentences(p)]
    if len(lens) < 4 or statistics.mean(lens) == 0:
        return None
    return round(statistics.pstdev(lens) / statistics.mean(lens), 3)


TRANSIENT_RETRIES = 2


def call_transient_safe(key, base, messages, label, record, tool=None) -> dict:
    import time

    for n in range(TRANSIENT_RETRIES + 1):
        try:
            return call_model(key, base, messages, tool)
        except (ProviderTransient, httpx.TransportError) as e:
            record.setdefault("transient_errors", []).append(str(e)[:300])
            if n == TRANSIENT_RETRIES:
                raise BuildError(f"provider failed {n + 1} times running: {e}") from e
            print(f"  [{label}] provider error, retrying the same request: {str(e)[:120]}", flush=True)
            time.sleep(10 * (n + 1))
    raise AssertionError("unreachable")


def synthesise(post, docs, facts, key, base) -> dict:
    context = "\n".join(d["text"] for d in docs) + "\n" + fact_lines(facts)
    seed = [{"role": "system", "content": post.get("system", SYSTEM)},
            {"role": "user", "content": user_message(post, docs, facts)}]
    messages = seed[:]
    best = None
    record = post["_record"] = {"post": post["key"], "requested_model": GEN_MODEL,
              "started": datetime.now(UTC).isoformat(timespec="seconds"),
              "selection": post.get("_selection"),
              "documents": [{k: d[k] for k in ("thread_context_id", "source", "chars", "truncated", "why") if k in d}
                            for d in docs],
              "facts": [f["canonical_id"] for f in facts], "attempts": [], "passed": False,
              "plan": post.get("plan")}
    try:
        for attempt in range(1 + MAX_REPAIRS):
            got = call_transient_safe(key, base, messages, post["key"], record, post.get("tool"))
            ui_status(item=post["key"], item_state="checking", attempt=attempt + 1)
            raw = got["call"]["function"]["arguments"]
            wrapped = False
            try:
                essay = json.loads(raw)
                # Measured 2026-10-01: after a malformed draw Flash nested the
                # whole essay as {"arguments": {...}} three times running. The
                # content is all there; unwrap it, record that we did, and let
                # the full check run on what is inside.
                while isinstance(essay, dict) and list(essay) == ["arguments"]:
                    inner = essay["arguments"]
                    essay = json.loads(inner) if isinstance(inner, str) else inner
                    wrapped = True
                if not isinstance(essay, dict):
                    raise json.JSONDecodeError("not an object", raw, 0)
                violations = check(essay, context, post.get("rules"),
                                   post.get("experience_text", ""), post.get("seo"),
                                   [d["text"] for d in docs] if post.get("names") else None)
            except json.JSONDecodeError as e:
                essay, violations = None, [f"arguments are not valid JSON: {e}"]
            record["attempts"].append({"served": got["served"], "provider": got["provider"],
                                       "generation_id": got["generation_id"], "unwrapped": wrapped,
                                       "usage": got["usage"], "violations": violations,
                                       "rhythm_cv": rhythm_cv(essay),
                                       "essay": essay, "raw": None if essay else raw})
            # EVERY CALL IS SPEND, a refused draft included: into the ledger now.
            record_spend(record, len(record["attempts"]) - 1)
            print(f"  [{post['key']}] attempt {attempt + 1}: served={got['served']} "
                  f"violations={len(violations)} words={words_in(essay) if essay else '-'} "
                  f"rhythm={record['attempts'][-1]['rhythm_cv']} "
                  f"(target {((post.get('rules') or {}).get('prose') or {}).get('rhythm_cv_target', 'n/a')}, recorded)")
            if not violations:
                record["passed"], record["essay"] = True, essay
                return record
            if essay is None or not essay.get("sections"):
                # NOTHING TO REPAIR IN THIS DRAW. Measured 2026-10-01: feeding a
                # broken call back produced two empty essays in a row. Fall back
                # to the best draft so far if there is one - a Gemini run threw
                # away a 3-violation draft by restarting from the brief here -
                # and only start over when nothing usable exists yet.
                if best is None:
                    messages = seed[:]
                continue
            # REPAIR FROM THE BEST DRAFT SO FAR, NOT THE LATEST. Measured
            # 2026-10-01: an Opus run went 24 -> 9 -> 5 -> 10 violations, because
            # every repair rewrites the whole essay and a bad round threw away
            # the 5-violation draft. One draft in the prompt, never the history.
            if best is None or len(violations) < len(best[1]):
                best = (got, violations)
            b_got, b_viol = best
            messages = seed + [
                {"role": "assistant", "content": b_got["message"].get("content") or "",
                 "tool_calls": [b_got["call"]]},
                {"role": "tool", "tool_call_id": b_got["call"]["id"],
                 "content": ("REJECTED by the checker. Call publish_essay again with the COMPLETE essay: "
                             "copy every section, paragraph, matrix row and branch unchanged EXCEPT the "
                             "exact items listed, and fix those without introducing new problems:\n- "
                             + "\n- ".join(b_viol[:60]))},
            ]
        raise BuildError(f"{post['key']}: still failing after {MAX_REPAIRS} repairs: "
                         + "; ".join(record['attempts'][-1]['violations'][:8]))
    finally:
        save(record)


def ledger_kwargs(record: dict, i: int) -> dict:
    """The `spend_ledger.record` arguments for attempt `i` of a synthesis record:
    one model call, stage 'blog', OUTSIDE the daily cap (judge/spend_ledger.py).

    THE SAME FOR A LIVE CALL AND A BACKFILL (scripts/backfill_blog_spend.py), so
    both produce one ledger id and recording a call twice is a no-op. Hence
    `at` is the synthesis's start, not the call's moment - a post's attempts
    fall within its few minutes, and the ledger is read by month - and the
    attempt number is in `run_id`, which also names the saved record file.

    usd is what OpenRouter REPORTED for the call (`usage.cost`); a call it did
    not price is `unpriced` (usd 0), never priced here on a guess. A transport
    error before a response is not a row: no usage was returned for it.
    """
    a = record["attempts"][i]
    u = a.get("usage") or {}
    return {
        "stage": "blog",
        "model": a.get("served") or record.get("requested_model") or GEN_MODEL,
        "input_tokens": int(u.get("prompt_tokens") or 0),
        "output_tokens": int(u.get("completion_tokens") or 0),
        "at": datetime.fromisoformat(record["started"]),
        "run_id": f"blog:{record['post']}@{record['started']}#{i + 1}",
        "reported": True,
        "reported_usd": u.get("cost"),
    }


def record_spend(record: dict, i: int) -> None:
    """Write attempt `i` to the spend ledger: the local file, then the shared
    table. Never raises - the call is already paid for, and a lost telemetry row
    must not lose the draft as well.

    ⚠ THE DSN IS PASSED, NOT LEFT TO THE ENVIRONMENT. `env()` reads .env into a
      dict and never sets os.environ, so a run started from a terminal has no
      DATABASE_URL there, and `spend_ledger.record` alone wrote the local file
      only - silently (found 2026-10-07, when the backfill did the same thing).
    """
    try:
        from judge import spend_ledger

        call = spend_ledger.record(**ledger_kwargs(record, i), to_database=False)
        dsn = env().get("DATABASE_URL")
        if not dsn:
            print(f"  [{record['post']}] spend kept in the local ledger file only: no "
                  "DATABASE_URL", flush=True)
            return
        spend_ledger.append_to_database([call], dsn=dsn)
    except Exception as e:  # noqa: BLE001
        print(f"  [{record['post']}] spend not recorded: {type(e).__name__}: {e}", flush=True)


def save(record: dict) -> Path:
    d = RUNS / record["post"]
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{record['started'].replace(':', '')}.json"
    p.write_text(json.dumps(record, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return p


def latest_passing(key: str) -> dict:
    for p in sorted((RUNS / key).glob("*.json"), reverse=True):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("passed") and rec.get("requested_model") == GEN_MODEL:
            return rec
    raise BuildError(f"--reuse: no passing run saved for {key!r} under {RUNS / key}")


# ── 4 · rendering ────────────────────────────────────────────────────────────

CSS = """
:root{
  --bg:#0a0c10; --panel:#10141b; --panel2:#151a23; --line:#222a36; --line2:#2c3544;
  --text:#e8edf5; --body:#c9d2df; --muted:#95a1b4; --dim:#667286;
  --accent:#7aa2ff; --accent2:#a78bfa; --good:#3ecf8e; --bad:#f2716b; --neu:#8492a8; --warn:#e3b341;
  --sans:Inter,"Segoe UI",system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif;
  --mono:"JetBrains Mono","SF Mono",ui-monospace,Menlo,Consolas,monospace;
  --radius:14px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:
  radial-gradient(900px 480px at 12% -8%,rgba(122,162,255,.09),transparent 60%),
  radial-gradient(760px 420px at 100% 0%,rgba(167,139,250,.07),transparent 60%),var(--bg);
  color:var(--text);font:17.5px/1.75 var(--sans);-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.topbar{border-bottom:1px solid var(--line);background:rgba(10,12,16,.72);backdrop-filter:blur(8px);
  position:sticky;top:0;z-index:5}
.topbar .in{max-width:1200px;margin:0 auto;padding:.7rem 1.2rem;display:flex;gap:1rem;align-items:center;
  font-family:var(--mono);font-size:.78rem;color:var(--muted)}
.topbar b{color:var(--text);letter-spacing:.06em}
.wrap{max-width:1200px;margin:0 auto;padding:2.8rem 1.2rem 5rem}
.hero{max-width:880px;margin-bottom:2.4rem}
.kicker{font-family:var(--mono);font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;color:var(--accent)}
h1{font-size:clamp(2rem,4.4vw,3.2rem);line-height:1.08;letter-spacing:-.025em;margin:.55rem 0 .9rem;font-weight:700}
.dek{font-size:1.22rem;line-height:1.6;color:var(--muted);max-width:62ch;margin:0}
.byline{margin-top:1.1rem;font-family:var(--mono);font-size:.78rem;color:var(--dim);display:flex;gap:1.1rem;flex-wrap:wrap}
.tags{display:flex;gap:.45rem;flex-wrap:wrap;margin-top:.9rem}
.tag{font-family:var(--mono);font-size:.7rem;padding:.18rem .6rem;border:1px solid var(--line2);border-radius:999px;color:var(--muted)}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:3.2rem;align-items:start}
@media(max-width:1000px){.layout{grid-template-columns:1fr}.side{order:-1}}
article{min-width:0;max-width:770px}
article p{color:var(--body);margin:1.1rem 0}
article h2{font-size:1.66rem;letter-spacing:-.015em;line-height:1.25;margin:3.4rem 0 .5rem;padding-top:.4rem}
article h2 .num{font-family:var(--mono);font-size:.78rem;color:var(--accent);display:block;letter-spacing:.14em;margin-bottom:.35rem}
article h3{font-size:1.14rem;margin:2.1rem 0 .2rem;color:var(--text)}
.thesis{font-size:1.08rem;color:#dde4ef !important;border-left:2px solid var(--line2);padding-left:1rem}
code{font-family:var(--mono);font-size:.86em;background:var(--panel2);border:1px solid var(--line);
  border-radius:6px;padding:.08rem .36rem;color:#dbe4ff}
q.iq{quotes:"\\201C" "\\201D";color:#e9eef8;font-style:italic}
.takeaway{background:linear-gradient(180deg,var(--panel2),var(--panel));border:1px solid var(--line2);
  border-left:3px solid var(--accent);border-radius:var(--radius);padding:1.35rem 1.55rem;margin:0 0 2.2rem}
.takeaway .lbl{font-family:var(--mono);font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
.takeaway p{margin:.55rem 0 0;color:#dde4ef;font-size:1.06rem}
figure.pq{margin:1.6rem 0;padding:1.1rem 1.35rem;background:var(--panel);border:1px solid var(--line);
  border-left:3px solid var(--accent2);border-radius:0 12px 12px 0}
figure.pq blockquote{margin:0;font-size:1.05rem;line-height:1.62;color:#e9eef7}
figure.pq blockquote::before{content:"\\201C";color:var(--dim);margin-right:.1rem}
figure.pq blockquote::after{content:"\\201D";color:var(--dim)}
figure.pq figcaption{margin-top:.55rem;font-family:var(--mono);font-size:.72rem;color:var(--dim);letter-spacing:.04em}
.chart{margin:1.7rem 0 2rem;padding:1.15rem 1.15rem .75rem;background:var(--panel);border:1px solid var(--line);border-radius:var(--radius)}
.chart .cap{font-family:var(--mono);font-size:.74rem;color:var(--dim);margin:.45rem .2rem 0;line-height:1.55}
.chart .ttl{font-weight:600;font-size:.96rem;margin:0 .2rem .6rem;color:var(--text)}
svg{display:block;width:100%;height:auto}
.svt{font-family:var(--mono);font-size:12px;fill:var(--muted)}
.svs{font-family:var(--mono);font-size:11px;fill:var(--dim)}
.svb{font-family:var(--sans);font-size:13px;fill:var(--text);font-weight:600}
.svh{font-family:var(--mono);font-size:11px;fill:var(--accent);letter-spacing:.12em}
.good{fill:var(--good)} .bad{fill:var(--bad)} .neu{fill:var(--neu)} .acc{fill:var(--accent)} .acc2{fill:var(--accent2)}
.gridl{stroke:var(--line);stroke-width:1} .axis{stroke:var(--line2);stroke-width:1}
.tbl{border:1px solid var(--line);border-radius:12px;overflow:hidden;overflow-x:auto;margin:1.4rem 0 1.7rem}
table{width:100%;border-collapse:collapse;font-size:.9rem;margin:0}
th,td{padding:.66rem .85rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{font-family:var(--mono);font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);background:var(--panel2);font-weight:500}
td{color:var(--body)} tr:last-child td{border-bottom:0}
td.n{font-family:var(--mono);text-align:right;white-space:nowrap;color:var(--text)}
td b{color:var(--text)}
.bdg{font-family:var(--mono);font-size:.68rem;padding:.14rem .52rem;border-radius:999px;border:1px solid;white-space:nowrap}
.bdg.g{color:var(--good);border-color:rgba(62,207,142,.4)} .bdg.r{color:var(--bad);border-color:rgba(242,113,107,.4)}
.bdg.y{color:var(--warn);border-color:rgba(227,179,65,.4)} .bdg.b{color:var(--accent);border-color:rgba(122,162,255,.4)}
.bdg.p{color:var(--accent2);border-color:rgba(167,139,250,.4)} .bdg.m{color:var(--muted);border-color:var(--line2)}
.ratios{display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem;margin:1.3rem 0}
@media(max-width:640px){.ratios{grid-template-columns:1fr}}
.ratio{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:1rem}
.ratio .v{font-family:var(--mono);font-size:1.7rem;font-weight:600;color:var(--text);line-height:1}
.ratio .k{font-size:.82rem;color:var(--muted);margin-top:.4rem;line-height:1.45}
.callout{border:1px solid var(--line2);background:var(--panel2);border-radius:12px;padding:1rem 1.25rem;margin:1.5rem 0}
.callout .lbl{font-family:var(--mono);font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;color:var(--warn)}
.callout p{margin:.45rem 0 0;font-size:.95rem}
.codehead{font-family:var(--mono);font-size:.72rem;color:var(--dim);margin:1.6rem 0 -.9rem;letter-spacing:.06em}
pre{background:#0d1117;border:1px solid var(--line);border-radius:12px;padding:1rem 1.15rem;overflow-x:auto;
  font-family:var(--mono);font-size:.8rem;line-height:1.65;color:#c9d6ea;margin:1.3rem 0}
pre .c{color:#6f7f96} pre .s{color:#8fd6a6} pre .k{color:#c4a5ff}
.side{position:sticky;top:4.4rem}
@media(max-width:1000px){.side{position:static}}
.scard{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:1.1rem 1.2rem}
.scard + .scard{margin-top:1rem}
.scard .lbl{font-family:var(--mono);font-size:.68rem;letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}
.scard ol{margin:.6rem 0 0;padding-left:1.15rem;font-size:.88rem}
.scard ol li{margin:.32rem 0;color:var(--muted)}
.scard ol li a{color:var(--muted)} .scard ol li a:hover{color:var(--text)}
.scard ul.dec{list-style:none;margin:.6rem 0 0;padding:0;font-size:.88rem}
.scard ul.dec li{position:relative;padding-left:1.15rem;margin:.55rem 0;color:var(--body);line-height:1.5}
.scard ul.dec li::before{content:"\\2192";position:absolute;left:0;color:var(--accent);font-family:var(--mono)}
.scard a.rel{display:block;padding:.55rem .7rem;border:1px solid var(--line);border-radius:10px;margin-top:.5rem;font-size:.86rem}
footer{margin-top:4rem;border-top:1px solid var(--line);padding-top:1.4rem;color:var(--dim);font-size:.82rem;max-width:770px}
.hub-h{max-width:840px;margin-bottom:2.4rem}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:1.2rem}
.card{display:block;background:linear-gradient(180deg,var(--panel2),var(--panel));border:1px solid var(--line);
  border-radius:var(--radius);padding:1.45rem 1.45rem 1.2rem;color:var(--text);transition:border-color .15s,transform .15s}
.card:hover{border-color:var(--line2);transform:translateY(-2px);text-decoration:none}
.card h3{font-size:1.3rem;line-height:1.3;margin:.55rem 0 .5rem;letter-spacing:-.01em}
.card p{color:var(--muted);font-size:.93rem;margin:.4rem 0}
.card .meta{display:flex;justify-content:space-between;font-family:var(--mono);font-size:.72rem;color:var(--dim);margin-top:1rem}
.card .sum{border-top:1px solid var(--line);margin-top:.9rem;padding-top:.8rem;font-size:.88rem;color:var(--body)}
""" + """
.tldr{background:linear-gradient(180deg,var(--panel2),var(--panel));border:1px solid var(--line2);
  border-left:3px solid var(--accent);border-radius:var(--radius);padding:1.35rem 1.55rem;margin:0 0 2.2rem}
.tldr .lbl{font-family:var(--mono);font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
.tldr p{margin:.55rem 0 0;color:#dde4ef;font-size:1.06rem}
.mx td.route{white-space:nowrap}
.dtree{margin:1.6rem 0 2.2rem}
.dtree .q{background:var(--panel2);border:1px solid var(--accent);border-radius:12px;padding:.9rem 1.15rem;
  font-weight:600;color:var(--text);text-align:center;max-width:560px;margin:0 auto;position:relative}
.dtree .q::after{content:"";position:absolute;left:50%;bottom:-1.3rem;height:1.3rem;border-left:1px solid var(--line2)}
.dtree .br{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:.9rem;margin-top:1.3rem;
  padding-top:1.3rem;border-top:1px solid var(--line2)}
.dtree .b{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:.9rem 1rem;position:relative}
.dtree .b::before{content:"";position:absolute;left:50%;top:-1.3rem;height:1.3rem;border-left:1px solid var(--line2)}
.dtree .cond{font-family:var(--mono);font-size:.74rem;color:var(--warn);letter-spacing:.02em}
.dtree .out{color:var(--body);font-size:.92rem;margin:.45rem 0 .6rem;line-height:1.5}
.illus{font-family:var(--mono);font-size:.66rem;letter-spacing:.12em;text-transform:uppercase;color:var(--accent2);margin-right:.5rem}
"""


def inline(text: str) -> str:
    s = esc(text)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"«([^»]+)»", r'<q class="iq">\1</q>', s)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "section"


def code_block(src: str, label: str) -> str:
    out = []
    for line in esc(src.rstrip()).split("\n"):
        i = line.find("#")
        out.append(line[:i] + f'<span class="c">{line[i:]}</span>' if i >= 0 else line)
    return (f'<div class="codehead"><span class="illus">Illustrative</span>{esc(label)}</div>'
            "<pre>" + "\n".join(out) + "</pre>")


def source_of(passage: str, docs) -> dict:
    """The document a verbatim passage came from. Raises if none holds it: the
    check already proved it is there, so a miss here is a defect, not absence."""
    n = norm(passage)
    for d in docs:
        if n in norm(d["text"]):
            return d
    raise BuildError(f"quoted passage not found at render time: {passage[:60]!r}")


def route_badge(route: str) -> str:
    r = route.lower()
    tone = "p" if "opus" in r else "b" if "sonnet" in r else "g" if "haiku" in r or "low" in r else "y"
    return f'<span class="bdg {tone}">{esc(route)}</span>'


def price_table(facts) -> str:
    rows = "".join(
        f"<tr><td><b>{esc(clean(f['display_name']))}</b></td>"
        f"<td class=\"n\">{esc(money(f['price_in']) or 'not published')}</td>"
        f"<td class=\"n\">{esc(money(f['price_out']) or 'not published')}</td>"
        f"<td class=\"n\">{esc(money(f['price_cached_read']) or 'not published')}</td></tr>"
        for f in facts)
    return ('<h3>List prices</h3><div class="tbl"><table><thead><tr><th>Model</th><th>Input $/M</th>'
            f'<th>Output $/M</th><th>Cached input $/M</th></tr></thead><tbody>{rows}</tbody></table></div>'
            '<p style="font-size:.85rem;color:var(--dim)">OpenRouter list prices as last polled into the '
            'registry. A price the provider does not publish is shown as not published, never as zero.</p>')


def render(post, essay, docs, facts):
    toc, body = [], []
    body.append(f'<div class="tldr"><div class="lbl">The short answer</div><p>{inline(essay["tldr"])}</p></div>')
    for i, s in enumerate(essay["sections"], 1):
        a = slug(s["heading"])
        toc.append((a, s["heading"]))
        body.append(f'<h2 id="{a}"><span class="num">{i:02d}</span>{esc(s["heading"])}</h2>')
        paras = [f"<p>{inline(p)}</p>" for p in s["paragraphs"]]
        if s.get("pull_quote"):
            pq = (f'<figure class="pq"><blockquote>{esc(s["pull_quote"])}</blockquote>'
                  f'<figcaption>Engineer report</figcaption></figure>')
            paras.insert(min(2, len(paras)), pq)
        if has_code(s):
            paras.append(code_block(s["code"]["source"], s["code"]["label"]))
        body += paras
    m, t = essay["scenario_matrix"], essay["decision_tree"]
    toc.append(("matrix", m["title"]))
    rows = "".join(f"<tr><td><b>{inline(r['scenario'])}</b></td><td>{inline(r['tradeoff'])}</td>"
                   f"<td>{inline(r['mitigation'])}</td><td class=\"route\">{route_badge(r['route'])}</td></tr>"
                   for r in m["rows"])
    body.append(f'<h2 id="matrix"><span class="num">Matrix</span>{esc(m["title"])}</h2>'
                '<div class="tbl mx"><table><thead><tr><th>Production scenario</th><th>Behavioral trade-off</th>'
                f'<th>Recommended mitigation</th><th>Route</th></tr></thead><tbody>{rows}</tbody></table></div>')
    toc.append(("decision", "Decision tree"))
    br = "".join(f'<div class="b"><div class="cond">{inline(b["condition"])}</div>'
                 f'<div class="out">{inline(b["outcome"])}</div>{route_badge(b["route"])}</div>'
                 for b in t["branches"])
    body.append(f'<h2 id="decision"><span class="num">Decision tree</span>{inline(t["question"])}</h2>'
                f'<div class="dtree"><div class="q">{inline(t["question"])}</div><div class="br">{br}</div></div>')
    body.append(price_table(facts))
    article = "\n".join(body)
    words = len(re.sub(r"<[^>]+>", " ", article).split())
    mins = max(1, math.ceil(words / 230))
    return article, toc, words, mins


def page(post, essay, article, toc, words, mins, related) -> str:
    title, desc = essay["title"], essay["description"][:160]
    ld = json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": title,
                     "description": desc, "datePublished": TODAY.isoformat(),
                     "dateModified": TODAY.isoformat(), "wordCount": words,
                     "keywords": essay["keywords"], "author": {"@type": "Organization", "name": ORG},
                     "publisher": {"@type": "Organization", "name": ORG}, "isAccessibleForFree": True},
                    ensure_ascii=False, indent=2).replace("</", "<\\/")
    tags = "".join(f'<span class="tag">{esc(x)}</span>' for x in post["tags"])
    toc_html = "".join(f'<li><a href="#{a}">{esc(h)}</a></li>' for a, h in toc)
    dec = "".join(f"<li>{inline(d)}</li>" for d in essay["decisions"])
    rel = "".join(f'<a class="rel" href="./{f}">{esc(t)}</a>' for t, f in related)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta name="robots" content="noindex,nofollow">
<script type="application/ld+json">
{ld}
</script>
<style>{CSS}</style>
</head>
<body>
<div class="topbar"><div class="in"><b>FIELD NOTES</b><span>{esc(ORG)}</span><span style="margin-left:auto"><a href="./index.html">All essays</a></span></div></div>
<div class="wrap">
<header class="hero"><div class="kicker">{esc(post["kicker"])}</div><h1>{esc(title)}</h1>
<p class="dek">{inline(essay["dek"])}</p><div class="byline"><span>{TODAY.strftime("%d %B %Y")}</span><span>{mins} min read</span></div>
<div class="tags">{tags}</div></header>
<div class="layout">
<article>
{article}
</article>
<aside class="side">
<div class="scard"><div class="lbl">In this essay</div><ol>{toc_html}</ol></div>
<div class="scard"><div class="lbl">Decisions it supports</div><ul class="dec">{dec}</ul></div>
<div class="scard"><div class="lbl">Continue reading</div>{rel}</div>
</aside>
</div>
<footer>
<p>Published {TODAY.isoformat()} · {esc(ORG)}. Synthesised by a language model from engineers' public
discussions. Passages in quotation marks are verified verbatim against the source text at build time, and
every figure in the prose is checked against the source text or the registry price sheet. Code samples are
illustrative patterns. No model is scored or ranked on quality.</p>
<p>Draft — not for external publication.</p>
</footer>
</div>
</body>
</html>
"""


def hub(entries) -> str:
    cards = []
    for post, essay, mins in entries:
        t = "".join(f'<span class="tag">{esc(x)}</span>' for x in post["tags"])
        cards.append(f'<a class="card" href="./{post["file"]}"><div class="kicker">{esc(post["kicker"])}</div>'
                     f'<h3>{esc(essay["title"])}</h3><p>{inline(essay["dek"])}</p><div class="tags">{t}</div>'
                     f'<div class="sum">{inline(essay["tldr"])}</div>'
                     f'<div class="meta"><span>{mins} min read</span><span>{TODAY.strftime("%d %b %Y")}</span></div></a>')
    ld = json.dumps({"@context": "https://schema.org", "@type": "CollectionPage", "name": f"Field Notes — {ORG}",
                     "hasPart": [{"@type": "Article", "headline": e["title"], "url": p["file"]}
                                 for p, e, _ in entries]}, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Field Notes — {esc(ORG)}</title>
<meta name="description" content="Long-form engineering essays on AI models in production.">
<meta property="og:title" content="Field Notes — {esc(ORG)}">
<meta property="og:description" content="Long-form engineering essays on AI models in production.">
<meta name="robots" content="noindex,nofollow">
<script type="application/ld+json">{ld}</script>
<style>{CSS}</style></head><body>
<div class="topbar"><div class="in"><b>FIELD NOTES</b><span>{esc(ORG)}</span></div></div>
<div class="wrap"><header class="hub-h"><div class="kicker">Field notes · {esc(ORG)}</div>
<h1>How AI models behave in production</h1><p class="dek">Long-form engineering essays on running frontier
models in real systems — the failure modes, the architecture that contains them, and the economics that decide
what is worth building.</p></header><div class="cards">{"".join(cards)}</div>
<footer><p>Draft — not for external publication.</p></footer></div></body></html>
"""


# ── UI export ────────────────────────────────────────────────────────────────

#: Where the UI's Blogs section reads drafts from. `judge/blog_posts.py` serves
#: this directory at GET /blog-posts; BLOG_POSTS_DIR in .env must point here.
POSTS_OUT = ROOT / "blog_posts"


def post_slug(post) -> str:
    return post["file"].removesuffix(".html")


def _export_special(post, essay, text):
    key = (post.get("format_cfg") or {}).get("special")
    if not key or not essay.get(key):
        return None
    sp = SPECIALS[key]
    return {"type": key, "title": sp["title"],
            "items": [{f: (text(str(it.get(f, ""))) if f in sp["prose"] else it.get(f))
                       for f in sp["fields"]} for it in essay[key]]}


def _arrangement_for(fmt_key: str | None, slug: str) -> str | None:
    """'a' or 'b': alternate by how many OTHER drafts of this format exist on
    this machine. None for a post with no format (the first three), which
    views.js then alternates by order."""
    if not fmt_key:
        return None
    same = 0
    for f in POSTS_OUT.glob("*.json"):
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if doc.get("slug") != slug and (doc.get("provenance") or {}).get("format") == fmt_key:
            same += 1
    return "ab"[same % 2]


def export_post(post, essay, docs, facts, rec, mins, rel_posts) -> Path:
    """Write one post in the shape `web/src/board/views.js` `vPost` renders.

    NO EVIDENCE PANEL OR BOOKMARKS (team decision, 2026-10-01): the post shows
    quotes as quotes and nothing else. The verbatim check still runs - here, on
    every fragment, at export - it is just not displayed. Attribution is
    "Engineer report": NO platform name, and no document source is exported.
    """

    def verified(frag: str) -> str:
        source_of(frag, docs)  # proves it is still in the text; raises otherwise
        return frag

    def text(t: str) -> str:
        # «fragment» stays marked so the page can style it as a quotation.
        return GUILLEMET.sub(lambda m: f"\u00ab{verified(m.group(1))}\u00bb", t)

    # Headings carry the essay layout's number and anchor, so the page can build
    # its "In this essay" contents from the body rather than from a second list.
    body: list[list] = []
    for n, s in enumerate(essay["sections"], 1):
        body.append(["h2", {"text": s["heading"], "num": f"{n:02d}", "id": slug(s["heading"])}])
        # NO SKIM LINES (2026-10-13): the skim view read as an incomplete post,
        # so paragraphs travel as plain text and the page shows them in full.
        paras = [["p", text(p)] for p in s["paragraphs"]]
        # A GENERATED PICTURE sits after the section's first paragraph, always
        # labelled as AI-generated on the page (views.js).
        for il in post.get("_illustrations") or []:
            if il["section"] == n - 1:
                paras.insert(1, ["image", {"src": il["src"], "alt": il["alt"], "caption": il["caption"],
                                           "generated_by": il["model"]}])
        if s.get("pull_quote"):
            paras.insert(min(2, len(paras)), ["quote", verified(s["pull_quote"])])
        body += paras
        if has_code(s):
            body.append(["code", {"label": s["code"]["label"], "language": s["code"].get("language", ""),
                                  "source": s["code"]["source"]}])
        # A TABLE, CHART OR DIAGRAM travels as one `visual` block (views.js
        # essayBlock draws it). Text is exported like prose: «fragments» verified.
        for vis in [x for x in essay.get("visuals") or [] if (x or {}).get("section") == n - 1][:1]:
            out = {"kind": vis["kind"], "caption": text(vis.get("caption", ""))}
            if vis["kind"] == "table":
                out |= {"columns": [text(c) for c in vis.get("columns") or []],
                        "rows": [[text(c) for c in r] for r in vis.get("rows") or []]}
            elif vis["kind"] == "chart":
                out |= {"unit": vis.get("unit", ""),
                        "bars": [{"label": text(b["label"]), "value": float(b["value"])} for b in vis["bars"]]}
            else:
                out |= {"steps": [text(x) for x in vis.get("steps") or []]}
            body.append(["visual", out])
    # A format may carry no matrix, no tree, or no price table; the three
    # original posts carry all three.
    m, t = essay.get("scenario_matrix"), essay.get("decision_tree")
    if m and m.get("rows"):
        body += [["h2", {"text": m["title"], "num": "Matrix", "id": "matrix"}],
                 ["table", {"kind": "matrix",
                            "cols": ["Production scenario", "Behavioral trade-off", "Recommended mitigation", "Route"],
                            "rows": [[text(r["scenario"]), text(r["tradeoff"]), text(r["mitigation"]), r["route"]]
                                     for r in m["rows"]]}]]
    if t and t.get("branches"):
        body += [["h2", {"text": t["question"], "num": "Decision tree", "id": "decision"}],
                 ["tree", {"question": t["question"],
                           "branches": [{"condition": text(b["condition"]), "outcome": text(b["outcome"]),
                                         "route": b["route"]} for b in t["branches"]]}]]
    # THE FAQ IS A SECTION OF ITS OWN (2026-10-13): question headings and short
    # direct answers, the shape search engines quote. Rendered by views.js as an
    # ordinary section - h3 per question, a paragraph per answer.
    if essay.get("faq"):
        body.append(["h2", {"text": "Questions people ask", "num": "FAQ", "id": "faq"}])
        for qa in essay["faq"]:
            body += [["h3", qa["question"]], ["p", text(qa["answer"])]]
    if post.get("prices", True) and facts:
        body += [["h3", "List prices"],
                 ["table", {"kind": "prices", "cols": ["Model", "Input $/M", "Output $/M", "Cached input $/M"],
                            "rows": [[clean(f["display_name"]), money(f["price_in"]) or "not published",
                                      money(f["price_out"]) or "not published",
                                      money(f["price_cached_read"]) or "not published"] for f in facts],
                            "note": ("OpenRouter list prices as last polled into the registry. A price the "
                                     "provider does not publish is shown as not published, never as zero.")}]]
    served = sorted({a["served"] for a in rec.get("attempts", [])}) or [rec["requested_model"]]
    doc = {
        "slug": post_slug(post),
        "status": "draft",
        "tag": post["kicker"],
        "feat": post["key"] == "opus",
        "title": essay["title"],
        "dek": GUILLEMET.sub(r"\1", essay["dek"]),
        "by": "Draft for team review · written by a language model from engineers' public reports · checked in code",
        "lead": text(essay["tldr"]),
        # THE META DESCRIPTION AND KEYWORDS TRAVEL WITH THE POST (2026-10-13).
        # The model wrote both on every draft and export dropped them, so the
        # page's meta description fell back to the dek (rule 9: paid for and
        # never read). Read by web/src/seo/pages.js blogPost and structured.js.
        "description": GUILLEMET.sub(r"\1", essay.get("description") or "") or None,
        "keywords": [k for k in (essay.get("keywords") or []) if str(k).strip()],
        # The essay layout's hero and sidebar (read by views.js vPost).
        "kicker": post["kicker"],
        "tags": post["tags"],
        "read": mins,
        "decisions": [text(d) for d in essay["decisions"]],
        # The page structure this format renders with (views.js); absent on the
        # first three posts, which keep the original essay layout.
        "layout": (post.get("format_cfg") or {}).get("layout"),
        # WHICH OF THE FORMAT'S TWO ARRANGEMENTS (views.js arrangementOf). Two
        # head-to-heads shared one page (2026-10-08), so posts of a format
        # alternate a, b, a ... by how many of that format exist here already.
        # Recorded on the post, so a preview and the published page agree.
        "arrangement": _arrangement_for((post.get("plan") or {}).get("format"), post_slug(post)),
        "special": _export_special(post, essay, text),
        "meta": [TODAY.strftime("%d %B %Y"), f"~{mins} min read", "Draft — not reviewed"],
        "body": body,
        "rel": [[f"post:{slug}", title] for slug, title in rel_posts],
        # READ BY vPost's "How this draft was made" block (rule 9). No platform
        # and no per-document source field: thread ids only.
        "provenance": {
            "model": rec["requested_model"], "served_as": served,
            "generated_at": rec["started"], "rechecked_from": rec.get("rechecked_from"),
            "documents": [d["thread_context_id"] for d in docs],
            "checks": "verbatim quotes, figures, attributions and banned phrasing - passed",
            # The planner reads plan_key so it never writes the same
            # (format, subject) twice; legacy posts carry theirs from LEGACY_PLAN_KEYS.
            "plan_key": (post.get("plan") or {}).get("plan_key") or LEGACY_PLAN_KEYS.get(post["key"]),
            "format": (post.get("plan") or {}).get("format"),
            "reviewed_by": None,
        },
    }
    POSTS_OUT.mkdir(exist_ok=True)
    out = POSTS_OUT / f"{doc['slug']}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ── the planner: which posts to write next ────────────────────────────────────
#
# CODE DECIDES WHAT GETS WRITTEN; THE MODEL ONLY WRITES IT. Formats come from
# blog_formats.yaml (each read off the collected practitioner blogs), subjects
# from the board's own evidence. Nothing here calls a model.

FORMATS_FILE = ROOT / "blog_formats.yaml"
STRUCT_HEAD = "STRUCTURE (call publish_essay exactly once)"
#: The three original posts, so the planner treats their subjects as written.
LEGACY_PLAN_KEYS = {"opus": "deep-dive:anthropic/claude-opus-5",
                    "compare": "head-to-head:anthropic/claude-opus-5+anthropic/claude-sonnet-5",
                    "reasoning": "capability-analysis:capability/reasoning"}
VERIFIED = "be.quote_verified AND coalesce(be.ruling,'') <> 'declined'"


#: ONE STRUCTURED BLOCK PER FORMAT, ONLY THAT FORMAT CARRIES IT (2026-10-05).
#: The first nine posts drew on the same five blocks, so every page looked the
#: same whatever its format. Each entry: the tool-schema item, which fields are
#: prose (checked like any paragraph), item-count bounds, and the instruction.
#: `status` values are categorical words chosen from a fixed list - never a
#: number - so rule 3 is not in play.
SPECIALS: dict[str, dict] = {
    "findings": {
        "title": "Findings", "items": (4, 8), "prose": ["finding"],
        "fields": {"finding": {"type": "string"},
                   "status": {"type": "string", "enum": ["established", "not established"]}},
        "ask": "FINDINGS: 4 to 8 one-sentence findings about the subject, each marked 'established' "
               "(the discussions show it) or 'not established' (claimed or suspected, not shown).",
    },
    "picks": {
        "title": "Pick it when", "items": (4, 8), "prose": ["when"],
        "fields": {"pick": {"type": "string"}, "when": {"type": "string"}},
        "ask": "PICKS: 4 to 8 items; each names one of the two models exactly as given in SUBJECT "
               "('pick') and one concrete situation where it is the better choice ('when'). "
               "At least two for each model.",
    },
    "drivers": {
        "title": "Cost drivers", "items": (4, 7), "prose": ["driver", "mechanism", "lever"],
        "fields": {"driver": {"type": "string"}, "mechanism": {"type": "string"}, "lever": {"type": "string"}},
        "ask": "DRIVERS: 4 to 7 cost drivers: the driver (a short noun phrase), the mechanism by which "
               "it grows the bill, and the lever that reduces it. Figures only as the discussions give them.",
    },
    "steps": {
        "title": "Runbook", "items": (5, 9), "prose": ["step", "action", "check"],
        "fields": {"step": {"type": "string"}, "action": {"type": "string"}, "check": {"type": "string"}},
        "ask": "STEPS: 5 to 9 ordered migration steps: a short imperative title, the action to take, and "
               "the check that confirms it worked before moving on.",
    },
    "layers": {
        "title": "The layers", "items": (3, 6), "prose": ["layer", "role", "failure_contained"],
        "fields": {"layer": {"type": "string"}, "role": {"type": "string"},
                   "failure_contained": {"type": "string"}},
        "ask": "LAYERS: 3 to 6 architecture layers from the outside in: the layer's name, its role, and "
               "the failure it contains.",
    },
    "claims": {
        "title": "Claims against reality", "items": (3, 6), "prose": ["claim", "finding"],
        "fields": {"claim": {"type": "string"}, "finding": {"type": "string"},
                   "status": {"type": "string", "enum": ["holds", "partly holds", "not shown"]}},
        "ask": "CLAIMS: 3 to 6 claims made about the subject, what practitioners found, and whether the "
               "claim 'holds', 'partly holds' or is 'not shown' by the discussions.",
    },
    "probes": {
        "title": "What is measured, and what is missed", "items": (3, 6),
        "prose": ["measure", "tests", "misses"],
        "fields": {"measure": {"type": "string"}, "tests": {"type": "string"}, "misses": {"type": "string"}},
        "ask": "PROBES: 3 to 6 rows, one per evaluation or claim: what is reported ('measure'), what it "
               "actually tests ('tests'), and what it misses for a production workload ('misses').",
    },
}
_WH = re.compile(r"^\s*(what|why|how)\b", re.I)


def norm_heading(h: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", (h or "").lower())).strip()


def load_formats() -> dict:
    cfg = yaml.safe_load(FORMATS_FILE.read_text(encoding="utf-8"))
    need = {"key", "name", "subject", "shape", "layout", "voice", "paragraphs", "heading_rules",
            "special", "sections", "words", "blocks", "opening", "closing"}
    prose = cfg.get("prose") or {}
    lacking = {"sentence_median_max", "sentence_max", "lead_words_max", "rhythm_cv_target",
               "short_sentence_words", "short_sentence_paragraph_share_min", "word_caps", "avoid_phrases",
               "price_recital_max"} - set(prose)
    if lacking:  # rule 12: no limit in code stands in for one the file forgot
        raise BuildError(f"blog_formats.yaml: prose is missing {sorted(lacking)}")
    for f in cfg["formats"]:
        f["prose"] = prose
        missing = need - set(f)
        if missing:  # rule 12: a half-specified format must not run on defaults
            raise BuildError(f"blog_formats.yaml: format {f.get('key')!r} is missing {sorted(missing)}")
        if "visuals" not in (f.get("blocks") or {}):
            raise BuildError(f"blog_formats.yaml: format {f.get('key')!r} blocks has no `visuals` range")
        if f["special"] not in SPECIALS:
            raise BuildError(f"blog_formats.yaml: format {f['key']!r} names unknown special {f['special']!r}")
        # A FLOOR THE FORMAT'S OWN SHAPE CANNOT REACH IS A CONTRADICTION, NOT A
        # QUALITY BAR. Measured 2026-10-05: cost-teardown asked for 4-6
        # sections of 2-3 paragraphs of 40-90 words (typically ~810 words) with
        # a 1,000-word floor, and failed six rounds at ~880 words.
        mid = (sum(f["sections"]) / 2 * sum(f["paragraphs"]["per_section"]) / 2
               * sum(f["paragraphs"]["words"]) / 2)
        if f["words"][0] > mid:
            raise BuildError(f"blog_formats.yaml: format {f['key']!r} has a {f['words'][0]}-word floor, above the "
                             f"~{mid:.0f} words its sections/paragraphs produce; lower the floor or widen the shape")
    return cfg


def system_for(fmt: dict) -> str:
    """SYSTEM with its STRUCTURE section rebuilt for this format. Voice and
    grounding - everything above the STRUCTURE heading - are unchanged."""
    lo, hi = fmt["sections"]
    wlo, whi = fmt["words"]
    b = fmt["blocks"]
    clo, chi = b["code"]
    plo, phi = fmt["paragraphs"]["per_section"]
    pwlo, pwhi = fmt["paragraphs"]["words"]
    lines = [STRUCT_HEAD,
             f"- FORMAT: {fmt['name']}. {fmt['shape']}",
             f"- VOICE FOR THIS FORMAT: {fmt['voice']} This sets how paragraphs are built. The blogger voice "
             "above still applies throughout: speak as \"we\", talk to \"you\", and take positions - at least two "
             "sentences where we agree, disagree or give our view.",
             f"- {lo} to {hi} sections, each with {plo} to {phi} paragraphs of {pwlo} to {pwhi} words. "
             f"Total length {wlo:,} to {whi:,} words. Vary how paragraphs open: do not start more than a "
             "third of them with the same word.",
             f"- HEADINGS: {fmt['heading_rules']} Write your own headings for this subject; do not reuse "
             "any heading listed under HEADINGS ALREADY USED in the brief.",
             f"- {SPECIALS[fmt['special']]['ask']}",
             f"- OPENING: the first section's first paragraph opens on {fmt['opening']}.",
             f"- CLOSING: the last section is {fmt['closing']}. Do not end on choosing, selecting, routing or "
             "adopting a model; those decisions belong in the matrix, the tree and the decisions list.",
             f"- The tldr is one line of at most {fmt['prose']['lead_words_max']} words. Sentences have a median "
             f"of at most {fmt['prose']['sentence_median_max']} words, and none runs over "
             f"{fmt['prose']['sentence_max']}.",
             "- RHYTHM: in at least " + f"{int(fmt['prose']['short_sentence_paragraph_share_min'] * 100)}% of "
             f"paragraphs of three or more sentences, include one of {fmt['prose']['short_sentence_words']} words "
             "or fewer.",
             "- NEVER USE these phrases: " + "; ".join(f'"{p}"' for p in fmt['prose']['avoid_phrases']) + ". "
             "Use each of these words at most as often as shown: "
             + ", ".join(f"{w} {n}" for w, n in fmt['prose']['word_caps'].items()) + ".",
             "- At most one pull quote per section, verbatim as above.",
             f"- VISUALS: the `visuals` list holds {fmt['blocks']['visuals'][0]} to {fmt['blocks']['visuals'][1]} for the "
             "WHOLE post - not one per section. Each names its `section`; at most one per section, chosen by what "
             "that section needs - never for decoration. A `table` compares options, "
             "settings or results side by side. A `chart` plots figures that share one unit and one scale. A "
             "`diagram` shows a sequence, a flow or an architecture as 3 to 8 short steps. Use whichever kinds "
             "the topic calls for; you need not use all three. Every number in a table or chart must appear in "
             "the discussions, the FACT SHEET or a WHAT WE TRIED note; a chart never plots counts of people, "
             "scores or ratings.",
             "- A `faq` of exactly 3 questions, as SEARCH describes - one section at the end, not the shape "
             "of the whole post.",
             f"- ILLUSTRATIONS: {ILLUSTRATIONS_PER_POST[0]} to {ILLUSTRATIONS_PER_POST[1]} AI-generated pictures. "
             "For each, pick the section whose situation is easiest to picture and describe the scene: a "
             "concrete moment or a clear visual metaphor (a queue of requests stalling at one gate, a "
             "developer comparing two diverging paths). The picture carries NO text, numbers, logos, brand or "
             "product names, real people, screenshots, dashboards or charts - data belongs in the visuals, "
             "never in a generated picture."]
    lines.append(f"- {clo} to {chi} code or configuration examples, attached to the section they belong to."
                 if chi else "- No code examples.")
    if b["matrix"]:
        lines.append("- One scenario matrix (5 to 8 rows), as the brief describes.")
    if b["tree"]:
        lines.append("- One decision tree (3 to 5 branches), as the brief describes.")
    return SYSTEM.split(STRUCT_HEAD)[0] + "\n".join(lines)


def tool_for(fmt: dict) -> dict:
    """TOOL with the blocks this format does not use removed, so the model is
    never asked for a matrix or tree the format does not carry."""
    t = copy.deepcopy(TOOL)
    params = t["function"]["parameters"]
    for block, field in (("matrix", "scenario_matrix"), ("tree", "decision_tree")):
        if not fmt["blocks"][block]:
            params["properties"].pop(field)
            params["required"].remove(field)
    if not fmt["blocks"]["code"][1]:
        params["properties"]["sections"]["items"]["properties"].pop("code")
    sp = SPECIALS[fmt["special"]]
    params["properties"][fmt["special"]] = {
        "type": "array", "description": sp["ask"],
        "items": {"type": "object", "required": list(sp["fields"]), "properties": copy.deepcopy(sp["fields"])}}
    params["required"].append(fmt["special"])
    return t


def rules_for(fmt: dict, a: str = "", b: str = "") -> dict:
    question = bool(fmt.get("headings_end_with_question"))
    return {"sections": tuple(fmt["sections"]), "matrix": fmt["blocks"]["matrix"],
            "tree": fmt["blocks"]["tree"], "code": tuple(fmt["blocks"]["code"]), "words": tuple(fmt["words"]),
            "per_section": tuple(fmt["paragraphs"]["per_section"]),
            "para_words": tuple(fmt["paragraphs"]["words"]),
            "heading_question": question, "heading_no_wh": not question,
            "special": fmt["special"], "pick_names": [x for x in (a, b) if x],
            "visuals": tuple(fmt["blocks"]["visuals"]),
            "prose": fmt["prose"],
            # Filled per post by run_plan: every heading other posts already use.
            "taken_headings": set()}


def brief_for(fmt: dict, label: str, a: str, b: str) -> str:
    lines = [f"SUBJECT: {label}.", f"FORMAT: {fmt['name']}. {fmt['shape']}"]
    if fmt["blocks"]["matrix"]:
        title = fmt.get("matrix_title", "Where this fits").format(a=a, b=b)
        lines.append(f"SCENARIO MATRIX: title it '{title}'. Each row is a production scenario, the behavioural "
                     "trade-off there, the mitigation, and the route (which model or configuration to use).")
    if fmt["blocks"]["tree"]:
        q = fmt.get("tree_question", "What should an architect decide here?").format(a=a, b=b)
        lines.append(f"DECISION TREE: the question is '{q}'; each branch is a condition and the resulting choice.")
    return "\n".join(lines)


BLOG_KEYWORDS = ROOT / "blog_keywords.yaml"
BLOG_EXPERIENCES = ROOT / "blog_experiences.yaml"


def load_keywords() -> dict:
    """blog_keywords.yaml. Absent or malformed RAISES: a post written to no
    keyword would pass every check while missing the point of the change."""
    cfg = yaml.safe_load(BLOG_KEYWORDS.read_text(encoding="utf-8"))
    for kind in ("model", "pair", "topic"):
        t = cfg["templates"][kind]
        if not t.get("primary") or not isinstance(t.get("secondary"), list):
            raise ValueError(f"blog_keywords.yaml: templates.{kind} needs a primary and a secondary list")
    return cfg


def load_experiences() -> list[dict]:
    """blog_experiences.yaml entries. A missing file means NO first-person
    experience may be written - it never means "anything goes"."""
    if not BLOG_EXPERIENCES.exists():
        return []
    out = yaml.safe_load(BLOG_EXPERIENCES.read_text(encoding="utf-8")).get("experiences") or []
    for e in out:
        if not (e.get("id") and e.get("said") and e.get("source") and e.get("date")):
            raise ValueError(f"blog_experiences.yaml: {e.get('id')!r} needs id, date, source and said")
    return out


#: A trailing build stamp ("0423", "0731", "20260423") - part of the registry
#: name, never part of what people search for.
_BUILD_STAMP = re.compile(r"\s+(?:\d{4}|\d{8})$")


def search_name(name: str) -> str:
    """'DeepSeek V4 Flash 0423' -> 'DeepSeek V4 Flash'. Measured on the first
    sample (2026-10-13): the dated name made the keyword 'DeepSeek V4 Flash 0423
    review', and the FAQ wrote 'Is DeepSeek V4 Flash 0423 review evidence ...'."""
    return _BUILD_STAMP.sub("", (name or "").strip())


def keyword_plan(names: dict, cfg: dict) -> dict:
    """{'primary', 'secondary', 'subject'} for one subject, from the templates.
    `subject` is what an FAQ question must name - the model(s) or the topic -
    so the questions read as people ask them, not as the keyword phrase."""
    t = cfg["templates"][names["kind"]]
    a, b = search_name(names.get("a") or names.get("label", "")), search_name(names.get("b", ""))
    fill = {"a": a, "b": b, "label": (names.get("label") or "").lower()}
    sec = [x.format(**fill) for x in t["secondary"]]
    subject = [x for x in (a, b) if x] if names["kind"] != "topic" else [fill["label"]]
    return {"primary": t["primary"].format(**fill), "secondary": [x for x in sec if x.strip()],
            "subject": subject}


def experiences_for(post: dict, entries: list[dict]) -> list[dict]:
    """The WHAT WE TRIED notes that belong to this post: a model it is about,
    or a topic its subject names. Dated builds match their undated family."""
    ids = {str(x).lower() for x in (post.get("subject") or [])}
    fam = {re.sub(r"-\d{4}$", "", x) for x in ids}
    label = ((post.get("plan") or {}).get("subject") or "").lower()
    picked = []
    for e in entries:
        models = {str(m).lower() for m in e.get("models") or []}
        if models & ids or {re.sub(r"-\d{4}$", "", m) for m in models} & fam or \
                any(str(t).lower() in label for t in e.get("topics") or []):
            picked.append(e)
    return picked


def trending_terms(cur, window_days: int | None = None, top: int | None = None) -> list[str]:
    """The sections engineers reported on most in the last `window_days`, by
    distinct documents - what is being talked about now, read from the board's
    own entries. NOT search volume: there is no trend feed. Declined entries
    excluded, as on the board."""
    cfg = load_keywords().get("trending") or {}
    days = window_days or int(cfg.get("window_days", 14))
    n = top or int(cfg.get("top", 6))
    cur.execute(
        "SELECT name, count(DISTINCT document_id) AS docs FROM board_entry "
        "WHERE created_at > now() - make_interval(days => %s) AND ruling IS DISTINCT FROM 'declined' "
        "AND name IS NOT NULL GROUP BY name ORDER BY docs DESC, name LIMIT %s", (days, n))
    return [r["name"] if isinstance(r, dict) else r[0] for r in cur.fetchall()]


def add_search_and_experience(post: dict, trending: list[str] | None = None) -> None:
    """Keywords, our own notes and trending terms into one planned post's brief,
    and the matching check inputs onto the post (`seo`, `experience_text`)."""
    if post.get("names"):
        post["seo"] = keyword_plan(post["names"], load_keywords())
        post["brief"] += (f"\nPRIMARY KEYWORD: {post['seo']['primary']}"
                          f"\nSECONDARY KEYWORDS: {'; '.join(post['seo']['secondary'])}")
    notes = experiences_for(post, load_experiences())
    post["experience_text"] = "\n".join(e["said"] for e in notes)
    if notes:
        post["brief"] += "\nWHAT WE TRIED (our own tests - the only first-person experience you may write):" + "".join(
            f"\n- ({e['date']}) {' '.join(str(e['said']).split())}" for e in notes)
    if trending:
        post["brief"] += "\nTRENDING IN RECENT REPORTS: " + "; ".join(trending)
    if post.get("agreement"):
        post["brief"] += ("\nWHERE ENGINEERS AGREE AND SPLIT (our board entries for the discussions below, "
                          "counted by discussion - for planning only, never quote these counts):\n"
                          + post["agreement"])


def existing_headings() -> set[str]:
    """Every section heading the drafts already on disk use, normalised."""
    out: set[str] = set()
    for f in POSTS_OUT.glob("*.json"):
        try:
            body = json.loads(f.read_text(encoding="utf-8")).get("body") or []
        except (OSError, json.JSONDecodeError):
            continue
        for t, v in body:
            if t == "h2" and isinstance(v, dict) and v.get("num") not in ("Matrix", "Decision tree"):
                out.add(norm_heading(v.get("text", "")))
            elif t == "h2" and isinstance(v, str):
                out.add(norm_heading(v))
    out.discard("")
    return out


def stored_plan_keys(cur) -> set[str]:
    """(format, subject) keys of posts in the shared `blog_post` table - REJECTED
    ONES INCLUDED. A rejected post is kept, content and all, and its key is what
    stops the planner writing it again and paying for it twice (migration
    20261006T1500). A database without the table has no rejections to remember,
    so that one case reads as none; any other error stops the run."""
    try:
        with cur.connection.transaction():  # a savepoint: the plan's transaction survives
            cur.execute("SELECT plan_key FROM blog_post WHERE plan_key IS NOT NULL")
            return {r["plan_key"] for r in cur.fetchall()}
    except psycopg.errors.UndefinedTable:
        return set()


def existing_plan_keys(cur=None) -> set[str]:
    keys = stored_plan_keys(cur) if cur is not None else set()
    for f in POSTS_OUT.glob("*.json"):
        try:
            k = (json.loads(f.read_text(encoding="utf-8")).get("provenance") or {}).get("plan_key")
        except (OSError, json.JSONDecodeError):
            continue
        if k:
            keys.add(k)
    return keys | set(LEGACY_PLAN_KEYS.values())


def candidates(cur, kind: str, cfg: dict) -> list[dict]:
    """Subjects with enough evidence, most-evidenced first (an internal order)."""
    lim = cfg["candidates_per_kind"]
    # Counted over the threads a draft MAY use (`_public_thread_sql`), so a
    # subject qualifies on evidence the selector will not then refuse.
    ok = f"{VERIFIED} AND {_public_thread_sql('c.thread_context_id')}"
    if kind == "model":
        cur.execute(f"""SELECT mv.canonical_id AS id, max(mv.display_name) AS name
            FROM board_entry be JOIN claim c ON c.id = be.claim_id JOIN model_version mv ON mv.id = be.model_version_id
            WHERE {ok} GROUP BY mv.canonical_id
            HAVING count(DISTINCT c.thread_context_id) >= %s
            ORDER BY count(DISTINCT c.thread_context_id) DESC, mv.canonical_id LIMIT %s""",
                    (cfg["min_threads_model"], lim))
        return [{"ids": [r["id"]], "label": clean(r["name"]), "a": clean(r["name"]), "b": ""} for r in cur.fetchall()]
    if kind == "pair":
        cur.execute(f"""WITH t AS (SELECT DISTINCT c.thread_context_id AS tc, mv.canonical_id AS m, mv.display_name AS n
                FROM board_entry be JOIN claim c ON c.id = be.claim_id JOIN model_version mv ON mv.id = be.model_version_id
                WHERE {ok})
            SELECT a.m AS m1, max(a.n) AS n1, b.m AS m2, max(b.n) AS n2 FROM t a JOIN t b ON a.tc = b.tc AND a.m < b.m
            GROUP BY a.m, b.m HAVING count(*) >= %s ORDER BY count(*) DESC, a.m, b.m LIMIT %s""",
                    (cfg["min_threads_pair"], lim))
        return [{"ids": [r["m1"], r["m2"]], "label": f"{clean(r['n1'])} and {clean(r['n2'])}",
                 "a": clean(r["n1"]), "b": clean(r["n2"])} for r in cur.fetchall()]
    if kind == "topic":
        cur.execute(f"""SELECT be.section, coalesce(nullif(be.ruling_target,''), be.slug) AS key, max(be.name) AS name
            FROM board_entry be JOIN claim c ON c.id = be.claim_id
            WHERE {ok} AND be.section IN ('capability', 'best_for')
            GROUP BY be.section, coalesce(nullif(be.ruling_target,''), be.slug)
            HAVING count(DISTINCT c.thread_context_id) >= %s AND count(DISTINCT be.model_version_id) >= %s
            ORDER BY count(DISTINCT c.thread_context_id) DESC, 2 LIMIT %s""",
                    (cfg["min_threads_topic"], cfg["min_models_topic"], lim))
        return [{"section": r["section"], "topic": r["key"], "label": r["name"], "a": r["name"], "b": ""}
                for r in cur.fetchall()]
    raise BuildError(f"blog_formats.yaml: unknown subject kind {kind!r}")


def planned_post(fmt: dict, cand: dict) -> dict:
    if fmt["subject"] == "topic":
        subject_key = f"{cand['section']}/{cand['topic']}"
        where = ("be.section = %(section)s AND "
                 "coalesce(nullif(be.ruling_target,''), be.slug) = %(topic)s")
        extra = {"subject": None, "params": {"section": cand["section"], "topic": cand["topic"]}, "facts": []}
        tags = [cand["label"], fmt["name"]]
    else:
        subject_key = "+".join(sorted(cand["ids"]))
        where = "mv.canonical_id = ANY(%(subject)s)"
        extra = {"subject": cand["ids"], "params": {}, "facts": list(cand["ids"])}
        tags = [x for x in (cand["a"], cand["b"]) if x] + [fmt["name"]]
    plan_key = f"{fmt['key']}:{subject_key}"
    slug = re.sub(r"[^a-z0-9]+", "-", plan_key.lower()).strip("-")[:90]
    return {"key": slug, "file": f"{slug}.html", "kicker": fmt["name"], "where": where, "tags": tags,
            "brief": brief_for(fmt, cand["label"], cand["a"], cand["b"]), "system": system_for(fmt),
            "tool": tool_for(fmt), "rules": rules_for(fmt, cand["a"], cand["b"]),
            "prices": fmt["blocks"]["prices"], "format_cfg": fmt,
            "plan": {"plan_key": plan_key, "format": fmt["key"], "subject": cand["label"]},
            "names": {"kind": "topic" if "section" in cand else ("pair" if cand.get("b") else "model"),
                      "a": cand.get("a") or "", "b": cand.get("b") or "", "label": cand["label"]},
            **extra}


def plan_posts(cur, reader, n: int) -> list[tuple]:
    """Pick the next `n` posts: distinct formats, least-written formats first,
    never a (format, subject) already written, never one subject twice in a
    batch. Each pick must have its documents on this machine."""
    cfg = load_formats()
    done = existing_plan_keys(cur)
    order = sorted(cfg["formats"], key=lambda f: (sum(k.startswith(f["key"] + ":") for k in done),
                                                 cfg["formats"].index(f)))
    pools: dict[str, list] = {}
    picked, subjects = [], set()
    for fmt in order:
        if len(picked) == n:
            break
        pool = pools.setdefault(fmt["subject"], candidates(cur, fmt["subject"], cfg["planner"]))
        # SUBJECTS NO POST COVERS YET COME FIRST. Measured 2026-10-01: without
        # this the first plan was Opus 5 and Opus/Sonnet again, in new formats -
        # allowed, but a blog of one model in seven shapes. A stable sort keeps
        # the evidence order within each group.
        covered = {k.split(":", 1)[1] for k in done}
        pool = sorted(pool, key=lambda c: planned_post(fmt, c)["plan"]["plan_key"].split(":", 1)[1] in covered)
        for cand in pool:
            post = planned_post(fmt, cand)
            subj = post["plan"]["plan_key"].split(":", 1)[1]
            if post["plan"]["plan_key"] in done or subj in subjects:
                continue
            try:
                docs, skipped = select_documents(cur, post, reader)
                post["agreement"] = agreement_map(cur, post, docs)
            except BuildError:
                continue  # not enough of its evidence on this machine - next candidate
            picked.append((post, docs, skipped, fact_sheet(cur, post, docs)))
            subjects.add(subj)
            break
    return picked


# ── UI status (read by judge/blog_posts.py for the Blogs page button) ─────────

UI_STATUS = RUNS / "_ui_status.json"
_ui = {"on": False}


def ui_status(**kw) -> None:
    """Merge `kw` into the status file the Blogs page polls. A no-op unless
    --status was passed, so a run from the terminal leaves no file behind."""
    if not _ui["on"]:
        return
    try:
        cur = json.loads(UI_STATUS.read_text(encoding="utf-8")) if UI_STATUS.exists() else {}
    except (OSError, json.JSONDecodeError):
        cur = {}
    item, item_state = kw.pop("item", None), kw.pop("item_state", None)
    attempt = kw.pop("attempt", None)
    cur.update(kw)
    if item:
        for it in cur.get("items", []):
            if it["key"] == item:
                it["state"] = item_state or it.get("state")
                if attempt:
                    it["attempt"] = attempt
    cur["updated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    RUNS.mkdir(exist_ok=True)
    UI_STATUS.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")


def run_plan(args, dsn, key, base, reader) -> None:
    with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=20) as conn:
        conn.read_only = True
        inputs = plan_posts(conn.cursor(), reader, args.plan)
        trending = trending_terms(conn.cursor())
    ui_status(state="running", model=GEN_MODEL, items=[
        {"key": p["key"], "format": p["kicker"], "subject": p["plan"]["subject"], "state": "queued"}
        for p, *_ in inputs])
    print(f"planned {len(inputs)} of {args.plan}:", flush=True)
    for p, docs, skipped, _facts in inputs:
        print(f"  - {p['plan']['plan_key']}  ({len(docs)} documents; skipped {len(skipped)})", flush=True)
    if args.dry_run:
        ui_status(state="done", message="dry run - nothing generated")
        return
    if not inputs:
        ui_status(state="failed", message="no subject with enough evidence on this machine is left unwritten")
        raise BuildError("the planner found nothing left to write")
    existing = []
    for f in sorted(POSTS_OUT.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            existing.append((d["slug"], d["title"]))
        except (OSError, json.JSONDecodeError, KeyError):
            continue
    # COST IS INCOMPLETE, NOT $0, when any call did not report one - and a
    # failed post's calls were paid for too, so they are counted (review of
    # #508, item 5).
    written, failed, total_cost, cost_incomplete = [], {}, 0.0, False
    taken = existing_headings()
    for post, docs, _skipped, facts in inputs:
        ui_status(item=post["key"], item_state="writing")
        # THE BATCH AVOIDS ITSELF: each post is checked against every heading
        # already on disk plus the ones written earlier in this run, and the
        # brief lists them so the model can avoid them on the first draw.
        post["rules"]["taken_headings"] = set(taken)
        add_search_and_experience(post, trending)
        if taken:
            post["brief"] += ("\nHEADINGS ALREADY USED (do not reuse any): "
                              + "; ".join(sorted(taken)))
        try:
            rec = synthesise(post, docs, facts, key, base)
        except BuildError as e:
            failed[post["key"]] = str(e)
            if post.get("_record"):
                f_cost, _tin, _tout = spend(post["_record"])
                if f_cost is None:
                    cost_incomplete = True
                else:
                    total_cost += f_cost
            ui_status(item=post["key"], item_state="failed", cost_usd=round(total_cost, 4),
                      cost_incomplete=cost_incomplete)
            print(f"  [{post['key']}] FAILED: {e}", flush=True)
            continue
        cost, tin, tout = spend(rec)
        if cost is None:
            cost_incomplete = True
        else:
            total_cost += cost
        essay = rec["essay"]
        post["_illustrations"] = illustrate(post, essay, key, base, rec["started"])
        for il in post["_illustrations"]:
            if il.get("usd") is None:
                cost_incomplete = True
            else:
                total_cost += il["usd"]
        mins = max(1, math.ceil(words_in(essay) / 230))
        rel = existing[-3:]  # the most recent other drafts, for "Continue reading"
        out = export_post(post, essay, docs, facts, rec, mins, rel)
        written.append(post["key"])
        existing.append((post["key"], essay["title"]))
        taken |= {norm_heading(s.get("heading", "")) for s in essay.get("sections", [])}
        ui_status(item=post["key"], item_state="done", cost_usd=round(total_cost, 4),
                  cost_incomplete=cost_incomplete)
        print(f"  [{post['key']}] wrote {out.relative_to(ROOT)} - {len(rec['attempts'])} call(s), "
              f"cost {f'${cost:.4f}' if cost is not None else 'not reported'}, "
              f"tokens {tin:,} in / {tout:,} out", flush=True)
    ui_status(state="done" if not failed else ("failed" if not written else "partial"),
              message=f"{len(written)} written, {len(failed)} failed",
              finished_at=datetime.now(UTC).isoformat(timespec="seconds"))
    if failed:
        # Loud (non-zero exit) WITHOUT raising: the BuildError handler would
        # overwrite the "partial" status above with "failed", and a run that
        # wrote two of three posts is not a failed run.
        print(f"BUILD INCOMPLETE: {len(failed)} planned post(s) failed: {sorted(failed)}", flush=True)
        sys.exit(1)


# ── main ─────────────────────────────────────────────────────────────────────

def spend(record: dict) -> tuple[float | None, int, int]:
    reported, tin, tout, complete = 0.0, 0, 0, True
    for a in record["attempts"]:
        u = a.get("usage") or {}
        tin += u.get("prompt_tokens") or 0
        tout += u.get("completion_tokens") or 0
        if u.get("cost") is None:
            complete = False
        else:
            reported += float(u["cost"])
    return (reported if complete else None), tin, tout


def main() -> None:
    global GEN_MODEL
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reuse", action="store_true", help="re-render the latest passing draws; no model call")
    ap.add_argument("--only", choices=[p["key"] for p in POSTS])
    ap.add_argument("--model", choices=sorted(GEN_MODELS), default=GEN_MODEL,
                    help="generation model (default: %(default)s)")
    ap.add_argument("--no-write", action="store_true",
                    help="run and save the draw records, but write no HTML (for comparisons)")
    ap.add_argument("--recheck", action="store_true",
                    help="re-run the checks on saved drafts (no model call); save any that now pass")
    ap.add_argument("--plan", type=int, metavar="N",
                    help="plan and write N NEW posts from blog_formats.yaml (UI drafts only, no HTML)")
    ap.add_argument("--dry-run", action="store_true", help="with --plan: show the plan, call nothing")
    ap.add_argument("--status", action="store_true",
                    help="with --plan: keep _blog_synthesis/_ui_status.json current (the Blogs page polls it)")
    args = ap.parse_args()
    _ui["on"] = bool(args.status)
    GEN_MODEL = args.model
    print(f"generation model: {GEN_MODEL}", flush=True)
    os.chdir(ROOT)
    E = env()
    dsn = E.get("STAGING_DATABASE_URL") or E.get("DATABASE_URL")
    if not dsn:
        raise BuildError("no STAGING_DATABASE_URL / DATABASE_URL in .env")
    key = E.get("OPENROUTER_API_KEY")
    if not args.reuse and not key:
        raise BuildError("OPENROUTER_API_KEY is unset; refusing to start")
    base = E.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
    reader = RawStoreReader(RawStore(E.get("RAW_STORE_PATH") or "./raw_store"))
    OUT.mkdir(exist_ok=True)

    if args.plan is not None:
        if not 1 <= args.plan <= 5:
            raise BuildError("--plan takes 1 to 5")
        run_plan(args, dsn, key, base, reader)
        return

    # ALL READS FIRST, THEN THE CONNECTION CLOSES. A model call can take many
    # minutes and the staging server drops an idle connection in that time -
    # the second run lost its connection mid-call (read-only, nothing at risk,
    # but a build should not depend on a socket surviving a generation).
    wanted = [p for p in POSTS if not args.only or p["key"] == args.only]
    inputs = []
    with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=20) as conn:
        conn.read_only = True
        cur = conn.cursor()
        for post in wanted:
            docs, skipped = select_documents(cur, post, reader)
            inputs.append((post, docs, skipped, fact_sheet(cur, post, docs)))

    if args.recheck:
        # NO MODEL CALL. Exists because three checker rules were too broad on
        # 2026-10-01 and failed correct drafts; once a rule is corrected, the
        # saved draft is the same text and the check is deterministic code, so
        # paying for a new draw would only buy a different essay to re-read.
        # The original record is never edited - a NEW record says what was
        # rechecked, from which file, under which rules.
        for post, docs, _skipped, facts in inputs:
            context = "\n".join(d["text"] for d in docs) + "\n" + fact_lines(facts)
            ids = [d["thread_context_id"] for d in docs]
            found = None
            for p in sorted((RUNS / post["key"]).glob("*.json"), reverse=True):
                rec = json.loads(p.read_text(encoding="utf-8"))
                if rec.get("requested_model") != GEN_MODEL or rec.get("rechecked_from"):
                    continue
                if [d["thread_context_id"] for d in rec["documents"]] != ids:
                    continue
                for i, a in reversed(list(enumerate(rec["attempts"]))):
                    if a.get("essay") and not check(a["essay"], context):
                        found = (p, i, a["essay"], rec)
                        break
                if found or rec.get("passed"):
                    break
            if not found:
                print(f"[{post['key']}] recheck: no saved {GEN_MODEL} draft passes the current checks")
                continue
            p, i, essay, rec = found
            new = {**{k: rec[k] for k in ("post", "requested_model", "documents", "facts")},
                   "started": datetime.now(UTC).isoformat(timespec="seconds"),
                   "rechecked_from": p.name, "rechecked_attempt": i + 1,
                   "attempts": [], "passed": True, "essay": essay}
            save(new)
            print(f"[{post['key']}] recheck: attempt {i + 1} of {p.name} passes the current checks; saved")
        return

    built, failed = {}, {}
    for post, docs, skipped, facts in inputs:
        print(f"[{post['key']}] {len(docs)} documents "
              f"({sum(d['chars'] for d in docs):,} chars, {sum(d['truncated'] for d in docs)} truncated); "
              f"skipped as not on this machine: {[s['thread_context_id'] for s in skipped]}", flush=True)
        if args.reuse:
            rec = latest_passing(post["key"])
            if [d["thread_context_id"] for d in docs] != [d["thread_context_id"] for d in rec["documents"]]:
                raise BuildError(f"--reuse: {post['key']}'s document selection changed since the saved draw")
        else:
            try:
                rec = synthesise(post, docs, facts, key, base)
            except BuildError as e:
                # One post failing must not cost the others their draw. The
                # failure is still loud: listed below and a non-zero exit.
                failed[post["key"]] = str(e)
                print(f"  [{post['key']}] FAILED: {e}", flush=True)
                continue
            cost, tin, tout = spend(rec)
            print(f"  [{post['key']}] {len(rec['attempts'])} call(s), {tin:,} in / {tout:,} out tokens, "
                  f"OpenRouter-reported cost {f'${cost:.4f}' if cost is not None else 'not reported'}")
        built[post["key"]] = (post, rec["essay"], docs, facts, rec)

    if args.no_write:
        print(f"--no-write: {sorted(built)} passed, {sorted(failed)} failed; no HTML written")
        return
    titles = {k: v[1]["title"] for k, v in built.items()}
    hub_entries = []
    for k, (post, essay, docs, facts, rec) in built.items():
        article, toc, words, mins = render(post, essay, docs, facts)
        related = [(titles[o], built[o][0]["file"]) for o in built if o != k]
        (OUT / post["file"]).write_text(page(post, essay, article, toc, words, mins, related), encoding="utf-8")
        hub_entries.append((post, essay, mins))
        print(f"wrote {post['file']}: {words:,} words, ~{mins} min")
        rel_posts = [(post_slug(built[o][0]), titles[o]) for o in built if o != k]
        out = export_post(post, essay, docs, facts, rec, mins, rel_posts)
        print(f"wrote {out.relative_to(ROOT)} (UI draft)")
    if failed:
        raise BuildError(f"{len(failed)} post(s) failed and were not written: {sorted(failed)}; "
                         f"index.html left as it was")
    if not args.only:
        (OUT / "index.html").write_text(hub(hub_entries), encoding="utf-8")
        print("wrote index.html")


if __name__ == "__main__":
    try:
        main()
    except BuildError as e:
        ui_status(state="failed", message=str(e)[:400],
                  finished_at=datetime.now(UTC).isoformat(timespec="seconds"))
        sys.exit(f"BUILD FAILED: {e}")
    except Exception as e:  # noqa: BLE001 - the page must not show "running" forever
        ui_status(state="failed", message=f"{type(e).__name__}: {str(e)[:380]}",
                  finished_at=datetime.now(UTC).isoformat(timespec="seconds"))
        raise
