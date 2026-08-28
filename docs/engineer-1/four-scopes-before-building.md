# Four things scoped, with costs. Nothing built

**One of the four premises is superseded by a measurement already on disk, and it
changes the ranking of all four.** That correction is §0. The scopes follow.

*Engineer 1 · 2026-08-28 · no model calls, no fetches, no writes. Two read-only
measurements over corpora already held — method and denominators in §0.3*

---

## 0 · Corrections and method, before any of the four

### 0.1 · "GitHub is 76% of token cost on 13.5% of units" no longer holds

It was mine, it was true of the quantity it measured, and
`docs/measurements/the-output-ratio-and-reddits-two-missing-paths.md` (2026-08-24,
already committed) replaced it. The 76% is a share of **document input tokens**.
The billed quantity is the **request**, and the request carries ~1,882 tokens of
system prompt, JSON schema and twelve capability keys on every call:

```
                units    input tokens    of which fixed overhead    cost (mean out)
reddit           190       360,692        357,580   (99.2%)          $0.1981
blog             120       349,514        225,840   (64.6%)          $0.1616
github            53       521,045         99,746   (19.1%)          $0.1814
                        -----------    -----------                  -------
                          1,231,251        683,166   (55.5%)         $0.5412
```

**GitHub is 36% of the money, not 76%**, and **55.5% of all input tokens are the
prompt rather than the corpus**. The whole batch is $0.54 at the measured mean,
not $0.93.

Two consequences that govern §4, and one that governs §2:

- The largest single line item in the extraction budget is not any document. It
  is the per-call constant, paid 391 times. **That is a unit-of-call decision,
  not a filtering decision**, and it is bigger than every filter below combined.
- Ranking pre-call filters by *tokens saved per document* ranks them wrongly.
  Rank by **units removed**, because a removed unit takes ~1,882 tokens of
  overhead with it whatever the document weighs.
- Reddit's 94-character comments cost 2,113 input tokens each. Reddit is the
  most expensive corpus per unit of evidence, and it is the one that can be
  neither swept nor assembled.

### 0.2 · What did not change

`0.39%` GitHub against `0.42%` blogs, per-entry — the figure the brief cites for
§1 — stands. It was pre-registered, run, and it retracted my own coverage
argument. `docs/measurements/prediction-signal-on-prose.md`.

### 0.3 · The two measurements run today, with their denominators

Both are code-only, deterministic, and re-runnable. No model participated.

```
GITHUB   53 stored issue payloads in _sweep_store/flattened/
         (the same 53 the cost model used; median 23,022 chars payload,
          17,407 chars title+body)
BLOG    190 flattened article texts in raw_store/flattened/
         (median 2,908 chars; 1,310,585 chars total)
```

**Population caveat, and it bounds every drop rate below.** The entity gate was
run against a population built from `contract/seed_models.yaml` — **11 models, 71
surfaces**. Staging carries 340 models and 41 are seated. A narrower population
drops *more* documents, so every `no-resolvable-entity` figure here is an **upper
bound on the drop** and a lower bound on survival. The independently-measured
figure from the real registry agrees in order: 23 of 119 blog documents name any
model, 15 resolve to one (`nine-feeds-and-one-writer.md`).

Method, so the numbers carry it: `judge.vet.reject.check` run over each corpus
with `links` extracted by `https?://\S+`; `collect.triage.gates.triage` run over
each corpus against `build_population(seed_models, declared_variants)`. Nothing
was written; both scripts were one-shot `python -c` invocations.

---

## 1 · Per-platform query rendering

### 1.1 · The retraction shrinks this to one module and zero contract changes

The withdrawn proposal was per-platform **terms**, and it needed a
`contract/queries.yaml` schema change plus a `TermSet` change plus platform
selection in `plan_searches`. Per-platform **rendering** needs none of those.
`collect/adapters/queries/` is already split for it — the package docstring says
so: *"RETRIEVAL broad and cheap, whatever an index honours. SIEVE local, exact,
identical on all three platforms."* `contract.py` and `sieve.py` are already
platform-neutral. `github.py` is the only platform-bound module.

**So the shape is: one new sibling, `collect/adapters/queries/reddit.py`, with
the same two entry points.**

```
render_search(entry, alias, ...) -> SearchRequest | Unrenderable
plan_searches(entries, aliases, ...) -> SearchPlan
```

Blogs need no renderer at all. RSS is a fetch of a known URL; the same terms are
already a post-fetch relevance filter there.

### 1.2 · It is not a mirror of `github.py`, and the difference is the point

GitHub's renderer exists to *avoid syntax the index silently discards*:
`FORBIDDEN_SYNTAX` refuses ` OR `, `(`, `)` and `*`; `github_alias_form`
hyphenates a trailing numeral so `claude sonnet 5` cannot collect issue #5; one
narrowing token is appended because the index cannot OR two.

Reddit has **no operators to forbid**. Measured: there is no phrase operator, it
degrades to OR over tokens, `"rolled back"` returns posts containing `back`
without `rolled`, and a literal `OR` is just another token. So a Reddit renderer
cannot narrow, and its job is the opposite of GitHub's: **decide how few tokens
to send, accept that retrieval carries no precision, and record that as a
coverage fact rather than as a query property.**

Two things carry over unchanged and should not be re-derived:

- The **substitution refusal**. `direction: decided_at_extraction` is a fact
  about the pipeline, not about an index, so both platforms refuse the same 2 of
  26 entries for the same reason. 24 entries render.
- The **retrieve-once-sieve-against-every-spelling** rule in `SearchRequest`.
  Worth 28 documents of 136 on GitHub for zero extra requests, and there is no
  reason it would be platform-specific.

One thing genuinely open: **nobody has measured whether Reddit has a numeral
collision** of the kind `github_alias_form` exists to fix. Cost to settle: 2–4
search requests.

### 1.3 · Cost, and what it does and does not buy

```
build        ~250-350 lines + tests, mirroring github.py's contract    ~1 day
contract     none
HTTP         2-4 requests to settle the numeral question
```

**Buys:** efficiency — a query rendered for GitHub wastes requests on Reddit.
**Does not buy:** coverage. The per-entry signal rate is 0.39% on GitHub against
0.42% on blogs, so no request experiences the vocabulary-wide gap. The coverage
lever is the **101 of 207 terms that fire on neither platform**, and it is
platform-independent and larger than this.

### 1.4 · Recommendation: do not build this first

A renderer is the *query* half of a decision that may not be query-shaped.
`/getPostsBySubreddit` takes no query at all, and §2 is a ruling on whether
Reddit's unit of retrieval is a query or a subreddit-and-window. Building the
renderer before that ruling is building for one of two answers.

---

## 2 · A Reddit sweep

### 2.1 · Most of the 2026-08-18 proposal's blockers have closed

| blocker | state |
|---|---|
| terms ruling | **landed** — `reddit-via-rapidapi`, `contract/sources.yaml:367`, reviewed 2026-08-18, four unresolved conditions recorded, escalated to the MD |
| the gate factory | **landed** — `harvester_for_source`, `collect/adapters/reddit.py:948` |
| a document writer | **landed** — `collect/adapters/reddit_write.py`, canonicalising `author_id` |
| quota, exactly | **measured** — 1 request = 1 quota unit, exact over 558 requests and per call over the last 186; window is 23.893 days, limit read at 1,000,000 with `monthly_limit_is_billed_tier: null` |
| the subreddit list | **not written.** `sweep_subreddits` is proposed in `docs/proposals/reddit-sweep-contract.md` §2.4 and does not exist in `contract/sources.yaml` |
| the sweep itself | **not written** |

### 2.2 · Two shapes, and choosing between them is a ruling, not a build

**A · Query shape — port GitHub's.** `/getSearchPosts`, one query per (entry, alias).

```
plan            24 renderable entries x 41 seated models  =  2,176 requests/day
                (the same plan GitHub computes today)
wall clock      2,176 / 25 per minute                     =  87 minutes
contract        harvest.yaml sets max_minutes: 35 daily   -> 2.5x OVER, before
                                                              one comment fetch
quota           2,176 x 23.893-day window = 51,990        =  5.2% of the read
                                                              1,000,000
                                                              10.4% if the billed
                                                              tier is the plan
                                                              page's 500,000
plus            1 /getPostComments per survivor
```

**B · Listing shape — reuse `unfiltered_sweep.py`'s.** `/getPostsBySubreddit`,
12 subreddits × 7 pages × 25.

```
plan            84 requests/day
wall clock      ~3.4 minutes
quota           84 x 23.893 = 2,007                       =  0.2%
```

**The trade is precision against a selection effect, and it is already written
down.** `unfiltered_sweep.py` avoids `/getSearchPosts` deliberately — *"the index
ranks, and ranking is the selection effect this exists to escape."* Shape A buys
alias-scoped retrieval and re-imports that effect. Shape B has no query, so the
sieve does 100% of the work — which is where the contract's terms already do
their work by design, and which makes §1's renderer unnecessary for it.

### 2.3 · How much of the GitHub sweep's shape reuses

**Reusable as-is:** `SweepReport` (including `unreached`, `excluded`,
`marked_swept`, `ledger_failures`), `seated_variants`, `mark_swept`,
`excluded_seats`, `open_harvest_run`/`close_harvest_run`, the two-phase
commit-per-query arrangement, the sieve, `RedditRun.harvest_run_fields`,
`harvester_for_source`, `reddit_write.write_documents`.

**Not reusable, and each is a real cost:**

- `plan_searches` / `render_search` — GitHub-bound. See §1.
- `sweep_budget`. `contract/harvest.yaml`'s `sweep_budget` has **no platform
  dimension**, so one cap governs both platforms, and GitHub's 900/35 is not
  Reddit's constraint. Contract change.
- **Reddit's binding constraint has no representation anywhere.** The cap that
  matters is a monthly quota, and `harvest_run.truncated_by`'s CHECK has no
  `'quota'` value — the adapter says so in its own comment and carries
  `quota_exhausted` as a separate field precisely because it could not be
  folded in. Migration.

```
sweep_reddit stage beside sweep_github                    ~200 lines
harvest.yaml per-platform budget + a quota ceiling        contract change
truncated_by vocabulary + quota columns                   one migration
sweep_subreddits block (shape A does not need it)         contract change
```

### 2.4 · The blocker that makes all of it premature

**190 of 191 Reddit documents have no `thread_context`, and `judge/` reads
`thread_context`.** `collect assemble` exposes only `github`. A Reddit sweep
built today adds documents the extractor cannot see.

`assemble reddit` is the smaller job, the same shape as `assemble github`
(~120 lines + a batch driver, ~1 day), and it pays for itself twice: it makes 190
held documents extractable, and it collapses 190 calls into a handful of threads
— which is the §0.1 finding and the largest single saving available anywhere in
§4.

**Recommendation: `assemble reddit` first, the shape ruling second, the sweep
third.**

---

## 3 · Blog feed expansion

### 3.1 · Adding feed number ten re-opens the ruling

This is the binding cost, and it is a person's time rather than code. The class-A
ruling states it in its own text:

> RE-REVIEW REQUIRED BEFORE: any external publication, any external user, any
> monetization, **or adding a feed outside the nine assessed.**

So a tenth feed is not a row. It is a dated re-reading by a named person, with
`reviewed_on` and `review_valid_days` reset, of a ruling that currently records
that **no terms page has been read for any of the nine feeds** and that robots
permission and terms permission are different documents.

### 3.2 · Per feed, what a row actually requires

| block | content | cost |
|---|---|---|
| `terms_ruling` | which ruling this feed falls under | the re-review above |
| `terms_evidence` | robots status + http, feed path allowed, article path allowed, article http, paywall observed, login required, feed type | ~3 requests; **the robots half is already automated** — `collect/adapters/blog/robots.py`, re-read every run, cached one hour per host |
| `measured` | 12 fields incl. `byline_source`, `declared_author`, `resolves_to_voices`, `median_body_chars`, `version_rate` | 1 feed fetch + a person reading it |
| `template_block` | `status`, `checked_on`, `pages_examined`, `headings` | **the expensive one.** Willison took 62 pages examined; the contract is explicit that `unverified` must never read as "no template block" |
| `base_trust`, `provenance` | a judgement | a person |

**The current list already carries a debt here:** 2 feeds strip, 3 are verified
clean, **4 have never been looked at**. Adding feeds without clearing that makes
a rule that fires on two feeds and silently does nothing on eight.

### 3.3 · Is there a free API that gives many engineering blogs at once?

**No, and the reason is structural rather than a gap in the market.**

Aggregators with free APIs — Hacker News' Algolia index, Lobsters, dev.to,
r/programming — return **links to third-party hosts**. The fetch target is still
one host at a time, so `robots.txt`, the paywall and login observations, and the
terms ruling all remain **per host**. An aggregator removes *discovery* cost.
Discovery is not what is expensive here; **permission is**, and the aggregator
does not touch it.

The only shape that genuinely collapses many blogs under one ruling is a
**platform** — Medium, dev.to, Hashnode — where one party's terms cover every
publication on it. We have the precedent and it is not encouraging:
`blog-class-b-medium` is `fetch_articles: false`, feed only, refused twice over
— and both Medium-hosted feeds returned **0 articles** in the last sweep.

*Not verified in this session: the current terms and response shape of the
aggregator and platform APIs named above. The structural argument does not depend
on them; a decision to use one would, and each is one reading plus one request to
settle.*

### 3.4 · The yield finding says feed count is the wrong lever

```
nine feeds, last sweep    105 articles offered    104 already present    1 new
model-naming, non-Willison        8 of 75
resolving to one model            5 of 75
entity gate, measured today      19 of 190 blog documents pass   (upper-bound
                                                                  drop, §0.3)
```

**"Engineering blog" is not one channel.** A practitioner link blog names model
versions constantly, because naming the model is the point of the post. A company
engineering blog names architecture and almost never a version. They share a
retrieval mechanism and a terms class and they are different populations. The
three corporate feeds — Grab, Slack, Spotify — contribute **1 model-naming
document each and 0 that resolve to a single model**.

So adding company feeds costs a full ruling re-review and buys approximately no
evidence. The class that pays is practitioner link blogs, and there are not many
of them. `contract/sources.yaml` classifies feeds by *terms*, which is the right
axis for permission and the wrong axis for yield, and nothing in the contract
records which kind a feed is.

### 3.5 · The cheapest item in this lane is not a feed

`watermark.etag` and `watermark.last_modified`. Conditional GET is **designed,
tested and unwired** — `BlogFetcher` defaults to `InMemoryValidatorStore` and the
durable columns are an unagreed contract change. Until they land, **every blog
sweep costs the full ~123 requests including feeds that have not changed**, which
is what the last sweep proved when Willison's feed returned all 30 entries rather
than a 304.

---

## 4 · Pre-LLM filtering

### 4.1 · Nothing filters before the model call today except one nine-character test

`judge/extract/placeholder.py` skips `[removed]` and `[deleted]` bodies. That is
the entire pre-call filter set in production.

`collect/triage/` computes six gates, three of them built, all of them tested —
and **nothing persists their output**. `chain.py` carries
`Stage("triage", run=None, ...)` whose own `starves=` text says
*"document.status and document.specificity_score, which no writer sets today"*,
and `triage_verdict` is NULL on 254 of 254 rows.

**This is the load-bearing fact for E2's proposal.** Moving the promotional
hard-rejections from vet into triage is right, and today it moves them into a
stage that does not run. The proposal's value is realised by wiring triage, not
by relocating three regexes.

### 4.2 · Every decision made after the model call, and whether it could move

| decision | module | needs model output? | movable? | measured saving |
|---|---|---|---|---|
| placeholder body | `extract/placeholder.py` | no | **already pre-call** | 6 of 4,153 documents |
| schema salvage | `extract/runner.py` | yes | no | — |
| **quote verification** | `extract/verify.py` | yes | **never.** Rule 1 works because proposer and checker are different things | — |
| affiliate link | `vet/reject.py` | no — text + links | **yes** | **0 of 243** |
| sponsored disclosure | `vet/reject.py` | no — text | **yes** | **0 of 243** |
| discount code | `vet/reject.py` | no — text | **yes** | **1 of 243** — see 4.3 |
| syndicated duplicate | `vet/reject.py` | no — needs `dedup_cluster` | **yes, once dedupe runs**; `Stage("assemble-dedupe", run=None)` | unmeasurable today |
| predates model | `vet/reject.py` | its input is `claim.model_ref.resolved_version_id`, **which nothing populates** | **yes**, fed by `collect/surface_resolver.py` instead | **0 today, by construction** |
| no resolvable entity | `triage/gates.py` | no | **yes — built, tested, unwired** | blog **171 of 190**; github **7 of 53** |
| too short, no artifact | `triage/gates.py` | no | yes, unwired | blog 1 of 190; github 0 of 53 |
| out of window | `triage/gates.py` | no | yes, unwired; needs an `in_window` map | not run |
| claim resolves to no tracked model | `pipeline.py` | after the call | **the same question the entity gate asks, one stage and one paid call later** | as above |
| `has_numbers` disagreement | `pipeline.py` | yes | no — a quality signal, not a filter | — |
| quote names another model | `pipeline.py` | yes | no | — |
| weighting, `n_eff`, consensus | `vet/weight.py`, `curate/gate.py` | yes | no | — |

### 4.3 · Three things the measurement found that the enumeration would not

**The promotional rules never fire on the corpus that was thought to be
expensive.** 0 of 53 GitHub issues trigger any of the five. They are a
blog-and-Reddit-shaped filter, and GitHub carries none of the shapes they match.

**The one blog document they reject looks like a false positive by the rule's own
definition.** `discount_code` fires on a 69,934-character LLM-evals guide for the
string `discount code` — a 25% discount on *the author's own course*, not on
"the product being reviewed", which is what the rule's docstring says it catches.
That does not argue against moving the rule earlier; the verdict is identical at
either position. It argues that the rule needs a provider-proximity condition of
the kind `_is_tracked_provider_link` already applies to the affiliate rule, and
that `/filtered` will carry this document either way.

**The affiliate rule is running on nearly empty input.** Across 190 flattened
blog documents the link extractor found **49 URLs total**. Flattening resolves
markdown links away, so `links=` is close to empty by the time vet sees it, and
`_is_tracked_provider_link` has almost nothing to test. Moving the rule earlier
in the pipeline would put it *closer* to the raw HTML, which is where its input
actually lives — a correctness gain the cost argument does not mention.

### 4.4 · Ranked by measured saving, against the corrected $0.5412 base

**1 · Change the unit for Reddit — `assemble reddit`.** 357,580 of Reddit's
360,692 input tokens (99.2%) are fixed per-call overhead, paid 190 times to read
3,040 tokens of comment text. Collapsing 190 calls into a handful of thread
contexts saves on the order of **$0.10–0.15 of a $0.54 batch**. It is not a
filter, it is the largest single saving available, and it is already §2.4's
recommendation for an unrelated reason.

**2 · Wire triage and let the entity gate run.** Blog: **171 of 190 units**
removed at ~2,698 in + 189 out per unit ≈ **$0.22 at the seed population**, less
at the real registry — see the §0.3 bound. GitHub: 7 of 53, because those
documents were *retrieved by a query containing an alias*, so they contain one.
That circularity is the same one that made the 82.8% figure uncomparable, and it
means the entity gate is a blog-and-Reddit lever, not a GitHub one.

**3 · The prompt overhead itself.** 683,166 of 1,231,251 input tokens — **55.5%**
— is system prompt, JSON schema and twelve capability keys, byte-identical on
every one of 391 calls. **This is larger than every filter in the table
combined.** It is a caching-and-batching question rather than a filtering one,
and the cheapest next action in §4 is one reading of the extractor provider's
current caching terms and minimums against a 1,882-token constant. Not costed
here, because I would be costing it from memory.

**4 · Move the promotional hard-rejections into triage (E2's proposal).**
Measured saving: **1 of 243 documents**, and that one is arguably a false
positive. **Do it, and do it on the correctness argument, not this one** — the
four claims on staging are quotes from a product announcement with polarity
positive, which is exactly what these rules exist to stop, and they currently run
after the money is spent. The cost case for it is real and small; the correctness
case is the one that carries it.

**Not on the list, and why:** stripping the JSON envelope from GitHub payloads
saves 11.3% of GitHub input (title+body is 88.7% of a stored payload), and
GitHub's overhead-inclusive share is 19.1% of input, so the whole move is worth
about 2% of input tokens. Stripping excluded containers — code fences,
tracebacks, logs — would take GitHub input to 73.9% of payload, and it is
**refused**: `collect/CLAUDE.md` requires code fences, error strings, diffs and
numbers-with-units preserved verbatim because they are the specificity signal,
and rule 1 requires the quote to exist in the text the extractor was given.
Stripping them would make a whole class of the highest-signal quotes
unverifiable.

---

## 5 · The ordering that falls out

Nothing here is a recommendation to build the four things in the order they were
asked in. Three of them are downstream of one decision and one measurement.

```
1  assemble reddit          §2.4 and §4.4 arrive at it independently. ~1 day.
                            Unblocks 190 documents AND removes the largest
                            single cost line.
2  read the caching terms   §4.4 item 3. 55.5% of input tokens. One reading.
3  wire triage              §4.1. The gates exist and are tested. Wiring them
                            is what makes E2's proposal mean anything, and it
                            is the second-largest saving.
4  rule the Reddit shape    §2.2. Query or subreddit-and-window. Not mine
                            alone, and §1 is downstream of the answer.
5  the Reddit renderer      §1, only if the ruling goes to shape A.
6  blogs                    §3.5 first — conditional GET, blocked on a contract
                            change, not on work. Feeds after, and only
                            practitioner link blogs.
```

**What I am not proposing:** any change to `contract/queries.yaml`,
`contract/sources.yaml` or `contract/harvest.yaml`. Three are named above as
required contract changes — a per-platform sweep budget, a quota vocabulary on
`truncated_by`, and the conditional-GET columns — and each is a proposal to be
made, not an edit to take.
