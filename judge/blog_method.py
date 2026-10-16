"""How a blog post is made, for Admin -> Blogs (2026-10-16).

Three things the Blogs panel shows beside the drafts, so the reviewer sees the
method next to its output:

    method()    who writes (blog_formats.yaml `writer`), the stages a post goes
                through, and the rules code checks every draft against
    packs()     the writing packs waiting for Claude Code, and how far each got
    start_pack  prepare N packs (generate_sample_blogs.py --pack N): the same
                planner and selection as before, no model call

The prompt itself is read where the Prompts panel reads it
(judge/app.py `_blog_prompt_parts`), so the two panels can never show two
different prompts.

WHY THE WRITER CHANGED. The team's review found no journalistic improvement in
the OpenRouter drafts, so until the prompt is tuned the blog makes no
OpenRouter call: Claude Code (Opus 5.5) writes from a pack, and code checks
the result exactly as it checked a model draft.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
FORMATS = ROOT / "blog_formats.yaml"
PACKS = ROOT / "blog_packs"
PACK_LOG = PACKS / "_pack_run.log"

WRITERS = {
    "claude-code": "Claude Code (Opus 5.5) writes from a writing pack; no OpenRouter call",
    "openrouter": "A model on OpenRouter writes and repairs the draft",
}

#: THE PIPELINE, in the order a post moves through it. Words, not counts
#: (rule 11): each line names the code that does the step.
STAGES = [
    {"step": "Choose what to write",
     "who": "code",
     "what": "The planner picks a format (field report, head-to-head, cost teardown, migration "
             "guide, architecture pattern, release analysis, evaluation critique) and a subject "
             "with enough board evidence that has not been written yet - least-used formats first, "
             "never the same subject twice in a batch.",
     "where": "generate_sample_blogs.py plan_posts, blog_formats.yaml planner"},
    {"step": "Select the documents",
     "who": "code",
     "what": "The threads behind the subject's board entries, ranked by how many models, entries "
             "and themes they carry, with room kept for threads reporting problems; capped per "
             "source and for embed-only sources. A thread whose text is not on this machine is "
             "skipped and counted.",
     "where": "select_documents, rank_threads"},
    {"step": "Build the brief",
     "who": "code",
     "what": "The format's structure, voice and length; the fact sheet of published prices; the "
             "agreement map of who said what; the search phrases; titles and headings already "
             "used, so a new post does not echo them.",
     "where": "planned_post, brief_for, fact_sheet, agreement_map, add_search_and_experience"},
    {"step": "Write the post",
     "who": "writer",
     "what": "From the writing pack: the system prompt, the brief, the full source texts and the "
             "output schema.",
     "where": "blog_packs/<key>/prompt.md -> essay.json"},
    {"step": "Check it",
     "who": "code",
     "what": "Every rule below, by the same function a model draft faced. Any blocking violation "
             "refuses the post; style findings are recorded beside it.",
     "where": "generate_sample_blogs.py check (via --ingest)"},
    {"step": "Store it as a draft",
     "who": "code",
     "what": "The post is rendered in the page's shape, every quote numbered to its source, and "
             "stored as pending in the shared post table.",
     "where": "export_post, judge/blog_store.store_drafts"},
    {"step": "Approve or reject",
     "who": "person",
     "what": "A team member reads the draft here and approves or rejects it, with a reason. Only "
             "approved posts reach the Blogs page; every decision is kept.",
     "where": "Admin -> Blogs, judge/blog_store.decide"},
]

#: THE RULES CODE CHECKS, grouped as a reviewer reads them. Each names the
#: function that enforces it, so the list can be checked against the code.
RULES = [
    {"group": "Quotes and sources",
     "items": [
         "Every «verbatim fragment» appears word for word in one of the selected discussions.",
         "No quotation marks around words that are not a verbatim fragment.",
         "A sentence crediting practitioners carries a «verbatim» fragment from them.",
         "Our own notes are never quoted as if an engineer said them.",
         "Reddit and X appear only as the platform's official embed, never quoted in our prose; no "
         "other source is embedded.",
         "Enough distinct voices are quoted, and the post retraces at least one engineer's work.",
     ],
     "where": "check, embed_violations, voices_violations, retrace_violations"},
    {"group": "Numbers",
     "items": [
         "Every number appears in a discussion or the fact sheet - none is computed or invented.",
         "Tables and charts plot only figures from the sources; never counts of people, scores or "
         "ratings.",
     ],
     "where": "check, visual_violations"},
    {"group": "Shape",
     "items": [
         "The format's section count, paragraphs per section and paragraph length.",
         "The format's reading length, counted the way the page counts it.",
         "The format's structured block (findings, picks, cost drivers, runbook, layers, claims "
         "or probes), code examples within its bounds, a 3-question FAQ.",
         "Illustration scenes with no text, numbers, logos, product names or real people.",
     ],
     "where": "check, illustration_violations"},
    {"group": "Writing",
     "items": [
         "Sentence length and rhythm limits; banned stock phrases; capped words.",
         "Openings vary; headings and titles do not reuse ones already used.",
         "The title and search fields follow the SEO rules for the subject.",
     ],
     "where": "check, title_violations, seo_violations, _pace, _lively"},
]


def writer() -> str:
    raw = yaml.safe_load(FORMATS.read_text(encoding="utf-8")) or {}
    w = raw.get("writer")
    if w not in WRITERS:
        raise ValueError(f"blog_formats.yaml `writer` must be one of {sorted(WRITERS)}, not {w!r}")
    return w


def method() -> dict[str, Any]:
    w = writer()
    return {"writer": w, "writer_label": WRITERS[w], "stages": STAGES, "rules": RULES}


def packs() -> list[dict[str, Any]]:
    """Every writing pack, newest first, and how far it got."""
    out = []
    for d in sorted((p for p in PACKS.glob("*") if p.is_dir()),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            pack = json.loads((d / "pack.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        post = pack.get("post") or {}
        checks = d / "checks.txt"
        first = checks.read_text(encoding="utf-8").splitlines()[0] if checks.exists() else None
        out.append({
            "key": d.name,
            "subject": (post.get("plan") or {}).get("subject"),
            "format": post.get("kicker"),
            "documents": len(pack.get("docs") or []),
            "created": pack.get("created"),
            "essay_written": (d / "essay.json").exists(),
            "checks": first,
        })
    return out


_proc: subprocess.Popen | None = None


def start_pack(count: int) -> dict[str, Any]:
    """Prepare `count` writing packs in the background. No model call."""
    global _proc
    if not 1 <= count <= 5:
        raise ValueError("count must be 1 to 5")
    if _proc is not None and _proc.poll() is None:
        raise RuntimeError("packs are already being prepared")
    PACKS.mkdir(exist_ok=True)
    log = PACK_LOG.open("w", encoding="utf-8")
    _proc = subprocess.Popen(
        [sys.executable, "-u", str(ROOT / "generate_sample_blogs.py"), "--pack", str(count)],
        cwd=str(ROOT), env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT,
    )
    return {"started": datetime.now(UTC).isoformat(timespec="seconds"), "count": count}


def pack_status() -> dict[str, Any]:
    running = _proc is not None and _proc.poll() is None
    tail = []
    if PACK_LOG.exists():
        tail = [ln for ln in PACK_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
                if not ln.startswith("raw store:")][-6:]
    return {"running": running,
            "exit_code": None if _proc is None or running else _proc.returncode,
            "log_tail": tail}
