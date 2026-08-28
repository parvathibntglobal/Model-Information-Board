"""A TEMPORARY classification pass. Not a pipeline stage, and not the extractor.

WHAT IT IS FOR

One question, asked of a model-only corpus: **does a person say something about
how a model behaved — anywhere in the document?** Including inside a price
comparison, a "which model should I use" thread, or a recommendation. A price
complaint carrying *"2x the cost and worse at instruction following"* is a
capability report; a recommendation thread's ANSWERS are often the evidence even
when the question is not.

That wider reading is the thing being tested. The extractor's prompt is narrower
by design and is not touched here.

WHAT IT DELIBERATELY DOES NOT CONTAIN

**No signal vocabulary.** The prompt never says what "working" or "broken"
phrasing looks like, gives no example phrases, and lists no terms from
`contract/queries.yaml`. The whole point is to find out what a reader identifies
as a capability report WITHOUT being told the words — because the sieve's signal
group is measured at 5.0% on this corpus and 0.4% on a recency listing, and
whether that is a vocabulary limit or a corpus limit is exactly what this asks.

It DOES contain the twelve existing keys with their definitions, because a
proposal has to be shaped like a key rather than like a topic. Teaching the
structure is not the same as teaching the vocabulary.

RULE 2, STATED RATHER THAN ASSUMED

`CLAUDE.md` permits exactly two stages to call a model: `judge/extract/` and
`judge/ask/`. **This is neither, and it must not become a third.** It is a
measurement harness — it writes no `claim`, no `cell`, and no `capability`, and
its output is a file plus a proposal. If the wider reading turns out to be worth
adopting, that is a change to `judge/extract/`'s prompt under review, not a new
stage that arrived by accident.

The model PROPOSES and nothing here decides: every quote is verified by exact
substring match against the text the model was shown, and a claim whose quote is
not present is recorded as unverified rather than trusted.

    python scripts/classify_capability_reports.py --cap-usd 1.00 --out results.jsonl
"""

from __future__ import annotations

import argparse
import json
import pathlib

import yaml

from collect.config import CONTRACT_DIR, settings
from collect.rawstore import RawStore
from collect.rawstore_reader import RawStoreReader
from collect.triage.entity import build_population
from collect.triage.gates import Document, triage
from judge.extract.budget import Budget, BudgetExhausted
from judge.extract.client import OpenRouterClient

TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "is_capability_report": {
            "type": "boolean",
            "description": (
                "True if anyone in this document says something about how a named "
                "model behaved in use. Include statements inside price "
                "comparisons, recommendation threads, and answers to questions."
            ),
        },
        "capability_key": {
            "type": ["string", "null"],
            "description": "One of the listed keys, or null if none fits.",
        },
        "proposed_key": {
            "type": ["object", "null"],
            "properties": {
                "name": {"type": "string"},
                "definition": {"type": "string"},
            },
            "required": ["name", "definition"],
            "description": (
                "Only when the document reports a capability that NO listed key "
                "covers. Name it in the same dotted style as the listed keys."
            ),
        },
        "quote": {
            "type": ["string", "null"],
            "description": (
                "VERBATIM span from the document that carries the report. Copy it "
                "exactly, including punctuation. Null only when "
                "is_capability_report is false."
            ),
        },
        "reason": {
            "type": "string",
            "description": "One sentence. Why this is or is not a capability report.",
        },
    },
    "required": ["is_capability_report", "reason"],
}


def system_prompt() -> str:
    """The twelve keys with definitions. No signal vocabulary — see the module."""
    raw = yaml.safe_load((CONTRACT_DIR / "capabilities.yaml").read_text(encoding="utf-8"))
    caps = raw.get("capabilities") or raw
    lines = [
        "You are reading one post from a public forum about AI models.",
        "",
        "DECIDE: does anyone in this document say something about how a named "
        "model BEHAVED when they used it?",
        "",
        "Read widely. A capability report can be:",
        "  - inside a price or cost comparison",
        "  - an answer in a 'which model should I use' thread",
        "  - a recommendation, or a reason for switching",
        "  - an aside in a post that is mostly about something else",
        "",
        "It is NOT a capability report if the document only: announces or links a "
        "release, asks a question without answering it, discusses company news or "
        "pricing with no behavioural claim, or is a benchmark table with no "
        "first-hand observation.",
        "",
        "If it IS a report, assign ONE of these capability keys:",
        "",
    ]
    for cap in caps:
        lines.append(f"  {cap['key']}")
        lines.append(f"      {(cap.get('description') or '').strip()}")
    lines += [
        "",
        "If the document reports a real capability that none of these keys covers, "
        "leave capability_key null and fill proposed_key instead: a dotted name in "
        "the same style, and a one-line definition of what it measures. Propose "
        "sparingly — only when no listed key fits.",
        "",
        "Always give a verbatim quote when is_capability_report is true. Copy the "
        "span exactly from the document; do not paraphrase, correct or shorten it.",
    ]
    return "\n".join(lines)


def survivors(conn, reader):
    """Triage survivors from today's model-only sweep, with their text."""
    cur = conn.cursor()
    cur.execute("SELECT canonical_id, display_name FROM model_version")
    population = build_population(cur.fetchall())
    cur.execute(
        "SELECT d.id, d.external_id, d.url, d.text_ref, d.harvest_run_id, h.query_key "
        "FROM document d LEFT JOIN harvest_run h ON h.id = d.harvest_run_id "
        "WHERE d.source = 'reddit' AND date(d.fetched_at) = current_date "
        "  AND d.retrieval_provenance = 'run_recorded' ORDER BY d.id"
    )
    out = []
    for doc_id, external_id, url, text_ref, _run_id, query_key in cur.fetchall():
        outcome = reader.resolve(text_ref) if text_ref else None
        if outcome is None or not outcome.found:
            continue
        payload = json.loads(outcome.require())
        text = (payload.get("title") or "") + "\n\n" + (payload.get("selftext") or "")
        verdict = triage(
            Document(text=text, is_self_post=payload.get("is_self")),
            population=population,
        )
        if getattr(verdict.verdict, "value", verdict.verdict) != "kept":
            continue
        out.append({
            "document_id": doc_id,
            "external_id": external_id,
            "url": url,
            "query_key": query_key,
            "subreddit": payload.get("subreddit"),
            "text": text,
        })
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cap-usd", type=float, default=1.00)
    parser.add_argument("--out", default="classification.jsonl")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    reader = RawStoreReader(RawStore(settings().raw_store_path))
    from collect.db import connect

    conn = connect()
    try:
        docs = survivors(conn, reader)
    finally:
        conn.close()
    if args.limit:
        docs = docs[: args.limit]

    budget = Budget(limit_usd=args.cap_usd)
    print(f"documents : {len(docs)} triage survivors")
    print(f"cap       : ${args.cap_usd:.2f}, enforced by Budget.check_before_call "
          f"BEFORE each request")
    print(f"estimate  : {len(docs)} x ${budget.estimated_next_call_usd:.5f} = "
          f"${len(docs) * budget.estimated_next_call_usd:.4f}")
    if args.dry_run:
        print("(dry run — no model call, no spend)")
        return 0

    system = system_prompt()
    client = OpenRouterClient.from_env()
    print(f"model     : {client.model}")
    rows: list[dict] = []
    stopped = None

    for i, doc in enumerate(docs, 1):
        try:
            budget.check_before_call()
        except BudgetExhausted as exhausted:
            stopped = str(exhausted)
            print(f"\nSTOPPED ON BUDGET after {i - 1} documents: {exhausted}")
            break
        try:
            completion = client.complete(
                system=system, user=doc["text"], tool_schema=TOOL_SCHEMA
            )
        except Exception as error:  # noqa: BLE001
            rows.append({**{k: v for k, v in doc.items() if k != "text"},
                         "error": f"{type(error).__name__}: {error}"})
            continue
        budget.charge(completion)
        # `raw_arguments`, kept as TEXT by the client on purpose: a schema
        # violation is something to log verbatim rather than something to have
        # already failed to parse. Same reason the runner salvages from it.
        try:
            parsed = {} if completion.is_empty else json.loads(completion.raw_arguments)
        except ValueError:
            parsed = {}
        quote = parsed.get("quote")
        # RULE 1's SHAPE, EVEN THOUGH THIS WRITES NO CLAIM. The model proposed
        # the quote; code checks it exists byte for byte in the text the model
        # was shown. A quote that does not verify is recorded as unverified, so
        # a fabricated span cannot be read as evidence.
        verified = bool(quote) and quote in doc["text"]
        rows.append({
            **{k: v for k, v in doc.items() if k != "text"},
            "is_capability_report": bool(parsed.get("is_capability_report")),
            "capability_key": parsed.get("capability_key"),
            "proposed_key": parsed.get("proposed_key"),
            "quote": quote,
            "quote_verified": verified,
            "reason": parsed.get("reason"),
            "input_tokens": completion.input_tokens,
            "output_tokens": completion.output_tokens,
        })
        if i % 25 == 0:
            print(f"  ...{i}/{len(docs)}  spent ${budget.spent_usd:.4f}")

    out = pathlib.Path(args.out)
    with out.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    classified = [r for r in rows if "error" not in r]
    yes = [r for r in classified if r["is_capability_report"]]
    assigned = [r for r in yes if r.get("capability_key")]
    proposed = [r for r in yes if r.get("proposed_key")]
    print(f"\nspent     : ${budget.spent_usd:.4f} of ${args.cap_usd:.2f} "
          f"over {budget.calls} calls")
    if stopped:
        print(f"            STOPPED ON BUDGET: {stopped}")
    print(f"errors    : {len(rows) - len(classified)}")
    print(f"DENOMINATOR: {len(classified)} triage survivors classified")
    rate = 100 * len(yes) / max(1, len(classified))
    print(f"  capability report      {len(yes):4d}  ({rate:5.1f}%)")
    print(f"  existing key assigned  {len(assigned):4d}")
    print(f"  new key proposed       {len(proposed):4d}")
    ok = sum(1 for r in yes if r["quote_verified"])
    print(f"  quote verified         {ok:4d} of {len(yes)}")
    print(f"\nresults   : {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
