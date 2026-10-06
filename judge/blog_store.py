"""Blog posts in the shared database: pending, approved, or a rejected tombstone.

Migration `20261006T1500_blog_post_store.sql` says why posts moved here from
files, and why rejecting a post deletes its content. In short:

  pending    stored, awaiting review in Admin -> Blogs; never on the Blogs page
  approved   on the Blogs page
  rejected   content deleted; the row stays so the planner never writes the
             same (format, subject) again, and the decision stays in
             `blog_post_review` with its reason

WHO PUTS POSTS HERE. The generator still writes draft FILES on the machine that
runs it (it calls a paid model and is local only). `store_drafts` copies drafts
into this table: automatically for a run started from Admin -> Blogs
(`judge/blog_runs._finish`), and from the "store this machine's drafts" action
for anything else - the drafts that predate this table, or a run started from a
terminal. Storing never overwrites: a slug already here is left as it is.

FAILS CLOSED. Every reader raises `StoreUnreadable` when the table cannot be
read, and the routes turn that into "no posts, and here is why" - never into
"show the files instead". A Blogs page that cannot tell what was approved shows
nothing, rather than everything (CLAUDE.md rule 12; #508 review).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from judge import blog_posts

STATES = ("pending", "approved", "rejected")
DECISIONS = ("approved", "rejected", "reopened")

#: What each decision does to a post in each state. Absent = refused, with the
#: reason in `_REFUSAL`. Rejected has no way out: its content is gone.
_TRANSITIONS = {
    ("pending", "approved"): "approved",
    ("pending", "rejected"): "rejected",
    ("approved", "rejected"): "rejected",
    ("approved", "reopened"): "pending",
}
_REFUSAL = {
    "rejected": "this post was rejected and its content deleted, so there is nothing to move back",
    "pending": "this post is already awaiting review",
    "approved": "this post is already approved",
}


class StoreUnreadable(Exception):
    """The `blog_post` table could not be read. Carries a reader-facing reason."""


class DecisionRefused(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


def _read(conn, sql: str, params: tuple = ()) -> list[tuple]:
    try:
        return conn.execute(sql, params).fetchall()
    except psycopg.errors.UndefinedTable as e:
        raise StoreUnreadable(
            "this database has no blog_post table yet - run the pending migration "
            "(20261006T1500_blog_post_store.sql) with `python -m collect.cli db migrate`"
        ) from e
    except psycopg.Error as e:
        raise StoreUnreadable(f"the blog store could not be read ({type(e).__name__})") from e


def _when(ts: Any) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(ts))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _order(docs: list[dict]) -> list[dict]:
    # The order blog_posts.load() always used: the featured post first, then by title.
    return sorted(docs, key=lambda p: (not p.get("feat"), str(p.get("title", ""))))


# ── storing ─────────────────────────────────────────────────────────────────

def store_drafts(conn, posts: list[dict], run_id: str | None = None) -> dict[str, list]:
    """Store drafts as `pending`. Returns what was stored, what was already
    here (left untouched, whatever its state), and what was refused and why."""
    stored, already, refused = [], [], []
    for doc in posts:
        slug = doc.get("slug") if isinstance(doc, dict) else None
        why = blog_posts._problem(doc)
        if why or not slug:
            refused.append({"slug": slug, "why": why or "no slug"})
            continue
        prov = doc.get("provenance") or {}
        row = conn.execute(
            "INSERT INTO blog_post (slug, state, doc, plan_key, run_id, generated_at, stored_at) "
            "VALUES (%s, 'pending', %s, %s, %s, %s, now()) "
            "ON CONFLICT (slug) DO NOTHING RETURNING slug",
            (slug, Jsonb(doc), prov.get("plan_key"), run_id, _when(prov.get("generated_at"))),
        ).fetchone()
        (stored if row else already).append(slug)
    return {"stored": stored, "already": already, "refused": refused}


# ── reading ─────────────────────────────────────────────────────────────────

def published(conn) -> list[dict]:
    """The approved posts, as the Blogs page renders them."""
    rows = _read(conn, "SELECT doc FROM blog_post WHERE state = 'approved'")
    return _order([r[0] for r in rows])


def for_review(conn) -> list[dict]:
    """Every stored post for Admin -> Blogs and its preview: pending and approved
    with their content and `review` state, rejected as a tombstone with none."""
    rows = _read(
        conn,
        "SELECT p.slug, p.state, p.doc, p.plan_key, p.run_id, p.generated_at, p.stored_at, "
        "       r.reason, r.decided_at "
        "FROM blog_post p "
        "LEFT JOIN LATERAL (SELECT reason, decided_at FROM blog_post_review "
        "                   WHERE slug = p.slug ORDER BY decided_at DESC LIMIT 1) r ON true",
    )
    live, tombstones = [], []
    for slug, state, doc, plan_key, run_id, gen_at, stored_at, reason, decided_at in rows:
        meta = {"review": state, "run_id": run_id, "stored_at": stored_at.isoformat(),
                "review_reason": reason,
                "decided_at": decided_at.isoformat() if decided_at else None}
        if doc is None:
            tombstones.append({"slug": slug, "plan_key": plan_key,
                               "generated_at": gen_at.isoformat() if gen_at else None, **meta})
        else:
            live.append({**doc, **meta})
    return _order(live) + sorted(tombstones, key=lambda t: t["decided_at"] or "", reverse=True)


def stored_slugs(conn) -> set[str]:
    return {r[0] for r in _read(conn, "SELECT slug FROM blog_post")}


def planned_keys(conn) -> set[str]:
    """Every (format, subject) key a stored post was written for - rejected ones
    included, which is why a tombstone keeps its `plan_key`."""
    return {r[0] for r in _read(conn, "SELECT plan_key FROM blog_post WHERE plan_key IS NOT NULL")}


# ── deciding ────────────────────────────────────────────────────────────────

def decide(conn, slug: str, decision: str, reason: str | None) -> dict:
    """Approve, reject or move back one post. The state change and its
    `blog_post_review` row are one transaction (the route's connection).
    Rejecting deletes the content: `doc` becomes NULL."""
    if decision not in DECISIONS:
        raise DecisionRefused(422, f"decision must be one of {list(DECISIONS)}")
    row = _read(conn, "SELECT state, run_id FROM blog_post WHERE slug = %s FOR UPDATE", (slug,))
    if not row:
        raise DecisionRefused(404, "no stored post has this slug; store the draft first")
    state, run_id = row[0]
    new = _TRANSITIONS.get((state, decision))
    if new is None:
        raise DecisionRefused(409, _REFUSAL[state])
    if new == "rejected":
        conn.execute("UPDATE blog_post SET state = 'rejected', doc = NULL WHERE slug = %s", (slug,))
    else:
        conn.execute("UPDATE blog_post SET state = %s WHERE slug = %s", (new, slug))
    rid = f"bpr_{uuid.uuid4().hex[:16]}"
    # STRICTLY AFTER the slug's previous decision (blog_runs.review's reason):
    # two clicks inside one coarse clock tick must not tie.
    conn.execute(
        "INSERT INTO blog_post_review (id, slug, run_id, decision, reason, decided_at) "
        "VALUES (%s, %s, %s, %s, %s, GREATEST(clock_timestamp(), "
        "(SELECT max(decided_at) FROM blog_post_review WHERE slug = %s) "
        "+ interval '1 microsecond'))",
        (rid, slug, run_id, decision, (reason or "").strip() or None, slug),
    )
    return {"id": rid, "slug": slug, "run_id": run_id, "decision": decision, "state": new}
