# The family-word rule is worth nothing, and looking for it found a nondeterminism

**A version-adjacency rule for `FAMILY_WORDS` recovers 0 of 40 labelled rows and
costs 0 false positives on 750 control documents. It should not be built.** The
exclusion was not the error source at this sample size; registry coverage was.
Measuring it turned up a real defect: `RegistrySurfaceResolver` returned a
different answer for the same surface depending on `PYTHONHASHSEED`.

*Engineer 1 · 2026-08-21 · population `b5744297e9210497`*

---

## 1 · Scope: there is no window at `_admissible`

Four sites exclude family words. **All four are in population construction and
none has a document.**

| site | what it does |
|---|---|
| `propose.py:246` `_renderings` | drops any rendering that is a family word |
| `propose.py:306` `rule_variants` | guard 1 — the dropped token must **be** a family word |
| `propose.py:308` `rule_variants` | guard 2 — `rest[0]` must **be** a family word |
| `entity.py:191` `_admissible` | drops any surface that is a family word |

`build_population(models, declared)` takes registry rows and declared surfaces.
There is no text parameter, and it runs once per process before any document is
read. **So the exclusion happens before there is a window to look in.** A
version-adjacency rule cannot live at `_admissible` at any price — the decision
would have to move to match time in `resolve()`, and `SurfacePopulation` would
have to start carrying family-word surfaces separately so `resolve()` could
consider them under a rule. That is a restructure of the boundary between the
population and the matcher, not a change to a predicate.

**And `FAMILY_WORDS` is load-bearing in the opposite direction.** My first
attempt at a ceiling emptied the set, and the population went *down*: 1,247
surfaces → 1,205, with all 51 vendor-drop surfaces gone. `rule_variants` guard 1
*requires* the dropped token to be a family word, so an empty set kills the rule
that produces `opus 5` from `anthropic/claude-opus-5`. The list is both the
exclusion and the input to the derivation that makes the exclusion survivable.
The corrected ceiling patches `_admissible` only.

---

## 2 · What the exclusion actually costs, both sides

Corrected ceiling — derivation untouched, `_admissible` admitting everything:

```
baseline  1247 surfaces (declared 23, mechanical 1173, vendor-drop 51)  b5744297e9210497
ceiling   1250 surfaces (declared 26, mechanical 1173, vendor-drop 51)  6dd62c5ebb2351b2
admitted: ['haiku', 'opus', 'sonnet']       lost: []
```

**The entire footprint of the exclusion is three surfaces.** The other 23 family
words never enter the population regardless — nothing derives them and they are
not declared. So the exclusion cannot be preventing `air`: **`air` is not in the
population with or without it.** What keeps `air` out is that no registry id and
no declared surface produces it.

That row is in the pool because `bare_family_hits()` scans `FAMILY_WORDS`
directly against the text — that is the **sampler**, not the gate. `air` in *"a
breath of fresh air"* was never a false positive the gate could make. The claim
that the exclusion "prevents `air`" does not survive the measurement, and that is
why the cost side below is zero rather than a trade.

### Side 1 — the 40 labelled rows with a surface

Scored under the four-outcome mapping in use at the time. **The headline figure
is now 26/40 = 65.0% under the collapsed binary scoring ruled in section 9**; the
arms below are equal under either, and +0/-0 is the result that matters.

| arm | agreement | vs baseline |
|---|---|---|
| baseline | 22/40 = 55.0% | — |
| ceiling (admit all three) | 22/40 = 55.0% | **+0 / −0** |
| R1 — immediately adjacent token opens with a digit | 22/40 = 55.0% | **+0 / −0** |
| R2 — a digit within 20 chars either side | 22/40 = 55.0% | **+0 / −0** |

Two rows change *outcome* and neither changes *verdict*:

```
#6 'opus'   label=resolves   no-match -> no-owner   (opus -> no registry model derives it)
#7 'sonnet' label=resolves   no-match -> no-owner   (sonnet -> no registry model derives it)
```

**That is the whole answer.** Admitting bare `opus` cannot produce
`names-one-model`, because bare `opus` is a *declared-only* surface and
`build_population` records no owner for it — it refuses to guess which model a
human meant (rule 6). So the best any family-word rule can do on those rows is
move them from `no-match` to `no-owner`, and the label is `resolves`. They
disagree either way.

The three rows the brief names:

| row | surface | label | baseline | ceiling | R1 | R2 |
|---|---|---|---|---|---|---|
| 5 | `mini` | resolves | one-owner | one-owner | one-owner | one-owner |
| 6 | `opus` | resolves | no-match | no-owner | no-owner | no-owner |
| 7 | `sonnet` | resolves | no-match | no-owner | no-match | no-owner |

`mini` in *"GPT-4o mini"* **already agrees** — reading the document covers it
through `gpt-4o-mini`, which landed in the previous round. It was not waiting on
a family-word rule.

`opus` and `sonnet` in *"Claude 3 Opus & Sonnet"* fail for a reason no rule
touches: **the registry holds no `anthropic/claude-3-opus` and no
`anthropic/claude-3-sonnet` row.** The only `claude-3-*` id it holds is
`anthropic/claude-3-haiku`. There is no model to resolve to. Same for `mixtral` —
no `mistralai/mixtral-*` row beyond `mixtral-8x22b-instruct`, which the document
does not name.

Note R1 and R2 disagree with each other on row 7: `sonnet` in *"Claude 3 Opus &
Sonnet"* has no digit in the immediately adjacent token either side (`opus` before,
`mistral` after), so R1 refuses it and R2's 20-character window reaches back to
the `3`. Neither changes the verdict, which is the point — the rule's tuning
parameter has no purchase on the outcome.

### Side 2 — the control corpora, 450 Tier 1 + 300 Tier 2

| arm | Tier 1 | Tier 2 |
|---|---|---|
| baseline | 2/450 (0.4%) | 0/300 (0.0%) |
| ceiling | 2/450 (0.4%) | 0/300 (0.0%) |
| R1 | 2/450 (0.4%) | 0/300 (0.0%) |
| R2 | 2/450 (0.4%) | 0/300 (0.0%) |

**Identical in every arm.** The ceiling adds exactly one family-word hit —
`opus`, in the one Tier 1 document that already matched `claude opus` — so not
even one new document survives. Tier 2 stays at exactly 0.0%.

So the trade the brief describes is not a trade. The rule gains nothing and costs
nothing, because the three surfaces it would admit are ownerless and the words
that would cause damage were never admissible in the first place.

### And it does not recover `oqocfjv`

> *"Fable uses up more tokens than a old Porsche gas"*

No match under baseline, ceiling, R1 or R2. **There is no digit anywhere in the
text.** An adjacency rule tests for a version token, and there is none to find —
so the one first-hand capability observation in the seven stays invisible at any
window size. It is a cost of the exclusion that this shape of fix does not buy
back, which matters when weighing the restructure: the row most often cited as
the reason to do this is not among the rows it would recover.

**Verdict against the brief's own test — *"if it recovers the three and
reintroduces `air`, it is not a fix"*: it recovers none and reintroduces
nothing.** Do not build it. What would recover rows 6, 7 and 12 is registry
coverage of deprecated models, which is a different piece of work with a
different owner.

---

## 3 · The nondeterminism, found by a measurement disagreeing with itself

Three runs of the same scoring script over the same pool gave **50.0%, 52.5% and
55.0%**. Row 14, `4.1 mini`, flipped between `no-owner` and `one-owner`.

I had attributed the movement to the `commanda` re-label. That was wrong: the
re-label accounts for one row, and the rest was this.

### The mechanism

`build_population` records `owners` **per spelling**. `normalize` folds spellings
onto one key. Three of the 414 keys have spellings that disagree — some derived
and owned, some declared-only and ownerless:

```
gpt41mini      gpt 4.1 mini -> openai/gpt-4.1-mini      gpt-4.1 mini -> ()
               gpt-4.1-mini -> openai/gpt-4.1-mini      gpt41mini    -> ()
               gpt4.1mini   -> openai/gpt-4.1-mini
gemini25pro    three spellings owned, `gemini 2.5pro` declared-only
claudehaiku45  three spellings owned, `claude-haiku-4-5` declared-only
```

`RegistrySurfaceResolver` looked the surface up like this:

```python
for candidate in self._population.surfaces:
    if normalize(candidate) == needle:
        matched = candidate
        break
```

`surfaces` is a **frozenset**, so "first" is iteration order, so it is
`PYTHONHASHSEED`. Measured:

```
PYTHONHASHSEED=3   RegistrySurfaceResolver("gpt-4.1 mini") -> mv_ebd5240e5f207506
PYTHONHASHSEED=1,2,4,5                                     -> None
```

**Same registry, same input, same fingerprint, different answer.** A claim either
attaches to `openai/gpt-4.1-mini` or is counted as an unresolved absence,
depending on the process that ran the batch. That is precisely the
reproducibility the fingerprint apparatus exists to provide, defeated inside the
function it protects — and it renders as an absence, which is the expensive
class (rule 6).

Two of the three colliding keys are in the labelled pool: row 14 `4.1 mini` and
row 22 `claudehaiku4.5`.

### The fix

Resolution is now by **normalised key**, with owners **unioned** across the
spellings that share it. Stable across seeds 1, 2, 3, 4, 5, 7 and 11.

The union is the honest read rather than a convenience. An unowned spelling is a
declared surface whose owner `build_population` **declined to guess** — that is
absence of information about the owner, not evidence that there is none. Three
spellings naming `openai/gpt-4.1-mini` and two saying nothing is one owner.

**My own measurement harness had the same bug** — `for cand in pop.surfaces` with
a strictly-greater tie-break — which is how it surfaced. Both are now sorted.

---

## 4 · The `ambiguous` asymmetry: the resolver gains the outcome

The question was sharp and the answer changed once the union landed.

**Before the fix**, owners were per spelling and derivation is injective, so no
spelling could have two owners. `several-owners` was unreachable: 0 of 1,247
surfaces, 0 occurrences over 1,297 posts. The labeller could select a category
the code could never return, and those rows could only ever disagree. The brief
is right about that.

**After the fix**, unioning by key makes it reachable. Over the 414 keys:

| owners per key | keys |
|---|---|
| 0 | 17 |
| 1 | 396 |
| **2** | **1** |

The one is `commandr082024`. `normalize` strips `+`, so `command-r+ (08-2024)`
and `command-r (08-2024)` collapse onto one key — two different Cohere models,
one spelling as far as matching is concerned. Verified live:

```
RegistrySurfaceResolver("command r+ (08 2024)") -> None
report.ambiguous = {'command r+ (08 2024)':
    ('cohere/command-r-08-2024', 'cohere/command-r-plus-08-2024')}
```

**So: the resolver gains the outcome, and the label stays.** Three reasons, in
order of weight:

1. **It is reachable and correct.** 1 key of 414, refused rather than guessed,
   which is exactly what rule 6 asks for. The mechanism producing it —
   `normalize` stripping `+` — is load-bearing and is not going away.
2. **The label option is well-populated anyway.**
   `names-a-model-we-cannot-identify` maps to *two* resolver outcomes, and the
   other one is common: `no-owner` accounts for **964 of 18,090** surface
   occurrences in the corpus. The option is answerable by the code today
   regardless of how rare ambiguity is.
3. **Zero occurrences is not zero reachability.** The corpus measured 0
   multi-owner occurrences, and that 0 was a property of the *indexing* rather
   than of the world (rule 7 — the figure was answering a question about how
   owners are stored, not about how people write). Dropping a label because a
   count is 0 is how a real category becomes an absence nobody audits.

What the brief identified as a permanent disagreement was real, and its cause was
the per-spelling indexing rather than the label vocabulary. Fixing the indexing
dissolves it.

The remaining `ambiguous`-labelled rows still disagree, but for the reason in
§2 of the previous memo: their surfaces are not in the population at all. That is
coverage, not vocabulary.

---

## 5 · The pool files, and one regression

### `commanda` — confirmed, and the field fix was overwritten

The re-label **landed**: row 49 now reads `resolves`, `labelled_at`
`2026-08-21T05:31:23Z`. Exactly one row moved across the whole file
(`resolves` 32→33, `not-a-model` 8→7), so nothing else shifted. Single-clear is
now 7/7.

**But the export also undid the previous round's fix.** The tool wrote a fresh
file at `entity-pool-50--labelled-by-anon.jsonl` with `labelled_by: "anon"` on
the `_meta` and all 50 rows. The rename was gone and the field was back.

Re-applied — one file, `entity-pool-50--labelled-by-anooj.jsonl`, no label
altered. **It will keep reverting.** Patching the artifact cannot hold, because
the tool is the source of truth and re-exports from its own state; the name has
to be set in the tool. Until it is, every export re-creates the `--anon` file
alongside the renamed one, which is the two-files-one-purpose hazard arriving by
a different door.

### Superseded, and now readable from the filename

Not superseded — **kept deliberately, and renamed to say which population they
describe**:

| file | status |
|---|---|
| `entity-pool-candidates--dc69d8725ccfe658.jsonl` | was `entity-pool-candidates.jsonl`. **Kept**: it is the parent of the labelled 50, and deleting it orphans their provenance. |
| `filter-pool-candidates--dc69d8725ccfe658.jsonl` | was `filter-pool-candidates.jsonl`. **Superseded** in use; kept only as the sibling of the run that produced the parent. |
| `entity-pool-candidates--b5744297e9210497.jsonl` | current |
| `filter-pool-candidates--b5744297e9210497.jsonl` | current |
| `entity-pool-control-negatives--b5744297e9210497.jsonl` | current; own retention date |

The unfingerprinted names were the actual hazard. Every pool file now carries its
population fingerprint, so "which is current" is answerable from the filename
without opening it, and two pools with one purpose can no longer look alike. If
the `dc69d…` pair should go rather than stay, that is a call to make once the
labelled 50 has been superseded by a re-draw — not before.

---

## 6 · Corrections to the previous memo

- **Agreement is 22/40 = 55.0%, not 20/40 = 50.0%**, with 18 disagreements not
  20. Two causes: the `commanda` re-label (+1) and the union fix, which resolves
  row 14 `4.1 mini` to `openai/gpt-4.1-mini` (+1). The 50.0% figure was also
  *unstable* — see §3.
- **`several-owners` is reachable**, contradicting "surface-occurrences with more
  than one owner: 0" as a statement about the world. It was true of the
  per-spelling index and false of the population once keyed.
- Per stratum now: `family-bare` 5/13, `spacing-variant` 9/10,
  `ambiguous-owner` 1/10, `single-clear` **7/7**.

---

## 7 - The ruling, recorded in the code

`collect/triage/entity.py` now carries it, because a reason that lives only in a
report is a reason that gets re-litigated by whoever finds the word list next.
Two headings: **THIS EXCLUSION IS A SPECIFICITY RULING, NOT A MATCHER RULE**, and
**WHAT WOULD ACTUALLY RECOVER `oqocfjv`**.

The argument that makes it a ruling rather than a measurement, and it is sharper
than "it buys nothing":

`contract/seed_models.yaml` **does** name a model for each bare word, on purpose,
with a comment saying it must resolve at family specificity and never at
snapshot. What it names:

```
opus   -> anthropic/claude-opus-5      specificity=family
sonnet -> anthropic/claude-sonnet-5    specificity=family
haiku  -> anthropic/claude-haiku-4-5   specificity=family
```

Now the row the proposal existed to recover. `sonnet` in *"LLM Comparison/Test:
New API Edition (Claude 3 Opus & Sonnet + Mistral Large)"*, **posted
2024-03-11**, about Claude 3. Resolving through the family word attaches that
engineer's comparison to **Claude Sonnet 5** - which did not exist when they
wrote it.

**That is not a vague claim about a line. It is a definite claim about the wrong
model**, which is what `surface_resolver.py` refuses ambiguity to avoid: *"an
unresolved claim is a counted absence, and a mis-resolved one is evidence against
the wrong model."* A version being *adjacent* is not the version the surface
*means*, and no window size closes that gap - `Claude 3` next to `Sonnet` tells
you the writer meant Claude 3 Sonnet, and the population's answer for `sonnet` is
Sonnet 5. The rule reads the context correctly and resolves incorrectly.

`oqocfjv` needs a different ruling entirely: **whether a family-specificity claim
may be stored and displayed at all**, and what a page says when it holds one.
That touches `judge/vet/weight.py`'s 0.3, `judge/curate/gate.py`, and rule 4's
display side. Not E1's alone, and not a matcher change.

### One citation corrected while checking it

`propose.py` said a family-specificity claim *"never counts as independent
corroboration"*. It does count. `judge/curate/gate.py:count` takes one
representative per voice and **does not read specificity at all**; the only place
specificity enters is `n_eff`, via `FUZZINESS_WEIGHT["family"] = 0.3`. So a
family claim is down-weighted to a third, not excluded. Corrected in place, with
a note that the exclusion is right for a stronger reason than the one written
there.

---

## 8 - The recall figure with its denominator, and I cannot reproduce 5 of 6,646

A recall claim off this pool measures the pool. That correction is right. But the
corpus figure I get is not the one quoted, so here is mine with its counting rule
attached.

**Counting rule:** each (document, bare word) pair once. A bare word is a bounded
occurrence of a `FAMILY_WORDS` member with **no population surface covering the
same position** - so `opus` inside `claude opus 4` is not counted, and `opus` in
*"which Opus"* is.

| | count |
|---|---:|
| surface occurrences the gate matches | 18,090 |
| bare family words it declines | 4,954 |
| **denominator - every mention the gate could see** | **23,044** |
| of the bare words, ones `seed_models.yaml` could attribute | **1,026** |
| ... `opus` 517, `sonnet` 379, `haiku` 130 | |
| documents affected | 692 of 1,297 |
| documents the gate would **newly keep** | 48 |

**1,026 of 23,044 = 4.45%**, over 1,297 Reddit posts every one of which was
retrieved by a query naming a model. Against matched mentions only,
1,026/18,090 = **5.67%**.

I cannot reach **5 of 6,646 = 0.08%** from any counting rule I tried, and I am
not going to adopt a figure I cannot derive - that is the failure this rule
exists to catch. If the numerator is "documents where a bare word is the *only*
model reference and the seed file names it", I measure **48**, not 5. Name the
rule and I will re-run it.

**And 4.45% is not negligible**, which matters for how the decision reads: the
answer is a ruling because the recovery would be a misattribution, not because
the cost is small. Those are different arguments and only the first survives.

### The over-sampling factor, also measured

| | |
|---|---|
| family-bare share of the 40 scoreable rows | 13/40 = **32%** |
| bare family words as a share of corpus mentions | 4,954/23,044 = **21.5%** |
| over-sampling factor by mention share | **~1.5x** |
| parent-pool quota | 50 of 200 = 25%, against 3,693 available |

By sampling *rate* against the `single-clear` stratum - 50/3,693 versus
30/13,435 - it is **6.1x**. I do not reach 50:1 on either reading. The direction
is right and unarguable: the stratum is over-weighted on purpose, so *"n of 36"*
or *"n of 40"* is a property of the quota, and any recall claim comes off the
corpus.

---

## 9 - The `ambiguous` ruling, taken

**Three-way label kept. `resolve()` scored binary. `names-a-line-not-a-version`
and `not-a-model` collapsed for comparison.**

The framing is the part worth recording, and it is now the first thing
`LABEL_OPTIONS` says: **a label records what the text names.** It is not a
prediction of what `resolve()` can return, and it must not be trimmed to match
the resolver's outcomes - that would make the golden set unable to disagree with
the thing it exists to measure.

Two labellers reached this from opposite ends. Yathu never used the middle
option; anooj used it for bare product lines like `chatgpt` where no version is
stated. *"Someone discussed a product line"* is not *"someone typed a word that
isn't a model"* - the first is evidence about a line, the second is noise, and
folding them together at **labelling** time is rule 4's confusion moved upstream.
So the distinction is recorded and never scored.

`RegistrySurfaceResolver` returns `str | None`. One id, or nothing - and it does
not distinguish *why* nothing. So scoring is binary and the middle option has no
column of its own.

The previous four-option set split the middle in two, a family word versus a
model we cannot pin down. That split cannot be scored either, so it bought
precision the comparison could not use. Three, with the middle one honest about
covering both.

### Re-run under collapsed scoring - 26/40 = 65.0%

```
                       resolve() returned
                     a model id     nothing     total
  label expects id           18          12        30
  label expects no            2           8        10
  total                      20          20        40
```

| | |
|---|---|
| **precision** | 18/20 = **90.0%** - of what the resolver resolved, how much the labeller agreed named one model |
| **recall** | 18/30 = **60.0%** - of what the labeller read as one model, how much the resolver got |
| **false positives** | **2** - the expensive direction |

Per stratum: `family-bare` 8/13, `spacing-variant` 9/10, `ambiguous-owner` 2/10,
`single-clear` 7/7. Deterministic across seeds.

**This is the first number here that means something.** The four-outcome scoring
was penalising rows where the label and the resolver were not answering the same
question: `codex`, `grok`, `chatgpt` and `claude 4` were all labelled `ambiguous`
and all correctly returned nothing, and all counted as disagreements. They agree.
14 disagreements, not 18.

**Both false positives are the same shape and neither is clearly the resolver's
fault** - `deepseek` in *"DeepSeek-R1-Lite-Preview"* and `glm` in *"glm 4.6"*.
The labeller read a product line; the resolver found a version elsewhere in the
document covering the word and resolved it. Reasonable people differ, and at
n=40 two rows is not a rate. The remaining 12 misses are the coverage story from
section 2 and the previous memo: 8 are surfaces the population does not contain,
3 are models the registry does not hold, 1 is ownerless.

## What changed

| File | Change |
|---|---|
| `collect/surface_resolver.py` | lookup by normalised key, owners unioned across spellings; the nondeterminism written up in the module docstring |
| `tests/test_surface_resolver.py` | the ambiguity forge now forges every spelling of the key; new test for one-owned-one-unowned |
| `fixtures/golden/entity-pool-50--labelled-by-anooj.jsonl` | `labelled_by` re-applied after the tool overwrote it; **no label altered** |
| `fixtures/golden/*--dc69d8725ccfe658.jsonl` | the two unfingerprinted pools renamed to name their population |
| `collect/triage/entity.py` | the specificity ruling, recorded where the word list is |
| `collect/registry/propose.py` | the "never counts as independent corroboration" overstatement corrected |
| `scripts/labelling_pools.py` | `LABEL_OPTIONS` reduced to three with the "records what the text names" framing; `SCORING` maps them onto the resolver's binary answer |
| `docs/measurements/entity-pool-labelled-resolve-run.txt` | regenerated, deterministic |
| `docs/measurements/family-word-adjacency-and-a-nondeterminism.txt` | the four-arm measurement, in full |

**No change to `FAMILY_WORDS`, `_admissible`, `rule_variants` or `resolve()`.**
The measurement says the rule is not worth building, and the code says building
it is a restructure.

**Suite: 1,922 passed** — every test that does not want a database. The ten files
taking the `test_dsn` fixture still hang in `psycopg.connect` during fixture
setup; environmental and pre-existing.
