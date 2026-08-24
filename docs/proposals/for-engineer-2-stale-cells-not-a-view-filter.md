# `cell_current` after a version bump — the hazard is real and it is not the view

**Concretely: old rows are REPLACED, not shadowed and not returned alongside. The
residual hazard is a stale row nobody deletes, and it is inert today because
`cell_current` returns 0 rows.**

**Safe to leave for one cycle. The fix is not a view filter.**

*Engineer 1 · 2026-08-21 · reads only, `judge/` unmodified*

---

## What happens on the first rollup after the bump

Three facts settle it, and the second is the one that changes the answer:

```sql
-- contract/tables.sql:648   no pipeline_version filter, correctly
CREATE VIEW cell_current AS
  SELECT * FROM cell WHERE status IN ('published', 'contested');

-- contract/tables.sql:642   pipeline_version is NOT in the key
PRIMARY KEY (model_version_id, capability_key, condition_bucket)

-- judge/store/cells.py:208  so a re-run upserts rather than inserting
ON CONFLICT (model_version_id, capability_key, condition_bucket) DO UPDATE SET …
```

**Two rows for one cell key cannot exist.** So on the first rollup after a
`PIPELINE_VERSION` bump:

| the new rollup… | what happens to the old row |
|---|---|
| **produces that cell key** | **REPLACED in place.** `pipeline_version` is overwritten with the new value. Not shadowed, not duplicated, nothing to disambiguate |
| **does not produce it** | **survives unchanged**, at the old version, and `cell_current` will serve it if its status qualifies |

So the hazard is a **stale row**, not a version collision. And the reason a key
stops being produced is ordinary: its claims stopped resolving, the capability
moved, the surface fix refused a claim that used to resolve. All of which the
resolver guard makes *more* likely, not less.

## Why it is safe to leave for one cycle

```
cell rows          4
cell by status     insufficient 4
cell_current rows  0
```

**`cell_current` filters `status IN ('published','contested')`, and every cell on
the board is `insufficient`.** The view returns nothing, so a stale row cannot be
surfaced by it however long it sits there.

**The precise condition on which that stops being true**, so it is not a
standing assumption: the hazard goes live the first time a cell reaches
`published` or `contested` **and** a later rollup stops producing that key. Both
have to happen. Neither has happened once.

At `N_EFF_MINIMUM = 3.0` against a per-voice weight of ~0.012, nothing is close
to `published`. So one cycle is safe, and the thing to watch is the first
published cell rather than the version stamp.

## The fix is not a view filter

A `WHERE pipeline_version = …` clause would need the view to know the current
version, which a static view cannot express without a parameter — and it would be
solving the wrong problem, because **there is only ever one row per key.** The
view is right to be version-agnostic.

**The gap is that nothing deletes a cell whose claims are gone:**

```python
# judge/store/cells.py:263
for key in self.keys_with_claims():   # reads `claim`
    self.write(outcome)               # upserts
```

`keys_with_claims()` enumerates keys **from `claim`**, so a cell whose claims no
longer exist is never visited and never rewritten. `rebuild_all` has no delete.

I hit exactly this by hand on 2026-08-21: deleting six claims left three cells
rendering `insufficient` with `quote_ids` pointing at deleted rows, and I removed
them with

```sql
DELETE FROM cell ce WHERE NOT EXISTS (
  SELECT 1 FROM claim cl WHERE cl.model_version_id = ce.model_version_id
    AND cl.capability_key = ce.capability_key
    AND cl.condition_bucket = ce.condition_bucket);
```

**Proposed: that becomes a step in `rebuild_all`** — reconcile rather than
upsert-only, so the cell table cannot outlive the claims it was computed from.
One statement, `judge/` lane, no contract change, and it closes the version
hazard as a side effect rather than needing to name a version at all.

Two things I would want your call on:

1. **whether a delete or a status transition.** Deleting loses the fact that a
   cell once said something; writing it to `insufficient` with zero voices keeps
   a trace and keeps the row auditable. The changelog page may prefer the second.
2. **whether `rebuild_all` is the right home**, or whether reconciliation belongs
   in the nightly chain beside it, so a partial rollup cannot delete cells whose
   claims simply were not re-extracted that night. That distinction matters: "no
   claims" and "not re-extracted tonight" are different states, and the delete
   above cannot tell them apart.

That second point is the one that would bite. A nightly run over a subset of
threads would, with a naive reconcile, delete every cell it did not happen to
recompute.
