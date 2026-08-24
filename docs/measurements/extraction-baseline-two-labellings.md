# Both labellers were moved by presentation, in the same direction, away from the citation

**The same quote, judged twice by the same two people, got `first-hand` in the
section that showed the comment it came from and `relayed` in the section that
showed the bare fragment. From both of them. And the section carrying the
explicit citation — the strongest signal of relaying anywhere in the set — is the
one that got `first-hand`.**

That is worth more than any coefficient in the file. Framing beat evidence,
twice, in the same direction, and the cause is that I built one section without
source text.

Raw agreement 8/14 = 57.1%, Cohen's kappa 0.421. Six disagreements, four distinct
judgements, **none of them about what the text says**.

*Engineer 1 · 2026-08-21 · neither labelling treated as an answer key; no
extractor output read while comparing. Round 1 files:
`pool--labelled-by-anooj1.jsonl`, `pool--labelled-by-yathu.jsonl`. Run in
`extraction-baseline-two-labellings.txt`.*

---

## 1 · The framing result

| *"gives 10%+ better results on SWE-Bench"* | section C | section A |
|---|---|---|
| **anooj1** | `first-hand-observation` | `relayed-vendor-claim` |
| **yathu** | `first-hand-observation` | `relayed-vendor-claim` |

What each section showed:

```
C[3]   quote + the comment it came from:
       "Fable 5 on med is cheaper than Opus 4.8 on xhigh and gives 10%+ better
        results on SWE-Bench (p 255 of the model card pdf)."
       source_document_text = 163 chars

A[13]  the quote alone.
       source_document_text = ""
```

**Section A carried no source text on any row** — `doc_text = 0` on all four,
against 1739, 1739, 1739 and 163 in section C.

The direction is the part that matters. *"(p 255 of the model card pdf)"* is an
explicit citation sitting inside the C text — the clearest possible marker that
the number is being relayed — and C is the section both labellers called
`first-hand`. Strip the surrounding sentence and both called it `relayed`.

So this is not "more context, better label". A human voice around a number reads
as a person reporting; a bare fragment reads as a benchmark string; and the
citation inside the voice did not override the framing. **The instrument moved
with presentation rather than with evidence, and it moved the same way twice.**

Two consequences:

- **Pooling A and C into one kappa was wrong.** Those eight rows are five
  distinct judgements, three asked twice with different evidence.
- **Section A is dropped rather than repaired.** Deduplicated, its only unique
  row is `"exceptional performance in software engineering"` — the one with
  nothing to read it against.

---

## 2 · Agreement, split by unit, and why the coefficients are near-useless here

| | n | raw agreement | kappa |
|---|---:|---:|---:|
| all rows | 14 | 8/14 = **57.1%** | **0.421** |
| **claim rows** (A + C) | 8 | 3/8 = **37.5%** | **0.149** |
| **document rows** (B) | 6 | 5/6 = **83.3%** | **0.739** |
| distinct claim quotes (C preferred) | 5 | 2/5 = **40.0%** | **0.211** |

At n=6 with four categories one row moves kappa by roughly 0.15–0.2; at n=5 it
moves it more. And the marginals are badly skewed, which is what inflates the
chance correction:

```
anooj1   relayed 8   first-hand 3   nothing 3   over-read 0
yathu    first-hand 6   relayed 3   nothing 3   over-read 2
```

anooj1 called eight of fourteen rows relayed; yathu three. Every off-diagonal
cell but one sits in anooj1's `relayed` row, scattering across all four of
yathu's categories.

**The one durable reading:** document rows agree at 83.3% against claim rows at
37.5%. *Does this document contain a claim* is a question these two answer the
same way. *What is this extracted claim* is not.

---

## 3 · Every disagreement, and all four are taxonomy

Six rows, four distinct judgements — rows 0/10 and 2/11 are the same quote in C
and A.

**D1 · `relayed` vs `over-read`** — rows 0, 10.
*"So when Fable's classifiers detect a request related to cybersecurity … the
response is handled by Claude Opus 4.8, our next-most-capable model."*
Both agree it is not a first-hand report; they differ on which wrongness to
record. **The options are not mutually exclusive and nothing orders them.** This
sentence is both vendor copy and attached to a capability it does not assert.

**D2 · `relayed` vs `nothing-here`** — row 1.
*"more than 95% of sessions involve no fallback at all, and performance
everywhere else is unaffected."*
`nothing-here`'s help said **"SECTION B ONLY"** and the tool offered it on every
row. Both readings of the text are identical — a vendor statistic that is not a
capability report. The option set made them record it differently.

**D3 · `relayed` vs `first-hand`** — rows 2, 11.
*"We'll keep refining the safeguards to reduce false positives."*
`first-hand-observation` is defined as *"the writer is reporting something they
observed themselves"*, and **the writer is Anthropic**. For a vendor-authored
root, first-hand is literally true and means the opposite of the category's
purpose. The option never says *whose*. And there is a third reading neither
could record: this is a forward-looking commitment, not an observation of
anything.

**D4 · `nothing-here` vs `first-hand`** — row 9.
`reddit:t1_oqoehi3` — *"It already costs 2x Opus 4.8(says claude.ai app) and will
be cancelled post June 22?"*
Both agree what the sentence says. They differ on whether cost is in scope.
**Decided:** cost is out of scope — the board holds claims about what a model
does, not what it charges; price is a fact in `model_version`, not a report in
`claim`. So this is `nothing-here`, and the ruling is now in the option help
rather than left to be inferred.

---

## 4 · Which of these should be re-labelled rather than counted

**Five of the six rows — D1, D2 and D3 — should be re-labelled and not counted.**

They are quotes from a root post written by **`ClaudeOfficial`**, announcing
their own model. Every one of them turns on that. `relayed-vendor-claim` is
largely a judgement about *who wrote a sentence*, and **no row in round 1
supplied the author.**

A label made without the input the category depends on is not evidence about the
reader. It is evidence about the pool. And the "whose first hand" rewording does
not help if the answer is not in the row — that is why the author fix and the
wording proposal have to land together.

So round 1's usable yield is:

- **document rows**: 5 of 6 agree, and the sixth is D4, which was answerable with
  what the row gave and is now ruled;
- **claim rows**: not evidence about the labellers at all. Three of the four
  distinct judgements were unanswerable as posed.

**Round 1's claim-row kappa of 0.149 should not be carried forward, and round 2
is not a before/after on the labellers.** It is a before/after on the pool.

---

## 5 · The six fixes: five taken, one proposed

Built by `scripts/extraction_reading_pool.py` into
`fixtures/golden/extraction-reading-round2--unlabelled.jsonl` — **10 rows, 4
claim, 6 document, every row with an author, all `label: null`.**

| | fix | status |
|---|---|---|
| 1 | section A dropped | taken |
| 2 | author on every row — `author_external_id`, `author_role` | taken |
| 3 | `allowed_labels` per row, so a tool cannot offer an unsupported option | taken |
| 4 | cost out of scope, recorded in `nothing-here`'s help | taken |
| 5 | `over-read` precedence stated, plus `also_over_read` | taken |
| 6 | the first-hand wording | **proposed** |

### On `nothing-here`'s scope — it should not be enforced, and a claim row genuinely can be `nothing-here`

Adding the fourth option to the tool without carrying its scope is how it reached
every row; carrying `allowed_labels` in the data fixes the mechanism. But the
answer to *what the scope should be* is that there should not be one.

For a claim row, "this sentence contains no claim" already has a home:
`over-read` — the quote does not support the claim attached to it. That is why
scoping it to section B looked right.

**The D4 ruling creates a case that neither covers.** A quote can be a perfectly
correct reading of a sentence the board simply does not hold claims about. *"It
already costs 2x Opus 4.8"* read as a cost claim is not an over-read — the
reading is right — and it is neither relayed nor first-hand in any useful sense,
because both of those would admit it as evidence. It is out of scope, and that is
a claim-row verdict.

So `nothing-here` is available on both units, and its help now carries the
ruling. **I cannot fix the tool** — it is not in this repository — so the scope
travels in `allowed_labels` and the tool's job is to render what the row permits
rather than a list of its own. That is the same fix that worked for the entity
pool's `question` field.

### Proposed, not taken: the wording

D3 cannot be fixed by rewording one option, because the set collapses **two
independent questions** into one choice — the same defect as
`ResolutionReport.ambiguous` holding *"owned by nobody"* and *"owned by several"*
under one name. Proposed instead, as two questions of 3 and 4:

**Who is speaking?**

| option | means |
|---|---|
| `own-experience` | the writer is reporting what happened when **they** used the model |
| `vendor-about-own-product` | the writer is the vendor, or speaking for it, describing their own model. **New** — what round 1 had no name for, and what `first-hand-observation` wrongly admitted |
| `relayed-from-elsewhere` | repeating a claim somebody else made — a benchmark, a model card, another post. **Renamed**, because a commenter relaying a number is not a vendor |

**Is the claim sound?**

| option | means |
|---|---|
| `supported` | the quote asserts what the claim says it asserts |
| `over-read` | the quote does not support the claim attached to it |
| `not-an-observation` | states an intention, a plan or a commitment rather than something observed. **New** — *"We'll keep refining the safeguards"* is this, and nothing covers it |
| `out-of-scope` | a correct reading of a sentence about price, availability or plan limits |

This fixes three of the four disagreements structurally rather than by wording:
D1 stops being a choice, D3 gets a name, D4 gets a slot. **And it costs what more
categories always cost at small n** — kappa falls before it rises, so a round
using it is not comparable to 0.421 and must not be reported as if it were.

Both option sets are in the pool's `_meta`: the four in use under
`label_options`, the proposal under `proposed_options_not_in_use`.

---

## 6 · Where more documents come from

10 rows is too few, and the answer is more documents rather than better ones.
Measured on this machine:

| source | documents | readable text | `author_id` set |
|---|---:|---:|---:|
| blog | 31 | **30** | **30** |
| reddit | 6 | 0 (payload) | 0 (payload) |
| github | 27 | **0** | 0 |

**The growth is the blog corpus** — the 30 readable `whole_document` thread
contexts, which is the pre-registered unrun extraction. One byline, and
`blog-extraction-pre-registration.md` already predicts it publishes nothing and
says why. Publication is not what this set measures: **Simon Willison relaying a
vendor announcement is exactly the relayed/first-hand case**, so a corpus of one
author writing about other people's models is a better source for this taxonomy
than a second Reddit thread would be. And 30 of 30 carry an author, which is the
input round 1 lacked.

GitHub's 27 are the better source in principle — the failure channel, the most
likely place a first-hand observation appears — and have **no readable text
locally**. That is the store/DB mismatch, not a gap in the corpus.

### One premise correction

The author does **not** come from `document.author_id` for Reddit. Measured: that
column is set on 30 of 31 blog rows and **0 of 6 reddit rows** — only
`collect/adapters/blog/write.py` writes it, and there is no Reddit document
writer. The handles are in the stored API payload, so the pool carries them from
there; the column cannot supply them yet. `author` holds exactly one row,
`blog:simonwillison.net`.

---

## Housekeeping

`pool--labelled-by-anooj1.jsonl` carries `labelled_by: "anon"` in its `_meta` and
on all 14 rows — third export running with the tool's labeller name unset. The
filename says `anooj1`. Not corrected in the artifact, because that has not held
twice; the name needs setting in the tool.
