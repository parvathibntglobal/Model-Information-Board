# The dated baseline sweep: what it is for, what it costs, and the two things blocking it

**Written 2026-08-24, before the sweep runs. Nothing has been swept and nothing
has been seated.** Two blockers were found while costing it; both are reported
rather than worked around.

*Engineer 1*

---

## 1 · What the sweep is for, since the framing has changed twice

**Not "more evidence."** That was measured twice and answered:

```
GitHub, 5 repos, 10 seeded models    3,776 candidates -> 25 documents -> 0 claims from author prose
Blogs, 9 feeds                       140 claims extracted -> 7 stored, 133 resolving to nothing
Seating 50 more models               0 of 134 unresolved claims recovered
```

**It is a dated baseline.** One sweep, timestamped, over a known population, so
that in a fortnight there is a *before* to compare a second sweep against. The
prior sweeps cannot serve as a before: the only per-model sweep record in the
database is 153 GitHub rows inside 26 minutes on 2026-08-20, covering three
models, with `outcome IS NULL` on 121 of them.

The baseline's value is entirely in its date and its population being written
down. That is why §6 pre-registers the fortnight comparison now.

## 2 · How many models are in the sweep: 40

Counted from `model_alias` via `collect.ops.sweep.seated_variants`, which is the
function the sweep itself calls — not inferred.

```
model_version rows                              342
model_alias rows, all                           105
model_alias rows, valid_until IS NULL           103
DISTINCT models with any alias row               41
DISTINCT models the sweep actually reads         40   <- seated_variants(conn)
distinct search variants across them            177
excluded, named rather than silent                1   z-ai/glm-4.5, every alias
                                                      window closed: retired
```

**The sweep is 40 models and 177 variants.** The 41st is `z-ai/glm-4.5`, and
`excluded_seats()` names it rather than letting the count shrink quietly.

### Reconciling 41, 53 and 78

- **41** is right for *"models with a curated alias row"*.
- **40** is right for *"models a sweep will search for"*.
- **103** is the count of *valid alias rows*, not models — and **this is where a
  models-figure near 100 comes from. It is rows.** My own previous report costed
  "103 seated models"; that number is alias rows and the model count is 40. Mine
  to correct.
- **53 and 78 are not reproducible from this database.** No query I can construct
  returns either: the available counts are 342 versions, 282 `in_window`, 105
  alias rows, 103 valid, 41 models, 40 swept. Both figures need sourcing from
  whoever wrote them before anything rests on them.

**The 1,258-minute estimate rests on 40 models, or on 60 after seating** — see
§5. It does not rest on 78, and at 78 it would be roughly double.

## 3 · Why the two-arm design died — and it was not `render_all`

**`render_all` does not exist.** It appears nowhere in the repository: no Python
symbol, no test, no document. It was not my finding and I am not adopting it.
The render functions that exist are `render_search` and a local `render` inside
`contract.py`, and neither is the constraint.

**What I actually found** was that coverage never happened: only 3 of 41 seated
models were ever named in a recorded sweep, so arm B had 3 candidates rather than
25 and there was no *covered* population to compare against.

**But the substance attributed to `render_all` is separately true, and it is a
second, independent reason the design could not run.** `collect/ops/sweep.py`:

```python
by_model = seated_variants(conn)          # EVERY row in model_alias
plans = {cid: plan_searches(entries, list(v), scope=scope)
         for cid, v in by_model.items()}
for canonical_id, variants in by_model.items():   # ORDER BY canonical_id
    if report.requests_issued + plan.request_count > cap:
        report.unreached.append(canonical_id)      # and stop
```

`run_sweep` has **no model-selection parameter.** A sweep is a property of the
seated population, exactly as stated. Per-model *planning* exists — `plan_searches`
is called per model — but per-model *selection* does not, and adding it means
changing `run_sweep`'s signature and `seated_variants`, not a renderer.

**And the iteration order has a consequence worth more than the API gap:** the
sweep walks `ORDER BY canonical_id` and stops on the budget, so what gets covered
is an **alphabetical prefix**. At 40 models against a 900-request cap, `anthropic/*`
consumes the budget and `z-ai/*` is never reached. This also explains the
2026-08-20 record without any other hypothesis: the three models it swept —
`claude-3-haiku`, `claude-haiku-4.5`, `gpt-4` — are alphabetically early. Nobody
chose them.

**So `unreached` is where most of the roster will land, and the baseline must
report it as coverage rather than as absence.** That is rule 4 at the population
level: a model the budget never reached must not render as a model nobody
discussed.

## 4 · Blocker: the 20 cannot be seated without revoking 30 existing reviews

**The attested set is 20, not 25.** Unseated, non-route, with at least one
attested mention: 20. The other 5 of a notional 25 carry zero mentions, which
inverts the criterion. Stated for the third time and not padded.

Seating goes through `registry load-tracked-set`, which requires a **manifest**
carrying `reviewed_at`, `reviewed_by`, a population count, and a **sha256
fingerprint of each entry's surfaces as reviewed**. The module exists precisely
so a loader cannot key on the generator's own `attested` label — its docstring:
*"a loader keyed on them admits every future entry the generator labels attested
with no human in the path."*

The current record is real and it verifies:

```
docs/proposals/reviewed-seats.yaml   41 seats, reviewed 2026-08-20 by engineer-1
recomputed against the artifact:     41 of 41 fingerprints match
all 41 are seated in model_alias
```

Of the 20 attested models, **7 are already entries in the artifact and 13 are
not** — including the largest, `anthropic/claude-fable-5` at 45 documents. So
seating them means adding 13 entries to the artifact. **Regenerating it does
this:**

```
regenerated for the same 63 ids, with today's observed data
  reviewed seats unchanged :  11 of 41
  reviewed seats MOVED     :  30 of 41     <- review revoked for each
  of those, primary surface now INCOMPLETE :  23
  entries with an INCOMPLETE primary       :  38 of 63
```

**Regenerating would revoke 30 of the 41 live reviews, and 23 would come back
with `INCOMPLETE` as the primary surface, which `plan()` refuses.** They moved
because `observed` changed: the corpus went from 64 documents to 343, so the
attested forms changed and the generator now picks differently.

```
anthropic/claude-opus-4    was: opus-4    now: opus 4
openai/gpt-5.2             was: gpt-5.2   now: INCOMPLETE
google/gemini-2.5-pro      was: gemini 2.5 pro   now: INCOMPLETE
```

The fingerprint mechanism is working exactly as designed — it is telling us the
content moved. **The seats themselves are safe:** `model_alias` is append-only,
so the 41 stay seated and stay swept. What a regeneration destroys is the audit
trail, and `tracked_load.py` is explicit that there is no undo.

**So I have not seated anything, and I am not going to by regenerating.** The
safe path is additive: a **second artifact** covering only the 13 (or all 20),
with its own manifest, leaving the existing pair untouched — `read_manifest`
takes a path and the artifact name is a field, so this is supported rather than
a workaround. That still needs the review act, which is not mine to perform: a
manifest I write and sign has a `reviewed_by` naming a person who did not review
it, which is the one guarantee the module claims.

**What I can do without writing anything:** `load-tracked-set --dry-run` runs
`plan()`, which touches nothing and prints every verdict and refusal per seat.
That is the diagnostic to look at before deciding.

## 5 · Cost, and reconciling 1,258 minutes with 208

Two figures, both correct, differing by one unmeasured factor.

**What is measured here.** Sieve throughput, cache warm, real variants, real
documents:

```
per sieve call, by document length          ms      per 1,000 chars
  12,705 chars                            37.3           2.94 ms
  25,410 chars                            71.2           2.80 ms
 101,640 chars                           275.8           2.71 ms
 254,100 chars                           678.5           2.67 ms
```

**The sieve costs ~2.7-2.9 ms per 1,000 characters and is linear.** One call does
198 pattern lookups over 25 distinct compiled patterns, for 6 spellings x 120
terms.

Cold cache is **not** a factor: cold 36.7 ms against warm 36.8 ms, ratio 1.0x,
and `_pattern_for` fills in 25 misses on the first call. Caching is already
doing its job.

**HTTP cost, real alias sets, 26 entries (18 daily / 8 weekly), 5 repos:**

| | requests | HTTP min @30/min |
|---|---|---|
| 40 seated, today | 3,216 | 107.2 |
| 60, after seating the 20 | 4,944 | 164.8 |

**Total, at the two document populations:**

| document size | sieve/call | sieve min | + HTTP | total | sieve share |
|---|---|---|---|---|---|
| 2.2k chars (Reddit, measured) | 5.3 ms | 43.5 | 164.8 | **208 min (3.5 h)** | 21% |
| ~48k chars (GitHub thread, assumed) | 133 ms | 1,096 | 164.8 | **1,261 min (21 h)** | 87% |

**The 1,258-minute figure reconciles exactly**: it is the 60-model sweep at 100
items per request over ~48,000-character documents. It is not wrong. It is a
different population from the one I measured, and the 6x spread between 208 and
1,261 minutes is **entirely the document size**, which is the factor neither
figure carries with it.

**And I cannot measure that factor on this machine.** All **27 of 27** GitHub
payloads resolve `missing` from the local raw store, so the real GitHub document
size is not observable here. So: the *rate* is measured, the *population* is not,
and until somebody runs this where the store lives, the honest statement is
**"208 minutes at Reddit-sized documents, 1,261 at 48k-sized, and we do not know
which GitHub is."** That is the number to settle before treating 21 hours as the
decision.

### The sieve cost is reducible, and by a lot

87% being local processing makes this a performance question, and the mechanism
is identifiable rather than speculative. One sieve call scans **25 patterns
separately**. Unioning them into one alternation, measured:

```
25 separate pattern scans   3.139 ms
ONE unioned alternation     0.235 ms      13x faster
```

**At 13x, the 1,096-minute sieve becomes 84 minutes, and the 21-hour sweep
becomes 4.2 hours with HTTP as 66% of it.** That inverts which half is worth
optimising, and it is a change inside `sieve_any`/`_pattern_for` with no effect
on what passes — a union of the same patterns matches the same set.

**Caveats, because a 13x on a microbenchmark is not a 13x in production.**
`sieve_any` returns the *furthest-progressing verdict* with per-group missing
counts, and a single alternation loses which alternative matched. So the real fix
is a **two-stage sieve**: one unioned regex as a cheap reject filter, then the
per-pattern pass only on documents that survive it. Given the measured pass rate
of **0.00-0.03**, 97-100% of documents would exit at stage one, which is where the
13x is actually available. That preserves the verdict shape the defect-4 costing
depends on.

**This is the cheaper thing to fix, and I would fix it before running a 21-hour
sweep.** It is one function, it is testable against the existing sieve for
identical verdicts on the stored corpus, and it changes the sweep from an
overnight commitment to an afternoon.

## 6 · Can it be split across nights? Not today, and the timestamp is not the reason

Two separate answers.

**Does splitting invalidate the baseline?** No, *in principle* — a baseline is
per-model evidence with a per-model date, so models swept on different nights are
fine as long as each model's date is recorded. **In practice it does, because
nothing records them:** `model_version.last_swept_at` is **NULL on all 342 rows.**
The column exists (`contract/tables.sql:83`), `assert_no_phantom_sweeps` guards
it, and no code writes it. A split sweep today produces a baseline whose per-model
date is unknown, which is not a baseline.

**Can it be split at all?** No. `watermark` exists as a table keyed
`(source_id, query_key)` — the right key — but **nothing in `collect/ops/` reads
or writes it.** `run_sweep` re-derives `by_model` from `seated_variants` in
`canonical_id` order every invocation, so night two starts at
`anthropic/claude-3-haiku` again and re-issues night one's requests. It is a
restart, not a resume, and `z-ai/*` is never reached on any night.

**So splitting needs one of two small pieces of work, and they are the same work
the rotation in `harvest.yaml` already needs:** write `last_swept_at`, and either
order by it or consult `watermark`. Both were named as preconditions ten days ago
in `harvest.yaml` lines 94-99. Neither is large.

**Given that, running one sweep inside one budget is the wrong shape anyway** —
at 3,216 requests against a 900 cap, a single night covers ~11 of 40 models
alphabetically and reports 29 `unreached`. A baseline over 11 alphabetically-early
models is not a baseline over the population.

## 7 · Pre-registration of the fortnight comparison

**Written now, before the first sweep, so neither reading can be chosen
afterwards.** Compares sweep 1 (baseline, date D) against sweep 2 (date D+14),
same code, same population, same scope.

### The measurement

Per model, and reported per model rather than as arm totals:
documents retrieved, documents surviving triage, stored quote-verified claims,
and `unreached` status. Plus corpus-wide: sieve pass rate, and the count of
models that moved from `unreached` to covered.

### What would mean coverage matters

> **Sweep 2 yields >= 3 stored, quote-verified claims from models that sweep 1
> left `unreached`, while models covered in both sweeps yield ~0 new.**

That is the only shape that isolates coverage. It says the evidence was there and
we were not asking. If it holds, the lever is coverage — write `last_swept_at`,
build the rotation, and the registry work is justified after all.

### What would mean the constraint is what people write

> **Sweep 2 yields < 3 stored claims in total, regardless of which models moved
> from `unreached` to covered.**

Two sweeps a fortnight apart over the same population, with real new documents in
between, producing nothing. Combined with 0 claims from 3,776 GitHub candidates,
7 stored of 140 blog claims, and 0 of 134 recovered by 50 seats, that is the
fourth independent test of one hypothesis and it should be closed.

### The other outcomes, named now

| result | reading |
|---|---|
| **both sweeps yield ~0, and sieve pass rate stays 0.00-0.03** | the constraint is what people write. Close it. The lever is the family-word ruling (26 claims v 0 from 50 seats) and family-level rendering |
| **sweep 2 yields on models covered in BOTH sweeps** | it is time, not coverage — new documents appeared. Predicts cadence matters and the nightly schedule is doing real work |
| **sweep 2 yields only on newly-covered models** | coverage matters. Overturns the standing conclusion |
| **sweep 2 yields broadly, on covered and new alike** | the first sweep was mis-executed rather than the corpus mis-written. Examine the 0.00-0.03 pass rate and the sieve before concluding anything about the corpus |
| **neither sweep completes its population** | the comparison is between two alphabetical prefixes and measures budget, not coverage. Must be reported as inconclusive rather than as a null result |

**"Yields" is >= 3 stored, quote-verified claims resolving to a seated model.**
Not documents and not candidates: both prior sweeps had candidates in abundance
and the thing that never appeared was a claim.

**What would NOT change any conclusion:** a larger candidate count. A sweep
returning 10,000 items and 6 kept is 2026-08-20 at scale.

**And the confound that applies to the fortnight comparison specifically:** the
corpus grows between the sweeps from *other* sources — blog and Reddit sweeps are
population-scoped and run on their own cadence. So a claim appearing in sweep 2
may come from a document that GitHub retrieval had nothing to do with. **Sweep 2
must attribute each new claim to the source that retrieved its document**, or a
blog-sourced claim will read as evidence that GitHub coverage worked.

## 8 · What I recommend, in order

1. **Fix the sieve** (two-stage, unioned pre-filter). One function, testable for
   identical verdicts against the stored corpus, and it decides whether the
   baseline is 4 hours or 21.
2. **Write `last_swept_at` from the sweep.** Without it there is no per-model
   date, so there is no baseline to compare against in a fortnight — the entire
   point of §1.
3. **Settle the document-size question** by running the cost on a machine that
   has the raw store. 208 against 1,261 minutes is a different decision, and it
   is one unmeasured factor.
4. **Then decide the seating**, from `load-tracked-set --dry-run` output, as an
   additive second artifact. It is not a prerequisite for a baseline — a baseline
   over 40 models is a valid before, provided §7's population is recorded as 40
   and not described as the roster.

Nothing here has been run and nothing has been written to the registry.
