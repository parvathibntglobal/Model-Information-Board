# If a migration generator is built, it reads `tables.sql` — never the database

**No such tool exists today.** `collect/migrate.py` discovers, checks, stamps and
applies; it has no generator, and nothing in the repo emits a `.sql` migration.
This is a specification written before the tool, because the wrong version of it
is the one that feels natural to write.

*Engineer 1 · 2026-08-19 · for Engineer 2's sight, since `contract/` is shared*

---

## 0 · What is true of the two artifacts today, measured

Both open questions are already answered by the code, so neither needs a change:

| | |
|---|---|
| `schema_migration` | `contract/tables.sql:105` **and** `contract/migrations/baseline.sql:105` |
| `job_run` | `contract/tables.sql:985` **and** `20260818T1400_job_run.sql` |

There is no migration-only category in this design and nothing claims one. The
equivalence test now compares relation names directly and reports **31 on each
side**, so every table in one artifact is in the other.

The live divergence between the file and a running database is **one table**, and
it runs *file ahead of chain*: `thread_extraction` is declared in `tables.sql`
and absent from staging because its migration is pending, which `db check` reports
in one line. `ONLY ON STAGING` is **0** in every object class — tables, columns,
constraints, indexes, views, sequences, types, functions, triggers. So nothing
exists on staging that the contract does not describe, in either direction.

## 1 · The design: the file is the target, the database is never an input

A generator has two possible inputs and only one is safe.

**Reading the database is wrong by construction.** It produces a migration that is
correct about the database and silent about the contract, because the contract was
never consulted. The database is the artifact that drifts; the file is the one that
gets reviewed. A generator pointed at a database launders whatever is already
there into something that looks authored.

So:

```
   read      contract/tables.sql          (the reviewed artifact)
   read      the migration chain's RESULT (built fresh, in a scratch schema)
   emit      the DDL that closes file-minus-chain
   verify    re-run the equivalence comparison ON ITS OWN OUTPUT
   refuse    exit non-zero if the two do not converge
```

**The success condition must be the test's pass condition.** If the generator's
exit code is anything other than "the chain now produces the file", it can emit a
migration that leaves them apart — which is the state it exists to prevent.

## 2 · Why a database-reading generator is unsafe even with a warning

A person doing a manual `ALTER` on staging — to unblock themselves, at speed,
correctly for that moment — would have that change **read back and promoted into
a migration, and from there into the contract**, with nobody deciding. A defect
becomes a schema change by machinery, and it arrives wearing a reviewed migration
file.

That is not a documentation problem and a warning does not fix it: the output is
indistinguishable from an intended change, and the review that would catch it is
the review the file was supposed to receive *before* the migration existed. The
same argument rules out seeding the tool from `pg_dump`.

This is why the answer is not "the tool should not exist". The mechanical work is
real, the same migration can be written by hand, and removing the tool removes
neither the work nor the hazard. Constraining its **input** removes the hazard.

## 3 · Two requirements about what it says, not what it does

**Its output header must report what happened, not what the tool is for.** A
generated file that opens with *"brings the database in line with the contract"*
asserts the design rather than the run. The header should name the two artifacts
it compared, the count of differences it found, and the verification result — so a
reader of the migration can tell whether the tool converged, from the file, without
running anything.

**Its docstring must state its input.** The failure mode this whole specification
exists to prevent is a tool documented as making `tables.sql` primary while
reading a database, because then the output asserts the docstring's version and
nobody checks the body. `tests/conftest.py` habit 9 is the general form: a helper's
name and its docstring are what later readers check *instead of* the body, so for
anything that generates a reviewed artifact, the input belongs in the first line.

## 4 · What already enforces the invariant, so the tool is not load-bearing

`tests/test_migrations.py` compares the chain's result against `tables.sql` on
five object classes, and fails when a migration changes the schema without the
file moving with it. Demonstrated rather than assumed — a probe migration widening
`document_status_ck` in the chain only:

```
FAILED test_the_chain_and_the_file_agree_on_constraints
AssertionError: in tables.sql and not reachable by migrating:
  [('document_status_ck', 'c', "CHECK ((status = ANY (ARRAY['kept'...
23 passed, 1 failed
```

So divergence fails on the first CI run after such a migration, whether it was
generated or hand-written. What that test cannot do is fire *before* the migration
is written, and it says nothing about a live database — both now stated in its own
coverage list rather than left to be discovered.

## 5 · Not proposed here

No change to `contract/tables.sql`: both tables named above are already in it, and
the artifacts agree on every class. The `document.status` vocabulary change is a
separate proposal — `docs/proposals/document-status-pending.md` — and it is
justified by rule 4 rather than by any divergence, since `write_documents`' insert
is **accepted** by a fresh build and by staging alike, and `'pending'` is refused
by both.
