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
