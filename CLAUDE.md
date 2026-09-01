# Model Information Board

A board of what engineers publicly report about AI model capabilities, and an
advisor that uses it to recommend cheaper models for specific sub-agent tasks.

- **Requirements and the build plan:** `BUILD-PLAN.md`
- **How the machinery works:** `docs/logic-and-workflow.md`

## Working agreement (lanes dropped 2026-08-28)

We no longer divide the repo into owned lanes. The `collect/` → `judge/`
data-flow architecture stays; the *ownership* rule around it is gone, because it
cost more than it saved - a signal measurement sat in a PR for two days before
it reached the person building a gate on top of it. This supersedes the
per-lane ownership language still in `collect/CLAUDE.md` and `judge/CLAUDE.md`.

- **Touch anything. Tell each other after, not before.** No routing a change
  through a proposal that then sits.
- **The AST lane-boundary test stays - for testing, not ownership.** Two
  implementations of one storage contract can only be byte-compared while
  neither imports the other, which is what the flattener equivalence check
  relies on. Keep the reason visible so nobody removes the test as a leftover.
- **`contract/` still gets two eyes.** That file is the agreement, not just
  code - a contract change is proposed and reviewed, never taken solo.
- **Measurements travel the day they are taken**, not via a PR body.
- **Say what you broke, not what you built.**
- **Shared-DB / staging writes are coordinated** - see Conventions.

The data still crosses the boundary exactly once, in one direction:

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

   **Code-only extraction was proposed and refused, 2026-08-18.** Dropping the
   model at E5 and keeping it only in the Ask box would remove an injection
   surface, a dependency and a source of nondeterminism, and it is not a cost
   question - the whole corpus extracts for **$1.84**, which is 887 threads at
   the measured $0.00208 each. Was `$2.12`, quoted with no denominator and
   computed from a token estimate that no run had produced; the tokens were
   measured 2026-08-19 (n=3 calls, one thread) and the figure fell.
   `docs/measurements/extraction-token-counts.md`. The conclusion is unchanged
   and was never cost-dependent - that is why this sentence says "not a cost
   question" and then gives one number rather than an argument.

   It was refused for one structural reason. **Rule 1 works because the
   proposer and the checker are different things.** The model proposes a
   quote; code checks that quote exists byte for byte in the text the model
   was shown. If code extracts, code picks the quote and code verifies its own
   pick - the check passes by construction. We would still have three-step
   verification, a green suite, and a `quote_verified` column that means
   nothing: a guarantee that looks like one and is not.

   The supporting evidence is our own. A pure-code matcher hit `free` inside
   *"freeze"* and `fusion` inside *"confusion"* on the easiest subtask in the
   pipeline - exact matching against a known list - and was invisible on an AI
   corpus until it ran on movie posts (`docs/measurements/control-and-reshape.md`).
   If code needs a boundary map and a control experiment to decide whether a
   four-character string is a model name, *"is this person complaining or
   joking, about which capability, under what condition"* is not the smaller
   problem.

   **The alternative was weighed, not dismissed.** A code-only board is
   possible as *high precision, low recall*: publish only unambiguously-phrased
   claims, discard the rest unread, and **say so on every page**. That is a
   real product and a defensible one. What it costs is most of the evidence,
   and the saying-so is not optional - silence about ambiguously-phrased
   failures reads as absence of failures, which is rule 4 at the largest scale
   it covers. Recorded here rather than left in a message, because a reason
   that lives in a conversation gets re-litigated by whoever finds the model
   call expensive in month four.

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

   **It applies to claims about RISK, not only to figures**, and that form has
   no number in it at all - which is why the wording above misses it. *"Any
   branch older than the fix carries this defect"* is a true statement about
   what COULD be wrong, and with no population attached it reads as a statement
   about what IS. The population was 1 of 69 branches, and it was the one
   already being deleted. Same failure, same fix: name the denominator, and the
   worry changes even though the conclusion does not.

   Agreed by both engineers 2026-08-19, after E1 generalised from one instance
   without counting and E2 counted. Recorded because the risk form is the one
   that survives the rule as originally written - a reader checking "does this
   figure carry its denominator" finds no figure and moves on.

   Method and worked examples in `docs/measurements/README.md`.

8. **An unmeasured check ships as a weight, not a gate.** A check whose error
   rate has not been measured against a population it did not choose ships as a
   weight, a flag, or a recorded field - never a gate - and is promoted only
   once measured. A wrong gate's false positives are invisible: it drops the
   document, and an absence we *caused* reads as one we *found* - rule 4 one
   stage earlier, on what the pipeline discards rather than what the page
   renders. A wrong weight keeps the document and mis-ranks it visibly, which is
   the evidence that decides whether it should ever become a gate; so the
   direction is one-way, weight first and gate later on evidence, never the
   reverse.

   No test can tell a measured check from an unmeasured one - the measurement
   lives in a document - so this one is a **reviewer question** rather than a
   code constraint, the same shape as rule 7's: **what population was this
   filter's error rate measured on, and did the filter, or anything upstream of
   it, choose that population?** (The upstream clause catches the trap: "no, I
   used the whole corpus" is not an answer when the corpus is an earlier
   filter's output.) The PR template carries it. Settled twice - speaking on
   ModelRef, and the 8★ behaviour check - which is what makes it a rule rather
   than a precedent.
   Argument and both instances in `docs/weight-before-drop.md`.

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

  **Both are wired, since 2026-08-18.** `collect/ops/preflight.py` calls them
  and `collect/cli.py` runs `preflight()` before a command touches a database.
  Issue #27 is closed. A check whose input is absent is **skipped and named**
  rather than counted as a pass, so "no connection supplied" cannot read as
  "the fixture check passed".

  E1 found the real defect while wiring it, and it was not a broken check: two
  commands had never acquired one. `registry load-seed` - the command that
  *creates* the fixture - opened a transaction without gating, so
  `assert_no_fixtures` could only ever report seeded rows some other path had
  already written. `recompute-window`, the sole writer of `in_window`, was
  gated inside the nightly chain and unguarded when run by hand: guarded by the
  schedule rather than by the code. The guard is now an **AST test over
  `cli.py`** - any command opening a `transaction()` without `_gate` fails, and
  read-only commands must be listed explicitly so an unclassified one fails
  rather than running unguarded. A behavioural test over existing commands
  cannot see a path that never had a check.

  `assert_terms_reviewed()` was already wired -
  `collect/adapters/blog/fetch.py` and `scripts/harvest_github.py`.

  `assert_no_fixtures()` reads three tables: `model_version.provenance = 'seed'`,
  `cell.provenance = 'hand_curated'`, and
  `reported_context.provenance = 'hand_seeded'`. The third is FR-31's protection
  and the one worth naming, because `reported_low` is a hard filter: a wrong
  `cell` renders as a phrase somebody can argue with, a wrong `reported_low`
  renders as an absence, and nobody audits a model that was never in the list.
  Verified firing against a real database, not only present in the source.

  **This entry has now been wrong three times and each correction was smaller
  than the last.** It said "Production asserts on startup that none are
  present" for weeks; the first correction said the check was "called from the
  loaders and from tests", which was also wrong, because the three apparent
  call sites in `collect/` were a docstring and two comments; the second
  correction counted them and said neither had a caller, which was true when
  written and stopped being true the day #27 closed. The lesson is not to write
  more carefully - all three were written carefully - it is that a claim about
  wiring goes stale silently, so this entry is the one to re-check rather than
  re-read.
- Estimates are labelled as estimates, **and an estimate carries its
  population** (rule 7). Triage survival is ~10-15% *of documents retrieved
  from the sources we sweep* - never "of Reddit", which we do not sample.
  Output verbosity and retry rate are figures to calibrate, not
  specifications.
- **Writing to the shared staging DB is coordinated.** Evidence writes are
  append-only (`ON CONFLICT DO NOTHING`); never a global rebuild against
  staging. Migrations apply **once, in order, by whoever merges the migration
  PR, immediately after merge, and announced the same day** - check the ledger
  first, because it got out of step once. Before a staging write session, say
  so, so two of us are not writing the same afternoon.
- **A commit pushed to a branch whose PR has closed is invisible to everyone,
  including whoever pushed it.** Twice now, and the second was three minutes
  after the merge:

  ```
  f986e0e  feat/column-state-manifest    #166 merged 12:50, pushed 12:53
  0e026e8  fix/column-audit-web-scan…    #207 merged 08:39Z, pushed later
  ```

  **Nothing observes that push.** CI is `on: push: branches: [main]` plus
  `on: pull_request`, so a push to a feature branch with no open PR triggers
  **zero workflow runs** - no run, no notification, no review, no red build.
  Both of these surfaced in a branch audit weeks later, not from any signal.

  **Something CAN signal it, and only in one place.** A `pre-push` hook is the
  only moment anything knows both facts at once - that you are pushing, and that
  `gh pr list --head <branch> --state open` is empty while the branch is ahead of
  `main`. It must warn and never block: it needs `gh` auth and the network, and a
  hook that fails offline would be worse than the defect. No hooks are installed
  or shipped here today, so until one is, the rule is the rule:

  **Before pushing to a branch you did not just create, check whether its PR is
  still open.** `gh pr list --head "$(git branch --show-current)"` answers it.
  Writing this down rather than trusting the habit, because both instances were
  a follow-up commit written *because a review comment asked for it* - the moment
  you are most sure the PR is open is right after it closed.

## Build fixtures currently in place

Load-bearing during the build and poisonous afterwards.

| Fixture | Purpose | Removed |
|---|---|---|
| `contract/seed_models.yaml` | 10 hardcoded models so work starts without the registry poller | When OpenRouter polling lands |

**The shared database is already fully polled: 342 `model_version` rows,
`provenance='polled'`, ZERO `seed` (verified 2026-08-28).** So on the one
database the poisoning risk matters for, it is absent - polling has landed
there. The file has NOT been removed, because code still references it (the
seed loader, and `scripts/fetch_model.py`'s alias fallback), so a fresh or
local DB can still be seeded. A fixture nobody loaded looks identical from the
file to a fixture nobody removed, which is why this row now carries the count
rather than only the trigger.

`fixtures/hand_cells.yaml` was listed here until the Ask box was parked and the
file deleted. The section documenting our guard against stale fixtures had gone
stale itself, which is the joke writing itself and the reason this table lists
what exists rather than what was planned.
