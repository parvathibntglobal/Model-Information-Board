"""Rebuild GitHub `thread_context` rows that hold a JSON envelope instead of prose.

WHY THEY HOLD JSON. `collect/adapters/github.py:583` sets
`text_ref = issue.ref`, which is correct and deliberate - it points at the issue
PAYLOAD so `content_hash` identifies one document rather than a search page
covering a hundred. `assemble_issue` then flattened those bytes VERBATIM, so all
80 contexts begin `{"url":"https://api.github.com/repos/...`.

WHY IT REPORTED CLEAN. The prose is present inside the JSON as `"body": "..."`,
so a quote of it verifies by exact substring, `quote_verified` is true and
`claim_verified_ck` is satisfied. Rule 1 returning true for the wrong reason,
with the offsets pointing into an API response. `assemble_issue` now extracts via
`collect/assemble/prose.py` - this rebuilds what the old path produced.

WHY DELETING IS SAFE HERE AND WOULD NOT BE LATER. `thread_context` has exactly
two inbound foreign keys, `claim.thread_context_id` and
`thread_extraction.thread_context_id`, and both are checked before anything is
removed. Today github has **0 claims and 0 extractions**, so this costs nothing.
It stops being free the moment a github claim exists, because re-flattening moves
every character position and an offset cannot be rebuilt later
(`collect/CLAUDE.md`, first rule).

`thread_context.id` is `stable_id("thread_context", document_id, version)`, so a
rebuild at the same `pipeline_version` reuses the same id - the delete is what
lets `assemble_github_documents` see the document as a candidate again, since it
selects on `NOT EXISTS`.

    python scripts/rebuild_github_contexts.py --dry-run
    python scripts/rebuild_github_contexts.py --apply
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collect.assemble.issue import assemble_github_documents  # noqa: E402
from collect.config import settings                            # noqa: E402
from collect.db import connect                                 # noqa: E402
from collect.rawstore import RawStore                          # noqa: E402
from collect.rawstore_reader import RawStoreReader             # noqa: E402

_IDS = (
    "SELECT tc.id FROM thread_context tc "
    "JOIN document d ON d.id = tc.thread_root_id "
    "WHERE d.source = 'github'"
)


def looks_like_json(text: str) -> bool:
    """PARSES rather than sniffs the first character.

    A leading `[` is not evidence: 39 rebuilt contexts were flagged by a
    first-character check and every one was prose, because the flattener
    substitutes emoji as shortcodes and the titles began `[bar_chart] AI CLI
    Tools Digest`. Sniffing produced a 100% false-positive rate on real data.
    """
    head = text.lstrip()[:1]
    if head not in {"{", "["}:
        return False
    try:
        return isinstance(json.loads(text), (dict, list))
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    conn = connect()
    store = RawStore(settings().raw_store_path)
    reader = RawStoreReader(store)

    ids = [r[0] for r in conn.execute(_IDS).fetchall()]
    print(f"github thread_context rows        : {len(ids)}")

    envelope = unresolved = prose = 0
    for (flat_ref,) in conn.execute(
        _IDS.replace("tc.id", "tc.flattened_text_ref")
    ).fetchall():
        outcome = reader.resolve(flat_ref) if flat_ref else None
        if outcome is None or not outcome.found:
            unresolved += 1
        elif looks_like_json(outcome.require()):
            envelope += 1
        else:
            prose += 1
    print(f"  flattened text is a JSON envelope: {envelope}")
    print(f"  flattened text is prose          : {prose}")
    print(f"  flattened text did not resolve   : {unresolved}")

    claims = conn.execute(
        "SELECT count(*) FROM claim WHERE thread_context_id = ANY(%s)", (ids,)
    ).fetchone()[0]
    extractions = conn.execute(
        "SELECT count(*) FROM thread_extraction WHERE thread_context_id = ANY(%s)",
        (ids,),
    ).fetchone()[0]
    print(f"  claims referencing them          : {claims}")
    print(f"  thread_extraction rows           : {extractions}")

    if claims or extractions:
        # REFUSES RATHER THAN CASCADING. A claim carries offsets into the old
        # flattened text; re-flattening invalidates them and they cannot be
        # recomputed. Deleting the claim silently would discard verified
        # evidence, so this stops and says what to decide.
        print(
            "\nREFUSING: rows depend on these contexts. Re-flattening moves every "
            "offset, so those claims would carry positions into text that no "
            "longer exists. Re-extraction is the repair, and it is a decision "
            "rather than a side effect of this script."
        )
        conn.close()
        return 1

    # ── CONSOLIDATE PAYLOADS INTO THE CONFIGURED STORE ──────────────────────
    #
    # The github payloads landed in `_sweep_store`, a scratch store from ad-hoc
    # runs; `settings().raw_store_path` is the durable one the pipeline reads. The
    # store is CONTENT-ADDRESSED, so putting the same bytes in produces the same
    # ref - `document.text_ref` stays valid, and the copy is idempotent. Without
    # this the driver refuses all 71 with "did not resolve", which would read as
    # missing payloads rather than as payloads in the wrong place.
    others = [RawStoreReader(RawStore(name)) for name in ("_sweep_store",)]
    to_copy: list[tuple[str, str]] = []
    for doc_id, text_ref in conn.execute(
        "SELECT id, text_ref FROM document WHERE source = 'github' "
        "AND text_ref IS NOT NULL"
    ).fetchall():
        if reader.resolve(text_ref).found:
            continue
        for other in others:
            outcome = other.resolve(text_ref)
            if outcome.found:
                to_copy.append((doc_id, text_ref))
                break
    print(f"  payloads to copy into {settings().raw_store_path}: {len(to_copy)}")

    if args.dry_run:
        print(f"\n--dry-run: would copy {len(to_copy)} payload(s), delete "
              f"{len(ids)} context(s) and re-assemble. Nothing written.")
        conn.close()
        return 0

    # READ THE FILE BY ITS REF PATH, not through `resolve().require()`. The
    # reader returns `str`, and re-encoding a decoded string is not guaranteed to
    # reproduce the original bytes - which would change the hash and so the ref.
    # A ref IS the layout (`raw/sha256/ab/cd/abcd...`), so the path is derivable
    # and the copy is exact.
    copied = mismatched = missing = 0
    for _doc_id, text_ref in to_copy:
        source_path = pathlib.Path("_sweep_store", text_ref)
        if not source_path.is_file():
            missing += 1
            continue
        stored = store.put(source_path.read_bytes())
        if stored.ref != text_ref:
            # NAMED, NOT IGNORED. A different ref means different bytes, so the
            # copy is not the artifact the row points at - and silently
            # repointing the row would be the original defect again.
            mismatched += 1
        else:
            copied += 1
    print(f"copied {copied} payload(s) into the configured store, ref unchanged"
          + (f"; {mismatched} hashed DIFFERENTLY and were left alone" if mismatched else "")
          + (f"; {missing} not found at their ref path" if missing else ""))

    with conn.cursor() as cur:
        cur.execute("DELETE FROM thread_context WHERE id = ANY(%s)", (ids,))
        deleted = cur.rowcount
    print(f"\ndeleted {deleted} context(s)")

    report = assemble_github_documents(conn, store=store)
    conn.commit()

    print(f"candidates : {report.candidates}")
    print(f"assembled  : {report.assembled}")
    print(f"comments unread (a floor, not a guess): {report.comments_unread}")
    if report.refusals:
        print(f"refusals   : {len(report.refusals)}")
        for line in report.refusals[:6]:
            print(f"    {line[:150]}")

    # VERIFY, in the same run. A rebuild that reports success while leaving
    # envelopes behind is the defect wearing a green tick.
    still = 0
    for (flat_ref,) in conn.execute(
        _IDS.replace("tc.id", "tc.flattened_text_ref")
    ).fetchall():
        outcome = reader.resolve(flat_ref) if flat_ref else None
        if outcome is not None and outcome.found and looks_like_json(outcome.require()):
            still += 1
    print(f"\ncontexts still holding JSON after the rebuild: {still}")
    conn.close()
    return 0 if still == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
