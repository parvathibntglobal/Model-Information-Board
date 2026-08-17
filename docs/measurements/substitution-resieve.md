# Substitution, re-sieved against the new term shape

**168 queries · 1,297 distinct Reddit documents · four term shapes · substitution
now yields. The topic change supplies the yield; the subject change supplies the
attribution.**

**0 → 2 documents on version-only surfaces, 1 → 4 with surfaces as declared.**
Finding 4 is no longer a measured zero — and it is small enough that the next
section is about what would still overturn it.

*Engineer 1 · Reddit, RapidAPI · 2026-08-17 · 168 requests, quota 999,028 → 998,860*

> This is the measurement Engineer 2 asked for before either of us calls finding
> 4 closed. Her change made substitution **retrievable**; whether it *yields*
> anything was nobody's measurement yet.

---

## 0 · It is not the same corpus, and that has to be said first

The 2026-08-17 run's 1,678 documents are **gone**. Its script was never
committed and its corpus lived in a scratch database that has since been reset,
so "re-sieve the corpus" was not possible as asked: re-sieving is only free when
the text is local, and it wasn't.

So this is a **re-retrieve and sieve**, and the two runs' numbers are not paired.
`scripts/substitution_slice.py` is committed this time, in two stages, so the
next shape change costs zero requests.

Two other differences from the prior run, both in the direction of a smaller
corpus: `deepseek/deepseek-r1` and `deepseek/deepseek-v3` retired on 2026-07-24,
so 8 seed models are live rather than 10.

## 1 · The control, and what it caught

The prior run stated its control first, for the reason that still holds: a zero
from a harness nobody has shown can produce a one is indistinguishable from a
broken harness. Same synthetic document, through all four shapes:

> "We replaced claude opus 5 with claude haiku 4.5 for our ticket summariser
> back in March. Six months on there has been no regression that anyone has
> noticed, and it is still running in production."

| shape | verdict | why |
|---|---|---|
| OLD | **passes only as (haiku, opus)** | topic renders `replaced claude opus 5`; reverse the roles and it renders `replaced claude haiku 4.5`, which the sentence does not contain |
| NEW | passes either way | both aliases sit in an all-of `subject`; topic carries no placeholder |
| SUBJECT-only | fails | the adjacency phrase still has to match |
| TOPIC-only | passes | `replaced` alone, with one model named |

**The control caught a defect in my own harness.** The first version tested one
ordering per pair, which would have measured the old shape at half its reach and
made her change look better for a reason that was mine. `orderings_for` now
decides by rendering with two sentinels and comparing: a symmetric shape is not
double-counted and a directional one is not halved.

That difference is itself a result. Under the old shape the pair is **ordered** —
90 ordered pairs, as `queries.yaml` says. Under the new shape (a, b) and (b, a)
render the same requirement, so the collapse to 45 that the file called a
rendering decision is now arithmetic.

## 2 · The 2×2, because two things changed at once

Reporting the net would say nothing about which half moved it. Every document is
sieved under four shapes: OLD, NEW, and each change on its own.

Surfaces as declared in `contract/seed_models.yaml`:

| shape | subject | topic | signal | independence predicts | **documents** | (entry, document) pairs |
|---|---|---|---|---|---|---|
| OLD | 78.6% | 3.6% | 2.5% | 1.60 | **1** | 1 |
| TOPIC-only — looser topic, old subject | 78.6% | **34.0%** | 2.5% | 62.75 | **5** | **67** |
| SUBJECT-only — stricter subject, old topic | 35.2% | 3.6% | 2.5% | 0.24 | **1** | 1 |
| NEW — both | 35.2% | **34.0%** | 2.5% | 4.37 | **4** | **7** |

The same four shapes with family surfaces dropped (§4 is about why this table
exists at all):

| shape | subject | topic | signal | independence predicts | **documents** | (entry, document) pairs |
|---|---|---|---|---|---|---|
| OLD | 67.1% | 3.2% | 2.5% | 1.16 | **0** | 0 |
| TOPIC-only | 67.1% | **34.0%** | 2.5% | 46.33 | **5** | **44** |
| SUBJECT-only | 25.5% | 3.2% | 2.5% | 0.15 | **0** | 0 |
| NEW | 25.5% | **34.0%** | 2.5% | 2.93 | **2** | **4** |

**The old shape is a measured zero on version-only surfaces**, which is the prior
run's headline reproduced on a different corpus. The new shape is 2.

Each group is counted **independently** over all 1,297 documents. The
2026-08-14 run reported "77% topic" by counting topic only among documents where
subject also matched, which is bounded by the subject rate and cannot measure
topic at all; here topic and signal are read with a subject-free term set.

### The retrieval side says the same thing before the sieve runs

Three query families were issued and the corpus is their union, so neither shape
is measured on the other's corpus:

| family | queries | posts returned | queries returning nothing |
|---|---|---|---|
| `pair` — both aliases, no verb | 30 | 700 | 2 |
| `pair+verb` | 90 | 2,150 | 4 |
| `phrase` — the **retired** directional phrases | 48 | **26** | **43** |

48 queries built the way the old shape asked for them returned 26 posts between
them, and 43 of the 48 returned nothing at all. The old shape's problem starts
at retrieval and the sieve never gets a chance to be the constraint.

Because the corpus is the union, the old shape is sieved over documents its own
queries would never have found. That bias runs in its favour, which is the safe
direction for a comparison that concludes against it.

## 3 · Which half moved it — the topic change, and not by a little

**Topic supplies the yield.** Holding subject at its old shape, replacing six
directional phrases with bare verbs takes topic from 3.6% to 34.0% and documents
from 1 to 5. Holding subject at its new shape, the same change gives 1 → 4. The
adjacency phrases were the constraint, exactly as the 0% containment finding
said.

**Subject supplies the attribution.** It costs one document (5 → 4) and removes
**60 of 67 (entry, document) pairs** — the same handful of documents, attributed
to six times fewer model pairs. On version-only surfaces the same split is
44 → 4, so **40 of 44 attributions go** and 2 of 5 documents stay.

Under TOPIC-only, `t3_1uh8cmg` is filed against `claude-haiku-4-5|claude-opus-5`,
`claude-haiku-4-5|gemini-2.5-pro`, `claude-haiku-4-5|claude-sonnet-5` and
`claude-sonnet-5|gemini-2.5-flash`; at most one of those can be what the post is
about, and one of them pairs a model with a second model the post never names.
Requiring both models named is what removes the rest.

So the two halves do different jobs, and the one that looks restrictive is the
one that makes the yield worth having. Her framing — *the conjunction does the
narrowing the adjacency was only pretending to do* — is what the numbers show,
with the addition that the narrowing is measured in wrong attributions removed
rather than in documents lost.

**Independence overpredicts badly here**: 62.75 against 5 for TOPIC-only. The
three groups are not independent — signal concentrates in a few documents that
also carry topic — so the prediction is an upper bound and the ratio between
prediction and measurement is not a finding about substitution.

## 4 · Three of the four passes rest on a bare family word

`contract/seed_models.yaml` declares `sonnet`, `haiku`, `opus` and
`claude sonnet` as variants. They resolve at **family** specificity, which never
counts as independent corroboration — and they were harmless while `subject` held
one alias. With two, a post that says "sonnet" and "haiku" satisfies an all-of
subject for (claude-sonnet-5, claude-haiku-4-5), and the conjunction narrows far
less than it appears to.

Re-checked with family surfaces dropped — `classify_specificity` decides which,
not this measurement:

| | surfaces as declared | version-only surfaces |
|---|---|---|
| posts naming any model | 1,019 / 1,297 | 870 / 1,297 |
| (pair, post) naming both | 691 | **463** |
| NEW: subject rate | 35.2% | **25.5%** |
| **NEW: documents passing** | **4** | **2** |

**Half the new shape's yield is a family word.** Of the four passes with surfaces
as declared, two survive on version surfaces; the other two are carried by
`sonnet` or `claude sonnet` standing in for `claude-sonnet-5` — a post that names
a line satisfying half a requirement to name two tiers.

This is a finding about the **seed file**, not about her change: with `{alias_b}`
in an all-of group, a family-specificity variant in the alias list becomes a way
to satisfy half a subject requirement without naming a tier. #33's ruling already
keeps family surfaces out of what the proposer offers; the eleven hand-written
lists predate it and still carry them. **The conjunction is only as strong as the
weakest surface in either list**, which is an argument for pruning family
variants from `subject` rather than an argument against requiring both models.

## 5 · What the 340-model registry could and could not test

The prediction was that the subject constraint is materially different now the
registry holds 340 models rather than 11. **Registry size alone cannot reach
retrieval**: a polled model carries no reviewed alias surfaces, and
`openrouter.alias_coverage` reports exactly that gap. Only the 11 seeded models
have surfaces a query can be built from.

What the surface extract supplies instead is *measured* spellings for the 72
models the corpus discusses, so this run pairs those too — `opus 5` at 1,445
mentions where the seed file nominates `claude opus 5` at 0.

**Every version-only pass comes from that half of the pair set.** All four
surviving (entry, document) attributions are between `claude-opus-4.6`,
`claude-sonnet-4.5` and `gpt-5` — polled models with attested surfaces and no
seed entry. The eight hand-curated live models contribute **zero** version-only
passes.

So the prediction is confirmed in a narrower and more useful form than it was
made: the registry going 11 → 340 does move the subject constraint, but **through
the alias surfaces rather than through the model count**. That is the #33
proposal's job, and it is the second independent confirmation that the
hand-written surface lists are the weaker input.

## 6 · Signal is still what binds

| group | rate | change |
|---|---|---|
| subject | 78.6% → 35.2% | stricter by design |
| topic | 3.6% → **34.0%** | the change that moved yield |
| signal | **2.5%** | untouched, and now the floor |

32 documents of 1,297 carry a substitution signal phrase in the author's own
prose. The prior run's funnel put it at 0 of 69; this run has it at 32 of 1,297
with 4 documents clearing all three groups. Signal is where the next measurement
should go, and it is a vocabulary question rather than a retrieval one —
`docs/measurements/per-term-vocabulary-counts.md` already shows
`substitution:positive` with 3 live signal terms of 9 and `substitution:negative`
with 0 of 6.

**2 or 4 documents of 1,297 is a thin result and is not being dressed up as more.**
What it establishes is that the pipeline can produce a substitution document at
all, which is the thing no measurement had shown. A rate this low cannot support a
claim about how often engineers report migrations.

**Nothing here has a negative-stance pass.** Every passing document is
`positive`. A revert is rarer and worth more per instance than anything else in
the corpus, and this run does not contain one.

## 7 · What the sieve cannot decide, and correctly does not

`t3_1tsan0m` is a genuine migration report — a companion app moved from Sonnet
4.5 to Sonnet 4.6 when 4.5 was discontinued — and the pair it was filed against
is `(opus 4.6, sonnet 4.5)`, which is wrong in detail: Opus 4.6 is a different
model mentioned in the same post. Both names are present, the document is worth
extracting, and **which model moved to which is not something retrieval can
decide**. That is `direction: decided_at_extraction` doing its job rather than
failing at it.

## 8 · What would revise this

- **A signal vocabulary that reaches how people write about migrations.** 2.5% is the binding constraint and nothing in this run addresses it.
- **The family surfaces in `contract/seed_models.yaml`.** Three of four passes depend on them; #33's ruling points the other way.
- **A negative-stance instance.** Zero here, and a revert is the highest-value document in the corpus.
- **More than one page per query.** `max_pages=1`, so 1,297 documents is page 1 of 168 queries and the ceiling was never probed.
- **The same shapes on GitHub and blogs.** All 1,297 documents are Reddit, and `docs/measurements/alias-surfaces.md` §6.1 argues the naming shape differs per platform.
