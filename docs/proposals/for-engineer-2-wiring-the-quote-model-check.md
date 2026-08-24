# For Engineer 2 — the quote-model check, and the three products it could be

**Built, tested, counted, and not wired to any consequence. Proposing rather than
taking, because two of the three options store a column.**

`judge/pipeline.py:quote_subject_verdict` resolves a claim's quote and compares
what it names to the model the claim is filed against. No model call — the
extractor proposes the attribution, code checks whether the quote supports it,
which is quote verification's own argument applied to the subject.

**Your lean is store-and-flag and I agree, for the reason you gave.** The
argument below is why the other two are worse, and what store-and-flag needs from
you.

*Engineer 1 · 2026-08-21 · 11 tests, suite 1,999*

---

## The gap it closes

```
verification   proves the quote is real          judge/extract/verify.py
resolution     proves the model exists           collect/surface_resolver.py
NOTHING        proved the quote mentions the model
```

**A claim could be verified, attributed, and about a different model than the
page it renders on.** Three of the five quotes on `/models/openai/gpt-5` were
about GPT-5.6 variants, each with a working permalink.

> Read as the motivating case and not as a rate: those five came from a
> population I had built wrong, so they measure my query rather than the
> pipeline. The gap they exposed is real and independent of how they got there —
> **nothing in the chain compares the quote to the model** — which is what this
> check closes.

## What it says about the six stored claims — and it is mostly "nothing wrong"

**Leading with this, because a check that fires on five and means one is a check
somebody mutes.**

```
claude-opus-4.6   code.generation        names-nothing        legitimate
claude-haiku-4.5  instruction.adherence  names-the-model      agreement
claude-fable-5    code.generation        names-nothing        legitimate
claude-fable-5    code.generation        names-nothing        legitimate
claude-fable-5    over_refusal           names-nothing        legitimate
claude-fable-5    over_refusal           names-another-model  FLAGGED
```

**Five of six say nothing is wrong, and four of those five say it for the same
good reason:** the quote names no model, because its subject came from the thread
root or from an earlier sentence. That is the normal way people write, and
`subject_inherited` already names it.

**That composition is what makes the column safe to store.** Without it,
`names-nothing` on four rows out of six looks like a check that mostly cannot
tell — and a reader would treat the fifth state as noise of the same kind. With
it, `names-nothing` is a POSITIVE statement that a specific, expected, legitimate
thing happened, and `names-another-model` is the only value that asks for
attention. One row in six, not five.

A check whose common value means "fine, and here is why" survives contact with a
reviewer. A check whose common value means "no answer" gets muted in a week.

## Four states, and the fourth is load-bearing

```
QUOTE_NAMES_NOTHING               the quote names no model        LEGITIMATE
QUOTE_NAMES_THE_MODEL             agreement
QUOTE_NAMES_ANOTHER               a different model               the defect
QUOTE_NAMES_SOMETHING_UNCOMPARED  named, but no resolver supplied
```

`subject_was_inherited` is now a **projection** of this — `verdict is
QUOTE_NAMES_NOTHING` — so the two cannot disagree about the same quote. As
siblings each would call `find_surfaces(quote)` and reach its own conclusion, and
`subject_inherited=False` beside *"the quote names nothing"* is a contradiction
reported in two places, which is to say invisible.

The fourth state exists because folding it into `None` regressed
`subject_was_inherited` from `False` to `None`: **its** question is settled by the
surface list alone, so a missing comparison must not unsettle it.

---

## Three products, and only one is a gate

| | what it does | what it costs |
|---|---|---|
| **refuse at extraction** | the claim never exists | **a gate on an unmeasured check.** Every false positive is evidence destroyed with no record. The live false positive below would have been silently discarded |
| **store flagged** | claim stored, disagreement recorded per row | one column, one contract change, and the flag is auditable and reversible |
| **report for review** | counted and logged only — **today's behaviour** | nothing persists, so nobody sees it unless they read a log |

### Why store-and-flag, in your words and mine

**Yours:** the check has never run, and its accuracy is unmeasured on exactly the
decision it would be making. That is the `speaking` argument — weighting rather
than storage until the golden set can speak to it — and it applies harder here,
because refusing destroys the evidence that would let anyone measure the check.

**Mine, and it is a measurement rather than a principle:** the check has a
**known false-positive class** and it is live right now.

```
claim   clm_ab1788eaed811277a85ecbe4   anthropic/claude-fable-5 / over_refusal
quote   "So when Fable's classifiers detect a request related to cybersecurity,
         biology and chemistry, or distillation, the response is handled by
         Claude Opus 4.8"
verdict QUOTE_NAMES_ANOTHER
truth   the attribution is DEFENSIBLE - the quote's subject is Fable's
        classifiers, and Opus 4.8 is the fallback it mentions
cause   `Fable's` is a possessive of a bare family word, and family words are
        excluded from the surface population, so the finder sees Opus 4.8 and
        not Fable
```

**So the check's precision is governed by `FAMILY_WORDS`** — the ruling still open
with you. A gate wired to it today would refuse claims whose subject is named by
a family word, which is a large and un-measured population.

**1 of 6 stored claims flagged, and the one is probably correct.** That is not an
argument against the check; it is an argument against making it a gate before the
golden set has labelled attribution, which nothing currently does — round 3 asks
about the capability, not the subject.

And the ratio that argued for urgency has been withdrawn. I wrote that the board
surfaces mis-attribution preferentially, on 3 of 5 quotes on the GPT-5 page —
which came from a population I had built wrong rather than from the pipeline. On
the claims that remain there is **no over-representation**: 1 of 6 stored, and 1
of the 2 quotes in its own cell. The narrower true statement is that a
mis-attributed claim renders exactly as readily as a correct one, which is reason
enough to check and not reason to gate.

---

## What store-and-flag needs, and it is a contract change

**Not taken. This is the ask.**

```sql
ALTER TABLE claim ADD COLUMN quote_subject text
  CHECK (quote_subject IN ('names-nothing','names-the-model',
                           'names-another-model','names-something-uncompared'));
```

Four things I would want decided rather than assumed:

1. **the column is nullable and NULL means "not checked"**, not "agreed". Every
   row written before it existed is NULL, and rule 6 says that has to stay
   distinguishable from a check that ran and found agreement.
2. **it does not feed a weight.** `f_*` has no factor for it and should not: the
   check's accuracy is unmeasured, and a weight is a silent decision. If it ever
   does, that is a separate ruling with a measurement behind it.
3. **it does not feed the gate.** `gate.count` counts voices; a flagged claim is
   still one person saying one thing, and whether it counts is exactly the
   question this cannot yet answer.
4. **it is renderable, and that is the point.** A `/filtered`-style page listing
   flagged claims is the instrument that would let someone label them — which is
   how the check's accuracy gets measured, which is what unblocks every other
   option.

`subject_inherited` is the sibling column already proposed and unsigned. **These
two want deciding together**: they are derived from one resolution, they have the
same standing, and shipping one without the other leaves half a signal in the
schema.

---

## Not done, and one thing I declined

**No deletion.** The instruction was to delete the one mis-attributed claim, and
the premise had moved: the GPT-5.6 rows were deleted last turn, so `openai/gpt-5`
holds **0 claims and renders 12 unreported with 0 quotes**. There is nothing left
on that page to confirm after a delete, and no claim in the table quotes GPT-5.6.

The claim the check flags today is the Fable/Opus 4.8 row above, which is a
different case and probably correctly attributed. Deleting it would remove real
evidence on the verdict of a check whose accuracy is unmeasured — which is the
argument for store-and-flag, applied to the row rather than to the design.

Say the word and it goes. But the six deleted earlier turned out to be correct
evidence removed for a defect in my measurement of them, and this has the same
shape.
