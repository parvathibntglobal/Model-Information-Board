# Option 1 is taken, it removed 1.95× of 10.59×, and it cost the gate two voices

**Two questions, in one document, because the first exposes the second and
ruling on it alone means ruling blind.** Option 1 is implemented on E1's
instruction — `has_numbers` and `has_repro_steps` no longer reach
`specificity_factor()`. What that leaves is a factor with two signals, one of
which is dead on this corpus and the other of which `f_fuzziness` already
prices. So the real question was never "Option 1 or Option 2". It is **two
signals or six factors**, and both halves are below.

*Engineer 1 · 2026-08-30. Option 1 taken; the second question is E2's and
nothing has been done about it.*

---

## 1 · What the double count was, and that it is gone

`specificity_factor()` and `evidence_tier_rules` read the same two booleans.

```
BEFORE
  f_specificity   version only                0.44
                  version + numbers + repro   0.86     1.9545×
  f_evidence      tier D -> B                          5.4167×
  combined on one claim                               10.5871×

AFTER (Option 1)
  f_specificity   version only                0.44
                  version + numbers + repro   0.44     1.0000×   <- gone
  combined on one claim                                5.4167×   <- the tier alone
```

Exactly the double count and nothing else. The old contract block's objection —
*"raising the tier on the same signals would price one fact twice"* — is
answered rather than capped.

**Option 2 was not taken and here is why, briefly.** Clamping
`f_evidence · f_specificity` would have left the two signals entering twice and
merely stopped the total showing it, and it breaks the property the drill-down
depends on: seven stored factors that multiply to `w_final`. Keeping that honest
needs an eighth column, which makes it the larger change as well as the weaker
one.

## 2 · What it cost, and this is the part the first draft of this proposal missed

`f_specificity` is a term in a product, so removing two of its four signals took
its **range** down with its weights — and that applies to every claim, not only
to the ones that carried the removed signals.

```
max f_specificity            1.00  ->  0.58        a 42% cut to the ceiling
MAX_POSSIBLE_WEIGHT          0.95  ->  0.551
claims needed for n_eff 3.0  3.16  ->  5.44        "four or more" is now "six or more"

and at the rung the ladder can actually reach (B, not A):
MAX_REACHABLE_WEIGHT               ->  0.358
voices needed on a realistic best claim   9.4  ->  18.4
```

**The publication gate now asks for roughly twice the voices, and nobody voted
for that.** Option 1 was argued as a fix to how one fact is priced; it moved
what the bar means. `curate/gate.py`'s *"n_eff >= 3.0 already demands four or
more claims"* is now false, and the constants are derived from the weights
rather than typed so this cannot go stale again.

**Nothing compensates for it and nothing should without a ruling.** Lowering
`N_EFF_MINIMUM` to restore the old effective bar would be a threshold change
dressed as bookkeeping, and the threshold is not mine to move. If you think the
bar should hold where it was, that is a third decision and it is yours.

## 3 · The good news, which is real: Option 1 closed a door I had left open

An announcement carries numbers by construction. Under the four-signal formula
those numbers lifted its `f_specificity` while it sat correctly at tier F — so a
vendor claim got **heavier** without being promoted, which is the second route
into the worry you raised and one the tier ladder's flat vendor rung does not
cover.

**Under Option 1 that route is gone.** `has_numbers` and `has_repro_steps` reach
only the tier, and the tier has no vendor rung, so an announcement's own figures
now buy it nothing anywhere. The fable-5 vendor claim gets *lighter* rather than
heavier. Tested both ways —
`test_under_the_legacy_formula_it_got_heavier_at_the_same_tier` and
`test_option_1_closes_that_route`.

**And it shrank the blast radius of the `None` repair.** A NULL
`document.has_numbers` used to refuse the claim, because `f_specificity` read
it. Now that column reaches only the tier falsifier, which *withholds a
promotion* rather than refusing — so the claim survives at the tier its other
signal earns. `compute()`'s refusal list follows `specificity_weights` for this
reason: refusing over an input the function no longer reads is a gate that has
stopped meaning anything and goes on dropping documents.

## 4 · The second question, and it is the one that matters now

**What is left of `f_specificity` is `version_named` and `has_conditions`.**

```
has_conditions   False on all 7 populated rows, NULL on 57.
                 collect/triage/ computes it; nothing writes the column.
version_named    priced by f_fuzziness ALREADY, at 1.0 / 0.6 / 0.3

values f_specificity can reach on this corpus:   {0.30, 0.44}
```

So the factor is now a **two-valued restatement of another factor**. That is not
a new defect — `judge/pipeline.py`'s own docstring recorded it before any of
this:

> *"`f_specificity` now gives +0.2 for a fact `f_fuzziness` already prices at
> 1.0/0.6/0.3, so one fact is priced twice … The clean version is to drop
> `version_named` from `specificity_factor` entirely."*

**This is a known thing arriving, not a discovery.** Option 1 did not create the
overlap; it removed the three live signals that were standing in front of it.

### The choice

| | **Stop at two signals** | **Retire `f_specificity`, run six factors** |
|---|---|---|
| what the factor measures | `version_named`, which `f_fuzziness` prices, plus a column nothing writes | — |
| values it reaches today | `{0.30, 0.44}` | — |
| double counts remaining | one: `version_named` against `f_fuzziness` | none |
| ceiling | 0.551 possible / 0.358 reachable | 0.95 / 0.6175 — the gate's arithmetic returns to "four or more" |
| stored columns | 7, one of which measures nothing | 6, each pricing one thing |
| cost | a factor that renders as a measurement and is not one | `claim_weight.f_specificity` becomes a dead column; the drill-down loses a row people may expect |
| honesty of the drill-down | seven numbers, one meaningless | six numbers, all live |

**Retiring it also undoes §2.** With `f_specificity` gone the product has no
sub-1.0 factor left, `MAX_POSSIBLE_WEIGHT` returns to 0.95, and the gate means
what `curate/gate.py` says it means. That is a real argument and I want to be
careful about it: *"it fixes the number I broke"* is a good reason and a
dangerous one, because it would also be satisfied by putting the two signals
back. The difference is that retiring removes a double count and restoring
re-creates one.

**What I would argue for, and it is yours:** retire it. Seven factors where one
is a restatement is worse than six, and the drill-down is the product's
credibility surface — a reader who checks and finds a factor that never varies
learns something about the whole table.

**What I am not doing without your ruling:** touching it. Option 1 was
instructed; this is not.

## 5 · Two smaller things attached to the same decision

**Rule 5 says these weights belong in `contract/`, and they never have been.**
`specificity_factor`'s numbers live in `judge/vet/weight.py`. That was already
true of the four; it is still true of the two. If the factor survives question
4, the weights should move to the contract with the rest of the thresholds. If
it does not, the question dissolves. Worth noting rather than fixing, because
moving them is a contract change and this document is the wrong instrument.

**A third `pipeline_version` exists because of this.** Taking Option 1 changes
`f_specificity` on stored rows, which is its own ruling and its own diff:
`e5.3 -> e5.4`, `judge reweight --specificity current`. The `legacy` four-signal
form is kept in `weight.py` solely so a re-weight can reproduce the BEFORE side
of a version that predates Option 1 — a diff against a formula that never
applied is a diff about nothing.

## 6 · What is NOT a reason to hurry, unchanged from the first draft

On every population currently readable, **no claim carries both booleans**:
`has_repro_steps` is False on all 186 claims across the three persisted blog
runs, and the stored 197 came from the same prompt. So the double count Option 1
removed had an empty blast radius today — while the ceiling change in §2 hits
**every claim in the corpus**. That asymmetry is worth sitting with before
ruling on question 4, and the numbers to sit with arrive from steps 2 to 4 of
the run order in
`docs/measurements/the-tier-rekey-and-the-ceiling-it-does-not-reach.md`.
