"""Reads and writes of the workspace database. Every function takes an open
connection and leaves the commit to the caller."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from psycopg.types.json import Jsonb

from judge.content_workspace import settings

DRAFT_STATUSES = ("draft", "ready", "posted", "dropped")
SEVERITIES = ("fail", "warn", "manual")
NOTE_FIELDS = ("body", "topic", "source", "source_type", "check_id", "severity",
               "params", "formats", "sort_order", "archived")


class WorkspaceRequestError(ValueError):
    """A request the workspace refuses; the message says why (HTTP 400/404)."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


# ── seed ─────────────────────────────────────────────────────────────────────


def load_seed(conn: Any, data: dict[str, Any] | None = None) -> dict[str, int]:
    """Insert platforms and notes the database does not hold yet.

    A note whose seed_key is already present is never touched, so a re-run
    cannot overwrite an edit. A platform already present gains any format or
    topic kind the seed lists that it lacks (those lists are not edited in the
    page, so adding cannot undo a person's choice); nothing else about it
    changes. Returns how many platforms, notes and new list entries were added."""
    data = data or settings.seed()
    added = {"platforms": 0, "notes": 0, "platform_lists": 0}
    for p in data["platforms"]:
        row = conn.execute(
            "INSERT INTO cw_platform (key, name, sort_order, formats, topic_kinds,"
            " video_creation, ai_writer_allowed, researched)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (key) DO NOTHING RETURNING key",
            (p["key"], p["name"], p["order"], p["formats"], p["topics"],
             p["video_creation"], p["ai_writer_allowed"], p["researched"]),
        ).fetchone()
        added["platforms"] += row is not None
        if row is None:
            have_f, have_t = conn.execute(
                "SELECT formats, topic_kinds FROM cw_platform WHERE key = %s", (p["key"],)
            ).fetchone()
            new_f = [f for f in p["formats"] if f not in have_f]
            new_t = [t for t in p["topics"] if t not in have_t]
            if new_f or new_t:
                conn.execute(
                    "UPDATE cw_platform SET formats = formats || %s::text[],"
                    " topic_kinds = topic_kinds || %s::text[] WHERE key = %s",
                    (new_f, new_t, p["key"]))
                added["platform_lists"] += len(new_f) + len(new_t)
    blocks = [(None, data["common"])] + [(p["key"], p) for p in data["platforms"]]
    for platform_key, block in blocks:
        for section in settings.SECTIONS:
            for i, n in enumerate(block.get(settings.SEED_SECTION_KEYS[section]) or []):
                added["notes"] += _seed_note(conn, platform_key, section, i, n)
    return added


def _seed_note(conn: Any, platform_key: str | None, section: str, i: int,
               n: dict[str, Any]) -> int:
    is_rule = section == "rule"
    row = conn.execute(
        "INSERT INTO cw_note (platform_key, section, seed_key, topic, source, source_type,"
        " body, check_id, severity, params, formats, sort_order, created_by)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'seed')"
        " ON CONFLICT (seed_key) DO NOTHING RETURNING id",
        (platform_key, section, n["key"], n.get("topic"),
         n.get("source") or ("workspace-rules" if is_rule else None),
         n.get("source_type"), " ".join(str(n["text"]).split()),
         n["check"] if is_rule else None, n["severity"] if is_rule else None,
         Jsonb(n.get("params") or {}), n.get("formats"), i),
    ).fetchone()
    return int(row is not None)


# ── platforms and notes ──────────────────────────────────────────────────────


PLATFORM_COLUMNS = ("key", "name", "sort_order", "formats", "topic_kinds", "video_creation",
                    "ai_writer_allowed", "researched")


def platforms(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"SELECT {', '.join(PLATFORM_COLUMNS)} FROM cw_platform ORDER BY sort_order, key"
    ).fetchall()
    counts = {
        (r[0], r[1]): r[2]
        for r in conn.execute(
            "SELECT platform_key, status, count(*) FROM cw_draft GROUP BY 1, 2").fetchall()
    }
    out = []
    for r in rows:
        p = dict(zip(PLATFORM_COLUMNS, r, strict=True))
        p["drafts"] = {s: counts.get((p["key"], s), 0) for s in DRAFT_STATUSES}
        out.append(p)
    return out


def platform(conn: Any, key: str) -> dict[str, Any]:
    for p in platforms(conn):
        if p["key"] == key:
            return p
    raise WorkspaceRequestError(f"no platform {key!r}", 404)


NOTE_COLUMNS = ("id", "platform_key", "section", "seed_key", "topic", "source", "source_type",
                "body", "check_id", "severity", "params", "formats", "sort_order", "archived",
                "created_at", "created_by", "updated_at", "updated_by")


def _note(row: tuple) -> dict[str, Any]:
    n = dict(zip(NOTE_COLUMNS, row, strict=True))
    for k in ("created_at", "updated_at"):
        n[k] = n[k].isoformat() if n[k] else None
    return n


def notes(conn: Any, platform_key: str, *, archived: bool = False) -> dict[str, list]:
    """The platform's notes and the notes for every platform, by section."""
    rows = conn.execute(
        f"SELECT {', '.join(NOTE_COLUMNS)} FROM cw_note"
        " WHERE (platform_key = %s OR platform_key IS NULL) AND (archived = false OR %s)"
        # The platform's own notes first, then those for every platform.
        " ORDER BY section, platform_key NULLS LAST, sort_order, id",
        (platform_key, archived),
    ).fetchall()
    out: dict[str, list] = {s: [] for s in settings.SECTIONS}
    for r in rows:
        n = _note(r)
        out[n["section"]].append(n)
    return out


def note(conn: Any, note_id: int) -> dict[str, Any]:
    row = conn.execute(
        f"SELECT {', '.join(NOTE_COLUMNS)} FROM cw_note WHERE id = %s", (note_id,)).fetchone()
    if row is None:
        raise WorkspaceRequestError(f"no note {note_id}", 404)
    return _note(row)


def _check_rule_fields(section: str, fields: dict[str, Any]) -> None:
    from judge.content_workspace.checks import CHECKS

    if section == "rule":
        if fields.get("check_id") not in CHECKS:
            raise WorkspaceRequestError(
                f"a rule names one of the checks: {', '.join(sorted(CHECKS))}")
        if fields.get("severity") not in SEVERITIES:
            raise WorkspaceRequestError(f"severity is one of {', '.join(SEVERITIES)}")
        if not isinstance(fields.get("params") or {}, dict):
            raise WorkspaceRequestError("params is an object, e.g. {\"max_chars\": 280}")
    elif fields.get("check_id") or fields.get("severity"):
        raise WorkspaceRequestError("only a rule has a check and a severity")


def create_note(conn: Any, *, platform_key: str | None, section: str, body: str,
                source: str, by: str | None, **fields: Any) -> dict[str, Any]:
    if section not in settings.SECTIONS:
        raise WorkspaceRequestError(f"section is one of {', '.join(settings.SECTIONS)}")
    if not (body or "").strip():
        raise WorkspaceRequestError("a note needs text")
    if not (source or "").strip():
        raise WorkspaceRequestError("a note names its source")
    if platform_key is not None:
        platform(conn, platform_key)
    _check_rule_fields(section, fields)
    row = conn.execute(
        "INSERT INTO cw_note (platform_key, section, topic, source, source_type, body,"
        " check_id, severity, params, formats, sort_order, created_by, updated_by)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
        "  (SELECT coalesce(max(sort_order), -1) + 1 FROM cw_note"
        "   WHERE platform_key IS NOT DISTINCT FROM %s AND section = %s), %s, %s)"
        " RETURNING id",
        (platform_key, section, fields.get("topic"), source.strip(), fields.get("source_type"),
         body.strip(), fields.get("check_id"), fields.get("severity"),
         Jsonb(fields.get("params") or {}), fields.get("formats"), platform_key, section,
         by, by),
    ).fetchone()
    return note(conn, row[0])


def update_note(conn: Any, note_id: int, changes: dict[str, Any],
                by: str | None) -> dict[str, Any]:
    before = note(conn, note_id)
    unknown = set(changes) - set(NOTE_FIELDS)
    if unknown:
        raise WorkspaceRequestError(f"cannot change {', '.join(sorted(unknown))}")
    after = {**before, **changes}
    if not str(after["body"] or "").strip():
        raise WorkspaceRequestError("a note needs text")
    _check_rule_fields(before["section"], after)
    if all(before[k] == after[k] for k in changes):
        return before
    sets = ", ".join(f"{k} = %s" for k in changes)
    values = [Jsonb(v) if k == "params" else (v.strip() if k == "body" else v)
              for k, v in changes.items()]
    conn.execute(
        f"UPDATE cw_note SET {sets}, updated_at = now(), updated_by = %s WHERE id = %s",
        (*values, by, note_id),
    )
    conn.execute(
        "INSERT INTO cw_note_edit (note_id, before, after, edited_by) VALUES (%s,%s,%s,%s)",
        (note_id, Jsonb({k: before[k] for k in changes}),
         Jsonb({k: after[k] for k in changes}), by),
    )
    return note(conn, note_id)


def note_history(conn: Any, note_id: int) -> list[dict[str, Any]]:
    note(conn, note_id)
    return [
        {"before": b, "after": a, "edited_at": at.isoformat(), "edited_by": who}
        for b, a, at, who in conn.execute(
            "SELECT before, after, edited_at, edited_by FROM cw_note_edit"
            " WHERE note_id = %s ORDER BY edited_at DESC, id DESC", (note_id,)).fetchall()
    ]


# ── drafts ───────────────────────────────────────────────────────────────────


DRAFT_COLUMNS = ("id", "platform_key", "format", "topic_kind", "title", "body", "first_comment",
                 "tags", "suggestion", "ai_assisted", "status", "posted_url", "posted_at",
                 "created_at", "created_by", "updated_at", "updated_by")
DRAFT_FIELDS = ("format", "topic_kind", "title", "body", "first_comment", "tags", "suggestion",
                "ai_assisted", "status", "posted_url")


def _draft(row: tuple) -> dict[str, Any]:
    d = dict(zip(DRAFT_COLUMNS, row, strict=True))
    for k in ("posted_at", "created_at", "updated_at"):
        d[k] = d[k].isoformat() if d[k] else None
    return d


def drafts(conn: Any, platform_key: str | None = None) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"SELECT {', '.join(DRAFT_COLUMNS)} FROM cw_draft"
        " WHERE (%s::text IS NULL OR platform_key = %s) ORDER BY updated_at DESC, id DESC",
        (platform_key, platform_key),
    ).fetchall()
    out = [_draft(r) for r in rows]
    ids = [d["id"] for d in out]
    latest, saved = latest_checks(conn, ids), ticks(conn, ids)
    for d in out:
        d["last_check"] = latest.get(d["id"])
        d["ticks"] = {str(k): v for k, v in saved.get(d["id"], {}).items()}
        d["content_sha"] = content_sha(d)
    return out


def draft(conn: Any, draft_id: int) -> dict[str, Any]:
    row = conn.execute(
        f"SELECT {', '.join(DRAFT_COLUMNS)} FROM cw_draft WHERE id = %s", (draft_id,)).fetchone()
    if row is None:
        raise WorkspaceRequestError(f"no draft {draft_id}", 404)
    d = _draft(row)
    d["last_check"] = latest_checks(conn, [draft_id]).get(draft_id)
    d["ticks"] = {str(k): v for k, v in ticks(conn, [draft_id]).get(draft_id, {}).items()}
    d["content_sha"] = content_sha(d)
    return d


def _check_draft_fields(p: dict[str, Any], fields: dict[str, Any]) -> None:
    if "format" in fields and fields["format"] not in p["formats"]:
        raise WorkspaceRequestError(
            f"{p['name']} formats are {', '.join(p['formats'])}")
    if fields.get("topic_kind") and fields["topic_kind"] not in p["topic_kinds"]:
        raise WorkspaceRequestError(f"{fields['topic_kind']!r} is not a {p['name']} topic")
    if "status" in fields and fields["status"] not in DRAFT_STATUSES:
        raise WorkspaceRequestError(f"status is one of {', '.join(DRAFT_STATUSES)}")
    # `ai_assisted` on a platform that allows no AI writer is recorded, not
    # refused: the flag is a person's statement of fact, and refusing it would
    # teach them to hide it. The platform's ai_assisted rule decides what it
    # means (fail on Hacker News, warn on Reddit and Medium).
    if "tags" in fields and not all(isinstance(t, str) for t in fields["tags"] or []):
        raise WorkspaceRequestError("tags is a list of words")


def create_draft(conn: Any, platform_key: str, fields: dict[str, Any],
                 by: str | None) -> dict[str, Any]:
    p = platform(conn, platform_key)
    unknown = set(fields) - set(DRAFT_FIELDS)
    if unknown:
        raise WorkspaceRequestError(f"unknown draft fields: {', '.join(sorted(unknown))}")
    if "format" not in fields:
        raise WorkspaceRequestError("a draft names its format")
    _check_draft_fields(p, fields)
    row = conn.execute(
        "INSERT INTO cw_draft (platform_key, format, topic_kind, title, body, first_comment, tags,"
        " suggestion, ai_assisted, created_by, updated_by)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (platform_key, fields["format"], fields.get("topic_kind"), fields.get("title"),
         fields.get("body") or "", fields.get("first_comment") or None, fields.get("tags") or [],
         Jsonb(fields["suggestion"]) if fields.get("suggestion") else None,
         bool(fields.get("ai_assisted")), by, by),
    ).fetchone()
    return draft(conn, row[0])


def update_draft(conn: Any, draft_id: int, changes: dict[str, Any],
                 by: str | None) -> dict[str, Any]:
    before = draft(conn, draft_id)
    unknown = set(changes) - set(DRAFT_FIELDS)
    if unknown:
        raise WorkspaceRequestError(f"cannot change {', '.join(sorted(unknown))}")
    _check_draft_fields(platform(conn, before["platform_key"]), changes)
    if not changes:
        return before
    if changes.get("status") == "posted" and not (
            changes.get("posted_url") or before["posted_url"]):
        raise WorkspaceRequestError("a posted draft records where it was posted (posted_url)")
    sets = [f"{k} = %s" for k in changes]
    values = [Jsonb(v) if k == "suggestion" and v is not None else v
              for k, v in changes.items()]
    if changes.get("status") == "posted" and before["status"] != "posted":
        sets.append("posted_at = now()")
    conn.execute(
        f"UPDATE cw_draft SET {', '.join(sets)}, updated_at = now(), updated_by = %s"
        " WHERE id = %s", (*values, by, draft_id))
    return draft(conn, draft_id)


# ── check runs ───────────────────────────────────────────────────────────────


def content_sha(d: dict[str, Any]) -> str:
    """What a check run checked: the fields a check reads."""
    keys = ("format", "title", "body", "first_comment", "tags", "ai_assisted")
    raw = json.dumps({k: d.get(k) for k in keys}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def record_check(conn: Any, d: dict[str, Any], report: dict[str, Any],
                 by: str | None) -> dict[str, Any]:
    row = conn.execute(
        "INSERT INTO cw_check_run (draft_id, ran_by, content_sha, results, counts)"
        " VALUES (%s,%s,%s,%s,%s) RETURNING id, ran_at",
        (d["id"], by, content_sha(d), Jsonb(report["results"]), Jsonb(report["counts"])),
    ).fetchone()
    return {"id": row[0], "ran_at": row[1].isoformat(), "content_sha": content_sha(d),
            **report}


def latest_checks(conn: Any, draft_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not draft_ids:
        return {}
    rows = conn.execute(
        "SELECT DISTINCT ON (draft_id) draft_id, id, ran_at, content_sha, results, counts"
        " FROM cw_check_run WHERE draft_id = ANY(%s) ORDER BY draft_id, ran_at DESC, id DESC",
        (draft_ids,),
    ).fetchall()
    return {r[0]: {"id": r[1], "ran_at": r[2].isoformat(), "content_sha": r[3],
                   "results": r[4], "counts": r[5]} for r in rows}


# ── saved ticks for rules checked by hand ────────────────────────────────────


def ticks(conn: Any, draft_ids: list[int]) -> dict[int, dict[int, dict[str, Any]]]:
    """The latest tick per (draft, rule): {draft_id: {note_id: {...}}}."""
    if not draft_ids:
        return {}
    out: dict[int, dict[int, dict[str, Any]]] = {}
    for draft_id, note_id, ticked, sha, at, by in conn.execute(
            "SELECT DISTINCT ON (draft_id, note_id) draft_id, note_id, ticked, content_sha, at,"
            " by_whom FROM cw_tick WHERE draft_id = ANY(%s)"
            " ORDER BY draft_id, note_id, at DESC, id DESC", (draft_ids,)).fetchall():
        out.setdefault(draft_id, {})[note_id] = {
            "ticked": ticked, "content_sha": sha, "at": at.isoformat(), "by": by}
    return out


def set_tick(conn: Any, draft_id: int, note_id: int, ticked: bool,
             by: str | None) -> dict[str, Any]:
    """Record a person ticking (or unticking) a hand-checked rule on a draft,
    against the draft's content as it is now (`content_sha`)."""
    d = draft(conn, draft_id)
    n = note(conn, note_id)
    if n["section"] != "rule" or (n["severity"] != "manual" and n["check_id"] != "manual"):
        raise WorkspaceRequestError("only a rule checked by hand can be ticked")
    if n["platform_key"] not in (None, d["platform_key"]):
        raise WorkspaceRequestError("that rule belongs to another platform")
    conn.execute(
        "INSERT INTO cw_tick (draft_id, note_id, ticked, content_sha, by_whom)"
        " VALUES (%s,%s,%s,%s,%s)", (draft_id, note_id, bool(ticked), content_sha(d), by))
    return ticks(conn, [draft_id]).get(draft_id, {})
