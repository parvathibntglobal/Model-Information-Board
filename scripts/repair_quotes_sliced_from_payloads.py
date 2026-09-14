#!/usr/bin/env python
"""Re-slice `claim.quote` for claims whose display text came from the payload.

WHAT WENT WRONG

`verify()` step 3 renders `raw_text_of[document_id][raw_start:raw_end]` and that
string is what `claim.quote` stores and the board publishes. The offsets index
the PROSE - `collect/assemble/flatten.py` builds the map's raw side against the
text `platforms.py` gave it, which is `prose.for_source(source)(payload)`.

`scripts/fetch_model.py` filled `raw_text_of` from `document.text_ref` instead.
That was correct when written on 2026-08-27 and stopped being correct at
2026-08-28 17:55, when the ruling made `text_ref` the payload. Every writer was
corrected; this reader, two stages away, kept the old meaning.

So ten claims from the 2026-09-14 run carry a slice of a JSON envelope as their
published quote, each with `quote_verified = true` - because verification
checked the MODEL's quote against the flattened prose and step 3 then
substituted a different string from a different artifact.

WHY THIS IS A RE-SLICE AND NOT A RE-EXTRACTION

`quote_raw_offset` is CODE-COMPUTED (`_resolve_raw_span`) and it is sound:
measured 2026-09-14, `prose(payload)[raw_offset]` reproduces the stored quote
EXACTLY on 148 of 148 checkable claims written through the export path. The
offsets were never the problem - the artifact they were applied to was. So the
repair reads the same offsets against the right text and no model is called.

WHAT THIS DELIBERATELY DOES NOT TOUCH

`quote_flat_offset`, which is a SEPARATE and still-open defect:
`judge/store/claims.py:246` stores `claim.quote_offset`, the MODEL's own hint,
rather than the located span `verify()` computed. It disagrees with
`quote_raw_offset` on 201 of 221 claims (91%), median 153 characters. It is
hashed into `claim_id`, so changing it changes claim identity - a decision, not
a repair, and not taken here.

    python scripts/repair_quotes_sliced_from_payloads.py --dry-run
    python scripts/repair_quotes_sliced_from_payloads.py --apply
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import io
import json
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

_UPDATE = "UPDATE claim SET quote = %(quote)s WHERE id = %(id)s"

SELECT = """
SELECT cl.id, cl.document_id, cl.quote, cl.quote_raw_offset, d.source, d.text_ref
FROM claim cl JOIN document d ON d.id = cl.document_id
ORDER BY cl.id
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
    before: dict[str, str] = {}
    skipped: list[str] = []

    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        rows = conn.execute(SELECT).fetchall()
        for cid, _did, quote, raw_range, source, text_ref in rows:
            if not text_ref or raw_range is None:
                continue
            outcome = reader.resolve(text_ref)
            if not outcome.found:
                continue                      # payload not on this host
            extract = prose.for_source(source)
            if extract is None:
                continue
            try:
                text = extract(outcome.require())
            except Exception:                 # noqa: BLE001 - NotAPayload
                continue
            lo, hi = raw_range.lower, raw_range.upper
            if hi > len(text):
                # NAMED, NOT SKIPPED SILENTLY. An offset past the end of the
                # prose means the map was built against something else, and
                # that is a different defect from this one.
                skipped.append(f"{cid}: raw span [{lo}:{hi}] exceeds prose of {len(text)}")
                continue
            # ONLY ROWS WHOSE CURRENT QUOTE IS NOT THE AUTHOR'S PROSE.
            #
            # THE FIRST DRAFT PLANNED EVERY ROW WHERE `text[lo:hi] != quote`
            # AND THAT WAS WRONG IN THE DANGEROUS DIRECTION. It planned 15 rows,
            # and 5 of them were already CORRECT quotes that the re-slice would
            # have corrupted by one character:
            #
            #   before  "overall quality and consistency I'd definitely put ab"
            #   after   " overall quality and consistency I'd definitely put a"
            #
            # `prose(payload)` today is not byte-identical to what the assembler
            # flattened for every platform - a separator or a strip differs by a
            # character - so the offsets are right for the text that was
            # flattened and one out against today's extraction. Re-slicing a
            # row that is already correct trades a real quote for a shifted one.
            #
            # The defect's signature is not "the slice disagrees". It is "the
            # published quote is not in the author's prose AT ALL", which is
            # what a payload slice looks like and what a one-character shift
            # does not. So the test is containment, not equality, and the
            # re-slice is applied only where there is nothing to lose.
            if quote in text:
                continue                      # already the author's words
            correct = text[lo:hi]
            if not correct.strip():
                skipped.append(f"{cid}: raw span [{lo}:{hi}] is blank in the prose")
                continue
            plan.append({"id": cid, "quote": correct})
            before[cid] = quote

    print(f"claims examined            : {len(rows)}")
    print(f"already correct or unchecked: {len(rows) - len(plan) - len(skipped)}")
    print(f"raw span exceeds the prose  : {len(skipped)}")
    for s in skipped[:5]:
        print(f"    {s}")
    print(f"to re-slice                 : {len(plan)}")
    print()
    print("THE STATEMENT, once per planned row:")
    print(f"    {_UPDATE}")
    print()
    for p in plan[:3]:
        print(f"    {p['id']}")
        print(f"      before {before[p['id']][:64]!r}")
        print(f"      after  {p['quote'][:64]!r}")

    if args.dry_run or not plan:
        print("\n--dry-run: nothing written." if args.dry_run else "\nnothing to do.")
        conn.close()
        return 0

    backup = ROOT / "var" / f"claim-quotes-before-{datetime.datetime.now():%Y%m%dT%H%M%S}.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(json.dumps({"statement": _UPDATE, "before": before,
                                  "after": {p["id"]: p["quote"] for p in plan}}, indent=2),
                      encoding="utf-8")
    print(f"\nbackup written: {backup}  ({len(before)} rows)")

    ids = [p["id"] for p in plan]
    total_before = conn.execute("SELECT count(*) FROM claim").fetchone()[0]
    untouched_before = conn.execute(
        "SELECT count(*) FROM claim WHERE NOT (id = ANY(%s))", (ids,)).fetchone()[0]
    verified_before = conn.execute(
        "SELECT count(*) FROM claim WHERE quote_verified").fetchone()[0]

    failures: list[str] = []
    with conn.cursor() as cur:
        cur.executemany(_UPDATE, plan)
        print(f"UPDATE applied, not yet committed: {len(plan)} row(s)")

        # ---- READ-BACK, INSIDE THE TRANSACTION ----
        got = dict(conn.execute(
            "SELECT id, quote FROM claim WHERE id = ANY(%s)", (ids,)).fetchall())
        for p in plan:
            if got.get(p["id"]) != p["quote"]:
                failures.append(f'{p["id"]}: quote is not the planned text')
        total_after = conn.execute("SELECT count(*) FROM claim").fetchone()[0]
        untouched_after = conn.execute(
            "SELECT count(*) FROM claim WHERE NOT (id = ANY(%s))", (ids,)).fetchone()[0]
        verified_after = conn.execute(
            "SELECT count(*) FROM claim WHERE quote_verified").fetchone()[0]
        if total_after != total_before:
            failures.append(f"claim count moved: {total_before} -> {total_after}")
        if untouched_after != untouched_before:
            failures.append("rows outside the plan changed")
        if verified_after != verified_before:
            failures.append("quote_verified changed; this repair must not touch it")

        # The point of the exercise: every repaired quote is now a substring of
        # the document's own prose. Checked here rather than trusted.
        still_bad = 0
        with contextlib.redirect_stderr(io.StringIO()):
            for cid, _did, _q, _rr, source, text_ref in rows:
                if cid not in got:
                    continue
                o = reader.resolve(text_ref)
                if not o.found:
                    continue
                if got[cid] not in prose.for_source(source)(o.require()):
                    still_bad += 1
        if still_bad:
            failures.append(f"{still_bad} repaired quote(s) are still not in the prose")

        print()
        print("READ-BACK INSIDE THE TRANSACTION")
        print(f"  rows matching the plan        : {len(plan) - len(failures)} of {len(plan)}")
        print(f"  repaired quotes now in prose  : {len(plan) - still_bad} of {len(plan)}")
        print(f"  claim rows total    {total_before} -> {total_after}")
        print(f"  rows outside plan   {untouched_before} -> {untouched_after}")
        print(f"  quote_verified      {verified_before} -> {verified_after}")

    if failures:
        conn.rollback()
        print(f"\nROLLED BACK. {len(failures)} check(s) failed:")
        for f in failures[:10]:
            print("   ", f)
        conn.close()
        return 1

    conn.commit()
    conn.close()
    print(f"\nCOMMITTED: {len(plan)} quote(s) re-sliced. Every check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
