# The re-weight stopped at step 2, and the tier ruling moves nothing

**Zero promotions on 197 claims.** `claim.has_repro_steps` is `False` on all 197
and `document.has_numbers` is NULL on 194 of them, so the ladder's two rungs are
unreachable and every claim stays where it was: D→D 154, E→E 29, F→F 11.

**And the drift check fired before that number could be trusted.** `f_launch`
moved on 96 claims and `f_specificity` on 16, so the run is not attributable to
the tier ruling and **nothing was applied**. The chain ran inside one transaction
and was rolled back; staging holds the same 197 claims at `e5.1` and the same 94
cells it held before.

*Engineer 1 · 2026-08-31, the morning staging came back.*

---

## 0 · The two pre-checks

**Nothing changed while the host was down.** 197 claims, all at `e5.1`; 94 cells,
all `insufficient`; 197 `claim_weight` rows; newest claim 2026-08-29 13:03 UTC.

**The stale baseline was refused before step 0 could overwrite it.**
`report_rollup_delta.py` printed the refusal and its reason, then fell back to
absolute figures — and its new version filter reported `0` claims at `e5.4`,
correctly, because no fork existed yet. The stale file was copied aside first so
the refusal could be demonstrated rather than described.

## 1 · The document-facts gap cost the whole board and bought nothing

```
population: 197 claims at e5.1 - the corpus, not a sample

would REFUSE (a NULL column is not a False)   194   98.5%
    NULL in has_numbers + has_conditions      194
    by platform      reddit 157   blog 20   github 17
f_specificity MOVES                             0    0.0%
columns present and genuinely False             3    1.5%
```

**`collect/triage/` has written those columns on 7 of 2980 documents.** So the
repaired `None` check — which is correct, and which I would not revert — turns
98.5% of the corpus into refused claims and moves not one weight. Step 3 confirms
it exactly: **194 read, 0 written, all 94 cells gone.**

That is the answer to *what did the gap cost*: **everything, and it buys
nothing**, because the columns the check now demands are not written. The repair
belongs in the other lane — `collect/triage/specificity.py` computes both and
nothing calls it — and until it lands, `--document-facts read` is a migration
that deletes the board.

**A correction to something I asserted twice.** I said *"every claim in the table
was weighted as though both were False."* It is **194 of 197**. Three rows carry
`document.has_numbers = True` and were weighted with it — `f_specificity` 0.58,
not 0.44. Those same three are the only rows with `speaking` NULL, so they are
also the three the tier ruling refuses. The corpus offers exactly zero claims
where the document facts are present *and* the ladder can act.

## 2 · The tier ruling, measured, moves zero claims

```
197 read   194 written   3 refused (speaking NULL)

tier moves      D->D 154    E->E 29    F->F 11
promotions           0
```

**Why, and both halves are measured:**

```
claim.has_repro_steps    False on 197 of 197      no claim in the corpus has any
claim.has_numbers        True on 20
document.has_numbers     NULL on 194 of 197       so the falsifier cannot confirm
                                                  and the numbers rung is withheld
```

The B rung needs both signals; the C rung needs one. `has_repro_steps` supplies
neither because it is false everywhere, and `has_numbers` is withheld on all but
three claims — which are refused for a different reason. **The ladder is
correct and the corpus cannot reach it.**

This is what the blog-run population predicted: `has_repro_steps` was False on
all 186 claims across three persisted runs, and I wrote that if the stored 197
resembled it the lift would be near zero. It does, and it is exactly zero.

## 3 · What publishes: nothing, and the closest cell is short on tier

```
cells 94    publishing 0    cells with >= 2 platforms 12

closest three                                   n_eff before -> after  voices  platforms
anthropic/claude-opus-4.6  code.generation           0.0941 -> 0.0900       6          2
anthropic/claude-sonnet-5  reasoning.multistep       0.1409 -> 0.0777       7          2
anthropic/claude-opus-4.6  instruction.adherence     0.0730 -> 0.0721       4          1
```

**The closest cell already has its second platform.** `claude-opus-4.6 ·
code.generation` clears `PLATFORM_MINIMUM` with 6 voices across 2 platforms and
fails on weight alone: 0.0900 against 3.0. At its own per-voice weight of 0.0150
it needs roughly **200 voices**.

So the answer to *more voices, a second platform, or a tier the ladder cannot
emit* is the third. It is not short of people and it is not short of platforms.
It is short of a tier, and the tier it needs is one the ladder cannot produce
from this corpus — not because the ladder is capped at B, but because both
signals the ladder reads are dead in the data.

⚠ **`n_eff` went DOWN, not up.** `claude-sonnet-5 · reasoning.multistep` falls
from 0.1409 to 0.0777. No claim was demoted — the drop is the two corrections in
§4 arriving with the re-weight, which is exactly why the drift check refuses the
run.

## 4 · What the drift check caught, and it is two more of the same defect

### `f_launch` has never been applied to 194 of 197 claims

```
stored f_launch, distinct values     1.0 on 194     0.45 on 3
recomputed from the registry         1.0 on  98     0.45-0.92 on 99
model_version.release_date           non-NULL on 342 of 342
```

The formula is continuous — `0.45 + 0.55 · min(1, days/21)` — and the stored
column takes **two values**. Every model carries a release date, so a stored 1.0
means the original run passed `release_date=None`: `judge/pipeline.py` reads
`(release_dates or {}).get(...)` and the caller supplied nothing.

**The launch-window discount, which `weight.py` calls "computed once, at
extraction, and frozen", was frozen at 'no discount'.** Half the corpus is
over-weighted, and the correction halves some claims — 1.0 → 0.5024 is typical.

**23 claims are dated on or before their model's release date**, which floors
them at 0.45 and is the population E6's `predates_model` trigger exists for.
Worth a look on its own terms.

### `f_specificity` on 16 claims does not follow from its own stored inputs

```
stored 0.72   claim.specificity=version   has_repro_steps=False    n=9
stored 0.58   claim.specificity=version   document.has_numbers=NULL n=5
stored 0.44   claim.specificity=family                             n=2
```

0.72 requires `has_repro_steps=True`; the column says False. 0.44 requires
`version_named=True`; `family` gives False. **These weights are not a function
of the inputs stored beside them**, so for those rows a re-weight cannot
reproduce the before-state at all — which is the assumption the whole
`--document-facts frozen` mechanism rests on.

Sixteen of 194 is small and the implication is not: a stored weight that cannot
be recomputed from its stored inputs is a number with no derivation, and the
drill-down renders it as though it had one.

## 5 · Why I did not apply

The stop condition was *"empty drift at step 2"*, and drift was
`{f_launch: 96, f_specificity: 16}`. Applying would have committed a fork whose
diff carries three causes — the tier ruling, the launch discount arriving for the
first time, and 16 unreproducible rows — and the tier ruling's contribution to
that fork is **zero**, so the entire visible movement would have been
misattributed to it.

`judge/writeguard.py` would also have refused: `ENVIRONMENT=development` pointed
at a remote database is the pairing it exists to stop, and applying is a
coordinated staging write session under `CLAUDE.md`'s conventions rather than
something a measurement does on the way past.

## 6 · The quieter board, per cell

Two cells lost evidence at step 2, both from the three refused claims. Neither
lost a platform.

```
anthropic/claude-fable-5  code.generation  context_size:unknown  voices 7->5  platforms 1->1
anthropic/claude-fable-5  over_refusal     context_size:unknown  voices 2->1  platforms 1->1
```

At step 3 the count is **94 of 94** — every cell on the board, because every
claim is refused. That is not a quieter board, it is an empty one.

## 7 · What next, and the order has changed

The tier ruling is landed, correct, and **worth nothing until the extractor
produces a claim with a repro step or a document with counted numbers**. Three
things now sit in front of it, and none is the re-weight.

1. **Write `document.has_numbers` and `has_conditions`.** 7 of 2980. It is the
   prerequisite for the `None` repair, for the numbers rung, and for
   `f_specificity` meaning anything. `collect/triage/specificity.py` already
   computes them.
2. **Rule on `f_launch`.** It needs its own `pipeline_version` and its own diff —
   it is a third ruling, not a passenger on the tier's. It is also the only one
   of the three that changes weights *today*, on 99 claims.
3. **Ask why `has_repro_steps` is False on 197 of 197.** A field that is never
   true is either measuring nothing or being asked wrongly, and it is half of
   the ladder E2 delegated. Round 3 of the golden set is where that is settled.

The 16 unreproducible rows want an owner too, though they are the smallest of
the four.
