# Bringing staging to the contract: no migration to write, three to run

**Staging lacks four constraints. All four are in migrations that already exist
and have never been applied. There is nothing to author.**

*Engineer 1 · 2026-08-19 · measured, both sides from the catalog*

> **The direction is the opposite of the migration I nearly wrote a week ago**,
> and that is worth saying first. That one would have added constraints to
> `contract/tables.sql` on the belief that the file was missing them — a schema
> change proposed for a constraint that already existed, which would have looked
> like progress and been harder to remove than to add. This is the reverse:
> `tables.sql` is unchanged, correct, and ahead. What is behind is a deployed
> database.

---

## 1 · The gap, measured

Staging's `public` schema against a fresh build of `contract/tables.sql`, both
read from `pg_constraint` with schema qualifiers stripped:

```
staging 76 constraints    fresh build of tables.sql 80
ONLY ON STAGING       : 0
MISSING FROM STAGING  : 4
DEFINITION DIFFERS    : 0
NOT VALID ON STAGING  : 0
```

| missing constraint | kind | carried by |
|---|---|---|
| `thread_extraction_pkey` | PK | `20260818T1830_thread_extraction.sql` |
| `thread_extraction_thread_context_id_fkey` | FK | same |
| `harvest_run_outcome_ck` | CHECK | `20260819T0915_harvest_run_columns.sql` |
| `harvest_run_finish_ck` | CHECK | same |

`ONLY ON STAGING: 0` matters as much as the four: **nothing exists on staging
that the contract does not declare**, in any object class — tables, columns,
constraints, indexes, views, sequences, types, functions, triggers. The drift is
one-directional and it is entirely "not yet applied".

## 2 · `db check` already says this, in one line

```
3 applied, 3 PENDING: 20260818T1830_thread_extraction.sql,
                      20260818T2010_thread_extraction_fingerprint.sql,
                      20260819T0915_harvest_run_columns.sql
```

So this is not a discovered divergence. It is a reported one, by a check that has
been correct the whole time, and the four missing constraints are a consequence
rather than a finding. **The action is `db migrate`, not a new file.**

Authoring a migration to add these would put four constraints into a fifth file
that the three pending files already create — the same shape as adding a column
that is already declared, one layer over.

## 3 · Violations: zero, and provably rather than luckily

| constraint | affected rows on staging |
|---|---|
| `thread_extraction_pkey` | table **absent** — 0 rows, nothing to violate |
| `thread_extraction_..._fkey` | table absent; its FK target `thread_context` holds 32 rows, all valid ids |
| `harvest_run_outcome_ck` | `harvest_run` holds **0 rows** |
| `harvest_run_finish_ck` | `harvest_run` holds **0 rows** |

The two CHECK predicates cannot even be evaluated against staging today — they
reference `outcome`, which arrives in the same migration — and that is the
cleanest possible answer to the validated-or-NOT-VALID question:

**All four go on validated, in one statement each, with no NOT VALID step and no
repair pass.** And a fact about today rather than a property of the change: it is
free because `harvest_run` has never been written to and `thread_extraction` has
never existed. A single closed `harvest_run` row would make
`harvest_run_finish_ck` a data question, because a row with `finished_at` set and
no `outcome` would have to be repaired before the constraint could be validated.
The migration comment already says this.

## 4 · What applying them changes

- **`thread_extraction` appears**, with `content_fingerprint` — which is why
  Engineer 2 cannot see that column on staging today.
- **`harvest_run` gains four columns and two constraints**, which is what the
  writer needs before it can record a sweep. It still cannot: `harvest_run.source_id`
  references `source(id)` and `source` holds 0 rows because `load_source_rows` has
  no caller.
- **Nothing existing is touched.** No column type changes, no vocabulary widens,
  no row is rewritten. Every statement in the three files is `CREATE TABLE`,
  `ADD COLUMN` or `ADD CONSTRAINT`.

## 5 · Not proposed

**No change to `contract/tables.sql`.** It is the contract, it is correct, and
the fresh build of it is the target this brings staging to.

**No migration authored.** Three exist. Applying them is a write to a shared
database and is not mine to take unasked — that is the one decision left here.

**Nothing about `document.status`.** Its DEFAULT on staging is `'kept'`, the
CHECK is present and validated, and both writers pass `'kept'` as a literal in
their INSERT. The `pending` question is a separate proposal
(`docs/proposals/document-status-pending.md`) and it is a rule-4 argument about
what an untriaged document should say, not a divergence between artifacts.
