# Specificity backfill — the calibration `harvest.yaml` names

**285 documents re-scored from the raw store. No fetch.** The floor drops 22 of
them, and the run found a defect in the scorer it was measuring.

*Engineer 1 · 174 GitHub candidates · 111 blog articles · 2026-08-17*

> **`names_version` was broken when this run started.** `sieve.matches`
> documents itself as operating on *"already-normalised text"* and does not
> casefold; the first version of `names_version` passed raw text, so it missed
> every capitalised model name — which is how people write them. It scored
> **1 of 111** blog articles where the true figure is **7**. All 45 tests passed
> against the defect because every one used lowercase. Fixed, and the numbers
> below are post-fix. §5 is what the near-miss says.

---

## 1 · The floor — weight-independent, and therefore solid

The floor is a five-way OR over the components. **It does not read the weights
at all**, so nothing here changes if the weights change.

| channel | n | clears | fails | unscored | clear rate |
|---|---|---|---|---|---|
| github | 174 | 172 | 2 | 0 | **98.9%** |
| blogs | 111 | 91 | 20 | 0 | **82.0%** |
| **total** | **285** | **263** | **22** | **0** | **92.3%** |

`filter_reasons` written: 263 rows clean, 22 rows `specificity-floor`.

**`unscored` is 0 by construction** — every document in this corpus was scored
by this run. `FloorVerdict.UNKNOWN` exists for `document` rows written before
the scorer, which live in a database this re-score does not touch. Its zero here
is not evidence the state is unreachable, and reading it that way would be the
mistake the tri-state exists to prevent.

### The floor is not carrying the load it is credited with

`docs/logic-and-workflow.md` says *"the hard gates plus the specificity floor
already remove the overwhelming majority of junk"*. **The floor removes 7.7%.**

That is not a contradiction of the ~10–15% triage survival estimate, because the
floor is one gate of several — language, token count, resolvable entity, window,
bot list and amplification collapse all run too, and none of them exists yet. But
it does locate the expectation: **if survival is to land near 10–15%, the hard
gates have to do nearly all of it.** The floor as specified is a backstop, not a
filter, and the sentence crediting the pair should not be read as crediting the
floor.

Whether that is the right design is a real question and this measurement does
not answer it. It only says the floor is currently cheap.

### 7.7% carries a parameter, added 2026-08-18

**The floor is not a pure function of the document.** `score_document(text, *,
version_aliases=...)` takes the alias list, and `names_version` is one of the
five components the floor ORs over. So the same document clears or fails the
floor depending on which surfaces were loaded when it ran.

Measured on the 1,074 documents of `_substitution_slice/` that survive the built
hard gates, changing only the alias population:

| alias population | floor drops | of survivors |
|---|---|---|
| hand-written, 11 seeded models, 59 surfaces | 41 | **3.8%** |
| registry-derived union, 340 models, 1,337 surfaces | 9 | **0.8%** |

Identical documents. A factor of four.

So the figure above is properly stated as:

```
the specificity floor drops 7.7%
  of 285 documents — 174 GitHub candidates, 111 blog articles
  re-scored from the raw store, 2026-08-17, no fetch
  under the alias surfaces loaded that day: contract/seed_models.yaml,
  11 models, 59 surfaces
  NOT RE-DERIVABLE. That raw store no longer exists on any machine, and
  the alias list has since grown.
```

Not wrong, and not reproducible. It remains the only calibration this stage has,
which is the reason to state its parameter rather than quietly retire it — and
the reason a re-run belongs on the list in §6.

---

## 2 · Per-component hit rates — also weight-independent

| component | github | blogs | both |
|---|---|---|---|
| `has_numbers` | 87 · 50.0% | 63 · 56.8% | 150 · 52.6% |
| `has_error_strings` | 73 · 42.0% | 4 · **3.6%** | 77 · 27.0% |
| `has_code` | 159 · 91.4% | 60 · 54.1% | 219 · 76.8% |
| `has_conditions` | 36 · 20.7% | 18 · 16.2% | 54 · 18.9% |
| `names_version` | 84 · 48.3% | 7 · **6.3%** | 91 · 31.9% |

Components present per document:

| count | github | blogs | both |
|---|---|---|---|
| 0 | 2 | 20 | 22 |
| 1 | 23 | 45 | 68 |
| 2 | 65 | 33 | 98 |
| 3 | 54 | 11 | 65 |
| 4 | 26 | 2 | 28 |
| 5 | 4 | 0 | 4 |

A GitHub document typically carries two or three components; a blog article
typically carries one. Four of 111 blog articles reach four, and none reaches
five.

---

## 3 · The channels supply different things, and sharply

| component | github | blogs | gap |
|---|---|---|---|
| `names_version` | 48.3% | 6.3% | **+42.0 pp** |
| `has_error_strings` | 42.0% | 3.6% | **+38.4 pp** |
| `has_code` | 91.4% | 54.1% | **+37.3 pp** |
| `has_conditions` | 20.7% | 16.2% | +4.5 pp |
| `has_numbers` | 50.0% | 56.8% | **−6.8 pp** |

This is the platform-job question with numbers on it.

**GitHub supplies identity and machine evidence.** Error strings, code
containers and a version-specific model name, the last of which usually arrives
in a config block rather than a sentence — which is exactly the aboutness
argument `sieve` makes for matching subject anywhere.

**Blogs supply prose and quantities, and almost no resolvable identity.** 6.3%
name a model at version or snapshot specificity. Including family surfaces takes
it to 9.0%, and the extra 2.7 points are documents naming a *line* rather than a
tier, which cannot be attributed. `collect/CLAUDE.md` calls blogs **the only
positive-evidence channel**; they are also the channel that least often says
which model it is talking about.

That is the registry-generation problem again, from a different angle, and it
agrees with the substitution slice: the corpus discusses models the registry has
never heard of.

---

## 4 · Score distribution — provisional, and not comparable to §1 or §2

**Everything in this section reads five weights nobody has calibrated.** A
weight change moves every number here and cannot move a single number above.

| channel | min | median | max | mean |
|---|---|---|---|---|
| github | 0.00 | 0.50 | 1.00 | 0.527 |
| blogs | 0.00 | 0.25 | 0.85 | 0.286 |

```
github   0.0-0.2   4   0.2-0.4  47   0.4-0.6  44   0.6-0.8  55   0.8-1.0  24
blogs    0.0-0.2  24   0.2-0.4  49   0.4-0.6  30   0.6-0.8   7   0.8-1.0   1
```

### The finding that matters, and it is about the weights

**The composite systematically ranks blogs below GitHub — 0.286 against 0.527 —
and the largest single weight sits on the component blogs almost never have.**
`has_error_strings` carries 0.30 and is present in 3.6% of blog articles.
`names_version` carries 0.15 and is present in 6.3%. Nearly half the available
weight is on two components the positive-evidence channel structurally lacks.

Latent rather than active today, and the distinction is worth keeping: E3 ranks
children *within a thread*, so every comparison it makes is intra-channel and
this bias never fires. It fires the moment the composite is used as a
corpus-wide quality sort — a "best evidence" list, a triage priority queue, a
cross-channel ranking of any kind.

It is also rule 4 in a new place. A blog article reporting *"we ran it on 40k
tickets a week for three months, no complaints"* — which
`contract/queries.yaml` calls the only way a silent failure can be cleared —
carries numbers and nothing else, and scores 0.25. A GitHub issue with a
traceback and a config block scores 0.65 while asserting nothing about quality
at all. **Absence of an error string is being scored as absence of specificity
on the one channel where positive evidence lives.**

I am not proposing a weight change on this evidence. One corpus of 285
documents, with a known registry gap depressing `names_version`, does not
establish what the weights should be. What it establishes is that the
provisional weights encode a channel preference nobody chose, and that the
correct next step is a decision about whether the composite is ever allowed to
compare across channels.

---

## 5 · What the near-miss says about the test suite

The defect was in `names_version`, found by cross-checking one figure against a
direct count rather than by a test. The tests could not have found it: all 45
used lowercase model names, and the function was correct for lowercase.

That is the same shape as the `assemble_thread` refusal test — which asserted
that the message *mentioned* `specificity_score` rather than that the claim was
*true* — and as the `sieve_any` option no test ever passed. **A test that
exercises only the shape the author had in mind cannot fail for the reason it
was written.**

Four tests now cover capitalisation and line-wrapped names, verified by
reverting the fix and watching three of them fail.

The cheap general lesson, recorded because it keeps recurring here: when a
detector delegates to something whose docstring states a precondition —
`matches` says *"already-normalised text"* — the precondition is the test case,
not a comment.

---

## 6 · What would revise this

- **The poller.** `names_version` at 6.3% on blogs is measuring the registry, not
  the channel. Re-run once `contract/seed_models.yaml` is replaced.
- **The other E4 gates.** The floor's 7.7% is only interpretable against total
  triage survival. Three of the six now exist (`collect/triage/gates.py`); the
  language gate and the bot list still do not.
- **A re-run under a stated alias population.** The 7.7% was taken under the
  hand-written 59, which is the narrowest population this project will ever use
  again. `SurfacePopulation.fingerprint` exists so the next run records which
  one it used.
- **A labelled corpus.** Nothing here calibrates the weights; it only shows what
  the current ones do. §4 is a description, not a validation.
