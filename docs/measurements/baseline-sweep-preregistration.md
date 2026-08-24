# Pre-registration: the baseline sweep, 2026-08-24

**Written before the sweep runs.** Nothing here is a result. The point of the
document is that the two readings below cannot be chosen after the numbers exist.

*Engineer 1*

---

## 1 · This sweep queries a different population, so the earlier figures are not its baseline

**State it now, because it is the thing that would otherwise be used to explain
a disappointing result afterwards.**

The recorded GitHub sweep — `harvest_run`, 153 rows, all `source_id = 'github'`,
all inside 26 minutes on 2026-08-20 — named **3 models** across its 121 distinct
`query_key`s:

```
anthropic/claude-3-haiku
anthropic/claude-haiku-4.5
openai/gpt-4
```

That is the corpus every prior figure was measured on:

| figure | population it was drawn from |
|---|---|
| 3,776 candidates -> 25 documents -> 0 claims from author prose | GitHub retrieval for **3 models**, two of them Haiku, one `gpt-4` |
| 140 blog claims -> 7 stored | **blog feeds**, not model-scoped retrieval at all |
| 2,887 fetched -> 6 kept, sieve 0.00-0.03 | the same 3-model sweep |

**This sweep plans over 40 seated models**, and with the resume ordering it
reaches them across nights rather than re-covering one alphabetical prefix. So:

> **The 3,776-to-25 and 140-to-7 figures are not a baseline for this sweep.**
> They describe a corpus retrieved for three models. A worse ratio here is not a
> regression and a better one is not an improvement — the denominators are
> different populations.

**What is comparable** is the per-query sieve pass rate (0.00-0.03), because that
is a property of the sieve against retrieved text rather than of the roster. If
that moves, it moved for a reason worth finding.

**And a correction that belongs here rather than in a footnote:** the earlier
claim that the sweep queries 4 models "however many are seated" was checked and
does not hold — `seated_variants(conn)` returns 40 models and all 40 plan
requests, before this session and after it. The 3-model figure is a property of
**the 2026-08-20 run's budget and ordering**, not of eligibility. Same number,
different cause, and the causes have opposite fixes: one is a loader bug that does
not exist, the other is the alphabetical ordering now fixed in `a482b08`.

## 2 · `context.effective_window` — committed hardest, and what would count

This is the entry to watch, and the reason is that **the only thing that changed
for it is that more models became nameable.**

Its history, from `harvest_run`:

```
query_keys narrowing on `recall` :  22 runs
items fetched                    : 400
items kept                       :   1
```

**One sieve survivor from 400 candidates across 22 queries.** Not zero — and the
distinction matters, because zero would suggest the query is malformed while one
suggests it is merely narrow. Whether that survivor became a stored document
**cannot be answered today**, because nothing links a `harvest_run` to a
`document`. That missing link is item 3 of the proposal sent to Engineer 2 this
session, and this is the concrete cost of not having it.

The entry has two stances, both daily, both narrowing on context-recall
vocabulary:

```
negative  topic: context, long context, context window, recall, needle, long document
          signal: loses recall, forgets the middle, falls apart, degrades past,
                  stops using the, ignores the earlier
positive  signal: held up at, no degradation at, still accurate at, fine at,
                  recall stayed, handled the whole
```

### Stated before it runs

| result | reading |
|---|---|
| **>= 1 stored document** attributable to this entry | the query works and was coverage-limited. 3 models to 40 was the constraint, and the entry earns its place |
| **>= 3 stored documents** | it works and matters. Worth its share of the daily budget, and the positive stance in particular is load-bearing — `context.effective_window` is a silent-failure capability, so "nobody complained" is not evidence for it |
| **0 candidates kept, again** | **the constraint is the query, not the coverage.** 40 models named instead of 3, over the same repos, with the same vocabulary, producing nothing is the query's verdict on itself |
| **candidates kept but 0 stored** | the sieve passes and the fetch or the write drops them. A different defect entirely, and in my lane |

**I am committing to the third row.** If it returns nothing with 40 models
named, I will not attribute that to coverage a fourth time. The signal phrases
are six English constructions chosen by hand; *"loses recall"* and *"forgets the
middle"* are how somebody would write it in an essay, not how they title a GitHub
issue. That is the hypothesis a null result confirms, and the fix is vocabulary
rather than roster.

**One document is enough to change the reading, and it is not enough to call it
working.** Both halves stated deliberately: a single document distinguishes "the
query can match real text" from "it cannot", which is the question. It does not
establish that the entry pays for 2 of 18 daily entries' worth of requests.

## 3 · The reporting shape, fixed now

Same as the previous sweeps, so the rows line up:

```
requests issued / planned, against the cap
candidates retrieved
per-group sieve rates (subject / topic / signal), with the candidate denominator
documents stored
wall clock, against the 35-minute contract ceiling
models reached / unreached          <- new, and it must be reported
last_swept_at set on N models       <- new
```

**`unreached` is not optional.** At 3,216 planned daily requests against a
900-request cap, most of the roster will not be reached tonight. A sweep that
reports only what it covered reads as a sweep that covered everything, and that
is rule 4 at the population level.

## 4 · The wall clock, and a figure I will not repeat

The estimate for tonight is **~33 minutes** — 900 requests at
`SEARCH_INTERVAL` 2.222s, which is GitHub's documented 30 searches/minute at 0.9
headroom. The 35-minute contract ceiling is set just above it.

**Almost all of that is sleeping, and it is the rate limit rather than a
defect.** Both `HostLimiter.wait()` call sites in the repository —
`github._get` and `blog/fetch.py:354` — sit immediately before a `client.get`,
and the sieve loop (`for hit in hits: request.sieve(...)`) reaches neither. There
is no limiter held across local work.

**The "20.5 hours at 97.6%" figure is not carried forward, and the reason is
mine:** it rests on 100 items per query, and the recorded sweep says **18.9**
(2,887 items over 153 runs). With the measured figure the sieve is 9.4 minutes of
a 192.5-minute full-roster sweep. I published the 21-hour number and it was an
unstated assumption of my own, so it is corrected here rather than repeated with
a caveat.

---

## 5 · Three populations that have been used interchangeably, and one that was never any of them

**Added before the sweep re-ran.** These four numbers have all appeared this week
meaning "the models", including in my own reports, and they are four different
things:

| | what it counts | where it comes from |
|---|---|---|
| **38** | models **named in at least one document we hold** | resolving the 316 readable texts against `build_population` |
| **40** | models the **sweep queries** | `seated_variants(conn)` — a non-empty `variants` array, `valid_until IS NULL` |
| **41** | models with **any** `model_alias` row | one more than 40: `z-ai/glm-4.5` is retired, every window closed |
| **342** | rows in `model_version` | the OpenRouter registry, everything polled |
| **78** | **nothing** | not reproducible from this database by any query |
| **73** | **nothing** | never any of them |

Two more that get confused with the above: **103** is valid `model_alias`
**rows**, not models, and **282** is `in_window`.

**Why it matters here rather than being pedantry:** the sweep cost rests on 40,
the coverage claim rests on 38, and the "how much of the registry do we cover"
question rests on 342. A figure quoted as "78 seated models" produced a
145-minute estimate that is actually the 41-model figure, and using it as a
per-model rate would read as a sweep costing half what it costs.

**And the honest note:** I contributed to this. My own report costed "103 seated
models", which is alias rows. The correction is the same one in both directions —
name the population beside the number, which is rule 7 and which these four
figures are a clean instance of.

## 6 · Candidate volume: 6,132, not 74,000

**The 21-hour projection was an extrapolation and the base was too small.**

It came from a ~200-candidate bracket scaled to a full sweep, which produced
figures near 74,000 candidates and put the sieve at 87% of a 21-hour run. The
recorded evidence disagrees by an order of magnitude:

```
2026-08-20 sweep    153 runs    2,887 items fetched   18.9 items/query
tonight, stopped     41 runs    2,853 items fetched   69.6 items/query
```

At the 900-request daily cap that is **~6,100 candidates**, not 74,000. So the
sieve — measured at 2.7-2.9 ms per 1,000 characters — is minutes rather than
hours, and **the sleep is not 97.6% of 21 hours; it is most of ~35 minutes,
which is what the rate limit costs.**

Both halves of that correction are mine and both had the same shape: a real
measurement extrapolated from a population I chose and did not state. Recorded
next to the sleep finding rather than in a footnote, because the two numbers were
published together and would otherwise be corrected apart.

## 7 · Provenance landed first

`document.harvest_run_id` and `document.retrieval_provenance` are in the schema
before this sweep runs, so **this is the first corpus that can name what
retrieved it.** All 343 prior documents read `not_recorded`, which is what they
are, and the state is distinguishable from the `no_run_for_source` that reddit
and blog documents will carry from now on.

The stopped run left one `harvest_run` row with `finished_at IS NULL`. That is
the two-phase ledger doing exactly what it is for — a process that dies cannot
write its own failure — and it should be read as "killed", not as "errored".
