# For Yathu — four rows

**One ask. Rows 0, 1, 2 and 3 of the round-2 file you already have.**

Two questions each, so eight answers. That is the whole request.

```
file   fixtures/golden/extraction-reading-round2--labelled-by-yathu.jsonl
rows   0, 1, 2, 3        (the four reddit-thread claim rows)
each   who_is_speaking   +   is_the_claim_sound
```

Nothing else needs re-doing. Your other 34 rows are in and are being used.

---

## Why these four and not the others

All four are quotes from a root post by `ClaudeOfficial` announcing their own
model. They are the only rows in either pool that test
`vendor-about-own-product`.

That value is now **built and required** on every claim, and it sets the
evidence tier — `vendor-about-own-product` weights a claim at **0.02 against
1.00** for a first-hand report. A sixfold-plus difference in what a claim
contributes, decided by a field whose only supporting labels are **four rows
labelled by one person.**

So right now the strongest weighting decision in the pipeline rests on an
uncorroborated category. Your four answers either corroborate it or they do not,
and both outcomes are useful. If you read those quotes as
`relayed-from-elsewhere` rather than `vendor-about-own-product`, that is a real
finding about the option text and I would rather know now than after the tier
mapping is load-bearing.

**Please do not look at anooj's file first.** Two independent readings is the
entire point; a second reading of the first one measures nothing.

---

## Two other things exist and neither is this ask

Listing them so you know they are queued, **not so you do them now.** If you
only have time for one thing, it is the four rows above.

| | what | when |
|---|---|---|
| **2** | the other 10 blank round-2 rows — 4, 5, 6, 7, 8, 9 (reddit document rows), 10, 11, 12 (blog claim rows), 21 | after the four |
| **3** | round 3, `capability-choice-round3--unlabelled.jsonl` — 36 rows, one question each, capability choice | not started, no deadline from me |

Round 3 is the bigger job and the less urgent one. It measures whether the
extractor picks the right capability key, and it cannot be started wrong — the
pool is built, shuffled and stable, and it will be exactly as valid in a week.

The four rows are urgent because a field is already shipping on top of them.
