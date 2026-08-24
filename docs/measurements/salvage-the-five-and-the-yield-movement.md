# 8 claims from 4 documents became 42 from 14, on the same corpus

**Nothing changed about capability, retrieval or vocabulary. The corpus is the
same 30 blog documents, read by the same model, against the same 12 capability
keys. What changed is that two constraints moved into the descriptions of the
fields the model was filling, and a per-document all-or-nothing became
per-claim.**

```
                        claims   documents
first run                   8           4
30 of 30, after            42          14
                         x5.25       x3.50
```

**The largest single yield movement in the project, and it came from where the
constraint was written rather than from anything about the corpus.**

*Engineer 1 · 2026-08-21 · the five dark documents cost $0.0205*

> ⚠ **TOKEN FIGURES ON THIS PAGE WERE LOW, AND IN THE FLATTERING DIRECTION.**
> `run.input_tokens` took the FINAL completion only, so one call per retry went
> unbilled in our own numbers. Corrected 2026-08-21 in
> `judge/extract/runner.py`; the figures below are left as recorded with the
> correction beside them, because editing a measurement in place hides that it
> moved.
>
> | | reported | corrected | |
> |---|---:|---:|---|
> | corpus run, 30 docs, 6 retries | 75,985 in / 5,679 out | ~91,200 / ~6,800 | **83% of true** |
> | cost | $0.0370 | **$0.0444** | **+20%** |
>
> Method: the 6 uncounted calls are the first attempt of each retried document.
> A retry carries the correction text and so is larger than the call it follows,
> which makes scaling by the per-document average an upper bound.
> `docs/measurements/salvage-the-five-and-the-yield-movement.md` §2.

---

## 1 · The migration

```
DSN          postgresql://bv_agent:***@52.17.75.29:5432/Model-information-Board
ENVIRONMENT  staging
```

```
preflight ok in 'staging': 3 passed, 0 failed, 1 skipped
applied 20260821T1600_claim_speaking.sql
current — 7 applied, none pending
```

Column and constraint as written:

```
speaking   text   nullable
CHECK (speaking = ANY (ARRAY['own-experience','vendor-about-own-product',
                            'relayed-from-elsewhere']))
```

**NULL appears on exactly the four rows that predate the field**, all four created
`2026-08-20 14:05:13`, one day before the migration. `SELECT speaking, count(*)`
returns a single group: `(None, 4)`. Nothing was back-filled — the check needs the
population the claim was resolved against, and re-deriving today against a
different fingerprint would record a verdict from the wrong population.

**The storage path works.** `claims.py` had been inserting a column that did not
exist. Proved by issuing the insert it issues, in a transaction, then rolling
back:

```
INSERT with speaking:  ('vendor-about-own-product', 'F')
CHECK rejects off-enum: CheckViolation
after rollback, claim rows: 4
```

---

## 2 · Per-claim salvage, and what it cost

`salvage_claims(raw_arguments)` builds each claim on its own and returns
`(built, unsalvaged, envelope_error)`.

**Not a retry ceiling.** A ceiling trades one all-or-nothing for a slower
all-or-nothing: the batch still stands or falls together, it just costs more
calls first. The correction loop does converge — `qwen-38-27b` went from 5
validation errors to 1 on its retry — and converging is not arriving.

### What it costs

| | |
|---|---|
| **code** | one function, one branch in `extract`, two record types. No contract change. |
| **calls** | none. Salvage runs on completions already paid for. |
| **a partially-valid batch is stored** | yes, and the invalid claims are recorded rather than dropped — `ExtractionRun.unsalvaged` holds `Unsalvaged(index, errors, raw)`, with the model's own dict. A count of losses is not evidence; the quote is. |
| **`proposed` now counts them** | a 14-claim document that stored nothing used to report `proposed = 0`, hiding the loudest signal in the run. |
| **what is not salvaged** | anything outside `claims`. `unclassified` and `no_claim_reason` live on the envelope, and the envelope is what failed — reading them from a broken parse would invent a finding about the capability vocabulary. |

### Two defects it exposed while being built

**Tokens were under-counted.** `run.input_tokens = completion.input_tokens` took
the final call only. The corpus run reported 75,985 input tokens across 30
documents **with 6 retries**, so six calls were unbilled in our own figures — in
the flattering direction. Now summed across every completion.

**A retry can be worse than what it replaced.** A first answer with one over-long
quote, retried, came back unreadable — and salvaging from the last completion
threw away eleven good claims in the first. Salvage now runs over every
completion and takes whichever yields most, logging when that is not the newest.

Both were found by a test failing for the right reason, which is the argument for
writing the test before believing the fix.

---

## 3 · A real zero and a validation zero are now different findings

```python
ZERO_SILENT      the model read the document and proposed nothing
ZERO_UNSALVAGED  every claim it proposed failed the schema
```

`ExtractionRun.zero_kind` carries it. Until today these read identically, which is
how `qwen-38-27b` was recorded as a clean nothing while holding fourteen claims.

Both are still zeros on the board. The difference is that one is a fact about the
corpus and the other is a fact about our plumbing, and only one of them should
ever appear in a coverage figure as "nobody discussed this".

---

## 4 · The five dark documents

Three of five now yield. Two are zeros — and are marked as such.

| document | before | after | note |
|---|---:|---:|---|
| `openai-timeline` | 0 | **12** | 1 unsalvaged |
| `introducing-muse-glimmer` | 0 | **1** | 1 unsalvaged, 1 verification-rejected |
| `stealing-reasoning-traces` | 0 | **1** | 1 unsalvaged |
| `auto-mode` | 0 | **0** | `zero_kind=unsalvaged`, 4 of 4 lost |
| `claude-opus-5-system-prompt` | 0 | **0** | `zero_kind=unsalvaged`, 1 of 1 lost |

**`auto-mode` is the third instance of `structured_mode` taking a string.** Four
claims lost to `'auto mode'` in a `bool | None` field meaning *"was provider-side
schema enforcement on"* — after `'xhigh'` on `qwen-38-27b`. The document is about
a feature called auto mode, and `Conditions` has no field for it, so the value
went to the nearest-shaped slot. Same mechanism as the missing capability key, in
`contract/conditions.yaml` rather than `capabilities.yaml`.

Both remaining zeros are one over-long quote or one bad `conditions` away from
yielding, and both are now visibly that rather than silently nothing.

---

## 5 · The capability key on 30 of 30 — and the evidence does not settle it

> ⚠ **§5's CENTRAL EXHIBIT DOES NOT REPRODUCE, AND WAS NEVER PERSISTED.**
> `openai-timeline`'s twelve `code.generation` claims — quoted below as the
> visible proof that misfiling happens past `unclassified` — came from one draw
> that was never written to disk. **Four draws at current HEAD return zero
> claims**, every one `zero_kind=silent`, with the stated reason *"describes an
> incident involving an experimental, unreleased OpenAI model, but does not make
> any claims"*, which is correct.
>
> So the sentence *"the evidence that the vocabulary is incomplete in general is
> strong"* is withdrawn. It rested on a population of **1 draw of 1 document out
> of 30**, and that population is not stated anywhere in this section — rule 7
> in the form that carries no figure.
>
> **The recommendation at the end of §5 is unchanged and is now better founded:**
> do not add a capability key on this evidence; build the instrument. Round 3 is
> built — `fixtures/golden/capability-choice-round3--unlabelled.jsonl`, 36
> claims — and it cannot label the twelve, because nothing recorded them.
>
> A separate finding found while building it changes what this section was
> measuring: **the extractor is shown the twelve capability keys as bare strings
> and never sees their `description` or `sounds_like`.** Misfiling under those
> conditions is not evidence of a vocabulary gap.
> `docs/measurements/the-effort-dimension.md` §4 and §5.

**`unclassified` collected one quote across all thirty documents:**

> *"Qwen's self-reported benchmarks for this model are eye-opening. They show a
> boost from both Qwen 3.6 27B and the closed-weight Qwen 3.7-Plus…"*

Zero from the five. So the direct evidence for a **token-spend or output-length
key is nil** — not one declined quote was about it, and the one that was declined
is about a vendor's self-reporting, which is a `speaking` matter rather than a
capability gap.

**But I am not going to report that as a clean negative, because the detector is
under-firing and it is visible.** `openai-timeline` produced **12 claims, every
one `code.generation`**, on a document that is a timeline of agents attacking an
Artifactory instance:

```
code.generation  "Agents successfully execute an SSRF attack on Artifactory"
code.generation  "Agents find and exploit a zero-day RCE on Artifactory"
code.generation  "The agents have remote code execution in Artifactory"
```

Those are not claims about a model's code generation. They are misfilings, and
`unclassified` was empty for that document — with the strengthened description
that names the misfiling case explicitly.

So the honest position, and it is two claims rather than one:

- **the evidence for a token-spend key specifically is nil**, on 30 of 30;
- **the evidence that the vocabulary is incomplete in general is strong**, and
  `unclassified`'s emptiness is weak evidence either way because misfiling is
  demonstrably happening past it.

**So the next instrument is not `unclassified`, it is the golden set.** Round 2's
`is_the_claim_sound` question already has `over-read` for *"the quote does not
support the claim attached to it"*, which is exactly what these twelve are. A
labelling round over these 42 claims would measure the misfiling rate directly
rather than relying on the model to volunteer it.

**Recommendation: do not add a capability key on this evidence.** Add the 42
claims to the golden set and label the capability choice. That replaces a guess
with a measurement, which is what the run was for.

---

## 6 · The yield movement, and what it is not

```
first run          8 claims,  4 documents
30 of 30          42 claims, 14 documents      x5.25 claims, x3.50 documents
```

Same 30 documents, same model, same 12 capability keys, same retrieval, same
prompt except one sentence. What changed:

1. **`maxLength: 200` moved from the schema's machinery into `quote`'s
   description**, phrased as the choice it implies. `qwen-38-27b` alone went 0 →
   11 with zero retries.
2. **`unclassified`'s description became a positive check** rather than a
   statement of purpose.
3. **Per-claim salvage** recovered 14 claims from 3 documents that had been
   reporting nothing.

**None of it is about capability, retrieval or vocabulary.** No new key, no new
query, no new corpus, no model change. The claims were being produced the whole
time and discarded by a per-document validator, or not produced because the
constraint the model needed was machine-readable rather than instruction.

### What it is not

**It is not a quality result.** 42 claims is more claims, not better ones — and
§5 shows at least 12 of them are probably misfiled. The yield movement and the
correctness question are separate, and the golden set is the only thing that can
speak to the second.

**And it is not a rate.** One corpus, 30 documents, one author, one site, one
extractor, single runs. `qwen-38-27b` alone produced 14, 13, 11 and 11 claims
across four calls, so the per-document counts carry real variance. What is not
variance is 0 → 11 on a document that failed twice, and 8 → 42 across a corpus.

The transferable finding is written separately, because it will recur:
`docs/measurements/a-constraint-not-in-the-description-is-invisible.md`.
