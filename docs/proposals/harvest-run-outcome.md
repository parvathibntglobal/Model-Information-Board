# `harvest_run` needs a verdict column, and it must not be a fifth `truncated_by`

**Proposed, not applied. `contract/` is shared.**

*Engineer 1 · 2026-08-19 · for Engineer 2's sight*

---

## 0 · The answer to "does it have an outcome or equivalent"

**No.** `harvest_run` has eleven columns and none of them is a verdict:

```
id · source_id · query_key · started_at · finished_at
items_fetched · items_kept · http_errors
exhausted · truncated_by · pipeline_version
```

Read from `information_schema` on staging, not from the file. `exhausted` is
tri-state but it is about pagination — *did this query reach the end of its
results* — and `truncated_by` is about caps. Neither can answer *did this sweep
happen*.

## 1 · Why `truncated_by` is the wrong column

`truncated_by` says **a sweep stopped early**. Every value names something that
cut short a fetch already in progress, and the column's own comment in
`tables.sql` splits them on exactly that axis:

```
CAPS WE CHOSE            query-budget · time-budget · extraction-budget
  "we decided not to look further"
THE PLATFORM STOPPING US  rate-limit · result-ceiling
  "we were not allowed to look further"
```

A refused sweep is neither. **Nothing was truncated, because nothing was
fetched.** Adding a fifth value would make the column mean two incompatible
things — *cut short* and *never begun* — and the coverage page renders it as the
first, so a refusal would appear as a sweep that hit a cap. That is worse than
the gap: it is a wrong answer where there is currently no answer.

**Nor can a refused sweep be left open.** `finished_at IS NULL` is how a killed
process is recognised, and keeping that distinction is the whole reason the write
happens in two phases. Overloading it would trade one silent conflation for
another.

## 2 · The proposal

```sql
-- 2026MMDDTHHMM_harvest_run_outcome.sql
ALTER TABLE harvest_run ADD COLUMN outcome text;
ALTER TABLE harvest_run ADD CONSTRAINT harvest_run_outcome_ck
  CHECK (outcome IS NULL OR outcome IN ('ok', 'refused', 'error'));
```

**`job_run`'s vocabulary, deliberately, and not a second one.** That table already
learned this lesson: its first CHECK said `failed`, and
`20260818T1520_job_run_outcome_vocabulary.sql` exists solely to replace it with
`error` so the chain and the ledger share one word per concept. A harvest ledger
inventing `blocked` or `gated` would need a translation layer at the one place
both are read together.

**NULL means "still running, or killed"**, matching `job_run` exactly, and it
pairs with `finished_at` the same way — which argues for the same constraint
`job_run` carries:

```sql
CONSTRAINT harvest_run_finish_ck CHECK ((finished_at IS NULL) = (outcome IS NULL))
```

That is worth taking or rejecting deliberately. It makes a row unable to claim a
verdict without a finishing time, which is the invariant that stopped `job_run`
rows from being half-written — but it also means `close_harvest_run` must always
set both, and a refused sweep gets `finished_at = now()` even though it never
fetched. I lean towards taking it, on the grounds that a refusal *is* a finish.

## 3 · What it makes distinguishable

| state | today | with the column |
|---|---|---|
| refused by the terms gate | `items_fetched = 0` | `outcome = 'refused'` |
| ran, platform returned nothing | `items_fetched = 0` | `outcome = 'ok'`, `items_fetched = 0` |
| ran, everything filtered | `items_fetched > 0, items_kept = 0` | unchanged |
| raised mid-sweep | indistinguishable from the above | `outcome = 'error'` |
| killed | `finished_at IS NULL` | unchanged |

**FR-10 needs the first two apart.** A yield figure computed across them averages
sweeps that happened with sweeps that were never allowed to, and the resulting
number is about our permissions rather than about the platform's content — rule 7,
with the population silently including non-events.

## 4 · Until it lands

`collect/ops/ledger.py` records the reasoning at the writer, aimed specifically at
the next reader who sees the gap and closes it with a fifth `truncated_by` value.
A refused run records **only that it was attempted**: the row exists, the counts
are zero, and nothing claims to know why. That is honest, and it is what the two
phases already buy — before this change, a refused sweep left no trace at all.

## 5 · Not proposed

No change to `truncated_by`'s vocabulary. No change to `exhausted`. And the
`outcome` key that all three adapters' `harvest_run_fields()` already carry stays
dropped by name in the writer until the column exists — so the day it lands, the
writer stops discarding a value it is already being handed.
