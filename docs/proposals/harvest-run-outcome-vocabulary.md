# `harvest_run.outcome`: one column name, two vocabularies, and the 304 is still homeless

**Proposed, not applied. `contract/` is shared.**

*Engineer 1 · 2026-08-19 · for Engineer 2's sight*

---

## 0 · The column landed and closed one of the two gaps it was read as closing

`dab9d41` added `harvest_run.outcome` with `job_run`'s vocabulary:

```sql
CONSTRAINT harvest_run_outcome_ck
  CHECK (outcome IS NULL OR outcome IN ('ok', 'refused', 'error')),
CONSTRAINT harvest_run_finish_ck
  CHECK ((finished_at IS NULL) = (outcome IS NULL))
```

That was the right call for the gap `docs/proposals/harvest-run-outcome.md` §7
tabulated — **refused-by-the-gate against ran-and-got-nothing** — and the
reasoning for reusing `job_run`'s words rather than minting a second set is good
and stands: one concept, one word, and that table already spent a migration
replacing `failed`.

**A different gap was also being tracked under the same column name, and it did
not close.** `collect/adapters/blog/fetch.py:82` declares

```python
Outcome = Literal["fetched", "not-modified", "robots-blocked", "error"]
```

and its docstring calls that set "the closed set proposed for
`harvest_run.outcome`". `github.py:559` says the same in `outcome_of`. So two
files describe a four-value **fetch disposition** as the proposed contents of a
column that landed holding a three-value **job verdict**.

`error` is the only word in both. It is also the only one that means the same
thing in both.

## 1 · What each vocabulary is about

They are not competing names for one concept, which is why neither is wrong:

| | question it answers | values |
|---|---|---|
| `job_run.outcome`, and now `harvest_run.outcome` | **how did the run conclude?** | `ok` · `refused` · `error` |
| `blog/fetch.py:Outcome` | **what did the fetch do?** | `fetched` · `not-modified` · `robots-blocked` · `error` |

A 304 concluded fine. It is `ok`. So is a 200 that returned a feed we parsed to
zero entries. **Both are `ok` with `items_fetched = 0`, and that is FR-10's
collision exactly as it stood before the column existed.**

## 2 · Counted, not asserted

`tests/test_blog_fetch_db.py::test_a_304_and_a_dead_parser_are_the_same_row`
writes both rows to Postgres and compares them as the database sees them.
`outcome` is now inside its `SELECT` list. The two rows are equal.

Population: 2 rows, from 2 sweeps of 2 feeds, on the schema built from
`contract/tables.sql` at `7f75ed6` — not a sample of anything, and not a claim
about the other adapters, which are unmeasured here.

Scope of the naming claim, so it is not read wider than it was checked: 2 of the
3 adapters name a four-value disposition as the proposal for this column
(`blog/fetch.py:82`, `github.py:563`). `reddit.py` carries an `outcome` key
homeless without declaring a value set.

## 3 · What this cost, and it was not the 304

The column landing without this reconciled broke CI, and the shape of the break
is worth recording because the obvious fix was the wrong one.

`tests/test_blog_fetch_db.py` held a local `insert_harvest_run` that popped
`outcome` and inserted the rest, including `finished_at`. Against the new
`harvest_run_finish_ck` that is a `CheckViolation`, and the file's own canary
`test_outcome_has_no_column_yet` fired alongside it with the instruction **"stop
popping it in insert_harvest_run and write it, then delete this test"**.

Following that instruction writes `'fetched'` into the column and trades
`harvest_run_finish_ck` for `harvest_run_outcome_ck`. The canary was written
before the vocabulary question existed, so it named the mechanical half of the
fix and could not name the half that matters. Three tests, one file, and the
same three on `main` at `7f75ed6`.

## 4 · Proposed

**Add `not-modified` to `harvest_run_outcome_ck`.** One value, one statement:

```sql
ALTER TABLE harvest_run DROP CONSTRAINT harvest_run_outcome_ck;
ALTER TABLE harvest_run ADD CONSTRAINT harvest_run_outcome_ck
  CHECK (outcome IS NULL OR outcome IN ('ok', 'not-modified', 'refused', 'error'));
```

`robots-blocked` needs nothing: it maps onto `refused`, which is what `refused`
already means at `ledger.py:161` for the terms gate, and robots is the same kind
of no — we chose not to fetch. Folding it in loses nothing, because
`robots_blocked` is separately counted on the run object.

`not-modified` is the one that cannot fold. It is the difference between a
working conditional GET and a dead parser, and it is the difference FR-10's
acceptance test turns on.

### Why a value and not a column

A `not_modified boolean` would work and should not be taken. `outcome` is
already the column for "which of these mutually-exclusive things happened", a
second boolean makes two places to look, and a NULL in it would be a rule-6
hazard — absent reading as `false` reading as "was modified".

### Why this does not reintroduce the vocabulary split

`ok | not-modified | refused | error` is still one set of words for one concept,
and it stays a superset relationship with `job_run`'s three rather than a
translation layer: every `job_run` value is a `harvest_run` value. A sweep is a
job that can additionally have been a no-op, and no other job kind can.

**It does diverge from `job_run`, which is a real cost** and the thing worth
arguing about. The alternative is to accept that `harvest_run.outcome` cannot
express a 304 and record the disposition elsewhere — which is a fifth homeless
field, and `_PROPOSED_NOT_IN_SCHEMA` was just emptied.

## 5 · Until it lands

`tests/test_blog_fetch_db.py` maps disposition to verdict at the boundary, in
`DISPOSITION_TO_VERDICT`, with `fetched` and `not-modified` both going to `ok`.
The mapping lives in the test rather than in `collect/` deliberately: picking it
is this decision, and a mapping in the writer would look like the decision
having been taken.

Two tests guard it:

- `test_every_disposition_has_a_verdict` — the mapping's domain is
  `get_args(Outcome)` exactly, so a fifth disposition added upstream fails here
  rather than at an `INSERT`.
- `test_outcome_landed_and_cannot_say_unchanged` — reads
  `pg_get_constraintdef` from the live catalog and **fails the day
  `not-modified` is accepted**, pointing at the two places that then change.

So the gap is asserted rather than commented, and the fix has a test that goes
red when it is applied instead of a note nobody greps for. Rule 4 at the schema
level: an unclosed gap that nothing re-checks reads as closed.

## 6 · Also stale, not fixed here

`collect/ops/ledger.py:156` still opens **"`harvest_run` has no `outcome`
column - the eleven are…"** and enumerates them. The column exists; the
enumeration is now twelve-plus-four and the sentence is false. `close_harvest_run`
below it is correct and validates the vocabulary properly, so this is a comment
that has gone stale rather than behaviour that is wrong — but it is the
load-bearing kind, because it is aimed at exactly the reader who arrives at this
question next.

Left out of the CI fix on purpose: that branch touches one test file and this
document, and a reviewer reading a red-CI fix should not have to decide whether a
`collect/` comment rewrite is part of it.

## 7 · Not proposed

**No change to `harvest_run_finish_ck`.** It did what Engineer 2 argued it would
— it caught a writer that set `finished_at` without a verdict, on the first
commit after it landed, and the writer it caught was a test helper duplicating
the insert rather than calling `close_harvest_run`. The constraint is the reason
this was three failing tests instead of a column of silent NULLs.

**No change to `job_run_outcome_ck`.** `job_run` has no 304.

**No fifth `truncated_by` value.** Same trap the writer already documents: a 304
was not cut short.
