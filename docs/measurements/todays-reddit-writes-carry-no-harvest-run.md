# Today's 220 Reddit documents carry no `harvest_run`, and the gap they join is 1,492 not 344

**A note, not a complaint.** The rows are fine, the writer did nothing wrong that
a rule forbids, and `not_recorded` is the honest value for a path nobody
instrumented. This is here because the gap is now large enough that its size is
itself the finding, and because the figure the gap is usually quoted at is stale.

*Engineer 1 · 2026-08-31, written the day it was noticed.*

---

## What was seen

220 Reddit documents landed on staging today — 81 at 04:00 UTC and 139 at 05:00,
the second batch arriving mid-session while a GitHub sweep was running from this
machine.

```
  reddit documents fetched 2026-08-31        220
  of those, retrieval_provenance             not_recorded   220
                                             run_recorded     0
  harvest_run rows opened by them              0
```

**They are invisible in the ledger.** The only way to identify them is
`fetched_at`, which is a fact about when we stored bytes rather than about what
retrieved them. `harvest_run_id` landed specifically so a document can name the
query that found it — *"the join that separates 'this page is empty because we
never asked' from 'we asked and got nothing'"*, per `contract/tables.sql`.

## ⚠ The attribution above is wrong, and Engineer 2's reply is why

**Recorded 2026-08-31, after she answered.** I wrote this as though one other
person had written on 2026-08-31. There were **two**, and neither batch is
hers in the way I assumed:

- **The three Reddit thread_contexts were not hers.**
- **Her per-model fetch stored roughly 13 claims at 11:48 IST, plus 2 earlier**,
  and neither was announced.

So the day had **two unannounced writers, not one**, and I was one of them — the
926 NULL-specificity rows in the last section are mine and I did not announce
them either. The convention this note leans on is *"before a staging write
session, say so"*, and it was broken from both sides on the same afternoon.

**The re-baseline was the right call for both.** Every figure in this session
that was taken before those writes and quoted after them needed re-deriving
rather than carrying, and that is what happened — three times for the extraction
projection alone. The lesson is not "announce better"; it is that a measurement
against a shared database has a denominator that moves, and re-deriving is
cheaper than the argument about who moved it.

I am leaving the original text below rather than editing it, because what it got
wrong is the interesting part: I identified the writes correctly and attributed
them to a single person by elimination, which is exactly the reasoning
`harvest_run` exists to make unnecessary.

## No collision

Checked, because two of us were writing the same afternoon and the convention
says to say so:

```
  their writes        reddit only
  mine                github only - 148 comments, 30 forked thread_contexts,
                      and the multi-shape sweep's documents
  shared rows         none. Both paths are ON CONFLICT (source, external_id)
                      DO NOTHING, and the sources do not overlap.
  claim / cell        199 / 96, untouched by either of us
```

What did move under me is measurement, not data: `thread_context` went
1,725 → 1,760 (30 mine, 5 theirs), so the "1,510 readable unread threads" figure
in this morning's extraction costing is stale. Restated in
`docs/measurements/comments-shapes-and-the-legacy-weights.md` §4 rather than
carried forward.

## The gap is 1,492 on Reddit, not 344

**The figure this is usually waved at has not been re-counted in a while.**
`not_recorded` across the whole corpus today:

```
  reddit    1,492      of 2,999 reddit documents
  github      176      of 1,200
  blog        120      of 121
  ---------------------
  total     1,788      of 4,320
```

Reddit's 1,492, by the day it was fetched:

```
  2026-08-20        6
  2026-08-24      190
  2026-08-27      853     <- the batch that had asserted `no_run_for_source`
  2026-08-28      223
  2026-08-31      220     <- today
```

So today's 220 is **15% of the Reddit gap and 12% of the whole**, and it joins a
gap that grew by 1,148 in the last four days. That is the part worth knowing: it
is not a rounding error on a settled number, it is a gap that is currently
growing faster than anything is closing it.

**Nothing here is a rule violation.** `retrieval_provenance` defaults to
`not_recorded` precisely so an uninstrumented writer under-claims rather than
asserting something false, and `collect/adapters/reddit_write.py` makes the
caller type the value rather than inheriting one — which is the fix that landed
after 853 rows claimed `no_run_for_source` on a path that had issued queries. The
default is working as designed. It is the volume that has changed.

## What would close it, if anyone wants to

The listing sweep renders no per-query search, so `no_run_for_source` is arguably
correct for a genuine subreddit listing — but only for a listing. The per-model
fetch's Reddit arm issues model-name queries through the same writer, and that is
the case the 853-row incident was about. Whoever ran today's batch is the only
person who knows which of the two it was, and the row cannot say.

`collect/ops/sweep_reddit.py` already opens `harvest_run` rows for the listing
path in the chain. A hand-run that bypasses the chain bypasses that too.

## The comparable gap on my side, so this is not one-directional

I opened a larger one today and by the same mechanism. `document`'s six
specificity columns went from 1,106 NULL to 2,171, and **926 of the 1,065 new
NULLs are mine** — 148 comment rows and 778 sweep rows, all written by paths that
do not score. The forward path exists (`score-documents` in
`collect/ops/chain.py`) and nothing invokes it, so every document any of us
writes outside the chain reopens it.

Same shape, same afternoon, larger number.
