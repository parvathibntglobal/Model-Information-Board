# The publication gate is uncalibrated — a ruling, not more measurement

**Status:** proposal for a joint ruling. Measured twice, independently (E1 and
Parvathi), same arithmetic. This is the single thing standing between the board
and anything publishing.

---

## The gap, in one line

`n_eff` must reach **3.0** to publish. Real forum claims weigh **~0.015**. The
gate's own docstring assumes weights near the **0.95** cap. Those are **30–60×
apart**, and no amount of collection closes it.

## What the numbers actually are

Measured on staging (199 claims, 96 cells, all `insufficient`):

- **Highest cell:** sonnet-5 · `reasoning.multistep` — **7 voices, 2 platforms**,
  n_eff **0.1409**. Genuinely well-corroborated, and nowhere near 3.0.
- Per-voice weight there: **~0.020**.
- At 0.015/claim, a cell needs **~200 distinct voices** to publish. The best has 7.

**Independently corroborated by E1's committed multi-platform run** (PR #193,
`feat/model-only-sweep-and-classification`): 197 claims across three platforms,
94 cells, **0 published**, and the same top cell to the decimal — sonnet-5 ·
`reasoning.multistep` · n_eff **0.1409** · 7 voices · 2 platforms. Two people,
two corpora, one number.

**Platform is no longer the binding constraint — weight is, alone.** E1's run
lifted 12 cells to two platforms (up from 1), so `PLATFORM_MINIMUM = 2` is now
met where it matters and **all 94 cells still fail on weight**. The earlier
"84 of 96 single-platform" framing is stale; the single blocker is the weight
scale.

## Why it's the AGGREGATION, not the tier

The weight is a **product of seven factors, each ≤ 1**:

| factor | staged avg | note |
|---|---|---|
| `f_evidence` (tier) | **0.10** | all D/E/F (A=1.00, D=0.12, F=0.02) — fixable; code-count the tier signals (`judge/vet/repro.py`) |
| `f_specificity` | **0.43** | claim detail: numbers, conditions, repro, version named |
| `f_fuzziness` | 0.53 | model-version specificity — snapshot 1.0 / version 0.6 / family 0.3 |
| `f_recency` | 0.74 | age |
| `f_platform` | 0.86 | trust weight — github .95 / blog .90 / reddit .85 |
| `f_relevance` | 0.95 | central vs passing |
| `f_launch` | 0.99 | launch-window discount |
| **`w_final`** | **~0.020 / voice** | the product, in the top cell |

**Walk the fixes up the ladder, on the top cell** (sonnet-5 · `reasoning.multistep`,
7 voices; n_eff must reach 3.0):

| what you change | per-voice w | n_eff | publishes? |
|---|---|---|---|
| nothing (today) | 0.020 | **0.14** | no |
| tier D→A, still a product | ~0.17 | ~1.2 | no |
| + remove the version double-count | ~0.32 | **~2.2–2.6** | no |
| **geometric mean** `(∏f)^(1/7)` | ~0.57 | **~4.0** | **yes** |
| geometric mean + tier D→A | ~0.77 | ~5.4 | yes |

**Every fix that keeps the multiplicative form tops out at ~2.6** for the
best-corroborated cell in the entire dataset — still short of 3.0. Only changing
the *form* of the aggregation, or lowering the bar, crosses it. That one row —
**seven genuine voices at ~2.6** — is the finding: the gap survives every fix on
the table except the two that change what "3.0" is measured against.

**And the two tier-fix rungs may not even be reachable.** E1's PR reports *"tier
A is unreachable by construction"* (commit `e04115e`) — the speaking-role
classification that sets the tier can't award A to the evidence this board
actually collects. If that holds, the top two rows of the ladder are struck out,
and the *only* remaining levers are the aggregation form and the bar. E1's PR
opens arguing GitHub's tier-A channel is the fix and closes conceding the tier
can't be reached — which is the same place this doc starts. The two analyses
converged on the aggregation.

### Why the multiplicative form, first

The product is not a mistake, and it deserves to be argued against on its merits
rather than discarded. Multiplying independent filters is the correct way to say
"all of these must hold" — if each factor prices a genuinely separate reason to
trust a claim less, the product is right and the collapse to ~0.02 is the honest
verdict on hedged, single-platform, month-old forum prose. On that reading the
fix is to lower the bar, not to touch the form.

The form breaks only where the factors are **not** independent, and two are not.
`f_specificity` already prices whether the model version was named
(`version_named`), and `f_fuzziness` prices *nothing else* — it is entirely
snapshot/version/family. Version-pinning is multiplied in twice. That is the
**same double-count shape as the tier signals, one level up**: the evidence tier
already prices "has numbers / has a repro", and `f_specificity` prices
`has_numbers` and `has_repro_steps` *again*. One honest signal, two
multiplications — and each duplicate is a second sub-1 haircut for a fact already
charged once.

So the ruling is two questions, not one: **is the product the right form**
(independence), and **is the bar in the right place** (calibration). Removing the
double-counts is uncontroversial either way — a bug on any reading. The geometric
mean is the larger claim, and it is the one that actually publishes today's best
cell without moving the bar.

## The three options, with arithmetic

**A — Lower the `n_eff` threshold.**
To publish the 7-voice cell as-is needs a bar of ~0.14; with the tier fixed,
~1.2. Cheapest change, one constant. But 1.2 is an arbitrary number chosen to
clear the cells we happen to have, and it treats the symptom: the *reason*
nothing reaches 3.0 is untouched, so the next recalibration is the same argument.

**B — Fix the aggregation (recommended core).**
The product-of-fractions is the actual defect. Two ways, not exclusive:
- **Geometric mean of the factors** instead of the product: `w = (∏f)^(1/7)`.
  For the top voice (product ~0.020) that is **~0.57**, so 7 voices → n_eff
  **~4.0 → publishes**, with no threshold change. Each factor keeps proportional
  influence without the multiplicative collapse. **Knock-on to price in:** the
  per-claim ceiling rises from 0.95 (today's `MAX_POSSIBLE_WEIGHT`) toward 1.0,
  so `n_eff ≥ 3` stops implying "≥ 4 claims" — the equivalence the gate docstring
  and the dropped `voices ≥ 3` rule lean on. The bar must be re-read against the
  new scale, which is decision 2 below, not a surprise.
- **Remove the double-count:** version-pinning is priced twice —
  `f_specificity` includes `version_named`, and `f_fuzziness` is *entirely*
  model-version specificity (snapshot/version/family). Arguably the same shape as
  the evidence tier's own gloss ("has numbers / has a repro") overlapping
  `f_specificity`'s `has_numbers` and `has_repro_steps`. One fact, two haircuts — a bug independent of the form
  question.

**C — Both:** fix `has_repro_steps` (so the tier is real and rule-2-clean),
*and* fix the aggregation, *and* set the bar deliberately against the new scale.

## Recommendation

**B, then set the bar** — the aggregation is the real defect; lowering the
threshold alone (A) is treating the symptom and guarantees this conversation
again. Concretely:

1. Code-count `has_repro_steps` (`judge/vet/repro.py`, built) so `f_evidence` is
   real — rule-2-clean, $0, no re-extraction. E1's note: E6 vet has never run for
   the same `DocumentFacts.text` wire this needs, so the fix closes two dead
   mechanisms at once.
2. Change the aggregation from a bare product (geometric mean, or drop the
   specificity/fuzziness double-count) so an honest, well-corroborated cell lands
   in a range the bar can sit above.
3. Then **set `N_EFF_MINIMUM` deliberately** against the new weight scale — a
   number chosen because it means "N corroborating first-hand voices across ≥2
   platforms," not because it clears today's data.

What this is NOT: spending $4.70 on the remaining 1,510 Reddit threads. That buys
~2,000 more tier-D claims spread across MORE cells, not deeper ones — it does not
close 30×. The decision is calibration, and it wants ruling, not measuring.

## The decision we need from the team

1. Aggregation: **geometric mean**, **de-double-count**, or **leave as product**?
2. Threshold: what does `N_EFF_MINIMUM` mean in voices, once the scale is fixed?
3. `has_repro_steps`: code-count (recommended) or re-extract?

None of these is reversible-by-accident, and all three are config in
`judge/curate/gate.py` and `contract/`, so each lands as a small change once ruled.
