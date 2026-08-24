# For Engineer 2 — `claim.subject_inherited`, and what an inherited subject may do

**Three of the four claims in the table quote text naming no model, and all four
record `specificity=version`. `claim` has no `surface` column, so the string that
justified `version` is not in the row and cannot be recovered from it.** Those
rows assert a precision their quotes do not have, and they are rows already
rendered.

The check is built and derived in code. **The column and the ruling are not, and
they go together**, because what an inherited subject may do runs into
`max_thread_share` and neither is one lane's call.

*Engineer 1 · 2026-08-21 · `docs/measurements/the-limit-in-the-description.md` §3*

---

## 1 · What is built

```python
# judge/pipeline.py
def subject_was_inherited(quote, *, model_version_id, find_surfaces) -> bool | None:
    if find_surfaces is None:
        return None          # nobody checked
    if model_version_id is None:
        return None          # no subject to inherit
    return not bool(find_surfaces(quote))
```

**Derived, never asked of the model.** A field the extractor filled could assert
`false` about a quote naming nothing and nothing would catch it — the same shape
as asking for a canonical id instead of resolving one. Here the model proposes
the attribution and code checks whether the quote supports it, which is quote
verification's own argument applied to the subject.

Run against the table:

```
inherited=False  spec=version   "So when Fable's classifiers detect a request…"   13 surfaces
inherited=True   spec=version   "We'll keep refining the safeguards…"              0
inherited=True   spec=version   "exceptional performance in software engineering"  0
inherited=True   spec=version   "gives 10%+ better results on SWE-Bench"           0
```

`None` rather than `False` when unchecked, because *"nobody checked"* and
*"checked, and the quote names a model"* are different facts (rule 6).

**`SurfaceFinder` is a second Protocol, injected like `SurfaceResolver`.**
`judge/` may not import `collect/`, and the answer depends on the surface
population, which changes nightly. A copy in this lane would be a second
population with its own fingerprint, and a verdict is only reproducible against
the one it was computed with. `collect.surface_resolver.RegistrySurfaceFinder`
supplies it; five tests cover it.

Computed and logged today, counted on `PipelineResult.subjects_inherited`.
**Nothing is stored**, because that needs the column below.

---

## 2 · The column

```sql
ALTER TABLE claim
  ADD COLUMN subject_inherited boolean;   -- NULL = nobody checked
```

Three properties worth agreeing explicitly:

**Nullable, and NULL means unchecked rather than false.** The four existing rows
would be NULL, not back-filled — the check needs the population the claim was
resolved against, and re-deriving it today against a different fingerprint would
record a verdict from the wrong population. That is the mistake
`SurfacePopulation.fingerprint` exists to prevent.

**Derived, so it cannot disagree with the quote.** Unlike `specificity`, which is
the extractor's account of a surface the row does not store, this one is
recomputable from `claim.quote` and a population at any time. If the two ever
disagree, the derived one is right.

**And it makes `specificity` auditable for the first time.** Today
`specificity=version` on a quote naming nothing is unfalsifiable, because the
surface is gone. With `subject_inherited` beside it, the pair says what happened:
*version-specific subject, taken from elsewhere in the document.*

### The sharper question underneath: should `surface` be stored too?

I am not proposing it, and it is worth naming. `ModelRef.surface` is *"exactly as
the human wrote it"* and is discarded at storage. So the row records a
`specificity` derived from a string nobody kept. Storing the surface would make
`specificity` checkable directly rather than inferable from a boolean — a
one-column change, and a bigger conversation about what `claim` is for. Your
table.

---

## 3 · The ruling, which is the part that is not ours alone

**What may an inherited subject do?** Four questions, in the order they bite.

### (a) May it be stored at all — yes, and for the `speaking` reason

Refusing storage means a claim the check marks wrong disappears with no record,
and the check has never run against a labelled set. Store it, mark it, revisit.
Same argument as `speaking`, and I would keep them consistent.

### (b) May it count as an independent voice — this is `max_thread_share`

**This is the one that matters and it is not about weighting.** Measured on the
one Reddit thread we hold in full: a root announcing a model, and **80 distinct
authors** among the comments that survive triage. Every comment saying *"it's much
faster"* inherits that subject.

`gate.count` dedups by `voice_id` and reads neither `speaking` nor `specificity`,
so it would read neither `subject_inherited`. **80 inherited claims from one act
of naming would be 80 independent voices**, against `WIDELY_PRAISED_VOICES = 5`.
`max_author_share` cannot see it because the authors really are different people.

Two shapes, and I prefer the second:

```
1. subject_inherited claims do not count toward independent_voices
   Simple, and wrong at the edges: "it's much faster" about a model the root
   named IS a person's own observation. Discarding the voice discards real
   evidence for a bookkeeping reason.

2. max_thread_share on CellCounts, capped as max_author_share is
   One thread cannot supply a cell's voices, whether the subject was inherited
   or stated. It bounds the actual failure - concentration - rather than
   proxying it through inheritance.
```

(2) is also needed **whether or not `subject_inherited` is ever stored**, because
inherited claims already exist: 3 of the 4 rows. And the only thing bounding it
today is an accident — the thread selector keeps 2.7% of observed children.

**Please do not widen thread assembly before it exists.**

### (c) May it lift a cell to published — I would say not alone

An inherited subject is a real claim about a real model and weaker evidence than
a stated one, in the same sense a family-specificity claim is. It should not be
the marginal claim. That is a `contract/` rule rather than a weight, and it is the
same shape as the family-specificity ask that is still open.

### (d) Does it interact with `speaking` — no, and that is worth stating

They are orthogonal. *"Introducing Claude Fable 5"* is `vendor-about-own-product`
and snapshot-specific; a comment inheriting it is `own-experience` and inherited.
A field that folded them would be the `ResolutionReport.ambiguous` mistake again —
one name for two facts.

---

## 4 · One thing I broke that needs your migration to land

`judge/store/claims.py` now inserts `speaking`, and **the column does not exist on
staging** — `contract/migrations/20260821T1600_claim_speaking.sql` is written and
awaiting your sign-off.

So the storage path is currently broken: the next real pipeline run fails on
insert. It is not exercised by anything today (the `test_dsn` suite does not run
here and nothing calls `run_all` in production), and I would rather flag it than
guard it, because a guard would let the pipeline run without recording
`speaking`, which is the thing the field exists for.

**Two migrations pending, both flagged, both yours:** `claim.speaking` and — if
you take §2 — `claim.subject_inherited`.

---

## 5 · Suite

**1,959 passed.** New tests: five on the finder and the derivation, including one
asserting on the source that the model is never asked —

```python
assert "subject_inherited" not in ModelRef.model_fields
assert "find_surfaces(quote)" in inspect.getsource(subject_was_inherited)
```

— because a field the extractor fills is the tempting fix and it is the wrong one.
