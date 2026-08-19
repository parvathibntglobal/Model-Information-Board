# The first extraction run — written before it happens

**Status: pre-registered, not yet run.** Everything below is committed in
advance so nothing in it can be an explanation constructed after the data
arrives.

*Engineer 2 · 2026-08-19 · agreed with Engineer 1 before the run*

This is the same discipline that stopped the Tier 2 sweep result from being
explained afterwards: the prediction is written down first, and then the
measurement either matches it or does not.

---

## 0 · Why this document exists at all

Two things would otherwise be read wrongly, and both would cost somebody a
morning of looking in the wrong place.

The first is the word **`insufficient`**, which every cell this run produces
will carry, for a reason that has nothing to do with the work most recently
done on it. The second is **who owns a failure**, which is cheap to assign now
and expensive to argue about once there is data to argue from.

---

## 1 · What is being measured

**Token counts, and nothing else.** The extractor has never met a real model,
so the run's purpose is to replace an estimate with a fact.

| | current value | how it was arrived at |
|---|---|---|
| `ESTIMATED_INPUT_TOKENS` | **1300** | 569 system prompt + 663 for a real thread, **measured in characters** and divided by an assumed 4 chars/token that is not known to be this tokenizer's |
| `ESTIMATED_OUTPUT_TOKENS` | **800** | **a guess.** Nothing has ever produced an output to count |
| cost per call at those figures | **$0.00239** | $0.30/M in, $2.50/M out — Gemini 2.5 Flash, `contract/seed_models.yaml`, sourced to Google's pricing page |
| what `$1.00` therefore allows | **~418 calls** | derived from the above, so it moves when they do |

The output half is the weakest input in the budget by a wide margin, and it is
the one number in the system that has never been anything but arithmetic on a
guess.

**Input:** two threads from `_handoff/` — one Reddit (3,322 flattened chars),
one blog (1,607). Both verified through the real types: 11 spans resolved, 0
failures.

**Expected spend: about $0.005.** The $1.00 cap will not bind and is not being
tested here.

---

## 2 · `insufficient` will mean voices, not platforms

Every cell this run produces will read `insufficient`. **That is correct
output.** The publication gate requires:

```
n_eff >= 3.0            roughly four independent voices
distinct_platforms >= 2
conditional author cap
```

Two threads cannot reach `n_eff >= 3.0`. That is arithmetic about a two-thread
corpus, not a finding about anything.

**The distinction that has to be in writing:** one Reddit thread plus one blog
article *can* reach `platform_count = 2`, and the cell will still be
insufficient on voices. So `insufficient` here has two possible reasons and
only one of them was ever a defect:

| reason | state |
|---|---|
| `platform_count < 2` | **fixed.** E1's blog path landed; both platforms now write documents |
| `n_eff < 3.0` | **arithmetic.** Two threads, and no amount of correctness changes it |

Without this stated in advance, the first `insufficient` reads as the platform
work not having landed, and somebody goes and checks work that is finished.

---

## 3 · Where to look if it goes badly — assigned before the data

Committed by both engineers in advance. The point is that neither of us starts
from the other's artefact.

| symptom | owner | why |
|---|---|---|
| **Reddit fails, blog passes** | **E2 — `judge/extract/prompt.py`, then the schema** | The threads, offset maps and flattener are verified. A high rejection rate on the platform whose maps have been checked byte-for-byte is a prompt producing unverifiable quotes |
| **Blog fails, Reddit passes** | **E1 — the flattener** | `trafilatura` double-decodes entities, so E1's entity pass is disabled for blogs. If that pass was needed after all, the offsets are wrong in exactly the way that surfaces as failed verification on one platform and not the other |
| **Both fail** | **E2 — the schema, then the prompt** | A platform-independent failure is not about text |
| **Schema rejection rather than verification failure** | **E2 — `judge/extract/schema.py`** | The model returned something the forced tool call would not accept, which is a contract between the prompt and the schema and touches no data |

Reddit failing and blogs passing is a prompt. Blogs failing and Reddit passing
is a flattener. Stated this way round because the two look identical in a
summary count and diverge completely in what to do next.

---

## 4 · What this run cannot show

- **Whether the board says anything true.** No cell will publish, so nothing
  reaches a page.
- **Whether a quote renders.** The blog document in this export carries no
  `url` — withheld deliberately, and since corrected on staging. So claims from
  it can be extracted, verified and counted, and **never displayed**. That is a
  second measurement needing a fresh export, not a prerequisite for this one.
- **A zero-yield rate.** With n=2 there is no rate. It is the first observation
  of whether a real thread yields claims at all, and the skip logic's saving
  still rests on a number nobody has.
- **Whether the extraction budget binds.** $0.005 against $1.00.

---

## 5 · Where it runs

**The local disposable Postgres on port 5433**, never `DATABASE_URL` — which
points at a remote host. Same reasoning E1 gave for export-rather-than-DSN: a
shared database makes *"did the extractor write that row or the harvester"*
unanswerable from the rows, and a first run is the worst time to lose that.
