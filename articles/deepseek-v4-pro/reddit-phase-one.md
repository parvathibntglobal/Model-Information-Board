# Reddit phase one — the post surface

The seven phase-one tests applied to the 1,601 Reddit **post** records already on disk from the
2026-09-01 sweep. **Nothing was fetched. Zero API requests. No database writes.** Comments are
out of scope. Source: `.../scratchpad/dsv4/out/records.json`, `labels.json`, `profiles.json`.

Companion data: **`reddit-phase-one-items.jsonl`** — 16 rows, one per item, 6 passes and the 10
closest near-misses, each carrying the verbatim passage that decides it. Every quote in that file
is verified by exact substring match against the stored record, in plain Python.

---

## The result first

**6 posts pass all seven tests**, of 1,601 records — 0.37%.

| # | Stage | Items | Of |
|---|---|---:|---:|
| S0 | Post records on disk (1,568 posts + 33 crossposts) | **1,601** | — |
| — | − exact duplicates already flagged by the sweep (56) and hand-crossposts (12) | **1,533** | 1,601 |
| T0 | − high-volume accounts with no checkable external artifact (100), promo/referral tells (27) | **1,406** | 1,533 |
| T5 | − Flash-titled (197), model named body-only (257), no Pro reference (434) | **518** | 1,406 (36.8%) |
| T4 | − under the measured 100-word floor (250) | **268** | 518 |
| R2 | carries ≥1 own-execution signal | **118** | 268 (44.0%) |
| R3 | …and ≥2 condition classes | **55** | 118 |
| **✓** | **Pass all seven — T1, T2, T3 applied by hand** | **6** | **1,601** |

For scale against the platforms already swept: dev.to yielded ~7 of 620 distinct articles,
Hacker News 34 of 4,917 comments, Hugging Face 22 of 281 discussions. **Reddit's post surface
yields 6 of 1,601 — and they are better documented than the dev.to seven.** Two of the six carry
protocols stronger than most published benchmarks: one verifies 239 extracted claims against the
code with a third model plus an independent verifier, another states sampling parameters, endpoint,
trial count and retry policy before reporting p50/p95 latency.

---

## The ranking question, reported not acted on

You asked how far below the top-150 read cut the phase-one posts sit. **They do not. All six were
inside it.**

| Item | Subreddit | Rank | Read? |
|---|---|---:|---|
| [I ran a personal AI benchmark across 6 models…](https://www.reddit.com/r/GithubCopilot/comments/1t0mcov/i_ran_a_personal_ai_benchmark_across_6_models/) | r/GithubCopilot | 24 | yes |
| [DeepSeek V4 Flash (0731) vs V4 Pro (0813): I benchmarked them…](https://www.reddit.com/r/opencode/comments/1vnaje2/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813_i/) | r/opencode | 62 | yes |
| [Ollama Cloud reliability + speed: 36-call bench…](https://www.reddit.com/r/ollama/comments/1sxjbo5/ollama_cloud_reliability_speed_36call_bench/) | r/ollama | 72 | yes |
| [DeepSeek V4 in llama.cpp — Flash + Pro, CUDA + Metal…](https://www.reddit.com/r/LocalLLM/comments/1taclsw/deepseek_v4_in_llamacpp_flash_pro_cuda_metal/) | r/LocalLLM | 100 | yes |
| [I have (even faster) DeepSeek V4 Pro at home](https://www.reddit.com/r/LocalLLaMA/comments/1tdpk3f/i_have_even_faster_deepseek_v4_pro_at_home/) | r/LocalLLaMA | 120 | yes |
| [The exact KV cache usage of DeepSeek V4](https://www.reddit.com/r/LocalLLaMA/comments/1svzlog/the_exact_kv_cache_usage_of_deepseek_v4/) | r/LocalLLaMA | 159 | yes |

**A correction to the premise, and to my own first test of it.** The cut was not "the top 150 by
substance rank". The previous run read *the top 150 literal-matching records*, and their substance
ranks span **1 to 279, median 141**. So rank ≤ 150 is the wrong test — I ran it first and it
wrongly reported the rank-159 item as unread. Using the actual read set (`labels.json`, 150 entries)
all six are in it. The deepest survivor, at rank 159, was read **only because the cut ran over
literal matches rather than over the whole ranking** — under a strict top-150-by-rank cut it would
have been missed by nine places.

**So the ranking worked on posts. What it could not do is know that.**

- Of the 268 posts surviving T0, T5 and T4, the previous run read **36 (13%)**.
- Of the 55 best-conditioned candidates — own-execution signal plus two or more named conditions —
  it read **21 (38%)**. **34 went unread, at substance ranks 17 to 1,176.**
- Two of those 34 are the *part 2* posts of the highest-scoring benchmark in the corpus, at ranks
  296–298. The run read part 1 and not the follow-up.

The read cut was set by **count**, not by evidence. It happened to cover every survivor here, and
nothing in the run could have established that: the surviving set was only knowable after reading
past it. The finding is therefore not "the ranking failed" but "the ranking was not checkable" —
a stopping rule that spends its budget on a fixed 150 has no residual estimate attached, so it
cannot distinguish having found everything from having stopped early. A read cut that samples below
itself would cost a few dozen more reads and would have said which of the two it was.

This is a fact about the ranking, and it applies to comments too — but comments are out of scope
here and this pass makes no claim about them.

---

## The seven tests as applied, and the one substitution that mattered

### T0 — account, before content. The canonical clause inverts; the checkable-artifact clause works.

T0 rejects an account that published more than ~10 items about one model **and** carries no external
canonical URL. On the post surface the volume clause behaves the way it does on dev.to — only
**5 of 1,140 authors (0.4%)** clear the threshold, and the three largest are exactly the three types
the test is meant to separate:

| Author | Posts | Subreddits | Median words | ≥1 own-execution signal | External links go to | Account |
|---|---:|---:|---:|---:|---|---|
| NecessaryBear98 | 50 | 1 (r/AISEOInsider, which is only them) | 2,115 | 8/50 | **skool.com ×226**, youtube ×92 | 128 days, 572 karma |
| VexObserver | 26 | 1 (r/WhaleSeekers, only them) | 0 | 2/26 | none at all | 1,320 days |
| Jonathan_Rivera | 20 | 4 | 3,601 | 19/20 | openrouter ×94, huggingface ×20, github ×17 | 2,736 days, 18,005 karma |

The first is the dev.to generated-account pattern reproduced exactly: **the longest posts in the
corpus, the highest condition density, SEO-shaped titles, one subreddit it owns, and almost no
own-execution signal.** The third is the genuine high-volume practitioner — a megathread curator
whose posts score 91–237.

**And the canonical clause as written spares the farm.** 46 of its 50 posts carry an external
canonical URL, so it passes; the bare-headline feed, which links nothing, gets rejected. On dev.to
a canonical URL is a structural claim of provenance — this article is syndicated from a domain the
author owns. On Reddit an outbound link is just a link, and 226 of the farm's point at a paid-
community funnel.

**The substitution: not "an external canonical URL" but "a link to an artifact a reader can
independently check"** — a repo, a model page, a gist, a paper, an API doc. On that clause the
farm scores 0 and the curator scores dozens. It rejects **4 authors and 100 posts**, and it is the
same substitution the definition's own clause is reaching for; only the proxy had to change.

Two limits worth stating rather than leaving implicit. Account age cannot carry this: profiles were
fetched for post authors only, and rule 6 forbids reading an absent `created_utc` as a young
account. And the text-confirmed tell does not transfer at all — **zero posts in 1,601 leak a
`<think>` tag or "as an AI language model"**, against 21 of 620 on dev.to. One machine-generated
post in the corpus announces itself in prose instead ("compiled by AION, an autonomous intelligence
operations network", with redacted sections) and no pattern would catch it.

### T5 — the model is the subject. The strongest test on this surface.

T5 removes **888 of 1,406 (63.2%)** and it is the cheapest place to spend the cut, because a Reddit
title is a headline about a topic rather than an SEO string:

| | Posts | of 1,601 |
|---|---:|---:|
| Title names DeepSeek V4 Pro | 365 | 22.8% |
| Title names Pro and Flash | 29 | 1.8% |
| Title names DeepSeek V4, undifferentiated | 192 | 12.0% |
| **Subject-titled** | **586** | **36.6%** |
| Title names Flash only | 240 | 15.0% |
| Model named in the body only | 300 | 18.7% |
| No Pro reference at all | 475 | 29.7% |

This table is over all 1,601 records; the funnel's T5 row is over the 1,406 that survive dedup and
T0, which is why its Flash-titled count is 197 rather than 240.

Compare dev.to, where **63 of 620 (10%)** name it in the title and 84% mention it body-only. The
title test that could not be a hard gate on dev.to *can* be one here, which is why T5 runs before
the expensive tests on this surface. The 300 body-only posts are the dev.to "row in a comparison"
class and are excluded as mentions.

### T4 — length as a floor only, and the floor is measured

Not asserted at dev.to's 500 words. Measured on this corpus, the same way dev.to measured its:

| Body words | Posts | ≥2 own-execution signals |
|---|---:|---:|
| 0 | 174 | **0** |
| 1–49 | 264 | 1 |
| 50–99 | 197 | 1 |
| 100–199 | 267 | 16 |
| 200+ | 699 | 158 |

**2 of the 635 posts under 100 words carry two or more own-execution signals (0.3%), against 174 of
966 above it (18.0%).** The floor sits at ~100 words on this surface — a fifth of dev.to's, because
a Reddit post is short-form by convention. Structure is recorded, never scored: a passing post here
may be prose, and one of the six is.

### T1 — the author produced the number, applied subtractively

Delete every figure that appears in the vendor's announcement, model card or pricing page: the price
rows, 1M context, 1.6T/49B and 284B/13B, the 27%-FLOPs and 10%-KV figures, the official benchmark
table, the `0813`/`0731` strings. What must remain is an execution detail no announcement contains.

### T2 — conditions named. ≥2 attached to a specific number.

Hardware or provider, quantisation, context length, reasoning effort or sampling, harness,
checkpoint or date.

### T3 — repeatable, or a stated method.

A named task or benchmark (not "my project"), the harness or command, the baseline compared against.
Method arguments count on their own; one of the six qualifies partly that way.

### T6 — announcements and news feeds are phase two. Where the line was drawn.

**T1 asks who produced the figure; T6 asks what the item is for.** An item fails T6 when its whole
evidentiary content is a report of results produced elsewhere, however well attributed — because
what makes it useful is the original it points at, and phase one is the original. Operationally:
delete every figure whose source is named as somebody else — a model card, a leaderboard, a linked
blog, a news article, a video — and if no figure the author produced remains, the item is phase two.
A retrieval seed, not evidence.

On this surface that is the *majority* verdict, not an edge case, and it catches the corpus's most
prominent posts. The rank-17 record is a pre-release rumour digest that says of itself that nothing
in it is confirmed. The 423-point launch-day post opens "I just spent the morning running through
the model card, the architectural claims, and the pricing tiers". Both are dense, sourced, popular,
and phase two.

---

## Where the line sits: what the ten near-misses are lost to

The gap teaches more than the clear cases, and **Reddit's post surface loses its near-misses to
something different from dev.to's.**

dev.to's 53 → 16 collapse was **missing provenance**: the largest class, 21 of 53, was *unattributed*
— a conditioned comparison and a benchmark number that never say where either came from.

Reddit posts fail the opposite way. **4 of the 10 closest near-misses fail T1 while citing their
sources correctly**, and that is the dominant class:

| Failed test | Near-misses | The class |
|---|---:|---|
| **T1** | **4** | Original arithmetic over somebody else's published figures, sources linked |
| T6 | 2 | Launch-day and pre-release relay |
| T3 | 2 | Own measurement, real bill, no task another reader can re-run |
| T5 | 2 | Fully stated method, run on Flash rather than Pro |

The clearest case is a water-and-electricity calculation for V4 Pro that links every input:
ArtificialAnalysis for the token count, DeepSeek's docs for the parameters, SemiAnalysis/InferenceX
for throughput per megawatt, AWS for PUE, EESI for WUE. The joules-to-kWh arithmetic is the
author's. **Not one measurement is.** Another asks Flash to write a Python script to compute the
pricing comparison and then has Opus verify it — a clean, honest, entirely derived result.

So the two platforms fail at different points on the same axis. **dev.to's near-misses do not say
where their numbers came from; Reddit's say exactly where, and the answer is somewhere else.**
A provenance column would have caught dev.to's 21. It would pass all four of these, because their
provenance is impeccable and external. Only the subtractive test catches them, which is why the
definition specifies T1 subtractively rather than as a provenance check.

Two further near-miss classes worth naming because both are close enough to be tempting:

- **The real bill without a re-runnable task** (T3, 2 of 10). A console screenshot with
  384,499,224 tokens at a 99.6% cache-hit rate for ¥18.56 is a genuine own measurement of what Pro
  costs. It cannot answer what Pro *does*, because the workload is a production agent and the token
  count is a property of the workflow.
- **The right method on the wrong model** (T5, 2 of 10). One near-miss states a 20-call controlled
  experiment with identical prompts, `max_tokens` and a 60-second settle, plus a 48-hour
  observational study that pins quota-reset boundaries to a fixed 5-hour epoch with zero drift over
  six resets. It is better method than four of the six passes. It measures Flash.

---

## The sixteen items, with links

Machine-readable in `reddit-phase-one-items.jsonl`, one row per item, carrying the verbatim quote
that decides each verdict. Figures below are the posters' own and are **not verified**.

### The six that pass

| Post | Subreddit | Date | What makes it phase one |
|---|---|---|---|
| [Ollama Cloud reliability + speed: 36-call bench across DeepSeek v3.2 -> v4-pro -> v4-flash + GLM-5.1](https://www.reddit.com/r/ollama/comments/1sxjbo5/ollama_cloud_reliability_speed_36call_bench/) | r/ollama | 2026-04-27 | 4 models x 3 prompts x 3 trials at `temp=0.3`, `top_p=0.9`, `max_tokens=2000` on a named endpoint, retry policy stated. Reports p50/p95 latency and the reliability figure nobody publishes: 6 of 36 trials hit a transient fault, and they cluster in time. |
| [DeepSeek V4 Flash (0731) vs DeepSeek V4 Pro (0813): I benchmarked them on real code-analysis tasks](https://www.reddit.com/r/opencode/comments/1vnaje2/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813_i/) | r/opencode | 2026-08-13 | 6 task types, 18 runs, fresh sessions, repeatability runs on two tasks, models blind to the benchmark, canonical answer keys built beforehand, and 239 extracted claims verified against the code by a third model plus an independent verifier. Also posted to [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vnc7u7/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813_i/) and [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1vnccvm/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813_i/). |
| [DeepSeek V4 in llama.cpp - Flash + Pro, CUDA + Metal, GGUFs out. Help me break it.](https://www.reddit.com/r/LocalLLM/comments/1taclsw/deepseek_v4_in_llamacpp_flash_pro_cuda_metal/) | r/LocalLLM | 2026-05-11 | Ports V4 to a llama.cpp fork and publishes the quant ladder with measured sizes and bits-per-weight, including a 498 GiB Pro quant tested end-to-end on a single 512 GiB Mac Studio - plus a runnable per-op test suite with exact commands and the expected pass count. Also in [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1tad2h3/deepseek_v4_in_llamacpp_flash_pro_cuda_metal/). |
| [I have (even faster) DeepSeek V4 Pro at home](https://www.reddit.com/r/LocalLLaMA/comments/1tdpk3f/i_have_even_faster_deepseek_v4_pro_at_home/) | r/LocalLLaMA | 2026-05-15 | Throughput and time-to-first-token for **Pro itself**, swept across context depths from 0 to 16k+ on an Epyc 9374F with one RTX PRO 6000 Max-Q, through ktransformers and llama-benchy - every table reproducible from the named tools. |
| [I ran a personal AI benchmark across 6 models, DeepSeek V4 Pro delivered 287 score per dollar while Opus gave me 18](https://www.reddit.com/r/GithubCopilot/comments/1t0mcov/i_ran_a_personal_ai_benchmark_across_6_models/) | r/GithubCopilot | 2026-05-01 | Six models, identical prompt in plan mode, scored per issue on a published severity rubric (1/3/5/10) with the whole issue matrix printed, plus token and cost columns - and an explicit caveat that one test is one test. |
| [The exact KV cache usage of DeepSeek V4](https://www.reddit.com/r/LocalLLaMA/comments/1svzlog/the_exact_kv_cache_usage_of_deepseek_v4/) | r/LocalLLaMA | 2026-04-26 | Recomputes KV cache per architecture from an own llama.cpp run at FP16 and 160k context, publishes the derivation layer by layer for CSA and HCA, and corrects the vendor's own compression ratio - 7.879x not 9.5x, 12.5x not 13.7x. |

### The ten closest near-misses

| Post | Subreddit | Fails | Why it falls on the wrong side |
|---|---|---|---|
| [DeepSeek V4 Flash vs DeepSeek V4 Pro - Agent Prompt Battle](https://www.reddit.com/r/opencodeCLI/comments/1ttxclt/deepseek_v4_flash_vs_deepseek_v4_pro_agent_prompt/) | r/opencodeCLI | T1 | 12k lines of session dumps and a published writeup in a public repo, but the findings are behavioural characterisations and the one ratio given is Flash's. |
| [Considering that no one wants to calculate electricity and water consumption for new AI models, here is the calculation for Deepseek v4 pro](https://www.reddit.com/r/aiwars/comments/1tuvr0s/considering_that_no_one_wants_to_calculate/) | r/aiwars | T1 | The cleanest example of why T1 is subtractive: original arithmetic, every source linked, and not one input the author measured - token count, throughput, PUE and WUE all come from elsewhere. |
| [Deepseek v4 vs kimi k2.6 vs gpt5.5 breakdown](https://www.reddit.com/r/LLMDevs/comments/1t0o89l/deepseek_v4_vs_kimi_k26_vs_gpt55_breakdown/) | r/LLMDevs | T1 | The densest four-model comparison table in the corpus, correctly footnoted to model cards and vendor-reported throughput - which is exactly what makes it phase two. |
| [Decreased Intelligence Density in DeepSeek V4 Pro](https://www.reddit.com/r/LocalLLaMA/comments/1svbmnc/decreased_intelligence_density_in_deepseek_v4_pro/) | r/LocalLLaMA | T1 | The right axis - token efficiency rather than score - argued from the vendor's own V3.2 paper, with a 10x claim the author did not measure and no method attached. |
| [Deepseek v4 Pro 0813 - Minimal Preset on DSH vs other models](https://www.reddit.com/r/DeepSeek/comments/1vpcutr/deepseek_v4_pro_0813_minimal_preset_on_dsh_vs/) | r/DeepSeek | T3 | A controlled comparison at Max reasoning across four harnesses against a fixed git commit - but the task is the author's own project and the output cannot be shown, so no reader can re-run it. |
| [How we got 99.6% cache hit rate on DeepSeek V4 Pro for a long-context coding agent](https://www.reddit.com/r/DeepSeek/comments/1uwxvnd/how_we_got_996_cache_hit_rate_on_deepseek_v4_pro/) | r/DeepSeek | T3 | A real console bill - 384,499,224 tokens, 99.6% cached, 18.56 CNY - on a named model and date, with four stated cache techniques. A production figure, not a task score anyone else can reproduce. |
| [Glm 5.3 vs deepseek v4 usage](https://www.reddit.com/r/ollama/comments/1vzkcc6/glm_53_vs_deepseek_v4_usage/) | r/ollama | T5 | Better method than four of the six passes: a 20-call controlled experiment with identical prompts and a 60s settle, plus a 48-hour study pinning quota resets to a fixed 5-hour epoch with zero drift over six boundaries. It measures Flash. |
| [I'v tried DeepSeek V4 Spark 0731 with Lvllm-x which is a CPU-GPU hybrid inference when VRAM is not enough](https://www.reddit.com/r/LocalLLM/comments/1vo1olv/iv_tried_deepseek_v4_spark_0731_with_lvllmx_which/) | r/LocalLLM | T5 | One hardware configuration is the author's own measured run; the other two are the upstream project author's, and the model under test is Flash 0731 rather than Pro. |
| [DeepSeek V4 dropped 1.6T params and 1M context without Nvidia GPUs. Here's the data.](https://www.reddit.com/r/DeepSeek/comments/1su7rzr/deepseek_v4_dropped_16t_params_and_1m_context/) | r/DeepSeek | T6 | 423 points, and it opens by saying the author spent the morning reading the model card, the architectural claims and the pricing tiers. No execution the author performed. |
| [Deepseek V4 - All Leaks and Infos for the Release Day - Not Verified!](https://www.reddit.com/r/DeepSeek/comments/1ridmnm/deepseek_v4_all_leaks_and_infos_for_the_release/) | r/DeepSeek | T6 | The corpus's rank-17 post: a pre-release rumour digest with tables, a delay history and leaked specifications, which says of itself that none of it is confirmed. |

---

## Method, and what these numbers do not mean

**Route.** A read of `records.json` and its siblings from the 2026-09-01 run. No network, no adapter
invocation, no database connection, no writes outside the two files this report names.

**What code did and did not decide.** Every count, band, regex match and percentage here is plain
Python over the corpus. T1, T2, T3, T5 and T6 were applied **by hand** to the 55 ring-3 candidates —
all of them, regardless of rank — plus the top of the pool by triage weight; no model classified
anything. The signal detectors are **unmeasured**, so per rule 8 they order the reading and define
a stratum read exhaustively; they never gate. The 16 quotes in the JSONL are verified by exact
substring match, code checking a claim it did not make.

**Two corrections I made to my own classifier, both found by asking what a discard's denominator
was.**

1. The Flash pattern required `v4`-adjacency and so missed **`DS4-Flash`**. Two subject-classified
   posts named Flash only under the corrected pattern; one was genuinely a Flash finetune and is now
   excluded, one names Pro too and stays.
2. Exact-body dedup leaves **44 redundant records across 39 groups** — the same author posting the
   same title to two or three subreddits, bodies differing only by a per-subreddit link, so the
   sweep's hash never matched. Both of the strongest passes are in that set (one posted three times,
   one twice). Counted as one item each; the siblings travel in the `crossposted_to` field.

**Denominators for every figure that reached a conclusion.**

- 1,601 records = 1,568 posts + 33 crossposts; 727 match the name literally; 1,140 distinct authors.
- 586 of 1,601 subject-titled; 268 survive T0 + T5 + T4; 118 carry an own-execution signal; 55 also
  carry two conditions; 6 pass.
- 5 of 1,140 authors exceed the T0 volume threshold; the corrected clause rejects 4 of them, 100 posts.
- The previous run read 150 records spanning substance ranks 1–279, median 141 — 13% of the
  268-post pool and 38% of the 55 candidates.
- Body-length bands: 635 posts under 100 words, 966 at or above.

**Three things these numbers are not.**

- **Not a census, a naming rate or a sentiment measure.** They are counts over one retrieval by a
  search API with no phrase operator, capped at 3 pages per query, where **119 of 127 queries hit
  the ceiling with a cursor still available**. Every count is a floor. The endpoint returns live
  posts only: all 1,601 payloads carry NULL in every removal field, so whatever was taken down is
  invisible here.
- **Not verified.** Every tok/s, dollar and score in the JSONL is what somebody wrote on Reddit.
  Posts in this corpus contradict each other about the same model in the same week. The `quote`
  field is verified to be what they wrote — not to be true.
- **Not a complete read.** The 213 pool posts outside ring-3 were judged from title, signal
  vector and opening text rather than read in full. The residual risk sits in the 46 posts carrying
  exactly one condition class, which T2 excludes as written and which a longer read might promote.

**One asymmetry to carry forward.** This corpus says far more about what Pro costs than about what
it does, and the reason is physical: at 1.6T parameters and ~792 GB quantised, the posts that run it
locally at all are two authors' and one is a 498 GiB quant built to fit a single 512 GiB Mac Studio.
Everything else compares a hosted endpoint whose serving configuration nobody in this corpus can
see.
