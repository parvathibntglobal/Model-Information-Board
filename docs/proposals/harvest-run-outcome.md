# `harvest_run`: four fields the adapters compute and the table cannot hold

**Proposed, not applied. `contract/` is shared.**

*Engineer 1 · 2026-08-19 · for Engineer 2's sight*

---

## 0 · One defect, four fields, and it is the table audit at column level

`docs/measurements/unwired-tables.md` asked which tables nothing writes. This is
the same question one layer down — **which values does the code compute that the
schema has no column for** — and on `harvest_run` the answer is four:

| field | computed at | proposed on |
|---|---|---|
| `outcome` | `github.py:554` | here |
| `sieve_pass_rate` | `github.py:555` | here |
| `pages_fetched` | `reddit.py:307` | issue #5 |
| `pages_stored` | `reddit.py:308` | issue #5 |

All four are carried by `harvest_run_fields()` or by the run objects feeding it,
all four are dropped by name in `collect/ops/ledger.py`, and none has a column.
The tables were the coarse layer; this is the fine one, and it was invisible to
the schema comparison for the same reason: **a comparison of two artifacts that
agree cannot see a value that is in neither.**

## 1 · Two things that are NOT wrong, checked before proposing

**`truncated_by` already permits `rate-limit`.** From the catalog, not the file:

```
CHECK (truncated_by IS NULL OR truncated_by = ANY (ARRAY[
  'query-budget', 'rate-limit', 'time-budget',
  'extraction-budget', 'result-ceiling']))
```

Every value the code writes is in that set — `rate-limit` (`github.py:356`,
`reddit.py:558`), `result-ceiling` (`github.py:395`, `reddit.py:611`),
`query-budget` (`github.py:399`, `:446`). **No widening is needed and no
constraint violation is waiting on the first throttled sweep.** What is true is
the inverse: `time-budget` and `extraction-budget` are permitted and emitted by
nothing.

**`pipeline_version` is `NOT NULL`.** It cannot be silently unset — an insert
omitting it fails — and `write_harvest_run` defaults it from `settings()`. The
two-tables-one-column concern applies elsewhere: `job_run.items_in` and
`items_out` are nullable, set by nothing, and NULL on all 12 rows.

**And every column-level claim about `harvest_run`'s rows is a claim about an
empty table.** It holds 0 rows, because until this week it had no writer at all.

## 2 · `exhausted` — the column exists, and FR-9 still cannot resume

`exhausted` is present, nullable, and already computed: `github.py:550` derives it
from `total_count <= retrieved`, and the blog fetcher sets NULL **deliberately** —
`validators.py:16`, *"`exhausted` has no meaning for a feed. A feed is never
exhausted"*.

So this is not a missing column. It is a computed value with nowhere to land,
because FR-9's resume needs two things and both are absent as data:

```
harvest_run   0 rows   the writer landed this week and has never run
watermark     0 rows   no writer at all — docs/measurements/unwired-tables.md
```

`watermark` is the durable per-`(source_id, query_key)` resume point;
`harvest_run.exhausted` is the flag saying whether resuming is even correct.
**Neither exists.** A sweep interrupted mid-pagination and one that completed are
indistinguishable today — not because the column is wrong, but because no row has
ever been written to distinguish them.

That makes `exhausted` an argument for wiring rather than for a schema change,
and it is why the writer landing matters more than the column list.

## 3 · `pages_fetched` and `pages_stored` — evidence for a decision already taken

These carry the recoverability argument, and the argument is written down while
its evidence never has been. From `collect/adapters/github.py`:

> Storing every page was the other option and was not taken … Recording what was
> stored is the rule 6 treatment: a re-sieve that can say *"this run stored page 1
> of 4"* is a re-sieve nobody over-trusts.

And `contract/harvest.yaml`: *"Raise `max_pages` and pages 2+ are sieved and never
stored … so a re-sieve can say 'this run stored page 1 of 4' rather than leaving
the reader to assume completeness."*

`RedditRun` computes both today (`reddit.py:307-308`), with the comment *"carried
here meanwhile so the number exists before the column does"*. So the decision was
taken carefully, the mechanism to audit it was specified, and **no run has ever
recorded which pages it stored.** A re-sieve cannot distinguish "page 1 of 1" from
"page 1 of 4" — which is exactly the over-trust that note exists to prevent.

## 4 · The answer to "does it have an outcome or equivalent"

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

## 5 · Why `truncated_by` is the wrong column

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

## 6 · The proposal

```sql
-- 2026MMDDTHHMM_harvest_run_columns.sql
ALTER TABLE harvest_run ADD COLUMN outcome text;
ALTER TABLE harvest_run ADD CONSTRAINT harvest_run_outcome_ck
  CHECK (outcome IS NULL OR outcome IN ('ok', 'refused', 'error'));

-- Issue #5's two, so a re-sieve can say "page 1 of 4" rather than leaving the
-- reader to assume completeness. NULL is "not recorded", never zero: a run that
-- stored no pages is 0, and a run predating the column is unknown.
ALTER TABLE harvest_run ADD COLUMN pages_fetched int;
ALTER TABLE harvest_run ADD COLUMN pages_stored  int;

-- The sieve's own yield, which the GitHub harvester already rounds to 3 places.
ALTER TABLE harvest_run ADD COLUMN sieve_pass_rate real;
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

## 7 · What it makes distinguishable

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

## 8 · Until it lands

`collect/ops/ledger.py` records the reasoning at the writer, aimed specifically at
the next reader who sees the gap and closes it with a fifth `truncated_by` value.
A refused run records **only that it was attempted**: the row exists, the counts
are zero, and nothing claims to know why. That is honest, and it is what the two
phases already buy — before this change, a refused sweep left no trace at all.

## 9 · Not proposed

**No change to `truncated_by`'s vocabulary** — `rate-limit` is already in it, and
the fifth-value trap is documented at the writer. **No change to `exhausted`** —
it exists, it is computed, and what it needs is rows. **No change to
`pipeline_version`** — it is `NOT NULL` and cannot go missing.

All four keys stay dropped by name in `write_harvest_run` until the columns exist,
so the day this lands the writer stops discarding values it is already handed, and
`_PROPOSED_NOT_IN_SCHEMA` empties rather than being edited around.

## 10 · Why this is one proposal and not two

They are the same defect on the same table, found by the same method one layer
below the table audit. A second document an hour later would be the third thing to
read about `harvest_run` today, and a reviewer who has read two already reads the
third less carefully — which is this week's failure mode relocated from a check
into a reviewer.
