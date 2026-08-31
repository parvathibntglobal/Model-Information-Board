"""Re-point `document.text_ref` at the post's TEXT where it points at JSON.

A ONE-OFF CORRECTION OF MY OWN SAME-DAY ERROR, and not a migration because a
migration is pure SQL: this has to read each payload out of the object store,
extract the text, write a new store entry, and only then update the row.

WHAT WENT WRONG

`scripts/model_only_sweep.py` and `collect/ops/sweep_reddit.py` stored
`json.dumps(post.raw)` and pointed `text_ref` at it. `document.text_ref` is where
the document's TEXT lives - `rawstore.py` opens by separating location from
identity - and the API payload belongs in the `raw` namespace, which the stored
search and listing pages already hold. So the payload was stored twice and the
text not at all.

WHY IT MATTERS MORE THAN A WASTED WRITE

`assemble_*` passes whatever `text_ref` resolves to straight into `flatten`, so a
`thread_context` built from these rows would have held a JSON envelope. A quote
would then verify against a FIELD VALUE - `"selftext": "..."` contains the text,
so a substring check passes - which is rule 1 returning true for the wrong reason.
Worse than failing to verify, because it looks like it worked.

Caught before `assemble reddit` ran over the corpus, by checking what `text_ref`
actually contained rather than assuming.

IDEMPOTENT, AND THE TEST IS THE CONTENT

Only rows whose stored text parses as a JSON object with a `selftext` or `title`
key are touched. A row already pointing at prose is left alone, so a second run
is a no-op and a partial first run resumes cleanly.

    python scripts/repoint_reddit_text_refs.py --dry-run
    python scripts/repoint_reddit_text_refs.py
"""

from __future__ import annotations

import argparse
import json

from collect.config import settings
from collect.rawstore import RAW, RawStore
from collect.rawstore_reader import RawStoreReader

_UPDATE = (
    "UPDATE document SET text_ref = %(text_ref)s, content_hash = %(content_hash)s "
    "WHERE id = %(id)s"
)


def payload_text(stored: str) -> str | None:
    """The post's text if `stored` is a raw payload, else None.

    None means LEAVE THIS ROW ALONE - it is already prose, or it is something
    this script does not understand, and either way guessing is worse than
    skipping. The skip is counted and reported.
    """
    if not stored.lstrip().startswith("{"):
        return None
    try:
        payload = json.loads(stored)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    if "selftext" not in payload and "title" not in payload:
        return None
    return (payload.get("title") or "") + "\n\n" + (payload.get("selftext") or "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    store = RawStore(settings().raw_store_path)
    reader = RawStoreReader(store)

    from collect.db import connect, transaction

    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, text_ref FROM document "
            "WHERE source = 'reddit' AND text_ref IS NOT NULL ORDER BY id"
            + (f" LIMIT {int(args.limit)}" if args.limit else "")
        ).fetchall()
    finally:
        conn.close()

    plan: list[dict] = []
    counts = {"rows": len(rows), "json": 0, "prose": 0, "unreadable": 0, "empty": 0}
    for document_id, text_ref in rows:
        outcome = reader.resolve(text_ref)
        if not outcome.found:
            counts["unreadable"] += 1
            continue
        text = payload_text(outcome.require())
        if text is None:
            counts["prose"] += 1
            continue
        counts["json"] += 1
        if not text.strip():
            # A post with an empty title AND empty selftext. Re-pointing at an
            # empty string is worse than leaving the JSON: `assemble_*` refuses
            # empty text loudly, and an empty ref would refuse quietly.
            counts["empty"] += 1
            continue
        plan.append({"id": document_id, "text": text})

    print(f"reddit rows with a text_ref     {counts['rows']}")
    print(f"  pointing at a JSON payload    {counts['json']}   <- to re-point")
    print(f"  already prose, left alone     {counts['prose']}")
    print(f"  unreadable in this store      {counts['unreadable']}")
    print(f"  JSON but no text at all       {counts['empty']}   <- skipped, see the code")
    print(f"  will update                   {len(plan)}")

    if args.dry_run:
        print("(dry run - nothing stored, nothing updated)")
        return 0

    for entry in plan:
        stored = store.put(entry["text"].encode("utf-8"), namespace=RAW)
        entry["text_ref"] = stored.ref
        entry["content_hash"] = stored.content_hash

    with transaction() as conn:
        from collect.cli import _gate

        _gate(conn)
        with conn.cursor() as cur:
            cur.executemany(_UPDATE, plan)
            updated = cur.rowcount
    print(f"updated  : {updated} row(s) re-pointed at the post text")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
