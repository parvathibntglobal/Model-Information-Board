# The comments are stored, the sweep is corpus, and the 19 rows were a weight change

**Four pieces of work in the order they were asked for, and one outstanding
question closed.** Written the day it was done.

*Engineer 1 · 2026-08-31.*

---

## 1 · The comment write path, on the 148 already fetched

`scripts/write_github_comments.py --apply`. No network: the payloads were in the
local raw store and carry `user.id`, `user.type`, `created_at` and `body`, so
`StoredComment` was rebuilt from the store and
`GitHubHarvester.write_comments` did the writing unchanged.

```
  seen                       148        human                      125
  linked                     148        bot_filtered                23
  skipped_no_issue             0        bot_accounts                 2
  inserted                   148        bot_suffix_disagreements     0
  authors_inserted            45        unattributable               0
```

### 1.1 · Bots are stored, named, and are not voices

`is_bot` keys on `user.type`, not on the `[bot]` suffix, and the run reports both
so the day they disagree is a finding rather than a silent reclassification.

```
  user.type over 148 comments   User=125   Bot=23
  is_bot true                   23, from TWO accounts
                                github-actions[bot] (22), linear[bot] (1)
  suffix/type disagreements     0
```

**The agreement's denominator is 2, not 148.** Two GitHub Apps follow GitHub's
own naming convention because the platform renders it. That is why the suffix is
a corroboration and not the test.

Each bot comment is stored with `status='filtered'`, `filter_reasons=['bot_author']`
and `author_id` NULL, payload kept. And `assemble_issue_thread` refuses them as
members — which is the guard that matters, because `judge/store/cells.py` maps a
NULL author to `ANONYMOUS_VOICE:platform`, so a bot left in a flattened thread
could be quoted and still contribute that shared voice.

### 1.2 · Voices before and after: **+0, and zero is the correct answer**

```
                                          before   after
  cells                                       96      96
  independent_voices summed                  155     155
  max voices on any cell                       7       7
  distinct voices across all claims            87      87
  github documents carrying an author_id       45      90
```

A voice is `claim.author_id`; a claim comes from an extraction; **nothing in this
step extracts.** What moved is the *pool* — github author identities doubled,
45 → 90, which is the 65-distinct-human-authors figure landing net of overlap
with the 45 issue-body authors. The cell number moves when the re-assembled
contexts are read, not before. Reporting it as before/after with an identical
column is the honest form; anything else presents a no-op as a result.

### 1.3 · Re-assembly forks rather than deletes, and that was forced

`assemble_issue_thread` derives its id from
`stable_id("thread_context", root_document_id, version)` — the same formula
`assemble_issue` uses — so at the same `pipeline_version` the new context
collides with the body-only one and `ON CONFLICT DO NOTHING` silently keeps the
old row.

`scripts/rebuild_github_contexts.py` solved that by deleting, and said in its own
docstring that the manoeuvre *"stops being free the moment a github claim
exists"*. **It now exists**: 4 of these 30 issues have been extracted and one
carries 5 stored claims. Deleting would have destroyed verified offsets. So the
30 comment-bearing issues were assembled at
`pipeline_version = 'collect-0.2.0-issue-comments'`, passed per call rather than
by bumping `collect.config.PIPELINE_VERSION`, which would have forked every
reddit and blog context for a change that touched neither.

### 1.4 · coverage_ratio on the 30 issues that gained comments

```
  before   0.000 on all 30          root read, no thread
  after    mean 0.786, median 1.000
           at 1.000: 16   at 0.000: 3
           observed 125 human comments, 26 still unread
```

**The forked rows alone, and that is the comparison to quote.** The pooled github
mean is 0.393 over 60, because it also contains the 30 body-only rows this did
not delete and excludes 41 empty threads where the ratio is NULL — it would
average a fork against its own original and report an improvement half its size.

**The 3 still at 0.000 are bot-only threads** (3, 2 and 3 comments, all
`user.type == "Bot"`). Bots are excluded from `observed` deliberately, so the
ratio describes *human* coverage: an issue whose only replies are CI runs has no
thread we want, and 0.000 is true rather than a fetch that failed.

`retrieval_provenance` on the comment rows is `not_recorded`. **Not
`no_run_for_source`** — that would assert github issues no runs, which is false,
the issue bodies above them carry one. A comment fetch renders no search query
and opened no `harvest_run`, so there is no id to point at, and the column's
under-claiming state is the accurate one.

## 2 · The multi-shape sweep

`scripts/multi_shape_sweep.py`. `title` then `repro`, shape-major, `label`
refused — `sweep_requests` raises rather than filtering, so asking for it is
visible.

### 2.1 · What it does not buy, first

**Four shapes across the 18-request experiment returned zero signal hits and zero
kept documents** — `title` 0/300, `repro` 0/600, `signal` 0/251, `label` 0/300.
Signal is what the full sieve needs to KEEP a document, so a sweep with no signal
hits **enlarges the pool and produces no claim by itself.** No claim, no voice,
no cell. It is corpus. The comment path in §1 is the part that touches voices.

### 2.2 · Subject is the gate, and the full sieve cannot be

`sieve()` treats an empty `topic` or `signal` group as a **failed** group — an
empty group would be vacuously true and collapse the query to its subject alone.
A shape query has no capability entry and therefore neither group, so running the
full sieve as the store gate keeps exactly zero documents. This gates on subject
and *records* topic and signal as counts: rule 8's shape, a field rather than a
gate.

### 2.3 · Two subject figures, because the obvious one is near-tautological

The first slice measured **96.2% on-subject** and that number must not be quoted.
A `title` query asks GitHub for documents whose title contains
`claude-sonnet-4.5`, and `sieve.normalize` casefolds and collapses whitespace
**without stripping hyphens** — so the retrieval form is in the text by
construction and an any-form subject check passes on nearly everything. It is
GitHub confirming it honoured the query. Rule 7 exactly.

```
  any%     ANY spelling appears. The STORE GATE. Near-tautological on `title`.
  prose%   a SPACED spelling appears - somebody wrote the name out.
           Comparable to the experiment's title 31.0% / repro 17.0%.
```

Both are reported. **And the slice's `prose%` is not comparable to the
experiment's 31.0% either**, for a second reason worth naming: the slice covered
one model, and it was `claude-sonnet-4.5`, the model with the experiment's best
title yield (76/100 against 8 and 9 for the other two). A per-model figure
against a three-model mean is not a comparison.

### 2.4 · The cost model in the earlier write-up counted the wrong bucket

`docs/measurements/the-github-sweep-and-the-comment-write-path.md` §5 costs a
full-registry `title+repro` run at **684 requests and 22.8 minutes**. That is the
**search** bucket at 30/minute, and it is not what the run spends.

```
  measured, 4 title requests on one model
    search requests            4
    candidates               209
    on-subject (any form)    201
    REST issue fetches       141        <- one per on-subject candidate
    wall clock              ~4 min      <- ~1 min per SEARCH request
```

**The binding cost is the REST fetch, not the search.** Roughly 35 documents are
fetched per search request, so the 268-request plan over 40 seated models implies
on the order of **9,000 REST calls** against a 5,000/hour core bucket — hours,
not minutes. Shape-major is what makes a truncated run useful rather than
useless, and it is doing real work here rather than being a nicety.

The plan itself, for the record:

```
  seated models        40
  distinct surfaces   177
  requests planned    268     title=134, repro=134
```

### 2.5 · The run: 34 of 134, stopped on the ceiling

`--shapes title --max-minutes 30`. The `title` arm alone, because the cost model
above says `title+repro` is 3½ hours.

```
  requests issued        34 of 134       STOPPED ON TIME, at 30.0 min exactly
  observed rate          51 s/request    plan assumed 2.2s, the search interval
  http_errors             0              no throttle, no truncated_by='rate-limit'

  candidates          2,368 slots
  any-form subject    2,089   88.2%      THE STORE GATE. Near-tautological.
  prose subject       1,143   48.3%      the comparable figure
  topic                   0
  signal                  0
  distinct candidates 1,410
  documents stored    1,145              github 369 -> 1,514
```

**`prose%` is 48.3% against the experiment's 31.0%**, and the two are not the
same population: 34 requests over ~9 models here, 3 requests over 3 models
there, and the shape ranking's 31.0% is a three-model mean whose per-model spread
was 76 / 8 / 9. Higher, on a bigger sample, in the same direction — not a
contradiction and not a confirmation.

**Signal hits: 0 over 2,368 candidates.** The experiment saw 0 over 230; this is
roughly ten times the sample of the same question with the same answer. The sweep
is corpus.

**The REST bucket never came close, by design.** `REST_INTERVAL` is 0.8s, which
is `CORE_LIMIT_PER_HOUR × SEARCH_HEADROOM / 60` — our own limiter capped the run
at 4,500 fetches/hour against GitHub's 5,000, and the observed rate was ~4,150.
53 REST fetches × 0.8s is 43s of the 51s per request, so **the limiter is the
pace and the bucket cannot bind while it holds.** Search ran at 1.3 requests per
minute against 27 available.

An earlier draft of this section said the run was slow "against a 5,000/hour core
bucket", which implied GitHub was the constraint. It is not; our own politeness
interval is, precisely so GitHub never becomes one.

### 2.6 · A counter of mine was wrong, and two numbers in one row caught it

The first full run printed `new 1,881` beside `unique 1,410` and `stored 1,145`.
**A count of documents cannot exceed the distinct documents it counts.**
`new_to_corpus` was `+= 1` per FETCH, so a document retrieved by both
`claude-sonnet-4.5` and `sonnet-4.5` counted twice. It is a set now, and the
JSON says to cross-check it against the `document` delta.

The real figure is **1,145**, which is what the table moved by. Same family as
everything else this sweep measures: a per-request tally read as a per-document
one.

### 2.7 · And none of the 1,145 is extractable yet

The sharpest form of "what it does not buy", found after the run:

```
  github documents                1,514
    with a thread_context            71
    WITHOUT one                   1,443     148 comments + 1,295 issue bodies
```

**Extraction reads `thread_context`, not `document`.** The sweep wrote 1,145
documents and zero contexts, so the extractable population did not move at all —
which is why the projection in §4 is unchanged at $4.70 even though the corpus
grew by a quarter.

`assemble_github_documents` selects on `NOT EXISTS (thread_context)`, so it would
pick every one of them up and is a no-op on a re-run. Nothing invokes it: the
`assemble-flatten` chain stage is `run=None`, and there is no `ops` subcommand
for it. Same shape as §6 below and as `score-documents` — code that works,
reachable by nothing.

So the honest ledger for 30 minutes of sweeping is: **+1,145 documents, +0
extractable threads, +0 claims, +0 voices, +0 cells.**

## 3 · `has_repro_steps` — the cost question, answered

Full argument in
`docs/proposals/for-engineer-2-has-repro-steps-is-a-question-nobody-asked.md`.
The addition this round is the number Engineer 2 asked for before ruling.

**New claims need no backfill. The existing 199 need a re-extraction, and it is
$0.43.** `has_repro_steps` is a column on `claim` written by the extractor, so a
description changes what the model emits from the next call. `judge reweight`
cannot help — it re-prices stored fields and would faithfully re-price 199
falses.

```
  thread_contexts behind the 199 claims        93
  input tokens                            487,060
  output tokens                           115,393
  cost at contract/seed_models.yaml pricing  $0.4346    $0.00467 per thread
```

Measured from the token counts of those very extractions — **n = 93, not the n = 3
estimate.** Two caveats travel with it: it is a measured token count times a
*seeded* price, not a billed amount; and $0.00467 is **56% above the corpus mean
of $0.00299** across all 207 extractions, because threads that yield claims are
longer than threads that do not. Do not reuse it as a per-thread rate.

## 4 · The extraction on the unread threads — held, and the price was wrong

**Projected $4.70, not $2.14.** Fitting input tokens against flattened length
over the 195 extractions with a readable context:

```
  input_tokens = 2,683 + 0.6016 x chars     mean abs residual 1,001 tokens
                 ^^^^^ fixed prompt overhead: system prompt + capability vocabulary

  1,540 unread readable threads
    projected input   7,518,676 tokens      $2.25
    projected output    979,495 tokens      $2.45   at the measured 636/call
    TOTAL                                   $4.70
```

The old `$0.00208` per thread came from **n = 3 calls on one thread** and does not
carry the fixed overhead correctly — a naive chars-per-token ratio over the
corpus reads 0.69 chars/token, which is not a tokenizer property but 2,683 tokens
of prompt amortised over a 682-character median thread.

Output dominates at 2.50/1M. Held pending a decision.

**Restated after the sweep, against the population as it now stands:**

```
  thread_context            1,760
  unread                    1,549      was 1,519 this morning
  readable on this host     1,540      9 payloads absent, named not dropped
  PROJECTION                $4.70      unchanged
```

**The population moved and the number did not, and the reason is worth stating
rather than filing as luck.** Three things happened at once and they cancelled:
the 30 `issue_with_comments` I forked were already inside the earlier 1,540; the
teammate's new Reddit contexts have payloads that are not on this machine, so
they are excluded and counted; and the sweep's 1,145 documents produced **no
thread_contexts at all** (§2.7), so the largest corpus movement of the day
contributed nothing to the extractable set.

A figure that survives its denominator moving is worth re-deriving rather than
carrying, which is why this is a re-run and not a restatement.

## 5 · The 19 rows: a weight change without a `pipeline_version` bump

**Closed. They are explained, and the finding is not the rows.**

All 19 reproduce exactly under `LEGACY_SPECIFICITY_WEIGHTS`, the four-signal form
(`version_named` 0.2, `has_numbers` 0.2, `has_conditions` 0.2, `has_repro_steps`
0.4) that the 2026-08-30 change replaced with the two-signal form. After
modelling that, `stale_before` is **0** — there is no second population of
unexplained weights.

```
  non-reproducing under today's weights        19
    all have document.has_numbers = true       19
    created 2026-08-24 (blog)                  16
    created 2026-08-20 (reddit)                 3
    created after the change                    0
  reproduce under LEGACY                       19
  reproduce under neither                       0
```

**The defect is the label.** `SPECIFICITY_WEIGHTS` changed without bumping
`pipeline_version`, so `e5.1` now names two different arithmetics and only
`claim.created_at` separates them. That is this project's own convention not
holding — *"every derived row carries `pipeline_version`, so any scoring change
is fully re-runnable and diffable"* — and it is precisely what stops a reweight:
**a reweight that cannot reproduce the BEFORE side computes a diff against a
version that never existed.**

Claims created 2026-08-27 onward reproduce under *both* forms, so they are not
evidence that the current weights priced them — with `has_numbers` and
`has_repro_steps` both false the two forms are arithmetically identical. The
19 are simply the rows where the forms disagree.

`scripts/measure_document_facts_gap.py` now models this and says so.

## 6 · Two bugs in my own output, and one guard

**A savepoint is not a commit** — recorded in the previous write-up; the fix
stands and `tests/test_triage_store.py` counts commits rather than `run.written`.

**`⚠` crashes on cp1252, and it crashes only when there is something to warn
about.** `measure_document_facts_gap.py` printed every figure and then raised
`UnicodeEncodeError` on its warning block. I removed the character, then
reintroduced it into the same file within the hour, in a new block, having just
written the comment explaining why not to.

So it is a test now: `tests/test_script_output_is_encodable.py` walks the AST of
every script and checks the string literals reaching `print`. Comments and
docstrings are unaffected and unchecked — they never reach a stream.

It found a third instance immediately, in a file nobody had touched:
`scripts/why_subject_failed.py:211`, same shape — a warning inside an `if`,
carrying the sentence *"the split below is over N and not M"*. A denominator
caveat that disappears exactly when it applies.

### Reproducing

```
python scripts/write_github_comments.py --dry-run
python scripts/multi_shape_sweep.py --plan
python scripts/measure_document_facts_gap.py
python -m pytest tests/test_script_output_is_encodable.py
```

## 7 · The backfill, re-run, and what running the chain actually needs

Re-run after the sweep, because 926 of the 1,065 new NULLs were mine.

```
  eligible when it started        2,679
  scored / written                1,436     in 2 passes; one connection dropped
                                            and the resume loop picked it up
  still NULL                      1,243     reddit 1,234 + github 9
  populated                       3,391 of 4,634
```

Rates over the 1,436 newly scored — mostly GitHub issue bodies, which is why the
shape differs from the corpus:

```
  has_code          99.9%     an issue template is a code fence
  names_version     87.2%
  has_numbers       43.6%
  has_conditions     8.6%
  has_error_strings  8.2%     against 1.9% corpus-wide - the failure channel
```

The 1,243 that stay NULL are payload-absent on this host and are left NULL
rather than written False. Every readable document in the corpus now carries the
columns.

### 7.1 · Nothing is blocking the chain. Nothing is calling it either

`collect ops run` exists at `collect/cli.py:156` and is complete. Checked:

```
  unfinished job_run rows        0      the overlap guard would not refuse
  job_run rows total            24      12 stages x 2 runs
  both runs                     2026-08-20      eleven days ago
  score-documents runs           0      the stage was added today
  .github/workflows/            ci.yml only, no `schedule:` trigger
```

**So it is not a scheduler bug, it is a missing scheduler.** The chain has run
twice in the project's life, by hand, and there is no cron entry, workflow
schedule, or service unit anywhere in the repo. Whatever runs it has to be
created; nothing needs to be fixed first.

### 7.2 · And running it is not a drop-in for the backfill

Two things make `collect ops run` the wrong tool for closing this gap today:

**`sweep-reddit` would fire live.** It is wired, it needs only
`recompute-window`, and `_sweep_reddit_stage` **builds its own Reddit client** —
`context["client"]` is the OpenRouter client and carries no RapidAPI headers. So
`--no-network`, which only withholds that one client, does not stop it. It
refuses on a missing `RAPIDAPI_KEY`, and `.env` has one. A chain run to score
documents would also harvest Reddit.

**There is no way to run one stage.** `ops` has four subcommands — `preflight`,
`sweep`, `sweep-reddit`, `run` — and `run` has no `--only`. There is no
`ops score-documents`.

The smallest honest fixes, in the order they reduce surprise:

```
1  an `ops score-documents` subcommand, or `ops run --only <stage>`
   so the cheap deterministic stage can run without a live harvest
2  a schedule - whatever this deploys onto - invoking `collect ops run`
3  nothing else. preflight passes, the guard is clear, the stage works
```

Until (1) or (2) exists, every document written outside the chain reopens the
gap, and `scripts/backfill_document_facts.py --write` closes it again for
nothing. It is idempotent and a second run exits 0 having scored zero.

## 8 · The GitHub corpus, assembled

`collect assemble github`, after fixing what it selected.

### 8.1 · The selection was wrong, and it had been right until the day before

`assemble_github_documents` selected **every** github document with no
`thread_context`. That was exactly the issue bodies for as long as `document`
held nothing else — every github row had `parent_id IS NULL` because no comment
had ever been written. §1 landed 148 of them, and the premise expired without the
query changing.

Left alone it would have built **148 single-comment thread_contexts, each a
"thread" whose root is a reply.** 99 of those comments are already members of the
30 `issue_with_comments` contexts, so the same text would have reached the
extractor twice under two ids — and a second claim from a re-read of one comment
is a second VOICE from one author, the over-clustering `collect/CLAUDE.md` calls
the worse of the two failures. **23 of them are bots**, and assembling a bot as a
ROOT walks around `assemble_issue_thread`'s member-level refusal from the other
side.

Now `parent_id IS NULL AND status <> 'filtered'`. Either check alone would have
stopped this instance; they guard different things, so both are asserted in
`tests/test_assemble_github_selection_db.py`.

### 8.2 · What it built

```
  candidates                1,295 issue bodies
  assembled                 1,286
  refused                       9   payload missing from this store - the SAME 9
                                    the backfill left NULL, which is the check
```

The GitHub corpus, before and after:

```
                              before   after
  github thread_contexts          71   1,387
    issue_body_only               71   1,357
      NULL   (no comments)        41     771     an empty thread, not 1.0
      0.000  (comments unfetched) 30     586
    issue_with_comments           30      30
      1.000  complete             16      16
      partial                     11      11
      0.000  bot-only              3       3
```

**30 carry comments against 1,357 body-only** — so the comment work covers 2.2%
of the assembled GitHub corpus. **586 of the body-only contexts have comments we
have not fetched, 2,032 of them**, and `hidden_children_min` records that, which
is why their `coverage_ratio` reads 0.000 rather than NULL. The 771 NULLs are
genuinely comment-free issues.

That is the size of the next comment fetch if anyone wants it: 586 issues, one
core request each, and §2's arithmetic says the REST limiter would pace it at
about 8 minutes.

### 8.3 · And it re-prices item 4

Assembly is what turns documents into an extractable population, so the figure
restated in §4 moved again the moment it ran:

```
                        this morning   after the sweep   after assembly
  thread_context               1,725             1,760           3,046
  unread                       1,519             1,549           2,835
  readable here                1,540             1,540           2,826
  median chars                   682               682             829
  PROJECTION                   $4.70             $4.70           $8.29
```

**$4.70 → $8.29, and the cause is 1,286 GitHub contexts that did not exist an
hour ago.** The sweep bought corpus; assembly made it reachable; reachable corpus
is what extraction is priced against. Three restatements of one figure in one
afternoon is the argument for re-deriving it rather than carrying it — and the
$2.14 in the original brief is now 26% of the real number.

## 9 · `run --only`, and a flag that was not doing anything

### 9.1 · `--only <stage>`

```
collect ops run --only score-documents --no-network

  nightly chain, PARTIAL RUN: --only score-documents selected 2 of 14 stages
  (the named ones and what they depend on). The other 12 were NOT ATTEMPTED
  and are not refusals.
  nightly chain: 2 of 2 stages ran, 0 refused, 0 errored
    OK  preflight        passed=3 failed=0 skipped=1
    OK  score-documents  eligible=1243 scored=0 unreadable=1243 written=0
```

Three properties worth naming:

**Dependencies come too.** `score-documents` needs `preflight`, and preflight is
the build-fixture guard. `--only` narrows what is ATTEMPTED, never what is
CHECKED — a `--only` that skipped preflight would run a write stage with the
guard bypassed, which is what `cli.py`'s AST test prevents one layer down.

**The summary carries the denominator.** "2 of 2 stages ran" is true and reads as
a complete night. The 12 nobody selected are **not refusals** — no code declined
them — so they are named in a header rather than given a fourth outcome, which is
the mistake `retrieval_provenance` made and withdrew.

**An unknown name refuses and lists what exists**, rather than selecting nothing
and printing a clean summary of no work.

### 9.2 · `--no-network` was a no-op for the one stage that writes

**`--only` is not enough, and this needed fixing regardless.** `_cmd_ops_run`
implements `--no-network` by withholding `context["client"]`.
`_sweep_reddit_stage` never read it — it builds its own, correctly, because the
registry client carries no RapidAPI headers and a Reddit request through it would
404 at the gateway.

So a flag documented as *"run without an HTTP client"* left the only wired
document-writing stage issuing live requests. `--no-network` is how the chain's
refusals get read without a server; anyone using it to inspect the chain would
have harvested Reddit as a side effect of looking.

**A flag that silently does not apply is worse than an absent one, because the
caller has already decided.** The intent now travels in `context["offline"]` and
the stage honours it — checked after its contract and subreddit checks, so an
offline run still surfaces a missing source row, which is exactly what somebody
reading the chain offline is looking for.

This is a hazard beyond the `score-documents` use, and it would have outlived it:
any future stage that builds its own client inherits the same trap unless it
reads the flag. `--only` reduces the need to run the whole chain; it does not
make a lying flag safe.

## 10 · The scheduler is a decision, so here is the scope and nothing more

**What invoking `collect ops run` nightly needs on this machine:**

```
  the machine        Windows 11. Task Scheduler, not cron.
  the invocation     .venv\Scripts\python.exe -m collect.cli ops run
                     working directory = repo root, because .env is read from it
  the guard          none needed. 0 unfinished job_run rows, so the overlap
                     check passes. It refuses on its own if a run is killed.
  the journal        --journal <path> for the append-only JSONL, which is the
                     only record that survives a killed process
  what stops it      nothing. The command is complete and ran by hand twice
                     (both 2026-08-20). There is no schedule anywhere in the
                     repo: .github/workflows holds ci.yml with no schedule key.
```

**What one night costs at the current corpus:**

```
  preflight           DB only
  poll-registry       1 request to the OpenRouter feed, no credential, ~679 KB
  recompute-window    DB only
  load-capabilities   DB only, idempotent
  sweep-reddit        12 subreddits x 7 pages = 84 RapidAPI requests
                      paced at 25/min -> ~3.5 min
                      quota: 1,000,000/month at 1 per request, so ~2,520/month
                      for nightly runs. The gateway reads 1,000,000 and the plan
                      page says 500,000; either way this is under 0.6%.
  score-documents     CPU + DB. Measured ~1.0 s/document on this host, so a
                      night's harvest of ~200 documents is ~3.5 min.
  ----
  wall clock          ~10 min      API requests  ~85      dollar cost  none
```

**No money, ~10 minutes, and no code.** The remaining questions are ones we
should not answer alone: which machine it runs on (this one sleeps), whether a
nightly Reddit sweep is wanted at all before the terms ruling is revisited, and
who reads the journal in the morning — because the chain's whole premise is that
under cron there is no person, and a scheduled run nobody reads reintroduces
exactly the silent failure it was built to prevent.

Put to the team rather than chosen.

## 11 · The $8.29 extraction is held, and §5 is the reason it should be

**Not "held pending budget". Held because a claim's price is about to change and
the table cannot currently tell you which price it paid.**

Two rulings are open with Engineer 2, and both move what a stored claim is worth:

```
  has_repro_steps gets a description     docs/proposals/for-engineer-2-has-repro-
                                         steps-is-a-question-nobody-asked.md
                                         -> B becomes reachable; every claim the
                                            field fires on moves D -> C or -> B

  the f_specificity double-count         contract/harvest.yaml records it as a
                                         KNOWN over-weight: has_numbers and
                                         has_repro_steps price once in the tier
                                         and once in the factor, 10.6x combined
                                         of which 1.95x is counted twice.
                                         De-duplicating is "a SEPARATE ruling"
                                         and has not been taken.
```

Extracting 2,826 threads before either lands buys claims at a weight nobody has
ruled on, and re-pricing them afterwards is a `judge reweight` fork over a table
an order of magnitude larger than today's.

**And §5 is why this is worse than it sounds.** The 2026-08-30 weight change
shipped **without a `pipeline_version` bump**, so `e5.1` already labels two
different arithmetics and only `claim.created_at` separates them. Nineteen rows
of 199 are on the far side of that boundary and were only explicable because 199
is small enough to characterise by hand. **Run the same pattern across 2,826
threads and the mixed-regime population is thousands of rows, distinguishable
only by a timestamp, in a table whose whole purpose is to be diffable.**

So the sequencing is not a preference:

```
  1  E2 rules on has_repro_steps and on the double-count
  2  whatever the ruling is, it forks pipeline_version - which is the
     convention `e5.1` already broke once and the cheapest possible fix
  3  then extract, at a price that is known and a version that is legible
```

The cost of waiting is zero: the threads are assembled, the payloads are stored,
`run_extraction_batched.py` is resumable, and nothing about the corpus decays in
the meantime. The cost of not waiting is a re-price of the whole board.

**What is worth doing before the rulings** is what has already been done today —
the comment fetch, which touches voices rather than claims and is unaffected by
any weighting decision. A voice is `claim.author_id`; how heavily that claim is
priced does not change who said it.

## 12 · The 586 comment fetch, and the voices it did not move

The cheapest remaining move on voices, run because §8.2 had sized it.

### 12.1 · The fetch

```
  requests issued     586        one per issue, paced by the real limiter
  http errors           0
  comments fetched  2,016        against 2,032 recorded as hidden
  wall clock         ~11 min
```

The script stubbed **both rate limiters with a `_NoWait`** and that had to go
first. Defensible at 30 requests; not at 586 — the 5,000/hour core bucket is not
the risk, the SECONDARY limit is, which GitHub applies to burst rate and answers
with a 403 indistinguishable from a permission error. The tell was arithmetic:
the eight-minute estimate was computed FROM `REST_INTERVAL`, so running unpaced
would have finished faster than the number we costed. Same shape as the
`--no-network` no-op fixed the same day — a control that is present, correct
elsewhere, and bypassed here.

### 12.2 · The deciding metric: 824 authors the bodies did not have

```
  issue-body authors                    1,052
  comment authors                       1,073
  overlap - the same person did both      249      <- ONE voice, not two
  NEW authors from comments               824
  total distinct github authors         1,876      was 1,097
```

**2,016 comments, 1,073 authors, 824 of them new.** The 249 overlap is the
comment path's own argument made concrete: a person who filed an issue and then
commented on another is one voice, and counting comments would have reported
this work as worth two and a half times what it is.

### 12.3 · Voices per cell: 164 -> 164

```
                                  before   after
  cells                              105     105
  independent_voices summed          164     164
  max voices on any cell               7       7
  distinct voices across claims        91      91
  github documents with an author  1,097   1,876
```

**+0, and zero is still the correct answer.** A voice is `claim.author_id`, a
claim comes from an extraction, and nothing here extracts. What moved is the
pool. The cells move when the forked contexts are read — and §11 holds that
until Engineer 2's two rulings land.

### 12.4 · Coverage on the 584 issues that gained comments

```
  before   0.000 on all 584           root read, no thread
  after    mean 0.868, median 1.000
           at 1.000: 454   at 0.000: 48
           observed 1,816 human comments, 216 still unread
```

The 48 still at 0.000 are **bot-only threads** — every reply a GitHub App. Bots
are excluded from `observed` deliberately, so the ratio describes HUMAN coverage:
an issue whose only replies are CI runs has no thread we want, and 0.000 is true
rather than a fetch that failed.

584 re-assembled, 0 refusals, at `collect-0.2.0-issue-comments`.

### 12.5 · ⚠ 586 issues now hold TWO contexts each, and extraction must know

The fork is non-destructive by design (§1.3), so every issue that gained comments
keeps its `issue_body_only` row **and** gains an `issue_with_comments` one:

```
  collect-0.1.0                  issue_body_only        1,357
  collect-0.2.0-issue-comments   issue_with_comments      584
  issues holding BOTH                                     584
```

**An extraction selecting on "no `thread_extraction` row" would read those 584
issues twice** — once body-only and once with comments — and the second read is a
superset of the first. Two claims from one issue body under two context ids is
one author counted as two voices, which is the failure §8.1 was about, arriving
by a different door.

Extraction must filter on `pipeline_version`, not only on the absence of an
extraction row. Recorded here rather than fixed, because which version the board
should read is a decision that belongs with the two held rulings.

### 12.6 · The bot denominator is no longer two, and a new gap has a number

The standing caveat — *"the suffix and `user.type` agree on all 148, but the
denominator is TWO accounts"* — is resolved in `user.type`'s favour:

```
  type: Bot        200 comments from 26 distinct GitHub Apps
  type: User     1,816 comments from 1,073 accounts
  disagreements      0 of 2,016
```

**But seven accounts declare `type: User` and are plainly automation** — 42
comments, 13 issues, led by `tenstorrent-github-bot` at 33. These run on personal
access tokens rather than as GitHub Apps, so the platform has nothing to declare
and correctly says `User`; the `[bot]` suffix misses all seven.

Neither signal sees them, and `triage/gates.py` has reported
`KNOWN_BOT: UNAVAILABLE` since it was written for exactly this. Proposed to
Engineer 2 with the keying question, which is the hard part:
`docs/proposals/for-engineer-2-the-known-bot-list-and-what-it-keys-on.md`.

**The obvious version of that argument is wrong and the proposal says so.** 33
comments is not 33 voices — `gate.count` takes one representative per author, so
it is ONE voice across at most 7 issues, and a bot that WAS a cell's only voice
would trip `max_author_share` at 1.0 against a 0.50 cap. Domination is already
handled. The real exposure is the bot as **one voice among three**: it clears
`n_eff >= 3.0`, leaves `max_author_share` near 0.33, and lands exactly where 91
of 105 cells sit. The gate stops a bot that shouts and has nothing to stop a bot
that nods.
