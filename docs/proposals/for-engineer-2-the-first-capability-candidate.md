# The first capability candidate arrives before the table has a writer: token spend and price-per-capability

**Three independent routes to one missing key.** Not three readings of one
measurement — three different mechanisms, on three different corpora, none of
which was looking for this.

This is the evidence `capability_candidate` was built to accumulate, and it
accumulated without the table. Worth deciding on its own merits rather than
waiting for a wire-up to produce a first row.

*Engineer 1 · 2026-08-28*

---

## 1 · The three arrivals

**1 · `judge/extract/runner.py` recorded the gap in its own docstring, 2026-08-21.**
On `ExtractionRun.unclassified`, about `deepseek-v4-pro-0813`:

> *"The capability really is missing — the 12 keys contain one `ops` entry,
> `ops.latency_ttft`, and nothing for token spend or output length — so the signal
> designed to catch a missing capability failed on the missing capability."*

And immediately after: *"Three first-person token-efficiency reports are off the
board for three different reasons and this is one of them."*

**2 · The blog extraction run's `unclassified` pointed at it.** Same shape: quotes
that say something about a model, fit no key, and the `no_key_fits` reason named
vagueness rather than the real absence. The signal built to detect a missing
capability could not detect this one, because a report about token spend reads as
"too vague to map" against twelve keys that have no slot for it.

**3 · The withheld-list classification, 2026-08-28: 51 of 552 proposals cluster
here.** With the twelve-key list removed from the prompt, the classifier named
capabilities in its own words over 774 documents. 528 distinct names came back —
near-total fragmentation — but one cluster recurs:

```
efficiency.token_usage
model.power_for_price
model_performance.token_generation_speed     (partly ops.latency_ttft)
model_performance.task_completion_and_efficiency
codex_subscription value
...
51 of 552 proposals  (9.2%)
```

**None of the three was looking for this.** The first was explaining why a
different signal failed. The second was a yield measurement. The third was a
control for prompt anchoring. That is what makes it three arrivals rather than
one finding cited three times.

## 2 · What the key would be, and I am not naming it

The shape is clear and the name is not mine to pick. What the evidence supports:

```
what it measures    tokens spent to complete a task, and whether the capability
                    obtained is worth the price paid for it
what it is NOT      ops.latency_ttft. Speed and spend come apart: a fast model
                    that emits four times the tokens is worse on this and better
                    on that, and the corpus distinguishes them
failure mode        LOUD or SILENT? This is the question I would want settled
                    first, and it decides more than the name
```

**On failure mode, and it is genuinely hard.** Token spend is *visible on the
invoice*, which argues loud. But **whether you are being overcharged for the
capability you got is not visible at all** — you would have to run the other model
on the same task to know, and almost nobody does. So a report saying "2x the cost
and worse at instruction following" is the rare case where somebody did the
comparison, and its absence proves nothing. That is the definition of a silent
failure mode, and `harvest.yaml` already says of the four silent capabilities that
*"nobody complained" is not evidence, because you would not find out*.

If it is silent, the positive-retrieval problem applies: the queries would need
positive stances to reach consensus at all, and those already measure 0.00–0.07%
on GitHub.

## 3 · Why this is worth deciding now rather than after the wire-up

**`capability_candidate` has no rows and would not have had this one.** The
twelve-key classification proposed zero new keys — anchored by the list, as the
control showed — so a table wired to that pass would have accumulated nothing. The
evidence for this key came from a prompt that had the list *removed*, which is not
the pass anybody would run in production.

So the accumulation argument for the table is sound and this candidate did not
arrive through it. Both things are true, and the second is the reason to look at
this now.

## 4 · The counter-argument, which I think is the strongest one against

**51 of 552 is 9.2% of proposals and a much smaller share of documents.** Of 774
classified, the cluster is ~51 documents — under 7%. A twelfth of the corpus is
not obviously a capability the board should carry, and the twelve existing keys
were chosen against a fuller picture than one platform's afternoon.

**And the withheld run's own output undercuts it.** 528 distinct names from 552
proposals means the classifier was naming documents, not categories. A cluster
picked out of that by my keyword grouping is a cluster I chose the boundaries of —
and I grouped `model.power_for_price` with `efficiency.token_usage` on a judgement
nobody has checked.

**What would settle it:** the three arrivals are the strongest part, because they
are independent of my grouping. Arrivals 1 and 2 named token spend without any
clustering by me at all.

## 5 · What I am asking for

Not a key. A ruling on whether this is one candidate or three coincidences, and if
it is a candidate, **whether its failure mode is loud or silent** — because that
decides whether the query set needs positive stances for it, and that is a
`contract/queries.yaml` question rather than a `capabilities.yaml` one.

`docs/proposals/for-engineer-2-capability-candidate.md` still stands as the place
a proposal would live. This one is in a document because the table is not built,
and it should not wait for the table to be worth reading.
