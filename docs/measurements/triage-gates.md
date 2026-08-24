# E4's hard gates, and the population problem underneath them

**Three of six gates built. The entity gate's verdict moves 385 documents in
1,297 — 29.7% of the corpus — on the alias population alone, with no document
changing. So a triage verdict is not reproducible from the document, and the
population needs an identity.**

*Engineer 1 · 1,297 Reddit posts · 340-model registry (staging) · no fetch · 2026-08-18*

> `collect/triage/` held `specificity.py` and nothing else. The floor was
> measured removing 7.7%, so the hard gates were expected to carry nearly all of
> the 10–15% survival target, and none of them existed.

---

## 0 · The caveat that governs every figure here

```
1,297 distinct Reddit posts, recovered from 120 raw payloads in
_substitution_slice/, retrieved 2026-08-17 by the substitution sweep

EVERY POST WAS RETRIEVED BY A QUERY CONTAINING MODEL NAMES.
```

The corpus is pre-filtered for exactly what the entity gate tests. **Nothing
below calibrates the 10–15% survival estimate**, and no survival figure here
should be compared to it. What the corpus can do is rank the gates against each
other and expose the population effect, which is what it is used for.

Two further limits: Reddit and short-form only — GitHub config lines and blog
prose name models differently — and `raw_store/` is absent, so the 285-document
GitHub+blog corpus behind the 7.7% figure is gone and could not be re-run.

---

## 1 · What got built, and what deliberately did not

| gate | state | why |
|---|---|---|
| pure link post | **built** | `is_self` false and no commentary of the poster's own |
| <15 tokens, no artifact | **built** | reuses `specificity`'s four text components |
| no resolvable model entity | **built** | §2, §3 |
| out of window | **built, usually unavailable** | needs a surface to resolve to exactly one model |
| wrong language | **not built** | no detector installed, none declared in `pyproject.toml` |
| known-bot list | **not built** | rule 5 puts the list in `contract/`, and it is not there |

### A gate that cannot run has not passed the document

This is the design decision the module is arranged around. `triage_verdict` is
`kept | dropped`, and a document cleared by three gates is not in the condition
of one cleared by five — but it writes the same row. So every verdict carries
`unavailable`, naming the gates that did not run, and every survival figure
prints:

```
GATES THAT DID NOT RUN: wrong-language (1297), out-of-window (1297),
known-bot (1297). This survival rate is an UPPER BOUND - documents these
gates would have dropped are counted as kept.
```

Three gates return `None` rather than `False` where they cannot decide, and the
distinction is tested in each case: no allow-list, no detected language, no bot
list, no owner for a matched surface, no window flag for a named model. An empty
bot list is a different statement from no bot list, and both are tested.

**Every gate runs on every document — no short-circuit.** Stopping at the first
rejection would make `unavailable` mean two things at once, "cannot run" and
"not reached", and the whole value of the field is that it means only the first.
It also gives `/filtered` every trigger a document hit rather than the earliest,
which is what *"sorted by how close it came to passing"* needs.

---

## 2 · The union population

`build_population` unions three sources and excludes bare family words from all
of them.

| part | surfaces | what it buys |
|---|---|---|
| mechanical, over all 340 registry ids | 1,263 | the gate tracks releases: `qwen3.8-27b` is resolvable the night it is polled |
| vendor-drop rule | +51 | the rule the corpus supplied — people write `opus 5`, not `claude opus 5` |
| declared, `contract/seed_models.yaml` | +23 | 27 hand-written surfaces no derivation reaches |

**1,337 surfaces, fingerprint `dc69d8725ccfe658`.**

The declared part is not redundant, and this is the finding that decided the
design. Surfaces reachable by no derivation:

```
reorderings the rule refuses        flash 2.5 · pro 2.5 · gemini flash 2.5
letter-prefixed versions            r1 · deepseek reasoner
tier vocabulary nothing derives     mistral large 3 · deepseek v4 · v4 flash
```

A registry-only population rejects a document naming `deepseek r1`. Dropping the
declared list would be discarding human judgement the corpus has corroborated.

Bare `opus`, `sonnet` and `haiku` are declared and still excluded: 62% of
family-word mentions carry no version, so a bare family word names a line rather
than a tier, and `classify_specificity` would rank the resulting claim `family`
— one that can record a claim and never lift a cell. The gate would pass a
document that cannot help.

---

## 3 · The population problem, measured

Same 1,297 documents. Same code. Only the surfaces differ.

| population | surfaces | survival | entity gate drops |
|---|---|---|---|
| hand-written only (11 seeded models) | 59 | 693 / 1,297 = **53.4%** | **552** |
| registry union | 1,337 | 1,078 / 1,297 = **83.1%** | **105** |

**385 documents — 29.7% of the corpus — change verdict on the alias population
alone.** `qwen 3.8 27b` is the case: DROPPED under the hand-written list, KEPT
under the union, with nothing about the document different.

### So which should the gate read — and the answer is neither, alone

Both inputs move:

- The **alias table** is append-only but human-driven. It holds 7 models today
  and 64 once the review artifact lands. Its verdict changes when a person edits
  a file.
- The **registry** is machine-driven and grows nightly. Deriving from it is what
  makes the gate track releases — and also makes tonight's verdict differ from
  last night's.

A triage verdict is therefore **not reproducible from the document**. It is
reproducible from *(document, population)*, so the population has to be
something you can write down:

```python
SurfacePopulation.fingerprint   # sha256 over the sorted surface set, 16 hex
```

`pipeline_version` does not cover this. It tracks what `collect/` *does*, and
this gate's answer changes when the registry grows without a line of code
changing — two runs at the same `pipeline_version` can legitimately disagree.
Only the fingerprint makes that visible instead of silent.

---

## 4 · The funnel, at its right size

Registry union, all gates, no short-circuit:

| gate | drops |
|---|---|
| pure link post | 144 |
| no resolvable entity | 105 |
| <15 tokens, no artifact | 89 |
| **survival** | **1,078 / 1,297 = 83.1%** |

Against a 10–15% target — and §0 says why that comparison is not available. Two
of six gates never ran, and the corpus was retrieved by model-name queries.

Two observations that do survive the bias:

**The length gate drops 89 and is not a filter.** It is a correctness guard, and
its value is entirely in the conjunction: `TypeError: 'NoneType' object is not
subscriptable` is a complete bug report in eleven tokens.

**"Pure link post" is a definition, and it cost 392 documents to get right.** Of
536 link posts, 392 carry commentary in `selftext`. Dropping all 536 would
discard the part an engineer actually wrote; only the 144 with none are dropped.

### One bug this found in itself

The first version of the length gate defined "artifact" with a private regex,
and `\bError\b` does not match inside `TypeError` — the single most common
artifact in the corpus read as absent. It now reuses `specificity`'s four
text-only components, which are contract-backed and already tested. Two
definitions of one concept drift; that is what drifting looks like.

---

## 5 · Raised as contract, not written

`contract/tables.sql` and `contract/registry.yaml` are untouched. Three things
need a ruling before the gates can be wired into a nightly run.

**1 — `document` has nowhere to record the population.** The verdict is not
reproducible without it. Proposed:

```sql
-- Which surface population the entity gate resolved against.
-- NOT covered by pipeline_version: that tracks what collect/ does, and this
-- gate's answer changes when the registry grows with no code change.
triage_population   text,
```

**2 — `document` has nowhere to record gates that did not run.** `filter_reasons`
is why a document was dropped; this is which questions were never asked. Folding
them into one array would make "dropped for language" and "language never
checked" the same row. Proposed:

```sql
gates_unavailable   text[],
```

**3 — the language allow-list and the bot list, if the gates are to exist at
all.** Both are filter rules and rule 5 puts them in `contract/`. The language
gate additionally needs a dependency decision: no detector is installed and none
is declared. `document.lang` is already a nullable column with nothing
populating it.

---

## 6 · What would revise this

- **An unfiltered sweep.** A sample of a subreddit's recent posts with no query
  terms is the only thing that can calibrate 10–15%, and nobody has fetched one.
  Until then the 2σ triage alert has no baseline it can safely arm against —
  a baseline collected while two gates are missing moves when the gates land,
  not when the world changes.
- **The two missing gates.** Both are contract decisions before they are code.
- **Engineer 2's labelling sets.** `fixtures/golden/filter-pool-candidates.jsonl`
  carries each document's gate verdict, so her labels measure the gates directly
  rather than in the abstract. Disagreement is the signal that pool exists for.
- **A GitHub and blog corpus.** §0's platform limit is the most likely way these
  numbers mislead: `deepseek r1` is unattested in Reddit prose and may be the
  common form in a config line.
