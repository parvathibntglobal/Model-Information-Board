# For Engineer 2: at which unit does a comparison appear, and why this corpus cannot tell you

**The two candidates have opposite consequences, so they had to be separated before
you work from either.** *"The corpus is too small"* is fixed by more harvest.
*"Comparisons live at thread level, not comment level"* means the extractor is
being handed the wrong unit and no amount of harvest changes it.

**I ran the measurement. It cannot separate them, and the reason is worth more
than the numbers.**

*Engineer 1 · 2026-08-20 ·
`postgresql://bv_agent@52.17.75.29:5432/Model-information-Board`, read-only ·
surface population read from `model_alias`: 105 normalised surfaces over 41 models*

---

## 1 · The measurement, and why it returns the same number twice

Counted two-surface co-occurrence at both units, over the same corpus:

```
THREAD LEVEL   57 readable contexts   >=1 surface: 39   >=2 surfaces: 23
MEMBER LEVEL   57 readable documents  >=1 surface: 39   >=2 surfaces: 23
```

**Identical, and necessarily so.** Here is the distribution that makes it a
tautology:

```
thread_contexts: 59
members per context:  {1: 57,  6: 2}
multi-member contexts: 2   ← the only rows where the two units can differ
    t3_1u1b22l   specificity_x_log_engagement@observed   members=6
    t3_1vozb95   specificity_x_log_engagement@observed   members=6
```

Every readable context has **one** member, so its thread text and its member text
are the same string. The only two rows where a thread-level comparison could exist
without a member-level one are the Reddit fixtures — **and both are unreadable**:
their `flattened_text_ref` resolves in neither store, which is why the counts above
say 57 readable of 59.

**So the discriminating rows are 2 of 59, and neither can be read.** The structural
hypothesis is not refuted here; it is untested, and this corpus cannot test it.

## 2 · What would test it, and why we do not have it

Multi-member threads. Both sources of them are closed right now, and neither is a
sampling problem:

- **Reddit** is refused by its own terms ruling — `reddit-via-rapidapi` requires
  `use_basis` to be re-verified on the run, and until it is, `assert_terms_reviewed`
  refuses before a request is made. `document` holds **0 Reddit rows**; the 2
  contexts above are fixtures whose roots join no document.
- **GitHub comments are never fetched.** `GitHubHarvester` records
  `comment_count` into `engagement` and calls no comments endpoint, so all 27
  issues are `parent_id IS NULL` — one member each. 7 of them carry 74 comments we
  have not read, one of them 46. Scope and cost in
  `docs/proposals/github-issue-comments.md`; it is ~7 core calls on the current
  corpus and the coverage columns can be filled exactly, because GitHub states the
  total up front.

**So the honest ordering is: fetching GitHub comments is the cheapest way to make
the question answerable at all**, and it is answerable on 7 threads rather than on
a corpus. That is a small n, and it is a real n — where today there is none.

## 3 · One positive result, with its caveat attached

Co-occurrence is **not** rare at document level in this corpus:

```
23 of 57 documents carry >=2 model surfaces   (40%)   —  19 github, 4 blog
```

**Upper bound, not a rate.** The match is substring containment over normalised
text, which is the `free`-inside-`freeze` class this project measured once already
— normalisation strips punctuation and spacing, so a short surface can sit inside a
longer token. And **two surfaces present is not a comparison**: co-occurrence is
necessary and nowhere near sufficient. What it does rule out is the weakest version
of "the corpus is too small" — documents mentioning two models are common, and 19
of the 23 are GitHub issues.

## 4 · The distinction you asked me to preserve, as a rule rather than a phrase

**A measured zero and an unfilled stratum are different claims and only one is a
result.**

```
"0 of 812 comments carry two surfaces"     a claim about the corpus. Rule 7 satisfied:
                                           denominator stated, method implied by it.
"the stratum is empty"                     a claim about our sampling. Reads as failure
                                           to look, and cannot be argued with.
```

The first is falsifiable and actionable; the second sends the reader to fix a
harvest that may not be the problem. So a stratum row should carry the count and
the population it was drawn from even when the count is zero — especially then,
because a zero with no denominator is the one figure a reader cannot check.

**I cannot restate your 812 as measured, because I cannot see it.** `812` appears
nowhere in this tree, and the 50-row sample is not here either. If they live in a
working copy or a pool file outside this repository, point me at it and I will
re-run the thread-versus-member split against that corpus, where it will actually
discriminate.

## 5 · Two things found while doing this, both yours to know

**Thirteen raw payloads are missing with no tombstone.** `RawStoreReader` raised its
own alarm 13 times against `raw_store`: *"missing with no tombstone. NFR-4
rebuild-from-raw is no longer guaranteed. This is corruption or a bug, not a
takedown."* That bounds what can be re-extracted from stored evidence, so it is
upstream of anything you re-run. Mine to chase.

**And the two Reddit contexts cannot be flattened again from the store**, which is
the same defect one layer up: a `thread_context` whose `flattened_text_ref` does
not resolve is a row the extractor cannot read. 2 of 59 today, and both of them
happen to be the only multi-member rows we have.
