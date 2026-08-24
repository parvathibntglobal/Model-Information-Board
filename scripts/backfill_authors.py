"""Set `author_id` on Reddit and GitHub documents that already have none.

Usage:
    py -3 scripts/backfill_authors.py --dry-run
    py -3 scripts/backfill_authors.py

REPORTS BEFORE AND AFTER, AND NAMES WHAT IT COULD NOT DO. A backfill that
prints only what it changed cannot be told apart from one that found nothing to
change, and those are opposite outcomes.

WHERE THE IDS COME FROM: THE STORED PAYLOAD, NOT A RE-FETCH
-----------------------------------------------------------
`document.text_ref` points at the immutable payload the adapter stored, and that
payload carries `author_fullname` for Reddit and `user.id` for GitHub. So this is
a re-parse, which is the convention this lane already holds: *"Raw payloads are
immutable and content-hash addressed. Reprocess from there rather than
re-fetching."*

Re-fetching would also be wrong for a second reason: a rename between the
original fetch and today would attribute the document to the account's CURRENT
handle rather than the one that wrote it. The stored payload is the only source
that cannot drift.

A DOCUMENT WHOSE PAYLOAD IS UNREADABLE IS NAMED, NOT SKIPPED
------------------------------------------------------------
`missing`, `tombstoned` and `corrupt` are three different findings and only one
of them is routine. A tombstone is a takedown honoured; a missing blob is an
NFR-4 alert. Both leave `author_id` NULL, and the difference is what tells you
whether to investigate or to accept.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from collect.adapters.github import github_author_id  # noqa: E402
from collect.adapters.reddit import author_external_id  # noqa: E402
from collect.adapters.reddit_write import _SET_AUTHOR  # noqa: E402
from collect.assemble.authors import (  # noqa: E402
    AuthorRow,
    hash_handle,
    write_authors,
)
from collect.db import connect  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.rawstore_reader import RawStoreReader, ReadOutcome  # noqa: E402


def census(conn) -> dict[str, Any]:
    """The counts this whole exercise is measured by."""
    rows = conn.execute(
        "SELECT source, count(*), count(author_id), count(DISTINCT author_id) "
        "FROM document GROUP BY 1 ORDER BY 1"
    ).fetchall()
    authors = conn.execute("SELECT count(*) FROM author").fetchone()[0]
    by_source = conn.execute(
        "SELECT source, count(*) FROM author GROUP BY 1 ORDER BY 1"
    ).fetchall()
    return {
        "documents": {
            src: {"docs": n, "with_author": a, "distinct_authors": d}
            for src, n, a, d in rows
        },
        "author_rows": authors,
        "author_rows_by_source": dict(by_source),
    }


def show(label: str, c: dict[str, Any]) -> None:
    print(f"  {label}")
    total = with_author = 0
    for src, v in sorted(c["documents"].items()):
        print(f"    {src:<8} docs={v['docs']:<4} with_author={v['with_author']:<4} "
              f"distinct_authors={v['distinct_authors']}")
        total += v["docs"]
        with_author += v["with_author"]
    print(f"    {'TOTAL':<8} docs={total:<4} with_author={with_author:<4} "
          f"without={total - with_author}")
    print(f"    author rows: {c['author_rows']}  {c['author_rows_by_source']}")


def _reddit_author(payload: Any) -> tuple[str | None, str | None]:
    """`(external_id, handle)` from a stored comment or post payload."""
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    return author_external_id(data.get("author_fullname")), data.get("author")


def _github_author(payload: Any) -> tuple[str | None, str | None]:
    data = payload if isinstance(payload, dict) else {}
    user = data.get("user") or {}
    uid = user.get("id")
    return (str(uid) if uid is not None else None), user.get("login")


def collect_attributions(conn, store: RawStoreReader) -> dict[str, Any]:
    """Read every authorless Reddit/GitHub document's payload for its author.

    Returns the updates it can make and a tally of every reason it could not.
    """
    rows = conn.execute(
        "SELECT id, source, external_id, text_ref FROM document "
        "WHERE source IN ('reddit', 'github') AND author_id IS NULL "
        "ORDER BY source, id"
    ).fetchall()

    updates: list[dict[str, str]] = []
    author_rows: list[AuthorRow] = []
    reasons: Counter[str] = Counter()
    unresolved: list[tuple[str, str]] = []

    for doc_id, source, _external, ref in rows:
        if not ref:
            reasons[f"{source}: no text_ref"] += 1
            unresolved.append((doc_id, "no text_ref"))
            continue
        try:
            got = store.resolve(ref)
        except ValueError:
            reasons[f"{source}: malformed ref"] += 1
            unresolved.append((doc_id, "malformed ref"))
            continue
        if got.outcome is not ReadOutcome.FOUND:
            # NAMED, NOT COUNTED AS ONE THING. A tombstone is a takedown
            # honoured; a missing blob is an NFR-4 alert.
            reasons[f"{source}: payload {got.outcome}"] += 1
            unresolved.append((doc_id, f"payload {got.outcome}"))
            continue
        try:
            payload = json.loads(got.text)
        except json.JSONDecodeError:
            reasons[f"{source}: payload is not JSON"] += 1
            unresolved.append((doc_id, "payload is not JSON"))
            continue

        external_id, handle = (
            _reddit_author(payload) if source == "reddit" else _github_author(payload)
        )
        if not external_id:
            # The account is gone. NO ROW rather than a shared one.
            reasons[f"{source}: no stable author id in payload"] += 1
            unresolved.append((doc_id, "no stable author id"))
            continue

        row = AuthorRow(source=source, external_id=external_id,
                        handle_hash=hash_handle(handle))
        author_rows.append(row)
        updates.append({"id": doc_id, "author_id": row.id})

    return {
        "candidates": len(rows),
        "updates": updates,
        "author_rows": author_rows,
        "reasons": dict(reasons),
        "unresolved": unresolved,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change and write nothing")
    args = ap.parse_args(argv)

    conn = connect()
    store = RawStoreReader(RawStore())

    print("BEFORE")
    before = census(conn)
    show("", before)
    print()

    found = collect_attributions(conn, store)
    print(f"authorless reddit+github documents   {found['candidates']}")
    print(f"attributable from the stored payload {len(found['updates'])}")
    print(f"distinct authors they resolve to     "
          f"{len({r.id for r in found['author_rows']})}")
    if found["reasons"]:
        print("  could not attribute — named rather than skipped:")
        for reason, n in sorted(found["reasons"].items()):
            print(f"    {n:>4}  {reason}")
    print()

    if args.dry_run:
        print("dry run — nothing written")
        conn.close()
        return 0

    if not found["updates"]:
        print("NOTHING TO WRITE, and that is not the same as nothing to do.")
        print("Every candidate above is listed with the reason it could not be")
        print("attributed. `author_id` stays NULL, which the gate reads as no")
        print("voice — correctly, since no identity was recovered.")
        conn.close()
        return 0

    author_counts = write_authors(conn, found["author_rows"])
    updated = 0
    with conn.cursor() as cur:
        cur.executemany(_SET_AUTHOR, found["updates"])
        updated = max(0, cur.rowcount)
    conn.commit()

    print(f"author rows inserted   {author_counts['inserted']}")
    print(f"documents updated      {updated}")
    print()
    print("AFTER")
    after = census(conn)
    show("", after)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
