# The double count is 1.95× of 10.59×, and removing it costs `f_specificity` its last live signal

**Recommendation: Option 1 — drop `has_numbers` and `has_repro_steps` from
`specificity_factor()`.** It is the smaller change by every measure that matters
and it removes the double count exactly. What it costs is that the factor it
leaves behind is a two-valued duplicate of `f_fuzziness` on this corpus, which
is not a new defect — it is one this repo already recorded and declined to fix,
now with nothing left in front of it.

*Engineer 1 · 2026-08-30. E2 delegated the tier decision and explicitly not this
one, so this is a proposal and no code has been changed.*

---

## 1 · What the double count actually is

`specificity_factor()` and `evidence_tier_rules` now read the same two booleans.

```
specificity_factor = 0.3 + 0.7 · (0.2·version_named + 0.2·has_numbers
                                  + 0.2·has_conditions + 0.4·has_repro_steps)

  version only                   0.44
  version + numbers              0.58
  version + repro                0.72
  version + numbers + repro      0.86      1.9545×

  tier D -> B                              5.4167×
  combined on one claim                   10.5871×
```

So a first-hand claim carrying repro steps and numbers is worth **10.59× a bare
opinion**, of which **1.95× is the same two facts priced a second time**. The old
contract block used this as its argument against promoting at all, and your
ruling overrides the conclusion rather than the objection — which is why it is
still here.

## 2 · Option 1 — drop the two signals from `specificity_factor`

```python
score = 0.0
if version_named:
    score += 0.2
if has_conditions:
    score += 0.2
return 0.3 + 0.7 * score
```

**Cost, measured on the formula:**

```
new range                    0.30 .. 0.58     (was 0.30 .. 1.00)
combined lift                5.4167×          the tier alone. Exactly right.
values reachable on THIS corpus              {0.30, 0.44}
```

That last line is the real cost and it is not small. `document.has_conditions`
is **False on all 7 populated rows and NULL on 57**, so the only signal left
alive in the factor is `version_named` — and `version_named` is a fact
`f_fuzziness` already prices at 1.0 / 0.6 / 0.3.

**Which means Option 1 does not create a duplicate, it exposes one.** The
pipeline's own docstring recorded it before any of this:

> *"`f_specificity` now gives +0.2 for a fact `f_fuzziness` already prices at
> 1.0/0.6/0.3, so one fact is priced twice … The clean version is to drop
> `version_named` from `specificity_factor` entirely."*

Take Option 1 and `f_specificity` becomes a two-valued restatement of
`f_fuzziness`. The honest end of that road is **six factors, not seven** —
retire `f_specificity` and let `f_fuzziness` price attribution, the tier price
checkability, and nothing price either twice. I am not proposing that here
because it is a third ruling; I am naming it because Option 1 walks most of the
way there and somebody should decide whether to stop halfway on purpose.

## 3 · Option 2 — cap the combined lift

Clamp `f_evidence · f_specificity` so a claim carrying both signals gains 5.42×
rather than 10.59×.

**It is the larger change, and the reason is structural rather than the
line count.** Seven factors multiplied, each stored in its own column, is the
audit feature:

> *"why does this page say that?" must be answerable with a table of
> contributing claims and their itemised weights.*

A clamp breaks that. `w_final` stops being the product of the seven stored
numbers, so the drill-down shows seven factors that do not multiply to the
answer — and the reader who checks is the reader this board is for. Fixing that
means storing the clamp as an eighth column, at which point it is a bigger
change than Option 1 and has invented a number besides.

It also **preserves the pricing error while hiding its size.** The two signals
still enter twice; the clamp just stops the total from showing it. Option 1
removes the double count; Option 2 caps its consequence.

## 4 · The comparison, stated plainly

| | Option 1 — drop from `f_specificity` | Option 2 — cap the combined lift |
|---|---|---|
| removes the double count | **yes, exactly** | no — hides its size |
| combined lift | 5.4167×, the tier alone | 5.4167× by clamping |
| code | delete two branches | new clamp + a new stored column to keep the audit honest |
| itemisation still multiplies to `w_final` | **yes** | no |
| new number invented | none | the cap |
| what it costs | `f_specificity` becomes `{0.30, 0.44}` on this corpus and duplicates `f_fuzziness` | the drill-down stops reconciling |

**Option 1 is the smaller change.** It is fewer lines, it invents nothing, it
keeps the property the drill-down depends on, and it removes the double count
rather than capping it.

## 5 · What I would want you to decide, and it is three things not one

1. **Option 1 or Option 2.** My recommendation is Option 1.
2. **If Option 1: stop at two signals, or retire `f_specificity` entirely?**
   Stopping leaves a factor that duplicates `f_fuzziness` and reaches two values.
   Retiring is a bigger edit and leaves six factors that each price one thing.
3. **Whether either lands before or after the two re-weights.** They are
   separate rulings and each deserves its own `pipeline_version`, or the diffs
   stop measuring anything — which is the mistake this fortnight has now
   avoided twice and should not make on the third.

## 6 · One thing that is NOT a reason to hurry

The double count only bites a claim carrying both booleans, and **on every
population we can currently read, that is zero claims.** `has_repro_steps` is
False on all 186 claims across the three persisted blog runs, and the stored 197
were extracted by the same prompt. So this is very likely a defect with an empty
blast radius today and a growing one as GitHub coverage lands — which argues for
deciding it deliberately rather than quickly, and for measuring the real
population first. `judge reweight --from-version e5.1 --document-facts frozen`
prints the count directly, as `B` in its tier-moves table.
