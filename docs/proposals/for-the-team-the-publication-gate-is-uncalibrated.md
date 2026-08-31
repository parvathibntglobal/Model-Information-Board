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

Platform is **not** the binding constraint for the cells that matter: the top two
(6 and 7 voices) both clear the ≥2-platform rule and fail on weight alone. (It is
a real problem for 84 of 96 single-platform cells — a separate one.)

## Why it's the AGGREGATION, not the tier

The weight is a **product of seven factors, each < 1**:

| factor | avg | note |
|---|---|---|
| `f_evidence` (tier) | **0.10** | all D/E/F — fixable (see the has_repro_steps proposal) |
| `f_specificity` | **0.43** | honest: forum claims are vague |
| `f_fuzziness` | 0.53 | honest: forum claims hedge |
| `f_recency` | 0.74 | age |
| `f_platform` | 0.86 | trust weight |
| `f_relevance` | 0.95 | ~no cut |
| `f_launch` | 0.99 | ~no cut |
| **`w_final`** | **0.015** | the product |

Fixing the tier (D→A) multiplies ONE factor by ~5–8×. Applied to the 7-voice
cell that is n_eff **0.85** — still under 3.0. The residual is `f_specificity`
(0.43) × `f_fuzziness` (0.53) × `f_recency` (0.74), and **those values are
correct** for hedged forum prose. So the gap is not a bug in any one factor. **A
product of seven independent fractions is mathematically guaranteed to be tiny**,
and the 3.0 bar was set against a 0.95 ceiling only the ideal claim reaches.

## The three options, with arithmetic

**A — Lower the `n_eff` threshold.**
To publish the 7-voice cell as-is needs a bar of ~0.14; with the tier fixed,
~0.85. Cheapest change, one constant. But 0.85 is an arbitrary number chosen to
clear the cells we happen to have, and it treats the symptom: the *reason*
nothing reaches 3.0 is untouched, so the next recalibration is the same argument.

**B — Fix the aggregation (recommended core).**
The product-of-fractions is the actual defect. Two ways, not exclusive:
- **Geometric mean of the factors** instead of the product: `w = (f1·…·f7)^(1/7)`.
  For the top claim (product 0.045) that is **~0.64**, so 7 voices → n_eff **~4.5
  → publishes**, with no threshold change. Each factor keeps proportional
  influence without the multiplicative collapse.
- **Remove the double-count:** `f_specificity` and `f_fuzziness` both penalise
  vagueness — `docs/measurements/f-specificity-double-counting.txt` already flags
  it. One fact priced twice.

**C — Both:** fix `has_repro_steps` (so the tier is real and rule-2-clean),
*and* fix the aggregation, *and* set the bar deliberately against the new scale.

## Recommendation

**B, then set the bar** — the aggregation is the real defect; lowering the
threshold alone (A) is treating the symptom and guarantees this conversation
again. Concretely:

1. Fix `has_repro_steps` (its own proposal) so `f_evidence` is real — rule-2-clean
   (code-counted), $0, no re-extraction.
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
