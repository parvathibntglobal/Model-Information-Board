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
    raw text past the map's end  a span that cannot be taken at all. 53 of 179
                                 blog contexts, all on the two feeds that strip
                                 a template block, whose maps were built before
                                 the current rule - see `_offset_map_drift`

Named and counted, never written as a partial file.

AND ONE THING THAT IS RECORDED RATHER THAN REFUSED. A one-to-one segment whose
raw text differs from the flattened text IN PLACE is exported with the drift
counted. Rule 8: that check refused 12 of 40 github contexts on its first run,
for two leading newlines, and a gate whose error rate has not been measured
against a population it did not choose ships as a recorded field.

    python scripts/export_contexts_for_extract.py --out DIR [--limit N]
                                                  [--selection-method post_body_only]
"""

from __future__ import annotations

import argparse
import json
import pathlib

from collect.adapters.blog.parse import (
    extract_article_text,
    strip_template_block,
    template_block_for,
)
from collect.assemble.prose import (
    NotAPayload,
    github_issue_prose,
    reddit_prose,
)
from collect.config import settings
from collect.rawstore import RawStore
from collect.rawstore_reader import RawStoreReader


def _blog_prose(_text: str, *, raw: bytes, url: str | None, source_id: str | None) -> str:
    """Blog article HTML to the prose `flattened_text` was derived from.

    THE POINT IS NOT "PROSE", IT IS "THE SAME PROSE". `raw_text_of` is what
    step 3 renders a verified quote from and what E6's `reject_check` is handed
    (`judge/cli.py`). If it carries text that differs from what the flattener
    saw, every offset in `offset_map` points somewhere slightly wrong and a
    quote that verified renders as the neighbouring sentence.

    So this reproduces `collect/adapters/blog/write.py`'s two steps exactly,
    in order, rather than doing something equivalent:

        text = extract_article_text(payload, url=...)      # 1
        if text and rule.strips: text = strip_template_block(text, headings)

    The second step is the one that is easy to omit. `simonwillison.net` strips
    `['Recent articles', 'More recent articles']`; skipping it would put a
    navigation block into the field the vet step trusts, and the surface finder
    already matched a model name inside exactly that block once (#365).

    BYTES, NOT THE STORE'S TEXT. `extract_article_text` takes the article
    undecoded on purpose - trafilatura's charset detection beats a guess made
    here, and a mis-decoded article produces mojibake that verifies as a quote.
    `_text` is the reader's decoded form and is deliberately unused.
    """
    text = extract_article_text(raw, url=url)
    if text is None:
        # trafilatura found no article body - a nav page, a paywall stub, a JS
        # shell. NotAPayload so the caller refuses the thread by "no member raw
        # text" rather than exporting it with an envelope in it, which is what
        # the JSON sources do for the same condition.
        raise NotAPayload(f"no article body extracted from {url or 'unknown url'}")
    rule = template_block_for(source_id)
    if rule.strips:
        stripped = strip_template_block(text, rule.headings)
        if not stripped:
            # `write.py` turns this into `nothing_extracted` rather than keeping
            # the unstripped text. Same decision here: a document whose whole
            # body was template is not a document with a body.
            raise NotAPayload(f"template block consumed the whole article: {url}")
        text = stripped
    return text


def _plain(fn):
    """A `blob -> str` extractor, given the uniform signature."""

    def call(text: str, *, raw: bytes, url: str | None, source_id: str | None) -> str:
        return fn(text)

    return call


#: `document.source` -> how to get prose out of that platform's payload.
#:
#: EVERY VALUE TAKES THE SAME ARGUMENTS even though only blog uses `raw`, `url`
#: and `source_id`. One dispatch point, so a source added later cannot quietly
#: get a different contract - and blog needed all three, which is why it was
#: absent rather than hard.
#:
#: A source with no entry is still passed through unchanged, and that is now the
#: only remaining case of the defect this map exists to prevent.
_EXTRACTORS = {
    "reddit": _plain(reddit_prose),
    "github": _plain(github_issue_prose),
    "blog": _blog_prose,
}


def _feed_ids_by_host() -> dict[str, str]:
    """`simonwillison.net` -> `blog:simonwillison.net`, from the contract.

    `template_block_for` is keyed by the FEED id and a document carries a url,
    so something has to join them. The contract is the only place that knows,
    and an unknown host maps to nothing - which `template_block_for` then reads
    as `unverified`, never as "clean". Rule 6 across two layers.
    """
    from urllib.parse import urlparse

    from collect.registry.sources import load_sources

    out: dict[str, str] = {}
    for feed in load_sources().feeds:
        host = (urlparse(feed.get("endpoint") or "").hostname or "").lower()
        if host:
            out[host.removeprefix("www.")] = feed.get("id")
    return out


def _offset_map_drift(offset_map, flattened: str, raw_text_of: dict):
    """`(severity, reason)` where the raw text does not fit its offset map.

    `severity` is `refuse` where the span cannot be taken at all and `report`
    where it can be taken and is not what the flattener saw. Two states, kept
    apart, because collapsing them makes a two-character whitespace shift and
    an out-of-range index the same event.

    Checks only ONE-TO-ONE segments. A substitution segment has different flat
    and raw lengths by design - an emoji becoming `[upside_down_face]` is 1
    character becoming 18 - and comparing them would report every emoji as
    drift.
    """
    for seg in offset_map or ():
        raw = raw_text_of.get(seg.get("document_id"))
        if raw is None:
            continue
        flat_start, flat_end = seg.get("flat_start"), seg.get("flat_end")
        raw_start, raw_end = seg.get("raw_start"), seg.get("raw_end")
        if None in (flat_start, flat_end, raw_start, raw_end):
            return ("refuse", "a segment is missing an offset")
        if (flat_end - flat_start) != (raw_end - raw_start):
            continue                      # substitution, by design
        if raw_end > len(raw):
            # SEVERE. The span cannot be taken at all: step 3 would index past
            # the end and render a truncated quote or raise.
            return ("refuse", "a span ends past the end of the raw text")
        if flattened[flat_start:flat_end] != raw[raw_start:raw_end]:
            # NOT SEVERE, AND NOT A REFUSAL - rule 8, learned on this check's
            # first contact with a second source. It refused 12 of 40 github
            # contexts, and the cause was `github_issue_prose` emitting two
            # leading newlines the flattener did not see: a rendered span off
            # by two characters of whitespace, not the wrong sentence.
            #
            # A gate whose error rate has not been measured against a
            # population it did not choose ships as a RECORDED FIELD. So this
            # is counted, named and exported; the blog overshoot above is
            # refused because it cannot be rendered at all.
            return ("report", "a one-to-one segment maps to different text")
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--source", default=None,
        help="restrict to one platform, e.g. blog. `selection_method` is NOT a "
             "substitute: `whole_document` is shared by blog, devto, x and "
             "huggingface, so scoping by it selects 598 contexts of which 175 "
             "are blog (measured 2026-09-17).",
    )
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
    store = RawStore(settings().raw_store_path)
    reader = RawStoreReader(store)
    feed_of_host = _feed_ids_by_host()

    from collect.db import connect

    conn = connect()
    try:
        clauses = ["tc.flattened_text_ref IS NOT NULL"]
        params: list[object] = []
        if args.source:
            # THE ROOT'S SOURCE, matching the `d.source` the SELECT already
            # joins and reports. A thread is one platform's - the join is on
            # `thread_root_id`, so this cannot half-select a mixed thread.
            clauses.append("d.source = %s")
            params.append(args.source)
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
            for doc_id, source, ref, doc_url in conn.execute(
                "SELECT id, source, text_ref, url FROM document WHERE id = ANY(%s)",
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
                    from urllib.parse import urlparse

                    host = (urlparse(doc_url or "").hostname or "").lower()
                    text_of[doc_id] = extract(
                        outcome.require(),
                        # BYTES FROM THE STORE, not the reader's decoded text.
                        # Only blog uses it; see `_blog_prose`.
                        raw=store.get(ref),
                        url=doc_url,
                        source_id=feed_of_host.get(host.removeprefix("www.")),
                    )
                except NotAPayload:
                    # SKIPPED, so the thread is refused below by
                    # "no member raw text" rather than exported with an
                    # envelope in it.
                    continue
    finally:
        conn.close()

    written = 0
    refused: dict[str, int] = {}
    #: Drift that is recorded rather than refused. Reported beside `written`,
    #: because a count nobody prints is a measurement nobody has.
    drifted: dict[str, int] = {}

    def refuse(reason: str) -> None:
        refused[reason] = refused.get(reason, 0) + 1

    for (thread_id, root_id, members, flat_ref, offset_map,
         selection_method, hidden_min, source) in rows:
        # A MALFORMED REF IS REFUSED, NOT RAISED. `RawStore.parse_ref` rejects
        # anything that is not `flattened/sha256/...` before touching the
        # filesystem, which is right for the store and wrong for a batch: one
        # bad row would take the whole export with it.
        #
        # There is exactly one such row today - a blog context assembled
        # 2026-08-20 whose `flattened_text_ref` reads `flattened/inline-see-json`,
        # a sentinel left by an earlier export that inlined the text into JSON
        # and overwrote the ref. 1 of 175 blog contexts; 0 on every other
        # source. Its text is unreachable from the database, so the row is a
        # real gap rather than a parsing nuisance - and it is REFUSED BY NAME
        # here so the count says so instead of the export dying at row 1.
        try:
            outcome = reader.resolve(flat_ref)
        except ValueError:
            refuse(f"flattened_text_ref is not a store ref ({flat_ref!r})")
            continue
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
        drift = _offset_map_drift(offset_map, flattened, raw_text_of)
        if drift and drift[0] == "report":
            drifted[drift[1]] = drifted.get(drift[1], 0) + 1
            drift = None
        if drift:
            # THE SIXTH REFUSAL, AND IT IS THE SAME CLASS AS THE FIFTH.
            # `offset_map` is the artifact that cannot be reconstructed, so it
            # is the ground truth: raw text that does not agree with it means a
            # quote can verify against the flattened string and render the
            # neighbouring sentence, or raise on a span past the end.
            #
            # Measured 2026-09-18: 53 of 179 blog contexts, ALL of them on the
            # two feeds that strip a template block (simonwillison.net 43,
            # engineering.grab.com 10). Their maps were built BEFORE the
            # current rule, from the unstripped article - re-extracting today
            # strips `Recent articles` / `Join us` and the map overshoots by
            # exactly that block. Verified: with stripping off, all 53 agree.
            #
            # Exporting them unstripped would satisfy the map and put a
            # navigation block into the field E6's reject_check reads - and a
            # nav block is where the surface finder matched a model name in
            # #365. So neither text is right for these rows: the REPAIR is to
            # re-flatten them, and until then they are refused by name rather
            # than exported with a map that does not fit.
            refuse(f"raw text disagrees with offset_map ({drift[1]})")
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
    if drifted:
        print("exported WITH RECORDED DRIFT (not refused, see _offset_map_drift):")
        for reason, count in sorted(drifted.items(), key=lambda kv: -kv[1]):
            print(f"     {count:3d}  {reason}")
    if refused:
        print("refused    :")
        for reason, count in sorted(refused.items(), key=lambda kv: -kv[1]):
            print(f"  {count:5d}  {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
