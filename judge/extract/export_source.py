"""Threads from an export carrying its own text, so a run has an input at all.

WHY THIS EXISTS, AND WHY IT IS A STOPGAP

`thread_context.flattened_text_ref` is a LOCATION in an object store, not the
text. `collect/rawstore.py` is the only reader and `judge/` never imports
`collect/` - asserted in both directions by `tests/test_lane_boundary.py` with no
allowlist. So this lane can be HANDED threads and cannot fetch them.

`_handoff/threads/*.json` is Engineer 1's export and carries `flattened_text`,
`offset_map` and `raw_text_of` inline. That is a real input, and it is the only
one this lane can read today.

**Named a stopgap rather than the interface, by agreement.** The durable fix is
one shared object-store reader that both lanes import - option 1 of three, taken
2026-08-20, and E1 is scoping what "shared" means for `rawstore.py`. When that
lands, `RawTextResolver` gets its implementation and this module becomes one of
two ways in rather than the only one.

WHAT IT DELIBERATELY DOES NOT DO

It does not guess. A thread missing `flattened_text` is reported by id and
skipped, never loaded with an empty string - an empty flattened text extracts to
nothing and would be indistinguishable from a thread that genuinely says
nothing. Same distinction `claims_written = 0` versus no row exists.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from judge.extract.runner import ThreadInput
from judge.extract.verify import OffsetMapping


@dataclass(frozen=True)
class LoadedExport:
    """What an export directory yielded, and what it could not."""

    threads: list[ThreadInput]

    #: Files that carried no usable text, by name and reason. Reported rather
    #: than counted: a run over 5 of 7 threads that says "7" is a yield figure
    #: with the wrong denominator.
    skipped: list[tuple[str, str]]

    #: Every document id the loaded threads refer to. The caller needs these to
    #: build `DocumentFacts`, and deriving them here keeps the two in step.
    document_ids: set[str]


def load(directory: Path) -> LoadedExport:
    """Read every `*.json` in `directory` as a thread with inlined text."""
    if not directory.is_dir():
        raise SystemExit(f"{directory} is not a directory")

    threads: list[ThreadInput] = []
    skipped: list[tuple[str, str]] = []
    document_ids: set[str] = set()

    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            skipped.append((path.name, f"unreadable: {exc}"))
            continue

        text = payload.get("flattened_text")
        if not isinstance(text, str) or not text.strip():
            # NOT loaded as an empty string. An empty flattened text extracts to
            # nothing, which is indistinguishable from a thread that says
            # nothing - and one is a broken input while the other is a finding.
            skipped.append((path.name, "no flattened_text; a missing input, not an empty thread"))
            continue

        thread_id = payload.get("thread_context_id")
        if not isinstance(thread_id, str) or not thread_id:
            skipped.append((path.name, "no thread_context_id; the ledger row would have no key"))
            continue

        # TYPED, not raw dicts. `verify()` calls `.overlaps(start, end)` on each
        # entry, so a list of dicts reaches step 2 and raises AttributeError
        # mid-run - AFTER the model call has been paid for. `ThreadInput`
        # annotates `tuple[OffsetMapping, ...]` and nothing enforced it, so the
        # test passed with proper objects while this loader handed over dicts:
        # a variable the test supplies is a variable the test cannot check.
        try:
            offset_map = tuple(OffsetMapping(**span) for span in payload.get("offset_map") or ())
        except TypeError as exc:
            skipped.append((path.name, f"offset_map entry does not match OffsetMapping: {exc}"))
            continue
        raw_text_of = payload.get("raw_text_of") or {}
        if not raw_text_of:
            # Step 3 renders the RAW span. Without `raw_text_of` a verified quote
            # cannot be displayed as written, so the claim would pass
            # verification and be unrenderable.
            skipped.append(
                (path.name, "no raw_text_of; quotes could be verified and never displayed")
            )
            continue

        threads.append(
            ThreadInput(
                thread_context_id=thread_id,
                flattened_text=text,
                offset_map=offset_map,
                raw_text_of=raw_text_of,
            )
        )
        document_ids.update(payload.get("member_document_ids") or [])

    return LoadedExport(threads=threads, skipped=skipped, document_ids=document_ids)
