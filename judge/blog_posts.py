"""Blog draft FILES on this machine, and the generation run that writes them.

THE PAGES DO NOT READ THESE FILES (since 2026-10-06). Posts live in the shared
`blog_post` table (`judge/blog_store.py`, migration 20261006T1500): the Blogs
page shows the approved ones and Admin -> Blogs reviews the rest. The files are
the generator's output on the machine that ran it - `generate_sample_blogs.py`
calls a paid model and runs locally - and they reach the table two ways: a run
started from Admin -> Blogs stores its drafts when it finishes
(`judge/blog_runs._finish`), and anything else is stored from Admin -> Blogs'
"Store them as drafts" (`POST /blog-posts/store`). This module validates and
lists the files for both. Nothing here calls a model.

THREE STATES, NOT TWO (rule 4, rule 6)

  posts: [...]                   drafts exist and were read
  posts: [], reason: None        the directory exists and holds no drafts
  posts: [], reason: "..."       the directory is not configured or not there

"No posts yet" and "this machine is not set up to show posts" must not render
the same, so the second and third differ in `reason`. A file that cannot be
read is listed in `skipped` by name and cause rather than dropped.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

#: The keys `web/src/board/views.js` `vPost` reads. A file missing one is
#: skipped and named, never half-rendered.
REQUIRED = ("slug", "title", "dek", "tag", "by", "lead", "meta", "body", "provenance")

#: Body block types `vPost` knows how to render. An unknown type would render
#: as nothing, which reads as a shorter post rather than a broken one.
BLOCK_TYPES = {"h2", "h3", "p", "ul", "quote", "code", "table", "tree"}


def posts_dir() -> Path | None:
    """BLOG_POSTS_DIR, resolved against the repo root. None when unset.

    No default: a default path would serve whatever happens to be there on a
    machine nobody configured (rule 12).
    """
    raw = os.getenv("BLOG_POSTS_DIR", "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_absolute() else ROOT / p


def _problem(doc: Any) -> str | None:
    if not isinstance(doc, dict):
        return "not a JSON object"
    missing = [k for k in REQUIRED if k not in doc]
    if missing:
        return f"missing {', '.join(missing)}"
    if not isinstance(doc["body"], list):
        return "body is not a list"
    for i, block in enumerate(doc["body"]):
        if not (isinstance(block, list) and len(block) == 2 and block[0] in BLOCK_TYPES):
            return f"body[{i}] is not one of {sorted(BLOCK_TYPES)}"
    return None


def load() -> dict[str, Any]:
    d = posts_dir()
    if d is None:
        return {"posts": [], "skipped": [], "reason": (
            "BLOG_POSTS_DIR is not set, so this backend is not configured to serve blog drafts. "
            "Set it in .env to the directory generate_sample_blogs.py writes (blog_posts/).")}
    if not d.is_dir():
        return {"posts": [], "skipped": [], "reason": (
            f"BLOG_POSTS_DIR points at {d.name!r}, which does not exist on this machine. "
            "Run generate_sample_blogs.py to create drafts, or correct the setting.")}
    posts, skipped = [], []
    for f in sorted(d.glob("*.json")):
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            skipped.append({"file": f.name, "why": f"unreadable: {e}"})
            continue
        why = _problem(doc)
        if why:
            skipped.append({"file": f.name, "why": why})
            continue
        posts.append(doc)
    # The featured post first, then by title: a stable order a reader can predict.
    posts.sort(key=lambda p: (not p.get("feat"), p["title"]))
    return {"posts": posts, "skipped": skipped, "reason": None}


# ── generating more drafts from the Blogs page ────────────────────────────────
#
# THE BUTTON STARTS A BACKGROUND RUN AND NOTHING ELSE. The run is
# `generate_sample_blogs.py --plan N --status`, a subprocess - this module never
# imports it (it imports collect/, and judge/ may not). The page polls the
# status file the run keeps current.
#
# LOCAL ONLY. It calls a paid model and writes files, so it refuses unless
# ENVIRONMENT=development. One run at a time: a second press while one is
# running is a 409, not a second bill.

STATUS_FILE = ROOT / "_blog_synthesis" / "_ui_status.json"
LOG_FILE = ROOT / "_blog_synthesis" / "_ui_run.log"
#: A run whose status file has not moved for this long is reported as stalled
#: rather than running. A planned post takes a few minutes; this is far longer.
STALE_AFTER_S = 30 * 60

_proc: subprocess.Popen | None = None


class GenerationRefused(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


def _read_status() -> dict | None:
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def generation_status() -> dict:
    """What the last (or current) run says about itself, plus whether this
    backend can see it still running. Never guesses: a status file that says
    running with no live process and no recent update is `stalled`."""
    st = _read_status() or {"state": "idle"}
    alive = _proc is not None and _proc.poll() is None
    if st.get("state") in ("starting", "running") and not alive:
        try:
            age = (datetime.now(UTC) - datetime.fromisoformat(st["updated_at"])).total_seconds()
        except (KeyError, ValueError, TypeError):
            age = None
        if _proc is not None and _proc.poll() is not None:
            st = {**st, "state": "failed", "message": st.get("message") or
                  f"the run exited (code {_proc.returncode}) without reporting; "
                  f"see {LOG_FILE.name}"}
        elif age is None or age > STALE_AFTER_S:
            st = {**st, "state": "stalled",
                  "message": "the run stopped reporting; it is not running from this backend"}
    return {**st, "alive": alive}


def start_generation(count: int) -> dict:
    global _proc
    if os.getenv("ENVIRONMENT", "").strip().lower() != "development":
        raise GenerationRefused(
            403, "generating posts is a local-development action; ENVIRONMENT is not development")
    if not 1 <= count <= 5:
        raise GenerationRefused(422, "count must be 1 to 5")
    if _proc is not None and _proc.poll() is None:
        raise GenerationRefused(409, "a generation run is already in progress")
    script = ROOT / "generate_sample_blogs.py"
    STATUS_FILE.parent.mkdir(exist_ok=True)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    STATUS_FILE.write_text(json.dumps({"state": "starting", "count": count, "started_at": now,
                                       "updated_at": now, "items": []}), encoding="utf-8")
    log = LOG_FILE.open("w", encoding="utf-8")
    _proc = subprocess.Popen([sys.executable, "-u", str(script), "--plan", str(count), "--status"],
                             cwd=str(ROOT), env=os.environ.copy(), stdout=log,
                             stderr=subprocess.STDOUT)
    return generation_status()
