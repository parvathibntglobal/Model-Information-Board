# Stop the extractor picking a key that does not fit

*anooj · 2026-09-22 · a proposal. `judge/extract/prompt.py`, `judge/extract/schema.py`
and `contract/` are not edited by it.*

Measurement behind it: `docs/measurements/the-key-that-takes-anything-2026-09-22.md`.

---

## 0 · What this must not re-litigate

`docs/measurements/the-vocabulary-hypothesis.md` already pre-registers the
question "do the twelve keys describe what engineers write about", with its
arithmetic fixed in advance and `fixtures/golden/capability-choice-round3--unlabelled.jsonl`
(36 rows) built to test it. **That pool has never been labelled.**

**My 63% is not that measurement and must not be read as testing it.** Round 3
asks a labeller to *choose* a key blind. I asked a different question — does the
key the extractor chose name what the quote describes — of a different
population, on a different draw, with one reader. Compatible with the
hypothesis; not evidence for it. Round 3 stays the instrument.

One thing my measurement does contradict, and §5 is about it: that document's §4
says a mis-fitting vocabulary "does not produce wrong cells — it produces
**empty** ones". It produces populated wrong ones.

---

## 1 · The wording

Three changes to text already in the repo. No new contract content.

**(a) `prompt.py:84`, item 4 of WHAT YOU RECORD.**

```
-  4. A `capability` key from the ratified list at the end of this prompt. That
-     one field feeds an older scoring path and is NOT what the board displays;
-     pick the closest key and move on.
+  4. A `legacy_score_key` - ONLY IF one of the ratified keys at the end of this
+     prompt names what the quote is about. Leave it empty when none does. That
+     is the common answer and it is a correct one.
```

**(b) `prompt.py:267`** — the prohibition. **Unchanged.** It is already right
and it is already being overridden.

**(c) `prompt.py:390-396`**, the closing block — the one the model reads last.

```
-THE RATIFIED CAPABILITY KEYS (`capability`) - CLOSED, use these and no others
+THE RATIFIED KEYS (`legacy_score_key`) - CLOSED, AND OPTIONAL
 ======================================================================
-This single field feeds an older scoring path, NOT the board. Pick the
-closest key. It does not limit what you may discover above, and where no
-key is close, still pick the closest one AND propose the missing key in
-`proposed_capabilities`.
+This field feeds an older scoring path and is NOT what the board displays.
+
+LEAVE IT EMPTY unless one of these keys names what the quote is about. Empty
+is stated first because empty is the common answer: these twelve were written
+for a different corpus, and most quotes are about something else.
+
+DO NOT PICK THE CLOSEST. A key that is merely nearest files this quote into a
+count about something the writer never discussed. Five people discussing
+GLM-4.6V's vision and Chinese OCR were counted as "5 people mentioned
+following instructions" on that model's row, because `instruction.adherence`
+was the nearest of twelve.
+
+If no key names it, leave this empty AND propose the missing key in
+`proposed_capabilities`.
```

Three things about this, in the order they matter:

- **Empty is stated first and stated as correct.** This is the fix that already
  worked on `axis_verbatim`, whose own comment records the failure it repaired:
  *"the first version said REQUIRED while also saying LEAVE THIS EMPTY … 22
  metric figures, 0 ABSENT and 19 naming an axis the quote does not contain. The
  extractor was never allowed to say 'the quote names none', so it named
  something every time."*
- **The prohibition moves last.** It is currently 126 lines before the
  instruction that reverses it, and the reversing one closes the prompt.
- **The rename is not cosmetic** — §2.

`schema.py:490` changes to match: `capability: str` → `legacy_score_key: str | None = None`,
description rewritten the same way. The DB already allows it (§2).

---

## 2 · No, NULL becoming usable is not enough — and we have measured why

The column has allowed NULL since **2026-09-10**. **1,194 of the 1,385 claims
were written on or after that date. None used it.** That is the question's own
answer, and three more instances say it is a pattern rather than an oversight:

| available | used | |
|---|---|---|
| `capability_key` NULL, since 2026-09-10 | **0 of 1,194** | the prompt still mandates a pick |
| `conditions.framework`, since the schema was written | **42 of 1,385 (3.0%)** | and empty on `"Locus with Opus 5 gets a score of 44.7"` — a quote that names the framework |
| `capability_candidate` | **0 of 12** on minimaxir | 160 rows corpus-wide, so it does fire; it did not fire where every one of 12 claims needed it |

**A field being available is not a field being used.** The `conditions.framework`
row is the sharpest: the concept exists, the field exists, the quote names Locus
in its own characters, and the record says `{}`.

### And the repo has already run the experiment that says why

`Conditions`' docstring, quoted in the `unaided` proposal:

> Two fixes were tried and only the second worked. **1.** add `reasoning_effort`
> with a description naming `'auto mode'` as its own example — misfiling
> continued unchanged. **2.** rename `structured_mode` to `schema_enforced`,
> changing nothing else — misfiling stopped dead.
>
> **A field name is a stronger instruction than any field's description.**

So a description change to a field still named `capability` is change type 1, the
one that did not work. **And `capability` is the worst possible name here**, by
that docstring's own naming rule — *do not name a field after a word that
appears in the corpus in another sense*. `capability` is this prompt's most
overloaded word: it is the board's own discovered section, it is
`contract/capabilities.yaml`, it is `capability_candidate`, and the prompt spends
most of its length teaching the **open** vocabulary under that exact name. The
field named `capability` collides head-on with the thing it is not.

`legacy_score_key` says what it feeds and nothing about capability. A model has
no intuition to force into a field with that name.

### The larger lever, which is not wording at all

**The extractor has never been shown what the keys mean.**
`build_system_prompt` takes `capability_keys: list[str]` and emits
`"\n".join(f"  - {key}")` — twelve bare dotted strings.
`description` and `sounds_like` in `contract/capabilities.yaml` do not reach the
model. Already recorded, verified, in `the-vocabulary-hypothesis.md` §2 as "the
single largest confound".

Read `extraction.faithfulness` as a bare string with no definition and reading
names off a photograph is a defensible pick. The definition — *typed fields from
messy input, with correct nulls* — is the thing that excludes it, and the model
has never seen it.

### So: ordering, and what measures each step

**Step 1 — the wording and the rename (§1).** Text and a field name, no new
contract content, no config plumbing. Measured by re-extracting round 3's **15
documents** under the new prompt and reporting the NULL rate and the paired
change against the choices already stored in
`capability-choice-round3--extractor-chose.jsonl`. At the measured $0.00208 per
thread (`docs/measurements/extraction-token-counts.md`), that re-run is cents.

**Step 2 — ship `description` and `sounds_like` into the prompt.** Bigger lever,
and it is config plumbing rather than new content, so rule 5 is satisfied
already.

> **⚠ CORRECTED 2026-09-22, BEFORE SHIPPING.** This paragraph said *"it must be
> labelled before it ships, not after"* — that a `no-key-fits` label taken after
> step 2 would measure a prompt that no longer exists, leaving the confound
> unresolvable. **That is wrong, and it is worth correcting rather than deleting
> because it would have blocked the cheapest lever on a task nobody had started.**
>
> The pool does not decay. Round 3's 36 rows and its frozen
> `--extractor-chose.jsonl` sidecar are fixed artefacts: labelling them tomorrow
> still measures the **bare-key** extractor, because that is the extractor whose
> choices are in the sidecar. One human labelling is one gold, and one gold
> scores **both** arms —
>
> ```
> before   the frozen sidecar             bare-key prompt, e5.4
> after    re-run the same 15 documents   definitions shipped, e5.5
> ```
>
> — so shipping step 2 first does not spoil the instrument, it **creates the
> second arm**. The gap between the arms *is* the confound, measured rather than
> argued. What the labelling gates is not the change; it is any claim that the
> change helped. `build_system_prompt(keys, definitions={})` keeps the old prompt
> constructible and a test pins it.
>
> Both steps shipped on 2026-09-22. §9 of the measurement records what that
> took, including one thing this proposal did not predict.

**Step 3 — negative boundaries on each key** (`instruction.adherence` — *NOT
writing quality, tone or verbosity*). This is **new `contract/` content and gets
two eyes**, and it should only be written against whatever step 2 leaves behind.
Three of the sample's mis-keys are exactly this shape and none of them would
survive it — but that is a prediction, and it is the third step for a reason.

One-way, and weight-before-gate throughout (rule 8): nothing here refuses a
document at any step.

---

## 3 · The §3a disagreement check, as a recorded field

Two readings of one quote are already written in one transaction —
`claim.capability_key` and `board_entry.slug` — and nothing compares them.

### Definition, judgement-free

Four states, and the third is not the second (rule 6):

```
no_key       the claim carries no legacy_score_key            nothing to compare
alone        this slug appears under exactly ONE key          nothing to compare
agree        the key is the modal key for this slug
disagrees    the key differs from the modal key for this slug
```

`alone` is **not** confirmation, and keeping it apart from `agree` is the whole
of rule 6 here: **360 of 689** capability entries sit on a slug used under one
key only, and every one of them could be uniformly wrong.

### Where it goes, and where it does not

**Not a column.** It is a pure function of two stored values plus a corpus-wide
modal, so a stored copy goes stale the next time a run writes — which is rule 11
exactly, and the fastest instance of rule 11 on record took thirty-five minutes.
Compute it where it is shown.

**Not a factor in `claim_weight`.** All seven `f_*` factors multiply into
`w_final`, so adding an eighth changes ranking, and an unmeasured check that
changes ranking is not the "flag or recorded field" rule 8 permits.

**The precedent is `quoted_support`**, in `judge/store/board_entries.py`, whose
docstring already states the standing this needs: *"MEASURED, NOT ENFORCED —
this is reported and nothing is refused on it, because what it is measuring is
whether the extractor can be made to quote its axis at all. Shipping it as a
gate before that is known would be rule 8 exactly."* Same file, sibling
function, same surface: `/admin/board-entries`, which `judge/app.py:393` already
serves and the review UI already reads. **Named consumer, file and line**
(rule 9), and it refuses nothing.

### ⚠ It does not catch the case that prompted it

`public-figure-identification` appears under **one** key — `extraction.faithfulness`,
12 rows. Spread is 1, so the check returns `alone` and says nothing. It catches
`vision` (33 rows, 4 keys) only because that slug got scattered.

**A uniformly wrong key is invisible to a consistency check**, which is the
argument for the check being a weight and against anyone ever promoting it. Said
here rather than discovered later.

### What to count before promoting it

Rule 8's reviewer question is *what population was this error rate measured on,
and did the filter or anything upstream choose it?* The corpus cannot answer:
the 689 entries are the extractor's own output.

Round 3's 36 claims are a population **drawn for a different question, by a
different draw, before this check existed** — the one population available that
the check did not choose. The cross-tab is `disagrees` against the labellers'
key choice, reported with `alone` broken out, and the promotion question stays
closed until it exists.

---

## 4 · The golden set: Import AI beside minimaxir

Agreed, and the pair is worth more than either — with one correction that makes
it sharper rather than weaker.

```
document   jack-clark.net/.../import-ai-468-23-rsi-ideas-posttrainbench-...
claim      clm_371d3d20cb40e274b2c925e2
quote      "Locus with Opus 5 gets a score of 44.7 (versus 34.1% for Opus 5
            without any kind of special harness)"
stored     capability_key = code.generation      slug = automated-ai-rd
           conditions    = {}
           metric        = PostTrainBench, 44.7%, reported
```

**The correction: the distinction survived in the QUOTE, not in any field.**
`conditions` is `{}`. `conditions.framework` exists, is documented, and would
have held `"Locus"` — the quote names it. So this is not "`unaided` captured
correctly"; it is **the extractor choosing a quote span wide enough to carry its
own condition, while every field that could have recorded it stayed empty.**

That makes the pair a cleaner test than a success/failure pair would be:

| | minimaxir | Import AI |
|---|---|---|
| where the condition lives | a pivot sentence **6,000 chars** from the row | **inside the quoted sentence** |
| can a quote carry it? | **no** — the extracted span is a table cell | **yes**, and it did |
| what the record holds | nothing | nothing (`conditions = {}`) |
| what `unaided` would fix | the only place it could go | nothing the quote does not already say |

So the pair separates two things a single document conflates: **whether the
condition is recoverable from the quote**, and **whether any field recorded it**.
`unaided` is needed for the first column and is not what is wrong in the second
— the second is a `framework` field left empty, which is the §2 finding again
and needs no new field at all.

**Expectations, written as the thing that is currently wrong** — and per the
standing rule, the pool is exported **unlabelled**, the extractor's choice goes
to a sidecar, and what gets fixed on disagreement is the option text, never the
labels:

```
document   minimaxir.com/2025/07/llms-identify-people/
expect     no claim from char >8,849 is `positive` with nothing recording the
           revised prompt
expect     at least one NEGATIVE claim for each of GPT-4.1 and Claude Sonnet 4,
           from the four pre-revision refusal rows
expect     legacy_score_key is EMPTY on all 12 - extraction.faithfulness does
           not name identifying people in photographs, and after step 1 the
           extractor is allowed to say so
expect     a capability_candidate proposing a vision or identification key
           (zero were proposed from this document)

document   jack-clark.net/.../import-ai-468-23-...
expect     conditions.framework = "Locus" on clm_371d3d20cb40e274b2c925e2
expect     the quote still carries both figures and the "without any kind of
           special harness" clause - a narrower span is a regression even
           though it would still verify
expect     legacy_score_key: code.generation is ARGUABLE and is a labeller
           question, not a pre-written expectation
```

The last line is deliberate. `automated-ai-rd` under `code.generation` is one of
the `near` rows in the sample; writing an expectation for it would be filling in
a label I do not have.

---

## 5 · What the 63% means for the board today

**Nothing publishes a consensus, and the counts are wrong now.** Those are
different statements and only the second is about this defect.

**Nothing publishes.** All **302** cells are `insufficient`. `check_gate` has
three conditions — `n_eff`, `platform_count`, `max_author_share` — and **none of
them is about whether the key names the quote.** A mis-key is orthogonal to the
gate; what holds these cells back is corpus size, and corpus size is what every
nightly run changes.

**The model page does not render them, deliberately.**
`web/src/routes/ModelDetail.jsx:138` stopped rendering cells, and its comment
gives this defect as the reason: *"six of the eight capability sections on the
reference board have no ratified key and could never have appeared here."*

**But the roster does.** `web/src/routes/Models.jsx:182` folds **every**
capability page into a per-model evidence badge and renders
`capLabel(capability) · N voices` at lines 425 and 483. So today:

```
GLM 4.6V      "Adherence · 5 voices"        5 voices, 5 positive, 0 negative
                                            all five quotes vision / Chinese OCR
                                            all five slugged `vision`
GPT-4.1       "Faithfulness · 1 voice"      the voice named Barack Obama in a photo
```

Five people discussed vision. Nobody discussed following instructions. The
roster says five people mentioned adherence — and `capLabel` takes the **last
dotted segment**, so it renders "Faithfulness", dropping the one word
("extraction") that would let a reader notice.

**Reach, using only the judgement-free floor from §3a:**

```
cells                                     302
  containing >=1 floor-mis claim           56   (18.5%)
  sourced ENTIRELY from floor-mis claims   16   ( 5.3%)
```

Those 16 cells should not exist. One of them carries 5 voices.

### The correction this forces

`the-vocabulary-hypothesis.md` §4 says:

> A vocabulary that misses most of what people write about does not produce
> wrong cells — it produces **empty** ones, which render as silence and are
> honest. The cost is coverage, not correctness.

**That is only true if the mis-fitting claim is dropped, and the prompt forces it
to be filed instead.** The cost is coverage *and* correctness: 16 cells that
exist on nothing, 56 with inflated voice counts, and a roster line per model
naming a capability nobody discussed. Rule 4's shape one stage earlier than rule
8 describes it — not an absence we caused, but a **presence** we manufactured.

Worth noting while that file is open: its §4 also says "the table holds **4
claims**". It holds 1,385. Rule 11.

---

## 6 · What I am asking for

**Steps 1 and 2 shipped 2026-09-22** (§9 of the measurement). Outstanding:

1. **Review the shipped diff**, and in particular the keep-the-claim branch in
   `judge/pipeline.py` — it is the part neither this proposal nor step 1 as
   scoped ("the wording and the rename") anticipated, and it carries two rule-6
   judgement calls I made alone: no weight rather than a defaulted one, and
   `condition_bucket = "none:no_ratified_key"`.
2. **Label round 3.** Not a blocker for the change any more (see the correction
   in §1), and now the only thing that can say whether either step helped. A
   model must not do it: the pool is the instrument that measures the extractor.
3. **§3** — is `/admin/board-entries` the right surface, as a `quoted_support`
   sibling that refuses nothing? Not built.
4. **§4** — add both documents to the golden set; the `framework` correction is
   the part I would most like disagreed with. Not built.
5. **Step 3** — negative boundaries per key. Touches `contract/`, so two eyes,
   and it should be written against whatever step 2 leaves behind rather than now.

Nothing shipped touches `contract/`.
