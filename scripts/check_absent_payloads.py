"""Does THIS host's raw store hold the 1,234 Reddit blobs the 2026-09-08 audit missed?

    py -3 scripts/check_absent_payloads.py

One command, no database, no network. It reads the hash list the audit already
committed and asks the filesystem. Run it on every machine that has ever run a
Reddit script; the answer is a count, and a count from each store settles it.

WHY THIS IS A SCRIPT AND NOT A PASTED SNIPPET
----------------------------------------------
`docs/for-the-team-reddit-payloads-absent-2026-09-08.md` §5 asked three people
to "check your own store", and the check was a paragraph describing how. Three
people writing the same loop is three chances to compare the wrong column -
`content_hash` is identity and `text_ref` is location, and the store is keyed by
the second. This asks the same question the same way everywhere.

WHAT THE ANSWER MEANS, BOTH WAYS
---------------------------------
The refs are CONTENT ADDRESSES, valid on every host - `scripts/
write_reddit_thread.py` says so in its own docstring, and predicted this exact
symptom: *"whether the BLOB is present is a separate fact about a particular
store ... that is the store being host-specific, not the refs being wrong."*

    a non-zero count   NFR-4 holds and the fix is a FILE COPY, not a re-fetch.
                       Copy `raw/sha256/**` for the listed refs; the refs in
                       the shared database already point at them.

    zero on every host The bytes are gone, and those 1,234 documents can never
                       be re-verified or re-extracted without re-fetching the
                       23 threads. That is a `reddit-via-rapidapi` spend, and it
                       is the decision this check exists to inform rather than
                       to pre-empt.

⚠  A ZERO HERE IS NOT AN ANSWER ON ITS OWN. This host reported 0 of 1,234 on
   2026-09-10, and that is the expected reading for a machine that never ran
   `write_reddit_thread.py` - which is the whole point. Absence on one store is
   evidence about that store (rule 7: the population is one machine).
"""

from __future__ import annotations

import json
import socket
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.config import settings  # noqa: E402

AUDIT = Path("docs/measurements/reddit-absent-payloads-2026-09-08.json")


def main() -> int:
    if not AUDIT.exists():
        print(f"{AUDIT} is missing, so there is no hash list to check against.",
              file=sys.stderr)
        return 2
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    store = settings().raw_store_path
    rows = audit["absent"]

    present = [r for r in rows if (store / r["text_ref"]).exists()]
    missing = [r for r in rows if not (store / r["text_ref"]).exists()]

    print(f"host           {socket.gethostname()}")
    print(f"RAW_STORE_PATH {store.resolve()}")
    print(f"audit          {AUDIT}  ({audit['measured_at'][:10]})")
    print()
    print(f"  blobs PRESENT in this store   {len(present):>6,} of {len(rows):,}")
    print(f"  blobs absent                  {len(missing):>6,} of {len(rows):,}")
    print()

    kinds = Counter("comment" if r["is_comment"] else "post" for r in present)
    if present:
        print("  present, by kind:")
        for kind, count in sorted(kinds.items()):
            print(f"     {kind:<9} {count:>6,}")
        print()
        print("  >> NFR-4 HOLDS. The fix is a file copy, not a re-fetch. These refs")
        print("     are already correct in the shared database; only the objects")
        print("     need to travel. Copy them and re-run this on the other host.")
    else:
        print("  >> NOTHING HERE. Expected on a machine that never ran")
        print("     scripts/write_reddit_thread.py - it stores each comment body")
        print("     into the LOCAL raw store, and the store is per-host and")
        print("     gitignored. This is evidence about THIS store only; the")
        print("     question stays open until every host has answered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
