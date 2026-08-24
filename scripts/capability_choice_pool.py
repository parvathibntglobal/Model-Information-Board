"""Round 3 of the golden set: was the capability key the right one?

Usage:
    py -3 scripts/capability_choice_pool.py

WHY THIS IS A ROUND 3 AND NOT A THIRD QUESTION ON ROUND 2
---------------------------------------------------------

Round 2's rows are 12 claims from a Reddit thread and a blog post, drawn for a
different question. The claims this round is about are 36 blog claims from the
30-document corpus run. **They are not the same rows**, so a third question
bolted onto round 2 would ask about 12 claims that are not the ones in
question - it cannot answer this even in principle. And Yathu is 34 of 48 into
round 2; a pool that grows mid-labelling is a pool nobody can compare, which is
the rule that governed round 2's own construction.

Cost, in labels, and the comparison is not close on the axis that matters:

    third question on round 2   12 labels/labeller, on claims drawn for
                                another question, none of them the corpus run's
    round 3 as built here       36 labels/labeller, every one on a claim whose
                                capability choice is the thing under test

So round 3 is 3x the labels and ~infinity times the relevant labels. It also
asks ONE question rather than three, so a row is a single choice rather than a
re-read - the per-label cost is lower than round 2's.

WHAT THE POOL CARRIES, AND WHY EACH PIECE
-----------------------------------------

1.  THE EXTRACTOR'S CHOICE IS WITHHELD. It goes to a sidecar file keyed by
    row_index, not into the row. Round 2 could show the claim because its
    question was "does the quote support THIS claim". Here the labeller is
    choosing, and showing them the answer measures anchoring instead of
    judgement.

2.  THE 12 KEYS WITH THEIR CONTRACT TEXT. A labeller cannot choose between
    `ops.latency_ttft` and `over_refusal` from the key names alone.

    AND THAT IS AN ASYMMETRY, STATED HERE BECAUSE IT CHANGES WHAT A
    DISAGREEMENT MEANS: the extractor is shown the 12 key strings AND NOTHING
    ELSE. `build_system_prompt` appends bare keys; `description` and
    `sounds_like` never reach the model. So the labeller is better informed than
    the extractor was, and a disagreement is not proof the extractor was wrong -
    it is an upper bound on what telling the model the definitions could fix.

3.  THREE OPTIONS BEYOND THE KEYS, because `unclassified` collapsed two
    different findings into one bucket and could not argue for either:
      no-key-fits              a real capability the list does not name
                               -> argues for adding a key
      not-a-capability-claim   not about a model's behaviour at all
                               -> argues the claim should not exist
      cannot-tell              the row does not give enough to choose
                               -> argues about the pool, not the extractor

4.  ROWS SHUFFLED, seed recorded. Eleven of the 36 claims come from two
    documents; consecutive same-document rows get labelled as a block.

5.  `recovered_by_salvage` and `conditions`, so a difference in misfiling rate
    between salvaged and first-pass claims is visible rather than assumed absent.

WHAT THIS POOL IS TESTING, PRE-REGISTERED
-----------------------------------------

`docs/measurements/the-vocabulary-hypothesis.md` states the prediction BEFORE
the second labelling exists: if a majority of these 36 claims come back
`no-key-fits`, the finding is not a missing capability key but a vocabulary that
does not describe what engineers write about. It also states the arithmetic -
binary agreement, not 15-way kappa; `no-key-fits` and `not-a-capability-claim`
counted separately - so the scoring cannot be chosen after the numbers are in.

THE DENOMINATOR IS 36, NOT 42. `42` was `28 + 14` from an earlier run whose 14
were never persisted and do not reproduce. Any figure quoted from this pool says
"of 36".
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from judge.config import capabilities  # noqa: E402
from judge.extract.prompt import build_system_prompt  # noqa: E402

RUN = ROOT / "docs" / "measurements" / "blog-extraction-run.json"
SHUFFLE_SEED = 20260821

#: Beyond the 12 keys. Each one is a different argument, which is the point.
EXTRA_OPTIONS = {
    "no-key-fits": {
        "means": "the quote is about a real capability, and no key on the list names it",
        "help": (
            "This is the option `unclassified` was supposed to be and is not. "
            "Choose it when you can say WHAT the quote is about and none of the "
            "twelve is that thing - output length and token spend is the "
            "standing example, since a model that answers correctly at four "
            "times the length has a problem no key here names. Picking this is "
            "an argument for adding a capability key, so say which one in "
            "`note` if you can."
        ),
    },
    "not-a-capability-claim": {
        "means": "the quote is not about how a model behaves at all",
        "help": (
            "A different finding from `no-key-fits` and the two must not be "
            "collapsed. This one says the claim should not exist: a quote about "
            "an incident, a price, a company, a release date, or about software "
            "that is not a model. `no-key-fits` argues for a new key; this "
            "argues the extractor should have returned nothing."
        ),
    },
    "cannot-tell": {
        "means": "the row does not give you enough to choose",
        "help": (
            "About the pool, not about the extractor. If the quote needs "
            "surrounding text the row does not show, say so here rather than "
            "guessing - a guess under this condition is noise that looks like a "
            "judgement. Please say what was missing in `note`."
        ),
    },
}


def source_text_and_authors() -> tuple[dict[str, str], dict[str, str]]:
    """The text the extractor was GIVEN, and who wrote each document.

    The text is post-strip: `## Recent articles` is removed in memory before the
    call, so a labeller checking a quote against the live page would find
    different offsets and, on one document, a different article. The row has to
    carry what the model read.
    """
    sys.argv = [sys.argv[0]]
    from scripts.blog_extraction_run import load_documents  # noqa: PLC0415

    from collect.db import connect  # noqa: PLC0415

    docs, _ = load_documents()
    text = {d["member"]: d["text"] for d in docs}

    conn = connect()
    rows = conn.execute(
        "SELECT d.id, a.external_id FROM document d "
        "LEFT JOIN author a ON a.id = d.author_id"
    ).fetchall()
    conn.close()
    return text, {doc_id: ext for doc_id, ext in rows}


def build(run: dict, text_of: dict[str, str], author_of: dict[str, str]
          ) -> tuple[list[dict], list[dict]]:
    caps = capabilities()
    keys = list(caps.keys())
    options = {
        key: {
            "means": caps[key].description,
            "sounds_like": list(caps[key].sounds_like),
            "failure_mode": caps[key].failure_mode,
        }
        for key in keys
    }
    options.update(EXTRA_OPTIONS)

    # A claim came through salvage when its document's ENVELOPE failed - which
    # is what a non-zero `unsalvaged` count records. Derived rather than asked
    # for, because the run does not tag claims individually and a uniformly
    # `false` flag would read as "salvage contributed nothing".
    via_salvage = {p["slug"] for p in run.get("per_document", []) if p["unsalvaged"]}

    claims = run["claims"]
    rows: list[dict] = []
    withheld: list[dict] = []
    for c in claims:
        rows.append({
            "unit": "claim",
            "corpus": "blog",
            "document_id": c["document_id"],
            "post": c["post"],
            "slug": c["slug"],
            "author_external_id": author_of.get(c["document_id"]),
            "source_document_text": text_of.get(c["document_id"]),
            # SAME SHAPE AS ROUND 2 - `questions` and `allowed_answers` keyed
            # by question name - so `scripts/check_labelling.py` validates a
            # returned round 3 with no change. A flat list here would have made
            # the checker raise on its own pool.
            "questions": {
                "capability": (
                    "Which capability is this quote about? Read the quote, then "
                    "the document it came from. Choose ONE."
                )
            },
            "quote": c["quote"],
            "model_surface_the_extractor_read": c["surface"],
            "polarity_the_extractor_read": c["polarity"],
            "conditions_the_extractor_recorded": c.get("conditions") or {},
            "recovered_by_salvage": c["slug"] in via_salvage,
            "allowed_answers": {"capability": sorted(options)},
            "answers": {"capability": None},
            "note": None,
        })
        withheld.append({
            "quote": c["quote"],
            "slug": c["slug"],
            "extractor_chose": c["capability"],
        })

    rnd = random.Random(SHUFFLE_SEED)
    order = list(range(len(rows)))
    rnd.shuffle(order)
    rows = [rows[i] for i in order]
    withheld = [withheld[i] for i in order]
    for i, (row, w) in enumerate(zip(rows, withheld, strict=True)):
        row["row_index"] = i
        w["row_index"] = i

    return rows, withheld


def meta(run: dict, rows: list[dict], options: dict) -> dict:
    prompt = build_system_prompt(list(capabilities().keys()))
    return {
        "purpose": (
            "GOLDEN SET, round 3. ONE question: was the capability key the "
            "extractor chose the right one? The extractor's choice is NOT in "
            "these rows - it is in the sidecar, and the sidecar is not for the "
            "labeller."
        ),
        "round": 3,
        "labels": "every row has answers.capability = null. Nothing here is an answer key.",
        "DENOMINATOR": (
            f"{len(rows)} claims from {len({r['slug'] for r in rows})} of "
            f"{run['documents']} blog documents, ONE site, ONE author, ONE "
            f"extractor ({run['extractor_model']}), ONE draw, run at "
            f"{run['run_at']}. This is not a misfiling rate for the pipeline "
            "and it is not a rate for anything but this corpus. The extractor "
            "is nondeterministic: the same 30 documents have produced 8, 28 and "
            "36 claims on three runs at three code states."
        ),
        "THE_ASYMMETRY_THAT_CHANGES_WHAT_A_DISAGREEMENT_MEANS": (
            "YOU ARE BETTER INFORMED THAN THE EXTRACTOR WAS. Its system prompt "
            f"is {len(prompt)} characters and appends the 12 capability keys as "
            "bare strings - `contract/capabilities.yaml`'s `description` and "
            "`sounds_like` never reach the model, which was measured 2026-08-21 "
            "and is not intended. You are shown both. So a disagreement is NOT "
            "evidence the extractor chose badly; it is an upper bound on how "
            "much telling the model what the keys mean could fix. If this pool "
            "is relabelled after that changes, THE TWO ROUNDS ARE NOT "
            "COMPARABLE, because the instrument moved."
        ),
        "INCOMPARABILITY": (
            "ROUND 3 IS NOT COMPARABLE TO ROUNDS 1 OR 2 AND MUST NOT BE PLACED "
            "BESIDE THEM AS A TREND. Different question, different claims, "
            "different corpus, 15 options against 4 and 3x4. Round 1 asked one "
            "question with 4 options; round 2 asked two with 3 and 4; this asks "
            "one with 15. Kappa falls as categories rise before it buys "
            "anything, so a lower figure here is the instrument and not the "
            "readers."
        ),
        "HOW_TO_SCORE_IT": (
            "THE HEADLINE IS THE BINARY, NOT 15-WAY KAPPA. With 36 rows and 15 "
            "options, a 15-way kappa is noise. Report: (a) labeller-vs-extractor "
            "agreement, which is the measurement - did the extractor pick the "
            "key a reader picks; (b) labeller-vs-labeller agreement on the same "
            "binary, which is the instrument's reliability and bounds how much "
            "of (a) to believe; (c) the 15-way distribution as description only. "
            "And count `no-key-fits` and `not-a-capability-claim` SEPARATELY - "
            "collapsing them is what made `unclassified` unable to argue for "
            "anything."
        ),
        "WHAT_THIS_POOL_CANNOT_ANSWER": (
            "openai-timeline's twelve code.generation claims, which were the "
            "reason for building it. They were quoted from one draw, never "
            "persisted, and DO NOT REPRODUCE: 4 draws at current HEAD return 0 "
            "claims with the stated reason 'describes an incident involving an "
            "experimental, unreleased OpenAI model, but does not make any "
            "claims'. So the sharpest piece of evidence for an incomplete "
            "vocabulary cannot be examined, and nothing in this pool stands in "
            "for it. `docs/measurements/the-effort-dimension.md` §4."
        ),
        "options": options,
        "extractor_prompt_chars": len(prompt),
        "source_run": "docs/measurements/blog-extraction-run.json",
        "shuffle_seed": SHUFFLE_SEED,
        "sidecar": "fixtures/golden/capability-choice-round3--extractor-chose.jsonl",
        "supersedes": None,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "fixtures" / "golden")
    args = ap.parse_args(argv)

    run = json.loads(RUN.read_text(encoding="utf-8"))
    text_of, author_of = source_text_and_authors()
    rows, withheld = build(run, text_of, author_of)
    missing_text = [r["row_index"] for r in rows if not r["source_document_text"]]
    missing_author = [r["row_index"] for r in rows if not r["author_external_id"]]

    caps = capabilities()
    options = {
        key: {
            "means": caps[key].description,
            "sounds_like": list(caps[key].sounds_like),
            "failure_mode": caps[key].failure_mode,
        }
        for key in caps
    }
    options.update(EXTRA_OPTIONS)

    args.out.mkdir(parents=True, exist_ok=True)
    pool = args.out / "capability-choice-round3--unlabelled.jsonl"
    with pool.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_meta": meta(run, rows, options)}, ensure_ascii=False) + "\n")
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    side = args.out / "capability-choice-round3--extractor-chose.jsonl"
    with side.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_meta": {
            "purpose": "WITHHELD FROM THE LABELLER. What the extractor chose, by row_index.",
            "do_not": "Do not open this before labelling. It is the thing being measured.",
        }}, ensure_ascii=False) + "\n")
        for w in withheld:
            fh.write(json.dumps(w, ensure_ascii=False) + "\n")

    print(f"rows        {len(rows)}")
    print(f"documents   {len({r['slug'] for r in rows})}")
    print(f"options     {len(options)}  ({len(caps)} keys + {len(EXTRA_OPTIONS)})")
    n_salv = sum(1 for r in rows if r["recovered_by_salvage"])
    print(f"salvaged    {n_salv} of {len(rows)} "
          f"({len({r['slug'] for r in rows if r['recovered_by_salvage']})} documents)")
    print(f"no text     {len(missing_text)}  {missing_text}")
    print(f"no author   {len(missing_author)}  {missing_author}")
    if missing_text or missing_author:
        print("  ^ NAMED RATHER THAN DROPPED. A row missing its document or its "
              "author is a row the labeller cannot answer; it stays in the pool "
              "so the gap is visible, and `author_external_id: null` is the "
              "defect round 1 was undone by.")
    print(f"pool     -> {pool}")
    print(f"sidecar  -> {side}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
