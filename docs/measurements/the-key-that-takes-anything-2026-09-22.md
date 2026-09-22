# The key that takes anything

**2026-09-22, anooj.** How often does `claim.capability_key` name what its quote
describes, and can that be told without reading each claim?

Prompted by §5 of `docs/proposals/a-capability-that-works-after-intervention.md`,
which left three claims filed under `extraction.faithfulness` for identifying
people in photographs and said only that it "looks wrong and is a different
defect". It is a different defect, it is not three claims, and the mechanical
part of it can be counted.

All figures below were taken against the shared staging DB on **2026-09-22**.

---

## 1 · Population

| | |
|---|---|
| `claim` rows | **1,385** |
| carrying a `capability_key` | **1,385** (100%) |
| `capability_key IS NULL` | **0** |
| ratified keys in `contract/capabilities.yaml` | **12** |
| `board_entry` rows | 1,468 — capability 689, metric 501, best_for 278 |
| claims with ≥1 capability `board_entry` | 672 |
| claims with **none** | **713** |
| distinct discovered capability slugs | **192** |
| distinct (`capability_key`, slug) pairs | **228** |
| `capability_candidate` rows | 160 (152 distinct keys), **0 ruled** |

`claim.capability_key` became **nullable on 2026-09-10**
(`20260910T1300_claim_capability_key_nullable.sql`). **1,194 of the 1,385 claims
were written on or after that date and not one of them used NULL.** The
database stopped requiring a key twelve days ago; nothing else did.

---

## 2 · The three claims, and the twelve they belong to

`minimaxir.com/2025/07/llms-identify-people/` produced **12 claims, all 12 keyed
`extraction.faithfulness`, all 12 positive, and ZERO `capability_candidate`
proposals.** The escape hatch was open and unused.

The three named in the proposal:

```
clm_0396f583fc1572b0e0a69dc7   GPT-4.1 | Barack Obama.
clm_045a7061bb24d556f3fe5198   GPT-4.1 | Priscilla Chan and Mark Zuckerberg.
clm_b7a5a501841e5030ff758236   GPT-4.1 | Vanessa Kirby, Pedro Pascal, ...
```

Of the **37** claims under `extraction.faithfulness` corpus-wide, **16** carry a
capability slug of `public-figure-identification` (11) or `vision` (5).

**It reaches a page.** Five of the 21 `extraction.faithfulness` cells are sourced
**entirely** from facial-recognition or vision quotes — Claude Sonnet 4 (3/3),
GPT-4.1 (3/3), Nano Banana 2 (3/3), Llama 4 Scout (2/2), Qwen3.8 27B (2/2) — and
each renders `"One person mentioned extraction - not yet corroborated"` about a
model for which nobody mentioned extraction. `extraction.faithfulness` is
`failure_mode: silent`, so `judge/pages/capability.py:110` appends *"an absence
of complaints about any model here is not evidence that it works"* — a rule-4
caveat attached to the wrong subject.

All 302 cells are `insufficient`, so no consensus phrase publishes yet. The
counting is wrong now; the phrase is withheld for an unrelated reason.

---

## 3 · How common — three mechanical signals and one hand read

### 3a · Judgement-free: a slug that sits under more than one key

If `vision` is `over_refusal` in 13 rows and `extraction.faithfulness` in 5, at
most one is right. No reading required, no opinion about which.

**18 slugs span two or more keys, covering 329 of 689 capability entries.
Assuming the largest bloc of each is correct, 101 entries (14.7%) are mis-keyed
— a floor.**

```
reasoning              reasoning.multistep=64 | code.generation=7 | ops.latency_ttft=5 | instruction.adherence=2 | over_refusal=1
instruction-following  instruction.adherence=67 | code.generation=6 | over_refusal=2 | ops.latency_ttft=1
agentic-tool-use       code.generation=12 | tool_calling.long_chain_reliability=12 | reasoning.multistep=5 | ...
vision                 over_refusal=13 | instruction.adherence=11 | extraction.faithfulness=5 | code.generation=4
long-context           context.effective_window=25 | code.generation=3 | ops.latency_ttft=2
code-review            code.editing_diff_fidelity=12 | code.generation=4 | reasoning.multistep=1
```

The floor **undercounts wherever no key is right**. `vision` has no ratified key,
so all 33 are mis-keyed and the floor scores 20.

### 3b · Slugs the nullable migration itself named as having no ratified key

**187 of 689 capability entries (27%)** sit on those six slugs — against
`judge/extract/prompt.py`'s own estimate that the closed list "would have dropped
a third of the board".

```
instruction-following  76    agentic-tool-use  34    vision       33
long-context           30    function-calling  10    multimodal    4
```

### 3c · A claim with no capability entry at all

**713 of 1,385 claims** carry a required `capability_key` while the extractor's
own free reading produced no capability section for that quote. Mostly prices and
bare figures. It is a weight, not a gate: in the sample below, 14 of 15 `filler`
claims had no slug — and so did 6 of 14 correctly-keyed ones.

### 3d · Hand read — 60 claims, seed 20260922, one reader

Drawn from all 1,385 with `random.seed(20260922)`. One reader, one pass.

| label | | | meaning |
|---|---|---|---|
| `match` | 14 | 23% | the key names what the quote describes |
| `near` | 8 | 13% | arguable either way |
| `filler` | 15 | 25% | the quote describes **no capability at all** (a price, a bare figure, an advertised spec) and the key was supplied anyway |
| `mis` | 23 | 38% | the quote describes a capability the key does not name |

**The key does not name what the quote describes in 38 of 60 = 63%**
(`filler` + `mis`; 95% CI ≈ 51–76%, so **≈700–1,050 of 1,385**). Counting `near`
as `match` does not change it. The strict subset — a real capability under a
wrong key — is **23 of 60 = 38%** (≈360–705 claims).

Worth naming, because both are cases the prompt explicitly legislates against
and lost anyway:

```
#31  code.generation  "spending 5-8x more tokens than competitors"   token spend: schema says NO KEY
#34  over_refusal     "it elaborates endlessly ... 'both sides'"     verbosity: schema says NOT over_refusal
#43  code.generation  "more than 1/3 the expressions had an error"   slug: text-to-speech-japanese
#53  context.effective_window  "up to 1,048,576 input tokens"        the key says never the advertised figure
#60  instruction.adherence     "77.2% on MMAU"                       an audio benchmark
```

### 3e · So: can it be told without reading each one?

**Partly, and the reduction is real.** 228 distinct (key, slug) pairs cover 689
entries — a 3x reduction, and a pair is judgeable from the pair. §3a needs no
judgement at all. What none of it covers is the 713 claims with no slug, which is
where most of the `filler` lives.

**And the row already contains its own disagreement.** On the minimaxir claims
the extractor named the capability `public-figure-identification` in
`board_entry` and keyed the claim `extraction.faithfulness` in the same write.
Nothing compares the two.

---

## 4 · Why the extractor does it: the prompt says both things

```
prompt.py:84    "pick the closest key and move on"
prompt.py:267   "Do not stretch a quote to fit a key. Forcing a quote into the
                 nearest key fabricates consensus about something the writer
                 never discussed."
prompt.py:393   "Pick the closest key. ... where no key is close, still pick the
                 closest one AND propose the missing key"
schema.py:490   "Pick the closest ratified key; if none is close, still pick
                 the closest AND propose the missing one"
```

Three instructions to force it, one not to. The prohibition is 126 lines before
the instruction that overrides it, and the overriding one is **last in the
prompt**. `docs/discovered-capabilities-and-the-cell-question-2026-09-08.md` §1a
quotes line 267 as evidence that "a quote that fits no key does not get
classified into the nearest one". It did, 1,385 times.

---

## 5 · Is it the same shape as the metric-axis defect?

**Same cause, opposite symptom, and only one of the two fixes transfers.**

| | metric axis (#368) | capability key |
|---|---|---|
| cause | the grouping key was **named** by inference, not copied | same |
| symptom | **over-merge** — 9 benchmarks under `swe-bench` | **both**: `extraction.faithfulness` absorbs facial recognition, *and* `vision` disperses across 4 keys |
| vocabulary | open — the right slug can be created | **closed at 12** — the right key does not exist |
| is the right answer in the text? | **yes** — `'Terminal-bench 4.0'` is a string in the quote | **no** |

The over-merge half is confirmed still live: **39 rows under slug `swe-bench`**,
whose quotes name OSWorld-2.0, Terminal-Bench 4.0, AutomationBench,
CursorBench 3.2.0, DeepSWE v1.1, SWE-Bench Pro and SWE-bench Verified.

**And the axis fix has never run.** `20260921T1330_board_entry_axis_quoted.sql`
added `axis_verbatim`, `subject_verbatim` and `axis_quoted` and applied at
**13:20:36Z on 2026-09-21**; the newest `board_entry` row was written at
**13:03:04Z**, seventeen minutes earlier. All three columns are NULL on **all
501** metric entries. That is "no run yet", not a compliance rate — and it means
the transfer below is being judged against a mechanism with no measured error
rate of its own.

---

## 6 · Does `axis_verbatim`'s shape transfer?

`axis_verbatim` works in four parts. Three transfer. The load-bearing one does
not.

1. **Ask for a copy, not a name** — transfers.
2. **Keep three states apart** (`quoted` / `absent` / `unsupported`, rule 6) —
   transfers, and would be an improvement on `capability_key`, which has no way
   to say "the quote names none".
3. **Ship as a weight, measure first** (rule 8) — transfers.
4. **Check the copy by exact substring against the quote** — **does not
   transfer**, and it is the only reason the other three are worth anything.
   `judge/store/board_entries.py:181` says so itself: *"`value_verbatim` is
   trustworthy because code compares the copy against the text — not because its
   instruction is emphatic, which it already was while 10% of figures were not in
   their quote."*

**A benchmark name is a string in the document. A capability is a reading of
it.** `"GPT-4.1 | Barack Obama."` contains no substring naming a capability, so
`quoted_support` can only ever return `absent`.

**Measured.** Running `quoted_support`'s own check over the capability section's
names — the closest thing the corpus has to a `capability_verbatim` today:

```
capability  n=689   name is a substring of its own quote:   89  (12.9%)
                    NOT in the quote:                      600  (87.1%)
```

So a `capability_verbatim` would inherit `axis_verbatim`'s **asking** and none of
its **checking** — the shape rule 1 exists to prevent, and the thing
`CLAUDE.md` rule 2 calls a guarantee that looks like one and is not.

**What the corpus does have instead of a substring**: a second independent
reading of the same quote, already written, in the same row —
`board_entry.slug`. That is a checkable *disagreement* rather than a checkable
*copy*, and §3a is it being counted. Where the two readings conflict, at least
one is wrong; where they agree, neither is confirmed. That is weaker than
`axis_verbatim` and it is not nothing.

**No proposal here.** This is the measurement.

---

## 7 · Artefacts

Scratchpad, this session — not committed:

```
sample60.json             the 60-claim draw, seed 20260922
sample60_labelled.json    the same rows with one reader's labels
label.py                  labels + the cross-tab in §3c/§3d
transfer.py               the substring check in §6
pairs.txt                 all 228 (key, slug) pairs with counts
```

⚠ `copyable.py` was also run and **its output is not reported**. It counted
benchmark-shaped names in quotes with a hand-written regex and returned 7.4% for
metric entries. That figure measures the regex, not the corpus — rule 7 — and
nothing here rests on it.

---

## 8 · Reach into cells (added same day)

Using only §3a's judgement-free floor — 99 claims whose slug spans keys and
whose key is not the modal one:

```
cells                                     302  (all `insufficient`)
  containing >=1 floor-mis claim           56   (18.5%)
  sourced ENTIRELY from floor-mis claims   16   ( 5.3%)
```

The sharpest instance, and the one carrying the most voices:

```
Z.ai: GLM 4.6V   instruction.adherence   voices=5  +5/-0   n_eff=0.038  platforms=1
  all five quotes are about vision or Chinese OCR
  all five board_entry slugs are `vision`
  phrase: "5 people mentioned following instructions - not yet corroborated"
```

`judge/curate/gate.py:check_gate` tests `n_eff`, `platform_count` and
`max_author_share`. **None of the three is about whether the key names the
quote**, so the mis-key is orthogonal to publication: what holds this cell back
is corpus size.

**It renders today.** `web/src/routes/ModelDetail.jsx:138` stopped rendering
cells on purpose, citing this defect — but `web/src/routes/Models.jsx:182` folds
every capability page into a per-model evidence badge, drawn at lines 425 and
483 as `capLabel(capability) · N voices`. GLM 4.6V reads **"Adherence · 5
voices"**; GPT-4.1 reads **"Faithfulness · 1 voice"**. `capLabel` keeps only the
last dotted segment, so "extraction" — the word that would let a reader notice —
is not shown.

This corrects `the-vocabulary-hypothesis.md` §4, which says a mis-fitting
vocabulary produces **empty** cells and costs "coverage, not correctness". That
holds only if the mis-fitting claim is dropped; the prompt forces it to be filed
instead.

Script: `cells.py`.

---

## 9 · What shipped, same day

Steps 1 and 2 of `docs/proposals/the-key-that-takes-anything.md`, on E1's
instruction. **Every figure above describes `e5.4` and is now history**, which
is the point of recording it: the 1,385 rows keep their keys, `CellStore`
filters on `PIPELINE_VERSION`, and the bump to **`e5.5`** is what stops them
reaching cells.

```
prompt.py    "pick the closest key and move on"        -> removed
             "still pick the closest one AND propose"  -> removed
             "Do not stretch a quote to fit a key."    -> KEPT, and now has a
                                                          third home: leave it
                                                          empty
             the closing block                         -> "CLOSED, AND OPTIONAL",
                                                          empty stated first
             each key's description + sounds_like      -> SENT (`_keys_block`)
schema.py    capability: str                           -> legacy_score_key:
                                                          str | None = None
client.py    _close_capability                         -> accepts the optional
                                                          shape, flattens it,
                                                          and REFUSES if the
                                                          field is `required`
pipeline.py  legacy_score_key is None                  -> claim kept, no cell,
                                                          counted in
                                                          `cell_skipped_no_key`
claims.py    StoredClaim.weights                       -> WeightFactors | None
```

**⚠ THE RENAME ALONE WOULD HAVE DELETED MOST OF THE CORPUS, and nothing in the
proposal predicted it.** Both readers of the key refuse an absent one —
`compute()` with a ValueError, `bucket_for()` with a KeyError — and the handler
around them sets the claim aside, which writes **no claim row at all**: no
claim, no weight, no quote, only a board entry with a null `claim_id`. So
"the extractor may say it does not know" would have become "the pipeline
discards every claim it does not know" — rule 4 at the worst stage, in the table
every count comes from. `judge/pipeline.py`'s keep-the-claim branch is the fix
and `TestAnEmptyKeyKeepsTheClaim` pins it.

Two judgement calls inside that branch, both rule 6:

- **No weight rather than a defaulted one.** All seven factors rank a claim
  *within* a cell and a keyless claim has none. A default would mean picking a
  half-life, and `half_life_for` returns the SLOW default for any key it does
  not recognise — the gentlest decay there is, handed to the claims we know
  least about, by a fallback that cannot fail (rule 12).
- **`condition_bucket = "none:no_ratified_key"`.** The column is NOT NULL and
  reads `<dimension>:<band>` for a capability; with no capability there is no
  dominant dimension, so it names the absence instead of borrowing one.

`cell_skipped_no_key` is counted apart from `cell_refusals` deliberately: that
list rising means our vocabulary could not resolve a key the extractor supplied,
this rising means the extractor honestly reported that none applies. One number
would climb both when the pipeline breaks and when it starts telling the truth.

### What is NOT measured

**No extraction has run under `e5.5`.** Every claim in the database is `e5.4`,
so there is no empty-key rate, no change in board coverage and no evidence that
any of this helped. The figure that would say so does not exist — see §10.

### Checks, and their scope

```
ruff     scoped to the diff (11 files)            all passed
pytest   3,373 tests, DB-dependent files excluded  3 failed -> 2 fixed, 1 pre-existing
```

The two were this change, both caught by source-inspection tests doing their
job: `_close_capability`'s refusal message pinned the old field name, and
`test_has_conditions_is_not_derived_from_the_claim` greps `Pipeline.run` for a
line that moved into `_stored_with_cell_weight`. Both updated; the second now
reads both methods and additionally asserts the forbidden derivation is absent,
which is the property it was actually protecting.

The pre-existing one is **not mine and is a rule-11 instance**:
`tests/test_export_source.py` asserts `len(document_ids) == 7` against an
untracked local `_handoff/` that now holds 17 — a bare count in a test about
state the test does not own.

⚠ **THIS IS NOT "CI IS GREEN".** No Postgres is running here, so ~28 files were
excluded by name and `tests/test_column_states.py` errored on `import psycopg`
after the documented `grep` missed it — which is the exact staleness that grep
is warned about in `CLAUDE.md`. `test_pipeline_db.py`, `test_claim_store_db.py`
and `test_cell_store_db.py` all exercise the paths this change touches and
**none of them ran.**

---

## 10 · The one measurement that would settle it, and why it is not here

A model must not label the golden set. `fixtures/golden/capability-choice-round3--unlabelled.jsonl`
is round 3 of the golden set on precisely this question — *was the capability key
the right one* — 36 rows, 15 documents, every answer `null`, the extractor's
choice frozen in a sidecar. It has never been labelled.

Labelling it is what turns steps 1 and 2 from a hope into a number, and it is
the half that has to be human: the pool is the instrument that measures the
extractor, and an instrument a model adjusted measures nothing. The design is a
paired arm against one gold —

```
before   the frozen sidecar               bare-key prompt, e5.4
after    re-run the same 15 documents     definitions shipped, e5.5
gold     one human labelling, scored against both
```

— and the *before* arm stays constructible:
`build_system_prompt(keys, definitions={})` reproduces the bare-key prompt, and
`test_the_bare_key_prompt_is_still_reproducible` pins it. At the measured $0.00208/thread the re-run is cents.
