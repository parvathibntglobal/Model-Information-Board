# `document.status` needs a fifth value, and it is not a `collect/` decision

**Proposed, not applied. The DDL is below and it is deliberately not in
`contract/migrations/`, because a file there is applied by anyone running
`db migrate` and this one changes the meaning of a figure on `/filtered`.**

*Engineer 1 · 2026-08-19 · measured against staging*

---

## 0 · Three things that were proposed alongside this and are not needed

Measured directly against staging rather than against `tables.sql`, because the
whole reason this document exists is that the file and the database were being
read as interchangeable.

| proposed | measured | verdict |
|---|---|---|
| 21 constraints missing from staging | **2** missing: `thread_extraction_pkey`, `thread_extraction_thread_context_id_fkey` | both belong to the table `20260818T1830` creates, which `db check` reports as pending |
| `UNIQUE (source, external_id)` never enforced | present and `convalidated = True` on **both** `document` and `author` | nothing to add |
| `coverage_ratio` needs restoring to GENERATED | `is_generated = ALWAYS`, full CASE expression present | nothing to drop, nothing to recreate, no cost to state |

Whole-schema comparison, `pg_get_constraintdef` on both sides, whitespace
collapsed so a newline cannot matter, **both sides sized before the diff**:

```
staging 76 constraints, fresh build of tables.sql 78
  staging by contype: {'c': 18, 'f': 25, 'p': 29, 'u': 4}
  fresh   by contype: {'c': 18, 'f': 26, 'p': 30, 'u': 4}
MISSING FROM STAGING : 2   (both thread_extraction)
ONLY ON STAGING      : 0
DEFINITION DIFFERS   : 0
NOT VALID ON STAGING : 0
```

**CHECK constraints: 18 on staging, 18 in a fresh build, none missing.** So the
"zero violations across all 21" framing has no subject: there is no set of 21,
and consequently no NOT VALID step and no data repair to describe. That is worth
stating rather than quietly dropping, because the migration it justified would
have added constraints that already exist.

## 1 · What IS wrong, and it is not a missing constraint

Both writers insert `'kept'` as a literal — `collect/adapters/github.py:526`,
and `collect/assemble/article.py:document_row` — and the column's `DEFAULT` is
`'kept'`. `kept` is a **triage verdict**.

So all 30 `document` rows on staging assert a verdict that no triage produced.
`collect/adapters/blog/write.py` even documents the intended reading:

> `document.status` stays `'kept'`, which is the schema default and means *this
> stage did not filter*, not *this passed*.

That reading is not recoverable from the value. It is rule 4 on the data side: a
stage that has not run looks exactly like a stage that passed.

**And no writer is blocked today.** Audited both lanes against all 15 vocabulary
CHECKs: `collect/` emits `'kept'` (permitted) and parameterises the rest;
`judge/` parameterises everything and its one literal, `'harvested'` into
`reported_context.provenance`, is permitted. **No column has an omitted value in
either lane.** So this is a design correction, not an unblocking fix, and it is
not urgent in the way a refused insert would be.

## 2 · The proposed change, in full

```sql
-- 20260819THHMM_document_status_pending.sql
--
-- WHY: both writers insert 'kept' and the DEFAULT is 'kept', so a document that
-- has never been triaged carries a triage verdict. Rule 4 on the data side.
--
-- A FACT ABOUT TODAY, NOT A PROPERTY OF THIS CHANGE: staging holds 30 document
-- rows, all 'kept', and nothing anywhere emits a value the CHECK omits. So the
-- constraint can be replaced validated, in one statement, with no NOT VALID
-- step and no repair pass. On a database with triaged rows that would not hold.

ALTER TABLE document DROP CONSTRAINT document_status_ck;
ALTER TABLE document ADD CONSTRAINT document_status_ck
  CHECK (status IN ('pending', 'kept', 'filtered', 'rejected', 'tombstoned'));

ALTER TABLE document ALTER COLUMN status SET DEFAULT 'pending';

-- The 30 existing rows were written by the blog path and never triaged. Moving
-- them is a CORRECTION, not a rewrite: 'kept' was never true of them.
UPDATE document SET status = 'pending'
 WHERE status = 'kept' AND triage_verdict IS NULL;

-- The partial index no longer covers fresh documents. Kept as-is deliberately:
-- it exists for the triaged-and-kept set, which is what the answer path reads.
-- Stated here so it is a decision rather than a discovery.
--   CREATE INDEX document_status_idx ON document (status) WHERE status = 'kept'
```

`contract/tables.sql` moves in the same commit or the equivalence test fails —
the chain and the declaration have to agree, and that test is the only thing
that checks it.

## 3 · Why this is hers to rule on, and the reason is not "`contract/` is shared"

`judge/pages/filtered.py` partitions the vocabulary **exhaustively**, and its
denominator is open-ended:

```python
DISPLAYABLE     = ("filtered", "rejected")
NEVER_DISPLAYED = "tombstoned"
...
"SELECT count(*) FROM document WHERE status <> %s", (NEVER_DISPLAYED,)
```

So a fifth value is silently included in that denominator. The page's own
docstring says why that matters more than it looks:

> "12 documents rejected" is not a claim. "12 of 1,297 documents" is, and the
> difference decides whether the filter looks reasonable or looks like a purge.

Add `pending` and the denominator becomes *"12 of 1,297, of which an unstated
number were never triaged at all"* — the population changes meaning while the
figure keeps its form. That is rule 7's failure on a published page, and it is
the strongest argument for the change being reviewed rather than applied.

Three things she may want instead, and each is a different fix:

1. **`WHERE status = ANY(DISPLAYABLE ∪ {'kept'})`** as the denominator — the
   population becomes "documents triage has seen", which is what the figure
   means today by accident.
2. **`pending` excluded explicitly**, alongside `tombstoned`, with the reason
   written where `NEVER_DISPLAYED` is.
3. **A different word.** `untriaged` says what is true of the row; `pending`
   borrows the ledger's vocabulary for a different idea. I lean `pending` for
   cross-table consistency and hold it lightly.

Also her call: the docstring line *"`document.status` has four values and only
two belong on this page"* becomes false, and that file is the one place the
vocabulary is explained to a reader.

## 4 · What I have not done

Not applied, not written into `contract/migrations/`, and `tables.sql` is
untouched. The writers still insert `'kept'`, because changing them ahead of the
CHECK would produce refused inserts, and changing them after it without her
ruling on the denominator would move a published figure without her seeing it.
