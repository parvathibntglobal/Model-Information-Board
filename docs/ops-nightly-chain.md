# `collect/ops/` — the nightly chain, the five alerts, startup, and coverage

**A report before building, on four decisions. `collect/ops/` currently holds
nothing but `.gitkeep`.**

*Engineer 1 · 2026-08-18 · every count below is from the remote database or the
working tree on this date, with its denominator stated (rule 7)*

> The lane's other eight directories run when somebody types a command. This one
> runs when nobody is there. Everything below is arranged around that difference.

---

## 0 · What makes a 3am failure visible, before what makes it work

Asked for first, and it changes the design of everything after it.

**Nine silent-failure defects were found in this lane in one fortnight.** Every
one was caught by a person looking at a number that was wrong in a way that read
as an answer. Under cron there is no person:

| defect | what it looked like |
|---|---|
| a rate-limited query counted as `0` results | a query with no matches |
| GitHub Search discarding `OR` and `(` | a capability-scoped query returning a corpus |
| `sieve_any` returning a positional verdict | subject-miss at 100% instead of 67% |
| `needs_second_model` reading two groups of three | an entry that needs no second model |
| `direction:` unvalidated at load | the one machine-readable constraint, silently off |
| `write_documents` counting attempts | rows reported written that were not |
| the first substitution probe taking `topic[0]` | one query measured four times |
| a family word satisfying half a subject | two models named where one was |
| `connect()` with no timeout | a suite that looked hung for ten minutes |

So the chain's first requirement is not that stages succeed. It is that **a stage
which did not run is distinguishable from a stage that ran and found nothing.**
Five rules, each a thing to build rather than a thing to intend:

1. **A stage writes its row before it does its work.** `job_run` is inserted at
   the start with `finished_at` NULL and updated at the end. A killed process
   then leaves *"started 03:00, never finished"*, which is a fact. A row written
   only on success leaves nothing at all, which reads as a night with no work.

2. **Counts are NULL where unknown, never 0** (rule 6). `items_fetched = 0` means
   the platform returned nothing; NULL means we never got an answer.
   `harvest_run` already models this correctly for `exhausted`, and the chain
   must not undo it by defaulting counters at the call site.

3. **Every figure carries its denominator** (rule 7). Yield is stored as
   `(kept, candidates)` per query, never as a rate. Rates are computed where they
   are displayed, next to both numbers, and an alert that fires on one states
   both in its message.

4. **An alert has three states, not two:** `fired`, `did not fire`, and
   **`could not be computed`**. §2 below is almost entirely the third, and an
   alerting layer that reports "no alerts" while its inputs do not exist is
   precisely the failure this lane keeps finding.

5. **Unreachable is fast.** `connect()` now carries a 10-second timeout (#47)
   because a stage that could not reach the database was taking 250 seconds per
   attempt. The chain sets a per-stage wall clock for the same reason: a stage
   that hangs spends the window every later stage needed.

The run report is a row and a printed summary, not an email. Nobody is watching
either, but a row can be read the next morning and a page can render it.

---

## 1 · The chain, and what depends on what

```
  preflight ──> poll registry ──> refresh coverage
                     │
                     └─────────> sweep github ─┐
                                 sweep blogs  ─┼──> assemble ──> triage ──> rollup
                                 sweep reddit ─┘
```

| # | stage | reads | writes | re-runnable? |
|---|---|---|---|---|
| 1 | **preflight** | contract, environment | `job_run` | yes — a gate, it changes nothing |
| 2 | **poll registry** | OpenRouter feed | `model_version`, `model_event`, `pricing_history` | **yes** — upsert keyed on `canonical_id`, unmetered feed |
| 3 | **refresh coverage** | registry | `model_version.in_window`, `coverage_gap` | **yes** — a pure function of the registry |
| 4 | **sweep** ×3 | registry, `watermark` | `raw/`, `document`, `harvest_run`, `watermark` | **partly — see below** |
| 5 | **assemble** | `document`, `raw/` | `author`, `dedup_cluster`, `thread_context` | **yes** — no network, reads stored text |
| 6 | **triage** | `document`, `thread_context` | `document.status`, `triage_verdict` | **yes** |
| 7 | **rollup** | all of the above | `job_run`, the run report | yes |

**Dependencies that are real.** 2 → 3, because the window and the gaps are
computed from the registry. 2 → 4, because a sweep needs alias surfaces and a
model polled tonight should be searchable tonight. 4 → 5 → 6, each consuming the
previous stage's rows. Everything → 7.

**Dependencies that are not real, and must not be encoded as ordering.** The
three sweeps are independent. GitHub failing must not stop the blog sweep: they
share only the registry they both read, and the publication gate needs two
platforms, so losing both because one broke is the expensive outcome.

### When a stage fails

| stage | on failure | why |
|---|---|---|
| preflight | **stop the chain**, record `refused` | it is the check that this environment may write at all |
| poll | continue, record `error` | the sweep can run against last night's registry; a stale registry is worse than a missed night, not worse than a missed sweep |
| coverage | continue, record `error` | it writes a reporting surface and nothing downstream reads it |
| sweep | **continue to the next platform**, record `error` against that source | independent, and `truncated_by` already separates "we stopped" from "we were stopped" |
| assemble | skip triage, run rollup | triage over half-assembled threads would set `status` on rows whose `offset_map` is missing, and `offset_map` cannot be built later |
| triage | continue to rollup | documents stay at their default `kept` — visible as a stage that did not run, not as a corpus that passed |
| rollup | record, exit non-zero | last stage, nothing depends on it |

**Re-runnability, honestly.** The raw store is content-hash addressed, so
re-fetching an unchanged page writes nothing and a re-run is safe everywhere.
What a re-run is not is free: the sweep is the only stage with a metered cost —
GitHub at 30 searches/minute, Reddit at the 25/minute the limiter was measured
at, against a RapidAPI quota read on 2026-08-18 as **1,000,000 per window with
998,660 remaining, resetting 2026-09-11 09:45 UTC**. The window is 23.893 days,
so this chain costs ~21,500 requests per reset — **2.15%**, or 4.30% if the billed
tier is the 500,000 the plan page states rather than the 1,000,000 the gateway
reports (`docs/measurements/reddit-rate-and-quota.md` §1.4). Comfortable either
way. So the sweep resumes from `watermark`
rather than restarting, and stages 3, 5, 6 and 7 can be re-run at will from
stored text. That is the property the workflow doc calls *reprocess from the raw
store rather than re-fetching*, and it holds for every stage after the sweep.

### What is missing before this chain can run end to end

Stated here rather than discovered at 3am. Four stages have no implementation to
call, and the chain will carry them as stages that **refuse loudly** rather than
as stages that quietly do nothing:

| gap | consequence |
|---|---|
| no `document` writer for Reddit or blogs — only `github.write_documents` exists | two of three platforms sweep into the raw store and write no rows |
| no `watermark` writer anywhere | FR-9's *"kill it mid-run and it resumes cleanly"* has no state to resume from |
| **no flattening and no `offset_map`** (FR-14, FR-15) | `thread_context` is never written, so `judge/` has nothing to extract from — and `offset_map` provably cannot be reconstructed afterwards |
| no triage gate — `specificity.py` computes a score and nothing consumes it | `document.status` is never set, so survival cannot be measured |

The chain is worth building before these exist, because it is what turns their
absence into a printed line every morning instead of a thing to remember.

---

## 2 · The five alerts, and what each fires on today

The five are already specified in `docs/logic-and-workflow.md §17`. What follows
is what each would do **tonight**, against real data.

| # | alert | input it needs | rows available today | verdict |
|---|---|---|---|---|
| 1 | adapter yield drop | `harvest_run.items_kept` / `items_fetched` per `(source_id, query_key)` | **0 rows** — remote database and both local ones | **cannot be computed** |
| 2 | triage survival ±2σ | `document.status` from a triage gate, over ≥14 nights | 0 documents, 0 nights | **cannot be computed** |
| 3 | extraction `ValidationError` rate | `judge/` extraction outcomes | none — `judge/` opens no database connection at all | **out of lane, and unwritable** |
| 4 | quote-verification failure above 1% | `claim.quote_verified` | 0 claims | **out of lane** |
| 5 | any registry field change | `model_event` | **0 rows**, against 340 polled models | **cannot be computed** |

**Five alerts, none computable tonight, and only two of them are one writer
away.** That is the report, and it is more useful than a chain whose first run
prints "no alerts".

### 1 — yield drop, and why there is no history

The premise is true of the **adapter objects**: `QueryRun`, `FeedRun` and
`RedditRun` each build a `harvest_run_fields()` dict, and `SieveYield` carries
`candidates`, `kept` and three miss counters. None of it is ever inserted —
`harvest_run` has no writer, which the writer audit on #45 found and deliberately
did not fix.

What history exists sits in measurement documents, and it is **not a baseline**,
because each run used a different vocabulary and scope:

| run | corpus | kept |
|---|---|---|
| 2026-08-13 GitHub, 16-entry vocabulary | 149 candidates | 0 |
| 2026-08-14 GitHub, 24-entry vocabulary + containment split | 636 candidates | 5 keeps of 1 distinct document |
| 2026-08-17 Reddit substitution slice | 1,678 documents | 0 |
| 2026-08-18 Reddit re-sieve | 1,297 documents | 4 (2 on version-only surfaces) |

Comparing 0 of 149 against 5 of 636 measures a vocabulary change, not a platform
change. A yield alert built on these fires on our own edits.

**So the first deliverable is the `harvest_run` writer**, batched from the first
commit — one row per query, 146–600 per sweep, the shape #45 flagged. The alert
arms once it has nights to compare and until then reports *"no baseline: N
nights recorded"*.

### 2 — triage survival, and the burn-in

The workflow doc already says this arms after a 14-day burn-in, because there is
no σ to compute against on day one. Today it is worse than un-armed: no gate sets
`document.status`, so the numerator does not exist either. It should report
**"0 of 14 nights recorded"** — a countdown a person can read, not a green tick.

The 10–15% survival expectation is an estimate to calibrate, and the only
measured component is the specificity floor's 7.7% — which **carries a
parameter**: the floor reads the alias list through `names_version`, so the same
documents drop at 3.8% under the 59 hand-written surfaces and 0.8% under the
1,337-surface registry union. Stated in `docs/measurements/specificity-backfill.md`.

Three of E4's six gates now exist (`collect/triage/gates.py`); the language gate
and the bot list do not, and `TriageResult.unavailable` names them on every
verdict. **A survival rate computed while two gates are missing is an upper
bound**, and the burn-in must not arm a 2σ alert against a baseline collected in
that state — the baseline would move when the gates land, not when the world
changed.

### 5 — registry field change, and the producer that is not there

`model_event` is empty against 340 polled models, and the reason is not the
alerting layer. `_record_event` and `_record_prices` are called from
`load_seed()` only — the 11-model seed path. `write_model_versions`, which is
what actually populates the registry, upserts and returns `{inserted, updated}`
and emits **nothing**. It knows that a row changed; it does not know which
fields, because it never reads the old row.

FR-3's *"price change caught within 24h"* therefore has no producer on the polled
path. The fix belongs in `collect/registry/openrouter.py` and not in `ops/`:
read the prior row in the same batch, diff the fields `_changed_fields` already
knows how to compare, and append `model_event` and `pricing_history` rows. That
is the second writer the alerts are waiting on.

### 3 and 4 are Engineer 2's, and cannot be written from here

Both read extraction outputs, and `judge/` opens no database connection today, so
there is no table for `ops/` to poll. Two shapes are possible — `judge/` writes
its own counters, or extraction returns them to a caller in `collect/ops/` that
writes them — and it is **her call**. Raising it rather than choosing it: the
lane boundary says data crosses once in one direction, and an alerting stage that
reaches into her lane's outputs is the wrong shape for both of us.

---

## 3 · Where startup lives — the answer to #27

`collect/ops/preflight.py`, called as stage 1 of the chain and by the CLI on
**write commands only**.

```python
def preflight(conn, *, environment, policy, sources) -> None:
    assert_no_fixtures(conn, environment=environment)        # build fixtures
    assert_contract_backed(policy, environment=environment)  # NFR-10
    assert_terms_reviewed(sources, ...)                      # NFR-5, already wired
```

**Why the chain and not a server.** The correction already in `CLAUDE.md` is that
there is no server process, so *"asserts on startup"* described something that
does not exist. The nightly chain is the first process in this lane with a
startup at all, which is what makes it the right home and what makes #27
closeable rather than re-worded.

**Why write commands only.** `registry check-sources`, `registry aliases` and
`registry propose-aliases` read and print. Gating them means a broken environment
cannot be diagnosed with the tools built to diagnose it. The gate belongs where
the damage is: `db init`, `db migrate`, `registry load-seed`, and every sweep or
poll command the chain adds.

**What it does tonight, on real data.** The remote database holds 340
`model_version` rows, all `provenance = 'polled'`, with 0 hand-curated cells and
0 hand-seeded thresholds — so `assert_no_fixtures` **passes**, and wiring it costs
nothing today while starting to protect immediately. `assert_contract_backed`
**fails**: `contract/registry.yaml` does not exist, so the policy loads from
built-in defaults, which is exactly the state NFR-10 says must not reach
production. That failure is correct and is the point of the check — `development`
skips both, and the environment variable is what decides.

**Recorded, not merely raised.** A refusal writes a `job_run` row with
`outcome = 'refused'` before exiting non-zero, or a night that refused to start
is indistinguishable from a night cron never fired.

---

## 4 · The coverage surface

`coverage_gap` exists with a deliberately closed `kind` CHECK of four values and
no writer. `LoadReport.coverage_gaps()` already builds exactly those four kinds
as objects, and drops them on the floor.

### What belongs there, and what it would write tonight

| kind | source | rows tonight | denominator |
|---|---|---|---|
| `unsourced-field` | FR-2 gaps in the seed file | **0** | 88 of 88 populated fields carry a source |
| `missing-spelling` | `spelling_gaps()` | **0** | 11 seed models, all three renderings declared |
| `unknown-release-date` | `window_report().unknown` | **0** | all 340 polled rows carry a release date |
| `out-of-window` | released before the trailing window | **60** | of 340 polled rows, window starting 2025-02-18 |

Three of the four are empty tonight, and that is worth writing down: the gaps
those kinds were specified for have since been closed. The fourth is the real
one, and 60 of 340 is a number the coverage page should carry rather than one a
person recomputes.

### What does not belong, and where it goes

| gap | why not `coverage_gap` | where it belongs |
|---|---|---|
| **`alias_coverage` — models with no search surface** | not one of the four kinds, and the CHECK is closed on purpose | **a proposed fifth kind**, below |
| FR-11 truncation | a property of a run, not of a model | `harvest_run.truncated_by`, already correct and already split into caps we chose and the platform stopping us |
| yield drop | same | `harvest_run`, once it has a writer |
| robots-blocked feeds | `blog/robots.py` says it has nowhere to record this | the same fifth-kind question, on the same argument |

**The fifth kind, proposed to Engineer 2 and not taken here** — `contract/` is
shared. The case: of **340 polled models, 7 carry a hand-written alias list**. The
remote registry has never had the seed load applied, and 4 of the 11 seeded
models are absent from the feed entirely (`mistral-large-2411`,
`mistral-large-3`, `deepseek-v3`, `claude-haiku-4-5-20251001`). **333 models
cannot be searched at all**, and a model nobody can search produces silence
indistinguishable from a model nobody discusses. That is rule 4's failure at
registry scale, and the coverage page is exactly where it should be visible.
Proposed value: `no-search-surface`.

### One semantic question, also hers

`coverage_gap_unique (kind, subject, detail, pipeline_version)` stops a nightly
re-run multiplying a gap. It also means **a gap that gets fixed stays in the
table forever**: the row is never contradicted, only never repeated.

Recommendation: the writer replaces the set per `(kind, pipeline_version)` on
each run, so the table means *the gaps as of the last run*, which is what a
coverage page needs to render. History lives in the raw store and in git, not
here. No schema change is needed for that — but it changes what the table means,
so it is a contract conversation rather than a writer detail.

---

## 5 · What I would build, in order

1. `job_run` and the chain skeleton, every stage refusing loudly — the visibility
   layer from §0, before any stage does real work.
2. `preflight`, closing #27, with the `CLAUDE.md` paragraph that currently says
   neither assertion has a caller.
3. The `harvest_run` writer, batched — it unblocks alert 1 and starts the
   baseline alert 1 needs.
4. The `coverage_gap` writer for the four existing kinds.
5. The alert layer, reporting `could not be computed` honestly for all five.
6. Registry events on the polled path — the fix that unblocks alert 5. It lives
   in `registry/`, and is raised here because the alert is what it is for.

Not in this piece: flattening and `offset_map`, the triage gate, and the two
missing document writers. Each is a stage the chain will name and refuse.

---

## 6 · The 121 open `harvest_run` rows, and why they stay open

**Recorded 2026-08-20. They are not a backlog and they are not a crash.**

The first real GitHub sweep opened 121 `harvest_run` rows and closed none.
`GitHubHarvester.outcome_of` returned `fetched`, from the closed set proposed on
issue #5 which never landed, and `harvest_run_outcome_ck` permits
`ok | refused | error` — so `close_harvest_run` raised `ValueError` on every one,
by design, and the caller logged it and carried on. Both halves are fixed: the
adapter returns the schema's vocabulary, and the sweep report now carries
`ledger_failures` so a failed close cannot be a log line again.

**Three options were weighed and the third was taken.**

| | what it costs |
|---|---|
| close them with `outcome = 'error'` | asserts the queries failed. They did not — 21 documents were stored from them |
| close them with `outcome = 'ok'` and a synthetic `finished_at` | **invents a timestamp nothing recorded.** The row would claim to know when it concluded |
| **leave them open, and write down what they mean** | the rows stay honest; the risk moves to a reader inferring a crash |

**The risk the third option carries is the one worth naming.** Everywhere else in
this project a NULL finish means *started and never came back* — that is why the
writer has two phases at all. On these 121 it means **the close was attempted and
refused by a CHECK**. The query ran, the documents landed, and only the verdict
never did.

**So the note lives in the code rather than here.** `collect/ops/ledger.py` now
carries `UNCLOSED_BY_VOCABULARY` beside `DURATION_FILTER`, because the person who
will misread these rows is writing a query and reading that module, not opening a
document. Identified by time — `pipeline_version` is `collect-0.1.0` on both
populations and does not separate them — with a clean boundary: the open rows span
10:01:36–10:13:51 UTC and the 32 correctly-closed ones 10:23:59–10:27:08.

One reader exists and is unaffected: `assert_no_phantom_sweeps` asks only whether
`harvest_run` is empty, before calling a `last_swept_at` a phantom. The 121 make
it non-empty, which is true — those sweeps happened.
