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
      monthly_limit: 1000000            # x-ratelimit-requests-limit
      quota_unit: request               # 1 per request, exact over 372 requests
```

**`per_minute_allowance: null` is the load-bearing line.** 32 is where it broke,
not what the plan permits, and writing 32 — or the adapter's working 25 — into
the ruling as *the limit* would convert an inference into a recorded fact. Rule
6: an unread value stays unread.

### 1.2 · Quota — measured, exact

Confirmed twice, on different days:

| run | requests | quota delta | per request |
|---|---|---|---|
| substitution-slice | 204 | 204 | 1.000 |
| substitution-resieve | 168 | 168 | 1.000 |

So cost is a function of **calls**, knowable before a sweep, not of yield.
1,140 of 1,000,000 consumed by 2026-08-17 — 0.114%. Both planned sweeps
together are 2.94% of a month.

What is *not* measured: what the PRO plan's own terms permit. The quota headers
name the plan; nobody has read its document. That is reading, not measurement,
and it belongs with §1.3.

### 1.3 · Yours: is a measurement sweep the same fetch as an evidence sweep?

Not measurable — it turns on what we would say if asked. Both arguments, without
a recommendation.

**They are the same, and one ruling covers both.**
The gate's own position is that a fetch is a fetch: it takes a source row and a
set of live observations, and has no concept of purpose. That is deliberate —
purpose is self-declared, and a category that exempts a request from review is a
category everything eventually gets filed under. Mechanically the two are
identical: same host, same endpoints, same payloads, same retention. And the
unfiltered sweep is arguably the *more* defensible of the two, because it reads
a subreddit's public timeline rather than searching for named products. A ruling
that covered evidence but not measurement would refuse the milder request.

**They are different, and the ruling should say which it covers.**
What we retain differs, and retention is what the terms are mostly about. An
evidence sweep keeps documents it intends to quote, attribute and link — the
board's whole published surface. A measurement sweep keeps ~2,000 posts *because
most of them are about nothing*, quotes none of them, publishes none of them,
and exists to compute one percentage. If asked "why do you hold this person's
post", the honest answer differs: one is "we cited you"; the other is "you were
in a denominator". A ruling silent on that distinction has not been thought
about, and the sweep's population is stored outside `raw/` precisely because the
two are not the same kind of object.

**What turns on it:** if one ruling covers both, §1 as drafted is complete. If
not, the sweep needs its own ruling naming a retention period and a deletion
date, and `assert_terms_reviewed` needs the sweep to pass a different source id
— which is a code change as well as a contract one.

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
`/getSearchPosts` and `/getPostComments`. Cost: 1 of ~999,000.

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
