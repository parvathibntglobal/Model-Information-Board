"""Readers' discussion posts and replies: checked, stored pending, shown once approved.

THE SHAPE (2026-10-20, Parvathi): the Discussions page lets a reader share
their own experience with an AI model, and reply to what others posted. A post
or reply is checked here, stored `pending` in `discussion_post`, and shown on
the public page only once a person approves it in Admin -> Discussions - the
draft-then-approve shape of the blog and the quiz bank. Nothing typed is lost,
and nothing appears unreviewed.

ORDER: posts newest first by when they were written; each post's replies
oldest first, so a thread reads as a conversation.

NEVER EVIDENCE. Nothing here feeds `claim`, `board_entry` or any count. A
reader's post is shown beside the reports, not added to them.

NOTHING PERSONAL IS KEPT. No email, no account, no address: the display name
is required (every post is signed, 2026-10-20) but it is free text - a first
name or a handle - and the rate limit lives in memory (judge/gate.py).

THE LIMITS ARE THE CONTRACT'S (contract/discussions.yaml), read on every call
so an edit there needs no deploy. Absent raises (rule 6): this never guesses
what a reader may post.
"""
from __future__ import annotations

import re
import secrets
from typing import Any

STATES = ("pending", "approved", "rejected")

# A bare URL or a markdown link - what "a link" means for `links_max`.
_LINK = re.compile(r"https?://|www\.", re.I)
# Markup is not refused (the page prints text, never HTML), but a post that is
# mostly tags is not a post.
_TAG = re.compile(r"<[^>]{1,200}>")
_WS = re.compile(r"[ \t]+")
# Canonical model ids look like `provider/model-name`.
_MODEL_ID = re.compile(r"^[a-z0-9][a-z0-9._~-]*/[a-z0-9][a-z0-9._:~-]*$", re.I)

#: What a reader sees of a post or a reply - never the moderation fields.
_PUBLIC = ("id", "title", "body", "author_name", "model_id", "created_at")


class PostRefused(ValueError):
    """The post breaks a limit; nothing was stored. The message says which."""


class DiscussionsConfigError(RuntimeError):
    """contract/discussions.yaml is missing something this module needs."""


def settings() -> dict[str, Any]:
    """`contract/discussions.yaml`: the topics and the limits, checked."""
    from judge.config import _read

    raw = _read("discussions.yaml") or {}
    topics = raw.get("topics")
    limits = raw.get("limits")
    if not isinstance(topics, list) or not topics:
        raise DiscussionsConfigError("contract/discussions.yaml has no `topics` list.")
    if not isinstance(limits, dict):
        raise DiscussionsConfigError("contract/discussions.yaml has no `limits` block.")
    needed = ("title_min", "title_max", "body_min", "body_max", "reply_min", "name_min",
              "name_max", "links_max", "posts_per_hour")
    missing = [k for k in needed if not isinstance(limits.get(k), int)]
    if missing:
        raise DiscussionsConfigError(
            f"contract/discussions.yaml `limits` is missing {', '.join(missing)}."
        )
    clean = []
    for t in topics:
        if not isinstance(t, dict) or not t.get("slug") or not t.get("name"):
            raise DiscussionsConfigError("every discussions topic needs a `slug` and a `name`.")
        clean.append({"slug": str(t["slug"]), "name": str(t["name"]),
                      "blurb": " ".join(str(t.get("blurb") or "").split())})
    return {"topics": clean, "limits": {k: int(limits[k]) for k in needed}}


def _text(value: Any) -> str:
    """Trimmed text with runs of spaces folded; line breaks are kept."""
    raw = str(value or "").replace("\r\n", "\n")
    lines = [_WS.sub(" ", line).strip() for line in raw.split("\n")]
    out = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", out)


def _name(post: dict[str, Any], lim: dict[str, int]) -> str:
    name = _text(post.get("author_name")).replace("\n", " ")
    if len(name) < lim["name_min"]:
        raise PostRefused("Add your name - a first name or a handle is enough.")
    if len(name) > lim["name_max"]:
        raise PostRefused(f"A name may be at most {lim['name_max']} characters.")
    return name


def _links_ok(text: str, lim: dict[str, int]) -> None:
    if len(_LINK.findall(text)) > lim["links_max"]:
        raise PostRefused(f"A post may carry at most {lim['links_max']} links.")


def check(post: dict[str, Any]) -> dict[str, Any]:
    """A submitted post or reply, cleaned, or PostRefused with the reason.

    A REPLY names `parent_id` and carries only a body and a name; it takes its
    parent's topic when stored. Whether the parent exists and may take replies
    needs the database, so `submit` checks that.

    `website` is a honeypot: the page hides it, so a person never fills it and
    a form-filling bot usually does. A filled one is refused with the same
    words as any other refusal, so the bot learns nothing.
    """
    cfg = settings()
    lim = cfg["limits"]
    if str(post.get("website") or "").strip():
        raise PostRefused("This post could not be accepted.")

    parent = str(post.get("parent_id") or "").strip()
    if parent:
        if not parent.startswith("dp_") or len(parent) > 40:
            raise PostRefused("That post cannot take replies.")
        body = _text(post.get("body"))
        if not lim["reply_min"] <= len(body) <= lim["body_max"]:
            raise PostRefused(
                f"A reply needs {lim['reply_min']} to {lim['body_max']} characters."
            )
        _links_ok(body, lim)
        return {"parent_id": parent, "body": body, "author_name": _name(post, lim)}

    slugs = {t["slug"] for t in cfg["topics"]}
    topic = str(post.get("topic") or "").strip()
    if topic not in slugs:
        raise PostRefused("Pick one of the topics.")

    title = _text(post.get("title")).replace("\n", " ")
    if not lim["title_min"] <= len(title) <= lim["title_max"]:
        raise PostRefused(
            f"The title needs {lim['title_min']} to {lim['title_max']} characters."
        )
    body = _text(post.get("body"))
    if not lim["body_min"] <= len(body) <= lim["body_max"]:
        raise PostRefused(
            f"The post needs {lim['body_min']} to {lim['body_max']} characters."
        )
    _links_ok(f"{title} {body}", lim)
    if len(_TAG.sub("", body).strip()) < lim["body_min"]:
        raise PostRefused("Write the post in plain text.")

    name = _name(post, lim)

    model = str(post.get("model_id") or "").strip()
    if model and (len(model) > 120 or not _MODEL_ID.match(model)):
        raise PostRefused("Pick a model from the list, or leave it empty.")

    return {"topic": topic, "title": title, "body": body,
            "author_name": name, "model_id": model or None}


def submit(conn, post: dict[str, Any]) -> dict[str, Any]:
    """Check and store one post or reply as `pending`. Returns its id and state.

    A REPLY ANSWERS AN APPROVED POST, ONE LEVEL DEEP: a reply to a pending,
    rejected or missing post - or to another reply - is refused, so nothing is
    attached to what a reader cannot see. It takes its parent's topic.
    """
    clean = check(post)
    pid = f"dp_{secrets.token_hex(8)}"
    if "parent_id" in clean:
        parent = conn.execute(
            "SELECT topic, state, parent_id FROM discussion_post WHERE id = %s",
            (clean["parent_id"],),
        ).fetchone()
        if parent is None or parent[1] != "approved" or parent[2] is not None:
            raise PostRefused("That post cannot take replies.")
        conn.execute(
            "INSERT INTO discussion_post (id, topic, parent_id, body, author_name) "
            "VALUES (%s, %s, %s, %s, %s)",
            (pid, parent[0], clean["parent_id"], clean["body"], clean["author_name"]),
        )
    else:
        conn.execute(
            "INSERT INTO discussion_post (id, topic, title, body, author_name, model_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (pid, clean["topic"], clean["title"], clean["body"], clean["author_name"],
             clean["model_id"]),
        )
    conn.commit()
    return {"id": pid, "state": "pending"}


def _row(r) -> dict[str, Any]:
    pid, topic, parent, title, body, name, model, state, created, reviewed, note = r[:11]
    return {
        "id": pid,
        "topic": topic,
        "parent_id": parent,
        "title": title,
        "body": body,
        "author_name": name,
        "model_id": model,
        "state": state,
        "created_at": created.isoformat() if created else None,
        "reviewed_at": reviewed.isoformat() if reviewed else None,
        "review_note": note,
    }


# THE COLUMNS ARE WRITTEN OUT IN EACH QUERY, not shared through a constant:
# the column audit (tests/test_column_states.py) reads SQL literals.


def public_view(conn, per_topic: int = 50) -> dict[str, Any]:
    """The public page: every topic with its APPROVED posts, NEWEST FIRST by
    when they were written, each carrying its approved replies OLDEST FIRST.

    Pending and rejected rows never leave this function; neither does a review
    note. A reply under a post that is not approved is not shown. The topics
    come from the contract, so a topic with no posts still appears - with an
    empty list, not a missing key (rule 4).
    """
    cfg = settings()
    rows = conn.execute(
        "SELECT id, topic, parent_id, title, body, author_name, model_id, state, "
        "       created_at, reviewed_at, review_note "
        "FROM discussion_post WHERE state = 'approved' "
        "ORDER BY created_at DESC, id",
    ).fetchall()
    posts = [_row(r) for r in rows]
    replies: dict[str, list[dict[str, Any]]] = {}
    for p in reversed(posts):  # oldest first, for a thread
        if p["parent_id"]:
            replies.setdefault(p["parent_id"], []).append({k: p[k] for k in _PUBLIC})
    by_topic: dict[str, list[dict[str, Any]]] = {t["slug"]: [] for t in cfg["topics"]}
    for p in posts:
        if p["parent_id"] or p["topic"] not in by_topic:
            continue
        if len(by_topic[p["topic"]]) < per_topic:
            by_topic[p["topic"]].append(
                {**{k: p[k] for k in _PUBLIC}, "replies": replies.get(p["id"], [])})
    topics = [{**t, "posts": by_topic[t["slug"]]} for t in cfg["topics"]]
    return {
        "topics": topics,
        "total": sum(len(t["posts"]) for t in topics),
        "limits": {k: cfg["limits"][k] for k in ("title_min", "title_max", "body_min",
                                                 "body_max", "reply_min", "name_min",
                                                 "name_max", "links_max")},
    }


def listing(conn, state: str = "pending", limit: int = 200) -> dict[str, Any]:
    """Admin -> Discussions: one state's posts and replies, newest first, and the
    count in each state. A reply carries the title of the post it answers."""
    if state not in STATES:
        raise ValueError("state must be pending, approved or rejected")
    items = [
        {**_row(r), "parent_title": r[11]}
        for r in conn.execute(
            "SELECT d.id, d.topic, d.parent_id, d.title, d.body, d.author_name, d.model_id, "
            "       d.state, d.created_at, d.reviewed_at, d.review_note, p.title "
            "FROM discussion_post d LEFT JOIN discussion_post p ON p.id = d.parent_id "
            "WHERE d.state = %s "
            "ORDER BY d.created_at DESC, d.id LIMIT %s",
            (state, limit),
        ).fetchall()
    ]
    by_state = dict(conn.execute(
        "SELECT state, count(*) FROM discussion_post GROUP BY 1").fetchall())
    return {"counts": {s: by_state.get(s, 0) for s in STATES}, "items": items}


def review(conn, pid: str, decision: str, note: str | None = None) -> dict[str, Any] | None:
    """A person's decision on one post or reply. Deciding again is allowed - a
    misclick is undone by deciding again. None for an unknown id."""
    if decision not in STATES:
        raise ValueError("decision must be approved, rejected or pending")
    row = conn.execute(
        "UPDATE discussion_post SET state = %s, review_note = %s, "
        " reviewed_at = CASE WHEN %s = 'pending' THEN NULL ELSE now() END "
        "WHERE id = %s RETURNING id, state",
        (decision, (note or "").strip() or None, decision, pid),
    ).fetchone()
    conn.commit()
    return {"id": row[0], "state": row[1]} if row else None


def delete(conn, pid: str) -> bool:
    """Remove one post or reply for good (Admin -> Discussions). For what must
    not be kept at all - personal data, abuse, spam. Rejecting hides a row and
    keeps it with its reason; deleting leaves none, and a post's replies go
    with it (ON DELETE CASCADE). False for an unknown id."""
    row = conn.execute("DELETE FROM discussion_post WHERE id = %s RETURNING id", (pid,)).fetchone()
    conn.commit()
    return row is not None
