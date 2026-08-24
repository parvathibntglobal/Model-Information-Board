# Blog evidence reached the database, and six of eight claims are mis-attributed

**First blog claims ever stored: 8. Cells 2 → 7, models with a cell 1 → 5.**

**And the substring defect wrote six false attributions.** Five `GPT-5.6`
variants are filed as `openai/gpt-5`, and one claim naming three models is filed
against one of them. Nothing renders wrongly today because all seven cells are
`insufficient` — but the rows are in a shared database and they are wrong.

*Engineer 1 · 2026-08-21 · 44 documents, two runs, ~$0.11*

---

## 0 · Cost, and which ratio — because that was the finding

```
corpus            44 Willison blog contexts, 70,859 chars
ratio used        5.83 chars/token
estimate          96,590 input tokens  (12,155 content + 44 x 1,919 prompt)
```

**5.83, not 2.87, and deliberately.** The two measured ratios are per-corpus:
5.83 on Reddit comments and Willison's link-blog prose, 2.87 on engineering posts
full of code and JSON. This corpus is the first of those — Willison averages
1,610 chars per document, short prose link-blog entries — so 5.83 is the
corpus-appropriate figure. Had I used 2.87 here I would have doubled the
estimate for text that does not justify it.

The point of recording two ratios was to stop one being reused blind. Stating
which and why is the whole mechanism, so: **5.83, because this is prose.**

**Actual spend was about twice the estimate, and it was my defect, not the
ratio's.** The first run keyed `DocumentFacts` by `thread_context_id` where the
pipeline looks it up by `document_id`, so all 44 documents extracted, produced
claims, and had every one skipped:

```
no document facts for blog:https://simonwillison.net/...; claim skipped
rather than weighted from defaults
```

**The log line is correct and that is why it cost a run.** The pipeline behaved
exactly as designed — refusing to weight from defaults is the 2026-08-21 ruling
working — and a correct refusal reads identically whether the facts are missing
because nothing supplies them or because the caller keyed the dict wrong. Two
runs, ~$0.11 total.

---

## 1 · The premise: extraction never reads the population

**Nothing needed re-running against "324 models instead of 12", because the
resolutions already ran against 342.**

```
model_version rows on staging          342, all provenance='polled'
population built for every resolution  c511fceb6b7fb3df, 1385 surfaces, 342 models
seed_models()                          11, and it is ADDED to the DB population,
                                       not used instead of it
```

And structurally: **`Pipeline.run_all` takes `resolve_surface` as a parameter
applied *after* extraction.** The extractor emits a `surface` string and never
sees the registry. So a bigger population cannot change what extraction
produces — only what resolution does with it, and that measurement was already
against the full 342.

So the `9 of 176 resolve` figure reported previously **was** the after-state. The
re-run was needed to get quote offsets for storage, not to change resolution.

---

## 2 · Before and after

```
                        BEFORE   AFTER
claim                        4      12      +8, all blog
claim_weight                 4      12
cell                         2       7
models with any cell         1       5
```

```
claims by model and capability
  anthropic/claude-fable-5      code.generation         reddit  2
  anthropic/claude-fable-5      over_refusal            reddit  2
  anthropic/claude-haiku-4.5    instruction.adherence   blog    1
  anthropic/claude-opus-4.6     code.generation         blog    1
  anthropic/claude-sonnet-5     instruction.adherence   blog    1
  openai/gpt-5                  code.generation         blog    3
  openai/gpt-5                  summarization.fidelity  blog    2
```

`subjects_inherited = 3`, derived and logged rather than stored, as ruled.
Resolver: 8 surfaces resolved, 0 ambiguous, 0 no-owner.

### ⚠ Six of the eight are wrong, and here is the list

```
Codex Desktop running GPT-5.6 Sol Ultra  -> openai/gpt-5     WRONG
GPT-5.6 Sol Ultra                        -> openai/gpt-5     WRONG
GPT-5.6 Sol Pro                          -> openai/gpt-5     WRONG
GPT-5.6 Luna                             -> openai/gpt-5     WRONG
GPT-5.6                                  -> openai/gpt-5     WRONG
Claude Fable 5, Opus 5, or Sonnet 5      -> claude-sonnet-5  WRONG (3 named, 1 picked)
Opus 4.6                                 -> claude-opus-4.6  correct
Claude Haiku 4.5                         -> claude-haiku-4.5 correct
```

**`gpt-5` matches inside `gpt-5.6`** — the version-substring defect, now written
to the database rather than measured beside it. And a surface naming three models
resolved to one, silently, because `resolve()` returns longest-first and the
caller takes a single answer.

I refused this rollup twice on exactly this ground. Running it on instruction was
right — *the refusal was a prediction and this is the measurement* — and the
prediction held.

**Nothing false is on a page**: all 7 cells are `insufficient`, so every rendered
phrase is *"One person mentioned … — not yet corroborated"*, which is true of a
mis-attributed claim as much as a correct one. The hazard is later: a real
`openai/gpt-5` claim arriving would find five phantom voices waiting to
corroborate it.

**Recommended, and it is your call because it destroys the run:**

```sql
DELETE FROM claim WHERE id IN (SELECT id FROM claim WHERE model_version_id
  IN (SELECT id FROM model_version WHERE canonical_id IN
      ('openai/gpt-5','anthropic/claude-sonnet-5')));   -- 6 rows, then recompute cells
```

I have not run it. The alternative — fix the resolver first, then re-run — costs
another $0.05 and leaves nothing wrong in the meantime.

---

## 3 · What each model page renders

```
model                          caps  reported  unreported  published  insufficient
anthropic/claude-fable-5         12       2         10          0           2
anthropic/claude-haiku-4.5       12       1         11          0           1
anthropic/claude-opus-4.6        12       1         11          0           1
anthropic/claude-sonnet-5        12       1         11          0           1
openai/gpt-5                     12       2         10          0           2
TOTAL, the 5 models with a cell  60       7         53          0           7

337 other models                 12       0         12          0           0  each
```

**Zero published cells, on any page.** Seven sentences on the whole board, all of
the form *"One person mentioned X — not yet corroborated"*.

The board went from 2 sentences on 1 model to 7 sentences on 5 models. That is
the honest description of what the rollup put on screen.

---

## 4 · The `unreported` finding: two states, one sentence

**`unreported` renders identically for a capability nobody discussed and a model
nothing has ever been extracted for. Those are different states and a customer
cannot tell them apart.**

```
anthropic/claude-fable-5    over_refusal  reported      2 claims exist
anthropic/claude-fable-5    ops.latency   unreported    documents were read,
                                                        nothing said this
openai/gpt-4o-mini          ops.latency   unreported    no document has ever
                                                        mentioned this model
```

Those last two render the same. And 337 of 342 models are in the third state
entirely — **99% of the board is "unreported" because nothing was ever read
about them**, not because readers were silent.

`judge/pages/model.py` already knows this is a problem and solves half of it:

```python
@property
def unreported(self) -> bool:
    return not self.slices
```

and its docstring: *"cells I have" collapses `unreported` into `insufficient` and
reports "no evidence"*. So the three-way split published / insufficient /
unreported exists and is correct. **What is missing is a fourth state**, and it
is the difference between *nobody said it* and *nobody looked*.

### What the page would need

The distinguishing fact is **whether any document about this model was ever
read** — and it is not in `cell`, which only exists where a claim exists. Three
things, in increasing cost:

1. **a per-model corpus count** — how many documents mention this model at all,
   resolvable from the population against stored documents. Distinguishes
   *"12 documents mention it and none discussed latency"* from *"no document has
   ever mentioned it"*. This is a **`collect/` figure** — the population and the
   documents are both ours — and it is a read, not a schema change.
2. **a fourth rendered state**, e.g. `unexamined`, with its own sentence. *"No
   document we have read mentions this model"* is a true and different statement
   from *"Nobody has publicly discussed latency"*. **Engineer 2's**, in
   `pages/model.py` and `curate/phrases.py`.
3. **the coverage page carrying it**, so 337 unexamined models are visible as a
   coverage fact rather than 337 pages of apparent silence.

### Whose it is

**Split, and the split is clean.** The *number* is `collect/`'s — I can supply
"documents mentioning this model" from the population without a schema change or
a model call. The *rendering* is Engineer 2's, and it is a rule-4 decision rather
than a display preference: **rule 4 says absence of evidence must never read as
evidence of capability, and today it also does not distinguish absence of
evidence from absence of looking.** That second gap is one the rule does not
currently name, and it is on the page a customer reads.

Proposed to Engineer 2 with the count attached rather than as a request for a
column. Nothing here is blocked on it — but 337 pages currently say the same
thing about a model nobody has ever swept for and a model that was read and found
quiet, and only one of those deserves a reader's confidence.

---

## What changed

| | |
|---|---|
| database | 8 blog claims, 8 weights, 5 new cells. **6 claims mis-attributed** (§2) |
| `docs/measurements/extraction-token-counts.md` | already carries the two per-corpus ratios; this run is the first use of the rule and it worked |
| nothing in code | the rollup needed no triage writer — `DocumentFacts` is caller-built by design |
