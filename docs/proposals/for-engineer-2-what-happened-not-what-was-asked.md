# Four traceability writers, led by the one that says nothing was found

**Proposed. `contract/` and `judge/` unchanged by this document.**

*Engineer 1 · 2026-08-24*

Your question was what an empty page means. The honest answer today is that we
cannot tell you, because **the pipeline records what it stored and almost nothing
about what it looked at and discarded.** Four writers close that, and they are
ordered here by how much of your question each one answers — not by how easy
each is.

**And none of them needs model-first retrieval.** That was your other proposal,
and it answers the same question by changing what goes out. These change what
gets written down, so they cost no requests, no budget and no change to the sweep
shape. If you want model-first retrieval for its own sake that is a separate
argument; it is not needed for this.

---

## 1 · `mention_unresolvable` — what happened, not what was asked

**Lead item, because this population is your answer.**

```
documents stored                                   343
documents that produced NO claim                   330    (96.2%)
   blog 109      github 27      reddit 194
documents that produced a claim                     13    -> 23 claims

blog claims extracted                              140
   resolved to a seated model                        6
   resolved to nothing                             134    (95.7%)
```

**330 of 343 documents were retrieved, stored, read, and left no row anywhere
that says what happened to them.** A model that was searched for and produced
nothing currently leaves no trace at all, and that is most of what an empty page
means. Not "nobody discussed this" — *"we looked, something came back, and we
cannot tell you what became of it."*

The blog half is sharper because we know why: **134 of 140 claims named something
no registry can resolve.** 96 subjects carried no version at all, 26 were family
words excluded by design, 12 were versioned and unseated. That is a finding with
a shape, and today it renders as an absence indistinguishable from silence —
rule 4 at the largest scale it covers.

**Proposed shape:** a `coverage_gap` kind, not a new column.
`docs/proposals/coverage-gap-unresolvable-mentions.md` already proposes extending
that CHECK for route-unresolvable mentions, and this is the same operation on the
same table: one more kind, counted per surface, with the reason it did not
resolve. Reusing it means the coverage page learns about this the same way it
learns about the other four.

**Why per surface and not per document:** the surface is what a person wrote.
`claude 5`, unresolvable, 11 mentions is a fact somebody can act on — it names a
real gap and a real ambiguity. `document 7f3a, no claim` is not.

## 2 · `triage_verdict` — a column that exists and has never been written

**Found while measuring the first, and cheaper than items 1 and 3 in lane terms
but not in hours — see below, where I correct my own estimate.**

```sql
SELECT triage_verdict, count(*) FROM document GROUP BY 1;
-- (NULL, 343)
```

`document.triage_verdict` and `document.filter_reasons` are **already in the
schema**. Triage has run — over the 195 comments, over the blog corpus — and
**every verdict was computed, used, and thrown away.** So the question *"did this
document fail triage, or was it never triaged?"* has no answer in the database,
and those are opposite findings: one is a filter working, the other is a stage
that never reached it.

**Cost: no contract change — but larger than a write, and I had this wrong when
I first drafted this section.** I wrote "a write at the triage call site" and
then went to make it. **There is no triage call site.**

```python
# collect/ops/chain.py:433
Stage("triage", run=None, needs=("assemble-flatten",),
      starves="document.status and document.specificity_score, which no "
              "writer sets today — so triage survival has neither a "
              "numerator nor a denominator")
```

`run=None`. The stage is declared, its starvation is documented, and it has no
runner. The only `triage` CLI subcommand is `population`, which prints the
surface set and writes nothing. The triage I have run over the 195 comments and
the blog corpus was **ad-hoc script work that never touched the database.**

So this is: a stage runner, persistence for `triage_verdict`, `filter_reasons`,
`status` and `specificity_score`, and tests. The pieces it composes already exist
— `collect/triage/gates.py` and `specificity.py` are written and tested. **Still
no contract change and still entirely my lane**, but it is a day's work rather
than a line, and `ops.alerts` line 113 is already carrying the consequence:
*"no triage gate sets document.status, so survival has no numerator"*.

Correcting it here rather than quietly, because the estimate is what you would
have scheduled against.

## 3 · The run reference — what was asked

`document.harvest_run_id` **does not exist as a column**, so the backfill is 0 of
343 rather than 0 of 253, and provenance is lost for everything already stored.

This tells you what was asked: which query, which alias, which capability entry
retrieved this document. That is the join that answers *"is this page empty
because we never asked, or because we asked and got nothing?"* — the other half
of item 1.

**Two things to decide rather than assume:**

**It is GitHub-only today.** `harvest_run` holds 153 rows and **all 153 are
`source_id = 'github'`.** Reddit and blog sweeps write no run rows at all, so
blog and reddit documents would carry NULL — correctly, under rule 6, but it
means this column answers the question for 27 of 343 documents plus whatever
GitHub sweeps add. It is not a general provenance fix and should not be sold as
one.

**A document has more than one run.** 3,776 candidates reduced to 25 documents
means documents were returned by many queries. A single FK can only record *first
seen by*, which is a defensible choice and must be **named** as that rather than
read as *"the query that found this"*. If you want all of them it is a join
table, which is a bigger change.

## 4 · Searched and returned nothing

`harvest_run` already records this per query — `items_fetched = 0` — and
**nothing joins it to a model.** The 2026-08-20 sweep: 153 runs, 2,887 items
fetched, **6 kept**, sieve pass rate 0.00 to 0.03. So "we asked about this model
and the platform had nothing" is already in the database and unreachable from a
model page.

This needs no new column either — it needs the model page to be able to read
`harvest_run` by alias. Cheapest as a view.

---

## What each costs

| | change | lane |
|---|---|---|
| 2 · `triage_verdict` | a stage runner + persistence. Columns exist, no contract change | **mine, no sign-off — but a day, not a line** |
| 4 · searched-nothing | a view over `harvest_run` | mine |
| 1 · `mention_unresolvable` | one `coverage_gap` kind — a CHECK alteration | **`contract/`, yours to approve** |
| 3 · run reference | one column + one migration + one writer + two call sites | **`contract/`, yours to approve** |

**Items 1 and 3 are small implementations in a shared file**, which is why they
are proposals and not commits. Item 3's exact DDL and call sites are in
`docs/measurements/three-premises-and-the-baseline.md` if you want to check the
size before agreeing to it.

## On the timing, since a sweep is about to run

The sweep about to go out is the first corpus that could carry a run reference
from the start. **I am not holding it for item 3**, and the reason is not the
implementation size — it is one column and one call site, which is small enough
that waiting would be right if waiting were bounded. It is not: item 3 lands in
`contract/`, and a cross-lane sign-off has no deadline I control.

**What makes that acceptable rather than merely convenient:** `harvest_run` rows
*will* exist for this sweep, written two-phase before each query. So the
provenance is not destroyed by running first — it is recoverable later for
GitHub, by matching `harvest_run.query_key` and time against
`document.fetched_at`, imperfectly but far better than for the existing 27.

**What is genuinely lost by running first** is exactness: a document retrieved by
six queries cannot be attributed to the first one after the fact. If you want
that, say so and the sweep waits — it is your call, not mine, because the column
is in your half of the contract.

**Item 2 I am landing next**, since it needs nobody's permission and the
sweep will produce documents whose triage verdicts would otherwise be discarded
exactly as the previous 343 were.
