# `sweep_subreddits`, the listing shape, and the two contract changes it needs

**Proposed, not taken. `contract/sources.yaml` and `contract/harvest.yaml` are
untouched by this document.** Both blocks below are drafts for the PR that adds
them.

*Engineer 1 · 2026-08-28*

---

## 1 · Why the listing shape, in one table

```
                        A · QUERY SHAPE              B · LISTING SHAPE
                        /getSearchPosts              /getPostsBySubreddit
                        one query per (entry, alias) 12 subreddits x 7 pages

requests / day          2,176                        84
wall clock at 25/min    87 minutes                   ~3.4 minutes
against harvest.yaml    max_minutes: 35 -> 2.5x OVER  inside any ceiling
quota / 23.893-day win. 51,990   = 5.2%              2,007   = 0.2%
   if billed tier is 500,000     = 10.4%                     = 0.4%
needs a renderer        yes (parked - see below)     no
selection effect        the index RANKS              none from ranking
```

**The deciding argument is not the cost, it is the ranking.**
`scripts/unfiltered_sweep.py` already avoids `/getSearchPosts` deliberately and
says why in its own docstring: *"the index ranks, and ranking is the selection
effect this exists to escape."* Shape A re-imports it.

And that argument has just been reinforced from an unrelated direction. The
GitHub probes established that **`max_pages = 1`, so every retrieval figure this
project holds is a top-100-by-relevance figure** — 321 of 1,019 runs hit the
page-1 ceiling and supplied 51% of the yield
(`docs/measurements/model-name-versus-capability-retrieval.md` §6). Choosing a
Reddit shape that also depends on an index's ranking would build a second corpus
with the same unstated denominator, on the platform we have least reason to
trust it on: Reddit has no phrase operator and degrades to OR over tokens, so its
ranking is doing more of the work than GitHub's, not less.

**A listing has no such denominator.** "Every post in these subreddits, newest
first, seven pages deep" is a population a person can state.

## 2 · The contract block

Carried forward from `docs/proposals/reddit-sweep-contract.md` §2.4, which was
written 2026-08-18 and never landed. Unchanged in substance; the header is
expanded because §1 gave it a second reason.

```yaml
# contract/sources.yaml  ->  sweep_subreddits:
#
# WHAT A FIGURE MEASURED HERE MEANS, AND WHAT IT DOES NOT
#
# Survival measured over these subreddits is SURVIVAL WITHIN THE SUBREDDITS WE
# WOULD HARVEST. It is not survival over Reddit and must never be quoted as
# such. Every available basis for choosing them biases upward - these were
# nominated by how many distinct model-pair queries each answered in the
# 2026-08-17 slice, which is less circular than post count and is not
# uncircular. The bias runs one way and is stated so the number can be read.
#
# A LISTING, NOT A SEARCH, AND THAT IS THE POINT. /getPostsBySubreddit takes no
# query, so nothing here is ranked by an index. Compare the GitHub corpus, where
# max_pages = 1 makes every rate a top-100-by-relevance figure with an unstated
# denominator. This population is stateable: every post in these subreddits,
# newest first, to the page depth below.
#
# EQUAL DRAW, NOT PROPORTIONAL. Sampling in proportion to volume would make
# r/ClaudeAI roughly half the sample and the figure a fact about one subreddit.
# Equal draw makes it a fact about the set, at the cost of a design effect the
# confidence interval has to carry.
#
# HAND-CURATED, like the seeded blog feeds. Nominated by measurement, chosen by
# a person, and two high-ranking nominees were excluded as content marketing.

sweep_subreddits:
  version: "1.0"
  chosen_on: 2026-08-__          # the day a person signs this list
  draw: equal                    # posts per subreddit, not per corpus
  pages_per_subreddit: 7         # 7 x 25 = 175 each, ~2,100 total
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
```

## 3 · Contract change 1 — `sweep_budget` has no platform dimension

```yaml
# contract/harvest.yaml, as it stands
sweep_budget:
  daily:   {max_requests: 900, max_minutes: 35}
  weekly:  {max_requests: 600, max_minutes: 25}
```

One budget, two platforms, and the numbers are GitHub's: `max_minutes: 35` is
derived from *"GitHub's observed 30 search requests/minute"* and says so. Reddit
runs at 25/min against a different endpoint with a different ceiling.

`collect/ops/sweep.py:sweep_budget(cadence)` reads it by cadence only. A Reddit
sweep calling it would silently spend GitHub's allowance — which is the shape of
defect this project keeps producing: a value that loads, looks right, and answers
a question it was not asked.

**Proposed:**

```yaml
sweep_budget:

  github:
    daily:  {max_requests: 900, max_minutes: 35}
    weekly: {max_requests: 600, max_minutes: 25}

  reddit:
    daily:
      max_requests: 84      # 12 subreddits x 7 pages, the whole plan
      max_minutes: 10       # ~3.4 min at 25/min, with headroom for backoff
    weekly:
      max_requests: 84
      max_minutes: 10
```

`sweep_budget(cadence)` becomes `sweep_budget(platform, cadence)` and **raises on
an unknown platform rather than defaulting**, for the same reason the loader
raises on a missing file: a built-in fallback is a second source of truth that
renders identically to the real one.

## 4 · Contract change 2 — `truncated_by` has no `quota` value

```sql
harvest_run_truncated_ck
  CHECK (truncated_by IS NULL OR truncated_by IN
         ('query-budget','rate-limit','time-budget','extraction-budget','result-ceiling'))
```

Five values, and **none of them is "the monthly quota is exhausted"**. The Reddit
adapter already knows this — it carries `quota_exhausted` as a separate boolean
with a comment saying the value could not be folded in.

**Why a fifth value rather than reusing `rate-limit`, and this is the whole
argument:**

```
rate-limit    retry shortly. The window is ~60 seconds and the right response
              is a backoff.
quota         stop until the reset. The window is 23.893 DAYS (measured,
              2026-08-18) and the right response is to not run.
```

A scheduler told `rate-limit` when the truth is `quota` **retries against a
wall** — every retry consumes another unit of the exhausted quota, and the run
reports throttling rather than exhaustion. The two states want opposite
behaviour, and collapsing them makes the more expensive one invisible.

**Proposed:**

```sql
ALTER TABLE harvest_run DROP CONSTRAINT harvest_run_truncated_ck;
ALTER TABLE harvest_run ADD CONSTRAINT harvest_run_truncated_ck
  CHECK (truncated_by IS NULL OR truncated_by IN
         ('query-budget','rate-limit','time-budget','extraction-budget',
          'result-ceiling','quota'));
```

And a ceiling in the contract, since the quota currently exists in no file:

```yaml
# contract/harvest.yaml
quota:
  reddit:
    #: READ off the response 2026-08-18, not taken from a docstring.
    monthly_limit: 1000000
    monthly_limit_read_on: 2026-08-18
    #: The plan page says 500,000 and the header says 1,000,000. UNRESOLVED -
    #: a header is the gateway's view and internal consistency is not proof of
    #: the billed tier. No request can settle it; a browser can.
    monthly_limit_is_billed_tier: null
    #: 23.893 days, READ. Stored as a duration; a date would need its read_at.
    reset_seconds: 2064366
    #: Stop the sweep at this fraction of the LOWER plausible tier, so the
    #: ceiling holds whichever figure turns out to be the billed one.
    stop_at_fraction_of: 500000
    stop_at: 0.50
```

## 5 · What reuses, and what is new

**Reuses unchanged:** `SweepReport` (with `unreached`, `excluded`,
`marked_swept`, `ledger_failures`), `open_harvest_run` / `close_harvest_run` and
the two-phase commit-per-query arrangement, `RedditRun.harvest_run_fields`,
`harvester_for_source` (the terms gate, already wired), `reddit_write.write_documents`,
and the sieve.

**New:** a `sweep_reddit` stage beside `sweep_github`, ~200 lines. It iterates
subreddits rather than seated models, so `seated_variants` and `mark_swept` do
**not** apply — `last_swept_at` is a per-model column and a listing sweep covers
no particular model. That asymmetry should be stated in the stage rather than
worked around, or the rotation will read a listing sweep as having refreshed
models it never targeted.

**Not needed:** the per-platform renderer. A listing takes no query, so the
renderer stays parked until and unless shape A is chosen. The GitHub probes
already reduced its first job to a negative — structural qualifiers narrow
`total_count` 3.65x and change nothing at page-1 depth — so there is no
independent reason to build it now.

## 6 · What must land before this runs

1. **The `sweep_subreddits` block signed** — §2, a person's choice with a date.
2. **The two contract changes** — §3 and §4.
3. **A view on the 47 unreachable payloads.** 47 of 63 stored Reddit roots have
   bodies that do not resolve in this machine's store, and a sweep that adds
   more posts before that is understood grows the unreadable fraction. Not a
   blocker for the sweep; a blocker for quoting a survival figure over it.

**And one thing that is not a blocker and should be said anyway:** the quota is
cheap enough that this is not a budget decision. 2,007 requests against a read
1,000,000 is 0.2%. The reason to be careful here is the population and the
ranking, not the money.
