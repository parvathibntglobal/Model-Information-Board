"""Export real `thread_context` rows in the shape `judge/extract` can load.

WHY THIS EXISTS AND WHY IT IS NOT `export_thread_contexts.py`

`judge extract` refuses to read thread text from the database, deliberately:
`thread_context.flattened_text_ref` is a LOCATION in an object store,
`collect/rawstore.py` is the only reader, and `judge/` never imports `collect/`.
So the pipeline can be HANDED threads and cannot fetch them. That is the lane
interface working, not a gap to route around.

`scripts/export_thread_contexts.py` looks like the exporter for this and is not:
it re-derives blog articles by scanning `raw_store` for HTML and re-assembling
them. It never reads a `thread_context` row. Run with `--all` against a database
holding 1,512 reddit contexts it emitted 128 blog threads, because reddit is not
a shape it builds.

**This reads the rows.** `thread_context` for the flattened ref and the offset
map, then each member document's `text_ref` for `raw_text_of`, then one JSON file
per thread in the shape `export_source.load` parses.

WHAT IT REFUSES RATHER THAN DEFAULTS

Every one of these is a case `export_source.load` would otherwise skip after the
model call was already paid for, or worse, load as an empty thread:

    no flattened_text_ref        the row exists and its text does not
    ref does not resolve         a missing payload is a missing document
    empty flattened text         extracts to nothing, indistinguishable from a
                                 thread that says nothing
    no member raw text           step 3 renders the RAW span, so a quote could
                                 verify and be unrenderable
    offset_map empty             `verify` has nothing to map a span through

Named and counted, never written as a partial file.

    python scripts/export_contexts_for_extract.py --out DIR [--limit N]
                                                  [--selection-method post_body_only]
"""

from __future__ import annotations

import argparse
import json
import pathlib

from collect.assemble.prose import (
    NotAPayload,
    github_issue_prose,
    reddit_prose,
)
from collect.config import settings
from collect.rawstore import RawStore
from collect.rawstore_reader import RawStoreReader

#: `document.source` -> how to get prose out of that platform's payload. A
#: source with no entry is passed through unchanged: blog `text_ref` is HTML and
#: `extract_article_text` is not importable here, so blog exports are not this
#: script's business.
_EXTRACTORS = {
    "reddit": reddit_prose,
    "github": github_issue_prose,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--selection-method", default=None,
        help="restrict to one selection_method, e.g. post_body_only",
    )
    parser.add_argument(
        "--pipeline-version", default=None,
        help="restrict to contexts assembled at this pipeline_version. Added "
             "2026-08-31, when 584 GitHub issues gained a second context under "
             "a fork: without it, --skip-extracted selects both the body-only "
             "row and its with-comments fork and the same issue body is "
             "extracted twice. See the comment on --skip-extracted.",
    )
    parser.add_argument(
        "--skip-extracted", action="store_true",
        help="omit threads already in `thread_extraction` at this pipeline "
             "version. The extractor skips them anyway; this keeps the export "
             "honest about what it is offering.",
    )
    args = parser.parse_args()

    out_dir = pathlib.Path(args.out) / "threads"
    out_dir.mkdir(parents=True, exist_ok=True)
    reader = RawStoreReader(RawStore(settings().raw_store_path))

    from collect.db import connect

    conn = connect()
    try:
        clauses = ["tc.flattened_text_ref IS NOT NULL"]
        params: list[object] = []
        if args.selection_method:
            clauses.append("tc.selection_method = %s")
            params.append(args.selection_method)
        if args.pipeline_version:
            clauses.append("tc.pipeline_version = %s")
            params.append(args.pipeline_version)
        if args.skip_extracted:
            # ⚠ `--skip-extracted` IS NOT ENOUGH ON ITS OWN SINCE 2026-08-31,
            #   AND ADDING `--selection-method` OR `--pipeline-version` IS.
            #
            #   584 GitHub issues now hold TWO contexts: the original
            #   `issue_body_only` at `collect-0.1.0`, and an
            #   `issue_with_comments` fork at `collect-0.2.0-issue-comments`.
            #   The fork was deliberate - re-assembling in place would have
            #   destroyed the offsets of claims already written against the
            #   body-only rows (`scripts/write_github_comments.py`).
            #
            #   NEITHER HAS A `thread_extraction` ROW, so this clause selects
            #   BOTH, and the fork's flattened text is a SUPERSET of the
            #   body-only one - it is the same issue body plus its comments. The
            #   extractor would read the body twice, under two context ids, and
            #   two claims quoting one issue body is ONE AUTHOR COUNTED AS TWO
            #   VOICES.
            #
            #   That is precisely the failure the comment path exists to
            #   prevent, arriving from the other side: `assemble_issue_thread`
            #   refuses bots as members and `gate.count` takes one
            #   representative per author, and both are defeated if the same
            #   person's text enters twice under different ids.
            #
            #   The collision is COUNTED AND PRINTED below rather than filtered
            #   here, because which version the board should read is a ruling
            #   and not this script's to take.
            clauses.append(
                "NOT EXISTS (SELECT 1 FROM thread_extraction te "
                "WHERE te.thread_context_id = tc.id)"
            )
        rows = conn.execute(
            "SELECT tc.id, tc.thread_root_id, tc.member_document_ids, "
            "       tc.flattened_text_ref, tc.offset_map, tc.selection_method, "
            "       tc.hidden_children_min, d.source "
            "FROM thread_context tc "
            "JOIN document d ON d.id = tc.thread_root_id "
            "WHERE " + " AND ".join(clauses) + " ORDER BY tc.id"
            + (f" LIMIT {int(args.limit)}" if args.limit else ""),
            tuple(params),
        ).fetchall()

        # THE COLLISION, COUNTED. One thread_root_id appearing twice means the
        # same issue body is about to be extracted under two context ids. See
        # the `--skip-extracted` comment above for why that is a voice defect
        # rather than a duplication nuisance.
        _roots: dict[str, list[str]] = {}
        for _r in rows:
            _roots.setdefault(_r[1], []).append(_r[5])
        _doubled = {root: methods for root, methods in _roots.items() if len(methods) > 1}
        if _doubled:
            _shapes: dict[str, int] = {}
            for methods in _doubled.values():
                _shapes["+".join(sorted(methods))] = (
                    _shapes.get("+".join(sorted(methods)), 0) + 1
                )
            print(
                f"!! {len(_doubled)} thread_root_id(s) appear TWICE in this "
                f"selection. The same document text would be extracted under two "
                f"context ids, and one author would be counted as two voices."
            )
            for shape, n in sorted(_shapes.items(), key=lambda kv: -kv[1]):
                print(f"     {n:5d}  {shape}")
            print(
                "   Narrow with --selection-method or --pipeline-version. "
                "Exporting anyway: which version the board reads is a ruling, "
                "not this script's call."
            )

        text_of: dict[str, str] = {}
        wanted = {m for r in rows for m in (r[2] or [])}
        if wanted:
            for doc_id, source, ref in conn.execute(
                "SELECT id, source, text_ref FROM document WHERE id = ANY(%s)",
                (list(wanted),),
            ).fetchall():
                if not ref:
                    continue
                outcome = reader.resolve(ref)
                if not outcome.found:
                    continue
                # PROSE, NOT THE PAYLOAD. `text_ref` points at the bytes the
                # platform gave us since the content_hash ruling, and
                # `raw_text_of` is what step 3 renders a verified quote FROM.
                # Handing it the envelope would display a JSON span - the same
                # defect one layer further on, and the layer a reader sees.
                extract = _EXTRACTORS.get(source)
                if extract is None:
                    text_of[doc_id] = outcome.require()
                    continue
                try:
                    text_of[doc_id] = extract(outcome.require())
                except NotAPayload:
                    # SKIPPED, so the thread is refused below by
                    # "no member raw text" rather than exported with an
                    # envelope in it.
                    continue
    finally:
        conn.close()

    written = 0
    refused: dict[str, int] = {}

    def refuse(reason: str) -> None:
        refused[reason] = refused.get(reason, 0) + 1

    for (thread_id, root_id, members, flat_ref, offset_map,
         selection_method, hidden_min, source) in rows:
        outcome = reader.resolve(flat_ref)
        if not outcome.found:
            refuse(f"flattened text did not resolve ({outcome.outcome})")
            continue
        flattened = outcome.require()
        if not flattened.strip():
            refuse("flattened text is empty")
            continue
        if not offset_map:
            refuse("offset_map is empty, so a span cannot be mapped")
            continue
        raw_text_of = {m: text_of[m] for m in (members or []) if m in text_of}
        if not raw_text_of:
            refuse("no member raw text, so a verified quote could not be displayed")
            continue

        payload = {
            "thread_context_id": thread_id,
            "thread_root_id": root_id,
            "member_document_ids": list(members or []),
            "flattened_text": flattened,
            "offset_map": offset_map,
            "raw_text_of": raw_text_of,
            "provenance": {
                "platform": source,
                "built_by": "scripts/export_contexts_for_extract.py",
                "rulings": {
                    "selection_method": selection_method,
                    # CARRIED, because it is the coverage the extractor is
                    # entitled to know about: 0 observed children with a
                    # non-zero floor means we read the root and none of the
                    # thread, and a claim from it is one voice by construction.
                    "hidden_children_min": hidden_min,
                },
            },
        }
        (out_dir / f"{thread_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8"
        )
        written += 1

    print(f"candidates : {len(rows)} thread_context row(s)")
    print(f"written    : {written} -> {out_dir}")
    if refused:
        print("refused    :")
        for reason, count in sorted(refused.items(), key=lambda kv: -kv[1]):
            print(f"  {count:5d}  {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
