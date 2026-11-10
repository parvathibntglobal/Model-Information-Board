"""Admin -> Kite Pulse -> Outreach: the phase-1 review queue (ARCHITECTURE.md 5.5).

A person reads a thread the Finders saved, and either SKIPS it with a reason
or answers it on the forum FROM THEIR OWN ACCOUNT and records the reply's URL
here. Nothing here posts anywhere, holds a forum credential or calls a model;
it reads and updates kp_outreach_thread in the outreach database only.

Imported by judge/app.py (`_kp_review`), which appends this folder to sys.path.
This module imports nothing from collect/ (tests/test_lane_boundary.py: judge
may not reach collect/ through a module in between).

Transitions, and the only ones:

    found   -> skipped    skip(): a reason from SKIP_REASONS; 'other' needs a note
    found   -> posted     mark_posted(): the reply's URL and the account it was
                          posted from; the URL is checked against the thread
    skipped -> found      reopen(): undoes a misclick; the decision is cleared
    posted  -> found      reopen()

A dropped thread is shown, with its reason, and cannot be acted on: the code
filter that dropped it is the decision (ARCHITECTURE.md 5.2a).
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import reply_check
from common import db, spend
from common import thread as t

HERE = Path(__file__).resolve().parent
MAX_REPLY_TO_CHECK = 20_000

SKIP_REASONS = {
    "not_relevant": "Not relevant",
    "already_answered": "Already answered well",
    "community_unwelcoming": "The community would not welcome it",
    "other": "Other (say why)",
}
TABS = ("found", "posted", "skipped", "dropped")
LIST_LIMIT = 200
MAX_NOTE = 500
MAX_ACCOUNT = 100

# How far a posted URL can be tied to its thread, per source. Hacker News and
# dev.to reply links do not name the story or article they belong to, so for
# those only the site and the link's shape are checked.
URL_CHECK = {
    "github": "same discussion",
    "discourse": "same topic",
    "hackernews": "site and link shape only (a Hacker News reply link does not name its story)",
    "devto": "site and link shape only (a dev.to comment link does not name its article)",
    "reddit": "same post",
}


class Refused(ValueError):
    """The request is wrong: a bad reason, URL or account. HTTP 400."""


class NotFound(LookupError):
    """No thread with that id. HTTP 404."""


class WrongState(RuntimeError):
    """The thread is not in a state this action applies to. HTTP 409."""


def assert_loaded_from(folder: Path) -> None:
    """This module and the `common` package it uses come from `folder`.

    judge/app.py APPENDS this folder to sys.path, so an unrelated top-level
    package called `common` installed later would win silently. Fail instead.
    """
    for name, path in (("kp_review", __file__), ("common", db.__file__),
                       ("reply_check", reply_check.__file__)):
        if Path(folder).resolve() not in Path(path).resolve().parents:
            raise RuntimeError(f"{name} was imported from {path}, not from {folder}")


def connect() -> Any:
    return db.connect()


# ── reading ──────────────────────────────────────────────────────────────────

COLUMNS = (
    "id, source, kind, community, url, root_id, title, body, author, created_at, "
    "fetched_at, matched_problems, matched_phrases, status, drop_reason, flags, "
    "decided_at, decided_by, skip_reason, skip_note, posted_url, posted_by_account"
)
ORDER = {
    "found": "sl_group, created_at DESC",
    "dropped": "created_at DESC",
    "posted": "decided_at DESC",
    "skipped": "decided_at DESC",
}

# THE SHORTLISTER'S ROW for each thread (shortlist.py), the newest under any
# prompt version. It ORDERS To review and nothing else: no thread is hidden or
# acted on because of it. The groups, in order, are said in words on the page
# (SHORTLIST_GROUPS); within a group, newest first.
SHORTLIST_JOIN = """
LEFT JOIN LATERAL (
  SELECT s.outcome AS sl_outcome, s.set_aside_reason AS sl_set_aside_reason,
         s.model AS sl_model, s.problem AS sl_problem, s.relevance AS sl_relevance,
         s.article_slug AS sl_article_slug, s.slug_verified AS sl_slug_verified,
         s.reason AS sl_reason, s.invalid_why AS sl_invalid_why, s.at AS sl_at,
         sp.input_tokens AS sl_input_tokens, sp.output_tokens AS sl_output_tokens,
         sp.usd AS sl_usd
  FROM kp_outreach_shortlist s LEFT JOIN kp_outreach_spend sp ON sp.id = s.spend_id
  WHERE s.thread_id = t.id ORDER BY s.at DESC, s.id DESC LIMIT 1
) sl ON true
"""
SHORTLIST_GROUP_SQL = """
CASE
  WHEN sl.sl_outcome = 'proposed' AND sl.sl_problem <> 'none' AND sl.sl_relevance = 'high' THEN 1
  WHEN sl.sl_outcome = 'proposed' AND sl.sl_problem <> 'none' AND sl.sl_relevance = 'medium' THEN 2
  WHEN sl.sl_outcome IS NULL OR sl.sl_outcome = 'invalid' THEN 3
  WHEN sl.sl_outcome = 'proposed' AND sl.sl_problem <> 'none' THEN 4
  WHEN sl.sl_outcome = 'proposed' THEN 5
  ELSE 6
END
"""
SHORTLIST_GROUPS = {
    1: "Model suggests: high relevance",
    2: "Model suggests: medium relevance",
    3: "Not sorted yet",
    4: "Model suggests: low relevance",
    5: "Model suggests: none of our problems",
    6: "Set aside by code, not sent to the model",
}
SHORTLIST_FIELDS = ("outcome", "set_aside_reason", "model", "problem", "relevance",
                    "article_slug", "slug_verified", "reason", "invalid_why", "at",
                    "input_tokens", "output_tokens", "usd")


def _item(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key in ("created_at", "fetched_at", "decided_at"):
        out[key] = out[key].isoformat() if out[key] else None
    out["url_check"] = URL_CHECK.get(out["source"]) if out["status"] == "posted" else None
    sl = {k: out.pop(f"sl_{k}", None) for k in SHORTLIST_FIELDS}
    group = out.pop("sl_group", None)
    if sl["at"]:
        sl["at"] = sl["at"].isoformat()
    # A cost as text, so no float rounds it; None stays None (not reported, not $0).
    sl["usd"] = None if sl["usd"] is None else str(sl["usd"])
    out["shortlist"] = sl if sl["outcome"] else None     # None: never shortlisted
    out["shortlist_group"] = group
    return out


def _usage_between(conn: Any, start: Any, end: Any) -> dict[str, Any]:
    calls, tin, tout, unmetered, usd, unpriced, first = conn.execute(
        "SELECT count(*), sum(input_tokens), sum(output_tokens), "
        "count(*) FILTER (WHERE input_tokens IS NULL OR output_tokens IS NULL), "
        "sum(usd), count(*) FILTER (WHERE usd IS NULL), min(at) "
        "FROM kp_outreach_spend WHERE (%s::timestamptz IS NULL OR at >= %s) "
        "AND (%s::timestamptz IS NULL OR at < %s)", (start, start, end, end)).fetchone()
    return {
        "calls": calls,
        # sums over the calls that reported them; None when no call did
        "input_tokens": tin, "output_tokens": tout, "unmetered_calls": unmetered,
        "usd": None if usd is None else str(usd), "unpriced_calls": unpriced,
        "first_at": first.isoformat() if first else None,
    }


def usage(conn: Any) -> dict[str, Any]:
    """Every outreach model call (kp_outreach_spend): today (UTC) and in all.

    Every step and every source, including calls repeated after a prompt
    change, so it can exceed the sum of the per-thread figures on screen.
    A sum with an unpriced or unmetered call in it is a floor, and says so.
    """
    start = spend.day_start()
    try:
        budget, budget_problem = str(spend.daily_budget()), None
    except spend.SpendError as exc:
        budget, budget_problem = None, str(exc)
    return {
        "today": _usage_between(conn, start, start + timedelta(days=1)),
        "all_time": _usage_between(conn, None, None),
        "day_starts_at": start.isoformat(),
        "daily_budget_usd": budget,
        "budget_problem": budget_problem,
    }


# To review, three ways to look at it. Each is a filter on the Shortlister's
# row; none changes what a thread IS, and "all" is always one click away.
VIEWS = {
    "all": None,
    "sent": "sl.sl_outcome IN ('proposed', 'invalid')",
    "selected": f"({SHORTLIST_GROUP_SQL}) IN (1, 2)",
}


def _shortlist_stats(conn: Any, where: str, params: list[Any]) -> dict[str, Any]:
    """What the Shortlister did with the threads in To review (these filters).

    Every count is of threads, by their newest shortlist row. `not_sorted` is
    threads with no row at all: never read, which is not "rated low" (rule 4).
    """
    base = f"FROM kp_outreach_thread t {SHORTLIST_JOIN} WHERE {where}"
    total, not_sorted, set_aside, sent, proposed, invalid = conn.execute(
        "SELECT count(*), count(*) FILTER (WHERE sl.sl_outcome IS NULL), "
        "count(*) FILTER (WHERE sl.sl_outcome = 'set_aside'), "
        "count(*) FILTER (WHERE sl.sl_outcome IN ('proposed', 'invalid')), "
        "count(*) FILTER (WHERE sl.sl_outcome = 'proposed'), "
        f"count(*) FILTER (WHERE sl.sl_outcome = 'invalid') {base}", params).fetchone()
    by_reason = dict(conn.execute(
        f"SELECT sl.sl_set_aside_reason, count(*) {base} AND sl.sl_outcome = 'set_aside' "
        "GROUP BY 1", params).fetchall())
    groups = dict(conn.execute(
        f"SELECT {SHORTLIST_GROUP_SQL} AS g, count(*) {base} GROUP BY 1", params).fetchall())
    return {
        "total": total,
        "not_sorted": not_sorted,
        "set_aside": set_aside,
        "set_aside_by_reason": by_reason,
        "sent_to_model": sent,
        "model_answered": proposed,
        "model_answer_failed_checks": invalid,
        "groups": [{"group": g, "label": label, "count": groups.get(g, 0)}
                   for g, label in SHORTLIST_GROUPS.items()],
    }


def listing(conn: Any, tab: str, *, source: str | None = None,
            problem: str | None = None, view: str | None = None) -> dict[str, Any]:
    """One tab's threads (at most LIST_LIMIT) and every count.

    `view` applies to To review only: all (default), sent (threads the
    Shortlister sent to the model) or selected (the model suggested high or
    medium relevance).
    """
    if tab not in TABS:
        raise Refused(f"tab must be one of {', '.join(TABS)}, got {tab!r}")
    view = view or "all"
    if view not in VIEWS:
        raise Refused(f"view must be one of {', '.join(VIEWS)}, got {view!r}")
    if view != "all" and tab != "found":
        raise Refused("a view other than 'all' applies to To review only")
    from psycopg.rows import dict_row

    where, params = ["t.status = %s"], [tab]
    if source:
        where.append("t.source = %s")
        params.append(source)
    if problem:
        where.append("%s = ANY(t.matched_problems)")
        params.append(problem)
    stats = _shortlist_stats(conn, " AND ".join(where), params) if tab == "found" else None
    if VIEWS[view]:
        where.append(VIEWS[view])
    cur = conn.cursor(row_factory=dict_row)
    matching = cur.execute(
        f"SELECT count(*) AS n FROM kp_outreach_thread t {SHORTLIST_JOIN} "
        f"WHERE {' AND '.join(where)}", params).fetchone()["n"]
    rows = cur.execute(
        f"SELECT * FROM (SELECT t.{COLUMNS.replace(', ', ', t.')}, sl.*, "
        f"{SHORTLIST_GROUP_SQL} AS sl_group "
        f"FROM kp_outreach_thread t {SHORTLIST_JOIN} WHERE {' AND '.join(where)}) x "
        f"ORDER BY {ORDER[tab]}, id DESC LIMIT %s", [*params, LIST_LIMIT]).fetchall()
    counts = {s: 0 for s in TABS}
    counts.update(dict(conn.execute(
        "SELECT status, count(*) FROM kp_outreach_thread GROUP BY 1").fetchall()))
    return {
        "tab": tab,
        "view": view,
        "items": [_item(r) for r in rows],
        "matching": matching,          # in this tab, view and filters; items may be fewer
        "limit": LIST_LIMIT,
        "counts": counts,
        "sources": [r[0] for r in conn.execute(
            "SELECT DISTINCT source FROM kp_outreach_thread ORDER BY 1")],
        "problems": [r[0] for r in conn.execute(
            "SELECT DISTINCT unnest(matched_problems) FROM kp_outreach_thread ORDER BY 1")],
        "skip_reasons": SKIP_REASONS,
        # To review only: what the Shortlister did, under the source and
        # problem filters but across every view, so switching view never
        # changes these numbers. None on other tabs.
        "shortlist": stats,
        "usage": usage(conn) if tab == "found" else None,
        "database": conn.info.dbname,
    }


# ── the posted URL ───────────────────────────────────────────────────────────

def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def check_reply_url(th: dict[str, Any], url: str) -> str:
    """The reply URL, cleaned, or Refused saying what is wrong with it.

    Checks what each site's URLs allow (URL_CHECK). Never fetches anything:
    the backend makes no request to a forum.
    """
    url = (url or "").strip()
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise Refused("paste the full link to your reply, starting with https://")
    if _host(url) != _host(th["url"]):
        raise Refused(f"that link is on {_host(url)}, but this thread is on {_host(th['url'])}")
    if url.rstrip("/") == th["url"].rstrip("/"):
        raise Refused("that is the thread's own link; paste the link to YOUR reply")
    path = [p for p in parts.path.split("/") if p]
    source = th["source"]

    if source == "github":
        thread_path = [p for p in urlsplit(th["url"]).path.split("/") if p]
        if path != thread_path or not parts.fragment.startswith("discussioncomment-"):
            raise Refused("a GitHub reply link is the discussion's link ending "
                          "#discussioncomment-<number> (use the reply's '...' > Copy link)")
    elif source == "discourse":
        topic = str(th["root_id"])
        ok = ("t" in path and topic in path and path.index(topic) + 1 < len(path)
              and path[path.index(topic) + 1].isdigit()
              and int(path[path.index(topic) + 1]) > 1)
        if not ok:
            raise Refused(f"a reply in this topic links as .../t/<slug>/{topic}/<post number>; "
                          "use the reply's link icon")
    elif source == "hackernews":
        ids = parse_qs(parts.query).get("id", [])
        if path != ["item"] or len(ids) != 1 or not ids[0].isdigit():
            raise Refused("a Hacker News reply links as news.ycombinator.com/item?id=<number>; "
                          "click your reply's timestamp to get it")
    elif source == "devto":
        if len(path) != 3 or path[1] != "comment":
            raise Refused("a dev.to comment links as dev.to/<you>/comment/<id>; "
                          "use the comment's '...' > Copy link")
    elif source == "reddit":
        # /r/<sub>/comments/<post>/comment/<id>/ (Share > Copy link) or the
        # older /r/<sub>/comments/<post>/<slug>/<id>/. A /r/<sub>/s/<token>
        # share link names no post, so it is refused rather than guessed at.
        post = str(th["root_id"])
        thread_sub = [p for p in urlsplit(th["url"]).path.split("/") if p][1:2]
        ok = (len(path) == 6 and path[0] == "r" and path[2] == "comments"
              and [path[1].lower()] == [s.lower() for s in thread_sub]
              and path[3] == post and path[5].isalnum())
        if not ok:
            raise Refused(f"a reply on this post links as reddit.com/r/<sub>/comments/{post}/"
                          "comment/<id>; use the comment's Share > Copy link, and if it "
                          "gives a /s/ link, open it and copy the address it lands on")
    else:
        raise Refused(f"no rule for checking a {source!r} reply link")
    return url


# ── checking a reply before it is posted ─────────────────────────────────────

def check_reply(conn: Any, thread_id: int, text: str) -> dict[str, Any]:
    """Run the REPLY CHECK on a reply a person is about to post. Writes nothing.

    ADVISORY in phase 1 (reply_check.py): the result is shown, it does not
    gate Mark posted. Any thread may be checked, whatever its status.
    """
    if len(text or "") > MAX_REPLY_TO_CHECK:
        raise Refused(f"the reply is {len(text)} characters; the limit is {MAX_REPLY_TO_CHECK}")
    from psycopg.rows import dict_row

    th = conn.cursor(row_factory=dict_row).execute(
        "SELECT id, source, url, title, body FROM kp_outreach_thread WHERE id = %s",
        (thread_id,)).fetchone()
    if th is None:
        raise NotFound(f"no thread {thread_id}")
    try:
        return reply_check.check(text, th, reply_check.load_rules()).as_dict()
    except reply_check.Refused as exc:
        raise Refused(str(exc)) from None


# ── deciding ─────────────────────────────────────────────────────────────────

def _thread(conn: Any, thread_id: int) -> dict[str, Any]:
    from psycopg.rows import dict_row

    row = conn.cursor(row_factory=dict_row).execute(
        f"SELECT {COLUMNS} FROM kp_outreach_thread WHERE id = %s FOR UPDATE",
        (thread_id,)).fetchone()
    if row is None:
        raise NotFound(f"no thread {thread_id}")
    return row


def _require(th: dict[str, Any], *states: str) -> None:
    if th["status"] not in states:
        raise WrongState(f"thread {th['id']} is {th['status']!r}; this applies to "
                         f"{' or '.join(states)} threads only")


def skip(conn: Any, thread_id: int, reason: str, note: str | None,
         by: str | None) -> dict[str, Any]:
    note = (note or "").strip() or None
    if reason not in SKIP_REASONS:
        raise Refused(f"reason must be one of {', '.join(SKIP_REASONS)}, got {reason!r}")
    if reason == "other" and not note:
        raise Refused("say why in the note when the reason is 'other'")
    if note and len(note) > MAX_NOTE:
        raise Refused(f"the note is {len(note)} characters; the limit is {MAX_NOTE}")
    with conn.transaction():
        th = _thread(conn, thread_id)
        _require(th, t.STATUS_FOUND)
        conn.execute(
            "UPDATE kp_outreach_thread SET status = 'skipped', skip_reason = %s, "
            "skip_note = %s, decided_at = now(), decided_by = %s WHERE id = %s",
            (reason, note, by, thread_id))
        return _item(_thread(conn, thread_id))


def mark_posted(conn: Any, thread_id: int, url: str, account: str,
                by: str | None) -> dict[str, Any]:
    account = (account or "").strip().removeprefix("@")
    if not account:
        raise Refused("say which account you posted from")
    if len(account) > MAX_ACCOUNT:
        raise Refused(f"the account name is {len(account)} characters; the limit is "
                      f"{MAX_ACCOUNT}")
    with conn.transaction():
        th = _thread(conn, thread_id)
        _require(th, t.STATUS_FOUND)
        url = check_reply_url(th, url)
        conn.execute(
            "UPDATE kp_outreach_thread SET status = 'posted', posted_url = %s, "
            "posted_by_account = %s, decided_at = now(), decided_by = %s WHERE id = %s",
            (url, account, by, thread_id))
        return _item(_thread(conn, thread_id))


def reopen(conn: Any, thread_id: int) -> dict[str, Any]:
    with conn.transaction():
        th = _thread(conn, thread_id)
        _require(th, "skipped", "posted")
        conn.execute(
            "UPDATE kp_outreach_thread SET status = 'found', skip_reason = NULL, "
            "skip_note = NULL, posted_url = NULL, posted_by_account = NULL, "
            "decided_at = NULL, decided_by = NULL WHERE id = %s", (thread_id,))
        return _item(_thread(conn, thread_id))
