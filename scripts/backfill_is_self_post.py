"""`document.is_self_post` from stored payloads. A backfill, not a re-fetch.

WHY THIS IS CHEAP, AND IT IS THE REASON THIS GATE WAS PICKED SECOND.
`is_self` is present in **100% of readable Reddit payloads** (measured
2026-09-08: 0 unknown of 1,362), and Hacker News answers from `type`, `text` and
`url`. So the value is already on this machine's disk - no request, no
inference, no dependency decision. The column landed in
`contract/migrations/20260908T1500_document_is_self_post.sql` and this fills it.

Compare the language gate, which is the same shape and is NOT cheap: no
platform in the stored corpus declares a language, so there is nothing to
backfill FROM and a detector would be an inference (rule 8: weight first).
`docs/the-three-dead-gates-2026-09-08.md` sets the two side by side.

    .venv\\Scripts\\python.exe scripts/backfill_is_self_post.py
    .venv\\Scripts\\python.exe scripts/backfill_is_self_post.py --write

DRY RUN BY DEFAULT. `DATABASE_URL` is the shared staging database and CLAUDE.md
requires a write session to be announced; `--write` is that announcement.

⚠  NULL IS AN ANSWER AND THIS SCRIPT WRITES IT AS ONE - by leaving it alone.
   Three states, and only two are ever written:

       true    a self/text post
       false   a LINK submission
       NULL    the platform has no such notion for this record. A blog
               article, a GitHub issue, and A COMMENT ON ANY PLATFORM.

   `pure_link_post` DROPS a link post with no commentary, so writing `false`
   where the answer is unknown would turn an absence into a droppable document
   (rule 6, on the gate that acts on the value). Every row this script cannot
   place is counted and named, never written.

⚠  THE RAW STORE IS PER MACHINE, so this backfills what THIS HOST can read.
   1,234 Reddit payloads are absent here with no tombstone
   (`docs/for-the-team-reddit-payloads-absent-2026-09-08.md`), and those rows
   stay NULL. The report says how many, because a backfill that silently
   skipped 41% of one platform would look like a platform with no link posts.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collect.adapters.hackernews import is_self_post_of as hn_is_self_post  # noqa: E402
from collect.adapters.reddit import is_self_post_of as reddit_is_self_post  # noqa: E402
from collect.config import settings  # noqa: E402
from collect.db import connect  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402

#: source -> the platform's own derivation. **A SOURCE ABSENT FROM THIS MAP HAS
#: NO SELF/LINK NOTION**, which is a fact about the platform and not a gap here:
#: a blog article and a GitHub issue are neither self posts nor link posts, and
#: `pure_link_post` returns NOT_APPLICABLE for their NULL forever.
DERIVERS = {"reddit": reddit_is_self_post, "hackernews": hn_is_self_post}

_SELECT = """
SELECT id, source, text_ref
FROM document
WHERE is_self_post IS NULL
  AND source = ANY(%(sources)s)
ORDER BY source, id
"""

#: Re-checks `IS NULL`, so two runs racing cannot half-write a row and a second
#: run is a no-op - the arrangement `collect/triage/store.py:_UPDATE` uses.
_UPDATE = """
UPDATE document SET is_self_post = %(is_self_post)s
WHERE id = %(id)s AND is_self_post IS NULL
"""


@dataclass
class BackfillRun:
    """What one pass did. Every count says what population it is over."""

    eligible: int = 0
    #: Payload read AND the platform's field present. The only rows written.
    placed: int = 0
    self_posts: int = 0
    link_posts: int = 0
    #: Payload read and the field ABSENT - a comment. Left NULL, and that NULL
    #: is the correct permanent answer rather than a gap.
    no_such_notion: int = 0
    #: Payload not on this host. LEFT NULL and counted apart from the line
    #: above, because one is a fact about the record and the other is a fact
    #: about this machine.
    unreadable: int = 0
    not_json: int = 0
    written: int = 0
    by_source: dict[str, dict[str, int]] = field(default_factory=dict)

    def _bump(self, source: str, key: str) -> None:
        self.by_source.setdefault(source, {})
        self.by_source[source][key] = self.by_source[source].get(key, 0) + 1

    def describe(self) -> str:
        if not self.eligible:
            return "nothing eligible: every row in scope already has a value"
        lines = [
            f"eligible {self.eligible}   placed {self.placed}   "
            f"(self {self.self_posts}, link {self.link_posts})",
            "  LEFT NULL, and the three reasons are different:",
            f"    no such notion (a comment)      {self.no_such_notion:>6}  "
            "correct and PERMANENT",
            f"    payload absent from this host   {self.unreadable:>6}  "
            "fixable elsewhere, not here",
            f"    payload present and not JSON    {self.not_json:>6}  "
            "a provenance defect",
            f"  written {self.written}",
        ]
        for source in sorted(self.by_source):
            counts = ", ".join(
                f"{k} {v}" for k, v in sorted(self.by_source[source].items())
            )
            lines.append(f"  {source}: {counts}")
        return "\n".join(lines)


def backfill(conn, store, *, dry_run: bool = True, batch: int = 200) -> BackfillRun:
    run = BackfillRun()
    rows = conn.execute(_SELECT, {"sources": list(DERIVERS)}).fetchall()
    run.eligible = len(rows)

    def _flush(pending: list[dict]) -> None:
        # `conn.commit()`, never `conn.transaction()` - autocommit is off, so a
        # nested transaction is a SAVEPOINT whose exit commits nothing. That
        # shape reported rows written and stored none once already.
        if dry_run or not pending:
            return
        for record in pending:
            conn.execute(_UPDATE, record)
        conn.commit()
        run.written += len(pending)

    pending: list[dict] = []
    for doc_id, source, ref in rows:
        run._bump(source, "eligible")
        try:
            blob = store.get_text(ref)
        except Exception:
            run.unreadable += 1
            run._bump(source, "unreadable")
            continue
        try:
            payload = json.loads(blob)
        except Exception:
            run.not_json += 1
            run._bump(source, "not_json")
            continue
        value = DERIVERS[source](payload)
        if value is None:
            run.no_such_notion += 1
            run._bump(source, "no_such_notion")
            continue
        run.placed += 1
        run._bump(source, "self_post" if value else "link_post")
        if value:
            run.self_posts += 1
        else:
            run.link_posts += 1
        pending.append({"id": doc_id, "is_self_post": value})
        if len(pending) >= batch:
            _flush(pending)
            pending = []
    _flush(pending)
    return run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--database-url", default=None)
    parser.add_argument(
        "--out", default="docs/measurements/is-self-post-backfill-2026-09-08.json"
    )
    args = parser.parse_args(argv)

    # THE WRITEGUARD, BEFORE THE CONNECTION (#328). The dsn arrives as an
    # argument here rather than from the environment, which is exactly why it
    # needs checking: `--database-url` defaults to DATABASE_URL and a caller
    # can also pass a shared host explicitly.
    from judge.writeguard import check as writeguard_check
    writeguard_check(args.database_url, command="backfill_is_self_post.py")

    store = RawStore(Path(settings().raw_store_path))
    conn = connect(args.database_url)
    try:
        run = backfill(conn, store, dry_run=not args.write)
    finally:
        conn.close()

    print(run.describe())
    payload = {
        "ran_at": datetime.now(UTC).isoformat(),
        "what": (
            "document.is_self_post from stored payloads - the platform's own "
            "field, never an inference. Fills the input pure_link_post has "
            "needed since it was written."
        ),
        "wrote": bool(args.write),
        "scope": (
            "reddit and hackernews only. Absent from DERIVERS means the platform "
            "has NO self/link notion (blog, github, arxiv, devto, huggingface, "
            "x) - a fact about the platform, so those rows stay NULL forever."
        ),
        "raw_store_caveat": (
            "The raw store is per machine. Rows whose payload is absent on this "
            "host stay NULL and are counted under `unreadable`."
        ),
        "eligible": run.eligible,
        "placed": run.placed,
        "self_posts": run.self_posts,
        "link_posts": run.link_posts,
        "left_null": {
            "no_such_notion_a_comment": run.no_such_notion,
            "payload_absent_from_this_host": run.unreadable,
            "payload_present_and_not_json": run.not_json,
        },
        "written": run.written,
        "by_source": run.by_source,
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwritten: {args.out}")
    if not args.write:
        print("DRY RUN. No row was changed. `--write` writes to the shared DB.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
