# What separates a populated board from a publishing one: evidence tier, not volume

**It is not comment fetching, and it is not this run.** Both were my answer and
Anooj's, and the stored weights say otherwise. The gate is blocked by
`f_evidence`, and the corpus contains **zero** tier-A, tier-B and tier-C claims.

More volume does not move this. **More Reddit does not move this at all.**

*Engineer 1 · 2026-08-28. Measured on the 46 pre-existing claims, before the
1,512-context run landed, so nothing here is shaped by its outcome.*

---

## 1 · The measurement

Seven factors, multiplied, all stored (`claim_weight`), n=46:

```
                  min      median     max      distinct values observed
f_evidence      0.0200     0.1200   0.1200     0.02  0.04  0.12
f_platform      0.8500     0.8500   0.9000     0.85  0.90
f_specificity   0.4400     0.4400   0.7200     0.44  0.58  0.72
f_relevance     0.4000     1.0000   1.0000     0.40  1.00
f_recency       0.2618     0.8123   0.9809     ...
f_launch        0.4500     1.0000   1.0000     0.45  1.00
f_fuzziness     0.3000     0.6000   0.6000     0.30  0.60

product         0.0022     0.0217   0.0452
```

`N_EFF_MINIMUM = 3.0`. At the observed median claim weight of **0.0217**, one
cell needs

```
3.0 / 0.0217  =  138 independent voices
```

At the best weight any claim in this corpus achieved, 0.0452, it needs **67**.

## 2 · Why, and the answer is one factor

```
TIER_WEIGHT   A 1.00   published harness/prompts, N runs, numbers; or a GITHUB REPRO
              B 0.65   detailed first-hand build report: task, versions, conditions
              C 0.35   qualitative first-hand with conditions
              D 0.12   bare first-hand opinion
              E 0.04   hearsay, summarising someone else
              F 0.02   vendor marketing

observed      D 42     E 3     F 1     A 0     B 0     C 0
```

**Every claim on this board is a bare first-hand opinion or worse.** Tier D
alone costs a factor of 8.3 against tier A, and it is 42 of 46.

The other factors are working as designed and none is the problem.
`f_fuzziness = 0.6` is `version` rather than `snapshot` — engineers write
"Opus 4.8", not a dated snapshot id — and that is a fact about how people talk,
not a defect. `f_platform = 0.85` is Reddit's base. Neither is worth chasing.

## 3 · A correction to something I asserted an hour ago

I claimed the gate's own arithmetic was wrong — that
`MAX_POSSIBLE_WEIGHT = 0.95` could not be reached because `f_fuzziness` tops out
at 0.6, so the docstring's *"`n_eff >= 3.0` already demands four or more
claims"* was off by a factor of twenty.

**That was wrong and I had checked five of the seven factors.**
`FUZZINESS_WEIGHT["snapshot"] = 1.0`; every non-platform factor genuinely does
top out at 1.0; `MAX_POSSIBLE_WEIGHT` is 0.95 and the comment is correct.

What survives is smaller and truer. The docstring is right **about tier-A
evidence** and carries no denominator, so it reads as a statement about claims
in general:

> *"A single claim cannot exceed w = 0.95 … so `n_eff >= 3.0` already demands
> four or more claims."*

Four or more **tier-A** claims. The corpus has zero. **Rule 7 exactly** — a real
number answering a question it was not asked, and it survived inspection because
the arithmetic checks out. The check that catches it is the one rule 7 names:
ask what population the figure was drawn from.

Worth a clause in that docstring, and it is E2's file.

## 4 · What actually clears the gate, with the arithmetic

A tier-A GitHub claim, realistic other factors:

```
1.00  f_evidence   tier A
0.95  f_platform   github
0.72  f_specificity
1.00  f_relevance  central
0.90  f_recency    fresh
1.00  f_launch
0.60  f_fuzziness  "opus 4.8" — version, not snapshot
----
0.37  per claim    ->  n_eff 3.0 needs ~8 independent voices
```

**Eight tier-A voices on one (model, capability, condition_bucket).** That is a
demanding target and it is a reachable one. 138 is not.

And tier A's own gloss names the channel: *"or a GitHub repro."*

## 5 · Which makes today's three findings one finding

```
GitHub thread_contexts hold JSON envelopes       ->  GitHub has 0 claims
GitHub is the tier-A channel (repro steps)       ->  no tier-A evidence exists
GitHub is the only available SECOND platform     ->  PLATFORM_MINIMUM = 2 unmet
```

Both gate conditions that block every cell today are blocked by **the same
defect**, in the same 80 rows, on the platform nobody had checked.

So the answer to *"what stands between a populated board and a publishing
board"* is not comment fetching and not corpus size. **It is that the one
platform capable of producing publishable evidence has been writing JSON where
prose belongs**, and its 80 documents have never produced a claim.

## 6 · What this says about the Reddit work, and it is not nothing

The 1,512 contexts are tier D by construction: a Reddit comment is a bare
first-hand opinion, and `f_platform = 0.85` on top. **They will populate the
board and they cannot publish a cell, at any volume.** That is not a failure of
the sweep — it is what the weight function is for, and it is working.

What they are worth:

- **coverage** — which models and capabilities are discussed at all, and rule
  4's distinction between silence and criticism needs exactly this.
- **the denominator** for every retrieval and yield figure this project quotes.
- **direction**, as a weight rather than a gate (rule 8): where to point GitHub
  queries, which is where the publishable evidence is.

**And comment fetching is still worth doing** — 132,442 unread comments, and
`coverage_ratio = 0.0` on 1,417 of the contexts is an honest embarrassment. It
buys voices and coverage. It does not buy a published cell, and I said it would.

## 7 · What would revise this

`evidence_tier_by_speaking` in `contract/harvest.yaml` is flagged in
`weight.py` as wanting E2's sign-off — *"the mapping changes the weight of
three stored claims by 6x"*. If tier assignment changes, §1 changes with it.
Everything in §2 through §5 is about tier D being 0.12 and the corpus having no
tier A, and neither depends on that mapping.

The threshold itself is not mine to move and I am not proposing it. `3.0`
against tier-A weights asks for eight voices, which is a defensible bar for
*"engineers report"*. The problem was never the bar.
