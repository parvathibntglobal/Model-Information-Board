# DeepSeek V4 Pro — Hacker News data pull

A sweep of Hacker News for substantive discussion of the language model **DeepSeek V4 Pro**, run over the Algolia HN Search API. Comments are included alongside stories and are the point of the exercise: on this platform, for this model, the evidence is in the replies.

> **One-off research pull, contained by design.** Nothing was written to any database. Nothing was imported from `collect/` or `judge/`. The raw pull lives under `var/hackernews/` (gitignored); this report is the committed artifact. See §9 *Method and containment* — including why this data is **not** admissible to the pipeline as it stands.

## 1. Run metadata

| Field | Value |
|---|---|
| Report generated | 2026-09-01T11:50:10+00:00 |
| Pull fetched at | 2026-09-01T11:34:52.050685+00:00 |
| Route | `scripts/fetch_hackernews_articles.py` — standalone, no `collect/` import |
| API | Algolia HN Search — `https://hn.algolia.com/api/v1` |
| Endpoints | `/search`, `/search_by_date`, `/search_by_date?tags=comment,story_<id>` |
| Auth | none — Algolia's HN Search API is public and unauthenticated |
| Window requested | 2026-03-02 → 2026-09-01 (6 months) |
| Keyword surfaces | 5 — `DeepSeek V4 Pro`, `deepseek v4 pro`, `deepseek-v4-pro`, `deepseek-v4-pro-0813`, `deepseek v4` |
| Queries | 10 (each keyword × both ranking endpoints) |
| Total API calls | 580 |
| Windows bisected | 8 (see §2.3) |
| Records returned | 2000 |
| **Literal matches** | **675** (623 comments, 52 stories) |
| Threads followed | 277 |
| Comments hand-read and labelled | 81 |
| Terms ruling | **none exists** for Algolia/HN in `contract/sources.yaml`. The gate was not invoked because this does not route through `collect/`. See §9.1 |

## 2. What the queries returned

### 2.1 Per query, with the denominator

`returned` is what Algolia handed back for that query; `literal` is how many of those actually contain the model's name once matched locally. The gap is the API's, not the corpus's — see §2.2.

| Keyword | Endpoint | Returned | Literal | Literal share |
|---|---|---|---|---|
| `DeepSeek V4 Pro` | `search` | 1213 | 652 | 54% |
| `DeepSeek V4 Pro` | `search_by_date` | 1210 | 651 | 54% |
| `deepseek v4 pro` | `search` | 1211 | 651 | 54% |
| `deepseek v4 pro` | `search_by_date` | 1212 | 652 | 54% |
| `deepseek-v4-pro` | `search` | 632 | 625 | 99% |
| `deepseek-v4-pro` | `search_by_date` | 632 | 625 | 99% |
| `deepseek-v4-pro-0813` | `search` | 31 | 31 | 100% |
| `deepseek-v4-pro-0813` | `search_by_date` | 31 | 31 | 100% |
| `deepseek v4` | `search` | 2000 | 675 | 34% |
| `deepseek v4` | `search_by_date` | 2000 | 675 | 34% |

After union and dedup across all 10 queries: **2000 distinct records, 675 literal matches (34%).**

### 2.2 Algolia prefix-matches query tokens, so raw hit counts are not match counts

The index matches a trailing token as a prefix. A query for `deepseek v4 pro` therefore matches *problem*, *production* and every unrelated `Pro`-suffixed model name. Nothing in the response marks these as weak hits.

Every record is consequently re-verified in this repo against `deepseek[\s\-_]*v?4[\s\-_]*pro(?:[\s\-_]*\d{3,4})?` over title, story title, URL and body before it counts as a match. **The unverified count would have been 2000; the verified count is 675.**

### 2.3 The API silently truncates at 1000 hits

Pagination is capped at 1000 records per query. A query whose `nbHits` is 2000 still returns `nbPages: 1` and hands back 1000 records with no error field, so a naive fetch is short and looks complete. Any window reporting at or above the cap is bisected by `created_at_i` until it is under — **8 bisections** in this run.

**The union landing on exactly 2000 looked like a cap artifact, so it was checked rather than assumed.** Re-walking the broadest query's bisection tree and summing each leaf window's own `nbHits` gives **1997**, with no leaf sitting at the cap. Were the true corpus larger than the reported 2000, the leaf sum would exceed it. So the round number is the corpus, not a ceiling; the 3-record difference is boundary effects across split windows.

One residual hole is worth naming: the bisection stops at a one-hour floor, so a single hour containing 1000+ matching records would still truncate silently. No window in this run came close, but the guard has a bottom.

## 3. Headline numbers

| Figure | Value | Denominator |
|---|---|---|
| Literal matches | 675 | of 2000 records returned |
| Comments | 623 | of 675 matches |
| Stories | 52 | of 675 matches |
| Distinct comment authors | 401 | across 623 matched comments |
| Threads containing a match | 236 | of 277 threads followed |
| Threads with 3+ matched comments | 56 | of 236 |
| Comments hand-labelled | 81 | of 623 matched comments |
| Date range of matches | 2026-04-24 → 2026-08-31 | — |

**The comment/story split is the finding.** 92% of matches are comments, not submissions. A stories-only fetch — the default shape for a platform sweep — would have returned 52 items and lost everything below.

Matches by month:

| Month | Matched comments |
|---|---|
| 2026-04 | 38 |
| 2026-05 | 190 |
| 2026-06 | 210 |
| 2026-07 | 100 |
| 2026-08 | 85 |

## 4. Artifacts — what separates a checkable claim from an opinion

Post length does not separate them. The comment this pull was commissioned around ([48006241](https://news.ycombinator.com/item?id=48006241)) is four sentences, and it carries a quoted price, the vendor's pricing URL, a dated expiry, a routing claim and a first-hand line. Meanwhile long comments in the same threads carry nothing a reader can check.

So each matched comment is tested for four artifacts, each independently falsifiable by a reader: a **link** resolves or 404s, a **number** is right or wrong, a **version** string names a build that shipped or did not, **code** runs or does not.

| Artifact | Comments carrying it | of 623 matched |
|---|---|---|
| `link` | 159 | 26% |
| `number` | 265 | 43% |
| `version` | 319 | 51% |
| `code` | 30 | 5% |

| Artifacts per comment | Comments | of 623 |
|---|---|---|
| 0 | 142 | 23% |
| 1 | 250 | 40% |
| 2 | 177 | 28% |
| 3 | 47 | 8% |
| 4 | 7 | 1% |

**142 matched comments (23%) carry no artifact at all** — that is the discrimination the column buys. It is not the same axis as content type: an `opinion` can carry a link and a `benchmark` can carry none.

### 4.1 Two detector corrections worth recording

Both of these produced a confident wrong number first, and both are the kind that survives review because the output looks plausible.

- **`version` fired on 601 of 623 comments (96%) in the first pass**, because the detector counted `v4 pro` — the keyword every matched comment contains by construction. A figure that is 96% by definition measures the query, not the comment. The model's own surface is now stripped before the test, and `version` means *a different build named*: a dated build (0813/0731) or a rival's version. It now stands at 319.
- **`code` found 2 blocks in the whole corpus in the first pass**, because it ran after HTML stripping and Algolia returns comment bodies with `<pre><code>` intact. It is now tested against the raw HTML and finds 30 — including the `#!/bin/sh` block in the DeepClaude thread that prompted this fetch, which the first pass missed.

## 5. Content type

Content type is **hand-assigned**, on 81 comments read in full — 13% of the 623 matched comments. The rest are counted, indexed and left unlabelled rather than guessed; §8 lists them with their mechanically-detected artifacts and no content type.

| Content type | Labelled comments |
|---|---|
| Deep Analysis | 18 |
| Benchmark | 17 |
| Usage Demo | 12 |
| Workflow | 8 |
| Comparison | 12 |
| Opinion | 6 |
| Announcement | 6 |
| News Roundup | 1 |
| Promo | 1 |
| **Total** | **81** |

Two mappings, stated because the vocabulary is fixed and the fit is not always obvious. **`deep_analysis`** covers evidenced corrections and original arithmetic, not only long essays — a price claim checked against the vendor's own pricing page is a deep-analysis item at four sentences. **`comparison`** is for lining named models up against each other; where the comparison is the author's own measured run it is filed as **`benchmark`** instead.

The labelling set was chosen as: matched comments carrying **two or more** artifact kinds, within the 14 threads holding the most matches. That is a stated selection rule, not a quality claim about the remainder — a one-artifact comment can be excellent and several are.

## 6. Threads

All 236 threads containing at least one matched comment are indexed in §7. The 14 below are the ones whose matched comments were read and labelled, in full.

### 6.1 DeepClaude – Claude Code agent loop with DeepSeek V4 Pro

**Thread** [48002136](https://news.ycombinator.com/item?id=48002136) · 678 points · 281 comments (281 fetched) · 2026-05-03  
*30 matched comments · 27 distinct authors · 16 of 30 carry an artifact · 9 labelled below*

**1. aftbit** · [48002640](https://news.ycombinator.com/item?id=48002640) · 2026-05-03 · `workflow` · artifacts: `link`, `version`, `code`  
> **Why this label:** The `#!/bin/sh` wrapper itself - exports ANTHROPIC_BASE_URL/AUTH_TOKEN/MODEL to point Claude Code at DeepSeek. Runnable as posted.

> #!/bin/sh export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic export ANTHROPIC_AUTH_TOKEN=sk-secret export ANTHROPIC_MODEL=deepseek-v4-flash export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 exec claude $@

**2. jubilanti** · [48003077](https://news.ycombinator.com/item?id=48003077) · 2026-05-04 · `workflow` · artifacts: `link`, `version`, `code`  
> **Why this label:** Same redirect as a single-line env prefix, routed through OpenRouter instead of the DeepSeek API.

> Here's a oneliner: ANTHROPIC_BASE_URL="https://openrouter.ai/api" ANTHROPIC_AUTH_TOKEN="$OPENROUTER_API_KEY" ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek/deepseek-v4-flash" CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 claude

**3. rapind** · [48004086](https://news.ycombinator.com/item?id=48004086) · 2026-05-04 · `workflow` · artifacts: `number`, `version`, `code`  
> **Why this label:** Model/subagent pairing (`pro[1m]` + Flash) with a week of first-hand use behind it, and the training-opt-out caveat stated rather than glossed.

> ANTHROPIC_MODEL=deepseek-v4-pro[1m] ANTHROPIC_SUBAGENT_MODEL=deepseek-v4-flash This is what I’ve been using for non-confidential projects for about a week now (soon after v4 came out). I honestly can’t tell the difference, but I’m not doing anything crazy with it either. Worth noting that I don’t think DeepSeek‘s API lets you opt out of training. Once this is up on other providers though… (OpenRouter is just proxying to DeepSeek atm)

**4. sowild_fun** · [48004484](https://news.ycombinator.com/item?id=48004484) · 2026-05-04 · `usage_demo` · artifacts: `number`, `version`  
> **Why this label:** Reports which CLI fits the model and a cache-hit rate above 95% for programming tasks, plus in-context switching between Flash and Pro.

> Using a bunch of CLIs to work with DeepSeek V4, I've found that Langcli is the best fit for DeepSeek V4. For programming tasks, the cache hit rate is above 95%. Not only can it seamlessly and dynamically switch between DeepSeek V4 Flash, V4 Pro, and other mainstream models within the same context, but it is also 100% compatible with Claude Code.

**5. l5870uoo9y** · [48005694](https://news.ycombinator.com/item?id=48005694) · 2026-05-04 · `deep_analysis` · artifacts: `link`, `number`  
> **Why this label:** Corrects the submission's headline price with the vendor's own pricing page and the dated expiry - the claim is checkable in one click.

> > DeepSeek V4 Pro scores 96.4% on LiveCodeBench and costs $0.87/M output tokens. Yes and this is a temporary discount which increases to 3.48 USD on 2026/05/31 15:59 UTC. Source: https://api-docs.deepseek.com/quick_start/pricing

**6. rsanek** · [48006241](https://news.ycombinator.com/item?id=48006241) · 2026-05-04 · `deep_analysis` · artifacts: `link`, `number`  
> **Why this label:** The same price correction plus two further checkable claims: the cheap rate only exists by passing through to the China-based API, and a first-hand line about which route the author actually uses.

> >DeepSeek V4 Pro scores 96.4% on LiveCodeBench and costs $0.87/M output tokens This is a heavily subsidized price and will only last until the end of the month: "The deepseek-v4-pro model is currently offered at a 75% discount, extended until 2026/05/31 15:59 UTC." [0] The "supported backends" table is also deceiving -- while OpenRouter's server's may be in the US, the only way to get the $0.44/$0.87 pricing is to pass through to the DeepSeek API, which of course is China-based. [1] I do think the model is quite good, I myself use it through Ollama Cloud for simple tasks. But I think some folks have bought in a little too much to the marketing hype around it. [0] https://api-docs.deepseek.com/quick_start/pricing [1] https://openrouter.ai/deepseek/deepseek-v4-pro/providers

**7. zozbot234** · [48006325](https://news.ycombinator.com/item?id=48006325) · 2026-05-04 · `usage_demo` · artifacts: `number`, `version`  
> **Why this label:** Names the concrete local-inference state: a fork running Q2 expert layers of Flash in 128GB RAM without disk offload.

> Waiting for official support in llama.cpp. There is a fork that can run a lightly quantized (Q2 expert layers) DeepSeek V4 Flash in 128GB RAM without offloading weight fetches from disk.

**8. guluarte** · [48012870](https://news.ycombinator.com/item?id=48012870) · 2026-05-04 · `workflow` · artifacts: `link`, `version`, `code`  
> **Why this label:** Shell function with the timeout and small-fast-model settings included, unsetting the inherited token first.

> I'm using this deepseek() { unset ANTHROPIC_AUTH_TOKEN local -x ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic" local -x ANTHROPIC_AUTH_TOKEN="${DEEPSEEK_API_KEY}" local -x ANTHROPIC_MODEL="deepseek-v4-pro" local -x ANTHROPIC_SMALL_FAST_MODEL="deepseek-v4-flash" local -x API_TIMEOUT_MS=600000 local -x CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 TMUX= command claude "$@" }

**9. rapind** · [48013784](https://news.ycombinator.com/item?id=48013784) · 2026-05-04 · `workflow` · artifacts: `link`, `number`, `version`, `code`  
> **Why this label:** The verbatim alias, corrected from the author's own earlier phone-typed version, with the VPS-isolation reason for running it credential-free.

> This is correct. Sorry I was using my phone to post. Here's what my bash alias verbatim looks like (.bashrc / .zshrc). The DEEPSEEK_API_KEY var is setup separately (so claude doesn't see it): ---- alias clauded='ANTHROPIC_BASE_URL= https://api.deepseek.com/anthropic ANTHROPIC_AUTH_TOKEN=$DEEPSEEK_API_KEY ANTHROPIC_MODEL=deepseek-v4-pro[1m] ANTHROPIC_DEFAULT_OPUS_MODEL=deepseek-v4-pro[1m] ANTHROPIC_DEFAULT_SONNET_MODEL=deepseek-v4-pro[1m] ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-v4-flash CLAUDE_CODE_SUBAGENT_MODEL=deepseek-v4-flash CLAUDE_CODE_EFFORT_LEVEL=max claude' ---- I doubt that the opus, sonnet, and haiku model args actually matter if you want to omit them. I run this on a VPS that has no other credentials or project access so I can give it the skip permissions arg.

### 6.2 DeepSeek V4 Pro beats GPT-5.5 Pro on precision

**Thread** [48440448](https://news.ycombinator.com/item?id=48440448) · 397 points · 225 comments (225 fetched) · 2026-06-08  
*26 matched comments · 21 distinct authors · 22 of 26 carry an artifact · 7 labelled below*

**1. SwellJoe** · [48440796](https://news.ycombinator.com/item?id=48440796) · 2026-06-08 · `benchmark` · artifacts: `link`, `number`, `version`  
> **Why this label:** The author's own vulnerability-scanning benchmark with cost per case: ~$1 for the whole V4 Pro run against $22/case for GPT-5.5 Pro, and 4-of-9 bugs found tied with Opus 4.8.

> I tried adding GPT 5.5 Pro to a vulnerability scanning benchmark I made ( https://swelljoe.com/post/will-it-mythos/ ), and it blew through the $100 budget limit halfway through. DeepSeek V4 Pro cost about a dollar for the whole benchmark. GPT Pro cost an average of $22 per case (a case could be 1-5 files with a recent known vulnerability, usually just a single file and a prompt along the lines of "does this file have any vulnerabilities"). GPT 5.5 Pro found two out of four cases that it got to before blowing its budget. Maybe it would have been the best of the bunch with infinite budget, but Opus 4.8, DeepSeek V4 Pro, and MiMo 2.5 Pro found four of nine of the bugs. Opus was an order of magnitude cheaper than GPT 5.5 Pro (and something like 30% cheaper than GPT 5.5), DeepSeek and MiMo were two orders of magnitude cheaper at roughly a dime per case. GPT Pro also chews a lot and a long tim…

**2. CJefferson** · [48441514](https://news.ycombinator.com/item?id=48441514) · 2026-06-08 · `workflow` · artifacts: `link`, `number`, `version`, `code`  
> **Why this label:** A working config script to try it for $5, paired with an honest 'not quite as good' quality caveat.

> My advice -- give it a try. Chuck $5 into deepseek.com , and use this config (put it in a shell script, run ' . ./deepseek-claude.sh ', then just run claude as normal. export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic export ANTHROPIC_AUTH_TOKEN= *** PUT YOUR DEEPSEEK KEY HERE *** export ANTHROPIC_MODEL=deepseek-v4-pro export ANTHROPIC_DEFAULT_OPUS_MODEL=deepseek-v4-pro export ANTHROPIC_DEFAULT_SONNET_MODEL=deepseek-v4-pro export ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-v4-flash export CLAUDE_CODE_SUBAGENT_MODEL=deepseek-v4-flash export CLAUDE_CODE_EFFORT_LEVEL=max I started by using it for some bigger reading jobs, particularly when I was near limit. Honestly, it's not quite as good, but it's much cheaper, and means I can carry on working. I also find sometimes it's good to ask claude and deepseek to consider code, how to polish, it see what they both say.

**3. metalspot** · [48442945](https://news.ycombinator.com/item?id=48442945) · 2026-06-08 · `usage_demo` · artifacts: `number`, `version`  
> **Why this label:** Extended first-hand report across a spec/test-driven harness: 98.5% input cache-hit ratio, degradation at 400-500K context, and named porting tasks completed.

> i have been using deepseek-v4-flash since it came out. i use a highly structured harness and spec/test driven workflow running through opencode, and so far there has been nothing it can't do. i have run through a bunch of tests: re-writing vvenc with assembly kernels, creating the first generation agent harness integration with opencode, porting TS npm modules to C++, porting an entire TS server app to C++, creating a new pure io_uring http server with zero-copy (325K RPS single core), creating a second generation agent from the ground up in C++, setting up a dev environment for custom kernel development on tenstorrent accelerators using tt-metal and ttsim. i consistently get 98.5% input cache hit ratio. i do see noticeable degradation in performance in the 400-500K context range, so i always try to wrap up sessions by 500K max. a non-intuitive thing is that the model is very good at low…

**4. smartbit** · [48444400](https://news.ycombinator.com/item?id=48444400) · 2026-06-08 · `comparison` · artifacts: `link`, `version`, `code`  
> **Why this label:** Corrects a cached-price claim with an effective-input-price table for MiMo V2.5 Pro against V4 Pro Max.

> > MiMo V2.5 Pro ... lower cached price At the moment of writing https://news.ycombinator.com/item?id=48343690 MiMo V2.5 Pro had a lower cache hit ratio. From the article: OSS models, depending on who you use them from, make a huge difference, mostly due to cache-hit rates. Model Cheapest effectiveInputPrice (Provider) MiMo-V2.5-Pro 0.3720 (Xiaomi) DeepSeek V4 Pro (Max) 0.0560 (DeepSeek)

**5. fc417fc802** · [48444621](https://news.ycombinator.com/item?id=48444621) · 2026-06-08 · `benchmark` · artifacts: `link`, `number`  
> **Why this label:** Throughput figures against the OpenRouter performance page - sub-2s to first token, 15-50 tps by provider - offered as a correction.

> That isn't what the charts on OpenRouter appear to show but they only seem to go back 1 week (unless I missed something). It should be less than 2 seconds to first token and anywhere from 15 to 50 tps depending on the provider. Admittedly 15 is a bit slow but most look to be closer to 30 or 40 which at least personally I think is fine. https://openrouter.ai/deepseek/deepseek-v4-pro/performance

**6. andai** · [48452996](https://news.ycombinator.com/item?id=48452996) · 2026-06-08 · `deep_analysis` · artifacts: `link`, `version`  
> **Why this label:** Small but checkable: the alias in question resolves to V4 Flash with reasoning disabled, cited to the API docs.

> Dang apparently it maps to DeepSeek V4 Flash with reasoning disabled! https://api-docs.deepseek.com/

**7. smartbit** · [48488118](https://news.ycombinator.com/item?id=48488118) · 2026-06-11 · `deep_analysis` · artifacts: `link`, `number`, `version`, `code`  
> **Why this label:** Cache-read-to-input cost ratios (Pro 0.83%, Flash 2%) sourced to a third-party write-up, with the ZDR caveat that voids response caching.

> Correct. According to https://minimaxir.com/2026/05/openrouter-hy3/#llm-economics-... [0] when served by DeepSeek, Cache Read Costs/Input Costs are a very low percentage: DeepSeek V4 Pro 0.83% DeepSeek V4 Flash 2% Notice that OpenRouter response caching is not available when account-level ZDR is enforced [1] [0] https://news.ycombinator.com/item?id=48317294#48317823 [1] https://openrouter.ai/docs/guides/features/response-caching#...

### 6.3 DeepSeek v4

**Thread** [47884971](https://news.ycombinator.com/item?id=47884971) · 2091 points · 1607 comments (1000 fetched) · 2026-04-24  
*24 matched comments · 21 distinct authors · 24 of 24 carry an artifact · 12 labelled below*

**1. nthypes** · [47885263](https://news.ycombinator.com/item?id=47885263) · 2026-04-24 · `opinion` · artifacts: `link`, `version`  
> **Why this label:** Frontier-level-at-a-fraction claim with a weights link but no measurement behind it.

> https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main... Model was released and it's amazing. Frontier level (better than Opus 4.6) at a fraction of the cost.

**2. simonw** · [47885574](https://news.ycombinator.com/item?id=47885574) · 2026-04-24 · `usage_demo` · artifacts: `link`, `version`  
> **Why this label:** Runs the author's standing SVG test on both variants and links four prior generations for comparison.

> I like the pelican I got out of deepseek-v4-flash more than the one I got from deepseek-v4-pro. https://simonwillison.net/2026/Apr/24/deepseek-v4/ Both generated using OpenRouter. For comparison, here's what I got from DeepSeek 3.2 back in December: https://simonwillison.net/2025/Dec/1/deepseek-v32/ And DeepSeek 3.1 in August: https://simonwillison.net/2025/Aug/22/deepseek-31/ And DeepSeek v3-0324 in March last year: https://simonwillison.net/2025/Mar/24/deepseek/

**3. esafak** · [47885649](https://news.ycombinator.com/item?id=47885649) · 2026-04-24 · `announcement` · artifacts: `link`, `version`  
> **Why this label:** The two OpenRouter model pages, nothing more.

> https://openrouter.ai/deepseek/deepseek-v4-pro https://openrouter.ai/deepseek/deepseek-v4-flash

**4. simonw** · [47885654](https://news.ycombinator.com/item?id=47885654) · 2026-04-24 · `deep_analysis` · artifacts: `number`, `version`  
> **Why this label:** Works the streaming-experts memory requirement from the published active-parameter count: 49B active is ~100GB at 16-bit, ~50GB at 8-bit.

> I've been calling that the "streaming experts" trick, the key idea is to take advantage of Mixture of Expert models where only a subset of the weights are used for each round of calculations, then load those weights from SSD into RAM for each round. As I understand it if DeepSeek v4 Pro is a 1.6T, 49B active that means you'd need just 49B in memory, so ~100GB at 16 bit or ~50GB at 8bit quantized. v4 Flash is 284B, 13B active so might even fit in <32GB.

**5. BoorishBears** · [47885796](https://news.ycombinator.com/item?id=47885796) · 2026-04-24 · `announcement` · artifacts: `link`, `version`  
> **Why this label:** Base-model weights appearing on Hugging Face.

> https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Base https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base And we got new base models, wonderful, truly wonderful

**6. sixhobbits** · [47886609](https://news.ycombinator.com/item?id=47886609) · 2026-04-24 · `announcement` · artifacts: `link`, `number`, `version`  
> **Why this label:** Reproduces the official launch post because the submitted link went to a generic docs page - parameter counts, context length, tech report and weights.

> I know people don't like Twitter links here but the main link just goes to their main docs site generic 'getting started' page. The website now has a link to the announcement on Twitter here https://x.com/deepseek_ai/status/2047516922263285776 Copying text of that below DeepSeek-V4 Preview is officially live & open-sourced! Welcome to the era of cost-effective 1M context length. DeepSeek-V4-Pro: 1.6T total / 49B active params. Performance rivaling the world's top closed-source models. DeepSeek-V4-Flash: 284B total / 13B active params. Your fast, efficient, and economical choice. Try it now at http://chat.deepseek.com via Expert Mode / Instant Mode. API is updated & available today! Tech Report: https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main... Open Weights: https://huggingface.co/collections/deepseek-ai/deepseek-v4

**7. cubefox** · [47887485](https://news.ycombinator.com/item?id=47887485) · 2026-04-24 · `deep_analysis` · artifacts: `link`, `number`, `version`  
> **Why this label:** Quotes the technical report abstract: 1.6T/49B MoE, CSA+HCA attention, mHC residuals, Muon optimiser, 32T training tokens.

> Abstract of the technical report [1]: > We present a preview version of DeepSeek-V4 series, including two strong Mixture-of-Experts (MoE) language models — DeepSeek-V4-Pro with 1.6T parameters (49B activated) and DeepSeek-V4-Flash with 284B parameters (13B activated) — both supporting a context length of one million tokens. DeepSeek-V4 series incorporate several key upgrades in architecture and optimization: (1) a hybrid attention architecture that combines Compressed Sparse Attention (CSA) and Heavily Compressed Attention (HCA) to improve long-context efficiency; (2) Manifold-Constrained Hyper-Connections (mHC) that enhance conventional residual connections; (3) and the Muon optimizer for faster convergence and greater training stability. We pre-train both models on more than 32T diverse and high-quality tokens, followed by a comprehensive post-training pipeline that unlocks and further…

**8. nsoonhui** · [47888227](https://news.ycombinator.com/item?id=47888227) · 2026-04-24 · `deep_analysis` · artifacts: `link`, `code`  
> **Why this label:** Checks the 'runs entirely on Huawei' claim against the tech report, quotes the fine-grained-EP speedup figures, and flags that the author leaned on the model to read it.

> Sorry, but exactly where did you get the idea that DS V4 runs entirely on Huawei? I asked DS itself and it denied this. It says: 'Nvidia chips are absolutely used for DeepSeek V4. The reality is a pragmatic "both-and" strategy, not an "either-or."' And based on the DS V4 technical report ( https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main... ), it is mentioned that: We validated the fine-grained EP scheme on both NVIDIA GPUs and HUAWEI Ascend NPUs platforms. Compared against strong non-fused baselines, it achieves 1.50 ~ 1.73× speedup for general inference workloads, and up to 1.96× for latency-sensitive scenarios such as RL rollouts and high-speed agent serving. (In all honesty I relied on DS to give me the above, so I haven't vetted the information in full.) It mentions that Nvidia is still used. It doesn't even mention that Huawei chips are used in production — only in test…

**9. XCSme** · [47888887](https://news.ycombinator.com/item?id=47888887) · 2026-04-24 · `benchmark` · artifacts: `link`, `version`  
> **Why this label:** Third-party benchmark placing it outside the top ten, with the confound named: Pro was rate-limited and timing out during testing.

> Something is odd with this model, their blog posts shows REALLY good results, but in most other third-party benchmarks, people realize it's not really SOTA, even bellow Kimi K2.6 and GLM-5/5.1 In my tests too[0], it doesn't reach top 10. One issue, which they also mentioned in their post, is that they can't really serve well the model at the moment, so V4-Pro is heavily rate-limited and gives a lot of timeout errors when I try to test it. This shouldn't be an issue though, considering the model is open-source, but it makes it hard to accurately test at the moment. [0]: https://aibenchy.com/compare/deepseek-deepseek-v4-flash-high...

**10. cmitsakis** · [47889301](https://news.ycombinator.com/item?id=47889301) · 2026-04-24 · `benchmark` · artifacts: `number`, `version`  
> **Why this label:** The author's own customer-support benchmark with scores for Flash against two Qwen sizes and Gemini 3 Flash, and a question about Pro scoring below Flash.

> I just did some quick testing on my own benchmark that tests LLMs as customer support chatbots, and found out that deepseek-v4-flash (scored 90.2%) was better than qwen3.5-27b (89%) and qwen3.5-35b-a3b (89.1%) and roughly equal to gemini-3-flash-preview (90.5%), but deepseek-v4-flash had the lowest cost of all of them by far. Half the cost of gemini-3-flash and an order of magnitude less cost than the qwen models. Have you noticed the deepseek-v4-pro performing worse than deepseek-v4-flash? It performed even worse than qwen3.5-27b. I found it surprising and I'm wondering if there is a bug on my software because I had to implement sending the `reasoning_content` otherwise the API failed with BadRequestError.

**11. maxloh** · [47891553](https://news.ycombinator.com/item?id=47891553) · 2026-04-24 · `announcement` · artifacts: `link`, `version`  
> **Why this label:** Both variants' weights are MIT-licensed, with links.

> They published model weights on Hugging Face. Both of them are MIT-licensed. DeepSeek-V4-Flash: https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash DeepSeek-V4-Pro: https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro

**12. XCSme** · [47901068](https://news.ycombinator.com/item?id=47901068) · 2026-04-25 · `benchmark` · artifacts: `link`, `version`  
> **Why this label:** Follow-up after the API issues cleared: the score moved to roughly GLM 5 level.

> Their API issues seemed to have been resolved, now it does[0] as expected, similar to GLM 5 level. [0]: https://aibenchy.com/compare/deepseek-deepseek-v4-flash-high...

### 6.4 DeepSeek V4 – almost on the frontier

**Thread** [47977026](https://news.ycombinator.com/item?id=47977026) · 677 points · 398 comments (397 fetched) · 2026-05-01  
*24 matched comments · 21 distinct authors · 22 of 24 carry an artifact · 9 labelled below*

**1. wg0** · [47982523](https://news.ycombinator.com/item?id=47982523) · 2026-05-02 · `usage_demo` · artifacts: `number`, `version`  
> **Why this label:** A layer-by-layer type audit of a TypeScript codebase for $0.09 on Pro, with the Opus counterfactual estimated from prior experience.

> Deepseek v4 Pro feels like Claude Opus 4.6 in it's personality but here's what I did find out about costs: I did cut loose Deepseek v4 on a decent sized Typescript codebase and asked it to only focus on a single endpoint and go in depth on it layer by layer (API, DTOs, service, database models) and form a complete picture of types involved and introduced and ensure no adhoc types are being introduced. It developed a very brief but very to the point summary of types being introduced and which of them were refunded etc. Then I asked it to simplify it all. It obviously went through lots of files in both prompts but total cost? Just $0.09 for the Pro version. On Claude Opus I think (from past experience before price hikes) these two prompts alone would have burned somewhere between $9 to $13 easily with not much benefit. Note - I didn't use Open router rather used the Deepseek API directly b…

**2. cheshire_cat** · [47985381](https://news.ycombinator.com/item?id=47985381) · 2026-05-02 · `deep_analysis` · artifacts: `link`, `number`, `version`  
> **Why this label:** Identifies the hidden cost: Pro burns 190M reasoning tokens on the AA index against GPT-5.5-high's 45M, so cheap per token is not cheap per task.

> While the cost are lower than frontier models there are two factors that make DS4 Pro and K2.6 not as cheap as they might look. For DS4 Pro there's a discount going on for the official API, which sometimes gets overlooked and mixed up in discussions. Simon uses the full price in the comparison, so that's not an issue here. The other issue is that DS4 Pro and K2.6 often use way more reasoning tokens than the frontier models. In my testing there are certain pathological cases where a request can cost the same as with a frontier model because they use so much more tokens. To be fair I'm using DS and kimi via 3rd party providers, so they might have issues with their setups. But if you look at the Artificial Analysis pages of the models you'll see that DSv4 Pro uses 190M tokens and K2.6 170M tokens for their intelligence benchmark, while GPT 5.5 (high) only used 45M.[0][1][2] I recommend look…

**3. segmondy** · [47986125](https://news.ycombinator.com/item?id=47986125) · 2026-05-02 · `deep_analysis` · artifacts: `link`, `number`, `version`  
> **Why this label:** Efficiency claims from the release paper - 27% of the FLOPs and 10% of the KV cache of V3.2 - with the author's own local before/after.

> This is very false DS4 is super cheap. I would advise to begin by reading their release paper. https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main... They introduce very novel methods to improve long context efficiency and attention. HCA & mCH. It requires only 27% of flops for inference and 10% for KV cache than v3.2. This makes it super efficient. Think of this. For flops, we can now serve more than 3x the amount with the same number of compute, and you would need 30% of prior KV cache. Furthermore, this release is a PREVIEW, DeepSeek is the real open labs and they not only cook up quite a bit with every single release, but they publish and share it. I'm running this locally. Let me tell you how "CHEAP" this is. With v3.2 I would run out of GPU ram, spill into system ram with 256k context. It ran quite alright and I was happy with my 7tk/sec. With this, I'm 100% in GPU ram wit…

**4. gertlabs** · [47987685](https://news.ycombinator.com/item?id=47987685) · 2026-05-02 · `benchmark` · artifacts: `link`, `version`  
> **Why this label:** Their ranking has Flash outperforming Pro, and separates why: Pro is stronger one-shot, weaker with unfamiliar tools over long horizons.

> DeepSeek V4 Flash is the most cost effective model we've tested. We had to really understand why it outperformed DeepSeek V4 Pro (although even on unreliable model cards, Flash was very close to Pro). Pro is slower and smarter in one-shot reasoning problems, but less effective with tools and therefore less performant in long horizon agentic tasks (especially with custom tools it was not trained on). Benchmarks at https://gertlabs.com/rankings

**5. scrollop** · [47988232](https://news.ycombinator.com/item?id=47988232) · 2026-05-02 · `benchmark` · artifacts: `link`, `number`, `version`  
> **Why this label:** Hallucination rates of 94% (Pro) and 96% (Flash) on the omniscience eval, linked.

> Obscene levels of hallucinations, the worst of LLMs, unfortunately. Deepseek v4 pro 94% Deepseek v4 flash - 96% https://artificialanalysis.ai/evaluations/omniscience?models...

**6. rurban** · [47988728](https://news.ycombinator.com/item?id=47988728) · 2026-05-02 · `usage_demo` · artifacts: `number`, `version`  
> **Why this label:** A working arm64 compiler port in about half an hour for roughly $8 of API spend, with the Pro-to-Flash switch and where each model failed.

> Well, I'm using all the top models extensively on the very same codebase, my new compiler. I use deepseek for it's cheap API costs, when kimi, claude and codex are in their overbudget phase. I asked deepseek V4 Pro for an estimate of a new arm64 port. It said 4 weeks, I said, ok, do it. (I knew ncc was there, and tinycc was also known to the AI's). So it took it half an hour to produce a working arm64 port. First for arm64-elf, because this was easiest to test, and then also after more hours of back and forth the arm64-darwin port. (with crossbuild and github actions). It did cost me with all the subsequent fixes around $8 API costs. So the experience: at the beginning deepseek was amazing. When it started to get expensive (china day time), I switched from Pro to Flash. No problem, same results. Some bitfield implementation was too complicated so I had to wait for Sonnet 4.6 tokens, kimi…

**7. gpugreg** · [47989937](https://news.ycombinator.com/item?id=47989937) · 2026-05-02 · `deep_analysis` · artifacts: `link`, `number`  
> **Why this label:** Derives a ~202% margin at promotional pricing from DeepSeek's own V3 infra numbers, NVIDIA's throughput figure and a $7/hr B300.

> I believe that DeepSeek-V4-Pro API at promotional pricing ( https://api-docs.deepseek.com/quick_start/pricing ) could run at almost exactly 200 % profit. If you take DeepSeek's numbers for DeepSeek-V3 ( https://github.com/deepseek-ai/open-infra-index/blob/main/20... ) and plug in ~3333 tps/GPU for DeepSeek-V4-Pro ( https://developer.nvidia.com/blog/build-with-deepseek-v4-usi... ) and a price of $7/hr per B300 GPU, the profit comes out as 202%. The rumor is that Anthropic's Opus models have ~100B active parameters, which is twice as much as DeepSeek-V4-Pro, so inference is at least twice as expensive. Since the API pricing is almost 30 times that of DeepSeek, Anthropic's margins are likely very healthy. But they have to be, since Anthropic has to offset the model training costs, while DeepSeek is backed by High-Flyer Quant. DeepSeek might still be profitable anyway, but without knowing ho…

**8. XCSme** · [47990148](https://news.ycombinator.com/item?id=47990148) · 2026-05-02 · `benchmark` · artifacts: `link`, `version`  
> **Why this label:** Flash scoring slightly better than Pro in the author's tests, attributed to Flash reasoning twice as much.

> Strangely, the V4 Flash pelican looks better than the V4 Pro one. In my tests[0], V4 Flash actually does slightly better and for a lot cheaper than V4 Pro, mostly because it reasons twice as much. [0]: https://aibenchy.com/compare/deepseek-deepseek-v4-flash-high...

**9. irthomasthomas** · [47990809](https://news.ycombinator.com/item?id=47990809) · 2026-05-02 · `workflow` · artifacts: `link`, `version`, `code`  
> **Why this label:** Multi-model consortium tool with Pro as one member and Flash as judge, with a rendered output to inspect.

> Not op but I wrote llm-consortium to prompt multiple models and create a synthesis. And it can run on an openai endpoint using llm-model-gateway. It's expensive, naturally, but for situations where you absolutely must get max intelligence its hard to beat. e.g. Pelican Riding a Bicycle — Engineering Study by DeepSeek v4 Pro, Kimi K2.6, and GLM-5.1 (1 iteration in synthesis mode with DeepSeek v4 flash as judge) https://htmlpreview.github.io/?https://gist.githubuserconten...

### 6.5 DeepSeek V4 Pro 0813

**Thread** [49274600](https://news.ycombinator.com/item?id=49274600) · 1041 points · 453 comments (453 fetched) · 2026-08-12  
*23 matched comments · 22 distinct authors · 17 of 23 carry an artifact · 11 labelled below*

**1. scrlk** · [49275180](https://news.ycombinator.com/item?id=49275180) · 2026-08-12 · `benchmark` · artifacts: `link`, `version`, `code`  
> **Why this label:** The full ten-benchmark table for 0813 against Flash 0731, both Previews, GLM-5.2, Kimi-K3, Opus-4.8 and Fable 5.

> Benchmarks: | Benchmark | DS-V4-Pro | DS-V4-Flash | DS-V4-Pro | DS-V4-Flash | GLM-5.2 | Kimi-K3 | Opus-4.8 | Fable 5 | | | 0813 | 0731 | Preview | Preview | | | | (w/ fallback) | |--------------------------|-----------|-------------|-----------|-------------|-----------|-----------|-----------|---------------| | HLE (wo/w tools) | 42.7/60.0 | 37.8/51.5 | 37.7/48.2 | 34.8/45.1 | 40.5/54.7 | 43.5/56.0 | 49.8/57.9 | 53.3/63.0 | | Terminal Bench 2.1 | 87.9 | 82.7 | 72.1 | 61.8 | 81.0 | 88.3 | 85.0 | 88.0 | | NL2Repo | 61.5 | 54.2 | 38.5 | 39.4 | 48.9 | - | 69.7 | - | | Cybergym | 83.3 | 76.7 | 52.7 | 38.7 | - | 80.0 | 78.3 | 83.1 | | DeepSWE | 62.7 | 54.4 | 12.8 | 7.3 | 46.2 | 67.5 | 58.0 | 70.0 | | Toolathlon-Verified | 74.1 | 70.3 | 55.9 | 49.7 | 59.9 | 76.5 | 76.2 | 77.9 | | Agents' Last Exam | 25.7 | 25.2 | 16.5 | 15.8 | 23.8 | 27.6 | 25.7 | - | | AutomationBench (Public) | 31.8 | 25.1 |…

**2. sparkling** · [49275340](https://news.ycombinator.com/item?id=49275340) · 2026-08-12 · `opinion` · artifacts: `number`, `version`  
> **Why this label:** A speed-for-accuracy preference stated as a feel, with one unattributed percentage.

> deepseek-v4-flash feels so fast and snappy, i'm loving it. Happy to trade speed for the the 5% degraded benchmarking performance.

**3. networked** · [49275464](https://news.ycombinator.com/item?id=49275464) · 2026-08-12 · `comparison` · artifacts: `link`, `version`  
> **Why this label:** Names a concrete task MiMo solved that Flash could not, and points out the AA pages would not have predicted it.

> I haven't tried DeepSeek V4 Pro 0813 yet. Recent experience tells me that larger models are worth it in non-obvious ways. MiMo-V2.5-Pro solved problems that DeepSeek V4 Flash 0731 couldn't solve for me: for example, adding a live counter for elided reasoning lines to a terminal-based coding harness. You wouldn't be able to tell from the scores on their respective Artifical Analysis page ( https://artificialanalysis.ai/models/mimo-v2-5-pro , https://artificialanalysis.ai/models/deepseek-v4-flash ). I like the DeepSeek V4 models, though. They critiqued my engineering decisions better than MiMo, and they seem to have a distinct aesthetic in the SVGs they write.

**4. nolist_policy** · [49275586](https://news.ycombinator.com/item?id=49275586) · 2026-08-12 · `usage_demo` · artifacts: `link`, `number`, `version`  
> **Why this label:** Full unquantized Flash locally at full 1M context for $8000 of hardware, with the setup repo linked.

> DeepSeek V4 Flash is the "too cheap to meter" of AI. And you can run the full unquantized model locally for $8000 (2x DGX Spark) at full 1M context and decent speeds: https://github.com/elsung/dgx-spark-deepseek-v4-flash#-long-...

**5. Gecko4072** · [49275606](https://news.ycombinator.com/item?id=49275606) · 2026-08-12 · `announcement` · artifacts: `link`, `version`  
> **Why this label:** The pricing page plus the banner notice that Flash pricing rises first, amount undetermined.

> https://api-docs.deepseek.com/quick_start/pricing/ edit: there are banner announcements saying v4 flash pricing will increase first then overall by an undetermined amount

**6. parsimo2010** · [49275709](https://news.ycombinator.com/item?id=49275709) · 2026-08-12 · `comparison` · artifacts: `link`, `version`  
> **Why this label:** Benchmark-by-benchmark against Qwen3.8-max released the same day, with each published figure named and the vision caveat.

> The timing looks like they are trying to take the wind out of Qwen's sails by releasing this on the same day that Qwen released the weights of Qwen3.8-max. Or maybe it's coincidence... For comparison I looked at Qwen's claimed benchmarks for Qwen3.8-max ( https://qwen.ai/blog?id=qwen3.8 ). Assuming each published set of benchmarks is believable, it looks like v4 Pro 0813 is better on average but overall performance is comparable. Pro 0813 is much cheaper. If you don't need vision capabilities then you don't have much reason to use Qwen3.8-max. - 43.6 on HLE (Presumably without tools). Pro 0813 is a little worse. - 86.6 on Terminal Bench 2.1. Pro 0813 is better. - 55.9 on NL2Repo. Pro 0813 is better. - 27 on Agent's Last Exam. Pro 0813 is a little worse. - 72.5 on Toolathon-Verified. Pro 0813 is better. - 56.6 on DeepSWE 1.1. If the DeepSWE listed for Pro 0813 is the same version, then Pr…

**7. xynelius** · [49275775](https://news.ycombinator.com/item?id=49275775) · 2026-08-12 · `deep_analysis` · artifacts: `link`, `number`  
> **Why this label:** Per-request cost derived from OpenCode's published token split (750 in / 290 out / 82k cached): $0.000875 against $0.052 for Opus.

> If that wasn't impressive enough, it's actually ~60x cheaper if you take into account the typical cache-read/input/output split in agentic coding, and the deep discount for cache reads offered by DeepSeek. Opencode has some public data on the typical split [1]: For DeepSeek V4 Pro the typical split is 750 in, 290 out, 82k cached. Cost per request for V4 Pro: $0.000875 per request. Equivalent Opus cost (w/o taking into account cache write costs): $0.052 per request. [1] https://opencode.ai/docs/go/#usage-limits

**8. jklmnopqrstuvw** · [49275985](https://news.ycombinator.com/item?id=49275985) · 2026-08-12 · `benchmark` · artifacts: `number`, `version`  
> **Why this label:** Same feature built twice on Codex CLI: Pro 12m02s at $0.12 with a bug, Grok 4.6 3m18s at $1.41 without.

> Tested both DS v4 pro 0813 and Grok 4.6 (all from openrouter) on Codex cli. Worked on a same new feature development on my project. Deepseek 4 pro: Worked for 12m 02s - cost $0.12 - has bug. Grok 4.6: Worked for 3m 18s - cost $ 1.41 - no bug.

**9. taosx** · [49277160](https://news.ycombinator.com/item?id=49277160) · 2026-08-12 · `deep_analysis` · artifacts: `link`, `version`  
> **Why this label:** The author's harness cost simulation, with the caveat about which numbers to trust, concluding Pro beats the Luna models on caching.

> I created a simulation for coding harnesses based on my own pi sessions. When taking into account all factors, DS-v4-Pro is cheaper than gpt-5.6-luna due to caching. Look at the bill segments difference for cache read cost and uncached cost between deepseek and the other models. At this point is cheaper to use ds-v4-pro than the luna models from openai. ignore the numbers except the classic and keep in mind that classic is based on pi with the only change limiting tool output to 10kb https://harness.eveid.com/lazy-harness-cost-simulation * I built this for getting an initial estimate between different checkpoint/ compaction methods for the harness.

**10. gunalx** · [49282465](https://news.ycombinator.com/item?id=49282465) · 2026-08-13 · `opinion` · artifacts: `number`, `version`  
> **Why this label:** A multilingual-prose complaint about Flash, rated below the author's local Qwen, with no artifact beyond the comparison.

> Yeah. I stopped ising deepseek v4 flashbecause it is awful (even worse than my local qwen3.6 35B model) at multilingual prose.

**11. m00dy** · [49285797](https://news.ycombinator.com/item?id=49285797) · 2026-08-13 · `announcement` · artifacts: `number`, `version`  
> **Why this label:** The peak/off-peak price table with the exact UTC windows and effective date, plus the batching implication.

> DeepSeek is moving to peak/off-peak API pricing. Off-peak rates are 50% of peak rates. Peak: 01:00–04:00 UTC and 06:00–10:00 UTC Off-peak: all other hours New pricing takes effect August 16, 2026 at 16:00 UTC. Model Period Cache hit Cache miss Output (input / 1M) (input / 1M) (/ 1M) deepseek-v4-flash Off-peak $0.007 $0.22 $0.66 deepseek-v4-flash Peak $0.014 $0.44 $1.32 deepseek-v4-pro Off-peak $0.022 $0.66 $1.98 deepseek-v4-pro Peak $0.044 $1.32 $3.96 For batchable workloads, scheduling outside those two UTC windows cuts token costs in half.

### 6.6 DeepSeek makes the V4 Pro price discount permanent

**Thread** [48237663](https://news.ycombinator.com/item?id=48237663) · 621 points · 549 comments (534 fetched) · 2026-05-22  
*22 matched comments · 18 distinct authors · 16 of 22 carry an artifact · 8 labelled below*

**1. Reubend** · [48239072](https://news.ycombinator.com/item?id=48239072) · 2026-05-22 · `comparison` · artifacts: `number`, `version`  
> **Why this label:** Output price per million lined up across six named models.

> Props to them. That makes DeepSeek v4 Pro extremely cheap compared to others, even in the same category. Look at these prices per million outputs tokens: DeepSeek V4 Pro: $0.87 Qwen 3.7 Max: $7.50 Grok 4.3: $2.50 GLM 1.5: $3.08 Opus 4.7: $25.00 GPT-5.5: $30.00

**2. minimaxir** · [48241620](https://news.ycombinator.com/item?id=48241620) · 2026-05-22 · `deep_analysis` · artifacts: `link`, `number`, `version`  
> **Why this label:** Reads the caching clause: cache-hit input at 0.8% of input price for Pro, an effective ~$0.04/M, and notes there is no end date.

> I'm more curious about the caching: > (2) For all models, the input cache hit price has been reduced to 1/10 of the launch price. This price adjustment takes effect from 2026/4/26 12:15 UTC. There is no end date. Currently, it's 2% of the input price for DeepSeek V4 Flash and 0.8% with this new V4 Pro pricing, which is extremely low compared to competitors to the point that it affects the unit economics a bit and I thought it would be temporary. In the case of V4 Pro, the effective cost is ~$0.04/M input tokens given the caching (based on OpenRouter's metrics: https://openrouter.ai/deepseek/deepseek-v4-pro ), which is significantly cheaper than even small models from competitors.

**3. spudlyo** · [48242980](https://news.ycombinator.com/item?id=48242980) · 2026-05-22 · `usage_demo` · artifacts: `number`, `version`  
> **Why this label:** First-hand on Pi and Gptel - happy on price, unhappy on speed, with the reasoning trace called out as unusually transparent.

> I use it with Pi and with Gptel and I'm extremely happy about the price. The speed of deepseek-v4-pro though leaves something to be desired. I do love how detailed its chain of thought reasoning is, and it's pretty wild watching it think at ~2400 baud. It much more transparent than Gemini 3.5 flash in that regard, but maybe 4-5x slower? For my Latin language morphology and linguistic tasks it seems to be up to the job, and on the plus side I can analyze a handful of sentences parallel without worrying about breaking the bank.

**4. vinhnx** · [48243363](https://news.ycombinator.com/item?id=48243363) · 2026-05-23 · `promo` · artifacts: `link`, `version`  
> **Why this label:** The author's own coding agent now supports the model. Useful, but it is his project being advertised.

> You can use DeepSeek with my coding agent VT Code. Recently I've added DeepSeek V4 Pro and DeepSeek V4 Flash support with all providers, via: Official DeepSeek API, HuggingFace, Ollama Cloud, OpenRouter providers. > https://github.com/vinhnx/vtcode

**5. lot-xcvb** · [48258264](https://news.ycombinator.com/item?id=48258264) · 2026-05-24 · `deep_analysis` · artifacts: `link`, `number`  
> **Why this label:** Quotes the clause that sets post-promotion pricing at a quarter of the original, answering a claim in the thread.

> An API is a local model? https://api-docs.deepseek.com/quick_start/pricing "(3) The deepseek-v4-pro model API pricing will be officially adjusted to 1/4 of the original price after the 75% discount promotion ends on 2026/05/31 15:59 UTC."

**6. elcritch** · [48262042](https://news.ycombinator.com/item?id=48262042) · 2026-05-24 · `benchmark` · artifacts: `number`, `version`  
> **Why this label:** Cost-to-solve one task across models on OpenRouter, with the result against expectation: V4 Pro at $2.47 against GPT-5.4's $0.45.

> Yesterday I did some testing on the cost to solve the same simple problem on openrouter with different models using cline. Simple problem but it had a few nuances to solve it properly and so required reasoning. After reading comments like this I was expecting (hoping?) that DeepSeek or similar would be cheaper. However I was surprised that DeepSeek v4 cost about 5.5x GPT-5.4 to solve the problem. - Deepseek-v4-pro-medium cost $2.47 - GPT-5.4-medium cost $0.45 - GPT-5.5-low was $0.86

**7. nl** · [48262873](https://news.ycombinator.com/item?id=48262873) · 2026-05-25 · `benchmark` · artifacts: `link`, `number`, `version`  
> **Why this label:** Per-task rather than per-token costing from the author's own SQL benchmark: Kimi K2.5 at double the token price came in at $0.05 against $0.16.

> It's not unheard of for "more expensive" models (on a per-token basis) to end up cheaper than weaker models (on a per-task basis). Kimi K2.5 is roughly double the price (per token) of DeepSeek v4 Pro, but cost $0.05 vs $0.16 (for the same score) on my own benchmark. https://sql-benchmark.nicklothian.com/?highlight=moonshotai_... https://sql-benchmark.nicklothian.com/?highlight=deepseek_de...

**8. vinhnx** · [48263099](https://news.ycombinator.com/item?id=48263099) · 2026-05-25 · `usage_demo` · artifacts: `link`, `number`  
> **Why this label:** Cache-hit behaviour from integrating the model into his own agent, with the running total ($1.15 over two weekends). Self-referential but measured.

> DeepSeek's KV cache is impressive and very cost-efficient for long-horizon tasks. I tested on VT Code with DeepSeek V4 Pro, and the cache-hit ratio is high. *I build a coding agent and have recently improved and hardened DeepSeek V4 integration. I registered the DeepSeek API key, topped up just 2 USD, and used just DeepSeek V4 Pro and Flash with max thinking. So far the most visible improvement in both cost and context is the cache improvement; it's quite impressive with this announcement of a permanent price drop. ( https://xcancel.com/vinhnx/status/2058748305350557932 ). Currently, my usage is still at $1.15 after 2 full weekends.

### 6.7 MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 tokens per second

**Thread** [48446639](https://news.ycombinator.com/item?id=48446639) · 628 points · 489 comments (489 fetched) · 2026-06-08  
*13 matched comments · 11 distinct authors · 8 of 13 carry an artifact · 3 labelled below*

**1. RussianCow** · [48447778](https://news.ycombinator.com/item?id=48447778) · 2026-06-08 · `benchmark` · artifacts: `link`, `number`  
> **Why this label:** Throughput correction: the fastest Pro providers on OpenRouter are ~50tps, slower than Opus.

> Do you mean Flash and not Pro? I haven't tried it personally, but according to OpenRouter, the fastest DeekSeep V4 Pro providers are only ~50tps. That's slower than Claude Opus. https://openrouter.ai/deepseek/deepseek-v4-pro?sort=throughp...

**2. SwellJoe** · [48450276](https://news.ycombinator.com/item?id=48450276) · 2026-06-08 · `benchmark` · artifacts: `link`, `version`  
> **Why this label:** Pro fastest of 21 models in the author's runs, published - and the author names the confound himself, that he may have hit a quiet period.

> In recent benchmarking I've been doing, DeepSeek V4 Pro was the fastest of 21 models, by a comfortable margin ( https://swelljoe.com/html/bench-report-final.html ). Faster than Claude Opus 4.8, which was the second fastest (Mistral doesn't count because it seems to have refused to participate). But, it's a limited data set, just a few benchmark runs of a limited set of tasks. It's entirely possible I happened to be calling the API at its least busy time and maybe Claude got hit during a busy time.

**3. gertlabs** · [48450981](https://news.ycombinator.com/item?id=48450981) · 2026-06-08 · `benchmark` · artifacts: `link`, `version`  
> **Why this label:** Explains the ranking: Pro struggles with their custom harness so it is down-weighted on agentic tasks while leading one-shot, and warns about benchmaxxing.

> DeepSeek v4 Pro struggles with a custom harness, and all the models ranked above it don't, so it gets downweighted in the agentic coding benchmarks (although it ranks better than Flash in one-shot problem solving: https://gertlabs.com/rankings?ow=1&mode=oneshot_coding ). We ran plenty of samples. MiMo v2.5 is on there, as well as the pro version. We found a few anomalies in our evaluations, which makes sense -- if every new sub-release is better across the board in every area of the model card, that should raise alarms about benchmaxxing. But the main thing we found is that hype != performance, and I trust our benchmark methodology significantly more than the model cards the labs add to their press releases.

### 6.8 Claude Opus 4.8

**Thread** [48311647](https://news.ycombinator.com/item?id=48311647) · 1774 points · 1376 comments (1000 fetched) · 2026-05-28  
*10 matched comments · 8 distinct authors · 7 of 10 carry an artifact · 3 labelled below*

**1. pants2** · [48313418](https://news.ycombinator.com/item?id=48313418) · 2026-05-28 · `comparison` · artifacts: `link`, `number`  
> **Why this label:** Third-party hosting against first-party: DeepInfra $1.30/$2.60 at 37 t/s on an FP4 quant, against DeepSeek's $0.435/$0.87.

> Not similar. DeepInfra[1] has DS4 Pro pricing at $1.30/$2.60 which is 3X the Deepseek[2] (Chinese) hosting at $0.435/$0.87. DeepInfra is also very slow at 37 t/s and uses an FP4 quant[3], so intelligence will be degraded slightly. Meanwhile you could use Grok 4.3 for the same price which is smarter and 5X faster[4]. 1. https://deepinfra.com/pricing 2. https://api-docs.deepseek.com/quick_start/pricing 3. https://artificialanalysis.ai/models/deepseek-v4-pro/provide... 4. https://artificialanalysis.ai/models/grok-4-3

**2. slopinthebag** · [48315040](https://news.ycombinator.com/item?id=48315040) · 2026-05-28 · `comparison` · artifacts: `number`, `version`  
> **Why this label:** Positions Pro against Sonnet and argues Opus 4.5 is the fairer comparison.

> Deepseek v4 Pro on US hosting is like 1.5x cheaper and 5x cheaper on input/output compared to Sonnet, and that's not even a fair comparison because Deepseek is much stronger than Sonnet. It's more reasonable to compare with Opus 4.5, which is much more expensive.

**3. joshhart** · [48318989](https://news.ycombinator.com/item?id=48318989) · 2026-05-29 · `comparison` · artifacts: `link`, `number`  
> **Why this label:** Fireworks' three-part pricing for the model, called about a third of Sonnet.

> Fireworks will serve them for $1.74 / $0.14 / $3.48. That's input / cached input / output. https://fireworks.ai/models/deepseek-ai/deepseek-v4-pro . Call it about a third the price of Sonnet. Not nearly as cheap as the Chinese infra but still pretty cheap.

### 6.9 DeepSeek reasonix, DeepSeek native coding agent with high caching and low cost

**Thread** [48256953](https://news.ycombinator.com/item?id=48256953) · 729 points · 288 comments (288 fetched) · 2026-05-24  
*9 matched comments · 8 distinct authors · 6 of 9 carry an artifact · 1 labelled below*

**1. stavros** · [48261733](https://news.ycombinator.com/item?id=48261733) · 2026-05-24 · `deep_analysis` · artifacts: `number`, `code`  
> **Why this label:** Real billing dump from the author's own script: 486.3M tokens, 97.27% cache hit, $10 paid against a $241.79 Sonnet-equivalent.

> Here are my stats (from DeepSeek directly, with a script I wrote). The prices are what equivalent Sonnet usage would have cost, the actual amount I paid was $10. On performance, DeepSeek V4 Pro is comparable to Sonnet for me. ./cost.py amount-2026-5.csv 0.3 3.75 15 input_cache_hit_tokens: 472,971,520 tokens -> $141.8915 input_cache_miss_tokens: 13,299,013 tokens -> $49.8713 output_tokens: 3,334,962 tokens -> $50.0244 cache hit rate: 97.27% (472,971,520/486,270,533) cache miss rate: 2.73% (13,299,013/486,270,533) total: $241.7872 All of this usage was with an OpenCode subagent exclusively.

### 6.10 GLM 5.2 and the coming AI margin collapse

**Thread** [48809877](https://news.ycombinator.com/item?id=48809877) · 694 points · 469 comments (469 fetched) · 2026-07-06  
*9 matched comments · 9 distinct authors · 7 of 9 carry an artifact · 3 labelled below*

**1. KronisLV** · [48811296](https://news.ycombinator.com/item?id=48811296) · 2026-07-06 · `comparison` · artifacts: `link`, `number`, `version`  
> **Why this label:** Places GLM 5.2 above V4 Pro from sustained use, with the subscription quota arithmetic that made the author reconsider.

> They have a vision MCP to make up for the model itself not having the capability natively: https://docs.z.ai/devpack/mcp/vision-mcp-server I also found their web search to be mostly okay. Furthermore, in case this is of interest to anyone, if you use their ZCode harness then you get bigger Coding Plan quotas: https://zcode.z.ai/en Used it for a bit, it sits somewhere between OpenCode Desktop (still new but nice) and Claude Desktop (recent versions are good). As for GLM 5.2 as a model - with max thinking it’s generally satisfactory, somewhere between Sonnet 5 and Opus 4.8, better than DeepSeek V4 Pro for sure. Pricing wise, the subscription doesn’t seem as good as expected. I spent like 60% of the weekly limits of the Pro (50 USD) plan in one day, only because each 5 hour limit only gave me 20% to spend, otherwise it’d be 80-100%. Not even doing anything crazy, just parallel long form wor…

**2. AgentMasterRace** · [48812660](https://news.ycombinator.com/item?id=48812660) · 2026-07-07 · `comparison` · artifacts: `number`, `version`  
> **Why this label:** A concrete failure: a Fable-written implementation guide executed by V4 Pro came back ~80% wrong by Fable's own assessment, where GLM 5.2 did better.

> I don't think the writer has used top tier models very much. I have subscriptions to basically every provider, the difference between glm5.2 and opus is not even close, the gap is huge. raw benchmarks glm is impressive , but in practice these models are lacking so much. I had fable create a detailed implementation guide that explained how to implement everything in immense detail, it included all the libraries to use and versions. I then had deepseek v4 pro execute and it used old versions , different libraries and cut corners. Fable said about 80% was implemented wrong. I had GLM 5.2 do the same, and it performed exceptionally better, but when it got stuck on something it would be trial and error mode going forward and have zero foresight for future issues that might occur due to fixes it was trying. the model severally lacks prompt understanding, and testing .

**3. Obertr** · [48813015](https://news.ycombinator.com/item?id=48813015) · 2026-07-07 · `opinion` · artifacts: `number`, `version`  
> **Why this label:** The commodity-abundance framing, carrying the two published prices as its only artifact.

> Metaphor i like is that it will be as cheap as electricty? Do you know who is supplying your electricity or which factory it runs on? probably no, bc its a commodity and mostly settled and there is so many energy resources. some are alternative some are coal mines. And they all fight in the supply demand trade for energy which is happening real time ( think open router here) And eventually the consumer wins bc of the abundance. I think greatest example of abundance of cheap infinite intelligence will be not glm5.2 but DeepSeek V4 Pro max with $0.435 per 1M input tokens and $0.87 per 1M output tokens

### 6.11 Uber's $1,500/month AI limit is a useful signal for AI tool pricing

**Thread** [48383056](https://news.ycombinator.com/item?id=48383056) · 624 points · 769 comments (769 fetched) · 2026-06-03  
*9 matched comments · 9 distinct authors · 8 of 9 carry an artifact · 4 labelled below*

**1. dakolli** · [48392791](https://news.ycombinator.com/item?id=48392791) · 2026-06-04 · `deep_analysis` · artifacts: `number`, `version`  
> **Why this label:** Argues Western inference providers set the floor price and that ~$0.80/M was never intended to be permanent.

> Deepseek's api platform for V4 Pro is the only example of this, and Deepseek V4 Flash is cheaper (usually) than from Deepseek itself on openrouter via DeepInfra. Deepseek shot themselves in the foot because they never intended to serve V4 Pro for .80c mm ouput, that was a promotional price that was meant to expire (and still might). They intended for v4 to cost $4.00 per million but Western inference providers drove down the price because they can operate at negative margins to try and push competition out. I can assure you they are losing a ton of money @ ~80cents. My point is, its Western inference providers that are establishing the floor price of inference. They are willing to operate at a loss in order to put their competition out of business. Chinese providers are typically at or above the prices set by American/western providers if you go looking on the Chinese internet. You aren'…

**2. vinzenzu** · [48395242](https://news.ycombinator.com/item?id=48395242) · 2026-06-04 · `deep_analysis` · artifacts: `link`, `version`  
> **Why this label:** Uses the provider list and a third-party cost analysis to argue the cheap Chinese prices are closer to true cost than the US API prices.

> API prices of Anthropic, OpenAI, and Google are massively inflated. https://martinalderson.com/posts/no-it-doesnt-cost-anthropic... There's no way that all AI inference providers are colluding and/or all running at a massive loss, meaning the cheap Chinese model prices must be the real cost it takes to run frontier-class models PLUS their margin. Look at Deepseek 4 Pro. https://openrouter.ai/deepseek/deepseek-v4-pro/providers Deepseek and Baidu are subsidising prices but they probably train on inputs. I have no model training and ZDR in OpenRouter enabled, and the first provider that shows up there is Deepinfra, significantly more expensive than Deepseek. BUT much cheaper than Sonnet 4.6 and ChatGPT GPT-5.4.

**3. gpugreg** · [48396839](https://news.ycombinator.com/item?id=48396839) · 2026-06-04 · `comparison` · artifacts: `link`, `number`  
> **Why this label:** Two providers' exact three-part prices side by side, offered to settle a disagreement.

> Not as far as I can tell. Are we seeing different things? For deepseek-v4-pro: - $0.350 in, $0.003000 cache, $0.80 out https://crof.ai/pricing - $0.435 in, $0.003625 cache, $0.87 out https://api-docs.deepseek.com/quick_start/pricing

**4. KronisLV** · [48404092](https://news.ycombinator.com/item?id=48404092) · 2026-06-04 · `usage_demo` · artifacts: `number`, `version`  
> **Why this label:** Substituting Pro at Max reasoning for Opus 4.8 after hitting subscription limits: passable, with repeated corrections and token waste.

> > Perhaps programmers in these countries will use cheaper models like Deepseek and they will be able to compete better, so offshoring continues? Even here, companies don't really trust Eastern providers that much, so they'd be looking for someone in the EU running DeepSeek instances, which might come with a bit of markup. Those orgs would also sometimes be weary of OpenRouter which to me seems like shooting yourself in the foot by being so picky. That said, DeepSeek V4 Pro (with Max reasoning) is pretty okay and I'm using it instead of Opus 4.8 (my Max 100 USD subscription weekly limits ran out today) and it can do stuff passably (even better than Mistral's offering and has nice context window), but compared to the amount of work I can get done with Anthropic's models, it keeps occasionally fucking up and I have to go back and correct it, so lots of token waste. Maybe it's close to SOTA…

### 6.12 Access to frontier AI will soon be limited by economic and security constraints

**Thread** [48143284](https://news.ycombinator.com/item?id=48143284) · 228 points · 216 comments (216 fetched) · 2026-05-15  
*9 matched comments · 7 distinct authors · 6 of 9 carry an artifact · 5 labelled below*

**1. trollbridge** · [48144828](https://news.ycombinator.com/item?id=48144828) · 2026-05-15 · `opinion` · artifacts: `number`, `version`  
> **Why this label:** The cost collapse as felt rather than measured - $150 of work a year ago now 35 cents - with no source for either figure.

> But a “good enough” lamp just got a lot cheaper. The cost of tokens on DeepSeek V4 Pro is so low I don’t even think about and currently am trying to figure out useful things for as many agents simultaneously running as I can. What would have cost $150 less than a year ago now costs 35¢. Likewise Qwen 3.6 absolutely blows me away and that’s on a 35b 6-bit model on a local 5090. Same thing, busy trying to find stuff to do to keep it busy 24/7. I can still find some niches for Opus 4.7 but being able to attack problems and not worry about consumption is a game changer.

**2. cubefox** · [48145354](https://news.ycombinator.com/item?id=48145354) · 2026-05-15 · `news_roundup` · artifacts: `link`, `version`  
> **Why this label:** Points at the NIST CAISI evaluation and its graph, and says plainly that the model found the link.

> Someone recently made a graph showing that the gap between US American frontier LLMs and Chinese open weight LLMs (including DeepSeek v4) is widening. Unfortunately I can't find it anymore. Update: GPT-5.5 found it. Article: https://www.nist.gov/news-events/news/2026/05/caisi-evaluati... Graph: https://www.nist.gov/sites/default/files/images/2026/05/01/1...

**3. pjerem** · [48145833](https://news.ycombinator.com/item?id=48145833) · 2026-05-15 · `usage_demo` · artifacts: `link`, `number`  
> **Why this label:** Two weeks on an Ollama Cloud subscription without hitting the limits that one Opus prompt could exhaust.

> Hum, I'm using it [0] with my Ollama Cloud subscription since the last two weeks and I love it. Never reached the 5 hours usage limits of the $20 plan (on side projects) where I would reach it sometimes in ONE prompt with Opus. [0]: https://ollama.com/library/deepseek-v4-pro

**4. DCKing** · [48145930](https://news.ycombinator.com/item?id=48145930) · 2026-05-15 · `comparison` · artifacts: `link`, `version`  
> **Why this label:** Corrects the state of the art in the parent's comparison, naming release dates and context sizes across four families.

> Deepseek V4 came out three weeks ago: https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro Kimi K2.5 has also been superseded by a finer tuned Kimi K2.6 three weeks ago. Moonshot's Kimi models appear to be the favored Chinese model, at least for coding, and not Deepseek V4. z.AI's GLM 5.1 is also worth mentioning as rather competent for coding, also released in April. Those models too will not be beating US AI labs by your metrics (although for coding, Kimi K2.6 might beat the very uneven Gemini depending on the situation), but in your critism at least consider the state of the art in your comparisons.

**5. ageitgey** · [48146121](https://news.ycombinator.com/item?id=48146121) · 2026-05-15 · `opinion` · artifacts: `number`, `version`  
> **Why this label:** Argues benchmarks miss domain feel, with a made-up example the author flags as made up.

> On the same topic but from a slightly different angle - as SOTA models get more capable, the 'quality' and 'feel' of the experience they provide in each domain is heavily dependent on the reinforcement learning the vendor does for that specific domain. After all, many fields have 100 flavors of "good answers," but the model has to pick one answer. Benchmarks are not very good at capturing this yet. But it could be the case that DeepSeek v4 Pro is 100% as good as Claude Opus 4.7 at scaffolding a basic Rails app, but absolutely terrible at creating a credible business plan that another businessperson would think is real. That's a made-up example, but you get the point. The end result will be a lot of people arguing about which model is "better," but "better" depends heavily on the task and how that model was trained to interact with the user for that task. Two users may have very different…

### 6.13 GLM 5.2 beats Claude in our benchmarks

**Thread** [48709670](https://news.ycombinator.com/item?id=48709670) · 1113 points · 516 comments (516 fetched) · 2026-06-28  
*8 matched comments · 7 distinct authors · 6 of 8 carry an artifact · 3 labelled below*

**1. SwellJoe** · [48712434](https://news.ycombinator.com/item?id=48712434) · 2026-06-28 · `benchmark` · artifacts: `link`, `version`  
> **Why this label:** Security bug-hunting benchmark across releases: Pro consistently among the best while MiMo's early showing did not hold, plus the finding that semgrep-as-a-tool made models worse.

> I added GLM 5.2 to my security bug hunting benchmark when it came out, and found it to be a good performer, but not the best open model. The benchmark tests whether models can find bugs Mythos found. The best open models in the initial benchmark were DeepSeek V4 Pro or MiMo 2.5 Pro. But it turned out MiMo got lucky, it's performed worse on almost every test I've done since, while DeepSeek has consistently been among the best performers and its extreme caching performance makes it cheaper than just about anything, including much smaller models. https://swelljoe.com/post/will-it-mythos/ Also of note, I found giving models access to the open source semgrep as a tool makes some perform worse and none perform better, though it's plausible there's a way to wire it up in a harness that presents useful information to the model without the model having to know how to use it (my theory is that sem…

**2. lebovic** · [48713609](https://news.ycombinator.com/item?id=48713609) · 2026-06-29 · `benchmark` · artifacts: `link`, `number`  
> **Why this label:** Points at the author's own write-up on how the two models approach security research differently, with the version caveat stated.

> GLM 5.2 and DeepSeek v4 Pro seem to approach security research differently. This benchmark was with GLM 5.1, but the patterns are similar: https://dualuse.dev/posts/deepseek-v4-thinks-different Overall, I still think GLM 5.2 is the much stronger performer. It's hard to tell the difference between GLM 5.2 and Opus at <120k tokens.

**3. neya** · [48714414](https://news.ycombinator.com/item?id=48714414) · 2026-06-29 · `usage_demo` · artifacts: `number`, `version`  
> **Why this label:** Elixir work across both models with the actual bills - $20/day on GLM via OpenRouter against $10 lasting six weeks on DeepSeek direct.

> I am seeing extremely positive results with Elixir too. Previously I was on Deepseek (deepseek-v4-pro) and GLM5.2 outperforms Deepseek easily. It's been a month since I used any native Claude models (simply because of pricing) but then, GLM5.2 is running for me at $20/day in usage on OpenRouter for GLM5.2. I am not sure if I've misconfigured Claude code or if this is indeed normal usage pricing. But, the output more than makes up for it. However, using Deepseek v4 pro directly from deepseek.com using their discounted pricing is insanely cost efficient. I topped up $10 a month and a half ago and I'm still yet to use up all the money in my account. Here's hoping that SOTA models become even cheaper!

### 6.14 Kimi K2.7-Code: open-source coding model with better token efficiency

**Thread** [48502347](https://news.ycombinator.com/item?id=48502347) · 463 points · 240 comments (240 fetched) · 2026-06-12  
*8 matched comments · 7 distinct authors · 7 of 8 carry an artifact · 3 labelled below*

**1. trollbridge** · [48503533](https://news.ycombinator.com/item?id=48503533) · 2026-06-12 · `workflow` · artifacts: `number`, `version`  
> **Why this label:** A multi-provider routing recipe with the prices to sign up at and what to send where.

> I am extremely happy with ohmypi, but you could use OpenCode or just keep using Claude Code! DeepSeek-V4-Pro is adequate plus use DS4-Flash for tasks or other small activity you’d use Haiku or Sonnet for. Go sign up with $10 prepaid. OpenCode Go - go sign up with $5 for a month and use Qwen-3.7-Max for design/plan/architecture or difficult troubleshooting. Feels closer to Opus 3.6 or 3.7 than DeepSeek, closest I’ve found. OpenAI Codex, $20 a month plan, use GPT-5.5 via API for the same design/plan/architecture/troubleshooting/author commits. (You can also pay $100 and cut and paste really difficult problems into chat with the GPT-5.5-Pro model.) Xiaomi MiMo-2.5-Pro, find a friend to give you a $2 referral code, you get 72 cents free. Same pricing as DeepSeek. Somewhere between Sonnet and Opus, quite capable. Apply for the UltraSpeed beta too. You can switch in and out from these models o…

**2. bel8** · [48506648](https://news.ycombinator.com/item?id=48506648) · 2026-06-12 · `comparison` · artifacts: `link`, `number`  
> **Why this label:** Argues DS4 over GLM 5.1 on context window with a benchmark comparison linked.

> How so? In my experience trying these models using opencode Go, DeepSeek is superior to GLM 5.1. If anything, DS4 has 1 million context window, while GLM 5.1 has 200K. There are also benchmarks comparing the two: https://artificialanalysis.ai/models/comparisons/deepseek-v4...

**3. mdasen** · [48507479](https://news.ycombinator.com/item?id=48507479) · 2026-06-12 · `deep_analysis` · artifacts: `number`, `version`  
> **Why this label:** Cached-input arithmetic for a real token mix: Kimi K2.7 Code is 53x more expensive on the 95% of spend that is cached input.

> I find that I don't use a ton of output tokens. I'm usually around 95% cached input, 4% input, and 1% output. For me, the big thing with MiMo-V2.5-Pro and DeepSeek V4-Pro is that cached inputs are practically free. Kimi K2.7 Code is 53x more expensive for cached inputs which is 95% of my costs. If I use 95M cached input tokens, 4M input tokens, and 1M output tokens, that'd be: $18 for cached input on Kimi K2.7 Code vs $0.34 with MiMo/DS; $3.80 for inputs on Kimi vs $1.74 with MiMo/DS; and $4 for output on Kimi vs $0.87 with MiMo/DS. Of all the places where I'm accumulating costs by using Kimi, it's the cached inputs. The real savings with MiMo/DS's price cut is the cached inputs.

## 7. Every thread containing a match

All 236 of them, most-matched first. `matched` counts comments carrying the model's name; `comments` is the thread's own size, so the ratio is visible. A thread appears here because a comment in it matched, which does not make the thread about the model.

| Thread | Date | Pts | Comments | Fetched | Matched | Authors | With artifact |
|---|---|---|---|---|---|---|---|
| [DeepClaude – Claude Code agent loop with DeepSeek V4 Pro](https://news.ycombinator.com/item?id=48002136) | 2026-05-03 | 678 | 281 | 281 | 30 | 27 | 16 |
| [DeepSeek V4 Pro beats GPT-5.5 Pro on precision](https://news.ycombinator.com/item?id=48440448) | 2026-06-08 | 397 | 225 | 225 | 26 | 21 | 22 |
| [DeepSeek v4](https://news.ycombinator.com/item?id=47884971) | 2026-04-24 | 2091 | 1607 | 1000 | 24 | 21 | 24 |
| [DeepSeek V4 – almost on the frontier](https://news.ycombinator.com/item?id=47977026) | 2026-05-01 | 677 | 398 | 397 | 24 | 21 | 22 |
| [DeepSeek V4 Pro 0813](https://news.ycombinator.com/item?id=49274600) | 2026-08-12 | 1041 | 453 | 453 | 23 | 22 | 17 |
| [DeepSeek makes the V4 Pro price discount permanent](https://news.ycombinator.com/item?id=48237663) | 2026-05-22 | 621 | 549 | 534 | 22 | 18 | 16 |
| [MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 tokens per second](https://news.ycombinator.com/item?id=48446639) | 2026-06-08 | 628 | 489 | 489 | 13 | 11 | 8 |
| [Claude Opus 4.8](https://news.ycombinator.com/item?id=48311647) | 2026-05-28 | 1774 | 1376 | 1000 | 10 | 8 | 7 |
| [DeepSeek reasonix, DeepSeek native coding agent with high cachin](https://news.ycombinator.com/item?id=48256953) | 2026-05-24 | 729 | 288 | 288 | 9 | 8 | 6 |
| [GLM 5.2 and the coming AI margin collapse](https://news.ycombinator.com/item?id=48809877) | 2026-07-06 | 694 | 469 | 469 | 9 | 9 | 7 |
| [Uber's $1,500/month AI limit is a useful signal for AI tool pric](https://news.ycombinator.com/item?id=48383056) | 2026-06-03 | 624 | 769 | 769 | 9 | 9 | 8 |
| [Access to frontier AI will soon be limited by economic and secur](https://news.ycombinator.com/item?id=48143284) | 2026-05-15 | 228 | 216 | 216 | 9 | 7 | 6 |
| [GLM 5.2 beats Claude in our benchmarks](https://news.ycombinator.com/item?id=48709670) | 2026-06-28 | 1113 | 516 | 516 | 8 | 7 | 6 |
| [Kimi K2.7-Code: open-source coding model with better token effic](https://news.ycombinator.com/item?id=48502347) | 2026-06-12 | 463 | 240 | 240 | 8 | 7 | 7 |
| [Claude Fable 5](https://news.ycombinator.com/item?id=48463808) | 2026-06-09 | 2626 | 2159 | 1000 | 7 | 7 | 4 |
| [Kimi K3: Open Frontier Intelligence](https://news.ycombinator.com/item?id=48935342) | 2026-07-16 | 2107 | 1216 | 1000 | 7 | 7 | 6 |
| [Qwen 3.8 27B](https://news.ycombinator.com/item?id=49299605) | 2026-08-14 | 1438 | 793 | 786 | 7 | 6 | 5 |
| [Qwen 3.8](https://news.ycombinator.com/item?id=48966120) | 2026-07-19 | 961 | 731 | 706 | 7 | 6 | 5 |
| [GLM-5.2 is the new leading open weights model on Artificial Anal](https://news.ycombinator.com/item?id=48567759) | 2026-06-17 | 916 | 444 | 444 | 7 | 7 | 7 |
| [DeepSeek V4 Flash 0731](https://news.ycombinator.com/item?id=49214008) | 2026-08-07 | 796 | 476 | 476 | 7 | 5 | 7 |
| [Advancing the price-performance frontier with GPT‑5.6](https://news.ycombinator.com/item?id=49112867) | 2026-07-30 | 610 | 402 | 402 | 6 | 6 | 3 |
| [There is minimal downside to switching to open models](https://news.ycombinator.com/item?id=48622518) | 2026-06-21 | 407 | 330 | 330 | 6 | 5 | 5 |
| [Statement on US government directive to suspend access to Fable ](https://news.ycombinator.com/item?id=48511072) | 2026-06-13 | 3158 | 2314 | 1000 | 5 | 5 | 3 |
| [Ask HN: Has anyone replaced Claude/GPT with a local model for da](https://news.ycombinator.com/item?id=48542100) | 2026-06-15 | 1318 | 563 | 563 | 5 | 5 | 4 |
| [I think Anthropic and OpenAI have found product-market fit](https://news.ycombinator.com/item?id=48296794) | 2026-05-27 | 1094 | 1245 | 1000 | 5 | 5 | 4 |
| [DSpark: Speculative decoding accelerates LLM inference [pdf]](https://news.ycombinator.com/item?id=48696585) | 2026-06-27 | 797 | 361 | 361 | 5 | 5 | 4 |
| [A few words on DS4](https://news.ycombinator.com/item?id=48142108) | 2026-05-14 | 440 | 190 | 190 | 5 | 5 | 1 |
| [Kimi K2.6 just beat Claude, GPT-5.5, and Gemini in a coding chal](https://news.ycombinator.com/item?id=47993235) | 2026-05-03 | 380 | 219 | 219 | 5 | 5 | 4 |
| [Previewing GPT‑5.6 Sol: a next-generation model](https://news.ycombinator.com/item?id=48689028) | 2026-06-26 | 1139 | 744 | 748 | 4 | 4 | 4 |
| [Gemini 3.5 Flash](https://news.ycombinator.com/item?id=48196570) | 2026-05-19 | 962 | 658 | 647 | 4 | 4 | 4 |
| [Identity verification on Claude](https://news.ycombinator.com/item?id=48618455) | 2026-06-21 | 866 | 735 | 735 | 4 | 4 | 3 |
| [Anthropic says Alibaba illicitly extracted Claude AI model capab](https://news.ycombinator.com/item?id=48664814) | 2026-06-24 | 813 | 1324 | 1000 | 4 | 4 | 4 |
| [DeepSeek-V4-Flash Update](https://news.ycombinator.com/item?id=49119559) | 2026-07-31 | 745 | 347 | 347 | 4 | 3 | 4 |
| [GPT-5.5 hallucinates 3x more than MIT-licensed GLM-5.2](https://news.ycombinator.com/item?id=48600167) | 2026-06-19 | 585 | 294 | 294 | 4 | 4 | 4 |
| [Hy3](https://news.ycombinator.com/item?id=48847552) | 2026-07-09 | 561 | 120 | 120 | 4 | 4 | 4 |
| [GLM-5.2 is a step change for open agents](https://news.ycombinator.com/item?id=48639840) | 2026-06-23 | 367 | 223 | 223 | 4 | 4 | 3 |
| [AI coding at home without going broke](https://news.ycombinator.com/item?id=48518969) | 2026-06-13 | 352 | 294 | 294 | 4 | 4 | 4 |
| [LongCat-2.0, a large-scale MoE model with 1.6T total and 48B Act](https://news.ycombinator.com/item?id=48727116) | 2026-06-30 | 281 | 88 | 88 | 4 | 3 | 0 |
| [The current AI pricing was always going to go away](https://news.ycombinator.com/item?id=48234391) | 2026-05-22 | 82 | 91 | 91 | 4 | 4 | 4 |
| [Claude Code is steganographically marking requests](https://news.ycombinator.com/item?id=48734373) | 2026-06-30 | 2445 | 750 | 750 | 3 | 2 | 2 |
| [Kimi K3 Is Competitive with Fable; Kimi K3 and Fable Is SoTA](https://news.ycombinator.com/item?id=48999291) | 2026-07-21 | 877 | 451 | 451 | 3 | 3 | 3 |
| [Qwen3.8-2.4T](https://news.ycombinator.com/item?id=49273478) | 2026-08-12 | 713 | 171 | 171 | 3 | 2 | 3 |
| [The Kimi K3 Moment](https://news.ycombinator.com/item?id=48960218) | 2026-07-18 | 636 | 613 | 613 | 3 | 3 | 1 |
| [GLM-5.2 – How to Run Locally](https://news.ycombinator.com/item?id=48636377) | 2026-06-22 | 617 | 305 | 305 | 3 | 3 | 2 |
| [MAI-Code-1-Flash](https://news.ycombinator.com/item?id=48374466) | 2026-06-02 | 540 | 255 | 255 | 3 | 3 | 3 |
| [US holds off blacklisting DeepSeek, more than 100 firms deemed s](https://news.ycombinator.com/item?id=48565498) | 2026-06-17 | 537 | 603 | 603 | 3 | 3 | 3 |
| [Ask HN: What is your (AI) dev tech stack / workflow?](https://news.ycombinator.com/item?id=48413629) | 2026-06-05 | 171 | 136 | 136 | 3 | 3 | 2 |
| [Show HN: State of the Art of Coding Models, According to Hacker ](https://news.ycombinator.com/item?id=47990708) | 2026-05-02 | 168 | 87 | 87 | 3 | 3 | 3 |
| [The OnlyFans Economy of American AI](https://news.ycombinator.com/item?id=48435371) | 2026-06-07 | 146 | 204 | 204 | 3 | 3 | 3 |
| [Xiaomi MiMo-v2.5 Series API Permanent Price Reduction Up to 99%](https://news.ycombinator.com/item?id=48282814) | 2026-05-26 | 134 | 160 | 160 | 3 | 3 | 3 |
| [DeepSeek API Pricing Update](https://news.ycombinator.com/item?id=49285160) | 2026-08-13 | 130 | 185 | 137 | 3 | 3 | 3 |
| [Bringing Up DeepSeek-V4-Flash on AMD MI300X](https://news.ycombinator.com/item?id=48373675) | 2026-06-02 | 120 | 25 | 25 | 3 | 3 | 1 |
| [UK sovereign LLM inference](https://news.ycombinator.com/item?id=48146424) | 2026-05-15 | 107 | 112 | 112 | 3 | 2 | 2 |
| [DeepSeek V4 Pro at 75% off until 31 May](https://news.ycombinator.com/item?id=48043040) | 2026-05-06 | 87 | 86 | 86 | 3 | 3 | 2 |
| [Bringing the cybersecurity capabilities of Claude Mythos 5 to mo](https://news.ycombinator.com/item?id=49392331) | 2026-08-21 | 50 | 52 | 52 | 3 | 3 | 3 |
| [Ask HN: Which cheap Chinese LLM are you using?](https://news.ycombinator.com/item?id=48523455) | 2026-06-14 | 18 | 9 | 9 | 3 | 2 | 3 |
| [Kimi-K3 on HuggingFace](https://news.ycombinator.com/item?id=49065752) | 2026-07-27 | 1382 | 544 | 544 | 2 | 2 | 2 |
| [Claude Code refuses requests or charges extra if your commits me](https://news.ycombinator.com/item?id=47963204) | 2026-04-30 | 1349 | 720 | 720 | 2 | 2 | 2 |
| [Inkling: Our Open-Weights Model](https://news.ycombinator.com/item?id=48924912) | 2026-07-15 | 1227 | 294 | 294 | 2 | 2 | 2 |
| [Qwen 3.6 27B is the sweet spot for local development](https://news.ycombinator.com/item?id=48721903) | 2026-06-29 | 1192 | 759 | 759 | 2 | 2 | 2 |
| [Qwen3.8-Max: A New Bar for Coding and Cowork](https://news.ycombinator.com/item?id=49150470) | 2026-08-03 | 1124 | 615 | 615 | 2 | 2 | 2 |
| [Microsoft and OpenAI end their exclusive and revenue-sharing dea](https://news.ycombinator.com/item?id=47921248) | 2026-04-27 | 990 | 845 | 836 | 2 | 2 | 2 |
| [Department of Commerce has lifted export controls on Claude Fabl](https://news.ycombinator.com/item?id=48740771) | 2026-06-30 | 977 | 692 | 693 | 2 | 2 | 2 |
| [AMD acquires Taalas to boost inference performance by etching mo](https://news.ycombinator.com/item?id=49201970) | 2026-08-06 | 949 | 724 | 723 | 2 | 2 | 1 |
| [GLM 5.2 Is Out](https://news.ycombinator.com/item?id=48518684) | 2026-06-13 | 772 | 504 | 504 | 2 | 2 | 1 |
| [Gemini 3.6 Flash, 3.5 Flash-Lite, and 3.5 Flash Cyber](https://news.ycombinator.com/item?id=48993414) | 2026-07-21 | 760 | 577 | 577 | 2 | 2 | 1 |
| [Grok 4.6](https://news.ycombinator.com/item?id=49274027) | 2026-08-12 | 632 | 616 | 615 | 2 | 2 | 1 |
| [DeepSeek V4 Flash 0731 Intelligence, Performance and Price Analy](https://news.ycombinator.com/item?id=49120299) | 2026-07-31 | 594 | 312 | 312 | 2 | 2 | 1 |
| [MiMo Code is now released and open-source](https://news.ycombinator.com/item?id=48490826) | 2026-06-11 | 557 | 315 | 315 | 2 | 2 | 1 |
| [Higher usage limits for Claude and a compute deal with SpaceX](https://news.ycombinator.com/item?id=48037986) | 2026-05-06 | 512 | 486 | 486 | 2 | 2 | 2 |
| [DeepSeek Introduces Vision](https://news.ycombinator.com/item?id=48581458) | 2026-06-18 | 498 | 204 | 204 | 2 | 2 | 1 |
| [I turned a $80 RK3562 Android tablet into a Debian Linux worksta](https://news.ycombinator.com/item?id=48168668) | 2026-05-17 | 449 | 237 | 237 | 2 | 2 | 0 |
| [Anthropic surpasses OpenAI to become most valuable AI startup](https://news.ycombinator.com/item?id=48336233) | 2026-05-30 | 422 | 472 | 472 | 2 | 2 | 2 |
| [Nativ: Run frontier open models locally on your Mac](https://news.ycombinator.com/item?id=48982681) | 2026-07-20 | 377 | 131 | 131 | 2 | 2 | 2 |
| [A $500 RL fine-tune of a 9B open model beat frontier models on c](https://news.ycombinator.com/item?id=49078454) | 2026-07-28 | 342 | 128 | 128 | 2 | 2 | 1 |
| [OpenAI: GPT 5.6 Sol price reduction (until at least Nov 21)](https://news.ycombinator.com/item?id=49421074) | 2026-08-24 | 338 | 344 | 328 | 2 | 1 | 1 |
| [Qwen 3.8-Flash-Next releasing tomorrow (125B a6B)](https://news.ycombinator.com/item?id=49432317) | 2026-08-25 | 336 | 172 | 172 | 2 | 1 | 2 |
| [AI's Affordability Crisis](https://news.ycombinator.com/item?id=48646276) | 2026-06-23 | 332 | 422 | 422 | 2 | 2 | 2 |
| [Outsourcing plus local AI will soon become more economical vs. f](https://news.ycombinator.com/item?id=48278610) | 2026-05-26 | 323 | 374 | 374 | 2 | 2 | 2 |
| [AI eats the world (Spring 26) [pdf]](https://news.ycombinator.com/item?id=48179021) | 2026-05-18 | 307 | 173 | 173 | 2 | 2 | 2 |
| [Moonshot AI suspends new subscriptions due to Kimi K3 demand](https://news.ycombinator.com/item?id=48969291) | 2026-07-19 | 284 | 114 | 114 | 2 | 2 | 2 |
| [Teaching Claude Why](https://news.ycombinator.com/item?id=48066592) | 2026-05-08 | 266 | 159 | 159 | 2 | 2 | 0 |
| [Real-time LLM Inference on Standard GPUs: 3k tokens/s per reques](https://news.ycombinator.com/item?id=48321076) | 2026-05-29 | 219 | 97 | 97 | 2 | 2 | 2 |
| [Notes on DeepSeek](https://news.ycombinator.com/item?id=48476474) | 2026-06-10 | 211 | 141 | 141 | 2 | 2 | 0 |
| [The unbearable cheapness of open weight models](https://news.ycombinator.com/item?id=48668255) | 2026-06-25 | 203 | 186 | 186 | 2 | 2 | 2 |
| [Redeploying Fable 5](https://news.ycombinator.com/item?id=48741853) | 2026-07-01 | 169 | 56 | 56 | 2 | 2 | 1 |
| [Cohere's First Model for Developers](https://news.ycombinator.com/item?id=48489934) | 2026-06-11 | 146 | 41 | 41 | 2 | 2 | 2 |
| [Why current LLM costs are not sustainable](https://news.ycombinator.com/item?id=48683588) | 2026-06-26 | 116 | 196 | 196 | 2 | 2 | 2 |
| [Inference Optimization for MiMo v2.5: Pushing Hybrid SWA Efficie](https://news.ycombinator.com/item?id=48814170) | 2026-07-07 | 116 | 49 | 49 | 2 | 2 | 2 |
| [Hacking with Claude on a $27 smart watch](https://news.ycombinator.com/item?id=49374772) | 2026-08-20 | 110 | 59 | 57 | 2 | 2 | 2 |
| [DeepSeek V4: The Open-Source Model Frontier Labs Feared](https://news.ycombinator.com/item?id=48145171) | 2026-05-15 | 85 | 31 | 31 | 2 | 2 | 1 |
| [DeepSeek planning to significantly raise prices](https://news.ycombinator.com/item?id=49197005) | 2026-08-06 | 85 | 72 | 72 | 2 | 2 | 2 |
| [DeepSeek-V4-Pro-0813 Publish](https://news.ycombinator.com/item?id=49274018) | 2026-08-12 | 67 | 10 | 10 | 2 | 2 | 1 |
| [How did we make DeepSeek outperform Opus](https://news.ycombinator.com/item?id=48820182) | 2026-07-07 | 34 | 7 | 7 | 2 | 2 | 2 |
| [Ask HN: What LLM models are you using and why?](https://news.ycombinator.com/item?id=48166147) | 2026-05-17 | 11 | 16 | 16 | 2 | 2 | 2 |
| [Xiaomi MiMo-v2.5-Pro Open-Sourced: 1T Parameter Model](https://news.ycombinator.com/item?id=47928905) | 2026-04-28 | 9 | 5 | 5 | 2 | 2 | 1 |
| [Claude Opus 5](https://news.ycombinator.com/item?id=49038433) | 2026-07-24 | 1778 | 1335 | 1000 | 1 | 1 | 0 |
| [Open source AI must win](https://news.ycombinator.com/item?id=48511908) | 2026-06-13 | 1603 | 482 | 482 | 1 | 1 | 1 |
| [Running local models is good now](https://news.ycombinator.com/item?id=48555993) | 2026-06-16 | 1596 | 608 | 608 | 1 | 1 | 1 |
| [GPT-5.6](https://news.ycombinator.com/item?id=48849066) | 2026-07-09 | 1561 | 1113 | 1000 | 1 | 1 | 1 |
| [S&P 500 rejects SpaceX, also blocking entry for OpenAI and Anthr](https://news.ycombinator.com/item?id=48421442) | 2026-06-06 | 1484 | 502 | 502 | 1 | 1 | 1 |
| [Apple introduces M6 and M5 Ultra](https://news.ycombinator.com/item?id=49433292) | 2026-08-25 | 1311 | 1300 | 1000 | 1 | 1 | 1 |
| [Using AI to write better code more slowly](https://news.ycombinator.com/item?id=48272984) | 2026-05-25 | 1257 | 446 | 445 | 1 | 1 | 0 |
| [China’s open-weights AI strategy is winning](https://news.ycombinator.com/item?id=48979269) | 2026-07-20 | 1243 | 932 | 932 | 1 | 1 | 1 |
| [U.S. government will decide who gets to use GPT-5.6](https://news.ycombinator.com/item?id=48690101) | 2026-06-26 | 1184 | 1240 | 1000 | 1 | 1 | 1 |
| [Our position on open-weights models](https://news.ycombinator.com/item?id=49076057) | 2026-07-27 | 1180 | 1747 | 1000 | 1 | 1 | 0 |
| [GLM-5.3: Frontier coding with emergent cyber capabilities](https://news.ycombinator.com/item?id=49294997) | 2026-08-14 | 1171 | 584 | 584 | 1 | 1 | 1 |
| [GLM-5.3-Flash](https://news.ycombinator.com/item?id=49449507) | 2026-08-26 | 1130 | 577 | 577 | 1 | 1 | 1 |
| [Gemma 4 12B: A unified, encoder-free multimodal model](https://news.ycombinator.com/item?id=48385906) | 2026-06-03 | 1062 | 401 | 401 | 1 | 1 | 1 |
| [If Claude Fable stops helping you, you'll never know](https://news.ycombinator.com/item?id=48467896) | 2026-06-09 | 1036 | 501 | 501 | 1 | 1 | 1 |
| [Why does Opus 5 feel worse to work with?](https://news.ycombinator.com/item?id=49296740) | 2026-08-14 | 993 | 873 | 872 | 1 | 1 | 0 |
| [I cancelled Claude: Token issues, declining quality, and poor su](https://news.ycombinator.com/item?id=47892019) | 2026-04-24 | 971 | 582 | 582 | 1 | 1 | 1 |
| [Norway imposes near ban on AI in elementary school](https://news.ycombinator.com/item?id=48600093) | 2026-06-19 | 823 | 588 | 588 | 1 | 1 | 1 |
| [Rewriting Bun in Rust](https://news.ycombinator.com/item?id=48837877) | 2026-07-08 | 795 | 534 | 534 | 1 | 1 | 1 |
| [Grok 4.5](https://news.ycombinator.com/item?id=48835111) | 2026-07-08 | 776 | 1502 | 1000 | 1 | 1 | 0 |
| [Claude Fable is relentlessly proactive](https://news.ycombinator.com/item?id=48498573) | 2026-06-12 | 774 | 656 | 656 | 1 | 1 | 1 |
| [Google's Antigravity bait and switch](https://news.ycombinator.com/item?id=48222529) | 2026-05-21 | 771 | 345 | 345 | 1 | 1 | 1 |
| [GitHub Copilot is moving to usage-based billing](https://news.ycombinator.com/item?id=47923357) | 2026-04-27 | 767 | 553 | 553 | 1 | 1 | 1 |
| [Apple reveals new AI architecture built around Google Gemini mod](https://news.ycombinator.com/item?id=48450142) | 2026-06-08 | 738 | 566 | 566 | 1 | 1 | 1 |
| [A recent experience with ChatGPT 5.5 Pro](https://news.ycombinator.com/item?id=48071262) | 2026-05-09 | 728 | 535 | 535 | 1 | 1 | 1 |
| [Accelerating GPT-5.6 Sol Ultrafast](https://news.ycombinator.com/item?id=49289844) | 2026-08-13 | 713 | 279 | 279 | 1 | 1 | 1 |
| [Claude Code sends 33k tokens before reading the prompt; OpenCode](https://news.ycombinator.com/item?id=48883275) | 2026-07-12 | 706 | 396 | 396 | 1 | 1 | 0 |
| [Bonsai 27B: A 27B-Class model that runs on a phone](https://news.ycombinator.com/item?id=48910545) | 2026-07-14 | 706 | 251 | 251 | 1 | 1 | 1 |
| [Qwen3.8-Flash-Next](https://news.ycombinator.com/item?id=49448210) | 2026-08-26 | 701 | 233 | 233 | 1 | 1 | 1 |
| [Show HN: Forge – Guardrails take an 8B model from 53% to 99% on ](https://news.ycombinator.com/item?id=48192383) | 2026-05-19 | 687 | 252 | 252 | 1 | 1 | 0 |
| [AI is slowing down](https://news.ycombinator.com/item?id=48446893) | 2026-06-08 | 674 | 770 | 770 | 1 | 1 | 1 |
| [Fable turned reMarkable into Tom Riddle's diary from Harry Potte](https://news.ycombinator.com/item?id=48811591) | 2026-07-06 | 633 | 422 | 422 | 1 | 1 | 0 |
| [Cybersecurity researchers aren't happy about the guardrails on A](https://news.ycombinator.com/item?id=48478969) | 2026-06-10 | 589 | 525 | 525 | 1 | 1 | 0 |
| [Zerostack – A Unix-inspired coding agent written in pure Rust](https://news.ycombinator.com/item?id=48164287) | 2026-05-16 | 575 | 308 | 308 | 1 | 1 | 1 |
| [Judge approves $1.5B Anthropic settlement for pirated books used](https://news.ycombinator.com/item?id=48996652) | 2026-07-21 | 568 | 632 | 632 | 1 | 1 | 1 |
| [Incident with Github.com [resolved]](https://news.ycombinator.com/item?id=49330597) | 2026-08-17 | 562 | 976 | 822 | 1 | 1 | 1 |
| [I am worried about Bun](https://news.ycombinator.com/item?id=48011184) | 2026-05-04 | 523 | 349 | 349 | 1 | 1 | 1 |
| [GLM 5.2 vs. Opus](https://news.ycombinator.com/item?id=48626866) | 2026-06-22 | 519 | 343 | 343 | 1 | 1 | 0 |
| [We can still stop California's 3D printer surveillance scheme](https://news.ycombinator.com/item?id=48692051) | 2026-06-26 | 513 | 193 | 193 | 1 | 1 | 0 |
| [Kimi K3 Architecture Overview and Notes](https://news.ycombinator.com/item?id=49085698) | 2026-07-28 | 507 | 111 | 111 | 1 | 1 | 1 |
| [I love LLMs, I hate hype](https://news.ycombinator.com/item?id=48883343) | 2026-07-12 | 501 | 322 | 322 | 1 | 1 | 1 |
| [DeepSeek 4 Flash local inference engine for Metal](https://news.ycombinator.com/item?id=48050751) | 2026-05-07 | 499 | 159 | 158 | 1 | 1 | 1 |
| [How fast is N tokens per second really?](https://news.ycombinator.com/item?id=48174920) | 2026-05-18 | 494 | 96 | 96 | 1 | 1 | 1 |
| [Microsoft starts canceling Claude Code licenses](https://news.ycombinator.com/item?id=48238896) | 2026-05-22 | 493 | 466 | 466 | 1 | 1 | 1 |
| [A global workspace in language models](https://news.ycombinator.com/item?id=48808002) | 2026-07-06 | 467 | 201 | 201 | 1 | 1 | 0 |
| [Cerebras CS-4](https://news.ycombinator.com/item?id=49354949) | 2026-08-19 | 464 | 275 | 274 | 1 | 1 | 1 |
| [Ask HN: What are tools you have made for yourself since the adve](https://news.ycombinator.com/item?id=48449187) | 2026-06-08 | 445 | 788 | 788 | 1 | 1 | 1 |
| [Z.ai confirms Ox Alpha is a new GLM-series model and will releas](https://news.ycombinator.com/item?id=49446422) | 2026-08-26 | 434 | 146 | 146 | 1 | 1 | 1 |
| [Codex starts encrypting sub-agent prompts](https://news.ycombinator.com/item?id=48905028) | 2026-07-14 | 425 | 250 | 250 | 1 | 1 | 1 |
| [Apple caught off guard by AI demand for Mac Mini and Mac Studio](https://news.ycombinator.com/item?id=49508982) | 2026-08-31 | 422 | 476 | 476 | 1 | 1 | 1 |
| [Laguna S 2.1](https://news.ycombinator.com/item?id=48995261) | 2026-07-21 | 416 | 89 | 89 | 1 | 1 | 0 |
| [GPT-5.6 Sol Ultra will be in Codex](https://news.ycombinator.com/item?id=48799614) | 2026-07-06 | 415 | 405 | 405 | 1 | 1 | 0 |
| [Kimi K3, and what we can still learn from the pelican benchmark](https://news.ycombinator.com/item?id=48947717) | 2026-07-17 | 407 | 223 | 223 | 1 | 1 | 1 |
| [Grok 4.3](https://news.ycombinator.com/item?id=47972447) | 2026-05-01 | 405 | 529 | 529 | 1 | 1 | 1 |
| [I built a vulnerable app and spent $1,500 seeing if LLMs could h](https://news.ycombinator.com/item?id=48392343) | 2026-06-04 | 402 | 216 | 216 | 1 | 1 | 1 |
| [VibeThinker: 3B param model that beats Opus 4.5 on reasoning wit](https://news.ycombinator.com/item?id=48639240) | 2026-06-23 | 398 | 205 | 205 | 1 | 1 | 1 |
| [DeepSeek V4 Flash on a Single AMD MI300X](https://news.ycombinator.com/item?id=49166386) | 2026-08-04 | 382 | 109 | 109 | 1 | 1 | 1 |
| [Shunning AI is the human choice](https://news.ycombinator.com/item?id=48222366) | 2026-05-21 | 373 | 537 | 537 | 1 | 1 | 0 |
| [OpenAI reduces Codex Model Context Size from 372k to 272k](https://news.ycombinator.com/item?id=48965850) | 2026-07-19 | 371 | 166 | 166 | 1 | 1 | 1 |
| [Apple Silicon costs more than OpenRouter](https://news.ycombinator.com/item?id=48168198) | 2026-05-17 | 355 | 302 | 302 | 1 | 1 | 1 |
| [SWE-bench Verified no longer measures frontier coding capabiliti](https://news.ycombinator.com/item?id=47910388) | 2026-04-26 | 343 | 181 | 181 | 1 | 1 | 1 |
| [Nvidia is proposing a beast of a CPU system for Windows PCs](https://news.ycombinator.com/item?id=48424605) | 2026-06-06 | 332 | 557 | 557 | 1 | 1 | 1 |
| [Google to pay SpaceX $920M a month for compute capacity at xAI d](https://news.ycombinator.com/item?id=48417490) | 2026-06-05 | 327 | 955 | 775 | 1 | 1 | 1 |
| [Using an open model feels surprisingly good](https://news.ycombinator.com/item?id=49078583) | 2026-07-28 | 326 | 143 | 143 | 1 | 1 | 1 |
| [Will It Mythos?](https://news.ycombinator.com/item?id=48640196) | 2026-06-23 | 321 | 223 | 223 | 1 | 1 | 1 |
| [Codex Resets](https://news.ycombinator.com/item?id=48963465) | 2026-07-18 | 312 | 202 | 202 | 1 | 1 | 1 |
| [Anthropic is expanding to Colossus2. Will use GB200](https://news.ycombinator.com/item?id=48214017) | 2026-05-20 | 307 | 351 | 351 | 1 | 1 | 1 |
| [Motherboard sales 'collapse' amid unprecedented shortages fueled](https://news.ycombinator.com/item?id=48050540) | 2026-05-07 | 300 | 343 | 343 | 1 | 1 | 1 |
| [Ask HN: What are you working on? (May 2026)](https://news.ycombinator.com/item?id=48085993) | 2026-05-10 | 290 | 1120 | 1000 | 1 | 1 | 1 |
| [Specsmaxxing – On overcoming AI psychosis, and why I write specs](https://news.ycombinator.com/item?id=47994012) | 2026-05-03 | 287 | 295 | 295 | 1 | 1 | 1 |
| [Nobody knows what a used GPU cluster is worth](https://news.ycombinator.com/item?id=48917135) | 2026-07-15 | 279 | 264 | 264 | 1 | 1 | 1 |
| [SWE-1.7 Reach Near GPT 5.5 and Opus Intelligence](https://news.ycombinator.com/item?id=48833866) | 2026-07-08 | 272 | 140 | 140 | 1 | 1 | 1 |
| [Ox Alpha](https://news.ycombinator.com/item?id=49381896) | 2026-08-20 | 263 | 204 | 202 | 1 | 1 | 0 |
| [OpenAI releases GPT-5.5 and GPT-5.5 Pro in the API](https://news.ycombinator.com/item?id=47894000) | 2026-04-24 | 256 | 159 | 159 | 1 | 1 | 0 |
| [Sakana Fugu](https://news.ycombinator.com/item?id=48624782) | 2026-06-22 | 247 | 127 | 127 | 1 | 1 | 1 |
| [Computer use in Gemini 3.5 Flash](https://news.ycombinator.com/item?id=48662999) | 2026-06-24 | 242 | 167 | 167 | 1 | 1 | 0 |
| [The US is winning the AI race where it matters most: commerciali](https://news.ycombinator.com/item?id=48121929) | 2026-05-13 | 241 | 677 | 677 | 1 | 1 | 0 |
| [For thirty years I programmed with Phish on, every day](https://news.ycombinator.com/item?id=47998225) | 2026-05-03 | 235 | 178 | 178 | 1 | 1 | 1 |
| [AMD Strix Halo RDMA Cluster Setup Guide](https://news.ycombinator.com/item?id=48703258) | 2026-06-28 | 232 | 87 | 87 | 1 | 1 | 0 |
| [Leaked OpenAI financials show $38.5B loss and compute burn](https://news.ycombinator.com/item?id=48565130) | 2026-06-17 | 221 | 263 | 263 | 1 | 1 | 1 |
| [Apple Silicon Exec Explains Mac Mini AI Demand and On-Device Fut](https://news.ycombinator.com/item?id=48805598) | 2026-07-06 | 220 | 317 | 317 | 1 | 1 | 1 |
| [Openrouter Fusion API](https://news.ycombinator.com/item?id=48537641) | 2026-06-15 | 217 | 85 | 85 | 1 | 1 | 1 |
| [Show HN: Smart model routing directly in Claude, Codex and Curso](https://news.ycombinator.com/item?id=48688700) | 2026-06-26 | 216 | 113 | 113 | 1 | 1 | 1 |
| [GPT-5.5 Price Increase: What It Costs](https://news.ycombinator.com/item?id=48057209) | 2026-05-08 | 214 | 73 | 73 | 1 | 1 | 1 |
| [Anthropic updates their terms to verify age or identity](https://news.ycombinator.com/item?id=48650311) | 2026-06-23 | 196 | 183 | 183 | 1 | 1 | 1 |
| [Corporate America Is Starting to Ration AI as Cost Skyrockets](https://news.ycombinator.com/item?id=48335388) | 2026-05-30 | 188 | 179 | 179 | 1 | 1 | 0 |
| [Replies to comments on my "LLMs are eroding my career" post](https://news.ycombinator.com/item?id=48443258) | 2026-06-08 | 186 | 256 | 256 | 1 | 1 | 1 |
| [Grit: Rewriting Git in Rust with agents](https://news.ycombinator.com/item?id=48466812) | 2026-06-09 | 178 | 306 | 306 | 1 | 1 | 1 |
| [CursorBench 3.1](https://news.ycombinator.com/item?id=48756840) | 2026-07-02 | 171 | 104 | 104 | 1 | 1 | 1 |
| [Show HN: Distilling DeepSeek into GPT-OSS doesn't transfer censo](https://news.ycombinator.com/item?id=49113599) | 2026-07-30 | 170 | 73 | 73 | 1 | 1 | 1 |
| [Google limits Meta's use of its Gemini AI models](https://news.ycombinator.com/item?id=48707103) | 2026-06-28 | 162 | 72 | 72 | 1 | 1 | 1 |
| [Gemini API File Search is now multimodal](https://news.ycombinator.com/item?id=48080702) | 2026-05-10 | 156 | 46 | 46 | 1 | 1 | 1 |
| [The mysterious Hy3 LLM is topping OpenRouter Model Rankings by a](https://news.ycombinator.com/item?id=48317294) | 2026-05-29 | 150 | 112 | 112 | 1 | 1 | 0 |
| [After dissing Anthropic for limiting Mythos, OpenAI restricts ac](https://news.ycombinator.com/item?id=47973108) | 2026-05-01 | 143 | 128 | 128 | 1 | 1 | 0 |
| [GLM-5.3-Flash Intelligence, Performance and Price Analysis](https://news.ycombinator.com/item?id=49450353) | 2026-08-26 | 139 | 60 | 60 | 1 | 1 | 1 |
| [OpenAI mulls slashing prices as it competes with Anthropic for u](https://news.ycombinator.com/item?id=48486486) | 2026-06-11 | 135 | 142 | 142 | 1 | 1 | 1 |
| [SubQ 1.1 Small](https://news.ycombinator.com/item?id=48556163) | 2026-06-16 | 132 | 52 | 52 | 1 | 1 | 1 |
| [GitHub Copilot App](https://news.ycombinator.com/item?id=48373764) | 2026-06-02 | 124 | 76 | 76 | 1 | 1 | 1 |
| [Wayfinder Router: deterministic routing of queries between local](https://news.ycombinator.com/item?id=48704373) | 2026-06-28 | 123 | 56 | 56 | 1 | 1 | 0 |
| [OpenAI restores 5-hour Codex and Work limits for ChatGPT Plus us](https://news.ycombinator.com/item?id=49432879) | 2026-08-25 | 120 | 125 | 125 | 1 | 1 | 1 |
| [Launch HN: Speko (YC S26) – OpenRouter for Voice AI](https://news.ycombinator.com/item?id=49332751) | 2026-08-17 | 118 | 69 | 69 | 1 | 1 | 1 |
| [White House Considers Vetting A.I. Models Before They Are Releas](https://news.ycombinator.com/item?id=48013608) | 2026-05-04 | 102 | 108 | 108 | 1 | 1 | 1 |
| [Show HN: Jacquard, a programming language for AI-written, human-](https://news.ycombinator.com/item?id=48894630) | 2026-07-13 | 102 | 59 | 59 | 1 | 1 | 1 |
| [Two Qwen3 models on one DGX Spark: the residency math](https://news.ycombinator.com/item?id=48587865) | 2026-06-18 | 95 | 49 | 49 | 1 | 1 | 0 |
| [Ask HN: Anthropic banned me from using Claude Code and I don't k](https://news.ycombinator.com/item?id=48641160) | 2026-06-23 | 82 | 94 | 94 | 1 | 1 | 1 |
| [Xiaomi MiMo Token Plan is Now Globally Available](https://news.ycombinator.com/item?id=48287220) | 2026-05-26 | 79 | 57 | 57 | 1 | 1 | 1 |
| [DeepSeek V4 Pro 0813 quietly released](https://news.ycombinator.com/item?id=49275114) | 2026-08-12 | 79 | 6 | 6 | 1 | 1 | 1 |
| [Interview with Boris Cherny [video]](https://news.ycombinator.com/item?id=49077040) | 2026-07-27 | 74 | 80 | 80 | 1 | 1 | 0 |
| [Launch HN: Tokenless (YC S26) – Automatic model switching to sav](https://news.ycombinator.com/item?id=49099143) | 2026-07-29 | 71 | 63 | 63 | 1 | 1 | 1 |
| [Ruby vs. Java vs. TypeScript: my experience on building a Cowork](https://news.ycombinator.com/item?id=48270265) | 2026-05-25 | 63 | 46 | 46 | 1 | 1 | 1 |
| [AI Engineers aren't safe from being replaced by AI](https://news.ycombinator.com/item?id=48380987) | 2026-06-03 | 45 | 76 | 76 | 1 | 1 | 1 |
| [How to buy cheap Claude tokens in China](https://news.ycombinator.com/item?id=48165492) | 2026-05-17 | 38 | 10 | 10 | 1 | 1 | 1 |
| [Qwen3.7-Max Ran for 35 Hours on Unknown Hardware and Achieved a ](https://news.ycombinator.com/item?id=48264663) | 2026-05-25 | 38 | 31 | 31 | 1 | 1 | 1 |
| [Local LLMs perform better when you teach them to ask before they](https://news.ycombinator.com/item?id=48254993) | 2026-05-24 | 33 | 12 | 12 | 1 | 1 | 1 |
| [The Economics of Speculative Decoding](https://news.ycombinator.com/item?id=48449036) | 2026-06-08 | 30 | 6 | 6 | 1 | 1 | 0 |
| [GLM-5.2 is probably the most powerful text-only open weights LLM](https://news.ycombinator.com/item?id=48587383) | 2026-06-18 | 28 | 4 | 4 | 1 | 1 | 0 |
| [DeepSeek-V4 Technical Report [pdf]](https://news.ycombinator.com/item?id=47884933) | 2026-04-24 | 26 | 4 | 4 | 1 | 1 | 1 |
| [DeepSeek up to 1000% price hike is live](https://news.ycombinator.com/item?id=49287881) | 2026-08-13 | 25 | 7 | 7 | 1 | 1 | 1 |
| ["No, I swear I wrote this."](https://news.ycombinator.com/item?id=48699969) | 2026-06-27 | 17 | 46 | 46 | 1 | 1 | 1 |
| [Best AI coding plan alternative to Claude and ChatGPT](https://news.ycombinator.com/item?id=48081266) | 2026-05-10 | 16 | 13 | 13 | 1 | 1 | 1 |
| [Grok Build 0.1: Intelligence, Performance and Price Analysis](https://news.ycombinator.com/item?id=48656943) | 2026-06-24 | 16 | 18 | 18 | 1 | 1 | 0 |
| [We burned 11.7B tokens to find the best cyber AI model](https://news.ycombinator.com/item?id=49386885) | 2026-08-21 | 15 | 7 | 7 | 1 | 1 | 0 |
| [DeepSeek routes your request to Fable5](https://news.ycombinator.com/item?id=48966016) | 2026-07-19 | 14 | 4 | 4 | 1 | 1 | 1 |
| [DeepSeek Slashes AI Costs to Cents](https://news.ycombinator.com/item?id=48321422) | 2026-05-29 | 13 | 4 | 4 | 1 | 1 | 1 |
| [Ask HN: Claude Code or Codex?](https://news.ycombinator.com/item?id=48989357) | 2026-07-21 | 13 | 33 | 33 | 1 | 1 | 0 |
| [What happens behind the scenes when we change effort for same LL](https://news.ycombinator.com/item?id=49048125) | 2026-07-25 | 13 | 8 | 8 | 1 | 1 | 1 |
| [DeepSeek v4 Price Increase](https://news.ycombinator.com/item?id=49285741) | 2026-08-13 | 11 | 4 | 4 | 1 | 1 | 1 |
| [Show HN: HarnessRouter: Unified interface for agent harnesses](https://news.ycombinator.com/item?id=49335595) | 2026-08-17 | 10 | 14 | 14 | 1 | 1 | 1 |
| [Do frontier models matter if most production AI ends up running ](https://news.ycombinator.com/item?id=48909401) | 2026-07-14 | 9 | 4 | 4 | 1 | 1 | 1 |
| [EU opens call for seven 'gigafactories' to train next-generation](https://news.ycombinator.com/item?id=49107928) | 2026-07-30 | 8 | 5 | 5 | 1 | 1 | 1 |
| [DeepSeek Slashes Fees for New AI Model](https://news.ycombinator.com/item?id=47919889) | 2026-04-27 | 7 | 4 | 4 | 1 | 1 | 1 |
| [Show HN: A free CLI coding agent, powered by ads](https://news.ycombinator.com/item?id=48578487) | 2026-06-17 | 7 | 7 | 7 | 1 | 1 | 1 |
| [America must guard against China's own Mythos](https://news.ycombinator.com/item?id=47889468) | 2026-04-24 | 5 | 4 | 4 | 1 | 1 | 0 |
| [Chinese AI models are ~8 months behind and falling further behin](https://news.ycombinator.com/item?id=47986919) | 2026-05-02 | 3 | 6 | 6 | 1 | 1 | 1 |
| [I added vi-modal bindings to my blog, a Chinese AI helped me do ](https://news.ycombinator.com/item?id=48299752) | 2026-05-27 | 3 | 1 | 1 | 1 | 1 | 0 |
| [Show HN: role-model, a router for hybrid local/cloud AI](https://news.ycombinator.com/item?id=48706181) | 2026-06-28 | 3 | 2 | 2 | 1 | 1 | 1 |
| [The $0 Personalized News Roundup That Lands in Your Podcast App ](https://news.ycombinator.com/item?id=49242398) | 2026-08-10 | 3 | 1 | 1 | 1 | 1 | 0 |
| [A 3D Flappy Bird side-scroller game built with DeepSeek V4 Pro](https://news.ycombinator.com/item?id=47943784) | 2026-04-29 | 2 | 1 | 1 | 1 | 1 | 1 |
| [Reflection SDD: Use a Reflection Harness to Level Up Your OpenSp](https://news.ycombinator.com/item?id=48352492) | 2026-06-01 | 2 | 1 | 1 | 1 | 1 | 1 |
| [[dead]](https://news.ycombinator.com/item?id=49284564) | 2026-08-13 | 0 | 0 | 1 | 1 | 1 | 1 |
| [New Studio M5 Ultra ready for local home AI lab? Compared to Ope](https://news.ycombinator.com/item?id=49475496) | 2026-08-28 | 0 | 0 | 2 | 1 | 1 | 1 |

## 8. Full index of matched comments

All 623 of them. `type` is filled only where the comment was hand-read; `—` means unlabelled, not unclassifiable. Artifacts are mechanical and present for every row.

| Comment | Author | Date | Thread | Type | Artifacts |
|---|---|---|---|---|---|
| [49513091](https://news.ycombinator.com/item?id=49513091) | jmyeet | 2026-08-31 | Apple caught off guard by AI demand for Mac  | — | number, version |
| [49475497](https://news.ycombinator.com/item?id=49475497) | gaborme | 2026-08-28 | New Studio M5 Ultra ready for local home AI  | — | number, version |
| [49464861](https://news.ycombinator.com/item?id=49464861) | bkd9 | 2026-08-27 | GLM-5.3-Flash | — | link, version |
| [49461951](https://news.ycombinator.com/item?id=49461951) | irthomasthomas | 2026-08-27 | Qwen 3.8-Flash-Next releasing tomorrow (125B | — | link, number |
| [49461941](https://news.ycombinator.com/item?id=49461941) | irthomasthomas | 2026-08-27 | Qwen 3.8-Flash-Next releasing tomorrow (125B | — | link, number |
| [49458769](https://news.ycombinator.com/item?id=49458769) | nl | 2026-08-27 | Qwen3.8-Flash-Next | — | link, number, version |
| [49451754](https://news.ycombinator.com/item?id=49451754) | jhack | 2026-08-26 | GLM-5.3-Flash Intelligence, Performance and  | — | number |
| [49447252](https://news.ycombinator.com/item?id=49447252) | kosolam | 2026-08-26 | Z.ai confirms Ox Alpha is a new GLM-series m | — | version |
| [49436855](https://news.ycombinator.com/item?id=49436855) | ltbarcly3 | 2026-08-25 | Apple introduces M6 and M5 Ultra | — | number, version, code |
| [49435524](https://news.ycombinator.com/item?id=49435524) | phiresky | 2026-08-25 | OpenAI restores 5-hour Codex and Work limits | — | link, number |
| [49431274](https://news.ycombinator.com/item?id=49431274) | Ringz | 2026-08-25 | OpenAI: GPT 5.6 Sol price reduction (until a | — | — |
| [49422920](https://news.ycombinator.com/item?id=49422920) | Ringz | 2026-08-24 | OpenAI: GPT 5.6 Sol price reduction (until a | — | version |
| [49394289](https://news.ycombinator.com/item?id=49394289) | cge | 2026-08-21 | Bringing the cybersecurity capabilities of C | — | version |
| [49393709](https://news.ycombinator.com/item?id=49393709) | enraged_camel | 2026-08-21 | Bringing the cybersecurity capabilities of C | — | version |
| [49393396](https://news.ycombinator.com/item?id=49393396) | surgical_fire | 2026-08-21 | Bringing the cybersecurity capabilities of C | — | version |
| [49389271](https://news.ycombinator.com/item?id=49389271) | LoganDark | 2026-08-21 | We burned 11.7B tokens to find the best cybe | — | — |
| [49385045](https://news.ycombinator.com/item?id=49385045) | wilj | 2026-08-21 | Ox Alpha | — | — |
| [49376380](https://news.ycombinator.com/item?id=49376380) | wxw | 2026-08-20 | Hacking with Claude on a $27 smart watch | — | version |
| [49375090](https://news.ycombinator.com/item?id=49375090) | NoboruWataya | 2026-08-20 | Hacking with Claude on a $27 smart watch | — | version |
| [49370038](https://news.ycombinator.com/item?id=49370038) | modgate | 2026-08-20 | Launch HN: Speko (YC S26) – OpenRouter for V | — | number |
| [49357345](https://news.ycombinator.com/item?id=49357345) | zozbot234 | 2026-08-19 | Cerebras CS-4 | — | number |
| [49337979](https://news.ycombinator.com/item?id=49337979) | songrenchu | 2026-08-17 | Show HN: HarnessRouter: Unified interface fo | — | version |
| [49335276](https://news.ycombinator.com/item?id=49335276) | ALLTaken | 2026-08-17 | Incident with Github.com | — | version |
| [49310730](https://news.ycombinator.com/item?id=49310730) | Topfi | 2026-08-15 | Qwen 3.8 27B | — | number |
| [49309087](https://news.ycombinator.com/item?id=49309087) | not_paid_by_yt | 2026-08-15 | Why does Opus 5 feel worse to work with? | — | — |
| [49308753](https://news.ycombinator.com/item?id=49308753) | dexterlagan | 2026-08-15 | Qwen 3.8 27B | — | version |
| [49302610](https://news.ycombinator.com/item?id=49302610) | dannyw | 2026-08-14 | Qwen 3.8 27B | — | version |
| [49301898](https://news.ycombinator.com/item?id=49301898) | kristjansson | 2026-08-14 | Qwen 3.8 27B | — | — |
| [49300362](https://news.ycombinator.com/item?id=49300362) | ramon156 | 2026-08-14 | Qwen 3.8 27B | — | — |
| [49300344](https://news.ycombinator.com/item?id=49300344) | hypfer | 2026-08-14 | Qwen 3.8 27B | — | version |
| [49300308](https://news.ycombinator.com/item?id=49300308) | ramon156 | 2026-08-14 | Qwen 3.8 27B | — | version |
| [49296957](https://news.ycombinator.com/item?id=49296957) | floppyd | 2026-08-14 | DeepSeek API Pricing Update | — | number, version |
| [49295197](https://news.ycombinator.com/item?id=49295197) | npn | 2026-08-14 | GLM-5.3: Frontier coding with emergent cyber | — | version |
| [49291742](https://news.ycombinator.com/item?id=49291742) | YetAnotherNick | 2026-08-13 | Accelerating GPT-5.6 Sol Ultrafast | — | link, number |
| [49289791](https://news.ycombinator.com/item?id=49289791) | cloudie78 | 2026-08-13 | DeepSeek up to 1000% price hike is live | — | number, version |
| [49288301](https://news.ycombinator.com/item?id=49288301) | dhx | 2026-08-13 | Qwen3.8-2.4T | — | link, number, version |
| [49286679](https://news.ycombinator.com/item?id=49286679) | usagisushi | 2026-08-13 | DeepSeek API Pricing Update | — | number, version, code |
| [49286589](https://news.ycombinator.com/item?id=49286589) | cmrdporcupine | 2026-08-13 | DeepSeek API Pricing Update | — | version |
| [49285797](https://news.ycombinator.com/item?id=49285797) | m00dy | 2026-08-13 | DeepSeek V4 Pro 0813 | announcement | number, version |
| [49285742](https://news.ycombinator.com/item?id=49285742) | lukax | 2026-08-13 | DeepSeek v4 Price Increase | — | number, version |
| [49285181](https://news.ycombinator.com/item?id=49285181) | kaeluka | 2026-08-13 | DeepSeek V4 Pro 0813 | — | version |
| [49284756](https://news.ycombinator.com/item?id=49284756) | simjnd | 2026-08-13 | DeepSeek V4 Pro 0813 | — | version |
| [49284565](https://news.ycombinator.com/item?id=49284565) | ahmadawais | 2026-08-13 | [dead] | — | version |
| [49284396](https://news.ycombinator.com/item?id=49284396) | hemkeshr | 2026-08-13 | DeepSeek V4 Pro 0813 | — | version |
| [49283986](https://news.ycombinator.com/item?id=49283986) | thunfischtoast | 2026-08-13 | DeepSeek V4 Pro 0813 | — | — |
| [49282929](https://news.ycombinator.com/item?id=49282929) | Hardd | 2026-08-13 | DeepSeek V4 Pro 0813 | — | — |
| [49282918](https://news.ycombinator.com/item?id=49282918) | minraws | 2026-08-13 | DeepSeek V4 Pro 0813 | — | — |
| [49282465](https://news.ycombinator.com/item?id=49282465) | gunalx | 2026-08-13 | DeepSeek V4 Pro 0813 | opinion | number, version |
| [49281662](https://news.ycombinator.com/item?id=49281662) | jeffmcjunkin | 2026-08-13 | DeepSeek V4 Pro 0813 | — | link |
| [49279690](https://news.ycombinator.com/item?id=49279690) | HDBaseT | 2026-08-12 | DeepSeek-V4-Pro-0813 Publish | — | version |
| [49277965](https://news.ycombinator.com/item?id=49277965) | Phemist | 2026-08-12 | DeepSeek V4 Pro 0813 | — | — |
| [49277944](https://news.ycombinator.com/item?id=49277944) | ApolloFortyNine | 2026-08-12 | DeepSeek V4 Pro 0813 | — | version |
| [49277253](https://news.ycombinator.com/item?id=49277253) | txrx0000 | 2026-08-12 | Grok 4.6 | — | version |
| [49277160](https://news.ycombinator.com/item?id=49277160) | taosx | 2026-08-12 | DeepSeek V4 Pro 0813 | deep_analysis | link, version |
| [49276842](https://news.ycombinator.com/item?id=49276842) | cjg007 | 2026-08-12 | DeepSeek V4 Pro 0813 | — | — |
| [49276127](https://news.ycombinator.com/item?id=49276127) | nullbyte | 2026-08-12 | DeepSeek V4 Pro 0813 | — | — |
| [49276029](https://news.ycombinator.com/item?id=49276029) | johndough | 2026-08-12 | DeepSeek V4 Pro 0813 quietly released | — | code |
| [49275985](https://news.ycombinator.com/item?id=49275985) | jklmnopqrstuvw | 2026-08-12 | DeepSeek V4 Pro 0813 | benchmark | number, version |
| [49275775](https://news.ycombinator.com/item?id=49275775) | xynelius | 2026-08-12 | DeepSeek V4 Pro 0813 | deep_analysis | link, number |
| [49275709](https://news.ycombinator.com/item?id=49275709) | parsimo2010 | 2026-08-12 | DeepSeek V4 Pro 0813 | comparison | link, version |
| [49275606](https://news.ycombinator.com/item?id=49275606) | Gecko4072 | 2026-08-12 | DeepSeek V4 Pro 0813 | announcement | link, version |
| [49275586](https://news.ycombinator.com/item?id=49275586) | nolist_policy | 2026-08-12 | DeepSeek V4 Pro 0813 | usage_demo | link, number, version |
| [49275464](https://news.ycombinator.com/item?id=49275464) | networked | 2026-08-12 | DeepSeek V4 Pro 0813 | comparison | link, version |
| [49275340](https://news.ycombinator.com/item?id=49275340) | sparkling | 2026-08-12 | DeepSeek V4 Pro 0813 | opinion | number, version |
| [49275288](https://news.ycombinator.com/item?id=49275288) | Gecko4072 | 2026-08-12 | DeepSeek V4 Pro 0813 | — | version |
| [49275222](https://news.ycombinator.com/item?id=49275222) | npn | 2026-08-12 | DeepSeek-V4-Pro-0813 Publish | — | — |
| [49275180](https://news.ycombinator.com/item?id=49275180) | scrlk | 2026-08-12 | DeepSeek V4 Pro 0813 | benchmark | link, version, code |
| [49274719](https://news.ycombinator.com/item?id=49274719) | svantana | 2026-08-12 | Qwen3.8-2.4T | — | link |
| [49274543](https://news.ycombinator.com/item?id=49274543) | dhx | 2026-08-12 | Qwen3.8-2.4T | — | link, number, version |
| [49274076](https://news.ycombinator.com/item?id=49274076) | zxilly | 2026-08-12 | Grok 4.6 | — | — |
| [49242399](https://news.ycombinator.com/item?id=49242399) | gadgetboy | 2026-08-10 | The $0 Personalized News Roundup That Lands  | — | — |
| [49223505](https://news.ycombinator.com/item?id=49223505) | KronisLV | 2026-08-08 | DeepSeek V4 Flash 0731 | — | number, version |
| [49220263](https://news.ycombinator.com/item?id=49220263) | re-thc | 2026-08-08 | DeepSeek V4 Flash 0731 | — | number, version |
| [49219942](https://news.ycombinator.com/item?id=49219942) | ignoramous | 2026-08-08 | DeepSeek V4 Flash 0731 | — | link |
| [49219903](https://news.ycombinator.com/item?id=49219903) | KronisLV | 2026-08-08 | DeepSeek V4 Flash 0731 | — | link, number, version |
| [49217148](https://news.ycombinator.com/item?id=49217148) | dools | 2026-08-07 | DeepSeek V4 Flash 0731 | — | number |
| [49215905](https://news.ycombinator.com/item?id=49215905) | ignoramous | 2026-08-07 | DeepSeek V4 Flash 0731 | — | number |
| [49215736](https://news.ycombinator.com/item?id=49215736) | NoboruWataya | 2026-08-07 | DeepSeek V4 Flash 0731 | — | number |
| [49210821](https://news.ycombinator.com/item?id=49210821) | phonon | 2026-08-07 | AMD acquires Taalas to boost inference perfo | — | number |
| [49205628](https://news.ycombinator.com/item?id=49205628) | octoberfranklin | 2026-08-07 | AMD acquires Taalas to boost inference perfo | — | — |
| [49200026](https://news.ycombinator.com/item?id=49200026) | ignoramous | 2026-08-06 | DeepSeek planning to significantly raise pri | — | number, version |
| [49197539](https://news.ycombinator.com/item?id=49197539) | petercooper | 2026-08-06 | DeepSeek planning to significantly raise pri | — | link, number |
| [49169038](https://news.ycombinator.com/item?id=49169038) | wren6991 | 2026-08-04 | DeepSeek V4 Flash on a Single AMD MI300X | — | number, version |
| [49152622](https://news.ycombinator.com/item?id=49152622) | throwaw12 | 2026-08-03 | Qwen3.8-Max: A New Bar for Coding and Cowork | — | version |
| [49151096](https://news.ycombinator.com/item?id=49151096) | ycui7 | 2026-08-03 | Qwen3.8-Max: A New Bar for Coding and Cowork | — | version |
| [49122120](https://news.ycombinator.com/item?id=49122120) | websap | 2026-07-31 | DeepSeek V4 Flash 0731 Intelligence, Perform | — | — |
| [49121683](https://news.ycombinator.com/item?id=49121683) | throwaw12 | 2026-07-31 | DeepSeek V4 Flash 0731 Intelligence, Perform | — | version |
| [49121460](https://news.ycombinator.com/item?id=49121460) | benjiro29 | 2026-07-31 | DeepSeek-V4-Flash Update | — | number, version |
| [49121388](https://news.ycombinator.com/item?id=49121388) | gpugreg | 2026-07-31 | DeepSeek-V4-Flash Update | — | link, number, version |
| [49120289](https://news.ycombinator.com/item?id=49120289) | baalimago | 2026-07-31 | DeepSeek-V4-Flash Update | — | version |
| [49120154](https://news.ycombinator.com/item?id=49120154) | baalimago | 2026-07-31 | DeepSeek-V4-Flash Update | — | version |
| [49116098](https://news.ycombinator.com/item?id=49116098) | michaellee8 | 2026-07-30 | Show HN: Distilling DeepSeek into GPT-OSS do | — | version |
| [49115225](https://news.ycombinator.com/item?id=49115225) | forsalebypwner | 2026-07-30 | Advancing the price-performance frontier wit | — | number |
| [49114913](https://news.ycombinator.com/item?id=49114913) | fy20 | 2026-07-30 | Advancing the price-performance frontier wit | — | number |
| [49114276](https://news.ycombinator.com/item?id=49114276) | subarctic | 2026-07-30 | Advancing the price-performance frontier wit | — | — |
| [49114167](https://news.ycombinator.com/item?id=49114167) | ignoramous | 2026-07-30 | Advancing the price-performance frontier wit | — | number, version |
| [49113922](https://news.ycombinator.com/item?id=49113922) | jrflo | 2026-07-30 | Advancing the price-performance frontier wit | — | — |
| [49113813](https://news.ycombinator.com/item?id=49113813) | efficax | 2026-07-30 | Advancing the price-performance frontier wit | — | — |
| [49108141](https://news.ycombinator.com/item?id=49108141) | gpugreg | 2026-07-30 | EU opens call for seven 'gigafactories' to t | — | number, code |
| [49099772](https://news.ycombinator.com/item?id=49099772) | ignoramous | 2026-07-29 | Launch HN: Tokenless (YC S26) – Automatic mo | — | number |
| [49094285](https://news.ycombinator.com/item?id=49094285) | igravious | 2026-07-29 | Kimi K3 Architecture Overview and Notes | — | version |
| [49093062](https://news.ycombinator.com/item?id=49093062) | wilj | 2026-07-29 | Interview with Boris Cherny [video] | — | — |
| [49082332](https://news.ycombinator.com/item?id=49082332) | h8hawk | 2026-07-28 | Using an open model feels surprisingly good | — | version |
| [49081828](https://news.ycombinator.com/item?id=49081828) | torginus | 2026-07-28 | A $500 RL fine-tune of a 9B open model beat  | — | version |
| [49080474](https://news.ycombinator.com/item?id=49080474) | solarkraft | 2026-07-28 | A $500 RL fine-tune of a 9B open model beat  | — | — |
| [49077133](https://news.ycombinator.com/item?id=49077133) | wren6991 | 2026-07-27 | Our position on open-weights models | — | — |
| [49068741](https://news.ycombinator.com/item?id=49068741) | nl | 2026-07-27 | Kimi-K3 on HuggingFace | — | link, number |
| [49067331](https://news.ycombinator.com/item?id=49067331) | johndough | 2026-07-27 | Kimi-K3 on HuggingFace | — | link, number |
| [49049690](https://news.ycombinator.com/item?id=49049690) | neongreen | 2026-07-25 | What happens behind the scenes when we chang | — | link |
| [49042072](https://news.ycombinator.com/item?id=49042072) | Footprint0521 | 2026-07-24 | Claude Opus 5 | — | — |
| [49018613](https://news.ycombinator.com/item?id=49018613) | SwellJoe | 2026-07-23 | Laguna S 2.1 | — | — |
| [49013750](https://news.ycombinator.com/item?id=49013750) | jmyeet | 2026-07-22 | Nobody knows what a used GPU cluster is wort | — | link, number |
| [49009197](https://news.ycombinator.com/item?id=49009197) | flir | 2026-07-22 | Judge approves $1.5B Anthropic settlement fo | — | number |
| [49002813](https://news.ycombinator.com/item?id=49002813) | KronisLV | 2026-07-22 | Kimi K3 Is Competitive with Fable; Kimi K3 a | — | link, version |
| [49001259](https://news.ycombinator.com/item?id=49001259) | ignoramous | 2026-07-22 | Kimi K3 Is Competitive with Fable; Kimi K3 a | — | number, version |
| [49000931](https://news.ycombinator.com/item?id=49000931) | dools | 2026-07-22 | Kimi K3 Is Competitive with Fable; Kimi K3 a | — | version |
| [48998987](https://news.ycombinator.com/item?id=48998987) | kzrdude | 2026-07-21 | Gemini 3.6 Flash, 3.5 Flash-Lite, and 3.5 Fl | — | — |
| [48996221](https://news.ycombinator.com/item?id=48996221) | wasfgwp | 2026-07-21 | Gemini 3.6 Flash, 3.5 Flash-Lite, and 3.5 Fl | — | version |
| [48991043](https://news.ycombinator.com/item?id=48991043) | Squeeze2664 | 2026-07-21 | Ask HN: Claude Code or Codex? | — | — |
| [48986891](https://news.ycombinator.com/item?id=48986891) | wmf | 2026-07-21 | Nativ: Run frontier open models locally on y | — | version |
| [48986768](https://news.ycombinator.com/item?id=48986768) | oersted | 2026-07-21 | Nativ: Run frontier open models locally on y | — | link |
| [48981690](https://news.ycombinator.com/item?id=48981690) | ItsBob | 2026-07-20 | China’s open-weights AI strategy is winning | — | number |
| [48973444](https://news.ycombinator.com/item?id=48973444) | monster_truck | 2026-07-20 | Codex Resets | — | number |
| [48972587](https://news.ycombinator.com/item?id=48972587) | ezekiel68 | 2026-07-19 | Moonshot AI suspends new subscriptions due t | — | number |
| [48971044](https://news.ycombinator.com/item?id=48971044) | abalashov | 2026-07-19 | Moonshot AI suspends new subscriptions due t | — | number, version |
| [48970262](https://news.ycombinator.com/item?id=48970262) | yowlingcat | 2026-07-19 | Qwen 3.8 | — | number, version |
| [48969557](https://news.ycombinator.com/item?id=48969557) | vblanco | 2026-07-19 | Qwen 3.8 | — | — |
| [48969555](https://news.ycombinator.com/item?id=48969555) | KronisLV | 2026-07-19 | OpenAI reduces Codex Model Context Size from | — | number, version |
| [48968261](https://news.ycombinator.com/item?id=48968261) | 3abiton | 2026-07-19 | Qwen 3.8 | — | number, version |
| [48967613](https://news.ycombinator.com/item?id=48967613) | Alifatisk | 2026-07-19 | DeepSeek routes your request to Fable5 | — | version |
| [48967370](https://news.ycombinator.com/item?id=48967370) | SwellJoe | 2026-07-19 | Qwen 3.8 | — | version |
| [48967291](https://news.ycombinator.com/item?id=48967291) | rubslopes | 2026-07-19 | Qwen 3.8 | — | — |
| [48967077](https://news.ycombinator.com/item?id=48967077) | bel8 | 2026-07-19 | The Kimi K3 Moment | — | number, version |
| [48966879](https://news.ycombinator.com/item?id=48966879) | 5701652400 | 2026-07-19 | Qwen 3.8 | — | version |
| [48966391](https://news.ycombinator.com/item?id=48966391) | SwellJoe | 2026-07-19 | Qwen 3.8 | — | number, version |
| [48966119](https://news.ycombinator.com/item?id=48966119) | progx | 2026-07-19 | The Kimi K3 Moment | — | — |
| [48962434](https://news.ycombinator.com/item?id=48962434) | SwellJoe | 2026-07-18 | The Kimi K3 Moment | — | — |
| [48949188](https://news.ycombinator.com/item?id=48949188) | devttyeu | 2026-07-17 | Kimi K3, and what we can still learn from th | — | link, version |
| [48942486](https://news.ycombinator.com/item?id=48942486) | rsanek | 2026-07-17 | Kimi K3: Open Frontier Intelligence | — | link, number |
| [48940626](https://news.ycombinator.com/item?id=48940626) | KronisLV | 2026-07-16 | Kimi K3: Open Frontier Intelligence | — | link, version |
| [48939274](https://news.ycombinator.com/item?id=48939274) | cg5280 | 2026-07-16 | Kimi K3: Open Frontier Intelligence | — | number |
| [48937822](https://news.ycombinator.com/item?id=48937822) | ignoramous | 2026-07-16 | Kimi K3: Open Frontier Intelligence | — | number, version |
| [48937199](https://news.ycombinator.com/item?id=48937199) | computerex | 2026-07-16 | Kimi K3: Open Frontier Intelligence | — | — |
| [48936159](https://news.ycombinator.com/item?id=48936159) | NortySpock | 2026-07-16 | Kimi K3: Open Frontier Intelligence | — | link |
| [48936108](https://news.ycombinator.com/item?id=48936108) | m3h | 2026-07-16 | Kimi K3: Open Frontier Intelligence | — | number, version, code |
| [48925838](https://news.ycombinator.com/item?id=48925838) | KronisLV | 2026-07-15 | Inkling: Our Open-Weights Model | — | number, version |
| [48925689](https://news.ycombinator.com/item?id=48925689) | 0xbadcafebee | 2026-07-15 | Inkling: Our Open-Weights Model | — | number |
| [48920481](https://news.ycombinator.com/item?id=48920481) | diseasedyak | 2026-07-15 | Bonsai 27B: A 27B-Class model that runs on a | — | version |
| [48916323](https://news.ycombinator.com/item?id=48916323) | rurban | 2026-07-15 | Do frontier models matter if most production | — | version |
| [48907392](https://news.ycombinator.com/item?id=48907392) | embedding-shape | 2026-07-14 | Codex starts encrypting sub-agent prompts | — | version |
| [48902566](https://news.ycombinator.com/item?id=48902566) | applfanboysbgon | 2026-07-14 | Show HN: Jacquard, a programming language fo | — | number |
| [48886802](https://news.ycombinator.com/item?id=48886802) | marcus_holmes | 2026-07-13 | Claude Code sends 33k tokens before reading  | — | — |
| [48884391](https://news.ycombinator.com/item?id=48884391) | ekidd | 2026-07-12 | I love LLMs, I hate hype | — | number, version |
| [48868036](https://news.ycombinator.com/item?id=48868036) | SwellJoe | 2026-07-11 | Inference Optimization for MiMo v2.5: Pushin | — | number |
| [48866511](https://news.ycombinator.com/item?id=48866511) | ignoramous | 2026-07-10 | Inference Optimization for MiMo v2.5: Pushin | — | link, version |
| [48866294](https://news.ycombinator.com/item?id=48866294) | Ancapistani | 2026-07-10 | Apple Silicon Exec Explains Mac Mini AI Dema | — | number |
| [48857510](https://news.ycombinator.com/item?id=48857510) | beefsack | 2026-07-10 | GPT-5.6 | — | version, code |
| [48852596](https://news.ycombinator.com/item?id=48852596) | VulgarExigency | 2026-07-09 | Hy3 | — | version |
| [48848970](https://news.ycombinator.com/item?id=48848970) | wgd | 2026-07-09 | Hy3 | — | version |
| [48848653](https://news.ycombinator.com/item?id=48848653) | ignoramous | 2026-07-09 | Hy3 | — | number, version |
| [48848290](https://news.ycombinator.com/item?id=48848290) | andai | 2026-07-09 | Hy3 | — | version |
| [48839643](https://news.ycombinator.com/item?id=48839643) | ignoramous | 2026-07-09 | Rewriting Bun in Rust | — | number, version, code |
| [48838614](https://news.ycombinator.com/item?id=48838614) | bashtoni | 2026-07-08 | Grok 4.5 | — | — |
| [48834410](https://news.ycombinator.com/item?id=48834410) | wongarsu | 2026-07-08 | SWE-1.7 Reach Near GPT 5.5 and Opus Intellig | — | number |
| [48823692](https://news.ycombinator.com/item?id=48823692) | bel8 | 2026-07-07 | How did we make DeepSeek outperform Opus | — | link, version |
| [48823202](https://news.ycombinator.com/item?id=48823202) | diseasedyak | 2026-07-07 | GLM 5.2 and the coming AI margin collapse | — | — |
| [48820183](https://news.ycombinator.com/item?id=48820183) | ahmadawais | 2026-07-07 | How did we make DeepSeek outperform Opus | — | link, version |
| [48819784](https://news.ycombinator.com/item?id=48819784) | _def | 2026-07-07 | GLM 5.2 and the coming AI margin collapse | — | — |
| [48816644](https://news.ycombinator.com/item?id=48816644) | jeremyjh | 2026-07-07 | GLM 5.2 and the coming AI margin collapse | — | number |
| [48815378](https://news.ycombinator.com/item?id=48815378) | wongarsu | 2026-07-07 | GLM 5.2 and the coming AI margin collapse | — | number |
| [48814927](https://news.ycombinator.com/item?id=48814927) | miroljub | 2026-07-07 | GLM 5.2 and the coming AI margin collapse | — | version |
| [48813015](https://news.ycombinator.com/item?id=48813015) | Obertr | 2026-07-07 | GLM 5.2 and the coming AI margin collapse | opinion | number, version |
| [48812682](https://news.ycombinator.com/item?id=48812682) | jmyeet | 2026-07-07 | GLM 5.2 and the coming AI margin collapse | — | number |
| [48812660](https://news.ycombinator.com/item?id=48812660) | AgentMasterRace | 2026-07-07 | GLM 5.2 and the coming AI margin collapse | comparison | number, version |
| [48812549](https://news.ycombinator.com/item?id=48812549) | Footprint0521 | 2026-07-07 | Fable turned reMarkable into Tom Riddle's di | — | — |
| [48811741](https://news.ycombinator.com/item?id=48811741) | eunos | 2026-07-06 | A global workspace in language models | — | — |
| [48811296](https://news.ycombinator.com/item?id=48811296) | KronisLV | 2026-07-06 | GLM 5.2 and the coming AI margin collapse | comparison | link, number, version |
| [48801023](https://news.ycombinator.com/item?id=48801023) | KronisLV | 2026-07-06 | GPT-5.6 Sol Ultra will be in Codex | — | — |
| [48766145](https://news.ycombinator.com/item?id=48766145) | aftbit | 2026-07-02 | Claude Code is steganographically marking re | — | link, code |
| [48757486](https://news.ycombinator.com/item?id=48757486) | mdasen | 2026-07-02 | CursorBench 3.1 | — | link, version |
| [48750973](https://news.ycombinator.com/item?id=48750973) | SwellJoe | 2026-07-01 | Qwen 3.6 27B is the sweet spot for local dev | — | link, number, version |
| [48746790](https://news.ycombinator.com/item?id=48746790) | jm4 | 2026-07-01 | Department of Commerce has lifted export con | — | version |
| [48744837](https://news.ycombinator.com/item?id=48744837) | nextaccountic | 2026-07-01 | Redeploying Fable 5 | — | — |
| [48744338](https://news.ycombinator.com/item?id=48744338) | KronisLV | 2026-07-01 | Department of Commerce has lifted export con | — | version |
| [48743195](https://news.ycombinator.com/item?id=48743195) | nl | 2026-07-01 | Redeploying Fable 5 | — | version |
| [48739852](https://news.ycombinator.com/item?id=48739852) | MikuMikuMe | 2026-06-30 | LongCat-2.0, a large-scale MoE model with 1. | — | — |
| [48739719](https://news.ycombinator.com/item?id=48739719) | MikuMikuMe | 2026-06-30 | LongCat-2.0, a large-scale MoE model with 1. | — | — |
| [48739203](https://news.ycombinator.com/item?id=48739203) | Imustaskforhelp | 2026-06-30 | Claude Code is steganographically marking re | — | number, version |
| [48738865](https://news.ycombinator.com/item?id=48738865) | doctorpangloss | 2026-06-30 | LongCat-2.0, a large-scale MoE model with 1. | — | — |
| [48737952](https://news.ycombinator.com/item?id=48737952) | aftbit | 2026-06-30 | Claude Code is steganographically marking re | — | — |
| [48727549](https://news.ycombinator.com/item?id=48727549) | dryarzeg | 2026-06-30 | LongCat-2.0, a large-scale MoE model with 1. | — | — |
| [48725565](https://news.ycombinator.com/item?id=48725565) | mark_l_watson | 2026-06-29 | Qwen 3.6 27B is the sweet spot for local dev | — | number |
| [48719827](https://news.ycombinator.com/item?id=48719827) | maherbeg | 2026-06-29 | GLM 5.2 beats Claude in our benchmarks | — | — |
| [48714689](https://news.ycombinator.com/item?id=48714689) | try-working | 2026-06-29 | GLM 5.2 beats Claude in our benchmarks | — | — |
| [48714414](https://news.ycombinator.com/item?id=48714414) | neya | 2026-06-29 | GLM 5.2 beats Claude in our benchmarks | usage_demo | number, version |
| [48714253](https://news.ycombinator.com/item?id=48714253) | acters | 2026-06-29 | GLM 5.2 beats Claude in our benchmarks | — | version |
| [48713946](https://news.ycombinator.com/item?id=48713946) | SwellJoe | 2026-06-29 | GLM 5.2 beats Claude in our benchmarks | — | number |
| [48713876](https://news.ycombinator.com/item?id=48713876) | gertlabs | 2026-06-29 | GLM 5.2 beats Claude in our benchmarks | — | number |
| [48713609](https://news.ycombinator.com/item?id=48713609) | lebovic | 2026-06-29 | GLM 5.2 beats Claude in our benchmarks | benchmark | link, number |
| [48712434](https://news.ycombinator.com/item?id=48712434) | SwellJoe | 2026-06-28 | GLM 5.2 beats Claude in our benchmarks | benchmark | link, version |
| [48707749](https://news.ycombinator.com/item?id=48707749) | mark_l_watson | 2026-06-28 | Google limits Meta's use of its Gemini AI mo | — | version |
| [48706187](https://news.ycombinator.com/item?id=48706187) | try-working | 2026-06-28 | Show HN: role-model, a router for hybrid loc | — | link |
| [48706130](https://news.ycombinator.com/item?id=48706130) | try-working | 2026-06-28 | Wayfinder Router: deterministic routing of q | — | — |
| [48705577](https://news.ycombinator.com/item?id=48705577) | SwellJoe | 2026-06-28 | "No, I swear I wrote this." | — | link, number, version |
| [48705018](https://news.ycombinator.com/item?id=48705018) | francisduvivier | 2026-06-28 | AMD Strix Halo RDMA Cluster Setup Guide | — | — |
| [48697282](https://news.ycombinator.com/item?id=48697282) | chronogram | 2026-06-27 | DSpark: Speculative decoding accelerates LLM | — | version |
| [48697240](https://news.ycombinator.com/item?id=48697240) | kamranjon | 2026-06-27 | DSpark: Speculative decoding accelerates LLM | — | link, version |
| [48697233](https://news.ycombinator.com/item?id=48697233) | sschueller | 2026-06-27 | DSpark: Speculative decoding accelerates LLM | — | number |
| [48697229](https://news.ycombinator.com/item?id=48697229) | pokot0 | 2026-06-27 | DSpark: Speculative decoding accelerates LLM | — | — |
| [48696874](https://news.ycombinator.com/item?id=48696874) | piterrro | 2026-06-27 | DSpark: Speculative decoding accelerates LLM | — | number |
| [48695405](https://news.ycombinator.com/item?id=48695405) | 127 | 2026-06-27 | Previewing GPT‑5.6 Sol: a next-generation mo | — | number, version |
| [48694821](https://news.ycombinator.com/item?id=48694821) | dools | 2026-06-27 | Show HN: Smart model routing directly in Cla | — | version |
| [48693678](https://news.ycombinator.com/item?id=48693678) | mark_l_watson | 2026-06-27 | Previewing GPT‑5.6 Sol: a next-generation mo | — | version |
| [48693573](https://news.ycombinator.com/item?id=48693573) | wyrdcurt | 2026-06-26 | We can still stop California's 3D printer su | — | — |
| [48691542](https://news.ycombinator.com/item?id=48691542) | lmf4lol | 2026-06-26 | Previewing GPT‑5.6 Sol: a next-generation mo | — | version |
| [48691405](https://news.ycombinator.com/item?id=48691405) | general1465 | 2026-06-26 | U.S. government will decide who gets to use  | — | number, version |
| [48690545](https://news.ycombinator.com/item?id=48690545) | whalesalad | 2026-06-26 | Previewing GPT‑5.6 Sol: a next-generation mo | — | version |
| [48686159](https://news.ycombinator.com/item?id=48686159) | _flux | 2026-06-26 | Why current LLM costs are not sustainable | — | link, number, version, code |
| [48684002](https://news.ycombinator.com/item?id=48684002) | KronisLV | 2026-06-26 | Why current LLM costs are not sustainable | — | number, version |
| [48680421](https://news.ycombinator.com/item?id=48680421) | Tuna-Fish | 2026-06-25 | The unbearable cheapness of open weight mode | — | number |
| [48674493](https://news.ycombinator.com/item?id=48674493) | samuelknight | 2026-06-25 | Anthropic says Alibaba illicitly extracted C | — | link, number |
| [48671159](https://news.ycombinator.com/item?id=48671159) | reacharavindh | 2026-06-25 | Computer use in Gemini 3.5 Flash | — | — |
| [48671052](https://news.ycombinator.com/item?id=48671052) | Scaevolus | 2026-06-25 | The unbearable cheapness of open weight mode | — | number |
| [48670501](https://news.ycombinator.com/item?id=48670501) | PhilippGille | 2026-06-25 | GLM-5.2 is a step change for open agents | — | link, version |
| [48668499](https://news.ycombinator.com/item?id=48668499) | ssivark | 2026-06-25 | Anthropic says Alibaba illicitly extracted C | — | version |
| [48668444](https://news.ycombinator.com/item?id=48668444) | forsalebypwner | 2026-06-25 | GLM-5.2 is a step change for open agents | — | — |
| [48668297](https://news.ycombinator.com/item?id=48668297) | try-working | 2026-06-25 | GLM-5.2 is a step change for open agents | — | link, number, version |
| [48667886](https://news.ycombinator.com/item?id=48667886) | lebovic | 2026-06-25 | Anthropic says Alibaba illicitly extracted C | — | link, version |
| [48667783](https://news.ycombinator.com/item?id=48667783) | tristanj | 2026-06-25 | Anthropic says Alibaba illicitly extracted C | — | number, version |
| [48666780](https://news.ycombinator.com/item?id=48666780) | gandreani | 2026-06-24 | GLM-5.2 is a step change for open agents | — | link, version |
| [48657764](https://news.ycombinator.com/item?id=48657764) | criley2 | 2026-06-24 | Grok Build 0.1: Intelligence, Performance an | — | — |
| [48655728](https://news.ycombinator.com/item?id=48655728) | ignoramous | 2026-06-24 | There is minimal downside to switching to op | — | link, number, version |
| [48651637](https://news.ycombinator.com/item?id=48651637) | KronisLV | 2026-06-23 | Anthropic updates their terms to verify age  | — | link, number, version |
| [48648082](https://news.ycombinator.com/item?id=48648082) | SwellJoe | 2026-06-23 | AI's Affordability Crisis | — | number, version |
| [48648062](https://news.ycombinator.com/item?id=48648062) | zozbot234 | 2026-06-23 | GLM-5.2 – How to Run Locally | — | number |
| [48646798](https://news.ycombinator.com/item?id=48646798) | trollbridge | 2026-06-23 | AI's Affordability Crisis | — | number, version |
| [48644965](https://news.ycombinator.com/item?id=48644965) | antirez | 2026-06-23 | GLM-5.2 – How to Run Locally | — | number, version |
| [48644905](https://news.ycombinator.com/item?id=48644905) | diseasedyak | 2026-06-23 | VibeThinker: 3B param model that beats Opus  | — | number |
| [48642141](https://news.ycombinator.com/item?id=48642141) | rubymamis | 2026-06-23 | Will It Mythos? | — | link, version |
| [48641848](https://news.ycombinator.com/item?id=48641848) | abalashov | 2026-06-23 | Ask HN: Anthropic banned me from using Claud | — | version |
| [48637743](https://news.ycombinator.com/item?id=48637743) | andai | 2026-06-22 | GLM-5.2 – How to Run Locally | — | — |
| [48630461](https://news.ycombinator.com/item?id=48630461) | ricardobeat | 2026-06-22 | Sakana Fugu | — | number, version, code |
| [48628034](https://news.ycombinator.com/item?id=48628034) | iagooar | 2026-06-22 | GLM 5.2 vs. Opus | — | — |
| [48626795](https://news.ycombinator.com/item?id=48626795) | linzhangrun | 2026-06-22 | There is minimal downside to switching to op | — | number, version |
| [48626751](https://news.ycombinator.com/item?id=48626751) | johndough | 2026-06-22 | There is minimal downside to switching to op | — | link, number, version |
| [48626468](https://news.ycombinator.com/item?id=48626468) | johndough | 2026-06-22 | There is minimal downside to switching to op | — | number |
| [48625716](https://news.ycombinator.com/item?id=48625716) | coffinbirth | 2026-06-22 | There is minimal downside to switching to op | — | link, version, code |
| [48624502](https://news.ycombinator.com/item?id=48624502) | trollbridge | 2026-06-22 | Identity verification on Claude | — | version |
| [48624490](https://news.ycombinator.com/item?id=48624490) | radhitya | 2026-06-22 | There is minimal downside to switching to op | — | — |
| [48623772](https://news.ycombinator.com/item?id=48623772) | chorizo | 2026-06-21 | Identity verification on Claude | — | — |
| [48622918](https://news.ycombinator.com/item?id=48622918) | zozbot234 | 2026-06-21 | Two Qwen3 models on one DGX Spark: the resid | — | — |
| [48622477](https://news.ycombinator.com/item?id=48622477) | secretslol | 2026-06-21 | Identity verification on Claude | — | version |
| [48621792](https://news.ycombinator.com/item?id=48621792) | stavros | 2026-06-21 | Identity verification on Claude | — | version |
| [48609127](https://news.ycombinator.com/item?id=48609127) | andai | 2026-06-20 | GPT-5.5 hallucinates 3x more than MIT-licens | — | version |
| [48606020](https://news.ycombinator.com/item?id=48606020) | nextaccountic | 2026-06-20 | GPT-5.5 hallucinates 3x more than MIT-licens | — | version |
| [48605020](https://news.ycombinator.com/item?id=48605020) | aesthesia | 2026-06-20 | GPT-5.5 hallucinates 3x more than MIT-licens | — | number, version |
| [48604736](https://news.ycombinator.com/item?id=48604736) | solid_fuel | 2026-06-19 | Norway imposes near ban on AI in elementary  | — | link, number, version |
| [48604666](https://news.ycombinator.com/item?id=48604666) | solid_fuel | 2026-06-19 | GPT-5.5 hallucinates 3x more than MIT-licens | — | number, version |
| [48591855](https://news.ycombinator.com/item?id=48591855) | ricardobeat | 2026-06-18 | GLM-5.2 is probably the most powerful text-o | — | — |
| [48587139](https://news.ycombinator.com/item?id=48587139) | theanonymousone | 2026-06-18 | US holds off blacklisting DeepSeek, more tha | — | version |
| [48587006](https://news.ycombinator.com/item?id=48587006) | jameson | 2026-06-18 | DeepSeek Introduces Vision | — | number, version, code |
| [48582836](https://news.ycombinator.com/item?id=48582836) | 5701652400 | 2026-06-18 | DeepSeek Introduces Vision | — | — |
| [48578968](https://news.ycombinator.com/item?id=48578968) | benjiro29 | 2026-06-18 | GLM-5.2 is the new leading open weights mode | — | number, version |
| [48578927](https://news.ycombinator.com/item?id=48578927) | fraXis | 2026-06-18 | US holds off blacklisting DeepSeek, more tha | — | number |
| [48578722](https://news.ycombinator.com/item?id=48578722) | rvz | 2026-06-18 | Show HN: A free CLI coding agent, powered by | — | version |
| [48576279](https://news.ycombinator.com/item?id=48576279) | dryarzeg | 2026-06-17 | US holds off blacklisting DeepSeek, more tha | — | version |
| [48571729](https://news.ycombinator.com/item?id=48571729) | papersail | 2026-06-17 | GLM-5.2 is the new leading open weights mode | — | number, version, code |
| [48570538](https://news.ycombinator.com/item?id=48570538) | 0xbadcafebee | 2026-06-17 | GLM-5.2 is the new leading open weights mode | — | number |
| [48570411](https://news.ycombinator.com/item?id=48570411) | piterrro | 2026-06-17 | GLM-5.2 is the new leading open weights mode | — | number, version |
| [48569862](https://news.ycombinator.com/item?id=48569862) | pjerem | 2026-06-17 | GLM-5.2 is the new leading open weights mode | — | number, version |
| [48569244](https://news.ycombinator.com/item?id=48569244) | kristopolous | 2026-06-17 | GLM-5.2 is the new leading open weights mode | — | link, version, code |
| [48568549](https://news.ycombinator.com/item?id=48568549) | tensegrist | 2026-06-17 | GLM-5.2 is the new leading open weights mode | — | number, version |
| [48566180](https://news.ycombinator.com/item?id=48566180) | nl | 2026-06-17 | Leaked OpenAI financials show $38.5B loss an | — | link, number |
| [48565267](https://news.ycombinator.com/item?id=48565267) | sosodev | 2026-06-17 | Ask HN: Has anyone replaced Claude/GPT with  | — | number |
| [48565117](https://news.ycombinator.com/item?id=48565117) | mark_l_watson | 2026-06-17 | SubQ 1.1 Small | — | number, version |
| [48560093](https://news.ycombinator.com/item?id=48560093) | namr2000 | 2026-06-16 | Cohere's First Model for Developers | — | link, number |
| [48557044](https://news.ycombinator.com/item?id=48557044) | StevenWaterman | 2026-06-16 | Running local models is good now | — | number, version |
| [48553543](https://news.ycombinator.com/item?id=48553543) | amunozo | 2026-06-16 | Cohere's First Model for Developers | — | number |
| [48551176](https://news.ycombinator.com/item?id=48551176) | goranmoomin | 2026-06-16 | Ask HN: Has anyone replaced Claude/GPT with  | — | number, version |
| [48547022](https://news.ycombinator.com/item?id=48547022) | ThomasGlanzmann | 2026-06-15 | Ask HN: Has anyone replaced Claude/GPT with  | — | number |
| [48546018](https://news.ycombinator.com/item?id=48546018) | mark_l_watson | 2026-06-15 | Ask HN: Has anyone replaced Claude/GPT with  | — | version |
| [48545154](https://news.ycombinator.com/item?id=48545154) | gigatexal | 2026-06-15 | Ask HN: Has anyone replaced Claude/GPT with  | — | — |
| [48544435](https://news.ycombinator.com/item?id=48544435) | rubslopes | 2026-06-15 | Ask HN: Which cheap Chinese LLM are you usin | — | number, version |
| [48539725](https://news.ycombinator.com/item?id=48539725) | rektlessness | 2026-06-15 | Openrouter Fusion API | — | number, version |
| [48539653](https://news.ycombinator.com/item?id=48539653) | arizen | 2026-06-15 | GLM 5.2 Is Out | — | link, version |
| [48536401](https://news.ycombinator.com/item?id=48536401) | zionsati | 2026-06-15 | Ask HN: Which cheap Chinese LLM are you usin | — | link, version |
| [48525949](https://news.ycombinator.com/item?id=48525949) | zionsati | 2026-06-14 | Ask HN: Which cheap Chinese LLM are you usin | — | version |
| [48525296](https://news.ycombinator.com/item?id=48525296) | abustamam | 2026-06-14 | GLM 5.2 Is Out | — | — |
| [48522818](https://news.ycombinator.com/item?id=48522818) | montroser | 2026-06-14 | AI coding at home without going broke | — | number |
| [48521194](https://news.ycombinator.com/item?id=48521194) | atreids | 2026-06-13 | AI coding at home without going broke | — | link, number, version |
| [48520632](https://news.ycombinator.com/item?id=48520632) | zozbot234 | 2026-06-13 | AI Coding at Home Without Going Broke | — | number |
| [48519652](https://news.ycombinator.com/item?id=48519652) | atemerev | 2026-06-13 | AI Coding at Home Without Going Broke | — | number |
| [48515650](https://news.ycombinator.com/item?id=48515650) | monster_truck | 2026-06-13 | Open source AI must win | — | number |
| [48515542](https://news.ycombinator.com/item?id=48515542) | monster_truck | 2026-06-13 | Statement on US government directive to susp | — | — |
| [48514436](https://news.ycombinator.com/item?id=48514436) | sourcecodeplz | 2026-06-13 | Statement on US government directive to susp | — | version |
| [48512324](https://news.ycombinator.com/item?id=48512324) | jchw | 2026-06-13 | Statement on US government directive to susp | — | version |
| [48512252](https://news.ycombinator.com/item?id=48512252) | zmmmmm | 2026-06-13 | Statement on US government directive to susp | — | version |
| [48511530](https://news.ycombinator.com/item?id=48511530) | andrewchambers | 2026-06-13 | Statement on US government directive to susp | — | — |
| [48509102](https://news.ycombinator.com/item?id=48509102) | jwbron | 2026-06-12 | Kimi K2.7-Code: open-source coding model wit | — | version |
| [48509079](https://news.ycombinator.com/item?id=48509079) | jwbron | 2026-06-12 | Kimi K2.7-Code: open-source coding model wit | — | version |
| [48507479](https://news.ycombinator.com/item?id=48507479) | mdasen | 2026-06-12 | Kimi K2.7-Code: open-source coding model wit | deep_analysis | number, version |
| [48506648](https://news.ycombinator.com/item?id=48506648) | bel8 | 2026-06-12 | Kimi K2.7-Code: open-source coding model wit | comparison | link, number |
| [48505469](https://news.ycombinator.com/item?id=48505469) | 0xbadcafebee | 2026-06-12 | Kimi K2.7-Code: open-source coding model wit | — | version |
| [48504016](https://news.ycombinator.com/item?id=48504016) | the_lucifer | 2026-06-12 | OpenAI mulls slashing prices as it competes  | — | number, version |
| [48503724](https://news.ycombinator.com/item?id=48503724) | solarkraft | 2026-06-12 | Kimi K2.7-Code: open-source coding model wit | — | — |
| [48503550](https://news.ycombinator.com/item?id=48503550) | psittacus | 2026-06-12 | Kimi K2.7-Code: open-source coding model wit | — | link |
| [48503533](https://news.ycombinator.com/item?id=48503533) | trollbridge | 2026-06-12 | Kimi K2.7-Code: open-source coding model wit | workflow | number, version |
| [48499218](https://news.ycombinator.com/item?id=48499218) | UncleOxidant | 2026-06-12 | Claude Fable is relentlessly proactive | — | number, version |
| [48495770](https://news.ycombinator.com/item?id=48495770) | alkonaut | 2026-06-11 | MiMo Code is now released and open-source | — | — |
| [48491812](https://news.ycombinator.com/item?id=48491812) | ignoramous | 2026-06-11 | MiMo Code is now released and open-source | — | number, version |
| [48490661](https://news.ycombinator.com/item?id=48490661) | zozbot234 | 2026-06-11 | The Economics of Speculative Decoding | — | — |
| [48488118](https://news.ycombinator.com/item?id=48488118) | smartbit | 2026-06-11 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | deep_analysis | link, number, version, code |
| [48486926](https://news.ycombinator.com/item?id=48486926) | Grimblewald | 2026-06-11 | Cybersecurity researchers aren't happy about | — | — |
| [48486402](https://news.ycombinator.com/item?id=48486402) | edot | 2026-06-11 | Notes on DeepSeek | — | — |
| [48482769](https://news.ycombinator.com/item?id=48482769) | imagetic | 2026-06-10 | Notes on DeepSeek | — | — |
| [48480483](https://news.ycombinator.com/item?id=48480483) | holysantamaria | 2026-06-10 | Claude Fable 5 | — | version |
| [48480261](https://news.ycombinator.com/item?id=48480261) | Footprint0521 | 2026-06-10 | Grit: Rewriting Git in Rust with agents | — | number |
| [48474588](https://news.ycombinator.com/item?id=48474588) | Vetch | 2026-06-10 | If Claude Fable stops helping you, you'll ne | — | number, version |
| [48472070](https://news.ycombinator.com/item?id=48472070) | sevenzero | 2026-06-10 | Claude Fable 5 | — | — |
| [48471771](https://news.ycombinator.com/item?id=48471771) | caleblloyd | 2026-06-10 | Claude Fable 5 | — | number |
| [48471351](https://news.ycombinator.com/item?id=48471351) | jameson | 2026-06-10 | Claude Fable 5 | — | link |
| [48470213](https://news.ycombinator.com/item?id=48470213) | trollbridge | 2026-06-10 | MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 | — | — |
| [48466624](https://news.ycombinator.com/item?id=48466624) | syzygyhack | 2026-06-09 | Claude Fable 5 | — | — |
| [48464959](https://news.ycombinator.com/item?id=48464959) | himata4113 | 2026-06-09 | Claude Fable 5 | — | — |
| [48464915](https://news.ycombinator.com/item?id=48464915) | baalimago | 2026-06-09 | Claude Fable 5 | — | number |
| [48463687](https://news.ycombinator.com/item?id=48463687) | metalspot | 2026-06-09 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | version |
| [48462130](https://news.ycombinator.com/item?id=48462130) | ilaksh | 2026-06-09 | MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 | — | — |
| [48458857](https://news.ycombinator.com/item?id=48458857) | zmmmmm | 2026-06-09 | AI is slowing down | — | number |
| [48458001](https://news.ycombinator.com/item?id=48458001) | atemerev | 2026-06-09 | MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 | — | version |
| [48456466](https://news.ycombinator.com/item?id=48456466) | justinram11 | 2026-06-09 | Ask HN: What are tools you have made for you | — | link |
| [48456166](https://news.ycombinator.com/item?id=48456166) | Frannky | 2026-06-09 | MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 | — | number |
| [48456099](https://news.ycombinator.com/item?id=48456099) | andai | 2026-06-09 | MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 | — | — |
| [48455186](https://news.ycombinator.com/item?id=48455186) | gertlabs | 2026-06-09 | MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 | — | — |
| [48453683](https://news.ycombinator.com/item?id=48453683) | mark_l_watson | 2026-06-08 | Apple reveals new AI architecture built arou | — | number, version |
| [48453222](https://news.ycombinator.com/item?id=48453222) | SwellJoe | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | number |
| [48452996](https://news.ycombinator.com/item?id=48452996) | andai | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | deep_analysis | link, version |
| [48452673](https://news.ycombinator.com/item?id=48452673) | zozbot234 | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | number |
| [48450981](https://news.ycombinator.com/item?id=48450981) | gertlabs | 2026-06-08 | MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 | benchmark | link, version |
| [48450276](https://news.ycombinator.com/item?id=48450276) | SwellJoe | 2026-06-08 | MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 | benchmark | link, version |
| [48449789](https://news.ycombinator.com/item?id=48449789) | jona-f | 2026-06-08 | MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 | — | version |
| [48449696](https://news.ycombinator.com/item?id=48449696) | SwellJoe | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | version |
| [48448997](https://news.ycombinator.com/item?id=48448997) | atemerev | 2026-06-08 | MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 | — | version |
| [48448772](https://news.ycombinator.com/item?id=48448772) | unrvl22 | 2026-06-08 | MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 | — | version |
| [48447778](https://news.ycombinator.com/item?id=48447778) | RussianCow | 2026-06-08 | MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 | benchmark | link, number |
| [48447699](https://news.ycombinator.com/item?id=48447699) | flexagoon | 2026-06-08 | MiMo-v2.5-Pro-UltraSpeed: 1T model with 1000 | — | — |
| [48447044](https://news.ycombinator.com/item?id=48447044) | onlyrealcuzzo | 2026-06-08 | Replies to comments on my "LLMs are eroding  | — | number |
| [48446602](https://news.ycombinator.com/item?id=48446602) | smhanov | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | — |
| [48444621](https://news.ycombinator.com/item?id=48444621) | fc417fc802 | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | benchmark | link, number |
| [48444400](https://news.ycombinator.com/item?id=48444400) | smartbit | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | comparison | link, version, code |
| [48444265](https://news.ycombinator.com/item?id=48444265) | fc417fc802 | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | link |
| [48444125](https://news.ycombinator.com/item?id=48444125) | amunozo | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | version |
| [48442945](https://news.ycombinator.com/item?id=48442945) | metalspot | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | usage_demo | number, version |
| [48442933](https://news.ycombinator.com/item?id=48442933) | KronisLV | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | — |
| [48442874](https://news.ycombinator.com/item?id=48442874) | jampekka | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | link |
| [48442257](https://news.ycombinator.com/item?id=48442257) | woadwarrior01 | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | version |
| [48441863](https://news.ycombinator.com/item?id=48441863) | jumploops | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | link |
| [48441816](https://news.ycombinator.com/item?id=48441816) | raincole | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | — |
| [48441659](https://news.ycombinator.com/item?id=48441659) | wg0 | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | version |
| [48441583](https://news.ycombinator.com/item?id=48441583) | rurban | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | number |
| [48441514](https://news.ycombinator.com/item?id=48441514) | CJefferson | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | workflow | link, number, version, code |
| [48441271](https://news.ycombinator.com/item?id=48441271) | nerdsniper | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | version |
| [48441125](https://news.ycombinator.com/item?id=48441125) | Stitch4223 | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | version |
| [48441083](https://news.ycombinator.com/item?id=48441083) | unliftedq | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | version |
| [48440992](https://news.ycombinator.com/item?id=48440992) | morpheos137 | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | — |
| [48440796](https://news.ycombinator.com/item?id=48440796) | SwellJoe | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | benchmark | link, number, version |
| [48440698](https://news.ycombinator.com/item?id=48440698) | embedding-shape | 2026-06-08 | DeepSeek V4 Pro beats GPT-5.5 Pro on precisi | — | version |
| [48440424](https://news.ycombinator.com/item?id=48440424) | throw10920 | 2026-06-08 | The OnlyFans Economy of American AI | — | version |
| [48439925](https://news.ycombinator.com/item?id=48439925) | ignoramous | 2026-06-08 | The OnlyFans Economy of American AI | — | number, version |
| [48437130](https://news.ycombinator.com/item?id=48437130) | qarl | 2026-06-07 | The OnlyFans Economy of American AI | — | number, version |
| [48431530](https://news.ycombinator.com/item?id=48431530) | MichaelNolan | 2026-06-07 | Google to pay SpaceX $920M a month for compu | — | version |
| [48428077](https://news.ycombinator.com/item?id=48428077) | zozbot234 | 2026-06-06 | Nvidia is proposing a beast of a CPU system  | — | number |
| [48424119](https://news.ycombinator.com/item?id=48424119) | abustamam | 2026-06-06 | S&P 500 rejects SpaceX, also blocking entry  | — | number |
| [48423534](https://news.ycombinator.com/item?id=48423534) | rurban | 2026-06-06 | Ask HN: What is your (AI) dev tech stack / w | — | — |
| [48417329](https://news.ycombinator.com/item?id=48417329) | igorhvr | 2026-06-05 | Ask HN: What is your (AI) dev tech stack / w | — | link, number, version |
| [48416641](https://news.ycombinator.com/item?id=48416641) | 0xbadcafebee | 2026-06-05 | Ask HN: What is your (AI) dev tech stack / w | — | link, number, version |
| [48404092](https://news.ycombinator.com/item?id=48404092) | KronisLV | 2026-06-04 | Uber's $1,500/month AI limit is a useful sig | usage_demo | number, version |
| [48399726](https://news.ycombinator.com/item?id=48399726) | vablings | 2026-06-04 | Uber's $1,500/month AI limit is a useful sig | — | version |
| [48398610](https://news.ycombinator.com/item?id=48398610) | Haven880 | 2026-06-04 | I built a vulnerable app and spent $1,500 se | — | number, version |
| [48396839](https://news.ycombinator.com/item?id=48396839) | gpugreg | 2026-06-04 | Uber's $1,500/month AI limit is a useful sig | comparison | link, number |
| [48395242](https://news.ycombinator.com/item?id=48395242) | vinzenzu | 2026-06-04 | Uber's $1,500/month AI limit is a useful sig | deep_analysis | link, version |
| [48392791](https://news.ycombinator.com/item?id=48392791) | dakolli | 2026-06-04 | Uber's $1,500/month AI limit is a useful sig | deep_analysis | number, version |
| [48392175](https://news.ycombinator.com/item?id=48392175) | Kaliboy | 2026-06-04 | Uber's $1,500/month AI limit is a useful sig | — | number |
| [48391784](https://news.ycombinator.com/item?id=48391784) | tokioyoyo | 2026-06-03 | Uber's $1,500/month AI limit is a useful sig | — | — |
| [48388961](https://news.ycombinator.com/item?id=48388961) | eikenberry | 2026-06-03 | Uber's $1,500/month AI limit is a useful sig | — | version |
| [48388726](https://news.ycombinator.com/item?id=48388726) | ricardobayes | 2026-06-03 | Uber's $1,500/month AI limit is a useful sig | — | number |
| [48386816](https://news.ycombinator.com/item?id=48386816) | zozbot234 | 2026-06-03 | Gemma 4 12B: A unified, encoder-free multimo | — | number |
| [48382308](https://news.ycombinator.com/item?id=48382308) | ignoramous | 2026-06-03 | MAI-Code-1-Flash | — | link, number, version |
| [48381645](https://news.ycombinator.com/item?id=48381645) | antirez | 2026-06-03 | AI Engineers aren't safe from being replaced | — | number |
| [48381335](https://news.ycombinator.com/item?id=48381335) | bel8 | 2026-06-03 | MAI-Code-1-Flash | — | link, number, version |
| [48379892](https://news.ycombinator.com/item?id=48379892) | erichocean | 2026-06-03 | Bringing Up DeepSeek-V4-Flash on AMD MI300X | — | link |
| [48379801](https://news.ycombinator.com/item?id=48379801) | edg5000 | 2026-06-03 | Bringing Up DeepSeek-V4-Flash on AMD MI300X | — | — |
| [48377955](https://news.ycombinator.com/item?id=48377955) | chillfox | 2026-06-03 | MAI-Code-1-Flash | — | number, version |
| [48376959](https://news.ycombinator.com/item?id=48376959) | ignoramous | 2026-06-02 | GitHub Copilot App | — | number, version |
| [48374964](https://news.ycombinator.com/item?id=48374964) | benlm | 2026-06-02 | Bringing Up DeepSeek-V4-Flash on AMD MI300X | — | — |
| [48352493](https://news.ycombinator.com/item?id=48352493) | qtalen | 2026-06-01 | Reflection SDD: Use a Reflection Harness to  | — | version |
| [48339538](https://news.ycombinator.com/item?id=48339538) | jaggs | 2026-05-30 | The mysterious Hy3 LLM is topping OpenRouter | — | — |
| [48337924](https://news.ycombinator.com/item?id=48337924) | Petersipoi | 2026-05-30 | Anthropic surpasses OpenAI to become most va | — | number |
| [48336852](https://news.ycombinator.com/item?id=48336852) | Leynos | 2026-05-30 | Anthropic surpasses OpenAI to become most va | — | version |
| [48336800](https://news.ycombinator.com/item?id=48336800) | onlyrealcuzzo | 2026-05-30 | Corporate America Is Starting to Ration AI a | — | — |
| [48328966](https://news.ycombinator.com/item?id=48328966) | pants2 | 2026-05-29 | Claude Opus 4.8 | — | number |
| [48327036](https://news.ycombinator.com/item?id=48327036) | Bnjoroge | 2026-05-29 | Claude Opus 4.8 | — | — |
| [48323096](https://news.ycombinator.com/item?id=48323096) | GneojJ | 2026-05-29 | Claude Opus 4.8 | — | version |
| [48322964](https://news.ycombinator.com/item?id=48322964) | gaeld | 2026-05-29 | Real-time LLM Inference on Standard GPUs: 3k | — | number |
| [48322949](https://news.ycombinator.com/item?id=48322949) | malshe | 2026-05-29 | DeepSeek Slashes AI Costs to Cents | — | number |
| [48321519](https://news.ycombinator.com/item?id=48321519) | kirtivr | 2026-05-29 | Real-time LLM Inference on Standard GPUs: 3k | — | number |
| [48318989](https://news.ycombinator.com/item?id=48318989) | joshhart | 2026-05-29 | Claude Opus 4.8 | comparison | link, number |
| [48318880](https://news.ycombinator.com/item?id=48318880) | pants2 | 2026-05-29 | Claude Opus 4.8 | — | link |
| [48316438](https://news.ycombinator.com/item?id=48316438) | HDBaseT | 2026-05-28 | Claude Opus 4.8 | — | — |
| [48315040](https://news.ycombinator.com/item?id=48315040) | slopinthebag | 2026-05-28 | Claude Opus 4.8 | comparison | number, version |
| [48314932](https://news.ycombinator.com/item?id=48314932) | KronisLV | 2026-05-28 | Claude Opus 4.8 | — | — |
| [48313418](https://news.ycombinator.com/item?id=48313418) | pants2 | 2026-05-28 | Claude Opus 4.8 | comparison | link, number |
| [48313283](https://news.ycombinator.com/item?id=48313283) | londons_explore | 2026-05-28 | I think Anthropic and OpenAI have found prod | — | — |
| [48313033](https://news.ycombinator.com/item?id=48313033) | phainopepla2 | 2026-05-28 | Claude Opus 4.8 | — | version |
| [48308883](https://news.ycombinator.com/item?id=48308883) | mark_l_watson | 2026-05-28 | Ruby vs. Java vs. TypeScript: my experience  | — | number |
| [48305406](https://news.ycombinator.com/item?id=48305406) | mosselman | 2026-05-28 | Qwen3.7-Max Ran for 35 Hours on Unknown Hard | — | number, version |
| [48300457](https://news.ycombinator.com/item?id=48300457) | simonw | 2026-05-27 | I think Anthropic and OpenAI have found prod | — | link, number, version |
| [48299763](https://news.ycombinator.com/item?id=48299763) | gigatexal | 2026-05-27 | I added vi-modal bindings to my blog, a Chin | — | — |
| [48298675](https://news.ycombinator.com/item?id=48298675) | pzo | 2026-05-27 | I think Anthropic and OpenAI have found prod | — | number |
| [48298161](https://news.ycombinator.com/item?id=48298161) | NortySpock | 2026-05-27 | I think Anthropic and OpenAI have found prod | — | number, version |
| [48298115](https://news.ycombinator.com/item?id=48298115) | cassianoleal | 2026-05-27 | I think Anthropic and OpenAI have found prod | — | number, version |
| [48293951](https://news.ycombinator.com/item?id=48293951) | ericd | 2026-05-27 | DeepSeek makes the V4 Pro price discount per | — | link |
| [48288959](https://news.ycombinator.com/item?id=48288959) | 6ak74rfy | 2026-05-27 | Xiaomi MiMo-v2.5 Series API Permanent Price  | — | version |
| [48288908](https://news.ycombinator.com/item?id=48288908) | chillfox | 2026-05-27 | DeepSeek reasonix, DeepSeek native coding ag | — | version |
| [48288791](https://news.ycombinator.com/item?id=48288791) | discordance | 2026-05-27 | Xiaomi MiMo-v2.5 price drops 99% – AI pricin | — | number, version |
| [48287304](https://news.ycombinator.com/item?id=48287304) | NortySpock | 2026-05-26 | Outsourcing plus local AI will soon become m | — | link |
| [48284619](https://news.ycombinator.com/item?id=48284619) | wg0 | 2026-05-26 | Xiaomi MiMo-v2.5 Series API Permanent Price  | — | version |
| [48284074](https://news.ycombinator.com/item?id=48284074) | Flockster | 2026-05-26 | Xiaomi MiMo-v2.5 Series API Permanent Price  | — | number |
| [48280659](https://news.ycombinator.com/item?id=48280659) | aftbit | 2026-05-26 | Outsourcing plus local AI will soon become m | — | link, number, version |
| [48279652](https://news.ycombinator.com/item?id=48279652) | TacticalCoder | 2026-05-26 | Using AI to write better code more slowly | — | — |
| [48263719](https://news.ycombinator.com/item?id=48263719) | habosa | 2026-05-25 | DeepSeek makes the V4 Pro price discount per | — | — |
| [48263660](https://news.ycombinator.com/item?id=48263660) | Amekedl | 2026-05-25 | DeepSeek makes the V4 Pro price discount per | — | — |
| [48263099](https://news.ycombinator.com/item?id=48263099) | vinhnx | 2026-05-25 | DeepSeek makes the V4 Pro price discount per | usage_demo | link, number |
| [48263051](https://news.ycombinator.com/item?id=48263051) | HDBaseT | 2026-05-25 | DeepSeek makes the V4 Pro price discount per | — | number |
| [48262873](https://news.ycombinator.com/item?id=48262873) | nl | 2026-05-25 | DeepSeek makes the V4 Pro price discount per | benchmark | link, number, version |
| [48262448](https://news.ycombinator.com/item?id=48262448) | HDBaseT | 2026-05-25 | DeepSeek makes the V4 Pro price discount per | — | — |
| [48262210](https://news.ycombinator.com/item?id=48262210) | HDBaseT | 2026-05-24 | DeepSeek reasonix, DeepSeek native coding ag | — | version |
| [48262042](https://news.ycombinator.com/item?id=48262042) | elcritch | 2026-05-24 | DeepSeek makes the V4 Pro price discount per | benchmark | number, version |
| [48261733](https://news.ycombinator.com/item?id=48261733) | stavros | 2026-05-24 | DeepSeek reasonix, DeepSeek native coding ag | deep_analysis | number, code |
| [48261123](https://news.ycombinator.com/item?id=48261123) | h8hawk | 2026-05-24 | DeepSeek makes the V4 Pro price discount per | — | link |
| [48260621](https://news.ycombinator.com/item?id=48260621) | port11 | 2026-05-24 | DeepSeek reasonix, DeepSeek native coding ag | — | number |
| [48260258](https://news.ycombinator.com/item?id=48260258) | peheje | 2026-05-24 | DeepSeek reasonix, DeepSeek native coding ag | — | — |
| [48258264](https://news.ycombinator.com/item?id=48258264) | lot-xcvb | 2026-05-24 | DeepSeek makes the V4 Pro price discount per | deep_analysis | link, number |
| [48258056](https://news.ycombinator.com/item?id=48258056) | chillfox | 2026-05-24 | DeepSeek reasonix, DeepSeek native coding ag | — | — |
| [48258021](https://news.ycombinator.com/item?id=48258021) | wongarsu | 2026-05-24 | DeepSeek reasonix, DeepSeek native coding ag | — | number |
| [48257543](https://news.ycombinator.com/item?id=48257543) | bwfan123 | 2026-05-24 | DeepSeek reasonix, DeepSeek native coding ag | — | — |
| [48257509](https://news.ycombinator.com/item?id=48257509) | embedding-shape | 2026-05-24 | DeepSeek reasonix, DeepSeek native coding ag | — | link |
| [48255629](https://news.ycombinator.com/item?id=48255629) | intothemild | 2026-05-24 | Local LLMs perform better when you teach the | — | number, version |
| [48247688](https://news.ycombinator.com/item?id=48247688) | trollbridge | 2026-05-23 | Microsoft starts canceling Claude Code licen | — | number, version |
| [48244472](https://news.ycombinator.com/item?id=48244472) | raincole | 2026-05-23 | DeepSeek makes the V4 Pro price discount per | — | — |
| [48243776](https://news.ycombinator.com/item?id=48243776) | raincole | 2026-05-23 | DeepSeek makes the V4 Pro price discount per | — | number |
| [48243756](https://news.ycombinator.com/item?id=48243756) | pzo | 2026-05-23 | DeepSeek makes the V4 Pro price discount per | — | number |
| [48243684](https://news.ycombinator.com/item?id=48243684) | maltalex | 2026-05-23 | DeepSeek makes the V4 Pro price discount per | — | link |
| [48243363](https://news.ycombinator.com/item?id=48243363) | vinhnx | 2026-05-23 | DeepSeek makes the V4 Pro price discount per | promo | link, version |
| [48242980](https://news.ycombinator.com/item?id=48242980) | spudlyo | 2026-05-22 | DeepSeek makes the V4 Pro price discount per | usage_demo | number, version |
| [48242427](https://news.ycombinator.com/item?id=48242427) | 0xbadcafebee | 2026-05-22 | DeepSeek makes the V4 Pro price discount per | — | link |
| [48241620](https://news.ycombinator.com/item?id=48241620) | minimaxir | 2026-05-22 | DeepSeek makes the V4 Pro price discount per | deep_analysis | link, number, version |
| [48240690](https://news.ycombinator.com/item?id=48240690) | raincole | 2026-05-22 | DeepSeek makes the V4 Pro price discount per | — | — |
| [48239763](https://news.ycombinator.com/item?id=48239763) | wkcheng | 2026-05-22 | DeepSeek makes the V4 Pro price discount per | — | — |
| [48239072](https://news.ycombinator.com/item?id=48239072) | Reubend | 2026-05-22 | DeepSeek makes the V4 Pro price discount per | comparison | number, version |
| [48238761](https://news.ycombinator.com/item?id=48238761) | Sphax | 2026-05-22 | DeepSeek makes the V4 Pro price discount per | — | number |
| [48237983](https://news.ycombinator.com/item?id=48237983) | fallpeak | 2026-05-22 | The current AI pricing was always going to g | — | number, version |
| [48237919](https://news.ycombinator.com/item?id=48237919) | gruez | 2026-05-22 | The current AI pricing was always going to g | — | number, version |
| [48237918](https://news.ycombinator.com/item?id=48237918) | jplusequalt | 2026-05-22 | The current AI pricing was always going to g | — | number, version |
| [48237353](https://news.ycombinator.com/item?id=48237353) | PiRho3141 | 2026-05-22 | The current AI pricing was always going to g | — | number, version |
| [48230573](https://news.ycombinator.com/item?id=48230573) | mark_l_watson | 2026-05-22 | Google's Antigravity bait and switch | — | number |
| [48225405](https://news.ycombinator.com/item?id=48225405) | ang_cire | 2026-05-21 | Shunning AI is the human choice | — | — |
| [48216674](https://news.ycombinator.com/item?id=48216674) | tristanj | 2026-05-21 | Anthropic is expanding to Colossus2. Will us | — | link, number |
| [48214204](https://news.ycombinator.com/item?id=48214204) | KronisLV | 2026-05-20 | How fast is N tokens per second really? | — | link, version |
| [48206448](https://news.ycombinator.com/item?id=48206448) | DCKing | 2026-05-20 | Gemini 3.5 Flash | — | number, version |
| [48202873](https://news.ycombinator.com/item?id=48202873) | trollbridge | 2026-05-20 | Show HN: Forge – Guardrails take an 8B model | — | — |
| [48200545](https://news.ycombinator.com/item?id=48200545) | gpugreg | 2026-05-19 | Gemini 3.5 Flash | — | link, number |
| [48199741](https://news.ycombinator.com/item?id=48199741) | trollbridge | 2026-05-19 | Gemini 3.5 Flash | — | number, version |
| [48198530](https://news.ycombinator.com/item?id=48198530) | SwellJoe | 2026-05-19 | Gemini 3.5 Flash | — | number, version |
| [48184117](https://news.ycombinator.com/item?id=48184117) | mewse-hn | 2026-05-18 | I turned a $80 RK3562 Android tablet into a  | — | — |
| [48180355](https://news.ycombinator.com/item?id=48180355) | eli | 2026-05-18 | AI eats the world (Spring 26) [pdf] | — | link |
| [48180079](https://news.ycombinator.com/item?id=48180079) | nmfisher | 2026-05-18 | AI eats the world (Spring 26) [pdf] | — | link, number |
| [48177013](https://news.ycombinator.com/item?id=48177013) | raihansaputra | 2026-05-18 | I turned a $80 RK3562 Android tablet into a  | — | — |
| [48170765](https://news.ycombinator.com/item?id=48170765) | freakynit | 2026-05-17 | Ask HN: What LLM models are you using and wh | — | number, version |
| [48169365](https://news.ycombinator.com/item?id=48169365) | trollbridge | 2026-05-17 | Apple Silicon costs more than OpenRouter | — | number, version |
| [48166593](https://news.ycombinator.com/item?id=48166593) | KronisLV | 2026-05-17 | How to buy cheap Claude tokens in China | — | number, version |
| [48166219](https://news.ycombinator.com/item?id=48166219) | david_d8912 | 2026-05-17 | Ask HN: What LLM models are you using and wh | — | version |
| [48164981](https://news.ycombinator.com/item?id=48164981) | koito17 | 2026-05-17 | Zerostack – A Unix-inspired coding agent wri | — | version |
| [48150110](https://news.ycombinator.com/item?id=48150110) | karmakaze | 2026-05-15 | DeepSeek V4: The Open-Source Model Frontier  | — | link, version |
| [48149033](https://news.ycombinator.com/item?id=48149033) | Lucasoato | 2026-05-15 | DeepSeek V4: The Open-Source Model Frontier  | — | — |
| [48148326](https://news.ycombinator.com/item?id=48148326) | benjamintnorris | 2026-05-15 | UK sovereign LLM inference | — | number |
| [48147588](https://news.ycombinator.com/item?id=48147588) | noisy_boy | 2026-05-15 | Access to frontier AI will soon be limited b | — | — |
| [48147286](https://news.ycombinator.com/item?id=48147286) | wg0 | 2026-05-15 | A few words on DS4 | — | — |
| [48147238](https://news.ycombinator.com/item?id=48147238) | zozbot234 | 2026-05-15 | Access to frontier AI will soon be limited b | — | number |
| [48146845](https://news.ycombinator.com/item?id=48146845) | graemep | 2026-05-15 | UK sovereign LLM inference | — | — |
| [48146425](https://news.ycombinator.com/item?id=48146425) | benjamintnorris | 2026-05-15 | UK sovereign LLM inference | — | number, version |
| [48146121](https://news.ycombinator.com/item?id=48146121) | ageitgey | 2026-05-15 | Access to frontier AI will soon be limited b | opinion | number, version |
| [48145930](https://news.ycombinator.com/item?id=48145930) | DCKing | 2026-05-15 | Access to frontier AI will soon be limited b | comparison | link, version |
| [48145926](https://news.ycombinator.com/item?id=48145926) | pjerem | 2026-05-15 | Access to frontier AI will soon be limited b | — | — |
| [48145833](https://news.ycombinator.com/item?id=48145833) | pjerem | 2026-05-15 | Access to frontier AI will soon be limited b | usage_demo | link, number |
| [48145354](https://news.ycombinator.com/item?id=48145354) | cubefox | 2026-05-15 | Access to frontier AI will soon be limited b | news_roundup | link, version |
| [48145274](https://news.ycombinator.com/item?id=48145274) | ageitgey | 2026-05-15 | Access to frontier AI will soon be limited b | — | — |
| [48145156](https://news.ycombinator.com/item?id=48145156) | nl | 2026-05-15 | A few words on DS4 | — | link, version |
| [48144828](https://news.ycombinator.com/item?id=48144828) | trollbridge | 2026-05-15 | Access to frontier AI will soon be limited b | opinion | number, version |
| [48143910](https://news.ycombinator.com/item?id=48143910) | jofzar | 2026-05-15 | A few words on DS4 | — | — |
| [48143808](https://news.ycombinator.com/item?id=48143808) | zmmmmm | 2026-05-15 | A few words on DS4 | — | — |
| [48143239](https://news.ycombinator.com/item?id=48143239) | stavros | 2026-05-15 | A few words on DS4 | — | — |
| [48125020](https://news.ycombinator.com/item?id=48125020) | Matl | 2026-05-13 | The US is winning the AI race where it matte | — | — |
| [48090537](https://news.ycombinator.com/item?id=48090537) | pants2 | 2026-05-11 | Gemini API File Search is now multimodal | — | link, number |
| [48088239](https://news.ycombinator.com/item?id=48088239) | alasano | 2026-05-10 | Ask HN: What are you working on? (May 2026) | — | link, version |
| [48084469](https://news.ycombinator.com/item?id=48084469) | fatbrowndog | 2026-05-10 | Best AI coding plan alternative to Claude an | — | number |
| [48076645](https://news.ycombinator.com/item?id=48076645) | motbus3 | 2026-05-09 | Teaching Claude Why | — | — |
| [48075919](https://news.ycombinator.com/item?id=48075919) | jtbayly | 2026-05-09 | Teaching Claude Why | — | — |
| [48072812](https://news.ycombinator.com/item?id=48072812) | johndough | 2026-05-09 | A recent experience with ChatGPT 5.5 Pro | — | link |
| [48070245](https://news.ycombinator.com/item?id=48070245) | trollbridge | 2026-05-08 | DeepSeek V4 – almost on the frontier | — | number |
| [48064535](https://news.ycombinator.com/item?id=48064535) | lukewarm707 | 2026-05-08 | GPT-5.5 Price Increase: What It Costs | — | version |
| [48063775](https://news.ycombinator.com/item?id=48063775) | dw_arthur | 2026-05-08 | Higher usage limits for Claude and a compute | — | version |
| [48061305](https://news.ycombinator.com/item?id=48061305) | davidwritesbugs | 2026-05-08 | DeepSeek 4 Flash local inference engine for  | — | version |
| [48053247](https://news.ycombinator.com/item?id=48053247) | kingstnap | 2026-05-07 | Motherboard sales 'collapse' amid unpreceden | — | number |
| [48051322](https://news.ycombinator.com/item?id=48051322) | speu | 2026-05-07 | DeepSeek V4 Pro at 75% off until 31 May | — | version |
| [48044365](https://news.ycombinator.com/item?id=48044365) | mostafas | 2026-05-07 | Higher usage limits for Claude and a compute | — | link, number |
| [48044157](https://news.ycombinator.com/item?id=48044157) | flakiness | 2026-05-07 | DeepSeek V4 Pro at 75% off until 31 May | — | — |
| [48043895](https://news.ycombinator.com/item?id=48043895) | deevus | 2026-05-07 | DeepSeek V4 Pro at 75% off until 31 May | — | link |
| [48023822](https://news.ycombinator.com/item?id=48023822) | KronisLV | 2026-05-05 | I am worried about Bun | — | link, number, version, code |
| [48014597](https://news.ycombinator.com/item?id=48014597) | segmondy | 2026-05-04 | White House Considers Vetting A.I. Models Be | — | number, version |
| [48013784](https://news.ycombinator.com/item?id=48013784) | rapind | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | workflow | link, number, version, code |
| [48012870](https://news.ycombinator.com/item?id=48012870) | guluarte | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | workflow | link, version, code |
| [48008919](https://news.ycombinator.com/item?id=48008919) | sbinnee | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | version |
| [48008657](https://news.ycombinator.com/item?id=48008657) | BeetleB | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48008526](https://news.ycombinator.com/item?id=48008526) | dzink | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48008482](https://news.ycombinator.com/item?id=48008482) | rib3ye | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48008413](https://news.ycombinator.com/item?id=48008413) | ultrasandwich | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48007979](https://news.ycombinator.com/item?id=48007979) | connorwhitlock | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | number |
| [48007971](https://news.ycombinator.com/item?id=48007971) | tomw1808 | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48007645](https://news.ycombinator.com/item?id=48007645) | amunozo | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | version |
| [48007009](https://news.ycombinator.com/item?id=48007009) | TacticalCoder | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48006617](https://news.ycombinator.com/item?id=48006617) | lhl | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | version |
| [48006325](https://news.ycombinator.com/item?id=48006325) | zozbot234 | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | usage_demo | number, version |
| [48006241](https://news.ycombinator.com/item?id=48006241) | rsanek | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | deep_analysis | link, number |
| [48006112](https://news.ycombinator.com/item?id=48006112) | syntex | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48005694](https://news.ycombinator.com/item?id=48005694) | l5870uoo9y | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | deep_analysis | link, number |
| [48005373](https://news.ycombinator.com/item?id=48005373) | lukaslalinsky | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48005371](https://news.ycombinator.com/item?id=48005371) | zozbot234 | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48005144](https://news.ycombinator.com/item?id=48005144) | zozbot234 | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48004995](https://news.ycombinator.com/item?id=48004995) | adonese | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48004542](https://news.ycombinator.com/item?id=48004542) | sfewfweg | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48004484](https://news.ycombinator.com/item?id=48004484) | sowild_fun | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | usage_demo | number, version |
| [48004256](https://news.ycombinator.com/item?id=48004256) | spirit23 | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | link |
| [48004173](https://news.ycombinator.com/item?id=48004173) | energy123 | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | number |
| [48004139](https://news.ycombinator.com/item?id=48004139) | faangguyindia | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48004103](https://news.ycombinator.com/item?id=48004103) | maxdo | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | version |
| [48004086](https://news.ycombinator.com/item?id=48004086) | rapind | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | workflow | number, version, code |
| [48003630](https://news.ycombinator.com/item?id=48003630) | LeFantome | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | — | — |
| [48003077](https://news.ycombinator.com/item?id=48003077) | jubilanti | 2026-05-04 | DeepClaude – Claude Code agent loop with Dee | workflow | link, version, code |
| [48002640](https://news.ycombinator.com/item?id=48002640) | aftbit | 2026-05-03 | DeepClaude – Claude Code agent loop with Dee | workflow | link, version, code |
| [48000007](https://news.ycombinator.com/item?id=48000007) | jorvi | 2026-05-03 | For thirty years I programmed with Phish on, | — | number |
| [47999974](https://news.ycombinator.com/item?id=47999974) | FrasiertheLion | 2026-05-03 | DeepSeek V4 – almost on the frontier | — | version |
| [47999947](https://news.ycombinator.com/item?id=47999947) | FrasiertheLion | 2026-05-03 | DeepSeek V4 – almost on the frontier | — | link |
| [47999222](https://news.ycombinator.com/item?id=47999222) | alasano | 2026-05-03 | Specsmaxxing – On overcoming AI psychosis, a | — | link, version |
| [47996080](https://news.ycombinator.com/item?id=47996080) | zozbot234 | 2026-05-03 | Kimi K2.6 just beat Claude, GPT-5.5, and Gem | — | number |
| [47996041](https://news.ycombinator.com/item?id=47996041) | Topfi | 2026-05-03 | Show HN: State of the Art of Coding Models,  | — | link, number, version |
| [47995584](https://news.ycombinator.com/item?id=47995584) | nmfisher | 2026-05-03 | Kimi K2.6 just beat Claude, GPT-5.5, and Gem | — | — |
| [47995484](https://news.ycombinator.com/item?id=47995484) | adrian_b | 2026-05-03 | Kimi K2.6 just beat Claude, GPT-5.5, and Gem | — | number, version, code |
| [47995196](https://news.ycombinator.com/item?id=47995196) | linzhangrun | 2026-05-03 | DeepSeek V4 – almost on the frontier | — | version |
| [47994199](https://news.ycombinator.com/item?id=47994199) | pjerem | 2026-05-03 | Kimi K2.6 just beat Claude, GPT-5.5, and Gem | — | number, version |
| [47993684](https://news.ycombinator.com/item?id=47993684) | gertlabs | 2026-05-03 | Show HN: State of the Art of Coding Models,  | — | link, version |
| [47993596](https://news.ycombinator.com/item?id=47993596) | gertlabs | 2026-05-03 | Kimi K2.6 just beat Claude, GPT-5.5, and Gem | — | link, version |
| [47993031](https://news.ycombinator.com/item?id=47993031) | cheesecakegood | 2026-05-03 | Show HN: State of the Art of Coding Models,  | — | number, version |
| [47990809](https://news.ycombinator.com/item?id=47990809) | irthomasthomas | 2026-05-02 | DeepSeek V4—almost on the frontier | workflow | link, version, code |
| [47990148](https://news.ycombinator.com/item?id=47990148) | XCSme | 2026-05-02 | DeepSeek V4—almost on the frontier | benchmark | link, version |
| [47990145](https://news.ycombinator.com/item?id=47990145) | zozbot234 | 2026-05-02 | DeepSeek V4 – almost on the frontier | — | number |
| [47989937](https://news.ycombinator.com/item?id=47989937) | gpugreg | 2026-05-02 | DeepSeek V4 – almost on the frontier | deep_analysis | link, number |
| [47988728](https://news.ycombinator.com/item?id=47988728) | rurban | 2026-05-02 | DeepSeek V4 – almost on the frontier | usage_demo | number, version |
| [47988232](https://news.ycombinator.com/item?id=47988232) | scrollop | 2026-05-02 | DeepSeek V4 – almost on the frontier | benchmark | link, number, version |
| [47988227](https://news.ycombinator.com/item?id=47988227) | kamikazechaser | 2026-05-02 | DeepSeek V4 – almost on the frontier | — | — |
| [47987685](https://news.ycombinator.com/item?id=47987685) | gertlabs | 2026-05-02 | DeepSeek V4 – almost on the frontier | benchmark | link, version |
| [47987628](https://news.ycombinator.com/item?id=47987628) | ollin | 2026-05-02 | Chinese AI models are ~8 months behind and f | — | link, number, version, code |
| [47987379](https://news.ycombinator.com/item?id=47987379) | TacticalCoder | 2026-05-02 | DeepSeek V4–almost on the frontier, a fracti | — | number |
| [47986188](https://news.ycombinator.com/item?id=47986188) | johndough | 2026-05-02 | DeepSeek V4 – almost on the frontier | — | version |
| [47986125](https://news.ycombinator.com/item?id=47986125) | segmondy | 2026-05-02 | DeepSeek V4 – almost on the frontier | deep_analysis | link, number, version |
| [47985978](https://news.ycombinator.com/item?id=47985978) | MintsJohn | 2026-05-02 | DeepSeek V4–almost on the frontier, a fracti | — | version |
| [47985529](https://news.ycombinator.com/item?id=47985529) | swiftcoder | 2026-05-02 | DeepSeek V4–almost on the frontier, a fracti | — | version |
| [47985451](https://news.ycombinator.com/item?id=47985451) | FrasiertheLion | 2026-05-02 | DeepSeek V4 – almost on the frontier | — | version |
| [47985381](https://news.ycombinator.com/item?id=47985381) | cheshire_cat | 2026-05-02 | DeepSeek V4 – almost on the frontier | deep_analysis | link, number, version |
| [47985237](https://news.ycombinator.com/item?id=47985237) | zozbot234 | 2026-05-02 | DeepSeek V4—almost on the frontier | — | number |
| [47984886](https://news.ycombinator.com/item?id=47984886) | dbeley | 2026-05-02 | DeepSeek V4 – almost on the frontier | — | — |
| [47984051](https://news.ycombinator.com/item?id=47984051) | holysantamaria | 2026-05-02 | DeepSeek V4 – almost on the frontier | — | number |
| [47983805](https://news.ycombinator.com/item?id=47983805) | myaccountonhn | 2026-05-02 | DeepSeek V4–almost on the frontier, a fracti | — | version |
| [47982523](https://news.ycombinator.com/item?id=47982523) | wg0 | 2026-05-02 | DeepSeek V4 – almost on the frontier | usage_demo | number, version |
| [47979437](https://news.ycombinator.com/item?id=47979437) | dyauspitr | 2026-05-01 | After dissing Anthropic for limiting Mythos, | — | — |
| [47976740](https://news.ycombinator.com/item?id=47976740) | culi | 2026-05-01 | Grok 4.3 | — | link, number, version, code |
| [47965617](https://news.ycombinator.com/item?id=47965617) | tappio | 2026-04-30 | Claude Code refuses requests or charges extr | — | version |
| [47964973](https://news.ycombinator.com/item?id=47964973) | sergiotapia | 2026-04-30 | Claude Code refuses requests or charges extr | — | version |
| [47949547](https://news.ycombinator.com/item?id=47949547) | wmertens | 2026-04-29 | Xiaomi MiMo-v2.5-Pro Open-Sourced: 1T Parame | — | — |
| [47943785](https://news.ycombinator.com/item?id=47943785) | guiguan | 2026-04-29 | A 3D Flappy Bird side-scroller game built wi | — | link |
| [47935600](https://news.ycombinator.com/item?id=47935600) | paoliniluis | 2026-04-28 | Xiaomi MiMo-v2.5-Pro Open-Sourced: 1T Parame | — | link, version |
| [47931289](https://news.ycombinator.com/item?id=47931289) | hu3 | 2026-04-28 | GitHub Copilot is moving to usage-based bill | — | version |
| [47928506](https://news.ycombinator.com/item?id=47928506) | zozbot234 | 2026-04-27 | Microsoft and OpenAI end their exclusive and | — | number |
| [47928271](https://news.ycombinator.com/item?id=47928271) | aucisson_masque | 2026-04-27 | Microsoft and OpenAI end their exclusive and | — | number |
| [47919987](https://news.ycombinator.com/item?id=47919987) | LatencyKills | 2026-04-27 | DeepSeek Slashes Fees for New AI Model | — | link, number |
| [47915128](https://news.ycombinator.com/item?id=47915128) | monlockandkey | 2026-04-26 | SWE-bench Verified no longer measures fronti | — | version |
| [47901792](https://news.ycombinator.com/item?id=47901792) | Sembiance | 2026-04-25 | OpenAI releases GPT-5.5 and GPT-5.5 Pro in t | — | — |
| [47901068](https://news.ycombinator.com/item?id=47901068) | XCSme | 2026-04-25 | DeepSeek v4 | benchmark | link, version |
| [47894311](https://news.ycombinator.com/item?id=47894311) | zozbot234 | 2026-04-24 | I cancelled Claude: Token issues, declining  | — | number |
| [47892830](https://news.ycombinator.com/item?id=47892830) | nabakin | 2026-04-24 | DeepSeek v4 | — | link |
| [47891553](https://news.ycombinator.com/item?id=47891553) | maxloh | 2026-04-24 | DeepSeek v4 | announcement | link, version |
| [47889569](https://news.ycombinator.com/item?id=47889569) | Iolaum | 2026-04-24 | America must guard against China's own Mytho | — | — |
| [47889301](https://news.ycombinator.com/item?id=47889301) | cmitsakis | 2026-04-24 | DeepSeek v4 | benchmark | number, version |
| [47888887](https://news.ycombinator.com/item?id=47888887) | XCSme | 2026-04-24 | DeepSeek v4 | benchmark | link, version |
| [47888227](https://news.ycombinator.com/item?id=47888227) | nsoonhui | 2026-04-24 | DeepSeek v4 | deep_analysis | link, code |
| [47887846](https://news.ycombinator.com/item?id=47887846) | ozgune | 2026-04-24 | DeepSeek v4 | — | version |
| [47887485](https://news.ycombinator.com/item?id=47887485) | cubefox | 2026-04-24 | DeepSeek v4 | deep_analysis | link, number, version |
| [47887146](https://news.ycombinator.com/item?id=47887146) | yorwba | 2026-04-24 | DeepSeek v4 | — | link |
| [47886696](https://news.ycombinator.com/item?id=47886696) | hodgehog11 | 2026-04-24 | DeepSeek v4 | — | version |
| [47886687](https://news.ycombinator.com/item?id=47886687) | creamyhorror | 2026-04-24 | DeepSeek v4 | — | version |
| [47886609](https://news.ycombinator.com/item?id=47886609) | sixhobbits | 2026-04-24 | DeepSeek v4 | announcement | link, number, version |
| [47886101](https://news.ycombinator.com/item?id=47886101) | mohsen1 | 2026-04-24 | DeepSeek v4 | — | link |
| [47885796](https://news.ycombinator.com/item?id=47885796) | BoorishBears | 2026-04-24 | DeepSeek v4 | announcement | link, version |
| [47885714](https://news.ycombinator.com/item?id=47885714) | 77ko | 2026-04-24 | DeepSeek v4 | — | link |
| [47885654](https://news.ycombinator.com/item?id=47885654) | simonw | 2026-04-24 | DeepSeek v4 | deep_analysis | number, version |
| [47885649](https://news.ycombinator.com/item?id=47885649) | esafak | 2026-04-24 | DeepSeek v4 | announcement | link, version |
| [47885597](https://news.ycombinator.com/item?id=47885597) | simonw | 2026-04-24 | DeepSeek v4 | — | link |
| [47885574](https://news.ycombinator.com/item?id=47885574) | simonw | 2026-04-24 | DeepSeek v4 | usage_demo | link, version |
| [47885426](https://news.ycombinator.com/item?id=47885426) | frozenseven | 2026-04-24 | DeepSeek v4 | — | link |
| [47885355](https://news.ycombinator.com/item?id=47885355) | rvz | 2026-04-24 | DeepSeek v4 | — | link |
| [47885275](https://news.ycombinator.com/item?id=47885275) | creamyhorror | 2026-04-24 | DeepSeek-V4 Technical Report [pdf] | — | version |
| [47885263](https://news.ycombinator.com/item?id=47885263) | nthypes | 2026-04-24 | DeepSeek v4 | opinion | link, version |
| [47885255](https://news.ycombinator.com/item?id=47885255) | seanobannon | 2026-04-24 | DeepSeek v4 | — | link |
| [47885254](https://news.ycombinator.com/item?id=47885254) | talim | 2026-04-24 | DeepSeek v4 | — | link |

## 9. Method and containment, and what these numbers do not mean

### 9.1 Containment, and the ruling that does not exist

- The fetcher imports nothing from `collect/` or `judge/`, opens no database connection, and writes only to `var/hackernews/` (gitignored) and this report. The containment is the same as the arXiv path's and it is deliberate: an unverified scrape must not be able to reach `document`, `claim` or `cell`.
- **Consequence, stated rather than worked around:** because this does not route through `harvester_for_source()`, the `assert_terms_reviewed()` gate did not run. `contract/sources.yaml` carries no `terms_ruling` for Algolia or Hacker News at all — not a failed one, an absent one. **This data is therefore publishable on the Articles page and is not admissible to the pipeline.** Feeding it to `collect/` requires writing that ruling first, with a basis and an expiry, the way `reddit-via-rapidapi` was written.
- The API is public and unauthenticated. No credentials were created or used, so no key is at risk in this path.

### 9.2 The sample is retrieval-shaped, not representative

- These are the records **our five keyword surfaces and two ranking endpoints returned**, deduped. A different keyword set returns a different corpus. Nothing here supports a claim about what HN as a whole thinks.
- `/search` ranks by relevance and `/search_by_date` by recency. Both were run and unioned precisely because either alone is a biased slice, but the union is still a slice.
- Thread-following is **triggered by a match**, so a thread with substantial discussion that never spells the model's name is absent. This is a known and material gap: inside a thread already titled about the model, commenters write *V4 Pro*, *DS4* or *it*, and none of those match. The per-thread `matched` against `comments` columns in §7 make the size of the gap visible rather than hiding it — in the DeepClaude thread it is 30 of 281.

### 9.3 The figures in these comments are theirs, not ours

- Every price, token count, benchmark score and throughput number quoted in §6 is **the commenter's own claim, reproduced**. None has been re-run or verified here. The artifact column says a claim is *checkable*; it does not say it is *checked*.
- Several are contradicted inside the same corpus, and the contradictions are kept rather than resolved — one commenter measures Pro as the fastest of 21 models, another measures the fastest providers at ~50tps and slower than Opus. Both are in §6.

### 9.4 Points and comment counts are read at fetch time

- HN scores drift. Every figure is as of the fetch timestamp in §1, not as of posting, and a re-run will differ.
- `fetched` is below `comments` on several threads. Algolia does not return deleted or dead comments, and on the largest threads its 1000-record cap applies to the comment listing too. Both are retrieval properties, not findings about the discussion.

### 9.5 Reproducing this

```
py -3 scripts/fetch_hackernews_articles.py     # -> var/hackernews/hn-*.json
py -3 scripts/build_hackernews_report.py      # -> this file
py -3 articles/build_data.py                  # -> web/src/data/*.json
```

The pull is timestamped and kept, so the report and the page JSON can both be rebuilt from it without re-fetching. Hand labels live in `LABELS` in `scripts/build_hackernews_report.py`.
