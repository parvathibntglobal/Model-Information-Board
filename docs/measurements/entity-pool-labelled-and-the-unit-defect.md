# The 50-row entity pool, labelled — and the unit the pool never named

50 rows drawn from `entity-pool-candidates.jsonl`, hand-labelled 2026-08-21 by
`anooj`. `fixtures/golden/entity-pool-50--labelled-by-anooj.jsonl`.

**The labels are the ground truth and none of them were changed.** `resolve()`
is what is being measured. The pool's per-row `note` is what its builder expected
in August and is not the answer key.

Three findings. Two were defects in the pool and the third was a defect in the
question the pool asked. All three are taken, and one stratum is retired rather
than repaired.

---

## The denominators, first

| Figure | Population it was drawn from |
|---|---|
| 50 labelled rows | a stratified draw from 200 candidates, itself from 1,297 Reddit posts retrieved 2026-08-17 by the substitution sweep |
| 40 scored rows | the 50 minus the 10 whose `surface` is `""` |
| 748 qualifying negatives | the 750 control posts of `_control_sweep/`, collected 2026-08-18 |
| 1,103 ownerless matches | surface-occurrences over the 1,297 slice posts, current population |

**Every post in the substitution slice was retrieved by a query containing model
names.** That fact does most of the work below — it is why the negative class
cannot come from there. Reddit-only and short-form only. Nothing here is a rate
about a platform.

Per-stratum n is 7–13. At that size the 95% half-width is ±25pp or worse, so the
per-stratum splits show direction and not rates.

### The population fingerprint, and it moved

```
pool built at   dc69d8725ccfe658
                1337 surfaces (declared 23, mechanical 1263, vendor-drop 51)
                over 340 registry models and 55 declared

scored against  b5744297e9210497
                1247 surfaces (declared 23, mechanical 1173, vendor-drop 51)
                over 324 registry models and 55 declared
```

**The registry grew and the population shrank, and those are two facts.**
`model_version` holds 342 rows now against 340 then — two models added. The
population's model count fell to **324** because commit `d7892f2` landed between
the two and ruled that routes are not models: `is_route` excludes 18 rows, six
`openrouter/*` endpoints and twelve `~vendor/…-latest` floating pointers.
Surfaces fell 1,337 → 1,247 with them.

The labeller was shown a population this run does not use. That is not a flaw in
either — it is what the fingerprint exists for — but no number here means
anything without both fingerprints beside it.

---

## 1. `unresolvable` is retired, not repaired

All 40 rows of the parent pool, and all 10 that reached the labelled 50, carried
`surface: ""`. Three of the 10 were labelled `resolves` from the snippet alone,
which is the only sensible thing a person can do when asked whether the empty
string names a model.

### What it was meant to hold, and why the blank was not the real defect

Its docstring: *"no surface matches at all. **Real negatives**, without which
precision cannot be computed and the set measures only recall."* The branch:

```python
if not matched:
    r = row(UNRESOLVABLE, "", "no surface in the population appears here")
```

`matched` is `resolve(document_text, population)`, so the fact is per-document.
The blank was not the builder taking the wrong field — there is no field to take,
and `row()` already special-cased it. It was not an empty population either: 105
were available for a quota of 40, `shortfall: {}`.

The visible defect was a **unit mismatch** — a per-document fact in a per-surface
row, printed by a tool that assumed every row was about a string.

### But the unit was the symptom. The corpus is the disease

**A sampler that only reaches documents which matched a surface cannot produce a
document where nothing matches.** Every post in `_substitution_slice/` arrived
through a query containing model names. So a slice document that matches nothing
is not a document about something else — it is a document the *retrieval* thought
named a model and the *population* disagreed.

That is a real measurement, of the gap between query and population, and it is a
different thing from a negative. Fixing the unit in place would have drawn from
the same 1,297 posts and produced the same 40 blanks with better field names.

So the branch is gone, and the empty branch is left in the source with the reason
in it, so that the next person to notice the pool has no negatives finds the
argument rather than re-adding the stratum.

### Rebuilt from the control corpora — counted before drawn

`_control_sweep/` is the only set of documents in this repository chosen for
having nothing to do with models: 450 Tier 1 posts (`programming`, `webdev`,
`devops`, `rust`, `golang`, `sysadmin`) and 300 Tier 2 (`AskReddit`,
`todayilearned`, `movies`, `cooking`), collected 2026-08-18 to calibrate triage
survival. `control-and-reshape.md` already used them for this exact question —
the `saba`-inside-*"was a bad"* defect is a false positive on this corpus, which
is a mislabelled negative.

**How many qualify, before any were drawn:**

| | posts | qualify | rate |
|---|---:|---:|---:|
| Tier 1 general-technical | 450 | **448** | 99.6% |
| Tier 2 non-technical | 300 | **300** | 100.0% |
| **both** | **750** | **748** | **99.7%** |

So the stratum is 748, and the binding constraint is the target rather than the
corpus. Tier 2 at exactly 300 of 300 is the same instrument control passing that
`control-and-reshape.md` reports as 0.0% survival — nothing about models in a
corpus about movies.

The two Tier 1 posts that do match name real models (`gpt 5`, `deepseek v4 flash`,
`gpt 5.6 sol`, `claude opus`) in programming subreddits, which is the residual
bias the control was built to measure, not a matching defect.

Drawn: **40, twenty from each tier.** Equal rather than proportional, because
the tiers measure different things — Tier 1 the bias, Tier 2 the instrument — and
a proportional draw would let the larger tier set the character of the stratum.
Even stride over each tier in id order, deterministic. 33 of the 40 run past 80
characters; that split is reported rather than engineered, since selecting for
body text would pick the corpus's chattier half and quietly change what the
stratum measures.

**The deletion date travels with the copy.** Both manifests carry
`delete_after: 2026-11-16` — Data API Terms 3.2 is unresolved against the
immutable store, which is precisely why these posts sit outside `raw/`. A snippet
copied into a committed fixture outlives its source unless the obligation is
copied too, so it is on every row and in the header, and these rows are in
`fixtures/golden/entity-pool-control-negatives--b5744297e9210497.jsonl` — their
own file, so it can be dropped whole on that date.

### The other rebuild items

The ownerless case — a surface the population holds that no registry id derives —
had no bucket at all. `elif len(owners) == 1` dropped it, and the sibling test
above it read `() == ()` as *same owner*, so **5 of the parent pool's 40
`spacing-variant` rows** were ownerless surfaces under an expectation of
"resolves": `4.1 mini`, `claude haiku`, `claude opus`, `claude sonnet`,
`claude-haiku-4-5`. It is now `matched-no-owner`, quota 40, availability **1,103
occurrences over 22 distinct surfaces** (`claude opus` 274, `claude sonnet` 193).

The `ambiguous-in-context` branch tested `normalize(surface) in normalize(text)`
with no boundary map — the third site of the `free`-inside-`freeze` defect, and
the first one written *after* the fix landed. It now delegates to the shared
matcher, and `tests/test_surface_matching_boundaries.py` guards the third site
the way it already guarded the second.

Every row now carries `unit` (`surface` | `document`) and its own `question`
text, and the pool header carries `label_options`. The tool renders those and
holds no list of its own, so a stratum, its question and its options cannot drift
apart.

```
available  family-bare 3501  spacing-variant 4906  ambiguous-in-context 557
           matched-no-owner 1103  single-clear 12081
taken            45                40                    40
                 40                35                              = 200
control-names-nothing: 748 qualify, 40 taken (20 tier1, 20 tier2)
```

---

## 2. The option text was wrong, and the labels were right

### Settled against the code

**`collect/triage/entity.py:258` — `resolve(text, population)`** normalises the
*whole* string it is handed with the boundary map and returns every population
surface occurring in it. `names_a_model()` hands it `Document.text`. It reads the
normalised **document**.

**`collect/surface_resolver.py` — `RegistrySurfaceResolver.__call__(surface)`**
tries an exact normalised match, then falls back to `resolve(cleaned, population)`
where `cleaned` is the surface. Surface unit, and the only thing on the store path
that turns a string into a `model_version.id`.

So *"the string in its document"* is what `resolve()` does, **the 14 are correct,
and the strata were asserting something the code does not**. The labels stand.

### What changed instead

`ambiguous-owner`'s note read *"attribution cannot be decided from the string
alone"*. That phrasing invited a reader to decide it from the string alone and
got exactly that — and then nine labellers' answers looked like a labelling
problem. It was a naming problem.

**The stratum is renamed `ambiguous-in-context`**: ambiguity that survives
reading the document is the fact it holds. `family-bare` keeps its name — it is
accurate about what it *selected*, and its question now says "read the document"
so the two readings stop being silently swapped. `spacing-variant`,
`matched-no-owner` and `single-clear` are unchanged. The retired stratum's
replacement is `control-names-nothing`, which names both its unit and its corpus.

**The question now hands over the document and allows the answer to still be
"cannot":**

> Read the document, then say which ONE model the highlighted string means. If
> the document does not narrow it to one, say so — the registry holds several
> candidates and derives the string from none of them, and the document is
> allowed to leave that unresolved.

**The four label options** replace `resolves` / `ambiguous` / `not-a-model`.
`ambiguous` was carrying three incompatible facts — several owners, no owner, and
the labeller's own uncertainty — and 6 of the 40 scored rows used it, no two
meaning the same thing. Each option now names the unit inside the option.

| Option | Means |
|---|---|
| `names-one-model` | reading this document, the string names exactly one specific version |
| `names-a-family-only` | names a line or tier; even with the document there is no version to attach a claim to |
| `names-a-model-we-cannot-identify` | a person can see a model is named; **the ambiguity survives reading the document** |
| `not-a-model` | not a model reference at all |

`mistral 3` is the worked example, and it is in the option's own help text where
a labeller will see it:

> The registry holds `mistral-medium-3`, `mistral-medium-3-5` and
> `mistral-medium-3.1`, and derives the surface `mistral 3` from none of them.
> Reading the document does not settle it and makes it worse: the post says
> *"Mistral just went nuclear with their Mistral 3 release … They released FOUR
> models at once"*. Four candidates in the document, three in the registry, and
> no way to pick. Choose this option **after** reading, not instead of reading.

One correction to the example as briefed: the registry holds no `mistral-large-3`
or `mistral-small-3`. It holds `mistral-large-2512` and `mistral-small-2603`, and
the three `mistral-medium-3*` ids above are the actual candidate set. The shape of
the point is right and the real case is stronger — the document adds a fourth
candidate rather than resolving to one.

### The sharpest case, and it is not about units

All nine `ambiguous-owner` rows labelled `resolves` come back `no-match`, and the
reason is that **their surfaces are not in the population**. They come from the 49
`attested-gap-ambiguous` entries in `observed-surfaces.json`, of which the
builder's own docstring records 48 are reachable by no derivation.

Corroborating, over 1,297 posts: **surface-occurrences with more than one owner:
0.** Derivation is injective. `RegistrySurfaceResolver`'s ambiguity branch is
unreachable from derived surfaces, and every real ambiguity is the attested kind.

So `gemini 3 pro` in *"Google is launching Gemini 3 Pro today"* is not
document-versus-string. It is *"is this a model in the world"* versus *"does our
registry derive this string"* — which is what
`names-a-model-we-cannot-identify` exists to say, and what the old three options
could not.

---

## 3. The two single-clear rows

### `auto` inside `&auto=webp` — real, and the boundary map is not the defence

Row #47, `candidate_models: ['openrouter/auto']`, labelled `not-a-model`. The
snippet is a Reddit image URL.

```
normalize_with_boundaries("…png?width=828&auto=webp&s=abc")
  → 'httpsiredditxjpgwidth640autowebpsabc'
  at=24  starts=True  ends=True   → BOUNDED MATCH PASSES
```

`&` and `=` are non-alphanumeric, so they read as word boundaries. Every URL
query parameter looks like a word to this function.

It scores as agreement today only because `openrouter/auto` is now excluded as a
route — the pool (`4f960ac`) predates the ruling (`d7892f2`). **The fix was
incidental.** The available control is to strip URLs before matching, and I have
not done it: it changes `resolve()` on the gate path and wants its own
measurement of what it costs in mentions that legitimately sit inside links.

### `commanda` from *"Cohere: Command (A)"*

Row #49, labelled `not-a-model`; `normalize("Cohere: Command (A)")` →
`coherecommanda`, owner `cohere/command-a`, and `resolve()` returns it.

**Left exactly as labelled**, and anooj re-labelled it `resolves` on
2026-08-21 — a golden set someone else corrected is not a golden set. It now
agrees, and `single-clear` is 7/7.

---

## 4. `resolve()` against the labels

Scored **40 of 50**. The other 10 are the retired stratum's blanks — no string to
hand a resolver. (This is 40, not 36. Every one of the 40 occurs in its own
snippet; only `pro`, row 13, occurs unbounded-only. If four were meant out on
another ground, name them and I will rescore.)

**Population fingerprint: `b5744297e9210497`** — 1247 surfaces (declared 23,
mechanical 1173, vendor-drop 51) over 324 registry models and 55 declared.

### resolve() has four outcomes; the label set has four options; they do not line up

| resolve() outcome | label option |
|---|---|
| `one-owner` | `names-one-model` |
| `several-owners` | `names-a-model-we-cannot-identify` |
| `no-owner` | `names-a-model-we-cannot-identify` |
| `no-match` | `names-a-family-only` **or** `not-a-model` |

That last row is a finding, not a defect. `resolve()` returning nothing means
only *"this population holds no model here"*. It cannot tell a family word from a
coincidence of spelling, and it must not: **rule 4 requires the display to
separate "nobody has discussed this" from "not a model", and that separation is a
human judgement the code never makes.** A `no-match` prediction is therefore
scored as agreeing with either of those two labels.

The old three options map forward as `resolves → names-one-model`,
`not-a-model → not-a-model`, `ambiguous → names-a-model-we-cannot-identify`.

### Overall agreement: 20/40 = 50.0%

> **SUPERSEDED 2026-08-21, and the figure was unstable when written.** The number
> is now **22/40 = 55.0%** with 18 disagreements. Two causes: anooj re-labelled
> `commanda`, and a nondeterminism in `RegistrySurfaceResolver` was fixed — the
> lookup scanned a frozenset and broke on the first spelling matching the
> normalised key, so `gpt-4.1 mini` resolved at `PYTHONHASHSEED=3` and came back
> `None` at 1, 2, 4 and 5. Three runs of this scoring script gave 50.0%, 52.5%
> and 55.0%. `docs/measurements/family-words-and-a-nondeterminism.md`.
>
> Also corrected there: "surface-occurrences with more than one owner: 0" was
> true of the per-spelling index and false of the population once keyed. Per
> stratum is now `family-bare` 5/13, `spacing-variant` 9/10, `ambiguous-owner`
> 1/10, `single-clear` 7/7.

```
  label \ resolve() |     one-owner  several-owners      no-owner      no-match   total
  one-model         |            16               0             2            11      29
  cannot-identify   |             2               0             0             4       6
  family-only       |             -               -             -             -       0
  not-a-model       |             1               0             0             4       5
  total             |            19               0             2            19      40
```

`family-only` is empty because the three-option set had no such option — which is
the measurement arguing for the new one. Six rows used `ambiguous` and four of
them are family words in documents that do name a version.

| stratum | agreement |
|---|---|
| `family-bare` | 5/13 |
| `spacing-variant` | 8/10 |
| `ambiguous-owner` | 1/10 |
| `single-clear` | 6/7 |

### Every disagreement — 20 of 40

Full text with snippets in `entity-pool-labelled-resolve-run.txt`.

| # | row | stratum | surface | label | resolve() | why |
|---|---|---|---|---|---|---|
| 1 | 2 | family-bare | `codex` | ambiguous | no-match | *"Codex logic"* in an unrelated post |
| 2 | 4 | family-bare | `grok` | ambiguous | no-match | bare family word, no version near |
| 3 | 6 | family-bare | `opus` | resolves | no-match | *"Claude 3 Opus"* — **registry holds no claude-3-opus** |
| 4 | 7 | family-bare | `sonnet` | resolves | no-match | same document, same gap |
| 5 | 8 | family-bare | `chatgpt` | ambiguous | no-match | product name, not a version |
| 6 | 9 | family-bare | `deepseek` | ambiguous | one-owner | `deepseek-r1` covers it — the label is the cautious one |
| 7 | 10 | family-bare | `glm` | ambiguous | one-owner | `glm 4.6` covers it |
| 8 | 12 | family-bare | `mixtral` | resolves | no-match | **registry holds no mixtral row** |
| 9 | 14 | spacing-variant | `4.1 mini` | resolves | no-owner | ownerless — mis-bucketed by `()==()` |
| 10 | 17 | spacing-variant | `claude sonnet` | resolves | no-owner | ownerless — mis-bucketed by `()==()` |
| 11 | 24 | ambiguous-owner | `claude 4` | ambiguous | no-match | not in the population |
| 12 | 25 | ambiguous-owner | `gemini 2.5` | resolves | no-match | not in the population |
| 13 | 26 | ambiguous-owner | `gemini 3 pro` | resolves | no-match | not in the population |
| 14 | 27 | ambiguous-owner | `gemini 3.5` | resolves | no-match | not in the population |
| 15 | 28 | ambiguous-owner | `gpt 3.5` | resolves | no-match | not in the population |
| 16 | 30 | ambiguous-owner | `mistral 3` | resolves | no-match | not in the population — the worked example |
| 17 | 31 | ambiguous-owner | `qwen3.6` | resolves | no-match | not in the population |
| 18 | 32 | ambiguous-owner | `claude 5` | resolves | no-match | not in the population |
| 19 | 33 | ambiguous-owner | `gemini 3` | resolves | no-match | not in the population |
| 20 | 49 | single-clear | `commanda` | not-a-model | one-owner | anooj's to re-label; left standing |

Row #5 `mini` in *"Why GPT-4o mini beats Claude 3.5 Sonnet"* and row #11 `kimi`
in *"Kimi K2"* now **agree** — they are the document effect the option text was
missing, and there are two of them plus rows 9 and 10 pointing the other way.

**Reading the document is worth less than the framing suggested, and the reason
is worth more.** Of the 20 remaining disagreements, 9 are surfaces the population
does not contain, 3 are models the registry does not hold at all
(`claude-3-opus`, `mixtral`), and 2 are the ownerless bug. Fourteen of twenty are
registry and population coverage, not resolution logic. The option text was still
wrong and the labels were still right; it was just never the largest thing in the
number.

---

## 5. A defect found by running the report

`RegistrySurfaceResolver` counted an **ownerless** surface as **ambiguous**:

```python
owners = self._population.owners.get(matched, ())
if len(owners) != 1:
    self.report.ambiguous[cleaned] = tuple(owners)   # tuple(()) == ()
```

Both return `None`, so nothing was mis-stored. **The report was wrong**, and the
report is the entire reason the class exists — it was saying *"several models
answer to this spelling"* about a surface no model answers to, with an empty
candidate tuple beside it.

Scale: 1,103 ownerless occurrences and **0** with more than one owner. Anyone
reading `report.ambiguous` to decide whether ambiguity was worth solving would
have been reading entirely the other thing. Rule 6 in the counting rather than
the data. Split into `report.no_owner`, named in `summary()`, test added.

---

## What changed

| File | Change |
|---|---|
| `fixtures/golden/entity-pool-50--labelled-by-anooj.jsonl` | renamed from `--anon`; `labelled_by` → `anooj` on the `_meta` and all 50 rows. **No label altered.** |
| `scripts/labelling_pools.py` | `unresolvable` retired; `ambiguous-owner` → `ambiguous-in-context`; `matched-no-owner` added; `control-names-nothing` built from `_control_sweep/`; `unit`, `question` and `delete_after` per row; `LABEL_OPTIONS` in the header; bounded ambiguous match; sibling test requires an owner |
| `fixtures/golden/entity-pool-candidates--b5744297e9210497.jsonl` | regenerated, fingerprint in the name |
| `fixtures/golden/entity-pool-control-negatives--b5744297e9210497.jsonl` | new — 40 negatives, own file, `delete_after: 2026-11-16` |
| `fixtures/golden/filter-pool-candidates--b5744297e9210497.jsonl` | regenerated alongside |
| `collect/surface_resolver.py` | `report.no_owner` split out of `report.ambiguous` |
| `tests/test_surface_resolver.py` | test for the split |
| `tests/test_surface_matching_boundaries.py` | guards the third boundary call site |
| `docs/measurements/entity-pool-labelled-resolve-run.txt` | the run, in full |

The originals `entity-pool-candidates.jsonl` and `filter-pool-candidates.jsonl`
are left in place — the first is the parent of the labelled 50 and deleting it
would orphan their provenance.

**Suite: 1,921 passed** — every test that does not want a database.
`tests/test_blog_fetch_db.py` and the nine other files taking the `test_dsn`
fixture hang in `psycopg.connect` during fixture setup because no test Postgres
is up here. The hang precedes any changed code and none of those files touch what
changed; it is environmental and pre-existing. Somebody with the test database up
should confirm.
