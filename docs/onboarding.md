# Onboarding

For an engineer joining with nothing read. It is organised by **the path a claim
takes**, because the `collect/` → `judge/` split is an implementation detail and
the path is the thing.

The two things you should be able to do alone by the end of your first week:

1. **Answer "why does the board say nothing about this model?"** without asking
   anyone. There are four different answers and they live at four different
   stages. §12 walks it.
2. **Find where a decision was made** without asking who made it. Every ruling
   is written down, dated, and says what it ruled *out*. §13 is the index.

---

## 0 · How to read every number in this document

Three conventions, and they are not stylistic. They are rules 6 and 7 (§5)
applied to this file.

**Every figure carries its population.** If a number came from one slice on one
model on one day, it says so beside the number. `52.7%` is not a claim;
`52.7% of 636 candidates retrieved for one model using that model's own
variants` is. Where you see a bare number in an older document, distrust it —
that is the defect this project has paid for most often.

**Nothing is called "built" here without checking the definition.** The check is
`grep "def <name>"`, never `grep "<name>"`, because a bare substring matches any
longer identifier and an absent symbol comes back looking defined. For "is this
on the remote", the check is `git log --oneline origin/main -- <path>` or
`git show origin/main:<path>`, never reading the working tree — a claim true on
one machine at one moment is not a property of the project. Both of those were
learned expensively; §11 has the incidents.

**What could not be verified is marked, not omitted.** An absent figure and a
figure that could not be confirmed are different things, and only one of them
tells you to go and check. Look for **⚠ NOT VERIFIED**.

Figures below are of **2026-08-31** unless dated otherwise. Database counts are
from `203.0.113.5/Model-information-Board`, the shared staging instance — **a row
count is a property of an instance, never of a commit.**

---

## 1 · The board in one paragraph, and its current state

The board reports what engineers *publicly say* about AI model capabilities, and
an advisor uses it to recommend cheaper models for sub-agent tasks. It publishes
**quote + attribution + link**, never full text, never a score.

Where it actually is today:

```
model_version                 342     every one provenance='polled', zero seeded
models with any alias           41     so 301 of 342 cannot be searched for at all
document                     6,502     github 3,382 · reddit 2,999 · blog 121
thread_context               3,600
claim                          211     all at pipeline_version e5.1
                                       all quote_verified = true
cell                           105     all `insufficient`
models with any cell            39     so 303 of 342 model pages are empty
PUBLISHED CELLS                  0     for the life of the project
```

**Nothing has ever published.** That is not a bug you are being handed to fix
casually — it is an arithmetic property of the weighting, it has been measured
four times by two people, and §6 is the whole derivation. Read §6 before
proposing anything about collecting more data.

---

## 2 · Where the data lives

### Postgres — the shared staging instance

One database, both lanes, `DATABASE_URL` in `.env`. Not a copy each: the
precedent matters, because the raw store went the other way and it cost
something (below).

Migrations live in `contract/migrations/`, timestamped filenames, applied **once,
in order, by whoever merges the migration PR, immediately after merge, and
announced the same day**. Check the ledger before applying — it got out of step
once. Before a staging write session, say so, so two people are not writing the
same afternoon.

`run-backend.py --staging` forces `default_transaction_read_only=on` at the
server, so no code path in that process can write whatever it tries. The
guarantee is in Postgres, not in a promise about which functions only SELECT.

### The raw store — and this is the thing that will confuse you first

**`RAW_STORE_PATH` points at a gitignored directory on one machine.** You will
query the database, see a `document.text_ref` like
`raw/sha256/05/d2/05d2de39…`, try to read the document, and fail. Nothing is
broken. The bytes are on somebody else's laptop.

```
collect/config.py:94    raw_store_path = RAW_STORE_PATH or <repo>/raw_store
.gitignore:12           raw_store/
on the machine that has it (2026-08-20)   180 files, 8.6 MB
```

The two columns mean different things, and this was ruled explicitly
(`docs/engineer-1/ruling-what-content-hash-identifies.md`, 2026-08-28):

```
content_hash    identity — the hash of the BYTES THE PLATFORM GAVE US, unmodified
text_ref        location — where those same bytes are
prose           DERIVED at assembly, never stored in place of the payload
the invariant   content_hash(resolve(text_ref)) == content_hash, always
```

The invariant is **necessary and not sufficient**, and that is the interesting
part. It catches a *mismatch* between the two columns. It cannot catch a *wrong
choice* of what both point at — which is the failure that actually happened,
twice, on two platforms, because the repair script updated `text_ref` and
`content_hash` together and so the hash always matched its artifact. It was
simply the wrong artifact. Measured after the repair: the invariant holds on
1,763 rows, violated on 0, **and 246 of those 1,763 still point at pre-extracted
prose** — the exact defect the ruling exists to fix. That residue is open (§10).

The check that catches the wrong choice is the cheap one and it now lives in
`tests/test_assembly_prose.py`: *does the flattened text parse as a JSON object
or array, or start with `<`*.

**Why `_handoff/` works when the store does not:** it inlines. Each exported
thread carries a `raw_text_of` mapping of document id → text, so nothing resolves
a ref. That is a copy, not a pointer, which is why the export path has never hit
this — and the cost is that `RawStoreReader`'s outcomes have never run against
anything real.

`collect/rawstore_reader.py:246 def resolve` maps store exceptions onto
`judge/`'s three-state outcome. Two `except` clauses, both named, deliberately:
`PayloadTombstoned` is a deletion we honoured on purpose and **nothing is
broken**; `PayloadMissing` is a bug and an urgent one. `except RawStoreError`
would catch both and fold a deliberate deletion into a data-loss alarm — and the
payload is gone in both cases, so there is nothing left to disagree with the
wrong answer.

⚠ **Corruption is undetected rather than mishandled.** Verified 2026-08-19:
`RawStore.get` computes no hash on any read path; `RawStore.verify` is the method
that hashes and has **no production caller** (two test call sites); and
`PayloadCorrupt` is raised only by `put()`, on a *size* mismatch. So a `CORRUPT`
outcome will read zero until something computes a hash on read.

### The gitignored measurement corpora

`_substitution_slice/`, `_unfiltered_sweep/`, `_control_sweep/`, `_blog_so_sweep/`,
`_handoff/`, `_sweep_store/`, `raw_store/`. **A clone reproduces none of them and
one is already gone.** Every figure drawn from them is cited, never re-derived.
This matters practically in §11: one of them makes a committed test fail on the
machine that has it and skip on the machine that does not.

---

## 3 · The path a claim takes

Seven stages. The lane boundary is crossed exactly once, in one direction, and
nothing flows back:

```
collect/  ---->  document + thread_context (carrying offset_map)  ---->  judge/
```

The `contract/` directory is the agreement between the two sides. It gets two
eyes: **a contract change is proposed and reviewed, never taken solo.**

---

### Stage 1 · Harvest — get candidate documents

**What it does.** One adapter class per platform, official APIs and public feeds
only. `collect/adapters/{reddit,github,blog/}`. Queries are rendered from
`contract/queries.yaml` — 26 entries, each carrying
`subject / topic / signal / stance / records_condition`. The sieve
(`collect/adapters/queries/sieve.py:450 def sieve_any`) requires **subject AND
topic AND signal** within a locality window of 1,200 characters.

Durable cursors live in `watermark`; every run writes a `harvest_run` row
(1,163 of them today) so the population of any figure is recoverable from the
database rather than from a document.

**What it refuses to do, and why.**

- **No scraping, no paywall circumvention.** `robots.txt` respected, identifying
  User-Agent with a contact URL. Every source carries a dated `terms_ruling` in
  `contract/sources.yaml` plus its own mechanical `terms_evidence`, and
  `assert_terms_reviewed()` demands both — a known unexpired ruling *and*
  re-verified live preconditions. A class ruling asserted forever against a site
  that changed in October is the placeholder failure with extra steps.
- **A 404 `robots.txt` is not consent.** It is the absence of a crawl policy.
  The class-A ruling says so in its own text.
- **The blog class-A ruling refuses to claim more than it checked.** In its own
  words: *"NO TERMS PAGE HAS BEEN READ FOR ANY OF THE NINE FEEDS."* Robots
  permission and terms permission are different things from different documents,
  and only the first is established. The deferral is written into the ruling
  rather than left as an absence somebody later reads as a clearance.
- **Routes are not models.** Worth 10.6 points of survival on its own (below).

**What it measured.**

*The retrieval bias — 58.1 percentage points.* Identical code, identical gates,
identical surface population:

| corpus | what it is | survival |
|---|---|---|
| **A** | model-name-retrieved slice, 1,297 Reddit posts | **78.0%** |
| **B** | unfiltered, 26 AI subreddits × 75, no query terms | **19.9%** |
| **C** | Tier 1 general-technical control (programming, webdev) | **0.4%** |
| **D** | Tier 2 non-technical control (movies, cooking, AskReddit) | **0.0%** |

**Retrieval bias A → B is 58.1pp; the topicality bound B → C is 19.5pp**, so
19.5 of B's 19.9 points are topicality and the pipeline's own discrimination on a
technically-literate population is **0.4%**.

*Population:* B is 1,925 posts over 11 subreddits × 175 then 26 × 75,
`/getPostsBySubreddit` sort `new`, no query terms, 2026-08-18, 78 calls. C and D
are 750 control posts, 30 calls. **Survival within those subreddits — never
survival over Reddit, which is not sampled.** Every basis for choosing subreddits
biases upward.

What it changed: it killed the practice of quoting a survival figure from a
search corpus. **Every one ever published was too high by roughly 2.5×**, and a
2σ baseline built on one would have been calibrated against a population that
does not exist. It also found two code defects — the entity matcher crossed word
boundaries (`free` inside "freeze", `fusion` inside "confusion", `saba` inside
"wa[s a ba]d") and routes were counted as models.

The sampling lesson is larger than the figure: the design report predicted a
design effect of 1.5–3 and sized n=2,000 against it; **measured, it is 14.5.**
Survival ranged from 15.4% (r/singularity) to 59.4% (r/LocalLLaMA) over 175 posts
each. **Effective n is 132, not 1,925**, and the 95% CI widens from ±2.1pp to
±7.9pp. The subreddit is the unit of variation, so more pages buys almost nothing
and more subreddits is the only thing that buys precision.

*Read this one if you read one measurement.* The predictions were committed
**before** fetching — Tier 2 under 1%, Tier 1 at 3–8% — and both missed in the
same direction (5.0%, 17.8%). Tier 1 alone would have read as *"the technical
control is higher than expected, interesting."* **Tier 2 at 5% on posts about
movies is not interesting, it is broken.** The control found a real defect by
failing its own prediction, on the first run.

*The signal vocabulary is the binding constraint.* Over 32,723 GitHub candidates
re-sieved offline with the same matcher the sieve uses:

```
signal terms in contract/queries.yaml       207
  fired at least once                       105
  NEVER fired                               102   (49.3%)
`truncat` alone                          34.2% of all firings
top 10 terms                             64.8% of all firings
```

Per-entry — which is what one request actually asks, median 8 terms — the median
across 26 entries is **0.39%**, best 9.05%, and three entries are at exactly
0.00%. On 119 blog documents the same figure is **0.42%**. **101 of 207 terms
fire on neither platform.**

*Per-channel yields.* ⚠ **NOT VERIFIED — there is no three-channel yield
measurement.** Reddit has never been sieved for per-channel yield. The comparison
that exists is two channels: GitHub 0.39% against blogs 0.42% per-entry, over 285
documents (174 GitHub candidates, 111 blog articles, re-scored 2026-08-17 under
the 59 hand-written alias surfaces loaded that day). Anybody quoting "the
per-channel yields" is quoting GitHub and blogs. The GitHub half is also narrower
than it looks — those 174 were retrieved for three capabilities and one model, so
signal terms belonging to the other eighteen entries never had a fair chance
there. The blog 111 are unfiltered, so blogs are the fairer test of recall.

**What is unbuilt.**

- `harvest_run.outcome` vocabulary is proposed, not settled
  (`docs/proposals/harvest-run-outcome-vocabulary.md`). The only per-model sweep
  record in the database is 153 GitHub rows on 2026-08-20 with `outcome IS NULL`
  on 121 of them.
- `KNOWN_BOT` has reported UNAVAILABLE since it was written (§10).
- `collect/adapters/github.py` sets `max_pages = 1` and its own docstring records
  that this is *"the default, and every run so far."* Nobody fetches page 2.

---

### Stage 2 · Assemble — documents into threads

**What it does.** `collect/assemble/` turns raw payloads into `document` rows and
one `thread_context` per thread, carrying the flattened text and an
**`offset_map`** so a quote's offset in the flattened text can be mapped back to
the raw bytes. That map is what makes rule 1 checkable across a platform's
markup.

`collect/assemble/flatten.py:317 def flatten`. Flattening rules are
**per-platform**, and entities are decoded before symbols.

**What it refuses to do, and why.**

**Assembly refused to exist for eighteen days.** `assemble_thread` raised
`AssemblyNotBuilt` rather than returning a tree, until the four coverage columns
landed on 2026-08-18.

The argument, and it is the single best illustration of how this project decides
things: **a selection that cannot state what it saw writes "the top 5 children"
when it means "the top 5 of the 4% we happened to fetch."** One `getPostComments`
call returned **200 of 4,833** comments. Reddit orders *siblings* rather than the
tree, with 30% of adjacent pairs score-inverted and a depth-2 comment scoring 610
sitting under top-level comments scoring 6 — so **the last-seen score bounds
nothing unseen**, and a global ranking is not available from this data at all.

The alternative was to ship and add coverage later, which is what almost every
schedule wants. It was refused because **the row it would have written is
indistinguishable from a correct one**: `child_count = 5`, a valid `offset_map`,
a `selection_method` naming a global ranking. Nothing downstream could have
detected the difference, and claims extracted against it would have been counted
as *"five engineers"* with no record that five was out of two hundred out of
nearly five thousand.

The narrower ruling inside it: `selection_method` must never write the schema's
bare default `specificity_x_log_engagement`, because a row reading the default
claims exactly the thing the refusal spent eighteen days protecting. It writes
`specificity_x_log_engagement@observed`; a one-member thread (a blog article)
writes `whole_document`.

Also: **a blog writes `None` rather than `0`** into the coverage columns. Nothing
was ranked, so there is no ratio — and `0` would be a definite answer to a
question that was not asked.

**What it measured.**

*Dedupe — the number survived and the design did not.* MinHash + LSH separates
duplicates from strangers **better at every length**, including the long bands
simhash was specified to own. **simhash's margin at 400–800 tokens is one bit of
64**; re-run in simhash's conventional word-3-gram tf-weighted form its margins
were 0–12 bits.

*Population:* 6,824 stored documents; **79 ground-truth duplicate pairs** and 951
stranger pairs drawn from 3,767 Reddit documents, 2026-08-17. All 79 are Reddit
self-syndication and crossposts; **the corpus contains no blog syndication at
all**, so nothing is measured on the channel FR-16's own example is about.

`collect/CLAUDE.md` specified two methods. The two-method design is gone and
**`document.simhash` stays NULL as a measured decision, not an unimplemented
column.** `min_tokens_for_signature: 200` survived but means something different
— a *floor* below which no signature is computed, rather than a switch between
methods. The band the data supports is (50, 200); 200 is the top of it, chosen
because the lane's own rule says over-clustering is worse than under-clustering.

*The blog symbol census — both candidate rules were wrong.* **Zero of the five
entities** reached the flattener across 53 articles / 519,997 characters. The
author's own counter-examples — `°`, `©`, `®`, `™` — occurred **zero** times. The
dominant symbol class is box-drawing characters inside fenced code blocks, from
**2 documents out of 106**.

It changed one thing and stopped a second. `FlatteningRules` became per-platform
with `decode_entities = False` for blogs, because trafilatura has already decoded
and decodes twice (isolated against bare lxml: `type &amp;gt; here` → `type >
here`). And the `So` symbol rule was **not** narrowed, because the corpus refused
both candidate replacements — narrowing from a corpus of two would have repeated
the original mistake in the other direction.

*"Rules are wrong" is a severity finding here, not a frequency one.* 2 documents
of 106 is not a rate; it matters because substitution inside a fence destroys a
directory tree.

**What is unbuilt.**

- The shared raw store (§2). Scoped, not built.
- `document.simhash` — deliberately NULL, see above. Do not "finish" it.

---

### Stage 3 · Triage — the hard gates

**What it does.** `collect/triage/gates.py`, six gates in a fixed order:

```
GATE_ORDER = (LANGUAGE, PURE_LINK, TOO_SHORT, NO_ENTITY, OUT_OF_WINDOW, KNOWN_BOT)
```

Plus a specificity *score* (`collect/triage/specificity.py`) which is a
backstop, not a filter.

**What it refuses to do, and why.**

- **A gate whose input is absent is `NotRun`, not a pass and not a fail.**
  `collect/triage/gates.py:124 class NotRun`. `wrong_language`, `pure_link_post`,
  `out_of_window` and `known_bot` all return `bool | NotRun`. "No bot list
  supplied" must not read as "the bot check passed."
- **A triage verdict is not a property of the document.** It is a property of
  *(document, population)*. See below — this is the most important thing in the
  stage.
- **The specificity composite may not compare across channels. Ever.**

**What it measured.**

*The population problem.* Same 1,297 documents, same code, only the surfaces
differ:

| population | surfaces | survival | entity gate drops |
|---|---|---|---|
| hand-written, 11 seeded models | 59 | 53.4% | 552 |
| registry union | 1,337 | 83.1% | 105 |

**385 documents — 29.7% of the corpus — change verdict on the alias population
alone**, with nothing about any document different.

*Population:* 1,297 distinct Reddit posts from 120 raw payloads in
`_substitution_slice/`, retrieved 2026-08-17. **Every post was retrieved by a
query containing model names**, so the corpus is pre-filtered for exactly what
the entity gate tests. Neither survival figure calibrates anything; two of six
gates never ran; and the 83.1% has since moved twice (to 78.0%, §Harvest).

`SurfacePopulation.fingerprint` exists because of this number. **Two runs at the
same `pipeline_version` can legitimately disagree**, because this gate's answer
changes when the registry grows without a line of code changing — so
`pipeline_version` cannot substitute for the fingerprint.

It also settled that the *declared* surface list is not redundant: 27
hand-written surfaces are reachable by no derivation (`flash 2.5`, `r1`,
`mistral large 3`), and a registry-only population rejects 39 documents naming
`deepseek r1`.

*The specificity floor removes 7.7%, not "the overwhelming majority of junk."*
Over 285 documents (174 GitHub, 111 blogs, re-scored from the raw store
2026-08-17, under the 59 hand-written surfaces loaded that day):

| | github | blogs | both |
|---|---|---|---|
| n | 174 | 111 | 285 |
| floor clear rate | **98.9%** | **82.0%** | **92.3%** |
| `names_version` | 48.3% | **6.3%** | 31.9% |
| `has_error_strings` | 42.0% | **3.6%** | 27.0% |
| `has_code` | 91.4% | 54.1% | 76.8% |
| mean composite | 0.527 | 0.286 | — |

So the floor is a **backstop, not a filter**, and if survival is to reach 10–15%
the hard gates have to do nearly all of it — which is why the hard gates were
built next. The cross-channel ban was ruled from that split:
`has_error_strings` and `names_version` are 0.45 of the weight and both are
largely a proxy for *medium*, so a cross-channel sort by specificity is a sort by
"is this GitHub" with extra steps — and it would demote **the only
positive-evidence channel.**

⚠ **The 7.7% is not reproducible.** The floor takes `version_aliases` as a
parameter, so the same documents give **3.8%** under those 59 surfaces and
**0.8%** under the 1,337-surface registry union — a factor of four, identical
documents. **That raw store no longer exists on any machine.** It remains the
only calibration this stage has, which is the reason to state its parameter
rather than quietly retire it.

**What is unbuilt, and this one is load-bearing.**

`document.triage_verdict` is **NULL on all 6,502 rows**. The gates have never
written their verdict to the database. `document.status` carries `kept` on 6,302
and `filtered` on 200, which is a different and coarser thing.

The specificity columns *have* been written since the last document described
them, and this is the kind of drift you must check rather than read:

```
document.has_numbers      True 2,341   False 2,918   NULL 1,243
document.has_conditions   True   414   False 4,845   NULL 1,243
```

`docs/measurements/the-reweight-stopped-at-step-two.md` says these were written
on "7 of 2980 documents". **That was true when written and is not true now** —
5,259 of 6,502 carry them. This changes the weighting story in §6 and I have
re-derived it there rather than quoting the doc.

---

### Stage 4 · Extract — the first of exactly two LLM stages

**What it does.** `judge/extract/` is handed a flattened thread and proposes
claims: a model reference, a capability key, conditions, a polarity, and a
**verbatim quote**. `judge/extract/verify.py:182 def verify` then checks that
quote by exact substring match against the text the extractor was given.

**What it refuses to do, and why.** This stage is where the project's central
guarantee lives, so the refusals are the design.

- **No claim without a verbatim quote**, and **the verification is plain Python —
  never a model checking a model.** Today: `claim.quote_verified` is `true` on
  **211 of 211** rows.
- **An LLM may propose; it may never decide.** Only `judge/extract/` and
  `judge/ask/` may call a model. No model participates in counting, weighting,
  gating, ranking, filtering or phrase assembly.
- **Code-only extraction was proposed and refused, 2026-08-18**, and you should
  read the reason before proposing it, because it is not a cost question — the
  whole corpus extracts for **$1.84** (887 threads at the measured $0.00208
  each). It was refused because **rule 1 works precisely because the proposer and
  the checker are different things.** If code extracts, code picks the quote and
  code verifies its own pick: the check passes by construction, and
  `quote_verified` becomes a guarantee that looks like one and is not.

  The supporting evidence is our own: a pure-code matcher hit `free` inside
  *"freeze"* and `fusion` inside *"confusion"* on the easiest subtask in the
  pipeline — exact matching against a known list — and was invisible on an AI
  corpus until it ran on movie posts. If code needs a boundary map and a control
  experiment to decide whether a four-character string is a model name, *"is this
  person complaining or joking, about which capability, under what condition"* is
  not the smaller problem.

  The alternative was weighed, not dismissed: a code-only board is possible as
  *high precision, low recall* — publish only unambiguously-phrased claims,
  discard the rest unread, **and say so on every page.** What it costs is most of
  the evidence, and the saying-so is not optional.

- **`speaking` is required**, and its evidence is asymmetric on purpose.
  `own-experience` is corroborated (8 of 8 by one labeller, 4 of 5 where both
  answered); `vendor-about-own-product` has **one reader on four rows from one
  announcement thread**; `relayed-from-elsewhere` was used once. So the field is
  built on the stronger half and enforces the weaker one — deliberately, because
  `vendor-about-own-product` is the value that changes a weight sixfold and is
  the value with one reader.

  Today: own-experience 167, relayed-from-elsewhere 30,
  vendor-about-own-product 11, NULL 3.

**What it measured.**

*Extraction cost.* 2,010 tokens in / 589 out, **$0.00208 per thread**. ⚠ **n = 3
calls against ONE thread**, E2's first live run. The old estimate agreed within
13% *for the wrong reason* — two errors in opposite directions partly cancelled —
so the agreement validates nothing. No artifact of that run is in the tree; it
ran against a disposable local instance on purpose.

*The first real verification evidence.* 8 proposed / 8 verified / 0 rejected,
after two schema defects were fixed — the first evidence that the offset map and
the flattener agree with a real model.

*Quote fabrication is real and was mis-stated once.* On the model-only sweep,
**34 of 255 quotes were fabricated or paraphrased** — reported initially as 68,
which conflated two distinct verification failures. Separating the two causes is
open (§10).

**What is unbuilt.**

- **`golden_label` has 0 rows.** Round 1's claim-row figure was **withdrawn, not
  superseded** (0.149 — three of its four disagreements were quotes from a
  vendor-authored root and no row carried the author, so the labels were evidence
  about the pool rather than about the readers). Round 2: claim rows n=5, document
  rows n=29, and **0 of 7 disagreements was about what the text says** — every one
  was the option set. Round 2 is **not** a trend against round 1: round 1 was one
  question with 4 options (4 cells), round 2 two questions with 3 and 4 (12
  cells), and more categories cost agreement at small n before they buy any.
  **Round 3 is unlabelled**, and it is what would measure `has_repro_steps` —
  which is why tier A is capped (§6).
- `capability_candidate` has 0 rows. Zero new capabilities have been proposed,
  and that cuts two ways: it is either evidence the 12-key vocabulary is adequate,
  or evidence the prompt anchored on the key list it was shown. Re-running the
  classification with the key list withheld (~26 cents) is what separates those.

---

### Stage 5 · Weight — pure code, seven factors

**What it does.** `judge/vet/weight.py:526 def compute` prices one claim as a
**product of seven factors, each ≤ 1**:

```
w = f_evidence     tier: A 1.00 · B 0.65 · C 0.35 · D 0.12 · E 0.04 · F 0.02
  · f_platform     github .95 · blog .90 · reddit .85
  · f_specificity  numbers · conditions · repro steps  (version_named removed 2026-08-21)
  · f_relevance    central 1.0 · passing 0.4
  · f_recency      exp(-ln2 · age_days / half_life)
  · f_launch       0.45 + 0.55 · min(1, days_since_release / 21), FROZEN at extraction
  · f_fuzziness    snapshot 1.0 · version 0.6 · family 0.3
```

Verified in code — `w_final` is still a plain product of those seven.

The tier is keyed on three stored fields, re-keyed 2026-08-30 from `speaking`
alone (`contract/harvest.yaml: evidence_tier_rules`):

```
own-experience  + repro steps + numbers   ->  B
own-experience  + one of the two          ->  C
own-experience  + neither                 ->  D
relayed-from-elsewhere                    ->  E   (no rungs)
vendor-about-own-product                  ->  F   (no rungs)
```

**What it refuses to do, and why.**

- **A weighting input may not have a silent default.** `compute()` raises
  `UnsuppliedWeightInput` and names which module should have supplied the value.
  This is why the whole class of defect below was findable at all.
- **`None` was a silent default until 2026-08-30**, and the consequence was
  total: the check tested `value is UNSUPPLIED`, and a literal `None` walked past
  it into `specificity_factor`, which read it as falsy. So **every claim the
  pipeline had ever written was weighted as though `has_numbers` and
  `has_conditions` were both False.** The check now refuses `None` on all ten
  inputs — but not on `release_date`, where `None` genuinely means "no release
  date known" and returns `f_launch = 1.0`.
- **`f_launch` is frozen into `claim_weight` at extraction, never recomputed.**
  If it were recomputed at aggregation then once a model turned 22 days old every
  claim — *including the day-three hype post* — would snap to 1.0 and the
  discount would delete itself. A launch-week claim stays discounted forever.
  What legitimately strengthens over time is the *cell*.
- **`has_numbers` is falsified by code before it may promote.**
  `claim.has_numbers` is the extractor's self-report; `document.has_numbers` is
  the same question answered by `collect/triage/`. It **falsifies without
  confirming**: a document with no numbers cannot contain a quote with one, while
  a document that has some says nothing about *this* quote. Where the column is
  NULL the promotion is **withheld and counted**, never silently taken or
  silently refused.
- **The vendor rung is flat, and that is the guard.** A launch post carries
  figures by construction, so if `has_numbers` reached the vendor rung an
  announcement would outweigh the engineers disagreeing with it. It does not.
- **`evidence_tier_for` returns two values because rule 6 asks for two** —
  `tier`, and `unconfirmed`: which promotion signals were *absent* rather than
  false. A single return value would make those indistinguishable.

**What it measured.**

The staged factor averages, on the top cell:

| factor | staged avg |
|---|---|
| `f_evidence` (tier) | **0.10** |
| `f_specificity` | **0.43** |
| `f_fuzziness` | 0.53 |
| `f_recency` | 0.74 |
| `f_platform` | 0.86 |
| `f_relevance` | 0.95 |
| `f_launch` | 0.99 |
| **`w_final`** | **~0.020 / voice** |

*The ceilings, and both of them moved without anybody voting for it:*

```
MAX_SPECIFICITY        0.58    was 1.00 until Option 1 landed 2026-08-30
MAX_POSSIBLE_WEIGHT    0.551   was 0.95  — and it prices tier A, which is unreachable
MAX_REACHABLE_WEIGHT   0.358   tier B — the ceiling a real claim can reach
```

`f_specificity` lost two of its four signals when the evidence tier took over
pricing them, which took the factor's **range** from 1.00 to 0.58 — and a factor
in a product carries its range into the ceiling. So `n_eff >= 3.0` needed 3.16
claims at 0.95 and needs 5.44 at 0.551: `judge/curate/gate.py`'s docstring
"four or more" became **"six or more"** as a *side effect*. Nothing compensates
for it, and lowering `N_EFF_MINIMUM` to restore the old effective bar would be a
threshold change dressed as bookkeeping.

And **0.95 was already a figure about an unreachable rung** — a rule-7 instance
that survived years of inspection because its arithmetic was correct. The number
to quote when asking what a cell needs is `3.0 / 0.358` = **8.38, so nine whole voices**.

**What is unbuilt.**

`judge/vet/repro.py:36 def has_repro_steps` — the code-counted replacement for
the extractor's boolean — **exists and has zero callers.** Verified: every other
`has_repro_steps` in the tree is the extractor's field on `claim`. It is decision
4 of the four coupled rulings (§10), and `claim.has_repro_steps` is `False` on
**all 211** rows, which is why the B rung is unreachable.

---

### Stage 6 · Gate — counting voices

**What it does.** `judge/curate/gate.py`. Pure code, no model, and no score is
displayed.

```
N_EFF_MINIMUM               = 3.0
PLATFORM_MINIMUM            = 2
AUTHOR_CAP_BELOW_FIVE_VOICES = 0.50
AUTHOR_CAP_AT_FIVE_PLUS      = 0.20
VOICES_FOR_TIGHTER_CAP       = 5
```

`count()` sums per-voice maxima into `n_eff`; `check_gate()` applies the
thresholds; `classify()` assigns `published` / `contested` / `insufficient`.

**What it refuses to do, and why.**

- **The author cap is conditional, deliberately.** It exists to stop one loud
  account carrying a cell. Below five voices that risk is already bounded by the
  two-platform rule, and a flat 20% cap would need five exactly-equal authors —
  real weights are never equal, so it would only ever permit cells you rarely
  have.
- **The gate does not import the weighting's ceilings**, on purpose: this module
  holds thresholds and `weight.py` holds factors, and a gate that computed its
  own ceiling would be a second description of the weighting that can disagree
  with the first.
- **An unweighted claim is excluded, not counted as zero.** There is a test named
  exactly that.

**What it measured.** See §6 — this is where the whole project currently sits.

**What is unbuilt.** A separate `voices >= 3` condition is dead text in the
docstring. It is documented as dead rather than deleted, because the numbers it
rested on moved and the paragraph explaining that is more useful than its
absence.

---

### Stage 7 · Publish — pages and phrases

**What it does.** `judge/curate/phrases.py` assembles a **phrase** from counts;
`judge/pages/` renders model, capability, coverage, roster and changelog pages.
The frontend is React + Vite in `web/`.

**What it refuses to do, and why.**

- **No synthesised number reaches a page.** Every figure displayed is *counted*
  (people, quotes, days) or *measured* (price, tokens). **There is no 0–100
  capability figure anywhere in the schema or the UI.** Consensus is a phrase
  assembled from counts, never a score.
- **The seven-factor product is never on the page surface.** It lives behind a
  drill-down, because a synthetic product is exactly the kind of number this
  board does not display.
- **Silence renders differently from criticism.** Verified in code:

```
judge/curate/phrases.py:115    "Nobody has publicly discussed {what}"
judge/curate/phrases.py:127    "{who} mentioned {what} — not yet corroborated"
```

**What it measured.** As of today: 105 cells, all `insufficient`, all carrying a
consensus phrase; 39 of 342 models have any cell; the other 303 model pages
render 12 unreported capabilities and nothing else.

**What is unbuilt.** `reported_context` has 0 rows — FR-31's `reported_low`
threshold has never been seeded, which matters because it is a **hard filter**: a
wrong `cell` renders as a phrase somebody can argue with, a wrong `reported_low`
renders as an *absence*, and nobody audits a model that was never in the list.

---

## 4 · Absent from the pipeline: the answer path

`judge/ask/` is the second and only other LLM stage, and it is **task
understanding only**. It reads a materialised view and never touches the
pipeline. `answer` has 1 row. The Ask box is parked; `fixtures/hand_cells.yaml`
was deleted when it was.

---

## 5 · The eight rules, by what each prevents

`CLAUDE.md` states the rules. This section is about what each one *stops*,
because that is what tells you whether your change violates one.

**Rules 6 and 7 are out of order below, and deliberately.** They do most of the
work in this codebase and they each get a full subsection at the end, so the six
that state quickly come first and the two you will actually trip over come last.

**Rule 1 — no claim without a verbatim quote.** Prevents a plausible-sounding
claim nobody said. The check is plain Python substring matching against the text
the extractor was given. What makes it work is that the proposer and the checker
are different things (§Extract).

**Rule 2 — exactly two stages may call a model; an LLM may propose, never
decide.** Prevents the failure where the system's output is the model's opinion
wearing the pipeline's authority. It is also why `judge/vet/repro.py` exists at
all: `has_repro_steps` feeding a weight is a model's self-assessment feeding a
number, and the fix is to code-count it.

**Rule 3 — no synthesised number reaches a page.** Prevents a fabricated
precision. A 0–100 "capability score" would be a number nobody measured, and
readers would treat it as one somebody did.

**Rule 4 — silence is not criticism.** Prevents the worst possible
misrepresentation: "nobody has discussed this" rendering identically to
"engineers report problems". Absence of evidence must never read as evidence of
absence of capability.

**Rule 5 — config in versioned YAML, not code.** Prevents a threshold change
being invisible in a diff. Thresholds, weights, half-lives, the capability list,
alias variants and filter rules all live in `contract/`.

**Rule 8 — an unmeasured check ships as a weight, not a gate.** Prevents an
absence *we caused* reading as one we *found*. A wrong gate's false positives are
invisible — it drops the document. A wrong weight keeps the document and
mis-ranks it visibly, which is the evidence that decides whether it should ever
become a gate. **The direction is one-way**: weight first, gate later on
evidence, never the reverse.

No test can tell a measured check from an unmeasured one, because the measurement
lives in a document. So this is a **reviewer question**: *what population was
this filter's error rate measured on, and did the filter, or anything upstream of
it, choose that population?* The upstream clause catches the trap — "no, I used
the whole corpus" is not an answer when the corpus is an earlier filter's output.

Settled twice (`speaking` on `ModelRef`, and the 8★ behaviour check), which is
what makes it a rule rather than a precedent. It is also why tier A is capped at
B today: `has_repro_steps` is unmeasured, and round 3 of the golden set is what
would measure it.

---

### Rule 6 — a missing value is never silently converted into a definite one

This rule and rule 7 do most of the work in this codebase. Learn these two and
you will avoid the majority of the expensive defects.

**What it prevents:** the class of defect that *looks like a considered answer*.
An unpublished capability flag is not `false`. A NULL price is not free and not
the cheapest tier. An unseeded `reported_low` is not a threshold. A gate whose
input is absent has not passed.

Rule 4 is this rule's display side; this is the data side. **Both lanes have
broken it once:**

- `judge/`'s hard filter read an absent `supports_tools` as "cannot", taking a
  candidate list **from 11 models to 1**.
- GitHub Search silently discards the qualifiers in a query, turning a
  capability-scoped search into a bare alias match.

Both surfaced as an absence with nothing on the page to disagree with, which is
what makes this class expensive.

**How it shows up in code you will read:**

```
collect/triage/gates.py:124   class NotRun          — a gate that could not run
judge/vet/weight.py           UnsuppliedWeightInput — refuses and names the gap
judge/vet/weight.py:~220      TierVerdict(tier, unconfirmed) — two values, on purpose
collect/rawstore_reader.py    three named outcomes, never a boolean
collect/registry/assertions.py  a check whose input is absent is SKIPPED AND NAMED
```

**The pattern to copy:** where a value is missing at the point it would have been
used, **say so** — a caveat the reader can act on, never a silent exclusion.

**And its own entry in `CLAUDE.md` has been wrong three times.** The
`assert_no_fixtures` paragraph said "Production asserts on startup that none are
present" for weeks; the first correction said the check was "called from the
loaders and from tests", also wrong, because the three apparent call sites in
`collect/` were a docstring and two comments; the second correction counted them
and said neither had a caller, which was true when written and stopped being true
the day issue #27 closed. **The lesson is not to write more carefully — all three
were written carefully. It is that a claim about wiring goes stale silently.**

That is live right now, and here is one you can verify in ten seconds:

> `judge/pipeline.py`'s `DocumentFacts` docstring says *"THIS CLASS HAS NO
> PRODUCTION CONSTRUCTOR. The only one in the repository is
> `tests/test_pipeline_db.py:190`."* **It is stale.** There is a production
> constructor at `judge/cli.py:229`, reached through
> `judge/cli.py:172 def _document_facts`, which has six non-test callers.
> Similarly `docs/proposals/for-engineer-2-e6-has-never-run-on-the-export-path.md`
> says `grep -n "text=" judge/cli.py` returns nothing; it now returns
> `judge/cli.py:265`, and commit `647d7e3` *"Wire E6"* is on `origin/main`.

Both were found by checking rather than reading, which is the whole point.

---

### Rule 7 — a figure travels with its denominator and where that came from

**What it prevents:** a **real value silently answering a question it was not
asked.** Rule 6 is a missing value becoming a definite one; this is its sibling.

This class **survives inspection**, which is what makes it expensive: a number
looks like evidence, and a spot-check confirms it. Three figures did it in one
fortnight:

- `"context window"` present in **96%** of returns, and `"went back to"` in
  **100%** — both measuring *collocation frequency* rather than a phrase
  operator.
- **52.7%** subject match — measuring the *retrieval that produced the corpus*.

Each was load-bearing in an argument before anyone checked what it counted.

**The check that catches it needs no suspicion:** ask what the denominator is and
where it came from. If the answer is not beside the figure, the figure is not yet
evidence. It applies to counts as much as to percentages — what those three
shared was an unstated population, not a form.

**It applies to claims about RISK, not only to figures**, and that form has no
number in it at all. *"Any branch older than the fix carries this defect"* is a
true statement about what COULD be wrong, and with no population attached it
reads as a statement about what IS. The population was **1 of 69 branches**, and
it was the one already being deleted. Same failure, same fix: name the
denominator, and the worry changes even though the conclusion does not. This is
the form that survives the rule as originally written — a reader checking "does
this figure carry its denominator" finds no figure and moves on.

**Worked examples you will meet:**

- **"3.4% capability-arm precision"** was an order of magnitude high. No slice of
  `harvest_run` produces it; the closest value is `avg(sieve_pass_rate) = 0.0036`
  = **0.36%**. And the pooled figure is the one to quote — the mean of per-run
  ratios weights a 2-candidate run like a 200-candidate one, which is the same
  mean-of-ratios error the extraction cost model already made once across corpora
  with a 240× median spread.
- **"23×"** worse became **~3×** on the same comparison, corrected.
- **"103 seated models"** is alias *rows*. The model count is **40** — and 41 is
  right for "models with a curated alias row", 40 for "models a sweep will search
  for", 103 for "valid alias rows". Three numbers, three questions.
- **`substitution_kept: 0`** was **unknown, not zero.** The probe took
  `entry.terms.topic[0]` — one topic term — whose first term carries no
  `{alias_b}`, so all four model pairs rendered the same query and the run
  measured one query four times. **A zero from a harness nobody has shown can
  produce a one is indistinguishable from a broken harness.** Every measurement
  in `measurements.md` that reports a zero now states whether the instrument
  could have seen a one.
- **The ~23.8% E4 survival ceiling.** ⚠ **NOT VERIFIED.**
  `docs/proposals/extraction-budget.md` §3 lists it in a table headed *"three
  measured figures"*. It is not a third measurement — it is a projection, and
  `control-and-reshape.md` §6 marks it *"to be re-measured"*. One document
  carries it as stale and another quotes it as current, and its derivation could
  not be reconstructed from either.

---

## 6 · Why nothing publishes, in full arithmetic

This is the current state of the project. It takes three steps, and each one
kills a different hypothesis. **Measured four times, by two people, on two
corpora, converging on the same numbers.**

Today's figures, from the live database:

```
cells                                       105
cells `published`                             0
cells failing n_eff < 3.0                   105   (all of them)
cells with >= 2 platforms                    12
cells below PLATFORM_MINIMUM                 93
best cell   claude-sonnet-5 · reasoning.multistep
            n_eff 0.14091666 · 7 voices · 2 platforms
mean n_eff across all 105 cells         0.023971
```

### Step 1 — platform is not the blocker

The earlier framing was "84 of 96 cells are single-platform". **That is stale.**
Twelve cells now clear `PLATFORM_MINIMUM = 2`, including the best one and the
next four. The closest cell —
`claude-opus-4.6 · code.generation` — has **6 voices across 2 platforms** and
fails on weight alone: **0.0900 against 3.0.** At its own per-voice weight of
0.0150 it needs roughly **200 voices**.

So it is not short of people and it is not short of platforms.

### Step 2 — tier A is unreachable by construction, and the fix that landed moves nothing

`TIER_WEIGHT` defines six tiers. `speaking` has three values. Before 2026-08-30
the contract mapped them straight to D, E and F, so **A, B and C were unreachable
no matter how good the evidence** — measured on 197 claims across three
platforms, **0 at A, B or C**:

```
             tier D   tier E   tier F      A/B/C
reddit         134       16       10          0
blog            16        3        1          0
github           7       10        0          0
```

The 17 GitHub claims — from the channel tier A's own gloss names, *"or a GitHub
repro"* — came out **7 tier D and 10 tier E**, worse than the corpus average. Not
one reached A. **And that is not a finding about the extractor.** It emitted
exactly what its schema allows. It is a finding about the mapping.

The cause: `TIER_WEIGHT`'s glosses describe **reproducibility** (*"published
harness/prompts, N runs, numbers"*) while the mapping keyed on `speaking`, which
is **whose claim it is**. Two different axes. Consequence: an engineer who
publishes a harness, three runs and numbers, and an engineer who writes *"opus
feels slow"*, are both `own-experience` and therefore both tier D — an 8.3× gloss
difference collapsed to nothing by the key.

**The re-key landed on 2026-08-30** and added the B and C rungs (§Weight). Its
result was a **bound, computed before the rows were available**: `n_eff` is a sum
of per-voice maxima and every claim's `f_evidence` rises by at most
`0.65 / 0.12 = 5.4167`, so `n_eff_after ≤ 5.4167 × n_eff_before` for every cell
whatever the booleans say.

```
best cell   0.1409  ->  ceiling at tier B  0.7632   25.4% of the gate
                    ->  ceiling at tier A  1.1742   39.1% of the gate
```

**Tier A would not have published it either.** Worth stating plainly, because the
rule-8 argument for capping at B invites *"we are leaving publication on the
table to be careful"* — and we are not. The rung we refused does not reach the bar
on this corpus.

Then it was measured, and it moved **zero claims**:

```
197 read   194 written   3 refused (speaking NULL)
tier moves      D->D 154    E->E 29    F->F 11
promotions           0
```

Because both signals the ladder reads are dead in the data. **Today, on 211
claims:**

```
claim.has_repro_steps    False on 211 of 211    no claim in the corpus has any
claim.has_numbers        True on 24
```

The B rung needs both; the C rung needs one. `has_repro_steps` supplies neither
because it is false everywhere — and `judge/vet/repro.py`, the code-counted
replacement, **has no callers.** So the ladder is correct and the corpus cannot
reach it.

> **One thing has changed since those documents were written, and it matters.**
> They report `document.has_numbers` as NULL on 194 of 197, with the columns
> written on "7 of 2980 documents", making the `has_numbers` falsifier
> unavailable. **Triage has since run:** `document.has_numbers` is now non-NULL
> on 5,259 of 6,502 documents, and **175 of 211 claims** sit on a document that
> carries the facts. So the C rung's falsifier *is* now available for most of the
> corpus. The claims are still stored at `e5.1` and have not been re-priced, so
> **what the C rung would now do is unmeasured** — this is the first thing worth
> re-running, and it costs no model calls.

### Step 3 — and fixing the tier still leaves seven voices at 2.6

Walk every fix up the ladder on the best cell (7 voices, `n_eff` must reach 3.0):

| what you change | per-voice w | n_eff | publishes? |
|---|---|---|---|
| nothing (today) | 0.020 | **0.14** | no |
| tier D→A, still a product | ~0.17 | ~1.2 | no |
| + remove the version double-count | ~0.32 | **~2.2–2.6** | no |
| **geometric mean** `(∏f)^(1/7)` | ~0.57 | **~4.0** | **yes** |
| geometric mean + tier D→A | ~0.77 | ~5.4 | yes |

**Every fix that keeps the multiplicative form tops out at ~2.6** for the
best-corroborated cell in the entire dataset. That one row — **seven genuine
voices at ~2.6** — is the finding: the gap survives every fix on the table except
the two that change what "3.0" is measured against.

### Why it is the aggregation, and the case for the product first

The product is not a mistake and deserves to be argued against on its merits.
Multiplying independent filters is the correct way to say "all of these must
hold" — if each factor prices a genuinely separate reason to trust a claim less,
the product is right and the collapse to ~0.02 is the honest verdict on hedged,
single-platform, month-old forum prose. On that reading the fix is to lower the
bar, not to touch the form.

**The form breaks only where the factors are not independent, and two are not.**
`f_specificity` includes `version_named`, and `f_fuzziness` is *entirely*
model-version specificity (snapshot / version / family). Version-pinning is
multiplied in twice. Same shape one level up: the evidence tier prices "has
numbers / has a repro", and `f_specificity` prices `has_numbers` and
`has_repro_steps` **again** — 5.42× and 1.95×, **10.6× combined** on a claim
carrying both. De-duplicating is a bug fix on any reading; it is also a separate
ruling and has not been taken.

### And this is why more collection cannot fix it

There are ~1,505 unread threads costing about $2.14. **They cannot publish a
cell.** Not "probably will not" — the arithmetic does not depend on what they
say. Coverage would widen, the board would populate further, and `PUBLISHED`
would stay 0. Sharper still: **the entire GitHub corpus we can build (~137
documents) is smaller than one tier-D cell's requirement (138 voices).**

The decision is calibration. It wants ruling, not measuring.

---

## 7 · Every measurement that changed a decision

Consolidated, with denominators. Full working in `docs/engineer-1/measurements.md`
and `docs/measurements/`.

| # | figure | population | what it changed |
|---|---|---|---|
| 1 | **retrieval bias 58.1pp**; topicality bound 19.5pp; pipeline discrimination 0.4% | A 1,297 model-name-retrieved Reddit posts; B 1,925 posts / 26 subreddits × 75; C+D 750 control posts. Survival *within those subreddits*, 2026-08-18 | killed quoting survival from a search corpus — every published figure was ~2.5× too high; found the word-boundary defect and the routes ruling |
| 2 | **design effect 14.5**, predicted 1.5–3. Effective n **132**, not 1,925. CI ±2.1pp → **±7.9pp** | same as above; survival 15.4% (r/singularity) to 59.4% (r/LocalLLaMA) over 175 posts each | more pages buys nothing; more *subreddits* is the only thing that buys precision |
| 3 | **385 documents (29.7%) change verdict on the alias population alone** — 53.4% at 59 surfaces vs 83.1% at 1,337 | 1,297 Reddit posts, `_substitution_slice/`, 2026-08-17, all retrieved by model-name queries | `SurfacePopulation.fingerprint`; a verdict is a property of *(document, population)*, and `pipeline_version` cannot substitute |
| 4 | **specificity floor removes 7.7%**, not "the overwhelming majority" | 285 documents (174 GitHub, 111 blogs) re-scored 2026-08-17 under 59 hand-written surfaces. ⚠ not reproducible: 3.8% / 0.8% under different surface sets; that raw store is gone | floor is a backstop not a filter, so the hard gates were built next; and the cross-channel comparison was banned outright |
| 5 | **signal group: 102 of 207 terms never fired**; `truncat` alone 34.2%; per-entry median **0.39%** | 32,723 GitHub candidates re-sieved offline with the sieve's own matcher | signal, not topic, is the binding constraint on retrieval |
| 6 | **per-entry 0.39% GitHub vs 0.42% blogs**; **101 of 207 dead on both** | 119 blog documents, pre-registered | withdrew the per-platform-terms proposal (§8) |
| 7 | **MinHash beats simhash at every length**; simhash's margin at 400–800 tokens is **one bit of 64** | 79 ground-truth duplicate pairs + 951 stranger pairs from 3,767 Reddit documents, 2026-08-17. **No blog syndication in the corpus at all** | two-method design deleted; `document.simhash` stays NULL as a measured decision |
| 8 | **0 of 5 entities reached the flattener**; `°©®™` occurred zero times; box-drawing from **2 documents of 106** | A: 53 articles / 519,997 chars; B: 106 articles re-extracted with no network. 9 feeds, 2026-08-18 | per-platform flattening rules; and it *stopped* a second change — the `So` rule was not narrowed from a corpus of two |
| 9 | **tier distribution: 0 of 197 claims at A, B or C**; GitHub's 17 were 7×D + 10×E | 197 claims across three platforms, 2026-08-28 | the tier re-key (§6 step 2) |
| 10 | **calibration gap: n_eff must reach 3.0, real claims weigh ~0.015**; gate docstring assumes ~0.95. **30–60× apart** | staging, 199 claims / 96 cells, all insufficient; independently reproduced on 197 claims / 94 cells with the same top cell to the decimal | the four coupled rulings (§10) |
| 11 | **the re-key moves 0 claims**; `has_repro_steps` False on 197/197 | the corpus, not a sample, at `e5.1` | the reweight was rolled back inside its transaction; blocker moved to the document-facts columns |
| 12 | **ceilings moved without a vote:** MAX_SPECIFICITY 1.00→0.58, MAX_POSSIBLE_WEIGHT 0.95→0.551, so the gate went from "four or more" to "six or more"; MAX_REACHABLE 0.358 → **~9 voices** | derived from the weights, not typed | recorded rather than compensated, because moving `N_EFF_MINIMUM` back would be a ruling wearing bookkeeping's clothes |
| 13 | **extraction $0.00208/thread**, 2,010 in / 589 out; whole corpus **$1.84** | ⚠ **n = 3 calls against ONE thread.** Old estimate agreed within 13% for the wrong reason — two errors partly cancelled | settled that code-only extraction is not a cost question |
| 14 | **specificity weights select for relays: 4 of 5** | one thread, `t3_1u1b22l`, 195 comments, coverage 0.238 | see §8 — the artifact-density hypothesis, retracted |
| 15 | **model-only Reddit: signal 5.0% vs 0.4% under a recency listing — 12.5×** | 2,500 candidates vs 1,950, same subreddits, same day | model-only retrieval kept as a shape; see §8 for why it is not one answer |
| 16 | **model-name arm 3× WORSE than capability on GitHub** (0.134% vs 0.404% pooled) | capability arm 1,019 `harvest_run` rows / 44,848 candidates / 181 kept. ⚠ the model-name arm's 2,239 candidates left **no `harvest_run` row** and are carried as reported | corrected a "23×" claim; and the 3× is a signal-vocabulary result wearing a retrieval result's clothes |
| 17 | **baseline instability: 0.208% vs 0.417% pooled, four days apart** | 153 requests / 2,887 candidates (08-20) vs 866 / 41,961 (08-24), same instrument | bounds how much any single retrieval comparison can carry |
| 18 | **substitution_kept: 0 was UNKNOWN, not zero** → re-run: 0→2, 1→4 documents | 146 queries / 1,678 documents, then 168 / 1,297. ⚠ **not paired** — the first corpus is gone | every reported zero now states whether the instrument could have seen a one |
| 19 | **`user.type` catches 200 bot comments from 26 apps; 0 suffix/type disagreements** — and misses **7 automation accounts declared `type: User`** | 2,016 comments across 586 GitHub issues, 2026-08-31 | `is_bot` on `user.type` confirmed correct; the extra list proposed, not written (§10) |
| 20 | **the board renders 2 sentences on 1 model of 342** — measured 2026-08-21 | ⚠ **stale.** Today: 105 cells over 39 models, still 0 published | superseded by the live figures in §1 |

---

## 8 · Where a design was reversed by measurement

**Read this section before proposing anything.** Every item here is the obvious
idea, argued well, and killed by a number. You will otherwise propose one of them
in your first fortnight and be surprised.

### Per-platform signal terms — proposed, then withdrawn by its own pre-registered test

**The idea:** signal terms are prose-shaped and GitHub is not, so render them per
platform.

**Why it was good:** the vocabulary genuinely is better matched to prose —
16.25% vocabulary-wide on GitHub against 21.85% on blogs, 30.88% on long-form.

**What killed it:** the author pre-registered the threshold — *withdraw if
per-entry on prose comes back under 1%* — and ran it on 119 blog documents. It
came back at **0.42%**, against GitHub's 0.39%. **The per-entry rate is the same
on both platforms**, and it is the per-entry rate that determines retrieval.
Per-platform terms address the vocabulary-wide figure and not the one that
matters.

**What replaced it:** **101 of 207 terms fire on neither platform.** That is a
term-selection problem, it is platform-independent, and it is a larger lever.

The proposal is left in the tree with a withdrawal banner rather than deleted,
because a proposal argued and then refuted by its own pre-registered test is
worth more as a record than as an absence. **Copy this pattern.**

### The artifact-density hypothesis — retracted

**The idea:** `specificity_score` rewards numbers, code, error strings and
version names, so it selects the claims worth extracting.

**What killed it:** measured on one thread (`t3_1u1b22l`, 195 comments, coverage
0.238), the five comments the selector picks are **four relays out of five** —
and they are relays *because* of what scores. A model-card number, a link to the
announcement, a version string. Someone repeating a benchmark carries numbers and
a version and a URL; someone reporting their own experience carries an adjective.

The sharpest number: `oqocfjv`, the only first-hand capability observation in its
thread, **falls from rank 3 to rank 8 of 195 when the selector is *fixed*** — not
because anything about it changed, but because five competitors each gained +0.15
for a version token it does not carry.

**Why it generalises:** every one of the five components is a property of the
*artifact*, not of the writer's relationship to what they are describing. And the
two failures compound — the selector selects for what the extractor then
over-reads.

⚠ This is n=1 thread. It is strong evidence about *what the weights select* and
weak evidence about *rates*.

### Structural qualifiers — measured to zero

**The idea:** narrow GitHub retrieval with `is:issue`, `label:bug`, `repo:`,
`org:` rather than a capability token, so a capability nobody wrote a query for
is still reachable. This answers the circularity objection, which is why it was a
genuine third option and not a variant.

**First correction:** the claim that four of twelve queries already used it was
wrong. `contract/queries.yaml` has **no qualifier field**, and of 591 distinct
`query_key` values, 591 carry `type:` (hardcoded in `render_search`) and **zero**
carry `is:issue`, `label:`, `repo:` or `org:`. **No structural qualifier beyond
`type:issue` has ever been issued.** The mechanism exists and is unused.

**What killed it:** priced at **zero benefit and one request, at the depth we
read** — because `collect/adapters/github.py` sets `max_pages = 1`. Qualifiers
would begin to matter only if `max_pages` rose, and raising it is the more direct
way to get the same documents.

**And one of them is nearly the objection it was meant to answer:**
`label:bug` selects for complaints, which is a *stance* and not a capability — so
a corpus filtered that way makes positive evidence structurally unreachable,
which is rule 4 arriving at retrieval.

*Supporting fact worth keeping:* `org:` qualifiers do compose and union exactly —
`org:langchain-ai` 475 + `org:run-llama` 56, both together 531. Qualifiers are
honoured where boolean operators are not.

### Thread-subject inheritance — ruled against twice, on different evidence

**This is CLOSED, not pending**, and the two rulings do not stack. Recorded that
way because the second measurement made the rule look **better** on the axis it
was reopened for, and made the case against it stronger on three axes nobody had
measured. **A reader who finds only the first ruling will reopen it for exactly
the reason it was already reopened once.**

```
ruling 1   the rule's second condition fires on 60% of candidates, and what
           survives is announcement threads.          A QUALITY objection.
reopened   the recoverable population is far larger than the 21 measured —
           true, and measured at 104 with 86 voices, a 6.1x n_eff multiplier.
ruling 2   it fails the FIRST condition (population 0 on the one thread we
           hold), 72% of what it recovers carries no specificity signal at
           all, and 6.1x still lands at 1.247 against a threshold of 3.0.
           A CORRECTNESS objection, a PURPOSE objection, and an ARITHMETIC one.
```

Note what the arithmetic does here: even granting the reopening's own best number
in full, the answer is 1.247 against 3.0. That is §6 again — the aggregation
dominates everything upstream of it.

**The adjacent ruling, on family words**, went the same way and for a sharper
reason: of 133 blog claims resolving to no model, **80 contain no family word at
all.** `LLM` 15, `AI` 6, `model` 4, `agents` 4, `LLMs` 3, `"JetBrains' model"` 3.
**60% of unresolved claims are unreachable by any ruling about `FAMILY_WORDS`**,
because people wrote a category noun rather than a family. Only 26 of the 133 are
bare family mentions.

And a correction inside it worth copying: of the four instances cited as evidence
that the family exclusion was binding, one was agreed, one could not be sourced
at all (*"62.5% on the first blog run"* — no run reports it), one was 177 of 195
rather than 172, and the fourth was agreed but only 26 of its 133 were actually
family words. **The pattern was real and the evidence for it was weaker than it
looked.**

### Model-name harvest — three different answers on three platforms

The most instructive reversal, because it is not a reversal. It is one question
that has three answers, and any single-platform result presented as "the answer"
is wrong.

| platform | model-name retrieval vs the alternative | verdict |
|---|---|---|
| **Reddit** | signal fires **5.0%** vs **0.4%** under a recency listing — 12.5×; topic 8× | **worth keeping as a shape** |
| **GitHub** | **3× WORSE** than capability queries on precision (0.134% vs 0.404% pooled) | capability queries win |
| **Blogs** | per-entry signal 0.42%, unfiltered, so the fairer test of recall | neither arm tested |

*Populations:* Reddit — 2,500 candidates vs 1,950, same subreddits, same day.
GitHub — capability arm 1,019 `harvest_run` rows / 44,848 candidates / 181 kept;
⚠ the model-name arm left **no `harvest_run` row** and its 2,239 candidates are
carried as reported, not verifiable. Blogs — 119 documents.

**What the author would not do on this evidence:** replace capability queries with
model-only queries (a coverage decision needing the same measurement on GitHub
and blogs), or wire a classification stage (a third model-calling stage, and
rule 2 permits two).

And the honest reading of the Reddit result: 5.0% is still the smallest of the
three sieve groups by a factor of six. **The sieve's signal vocabulary identifies
a small fraction of the capability reports a reader finds.** What the retrieval
shape changes is the size of the pool the vocabulary is failing to catch.

---

## 9 · The defect shapes

Roughly forty defects in this project reduce to a handful of shapes. **The shapes
transfer where the instances do not.** Canonical catalogue:
`tests/conftest.py` (module docstring) and `docs/engineer-1/defect-shapes.md`.

**The single sentence underneath almost all of them:** what each cost was not a
wrong answer but a **missing** one — rule 6's expensive case, where the defect
surfaces as an absence with nothing to disagree with.

### The shapes

| | shape |
|---|---|
| 1 | **The check that cannot fail.** A test asserted `"specificity_score" in message` — the *mention*, not the claim. It passes whether or not the scorer exists. When the scorer landed the refusal went on asserting something false and 878 tests stayed green |
| 2 | **The guard with no caller.** `assert_no_fixtures` had none for weeks. The three apparent call sites were a docstring and two comments. **Live instance today:** `judge/vet/repro.py:36 def has_repro_steps` has zero callers |
| 2a | **The refusal that outlived its premise.** An assertion that ran, and checked something that had stopped being true |
| 3 | **The guard in the wrong place in the sequence.** A test for the exact YAML defect that killed CI ran at step 5, inside `pytest` — after install, after the database. Correct, present, and three steps too late. **A guard downstream of the thing it protects reports on a corpse** |
| 4 | **The guard that enumerates attributes.** It covers the attributes somebody thought of. Write down what it omits |
| 5 | **The name that answers a different question.** `columns()` returns columns and compares columns; the inference that it covered *tables* was never in the code, and the name is what made the inference feel checked |
| 5a | **The match that ignored word boundaries, twice.** `free` in "freeze", `fusion` in "confusion", `saba` in "wa[s a ba]d" |
| 5b | **The literal inside SQL, invisible to a search for the column** |
| 6 | **The absent value that became a definite one.** Rule 6 |
| 7 | **The real value answering a question it was not asked.** Rule 7 |
| 8 | **The input that silently emptied.** A check scoped to one file reported clean; widened to the tree, the regex stopped matching and printed ONE file where there were two — which looked exactly like a pass. Caught because a line of *output* was missing, not because anything failed |
| 9 | **The test's relationship to a variable.** Byte equality between two flatteners passed on 2,481 characters and 20 segments and did not notice their `document_id`s used different conventions — because `document_id` was an **input the test supplied to both sides**. Inverse: two tests passed on a laptop and failed in CI with `RAPIDAPI_HOST is not set`, because the constructor read a setting the tests supplied to *neither* |

### The habits, in the order they are cheapest

1. Where a callee's docstring states a precondition, **the precondition is a test case.**
2. **Assert the state of the world, not the wording that describes it.**
3. **Break it on purpose and watch the test fail.** A test that has never failed has not been tested.
4. A check that iterates **must count what it iterated over**, and something must assert the count.
5. Where two components must agree about a value, **do not let the test supply it to both.**
6. **Run the suite without your `.env`.** The cheapest audit there is.
7. **Ask where a guard runs**, not only whether it passes.
8. A guard that enumerates attributes covers what somebody thought of — **write down what it omits.**
9. A helper **named for what it returns** is read as a statement about what it covers.
10. **An import chain is no evidence of a call path.** Count the rows.
11. **Name the question before choosing the tool**, and say which question you answered.
12. **A containment match is a boundary match's false positive.** `\b` both ends — and ask whether any surface in the list is a word.
13. **Grep the SQL too.** A column written as a literal inside a statement answers no search for the assignment.
14. **`grep "<name>"` reads as presence. `grep "def <name>"` is the check.** A bare substring matches any longer identifier — `_local_part` hits `def test_local_part` — so an absent symbol returns a line and looks defined.
15. **A description is not a change.** ~20 measurement documents against ~10 code changes in one session, and every change that landed had a failing test to attach to. **If the failing test cannot be written, the defect is not yet understood well enough to fix.**

### The two that will happen to you

**A clean merge is not a working one.** 304 commits merged, **one** textual
conflict, **two** defects the merge introduced with no conflict marker — and the
diff, the import and `ruff` all passed.

> **A dataclass field list and a Protocol body are the same shape to `git`.**
> `main` added six fields to `DocumentFacts`; the branch rewrote the adjacent
> defaults. The merge kept the branch's block wholesale — so `DocumentFacts`
> **lost six fields that `vet.reject.check()` reads** — and put `main`'s copy of
> those same lines **inside `SurfaceResolver(Protocol)`**, after its `__call__`. A
> `runtime_checkable` Protocol with data members stops matching a plain callable,
> so `isinstance(resolver, SurfaceResolver)` silently went False. Both classes
> still parsed. Both modules still imported. Every name still resolved.

The transferable pair:

- **After a merge, run the suite before believing the merge.** "No conflicts" is
  a statement about text, not about behaviour.
- **When a tool refuses, the refusal is evidence.** `git merge` aborting on 21
  untracked files was the only thing that enforced the ordering — nothing we
  built checked for it. Read the refusal; do not force past it. Same class of
  signal as `compute()` raising `UnsuppliedWeightInput`.

**Reported as done, and not on the remote.** The dominant failure of one
fortnight was **reporting a working tree as a repository** — a claim true on one
machine, at one moment, published as a property of the project. The checks that
fix it:

```
git ls-tree -r origin/main --name-only <dir>     module inventory
git show origin/main:<path>                       every quoted line
git grep -n <symbol> origin/main -- <dir>         call sites
git log --oneline origin/main -- <path>           whether it landed
```

Its close relative, and this one *will* bite you: **`-k "not _db"` let 28 fixed
sites read as all of them.** Making `speaking` required broke 28 construction
sites; the author fixed 28, and every local run excluded every database test
because the remote Postgres was unreachable. CI has a database and found three
more. **An exclusion that makes a suite green is a smaller suite, not a passing
one** — and the green is indistinguishable from the real thing at the summary
line. **Say which tests did not run, every time you quote a total.**

---

## 10 · What is open, and who owns it

| what | state | owner |
|---|---|---|
| **The four coupled rulings** (below) | proposed, measured twice, **not ruled** | both engineers jointly — this is the one thing standing between the board and anything publishing |
| **The scheduler's three questions** | raised 2026-08-31, not resolved. Build is complete: `collect ops run` at `collect/cli.py:156`, 2 runs to date (both by hand, both 2026-08-20), 0 blockers | needs a team answer, not a commit |
| **The `KNOWN_BOT` list** | 7 accounts identified; list **proposed, not written**, because `contract/` is shared and what the list keys on is a ruling with a false-positive cost measured in dropped people | proposed to E2 |
| **The dated baseline sweep** | scoped and costed 2026-08-24; **nothing swept, nothing seated.** 40 models / 177 variants via `seated_variants(conn)` | E1; the branch you are on (`fix/baseline-staleness-within-a-version`) is about baseline staleness |
| **Golden set rounds** | `golden_label` = **0 rows**. Round 1's claim figure withdrawn; round 2 n=5 claim rows with 0 of 7 disagreements about the text; **round 3 unlabelled** | blocks measuring `has_repro_steps`, which caps the tier at B |
| **The `content_hash` residue** | **246 of 1,763** rows still point at pre-extracted prose. The invariant holds on all 1,763 and cannot see it | E1 |
| **Separating the two verification failure causes** | one counter conflates fabrication with paraphrase — reported as 68, actually 34 of 255 | E2, free to fix |
| **Shared raw store** | scoped, not built. `RawStoreReader`'s outcomes have never run against anything real | joint |
| **`document.triage_verdict`** | NULL on all 6,502 rows | E1 |
| **`reported_context`** | 0 rows. FR-31's `reported_low` unseeded, and it is a hard filter | E2 |

### The four coupled rulings

**Rule them together — fixing any one alone still publishes zero.** The tier fix
alone lands the top cell at ~2.6; the aggregation fix alone rides a fake tier.

| # | decision | recommended | state |
|---|---|---|---|
| 1 | **Aggregation form** — product · geometric mean · de-double-count | geometric mean **and** de-double-count | **not taken.** `w_final` is still a product of 7 |
| 2 | **The bar** (`N_EFF_MINIMUM`) | re-set deliberately, in voices, against the new scale | **not taken.** Still 3.0, and its meaning moved when the ceiling fell to 0.551 |
| 3 | **Tier mapping** — leave · re-key to reachable B · reach A | re-key to B on code-counted signals | **LANDED 2026-08-30.** Moved zero claims (§6) |
| 4 | **`has_repro_steps`** — model boolean · code-count | code-count (`judge/vet/repro.py`) | **not taken.** The module exists with zero callers |

Implementation sequence once ruled, from the proposal: wire `repro.py` into
`f_specificity` and the tier → re-key `harvest.yaml` *(done)* → change the
aggregation → set `N_EFF_MINIMUM` → **bump `pipeline_version` and re-run the
rollup.** No re-extraction, no model calls, old rows stay diffable. That last
step is what `pipeline_version` is for.

Note that `judge reweight --from-version <v>` **forks** the claim table rather
than updating it, because the version is hashed into `claim_id_for`. `CellStore`
filters on `pipeline_version`, so `n_eff` aggregates one version instead of
handing each voice its best weight across two. And a tier ruling reaches stored
claims through `judge reweight`, **not** `rebuild-cells` — the latter
re-aggregates `claim_weight` and never re-prices it.

### The scheduler's three questions

1. **Which machine.** The chain has only ever run on a developer laptop, which
   **sleeps** — and a scheduled task on a sleeping machine does not produce a
   failure, it produces *nothing*, indistinguishable from a night with no work.
2. **Is a nightly Reddit sweep wanted at all**, before the terms ruling is
   revisited. `sweep-reddit` is the only wired stage that fetches. Its ruling
   (`reddit-via-rapidapi`, basis `internal-development-only`, 2026-08-18) was
   written for a narrower purpose, and whether a *measurement* sweep is covered
   by the same ruling as an *evidence* sweep was explicitly declined. Option (b)
   is newly available: `--only` lets the deterministic, free, local half run
   nightly without settling the harvesting question at all.
3. **Who reads the journal** — and this is the one that decides whether any of it
   is worth having.

On that third question, `collect/ops/chain.py` opens with the premise the module
exists to serve:

> Nine silent-failure defects were found in this lane in one fortnight, every one
> of them caught by a person reading a number that was wrong in a way that read
> as an answer. **Under cron there is no person.**

Everything the chain does about that is preparatory — it writes a stage's line
*before* doing the work, so a killed process leaves `started 03:00, never
finished`; it refuses rather than skipping, and every refusal names what it
starves; it reports absent counts rather than zeros. **Every one of those is a
message with no recipient until somebody reads it.** So the failure mode of
scheduling without answering question 3 is not that the chain breaks — it is that
**the chain works perfectly and nobody notices it stopped**, which is worse than
the hand-run state, because a hand-run has a person attached by construction.

Cost of one night at the current corpus: **~10 minutes, ~85 requests, no dollar
cost.** ⚠ Quota caveat: the gateway header reads 1,000,000 and the plan page says
500,000, and **which is our billed allowance has never been settled.** Either way
nightly is under 0.6%.

---

## 11 · How to run things

### Setup

```bash
cp .env.example .env          # then fill in credentials
pip install -e ".[dev]"
psql "$DATABASE_URL" -f contract/tables.sql
```

⚠ `README.md`'s "Getting started" is partly stale — it tells you to finish
`contract/seed_models.yaml` first. Don't. That file is a **build fixture**: the
shared database is fully polled (342 `model_version` rows, `provenance='polled'`,
**zero** `seed`). The file still exists because code references it (the seed
loader and `scripts/fetch_model.py`'s alias fallback) so a fresh local DB can be
seeded. `README.md` also says "the five rules"; there are eight, in `CLAUDE.md`.

### Frontend and backend

```bash
# 1 · API on :8000 — loads .env, which judge/app.py does not do for itself
python run-backend.py --reload

# 2 · frontend on :5173
cd web && npm install && npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api/*` to `127.0.0.1:8000`, so
there is no CORS to configure. Point it elsewhere with
`BACKEND_URL=http://host:port npm run dev`.

**Started any other way than `run-backend.py`, the database-backed pages answer
503**, because `judge/app.py` reads `os.environ` and does not load `.env` itself.

`python run-backend.py --staging` uses `STAGING_DATABASE_URL` and forces every
session read-only **at the server**.

### The chain and the sweeps

```bash
collect ops preflight                    # the four provenance assertions
collect ops run                          # the nightly chain
collect ops run --only score-documents   # one stage alone (built 2026-08-31)
collect ops run --no-network             # fixed 2026-08-31; was a no-op for sweep-reddit
collect ops sweep-github / sweep-reddit
collect assemble github / reddit
collect registry recompute-window        # the sole writer of in_window
collect triage population
```

**Every write command is gated.** `collect/cli.py:_gate` runs `preflight()`
before a command touches a database, and the guard is an **AST test over
`cli.py`**: any command opening a `transaction()` without `_gate` fails, and
read-only commands must be listed explicitly so an unclassified one fails rather
than running unguarded. A behavioural test over existing commands cannot see a
path that never had a check — which is exactly how `registry load-seed`, the
command that *creates* the fixture, had been opening a transaction without
gating.

### Extraction

```bash
judge extract                # the evidence pipeline (calls a model — costs money)
judge rebuild-cells          # re-aggregate claim_weight into cells. Does NOT re-price
judge reweight --from-version e5.1   # re-price stored claims, NO model call
```

`EXTRACTION_DAILY_BUDGET_USD` is in `.env`; spend is journalled to
`var/spend-ledger.jsonl`.

### The test suite — and read this before you believe a green run

**Measured on this machine, 2026-08-31, against the remote Postgres. These are
properties of this machine on this day, not of the repo.**

```
collected                                    2,788
FULL SUITE   (pytest -q, default config)     2,787 passed, 1 FAILED   161.4 s  (2:41)
non-DB set   (-k "not _db" -p no:randomly)   2,610 passed, 1 FAILED, 177 deselected   99.9 s
DB set       (-k "_db"     -p no:randomly)     177 passed, 2,611 deselected            61.6 s
```

⚠ **The suite takes 2 minutes 41 seconds, not 21 minutes, and nothing in the
non-DB set is slow.** If you were told 21 minutes, that is not reproducible here
— and the two halves sum to 161.4 s, exactly the full-suite time, so ordering and
`pytest-randomly` are not hiding anything either. The slowest single test is
`tests/test_dedupe.py::test_the_real_syndicated_set_becomes_one_cluster` at
**6.9 s**; the next is 2.9 s and most setup is ~0.4 s.

Two caveats on that, both of which could make your number differ from mine.
The DB half's 61.6 s is **177 tests each doing `DROP SCHEMA public CASCADE`
against a remote Postgres at `203.0.113.5`** — it is entirely
round-trip-bound, so on a worse link it will dominate, and this is the half
most likely to have produced a 21-minute run on a bad afternoon. And that host
was **unreachable for a whole session on 2026-08-30** (40 probes over 35
minutes, zero connections), which is the failure mode to suspect before you
suspect a slow test.

**Three things about the suite that are design, not accident:**

- **A missing database is a FAILURE, not a skip.** Six real defects survived a
  green suite because `tests/test_registry_load_db.py` skipped for want of a
  database, and **a skip reads as success**. It gets worse as the suite grows:
  247 passed with 9 silent skips looks healthier than the 139 that originally hid
  the bugs. `ALLOW_MISSING_TEST_DB=1` degrades it to a skip and says so loudly in
  the summary, because an override whose consequence is invisible becomes
  permanent the first time somebody puts it in a shell profile.
- **The suite destroys the database it points at.** `conn` runs
  `DROP SCHEMA public CASCADE` before every test. Three layers stop you pointing
  it at anything real. Do not remove them.
- **Never quote a total without saying what was deselected.** See shape 18 in
  §9.

### The one failing test, and why it is a perfect first exercise

```
FAILED tests/test_export_source.py::TestItLoadsTheRealExport
       ::test_the_handoff_export_loads_with_typed_spans
       assert 17 == 7   # "1 + 6 documents across two threads"
```

Reproduced on a **clean tree** (`git status --porcelain` empty), so it is not
yours. The test reads `_handoff/threads`, which is **gitignored** (`.gitignore`
lines 42 and 95) and untracked. It holds 12 thread files on this machine
producing 17 document ids; the test asserts 7.

It skips cleanly on a fresh clone (`if not directory.is_dir(): pytest.skip`).
**So your clone will be green here and this machine is red, and neither of those
is "the suite."**

It is simultaneously three documented shapes: a **hardcoded count against a local
instance** (a row count is a property of an instance, never of a commit); an
**invariant derived from the data in front of the author** and written as a
property rather than a description (shape #58b); and a reminder that the
gitignored corpora are not reproducible from a checkout.

---

## 12 · Answering "why does the board say nothing about this model?"

The whole point of §3. There are four answers, at four stages, and they are
distinguishable with four queries. Work down.

**Answer 1 — the model has no alias, so nothing ever searched for it.**
301 of 342 `model_version` rows have no `model_alias` row at all. A model with no
seated surface cannot be retrieved, so no document names it, so no claim resolves
to it. `registry.yaml` sets `declared_surfaces_only: true`, which is correct —
what is missing is the declaring.

```sql
select count(*) from model_alias a
  join model_version mv on mv.id = a.model_version_id
 where mv.canonical_id = '<model>';
```

Note the trap: the top model by cell count today, `qwen/qwen3.8-27b` with 9
cells, has **zero** aliases. So "no alias" does not imply "no cells" — claims can
reach a model through a surface the extractor read even where the sweep could not
search for it.

**Answer 2 — no claim resolved to it.** 303 of 342 models have no cell.

```sql
select count(*) from claim where model_version_id =
  (select id from model_version where canonical_id = '<model>');
```

If this is 0, look upstream: was there a document? Did it survive triage
(`document.status`)? Did the extractor resolve the surface, or did it land in the
133-of-140 unresolved pile — remembering that **60% of those are unreachable by
any family-word ruling**, because people wrote `LLM`, `AI`, `model`, `agents`.

**Answer 3 — the capability has no cell, and the page says so distinctly.** With
12 capabilities and 105 cells over 39 models, most (model, capability) pairs have
nothing. This is rule 4's case and the page must render *"Nobody has publicly
discussed X"* rather than anything resembling criticism
(`judge/curate/phrases.py:115`).

**Answer 4 — it has a cell, and the cell is `insufficient`.** This is the answer
for every cell that exists: **105 of 105.**

```sql
select capability_key, status, n_eff, independent_voices, platform_count
  from cell where model_version_id = (...) order by n_eff desc;
```

`n_eff` will be far below `N_EFF_MINIMUM = 3.0` — the maximum on the entire board
is **0.1409** and the mean is **0.0240**. Then §6 tells you why, and the short
version is: *not because we have too little data.* The best-corroborated cell in
the dataset — 7 independent voices across 2 platforms — reaches **4.7%** of the
gate, and every fix that preserves the multiplicative weighting form tops out at
**~2.6 against 3.0**.

**The answer you should not give:** "we need to collect more." The arithmetic in
§6 does not depend on what the unread threads say.

---

## 13 · Finding where a decision was made

Every ruling is written down, dated, and says what it ruled **out**. You should
never need to ask who made one.

| you want | look in |
|---|---|
| the non-negotiable rules and the conventions | `CLAUDE.md` — read this first, and note that its `assert_no_fixtures` entry flags itself as the one to re-check rather than re-read |
| how the machinery works, stage by stage | `docs/logic-and-workflow.md` (nine stages + the answer path) and `docs/how-it-works.md` |
| requirements and the build plan | `BUILD-PLAN.md` (36 FR, 10 NFR) |
| a ruling and what it ruled out | `docs/engineer-1/rulings.md` — eleven, numbered, each with "what would revise it" |
| a measurement and its denominator | `docs/engineer-1/measurements.md` (the ten that changed a decision) and `docs/measurements/` (92 individual runs). **`docs/measurements/README.md` has the method** |
| the defect catalogue | `tests/conftest.py` module docstring (canonical) and `docs/engineer-1/defect-shapes.md` |
| something proposed but not taken | `docs/proposals/` — 62 files. A `for-engineer-2-*` name means it crosses the lane boundary and needs the other side's ruling |
| what is next and why *that* | `docs/engineer-1/whats-next.md` |
| weights, thresholds, half-lives, capabilities, aliases, filter rules | `contract/` — and a change there is proposed and reviewed, never taken solo |
| why the board publishes nothing | `docs/proposals/for-the-team-the-publication-gate-is-uncalibrated.md`, then `for-engineer-2-tier-a-is-unreachable-by-construction.md`, then `docs/measurements/the-reweight-stopped-at-step-two.md` — in that order; each corrects the previous |

**How to read a proposal that was withdrawn.** Several are left in place with a
banner rather than deleted — `for-engineer-2-per-platform-signal-terms.md` is the
model. A proposal that was argued and then refuted by its own pre-registered test
is worth more as a record than as an absence. If you are about to propose
something, check `docs/proposals/` for its corpse first.

### The working agreement

Lanes were dropped **2026-08-28**. The `collect/` → `judge/` data-flow
architecture stays; the *ownership* rule around it is gone, because it cost more
than it saved — a signal measurement sat in a PR for two days before it reached
the person building a gate on top of it. This supersedes the per-lane ownership
language still in `collect/CLAUDE.md` and `judge/CLAUDE.md`.

- **Touch anything. Tell each other after, not before.**
- **`contract/` still gets two eyes.** That file is the agreement, not just code.
- **Measurements travel the day they are taken**, not via a PR body.
- **Say what you broke, not what you built.**
- **Shared-DB and staging writes are coordinated.**
- **The AST lane-boundary test stays — for testing, not ownership.** Two
  implementations of one storage contract can only be byte-compared while neither
  imports the other, which is what the flattener equivalence check relies on.
  Keep the reason visible so nobody removes the test as a leftover.

### One last habit, which is the point of this whole document

**Persist any run that enters an argument.** The extractor is nondeterministic and
an unsaved draw is gone. This has cost something concrete: the 150-thread run's
per-claim output was never written to disk, so when a tier ruling needed
re-pricing offline it could not be reconstructed from the checkout and had to wait
for a host that was down all afternoon. `docs/measurements/` exists to prevent
exactly that.
