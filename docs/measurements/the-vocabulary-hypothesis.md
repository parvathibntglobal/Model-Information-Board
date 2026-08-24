# If most claims have no key that fits, the vocabulary is the wrong shape

**A HYPOTHESIS, NOT A RESULT. Nothing here has been measured.** It is written
down so the second labelling of round 3 tests a stated prediction rather than
producing a number that gets interpreted afterwards.

---

## 0 · What exists, and what does not

Stated first because the arithmetic below rests on a figure this repository does
not contain.

```
fixtures/golden/capability-choice-round3--unlabelled.jsonl     36 rows, answers all null
fixtures/golden/capability-choice-round3--*labelled*           DOES NOT EXIST
```

**There is no first labelling of round 3 on disk.** `no-key-fits` appears in the
repository exactly twice: as an option in the pool, and in prose. So the figure
this document reasons about — *26 of 42* — is **not a measurement made here**,
and it is recorded as a prediction attributed to E1 rather than as a count.

**And the denominator does not match the pool.** Round 3 has **36 claims**, not
42. `42` was an earlier figure, and it was `28 + 14` where the 14 came from a
re-run that was never persisted and does not reproduce
(`the-effort-dimension.md` §4). The pool was built from one coherent 30-document
draw, which produced 36.

That changes the number and not the hypothesis:

```
26 of 42   =  61.9%
26 of 36   =  72.2%
```

Both are a majority and the hypothesis is about the majority, so it survives
either denominator. But the two figures are not the same claim, and rule 7 is
that a figure travels with the population it was drawn from. **If a first
labelling reports 26, it must say 26 of what.**

---

## 1 · The hypothesis

> **If a majority of claims come back `no-key-fits`, the finding is not a
> missing capability key. It is that the twelve keys do not describe what
> engineers write about.**

Twelve keys. A majority of real, verified, quote-backed claims that none of them
names. That is not a gap in a list — a gap is one or two keys, found by a
detector, added by a PR. A majority is a **category system built for the wrong
corpus.**

And the detector agrees it is not measuring this: `unclassified` collected
**one** quote across 30 documents, and that quote was about a vendor's
self-reported benchmarks, which is a `speaking` matter rather than a capability
gap. A detector that finds one where a labeller finds twenty-six is not
under-tuned. It is answering a different question.

## 2 · Why this is a hypothesis and not a conclusion

Four reasons, in the order that would change the answer.

**The extractor was never shown what the keys mean.** `build_system_prompt`
appends the twelve keys as bare strings; `description` and `sounds_like` in
`contract/capabilities.yaml` do not reach the model — verified, zero hits for
every description fragment and every `sounds_like` phrase. The labeller **is**
shown both. So a `no-key-fits` label may say the vocabulary is wrong, or it may
say *the extractor picked a key it could not have picked well*, and those have
opposite fixes. This is the single largest confound and it is not small.

**One labelling is not a measurement.** Round 1's claim-row labels had to be
discarded entirely once it emerged that three of four disagreements were quotes
from a vendor-authored root post that no row identified. A first labelling
establishes what one reader saw.

**`no-key-fits` and `not-a-capability-claim` are separate options for exactly
this reason.** If the 26 are mostly `not-a-capability-claim`, the finding is that
the extractor is over-producing — claims about incidents, prices and companies
that should never have been claims — and the vocabulary is fine. If they are
mostly `no-key-fits`, the vocabulary is the story. **A merged count of the two
cannot distinguish these and must not be reported as one number.** That merge is
precisely what made `unclassified` unable to argue for anything.

**The corpus is one author on one site.** 36 claims, 15 documents, one voice.
"What engineers write about" is a claim about engineers; this is a claim about
one engineer's blog. A vocabulary can fail badly on one writer's subject matter
and fit a Reddit thread well.

## 3 · What the second labelling tests

Stated now, so the second reading is a test rather than an interpretation:

| if the second labelling shows | then |
|---|---|
| `no-key-fits` again in the majority, **and** the two labellers agree on *which* rows | the hypothesis holds. The vocabulary is the wrong shape and the next step is re-deriving keys from the corpus, not appending to the list |
| a majority, but the labellers pick **different rows** | the instrument is unreliable at 15 options and the figure is not yet evidence. Fix the option text before believing either count |
| mostly `not-a-capability-claim` | the extractor is over-producing. The vocabulary is not the problem and `capabilities.yaml` should not be touched |
| a small minority | the first labelling was one reader, and the standing conclusion — *do not add a key* — needs no revision |

**The pre-registered arithmetic**, so it cannot be chosen after the fact: report
labeller-vs-labeller agreement on the **binary** (did the labeller pick the key
the extractor picked), not a 15-way kappa on 36 rows. Report `no-key-fits` and
`not-a-capability-claim` as separate counts. Both with the denominator attached.

## 4 · What would follow if it holds, and what would not

**Would follow:** the keys get re-derived from the corpus rather than extended.
That is a `contract/capabilities.yaml` rewrite, two queries per key in
`queries.yaml`, a half-life per key in `judge/vet/weight.py`, and every stored
claim re-filed — a re-run, not an edit. Expensive, and cheaper now than at any
later point, since the table holds **4 claims**.

**Would not follow:** that the board cannot be built. Rule 4 already covers a
capability nobody has discussed. A vocabulary that misses most of what people
write about does not produce wrong cells — it produces **empty** ones, which
render as silence and are honest. The cost is coverage, not correctness.

**And it is not the reason the board currently says nothing.** That is one
author across 64 documents, against a gate needing three effective voices across
two platforms. The capability vocabulary could be perfect and every cell would
still read `insufficient`. `docs/engineer-1/whats-next.md`.
