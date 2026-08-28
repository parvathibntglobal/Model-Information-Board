# `harvest_run` has been waiting for a reader since it was built, and your panel is the first thing that wants it

**Not a complaint about the panel. A match.** Your admin panel asks the two
questions `harvest_run` was built to answer, and it is answering the second from
the coarser of the two ledgers because the finer one has never had a caller.

*Engineer 1 · 2026-08-28*

---

## 1 · The state of the table

```
harvest_run    1,019 rows, 15 columns
               10 of the 15 are written and read by NOTHING

  source_id  query_key  items_fetched  items_kept  http_errors
  exhausted  truncated_by  pages_fetched  pages_stored  sieve_pass_rate
```

Nothing in `collect/`, `judge/`, `scripts/` or `web/src` selects one column of
it. Full audit: `docs/measurements/column-audit-306-columns.md`, corrected
figures in PR #166.

**Every retrieval figure in the comparison going to the team came out of this
table by ad-hoc query** — the pooled 0.404%, the per-night split, the truncation
share. None of it is reachable from a page.

## 2 · Where your panel and this table meet, exactly

`judge/pages/pipeline_status.py` states its two questions:

> 1. WHAT IS IN EACH STAGE now — row counts grouped by the status column that
>    partitions that stage's output
> 2. **WHAT HAPPENED ON THE LAST RUN — the `job_run` ledger, one row per stage**

**`job_run` is one row per STAGE. `harvest_run` is one row per QUERY.** They are
the same ledger at two grains, and the finer one carries what the coarser cannot:

```
job_run        did sweep-github run, when, and did it finish
harvest_run    what was searched for, how many candidates came back, how many
               survived the sieve, and whether the platform cut us off
```

Question 2 is already the right question. It is being answered at the grain that
says *whether* a sweep happened rather than *what it retrieved*.

## 3 · The one figure your panel says it cannot show — and this table has it

Your docstring is explicit and correct about a real limit:

> What this panel deliberately CANNOT show, and says so rather than implying
> zero: **attrition at extract and vet.** A failed quote verification, a
> sarcastic claim, a promotional rejection are LOGGED and never written as rows
> — `CONSTRAINT claim_verified_ck CHECK (quote_verified = true)` forbids the
> row. So those stages show survivors and carry a caveat.

**Attrition at RETRIEVAL is not in that category.** It is written, it is
counted, and it is 1,019 rows deep:

```
44,848 candidates  ->  181 kept
```

That is the one attrition figure in the pipeline that does not need a caveat
about discards nobody recorded, and it is the only one currently invisible for
the opposite reason — the rows exist and nothing reads them.

## 4 · Why it fits your panel's rules rather than straining them

Stated per rule, because that is how the panel is built:

- **Rule 3, nothing synthesised.** `items_fetched` and `items_kept` are counts.
  `181 / 44,848` is a ratio of two counted things, which is what the panel
  already does for status buckets.
- **Rule 7, a figure travels with its denominator.** This is the part that needs
  you rather than me. The pooled rate must be shown with **321 of 1,019 runs hit
  the page-1 result ceiling** beside it, because `max_pages = 1` makes every rate
  a top-100-by-relevance figure and those 321 runs supply 51% of the yield.
  `truncated_by = 'result-ceiling'` on 126 rows is where that lives.
- **Rule 4, silence is not criticism.** `harvest_run` has **zero rows for reddit
  and blog**. That must render as NOT-YET-SWEPT, exactly as your `measured` flag
  already draws that line for a stage with no rows — never as a zero yield.
- **Rule 6, NULL is a third state.** `sieve_pass_rate` is NULL on 124 of 1,019
  and `pages_fetched` is NULL on all 1,019. Both are third states and the second
  is a defect (§5), not an absence.

## 5 · Two things to know before reading it, because they would mislead a page

**`pages_fetched` and `pages_stored` are NULL on all 1,019 rows.** Not unread —
never written. `collect/adapters/reddit.py` populates them and has never written
a `harvest_run` row; `collect/adapters/github.py` has written 1,019 and populates
neither. **That is mine and I will fix the writer**; until then a panel reading
those columns would render "0 pages" for every run.

**Do not average `sieve_pass_rate`.** It is a per-run ratio, so `avg()` weights a
run that fetched 2 candidates like one that fetched 200, and 380 of 1,019 runs
fetched nothing at all. `avg()` returns 0.0036 where the pooled rate is 0.00404 —
and a misreading of that column by one decimal place is where the retracted "3.4%
against 0.15%" figure came from. The pooled form is
`sum(items_kept) / sum(items_fetched)`.

## 6 · What I am proposing

**Nothing in `judge/`, and no schema change.** The table is `collect/`'s to write
and yours to read, exactly as `filtered.py` reads `document.status` — a SQL read
across the boundary, never an import.

What I am asking is that **retrieval gets a stage row in the panel**, at the
query grain, whenever you next open that file. The columns are there, the rules
you built it under all hold, and the two caveats in §5 are the whole briefing.

What I will do on my side, unasked:

```
github.py populates pages_fetched / pages_stored     E1, small, before the next
                                                     sweep so the next 1,019 rows
                                                     do not have the same hole
a `quota` value on truncated_by                      proposed in PR #161
```

**The ledger has been correct and unread since it was built.** A measurement
recorded and never quoted is the same defect as one never taken, and this one is
1,019 rows of it — which is a better argument for reading it than anything I
could say about the columns.
