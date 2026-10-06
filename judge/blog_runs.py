"""Blog generation history and post review, in the shared database.

Admin -> Blogs starts a generation run (`judge/blog_posts.start_generation`,
which runs `generate_sample_blogs.py --plan N` as a subprocess). This module
records each run as a `blog_generation_run` row and each decision about a post
it wrote as a `blog_post_review` row. Migration
`20261006T1200_blog_generation_history.sql` says why both exist.

`judge/blog_posts.py` is not changed: it still reads drafts from files and
runs the generator. This module only RECORDS - it reads that module's status
and log files, and the drafts' own `provenance.generated_at`.

WHICH POSTS A RUN WROTE is read off the drafts, not remembered: a draft whose
`provenance.generated_at` falls inside the run's window belongs to it. So the
answer survives a backend restart mid-run, which an in-memory "before" list
would not.

SCOPE: posts the button writes from now on. Drafts that predate the first
recorded run belong to no run and are not reviewable here.
"""
from __future__ import annotations

import re
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from judge import blog_posts

#: Terminal states a run reports about itself, plus `stalled` from
#: `blog_posts.generation_status` when it stopped reporting.
FINISHED = {"done", "partial", "failed", "stalled"}
DECISIONS = {"approved", "rejected", "reopened"}

_TOKENS = re.compile(r"tokens ([\d,]+) in / ([\d,]+) out")


def mask(text: str) -> str:
    """Anything shaped like a key or a bearer token, masked. The log is the
    generator's own output and is not otherwise vetted for a page."""
    text = re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "sk-***", text)
    return re.sub(r"(?i)(bearer|authorization|api[_-]?key|token)(\s*[:=]\s*)\S+", r"\1\2***", text)


def read_log() -> str | None:
    try:
        return blog_posts.LOG_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _tokens(log: str | None) -> tuple[int | None, int | None]:
    """Summed from the per-post "tokens X in / Y out" lines. None when the log
    has no such line - not reported, never zero."""
    hits = _TOKENS.findall(log or "")
    if not hits:
        return None, None
    return (sum(int(a.replace(",", "")) for a, _ in hits),
            sum(int(b.replace(",", "")) for _, b in hits))


def _parse(ts: Any) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(ts))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _written_between(start: datetime, end: datetime | None) -> list[str]:
    """Slugs of drafts on disk generated inside [start, end]."""
    out = []
    for p in blog_posts.load().get("posts", []):
        at = _parse((p.get("provenance") or {}).get("generated_at"))
        if at and at >= start and (end is None or at <= end):
            out.append(p["slug"])
    return sorted(out)


# ── recording a run ──────────────────────────────────────────────────────────

def record_start(conn, count: int, status: dict) -> str:
    """One row for a run that just started. `started_at` is the status file's
    own, so a later reconcile can match the two exactly."""
    run_id = f"bgr_{uuid.uuid4().hex[:16]}"
    started = _parse(status.get("started_at")) or datetime.now(UTC)
    conn.execute(
        "INSERT INTO blog_generation_run (id, started_at, state, requested_count, "
        "posts_written, posts_failed) VALUES (%s, %s, %s, %s, '{}', '{}')",
        (run_id, started, status.get("state") or "starting", count),
    )
    return run_id


def _finish(conn, run_id: str, started: datetime, status: dict) -> None:
    log = read_log()
    finished = _parse(status.get("finished_at")) or datetime.now(UTC)
    tin, tout = _tokens(log)
    failed = [i.get("key") for i in status.get("items", []) if i.get("state") == "failed"]
    conn.execute(
        "UPDATE blog_generation_run SET finished_at = %s, state = %s, model = %s, "
        "cost_usd = %s, tokens_in = %s, tokens_out = %s, posts_written = %s, "
        "posts_failed = %s, message = %s, log = %s WHERE id = %s",
        (finished, status.get("state"), status.get("model"), status.get("cost_usd"),
         tin, tout, _written_between(started, finished), failed,
         status.get("message"), mask(log) if log is not None else None, run_id),
    )


def reconcile(conn) -> None:
    """Close any open run whose status file now says it finished. Called when
    the status is polled, so a run is recorded even if the watcher thread died
    with a backend restart."""
    status = blog_posts.generation_status()
    if status.get("state") not in FINISHED:
        return
    started = _parse(status.get("started_at"))
    if started is None:
        return
    rows = conn.execute(
        "SELECT id, started_at FROM blog_generation_run WHERE finished_at IS NULL"
    ).fetchall()
    for run_id, row_started in rows:
        if row_started == started:
            _finish(conn, run_id, row_started, status)


def watch(conn_factory, run_id: str) -> None:
    """Wait for the run's process, then record how it ended. A daemon thread:
    if the backend stops first, `reconcile` closes the row on the next poll."""
    proc = blog_posts._proc

    def _wait() -> None:
        if proc is not None:
            proc.wait()
        try:
            with conn_factory() as conn:
                reconcile(conn)
        except Exception:  # noqa: BLE001 - recording must never crash the backend
            pass

    threading.Thread(target=_wait, daemon=True, name=f"blog-run-{run_id}").start()


# ── reading history and reviews ─────────────────────────────────────────────

def runs(conn, limit: int = 20) -> list[dict]:
    rows = conn.execute(
        "SELECT id, started_at, finished_at, state, requested_count, model, cost_usd, "
        "tokens_in, tokens_out, posts_written, posts_failed, message, log "
        "FROM blog_generation_run ORDER BY started_at DESC LIMIT %s",
        (limit,),
    ).fetchall()
    keys = ("id", "started_at", "finished_at", "state", "requested_count", "model", "cost_usd",
            "tokens_in", "tokens_out", "posts_written", "posts_failed", "message", "log")
    out = []
    for r in rows:
        d = dict(zip(keys, r, strict=True))
        for k in ("started_at", "finished_at"):
            d[k] = d[k].isoformat() if d[k] else None
        d["cost_usd"] = float(d["cost_usd"]) if d["cost_usd"] is not None else None
        out.append(d)
    return out


def latest_reviews(conn) -> dict[str, dict]:
    """The current state of every reviewed post: its latest decision."""
    rows = conn.execute(
        "SELECT DISTINCT ON (slug) id, slug, run_id, decision, reason, decided_at "
        "FROM blog_post_review ORDER BY slug, decided_at DESC"
    ).fetchall()
    return {r[1]: {"id": r[0], "run_id": r[2], "decision": r[3], "reason": r[4],
                   "decided_at": r[5].isoformat()} for r in rows}


def reviewable(conn) -> dict[str, str]:
    """slug -> the run that wrote it, for every post a recorded run wrote."""
    rows = conn.execute(
        "SELECT id, posts_written FROM blog_generation_run ORDER BY started_at"
    ).fetchall()
    return {slug: run_id for run_id, slugs in rows for slug in (slugs or [])}


class ReviewRefused(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


def review(conn, slug: str, decision: str, reason: str | None) -> dict:
    if decision not in DECISIONS:
        raise ReviewRefused(422, f"decision must be one of {sorted(DECISIONS)}")
    run_id = reviewable(conn).get(slug)
    if run_id is None:
        raise ReviewRefused(
            404, "only posts written by a recorded generation run can be reviewed here; "
                 "drafts that predate the history belong to no run")
    rid = f"bpr_{uuid.uuid4().hex[:16]}"
    # STRICTLY AFTER the slug's previous decision. Two clicks inside one tick of
    # the clock (coarse on Windows) would otherwise tie, and "the latest
    # decision" would be whichever the index happened to return.
    conn.execute(
        "INSERT INTO blog_post_review (id, slug, run_id, decision, reason, decided_at) "
        "VALUES (%s, %s, %s, %s, %s, GREATEST(clock_timestamp(), "
        "(SELECT max(decided_at) FROM blog_post_review WHERE slug = %s) "
        "+ interval '1 microsecond'))",
        (rid, slug, run_id, decision, (reason or "").strip() or None, slug),
    )
    return {"id": rid, "slug": slug, "run_id": run_id, "decision": decision}


def public_state(conn) -> dict[str, str]:
    """slug -> pending | approved | rejected, for posts a recorded run wrote.
    A post absent from this map predates the history and is left as it was."""
    latest = latest_reviews(conn)
    out = {}
    for slug in reviewable(conn):
        d = (latest.get(slug) or {}).get("decision")
        out[slug] = d if d in ("approved", "rejected") else "pending"
    return out
