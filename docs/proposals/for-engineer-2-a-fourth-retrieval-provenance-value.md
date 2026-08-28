# A fourth `retrieval_provenance` value: `unreviewed_writer`

**Proposed, not taken. `contract/tables.sql` and `contract/migrations/` are
untouched by this document** — the column's CHECK is shared, and this is a
ruling before it is a migration.

*Engineer 1 · 2026-08-28*

---

## 1 · The state that has no value

Documents written by `feat/per-model-fetch`, a branch that is local-only and
unpushed. They are real rows describing real documents, produced by code that is
not on `main` and has been reviewed by nobody. The run opened no `harvest_run`,
so nothing records what retrieved them.

The column as it stands:

```sql
document_retrieval_provenance_ck
  CHECK (retrieval_provenance IN ('run_recorded','no_run_for_source','not_recorded'))

document_retrieval_provenance_agrees_ck
  CHECK ((retrieval_provenance = 'run_recorded') = (harvest_run_id IS NOT NULL))
```

Three values, and each already means something specific:

| value | means | rows |
|---|---|---|
| `run_recorded` | a run exists and its id is on the row | 52 |
| `no_run_for_source` | this source renders no query, so there is nothing to record | 854 |
| `not_recorded` | **a run existed and no id was passed** | 344 |

## 2 · Why `not_recorded` is the wrong home, and it is rule 6

`not_recorded` is a statement about *plumbing*: the sweep ran, the ledger row was
opened, and the id did not reach the writer. That is what the 28 GitHub documents
from 2026-08-20 are, and the migration that introduced the column says so — it
placed all 343 then-existing rows there because *"that is what they are"*.

The unreviewed-writer rows are a statement about *code*: no run was opened at
all, and the path that wrote them is not in the repository.

Filing the second under the first makes them indistinguishable from documents
whose run was simply never recorded. **That is a missing value silently becoming
a definite one** — a reader computing a yield figure over the corpus includes
them and has nothing on the page to disagree with, which is the class of defect
rule 6 exists for and the one this project has now met in five places.

It is rule 7's half too: any denominator drawn over `document` silently contains
rows whose population nobody can state.

## 3 · The proposal

```sql
-- contract/migrations/<stamp>_document_retrieval_provenance_unreviewed.sql
ALTER TABLE document DROP CONSTRAINT document_retrieval_provenance_ck;
ALTER TABLE document ADD CONSTRAINT document_retrieval_provenance_ck
  CHECK (retrieval_provenance IN
         ('run_recorded','no_run_for_source','not_recorded','unreviewed_writer'));
```

**`document_retrieval_provenance_agrees_ck` needs no change.** It reads
`(retrieval_provenance = 'run_recorded') = (harvest_run_id IS NOT NULL)`, and a
fourth value on a row with a NULL id satisfies it exactly as written. Worth
saying because a second constraint on the same column is the thing a migration
like this usually breaks.

**On the name.** `unreviewed_writer` states the fact — the code path that wrote
the row is not on `main` — rather than a judgement about the data. It stays true
whether the branch is later merged or deleted, and it does not imply the
documents are wrong. `orphan`, `untrusted` and `bad_provenance` were considered
and rejected for asserting more than is known: the rows may be perfectly good
documents.

**What it is not.** It is not a quarantine and it does not change what the rows
mean for any other column. It is a discriminator, so a denominator can exclude
them deliberately and a reader can see they were excluded.

## 4 · What it costs, and what happens if it is declined

```
migration            one ALTER, ~6 lines, no data change to existing rows
writers              none today - no writer on main produces this state, which
                     is the point. A future one would set it explicitly.
readers              anything grouping on retrieval_provenance gains a fourth
                     bucket. `judge/pages/coverage.py` is the one to check.
backfill             17 rows, and see 5 - they are not reachable from here
```

**If it is declined**, the honest fallback is to file them under `not_recorded`
**and record the collapse in writing**, so a later reader of a corpus figure can
find out that two states were merged. A silent merge is the part that is not
acceptable; a documented one is a judgement call about whether 17 rows justify a
contract change, and that judgement is legitimately E2's.

## 5 · The rows are not reachable, and that is a second finding

**They are not in the shared database.** Checked exhaustively: 30 tables, one
schema, and nothing anywhere is newer than 2026-08-27; `harvest_run` stops at
2026-08-24 and holds no row outside `source_id = 'github'`. `DATABASE_URL` and
`STAGING_DATABASE_URL` resolve to the same host and the same database, so there
is no second shared instance.

Three homes exist for a write in this project and only one of them is shared:

```
DATABASE_URL / STAGING_DATABASE_URL   52.17.75.29  Model-information-Board   shared
TEST_DATABASE_URL                     localhost:5433  modelboard_test        PER MACHINE,
                                                                             DISPOSABLE
```

`docs/dev-database.md` documents the second as a disposable instance created by
`scripts/dev-postgres.ps1`, and `-Destroy` drops it. It is not running on this
machine.

**So the most probable answer is that the 17 rows are on a disposable local
instance** — `feat/per-model-fetch` is described as *test* runs, and that is
where a write-path test writes. I cannot confirm it from here; whoever ran it
can, with one query.

**Why this is not the raw-store problem again.** The raw store is machine-local
and the database is shared: the 2026-08-27 Reddit work proves it, because its
853 documents are in the shared database while 758 of their payloads are absent
from this machine's store. Evidence landing on a *disposable local database* is a
different and sharper failure — the store problem loses the payload and keeps the
row, and this loses the row too, on an instance whose documentation says to
destroy it.

**Named rather than worked around**, as asked. The action is not a migration: it
is to confirm where those 17 rows live and, if they are on a disposable instance,
to move them or accept that the figures quoted from them cannot be re-derived.
