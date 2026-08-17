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
- Seeded and hand-curated rows carry `provenance`. `collect/registry/assertions.py`
  provides `assert_no_fixtures()` and `assert_contract_backed()` to refuse them.

  **Neither has a caller outside tests. Nothing currently stops a seeded row
  reaching a non-development environment.** Wiring is pending a startup path -
  issue #27. `judge/` opens no database connection at all, `collect/cli.py` runs
  per command rather than at startup, and the nightly chain that is the natural
  home does not exist yet.

  The third function in that module, `assert_terms_reviewed()`, **is** wired -
  `collect/adapters/blog/fetch.py` and `scripts/harvest_github.py` - so the
  module is not uniformly unwired and these two are not an oversight of style.

  This entry said "Production asserts on startup that none are present" for
  weeks. The first correction said the check was "called from the loaders and
  from tests", which was also wrong: the three apparent call sites in `collect/`
  are a docstring and two comments. Counted, the second time.
- Estimates are labelled as estimates. Triage survival (~10-15%), output
  verbosity and retry rate are figures to calibrate, not specifications.

## Build fixtures currently in place

Load-bearing during the build and poisonous afterwards.

| Fixture | Purpose | Removed |
|---|---|---|
| `contract/seed_models.yaml` | 10 hardcoded models so work starts without the registry poller | When OpenRouter polling lands |

`fixtures/hand_cells.yaml` was listed here until the Ask box was parked and the
file deleted. The section documenting our guard against stale fixtures had gone
stale itself, which is the joke writing itself and the reason this table lists
what exists rather than what was planned.
