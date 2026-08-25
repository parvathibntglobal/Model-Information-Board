# Prediction: what the signal group does on prose, written before it is measured

**Nothing here is a result.** The prose corpus already exists — 120 blog and 196
Reddit documents — so this can be measured offline in minutes, which is exactly
why the prediction has to be written first.

*Engineer 1 · 2026-08-24*

---

## 1 · The comparison must be like-for-like, and there are three figures not one

GitHub, measured over 32,723 candidates:

| | GitHub |
|---|---|
| **vocabulary-wide** — any of 207 terms, anywhere | **16.25%** |
| **per-entry** — one entry's ~8 terms, which is what a request asks | **0.39% median** |
| **sweep-observed** — the weighted per-request group rate | **1.3%** |

**All three must be reported for prose, or the comparison will be made between a
vocabulary-wide figure on one platform and a per-entry figure on the other** —
which is the mistake that produced "1.3% versus 16.25%" as though it were a
platform difference when it was a denominator difference.

## 2 · The hypothesis under test

> **The signal vocabulary is prose-register and GitHub is issue-register, so it
> should perform substantially better on blogs and Reddit than on GitHub.**

This is the reading that motivates per-platform signal terms. It has one clean
prediction and one clean falsifier.

## 3 · The prediction, with thresholds

**I predict the vocabulary does better on prose, and by less than the register
argument implies.**

| figure | GitHub | predicted on prose |
|---|---|---|
| vocabulary-wide | 16.25% | **30-55%** |
| per-entry median | 0.39% | **1.5-4%** |
| terms that never fire | 102 of 207 | **60-85 of 207** |

**Why "better but by less".** Two reasons pulling in opposite directions:

- *Better*, because the terms were written in this register. `forgets the
  middle`, `applied cleanly`, `didn't invent` are essay constructions and this is
  the essay corpus.
- *By less than the register argument implies*, because the register argument does
  not explain the concentration. `truncat` alone is 34.2% of GitHub firings and
  `truncat` is not issue-specific — it is a stem of an ordinary English word that
  appears wherever anybody discusses context limits. A vocabulary carrying 207
  terms of which 105 fire and one supplies a third of the mass has a **term
  selection** problem that changing platform does not fix.

## 4 · What each outcome means, decided now

| result | reading |
|---|---|
| **per-entry >= 4%, i.e. 10x GitHub's 0.39%** | the register hypothesis holds strongly. The vocabulary is fine and GitHub was the wrong platform for it. Per-platform signal terms become the clear ruling |
| **per-entry 1.5-4%** | the register hypothesis holds partly. Prose is the better fit AND the vocabulary is thin on both. Per-platform terms help, and so would widening the per-entry sets on **both** platforms — two fixes rather than one |
| **per-entry < 1%, near GitHub's 0.39%** | **the register hypothesis is wrong.** The vocabulary underperforms on the corpus it was written for, and the platform reading was never the story. Term selection is the whole finding, and per-platform rendering loses its coverage argument entirely |
| **never-fire count stays near 102** | decisive whichever way the rates go: a term that fires on neither platform is dead vocabulary, not misplaced vocabulary |

**The never-fire count is the sharpest of the four** and I want it read as the
primary. Rates can move for corpus-size reasons; a term that fires zero times
across 32,723 GitHub candidates *and* 316 prose documents is not in the wrong
place.

## 5 · What this cannot settle

**The prose corpus is 316 documents against GitHub's 32,723 candidates** — two
orders of magnitude apart. That asymmetry cuts one specific way and it must be
stated with the result:

- A **high** prose rate on 316 documents is trustworthy — a rate that survives a
  small sample is real.
- A **zero** on 316 documents is not the same claim as a zero on 32,723. A term
  firing once in 2,000 prose documents would read as 0 here. **So the never-fire
  list from prose is an upper bound, not a count**, and any term it calls dead
  needs the larger corpus before it is removed from anything.

**And the blog corpus is one dominant author.** 120 blog documents, heavily one
voice. "Prose register" is a claim about how engineers write; this is mostly a
claim about how one engineer writes.

## 6 · What would make me drop the per-platform proposal

Stated plainly so it is not defended past its evidence: **if the per-entry rate
on prose comes back under 1%, I will withdraw the coverage argument in
`docs/proposals/for-engineer-2-per-platform-signal-terms.md`** and reduce that
proposal to the efficiency argument it already had, which is Engineer 2's to
weigh on its own merits.

The measurement follows this document, not the reverse.

---

# The result: the register hypothesis is falsified, and my own pooled figure was a denominator error

## 7 · Pooling blogs with Reddit was wrong, and I did it first

My first run reported the prose corpus as one population: **8.57% vocabulary-wide,
0.16% per-entry, 191 of 207 never firing.** Read that way it looks like prose is
*worse* than GitHub, which would have been a strange result.

It is a pooling error. **Median document length: blogs 6,054 characters, Reddit
95.** A 64x difference, averaged into one figure.

```
blog     n=119   median 6,054   p90 20,291   max 69,934
           vocabulary-wide 21.85%    per-entry median 0.42%
           of the 68 documents >=4,000 chars:  30.88%

reddit   n=196   median    95   p90    403   max  3,550
           vocabulary-wide  0.51%    per-entry median 0.00%
```

**Reddit's 95-character comments dragged blogs' 21.85% down to 8.57%.** Exactly
the class of error this document's own §1 warned about, committed two sections
later by me. A 95-character comment has no room for an eight-word phrase; it is
not evidence that the vocabulary fails on prose.

**Reddit is not the essay corpus and must not be reported as prose.** The essay
corpus is the 119 blog documents.

## 8 · Against the prediction, on the corpus that is actually prose

| figure | GitHub | **predicted** | **blogs, measured** |
|---|---|---|---|
| vocabulary-wide | 16.25% | 30-55% | **21.85%** (30.88% on long-form) |
| per-entry median | 0.39% | 1.5-4% | **0.42%** |
| never fire | 102 | 60-85 | 191 pooled — see §9 |

**My prediction was wrong in the direction I said it might be, and by more.** I
predicted "better on prose, but by less than the register argument implies." The
vocabulary-wide rate is better — 21.85% against 16.25%, and 30.88% on long-form,
which lands inside the predicted band. **The per-entry rate is not better at all:
0.42% against 0.39%.**

## 9 · The pre-registered row that fires

> **per-entry < 1%, near GitHub's 0.39%** — *"the register hypothesis is wrong.
> The vocabulary underperforms on the corpus it was written for, and the platform
> reading was never the story. Term selection is the whole finding, and
> per-platform rendering loses its coverage argument entirely."*

**0.42% on blogs. The row fires, on the corpus the vocabulary was written for.**

And the sharpest single number, from the pooled run where it is still valid
because it is a zero rather than a rate:

```
DEAD ON BOTH PLATFORMS: 101 of 207 terms
```

**Half the vocabulary fires nowhere** — not on 32,723 GitHub candidates and not
on 315 prose documents. A term that fires on neither is dead vocabulary, not
misplaced vocabulary, and §4 pre-committed to reading that as primary.

**The distinction the result forces:**

- **The vocabulary as a whole is somewhat better matched to prose** — 21.85%
  against 16.25%, 30.88% on long-form. The register argument is not nothing.
- **Each entry's ~8 terms are equally thin on both platforms** — 0.42% against
  0.39%. And it is the per-entry rate that a request asks, so it is the per-entry
  rate that determines retrieval.

Per-platform terms address the first and not the second. **More terms per entry
addresses the second, on both platforms at once.**

## 10 · Withdrawing the coverage argument, as committed

§6 said: *"if the per-entry rate on prose comes back under 1%, I will withdraw
the coverage argument in `for-engineer-2-per-platform-signal-terms.md`."*

**It came back at 0.42%. Withdrawn.** That proposal now carries only its original
efficiency argument, which is Engineer 2's to weigh on its own merits, and the
coverage claim is retracted in the file itself rather than left standing.

**What replaces it as the finding:** the signal group is thin per entry
everywhere, half the vocabulary is dead, and one term supplies a third of GitHub's
firings. That is a term-selection problem, it is platform-independent, and it is
a bigger lever than either per-platform rendering or the locality window.

## 11 · What this still cannot settle

**119 blog documents, one dominant author.** "The vocabulary works better on
prose" is a claim about how engineers write; this measures how one engineer
writes, plus 68 documents long enough to carry a phrase.

**And the never-fire count from prose is an upper bound, not a count** — §5 said
so before the numbers and it holds: a term firing once in 2,000 prose documents
reads as 0 across 119. The 101 dead-on-both figure is the durable one, because
its GitHub half rests on 32,723 candidates.
