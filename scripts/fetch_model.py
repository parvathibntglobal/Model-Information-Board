#!/usr/bin/env python
"""Per-model fresh fetch — the evidence pipeline for ONE model, on demand.

Composition root: harvest is `collect/`'s, extraction is `judge/`'s, and only a
script outside both lanes may import both. The backend invokes this as a
SUBPROCESS (never an import) when the user clicks Fetch, so neither lane imports
the other. Nothing runs on its own — a fetch happens only on a click.

APPEND-ONLY, AND THAT IS LOAD-BEARING. This runs against the shared database, so:
  - it NEVER drops the schema (the sibling probe `harvest_github.py` does, which
    is exactly why that one cannot be reused here),
  - every document write is `ON CONFLICT DO NOTHING` (github.py:612),
  - curation, when wired, is SCOPED to the fetched model — never `rebuild_all`,
    which would recompute every other model's cells.
Nothing that already exists is edited or removed; a fetch only adds this model's
rows.

PROGRESS is written per stage to `var/fetch/<run_id>.jsonl` (local, gitignored).
The model page's fetch log polls it, so "which stage, what counts" is visible as
it happens rather than reconstructed after.

    python scripts/fetch_model.py <model_version_id> [--run-id ID] [--fetch-cap N]
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import logging
import os
import re
import sys
import threading
import time
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collect import usage  # noqa: E402
from collect.adapters.github import GitHubHarvester  # noqa: E402
from collect.adapters.queries import load_queries, plan_searches  # noqa: E402
from collect.assemble import prose  # noqa: E402

log = logging.getLogger(__name__)
from collect.config import settings  # noqa: E402
from collect.db import connect  # noqa: E402
from collect.http import build_client  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.registry.aliases import alias_rows  # noqa: E402
from collect.registry.assertions import assert_terms_reviewed  # noqa: E402
from collect.registry.seed import seed_models  # noqa: E402
from collect.registry.sources import load_sources  # noqa: E402

# The GitHub repos the sweep scopes to — the same set the probe uses, so the
# search space is the one that has actually returned model discussion before.
SCOPE = (
    "repo:langchain-ai/langchain",
    "repo:run-llama/llama_index",
    "repo:Aider-AI/aider",
    "repo:microsoft/autogen",
    "repo:crewAIInc/crewAI",
)
CAPABILITIES = (
    "tool_calling.schema_accuracy",
    "summarization.fidelity",
    "context.effective_window",
)

FETCH_DIR = ROOT / "var" / "fetch"

#: An on-demand fetch must stay responsive, and extraction is one LLM call per
#: thread whose latency scales with the prompt. A 45-comment thread produced a
#: ~13-minute E5 with no visible progress. Threads larger than this are DEFERRED
#: to the nightly batch (which is uncapped) rather than read on a click; the cap
#: is generous, so only pathologically large threads are held back.
MAX_FETCH_THREAD_CHARS = 30_000

#: Sources dedupe runs over. Every one has a prose extractor; a source
#: without one is refused by `dedupe_write` rather than signed raw.
DEDUPE_SOURCES = ("github", "reddit", "arxiv", "x", "devto", "hackernews", "huggingface")

#: How many threads ONE fetch may send to the language model.
#:
#: The daily budget caps the money; this caps the WAIT.
#:
#: WHAT A THREAD COSTS IN TIME, AND WHY THE OLD FIGURE MISLED WITHOUT BEING
#: WRONG. This said "roughly 15 seconds per thread on 2026-08-31" and used it
#: to size the cap. 15s is a MEDIAN, and the distribution has a long right tail,
#: so a median is the one summary that cannot be multiplied by a thread count.
#:
#: Measured 2026-09-14 over **115 consecutive-thread intervals in the 5 fetch
#: logs on this machine that carry per-thread lines** - the gap between
#: `reading thread N` and `reading thread N+1`, which is one thread's whole E5
#: (call, verification, store). Not a sample of extraction in general: it is
#: five runs on four models, on one machine, against one extractor.
#:
#:     min 9s    p50 15s    mean 33s    p90 64s    max 580s
#:
#: So: **quote 33s to size a cap, 15s to describe a typical thread**, and never
#: swap them. A single 580s thread is not an anomaly to discount - it is why the
#: mean is what a wait is built from.
#:
#: AT THE MEAN, THEN: 25 x 33s is ~14 minutes expected, and the tail can double
#: it. 40 would be ~22 minutes.
#:
#: ⚠ THIS LINE SAID "~28 minutes" AND THAT WAS THIS COMMENT CONTRADICTING
#:   ITSELF. 28 minutes is 25 x 67s - the "~65 seconds per thread" figure the
#:   paragraph below disavows by name, as "how a tail becomes a typical case".
#:   The per-thread number was corrected when it was measured properly and the
#:   minutes derived from it were not, so the stale figure outlived its own
#:   retraction four lines away. Checked against git: the cap was already 25
#:   when "28 minutes" was written, so it was never a leftover from a larger
#:   cap - just arithmetic nobody redid. Rule 7: a figure travels with its
#:   denominator, and that includes the one it was multiplied by.
#:
#: (One figure this replaces was mine and was worse: "~65 seconds per thread",
#: computed as wall-clock over threads-completed on one run that happened to
#: contain the 580s outlier. It lands within a second of the p90 by coincidence.
#: A denominator of one run is how a tail becomes a typical case.)
#:
#: SMALL IS SAFE BECAUSE THE PIPELINE RESUMES. `already_extracted()` skips
#: threads already read at this pipeline version, so the next click continues
#: from here instead of re-reading. This is a pause, not a ceiling on what can
#: ever be extracted.
MAX_FETCH_THREADS = int(os.getenv("FETCH_MAX_THREADS", "25"))

#: WHETHER A PER-MODEL FETCH FILLS ITS CAP FROM THE BACKLOG. Off by default.
#:
#: The backlog is every unread thread that neither names this model nor holds a
#: document this run harvested. Filling the cap from it spent the 2026-09-24
#: GPT-5.5 fetch on 22 of 24 threads about other models - 27 minutes of LLM calls
#: for a button that says "fetch GPT-5.5". Off, the fetch reads this model's
#: threads only and the backlog waits for the nightly batch, which reads the
#: whole unread pool. Deferred, not dropped (rule 8): nothing is marked read.
#: `FETCH_BACKLOG=on` restores the old fill.
FETCH_BACKLOG = os.getenv("FETCH_BACKLOG", "").strip().lower() in {"1", "on", "true", "yes"}

#: How far `len(prose(payload))` may differ from what `thread_context.offset_map`
#: says that member was, before the member is dropped rather than sliced.
#:
#: NOT A ROUND NUMBER. Measured over 4,525 documents on 2026-09-14: the largest
#: benign drift is +2, on github, where `github_issue_prose` joins title and body
#: with a separator the assembled text did not carry. The smallest real failure -
#: the payload loaded in place of the prose - is +1,239. Eight is four times the
#: former and two orders of magnitude below the latter.
#:
#: Widening this past ~10 stops it catching anything. If the github +2 is ever
#: fixed at its source this should go back to a much smaller number, because the
#: whole value of the check is that the gap it tolerates is tiny.
_MAX_PROSE_DRIFT = 8

#: A RUNAWAY GUARD on GitHub search calls, not a budget. GitHub is free; this
#: exists because `--fetch-cap` bounds only `rest_calls` (the per-issue fetches)
#: and the searches were counted by nothing at all.
#:
#: SET ABOVE WHAT A REAL RUN SPENDS, DELIBERATELY. The 2026-09-09 run issued 48
#: searches - 11 variants x 6 capability queries - in 107 seconds with no
#: throttling, so a cap of 12 was set on a 429 that never happened and would
#: have cut coverage by three quarters on the one platform that costs nothing.
#: 60 sits above the observed 48, so it does not bite in normal operation and
#: still stops an unbounded cross-product if the variant or capability list
#: grows: 20 variants x 6 queries is 120 searches nobody asked for.
MAX_GITHUB_SEARCHES = int(os.getenv("FETCH_MAX_GITHUB_SEARCHES", "60"))

#: X pages per model. NOT a post count - twitter241 ignores `count` and
#: paginates by cursor, so a page is 20 posts however many are asked for, and
#: this is the only depth lever there is. Three pages is ~60 retrieved against
#: X 100,000/month ceiling, which is a TENTH of Reddit and the reason this is
#: bounded at all.
X_PAGES_PER_MODEL = int(os.getenv("FETCH_X_PAGES", "3"))


# ── THE TERMINAL ACCOUNT OF A RUN ───────────────────────────────────────────
#
# `judge/app.py` spawns this script with its streams INHERITED, so everything
# written here lands in the terminal running the backend. That is the only place
# a person can watch a fetch WITHOUT the model page open, and until those streams
# stopped going to DEVNULL there was no such place: a run harvested, called a
# paid model and wrote rows for up to twenty minutes in complete silence.
#
# THIS IS A SECOND RENDERING OF THE JSONL LOG, NEVER A SECOND SOURCE. Every line
# below is formatted from a record `Progress._write` has already put on disk, so
# the terminal cannot say something the log does not - and losing the terminal
# (a closed window, a redirect to a full disk) costs the rendering and not the
# record. That is the same reason the log is a file rather than a table.
#
# ASCII ONLY, DELIBERATELY. An arrow or a box-drawing character is one cp1252
# console away from a `UnicodeEncodeError` raised inside a print, which would end
# a run over its own progress report. This project has already paid for one
# UTF-8/cp1252 round trip (FRONTEND.md, the double-encoded em dashes); a log line
# is not worth a second.
CONSOLE_WIDTH = 100

#: Stage `detail` strings in this file are paragraphs - they are written for the
#: fetch panel, which has a column to put them in. Wrapped to this many lines on
#: the console and then cut, because the terminal is a step-by-step account and
#: not the place to read a caveat in full. The whole text is always in the JSONL
#: and on the page; the cut is marked so nobody mistakes it for the end.
CONSOLE_DETAIL_LINES = 3

#: How far a stage's counts and detail sit under its heading.
INDENT = 4


#: Where `_say` also writes, once `open_transcript` has been called. The
#: terminal is the point of this output and the file is the copy: a scrollback
#: is gone the moment somebody closes the window, and an on-demand fetch is
#: exactly the thing you want to read AFTER it went wrong.
#:
#: NOT the same file as `logs/backend.log`. A fetch is one run with a beginning
#: and an end, so it gets one file per run named after it, the way
#: `var/fetch/<run_id>.jsonl` already is - interleaving twenty minutes of one
#: run into a rolling backend log would make both harder to read.
_TRANSCRIPT = None


def open_transcript(run_id: str) -> Path | None:
    """Start copying console output to `logs/fetch-<run_id>.log`.

    Never raises: a read-only checkout or a full disk costs the copy, not the
    run. Returns the path so the header can name it, or None when it could not
    be opened - which the header then says rather than implying a file exists.
    """
    global _TRANSCRIPT
    try:
        import logging_setup

        directory = logging_setup.logs_dir()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"fetch-{run_id}.log"
        _TRANSCRIPT = path.open("a", encoding="utf-8")
        return path
    except Exception:  # noqa: BLE001 - see the docstring
        _TRANSCRIPT = None
        return None


def transcript_name(run_id: str, model_slug: str | None = None) -> str:
    """`fetch-<model>-<run_id>.log`, or `fetch-<run_id>.log` when no name is known.

    THE MODEL NAME IS IN THE FILE NAME since 2026-09-24. A run started from the
    page gets a run id built on the registry id (`mv_1bb208f033c7ce0f-072e3516`),
    so a Grok 4.6 run was invisible to anyone looking for "grok" in `logs/`.
    `model_slug` is the canonical id with `/` as `_` (`x-ai_grok-4.6`); it is
    not repeated when the run id already starts with it, as it does for a run
    started by slug (`openai_gpt-6-astra-b6c576d3`).
    """
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", (model_slug or "").replace("/", "_")).strip("_.")
    if slug and not run_id.startswith(slug):
        return f"fetch-{slug}-{run_id}.log"
    return f"fetch-{run_id}.log"


def name_transcript(run_id: str, model_slug: str | None) -> Path | None:
    """Rename the open transcript once E1 knows which model this is. Never raises.

    The name is not known when the transcript opens - that is before E1 - so the
    file starts as `fetch-<run_id>.log` and is renamed here. CLOSED FIRST:
    Windows will not rename a file that is open. On any failure the copy keeps
    its first name and the run carries on; the header says which name it has.
    """
    global _TRANSCRIPT
    if _TRANSCRIPT is None:
        return None
    current = Path(_TRANSCRIPT.name)
    target = current.with_name(transcript_name(run_id, model_slug))
    if target == current:
        return current
    try:
        _TRANSCRIPT.close()
        current.rename(target)
        _TRANSCRIPT = target.open("a", encoding="utf-8")
        return target
    except Exception:  # noqa: BLE001 - see the docstring
        try:
            _TRANSCRIPT = current.open("a", encoding="utf-8")
        except Exception:  # noqa: BLE001
            _TRANSCRIPT = None
        return None


def _use_utf8_console() -> None:
    """Write UTF-8 to the terminal, replacing what it cannot take. Never raises.

    ⚠ ASCII IN OUR OWN STRINGS IS NOT ENOUGH, BECAUSE THE EVIDENCE IS NOT OURS.
      A thread title reads `Bend - A language...` with a real em dash, and
      quotes carry whatever an engineer typed. On Windows `sys.stderr` defaults
      to cp1252, so U+2014 goes out as the single byte 0x97 - which a terminal
      reading UTF-8 renders as a replacement character. Every quote this log
      prints was arriving visibly corrupted, and a log of VERBATIM QUOTES that
      silently mangles them is worse than one that prints nothing.

      Note the failure is not a crash here: cp1252 HAS an em dash, so nothing
      raised and the test over `_say` literals stayed green. It is a mismatch
      between what we encode and what the terminal decodes, which no check on
      our own string constants can see.

    `errors="replace"` keeps the guarantee this file cares about more: a
    character no encoding can carry becomes a `?` rather than an exception that
    ends a paid run inside its own progress report.
    """
    for stream in (sys.stderr, sys.stdout):
        # A redirected, wrapped or already-detached stream has no `reconfigure`.
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _say(line: str = "") -> None:
    """One line to the inherited terminal, and to the transcript. NEVER raises.

    A closed console, a full pipe or an encoding the stream will not take must
    not end a run that is otherwise fine. This is the REPORT of the work, not
    the work, and the record it is rendering is already on disk.

    The two writes are guarded SEPARATELY so a failing file cannot silence the
    terminal, and a closed terminal cannot stop the file.
    """
    try:
        sys.stderr.write(line + "\n")
        sys.stderr.flush()
    except Exception:  # noqa: BLE001 - see the docstring
        pass
    if _TRANSCRIPT is not None:
        try:
            _TRANSCRIPT.write(line + "\n")
            _TRANSCRIPT.flush()
        except Exception:  # noqa: BLE001
            pass


def _rule(char: str = "-") -> None:
    _say(char * CONSOLE_WIDTH)


def _n(value) -> str:
    """A count with thousands separators, or `?` when we were given nothing.

    `?` rather than `0`, per rule 6: a token count we never received is not a
    call that used no tokens, and this line is read as a spend report.
    """
    return f"{value:,}" if isinstance(value, int) else "?"


def _usd(
    model: str, input_tokens: int, output_tokens: int, cached_input_tokens: int = 0
) -> str:
    """What this call cost, or why no figure is shown.

    MEASURED TIMES PUBLISHED, and neither half is invented: the tokens come from
    the provider's own usage block and the rate from `MODEL_PRICING`. A model we
    hold no rate for prints the tokens and says `unpriced` - it does NOT print
    `$0.0000`, which is rule 6 exactly (a missing price is not a free call) and
    is the same answer `spend_ledger.record` gives the ledger.
    """
    from judge.extract.budget import pricing_for
    from judge.spend_ledger import cost_of

    rate = pricing_for(model)
    if rate is None:
        return f"unpriced (no published rate for {model})"
    return f"${cost_of(input_tokens, output_tokens, rate, cached_input_tokens):.6f}"


#: The (id, status) of the last stage line rendered, so a heading is printed
#: when the run MOVES rather than once per record.
#:
#: E5 writes five or six `running` lines as it selects, screens and reads
#: threads. A heading on each would put the same title on the screen six times
#: and make the section breaks meaningless - the heading is there to say "a new
#: thing is happening", so it prints when the stage or its status changes and
#: the rest of the lines hang underneath it as continuation.
_LAST_STAGE: tuple[str, str] | None = None


#: How much of a quote reaches the terminal. The schema permits quotes far
#: longer than a line, and the point here is to let a reader RECOGNISE what the
#: model found - the verbatim span is stored in `claim.quote` and rendered in
#: full on the board, which is where it is read as evidence.
CONSOLE_QUOTE_CHARS = 150

#: The board's three sections as the page names them, in the page's order.
#: Keys are `BoardEntry.section` (`judge/extract/schema.py`).
BOARD_SECTION_LABELS = {
    "best_for": "Best for",
    "capability": "Capabilities",
    "metric": "Metrics",
}

#: `FETCH_LOG_TEXT=1` also dumps the flattened text of every thread before its
#: call. Off by default and deliberately so: 20 threads x up to 30,000 chars is
#: the whole corpus in the scrollback, and the text is already on disk under
#: `raw_store/flattened/`. On when somebody is debugging what the model was
#: actually shown, which is the one question the summary cannot answer.
LOG_SENT_TEXT = os.getenv("FETCH_LOG_TEXT", "").strip().lower() in {"1", "true", "yes"}


def _title_of(thread) -> str:
    """The thread's title - the first line of what the model is shown.

    `prose.py` composes every document as `title + TITLE_SEPARATOR + body`, so
    the first non-empty line is the root post's title on every platform. Falls
    back to the opening of the body for a document that genuinely has no title,
    rather than printing an empty string that would read as a missing thread.
    """
    for line in (thread.flattened_text or "").splitlines():
        line = line.strip()
        if line:
            return line if len(line) <= 88 else line[:85] + "..."
    return "(no title - empty flattened text)"


def _console_stage(rec: dict) -> None:
    """Render one `kind: "stage"` record as one step of the run."""
    global _LAST_STAGE
    import textwrap

    at = (rec.get("at") or "")[11:19] or "--:--:--"
    sid = str(rec.get("id", "?"))
    name = str(rec.get("name", ""))
    status = str(rec.get("status", ""))

    if (sid, status) != _LAST_STAGE:
        _LAST_STAGE = (sid, status)
        # A HEADING, NOT A PREFIXED LINE. Twenty-odd stages of flat text is a
        # wall that a reader has to parse to find where one thing ended and the
        # next began; the rule does that for them. ASCII only - see the module
        # note on cp1252.
        title = f" {sid}  {name} "
        tail = f" {status}  {at}"
        fill = max(3, CONSOLE_WIDTH - len(title) - len(tail) - 2)
        _say("")
        _say("--" + title + "-" * fill + tail)

    # The counts a stage reported, on their own line. Same selection the fetch
    # panel makes (`SKIP_FIELDS` in FetchPanel.jsx): the bookkeeping fields
    # identify the record, the rest is what the stage found.
    skip = {"kind", "id", "name", "status", "at", "detail"}
    nums = [f"{k.replace('_', ' ')}={v:,}" if isinstance(v, int) and not isinstance(v, bool)
            else f"{k.replace('_', ' ')}={v}"
            for k, v in rec.items()
            if k not in skip and isinstance(v, (int, float, bool))]
    if nums:
        # Wrapped like the detail. A stage reporting eight counts ran to 117
        # characters on one line and wrapped wherever the terminal happened to
        # be, which breaks a `name=value` pair across the fold.
        for line in textwrap.wrap(" ".join(nums), width=CONSOLE_WIDTH - INDENT):
            _say(" " * INDENT + line)

    detail = (rec.get("detail") or "").strip()
    if detail:
        lines = textwrap.wrap(detail, width=CONSOLE_WIDTH - INDENT) or []
        for line in lines[:CONSOLE_DETAIL_LINES]:
            _say(" " * INDENT + line)
        if len(lines) > CONSOLE_DETAIL_LINES:
            # SAID, NOT SILENTLY TRUNCATED. A caveat cut off mid-sentence with
            # no mark reads as the whole caveat, and these details are where a
            # stage explains what it could NOT do.
            _say(" " * INDENT + "... (cut; full text in var/fetch/ and on the page)")


class RunStopped(BaseException):
    """A person pressed Stop. NOT an `Exception`, deliberately.

    Every harvest arm and every later stage in `main` is wrapped in
    `except Exception` that turns a failure into a stage row reading `error`.
    A stop request travelling through those would be RECORDED AS THE ARM
    FAILING - the run would report "Harvest · Reddit · error" when nothing
    about Reddit went wrong, and the log is the only account anybody has of
    what a run did.

    Deriving from BaseException is the same choice the standard library makes
    for `KeyboardInterrupt`: this is not a fault in the code it passes
    through, so it passes through untouched. `with` blocks still run their
    `__exit__`, so the database connection and the HTTP client close normally.
    """


class Progress:
    """One run's per-stage log. Append-only JSONL the fetch view tails.

    THE FILE IS THE SURVIVOR AND THE TABLE IS THE SHARED VIEW. Every line is
    written to disk first and mirrored into `fetch_log` best-effort, because
    the whole reason this log is a file is that a run which dies BECAUSE THE
    DATABASE IS UNREACHABLE must still be able to say so. That is not
    hypothetical: it is how the 2026-09-09 and 2026-09-10 runs were diagnosed,
    the second of them while the shared database was down for a day. A log that
    needs the database to record the database being unreachable records
    nothing, exactly when it matters most.

    So the mirror never raises and never blocks: a failed insert costs the
    shared view of one line, not the line and not the run.
    """

    def __init__(self, run_id: str, model_version_id: str) -> None:
        FETCH_DIR.mkdir(parents=True, exist_ok=True)
        self.path = FETCH_DIR / f"{run_id}.jsonl"
        #: A STOP REQUEST IS A FILE, beside the log and for the same reason the
        #: log is one: it has to work when the database does not. `POST
        #: /fetch/stop` creates it, this process notices at its next stage
        #: boundary. No signal, no PID, nothing that breaks when the backend
        #: restarts between the request and the run noticing it.
        self.stop_path = FETCH_DIR / f"{run_id}.stop"
        #: RAISED AT MOST ONCE. `main`'s RunStopped handler writes a STOP stage
        #: row before it writes the end record, and that row goes through
        #: `stage()` like any other - so without this latch the handler's own
        #: line raised RunStopped again, escaped `main` entirely, and
        #: `prog.done()` never ran. The log then had no `end` record and the UI
        #: polled that run forever. Measured, not imagined.
        self._stop_raised = False
        self.run_id = run_id
        self.model_version_id = model_version_id
        #: When this run began, as a tz-aware UTC datetime. READ BY SELECTION,
        #: not only by the log: `build_thread_inputs` scopes the extraction to
        #: documents this run harvested, and `fetched_at >= started_at` is the
        #: only marker that identifies them - the harvest arms write
        #: `harvest_run_id=None`, so there is no id to join on.
        self.started_at = datetime.now(UTC)
        self._seq = 0
        #: Stop trying after the first failure. A database that is down stays
        #: down for the length of a run, and re-attempting a connection on
        #: every stage line turns a quiet mirror into a per-line timeout.
        self._mirror = True
        #: TWO THREADS WRITE NOW, so `_seq` and the file append need one. The
        #: heartbeat below runs off the main thread on purpose — that is the
        #: whole point of it — and two unsynchronised appends would interleave a
        #: line and hand the same seq to both.
        self._lock = threading.Lock()
        self._stop_beating = threading.Event()
        #: WHAT THE PAID STAGE ACTUALLY SPENT, accumulated by the E5 hooks and
        #: printed by `done()`. Kept here rather than in `extract_and_curate`
        #: because the footer belongs to the RUN: a run that is stopped, or that
        #: dies in E6, has still spent whatever E5 spent, and a total printed
        #: only on the happy path would report the least when it matters most.
        #:
        #: `threads`/`posts` count what was SENT, `verified`/`stored` what came
        #: back. They are four numbers and not one, because a thread that
        #: returned nothing is a finding and averaging it away hides that.
        self.llm = {"model": None, "threads": 0, "posts": 0, "chars": 0,
                    "input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0,
                    "verified": 0, "stored": 0, "truncated": 0}
        self._write({"kind": "run", "run_id": run_id,
                     "model_version_id": model_version_id, "at": _now()})
        # OPENED BEFORE THE HEADER so the header is the transcript's first line
        # too - a copy that starts halfway through the run it is a copy of is
        # the kind of thing nobody notices until they need it.
        _use_utf8_console()
        transcript = open_transcript(run_id)
        _rule("=")
        _say(f"  FETCH   {model_version_id}")
        _say(f"  run     {run_id}")
        _say(f"  records var/fetch/{run_id}.jsonl")
        _say(f"  log     {transcript}" if transcript
             else "  log     (logs/ could not be opened - terminal only)")
        _rule("=")
        self._start_heartbeat()

    # ── the heartbeat ────────────────────────────────────────────────────────
    #
    # WHY A RUN HAS TO SAY IT IS ALIVE, SEPARATELY FROM SAYING WHAT IT IS DOING.
    #
    # The reaper marks a run abandoned when it has written nothing for 45
    # minutes, and that is the only signal available across machines: the
    # database is shared, the process is not, so "is it still running" cannot be
    # asked of a pid on somebody else's laptop.
    #
    # But silence and death are different things, and @anoojntglobal-sudo caught
    # the gap on #285: a run wedged inside one call is silent AND alive. Reaping
    # it would assert `abandoned` about a process still holding its connection
    # and still able to write threads 28+ if the call returned — a missing value
    # becoming a definite one, which is the exact shape the record was written to
    # avoid.
    #
    # A heartbeat off the main thread closes it. Stage lines say what a run is
    # DOING and stop when it wedges; this says it EXISTS and keeps going, so:
    #
    #     no heartbeat        the process is gone            -> reap
    #     heartbeat, no stage the process is wedged          -> a person looks
    #
    # The reaper needs no change: it keys on `max(at)` over every line, so a
    # heartbeat simply makes silence honest. And `collapseStages` in
    # FetchPanel.jsx skips anything that is not `kind: "stage"`, so these never
    # reach the page.
    HEARTBEAT_SECONDS = float(os.getenv("FETCH_HEARTBEAT_SECONDS", "60"))

    def _start_heartbeat(self) -> None:
        def beat() -> None:
            # `wait` rather than `sleep`: `done()` sets the event and the thread
            # leaves immediately instead of holding the process open for up to a
            # minute after the run has finished.
            while not self._stop_beating.wait(self.HEARTBEAT_SECONDS):
                with contextlib.suppress(Exception):
                    # NEVER RAISES. A heartbeat that could end a run would be a
                    # liveness check that kills the patient.
                    self._write({"kind": "alive", "at": _now()})

        self._heart = threading.Thread(
            target=beat, name=f"heartbeat-{self.run_id}", daemon=True
        )
        self._heart.start()

    def _write(self, rec: dict, *, console: bool = True) -> None:
        with self._lock:
            seq = self._seq
            self._seq += 1
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            mirror = self._mirror
        # THE TERMINAL, AFTER THE FILE AND INSIDE NOTHING. The disk write above
        # is what a run is judged on; this is a rendering of it for whoever is
        # watching, so it happens once the record is safe and it cannot raise.
        # `alive` heartbeats are skipped: they exist so the reaper can tell a
        # wedged run from a dead one, and a minute tick in the terminal is the
        # definition of a junk line.
        if console and rec.get("kind") == "stage":
            _console_stage(rec)
        if mirror:
            # OUTSIDE THE LOCK. The mirror opens a connection and can wait on the
            # network; holding the lock across it would let a slow database stall
            # the main thread behind a heartbeat, which is the opposite of what
            # this is for.
            self._mirror = _mirror_fetch_line(
                run_id=self.run_id, seq=seq, rec=rec,
                model_version_id=self.model_version_id,
            )

    def stop_requested(self) -> bool:
        """Has somebody asked this run to stop? Never raises."""
        try:
            return self.stop_path.exists()
        except OSError:
            # An unreadable var/ must not stop a run that was going fine.
            return False

    def checkpoint(self) -> None:
        """Raise `RunStopped` if a stop has been asked for.

        CALLED FROM `stage()`, WHICH IS WHY ONE CHECK COVERS EVERYTHING. Every
        transition in the pipeline goes through `stage()` - including the
        per-query updates inside the harvest arms - so the run notices a stop
        at the next thing it was going to report, rather than only between the
        big stages. A check placed in `main` instead would have sat behind
        whichever arm was running, and the arms are the slow part.
        """
        if self._stop_raised:
            # Already unwinding. Raising again would only break the recording
            # of the stop, which is the one thing that still has to happen.
            return
        if self.stop_requested():
            self._stop_raised = True
            raise RunStopped

    def stage(self, id_: str, name: str, status: str, _console: bool = True,
              **fields) -> None:
        # status: running | ok | skipped | error. Counts and detail ride along
        # so the log line is a finding, not just a heartbeat.
        #
        # `_console` SUPPRESSES THE TERMINAL RENDERING OF THIS LINE AND NOTHING
        # ELSE. It is a parameter rather than a field, so it never reaches the
        # JSONL, `fetch_log` or the page - the record is identical either way,
        # and only the second rendering of it is skipped. Used by E5's
        # per-thread line, which the console prints in a richer form (posts,
        # tokens, cost) immediately afterwards; printing both would say the same
        # thing twice with one of them missing the numbers.
        self._write({"kind": "stage", "id": id_, "name": name,
                     "status": status, "at": _now(), **fields}, console=_console)
        # AFTER the write, never before: the stage that just finished is a real
        # finding and belongs in the log whether or not the run continues.
        self.checkpoint()

    def done(self, status: str, detail: str = "") -> None:
        """The run's last line. NEVER checkpoints - this is how a stop is
        recorded, and a `done` that could raise `RunStopped` would leave the
        run with no end record and the UI polling a run that had finished."""
        # THE HEARTBEAT STOPS FIRST. A beat written after the end record would
        # sort after it, and a run whose last line is `alive` reads as one that
        # came back from the dead.
        self._stop_beating.set()
        self._write({"kind": "end", "status": status, "detail": detail, "at": _now()})
        self._console_footer(status, detail)

    def _console_footer(self, status: str, detail: str) -> None:
        """The run's totals, on the terminal only. Never raises - `_say` swallows.

        PRINTED FOR EVERY ENDING, including `stopped` and `error`. A stopped run
        has already paid for the threads it read, and a footer that appeared only
        on success would report nothing in the one case somebody needs the number
        - which is the shape of defect rule 4 names: an absence we caused reading
        as an absence we found.
        """
        s = self.llm
        _rule("=")
        _say(f"  RUN {status.upper()}   {detail}")
        _say(f"  model   {self.model_version_id}")
        if s["threads"] == 0:
            # NOT "cost $0.00". No thread reached the model, so there is no
            # spend to report rather than a spend of zero - and E5's own stage
            # line above has already said WHY (nothing new, all deferred, or
            # every thread dropped at the pre-LLM gates).
            _say("  llm     no thread reached the model - see the E5 line above for why")
            _rule("=")
            return
        _say(f"  llm     {s['model']}")
        _say(f"  sent    {_n(s['threads'])} thread(s) - {_n(s['posts'])} post(s), "
             f"{_n(s['chars'])} chars")
        _say(f"  tokens  in {_n(s['input_tokens'])} ({_n(s.get('cached_input_tokens', 0))} "
             f"cached)  out {_n(s['output_tokens'])} "
             f"({_n(s.get('reasoning_tokens'))} reasoning)")
        cost = _usd(s["model"], s["input_tokens"], s["output_tokens"],
                    s.get("cached_input_tokens", 0))
        _say(f"  cost    {cost}")
        from judge.legacy import legacy_cells_enabled
        _say(f"  back    {_n(s['verified'])} claim(s) verified, "
             f"{_n(s.get('board', 0))} board entr(ies) stored"
             + (f", {_n(s['stored'])} legacy claim row(s)"
                if legacy_cells_enabled() else ""))
        if s["truncated"]:
            # Rule 4 at the footer. A truncated thread produced claims, so it
            # looks like a complete read in every other number on this block.
            _say(f"  ! {s['truncated']} thread(s) stopped at the token ceiling and were "
                 f"not read to the end")
        _rule("=")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _mirror_fetch_line(
    *, run_id: str, seq: int, rec: dict, model_version_id: str
) -> bool:
    """Copy one log line into `fetch_log`. Returns whether to keep mirroring.

    NEVER RAISES. See `Progress` — the file has already taken the line, and an
    exception here would mean the database going down takes the run's own
    account of it down too.

    The id hashes run and position, so replaying a run's file into the table is
    idempotent and the backfill of the 18 existing logs can be re-run freely.
    `seq` is stored because the log is a SEQUENCE: timestamps here are
    second-resolution and several stages share one, so ordering by time alone
    scrambles the order in which things actually happened.
    """
    try:
        payload = json.dumps(rec, sort_keys=True)
        line_id = "fl_" + hashlib.sha256(
            f"{run_id}|{seq}|{payload}".encode()
        ).hexdigest()[:24]
        # THE GUARDED CONNECTION, not `db.transaction()`. The latter reads
        # DATABASE_URL with no test guard and no short timeout, which is how
        # this mirror wrote fixture lines into the shared table during a suite
        # run — and `on conflict do nothing` kept the row count flat, so the
        # first check for it came back clean.
        conn = usage.telemetry_connection()
        if conn is None:
            return False
        try:
            with conn:
                conn.execute(
                    "insert into fetch_log "
                    "(id, run_id, seq, at, machine, payload, kind, model_version_id) "
                    "values (%s,%s,%s,%s,%s,%s,%s,%s) on conflict (id) do nothing",
                    (line_id, run_id, seq, rec.get("at"), usage.machine(),
                     payload, rec.get("kind"), model_version_id),
                )
        finally:
            conn.close()
        return True
    except Exception:
        return False


def _safe_rollback(conn) -> None:
    """Roll back if the connection still can. Never raise.

    THIS IS WHAT ENDED THE 2026-09-09 RUN. E3 raised `the connection is lost`,
    its handler called `conn.rollback()` to clean up, and the rollback raised
    the same error on the same dead socket - out of the handler, past E3b, E4
    and E5, into the outer catch. The log showed `? · fetch · error` and E3
    stuck on "running", so the one stage that failed was the one stage with no
    verdict, and the three that never ran left no trace at all.

    A recovery path that can fail is not a recovery path.
    """
    with contextlib.suppress(Exception):
        conn.rollback()


class _Db:
    """The run's connection, re-opened when the server drops it.

    A fetch holds ONE connection for its whole life, and the harvest phase is
    minutes of HTTP with no SQL in it. Cloud Postgres and the boxes in front of
    it reap idle sockets, so the connection that E1 read the registry on is not
    always the connection E3 needs - and libpq only finds out at the next query.

    Two halves to the fix and both are needed. `collect/db.py` now sets TCP
    keepalives, so an idle socket proves it is alive rather than hoping. This
    is the other half: before each stage the connection is PROVEN with a
    `SELECT 1`, and re-opened if that fails. Cheap - one round trip per stage
    against stages that take seconds to minutes.

    A reconnect is REPORTED as its own stage row rather than done quietly. A run
    that silently reconnected four times looks identical in the log to one that
    never lost the database, and those are different afternoons.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn = connect(dsn)
        self.reconnects = 0

    @property
    def raw(self):
        """The connection as-is, unchecked. For use right after opening."""
        return self._conn

    def live(self, prog: Progress | None = None):
        """The connection, proven live this instant.

        The rollback first is deliberate: a stage that failed may have left the
        transaction aborted, in which case every later query raises
        `InFailedSqlTransaction` and the connection looks dead when it is only
        dirty. Every stage here commits its own writes, so there is never
        anything at a stage boundary a rollback could throw away.
        """
        conn = self._conn
        try:
            if conn.closed:
                raise RuntimeError("connection is closed")
            conn.rollback()
            conn.execute("SELECT 1").fetchone()
            return conn
        except Exception as exc:
            with contextlib.suppress(Exception):
                conn.close()
            self._conn = connect(self._dsn)
            self.reconnects += 1
            if prog is not None:
                prog.stage("DB", "Database · reconnect", "ok",
                           reconnects=self.reconnects,
                           detail=f"the connection was gone ({str(exc).splitlines()[0][:80]}) "
                                  f"and was re-opened; reconnect #{self.reconnects} this run")
            return self._conn


def _variants_for(conn, model_version_id: str, canonical_id: str) -> list[str]:
    """Search variants for this model, from the append-only `model_alias` table.

    Falls back to the seed model's computed aliases when the model is one of the
    seeds and carries no alias rows yet. Read-only.
    """
    # `search_eligible` is a Python field on AliasRow, not a DB column. In the
    # table, a variant is searchable when it names a version or snapshot (a bare
    # `family` form like "sonnet" names a line, not a model) and is still
    # current.
    #
    # ⚠ "STILL CURRENT" IS NOT `valid_until IS NULL`, AND READING IT THAT WAY
    #   SILENTLY EMPTIED A MODEL'S SEARCH.
    #
    #   `seat` copies `model_version.retirement_date` into the alias's
    #   `valid_until`, which is right - a surface stops naming a model when the
    #   model retires. But `z-ai/glm-5.3` carries `retirement_date`
    #   **2098-12-31**, a sentinel the poll supplies, and the old predicate read
    #   a window closing in seventy-two years as one already shut. GLM 5.3 was
    #   seated with two alias rows on 2026-09-16 and a fetch against it still
    #   reported:
    #
    #       E1 Registry ok     resolved Z.ai: GLM 5.3 - 0 search-eligible name variant(s)
    #       E2 Harvest skipped no search variants for this model - nothing to search for
    #
    #   Measured the same day: 10 of 344 registry rows carry a retirement_date,
    #   and of the alias rows with a non-null `valid_until`, **4 are in the
    #   future and 0 are in the past**. So the old filter excluded four rows
    #   that should search and not one that should not - it was doing only
    #   harm, and would do more as the poll supplies more dates.
    #
    #   FR-4 append-only is still why `valid_until` exists: a closed window says
    #   a surface stopped meaning this model on a date. That is a claim about
    #   the PAST, so the comparison belongs against now(), not against NULL.
    rows = conn.execute(
        "SELECT variants FROM model_alias "
        "WHERE model_version_id = %s "
        "AND specificity IN ('version', 'snapshot') "
        "AND (valid_until IS NULL OR valid_until > now())",
        (model_version_id,),
    ).fetchall()
    variants: set[str] = set()
    for (vs,) in rows:
        for v in (vs or []):
            variants.add(v)
    if not variants:
        seed = next((m for m in seed_models() if m.canonical_id == canonical_id), None)
        if seed is not None:
            for r in alias_rows(seed):
                if r.search_eligible:
                    variants.update(r.variants)
    return _order_variants(variants)


def _order_variants(variants) -> list[str]:
    """DISTINCT SURFACES FIRST, then extra spellings of each.

    This was `sorted(variants)` and the caps made that expensive. Every platform
    arm searches only the first 1-3 variants - arXiv, X, dev.to and Hacker News
    take two - and alphabetical order put "Claude Fable 5.1" and
    "Claude-Fable-5.1" first: two spellings of ONE surface, spending the whole
    budget without ever trying "Fable 5.1", which is the form the corpus shows
    people actually write.

    So variants are grouped by their normalised key - one key IS one surface -
    and the shortest spelling of each key goes first, because the short form is
    what somebody types. Only once every distinct surface has had a query do the
    alternate spellings follow.

    Ordering matters MORE than breadth here: a wider alias list that never gets
    queried past position two is not wider at all.
    """
    from collect.registry.aliases import normalize

    by_key: dict[str, list[str]] = {}
    for v in variants:
        by_key.setdefault(normalize(v), []).append(v)
    def rendering_rank(spelling: str) -> tuple:
        """SPACED first, then hyphenated, then concatenated.

        Length was the wrong ranking and it chose the worst query: the shortest
        spelling of a key is the CONCATENATION - "fable51", "gpt6" - which is
        precisely what nobody types into a search box. A search API has no fuzzy
        operator, so the query has to be the form a human wrote, and that is the
        spaced one. The concatenation is kept as a later query because it does
        occasionally appear in a slug or a hashtag.
        """
        spaced = " " in spelling
        hyphenated = "-" in spelling
        tier = 0 if spaced else (1 if hyphenated else 2)
        return (tier, len(spelling), spelling)

    for spellings in by_key.values():
        spellings.sort(key=rendering_rank)
    # Keys ordered by their own BEST spelling, so both "Fable 5.1" and "Claude
    # Fable 5.1" get a query inside a two-query cap rather than two spellings of
    # one of them.
    keys = sorted(by_key, key=lambda k: rendering_rank(by_key[k][0]))
    ordered: list[str] = [by_key[k][0] for k in keys]          # one per surface
    for k in keys:                                            # then the rest
        ordered.extend(by_key[k][1:])
    return ordered


def _ensure_github_source(conn) -> None:
    """Make sure the `github` source row exists — WITHOUT touching it if it does.

    `ON CONFLICT DO NOTHING`, so a fetch on a database that already has the row
    (the shared one does) changes nothing; a fresh database gets it once.
    """
    from psycopg.types.json import Json

    contract = load_sources()
    gh = next(s for s in contract.platforms if s["id"] == "github")
    conn.execute(
        "INSERT INTO source (id, platform, endpoint, base_trust, tos_notes, provenance,"
        " terms_ruling, terms_checked_on, terms_evidence)"
        " VALUES ('github','github','https://api.github.com',0.95,%s,'seed',%s,%s,%s)"
        " ON CONFLICT (id) DO NOTHING",
        (gh["tos_notes"], gh["terms_ruling"], gh["terms_evidence"]["checked_on"],
         Json({k: str(v) for k, v in gh["terms_evidence"].items()})),
    )
    conn.commit()


def harvest_github(conn, prog: Progress, variants: list[str], *, fetch_cap: int) -> int:
    """E2 harvest — live GitHub search for this model, appended to `document`.

    The terms gate runs first (the same one the nightly path runs), then the
    proven adapter loop: plan, harvest, `write_documents` (ON CONFLICT). Bounded
    by `fetch_cap` so an on-demand click cannot run away against the rate limit.
    Returns the number of documents newly inserted.
    """
    from datetime import UTC, datetime

    contract = load_sources()
    gh = next(s for s in contract.platforms if s["id"] == "github")
    assert_terms_reviewed([gh], rulings=contract.rulings,
                          observations={"github": {"access_path": "api"}},
                          today=datetime.now(UTC).date())

    entries = [e for cap in CAPABILITIES for e in load_queries().for_capability(cap)]
    plan = plan_searches(entries, variants, scope=SCOPE)
    prog.stage("E2", "Harvest", "running",
               variants=len(variants), planned_requests=plan.request_count,
               detail=f"GitHub search for {len(variants)} name variants "
                      f"× {len(entries)} capability queries")

    client = build_client(timeout=30.0, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {settings().github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    harvester = GitHubHarvester(
        client=client, store=RawStore(Path(settings().raw_store_path)),
        max_pages=1, max_fetch_per_query=15,
    )
    _ensure_github_source(conn)

    fetched = inserted = kept = candidates = 0
    for req in plan.requests:
        if fetched >= fetch_cap:
            prog.stage("E2", "Harvest", "running",
                       detail=f"fetch cap of {fetch_cap} issue-fetch call(s) reached, stopping")
            break
        # THE SEARCH CALLS, WHICH `fetch_cap` DOES NOT COUNT. It bounds
        # `rest_calls` - the per-issue fetches - and 48 searches went out
        # unbounded on 2026-09-09 against a 30-a-minute limit. Read from the
        # harvester's own ledger rather than recounted here, for the reason
        # github.py:375 gives: a total summed over what the caller happened to
        # keep under-reported its own failures once already.
        spent_searches = int(harvester.totals().get("search_calls") or 0)
        if spent_searches >= MAX_GITHUB_SEARCHES:
            prog.stage("E2", "Harvest", "running",
                       search_calls=spent_searches,
                       detail=f"search cap of {MAX_GITHUB_SEARCHES} reached after "
                              f"{spent_searches} search(es) — stopping before GitHub "
                              f"throttles and the platform reads as empty")
            break
        run = harvester.harvest(req)
        wrote = harvester.write_documents(conn, run)
        conn.commit()
        fetched += run.rest_calls
        inserted += wrote["inserted"]
        kept += run.sieve_yield.kept
        candidates += run.sieve_yield.candidates

    # THE HARVESTER'S OWN LEDGER, NOT THE LOOP'S RUNNING TOTALS. The loop
    # counted `rest_calls` only - issue fetches - so a run whose 48 SEARCHES all
    # failed reported "0 requests spent" and signed off `ok`. The adapter keeps
    # `search_calls` and `http_errors` in a ledger precisely because summing
    # over what a caller happened to hold under-reported its own failures once
    # already (github.py:375). Read it here rather than recount.
    totals = harvester.totals()
    searches = int(totals.get("search_calls") or 0)
    errors = int(totals.get("http_errors") or 0)
    throttled = int(totals.get("rate_limited_queries") or 0)
    parts = [f"{inserted} new document(s) appended",
             f"{kept} of {candidates} passed the sieve",
             f"{searches} search + {fetched} fetch call(s)"]
    if errors:
        parts.append(f"{errors} HTTP error(s)")
    if throttled:
        parts.append(f"{throttled} query(ies) throttled")
    # NOTHING CAME BACK AND REQUESTS FAILED: that is not a quiet platform, and
    # the two must not render alike. An empty result set with no errors stays
    # `ok` - GitHub genuinely may hold nothing about a model released last week.
    status = "error" if errors and not candidates else "ok"
    prog.stage("E2", "Harvest", status,
               requests_spent=fetched, search_calls=searches, http_errors=errors,
               rate_limited_queries=throttled,
               sieve_kept=kept, sieve_candidates=candidates,
               documents_inserted=inserted,
               detail="; ".join(parts))
    return inserted


def _write_rapidapi_quota(remaining: int | None, limit: int | None, run_id: str,
                          *, read_on: str) -> None:
    """Persist the latest RapidAPI quota reading. Delegates to `collect.usage`.

    KEPT AS A THIN WRAPPER RATHER THAN DELETED. The adapters now record every
    metered response themselves, so by the time an arm finishes, the file
    already holds a reading at least as fresh as this one. This call adds the
    `run_id`, which the adapter does not know - it is what ties a reading to
    the run that spent it - and it is harmless when the adapter has already
    written a later value with a null run.

    Two writers, one file, and that is fine because both go through
    `record_rapidapi_quota`: the write is atomic and the last one wins, which
    for a monotonically-decreasing quota is the correct rule.
    """
    from collect.usage import record_rapidapi_quota

    # WHICH SUBSCRIPTION THIS READING IS OF, picked the way the arm that made
    # the request picks it. Reddit has one candidate; X falls back
    # X_RAPIDAPI_KEY -> RAPIDAPI_KEY, and `key_for()` is the only thing that
    # knows which one answered. Hashed inside `record_rapidapi_quota` and never
    # stored - see `collect/usage.py:key_fingerprint`.
    if read_on == "x":
        from collect.adapters.x import key_for
        api_key = key_for()[0]
    else:
        from collect.config import settings as _settings
        api_key = _settings().rapidapi_key

    record_rapidapi_quota(
        remaining=remaining, limit=limit, read_on=read_on,
        read_by="harvest", run_id=run_id, api_key=api_key,
    )


def harvest_reddit(conn, prog: Progress, variants: list[str], *, max_searches: int,
                   max_threads: int) -> int:
    """E2 harvest — live Reddit search (RapidAPI) for this model, WITH comments.

    A post with no comments is refused by the assembler ("the blog shape, not a
    Reddit thread"), so posts-only harvesting produces nothing usable. This
    searches the top `max_searches` variants, then fetches the comment tree for
    the top posts up to `max_threads` — writing `[post, *comments]` so a real
    thread assembles. Bounded on BOTH axes because Reddit 429s at ~32 rapid
    calls: roughly max_searches + max_threads requests total. Append-only.
    """
    import httpx

    from collect.adapters.reddit import build_client, harvester_for_source
    from collect.adapters.reddit_write import write_documents as reddit_write
    from collect.ids import content_hash

    contract = load_sources()
    reddit_src = next(s for s in contract.platforms if s.get("id") == "reddit")
    store = RawStore(Path(settings().raw_store_path))
    queries = variants[:max_searches]
    prog.stage("E2R", "Harvest · Reddit", "running", queries=len(queries),
               detail=f"RapidAPI search for {len(queries)} variant(s), then comments "
                      f"for up to {max_threads} thread(s)")

    inserted = hits = threads = errors = 0
    failures: list[str] = []
    q_remaining = q_limit = None  # latest RapidAPI quota header seen this fetch
    with build_client() as client:
        searcher = harvester_for_source(reddit_src, client=client, store=store)
        for variant in queries:
            if threads >= max_threads:
                break
            # ONE FAILED LOOKUP USED TO COST THE WHOLE PLATFORM. Reddit's `_get`
            # deliberately does not catch transport errors - it is the only
            # adapter that lets them out, which is the honest choice - so a
            # single `getaddrinfo` failure on the first variant propagated past
            # every remaining variant and ended the arm. Twice, on 2026-09-09.
            # Caught per QUERY: the failure is still counted and named, but the
            # other variants are still asked. The client also retries the
            # connection twice before it ever gets here (collect/http.py).
            try:
                run = searcher.search(variant)
            except httpx.HTTPError as exc:
                errors += 1
                failures.append(f"{variant}: {type(exc).__name__} {str(exc)[:60]}")
                continue
            if run.quota_remaining is not None:
                q_remaining = run.quota_remaining
            if run.quota_limit is not None:
                q_limit = run.quota_limit
            hits += len(run.posts)
            for post in run.posts:
                if threads >= max_threads:
                    break
                try:
                    fetch = searcher.fetch_comments(post)
                except httpx.HTTPError as exc:
                    errors += 1
                    failures.append(f"comments {post.external_id}: {type(exc).__name__}")
                    continue
                # A comment fetch is a metered call, so its quota reading is as
                # fresh as a search's — take the latest either reports.
                if getattr(fetch, "quota_remaining", None) is not None:
                    q_remaining = fetch.quota_remaining
                if getattr(fetch, "quota_limit", None) is not None:
                    q_limit = fetch.quota_limit
                if getattr(fetch, "not_a_thread", False) or not getattr(fetch, "comments", None):
                    continue  # a post with no comments will not assemble
                items = [post, *fetch.comments]
                # THE PAYLOAD, NOT THE PROSE. This stored `sieve_text` for the
                # post and `body` for each comment - already-flattened TEXT -
                # and Reddit is the only platform that did. Both readers parse
                # JSON: `collect/assemble/reddit.py` refuses a non-JSON payload
                # ("REFUSED reddit payload: not JSON") and
                # `collect/assemble/prose.py:reddit_prose` needs `title` /
                # `selftext` / `body` keys. The 2026-09-10 run lost 716 of 718
                # documents to it, and `assemble/reddit.py` had already written
                # down the remedy: "store the raw getPostComments payload".
                #
                # `.raw` is the original `data` dict, kept on both types on
                # purpose (`_comment_of` ends with `raw=inner`), so this is the
                # payload as the platform sent it - not an envelope rebuilt here.
                #
                # `content_hash` moves onto the same bytes, so the hash keeps
                # identifying what is stored rather than something adjacent.
                # `ensure_ascii=False` IS LOAD-BEARING, NOT COSMETIC. It is the
                # house spelling - `github.py:703`, `huggingface.py:710`,
                # `x.py:1044`, and both Reddit sweeps - and this call site was
                # the only one missing it. `json.dumps` escapes every non-ASCII
                # character to `\uXXXX` without it, so THE SAME POST fetched by
                # this arm and by `collect/ops/sweep_reddit.py` produced two
                # different byte strings, two hashes and two stored objects
                # whenever its text was not pure ASCII - which on a corpus of
                # people quoting model output is most of it.
                #
                # That is not just wasted bytes. The store is content-addressed,
                # and `scripts/restore_reddit_payload_refs.py` repairs a broken
                # row by finding the SAME post's payload under some other
                # sweep's hash. Two spellings mean two hashes mean a payload the
                # repair cannot recognise as the one it is looking for - so a
                # divergent spelling silently removes rows from the set that can
                # ever be repaired. 264 rows were recovered that way on
                # 2026-09-14 and this defect was upstream of all of them.
                #
                # Existing refs stay valid: their objects are still in the store
                # under the old hash. What changes is that a re-fetch from here
                # now lands on the same object the other writers produce.
                def _payload(obj) -> str:
                    return json.dumps(
                        getattr(obj, "raw", None) or {},
                        ensure_ascii=False,
                        sort_keys=True,
                    )

                refs = {}
                for obj in items:
                    blob = _payload(obj)
                    refs[obj.external_id] = (store.put(blob).ref, content_hash(blob))
                # This is the model-name SEARCH arm: a query was issued but no
                # harvest_run row was opened, so `not_recorded` is the honest
                # provenance — reddit_write.py:147 names this exact caller. The
                # argument became required when retrieval_provenance merged, and
                # this call site was not updated with it.
                wrote = reddit_write(
                    conn, items, refs=refs, retrieval_provenance="not_recorded"
                )
                conn.commit()
                inserted += int(wrote.get("documents_inserted", 0) or 0)
                threads += 1
    _write_rapidapi_quota(q_remaining, q_limit, prog.run_id, read_on="reddit")
    detail = (f"{threads} thread(s) with comments fetched, "
              f"{inserted} document(s) appended")
    if errors:
        detail += f" — {errors} request(s) failed: " + "; ".join(failures[:3])
    prog.stage("E2R", "Harvest · Reddit", _harvest_verdict(errors, hits),
               search_hits=hits, threads_fetched=threads, documents_inserted=inserted,
               http_errors=errors,
               quota_remaining=q_remaining, quota_limit=q_limit,
               detail=detail)
    return inserted


def _gated_harvester(platform_id: str, factory, **kwargs):
    """Build a harvester through the adapter's OWN gate. Returns (h, why-not).

    EVERY ADAPTER PUBLISHES `harvester_for_source`, and it is the entry point
    anything that fetches must use. This lane learned that the expensive way:
    the Reddit path once had no such entry point, a 1,297-post corpus was
    gathered without the gate ever being asked, and the gate had been refusing
    Reddit correctly the whole time — nothing consulted it.

    So this does NOT call `assert_terms_reviewed` itself. It cannot: each ruling
    names its own live preconditions — `use_basis` for arXiv, and for X also
    `scraper_provider`, `credential_present` and an `access_path` of
    `rapidapi-reseller` — and only the adapter can observe them. A generic
    observation passed from here would be an observation NOBODY MADE wearing the
    costume of one that passed, which is precisely what rule 6 refuses.

    A platform absent from `contract/sources.yaml` is UNASSESSED, not refused,
    and the two must not render alike.
    """
    contract = load_sources()
    source = next((s for s in contract.platforms if s.get("id") == platform_id), None)
    if source is None:
        return None, (
            f"{platform_id} has no entry in contract/sources.yaml, so its terms have "
            "never been reviewed. Not refused — unassessed. Adding one is a contract "
            "change (two eyes), never something a fetch may assume for itself."
        )
    try:
        return factory(source, rulings=contract.rulings, **kwargs), ""
    except Exception as exc:
        return None, str(exc).splitlines()[0][:180]


def _harvest_verdict(errors: int, produced: int) -> str:
    """`error` when requests failed and nothing came back. Otherwise `ok`.

    EVERY ADAPTER HERE SWALLOWS `httpx.HTTPError` INTO A COUNTER and returns an
    empty run - which is right, because one failed query should not abandon the
    others. What was wrong was the stage above it: it reported `ok · 0 post(s)
    seen` whether the platform had been asked and answered nothing or asked and
    never connected. The 2026-09-09 log showed `E2X · ok · 0 post(s) seen` for
    two X queries that had failed to resolve DNS, one line below the Reddit arm
    reporting the same failure as an error.

    An empty result set with no errors stays `ok`, and that is not leniency: a
    model released last week genuinely has nothing written about it yet, and
    calling that a failure would make the log cry wolf on the normal case.
    """
    return "error" if errors and not produced else "ok"


def harvest_arxiv(conn, prog: Progress, variants: list[str], *, max_queries: int) -> int:
    """E2 harvest — arXiv search for this model, appended to `document`.

    Papers are the one source here that is CITED rather than reported. An author
    writing about a model is not an engineer reporting their own run, so what
    lands extracts as `relayed-from-elsewhere` and is weighted accordingly. It is
    harvested anyway because a paper naming a measurement is exactly the figure
    the metric pages want, and it arrives with a citation attached.
    """
    from collect.adapters.arxiv import harvester_for_source

    harvester, why = _gated_harvester(
        "arxiv", harvester_for_source,
        client=build_client(timeout=30.0),
        store=RawStore(Path(settings().raw_store_path)),
        max_pages=1,
    )
    if harvester is None:
        prog.stage("E2A", "Harvest · arXiv", "skipped", detail=why)
        return 0

    queries = variants[:max_queries]
    prog.stage("E2A", "Harvest · arXiv", "running", queries=len(queries),
               detail=f"arXiv search for {len(queries)} name variant(s)")
    inserted = papers = errors = found = 0
    for variant in queries:
        run = harvester.search(variant)
        found += len(getattr(run, "papers", []) or [])
        for paper in list(getattr(run, "papers", []) or [])[:5]:
            harvester.fetch_paper(paper, run)
        papers += len(getattr(run, "stored", []) or [])
        errors += int(getattr(run, "http_errors", 0) or 0)
        wrote = harvester.write_documents(conn, run, retrieval_provenance="not_recorded")
        conn.commit()
        inserted += int(getattr(wrote, "inserted", 0) or 0)
    detail = f"{papers} paper(s) stored, {inserted} document(s) appended"
    if errors:
        detail += f" — {errors} request(s) failed"
    prog.stage("E2A", "Harvest · arXiv", _harvest_verdict(errors, found),
               papers=papers, documents_inserted=inserted, http_errors=errors,
               detail=detail)
    return inserted


def harvest_x(conn, prog: Progress, variants: list[str], *, max_queries: int) -> int:
    """E2 harvest — X search for this model, appended to `document`.

    ONE REQUEST, ALL SURFACES, SINCE 2026-09-11. This issued one search PER
    VARIANT and took the first `max_queries` of them, so a model with five
    alias variants was searched on two and the other three were never asked.
    The surfaces are now clubbed into a single `"a" OR "b"` query.

    ⚠ IT DOES NOT SHARE REDDIT'S KEY OR QUOTA, and this docstring said it did.
      Measured 2026-09-10: two RapidAPI accounts, two meters, each 403 on the
      other's provider. X's ceiling is 100,000 a month against Reddit's
      1,000,000 - a TENTH, not a share - which is what makes the request
      saving below worth having rather than a tidy-up.

    MEASURED, NOT ASSUMED, on `opus 5`'s five variants
    (`docs/measurements/x-clubbed-surfaces.json`):

        today, 2 separate surfaces   2 requests -> 30 distinct   15.0 /request
        all 5 separate surfaces      5 requests -> 71 distinct   14.2 /request
        clubbed, 1 page              1 request  -> 20 distinct   20.0 /request

    Separate queries overlap and the platform charges for the duplicates - S1
    and S2 shared 10 of their 40 returns. A clubbed query cannot return the
    same post twice, so every one of its 20 is new. **Halving the requests
    per model while covering five surfaces instead of two.**

    WHAT IT COSTS, STATED BECAUSE THE SAVING IS NOT FREE. A page is 20 posts
    whatever the query, so one clubbed request retrieves 20 distinct where two
    separate ones retrieved 30. Depth is the lever if that matters: at the
    SAME 2-request budget, two clubbed pages returned 40 distinct against the
    old shape's 30. Left at one page here because page 1 is also the cleanest
    - 85% of its posts carried a variant literally, against 68% over three
    pages - and the sieve pays for the rest.

    `harvester_for_source` runs the ToS gate and THEN the credential, so a
    missing `RAPIDAPI_KEY` arrives here as a refusal to build rather than as a
    request that fails midway. Both are reported as `skipped` with the reason:
    neither is a fault of this run, and an error badge would say it was.

    IT STORED NOTHING, AND THE SIEVE WAS NOT WHY - THE SIEVE NEVER RAN
    ------------------------------------------------------------------
    Every X stage in the fetch log reads `20 post(s) seen, 0 document(s)
    appended`, and `document` held **zero rows with source='x'** on
    2026-09-14, across every run ever made. That looks like a filter set too
    tight. It was not a filter at all.

    This arm called `harvester.search(query)`, which is the retrieval HALF of
    `harvester.harvest(query, terms)`. `search` fills `run.posts`. `drafts()`
    iterates `run.stored`, and only `store_posts()` fills that - and
    `store_posts` is called only from `harvest`. So `drafts()` returned `[]`
    on a run holding 20 parsed posts, and `write_documents` faithfully
    inserted nothing. **More pages of that is still nothing**, which is why
    pagination had to wait for this line rather than ship beside it.

    WHY THE SIEVE IS RUN HERE RATHER THAN PASSED TO `harvest`
    ---------------------------------------------------------
    `harvest(query, terms)` takes ONE rendered term set. A post is relevant if
    it matches ANY capability query under ANY of this model surfaces, which is
    24 entries x the clubbed surfaces - so the loop is here and `store_posts`
    is called with what survives. This is the same shape
    `scripts/measure_signal_demotion_x.py` measured on 2026-09-14, so what
    ships is what was measured rather than a second implementation of it.

    WHAT TO EXPECT, WITH ITS POPULATION (rule 7). That measurement read **127
    posts captured by the two 2026-09-11 retrieval probes for five seeded
    Fable 5.1 surfaces** - not a sample of X, and no rate from it is an X
    retrieval rate. Of those, 72 named a seeded surface and **6 pass the sieve
    now that signal is a weight, against 0 under the old gate**: 8.3% of the
    72, 4.7% of the 127. So a three-page harvest of ~60 posts should append
    single digits, and appending 2 is not evidence of a broken sieve.

    THE DROPS ARE COUNTED AND NAMED ON THE STAGE LINE, never silent. A post
    dropped here is a document the board will never see, and a run that cannot
    say how many were dropped cannot tell a tight sieve from an empty search
    (rule 4).
    """
    from collect.adapters.x import club_surfaces, harvester_for_source

    harvester, why = _gated_harvester(
        "x", harvester_for_source,
        client=build_client(timeout=30.0),
        store=RawStore(Path(settings().raw_store_path)),
        # THREE PAGES, BECAUSE COUNT IS NOT A KNOB HERE. twitter241 ignores the
        # requested count and paginates by cursor, so a page is 20 posts
        # whatever is asked for and depth is the only lever there is. The
        # clubbed-surface measurement has the trade: at a 2-request budget, two
        # clubbed pages returned 40 distinct where the old shape returned 30 -
        # but page 1 is also the cleanest, 85% of its posts carrying a variant
        # literally against 68% over three pages. That dilution is the sieve
        # problem now that the sieve runs, and it is counted on the stage line.
        max_pages=X_PAGES_PER_MODEL,
    )
    if harvester is None:
        prog.stage("E2X", "Harvest · X", "skipped", detail=why)
        return 0

    # `max_queries` is now a SURFACE cap, not a request count: all of them go
    # into one request. Kept under its old name because the call site passes it
    # positionally by keyword and renaming it is a change to a signature two
    # other branches also call; what it bounds is named in the stage detail.
    clubbed = club_surfaces(variants, limit=max_queries)
    if not clubbed.query:
        prog.stage("E2X", "Harvest · X", "skipped",
                   detail="no usable search surface for this model")
        return 0
    detail = (f"one X search clubbing {len(clubbed.used)} surface(s) into "
              f"`{clubbed.query[:80]}`")
    if clubbed.dropped:
        # NAMED, NEVER SILENT. A dropped surface narrows the query, and a
        # narrower query reported as a wider one is a denominator that lies.
        detail += f" — {len(clubbed.dropped)} surface(s) did not fit: {list(clubbed.dropped)[:3]}"
    detail += f" — up to {X_PAGES_PER_MODEL} page(s) of 20"
    prog.stage("E2X", "Harvest · X", "running", queries=1, detail=detail)
    inserted = posts = errors = 0
    survived = pages = 0
    q_remaining = q_limit = None  # latest RapidAPI quota header seen this fetch
    from collect.adapters.queries.sieve import sieve as sieve_post

    entries = [e for e in load_queries().all_entries if not e.direction_from_extraction]
    for variant in [clubbed.query]:
        run = harvester.search(variant)
        errors += int(getattr(run, "http_errors", 0) or 0)
        # THE X ARM SPENDS THE SHARED QUOTA, SO IT MUST ALSO RECORD IT. The
        # adapter has parsed these headers since it was written and nothing read
        # them, so an X-only fetch left the panel showing Reddit's older number
        # as though nothing had been spent.
        if getattr(run, "quota_remaining", None) is not None:
            q_remaining = run.quota_remaining
        if getattr(run, "quota_limit", None) is not None:
            q_limit = run.quota_limit
        posts += len(getattr(run, "posts", []) or [])
        pages += int(getattr(run, "pages_fetched", 0) or 0)
        # THE SIEVE, AND THEN THE STORE. See the docstring: `search` alone left
        # `run.stored` empty, so `drafts()` had nothing to draft and every run
        # in the log appended zero.
        survivors = []
        for post in run.posts:
            text = post.sieve_text
            if any(sieve_post(entry.terms.substitute(surface), text).passed
                   for surface in clubbed.used for entry in entries):
                survivors.append(post)
        harvester.store_posts(run, survivors)
        survived += len(survivors)
        wrote = harvester.write_documents(conn, run, retrieval_provenance="not_recorded")
        conn.commit()
        inserted += int(getattr(wrote, "inserted", 0) or 0)
    _write_rapidapi_quota(q_remaining, q_limit, prog.run_id, read_on="x")
    # THE DENOMINATOR IS IN THE SENTENCE. "0 appended" out of 60 retrieved and
    # "0 appended" out of 0 retrieved are different failures, and they used to
    # render identically.
    dropped = posts - survived
    detail = (f"{posts} post(s) seen over {pages} page(s); sieve kept {survived}, "
              f"dropped {dropped}; {inserted} document(s) appended")
    if survived and not inserted:
        detail += " — every survivor was already stored (append-only)"
    if errors:
        # THE ONE THE LOG GOT WRONG. `_get` catches every `httpx.HTTPError`,
        # DNS failures included, and returns None - so two searches that never
        # reached the gateway rendered as `ok · 0 post(s) seen`, directly under
        # the Reddit arm reporting the identical failure as an error.
        detail += f" — {errors} request(s) failed before returning anything"
    prog.stage("E2X", "Harvest · X", _harvest_verdict(errors, posts),
               posts=posts, pages=pages, sieve_kept=survived, sieve_dropped=dropped,
               documents_inserted=inserted, http_errors=errors,
               quota_remaining=q_remaining, quota_limit=q_limit,
               detail=detail)
    return inserted


#: The platforms that share one harvest shape: gate through
#: `harvester_for_source`, run `harvest(query, terms)` end to end, then
#: `write_documents`. Kept as data because the loop below is identical for each,
#: and three copies of one loop is three places to apply the next change twice.
#:
#: `stage` ids are distinct so the fetch log reads as a list of sources rather
#: than one repeated line, and `cap` is per-platform because their costs differ:
#: a Hugging Face harvest walks repos then discussions then comments, so it is
#: bounded hardest.
UNIFORM_PLATFORMS = (
    ("devto",       "E2D", "Harvest · dev.to",       2),
    ("hackernews",  "E2H", "Harvest · Hacker News",  2),
    ("huggingface", "E2F", "Harvest · Hugging Face", 1),
)


def _harvester_factory(platform_id: str):
    """The adapter's own gate-and-build entry point, imported lazily.

    Lazy because importing every adapter costs a fetch that skips them nothing,
    and because an adapter that fails to import must not take the whole run down
    with it - it is one source, and the others are still readable.
    """
    if platform_id == "devto":
        from collect.adapters.devto import harvester_for_source
    elif platform_id == "hackernews":
        from collect.adapters.hackernews import harvester_for_source
    elif platform_id == "huggingface":
        from collect.adapters.huggingface import harvester_for_source
    else:
        raise ValueError(f"no uniform factory for {platform_id!r}")
    return harvester_for_source


def harvest_uniform(conn, prog: Progress, variants: list[str], *,
                    platform_id: str, stage_id: str, stage_name: str,
                    max_queries: int) -> int:
    """E2 harvest for one of the uniform platforms, appended to `document`.

    The terms gate is the ADAPTER'S, never this script's. Each ruling names its
    own live preconditions and only the adapter observes them; a guessed
    observation passed from here would be an observation nobody made wearing the
    costume of one that passed, which is what the check exists to refuse.

    A platform missing from `contract/sources.yaml` is UNASSESSED rather than
    refused, and says so - those are different states and must not render alike
    (rule 6).
    """
    harvester, why = _gated_harvester(
        platform_id, _harvester_factory(platform_id),
        client=build_client(timeout=30.0),
        store=RawStore(Path(settings().raw_store_path)),
    )
    if harvester is None:
        prog.stage(stage_id, stage_name, "skipped", detail=why)
        return 0

    queries = variants[:max_queries]
    prog.stage(stage_id, stage_name, "running", queries=len(queries),
               detail=f"{platform_id} search for {len(queries)} name variant(s)")
    inserted = errors = items = 0
    for variant in queries:
        run = harvester.harvest(variant)
        errors += int(getattr(run, "http_errors", 0) or 0)
        # `items_fetched` where the adapter has it — what the platform actually
        # returned, which is the figure that separates "asked and empty" from
        # "never got through".
        items += int(getattr(run, "items_fetched", 0) or 0)
        wrote = harvester.write_documents(conn, run, retrieval_provenance="not_recorded")
        conn.commit()
        inserted += int(getattr(wrote, "inserted", 0) or 0)
    detail = f"{inserted} document(s) appended from {len(queries)} query(ies)"
    if errors:
        detail += f" — {errors} request(s) failed"
    # `items or inserted`: all three adapters expose `items_fetched` today, but
    # a fourth that does not must not be reported as failed for a harvest that
    # demonstrably wrote rows.
    prog.stage(stage_id, stage_name, _harvest_verdict(errors, items or inserted),
               documents_inserted=inserted, items_fetched=items, http_errors=errors,
               detail=detail)
    return inserted


def assemble_stage(conn, prog: Progress) -> None:
    """E3 — flatten this fetch's new documents into thread_context rows.

    Runs the collect assemblers over unassembled documents. Documents whose raw
    payload is not in THIS machine's store (anything harvested elsewhere) are
    skipped by the assemblers; the ones this fetch just harvested are local, so
    they are what actually get flattened. Append-only.
    """
    from collect.assemble.issue import assemble_github_documents
    from collect.assemble.platforms import PLATFORMS, assemble_platform_documents
    from collect.assemble.reddit import assemble_reddit_documents

    store = RawStore(Path(settings().raw_store_path))
    prog.stage("E3", "Assemble", "running", detail="flattening new documents into threads")
    notes = []
    # GitHub and Reddit keep their own drivers; the five newer platforms share
    # one. Without this the newer harvests wrote `document` rows that never
    # became a `thread_context`, so extraction never saw them and every stage
    # still reported success — the harvest cost requests and could not reach
    # the board.
    stages = [("github", assemble_github_documents), ("reddit", assemble_reddit_documents)]
    stages += [
        (src, (lambda conn_, *, store, limit=None, _s=src:
               assemble_platform_documents(conn_, source=_s, store=store, limit=limit)))
        for src in PLATFORMS
    ]
    from collect.assemble.ranking import ranking_config

    ran = failed = 0
    selection_blocks: list[tuple[str, list]] = []
    for name, fn in stages:
        try:
            report = fn(conn, store=store, limit=200)
            conn.commit()
            ran += 1
            notes.append(f"{name}: {report.summary()}")
            if getattr(report, "selections", None):
                selection_blocks.append((name, report.selections))
        except Exception as exc:
            # `_safe_rollback`, not `conn.rollback()`: one assembler failing
            # because the connection died must not stop the other six from
            # being TRIED, and a bare rollback on a dead socket raises.
            _safe_rollback(conn)
            failed += 1
            notes.append(f"{name}: FAILED ({str(exc).splitlines()[0][:80]})")

    # SEVEN FAILURES USED TO RENDER AS `ok`. Each assembler's exception became a
    # note and the stage signed off regardless, so a dead connection - which
    # fails all seven - looked the same in the log as a quiet corpus with
    # nothing to flatten. If none of them got through, the stage did not
    # succeed, and it now says so.
    if failed and not ran:
        prog.stage("E3", "Assemble", "error",
                   assemblers_failed=failed,
                   detail="every assembler failed · " + " · ".join(notes))
        return
    # HOW MUCH OF THE CORPUS E4 HAS NEVER JUDGED. Reported here and not used as
    # a filter: assembly gates on `status`, so an unjudged document is still
    # assembled. The number matters anyway, because every survival figure this
    # project quotes is computed over judged rows, and a large unjudged
    # remainder means those figures describe a fraction of the corpus (rule 7 -
    # a figure travels with its denominator).
    unjudged = conn.execute(
        "SELECT count(*) FROM document WHERE triage_verdict IS NULL"
    ).fetchone()[0]
    if unjudged:
        notes.append(f"{unjudged} document(s) still carry no triage verdict")
    prog.stage("E3", "Assemble", "ok", unjudged_documents=unjudged,
               assemblers_ran=ran, assemblers_failed=failed,
               detail=(f"{failed} of {ran + failed} assembler(s) failed · " if failed else "")
                      + " · ".join(notes))
    _say_selections(selection_blocks, ranking_config())


def _say_selections(blocks, config) -> None:
    """WHICH COMMENTS EACH THREAD KEPT, AND WHY - printed in full, not in `detail`.

    The stage's `detail` is truncated for the page, and this block is the only
    place the child ranking is visible at all: the score of every kept child
    split into its four terms, and how the whole thread split by relevance tier.
    A lexical tier that misfires ("flash" in "flash attention") is caught by
    reading these lines, which is why they are printed rather than summarised.
    """
    if not blocks:
        return
    from collect.assemble.ranking import selection_lines

    rel = " ".join(f"{t} {w:+.2f}" for t, w in config.relevance.items())
    _say("  child ranking (E3): score = specificity"
         f" + {config.engagement_weight:g} x log1p(votes)"
         f" + first-hand {config.first_hand_bonus:g} + relevance [{rel}]"
         f" | keep top {config.max_children}")
    for source, selections in blocks:
        _say(f"  {source}: {len(selections)} ranked thread(s)")
        for thread_id, selection in selections:
            for line in selection_lines(thread_id, selection):
                _say(line)


def threads_naming_the_model(conn, store, surfaces) -> tuple[set[str], int]:
    """Unread thread ids whose flattened text literally names one of `surfaces`,
    and how many unread threads were scanned - the denominator for the first.

    WHY A TIMESTAMP COULD NOT ANSWER THIS, MEASURED RATHER THAN ARGUED
    -------------------------------------------------------------------
    Selection first scoped to "documents THIS run fetched" (`fetched_at >= run
    start`), which is right for a model's first fetch and empty for its second.
    Measured on the 2026-09-14 re-fetch of `minimax/minimax-m3`, 40 minutes
    after the first one:

        own harvest 0, backlog 50 of 50

    The model's evidence had been harvested by the PREVIOUS run, so it was
    backlog, and the run would have spent its whole cap on dev.to threads again
    - the exact failure the scope was added to stop, wearing a different hat.
    Documents are append-only with `ON CONFLICT DO NOTHING`, so a re-harvest
    that retrieves the same 16 posts inserts 6 and updates no timestamp on the
    other 10: the rows that ARE this model's evidence are invisible to any
    `fetched_at` test.

    `WriteReport` carries counts and not ids, so "the documents this harvest
    touched" cannot be asked either without changing every adapter's write
    path. That is the durable fix and it is somebody's whole change; this is the
    question those ids would have been a proxy for, asked directly.

    NO MODEL PARTICIPATES, AND IT IS NOT A GATE. A normalised substring test
    over text already on disk, and its result is an ORDERING key - a thread that
    does not name the model sorts after one that does and is still reachable by
    this run and every later one (rule 8).

    WHAT IT COSTS, AND BOTH NUMBERS, BECAUSE ONE OF THEM ALONE MISLEADS. One
    local read per unread candidate, measured 2026-09-14 over 3,965 unread
    threads (3,837 readable here, 128 on another machine):

        cold page cache   23.6s
        warm page cache    1-2s

    Quoting 23.6s alone overstates what a run after the first one pays; quoting
    1-2s alone understates the first. Either way it is a small fraction of a
    50-thread extraction (~28 min expected), paid once per run, and it is why
    the expensive per-candidate work below still runs over a bounded pool
    rather than over everything.

    A surface that is absent from the whole corpus returns an empty set, which
    is a real answer - "nothing stored names this model" - and the caller says
    so rather than silently falling back (rule 4).
    """
    from collect.registry.aliases import normalize
    from judge.store.extractions import PIPELINE_VERSION

    #: 4 characters is the floor the resolver already uses for a surface to be
    #: worth matching. Below it a normalised key reaches inside unrelated words -
    #: the `free` inside "freeze" finding, one layer up.
    keys = {normalize(x) for x in surfaces if x and len(normalize(x)) >= 4}
    if not keys:
        return set(), 0
    rows = conn.execute(
        "SELECT tc.id, tc.flattened_text_ref FROM thread_context tc "
        "WHERE EXISTS (SELECT 1 FROM document d "
        "              WHERE d.id = ANY(tc.member_document_ids) AND d.status = 'kept') "
        "  AND NOT EXISTS (SELECT 1 FROM thread_extraction te "
        "                  WHERE te.thread_context_id = tc.id "
        "                    AND te.pipeline_version = %s "
        "                    AND te.content_fingerprint IS NOT NULL)",
        (PIPELINE_VERSION,),
    ).fetchall()
    naming = set()
    for tc_id, ref in rows:
        try:
            text = store.get_text(ref)
        except Exception:
            continue  # payload not on this machine - not this fetch's to judge
        hay = normalize(text)
        if any(k in hay for k in keys):
            naming.add(tc_id)
    return naming, len(rows)


def build_thread_inputs(conn, seen, *, limit: int, since=None, naming=(),
                        include_backlog: bool = True):
    """ThreadInputs for threads this fetch can actually read — the E5 input.

    This is the composition-root stand-in for the deferred RawTextResolver (#6):
    the store reader lives in collect/, judge/ may not import it, but a script
    outside both lanes may. A thread whose flattened payload is not in the local
    store (harvested elsewhere) raises on read and is skipped — so this naturally
    scopes to the threads this fetch just harvested and assembled.

    `include_backlog=False` keeps only threads that name the model (`naming`) or
    hold a document this run harvested (`since`); the rest of the unread pool
    is left for a later reader, not marked. See `FETCH_BACKLOG`.
    """
    from judge.extract.runner import ThreadInput
    from judge.extract.verify import OffsetMapping
    from judge.store.extractions import PIPELINE_VERSION, ExtractionLedger

    store = RawStore(Path(settings().raw_store_path))
    # ── THE TRIAGE VERDICT HAS TO BITE HERE OR IT IS DECORATIVE ──────────────
    # This query used to read every thread_context regardless of what E4 decided,
    # so a document could be gated as a bot post, a bare link or too short, have
    # its verdict written to `document.status`, and still be handed to the LLM.
    # The gates ran and changed nothing.
    #
    # A thread survives if ANY member survived. Per-MEMBER exclusion - dropping
    # one filtered comment and keeping the thread - is deliberately not done
    # here: the offset_map is built over the whole flattening, so removing a
    # member means rebuilding it, and a stale map silently resolves quotes to the
    # wrong document. That is the same refinement the pre-LLM screen defers, and
    # it must be done in the assembler or not at all.
    rows = conn.execute(
        "SELECT tc.id, tc.flattened_text_ref, tc.offset_map, tc.member_document_ids "
        "FROM thread_context tc "
        "WHERE EXISTS (SELECT 1 FROM document d "
        "              WHERE d.id = ANY(tc.member_document_ids) AND d.status = 'kept') "
        # OVER-FETCH, BECAUSE THE FILTERS RUN AFTER THIS. The oversized-thread
        # ceiling and the payload-readability checks are applied in Python
        # below, so a bare `LIMIT limit` spends its slots on candidates that are
        # then discarded. Measured on the 2026-09-10 run: 25 selected, 19 over
        # the 30,000-char ceiling, 6 reached the model - a cap of 25 delivering
        # 6. Fetching a wider pool and taking the first `limit` USABLE threads
        # makes the cap mean what it says.
        #
        # `ORDER BY assembled_at DESC` is kept and is the other half of that
        # run's story: dev.to assembled 37 minutes before Hacker News, so all
        # 38 of its threads fell outside a 25-row window and none was ever
        # considered. A wider pool reaches them.
        #
        # ── THE EXCLUSION IS IN THE QUERY, AND THAT IS THE WHOLE FIX ─────────
        # `seen` was applied in Python AFTER this LIMIT, so the pool was the
        # newest N by `assembled_at` regardless of what had been read. Measured
        # on the shared database 2026-09-14: 3,904 thread_contexts have a kept
        # member and 50 were read at e5.4, so 3,854 are unread - and a 200-row
        # pool could only ever offer the newest 200 of those. At a cap of 75
        # that drains in three runs and then yields nothing, permanently, while
        # ~3,650 older contexts stay unreachable. No cap fixes it: a pool
        # filtered after its own LIMIT cannot reach past its first page.
        #
        # `NOT EXISTS` against the ledger rather than shipping 3,854 ids as a
        # parameter, and it cannot go stale between two statements.
        #
        # `content_fingerprint IS NOT NULL` is load-bearing and is the ledger's
        # own ruling, not a tidy-up. `already_extracted` returns
        # {id: fingerprint} and `should_skip` treats a NULL as "we do not know,
        # RE-READ" - so excluding those here would be this query overriding the
        # ledger. They stay in the pool and `should_skip` decides them below,
        # against the text, which is the only place the text is in hand.
        "  AND NOT EXISTS (SELECT 1 FROM thread_extraction te "
        "                  WHERE te.thread_context_id = tc.id "
        "                    AND te.pipeline_version = %s "
        "                    AND te.content_fingerprint IS NOT NULL) "
        #
        # ── WHAT ORDERS IT. THE FIRST KEY IS A SCOPE, AND IT IS THE POINT ───
        #
        # THIS WAS MEASURED WRONG ONCE, IN THIS FUNCTION, TODAY. The ordering
        # was changed to "newest kept member document" on the argument that
        # `assembled_at` is a fact about the pipeline's schedule rather than
        # about the evidence. That argument is true and the change was still a
        # regression, because `assembled_at DESC` was doing a SECOND job nobody
        # had written down: the threads this fetch just assembled are the
        # newest-assembled rows, so it front-loaded the run's OWN harvest.
        #
        # Measured on the live pool, 2026-09-14, over the 3,965 unread threads,
        # asking how many of the first 75 hold a document that run harvested:
        #
        #     ORDER BY assembled_at DESC          75 of 75   (100%)
        #     ORDER BY newest member created_at    2 of 75   (3%)
        #
        # dev.to articles carry recent publication dates, so 63 of those 75
        # were dev.to threads from earlier in the week and NONE of the 13 X
        # documents the run had just harvested was reached. A per-model fetch
        # would have spent an hour of LLM calls on other models.
        #
        # So the scope is now EXPLICIT rather than a side effect of a sort key.
        # `own_harvest` is the first ordering key: threads holding a document
        # this run fetched come first, and the rest of the unread pool fills
        # whatever the cap leaves. That keeps both properties - the run reads
        # its own evidence, and the cap is not wasted when the harvest is thin -
        # and neither depends on a timestamp meaning something it does not say.
        #
        # `fetched_at >= since` is the marker because there is no better one:
        # every harvest arm passes `harvest_run_id=None`, so no id links a
        # document to the run that fetched it. Worth fixing at the source; not
        # fixed here, because it is a change to every arm's write call.
        #
        # WITHIN each tier, the newest kept member document - a property of what
        # people said rather than of when we flattened it. NOT
        # `document.specificity_score`, though it is computed on every row and
        # nothing reads it: `contract/column_states.yaml` declares it
        # `write_only` with its intended reader named (E3 child ranking,
        # blocked), and `contract/harvest.yaml` forbids this exact use in terms
        # - the composite is "COMPARABLE WITHIN A SOURCE ONLY", measured at
        # github 0.527 against blogs 0.286, so "a cross-channel sort by
        # specificity_score is a sort by `is this GitHub` with extra steps". It
        # would trade an accidental platform bias for a stable one and demote
        # blogs, the only positive-evidence channel. An unread column is not a
        # free one; this is the reader it must not have.
        #
        # `NULLS LAST` is stated rather than relied on - `document.created_at`
        # is non-null on all 9,532 rows today, and if that changes an undated
        # thread goes last instead of silently sorting as old (rule 6).
        #
        # Nothing is EXCLUDED by any of this: with the exclusion in the query,
        # whatever this run does not reach a later run does, which is what keeps
        # it a weight and not a gate (rule 8).
        # EXISTS, NOT `count(*) > 0`, and the difference is not style. The
        # gated-out query is distinguished from this one by counting, so a
        # `count(*)` in this ORDER BY makes the two indistinguishable to
        # anything matching on the SQL - which is exactly what
        # tests/test_fetch_model.py's `_Conn` does, and it caught this.
        # THE FIRST KEY IS "DOES THIS THREAD NAME THE MODEL WE WERE ASKED
        # ABOUT". See `threads_naming_the_model` for why a timestamp cannot
        # answer that on a re-fetch. The second key keeps this run's own fresh
        # harvest ahead of the rest when both are unnamed - a thread harvested
        # now for this model that happens not to spell a seated surface is
        # still likelier to be its evidence than a week-old dev.to article.
        "ORDER BY (tc.id = ANY(%s)) DESC, "
        "         EXISTS (SELECT 1 FROM document d "
        "                 WHERE d.id = ANY(tc.member_document_ids) "
        "                   AND d.fetched_at >= %s) DESC, "
        "         (SELECT max(d.created_at) FROM document d "
        "          WHERE d.id = ANY(tc.member_document_ids) AND d.status = 'kept') "
        "         DESC NULLS LAST, tc.assembled_at DESC, tc.id "
        "LIMIT %s",
        # 8x the cap, floored at 200 so a small cap still sees a real pool.
        # Bounded rather than unbounded: this reads a payload per candidate, and
        # an unbounded pool would read the whole corpus off disk to fill 25
        # slots. It is an over-fetch of UNREAD rows now, which is what makes it
        # drain rather than re-offer the same page.
        # `since` absent means nothing to scope on - every row scores 0 on the
        # first key and the ordering degrades to the within-tier one, rather
        # than the query refusing or silently scoping to "since the epoch".
        (PIPELINE_VERSION, list(naming) or [""],
         since or datetime.max.replace(tzinfo=UTC),
         max(limit * 8, 200)),
    ).fetchall()
    # What the verdict cost, counted rather than inferred: a thread with no
    # surviving member is one E4 removed, and a run that cannot say how many did
    # not survive cannot tell a strict gate from an empty harvest.
    gated_out = conn.execute(
        "SELECT count(*) FROM thread_context tc "
        "WHERE NOT EXISTS (SELECT 1 FROM document d "
        "                  WHERE d.id = ANY(tc.member_document_ids) AND d.status = 'kept')"
    ).fetchone()[0]

    #: How many of the selected threads hold a document THIS run harvested.
    #: Counted rather than inferred: "75 threads read" is the same sentence
    #: whether they were this model's evidence or the backlog's, and only one
    #: of those is what a per-model fetch was asked for.
    own_ids = {
        r[0] for r in conn.execute(
            "SELECT tc.id FROM thread_context tc "
            "WHERE EXISTS (SELECT 1 FROM document d "
            "              WHERE d.id = ANY(tc.member_document_ids) "
            "                AND d.fetched_at >= %s)",
            (since or datetime.max.replace(tzinfo=UTC),),
        ).fetchall()
    } if since is not None else set()
    inputs = []
    doc_ids: set[str] = set()
    #: Threads skipped for size. Returned rather than counted, so the caller can
    #: name them - "deferred to the nightly batch" is only honest if somebody
    #: can see WHICH threads are waiting.
    oversized: list[str] = []
    naming_set = set(naming)
    for tc_id, flat_ref, omap, members in rows:
        if not include_backlog and tc_id not in naming_set and tc_id not in own_ids:
            # Backlog. Skipped BEFORE the payload read, so a fetch that does
            # not want it does not pay the disk for it either.
            continue
        try:
            flattened = store.get_text(flat_ref)
        except Exception:
            continue  # payload not on this machine — not this fetch's thread
        # THE LEDGER DECIDES, AGAINST THE TEXT. The query excluded the threads
        # read at this version WITH a fingerprint recorded; what reaches here
        # carrying a ledger row has a NULL one, which `should_skip` reads as
        # "we do not know" and re-reads. The old `tc_id in seen` above could
        # not tell that state from a match and skipped it, so a thread whose
        # fingerprint was never recorded was never read again.
        if ExtractionLedger.should_skip(seen, tc_id, flattened):
            continue
        offset_map = tuple(OffsetMapping(**span) for span in (omap or ()))
        # THE DOCUMENT'S PROSE, NOT ITS PAYLOAD, AND THE OFFSET MAP DECIDES THAT.
        #
        # `verify()` step 3 renders `raw_text_of[document_id][raw_start:raw_end]`
        # and that string is what `claim.quote` stores and the board publishes.
        # The offsets come from `thread_context.offset_map`, whose raw side is
        # built by `collect/assemble/flatten.py` against the text the assembler
        # was given - and `collect/assemble/platforms.py` gives it
        # `prose.for_source(source)(payload)`. So the artifact indexed by
        # `raw_start`/`raw_end` is the PROSE, and nothing else.
        #
        # THIS READ `store.get_text(tref)` FROM 2026-08-27 UNTIL 2026-09-14 AND
        # WAS CORRECT WHEN WRITTEN. `document.text_ref` pointed at prose then.
        # The ruling of 2026-08-28 17:55 made it point at the PAYLOAD - "the
        # bytes the platform gave us" - and every writer was corrected while
        # this reader, two stages away, kept the old meaning. The result is a
        # slice of a JSON envelope rendered as somebody's sentence, on a claim
        # whose `quote_verified` is true, because verification checked the
        # MODEL's quote against the flattened prose and step 3 then substituted
        # a different string from a different artifact.
        #
        # It was invisible for the ordinary reason: the payload is LONGER than
        # the prose, so `raw_end > len(raw)` never trips and the slice lands
        # silently in the wrong place. Ten of ten claims on the 2026-09-14 run.
        #
        # A payload that will not yield prose is SKIPPED AND NAMED, not passed
        # through. Falling back to the payload is the defect this comment exists
        # to describe.
        raw_text_of = {}
        unreadable: list[str] = []
        drows = conn.execute(
            "SELECT id, text_ref, source FROM document WHERE id = ANY(%s)",
            (list(members),),
        ).fetchall()
        for did, tref, dsource in drows:
            if not tref:
                continue
            try:
                payload = store.get_text(tref)
            except Exception:  # noqa: BLE001 - payload not on this machine
                continue
            extract_prose = prose.for_source(dsource)
            if extract_prose is None:
                unreadable.append(f"{did}: no prose extractor for source {dsource!r}")
                continue
            try:
                raw_text_of[did] = extract_prose(payload)
            except Exception as exc:  # noqa: BLE001 - NotAPayload and friends
                unreadable.append(f"{did}: {type(exc).__name__}: {str(exc)[:80]}")
        # ── THE ARTIFACT GUARD, AND IT RUNS BEFORE ANY MODEL CALL ────────────
        #
        # Pointing `raw_text_of` at the prose fixes the artifact. It does not
        # PROVE the artifact, and this defect was invisible for exactly that
        # reason: `verify()` step 3 slices `raw[raw_start:raw_end]` and its only
        # check is `raw_end > len(raw)`. The payload is LONGER than the prose it
        # wraps, so every offset fitted and the slice landed silently in the
        # wrong place. Had the wrong artifact been the smaller one this would
        # have failed loudly on the first claim.
        #
        # So the check is on the artifact rather than on the quote: the offset
        # map already records how long each member's text was when the assembler
        # flattened it, and comparing that to what we just loaded costs one
        # subtraction per member. On the row that started this:
        #
        #     offset_map says hackernews:49682189 is   749 chars
        #     prose(payload)                           749   PASS
        #     payload (what this used to load)       1,988   FAIL
        #
        # A MEMBER THAT FAILS IS DROPPED, NOT THE WHOLE THREAD. The other
        # members' offsets are still good, and a quote attributed to a dropped
        # member comes back from `verify()` as RAW_TEXT_MISSING - a named
        # rejection rather than a wrong quote. If that empties `raw_text_of` the
        # existing guard below skips the thread.
        #
        # WHY A TOLERANCE AND NOT EQUALITY, measured over 4,525 documents:
        #
        #     drift +0   3,202 documents
        #     drift +2   1,285 documents   all github - `github_issue_prose`
        #                                  joins title and body with a separator
        #                                  the assembled text did not carry
        #     drift +1       4 documents
        #     large -ve      6 documents   hackernews; the map does not describe
        #                                  this text at all, and these SHOULD be
        #                                  refused
        #
        # So equality would refuse 1,289 good documents. 8 is four times the
        # largest benign drift and two orders of magnitude below the smallest
        # real failure (+1,239 on the row above). The github +2 is a real if
        # small inconsistency - prose() today is not byte-identical to what the
        # assembler flattened - and it is named here rather than fixed here.
        for did, text in list(raw_text_of.items()):
            spans = [s.raw_end for s in offset_map if s.document_id == did]
            if not spans:
                continue                      # no segment claims this member
            expected = max(spans)
            drift = len(text) - expected
            if abs(drift) > _MAX_PROSE_DRIFT:
                unreadable.append(
                    f"{did}: offset_map describes {expected} chars, the prose is "
                    f"{len(text)} ({drift:+d}); dropped rather than sliced"
                )
                del raw_text_of[did]
        if unreadable:
            log.warning(
                "thread %s: %d member(s) yielded no usable prose, so their quotes "
                "could not be rendered: %s",
                tc_id, len(unreadable), "; ".join(unreadable[:3]),
            )
        if not raw_text_of:
            continue  # step 3 renders the raw span; without it, unrenderable
        # THE OVERSIZED CEILING, APPLIED HERE rather than in the caller. It used
        # to run after selection, so an oversized thread consumed one of the
        # cap's slots and was then dropped - 19 of 25 on the 2026-09-10 run.
        # Skipping them during selection means `limit` counts threads the model
        # will actually read.
        if len(flattened) > MAX_FETCH_THREAD_CHARS:
            oversized.append(tc_id)
            continue
        inputs.append(ThreadInput(
            thread_context_id=tc_id, flattened_text=flattened,
            offset_map=offset_map, raw_text_of=raw_text_of,
        ))
        doc_ids.update(members)
        if len(inputs) >= limit:
            break
    named = sum(1 for t in inputs if t.thread_context_id in naming_set)
    from_own_harvest = sum(
        1 for t in inputs
        if t.thread_context_id in own_ids and t.thread_context_id not in naming_set
    )
    return inputs, doc_ids, gated_out, oversized, (named, from_own_harvest)


def _thread_latest_dates(conn, thread_ids: list[str]) -> dict:
    """thread_context_id -> the newest document date in it. For the release gate."""
    if not thread_ids:
        return {}
    rows = conn.execute(
        "SELECT tc.id, max(d.created_at) "
        "FROM thread_context tc JOIN document d ON d.id = ANY(tc.member_document_ids) "
        "WHERE tc.id = ANY(%s) GROUP BY tc.id",
        (thread_ids,),
    ).fetchall()
    return {tc_id: latest for tc_id, latest in rows}


def dedupe_stage(conn, prog: Progress) -> None:
    """E3d — cluster near-duplicates, so a syndicated copy stops being a voice.

    WIRED 2026-09-11. `collect/assemble/dedupe.py` and `signature.py` were both
    complete and neither had a caller: `collect/ops/chain.py` declared
    `Stage("assemble-dedupe", run=None)` and the four columns were populated on
    0 of 7,479 documents. `judge/vet/reject.py:check` already TOOK
    `dedup_cluster_id` and `is_canonical_in_cluster` and defaulted to
    "canonical", so every syndicated copy counted as an independent voice - the
    condition the publication gate exists to test, inverted.

    AFTER ASSEMBLE, NOT BEFORE. Clustering signs PROSE, and prose comes from the
    same extractors the assembler uses; running it first would sign whatever the
    adapter stored, which on 2026-09-10 was a JSON envelope every document of a
    platform shares.

    NEVER FATAL. A clustering failure must not lose an assembled corpus: the
    documents are stored, the threads are built, and a missing grouping costs
    precision on voice counts rather than the run.
    """
    from collect.assemble.dedupe_write import run as run_dedupe

    store = RawStore(Path(settings().raw_store_path))
    prog.stage("E3d", "Dedupe · count people, not posts", "running",
               detail="clustering near-duplicates so a syndicated copy is reach, not weight")
    try:
        reports = run_dedupe(conn, store=store, sources=DEDUPE_SOURCES, limit=500)
        conn.commit()
    except Exception as exc:
        _safe_rollback(conn)
        prog.stage("E3d", "Dedupe · count people, not posts", "error",
                   detail=str(exc).splitlines()[0][:200])
        return

    clusters = sum(r.clusters_written for r in reports)
    amps = sum(r.amplifications for r in reports)
    signed = sum(r.signed for r in reports)
    unreadable = sum(r.unreadable for r in reports)
    refused = sum(r.refused for r in reports)
    # A ZERO HERE IS A FINDING, NOT A FAILURE. Most comments are below the
    # measured 200-token floor, so no signature is computed for them at all -
    # `signature.py` found neither method separates duplicates from strangers
    # below it. Saying "0 clusters" beside "how many could even be compared" is
    # the difference between "nothing was duplicated" and "nothing was checked".
    prog.stage("E3d", "Dedupe · count people, not posts", "ok",
               clusters=clusters, amplifications=amps, signed=signed,
               unreadable=unreadable, refused=refused,
               detail=(f"{clusters} cluster(s), {amps} amplification(s) from "
                       f"{signed} signable document(s); {unreadable} payload(s) not on "
                       f"this machine, {refused} unsignable"))


def score_stage(conn, prog: Progress) -> None:
    """E3b — the six document signals, without which weighting refuses.

    `collect/adapters/documents.py` writes NULL into `has_numbers`,
    `has_error_strings`, `has_code`, `has_conditions`, `names_version` and
    `specificity_score` on purpose: `score_document` needs the version-alias
    population, and building it in five adapters is five chances to diverge.
    The columns are filled here instead, once, from one registry read.

    NOT OPTIONAL, AND THE FIRST REAL RUN PROVED IT. Without this stage
    `document.has_conditions` stays NULL, `_document_facts` reads NULL, and
    `weight.compute()` refuses - "a weighting input may not have a silent
    default". That refusal is correct: an absent condition is not a stated
    absence, and defaulting it to False would price every unscored document as
    though somebody had checked and found nothing.

    BETWEEN ASSEMBLE AND TRIAGE, forced from both sides. Scoring reads the prose
    a payload yields, so flatten must already have proven the payload readable.
    And triage's `has_artifact` gate reads `has_error_strings` and `has_code`,
    two of the six columns written here - gating before scoring would gate on
    NULLs and drop documents for lacking a signal nobody had computed.
    """
    from collect.triage.store import score_unscored

    store = RawStore(Path(settings().raw_store_path))
    prog.stage("E3b", "Score · document signals", "running",
               detail="filling the six signal columns weighting and triage read")
    run = score_unscored(conn, store, dry_run=False)
    conn.commit()

    # The real ScoreRun fields: eligible, scored, written, unreadable,
    # unreadable_by_source, true_counts.
    parts = [f"{run.scored} of {run.eligible} scored", f"{run.written} written"]
    # COULD-NOT-READ IS NOT SCORED-AS-ABSENT. A payload this host cannot read
    # was never scored, so its six columns stay NULL and weighting will refuse
    # its claims later. Naming it here beats letting it surface three stages on
    # as an unexplained refusal - and it is per-source, because a whole platform
    # being unreadable is a different problem from a few missing payloads.
    if run.unreadable:
        by = ", ".join(f"{k} {v}" for k, v in sorted(run.unreadable_by_source.items()))
        parts.append(f"{run.unreadable} unreadable ({by})" if by
                     else f"{run.unreadable} unreadable")
    # WHICH signals came back true, which is the only way to see a scorer that
    # ran and found nothing versus one that never ran.
    if run.true_counts:
        parts.append("true: " + ", ".join(
            f"{k} {v}" for k, v in sorted(run.true_counts.items())))
    prog.stage("E3b", "Score · document signals", "ok",
               eligible=run.eligible, scored=run.scored, written=run.written,
               unreadable=run.unreadable, true_counts=dict(run.true_counts),
               detail="; ".join(parts))


def triage_stage(conn, prog: Progress) -> None:
    """E4 — the hard gates, over every platform this fetch harvested.

    THIS USED TO BE A NO-OP AND THAT WAS THE EXPENSIVE KIND. Every document went
    to the extractor whatever it was: a bot post, a bare link with no commentary,
    a forty-character "same here", a thread written before the model existed. The
    gates were built and tested and simply never asked, so nothing failed - the
    LLM read junk, and junk that survives extraction reaches the board carrying a
    verified quote, which is exactly the shape nobody catches downstream.

    All eight platforms are gated, not the original three: `_prose_by_source()`
    maps arXiv, dev.to, Hacker News, Hugging Face and X to their own prose
    extractors. That matters more than it looks - the alternative to a real
    extractor is flattening a raw payload, and a payload flattened verbatim lets
    a quote verify against a JSON FIELD VALUE while `quote_verified` says true.

    `dry_run=False`, said explicitly. The default is True because triage writes a
    verdict over thousands of rows on a shared database and the convention is
    that a caller wanting the write asks for it. A per-model fetch is scoped and
    user-initiated, so it asks.

    A GATE THAT COULD NOT RUN IS REPORTED AS UNAVAILABLE, never as a pass.
    `wrong_language` has no detector installed and `known_bot` needs a curated
    list; both come back UNAVAILABLE rather than silently counting as clean, and
    the stage line says which, because "no bots found" and "we cannot look for
    bots" are different facts about the corpus.
    """
    from collect.triage.run import gate_availability, triage_stored

    store = RawStore(Path(settings().raw_store_path))
    prog.stage("E4", "Triage", "running",
               detail="running the hard gates over every unjudged document")
    run = triage_stored(conn, store, dry_run=False)
    conn.commit()

    # The REAL fields off TriageStoreRun, and the denominators with them. A
    # triage that reports "412 dropped" without saying by which gate is a number
    # nobody can act on, and the usual cause of a sudden drop is a broken parser
    # rather than a quiet corpus.
    detail = f"{run.triaged} of {run.eligible} judged; {run.kept} kept, {run.dropped} dropped"
    if run.by_reason:
        detail += " - " + ", ".join(f"{n} {g}" for g, n in sorted(run.by_reason.items()))
    # COULD-NOT-READ IS NOT COULD-NOT-PASS. A payload that did not resolve, or
    # that its extractor refused as not-prose, was never gated at all - counting
    # those as clean would be the silent-absence failure one stage earlier.
    unread = run.unreadable + run.not_prose + run.unmapped_source
    if unread:
        detail += (f" | {unread} never gated ({run.unreadable} unreadable, "
                   f"{run.not_prose} not prose, {run.unmapped_source} unmapped source)")
    # A GATE THAT COULD NOT RUN REPORTS UNAVAILABLE, NEVER A PASS. `wrong_language`
    # has no detector installed and `known_bot` needs a curated list; "no bots
    # found" and "we cannot look for bots" are different facts about the corpus.
    if run.never_ran:
        detail += " | unavailable: " + ", ".join(sorted(run.never_ran))
    # PER SOURCE, in the detail line and not only in an object field the panel
    # cannot render. This is the number that says whether the gates are tuned for
    # a platform or merely running on it: `too_short` was calibrated on Reddit
    # comments, and an arXiv abstract or a Hugging Face model card is a different
    # shape entirely. A single corpus-wide "5888 dropped" hides which source paid.
    if run.by_source:
        per = []
        for src in sorted(run.by_source):
            counts = run.by_source[src] or {}
            kept, triaged = counts.get("kept", 0), counts.get("triaged", 0)
            # kept / TRIAGED, which is the survival rate the triage module itself
            # reports. kept/(kept+dropped) would silently exclude the rows that
            # were never gated at all, and those are the ones worth seeing on a
            # platform whose prose extractor is new.
            per.append(f"{src} {kept}/{triaged}" if triaged else f"{src} none gated")
        detail += " | survived by source: " + ", ".join(per)
    prog.stage("E4", "Triage", "ok", eligible=run.eligible, triaged=run.triaged,
               kept=run.kept, dropped=run.dropped, written=run.written,
               by_reason=dict(run.by_reason), by_source=dict(run.by_source),
               never_ran=dict(run.never_ran), not_prose=run.not_prose,
               unreadable=run.unreadable, availability=gate_availability(run),
               detail=detail)


def _subject_ids(conn, given: str) -> frozenset[str]:
    """Every id shape that means "the model this run is for".

    The CLI is invoked with either form - `model_page` accepts both and
    the UI passes the canonical id - and `board_entry.model_version_id`
    stores both. Returning the pair is what lets `model_scope` be
    correct regardless of which route an entry arrived by. A lookup
    that finds nothing yields just what was given: labelling on one
    known form beats refusing to label at all.
    """
    ids = {given}
    row = conn.execute(
        "SELECT id, canonical_id FROM model_version WHERE id = %s OR canonical_id = %s",
        (given, given),
    ).fetchone()
    if row:
        ids.update(x for x in row if x)
    return frozenset(ids)


def extract_and_curate(conn, prog: Progress, *, release_date=None,
                       surfaces=()) -> None:
    """E5–E7 — extract claims from this fetch's threads, vet, and curate cells.

    Spends (capped) OpenRouter money and writes claims + cells. Scoped to the
    threads this fetch produced (build_thread_inputs skips anything not local).
    The surface resolver is wired here — the composition root's job — so a
    claim's SURFACE ("fable 5.1") maps to a model_version. Curation is the
    pipeline's own step; it runs inside one transaction, so it is atomic.

    `release_date` is the fetched model's release date. On a model-name harvest
    the model IS known, so the release gate (reject.py rule 5) runs here rather
    than in the generic text screen: a thread whose newest document predates the
    model cannot be about it — a coincidental name match or a fabrication.
    """
    from collect.surface_resolver import RegistrySurfaceResolver
    from judge import spend_ledger
    from judge.cli import _document_facts, _model_version_map
    from judge.config import capabilities
    from judge.curate.labels import Driver
    from judge.extract.budget import Budget
    from judge.extract.client import OpenRouterClient
    from judge.pipeline import Pipeline
    from judge.store.extractions import ExtractionLedger

    ledger = ExtractionLedger(conn)
    seen = ledger.already_extracted()
    store = RawStore(Path(settings().raw_store_path))
    prog.stage("E5", "Extract", "running",
               detail="scanning unread threads for this model's surfaces "
                      "(local reads, no network)")
    naming, unread_total = threads_naming_the_model(conn, store, surfaces)
    threads, doc_ids, gated_out, oversized, (named, own) = build_thread_inputs(
        conn, seen, limit=MAX_FETCH_THREADS, since=prog.started_at, naming=naming,
        include_backlog=FETCH_BACKLOG)
    # SAID, NOT IMPLIED. A run that reads 50 threads of which 2 name the model
    # whose page was clicked has done almost nothing for it, and "50 thread(s)
    # to read" is the same sentence either way. Three tiers because they are
    # three different claims: this model's evidence, this run's fresh harvest,
    # and the backlog the cap had room for.
    backlog = len(threads) - named - own
    # ⚠ THE CAP IS REPORTED, AND SO IS WHETHER IT BOUND. The progress line below
    # this one reads `reading thread N/25`, and until now 25 could mean either
    # "the cap stopped us" or "that is all there was" — two different facts about
    # the world, rendered identically. Somebody who raises FETCH_MAX_THREADS and
    # still sees /25 has no way to tell whether the variable failed to arrive or
    # the corpus simply held 25 threads.
    #
    # `len(threads) == cap` is the discriminator: selection takes the first
    # `limit` rows, so landing exactly on it means there was more to read.
    # Rule 4 — a caused absence must say it was caused.
    cap_bound = len(threads) >= MAX_FETCH_THREADS
    prog.stage("E5", "Extract", "running",
               threads_naming_the_model=named, threads_from_own_harvest=own,
               threads_from_backlog=backlog, unread_naming_the_model=len(naming),
               thread_cap=MAX_FETCH_THREADS, cap_reached=cap_bound,
               detail=f"{len(threads)} thread(s) selected — {named} name this model "
                      f"(of {len(naming)} unread that do), {own} from this run's own "
                      f"harvest, {backlog} from the backlog. "
                      + (f"THE CAP OF {MAX_FETCH_THREADS} STOPPED THIS — there is more "
                         f"to read, and clicking Fetch again continues from here "
                         f"(FETCH_MAX_THREADS raises it)."
                         if cap_bound else
                         f"The cap of {MAX_FETCH_THREADS} did not bind: this is every "
                         + ("thread there was to read." if FETCH_BACKLOG else
                            "unread thread for this model and this run's harvest.")))
    if not FETCH_BACKLOG:
        # SAID, because a 2-thread run must not read as a model with 2 threads
        # of evidence in the world when it is a run that chose not to read the
        # rest (rule 4). The denominator is the unread pool the scan covered.
        prog.stage("E5", "Extract", "running",
                   backlog_read=False, unread_threads=unread_total,
                   detail=f"backlog NOT read by this fetch: of {unread_total:,} unread "
                          f"thread(s) scanned, {len(naming)} name this model; the "
                          f"others are left unread for the nightly batch "
                          f"(FETCH_BACKLOG=on reads them here)")
    if not naming:
        # Rule 4: an empty scan is a finding, not a fallback to be silent about.
        prog.stage("E5", "Extract", "running",
                   detail="no unread thread anywhere in the corpus names this "
                          "model's seated surfaces — "
                          + ("everything below is backlog" if FETCH_BACKLOG else
                             "only this run's own harvest can be read"))
    if gated_out:
        # Said, not implied. A smaller corpus reaching the LLM because the gates
        # worked reads identically to a smaller corpus because the harvest was
        # thin, and only one of those is good news.
        prog.stage("E4b", "Vet · pre-LLM (same rules, thread level)", "running",
                   threads_gated_out=gated_out,
                   detail=f"{gated_out} thread(s) held back by E4 - no member survived "
                          "the hard gates, so they never reach the model")

    # The size ceiling now runs INSIDE selection (see build_thread_inputs), so
    # `threads` already excludes oversized ones and `MAX_FETCH_THREADS` counts
    # threads the model will actually read. Filtering here as well was what made
    # a cap of 25 deliver 6.
    if oversized:
        prog.stage("E5", "Extract", "running",
                   detail=f"{len(oversized)} oversized thread(s) deferred to the nightly "
                          f"batch (> {MAX_FETCH_THREAD_CHARS:,} chars, too slow on demand)")

    # PRE-LLM HARD GATES. The model reads only what survives them, so a
    # promotional/placeholder/too-short thread never costs a token. Reuses the
    # vet rules (judge/screen.py) on text the fetch already has - the funnel's
    # "gates before the LLM". Coarse by design: a thread drops if its flattened
    # text triggers a rule; per-DOCUMENT granularity (drop one comment, keep the
    # thread) would need to rewrite the assembled offset_map and is a later
    # refinement. Every drop is named on the stage line, not silent.
    from collections import Counter

    from judge.screen import screen as pre_llm_screen

    verdicts = [(t, pre_llm_screen(text=t.flattened_text)) for t in threads]
    dropped = [(t.thread_context_id, v.trigger) for t, v in verdicts if v.dropped]
    threads = [t for t, v in verdicts if not v.dropped]

    # RELEASE-DATE GATE (reject.py rule 5), here because the model is known: a
    # thread whose newest document predates the model's release cannot be about
    # it. Compared against the newest document so a thread that CONTINUED after
    # release is kept; only wholly-pre-release threads drop. Skipped when the
    # model has no release date on record (rule 6: absent is not "predates").
    if release_date is not None and threads:
        latest = _thread_latest_dates(conn, [t.thread_context_id for t in threads])
        predates = []
        kept = []
        for t in threads:
            newest = latest.get(t.thread_context_id)
            if newest is not None and newest.date() < release_date:
                predates.append(t.thread_context_id)
            else:
                kept.append(t)
        threads = kept
        dropped.extend((tc, "predates_model") for tc in predates)

    if dropped:
        by_trigger = Counter(trig for _, trig in dropped)
        summary = ", ".join(f"{n} {trig}" for trig, n in by_trigger.most_common())
        prog.stage("E4b", "Vet · pre-LLM (same rules, thread level)", "ok", dropped=len(dropped),
                   by_trigger=dict(by_trigger),
                   detail=f"{len(dropped)} thread(s) dropped before the LLM ({summary}); "
                          f"{len(threads)} pass to extract")
    else:
        prog.stage("E4b", "Vet · pre-LLM (same rules, thread level)", "ok",
                   detail=f"all {len(threads)} thread(s) passed the pre-LLM screen")

    prog.stage("E5", "Extract", "running",
               detail=f"{len(threads)} new thread(s) to read (LLM; capped spend)")
    if not threads:
        prog.stage("E5", "Extract", "skipped",
                   detail="no new readable threads to read now — "
                          "nothing local, or all deferred as oversized")
        from judge.legacy import legacy_cells_enabled
        stages = [("E6", "Vet")] + ([("E7", "Curate")] if legacy_cells_enabled() else [])
        for id_, name in stages:
            prog.stage(id_, name, "skipped", detail="no claims to curate")
        return

    budget = Budget.from_env()
    if budget is not None:
        budget.spent_usd = spend_ledger.spent_today()
    facts, _ = _document_facts(conn, doc_ids)
    mvo = _model_version_map(conn)
    resolver = RegistrySurfaceResolver.from_connection(conn)

    # Per-thread progress, so a slow E5 shows movement instead of looking hung -
    # the whole reason E6/E7 seemed never to arrive was E5 running in silence.
    total = len(threads)
    counter = {"n": 0}

    extractor_model = os.getenv("EXTRACTOR_MODEL", "deepseek/deepseek-v4-flash")
    prog.llm["model"] = extractor_model

    # WHAT IS ABOUT TO BE SENT, COUNTED IN POSTS AND NOT ONLY IN THREADS.
    #
    # A thread is what the model reads; a POST is what somebody wrote, and the
    # two differ by an order of magnitude. "8 threads" and "8 threads holding 47
    # posts" are different statements about how much evidence this call is worth,
    # and only the second one can be compared with the harvest lines above it.
    # `raw_text_of` is document id -> text, so its length IS the post count.
    posts_of = {t.thread_context_id: len(t.raw_text_of) for t in threads}
    # WHAT THE THREAD IS ABOUT, NOT ONLY WHICH ROW IT IS. A line reading
    # `thread_context_3845c1e30b51815d  3 post(s)` identifies the row and tells a
    # reader nothing about what was just paid for - and the id is the ONE thing
    # about a thread they cannot look up without a database.
    #
    # The title is the flattened text's first line by construction: `prose.py`
    # builds every document as `title + TITLE_SEPARATOR + body`, so the first
    # line IS the root post's title on every platform. Derived rather than
    # queried - E5 must not open a connection to write a log line.
    titles_of = {t.thread_context_id: _title_of(t) for t in threads}
    # `hackernews:49746163` -> `hackernews`. Which platform a thread came from
    # is the other thing the id hides, and it is already in the document keys.
    sources_of = {
        t.thread_context_id: (next(iter(t.raw_text_of), "") or "").split(":")[0] or "?"
        for t in threads
    }
    chars_of = {t.thread_context_id: len(t.flattened_text) for t in threads}
    #: Only populated when FETCH_LOG_TEXT is on - holding every thread's full
    #: text for a run that will not print it is megabytes kept for nothing.
    text_of = {t.thread_context_id: t.flattened_text for t in threads} if LOG_SENT_TEXT else {}
    _rule()
    _say(f"  LLM     {extractor_model}")
    _say(f"  sending {_n(total)} thread(s) - {_n(sum(posts_of.values()))} post(s), "
         f"{_n(sum(len(t.flattened_text) for t in threads))} chars")
    _say("          one call per thread; tokens and cost are printed per call below")
    _rule()

    def _on_thread(tc_id: str) -> None:
        counter["n"] += 1
        # `_console=False`: the terminal gets the richer line below instead, with
        # the post count on it. The RECORD is unchanged and the fetch panel still
        # shows this exactly as before.
        prog.stage("E5", "Extract", "running", _console=False,
                   detail=f"reading thread {counter['n']}/{total} (LLM) — {tc_id}")
        _say("")
        _say(f"  -> [{counter['n']}/{total}] {titles_of.get(tc_id, '?')}")
        _say(f"     sent  {sources_of.get(tc_id, '?')} | "
             f"{_n(posts_of.get(tc_id, 0))} post(s) | "
             f"{_n(chars_of.get(tc_id, 0))} chars | {tc_id}")
        if LOG_SENT_TEXT:
            # EXACTLY WHAT THE MODEL IS SHOWN, fenced the way the request fences
            # it. Printing our own paraphrase of the input would defeat the one
            # reason to turn this on.
            _say("     --- flattened text begins " + "-" * 40)
            for line in (text_of.get(tc_id) or "").splitlines():
                _say("     | " + line)
            _say("     --- flattened text ends " + "-" * 42)

    def _on_result(thread, result) -> None:
        """What came back for one thread. Rendering only - it stores nothing.

        SUMMARY, NOT THE PAYLOAD. The raw tool-call arguments are up to
        `EXTRACT_MAX_OUTPUT_TOKENS` (16,384 today) and one measured draw hit
        65,536, which would bury every other line of the run in a single thread's
        output. What a reader needs from a response is what it CLAIMED, what
        survived quote verification, and what it cost; all three are counts.

        WRAPPED, AND HERE RATHER THAN IN `Pipeline.run_all`. The thread this
        describes is extracted, stored and committed by the time this runs, and
        the call behind it is paid for and cannot be refunded - so an
        `AttributeError` in a format string must not be what ends the run. The
        guard is at this consumer and not around the hook, because a hook that
        raises IS a caller's bug and the pipeline should not quietly absorb one
        on everybody's behalf.
        """
        # THE TOTALS FIRST, AND OUTSIDE THE GUARD. They are what the footer
        # reports, and a thread whose LINE could not be formatted has still been
        # read and still been paid for - dropping it from the spend total
        # because of a rendering fault would under-report the bill, which is the
        # one direction a cost figure must never be wrong in.
        run = result.extraction
        prog.llm["threads"] += 1
        prog.llm["posts"] += len(thread.raw_text_of)
        prog.llm["chars"] += len(thread.flattened_text)
        prog.llm["input_tokens"] += run.input_tokens or 0
        prog.llm["output_tokens"] += run.output_tokens or 0
        prog.llm["cached_input_tokens"] += run.cached_input_tokens or 0
        # Stays None (printed `?`) until some thread's provider reports it.
        if getattr(run, "reasoning_tokens", None) is not None:
            prog.llm["reasoning_tokens"] = (
                (prog.llm.get("reasoning_tokens") or 0) + run.reasoning_tokens
            )
        prog.llm["verified"] += len(run.verified)
        prog.llm["stored"] += len(result.stored_claim_ids)
        prog.llm["board"] = prog.llm.get("board", 0) + (result.board_entries_stored or 0)
        prog.llm["truncated"] += 1 if run.truncated else 0
        try:
            _print_result(result)
        except Exception:  # noqa: BLE001 - see the docstring
            log.warning("could not render the E5 line for %s",
                        getattr(thread, "thread_context_id", "?"), exc_info=True)

    from judge.legacy import legacy_cells_enabled

    legacy_on = legacy_cells_enabled()

    def _entry_line(e) -> str:
        """One board entry as the board will file it: section, heading, slug.

        `Metrics  Time to first token (time-to-first-token) = 300ms [reported]`.
        The heading is the model's `name` - what the page renders - and the slug
        is the grouping key, printed beside it because two headings that share
        a slug land in ONE section and that is the thing worth seeing here.
        """
        label = BOARD_SECTION_LABELS.get(e.section, e.section)
        line = f"{label:<12}  {e.name} ({e.slug})"
        if e.section == "metric":
            line += f" = {e.value_verbatim} {e.unit} [{e.basis}]"
        return line

    def _print_result(result) -> None:
        run = result.extraction
        # VERIFIED AND REJECTED SEPARATELY. `verified` is the claims whose quote
        # was found byte for byte in the text the model was shown (rule 1) and
        # `rejected` is the ones where it was not - a model that proposes ten
        # claims of which two verify has told us something quite different from
        # one that proposes two, and a single "2 claims" line says neither.
        _say(f"     <- {len(run.verified)} verified, {len(run.rejected)} rejected, "
             f"{len(run.unsalvaged)} unsalvaged, {len(run.unclassified)} unclassified"
             + (f", {len(run.proposed_capabilities)} proposed" if legacy_on else ""))
        if run.verified:
            # Tallied by SECTION, in the board's order, zeros included: "no
            # metric" is a finding about this thread, not a line to leave out.
            per_section = Counter(e.section for claim, _q in run.verified
                                  for e in claim.board_entries)
            _say("        " + ", ".join(
                f"{label} x{per_section.get(key, 0)}"
                for key, label in BOARD_SECTION_LABELS.items()))
            # THE QUOTES, WHICH ARE THE ANSWER. A capability tally says the model
            # found three things about `code.generation`; it does not say what
            # anybody actually reported, and that is the only part a person can
            # judge. Rule 1 is that a claim IS its quote - so a log of what came
            # back that omits them logs the filing and not the finding.
            #
            # Every one printed here has already passed verification: the span
            # was found byte for byte in the text above. Truncated for width
            # only, and the cut is marked so a shortened quote is never mistaken
            # for a short one.
            #
            # Then WHERE EACH ONE IS FILED - every board entry the model named
            # for it, one line each, since one quote can land in all three.
            for i, (claim, _q) in enumerate(run.verified, 1):
                quote = " ".join((claim.quote or "").split())
                if len(quote) > CONSOLE_QUOTE_CHARS:
                    quote = quote[:CONSOLE_QUOTE_CHARS - 3] + "..."
                _say(f"        claim {i} [{claim.polarity}]"
                     + (f"  legacy key {claim.capability}"
                        if legacy_on and claim.capability else ""))
                _say(f"          \"{quote}\"")
                for e in claim.board_entries:
                    _say(f"          -> {_entry_line(e)}")
        elif run.no_claim_reason:
            # WHY NOTHING CAME BACK, in the model's own words. An empty thread
            # and a thread the model read and found nothing in are different
            # facts, and this is the line that tells them apart.
            _say(f"        no claim: {run.no_claim_reason[:CONSOLE_WIDTH - 20]}")
        cost = _usd(extractor_model, run.input_tokens or 0, run.output_tokens or 0,
                    run.cached_input_tokens or 0)
        reasoning = getattr(run, "reasoning_tokens", None)
        _say(f"        in {_n(run.input_tokens)} ({_n(run.cached_input_tokens)} cached)"
             f" / out {_n(run.output_tokens)} ({_n(reasoning)} reasoning) tok"
             f"   {cost}"
             + (f"   retries {run.schema_retries}" if run.schema_retries else ""))
        if run.truncated:
            _say("        ! stopped at the token ceiling - this thread was NOT read "
                 "to the end")
            # WHICH KIND OF CEILING HIT. Reasoning counts against `max_tokens`,
            # so a truncation that is mostly reasoning is the model thinking
            # itself out of room, not a long answer - and the fix differs.
            if reasoning and run.output_tokens:
                _say(f"          {reasoning * 100 // run.output_tokens}% of the output "
                     f"was reasoning ({_n(reasoning)} of {_n(run.output_tokens)} tokens)")

    # THE STOP BUTTON REACHES INSIDE A THREAD, WHICH IT DID NOT.
    #
    # `checkpoint()` is called from `stage()`, so during E5 the next check is the
    # progress line for the NEXT thread. A call that hangs never gets there.
    # Measured 2026-09-14: `POST /fetch/stop` returned `stop_requested: true,
    # was_running: true` — both true, the note accurate — and the run carried on
    # for 39 minutes until it was killed by pid. The button reported success and
    # did nothing, in the one situation anybody presses it.
    #
    # The client calls this about once a second while a response is arriving. It
    # does not know what it is calling; `checkpoint` raises `RunStopped`, which
    # unwinds to the same handler that records any other stop.
    extractor = OpenRouterClient.from_env()
    extractor.on_progress = prog.checkpoint

    results = Pipeline(
        conn,
        client=extractor,
        capability_keys=list(capabilities().keys()),
        extractor_model=extractor_model,
        # BOTH ID SHAPES for this run's subject. `board_entry.model_version_id`
        # holds the canonical id when a run names its own model and the
        # internal `mv_` key when the entry came out of a thread, so a single
        # form would mislabel the searched model's own rows as `mentioned`.
        searched_model_version_id=_subject_ids(conn, prog.model_version_id),
    ).run_all(
        threads, facts=facts, model_version_of=mvo, budget=budget,
        already_extracted=seen, driver=Driver("new-evidence"), resolve_surface=resolver,
        on_thread=_on_thread,
        on_result=_on_result,
        # COMMIT EACH THREAD AS IT LANDS. This batch used to commit once, after
        # every thread, so a run that was stopped or died at thread 20 of 24
        # discarded all 19 that had finished — measured E5 durations reach 13.8
        # minutes, and the model calls behind them are already paid for and
        # cannot be refunded. Nothing recorded that either, so the loss was
        # invisible as well as total.
        #
        # The Stop button made this reachable on purpose rather than by
        # accident: it exists so a person can halt a run they can see going
        # wrong, and until now using it threw away everything the run had
        # correctly extracted.
        after_thread=conn.commit,
    )
    # Still needed, and not redundant: the whole-board cell rebuild happens
    # after the loop and belongs to no thread, so it has nothing to ride on.
    conn.commit()

    verified = sum(len(r.extraction.verified) for r in results)
    stored = sum(len(r.stored_claim_ids) for r in results)
    cells = sum(len(r.cells) for r in results)
    # THREADS WE CUT OFF, NAMED ON THE LINE THAT REPORTS THE HARVEST.
    #
    # `max_tokens` bounds a degenerate call, and the price of a bound is that
    # some reads end early. A truncated thread is an absence THIS PIPELINE
    # created, so reporting "N claims verified" without it is rule 4 at the
    # stage line: the run would look like a complete reading of the batch.
    #
    # Counted off `extraction.truncated` rather than off `zero_kind`, because a
    # truncated thread can still have produced claims - and those are the ones
    # that most look like a finished read.
    truncated = [r.extraction.thread_context_id for r in results
                 if r.extraction.truncated]
    board_stored = sum(r.board_entries_stored or 0 for r in results)
    detail = (f"{verified} claim(s) verified, {board_stored} board entr(ies) stored"
              + (f", {stored} legacy claim row(s)" if legacy_on else ""))
    if truncated:
        detail += (
            f"; {len(truncated)} of {len(results)} thread(s) STOPPED AT THE "
            f"TOKEN CEILING and were not read to the end — their claims are "
            f"partial or absent, not a finding about the thread"
        )
    prog.stage("E5", "Extract", "ok", truncated=len(truncated),
               truncated_threads=truncated[:10], detail=detail)

    # CAPABILITY DISCOVERY. Proposals the extractor made for keys none of the 12
    # named — appended to capability_candidate for an admin to rule on. The LLM
    # proposes; a person adopts (a capabilities.yaml PR). Idempotent, so a
    # re-fetch cannot inflate the count.
    from judge.store.capability_candidates import store_proposals
    proposals = [p for r in results for p in r.extraction.proposed_capabilities]

    # WHAT THE BOARD ACTUALLY DISCOVERED, counted by section and reported FIRST.
    #
    # This is the discovery that matters and it had no line in the log. E5b
    # reported `capability_candidate` proposals - the narrow, legacy thing:
    # candidate keys against the ratified twelve, which exist only to feed the
    # cell score. So the log read as though the fetch were discovering
    # capabilities from a list of twelve, when what it was actually doing is
    # naming three OPEN vocabularies from the evidence with no seed list at all.
    from collections import Counter as _Counter

    _sections = _Counter(
        e.section
        for r in results
        for claim, _q in r.extraction.verified
        for e in claim.board_entries
    )
    _slugs = {
        (e.section, e.slug)
        for r in results
        for claim, _q in r.extraction.verified
        for e in claim.board_entries
    }
    _stored_entries = sum(r.board_entries_stored for r in results)
    if _slugs:
        prog.stage(
            "E5c", "Board sections discovered", "ok",
            best_for=_sections.get("best_for", 0),
            capability=_sections.get("capability", 0),
            metric=_sections.get("metric", 0),
            distinct_slugs=len(_slugs),
            rows_stored=_stored_entries,
            detail=(
                f"{len(_slugs)} distinct section(s) named across "
                f"{sum(_sections.values())} entr(ies): "
                f"{_sections.get('best_for', 0)} best-for, "
                f"{_sections.get('capability', 0)} capability, "
                f"{_sections.get('metric', 0)} metric. "
                f"{_stored_entries} row(s) appended to board_entry - discovered "
                f"from the evidence, not chosen from a list. Duplicates are "
                f"merged by a person at /admin/board-entries, never here."
            ),
        )
        # EVERY SECTION NAMED, by category, with how many verified claims were
        # filed under it. Printed in full rather than in `detail`, which is cut
        # at three lines - this list is the answer to "what did the board learn".
        _names: dict[tuple[str, str], str] = {}
        _per_slug = _Counter()
        for r in results:
            for claim, _q in r.extraction.verified:
                for e in claim.board_entries:
                    _names.setdefault((e.section, e.slug), e.name)
                    _per_slug[(e.section, e.slug)] += 1
        for key, label in BOARD_SECTION_LABELS.items():
            rows = sorted(((n, slug) for (sec, slug), n in _per_slug.items() if sec == key),
                          key=lambda t: (-t[0], t[1]))
            _say(f"    {label} ({len(rows)} section(s))")
            if not rows:
                _say("      none named this run")
            for n, slug in rows:
                _say(f"      {n:>3} x  {_names[(key, slug)]} ({slug})")
    else:
        # NOT THE SAME AS "no capabilities proposed", which is what this used to
        # say. Nothing was named on ANY of the three sections.
        prog.stage(
            "E5c", "Board sections discovered", "ok",
            detail=("no section named on any of the three surfaces - the quotes "
                    "that verified described no job, no behaviour and no figure"),
        )
    # The store must never break a fetch. If the migration has not reached this
    # database yet, the proposals are named in the log and dropped for this run
    # rather than crashing extraction on a missing table.
    if not legacy_on:
        # The capability-card stages (E5b proposals, E7 cells) print nothing
        # with the legacy path off: they did not run, and `judge/legacy.py` is
        # where that is said. E6's hard rejection still runs for the board.
        prog.stage("E6", "Vet", "ok",
                   detail="hard rejection ran over every document: promotional, affiliate "
                          "and pre-release claims dropped, and their board entries with "
                          "them")
        return
    table_present = conn.execute(
        "SELECT to_regclass('public.capability_candidate')"
    ).fetchone()[0] is not None
    if proposals and table_present:
        outcome = store_proposals(
            conn, proposals,
            proposer_model=os.getenv("EXTRACTOR_MODEL", "deepseek/deepseek-v4-flash"),
            prompt_label="fetch-extract",
        )
        conn.commit()
        prog.stage("E5b", "Capability keys (legacy cell score)", "ok",
                   proposed=outcome["proposed"], stored=outcome["stored"],
                   unattributed=outcome["unattributed"],
                   detail=f"{outcome['proposed']} proposal(s) against the ratified twelve; "
                          f"{outcome['stored']} new candidate(s) stored for review. "
                          f"SEPARATE from the board's sections above: this feeds the "
                          f"legacy cell score, which is keyed to a closed vocabulary"
                          + (f", {outcome['unattributed']} unattributable"
                             if outcome["unattributed"] else ""))
    elif proposals and not table_present:
        prog.stage("E5b", "Capability keys (legacy cell score)", "skipped",
                   proposed=len(proposals),
                   keys=sorted({p.proposed_key for p in proposals}),
                   detail=f"{len(proposals)} capability proposal(s) NOT stored: the "
                          "capability_candidate table is not on this database yet "
                          "(migration unapplied). Proposed keys: "
                          + ", ".join(sorted({p.proposed_key for p in proposals})[:8]))
    else:
        prog.stage("E5b", "Capability keys (legacy cell score)", "ok",
                   detail="no new key proposed — every claim fitted one of the ratified "
                          "twelve. Says nothing about the board, which discovered its "
                          "sections above without a list")

    prog.stage("E6", "Vet", "ok",
               detail="hard rejection ran over every document: promotional, affiliate and "
                      "pre-release claims dropped, and their board entries with them. The "
                      "WEIGHTING half (tier, n_eff) prices cells only - the board counts "
                      "reports instead of scoring them")
    prog.stage("E7", "Curate", "ok",
               detail=f"{cells} cell(s) computed for the legacy capability cards. The board "
                      f"is NOT curated here: its sections render from board_entry as soon as "
                      f"one report exists, with the count shown and no publication gate")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model_version_id")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--fetch-cap", type=int, default=20,
                        help="max GitHub REST calls this fetch may spend (default 20)")
    args = parser.parse_args(argv)

    run_id = args.run_id or f"{args.model_version_id}-{uuid.uuid4().hex[:8]}"
    # THE BACKEND DOES NOT READ THIS, AND THE COMMENT SAYING SO WAS WRONG.
    #
    # A bare `print(run_id)` stood here under "the backend reads this to know
    # which log to poll". `start_fetch` GENERATES the run id and passes it in
    # with `--run-id`; it never reads a byte of this process's stdout, and
    # nothing else in the repo invokes this script either. The line was a
    # leftover from a design where the child chose the id.
    #
    # It goes rather than moves because `Progress.__init__` has just printed the
    # id in the header - and while it was harmless when both streams went to
    # DEVNULL, it now lands on stdout while the header lands on stderr, so the
    # two interleave and the id appears twice in the wrong order.
    prog = Progress(run_id, args.model_version_id)

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        prog.stage("E1", "Registry", "error", detail="DATABASE_URL not set")
        prog.done("error", "no database configured")
        return 1

    try:
        db = _Db(dsn)  # NO drop, NO disposability wipe — append-only
        conn = db.raw
        row = conn.execute(
            "SELECT canonical_id, display_name, release_date FROM model_version WHERE id = %s",
            (args.model_version_id,),
        ).fetchone()
        if row is None:
            prog.stage("E1", "Registry", "error",
                       detail=f"{args.model_version_id} is not in the registry")
            prog.done("error", "unknown model")
            return 1
        canonical_id, display_name, release_date = row
        variants = _variants_for(conn, args.model_version_id, canonical_id)
        prog.stage("E1", "Registry", "ok",
                   model=display_name or canonical_id, variants=len(variants),
                   detail=f"resolved {display_name or canonical_id} — "
                          f"{len(variants)} search-eligible name variant(s)")
        renamed = name_transcript(run_id, canonical_id)
        if renamed is not None:
            _say(f"  log     {renamed}")
        if not variants:
            prog.stage("E2", "Harvest", "skipped",
                       detail="no search variants for this model — nothing to search for")
            prog.done("ok", "nothing to harvest")
            return 0

        # Each platform in its own guard: a Reddit quota error or a stale terms
        # ruling must not throw away a GitHub harvest that already succeeded.
        try:
            harvest_github(db.live(prog), prog, variants, fetch_cap=args.fetch_cap)
        except Exception as exc:
            prog.stage("E2", "Harvest", "error", detail=str(exc).splitlines()[0][:200])
        try:
            harvest_reddit(db.live(prog), prog, variants, max_searches=3, max_threads=5)
        except Exception as exc:
            prog.stage("E2R", "Harvest · Reddit", "error",
                       detail=str(exc).splitlines()[0][:200])

        try:
            harvest_arxiv(db.live(prog), prog, variants, max_queries=2)
        except Exception as exc:
            prog.stage("E2A", "Harvest · arXiv", "error", detail=str(exc).splitlines()[0][:200])
        try:
            # ALL the surfaces, in ONE request - `max_queries` bounds how many
            # are clubbed, not how many requests are spent. 6 is the adapter's
            # MAX_CLUBBED_SURFACES and covers every alias set in seed_models.
            harvest_x(db.live(prog), prog, variants, max_queries=6)
        except Exception as exc:
            prog.stage("E2X", "Harvest · X", "error", detail=str(exc).splitlines()[0][:200])

        # Blogs have no per-model search — they are RSS/feed-based, harvested
        # wholesale, so a model-name query cannot target them (rule 7: say what
        # the run did NOT do rather than let its absence read as coverage).
        prog.stage("E2B", "Harvest · Blogs", "skipped",
                   detail="blogs are feed-based — no per-model search; not run for one model")

        # dev.to, Hacker News and Hugging Face. Ruled on 2026-09-09, so they run
        # now; each still gates itself, and a ruling that lapses or whose
        # preconditions stop holding turns the arm back into a named skip rather
        # than a silent absence.
        for _pid, _sid, _sname, _cap in UNIFORM_PLATFORMS:
            try:
                harvest_uniform(db.live(prog), prog, variants, platform_id=_pid,
                                stage_id=_sid, stage_name=_sname, max_queries=_cap)
            except Exception as exc:
                prog.stage(_sid, _sname, "error", detail=str(exc).splitlines()[0][:200])

        # ── ASSEMBLE THEN TRIAGE, matching the nightly chain ─────────────────
        # I had these the other way round, reasoning that a stage should only
        # receive what the previous one passed. That is right in general and
        # wrong here, for two reasons the chain states outright.
        #
        # `collect/ops/chain.py` records that triage NEEDS the flatten stage:
        # it reads the prose a payload yields, and flatten is what proves that
        # payload is assemblable. The dependency is about the corpus being
        # coherent rather than about a column.
        #
        # And triage is NOT A GATE. It writes `triage_verdict` as a RECORDED
        # FIELD, because two of its six checks cannot run and its error rate has
        # never been measured - rule 8. So there is nothing for assembly to
        # receive from it, and ordering triage first bought nothing while
        # breaking the dependency.
        # EVERY DB STAGE STARTS ON A PROVEN CONNECTION, and every handler rolls
        # back through `_safe_rollback`. Both halves come from the same run: the
        # socket died during harvest, E3 found out, and its cleanup rollback
        # raised on the dead socket and took E3b, E4 and E5 down with it.
        try:
            assemble_stage(db.live(prog), prog)
        except Exception as exc:
            _safe_rollback(db.raw)
            prog.stage("E3", "Assemble", "error", detail=str(exc).splitlines()[0][:200])

        # E3b BEFORE E4. Triage's `has_artifact` gate reads two of the six
        # columns this writes, so gating first would gate on NULLs.
        try:
            dedupe_stage(db.live(prog), prog)
        except Exception as exc:
            _safe_rollback(db.raw)
            prog.stage("E3d", "Dedupe · count people, not posts", "error",
                       detail=str(exc).splitlines()[0][:200])

        try:
            score_stage(db.live(prog), prog)
        except Exception as exc:
            _safe_rollback(db.raw)
            prog.stage("E3b", "Score · document signals", "error",
                       detail=str(exc).splitlines()[0][:200])

        try:
            triage_stage(db.live(prog), prog)
        except Exception as exc:
            _safe_rollback(db.raw)
            prog.stage("E4", "Triage", "error", detail=str(exc).splitlines()[0][:200])

        try:
            extract_and_curate(db.live(prog), prog, release_date=release_date,
                               surfaces=variants)
        except Exception as exc:
            _safe_rollback(db.raw)
            prog.stage("E5", "Extract", "error", detail=str(exc).splitlines()[0][:200])

        prog.done("ok", "fetch complete")
        return 0
    except RunStopped:
        # A DELIBERATE HALT IS NOT A FAILURE, and the log must not call it one.
        # `stopped` is its own end status so the history reads "stopped" rather
        # than "error", which is the difference between "we chose to abandon
        # this run" and "something broke" - and rule 4 says a caused absence
        # has to say it was caused. Whatever did not run is genuinely absent,
        # not empty.
        prog.stage("STOP", "Stopped by request", "skipped",
                   detail="no further stage was started; rows already written "
                          "are kept, because every write in this pipeline is "
                          "an append")
        prog.done("stopped", "stopped by request")
        return 2
    except Exception as exc:  # a failed stage is a finding, logged, not a silent crash
        prog.stage("?", "fetch", "error", detail=str(exc).splitlines()[0][:200])
        prog.done("error", traceback.format_exc().splitlines()[-1][:200])
        return 1


if __name__ == "__main__":
    sys.exit(main())
