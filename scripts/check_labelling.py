"""Refuse a returned labelling that is not usable. Run it at hand-back.

    py -3 scripts/check_labelling.py fixtures/golden/<file>.jsonl
    py -3 scripts/check_labelling.py fixtures/golden/*.jsonl --source <pool>.jsonl

WHY THIS EXISTS, AND IT IS NOT ABOUT CARE
------------------------------------------
Four labelling exports in a row came back with `labelled_by: "anon"`. The
builders write `None`; the labelling tool substitutes a placeholder when its
name is unset, and the tool is not in this repository so it cannot be fixed from
here. Asking somebody to remember is what has already failed four times.

And the fifth round found something worse than a wrong name. One of the two
round-2 files had **14 of 48 rows completely blank** - including all ten Reddit
rows, which are the only place the category round 2 was built for applies. That
was discovered by hand, three steps into a comparison, after the numbers had
been computed once. A validator at hand-back turns both of those from things
somebody notices into things the file cannot hide.

WHAT IT CHECKS, AND WHY EACH ONE IS HERE
-----------------------------------------
    PLACEHOLDER NAME    `anon` and friends. Four rounds.
    NAME DISAGREES      `_meta.labelled_by` against the filename's `--by-x`.
                        The anooj files said `anon` in the field and `anooj` in
                        the name, every time.
    INCOMPLETE          any answer left null. 14 of 48 went unnoticed.
    UNANSWERABLE        an answer not in that row's own `allowed_answers`. The
                        pool carries the scope per row precisely so a tool
                        cannot offer an option the row does not support; this is
                        the check that the tool honoured it.
    ROW DRIFT           `row_index`, `document_id` and `quote` against the
                        unlabelled source, when `--source` is given. A pool that
                        changed under a labeller invalidates their work silently,
                        and comparing two files built from different pools is the
                        failure this cannot be allowed to reach.

EXIT CODE IS THE POINT. 0 means the file can be compared. Anything else means it
cannot, and the reason is on stdout rather than in somebody's memory.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

#: Names that mean "nobody set this". Compared casefolded.
PLACEHOLDERS = {
    "anon", "anonymous", "unknown", "none", "null", "user", "labeller",
    "test", "tbd", "",
}

#: `--labelled-by-anooj.jsonl` -> `anooj`. The character class deliberately
#: excludes `.` so the extension is not captured as part of the name.
_BY_NAME = re.compile(r"--(?:labelled-)?by-([a-z0-9_-]+)", re.I)


def load(path: Path):
    lines = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines or "_meta" not in lines[0]:
        raise ValueError(f"{path}: first line is not a _meta header")
    return lines[0]["_meta"], lines[1:]


def answers_of(row: dict) -> dict:
    """Round 2 shape (`answers` dict) or round 1 shape (a single `label`)."""
    if "answers" in row:
        return dict(row["answers"])
    if "label" in row:
        return {"label": row["label"]}
    return {}


def allowed_of(row: dict) -> dict:
    if "allowed_answers" in row:
        return dict(row["allowed_answers"])
    if "allowed_labels" in row:
        return {"label": list(row["allowed_labels"])}
    return {}


def check(path: Path, source: Path | None) -> list[str]:
    problems: list[str] = []
    meta, rows = load(path)

    # ── the name ────────────────────────────────────────────────────────────
    declared = (meta.get("labelled_by") or "").strip()
    if declared.casefold() in PLACEHOLDERS:
        problems.append(
            f"PLACEHOLDER NAME: _meta.labelled_by is {declared!r}. The labelling "
            "tool substitutes this when its name is unset. Set the name in the "
            "tool and re-export - patching the file has not held four times."
        )
    from_name = _BY_NAME.search(path.name)
    if from_name and declared and declared.casefold() not in PLACEHOLDERS:
        expected = from_name.group(1).casefold()
        if not declared.casefold().startswith(expected.rstrip("0123456789")):
            problems.append(
                f"NAME DISAGREES: filename says {from_name.group(1)!r}, "
                f"_meta.labelled_by says {declared!r}"
            )
    row_names = {(r.get("labelled_by") or "").strip() for r in rows}
    bad_rows = {n for n in row_names if n.casefold() in PLACEHOLDERS and n != ""}
    if bad_rows:
        problems.append(f"PLACEHOLDER NAME on rows: {sorted(bad_rows)}")

    # ── completeness ────────────────────────────────────────────────────────
    blank_rows, partial_rows = [], []
    for r in rows:
        ans = answers_of(r)
        if not ans:
            continue
        nulls = [q for q, v in ans.items() if v is None]
        if len(nulls) == len(ans):
            blank_rows.append(r.get("row_index"))
        elif nulls:
            partial_rows.append((r.get("row_index"), nulls))
    if blank_rows:
        problems.append(
            f"INCOMPLETE: {len(blank_rows)} of {len(rows)} rows are entirely "
            f"unanswered -> {blank_rows}"
        )
    if partial_rows:
        problems.append(
            f"INCOMPLETE: {len(partial_rows)} rows answer some questions and not "
            f"others -> {partial_rows}"
        )

    # ── answers inside the row's own scope ──────────────────────────────────
    off_scope = []
    for r in rows:
        allowed = allowed_of(r)
        for q, v in answers_of(r).items():
            if v is None or q not in allowed:
                continue
            if v not in allowed[q]:
                off_scope.append((r.get("row_index"), q, v))
    if off_scope:
        problems.append(
            f"UNANSWERABLE: {len(off_scope)} answers are outside the row's own "
            f"allowed_answers -> {off_scope[:8]}"
        )

    # ── the pool did not move under the labeller ────────────────────────────
    if source is not None:
        _, src_rows = load(source)
        src = {r["row_index"]: r for r in src_rows}
        got = {r["row_index"]: r for r in rows}
        if set(src) != set(got):
            problems.append(
                f"ROW DRIFT: row_index sets differ from {source.name}. "
                f"missing {sorted(set(src) - set(got))[:8]}, "
                f"extra {sorted(set(got) - set(src))[:8]}"
            )
        drifted = [
            i for i in sorted(set(src) & set(got))
            if src[i].get("document_id") != got[i].get("document_id")
            or src[i].get("quote") != got[i].get("quote")
        ]
        if drifted:
            problems.append(
                f"ROW DRIFT: {len(drifted)} rows have a different document_id or "
                f"quote than {source.name} -> {drifted[:8]}. Their labels are "
                "answers to a question that is no longer being asked."
            )
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", type=Path, nargs="+")
    ap.add_argument(
        "--source", type=Path, default=None,
        help="the unlabelled pool these were built from, to catch row drift")
    args = ap.parse_args(argv)

    worst = 0
    for path in args.files:
        problems = check(path, args.source)
        print(f"{path.name}")
        if not problems:
            print("  OK - usable for comparison")
        for p in problems:
            print(f"  REFUSED: {p}")
            worst = 1
        print()
    if worst:
        print("At least one file cannot be compared. Fix and re-export.")
    return worst


if __name__ == "__main__":
    sys.exit(main())
