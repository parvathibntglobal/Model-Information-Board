#!/usr/bin/env python
"""Did the one-line constraint stop the classifier folding the model into the key?

PAIRED ON IDENTICAL DOCUMENTS, which is the whole design. A fresh sample would
confound the prompt change with population drift, and the effect being measured
(15.4% -> ?) is small enough that drift could carry it either way. So this
re-runs a seeded sample of the SAME 774 documents the withheld run of
2026-08-28 used, resolved from the same raw store, and reports the before rate
and the after rate on those same documents.

THE BEFORE RATE IS RECOMPUTED, NOT QUOTED. 15.4% is the figure over all 552
proposals; the sample's own before rate is computed here from the stored run so
the two halves of the comparison share a denominator (rule 7).

Reads staging READ-ONLY and writes nothing to any database.
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import os
import pathlib
import random
import re
import sys
import urllib.parse
from dataclasses import replace
from datetime import UTC, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
    if m:
        os.environ.setdefault(m.group(1), m.group(2))

import psycopg  # noqa: E402

from collect.config import settings  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.rawstore_reader import RawStoreReader  # noqa: E402
from judge.extract.budget import Budget, BudgetExhausted  # noqa: E402
from judge.extract.client import OpenRouterClient  # noqa: E402
from scripts.classify_capability_reports import system_prompt, tool_schema  # noqa: E402

PRIOR = ROOT / "docs" / "measurements" / "model-only-classification-withheld.jsonl"
OUT = ROOT / "docs" / "measurements" / "key-constraint-rerun-2026-09-11.json"

#: A key naming any of these has folded the subject into the axis.
MODEL_WORDS = re.compile(
    r"claude|opus|sonnet|haiku|gpt|gemini|qwen|deepseek|mistral|llama|glm|kimi|"
    r"grok|colibri|audeta|anthropic|openai|google|fable|codex|copilot",
    re.I,
)


def key_name(pk):
    if not pk or str(pk).lower() in ("none", "null", ""):
        return None
    s = str(pk)
    if s.startswith("{"):
        try:
            return ast.literal_eval(s).get("name")
        except Exception:
            return None
    return s


def key_from_row(parsed: dict):
    """The proposed key, whichever field this variant puts it in.

    ⚠ THE FIRST RUN OF THIS SCRIPT READ ONLY `proposed_key` AND REPORTED ZERO
      PROPOSALS FROM 200 DOCUMENTS. The withheld and argued schemas both
      FLATTEN the proposal into `proposed_name`, for a reason
      `classify_capability_reports.tool_schema` states in a comment: a nested
      object came back null on every document. So the zero was this reader
      looking at a field the schema had deleted, not the model declining to
      propose - a null that measured the instrument. Both spellings are read
      here, and a run that finds neither is a real zero.
    """
    return key_name(parsed.get("proposed_name")) or key_name(parsed.get("proposed_key"))


def outcome_of(parsed: dict) -> str:
    """What the model DID with one document. Four outcomes, and the fourth is why.

    A COUNT OF PROPOSALS CANNOT TELL TWO ZEROS APART, and the two mean opposite
    things:

        a real zero      the constraint worked - every capability report still
                         got a capability, it just stopped naming a model
        a suppressed     the prompt talked the model out of proposing, so
        zero             reports come back with NO capability at all

    Both print `proposals: 0`. Only the per-document outcome separates them, so
    it is recorded per row rather than derived later.

    `silent` is the corner solution: the model said "yes, this document reports
    how a model behaved" and then named no capability, neither ratified nor
    proposed. That is the failure the withheld control was built to detect, and
    on the withheld variant it is ALWAYS a defect - there is no key list to
    assign from, so a report that proposes nothing has answered nothing.
    """
    if not parsed:
        return "no_tool_call"
    if not parsed.get("is_capability_report"):
        return "not_a_report"
    key = parsed.get("capability_key")
    if key not in (None, "", "null"):
        return "assigned_ratified"
    if key_from_row(parsed):
        return "proposed_new"
    return "silent"


def read_only_dsn() -> str:
    dsn = os.environ["DATABASE_URL"]
    sep = "&" if "?" in dsn else "?"
    ro = urllib.parse.quote("-c default_transaction_read_only=on")
    return f"{dsn}{sep}options={ro}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=200)
    ap.add_argument("--cap-usd", type=float, default=0.40)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--variant", choices=("withheld",), default="withheld",
        help="withheld = no key list (the 2026-08-28 control). `argued` - the "
             "middle prompt - is HELD: it was measured on 2026-09-14 and did "
             "not move fragmentation (rarefaction marginal 0.99 -> 0.97), which "
             "was the whole reason for it. It is not in "
             "`classify_capability_reports.py` on this branch, so offering the "
             "choice here would be a flag with nothing behind it - which is the "
             "defect this file was just repaired for.",
    )
    ap.add_argument(
        "--model", default="google/gemini-2.5-flash",
        help="PINNED, and pairing depends on it. The 2026-08-28 run used "
             "google/gemini-2.5-flash; EXTRACTOR_MODEL in .env is a different "
             "model today, and taking that default silently unpairs the "
             "comparison - which it did on the first run of this script.",
    )
    ap.add_argument(
        "--prior-model", default="google/gemini-2.5-flash",
        help="What produced the stored BEFORE run. Only used to say out loud "
             "whether this run is paired with it; it does not change behaviour.",
    )
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    with PRIOR.open(encoding="utf-8") as fh:
        prior = {r["document_id"]: r for r in (json.loads(line) for line in fh)}
    random.seed(args.seed)
    chosen = sorted(random.sample(sorted(prior), args.sample))

    reader = RawStoreReader(RawStore(settings().raw_store_path))
    with psycopg.connect(read_only_dsn(), connect_timeout=10) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, text_ref FROM document WHERE id = ANY(%s)", (chosen,))
        refs = dict(cur.fetchall())

    docs = []
    for did in chosen:
        outcome = reader.resolve(refs[did]) if refs.get(did) else None
        if outcome is None or not outcome.found:
            continue
        p = json.loads(outcome.require())
        docs.append({"document_id": did,
                     "text": (p.get("title") or "") + "\n\n" + (p.get("selftext") or "")})

    # ── the BEFORE rate, on these same documents ───────────────────────────
    before_keys = [key_name(prior[d["document_id"]].get("proposed_key")) for d in docs]
    before_keys = [k for k in before_keys if k]
    before_named = [k for k in before_keys if MODEL_WORDS.search(k)]
    print(f"documents resolved : {len(docs)} of {args.sample}")
    print(f"BEFORE  proposals  : {len(before_keys)}   naming a model: "
          f"{len(before_named)} = {len(before_named)/len(before_keys)*100:.1f}%")

    budget = Budget(limit_usd=args.cap_usd)
    print(f"cap                : ${args.cap_usd:.2f}   estimate "
          f"${len(docs)*budget.estimated_next_call_usd:.4f}")
    if args.dry_run:
        print("(dry run - no model call, no spend)")
        return 0

    # THE VARIANT REACHES THE PROMPT. This read `withhold_keys=True` with
    # `args.variant` ignored, so `--variant argued` silently ran the WITHHELD
    # prompt and labelled the output `argued`. Second dead flag in one file.
    system = system_prompt(withhold_keys=args.variant == "withheld")
    schema = tool_schema(withhold_keys=args.variant == "withheld")

    # THE MODEL REACHES THE CLIENT, AND THIS WAS THE DEFECT THE FILE DESCRIBED
    # AND DID NOT HAVE. `--model` carried a help string explaining that pairing
    # depends on pinning and that taking `EXTRACTOR_MODEL` "silently unpairs the
    # comparison - which it did on the first run of this script". Then
    # `from_env()` read `EXTRACTOR_MODEL` anyway and `args.model` was never
    # read, so the run that was supposed to prove the pinning had been fixed was
    # itself unpaired: before=google/gemini-2.5-flash, after=deepseek/deepseek-
    # v4-flash, 134 proposals -> 0, two variables moved at once.
    #
    # `from_env()` is kept for the key, which must not pass through argv.
    client = replace(OpenRouterClient.from_env(), model=args.model)
    print(f"model              : {client.model}   (--model, not EXTRACTOR_MODEL)")
    prior_model = args.prior_model
    if client.model != prior_model:
        print(f"  !! UNPAIRED: the prior run used {prior_model}. Any difference "
              "below confounds the prompt with the model.")
    else:
        print(f"  paired with the prior run ({prior_model})")
    print()

    rows, stopped = [], None
    for i, doc in enumerate(docs, 1):
        try:
            budget.check_before_call()
        except BudgetExhausted as e:
            stopped = str(e)
            print(f"STOPPED ON BUDGET after {i-1} documents: {e}")
            break
        try:
            c = client.complete(system=system, user=doc["text"], tool_schema=schema)
        except Exception as e:  # noqa: BLE001
            rows.append({"document_id": doc["document_id"], "error": f"{type(e).__name__}: {e}"})
            continue
        budget.charge(c)
        try:
            parsed = {} if c.is_empty else json.loads(c.raw_arguments)
        except ValueError:
            parsed = {}
        rows.append({
            "document_id": doc["document_id"],
            "is_capability_report": parsed.get("is_capability_report"),
            "capability_key": parsed.get("capability_key"),
            "proposed_key": key_from_row(parsed),
            "closest_existing_key": parsed.get("closest_existing_key"),
            "why_existing_insufficient": parsed.get("why_existing_insufficient"),
            "outcome": outcome_of(parsed),
        })
        if i % 25 == 0:
            print(f"  {i}/{len(docs)}  spent ${budget.spent_usd:.4f}")

    def rarefy(seq, trials: int = 40):
        """Distinct keys as a function of proposals seen, mean over shuffles.

        THE COUNT ALONE CANNOT TELL TWO PROMPTS APART. A prompt yielding 200
        keys from 200 documents has the withheld run's problem at a smaller
        number, and only the marginal rate shows it. Reported for whatever is
        run, always.
        """
        if len(seq) < 10:
            return {}
        steps = [n for n in range(10, len(seq) + 1, max(10, len(seq) // 10))]
        if steps[-1] != len(seq):
            steps.append(len(seq))
        out = {}
        for n in steps:
            tot = 0
            for t in range(trials):
                tot += len(set(random.Random(t).sample(seq, n)))
            out[n] = round(tot / trials, 1)
        return out

    after_keys = [r.get("proposed_key") for r in rows]
    after_keys = [k for k in after_keys if k]
    after_named = [k for k in after_keys if MODEL_WORDS.search(k)]
    if after_keys:
        print(f"\nAFTER   proposals  : {len(after_keys)}   naming a model: "
              f"{len(after_named)} = {len(after_named)/len(after_keys)*100:.1f}%")
    else:
        # NOT "no proposals" AND NOTHING ELSE. A bare zero here is what made the
        # first result unreadable: it looks like the constraint worked and it
        # looks like the prompt suppressed proposing, and the line cannot say
        # which. The outcome table below is the thing that can.
        print("\nAFTER   proposals  : 0   <- see the outcome table before reading this")
    for k in after_named[:10]:
        print(f"    still names a model: {k}")

    curve = rarefy(after_keys)
    if curve:
        pts = sorted(curve)
        print("\n  rarefaction (proposals -> distinct keys, mean of 40 shuffles)")
        print("   " + "".join(f"{n:>7}" for n in pts))
        print("   " + "".join(f"{curve[n]:>7.1f}" for n in pts))
        if len(pts) >= 3:
            head = (curve[pts[1]] - curve[pts[0]]) / (pts[1] - pts[0])
            tail = (curve[pts[-1]] - curve[pts[-2]]) / (pts[-1] - pts[-2])
            print(f"   marginal new keys per proposal: first {head:.2f}  last {tail:.2f}")
            print(f"   {'NOT converging' if tail > 0.5 else 'converging'}")

    # ── WHAT HAPPENED TO EVERY DOCUMENT, which is what separates the two zeros ──
    outcomes = collections.Counter(r.get("outcome") for r in rows)
    reports = sum(v for k, v in outcomes.items()
                  if k in ("assigned_ratified", "proposed_new", "silent"))
    assigned = outcomes["assigned_ratified"]
    silent = outcomes["silent"]
    print("\n  OUTCOME PER DOCUMENT")
    print(f"    not a capability report    : {outcomes['not_a_report']}")
    print(f"    no tool call / unparseable : {outcomes['no_tool_call']}")
    print(f"    capability reports         : {reports}")
    print(f"      assigned a ratified key  : {assigned}")
    print(f"      proposed a new key       : {outcomes['proposed_new']}"
          f"   distinct {len(set(after_keys))}")
    print(f"      SILENT (named neither)   : {silent}")
    if reports:
        print(f"    silent share of reports    : {silent/reports*100:.1f}%")
    if args.variant == "withheld" and silent:
        print("    !! ON THE WITHHELD VARIANT EVERY `silent` IS A DEFECT: there is "
              "no key list to assign from, so a report naming no capability has "
              "answered nothing. A zero with silent > 0 is a SUPPRESSED zero, "
              "not a clean one.")
    print(f"\nspent              : ${budget.spent_usd:.4f}")

    out_path = pathlib.Path(args.out) if args.out else OUT
    out_path.write_text(json.dumps({
        "ran_at": datetime.now(UTC).isoformat(),
        "design": "paired: the same documents, re-run with the behaviour-only key constraint",
        "prior_run": str(PRIOR.relative_to(ROOT)),
        "sample": args.sample, "seed": args.seed,
        "documents_resolved": len(docs),
        "prompt_label": (f"capability-classification/{args.variant}/"
                         f"behaviour-only/2026-09-11"),
        "proposer_model": client.model,
        "spent_usd": round(budget.spent_usd, 4),
        "stopped_on_budget": stopped,
        "variant": args.variant,
        "before": {"proposals": len(before_keys), "naming_a_model": len(before_named),
                   "distinct": len(set(before_keys)),
                   "rarefaction": rarefy(before_keys),
                   "examples": before_named[:10]},
        "after": {"proposals": len(after_keys), "naming_a_model": len(after_named),
                  "naming_a_model_pct": (round(len(after_named)/len(after_keys)*100, 1)
                                         if after_keys else None),
                  "distinct": len(set(after_keys)),
                  "assigned_to_ratified": assigned,
                  "rarefaction": curve,
                  "examples": after_named[:10],
                  # The zero-disambiguator. A run with proposals=0 and silent=0
                  # is a clean zero; proposals=0 with silent>0 is a suppressed
                  # one, and on the withheld variant every silent row is a
                  # defect. Stored so a later reader need not re-derive it.
                  "outcomes": dict(outcomes),
                  "capability_reports": reports,
                  "silent": silent,
                  "silent_share_of_reports": (round(silent/reports*100, 1)
                                              if reports else None)},
        "rows": rows,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
