"""Transcribe a labeller's answers into a golden pool. TRANSCRIPTION ONLY.

    py -3 scripts/load_round3_labels.py answers.txt --by anooj
    py -3 scripts/check_labelling.py \
        fixtures/golden/capability-choice-round3--labelled-by-anooj.jsonl \
        --source fixtures/golden/capability-choice-round3--unlabelled.jsonl

WHY THIS EXISTS AND WHAT IT REFUSES TO DO
------------------------------------------
The pool is the instrument that measures the extractor, so a label it did not
come from a labeller is not a label. This script therefore **copies** answers
and never supplies, repairs or infers one:

  - every row_index 0..N must appear EXACTLY ONCE, or it refuses. A missing row
    is not silently left null - `check_labelling.py` would catch that later, but
    later is after somebody has computed a number from it.
  - every answer must be in THAT ROW's own `allowed_answers`, or it refuses and
    names the row. The pool carries scope per row precisely so a tool cannot
    offer an option the row does not support.
  - nothing else in the row is touched. The quote, the document id and the
    row_index are copied verbatim so `--source` drift detection means something.

An answer that looks wrong is NOT corrected here. Flag it and let the labeller
re-do it: a golden set someone else corrected is not a golden set.

THE INPUT FORMAT is deliberately the dullest thing that can carry the data, so
a labeller can produce it from anything:

    0: cannot-tell
    1: code.generation
    # blank lines and # comments ignored

CAVEATS BELONG IN `_meta`, NOT IN A COMMIT MESSAGE. `--caveat` appends a line
to `_meta.caveats`, which is where a reader of the scored figure will be. A
labelling produced under a condition that bounds what it supports must say so
in the file that carries it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "fixtures" / "golden"

_LINE = re.compile(r"^\s*(\d+)\s*[:=]\s*(\S+)\s*$")


def parse_answers(text: str) -> dict[int, str]:
    """`row_index: answer` per line. Refuses a duplicate rather than last-wins."""
    out: dict[int, str] = {}
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE.match(line)
        if not m:
            raise SystemExit(f"line {lineno}: cannot read {raw!r} as `index: answer`")
        idx, answer = int(m.group(1)), m.group(2)
        if idx in out:
            raise SystemExit(
                f"line {lineno}: row {idx} answered twice ({out[idx]!r} then "
                f"{answer!r}). Refusing rather than picking one."
            )
        out[idx] = answer
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("answers", type=Path, help="`row_index: answer` per line")
    ap.add_argument("--by", required=True, help="the labeller's name")
    ap.add_argument(
        "--pool",
        type=Path,
        default=GOLDEN / "capability-choice-round3--unlabelled.jsonl",
    )
    ap.add_argument("--question", default="capability")
    ap.add_argument(
        "--caveat",
        action="append",
        default=[],
        help="a condition that bounds what this labelling supports; repeatable",
    )
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    lines = [
        json.loads(line)
        for line in args.pool.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if "_meta" not in lines[0]:
        raise SystemExit(f"{args.pool}: first line is not a _meta header")
    meta, rows = dict(lines[0]["_meta"]), [dict(r) for r in lines[1:]]

    answers = parse_answers(args.answers.read_text(encoding="utf-8"))

    expected = {r["row_index"] for r in rows}
    missing = sorted(expected - set(answers))
    extra = sorted(set(answers) - expected)
    if missing or extra:
        raise SystemExit(
            f"REFUSING. {len(answers)} answers against {len(rows)} rows.\n"
            f"  missing row_index: {missing}\n"
            f"  not in this pool : {extra}\n"
            "An incomplete labelling scored as if it were complete is the "
            "failure this refuses to enable."
        )

    off_scope = []
    for r in rows:
        answer = answers[r["row_index"]]
        allowed = r["allowed_answers"][args.question]
        if answer not in allowed:
            off_scope.append((r["row_index"], answer))
    if off_scope:
        raise SystemExit(
            "REFUSING. Answers outside the row's own allowed_answers:\n"
            + "\n".join(f"  row {i}: {a!r}" for i, a in off_scope)
        )

    for r in rows:
        r["answers"] = dict(r["answers"])
        r["answers"][args.question] = answers[r["row_index"]]
        r["labelled_by"] = args.by

    meta["labelled_by"] = args.by
    meta["transcribed_by"] = (
        "scripts/load_round3_labels.py - a copy, not a judgement. The answers "
        "came from the labeller; this script refuses to supply or repair one."
    )
    if args.caveat:
        meta["caveats"] = list(meta.get("caveats", ())) + list(args.caveat)

    out = args.out or (
        GOLDEN / f"capability-choice-round3--labelled-by-{args.by}.jsonl"
    )
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"_meta": meta}, ensure_ascii=False) + "\n")
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"wrote {out}")
    print(f"  {len(rows)} rows, all answered, all in scope")
    from collections import Counter

    for answer, n in Counter(answers.values()).most_common():
        print(f"  {n:3d}  {answer}")
    if args.caveat:
        print(f"  {len(args.caveat)} caveat(s) recorded in _meta.caveats")
    print("\nNow run scripts/check_labelling.py with --source before scoring it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
