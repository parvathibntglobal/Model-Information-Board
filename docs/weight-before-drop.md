# An unmeasured check ships as a weight, not a gate

**Agreed by both engineers, 2026-08-28.** Recorded as a rule rather than a
precedent, because the same argument has now settled two designs in two lanes
and the second time is when a coincidence becomes a pattern.

---

## The rule

> **A check whose accuracy has not been measured must not gate on the decision
> it would be making.** It ships as a weight, a flag, or a recorded field, and it
> is promoted to a gate only when its error rate has been measured against
> something it did not choose.

## Why, and it is rule 4 wearing a different hat

The asymmetry is in what the two failure modes leave behind.

```
A GATE that is wrong        drops the document. Its false positives are
                            INVISIBLE - the evidence is gone, the page shows an
                            absence, and an absence reads as a considered answer.
                            Nothing accumulates that would tell you the check
                            was wrong.

A WEIGHT that is wrong      keeps the document and mis-ranks it. Its errors are
                            visible, recoverable, and countable - and the corpus
                            it builds is exactly the evidence needed to decide
                            whether it should have been a gate.
```

So a gate is not merely riskier. **A gate destroys the measurement that would
justify it**, and a weight generates it. That is why the direction is one-way:
weight first, gate later on evidence, never the reverse.

This is rule 4 (*"silence is not criticism"*) applied to our own machinery
rather than to the corpus. Rule 4 says an absence of evidence must not render as
evidence of capability. This says an absence *we caused* must not render as an
absence *we found*.

## The two instances

**1 · `speaking` on `ModelRef`.** The extractor can tell first-hand use from a
vendor announcement, and the evidence tier that follows changes a claim's weight
sixfold. It ships as a **field on the claim** rather than as a rejection,
because the tier assignment was unvalidated and a wrong rejection would have
removed the quote that proved it wrong.
`docs/proposals/for-engineer-2-a-speaking-field-on-modelref.md`.

**2 · The 8★ bot layer.** Layer 1 has three inputs that are free in the listing
payload — `distinguished`, `stickied`, `author_fullname` — and they are rare:
3 and 4 hits in 3,200 posts. **A validation set drawn from one sweep has ~7
positives**, which cannot measure a false-positive rate. So 8★ ships as a
weight until the derived list validates. Issue #175 carries the measurement.

The 8★ case adds something the `speaking` case did not have: **the reason the
check cannot be measured yet is the same rarity that makes it attractive.** A
signal that fires on 0.2% of documents is valuable precisely because it is
selective, and selective is what makes its error rate unmeasurable on a small
corpus. That is not an argument against the check. It is an argument that the
corpus has to arrive before the gate does.

## What would revise this

A check whose error rate is measured against a population it did not select.
That is the whole condition, and it is deliberately about the *population* rather
than about confidence: a check validated on documents it chose is the
proposer-and-checker problem rule 1 exists to prevent, one layer up.

**Not revised by:** the check looking obviously correct, the false-positive rate
seeming small, or the gate being cheaper to implement than the weight. All three
were true of the `judge/` hard filter that read an absent `supports_tools` as
"cannot" and took a candidate list from 11 models to 1.

## Where this is enforced

Nowhere, and that is stated rather than left to be discovered. There is no test
that refuses a new gate, because a test cannot tell a measured check from an
unmeasured one — the measurement lives in a document, not in the code.

So this is a rule the reviewer applies, and the question to ask of any new
filter is: **what population was its error rate measured on, and did the filter
choose that population?** If there is no answer, it is a weight.
