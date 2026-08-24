# Prediction, written before the sweep: seating 50 more models buys ~nothing

**Recorded 2026-08-24, before any sweep at 91 seats has run.** The point of
writing it first is that the last two sweeps were read after the fact, and a
number interpreted afterwards can support either conclusion.

*Engineer 1 · writes only this document*

---

## 0 · The two prior sweeps, with their denominators

| sweep | retrieved | reached `document` | stored claims |
|---|---|---|---|
| GitHub, 10 seeded models, 5 repos | 3,776 candidates | 25 | 0 — zero signal in author prose |
| Blogs, 9 feeds, one author dominant | 140 claims extracted | 7 | 133 resolved to no seated model |

Both are **retrieval-limited at the far end, not at the near end.** Neither ran
short of candidates. Both ran short of candidates that said something about a
model we carry.

## 1 · The prediction

> **Seating the 50 highest-mention uncurated models adds fewer than 10
> triage-surviving documents and fewer than 3 stored claims, over the whole
> corpus we already sweep.**

The basis is a count, not an intuition. Of **301 model_version rows with no
curated surface**, exactly **20 are mentioned in at least one of the 316
readable texts we hold**. So:

```
50 proposed seats
 20  have >=1 attested mention   <- of which 16 have <=2 documents
 30  have ZERO attested mentions <- seated on launch-window derivation alone
```

And the attested 20 are not evenly attested. `claude-fable-5` (45 documents)
and `qwen3.8-27b` (43) carry the mass; the third is **5 documents**, the fourth
4, then 2, 2, 1, 1, 1, … Both leaders are already retrievable — they are the
two names this corpus talks about, and no new seat changes that.

**So 48 of the 50 seats are being added for a corpus that mentions them a
combined ~25 times.** A query naming a model nobody writes about retrieves on
the alias alone, and that is the GitHub result restated.

## 2 · The sweep as asked does not fit, and this was costed ten days ago

Measured today, 26 query entries (18 daily / 8 weekly), 5-repo scope:

```
                     aliases   daily req   minutes@30/min   verdict
one model                  5          80              2.7   within
41 curated (today)       205       3,280            109.3   OVER by 2,380
41 + the 50              455       7,280            242.7   OVER by 6,380
103 seated               515       8,240            274.7   OVER by 7,340
```

`contract/harvest.yaml` sweep_budget: **daily 900 requests / 35 minutes.**

**The cap binds at 11 models**, at 80 daily requests each. Not at 103, and not
at 91 — at **11**. We are already 3.6x over at the 41 we carry.

This is not a new finding. `harvest.yaml` lines 62-99 costed it on 2026-08-14
and got 11 models -> 896 requests, headroom 4 — **81 requests per model against
the 80 measured today**, from a different scope and two fewer daily entries.
The two measurements agree, ten days apart.

It also already names why a rotation is not free: on a five-night rotation a
model's evidence is up to five nights stale and *the page cannot say so* without
a per-model last-swept timestamp. That column exists — `model_version
.last_swept_at`, `contract/tables.sql:83` — and `collect/registry/assertions.py`
already guards the phantom case where it is set and no sweep has run.

**So the cost answer is: 103 seats is a 9.2x overrun on a budget whose overrun
was already documented, and the lever is a rotation whose precondition is
already built.** Nothing here is blocked on capacity. Which is the point of the
next section.

## 3 · What would change the conclusion — stated before the numbers exist

The standing conclusion after two sweeps is: **the constraint is what engineers
write, not how many models we carry.** If a third sweep lands the same way, that
is three tests of one hypothesis and it should be settled.

It would be **wrong**, and the registry would be the real constraint, if any of
these holds:

**(a) The 133 unresolved blog claims start resolving.** This is the decisive
test and it needs **no sweep, no requests and no budget** — the claims are
already in hand. Re-resolve those 133 subject strings against a population that
includes the 50 new seats. If a material fraction resolve, then the evidence was
always there and the registry was throwing it away. *Threshold, set now: **20 or
more of 133** resolving makes the registry the constraint. Fewer than 10 settles
it the other way.*

**(b) The uncurated models attract documents at a rate comparable to the curated
ones.** Measured today: 18 of 41 curated models are mentioned in >=1 document
(43.9%); 20 of 301 uncurated are (6.6%). If the per-model mention rate for newly
seated models came out near 43.9% rather than near 6.6%, "we do not carry enough
models" would be a real diagnosis. It is 6.6%.

**(c) Triage survival on newly retrieved documents resembles the blog corpus
rather than GitHub's.** Blog comments survived triage at 8.7%; GitHub author
prose produced 0 usable claims from 3,776 candidates. If a 91-seat sweep returns
documents surviving at blog-like rates, the seats bought something.

**What would NOT change it:** more retrieved candidates. All three of these
measure what survives, because both prior sweeps had candidates in abundance and
neither had signal. A fourth sweep returning 10,000 candidates and 25 documents
is the same result a third time.

## 4 · The order this implies

**(a) first, because it is free.** It is a re-resolution over stored rows, it
costs one query and no API calls, and it distinguishes the two hypotheses
directly. Running an over-budget sweep to answer a question that a re-resolution
answers for nothing is the expensive way round.

Recorded before running it, so the threshold in (a) cannot be chosen after the
count is known.

---

# The result: 0 of 134, and the constraint is now named precisely

**Run after §3 was written and committed to a threshold.** Test (a), the free
one, needs no sweep and it settles the question.

```
surfaces in population   before 1,224   after 1,274   (+50 declared)

THE 140 BLOG CLAIMS, RE-RESOLVED
  resolve today (all 342 rows, mechanical surfaces)   6 of 140
  resolve with the 50 seats declared                  6 of 140
  NEWLY resolving                                     0        <- threshold was >=20
  still resolving to nothing                        134
```

**Zero.** The prediction was "fewer than 10"; the count is 0. Seating 50 more
models moves not one claim.

## Why — and this is the part worth more than the zero

The 140 subjects, bucketed by the reason each does or does not resolve:

| | of 140 | |
|---|---|---|
| **UNVERSIONED — names no version at all** | 96 | 68.6% |
| **a FAMILY WORD — excluded by design** | 26 | 18.6% |
| **versioned and unseated — the only bucket a registry fixes** | **12** | **8.6%** |
| resolves today | 6 | 4.3% |

The commonest unresolved subjects are `LLM` (15), `Codex` (11), `Claude` (6),
`AI` (6), `Claude Code` (5), `MiniLM` (5), `model` (4), `Gemini` (4),
`agents` (4). Those are category nouns and product names, not model versions.

**87.2% of claims name something no registry can ever seat** — 96 unversioned
plus 26 family words. A registry of 342 models, or 3,420, resolves none of them,
because there is no version in the text to resolve.

And the extractor already said so: **`specificity` is `family` on 124 of 140
claims (88.6%)**, `version` on 15, `snapshot` on 1. The label was there the whole
time; nobody had joined it to the resolution failure.

**Even the 12 do not argue for the 50 seats.** They are `GPT-3`, `GPT-4-32k`,
`Llama2`, `Mistral 7B GGUF`, `Mistral 7B-Instruct`, `Gemini Flash 2.5`,
`Gemma 26B A4B`, `Qwen-3`, `gemma-4-12b-qat` — mostly models older than the
catalogue we poll, and quantisation/format spellings. Seating 50 *newly launched*
models addresses approximately none of them.

## What is settled, and what it moves the work to

**Settled, on the third test and with a pre-registered threshold: the constraint
is what engineers write, not how many models we carry.** Three sweeps, three
populations, one answer — 3,776 GitHub candidates to 0 claims, 140 blog claims to
7 stored, and now 0 of 134 recovered by a 50-model expansion.

**Registry expansion should stop being the proposed fix.** It is not a small
improvement badly measured; it is measured at zero, twice by prediction and once
by count.

**The lever is the family-word ruling, and it is Engineer 2's.** 18.6% of claims
are excluded by a deliberate design decision, not by a gap — `FAMILY_WORDS` drops
`Claude`, `Gemini`, `Codex`, `ChatGPT`, `Deepseek`, `Mistral` by exact
membership. That is 26 claims, against 0 from 50 seats. The ruling has been made
twice on different evidence and both times without this number beside it.
It should be reopened with **26 versus 0**, which is a different argument from
the one it was refused on.

**What it does not license.** Attributing a `Claude` claim to a specific version
is inheritance, which was ruled against twice, and nothing here reverses that. A
family-level claim can only ever render on a family-level surface — which is a
schema question and a page question, and both are outside this lane.
