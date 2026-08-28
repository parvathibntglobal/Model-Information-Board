# Correcting the 853: `not_recorded` in place, and I am withdrawing the fourth value

**The decision is still open, which is why this is worth writing.** #165 is merged
in git and **its migration has not been applied** — the live CHECK still permits
three values and all 853 rows still carry `no_run_for_source`. So nothing has been
done to them yet, and I now think #165's migration should not be the thing that
does it.

*Engineer 1 · 2026-08-28*

---

## 0 · Verified state, before the argument

```
live document.retrieval_provenance      no_run_for_source 854 | not_recorded 344 | run_recorded 52
                                        total 1,250. The panel's three buckets sum EXACTLY.
live CHECK                              three values. 'unreviewed_writer' is NOT in it.
20260828T1200_..._unreviewed.sql        on disk, merged, NOT applied
```

## 1 · Can the value be rewritten in place? Yes, and NULL was never available

**NULL is not an option.** The column is
`retrieval_provenance text NOT NULL DEFAULT 'not_recorded'`. Making it nullable
would defeat its purpose: it exists precisely so that a NULL `harvest_run_id`
cannot mean two things, and a nullable provenance column reintroduces exactly the
ambiguity it was added to remove. So "NULL is the only honest replacement" is not
on the table, and it should not be put there.

**And no missing information is required.** We know both facts the column asks
about:

```
was a query rendered?          YES - the per-model fetch's Reddit arm issues
                                     model-name queries (#160)
was its run recorded?          NO  - harvest_run has zero rows for reddit
```

That pair is exactly what `not_recorded` means. The NULL `harvest_run_id` on
those rows is **missing, not complete** — which is the one thing a reader needs
from this column, and it is knowable without guessing. **A plain in-place `UPDATE`
to `not_recorded` is honest, needs no schema change, and needs no new value.**

## 2 · Why I am withdrawing `unreviewed_writer`: it is on the wrong axis

This is a correction to my own proposal in #159 and my own migration in #165.

`retrieval_provenance` answers **one** question — *what do we know about what
retrieved this row* — with three positions on a single axis:

```
no_run_for_source    no query was rendered, so there is nothing to record   COMPLETE
run_recorded         a query was rendered and its run id is on the row      COMPLETE
not_recorded         a query was rendered and we cannot say which run       INCOMPLETE
```

*"The writer is not on `main`"* is not a position on that axis. It is a fact about
**code**, not about retrieval. Two rows could both be `unreviewed_writer` with one
having rendered a query and one not — and at that point the column has stopped
answering its own question.

**What `not_recorded` needs is one clause widened, not a fourth sibling.** Its
comment says *"a run existed and no id was passed"*. It should say *"a query was
rendered and we cannot say which run"* — which covers both "a `harvest_run` row
was opened and its id did not reach the writer" and "no `harvest_run` row was
opened at all". Downstream those are the same fact, and the column is downstream.

## 3 · The argument that decides it, and it is your panel

`judge/pages/pipeline_status.py` enumerates the three values as three
`count(*) FILTER` buckets against `count(*)` as the total:

```sql
SELECT count(*),
  count(*) FILTER (WHERE retrieval_provenance = 'run_recorded'),
  count(*) FILTER (WHERE retrieval_provenance = 'no_run_for_source'),
  count(*) FILTER (WHERE retrieval_provenance = 'not_recorded')
FROM document
```

**A fourth value makes those buckets stop summing.** 853 rows would count in the
total and appear in no bucket: a panel reading `1,250 documents` with buckets
adding to 397. Not an error — a discrepancy that reads as a rendering bug or goes
unnoticed entirely, in the one page built specifically to honour rules 4, 6 and 7.

Today they sum to 1,250 exactly. **#165's migration would break that silently**,
and it shipped without a change to your panel because I did not check for a
reader. The audit I wrote the same day says `document.retrieval_provenance` has
one, and I did not read my own output.

## 4 · And the value is already obsolete, because #163 merged

`unreviewed_writer` means *the code that wrote this row is not on `main`*. **#163
— "feat: per-model on-demand fetch + live fetch log" — is merged.** So from now
on the per-model fetch *is* on `main`, and the category is false for every future
row it writes.

A schema value that was true for one week, describes a branch state rather than a
data property, and outlives the branch is a value nobody can interpret in six
months. That is the opposite of what a closed vocabulary is for.

## 5 · Where the unreviewed-writer fact should live instead

Not in the schema. In `docs/measurements/`, as an id list with the date and the
branch — the same treatment the 47 unreachable payloads get. It is a fact about
one week of one branch, and it stops being true the moment the branch merges,
which it now has.

If it later turns out that *"which writer produced this row"* is a question worth
answering durably, that is its own column with its own vocabulary, and it is a
different proposal from this one.

## 6 · What I propose, concretely

```
1  a follow-up PR reverting the migration from #165
     - drop 20260828T1200_..._unreviewed.sql
     - revert the tables.sql CHECK to three values
     - KEEP the reddit_write.py change untouched. It is the actual defect and it
       stands alone: a writer must not type a claim about a run it cannot know.
       REDDIT_PROVENANCE simply loses its third member.

2  widen `not_recorded`'s comment in tables.sql, per section 2

3  one UPDATE, in its own migration so it is reviewable and recorded:
     UPDATE document SET retrieval_provenance = 'not_recorded'
      WHERE source = 'reddit' AND retrieval_provenance = 'no_run_for_source'
        AND fetched_at >= '2026-08-27' AND fetched_at < '2026-08-28';
     -- 853 rows. Rests on #160's account, not on a column. Stated in the
     -- migration, because there is no field recording which writer produced a
     -- row and this correction cannot invent one.

4  the id list in docs/measurements/, for the unreviewed-writer fact
```

**Your panel needs no change under this proposal**, which is the main thing that
recommends it over what I merged.

## 7 · One thing found while checking, and it blocks step 3

`schema_migration` is not a record of what has been applied to the shared
database.

```
migration files on disk          10
recorded in schema_migration      7

on disk and unrecorded:
  20260824T1500_document_retrieval_provenance.sql    <- APPLIED (the column exists)
  20260825T1200_claim_polarity_neutral.sql           <- APPLIED ('neutral' is in the CHECK)
  20260828T1200_..._unreviewed.sql                   <- NOT applied
```

**Two applied migrations are missing from the ledger**, so `db migrate` would try
to re-apply them: the 08-24 one adds columns and would fail on the second
attempt, which means **the migration path on that instance is currently broken
for everyone**. The 08-25 one happens to be idempotent and would pass, which is
luck.

That has to be sorted before any further migration is applied there, including
step 3 above. It is `collect/`'s and it is mine — flagged here because it is the
reason step 3 cannot simply be run tonight, and because a ledger that
under-records is the same defect class as everything else on this page: a value
that looks like a record and is not.
