# The publication gate cannot be satisfied by any corpus, and it is three lines of YAML

**Not "has not been". Cannot be.** `TIER_WEIGHT` defines six tiers and the
extractor can only ever produce the bottom three, because `speaking` has three
values and the contract maps them to D, E and F.

```
judge/extract/schema.py     Speaking = Literal[
                              "own-experience",
                              "vendor-about-own-product",
                              "relayed-from-elsewhere",
                            ]

contract/harvest.yaml       own-experience:            D    0.12
                            relayed-from-elsewhere:    E    0.04
                            vendor-about-own-product:  F    0.02
```

**There is no value the extractor can emit that maps to A, B or C.** Tiers worth
1.00, 0.65 and 0.35 are unreachable by construction.

*Engineer 1 · 2026-08-28. Measured on 197 claims across three platforms: 0 at
A, B or C.*

---

## 1 · The measurement this run existed to make

The GitHub repair put 71 contexts into an extraction corpus for the first time.
GitHub is the channel tier A's own gloss names — *"published harness/prompts, N
runs, numbers; **or a GitHub repro**"*. So: what tier did they come out at?

```
             tier D   tier E   tier F      A/B/C
reddit         134       16       10          0
blog            16        3        1          0
github           7       10        0          0
```

**The 17 GitHub claims are 7 tier D and 10 tier E — worse than the corpus
average.** Not one reached A.

**And this is not a finding about the extractor.** It emitted exactly what its
schema allows. It is a finding about the mapping.

## 2 · Two axes were conflated, and the glosses say so

`TIER_WEIGHT`'s own descriptions are about **reproducibility**:

```
A  published harness/prompts, N runs, numbers; or a GitHub repro
B  detailed first-hand build report: task, versions, conditions
C  qualitative first-hand with conditions
D  bare first-hand opinion
```

A → D is a gradient of *how checkable the evidence is*. But the mapping keys on
`speaking`, which is *whose claim it is*. Those are different axes, and the
consequence is exact:

**An engineer who publishes a harness, three runs and numbers, and an engineer
who writes "opus feels slow", are both `own-experience` and therefore both tier
D.** A 8.3× difference in the gloss, collapsed to nothing by the key.

The information to tell them apart **already exists on the claim**.
`has_repro_steps` and `has_numbers` are extracted and passed into `compute()` —
they raise `f_specificity` from 0.44 to 0.72, a 1.6× lift, and do not touch the
tier at all.

## 3 · What it costs, arithmetically

At tier D the ceiling on a claim is `0.12 × 0.95 = 0.114` before the other five
factors, and the observed median is **0.0217**.

```
N_EFF_MINIMUM = 3.0

at tier D median (0.0217)   ->  138 independent voices on ONE cell
at the best weight seen     ->   67
at tier A realistic (0.37)  ->    8
```

The best cell on the board after 197 claims:

```
claude-sonnet-5 · reasoning.multistep · n_eff 0.1409 · 7 voices · 2 platforms
```

**Seven independent voices across two platforms is 4.7% of the threshold.** No
corpus reaches 138 voices on one (model, capability, condition_bucket). This is
why 94 of 94 cells fail `not_enough_weight` and why `PUBLISHED` has been 0 for
the life of the project.

## 4 · What I am NOT proposing

**Not lowering `N_EFF_MINIMUM`.** 3.0 against tier-A weights asks for about eight
voices, which is a defensible bar for *"engineers report"*. The bar was never the
problem.

**Not changing `TIER_WEIGHT`'s values.** `harvest.yaml` already flags 0.12/0.04/
0.02 as provisional and says the ORDER is what is not provisional. That is right
and I am not touching it.

**Not adding a fallback.** The 2026-08-21 ruling that a weighting input may not
have a silent default is exactly right, and `compute()` refusing on an unmapped
key is why this was findable at all.

## 5 · What I am asking for

**A ruling on whether `speaking` is the right key for tier**, and if it is not,
what is. The shape I would argue for, and it is yours to decide:

```
tier is a function of (speaking, has_repro_steps, has_numbers, ...)

  own-experience + repro steps + numbers      -> B or A
  own-experience + conditions                 -> C
  own-experience alone                        -> D     (unchanged)
  relayed-from-elsewhere                      -> E     (unchanged)
  vendor-about-own-product                    -> F     (unchanged)
```

Every input is already on the claim. Nothing new is extracted, and the order the
contract calls non-provisional is preserved: a vendor is still below a relay, a
relay still below first-hand.

**The rule-8 question applies to me here and I want to name it before you ask.**
`has_repro_steps` is the extractor's boolean, unmeasured, and promoting a claim
from D to A on an unmeasured signal is a gate decided by a model — which is
rule 2's line and rule 8's. So the honest first version is **B, not A**: a
smaller lift, still an 5.4× improvement on D, and it keeps "published harness,
N runs" as something a human confirms rather than something the extractor
asserts. At tier B a claim weighs ~0.24 and `n_eff` 3.0 needs ~13 voices —
demanding, reachable, and not a promise the extractor is making about itself.

## 6 · Why this outranks collecting more corpus

There are 1,505 unread threads and they cost about $2.14. **They cannot publish a
cell.** Not "probably will not" — the arithmetic in §3 does not depend on what
those threads say. Coverage would widen, the board would populate further, and
`PUBLISHED` would stay 0.

So the money is better spent after this is settled, and that is the
recommendation attached to it.
