# The RapidAPI window is 30 days, measured — and the projection is stable

*2026-09-16 · ANOOJ · two metered requests, one per arm · bodies discarded*

## The answer

**Reddit's quota window is exactly 2,592,000 seconds — 30.000 days.** Not
approximately: the two boundaries agree to the second.

```
previous boundary   2026-09-11 09:45:23 UTC   (fixed by two readings, 22.7 days apart)
next boundary       2026-10-11 09:45:22 UTC   (this reading)
                    ─────────────────────────
window              2,592,000 s = 30.000 days
```

**X's window length is NOT measured.** Its next boundary is dated —
`2026-09-29 06:23:49 UTC` — but only one boundary is known, and one boundary is
not a period. Assuming 30 days because Reddit is 30 days is the inheritance this
document exists to avoid.

## What made it answerable in one request rather than four weeks

`read_at + x-ratelimit-requests-reset` projects a boundary, and **the projection
does not drift.** Measured on both arms:

```
REDDIT   2026-08-18 12:19:15  reset 2,064,366s  ->  2026-09-11 09:45:21 UTC
         2026-09-10 05:21:38  reset   102,225s  ->  2026-09-11 09:45:23 UTC
         22.7 days apart, boundaries differ by +2s  (+0.08 s/day)

X        2026-09-10 05:26:35  reset 1,645,033s  ->  2026-09-29 06:23:48 UTC
         2026-09-16 12:43:25  reset 1,100,424s  ->  2026-09-29 06:23:49 UTC
          6.3 days apart, boundaries differ by +1s  (+0.05 s/day)
```

Both `read_at` values are second-resolution and the header is an integer, so
±2s **is** the measurement precision. The projections do not drift within what
can be resolved.

This overturns a planning assumption. A boundary was thought to need a rollover
to observe, putting window length three to four weeks out. It needs one reading:
project forward, compare with a boundary already dated. **X's stability was
measured rather than inherited from Reddit's**, which is the same gateway over a
different upstream.

## What this corrects

`docs/measurements/reddit-rate-and-quota.md` says, correctly for its evidence:

> **What one reading cannot give: the window LENGTH.** 23.893 days remaining is
> consistent with a 28-day window that began 2026-08-14 and with a 30-day window
> that began 2026-08-12.

That stands as written — one reading cannot. TWO readings straddling a boundary
can, and that is what is now in hand. Its open item *"a second probe reading, to
date the window boundary. Cost: 1 request"* is **done**, and the answer is the
30-day option.

**The usage panel's "monthly" is nearly right and was unsupported when written.**
30 days is not a calendar month — it does not align to the 1st, and the boundary
sits at 09:45:22 UTC on a rolling date. Anything costed as "per month" is out by
up to a day, and was out by an unknown amount until today.

⚠ **This also makes a comment I wrote this morning false.** `judge/app.py`, in
#331, now reads *"THE WINDOW LENGTH IS NOT MEASURED"*. True when written at
12:15Z, false by 12:45Z. Named here rather than silently fixed, because it is the
third comment in one day made false by data rather than by an edit, and the
pattern is the point: `surface_resolver.py:240`'s refusal example that now
resolves, `judge/app.py`'s one-slot warning that described a fixed defect, and
this. **None was visible to a diff, a review, or the suite.**

## Method, and one caveat

Reddit: `scripts/quota_probe.py`, the existing tool, terms gate passed
(`reddit-via-rapidapi`, internal-development-only), status 200.

X: the same shape against `SEARCH_PATH` on `twitter241.p.rapidapi.com`, key from
`X_RAPIDAPI_KEY`, terms gate passed (`x-via-rapidapi-scraper`) after supplying
`observe_x_use()` — the gate refused the first attempt for want of an
observation, correctly, because *"an observation that was not made is not an
observation that passed"*.

**The X call returned 404**, my query parameters being wrong for that endpoint.
The reading is still real: the gateway metered it (`-remaining` fell 98,954 →
98,953) and served the full rate-limit triple. A header reading does not need a
200. Recorded because a reader should not have to discover it from the ledger.

Cost: 2 requests — 1 of 1,000,000 and 1 of 100,000.

## What still needs a reading

- **X's window length.** One more X reading after `2026-09-29 06:23:49 UTC`
  dates a second boundary and closes it. Cost: 1 request.
- **Whether either gateway limit is the BILLED allowance.** Unchanged and not
  settleable by any call — it is the RapidAPI dashboard, a browser.
