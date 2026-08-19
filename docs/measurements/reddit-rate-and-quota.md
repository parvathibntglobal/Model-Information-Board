# Reddit via RapidAPI — what the rate limit and the quota actually are

**`x-ratelimit-requests-limit` now READ: 1,000,000. The constant was right and
the method was wrong, which is the outcome least likely to teach the lesson.
Quota decrements exactly 1 per request, confirmed per call over 558 requests.
The window resets 2026-09-11 09:45 UTC and the docstring's "~28 days" was
23.9. What one reading CANNOT settle is whether the gateway's 1,000,000 is our
billed allowance when the plan page says 500,000 — that is a browser, not a
call, and §1.4 says so rather than picking.**

*Engineer 1 · one live call, all headers captured · 2026-08-18 (revised)*

> Two of the three inputs a Reddit terms ruling needs are measurable. These are
> those two. The third — whether a measurement sweep is covered by the same
> ruling as an evidence sweep — is not measurable and is not here.

---

## 0 · One call, taken after the ruling, capturing every header

**The first version of this document was written under a refusal** —
`assert_terms_reviewed` had no `reddit` ruling to name, so §1's limit was a
subtraction from a constant. The ruling landed 2026-08-18
(`reddit-via-rapidapi`, basis `internal-development-only`), the gate now passes,
and `scripts/quota_probe.py` spent **one request** to read the headers.

It records *all* of them, not the three it came for, and discards the body — a
header reading is not a collection, so it acquires no retention obligation and
writes nothing to `raw/`. Ledger: `docs/measurements/quota-headers.jsonl`.
Reading one header and inferring the rest is how §1.4 happened.

```
x-ratelimit-requests-limit         1000000
x-ratelimit-requests-remaining      998660
x-ratelimit-requests-reset         2064366     seconds = 23.893 days
read_at                            2026-08-18T12:19:16Z
```

No per-minute header of any kind on the response — 16 headers, and the only
rate-limit family is the monthly triple. **That settles §2's open question in the
negative**: the `< 32` inference cannot be replaced by a reading, because there
is nothing to read. The rest below is from evidence prior runs wrote down:

| source | what it carries |
|---|---|
| `docs/measurements/substitution-slice.md` | 204 requests, quota 999,267 → 999,063 |
| `docs/measurements/substitution-resieve.md` | 168 requests, quota 999,028 → 998,860 |
| `_unfiltered_sweep/calls.jsonl` + `manifest.json` | 78 requests, quota 998,850 → 998,772, **per call** |
| `_control_sweep/tier1/calls.jsonl` | 18 requests, quota 998,772 → 998,754, per call |
| `_control_sweep/tier2/calls.jsonl` | 12 requests, quota 998,754 → 998,742, per call |
| `_unfiltered_sweep_v2/calls.jsonl` | 78 requests, quota 998,742 → 998,664, per call |
| `collect/adapters/reddit.py` | the 2026-08-14 rate probe and the header names |

The four `calls.jsonl` ledgers are the `quota_remaining` fix §4 asked for. They
record the header on **every** call rather than at the two ends of a run, which
is what makes §1's reconciliation a check rather than a subtraction.

**The raw store keeps bodies, not headers** — `RawStore.put` takes bytes — so
response headers are not recoverable from the 120 stored payloads. That is the
boundary between what is settled below and what still needs one live call.

---

## 1 · Quota semantics: 1 request = 1 unit

| run | requests | before | after | delta | per request | granularity |
|---|---|---|---|---|---|---|
| substitution-slice | 204 | 999,267 | 999,063 | 204 | **1.000** | run ends only |
| substitution-resieve | 168 | 999,028 | 998,860 | 168 | **1.000** | run ends only |
| unfiltered sweep | 78 | 998,850 | 998,772 | 78 | **1.000** | per call |
| control tier 1 | 18 | 998,772 | 998,754 | 18 | **1.000** | per call |
| control tier 2 | 12 | 998,754 | 998,742 | 12 | **1.000** | per call |
| unfiltered sweep v2 | 78 | 998,742 | 998,664 | 78 | **1.000** | per call |
| **combined** | **558** | | | **558** | **1.000** | |

Six runs, on four days' code paths, all exact. The last four are exact *at every
individual call* — 186 consecutive calls each decrementing the header by exactly
1, with no step of 0 and none of 2 — which is a stronger claim than the first two
runs could make. So
`x-ratelimit-requests-remaining` counts **requests**, not results, pages or
bytes — a page returning 25 posts and a page returning `data not found` cost the
same.

That matters for budgeting because it means cost is a function of *calls*, which
is knowable before a sweep, rather than of *yield*, which is not.

### Consumption to date

**This section used to open by subtracting a read `remaining` from an assumed
`limit`. That was rule 7 in miniature and it is removed.** It reported
`consumed before the first run 733` and `total by 2026-08-17 1,140`; neither was
measured. Both were `1,000,000 minus a header value`, and the 1,000,000 has never
been read into any record. Substitute the 500,000 the plan is believed to be and
the same arithmetic yields **−499,267** consumed before the first run, which is
how you can tell it was never a measurement.

What the ledger states without assuming any limit:

```
monthly limit                      1,000,000   READ 2026-08-18, not assumed
latest remaining                     998,660   READ, the probe
--------------------------------------------
consumed this window                   1,340   = 0.134%
  attributed to a run                    558   six runs, table above
  unattributed, pre-fix gaps              45   §1.1
  unattributed, since the sweeps            3   §1.1
  the probe itself                          1
  before the first recorded run          733   now a subtraction from a READ
                                               limit rather than from a guess
```

**The 733 was arithmetically correct all along.** With the limit read, the whole
chain closes to the unit: `733 + 558 + 45 = 1,336`, and 1,000,000 − 1,336 =
998,664, exactly the last sweep reading. That is the uncomfortable result. The
figure this document deleted for being unsourced turns out to have been right,
and the deletion was still correct — it was right by an assumption nobody had
checked, and had the plan's 500,000 been the gateway's number it would have been
nonsense in the same confident format. **A right answer from an unsourced method
is the dangerous case, because nothing prompts anyone to go back.**

### 1.1 · The two gaps, and which of them the fix closed

```
(start of window)       1,000,000 → 999,267    733 calls   UNATTRIBUTED, pre-ledger
substitution-slice        999,267 → 999,063    204 calls   recorded
  gap                     999,063 → 999,028     35 calls   UNATTRIBUTED
substitution-resieve      999,028 → 998,860    168 calls   recorded
  gap                     998,860 → 998,850     10 calls   UNATTRIBUTED
unfiltered sweep          998,850 → 998,772     78 calls   recorded, per call
control tier 1            998,772 → 998,754     18 calls   recorded, per call
control tier 2            998,754 → 998,742     12 calls   recorded, per call
unfiltered sweep v2       998,742 → 998,664     78 calls   recorded, per call
  gap                     998,664 → 998,661      3 calls   UNATTRIBUTED, new
quota probe               998,661 → 998,660      1 call    recorded, all headers
```

**A third gap, of 3, opened between the last sweep and the probe.** Nothing in
this repo made those calls — the suite mocks `httpx` and no script ran — so the
key is being used from somewhere this ledger does not see. Small, and recorded
rather than explained: the honest reading is that per-call logging inside our
scripts bounds what *our scripts* spend, and does not bound the key.

**The four post-fix runs reconcile exactly.** Each run's first call reads one
below the previous run's last, with no gap anywhere in the chain: 186 calls,
186 units, boundaries contiguous. Reconciliation, not a subtraction — which is
the whole point of logging the header per call.

**Both gaps predate the fix, and both are permanent.** The 35 was already
recorded here. The **10 between the re-sieve and the unfiltered sweep is new**,
found by this reconciliation and not previously written down anywhere. Its most
likely occupant is the `/getPostComments` fetch behind
`docs/measurements/first-thread-context.md`, which is the only Reddit work
between those two runs — but *that document records no call count and no quota
reading*, so this is a candidate and not an attribution, and it is left as one.

Nothing on disk can close either gap. `RawStore.put` takes `bytes | str` and
stores no headers, so the ~120 payloads from those runs cannot be re-read for a
`remaining` value. Attributing the 45 would take RapidAPI's own request
analytics, which is a live call and outside what this document is allowed to do.

So: **runs from 2026-08-17 are reconcilable only at their end points, and their
45 unattributed requests stay unattributed for good.** Runs from 2026-08-18
onward reconcile per call. The fix does not backfill; it stops the class.

### 1.2 · The reset window, read

```
x-ratelimit-requests-reset   2064366   seconds, verbatim
                                       = 23d 21h 26m 6s = 23.893 days
read_at                      2026-08-18 12:19:16 UTC
resets at                    2026-09-11 09:45:22 UTC
```

**The docstring's `(~28 days)` was wrong too**, by four days, and in the same way
as the limit: nobody had read it. A month is not the window, so "share of a
month" was never quite the right phrase either.

**The header is a duration, and it is stored as one.** `quota_reset_seconds` on
`RedditRun` and `ThreadFetch` holds the seconds; the date above is derived beside
its `read_at` and is worthless without it. A reset date copied into prose without
the reading it came from goes stale inside the month — which is exactly what a
constant in a docstring is, and this document is not repeating the trick.

**What one reading cannot give: the window LENGTH.** 23.893 days remaining is
consistent with a 28-day window that began 2026-08-14 and with a 30-day window
that began 2026-08-12. `scripts/quota_probe.py` is re-runnable precisely so a
second reading dates the boundary rather than inferring it.

### 1.3 · No per-minute header exists

The probe recorded all 16 response headers. **The monthly triple is the only
rate-limit family present.** So §2's "what one live call would settle" is now
settled, and the answer is that nothing settles it from the response: `< 32`
stays the best available fact about the per-minute allowance, and the ruling
should say so rather than quoting the adapter's working 25 as though it were a
limit. §2 stands unchanged and is closed rather than pending.

### 1.4 · What the reading settles, and what it cannot

**Ruled out.** *"The header counts a 500,000 pool."* The header states
`1000000` explicitly. Dead.

**Ruled out.** *"The counter does not track our requests."* 186 consecutive
per-call decrements of exactly 1, run boundaries contiguous, and the probe
landing where the chain predicts. The decrement test — the thing a second live
call would check — has already effectively been run by the sweep ledger, and it
passes.

**NOT ruled out, and this is the one that matters.** *"Our billed allowance is
500,000 and the gateway is advertising something else."* A header is the API
gateway's view. It is internally consistent — a stated limit, a 1:1 decrement, a
reset window — and internal consistency is not the same as being the number
RapidAPI will bill and serve. If the subscription is a 500,000 tier and the
gateway reports a default or another tier's cap, we are cut off at 500,000
**with the header reading ~500,000 remaining and looking entirely healthy.**
That is the expensive case, and one live call cannot touch it, because every
value a call returns comes from the party whose figure is in doubt.

**What would settle it, and which instrument each needs:**

| check | instrument | what it settles |
|---|---|---|
| second reading after known consumption | **a call** | whether the counter tracks our requests. Already passed; adds nothing now. |
| the RapidAPI dashboard / subscription page | **a browser** | the subscribed tier and its quota. **The only thing that closes this.** |
| the PRO plan's own terms | reading | what the tier permits, still unread — §4 |

So: **a call cannot resolve this, and one has been spent finding that out.** The
remaining action is somebody opening the RapidAPI account page and comparing the
subscribed tier against `1000000`. Until then the figures below carry 1,000,000
as a *read gateway value*, not as a confirmed allowance, and the 500,000 column
stays in the table as the live downside.

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

| | calls per run | per window | share of 1,000,000 (read) | share if billed 500,000 |
|---|---|---|---|---|
| unfiltered sweep, n=2,000 | 80 | 1,911 | 0.19% | 0.38% |
| nightly evidence sweep | 900 | 21,504 | 2.15% | **4.30%** |
| both | | 23,415 | 2.34% | **4.68%** |

**Per WINDOW, not per month, and that is a real correction rather than
pedantry.** The reset window is 23.893 days (§1.2), not 30, so a nightly sweep
bills ~23.9 runs against a reset and not 30. The old table's `27,000 a month` was
a third too high — it multiplied by a calendar month nobody had read. The
counts here are `900 × 23.893`.

**The left column is now a share of a read denominator**, which the previous
version of this table could not say. The right column is retained because
§1.4 cannot rule out that the billed tier is 500,000; it sizes the downside and
is not a second candidate figure. Either way the call counts are the measured
part and the percentages follow from them.

Wall clock for the unfiltered sweep at the adapter's 25/min: **3 min 12 s**. At
a flat 30/min it would be 2 min 40 s and would risk the 429 at 32, so 25/min is
the number to use and the saving is not worth the retry.

**Quota is not a constraint on anything currently planned.** At 23,415 requests
per window the headroom is ~43× the planned workload against the read 1,000,000
and ~21× against a billed 500,000. Neither is tight, which is why §1.4's open
question is a thing to close on a schedule rather than an emergency — the
downside case still leaves 21× headroom. The per-minute limit remains the binding
ceiling, and it bounds wall clock rather than volume.

## 4 · What would revise this

- ~~**One live call reading the response headers.**~~ **Done, 2026-08-18**,
  `scripts/quota_probe.py`, all 16 headers into
  `docs/measurements/quota-headers.jsonl`. It turned `-limit` and `-reset` into
  readings (§0, §1.2) and it did **not** turn `< 32` into a number, because no
  per-minute header exists to read (§1.3). One call, and the negative result is
  the more useful half.
- **Somebody opening the RapidAPI subscription page.** The only remaining way to
  learn whether the gateway's 1,000,000 is our billed allowance (§1.4). A
  browser, not a call — no request can settle it, which is why spending more
  calls on it would be waste.
- **A second probe reading, to date the window boundary.** §1.2 knows the window
  is 23.893 days long *as of one reading* and cannot say when it started. One
  more reading on a later date fixes the boundary. Cost: 1 request.
- ~~**Logging `quota_remaining` per run.**~~ **Done, 2026-08-18.** The four
  `calls.jsonl` ledgers record it per call, and §1.1 is the first
  reconciliation it made possible — which promptly found a second gap of 10 that
  the endpoint-only method had hidden. `runs.jsonl` itself still drops the
  field; the sweep scripts write their own ledgers instead, so the substitution
  path would repeat the gap if it were re-run today.
- **A plan-terms reading.** What PRO permits is a document nobody has read, and
  it is one of the three inputs the ruling needs.
