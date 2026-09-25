# The sleep is the rate limit, and the eligible-four does not reproduce

**Written 2026-08-24. Nothing swept, nothing seated.** Two findings were handed
to me with numbers attached. One is right in magnitude and wrong in mechanism;
the other does not reproduce against the database the sweep would run in. Both
are reported before the sweep rather than discovered in its results.

*Engineer 1*

---

## 1 · The sleep: 95% confirmed, but it is not a misapplied limiter

### The mechanism described is not in the code

The claim is *"a rate limiter written for fetching applied to a loop that
fetches nothing."* The sieve loop is `GitHubHarvester.harvest`:

```python
survivors = []
for hit in hits:
    verdict = request.sieve(hit.sieve_text)      # no _get, no wait()
    run.verdicts.append(verdict)
```

**The sieve loop holds no limiter.** `HostLimiter.wait()` is reached from exactly
one place — `_get()` — and `_get()` always issues an HTTP request on the next
line:

```python
def _get(self, url, *, params=None, search: bool):
    (self._search if search else self._rest).wait(url)
    return self._client.get(url, params=params)
```

So of the two proposed fixes:

- **"the sieve loop should not hold the limiter at all"** — it already does not.
  A no-op.
- **"the limiter needs to distinguish a fetch from a local call"** — it already
  does, structurally: it is only ever called immediately before a fetch. Also a
  no-op.

Neither fix has anything to change. The more general one would be the better
design if the problem existed, and it does not.

### But the magnitude is right, and the reason is that the sleep IS the rate limit

```
SEARCH_LIMIT_PER_MINUTE  30        GitHub's documented search limit
SEARCH_HEADROOM          0.9
SEARCH_INTERVAL          2.222 s   -> 27.0 requests/minute
REST_INTERVAL            0.800 s   -> 75.0 requests/minute
```

Measured decomposition, using the **recorded** items-per-query rather than an
assumed one (see below):

| 60 models, 5-repo scope | limiter wait | sieve | total | sleep share |
|---|---|---|---|---|
| Reddit-sized documents (2.2k chars) | 183.1 min | 9.4 min | **192.5 min (3.2 h)** | **95.1%** |
| 48k-char documents | 183.1 min | 206.7 min | **389.8 min (6.5 h)** | 47.0% |

**95.1% against the reported 97.6% — the observation is correct.** The sweep is
overwhelmingly waiting. What it is waiting on is 4,944 search requests at 27 per
minute, which is GitHub's rate limit with 10% headroom. **That is not a defect
and it is not reducible by code.** You cannot issue 4,944 search requests faster
than the limit allows, and the limiter is what keeps us inside it.

**The lever on wall clock is fewer requests, not less sleeping.** 4,944 is
entries x variants, so it moves by narrowing the query set or the alias set —
both of which cost coverage — or by splitting across nights, which needs the
resume machinery that does not exist yet.

### And this corrects my own recommendation from the previous report

I said *"fix the sieve first."* That was wrong, and wrong because of an assumed
denominator.

**I assumed 100 items per query. The recorded sweep says 18.9** — 2,887 items
across 153 runs. That single substitution changes everything downstream:

```
             assumed 100 items/query      recorded 18.9 items/query
sieve         1,096 min                     206.7 min
total         1,261 min (21 h)              389.8 min (6.5 h)  at 48k chars
                                            192.5 min (3.2 h)  at 2.2k chars
```

**So the 21-hour sweep was my arithmetic, not the code's behaviour**, and the
sieve fix I recommended saves **9.4 of 192.5 minutes — 5%** in the
Reddit-sized case. It is worth doing only if documents are genuinely 48k-sized,
where it saves 53%. Which of those is real is still unmeasured, because all 27 of
27 GitHub payloads resolve `missing` from this machine's store.

**`pages_fetched` is NULL on all 153 recorded runs**, so pages-per-query is also
unmeasured and I have assumed 1. If queries commonly paginate, the limiter cost
is a multiple of the figure above and the sleep share rises further.

## 2 · The eligible-four does not reproduce: it is 40 of 40

The claim is *"4 of 78 models have search-eligible variants, and 3 of those 4 are
seed models. So a sweep queries 4 models however many are seated."*

Measured against the configured database — the only one this repo has a
`DATABASE_URL` for, and the one a sweep would run against:

```
seated models (seated_variants(conn))                     40
  models that plan >0 requests                            40
  models that plan  0 requests                             0
total daily requests, 5-repo scope                     3,216
of the 40, seed models                                     5
```

**Every seated model plans requests. None plans zero.** Request counts run 32 to
64 per model — `anthropic/claude-opus-5` 64, `openai/gpt-4` 32, `z-ai/glm-5.2`
32 — spread across all six vendors, not concentrated in the seed set.

### Why, mechanically — and it is none of the three proposed causes

**`search_eligible` is not a column.** `collect/ops/sweep.py` says so in as many
words: *"it is expressed as a non-empty `variants` array, which is what
`alias_rows` writes and what `search_queries()` filters on."* So there is no flag
for a loader to forget to set. The eligibility test is
`array_length(variants,1) > 0`, evaluated in `seated_variants`, and **40 models
pass it.**

Taking the three candidate explanations in turn:

| proposed cause | verdict |
|---|---|
| set by the seeding path and not by the tracked-set loader | **No.** 35 of the 40 models with variants are *not* seed models. The tracked-set loader writes variants; that is why they are there |
| a property the proposer never emits | **No.** The proposer emits `surface` + `variants`, and `rows_for` turns them into rows with those variants populated |
| a rule about which surfaces earn a query that the tracked set does not satisfy | **No, and this is the one worth explaining** — see below |

The rule does exist, and the tracked set satisfies it. In `alias_rows`:

```python
eligible = bool(spellings) or not policy.declared_surfaces_only
```

`spellings` are the hand-written forms from `contract/seed_models.yaml` that
normalise to this key. So under `declared_surfaces_only`, **a surface earns a
query when a human declared that spelling** — which is a deliberate rule, and its
stated reason is that *"a string no human types is a wasted request against a
rate limit."*

That rule governs the **seed** path. It is not the gate on the tracked-set path,
which supplies its variants directly from the reviewed artifact. Both paths end
in a row with a populated `variants` array, which is the only thing the sweep
reads. For the seed path specifically:

```
seed models 11   alias rows 48   search_eligible rows 36
seed models with >=1 eligible row:  11 of 11
distinct search strings across them: 59
```

**11 of 11, not 3 of 4.**

### And 78 does not reproduce either

The counts available from this database are 342 model_versions, 282 `in_window`,
105 alias rows, 103 valid alias rows, 41 models with an alias row, 40 the sweep
reads. **No query returns 78.** As with the 53 in the previous report, it needs
sourcing before anything rests on it.

### The one reading that would make it real, and how to check it

A database where `load-tracked-set` never ran would have only seed-loaded
aliases, and a sweep there really would query a handful of models. **That is the
scenario worth ruling out, because it is about the environment the sweep runs
in rather than about the code.** This repo configures exactly one
`DATABASE_URL` — the shared instance at `203.0.113.5` — and the 40 above are
measured on it. If the sweep is ever pointed somewhere else, this is the query
that answers it in one line:

```sql
SELECT count(DISTINCT model_version_id) FROM model_alias
WHERE valid_until IS NULL AND array_length(variants, 1) > 0;
```

Anything other than 40 there means the target database is not the one this
measurement describes.

## 3 · So: is the baseline worth taking?

**Yes, and it is a baseline about 40 models.** The premise that it would be a
baseline about 4 does not hold, so the fortnight comparison does not inherit that
defect.

It does inherit a different one, unchanged from the previous report and still the
real constraint: **the sweep walks `ORDER BY canonical_id` and stops on the
budget.** At 3,216 daily requests against a 900 cap, one night covers roughly the
first 11 models alphabetically and reports 29 `unreached`. So the honest
description of what a single night produces is **"a baseline over 11
alphabetically-early models of 40 seated"**, and that must be what gets written
down, not "a baseline over the roster".

**Three things, in the order they change the answer:**

1. **Write `last_swept_at`.** Without it there is no per-model date, and the
   fortnight comparison has nothing to join on. Unchanged from the previous
   report and still first.
2. **Resume, not restart.** `watermark` exists with the right key and nothing
   reads it; until then night two re-issues night one and `z-ai/*` is never
   reached on any night. This is what makes a 40-model baseline achievable at all
   under a 900-request cap.
3. **Settle the document size**, which decides whether the sieve fix is worth 5%
   or 53%. It needs a machine that has the raw store.

**The sieve fix drops to third from first**, on the strength of one corrected
denominator.
