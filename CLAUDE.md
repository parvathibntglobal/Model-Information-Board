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

9. **A produced value has a named consumer, or a declared reason it has
   none.** Any value this pipeline computes, extracts, pays a model for, or
   persists must either have a reader named at a file and line, or be
   **declared unconsumed** - with its intended reader and why that reader
   cannot read it yet. Never neither. A value with no reader is not
   necessarily waste; a value with no reader *and no statement about it* is
   always a defect, because the next person cannot tell those two apart.

   **Declaration, not deletion.** Three of the four instances below should
   stay: two have real intended readers and one is a field we want and already
   pay for. `contract/column_states.yaml` is the worked example - it declares a
   state for all 340 columns and **150 of them are not currently read**, which
   is a strength rather than a backlog.

   **And it stops at the schema boundary, which is where this rule earns its
   place.** All seven of that file's states describe *columns*. Three of the
   four instances are not columns - a field in an LLM tool schema, a field in
   an API payload, an adapter field dropped before the database - so the audit
   cannot see them, and the most expensive one is the furthest outside it.

   No test can catch this, for the same reason as rules 7 and 8: the absence of
   a reader is not a behaviour, it is a silence, and a suite passing over a
   silence looks exactly like one passing over a correct answer. So it is a
   **reviewer question**: **what reads this, and where - file and line?** If
   the answer is "nothing yet", the follow-up is not "delete it", it is "then
   declare that".

   Four instances, one week, and the shape is what makes it a rule:
   `comparison_target` extracted from a paid model call and dropped before any
   column; `unattributed_reading` published by the API and never rendered -
   **added by the fix for the first shape and creating the second**;
   `specificity_score` written and declared `write_only` with its blocked
   reader named; `quota_exhausted` computed and dropped by name with its fix in
   a numbered PR. The last two are what compliance looks like.

   The cost is of two kinds and they argue differently: unread *information* is
   recoverable whenever a reader is written, unread *spend* is not.
   `comparison_target` is tokens paid on input and output, per thread, on every
   re-run, invisible on any invoice because it is a fraction of a call nobody
   itemises.
   Argument and all four instances in `docs/produced-and-never-consumed.md`.

10. **An identifier is the whole identifier, and a separator is not part of
    it.** Anything used as a grouping key — a slug, an axis name, a benchmark
    — must be copied complete, and must be compared on its characters rather
    than on its punctuation. A prefix is a **different** identifier, and two
    spellings of one name are the **same** one.

    Three failures, one week, all on the metrics pages, and they need
    different fixes — which is why they are one rule rather than three
    patches:

    | | example | where the fix belongs |
    | --- | --- | --- |
    | truncation | `aime` vs `aime-2026` | the extractor, asked |
    | spelling | `exploitbench` vs `exploit-bench` | code, mechanically |
    | real versions | `osworld` vs `osworld-2` | **must never merge** |

    **The truncation case is not two writers disagreeing.** One model's 97.1%
    was filed under `aime` from the quote *"97.1% on AIME 2026 math"* and
    under `aime-2026` from *"97.1% on AIME 2026"*. The full name is in both
    quotes; the copy stopped at different depths. Both copies pass
    `metric_refusal`'s substring check, because a substring test cannot tell a
    complete name from a prefix.

    **⚠ AND THE MECHANICAL REPAIR IS A TRAP, WHICH IS THE PART WORTH
    REMEMBERING.** `axis_specificity` already detects a name that continues.
    Over the 314 published figures on 2026-09-21 it fired five times and
    **three of the five continuations were the score, not the name**:

        'CyberGym'      ->  'CyberGym 84.5'       84.5% is the result
        'ExploitBench'  ->  'ExploitBench 54.4'   54.4% is the result
        'AIME'          ->  'AIME 2026'           a year, genuinely the name

    Extending the copy automatically would invent three axes named after
    measurements in order to repair two. Telling a year from a score is a
    reading task, so it is **asked of the extractor** (`axis_verbatim`'s
    description, which now says where the name stops) and **reported as a
    weight** here, per rule 8.

    **The spelling case is the opposite: code must do it, because the prompt
    cannot.** The extractor is required to copy the axis character for
    character — that rule is what stops a Terminal-bench figure being filed as
    SWE-bench (#368). Two documents spelling one benchmark two ways therefore
    *must* produce two spellings, and asking the model to normalise would be
    asking it to write something the text does not say. `spelling_key` folds
    separators and nothing else; it left `osworld`/`osworld-2` alone and
    caught `over-thinking`/`overthinking` in a section nobody had looked at.

    **The boundary that keeps this from becoming rule 2's problem**:
    `normalise_slug` refuses to fold `tool-calling` into `function-calling`,
    because that is a judgement about **meaning** and belongs to a person
    through `ruling`. Folding a hyphen is a judgement about **nothing**. The
    day this rule is read as licence for a synonym table it has been
    misunderstood.

11. **A count in prose is a measurement with a date, or it is a defect.** Any
    number written into a comment, a docstring, a refusal message or a README
    must either be **computed where it is shown**, or **stated as a record**:
    what was counted, over what population, on what date. Never a bare present
    tense about state the file does not own.

    **Six instances, and "be more careful" has demonstrably been tried.**
    `CLAUDE.md`'s preflight entry was wrong three times in a row, each
    correction smaller than the last. The fixtures table above said *"ZERO
    seed (verified 2026-08-28)"* while four seeded rows carried 65 claims
    (#382). `weight.py`'s refusal told a reader that carrying `has_conditions`
    *"changes nothing"* when it had come to change 1,005 documents (#384).

    **The fastest instance took thirty-five minutes and was written by someone
    who had spent that morning measuring this exact class.**
    `board_entries.py` shipped `447 stored / 269 shown` at 10:15 on
    2026-09-21; by 10:50 it was `471 / 290`, because a run wrote in between.
    That comment was not decoration — it was the justification for withholding
    at all, so a reader checking whether the trade was still fair got a number
    two runs out of date with nothing to tell them.

    The two honest forms, and they are different:

    - a count the code **can** recompute — compute it, or state none. The
      module holding an open connection can count its own rows.
    - a count from **elsewhere** — date it and name the population, and phrase
      it as a record: *"was 269 of 447 on 2026-09-21"*, not *"269 shown"*.

    No test catches this, for rule 7's reason: a stale number is not a
    behaviour. It is a **reviewer question** — *does this number describe now,
    and what recounts it?* The mechanism for enforcing it in refusal messages
    is being decided on #384.

12. **A fallback that can succeed on a wrong input is not a fallback.** A
    default, a permissive pattern or a silent coercion must fail loudly when
    the thing it is standing in for is wrong. If it can quietly produce a
    plausible result, it is not protecting the code — it is hiding the branch
    where the code is broken.

    **Two instances on one page, both of which passed the suite, passed the
    linter and built clean.**

    `What was measured` shipped **unreadable**. It was styled
    `color: var(--fg, #1f2328)`, and there is no `--fg` in `tokens.css`, so
    every cell fell through to a light-theme fallback on a board whose
    background is `#0C0C0E`. The markup was right, the class was right, the
    text was in the DOM. A `var()` fallback is exactly the branch that runs
    when the name is wrong. `test_a_figure_is_one_measurement.py` now fails on
    any rule naming an undefined custom property, and found five more.

    `_HAS_QUANTITY` was `re.compile(r"\d")` — *is there a digit anywhere?* On
    2026-09-21 it published `'matches or trails Claude Fable 5 and GPT 5.6
    Sol'` as a measurement, because **Fable 5** and **GPT 5.6** contain
    digits. Every modern model name does. The check had been wrong since it
    was written and only became visible when a value arrived whose sole digits
    were a version number (#386).

    The question to ask of any default: **what does this do when I am wrong?**
    If the answer is "produces something that looks fine", it needs to fail
    instead.

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

- **A RED CHECK IS `UNSTABLE`, NOT `DIRTY`, UNTIL `gh` SAYS OTHERWISE.** Read
  the state before reading the X. Three times in a row a red PR was described as
  having conflicts and had none — #300, #301's sibling, #310 and #300 again:

  ```
  gh pr view <n> --json mergeable,mergeStateStatus --jq '.mergeable+" / "+.mergeStateStatus'

    MERGEABLE / UNSTABLE   a CHECK is failing. Nothing to resolve.
    CONFLICTING / DIRTY    a real conflict. Rebase.
  ```

  Only ONE of those four was a genuine conflict (#301, against #299's rewrite of
  the same file). **The cost each time is a rebase nobody needed** — and on a
  shared file like `contract/sources.yaml` an unnecessary rebase is not free,
  because it invites resolving a conflict that was never there.

  The tell is cheap and it is one command. `UNSTABLE` means go read the failing
  job; `DIRTY` means go rebase. And when it IS `DIRTY`, check whether the branch
  even touches the contested file before assuming the worst: #300 was assumed to
  clash with `contract/sources.yaml` and does not touch it at all.

- **A CHECK IS SCOPED TO WHAT CI RUNS, NEVER TO WHAT LOOKS RELATED.** This has
  now produced a wrong "it passes" claim twice in one day, on two different
  checks, and the second happened after the first was understood.

  ```
  ruff    #294 and #295 both failed Lint while reporting green locally, because
          `ruff check .` over the whole tree is noisy with untracked probe
          scripts and the real answer was
              ruff check $(git diff --name-only origin/main HEAD | grep '\.py$')

  pytest  #310 reported "737 tests pass" from a HAND-PICKED list of files.
          CI ran 3,473 and found 8 failures. Six were in `test_blog_fetch.py`,
          which needs no database and was simply never run - it did not look
          related to a change in `collect/adapters/basis.py`, and it exercises
          that path through two indirections.
  ```

  **The two share a cause and it is not haste.** A scope chosen by judgement
  answers "did the thing I was thinking about break", and CI answers "did
  anything break". Those differ exactly where the change had a consequence
  nobody predicted - which is the only case worth running a suite for.

  So: **scope ruff to the diff, and scope pytest to everything.** The local
  obstacle is that ~23 test files need Postgres and HANG rather than skip when
  it is absent, so an unscoped run looks like a hang rather than a result.
  Excluding them by name is the workaround and it is the thing that goes stale
  - the list is discoverable with
  `grep -rln "def conn\|TEST_DATABASE_URL\|psycopg.connect" tests/`, and a
  file added to it after that grep is the next wrong claim.
  **A local Postgres on :5433 removes the problem rather than working around
  it**, and is the durable fix.

  Say which scope a claim came from. "737 tests pass" and "CI is green" are
  different statements and only one of them is about the branch.

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
  first, because it got out of step TWICE. Before a staging write session, say
  so, so two of us are not writing the same afternoon.

  **A MIGRATION PR'S BODY MUST SAY WHO RUNS IT, AND WHEN.** Merging ships the
  FILE; a person runs the runner. The writer that needs the new column ships as
  CODE and takes effect the moment anyone pulls - so between the merge and the
  migrate, every other machine holds a writer for a schema it does not have.

  That gap is not theoretical. #260 merged at 11:16Z on 2026-09-11 with the
  `board_entry.model_scope` column, its migration and its writer. The writer
  reached the other machine on a pull; the migration reached it as a file
  nobody had run; E5 died on *"column model_scope of relation board_entry does
  not exist"* and spent three extract calls doing it. Applied 13:13Z.

  **The sentence that caused it was in the PR body**: *"the migration is the
  only pending one and the ledger is clean, so it applies on merge."* It does
  not apply on merge. Nor does *"lands with this"*, nor *"will apply"* - all
  three read as **no action required**, which is why the PR template now names
  them and refuses them by name rather than asking for care.

  **WHEN THE RUNNER IS BLOCKED AND A MIGRATION HAS TO GO IN NOW.** This has
  happened twice and both times the runner was routed around:
  `20260910T1300_claim_capability_key_nullable.sql` applied by hand to unblock
  an E5 foreign-key violation, and `20260911T1000_shared_telemetry.sql` the
  next day. Neither reached `schema_migration`, because nothing asked it to.

  The runner refusing everything on one mismatch is the guard working. But a
  guard that blocks all traffic until somebody investigates is a guard people
  step around under pressure, and then the ledger is wronger than before - so
  **hand-application is ALLOWED and recording it is NOT OPTIONAL**:

    1. Apply the SQL and INSERT the ledger row **in one transaction**. If the
       DDL commits and the row does not, you have created exactly the state
       this rule exists to prevent.
    2. The hash comes from `collect.migrate.content_hash` on the file, never
       typed by hand and never copied from another row.
    3. `applied_at` is when it was APPLIED. `schema_migration` has no
       `recorded_at`, so a backfilled row cannot carry both facts - say in the
       commit message that the timestamp was reconstructed and from what. That
       is weaker than an observed one and the weakness should be visible.
    4. Announce it the same day, like any other migration.

  **RESOLVING A MISMATCH IS AN INVESTIGATION, NOT A RE-HASH.** A stored hash
  that matches no encoding of the file on disk usually means the file was
  applied from a draft and revised before commit - `git log --follow` showing a
  single commit does not rule that out, it is the signature of it. Before
  re-hashing:

    - Search the whole object database, not the file's history:
      `git cat-file --batch-all-objects` and hash every plausible blob. A
      recovered draft turns a judgement call into a diff.
    - If it is unrecoverable, verify the migration's STATEMENTS against the
      live schema instead of its text - each `WHERE` clause as a `SELECT
      count(*)`, and any post-condition the file asserts. A migration whose
      statements would change zero rows and raise nothing is safe to re-hash
      whatever its prose used to say.
    - Say which of the two you did. **Never re-hash on the grounds that it is
      probably fine** - the hash is the only thing standing between a revised
      migration and a database nobody can reason about.

  Worked example, 2026-09-11: 132 of 160 lines were comment, the two `UPDATE`s
  were idempotent by their own `NOT LIKE` guards, all four predicates counted
  zero, and 99 candidate blobs in the object database hashed to none of it.
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

  **⚠ THIRD INSTANCE, 2026-09-21, AND THE CHECK WAS RUN. That is the part worth
  adding.** `7ea2798` pushed to `feat/fixture-exposure-gate` after #383 merged
  at 08:40; two measurement scripts, invisible on `main`, found only by a sweep
  hours later. The command above WAS run first, and it printed nothing, and the
  nothing was read as clearance.

  ```
  gh pr list --head "$(git branch --show-current)" --state open ...
      prints a number   the PR is open, push
      PRINTS NOTHING    there is no open PR. STOP. This is the warning.
  ```

  An empty result is the failure signal and it looks exactly like a clean
  check - same silence, opposite meaning, and the two-command form makes it
  worse by putting the push on the same line with `&&`. So the rule is no
  longer "run the check"; it is **read the empty result as a refusal**, and
  prefer a form that cannot be misread:

  ```
  gh pr list --head "$(git branch --show-current)" --state open --json number \
    --jq 'if length == 0 then error("no open PR for this branch") else .[0].number end'
  ```

  Same family as the `UNSTABLE`/`DIRTY` entry above and as rule 4: an absence
  that reads as a pass. The two earlier instances were a habit not followed;
  this one was the habit followed and the output misread, which no amount of
  remembering to run it would have caught.

## Build fixtures currently in place

Load-bearing during the build and poisonous afterwards.

| Fixture | Purpose | Removed |
|---|---|---|
| `contract/seed_models.yaml` | 10 hardcoded models so work starts without the registry poller | When OpenRouter polling lands |

**The shared database is 344 `model_version` rows at `provenance='polled'`
and FOUR at `provenance='seed'`, with 65 claims and 11 cells pointing at those
four (measured 2026-09-21, #382).** The file has NOT been removed, because code
still references it (the seed loader, and `scripts/fetch_model.py`'s alias
fallback), so a fresh or local DB can still be seeded. A fixture nobody loaded
looks identical from the file to a fixture nobody removed, which is why this
row carries the count rather than only the trigger.

⚠ **THE FOUR ARE NOT FIXTURES, AND THAT IS THE DEFECT.** This line read "ZERO
`seed` (verified 2026-08-28)" until 2026-09-21, and went stale on 09-15 and
again on 09-17 when Recraft V4.1 Pro, ElevenLabs v3, Qwen3.5 Omni Flash and
Gemini 3.8 Flash were seated by `3e1c343` and `dc45b47`. They are real models
OpenRouter does not list and never will, hand-entered so the board can link
them; every one of the 65 claims traces to a harvested document with a real
quote. Nothing about them is a build fixture.

`provenance` allowed only `seed|polled`, so there was no value for
"hand-entered and never going to be polled" - the third state got labelled with
the word that means fixture, and `assert_no_fixtures` then refused it correctly
by its own definition and wrongly by intent. Three contract files fed that one
value (`seed_models.yaml`, `unpolled_models.yaml`, `awaiting_poll_models.yaml`),
each added to dodge a load refusal rather than to mean something different.

**`unpolled` is the third value, and it lands in two steps.** The CHECK, the
loader and the guard ship as code; the four rows convert when somebody runs the
migration.

```
20260923T0500_model_version_unpolled_provenance.sql
```

⚠ **UNTIL THAT MIGRATION IS APPLIED TO A GIVEN DATABASE, THE WRITER IS AHEAD OF
THE SCHEMA THERE.** `scripts/load_unpolled_models.py` now writes
`provenance='unpolled'`, and against an un-migrated database that is a
`CHECK` violation rather than a mislabelled row - the #260 shape, where the
writer reached another machine on a pull and the migration reached it as a file
nobody had run. Pull, then migrate, then load.

**Do not read `provenance='seed'` as "this row is a fixture" on a database that
has not been migrated.** After it has, `seed` means fixture again and
`assert_no_fixtures` is unchanged in code and stricter in intent - it always
queried `seed` exactly, which is why it needed no edit.

`fixtures/hand_cells.yaml` was listed here until the Ask box was parked and the
file deleted. The section documenting our guard against stale fixtures had gone
stale itself, which is the joke writing itself and the reason this table lists
what exists rather than what was planned.
