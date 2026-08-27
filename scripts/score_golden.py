#!/usr/bin/env python
"""Read a labelled golden file and say what it measures. #17.

Until this existed, labelling had no destination: two people could label 48
claims and nothing turned the two files into a number. This is that reader.

It answers two different questions and keeps them apart, because they are about
different things:

  AGREEMENT (labeller vs labeller) measures the INSTRUMENT. If two careful
  people disagree, the question is ambiguous and no gold built from it is
  trustworthy yet. Reported as raw agreement AND Cohen's kappa — kappa because
  raw agreement flatters a skewed set (if 90% of claims are "supported", two
  people guessing "supported" agree 81% of the time knowing nothing), and kappa
  subtracts exactly that chance floor.

  ACCURACY (gold vs extractor) measures the EXTRACTOR, against the settled human
  answer. This is the only check that catches a verbatim quote carrying a false
  reading (#19) — rule 1 proves the quote is real, never that the claim is.

Three honesty rules it will not break:

  - EVERY figure carries N and the population it came from (rule 7). A rate with
    no denominator is refused; the file's `_meta` caveat is printed beside it.
  - ROUNDS ARE NOT A TREND. Round 1 was one question with 4 options; round 2 is
    two questions with 3 and 4. More categories cost kappa at small n before
    they buy anything, so a round-2 figure beside round-1's reads as a decline
    in the labellers when it is a change in the instrument. This script refuses
    to print them together.
  - NULL IS NOT A DISAGREEMENT (rule 6). A row one labeller left blank is not
    counted as a mismatch; it is excluded and the exclusion is reported, because
    "we did not both look" and "we looked and differed" are different findings.

No database, no model, stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "fixtures" / "golden"


def load_rows(path: Path) -> tuple[dict[str, Any], list[dict]]:
    """Return (meta, data_rows). The first `_meta` line is metadata, not a row."""
    meta: dict[str, Any] = {}
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if "_meta" in obj:
            meta = obj["_meta"]
            continue
        rows.append(obj)
    return meta, rows


def answers_of(row: dict) -> dict[str, Any]:
    """The answer dict for a row, whatever shape the file uses.

    `answers` (round 2/3), `reconciled` (the settled gold), or a bare `label`
    (round 1). Returned uniformly so one comparison works across rounds.
    """
    if isinstance(row.get("answers"), dict):
        return row["answers"]
    if isinstance(row.get("reconciled"), dict):
        return row["reconciled"]
    if "label" in row:
        return {"label": row["label"]}
    return {}


def questions_in(rows: list[dict]) -> list[str]:
    keys: list[str] = []
    for row in rows:
        for k in answers_of(row):
            if k not in keys:
                keys.append(k)
    return keys


def cohen_kappa(pairs: list[tuple[Any, Any]]) -> float | None:
    """Chance-corrected agreement for two raters over the same items.

    None when it is undefined: with pe == 1 (both raters used one category for
    everything) there is no chance floor to correct against, and (po-pe)/(1-pe)
    divides by zero. That is a real state — perfect skew — not a score, so it is
    named rather than rendered as 0.0 or 1.0.
    """
    n = len(pairs)
    if not n:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    a_counts = Counter(a for a, _ in pairs)
    b_counts = Counter(b for _, b in pairs)
    pe = sum((a_counts[c] / n) * (b_counts[c] / n) for c in set(a_counts) | set(b_counts))
    if pe >= 1.0:
        return None
    return (po - pe) / (1.0 - pe)


def inter_labeller(rows_a: list[dict], rows_b: list[dict]) -> dict[str, dict]:
    """Per-question agreement between two labellers, aligned by row_index."""
    by_a = {r["row_index"]: answers_of(r) for r in rows_a}
    by_b = {r["row_index"]: answers_of(r) for r in rows_b}
    shared = sorted(set(by_a) & set(by_b))

    out: dict[str, dict] = {}
    for q in questions_in(rows_a + rows_b):
        pairs: list[tuple[Any, Any]] = []
        skipped = 0
        for idx in shared:
            a, b = by_a[idx].get(q), by_b[idx].get(q)
            if a is None or b is None:
                skipped += 1  # rule 6: not-both-looked is excluded, not a miss
                continue
            pairs.append((a, b))
        agree = sum(1 for a, b in pairs if a == b)
        out[q] = {
            "n": len(pairs),
            "skipped_unlabelled": skipped,
            "agree": agree,
            "agreement": (agree / len(pairs)) if pairs else None,
            "kappa": cohen_kappa(pairs),
        }
    return out


def extractor_accuracy(
    gold: dict[int, Any], sidecar: dict[int, Any]
) -> dict[str, Any]:
    """How often the settled human answer matched the extractor's choice."""
    shared = sorted(set(gold) & set(sidecar))
    graded = [(gold[i], sidecar[i]) for i in shared if gold[i] is not None]
    correct = sum(1 for g, e in graded if g == e)
    return {
        "n": len(graded),
        "ungraded_no_gold": len(shared) - len(graded),
        "correct": correct,
        "accuracy": (correct / len(graded)) if graded else None,
        "mismatches": [
            {"row_index": i, "gold": gold[i], "extractor": sidecar[i]}
            for i in shared
            if gold[i] is not None and gold[i] != sidecar[i]
        ],
    }


def build_round2_gold(
    rows_a: list[dict], rows_b: list[dict], reconciled: list[dict]
) -> dict[str, dict]:
    """The round-2 gold: rows the two labellers agreed on, plus the reconciled ones.

    KEYED BY QUOTE, not row_index. The reconciliation file was written with its
    own 0..N indexing over just the disagreements, so a row_index merge silently
    pairs the wrong rows; the quote is the stable id both files share. A
    disagreement is not gold until it is settled, so an unreconciled one is left
    OUT rather than resolved to one labeller's answer.
    """
    by_a = {r["quote"]: answers_of(r) for r in rows_a if "quote" in r}
    by_b = {r["quote"]: answers_of(r) for r in rows_b if "quote" in r}
    settled = {r["quote"]: answers_of(r) for r in reconciled if "quote" in r}

    gold: dict[str, dict] = {}
    for quote in set(by_a) & set(by_b):
        a, b = by_a[quote], by_b[quote]
        if quote in settled and any(v is not None for v in settled[quote].values()):
            gold[quote] = settled[quote]
        elif a and a == b and all(v is not None for v in a.values()):
            gold[quote] = a
        # else: unsettled disagreement — deliberately not in the gold
    return gold


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{x * 100:.1f}%"


def _kappa_word(k: float | None) -> str:
    if k is None:
        return "undefined (one category carried everything — perfect skew, not a score)"
    # Landis & Koch bands, named so a bare number is not over-read.
    band = (
        "poor" if k < 0.0 else "slight" if k < 0.2 else "fair" if k < 0.4
        else "moderate" if k < 0.6 else "substantial" if k < 0.8 else "almost perfect"
    )
    return f"{k:.3f} ({band})"


def _print_caveat(meta: dict) -> None:
    for key in ("DENOMINATOR", "caveat", "population_basis", "corpus"):
        if meta.get(key):
            print(f"  population — {meta[key]}")
            return


def cmd_agree(args) -> int:
    meta_a, rows_a = load_rows(Path(args.file_a))
    _, rows_b = load_rows(Path(args.file_b))
    print(f"AGREEMENT (the instrument) — {Path(args.file_a).name} vs {Path(args.file_b).name}")
    _print_caveat(meta_a)
    result = inter_labeller(rows_a, rows_b)
    for q, r in result.items():
        print(f"\n  question: {q}")
        print(f"    n compared      : {r['n']}   "
              f"(excluded, one side blank: {r['skipped_unlabelled']})")
        print(f"    raw agreement   : {r['agree']}/{r['n']} = {_pct(r['agreement'])}")
        print(f"    Cohen's kappa   : {_kappa_word(r['kappa'])}")
    print("\n  kappa, not raw agreement, is the number to quote: raw agreement "
          "flatters a skewed set. Rounds are different instruments — do not trend them.")
    return 0


def cmd_round2(args) -> int:
    base = Path(args.dir)
    meta, rows_a = load_rows(base / "extraction-reading-round2--labelled-by-anooj.jsonl")
    _, rows_b = load_rows(base / "extraction-reading-round2--labelled-by-yathu.jsonl")
    recon_path = base / "pool--reconciled.jsonl"
    reconciled = load_rows(recon_path)[1] if recon_path.exists() else []

    print("ROUND 2 — extraction reading (who is speaking · is the claim sound · contains)")
    _print_caveat(meta)
    print("\n-- labeller agreement per question, BEFORE reconciliation --")
    print("   (each row asks ONE question, so the n differ; kappa is the number to quote)")
    for q, r in inter_labeller(rows_a, rows_b).items():
        print(f"  {q:20} {r['agree']}/{r['n']} = {_pct(r['agreement'])}, "
              f"kappa {_kappa_word(r['kappa'])}"
              + (f"   [{r['skipped_unlabelled']} unfinished, excluded]"
                 if r["skipped_unlabelled"] else ""))

    # Reconciliation status is reported as a raw count from the reconcile file,
    # NOT as a merged gold total: the reconcile file was indexed on its own
    # disagreement subset and the round-2 rows mix question types, so a single
    # merged "settled" number over both would pair rows that are not the same
    # row. `build_round2_gold` (quote-keyed) is the library path for a consistent
    # pair; here we state what is verifiable and no more (rule 7).
    recon_filled = sum(
        1 for r in reconciled if any(v is not None for v in answers_of(r).values())
    )
    print(f"\n-- reconciliation -- pool--reconciled.jsonl: {recon_filled} rows settled. "
          "The gold is the agreed rows plus these; an unsettled disagreement is not gold.")
    return 0


def cmd_round3(args) -> int:
    base = Path(args.dir)
    labelled = Path(args.labelled) if args.labelled else (
        base / "capability-choice-round3--unlabelled.jsonl"
    )
    meta, rows = load_rows(labelled)
    _, side = load_rows(base / "capability-choice-round3--extractor-chose.jsonl")
    sidecar = {r["row_index"]: r["extractor_chose"] for r in side}
    gold = {r["row_index"]: answers_of(r).get("capability") for r in rows}

    labelled_n = sum(1 for v in gold.values() if v is not None)
    print(f"ROUND 3 — capability choice (was the extractor's key right?)  [{labelled.name}]")
    _print_caveat(meta)
    if labelled_n == 0:
        print(f"\n  NOT LABELLED YET — 0 of {len(gold)} rows carry answers.capability. "
              "Label them (tools/label-pool.html, capability mode) and re-run. "
              "Nothing is scored, which is different from a score of zero.")
        return 0

    acc = extractor_accuracy(gold, sidecar)
    print(f"\n  extractor accuracy on THIS pool: "
          f"{acc['correct']}/{acc['n']} = {_pct(acc['accuracy'])}")
    print(f"  ({acc['ungraded_no_gold']} rows still unlabelled, excluded)")
    print("  NOT a pipeline misfiling rate: one site, one author, one extractor, one draw.")
    if acc["mismatches"]:
        print("\n  where gold and extractor differ:")
        for m in acc["mismatches"][:20]:
            print(f"    row {m['row_index']:>2}: gold={m['gold']}  extractor={m['extractor']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("agree", help="inter-labeller agreement between two labelled files")
    a.add_argument("file_a")
    a.add_argument("file_b")
    a.set_defaults(func=cmd_agree)

    r2 = sub.add_parser("round2", help="round-2 reading: agreement + gold coverage")
    r2.add_argument("--dir", default=str(GOLDEN))
    r2.set_defaults(func=cmd_round2)

    r3 = sub.add_parser("round3", help="round-3 capability: extractor accuracy vs gold")
    r3.add_argument("--dir", default=str(GOLDEN))
    r3.add_argument("--labelled", default=None,
                    help="a labelled round-3 file (default: the unlabelled template)")
    r3.set_defaults(func=cmd_round3)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
