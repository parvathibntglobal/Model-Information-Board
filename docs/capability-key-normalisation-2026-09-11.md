# The review queue's real problem is normalisation, and here are the numbers

*2026-09-11 · measured off `docs/measurements/model-only-classification-withheld.jsonl`,
the withheld-keys discovery run of 2026-08-28 (774 Reddit documents,
`google/gemini-2.5-flash`, $0.4407). Nothing here is a claim about any model.*

`judge/store/capability_candidates.py` already says the right thing —
*"free-text keys fragment one capability across phrasings — so any figure shown
from it reads `>= N` until clustering lands."* This document is that sentence
with a denominator attached, because the gap between "a known risk" and "a
known risk at this size" is the gap between deferring clustering and budgeting
for it.

**It does not bear on the signal demotion** (`docs/measurements/signal-as-weight-2026-09-11.md`).
That decision rests on `is_capability_report`, a boolean, and the boolean is
sound whatever the keys look like. The load-bearing claim there is *a described
behaviour is present in this document*. What follows is about what happens
after you believe that.

---

## 1 · The size of it

```
documents in the withheld run                      774
documents carrying a proposed key                  552
DISTINCT proposed keys                             528
proposals per distinct key                       1.045
keys proposed more than once                        20   of 528
```

**528 keys from 552 proposals.** Against `contract/capabilities.yaml`, which
declares **12**.

On the 254-document subset that matters most — the posts the old signal gate
refused and the discovery pass accepted — it is **251 distinct keys across 254
posts**. Essentially one new label per document.

This is not a taxonomy. It is 528 hapax legomena with dots in them.

## 2 · Three separate defects, and they need different fixes

**(a) Fragmentation across phrasings.** 42 final segments are used by more than
one distinct key, covering **113 of 552 proposals (20.5%)**:

```
   8x  ...performance          5x  ...instruction_following
   5x  ...speed                5x  ...coding_performance
   5x  ...accuracy             4x  ...degradation
   4x  ...token_efficiency     4x  ...efficiency
```

`model_behavior.instruction_following`, `model_understanding.instruction_following`
and `claude_haiku.instruction_following` are one capability wearing three
prefixes. A review queue that lists them as three rows asks a person to make
the same ruling three times, and a COUNT over them reports one capability as
three pieces of evidence — which is the `n_eff` double-counting shape one table
over.

**(b) The namespace is invented per document.** 155 distinct top-level
namespaces. `model_behavior` (160), `model_performance` (43) and `model` (43)
are the same intent three times; the long tail is one-offs like `fable5`,
`colibri`, `audeta`, `animation`.

**(c) 85 of 552 keys (15.4%) name a MODEL in the key.** `claude_haiku.instruction_following`,
`gpt_5_2.response_time`, `model_behavior.opus_4_6_capabilities`,
`claude.sonnet_haiku.prompt_behavior.md_spam_fix`.

**(c) is the one that is not a clustering problem.** A capability is a
dimension models are compared ON; a key that names a model has folded the
subject into the axis. Cluster those together and you get a capability called
"Claude", which is worse than 85 scattered rows because it looks finished.
They need rejecting at proposal time or rewriting at review, not merging.

## 3 · What this means for whoever builds the queue

- **The row count is not the candidate count.** 528 rows, upper-bounded by
  maybe a few dozen real capabilities. Sizing the review UI off the row count
  sizes it for the wrong job — the work is merging, not ruling.
- **Rule 3 applies to the queue's own figures.** "528 candidates" is a
  *counted* number and publishable as such; "528 discovered capabilities" is
  the same number answering a question it was not asked (rule 7). The existing
  `>= N` convention in `capability_candidates.py` is the right one — keep it,
  and say what the N counts.
- **Dedup by content hash does not help here.** `candidate_id` already hashes
  `(document, proposed_key, prompt_label, pipeline_version)`, which makes
  re-runs idempotent and does nothing about two documents proposing the same
  capability under different spellings. Those are different natural keys by
  construction. Idempotency and normalisation are separate problems and the
  first is solved.
- **The cheap first cut is mechanical and needs no model.** Strip a leading
  namespace, strip an embedded model alias using `model_alias`, lowercase,
  and cluster on the final one or two segments. That collapses the 20.5% with
  shared tails and flags the 15.4% carrying a model name for a human. Rule 2
  permits it precisely because it is code: an LLM may propose a key, it may
  never decide that two keys are the same one.

## 3b · Clustered. It does not collapse.

*Added 2026-09-11. `scripts/cluster_capability_keys.py`, code only — rule 2: a
model may propose a key, it may never decide that two keys are the same one.
**Nothing was merged.** Five rules are reported because the answer depends on
the rule, and one number would hide that.*

| rule | clusters | singletons | largest |
|---|---|---|---|
| 0 · exact key (baseline) | 528 | 528 (100%) | 1 |
| 1 · lowercase + strip model/vendor/version | **528** | 528 (100%) | 1 |
| 2 · + cluster on the final segment | 486 | 457 (94%) | 5 |
| 3 · + cluster on the last two segments | 514 | 503 (98%) | 3 |
| 4 · token Jaccard ≥ 0.5 | 394 | 361 (92%) | 60 |
| 4 · token Jaccard ≥ 0.34 | 329 | 290 (88%) | 122 |

**528 becomes 330 to 515. It does not become 30.**

**Rule 1 collapses NOTHING — 528 to 528.** Stripping every model, vendor and
version token merges not one pair. That is the most informative row in the
table and it corrects the cheap reading of §2: the keys are not one taxonomy
wearing different prefixes, they are distinct in their substance. The 15.4%
naming a model are a *correctness* problem, not a *duplication* one.

**And both large clusters are single-link chaining, not capabilities.** The
60-key and 122-key clusters share **zero tokens across their members** — they
chain through `code` → `coding` → `efficiency` → `quality`. Excluding the
chain, threshold 0.34 gives 328 clusters with 290 singletons. Read the
aggressive rows as an artifact with a real region inside them: there is a
large coding/code-generation neighbourhood, and it is a neighbourhood a person
would have to carve, not a cluster an algorithm found.

### The curve is the finding, not the count

Rarefaction over the 552 proposals, mean of 40 shuffles:

```
  proposals     50   100   150   200   250   300   350   400   450   500   552
  distinct    49.8  99.2 148.3 197.0 244.8 293.0 340.0 387.0 433.6 480.4 528.0
  new per 50  ----  49.4  49.1  48.7  47.8  48.2  47.0  47.0  46.5  46.8  45.8
```

**0.99 new keys per proposal at the start; 0.92 at the end.** Over an eleven-fold
increase in sample it barely bends. **The key set is not converging on a
taxonomy — it grows roughly 1:1 with documents**, at a measured **0.682
distinct keys per document**.

That is what settles "30 or 300". Neither: it is unbounded at this prompt.
A number quoted as "the capabilities discovered" would be a statement about
how many documents were processed.

## 3c · What the review queue looks like

At 0.682 keys/document, and with the sieve demotion having raised intake
×24.3 on Reddit and ×27.25 on GitHub (measured, `signal-as-weight-2026-09-11.md`):

| corpus | documents | ≈ distinct keys |
|---|---|---|
| the 774 already classified | 774 | 528 |
| one re-sieve of github + blog at the new rate | 230 | ~157 |
| **30 nights of the Reddit listing sweep at the new rate** | 2,190 | **~1,494** |

At **45 seconds a ruling** — read the key, its definition and the quote, then
decide adopt / map-to-existing / reject:

```
   330 decisions    4.1 h    0.6 working days
   528 decisions    6.6 h    0.9 working days
 1,494 decisions   18.7 h    2.7 working days       <- one month of Reddit alone
```

**A human can work through 528 once. A human cannot work through it monthly,
and that is the shape of the problem.** The one-off backlog is a day. The
*recurring* queue grows linearly with the corpus and the corpus just grew
25-fold, so the queue is a ~2.7-day-per-month standing cost that nobody has
budgeted, rising with every platform added.

Three things follow, and none of them is "cluster harder":

- **The 45 s estimate is mine and unmeasured.** No ruling has been timed. It
  is the one figure here with no denominator behind it, and the honest range
  is probably 20 s to 2 min depending on how long the quote is. Time ten
  rulings before trusting any of the totals above.
- **Clustering buys 38% at best** (528 → 329) and brings a chained blob with
  it. It is worth doing and it does not solve this.
- **The lever is the prompt, not the queue.** The behaviour-only constraint
  (blocker 1) addresses correctness, not volume. What would address volume is
  asking the model to choose from the twelve and propose *only* when none fit
  — which the non-withheld run already did, returning zero proposals from 255
  reports. Between those two extremes there is a prompt nobody has written,
  and finding it is cheaper than reviewing 1,494 keys a month.

## 4 · What is NOT established here

- **That 528 is the steady-state rate.** One run, one prompt label, one
  proposer model, 774 Reddit documents. A different prompt that showed the
  twelve keys produced far fewer proposals; that is what the non-withheld run
  is for, and the two are not comparable on this axis by design.
- **That any of the 528 is a real capability.** This document counts labels.
  Whether the board needs a thirteenth capability is a ruling against
  `contract/capabilities.yaml`, which is a PR with two eyes on it, and nothing
  here proposes one.
- **How many real capabilities the 528 collapse to.** Nobody has clustered
  them. That is the measurement this document exists to justify funding, and
  quoting a guess for it would be the same error it is warning about.
