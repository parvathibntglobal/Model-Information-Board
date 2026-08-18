# Reddit via RapidAPI — what the rate limit and the quota actually are

**Quota decrements exactly 1 per request, confirmed twice over 372 requests.
BUILD-PLAN's 60/min is not merely unsourced — it is wrong in the unsafe
direction: 429 arrived at call 32. And the per-minute allowance has been
*observed breaking*, never *read*, which is a different kind of fact.**

*Engineer 1 · from records already on disk · no fetch · 2026-08-18*

> Two of the three inputs a Reddit terms ruling needs are measurable. These are
> those two. The third — whether a measurement sweep is covered by the same
> ruling as an evidence sweep — is not measurable and is not here.

---

## 0 · Measured from record, not from a new fetch

`assert_terms_reviewed` refuses Reddit (`docs/unfiltered-sweep-design.md` §6), so
no new call was made. Everything below is extracted from evidence two prior runs
already wrote down:

| source | what it carries |
|---|---|
| `docs/measurements/substitution-slice.md` | 204 requests, quota 999,267 → 999,063 |
| `docs/measurements/substitution-resieve.md` | 168 requests, quota 999,028 → 998,860 |
| `collect/adapters/reddit.py` | the 2026-08-14 rate probe and the header names |

**The raw store keeps bodies, not headers** — `RawStore.put` takes bytes — so
response headers are not recoverable from the 120 stored payloads. That is the
boundary between what is settled below and what still needs one live call.

---

## 1 · Quota semantics: 1 request = 1 unit

| run | requests | before | after | delta | per request |
|---|---|---|---|---|---|
| substitution-slice | 204 | 999,267 | 999,063 | 204 | **1.000** |
| substitution-resieve | 168 | 999,028 | 998,860 | 168 | **1.000** |
| **combined** | **372** | | | **372** | **1.000** |

Two independent runs, on different days' code paths, both exact. So
`x-ratelimit-requests-remaining` counts **requests**, not results, pages or
bytes — a page returning 25 posts and a page returning `data not found` cost the
same.

That matters for budgeting because it means cost is a function of *calls*, which
is knowable before a sweep, rather than of *yield*, which is not.

### Consumption to date

```
monthly limit                    1,000,000   (x-ratelimit-requests-limit)
consumed before the first run          733
the two recorded runs                  372
unaccounted between them                35   (comment fetches and probes)
--------------------------------------------
total by 2026-08-17                  1,140   = 0.114% of the month
```

The 35 unaccounted requests are not a discrepancy in the ratio — they are calls
made between the two runs that nothing recorded. Worth noting only because it
shows quota is the one budget currently readable but not logged per run:
`runs.jsonl` carries `calls`, `http_errors` and `rate_limited`, and **not**
`quota_remaining`, though `RedditRun` has the field and `_get` populates it.

## 2 · The per-minute limit, and the correction

**BUILD-PLAN says 60 requests/minute. `.env.example` already records that no
source was ever found for it. The observation contradicts it.**

Measured 2026-08-14, recorded in `collect/adapters/reddit.py`:

```
429 after 32 rapid calls
message: "exceeded the rate limit per minute for your plan, PRO"
clears in ~60s
NO Retry-After header
```

So the true allowance is **below 32**, and 60/min would 429 in the first minute
of every sweep. The adapter's `SEARCH_PER_MINUTE = 25` sits at 78% of the
observed break point, which is why nothing has hit it since.

### What this is *not*

**32 is where it broke, not what the plan allows.** The distinction is the same
one this project keeps having to make: an observation of a boundary is not a
reading of the parameter. The 429 message names the plan (`PRO`) and not the
number, and no header recorded in the adapter states a per-minute allowance —
only the monthly triple (`-limit`, `-remaining`, `-reset`).

So the honest statement is:

```
per-minute allowance: NOT READ. Observed to be < 32.
  one probe, 2026-08-14, 32 rapid calls on /getSearchPosts
  no Retry-After, so the 60s backoff is assumed rather than read
  the plan is named PRO in the 429 body; its documented allowance is
  unrecorded anywhere in this repo
```

**What one live call would settle**, once a ruling permits it: whether the
response carries a per-minute header at all. If it does, the number replaces an
inference. If it does not, then `< 32` is the best available fact and the ruling
should say so rather than quoting 25 as though it were the limit.

## 3 · What this buys the sweeps that are waiting

At 1 unit per request:

| | calls per run | per month | share of quota |
|---|---|---|---|
| unfiltered sweep, n=2,000 | 80 | 2,400 | **0.24%** |
| nightly evidence sweep | 900 | 27,000 | **2.70%** |
| both | | 29,400 | **2.94%** |

Wall clock for the unfiltered sweep at the adapter's 25/min: **3 min 12 s**. At
a flat 30/min it would be 2 min 40 s and would risk the 429 at 32, so 25/min is
the number to use and the saving is not worth the retry.

**Quota is not a constraint on anything currently planned**, and will not become
one until roughly 33× the present workload. The per-minute limit is the only
real ceiling, and it bounds wall clock rather than volume.

## 4 · What would revise this

- **One live call reading the response headers**, after a terms ruling lands.
  It is the only thing that turns `< 32` into a number.
- **Logging `quota_remaining` per run.** `RedditRun` has the field and `_get`
  sets it; `runs.jsonl` drops it. Recording it would have made §1's 35
  unaccounted requests a fact rather than a subtraction.
- **A plan-terms reading.** What PRO permits is a document nobody has read, and
  it is one of the three inputs the ruling needs.
