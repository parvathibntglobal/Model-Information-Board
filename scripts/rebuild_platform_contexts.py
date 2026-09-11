"""Rebuild dev.to / Hacker News / Hugging Face contexts holding JSON instead of prose.

THE SAME DEFECT `rebuild_github_contexts.py` REPAIRED, one assembler over.
`collect/assemble/platforms.py` flattened each document's payload VERBATIM, so
a Hacker News thread reached the classifier as

    {"author":"simplybeing1","children":[{"author":"simplybeing1","children":[]…

with HTML entities intact (`&#x27;`, `&#x2F;`). The prose is inside the JSON, so
a quote of it verifies by exact substring and `quote_verified` is true — rule 1
returning true for the wrong reason, with offsets pointing into an API response.

WHAT IT COST, measured on the one context anybody has looked at closely. The
model read 3,364 characters of escaped JSON where 1,100 characters of prose
existed. Its three quotes came out with the governing clause stripped:

    stored   "Fable 5.1 agent shot and killed the man with gold in 2 of 20…"
    source   "WHEN NO ONE IS WATCHING, Fable 5.1 agent shot and killed…"

The experiment's entire finding is observed-versus-unobserved behaviour, and
that clause sat in a different escaped fragment from the figure it governs.

`platforms.py` now extracts through `collect/assemble/prose.py` before
flattening, and refuses a source with no extractor rather than passing bytes
through. This rebuilds what the old path produced.

A CONTEXT WITH CLAIMS IS EXCLUDED, NOT REBUILT. Re-flattening moves every
character position, and an offset cannot be recomputed afterwards
(`collect/CLAUDE.md`, first rule). Deleting the claim to make room would
discard verified evidence. So each such context is NAMED and skipped, and the
repair for those is re-extraction — a decision with a cost, not a side effect
of this script.

That differs deliberately from the github script, which refused the whole run:
there, every context was claim-free or none were. Here 2 of 86 carry claims, and
refusing all 86 would leave 84 repairable contexts broken to protect 2.

    python scripts/rebuild_platform_contexts.py --dry-run
    python scripts/rebuild_platform_contexts.py --apply

NO NETWORK, NO MODEL, NO SPEND. It reads payloads already on this machine and
re-runs a pure function over them.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collect.assemble.platforms import PLATFORMS, assemble_platform_documents  # noqa: E402
from collect.config import settings  # noqa: E402
from collect.db import connect  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.rawstore_reader import RawStoreReader  # noqa: E402

#: The sources `assemble_platform_documents` owns. GitHub and Reddit have their
#: own assemblers and their own rebuild path.
SOURCES = tuple(sorted(PLATFORMS))

_CONTEXTS = (
    "SELECT tc.id, tc.flattened_text_ref, d.source "
    "FROM thread_context tc "
    "JOIN document d ON d.id = tc.thread_root_id "
    "WHERE d.source = ANY(%s)"
)


def looks_like_json(text: str) -> bool:
    """PARSES rather than sniffs, for the reason the github script recorded.

    A leading `[` is not evidence: 39 rebuilt contexts were flagged by a
    first-character check and every one was prose, because the flattener
    substitutes emoji as shortcodes and titles begin `[bar_chart] …`. Sniffing
    produced a 100% false-positive rate on real data.

    Extended here for the ONE shape that script did not meet: this flattener
    joins several payloads with a `\\n---\\n` separator, so the whole file is
    not valid JSON even when every part of it is. The first part decides.
    """
    head = text.lstrip()[:1]
    if head not in {"{", "["}:
        return False
    first = text.split("\n---\n")[0].strip()
    for candidate in (text, first):
        try:
            if isinstance(json.loads(candidate), dict | list):
                return True
        except ValueError:
            continue
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not SOURCES:
        print("no platform sources are configured; nothing to do")
        return 0

    conn = connect()
    store = RawStore(settings().raw_store_path)
    reader = RawStoreReader(store)

    rows = conn.execute(_CONTEXTS, (list(SOURCES),)).fetchall()
    print(f"platform thread_context rows ({', '.join(SOURCES)}): {len(rows)}")

    envelope: list[tuple[str, str]] = []
    prose = unresolved = 0
    for tc_id, flat_ref, source in rows:
        outcome = reader.resolve(flat_ref) if flat_ref else None
        if outcome is None or not outcome.found:
            unresolved += 1
        elif looks_like_json(outcome.require()):
            envelope.append((tc_id, source))
        else:
            prose += 1
    print(f"  flattened text is a JSON envelope: {len(envelope)}")
    print(f"  flattened text is prose          : {prose}")
    print(f"  did not resolve on this machine  : {unresolved}")

    ids = [tc for tc, _ in envelope]
    if not ids:
        print("\nnothing to rebuild.")
        conn.close()
        return 0

    # ── EXCLUDE ANYTHING A CLAIM OR AN EXTRACTION DEPENDS ON ────────────────
    claimed = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT thread_context_id FROM claim WHERE thread_context_id = ANY(%s)",
            (ids,)).fetchall()
    }
    extracted = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT thread_context_id FROM thread_extraction "
            "WHERE thread_context_id = ANY(%s)", (ids,)).fetchall()
    }
    blocked = claimed | extracted
    rebuildable = [tc for tc in ids if tc not in blocked]

    if blocked:
        print(f"\n  EXCLUDED, because rows depend on them ({len(blocked)}):")
        for tc in sorted(blocked):
            n = conn.execute(
                "SELECT count(*) FROM claim WHERE thread_context_id = %s", (tc,)
            ).fetchone()[0]
            print(f"    {tc}  {n} claim(s)")
        print("    Re-flattening moves every offset and an offset cannot be "
              "recomputed, so these are left exactly as they are. The repair "
              "for them is re-extraction, which costs model spend and is a "
              "decision rather than a side effect of this script.")

    print(f"\n  to rebuild: {len(rebuildable)}")
    if args.dry_run:
        print(f"\n--dry-run: would delete {len(rebuildable)} context(s) and "
              "re-assemble them from payloads already on this machine. "
              "Nothing written, no network, no model.")
        conn.close()
        return 0

    if not rebuildable:
        print("\nnothing rebuildable; leaving the database untouched.")
        conn.close()
        return 0

    # `thread_context.id` is derived from the root document and the pipeline
    # version, so the rebuild reuses the same id. The delete is what lets the
    # assembler see the document as a candidate again — it selects on NOT EXISTS.
    with conn.cursor() as cur:
        cur.execute("DELETE FROM thread_context WHERE id = ANY(%s)", (rebuildable,))
        deleted = cur.rowcount
    print(f"\ndeleted {deleted} context row(s) — derived rows, regenerated below")

    # PER SOURCE. The assembler takes one source and selects roots with no
    # context, so it has to be called once for each - and only for the sources
    # that actually had an envelope, to keep the blast radius to what was
    # deleted rather than assembling every unassembled document on the machine.
    touched = sorted({src for tc, src in envelope if tc in set(rebuildable)})
    print(f"re-assembling: {', '.join(touched)}")
    roots = assembled = 0
    refusals: list[str] = []
    for src in touched:
        report = assemble_platform_documents(conn, source=src, store=store)
        roots += report.roots
        assembled += report.assembled
        refusals.extend(report.refusals or [])
        print(f"    {src:12} roots={report.roots} assembled={report.assembled} "
              f"(article {report.as_article}, thread {report.as_thread})")
    conn.commit()
    print(f"roots seen : {roots}")
    print(f"assembled  : {assembled}")
    if refusals:
        print(f"refusals   : {len(refusals)}")
        for line in refusals[:6]:
            print(f"    {line[:150]}")

    # VERIFY IN THE SAME RUN. A rebuild that reports success while leaving
    # envelopes behind is the defect wearing a green tick.
    still = []
    for tc_id, flat_ref, _source in conn.execute(_CONTEXTS, (list(SOURCES),)).fetchall():
        outcome = reader.resolve(flat_ref) if flat_ref else None
        if outcome is not None and outcome.found and looks_like_json(outcome.require()):
            still.append(tc_id)
    remaining = [tc for tc in still if tc not in blocked]
    print(f"\nverify: {len(still)} envelope(s) remain "
          f"({len(blocked)} deliberately excluded, {len(remaining)} unexpected)")
    return 1 if remaining else 0


if __name__ == "__main__":
    raise SystemExit(main())
