# The migration path, used for the first time

**Two migrations applied to staging. The equivalence test gained two real
checks it could not have at chain length zero and still does not check a third.
Three tests and one production function turned out to be condition B — assertions
that could not fail because the condition they named could not arise.**

*Engineer 1 · staging · 2026-08-18*

---

## 1 · What the equivalence test gains, asked before running

`baseline.sql` is a comment-stripped copy of `contract/tables.sql` — verified
identical modulo comments and whitespace. So at chain length zero the test
asserted:

```
apply(tables.sql)  ==  apply(baseline.sql)
```

Two copies of one DDL still agreeing. **Real drift protection and not trivial** —
that is the "second description of the schema" defect `migrate.py` was written
against — but it had never executed a migration statement.

**What length one adds:**

| | at length 0 | at length ≥1 |
|---|---|---|
| baseline and file agree | ✅ | ✅ |
| a migration's SQL is ever **executed** | ❌ never | ✅ |
| baseline **+ delta** reaches the file | ❌ vacuous | ✅ |
| `a migration creates what tables.sql does not describe` can fire | ❌ impossible | ✅ |
| migrations compose **in order** | ❌ | ❌ still — needs two, and now has them |

So the honest answer is **two real gains, not "nothing new"** — and one gap that
closed only because the vocabulary error in §3 forced a second migration.

The `only_chain` assertion is the interesting one: at length zero the chain *is*
the baseline, so "a migration creates what the file does not describe" could
never fire under any circumstances. It was an assertion about the empty set.

---

## 2 · Condition B, in the test suite

Adding the first migration broke three assertions, all of the same shape.

**`test_a_database_with_the_ledger_and_nothing_pending_is_current`** applied
`baseline.sql` and asserted `is_current`. True only while `discover()` returned
nothing. Corrected to apply the whole chain, plus a new test asserting the state
it used to claim was fine — a database at the baseline with work outstanding
must report as *behind*, and until today nothing could tell the difference.

**`test_a_database_predating_the_ledger_is_not_reported_as_current`** failed on
`describe()`, which exposed a real defect in production code:

```python
if self.pending_filenames:
    return f"... PENDING: ..."      # returned here
if not self.ledger_present:
    return "NO LEDGER — ..."        # unreachable whenever anything was pending
```

**A pre-ledger database with work to do reported only the work.** The schema
difference that `schema_migration` itself represents went unmentioned. It could
not surface while `pending` was always empty. `describe()` now says both.

That is the same shape as `finished_at IS NULL` versus `outcome = 'error'` on
`job_run`: two facts, one reader flattening them into one.

---

## 3 · The pre-ledger decision, made before it was discovered

**`db init` stamps the ledger at head.** A schema built from `tables.sql` is by
definition at the head of the chain — that is the entire content of the
equivalence test — so the migrations have nothing left to do and the ledger
should say so. Without it, the first migration breaks *every new database*: the
file creates `job_run`, then `db check` reports the migration pending, then
`db migrate` runs `CREATE TABLE job_run` against a table that exists.

**And a migration whose objects already exist is REFUSED, not recorded.**

This is where I came down against the lean. Recording-as-applied is safe only if
the shape was compared, and comparing it needs the equivalence machinery — build
both schemas, diff them — which is a test-time operation, not something to run
inside a migration. So the legitimate case is *removed* rather than *detected*:
`db init` is the only situation where objects legitimately pre-exist with known
provenance, and it now stamps. Anything else reaching that code has a schema
nobody can account for.

`SchemaDiverged` names the objects and says why recording is refused:

> That the objects exist does not mean they match what `contract/tables.sql`
> describes, and recording a migration whose shape nobody compared is how two
> databases quietly stop agreeing.

**What distinguishes "already correct" from "different in a way nobody
noticed": nothing available at migration time.** That is the finding, and the
response is to make the ambiguous case unreachable rather than to guess at it.

---

## 4 · What staging did

`schema_migration` existed and was empty — so staging was *not* pre-ledger in
the sense I had assumed. The table is in `tables.sql` and `db init` created it;
what it lacked was rows.

```
db check    →  0 applied, 1 PENDING: 20260818T1400_job_run.sql   exit 1
db migrate  →  applied 20260818T1400_job_run.sql
db migrate  →  current — 1 applied, none pending        (idempotent)
db check    →  current — 1 applied, none pending        exit 0
```

Then the second migration, which is an `ALTER`:

```
db migrate  →  applied 20260818T1520_job_run_outcome_vocabulary.sql
            →  current — 2 applied, none pending
```

Both commands work. Nine columns, three constraints, three indexes, verified
against the file.

### The second migration exists because I got the first one wrong

`job_run.outcome`'s CHECK said `'ok', 'refused', 'failed'`. `collect/ops/chain.py`
has used `OK / REFUSED / ERROR` since it was written. A writer bridging the two
would have translated `error` to `failed` on the way in and back on the way
out — **one concept, two vocabularies, drifting from the day it was written.**

The schema moved rather than the code: the chain's constants are older and more
used, and `error` is the more accurate word — a stage that raised is not a stage
that failed a check.

Worth having: the first migration proved the path on an object that did not
exist. **The second alters one that does**, which is the case neither the first
migration nor the length-zero test could reach.

---

## 5 · Condition B once `job_run` exists

The three findings behind this table, and whether the ledger would now catch
them:

| finding | caught by `job_run`? |
|---|---|
| `in_window` at its schema default on 340 rows | **partly.** `last_run('recompute-window')` returning None answers "has it ever run here". It does **not** catch a column at its default while the stage *has* run — that needed comparing stored against computed. |
| `mark_swept` residue on one row | **no, and it does not need to be.** `assert_no_phantom_sweeps` already covers it, and it is cheap for the same reason `job_run` is: a contradiction is checkable. |
| three writers greping as wired | **yes, for stages.** `last_run(stage)` is the query. **No, for functions** — `write_authors` is not a chain stage, and nothing will give it a row until something calls it. |

**So the ledger is worth less than the three findings suggest, and it is worth
knowing which part.** It converts *"has this stage ever run against this
database"* from an investigation into a query. It does not convert *"has this
function ever been called"*, because a function with no caller has nothing to
write a row.

That residual is the honest bound: `job_run` covers the twelve chain stages and
nothing else. `write_authors` and `mark_swept` remain uncovered, and the thing
that would cover them is a caller — which is a build, not a ledger.

Measured on the first real run: **twelve rows, one per stage, zero unfinished.**
Every refusal recorded, including the eight stages the chain refuses before they
run — the first wiring recorded only stages refused *by their own code*, so
`assemble-flatten` had no row while `poll-registry` had one saying `refused`.
Both are "we looked at this stage tonight and it produced nothing".

---

## 6 · The filtering is done by choosing where to look

Recorded here because the numbers are fresh and it deserves stating plainly
rather than being inferred from a table.

**19.5 of B's 19.9 points are subject matter.** On the 26-subreddit unfiltered
sample, survival is 19.9%. On a general-technical control — programming, webdev,
devops, rust, golang, sysadmin, people writing about software and mostly not
about models — the same pipeline, the same population fingerprint, the same
gates, survive at **0.4%**.

So **almost all of the filtering this pipeline appears to do is done by choosing
where to look, not by the gates.** The gates remove junk from a population that
was already selected for being about AI. Pointed at technically-literate prose
with no AI selection, they pass four documents in a thousand.

Two consequences worth carrying:

- **The subreddit list is not a detail of the sweep, it is most of the
  instrument.** A change to it moves the survival figure far more than any gate
  will. It belongs in `contract/` for that reason and not merely for tidiness.
- **A survival figure without its population is close to meaningless**, and
  this is the strongest statement of that yet: the same code gives 78.0%, 19.9%
  and 0.4% on three corpora. Rule 7 already says a figure travels with its
  denominator; this is what the spread actually is.
