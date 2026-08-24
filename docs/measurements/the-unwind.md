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
