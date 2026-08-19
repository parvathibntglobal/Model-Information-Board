# Model Information Board

A board of what engineers publicly report about AI model capabilities, and an
advisor that uses it to recommend cheaper models for specific sub-agent tasks.

- **Requirements and the build plan:** `BUILD-PLAN.md`
- **How the machinery works:** `docs/logic-and-workflow.md`

## Lane ownership

Two engineers work this repo in parallel.

- `collect/` is owned by **Engineer 1**. `judge/` is owned by **Engineer 2**.
- **Do not edit outside your lane.** Propose the change to the other person instead.
- `contract/` is **shared**. Never modify it without flagging it - it is the
  interface between two people working in parallel, and it should change
  perhaps five times in eight weeks, each time on purpose.

The data crosses the lane boundary exactly once, in one direction:

```
collect/  ---->  document + thread_context (carrying offset_map)  ---->  judge/
```

`collect/` fills those tables. `judge/` reads them. Nothing flows back.

## Non-negotiable rules

These are the rules a helpful refactor will otherwise quietly violate.

1. **No claim without a verbatim quote**, verified in code by exact substring
   match against the text the extractor was given. No quote, no claim. The
   verification is plain Python - never a model checking a model.

2. **Exactly two stages may call a language model**: `judge/extract/` and
   `judge/ask/` (task understanding only). No model participates in counting,
   weighting, gating, ranking, filtering or phrase assembly.
   The governing rule for anything added later:
   **an LLM may propose, it may never decide.**

3. **No synthesised number reaches a page.** Every figure displayed is either
   *counted* (people, quotes, days) or *measured* (price, tokens). Consensus is
   a phrase assembled from counts, never a score. There is no 0-100 capability
   figure anywhere in the schema or the UI.

4. **Silence is not criticism.** "Nobody has discussed this" must render
   distinctly from "engineers report problems". Absence of evidence must never
   read as evidence of capability.

5. **Config in versioned YAML, not code.** Thresholds, weights, half-lives, the
   capability list, alias variants and filter rules all live in `contract/`.

6. **A missing value is never silently converted into a definite one.** Absent
   data stays absent through every layer that reads it. An unpublished
   capability flag is not `false`. A NULL price is not free, and not the
   cheapest tier. An unseeded `reported_low` is not a threshold. Where a value
   is missing at the point it would have been used, **say so** - a caveat the
   reader can act on, never a silent exclusion.

   Rule 4 is this rule's display side. This is the data side, and **both lanes
   have broken it once**: `judge/`'s hard filter read an absent
   `supports_tools` as "cannot", taking a candidate list from 11 models to 1;
   GitHub Search silently discards the qualifiers in a query, turning a
   capability-scoped search into a bare alias match. Both surfaced as an
   absence with nothing on the page to disagree with, which is what makes this
   class of defect expensive - it looks like a considered answer.
   Both incidents are written up in `docs/contract-signoff-phase1-response.md`,
   which is where the rule was first stated.

7. **A figure travels with its denominator and where that came from.** Any
   number that reaches an argument, a page or a document states what population
   it was drawn from and how that population was gathered. `52.7%` is not a
   claim. `52.7% of 636 candidates retrieved for one model using that model's
   own variants` is a claim, and it is visibly not a naming rate.

   Rule 6's sibling. Rule 6 is a missing value silently becoming a definite
   one; this is a **real value silently answering a question it was not asked**.
   Three figures did that in one fortnight - `"context window"` present in 96%
   of returns and `"went back to"` in 100%, both measuring collocation
   frequency rather than a phrase operator, and 52.7% subject match, measuring
   the retrieval that produced the corpus. Each was load-bearing in an argument
   before anyone checked what it counted.

   This class survives inspection, which is what makes it expensive: a number
   looks like evidence, and a spot-check confirms it. **The check that catches
   it needs no suspicion** - ask what the denominator is and where it came
   from. If the answer is not beside the figure, the figure is not yet
   evidence. Applies to counts as much as to percentages: what the three shared
   was an unstated population, not a form.

   Method and worked examples in `docs/measurements/README.md`.

## Stack decisions already made - do not relitigate

- Python 3.11+. Postgres plus an object store. `httpx` for fetching.
- Cron plus a jobs table. **No workflow engine, no Kafka, no time-series DB.**
- One adapter class per platform. **Official APIs and public feeds only** -
  no scraping, no paywall circumvention, `robots.txt` respected, identifying
  User-Agent with a contact URL.
- The evidence pipeline is a **nightly batch**. The answer path reads a
  materialised view and never touches the pipeline.
- Published content is *quote + attribution + link*, never full text.

## Conventions

- Every derived row carries `pipeline_version`, so any scoring change is
  fully re-runnable and diffable.
- Raw payloads are immutable and content-hash addressed. Reprocess from there
  rather than re-fetching.
- Seeded and hand-curated rows carry `provenance`, and **every write path
  refuses them outside `development`**. `collect/registry/assertions.py` holds
  the four checks; `collect/ops/preflight.py` runs them; two callers invoke it.

  ```
  collect/ops/chain.py    stage 1 of the nightly chain, before anything writes
  collect/cli.py:_gate    on WRITE commands only - db init, db migrate,
                          registry load-seed, registry recompute-window
  ```

  Read-only commands are deliberately ungated: the state these checks refuse is
  exactly the state somebody needs `registry check-sources` to diagnose.
  `tests/test_cli_write_gate.py` reads `cli.py`'s AST and fails if a command
  opens a `transaction()` without calling `_gate`, so a NEW write path cannot
  arrive unguarded - which is the failure mode, rather than a broken check.

  `assert_no_fixtures()` reads three tables: `model_version.provenance = 'seed'`,
  `cell.provenance = 'hand_curated'`, and
  `reported_context.provenance = 'hand_seeded'`. The third is FR-31's protection
  and the one worth naming, because `reported_low` is a hard filter: a wrong
  `cell` renders as a phrase somebody can argue with, a wrong `reported_low`
  renders as an absence, and nobody audits a model that was never in the list.
  Verified firing against a real database, not only present in the source.

  **Do not weaken this entry into a negative again without counting.** It said
  "Production asserts on startup that none are present" for weeks while nothing
  called anything. The first correction said "called from the loaders and from
  tests", also wrong - the three apparent call sites were a docstring and two
  comments. The second correction said wiring was blocked because `collect/ops/`
  did not exist and the CLI runs per command; the first half stopped being true
  when `collect/ops/` landed, and the second was never a blocker, since a
  per-command CLI can gate per command. Three wrong statements, in both
  directions, on one four-line entry. Issue #27 closed 2026-08-18.
- Estimates are labelled as estimates, **and an estimate carries its
  population** (rule 7). Triage survival is ~10-15% *of documents retrieved
  from the sources we sweep* - never "of Reddit", which we do not sample.
  Output verbosity and retry rate are figures to calibrate, not
  specifications.

## Build fixtures currently in place

Load-bearing during the build and poisonous afterwards.

| Fixture | Purpose | Removed |
|---|---|---|
| `contract/seed_models.yaml` | 10 hardcoded models so work starts without the registry poller | When OpenRouter polling lands |

`fixtures/hand_cells.yaml` was listed here until the Ask box was parked and the
file deleted. The section documenting our guard against stale fixtures had gone
stale itself, which is the joke writing itself and the reason this table lists
what exists rather than what was planned.
