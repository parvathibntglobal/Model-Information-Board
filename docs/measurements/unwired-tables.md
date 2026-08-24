# Tables with no writer, no caller, or no reader

**Eight of thirty tables have no writer at all. One has a writer nothing calls.
One is written and never read. Nine are wired, and eleven belong to `judge/`.**

*Engineer 1 · 2026-08-19 · table by table against staging, not against
`BUILD-PLAN.md`*

> The companion to `uncalled-writers.md`, which went function by function and
> found `mark_swept` and `write_authors` with no callers. This goes **table by
> table**, which is Engineer 2's method and the one that found four unwritten
> tables in `judge/`. The difference matters: a function-first sweep can only
> find writers that exist, and the expensive case is a table nothing writes.

---

## 0 · Why this audit distrusts itself

Three checks on this schema read as coverage in the last two days and were not:
`contract/tables.sql` was thought not to describe tables it does describe,
`check_pending` was named for a state and asserted a mechanism, and `columns()`
was named for what it returned rather than what it compared. So the method here
is stated, and its own two defects are recorded rather than fixed silently.

**Writes are found by AST, not by regex.** A literal sweep for
`INSERT INTO <table>` misses `f"INSERT INTO {LEDGER}"`, which is exactly how
`schema_migration` came to look unwritten in the first pass of this audit.

**What it cannot attribute, it prints.** 16 statements build a table name at
runtime. They are listed in §4 rather than dropped, because a sweep that drops
what it cannot parse reports a cleaner schema than it measured.

**Its first run was wrong, in the direction of "nothing here".** One shared
transaction meant `thread_extraction` not existing aborted it, and every row
count after that read NULL — an empty answer wearing the clothes of a measured
one. Now autocommit, one query per table.

---

## 1 · The five you asked about first

| table | rows | state |
|---|---|---|
| `job_run` | **12** | **wired** — `ops/ledger.py` writes, `ops/chain.py` calls, `ops/ledger.py` reads |
| `coverage_gap` | 0 | **NO WRITER** — and `judge/pages/coverage.py` reads it, twice |
| `harvest_run` | 0 | **NO WRITER** — unchanged since the `ops/` design. One reader |
| `harvest_run_source` | — | **NOT A TABLE.** It is the name of an index on `harvest_run`: `harvest_run_source_query_idx`, `tables.sql:924` |
| `thread_extraction` | absent | **judge/** writes it (`store/extractions.py`) and reads it. Absent from staging because its migration is pending |

`harvest_run` is the one to look at twice. It has no writer, and its single
reader is a check: `assert_no_phantom_sweeps` compares
`count(model_version.last_swept_at IS NOT NULL)` against
`(SELECT count(*) FROM harvest_run)`. Both operands are pinned at zero — the
second because nothing writes the table, the first because `mark_swept` has no
caller either. **The check cannot currently fire in either direction.** It is
correct code measuring nothing, and it starts meaning something the day either
writer acquires a caller.

`coverage_gap` is the one that owes somebody. `tables.sql` says *"collect/ fills
this. judge/ reads it for the coverage page"*, `judge/pages/coverage.py` selects
from it in two places, and its own docstring records that a search for
`INSERT INTO coverage_gap` returns nothing anywhere. Four `kind` values are
declared and none is produced. **Deliberate and unbuilt** rather than broken —
but the consumer is built, so the page renders from an empty table.

---

## 2 · The whole list, three states

**NO WRITER — eight.** Nothing in either lane writes them.

| table | reader | note |
|---|---|---|
| `coverage_gap` | judge, ×2 | §1. Kinds proposed, none produced |
| `harvest_run` | one check | §1. Both operands of that check are zero |
| `capability` | — | **`claim.capability_key` REFERENCES it.** Nothing can write a claim until this table has rows, and nothing writes this table. The keys live in `contract/capabilities.yaml` with no loader |
| `watermark` | — | FR-9's durable resume. Six mentions, all prose |
| `dedup_cluster` | — | E3's clustering. Seven mentions, all prose |
| `author_identity_cluster` | — | identity clustering, unbuilt |
| `golden_label` | — | calibration set, unbuilt |
| `audit` | — | no mention anywhere except one unrelated docstring |

**WRITER, NO CALLER — one.**

| table | writer | note |
|---|---|---|
| `author` | `assemble/authors.py:write_authors` | No caller in `collect/` or `scripts/`. Already known from `uncalled-writers.md`, still true, and **nothing reads it either** — so it is in two categories at once. `claim.author_id` REFERENCES it |

**WRITTEN, NEVER READ — one.**

| table | writer | note |
|---|---|---|
| `model_event` | `registry/events.py`, `registry/load.py` | Both called. 0 rows: the poller ran and produced no events, because a first poll has no prior state to diff. Nothing anywhere selects from it |

**WIRED — nine.** `model_version` (340 rows), `document` (30), `thread_context`
(32), `job_run` (12), `schema_migration` (3), `model_alias`, `price_tier`,
`pricing_history`, `source`. The last four hold 0 rows because their only writer
is `load_seed`, and `assert_no_fixtures` refuses seed provenance outside
development — so 0 on staging is **correct**, not missing.

**judge/ — eleven.** `claim`, `claim_weight`, `cell`, `label`, `label_change`,
`reported_context`, `thread_extraction`, `answer`, `outcome`, `role`,
`task_profile`. Hers to audit; this pass records the writer and reader counts
and does not judge the wiring.

---

## 3 · What is deliberate and what is not

**Deliberate:** `coverage_gap`, `watermark`, `dedup_cluster`,
`author_identity_cluster`, `golden_label` — declared ahead of the stage that
fills them, which is how this schema was designed and is why a list beats five
individual fixes.

**Not deliberate, and cheap:** `capability` blocks `claim` through a foreign key,
and `contract/capabilities.yaml` already holds the twelve keys. A loader is
small and nothing else can proceed without it.

**Not deliberate, and load-bearing:** `author` has a writer, a foreign key
pointing at it, and no caller. The first Reddit claim cannot carry an author id.

**Worth deciding rather than fixing:** `audit` has no writer, no reader and no
mention. Either something is meant to write it or it should leave the schema.

---

## 4 · Statements this pass could not attribute

Sixteen build a table name at runtime, so the sweep above cannot key them to a
table. Printed because a check that iterates must say what it could not see.

```
collect/migrate.py:migrate                    INSERT INTO {X} (filename, content_hash)
collect/migrate.py:stamp_at_head              INSERT INTO {X} (filename, content_hash)
collect/registry/load.py:_upsert_model         INSERT INTO model_version ({X}) VALUES ({X})
collect/registry/sources.py:load_source_rows   INSERT INTO source ({X}) VALUES ({X})
collect/registry/openrouter.py:write_model_versions   INSERT INTO model_version (…
scripts/export_thread_contexts.py:_insert      INSERT INTO {X} ({X}) VALUES ({X})
… plus 10 in judge/, all naming their table literally on the next line
```

The first two are `schema_migration`'s writer, which is why it appears as wired
in §2 despite the sweep's own "NO WRITER" line: the reconciliation is manual and
recorded here rather than smoothed away.

---

## 5 · What would revise this

- **A caller for `write_authors`**, which unblocks `claim.author_id`.
- **A loader for `capability`**, which unblocks `claim` entirely.
- **Anything writing `harvest_run`**, which turns `assert_no_phantom_sweeps`
  from a check with two zero operands into a check.
- **The two pending migrations**, which is what `thread_extraction` is waiting
  for, and with it Engineer 2's `content_fingerprint` column.
- **A ruling on `audit`.**
