# Pre-registration: a two-arm sweep, and the check that broke arm B

**Written 2026-08-24, before any sweep runs.** Every figure here is measured
from the current database; every expectation is stated with a threshold so it
cannot be chosen after the count exists.

*Engineer 1 · this document writes nothing else*

---

## 0 · The blocking finding: arm B has 3 candidates, not 25

The design said *"confirm each was in a previous sweep, because a model that was
seated and never swept belongs in arm A."* That check was the right one to build
in, and it fires.

`harvest_run` is the only per-model record of a sweep. It holds **153 rows, all
`source_id = 'github'`, all inside 26 minutes on 2026-08-20**. Matching every
seated model's surfaces and variants against the 121 distinct `query_key`s:

```
seated models (curated alias)                          41
  ever named in a recorded harvest_run query_key        3
      anthropic/claude-haiku-4.5
      openai/gpt-4
      anthropic/claude-3-haiku
  seated and NEVER swept                               38
```

**Opus 5 and Opus 4.8 were never swept.** Zero query_keys contain `opus`,
`gpt-5`, or `sonnet-4`. The recorded sweep asked about `claude-3`,
`claude 3 haiku`, `gpt-4`, `gpt4` — a roster two generations older than the one
we carry.

So under the design's own rule, the honest partition of the 58 models with any
attested mention is:

| | |
|---|---|
| **first coverage** (never swept) | 20 unseated + 38 seated = **58** |
| **re-run** (ever swept) | **3** |

**A 25-versus-25 comparison of covered against uncovered cannot be built,
because coverage has essentially never happened.** The 343 documents we hold came
from blog feeds and Reddit subreddits, which are population-scoped, not
model-scoped. Only GitHub sweeps for a named model, and it did so once, for three
models, for 26 minutes.

`model_version.last_swept_at` is **NULL on all 342 rows**, so nothing in the
registry records coverage either. The column exists; nothing writes it.

### And the previous sweep is a weak baseline even for the 3

```
153 runs   2,887 items fetched   6 kept   0 http errors
sieve_pass_rate  0.00 to 0.03
outcome IS NULL on 121 of 153 runs      <- never concluded: killed, or still open
```

`collect/ops/ledger.py` is explicit that `finished_at IS NULL` and
`outcome = 'error'` must not be collapsed. **79% of the runs in arm B's baseline
never concluded at all**, so "was in a previous sweep" means "a query was issued
under its name", not "was swept to completion".

## 1 · Arm A is 20, not 25

Unseated (no curated alias), non-route, with at least one attested mention in
the 316 readable texts we hold: **20 models.** The other 5 of a notional 25 would
have **zero** mentions, which is the opposite of the arm's selection criterion.
`is_route` excludes 18 rows (`openrouter/auto`, `~vendor/model`) that name no
model version.

**Arm A is therefore 20 members, and this is reported rather than padded.**

## 2 · Mentions per model, recorded before the sweep

The confound the design named, quantified now so the result can be read against
it:

| | members | total mentions | median | mean | max |
|---|---|---|---|---|---|
| **arm A** (unseated, attested) | 20 | 453 | **3.0** | 22.6 | 243 |
| **arm B** (top 25 seated by mentions) | 25 | 291 | **6.0** | 11.6 | 75 |

**The confound is real but it runs the opposite way from the design's
assumption.** Arm B was expected to be the heavily-discussed arm. By median it is
— 6 against 3 — but arm A has the higher **mean and max**, because
`claude-fable-5` (243 mentions) and `qwen3.8-27b` sit in arm A. Two models carry
arm A's mass.

So a yield difference cannot be read as popularity in a single direction. **Both
arms must be reported per-model, not as arm totals**, or two outliers in arm A
will decide the comparison.

Arm B's top members, with coverage status:

```
never swept   anthropic/claude-opus-4      docs=21  mentions=75
never swept   anthropic/claude-opus-4.8    docs=17  mentions=60
never swept   openai/gpt-5                 docs=15  mentions=45
never swept   anthropic/claude-opus-5      docs=3   mentions=12
SWEPT         anthropic/claude-haiku-4.5   docs=3   mentions=12
SWEPT         openai/gpt-4                 docs=3   mentions=9
```

## 3 · Cost, scoped this way

Measured with the real alias sets and variants from `model_alias`, 26 query
entries (18 daily / 8 weekly), 5-repo scope:

| | surfaces | daily req | weekly req | total | minutes @30/min |
|---|---|---|---|---|---|
| arm A (20 models, proposed surfaces) | 72 | 1,056 | 528 | 1,584 | 52.8 |
| arm B (25 seated, real surfaces) | 141 | 1,728 | 864 | 2,592 | 86.4 |
| **both arms** | 213 | **2,784** | 1,392 | **4,176** | **139.2** |
| all 41 curated, for reference | 221 | 2,832 | 1,416 | 4,248 | 141.6 |

`contract/harvest.yaml`: **daily 900 requests / 35 minutes.**

**This is not one night. The daily half alone is 3.1x the nightly cap.**

And note the last two rows: **two arms of 20+25 cost 139.2 minutes; sweeping all
41 curated models costs 141.6.** Scoping to two arms saves 1.7% — because arm A's
20 unseated models bring 72 new surfaces with them. The scoping buys a clean
comparison, not a cheaper sweep.

### On the 145-minute figure

The figure the design anchors on — *"145 minutes was all 78 seated models"* —
does not reconcile with anything measured here, and the mismatch is a rule-7
one. I measure **141.6 minutes for 41 models**. The minutes agree within 2.4%;
the population differs by nearly 2x. Nothing in the repository records 78 seated
models: `model_version` holds 342 rows, 41 with a curated alias, 282 with
`in_window`. `docs/measurements/tracked-set.md:235` records 81.45 requests per
model, which matches the 80/model I measure and implies **11 models a night**,
not 78.

**So 145 minutes is very likely 41 models, not 78** — and if it is used to decide
whether this is one night, it will be read as though a sweep costs half what it
costs. What fits one night, at the measured per-model rates (arm A 52.8 daily
req/model, arm B 69.1):

```
7 per arm   ->   853 daily requests   fits, headroom 47
8 per arm   ->   975 daily requests   OVER by 75
```

**Two arms of 7 is one night. Two arms of 25 is 3.1 nights of daily budget**, or
one night if the weekly entries are dropped and the scope halves — neither of
which is free, since the weekly entries are the only positive evidence eight
capabilities ever get.

## 4 · Pre-registered expectations

Stated before the numbers exist.

### Arm A (20 unseated, attested), first coverage

> **Expect 0 stored claims. Expect fewer than 15 documents to survive triage,
> and expect more than half of those to be about `claude-fable-5` alone.**

Basis: three prior sweeps. GitHub returned 2,887 items for **6 kept** at a sieve
pass rate of 0.00-0.03; 3,776 candidates produced 0 claims from author prose;
and seating 50 models recovered **0 of 134** unresolved claims. 16 of arm A's 20
members have <=2 documents.

### Arm B (25 seated), 22 of which are also first coverage

> **Expect 0 stored claims. Expect a document count within a factor of 2 of arm
> A's, and expect the per-model yield to track mentions rather than coverage
> status.**

### The decision rules

| result | reading |
|---|---|
| **both arms ~0 claims** | the constraint is what people write. Fourth confirmation. Stop testing it; the lever is the family-word ruling (26 claims) and the page's family-level surface |
| **arm A yields and arm B does not** | coverage matters, and the registry ranking is the lever after all. Would overturn the standing conclusion |
| **arm B yields and arm A does not** | popularity, not coverage. Predicts yield from mentions — sweep by mention rank and ignore seat status |
| **both yield** | the prior sweeps were mis-scoped, not the corpus mis-written. Re-examine the sieve and the 0.00-0.03 pass rate first |
| **yield tracks mentions across BOTH arms, ignoring the arm boundary** | the arm variable is inert and the experiment measured the confound. Report as such rather than as a coverage finding |

**The threshold for "yields":** >= 3 stored, quote-verified claims resolving to
a seated model. Not documents, not candidates — both prior sweeps had candidates
in abundance. Anything under 3 is noise at these volumes.

**What would NOT change the conclusion:** more retrieved candidates. A sweep
returning 10,000 items and 6 kept is the 2026-08-20 result at larger scale.

## 5 · What I recommend, given §0

**The 25-versus-25 design cannot run as specified**, so it should not be run
half-way and reported as though it had. Two options, and the choice is not mine:

1. **Accept the honest partition** — arm A = 58 never-swept models, arm B = 3
   ever-swept. Arm B is too small to compare, so this is a coverage baseline
   rather than a two-arm experiment. Cheap, truthful, answers less.

2. **Change the variable to attestation**, which the data supports: two arms of
   equal size, both first coverage, split by whether the corpus already mentions
   them. That tests the popularity confound *as the variable* instead of leaving
   it uncontrolled, and it is decision-relevant either way. At 7 per arm it is
   one night.

**(2) is what I would propose**, sized at 7 per arm to fit the nightly budget,
with per-model reporting so arm A's two outliers cannot carry the result.

Whichever runs, **`last_swept_at` should be written by it.** It is the column
that would have answered §0 in one query instead of a reconstruction from
`query_key` strings, and it is the documented precondition for any rotation.
