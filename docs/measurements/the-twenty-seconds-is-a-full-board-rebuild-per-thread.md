# The 20 seconds a thread is a full board rebuild, once per thread, over a 167 ms link

**75% of wall clock is the database and none of it is the claim writes.**
`Pipeline.run` calls `self._cells.rebuild_all()` — *every cell that has
evidence* — once for every thread that stores a claim. At 3 sequential
statements per cell and 167 ms per round trip to the shared database in Ireland,
storing 2 claims cost **16.35 seconds in 95 statements**.

**And it degrades.** Cells grow as claims accumulate, and every later thread
pays for all of them. My "8 hours" was a linear extrapolation from the first 81
threads and it is wrong: the run had no finite ETA.

*Engineer 1 · 2026-08-28. Measured, n=5 threads timed and 1 instrumented.*

---

## 1 · The breakdown that was asked for

One thread, `thread_context_00ce9a186b340888`, 4 verified claims, 2 stored:

```
wall clock          21.70s
  model call         5.27s   24.3%
  database          16.35s   75.3%   in 95 statements
  neither            0.08s    0.4%

statements   seconds   ms each  shape
    31        5.32      171.6   select DISTINCT      <- keys_with_claims()
    30        5.18      172.7   select c.id          <- compute(), per cell
    30        5.17      172.3   insert into cell     <- write(),   per cell
     2        0.34      169.4   insert into claim
     2        0.34      171.0   insert into claim_weight
```

**The claim writes are 0.68s of 21.70s.** Everything else is the board being
rebuilt from scratch because two rows were added to it.

`cells touched: 30`, for 2 claims.

## 2 · What it is NOT, since three cheaper explanations were on the table

```
a fixed sleep          grep -rn "sleep|backoff|rate_limit|throttle" over the
                       extract path returns ONE COMMENT and no code
one model call/claim   no: `_complete_with_retries` makes one call per THREAD,
                       plus at most 2 schema retries. A thread with 18 claims
                       makes one call
a slow model           no: threads yielding zero claims take 2.06-2.36s, all of
                       it API. The model is fine
```

That last row is the control and it is the cleanest evidence in this document:
**a thread that produces no claims costs 2.2 seconds; a thread that produces
claims costs 21.7.** The difference is entirely post-extraction, and the only
thing that runs post-extraction and scales with the board is `rebuild_all`.

## 3 · Why the design is defensible and the measurement still kills it

`rebuild_all`'s docstring:

> *"Whole-table rather than incremental, deliberately. **Recomputation is cheap
> at any claim count this project will reach**, and an incremental path would be
> a second description of the aggregation that can disagree with the first —
> which is the defect this repo keeps finding in prose and would find again in
> code."*

**The argument is right and I would not touch it.** Two descriptions of one
aggregation is exactly the defect this repo keeps finding, and whole-table
recompute is the honest way to avoid it.

What is wrong is one word. *Recomputation* is cheap — the arithmetic is trivial.
**Round trips are not**, and there are three per cell, issued sequentially, to a
host 167 ms away. The claim carries no denominator: it is true against a local
Postgres and false against staging from here, and nothing beside it says which
was assumed. **Rule 7, in a docstring about cost.**

## 4 · The part I got wrong, and it is the estimate not the diagnosis

I told Anooj the run would finish at ~02:15, from 81 threads in 27 minutes.

**That assumed a constant rate, and the rate is not constant.** Cells grow with
claims; `rebuild_all` walks all of them; so thread *n* pays for every cell the
first *n−1* threads created. The board was 23 cells this morning and 30 after
two claims from a single thread.

A rough shape of what was actually ahead, at 3 statements × 167 ms per cell:

```
board size   cost of ONE claim-bearing thread
    30           15 s
   100           50 s
   300          150 s
   600          300 s
```

There is no ETA to quote, which is the point. **The kill at $0.17 was not
early.** It was the last cheap moment.

This is the third estimate I have had to correct today and all three failed the
same way: extrapolating from a sample without checking whether the thing being
sampled was stationary.

## 5 · The fix, and there are two that need no argument

**(a) Move `rebuild_all` out of the per-thread loop.** One call at the end of
`run_all`, or none at all — `judge extract` is always followed by
`rebuild-cells`, which does exactly this in bulk, and the rollup was already
going to be a separate step. Per-thread published counts are the only thing lost
and they are recomputed by the very next command.

This is `judge/pipeline.py`, so it is E2's, and it is a one-line move.

**(b) Run against a local Postgres and push afterwards.** 95 statements at ~1 ms
is 0.1 s instead of 16.35 s, with **no code change at all**. It also removes the
eight-hour transaction on staging, which was the other problem with this run.

Either alone brings a claim-bearing thread from 21.7 s to about 6 s, and (b) is
available today.

## 6 · What this says about batched commits

Batching commits was the instruction and it is right — a crash currently costs
the whole run, and the ledger rows that would let a restart skip finished
threads sit in the same uncommitted transaction.

**But batched commits do not make the run finish.** They convert an open-ended
run into an open-ended run you can resume, which is strictly better and is not
the fix. Both belong in the relaunch: commit every N threads *and* stop
rebuilding the board 1,512 times.
