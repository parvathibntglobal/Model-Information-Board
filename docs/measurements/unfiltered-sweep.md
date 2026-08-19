# The retrieval bias, measured

**83.1% survival on a model-name-retrieved corpus, 33.7% on an unfiltered one.
The gap is 49.5 percentage points, and the entity gate is almost all of it —
it drops 8.1% of one and 62.6% of the other. Neither figure is worth what the
gap is worth.**

*Engineer 1 · 1,925 posts, 78 calls, 5m08s · 2026-08-18*

> The first fetch this lane has made through `assert_terms_reviewed`. The Reddit
> path had never called it — `reddit-via-rapidapi` was ruled the same day.

---

## 0 · What was fetched, and under what

| | |
|---|---|
| endpoint | `/getPostsBySubreddit`, **no query terms** |
| sort | `new` |
| subreddits requested | 12, equal draw, 7 pages of 25 each |
| subreddits returned | **11** — see §4 |
| posts | 1,925 distinct |
| calls | 78 · quota 998,850 → 998,772 · **1 unit per call, again exact** |
| wall clock | 308s at 2.5s/call |
| terms ruling | `reddit-via-rapidapi`, basis `internal-development-only`, live-checked |
| storage | `_unfiltered_sweep/`, outside `raw/`, `delete_after: 2026-11-16` |

**This measures survival *within these subreddits*.** Not survival over Reddit.
Every available basis for choosing them biases upward, and these were nominated
by breadth of query coverage in the 2026-08-17 slice — less circular than post
count, and not uncircular.

---

## 1 · The two funnels, side by side

Identical code, identical surface population (`dc69d8725ccfe658`), identical
gates. Only the retrieval differs.

| | **A** model-name-retrieved | **B** unfiltered |
|---|---|---|
| corpus | `_substitution_slice/` | `_unfiltered_sweep/` |
| n | 1,297 | 1,925 |
| no resolvable entity | 105 · **8.1%** | 1,206 · **62.6%** |
| pure link post | 144 · 11.1% | 413 · 21.5% |
| <15 tokens, no artifact | 89 · 6.9% | 317 · 16.5% |
| **survival** | **83.1%** | **33.7%** |

**The gap is 49.5 points, and 54.6 of it is the entity gate** — the gate
over-shoots the total because the other two gates also drop more on B, and a
document can fail several at once.

That is the number this sweep existed to produce. Neither survival figure means
much alone: A's was always an upper bound, and B's has three gates missing. The
*difference* is a property of the retrieval and nothing else, because everything
downstream was held constant.

**Concretely: every survival figure ever quoted from a model-name-retrieved
corpus was too high by roughly a factor of 2.5.** Not slightly optimistic —
wrong enough that a 2σ baseline built on it would have been calibrated against a
population that does not exist.

---

## 2 · Against the 10–15% target

```
33.7% survival
  of 1,925 posts, sort=new, 11 AI-focused subreddits, equal draw
  /getPostsBySubreddit, no query terms, 2026-08-18
  95% CI 26.2% - 42.1% once clustering is accounted for (§3)

  STILL AN UPPER BOUND: three of six gates do not exist. wrong-language,
  known-bot and out-of-window did not run on any of the 1,925.
```

So the honest reading is **not** "survival is 33.7% and the estimate was wrong".
It is: within these subreddits, with half the gates built, a third of documents
survive. The missing gates can only push it down, and the remaining distance to
10–15% is roughly what three gates would have to account for.

Whether they can is now a checkable question rather than a guess. The largest
single unknown is the language gate — no detector is installed, and a `new` sort
over general subreddits returns whatever was posted, in whatever language.

---

## 3 · The design effect is 14.5, and my sample-size reasoning was wrong

`docs/unfiltered-sweep-design.md` §3 predicted a design effect of 1.5–3 and
sized n=2,000 against it. **Measured, it is 14.5.**

| subreddit | n | survival |
|---|---|---|
| r/LocalLLaMA | 175 | 59.4% |
| r/LocalLLM | 175 | 45.1% |
| r/ClaudeAI | 175 | 44.6% |
| r/GithubCopilot | 175 | 40.0% |
| r/ClaudeCode | 175 | 36.0% |
| r/codex | 175 | 35.4% |
| r/OpenAI | 175 | 26.3% |
| r/GeminiAI | 175 | 25.7% |
| r/ChatGPT | 175 | 23.4% |
| r/Bard | 175 | 18.9% |
| r/singularity | 175 | 15.4% |

**15.4% to 59.4% — a factor of nearly four between subreddits.**

| | simple | cluster-adjusted |
|---|---|---|
| effective n | 1,925 | **132** |
| 95% CI | 31.6% – 35.8% | **26.2% – 42.1%** |
| half-width | ±2.1pp | **±7.9pp** |

### What that changes

**The subreddit is the unit of variation, not the post.** 175 posts from
r/singularity tell you about r/singularity; they barely tell you about the next
subreddit. So:

- **more pages per subreddit buys almost nothing.** Going to 5,000 posts across
  the same 11 would move the interval by a fraction of a point.
- **more subreddits is the only thing that buys precision.** Doubling to 22 at
  the same 175 each roughly halves the variance of the mean.
- and the 12-subreddit list itself is now the dominant uncertainty. The figure
  is a property of *which* AI subreddits were picked, far more than of how many
  posts came from each.

I got this wrong in the design report by assuming subreddits differ mildly. They
differ enormously, and the direction is legible: r/LocalLLaMA is practitioners
posting configs and errors; r/singularity is speculation about AI in general,
where most posts name no model at all.

---

## 4 · r/Anthropic returned nothing, and it was not silent

One of the twelve returned `success: false, data: "data not found"` on its first
call — 0 posts, loop terminated, 1 call spent.

**That is exactly the collision `collect/adapters/reddit.py` documents**: the API
answers "no matches" with HTTP 200 and `data not found`, so a broken call and an
empty result are the same shape. Here it is neither — the other eleven all
returned 175, so a subreddit that returns nothing at all on page one is more
likely unavailable to this endpoint than genuinely empty.

The sweep recorded the refusal string verbatim in `calls.jsonl` rather than
counting a zero, which is why this is a footnote instead of a silently
11/12-sized sample reported as 12. **The figure above is over 11 subreddits.**

---

## 5 · The probe, recorded

Four endpoints exist on `reddit34.p.rapidapi.com`:

```
/getSearchPosts        200   (known)
/getPostComments       200   (known)
/getSubredditInfo      200   NEW
/getPostsBySubreddit   200   NEW  <- the listing endpoint the sweep needed
```

Ten other plausible names return `404 {"message":"Endpoint '/x' does not exist"}`.
**404s carry no `x-ratelimit-requests-remaining` header and cost no quota**, so
endpoint discovery is free; only the four real ones decremented.

### One trap worth the warning it got

`/getPostsBySubreddit` takes **lowercase** `sort`, while `/getSearchPosts` takes
`RELEVANCE` / `NEW` / `TOP` in caps. `sort=NEW` on the listing endpoint returns:

```
HTTP 200  {"success": false, "data": "sort value is wrong"}
```

A 200, no exception, zero posts. A sweep written with the search endpoint's
convention would have produced an empty corpus and a survival rate over nothing.
Recorded in the script's docstring beside the constant.

---

## 6 · What would revise this

- **The three missing gates.** Language especially: it is unmeasured and
  unbuilt, and it is the most likely single explanation for the distance
  between 33.7% and 10–15%.
- **More subreddits, not more posts.** §3. The next version of this measurement
  should widen the list rather than deepen the draw, and the list is the
  dominant uncertainty in the figure.
- **A non-AI control.** Every subreddit here was chosen for being about AI. A
  handful of general programming subreddits would bound how much of the 33.7%
  is the topic rather than the pipeline.
- **Re-running after the alias review lands.** The entity gate does almost all
  of the work here, and its population grows from 7 hand-written models to 64
  reviewed ones.
