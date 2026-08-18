# `job_run`, and the first real use of the migration path

**Report before building. The table should go to `contract/` now, and the
migration costs writing the DDL twice — which is the designed cost, not an
accident. The more interesting finding: `contract/migrations/` contains no
migrations, so the equivalence test has never compared a chain that includes
one. This would be its first real exercise.**

*Engineer 1 · 2026-08-18 · `contract/` unchanged by this document*

---

## 1 · Why now — three findings, one shape

`job_run` was proposed in `docs/ops-nightly-chain.md` as a JSONL artifact with
the table *flagged rather than taken*. Three findings since have all reduced to
one question the artifact cannot answer:

| finding | the question it needed |
|---|---|
| `in_window` at schema default on 340 rows | has `recompute_window` ever run here? |
| `mark_swept` residue on one row | has anything ever swept? |
| `write_documents`, `load_source_rows`, `migrate` greping as wired | has this caller ever run against a real database? |

**"Has this ever run" is not answerable today**, and every one of the three cost
a manual investigation to establish. A JSONL file on the machine that ran the
job answers it for that machine; a table answers it for the database the rows
are about, which is where the question is actually asked.

That is the argument for a table rather than an artifact, and it is stronger
than the original one (durability). `assert_no_phantom_sweeps` already
demonstrates the shape: it is cheap **only because it can join
`last_swept_at` against `harvest_run`** — a contradiction is checkable, an
absence is not. `job_run` generalises that from one column to every stage.

### What it does not solve

Condition B stays partly unguarded even with `job_run`. A writer that has never
run leaves an *absence*, and an absence before the first scheduled run is the
expected state. `job_run` converts "has this ever run" from an investigation
into a query; it does not make never-having-run an error, because for most of
this pipeline it is currently correct.

---

## 2 · Does the table go to `contract/` now?

**Yes**, and the alternative is worse than it looks.

`ops/chain.py` exists and refuses eight stages. Every refusal is currently
invisible after the process exits — the chain reports to stdout and forgets. The
first thing `docs/ops-nightly-chain.md` asks for is that **a stage which did not
run is distinguishable from a stage that ran and found nothing**, and that
requires a row written *before* the work, which requires the table.

Proposed shape, deliberately small — five columns do the job and every extra one
is a column the first migration has to get right:

```sql
-- Every stage of every nightly run, written BEFORE the work starts.
--
-- A row inserted at the start with finished_at NULL and updated at the end.
-- A killed process then leaves "started 03:00, never finished", which is a
-- fact; a row written only on success leaves nothing, which reads as a night
-- with no work. This asymmetry is the whole reason the table exists.
CREATE TABLE job_run (
  id            text PRIMARY KEY,
  stage         text NOT NULL,          -- preflight | registry | harvest | ...
  started_at    timestamptz NOT NULL DEFAULT now(),
  finished_at   timestamptz,            -- NULL = did not finish. NOT "failed".
  outcome       text,                   -- ok | refused | failed. NULL while running.
  -- Counts are NULL where unknown, never 0 (rule 6). A stage that could not
  -- ask has not counted zero.
  items_in      int,
  items_out     int,
  detail        jsonb,                  -- the refusal text, or the stage's report
  pipeline_version text NOT NULL,

  CONSTRAINT job_run_outcome_ck
    CHECK (outcome IS NULL OR outcome IN ('ok', 'refused', 'failed'))
);
CREATE INDEX job_run_stage_idx ON job_run (stage, started_at DESC);
```

Two design points worth arguing before it lands:

- **`finished_at IS NULL` means *did not finish*, not *failed*.** A killed
  process cannot write its own failure, so the absence has to carry the meaning.
  `outcome` is separately nullable for the same reason.
- **`items_in`/`items_out` are nullable.** A stage that refused counted nothing,
  and 0 would assert it counted and found none — the distinction this project
  has now made four times.

---

## 3 · What the migration costs

### The mechanical cost: the DDL twice

`collect/migrate.py` is forward-only, timestamp-named, content-hashed. Adding a
table means:

1. the `CREATE TABLE` in `contract/tables.sql` — the description of the schema;
2. the same DDL in `contract/migrations/20260819T_____job_run.sql` — the delta
   for databases that already exist.

That duplication *is* the design. `tests/test_migrations.py` builds both sides
and compares columns, constraints, indexes and views:

```
schema A  <- contract/tables.sql
schema B  <- baseline.sql + every migration in order
```

Diverge and the test names exactly what diverged. So the cost is writing it
twice and the protection is that writing it twice differently fails the build.

### The finding: this path has never been exercised

```
migrations discovered: 0  []
baseline length: 36,872 chars
```

**`contract/migrations/` contains only `baseline.sql`, and `discover()` returns
an empty list.** So the equivalence test currently compares `tables.sql` against
`baseline.sql` alone — a chain of length zero. Every one of its assertions has
only ever run against that.

`test_the_equivalence_test_can_fail` exists and guards the harness, so this is
not the "zero from a harness nobody has shown can produce a one" failure. But it
does mean:

- the machinery for *applying* a migration (`migrate()`, the ledger, the
  content-hash refusal) is tested against fixture files in `tmp_path`, and
- the machinery for *comparing* a migrated schema to the file has never seen a
  real delta.

**So `job_run` is a test of the path as much as a use of it**, and it is a good
first case: one new table, no ALTER, no data movement, nothing to get wrong
except the DDL agreeing with itself. If the path is broken, this is the cheapest
possible way to find out.

### What I would watch for, having not run it yet

1. **`schema_migration` is empty on staging.** `migrate` has ten call sites and
   the ledger holds nothing, so staging is a database predating the ledger.
   `db migrate` handles that explicitly — it creates the ledger when nothing is
   pending — but that path has never run against a real database either.
2. **Ordering against a fresh `db init`.** A new database gets `tables.sql`,
   which will already contain `job_run`, and then has a migration pending that
   creates it again. `test_the_baseline_is_not_a_migration` shows the shape is
   understood; whether `db check` reports the migration as pending against a
   freshly-initialised database is exactly the question the equivalence test
   does not answer, because it builds both sides itself rather than exercising
   the CLI.

That second one is the real risk and it is not hypothetical: it is how a
"migrate on startup" bug would present, and startup application is refused
everywhere else in this lane for that reason.

---

## 4 · Recommended order

1. **`job_run` in `contract/tables.sql` plus the migration**, as one PR, so the
   equivalence test sees both halves at once.
2. **Run `db check` and `db migrate` against staging** before wiring anything to
   the table — the path is being tested, so test it before depending on it.
3. **Then wire `ops/chain.py`** to write the row before the work.

Not proposed here: retention on `job_run`. It grows by one row per stage per
night, which is trivial, and a retention policy is a threshold that belongs in
`contract/` once there is a year of rows to reason about rather than now.
