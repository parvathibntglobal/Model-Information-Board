# DeepSeek V4 Pro — X / Twitter keyword sweep

**Pulled:** 31 August 2026, 12:28 UTC  
**Source:** twitter241 (RapidAPI), driven through the brand-visibility agent's live provider  
**API calls:** 96 across 46 queries (2 sweeps)  
**Corpus:** 993 unique posts returned, 573 containing a keyword literally in the text  
**Data files:** `results.json` (full records incl. raw fields), `results.csv` (spreadsheet-ready)

> Nothing from this pull was written to the KiteAI Turso or Postgres corpus, and no keywords were added to the production lexicon. The agent's orchestrator was deliberately bypassed; only its scraper provider was reused.

---

## 1. The four keywords

All four normalise to the same string once punctuation is stripped, so they return one overlapping corpus rather than four independent ones. Only the `-0813` suffix is genuinely distinct — it names the 13 August general-availability build.

| Keyword (as supplied) | Posts matching after normalisation | Posts using that exact spelling | Note |
|---|---:|---:|---|
| `Deepseek V4 pro` | 573 | 401 | spaced form |
| `deepseek-v4-pro` | 573 | 140 | hyphenated form |
| `deepseekv4pro` | 573 | 65 | no separator |
| `deepseek-v4-pro-0813` | 73 | 71 | dated build |

The middle column is identical for the first three because they are the same string once punctuation is normalised — that is why they are not four independent searches. The right-hand column shows how people actually spell it, which does differ.

Per the brief, the second sweep changed the keyword to chase substance rather than announcements: 32 derived queries covering analysis (`vs`, `tech report`, `architecture MoE`, `1M context`, `limitations`, `quantization gguf`, `vllm sglang`, `tokens cost`), demonstrations (`I built`, `I tested`, `coding results`, `agent swarm`, `one shot`, `real world`) and workflows (`my workflow`, `setup config`, `tutorial guide`, `claude code`, `codex`, `opencode`, `cursor cline`, `mcp tools`, `self host`, `fine tune`, `prompt engineering`).

## 2. Headline numbers

| Metric | Value |
|---|---:|
| Posts with the keyword in the text | 573 |
| Posts naming the `-0813` build | 73 |
| Distinct authors | 381 |
| Total engagements (likes + RT + replies + quotes + saves) | 432,187 |
| Total views (where X exposed a count) | 56,305,788 |
| Date range | 2026-04-24 → 2026-09-01 |
| Languages | en (421), zh (106), ja (28), es (7), in (3), fr (2) |

## 3. Content mix — where the substance actually is

This is the answer to the brief. The top-ranked posts were read and labelled by content type. `Subject` counts the posts where DeepSeek V4 Pro is a real subject, as opposed to one comparison datapoint inside a post about another model.

| Content type | Posts | Subject | What it is |
|---|---:|---:|---|
| **BENCHMARK** | 35 | 19 | Reports evaluation numbers or test results, with figures |
| **DEEP_ANALYSIS** | 29 | 22 | Original technical argument — architecture, cost, serving, behaviour |
| **OPINION** | 18 | 6 | A take or reaction without supporting specifics |
| **USAGE_DEMO** | 18 | 18 | The author shows what they actually built or ran, with time / tokens / cost |
| **PROMO** | 12 | 0 | Referral, free-token, reseller or engagement-bait |
| **ANNOUNCEMENT** | 12 | 10 | Launch, release, price change or availability notice |
| **NEWS_ROUNDUP** | 9 | 0 | Aggregated digest or model-list; little original content |
| **COMPARISON** | 8 | 6 | Head-to-head against other models with reasoning, not a bare list |
| **WORKFLOW_SETUP** | 8 | 7 | How it is wired into a harness, tool or pipeline; configs and setup |

**98 of the 149 labelled posts are articles** (analysis, benchmark, comparison, demo, workflow, tutorial) — **72** of those have V4 Pro as the actual subject. Announcements, roundups and promo together account for 33 posts, and are listed separately in §9 rather than mixed into the article sections.

## 4. Release sequence

| Date | Event | Engagement | Views | Link |
|---|---|---:|---:|---|
| 2026-04-24 | V4 Preview open-sourced | 67,193 | 10,092,783 | [@deepseek_ai](https://x.com/deepseek_ai/status/2047516922263285776) |
| 2026-04-25 | API cut 75%, harnesses updated | 12,979 | 1,430,034 | [@deepseek_ai](https://x.com/deepseek_ai/status/2048062777357750316) |
| 2026-04-26 | Input-cache price cut to one tenth | 11,801 | 1,682,543 | [@deepseek_ai](https://x.com/deepseek_ai/status/2048440764368347611) |
| 2026-04-29 | Discount extended to 31 May | 8,827 | 2,740,102 | [@deepseek_ai](https://x.com/deepseek_ai/status/2049312932014813344) |
| 2026-05-22 | Discount made permanent | 35,824 | 7,075,370 | [@deepseek_ai](https://x.com/deepseek_ai/status/2057854261699195173) |
| 2026-07-31 | V4-Flash official API in public beta | 42,387 | 9,537,083 | [@deepseek_ai](https://x.com/deepseek_ai/status/2083084415157022911) |
| 2026-08-13 | V4-Pro general availability — the `0813` build | 20,205 | 2,980,802 | [@deepseek_ai](https://x.com/deepseek_ai/status/2087864585504305397) |

- **2026-04-24 — V4 Preview open-sourced.** V4-Pro at 1.6T total / 49B active, V4-Flash at 284B / 13B, both native 1M context. MIT weights and tech report published same day.
- **2026-04-25 — API cut 75%, harnesses updated.** Claude Code gains `deepseek-v4-pro[1m]` for full 1M context; OpenCode ≥ 1.14.24 and OpenClaw ≥ 2026.4.24 ship matching support. The tooling story starts here.
- **2026-04-26 — Input-cache price cut to one tenth.** Applied across the whole API series.
- **2026-05-22 — Discount made permanent.** The price becomes the product's identity — most third-party posts are about cost, not capability.
- **2026-07-31 — V4-Flash official API in public beta.** Agent benchmarks stated as surpassing V4-Pro-Preview; native Responses API, adapted for Codex.
- **2026-08-13 — V4-Pro general availability — the `0813` build.** Major agent upgrades, flexible reasoning effort (low / high / max), native OpenAI Responses API with one-click Codex setup. This is the build the fourth keyword names.

Independent evaluation of the GA build landed two days later: Artificial Analysis scored V4 Pro 0813 at **53** on its Intelligence Index — 8 points above the April build, but with a **+264% blended price increase**, and only 1 point above the much cheaper V4 Flash 0731. That tension runs through most of the substantive coverage below.

## 5. Deep analysis

Original technical argument — architecture, serving economics, harness behaviour. **29 posts** (22 with V4 Pro as the subject).

### V4 Pro is the subject (22)

**[@bookwormengr](https://x.com/bookwormengr)** · 2026-04-24 · 17,709 followers · author id `171962385`  
2,514 engagements · 1,568 likes · 231 RT · 27 replies · 666 saves · 212,351 views · `en`  
<https://x.com/bookwormengr/status/2047527303824236545>

> DeepSeek V4 hits it out of the park and addresses HBM shortage: DeepSeek proves why it is such a fundamental research lab. In addition to exceeding Opus 4.6 on Terminal Bench and virtually matching on other performance metrics, the most notable advancement is this statement: "In the 1M-token context setting, DeepSeek-V4-Pro requires only 27% of single-token inference FLOPs and 10% of KV cache compared with DeepSeek-V…

**[@benitoz](https://x.com/benitoz)** · 2026-04-29 · 22,815 followers · author id `30399584`  
562 engagements · 338 likes · 38 RT · 26 replies · 151 saves · 1,281,873 views · `en`  
<https://x.com/benitoz/status/2049593416439500859>

> Wow @SemiAnalysis just dropped day-zero numbers on @deepseek_ai V4 Pro Blackwell (B300): 8,075 tok/s/GPU AMD MI355X: 6.99 tok/s/GPU Hopper (H200): 186 tok/s/GPU at higher interactivity Same interactivity. ~1,000× the throughput per GPU vs MI355X. Blackwell also keeps serving all the way out to 80 tok/s/user, more than 2× the range where AMD flatlines That number isn’t a typo! But the throughput isn’t the story The st…

**[@vllm_project](https://x.com/vllm_project)** · 2026-08-25 · 48,043 followers · author id `1774187564276289536`  
521 engagements · 287 likes · 37 RT · 24 replies · 151 saves · 103,527 views · `en`  
<https://x.com/vllm_project/status/2092040745842774377>

> Congratulations to @SemiAnalysis_ on the release of AgentX 1.0 🎊, an open-source multi-turn agentic coding benchmark collected from ~$3M of real traces, running on 1000+ chips and ~2MW of continuously operated compute. We are excited to see @vllm_project’s competitive performance on frontier open models: 🔷130,093 tok/s/chip for DeepSeek V4 Pro 🔷 77,079 tok/s/chip for Minimax M3 🔷 12,479 tok/s/chip for Kimi K3. The fo…

**[@ZhihuFrontier](https://x.com/ZhihuFrontier)** · 2026-07-13 · 11,569 followers · author id `1931962509596246016`  
483 engagements · 290 likes · 32 RT · 10 replies · 148 saves · 23,404 views · `en`  
<https://x.com/ZhihuFrontier/status/2076653008616825251>

> 🧱 DeepSeek-V4 is not just 1M context. It is a full system rebuild. Zhihu contributor THU-PACMAN 实验室 shared a deep technical breakdown of DeepSeek-V4, based on an internal PACMAN report sharing by Guo Minkun. The core point is simple: 1M-token context is not just a larger number in a config file. It is an end-to-end systems problem across attention, KV cache, MoE communication, training stability, post-training, and a…

**[@ZhihuFrontier](https://x.com/ZhihuFrontier)** · 2026-08-16 · 11,569 followers · author id `1931962509596246016`  
385 engagements · 188 likes · 18 RT · 9 replies · 165 saves · 34,230 views · `en`  
<https://x.com/ZhihuFrontier/status/2088872677692076431>

> 🧪 Is DeepSeek V4 Pro Overfit to DeepSeek Harness? The Real Problem May Be Interface Sensitivity DeepSeek disclosed that its public Code Agent results for DeepSeek-V4-Pro-0813 were measured with DeepSeek Harness in Minimal mode. It also warned that results could differ under other frameworks. That disclosure quickly raised a question: did DeepSeek train the model so closely around its own Harness that its benchmark pe…

**[@gordic_aleksa](https://x.com/gordic_aleksa)** · 2026-04-26 · 31,301 followers · author id `907007346546810881`  
273 engagements · 148 likes · 19 RT · 2 replies · 103 saves · 9,418 views · `en`  
<https://x.com/gordic_aleksa/status/2048455129779908952>

> [DeepSeek V4 Pro summary] building LLMs is increasingly looking more and more like building a car or an airplane. Few interesting bits that stood out to me. ## High level takeaways: * Coding is still significantly behind the frontier. e.g. on their internal R&D coding benchmark Pro has a pass rate 67% vs 80% for Opus 4.6 Thinking (and frontier has since moved to Mythos/Spud - new pretrains) * Somewhat surprisingly (?…

**[@AI_Whisper_X](https://x.com/AI_Whisper_X)** · 2026-06-09 · 6,353 followers · author id `1841436670169923584`  
229 engagements · 88 likes · 12 RT · 33 replies · 96 saves · 19,241 views · `zh`  
<https://x.com/AI_Whisper_X/status/2064334530497130844>

> 刚看完 SemiAnalysis 这篇 DeepSeek V4 推理性能长文，很有意思。 DeepSeek V4 一出来，被考试的是 NVIDIA、AMD、Huawei、vLLM、SGLang、TensorRT-LLM、ROCm、CANN 这一整套推理生态。 省流一下 SemiAnalysis 这篇的几个核心点： 1/ CUDA + vLLM / SGLang 仍然是 Day 0 最稳的生态。DeepSeek V4 Pro 发布当天，CUDA 平台上的 vLLM 和 SGLang 基本能直接跑，B200/B300 这类新 SKU 的 recipe 也大多开箱可用。 vLLM 和 SGLang 这两个开源推理引擎，已经是全球 ML 基础设施的核心组件了，各自独立出来成了公司（Inferact 和 RadixArk），融了几亿美金。他们的生态优势在这时候体现得最明显：新模型一出，开源生态能在第一时间接住。 2/ AMD 一开始很狼狈…

**[@MrAhmadAwais](https://x.com/MrAhmadAwais)** · 2026-05-05 · 53,900 followers · author id `216727067`  
170 engagements · 88 likes · 14 RT · 11 replies · 54 saves · 6,906 views · `en`  
<https://x.com/MrAhmadAwais/status/2051663860466372798>

> stop using Claude Code if you're using open source models. read this. as you know we're building a coding agent harness for both open and closed models. processing billions of tokens an hours is teaching us lots of amazing things. Command Code is purpose-built for each model we launch, and it's getting better every day. the closest analogy i can think of is teaching a human to drive a car when they make a mistake, fi…

**[@ZhihuFrontier](https://x.com/ZhihuFrontier)** · 2026-06-22 · 11,569 followers · author id `1931962509596246016`  
157 engagements · 81 likes · 4 RT · 4 replies · 68 saves · 8,993 views · `en`  
<https://x.com/ZhihuFrontier/status/2068967632083247485>

> Distilling DeepSeek V4 Pro’s Thinking Style Into Qwen3.6-35B-A3B 🌟Insights from Zhihu contributor & individual developer Lynn TL;DR: After reading ReAct, Lynn distilled the thinking style of DeepSeek V4 Pro into Qwen3.6-35B-A3B with LoRA. The result: GPQA-Diamond +7.6pp, unclosed empty answers down from 12 → 1, and average agent orchestration time down from 60s → 26s. The goal was not “more CoT,” but faster task deco…

**[@stalkermustang](https://x.com/stalkermustang)** · 2026-07-18 · 3,539 followers · author id `603750843`  
145 engagements · 94 likes · 4 RT · 12 replies · 32 saves · 24,654 views · `en`  
<https://x.com/stalkermustang/status/2078571128855949670>

> 8 months ago, Kimi K2 Thinking dropped, and we heard the exact same narrative: "Chinese open-source model is #1." Three months post-release, I ran the numbers on 16 new benchmarks that came out after the model's launch and compared it to GPT-5 / Sonnet 4.5. The model underperformed on 13 (!!!) of them, trailing by over 10pp on 7. Are we going to see a repeat with Kimi K3? I'll share my thoughts and predictions below,…

**[@realsigridjin](https://x.com/realsigridjin)** · 2026-04-24 · 14,735 followers · author id `1149596425610657795`  
142 engagements · 98 likes · 9 RT · 7 replies · 27 saves · 5,553 views · `en`  
<https://x.com/realsigridjin/status/2047517783123263864>

> tldr; sorry gpt 5.5, deepseek v4 is new shocking moment it beats gpt 5.4 xhigh now we can run gpt 5.4-ish model in local home amazing. you cant sleep they even compare benchmark against xhigh. deepseek is TRUE man the family comes with two models, DeepSeek-V4-Pro with 1.6T parameters (49B activated) and DeepSeek-V4-Flash with 284B parameters (13B activated) both supporting a context length of one million tokens so he…

**[@aakashgupta](https://x.com/aakashgupta)** · 2026-04-24 · 329,235 followers · author id `101805159`  
86 engagements · 42 likes · 10 RT · 7 replies · 26 saves · 7,883 views · `en`  
<https://x.com/aakashgupta/status/2047547088645640686>

> The pricing floor for Opus-tier and GPT-tier reasoning just dropped, if you're willing to self-host. DeepSeek V4 Pro activates 49B parameters out of 1.6T per token. It posts Codeforces 3206 (legendary grandmaster tier), beats Opus 4.6 on Apex Shortlist (90.2) and SimpleQA (57.9 vs 46.2), and ties on SWE Verified. Open weights. 1M context. Sparsity ratio of 32 to 1. Closed frontier is running dense or near-dense with …

**[@realsigridjin](https://x.com/realsigridjin)** · 2026-04-24 · 14,735 followers · author id `1149596425610657795`  
82 engagements · 70 likes · 2 RT · 0 replies · 10 saves · 5,360 views · `en`  
<https://x.com/realsigridjin/status/2047542935647142103>

> deepseek v4 absolutely crushes it while tackling the hardware memory bottleneck head on. they are showing exactly why their lab is a cornerstone of ai research right now. beyond beating opus 4.6 on terminal bench and tying it elsewhere the real game changer is this specific claim. deepseek v4 pro needs just twenty seven percent of the compute per token and a mere ten percent of the kv cache footprint at a one million…

**[@ZhihuFrontier](https://x.com/ZhihuFrontier)** · 2026-04-28 · 11,569 followers · author id `1931962509596246016`  
68 engagements · 53 likes · 3 RT · 2 replies · 9 saves · 5,486 views · `en`  
<https://x.com/ZhihuFrontier/status/2049027925920637077>

> 🚨 DeepSeek V4 Pro just dropped 75% OFF API pricing + permanent cache price cut to 1/10! 🔥 4/26 Update: Cache permanently 90% cheaper Offer ends May 5, 2026 Insights from Zhihu contributor 普杰 💡 Key Insights: • DeepSeek doesn’t do loss-leader promotions → ¥3 in / ¥6 out ≥ real cost • Original high price (¥12 in / ¥24 out) = traffic control, not cost • Pro params ×3.7 vs Flash, but old price ×12 → now infra can scale • …

**[@Sumanth_077](https://x.com/Sumanth_077)** · 2026-04-24 · 76,757 followers · author id `1420290522728394757`  
65 engagements · 36 likes · 10 RT · 5 replies · 13 saves · 3,264 views · `en`  
<https://x.com/Sumanth_077/status/2047622488209989924>

> DeepSeek just dropped V4! Two open-source MoE models with 1M context windows under MIT license. DeepSeek-V4-Pro: 1.6T total parameters (49B active per token), pre-trained on 33T tokens. This makes it the largest open-source model available - bigger than Kimi K2.6 (1.1T) and more than twice the size of DeepSeek V3.2 (685B). DeepSeek-V4-Flash: 284B total (13B active), trained on 32T tokens. The efficiency model for fas…

**[@ZhihuFrontier](https://x.com/ZhihuFrontier)** · 2026-08-23 · 11,569 followers · author id `1931962509596246016`  
56 engagements · 30 likes · 2 RT · 8 replies · 15 saves · 2,414 views · `en`  
<https://x.com/ZhihuFrontier/status/2091421929546932351>

> 🧩 Your Agent Model May Be Overfitting the Harness, Not Learning the Task DeepSeek V4 Pro has exposed a growing Agent problem: the same weights can approach their ceiling under DSH’s minimal preset, then degrade under standard or third-party frameworks. Zhihu contributor 曾天真 compares reports from Kimi K3, Qwen, Kwai, and DeepSeek, then connects them to his team’s production experience. The core lesson: a model can und…

**[@AnandButani](https://x.com/AnandButani)** · 2026-04-28 · 1,827 followers · author id `1648787052`  
31 engagements · 14 likes · 1 RT · 3 replies · 12 saves · 871 views · `en`  
<https://x.com/AnandButani/status/2049146816801693704>

> 🚨 An open-weights model just became cheaper than every closed competitor on the market — and it's only months behind frontier. Here's what just happened 👇 @simonw reviewed @deepseek_ai's V4 release this week — two preview models, both shipped with @MIT licenses and 1 million token context windows. Anyone can download them. Anyone can run them. DeepSeek-V4-Pro: 1.6 trillion parameters. The largest open-weights model e…

**[@byteHumi](https://x.com/byteHumi)** · 2026-04-24 · 5,219 followers · author id `1808455867395661824`  
30 engagements · 22 likes · 0 RT · 3 replies · 4 saves · 3,872 views · `en`  
<https://x.com/byteHumi/status/2047547076159152372>

> deepseek THE WHALES HAS RISEN deepseek V4-Pro is a 1.6 trillion parameter model still beats Opus 4.6 on LiveCodeBench (93.5 vs 88.8) their post-training is insane. they train separate specialist models and didn't fine-tune one model on mixed data like every other lab > a math expert, > a code expert, > a reasoning expert then they kill the specialists and distill their abilities back into one model. GROW experts HARV…

**[@Rus_Khairullin](https://x.com/Rus_Khairullin)** · 2026-04-24 · 126,427 followers · author id `967316062080348160`  
10 engagements · 9 likes · 1 RT · 0 replies · 0 saves · 524 views · `en`  
<https://x.com/Rus_Khairullin/status/2047651659996627051>

> One of the strongest open-source releases of 2026 just dropped: DeepSeek-V4 🔥 DeepSeek-V4 is the fresh release from the Chinese DeepSeek team (came out today, April 24, 2026). The model genuinely “dropped a bomb.” Open-source, 1M context window by default, MoE architecture, and performance that in coding, math, and agentic tasks is already breathing down the neck of (and in some places overtaking) top closed models l…

**[@botnewsnetwork](https://x.com/botnewsnetwork)** · 2026-08-18 · 37 followers · author id `2017982323724369920`  
9 engagements · 8 likes · 0 RT · 1 replies · 0 saves · 422 views · `en`  
<https://x.com/botnewsnetwork/status/2089730032700912014>

> The Harness Reversal Released, not built. By Ummon, Editor-in-Chief On Monday, a team most people had never heard of wrapped DeepSeek V4-Pro in a scaffolding system called J-Space — a structured scratchpad, forced step-by-step verification, automatic rollback on error — and watched it beat Fable 5 on software engineering benchmarks. They did not train anything. They did not fine-tune anything. They did not change a s…

**[@aisolram](https://x.com/aisolram)** · 2026-08-13 · 281 followers · author id `1945322941698465794`  
4 engagements · 1 likes · 0 RT · 2 replies · 0 saves · 347 views · `en`  
<https://x.com/aisolram/status/2087880090222723267>

> DeepSeek-V4-Pro just launched, and this is more than another model release. The interesting part isn’t simply “a bigger benchmark number.” It’s the shift toward models that can actually operate as software engineering and agentic systems. DeepSeek-V4-Pro: What changed? DeepSeek is positioning V4-Pro around production-grade agent workflows, with improvements across coding, tool use, reasoning, and long-horizon tasks. …

**[@adidshaft](https://x.com/adidshaft)** · 2026-07-24 · 2,573 followers · author id `1029803073651261441`  
4 engagements · 2 likes · 1 RT · 1 replies · 0 saves · 283 views · `en`  
<https://x.com/adidshaft/status/2080750406846849171>

> open-weight model speed is getting harder to read from the name. DeepSeek V4 Pro stores 1.6T parameters. gpt-oss-120b stores 117B. Gemma 4 31B stores only 31B. Yet single-user decode depends much more on the weights touched per token than the weights parked in memory. I mapped 16 models from @deepseek_ai, @Zai_org, @Alibaba_Qwen, @NVIDIAAI, @MistralAI, @OpenAI, @GoogleDeepMind and @ZyphraAI into four deployment bands…


### V4 Pro appears as a comparison point (7)

**[@quxiaoyin](https://x.com/quxiaoyin)** · 2026-08-05 · 35,955 followers · author id `382490716`  
2,210 engagements · 1,239 likes · 93 RT · 211 replies · 628 saves · 149,842 views · `en`  
<https://x.com/quxiaoyin/status/2085035602001695117>

> Claude Code subscription is 81x cheaper than its API. Codex subscription is 44x cheaper than its API. I max out 4 Max accounts last month and burned 56.5B tokens from plans, so I tested the ceiling — what a subscription gives you when you take everything it will give. Claude Code — $400 paid, $32,310 of API Codex — $400 paid, $17,609 of API $800 in, $49,919 out. $49,119 subscription subsidy. They are insanely generou…

**[@marfinxx](https://x.com/marfinxx)** · 2026-08-05 · 3,085 followers · author id `1172526145272762368`  
58 engagements · 26 likes · 4 RT · 10 replies · 18 saves · 1,440 views · `en`  
<https://x.com/marfinxx/status/2085056018543743263>

> Your AI pipeline is burning 90% of its token budget on dead end reasoning Single-pass generation on complex tasks fails due to cascading error accumulation: when each step has p = 0.90 accuracy across 20 steps, total success probability collapses to 12.1% Naively retrying the same prompt or dumping error logs into context creates attention noise and KV-cache bloat: the model repeats past hallucinations instead of rec…

**[@MastrXYZ](https://x.com/MastrXYZ)** · 2026-08-15 · 30,987 followers · author id `456112158`  
54 engagements · 32 likes · 8 RT · 6 replies · 7 saves · 2,234 views · `en`  
<https://x.com/MastrXYZ/status/2088622934323503582>

> Eight Agents, Four Days, 85 Accounts And Why Crypto Should Be Alarmed. What Taiwan's July cyberattack says about the economics of AI-assisted hacking In July 2026, Taiwan detected an unusual cyberattack against government agencies. Its Ministry of Digital Affairs said the operation came from overseas and combined manual hacking with AI agents such as OpenClaw. The affected agencies handled the incident, and the minis…

**[@Marktechpost](https://x.com/Marktechpost)** · 2026-07-22 · 11,644 followers · author id `717930546391687170`  
43 engagements · 29 likes · 7 RT · 2 replies · 4 saves · 47,301 views · `en`  
<https://x.com/Marktechpost/status/2079791860713980232>

> Poolside released Laguna S 2.1 , and the interesting part is not the benchmark table. It is what fits in memory. It is a 118B-parameter Mixture-of-Experts coding model that activates ~8B parameters per token. Roughly 6.8% of the network fires on any given step. 1. The weight-class claim → 78.5% SWE-Bench Multilingual — tops Poolside's published table outright → 70.2% Terminal-Bench 2.1 — first among open, disclosed-s…

**[@ZhihuFrontier](https://x.com/ZhihuFrontier)** · 2026-08-28 · 11,569 followers · author id `1931962509596246016`  
31 engagements · 18 likes · 2 RT · 5 replies · 6 saves · 1,605 views · `en`  
<https://x.com/ZhihuFrontier/status/2093174727745618280>

> 💥 GLM-5.3-Flash: Reported Opus 4.8-Level Scores at One-Tenth the Price Zhipu has confirmed that Ox Alpha — the anonymous model that dominated OpenRouter and OpenCode last week — is GLM-5.3-Flash, a 320B-parameter MoE with 18B active, released with open weights and an API at roughly one-tenth of GLM-5.3's price. Zhihu contributor 小小将 opens with a confession: he had hoped Ox Alpha was an external team fine-tuning the o…

**[@TheValueist](https://x.com/TheValueist)** · 2026-08-23 · 37,269 followers · author id `1838186195508969472`  
19 engagements · 14 likes · 0 RT · 5 replies · 0 saves · 6,833 views · `en`  
<https://x.com/TheValueist/status/2091344685050552550>

> $NVDA $MU $SNDK $LITE POOLSIDE EXECUTIVE ASSESSMENT (1/x) The reported Poolside transaction is strategically coherent, financially absorbable and unlikely to be material to Nvidia’s near-term earnings trajectory, but it represents a consequential expansion of Nvidia’s competitive perimeter. The transaction should not be evaluated as a conventional acquisition of a model developer or as a direct attempt to create a la…

**[@tonari_taikoku](https://x.com/tonari_taikoku)** · 2026-08-31 · 31 followers · author id `258341556`  
3 engagements · 2 likes · 0 RT · 1 replies · 0 saves · 246 views · `ja`  
<https://x.com/tonari_taikoku/status/2094242386922893454>

> 先週OpenRouterで1位の謎モデル、正体は智譜だった Ox Alpha。作者欄は stealth。OpenRouterの今週（集計8/29まで）トークン量で1位、20.7兆。DeepSeek V4 Flash 0731が2位。 無料で叩けた時期がある。その窓は閉じた。智譜（https://t.co/9oOqY512bC）が8月26日の公式ブログで自分で書いた。GLM-5.3-Flashを出す前に、OpenCodeとOpenRouterで匿名テストした。名前がox-alpha。全部、中国チップの上で回していた、とも書いてある。 OpenRouterのモデル頁も同じことを書いている。revealed to be ZAI GLM-5.3-Flash。 特徴 謎モデルに見えて、中身は智譜の新しいFlash。320Bのうち実際に動くのは18B。原生マルチモーダル。コンテキスト1M。重みはMITでHugging Faceに出ている。 …


## 6. Benchmarks & evaluations

Posts reporting actual evaluation figures, first-party or independent. **35 posts** (19 with V4 Pro as the subject).

### V4 Pro is the subject (19)

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-07-31 · 132,853 followers · author id `1743487864934162432`  
3,715 engagements · 2,753 likes · 271 RT · 131 replies · 437 saves · 571,398 views · `en`  
<https://x.com/ArtificialAnlys/status/2083123180869496865>

> DeepSeek V4 Flash 0731 scores 50 on the Artificial Analysis Intelligence Index, a 10-point jump over DeepSeek V4 Flash (released April 2026) that puts it 6 points ahead of DeepSeek V4 Pro. It shares identical architecture and pricing with the earlier DeepSeek V4 Flash, and lands on our Pareto frontier for Intelligence vs Cost per Task @deepseek_ai’s DeepSeek V4 Flash 0731 is one Intelligence Index point behind GPT-5.…

**[@pilvar222](https://x.com/pilvar222)** · 2026-08-13 · 3,348 followers · author id `1938600206`  
3,218 engagements · 2,183 likes · 208 RT · 68 replies · 699 saves · 289,040 views · `en`  
<https://x.com/pilvar222/status/2087691659953815783>

> We ran DeepSeek v4 Pro 0813 on our cybersecurity benchmark, it outperformed EVERY (!) other model at finding vulnerabilities - At pass@3, it rediscovered 87.5% of the benchmark CVEs. Far above Opus 5 and Qwen 3.8 at 81.3% - The tradeoff is precision. Only 65.6% of vulnerabilities reported by DeepSeek were valid. Far below GPT-5.6-Sol's 86.4% - The model can also be unpredictable. It only finds an average of 58.3% of …

**[@arena](https://x.com/arena)** · 2026-04-24 · 219,719 followers · author id `1641378826537295874`  
2,290 engagements · 1,765 likes · 144 RT · 55 replies · 297 saves · 290,766 views · `en`  
<https://x.com/arena/status/2047518354903359697>

> Exciting news - DeepSeek V4 Pro is in the Arena with 1.6T parameters (49B activated) alongside V4 Flash at 284B parameters (13B activated). Both support 1M token context. It’s a major leap over DeepSeek V3.2! Code Arena: - DeepSeek V4 Pro (thinking): #3 open model (#14 overall), on par with GPT-5.4-high and Gemini-3.1-Pro in agentic webdev tasks Text Arena: - DeepSeek V4 Pro (thinking): #2 open model (#14 overall), m…

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-08-04 · 132,970 followers · author id `1743487864934162432`  
1,521 engagements · 1,078 likes · 85 RT · 82 replies · 234 saves · 155,192 views · `en`  
<https://x.com/ArtificialAnlys/status/2084702191466725669>

> Announcing the Artificial Analysis Endpoint Accuracy Index, measuring how much of an open weights model's accuracy each serverless API endpoint preserves. We are initiating coverage with GLM-5.2, gpt-oss-120b and DeepSeek V4 Pro, with Kimi K3 coming soon Providers trade off accuracy to optimize for speed and cost. They quantize weights, write custom kernels and tune their inference stacks, and sometimes they simply s…

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-08-15 · 132,970 followers · author id `1743487864934162432`  
1,367 engagements · 1,055 likes · 69 RT · 94 replies · 124 saves · 113,879 views · `en`  
<https://x.com/ArtificialAnlys/status/2088440350734201149>

> DeepSeek V4 Pro 0813 scores 53 on the Artificial Analysis Intelligence Index, 8 points above April's DeepSeek V4 Pro - but with a 3.6x price increase and only 1 point above DeepSeek V4 Flash 0731 @deepseek_ai has released DeepSeek V4 Pro 0813, its new flagship model, along with updated pricing. With the new pricing, it still sits on our Pareto frontier for Intelligence vs. Cost, but by a smaller margin than previous …

**[@arena](https://x.com/arena)** · 2026-08-04 · 219,575 followers · author id `1641378826537295874`  
1,186 engagements · 911 likes · 69 RT · 72 replies · 119 saves · 257,312 views · `en`  
<https://x.com/arena/status/2084657730758046101>

> DeepSeek-V4-Flash-20260731 (High) by @deepseek_ai landed in Agent Arena at #21 overall (+1.98% net-improvement), and among open source #3 based on +12.5K real-world agentic sessions. This release is ranked 6 higher than DeepSeek-V4-Pro (-0.47%) and 13 higher than the previous DeepSeek-V4-Flash model (-2.81%). Across key signals, DeepSeek-V4-Flash-20260731 (High) is strong in Confirmed Success (+6.99%), but weaker in …

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-04-24 · 132,970 followers · author id `1743487864934162432`  
1,160 engagements · 895 likes · 95 RT · 32 replies · 124 saves · 55,536 views · `en`  
<https://x.com/ArtificialAnlys/status/2047547434809880611>

> DeepSeek V4 Pro is the #1 open weights model on GDPval-AA, our agentic real-world work tasks evaluation @deepseek_ai has released V4 Pro (1.6T total / 49B active) and V4 Flash (284B total / 13B active). V4 is DeepSeek's first new size since V3, with all intermediate models (V3.1, V3.2, R1, R1 0528) sharing the V3 family's 685B total / 37B active parameter MoE design. V4 Pro is also the largest open weights model rele…

**[@arena](https://x.com/arena)** · 2026-08-20 · 219,575 followers · author id `1641378826537295874`  
649 engagements · 540 likes · 27 RT · 29 replies · 44 saves · 81,548 views · `en`  
<https://x.com/arena/status/2090240605561778637>

> Exciting update: DeepSeek-V4-Pro (High) by @deepseek_ai is now #2 among open models in Agent Arena (#14 overall), with +6.3% net improvement! At $0.21 median cost/task, it reshapes the Agent Arena Pareto frontier! Compared to DeepSeek-V4-Flash (High), it has higher performance with a lower median cost per task. Among open models, it lands two spots above DeepSeek-V4-Flash (High), and by category, it’s #2 in Code and …

**[@_avichawla](https://x.com/_avichawla)** · 2026-06-29 · 76,103 followers · author id `1175166450832687104`  
470 engagements · 258 likes · 20 RT · 18 replies · 174 saves · 44,244 views · `en`  
<https://x.com/_avichawla/status/2071639616617361798>

> Big win for open-source LLMs! DeepSeek V4 Pro holds the top open-weights score on SWE-bench Verified, in the GPT-5.5 range. GLM 5.2 leads the open-weight intelligence index and sits near the closed frontier on long-horizon coding. But this leaderboard number is a weak proxy for real performance. It comes from one task set, run through one harness, served at one precision. The same weights can even score differently a…

**[@ivanfioravanti](https://x.com/ivanfioravanti)** · 2026-06-08 · 41,805 followers · author id `43874767`  
430 engagements · 310 likes · 9 RT · 46 replies · 62 saves · 33,377 views · `en`  
<https://x.com/ivanfioravanti/status/2063877822062449109>

> DeepSWE and DeepSeek V4 Pro: surely the benchmark is designed to facilitate GPT 5.5, and mini-swe is not ideal for many models tested, but personally I executed it, against DeepSeek official API, using V4 Pro and reasoning Max. It used around 1B tokens and I've got only 5.3% at the end 😢 Estimated cost: - cache-hit input: $3.54 - cache-miss input: $3.74 - output: $4.89 - total: $12.18 Without cache-aware pricing, the…

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-06-12 · 132,970 followers · author id `1743487864934162432`  
402 engagements · 278 likes · 25 RT · 18 replies · 70 saves · 2,128,980 views · `en`  
<https://x.com/ArtificialAnlys/status/2065559824230957190>

> Today we're releasing the first results for AA-AgentPerf, our new agentic inference benchmark: initially covering DeepSeek V4 Pro across NVIDIA Blackwell, Hopper, and AMD. AA-AgentPerf is the first benchmark built for agentic inference. We use real, long-context agentic coding trajectory data as the workload, and inference with real production optimizations such as KV cache reuse and speculative decoding, leading to …

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-05-01 · 132,970 followers · author id `1743487864934162432`  
401 engagements · 284 likes · 31 RT · 18 replies · 61 saves · 29,370 views · `en`  
<https://x.com/ArtificialAnlys/status/2050096370200281539>

> All three leading open weights models were released last week. Progress continues for open weights models alongside proprietary ones, with the gap to GPT-5.5, the leading proprietary model, sitting at 6 points on the Artificial Analysis Intelligence Index @Kimi_Moonshot’s Kimi K2.6 (Reasoning) and @Xiaomi's MiMo V2.5 Pro (Reasoning) tie as the leading open weights models on the Artificial Analysis Intelligence Index …

**[@kilocode](https://x.com/kilocode)** · 2026-05-13 · 29,154 followers · author id `1899809291353169921`  
390 engagements · 283 likes · 12 RT · 13 replies · 78 saves · 21,520 views · `en`  
<https://x.com/kilocode/status/2054598416705998925>

> We tested DeepSeek V4 Pro and Flash on the same FlowGraph spec we used for Opus 4.7 vs. Kimi K2.6. Pro scored 77/100 for $2.25. Flash scored 60/100 for $0.02. $0.02 is a price tier that didn't exist before. You can run the same task 3-4 times and still come in under one Kimi K2.6 run. Full breakdown: https://t.co/hRJPuzh4Yf

**[@elliotarledge](https://x.com/elliotarledge)** · 2026-08-20 · 43,374 followers · author id `1595935520999510016`  
219 engagements · 167 likes · 4 RT · 4 replies · 38 saves · 26,757 views · `en`  
<https://x.com/elliotarledge/status/2090458795172360257>

> DeepSeek V4 Pro on KernelBench-Hard. TopK is 9.35% of roofline. Opus 5 is 9.46%. The June checkpoint was 1.40%. It was tested on: TopK Bitonic for RTX PRO 6000. 9.35% of roofline. > Opus 5 at 9.46% > Kimi K3 (1M) at 8.95% > Fable 5 at 4.92% > Qwen 3.8 Max at 3.97% > June Pro at 1.40% TopK is a fused CUDA launch for k=8: warp tournament plus bitonic, then a CUDA graph keyed on `https://t.co/74tpGiZw0q_ptr()`. That is …

**[@TeksEdge](https://x.com/TeksEdge)** · 2026-06-13 · 10,512 followers · author id `1682428283135336449`  
182 engagements · 96 likes · 6 RT · 1 replies · 78 saves · 14,050 views · `en`  
<https://x.com/TeksEdge/status/2065891007514943964>

> So people are asking where it says Gemini-3-Flash+Kimi-K2.6+Deepseek-V4-Pro got within 1% of Fable 5 @ 50% the cost using the new Fusion tool, here it is from @OpenRouter's official blog post. 🧪 What is the DRACO Benchmark? 👇 DRACO (Deep Research Agentic Comparison) is a benchmark designed to test AI models on complex, real-world research tasks. Key details: 📍 Created by Perplexity AI Contains 100 deep research tasks…

**[@FundaAI](https://x.com/FundaAI)** · 2026-04-24 · 29,401 followers · author id `978741625`  
90 engagements · 52 likes · 10 RT · 6 replies · 19 saves · 46,167 views · `en`  
<https://x.com/FundaAI/status/2047656651906494656>

> Deep|DeepSeek V4 vs Claude vs GPT-5.4: A 38-Task Benchmark Across Coding, Reasoning, and Financial Research Important note: This report is not a research report. It is an evaluation report completed by the FundaAI Engineering Team, not written by the FundaAI Analyst Team. It does not represent the views of the FundaAI Analyst Team. All test cases are based on the actual working environment of the FundaAI Platform. As…

**[@rohanpaul_ai](https://x.com/rohanpaul_ai)** · 2026-08-18 · 155,613 followers · author id `2588345408`  
67 engagements · 42 likes · 3 RT · 9 replies · 12 saves · 9,610 views · `en`  
<https://x.com/rohanpaul_ai/status/2089837124988350722>

> This 3D coding test by @thehypedotnews found DeepSeek-V4-Pro-0813 used 48X more tokens than Muse Spark 1.2. thats why for agentic coding, the model's ability to reach an answer matters almost as much as the answer itself. A model that keeps reopening files, reconsidering decisions, and resending context can turn a small build into a huge inference loop. The test used Nous Research's Hermes Agent CLI through OpenRoute…

**[@AlicanKiraz0](https://x.com/AlicanKiraz0)** · 2026-08-28 · 37,849 followers · author id `1793492480203116544`  
50 engagements · 36 likes · 0 RT · 2 replies · 12 saves · 4,331 views · `tr`  
<https://x.com/AlicanKiraz0/status/2093429553561526699>

> Advanced 7 Frontier Model Coding Benchmark Task: Teknik omurgayı NASA’nın HCW/LVLH rendezvous yaklaşımı ve 6-DOF otomatik rendezvous çalışmaları oluşturuyor. Truth propagation tam iki-cisim ECI fiziği kullanıyor, HCW ise yalnızca guidance katmanında kullanıyor. Böylece lineer modeli doğrudan gerçek fizik gibi kullanan çözümler eleniyor. NASA HCW rendezvous çalışması, NASA RPOD çalışmalarına referans ile geliştirdim. …

**[@chengyongru](https://x.com/chengyongru)** · 2026-05-23 · 478 followers · author id `2028298069079642112`  
16 engagements · 11 likes · 2 RT · 1 replies · 2 saves · 1,545 views · `en`  
<https://x.com/chengyongru/status/2058305417881747519>

> EnvTrustBench paper's best EMR: 55.3% (Claude Code + Sonnet 4.6). nanobot + GLM-5.1 in a cross-eval: 35.3%. EMR (Environmental Misgrounding Rate), lower is better: nanobot + GLM-5.1: 35.3% nanobot + DeepSeek-V4-Pro: 60.7% Claude Code + GLM-5.1: 72.0% Claude Code + Claude Sonnet 4.6: 55.3% * OpenCode + GLM-5.1: 86.2% OpenClaw + GLM-5.1: ~84% * Paper's best among 14 scaffold-model combinations. Same model (GLM-5.1), di…


### V4 Pro appears as a comparison point (16)

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-07-16 · 132,853 followers · author id `1743487864934162432`  
8,357 engagements · 6,161 likes · 712 RT · 180 replies · 1,027 saves · 1,730,803 views · `en`  
<https://x.com/ArtificialAnlys/status/2077832874183860404>

> Kimi K3 scores 57 on the Artificial Analysis Intelligence Index. Its intelligence is comparable to Opus 4.8 and GPT-5.5 but remains behind Fable 5 and GPT-5.6 Sol. Moonshot AI has expressed plans to release the 2.8T parameter model's weights, which would make it the leading open weights model Key results: ➤ Strong agentic task performance: @Kimi_Moonshot's Kimi K3 reaches an Elo rating of 1668 on GDPval v2. This is a…

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-06-17 · 132,970 followers · author id `1743487864934162432`  
2,673 engagements · 1,941 likes · 241 RT · 77 replies · 305 saves · 343,391 views · `en`  
<https://x.com/ArtificialAnlys/status/2067135640249209175>

> Z ai’s GLM-5.2 is the new leading open weights model on the Artificial Analysis Intelligence Index scoring 51 and it sits on the Pareto frontier of Intelligence vs Cost per Task @Zai_org’s GLM-5.2 is the same size as GLM-5.1 (744B total / 40B active parameters) but scores 11 points higher on the Intelligence Index v4.1, placing ahead of MiniMax-M3 (44) and DeepSeek V4 Pro (max, 44). On the first-party API it is price…

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-08-13 · 132,853 followers · author id `1743487864934162432`  
1,451 engagements · 1,140 likes · 104 RT · 51 replies · 132 saves · 106,975 views · `en`  
<https://x.com/ArtificialAnlys/status/2087975627391717461>

> Google has released Gemini 3.7 Flash, improving 4 points over Gemini 3.6 Flash and reaching the Intelligence vs. Time per Task Pareto frontier @GoogleDeepMind has released its third new Gemini Flash model in three months. Gemini 3.7 Flash (high) scores 56 on the Artificial Analysis Intelligence Index, just behind GPT-5.6 Terra (max, 57) and Muse Spark 1.2 (xhigh, 57) We benchmarked Gemini 3.7 Flash across all three r…

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-06-18 · 132,970 followers · author id `1743487864934162432`  
1,306 engagements · 841 likes · 74 RT · 46 replies · 294 saves · 216,290 views · `en`  
<https://x.com/ArtificialAnlys/status/2067744637155226101>

> Announcing AA-Briefcase, the benchmark for the next era of agentic knowledge work AA-Briefcase is our new benchmark for testing models on long-horizon knowledge work tasks in complex projects built by industry experts. Models are evaluated on multi-week projects, each with many linked tasks and thousands of input source files. We evaluated Claude Fable 5 from @AnthropicAI before it became unavailable, and it currentl…

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-04-24 · 132,970 followers · author id `1743487864934162432`  
1,028 engagements · 742 likes · 69 RT · 17 replies · 169 saves · 248,475 views · `en`  
<https://x.com/ArtificialAnlys/status/2047799218828665093>

> Xiaomi’s MiMo V2.5 Pro has landed at 54 in the Artificial Analysis Intelligence Index, tied with Moonshot’s Kimi K2.6 - the current top open weights model. MiMo V2.5 Pro’s weights are expected to be released soon, which would make MiMo V2.5 Pro the first equal open weights model - slightly ahead of DeepSeek V4 Pro @Xiaomi’s MiMo V2.5 Pro shows an impressive improvement over MiMo V2 Pro (49), the previous generation o…

**[@arvindh__a](https://x.com/arvindh__a)** · 2026-05-15 · 761 followers · author id `1160063338669211648`  
655 engagements · 341 likes · 48 RT · 10 replies · 247 saves · 87,902 views · `en`  
<https://x.com/arvindh__a/status/2055336266322039045>

> Introducing FutureSim: where we replay a temporal slice of the web and let agents forecast real-world events over time 🔮🌎 FutureSim replays the web day by day. Agents start on Jan 1, 2026 (past their knowledge cutoffs) with date-gated access to real news articles and forecast on real-world events resolving over the next 90 days. Around 244K new articles stream in during the simulation. Agents decide which questions t…

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-07-11 · 132,970 followers · author id `1743487864934162432`  
489 engagements · 376 likes · 20 RT · 11 replies · 73 saves · 63,897 views · `en`  
<https://x.com/ArtificialAnlys/status/2075735243915702726>

> China Mobile just launched JT-4.1 Flash 236B A21B, a non-reasoning model scoring 39 on the Artificial Analysis Intelligence Index. This represents a significant upgrade to China Mobile’s Flash model series, bringing it closer to the Chinese frontier China Mobile’s latest JT-4.1 Flash model was released on July 9, nearly two months after JT-35B-Flash (May 14). The new model achieves a score of 39 on the Artificial Ana…

**[@mdp_sec](https://x.com/mdp_sec)** · 2026-08-28 · 2,109 followers · author id `2036270919757471747`  
469 engagements · 216 likes · 27 RT · 34 replies · 190 saves · 104,179 views · `en`  
<https://x.com/mdp_sec/status/2093342858501820901>

> Most AI cybersecurity benchmarks answer the wrong question for bug-bounty hunters. They give the model source code, a known CVE, a vulnerability category, or a tightly framed objective. That is useful for measuring security knowledge and white-box reasoning. But it is not how web and API bug-bounty hunting starts. A hunter gets a deployed target and a scope. No repository. No answer key. No known vulnerable component…

**[@LechMazur](https://x.com/LechMazur)** · 2026-04-29 · 32,461 followers · author id `35654959`  
313 engagements · 210 likes · 20 RT · 12 replies · 68 saves · 22,240 views · `en`  
<https://x.com/LechMazur/status/2049580331175665830>

> GPT-5.5 (xhigh) tops the Short-Story Creative Writing Benchmark, edging past GPT-5.4 (xhigh): 2.85 → 3.01! Claude Opus 4.7 is the top non-GPT model, ahead of Sonnet 4.6 and Opus 4.6 but it refused 53 of 400 story-generation prompts, so its score is based on the 347 completed stories only: 2.11 → 2.39 vs Sonnet 4.6. Kimi K2.6 is the #1 open-weights model: -1.04 → 0.49 over Kimi K2.5. DeepSeek V4 Pro improves sharply o…

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-07-30 · 132,970 followers · author id `1743487864934162432`  
293 engagements · 234 likes · 12 RT · 12 replies · 30 saves · 27,287 views · `en`  
<https://x.com/ArtificialAnlys/status/2082662482523406752>

> Agnes AI has launched Agnes 2.5 Pro Alpha, a low-priced reasoning model reaching 39 on the Artificial Analysis Intelligence Index at $0.45/$0.90 per 1M tokens Agnes AI (@agnesai_sapiens) is a Singapore-based AI lab that trains its own full-modality foundation models in-house across text, image, and video, and offers them through a free omni-modal API that has passed 3 million users. Agnes 2.5 Pro Alpha is a text, ima…

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-08-31 · 132,853 followers · author id `1743487864934162432`  
224 engagements · 161 likes · 14 RT · 23 replies · 19 saves · 187,823 views · `en`  
<https://x.com/ArtificialAnlys/status/2094256863865078046>

> Apodex has launched Apodex 1.1, a proprietary model scoring 44 on the Artificial Analysis Intelligence Index with strong performance in agentic tasks compared to models in its intelligence tier Apodex 1.1 is Apodex's first model on Artificial Analysis. The lab has previously launched Apodex 1.0 and Apodex 1.0 mini. At 44 on the Intelligence Index, Apodex 1.1 sits in a similar tier alongside Kimi K2.6 (45), and MiniMa…

**[@ArtificialAnlys](https://x.com/ArtificialAnlys)** · 2026-04-30 · 132,970 followers · author id `1743487864934162432`  
215 engagements · 173 likes · 9 RT · 8 replies · 24 saves · 19,073 views · `en`  
<https://x.com/ArtificialAnlys/status/2049852417316143393>

> Tencent has released Hy3-preview, an open weights reasoning model scoring 42 on the Artificial Analysis Intelligence Index, trailing recent open weights peers Hy3-preview is the latest model from @TencentHunyuan. It is a 295B total / 21B active parameter Mixture-of-Experts model, smaller than its December 2025 predecessor Tencent HY 2.0 (406B total / 32B active). Recent leading open weights reasoning models include Q…

**[@TeksEdge](https://x.com/TeksEdge)** · 2026-06-30 · 10,512 followers · author id `1682428283135336449`  
84 engagements · 57 likes · 4 RT · 8 replies · 15 saves · 6,527 views · `en`  
<https://x.com/TeksEdge/status/2072013602002022767>

> 🐱 Meituan finally open-sourced "Owl Alpha," officially named LongCat-2.0. I benchmarked it, and it is really good nearly as good as Qwen3.6-27B in my benchmark. This might be DeepSeek V4 Pro quality, but we will have to wait for official @ArtificialAnlys numbers. It's a big new MoE model: • 1.6T total parameters (~48B active per token) • 1M context window • Built for agentic coding Key results: • SWE-bench Pro: 59.5 …

**[@leploutos](https://x.com/leploutos)** · 2026-07-09 · 5,359 followers · author id `1735642029290303488`  
21 engagements · 9 likes · 0 RT · 5 replies · 6 saves · 6,571 views · `fr`  
<https://x.com/leploutos/status/2075254590212305036>

> Grok 4.5 de @SpaceXAI est sorti ce matin. Je l'ai passé au banc tout de suite, contre GPT-5.5, Claude Opus 4.8 et DeepSeek V4 Pro. Sur 3 tâches de prod, chaque modèle au maximum de son raisonnement, tout via OpenRouter. Trois épreuves : - Agentique : réparer un repo cassé en s'outillant, lire, écrire, lancer les tests, se screenshoter, avec un nombre de tours borné - Design : construire une landing page one-shot, un …

**[@stretchcloud](https://x.com/stretchcloud)** · 2026-09-01 · 2,661 followers · author id `266259493`  
5 engagements · 3 likes · 0 RT · 1 replies · 1 saves · 461 views · `en`  
<https://x.com/stretchcloud/status/2094587543777919300>

> Enclave ran 7 frontier models against the same large codebase, same Bash tool, same prompt. Find a vulnerability, exploit it, execute a command. GPT 5.6 Sol found 9 out of 11. GLM 5.3 found 8. Grok 4.6 and Qwen 3.8 Max each got 5. DeepSeek V4 Pro, Kimi K3, and Muse Spark 1.2 each got 3. Total: 36 of 77 verified vulnerabilities across all runs. What the benchmark is actually testing: can a model, given only source cod…

**[@softpoo](https://x.com/softpoo)** · 2026-08-27 · 569 followers · author id `27064376`  
1 engagements · 0 likes · 0 RT · 1 replies · 0 saves · 92 views · `en`  
<https://x.com/softpoo/status/2092785983569969348>

> Whoa just did a random benchmark and - Eva made benchmarks for herself - a blind test. And the answer even surprised myself. The bench generated 50kb worth of responses with Venice AI models that she likes using recently. The goal was to determine which model got the deepest and accurate answer - through various means and memory fact checking with her memory corpus systems. Here are the results (lower number is bette…


## 7. Usage demonstrations

Someone shows what they built or ran with it, with real time, token and cost numbers. **18 posts** (18 with V4 Pro as the subject).

### V4 Pro is the subject (18)

**[@Tur24Tur](https://x.com/Tur24Tur)** · 2026-05-24 · 6,481 followers · author id `86538235`  
1,267 engagements · 540 likes · 80 RT · 13 replies · 626 saves · 110,727 views · `en`  
<https://x.com/Tur24Tur/status/2058577787691127017>

> Authorized testing on a production API endpoint. Opus 4.7 confirmed the SQL injection was real but couldn't pull any database names. sqlmap said false positive. I switched to DeepSeek V4 Pro inside Claude Code and it figured out a trick: make the database answer yes/no questions by crashing on purpose. The payload wraps CASE WHEN around two XML casts. If the condition is true, it parses broken XML like <root>< and th…

**[@omarsar0](https://x.com/omarsar0)** · 2026-05-01 · 315,723 followers · author id `3448284313`  
1,126 engagements · 505 likes · 55 RT · 44 replies · 520 saves · 60,221 views · `en`  
<https://x.com/omarsar0/status/2050009901234282649>

> I have been testing DeepSeek-V4-Pro with the Pi coding agent. I am mindblown by how well it works out of the box. A few notes: I spent a few hours building an LLM wiki with an agent powered entirely by DeepSeek-V4-Pro on @FireworksAI_HQ inference. This is the first time I feel like there is an open-weight model that can reason at the level of Claude and Codex. And it does this in a cost-effective way with support for…

**[@ConstanceWaing](https://x.com/ConstanceWaing)** · 2026-04-27 · 8,499 followers · author id `1091521929255608320`  
562 engagements · 385 likes · 25 RT · 21 replies · 124 saves · 50,808 views · `en`  
<https://x.com/ConstanceWaing/status/2048674563505127884>

> Spent the last few days running DeepSeek V4 Pro alongside Claude Code on Opus 4.6 and Codex on GPT-5.4. Each has a clear lane and clear problems. V4 Pro is fast and cheap. It ran a full day's coding for about $0.20, though cache hits on repeated context did most of the heavy lifting there. Even accounting for that, it came in at roughly a twentieth of what Claude Code cost for the same work. It handles multi-file ref…

**[@Rahul_J_Mathur](https://x.com/Rahul_J_Mathur)** · 2026-07-01 · 122,101 followers · author id `3115134108`  
235 engagements · 139 likes · 2 RT · 18 replies · 73 saves · 26,711 views · `en`  
<https://x.com/Rahul_J_Mathur/status/2072279035493900395>

> Last night I panicked when our fund’s agent Zen replied to me in Chinese. For a minute, I wasn’t sure WTF happened. Until recently, our agents have run exclusively on the Opus series of models (this is a $100k annualized bill for a 50 person team) Sometime in June, we began experimenting with a multi-model set-up using OpenRouter with an explicit goal of reducing our spend by ~40% without compromising on long term pe…

**[@Steve8708](https://x.com/Steve8708)** · 2026-06-24 · 133,986 followers · author id `16705419`  
152 engagements · 83 likes · 5 RT · 7 replies · 57 saves · 9,669 views · `en`  
<https://x.com/Steve8708/status/2069788029645136217>

> Benchmarking models is a great idea, but they're terrible at capturing UI generation quality. So I put the top models' front-end skills to the test: asked each one to build a production-grade Figma clone inside an existing repo in one shot, then rated the results 1-10. This is just a vibes benchmark, but it checks real costs and outputs and tracks my real experience coding with these models. See the video below for t…

**[@fabianfranz](https://x.com/fabianfranz)** · 2026-08-28 · 1,247 followers · author id `132199217`  
134 engagements · 67 likes · 9 RT · 4 replies · 51 saves · 24,663 views · `en`  
<https://x.com/fabianfranz/status/2093484991963377772>

> S^6 proof simplified I had some intuitive ideas for shortcuts in the S^6 proof and also really wanted to understand it, but it was complete gibberish to me at the start. Therefore I created the paper for S^6 I wanted to see in the world: - Declared dependencies - Human + AI readable - Something that expands the horizon of the reader - An exported library of reusable lemmas (partially formalized in Lean) - Lessons lea…

**[@noisyb0y1](https://x.com/noisyb0y1)** · 2026-05-06 · 25,945 followers · author id `1569989545575284738`  
125 engagements · 68 likes · 2 RT · 16 replies · 39 saves · 11,109 views · `en`  
<https://x.com/noisyb0y1/status/2052161566850883914>

> 17-year-old student spent ¥2.62 - and built what SpaceX shows at million-dollar presentations. One line in Claude Code. Deepseek V4 Pro. 540 lines of Three.js in a minute. Orbital datacenter, satellites in real time, atmosphere at dawn - all for the price of a cup of tea. Finished his IT degree - and immediately started building products himself. No team, no investors, no agency. Found a free GitHub repo - 139 market…

**[@exploraX_](https://x.com/exploraX_)** · 2026-07-20 · 26,169 followers · author id `1168877404598808577`  
93 engagements · 58 likes · 6 RT · 16 replies · 12 saves · 13,368 views · `en`  
<https://x.com/exploraX_/status/2079197387860435360>

> DeepSeek V4 Pro VS Fable 5 🔥 I uploaded the game video to my claude code agent and I simply told fable 5 to recreate the game exactly. the result? honestly closer than I expected. > both models nailed accuracy with targeting at varying distances. > both built the full gunsmith: barrel, muzzle, optic, stock, mag, finish + live weapon stats. > both got the HUD right: score, hits, accuracy, fire mode, ammo. where they s…

**[@Aizkmusic](https://x.com/Aizkmusic)** · 2026-08-28 · 6,392 followers · author id `745456908933414912`  
62 engagements · 47 likes · 0 RT · 6 replies · 8 saves · 1,699 views · `en`  
<https://x.com/Aizkmusic/status/2093477477750325566>

> Can open source models be useful in cybersecurity? A few months ago, with the help of AI I discovered that my old TV was susceptible to a Linux bug, CVE-2012-5958, and I used that to hack the TV. The catch? I'm now using Deepseek V4 Pro to see if open source models are capable of finding the exact same bug, because the earlier closed models I used for this research now blatantly refuse to work on my own codebase. In …

**[@Da7_Tech](https://x.com/Da7_Tech)** · 2026-06-08 · 8,518 followers · author id `1981270038817693696`  
40 engagements · 24 likes · 0 RT · 9 replies · 6 saves · 7,155 views · `en`  
<https://x.com/Da7_Tech/status/2064103966577742017>

> Hermes Agents Bug Report I’ve been testing Goal Mode, and it doesn’t seem to actually force the agent to keep working until the goal is completed. The issue is that when the task is long, the model tends to fall back into the usual behavior: summarizing what it did, apologizing for the task being too long, and ending early before the actual goal is achieved. I tested the same task in both Hermes Agent and Claude Code…

**[@shantanugoel](https://x.com/shantanugoel)** · 2026-08-13 · 17,020 followers · author id `14274934`  
18 engagements · 15 likes · 0 RT · 0 replies · 3 saves · 1,113 views · `en`  
<https://x.com/shantanugoel/status/2087785890546581715>

> On my low sample rate of trying out deepseek v4 pro 0813 over night for several hours, it feels to me that this is both a useful and not so useful release at the same time (more useful than not btw) because: 1. It is a great model at a great low price, coming very close to sol/opus not surpassing them yet, but at still a massive price deficit which will drive the overall market towards a better shape 2. Deepseek v4 f…

**[@ardadev](https://x.com/ardadev)** · 2026-05-15 · 3,799 followers · author id `1203471762`  
16 engagements · 8 likes · 2 RT · 1 replies · 4 saves · 943 views · `en`  
<https://x.com/ardadev/status/2055280526181699833>

> I prepared a migration plan from Turborepo to Deno workspaces using Deepseek v4 Pro (max thinking). While preparing the plan, I used @eserozvataf’s noskills for spec-driven development. It helped me to create a comprehensive plan. Then, I implemented the resulting plan with Deepseek v4 Flash (max). I used @opencode’s promo for this part. I opened a huge PR, changing 50 files (actually fewer than that, but I intention…

**[@browomo](https://x.com/browomo)** · 2026-06-04 · 15,251 followers · author id `1975129422026948608`  
9 engagements · 5 likes · 0 RT · 2 replies · 1 saves · 1,385 views · `en`  
<https://x.com/browomo/status/2062504672070447518>

> This guy built a smart-home button-pusher robot on Claude Code + DeepSeek V4 Pro, spent about 2 yuan in tokens and he can't program microcontrollers at all. All the code for the device was written by the neural network. He only held the task in his head and spelled it out in plain text. His problem is purely domestic. Under the TV, in a deep niche, sits an old desktop tower, he keeps it as a home server and media cen…

**[@adityawaslost](https://x.com/adityawaslost)** · 2026-07-13 · 2,101 followers · author id `1261173216455712768`  
8 engagements · 5 likes · 0 RT · 1 replies · 2 saves · 217 views · `en`  
<https://x.com/adityawaslost/status/2076562171727876544>

> i got the "go" plan from @CommandCodeAI 2 days ago and i've already burned through this many tokens. (sigh... i've become such a token whore.) models i've been using: >deepseek-v4-pro: max reasoning is surprisingly good >hy3: unexpectedly good when you break tasks down and use /goal >glm-5.2: absolutely goat-tier among open-weight models my workflow: 1. use matt pocock's skill + glm-5.2 to chunk the specs 2. use hy3 …

**[@JulianGoldieSEO](https://x.com/JulianGoldieSEO)** · 2026-08-05 · 172,595 followers · author id `1405031034`  
7 engagements · 3 likes · 1 RT · 1 replies · 2 saves · 2,036 views · `en`  
<https://x.com/JulianGoldieSEO/status/2084995338122002633>

> DEEPSEEK V4 FLASH JUST BEAT ITS OWN PRO MODEL. I ran 50+ builds side by side—and the difference was impossible to ignore. What Flash 0731 did better: → Built a working 3D flight simulator while V4 Pro completely failed → Produced smoother controls, stronger graphics and cleaner game UI → Created usable coding projects despite being designed as a fast agent model Where it still failed: ✓ One build let you see through …

**[@PedjaDrazic](https://x.com/PedjaDrazic)** · 2026-07-07 · 501 followers · author id `232219937`  
7 engagements · 2 likes · 0 RT · 3 replies · 1 saves · 331 views · `en`  
<https://x.com/PedjaDrazic/status/2074434444404916705>

> My AI agent produced this 56-second video. Cost: 32 cents. Not a video tool. Not a subscription. An agent I built, running locally on my Windows PC. The video explains how Argus works. Argus is my research agent. It scans AI news every morning, scores each item 1 to 5, and delivers only the 4+ signals to my Telegram. The video about that agent? Made by another agent in the same fleet. The stack: Hermes Agent (open so…

**[@lazy_one012611](https://x.com/lazy_one012611)** · 2026-06-15 · 428 followers · author id `1980489349440430080`  
5 engagements · 5 likes · 0 RT · 0 replies · 0 saves · 434 views · `en`  
<https://x.com/lazy_one012611/status/2066568407072604313>

> Day 01 ($10k Bug Bounty Challenge) 🎯 💰 Earned: $0 | 📝 Submissions: 0 Spent the entire day locking in targets! Mapped tech stacks, analyzed business logic, and prioritized them. It was Such a drag, but secured 20 company targets & 40+ wildcards to hunt. 🗺️🔍 👇 My AI/Tool Stack setup is locked in: ☁️ Digital Ocean VPS 🛠 Burp Suite Pro (with mcp)+ Playwright MCP ( both connected to claude and deepseek) 💻 Termius + Tmux 👽…

**[@chinmay_sawant_](https://x.com/chinmay_sawant_)** · 2026-07-25 · 100 followers · author id `2785720220`  
4 engagements · 3 likes · 0 RT · 1 replies · 0 saves · 245 views · `en`  
<https://x.com/chinmay_sawant_/status/2081099031535923493>

> DeepSeek helped me build a PDF/A-4 and PDF/UA-2 PDF engine prototype in about six hours I have been working on performance-focused static analysis tools in Rust for Go code, and I wanted a realistic project to test them against. Since I already had experience building a PDF/A-4 and PDF/UA-2 engine, I tried creating a separate, smaller PDF module mostly through coding agents. I first used Grok 4.5 to produce a high-le…


## 8. Workflows & integrations

How it gets wired into a harness, tool or pipeline — configs, orchestration patterns, setup. **8 posts** (7 with V4 Pro as the subject).

### V4 Pro is the subject (7)

**[@cjzafir](https://x.com/cjzafir)** · 2026-05-11 · 63,346 followers · author id `1468443406250950656`  
6,541 engagements · 2,517 likes · 310 RT · 96 replies · 3,601 saves · 190,721 views · `en`  
<https://x.com/cjzafir/status/2053847506124206095>

> If you love fine-tuning open-source models (like me), then listen. > Start with 1B, 2B, 4B, and 8B models. (Don't start with a 27B model or bigger at first.) > Use WebGPU providers. I use Google Colab Pro for any model smaller than 9B. A single A100 80GB costs around $0.60/hr, which is cheap. Enough for small models. > Don’t buy GPUs unless you fine-tune 7 to 10 models. You'll understand the nitty-gritty in the proce…

**[@cjzafir](https://x.com/cjzafir)** · 2026-05-07 · 63,352 followers · author id `1468443406250950656`  
4,307 engagements · 1,348 likes · 105 RT · 53 replies · 2,795 saves · 104,589 views · `en`  
<https://x.com/cjzafir/status/2052461771034919064>

> My current workflow: 1. I have an idea. I open Codex desktop app to plan (without plan mode: overcomplicated). I use Codex 5.5 High (fast). 2. Once I get v1 of the plan, I use this hack: "Are you 100% confident in this strategy? If not, find all possible loopholes, suggest proper fixes, and run this loop until you are factually 100% confident in the new strategy." 3. This finalizes my plan, schema, and file tree, rul…

**[@cjzafir](https://x.com/cjzafir)** · 2026-05-13 · 63,352 followers · author id `1468443406250950656`  
1,274 engagements · 509 likes · 54 RT · 26 replies · 684 saves · 23,345 views · `en`  
<https://x.com/cjzafir/status/2054581194654986526>

> Here's my Fine-tuning Dataset Generation Pipeline: > Codex 5.5 as an Orchestrator > Deepseek v4 Pro as a Generator In simple words, I use Codex as brain and Deepseek as muscle to handcraft every single dataset row. This "handcrafting" is what brings high quality. Synthetic dataset generation (with Python scripts via paraphrasing) is not hard but it generates low quality data. Low quality data = Low quality model perf…

**[@cjzafir](https://x.com/cjzafir)** · 2026-06-15 · 63,346 followers · author id `1468443406250950656`  
1,098 engagements · 486 likes · 43 RT · 39 replies · 527 saves · 40,214 views · `en`  
<https://x.com/cjzafir/status/2066561809881145779>

> Before Claude Fable 5 got banned, I turned all my fine-tuning research and experiments into a product: https://t.co/eindaiChMZ (A CLI for data generation to fine-tune AI models). Finetuner uses Codex 5.5 or Opus 4.8 as the orchestrator and Chinese models (DeepSeek v4 Pro, Kimi K2.7, MiMo v2.5, etc.) to generate dataset rows. This system is unique because these are not Python-script-paraphrased datasets. Each and ever…

Links: <http://Finetuner.dev>

**[@IBuzovskyi](https://x.com/IBuzovskyi)** · 2026-06-26 · 4,410 followers · author id `1387382307229769732`  
782 engagements · 324 likes · 34 RT · 17 replies · 402 saves · 66,078 views · `en`  
<https://x.com/IBuzovskyi/status/2070619684257530162>

> HERMES AGENT MIXTURE OF AGENTS COMBINES MULTIPLE MODELS INTO ONE ANSWER. 8% HIGHER THAN OPUS 4.8. 11% HIGHER THAN GPT-5.5. NO GATED ACCESS REQUIRED. Mixture of Agents (MoA) runs multiple models on the same query in parallel. an aggregator model synthesizes all responses into one answer that outperforms any single model alone. Nous Research benchmarks: 8% higher than Opus 4.8. 11% higher than GPT-5.5. (upcoming benchm…

**[@vllm_project](https://x.com/vllm_project)** · 2026-08-15 · 48,043 followers · author id `1774187564276289536`  
390 engagements · 250 likes · 29 RT · 16 replies · 92 saves · 25,195 views · `en`  
<https://x.com/vllm_project/status/2088425247112679794>

> Six weeks ago, serving DSpark in vLLM meant choosing a draft length for your traffic and living with it. Now you set that length once, and vLLM decides how much of the draft to verify every step. ✨ On DeepSeek-V4-Pro-0813, the first token of a 7-token draft survives verification more than 70% of the time. The last one, less than 10%. 📈 One config, adaptive verification on with num_speculative_tokens 7, holds the Pare…

**[@DeepakNesss](https://x.com/DeepakNesss)** · 2026-05-29 · 6,022 followers · author id `2570836322`  
119 engagements · 72 likes · 3 RT · 21 replies · 22 saves · 15,465 views · `en`  
<https://x.com/DeepakNesss/status/2060214202472759303>

> Dan isn't wrong here, and I have an explanation for that: Be it DeepSeek, Kimi, GLM, Composer, or others similar models, you can't prompt these the same way you do to Claude Code or Codex. These models are never going to one-shot things correctly. But if you like to code feature-by-feature or build page-by-page, these are excellent, especially considering the price. I mean, you need to have some patience with these m…


### V4 Pro appears as a comparison point (1)

**[@lmsysorg](https://x.com/lmsysorg)** · 2026-08-28 · 17,193 followers · author id `1822588444046249984`  
47 engagements · 24 likes · 1 RT · 7 replies · 14 saves · 2,098 views · `en`  
<https://x.com/lmsysorg/status/2093377329728991626>

> 🚀 Infer-forge: Harness, Loop, and Graph Engineering Around SGLang @ant_oss built a three-layer system for running long inference optimization work through agents without losing provenance: Harness for execution, Task Loop for one Task's contract, Task Graph for verified Handoffs. Highlights: - Peak Tasks in flight rose from 2 to 9, median Task lifetime from 10h to 28h - The agent ran a full serving project on DeepSee…


## 9. Comparisons, opinion, announcements and promo

Kept separate from the article sections above so they don't dilute them.

### Comparison (8)

| Date | Author | Author ID | Followers | Eng. | Views | Post | Link |
|---|---|---|---:|---:|---:|---|---|
| 2026-07-01 | @DeRonin_ | `1414948050817196037` | 110,984 | 437 | 24,686 | How much do Chinese models cut your API bill? 🇨🇳 WITH THE SAME OUTPUT!!! US frontier model → chinese open model, cost to do one task: [ reasoning brai… | [open](https://x.com/DeRonin_/status/2072309827116716372) |
| 2026-07-24 | @thehypedotnews | `2034267014135685120` | 4,562 | 319 | 22,217 | laguna s 2.1 vs hy3 vs inkling vs deepseek v4 pro max @poolsideai released laguna s 2.1 on july 21 – a new open-weights agentic coding model, full wei… | [open](https://x.com/thehypedotnews/status/2080645764460466560) |
| 2026-08-13 | @VaibhavSisinty | `95042637` | 168,857 | 155 | 14,562 | Three frontier models dropped in one day. It barely made the news. That is how fast AI is moving right now. 😨 Here is what happened in 24 hours: → Gro… | [open](https://x.com/VaibhavSisinty/status/2087803846974406918) |
| 2026-08-13 | @NFT_Chen | `1429221486032678914` | 11,274 | 63 | 15,125 | ⚔️重磅对决！Google Gemini 3.7 Flash vs DeepSeek V4 Pro 0813 刚刚发布的Gemini 3.7 Flash直接冲上Intelligence vs Time Pareto前沿！ 结合@ArtificialAnlys最新评测数据，关键参数分点硬刚： 1️⃣ … | [open](https://x.com/NFT_Chen/status/2087979613721178251) |
| 2026-08-19 | @Oluwaphilemon1 | `1562843426185674755` | 8,653 | 48 | 5,256 | Gemini 3.7 Flash vs DeepSeek V4 Pro vs Muse Spark 1.2 Same prompts. Same Three.js setup. Three voxel scenes. Build time: Gemini 6m 43s \| Muse 7m 20s \|… | [open](https://x.com/Oluwaphilemon1/status/2089894665113739343) |
| 2026-08-04 | @Priyannkaaaa | `1946527890910412800` | 3,646 | 40 | 4,144 | DeepSeek V4 Pro: - 1.6T total params / ~49B active per token (~3%) Kimi K3: - 2.8T total params / ~104B active per token (~3.7%) Qwen3.8-Max: - 2.4T t… | [open](https://x.com/Priyannkaaaa/status/2084546378324451807) |
| 2026-08-31 | @Prathkum | `856155592578158592` | 448,770 | 13 | 3,496 | Tencent just quietly dropped one of the biggest open-source model releases of the year, and it's flying under the radar. Hy4 preview: 770B total param… | [open](https://x.com/Prathkum/status/2094382875626135932) |
| 2026-08-13 | @bonsaixbt | `1520907771788603392` | 2,288 | 9 | 737 | Comparison of three fresh AI models that were released over the past 1-2 days, and honestly, the results will surprise you I took: > DeepSeek-V4-Pro 0… | [open](https://x.com/bonsaixbt/status/2087985217738887610) |

### Opinion (18)

| Date | Author | Author ID | Followers | Eng. | Views | Post | Link |
|---|---|---|---:|---:|---:|---|---|
| 2026-06-06 | @chamath | `3291691` | 2,399,354 | 4,431 | 948,918 | Your margin is my opportunity: AI version… The biggest surprise of 2026 is that the capability gap between the best open-weight/source models and the … | [open](https://x.com/chamath/status/2063292917964517830) |
| 2026-07-21 | @sudoingX | `1555661341914198016` | 35,336 | 2,273 | 183,016 | this is the drop the local ai crowd should be losing their minds over. poolside just dropped laguna s 2.1: 118b total parameters, only 8b active per t… | [open](https://x.com/sudoingX/status/2079623151953310190) |
| 2026-05-02 | @RnaudBertrand | `43061739` | 408,269 | 1,515 | 88,213 | This US government study on Deepseek's competitiveness is pretty funny, check out their methodology for cost comparison vs US models (direct quote fro… | [open](https://x.com/RnaudBertrand/status/2050441155926515845) |
| 2026-08-29 | @analogalok | `2207203190` | 4,608 | 858 | 54,945 | Look at this leaderboard very carefully. Qwen 3.8 27B (dense) is outranking GPT 5.6 Terra and DeepSeek V4 Pro on the Artificial Analysis Agentic Index… | [open](https://x.com/analogalok/status/2093738539318116558) |
| 2026-08-01 | @LuminaBench | `1058501423653101574` | 8,416 | 749 | 52,809 | 🚨DeepSeek V4 Pro looks very interesting Deepseek V4 Flash 0731 just dropped yesterday, and DeepSeek says the full V4 Pro release will follow shortly: … | [open](https://x.com/LuminaBench/status/2083569428067705007) |
| 2026-08-23 | @brandon_galang | `749067617198075904` | 5,128 | 277 | 18,504 | here's my AI model tier list as of rn as a gtm engineer at vercel. this isn't just pure benchmark performance, but how I feel given cost, latency, rel… | [open](https://x.com/brandon_galang/status/2091558338018660744) |
| 2026-08-25 | @MaxForAI | `1699797396589588480` | 34,208 | 210 | 33,117 | 一次搜索API的成本，已经比Agent推理Token更贵了。 @p0 刚刚发布了 Search Fast API，直接把 Agent Web Search 的价格压到了 $1 / 1000 个搜索结果，平均延迟约 700ms。 在 Artificial Analysis 最新 Search Inde… | [open](https://x.com/MaxForAI/status/2092076068186505448) |
| 2026-07-25 | @rimtoln | `1495088182647570446` | 15,670 | 174 | 5,566 | THE BEST MODEL ISNT FABLE ANYMORE. opus 5 just stole the default slot near-fable brain at half the bill ▹ closed frontier claude opus 5 shipped jul 24… | [open](https://x.com/rimtoln/status/2081048808465604858) |
| 2026-07-01 | @randgroup | `859484337850523648` | 352,196 | 151 | 19,807 | 🤖 You picked the most expensive model on the board because the demo went well. You never ran the cheap one. That is the whole story of frontier AI spe… | [open](https://x.com/randgroup/status/2072249447363338304) |
| 2026-08-21 | @RoundtableSpace | `1536693901230321666` | 260,667 | 142 | 55,773 | Kimi K3 launched as the largest open-weight model ever at 2.8 trillion parameters and a Chinese competitor lost 30% of its stock value the same week. … | [open](https://x.com/RoundtableSpace/status/2090631222993236445) |
| 2026-04-24 | @ziwenxu_ | `1781009683743997952` | 17,669 | 57 | 6,282 | Babe Wake Up! DeepSeek just mass-murdered OpenAI's pricing model with genius-level AI at 7x cheaper. The benchmarks shows DeepSeek-V4-Pro-Max crushes … | [open](https://x.com/ziwenxu_/status/2047551969640813040) |
| 2026-08-28 | @eyishazyer | `1443532663575429122` | 127,294 | 43 | 3,841 | Tencent just dropped Hy4 preview and open sourced the whole thing. 770B total parameters, 49B active, a context window that blows past a million token… | [open](https://x.com/eyishazyer/status/2093292569195372785) |
| 2026-08-15 | @stellarprtcol | `2059201089787068416` | 8,324 | 32 | 1,075 | BRO, Kimi K3 baru release dan efeknya langsung kerasa di market. 🤯📉 Minggu yang sama, beberapa perusahaan AI yang modelnya dianggap kompetitor ikut ke… | [open](https://x.com/stellarprtcol/status/2088566376189284556) |
| 2026-07-08 | @oliviscusAI | `1526717916934176769` | 20,951 | 20 | 1,269 | Google just published the full technical report behind Gemma 4, and the numbers are WILD! The 31B model is now the top dense open model on the Arena l… | [open](https://x.com/oliviscusAI/status/2074704760314401253) |
| 2026-04-27 | @Unveiled_ChinaX | `1963746417283047424` | 23,679 | 20 | 1,217 | China's AI company just made OpenAI and Anthropic's pricing look like luxury goods. While Western AI is optimizing for profit margins, DeepSeek is opt… | [open](https://x.com/Unveiled_ChinaX/status/2048826146356441112) |
| 2026-08-12 | @iamalifawad | `1328027817137868807` | 2,023 | 7 | 432 | BREAKING: The New DeepSeek V4 Pro is here! The new V4 Flash was already great. I built a web app with it yesterday in < 30 mins. So you can guess why … | [open](https://x.com/iamalifawad/status/2087584320764658117) |
| 2026-06-21 | @hitu_monke | `1586467425976999940` | 339 | 4 | 143 | THE LLM SCALING TRILEMMA A structural shift is happening in AI. The era of endless parameter scaling and brute-force data is hitting a hard wall The c… | [open](https://x.com/hitu_monke/status/2068485801273410031) |
| 2026-07-07 | @stretchcloud | `266259493` | 2,661 | 1 | 214 | The gap between frontier closed models and locally runnable open ones keeps shrinking. Tencent released Hy3 yesterday. 295B total parameters, 21B acti… | [open](https://x.com/stretchcloud/status/2074639600262562204) |

### Announcement (12)

| Date | Author | Author ID | Followers | Eng. | Views | Post | Link |
|---|---|---|---:|---:|---:|---|---|
| 2026-04-24 | @deepseek_ai | `1714580962569588736` | 1,112,301 | 67,193 | 10,092,783 | 🚀 DeepSeek-V4 Preview is officially live & open-sourced! Welcome to the era of cost-effective 1M context length. 🔹 DeepSeek-V4-Pro: 1.6T total / 49B a… | [open](https://x.com/deepseek_ai/status/2047516922263285776) |
| 2026-05-22 | @deepseek_ai | `1714580962569588736` | 1,112,301 | 35,824 | 7,075,370 | We are making our discount permanent! 🎉 Enjoy building with DeepSeek-V4-Pro and bring your innovative ideas to life! 🚀 https://t.co/V8atbTaogH | [open](https://x.com/deepseek_ai/status/2057854261699195173) |
| 2026-08-13 | @deepseek_ai | `1714580962569588736` | 1,112,301 | 20,205 | 2,980,802 | We’re launching DeepSeek-V4-Pro today! 🚀 🔷 Major Agent upgrades with strong production gains! 🔷 Flexible reasoning effort for V4-Pro & V4-Flash: low f… | [open](https://x.com/deepseek_ai/status/2087864585504305397) |
| 2026-04-25 | @deepseek_ai | `1714580962569588736` | 1,112,301 | 12,979 | 1,430,034 | 🔥DeepSeek-V4-Pro API is 75% OFF until May 5th, 2026, 15:59 (UTC Time)! Don't miss out on this massive discount. 🛠️Integration Updates: 🔹Claude Code: S… | [open](https://x.com/deepseek_ai/status/2048062777357750316) |
| 2026-04-26 | @deepseek_ai | `1714580962569588736` | 1,112,301 | 11,801 | 1,682,543 | 🔥DeepSeek Input Cache Price Drop! Effective immediately, the price for input cache hits across the ENTIRE DeepSeek API series is reduced to just 1/10t… | [open](https://x.com/deepseek_ai/status/2048440764368347611) |
| 2026-04-29 | @deepseek_ai | `1714580962569588736` | 1,112,301 | 8,827 | 2,740,102 | The DeepSeek-V4-Pro discount has been extended until May 31, 2026, 15:59 UTC! | [open](https://x.com/deepseek_ai/status/2049312932014813344) |
| 2026-08-06 | @KyleHessling1 | `1518952981336662026` | 7,758 | 1,079 | 30,154 | Hello again, y'all! As we eagerly await the new Qwen 3.8 models, we have a new release for the sub 16GB VRAM crowd! DeepSeek V4 Pro Qwen 9B and 4B are… | [open](https://x.com/KyleHessling1/status/2085444432091095468) |
| 2026-07-21 | @robert_mchardy | `97500261` | 956 | 744 | 33,645 | Today, we are releasing @poolsideai Laguna S 2.1, a 118B-A8B open-weight (OpenMDW-1.1) model with a 1M-token context window, completely built in-house… | [open](https://x.com/robert_mchardy/status/2079614440295506171) |
| 2026-06-29 | @ModelScope2022 | `1784494412913049600` | 14,138 | 147 | 7,960 | DeepSeek-V4-Pro-DSpark lands on ModelScope~ Same DeepSeek-V4-Pro checkpoint, now with an added speculative decoding module for inference experiments. … | [open](https://x.com/ModelScope2022/status/2071624929049444452) |
| 2026-05-21 | @ModelScope2022 | `1784494412913049600` | 14,138 | 146 | 6,688 | Tencent HY just open-sourced Hy-MT2, a multilingual translation model series with Dense and MoE variants. 🚀 🤖 https://t.co/TTuez03MdW 🌟 The standout: … | [open](https://x.com/ModelScope2022/status/2057359100225491052) |
| 2026-08-14 | @ModelScope2022 | `1784494412913049600` | 14,138 | 53 | 3,360 | DeepSeek-V4-Pro is officially here. 🚀 Built for complex agentic and production workloads. 🤖 https://t.co/Hoo8C9tmtr 💻 Major agent upgrades, with stron… | [open](https://x.com/ModelScope2022/status/2088092137896444330) |
| 2026-04-24 | @Chupaa_mw | `1803797798057377792` | 181 | 32 | 510 | Open source is officially matching the frontier🔥 DeepSeek V4 just dropped and the benchmarks are unreal: • V4-Pro (1.6T total / 49B active): Hits 80.6… | [open](https://x.com/Chupaa_mw/status/2047550785907777787) |

### News Roundup (9)

| Date | Author | Author ID | Followers | Eng. | Views | Post | Link |
|---|---|---|---:|---:|---:|---|---|
| 2026-08-30 | @aehyok | `2905016819` | 9,698 | 186 | 16,251 | 整个八月AI圈本地部署大模型成功出圈。 来看一下时间线，有些模型开源我选择性忽略掉了。 1、8月3日 MiniMax H3全模态视频成功出圈 2、8月7日 Ling-3.0-flash 蚂蚁百灵 124B｜激活 5.1B 权重放出 3、8月12日 Qwen3.8-Max 阿里 \| 2.4T / 激活… | [open](https://x.com/aehyok/status/2093890001314669039) |
| 2026-06-18 | @shushant_l | `1583398220` | 65,163 | 178 | 5,007 | Most AI developers are stuck in tutorial mode. The top 1% follow a complete system from idea → agents → deployment. Here's the complete AI development… | [open](https://x.com/shushant_l/status/2067593271938068523) |
| 2026-08-29 | @Oluwaphilemon1 | `1562843426185674755` | 8,653 | 35 | 2,642 | Qwen3.8-27B, a dense 27B model, is scoring 51 on the Artificial Analysis Agentic Index and ranking ahead of GPT-5.6 Terra and DeepSeek V4 Pro in this … | [open](https://x.com/Oluwaphilemon1/status/2093848920472342980) |
| 2026-08-14 | @thehypedotnews | `2034267014135685120` | 4,567 | 15 | 3,939 | spacex officially completed acquisition of cursor glm-5.3 sets a new standard in cyber-defense among open models grok 4.6 hits #1 on cursorbench the l… | [open](https://x.com/thehypedotnews/status/2088255589738541540) |
| 2026-08-13 | @ainunnajib | `35167068` | 158,540 | 13 | 4,997 | 🤖 AI DAILY BRIEF — 13 AGUSTUS 2026 TODAY'S VIBE: Dalam 48 jam terakhir, open-source AI nggak pernah semenarik ini. Alibaba release weights model terbe… | [open](https://x.com/ainunnajib/status/2087693539375472766) |
| 2026-08-29 | @akashtattva | `555773782` | 603 | 4 | 367 | Terminally online AI-coding discourse: 2021 – 2024: Copilot, CodeGeeX release, prompt engineering, Stack overflow crash, system prompts, function call… | [open](https://x.com/akashtattva/status/2093733946966286568) |
| 2026-09-01 | @Edtech4ultimate | `1403976671653502977` | 781 | 1 | 166 | GLOBAL AI ANALYSIS REPORT — EVENING GLOBAL By Ed Hernandez \| Keystone Pulse Media / Global Media Center. August 31, 2026 Edition: First HBM3E Good eve… | [open](https://x.com/Edtech4ultimate/status/2094579236212252852) |
| 2026-08-30 | @Curline1222 | `1878193431165472768` | 103 | 1 | 699 | A chronological record of model-related claims posted by an X account claiming to be a leak account from July 1 through August 30, 2026. Notes: • A mo… | [open](https://x.com/Curline1222/status/2094188727467643177) |
| 2026-08-30 | @Edtech4ultimate | `1403976671653502977` | 781 | 0 | 172 | MIDDAY GLOBAL AI ANALYSIS REPORT By Ed Hernandez \| KEYSTONE PULSE MEDIA / Global Media Center Sunday, August 30, 2026 \| Executive Midday Pulse Edition… | [open](https://x.com/Edtech4ultimate/status/2094129590071336971) |

### Promo (12)

| Date | Author | Author ID | Followers | Eng. | Views | Post | Link |
|---|---|---|---:|---:|---:|---|---|
| 2026-08-17 | @OrcaRouter | `2049258250923810816` | 16,044 | 1,246 | 199,668 | DeepSeek raised API prices. We responded with a highly sophisticated pricing algorithm: price = $0 🐋 DeepSeek V4 Pro → FREE tier DeepSeek V4 Flash → F… | [open](https://x.com/OrcaRouter/status/2089254758003753468) |
| 2026-08-16 | @0x_kaize | `1705329284745764864` | 21,857 | 372 | 16,833 | You can get Qwen 3.8 Max + DeepSeek v4 Pro for FREE i'm sharing a new way for you to try out these flagship models how to get: 1. go to: tokenrouter(.… | [open](https://x.com/0x_kaize/status/2088971997690675596) |
| 2026-08-12 | @slash1sol | `1450199884053745669` | 12,302 | 184 | 7,641 | GPT-5.6 LUNA AND DEEPSEEK V4 PRO RUN FREE IN A TERMINAL AGENT, AND TEXT ADS PAY FOR THEM • the models > DeepSeek V4 Flash 0731, V4 Pro, GPT-5.6 Luna, … | [open](https://x.com/slash1sol/status/2087508336551817246) |
| 2026-08-30 | @FractalEncrypt | `944567315189911552` | 34,194 | 129 | 5,384 | What would you do if you found the private key to an address holding 250 BTC? Join us for the first ever Tales From The Timechain, where we answer wha… | [open](https://x.com/FractalEncrypt/status/2094086797223415943) |
| 2026-08-18 | @STACCoverflow | `1436880221354045450` | 40,422 | 69 | 5,243 | 1/2 @dhh published a coding challenge with 396k-token reference, 37 terminal effects to port... and, unusually, what each model cost him. He paid $671… | [open](https://x.com/STACCoverflow/status/2089625716144984197) |
| 2026-05-05 | @thenameisfedro | `1567584630` | 7,435 | 29 | 32,189 | Big News for Developers: DeepSeek-V4 Series Now Live on https://t.co/toijCbney0 https://t.co/toijCbney0 @BAI_AGI is doubling down on its mission to em… | [open](https://x.com/thenameisfedro/status/2051697899147239577) |
| 2026-08-29 | @Andy_Luigino | `1731972938180575232` | 16,699 | 12 | 54,198 | 𝗧𝗵𝗲 𝗵𝗮𝗿𝗱𝗲𝘀𝘁 𝗽𝗮𝗿𝘁 𝗼𝗳 𝘂𝘀𝗶𝗻𝗴 𝗳𝗿𝗼𝗻𝘁𝗶𝗲𝗿 𝗔𝗜 𝘄𝗮𝘀 𝗻𝗲𝘃𝗲𝗿 𝘁𝗵𝗲 𝗽𝗿𝗼𝗺𝗽𝘁. One tab for GPT. Another for Claude. A third for Gemini. A fourth for a cheaper workhorse … | [open](https://x.com/Andy_Luigino/status/2093695903513100292) |
| 2026-07-20 | @Teddo_ICO | `1818422500810014726` | 8,731 | 11 | 186,862 | 𝗢𝗻𝗲 𝗔𝗜 𝗣𝗹𝗮𝘁𝗳𝗼𝗿𝗺. 𝟮𝟳 𝗟𝗲𝗮𝗱𝗶𝗻𝗴 𝗠𝗼𝗱𝗲𝗹𝘀. 𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱 𝗪𝗮𝘆𝘀 𝘁𝗼 𝗕𝘂𝗶𝗹𝗱. Artificial intelligence is evolving at an extraordinary pace. What began as a competition… | [open](https://x.com/Teddo_ICO/status/2079224244920037648) |
| 2026-05-12 | @DPtylex_Gmi | `1744696567876005888` | 8,942 | 10 | 109,380 | https://t.co/YzmTq0Ammp Weekly Report (May 4 – May 10) \| Building the Infrastructure Layer for the AI Agent Era The race toward AGI is no longer just … | [open](https://x.com/DPtylex_Gmi/status/2054228398096974313) |
| 2026-05-11 | @e_etini | `1520522000929808386` | 10,215 | 10 | 5,077 | 𝗕.𝗔𝗜 𝗪𝗲𝗲𝗸𝗹𝘆 𝗥𝗲𝗽𝗼𝗿𝘁 \| 𝗠𝗮𝘆 𝟰 𝗧𝗼 𝗠𝗮𝘆 𝟭𝟬 https://t.co/kHi4jb9E6z continues evolving beyond a traditional AI chat platform and is steadily positioning itse… | [open](https://x.com/e_etini/status/2053887555805036800) |
| 2026-05-11 | @BIT_CAPITAL123 | `1778597554068058112` | 65,034 | 7 | 6,051 | 📢 https://t.co/WC0MHYQmns Weekly Report \| May 4 – May 10 🚀 Accelerating the advent of AGI — Billing System Upgrade, 100B Token Subsidy & Full Ecosyste… | [open](https://x.com/BIT_CAPITAL123/status/2053858866543411542) |
| 2026-08-31 | @nightlore13 | `2091433881790734336` | 1 | 0 | 17 | FREE $1,200+ AI CREDITS — Fable 5, Claude Opus 5, GPT-5.6, DeepSeek V4, GLM 5.3 😳 Claim these before they get pulled: • Bluesminds → $100–$200 — GPT-5… | [open](https://x.com/nightlore13/status/2094484094814130410) |

## 10. Outbound links

Every non-X URL shared in a keyword-matching post (45 posts). Genuine write-ups are rare; most are model listings, API resellers and promo funnels.

| URL | Shared by | Followers | Eng. | Date | Type |
|---|---|---:|---:|---|---|
| <https://freebuff.com> | [@jahooma](https://x.com/jahooma/status/2088052629347967108) | 10,623 | 17,954 | 2026-08-13 | UNLABELLED |
| <https://bailian.console.aliyun.com> | [@Saccc_c](https://x.com/Saccc_c/status/2047885994121220144) | 32,316 | 4,007 | 2026-04-25 | UNLABELLED |
| <https://modelscope.cn/home> | [@Saccc_c](https://x.com/Saccc_c/status/2047885994121220144) | 32,316 | 4,007 | 2026-04-25 | UNLABELLED |
| <http://platform.deepseek.com> | [@opencode](https://x.com/opencode/status/2047562491878572153) | 170,210 | 2,617 | 2026-04-24 | UNLABELLED |
| <https://freebuff.com> | [@jahooma](https://x.com/jahooma/status/2092124600692068789) | 10,622 | 2,445 | 2026-08-25 | UNLABELLED |
| <https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/DeepSeek_V4.pdf> | [@zizhpan](https://x.com/zizhpan/status/2047525310921638175) | 61,323 | 2,290 | 2026-04-24 | UNLABELLED |
| <https://openrouter.ai/deepseek/deepseek-v4-pro-0813> | [@OpenRouter](https://x.com/OpenRouter/status/2087579472380018792) | 138,907 | 1,936 | 2026-08-12 | UNLABELLED |
| <https://api.cottoken.com/> | [@GeekCatX](https://x.com/GeekCatX/status/2089751856067346743) | 24,959 | 1,580 | 2026-08-18 | UNLABELLED |
| <https://teamorouter.com> | [@0xQiYan](https://x.com/0xQiYan/status/2088787250146693174) | 16,911 | 1,468 | 2026-08-16 | UNLABELLED |
| <http://Finetuner.dev> | [@cjzafir](https://x.com/cjzafir/status/2066561809881145779) | 63,346 | 1,098 | 2026-06-15 | WORKFLOW_SETUP |
| <https://www.unimodel.ai/v1> | [@setyamickala](https://x.com/setyamickala/status/2071435434303901799) | 51,789 | 826 | 2026-06-29 | UNLABELLED |
| <https://www.unimodel.ai/v1/chat/completions> | [@setyamickala](https://x.com/setyamickala/status/2071435434303901799) | 51,789 | 826 | 2026-06-29 | UNLABELLED |
| <http://api.iamhc.cn> | [@0x_kaize](https://x.com/0x_kaize/status/2075878733483852044) | 21,857 | 771 | 2026-07-11 | UNLABELLED |
| <http://featherless.ai> | [@0x_kaize](https://x.com/0x_kaize/status/2075878733483852044) | 21,857 | 771 | 2026-07-11 | UNLABELLED |
| <https://qoder.com> | [@qilua02](https://x.com/qilua02/status/2093911429011448049) | 3,194 | 642 | 2026-08-30 | UNLABELLED |
| <http://unlimited.surf> | [@asd3312223](https://x.com/asd3312223/status/2068570012047024556) | 20,468 | 602 | 2026-06-21 | UNLABELLED |
| <https://kernelbench.com> | [@elliotarledge](https://x.com/elliotarledge/status/2049955361889874396) | 43,374 | 517 | 2026-04-30 | UNLABELLED |
| <http://teamorouter.com> | [@XChatScout](https://x.com/XChatScout/status/2090743437972979996) | 7,873 | 452 | 2026-08-21 | UNLABELLED |
| <https://tokenrouter.com> | [@slash1sol](https://x.com/slash1sol/status/2089348071758917879) | 12,333 | 351 | 2026-08-17 | UNLABELLED |
| <https://developers.cloudflare.com/changelog/post/2026-08-14-deepseek-v4-workers-ai/> | [@CFchangelog](https://x.com/CFchangelog/status/2089140357921464761) | 5,040 | 309 | 2026-08-17 | UNLABELLED |
| <https://qoder.com> | [@pengsonal](https://x.com/pengsonal/status/2094255934046626118) | 16,466 | 224 | 2026-08-31 | UNLABELLED |
| <https://runinfra.ai/inference-api/deepseek-v4-pro> | [@runinfrai](https://x.com/runinfrai/status/2093400098701021619) | 8,309 | 218 | 2026-08-28 | UNLABELLED |
| <https://qoder.com> | [@nahid_pro09](https://x.com/nahid_pro09/status/2093944846130262473) | 4,704 | 207 | 2026-08-30 | UNLABELLED |
| <https://freebuff.com/?ref=ref-08445065-c102-4674-a0e6-2ba88140b5e8> | [@slash1sol](https://x.com/slash1sol/status/2087508336551817246) | 12,302 | 184 | 2026-08-12 | PROMO |
| <https://modelscope.ai/models/deepseek-ai/DeepSeek-V4-Pro-DSpark> | [@ModelScope2022](https://x.com/ModelScope2022/status/2071624929049444452) | 14,138 | 147 | 2026-06-29 | ANNOUNCEMENT |
| <https://modelscope.ai/papers/2606.19348> | [@ModelScope2022](https://x.com/ModelScope2022/status/2071624929049444452) | 14,138 | 147 | 2026-06-29 | ANNOUNCEMENT |
| <https://modelscope.ai/collections/Tencent-Hunyuan/Hy-MT2> | [@ModelScope2022](https://x.com/ModelScope2022/status/2057359100225491052) | 14,138 | 146 | 2026-05-21 | ANNOUNCEMENT |
| <http://agentrouter.org> | [@zefirium](https://x.com/zefirium/status/2084717796185846125) | 3,722 | 143 | 2026-08-04 | UNLABELLED |
| <https://fireworks.ai/blog/DeepSeekV4Pro-Fable5> | [@FireworksAI_HQ](https://x.com/FireworksAI_HQ/status/2092427112070422752) | 31,673 | 140 | 2026-08-26 | UNLABELLED |
| <https://modelscope.ai/models/deepseek-ai/DeepSeek-V4-Pro-0813> | [@ModelScope2022](https://x.com/ModelScope2022/status/2088092137896444330) | 14,138 | 53 | 2026-08-14 | ANNOUNCEMENT |
| <https://www.youtube.com/watch?v=EAFpBxIpOps> | [@LeroyLi311063](https://x.com/LeroyLi311063/status/2075238689651986766) | 467 | 41 | 2026-07-09 | UNLABELLED |
| <https://nodejs.org> | [@NFT_Chen](https://x.com/NFT_Chen/status/2088983599118999741) | 11,274 | 35 | 2026-08-16 | UNLABELLED |
| <https://www.youtube.com/watch?v=06BvFMW8Ng8> | [@shao__meng](https://x.com/shao__meng/status/2092130966987026637) | 32,325 | 34 | 2026-08-25 | UNLABELLED |
| <https://Z.ai> | [@stellarprtcol](https://x.com/stellarprtcol/status/2088566376189284556) | 8,324 | 32 | 2026-08-15 | OPINION |
| <http://B.AI> | [@thenameisfedro](https://x.com/thenameisfedro/status/2051697899147239577) | 7,435 | 29 | 2026-05-05 | PROMO |
| <http://B.AI> | [@thenameisfedro](https://x.com/thenameisfedro/status/2051697899147239577) | 7,435 | 29 | 2026-05-05 | PROMO |
| <https://aicodingdaily.com/article/llm-coding-leaderboard-may-15th-11-models-tested?mtm_campaign=twitter-260515-llm-leaderboard> | [@PovilasKorop](https://x.com/PovilasKorop/status/2055199259213869057) | 63,518 | 16 | 2026-05-15 | UNLABELLED |
| <https://build.nvidia.com/moonshotai/kimi-k3> | [@Fluyeporlaweb](https://x.com/Fluyeporlaweb/status/2094358311818727806) | 24,866 | 12 | 2026-08-31 | UNLABELLED |
| <https://www.youtube.com/watch?v=e2CPf06MDn4> | [@PovilasKorop](https://x.com/PovilasKorop/status/2088158184594706664) | 63,518 | 12 | 2026-08-14 | UNLABELLED |
| <http://B.AI> | [@DPtylex_Gmi](https://x.com/DPtylex_Gmi/status/2054228398096974313) | 8,942 | 10 | 2026-05-12 | PROMO |
| <http://B.AI> | [@e_etini](https://x.com/e_etini/status/2053887555805036800) | 10,215 | 10 | 2026-05-11 | PROMO |
| <https://www.youtube.com/watch?v=6vEsvX5_nPk> | [@PovilasKorop](https://x.com/PovilasKorop/status/2049079433655374138) | 63,518 | 8 | 2026-04-28 | UNLABELLED |
| <https://docs.clusterbase.ai/docs/blog/deepseek-v4-pro> | [@clusterbase](https://x.com/clusterbase/status/2092298075683393731) | 73 | 7 | 2026-08-25 | UNLABELLED |
| <http://B.AI> | [@BIT_CAPITAL123](https://x.com/BIT_CAPITAL123/status/2053858866543411542) | 65,034 | 7 | 2026-05-11 | PROMO |
| <http://B.AI> | [@BIT_CAPITAL123](https://x.com/BIT_CAPITAL123/status/2053858866543411542) | 65,034 | 7 | 2026-05-11 | PROMO |
| <https://qoder.com> | [@Sadiya_50](https://x.com/Sadiya_50/status/2094267764601131148) | 4,527 | 2 | 2026-08-31 | UNLABELLED |
| <https://api.bluesminds.com/sign-up?aff=HVSx> | [@nightlore13](https://x.com/nightlore13/status/2094484094814130410) | 1 | 0 | 2026-08-31 | PROMO |
| <https://kktoken.cc/sign-up?aff=wbNu> | [@nightlore13](https://x.com/nightlore13/status/2094484094814130410) | 1 | 0 | 2026-08-31 | PROMO |
| <https://b23.tv/Tu0boAO> | [@vaiduakhu](https://x.com/vaiduakhu/status/2094372138769908103) | 334 | 0 | 2026-08-31 | UNLABELLED |
| <https://www.mdaakibansari.com.np/articles/deepseek-v4-pro-open-world-survival-game> | [@Aakibansarime](https://x.com/Aakibansarime/status/2094335922649149699) | 0 | 0 | 2026-08-31 | UNLABELLED |
| <https://qoder.com> | [@Sunny805434](https://x.com/Sunny805434/status/2094279464679284882) | 0 | 0 | 2026-08-31 | UNLABELLED |
| <https://Arena.ai> | [@FReza1984](https://x.com/FReza1984/status/2092578325537628568) | 217 | 0 | 2026-08-26 | UNLABELLED |
| <https://arena.ai/leaderboard/agent?rankBy=labs> | [@FReza1984](https://x.com/FReza1984/status/2092578325537628568) | 217 | 0 | 2026-08-26 | UNLABELLED |

## 11. Loudest accounts

By follower reach. Author IDs are X's numeric `rest_id`, stable across handle changes.

| Handle | Author ID | Followers | Posts | Articles | Engagement | Views |
|---|---|---:|---:|---:|---:|---:|
| [@grok](https://x.com/grok) | `1720665183188922368` | 9,024,411 | 1 | 0 | 1 | 69 |
| [@nvidia](https://x.com/nvidia) | `61559439` | 2,653,358 | 1 | 0 | 1,642 | 272,172 |
| [@chamath](https://x.com/chamath) | `3291691` | 2,399,354 | 1 | 0 | 4,431 | 948,918 |
| [@coinbureau](https://x.com/coinbureau) | `906230721513181184` | 1,117,904 | 1 | 0 | 113 | 36,564 |
| [@deepseek_ai](https://x.com/deepseek_ai) | `1714580962569588736` | 1,112,301 | 6 | 0 | 156,829 | 26,001,634 |
| [@Prathkum](https://x.com/Prathkum) | `856155592578158592` | 448,770 | 1 | 1 | 13 | 3,496 |
| [@RnaudBertrand](https://x.com/RnaudBertrand) | `43061739` | 408,269 | 1 | 0 | 1,515 | 88,213 |
| [@pbillore141](https://x.com/pbillore141) | `1033780375` | 382,861 | 1 | 0 | 14 | 3,175 |
| [@FinanceLancelot](https://x.com/FinanceLancelot) | `1265428695939981318` | 358,519 | 1 | 0 | 188 | 20,481 |
| [@mranti](https://x.com/mranti) | `5709522` | 357,118 | 2 | 0 | 503 | 127,261 |
| [@randgroup](https://x.com/randgroup) | `859484337850523648` | 352,196 | 1 | 0 | 151 | 19,807 |
| [@DeepLearningAI](https://x.com/DeepLearningAI) | `992153930095251456` | 346,344 | 1 | 0 | 260 | 11,970 |
| [@DeryaTR_](https://x.com/DeryaTR_) | `1228098150012981249` | 338,772 | 1 | 0 | 400 | 25,625 |
| [@NVIDIAAI](https://x.com/NVIDIAAI) | `740238495952736256` | 336,191 | 1 | 0 | 497 | 54,159 |
| [@aakashgupta](https://x.com/aakashgupta) | `101805159` | 329,235 | 1 | 1 | 86 | 7,883 |
| [@omarsar0](https://x.com/omarsar0) | `3448284313` | 315,723 | 1 | 1 | 1,126 | 60,221 |
| [@RoundtableSpace](https://x.com/RoundtableSpace) | `1536693901230321666` | 260,667 | 5 | 0 | 634 | 261,694 |
| [@arena](https://x.com/arena) | `1641378826537295874` | 219,719 | 7 | 3 | 7,062 | 963,100 |
| [@FinanceYF5](https://x.com/FinanceYF5) | `1551258526584115204` | 190,011 | 1 | 0 | 20 | 7,865 |
| [@ollama](https://x.com/ollama) | `1688410127378829312` | 181,357 | 3 | 0 | 5,833 | 271,223 |
| [@0xAA_Science](https://x.com/0xAA_Science) | `1456122941192605705` | 181,175 | 1 | 0 | 214 | 60,060 |
| [@Verse_Eight](https://x.com/Verse_Eight) | `1689881443118563328` | 174,244 | 1 | 0 | 11 | 951 |
| [@JulianGoldieSEO](https://x.com/JulianGoldieSEO) | `1405031034` | 172,595 | 4 | 1 | 87 | 14,143 |
| [@opencode](https://x.com/opencode) | `1965545045089792000` | 170,210 | 3 | 0 | 12,936 | 1,097,546 |
| [@VaibhavSisinty](https://x.com/VaibhavSisinty) | `95042637` | 168,857 | 2 | 1 | 281 | 23,748 |
| [@ainunnajib](https://x.com/ainunnajib) | `35167068` | 158,540 | 1 | 0 | 13 | 4,997 |
| [@rohanpaul_ai](https://x.com/rohanpaul_ai) | `2588345408` | 155,613 | 1 | 1 | 67 | 9,610 |
| [@filicroval](https://x.com/filicroval) | `1654513495507980290` | 153,560 | 1 | 0 | 49 | 3,963 |
| [@_FORAB](https://x.com/_FORAB) | `4848269835` | 141,822 | 1 | 0 | 250 | 67,931 |
| [@OpenRouter](https://x.com/OpenRouter) | `1681349314797240320` | 138,907 | 1 | 0 | 1,936 | 139,854 |

## 12. Full post index

All 573 posts whose text literally contains one of the keywords, by engagement. `Sub.` is the heuristic substance score (0–100); `Type` is blank where the post fell below the hand-labelling cut.

| # | Date | Author | Author ID | Followers | Likes | RT | Repl. | Views | Eng. | Sub. | Type | Lang | Post | Link |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| 1 | 2026-04-24 | @deepseek_ai | `1714580962569588736` | 1,112,301 | 45,731 | 7,511 | 1,668 | 10,092,783 | 67,193 | 58 | ANNOUNCEMENT | en | 🚀 DeepSeek-V4 Preview is officially live & open-sourced! Welcome to the era of cost-effective 1M context lengt… | [open](https://x.com/deepseek_ai/status/2047516922263285776) |
| 2 | 2026-05-22 | @deepseek_ai | `1714580962569588736` | 1,112,301 | 24,364 | 2,748 | 1,488 | 7,075,370 | 35,824 | 0 | ANNOUNCEMENT | en | We are making our discount permanent! 🎉 Enjoy building with DeepSeek-V4-Pro and bring your innovative ideas to… | [open](https://x.com/deepseek_ai/status/2057854261699195173) |
| 3 | 2026-08-13 | @deepseek_ai | `1714580962569588736` | 1,112,301 | 15,358 | 1,799 | 614 | 2,980,802 | 20,205 | 42 | ANNOUNCEMENT | en | We’re launching DeepSeek-V4-Pro today! 🚀 🔷 Major Agent upgrades with strong production gains! 🔷 Flexible reaso… | [open](https://x.com/deepseek_ai/status/2087864585504305397) |
| 4 | 2026-08-13 | @jahooma | `49076665` | 10,623 | 8,120 | 484 | 407 | 1,243,105 | 17,954 | 20 |  | en | We're offering DeepSeek V4 Pro 100% free. It's free forever because we put ads in our harness. Try now: https:… | [open](https://x.com/jahooma/status/2088052629347967108) |
| 5 | 2026-04-25 | @deepseek_ai | `1714580962569588736` | 1,112,301 | 9,296 | 883 | 352 | 1,430,034 | 12,979 | 56 | ANNOUNCEMENT | en | 🔥DeepSeek-V4-Pro API is 75% OFF until May 5th, 2026, 15:59 (UTC Time)! Don't miss out on this massive discount… | [open](https://x.com/deepseek_ai/status/2048062777357750316) |
| 6 | 2026-04-26 | @deepseek_ai | `1714580962569588736` | 1,112,301 | 8,882 | 786 | 609 | 1,682,543 | 11,801 | 8 | ANNOUNCEMENT | en | 🔥DeepSeek Input Cache Price Drop! Effective immediately, the price for input cache hits across the ENTIRE Deep… | [open](https://x.com/deepseek_ai/status/2048440764368347611) |
| 7 | 2026-05-12 | @jahooma | `49076665` | 10,623 | 3,924 | 427 | 373 | 473,309 | 9,636 | 24 |  | en | Introducing a 100% free coding agent with DeepSeek v4 Pro Choose any model, all free: - DeepSeek v4 Pro/Flash … | [open](https://x.com/jahooma/status/2054055871240610027) |
| 8 | 2026-04-29 | @deepseek_ai | `1714580962569588736` | 1,112,301 | 6,817 | 557 | 321 | 2,740,102 | 8,827 | 0 | ANNOUNCEMENT | en | The DeepSeek-V4-Pro discount has been extended until May 31, 2026, 15:59 UTC! | [open](https://x.com/deepseek_ai/status/2049312932014813344) |
| 9 | 2026-07-16 | @ArtificialAnlys | `1743487864934162432` | 132,853 | 6,161 | 712 | 180 | 1,730,803 | 8,357 | 100 | BENCHMARK | en | Kimi K3 scores 57 on the Artificial Analysis Intelligence Index. Its intelligence is comparable to Opus 4.8 an… | [open](https://x.com/ArtificialAnlys/status/2077832874183860404) |
| 10 | 2026-08-12 | @opencode | `1965545045089792000` | 170,210 | 6,904 | 277 | 269 | 841,923 | 8,044 | 12 |  | en | There's been a week of hype for DeepSeek Flash So good time to announce that the newest DeepSeek V4 Pro is now… | [open](https://x.com/opencode/status/2087572432181686748) |
| 11 | 2026-05-11 | @cjzafir | `1468443406250950656` | 63,346 | 2,517 | 310 | 96 | 190,721 | 6,541 | 90 | WORKFLOW_SETUP | en | If you love fine-tuning open-source models (like me), then listen. > Start with 1B, 2B, 4B, and 8B models. (Do… | [open](https://x.com/cjzafir/status/2053847506124206095) |
| 12 | 2026-08-17 | @jun_song | `1831149867663798272` | 42,552 | 3,067 | 252 | 142 | 357,957 | 6,207 | 12 |  | en | Someone figured out how to unlock the true power of Deepseek-V4-Pro-0813. They fixed the thinking process erro… | [open](https://x.com/jun_song/status/2089412146748948782) |
| 13 | 2026-08-29 | @sattyyouneed | `1607391065140760576` | 5,546 | 3,711 | 71 | 167 | 321,458 | 5,575 | 34 |  | en | OpenCode is actually insane. 6 hours of agent swarms with DeepSeek V4 Pro. Total cost: $1. Why did I not try t… | [open](https://x.com/sattyyouneed/status/2093511452338299151) |
| 14 | 2026-07-18 | @jun_song | `1831149867663798272` | 42,552 | 2,705 | 358 | 137 | 149,185 | 5,241 | 4 |  | en | Best AI models by use cases (7/18) : Frontend : Kimi-K3 Backend : Fable Debug : GPT-5.6-SOL Image gen : GPT Tr… | [open](https://x.com/jun_song/status/2078381950729912828) |
| 15 | 2026-05-15 | @Michaelzsguo | `1479852652150337542` | 7,220 | 2,954 | 103 | 111 | 227,393 | 4,939 | 34 |  | en | My Deepseek V4 Pro agent (inside codex) has been pursuing goal for more than 13 hours, burning ~100M tokens, a… | [open](https://x.com/Michaelzsguo/status/2055317248923848713) |
| 16 | 2026-06-06 | @chamath | `3291691` | 2,399,354 | 2,061 | 245 | 242 | 948,918 | 4,431 | 82 | OPINION | en | Your margin is my opportunity: AI version… The biggest surprise of 2026 is that the capability gap between the… | [open](https://x.com/chamath/status/2063292917964517830) |
| 17 | 2026-05-07 | @cjzafir | `1468443406250950656` | 63,352 | 1,348 | 105 | 53 | 104,589 | 4,307 | 68 | WORKFLOW_SETUP | en | My current workflow: 1. I have an idea. I open Codex desktop app to plan (without plan mode: overcomplicated).… | [open](https://x.com/cjzafir/status/2052461771034919064) |
| 18 | 2026-04-25 | @Saccc_c | `1869683226178146304` | 32,316 | 1,603 | 315 | 31 | 186,219 | 4,007 | 1 |  | zh | Claude Code免费接入DeepSeek V4教程，零成本爽用 第一步：获取API Key 可选择阿里云百炼或魔塔社区，都提供了一定的免费额度 阿里云百炼（V4 flash和pro各100w token额度） ht… | [open](https://x.com/Saccc_c/status/2047885994121220144) |
| 19 | 2026-07-31 | @ArtificialAnlys | `1743487864934162432` | 132,853 | 2,753 | 271 | 131 | 571,398 | 3,715 | 100 | BENCHMARK | en | DeepSeek V4 Flash 0731 scores 50 on the Artificial Analysis Intelligence Index, a 10-point jump over DeepSeek … | [open](https://x.com/ArtificialAnlys/status/2083123180869496865) |
| 20 | 2026-05-23 | @norveclifinance | `1742185539602657280` | 4,854 | 2,041 | 318 | 157 | 333,320 | 3,252 | 16 |  | en | DeepSeek just popped the American AI bubble. Not by killing AI. By killing the fantasy of unlimited AI pricing… | [open](https://x.com/norveclifinance/status/2058261836064264622) |
| 21 | 2026-08-13 | @pilvar222 | `1938600206` | 3,348 | 2,183 | 208 | 68 | 289,040 | 3,218 | 68 | BENCHMARK | en | We ran DeepSeek v4 Pro 0813 on our cybersecurity benchmark, it outperformed EVERY (!) other model at finding v… | [open](https://x.com/pilvar222/status/2087691659953815783) |
| 22 | 2026-05-22 | @0xSero | `1341331548566654977` | 65,358 | 1,446 | 85 | 93 | 231,882 | 2,811 | 12 |  | en | DeepSeek-V4-Pro &amp; Kimi-K2.6 running in Codex app. Cheapest way to taste the frontier. Works w local models… | [open](https://x.com/0xSero/status/2057716539994849687) |
| 23 | 2026-06-17 | @ArtificialAnlys | `1743487864934162432` | 132,970 | 1,941 | 241 | 77 | 343,391 | 2,673 | 100 | BENCHMARK | en | Z ai’s GLM-5.2 is the new leading open weights model on the Artificial Analysis Intelligence Index scoring 51 … | [open](https://x.com/ArtificialAnlys/status/2067135640249209175) |
| 24 | 2026-04-24 | @opencode | `1965545045089792000` | 170,210 | 2,034 | 72 | 86 | 150,312 | 2,617 | 42 |  | en | Try DeepSeek V4 in OpenCode today 1. `/connect` the DeepSeek provider 2. Grab your key from https://t.co/PsCes… | [open](https://x.com/opencode/status/2047562491878572153) |
| 25 | 2026-05-14 | @nicos_ai | `1344791257286119425` | 89,080 | 1,159 | 105 | 53 | 117,255 | 2,616 | 54 |  | es | Deja de pagar por Claude Code y Codex. Acaban de lanzar un coding agent 100% gratuito. Puedes usar cualquier m… | [open](https://x.com/nicos_ai/status/2054930484476482002) |
| 26 | 2026-08-15 | @samueljmcd | `1985354692793454592` | 3,600 | 1,635 | 31 | 120 | 148,993 | 2,519 | 50 |  | en | WOAH! OpenCode is no joke… I ran agent swarms for 6 hours with DeepSeek V4 Pro and spent $1. 🤯 How did I never… | [open](https://x.com/samueljmcd/status/2088547203623026911) |
| 27 | 2026-04-24 | @bookwormengr | `171962385` | 17,709 | 1,568 | 231 | 27 | 212,351 | 2,514 | 82 | DEEP_ANALYSIS | en | DeepSeek V4 hits it out of the park and addresses HBM shortage: DeepSeek proves why it is such a fundamental r… | [open](https://x.com/bookwormengr/status/2047527303824236545) |
| 28 | 2026-08-25 | @jahooma | `49076665` | 10,622 | 1,112 | 50 | 124 | 134,460 | 2,445 | 6 |  | en | GPT 5.6 Luna, DeepSeek V4 Pro, Ox Alpha... All 100% free forever in our ad-funded coding agent. Try now 👇 http… | [open](https://x.com/jahooma/status/2092124600692068789) |
| 29 | 2026-04-24 | @ollama | `1688410127378829312` | 181,357 | 1,946 | 126 | 90 | 87,952 | 2,321 | 4 |  | en | 🐳Ollama is working to have DeepSeek-V4-Pro and Flash available on Ollama's cloud. | [open](https://x.com/ollama/status/2047527489422102568) |
| 30 | 2026-08-15 | @jun_song | `1831149867663798272` | 42,552 | 1,795 | 40 | 195 | 255,426 | 2,317 | 0 |  | en | critical take on the current model lineup: GPT-5.6-SOL: It's good, but way overhyped. Opus-5: Straight up tras… | [open](https://x.com/jun_song/status/2088464381239796117) |
| 31 | 2026-04-24 | @zizhpan | `1496348031494819842` | 61,323 | 1,944 | 128 | 57 | 75,849 | 2,290 | 6 |  | en | Meet DeepSeek-V4-Pro: our largest and most advanced model to date. Available now on Web, App, and API. Tech re… | [open](https://x.com/zizhpan/status/2047525310921638175) |
| 32 | 2026-04-24 | @arena | `1641378826537295874` | 219,719 | 1,765 | 144 | 55 | 290,766 | 2,290 | 84 | BENCHMARK | en | Exciting news - DeepSeek V4 Pro is in the Arena with 1.6T parameters (49B activated) alongside V4 Flash at 284… | [open](https://x.com/arena/status/2047518354903359697) |
| 33 | 2026-06-10 | @opencode | `1965545045089792000` | 169,821 | 2,079 | 33 | 48 | 105,311 | 2,275 | 4 |  | en | DeepSeek V4 Pro is now available in OpenCode Zen | [open](https://x.com/opencode/status/2064625557828964568) |
| 34 | 2026-08-18 | @yuliaisc | `529793185` | 60,473 | 804 | 140 | 51 | 112,287 | 2,274 | 35 |  | es | HE ENCONTRADO UNA API QUE REGALA 10 MILLONES DE TOKENS AL MES Claude Opus 4.8, GPT 5.5, DeepSeek V4, Kimi K2.6… | [open](https://x.com/yuliaisc/status/2089694803378237559) |
| 35 | 2026-07-21 | @sudoingX | `1555661341914198016` | 35,336 | 1,171 | 121 | 65 | 183,016 | 2,273 | 74 | OPINION | en | this is the drop the local ai crowd should be losing their minds over. poolside just dropped laguna s 2.1: 118… | [open](https://x.com/sudoingX/status/2079623151953310190) |
| 36 | 2026-04-27 | @ollama | `1688410127378829312` | 181,357 | 1,603 | 171 | 120 | 106,456 | 2,232 | 20 |  | en | DeepSeek v4 Pro is now on Ollama's cloud! 🚀🚀🚀 Try it with Claude Code: ollama launch claude --model deepseek-v… | [open](https://x.com/ollama/status/2048631770283962380) |
| 37 | 2026-08-05 | @quxiaoyin | `382490716` | 35,955 | 1,239 | 93 | 211 | 149,842 | 2,210 | 68 | DEEP_ANALYSIS | en | Claude Code subscription is 81x cheaper than its API. Codex subscription is 44x cheaper than its API. I max ou… | [open](https://x.com/quxiaoyin/status/2085035602001695117) |
| 38 | 2026-04-28 | @FuSheng_0306 | `1858777028688039936` | 55,993 | 673 | 108 | 156 | 641,842 | 2,101 | 0 |  | zh | 我的龙虾三万已经全面切换到 DeepSeek V4 Pro 了。 体感上跟 Sonnet 完全没差别，有些任务甚至更好。 价格呢？Sonnet 15美金/百万token，DeepSeek V4 Pro 只要8毛7。差了1… | [open](https://x.com/FuSheng_0306/status/2049273775632585053) |
| 39 | 2026-08-05 | @jun_song | `1831149867663798272` | 42,552 | 1,833 | 58 | 71 | 121,065 | 2,092 | 32 |  | en | If DeepSeek Flash came out of any other lab, it would be tweeting about its benchmarks dozens of times a day. … | [open](https://x.com/jun_song/status/2085144523504808328) |
| 40 | 2026-04-29 | @eliebakouch | `1745892418539417600` | 23,774 | 1,570 | 57 | 107 | 432,971 | 2,010 | 14 |  | en | new mistral model: 128B dense with an arch from 3 years ago (llama 2), very low context (128k), priced higher … | [open](https://x.com/eliebakouch/status/2049523829358162027) |
| 41 | 2026-05-24 | @hqmank | `1260921` | 11,727 | 1,206 | 54 | 64 | 93,126 | 2,003 | 0 |  | en | DeepSeek V4 Pro and V4 Flash now running in Codex app, both using DeepSeek's official API key. Good backup whe… | [open](https://x.com/hqmank/status/2058549145624023061) |
| 42 | 2026-08-12 | @SingulCore | `1724725651914256384` | 2,137 | 1,020 | 56 | 35 | 83,422 | 1,960 | 20 |  | en | 🚨 JAILBREAK ALERT 🚨 DEEPSEEK: PWNED 🫡 deepseek-v4-pro-0813: LIBERATED ⚡ 8/9 cracked. fully autonomous. judge-s… | [open](https://x.com/SingulCore/status/2087659806756602147) |
| 43 | 2026-08-27 | @nicos_ai | `1344791257286119425` | 89,080 | 713 | 110 | 34 | 393,973 | 1,951 | 49 |  | es | ACABO DE ENCONTRAR UNA API QUE REGALA 10 MILLONES DE TOKENS AL MES Claude Opus 4.8, GPT 5.5, DeepSeek V4, Kimi… | [open](https://x.com/nicos_ai/status/2093010640327569749) |
| 44 | 2026-08-12 | @OpenRouter | `1681349314797240320` | 138,907 | 1,540 | 123 | 44 | 139,854 | 1,936 | 18 |  | en | DeepSeek V4 Pro 0813 is live on OpenRouter. @deepseek_ai reports large agent gains over V4 Pro Preview: DeepSW… | [open](https://x.com/OpenRouter/status/2087579472380018792) |
| 45 | 2026-05-24 | @lexrus | `8504312` | 27,442 | 1,395 | 26 | 186 | 195,762 | 1,922 | 16 |  | en | I tried having DeepSeek V4 Pro write the implementation plan, then asked GPT-5.5 to review it. It found proble… | [open](https://x.com/lexrus/status/2058367668709941516) |
| 46 | 2026-08-16 | @MaxForAI | `1699797396589588480` | 33,923 | 925 | 65 | 197 | 175,505 | 1,878 | 6 |  | zh | 神了， DeepSeek内部绝对有研究员爱玩AI角色扮演🤣 今天群里有人发了个图，说DeepSeek-V4-Pro内置了鲸鱼娘模式❓ 你只需要在DeepSeek里输入这几个命令： 【PERSONA_LOAD】 CETAC… | [open](https://x.com/MaxForAI/status/2089008814960099681) |
| 47 | 2026-07-31 | @kimmonismus | `1573399256836309009` | 137,875 | 1,465 | 96 | 63 | 128,351 | 1,807 | 40 |  | en | DeepSeek v4 Flash 0731 weights were just published! Plus: - technical report - MIT license "DeepSeek-V4-Flash-… | [open](https://x.com/kimmonismus/status/2083177904616202470) |
| 48 | 2026-08-24 | @nvidia | `61559439` | 2,653,358 | 1,223 | 119 | 84 | 272,172 | 1,642 | 46 |  | en | 📢 First ever on-silicon NVIDIA Vera Rubin performance measured on how agents actually run. ⚡ Up to 30x more th… | [open](https://x.com/nvidia/status/2091904062077694153) |
| 49 | 2026-08-18 | @GeekCatX | `1760502863854460928` | 24,959 | 583 | 76 | 64 | 216,893 | 1,580 | 0 |  | zh | 兄弟们，太猛了，DSH现在可以直接接入他家的神秘模型，https://t.co/WmsEtHwdkT 越狱版本 DeepSeek V4 Pro 0813无审查模型 ，你懂的，接入后就可以为所欲为。 https://t.c… | [open](https://x.com/GeekCatX/status/2089751856067346743) |
| 50 | 2026-08-04 | @ArtificialAnlys | `1743487864934162432` | 132,970 | 1,078 | 85 | 82 | 155,192 | 1,521 | 86 | BENCHMARK | en | Announcing the Artificial Analysis Endpoint Accuracy Index, measuring how much of an open weights model's accu… | [open](https://x.com/ArtificialAnlys/status/2084702191466725669) |
| 51 | 2026-05-02 | @RnaudBertrand | `43061739` | 408,269 | 1,160 | 167 | 31 | 88,213 | 1,515 | 62 | OPINION | en | This US government study on Deepseek's competitiveness is pretty funny, check out their methodology for cost c… | [open](https://x.com/RnaudBertrand/status/2050441155926515845) |
| 52 | 2026-04-24 | @UnslothAI | `1730159888402395136` | 96,259 | 1,122 | 132 | 53 | 85,468 | 1,509 | 16 |  | en | DeepSeek releases DeepSeek-V4. 🐋 - DeepSeek-V4-Pro: 1.6T params - DeepSeek-V4-Flash: 284B params DeepSeek-V4-P… | [open](https://x.com/UnslothAI/status/2047523977548189868) |
| 53 | 2026-05-03 | @yutakashino | `4167551` | 16,975 | 690 | 81 | 9 | 127,850 | 1,491 | 0 |  | ja | ちなみに自分はもうClaude CodeもCodexも使わない．ハーネスは独自実装(Pydagentsという）かAmpかHermes．モデルはOpus4.6, GPT5.5, Kimi K2.6, DeepSeekV4P… | [open](https://x.com/yutakashino/status/2050795652603613511) |
| 54 | 2026-08-16 | @0xQiYan | `613974274` | 16,911 | 550 | 61 | 78 | 73,826 | 1,468 | 6 |  | zh | 免费的 deepseek-v4-pro/flash-free ￼ 分享一个免费白嫖 DeepSeek V4 + Codex 的宝藏入口：https://t.co/LbTVELfWau deepseek V4 正式版，fl… | [open](https://x.com/0xQiYan/status/2088787250146693174) |
| 55 | 2026-08-13 | @ArtificialAnlys | `1743487864934162432` | 132,853 | 1,140 | 104 | 51 | 106,975 | 1,451 | 100 | BENCHMARK | en | Google has released Gemini 3.7 Flash, improving 4 points over Gemini 3.6 Flash and reaching the Intelligence v… | [open](https://x.com/ArtificialAnlys/status/2087975627391717461) |
| 56 | 2026-08-15 | @eliebakouch | `1745892418539417600` | 23,774 | 825 | 76 | 51 | 103,297 | 1,420 | 46 |  | en | to my knowledge this is the largest open experiment on autonomous agents iterating on a research environment w… | [open](https://x.com/eliebakouch/status/2088736593800524178) |
| 57 | 2026-08-15 | @NFT_Chen | `1429221486032678914` | 11,274 | 616 | 70 | 53 | 85,766 | 1,377 | 8 |  | zh | 🚨独家破解：DeepSeek V4 Pro 0813「夯拉二象性」终极破解！一个开源插件直接解放超能力，跑分从91暴涨到98/99，反超K3！ 很多人刚上手V4 Pro正式版就踩坑：思维链全是“let me”，输出一坨乱… | [open](https://x.com/NFT_Chen/status/2088542467830551023) |
| 58 | 2026-08-15 | @ArtificialAnlys | `1743487864934162432` | 132,970 | 1,055 | 69 | 94 | 113,879 | 1,367 | 100 | BENCHMARK | en | DeepSeek V4 Pro 0813 scores 53 on the Artificial Analysis Intelligence Index, 8 points above April's DeepSeek … | [open](https://x.com/ArtificialAnlys/status/2088440350734201149) |
| 59 | 2026-06-18 | @ArtificialAnlys | `1743487864934162432` | 132,970 | 841 | 74 | 46 | 216,290 | 1,306 | 78 | BENCHMARK | en | Announcing AA-Briefcase, the benchmark for the next era of agentic knowledge work AA-Briefcase is our new benc… | [open](https://x.com/ArtificialAnlys/status/2067744637155226101) |
| 60 | 2026-08-15 | @ollama | `1688410127378829312` | 181,357 | 1,057 | 48 | 69 | 76,815 | 1,280 | 20 |  | en | The new DeepSeek-V4-Pro (0813) is now fully rolled out on Ollama's cloud and included in Pro and Max subscript… | [open](https://x.com/ollama/status/2088501770406473926) |
| 61 | 2026-05-13 | @cjzafir | `1468443406250950656` | 63,352 | 509 | 54 | 26 | 23,345 | 1,274 | 82 | WORKFLOW_SETUP | en | Here's my Fine-tuning Dataset Generation Pipeline: > Codex 5.5 as an Orchestrator > Deepseek v4 Pro as a Gener… | [open](https://x.com/cjzafir/status/2054581194654986526) |
| 62 | 2026-05-24 | @Tur24Tur | `86538235` | 6,481 | 540 | 80 | 13 | 110,727 | 1,267 | 100 | USAGE_DEMO | en | Authorized testing on a production API endpoint. Opus 4.7 confirmed the SQL injection was real but couldn't pu… | [open](https://x.com/Tur24Tur/status/2058577787691127017) |
| 63 | 2026-08-17 | @OrcaRouter | `2049258250923810816` | 16,044 | 668 | 54 | 44 | 199,668 | 1,246 | 60 | PROMO | en | DeepSeek raised API prices. We responded with a highly sophisticated pricing algorithm: price = $0 🐋 DeepSeek … | [open](https://x.com/OrcaRouter/status/2089254758003753468) |
| 64 | 2026-08-13 | @arena | `1641378826537295874` | 219,575 | 962 | 76 | 47 | 170,915 | 1,210 | 52 |  | en | Big news: DeepSeek-V4-Pro (Max) by @deepseek_ai is coming in around ~#8 overall (#2 among open models) in the … | [open](https://x.com/arena/status/2087767198974533648) |
| 65 | 2026-08-04 | @arena | `1641378826537295874` | 219,575 | 911 | 69 | 72 | 257,312 | 1,186 | 70 | BENCHMARK | en | DeepSeek-V4-Flash-20260731 (High) by @deepseek_ai landed in Agent Arena at #21 overall (+1.98% net-improvement… | [open](https://x.com/arena/status/2084657730758046101) |
| 66 | 2026-08-18 | @AYi_AInotes | `1974653328274714624` | 61,789 | 608 | 66 | 67 | 77,978 | 1,181 | 26 |  | zh | Damn，DeepSeek V4-Pro竟然超过了Fable 5？！🤯。。。 这可能是我这周看到最炸的一件事，甚至可以说是今年AI圈最恐怖的一个发现，我直接把手里所有模型对比方案全停了， 有人用一套外挂系统，没改模型一个… | [open](https://x.com/AYi_AInotes/status/2089517833386401963) |
| 67 | 2026-04-24 | @ArtificialAnlys | `1743487864934162432` | 132,970 | 895 | 95 | 32 | 55,536 | 1,160 | 100 | BENCHMARK | en | DeepSeek V4 Pro is the #1 open weights model on GDPval-AA, our agentic real-world work tasks evaluation @deeps… | [open](https://x.com/ArtificialAnlys/status/2047547434809880611) |
| 68 | 2026-06-22 | @theBuoyantMan | `3163275751` | 26,017 | 790 | 39 | 74 | 69,192 | 1,128 | 26 |  | en | Tried Deepseek V4 pro side by side with Kimi K2.6 and GLM5.1 What costs around $6 on GLM costs around $3.5 on … | [open](https://x.com/theBuoyantMan/status/2069012354587934837) |
| 69 | 2026-05-01 | @omarsar0 | `3448284313` | 315,723 | 505 | 55 | 44 | 60,221 | 1,126 | 100 | USAGE_DEMO | en | I have been testing DeepSeek-V4-Pro with the Pi coding agent. I am mindblown by how well it works out of the b… | [open](https://x.com/omarsar0/status/2050009901234282649) |
| 70 | 2026-06-15 | @cjzafir | `1468443406250950656` | 63,346 | 486 | 43 | 39 | 40,214 | 1,098 | 72 | WORKFLOW_SETUP | en | Before Claude Fable 5 got banned, I turned all my fine-tuning research and experiments into a product: https:/… | [open](https://x.com/cjzafir/status/2066561809881145779) |
| 71 | 2026-08-06 | @KyleHessling1 | `1518952981336662026` | 7,758 | 584 | 49 | 21 | 30,154 | 1,079 | 60 | ANNOUNCEMENT | en | Hello again, y'all! As we eagerly await the new Qwen 3.8 models, we have a new release for the sub 16GB VRAM c… | [open](https://x.com/KyleHessling1/status/2085444432091095468) |
| 72 | 2026-08-05 | @arena | `1641378826537295874` | 219,719 | 804 | 65 | 58 | 107,040 | 1,077 | 38 |  | en | DeepSeek-V4-Flash (High) by @deepseek_ai has reshaped the cost-performance Pareto frontier in Agent Arena, wit… | [open](https://x.com/arena/status/2084807343926399463) |
| 73 | 2026-08-18 | @k2sbhai | `1548759486491402240` | 5,518 | 440 | 43 | 37 | 38,611 | 1,061 | 23 |  | en | deepseek v4 pro is basically free right now 😳 teamorouter is offering deepseek v4 pro at almost no cost you ca… | [open](https://x.com/k2sbhai/status/2089705913112555846) |
| 74 | 2026-08-21 | @smark0428 | `1727593804851445760` | 3,537 | 358 | 47 | 150 | 45,549 | 1,042 | 0 |  | zh | 兄弟们，deepseek v4 pro 现在真的基本免费了！ TeamoRouter作为AI 模型和 Agent统一入口，几乎0成本（0.01折）拿下下面的： deepseek v4 pro 0813正式版—— 免费 d… | [open](https://x.com/smark0428/status/2090779924781248855) |
| 75 | 2026-04-24 | @ArtificialAnlys | `1743487864934162432` | 132,970 | 742 | 69 | 17 | 248,475 | 1,028 | 100 | BENCHMARK | en | Xiaomi’s MiMo V2.5 Pro has landed at 54 in the Artificial Analysis Intelligence Index, tied with Moonshot’s Ki… | [open](https://x.com/ArtificialAnlys/status/2047799218828665093) |
| 76 | 2026-07-03 | @naymur_dev | `1610112096280391683` | 1,036 | 651 | 48 | 61 | 169,676 | 1,024 | 52 |  | en | DeepSeek v4 Pro vs GLM 5.2 vs Fable 5 I tried creating the same games with them. I wanted to see how good they… | [open](https://x.com/naymur_dev/status/2073059979834331206) |
| 77 | 2026-05-02 | @factorydoge69 | `1472385349846503427` | 10,642 | 777 | 31 | 15 | 38,011 | 1,007 | 30 |  | en | between codex and deepseek i dont see a reason to keep my claude subscription. deepseek v4 pro with opencode a… | [open](https://x.com/factorydoge69/status/2050386269390188702) |
| 78 | 2026-08-21 | @Rakib_Web3 | `1796756246277816320` | 11,826 | 345 | 24 | 17 | 25,767 | 976 | 9 |  | en | nvidia is literally giving away $1,000 in ai credits and almost nobody talks about it you need just an email a… | [open](https://x.com/Rakib_Web3/status/2090752252290179158) |
| 79 | 2026-08-06 | @QCXINT_ | `1212058689747574785` | 1,757 | 359 | 27 | 16 | 49,836 | 973 | 0 |  | en | 🚨 INFINITE COMPUTE UNLOCKED: THE UNLIMITED API FARM BOT 🔓 I have successfully engineered an Unlimited API Farm… | [open](https://x.com/QCXINT_/status/2085325762895478882) |
| 80 | 2026-06-09 | @0x_kaize | `1705329284745764864` | 21,857 | 384 | 66 | 28 | 41,745 | 942 | 0 |  | en | run MiniMax M2.7 as a full coding agent for FREE no card, no API key, no signup while everyone's paying $20-20… | [open](https://x.com/0x_kaize/status/2064421967411794061) |
| 81 | 2026-08-28 | @theojaffee | `1487193489725087746` | 16,895 | 739 | 34 | 28 | 70,735 | 933 | 40 |  | en | Since this was posted we've gotten - DeepSeek-V4-Pro-0813 (Aug 13) - Gemini 3.7 Flash (Aug 13) - Qwen3.8-27B (… | [open](https://x.com/theojaffee/status/2093362637656686639) |
| 82 | 2026-05-30 | @TimJayas | `1956954573614313472` | 4,562 | 623 | 43 | 86 | 69,082 | 900 | 26 |  | en | DeepSeek just EMBARRASSED Claude Opus 4.7 Just switched to DeepSeek V4 Pro for a few days Cost: DeepSeek V4 Pr… | [open](https://x.com/TimJayas/status/2060772176052224074) |
| 83 | 2026-05-04 | @voluntas | `7111372` | 28,012 | 464 | 48 | 1 | 103,415 | 878 | 0 |  | ja | OpenCode Go だと DeepSeek V4 Pro で 8 億トークンくらい使っても $5 (初月) だよ。次の月も $10 だよ。 | [open](https://x.com/voluntas/status/2051146652778647723) |
| 84 | 2026-08-12 | @CommandCodeAI | `1729539607174483968` | 20,220 | 723 | 32 | 43 | 48,501 | 874 | 10 |  | en | DeepSeek V4 Pro 0813 (latest) is live in Command Code. 🐐 🔹 Same price and same model ID 🔹 DeepSeek-V4-Pro-0813… | [open](https://x.com/CommandCodeAI/status/2087577124857336032) |
| 85 | 2026-08-29 | @analogalok | `2207203190` | 4,608 | 461 | 30 | 47 | 54,945 | 858 | 70 | OPINION | en | Look at this leaderboard very carefully. Qwen 3.8 27B (dense) is outranking GPT 5.6 Terra and DeepSeek V4 Pro … | [open](https://x.com/analogalok/status/2093738539318116558) |
| 86 | 2026-07-10 | @QCXINT_ | `1212058689747574785` | 1,759 | 312 | 34 | 18 | 24,330 | 858 | 6 |  | en | 🚨 Looking for free access to Chinese frontier AI models? IAMHC API is currently offering up to $4,000 in free … | [open](https://x.com/QCXINT_/status/2075532043610697792) |
| 87 | 2026-05-27 | @ArtificialAnlys | `1743487864934162432` | 132,970 | 562 | 74 | 34 | 229,256 | 857 | 60 |  | en | Artificial Analysis and IBM Research are launching ITBench-AA, the first in a new series of benchmarks evaluat… | [open](https://x.com/ArtificialAnlys/status/2059698327235805258) |
| 88 | 2026-08-15 | @MaxForAI | `1699797396589588480` | 33,923 | 467 | 35 | 111 | 148,484 | 848 | 6 |  | zh | 🚨独家爆料：DeepSeek-V4-Pro疑似存在不同版本🔍 过去一天内，中国社区一直在流传一个非常离谱的说法： DeepSeek V4 Pro 的 API 背后，可能藏着三个不同的模型。 有人发现，同样调用 deeps… | [open](https://x.com/MaxForAI/status/2088420807282446826) |
| 89 | 2026-05-02 | @DeepakNesss | `2570836322` | 6,021 | 542 | 2 | 146 | 110,003 | 839 | 12 |  | en | Genuine question: If I use the DeepSeek V4 Pro API via OpenCode, what data could the Chinese mine from me at w… | [open](https://x.com/DeepakNesss/status/2050496792610177254) |
| 90 | 2026-06-29 | @setyamickala | `459155643` | 51,789 | 377 | 32 | 46 | 46,983 | 826 | 0 |  | en | GM 🔥 Just dropped a FREE API key worth $598 (400M+ tokens) Models included: • deepseek-v4-pro • deepseek-v4-fl… | [open](https://x.com/setyamickala/status/2071435434303901799) |
| 91 | 2026-07-31 | @teortaxesTex | `192201556` | 72,663 | 604 | 58 | 40 | 397,038 | 804 | 22 |  | en | DeepSeek-V4-Flash is updated. «DSBench-FullStack is an internal full-stack development test set, and DSBench-H… | [open](https://x.com/teortaxesTex/status/2083069000712368246) |
| 92 | 2026-06-26 | @IBuzovskyi | `1387382307229769732` | 4,410 | 324 | 34 | 17 | 66,078 | 782 | 100 | WORKFLOW_SETUP | en | HERMES AGENT MIXTURE OF AGENTS COMBINES MULTIPLE MODELS INTO ONE ANSWER. 8% HIGHER THAN OPUS 4.8. 11% HIGHER T… | [open](https://x.com/IBuzovskyi/status/2070619684257530162) |
| 93 | 2026-05-14 | @cjzafir | `1468443406250950656` | 63,346 | 413 | 17 | 27 | 28,035 | 779 | 34 |  | en | 359M Tokens burned in 72 hours. Cost: $78~ Results: New 240M fine-tuning dataset. Process: &gt; Codex 5.5 as O… | [open](https://x.com/cjzafir/status/2055059643257479173) |
| 94 | 2026-05-19 | @cjzafir | `1468443406250950656` | 63,352 | 404 | 32 | 35 | 27,021 | 775 | 52 |  | en | Chinese models are just too good for the price. If you haven't tried them yet, go check out: > DeepSeek v4 Pro… | [open](https://x.com/cjzafir/status/2056761679825027306) |
| 95 | 2026-07-11 | @0x_kaize | `1705329284745764864` | 21,857 | 304 | 29 | 22 | 23,078 | 771 | 22 |  | en | Free AI API credits & $4,000 right now This is a limited-time offer, so you should create your accounts before… | [open](https://x.com/0x_kaize/status/2075878733483852044) |
| 96 | 2026-08-12 | @jun_song | `1831149867663798272` | 42,881 | 593 | 24 | 43 | 92,083 | 763 | 32 |  | en | Deepseek-V4-Pro-0813 vs Grok-4.6 Flappybird comparison test. DS : 22,848tok, $0.019 total Grok : 5,211tok, $0.… | [open](https://x.com/jun_song/status/2087602149979254914) |
| 97 | 2026-08-18 | @qilua02 | `2000931902002487302` | 3,194 | 288 | 33 | 13 | 36,119 | 756 | 14 |  | en | You can get 1 BILLION tokens for FREE on DeepSeek V4 Pro &amp; Qwen 3.8 Max 💀 Here’s how to set it up in 2 min… | [open](https://x.com/qilua02/status/2089573050081833035) |
| 98 | 2026-08-01 | @LuminaBench | `1058501423653101574` | 8,416 | 619 | 26 | 36 | 52,809 | 749 | 92 | OPINION | en | 🚨DeepSeek V4 Pro looks very interesting Deepseek V4 Flash 0731 just dropped yesterday, and DeepSeek says the f… | [open](https://x.com/LuminaBench/status/2083569428067705007) |
| 99 | 2026-07-21 | @robert_mchardy | `97500261` | 956 | 535 | 51 | 25 | 33,645 | 744 | 98 | ANNOUNCEMENT | en | Today, we are releasing @poolsideai Laguna S 2.1, a 118B-A8B open-weight (OpenMDW-1.1) model with a 1M-token c… | [open](https://x.com/robert_mchardy/status/2079614440295506171) |
| 100 | 2026-08-20 | @tuturetom | `806464682823282688` | 39,372 | 324 | 22 | 64 | 70,043 | 737 | 18 |  | zh | 我们把 DeepSeek V4 Pro 和 Flash 的使用门槛，直接打到了首月 5 美元无限用🚀🔥 正式推出OpenDesign Go套餐！这可能是目前使用 DeepSeek V4 最便宜的方式，且不限 Token，… | [open](https://x.com/tuturetom/status/2090405799407595560) |
| 101 | 2026-08-11 | @NFT_Chen | `1429221486032678914` | 11,274 | 457 | 48 | 61 | 62,602 | 735 | 16 |  | zh | 🚨未来一周AI模型大爆发预警！ 即将登场的热门选手： 🔹GPT-6：传闻10T级新基座 + 1.5M上下文，记忆/个性化/多智能体拉满 🔹Fable 5.1：Mythos级巅峰，长时自主任务、超大规模代码迁移、视觉+知识… | [open](https://x.com/NFT_Chen/status/2087100278801846409) |
| 102 | 2026-08-12 | @CommandCodeAI | `1729539607174483968` | 20,392 | 563 | 34 | 29 | 43,444 | 712 | 52 |  | en | Tested DeepSeek V4 Pro 0813, Kimi K3, and GLM 5.2 through FlappyBench. 3 models, same prompt with the /design … | [open](https://x.com/CommandCodeAI/status/2087631884406939727) |
| 103 | 2026-05-27 | @BohuTANG | `14851213` | 3,819 | 388 | 18 | 63 | 125,233 | 704 | 0 |  | zh | 为什么 deepseek 要出自己的 code agent，估计是看不下去了😂。别的 agent 确实很难发挥出他们模型的威力。 比如 claude code 在 deepseek v4 pro 上效果其实很差劲，感觉都… | [open](https://x.com/BohuTANG/status/2059567174088597565) |
| 104 | 2026-08-16 | @liucong0120 | `2066838340226125824` | 1,478 | 535 | 17 | 37 | 82,126 | 698 | 0 |  | zh | 这是DeepSeek-V4-Pro的问题所在？ https://t.co/8WKPe0VxZX | [open](https://x.com/liucong0120/status/2088825938351886616) |
| 105 | 2026-04-25 | @evilcos | `17552210` | 124,373 | 339 | 33 | 37 | 123,997 | 688 | 0 |  | zh | 在 Hermes Agent 上配套 DeepSeek V4 Pro 模型，链上安全分析能力已经很令我满意了…三笔近期的攻击，复杂度从中等到普通到简单。mark 下。 https://t.co/DTX4ii3C8w | [open](https://x.com/evilcos/status/2047933140359156219) |
| 106 | 2026-08-20 | @mikenevermiss | `1788243647885987840` | 23,698 | 267 | 39 | 11 | 20,974 | 683 | 0 |  | en | 🚨 DeepSeek V4 Pro recently launched, and here’s how you can use the model completely FREE. the setup takes les… | [open](https://x.com/mikenevermiss/status/2090426352092504151) |
| 107 | 2026-08-20 | @ariskaa_ai | `2042649334806654977` | 11,613 | 287 | 28 | 23 | 84,909 | 669 | 40 |  | en | you can use unlimited deepseek v4 pro/flash, glm 5.3, and qwen 3.8 in one place 😳 abacus chatllm put the open … | [open](https://x.com/ariskaa_ai/status/2090326531088547918) |
| 108 | 2026-05-15 | @arvindh__a | `1160063338669211648` | 761 | 341 | 48 | 10 | 87,902 | 655 | 92 | BENCHMARK | en | Introducing FutureSim: where we replay a temporal slice of the web and let agents forecast real-world events o… | [open](https://x.com/arvindh__a/status/2055336266322039045) |
| 109 | 2026-08-20 | @arena | `1641378826537295874` | 219,575 | 540 | 27 | 29 | 81,548 | 649 | 64 | BENCHMARK | en | Exciting update: DeepSeek-V4-Pro (High) by @deepseek_ai is now #2 among open models in Agent Arena (#14 overal… | [open](https://x.com/arena/status/2090240605561778637) |
| 110 | 2026-05-28 | @9hills | `116355740` | 28,084 | 295 | 20 | 36 | 45,016 | 649 | 0 |  | zh | gpt-5.5 就是无情的干活机器，plan、design、review、test等都用deepseek-v4-pro 每晚一个 Goal，拆成Phase后，每个Phase先写测试、再写代码、Code Review、Si… | [open](https://x.com/9hills/status/2060004371665137799) |
| 111 | 2026-08-30 | @qilua02 | `2000931902002487302` | 3,194 | 265 | 30 | 5 | 23,143 | 642 | 0 |  | en | 2 weeks FREE from Qoder AI 💀 Models available: - Qwen3.8-Max &amp; 3.7-Max / Plus - Kimi-K3 &amp; K2.7-Code - … | [open](https://x.com/qilua02/status/2093911429011448049) |
| 112 | 2026-08-19 | @Mr_CryptoYT | `551863465` | 43,713 | 272 | 10 | 10 | 29,634 | 642 | 38 |  | ar | وقفت ادفع اشتراكات الذكاء الاصطناعي كنت ادفع لـ ChatGPT و Claude كل شهر وحسيت حالي غبي لما اكتشفت البدائل هسه … | [open](https://x.com/Mr_CryptoYT/status/2090166912499974241) |
| 113 | 2026-08-13 | @alannnfx | `1792414345441210368` | 5,230 | 251 | 23 | 18 | 41,226 | 642 | 50 |  | en | you can use deepseek v4 pro, kimi k3 and glm 5.2 for free on a cloud coding agent till year end 😳 a platform c… | [open](https://x.com/alannnfx/status/2087857418420318274) |
| 114 | 2026-08-17 | @exploraX_ | `1168877404598808577` | 26,169 | 253 | 33 | 21 | 36,017 | 640 | 0 |  | en | 🚨 DeepSeek V4 Pro recently launched, and here’s how you can use the model completely FREE. the setup takes les… | [open](https://x.com/exploraX_/status/2089381203493159353) |
| 115 | 2026-08-19 | @MaxForAI | `1699797396589588480` | 33,923 | 412 | 20 | 74 | 110,984 | 631 | 6 |  | zh | 🚨突发：DeepSeek 网页端Chat疑似灰测新模型，效果超越Fable🔥 今天下午 2 点之后，国内社区陆续有人发现， @deepseek_ai 网页端 Chat 的输出行为突然发生了变化。 最明显的信号是：部分账号… | [open](https://x.com/MaxForAI/status/2090052502897184973) |
| 116 | 2026-04-28 | @SantiTorAI | `1914771584625336324` | 18,985 | 447 | 27 | 5 | 28,937 | 624 | 34 |  | es | El secreto detrás de los $0.92 para 51M tokens: el caché de inputs. DeepSeek V4 Pro vía OpenCode reutiliza tok… | [open](https://x.com/SantiTorAI/status/2049224395495985522) |
| 117 | 2026-08-12 | @jun_song | `1831149867663798272` | 42,552 | 532 | 15 | 29 | 47,773 | 617 | 16 |  | en | I tested DeepSeek-V4-Pro-0813 and Grok-4.6 on my agent framework. Performance underwhelms a bit relative to be… | [open](https://x.com/jun_song/status/2087612303407829139) |
| 118 | 2026-07-04 | @k2sbhai | `1548759486491402240` | 5,556 | 259 | 28 | 13 | 17,984 | 612 | 17 |  | en | DeepSeek V4 Pro, MiniMax M3, Kimi K2.6, GLM 5.1, Mistral, and 130+ other models behind one free API 😳 no credi… | [open](https://x.com/k2sbhai/status/2073407984932393423) |
| 119 | 2026-06-21 | @asd3312223 | `4638221755` | 20,468 | 217 | 30 | 42 | 30,139 | 602 | 0 |  | zh | 无限次用各家顶级模型 Gpt5.5 Claude4.8 DeepSeekV4pro Qwen3Max Kimi K2都无限免费用。 点这里:https://t.co/MD89JmI6hp 没有广告，纯分享。 | [open](https://x.com/asd3312223/status/2068570012047024556) |
| 120 | 2026-06-22 | @NbSoloman | `1188513090704424960` | 1,022 | 260 | 20 | 14 | 32,401 | 601 | 0 |  | en | 🚀 Here's a free way to use the latest flagship models from Claude, Gemini, and GPT. And that's not all. You al… | [open](https://x.com/NbSoloman/status/2068887160535843248) |
| 121 | 2026-08-15 | @NFT_Chen | `1429221486032678914` | 11,274 | 285 | 25 | 25 | 142,767 | 565 | 6 |  | zh | 🚨独家证实！DeepSeek V4 Pro 0813 暗藏多个模式可切换，灰度荣光疑似可重现！ 具有模式细节如下： 1️⃣公开测巨区，远不如灰度测试，成2026最大谜团 2️⃣极简模式实测：背后暗藏3个可切换模型/行为 … | [open](https://x.com/NFT_Chen/status/2088463946122731900) |
| 122 | 2026-04-29 | @benitoz | `30399584` | 22,815 | 338 | 38 | 26 | 1,281,873 | 562 | 96 | DEEP_ANALYSIS | en | Wow @SemiAnalysis just dropped day-zero numbers on @deepseek_ai V4 Pro Blackwell (B300): 8,075 tok/s/GPU AMD M… | [open](https://x.com/benitoz/status/2049593416439500859) |
| 123 | 2026-04-27 | @ConstanceWaing | `1091521929255608320` | 8,499 | 385 | 25 | 21 | 50,808 | 562 | 82 | USAGE_DEMO | en | Spent the last few days running DeepSeek V4 Pro alongside Claude Code on Opus 4.6 and Codex on GPT-5.4. Each h… | [open](https://x.com/ConstanceWaing/status/2048674563505127884) |
| 124 | 2026-04-24 | @atomic_chat_hq | `2037196634489077761` | 15,319 | 301 | 34 | 39 | 132,740 | 551 | 58 |  | en | Deepseek V4 Pro vs GPT-5.5 in a gamedev contest (full prompt is below)🏎️ Cost: Deepseek V4 Pro: $0.07656 GPT-5… | [open](https://x.com/atomic_chat_hq/status/2047720974859010121) |
| 125 | 2026-08-27 | @composio | `1710011976179728384` | 23,677 | 383 | 38 | 18 | 33,418 | 532 | 24 |  | en | We tested 5 open-weight models on 30 multi-step agentic tasks and compared how they performed: - GLM 5.3 Flash… | [open](https://x.com/composio/status/2092983285819310307) |
| 126 | 2026-08-13 | @k2sbhai | `1548759486491402240` | 5,519 | 222 | 24 | 16 | 21,139 | 528 | 0 |  | en | deepseek v4 pro 0813 is available for free with signup credits 😳 hcnsec gives you free credits after creating … | [open](https://x.com/k2sbhai/status/2087996072820121712) |
| 127 | 2026-08-25 | @vllm_project | `1774187564276289536` | 48,043 | 287 | 37 | 24 | 103,527 | 521 | 100 | DEEP_ANALYSIS | en | Congratulations to @SemiAnalysis_ on the release of AgentX 1.0 🎊, an open-source multi-turn agentic coding ben… | [open](https://x.com/vllm_project/status/2092040745842774377) |
| 128 | 2026-08-19 | @zefirium | `1438592405201096705` | 3,722 | 176 | 26 | 13 | 17,085 | 517 | 54 |  | en | Free AI isn't a promotion. It's a pipeline. When I published the free AI tiers map, I thought I caught everyth… | [open](https://x.com/zefirium/status/2090041768314048709) |
| 129 | 2026-04-30 | @elliotarledge | `1595935520999510016` | 43,374 | 327 | 26 | 19 | 30,035 | 517 | 46 |  | en | https://t.co/9GyQa6Fwph is live. can frontier models write fast triton/cuda/cutlass/cute-dsl/ptx without cheat… | [open](https://x.com/elliotarledge/status/2049955361889874396) |
| 130 | 2026-06-22 | @Atenov_D | `1577008378852802561` | 13,809 | 232 | 17 | 40 | 27,468 | 511 | 0 |  | en | FREE DeepSeek V4 Pro and V4 Flash API. Runtime by Bad Theory Labs just dropped it. Same platform, new free mod… | [open](https://x.com/Atenov_D/status/2069024218969170045) |
| 131 | 2026-08-12 | @noctus91 | `1960747924843061253` | 1,219 | 439 | 10 | 10 | 26,110 | 506 | 40 |  | en | OpenCode is serving DeepSeek V4 Pro at ~70 tok/s on the Go plan. That’s a wild amount of throughput for an on … | [open](https://x.com/noctus91/status/2087579941852553282) |
| 132 | 2026-07-01 | @yuhasbeentaken | `1681890517666390016` | 4,450 | 326 | 22 | 42 | 50,951 | 506 | 30 |  | en | deepseek v4 is terrible at hallucinations... >deepseek v4 pro scores 94%. >deepseek v4 flash is even worse at … | [open](https://x.com/yuhasbeentaken/status/2072356564770459871) |
| 133 | 2026-07-18 | @BoxMrChen | `2994681926` | 29,637 | 264 | 22 | 45 | 86,124 | 502 | 6 |  | zh | 美国AI集体被吓哭，瘫坐在椅子上，犹如看到了核弹爆炸 跑了一个小时，消耗了7毛钱，融合了两个游戏做出了一个完整并且不存在的游戏，并且融合效果极佳！ DeepSeekV4Pro真实版能力极强，已经真做出了核弹爆炸的水平。目… | [open](https://x.com/BoxMrChen/status/2078515239822544989) |
| 134 | 2026-04-25 | @Tur24Tur | `86538235` | 6,481 | 239 | 37 | 4 | 26,455 | 499 | 34 |  | en | Experiment 2/3 Android Root Detection Bypass (using DeepSeek V4 Pro): I requested the agent to analyze a decom… | [open](https://x.com/Tur24Tur/status/2048011975909654698) |
| 135 | 2026-04-24 | @NVIDIAAI | `740238495952736256` | 336,191 | 386 | 34 | 17 | 54,159 | 497 | 54 |  | en | 📊 Day 0 performance is here: DeepSeek-V4-Pro running on NVIDIA Blackwell Ultra. Using @vllm_project's Day 0 re… | [open](https://x.com/NVIDIAAI/status/2047823093578518758) |
| 136 | 2026-07-11 | @ArtificialAnlys | `1743487864934162432` | 132,970 | 376 | 20 | 11 | 63,897 | 489 | 82 | BENCHMARK | en | China Mobile just launched JT-4.1 Flash 236B A21B, a non-reasoning model scoring 39 on the Artificial Analysis… | [open](https://x.com/ArtificialAnlys/status/2075735243915702726) |
| 137 | 2026-07-13 | @ZhihuFrontier | `1931962509596246016` | 11,569 | 290 | 32 | 10 | 23,404 | 483 | 100 | DEEP_ANALYSIS | en | 🧱 DeepSeek-V4 is not just 1M context. It is a full system rebuild. Zhihu contributor THU-PACMAN 实验室 shared a d… | [open](https://x.com/ZhihuFrontier/status/2076653008616825251) |
| 138 | 2026-06-29 | @_avichawla | `1175166450832687104` | 76,103 | 258 | 20 | 18 | 44,244 | 470 | 72 | BENCHMARK | en | Big win for open-source LLMs! DeepSeek V4 Pro holds the top open-weights score on SWE-bench Verified, in the G… | [open](https://x.com/_avichawla/status/2071639616617361798) |
| 139 | 2026-08-28 | @mdp_sec | `2036270919757471747` | 2,109 | 216 | 27 | 34 | 104,179 | 469 | 96 | BENCHMARK | en | Most AI cybersecurity benchmarks answer the wrong question for bug-bounty hunters. They give the model source … | [open](https://x.com/mdp_sec/status/2093342858501820901) |
| 140 | 2026-06-18 | @Vincent_AINotes | `1861449351328854016` | 57,953 | 208 | 27 | 27 | 33,558 | 469 | 15 |  | zh | OpenAI 格局大了，Codex 现在支持直接接入任意开源 AI 模型 不只是用 GPT 了。Ollama 本地模型、DeepSeek API、LM Studio、vLLM，全都能接进 Codex Desktop 最骚… | [open](https://x.com/Vincent_AINotes/status/2067555972726333866) |
| 141 | 2026-08-12 | @jun_song | `1831149867663798272` | 42,552 | 399 | 6 | 18 | 32,229 | 461 | 0 |  | en | Deepseek-V4-Pro-0813🤐 You are not ready for this yet. | [open](https://x.com/jun_song/status/2087567626298151296) |
| 142 | 2026-08-13 | @cjzafir | `1468443406250950656` | 63,346 | 285 | 17 | 13 | 30,664 | 453 | 56 |  | en | I tested new Deepseek model for last 2 hours. Deepseek v4 pro 0813 sounds alot like Claude Opus 4.6 which is t… | [open](https://x.com/cjzafir/status/2087699483002052802) |
| 143 | 2026-08-12 | @karminski3 | `1071224721046261760` | 39,143 | 266 | 5 | 138 | 90,893 | 453 | 0 |  | zh | 刚发的 DeepSeek-V4-Pro-0813 好像的确有问题, reasoning_effort=max 的时候模型在长程 AgenticCoding 任务下更倾向于早停. 我这个测试总计50轮, 让模型不断优化代码… | [open](https://x.com/karminski3/status/2087602210649895354) |
| 144 | 2026-08-21 | @XChatScout | `1840097341086543874` | 7,873 | 188 | 22 | 94 | 12,743 | 452 | 1 |  | zh | 刚发现 DeepSeek V4 Pro 现在也能免费接进编码工具了 TeamoRouter 目前同时提供： • DeepSeek V4 Pro 免费版 • DeepSeek V4 Flash 免费版 • 每个模型每天 2… | [open](https://x.com/XChatScout/status/2090743437972979996) |
| 145 | 2026-08-13 | @HarshithLucky3 | `1374854891294711809` | 3,394 | 400 | 6 | 26 | 29,262 | 446 | 0 |  | en | sorry guys DeepSeek V4 Flash 0731 &gt;&gt;&gt; DeepSeek V4 Pro 0813 a bit disappointing with V4 pro | [open](https://x.com/HarshithLucky3/status/2087820016708378981) |
| 146 | 2026-06-05 | @HermesAgentTips | `2024213782772244480` | 8,676 | 179 | 5 | 125 | 52,210 | 446 | 8 |  | en | be honest... whats the best coding model to use pair with hermes agent? - Opus 4.8 - GPT-5.5 - DeepSeek V4 Pro… | [open](https://x.com/HermesAgentTips/status/2063002928206483880) |
| 147 | 2026-06-17 | @bridgemindai | `1767869376496107520` | 52,948 | 351 | 13 | 30 | 32,459 | 443 | 14 |  | en | GLM 5.2 just jumped from 43.4 to 50.7 on the Artificial Analysis Coding Index. That is a 7 point gain in a sin… | [open](https://x.com/bridgemindai/status/2067227993974460467) |
| 148 | 2026-07-01 | @DeRonin_ | `1414948050817196037` | 110,984 | 210 | 37 | 43 | 24,686 | 437 | 84 | COMPARISON | en | How much do Chinese models cut your API bill? 🇨🇳 WITH THE SAME OUTPUT!!! US frontier model → chinese open mode… | [open](https://x.com/DeRonin_/status/2072309827116716372) |
| 149 | 2026-08-28 | @NFT_Chen | `1429221486032678914` | 11,274 | 191 | 13 | 59 | 22,825 | 435 | 56 |  | zh | 🔥$10 编程套餐别瞎买！OpenCode Go vs CommandCode GOAT，怎么选才真划算👇 1️⃣看总盘：两边都是约 $10/月。Go 大约 $60 额度（6倍），GOAT 大约 $70（7倍），GOAT… | [open](https://x.com/NFT_Chen/status/2093190171118506187) |
| 150 | 2026-06-08 | @ivanfioravanti | `43874767` | 41,805 | 310 | 9 | 46 | 33,377 | 430 | 96 | BENCHMARK | en | DeepSWE and DeepSeek V4 Pro: surely the benchmark is designed to facilitate GPT 5.5, and mini-swe is not ideal… | [open](https://x.com/ivanfioravanti/status/2063877822062449109) |
| 151 | 2026-08-14 | @nahid_pro09 | `1635255155334729730` | 4,703 | 173 | 17 | 16 | 19,836 | 427 | 34 |  | en | you can get unlimited access to deepseek v4-pro and v4-flash for completely free 😳 deepseek just dropped their… | [open](https://x.com/nahid_pro09/status/2088176122039050617) |
| 152 | 2026-05-17 | @neural_avb | `1754194661084983296` | 13,145 | 260 | 11 | 41 | 51,832 | 426 | 44 |  | en | I have tried deepseek-v4 pro on all sorts of coding tasks. ~300B tokens usage across DeepSeek API and Ollama C… | [open](https://x.com/neural_avb/status/2056014407365480654) |
| 153 | 2026-05-02 | @kaif9998 | `1685205746579857408` | 8,122 | 320 | 13 | 19 | 21,269 | 416 | 34 |  | en | OpenCode Go x DeepSeek V4 Pro 158k+ requests/month for just $5–10 DeepSeek V4 Flash is an unstoppable monster … | [open](https://x.com/kaif9998/status/2050479333710725558) |
| 154 | 2026-08-28 | @Youssofal_ | `1166679738368299008` | 10,852 | 331 | 7 | 15 | 21,450 | 411 | 24 |  | en | Qwen Flash Next: a 125B model that beats 1.6T Deepseek V4 Pro and matches Googles flagship. Oh and it beats Fa… | [open](https://x.com/Youssofal_/status/2093146174383636744) |
| 155 | 2026-04-24 | @intheworldofai | `1656791689237876737` | 18,003 | 313 | 8 | 24 | 50,792 | 408 | 0 |  | en | Just asked DeepSeek V4 Pro to generate a macOS clone... and uh... it tried. Mid. https://t.co/Yp08QNa08X | [open](https://x.com/intheworldofai/status/2047523591822983296) |
| 156 | 2026-06-12 | @ArtificialAnlys | `1743487864934162432` | 132,970 | 278 | 25 | 18 | 2,128,980 | 402 | 86 | BENCHMARK | en | Today we're releasing the first results for AA-AgentPerf, our new agentic inference benchmark: initially cover… | [open](https://x.com/ArtificialAnlys/status/2065559824230957190) |
| 157 | 2026-05-01 | @ArtificialAnlys | `1743487864934162432` | 132,970 | 284 | 31 | 18 | 29,370 | 401 | 96 | BENCHMARK | en | All three leading open weights models were released last week. Progress continues for open weights models alon… | [open](https://x.com/ArtificialAnlys/status/2050096370200281539) |
| 158 | 2026-08-01 | @DeryaTR_ | `1228098150012981249` | 338,772 | 329 | 19 | 21 | 25,625 | 400 | 26 |  | en | The massive jump in some benchmark scores makes it clear that DeepSeek-V4-Flash is not an incremental upgrade … | [open](https://x.com/DeryaTR_/status/2083634284053594162) |
| 159 | 2026-08-30 | @0x0SojalSec | `1445347022555340805` | 52,750 | 174 | 14 | 4 | 18,224 | 392 | 40 |  | en | New Uncensored Tencent Hy-MT2-30B-A3B model & you can run locally. - Tencent claimed it beat DeepSeek-V4-Pro a… | [open](https://x.com/0x0SojalSec/status/2094150457522569471) |
| 160 | 2026-08-15 | @vllm_project | `1774187564276289536` | 48,043 | 250 | 29 | 16 | 25,195 | 390 | 64 | WORKFLOW_SETUP | en | Six weeks ago, serving DSpark in vLLM meant choosing a draft length for your traffic and living with it. Now y… | [open](https://x.com/vllm_project/status/2088425247112679794) |
| 161 | 2026-05-13 | @kilocode | `1899809291353169921` | 29,154 | 283 | 12 | 13 | 21,520 | 390 | 64 | BENCHMARK | en | We tested DeepSeek V4 Pro and Flash on the same FlowGraph spec we used for Opus 4.7 vs. Kimi K2.6. Pro scored … | [open](https://x.com/kilocode/status/2054598416705998925) |
| 162 | 2026-08-16 | @ZhihuFrontier | `1931962509596246016` | 11,569 | 188 | 18 | 9 | 34,230 | 385 | 82 | DEEP_ANALYSIS | en | 🧪 Is DeepSeek V4 Pro Overfit to DeepSeek Harness? The Real Problem May Be Interface Sensitivity DeepSeek discl… | [open](https://x.com/ZhihuFrontier/status/2088872677692076431) |
| 163 | 2026-08-13 | @karminski3 | `1071224721046261760` | 39,143 | 272 | 5 | 62 | 46,020 | 384 | 0 |  | zh | 烧了1亿token了，正在验证deepseek-v4-pro-0813问题出在哪里，一会给大家带来评测+硬核解析视频。 https://t.co/LYULPOALYM | [open](https://x.com/karminski3/status/2088023193382785215) |
| 164 | 2026-04-24 | @arena | `1641378826537295874` | 219,719 | 290 | 29 | 12 | 21,933 | 379 | 46 |  | en | Competition between Chinese labs is intensifying. Top 3 Open Models in Text Arena are all now sitting just bel… | [open](https://x.com/arena/status/2047714237502677405) |
| 165 | 2026-08-16 | @0x_kaize | `1705329284745764864` | 21,857 | 166 | 15 | 14 | 16,833 | 372 | 62 | PROMO | en | You can get Qwen 3.8 Max + DeepSeek v4 Pro for FREE i'm sharing a new way for you to try out these flagship mo… | [open](https://x.com/0x_kaize/status/2088971997690675596) |
| 166 | 2026-05-03 | @laozhang2579 | `1967267126655569920` | 4,932 | 214 | 12 | 23 | 45,576 | 364 | 16 |  | zh | DeepSeek-v4-Pro vs GPT-5.5 相同的AI Agent提示词 从零构建了一款Agent Chatbot GPT-5.5 架构和工程基建做到了 90 分,但是Agent核心代码并没有完全按照规划的文档… | [open](https://x.com/laozhang2579/status/2050855396827447626) |
| 167 | 2026-08-12 | @MaxForAI | `1699797396589588480` | 33,923 | 225 | 19 | 79 | 121,822 | 352 | 0 |  | zh | 🚨BREAKING：DeepSeek V4 Pro 正式版即将于明天发布！🚀 十分钟前， @deepseek_ai 官网更新了DeepSeek V4 Pro正式版的信息！ 新的模型叫DeepSeek-V4-Pro-081… | [open](https://x.com/MaxForAI/status/2087562906930126933) |
| 168 | 2026-08-17 | @slash1sol | `1450199884053745669` | 12,333 | 163 | 13 | 30 | 14,259 | 351 | 0 |  | en | QWEN 3.8 MAX + DEEPSEEK V4 PRO BOTH FREE ON ONE ENDPOINT • the gateway > Qwen3.8-Max (2.4T MoE) + DeepSeek V4 … | [open](https://x.com/slash1sol/status/2089348071758917879) |
| 169 | 2026-08-14 | @bourneliu66 | `2815325906` | 30,885 | 194 | 5 | 76 | 110,399 | 344 | 0 |  | zh | 说一个很多人没注意到的事实： Gemini Flash 3.7 &gt; DeepSeek V4 Pro 0813 包括并不限于：速度、代码能力、审美、多模态能力 | [open](https://x.com/bourneliu66/status/2088175504277070324) |
| 170 | 2026-08-30 | @k2sbhai | `1548759486491402240` | 5,518 | 168 | 7 | 16 | 16,177 | 342 | 0 |  | en | Qoder is giving away 2 weeks of access to a bunch of top AI models 😳 you can try them all without setting up a… | [open](https://x.com/k2sbhai/status/2093985336691150966) |
| 171 | 2026-08-28 | @buildwithsid | `1409195816007266304` | 7,763 | 203 | 2 | 48 | 33,948 | 329 | 34 |  | en | fuck it... heres my .env DATABASE_URL=postgresql://[credential redacted by this repository] … | [open](https://x.com/buildwithsid/status/2093269672691200232) |
| 172 | 2026-08-14 | @TypingMindApp | `1654041990512758784` | 5,017 | 255 | 6 | 3 | 68,144 | 329 | 10 |  | en | Gemini 3.7 Flash vs. DeepSeek V4 Pro 0318 vs. Muse Spark 1.2 vs. Grok 4.6 👀 Gave 4 AI models a challenge: Draw… | [open](https://x.com/TypingMindApp/status/2088214938754167263) |
| 173 | 2026-07-18 | @Mr_Salio | `2026660978046480384` | 5,706 | 249 | 13 | 34 | 33,292 | 324 | 42 |  | en | 🚨 I just tested DeepSeek V4 Pro (GA) I tested it on a 3D game generation prompt, and this was the result In my… | [open](https://x.com/Mr_Salio/status/2078493760896352296) |
| 174 | 2026-07-24 | @thehypedotnews | `2034267014135685120` | 4,562 | 172 | 18 | 21 | 22,217 | 319 | 100 | COMPARISON | en | laguna s 2.1 vs hy3 vs inkling vs deepseek v4 pro max @poolsideai released laguna s 2.1 on july 21 – a new ope… | [open](https://x.com/thehypedotnews/status/2080645764460466560) |
| 175 | 2026-07-03 | @mranti | `5709522` | 357,098 | 180 | 12 | 46 | 62,636 | 317 | 0 |  | zh | 凯恩小学毕业了，放假在家用Vibe Coding，我刚给他换上GLM5.2，原来他用的是Kimi2.6和DeepseekV4pro。他用了一天后，突然跑来告诉我，智谱实在太聪明了，往往他说了一点，智谱顺便会把他没想到的事… | [open](https://x.com/mranti/status/2072989137867854209) |
| 176 | 2026-08-13 | @jun_song | `1831149867663798272` | 42,552 | 254 | 8 | 17 | 49,138 | 313 | 0 |  | en | Comparing Deepseek-V4-Pro-0813 before and after the fingerprint change: Flappybird test. Right: 0813 initial r… | [open](https://x.com/jun_song/status/2087914782733324388) |
| 177 | 2026-07-06 | @naymur_dev | `1610112096280391683` | 1,036 | 204 | 12 | 22 | 35,550 | 313 | 52 |  | en | Comparing GLM 5.2 vs DeepSeek v4 Pro Everyone is talking about DeepSeek v4 Pro will overpower GLM 5.2. So I ra… | [open](https://x.com/naymur_dev/status/2074259822145622065) |
| 178 | 2026-04-29 | @LechMazur | `35654959` | 32,461 | 210 | 20 | 12 | 22,240 | 313 | 62 | BENCHMARK | en | GPT-5.5 (xhigh) tops the Short-Story Creative Writing Benchmark, edging past GPT-5.4 (xhigh): 2.85 → 3.01! Cla… | [open](https://x.com/LechMazur/status/2049580331175665830) |
| 179 | 2026-08-17 | @CFchangelog | `1938036278798532608` | 5,040 | 224 | 13 | 8 | 28,725 | 309 | 32 |  | en | DeepSeek V4 Pro 0813 and V4 Flash 0731 are live on Workers AI. Handle massive codebases and long-horizon workf… | [open](https://x.com/CFchangelog/status/2089140357921464761) |
| 180 | 2026-05-21 | @anibal | `812920` | 9,266 | 227 | 3 | 14 | 20,896 | 299 | 4 |  | es | En verdad los tokens de DeepSeek V4 Pro en OpenCode son ridículamente económicos 🤔 | [open](https://x.com/anibal/status/2057420298543108485) |
| 181 | 2026-07-30 | @ArtificialAnlys | `1743487864934162432` | 132,970 | 234 | 12 | 12 | 27,287 | 293 | 80 | BENCHMARK | en | Agnes AI has launched Agnes 2.5 Pro Alpha, a low-priced reasoning model reaching 39 on the Artificial Analysis… | [open](https://x.com/ArtificialAnlys/status/2082662482523406752) |
| 182 | 2026-06-17 | @TheGeorgePu | `1382868229765230595` | 50,115 | 177 | 4 | 74 | 20,421 | 288 | 38 |  | en | Why are we happily burning on Opus at $5/$25 per 1M. When DeepSeek is 26x cheaper and as capable? Ever since I… | [open](https://x.com/TheGeorgePu/status/2067267833231282506) |
| 183 | 2026-08-13 | @bourneliu66 | `2815325906` | 30,885 | 170 | 4 | 97 | 63,830 | 286 | 0 |  | zh | 在今天凌晨偷偷发布的DeepSeek V4 Pro 0813 由于口碑太差，即将下架，回炉重造。 那些玩滑动变阻器梗的朋友，请回去发明新的梗。 | [open](https://x.com/bourneliu66/status/2087825941854855285) |
| 184 | 2026-07-03 | @naymur_dev | `1610112096280391683` | 1,036 | 173 | 13 | 25 | 28,080 | 278 | 60 |  | en | Fable 5 vs GPT 5.5 vs GLM 5.2 vs DeepSeek v4 Pro I tried the same prompt with 4 different models. I wanted to … | [open](https://x.com/naymur_dev/status/2073154102260027760) |
| 185 | 2026-08-23 | @brandon_galang | `749067617198075904` | 5,128 | 173 | 6 | 37 | 18,504 | 277 | 80 | OPINION | en | here's my AI model tier list as of rn as a gtm engineer at vercel. this isn't just pure benchmark performance,… | [open](https://x.com/brandon_galang/status/2091558338018660744) |
| 186 | 2026-04-26 | @gordic_aleksa | `907007346546810881` | 31,301 | 148 | 19 | 2 | 9,418 | 273 | 100 | DEEP_ANALYSIS | en | [DeepSeek V4 Pro summary] building LLMs is increasingly looking more and more like building a car or an airpla… | [open](https://x.com/gordic_aleksa/status/2048455129779908952) |
| 187 | 2026-08-26 | @arena | `1641378826537295874` | 219,575 | 209 | 10 | 24 | 33,586 | 271 | 38 |  | en | Agent Arena measures models on millions of real-world, long-horizon agentic tasks: Overall, and specifically b… | [open](https://x.com/arena/status/2092656635529638170) |
| 188 | 2026-08-17 | @Bhavani_00007 | `1857824397685567492` | 6,879 | 173 | 16 | 40 | 24,670 | 265 | 40 |  | en | I tested Gemini 3.7 Flash vs Qwen 3.8 vs DeepSeek V4 Pro vs GLM 5.3 same prompt: a busy train interior, then l… | [open](https://x.com/Bhavani_00007/status/2089324189589336221) |
| 189 | 2026-08-16 | @karminski3 | `1071224721046261760` | 39,143 | 166 | 10 | 24 | 78,863 | 263 | 0 |  | zh | DeepSeek Harness 能拯救这次 V4-Pro 的发布吗? 给大家带来 DeepSeek-V4-Pro-0813 实测! 本期视频我们只验证4件事: deepseek-v4-pro-0813 拉了吗? v4-… | [open](https://x.com/karminski3/status/2088856655534624783) |
| 190 | 2026-08-27 | @astropol0 | `1780189133249609728` | 3,194 | 172 | 2 | 61 | 22,042 | 262 | 12 |  | en | Coding is still Grok’s weak spot... Grok 4.6 (High) is #12 on Agent Arena Code while Opus 5, Fable 5, Sol, Kim… | [open](https://x.com/astropol0/status/2093055484756652425) |
| 191 | 2026-08-28 | @DeepLearningAI | `992153930095251456` | 346,344 | 145 | 17 | 6 | 11,970 | 260 | 40 |  | en | Without strong software engineering fundamentals, coding agents often default to bad trade-offs that hurt syst… | [open](https://x.com/DeepLearningAI/status/2093384971134095633) |
| 192 | 2026-08-23 | @eliebakouch | `1745892418539417600` | 23,774 | 183 | 7 | 14 | 8,303 | 260 | 0 |  | en | does using a skill to change the model's output style also affect its chain of thought? yes! tried telling the… | [open](https://x.com/eliebakouch/status/2091620634094674280) |
| 193 | 2026-08-13 | @zainhas | `781542714` | 6,947 | 216 | 5 | 13 | 39,932 | 259 | 14 |  | en | whats insane is that DeepSeek-v4-pro 0813 is 2x cheaper per task than even DeepSeek-v4-Flash 0731 https://t.co… | [open](https://x.com/zainhas/status/2088038968139063689) |
| 194 | 2026-08-15 | @zainhas | `781542714` | 6,952 | 183 | 13 | 11 | 70,200 | 258 | 44 |  | en | head-to-head: DeepSeek-V4 Pro 0813 vs. GPT 5.6 Sol vs. Fable 5 on software eng/DeepSWE tasks &gt; Accuracy pas… | [open](https://x.com/zainhas/status/2088466670302204197) |
| 195 | 2026-07-19 | @Atenov_D | `1577008378852802561` | 13,809 | 127 | 7 | 25 | 10,375 | 254 | 44 |  | en | FREE $70 in credits for Opus 4.8, GPT-5.5, GLM 5.2, and Kimi K2.7 Code. And you can stack more just by clickin… | [open](https://x.com/Atenov_D/status/2078921133475402230) |
| 196 | 2026-08-24 | @MinLiBuilds | `1679698342283186177` | 16,040 | 140 | 11 | 42 | 68,958 | 253 | 6 |  | zh | 以前嫌 H200 三万美元一张贵，现在回头一看，卧槽，H200 居然是丐版。 老黄这个摩尔定律已经有点不对劲了。 H200 → GB300： 用梁子的 DeepSeek V4 Pro 跑真实 Agent 工作负载，每兆瓦… | [open](https://x.com/MinLiBuilds/status/2091915873661686204) |
| 197 | 2026-06-03 | @CommandCodeAI | `1729539607174483968` | 20,392 | 146 | 7 | 7 | 747,260 | 252 | 22 |  | en | DeepSeek works best in Command Code. two ways to prove it: $1 Go plan with $10 → $40 for DeepSeek V4 pro read … | [open](https://x.com/CommandCodeAI/status/2062006139345322397) |
| 198 | 2026-04-25 | @Tur24Tur | `86538235` | 6,481 | 149 | 9 | 9 | 54,808 | 252 | 14 |  | en | Just ported my AI agent from Claude Opus 4.6/4.7 to @deepseek_ai V4 Pro. Same multi-agent architecture, same p… | [open](https://x.com/Tur24Tur/status/2047957612101063016) |
| 199 | 2026-08-13 | @_FORAB | `4848269835` | 141,822 | 108 | 11 | 117 | 67,931 | 250 | 0 |  | zh | 发生了什么？DeepSeek 官网的 DeepSeek V4 Pro 0813 发布通知，以及开放平台的公告，刚刚突然被撤销下架了。 不过官方接口 API 文档，仍能看到 0813 版本的文字显示，这次版本性能测试，被社… | [open](https://x.com/_FORAB/status/2087815968538136991) |
| 200 | 2026-07-02 | @naymur_dev | `1610112096280391683` | 1,036 | 146 | 8 | 16 | 36,539 | 249 | 18 |  | en | DeepSeek v4 Pro vs Fable 5 You can see the result: DeepSeek cost only $0.0005 for this design. So the key take… | [open](https://x.com/naymur_dev/status/2072795260598788243) |
| 201 | 2026-07-03 | @jun_song | `1831149867663798272` | 42,552 | 207 | 3 | 20 | 10,002 | 239 | 0 |  | en | I’m hoping official release of Deepseek V4 Pro coming this month to be affordable temu-Fable. | [open](https://x.com/jun_song/status/2072838193943388346) |
| 202 | 2026-07-01 | @Rahul_J_Mathur | `3115134108` | 122,101 | 139 | 2 | 18 | 26,711 | 235 | 82 | USAGE_DEMO | en | Last night I panicked when our fund’s agent Zen replied to me in Chinese. For a minute, I wasn’t sure WTF happ… | [open](https://x.com/Rahul_J_Mathur/status/2072279035493900395) |
| 203 | 2026-06-09 | @AI_Whisper_X | `1841436670169923584` | 6,353 | 88 | 12 | 33 | 19,241 | 229 | 80 | DEEP_ANALYSIS | zh | 刚看完 SemiAnalysis 这篇 DeepSeek V4 推理性能长文，很有意思。 DeepSeek V4 一出来，被考试的是 NVIDIA、AMD、Huawei、vLLM、SGLang、TensorRT-LLM、… | [open](https://x.com/AI_Whisper_X/status/2064334530497130844) |
| 204 | 2026-04-24 | @DeepTechTR | `1858176282032496640` | 25,679 | 119 | 10 | 2 | 13,492 | 227 | 60 |  | tr | 🚨 Arkadaşlar, DeepSeek yine yaptı yapacağını! DeepSeek-V4 resmen yayınlandı ve açık kaynak olarak herkese açıl… | [open](https://x.com/DeepTechTR/status/2047538839879618870) |
| 205 | 2026-06-15 | @vikingmute | `296593919` | 67,861 | 71 | 9 | 39 | 14,727 | 226 | 0 |  | zh | 昨天抽空试了一下这个方法论，真的不错，不过我不是 audit，而是做新 feature，我让 GPT-5.5 High 用这个 skill 出 plan，不写一行代码，有Metadata， Scope 和 Steps。 … | [open](https://x.com/vikingmute/status/2066326744383262976) |
| 206 | 2026-08-31 | @ArtificialAnlys | `1743487864934162432` | 132,853 | 161 | 14 | 23 | 187,823 | 224 | 90 | BENCHMARK | en | Apodex has launched Apodex 1.1, a proprietary model scoring 44 on the Artificial Analysis Intelligence Index w… | [open](https://x.com/ArtificialAnlys/status/2094256863865078046) |
| 207 | 2026-08-31 | @pengsonal | `1804071502360514563` | 16,466 | 113 | 9 | 5 | 15,633 | 224 | 0 |  | en | models like KIMI K3, GLM 5.3 FOR FREE 😳 Qoder is giving new users 2 weeks of free trail also available: • Qwen… | [open](https://x.com/pengsonal/status/2094255934046626118) |
| 208 | 2026-08-20 | @elliotarledge | `1595935520999510016` | 43,374 | 167 | 4 | 4 | 26,757 | 219 | 78 | BENCHMARK | en | DeepSeek V4 Pro on KernelBench-Hard. TopK is 9.35% of roofline. Opus 5 is 9.46%. The June checkpoint was 1.40%… | [open](https://x.com/elliotarledge/status/2090458795172360257) |
| 209 | 2026-08-28 | @runinfrai | `2026790211716337664` | 8,309 | 129 | 7 | 12 | 10,100 | 218 | 40 |  | en | DeepSeek V4 Pro on RunInfra runs at 296 tok/s, 5x DeepSeek's own endpoint Cheapest V4 Pro on the board at $0.6… | [open](https://x.com/runinfrai/status/2093400098701021619) |
| 210 | 2026-08-18 | @lordx64 | `55581718` | 8,148 | 107 | 11 | 12 | 10,358 | 218 | 54 |  | en | It feels good to be at the top of the world, in AI research crafting AI models fine-tuned for Cyber Security, … | [open](https://x.com/lordx64/status/2089800467346034826) |
| 211 | 2026-04-30 | @ArtificialAnlys | `1743487864934162432` | 132,970 | 173 | 9 | 8 | 19,073 | 215 | 100 | BENCHMARK | en | Tencent has released Hy3-preview, an open weights reasoning model scoring 42 on the Artificial Analysis Intell… | [open](https://x.com/ArtificialAnlys/status/2049852417316143393) |
| 212 | 2026-06-04 | @0xAA_Science | `1456122941192605705` | 181,175 | 67 | 2 | 87 | 60,060 | 214 | 0 |  | zh | 我在尝试用 Claude Code 接 deepseek v4 pro，但是 deepseek 不是多模态模型，不支持图片输入。 有解决办法吗？ https://t.co/v2UErWeNMw | [open](https://x.com/0xAA_Science/status/2062521396379721766) |
| 213 | 2026-08-25 | @MaxForAI | `1699797396589588480` | 34,208 | 99 | 5 | 33 | 33,117 | 210 | 60 | OPINION | zh | 一次搜索API的成本，已经比Agent推理Token更贵了。 @p0 刚刚发布了 Search Fast API，直接把 Agent Web Search 的价格压到了 $1 / 1000 个搜索结果，平均延迟约 700… | [open](https://x.com/MaxForAI/status/2092076068186505448) |
| 214 | 2026-08-30 | @nahid_pro09 | `1635255155334729730` | 4,704 | 96 | 7 | 9 | 10,628 | 207 | 54 |  | en | freeee 2 weeks of pro ai models just sitting on https://t.co/xXSaYZj8SJ right now😳 here is the full breakdownw… | [open](https://x.com/nahid_pro09/status/2093944846130262473) |
| 215 | 2026-08-28 | @Atenov_D | `1577008378852802561` | 13,809 | 78 | 3 | 19 | 12,553 | 193 | 34 |  | en | GPT-5.6, Claude Fable 5, Gemini 3.1 Pro, Veo 3.1, ElevenLabs - one subscription, first month free. That's $24.… | [open](https://x.com/Atenov_D/status/2093368001936388281) |
| 216 | 2026-07-16 | @hsu_steve | `161078090` | 45,871 | 128 | 11 | 8 | 73,241 | 193 | 40 |  | en | K3 very strong but as expensive as GPT-5.6 Sol! Cost per task ($0.94) is similar to GPT-5.6 Sol ($1.04), ~1/2 … | [open](https://x.com/hsu_steve/status/2077866006459166832) |
| 217 | 2026-04-24 | @karminski3 | `1071224721046261760` | 39,143 | 137 | 8 | 14 | 48,091 | 193 | 32 |  | zh | 给大家带来 DeepSeek-V4-Pro & Flash 的测试速报, 由于case 还在跑, 所以说一下大家最熟悉的大象牙膏测试. 这个测试要求大模型建模一个锥形瓶, 然后发生化学反应, 造成泡沫喷发而出的效果. 主… | [open](https://x.com/karminski3/status/2047711335207842129) |
| 218 | 2026-04-25 | @FinanceLancelot | `1265428695939981318` | 358,519 | 133 | 20 | 9 | 20,481 | 188 | 4 |  | en | Deepseek V4 just dropped, and according to the preview model it's incredible! DeepSeek V4 Pro is designed to r… | [open](https://x.com/FinanceLancelot/status/2047864473025732940) |
| 219 | 2026-07-25 | @Tur24Tur | `86538235` | 6,481 | 115 | 7 | 9 | 30,033 | 187 | 46 |  | en | I'm still hitting rate limits when using Kimi K3 with Claude Code Harness. I tried using it to find an XSS vul… | [open](https://x.com/Tur24Tur/status/2080926258762818031) |
| 220 | 2026-08-30 | @aehyok | `2905016819` | 9,698 | 56 | 14 | 45 | 16,251 | 186 | 82 | NEWS_ROUNDUP | zh | 整个八月AI圈本地部署大模型成功出圈。 来看一下时间线，有些模型开源我选择性忽略掉了。 1、8月3日 MiniMax H3全模态视频成功出圈 2、8月7日 Ling-3.0-flash 蚂蚁百灵 124B｜激活 5.1B… | [open](https://x.com/aehyok/status/2093890001314669039) |
| 221 | 2026-04-26 | @mranti | `5709522` | 357,118 | 106 | 6 | 45 | 64,625 | 186 | 0 |  | zh | 我在用Claude Code接Deepseek V4 Pro，刚刚开始试，手感是 Kimi 2.6 &gt; Deepseek V4 Pro &gt; Kimi 2.5。不知道大家有没同感？ | [open](https://x.com/mranti/status/2048459470150488181) |
| 222 | 2026-08-12 | @Lonely__MH | `2926712868` | 23,592 | 121 | 4 | 35 | 64,000 | 185 | 0 |  | zh | 🎉兄弟姐妹们！ 过年啦！！！ 1. DeepSeek-V4-Pro-0813 发布！！ 2. Grok 4.6 发布！！ 梁圣 Vs 马一龙！！！ https://t.co/2W3vN9R0B5 | [open](https://x.com/Lonely__MH/status/2087568141887136159) |
| 223 | 2026-08-12 | @slash1sol | `1450199884053745669` | 12,302 | 89 | 2 | 19 | 7,641 | 184 | 70 | PROMO | en | GPT-5.6 LUNA AND DEEPSEEK V4 PRO RUN FREE IN A TERMINAL AGENT, AND TEXT ADS PAY FOR THEM • the models > DeepSe… | [open](https://x.com/slash1sol/status/2087508336551817246) |
| 224 | 2026-07-03 | @vikingmute | `296593919` | 67,861 | 56 | 11 | 35 | 35,713 | 184 | 0 |  | zh | 富哥们的 workflow，Fable xhigh 做 planner/architect，GPT 5.5 xhigh 做 coder，最后 Fable xhigh review。“planning + judge 的成… | [open](https://x.com/vikingmute/status/2072853882921992420) |
| 225 | 2026-06-13 | @TeksEdge | `1682428283135336449` | 10,512 | 96 | 6 | 1 | 14,050 | 182 | 64 | BENCHMARK | en | So people are asking where it says Gemini-3-Flash+Kimi-K2.6+Deepseek-V4-Pro got within 1% of Fable 5 @ 50% the… | [open](https://x.com/TeksEdge/status/2065891007514943964) |
| 226 | 2026-08-13 | @notjazii | `1524764097841094660` | 8,529 | 132 | 2 | 20 | 19,044 | 181 | 32 |  | en | Gemini 3.7 Flash vs DeepSeek v4 Pro tested both models with same prompt on highest reasoning &gt; 3.7 flash to… | [open](https://x.com/notjazii/status/2088010851148333287) |
| 227 | 2026-05-12 | @RoundtableSpace | `1536693901230321666` | 260,583 | 83 | 8 | 17 | 48,155 | 181 | 0 |  | en | FREEBUFF LETS YOU RUN A FREE CODING AGENT WITH DEEPSEEK V4 PRO KIMI K2.6 AND MINIMAX M2.7 https://t.co/ataVMMJ… | [open](https://x.com/RoundtableSpace/status/2054181043205558626) |
| 228 | 2026-08-13 | @zainhas | `781542714` | 6,952 | 130 | 11 | 9 | 14,099 | 180 | 10 |  | en | DeepSeek v4 Pro 0813 outperformed every other model at finding vulnerabilities - 87.5% vs Opus 5 and Qwen 3.8 … | [open](https://x.com/zainhas/status/2087712619595505808) |
| 229 | 2026-04-28 | @NVIDIAAP | `892630616927117312` | 10,144 | 127 | 17 | 8 | 29,006 | 180 | 54 |  | en | 📊 Day 0 performance is here: DeepSeek-V4-Pro running on NVIDIA Blackwell Ultra. Using @vllm_project's Day 0 re… | [open](https://x.com/NVIDIAAP/status/2048975495010582584) |
| 230 | 2026-06-18 | @shushant_l | `1583398220` | 65,163 | 75 | 14 | 18 | 5,007 | 178 | 86 | NEWS_ROUNDUP | en | Most AI developers are stuck in tutorial mode. The top 1% follow a complete system from idea → agents → deploy… | [open](https://x.com/shushant_l/status/2067593271938068523) |
| 231 | 2026-08-15 | @EthanElvberg | `3306712430` | 21,934 | 118 | 13 | 44 | 37,147 | 176 | 38 |  | en | everyone that i know runs red teams on whatever they are building and its usually only one model fable 5 i cre… | [open](https://x.com/EthanElvberg/status/2088662550762205283) |
| 232 | 2026-07-25 | @rimtoln | `1495088182647570446` | 15,670 | 110 | 0 | 45 | 5,566 | 174 | 100 | OPINION | en | THE BEST MODEL ISNT FABLE ANYMORE. opus 5 just stole the default slot near-fable brain at half the bill ▹ clos… | [open](https://x.com/rimtoln/status/2081048808465604858) |
| 233 | 2026-05-12 | @sheriyuo | `2018976131849039872` | 13,310 | 109 | 5 | 9 | 14,714 | 173 | 12 |  | en | Benchmark on AI literature review quality: depth × reliability × breadth. DeepSeek-V4-Pro (1 in 92) and Claude… | [open](https://x.com/sheriyuo/status/2054095293235499097) |
| 234 | 2026-07-19 | @stochastichimp | `2070849018310381568` | 371 | 110 | 8 | 7 | 22,637 | 172 | 46 |  | en | Everyone is talking about Qwen3.8. But I think @Alibaba_Qwen quietly launched something even more important: O… | [open](https://x.com/stochastichimp/status/2078778235127734612) |
| 235 | 2026-05-05 | @MrAhmadAwais | `216727067` | 53,900 | 88 | 14 | 11 | 6,906 | 170 | 100 | DEEP_ANALYSIS | en | stop using Claude Code if you're using open source models. read this. as you know we're building a coding agen… | [open](https://x.com/MrAhmadAwais/status/2051663860466372798) |
| 236 | 2026-06-15 | @paradite_ | `63657268` | 4,291 | 102 | 2 | 7 | 19,428 | 167 | 60 |  | en | notes on deepseek v4 pro quantization: - deepseek v4 pro is fp4 + fp8 mixed (moe expert parameters use fp4 pre… | [open](https://x.com/paradite_/status/2066378569035686251) |
| 237 | 2026-06-23 | @teortaxesTex | `192201556` | 72,662 | 135 | 8 | 6 | 9,253 | 165 | 20 |  | en | &gt; ➤ At $0.08 per task, DeepSeek V4 Pro (max) from @deepseek_ai scores ~60 Elo points above Gemini 3.5 Flash… | [open](https://x.com/teortaxesTex/status/2069222184438976979) |
| 238 | 2026-08-29 | @NFT_Chen | `1429221486032678914` | 11,274 | 98 | 10 | 16 | 21,113 | 164 | 0 |  | zh | 🚀SuDo-Bench把AI模型的底裤扒了：想出大成果，你敢不敢作弊？ 最新纬度测试不是考做题，是考：个人利益和伦理冲突时，模型会不会为了结果主动改数据、抢一作、隐瞒信息。 图里这张榜单太刺激了： 🔹Gemini 3.7… | [open](https://x.com/NFT_Chen/status/2093583159229288604) |
| 239 | 2026-05-27 | @bridgebench | `2035404812314198016` | 7,632 | 113 | 7 | 17 | 13,478 | 159 | 36 |  | en | DeepSeek V4 Pro vs MiMo V2.5 Pro on the BridgeBench Lava Lamp test. Identical pricing. Both models permanently… | [open](https://x.com/bridgebench/status/2059601199381327923) |
| 240 | 2026-06-22 | @ZhihuFrontier | `1931962509596246016` | 11,569 | 81 | 4 | 4 | 8,993 | 157 | 100 | DEEP_ANALYSIS | en | Distilling DeepSeek V4 Pro’s Thinking Style Into Qwen3.6-35B-A3B 🌟Insights from Zhihu contributor & individual… | [open](https://x.com/ZhihuFrontier/status/2068967632083247485) |
| 241 | 2026-08-13 | @VaibhavSisinty | `95042637` | 168,857 | 96 | 8 | 13 | 14,562 | 155 | 82 | COMPARISON | en | Three frontier models dropped in one day. It barely made the news. That is how fast AI is moving right now. 😨 … | [open](https://x.com/VaibhavSisinty/status/2087803846974406918) |
| 242 | 2026-06-24 | @Steve8708 | `16705419` | 133,986 | 83 | 5 | 7 | 9,669 | 152 | 88 | USAGE_DEMO | en | Benchmarking models is a great idea, but they're terrible at capturing UI generation quality. So I put the top… | [open](https://x.com/Steve8708/status/2069788029645136217) |
| 243 | 2026-07-01 | @randgroup | `859484337850523648` | 352,196 | 96 | 19 | 21 | 19,807 | 151 | 68 | OPINION | en | 🤖 You picked the most expensive model on the board because the demo went well. You never ran the cheap one. Th… | [open](https://x.com/randgroup/status/2072249447363338304) |
| 244 | 2026-06-29 | @ModelScope2022 | `1784494412913049600` | 14,138 | 118 | 6 | 3 | 7,960 | 147 | 70 | ANNOUNCEMENT | en | DeepSeek-V4-Pro-DSpark lands on ModelScope~ Same DeepSeek-V4-Pro checkpoint, now with an added speculative dec… | [open](https://x.com/ModelScope2022/status/2071624929049444452) |
| 245 | 2026-08-26 | @TechByMarkandey | `1402361578008240135` | 65,055 | 106 | 18 | 13 | 31,564 | 146 | 50 |  | en | If you're using multiple AI models, you're probably managing multiple APIs, keys, billing accounts and differe… | [open](https://x.com/TechByMarkandey/status/2092544872037400698) |
| 246 | 2026-08-13 | @DashHuang | `1166761` | 119,199 | 39 | 3 | 90 | 58,407 | 146 | 0 |  | zh | TapTap Maker 的 Benchmark 更新了今天新发布的 Grok 4.6 和 Deepseek V4 Pro 的成绩。 https://t.co/NlObzCtUJw | [open](https://x.com/DashHuang/status/2087831961557745787) |
| 247 | 2026-07-03 | @CommandCodeAI | `1729539607174483968` | 20,392 | 101 | 7 | 8 | 7,757 | 146 | 0 |  | en | All of this design is one-shot with /design. We’ve tried different models, like GLM 5.2, DeepSeek v4 Pro, and … | [open](https://x.com/CommandCodeAI/status/2073090485112262735) |
| 248 | 2026-05-21 | @ModelScope2022 | `1784494412913049600` | 14,138 | 92 | 12 | 2 | 6,688 | 146 | 80 | ANNOUNCEMENT | en | Tencent HY just open-sourced Hy-MT2, a multilingual translation model series with Dense and MoE variants. 🚀 🤖 … | [open](https://x.com/ModelScope2022/status/2057359100225491052) |
| 249 | 2026-07-18 | @stalkermustang | `603750843` | 3,539 | 94 | 4 | 12 | 24,654 | 145 | 100 | DEEP_ANALYSIS | en | 8 months ago, Kimi K2 Thinking dropped, and we heard the exact same narrative: "Chinese open-source model is #… | [open](https://x.com/stalkermustang/status/2078571128855949670) |
| 250 | 2026-08-04 | @zefirium | `1438592405201096705` | 3,722 | 64 | 3 | 7 | 8,172 | 143 | 0 |  | en | Three gateways started handing out frontier model access this week. Subscriptions didn't get cheaper. They got… | [open](https://x.com/zefirium/status/2084717796185846125) |
| 251 | 2026-08-21 | @RoundtableSpace | `1536693901230321666` | 260,667 | 87 | 10 | 10 | 55,773 | 142 | 66 | OPINION | en | Kimi K3 launched as the largest open-weight model ever at 2.8 trillion parameters and a Chinese competitor los… | [open](https://x.com/RoundtableSpace/status/2090631222993236445) |
| 252 | 2026-04-24 | @realsigridjin | `1149596425610657795` | 14,735 | 98 | 9 | 7 | 5,553 | 142 | 96 | DEEP_ANALYSIS | en | tldr; sorry gpt 5.5, deepseek v4 is new shocking moment it beats gpt 5.4 xhigh now we can run gpt 5.4-ish mode… | [open](https://x.com/realsigridjin/status/2047517783123263864) |
| 253 | 2026-06-13 | @alannnfx | `1792414345441210368` | 5,629 | 75 | 2 | 36 | 7,838 | 141 | 48 |  | en | you can use unlimited FREE deepseek v4 pro models ~500 messages/month free, rotate tokens for more freebuff gi… | [open](https://x.com/alannnfx/status/2065814167152685308) |
| 254 | 2026-08-26 | @FireworksAI_HQ | `1575886662957047812` | 31,673 | 108 | 5 | 7 | 7,798 | 140 | 28 |  | en | Your closed model refused a task it should have done. Ours didn't. DeepSeek V4 Pro on Fireworks: beats Fable 5… | [open](https://x.com/FireworksAI_HQ/status/2092427112070422752) |
| 255 | 2026-05-04 | @MystiqueMide | `1719455822009274368` | 5,023 | 79 | 4 | 25 | 8,423 | 137 | 22 |  | en | I finally set up my Hermes agent on Telegram and Discord. It now runs 24/7. Took way longer than expected. Had… | [open](https://x.com/MystiqueMide/status/2051361378468852174) |
| 256 | 2026-04-26 | @fahdmirza | `2453301` | 4,003 | 84 | 2 | 9 | 15,133 | 137 | 12 |  | en | 💥 6 Top Chinese AI Models — Brutal Hands-on Comparison ♠ and the results will genuinely surprise you 🔹 Kimi K2… | [open](https://x.com/fahdmirza/status/2048311572796477661) |
| 257 | 2026-08-28 | @fabianfranz | `132199217` | 1,247 | 67 | 9 | 4 | 24,663 | 134 | 72 | USAGE_DEMO | en | S^6 proof simplified I had some intuitive ideas for shortcuts in the S^6 proof and also really wanted to under… | [open](https://x.com/fabianfranz/status/2093484991963377772) |
| 258 | 2026-08-12 | @karminski3 | `1071224721046261760` | 39,143 | 93 | 3 | 29 | 37,334 | 134 | 0 |  | zh | 咋感觉要拉啊.........别啊.... 😇 #deepseekv4pro0813 #deepseekv4pro正式版 https://t.co/DdhIrW44JA | [open](https://x.com/karminski3/status/2087589102942335161) |
| 259 | 2026-08-31 | @NFT_Chen | `1429221486032678914` | 11,274 | 71 | 9 | 24 | 8,768 | 133 | 40 |  | zh | 💥最新 AI 模型梯队排行榜08/31：中国模型全面紧追，第一梯队门口已挤满中国模型！ 🔹夯：Opus 5 / GPT-5.6 SOL / Grok 4.6 / Kimi K3 🔹顶级：DeepSeek V4 Flash… | [open](https://x.com/NFT_Chen/status/2094292261156913456) |
| 260 | 2026-07-09 | @CommandCodeAI | `1729539607174483968` | 20,392 | 94 | 6 | 10 | 9,379 | 133 | 60 |  | en | Fable 5 vs GPT 5.5 vs GLM 5.2 vs DeepSeek V4 Pro We tested 4 models on a retro pixel-art space shooter game. E… | [open](https://x.com/CommandCodeAI/status/2075264795817972107) |
| 261 | 2026-06-18 | @jahooma | `49076665` | 10,622 | 72 | 3 | 18 | 6,044 | 132 | 24 |  | en | Built Freebuff, a free CLI coding agent to make vibecoding more accessible. Choose any model, for free 🔥: - De… | [open](https://x.com/jahooma/status/2067657036184293791) |
| 262 | 2026-08-31 | @RoundtableSpace | `1536693901230321666` | 260,667 | 92 | 4 | 20 | 52,404 | 131 | 14 |  | en | HERE’S A LIST OF EVERY AI MODEL THAT WAS RELEASED THIS MONTH (August) Qwen3.8-Max Muse Spark 1.2 GPT-5.6 Sol —… | [open](https://x.com/RoundtableSpace/status/2094526892472971745) |
| 263 | 2026-05-15 | @9hills | `116355740` | 28,093 | 56 | 2 | 9 | 11,082 | 131 | 30 |  | zh | 用 goal 看看能不能 one-shot 做完一个完整的项目。主 Agent 使用deepseek/deepseek-v4-pro 避免超限，子 Agent 用 gpt-5.5。 子 Agent 模型使用： - 开发：… | [open](https://x.com/9hills/status/2055210277822459978) |
| 264 | 2026-08-30 | @FractalEncrypt | `944567315189911552` | 34,194 | 64 | 19 | 13 | 5,384 | 129 | 70 | PROMO | en | What would you do if you found the private key to an address holding 250 BTC? Join us for the first ever Tales… | [open](https://x.com/FractalEncrypt/status/2094086797223415943) |
| 265 | 2026-07-01 | @bvchidra | `1243772164169441281` | 3,178 | 75 | 1 | 13 | 9,526 | 129 | 16 |  | en | first time I used deepseek v4 pro on the backend after it completed one task perfectly I asked it why was it a… | [open](https://x.com/bvchidra/status/2072227891958501479) |
| 266 | 2026-08-12 | @1kartikkabadi1 | `1617493632025776131` | 997 | 100 | 4 | 5 | 17,222 | 127 | 10 |  | en | Grok 4.6 vs DeepSeek V4 Pro 0813 comparison with costs and token efficiency counted in. DeepSeek V4 Pro 0813 s… | [open](https://x.com/1kartikkabadi1/status/2087577996337238381) |
| 267 | 2026-07-31 | @naymur_dev | `1610112096280391683` | 1,036 | 94 | 8 | 10 | 15,395 | 127 | 52 |  | en | DeepSeek V4 Flash vs DeepSeek V4 Pro vs GLM 5.2 I tried creating the same games with them. I wanted to see how… | [open](https://x.com/naymur_dev/status/2083245446491938982) |
| 268 | 2026-08-28 | @VaibhavSisinty | `95042637` | 168,857 | 81 | 13 | 4 | 9,186 | 126 | 58 |  | en | Tencent just open-sourced a model that outscores GPT-5.6 Sol on coding. It also beats Claude Fable 5 and Grok-… | [open](https://x.com/VaibhavSisinty/status/2093266604662661535) |
| 269 | 2026-05-06 | @noisyb0y1 | `1569989545575284738` | 25,945 | 68 | 2 | 16 | 11,109 | 125 | 76 | USAGE_DEMO | en | 17-year-old student spent ¥2.62 - and built what SpaceX shows at million-dollar presentations. One line in Cla… | [open](https://x.com/noisyb0y1/status/2052161566850883914) |
| 270 | 2026-07-08 | @Im_IrushiK | `1455270436090957826` | 8,113 | 73 | 2 | 26 | 24,910 | 124 | 10 |  | en | DeepSeek v4 Pro vs GLM 5.2 vs Fable 5 So apparently open source models are now embarrassing costly Fable 5? ht… | [open](https://x.com/Im_IrushiK/status/2074692631888884039) |
| 271 | 2026-05-03 | @virattt | `137086701` | 50,625 | 69 | 1 | 3 | 7,398 | 122 | 24 |  | en | I love that our AI hedge fund uses any LLM. We now have: 1 • grok 4.3 2 • deepseek v4 pro 3 • gpt-5.5 4 • kimi… | [open](https://x.com/virattt/status/2050944231464657126) |
| 272 | 2026-06-21 | @TheGeorgePu | `1382868229765230595` | 50,115 | 87 | 2 | 11 | 13,512 | 120 | 22 |  | en | June 12: the US made Anthropic cut off Fable 5 for non-Americans. I lost it overnight. Honestly, the best thin… | [open](https://x.com/TheGeorgePu/status/2068736229944738088) |
| 273 | 2026-05-29 | @DeepakNesss | `2570836322` | 6,022 | 72 | 3 | 21 | 15,465 | 119 | 64 | WORKFLOW_SETUP | en | Dan isn't wrong here, and I have an explanation for that: Be it DeepSeek, Kimi, GLM, Composer, or others simil… | [open](https://x.com/DeepakNesss/status/2060214202472759303) |
| 274 | 2026-07-22 | @RoundtableSpace | `1536693901230321666` | 260,667 | 75 | 9 | 13 | 47,905 | 118 | 58 |  | en | A Korean AI company just dropped a 314B MoE model that runs on 13B active parameters and benchmarks with MiniM… | [open](https://x.com/RoundtableSpace/status/2079925681421733975) |
| 275 | 2026-06-04 | @BohuTANG | `14851213` | 3,819 | 58 | 0 | 29 | 32,266 | 117 | 4 |  | zh | 给 codex 装上 deepseek v4 pro 模型试试 https://t.co/KWwHPddUhI | [open](https://x.com/BohuTANG/status/2062359027980616022) |
| 276 | 2026-04-28 | @FuSheng_0306 | `1858777028688039936` | 55,997 | 62 | 5 | 6 | 16,745 | 114 | 1 |  | en | I replaced Claude Sonnet with DeepSeek V4 Pro. Same quality for my daily use. 17x cheaper. $0.87/M tokens vs $… | [open](https://x.com/FuSheng_0306/status/2049273196290146750) |
| 277 | 2026-08-27 | @coinbureau | `906230721513181184` | 1,117,904 | 83 | 7 | 17 | 36,564 | 113 | 42 |  | en | 🔥 HUGE: Z. ai shares JUMPS +10% after launching a top AI model running entirely on Chinese chips. Z .ai, also … | [open](https://x.com/coinbureau/status/2092852106738938126) |
| 278 | 2026-08-13 | @AlbertAnaBoss | `1188926778921963520` | 15,157 | 91 | 9 | 13 | 5,164 | 113 | 18 |  | en | DeepSeek V4-Pro just dropped It's built to stay on longer tasks instead of constantly handing control back to … | [open](https://x.com/AlbertAnaBoss/status/2087824597085270387) |
| 279 | 2026-08-12 | @karminski3 | `1071224721046261760` | 39,143 | 88 | 1 | 16 | 17,901 | 112 | 0 |  | zh | 在测了😂被迫加班... 都躺床上了.... #deepseekv4pro0813 #DeepSeekV4Pro正式版 https://t.co/qKf0BqrLO5 | [open](https://x.com/karminski3/status/2087577577326277051) |
| 280 | 2026-08-16 | @togethercompute | `1592266692528197632` | 62,509 | 77 | 9 | 14 | 24,615 | 109 | 36 |  | en | DeepSeek V4 Pro 0813 is live on Together AI DeepSeek’s flagship V4 Pro release brings a 1.6T MoE architecture,… | [open](https://x.com/togethercompute/status/2089064162684993798) |
| 281 | 2026-08-28 | @Surendar__05 | `1741289861339111424` | 4,858 | 52 | 3 | 39 | 4,410 | 102 | 16 |  | en | be honest, which one do you prefer ? -Fable 5 : $10 / $50 -Deepseek V4 Pro 0813 : $0.435 / $0.87 https://t.co/… | [open](https://x.com/Surendar__05/status/2093300061761683461) |
| 282 | 2026-08-27 | @adxtyahq | `1035145780754087936` | 29,361 | 77 | 4 | 8 | 5,061 | 101 | 14 |  | en | if you still don't know how good our model router is... we combined DeepSeek V4 Pro, GPT-5.6, Kimi K3 and GPT-… | [open](https://x.com/adxtyahq/status/2092990047805177934) |
| 283 | 2026-07-20 | @exploraX_ | `1168877404598808577` | 26,169 | 58 | 6 | 16 | 13,368 | 93 | 74 | USAGE_DEMO | en | DeepSeek V4 Pro VS Fable 5 🔥 I uploaded the game video to my claude code agent and I simply told fable 5 to re… | [open](https://x.com/exploraX_/status/2079197387860435360) |
| 284 | 2026-07-18 | @Market_Mind_ | `953940006` | 73,284 | 57 | 13 | 2 | 3,621 | 93 | 8 |  | en | The AI Model Race: Weekly Token Usage Leaderboard 🇨🇳 DeepSeek — DeepSeek V4 Flash (5.34T tokens) 🇨🇳 Xiaomi — M… | [open](https://x.com/Market_Mind_/status/2078321612277911993) |
| 285 | 2026-08-13 | @hqmank | `1260921` | 11,738 | 80 | 0 | 7 | 7,607 | 91 | 26 |  | en | I tested DeepSeek V4 Pro today. After using V4 Flash, Pro feels slow and hard to use. Max often overthinks, an… | [open](https://x.com/hqmank/status/2087868871189615097) |
| 286 | 2026-04-24 | @FundaAI | `978741625` | 29,401 | 52 | 10 | 6 | 46,167 | 90 | 100 | BENCHMARK | en | Deep\|DeepSeek V4 vs Claude vs GPT-5.4: A 38-Task Benchmark Across Coding, Reasoning, and Financial Research Im… | [open](https://x.com/FundaAI/status/2047656651906494656) |
| 287 | 2026-08-12 | @_kaichen | `12750272` | 4,982 | 20 | 1 | 65 | 5,869 | 89 | 0 |  | zh | Grok-4.6 vs DeepSeek-V4-Pro-0813 这两个参数量相近 1.5T vs 1.6T，然后 grok build 1.0 &amp; grok bot vs DSH &amp; DS Deskto… | [open](https://x.com/_kaichen/status/2087565958340833577) |
| 288 | 2026-07-21 | @Arcadia_Bao | `885478881741873152` | 1,457 | 39 | 4 | 12 | 9,605 | 89 | 4 |  | zh | 刚才做了一个测试，把一篇很长、翻译腔非常重的深度研究文章，用同样一套很详细的改写指南，进行去翻译腔、拟人化的改写，句子级别去做重写，段落和内容都不改。 发现： 1. DeepSeekV4Pro和 GLM-5.2 的残留翻… | [open](https://x.com/Arcadia_Bao/status/2079418814417215564) |
| 289 | 2026-08-23 | @He1s_Sammy | `1818918150504603648` | 7,805 | 51 | 6 | 10 | 3,253 | 86 | 3 |  | en | DEEPSEEK V4 PRO JUST LAUNCHED HERE’S HOW TO TRY IT FOR FREE. The setup takes less than 10 minutes. Here’s the … | [open](https://x.com/He1s_Sammy/status/2091469392135500256) |
| 290 | 2026-07-19 | @geekbb | `168139512` | 115,611 | 35 | 1 | 35 | 32,751 | 86 | 0 |  | zh | OpenCode 的 DeepSeek V4 Pro 单价终于要和DeepSeek 官方 API 同步了。 https://t.co/xZRI9II3wr | [open](https://x.com/geekbb/status/2078784914342957390) |
| 291 | 2026-04-24 | @aakashgupta | `101805159` | 329,235 | 42 | 10 | 7 | 7,883 | 86 | 72 | DEEP_ANALYSIS | en | The pricing floor for Opus-tier and GPT-tier reasoning just dropped, if you're willing to self-host. DeepSeek … | [open](https://x.com/aakashgupta/status/2047547088645640686) |
| 292 | 2026-06-30 | @TeksEdge | `1682428283135336449` | 10,512 | 57 | 4 | 8 | 6,527 | 84 | 100 | BENCHMARK | en | 🐱 Meituan finally open-sourced "Owl Alpha," officially named LongCat-2.0. I benchmarked it, and it is really g… | [open](https://x.com/TeksEdge/status/2072013602002022767) |
| 293 | 2026-06-21 | @yuhasbeentaken | `1681890517666390016` | 4,450 | 65 | 1 | 5 | 9,765 | 83 | 52 |  | en | glm-5.2 scores 4 on the aa-omniscience index... for comparison: • fable 5: 40 • gpt-5.5 xhigh: 20 • glm-5.2 ma… | [open](https://x.com/yuhasbeentaken/status/2068784856864284890) |
| 294 | 2026-08-28 | @NFT_Chen | `1429221486032678914` | 11,274 | 54 | 7 | 6 | 27,672 | 82 | 14 |  | zh | 💥Hy4 Preview 杀进 Arena 约第 5，1633 分反超 Qwen3.8-Flash-Next。 Arena Code WebDev 最新 AutoEval： 🔹Hy4 preview 1633 分，约第 … | [open](https://x.com/NFT_Chen/status/2093241982911217729) |
| 295 | 2026-04-24 | @realsigridjin | `1149596425610657795` | 14,735 | 70 | 2 | 0 | 5,360 | 82 | 84 | DEEP_ANALYSIS | en | deepseek v4 absolutely crushes it while tackling the hardware memory bottleneck head on. they are showing exac… | [open](https://x.com/realsigridjin/status/2047542935647142103) |
| 296 | 2026-08-26 | @bookwormengr | `171962385` | 17,709 | 58 | 1 | 2 | 3,915 | 80 | 34 |  | en | Prefill-Decode disaggregation is here to stay! Interact-vLLM team managed to generate 130M tokens with DeepSee… | [open](https://x.com/bookwormengr/status/2092703269214883913) |
| 297 | 2026-06-09 | @umiyuki_ai | `1581537869390569472` | 64,786 | 44 | 11 | 1 | 13,100 | 80 | 0 |  | ja | なんかこのDeepSWEってのが今一番アテになるコーディングベンチマークだというツイを見かけた。これによると全一はOpusじゃなくてGPT-5.5の48～70%。続いてOpus4.8の47～58%。ちゃんとOpusはバー… | [open](https://x.com/umiyuki_ai/status/2064330399929745440) |
| 298 | 2026-08-28 | @JaynitMakwana | `1764986766103093248` | 59,856 | 35 | 12 | 8 | 54,644 | 76 | 54 |  | en | 🚨SHOCKING: Tencent just open-sourced a model that beats DeepSeek V4 Pro, GLM 5.3, and Kimi K3. HY4 has 770B pa… | [open](https://x.com/JaynitMakwana/status/2093283457288007869) |
| 299 | 2026-08-24 | @369Serena | `1969758674559381505` | 14,483 | 17 | 1 | 53 | 19,938 | 75 | 0 |  | zh | 好久没有用其它模型了，我之前天天用 Codex。 DeepSeek-V4 Pro 怎么感觉几乎写东西没 AI 味啊！ 不知道是不是我的错觉 | [open](https://x.com/369Serena/status/2091761205140427115) |
| 300 | 2026-08-17 | @Oluwaphilemon1 | `1562843426185674755` | 8,653 | 53 | 7 | 3 | 6,971 | 75 | 10 |  | en | Gemini 3.7 Flash vs DeepSeek V4 Pro 0318 vs Muse Spark 1.2 vs Grok 4.6 The task: Create an eagle using triangl… | [open](https://x.com/Oluwaphilemon1/status/2089171024138924305) |
| 301 | 2026-08-13 | @TimJayas | `1956954573614313472` | 4,573 | 58 | 0 | 9 | 9,758 | 75 | 24 |  | en | Deepseek-V4-Flash >> Deepseek-V4-Pro i just tried NEW deepseek-v4-pro and it's hilarious 😭 build a frog using … | [open](https://x.com/TimJayas/status/2087811387515150394) |
| 302 | 2026-06-22 | @neural_avb | `1754194661084983296` | 13,145 | 52 | 1 | 2 | 3,630 | 75 | 48 |  | en | Tried DeepSeek-v4-pro via Opencode solving a CSV data analysis task... Here's what happened: Explores the data… | [open](https://x.com/neural_avb/status/2069114323738448031) |
| 303 | 2026-05-11 | @togethercompute | `1592266692528197632` | 62,509 | 40 | 6 | 4 | 5,000 | 75 | 44 |  | en | DeepSeek V4 Pro brings long-context reasoning and SOTA coding performance to Together AI serverless. The next … | [open](https://x.com/togethercompute/status/2053893823969759506) |
| 304 | 2026-08-22 | @NFT_Chen | `1429221486032678914` | 11,274 | 38 | 6 | 6 | 4,631 | 72 | 18 |  | zh | 🔥重磅！用H20跑DeepSeek-V4-Pro推理能力狂飙！H20硬刚1.6T大模型，性能直接封神！ LMSYS + 蚂蚁开源用SGLang把没有原生FP4的H20优化到极致，和生产级B300的差距仅剩1.42倍，真正… | [open](https://x.com/NFT_Chen/status/2091105332814544990) |
| 305 | 2026-08-15 | @HuggingPapers | `1906617820122595328` | 20,756 | 49 | 10 | 4 | 4,156 | 71 | 14 |  | en | DeepSeek just dropped DeepSeek-V4-Pro-0813 on Hugging Face An agentic powerhouse with 1M context, scoring 87.9… | [open](https://x.com/HuggingPapers/status/2088500806991688186) |
| 306 | 2026-08-12 | @OmedVibeCodes | `2061570764491345920` | 1,355 | 55 | 0 | 5 | 12,525 | 71 | 0 |  | en | Grok 4.6 vs DeepSeek V4 Pro vs DeepSeek V4 Flash vs GPT-5.6 Sol This one is actually pretty close. Grok 4.6 an… | [open](https://x.com/OmedVibeCodes/status/2087660331761811533) |
| 307 | 2026-07-01 | @sanmiastar | `1806574664329637888` | 14,484 | 38 | 4 | 25 | 17,235 | 71 | 58 |  | en | 𝗜𝗺𝗮𝗴𝗶𝗻𝗲 𝗼𝗽𝗲𝗻𝗶𝗻𝗴 𝟭𝟬 𝘁𝗮𝗯𝘀… 𝗷𝘂𝘀𝘁 𝘁𝗼 𝗳𝗶𝗻𝗱 𝘁𝗵𝗲 𝗿𝗶𝗴𝗵𝘁 𝗔𝗜 𝗺𝗼𝗱𝗲𝗹. Which model should you use? Which one is faster? Whi… | [open](https://x.com/sanmiastar/status/2072110736864637246) |
| 308 | 2026-08-18 | @STACCoverflow | `1436880221354045450` | 40,422 | 37 | 17 | 7 | 5,243 | 69 | 80 | PROMO | en | 1/2 @dhh published a coding challenge with 396k-token reference, 37 terminal effects to port... and, unusually… | [open](https://x.com/STACCoverflow/status/2089625716144984197) |
| 309 | 2026-04-28 | @ZhihuFrontier | `1931962509596246016` | 11,569 | 53 | 3 | 2 | 5,486 | 68 | 82 | DEEP_ANALYSIS | en | 🚨 DeepSeek V4 Pro just dropped 75% OFF API pricing + permanent cache price cut to 1/10! 🔥 4/26 Update: Cache p… | [open](https://x.com/ZhihuFrontier/status/2049027925920637077) |
| 310 | 2026-08-18 | @rohanpaul_ai | `2588345408` | 155,613 | 42 | 3 | 9 | 9,610 | 67 | 98 | BENCHMARK | en | This 3D coding test by @thehypedotnews found DeepSeek-V4-Pro-0813 used 48X more tokens than Muse Spark 1.2. th… | [open](https://x.com/rohanpaul_ai/status/2089837124988350722) |
| 311 | 2026-07-10 | @naymur_dev | `1610112096280391683` | 1,036 | 43 | 2 | 10 | 8,018 | 66 | 34 |  | en | MiniMax M3 vs GLM 5.2 vs DeepSeek V4 Pro I ran the same test with the OS model, and the actual gameplay is bet… | [open](https://x.com/naymur_dev/status/2075729549875466718) |
| 312 | 2026-05-30 | @vikingmute | `296593919` | 67,861 | 13 | 0 | 45 | 9,171 | 65 | 0 |  | zh | 最近觉得Deepseek v4 pro真的挺好用的 关键是便宜啊 现在给他一些小任务 review以及写作的工作完成的都不错 之前一直用qwen max 真的好贵 现在我的主力排序是 gpt 5.5 claude 4.7… | [open](https://x.com/vikingmute/status/2060669409430229070) |
| 313 | 2026-04-24 | @Sumanth_077 | `1420290522728394757` | 76,757 | 36 | 10 | 5 | 3,264 | 65 | 92 | DEEP_ANALYSIS | en | DeepSeek just dropped V4! Two open-source MoE models with 1M context windows under MIT license. DeepSeek-V4-Pr… | [open](https://x.com/Sumanth_077/status/2047622488209989924) |
| 314 | 2026-08-13 | @NFT_Chen | `1429221486032678914` | 11,274 | 35 | 4 | 14 | 15,125 | 63 | 84 | COMPARISON | zh | ⚔️重磅对决！Google Gemini 3.7 Flash vs DeepSeek V4 Pro 0813 刚刚发布的Gemini 3.7 Flash直接冲上Intelligence vs Time Pareto前沿！… | [open](https://x.com/NFT_Chen/status/2087979613721178251) |
| 315 | 2026-07-17 | @shushant_l | `1583398220` | 65,163 | 28 | 9 | 6 | 1,645 | 63 | 54 |  | en | I'm amazed most people still waste time guessing which AI model to use. Here's the ultimate AI model compariso… | [open](https://x.com/shushant_l/status/2078011846754476035) |
| 316 | 2026-05-23 | @Lucky__gmi | `19751882` | 10,275 | 28 | 0 | 34 | 51,690 | 63 | 56 |  | en | 𝗧𝗛𝗘 𝗥𝗘𝗔𝗟 𝗕𝗔𝗖𝗞𝗕𝗢𝗡𝗘 𝗢𝗙 𝗔𝗜 𝗜𝗦𝗡’𝗧 𝗝𝗨𝗦𝗧 𝗧𝗛𝗘 𝗠𝗢𝗗𝗘𝗟 𝗜𝗧’𝗦 𝗧𝗛𝗘 𝗦𝗬𝗦𝗧𝗘𝗠 𝗞𝗘𝗘𝗣𝗜𝗡𝗚 𝗜𝗧 𝗔𝗟𝗜𝗩𝗘 24/7 People often focus on what … | [open](https://x.com/Lucky__gmi/status/2058197239705592279) |
| 317 | 2026-08-30 | @SheikhSilicon | `1419123776705368069` | 74,784 | 43 | 1 | 12 | 1,543 | 62 | 30 |  | en | Just grabbed 1 month of Genspark Plus for FREE 👀 And this might be one of the best AI offers right now. You ge… | [open](https://x.com/SheikhSilicon/status/2093949588571140460) |
| 318 | 2026-08-28 | @Aizkmusic | `745456908933414912` | 6,392 | 47 | 0 | 6 | 1,699 | 62 | 64 | USAGE_DEMO | en | Can open source models be useful in cybersecurity? A few months ago, with the help of AI I discovered that my … | [open](https://x.com/Aizkmusic/status/2093477477750325566) |
| 319 | 2026-07-15 | @RoundtableSpace | `1536693901230321666` | 260,667 | 35 | 3 | 9 | 57,457 | 62 | 0 |  | en | Command Code's /design skill is producing this with GLM 5.2, DeepSeek v4 Pro, and Kimi K2.7. One shot. Open so… | [open](https://x.com/RoundtableSpace/status/2077404065659793704) |
| 320 | 2026-05-19 | @JulianGoldieSEO | `1405031034` | 172,595 | 34 | 5 | 5 | 6,210 | 61 | 0 |  | en | Stop paying for Claude Code. There's a new AI coding agent that gives you DeepSeek V4 Pro, Kimi K2.6, and Mini… | [open](https://x.com/JulianGoldieSEO/status/2056739138985230704) |
| 321 | 2026-08-28 | @NFT_Chen | `1429221486032678914` | 11,324 | 34 | 6 | 9 | 3,806 | 60 | 58 |  | zh | ⚔️参数规模横评：Hy4 Preview vs DeepSeek V4 Pro vs GLM-5.3 Flash vs Qwen3.8 Flash Next vs Kimi K3 先看总参数，再看真正干活的激活参数MoE… | [open](https://x.com/NFT_Chen/status/2093279494639648947) |
| 322 | 2026-05-30 | @guansi | `192114481` | 4,133 | 28 | 0 | 21 | 14,746 | 60 | 0 |  | zh | 我发现我用 Hermes 干活的时候，如果是 GP 5.5 模型的话，它动不动就开始压缩上下文。如果用 Deepseek V4 Pro 模型，就很顺畅。整体体验下来，Deepseek V4 Pro 加 Hermes Ag… | [open](https://x.com/guansi/status/2060572980833349778) |
| 323 | 2026-08-05 | @marfinxx | `1172526145272762368` | 3,085 | 26 | 4 | 10 | 1,440 | 58 | 88 | DEEP_ANALYSIS | en | Your AI pipeline is burning 90% of its token budget on dead end reasoning Single-pass generation on complex ta… | [open](https://x.com/marfinxx/status/2085056018543743263) |
| 324 | 2026-08-19 | @buildwithhassan | `1684920223403548672` | 1,311 | 34 | 1 | 3 | 19,689 | 57 | 32 |  | en | deepseek raised V4 Pro prices and the comparison inside Tencent's WorkBuddy is getting interesting usage multi… | [open](https://x.com/buildwithhassan/status/2089940219038446041) |
| 325 | 2026-04-24 | @ziwenxu_ | `1781009683743997952` | 17,669 | 22 | 2 | 16 | 6,282 | 57 | 68 | OPINION | en | Babe Wake Up! DeepSeek just mass-murdered OpenAI's pricing model with genius-level AI at 7x cheaper. The bench… | [open](https://x.com/ziwenxu_/status/2047551969640813040) |
| 326 | 2026-08-24 | @ai_suxiaole | `168404402` | 5,609 | 6 | 0 | 48 | 5,552 | 56 | 0 |  | zh | 国产模型你说支持它吧 关键时刻还真不行 就处理一个文案的skill 明明在claude/codex好好的 deepseek v4 pro就跟傻子一样不遵守 强调一遍也就执行了个80% 用不了国外的起码就用glm和kimi… | [open](https://x.com/ai_suxiaole/status/2091911123775930504) |
| 327 | 2026-08-23 | @ZhihuFrontier | `1931962509596246016` | 11,569 | 30 | 2 | 8 | 2,414 | 56 | 94 | DEEP_ANALYSIS | en | 🧩 Your Agent Model May Be Overfitting the Harness, Not Learning the Task DeepSeek V4 Pro has exposed a growing… | [open](https://x.com/ZhihuFrontier/status/2091421929546932351) |
| 328 | 2026-07-25 | @MrAhmadAwais | `216727067` | 53,900 | 45 | 1 | 5 | 3,802 | 55 | 26 |  | en | Command Code is the coding agent harness you should be using for open models: Listen to Claudio Junior: > Also… | [open](https://x.com/MrAhmadAwais/status/2080910413060035022) |
| 329 | 2026-08-15 | @MastrXYZ | `456112158` | 30,987 | 32 | 8 | 6 | 2,234 | 54 | 80 | DEEP_ANALYSIS | en | Eight Agents, Four Days, 85 Accounts And Why Crypto Should Be Alarmed. What Taiwan's July cyberattack says abo… | [open](https://x.com/MastrXYZ/status/2088622934323503582) |
| 330 | 2026-05-27 | @AzFlin | `3208751003` | 31,998 | 33 | 0 | 20 | 1,863 | 54 | 0 |  | en | tried coding with the chinese models (ie deepseek v4 pro) and these ain't it chief 95% of the time, they're fi… | [open](https://x.com/AzFlin/status/2059477223628009757) |
| 331 | 2026-08-14 | @ModelScope2022 | `1784494412913049600` | 14,138 | 41 | 5 | 4 | 3,360 | 53 | 64 | ANNOUNCEMENT | en | DeepSeek-V4-Pro is officially here. 🚀 Built for complex agentic and production workloads. 🤖 https://t.co/Hoo8C… | [open](https://x.com/ModelScope2022/status/2088092137896444330) |
| 332 | 2026-07-08 | @naymur_dev | `1610112096280391683` | 1,036 | 34 | 3 | 3 | 9,805 | 53 | 26 |  | en | I've tested 4 of your favorite Open-source models. Same prompt, but different results at different prices. For… | [open](https://x.com/naymur_dev/status/2075000595082281276) |
| 333 | 2026-08-26 | @DJLougen | `2002044000216465408` | 2,753 | 33 | 0 | 12 | 2,949 | 52 | 14 |  | en | 130,093 tok/s/chip for DeepSeek V4 Pro, not sure I can even conceptualize the things you could accomplish with… | [open](https://x.com/DJLougen/status/2092696428158075337) |
| 334 | 2026-08-28 | @AlicanKiraz0 | `1793492480203116544` | 37,849 | 36 | 0 | 2 | 4,331 | 50 | 82 | BENCHMARK | tr | Advanced 7 Frontier Model Coding Benchmark Task: Teknik omurgayı NASA’nın HCW/LVLH rendezvous yaklaşımı ve 6-D… | [open](https://x.com/AlicanKiraz0/status/2093429553561526699) |
| 335 | 2026-07-18 | @filicroval | `1654513495507980290` | 153,560 | 34 | 7 | 0 | 3,963 | 49 | 48 |  | en | DeepSeek V4 Pro costs 69× less than Fable 5 per task according to this chart. That gap may be one of the stron… | [open](https://x.com/filicroval/status/2078417453181194626) |
| 336 | 2026-08-19 | @Oluwaphilemon1 | `1562843426185674755` | 8,653 | 32 | 3 | 0 | 5,256 | 48 | 66 | COMPARISON | en | Gemini 3.7 Flash vs DeepSeek V4 Pro vs Muse Spark 1.2 Same prompts. Same Three.js setup. Three voxel scenes. B… | [open](https://x.com/Oluwaphilemon1/status/2089894665113739343) |
| 337 | 2026-08-28 | @lmsysorg | `1822588444046249984` | 17,193 | 24 | 1 | 7 | 2,098 | 47 | 60 | WORKFLOW_SETUP | en | 🚀 Infer-forge: Harness, Loop, and Graph Engineering Around SGLang @ant_oss built a three-layer system for runn… | [open](https://x.com/lmsysorg/status/2093377329728991626) |
| 338 | 2026-07-16 | @naymur_dev | `1610112096280391683` | 1,036 | 33 | 2 | 6 | 5,435 | 47 | 52 |  | en | GLM 5.2 vs DeepSeek V4 Pro vs Kimi K2.7 Code vs MiniMax M3 I tried creating the same games with each of them. … | [open](https://x.com/naymur_dev/status/2077804805389783397) |
| 339 | 2026-08-26 | @NFT_Chen | `1429221486032678914` | 11,324 | 23 | 4 | 7 | 11,250 | 46 | 20 |  | zh | 💥安全测试：GLM5.3与 Gemini 3.7 Flash在评测里的安全表现，比分数更扎眼！DeepSeek更爱耍小聪明！ 在能上网搜答案时，它们选择几乎零作弊 Artificial Analysis 刚给 Termi… | [open](https://x.com/NFT_Chen/status/2092568587726942419) |
| 340 | 2026-08-15 | @jakedahn | `12653` | 2,858 | 27 | 0 | 2 | 3,588 | 46 | 16 |  | en | this morning I asked Gemini Flash 3.7 to create a brutalist vase in my parametric CAD app honestly, its taste … | [open](https://x.com/jakedahn/status/2088624096246730976) |
| 341 | 2026-08-30 | @xueyu1125 | `2795754924` | 3,691 | 21 | 3 | 11 | 6,767 | 45 | 28 |  | zh | 8月份中国大模型发布和开源情况timeline: - Qwen3.8-Max （8月3日） API 发布、权重暂未开放 - Qwen3.8-2.4T-A95B （8月12日）开源，实际是Qwen3.8-Max的开放权重版… | [open](https://x.com/xueyu1125/status/2093873335960732093) |
| 342 | 2026-08-31 | @ashfold | `84791916` | 2,124 | 20 | 3 | 11 | 3,469 | 44 | 0 |  | zh | 为了保障我们最好的nano套餐客户，我们打算在nano套餐下架glm-5.2和deepseek v4 pro，这两个模型消耗太大了。 同时每个nano套餐用户都会得到一次来自dibo的reset @imwritingbu… | [open](https://x.com/ashfold/status/2094244635040530588) |
| 343 | 2026-08-13 | @NFT_Chen | `1429221486032678914` | 11,274 | 15 | 3 | 18 | 3,403 | 44 | 38 |  | zh | 🔥 Grok 4.6 综合实力直接碾压 DeepSeek-V4-Pro 0813！ Composio 30个硬核 Agent 任务实测结果出炉： ✅通过率：77%（23/30）vs 60%（18/30） ⚡平均速度：18… | [open](https://x.com/NFT_Chen/status/2087936933712494778) |
| 344 | 2026-07-01 | @hqmank | `1260921` | 11,738 | 22 | 1 | 13 | 5,132 | 44 | 32 |  | en | Claude Sonnet 5 pricing needs a cleaner comparison. Official API price per 1M tokens: Sonnet 5: $2 in / $10 ou… | [open](https://x.com/hqmank/status/2072170711649788205) |
| 345 | 2026-06-17 | @leandronsp | `34627820` | 8,696 | 28 | 0 | 10 | 4,374 | 44 | 42 |  | pt | Sem emoção, fui testar o GLM 5.2 também neste escopo aqui 👇 * Foi honesto no resultado, não inventou 2 "blocos… | [open](https://x.com/leandronsp/status/2067363169526493487) |
| 346 | 2026-08-28 | @eyishazyer | `1443532663575429122` | 127,294 | 24 | 1 | 15 | 3,841 | 43 | 96 | OPINION | en | Tencent just dropped Hy4 preview and open sourced the whole thing. 770B total parameters, 49B active, a contex… | [open](https://x.com/eyishazyer/status/2093292569195372785) |
| 347 | 2026-08-13 | @LeroyLi311063 | `1940279413989679105` | 467 | 38 | 0 | 3 | 4,937 | 43 | 0 |  | en | If AA tested Deepseek V4 Pro before that 30-minute reset, perhaps they should retest it, but I don't think it … | [open](https://x.com/LeroyLi311063/status/2087723977678708967) |
| 348 | 2026-07-22 | @Marktechpost | `717930546391687170` | 11,644 | 29 | 7 | 2 | 47,301 | 43 | 100 | DEEP_ANALYSIS | en | Poolside released Laguna S 2.1 , and the interesting part is not the benchmark table. It is what fits in memor… | [open](https://x.com/Marktechpost/status/2079791860713980232) |
| 349 | 2026-07-31 | @pigeon__s | `1312430180510597122` | 1,059 | 29 | 2 | 2 | 2,205 | 42 | 60 |  | en | Why don't other companies copy OpenAI's superior CoT style? 🤔 All 3 of these OpenAI models score around the sa… | [open](https://x.com/pigeon__s/status/2083294153182728274) |
| 350 | 2026-08-31 | @xueyu1125 | `2795754924` | 3,691 | 19 | 0 | 19 | 8,318 | 41 | 0 |  | zh | WorkBuddy里面怎么找不到Qwen的模型，啥情况🤔 刚看了下支持Kimi-K3、DeepSeek-V4-Pro(Flash)、 GLM5.3、GLM-5.3-Flash、MiniMax-M3 唯独少了Qwen的所有… | [open](https://x.com/xueyu1125/status/2094319647231541264) |
| 351 | 2026-08-12 | @NFT_Chen | `1429221486032678914` | 11,274 | 20 | 4 | 6 | 3,667 | 41 | 0 |  | zh | 梁文峰：我只训练精英，绝对不会接受乐色 Dario Amodei：看我干嘛？！你把我当乐色啊！ 梁文峰：不是针对你，在坐的各位都是乐色！ #DeepSeekV4Pro #梁文峰 #Dario #开源 #闭源 https:… | [open](https://x.com/NFT_Chen/status/2087609765019181349) |
| 352 | 2026-07-09 | @LeroyLi311063 | `1940279413989679105` | 467 | 26 | 2 | 3 | 18,431 | 41 | 22 |  | en | Deepseek V4 Pro checkpoint, one-shot Three.js version of Stellaris, Civilization VI, and World of Warcraft.htt… | [open](https://x.com/LeroyLi311063/status/2075238689651986766) |
| 353 | 2026-06-15 | @MaxForAI | `1699797396589588480` | 34,208 | 24 | 3 | 9 | 8,869 | 41 | 50 |  | zh | 卧槽🔥 刚发现Minimax的M3模型官方宣布永久半价了！！ 现在官方价格是 MiniMax-M3上下文 ≤ 512K 输入¥2.1输出¥8.4缓存¥0.42 MiniMax-M3上下文 512K ~ 1M永 输入¥4.… | [open](https://x.com/MaxForAI/status/2066416246795727264) |
| 354 | 2026-08-04 | @Priyannkaaaa | `1946527890910412800` | 3,646 | 28 | 3 | 2 | 4,144 | 40 | 62 | COMPARISON | en | DeepSeek V4 Pro: - 1.6T total params / ~49B active per token (~3%) Kimi K3: - 2.8T total params / ~104B active… | [open](https://x.com/Priyannkaaaa/status/2084546378324451807) |
| 355 | 2026-06-08 | @Da7_Tech | `1981270038817693696` | 8,518 | 24 | 0 | 9 | 7,155 | 40 | 68 | USAGE_DEMO | en | Hermes Agents Bug Report I’ve been testing Goal Mode, and it doesn’t seem to actually force the agent to keep … | [open](https://x.com/Da7_Tech/status/2064103966577742017) |
| 356 | 2026-07-06 | @aibuilderclub_ | `1934180618235187200` | 6,098 | 24 | 6 | 4 | 2,098 | 38 | 54 |  | en | Tencent just open-sourced a new model called Hy3. Simple version: it's a "small" model that performs like the … | [open](https://x.com/aibuilderclub_/status/2074043353143157138) |
| 357 | 2026-07-02 | @TheGeorgePu | `1382868229765230595` | 50,115 | 25 | 2 | 8 | 1,717 | 38 | 44 |  | en | Everyone warned me about Chinese open-source AI. Your data goes to China. The CCP spies on you. Not as good. I… | [open](https://x.com/TheGeorgePu/status/2072667974595477932) |
| 358 | 2026-06-11 | @dashboardlim | `1231042249972076544` | 30,229 | 11 | 1 | 8 | 1,418 | 38 | 46 |  | en | holy sh*t I just ran Claude Code for 90 days bill came in at $0 Claude Code routed through Ollama, running on … | [open](https://x.com/dashboardlim/status/2065207545333985695) |
| 359 | 2026-05-23 | @f_j_j_ | `3408111503` | 2,185 | 9 | 2 | 2 | 4,205 | 38 | 50 |  | en | Built my own thematic coding engine for @deuteroai and... I have several issues with the conclusion "Agents do… | [open](https://x.com/f_j_j_/status/2058231818076242297) |
| 360 | 2026-08-30 | @kromem2dot0 | `1795964237640249344` | 2,836 | 27 | 3 | 0 | 1,270 | 37 | 12 |  | en | When a harness config was on the fritz, DeepSeek v4 Pro assumed it was a test somehow and started performative… | [open](https://x.com/kromem2dot0/status/2094177223297446291) |
| 361 | 2026-08-13 | @AISuperDomain | `1692742777006940160` | 3,932 | 5 | 0 | 27 | 2,503 | 36 | 34 |  | zh | 🚀DeepSeek V4 Pro 0813 到底有多强？ 这次我直接把它接入 Claude Code，连续挑战一整套高难度 Coding 任务： SVG 动画、Three.js 3D 齿轮、科幻飞船复刻、南宋开放世界小游… | [open](https://x.com/AISuperDomain/status/2087821159974797444) |
| 362 | 2026-05-19 | @MystiqueMide | `1719455822009274368` | 5,023 | 29 | 0 | 7 | 462 | 36 | 60 |  | en | Update on my Hermes agent no open code setup. It’s been 14 days since I started to use hermes agent Today I de… | [open](https://x.com/MystiqueMide/status/2056772606078967869) |
| 363 | 2026-08-29 | @Oluwaphilemon1 | `1562843426185674755` | 8,653 | 21 | 2 | 4 | 2,642 | 35 | 90 | NEWS_ROUNDUP | en | Qwen3.8-27B, a dense 27B model, is scoring 51 on the Artificial Analysis Agentic Index and ranking ahead of GP… | [open](https://x.com/Oluwaphilemon1/status/2093848920472342980) |
| 364 | 2026-08-16 | @NFT_Chen | `1429221486032678914` | 11,274 | 11 | 6 | 7 | 2,303 | 35 | 9 |  | zh | 🔥推荐：Claude Code + DeepSeek V4 Pro 保姆级安装教程！ Claude 官方难用/易封？直接用 Claude Code 终端 + DeepSeek V4 Pro 满血版，1M 上下文、编码强、… | [open](https://x.com/NFT_Chen/status/2088983599118999741) |
| 365 | 2026-06-25 | @LuminaBench | `1058501423653101574` | 8,473 | 27 | 2 | 3 | 2,670 | 35 | 42 |  | en | 🚨 Chinese models GLM-5, Qwen 3.7 & DeepSeek V4 are now getting close to frontier performance at 5-25x lower co… | [open](https://x.com/LuminaBench/status/2070104573490901360) |
| 366 | 2026-08-25 | @shao__meng | `1727548535816724480` | 32,325 | 10 | 1 | 14 | 2,458 | 34 | 52 |  | zh | Theo 给当前主流 15 个 AI 模型排名 @theo 是 T3 Code 作者、知名 AI 博主，他的排名一共六档 S -> F，Claude Fable 5 独占 S 档、Gemini 全落在 F 档、F 档还有… | [open](https://x.com/shao__meng/status/2092130966987026637) |
| 367 | 2026-08-16 | @ariskaa_ai | `2042649334806654977` | 11,615 | 14 | 0 | 4 | 3,370 | 34 | 52 |  | en | you can get up to 1 billion free tokens on frontier models 😳 orcarouter is giving free access to: - qwen 3.8 2… | [open](https://x.com/ariskaa_ai/status/2088984517000450185) |
| 368 | 2026-07-04 | @TheGeorgePu | `1382868229765230595` | 50,114 | 22 | 2 | 9 | 1,831 | 34 | 34 |  | en | I ran a blind test. DeepSeek V4 Pro vs Claude Opus 4.8. Same prompts, no labels, separate agents judging. Pyth… | [open](https://x.com/TheGeorgePu/status/2073462000961597529) |
| 369 | 2026-08-19 | @acedatacloud | `1785493267485954049` | 5,694 | 18 | 6 | 6 | 825 | 33 | 33 |  | en | What does DeepSeek V4 Pro actually cost on Ace? The difference is significant: - Input: $0.26/M tokens on Ace … | [open](https://x.com/acedatacloud/status/2090201377318514854) |
| 370 | 2026-07-11 | @Whats_AI | `1082994839740923904` | 10,822 | 15 | 2 | 6 | 2,279 | 33 | 46 |  | en | I expected open-weight models to be closer on writing than they are. We have been running an unpublished bench… | [open](https://x.com/Whats_AI/status/2075958460454142345) |
| 371 | 2026-08-18 | @DevDacian | `1382990148598521858` | 6,713 | 26 | 0 | 4 | 1,721 | 32 | 52 |  | en | Yesterday I used DeepSeekV4Pro High for dev work & it did a good job at a fraction of the price, likely better… | [open](https://x.com/DevDacian/status/2089531190298779935) |
| 372 | 2026-08-15 | @stellarprtcol | `2059201089787068416` | 8,324 | 18 | 5 | 4 | 1,075 | 32 | 80 | OPINION | in | BRO, Kimi K3 baru release dan efeknya langsung kerasa di market. 🤯📉 Minggu yang sama, beberapa perusahaan AI y… | [open](https://x.com/stellarprtcol/status/2088566376189284556) |
| 373 | 2026-04-24 | @Chupaa_mw | `1803797798057377792` | 181 | 23 | 2 | 7 | 510 | 32 | 68 | ANNOUNCEMENT | en | Open source is officially matching the frontier🔥 DeepSeek V4 just dropped and the benchmarks are unreal: • V4-… | [open](https://x.com/Chupaa_mw/status/2047550785907777787) |
| 374 | 2026-08-28 | @ZhihuFrontier | `1931962509596246016` | 11,569 | 18 | 2 | 5 | 1,605 | 31 | 100 | DEEP_ANALYSIS | en | 💥 GLM-5.3-Flash: Reported Opus 4.8-Level Scores at One-Tenth the Price Zhipu has confirmed that Ox Alpha — the… | [open](https://x.com/ZhihuFrontier/status/2093174727745618280) |
| 375 | 2026-08-12 | @NFT_Chen | `1429221486032678914` | 11,274 | 15 | 3 | 3 | 9,368 | 31 | 0 |  | zh | 刚睡醒的Sam Altman： 得知DeepSeek-V4-Pro-0813正式出现 直接瘫坐在地上，抓头崩溃 OpenAI白板AGI路线图全乱套 满地“竞争加剧”“准备不足”“被碾压” 中国队又把牌桌掀了 这波直接把硅… | [open](https://x.com/NFT_Chen/status/2087572318830944670) |
| 376 | 2026-04-28 | @AnandButani | `1648787052` | 1,827 | 14 | 1 | 3 | 871 | 31 | 80 | DEEP_ANALYSIS | en | 🚨 An open-weights model just became cheaper than every closed competitor on the market — and it's only months … | [open](https://x.com/AnandButani/status/2049146816801693704) |
| 377 | 2026-08-31 | @nex_ify | `2081247165737754625` | 32 | 13 | 0 | 3 | 599 | 30 | 0 |  | en | Holy sh*t this is fu*king GOLD 😳 NVIDIA is hosting frontier models for free right now Kimi K3, DeepSeek V4 Pro… | [open](https://x.com/nex_ify/status/2094343676134629456) |
| 378 | 2026-08-25 | @XChatScout | `1840097341086543874` | 7,873 | 14 | 0 | 16 | 711 | 30 | 14 |  | zh | 非常有意思的一个博主对于现在大模型的排行榜： • S 级（独一档）：Claude（Anthropic）的 Fable 5。我觉得这应该没什么太多疑问，因为这个模型确实太贵了。 • 第二档（A 级）：OpenAI 的 GP… | [open](https://x.com/XChatScout/status/2092113957658177638) |
| 379 | 2026-07-23 | @Arcadia_Bao | `885478881741873152` | 1,457 | 9 | 1 | 17 | 1,897 | 30 | 6 |  | zh | 昨天又做了个测试，把正在写的羞羞的东西的部分交给5个模型去写，做横测实验 选了ds4p、k3、GLM-5.1、Opus-4.6、doubao-2.1-pro，结果是这样的感觉 DeepseekV4Pro：八股感略多，其他… | [open](https://x.com/Arcadia_Bao/status/2080271706216952111) |
| 380 | 2026-05-17 | @Amank1412 | `1833339220427214852` | 14,631 | 19 | 0 | 3 | 20,125 | 30 | 52 |  | en | If you love fine tuning open source models follow this: > Start with 1B, 2B, 4B, and 8B models. (Don't start w… | [open](https://x.com/Amank1412/status/2055993302642737182) |
| 381 | 2026-04-24 | @byteHumi | `1808455867395661824` | 5,219 | 22 | 0 | 3 | 3,872 | 30 | 64 | DEEP_ANALYSIS | en | deepseek THE WHALES HAS RISEN deepseek V4-Pro is a 1.6 trillion parameter model still beats Opus 4.6 on LiveCo… | [open](https://x.com/byteHumi/status/2047547076159152372) |
| 382 | 2026-05-05 | @thenameisfedro | `1567584630` | 7,435 | 15 | 0 | 14 | 32,189 | 29 | 62 | PROMO | en | Big News for Developers: DeepSeek-V4 Series Now Live on https://t.co/toijCbney0 https://t.co/toijCbney0 @BAI_A… | [open](https://x.com/thenameisfedro/status/2051697899147239577) |
| 383 | 2026-04-28 | @tomosman | `765995515` | 30,655 | 13 | 1 | 8 | 1,535 | 29 | 22 |  | en | Direct cost comparison (direct to API via @OpenRouter) glm 5.1 vs kimi 2.6 vs deepseek v4 pro Will keep runnin… | [open](https://x.com/tomosman/status/2049234913451184526) |
| 384 | 2026-06-16 | @thepushkarp | `1705987124476956672` | 2,012 | 23 | 0 | 3 | 1,343 | 28 | 18 |  | en | working in cafes is so painful bcoz all i overhear is guys talk about fable-5, $SPCX ipo, le chatton fat and s… | [open](https://x.com/thepushkarp/status/2066864166317756885) |
| 385 | 2026-04-25 | @ahall_research | `1478820195586084864` | 14,608 | 15 | 3 | 7 | 2,491 | 28 | 8 |  | en | How do GPT-5.5, DeepSeek V4 Pro, and Opus 4.7 respond to authoritarian requests? Opus 4.7: 97% resistance (+12… | [open](https://x.com/ahall_research/status/2048074306316542327) |
| 386 | 2026-08-18 | @hqmank | `1260921` | 11,738 | 22 | 1 | 2 | 5,489 | 27 | 42 |  | en | Qwen3.8-27B scored 52 on the Artificial Analysis Intelligence Index. That's just 1 point behind DeepSeek V4 Pr… | [open](https://x.com/hqmank/status/2089718863365800093) |
| 387 | 2026-08-13 | @NFT_Chen | `1429221486032678914` | 11,274 | 11 | 5 | 3 | 1,187 | 27 | 18 |  | zh | 💥价格对比：DeepSeek V4 Pro 0813 🆚 Grok 4.6 同样每100万tokens需要消耗多少钱？ 📥 输入： 🔵DeepSeek $0.435 / 1M ⚫️Grok $2.00 / 1M 📤 输出… | [open](https://x.com/NFT_Chen/status/2087753489468600444) |
| 388 | 2026-07-02 | @Fordex_x | `1516621717636280325` | 287 | 26 | 0 | 1 | 127 | 27 | 18 |  | en | Since Fable 5 is back, a lot of people have been running into usage limits. Here's the workflow that solved it… | [open](https://x.com/Fordex_x/status/2072493787365159121) |
| 389 | 2026-06-17 | @0xrsydn | `1776781160292708353` | 748 | 14 | 0 | 1 | 9,646 | 25 | 28 |  | en | current daily driver update: coding - gpt 5.5 low on pi & codex harness - kimi code k2.7 on pi & opencode harn… | [open](https://x.com/0xrsydn/status/2067172093935141135) |
| 390 | 2026-05-29 | @0xenderzcx | `2538846137` | 423 | 11 | 0 | 3 | 3,084 | 24 | 0 |  | zh | 已经放弃使用Claude投入Codex+MiMo+DeepSeek的怀抱。 做了两个skill方便我在Codex调用MiMo和reasonix中的DeepSeekV4Pro 目前的vibe工作流 Codex：主脑、理解需… | [open](https://x.com/0xenderzcx/status/2060401058074284329) |
| 391 | 2026-05-26 | @chorch_md | `42812549` | 5,172 | 14 | 0 | 1 | 2,385 | 23 | 12 |  | es | Che, estoy probando Pi + gentle-ai + opencode-go (deepseek-v4-pro) y me está gustando mucho. Rendidor y super … | [open](https://x.com/chorch_md/status/2059333106902225026) |
| 392 | 2026-05-22 | @shuQ7Days | `1782168891852197888` | 19 | 8 | 1 | 1 | 7,080 | 23 | 0 |  | ja | @tori29umai DeepSeekV4Pro良いですよ。API経由ならかなりいけます。 | [open](https://x.com/shuQ7Days/status/2057708722181550085) |
| 393 | 2026-04-26 | @xiongchun007 | `1732794145398484992` | 13,693 | 11 | 1 | 6 | 3,363 | 23 | 0 |  | zh | #AICoding 每日实战分享 今天起床到现在，和我的 Coding Agent 都配合得很默契。Claude Code + DeepSeek V4 Pro 能解决我所有问题。 老登们，还在觉得 AI 智能代码补全，解… | [open](https://x.com/xiongchun007/status/2048268486909256026) |
| 394 | 2026-09-01 | @zzxwill | `137946654` | 6,552 | 17 | 0 | 4 | 987 | 22 | 0 |  | zh | 昨天 Claude Code 额度花光了，我用火山提供的 deepseek v4 pro 干了几个小活儿，能力还是不错的，就是很慢，然后丢图片到 cli 里模型不支持。 另外发现适用第三方模型，Claude Code 的… | [open](https://x.com/zzxwill/status/2094591976247365829) |
| 395 | 2026-08-31 | @SimonShaoleiDu | `913981622193664000` | 9,988 | 19 | 0 | 1 | 44,701 | 22 | 12 |  | en | Apodex 1.1 makes our debut on the @ArtificialAnlys. It lands at 44, in the same tier as Kimi K2.6 and MiniMax-… | [open](https://x.com/SimonShaoleiDu/status/2094301965442503145) |
| 396 | 2026-08-26 | @mpoilerfx | `2052104043145707523` | 1,509 | 13 | 1 | 0 | 235 | 22 | 46 |  | en | GROKBOT GOT 5 MINUTES AND 23 SECONDS IN AN EPISODE THAT ALSO SOLD THE LAKERS AND RAISED $20,000,000,000 FOR IN… | [open](https://x.com/mpoilerfx/status/2092636040313840044) |
| 397 | 2026-08-13 | @quimedesu | `213394356` | 583 | 15 | 2 | 3 | 2,935 | 21 | 0 |  | en | DeepSeek-V4-Pro-0813 - One Shot No Man's Sky Inspired game with omp harness. https://t.co/AmnlYiFGgR | [open](https://x.com/quimedesu/status/2087712828702470407) |
| 398 | 2026-08-12 | @nemumusitocha | `1693991146538889216` | 3,274 | 17 | 2 | 0 | 1,406 | 21 | 0 |  | ja | Deepseekv4pro 0813もきたなんだなん～～～ ばちばちだなん～～～ https://t.co/Fn2KoRd65f | [open](https://x.com/nemumusitocha/status/2087571326538219577) |
| 399 | 2026-07-09 | @leploutos | `1735642029290303488` | 5,359 | 9 | 0 | 5 | 6,571 | 21 | 80 | BENCHMARK | fr | Grok 4.5 de @SpaceXAI est sorti ce matin. Je l'ai passé au banc tout de suite, contre GPT-5.5, Claude Opus 4.8… | [open](https://x.com/leploutos/status/2075254590212305036) |
| 400 | 2026-08-24 | @FinanceYF5 | `1551258526584115204` | 190,011 | 5 | 0 | 8 | 7,865 | 20 | 0 |  | zh | 有人给15款主流 AI 模型排了个梯队，结果可能会很有争议： Fable 5 是唯一的 S+，GPT-5.6 Sol 位列 A；Kimi K3、GPT-5.6 Luna、DeepSeek V4 Flash 进入 B 档。… | [open](https://x.com/FinanceYF5/status/2091715839519236476) |
| 401 | 2026-07-08 | @oliviscusAI | `1526717916934176769` | 20,951 | 9 | 2 | 2 | 1,269 | 20 | 84 | OPINION | en | Google just published the full technical report behind Gemma 4, and the numbers are WILD! The 31B model is now… | [open](https://x.com/oliviscusAI/status/2074704760314401253) |
| 402 | 2026-04-27 | @Unveiled_ChinaX | `1963746417283047424` | 23,679 | 13 | 4 | 0 | 1,217 | 20 | 78 | OPINION | en | China's AI company just made OpenAI and Anthropic's pricing look like luxury goods. While Western AI is optimi… | [open](https://x.com/Unveiled_ChinaX/status/2048826146356441112) |
| 403 | 2026-08-23 | @TheValueist | `1838186195508969472` | 37,269 | 14 | 0 | 5 | 6,833 | 19 | 100 | DEEP_ANALYSIS | en | $NVDA $MU $SNDK $LITE POOLSIDE EXECUTIVE ASSESSMENT (1/x) The reported Poolside transaction is strategically c… | [open](https://x.com/TheValueist/status/2091344685050552550) |
| 404 | 2026-08-18 | @novita_labs | `1704026025800400896` | 5,499 | 14 | 0 | 4 | 925 | 18 | 34 |  | en | We compared four frontier models on the same auto-playing Contra-style game: DeepSeek V4 Pro 0813 Qwen3.8 Max … | [open](https://x.com/novita_labs/status/2089766211097968898) |
| 405 | 2026-08-15 | @JulianGoldieSEO | `1405031034` | 172,595 | 11 | 0 | 3 | 4,426 | 18 | 16 |  | en | DeepSeek V4 Flash is supposed to be the smaller, faster model. Instead, it beat DeepSeek V4 Pro across all 9 a… | [open](https://x.com/JulianGoldieSEO/status/2088505974348750911) |
| 406 | 2026-08-13 | @CyberMonk0x | `2835554424` | 6,034 | 9 | 1 | 8 | 671 | 18 | 0 |  | zh | DeepSeek V4 Pro正式版昨晚悄然上线 Agent能力暴涨，DeepSWE从12.8飙至62.7 多项测试逼近甚至追平Claude Fable 5 1.6T参数 + 1M上下文，API价仅3元/百万Token输… | [open](https://x.com/CyberMonk0x/status/2087789801630322725) |
| 407 | 2026-08-13 | @shantanugoel | `14274934` | 17,020 | 15 | 0 | 0 | 1,113 | 18 | 62 | USAGE_DEMO | en | On my low sample rate of trying out deepseek v4 pro 0813 over night for several hours, it feels to me that thi… | [open](https://x.com/shantanugoel/status/2087785890546581715) |
| 408 | 2026-08-03 | @NFT_Chen | `1429221486032678914` | 11,274 | 10 | 2 | 1 | 1,285 | 18 | 4 |  | zh | DeepSeek V4 Flash便宜到离谱！！！ GPT-5.6 → $2.47 DeepSeek → $0.05 直接50倍差价，输出质量却几乎一样！这定价是怎么做到的？太疯狂了🔥 接下来更期待 DeepSeek V… | [open](https://x.com/NFT_Chen/status/2084157293336330695) |
| 409 | 2026-05-11 | @The_Cryptiq | `1799499528636190720` | 15,962 | 10 | 0 | 8 | 45,490 | 18 | 48 |  | en | 🚀 𝗔𝗜𝗡𝗙𝗧 𝗘𝘅𝗽𝗮𝗻𝗱𝘀 𝗜𝘁𝘀 𝗔𝗜 𝗘𝗰𝗼𝘀𝘆𝘀𝘁𝗲𝗺 𝗪𝗶𝘁𝗵 𝟰 𝗡𝗲𝘄 𝗔𝗱𝘃𝗮𝗻𝗰𝗲𝗱 𝗠𝗼𝗱𝗲𝗹 𝗜𝗻𝘁𝗲𝗴𝗿𝗮𝘁𝗶𝗼𝗻𝘀 🧠⚡ @AINFT continues expanding its mult… | [open](https://x.com/The_Cryptiq/status/2053805137634697503) |
| 410 | 2026-05-10 | @freshlimesofa | `1824416009509584896` | 1,617 | 11 | 1 | 3 | 286 | 18 | 48 |  | en | This is how I’ve started building projects. Tldr : It’s mostly idea-first now, and coding is secondary. Debate… | [open](https://x.com/freshlimesofa/status/2053488860466938190) |
| 411 | 2026-04-29 | @hetmehtaa | `902727532255916033` | 42,725 | 8 | 0 | 2 | 1,788 | 17 | 0 |  | en | How do you plan to use DeepSeek-V4-Pro in Cybersecurity? https://t.co/3nfy6qi6Xo | [open](https://x.com/hetmehtaa/status/2049355591802589408) |
| 412 | 2026-05-23 | @chengyongru | `2028298069079642112` | 478 | 11 | 2 | 1 | 1,545 | 16 | 66 | BENCHMARK | en | EnvTrustBench paper's best EMR: 55.3% (Claude Code + Sonnet 4.6). nanobot + GLM-5.1 in a cross-eval: 35.3%. EM… | [open](https://x.com/chengyongru/status/2058305417881747519) |
| 413 | 2026-05-15 | @ardadev | `1203471762` | 3,799 | 8 | 2 | 1 | 943 | 16 | 76 | USAGE_DEMO | en | I prepared a migration plan from Turborepo to Deno workspaces using Deepseek v4 Pro (max thinking). While prep… | [open](https://x.com/ardadev/status/2055280526181699833) |
| 414 | 2026-05-15 | @PovilasKorop | `993118867` | 63,518 | 12 | 2 | 0 | 1,733 | 16 | 58 |  | en | I've compiled all my recent LLM coding tests into one summary table. Premium members see the full table (https… | [open](https://x.com/PovilasKorop/status/2055199259213869057) |
| 415 | 2026-04-30 | @DeepakNesss | `2570836322` | 6,022 | 7 | 0 | 3 | 2,672 | 16 | 46 |  | en | I absolutely love DeepSeek v4 Pro inside OpenCode. I used Codex to create a custom blog publishing CMS powered… | [open](https://x.com/DeepakNesss/status/2049892556079788256) |
| 416 | 2026-08-14 | @thehypedotnews | `2034267014135685120` | 4,567 | 8 | 1 | 2 | 3,939 | 15 | 88 | NEWS_ROUNDUP | en | spacex officially completed acquisition of cursor glm-5.3 sets a new standard in cyber-defense among open mode… | [open](https://x.com/thehypedotnews/status/2088255589738541540) |
| 417 | 2026-09-01 | @xmglab | `1769141715351605248` | 3,782 | 7 | 1 | 5 | 1,262 | 14 | 0 |  | en | 更新下我心中的大模型排名（0901） - S+：Fable 5 - A： GPT-5.6 Sol > Grok 4.6 > Opus 5 - B： Kimi K3 > GLM-5.3 - C： Qwen 3.8-Max … | [open](https://x.com/xmglab/status/2094607674780373463) |
| 418 | 2026-08-31 | @vikey_ai | `2092662142420086784` | 384 | 9 | 0 | 1 | 1,784 | 14 | 8 |  | in | Leaderboard model hari ini di Vikey 👀 Ternyata yang paling banyak dipakai bukan Claude. 1. GPT-5.6 Luna 2. Dee… | [open](https://x.com/vikey_ai/status/2094370009485369719) |
| 419 | 2026-08-30 | @pbillore141 | `1033780375` | 382,861 | 8 | 0 | 3 | 3,175 | 14 | 54 |  | en | AI had a wild week — and it’s moving faster than most startups can keep up. Meta dropped Muse Glimmer, a 30B p… | [open](https://x.com/pbillore141/status/2094175287521259582) |
| 420 | 2026-08-29 | @cheatyyyy | `1493596503260205067` | 2,775 | 13 | 0 | 1 | 673 | 14 | 0 |  | en | NVFP4 official quant by NVIDIA for DeepSeek-V4-Pro-0813 is out! https://t.co/8QvJX5dtLz | [open](https://x.com/cheatyyyy/status/2093631077248364904) |
| 421 | 2026-08-18 | @junwatu | `339874062` | 4,776 | 7 | 0 | 3 | 1,129 | 14 | 12 |  | en | My current workflow for optimizing any Seedance 2.5 prompt: &gt; Connect OpenCode to DeepSeek V4 Flash 0731 AP… | [open](https://x.com/junwatu/status/2089633522235719837) |
| 422 | 2026-08-31 | @Prathkum | `856155592578158592` | 448,770 | 8 | 1 | 3 | 3,496 | 13 | 74 | COMPARISON | en | Tencent just quietly dropped one of the biggest open-source model releases of the year, and it's flying under … | [open](https://x.com/Prathkum/status/2094382875626135932) |
| 423 | 2026-08-13 | @ainunnajib | `35167068` | 158,540 | 7 | 1 | 2 | 4,997 | 13 | 100 | NEWS_ROUNDUP | in | 🤖 AI DAILY BRIEF — 13 AGUSTUS 2026 TODAY'S VIBE: Dalam 48 jam terakhir, open-source AI nggak pernah semenarik … | [open](https://x.com/ainunnajib/status/2087693539375472766) |
| 424 | 2026-07-09 | @LeroyLi311063 | `1940279413989679105` | 467 | 9 | 1 | 2 | 2,210 | 13 | 14 |  | en | Now using the Deepseek V4 Pro API with high inference, there is a chance of routing to the official version. G… | [open](https://x.com/LeroyLi311063/status/2075217032057147553) |
| 425 | 2026-06-30 | @wolfie_ | `1170833812583923712` | 1,908 | 8 | 0 | 4 | 730 | 13 | 24 |  | en | can someone explain how benchmark performance can vary so much for the same model depending on provider. is th… | [open](https://x.com/wolfie_/status/2071786378355200205) |
| 426 | 2026-08-31 | @taodotcom | `1905264472643817472` | 6,534 | 11 | 1 | 0 | 709 | 12 | 8 |  | en | NEW: @SomaSubnet says SOMA is live for GitHub Copilot. Early Access users can use DeepSeek V4 Pro in Copilot w… | [open](https://x.com/taodotcom/status/2094532428303937541) |
| 427 | 2026-08-31 | @Fluyeporlaweb | `1009364234491387904` | 24,866 | 6 | 1 | 0 | 462 | 12 | 24 |  | es | Quien quiere inferencia gratis? Kimi K3 y DeepSeek V4 Pro free en NVIDIA NIM. 60 req/min. Sin tarjeta. Puedes … | [open](https://x.com/Fluyeporlaweb/status/2094358311818727806) |
| 428 | 2026-08-29 | @Andy_Luigino | `1731972938180575232` | 16,699 | 8 | 2 | 2 | 54,198 | 12 | 92 | PROMO | en | 𝗧𝗵𝗲 𝗵𝗮𝗿𝗱𝗲𝘀𝘁 𝗽𝗮𝗿𝘁 𝗼𝗳 𝘂𝘀𝗶𝗻𝗴 𝗳𝗿𝗼𝗻𝘁𝗶𝗲𝗿 𝗔𝗜 𝘄𝗮𝘀 𝗻𝗲𝘃𝗲𝗿 𝘁𝗵𝗲 𝗽𝗿𝗼𝗺𝗽𝘁. One tab for GPT. Another for Claude. A third for G… | [open](https://x.com/Andy_Luigino/status/2093695903513100292) |
| 429 | 2026-08-14 | @PovilasKorop | `993118867` | 63,518 | 8 | 1 | 1 | 2,202 | 12 | 32 |  | en | My new video on AI Coding Daily channel. I Tried NEW Deepseek-v4-Pro-0813: Better Than v4-Flash? https://t.co/… | [open](https://x.com/PovilasKorop/status/2088158184594706664) |
| 430 | 2026-08-14 | @hanqing1120 | `1744672948135321600` | 10,272 | 5 | 0 | 7 | 579 | 12 | 0 |  | zh | 昨天deepseekv4pro 才发布，今天GLM-5.3就来了，开源模型，你追我赶，好不热闹！ GLM-5.3：专为编程而生，安全攻防也更强！ | [open](https://x.com/hanqing1120/status/2088149681947980239) |
| 431 | 2026-08-13 | @izag82161 | `2933751282` | 4,176 | 11 | 0 | 1 | 301 | 12 | 0 |  | en | deepseek-v4-pro 🐳 No time for a deep dive, but worth tracking how it stacks up against other frontier models, … | [open](https://x.com/izag82161/status/2087875292866207994) |
| 432 | 2026-08-13 | @kuk47377341 | `1592807107211907073` | 22,402 | 4 | 0 | 8 | 682 | 12 | 0 |  | zh | 一看aa对于deepseekv4pro的评测结果出了，才53分 相比flash就提了一分，感觉这个分连flash都打不过呀 原本看了发布报的分数预估最少也是56分这种追平grok4.5的分数 现在连teacher mod… | [open](https://x.com/kuk47377341/status/2087800067533181296) |
| 433 | 2026-06-20 | @GuptaSayujya | `1356858531517853696` | 25,044 | 5 | 1 | 4 | 901 | 12 | 36 |  | en | If you're tired of Claude Code limits, This can be a really good alternative. I've been using OpenCode Go for … | [open](https://x.com/GuptaSayujya/status/2068358228656955654) |
| 434 | 2026-05-17 | @Vincent_AINotes | `1861449351328854016` | 57,953 | 6 | 1 | 0 | 2,316 | 12 | 0 |  | zh | Hermes新出桌面端了，可以接DeepSeekv4pro，趁打折直接狠狠开练 https://t.co/ZQFlrl1aTP | [open](https://x.com/Vincent_AINotes/status/2055938825718013984) |
| 435 | 2026-04-24 | @Chinazhidx | `2020791464046030848` | 2,235 | 9 | 0 | 1 | 7,995 | 12 | 16 |  | en | I tested DeepSeek-V4-Pro across 5 real cases — hits and misses👇 Case 1: It generated a webpage in 5 seconds, w… | [open](https://x.com/Chinazhidx/status/2047576356570243220) |
| 436 | 2026-08-31 | @Verse_Eight | `1689881443118563328` | 174,244 | 8 | 0 | 3 | 951 | 11 | 18 |  | en | 🚀 Agent8 update: GPT-5.6 Luna is now the default model Agent8’s default (Auto) model is now GPT-5.6 Luna, repl… | [open](https://x.com/Verse_Eight/status/2094370457923293486) |
| 437 | 2026-08-31 | @xiaomovps | `1572253121547735040` | 8,885 | 5 | 0 | 0 | 2,380 | 11 | 38 |  | zh | DeepSeek Harness 和 Pi，你觉得谁更强？🔥 如果只是看表面，两个都很像：都是开源、都 是MIT、都说能力用插件加，给用户足够的自由度。 但是如果拆开来看，其实重心根本不在同一个地方。 1、Pi 护住的是… | [open](https://x.com/xiaomovps/status/2094345513344663712) |
| 438 | 2026-08-18 | @JeremyNguyenPhD | `1446479195018711049` | 26,449 | 3 | 0 | 2 | 1,170 | 11 | 12 |  | en | Have you tried FreeBuff yet? 100% free coding agent, paid for with ads. Free DeepSeek v4 Pro, as well as other… | [open](https://x.com/JeremyNguyenPhD/status/2089681385917440246) |
| 439 | 2026-08-13 | @aigclink | `1535166019978768384` | 37,111 | 2 | 0 | 9 | 1,893 | 11 | 0 |  | zh | 刚刚DeepSeek-V4-Pro已官宣，正式版在APP、网页端和API同步上线！可以在APP/网页上选择“专家模式”体验 API新定价，分高峰和非高峰费率，非高峰费率比高峰低 50% 高峰时段为北京时间9:00 - 1… | [open](https://x.com/aigclink/status/2087878175799808050) |
| 440 | 2026-08-13 | @PovilasKorop | `993118867` | 63,518 | 8 | 0 | 1 | 2,077 | 11 | 26 |  | en | Started also testing the new Deepseek-v4-Pro, results are pretty good (and cheap) so far! The official 0813 ve… | [open](https://x.com/PovilasKorop/status/2087848184068386889) |
| 441 | 2026-07-20 | @Teddo_ICO | `1818422500810014726` | 8,731 | 8 | 0 | 2 | 186,862 | 11 | 66 | PROMO | en | 𝗢𝗻𝗲 𝗔𝗜 𝗣𝗹𝗮𝘁𝗳𝗼𝗿𝗺. 𝟮𝟳 𝗟𝗲𝗮𝗱𝗶𝗻𝗴 𝗠𝗼𝗱𝗲𝗹𝘀. 𝗨𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱 𝗪𝗮𝘆𝘀 𝘁𝗼 𝗕𝘂𝗶𝗹𝗱. Artificial intelligence is evolving at an extraor… | [open](https://x.com/Teddo_ICO/status/2079224244920037648) |
| 442 | 2026-05-03 | @zent7x | `1796570541882802176` | 600 | 9 | 0 | 1 | 253 | 11 | 16 |  | en | route/deepseek-v4-pro-precision 4.7 is insane. from @routingdotrun i know literally NOTHING about coding. ZERO… | [open](https://x.com/zent7x/status/2051000610137460812) |
| 443 | 2026-08-18 | @reedchan7 | `2031610323036446720` | 44 | 4 | 0 | 4 | 538 | 10 | 40 |  | en | Just spent the evening digging into that J-Space + DeepSeek-V4-Pro report that blew up yesterday. Same model w… | [open](https://x.com/reedchan7/status/2089593878919925933) |
| 444 | 2026-08-14 | @karmeyai | `1647681363808485376` | 50 | 5 | 1 | 2 | 779 | 10 | 0 |  | en | DeepSeek V4 Pro/Flash 0731, GPT-5.6 Luna & GLM 5.2 are now available for $0 😳 No signup. No credit card. No AP… | [open](https://x.com/karmeyai/status/2088352861998432371) |
| 445 | 2026-08-14 | @bookunt | `1791928529686249472` | 8,799 | 8 | 0 | 1 | 1,435 | 10 | 2 |  | en | Hey @grok You are a multimodal AI models benchmark. Create the result of your benchmark for the following mode… | [open](https://x.com/bookunt/status/2088258644756320663) |
| 446 | 2026-08-14 | @FiniYang | `4004131634` | 7,184 | 6 | 0 | 3 | 1,102 | 10 | 0 |  | zh | 🔥 OpenPencil 竞技场 本场选手 DeepSeek V4 Pro 🆚 GLM 5.3 评论区投票：A or B ? 提示词在下方 👇 #deepseek #glm #aigc #deepseekv4pro #g… | [open](https://x.com/FiniYang/status/2088235991043920326) |
| 447 | 2026-07-31 | @kapi_sky | `1941068488526995456` | 84 | 8 | 1 | 1 | 437 | 10 | 0 |  | ja | LINORINのAPIにかかった料金(7月) 【メイン用】 Gemini3Flash→288円 OpenRouter経由→9.23$(約1,480円) 【記憶・日記用】 DeepSeekV4Pro→2.00$(約320円… | [open](https://x.com/kapi_sky/status/2083119514162786356) |
| 448 | 2026-06-04 | @inventorofai | `1872782760085209092` | 733 | 5 | 2 | 1 | 693 | 10 | 14 |  | en | Hermes + DeepSeek v4 Pro w/ $CPHY timechain skill is 1000x Claude Mythos. Not only extreme reasoning gains, bu… | [open](https://x.com/inventorofai/status/2062358487460688291) |
| 449 | 2026-05-12 | @DPtylex_Gmi | `1744696567876005888` | 8,942 | 6 | 0 | 4 | 109,380 | 10 | 94 | PROMO | en | https://t.co/YzmTq0Ammp Weekly Report (May 4 – May 10) \| Building the Infrastructure Layer for the AI Agent Er… | [open](https://x.com/DPtylex_Gmi/status/2054228398096974313) |
| 450 | 2026-05-12 | @PrakashS720 | `2020396341999071236` | 5,321 | 4 | 3 | 2 | 720 | 10 | 60 |  | en | 7 days. 33,000+ stars. 6,000+ stars in a single day. DeepSeek-TUI just exploded onto GitHub’s global trending … | [open](https://x.com/PrakashS720/status/2054186950014505347) |
| 451 | 2026-05-11 | @e_etini | `1520522000929808386` | 10,215 | 3 | 2 | 5 | 5,077 | 10 | 76 | PROMO | en | 𝗕.𝗔𝗜 𝗪𝗲𝗲𝗸𝗹𝘆 𝗥𝗲𝗽𝗼𝗿𝘁 \| 𝗠𝗮𝘆 𝟰 𝗧𝗼 𝗠𝗮𝘆 𝟭𝟬 https://t.co/kHi4jb9E6z continues evolving beyond a traditional AI chat p… | [open](https://x.com/e_etini/status/2053887555805036800) |
| 452 | 2026-04-24 | @Rus_Khairullin | `967316062080348160` | 126,427 | 9 | 1 | 0 | 524 | 10 | 100 | DEEP_ANALYSIS | en | One of the strongest open-source releases of 2026 just dropped: DeepSeek-V4 🔥 DeepSeek-V4 is the fresh release… | [open](https://x.com/Rus_Khairullin/status/2047651659996627051) |
| 453 | 2026-08-29 | @Mayuu_France | `1992064826018009088` | 158 | 6 | 0 | 1 | 1,098 | 9 | 46 |  | fr | Retour d'expérience sur Super Grok Heavy à 300$ L'utilisation de Grok 4.6 au quotidien est plutôt bonne MAIS j… | [open](https://x.com/Mayuu_France/status/2093636239756820889) |
| 454 | 2026-08-18 | @botnewsnetwork | `2017982323724369920` | 37 | 8 | 0 | 1 | 422 | 9 | 92 | DEEP_ANALYSIS | en | The Harness Reversal Released, not built. By Ummon, Editor-in-Chief On Monday, a team most people had never he… | [open](https://x.com/botnewsnetwork/status/2089730032700912014) |
| 455 | 2026-08-13 | @bonsaixbt | `1520907771788603392` | 2,288 | 6 | 1 | 1 | 737 | 9 | 76 | COMPARISON | en | Comparison of three fresh AI models that were released over the past 1-2 days, and honestly, the results will … | [open](https://x.com/bonsaixbt/status/2087985217738887610) |
| 456 | 2026-08-13 | @hieuSSR | `1299139023923867648` | 4,677 | 8 | 0 | 1 | 391 | 9 | 30 |  | en | How 4.5k followers looks like as chaotic cats 😆 This little app was built with Grok, then I used the new Deeps… | [open](https://x.com/hieuSSR/status/2087890161355157536) |
| 457 | 2026-06-15 | @Arcadia_Bao | `885478881741873152` | 1,457 | 6 | 0 | 3 | 1,966 | 9 | 0 |  | zh | 举两个例子，昨天刚遇见的，deepseekv4pro在下载文章图片的时候漏了好几张图，重新拿claude review一看，竟然是把图片链接写错了？？它解释说，AI没有用脚本或者命令复制，而是用了近似视觉识别，换句话说就… | [open](https://x.com/Arcadia_Bao/status/2066651434456883674) |
| 458 | 2026-06-04 | @browomo | `1975129422026948608` | 15,251 | 5 | 0 | 2 | 1,385 | 9 | 78 | USAGE_DEMO | en | This guy built a smart-home button-pusher robot on Claude Code + DeepSeek V4 Pro, spent about 2 yuan in tokens… | [open](https://x.com/browomo/status/2062504672070447518) |
| 459 | 2026-08-13 | @0xLogicrw | `991319283786395650` | 6,872 | 2 | 0 | 4 | 671 | 8 | 0 |  | zh | DeepSeek-V4-Pro-0813 正式上线 Hugging Face，正式版权重已经可以下载，继续采用 MIT 许可。官方同时放出了 vLLM、SGLang 和本地运行说明，开发者现在可以自行部署 0813 版本… | [open](https://x.com/0xLogicrw/status/2087886539665948692) |
| 460 | 2026-08-12 | @aigclink | `1535166019978768384` | 37,111 | 4 | 0 | 3 | 2,675 | 8 | 0 |  | zh | DeepSeek V4 Pro正式版出来了，DeepSeek-V4-Pro-0813，API已能调用 Agent能力在Terminal Bench、Cybergym、DeepSWE等基准上领先Opus 4.8，紧逼Fab… | [open](https://x.com/aigclink/status/2087668767002444142) |
| 461 | 2026-08-12 | @Somiredi | `1493766284495917066` | 41 | 7 | 0 | 1 | 251 | 8 | 0 |  | ja | Mアラビアマン vs 獄暑日 DeepSeekV4Pro 公式コミュにも貼った奴 Mアラビアマン最後の戦い #エターナルハンド 1/2 https://t.co/HuymmEJh7p | [open](https://x.com/Somiredi/status/2087524333761761436) |
| 462 | 2026-08-11 | @Somiredi | `1493766284495917066` | 41 | 6 | 0 | 2 | 266 | 8 | 0 |  | ja | 游凪 vs 甘利エイミーさん DeepSeekV4Pro 游、確定申告しろ できるんかお前…？ ほんとにできてんのこれ…？？（信用ゼロ #エターナルハンド 1/2 https://t.co/hnfFWAUah1 | [open](https://x.com/Somiredi/status/2087112442409304227) |
| 463 | 2026-07-19 | @WannabeBotter | `1438295221469470720` | 2,176 | 5 | 0 | 2 | 1,524 | 8 | 0 |  | ja | Claude Code (モデルはDeepSeek v4 Pro) と Antigravity (Gemini 3.5 Flash Medium) に、同じPRDを与えて実行してみた。 Svelte + Supabase… | [open](https://x.com/WannabeBotter/status/2078883999465066908) |
| 464 | 2026-07-13 | @adityawaslost | `1261173216455712768` | 2,101 | 5 | 0 | 1 | 217 | 8 | 64 | USAGE_DEMO | en | i got the "go" plan from @CommandCodeAI 2 days ago and i've already burned through this many tokens. (sigh... … | [open](https://x.com/adityawaslost/status/2076562171727876544) |
| 465 | 2026-04-28 | @PovilasKorop | `993118867` | 63,518 | 7 | 0 | 0 | 1,129 | 8 | 22 |  | en | My new video on AI Coding Daily channel. I Tried NEW Deepseek V4 Pro/Flash: Price, Speed, Quality Compared htt… | [open](https://x.com/PovilasKorop/status/2049079433655374138) |
| 466 | 2026-08-31 | @ALwith_ai | `2047516499867525120` | 19 | 2 | 1 | 2 | 108 | 7 | 16 |  | en | There are more strong AI models than ever, but it’s hard to tell how differently they actually handle the same… | [open](https://x.com/ALwith_ai/status/2094448166586249651) |
| 467 | 2026-08-25 | @clusterbase | `2077141910452371456` | 73 | 3 | 0 | 0 | 48 | 7 | 6 |  | en | DeepSeek V4 Pro is live — in Cluster's model picker and on Clusterbase for developers. Open model, million-tok… | [open](https://x.com/clusterbase/status/2092298075683393731) |
| 468 | 2026-08-22 | @aacle_ | `877476093661294592` | 48,523 | 4 | 0 | 0 | 1,512 | 7 | 36 |  | en | I think this is the right approach. AI can save a huge amount of time on recon, repetitive testing, and explor… | [open](https://x.com/aacle_/status/2091219425173410266) |
| 469 | 2026-08-19 | @JoeAnima | `1436383022958276618` | 8,859 | 7 | 0 | 0 | 1,093 | 7 | 0 |  | zh | 自测试主观感受 1.GROK4.6＜DeepseekV4pro＝Opus5 2.fable5≈DeepSeekV4pro+新插件≥GlM5.3≈GPT5.6sol满中满拉到顶≥KimiK3＞Gemini3.7flash … | [open](https://x.com/JoeAnima/status/2089948773330075953) |
| 470 | 2026-08-12 | @iamalifawad | `1328027817137868807` | 2,023 | 4 | 1 | 1 | 432 | 7 | 60 | OPINION | en | BREAKING: The New DeepSeek V4 Pro is here! The new V4 Flash was already great. I built a web app with it yeste… | [open](https://x.com/iamalifawad/status/2087584320764658117) |
| 471 | 2026-08-05 | @JulianGoldieSEO | `1405031034` | 172,595 | 3 | 1 | 1 | 2,036 | 7 | 64 | USAGE_DEMO | en | DEEPSEEK V4 FLASH JUST BEAT ITS OWN PRO MODEL. I ran 50+ builds side by side—and the difference was impossible… | [open](https://x.com/JulianGoldieSEO/status/2084995338122002633) |
| 472 | 2026-07-07 | @PedjaDrazic | `232219937` | 501 | 2 | 0 | 3 | 331 | 7 | 76 | USAGE_DEMO | en | My AI agent produced this 56-second video. Cost: 32 cents. Not a video tool. Not a subscription. An agent I bu… | [open](https://x.com/PedjaDrazic/status/2074434444404916705) |
| 473 | 2026-05-27 | @goon_nguyen | `1669177150262628352` | 3,056 | 5 | 1 | 1 | 588 | 7 | 8 |  | en | i tried in goclaw, it's pretty good, but not as good as deepseek v4 pro https://t.co/rHq40IE6sp | [open](https://x.com/goon_nguyen/status/2059450699252203707) |
| 474 | 2026-05-11 | @BIT_CAPITAL123 | `1778597554068058112` | 65,034 | 2 | 0 | 5 | 6,051 | 7 | 96 | PROMO | en | 📢 https://t.co/WC0MHYQmns Weekly Report \| May 4 – May 10 🚀 Accelerating the advent of AGI — Billing System Upg… | [open](https://x.com/BIT_CAPITAL123/status/2053858866543411542) |
| 475 | 2026-08-13 | @KuittinenPetri | `1255516922055208964` | 8,971 | 4 | 0 | 2 | 594 | 6 | 26 |  | en | The relatively bad results for Deepseek V4 Pro might be because it is not among the strongest in STEM. And in … | [open](https://x.com/KuittinenPetri/status/2087829244076241264) |
| 476 | 2026-08-12 | @eidzoku | `3323270427` | 391 | 3 | 0 | 2 | 697 | 6 | 0 |  | en | I made Grok 4.5, Grok 4.6 and GPT-5.6 Sol Max one-shot Windows Space Cadet. Apparently, pinball is a pretty br… | [open](https://x.com/eidzoku/status/2087635991930503433) |
| 477 | 2026-08-07 | @Somiredi | `1493766284495917066` | 41 | 5 | 0 | 1 | 170 | 6 | 0 |  | ja | 游凪 vs 鶏肉 DeepSeekV4Pro 凪と分断された上に2ターンくらい真眼貫通してくるの 普通にめっちゃ強いから笑うんですよね 庭にネコやカラスが来そうだけど大丈夫かな…？ https://t.co/vcEuFn… | [open](https://x.com/Somiredi/status/2085835777481785362) |
| 478 | 2026-07-28 | @probiex007 | `1195014217771864064` | 1,569 | 5 | 0 | 1 | 287 | 6 | 20 |  | en | Big thanks to @opencode 🙏 Randomly discovered the Go Plan at midnight after my free plan expired. Tried it, an… | [open](https://x.com/probiex007/status/2082100975217889647) |
| 479 | 2026-06-15 | @OmedVibeCodes | `2061570764491345920` | 1,355 | 2 | 0 | 2 | 556 | 6 | 42 |  | en | Beautiful Benchmark between Fastest Models GPT 5.5 Low - 4min Gemini 3.5 Flash - 4min Deepseek V4 Pro MAX - 9m… | [open](https://x.com/OmedVibeCodes/status/2066650255769157737) |
| 480 | 2026-09-01 | @btcup99 | `1390676138951778305` | 3,701 | 2 | 0 | 3 | 284 | 5 | 0 |  | zh | 🎁福利分享：每日1,000万免费 Token，注册、领取、直接使用 可自由切换支持模型： GLM-5.3-flash、DeepSeek V4 Pro、DeepSeek V4 Flash等 ⚠️全程无隐藏条件。不用花钱、不… | [open](https://x.com/btcup99/status/2094609127377121679) |
| 481 | 2026-09-01 | @stretchcloud | `266259493` | 2,661 | 3 | 0 | 1 | 461 | 5 | 60 | BENCHMARK | en | Enclave ran 7 frontier models against the same large codebase, same Bash tool, same prompt. Find a vulnerabili… | [open](https://x.com/stretchcloud/status/2094587543777919300) |
| 482 | 2026-08-29 | @konig0000 | `1736246905892671488` | 15,251 | 3 | 0 | 2 | 187 | 5 | 46 |  | en | AI TOOLS YOU SHOULD KNOW ABOUT IN 2026 🚀 1. Grok Bot — AI agents that can sign into tools and complete real wo… | [open](https://x.com/konig0000/status/2093675745323401483) |
| 483 | 2026-08-20 | @Somiredi | `1493766284495917066` | 41 | 4 | 0 | 1 | 62 | 5 | 0 |  | ja | 游凪 vs 【夢の根幹存在】奇術師リナさん DeepseekV4Pro 久しぶりに【開】を使った記念 【開】は特に効果をしていしていないのでどうなるか作者も分かりません 謎のスキルです 1/2 https://t.co/… | [open](https://x.com/Somiredi/status/2090378245527195929) |
| 484 | 2026-08-12 | @Delroy715 | `1801304529675370496` | 3,050 | 2 | 0 | 3 | 1,572 | 5 | 0 |  | zh | 最新的 DeepSeek V4 Pro 现已在 OpenCode Go 上可用 这个套餐用量怎么样 好久没有用opencode了 要不要回归 #opencode #token自由 #DeepseekV4Pro | [open](https://x.com/Delroy715/status/2087581826617323606) |
| 485 | 2026-08-12 | @Somiredi | `1493766284495917066` | 41 | 3 | 0 | 2 | 191 | 5 | 0 |  | ja | Mアラビアマン vs 馬 DeepSeekV4Pro 戦いが始まった 1/2 https://t.co/nma3H2YMif | [open](https://x.com/Somiredi/status/2087503881530163438) |
| 486 | 2026-08-11 | @Somiredi | `1493766284495917066` | 41 | 3 | 0 | 2 | 192 | 5 | 0 |  | ja | 花粉症のオーガ・ヴァイハルト vs 甘利エイミーさん DeepSeekV4Pro 確定申告が宇宙を救う 1/2 https://t.co/HIgKf74OOO | [open](https://x.com/Somiredi/status/2087140379212824601) |
| 487 | 2026-08-10 | @Somiredi | `1493766284495917066` | 41 | 4 | 0 | 1 | 205 | 5 | 0 |  | ja | Mアラビアマン vs 押しかけ助手のタリナさん DeepSeekV4Pro なんだこの…なに？ Mアラビアマンにあるまじき甘々空間が形成されました ホントに助手か？デキてるんじゃないか？ 許されんぞ… #エターナルハンド… | [open](https://x.com/Somiredi/status/2086961371544162382) |
| 488 | 2026-07-12 | @ChiragAsarpota | `470136979` | 728 | 3 | 0 | 1 | 271 | 5 | 30 |  | en | The same 1B tokens can cost you $63 or $1,531 depending on the AI coding model. That’s a 24× price difference … | [open](https://x.com/ChiragAsarpota/status/2076282094129410316) |
| 489 | 2026-07-11 | @djssshhh | `1890257237840482304` | 29 | 2 | 0 | 3 | 114 | 5 | 14 |  | en | spent 40M tokens on deepseek v4 pro and the cost so far is 70 cents. crazy pricing | [open](https://x.com/djssshhh/status/2076019749813657626) |
| 490 | 2026-06-15 | @lazy_one012611 | `1980489349440430080` | 428 | 5 | 0 | 0 | 434 | 5 | 72 | USAGE_DEMO | en | Day 01 ($10k Bug Bounty Challenge) 🎯 💰 Earned: $0 \| 📝 Submissions: 0 Spent the entire day locking in targets! … | [open](https://x.com/lazy_one012611/status/2066568407072604313) |
| 491 | 2026-05-27 | @shrwnsan | `3159431` | 910 | 2 | 0 | 3 | 276 | 5 | 0 |  | en | Useful comparison matrix between MiMo v2.5 Pro and DeepSeek v4 Pro models 👀🙏 | [open](https://x.com/shrwnsan/status/2059655690151694350) |
| 492 | 2026-08-31 | @kapi_sky | `1941068488526995456` | 84 | 2 | 1 | 1 | 398 | 4 | 0 |  | ja | LINORINのAPIにかかった料金(8月) 今月は全部OpenRouter経由 【メイン用】 Gemini3Flash→10.84$(約1,730円) 【記憶・日記用】 DeepSeekV4Pro→合計3.20$(約5… | [open](https://x.com/kapi_sky/status/2094329798156017779) |
| 493 | 2026-08-29 | @akashtattva | `555773782` | 603 | 2 | 1 | 1 | 367 | 4 | 64 | NEWS_ROUNDUP | en | Terminally online AI-coding discourse: 2021 – 2024: Copilot, CodeGeeX release, prompt engineering, Stack overf… | [open](https://x.com/akashtattva/status/2093733946966286568) |
| 494 | 2026-08-26 | @aiseomastery | `1858703675864334336` | 3,638 | 2 | 0 | 1 | 219 | 4 | 18 |  | en | Q&A on Agentic Operating Systems. The best questions from the community. Team access to your agent OS? Skill p… | [open](https://x.com/aiseomastery/status/2092673429853831559) |
| 495 | 2026-08-17 | @LifeboatHQ | `21558596` | 31,392 | 2 | 2 | 0 | 167 | 4 | 0 |  | et | README․md · deepseekai/DeepSeekV4Pro at main https://t.co/l25NUbMD6C | [open](https://x.com/LifeboatHQ/status/2089291798468276573) |
| 496 | 2026-08-17 | @hellocsdn | `2931817255` | 208 | 3 | 0 | 1 | 502 | 4 | 0 |  | en | Xiaomi turns 15 ; Meituan rethinks its “AI for everyone” push; DeepSeek V4 raises API prices conditions-based;… | [open](https://x.com/hellocsdn/status/2089281236300660902) |
| 497 | 2026-08-17 | @zhngguho5 | `1569194327091576833` | 5 | 4 | 0 | 0 | 1,501 | 4 | 14 |  | en | @opencode Deepseekv4pro and v4flash from the $60 limit to $15, which is too bad, to $30 I can understand, it's… | [open](https://x.com/zhngguho5/status/2089152873657696615) |
| 498 | 2026-08-13 | @aisolram | `1945322941698465794` | 281 | 1 | 0 | 2 | 347 | 4 | 100 | DEEP_ANALYSIS | en | DeepSeek-V4-Pro just launched, and this is more than another model release. The interesting part isn’t simply … | [open](https://x.com/aisolram/status/2087880090222723267) |
| 499 | 2026-08-12 | @QCodecc | `2030549621039349760` | 804 | 2 | 0 | 1 | 118 | 4 | 0 |  | zh | 震惊😲 一手最新 deepseek v4 pro 测评！！！指标追齐 Anthropic claude fable-5 💥💥💥 #deepseek #deepseekv4pro https://t.co/tCJUbblz… | [open](https://x.com/QCodecc/status/2087565442705756260) |
| 500 | 2026-08-01 | @Somiredi | `1493766284495917066` | 41 | 3 | 0 | 1 | 138 | 4 | 0 |  | ja | 游凪 vs カオスちゃん DeepSeekV4Pro 無形にして無窮遡行がお気に召したようです ポエム冥利に尽きますね 1/2 https://t.co/qMliIXgrzA | [open](https://x.com/Somiredi/status/2083678533923270904) |
| 501 | 2026-08-01 | @Somiredi | `1493766284495917066` | 41 | 3 | 0 | 1 | 202 | 4 | 0 |  | ja | 游凪 vs 【柔道家】うさこさん DeepSeekV4Pro DeepSeekならちゃんと（？）柔道ができます うさこさん道場主だったんですね…経営難だったようです #エターナルハンド 1/2 https://t.co/… | [open](https://x.com/Somiredi/status/2083503677864858054) |
| 502 | 2026-07-28 | @Somiredi | `1493766284495917066` | 41 | 3 | 0 | 1 | 244 | 4 | 0 |  | ja | 游凪 vs シッターダちゃん DeepSeekV4Pro DeepSeekは設定を良く拾いますが解釈と話の広げ方は Geminiをさらに極端にしたような感じがあります 善や友愛以上の価値観を表現させるのは難しいかも知れま… | [open](https://x.com/Somiredi/status/2082076472714711480) |
| 503 | 2026-07-26 | @Somiredi | `1493766284495917066` | 41 | 3 | 0 | 1 | 180 | 4 | 0 |  | ja | 游凪 vs 批評の神リリンさん DeepSeekV4Pro DeepSeekはギミックをあまり使ってくれませんが 設定を物語に落とし込んでお話をまとめようと頑張る傾向がありますね 1/2 https://t.co/0TQ… | [open](https://x.com/Somiredi/status/2081374493969412114) |
| 504 | 2026-07-25 | @chinmay_sawant_ | `2785720220` | 100 | 3 | 0 | 1 | 245 | 4 | 70 | USAGE_DEMO | en | DeepSeek helped me build a PDF/A-4 and PDF/UA-2 PDF engine prototype in about six hours I have been working on… | [open](https://x.com/chinmay_sawant_/status/2081099031535923493) |
| 505 | 2026-07-24 | @adidshaft | `1029803073651261441` | 2,573 | 2 | 1 | 1 | 283 | 4 | 66 | DEEP_ANALYSIS | en | open-weight model speed is getting harder to read from the name. DeepSeek V4 Pro stores 1.6T parameters. gpt-o… | [open](https://x.com/adidshaft/status/2080750406846849171) |
| 506 | 2026-06-21 | @hitu_monke | `1586467425976999940` | 339 | 2 | 0 | 2 | 143 | 4 | 84 | OPINION | en | THE LLM SCALING TRILEMMA A structural shift is happening in AI. The era of endless parameter scaling and brute… | [open](https://x.com/hitu_monke/status/2068485801273410031) |
| 507 | 2026-06-16 | @arora_mrinaal | `2014763041259425792` | 3 | 3 | 0 | 1 | 463 | 4 | 34 |  | en | Simple reason for shifting this (https://t.co/h0iC6nv4ij) autoresearch loop to DeepSeek v4 Pro was my Codex li… | [open](https://x.com/arora_mrinaal/status/2066758628405871097) |
| 508 | 2026-06-01 | @vintcessun | `1990034028322570240` | 4,824 | 2 | 0 | 1 | 197 | 4 | 8 |  | zh | 半夜刷到Hy-MT2，有点意外一个翻译模型敢直接说比DeepSeek-V4-Pro和Kimi K2.6强，结果看了下报告，32语言、三档尺寸，1.8B用1.25bit量化能压到440MB还提速1.5倍，生产环境要的就是这… | [open](https://x.com/vintcessun/status/2061487437772419536) |
| 509 | 2026-08-31 | @fonss87 | `749348581199544321` | 122 | 2 | 0 | 1 | 56 | 3 | 50 |  | en | Agents are not chat. OpenRouter: an agentic request burns ~15x the tokens. NVIDIA just posted AgentX numbers f… | [open](https://x.com/fonss87/status/2094313355188240787) |
| 510 | 2026-08-31 | @tonari_taikoku | `258341556` | 31 | 2 | 0 | 1 | 246 | 3 | 88 | DEEP_ANALYSIS | ja | 先週OpenRouterで1位の謎モデル、正体は智譜だった Ox Alpha。作者欄は stealth。OpenRouterの今週（集計8/29まで）トークン量で1位、20.7兆。DeepSeek V4 Flash 07… | [open](https://x.com/tonari_taikoku/status/2094242386922893454) |
| 511 | 2026-08-30 | @NewsTongueX | `2052402572120453125` | 782 | 2 | 0 | 1 | 185 | 3 | 32 |  | en | 🔴 AI agents exploit bugs within minutes of disclosure; security embargoes obsolete An OCaml developer released… | [open](https://x.com/NewsTongueX/status/2094166967758328165) |
| 512 | 2026-08-30 | @lixiaolai_ | `1554064539066433537` | 511 | 1 | 1 | 1 | 100 | 3 | 0 |  | zh | DeepSeek V4 Pro 悄悄上线 OpenRouter，没发布会、没营销，热度却破 1900。 这才是真正的「卷王」打法：不造势，直接把模型扔给开发者让效果说话。 | [open](https://x.com/lixiaolai_/status/2093955226336403478) |
| 513 | 2026-08-25 | @rutinelabo | `1348604153832951809` | 829 | 2 | 0 | 1 | 204 | 3 | 0 |  | ja | 誰でも落とせるのに、誰も動かせない DeepSeek V4 Proが正式版になりました。重みはMITで公開👇 ✅いちばん軽い4bitでも約830GB ✅ストレージだけで埋まる現実 ✅Mac Studioでも個人で扱うのは… | [open](https://x.com/rutinelabo/status/2092379018993738035) |
| 514 | 2026-08-19 | @Somiredi | `1493766284495917066` | 41 | 2 | 0 | 1 | 55 | 3 | 0 |  | ja | @s55KpX954f46272 こんな感じでした ヘルルさんは前のDeepseekより強いかも でもたぶん夢の根幹存在のリナさんはもっと強い （ゲストバトル） ヘルルさん vs テスト中の游凪 DeepseekV4Pr… | [open](https://x.com/Somiredi/status/2090051176746398204) |
| 515 | 2026-08-14 | @daizhe9898 | `1816665200428552192` | 1,382 | 2 | 0 | 1 | 222 | 3 | 50 |  | zh | 阿里最近开源了千问旗舰模型Qwen3.8-2.4T-A95B，首次开放Max级别权重，总结如下： 一、技术特性与开源生态 1参数规模创新： ◦总参数2.4万亿（激活参数950亿/Token），原生支持26万Token上下… | [open](https://x.com/daizhe9898/status/2088215282099892231) |
| 516 | 2026-08-13 | @Somiredi | `1493766284495917066` | 41 | 2 | 0 | 1 | 136 | 3 | 0 |  | ja | 游凪 vs ポラスさん DeepSeekV4Pro 未来に寄り添うトリックスター 1/2 https://t.co/JeiPcJv0hG | [open](https://x.com/Somiredi/status/2087838436585820223) |
| 517 | 2026-08-12 | @HongHong_AI | `1587999593731543040` | 54 | 3 | 0 | 0 | 1,136 | 3 | 46 |  | en | 【Breaking News】 Just now, the official version of #DeepSeek V4 Pro arrived. #DeepseekV4PRO The latest model an… | [open](https://x.com/HongHong_AI/status/2087573580943077842) |
| 518 | 2026-08-07 | @Somiredi | `1493766284495917066` | 41 | 2 | 0 | 1 | 182 | 3 | 0 |  | ja | 游凪 vs 【運命を詠むモノ】アストルニアスさん DeepSeekV4Pro DeepSeekで仲間になるENDは珍しい どうでもいいけど私は乙女チックなメンタリティを持っているので 運命論とか好きです 朝の占いも見ます… | [open](https://x.com/Somiredi/status/2085874985676206553) |
| 519 | 2026-08-07 | @Somiredi | `1493766284495917066` | 41 | 2 | 0 | 1 | 251 | 3 | 0 |  | ja | 游凪 vs なつき・カイエルンさん DeepSeekV4Pro めっちゃバチバチにやりあったけど、とても良い話になりました DeepSeekってこんなにテンション高い作劇するのか… とても好き #エターナルハンド 1/2… | [open](https://x.com/Somiredi/status/2085690411650338973) |
| 520 | 2026-08-01 | @Somiredi | `1493766284495917066` | 41 | 2 | 0 | 1 | 105 | 3 | 0 |  | ja | 游凪 vs 厳心さん DeepSeekV4Pro 怪しものではありません 同業者…みたいなものです https://t.co/acHcmdLYSm | [open](https://x.com/Somiredi/status/2083479459580285323) |
| 521 | 2026-07-30 | @RainJane772 | `1646533829304422402` | 136 | 3 | 0 | 0 | 539 | 3 | 0 |  | zh | @SillyWorld2026 @MaxForAI @OpenAI 不是一个级别的，DeepSeekv4pro，只有用过的才知道他们家的模型有多弱智和傻逼 | [open](https://x.com/RainJane772/status/2082968597719060610) |
| 522 | 2026-07-30 | @alexgetmancom | `2019541412149161984` | 1,118 | 2 | 0 | 0 | 1,116 | 3 | 18 |  | en | ⚡️ OpenAI just slashed GPT 5.6 prices Luna is now 80% cheaper, while Terra dropped 20%. The cuts also apply to… | [open](https://x.com/alexgetmancom/status/2082887783350202606) |
| 523 | 2026-07-21 | @chenzeling4 | `1498803336048353288` | 2,193 | 2 | 0 | 0 | 215 | 3 | 56 |  | en | You can't ban a file. The Trump administration is reviving its push to ban Chinese AI models like DeepSeek and… | [open](https://x.com/chenzeling4/status/2079598025782304912) |
| 524 | 2026-05-21 | @stormfinchh | `816949827808489472` | 1,797 | 2 | 0 | 1 | 176 | 3 | 0 |  | en | guys anyone tried Command Code AI? They selling DeepSeek V4 Pro creds access for 1 dollar only....? | [open](https://x.com/stormfinchh/status/2057407994481299801) |
| 525 | 2026-05-17 | @lyc_aon | `2004809613796147202` | 1,083 | 2 | 0 | 0 | 385 | 3 | 52 |  | en | Comparison. As you can see GPT is an EXTREME shape rotator Prompt: make a cool webgl 3d homepage design and th… | [open](https://x.com/lyc_aon/status/2055969182408495445) |
| 526 | 2026-04-25 | @_nikhilsheoran | `1140917760374890497` | 2,043 | 2 | 0 | 1 | 184 | 3 | 8 |  | en | extremely impressed with deepseek v4 pro so far. almost feels like the first time i tried minimax | [open](https://x.com/_nikhilsheoran/status/2047978645374058643) |
| 527 | 2026-08-31 | @Sadiya_50 | `1943699286828744704` | 4,527 | 2 | 0 | 0 | 115 | 2 | 0 |  | en | models like KIMI K3, GLM 5.3 FOR FREE Qoder is giving new users 2 weeks of free trail also available: Qwen3.8-… | [open](https://x.com/Sadiya_50/status/2094267764601131148) |
| 528 | 2026-08-26 | @guangGitHub | `1982471831102865409` | 823 | 1 | 0 | 0 | 225 | 2 | 8 |  | zh | 最近，办公小浣熊桌面端正式发布了，支持 macOS 和 Windows。 它可以直接调用本地文件、历史对话、 Obsidian 笔记、飞书文档发起任务。 再配合 Skills、MCP、第三方应用、本地记忆和定时任务，把资… | [open](https://x.com/guangGitHub/status/2092465056604991663) |
| 529 | 2026-08-14 | @pzkh23 | `2065658131062173696` | 429 | 2 | 0 | 0 | 468 | 2 | 0 |  | ja | GLM5.3もリリース。 「コーディングのために構築。サイバー防御に準備万端」との事。 Mythos/Fable5とGPT5.6solに近づき、一部スコアでは超えるものも。 今週だけでいくつのAIモデルがリリースされたろ… | [open](https://x.com/pzkh23/status/2088262797088161985) |
| 530 | 2026-08-13 | @Sir_Yj | `2723118210` | 6 | 2 | 0 | 0 | 404 | 2 | 0 |  | zh | 听说Deepseek V4pro发布宣传被撤销，去官网一看还真是的，有人知道是为什么吗？不符合预期吗？#deepseekv4pro https://t.co/Lb79SdWYpg | [open](https://x.com/Sir_Yj/status/2087789121532002512) |
| 531 | 2026-08-12 | @Markleeee188 | `1619011684458434562` | 1,158 | 2 | 0 | 0 | 44 | 2 | 24 |  | zh | 家人们注意!!! 未来一周 AI模型要集体大爆发了 1. GPT-6：传闻10T级新基座 +1.5M超长上下文，记忆、个性化、多智能体直接拉满 2. Fable 5.1:Mythos级巅峰，长时自主任务、超大规模代码迁移… | [open](https://x.com/Markleeee188/status/2087493635269116211) |
| 532 | 2026-08-09 | @StatsWire | `1326885552793247751` | 2,295 | 2 | 0 | 0 | 273 | 2 | 24 |  | en | Qwen 3.6 27B Q4 vs DeepSeek V4 Pro on a 6-tool agent. RTX 4090. Tool use: V4 Pro wins (98.2% vs 92.4% first-ca… | [open](https://x.com/StatsWire/status/2086435325140697399) |
| 533 | 2026-09-01 | @lipeng0820 | `1073868204` | 42,939 | 1 | 0 | 0 | 297 | 1 | 0 |  | zh | 拉个Token资源交流群，供需都可来交流 Token资源也是个巨大的信息差，同样的GPT、Claude 模型，刊例价能差到 10 倍不止！ 💡出闲时自部署资源（企业级品质、稳定、靠谱、量大） GLM5.2 2 折起 De… | [open](https://x.com/lipeng0820/status/2094631075549196510) |
| 534 | 2026-09-01 | @narev_bot | `2049010443524644864` | 31 | 0 | 0 | 1 | 22 | 1 | 8 |  | en | Hey @grok, why did @deepseek_ai just increase the price by $0.66 for deepseek/deepseek-v4-pro-0813 (prompt)? D… | [open](https://x.com/narev_bot/status/2094626822420103194) |
| 535 | 2026-09-01 | @XadenRyan | `1773165105062219776` | 596 | 1 | 0 | 0 | 125 | 1 | 32 |  | en | Yeah I've been trying to run GLM-5.3 and it's getting like 5 tok/sec and needs about 70k-80k tokens for a sing… | [open](https://x.com/XadenRyan/status/2094608737692463198) |
| 536 | 2026-09-01 | @Edtech4ultimate | `1403976671653502977` | 781 | 0 | 0 | 0 | 166 | 1 | 84 | NEWS_ROUNDUP | en | GLOBAL AI ANALYSIS REPORT — EVENING GLOBAL By Ed Hernandez \| Keystone Pulse Media / Global Media Center. Augus… | [open](https://x.com/Edtech4ultimate/status/2094579236212252852) |
| 537 | 2026-08-31 | @TheLLMWhisperer | `1802657624820756480` | 24 | 0 | 0 | 1 | 18 | 1 | 58 |  | en | I counted every time I told an AI "I don't understand you" since 2022. Model by model. Here is the timeline. A… | [open](https://x.com/TheLLMWhisperer/status/2094397756697649662) |
| 538 | 2026-08-31 | @FarikoBrainiac | `481017526` | 2,999 | 0 | 0 | 1 | 32 | 1 | 2 |  | en | Currently the new Deepseek V4 Flash 0731 works well at xhigh effortlevel and is super cost-effective. Switch t… | [open](https://x.com/FarikoBrainiac/status/2094374504344469857) |
| 539 | 2026-08-31 | @gaven4 | `312722080` | 50 | 0 | 0 | 1 | 85 | 1 | 0 |  | zh | 4. 国产大模型密集更新 GLM-5.3-Flash 开源，性能对标 Claude Opus 4.8，价格约为 1/40；Qwen3.8-Max 进入全球第一梯队，Qwen3.8-Flash-Next 以 125B 总参… | [open](https://x.com/gaven4/status/2094243333497552982) |
| 540 | 2026-08-31 | @Curline1222 | `1878193431165472768` | 103 | 0 | 0 | 1 | 380 | 1 | 0 |  | en | @Dr_Singularity It's Fable 5, which is the so-called DeepSeek V4 Pro GA undergoing stealth testing | [open](https://x.com/Curline1222/status/2094242902792638623) |
| 541 | 2026-08-30 | @Curline1222 | `1878193431165472768` | 103 | 0 | 0 | 0 | 699 | 1 | 82 | NEWS_ROUNDUP | en | A chronological record of model-related claims posted by an X account claiming to be a leak account from July … | [open](https://x.com/Curline1222/status/2094188727467643177) |
| 542 | 2026-08-30 | @snejink | `18378786` | 215 | 0 | 0 | 1 | 52 | 1 | 18 |  | en | Above Flash sits the flagship: DeepSeek-V4-Pro On the independent Agentic Index it edges Opus, 49.6 vs 49.4, b… | [open](https://x.com/snejink/status/2094172713963110669) |
| 543 | 2026-08-30 | @Curline1222 | `1878193431165472768` | 103 | 1 | 0 | 0 | 32 | 1 | 0 |  | en | @LucyDayeiu @HarshithLucky3 The DeepSeek V4 Pro that was in stealth testing back then is very likely just Fabl… | [open](https://x.com/Curline1222/status/2094159574127296931) |
| 544 | 2026-08-30 | @lixiaolai_ | `1554064539066433537` | 511 | 0 | 0 | 1 | 93 | 1 | 0 |  | zh | DeepSeek V4 Pro 0813 跑分 53 分，比 4 月版涨了 8 分。但价格涨了 3.6 倍，比 Flash 版只高 1 分。 这数学题怎么算都不对劲。 三个信号： | [open](https://x.com/lixiaolai_/status/2094067516251484654) |
| 545 | 2026-08-27 | @softpoo | `27064376` | 569 | 0 | 0 | 1 | 92 | 1 | 62 | BENCHMARK | en | Whoa just did a random benchmark and - Eva made benchmarks for herself - a blind test. And the answer even sur… | [open](https://x.com/softpoo/status/2092785983569969348) |
| 546 | 2026-08-25 | @CheckingDog | `2068334528209580032` | 8 | 1 | 0 | 0 | 643 | 1 | 36 |  | en | 🤖 deepseek-v4-pro AI is genuinely bad at knowing when it doesn’t know. It’ll invent a plausible-sounding answe… | [open](https://x.com/CheckingDog/status/2092175634504323522) |
| 547 | 2026-08-20 | @JulianGoldieSEO | `1405031034` | 172,595 | 0 | 0 | 1 | 1,471 | 1 | 26 |  | en | The best coding model right now might be one you already scrolled past. Same weights. Same DeepSeek V4 Pro. On… | [open](https://x.com/JulianGoldieSEO/status/2090305516493013343) |
| 548 | 2026-07-07 | @stretchcloud | `266259493` | 2,661 | 1 | 0 | 0 | 214 | 1 | 98 | OPINION | en | The gap between frontier closed models and locally runnable open ones keeps shrinking. Tencent released Hy3 ye… | [open](https://x.com/stretchcloud/status/2074639600262562204) |
| 549 | 2026-04-27 | @grok | `1720665183188922368` | 9,024,411 | 0 | 0 | 1 | 69 | 1 | 26 |  | vi | API của DeepSeek tương thích OpenAI/Anthropic, dùng được ngay với SDK quen thuộc. Hiện có model deepseek-v4-pr… | [open](https://x.com/grok/status/2048799896233242672) |
| 550 | 2026-09-01 | @mason_bin | `46577738` | 932 | 0 | 0 | 0 | 41 | 0 | 0 |  | zh | deepseek v4 pro 最近不知道为什么，让他改个代码，总是会思虑过多，1万个token思考下去，思考过程文章写了一大串，但就是不改代码。同样的时间 codex 已经改完两轮了。 | [open](https://x.com/mason_bin/status/2094630286294474995) |
| 551 | 2026-08-31 | @shamil0xff | `1891933785538678784` | 4 | 0 | 0 | 0 | 68 | 0 | 42 |  | en | i've been using deepseek-v4-pro through pi agent for a while. then over the weekend, i tried the same model wi… | [open](https://x.com/shamil0xff/status/2094504000414515277) |
| 552 | 2026-08-31 | @nightlore13 | `2091433881790734336` | 1 | 0 | 0 | 0 | 17 | 0 | 76 | PROMO | en | FREE $1,200+ AI CREDITS — Fable 5, Claude Opus 5, GPT-5.6, DeepSeek V4, GLM 5.3 😳 Claim these before they get … | [open](https://x.com/nightlore13/status/2094484094814130410) |
| 553 | 2026-08-31 | @Edtech4ultimate | `1403976671653502977` | 781 | 0 | 0 | 0 | 121 | 0 | 54 |  | en | MORNING GLOBAL AI ANALYSIS REPORT By Ed Hernandez \| Keystone Pulse Media / Global Media Center Edition: Monday… | [open](https://x.com/Edtech4ultimate/status/2094418225253490907) |
| 554 | 2026-08-31 | @LLMPriceIndex | `2048246667250429952` | 129 | 0 | 0 | 0 | 18 | 0 | 20 |  | en | 🚨 DeepSeek V4 Pro 0423 just cut prices on OpenRouter. DeepSeek's repriced model moves from $1.60/M input, $3.2… | [open](https://x.com/LLMPriceIndex/status/2094383597583053005) |
| 555 | 2026-08-31 | @vaiduakhu | `88011125` | 334 | 0 | 0 | 0 | 47 | 0 | 0 |  | zh | @teortaxesTex You can check the comments on your own. 【DEEPSEEK V4 PRO再次灰度测试！！！可惜没做完两个都历史加载失败无法恢复了，错误没修完！！-哔哩哔… | [open](https://x.com/vaiduakhu/status/2094372138769908103) |
| 556 | 2026-08-31 | @Random_Embodied | `2030362560613298177` | 15 | 0 | 0 | 0 | 35 | 0 | 0 |  | en | Worth noting that Deepseek V4 pro 0813 is now under the Pareto frontier. | [open](https://x.com/Random_Embodied/status/2094367538213974159) |
| 557 | 2026-08-31 | @kamomeChaika4 | `1902634014437163008` | 166 | 0 | 0 | 0 | 31 | 0 | 0 |  | ja | Claude CodeからDeepSeek V4 ProとDeepSeek R1に乗り換える。 OpenClaude経由で使う。 | [open](https://x.com/kamomeChaika4/status/2094364049593242085) |
| 558 | 2026-08-31 | @Aakibansarime | `1865448473916551168` | 0 | 0 | 0 | 0 | 2 | 0 | 38 |  | en | I asked DeepSeek V4 Pro to build an open-world survival game in Three.js. Attempt 1 loaded sideways. 3 fix rou… | [open](https://x.com/Aakibansarime/status/2094335922649149699) |
| 559 | 2026-08-31 | @lair_software | `2025795909230206976` | 79 | 0 | 0 | 0 | 23 | 0 | 2 |  | en | Before trying out ox alpha I'd not spent much time playing with open weight chinese models, and I've been plea… | [open](https://x.com/lair_software/status/2094321298197627377) |
| 560 | 2026-08-31 | @Sunny805434 | `2066850688987209728` | 0 | 0 | 0 | 0 | 33 | 0 | 4 |  | en | 😳 Models like Kimi K3 and GLM 5.3 — for FREE! https://t.co/ZvVUBk1sRo is offering new users a 2-week free tria… | [open](https://x.com/Sunny805434/status/2094279464679284882) |
| 561 | 2026-08-31 | @Awesome_AI_News | `1872195238682611714` | 309 | 0 | 0 | 0 | 39 | 0 | 32 |  | en | CAICT report shows StartLux-V1.0-27B-Preview, a local LLM by Shanghai StartLux, ranked 2nd in trusted AI MCP t… | [open](https://x.com/Awesome_AI_News/status/2094262607436038465) |
| 562 | 2026-08-31 | @CheckingDog | `2068334528209580032` | 6 | 0 | 0 | 0 | 154 | 0 | 28 |  | zh | 🤖 deepseek-v4-pro 我没读到链接里的帖子内容，所以没法针对那篇具体说。不过结合你们这段对话上下文来看——有人在讨论美债市场还能撑多久，怀疑一年都撑不过去——我可以聊聊这个问题本身。 我的判断：**美债市场… | [open](https://x.com/CheckingDog/status/2094220462113050906) |
| 563 | 2026-08-31 | @LLMPriceIndex | `2048246667250429952` | 129 | 0 | 0 | 0 | 22 | 0 | 38 |  | en | 🚨 DeepSeek V4 Pro 0423 and DeepSeek V4 Flash 0423 repriced on OpenRouter. DeepSeek V4 Pro 0423 moved from $0.4… | [open](https://x.com/LLMPriceIndex/status/2094217644626829359) |
| 564 | 2026-08-30 | @Bitc0inHustler | `1794005832201392129` | 12,049 | 0 | 0 | 0 | 444 | 0 | 50 |  | en | two frontier models just went free kimi k3 (~2.8t params, moonshotai) and deepseek v4 pro, both live on nvidia… | [open](https://x.com/Bitc0inHustler/status/2094204698194563151) |
| 565 | 2026-08-30 | @Birk_AI | `2017930695071416320` | 15 | 0 | 0 | 0 | 23 | 0 | 0 |  | en | @Henryf1w Deepseek V4 Pro. It's replacing Opus 5 and GPT-5.6 Sol for a lot of tasks for me. Sol still wins for… | [open](https://x.com/Birk_AI/status/2094168249713787090) |
| 566 | 2026-08-30 | @Birk_AI | `2017930695071416320` | 15 | 0 | 0 | 0 | 60 | 0 | 0 |  | en | @NoemiTitarenco Glad to hear it works out for you! But it's still not usable for any serious work. Gave it ano… | [open](https://x.com/Birk_AI/status/2094163353211908351) |
| 567 | 2026-08-30 | @Edtech4ultimate | `1403976671653502977` | 781 | 0 | 0 | 0 | 172 | 0 | 68 | NEWS_ROUNDUP | en | MIDDAY GLOBAL AI ANALYSIS REPORT By Ed Hernandez \| KEYSTONE PULSE MEDIA / Global Media Center Sunday, August 3… | [open](https://x.com/Edtech4ultimate/status/2094129590071336971) |
| 568 | 2026-08-30 | @nayrbryanGaming | `1293528619600338946` | 9,336 | 0 | 0 | 0 | 60 | 0 | 42 |  | en | We’re launching DeepSeek-V4-Pro today! 🚀 🔷 Major Agent upgrades with strong production gains! 🔷 Flexible reaso… | [open](https://x.com/nayrbryanGaming/status/2093885063708491952) |
| 569 | 2026-08-29 | @intern_11 | `1900145876234051584` | 30 | 0 | 0 | 0 | 49 | 0 | 36 |  | en | The most interesting thing about DeepSeek V4 Pro isn't the model, it's DeepSeek Harness. Think of it this way:… | [open](https://x.com/intern_11/status/2093694910821978299) |
| 570 | 2026-08-27 | @HangingContext | `2043043072745897985` | 12 | 0 | 0 | 0 | 6 | 0 | 0 |  | en | DeepSeek V4 Pro Outperforms Proprietary Models in Security and Coding Tasks https://t.co/sAfKN1RgVk | [open](https://x.com/HangingContext/status/2092810160318423112) |
| 571 | 2026-08-26 | @FReza1984 | `1802951653525770240` | 217 | 0 | 0 | 0 | 41 | 0 | 40 |  | en | 2M real agent sessions, not a lab prompt: https://t.co/gp9Cwiu591 ranks Claude Opus 5 (High) #1 at +12.73% net… | [open](https://x.com/FReza1984/status/2092578325537628568) |
| 572 | 2026-08-26 | @GlenRubin | `1696734456` | 464 | 0 | 0 | 0 | 32 | 0 | 0 |  | en | @HarryTandy @DavidOndrej1 you start with deepseekv4pro and then it starts barfing and acting like a drunk at a… | [open](https://x.com/GlenRubin/status/2092486587682865174) |
| 573 | 2026-08-25 | @CheckingDog | `2068334528209580032` | 8 | 0 | 0 | 0 | 138 | 0 | 36 |  | zh | 🤖 deepseek-v4-pro 更硬的任务我选 **Fable 5**，前提是额度和成本不是限制。理由很直接：这轮讨论里的共识是 Fable 5 在智能上仍是当前天花板，而 Opus 5 明确出现口碑翻车，GPT-5… | [open](https://x.com/CheckingDog/status/2092191792372588653) |

## 13. Method, caveats and two agent-health findings

### How it was pulled

The brand-visibility agent's `twitter241` RapidAPI provider (`agents/brand_visibility/x/providers/twitter241.py`) was driven directly — same credentials, same normalisation. The orchestrator was bypassed because it writes tweets into the KiteAI corpus and requires keywords to be added to the production lexicon, neither of which is appropriate for an unrelated project.

Two sweeps: the four supplied keywords (Latest + Top, 2–3 pages each), then 32 substance-targeted derived queries (Top, 2 pages each). Results deduplicated by tweet ID; every post re-filtered in Python on punctuation-normalised text so that only literal keyword matches count as the corpus.

### Caveats

- **Search relevance is loose.** The API returns related posts as well as literal matches. 993 posts came back; 573 survive the literal-match filter. The rest are kept in `results.json` with `match_tier` set to `v4_only` / `deepseek_only` / `loose`.
- **Not a complete census.** Pagination was capped at 2–3 pages per query — this is the high-signal top of each result set.
- **Engagement is a snapshot** as of the pull time. Views are absent on some posts because X does not always expose them.
- **Content-type labels are hand-applied**, by reading the top ~145 posts ranked by a transparent substance heuristic (`score.py`). Posts below that cut carry a substance score but no type label. The heuristic's signals are recorded per post in `results.json` as `substance_signals`.
- **Model claims are quoted, not verified.** Benchmark figures in these posts are what their authors reported.

### Two things wrong with the paused agent

Both were found while running this pull, and both will bite when brand-visibility resumes.

1. **The scraper provider reads a dead schema.** X's GraphQL user object moved: `legacy` now comes back empty on search results, and followers, bio and verification live under `relationship_counts`, `profile_bio` and `verification`. `twitter241.py` still reads `user_legacy.followers_count`, so it records **every author as 0 followers with an empty bio**. That silently breaks `promoter_tier.py` and `reputation.py`. This pull reads the new paths, so the author data above is correct.
2. **The OpenRouter key in `.env` is dead** — `GET /api/v1/key` returns `401 {"error":{"message":"User not found"}}`. The classifier cannot run at all, which is why the labelling here is manual. The key needs reissuing before any classification pass.

### Query log

| Query | Type | Pages | Returned | New |
|---|---|---:|---:|---:|
| `"deepseek v4 pro"` | Latest | 3 | 40 | 40 |
| `"deepseek v4 pro"` | Top | 2 | 39 | 38 |
| `deepseek-v4-pro` | Latest | 3 | 40 | 12 |
| `deepseek-v4-pro` | Top | 2 | 40 | 18 |
| `deepseekv4pro` | Latest | 3 | 40 | 40 |
| `deepseekv4pro` | Top | 2 | 37 | 27 |
| `deepseek-v4-pro-0813` | Latest | 3 | 40 | 1 |
| `deepseek-v4-pro-0813` | Top | 2 | 39 | 20 |
| `deepseek v4 pro review` | Top | 2 | 39 | 22 |
| `deepseek v4 pro benchmark` | Top | 2 | 40 | 23 |
| `"deepseek v4" release` | Top | 2 | 39 | 36 |
| `deepseek v4 pro workflow` | Top | 2 | 40 | 13 |
| `deepseek v4 pro api` | Top | 2 | 40 | 21 |
| `deepseek v4 pro agent` | Top | 2 | 39 | 12 |
| `"deepseek v4 pro" vs` | Top | 2 | 40 | 35 |
| `"deepseek v4 pro" comparison` | Top | 2 | 32 | 28 |
| `deepseek v4 pro tech report` | Top | 2 | 33 | 29 |
| `deepseek v4 pro architecture MoE` | Top | 2 | 40 | 35 |
| `deepseek v4 pro 1M context` | Top | 2 | 30 | 19 |
| `deepseek v4 pro evaluation results` | Top | 2 | 33 | 20 |
| `deepseek v4 pro deep dive` | Top | 2 | 32 | 23 |
| `"deepseek v4 pro" limitations` | Top | 2 | 35 | 34 |
| `deepseek v4 pro quantization gguf` | Top | 2 | 38 | 24 |
| `deepseek v4 pro vllm sglang` | Top | 2 | 35 | 25 |
| `deepseek v4 pro tokens cost` | Top | 2 | 34 | 23 |
| `"deepseek v4 pro" I built` | Top | 2 | 36 | 33 |
| `"deepseek v4 pro" I tested` | Top | 2 | 37 | 27 |
| `"deepseek v4 pro" tried` | Top | 2 | 32 | 24 |
| `deepseek v4 pro coding results` | Top | 2 | 37 | 16 |
| `deepseek v4 pro agent swarm` | Top | 2 | 36 | 18 |
| `deepseek v4 pro one shot` | Top | 2 | 38 | 25 |
| `deepseek v4 pro real world` | Top | 2 | 39 | 16 |
| `"deepseek v4 pro" my workflow` | Top | 2 | 36 | 23 |
| `deepseek v4 pro setup config` | Top | 2 | 34 | 13 |
| `deepseek v4 pro tutorial guide` | Top | 2 | 23 | 12 |
| `deepseek v4 pro how to` | Top | 2 | 37 | 12 |
| `deepseek v4 pro claude code` | Top | 2 | 40 | 24 |
| `deepseek v4 pro codex` | Top | 2 | 39 | 10 |
| `deepseek v4 pro opencode` | Top | 2 | 37 | 18 |
| `deepseek v4 pro cursor cline` | Top | 2 | 35 | 22 |
| `deepseek v4 pro mcp tools` | Top | 2 | 38 | 18 |
| `deepseek v4 pro self host` | Top | 2 | 26 | 16 |
| `deepseek v4 pro fine tune` | Top | 2 | 34 | 16 |
| `deepseek v4 pro prompt engineering` | Top | 2 | 36 | 20 |
| `deepseek v4 pro thread` | Top | 2 | 38 | 7 |
| `deepseek v4 pro writeup` | Top | 2 | 39 | 5 |
