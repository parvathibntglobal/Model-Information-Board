# Engineer 1 — `collect/`: the record

What this lane built, in what order, and why the shape it has is the shape it
has. Written so somebody can pick it up, or do the same job elsewhere, without
repeating the expensive parts.

*2026-08-20 · verified against `origin/main` at `225b126`*

---

## What this is, and what it is not

**This is not a second explanation of the machinery.** Two documents describing
one system is a drift shape this project has met repeatedly — the nearest
in-tree instances are `contract/tables.sql` recording *"the fifth instance of one
drift"* about a derived value stored beside its inputs, and `CLAUDE.md`'s wiring
entry, which *"has now been wrong three times and each correction was smaller
than the last"*. So the boundary is stated once, here, and enforced by pointing
rather than repeating:

| | |
|---|---|
| **`docs/how-it-works.md`** | **how the machinery works.** Mechanism, in the order a claim travels. What a reader needs in order to change something without breaking a guarantee. |
| **`docs/engineer-1/`** (this) | **what was done, in what order, and why.** The record: phases, the measurements that changed a decision, the defect shapes, the rulings and their alternatives. |

**If a sentence belongs in both, it belongs in `how-it-works.md` and this
document points at it.** So there is no description of the sieve here, no
account of what `offset_map` does, no walkthrough of the publication gate. There
are section references instead. Where this document gives a figure that also
appears there, it is because the *history* of the figure is the point — what it
replaced, and what it cannot support.

The companion for the other lane is `docs/engineer-2-handover.md`. It is a
handover; this is a record. The difference matters: a handover is written for
the next person to hold one lane, and a record is written so that a decision
made in week three can be argued with in week nine.

### The four documents

| | |
|---|---|
| **`README.md`** (this) | the boundary, the phase record, and how everything here was verified |
| **`measurements.md`** | every measurement that **changed** a design decision rather than confirming one, with its population and what it does not support |
| **`defect-shapes.md`** | ~30 defects grouped into the shapes they share, sharpest instance each. The shapes are the transferable part |
| **`rulings.md`** | what was decided, **what the alternative was**, and what would revise it |

---

## How this was verified, and where the verification stops

The dominant failure of the past fortnight was **reporting a working tree as a
repository** — a claim true on one machine, at one moment, published as a
property of the project. This document is the permanent record, so every claim
of the form *"X is built"* was checked against the remote rather than the disk:

```
git ls-tree -r origin/main --name-only collect/     module inventory
git show origin/main:<path>                          every quoted line
git archive origin/main collect | wc                 line counts
git grep -n <symbol> origin/main -- collect/         call sites
```

Three things that are **not** the remote, and are labelled wherever they appear:

- **Row counts** come from the database this machine can reach, queried
  2026-08-20. A row count is a property of an instance, never of a commit.
- **Test counts** come from local collection against this branch. CI is the
  authority for anything needing Postgres.
- **The measurement corpora** (`_substitution_slice/`, `_unfiltered_sweep/`,
  `_control_sweep/`, `_blog_so_sweep/`, `raw_store/`) are **gitignored**. They
  are on one machine, a clone reproduces none of them, and one is already gone.
  Every figure drawn from them is cited, not re-derived. `measurements.md` says
  which.

**Where a claim could not be verified it says so in place**, rather than being
left out. An absent figure and a figure that could not be confirmed are
different, and only one of them tells you to go and check. Five such notes, each
opening **Not confirmed** where the figure appears:

| | |
|---|---|
| `README.md` | which test files belong to this lane |
| `measurements.md` §3 | the 5,546-document corpus behind every mention count |
| `measurements.md` §4a | there is no three-channel yield measurement |
| `measurements.md` §8b | the ~23.8% E4 survival ceiling |
| `defect-shapes.md` | "around thirty" defects |

One claim went the other way and is worth naming for symmetry: the 195-comment
author check in `rulings.md` was cited from `judge/CLAUDE.md`, was cheap to
confirm because the fixture is committed, and **was re-verified** rather than
caveated.

### One limit of the method, found by using it

The caller inventory in this document came from an AST sweep over
`git archive origin/main` — every function whose body contains `INSERT INTO`,
`UPDATE ` or `DELETE FROM`, matched against every `Call` node in the tree. It
found 23 write-issuing functions, and it produced **a false positive by name
collision**: it reported `ops/ledger.py:close_run` as called from
`assemble/flatten.py`, which has a local closure of the same name doing
something unrelated.

That is habit 11 in `tests/conftest.py` — *a name match is evidence about a
string, not about a thing* — reproduced by the tool written to check for it, in
the document about it. The counts below were confirmed by grep per symbol
afterwards. It is recorded because it is the cheapest possible demonstration
that the habit is not about carelessness.

---

## The lane, at a glance

```
collect/    56 Python modules, 16,722 lines        (git archive origin/main)

  registry/   13 modules   4,658 lines   E1  know every model, and the facts
  adapters/   17 modules   5,809 lines   E2  search three platforms
  assemble/    7 modules   1,663 lines   E3  dedupe, flatten, emit offset_map
  triage/      4 modules   1,138 lines   E4  drop junk deterministically
  ops/         5 modules   1,106 lines   E9  the chain, the ledger, the alerts
  (top level) 10 modules   2,348 lines       store, db, http, ids, cli, migrate

tests/      62 files touching this lane, 1,534 tests collected
```

> **Not confirmed — which test files belong to this lane.** The 62 and the 1,534
> are real: the files were listed by hand and `pytest --collect-only` counted the
> tests. **What is not verifiable is the ownership boundary.** Several files are
> shared or arguably the other lane's — `test_migrations.py` and
> `test_insert_types.py` compare a schema both lanes write, `test_ci_workflow.py`
> guards a job neither owns, `test_job_run_ledger.py` covers a table this lane
> writes and both read. There is no ownership marker in the tree, so **treat 1,534
> as "tests that fail if `collect/` breaks", not as a contribution figure.** The
> whole suite is **1,932**, which is the only test count in this directory that is
> a fact rather than a partition.

**This lane never calls a language model. Not once.**
`tests/test_lane_boundary.py` asserts it by AST over every file in `collect/`:
no import of `anthropic`, `openai`, `litellm`, `langchain`, `transformers` or
`ollama`, and no import of `judge/` in either direction. The same file asserts
that `collect/registry/` cannot import `collect/adapters/` — the registry must
not be able to *see* harvest — which is a constraint that has already changed a
design: `propose._clean` exists because importing `sieve.normalize` would have
broken it (`rulings.md` §9).

---

## The order the work happened in, and why

Not the order in `BUILD-PLAN.md`, and the difference is the useful part.

```
week 1-2   registry (seeded)  ·  the three adapters  ·  the raw store
week 2-3   the query contract  ·  the sieve  ·  rate limits measured
week 3     the measurements start, and start changing the design
week 3     assemble: dedupe, authors, flattening + offset_map
week 3     triage: the specificity floor, then the hard gates
week 3     ops: preflight, the chain, the ledger
```

**The registry came first because it has no dependencies**, and that ordering
was right for a reason nobody stated in advance: it is the only stage whose
output every other stage reads. Harvest queries alias surfaces, triage resolves
against alias surfaces, and the answer path filters on prices. A late registry
would have meant every downstream measurement was taken against a stand-in.

**The adapters came before the measurements, and that was the mistake to
learn from.** Three of the four query-shape findings in `measurements.md` would
have changed the adapter design if they had arrived first: `(a OR b)` grouping
and wildcards are silently discarded, quoting does not bind a phrase, and a
trailing numeral matches the issue number. Twelve query templates were written,
shipped, and removed. **The cheapest of those controls was two API calls.**

**Assemble waited eighteen days on purpose**, and that is the one deliberate
delay in the sequence. `assemble_thread` refused to exist until the coverage
columns landed, because a selection that cannot state what it saw writes *"the
top 5 children"* when it means *"the top 5 of the 4% we happened to fetch"*
(`rulings.md` §5).

---

## Phase E1 — registry

`collect/registry/`. 13 modules, 4,658 lines.

### Built

| module | what it does |
|---|---|
| `openrouter.py` | the daily poll. 414 feed entries → 340 models, service tiers folded in, absent fields written as explicit NULL |
| `aliases.py` | `model_alias` rows, append-only and time-aware; collision detection over overlapping validity windows; the three-rendering spelling floor |
| `propose.py` | proposes alias surfaces from three kept-apart inputs — mechanical, attested, by-rule — and refuses routes |
| `tracked.py` | which models get swept: two seating grounds, one recorded refusal |
| `seed.py`, `load.py`, `models.py` | the seed contract → `model_version`, `price_tier`, `model_event`, `pricing_history` |
| `sources.py` | `contract/sources.yaml` → `source` rows, and the terms rulings |
| `assertions.py` | the four startup checks |
| `policy.py`, `window.py`, `events.py` | contract-backed thresholds; `in_window`; the FR-3 event producer |

Verified present on `origin/main`, and verified live: `model_version` holds
**340 rows, every one `provenance = 'polled'`** — 280 `in_window`, 60 not, and
**17 routes** (queried 2026-08-20, not a property of the commit).

### Deliberately not built

- **Hugging Face Hub and per-provider model APIs.** The spec names three
  sources; one endpoint covers most of the market and is the backbone of
  completeness. A second source is a second reconciliation problem, and nothing
  yet needs it.
- **An automatic alias loader for polled models.** The feed gives
  `anthropic/claude-opus-5` and `Anthropic: Claude Opus 5`. It does not give
  `opus 5`. Generating surfaces mechanically was measured and refused
  (`rulings.md` §2); the proposer produces a *reviewable* artifact instead, and
  `alias_coverage()` reports the gap rather than papering over it.
- **A `~vendor/…-latest` seat, at any threshold.** `rulings.md` §1.

### Still unbuilt

- **`capability` has no loader**, and `claim.capability_key` references it. The
  twelve keys sit in `contract/capabilities.yaml`. **Nothing can write a claim
  until this table has rows** — the smallest unblocking task in the repository.
- **`model_event` is written and never read.** Both writers are called; 0 rows,
  because a first poll has no prior state to diff. FR-3's consumer does not
  exist.
- **`mark_swept` has no caller**, so `last_swept_at` is NULL everywhere and the
  rotation the tracked set exists to feed cannot be measured.
- **`load_source_rows` has no caller**, so `source` holds 0 rows — which is why
  `open_harvest_run` refuses with a sentence naming the loader rather than a
  foreign-key error.
- **The tracked-set thresholds are not in `contract/`.** Drafted in
  `docs/measurements/tracked-set.md` §5 with two open questions.

---

## Phase E2 — adapters

`collect/adapters/`. 17 modules, 5,809 lines — the largest phase, and most of
it is not fetching.

### Built

| | |
|---|---|
| `github.py` | search → **sieve → fetch**. Two raw artifacts. Separate limiters for search (30/min) and core (5,000/hr) |
| `reddit.py`, `reddit_comments.py` | search, comment trees, the coverage counters, the full quota triple per call |
| `blog/` — 7 modules | `fetch` `parse` `robots` `rules` `validators` `options` `write`. RSS + sitemaps, conditional GET, per-hop robots re-check, 8 MB caps |
| `queries/contract.py` | `contract/queries.yaml` → typed entries; placeholder substitution in one place |
| `queries/sieve.py` | the local relevance filter. 613 lines, and the precision of the whole system |
| `queries/cadence.py` | daily vs weekly, **derived** from `stance` × `failure_mode` rather than listed |
| `queries/github.py` | the per-index rendering |

The sieve is the largest single module in the lane and it is not an adapter. That
is the shape the measurements forced: retrieval is broad and cheap because no
index can carry what these terms need, so precision moved local, where it is
identical on all three platforms (`how-it-works.md` §4.4).

### Deliberately not built

- **Query strings in `contract/queries.yaml`.** Term sets instead. A rendered
  query in a platform-neutral file is a string that is true for no platform
  (`measurements.md` §1).
- **`(a OR b)`, wildcards, phrase operators, appended aliases as scoping.** Each
  measured and each discarded (`measurements.md` §1).
- **A narrower sweep scope as a budget lever.** Measured inert: one repo and two
  repos both cost 896 requests. `repo:`/`org:` is a qualifier *inside* a query,
  not a multiplier of them. **A contract naming an inert lever is worse than
  naming two**, so it was removed from `harvest.yaml`.
- **Scraping, paywall circumvention, LinkedIn.** Official APIs and public feeds
  only, `robots.txt` honoured per redirect hop, identifying User-Agent with a
  contact URL. A source whose terms forbid this use is dropped, not worked
  around (`rulings.md` §3).

### Still unbuilt

- **No document writer for Reddit.** `document` holds **30 rows, every one
  `source = 'blog'`** (queried 2026-08-20). `github.write_documents` exists and
  is called only from `scripts/harvest_github.py`. This is the single biggest
  gap in the lane: the corpus every alias and survival measurement rests on was
  Reddit, and none of it is in `document`.
- **`harvest_run` has a writer and no caller.** `ops/ledger.py:open_harvest_run`
  and `close_harvest_run` landed 2026-08-19; grep finds no production call site,
  and the table holds 0 rows. **This corrects
  `docs/measurements/unwired-tables.md`, which lists `harvest_run` as having no
  writer** — true when written, stale now, and the consequence is unchanged:
  `assert_no_phantom_sweeps` compares `last_swept_at` against `harvest_run` and
  **both operands are still pinned at zero**, so the check cannot fire in either
  direction.
- **`watermark` — FR-9's durable cursor.** No writer. A kill mid-sweep loses its
  position.
- **The three sweep stages in the nightly chain**, which is what would give any
  of the above a caller (`how-it-works.md` §9.1).

---

## Phase E3 — assemble

`collect/assemble/`. 7 modules, 1,663 lines.

### Built

| | |
|---|---|
| `flatten.py` | one left-to-right walk; entities decoded before symbols substituted; per-platform rules; emits the segment map |
| `thread.py` | child selection, the coverage columns, `selection_method` with its qualifier |
| `article.py` | a blog article as a thread of one |
| `dedupe.py` | three mechanisms in descending order of certainty; sentinels never merged |
| `signature.py` | MinHash + LSH over character shingles, blockquotes excluded |
| `authors.py` | `author` rows, `handle_hash`, and the overlap *measurement* that is deliberately not a matcher |

Verified live: `thread_context` holds **32 rows, of which exactly 2 carry a
non-NULL `coverage_ratio`** — the two Reddit threads. The other 30 are blog
articles, where `observed_children = 0` and `hidden_children_min = NULL` leave
the generated `CASE` nothing to divide. That is the ruling in `rulings.md` §6
visible in the table.

### Deliberately not built

- **simhash.** `document.simhash` stays NULL. Measured over 79 ground-truth pairs
  and 951 stranger pairs: MinHash separates better at **every** length, and
  simhash's margin at 400–800 tokens is **one bit of 64**. A measured decision,
  not an unimplemented column (`measurements.md` §5).
- **FR-17, author identity clustering.** Not one observed cross-platform
  instance over 4,153 documents. A clustering rule with no observed case is a
  rule written from imagination, and §3.4 of `how-it-works.md` records what that
  cost the last time. `identity_cluster_id` is never written.
- **A per-platform `So` rule.** The symbol set was read off one Reddit fixture
  and does not generalise; the blog corpus refused **both** candidate
  replacements. It stays global and wrong-in-a-known-way rather than narrowed
  from a corpus of two (`measurements.md` §6).
- **An object store.** Content addressing makes it a deferral rather than a
  shortcut: migrating is a file copy plus a `text_ref` rewrite (`rulings.md` §4).

### Still unbuilt

- **`write_thread_context` and `write_authors` have no caller.** Both are
  correct, both are tested, and the only rows that exist were written by hand or
  by a script. `claim.author_id` references `author`, which holds 0 rows.
- **`dedup_cluster` has no writer**, so syndicated copies would count as
  independent voices the moment anything counts them.
- **`extraction_version` / `content_fingerprint` on `thread_context`** — proposed
  on issue #5, unruled, and the reason the identifier under-identified once
  (`defect-shapes.md` §7).

---

## Phase E4 — triage

`collect/triage/`. 4 modules, 1,138 lines. The smallest phase and the one whose
verdict is least reproducible.

### Built

| | |
|---|---|
| `specificity.py` | five counted components, the composite, and the **tri-state** floor verdict |
| `gates.py` | six gates, no short-circuit, and `NotRun` with two members |
| `entity.py` | the union surface population, its fingerprint, and word-boundary-aware matching |

Three of six gates are built; `out_of_window` is built and usually
`NOT_APPLICABLE`; two cannot be built yet.

### Deliberately not built

- **A trained spam classifier.** It needs labels that do not exist, and the hard
  gates already remove the overwhelming majority. It arrives later, trained on
  the labels this stage generates for free.
- **A threshold on the weighted specificity score.** The floor is a five-way OR
  over the components and reads no weights at all, so a weight change cannot
  alter which documents are dropped — only how survivors rank. `score > 0` and
  `any(component)` coincide today and **diverge the moment anyone calibrates**.
- **Cross-channel ranking by `specificity_score`.** Ruled out, not deferred:
  0.45 of the weight is largely a proxy for *medium*, so the composite ranks
  channels while wearing the clothes of ranking documents (`measurements.md` §4).

### Still unbuilt

- **The language gate.** No detector installed, none declared in
  `pyproject.toml`, `document.lang` nullable with nothing populating it. A
  dependency decision before it is a line of code.
- **The known-bot list.** Rule 5 puts a filter rule in `contract/` and it is not
  there. `ClaudeAI-mod-bot` is already in the top five authors of the
  1,297-post corpus, so the gap is real rather than theoretical.
- **`triage_population` and `gates_unavailable` on `document`.** Without the
  first, a verdict is not reproducible — the population moved 29.7% of one
  corpus with no document changing (`measurements.md` §7).
- **Nothing writes `document.status` or `document.specificity_score`** in a
  nightly run, so triage survival has neither a numerator nor a denominator, and
  alert 2's burn-in cannot start counting.

---

## Phase E9 — ops

`collect/ops/`. 5 modules, 1,106 lines.

### Built

| | |
|---|---|
| `preflight.py` | the four startup checks, run before anything writes. A check whose input is absent is **skipped and named**, never counted as a pass |
| `chain.py` | the nightly chain. 3 stages run, **9 refuse and say what they starve** |
| `ledger.py` | `job_run` rows, written **before** the work; `harvest_run`'s writer |
| `alerts.py` | the five alerts, and the third state every one of them is in |

Verified live: `job_run` holds **12 rows**; `schema_migration` holds 3.

The chain is the first process in this lane with a startup at all, which is what
made issue #27 closeable rather than re-worded a third time
(`defect-shapes.md` §2).

### Deliberately not built

- **A workflow engine, a queue, an event bus.** A jobs table and cron. Eight
  scheduled jobs do not need Airflow, and the deferral is recorded in
  `CLAUDE.md` as a decision not to relitigate.
- **Stubs for alerts 3 and 4.** They read extraction outputs, which belong to
  the other lane. **A stub is a producer nobody wrote**, and it would report
  QUIET forever while nothing measured anything. They appear in the list with
  `owner="judge/"` and no implementation.
- **Arming the survival alert.** It needs a 14-day burn-in, and the burn-in
  cannot start while three of six gates are missing: a baseline collected then
  moves when the gates land rather than when the world changes, which is an
  alert firing at its own construction.

### Still unbuilt

- **`coverage_gap` has no writer**, and `judge/pages/coverage.py` reads it in two
  places. `load.py:coverage_gaps()` builds the objects; nothing inserts them.
  Four `kind` values are declared and none is produced.
- **`audit` has no writer, no reader and no mention anywhere.** It wants a ruling
  rather than a fix.
- **The rollup stage**, which is what would make `ops.alerts` produce anything.

---

## What the numbers say about the lane as a whole

Three sentences, each verified above and each uncomfortable:

**The pipeline is built and almost nothing has run through it.** 56 modules,
1,534 tests, and `document` holds 30 rows from one channel. Six write-issuing
functions have no caller. Nine of twelve nightly stages refuse.

**The measurements changed the design more than the design guided the
measurements.** Of the ten in `measurements.md`, **nine changed something already
written and shipped** — a query file, a rate constant, an alias list, a floor's
justification, a dedupe method, a flattening rule, a matcher, a threshold, a
`0` that was an unknown. The tenth added a requirement nobody had thought of:
that a triage verdict needs a **population identity** to be reproducible at all.
That is the argument for measuring earlier, not for measuring more.

**Every gap above is visible from inside the system**, which is the one property
that was designed for rather than discovered. The chain names what each refusal
starves; the alerts report `CANNOT COMPUTE` rather than QUIET; the floor returns
UNKNOWN rather than DROPPED; `NotRun` has two members so the count of
unrunnable gates falls to zero as they are built rather than growing as coverage
improves. **A system that cannot say what it has not done reports a quiet night,
and that is the failure this lane spent most of its design budget on.**
