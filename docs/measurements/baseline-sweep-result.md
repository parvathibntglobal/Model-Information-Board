# The sweep, against the pre-registration: 52 documents, and `context.effective_window` returned one

**Run 2, authenticated, 2026-08-24 10:11:58–10:45 UTC.** Reported against
`baseline-sweep-preregistration.md`, whose thresholds were committed before
either run.

*Engineer 1*

---

## 1 · The report, in the fixed shape

```
sweep    : 7 model(s) swept, 34 unreached, 459 of 2144 planned request(s)
           issued against a cap of 900 request(s) / 35 minute(s)
           — STOPPED ON WALL CLOCK
           23,160 candidate(s), 116 kept, 52 document(s) stored
           harvest_run: 459 opened, 459 closed
           last_swept_at set on 6 model(s)
           sieve: signal  302/23,160 ( 1.3%)
                  subject 15,106/23,160 (65.2%)
                  topic   18,011/23,160 (77.8%)
EXCLUDED : 1 — z-ai/glm-4.5, every alias window closed. Retired, correctly not
           swept, and correctly not silent about it
UNREACHED: 34 seated models the budget did not cover
```

**Wall clock: 33m28s at the last check, stopped on the ceiling rather than past
it.** Run 1 overran to 41m51s; the per-request clock check landed between them
and this is it working.

**459 opened, 459 closed, 0 left open.** Run 1 left 4 open because I killed it —
the two-phase ledger distinguishing "killed" from "errored", both times.

## 2 · Q1 — does `harvest_run_id` hold at volume?

**Yes. 52 of 52, and the constraint is doing the work rather than the writer.**

```
run_recorded rows                52
  with a NULL harvest_run_id      0
  with a dangling foreign key     0
```

`document_retrieval_provenance_agrees_ck` makes the first impossible and
`document_harvest_run_fk` makes the second impossible, so this is a check that
the constraints are live rather than a hope about the writer. At 2 documents that
was suggestive; at 52 it is the answer.

## 3 · The retrieval-provenance join, across the whole corpus

**This is what Engineer 2 asked for, and it now exists.**

| source | state | documents | carry a run id |
|---|---|---|---|
| github | `run_recorded` | **52** | **52** |
| github | `not_recorded` | 28 | 0 |
| blog | `not_recorded` | 120 | 0 |
| reddit | `not_recorded` | 196 | 0 |

And the join it enables — *which query produced this document* — which no query
could answer four hours ago:

```
claude-4.8 SEARCH/REPLACE type:issue      3 docs   (that query fetched 153)
claude-4.8 throughput type:issue          3 docs   (fetched 300)
opus-4.8 SEARCH/REPLACE type:issue        3 docs   (fetched 234)
claude-4.7 summarizing type:issue         2 docs   (fetched 112)
claude-opus-5 SEARCH/REPLACE type:issue   2 docs   (fetched 200)
```

**One honest gap: `no_run_for_source` has 0 rows.** Blog and reddit documents all
read `not_recorded`, which is correct — they predate the column, and no blog or
reddit sweep has run since it landed. The writers type `no_run_for_source`, so
the first blog or reddit sweep will populate it. **Until then the state is
implemented and unexercised**, and that distinction is exactly the one the column
exists to preserve, so it should not be reported as though all three states have
been seen.

## 4 · Q2 — `context.effective_window`, against the threshold as written

```
runs                60
candidates       3,346
kept                 2
DOCUMENTS STORED     1
```

**The entry has returned a document. It had never returned one before.**

```
https://github.com/matouskozak/arxiv-digest/issues/175
   query = claude-sonnet-4.5 recall type:issue   (that query fetched 100)
```

The pre-registered table, and the row that fired:

| result | reading | |
|---|---|---|
| **>= 1 stored document** | *"the query works and was coverage-limited. 3 models to 40 was the constraint, and the entry earns its place"* | **← this one** |
| >= 3 stored | it works and matters | not reached |
| 0 candidates kept, again | the constraint is the query, not the coverage | **did not fire** |
| candidates kept, 0 stored | a fetch or write defect | fired in run 1, and was one |

**And the pre-registration's own qualifier applies exactly:**

> *"One document is enough to change the reading, and it is not enough to call it
> working. A single document distinguishes 'the query can match real text' from
> 'it cannot', which is the question. It does not establish that the entry pays
> for 2 of 18 daily entries' worth of requests."*

So: **the constraint was not the query.** That hypothesis is now retired — I
committed to it hard, and it did not hold. What the entry costs against what it
returns is a separate question and 1 document does not settle it.

**The document came from a newly-nameable model.** `claude-sonnet-4.5` was not
among the three models the 2026-08-20 sweep could name. That is the coverage
argument landing rather than being asserted — the entry did not start working
because the query changed, it started working because a model it could ask about
became askable.

**With one caveat that is mine to state rather than leave implied: only 7 of 40
models were swept.** The pre-registration said "40 models named instead of 3".
The sweep reached 7 before the clock stopped it, so the tested change is 3 → 7,
not 3 → 40. The result stands — a document is a document — but the *strength* of
the coverage reading is a seventh of what was pre-registered, and 34 models
remain unreached.

## 5 · What was comparable, and what moved

Pre-registration §1 committed to one figure being comparable across sweeps — the
per-query sieve pass rate, *"because that is a property of the sieve against
retrieved text rather than of the roster."*

```
2026-08-20 harness      6 kept /  2,887 candidates = 0.21%
run 1, anonymous       59 kept / 18,801 candidates = 0.31%
run 2, authenticated  116 kept / 23,160 candidates = 0.50%
```

**It moved, and it more than doubled from the harness run.** That is the figure
§1 said would be worth finding a reason for. Two candidate reasons, neither
tested: the roster is different (7 models rather than 3, and different ones), or
retrieval quality differs with the identity. I am not going to pick between them
from three points.

**The group rates are the more useful new number**, and they have never been
reported before:

```
subject  65.2%   the alias is present in the text
topic    77.8%   the capability vocabulary is present
signal    1.3%   the claim vocabulary is present
```

**The sieve is not failing to find models, and it is not failing to find topics.
It is failing on `signal` by a factor of fifty.** 302 of 23,160 documents contain
one of the hand-written signal phrases. That is a direct, quantified restatement
of the polarity and vocabulary findings from this week, arriving from retrieval
instead of from extraction: *"loses recall", "forgets the middle", "falls apart"*
are how somebody writes in an essay, not how they title a GitHub issue.

**This is the first number that localises the constraint inside the sieve rather
than around it**, and it is the thing I would take next.

## 6 · What this sweep is and is not

**It is not yet the baseline.** 7 of 40 models, 459 of 2,144 planned requests,
34 unreached. What it is: the first sweep in this project that stored documents
carrying their own provenance, the first per-model coverage record, and the first
measurement of where the sieve actually loses candidates.

**The baseline needs the remaining 33 models**, which is 2–3 more nights at the
900-request cap — and the resume ordering now makes that work rather than
re-covering the same alphabetical prefix. Six models carry a `last_swept_at` from
this run and go to the back of the next night's queue.

**One verification worth naming:** `anthropic/claude-sonnet-4.5` was cut short by
the clock mid-plan. It appears in `UNREACHED`, carries **no** `last_swept_at` —
and its completed queries still stored documents, including the
`context.effective_window` one. That is the rule-6 branch behaving exactly as
designed: a partially-swept model keeps no coverage date, and the evidence it did
produce is kept.
