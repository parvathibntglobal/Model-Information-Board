# For Engineer 2 — a rule described and not enforced, in `f_specificity`

Three asks, reordered. **The first is the one that matters and it is independent
of everything else in this document.** Measurements:
`docs/measurements/inherited-subjects-and-family-claims.md`, runs in
`f-specificity-double-counting.txt` and `thread-subject-inheritance.txt`.

All of this is your lane. Nothing in `judge/` has been touched — one docstring
warning went into `collect/triage/specificity.py`, at the source of the input
below, and that is the only code change.

**Thread-subject inheritance is ruled out and is no longer an ask.** Anooj's
second condition settled it: 32 of 53 candidates name a second model, and the 21
survivors are all in two announcement threads — the population that produced the
four vendor-copy claims already on staging. Recorded in the measurement so the
next person finds the reason.

---

## 1. `f_specificity` reads a document-level fact per claim

`judge/pipeline.py:223` → `judge/vet/weight.py:195`:

```python
version_named=document.names_version          # pipeline.py:223
...
f_specificity=specificity_factor(version_named=version_named, ...)
```

`document.names_version` is computed by `collect/triage/specificity.py:names_version`
over the **whole document**: does a version-bearing surface appear anywhere.
`claim.specificity` is about the surface **this claim used**. `compute()` takes
both, and prices overlapping facts twice at two granularities:

| factor | input | granularity |
|---|---|---|
| `f_fuzziness` | `FUZZINESS_WEIGHT[claim.specificity]` | claim |
| `f_specificity` | `specificity_factor(version_named=…)` → +0.2 | **document** |

So a family-specificity claim in a document that names a version anywhere
collects the +0.2 for a version it did not name. Reddit, tier A, central, fresh:

```
family + version_named + numbers + conditions + repro     0.2550   <-- outweighs
version + version_named, no artifacts                     0.2244
family  + numbers + conditions + repro, version_named off  0.2193   <-- does not
snapshot + version_named, no artifacts                     0.3740
```

**Exactly one family combination beats the version-named reference, by 14%, and
it requires `version_named=True`** — which is not a contradiction in the code,
because the flag is about the document. A launch thread is the worst case and the
common one: the root names the model, so every comment in the flattened text
inherits `names_version=True`.

`contract/harvest.yaml` already warns about this exact pair — *"Different
granularity (document vs claim) … They must never be merged AND NEVER
COMPARED — a reader seeing 0.7 in both will want them to mean the same thing."*
They are not compared; they are multiplied, which the warning did not anticipate.

## 2. Nothing counts specificity when counting voices

`judge/curate/gate.py:count` takes one representative per `voice_id` and **never
reads specificity**. Grepping `judge/curate/`, `judge/pages/` and `judge/ask/` for
`specificity` returns only `specificity_x_log_engagement` in `thread_coverage.py`,
which is the thread selector and unrelated.

So a family claim is one `independent_voices` exactly like a snapshot claim, and
the phrase vocabulary reads voice counts:

```
GENERALLY_PRAISED_VOICES = 3        WIDELY_PRAISED_VOICES = 5
```

Claims needed to reach `N_EFF_MINIMUM = 3.0`, at best case per specificity:

| | reddit | github |
|---|---:|---:|
| snapshot | 4 | 4 |
| **family, best case** | **12** | **11** |
| family, adjectives only | 40 | 36 |

**Twelve family claims publish a cell**, and they clear
`WIDELY_PRAISED_VOICES = 5` on the way — so a cell can read **"Widely praised"**
off twelve claims whose subject nobody stated. `contract/seed_models.yaml` maps
bare `opus` to `anthropic/claude-opus-5`, so that cell lands on Opus 5 regardless
of which Claude generation the writers meant.

`gate.py`'s docstring argues a `voices >= 3` condition would be dead text because
`n_eff >= 3.0` implies four or more claims. **True at snapshot weight and false at
0.3**, where it implies twelve — so voice count and weighted count stop tracking
each other exactly in the regime where the phrases read voice counts. The
docstring's reasoning is sound and its premise is specificity-dependent, which
nothing says.

### Which makes this a rule described and not enforced

`collect/registry/propose.py` said, for weeks, that a family-specificity claim
*"never counts as independent corroboration"*. I corrected that line on
2026-08-21 after grepping for the enforcement and finding none.

**That sentence is the constraint the `FAMILY_WORDS` ruling rests on.**
`collect/triage/entity.py` now refuses to admit bare family words partly because
a family claim cannot corroborate — and it can, at twelve. The ruling survives on
its stronger ground (admitting `sonnet` attributes a 2024 Claude 3 post to Claude
Sonnet 5, which is a definite claim about the wrong model), so nothing needs
reverting. But one of its two supports was load-bearing prose.

## What I would ask for

Not a number. **A stated rule** in `contract/`, and then whatever enforces it:

- a family claim may not be the marginal claim that publishes a cell; **or**
- family claims do not count toward the voice thresholds the phrase vocabulary
  reads.

Either is enforceable in `gate.count`, which is the one place that would need to
start reading specificity. I would not reach for a new weight: `harvest.yaml`
already labels the specificity weights *"PROVISIONAL · INTRA-CHANNEL ONLY · NEVER
CALIBRATED"*, and leaning a publication rule on an uncalibrated weight is how a
threshold quietly becomes a policy nobody chose.

### Is the fix a one-line source change? The change is one line; the decision is not

`version_named` **is** derivable — `claim.specificity in ("snapshot", "version")`
is one expression, and it is available at the call site. So substituting it is a
one-line change and you do not need anything from me to make it.

Two reasons I would not treat it as one:

1. **It double-prices one fact.** `f_specificity` would give +0.2 for what
   `f_fuzziness` already prices at 0.6/1.0. A family claim with version_named-only
   goes 0.1122 → 0.0765, a 32% cut, for a fact already discounted once. The 0.2
   and the 0.3 were chosen independently and neither was calibrated, so
   compounding them is a new weight arrived at by accident.
2. **It changes what `f_specificity` measures.** Its docstring is *"real
   experience carries numbers and error strings; slop carries adjectives"* — a
   document-quality score, with `version_named` in it as a cheap proxy for "this
   person was being specific", not as an attribution signal. Removing it narrows
   the factor to three artifact signals. That may well be right, and it is a
   decision about what the factor is for.

My read: **drop `version_named` from `specificity_factor` entirely** rather than
re-source it. Attribution is `f_fuzziness`'s job and it already does it;
`f_specificity` is then three artifact signals and one clean meaning, and the
document/claim granularity collision goes away instead of being repriced. But
that is your factor and your call.

## 3. Declare inherited subjects (unchanged from before)

3 of the 4 stored claims quote text naming no model — *"exceptional performance in
software engineering"*, *"We'll keep refining the safeguards"*, *"gives 10%+
better results on SWE-Bench"* — all recorded `specificity=version`. The extractor
is handed the whole flattened thread and `prompt.py` never mentions the root, so it
infers the subject correctly and has no way to say it did.

Two small things, if you agree:

- `subject_inherited: bool` — **not** a fourth `Specificity` value. Inheritance is
  orthogonal to specificity: *"Introducing Claude Fable 5"* is snapshot-specific
  while the claim's own text names nothing. A fourth level collides two facts in
  one column, which is the mistake I made in `ResolutionReport` last week, where
  "owned by nobody" and "owned by several" shared the name `ambiguous`.
- one paragraph in `prompt.py` saying the extractor may attribute a comment to a
  subject named in the thread root and must mark it.

And `max_thread_share` on `CellCounts`, capped the way `max_author_share` is. This
one is not conditional on inheritance being formalised, because inherited claims
already exist: measured on one launch thread, **80 distinct authors** would supply
80 independent voices from one act of naming by the vendor, and `max_author_share`
cannot see it because they really are different people. The only thing bounding it
today is that the thread selector keeps 2.7% of observed children — **so please do
not widen thread assembly before this exists.**

---

## What it takes on our side

**Nothing required.** `version_named` can be derived from `claim.specificity` at
your call site, and `claim.specificity` is already stored.

Two things I have done or can do:

- **Done:** a warning at the source. `collect/triage/specificity.py:names_version`
  now says in its docstring that it is a document-level fact and not an
  attribution signal for one claim, names the call site, and carries the 0.2550
  vs 0.2244 figure. It answers the question it was asked and the docstring exists
  so the next caller reads the granularity warning at the point of use.
- **Available if you want it:** a claim-level `names_version` cannot come from
  `collect/` — the claim is yours. What `collect/` could supply instead is a
  version-bearing-surface check over an arbitrary span, so you could ask "does
  *this quote* name a version" rather than "does the document". Say the word;
  `entity.resolve` already does it and it would be a thin wrapper.
- **Also mine, separately:** `build_population` would need to carry family
  surfaces as a labelled fourth contribution before a family claim could resolve
  at all — and `model_alias` currently holds **0 family rows** (82 snapshot, 23
  version), because every `model_version` row is `provenance='polled'` and the
  seed file's 13 family aliases have never been loaded here. So a family claim has
  no owner to resolve to today by accident rather than by rule. Cheap to fix, once
  there is a rule saying what family claims may do.

---

## And what this leaves `oqocfjv`

*"Fable uses up more tokens than a old Porsche gas"* — the only first-hand
capability observation in the seven documents. Plainly:

- **Not recoverable by inheritance.** Ruled out above, and it would not have
  qualified anyway: `fable` is bare in a comment, and the rule needs the root to
  resolve and the comment to name nothing else — which it satisfies, but the rule
  is not being built.
- **Not recoverable by the word list.** `FAMILY_WORDS` is unchanged and the
  measurement says an adjacency rule recovers 0 of 40 labelled rows. There is **no
  digit anywhere in the text**, so no adjacency rule can reach it at any window
  size. Every arm returned NO MATCH.
- **Recordable as a family claim only if the gate actually declines to count it —
  which it currently does not.** Today the sequence would be: bare `fable`
  resolves to nothing (no family aliases in `model_alias`, no family part in the
  population), so the claim is never stored. If both of those were fixed *without*
  the rule in ask 1, it would be stored, counted as one independent voice, and be
  one of twelve that could publish a cell against `anthropic/claude-fable-5` —
  from claims whose writers never said which Fable they meant.

So it stays invisible, and the order of work to change that is fixed: **the
counting rule first, the resolution path second.** Reversing that order is how
the only first-hand observation we have becomes the first family claim to lift a
cell.

That is worth saying out loud because it is the uncomfortable version: the reason
`oqocfjv` is invisible is not that anybody decided its evidence was weak. It is
that the machinery has no way to hold a claim at family specificity without also
letting twelve of them publish, and nobody has written the rule that would.
