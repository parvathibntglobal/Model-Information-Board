# The sweep was anonymous: 18,801 candidates, 0 documents, and a pre-registered row firing exactly as written

**This sweep is a diagnostic, not a baseline. The baseline still does not
exist.** Recorded because what it measured is real and worth having, and because
the thing that made it worthless was found by a row written before it ran.

*Engineer 1 · 2026-08-24*

---

## 1 · What it did

```
runs                407          elapsed        41m51s   (ceiling: 35m)
candidates         18,801        kept              59
documents stored        0        http_errors       65
rate-limited runs      30        runs left open     3   (killed; recorded)
last_swept_at set on    4 models
```

**59 candidates passed the sieve and none of them reached the database.**

## 2 · The pre-registration called this, and it is the reason it was caught

`baseline-sweep-preregistration.md` §2, written before the sweep ran, listed four
outcomes for `context.effective_window`. One of them was:

> **candidates kept but 0 stored** — the sieve passes and the fetch or the write
> drops them. **A different defect entirely, and in my lane.**

That row fired exactly as written. Its value was not that it predicted the cause
— it predicted nothing about credentials — but that **it pre-committed to reading
`59 kept, 0 stored` as a defect rather than as a result.** Without it, "0
documents" from a 40-model sweep is the most quotable number of the week, and it
means nothing.

**So `context.effective_window` returned nothing, and that fact carries no
information.** The commitment stands unspent: the entry has still never been
tested with 40 models nameable, because no model was reachable.

## 3 · Why: every request was anonymous

`collect/cli.py` built the client with no headers. Proven on one URL in one
process:

```
anonymous       core 0/60        search 10/10      fetch -> 403
authenticated   core 4988/5000   search 30/30      fetch -> 200
```

GitHub's anonymous ceilings against what the code assumes:

| | anonymous | authenticated | what `SEARCH_INTERVAL` targets |
|---|---|---|---|
| search | **10/min** | 30/min | 27/min |
| core (REST) | **60/HOUR** | 5,000/hour | 75/min |

So the sweep was **2.7x over the anonymous search limit from its first request**,
and it burned the entire 60/hour core budget in about a minute of fetching. Every
fetch after that 403s — which is why 59 survivors produced 0 documents.

`scripts/harvest_github.py:187` has always sent `Authorization`. **Only the CLI
path did not**, and that is the whole difference between the 2026-08-20 harness
run (2,887 items, 6 kept, documents stored) and this one.

### The distinguishing factor at the HTTP level, since that was the question

Not connection reuse, not burst rate, not the retry loop, not header
politeness. Both clients are `httpx.Client` with keep-alive and the same
User-Agent. **The difference is one header, absent:**

```
build_client()  ->  {accept, accept-encoding, connection: keep-alive, user-agent}
                    ^ no Authorization
```

Secondary-limit behaviour never entered into it. The requests were refused
because they were over a *primary* limit — the anonymous one — and `403` is
GitHub's answer to both, which `collect/adapters/github.py` documents at line
107 and which is exactly why the two are hard to tell apart from the status code.

### And my own diagnostic had the defect it was looking for

I checked `/rate_limit` twice and read `core 5000/5000, search 30/30`, and twice
concluded "not the primary limit". **My probe carried a Bearer header. The sweep
did not.** So the diagnostic reported a different identity's budget than the one
being starved.

That is rule 7 inside a debugging tool: a real number, correctly measured,
answering a question it was not asked. The check that would have caught it is the
one the rule already names — *what population is this drawn from* — applied to a
credential rather than to a corpus.

## 4 · The second defect: a ceiling checked where a model can overrun it

41m51s against a 35-minute contract ceiling. `max_minutes` was tested once per
model, and a model carries 32-64 requests, so a sweep that passed the check with
one minute left issued a whole plan anyway — stretched further by 15-22s throttle
backoffs.

**Cost of the fix: four lines and a `continue` branch.** The clock is now
re-checked before each request, and a seat the clock cuts short is reported
`unreached` and **not stamped**. That second half matters more than the first:
the sweep takes least-recently-swept first, so stamping a model that got 12 of 64
requests would send it to the **back** of the next night's queue, behind models
actually covered. A false coverage date does not merely lie, it inverts the
ordering it feeds.

**The same shape does not exist on the Reddit path.** There is no `sweep-reddit`
CLI command, and `collect/adapters/reddit.py:878` wraps
`collect.http.build_client` for the public JSON endpoints, which need no
credential. Both defects are specific to `ops sweep-github`.

## 5 · What this sweep is worth

**Not a baseline.** A dated baseline requires a corpus, and this produced none.
`baseline-sweep-preregistration.md` stands unspent — its thresholds, its
`context.effective_window` commitment, and the three-population correction all
apply to a sweep that has not yet happened.

**What it did establish, and these are real:**

1. **`last_swept_at` works in production.** Four models carry a coverage date, in
   ascending order, the first per-model coverage record this repository has ever
   had. The resume ordering and the stamp are verified against a live registry
   rather than a fake connection.
2. **The two-phase ledger works under a kill.** Three runs are open with
   `finished_at IS NULL` after I killed the process — which is precisely the
   state `collect/ops/ledger.py` exists to carry, and it must be read as
   "killed", not "errored".
3. **The retrieval side is healthy.** 18,801 candidates from 407 queries is 46
   per query, against the 18.9 the 2026-08-20 run recorded. Retrieval was never
   the constraint; it has not been the constraint in any sweep this project has
   run.
4. **The sieve pass rate is 0.31%** — 59 of 18,801. Consistent with the
   0.00-0.03 recorded before, on ten times the candidates. This is the one figure
   from tonight that is comparable to previous sweeps, exactly as
   `baseline-sweep-preregistration.md` §1 predicted would be the case.

**And what it cost:** 18,801 retrievals of a request budget, spent on a defect.
That is the argument for the refusal rather than a warning — the next
unauthenticated sweep will not run at all.
