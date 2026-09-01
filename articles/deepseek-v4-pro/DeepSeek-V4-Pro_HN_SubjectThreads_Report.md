# DeepSeek V4 Pro - Subject-Thread Analysis (Hacker News)

**Run (UTC):** 2026-09-01T11:05:05.443041+00:00  
**Source:** Algolia HN Search API - `https://hn.algolia.com/api/v1`, `tags=comment,story_<id>`  
**Subject threads found:** 167 (75 with discussion)  
**Comments fetched:** 4917  
**New detailed analysis cases:** **34** (none appear in the phrase-sweep report)

---

## 1. Why this run exists

The prompt for this was [48237663](https://news.ycombinator.com/item?id=48237663) - *DeepSeek makes the V4 Pro price discount permanent*, 621 points and 549 comments. The first HN report captured that story but only **22 of its comments**, because the sweep matched on the literal phrase `deepseek...v4...pro`. Inside a thread already titled about the model, almost nobody writes the full name - they write *V4 Pro*, *DS4*, *DSv4*, or just *it*. Most of the subject-based discussion was therefore invisible to a phrase query, and what did match skewed short - 15 of those 22 landed in the rubric's throwaway tier.

This run inverts the approach: find the threads whose **own title** is about the model, then pull **every comment** in them and judge the comments on analytical content rather than on whether they spell the name out.

| | Phrase sweep (first report) | Subject-thread sweep (this one) |
|---|---|---|
| Unit of search | items containing the phrase | threads about the model, then all comments |
| Corpus | 675 phrase-verified items | 4917 comments in 75 threads |
| Comments retrieved from 48237663 | 22 | 534 (the whole tree; 247 with 200+ chars) |
| Detailed analysis cases | 89 | 34 (all new) |

### Subject threads by variant

| Thread subject | Threads |
|---|---|
| flash-specific | 60 |
| V4 (undifferentiated) | 58 |
| Pro-specific | 49 |

Flash-specific threads are kept in the corpus but a comment there qualifies only if it names Pro explicitly; in Pro and undifferentiated-V4 threads the subject is established by the thread itself. That leaves 1570 subject-relevant comments of 2216 with 200+ characters.

### The threads that carry the discussion

| Date | Thread | Pts | Comments |
|---|---|---|---|
| 2026-04-24 | [DeepSeek v4](https://news.ycombinator.com/item?id=47884971) | 2091 | 1607 |
| 2026-05-22 | [DeepSeek makes the V4 Pro price discount permanent](https://news.ycombinator.com/item?id=48237663) | 621 | 549 |
| 2026-08-07 | [DeepSeek V4 Flash 0731](https://news.ycombinator.com/item?id=49214008) | 796 | 476 |
| 2026-08-12 | [DeepSeek V4 Pro 0813](https://news.ycombinator.com/item?id=49274600) | 1041 | 453 |
| 2026-05-01 | [DeepSeek V4 – almost on the frontier](https://news.ycombinator.com/item?id=47977026) | 677 | 398 |
| 2026-07-31 | [DeepSeek-V4-Flash Update](https://news.ycombinator.com/item?id=49119559) | 745 | 347 |
| 2026-07-31 | [DeepSeek V4 Flash 0731 Intelligence, Performance and Price](https://news.ycombinator.com/item?id=49120299) | 594 | 312 |
| 2026-05-03 | [DeepClaude – Claude Code agent loop with DeepSeek V4 Pro](https://news.ycombinator.com/item?id=48002136) | 678 | 281 |
| 2026-06-08 | [DeepSeek V4 Pro beats GPT-5.5 Pro on precision](https://news.ycombinator.com/item?id=48440448) | 397 | 225 |
| 2026-05-14 | [A few words on DS4](https://news.ycombinator.com/item?id=48142108) | 440 | 190 |
| 2026-08-21 | [DeepSeek-v4-flash-vision-exp](https://news.ycombinator.com/item?id=49386163) | 498 | 155 |
| 2026-08-04 | [DeepSeek V4 Flash on a Single AMD MI300X](https://news.ycombinator.com/item?id=49166386) | 382 | 109 |
| 2026-05-06 | [DeepSeek V4 Pro at 75% off until 31 May](https://news.ycombinator.com/item?id=48043040) | 87 | 86 |
| 2026-05-16 | [DeepSeek-V4-Flash means LLM steering is interesting again](https://news.ycombinator.com/item?id=48160807) | 280 | 76 |
| 2026-06-29 | [DeepSeek V4 Peak Valley Pricing Change](https://news.ycombinator.com/item?id=48717869) | 54 | 33 |
| 2026-05-15 | [DeepSeek V4: The Open-Source Model Frontier Labs Feared](https://news.ycombinator.com/item?id=48145171) | 85 | 31 |

---

## 2. What the subject threads add

Four things that the phrase-based corpus did not contain at all:

- **Variance, not just averages.** The most useful benchmark commentary here is about *reliability* - pass@1 versus pass@3 behaviour, and a claimed 30-60% rework rate at Max reasoning. Leaderboard tables never show this, and no phrase-matching comment did either.
- **Quantization ground truth.** Concrete numbers on what breaks: 2-bit quantization kills tool calling while 4-bit survives at 209GB and 4.36 tok/s; large MoE at 2-3 bits loses to dense 30B at 4-8 bits despite 5x the VRAM.
- **Per-task rather than per-token cost.** A commenter's own SQL benchmark has Kimi K2.5 at double the per-token price coming in cheaper per task ($0.05 vs $0.16 for equal score) - the inverse of the headline pricing story.
- **Structured dissent.** Because these are threads about the model, the sceptics show up: the compounding-5%-per-stage argument, the $200-plan user for whom any regression costs more than it saves, and the direct rebuttal that Flash 0731 already superseded Pro.

---

## 3. The 34 new analysis cases

All are comments inside subject threads, none matched the phrase sweep. Each note says what the item establishes; figures are the commenters' own and are reproduced, not verified.

### Benchmark results and evaluation methodology (8)

**[49282918](https://news.ycombinator.com/item?id=49282918)** - 2026-08-13 | by minraws | in *DeepSeek V4 Pro 0813* (1041 pts)
  - Argues the model is unreliable at pass@1 but matches Sol/Fable at pass@3, and speculates GRPO is the cause - a variance claim no leaderboard number captures.
  - > Deepseek V4 Pro 0813 is the most unreliable model I have tried, it works on pass@3 shockingly well you can get it to match Sol or Fable perhaps in task done, but it's horrendous at pass@1 very prone to going wrong and doing horribly at most benches. I am not sure what it is buy I suspect it might be GRPO.

**[49290033](https://news.ycombinator.com/item?id=49290033)** - 2026-08-13 | by computerex | in *DeepSeek V4 Pro 0813* (1041 pts)
  - Follow-up on why pass@k matters: self-consistency gives no guarantee the right answer is selected, so pass@5 would be more informative than pass@1.
  - > Yes, and the reason why pass@k exists is because of self-consistency. There is no guarantee for right answer to be selected or for the LLM to correct itself. While I agree pass@1 is a useful metric, I'd be more interested to know pass@5 so I can better compare the results.

**[49288853](https://news.ycombinator.com/item?id=49288853)** - 2026-08-13 | by WASDx | in *DeepSeek V4 Pro 0813* (1041 pts)
  - DeepSWE moved 53% -> 63%; notes DeepSeek's own measurements show a larger gain than Artificial Analysis, and that DeepSWE currently shows a lower total cost for Pro.
  - > On DeepSWE it's now 53% vs 63% which is one of the coding benchmarks I trust the most. DS own measurements also show a more significant increase so I suspect AA might update when they release an article. Surprisingly DeepSWE currently shows a lower total cost for pro so that might also update I guess. As usual, don't trust the benchmarks and try for yourself.

**[49280283](https://news.ycombinator.com/item?id=49280283)** - 2026-08-13 | by nl | in *DeepSeek V4 Pro 0813* (1041 pts)
  - Corrects a conflation of few-shot prompting with one-shot vs few-shot benchmarking - the distinction that decides whether the published scores are comparable at all.
  - > > An agent doing a task with 1 example is one shot. An agent doing a task with a few examples is few shot. I don't think you are correctly using these terms This is a different thing. Yes, giving multiple example is called "few-shot prompting". But one-shot vs few-shot benchmarking is different. In this context "one-shot" means "pass at 1 effort" as opposed to "multi-shot". In the literature this...

**[49275726](https://news.ycombinator.com/item?id=49275726)** - 2026-08-12 | by bel8 | in *DeepSeek V4 Pro 0813* (1041 pts)
  - Lines V4-Pro-0813 up against Fable 5 across eight benchmarks (HLE w/tools 60.0 vs 63.0, Terminal Bench 87.9 vs 88.0, Cybergym 83.3 vs 83.1, DeepSWE 62.7 vs 70.0, Toolathlon 74.1 vs 77.9, AutomationBench 31.8 vs 29.1, DSBench-FullStack 71.1 vs 77.2, DSBench-Hard 67.2 vs 68.3) to ask whether it is Fable-class.
  - > So it's a Fable class LLM? DSV4Pro vs Fable5 HLE w tools 60.0 vs 63.0 Terminal Bench 2.1 87.9 vs 88.0 Cybergym 83.3 vs 83.1 DeepSWE 62.7 vs 70.0 Toolathlon-Verified 74.1 vs 77.9 AutomationBench (Public) 31.8 vs 29.1 DSBench-FullStack 71.1 vs 77.2 DSBench-Hard 67.2 vs 68.3

**[48262873](https://news.ycombinator.com/item?id=48262873)** - 2026-05-25 | by nl | in *DeepSeek makes the V4 Pro price discount permanent* (621 pts)
  - Per-task rather than per-token costing from the author's own SQL benchmark: Kimi K2.5 is ~2x the per-token price of V4 Pro but came in at $0.05 vs $0.16 for the same score.
  - > It's not unheard of for "more expensive" models (on a per-token basis) to end up cheaper than weaker models (on a per-task basis). Kimi K2.5 is roughly double the price (per token) of DeepSeek v4 Pro, but cost $0.05 vs $0.16 (for the same score) on my own benchmark. https://sql-benchmark.nicklothian.com/?highlight=moonshotai_... https://sql-benchmark.nicklothian.com/?highlight=deepseek_de...

**[48007979](https://news.ycombinator.com/item?id=48007979)** - 2026-05-04 | by connorwhitlock | in *DeepClaude – Claude Code agent loop with DeepSeek V4 Pro* (678 pts)
  - Points out 96.4% LiveCodeBench is single-shot, and asks for a multi-turn agentic comparison against Opus at 30+ tool-call depth to find the cliff.
  - > 96.4% on LiveCodeBench is impressive but LiveCodeBench is single-shot. The interesting test is multi-turn agentic — has anyone benchmarked DeepSeek V4 Pro vs Opus on SWE-bench Verified or similar where the cheaper model has to be more decisive about tool use over 30+ turns? Curious if there's a cliff at higher tool-call depths.

**[47890702](https://news.ycombinator.com/item?id=47890702)** - 2026-04-24 | by coder543 | in *DeepSeek v4* (2091 pts)
  - Methodological takedown of a launch-day benchmark that scored the model while its host was being DDoSed - separates host reliability from model quality.
  - > Your “benchmark” is invalid. Penalizing the model because the hosting environment is being DDoSed by users a few hours after launch is utter nonsense. I see that you tried to justify this lower in the thread, but no… it completely invalidates your benchmark. You are not testing the model. You are conflating one specific model host and model performance, and then claiming you are benchmarking the m...

### Cost, caching and self-hosting economics (8)

**[49281132](https://news.ycombinator.com/item?id=49281132)** - 2026-08-13 | by p1necone | in *DeepSeek V4 Pro 0813* (1041 pts)
  - Reports 99%+ cache-hit rates even without pinning a provider, and that most providers charge ~10x DeepSeek's own cached-token price.
  - > This has not been my experience. Generally I do pin to 1 provider, or 1 provider with a couple fallbacks (especially with deepseek - most providers are 10x the cached token price compared to deepseek themselves), but even when I don't I still usually see 99%+ cache hit percentage. Specifically using pi with various ad-hoc customisations (that I was careful not to break prompt caching with).

**[48440971](https://news.ycombinator.com/item?id=48440971)** - 2026-06-08 | by slopinthebag | in *DeepSeek V4 Pro beats GPT-5.5 Pro on precision* (397 pts)
  - Measured single-day spend: ~16M input tokens, ~15M of them cache hits, $0.47 total on V4 Pro via Zed's harness.
  - > I used ~16,000,000 input tokens yesterday on v4 pro, ~15,000,000 were cache hits, and I spent $0.47. Output tokens were negligible. However that's with Zed's harness, I'm not sure what you would get with Claude Code. It's maybe not quite as knowledgeable as the most expensive American models and maybe makes more mistakes (just a feeling based off of vibes, don't take my word for it), so you need t...

**[48267911](https://news.ycombinator.com/item?id=48267911)** - 2026-05-25 | by sfifs | in *DeepSeek makes the V4 Pro price discount permanent* (621 pts)
  - Estimates inference at 90-95% gross margin from the author's own migration benchmarking, and predicts displacement of premium API usage.
  - > Benchmarking the kind of cost savings I'm seeing moving from sonnet and gemini flash to local models, inference runs at least 90-95% gross margins. So they are probably still gross margin profitable. BTW form my benchmarking, open weigh models are good enough for many agentic tasks starting with Qwen 3.5/6 family and Deepseek v4 family, so it's likely we'll see displacement of api usage from the p...

**[48259141](https://news.ycombinator.com/item?id=48259141)** - 2026-05-24 | by Alifatisk | in *DeepSeek makes the V4 Pro price discount permanent* (621 pts)
  - Frames the gap DeepSeek left open: no coding-plan subscription tier, unlike Z.ai, Kimi, MiniMax and MiMo, so heavy users stay on per-token billing.
  - > I wish they had a coding plan like Z.ai, Kimi, Minimax and Xiaomi (MiMo). So instead of paying per million token, I pay a subscription. At the same time, 75% discount is astonishing. I'll just topup and see how far it goes. I remember when Z.ai had a deal where I paid 7$ for three months, good times.

**[48245378](https://news.ycombinator.com/item?id=48245378)** - 2026-05-23 | by freakynit | in *DeepSeek makes the V4 Pro price discount permanent* (621 pts)
  - 70%+ of input tokens served from cache on agentic runs averaging 20+ tool calls, with a concrete account of the model repairing a misconfigured MCP in under 30 seconds.
  - > Also, deepseek cache hit rates are pretty good. I use deepseek v4 flash model regularly for agentic tasks (more than 20 tool calls on average per run), and 70%+ of input tokens get served from cache. The speed is absolutely bonkers too. I once misconfigured a mcp I was developing locally, and told it to use the tools provided by this mcp to get certain task done. It figured out that the mcp is mis...

**[48243622](https://news.ycombinator.com/item?id=48243622)** - 2026-05-23 | by BiraIgnacio | in *DeepSeek makes the V4 Pro price discount permanent* (621 pts)
  - ~$1/week at roughly 3 h/day, with the full harness environment configuration that produced it.
  - > I've been using V4 flash consistently with Claude. Pretty great fast and darn cheap. I use it about 3h/day and so far haven't crossed $1 USD/week. FWIW, I this is what I have in my settings.json "env": { "ANTHROPIC_AUTH_TOKEN":"sk-nope_not_real", "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic", "ANTHROPIC_MODEL": "deepseek-v4-flash", "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-flash",...

**[48043928](https://news.ycombinator.com/item?id=48043928)** - 2026-05-07 | by samdhar | in *DeepSeek V4 Pro at 75% off until 31 May* (87 pts)
  - Break-even math for self-hosting at the discounted rate: you would need to push roughly 1B output tokens/day to beat an 8xH100 rental fleet, which almost no 'run your own LLM' use case reaches.
  - > Cached input at $0.003625/M, output at $0.435/M. Aggressive pricing. For anyone doing the "should I self-host on rented GPUs?" math: at this rate you'd need to push roughly 1B output tokens/day to break even against an 8xH100 fleet on Vast/Lambda (assuming 3-5k tokens/sec aggregate throughput). The vast majority of "I should run my own LLM" use cases don't come close to that volume. Every API pric...

**[48005694](https://news.ycombinator.com/item?id=48005694)** - 2026-05-04 | by l5870uoo9y | in *DeepClaude – Claude Code agent loop with DeepSeek V4 Pro* (678 pts)
  - Pins down that the $0.87/M output figure was a temporary discount scheduled to rise to $3.48 on 2026-05-31, with the pricing-doc source.
  - > > DeepSeek V4 Pro scores 96.4% on LiveCodeBench and costs $0.87/M output tokens. Yes and this is a temporary discount which increases to 3.48 USD on 2026/05/31 15:59 UTC. Source: https://api-docs.deepseek.com/quick_start/pricing

### Local inference, quantization and hardware (7)

**[49276824](https://news.ycombinator.com/item?id=49276824)** - 2026-08-12 | by spijdar | in *DeepSeek V4 Pro 0813* (1041 pts)
  - Runs a 3-bit quant of DSv4 locally at ~15 tok/s and rates it the most effective local coding model despite trailing GPT and Claude.
  - > I'm not the most LLM-savvy person around, and I'm not gonna say I've put a ton of effort into practically compared these open models. But, a month or two ago I did do some "practical evaluates" testing GLM 5.2 versus DSv4 (flash/pro) with OpenCode's subscription with some late 80s Unix clone-type work, and this jives with my experience. GLM ended up being far slower, and far more expensive, for ap...

**[48144336](https://news.ycombinator.com/item?id=48144336)** - 2026-05-15 | by kgeist | in *A few words on DS4* (440 pts)
  - Quantization-vs-density analysis: DS4 needs ~5x the VRAM of Qwen3.6-27B even at 2 bits, large MoE at 2-3 bits historically underperforms dense ~30B at 4-8 bits, against 50-60 tok/s and 260k context measured on a 5090.
  - > Did someone compare DeepSeek 4 Flash to Qwen3.6-27B on real tasks (quality + speed)? According to the benchmarks at artificialanalysis.ai, Qwen3.6-27B is better at agentic tasks, and DS4 is only 2 points better at coding (both with max reasoning effort, full weights). At the same time, DS4 requires 5 times more VRAM even at 2 bits. Last time I explored this topic, large MoE models at 2-3 bits usua...

**[48149067](https://news.ycombinator.com/item?id=48149067)** - 2026-05-15 | by ljosifov | in *A few words on DS4* (440 pts)
  - Practical VRAM ceiling on a 96GB M2 Max - `sysctl iogpu.wired_limit_mb=88000` before driver glitches - and how ~80GB of DS4-Flash quants just fits with room for KV cache.
  - > On 96gb I can give up to about 88GB to the GPU with sysctl iogpu.wired_limit_mb=88000, without suffering any ill-effects. When pushed higher I tend to notice e.g. graphic driver errors, youtube web page not working, other semi-random glitches. So the ~80 GB of DS4-flash quants I could just about fit. Leaving some extra for the KV caches. Will try, I'm curious how's the DS4 degradation with context...

**[48146381](https://news.ycombinator.com/item?id=48146381)** - 2026-05-15 | by ljosifov | in *A few words on DS4* (440 pts)
  - Local-agent viability datapoint: 40-30 tok/s at 60W draw on an M2 Max, versus the 60-80 tok/s typical of the API.
  - > Love this, even if can't use it atm (not got the h/w - only 96gb on M2 Max). I get it the general comp/public will find it unusable or worse. Reminds me of how home computers were - mere toys - before they became personal computers (PC). On my h/w the only passable combo for me atm is pi agent + llama.cpp + nemotron cascade-2 model: to 1M context, hybrid arch doesn't crash & burn 1/N^2 with contex...

**[48142578](https://news.ycombinator.com/item?id=48142578)** - 2026-05-14 | by kamranjon | in *A few words on DS4* (440 pts)
  - Long-context behaviour on a 128GB M4 Max: still running cleanly at 124k tokens with no degradation, faster than a dense 27-31B model thanks to MoE.
  - > Just want to mention that I've been pulling down and using DwarfStar locally and it's incredible. I actually have it running on my personal macbook m4 max with 128gb of ram and I am running the server to share it through tailscale with my work laptop and just have pi running there. The long context reasoning is something I haven't even seen in frontier models - I was running at 124k tokens earlier...

**[47898106](https://news.ycombinator.com/item?id=47898106)** - 2026-04-25 | by josefcub | in *How good is Mac Studio M3 Ultra for Trillion param models li* (15 pts)
  - Mac Studio M3 Ultra 256GB reality check: 3-5 minute prefill on very large models, Q1/Q2 quants measurably degrade output, with a concrete 96GB recommendation instead.
  - > I've got 256GB of RAM on a Mac Studio M3 Ultra. Other posters are right: The M3 Ultra's prefill is super slow with really large models, 3-5 minutes while it digests the new additions to its context before it continues. On my heavy RAM model, I _can_ run 400b-500b models at Q2, and up to about 750b models at Q1, but the wait isn't the worst part. Lower quants like that affect its output, making it...

**[47896423](https://news.ycombinator.com/item?id=47896423)** - 2026-04-24 | by simonw | in *DeepSeek v4* (2091 pts)
  - Correction with hard numbers on the streaming-experts pattern: 4-bit expert quantization is 209GB on disk at 4.36 tok/s, and the 2-bit version broke tool calling while 4-bit handles it.
  - > It doesn't have to be a 2-bit quant - see the update at the bottom of my post: > Update: Dan's latest version upgrades to 4-bit quantization of the experts (209GB on disk, 4.36 tokens/second) after finding that the 2-bit version broke tool calling while 4-bit handles that well. That was also just the first version of this pattern that I encountered, it's since seen a bunch of additional activity f...

### First-hand production evaluation and dissent (11)

**[49219903](https://news.ycombinator.com/item?id=49219903)** - 2026-08-08 | by KronisLV | in *DeepSeek V4 Flash 0731* (796 pts)
  - Quantified error-rate ladder from sustained use: V4 Pro at Max reasoning needed 30-60% extra time to fix output, GLM 5.2 20-30%, Kimi K3 under 10% - the most concrete quality comparison in the corpus.
  - > > The Chinese models are not good enough for anything other than pair programming, which is just a very last-gen way of using agents. This matches my experience with DeepSeek V4 Pro at Max reasoning, the preview version of the model kept regularly messing things up. About 30-60% of additional time to fix the output was needed. On similar tasks, GLM 5.2 at Max reasoning screwed up maybe 20-30% of t...

**[49220263](https://news.ycombinator.com/item?id=49220263)** - 2026-08-08 | by re-thc | in *DeepSeek V4 Flash 0731* (796 pts)
  - Direct rebuttal that the V4 Pro comparison is already stale: Flash 0731 beats it and costs less.
  - > > This matches my experience with DeepSeek V4 Pro at Max reasoning, That was ages ago (in LLM release timelines). DeepSeek V4 Flash beats it now and a lot cheaper. > On similar tasks, GLM 5.2 at Max reasoning screwed up maybe 20-30% of the time, GLM 5.3 bridges this gap. > I'd say as Chinese models get better, whatever moat Anthropic and OpenAI have dissipates. Their moat, especially OpenAI is fun...

**[49215736](https://news.ycombinator.com/item?id=49215736)** - 2026-08-07 | by NoboruWataya | in *DeepSeek V4 Flash 0731* (796 pts)
  - Switching account: moved to V4 Pro on OpenRouter after a Claude ban and still paid significantly less than the subsidised subscription, valuing harness and provider portability.
  - > My Claude account was banned the other day. The only possible cause I can think of is that I tried to authenticate from the AI assistant in a JetBrains IDE and, not thinking, entered the details for my regular subscription rather than an API account. As soon as it became apparent that I needed an API account rather than a subscription, I just closed out of the tab. Nevertheless, about 20 minutes l...

**[48440935](https://news.ycombinator.com/item?id=48440935)** - 2026-06-08 | by willsmith72 | in *DeepSeek V4 Pro beats GPT-5.5 Pro on precision* (397 pts)
  - Dissent: on a $200 Claude plan, any performance reduction is unacceptable because getting stuck mid-run costs more than the token savings.
  - > also curious. On the claude code $200 plan, get close to weekly limits but don't usually hit it. to me just about any small reduction in performance would not be acceptable, the cost of redirecting and getting stuck during long runs without me are too big (like when I tried gemini cli for a few days). if it's 99.9% comparable performance for less money I'm interested, but I'm skeptical it's there

**[48168369](https://news.ycombinator.com/item?id=48168369)** - 2026-05-17 | by rapind | in *DeepSeek V4: The Open-Source Model Frontier Labs Feared* (85 pts)
  - Split workflow - Codex 5.5 for planning, DeepSeek V4 Flash for implementation - with a stated distrust of opaque frontier-model throttling.
  - > Claude at times feels lobotomized compared to where it was a few months ago with 4.6. I think Anthropic was (is still?) struggling with their infrastructure and hasn't felt as good for me anecdotally for a few months. Significantly enough that I've cancelled (max 20x). Codex 5.5 extra high currently feels a good amount smarter than either 4.6 or 4.7 Opus. I only just started using it about a week...

**[48142868](https://news.ycombinator.com/item?id=48142868)** - 2026-05-15 | by sbinnee | in *A few words on DS4* (440 pts)
  - Replaced Gemini 3 Flash with V4 Flash across personal use; finds tool calling more reliable than other open models, attributed to interleaved thinking.
  - > It is a big thing for sure to have a competitive local agentic model. I've replaced gemini 3 flash preview with DeepSeek v4 flash for all of my personal use cases. Starting from chat app, language learning, and even hobby coding. For coding, I couldn't get decent results no matter which sota latest models I used before. It's not close to Opus or Codex models. It's a flash model and makes mistakes...

**[47992827](https://news.ycombinator.com/item?id=47992827)** - 2026-05-03 | by skeledrew | in *DeepSeek V4 – almost on the frontier* (677 pts)
  - Dissent on local viability: ~4.5 tok/s after optimisation on a modest system, with the machine thermally maxed - not practical for serious work.
  - > It'll be a while yet before open models that're good enough will be viable for local use. Heck I've been trying to use the Qwen 3.5 39B A3B on my system, which is modest but no slouch, and have only been able to get ~4.5 tok/s after optimization, and it really runs my system red (fans instantly go crazy). It's just not practical for serious work.

**[47990009](https://news.ycombinator.com/item?id=47990009)** - 2026-05-02 | by rurban | in *DeepSeek V4 – almost on the frontier* (677 pts)
  - Cost and capability from a real compiler port: $15-30 total, and these models beat the expensive ones on low-level ARM calling-convention assembly.
  - > Unfortunately not. I'm using plain kimi, opencode (with deepseek, gpt, minmax, whatever) and claude. claude is the best, but only for some hours. The trick is to get a good AGENTS.md file, good test cases and test runner to repro, like seemless docker and qemu calls. GNU autotools would be easiest, but here I'm using plain makefiles. Also for LSP clangd being up-to-date a compile_commands.json is...

**[47986694](https://news.ycombinator.com/item?id=47986694)** - 2026-05-02 | by baldai | in *DeepSeek V4 – almost on the frontier* (677 pts)
  - Dissent: for chunkier plan-review-implement workflows, SOTA adds ~5% at every stage and it compounds, so the cheaper model does not pay off.
  - > Hi, I am happy it works well for you. For me personally I struggle finding good use-cases in general for these OOS models. I am lightly technical but I do not manually code. So my flow is /grill-me (can take hours), make plan, review plan with 2. model, implement, review after implementation. Maybe it is because my tasks are usually chunkier, or because I cant code myself that I struggle using che...

**[47915339](https://news.ycombinator.com/item?id=47915339)** - 2026-04-26 | by Kuyawa | in *DeepSeek v4* (2091 pts)
  - Solo-developer workflow in detail: a start.txt spec drives 5-10 minute full-app generation hitting ~95% of requirements, with manual tweaks after.
  - > No, I have not tested other coding agents. DeepSeek works well enough for what I need. From what I've seen I can guess that Claude, now with the new Design feature, is ten times more effective as it also creates images, styles and media, thing that DeepSeek doesn't, yet, but for now I try to keep my designs simple and find a free hero pic somewhere to keep the costs low and the mental friction low...

**[47890995](https://news.ycombinator.com/item?id=47890995)** - 2026-04-24 | by Kuyawa | in *DeepSeek v4* (2091 pts)
  - Volume datapoint: three apps in a month and a self-built CLI agent, under $1 spent across 10M+ tokens.
  - > I am using DeepSeek extensively to develop apps, three in the last month, with my own CLI coding agent [1] developed by DeepSeek itself line by line. I haven't spent $1 yet in well over 10 million tokens. If I considered myself a 10X programmer, now I am 100X. Love DeepSeek. [1] https://github.com/kuyawa/mecha-ai

---

## 4. Method

1. **Find subject threads.** Story-only Algolia sweeps (`tags=story`, `restrictSearchableAttributes=title`) for `deepseek`, `deepseek v4` and `ds4`, time-bisected against the 1000-hit cap, then filtered to titles that are about V4 / V4 Pro / DS4. Result: 167 threads, 75 with comments.
2. **Pull every comment** via `search_by_date` with `tags=comment,story_<id>`, paginated. 4917 comments retrieved against 5542 claimed by the story records - the gap is deleted and dead comments, which the API does not return.
3. **Score** comments of 200+ characters on quantitative signals, named benchmarks, first-hand-testing language and length.
4. **Read and curate.** The score is only a triage aid and is weaker here than in the phrase sweep: the 2091-point launch thread drags in long geopolitics and AI-economics arguments that score well on numbers and say nothing about the model. The top ~70 unpublished candidates were read in full and 34 selected; the rest of the corpus stays in the CSV with its score so the exclusions are auditable.

**No database writes.** Algolia only; nothing read from or written to Turso.

### Companion files

- `deepseek-v4-pro_hn_subject_analysis_cases.csv` - the 34 curated cases with thread context, full text and notes.
- `deepseek-v4_hn_subject_thread_comments.csv` - all 2216 scored comments (200+ chars) with `curated` flag, for auditing exclusions.
- `deepseek-v4_hn_subject_threads.csv` - all 167 subject threads with points, comment counts and links.
- `deepseek-v4_subject_threads_20260901T110557Z.json` - raw comment trees for all 75 threads.