#!/usr/bin/env python
"""Re-slice `board_entry.quote` for entries whose published text came from the payload.

WHY THIS EXISTS SEPARATELY FROM THE CLAIM REPAIR

`scripts/repair_quotes_sliced_from_payloads.py` repairs `claim.quote`. It is
correct and it does not reach the board, because **the page does not read
`claim.quote`**. `board_entry.quote` is a SECOND COPY of the text, written by
`judge/store/board_entries.py:157` at extraction time, and `board_sections()` -
everything the Board and model pages render - reads that copy.

So the claim repair leaves the published page byte-for-byte unchanged. Measured
2026-09-14 against staging: 34 of 64 `board_entry` rows carry a slice of a JSON
envelope, which is what a reader sees today.

Same defect as #274, same cause, one table over.

WHY THE ID MOVES TOO, AND WHY THAT IS THE SAFE DIRECTION

`board_entry.id` is `entry_id(document_id, section, slug, quote, pipeline_version)`
- a content hash that INCLUDES the quote - and the insert is
`ON CONFLICT (id) DO NOTHING`. Repairing the quote without the id would leave a
row whose id no longer describes its content, and the next correct run would
compute the RIGHT hash, miss the conflict, and append a second row beside this
one. The reader would then see the finding twice.

Recomputing the id makes the repaired row byte-identical to what the fixed
pipeline would have written, so that run conflicts and appends nothing. Nothing
holds a foreign key to `board_entry.id` (checked: 0 referencing constraints), so
the update is a key change with no dependents.

THE ID DERIVATION IS VERIFIED BEFORE IT IS TRUSTED, NOT ASSUMED. Every planned
row must reproduce its STORED id from its STORED fields first. If one does not,
the inputs are not what this script believes and it refuses the whole run rather
than inventing a key. Measured before writing: 64 of 64 reproduce.

WHAT IT DELIBERATELY DOES NOT DO

- It does not touch `quote_verified`. These quotes WERE verified against the
  flattened prose; the defect is that a different string was then displayed.
- It does not touch `claim.quote` - that is the other script's job.
- It does not delete or decline anything. A `ruling` applies to a whole
  (section, slug), and 6 of 21 groups here hold broken AND good rows, so
  declining would take 21 sound quotes off the board with the 24 bad ones.
  That is the caused-absence rule, so the rows are repaired, not hidden.

    python scripts/repair_board_entry_quotes.py --dry-run
    python scripts/repair_board_entry_quotes.py --apply
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import io
import json
import logging
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
    if m:
        os.environ.setdefault(m.group(1), m.group(2))

import psycopg  # noqa: E402

from collect.assemble import prose  # noqa: E402
from collect.config import settings  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.rawstore_reader import RawStoreReader  # noqa: E402
from judge.store.board_entries import entry_id  # noqa: E402

_UPDATE = "UPDATE board_entry SET id = %(new_id)s, quote = %(quote)s WHERE id = %(id)s"

SELECT = """
SELECT be.id, be.document_id, be.section, be.slug, be.quote, be.pipeline_version,
       be.claim_id, cl.quote_raw_offset, d.source, d.text_ref
FROM board_entry be
LEFT JOIN claim cl ON cl.id = be.claim_id
LEFT JOIN document d ON d.id = be.document_id
ORDER BY be.id
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    reader = RawStoreReader(RawStore(settings().raw_store_path))
    conn = psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=10)

    plan: list[dict[str, str]] = []
    before: dict[str, dict[str, str]] = {}
    skipped: list[str] = []
    unreadable = 0

    # A MISSING PAYLOAD IS EXPECTED HERE. The raw store is per-machine and the
    # database is shared, so a row this host cannot read is a fact about this
    # host. Declaring that here keeps the reader's warning out of the summary,
    # the same arrangement as collect/assemble/dedupe_write.py.
    store_log = logging.getLogger("collect.rawstore")
    previous = store_log.level
    store_log.setLevel(logging.CRITICAL)
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            rows = conn.execute(SELECT).fetchall()
            existing_ids = {r[0] for r in rows}
            for bid, did, section, slug, quote, pv, clid, rr, source, tref in rows:
                if not clid or rr is None or not tref:
                    continue
                outcome = reader.resolve(tref)
                if not outcome.found:
                    unreadable += 1
                    continue
                extract = prose.for_source(source)
                if extract is None:
                    continue
                try:
                    text = extract(outcome.require())
                except Exception:  # noqa: BLE001 - NotAPayload
                    continue
                lo, hi = rr.lower, rr.upper
                if hi > len(text):
                    skipped.append(f"{bid}: raw span [{lo}:{hi}] exceeds prose of {len(text)}")
                    continue
                # CONTAINMENT, NOT EQUALITY - the criterion #274 settled on.
                # `prose(payload)` today can differ from what the assembler
                # flattened by a separator or a strip, so a row whose quote IS
                # the author's words is already right and re-slicing it would
                # trade a real quote for one shifted by a character.
                if quote in text:
                    continue
                correct = text[lo:hi]
                if not correct.strip():
                    skipped.append(f"{bid}: raw span [{lo}:{hi}] is blank in the prose")
                    continue

                # THE ID DERIVATION IS PROVEN PER ROW BEFORE IT IS USED.
                reproduced = entry_id(document_id=did, section=section, slug=slug,
                                      quote=quote, pipeline_version=pv)
                if reproduced != bid:
                    skipped.append(
                        f"{bid}: stored id does not reproduce from stored fields "
                        f"(got {reproduced}); refusing to recompute a key whose "
                        f"inputs are not understood"
                    )
                    continue
                new_id = entry_id(document_id=did, section=section, slug=slug,
                                  quote=correct, pipeline_version=pv)
                if new_id in existing_ids:
                    # The corrected entry is ALREADY in the table, so this row is
                    # a duplicate of it rather than a row to repair. Updating
                    # would collide on the primary key. Named, not swallowed.
                    skipped.append(
                        f"{bid}: the repaired form already exists as {new_id}; "
                        f"this row is a duplicate and needs a person's ruling, "
                        f"not a re-slice"
                    )
                    continue
                plan.append({"id": bid, "new_id": new_id, "quote": correct})
                before[bid] = {"quote": quote, "section": section, "slug": slug}
    finally:
        store_log.setLevel(previous)

    print(f"board_entry rows examined     : {len(rows)}")
    print(f"payload unreadable on this host: {unreadable}")
    print(f"already the author's prose    : "
          f"{len(rows) - len(plan) - len(skipped) - unreadable}")
    print(f"named and skipped             : {len(skipped)}")
    for s in skipped[:5]:
        print(f"    {s}")
    print(f"to re-slice                   : {len(plan)}")
    print()
    print("THE STATEMENT, once per planned row:")
    print(f"    {_UPDATE}")
    print()
    for p in plan[:3]:
        b = before[p["id"]]
        print(f"    {p['id']} -> {p['new_id']}   [{b['section']}/{b['slug']}]")
        print(f"      before {b['quote'][:64]!r}")
        print(f"      after  {p['quote'][:64]!r}")

    if args.dry_run or not plan:
        print("\n--dry-run: nothing written." if args.dry_run else "\nnothing to do.")
        conn.close()
        return 0

    backup = ROOT / "var" / f"board-entry-quotes-before-{datetime.datetime.now():%Y%m%dT%H%M%S}.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(
        json.dumps({"statement": _UPDATE, "before": before,
                    "after": {p["id"]: {"new_id": p["new_id"], "quote": p["quote"]}
                              for p in plan}}, indent=2),
        encoding="utf-8")
    print(f"\nbackup written: {backup}  ({len(before)} rows)")

    old_ids = [p["id"] for p in plan]
    new_ids = [p["new_id"] for p in plan]
    total_before = conn.execute("SELECT count(*) FROM board_entry").fetchone()[0]
    untouched_before = conn.execute(
        "SELECT count(*) FROM board_entry WHERE NOT (id = ANY(%s))", (old_ids,)).fetchone()[0]
    verified_before = conn.execute(
        "SELECT count(*) FROM board_entry WHERE quote_verified").fetchone()[0]
    ruled_before = conn.execute(
        "SELECT count(*) FROM board_entry WHERE ruling IS NOT NULL").fetchone()[0]

    failures: list[str] = []
    with conn.cursor() as cur:
        cur.executemany(_UPDATE, plan)
        print(f"UPDATE applied, not yet committed: {len(plan)} row(s)")

        # ---- READ-BACK, INSIDE THE TRANSACTION ----
        got = dict(conn.execute(
            "SELECT id, quote FROM board_entry WHERE id = ANY(%s)", (new_ids,)).fetchall())
        for p in plan:
            if got.get(p["new_id"]) != p["quote"]:
                failures.append(f'{p["new_id"]}: quote is not the planned text')
        total_after = conn.execute("SELECT count(*) FROM board_entry").fetchone()[0]
        untouched_after = conn.execute(
            "SELECT count(*) FROM board_entry WHERE NOT (id = ANY(%s))", (new_ids,)).fetchone()[0]
        verified_after = conn.execute(
            "SELECT count(*) FROM board_entry WHERE quote_verified").fetchone()[0]
        ruled_after = conn.execute(
            "SELECT count(*) FROM board_entry WHERE ruling IS NOT NULL").fetchone()[0]
        if total_after != total_before:
            failures.append(f"board_entry count moved: {total_before} -> {total_after}")
        if untouched_after != untouched_before:
            failures.append("rows outside the plan changed")
        if verified_after != verified_before:
            failures.append("quote_verified changed; this repair must not touch it")
        if ruled_after != ruled_before:
            failures.append("a ruling changed; this repair must not touch a person's decision")

        # EVERY REPAIRED ID MUST NOW DESCRIBE ITS OWN CONTENT. That is the whole
        # reason the id moves, so it is checked rather than trusted.
        for bid, did, section, slug, _q, pv, *_rest in conn.execute(SELECT).fetchall():
            if bid not in got:
                continue
            if entry_id(document_id=did, section=section, slug=slug,
                        quote=got[bid], pipeline_version=pv) != bid:
                failures.append(f"{bid}: id does not hash its own repaired content")

        # And every repaired quote must be the author's prose.
        still_bad = 0
        store_log.setLevel(logging.CRITICAL)
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                for bid, _d, _s, _sl, _q, _pv, _cl, _rr, source, tref in conn.execute(
                        SELECT).fetchall():
                    if bid not in got or not tref:
                        continue
                    o = reader.resolve(tref)
                    if not o.found:
                        continue
                    ex = prose.for_source(source)
                    if ex is None:
                        continue
                    try:
                        if got[bid] not in ex(o.require()):
                            still_bad += 1
                    except Exception:  # noqa: BLE001
                        continue
        finally:
            store_log.setLevel(previous)
        if still_bad:
            failures.append(f"{still_bad} repaired quote(s) are still not in the prose")

        print()
        print("READ-BACK INSIDE THE TRANSACTION")
        print(f"  rows matching the plan        : {len(plan) - len(failures)} of {len(plan)}")
        print(f"  repaired quotes now in prose  : {len(plan) - still_bad} of {len(plan)}")
        print(f"  board_entry rows total {total_before} -> {total_after}")
        print(f"  rows outside plan      {untouched_before} -> {untouched_after}")
        print(f"  quote_verified         {verified_before} -> {verified_after}")
        print(f"  rows carrying a ruling {ruled_before} -> {ruled_after}")

    if failures:
        conn.rollback()
        print(f"\nROLLED BACK. {len(failures)} check(s) failed:")
        for f in failures[:10]:
            print("   ", f)
        conn.close()
        return 1

    conn.commit()
    conn.close()
    print(f"\nCOMMITTED: {len(plan)} board quote(s) re-sliced. Every check passed.")
    print(f"Restore with: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
