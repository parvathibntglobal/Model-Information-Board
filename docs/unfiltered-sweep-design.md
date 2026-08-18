# The unfiltered sweep — design, and the two things that block it

**Not fetched. `assert_terms_reviewed` refuses Reddit, and the endpoint the
design depends on is not confirmed to exist. Both were checked rather than
assumed, and both need a decision that is not mine to make.**

*Engineer 1 · design report · no fetch · 2026-08-18*

> Three things are waiting on this sweep: the 10–15% survival calibration, the
> triage 2σ alert's baseline, and any honest survival figure from the gates.
> It is a small fetch. It is not an unblocked one.

---

## 0 · The problem, so the design follows from it

Every corpus on disk was retrieved by queries containing model names.
`_substitution_slice/` is 1,297 posts returned by `"claude opus 5 gemini 2.5
flash"` and 145 queries like it. So the population is **pre-selected for the
property the entity gate tests**.

Consequences, in the direction they run:

- Every survival figure measured against it is an **upper bound**, and the
  entity gate's is severely so. Measured: the entity gate drops 105 of 1,297
  (8.1%) on that corpus. On a population not selected by model name it must drop
  more, and nothing on disk says how much more.
- A **baseline** collected there would move when the gates land, or when the
  registry grows, rather than when the world changes — which is the one thing a
  2σ alert must not do.

So the sweep needs a population selected by *something other than* whether a
model is named in it.

---

## 1 · Which subreddits, and a correction

**There is no six-subreddit list.** I looked for it: no `subreddit` key in any
file under `contract/`, no `subscriber` anywhere in the tree, and nothing in git
history for either term. `fixtures/reddit/syndication-4-subreddits.json` is four
copies of one crosspost — a dedupe fixture, not a selection. So there is also no
recorded note about subscriber count being a volume proxy; if that reasoning
happened it happened out of band, and it is not written down anywhere I can
find.

What does exist is the slice's **organic** distribution — 275 subreddits, none
of them chosen:

| subreddit | posts |
|---|---|
| r/ClaudeAI | 151 |
| r/ClaudeCode | 83 |
| r/LocalLLaMA | 82 |
| r/singularity | 76 |
| r/AISEOInsider | 40 |
| r/ChatGPT | 38 |
| r/OpenAI | 38 |
| … | |
| 167 subreddits with exactly 1 post | 167 |

**That list is not a safe starting point, and the reason is the same bias the
sweep exists to escape.** These subreddits are where model-name queries happened
to land. Selecting them and then measuring "how often is a model named here"
re-runs the circularity one level up: the population is still chosen by the
property being measured, just indirectly.

### Which way each candidate selection biases the answer

| basis | direction | why |
|---|---|---|
| **the slice's top subreddits** | survival **too high** | selected by having answered model-name queries |
| **subscriber count** | survival **too high**, mildly | the big AI subreddits are AI subreddits; volume correlates with topicality here |
| **a fixed named list, chosen on topic** | too high, but *statedly* | honest, reproducible, and its bias is legible rather than derived |
| **r/all or r/popular** | survival **far too low** | mostly not about software at all; measures Reddit, not our sources |

None of these is unbiased, and the sweep should not pretend otherwise. **The
figure this sweep can honestly produce is "survival within the subreddits we
would actually harvest",** not "survival over Reddit". That is the number the
pipeline needs — a nightly sweep does not read r/all — and it must be labelled
that way or it becomes the next 52.7%.

**Proposed**: a fixed, named, versioned list in `contract/`, chosen on topic and
stated as a judgement, with the sweep drawing from all of them equally rather
than in proportion to their volume. Equal draw matters: proportional draw makes
r/ClaudeAI half the sample and the figure becomes a fact about one subreddit.

That list is a filter rule under rule 5, so it belongs in `contract/` and it is
**proposed, not written**.

---

## 2 · What "unfiltered" means — and the endpoint is unconfirmed

Concretely: **recent posts from a subreddit, with no query terms**. The
retrieval must not be able to select on content, or the bias returns.

This matters more here than it would elsewhere because of what was already
measured about the search path: Reddit's search **degrades to OR over tokens**,
`"rolled back"` returns posts containing `back` without `rolled`, and relevance
ranking supplies containment for common phrases for free. A listing endpoint
avoids all of that by never taking a query at all — there is no ranking to bias
the window, and "the last N posts in r/X" is a definition rather than a result.

**The blocker: I cannot confirm such an endpoint exists.** The adapter knows two
paths and no others:

```python
SEARCH_PATH   = "/getSearchPosts"
COMMENTS_PATH = "/getPostComments"
```

No listing endpoint is implemented, none is named in any doc, and
`reddit34.p.rapidapi.com`'s catalogue is not recorded anywhere in the tree.
Confirming one exists costs a single call — but it is a call against the host
§4 says we may not call yet, so it belongs after the ruling and not before.

**Design consequence, stated now so it is not discovered later:** if no listing
endpoint exists on this host, the sweep as designed is impossible through
RapidAPI, and the options are the official Reddit API (which needs the account
the company holds, deferred since week 3) or abandoning the calibration until
one is available. **I have not built a harness against an endpoint I cannot
confirm** — building against an unverified interface is the speculative work
this report exists to prevent.

---

## 3 · Sample size, and what it buys

The whole point is a figure nobody has to caveat, so the target is a usable
confidence interval and no more. Wilson 95%, half-width in percentage points,
across the range survival might plausibly land in:

| n | calls @25/page | p=0.05 | p=0.10 | p=0.15 | p=0.30 |
|---|---|---|---|---|---|
| 200 | 8 | ±3.1 | ±4.2 | ±4.9 | ±6.3 |
| 400 | 16 | ±2.2 | ±3.0 | ±3.5 | ±4.5 |
| 800 | 32 | ±1.5 | ±2.1 | ±2.5 | ±3.2 |
| **1,000** | **40** | **±1.4** | **±1.9** | **±2.2** | **±2.8** |
| 2,000 | 80 | ±1.0 | ±1.3 | ±1.6 | ±2.0 |
| 5,000 | 200 | ±0.6 | ±0.8 | ±1.0 | ±1.3 |

**Posts cluster within subreddits, so the simple interval is optimistic.** With
a design effect of 1.5–3 — plausible for 8–12 subreddits of differing character
— n=2,000 gives an effective n of 667–1,333 and a real half-width of ±1.8 to
±2.5pp at p=0.125.

> ~~**Proposed: n ≈ 2,000**~~ — **this estimate was wrong and the sweep measured
> it.** The design effect is **14.5**, not 1.5–3: subreddit survival ranges from
> 15.4% (r/singularity) to 59.4% (r/LocalLLaMA). Effective n is 132, not 667–1,333,
> and the real half-width is **±7.9pp**. The subreddit is the unit of variation,
> not the post, so more pages buy almost nothing and only more *subreddits* buy
> precision. Measured in `docs/measurements/unfiltered-sweep.md` §3; the
> paragraphs below are left as written because the reasoning is the part that
> was wrong, not the arithmetic.

**Proposed: n ≈ 2,000, drawn equally across the chosen subreddits.** That
distinguishes 10% from 15% comfortably even at the worst design effect, which is
the question actually being asked. n=5,000 buys ±1pp instead of ±2pp and cannot
buy away the design effect or the subreddit-selection bias, which by then
dominate. Spending 2.5× the calls to shrink the smallest of three error terms is
not a purchase worth making.

---

## 4 · Where it is stored — separate, and not in `raw/`

**Separate.** A directory of its own, the same shape as `_substitution_slice/`,
gitignored.

`raw/` is content-hash addressed, immutable, and the thing every later count is
computed from. These documents are **a measurement population, not evidence**.
Most of them are about nothing — that is the entire point of collecting them.
Mixing them in means:

- every later "documents held" count silently includes ~2,000 posts that were
  never harvested for evidence,
- the triage survival rate over `document` becomes a blend of two populations
  with different selection rules, which is the exact defect this sweep exists to
  fix, reintroduced one layer down,
- and `assemble` would eventually walk them.

The counter-argument is real and does not win: the raw store's purpose is
"reprocess from here rather than re-fetching", and a sample outside it must be
re-fetched if the sieve changes. That cost is one afternoon of quota. The cost
of a contaminated denominator is every figure computed after it, and rule 7 says
that is the expensive class.

Same reasoning `_substitution_slice/` already applies, and `.gitignore` already
has the pattern and the note explaining why.

---

## 5 · Wall clock, and quota

Quota is not the constraint: `x-ratelimit-requests-limit: 1000000`, ~999,000
remaining, and a daily sweep is ~27,000 a month.

Rate is. Measured 2026-08-14: **429 after 32 rapid calls**, message *"exceeded
the rate limit per minute for your plan, PRO"*, and **no `Retry-After`**, so the
backoff is ours to choose rather than the server's to state.

| | |
|---|---|
| posts per page | 25 (observed on every slice payload) |
| calls for n=2,000 | 80 |
| at a self-imposed 30/min | **~2 min 40 s** |
| at a conservative 20/min | ~4 min |
| quota consumed | 80 of ~999,000 — **0.008%** |

Under five minutes and eight-thousandths of a percent. Cost is genuinely not the
objection here; the two blockers are.

---

## 6 · The terms gate — checked, and it refuses

Asked for confirmation rather than assumption, and the assumption was wrong.

**`tos_notes` being written is exactly what this gate stopped checking.** The
first version grepped for a placeholder marker; its own docstring records why
that was replaced — *"a dated placeholder is still a placeholder"*. The gate now
requires a **named ruling**, and `contract/sources.yaml`'s reddit row has none,
deliberately:

```yaml
- id: reddit
  # No `terms_ruling`, deliberately. That is what blocks it, and it is a
  # stronger block than a marker in prose: there is no ruling to name.
  tos_notes: >-
    REVIEW REQUIRED before first harvest. ...
```

Run against that row:

```
Refusing to harvest: 1 source(s) failed the NFR-5 terms check (reddit):
  - reddit: names no terms ruling. Read the terms, add a ruling to
    contract/sources.yaml:terms_rulings, and name it here.
```

The declared rulings are `blog-class-a-self-hosted`, `blog-class-b-medium`,
`blog-umbrella-not-a-fetch-target` and `github-api-terms`. There is no Reddit
ruling of any kind.

### And the hole that check exposes

**The Reddit fetch path has never called this gate.** Its only callers are
`collect/adapters/blog/fetch.py` and `scripts/harvest_github.py`.
`scripts/substitution_slice.py` does not call it, and neither does
`collect/adapters/reddit.py`.

So the 1,297-post corpus every measurement in this repo currently rests on was
fetched through a path that does not check terms. That is not a new decision
being proposed here — it already happened, twice — and it is worth stating
plainly because the gate looks like it covers the lane and covers two thirds of
it.

Wiring it into the Reddit path is in my lane and I will do it, but it should
land **with** the ruling rather than before it: wiring it today turns a
documented gap into a broken script, and the script is what would re-fetch the
corpus if the sieve changes.

### Proposed ruling, for review — not written

`contract/` is shared and untouched. This is a draft for the PR that adds it:

```yaml
terms_rulings:
  reddit-official-api-via-rapidapi:
    reviewed_on: 2026-08-__          # the day someone actually reads them
    review_valid_days: 180
    summary: >-
      Reddit's terms prohibit scraping. Access is via the official API,
      proxied by RapidAPI — responses carry kind/data envelopes, t2_/t3_
      fullnames and created_utc as an epoch float, none of which an HTML
      scraper reconstructs. Published content is quote + attribution +
      link, never full text.
    requires:
      - official_api: true
      - identifying_user_agent: true
      - full_text_republished: false
    evidence_valid_days: 180
```

Three things the reviewer has to establish, and only the third is a judgement:

1. **The real rate limit.** `BUILD-PLAN` says 60/min and `.env.example` already
   records that no source was ever found for it. The measured figure is 429
   after 32 rapid calls. Record the measurement, not the folklore.
2. **Free-tier eligibility and what the PRO plan permits**, since the quota
   headers say PRO and nobody has recorded what that plan's terms allow.
3. **Whether a measurement sweep is covered by the same ruling as an evidence
   sweep.** The gate cannot tell them apart and should not — a fetch is a fetch —
   but the reviewer should decide deliberately rather than by default.

---

## 7 · What I did not do, and why

- **Did not fetch.** Blocked at §6.
- **Did not add a Reddit ruling to `contract/sources.yaml`.** Shared file, and
  the ruling requires reading terms, which is a person's job, not a
  transformation of data I hold.
- **Did not build the sweep harness.** §2: the endpoint it would target is
  unconfirmed, and a harness against an unverified interface is exactly the work
  a design report exists to avoid.
- **Did not wire `assert_terms_reviewed` into the Reddit path yet.** §6: it
  should land with the ruling, not before it.

## 8 · What unblocks it, in order

1. A Reddit terms ruling in `contract/sources.yaml` — a PR, and a person reading
   terms.
2. One probe call confirming a listing endpoint exists on
   `reddit34.p.rapidapi.com`.
3. The subreddit list, versioned in `contract/`, chosen on topic and labelled as
   a judgement.

Then the sweep is 80 calls and under five minutes, and the funnel it produces
still carries the caveat that **three of six gates do not exist** — the sweep
fixes the population, not the coverage.
