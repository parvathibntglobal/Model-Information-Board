"""Restore `text_ref` and `content_hash` to the payload on Reddit documents.

WHAT THIS UNDOES, AND WHY THE THING IT UNDOES WAS ALSO NECESSARY

`scripts/repoint_reddit_text_refs.py` fixed a real defect: both sweeps stored
`json.dumps(post.raw)` and `assemble_reddit` was about to flatten JSON envelopes
for 1,512 threads, which would have verified quotes against field values while
reporting clean. That fix worked.

It also did this, and that half was wrong:

    UPDATE document SET text_ref = ..., content_hash = ...

`document` has exactly ONE ref column - no `raw_ref` - so pointing `text_ref` at
derived prose left the payload unreferenced, and overwriting `content_hash` left
it unidentified. NFR-6 wants a hash that fingerprints what the AUTHOR published
(ours fingerprinted a string we assembled, and it moved whenever our extractor
changed); NFR-4 wants the row to name its raw artifact.

The ruling is `docs/engineer-1/ruling-what-content-hash-identifies.md`:

    content_hash   the hash of the bytes the platform gave us, unmodified
    text_ref       the location of those same bytes
    prose          derived at ASSEMBLY, never stored in place of the payload
    invariant      content_hash(resolve(text_ref)) == content_hash

This script restores the first two. The third is the assembler change, which is
a separate commit - **so between the two, Reddit assembly is broken and must not
run.** That order is deliberate: a row pointing at a payload is honest and
unusable, while a row pointing at prose is usable and lying.

IDEMPOTENT BY CONSTRUCTION, not by a flag. Two independent reasons:

  * A row whose `text_ref` already resolves to a payload is SKIPPED, so a
    re-run selects nothing to do.
  * The target is computed from the payload bytes through a content-addressed
    store, so `put` of the same bytes yields the same ref and hash. Even if a
    row were re-processed, the UPDATE would write the values already there.

NO NETWORK CALLS. The payloads were never deleted - the store is immutable and
content-addressed, so overwriting a Postgres column orphaned the pointer, not
the object. Each payload carries the post's own `id`/`name`, which is how the
mapping is rebuilt.

    python scripts/restore_reddit_payload_refs.py --dry-run
    python scripts/restore_reddit_payload_refs.py --apply
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collect.config import settings  # noqa: E402
from collect.db import connect  # noqa: E402
from collect.rawstore import RAW, RawStore  # noqa: E402
from collect.rawstore_reader import RawStoreReader  # noqa: E402

#: Stores searched for payloads. The configured store is written to; the others
#: are read-only sources for objects that landed there during the sweeps.
SEARCH_STORES = ("raw_store", "_sweep_store")

_UPDATE = (
    "UPDATE document SET text_ref = %(text_ref)s, content_hash = %(content_hash)s "
    "WHERE id = %(id)s"
)


def is_payload(obj: object) -> bool:
    """A per-post/comment payload rather than a listing page or something else.

    `selftext` for a post, `body` for a comment. A listing page has `data` or
    `posts` and no `selftext` at its top level, which is what separates them.
    """
    return isinstance(obj, dict) and ("selftext" in obj or "body" in obj)


def build_index() -> dict[str, tuple[str, pathlib.Path]]:
    """`external_id` spelling -> (store name, path) for every stored payload.

    Keyed by BOTH `name` (`t3_abc`) and `id` (`abc`), because `document.
    external_id` carries the prefixed form and the payload spells it both ways.
    First writer wins: the same payload in two stores is the same bytes, so
    which one is found does not matter.
    """
    index: dict[str, tuple[str, pathlib.Path]] = {}
    for store in SEARCH_STORES:
        root = pathlib.Path(store, RAW.prefix)
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            blob = path.read_bytes()
            if blob[:1] != b"{":
                continue
            try:
                obj = json.loads(blob)
            except ValueError:
                continue
            if not is_payload(obj):
                continue
            for key in ("name", "id"):
                value = obj.get(key)
                if value:
                    index.setdefault(str(value), (store, path))
    return index


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    store = RawStore(settings().raw_store_path)
    readers = [(name, RawStoreReader(RawStore(name))) for name in SEARCH_STORES]

    def resolves_to_payload(ref: str | None) -> bool:
        if not ref:
            return False
        for _, reader in readers:
            outcome = reader.resolve(ref)
            if outcome.found:
                text = outcome.require().lstrip()
                if text[:1] != "{":
                    return False
                try:
                    return is_payload(json.loads(outcome.require()))
                except ValueError:
                    return False
        return False        # unresolved: not known to be a payload

    print("indexing stored payloads ...")
    index = build_index()
    print(f"  payload spellings indexed : {len(index)}")

    conn = connect()
    rows = conn.execute(
        "SELECT id, external_id, text_ref FROM document WHERE source = 'reddit' "
        "ORDER BY id"
    ).fetchall()
    print(f"  reddit documents          : {len(rows)}")

    plan: list[dict[str, str]] = []
    reasons: collections.Counter = collections.Counter()

    for doc_id, external_id, text_ref in rows:
        if resolves_to_payload(text_ref):
            reasons["already points at a payload - skipped"] += 1
            continue
        bare = external_id.split("_", 1)[-1]
        found = index.get(external_id) or index.get(bare)
        if found is None:
            # NAMED, NOT COUNTED SILENTLY. These rows stay broken and the
            # repair has to say so rather than reporting a clean run over the
            # subset it could reach.
            reasons["NO PAYLOAD IN ANY STORE - stays broken"] += 1
            continue
        _, path = found
        stored = store.put(path.read_bytes(), namespace=RAW)
        if stored.ref == text_ref:
            reasons["already correct - skipped"] += 1
            continue
        plan.append(
            {"id": doc_id, "text_ref": stored.ref, "content_hash": stored.content_hash}
        )

    print()
    print(f"to update : {len(plan)}")
    for reason, count in reasons.most_common():
        print(f"  {count:6d}  {reason}")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        conn.close()
        return 0

    with conn.cursor() as cur:
        cur.executemany(_UPDATE, plan)
    conn.commit()
    conn.close()
    print(f"\napplied: {len(plan)} row(s) updated and committed.")
    print("Reddit ASSEMBLY IS NOW BROKEN until the assembler extracts prose "
          "from the payload - that is the next commit, and it is deliberate: "
          "a row pointing at a payload is honest and unusable, one pointing at "
          "prose is usable and lying.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
