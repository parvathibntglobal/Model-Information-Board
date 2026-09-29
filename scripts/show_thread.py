"""Print a harvested Reddit thread - the post, then its comments as a tree.

Read-only. `document` holds metadata only; each body is the raw payload that
`text_ref` points at in the raw store, so this joins the two.

    py -3.12 scripts/show_thread.py                 # list threads
    py -3.12 scripts/show_thread.py t3_1wmymp2      # one thread
    py -3.12 scripts/show_thread.py t3_1wmymp2 > thread.txt
    py -3.12 scripts/show_thread.py t3_1wmymp2 --selected

`--selected` prints the latest `thread_context` for the thread instead: the
flattened text E3 built from the post and the comments it kept, which is
exactly what the extractor was shown.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import psycopg  # noqa: E402

from collect.config import settings  # noqa: E402
from collect.rawstore import RawStore, RawStoreError  # noqa: E402


def _payload(store: RawStore, ref: str | None) -> dict | None:
    if not ref:
        return None
    try:
        return json.loads(store.get_text(ref))
    except (RawStoreError, ValueError) as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


def list_threads(conn) -> None:
    rows = conn.execute(
        "SELECT p.external_id, p.url, count(c.id) "
        "FROM document p LEFT JOIN document c "
        "  ON c.thread_root_id = 'reddit:' || p.external_id "
        "WHERE p.external_id LIKE 't3\\_%' "
        "GROUP BY p.external_id, p.url ORDER BY 3 DESC"
    ).fetchall()
    if not rows:
        print("no Reddit posts in this database")
    for ext, url, n in rows:
        print(f"{ext}  {n:>4} comments  {url}")


def show_thread(conn, store: RawStore, post_id: str) -> int:
    post_id = post_id.removeprefix("reddit:")
    row = conn.execute(
        "SELECT url, text_ref FROM document WHERE external_id = %s", (post_id,)
    ).fetchone()
    if row is None:
        print(f"{post_id} is not in this database")
        return 1
    url, ref = row
    post = _payload(store, ref) or {}
    print(f"POST {post_id}  u/{post.get('author', '?')}  score {post.get('score', '?')}")
    print(f"  r/{post.get('subreddit', '?')}  {url}")
    print(f"  {post.get('title', '')}")
    if post.get("selftext"):
        print("  " + post["selftext"].replace("\n", "\n  "))
    if "_error" in post:
        print(f"  [payload unreadable: {post['_error']}]")
    print("-" * 80)

    comments = conn.execute(
        "SELECT external_id, text_ref FROM document "
        "WHERE thread_root_id = %s ORDER BY created_at, external_id",
        (f"reddit:{post_id}",),
    ).fetchall()
    children: dict[str, list[dict]] = defaultdict(list)
    for ext, cref in comments:
        body = _payload(store, cref) or {}
        body.setdefault("name", ext)
        children[body.get("parent_id") or post_id].append(body)

    def walk(parent: str, depth: int) -> None:
        for c in children.get(parent, []):
            pad = "    " * depth
            head = f"{pad}u/{c.get('author', '?')}  score {c.get('score', '?')}  [{c['name']}]"
            text = c.get("body") or f"[payload unreadable: {c.get('_error', 'no body')}]"
            print(head)
            print(pad + "  " + text.replace("\n", "\n" + pad + "  "))
            print()
            walk(c["name"], depth + 1)

    walk(post_id, 0)
    print(f"{len(comments)} comment(s)")
    return 0


def show_selected(conn, store: RawStore, post_id: str) -> int:
    root = "reddit:" + post_id.removeprefix("reddit:")
    row = conn.execute(
        "SELECT child_count, observed_children, selection_method, assembled_at, "
        "       flattened_text_ref "
        "FROM thread_context WHERE thread_root_id = %s "
        "ORDER BY assembled_at DESC LIMIT 1",
        (root,),
    ).fetchone()
    if row is None:
        print(f"{root} has no thread_context - E3 has not assembled it")
        return 1
    kept, observed, method, at, ref = row
    print(f"SELECTED {root}  kept {kept} of {observed} comment(s)  "
          f"method {method}  assembled {at:%Y-%m-%d %H:%M}")
    print("-" * 80)
    try:
        print(store.get_text(ref))
    except RawStoreError as exc:
        print(f"[flattened text unreadable: {type(exc).__name__}: {exc}]")
        return 1
    return 0


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args:
        list_threads(conn)
        return 0
    store = RawStore(settings().raw_store_path)
    if "--selected" in argv:
        return show_selected(conn, store, args[0])
    return show_thread(conn, store, args[0])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
