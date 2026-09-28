"""The pre-registered blog extraction run. 30 documents, one author, one site.

    py -3 scripts/blog_extraction_run.py --out docs/measurements

PRE-REGISTERED IN `docs/measurements/blog-extraction-pre-registration.md`,
written before any model call so nothing here can be edited into agreement with
what arrives. This script reports against that document's table rather than
producing a count.

THE PRE-REGISTRATION SAID DO NOT RUN UNTIL THE TEMPLATE BLOCK IS STRIPPED, AND
IT WAS STILL THERE
-------------------------------------------------------------------------------
Measured before spending anything: **29 of the 30 readable blog
`thread_context` rows still carry `## Recent articles`**, and 29 contain one of
the three headlines the pre-registration named. The strip landed in the PARSER
(`fbbfe94`), and these rows were flattened before it, so the stored text predates
the fix.

Running unstripped would have spent $0.062 to reproduce a defect already measured
for free, which is exactly what the pre-registration forbids. So the block is
stripped IN MEMORY here, with `parse.strip_template_block` and the two headings
`contract/sources.yaml` verified over 62 pages — not re-fetched, not rewritten
into the store.

**That is safe for verification because the block is terminal.** The strip removes
a suffix, so every offset before the cut is unchanged, and a blog
`thread_context` carries exactly one identity segment (`flat == raw`, one member)
whose end is clamped to the new length. A quote from the retained text maps to
the same raw span it always did; a quote from the block cannot be found at all,
which is the point.

Effect, before the run: 29 of 30 shortened, 8,118 bytes removed, mean 280, none
emptied.

WHAT A HEADLINE QUOTE MEANS AFTER THE STRIP
--------------------------------------------
Three posts legitimately contain one of the three pre-registered headlines
because they ARE those articles — `qwen-38-27b`, `moonlight-mayhem`,
`openai-timeline`. So the test is not "does a headline appear in a quote", it is
"does a headline appear in a quote **on a post about something else**". Both are
reported separately below.

NOTHING IS WRITTEN TO THE DATABASE. This is a measurement, and inserting 30
documents' worth of claims beside the four already on staging would make the
labelling baseline non-comparable. The voice count is COMPUTED so the
pre-registration's falsifiable check can run, and not stored.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from collect.adapters.blog.parse import strip_template_block  # noqa: E402
from collect.db import connect  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.rawstore_reader import RawStoreReader, ReadOutcome  # noqa: E402
from judge.config import capabilities  # noqa: E402
from judge.extract.client import OpenRouterClient  # noqa: E402
from judge.extract.runner import ThreadInput, extract  # noqa: E402
from judge.extract.verify import OffsetMapping  # noqa: E402

#: From `contract/sources.yaml`, simonwillison.net, status verified over 62 pages.
HEADINGS = ("Recent articles", "More recent articles")

#: The three the pre-registration named, and the posts that legitimately own them.
PREREG_HEADLINES = {
    "Qwen 3.8 27B is excellent": "qwen-38-27b",
    "One-shotting a Raccoon Heist": "moonlight-mayhem",
    "timeline of the OpenAI accidental attack": "openai-timeline",
}

#: Pre-registered as unsupported by this corpus: a claim here is a signal.
UNSUPPORTED_PREFIXES = ("tool_calling.", "context.")


def load_documents():
    """Blog thread contexts with readable flattened text, block stripped."""
    store = RawStoreReader(RawStore(ROOT / "raw_store"))
    conn = connect()
    rows = conn.execute(
        "SELECT tc.id, tc.thread_root_id, tc.flattened_text_ref, tc.offset_map, "
        "tc.member_document_ids FROM thread_context tc "
        "WHERE tc.selection_method = 'whole_document' ORDER BY tc.thread_root_id"
    ).fetchall()
    conn.close()

    out = []
    skipped = []
    for tc_id, root, ref, offset_map, members in rows:
        if not ref:
            skipped.append((root, "no ref"))
            continue
        try:
            got = store.resolve(ref)
        except ValueError:
            skipped.append((root, "malformed ref"))
            continue
        if got.outcome is not ReadOutcome.FOUND:
            skipped.append((root, str(got.outcome)))
            continue

        original = got.text
        stripped = strip_template_block(original, HEADINGS)
        if not stripped.strip():
            skipped.append((root, "empty after strip"))
            continue

        # One identity segment per blog context, clamped to the new length.
        segs = []
        for entry in offset_map or []:
            e = dict(entry)
            if e["flat_start"] >= len(stripped):
                continue
            e["flat_end"] = min(e["flat_end"], len(stripped))
            e["raw_end"] = min(e["raw_end"], len(stripped))
            segs.append(OffsetMapping(**e))
        if not segs:
            skipped.append((root, "no usable offset segment"))
            continue

        member = (members or [root])[0]
        out.append({
            "thread_context_id": tc_id,
            "root": root,
            "member": member,
            "original_len": len(original),
            "stripped_len": len(stripped),
            "text": stripped,
            "offset_map": tuple(segs),
        })
    return out, skipped


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "measurements")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    docs, skipped = load_documents()
    if args.limit:
        docs = docs[: args.limit]

    removed = sum(d["original_len"] - d["stripped_len"] for d in docs)
    shortened = sum(1 for d in docs if d["stripped_len"] < d["original_len"])
    print(f"documents            {len(docs)}")
    print(f"skipped              {len(skipped)}  {skipped}")
    print(f"shortened by strip   {shortened}")
    print(f"bytes removed        {removed}")
    print()
    if args.dry_run:
        print("dry run - no model call")
        return 0

    client = OpenRouterClient.from_env()
    caps = list(capabilities().keys())
    print(f"model                {client.model}")
    print(f"capabilities         {len(caps)}")
    print("pre-registered cost  30 x $0.00208 = $0.062, 6.2% of the $1.00 daily cap")
    print()

    results = []
    tok_in = tok_out = 0
    for i, d in enumerate(docs, 1):
        thread = ThreadInput(
            thread_context_id=d["thread_context_id"],
            flattened_text=d["text"],
            offset_map=d["offset_map"],
            raw_text_of={d["member"]: d["text"]},
        )
        run = extract(thread, client=client, capability_keys=caps)
        tok_in += run.input_tokens
        tok_out += run.output_tokens
        results.append((d, run))
        flag = f" <- {len(run.verified)} claim(s)" if run.verified else ""
        if run.unclassified:
            flag += f"  UNCLASSIFIED x{len(run.unclassified)}"
        print(f"  [{i:2d}/{len(docs)}] {d['root'].rsplit('/', 2)[-2]:52s} "
              f"proposed {run.proposed} verified {len(run.verified)} "
              f"rejected {len(run.rejected)}{flag}")

    print()
    print("=" * 74)
    print("AGAINST THE PRE-REGISTRATION")
    print("=" * 74)

    verified = [(d, c, q) for d, r in results for c, q in r.verified]
    rejected = sum(len(r.rejected) for _, r in results)
    n = len(verified)

    print(f"  claims verified                {n}")
    print(f"  claims rejected by verification {rejected}")
    print(f"  documents producing a claim     "
          f"{len({d['root'] for d, _, _ in verified})} of {len(docs)}")
    print(f"  tokens                          {tok_in} in / {tok_out} out")
    print()

    band = ("0-4 as predicted" if n <= 4 else
            "5-6, above the predicted band but below the over-extraction line" if n <= 6
            else "ABOVE 6 - the pre-registration calls this over-extraction")
    print(f"  §3 expected yield 0-4    -> {n} claims: {band}")

    caps_seen = Counter(c.legacy_score_key for _, c, _ in verified)
    bad_caps = {k: v for k, v in caps_seen.items()
                if k.startswith(UNSUPPORTED_PREFIXES)}
    print(f"  §4 unsupported keys      -> {bad_caps or 'none'}"
          f"   (capabilities seen: {dict(caps_seen) or 'none'})")

    template_hits = []
    for d, c, _quote in verified:
        for headline, owner in PREREG_HEADLINES.items():
            if headline in c.quote and owner not in d["root"]:
                template_hits.append((d["root"], headline, c.quote))
    print(f"  §2 template quotes on an unrelated post -> "
          f"{len(template_hits)}  {'(the flattener, not yield)' if template_hits else '(none)'}")
    for root, headline, quote in template_hits:
        print(f"       {root}")
        print(f"       headline {headline!r} in quote {quote[:70]!r}")

    legit = [(d["root"], c.quote) for d, c, q in verified
             for h, owner in PREREG_HEADLINES.items()
             if h in c.quote and owner in d["root"]]
    print(f"  ... the same headlines on the post that IS that article -> {len(legit)}")

    voices = len({d["member"] for d, _, _ in verified})
    authors = set()
    conn = connect()
    for d, _, _ in verified:
        row = conn.execute(
            "SELECT author_id FROM document WHERE id = %s", (d["member"],)).fetchone()
        if row and row[0]:
            authors.add(row[0])
    conn.close()
    print(f"  §1 independent voices    -> {len(authors)} distinct author_id "
          f"across {voices} documents")
    if len(authors) > 1:
        print("       *** FALSIFIED: the pre-registration says >1 voice means a "
              "voice was invented ***")
    else:
        print("       one voice, as predicted, so every cell is `insufficient` "
              "regardless of the claims")

    payload = {
        "run_at": datetime.now(UTC).isoformat(),
        "pre_registration": "docs/measurements/blog-extraction-pre-registration.md",
        "extractor_model": client.model,
        "documents": len(docs),
        "template_block_stripped_in_memory": True,
        "documents_shortened": shortened,
        "bytes_removed": removed,
        "claims_verified": n,
        "claims_rejected": rejected,
        "capabilities": dict(caps_seen),
        "unsupported_capability_claims": bad_caps,
        "template_quotes_on_unrelated_posts": [
            {"post": r, "headline": h, "quote": q} for r, h, q in template_hits
        ],
        "headline_quotes_on_the_owning_post": [
            {"post": r, "quote": q} for r, q in legit
        ],
        "distinct_author_ids": len(authors),
        "input_tokens": tok_in,
        "output_tokens": tok_out,
        "claims": [
            {
                "post": d["root"],
                "document_id": d["member"],
                "slug": d["root"].rsplit("/", 2)[-2],
                "quote": c.quote,
                "capability": c.legacy_score_key,
                "polarity": c.polarity,
                "surface": c.model_ref.surface,
                "specificity": c.model_ref.specificity,
                "speaking": c.model_ref.speaking,
                "relevance": c.relevance,
                "has_repro_steps": c.has_repro_steps,
                "has_numbers": c.has_numbers,
                "conditions": {
                    k: v for k, v in c.conditions.model_dump().items() if v is not None
                },
            }
            for d, c, q in verified
        ],
        # SALVAGE AND ZERO KIND. Recorded because a validation zero and a real
        # zero used to read identically, and because the claims a schema ate
        # are the loudest signal in the run.
        "unsalvaged": [
            {
                "slug": d["root"].rsplit("/", 2)[-2],
                "index": u.index,
                "errors": u.errors,
                "raw_quote": (u.raw or {}).get("quote"),
                "raw_capability": (u.raw or {}).get("legacy_score_key"),
            }
            for d, r in results for u in r.unsalvaged
        ],
        "per_document": [
            {
                "slug": d["root"].rsplit("/", 2)[-2],
                "proposed": r.proposed,
                "verified": len(r.verified),
                "rejected": len(r.rejected),
                "unsalvaged": len(r.unsalvaged),
                "zero_kind": r.zero_kind,
                "retries": r.schema_retries,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
            }
            for d, r in results
        ],
        "unclassified": [
            {"post": d["root"], "quotes": r.unclassified}
            for d, r in results if r.unclassified
        ],
        "unclassified_total": sum(len(r.unclassified) for _, r in results),
        "schema_retries_total": sum(r.schema_retries for _, r in results),
        "no_claim_reasons": [
            {"post": d["root"], "reason": r.no_claim_reason}
            for d, r in results if r.no_claim_reason
        ],
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "blog-extraction-run.json"
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print()
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
