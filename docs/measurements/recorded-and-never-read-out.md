# Measurements recorded and never read out: two of the four, and one of them is worse than unread

**A measurement recorded and not quoted is the same defect as one never taken.
That claim is right and it was about to be generalised from four instances, two
of which do not hold. Counted before declaring, because the risk form of rule 7
is the one that survives the rule as written.**

*Engineer 1 · 2026-08-28 · read-only. Column population from the shared
database; readers established by grep over `collect/`, `judge/`, `web/src`,
`scripts/`*

---

## 1 · The four claimed, and what each turned out to be

| column / value | written? | read out to a person? | verdict |
|---|---|---|---|
| `harvest_run.truncated_by` | yes, 421 of 1,019 rows | **no** — tests only | **holds** |
| `harvest_run.pages_fetched` / `pages_stored` | **NO — NULL on all 1,019 rows** | no | **holds, differently and worse** |
| `ExtractionRun.unclassified` | yes | **YES** — `judge/cli.py:329-345` sums it and prints it in the run summary | **does not hold** |
| `alias_match_count` | n/a — **not a column.** A function in `collect/triage/specificity.py` | called from `scripts/export_thread_contexts.py:352` and `scripts/harvest_github.py` | **does not hold** |

**So: two, not four.** And the two are not the same defect.

## 2 · `truncated_by` — the clean instance

```
421 of 1,019 rows carry a value
  query-budget      265
  result-ceiling    126
  rate-limit         30

readers   tests/test_harvest_schema.py, tests/test_blog_fetch_db.py
          nothing in judge/pages/, collect/ops/alerts.py, or web/src
```

Written correctly by `collect/ops/ledger.py`, constrained correctly by
`harvest_run_truncated_ck`, and never surfaced anywhere a person looks. The 126
`result-ceiling` rows are the exact fact that
`model-name-versus-capability-retrieval.md` §6 spent a paragraph establishing
from `items_fetched` — **the column already said it and nobody asked.**

This is the shape the claim is about, and on this one the claim is exactly right.

## 3 · `pages_fetched` — not unread. **Never written on the corpus that needed it**

```
harvest_run, all 1,019 rows, all source_id='github'
  pages_fetched   NULL on 1,019
  pages_stored    NULL on 1,019
  distinct values of pages_fetched: [None]
```

`collect/adapters/reddit.py` populates both (lines 339-340, 439-440, 616, 631).
**`collect/adapters/github.py` does not** — the only occurrence in that file is a
docstring at line 49 explaining why the columns exist: *"a re-sieve that can say
'this run stored page 1 of 4' is a re-sieve nobody over-trusts."*

Reddit has never written a `harvest_run` row. GitHub has written 1,019 and
populates neither column. **The one adapter that could fill it does not, and the
one that would has never run** — so the field is empty for a reason that reads
like an oversight and is actually two separate gaps meeting.

**Why this is worse than unread.** An unread column is recoverable: the value is
on disk and someone can query it later. This one is not — the paging depth of
1,019 completed runs is gone, and the truncation split in §6 of the comparison
doc had to be *inferred* from `items_fetched = 100` rather than read. The
inference is sound because `max_pages = 1`, but it only works while that constant
holds. Raise `max_pages` and the same figure becomes uncomputable for every run
already recorded.

**So the correct statement is not "written and never read".** It is: *a column
designed to make truncation visible was left NULL by the only adapter producing
rows, and the fact it was meant to carry had to be reconstructed from a
neighbouring column plus a source constant.*

## 4 · Why the two that do not hold matter

`unclassified` has a reader that prints it in the standard run summary.
`alias_match_count` is not a column at all and has two callers. Including them
would have taken the count from two to four and turned it into a habit.

**Four instances make a pattern; two make two.** CLAUDE.md rule 7 already records
this exact failure on this exact project — *"E1 generalised from one instance
without counting and E2 counted"* — and names the risk form specifically:

> *"Any branch older than the fix carries this defect"* is a true statement about
> what COULD be wrong, and with no population attached it reads as a statement
> about what IS.

A claim that this is *a habit rather than four instances* is that form. It has no
figure in it, so a reader checking "does this number carry its denominator" finds
nothing to check and moves on. The denominator here is **the set of columns
audited**, and it was four — chosen because they came to mind, not by enumeration.

## 5 · What would actually establish the habit

An enumeration rather than a recollection. The check is cheap and mechanical:

```
for every column in contract/tables.sql:
    written   -> does any INSERT or UPDATE in collect/ or judge/ set it?
    read      -> does any SELECT outside tests/ read it, or any page render it?
report the columns that are written and never read, with their row counts
```

30 tables. Until that runs, the honest statement is **two instances, one of them
a different defect**, and the general claim stays a hypothesis with a named way
to test it.

## 6 · What to do about the two

**`truncated_by`:** quote it. Any retrieval figure should carry the truncation
share beside it, and the column already holds the number —
*"0.404% over 1,019 runs, 126 of which hit the result ceiling."* No schema change,
no new measurement, one join.

**`pages_fetched`:** have `collect/adapters/github.py` populate it, which is E1's
lane and small. It cannot recover the 1,019 rows already written; it stops the
next 1,019 from having the same hole. And that is the argument for doing it
before the next sweep rather than after — the same argument the
`retrieval_provenance` migration was landed on, which is the one precedent here
that went the right way.
