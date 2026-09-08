# Phase one: the definition, and which platforms can carry it

Derived from the ten sweep reports in this folder, 2026-09-02. Every figure below carries
its denominator and names the report it comes from. Nothing was fetched; nothing outside
this folder was written.

**The finding first.** Across 104,752 items retrieved on ten platforms
(`deepseek-v4-pro-evidence-index (2).html`, headline), **553 were kept as carrying
anything checkable, and 41 report the author's own measurement on the five platforms
where that was countable.** Applying the tests below, phase one is **roughly 60 to 100
items in total** — the spread is whether arXiv's 38 baseline-evaluation papers count as
studies *of* the model or merely studies *using* it. Either way it is between 0.06% and
0.1% of what was swept, and **three platforms hold most of it.** Four platforms hold none
and should not be swept again.

---

## 1. The definition, written as tests

Six tests, ordered so the cheap ones run first. An item is phase one if it passes all six.
The order matters: T0 must run **before** T1–T4, for a measured reason given under T0.

### T0 — Account, before content

Reject the item if its account, in the sweep window, published more than ~10 items about
one model **and** carries no external canonical URL on any of them.

This runs first because on dev.to the generated accounts **beat** the independent ones on
every content signal that a filter would naturally use
(`deppseek v4 pro dev.to.md`, "The part that matters for filtering"):

| | Generated (12 accts) | Syndicated (2 accts) | Independent (132 accts) |
| --- | ---: | ---: | ---: |
| Articles | 354 | 44 | 222 |
| ≥2 non-inheritable artifacts | 170/354 (48%) | 16/44 (36%) | **37/222 (17%)** |
| First-person claim of own use | 335/354 (95%) | 13/44 (30%) | **66/222 (30%)** |
| Leaked LLM scaffolding | 21/354 (6%) | 0/44 | 0/222 |
| Median words | 1,837 | 1,190 | 991 |

All 21 leaked-`<think>`-tag cases fall inside the 12 generated accounts and zero fall
outside them, so the account cut tracks something the published text confirms by itself.
A ranking that sorts on apparent evidence density without cutting on account first puts
the synthetic material on top. The same test catches WordPress's other failure mode:
5/73 posts there are malware lures on compromised sites and are **artifact-dense by
construction** (`wp-deepseek-v4-pro-sweep.md`, "The five posts that are not articles"),
and 40/73 (55%) of bylines do not resolve to a person.

The external-canonical clause is what keeps the syndicated company blogs
(`owen_fox`, `tokenpapa` — 44 articles, 100% canonical to one owned domain, 0 leaks) from
being thrown out with the farms.

### T1 — The author produced the number

At least one quantitative claim must have been produced by the author's own execution.

**The operative test is subtractive:** delete every figure that appears in the vendor's
release announcement or model card. If nothing quantitative remains, the item fails.

This is not a formality. On dev.to the three commonest artifact kinds are precisely the
three a post gets free by paraphrasing the announcement — `version_string` 553/620 (89%),
`code_fence` 498/620 (80%), `price` 495/620 (80%) — which is why 570/620 (92%) clear a
naive "≥2 artifacts" bar. Excluding those three collapses the distribution: 397/620 carry
0 or 1 non-inheritable artifact and **zero** carry more than 3
(`deppseek v4 pro dev.to.md`, "Artifacts").

Hugging Face measures the same effect on the vendor side: 158/261 community model cards
are ≥80% textually identical to the official card, 21 are byte-identical at 13,137
characters, and 197 carry benchmark lines with a median of 29 rows — which is the
official table, reproduced (`hf-deepseek-v4-pro-sweep.md`, "Vendor claims are
quarantined"). Counted naively, 200 repos "carry benchmark numbers." They are one
company's scorecard with 200 different repo names above it.

Passing evidence is an execution detail no announcement contains: a wall-clock time, a
token count off a bill, tok/s at a named quantisation, a crash trace, a diff against a
prior checkpoint.

### T2 — Conditions named

At least two of these must be attached to a specific number: hardware or provider,
quantisation/precision, context length, reasoning effort or sampling settings, harness,
checkpoint or date.

Every item at the phase-one end does this without being asked. `47896423` (Hacker News):
4-bit expert quantisation, 209GB on disk, 4.36 tok/s, and the 2-bit version broke tool
calling while 4-bit handled it. `48149067`: 96GB M2 Max, `sysctl iogpu.wired_limit_mb=88000`
before driver glitches, ~80GB of quants fits with room for KV cache. `49219903`: V4 Pro
**at Max reasoning**, 30–60% additional time to fix output, against GLM 5.2 at Max
reasoning at 20–30% and Kimi K3 under 10%.

### T3 — Repeatable, or a stated method

A reader must be able to re-run it, or the item must make an argument about method that
another study could apply. Requires a named task or benchmark (not "my tasks"), the
harness or command, and the baseline compared against.

Method arguments count as phase one on their own. `47890702` invalidates a launch-day
benchmark because the host was being DDoSed, separating host reliability from model
quality. `49280283` corrects a conflation of few-shot prompting with one-shot vs few-shot
benchmarking — the distinction that decides whether published scores are comparable at
all. `49290033` argues pass@5 over pass@1 from self-consistency. None of these carry a new
measurement; all three are about how measurement works, and they are the most transferable
items in the corpus.

### T4 — Structure, with length as a floor only

Sections, a table, or a runnable code block that is not the vendor quickstart.

**Length does not predict evidence and must not be scored.** On dev.to, of the 453
articles over 1,200 words, 251 carry ≤1 non-inheritable artifact; median length across the
620 is 1,735 words. On WordPress the longest posts are weekly newsletters that mention the
model among thirty other items (`wp-deepseek-v4-pro-sweep.md`, "Classification").

Length works only as a floor, and there the evidence is clean: **0 of the 58 dev.to
articles under 500 words carry ≥2 non-inheritable artifacts.** Set the floor at ~500 words
on article surfaces and ~200 characters on comment surfaces — the latter is Hacker News's
own triage threshold, and the median English Hugging Face thread is 112 characters, i.e.
below it (`hf-deepseek-v4-pro-sweep.md`, "Language").

### T5 — The model is the subject, not a row

The model must be what the item is about.

dev.to: 63/620 (10%) name it in the title; 521/620 (84%) mention it body-only, as a row in
a price table or a column in a comparison. "Articles about DeepSeek V4 Pro" and "articles
that mention DeepSeek V4 Pro" differ by a factor of ten, and a keyword sweep returns the
second. arXiv is the extreme case: **the phrase appears in 0 of 43 titles** — every mention
is in an abstract, and the model is a baseline, a judge, or one of fourteen systems
evaluated (`DeepSeek-V4-Pro_arXiv_Report.md` §1).

This test is best applied at retrieval rather than after it, which is what the Hacker News
run did by searching story titles instead of comment bodies.

---

## 2. Where the line sits: the near-misses

The clear cases teach less than the gap. dev.to gives the sharpest reading of it, because
its 53-article usable set is one filter away from phase one on each side.

**53 → 16 → ~7.**

| Ring | Count | What is added |
| --- | ---: | --- |
| Independent/syndicated account + ≥2 non-inheritable artifacts | 53/620 | T0 + a weak T1 |
| …that also claim the author's own use | 16/53 | provenance is stated |
| …where the author's own run produced a number *about this model* | ~7/16 | T1 properly |

**The 53→16 gap is provenance, not evidence.** Breaking the 53 down by provenance column
(`deepseek-v4-pro-evidence-index (2).html`, dev.to rows): unattributed 21, vendor
announcement restated 10, somebody else's result repeated 5, author's own use 14, own use
+ relayed 2. The single largest near-miss class — 21 of 53 — is *unattributed*: pieces
carrying a conditioned comparison and a benchmark number that never say where either came
from. A well-copied table passes the artifact test. It cannot pass a provenance test.

**The 16→7 gap is subtler and Hashnode names it exactly.** Hashnode's 11 in-window posts
include 2 classed "author's own use," and neither measures the model: one is a setup
walkthrough for V4 **Flash** via OpenRouter, the other a multi-model gateway config that
lists `deepseek-v4-pro` among its routable models. Both show the author's own working
setup (`Hashnode_DeepSeek_V4_Pro_Sweep_2026-09-02.md` §1). So **own use is necessary and
not sufficient** — the run has to have produced a number about *this* model, not evidence
that the author configured something that could reach it.

The seven dev.to articles that survive all three rings, named so the cut is auditable:
#3 *I Gave DeepSeek a Token Limit. It Ignored Me.*; #7 *Should You Self-Host Now?*;
#10 *Replacing Claude with DeepSeek V4 in Claude Code: 30-Day, 100M-Token Cost & Quality
Test*; #38 *Across 3 APIs: Thinking Passback, Tool Calls, and Hidden 400s*;
#39 *A Cheap Model Drop Is Not a Migration Plan: Run a 30-Minute Gate*;
#41 *Its Own Benchmarks Didn't Survive a Neutral Harness*;
#51 *GA vs Preview, Measured: 18–62% Less Thinking*.

---

## 3. Which platforms can carry it

Counts are read off the reports named in the right-hand column, not re-judged here.

| Platform | Phase one exists? | Count / denominator | Source |
| --- | --- | --- | --- |
| **Hacker News** | Yes — densest per item | 34 curated of **4,917** comments in 75 subject threads; 11 first-hand; ~18 pass T1–T3 | HN subject-thread §3 |
| **arXiv** | Yes — method guaranteed, subject rare | **43 of 43** state a method; **0 of 43** name the model in the title; ~5 are about the model family rather than using it | arXiv §1, §2 |
| **Reddit** | Yes | 17 deep analysis + 29 benchmark of **150** hand-read, of **727** literal, of **1,601** records; subject-only: 7 + 12 = **19** | Reddit §3, §4 |
| **Hugging Face** | Yes, in one narrow band | **22 of 281** discussions carry ≥2 artifacts (8%); **11 of 152** English threads first-hand (7%) | HF headline |
| **dev.to** | Yes, behind an account filter | **53 of 620** distinct, of a **93,628**-article corpus; 16 claim own use; **~7** measure the model | dev.to headline |
| **X / Twitter** | As links, not as documents | 29 DEEP_ANALYSIS (22 subject) + 35 BENCHMARK (19 subject) of **149** labelled, of **573** literal, of **993** returned; no first-hand column exists | X §3 |
| **WordPress** | Barely — 3 items | **3 of 73** first-hand (4%); 27 usable but "almost all of the usable set is other people's numbers relayed"; 5 of 73 are malware | WP headline |
| **Hashnode** | **No** | **0 of 11** in-window posts report the author's own measurement; 6 core posts, and the substantive ones are cross-posted from the authors' own domains | Hashnode §1, §9 |
| **TikTok** | **No** | 137 on-target of 2,699; benchmarks/evals theme = 57 of 514 (11%) by caption keyword; usable set is the **top 30 by views**; median video 687.5 views | IG/TikTok §1, §7.1 |
| **Instagram** | **No** | 377 on-target; **no caption search exists** on the provider — hashtag feeds only; like count visible on 48.8% of posts; usable set is **top 30 by likes+comments** | IG/TikTok §2.1, §8 |

### Ruled out — four platforms, four sweeps saved

**Hashnode. Structurally unable.** Free GraphQL API retired 13 May 2026 (301/522/421 on
every endpoint); site search renders zero results server-side and loads from `/api/`,
which `robots.txt` disallows; tag pages return **the 10 most recent posts and will not
page**. There is no route to a six-month corpus, so the sample is recency-shaped on one
route and search-engine-ranking-shaped on the other. A better query cannot fix an absent
index. And the content that was reachable produced zero first-hand measurements.

**Instagram. Structurally unable.** The provider exposes hashtag feeds and no caption
search at all, so an Instagram post about the model without a DeepSeek hashtag is
invisible by construction. Ranking is by likes+comments on a platform that hides the like
count on half the returned posts. Nothing in the format carries conditions, method or a
runnable artifact.

**TikTok. Structurally unable, and its own numbers say so.** Ranking is by views, and
reach is decoupled from content: one video is 43.7% of all on-target reach, and 18 of 73
posts with known follower counts exceeded 10× their creator's following. Themes are
commercial before technical — API/deployment 228, pricing 221, benchmarks/evals 57, of
514 on-target. A "better query" would find more videos, not more depth.

**WordPress. Not structurally unable, but not worth a platform sweep.** 336 requests
returned **3 first-hand posts of 73**. The genuinely good items — MIT Technology Review,
Import AI, The Zvi's weekly, bdtechtalks — are commentary and relay, and they are known
sources reachable by name. The index also reaches Jetpack-connected self-hosted sites
(43/73, 59%), so its coverage is broader than assumed and the near-empty first-hand result
is a *stronger* negative than the brief allowed for. **Keep the ~4 named blogs as direct
fetches; drop the platform sweep.**

### A correction, because the next query depends on it

The arXiv report's summary says "There is no DeepSeek V4 Pro tech report on arXiv." That
is true only of titles. The vendor tech report is in the set at entry #40 — *DeepSeek-V4:
Towards Highly Efficient Million-Token Context Intelligence* (`2606.19348`, 2026-04-26,
DeepSeek-AI + 313 authors), whose abstract gives CSA/HCA hybrid attention,
Manifold-Constrained Hyper-Connections, the Muon optimizer, 32T pre-training tokens, and
27% of single-token inference FLOPs / 10% of KV cache versus V3.2 at 1M context. The
phase-one query must match on abstract, not title, or it will miss the single most
phase-one document in the corpus.

Separately: the folder contains no GitHub sweep, so the "GitHub tokenises on punctuation"
premise has no report behind it. The tokenisation finding on record is arXiv's — the API
tokenises quoted phrases, so all 478 fetched records had to be re-verified locally against
`deepseek[\s\-_]*v4[\s\-_]*pro(?:[\s\-_]*\d{3,4})?`. The separator-insensitivity finding
is Hugging Face's and WordPress's: `deepseek-v4-pro`, `deepseek v4 pro` and
`deepseek_v4_pro` return identical result sets on both.

---

## 4. The phase-one query, per surviving platform

Six surfaces. Not the same query on any two of them.

### Hacker News — title-scoped stories, then whole comment trees

**Change:** stop searching for the model name. Search story **titles** for it, then pull
every comment in the matching threads and judge the comments.

The evidence that this is the whole game: on thread `48237663` the phrase sweep retrieved
**22 comments** and the subject sweep retrieved **534** — the full tree, 247 of them over
200 characters. Inside a thread already titled about the model, almost nobody writes the
full name; they write *V4 Pro*, *DS4*, *DSv4*, or *it*. 15 of the 22 phrase-matched
comments landed in the throwaway tier.

- **Terms:** `deepseek`, `deepseek v4`, `ds4` — three only, with
  `tags=story&restrictSearchableAttributes=title`, time-bisected against the 1000-hit cap.
- **Then:** `search_by_date&tags=comment,story_<id>`, paginated, per thread.
- **Depth filter:** 200+ characters, then score on quantitative signals, named benchmarks
  and first-hand language — but treat the score as triage only. The 2,091-point launch
  thread drags in geopolitics and AI-economics arguments that score well on numbers and
  say nothing about the model; the previous run read the top ~70 candidates by hand and
  kept 34.
- **Cost:** ~3 title sweeps × ~10 bisected pages, plus 75 threads × 2–5 pages ≈ **250–300
  requests** for the same 4,917-comment base.

### arXiv — abstract match, then split the set in two

**Change:** nothing in retrieval — it is already complete and nearly free. Change the
post-filter.

Each variant was run restricted to the 30 active subjects and unrestricted across all of
arXiv, and both returned identical counts, so the subject filter costs nothing and hides
nothing. `deepseekv4pro` returns 1 record with 0 literal matches, and
`deepseek-v4-pro-0813` returns **0** — a regex sweep for any `deepseek-v4-pro-<digits>`
form across all 478 records found none. **Retire that variant.**

- **Terms:** `all:"Deepseek V4 pro"` and `all:"deepseek-v4-pro"` — these two return the
  full 43. Drop the other two.
- **Depth filter, split into two buckets rather than one:**
  (a) papers *about* the model — architecture, quantisation, serving, post-training
  (~5: the tech report, FlashMemory lightning-index long context, SLAI T-Rex full-parameter
  post-training on Ascend, DSpark speculative decoding, Tied Trit-Planes);
  (b) papers that *evaluate* it and publish their own numbers on it (~38). Bucket (b) is
  phase one for a benchmark question and phase two for an internals question. Do not pool.
- **Watch the surface forms.** The name is written 8 ways across 43 papers —
  `DeepSeek-V4-Pro` 23, `DeepSeek V4 Pro` 15, `DeepSeek V4-Pro` 4, and five more.
  Regex, never string equality.
- **Cost:** ~10 requests, 3-second inter-request rate limit.

### Reddit — subreddit-scoped, and include the comments

**Change two things.** First, scope to the subreddits that carry it instead of searching
the whole platform: the previous run spent 87 search queries and 1,833 API calls, and
r/DeepSeek (159 literal records), r/LocalLLaMA (40 records, 7,875 total score),
r/opencodeCLI (45), r/LocalLLM (19), r/ollama (15) and r/unsloth (3 records but 1,778 score
— the highest score-per-record in the table) hold the technical end.

Second, and more important: **the last run fetched 48,759 comments across 1,029 threads
and then excluded every one of them by instruction.** 692 matched the keyword literally.
By direct analogy to Hacker News — where the entire phase-one yield came from comments
inside subject threads and none from phrase-matched posts — Reddit's phase one is probably
sitting in that already-collected `comments.jsonl`, re-includable with `INCLUDE_COMMENTS=1`
and **no re-fetching**.

- **Terms:** the vendor's marketing spelling first. `DeepSeek V4 Pro` (title case, spaced)
  is 872 of 1,796 mentions (49%); `deepseek-v4-pro` is 143 and `deepseekv4pro` is 9. Reddit
  writes the name the way the vendor's launch post writes it.
- **Known blind spot to state in the next report:** `/getSearchPosts` and
  `/getPostsBySubreddit` return live posts only — all 1,601 post payloads carry NULL in
  every removal field while the comment trees for those same posts contain 441
  author-deleted and 820 moderator-removed bodies. Removed posts are invisible to this
  route, not absent from Reddit.
- **Cost:** 6 subreddit listings + ~200 comment threads ≈ **250 requests**, against 1,833.

### dev.to — two tags, account filter before body fetch

**Change:** cut on accounts before spending requests on bodies.

`search` is silently ignored on `/api/articles` — `search=zzqqxwvlkj` returns the same
unfiltered front page as no parameter at all — so retrieval is tag listings plus local
matching, and the tag yields are already measured: `deepseek` 275 v4-hits of 1,312
in-window articles (20.96%, and exhaustible in **2 requests**), `llm` 205 of 21,563
(0.95%, exhaustible in 24). `ai` (0.28%, 40 requests) and `programming` (0.11%, 25
requests) are both low-yield *and* truncated — they reach back only to 2026-07-23 and
2026-06-22 respectively. `chatgpt` (0.17%) and `machinelearning` (0.31%) add reach, not
density.

- **Surface:** `deepseek` + `llm` tags only. Drop the other four.
- **Depth filter, in this order:** T0 account cut (drops 354/620 before any body fetch) →
  fetch bodies for the remainder → subtractive artifact test → provenance column → T5 title
  check. Note that only 15 of the 53 usable articles name the model in the title, so T5
  cannot be applied as a hard gate here the way it can on Hacker News.
- **Do not rank on engagement.** 538/620 (87%) have zero reactions, 593/620 (96%) zero
  comments, and the most-liked article in six months got 32.
- **Cost:** ~26 tag requests + ~266 body requests ≈ **292**, against 1,603 — an 82% cut for
  the same or better yield.

### Hugging Face — skip the cards, go to discussions, add the runtime repos

**Change:** stop reading community model cards, and stop letting the id-match define the
repo set.

Search honours `search=` but scopes it to the repo **id** and matches fuzzily
(`deepseek zzz` returns 11 repos; `thinking passback`, a phrase in a card body, returns 0).
So the entire previous sweep is an id-match, which means the busiest discussions of the
model — on llama.cpp, vLLM, SGLang, unsloth — are absent **by construction**. Meanwhile
only 18 of 295 repos (6%) have any discussion at all, and 158/261 community cards are
≥80% the official card.

- **Terms:** `deepseek-v4-pro` (separator-insensitive; the spaced and underscored forms
  return the identical 301), then filter locally on the id. Add the named runtime repos
  directly rather than hoping the id-match finds them.
- **Depth filter:** discussions only, ≥2 artifact kinds, plus the bug-report and
  quantisation-question types regardless of artifact count — that band is where the yield
  is (loader crashes, quantisation size anomalies, tokeniser bugs, and the config.json
  catch below).
- **Do not filter to English and do not sort on reactions.** The single most useful item in
  the sweep — a trace of the repo's commit history showing the initial `config.json`
  shipped V4-Flash's architecture on the V4-Pro repo (`hidden_size` 4096→7168,
  `num_hidden_layers` 43→61, `n_routed_experts` 256→384), independently verified against the
  live repo — is titled 这是偷摸改啥文件了，哈哈哈, carries zero reactions, and would be
  discarded by either filter.
- **Cost:** ~120 requests against 1,266. Keep concurrency at or below 4 — 8 workers
  triggered 147 HTTP 429s in a 985-request pass.

### X / Twitter — a link-discovery surface, demoted

**Change of role, not of query.** X posts fail T3 and T4 structurally: 280 characters
cannot hold a stated method, a conditions block and a table. The 29 DEEP_ANALYSIS posts
are real, but what makes them phase one lives at the other end of their outbound links.

- **Keep:** the 32 substance-derived queries the last run added (`tech report`,
  `architecture MoE`, `1M context`, `quantization gguf`, `vllm sglang`, `I tested`,
  `my workflow`, `self host`, `fine tune`). They are cheap and they surface links.
- **Harvest §10 outbound links, not the posts.** Feed those URLs to the article-level
  tests directly.
- **Fix before running:** the `twitter241` provider reads a dead schema — X's GraphQL user
  object moved `legacy` fields to `relationship_counts` / `profile_bio` / `verification`,
  so every author is recorded as 0 followers with an empty bio, silently breaking
  `promoter_tier.py` and `reputation.py`. The OpenRouter key in `.env` returns 401, so no
  classifier can run and all labelling stays manual.
- **Cost:** ~96 requests, as before. It is the cheapest surface in the set and should stay
  in for that reason alone — just not as a source of documents.

---

## 5. What this adds up to

| | Items | Of |
| --- | ---: | ---: |
| Retrieved or read across ten platforms | — | **104,752** |
| Kept as carrying something checkable | **553** | 104,752 |
| Report the author's own measurement (5 platforms where countable) | **41** | 553 |
| Pass all six tests above — strict reading | **~64** | 104,752 |
| …counting arXiv's 38 baseline-evaluation papers as well | **~102** | 104,752 |

Phase one is rare on every platform including the good ones. Hacker News's 34 came out of
4,917 comments. dev.to's ~7 came out of 93,628 articles. Hugging Face's 22 came out of 281
threads of which 231 (82%) carry nothing checkable. The three-figure total is an artefact
of arXiv, where the method is guaranteed by the venue and the model is a baseline in 38 of
43 papers — which is a different thing from a study of the model.

Six platforms are worth re-sweeping at roughly **1,020 requests** total, against the
~5,400 the last round spent on ten. Four are not worth re-sweeping at any cost.
