"""Write EVERY comment in a Reddit thread as a `document`, with `author_id`.

Usage:
    py -3 scripts/write_reddit_thread.py --dry-run
    py -3 scripts/write_reddit_thread.py

WHY ALL 195 AND NOT THE SELECTED FIVE
-------------------------------------

`scripts/export_thread_contexts.py` writes documents for
`assembled.member_document_ids` — the children `collect/assemble/thread.py`
SELECTED for flattening. That is five of 195, and it answered the wrong question:

    selection for extraction   which children does the extractor read?
                               a ranking problem, bounded by prompt budget
    storage as evidence        who spoke in this thread?
                               a counting problem, bounded by nothing

Writing only the selected children answers the second with the first. The 190
unselected comments are not lower-quality evidence — they are **the voices**,
and `judge/curate/gate.py` counts people rather than passages. Five documents
from one thread can carry at most five voices; the thread has 151.

WHAT THIS DELIBERATELY DOES NOT CHANGE
--------------------------------------

**Extraction still reads five.** `thread_context` selection is untouched: its
`member_document_ids` and its `offset_map` are exactly what they were, so the
extractor's input is byte-identical and no claim yield changes. The 190 extra
documents are **evidence for the gate, not input to the extractor** — they exist
so that a claim extracted from a selected comment can be counted against a
corpus that knows how many people were in the room.

Anyone expecting more claims from this is expecting the wrong thing. What changes
is `author`, `document`, and every denominator downstream of them.

REFS ARE CONTENT ADDRESSES, NOT LOCATIONS
-----------------------------------------

Each body is `store.put`, so `text_ref` is the hash of the bytes. That ref is
correct on every host; whether the BLOB is present is a separate fact about a
particular store. The six pre-existing reddit rows carry refs whose blobs are
absent from this machine — that is the store being host-specific, not the refs
being wrong.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from collect.adapters.reddit_comments import parse_thread  # noqa: E402
from collect.adapters.reddit_write import write_documents  # noqa: E402
from collect.db import connect  # noqa: E402
from collect.ids import content_hash  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402

PAYLOAD = ROOT / "fixtures" / "reddit" / "thread-1u1b22l-getPostComments.json"
THREAD_URL = "https://www.reddit.com/r/ClaudeAI/comments/1u1b22l/"


@dataclass(frozen=True)
class RootPost:
    """The thread root as `write_documents` needs it.

    No `thread_root_id` and no `parent_id`: a post is its own root, and a
    self-reference would make "is this a root" unanswerable. `document_row`
    discriminates on the fields, so their absence is the whole signal.
    """

    external_id: str
    url: str
    author: str | None
    author_fullname: str | None
    created_at: datetime | None
    engagement: dict[str, Any]


def load() -> tuple[RootPost, list[Any], dict[str, str], Any]:
    payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    thread = parse_thread(payload, url=THREAD_URL)
    root = payload["data"][0]["data"]["children"][0]["data"]

    root_text = (root.get("title", "") + "\n\n" + (root.get("selftext") or "")).strip()
    created = (
        datetime.fromtimestamp(float(root["created_utc"]), tz=UTC)
        if root.get("created_utc") is not None
        else None
    )
    post = RootPost(
        external_id=root["name"],
        url=f"https://www.reddit.com{root.get('permalink', '/')}",
        author=root.get("author"),
        author_fullname=root.get("author_fullname"),
        created_at=created,
        engagement={
            "score": root.get("score"),
            "num_comments": root.get("num_comments"),
            "upvote_ratio": root.get("upvote_ratio"),
        },
    )
    texts = {post.external_id: root_text}
    for c in thread.comments:
        texts[c.external_id] = c.body
    return post, list(thread.comments), texts, thread.coverage


def census(conn) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT source, count(*), count(author_id), count(DISTINCT author_id) "
        "FROM document GROUP BY 1 ORDER BY 1"
    ).fetchall()
    authors = conn.execute(
        "SELECT source, count(*) FROM author GROUP BY 1 ORDER BY 1"
    ).fetchall()
    return {"documents": rows, "authors": dict(authors),
            "author_total": sum(n for _, n in authors)}


def show(c: dict[str, Any]) -> None:
    total = with_author = 0
    for src, n, a, d in c["documents"]:
        print(f"    {src:<8} docs={n:<5} with_author={a:<5} distinct_authors={d}")
        total += n
        with_author += a
    print(f"    {'TOTAL':<8} docs={total:<5} with_author={with_author:<5} "
          f"without={total - with_author}")
    print(f"    author rows: {c['author_total']}  {c['authors']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    post, comments, texts, coverage = load()
    items = [post, *comments]

    print(f"payload   {PAYLOAD.relative_to(ROOT)}")
    print(f"root      {post.external_id}  author={post.author_fullname}")
    print(f"comments  {len(comments)}")
    print(f"coverage  observed={coverage.observed_children} "
          f"hidden_min={coverage.hidden_children_min} "
          f"reported_total={coverage.reported_total}")
    print()

    # THE POPULATION, BEFORE WRITING ANYTHING. A count of what we are about to
    # attribute is the only way to tell "151 authors" from "151 rows".
    with_id = [i for i in items if getattr(i, "author_fullname", None)]
    print(f"items to write            {len(items)}   (root + {len(comments)} comments)")
    print(f"carrying author_fullname  {len(with_id)}")
    print(f"WITHOUT one               {len(items) - len(with_id)}  "
          f"-> no author row, no shared row")
    print(f"distinct author ids       "
          f"{len({i.author_fullname for i in with_id})}")
    print()

    conn = connect()
    print("BEFORE")
    show(census(conn))
    print()

    if args.dry_run:
        print("dry run - nothing written")
        conn.close()
        return 0

    store = RawStore()
    refs = {}
    for external_id, text in texts.items():
        refs[external_id] = (store.put(text).ref, content_hash(text))

    counts = write_documents(conn, items, refs=refs)
    conn.commit()

    print("WROTE")
    for k, v in counts.items():
        print(f"    {k:<26} {v}")
    print()
    print("AFTER")
    show(census(conn))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
