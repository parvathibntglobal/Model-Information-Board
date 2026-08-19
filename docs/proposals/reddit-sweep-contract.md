# Two contract proposals: the Reddit terms ruling, and the sweep subreddit list

**Proposed, not written. `contract/sources.yaml` is untouched.** Both blocks
below are drafts for the PR that adds them, in the same shape as the four blog
and GitHub rulings and the nine seeded blog feeds.

*Engineer 1 · 2026-08-18*

---

## 1 · The terms ruling

`assert_terms_reviewed` refuses Reddit because the row names no ruling — see
`docs/unfiltered-sweep-design.md` §6. This is the ruling it would name.

Two of the three inputs are measured, in
`docs/measurements/reddit-rate-and-quota.md`. The third is §1.3 and is not mine.

```yaml
# contract/sources.yaml  →  terms_rulings:

  reddit-official-api-via-rapidapi:
    reviewed_on: 2026-08-__          # the day a person reads the terms
    review_valid_days: 180
    summary: >-
      Reddit's terms prohibit scraping, so the official API is mandatory.
      Access is through RapidAPI, which PROXIES that API rather than
      re-implementing it: responses carry `kind`/`data` envelopes, `t2_`/`t3_`
      fullnames, `subreddit_id` and `created_utc` as an epoch float — none of
      which a scraper reconstructing from HTML produces. Verified 2026-08-14.
      Published content is quote + attribution + link, never full text; the
      retained payloads are for verification and reprocessing only.
    requires:
      - official_api: true
      - identifying_user_agent: true
      - full_text_republished: false
    evidence_valid_days: 180
    # See 1.3 for the block that goes here: one ruling covers both an evidence
    # sweep and a measurement sweep, with retention recorded on the sample.
```

`requires` names live preconditions, so `assert_terms_reviewed` re-verifies them
every run rather than trusting an August reading — the same half of the gate
that catches a blog host adding `Disallow: /` in October.

### 1.1 · Rate limit — measured, and BUILD-PLAN is wrong

BUILD-PLAN says 60 requests/minute and `.env.example` already records that no
source was ever found for it. **The observation contradicts it**: 429 arrived at
call 32, so the allowance is below 32 and 60/min would fail in the first minute
of every sweep.

For the evidence block:

```yaml
    measured:
      checked_on: 2026-08-14
      per_minute_observed_break: 32     # 429, "for your plan, PRO", clears ~60s
      per_minute_allowance: null        # NOT READ. Observed < 32, never stated
      retry_after_header: false         # backoff is ours to choose
      monthly_limit: 1000000            # READ 2026-08-18 off the response,
                                        #   not the docstring it used to cite
      monthly_limit_read_on: 2026-08-18
      monthly_limit_plan_states: 500000 # the plan page. STILL DISAGREES. What
                                        #   the gateway advertises is not proof
                                        #   of the billed tier — see below
      monthly_limit_is_billed_tier: null  # UNVERIFIED. A browser, not a call
      monthly_reset_seconds: 2064366    # READ. 23.893 days, NOT the ~28 the
                                        #   docstring claimed. Stored as the
                                        #   duration; a date needs its read_at
      monthly_reset_read_on: 2026-08-18
      per_minute_header_exists: false   # all 16 headers captured; the monthly
                                        #   triple is the only rate-limit family
      quota_unit: request               # 1 per request, exact over 558 requests,
                                        #   and per call over the last 186
```

**`per_minute_allowance: null` is the load-bearing line.** 32 is where it broke,
not what the plan permits, and writing 32 — or the adapter's working 25 — into
the ruling as *the limit* would convert an inference into a recorded fact. Rule
6: an unread value stays unread.

**`monthly_limit` is now a reading, and it was right before by luck.** Until
2026-08-18 that figure came from a docstring in `collect/adapters/reddit.py` and
from no response — `_get` captured `-remaining` and nothing else. Read live on
2026-08-18 it is 1,000,000, so the constant was correct and the method was not,
which is the worst combination for a number five documents cite: nothing prompts
anyone to go back and check a figure that keeps being right.

**One thing the reading does not settle, recorded as null rather than as
reassurance.** The plan page says 500,000. A header is the gateway's view —
internally consistent, 1:1 decrement, stated reset — and internal consistency is
not proof of the billed tier. If the subscription is a 500,000 tier, collection
stops there with the header reading ~500,000 remaining and looking healthy. No
request can distinguish this, because the value would come from the party whose
figure is in doubt. `monthly_limit_is_billed_tier` closes when somebody opens the
RapidAPI subscription page — a browser, not a call. What each instrument settles:
`docs/measurements/reddit-rate-and-quota.md` §1.4.

### 1.2 · Quota — measured, exact

Confirmed twice, on different days:

| run | requests | quota delta | per request | granularity |
|---|---|---|---|---|
| substitution-slice | 204 | 204 | 1.000 | run ends |
| substitution-resieve | 168 | 168 | 1.000 | run ends |
| unfiltered sweep | 78 | 78 | 1.000 | per call |
| control tier 1 | 18 | 18 | 1.000 | per call |
| control tier 2 | 12 | 12 | 1.000 | per call |
| unfiltered sweep v2 | 78 | 78 | 1.000 | per call |

So cost is a function of **calls**, knowable before a sweep, not of yield. Exact
over 558 requests, and exact at every individual call over the last 186.

**Consumption, against a denominator that has now been read.** 1,340 of
1,000,000 in the current window — 0.134%. Of that: 558 attributed to the six runs
above, 733 predating any ledger, 45 in two gaps that predate per-call logging and
cannot now be closed, 3 that appeared between the last sweep and the probe and
belong to no script here, 1 the probe itself.

**Both planned sweeps together are 23,415 requests per reset window** — 2.34% of
the read 1,000,000, or 4.68% if the billed tier turns out to be 500,000. Per
*window*, not per month: the reset is 23.893 days, so the previous
`29,400 a month` overstated the cost by a third by multiplying against a calendar
month nobody had read.

What is *not* measured: what the PRO plan's own terms permit. The quota headers
name the plan; nobody has read its document. That is reading, not measurement,
and it belongs with §1.3.

### 1.3 · Ruled: one ruling, and retention is a property of the sample

**Decided 2026-08-18. One ruling covers both an evidence sweep and a
measurement sweep.**

The deciding argument is the one against a second ruling: **purpose is
self-declared, and an exempt category is one everything eventually gets filed
under.** The moment "this is only a measurement" skips a check, every sweep
acquires a measurement justification — and the person writing that
justification is the same person who wants the data. The gate is built with no
concept of purpose on purpose: it takes a source row and this run's live
observations, and a fetch is a fetch.

**The retention difference is real, and it argues for stricter handling of the
sample rather than for a different set of terms.** Reddit's terms do not change
according to why we asked. What changes is what we keep and for how long, and
that is a property of the sample — so it is recorded on the sample, not
negotiated into a second ruling:

- stored **outside `raw/`**, as `docs/unfiltered-sweep-design.md` §4 already
  designed it, because a measurement population is not evidence and mixing them
  contaminates every later denominator;
- with a **deletion date recorded at collection**, because a sample kept to
  compute one percentage has no reason to outlive the percentage;
- under the **same ruling**, so it is subject to every precondition an evidence
  fetch is subject to and cannot drift out from under them.

**This reasoning is in the ruling and not only in this file**, because Engineer 2
flagged it as the thing whoever runs the next sweep will assume either way — and
they will assume it silently. A conclusion without its argument gets re-litigated
by the next person who finds a reason it should not apply to them.

```yaml
    # ONE RULING COVERS BOTH AN EVIDENCE SWEEP AND A MEASUREMENT SWEEP.
    #
    # Ruled 2026-08-18. The alternative was a second, lighter ruling for
    # sampling runs that quote nobody and publish nothing, and it was refused:
    # PURPOSE IS SELF-DECLARED. An exempt category is one everything ends up
    # filed under, and the person writing the justification is the person who
    # wants the data. `assert_terms_reviewed` has no concept of purpose,
    # deliberately — it takes a source row and this run's observations, and a
    # fetch is a fetch.
    #
    # The retention difference is real and cuts the other way. An evidence
    # sweep keeps documents it intends to quote, attribute and link. A
    # measurement sweep keeps ~2,000 posts BECAUSE MOST OF THEM ARE ABOUT
    # NOTHING, quotes none of them, and exists to compute one percentage. If
    # asked "why do you hold this post", the answers differ: "we cited you"
    # versus "you were in a denominator". That is a reason to handle the
    # sample more strictly, not to hold it under different terms — Reddit's
    # terms do not vary by our motive. So it is a property of the SAMPLE:
    #
    #   * stored outside raw/, never mixed with evidence
    #   * a deletion date recorded when it is collected
    #   * this ruling, with every precondition it carries
    measurement_sweeps_covered: true
    measurement_sample_retention_days: 90
    measurement_sample_storage: separate    # never raw/
```

`measurement_sample_retention_days` is the one number here nobody has grounds
for yet. 90 is proposed as "long enough to re-run the funnel after the two
missing gates land, and not longer" — if the gates are further out than that,
the right move is to raise it deliberately rather than to let the sample sit
undeleted because a date passed unnoticed.

---

## 2 · The subreddit list

Same class as the seeded blog feeds: a hand-curated decision that belongs
somewhere reviewable and diffable, and becomes ordinary rows at runtime.

### 2.1 · The circularity, stated in the file rather than resolved by it

**Every available basis for choosing subreddits biases survival upward.** This
is not fixed by the choice below; it is bounded and declared.

| basis | direction | why |
|---|---|---|
| the slice's top subreddits | too high | selected by having answered model-name queries |
| subscriber count | too high, mildly | volume correlates with topicality here |
| topic-chosen fixed list | too high, **statedly** | a judgement, legible as one |
| r/all or r/popular | far too low | measures Reddit, not our sources |

So the number this sweep produces is:

> **survival within the subreddits we would actually harvest**

and never *survival over Reddit*. A nightly sweep does not read r/all, so the
first figure is the one the pipeline needs — but quoted without its population
it becomes the next 52.7%. This paragraph belongs in the contract file, above
the list, so the number is read correctly by whoever finds it later.

### 2.2 · How the candidates were nominated

Ranked by **distinct queries answered**, not post count. The slice issued 113
distinct queries; a subreddit that returned posts for many different model pairs
is a general venue, while one that answered a single query is incidental to it.
Post count is dominated by whichever model was queried most, so breadth is the
less circular of the two available signals — though it is not uncircular.

| subreddit | posts | distinct queries | share of 113 |
|---|---|---|---|
| r/ClaudeAI | 151 | 54 | 47.8% |
| r/LocalLLaMA | 82 | 40 | 35.4% |
| r/ClaudeCode | 83 | 37 | 32.7% |
| r/singularity | 76 | 34 | 30.1% |
| r/OpenAI | 38 | 24 | 21.2% |
| r/GithubCopilot | 23 | 22 | 19.5% |
| r/codex | 33 | 21 | 18.6% |
| ~~r/AISEOInsider~~ | 40 | 20 | 17.7% |
| r/ChatGPT | 38 | 19 | 16.8% |
| r/Anthropic | 24 | 18 | 15.9% |
| r/GeminiAI | 34 | 17 | 15.0% |
| r/Bard | 32 | 14 | 12.4% |
| ~~r/u_enoumen~~ | 14 | 13 | 12.4% |
| r/LocalLLM | 13 | 12 | 10.6% |

Of 275 subreddits, 175 answered exactly one query and 38 answered five or more.

### 2.3 · Two exclusions, and why breadth alone cannot decide

**Breadth nominates; a person decides.** Two of the highest-breadth candidates
are content-marketing venues, and they rank high *because* they blanket-post
about every model — the exact behaviour breadth rewards.

- **`r/u_enoumen`** — a user profile page, not a subreddit. Syndicated
  *"[AI DAILY NEWS RUNDOWN]"* and *"(Special Report)"* posts. The `u_` prefix
  identifies it mechanically and it is the only one in the corpus.
- **`r/AISEOInsider`** — 40 posts of the shape *"The Coding Battle That Shocked
  Me"*, *"Makes Small AI Models INSANE"*. SEO listicles about models rather than
  reports from using them.

Both are what E6 vet exists to reject downstream. Excluding them at selection is
not a substitute for that — it is avoiding spending the sample on a population
we already know we would throw away, which would depress the survival figure for
a reason unrelated to what it is measuring.

### 2.4 · Proposed block

```yaml
# contract/sources.yaml  →  sweep_subreddits:
#
# WHAT A FIGURE MEASURED HERE MEANS, AND WHAT IT DOES NOT
#
# Survival measured over these subreddits is SURVIVAL WITHIN THE SUBREDDITS WE
# WOULD HARVEST. It is not survival over Reddit and must never be quoted as
# such. Every available basis for choosing them biases upward — these were
# nominated by how many distinct model-pair queries each answered in the
# 2026-08-17 slice, which is less circular than post count and is not
# uncircular. The bias runs one way and is stated so the number can be read.
#
# EQUAL DRAW, NOT PROPORTIONAL. Sampling in proportion to volume would make
# r/ClaudeAI roughly half the sample and the figure a fact about one subreddit.
# Equal draw makes it a fact about the set, at the cost of a design effect the
# confidence interval has to carry (see unfiltered-sweep-design.md §3).
#
# HAND-CURATED, like the seeded blog feeds. Nominated by measurement, chosen by
# a person, and two high-ranking nominees were excluded as content marketing.

sweep_subreddits:
  version: "1.0"
  chosen_on: 2026-08-__
  draw: equal            # posts per subreddit, not per corpus
  target_n: 2000
  members:
    - ClaudeAI
    - ClaudeCode
    - LocalLLaMA
    - singularity
    - OpenAI
    - GithubCopilot
    - codex
    - ChatGPT
    - Anthropic
    - GeminiAI
    - Bard
    - LocalLLM
  excluded:
    - id: u_enoumen
      reason: >-
        a user profile page, not a subreddit. Syndicated news-rundown posts;
        ranks high on breadth because it blanket-posts about every model.
    - id: AISEOInsider
      reason: >-
        SEO listicles about models rather than reports from using them.
        Same reason, same mechanism.
```

Twelve subreddits, 2,000 posts, ~167 per subreddit — about 7 pages each at 25
per page, comfortably inside the ~250-per-sort ceiling.

### 2.5 · What this list is not

- **Not a harvest list.** It scopes the calibration sample. Whether the nightly
  evidence sweep reads the same twelve is a separate decision.
- **Not stable.** Subreddits rise and die. `version` and `chosen_on` exist so a
  survival figure can be tied to the list that produced it, the same way a
  triage verdict is tied to `SurfacePopulation.fingerprint`.
- **Not defensible as representative.** §2.1.

---

## 3 · Wiring cost, so it lands in one change

`RedditHarvester` is constructed in exactly **two** places:

| site | needs the gate? |
|---|---|
| `scripts/substitution_slice.py:260` | **yes** |
| `tests/test_reddit_fetch.py:70` | **no** |
| the sweep harness, once built | **yes** |

So the change is one new factory plus one call site, mirroring
`blog/fetch.py:fetcher_for_source` exactly:

```python
def harvester_for_source(source, *, rulings=None, **kwargs) -> RedditHarvester:
    assert_terms_reviewed([source], rulings=rulings, observations={...})
    return RedditHarvester(**kwargs)
```

**The gate belongs in the factory, not in `_get` and not in `__init__`**, and
blog already documents why: firing in the constructor forces every test to
fabricate a reviewed source row, and *"a fixture that fakes a ruling is worse
than no gate, because it reads as one"*. `_get` is worse still — it would fire
per request and need the source row threaded through two call paths
(`search`, `fetch_comments`) that currently do not carry it.

Tests keep constructing `RedditHarvester` directly, which is the same
arrangement the nine blog feeds run under.

**Scope: one factory (~15 lines), one call site changed, one test file
untouched.** It should land with the ruling — wiring it first turns a documented
gap into a broken script, and that script is what re-fetches the corpus if the
sieve changes.

---

## 4 · The endpoint probe, and the fallback if it fails

After the ruling, one call confirms whether `reddit34.p.rapidapi.com` exposes a
listing endpoint (posts by subreddit / new posts) rather than only
`/getSearchPosts` and `/getPostComments`. Cost: 1 request. **The header half is
done** — `scripts/quota_probe.py` spent one call on 2026-08-18 and captured all 16
response headers, which is where `monthly_limit` and `monthly_reset_seconds` above
come from. The endpoint question is separate, and `/getPostsBySubreddit` has since
answered it by working.

**If none exists**, the options in order of preference:

1. **The official Reddit API.** `.env.example` already carries
   `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`, deferred since week 3 because
   the company holds the account. This would be the **second** thing waiting on
   it — FR-6's acceptance (all three adapters returning content) is the first.
   Two blocked deliverables is a better case for requesting it than one.
2. **`/getSearchPosts` with a subreddit scope and no query terms**, if the
   endpoint tolerates an empty or wildcard query. This is *not* equivalent —
   search ranks, and ranking is what the sweep exists to escape — so it would
   need its own control before it could be trusted: issue the same scope twice
   under different sorts and check the overlap, exactly as the
   `"as an AI"` finding did.
3. **Abandon the calibration** and keep quoting survival as an upper bound with
   its population stated. Least good, but honest, and it is where things stand
   today.

Option 2 is the one to be careful about: it looks like a cheap substitute and
would quietly reintroduce the selection effect the sweep was designed to remove.
