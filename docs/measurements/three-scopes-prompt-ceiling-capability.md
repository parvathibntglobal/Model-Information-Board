# Three scopes: the prompt, the quote ceiling, the missing capability

**Nothing changed. This is the scoping.**

Short answers, and one of them reorders itself under measurement:

1. **The prompt should say almost nothing about `speaking`** — the field's own
   description is 1,075 characters, 38% of the whole system prompt, and it is
   attached to the value being chosen. What the prompt needs is **one line
   changed, not a paragraph added**, because its existing framing now contradicts
   the field.
2. **Per-claim validation, not truncation.** A truncated quote still verifies and
   can drop the clause carrying the claim, which is this project's named failure
   mode. Measured: `qwen-38-27b` proposed **14 claims, 2 over the ceiling, 12
   lost**.
3. **A capability key costs two contract files, a sweep change and ~11 queries
   per platform** — and the measurement below weakens the case for doing it
   first, because the model did *not* fail for want of a key. It mis-filed
   instead.

**Do the quote ceiling first.** Your prior is right, and it now has a mechanism:
fixing the ceiling is what surfaces the capability problem, so the order is
forced rather than chosen.

*Engineer 1 · 2026-08-21 · one probe call, 5,217 in / 1,199 out*

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

## 1 · The prompt, and the answer is nearly nothing

`speaking` is a required enum. Its description carries the three values, an
example of each, and the rule that matters:

> *"A VERBATIM QUOTE FROM AN ANNOUNCEMENT IS vendor-about-own-product OR
> relayed-from-elsewhere, NEVER own-experience, however exactly it is quoted.
> Quote verification cannot catch that mistake — the sentence really is in the
> text — so this field is the only place it can be caught."*

```
speaking's description      1,075 chars   38% of the whole system prompt
system prompt              2,819 chars   17 non-blank lines
tool schema                8,367 chars   the model reads this while answering
```

**A paragraph in the prompt would be smaller than the description and further
from the decision.** That is the prose-versus-field problem exactly, and the
field is now the larger half of it.

### What the prompt can stop saying: nothing, because it never said it

The prompt has no provenance instruction to remove. That is the good case — the
field arrived into a gap rather than into a competition.

### What it must not gain

**A line telling the model to skip vendor copy would silently implement a storage
gate in prose**, against the ruling that `speaking` weights and never gates. The
prompt currently contains no such line, and the risk is a future editor adding
one because it reads as tidying. Worth a comment in `prompt.py` saying so, not an
instruction.

### The one real change: the prompt's framing now contradicts the field

```
WHAT YOU RECORD
  One entry per claim a human made about a named model.
```

**A vendor announcement is not a claim a human made**, and
`vendor-about-own-product` is now a legitimate answer to a required field. So the
prompt tells the model to emit nothing for a document the schema asks it to
classify. Three of the four claims already stored are exactly that case.

That is a one-line fix — *"a claim somebody made"*, or *"a claim made about a
named model, by whoever made it"* — and it is a correction rather than an
addition. **My recommendation: change that line, add a comment about the storage
gate, add no paragraph.**

---

## 2 · The quote ceiling — per-claim, not truncation

### What was lost, measured

A probe of `qwen-38-27b` capturing the model's answer before validation:

```
claims proposed                 14
quotes over MAX_QUOTE_CHARS       2   (indices 11 and 12, 215 and 208 chars)
claims lost                      12
speaking on all 14        own-experience
capability keys used      code.generation 5, over_refusal 3, ops.latency_ttft 3,
                          context.effective_window 1, extraction.faithfulness 1,
                          reasoning.multistep 1
```

Twelve first-hand claims from one document, discarded because two quotes were
8 and 15 characters too long.

**And the two that overflow are the two that carry numbers:**

```
[11] 215ch  "I've been getting around 15-30 tokens a second from LM Studio…"
[12] 208ch  "…this gave me a significant boost. I had GPT-5.6 in Codex run a comparative…"
```

So the ceiling is biased against exactly the quotes that carry measurements —
the thing `f_specificity` rewards through `has_numbers`. A quantitative claim
needs more characters to stay verbatim, and the ceiling is where it dies.

### Retrying harder is not the fix, and that is already evidenced

`_call_with_one_retry` re-prompts once with the validation error verbatim —
*"Your previous answer did not satisfy the schema: … Answer again, correcting
exactly that."* On this document it named `claims.10.quote` and the second answer
came back with `claims.10` **and** `claims.11` too long. The correction loop works
as designed and did not help.

### Truncation with a marker: no

A 200-character prefix of a real span is **still an exact substring**, so
verification would pass. That is the problem, not the reassurance:

- the clause carrying the claim is often at the end — *"…That's not terrible, but
  it means a long reasoning trace takes minutes"* truncated at 200 keeps the
  measurement and loses the consequence;
- rule 1's guarantee is that the quote is what the person wrote. A silently
  shortened quote that verifies is **a true quote carrying a false claim**, which
  is the failure this project has recorded twice and the one verification cannot
  catch;
- published content is *quote + attribution + link*, so a truncated quote reaches
  a page.

If truncation happens at all it must be the model's job, not the pipeline's — and
the prompt already asks for it (*"Choose the SHORTEST span that carries the
claim"*), which is the instruction that did not hold.

### Per-claim validation: yes, and what it costs

```
judge/extract/runner.py   `_parse` validates ExtractionResult as a whole today.
                          Per-claim means validating `claims[i]` individually and
                          keeping what passes.

                          The retry decision changes: retry when NOTHING
                          validated, not when anything failed. Otherwise a
                          14-claim answer with one long quote costs a second call
                          for no gain.

                          A place to record the drops. `ExtractionRun.rejected`
                          holds `(ExtractedClaim, Rejection)` — a schema-failed
                          claim has no `ExtractedClaim` to pair, so this needs a
                          new list of (raw dict, error).
```

One module, no contract change, no sign-off. **The drop must be recorded** — a
silent partial accept is how "12 of 14" becomes indistinguishable from "14 of
14", which is the same class as the `f_specificity` constant.

One risk worth stating: per-claim acceptance means the pipeline uses part of an
answer the model got partly wrong. Today it uses none of it. I think partial is
right — the 12 valid claims are not made wrong by the 2 invalid ones — but it is
a change in what "the model's answer" means, and the rejected count becomes a
quality signal that should be watched rather than assumed small.

---

## 3 · A capability for token spend — and the measurement weakens the case

### What it costs

**Two contract files, both shared, both needing sign-off:**

```
contract/capabilities.yaml   a new entry: key, failure_mode, description,
                             sounds_like. The header says changes go through a
                             PR because both lanes depend on the keys.

contract/queries.yaml        TWO rows, one per stance (negative and positive) -
                             every existing capability has exactly 2. Each needs
                             subject/topic/signal term lists, and optionally
                             records_condition.
```

**And it is a sweep change, not only a schema one.** `capabilities.yaml`'s own
header: *"EVERY CAPABILITY MUST HAVE A HARVEST QUERY (FR-7). Harvest is entirely
query-driven: a capability nobody searches for has empty cells forever. Adding
one here without adding its query is a no-op — and the build check will fail."*

Measured from `harvest_run`, 153 rows over 121 distinct query strings:

```
~11 queries per capability per platform   (11 aliases x 1 topic term on GitHub)
some reach 22-25 where a query matches two capabilities' topic terms
```

So one new capability is roughly **11–22 additional GitHub requests per sweep**,
plus Reddit's own expansion. Against the observed RapidAPI quota (998,754
remaining) that is negligible; GitHub's rate limit is the binding one.

**A fourth file, easily missed:** `judge/vet/weight.py` holds the decay sets.
`ops.latency_ttft` is in `_FAST_DECAY` at a 30-day half-life. Token spend moves
with model updates, so a new key needs a half-life chosen, and omitting it
defaults to `HALF_LIFE_DAYS_SLOW` — a silent default in the weighting path, which
is the thing just ruled against.

### And the probe says the model did not fail for want of a key

This is what reorders it. Of the 14 claims `qwen-38-27b` proposed, **every one
found a capability key**:

```
ops.latency_ttft   3   "it feels slow—especially when it starts over-thinking"
                       "I've been getting around 15-30 tokens a second"
over_refusal       3   "it defaults to wildly overthinking things"
                       "It took 21 minutes… 22,276 reasoning tokens to produce
                        3,223 tokens"
```

**Nothing went to `unclassified` because nothing needed to.** The model put
verbosity under `ops.latency_ttft` where it plausibly fits, and under
`over_refusal` where it does not — *"it defaults to wildly overthinking things"*
is not an over-refusal, and neither is a reasoning-token count.

So the failure is not *"no key, so no claim"*. It is ***"no key, so a mis-filed
claim"*** — which is worse in one way and better in another. Worse, because a
claim at `over_refusal` will be counted toward over-refusal consensus on a
document about verbosity. Better, because it means the extraction path is not
blocked and the key can be added later without re-running anything that failed.

It also explains why `unclassified` stayed empty on `deepseek-v4-pro-0813` and is
empty everywhere: the model would rather stretch than abstain, and the prompt's
*"Do not stretch a quote to fit a capability"* is losing to the fact that every
claim must carry a key from the list.

---

## 4 · The order, and why it is forced

**Quote ceiling first.** Not only because it discards correct work, which was the
prior, but because:

- it is one module, no contract change, no sign-off, and reversible;
- **it is the change that surfaces the capability problem.** Fixing it recovers
  12 claims from `qwen-38-27b`, of which 3 are at `ops.latency_ttft` and 2 more
  are verbosity mis-filed as `over_refusal`. Those mis-filings are currently
  invisible because the whole document is discarded before anything sees them.
  The capability argument needs that evidence to be made properly, and today it
  is behind the ceiling.
- and it is the failure that reports as a clean zero. `no_claim_reason` said
  *"extractor returned nothing parseable against the schema"* and the run
  recorded 0 for that document. The missing key at least produced a stated
  reason.

**The prompt line second** — it is one line and it costs nothing, but it changes
what the model emits, so it should not be in flight while the ceiling change is
being measured.

**The capability key third**, and by then with real evidence: a count of how many
recovered claims land at `ops.latency_ttft` or `over_refusal` while being about
token spend. That is the argument for a new key, and it does not exist yet.

None of this touches `gate.count`, so none of it changes whether anything
corroborates.
