"""Write a Finder's threads to the outreach database (kp_outreach_thread).

INSERT ONLY, and a thread already in the table is LEFT ALONE: matched again on
a later run, its row keeps whatever a person has since set (skipped, posted).
`ON CONFLICT (source, ext_id) DO NOTHING`.

What that means, so nobody reads more into a row than it says:

- A row's `status`, `drop_reason` and `flags` are what the Finder decided the
  FIRST time it saw the thread. A later run that would drop it (say, a team
  member has since replied) does not change the row.
- `matched_phrases` are the phrases that matched on that first run.

The JSONL files keep every run's view; this table is the review queue.

Every outcome is printed, and a failed or skipped write is never silent: the
Finder exits 1 when the database was meant to be written and was not.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from . import db
from .thread import Thread

INSERT = """
INSERT INTO kp_outreach_thread (
  source, ext_id, kind, community, url, root_id, title, body, author,
  created_at, fetched_at, matched_problems, matched_phrases, status, drop_reason, flags
) VALUES (
  %(source)s, %(ext_id)s, %(kind)s, %(community)s, %(url)s, %(root_id)s, %(title)s,
  %(body)s, %(author)s, %(created_at)s, %(fetched_at)s, %(matched_problems)s,
  %(matched_phrases)s, %(status)s, %(drop_reason)s, %(flags)s
)
ON CONFLICT (source, ext_id) DO NOTHING
RETURNING id
"""


@dataclass(frozen=True)
class Saved:
    database: str
    inserted: int
    already_present: int


def _row(th: Thread) -> dict[str, Any]:
    return {
        "source": th.source, "ext_id": th.ext_id, "kind": th.kind,
        "community": th.community, "url": th.url, "root_id": th.root_id,
        "title": th.title, "body": th.body, "author": th.author,
        "created_at": th.created_at, "fetched_at": th.fetched_at,
        "matched_problems": list(th.matched_problems),
        "matched_phrases": list(th.matched_phrases),
        "status": th.status, "drop_reason": th.drop_reason, "flags": list(th.flags),
    }


def save(conn: Any, threads: Iterable[Thread]) -> Saved:
    """Insert every thread not already present, in one transaction."""
    inserted = present = 0
    with conn.transaction():
        for th in threads:
            if conn.execute(INSERT, _row(th)).fetchone() is None:
                present += 1
            else:
                inserted += 1
    return Saved(database=conn.info.dbname, inserted=inserted, already_present=present)


def skip_reason(*, no_db: bool, phrase: str | None) -> str | None:
    """Why a Finder run should not write the database, or None to write it."""
    if no_db:
        return "--no-db"
    if phrase:
        return "a --phrase run is a phrase being tried out; it does not fill the review queue"
    return None


def save_and_report(threads: list[Thread], *, skip_reason: str | None) -> bool:
    """Write to the database and print one line saying what happened.

    Returns False when a write was meant to happen and did not, so the Finder
    can exit 1. A deliberate skip (`skip_reason`) is printed and returns True.
    """
    if skip_reason:
        print(f"\nDatabase: NOT written ({skip_reason}). The threads are in the JSONL only.")
        return True
    import psycopg

    try:
        with db.connect() as conn:
            saved = save(conn, threads)
    except psycopg.errors.UndefinedTable:
        print("\nDatabase: FAILED, kp_outreach_thread does not exist. Run "
              "py -3.12 web/src/kitepulse/outreach/setup_db.py, then this again. "
              "The threads are in the JSONL only.")
        return False
    except (db.OutreachDbError, psycopg.Error) as exc:
        print(f"\nDatabase: FAILED, {type(exc).__name__}: {exc}".rstrip()
              + "\n  The threads are in the JSONL only.")
        return False
    print(f"\nDatabase {saved.database}: {saved.inserted} new thread(s) added, "
          f"{saved.already_present} already there and left unchanged "
          f"(of {len(threads)} in this run).")
    return True
