# Signal terms are prose-shaped and GitHub is not: per-platform rendering, argued from measurement

> ## ⚠ THE COVERAGE ARGUMENT BELOW IS WITHDRAWN — 2026-08-24, same day
>
> **Sections 2, 3 and 5 rest on a hypothesis that has since been tested and
> falsified.** `docs/measurements/prediction-signal-on-prose.md` pre-registered
> the test and its thresholds, then ran it on the 119 blog documents:
>
> ```
>                       GitHub    blogs (the essay corpus)
> vocabulary-wide       16.25%    21.85%   (30.88% on long-form)
> per-entry median       0.39%     0.42%   <- the figure a request asks
> ```
>
> **The per-entry rate is the same on both platforms.** The vocabulary as a whole
> is somewhat better matched to prose, but each entry's ~8 terms are equally thin
> everywhere — and it is the per-entry rate that determines retrieval. Per-platform
> terms address the first and not the second.
>
> **101 of 207 terms fire on neither platform.** That is a term-selection problem,
> it is platform-independent, and it is a larger lever than per-platform rendering.
>
> I committed in advance to withdrawing this if per-entry on prose came back under
> 1%. It came back at 0.42%. **What remains of this proposal is the efficiency
> argument in §3 row 1, which was never mine and stands on its own merits.**
>
> Left in place rather than deleted, because a proposal that was argued and then
> refuted by its own pre-registered test is worth more as a record than as an
> absence.


**Proposed. `contract/queries.yaml` unchanged by this document** — it is shared,
and this is a ruling rather than an edit.

*Engineer 1 · 2026-08-24*

---

## 1 · The measurement, in four numbers

Over 32,723 candidates retrieved from GitHub and re-sieved offline with
`sieve._pattern_for` — the same matcher the sieve uses:

```
signal terms in contract/queries.yaml       207
  fired at least once                       105
  NEVER fired                               102   (49.3%)
`truncat` alone                          34.2% of all firings
top 10 terms                             64.8% of all firings
```

Per-entry, which is what a single request actually asks (median 8 terms):

```
best   code.editing_diff_fidelity:negative      9.05%
median across 26 entries                        0.39%
worst  three entries at exactly                 0.00%
```

Full working: `docs/measurements/the-signal-group.md`. The raw per-term counts
are `docs/measurements/signal-term-counts.json`.

## 2 · The register is the variable, not the capability

**Fires:** `truncat`, `hallucinated`, `infinite loop`, `gets stuck`, `timed out`,
`unparseable`, `invalid json`, `invalid argument`.

**Never fires:** `forgets the middle`, `applied cleanly`, `compiled first try`,
`didn't invent`, `faithful to the source`, `declined a perfectly`,
`full window without`, `drifted from the format`, `always picked the right`.

Both lists span the same capabilities. What separates them is **register**: an
engineer writing an essay says *"it loses recall past about 80k"*; the same
engineer opening an issue titles it *"context truncated at 128k"*. **An issue
reports a symptom with a number. An essay reports an impression with an adverb.**

The four terms that already work are all in the issue register, which is the
evidence that register is the variable — nothing about `truncat` makes it a better
description of `context.effective_window` than `forgets the middle` is. It is
just what people type into a bug tracker.

## 3 · This is the second independent argument for per-platform rendering

Stated plainly because the arguments arrive from different places and that is
what makes them worth combining:

| | argument | where it came from |
|---|---|---|
| 1 | budget and alias surfaces — a query rendered for one platform wastes requests on another | costing, and the `github_alias_form` hyphenation rule |
| 2 | **the signal vocabulary is register-specific, and 49.3% of it never fires on GitHub** | **this measurement** |

The first is an efficiency argument. **This one is a coverage argument, and it is
the stronger of the two** — a wasted request costs money, a term that never fires
costs evidence that exists and is never retrieved.

## 4 · What I am proposing, and what I am explicitly not

**Proposing:** that `signal` becomes per-platform in `contract/queries.yaml`,
with the current set retained as the blog/essay register and a GitHub register
added beside it. Shape, not content:

```yaml
signal:
  prose:   [loses recall, forgets the middle, ...]     # blogs, Reddit long-form
  issue:   [truncates at, returns empty, exits 1, ...] # GitHub
```

**Not proposing** which terms go in the issue register. Three reasons, and the
third is the one that matters:

1. **The list should be derived from the corpus, not invented.** We now have
   32,723 GitHub candidates. The right way to build it is to read what the
   sieve's *rejections* actually say — `harvest_run` records candidates and the
   texts are in `_sweep_store`.
2. **A term I invent is a term nobody typed.** `contract/queries.yaml` already
   carries the lesson: 275 of 275 multi-word terms failed to match their own
   plural before the final-word stem landed, and nobody noticed because nobody
   measured.
3. **The capability vocabulary itself is under a separate open question** —
   `the-vocabulary-hypothesis.md` predicts a majority of claims may come back
   `no-key-fits`. Rewriting signal terms per capability before that resolves
   risks doing the work twice.

**Also not proposing:** relaxing the exclusion set. It was the obvious suspect
and it is measured at **15%** of signal-bearing candidates, with the median issue
retaining 78.5% prose. It is not the constraint.

## 5 · The asymmetry that should decide the priority

**Positive stances are systematically worse than negative ones.** Four of the
five worst-performing entries are positive; the best is negative.

That lands on the part of the design least able to absorb it. `harvest.yaml` is
explicit that for the four **silent-failure** capabilities, *"nobody complained"
is not evidence, because you would not find out* — so those capabilities need
positive retrieval to reach consensus at all. Measured:

```
context.effective_window:positive     0.07%
format.structured_output:positive     0.00%
tool_calling.schema_accuracy:positive 0.00%
```

**If the issue register is only built for negative stances, the silent-failure
capabilities stay unretrievable on GitHub** — and the model page renders silence
that rule 4 says must not read as approval. So whichever way this ruling goes,
the positive/silent-failure half is the half to do first.

## 6 · What it costs, and the sequencing question that is yours

**The edit** is a `contract/queries.yaml` schema change plus a `TermSet` change
in `collect/adapters/queries/contract.py` to carry a per-platform set, plus
`plan_searches` selecting by platform. Small — the platform is already known at
render time, since `render_search` takes GitHub-specific scope qualifiers.

**The sequencing matters more than the edit.** 33 models are unreached. My
recommendation, argued in `the-signal-group.md` §6:

> Run the remaining ~3 nights as a **measurement**, not as a baseline. A baseline
> measured with a vocabulary that is about to change is a baseline nobody can
> compare against — the signal terms are embedded in the rendered queries, so
> changing them changes the retrieved corpus and the later sweep is a different
> instrument.

The measurement run is worth having regardless: three entries read 0.00% on
4,000 candidates, and **0 of 4,000 and 0 of 30,000 are different findings.** The
vocabulary decision needs the larger denominator, and a measurement's value does
not depend on comparability.

**The thing to avoid**, which is the default if nobody decides: finish the sweep,
call it the baseline, then change the vocabulary — leaving a before-and-after
whose instrument moved in between.
