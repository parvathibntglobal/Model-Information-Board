# The constraint was machine-readable and not instruction

**`maxLength: 200` was in the tool schema the whole time. The `quote` field's
description never mentioned it.** So the model had the limit as JSON metadata
sitting beside `"title": "Quote"`, and no instruction about what it implied.

Putting the limit into the description took `qwen-38-27b` from **0 claims after
two failed attempts** to **11 claims with zero retries** — and made
`unclassified` fire for the first time in any run.

*Engineer 1 · 2026-08-21 · five probe calls, ~$0.02*

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

## 1 · The quote ceiling

### Your diagnosis, measured

```
claim 11   215 chars   sentence boundary at 63
           "I've been getting around 15-30 tokens a second from LM Studio."
           — 62 chars, carries the whole measurement

claim 12   208 chars   sentence boundary at 51
           "And sure enough, this gave me a significant boost."
           — 50 chars, and it LOSES the number. The 72% is in the second
             sentence, which is ~157 chars and fits on its own.
```

A compliant span existed in both. So the model ignored an instruction it already
had — *"Choose the SHORTEST span that carries the claim"* — and a bigger ceiling
would have admitted a longer quote onto a page for no reason.

**Claim 12 is also why truncation is wrong.** Its prefix verifies, reads cleanly,
and drops the measurement the claim is about. A silently shortened quote that
passes verification is a true quote carrying a false claim.

### What was actually missing

```
maxLength appears in the tool schema:  True
the string "200" appears:              True
quote's description:  'VERBATIM text from the source. No paraphrase, no
                       ellipsis, no repair.'
```

The limit was a validator, not an instruction. This is the prose-versus-field
finding one level in: **a constraint in the schema's machinery is not a
constraint in the schema's description**, and the model reads the description.

### The fix, and it is three sentences in one field

`quote`'s description now says: at most 200 characters, roughly one sentence,
count before answering, a longer quote takes every other claim down with it —
and *"it may be the second sentence rather than the first, because the
measurement is often at the end"*, which is claim 12 written into the field.

```
qwen-38-27b, three runs of the same document

  before                      proposed 14, TWO validation errors, 0 kept
  targeted retry only         proposed 13 -> 1 error, retry, 0 kept
  limit in the description    proposed 11, retries 0, 11 KEPT
```

**Zero retries.** The specific retry (below) went from being the fix to being the
backstop, which is the right place for it.

### The retry is still better, and it needed fixing twice

`_quote_length_correction` replaces the schema error with an instruction naming
each claim, its length and the overage. Worth keeping because the description is
not a guarantee.

**Its first version was all-or-nothing on mixed error types** — a batch with four
bad `conditions` and one long quote fell back to the generic message and lost the
specific instruction with it. That is the exact shape it was written to fix,
reproduced inside the fix. Now additive: the quote instruction plus the other
errors verbatim.

### A second failure this surfaced

Between runs the model put `'xhigh'` into `Conditions.structured_mode`, a
`bool | None` meaning *"was provider-side schema enforcement on"*.

`xhigh` is the document's **reasoning effort**. `Conditions` has `tool_count`,
`context_size`, `structured_mode`, `framework`, `hosted_by`, `domain` — and **no
reasoning-effort field**. So the model put it in the nearest-shaped slot.

**Same failure as the missing capability key, one file over.** No field for the
thing, so it goes somewhere wrong rather than nowhere. `contract/conditions.yaml`
is where that would be fixed, and this document is entirely about
`reasoning_effort: xhigh | medium | low`.

---

## 2 · `unclassified` fires, and the cause was (a)

**It was the prompt not asking clearly, not the model refusing to decline.**

The evidence for the other hypothesis looked strong: 14 claims, every one with a
key, several stretched — *"it defaults to wildly overthinking things"* filed under
`over_refusal`. That reads like a model that maps rather than abstains.

But a sentence added to the *prompt* last turn (*"USE IT. A quote you decline to
classify and do not record here is a capability nobody learns is missing"*)
changed nothing. Rewriting the **field's own description** as a positive check did:

> *"BEFORE YOU ANSWER, CHECK EVERY CLAIM YOU MADE. For each one, ask: does the
> capability key you chose actually name what the quote is about? If it does not,
> DO NOT pick the nearest one — remove that claim and put its quote here
> instead."*

```
qwen-38-27b     UNCLASSIFIED: ["Qwen's self-reported benchmarks for this model
                are eye-opening. They show a boost from both Qwen 3.6 27B and
                the closed-weight Qwen 3.7-Plus…"]
```

**First non-empty `unclassified` in any run of this project.** The detector has
fired, so it can fire, and the reason it never had is that nothing asked the model
to check — the same answer as the quote limit, in the same place.

### What it did not fix, stated rather than glossed

The quote it declined is about **self-reported benchmarks**, not verbosity. The
description explicitly says *"if a quote is about how many tokens a model spends
… there is NO KEY FOR THAT"*, and the verbosity observations still went to
`ops.latency_ttft` (2) and `over_refusal` (1) rather than to `unclassified`.

So the mechanism works and the specific gap it was aimed at is only partly
surfaced. `over_refusal` fell from 3 to 1 across runs, which is movement in the
right direction and not a measurement — see the caveat below.

### And `deepseek-v4-pro-0813` went from 0 claims to 1

`reasoning.multistep`, and `unclassified` empty. The document whose stated reason
was previously *"too vague to map to a specific capability"* now produces a claim.
Whether that claim is a good reading is a golden-set question, not a run question.

### The caveat that governs all of this

**Claim counts across the four runs of `qwen-38-27b` were 14, 13, 11 and 11.**
The extractor is nondeterministic and these are single runs. What is not
run-to-run noise:

- 0 kept → 11 kept is a step change, not variance;
- `retries 1 → 0` is a step change;
- `unclassified` has never been non-empty before and now is.

The capability distribution is noise until it is measured over the corpus. **Do
not read `over_refusal` 3 → 1 as a fix.**

---

## 3 · The thread-root instruction — and yes, it is checkable

This is the real prompt gap and I have not changed it. Reporting only.

### The instruction

The prompt says nothing about the thread root. `wrap_untrusted(flattened_text)`
hands the model root and children as one string, so the extractor has been
inheriting the subject with no guidance and no record. Proposed wording, for the
**`ModelRef.surface` description** rather than the prompt, on the evidence above
that a field description is where an instruction lands:

> **If the sentence you are quoting does not name a model, and you are attributing
> it to one named elsewhere in the document, say which surface you used and where
> you got it.** A thread root announcing a model establishes a subject its
> comments inherit — *"Introducing Claude Fable 5"* followed by *"it's much
> faster"* is a claim about Fable 5. That inference is usually right and it is
> yours to make. What is not acceptable is making it silently: a claim whose quote
> names no model, recorded as though the quote did, cannot be audited.

### Whether anything can check it — yes, in code, with no model

```python
# does any population surface appear IN THE QUOTE?
stated = bool(resolve(claim.quote, population))
```

Run against the four stored claims:

```
STATED     surfaces_in_quote=13   "So when Fable's classifiers detect a request…"
INHERITED  surfaces_in_quote=0    "We'll keep refining the safeguards to reduce…"
INHERITED  surfaces_in_quote=0    'exceptional performance in software engineering'
INHERITED  surfaces_in_quote=0    'gives 10%+ better results on SWE-Bench'
```

**3 of 4 inherited, and every row records `specificity=version` with nothing
saying the subject came from elsewhere.**

The check is deterministic, needs no model, and reuses `entity.resolve` — which is
already the resolution path. It is the same shape as quote verification: **the
model proposes an attribution, and code checks whether the quote supports it.**

So the answer to *"is this an instruction nothing verifies"* is no, and that is
what makes it worth adding. Concretely it wants two things, neither built:

1. **`subject_inherited: bool` derived in code**, not asked of the model — the
   check above, run at verification time and stored. Deriving it removes any
   chance of the model asserting it falsely, which is why this is better than a
   field the model fills.
2. **A ruling on what an inherited subject may do.** It is orthogonal to
   `speaking` — an inherited subject can be perfectly snapshot-specific — and it
   interacts with `gate.count`, because N comments inheriting one root's subject
   are N voices for one act of naming. `max_thread_share` is the outstanding ask
   there.

Both are E2 sign-off. Neither is in flight.

---

## What changed

| file | change |
|---|---|
| `judge/extract/schema.py` | `quote`'s description states the limit and what it implies; `unclassified`'s description is a positive check |
| `judge/extract/runner.py` | `_quote_length_correction` — a targeted retry naming each claim and its length, additive across error types |

Suite: **1,954 passed.** No contract change, no sign-off needed for either.

Not changed: the prompt's *"a claim a human made"* line, the thread-root
instruction, `contract/capabilities.yaml`, `contract/conditions.yaml`. The
capability-key argument is now better evidenced than it was — `unclassified` has
started collecting — and it should be made from a corpus run rather than from one
document.
