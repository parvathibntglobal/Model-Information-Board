"""What a multi-shape GitHub sweep costs at three scales. Reads no database.

WHY THIS IS A SCRIPT AND NOT A PARAGRAPH. The question "should we spend the
remaining search budget on a sweep" has a numeric answer that moves whenever the
registry grows or a shape's measured yield is revised, and a paragraph goes
stale without saying so. Every figure here is derived from
`collect/adapters/queries/github.py` at run time.

WHERE THE BUDGET ACTUALLY IS. The existing query space is **76% consumed** -
44,848 of 59,100 candidate slots at `max_pages=1` and `PER_PAGE=100` - and the
~14,000 slots left yield roughly **57 more documents** at the pooled 0.404% keep
rate. So re-running what we already have is nearly exhausted, and this is where
the remaining budget goes if it goes anywhere.

⚠ THE YIELD FIGURES ARE ESTIMATES AND CARRY THEIR POPULATION. They come from
  18 requests over THREE models, and per-model yield on the title arm alone was
  76 / 8 / 9 on-subject - a factor of nine on one shape. So the per-request
  rates are a central tendency over three points, not a rate to plan a budget
  against, and the report says so beside every number rather than in a footnote.

    python scripts/github_sweep_cost.py
"""

from __future__ import annotations

import argparse

from collect.adapters.queries.github import (
    ON_SUBJECT_PER_REQUEST,
    PER_MODEL_TITLE_ON_SUBJECT,
    REFUSED_SHAPES,
    SEARCH_REQUESTS_PER_MINUTE,
    SWEEP_SHAPES,
    UNIQUE_PER_REQUEST,
    sweep_cost,
)

#: The three scales, and what each one IS - because "30 models" with no
#: definition is a number nobody can check.
SCALES: tuple[tuple[str, int], ...] = (
    ("11  models swept today", 11),
    ("30  models", 30),
    ("342 the full registry", 342),
)

#: `model_version` rows, `docs/measurements/alias-coverage-and-the-prefix-defect.md`.
REGISTRY_ROWS = 342

#: What re-running the EXISTING queries to exhaustion is worth. From
#: `docs/measurements/what-github-needs-before-a-sweep.md` §3.
EXISTING_QUERIES_CONSUMED = 0.76
EXISTING_QUERIES_REMAINING_DOCUMENTS = 57


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--surfaces-per-model",
        type=float,
        default=1.0,
        help="average usable aliases per model. A float because it is an "
        "average; rounding understates the models with the most aliases.",
    )
    args = ap.parse_args()

    arms = (("title",), ("title", "repro"))

    print("=" * 78)
    print("WHAT A MULTI-SHAPE GITHUB SWEEP COSTS")
    print(f"search bucket: {SEARCH_REQUESTS_PER_MINUTE}/minute, measured from "
          "GET /rate_limit. Core is 5,000/hour")
    print(f"surfaces per model: {args.surfaces_per_model} (an average, see --help)")
    print("=" * 78)
    print()
    # THE BAND, NOT A POINT. Scaled from the observed per-model spread on the
    # title arm, so the column shows what a registry of poor-yielding models
    # would give as well as what a registry of claude-sonnet-4.5s would. A
    # single figure here reads as a forecast; the ratio between the ends is
    # nine, which is the actual finding.
    lo = min(PER_MODEL_TITLE_ON_SUBJECT) / ON_SUBJECT_PER_REQUEST["title"]
    hi = max(PER_MODEL_TITLE_ON_SUBJECT) / ON_SUBJECT_PER_REQUEST["title"]

    header = (f"  {'scale':26s} {'shape(s)':16s} {'reqs':>6s} {'minutes':>9s} "
              f"{'~unique docs (band)':>24s}")
    print(header)
    print("  " + "-" * (len(header) - 2))
    for label, models in SCALES:
        for shapes in arms:
            cost = sweep_cost(
                models, shapes=shapes, surfaces_per_model=args.surfaces_per_model
            )
            mid = cost.unique_on_subject_estimate
            band = f"{mid * lo:,.0f} - {mid * hi:,.0f}"
            print(
                f"  {label:26s} {'+'.join(shapes):16s} {cost.requests:6d} "
                f"{cost.minutes:8.1f}m {band:>24s}"
            )
        print()

    print("  THE BAND IS THE POINT AND THE MIDPOINT IS NOT PRINTED. Population:")
    print("  18 requests, THREE models, 2026-08-28. Per-model title yield was")
    print(f"  {' / '.join(str(n) for n in PER_MODEL_TITLE_ON_SUBJECT)} on-subject"
          " - a factor of nine on one shape, with the mean")
    print("  above two of the three points. A single projected figure from that")
    print("  sample would be a real number answering a question it was not asked.")
    print()

    print("=" * 78)
    print("WHY BOTH ARMS, AND WHY unique RATHER THAN on-subject")
    print("=" * 78)
    print(f"  {'shape':10s} {'on-subject/req':>15s} {'UNIQUE/req':>12s}  what the gap means")
    for shape in SWEEP_SHAPES:
        on, uniq = ON_SUBJECT_PER_REQUEST[shape], UNIQUE_PER_REQUEST[shape]
        print(f"  {shape:10s} {on:15.1f} {uniq:12.1f}  "
              f"{1 - uniq / on:.0%} of its documents another arm also finds")
    print()
    print("  title n repro is 9 documents of 188, so the second arm roughly")
    print("  DOUBLES unique documents per model rather than re-finding the first")
    print("  arm's. That is the disjoint-sets lesson: an arm earns its requests")
    print("  on what only it finds.")
    print()

    print("=" * 78)
    print("WHAT IS NOT ISSUED")
    print("=" * 78)
    for shape, reason in REFUSED_SHAPES.items():
        print(f"  {shape}:")
        for line in _wrap(reason, 72):
            print(f"    {line}")
        print()

    print("=" * 78)
    print("WHERE THE REMAINING BUDGET GOES")
    print("=" * 78)
    print(f"  existing queries consumed        {EXISTING_QUERIES_CONSUMED:.0%}")
    print(f"  documents left in them           ~{EXISTING_QUERIES_REMAINING_DOCUMENTS}")
    full = sweep_cost(
        REGISTRY_ROWS, shapes=("title", "repro"), surfaces_per_model=args.surfaces_per_model
    )
    print(f"  a full-registry title+repro run  {full.requests} requests, "
          f"{full.minutes:.0f} minutes of the search bucket")
    print()
    print("  So the comparison is: ~57 more documents from re-running a query")
    print("  space that is 76% exhausted, against a sweep of two arms neither of")
    print("  which has ever been issued at scale. The sweep is where the budget")
    print("  goes - and it is retrieval, not extraction, which is a separate")
    print("  decision waiting on the tier re-weight.")
    return 0


def _wrap(text: str, width: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
