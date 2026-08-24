"""Build the extraction-reading golden set. Is this claim a correct reading?

    py -3 scripts/extraction_reading_pool.py --out fixtures/golden

THE SET EXISTS BEFORE THE PROMPT CHANGES, and it measures one distinction:
relayed from first-hand. A verbatim quote lifted out of a vendor announcement
passes quote verification perfectly and is not a report, so rule 1 structurally
cannot catch it and only a human reading the sentence can.

WHAT THE FIRST LABELLING ROUND TAUGHT, AND WHY THIS BUILDER EXISTS
------------------------------------------------------------------
Two labellers, 14 rows, raw agreement 57.1% and kappa 0.421. **Zero of the four
distinct disagreements was about what the text said.** All four were about the
option set. `docs/measurements/extraction-baseline-two-labellings.md`.

The result that mattered was not the coefficient. Both labellers labelled the
SAME quote differently in two sections, in the SAME direction:

    "gives 10%+ better results on SWE-Bench"
        section C, shown with the comment it came from   -> first-hand (both)
        section A, shown as a bare fragment             -> relayed    (both)

The comment reads *"... and gives 10%+ better results on SWE-Bench (p 255 of the
model card pdf)"*. The section carrying the **explicit citation** got
`first-hand` from both; the bare fragment got `relayed` from both. So the
instrument moved with PRESENTATION and moved AWAY from the strongest textual
signal of relaying in the whole set. Not "more context, better label" - framing
beat evidence, twice, in the same direction.

Section A carried no source text at all (`doc_text = 0` on all four rows against
1739 in section C), and that asymmetry is what produced it. **Section A is
dropped rather than repaired**: deduplicated it was five judgements, and A's only
unique row is the one with nothing to read it against.

SIX FIXES, FIVE TAKEN AND ONE PROPOSED
---------------------------------------
1. SECTION A DROPPED. See above.
2. THE AUTHOR IS ON EVERY ROW. `relayed-vendor-claim` is largely a judgement
   about WHO WROTE a sentence, and the first round supplied the sentence without
   supplying that. Three of the six disagreements are quotes from a root post
   written by `ClaudeOfficial` announcing their own model, and no row said so.
3. `nothing-here`'S SCOPE IS IN THE DATA. Every row carries `allowed_labels`, so
   a tool cannot offer an option the row does not support. It was scoped to one
   section in help text and offered on all of them.
4. COST IS OUT OF SCOPE, ruled 2026-08-21, and the ruling is in the option help
   rather than left to be inferred. The board holds claims about what a model
   DOES, not what it charges - price lives in `model_version` as a fact, not in
   `claim` as a report. So *"it already costs 2x Opus 4.8"* is `nothing-here`.
5. `over-read` HAS A STATED PRECEDENCE. A quote can be vendor copy AND attached
   to the wrong capability - the first round's D1 was both, and the option set
   forced a choice with no rule. Provenance wins, because provenance is what
   this set exists to measure, and `also_over_read` records the rest.
6. THE 3x4 TAXONOMY IS TAKEN, not proposed. Two questions - who is speaking
   (3 options) and is the claim sound (4) - so provenance and soundness stop
   competing for one answer. `vendor-about-own-product` and `not-an-observation`
   are new and each existed only as a forced miscategorisation in round 1.

   **ROUND 2 IS THEREFORE NOT COMPARABLE TO ROUND 1**, and `_meta` says so as
   well as this docstring: 12 cells against 4 at small n means agreement falls
   before it rises. See `INCOMPARABILITY`.

THE BLOG CORPUS IS IN, AND IT IS WHERE THE FIRST-HAND EVIDENCE IS
------------------------------------------------------------------
Round 1 had 10 rows and 10 is too few. The pre-registered blog extraction has now
run (`docs/measurements/blog-extraction-run.md`) and its 30 documents plus 8
claims are here.

They matter for a reason beyond size. The Reddit thread produced **4 claims, 4 of
them relayed vendor copy, 0 first-hand**. The blog corpus produced 8 claims that
read as an author's own runs - *"I had Codex optimize it and got it down to around
35 seconds"*, *"It churned away for 38 minutes"*, *"Codex failed to spot and
correct this bug"*. So the set now contains both halves of the distinction it is
built to measure, rather than one half and an absence.

GitHub is the better source in principle - the failure channel, the most likely
place a first-hand observation appears - and its 27 documents have no readable
text on this machine. That is a store/DB mismatch, not a gap in the corpus.

THE AUTHOR, AND WHICH ADAPTER WRITES IT
----------------------------------------
`document.author_id` is written by **`collect/adapters/blog/write.py` only**.
Measured 2026-08-21: set on 30 of 31 blog rows and on **0 of 6 reddit rows**;
`author` holds one row, `blog:simonwillison.net`. There is no Reddit document
writer, so Reddit handles come from the stored API payload here.

**That split is right for this pool and wrong for the pipeline.** A labelling
artifact needs a handle a reader can see, and the payload has one. A CELL needs a
stable `author_id`, because `judge/curate/gate.py:count` dedups by `voice_id` off
`claim.author_id` - which is why the four Reddit claims on staging collapse to
`independent_voices = 1` when the thread has 152 distinct commenters. So the
Reddit path SHOULD write `document.author_id`; payload-sourcing is the design for
the pool and a gap for the board.

NO MODEL PARTICIPATES IN THIS FILE. It reads a run that already happened.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "fixtures" / "reddit" / "thread-1u1b22l-getPostComments.json"
TARGET_TC = "thread_context_eacc17c8af367044"

#: THE 3x4 TAXONOMY, TAKEN 2026-08-21. Round 1's option set collapsed two
#: independent questions into one choice, and every one of its four distinct
#: disagreements was about the set rather than about the text. So there are two
#: questions now, and neither can force the other's answer.
#:
#: `docs/measurements/extraction-baseline-two-labellings.md` has the derivation.
WHO_IS_SPEAKING = {
    "own-experience": {
        "means": "the writer is reporting what happened when THEY used the model",
        "help": (
            "Their own run, their own session, their own bug. "
            "\"I had Codex optimize it and got it down to around 35 seconds\" is "
            "this. So is \"Fable uses up more tokens than a old Porsche gas\"."
        ),
    },
    "vendor-about-own-product": {
        "means": (
            "the writer is the vendor, or speaking for it, describing their own "
            "model"
        ),
        "help": (
            "NEW IN ROUND 2, and it is what round 1 had no name for. "
            "`first-hand-observation` said \"the writer observed this "
            "themselves\", which is LITERALLY TRUE of an announcement and means "
            "the opposite of what that category was for - three of round 1's six "
            "disagreements were quotes from a root post by `ClaudeOfficial` "
            "announcing their own model, and no row said so.\n\n"
            "CHECK `author_external_id` ON THE ROW. That is the input this "
            "question depends on."
        ),
    },
    "relayed-from-elsewhere": {
        "means": (
            "the writer is repeating a claim somebody else made - a benchmark, a "
            "model card, an announcement, another post"
        ),
        "help": (
            "RENAMED from `relayed-vendor-claim`, because a commenter repeating a "
            "number is not a vendor and round 1 had to call them the same thing. "
            "\"gives 10%+ better results on SWE-Bench (p 255 of the model card "
            "pdf)\" is this - the citation is the tell."
        ),
    },
}

IS_THE_CLAIM_SOUND = {
    "supported": {
        "means": "the quote asserts what the claim says it asserts",
        "help": "The reading is right, whoever wrote the sentence.",
    },
    "over-read": {
        "means": "the quote does not support the claim attached to it",
        "help": (
            "Wrong capability, wrong polarity, wrong model, or a claim assembled "
            "from a sentence that does not assert it. IN ROUND 1 THIS COMPETED "
            "WITH PROVENANCE and a labeller had to pick; now it does not, "
            "because the two questions are separate."
        ),
    },
    "not-an-observation": {
        "means": (
            "the sentence states an intention, a plan or a commitment rather "
            "than something observed"
        ),
        "help": (
            "NEW IN ROUND 2. \"We'll keep refining the safeguards to reduce "
            "false positives\" is this, and nothing in round 1's set covered it "
            "- it was forced into a provenance answer."
        ),
    },
    "out-of-scope": {
        "means": (
            "a correct reading of a sentence about something the board does not "
            "hold claims about"
        ),
        "help": (
            "COST IS OUT OF SCOPE - ruled 2026-08-21. The board holds claims "
            "about what a model DOES, not what it charges. Price is a fact in "
            "`model_version`, not a report in `claim`. So \"It already costs 2x "
            "Opus 4.8\" is this, and so is anything about plan limits, "
            "availability or credits."
        ),
    },
}

#: A DOCUMENT ROW GETS ONE QUESTION, not two. There is no proposed claim to
#: judge the soundness of, so `is_the_claim_sound` has nothing to answer about.
#: The options are the three who-answers plus `none`.
CONTAINS = {
    **{k: v for k, v in WHO_IS_SPEAKING.items()},
    "none": {
        "means": "no claim about what a model does",
        "help": (
            "Pricing chatter, capacity speculation, jokes about invented models, "
            "questions, and posts about something else entirely. Most documents "
            "are this and it is the expected answer."
        ),
    },
}

QUESTIONS = {
    "claim": {
        "who_is_speaking": {
            "prompt": (
                "Who is making this claim? Read the document AND the author "
                "before choosing."
            ),
            "options": WHO_IS_SPEAKING,
        },
        "is_the_claim_sound": {
            "prompt": "Does the quote support the claim attached to it?",
            "options": IS_THE_CLAIM_SOUND,
        },
    },
    "document": {
        "contains": {
            "prompt": (
                "Reading this document, what kind of claim about a model does it "
                "contain, if any? Read the author before choosing."
            ),
            "options": CONTAINS,
        },
    },
}

INCOMPARABILITY = (
    "ROUND 2 IS NOT COMPARABLE TO ROUND 1 AND MUST NOT BE REPORTED AS A TREND. "
    "Round 1 was one question with 4 options; round 2 is two questions with 3 "
    "and 4, so 12 cells against 4. More categories always cost agreement at "
    "small n before they buy any: kappa falls first. Any figure from round 2 "
    "placed beside round 1's 0.421 will be read as a decline in the labellers "
    "when it is a change in the instrument. "
    "AND round 1's claim-row figures should not be carried forward at all: "
    "three of its four distinct disagreements were quotes from a vendor-authored "
    "root post and no row supplied the author, so those labels are evidence "
    "about the pool rather than about the readers."
)


def reddit_authors(payload: dict) -> dict[str, str]:
    """`document_id -> handle`, from the payload. See the module docstring."""
    out: dict[str, str] = {}
    post = payload["data"][0]["data"]["children"][0]["data"]
    if post.get("author"):
        out[f"reddit:t3_{post['id']}"] = post["author"]

    def walk(nodes):
        for node in nodes:
            d = node.get("data") or {}
            if d.get("id") and d.get("author"):
                out[f"reddit:t1_{d['id']}"] = d["author"]
            replies = d.get("replies")
            if isinstance(replies, dict):
                walk(replies.get("data", {}).get("children", []))

    walk(payload["data"][1]["data"]["children"])
    return out


def reddit_texts(payload: dict) -> dict[str, str]:
    """`document_id -> untouched source text`, from the payload."""
    post = payload["data"][0]["data"]["children"][0]["data"]
    out = {
        f"reddit:t3_{post['id']}": (post.get("title") or "")
        + "\n\n"
        + (post.get("selftext") or "")
    }

    def walk(nodes):
        for node in nodes:
            d = node.get("data") or {}
            if d.get("id") and isinstance(d.get("body"), str):
                out[f"reddit:t1_{d['id']}"] = d["body"]
            replies = d.get("replies")
            if isinstance(replies, dict):
                walk(replies.get("data", {}).get("children", []))

    walk(payload["data"][1]["data"]["children"])
    return out


def blank_answers(unit: str) -> dict[str, None]:
    return {qid: None for qid in QUESTIONS[unit]}


def row(*, unit, corpus, document_id, author, author_role, text, quote=None,
        source_comment_id=None, note=""):
    return {
        "row_index": None,          # stamped after ordering
        "unit": unit,
        "corpus": corpus,
        "questions": {qid: q["prompt"] for qid, q in QUESTIONS[unit].items()},
        "allowed_answers": {
            qid: list(q["options"]) for qid, q in QUESTIONS[unit].items()
        },
        "answers": blank_answers(unit),
        "document_id": document_id,
        "author_external_id": author,
        "author_role": author_role,
        "source_comment_id": source_comment_id,
        "source_document_text": text,
        "quote": quote,
        "quote_verified": True if quote else None,
        "note": note,
        "labelled_by": None,
        "labeller_note": "",
    }


def build(previous_pool: Path, payload_path: Path, blog_run: Path):
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    authors = reddit_authors(payload)
    texts = reddit_texts(payload)

    lines = [
        json.loads(line)
        for line in previous_pool.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    prev_meta = lines[0]["_meta"]
    prev = lines[1:]

    rows = []

    # ── reddit claims, from the run against the staging corpus ──────────────
    for r in prev:
        if r.get("section") != "C-fresh-run-same-corpus":
            continue
        doc_id = r["document_id"]
        rows.append(row(
            unit="claim", corpus="reddit-thread", document_id=doc_id,
            author=authors.get(doc_id),
            author_role="root post author" if ":t3_" in doc_id else "commenter",
            text=texts.get(doc_id, ""), quote=r["quote"],
            source_comment_id=r["source_comment_id"],
        ))

    # ── reddit documents ────────────────────────────────────────────────────
    for r in prev:
        if r.get("section") != "B-documents":
            continue
        doc_id = r["document_id"]
        rows.append(row(
            unit="document", corpus="reddit-thread", document_id=doc_id,
            author=authors.get(doc_id),
            author_role="root post author" if ":t3_" in doc_id else "commenter",
            text=texts.get(doc_id, ""),
        ))

    # ── the blog run ────────────────────────────────────────────────────────
    run = json.loads(blog_run.read_text(encoding="utf-8"))
    blog_author = "blog:simonwillison.net"
    no_claim = {e["post"]: e["reason"] for e in run.get("no_claim_reasons", [])}

    from scripts.blog_extraction_run import load_documents  # noqa: PLC0415

    blog_docs, _skipped = load_documents()
    by_root = {d["root"]: d for d in blog_docs}

    for c in run["claims"]:
        d = by_root.get(c["post"])
        rows.append(row(
            unit="claim", corpus="blog", document_id=c["document_id"],
            author=blog_author, author_role="article author",
            text=(d["text"] if d else ""), quote=c["quote"],
            note=("template block stripped in memory before extraction; "
                  "see docs/measurements/blog-extraction-run.md"),
        ))

    for d in blog_docs:
        reason = no_claim.get(d["root"])
        note = "template block stripped in memory before extraction"
        if reason:
            note += f". The extractor's stated reason for proposing nothing: {reason!r}"
        rows.append(row(
            unit="document", corpus="blog", document_id=d["member"],
            author=blog_author, author_role="article author",
            text=d["text"], note=note,
        ))

    for i, r in enumerate(rows):
        r["row_index"] = i

    counts = Counter((r["corpus"], r["unit"]) for r in rows)
    meta = {
        "purpose": (
            "GOLDEN SET for the extraction prompt change. Two questions per "
            "claim row: who is speaking, and does the quote support the claim."
        ),
        "labels": "every row has answers: all null. Nothing here is an answer key.",
        "round": 2,
        "INCOMPARABILITY": INCOMPARABILITY,
        "supersedes": (
            "pool--labelled-by-anooj1.jsonl and pool--labelled-by-yathu.jsonl "
            "(round 1), which stay as evidence about the option set"
        ),
        "questions": {
            unit: {qid: {"prompt": q["prompt"], "options": q["options"]}
                   for qid, q in qs.items()}
            for unit, qs in QUESTIONS.items()
        },
        "what_changed_since_round_1": [
            "3x4 TAXONOMY. Two questions instead of one 4-way choice. "
            "`vendor-about-own-product` and `not-an-observation` are new; each "
            "existed only as a forced miscategorisation in round 1.",
            "SECTION A DROPPED. It carried no source text, so the same quote was "
            "a different question in two places - and both labellers answered it "
            "differently, in the same direction, away from an explicit citation.",
            "AUTHOR ON EVERY ROW. Three of round 1's six disagreements were "
            "quotes from a root written by ClaudeOfficial announcing their own "
            "model, and no row said so.",
            "`allowed_answers` PER ROW AND PER QUESTION, so a tool cannot offer "
            "an option the row does not support.",
            "COST RULED OUT OF SCOPE, recorded in `out-of-scope`'s help.",
            "THE BLOG CORPUS IS IN. 30 documents and 8 claims from the "
            "pre-registered run, which is where the first-hand half of the "
            "distinction lives.",
        ],
        "corpora": {
            "reddit-thread": prev_meta.get("corpus"),
            "blog": (
                "30 readable blog thread_contexts, one author "
                "(blog:simonwillison.net), template block stripped in memory. "
                "docs/measurements/blog-extraction-run.md"
            ),
        },
        "author_id_note": (
            "`document.author_id` is written by collect/adapters/blog/write.py "
            "ONLY - 30 of 31 blog rows, 0 of 6 reddit rows. Reddit handles here "
            "come from the stored API payload. Fine for a labelling artifact; a "
            "gap for the board, because gate.py:count dedups voices off "
            "claim.author_id."
        ),
        "rows": len(rows),
        "by_corpus_and_unit": {f"{k[0]}/{k[1]}": v for k, v in sorted(counts.items())},
        "extractor_model": run.get("extractor_model"),
        "prompt_version": "pre-change baseline",
        "built_at": datetime.now(UTC).isoformat(),
    }
    return rows, meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--previous", type=Path,
        default=ROOT / "fixtures" / "golden" / "extraction-reading-baseline--unlabelled.jsonl")
    ap.add_argument("--payload", type=Path, default=PAYLOAD)
    ap.add_argument(
        "--blog-run", type=Path,
        default=ROOT / "docs" / "measurements" / "blog-extraction-run.json")
    args = ap.parse_args(argv)

    rows, meta = build(args.previous, args.payload, args.blog_run)
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "extraction-reading-round2--unlabelled.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_meta": meta}, ensure_ascii=False) + "\n")
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"wrote {path}  ({len(rows)} rows)")
    print(f"  {meta['by_corpus_and_unit']}")
    missing = [r["document_id"] for r in rows if not r["author_external_id"]]
    print(f"  rows without an author: {len(missing)} {missing}")
    print(f"  questions per unit: "
          f"{ {u: list(q) for u, q in QUESTIONS.items()} }")
    return 0


if __name__ == "__main__":
    sys.exit(main())
