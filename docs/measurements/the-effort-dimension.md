# A field name outranks every description, and the twelve do not reproduce

**Four things, and two of them overturn something this project already wrote
down.**

1. `conditions.yaml` gained `reasoning_effort` — and **adding the field fixed
   nothing.** The misfiling stopped only when the bool it was landing in was
   *renamed*. The cause was the field's NAME, measured over three arms and three
   draws.
2. **`openai-timeline`'s twelve `code.generation` claims do not reproduce.** Four
   draws at current HEAD return zero claims. They were never persisted, so the
   sharpest piece of evidence for an incomplete capability vocabulary cannot be
   examined at all.
3. **The extractor has never been told what the capability keys mean.** The
   system prompt appends twelve bare key strings; `description` and
   `sounds_like` in `contract/capabilities.yaml` do not reach the model. This is
   probably the cause of the misfiling we have been attributing to the
   vocabulary.
4. Round 3 of the golden set is built — 36 claims, one question, the extractor's
   answer withheld.

*Engineer 1 · 2026-08-21 · 9 probe calls + one 30-document run, $0.049*

---

## 1 · `reasoning_effort` exists, and on its own it did nothing

The instruction was to fix `conditions.yaml` because `structured_mode` — a
`bool | None` meaning *"was provider-side schema enforcement on"* — had taken a
string three times: `'xhigh'` twice, `'auto mode'` once, the last costing four
claims. The recorded diagnosis, which I wrote and which reads well, was *"no
field for the thing, so it goes somewhere wrong rather than nowhere."*

So the field was added, with a description that names the offending value as its
own example:

> *"auto — the provider chose the effort rather than the user, e.g. a router or
> an 'auto mode'."*

Then the five previously-dark documents were re-run. **`auto-mode` misfiled
again, three claims out of three, `reasoning_effort` null on every one.**

```
auto-mode, with reasoning_effort in the schema
  proposed 3   verified 0   unsalvaged 3   zero_kind=unsalvaged
  all three:  conditions.structured_mode = 'auto mode'
```

The field was in the tool schema — verified by reading the schema the client
sends. The description was in it. The pointer was in `structured_mode`'s own
description. None of it held.

### The probe, and the first version of it measured nothing

Three arms on the same document, same prompt, one call each, differing **only in
field names**:

| | offered | `'auto mode'` in the bool | `reasoning_effort` |
|---|---|---|---|
| **A** as shipped | `structured_mode`, `reasoning_effort` | **3 of 4 claims** | null on 4 of 4 |
| **B** renamed `schema_enforced` | `schema_enforced`, `reasoning_effort` | **none** | **`auto` on 4 of 4** |
| **C** bool removed | `reasoning_effort` | none | `auto` on 4 of 4 |

Replicated three times. Identical every time, down to the token count.

> **v1 of this probe was invalid and it is worth recording why.** It passed
> `model_json_schema()` straight to the client instead of going through
> `tool_schema_for`, so the model received a schema full of `$ref` it cannot
> dereference — the exact failure `tool_schema_for` exists to prevent, and its
> docstring says so. All three arms returned **byte-identical answers in a shape
> the real schema does not have**: `claims` as a list of JSON strings with
> fields (`model`, `capability`, `start_offset`) that exist nowhere in
> `ExtractedClaim`. The tell was three different schemas producing one identical
> answer, which is impossible if the schema is being read. An experiment whose
> arms cannot differ produces a clean, stable, meaningless result.

### What that means, and it qualifies a rule written earlier today

`'auto mode'` was not going to the nearest-*shaped* slot. It was going to the
slot whose **name matched the words in the document** — "auto mode" to the only
field ending in `_mode`.

Earlier today this project recorded: *"if the model must respect a constraint,
the constraint goes in the description of the field it is filling"*
(`a-constraint-not-in-the-description-is-invisible.md`). That still holds, and
it is now **necessary and not sufficient**:

> **A field NAME is a stronger instruction than any field's description** —
> including the description of the field that should have won, and including an
> explicit pointer written into the wrong field's own description.

The actionable form, and it belongs wherever fields get named: **do not name a
field after a word the corpus uses in another sense.** `tool_count` and
`context_size` are safe. `*_mode` was not, in a corpus about models that have
modes.

### So the rename was taken, and it was not what was asked for

The instruction was a field, explicitly *"rather than a stricter bool"* — which
was right, and a stricter bool would have converted four silent misfilings into
four loud validation errors. But the field alone measurably does not work, and
leaving it at that would have shipped a known-broken state with a new field
beside it.

`structured_mode` → `schema_enforced` across five files. **Costs no migration
today**: `0 of 6` stored `condition_bucket` values carry the old prefix — 4
`claim` rows and 2 `cell` rows, all `context_size:unknown`. It will never be
cheaper, and revert is a find-and-replace.

**Both changes are flagged in `contract/conditions.yaml` and need E2's
sign-off.** `docs/proposals/for-engineer-2-the-effort-dimension.md`.

### On the corpus, not just in the probe

```
auto-mode      before  0 claims, 4 lost to the misfiling
               after   3 claims verified, and `unclassified` fired
```

---

## 2 · The corpus re-run: 36 claims from 15 of 30

One coherent draw at current HEAD, everything persisted —
`docs/measurements/blog-extraction-run.json`. The previous file is kept as
`blog-extraction-run--2026-08-21T1112-pre-rename.json`, because overwriting a
measurement hides that it moved.

```
                        claims   documents   retries   tokens (in/out)
first run                   8           4         ?    not comparable
30 of 30, pre-rename       28          11         6    75,985 / 5,679  (under-counted)
30 of 30, at HEAD          36          15         5    105,662 / 6,609
```

**`36` is not `42`.** The 42 was `28 + 14`, and the 14 came from a re-run that
was never written to disk. This draw of the same five gave 10, and the full
corpus at HEAD gives 36. Same 30 documents, same model, same 12 keys.

> **The token figures across these runs are not comparable and the earlier
> correction cannot be validated against this run.** The `~91,200` estimate was
> for the pre-rename run's calls; this run has a *larger schema* (`speaking` and
> `reasoning_effort` were both added) and a different retry count. The
> correction notes already added to four documents stand as written — they
> correct that run's arithmetic, which was wrong for a reason unrelated to this.

What moved, per document:

| document | pre-rename | at HEAD |
|---|---:|---:|
| `auto-mode` | 0 (4 lost) | **3** |
| `claude-opus-5-system-prompt` | 0 (1 lost) | **1** |
| `stealing-reasoning-traces` | 0 | **4** |
| `qwen-38-27b` | 11 | 11 |
| `openai-timeline` | 0 | **0** |

`unclassified` fired on **two** documents, up from one.

---

## 3 · Salvage is carrying 17 of the 36 claims

```
documents whose ENVELOPE failed and were salvaged        4
claims those documents produced                        17   (47% of the corpus)
claims still unsalvageable                              4
```

Nearly half this corpus reaches the pool through a path that until 2026-08-21
discarded everything. That is not a compliment to salvage — it says the envelope
fails often, and the reason is almost always **one over-long quote among many
good ones**.

---

## 4 · The twelve do not reproduce, and they were never written down

`salvage-the-five-and-the-yield-movement.md` §5 rests on this:

> *"`openai-timeline` produced **12 claims, every one `code.generation`**, on a
> document that is a timeline of agents attacking an Artifactory instance … The
> evidence that the vocabulary is incomplete in general is strong."*

**Four draws at current HEAD, and every one returns zero claims:**

```
30-of-30 corpus run   proposed 0   zero_kind=silent
draw 1                proposed 0   zero_kind=silent
draw 2                proposed 0   zero_kind=silent
draw 3                proposed 0   zero_kind=silent

stated reason, identical each time:
  "The document describes an incident involving an experimental, unreleased
   OpenAI model, but does not make any claims about..."
```

That reason is correct. The document is about an incident, not about a model's
capability, and returning nothing is the right answer.

**So the argument was built on one draw of one document, and the draw was not
persisted.** It cannot be re-examined, cannot be labelled, and cannot be
diagnosed. What survives of it is nothing.

This is rule 7's shape with no figure in it: *"twelve claims, every one
`code.generation`"* reads as a property of the extractor. Its population was **1
draw of 1 document out of 30**, unstated, and the population was also the entire
evidence base. Same failure as *"any branch older than the fix carries this
defect"* — a true statement about one instance, generalised without counting.

**Consequences, both directions:**

- **the case for a new capability key is weaker, not stronger.** It rested on
  demonstrated misfiling past `unclassified`, and the demonstration is gone. The
  standing conclusion — *do not add a key on this evidence* — holds, now for a
  better reason.
- **and the instrument still needs building**, because the question is open
  rather than answered. §6.

> **Operational rule this earns: an extraction run whose output enters an
> argument must be persisted at the time it is run.** The 30-of-30 run was
> persisted and is re-readable four hours later. The five-document re-run was
> not, and its most-quoted number is now unrecoverable. `scripts/` writers now
> record `claims`, `unsalvaged`, `per_document`, `speaking` and `conditions`.

---

## 5 · The extractor has never been told what the keys mean

Found while building the pool, and it may be the whole story.

```python
build_system_prompt(capability_keys)
  -> SYSTEM_PROMPT + "\n\nTHE CAPABILITY VOCABULARY. Use these keys and no others:\n"
                   + "\n".join(f"  - {key}" for key in capability_keys)
```

```
system prompt                                         2,819 chars
capability descriptions reaching the model:           NONE
`sounds_like` phrases reaching the model:             NONE
```

Verified by searching the assembled prompt for a fragment of every capability's
`description` and for every `sounds_like` string: zero hits.

`contract/capabilities.yaml` carries, for `over_refusal`, a `description` and
`sounds_like` phrases written precisely to fence it off. **The model has seen
none of them.** It has seen the string `over_refusal`.

So when `"it defaults to wildly overthinking things"` was filed under
`over_refusal` and we called that evidence of a missing capability key, the
model was choosing between twelve identifiers with no definitions. That is not a
vocabulary gap. It is the same mechanism as everything else in this file: **the
constraint exists in the contract and does not reach the reader.**

**Not fixed, deliberately.** It changes what the extractor emits, and round 3's
pool is drawn from the current extractor — so fixing it now would leave the
golden set measuring a superseded one. Building the pool first makes it the
before-measurement for exactly this change, which is the more valuable ordering.
It is the largest lever left and it should be the next thing done.

---

## 6 · Round 3, not a third question — and the cost comparison

**It is a round 3, and the "cheaper" option cannot answer the question even in
principle.**

Round 2's claim rows are 12 claims from a Reddit announcement thread and a blog
post, drawn for *"who is speaking"* and *"does the quote support the claim"*.
The claims in question are **36 blog claims from the corpus run**. They are not
the same rows. A third question added to round 2 would ask about capability
choice on twelve claims that are not the ones under test.

| | labels per labeller | on the claims in question |
|---|---:|---|
| third question on round 2 | 12 | **none of them** |
| round 3 as built | 36 | all 36 |

So round 3 is 3× the labels and the only option that measures anything. Two
things make it cheaper than the ratio suggests:

- **it asks ONE question**, not three, so a row is a single choice rather than a
  re-read;
- **round 2 is untouched.** Yathu is 34 of 48 in, and a pool that grows
  mid-labelling is a pool nobody can compare — the rule that governed round 2's
  own construction.

### What the pool carries, and why each piece

`fixtures/golden/capability-choice-round3--unlabelled.jsonl`, 36 rows, built by
`scripts/capability_choice_pool.py`.

1. **The extractor's choice is WITHHELD**, in a sidecar keyed by `row_index`.
   Round 2 could show the claim because its question was *"does the quote
   support THIS claim"*. Here the labeller is choosing, and showing them the
   answer measures anchoring rather than judgement.

2. **The 12 keys with their `description` and `sounds_like`.** A labeller cannot
   separate `ops.latency_ttft` from `over_refusal` from key names alone.

   **And that is an asymmetry the pool states up front:** the labeller sees more
   than the extractor did (§5). A disagreement is therefore *not* proof the
   extractor chose badly — it is an **upper bound on what telling the model the
   definitions could fix**, which is a more useful quantity than the one
   originally wanted.

3. **Fifteen options: the 12 keys plus three**, because a single
   "no key fits" bucket is what made `unclassified` unable to argue for
   anything:

   | option | what it argues |
   |---|---|
   | `no-key-fits` | a real capability the list does not name → **add a key** |
   | `not-a-capability-claim` | not about model behaviour at all → **the claim should not exist** |
   | `cannot-tell` | the row is insufficient → **about the pool, not the extractor** |

   Those are three different findings and `unclassified` collapsed the first two
   into one. The declined quote it did collect — about a vendor's self-reported
   benchmarks — is a `speaking` matter, which is a fourth thing again.

4. **Scoring stated before any labelling.** The headline is the **binary**:
   labeller-vs-extractor agreement (the measurement), and
   labeller-vs-labeller agreement on the same binary (the instrument's
   reliability, which bounds how much of the first to believe). The 15-way
   distribution is description only — a 15-way kappa on 36 rows is noise, and
   round 2's `_meta` already records that more categories cost agreement before
   they buy any.

5. **Rows shuffled**, seed `20260821` recorded. Eleven of the 36 come from one
   document; consecutive same-document rows get labelled as a block.

6. **`recovered_by_salvage`** per row, derived from which envelopes failed — 17
   of 36. If salvaged claims misfile at a different rate, that is a finding
   about salvage rather than about the vocabulary, and a uniformly `false` flag
   would have hidden it.

7. **`source_document_text` as the extractor was given it** — post-strip, with
   `## Recent articles` removed. A labeller checking a quote against the live
   page would find different offsets and, on one document, a different article.

8. **`author_external_id` on every row**, 36 of 36 non-null. Round 1's claim-row
   labels had to be discarded because no row said who was speaking.

9. **The denominator in `_meta`**: 36 claims, 15 of 30 documents, **one site,
   one author, one extractor, one draw** — and the note that the same 30
   documents have produced 8, 28 and 36 claims at three code states. Not a
   misfiling rate for the pipeline.

10. **What it cannot answer**, named rather than left out: the twelve (§4).
    Nothing in the pool stands in for them.

### `conditions.yaml`'s remaining gaps, not taken

Three, all E2's call and all recorded in the file:

- **no capability is `reasoning_effort`-dominant**, so the dimension is recorded
  and never bucketed on. `ops.latency_ttft` is the obvious candidate and moving
  it off `context_size` rebuckets every existing latency claim — a re-run, not
  an edit.
- **no query carries `records_condition: reasoning_effort`**, so nothing is
  retrieved *for* it; it is picked up incidentally.
- **`*:unknown` has no phrase** for any dimension, so `condition_label` falls
  back to the raw bucket string. Pre-existing, and the wording is a rule-4
  question — *"effort not stated"* must not read as *"no effort"*.

---

## What changed

| file | change | sign-off |
|---|---|---|
| `contract/conditions.yaml` | `reasoning_effort` dimension added; `structured_mode` → `schema_enforced` | **E2 — flagged in the file** |
| `contract/queries.yaml` | 2 × `records_condition` renamed | **E2** |
| `judge/extract/schema.py` | `ReasoningEffort`; `Conditions.reasoning_effort`; the bool renamed | with the above |
| `judge/config.py` | `band_for` branch, `_EFFORT_ALIASES`, unrecognised effort **raises** | |
| `judge/curate/phrases.py` | 6 effort bucket phrases, so no raw key can reach a page | |
| `judge/ask/requirements.py` | parameter renamed to match the bucket key | |
| `scripts/blog_extraction_run.py` | persists `speaking`, `conditions`, `unsalvaged`, `per_document` | |
| `scripts/capability_choice_pool.py` | **new** — builds round 3 and its withheld sidecar | |
| `tests/test_conditions_contract.py` | **new**, 17 tests, incl. no conditions field may end in `_mode` | |
| `docs/how-it-works.md`, `docs/logic-and-workflow.md` | the retry-is-not-a-second-chance rule, at both places retries are described | |

**Suite: 2,003 passed, 0 failures.** 58 errors, all fixture setup against
`203.0.113.5`, which stopped answering partway through the run — the same host
the migration and this run's document load both used successfully earlier.

Not changed: the capability vocabulary, the system prompt's bare-keys assembly
(§5), `dominant_dimension`, round 2.
