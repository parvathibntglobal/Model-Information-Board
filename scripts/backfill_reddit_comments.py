"""Give body-only Reddit threads that were NEVER EXTRACTED their comments.

WHY THESE AND NOT ALL OF THEM
-----------------------------
Measured on staging 2026-10-05: 1,615 Reddit contexts were `child_count = 0`,
1,520 of them on posts the platform says have comments, and 1,300 of those had
never been extracted. Nearly all came from the listing sweep, which stored posts
and nothing under them until `collect/ops/sweep_reddit.py` learned to fetch
comments the same day.

A context that was never extracted carries no `claim`, no `thread_extraction`
row and no `board_entry` - the only two foreign keys onto `thread_context` are
the first two, and both are NO ACTION. So for these, a rebuild costs requests
and nothing else: no evidence is superseded, no model is called. The extracted
ones (230 that day) are NOT touched here; their old evidence must be re-extracted
and swapped, which is `scripts/rebuild_reddit_contexts_with_comments.py`'s job
and is a paid, reviewed decision rather than a side effect of this one.

WHY A DELETE, AND WHY INSIDE ONE TRANSACTION
--------------------------------------------
A context's id hashes the root and the pipeline version, not its members, and
`write_thread_context` is ON CONFLICT DO NOTHING. So fetching comments and
re-running the assembler changes zero rows: the run looks successful and the
comments sit in `document` reachable by nothing. The body-only row has to go
first. Per root:

    1. fetch comments            network, metered, append-only
    2. store payloads + rows     append-only, committed
    3. ONE TRANSACTION:
         re-check the guards FOR UPDATE   (extracted since? skip)
         delete the body-only context
         assemble this root only          (`assemble_reddit_documents(roots=)`)
         refuse unless it assembled WITH at least one reply
       commit, or roll back to exactly the row that was there

A failure in 1-2 leaves the context as it was. A failure in 3 rolls back. There
is no moment at which a root has no context.

WHICH COMMENTS REACH THE EXTRACTOR is decided by the assembler's ranking
(`collect/assemble/ranking.py`, weights in `contract/harvest.yaml`
`child_ranking`). This script stores the whole tree and selects nothing.

STAGING IS SHARED. This deletes and rewrites context rows, so it is a
coordinated write: announce it before `--apply` against staging.

    python scripts/backfill_reddit_comments.py --dry-run
    python scripts/backfill_reddit_comments.py --apply --limit 5
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.assemble.reddit import REDDIT_SOURCE, assemble_reddit_documents  # noqa: E402
from collect.config import settings  # noqa: E402
from collect.db import connect  # noqa: E402
from collect.rawstore import RAW, RawStore  # noqa: E402
from collect.rawstore_reader import RawStoreReader  # noqa: E402

# The guards, written once and used twice: to choose candidates, and again
# FOR UPDATE inside the swap, so a root extracted between the two is skipped.
_UNTOUCHED = """
       tc.child_count = 0
   AND NOT EXISTS (SELECT 1 FROM thread_extraction te WHERE te.thread_context_id = tc.id)
   AND NOT EXISTS (SELECT 1 FROM claim cl WHERE cl.thread_context_id = tc.id)
   AND NOT EXISTS (SELECT 1 FROM board_entry be
                    WHERE be.document_id = ANY(tc.member_document_ids))
"""

CANDIDATES = f"""
    SELECT tc.id, tc.thread_root_id, d.text_ref,
           coalesce((d.engagement->>'comments')::int, 0) AS platform_comments
      FROM thread_context tc JOIN document d ON d.id = tc.thread_root_id
     WHERE d.source = %s
       AND coalesce((d.engagement->>'comments')::int, 0) > 0
       AND {_UNTOUCHED}
     ORDER BY platform_comments DESC, tc.id
"""

LOCK = f"""
    SELECT tc.id FROM thread_context tc
     WHERE tc.id = %s AND {_UNTOUCHED}
       FOR UPDATE
"""


class _Refused(Exception):
    """Roll the swap back; the reason is recorded."""


def _house(obj) -> bytes:
    # `sort_keys=True, ensure_ascii=False`: the house spelling. The store is
    # content-addressed, so any other spelling is a second copy under a second
    # hash that the repair scripts cannot recognise.
    return json.dumps(obj.raw, ensure_ascii=False, sort_keys=True).encode("utf-8")


def backfill_one(conn, harvester, store, reader, tc_id: str, root: str,
                 text_ref: str | None) -> dict:
    """One root: fetch, store, then delete-and-reassemble in one transaction.

    Returns `{"outcome": ..., ...}`. Never raises for an outcome; a refused swap
    rolls back to exactly the row that was there.
    """
    from collect.adapters.reddit import _post_of
    from collect.adapters.reddit_write import write_documents

    rec: dict = {}
    payload = reader.resolve(text_ref) if text_ref else None
    if payload is None or not payload.found:
        rec["outcome"] = "root payload not in this machine's store"
    else:
        # The adapter's own parser, so the writer gets a real `RedditPost` with
        # every field `document_row` reads - not a stand-in carrying three.
        post = _post_of(json.loads(payload.require()))
        fetch = harvester.fetch_comments(post)
        if fetch.not_a_thread:
            rec["outcome"] = "not a thread (no permalink)"
        # A 429 is counted in `rate_limited`, not `http_errors` (review of
        # #503): without it a rate-limited root read as "no comments".
        elif (fetch.http_errors or fetch.rate_limited) and not fetch.comments:
            rec["outcome"] = "FETCH FAILED"
        elif not fetch.comments:
            rec["outcome"] = "platform returned no comments"
        else:
            refs = {}
            for obj in (post, *fetch.comments):
                stored = store.put(_house(obj), namespace=RAW)
                refs[obj.external_id] = (stored.ref, stored.content_hash)
            # `not_recorded`: no harvest_run row is opened by a
            # backfill, so claiming one would be invented.
            write_documents(conn, [post, *fetch.comments], refs=refs,
                            retrieval_provenance="not_recorded")
            conn.commit()
            rec["comments_fetched"] = len(fetch.comments)
            try:
                with conn.transaction():
                    if conn.execute(LOCK, (tc_id,)).fetchone() is None:
                        raise _Refused("extracted or rebuilt since selection")
                    conn.execute("DELETE FROM thread_context WHERE id = %s",
                                 (tc_id,))
                    built = assemble_reddit_documents(
                        conn, store=store, roots=[root])
                    if built.assembled != 1:
                        raise _Refused("reassembly refused: "
                                       + "; ".join(built.refusals)[:200])
                    if built.comments_selected == 0:
                        raise _Refused("reassembled with no reply selected")
                    rec["replies_selected"] = built.comments_selected
                rec["outcome"] = "rebuilt with replies"
            except _Refused as why:
                rec["outcome"] = f"left as it was: {why}"
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true",
                      help="list candidates; no network, no writes")
    mode.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--report-dir", default="_reddit_comment_backfill")
    args = ap.parse_args(argv)

    store = RawStore(Path(settings().raw_store_path))
    reader = RawStoreReader(store)

    if args.apply:
        # Refuses ENVIRONMENT=development against a database that is not this
        # machine, like every other write script here.
        from judge.writeguard import check as writeguard_check

        writeguard_check(settings().database_url, command="backfill_reddit_comments.py")

    with connect() as conn:
        rows = conn.execute(CANDIDATES, (REDDIT_SOURCE,)).fetchall()
        total = len(rows)
        if args.limit is not None:
            rows = rows[: args.limit]
        print(f"candidates: {total} body-only, never-extracted Reddit context(s) on "
              f"posts the platform says have comments; this run takes {len(rows)}")
        if args.dry_run:
            for _tc, root, _ref, n in rows[:20]:
                print(f"  {root}  platform comments {n}")
            print(f"  ...requests this would issue: up to {len(rows)}, one per root")
            return 0

        from collect.adapters.reddit import build_client, harvester_for_source
        from collect.registry.sources import load_sources

        contract = load_sources()
        source = next(s for s in contract.platforms if s.get("id") == "reddit")
        records: list[dict] = []
        tally: dict[str, int] = {}

        with build_client() as http:
            # The adapter's own gate (NFR-5): it raises if the terms ruling
            # does not hold, and nothing below runs.
            harvester = harvester_for_source(
                source, rulings=contract.rulings, client=http, store=store
            )
            for i, (tc_id, root, text_ref, platform_comments) in enumerate(rows, 1):
                rec = {"thread_context_id": tc_id, "root": root,
                       "platform_comments": platform_comments}
                records.append(rec)

                rec.update(backfill_one(conn, harvester, store, reader,
                                        tc_id, root, text_ref))
                tally[rec["outcome"]] = tally.get(rec["outcome"], 0) + 1
                if i % 25 == 0 or i == len(rows):
                    print(f"  {i}/{len(rows)}  " + ", ".join(
                        f"{k}: {v}" for k, v in sorted(tally.items())), flush=True)

    out = Path(args.report_dir)
    out.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = out / f"backfill-{stamp}.json"
    path.write_text(json.dumps({"taken": len(records), "of_candidates": total,
                                "outcomes": tally, "records": records},
                               indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"report: {path}")
    return 0 if not tally.get("FETCH FAILED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
