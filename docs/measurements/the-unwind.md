# Four layers of cost, one missing header, and each layer looked like the cause from inside it

**Second time this week that a cost measured in hours turned out to be a defect
measured in characters.** Recorded as a shape rather than as an incident, because
the shape is what repeats.

*Engineer 1 · 2026-08-24*

---

## 1 · The stack, top to bottom

Each of these was investigated as a problem in its own right. Each is real. None
of them is the cause.

```
  a 21-hour projection            <- extrapolated from a 200-candidate bracket
  a max_minutes overrun            41m51s against a 35-minute ceiling
  throttle backoffs                15-22s, thirty times
  a retry loop                     "throttled on attempt 1/2, waiting 18.8s"
  ────────────────────────────────────────────────────────────────────────
  ONE HEADER, ABSENT               Authorization: Bearer …
```

`collect/cli.py` built the sweep's client with `build_client()` and no headers.
Every request went out anonymous.

```
anonymous       core 0/60        search 10/10      fetch -> 403
authenticated   core 4988/5000   search 30/30      fetch -> 200
```

`SEARCH_INTERVAL` is computed from GitHub's authenticated 30/minute, so the sweep
was **2.7x over the anonymous limit from its first request**, and 60 REST calls
an hour is exhausted in about a minute of fetching.

## 2 · Why each layer looked like the cause from inside it

This is the part worth keeping. Every layer had a coherent story, and the story
was locally correct.

**The retry loop.** `"search throttled (403) on attempt 1/2, waiting 18.8s"` is
the adapter doing exactly what it was built to do. From inside, the reading is
"GitHub is throttling us, and the backoff is working." It was, and the throttling
was real. It was throttling an anonymous client.

**The throttle backoffs.** Thirty runs marked `truncated_by = 'rate-limit'`,
15-22s each. From inside: "our rate limiting is too aggressive, or GitHub's is
stricter than documented." The second half was nearly right — GitHub's limit
*was* stricter than the documented 30/minute — but only because we were not the
identity the documentation describes.

**The `max_minutes` overrun.** 41m51s against 35. From inside: "the ceiling is
checked at the wrong boundary." **That one is a genuine defect and it is now
fixed** — but the sweep only reached the boundary because backoffs stretched a
64-request plan past it. Fix the header and the overrun does not occur; fix the
overrun and the sweep still stores nothing.

**The 21-hour projection.** Mine, extrapolated from a ~200-candidate bracket to
~74,000 candidates. Corrected separately to ~6,100 on recorded evidence. From
inside: "the sieve is 87% of the cost, so optimise the sieve." The sieve was
never the cost.

**Each fix would have been real work that changed nothing about the outcome.**
That is the defining property of this shape: the layers are not wrong, they are
*downstream*, and downstream work survives review because it is genuinely
defensible.

## 3 · The diagnostic had the defect it was looking for

I checked `/rate_limit` twice, read `core 5000/5000, search 30/30`, and twice
concluded "not the primary limit."

**My probe carried a Bearer header. The sweep did not.** So the tool reported a
different identity's budget than the one being starved — and it reported it
accurately, which is why it was convincing.

That is rule 7 inside a debugging tool: *a real number, correctly measured,
answering a question it was not asked.* The rule's own check catches it — **what
population is this drawn from** — applied to a credential rather than to a
corpus. I did not apply it, because a `rate_limit` endpoint does not look like a
figure with a denominator.

**It cost two turns and two wrong conclusions**, both published: "the 403s are
GitHub's secondary rate limit reacting to the request pattern" and, before that,
"the 403s were caused by two concurrent sweeps." Neither was true.

## 4 · The same shape as the sleep

The prior instance this week, and it is structurally identical:

| | sleep in a limiter | the anonymous sweep |
|---|---|---|
| **apparent cost** | 97.6% of a 21-hour run | 407 runs, 18,801 candidates, 0 documents |
| **apparent cause** | "a limiter written for fetching, applied to a loop that fetches nothing" | "GitHub's secondary rate limiting" |
| **actual cause** | the limiter was correct; the *denominator* was 100 items/query against a recorded 18.9 | one absent header |
| **size of the fix** | a corrected figure | one line |

Both were investigated at the layer where the symptom appeared. Both had a
plausible mechanism at that layer. Both resolved to something one line lower.

**The generalisation, and it is narrow on purpose:** when a cost is measured in
hours, check the cheapest thing at the bottom of the stack before modelling
anything above it. Not because bottom causes are common — I have no count and
two instances is not a rate — but because the check is nearly free and the
modelling is not. The two instances cost, between them, a 21-hour estimate that
prioritised the wrong fix and a sweep that spent 18,801 retrievals.

## 5 · What was NOT the cause, checked because it was proposed

Named so the file records what was ruled out rather than only what was found.

**No browser-shaped header exists anywhere in this lane.** `sec-fetch-mode`,
`sec-fetch-site`, `sec-fetch-dest`, `sec-ch-ua`, `referer` and an `origin` header:
**zero matches** across `collect/`, `scripts/` and `judge/`. The headers actually
on the wire are seven, all server-shaped:

```
accept  accept-encoding  authorization  connection  host  user-agent
x-github-api-version
```

`build_client()` adds exactly one — `User-Agent`, which NFR-5 requires and which
`assert_identifying_user_agent` refuses to omit. The rest are httpx defaults.
Nothing leaked in, so there is nothing to remove at the origin.

Also ruled out, each with a measurement: connection reuse (both clients are
`httpx.Client` with keep-alive), request rate within a burst (the limiter spaces
them at 2.222s), two concurrent sweeps (the 403s recurred with one process), and
permissions (the same URL returned 200 in the same second with a header added).

## 6 · The confirming fetch

One REST call, on the exact URL that 403'd sixty-five times:

```
status                : 200
x-ratelimit-resource  : core
x-ratelimit-remaining : 4979 of 5000
body                  : issue #933, 0 comments, 65,502 chars
```

**65,502 characters** is also the first real measurement of a GitHub document's
size, which the sieve cost model has been carrying as an unmeasured factor — the
gap between a 192-minute and a 389-minute full sweep. One document is not a
distribution, and it lands nearer the 48k assumption than the 2.2k one.

---

## 7 · The document size, n=1

**65,502 characters**, from the confirming fetch of `Augustrains/agents-radar#933`.

This is the **first real measurement of a GitHub document's size** in this
project. The sieve cost model has been carrying two competing assumptions and no
observation:

| assumption | source | full-sweep sieve cost |
|---|---|---|
| ~2.2k chars | measured, but on **Reddit thread contexts** | 9.4 min |
| ~48k chars | inferred by solving backwards from a 1,258-minute estimate | 206.7 min |

**n=1, and it lands nearer 48k.** At the measured 2.7-2.9 ms per 1,000
characters, a 65,502-character document costs ~180 ms to sieve — 34x the 5.3 ms
the Reddit-sized figure implies.

**What n=1 licenses and what it does not.** It settles that GitHub documents are
*not* Reddit-sized, which was a live possibility and is now closed. It does not
give a mean, a median, or a tail, and the tail is what a cost model needs: one
250k-character monorepo issue costs more than thirty short ones.

**What a distribution would take, and the sweep is the sample.** Every document
this sweep stores is a GitHub payload in the raw store with a `content_hash` and
now a `harvest_run_id`. The measurement is:

```sql
SELECT length(payload) FROM <raw store read> WHERE source = 'github'
```

over the stored set — median, p90, max. **At 30+ documents that is a usable
distribution**; below ~10 it is anecdote with a denominator. The blocker is not
method, it is n: the corpus held 27 GitHub documents and all 27 payloads resolve
`missing` from this machine, so the sample has to come from a sweep run where
the store lives.

Recorded now so the figure travels with its n. `65,502` on its own would become
"GitHub documents are 65k" inside a week.

## 8 · The `sec-fetch-mode` diagnosis was invented

Recorded at Engineer 2's request, as her own instance, because the pattern is
what makes it worth a file rather than a correction.

**The proposal was to remove `sec-fetch-mode` from the client "at the origin
rather than for one call", and to check whether `sec-fetch-site`,
`sec-fetch-dest`, `origin` and `referer` had leaked in with it.** It carried a
remediation plan, a rationale, and a named sibling set.

**None of those headers exists anywhere in this repository.** Zero matches across
`collect/`, `scripts/` and `judge/`. The client sends seven headers and all seven
are server-shaped. There was nothing to remove, and the mechanism the plan
described — a browser-shaped header tripping a bot heuristic — was not what was
happening.

**The check is one command, and it is the same command in both directions:**

```
grep -rni "sec-fetch" collect/ scripts/ judge/
```

Before proposing that a thing be removed, grep the thing. That is the same check
as *"`grep 'def <name>'` versus `grep '<name>'`"* from `defect-shapes.md` #14 —
asked about a header rather than a symbol.

**Why it is worth recording rather than absorbing.** This is the seventh instance
this week of a symbol or mechanism asserted from expectation rather than read:
`render_all`, the eligible-four, `harvest_reddit.py`, `78 seated models`, `73`,
the `24 of 25` prose forms, and now `sec-fetch-mode`. **Six of the seven cost a
verification pass and nothing else.** This one is the first to arrive with a
remediation plan attached, which is the escalation worth noticing — a plan is
harder to decline than an assertion, and had I taken it at face value I would
have edited a header set that does not exist and reported a fix.

**And the symmetry is the reason this file has both sections.** §3 records my
`/rate_limit` probe reporting a different identity's budget, published twice as
a conclusion. Same class: a mechanism believed before it was checked. The
difference is only which of us had the faster check available.
