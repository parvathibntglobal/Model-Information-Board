# Triage: 8.7% of 195. And 23.8% was a different quantity

**Four results, and two of them correct something I said last turn.**

1. **Survival is 8.7%** — 17 of 195, below the 10–15% band, and an upper bound.
2. **23.8% is not a survival figure.** It is this thread's `coverage_ratio`,
   `195 / (195 + 623)`. Different quantity, different denominator, and the two
   are not comparable.
3. **Triage does not move the gate**, because both claim-bearing documents
   survive it. It moves the *ceiling* by a factor of nine. Those are different
   facts and both are reported.
4. **`platform_count` is not one storage step away** — I said that last turn and
   it was wrong. It is blocked behind the same thing triage is: **nothing writes
   `collect/triage/`'s output.**

*Engineer 1 · 2026-08-21 · no model calls, no writes*

---

## 1 · Triage over the 195

Run read-only. `triage_verdict` is still NULL on 254 of 254 — see §2 for why that
is not a choice.

```
documents   195
kept         17
dropped     178
SURVIVAL    8.7%      (population c511fceb6b7fb3df, 1385 surfaces)

GATES THAT FIRED
  no-resolvable-entity      177
  too-short-no-artifact      74
GATES THAT COULD NOT RUN
  wrong-language            195      no detector
  known-bot                 195      no list
GATES WITH NOTHING TO RUN ON
  pure-link-post            195      comments have no such notion
  out-of-window             195      no in-window mapping supplied
```

**8.7% is an UPPER BOUND.** Two gates could not run and two had nothing to run
on; documents those would have dropped are counted as kept. The true figure is
lower, and the run says so itself rather than leaving it to be inferred.

### Denominator, and it is not the estimate's population

195 comments from **one thread**, one subreddit, one model-announcement post,
from one `getPostComments` call — and 195 of a reported 785, so under a quarter
of even that thread. The estimate is *"~10–15% of documents retrieved from the
sources we sweep"*. This is one thread, not a sample of those sources.

You are right that it is the first population that is neither query-retrieved nor
one author, and that is what makes it worth anything: it is the first time the
figure could be computed at all. What it establishes is that the first
measurement came in **under** the band, and that the band was never measured.

### The 177, and they are the inherited-subject problem

`no-resolvable-entity` drops **177 of 195 — 91%**. In an announcement thread the
root names the model and the comments say *"it's much faster"*.

**Extraction handles that by inheriting the subject and recording that it did.
Triage handles it by discarding the document before extraction sees it.** One
phenomenon, two stages, opposite treatments — and only one of them is written
down as a decision. That is the ruling worth having, and it governs 91% of this
corpus.

---

## 2 · 23.8% was `coverage_ratio`, not survival

```python
coverage_ratio = observed / (observed + hidden_children_min)
               = 195 / (195 + 623)
               = 0.2384
```

Confirmed three ways, all agreeing: the parser, the payload, and the stored
`thread_context` row (`t3_1u1b22l`: 195, 623, 0, 0.2383863).

**So 23.8% is the share of the tree we read, and 8.7% is the share of what we
read that survives the sieve.** They are not two measurements of one thing:

```
785 comments reported by Reddit
195 fetched            -> coverage_ratio 23.8%   "how much of the thread we hold"
 17 survive triage     -> survival      8.7%    "how much of what we hold is usable"
```

Composed, the thread yields 17 usable documents from a reported 785 — **2.2%** —
and that figure has a different meaning again and should not be quoted as
either. Three numbers, three populations. The reason to keep them apart is that
one is fixable by fetching more and the other is not.

> `coverage_ratio` also carries the more honest of the two labels already: its
> own docstring calls it *"AN UPPER BOUND ON COVERAGE, not an estimate of it"*,
> because the denominator uses a floor. Survival has now acquired the same
> property for a different reason — unrun gates — and says so in
> `TriageRun.describe()`.

---

## 3 · The gate, before and after triage

### On the claims that exist: identical, because both bearers survive

The four stored claims sit on two documents. Triaged individually:

```
ROOT   reddit:t3_1u1b22l   -> kept, no reasons
CHILD  reddit:t1_oqorjbe   -> kept, no reasons
```

So:

```
                            before triage        after triage
n_eff (as stored)               0.0121               0.0121
max_author_share                1.000                1.000
n_eff (claim.author_id propagated, code.generation)
                                0.0242               0.0242
max_author_share (same)         0.500                0.500
```

**Triage changes nothing about the gate on this corpus.** Your worry — that a
heavy triage drop would push `n_eff` back down and make the concentration fix
stop being the story — does not materialise, and the reason is specific rather
than lucky: the two documents that carry claims are exactly the two that name a
model outright. `no-resolvable-entity` is what dropped the other 178, and a
document that fails it was never going to produce a claim.

**That is the inverse of the case you were guarding against**, and it is worth
naming as its own fact: *the survival rate reads unhealthy and every voice that
currently matters survives it.* A survival rate is a statement about a corpus; a
voice count is a statement about a cell. On this thread the first is 8.7% and the
second is untouched.

### On the ceiling: a factor of nine

```
distinct authors across all 195 comments      151      n_eff ceiling 1.828
distinct authors among the 17 survivors        17      n_eff ceiling 0.206
max_author_share at 17 voices                0.059     cap 0.20 -> passes
```

Neither passes `N_EFF_MINIMUM = 3.0`. So triage does not create the problem and
does not fix it: it multiplies the distance by nine, from 1.6× short to 15×
short.

**Concentration is settled either way.** At 17 voices the share is 0.059 against
a cap of 0.20, and at 2 voices it was already 0.500 against a cap of 0.500. That
condition is not coming back.

---

## 4 · `platform_count`: I was wrong, and the correction is the finding

Last turn I called it *"one storage step — the 36 blog claims are extracted,
verified, and sitting in a JSON file"*. The storage step is real and it is not
the only one. Measured:

```
blog:  31 documents   31 thread_contexts (whole_document)   36 claims extracted
       created_at        31 of 31    <- compute() needs this, and it is there
       has_numbers        1 of 31    <- compute() needs this
       has_conditions     1 of 31    <- compute() needs this
       specificity_score  0 of 31
       triage_verdict     0 of 31
claim rows: 4, all reddit. Zero blog claims stored.
```

`compute()` refused on a real blog claim from the run, and named its own gaps:

```
refusing to weight: 4 input(s) were UNSUPPLIED.
  claim_date      [not carried]  document.created_at, via DocumentFacts
  version_named   [not carried]  closed 2026-08-21 (my call omitted it)
  has_numbers     [not carried]  document.has_numbers, written by collect/triage/
  has_conditions  [not carried]  document.has_conditions, written by collect/triage/
```

So the chain from a blog `thread_context` to a blog claim in a cell is **four
steps, not one**:

| | | |
|---|---|---|
| 1 | 31 blog `thread_context` rows | **done** |
| 2 | 36 claims extracted and verified | **done**, and stored in a JSON file rather than in `claim` |
| 3 | insert into `claim` | works — proved by a rolled-back insert when the `speaking` migration landed |
| 4 | `claim_weight` via `compute()` | **blocked.** `claim_date` is pure carriage (`created_at` is 31 of 31). `has_numbers` and `has_conditions` are NULL on 30 of 31, so they are *measurement*, not carriage |
| 5 | reach a cell | `CellStore.weighted_claims_for` INNER JOINs `claim_weight`, so an unweighted claim is excluded rather than counted at zero — correctly |

**And step 4's two missing columns are written by `collect/triage/`.** Which has
never run. Which brings the two halves of this turn together:

> **`platform_count` is blocked behind the same thing triage is.** Not behind a
> corpus, not behind extraction, and not behind `judge/`. Behind the fact that
> `collect/triage/` computes verdicts and signals that **nothing persists**.

### The writer does not exist

```
$ grep -rn "triage_verdict" collect/ scripts/
collect/triage/gates.py:8:   ...`triage_verdict` is        <- a docstring
```

One occurrence in the whole lane, and it is prose. **There is no writer for
`triage_verdict`, `specificity_score`, `has_numbers` or `has_conditions`.** That
is why they are NULL corpus-wide — not because the stage is slow or the corpus
was small, but because the stage's output has nowhere to go.

**Same shape as `document.author_id` two days ago**: a stage that works, tests
that pass, and no caller. That one was found by asking why the gate saw one
voice. This one was found by asking why a blog claim cannot be weighted. Both
were invisible from inside the stage, because a stage with no writer has nothing
failing in it.

---

## 5 · The shape: a figure describing a state already resolved

**I cannot reproduce 805 or `coverage_ratio 0.195`, and I looked in the three
places that could hold them.** The payload, the parser and the stored row agree:

```
observed_children 195   hidden_children_min 623   hidden_branches_unsized 0
markers 101, all sized  reported_total 785        coverage_ratio 0.2384
```

`0.195` would need a denominator of 1000, i.e. `hidden_children_min = 805`. No
such value appears in `thread_context`, in the fixture, or in any document.

**And the double-count it would imply is not present on this thread.** I checked
directly, because that is the claim's substance: the 101 markers list 464 child
ids between them, and **0 of the 464 are already in the observed 195.** So every
one of the 623 refers to a comment the fetch did not have, and on this payload
the floor is honest.

So the instance is either from a run I cannot see or from a different thread.
Taking you at your word that the shape matters more than the instance — **here is
the shape, and a verifiable instance of it in this repository:**

> **A caveat or a count can describe a condition that a later fix removed, and
> nothing re-checks it, because a caveat is not a test.**

`ThreadCoverage.coverage_ratio`'s docstring:

> *"Reading it as a measurement is the mistake `hidden_branches_unsized` exists
> to make visible — **with 126 unsized branches**, this number is as optimistic
> as the data allows."*

And three paragraphs above it, the module docstring's worked example:

> *"at least 340 hidden across 126 branches, plus 126 branches of unknown size"*

```
hidden_branches_unsized, both stored threads:
  t3_1u1b22l   195 observed, 623 hidden, 0 unsized, 101 of 101 markers sized
  t3_1vozb95   182 observed, 265 hidden, 0 unsized
```

**Zero unsized branches, on every thread this project holds.** The caveat is
attached to a state that the fix documented immediately above it — counting
`count: 0` as *unsized* rather than *empty* — had already resolved. A reader
arriving at `coverage_ratio` is told the figure is "as optimistic as the data
allows" because of 126 branches of unknown size, and there are none.

**Why this class is expensive**, and it is the same reason as the `f_specificity`
constant and the alias list that matched nothing: the figure is not wrong, and it
survives a spot-check. 126 *was* the count. The number decayed rather than
erred, and nothing decays louder than prose. The check that catches it is not
suspicion — it is asking, of any figure quoted in a caveat, **when was this last
computed**.

Three instances of the family now, in three files:

```
f_specificity = 0.58        the only value the column ever held; 3 of 4 inputs dead
35 aliases                  a non-empty list, matching zero documents
126 unsized branches        a caveat's evidence, resolved by the fix above it
```

The first two were caught by counting. This one is caught by dating. Neither is
caught by reading.

**Not fixed here.** The docstring is E1's to correct and I would rather propose
the general rule with it: **a figure in a comment carries the date it was
measured, or it is a claim about the past written in the present tense.**

---

## What changed

Nothing. This turn is measurement, and the two write paths it points at —
`triage_verdict` and `DocumentFacts` — are the next two pieces of work rather
than something to slip in beside a measurement.

| next | why it is first |
|---|---|
| **a writer for `collect/triage/`'s output** | unblocks `platform_count`, the survival series, and the specificity floor at once. It is the missing caller, not a new stage. |
| **rule on the inherited subject in triage** | 177 of 195 turn on it, and the two stages disagree by accident |
| **`DocumentFacts` from the `document` table** | `judge/`'s side of step 4, and it needs the columns above to be populated first |
| **date the figures in comments** | the cheap half of §5 |
