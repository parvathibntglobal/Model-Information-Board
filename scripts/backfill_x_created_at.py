#!/usr/bin/env python3
"""Date the X documents that were written with no `created_at`, and mark their
threads unread so their claims can reach the board.

WHY (2026-10-08). X sends `Sat May 16 07:41:54 +0000 2026`, and
`collect/adapters/documents.py:_as_timestamp` only read ISO-8601 and epoch
numbers, so every X document since the adapter landed (2026-09-08) was written
undated: 344 of 344 in the 2026-10-07 backup. `judge/cli.py:_document_facts`
gives an undated document no facts, and the pipeline skips every claim from a
document with no facts - so X produced 0 board entries from 233 threads read,
while local fetch logs show 477 verified X claims among 148 of them.

WHAT IT DOES
  1. For each X document with `created_at` NULL, read its stored payload and
     take the tweet's own `legacy.created_at` (not the author's account date,
     which the payload also carries), parsed by the fixed `_as_timestamp`.
     Only a NULL is filled; an existing date is never overwritten.
  2. With `--reread`: delete the `thread_extraction` row of every X thread
     whose documents are now dated and which has no board entry, so the next
     fetch for a model those threads name reads them again. Those claims were
     verified and then dropped, never stored, so re-reading is the only way to
     recover them. A thread that already has a board entry is left alone.

Dry run by default; `--write` writes. The writeguard runs before the
connection opens, as for every write path. Prints counts only: tweet ids are
X material and stay out of output that might be pasted into a PR.

    py scripts/backfill_x_created_at.py                      # dry run
    py scripts/backfill_x_created_at.py --write --reread     # write
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collect.adapters.documents import _as_timestamp  # noqa: E402
from collect.config import settings  # noqa: E402
from collect.db import connect  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.rawstore_reader import RawStoreReader  # noqa: E402

_UNDATED = "SELECT id, text_ref FROM document WHERE source = 'x' AND created_at IS NULL ORDER BY id"
_SET_DATE = ("UPDATE document SET created_at = %(created_at)s "
             "WHERE id = %(id)s AND created_at IS NULL")
#: X threads read, now fully dated, with no board entry from any member.
_REREAD = """
SELECT t.id
  FROM thread_context t
  JOIN thread_extraction x ON x.thread_context_id = t.id
 WHERE EXISTS (SELECT 1 FROM document d WHERE d.id = t.thread_root_id AND d.source = 'x')
   AND NOT EXISTS (SELECT 1 FROM document d
                    WHERE d.id = ANY(t.member_document_ids) AND d.created_at IS NULL)
   AND NOT EXISTS (SELECT 1 FROM board_entry b WHERE b.document_id = ANY(t.member_document_ids))
"""


def tweet_date(payload: object) -> str | None:
    """The tweet's own `legacy.created_at`. `TweetWithVisibilityResults` wraps
    the tweet one level down under `tweet`; nothing else is unwrapped."""
    if not isinstance(payload, dict):
        return None
    if "legacy" not in payload and isinstance(payload.get("tweet"), dict):
        payload = payload["tweet"]
    legacy = payload.get("legacy")
    return legacy.get("created_at") if isinstance(legacy, dict) else None


def dates_for(conn, reader: RawStoreReader) -> tuple[list[dict], Counter]:
    """Updates for undated X documents, and why each other one was left NULL."""
    updates: list[dict] = []
    left = Counter()
    for doc_id, ref in conn.execute(_UNDATED).fetchall():
        if not ref:
            left["no text_ref"] += 1
            continue
        got = reader.resolve(ref)
        if not got.found:
            left["payload not on this machine"] += 1
            continue
        try:
            payload = json.loads(got.require())
        except ValueError:
            left["payload not JSON"] += 1
            continue
        raw = tweet_date(payload)
        if raw is None:
            left["no legacy.created_at in the payload"] += 1
            continue
        when = _as_timestamp(raw)
        if when is None:
            left[f"date did not parse: {raw[:40]!r}"] += 1
            continue
        updates.append({"id": doc_id, "created_at": when})
    return updates, left


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="write; the default is a dry run")
    ap.add_argument("--reread", action="store_true",
                    help="also mark dated X threads with no board entry unread")
    ap.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    args = ap.parse_args(argv)

    # THE WRITEGUARD, BEFORE THE CONNECTION, as backfill_is_self_post.py does.
    from judge.writeguard import check as writeguard_check
    writeguard_check(args.database_url, command="backfill_x_created_at.py")

    reader = RawStoreReader(RawStore(Path(settings().raw_store_path)))
    conn = connect(args.database_url)
    try:
        total_x = conn.execute("SELECT count(*) FROM document WHERE source = 'x'").fetchone()[0]
        updates, left = dates_for(conn, reader)
        undated = len(updates) + sum(left.values())
        print(f"X documents                {total_x}")
        print(f"  with no created_at       {undated}")
        print(f"  datable from payload     {len(updates)}")
        for why, n in sorted(left.items()):
            print(f"  left NULL: {why:<34} {n}")

        if args.write and updates:
            with conn.cursor() as cur:
                cur.executemany(_SET_DATE, updates)
        reread = [r[0] for r in conn.execute(_REREAD).fetchall()] if args.reread else []
        if args.reread:
            # In a dry run the dates are not written, so the query sees today's
            # NULLs and finds fewer threads than a write would; say so.
            print(f"X threads to mark unread   {len(reread)}"
                  + ("" if args.write else "  (counted before dating; a write finds more)"))
        if args.write and reread:
            conn.execute("DELETE FROM thread_extraction WHERE thread_context_id = ANY(%s)",
                         (reread,))
        if args.write:
            conn.commit()
            print(f"\nWRITTEN: {len(updates)} document date(s)"
                  + (f", {len(reread)} thread(s) marked unread" if args.reread else ""))
            print("Next fetch for a model these threads name reads them again.")
        else:
            conn.rollback()
            print("\nDRY RUN. Nothing written. --write writes; --reread also marks threads unread.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
