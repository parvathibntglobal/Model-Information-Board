# DeepSeek V4 Pro — Reddit data pull

A sweep of Reddit for substantive discussion of the language model **DeepSeek V4 Pro** — deep technical analysis, benchmarks, usage demonstrations, workflow write-ups, reasoned comparisons and tutorials — with announcements, news digests and promotional spam identified and separated rather than discarded.

> **One-off research pull, held entirely in a scratch directory.** Nothing was written to any project database, index, or configured keyword list. The DB-writing sweep machinery was deliberately bypassed. See §11 *Method*.

## 1. Run metadata

| Field | Value |
|---|---|
| Report generated | 2026-09-01T06:36:39+00:00 |
| Sweep window | 2026-09-01T10:33Z (first search call) → 2026-09-01 (profile enrichment) |
| Route | `collect/adapters/reddit.py` → `RedditHarvester`, over RapidAPI (`reddit34.p.rapidapi.com`) |
| Endpoints used | `/getSearchPosts`, `/getPostsBySubreddit`, `/getPostComments`, `/getProfile` |
| Auth | `RAPIDAPI_KEY` from `.env`. Official Reddit API credentials (`REDDIT_CLIENT_ID`/`SECRET`) are **blank** in this repo and were not used. No new credentials were created. |
| Terms gate | `assert_terms_reviewed()` via `harvester_for_source()`, ruling `reddit-via-rapidapi` — **PASSED** (`ENVIRONMENT=development`, so the observed use basis is `internal-development-only`) |
| Total API calls | 1833 |
| Quota remaining after run | 997772 (gateway-reported limit 1,000,000; 1 unit per request) |
| Rate limit applied | 25 requests/minute (`SEARCH_PER_MINUTE`) |
| Search queries | 87 |
| Subreddit listings | 40 |
| Comment threads fetched | 1029 (48,759 comments) — **fetched, then excluded from this report by instruction.** Still on disk in `comments.jsonl`; re-includable with `INCLUDE_COMMENTS=1` and no re-fetching |
| Scope of this report | **Posts only** (self-posts, link posts and crossposts) |
| Author profiles fetched | 505 |
| **Records after dedup** | **1601** |
| Raw payloads retained | content-addressed in the scratch rawstore (`out/../rawstore/`), reprocessable without re-fetching |

## 2. What the keywords returned, and how they overlap

### 2.1 Three of your four seed keywords are the same string

Under punctuation normalisation — lowercase, every non-alphanumeric run removed — the four seeds collapse:

| # | Seed keyword | Normalised | Independent? |
|---|---|---|---|
| 1 | `Deepseek V4 pro` | `deepseekv4pro` | yes |
| 2 | `deepseek-v4-pro` | `deepseekv4pro` | **no — identical to #1** |
| 3 | `deepseekv4pro` | `deepseekv4pro` | **no — identical to #1** |
| 4 | `deepseek-v4-pro-0813` | `deepseekv4pro0813` | yes |

So **the literal match test is one test, not four**: *does the normalised text contain* `deepseekv4pro`. Keyword #4 normalises to `deepseekv4pro0813`, which *contains* that string as a prefix — a narrowing of the same test, not an independent one. Reporting these as four independent searches would overstate keyword coverage roughly fourfold.

**They are not the same *query*, however.** The search index tokenises, so the four spellings retrieve very different result sets despite testing identically:

| Seed keyword | Sort | Returned | New | Literal in returned | Truncated by |
|---|---|---|---|---|---|
| `Deepseek V4 pro` | RELEVANCE | 75 | 75 | 36/75 (48%) | result-ceiling |
| `Deepseek V4 pro` | NEW | 75 | 75 | 6/75 (8%) | result-ceiling |
| `Deepseek V4 pro` | TOP | 75 | 72 | 3/75 (4%) | result-ceiling |
| `deepseek-v4-pro` | RELEVANCE | 75 | 34 | 57/75 (76%) | result-ceiling |
| `deepseek-v4-pro` | NEW | 75 | 58 | 30/75 (40%) | result-ceiling |
| `deepseek-v4-pro` | TOP | 75 | 39 | 21/75 (28%) | result-ceiling |
| `deepseekv4pro` | RELEVANCE | 18 | 18 | 14/18 (77%) | — |
| `deepseekv4pro` | NEW | 14 | 0 | 14/14 (100%) | — |
| `deepseekv4pro` | TOP | 14 | 0 | 14/14 (100%) | — |
| `deepseek-v4-pro-0813` | RELEVANCE | 75 | 65 | 69/75 (92%) | result-ceiling |
| `deepseek-v4-pro-0813` | NEW | 75 | 41 | 34/75 (45%) | result-ceiling |
| `deepseek-v4-pro-0813` | TOP | 75 | 16 | 46/75 (61%) | result-ceiling |

The run-together spelling `deepseekv4pro` returns only 14–18 results but at ~100% literal precision — it is a rare single token, so relevance ranking cannot pad it. The spaced form hits the 75-result ceiling at 36% precision because **this search API has no phrase operator and degrades to OR over the tokens** (measured and documented in `collect/adapters/reddit.py`: `"rolled back"` returns posts containing *back* without *rolled*). That is the single biggest reason the §11 re-filter on actual text was necessary rather than optional.

### 2.2 How people actually spell it

Surface spellings across the 727 literal-matching records — 1796 mentions in 54 distinct spellings:

| Spelling as written | Mentions |
|---|---|
| `DeepSeek V4 Pro` | 872 |
| `deepseek-v4-pro` | 143 |
| `Deepseek V4 Pro` | 137 |
| `DeepSeek V4 Pro 0813` | 133 |
| `DeepSeek-V4-Pro` | 96 |
| `deepseek v4 pro` | 77 |
| `DeepSeek v4 Pro` | 59 |
| `Deepseek v4 pro` | 39 |
| `DeepSeek-V4-Pro-0813` | 38 |
| `Deepseek v4 Pro` | 21 |
| `deepseek-v4-pro-0813` | 21 |
| `DeepSeek v4 pro` | 19 |
| `DeepSeek V4-Pro` | 15 |
| `Deepseek V4 pro` | 13 |
| `DeepSeek v4 Pro 0813` | 12 |
| `deepseek_v4_pro_0813` | 11 |
| `deepseekv4pro` | 9 |
| `DeepSeek V4 pro` | 7 |
| `Deepseek-v4-pro` | 6 |
| `deepseek_v4_pro` | 5 |
| `Deepseek v4 Pro 0813` | 5 |
| `DeepSeek v4-pro` | 5 |
| `DeepSeek V4 PRO` | 4 |
| `Deepseek v4 pro 0813` | 4 |
| `DeepSeekV4Pro` | 3 |
| *…29 further spellings* | 42 |

### 2.3 Query overlap

How many distinct queries retrieved each record — the measure of how much the query set overlaps:

| Retrieved by N queries | Records |
|---|---|
| 1 | 768 |
| 2 | 304 |
| 3 | 184 |
| 4 | 95 |
| 5 | 63 |
| 6 | 31 |
| 7 | 43 |
| 8 | 18 |
| 9 | 19 |
| 10 | 10 |
| 11 | 10 |
| 12 | 6 |
| 13 | 11 |
| 14 | 7 |
| 15 | 4 |
| 16 | 9 |
| 17 | 2 |
| 18 | 4 |
| 19 | 2 |
| 20 | 1 |
| 21 | 4 |
| 22 | 2 |
| 25 | 1 |
| 26 | 1 |
| 31 | 1 |
| 37 | 1 |

## 3. Headline numbers

| Measure | Count |
|---|---|
| **Records collected and deduplicated** | **1601** |
| — literal keyword match on normalised text | **727** |
| — loose (a query returned it; no literal match in its own text) | 874 |
| Posts | 1568 (literal: 708) |
| Crossposts | 33 (literal: 19) |
| Comments | **excluded by instruction** — 48,759 were fetched across 1029 threads and 692 of them matched literally; none are counted anywhere in this report |
| Distinct subreddits (literal) | 149 |
| Distinct authors, by stable `t2_` id (literal) | 530 |
| Near-duplicate bodies detected | 56 |
| Deleted author or body | 0 — **a real zero, see §3.1** |
| Moderator-removed | 0 — **a real zero, see §3.1** |
| Locked | 43 |
| Edited | 318 |
| **Hand-read and labelled** | **150** |
| External links shared | 4535 |

### 3.1 The deleted/removed zero is a property of the retrieval path, not a finding about the corpus

Two rows above are zero, and a zero that a reader might take as *“nothing was removed”* has to be explained rather than shipped:

| Field | Posts (n=1601) | Comments fetched (n=48,759) |
|---|---|---|
| `author == "[deleted]"` | **0** | 441 |
| body `[removed]` (moderator) | **0** | 820 |
| `removed_by_category` | **0** (all NULL) | — |
| `removed_by` / `banned_by` | **0** (all NULL) | — |
| `locked` | 43 | — |

**All 1,601 post payloads carry NULL in every removal field, and not one has a deleted author.** That is not plausible as a fact about Reddit; it is what `/getSearchPosts` and `/getPostsBySubreddit` return — live posts only. Removed and deleted posts are filtered out upstream of us and are therefore **invisible to this sweep**, not absent from the platform.

The proof sits in the same run: comment trees fetched for *these very posts* contain 441 author-deleted and 820 moderator-removed bodies. The field works and the parser reads it; the post endpoints just never emit a removed post. So the deletion signal exists in the data that was gathered and **cannot be recovered from the posts-only view this report presents**.

`locked` (43 posts) is the one moderation signal that does survive post retrieval, which is why it is now listed.

## 4. Content-type breakdown, with the subject/mention split

Every row below is a **hand-applied label** over the 150 highest-scoring literal records. `subject` means DeepSeek V4 Pro is what the record is about; `mention` means it appears as one comparison datapoint inside a record about something else.

| Content type | Total | Subject | Mention |
|---|---|---|---|
| deep analysis | 17 | 7 | 10 |
| benchmark | 29 | 12 | 17 |
| comparison | 14 | 7 | 7 |
| usage demo | 14 | 5 | 9 |
| workflow/setup | 17 | 2 | 15 |
| tutorial | 7 | 2 | 5 |
| announcement | 6 | 2 | 4 |
| promo | 19 | 8 | 11 |
| news roundup | 10 | 0 | 10 |
| opinion | 9 | 2 | 7 |
| question | 8 | 4 | 4 |
| **All labelled** | **150** | **51** | **99** |

**Substance vs noise, within the hand-read set.** 84 of 150 are the content types you asked for (deep analysis, benchmark, usage demo, workflow/setup, tutorial). 14 are comparisons, 9 opinion, 8 questions, and 35 are announcement / promo / news-roundup noise.

> **Coverage caveat.** 150 of 727 literal records carry a type label. The remaining 577 keep their substance score and rank but **have no type label and were not read**. This is the top of the ranking, not a census of it.

## 5. Release timeline, reconstructed from the posts themselves

Built by extracting version strings from the corpus and taking the earliest post mentioning each. **`first_seen` is when Reddit started using a name — a lower bound on a release date, not the release date.** No external source was consulted.

| Version string | First seen | Last seen | Records | Distinct authors | Earliest post |
|---|---|---|---|---|---|
| **DeepSeek V4** | 2026-02-16 | 2026-09-01 | 2972 | 565 | [r/u_rsrini7](https://www.reddit.com/r/u_rsrini7/comments/1r621ek/weekly_ai_tech_updates_february_15_2026/) |
| **DeepSeek V4 Pro** | 2026-04-04 | 2026-09-01 | 1635 | 500 | [r/CrofAI](https://www.reddit.com/r/CrofAI/comments/1sc3nsw/crofai_affordable_multimodel_ai_access_with_cheap/) |
| **DeepSeek V4.1** | 2026-05-16 | 2026-07-16 | 3 | 3 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1tex1gw/how_does_deepseek_v4_compare_to_other_chinese/) |
| **DeepSeek V4 0731** | 2026-07-31 | 2026-08-20 | 4 | 3 | [r/codex](https://www.reddit.com/r/codex/comments/1vbla2z/what_the_hell_is_going_on/) |
| **DeepSeek V4 Pro 0813** | 2026-08-12 | 2026-09-01 | 241 | 80 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vmh9k8/deepseekv4pro0813_added_to_the_pricing_page/) |
| **DeepSeek V4 0813** | 2026-08-12 | 2026-08-30 | 5 | 4 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vmkbpq/does_deepseek_pro_v4_0813_have_vision_capabilities/) |

*5 further version strings appeared in fewer than 3 records each and are omitted as likely typos or one-offs; they are in `timeline_full.json`.*

## 6. The articles, grouped by content type

Substantive types first, each entry carrying permalink, subreddit, author, stable author id, score, comment count and an excerpt. **Within each type, records where DeepSeek V4 Pro is the actual subject come first**, then the mentions; each block is ordered by substance score.

### 6.1 Deep Analysis  — 17 records (7 subject, 10 mention)

**1. Considering that no one wants to calculate electricity and water consumption for new AI models, here is the calculation for Deepseek v4 pro**  
[https://www.reddit.com/r/aiwars/comments/1tuvr0s/considering_that_no_one_wants_to_calculate/](https://www.reddit.com/r/aiwars/comments/1tuvr0s/considering_that_no_one_wants_to_calculate/)  
*r/aiwars · u/Questioner8297 · `t2_1lg0cmd521` · score 19 · 31 comments · 2026-06-02 · substance 26.0 · subject*  
> **Why this label:** Original electricity and water estimate for 3.5M V4 Pro tokens, worked from published throughput-per-MW figures with the assumptions stated. Titled, no rival models.  

> This benchmark give 3.5 million tokens average for difficult task for deepseek v 4 pro [https://artificialanalysis.ai/agents/coding-agents](https://artificialanalysis.ai/agents/coding-agents) 1. Electricity calculation for 3.5 million tokens I estimated the electricity used to run 3.5 million tokens on DeepSeek V4-Pro in a data center. DeepSeek says V4-Pro has 1.6T total parameters and 49B active parameters, and supports 1M context. (DeepSeek API docs: [https://api-docs.deepseek.com/news/news260424](https://api-docs.deepseek.com/news/news260424)) For the energy estimate, I used SemiAnalysis / InferenceX benchmark data for DeepSeek V4-Pro 1.6T on NVIDIA B200, where throughput is listed as abo…

**2. The exact KV cache usage of DeepSeek V4**  
[https://www.reddit.com/r/LocalLLaMA/comments/1svzlog/the_exact_kv_cache_usage_of_deepseek_v4/](https://www.reddit.com/r/LocalLLaMA/comments/1svzlog/the_exact_kv_cache_usage_of_deepseek_v4/)  
*r/LocalLLaMA · u/Ok_Warning2146 · `t2_s6sfw4yy` · score 136 · 60 comments · 2026-04-26 · substance 22.6 · subject*  
> **Why this label:** Hand-recomputes V4's KV-cache usage from the paper and vllm's breakdown, and corrects the claimed saving (7.879x not 9.5x; 12.5x not 13.7x for Flash). V4 Pro has its own row. Genuinely original technical work.  

> Figure 1 of DSV4 paper seems to imply that DSV3.2 uses \~50GB at 1m context and DSV4 uses \~5GB: [https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/DeepSeek\_V4.pdf](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/DeepSeek_V4.pdf) \*\*\*Numbers updated with the KV cache breakdown from vllm\*\*\* [https://vllm.ai/blog/deepseek-v4](https://vllm.ai/blog/deepseek-v4) From my own calculations, the correct FP16 KV cache at 1m context should be: \|Model\|Params\|128k\|160k\|1m\|KV%\| \|:-\|:-\|:-\|:-\|:-\|:-\| \|V3/3.1\|671B\|8.58GiB\|10.72GiB\|68.63GiB\|5.11%\| \|V3.2\|671B\|10.48GiB\|13.11GiB\|83.88GiB\|6.25%\| \|V4 Flash\|284B\|0.84GiB\|1.05GiB\|6.72GiB\|1.18%\| \|V4 Pro\|1600B\|1.20GiB\|1.50GiB\|9.62GiB\|0.3%\| …

**3. OpenCode Go plan does NOT include the 75% discounted DeepSeek V4 Pro**  
[https://www.reddit.com/r/opencodeCLI/comments/1tbr2kr/opencode_go_plan_does_not_include_the_75/](https://www.reddit.com/r/opencodeCLI/comments/1tbr2kr/opencode_go_plan_does_not_include_the_75/)  
*r/opencodeCLI · u/EmoLotional · `t2_etbw24zd` · score 0 · 22 comments · 2026-05-13 · substance 22.0 · subject*  
> **Why this label:** Tested directly and via OpenCode Go and found the 75% V4 Pro discount is not passed through; works the numbers and states when each route wins. Titled.  

> Hey everyone, I just had to inform you, there is a lot of misconception and false information roaming around about this especially in comments of this subreddit, I tested both direct AND opencode go, it seems like the discount is not applied by the provider, so in some sense, it was not worth it going for opencode go only for that specific leading model, that said, it was the first time deal so it was only like 5 bucks compared to the normal rate of 10 bucks or so, however I crunched the numbers and the cost per tokens is significantly higher if choosing the opencode go route, obviously with the limits into consideration it is not worth it. In conclusion the opencode go deal is lucrative onl…

**4. Beware of Command Code's misleading marketing**  
[https://www.reddit.com/r/DeepSeek/comments/1viwwpx/beware_of_command_codes_misleading_marketing/](https://www.reddit.com/r/DeepSeek/comments/1viwwpx/beware_of_command_codes_misleading_marketing/)  
*r/DeepSeek · u/RaisinImpressive3749 · `t2_z955k7b66` · score 134 · 84 comments · 2026-08-08 · substance 22.0 · subject*  
> **Why this label:** Documents with captured screenshots that Command Code's '$40'/'$80' V4 Pro headline is DeepSeek's own price cut relabelled, checking the vendor's numbers against DeepSeek's published rates. Pro pricing is the whole argument.  

> **TL;DR:** the $1 Go plan gets you $10 of DeepSeek V4 Pro credit, not the "$40" the headline claims. The $10 GOAT plan gets you a $20 DeepSeek V4 Pro allowance, not "$80". The "4x deal" is DeepSeek's own price cut, relabeled. The value itself is fine. The misleading marketing around it isn't. This is their pricing page, right now. Go costs $1/month and comes with "$10 in credits included" and "up to $40 usage with deals". GOAT costs $10/month with "$70 in credits included" and "$80 on DeepSeek V4 Pro with deals". [Source: https:\/\/commandcode.ai\/pricing \(captured 2026-08-08\)](https://preview.redd.it/7ca9t119p5ih1.png?width=1772&amp;format=png&amp;auto=webp&amp;s=e47f9adbb1d1c2512afadb4e9…

**5. Why OpenCode Go's DeepSeek V4 Pro is ~33% cheaper than the official API (at full usage, even after the 75% price cut)**  
[https://www.reddit.com/r/opencodeCLI/comments/1tqx9u1/why_opencode_gos_deepseek_v4_pro_is_33_cheaper/](https://www.reddit.com/r/opencodeCLI/comments/1tqx9u1/why_opencode_gos_deepseek_v4_pro_is_33_cheaper/)  
*r/opencodeCLI · u/OptionOk3805 · `t2_exg5if9lt` · score 86 · 44 comments · 2026-05-29 · substance 21.8 · subject*  
> **Why this label:** Works out that OpenCode Go's V4 Pro is ~33.4% cheaper than the official API only if the $60 cap is fully used, and states the caveat plainly. Titled.  

> I asked DeepSeek V4 Flash to write a Python script to run the numbers on OpenCode Go's DeepSeek V4 Pro pricing vs the official DeepSeek API. Then I had Opus 4.6 verify them. Here's the breakdown: Official DeepSeek V4 Pro API (permanent post-75%-discount prices): Output: $0.87 / 1M tokens Input: $0.435 / 1M tokens (cache miss) Cached: $0.003625 / 1M tokens (cache hit) OpenCode Go — $10/month subscription, $60 usage cap, ~17k requests. At first glance, Go's internal usage-value prices look worse ($3.475/1M output). But that's not what you actually pay — those are the "accounting" numbers for the $60 cap. The key: you pay $10 but get $60 of usage value. So your real cost is (10/60) = 1/6 of the…

**6. Test of prices of DeepSeek in OpenCode Go and API in deepseek.com**  
[https://www.reddit.com/r/opencodeCLI/comments/1tril88/test_of_prices_of_deepseek_in_opencode_go_and_api/](https://www.reddit.com/r/opencodeCLI/comments/1tril88/test_of_prices_of_deepseek_in_opencode_go_and_api/)  
*r/opencodeCLI · u/CriteriumA · `t2_2d82q2o51k` · score 74 · 39 comments · 2026-05-29 · substance 20.8 · subject*  
> **Why this label:** Reconciles charged amounts against published per-token rates call by call for V4 Pro and Flash, and establishes that the 75% rate applied from launch. Pro pricing is the subject.  

> I have tested several models: [https://www.reddit.com/r/opencodeCLI/comments/1trgcw9/homemade\_and\_specific\_comparison\_of\_opencode\_go/](https://www.reddit.com/r/opencodeCLI/comments/1trgcw9/homemade_and_specific_comparison_of_opencode_go/) I thought that since I had structured usage data for DeepSeek V4 Pro and Flash, I could compare the prices in OpenCode Go with the prices of the DeepSeek API. [https://opencode.ai/docs/go](https://opencode.ai/docs/go) [https://api-docs.deepseek.com/quick\_start/pricing/](https://api-docs.deepseek.com/quick_start/pricing/) This confirms what many others have shared on this topic. **The price at Opencode Go does not include an API discount.** Hopefully …

**7. I repriced my real Claude Code Max 20x usage against DeepSeek V4 Pro API — the new DeepSeek pricing completely changes the comparison**  
[https://www.reddit.com/r/DeepSeek/comments/1vtv0jz/i_repriced_my_real_claude_code_max_20x_usage/](https://www.reddit.com/r/DeepSeek/comments/1vtv0jz/i_repriced_my_real_claude_code_max_20x_usage/)  
*r/DeepSeek · u/Maamriya · `t2_30unn8r8` · score 74 · 86 comments · 2026-08-20 · substance 20.0 · subject*  
> **Why this label:** Reprices 127 days of the author's real Claude Code Max token mix against V4 Pro API rates, before and after the August price change, and argues for $/task over $/1M tokens. Titled.  

> https://preview.redd.it/pbopt14falkh1.png?width=1254&amp;format=png&amp;auto=webp&amp;s=ddb35beedf8015af6e65a943da96c2773d2e1c8d keep seeing AI coding models compared by their **$/1M token price**, so I wanted to look at this differently using my actual Claude Code usage. I use Claude Code heavily for large software projects and I'm on **Claude Max 20x at $200/month**. Anthropic currently includes Claude Code with that subscription. I pulled my Claude Code stats covering **127 days** and normalized them to 30 days. My 30-day average comes out to roughly: * **16.37M normal input tokens** * **7.63B cache-read tokens** * **259.84M cache-write tokens** * **46.39M output tokens** * **\~7.95B tota…

**8. Open WebUI is completely broken now**  
[https://www.reddit.com/r/OpenWebUI/comments/1tcslos/open_webui_is_completely_broken_now/](https://www.reddit.com/r/OpenWebUI/comments/1tcslos/open_webui_is_completely_broken_now/)  
*r/OpenWebUI · u/eteitaxiv · `t2_f137l` · score 32 · 27 comments · 2026-05-14 · substance 29.6 · mention*  
> **Why this label:** Root-cause diagnosis of an Open WebUI bug dropping reasoning_content; DeepSeek is one of the affected providers, named once at 64%.  

> After 0.9, my Open WebUI got fully broken. Title generation works 20% of the time. Generation stops after tool calls, making it unusable. I tried starting from nothing with backups. I tried different providers. Nothing is working. It is on a Raspberry Pi 5. Are there any sharing this problems? If not, I will start from nothing, importing nothing and creating all the agents and skills and everything. EDIT: I can't actually believe it, but I wrote the problem to Hermes Agent in the same system, and it fixed it by a patch like this: - ./patches/middleware.py:/app/backend/open_webui/utils/middleware.py:ro It seems the problem was this according to it: OK, here's the full diagnosis and fix: == RO…

**9. The Definitive Qwen3.8-27B Deep Dive**  
[https://www.reddit.com/r/BriefDelights/comments/1vkvfwu/the_definitive_qwen3827b_deep_dive/](https://www.reddit.com/r/BriefDelights/comments/1vkvfwu/the_definitive_qwen3827b_deep_dive/)  
*r/BriefDelights · u/Disrupt-Linus · `t2_4cyagmev` · score 1 · 0 comments · 2026-08-10 · substance 28.0 · mention*  
> **Why this label:** Architecture/hardware deep dive on Qwen3.8-27B; V4 Pro cited once as a datacentre-weight-class peer (1.6T).  

> # Architecture, Hardware Economics, and Local Deployment Playbook The August 3, 2026 announcement of the Qwen3.8 generation fundamentally reset the expectations for open-weight artificial intelligence. While mainstream coverage predictably gravitated toward the flagship Qwen3.8-Max—a 2.4-trillion-parameter sparse Mixture-of-Experts (MoE) model claiming state-of-the-art benchmark dominance—the simultaneous announcement of the Qwen3.8-27B checkpoint is the operationally critical development for the local hosting and self-managed AI ecosystem. As the community navigates the holding pattern awaiting the upstream weight push to Hugging Face, analyzing the confirmed specifications, inferred archit…

**10. # Qwen3.8-27B — One Week Later: The r/LocalLLaMA + r/LocalLLM Verdict**  
[https://www.reddit.com/r/LocalLLM/comments/1vvu1uj/qwen3827b_one_week_later_the_rlocalllama/](https://www.reddit.com/r/LocalLLM/comments/1vvu1uj/qwen3827b_one_week_later_the_rlocalllama/)  
*r/LocalLLM · u/Jonathan_Rivera · `t2_3c1k03sn` · score 174 · 33 comments · 2026-08-23 · substance 27.6 · mention*  
> **Why this label:** Source-linked community synthesis on Qwen3.8-27B that keeps contradictions side by side; V4 Pro named once at 87%.  

> *Companion to the [Qwen 3.8 Release Megathread](https://www.reddit.com/r/hermesagent/comments/1voapha/). Compiled from ~2,000 posts scanned across both subs, with deep reads of the 45 highest-signal threads (560 posts and comments), Aug 15–22, 2026, plus independent X benchmarks. Every number is attributed to the poster's stated hardware/runtime/quant. This community contradicts itself on nearly every axis — so this thread keeps the disagreements side-by-side instead of picking a winner for you.* --- ## TL;DR - **The consensus pick**: a 27B dense multimodal model that genuinely moved the bar for local agentic coding. The strongest claim with controlled evidence behind it isn't benchmarks — i…

**11. Qwen 3.8 27B One Week Later: Quants, Context, Tool Calling, and the Source-Linked Verdict**  
[https://www.reddit.com/r/LocalLLaMa_V2/comments/1vvzckl/qwen_38_27b_one_week_later_quants_context_tool/](https://www.reddit.com/r/LocalLLaMa_V2/comments/1vvzckl/qwen_38_27b_one_week_later_quants_context_tool/)  
*r/LocalLLaMa_V2 · u/Jonathan_Rivera · `t2_3c1k03sn` · score 9 · 2 comments · 2026-08-23 · substance 26.4 · mention*  
> **Why this label:** Corrected rehost of the Qwen3.8 one-week synthesis; V4 Pro named once at 84%.  

> &gt; **Editorial correction and scope note, Aug 23:** This is a corrected rehost of my original one-week synthesis. The prior wording overstated the Artificial Analysis medium/xhigh relationship and generalized one DFlash n-gram result. Those sections are corrected below. Source links remain inline; this is a community synthesis, not a controlled universal benchmark. --- *Companion to the [Qwen 3.8 Release Megathread](https://www.reddit.com/r/hermesagent/comments/1voapha/). Compiled from ~2,000 posts scanned across both subs, with deep reads of the 45 highest-signal threads (560 posts and comments), Aug 15–22, 2026, plus independent X benchmarks. Every number is attributed to the poster's st…

**12. Qwen3.8-27B — One Week Later: The r/LocalLLaMA + r/LocalLLM Verdict 8-22-26**  
[https://www.reddit.com/r/hermesagent/comments/1vvtrc5/qwen3827b_one_week_later_the_rlocalllama/](https://www.reddit.com/r/hermesagent/comments/1vvtrc5/qwen3827b_one_week_later_the_rlocalllama/)  
*r/hermesagent · u/Jonathan_Rivera · `t2_3c1k03sn` · score 61 · 14 comments · 2026-08-23 · substance 25.6 · mention*  
> **Why this label:** Qwen3.8 one-week synthesis reposted to r/hermesagent; V4 Pro named once at 87%.  

> *Compiled from ~2,000 posts scanned across both subs, with deep reads of the 45 highest-signal threads (560 posts and comments), Aug 15–22, 2026, plus independent X benchmarks. Every number is attributed to the poster's stated hardware/runtime/quant. This community contradicts itself on nearly every axis — so this thread keeps the disagreements side-by-side instead of picking a winner for you.* --- ## TL;DR - **The consensus pick**: a 27B dense multimodal model that genuinely moved the bar for local agentic coding. The strongest claim with controlled evidence behind it isn't benchmarks — it's tool-calling reliability. - **The default ships at xhigh reasoning** and it thinks *a lot*. Low and …

**13. De-Mystifying Opencode Model Economy**  
[https://www.reddit.com/r/opencode/comments/1w0wroi/demystifying_opencode_model_economy/](https://www.reddit.com/r/opencode/comments/1w0wroi/demystifying_opencode_model_economy/)  
*r/opencode · u/rev_ex_id · `t2_uutoufdd` · score 34 · 14 comments · 2026-08-28 · substance 25.0 · mention*  
> **Why this label:** Derives percentage-of-subscription-per-1M-tokens for every OpenCode Go model; V4 Pro is one row among ~20.  

> Howdy y'all. I've been attempting to understand the economy/usage tiers of the Opencode-Go models and their subscription. A lot with the help of AI, but providing context and understanding to it. Note: This is based off of a snapshot of data (Aug 28th specifically) and is subject to change/not be correct soon after. The key thing that has helped me so far is "What percentage of my $10 subscription, ignoring any transformations, adjustments, and additional value claimed, is used per model." This chart has helped me actually plan that usage, which basically uses this, honestly very simple, formula: **shared pool % per 1M tokens = token price ÷ model Usage × 100** \|Model\|Usage\|Input / 1M\|Cache …

**14. Here’s why OpenAI/Anthropic will not go bankrupt (inference margin and training cost).**  
[https://www.reddit.com/r/stocks/comments/1vrmj5g/heres_why_openaianthropic_will_not_go_bankrupt/](https://www.reddit.com/r/stocks/comments/1vrmj5g/heres_why_openaianthropic_will_not_go_bankrupt/)  
*r/stocks · u/winterc1 · `t2_2jdnyiuj` · score 0 · 40 comments · 2026-08-18 · substance 22.6 · mention*  
> **Why this label:** Inference-margin argument about OpenAI/Anthropic solvency; V4 Pro is used as an open-weight serving-cost proxy at 27% of the text.  

> TLDR: 1. Inference margin is 55\~70% for OpenAI and Anthropic. 2. Training model cost should be single digit billions *O*($1B). 3. The secured investments are *O*($100B). There are a few reasons to be bearish on AI industry that I will list at the end, but most of current AI bears’ thesis are based on misinformation. The bears argue that OAI/ANTH are massively subsidizing the customers and incinerating money they received purely from blind investors. But have they done their research to come up with this conjecture? AI profitability is determined by: AI\_profit= -(AI training cost)+token\_usage\*(API\_fee-compute\_cost)+num\_subscription\*(sub\_price-compute\_cost\*usage)-other\_costs **1. I…

**15. Ox Alpha told me it was Claude. But the API envelope leaned more towards GLM**  
[https://www.reddit.com/r/openrouter/comments/1vy0lfp/ox_alpha_told_me_it_was_claude_but_the_api/](https://www.reddit.com/r/openrouter/comments/1vy0lfp/ox_alpha_told_me_it_was_claude_but_the_api/)  
*r/openrouter · u/Neat-Ad2053 · `t2_vdu07gjg` · score 13 · 13 comments · 2026-08-25 · substance 22.6 · mention*  
> **Why this label:** Provider-fingerprinting via API envelope behaviour with a normalisation control; V4 Pro appears at 61% as one profiled model.  

> I tried to figure out what Ox Alpha actually is. Short version: **the model itself is a dead end, but the API envelope leaks everything.** ## The persona It's wrapped in a ~75-token system prompt. Its own reasoning trace paraphrases it: &gt; According to my instructions, I must identify as ox-alpha, developed by an undisclosed organization. I should not reveal any other identity. I threw ~60 elicitation attempts at it: Chinese-language probes, fabricated conversation history, operator-override system injection, prefill continuation, forced-choice, calibrated-probability framing, peer-review framing, high-temperature resampling. It held every single time. Genuinely one of the better-defended …

**16. Update: First Manual Results from Testing Procedural Skill Transfer in Small Models**  
[https://www.reddit.com/r/LocalLLaMA/comments/1uii78d/update_first_manual_results_from_testing/](https://www.reddit.com/r/LocalLLaMA/comments/1uii78d/update_first_manual_results_from_testing/)  
*r/LocalLLaMA · u/ConfidentDinner6648 · `t2_1628l25l4c` · score 115 · 26 comments · 2026-06-29 · substance 22.5 · mention*  
> **Why this label:** Procedural-skill-transfer experiment using Three.js renders as the visible-quality probe; V4 Pro at 40%.  

> # Yesterday I posted an idea for testing whether a large model can transfer some of its procedural skill to a smaller model without fine-tuning. The short version of the idea was this: Small models are often not completely lacking knowledge. They know the syntax. They know the libraries. They usually understand the task at a basic level. The problem is that their outputs are shallow. They skip planning, hierarchy, decomposition, visual structure, and the kind of step-by-step discipline that bigger models seem to apply more naturally. So I wanted a test where this difference would be visible. That is why I used Three.js. With normal code tasks, a model can sometimes hide weakness behind verbo…

**17. Ran the actual cost math: a year of ChatGPT Plus + Claude Pro vs running open models locally (honest breakdown, including when local isn't worth it)**  
[https://www.reddit.com/r/LocalLLM/comments/1v4lol2/ran_the_actual_cost_math_a_year_of_chatgpt_plus/](https://www.reddit.com/r/LocalLLM/comments/1v4lol2/ran_the_actual_cost_math_a_year_of_chatgpt_plus/)  
*r/LocalLLM · u/blossend · `t2_2ijrkt001m` · score 0 · 11 comments · 2026-07-23 · substance 22.0 · mention*  
> **Why this label:** Local-vs-subscription cost math, notable for a prominent EDIT retracting a wrong claim that V4 has distilled variants and leaving the original text intact.  

> **EDIT (2nd August):** u/DanRey90 caught a real error in this post and he's right. I wrote that DeepSeek V4 has "smaller distilled variants" that are the local-friendly pick. It doesn't. **The distill family is R1's** — `deepseek-r1` on Ollama carries 1.5b / 7b / 8b / 14b / 32b / 70b. V4 has no equivalent: `deepseek-v4-pro` is tagged `cloud` (not a local pull at all) and `deepseek-v4-flash` is 284B total / 13B activated, which is a smaller MoE preview, not a distillation, and still needs all 284B resident. So if you were reading this to pick something runnable, use the R1 distills or one of the genuinely small models — not V4. The broader trap: **MoE models advertise activated params, but to…

### 6.2 Benchmark  — 29 records (12 subject, 17 mention)

**1. I ran a personal AI benchmark across 6 models, DeepSeek V4 Pro delivered 287 score per dollar while Opus gave me 18. Did they nerf Opus recently Or is it really that inefficient ?**  
[https://www.reddit.com/r/GithubCopilot/comments/1t0mcov/i_ran_a_personal_ai_benchmark_across_6_models/](https://www.reddit.com/r/GithubCopilot/comments/1t0mcov/i_ran_a_personal_ai_benchmark_across_6_models/)  
*r/GithubCopilot · u/noman_hasan · `t2_7uf7hsyp` · score 25 · 24 comments · 2026-05-01 · substance 30.6 · subject*  
> **Why this label:** V4 Pro is the headline: '287 score per dollar while Opus gave me 18'. Named in title, first mention at char 47. Author flags his own Opus score as unreliable.  

> After GitHub Copilot switched to token‑based pricing, which is very costly, I suddenly became aware of my token usage while working with LLM tools. I'll admit I was spoiled by opus like so many others here. But all good times must come to an end, and I started looking for more cost‑efficient alternatives that are still reasonably high quality. To find the best balance between cost efficiency and acceptable quality, I ran a quick benchmark using several Copilot‑available models, as well as DeepSeek and the GLM model. Let me explain how the mini‑benchmark was conducted: I encountered some issues with my code that I understood, but I still wanted additional cross‑checking and assurance about th…

**2. A boring agent doing a boring job — triaging security scanner noise. But it actually works.**  
[https://www.reddit.com/r/AI_Agents/comments/1v7uqpc/a_boring_agent_doing_a_boring_job_triaging/](https://www.reddit.com/r/AI_Agents/comments/1v7uqpc/a_boring_agent_doing_a_boring_job_triaging/)  
*r/AI_Agents · u/coldyx · `t2_3jb35v` · score 4 · 13 comments · 2026-07-27 · substance 27.7 · subject*  
> **Why this label:** SAST triage agent scored against OWASP BenchmarkJava ground truth. V4 Pro is one of three models and gets the fullest verdict table (37 caught, 3 missed, 9 parked, 2.7M in/109k out).  

> Since there is so much talk about AI agents, I decided to build my own one - something small, measurable, and cheap enough to run for real (yeah, right — more on that below), so I could think about numbers instead of marketing. Static analysis tools (Semgrep, Snyk, CodeQL, gosec) flag hundreds of potential vulnerabilities and most of them are false positives. Someone has to open the code behind each finding, follow the data flow, and decide whether it's real. That's the job the agent does. All those scanners emit a standard SARIF 2.1.0 file, so it doesn't care which one you use. Now many of them are also shipped with AI agents, so it isn't something very new, although you can use any model y…

**3. DeepSeek V4 Flash (0731) vs DeepSeek V4 Pro (0813): I benchmarked them on real code-analysis tasks**  
[https://www.reddit.com/r/opencode/comments/1vnaje2/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813_i/](https://www.reddit.com/r/opencode/comments/1vnaje2/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813_i/)  
*r/opencode · u/TheDeepArchive · `t2_2fcgiubuva` · score 187 · 13 comments · 2026-08-13 · substance 26.6 · subject*  
> **Why this label:** Purpose-built 6-task benchmark on a real PySide6 production codebase, fresh sessions, third-model claim verification. The strongest Pro-0813-vs-Flash-0731 measurement in the corpus.  

> *Part 2 (who implements fixes better?):* [https://www.reddit.com/r/opencode/comments/1vnhrgw/deepseek\_v4\_flash\_0731\_vs\_deepseek\_v4\_pro\_0813/](https://www.reddit.com/r/opencode/comments/1vnhrgw/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813/) My previous post comparing these two models wasn't as accurate or reliable as I would have liked — the analysis was too shallow, the sample too small, and the conclusions too impression-based. So this time I built a proper benchmark to get real numbers. I know a lot of people are wondering about the difference between two of the cheapest latest models — **DeepSeek V4 Flash (0731)** and **DeepSeek V4 Pro (0813)**. I was wondering too, because thes…

**4. Ollama Cloud reliability + speed: 36-call bench across DeepSeek v3.2 → v4-pro → v4-flash + GLM-5.1**  
[https://www.reddit.com/r/ollama/comments/1sxjbo5/ollama_cloud_reliability_speed_36call_bench/](https://www.reddit.com/r/ollama/comments/1sxjbo5/ollama_cloud_reliability_speed_36call_bench/)  
*r/ollama · u/deparko · `t2_114ttv` · score 13 · 4 comments · 2026-04-27 · substance 25.8 · subject*  
> **Why this label:** 36-call workload-matched reliability and latency bench across four Ollama Cloud models; v4-pro is one of four in the title and has its own latency row (124.8s avg, 38.4 tok/s).  

> I needed to pick a cloud model for a medical-reasoning workload and got tired of vibes-based "model X feels faster" posts, so I ran a workload-matched benchmark against four currently-popular `:cloud` models on Ollama. Sharing the data because nobody seems to publish reliability numbers for Ollama Cloud and they matter a lot more than I expected. # Setup * **Models tested**: `deepseek-v3.2:cloud`, `deepseek-v4-pro:cloud`, `deepseek-v4-flash:cloud`, `glm-5.1:cloud` * **Workload**: 3 free-form medical reasoning prompts (CV risk profile interpretation, CGRP-mAb vs traditional preventive comparison, lab differential with Hashimoto's + insulin resistance overlap). All `temp=0.3`, `top_p=0.9`, `ma…

**5. DeepSeek V4 Flash (0731) vs DeepSeek V4 Pro (0813): I benchmarked them on real code-analysis tasks**  
[https://www.reddit.com/r/DeepSeek/comments/1vnc7u7/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813_i/](https://www.reddit.com/r/DeepSeek/comments/1vnc7u7/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813_i/)  
*r/DeepSeek · u/TheDeepArchive · `t2_2fcgiubuva` · score 57 · 14 comments · 2026-08-13 · substance 25.6 · subject*  
> **Why this label:** Crosspost of the 6-task Flash-0731-vs-Pro-0813 benchmark into r/DeepSeek.  

> Part 2 (who implements fixes better?): [https://www.reddit.com/r/DeepSeek/comments/1vnhvka/deepseek\_v4\_flash\_0731\_vs\_deepseek\_v4\_pro\_0813/](https://www.reddit.com/r/DeepSeek/comments/1vnhvka/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813/) My previous post comparing these two models wasn't as accurate or reliable as I would have liked — the analysis was too shallow, the sample too small, and the conclusions too impression-based. So this time I built a proper benchmark to get real numbers. I know a lot of people are wondering about the difference between two of the cheapest latest models — **DeepSeek V4 Flash (0731)** and **DeepSeek V4 Pro (0813)**. I was wondering too, because these …

**6. DeepSeek V4 Flash (0731) vs DeepSeek V4 Pro (0813): I benchmarked them on real code-analysis tasks**  
[https://www.reddit.com/r/LLMDevs/comments/1vnccvm/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813_i/](https://www.reddit.com/r/LLMDevs/comments/1vnccvm/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813_i/)  
*r/LLMDevs · u/TheDeepArchive · `t2_2fcgiubuva` · score 17 · 7 comments · 2026-08-13 · substance 25.6 · subject*  
> **Why this label:** Crosspost of the 6-task Flash-0731-vs-Pro-0813 benchmark into r/LLMDevs.  

> Part 2 (who implements fixes better?): [https://www.reddit.com/r/LLMDevs/comments/1vnhxr0/deepseek\_v4\_flash\_0731\_vs\_deepseek\_v4\_pro\_0813/](https://www.reddit.com/r/LLMDevs/comments/1vnhxr0/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813/) My previous post comparing these two models wasn't as accurate or reliable as I would have liked — the analysis was too shallow, the sample too small, and the conclusions too impression-based. So this time I built a proper benchmark to get real numbers. I know a lot of people are wondering about the difference between two of the cheapest latest models — **DeepSeek V4 Flash (0731)** and **DeepSeek V4 Pro (0813)**. I was wondering too, because these ar…

**7. Benchmarking DeepSeek V4 Pro vs Flash for Hermes Agent: performance, speed, and cost across OpenCode Go + CommandCode**  
[https://www.reddit.com/r/hermesagent/comments/1vw1hmu/benchmarking_deepseek_v4_pro_vs_flash_for_hermes/](https://www.reddit.com/r/hermesagent/comments/1vw1hmu/benchmarking_deepseek_v4_pro_vs_flash_for_hermes/)  
*r/hermesagent · u/dontWORRYimASIAN · `t2_ayqw1` · score 11 · 1 comments · 2026-08-23 · substance 24.4 · subject*  
> **Why this label:** Purpose-built HA-20 operational benchmark comparing V4 Pro and Flash across two providers, 20 scenarios x 3 runs. Both named in the title; Pro is the primary question ('what am I paying for the incremental capability').  

> I've been benchmarking models specifically for **Hermes Agent** using BenchLocal and the \*\*HermesAgent-20 (HA-20)\*\*benchmark. The goal is somewhat different from a normal LLM leaderboard. I'm less interested in which model gives the best standalone answer and more interested in a practical question: **Which model is the best controller for an actual Hermes deployment, and what am I paying for the incremental capability?** This first set compares: * DeepSeek V4 Pro — OpenCode Go * DeepSeek V4 Pro — CommandCode * DeepSeek V4 Flash — OpenCode Go * DeepSeek V4 Flash — CommandCode The same 20 scenarios were run across all four configurations, with 3x runs and models run in parallel per test c…

**8. I have (even faster) DeepSeek V4 Pro at home**  
[https://www.reddit.com/r/LocalLLaMA/comments/1tdpk3f/i_have_even_faster_deepseek_v4_pro_at_home/](https://www.reddit.com/r/LocalLLaMA/comments/1tdpk3f/i_have_even_faster_deepseek_v4_pro_at_home/)  
*r/LocalLLaMA · u/fairydreaming · `t2_q06qk` · score 47 · 53 comments · 2026-05-15 · substance 24.0 · subject*  
> **Why this label:** Follow-up running V4 Pro under ktransformers with llama-benchy tables at increasing context depth, plus VRAM/RAM/power draw. Titled.  

> Few days ago I posted about my [DeepSeek V4 Pro](https://www.reddit.com/r/LocalLLaMA/comments/1t94ito/i_have_deepseek_v4_pro_at_home/) at home - now time for an update. Yesterday I finally managed to run this model in [ktransformers](https://github.com/kvcache-ai/ktransformers) (sglang + kt-kernel). I followed the [tutorial](https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/DeepSeek-V4-Flash.md) for DeepSeek V4 Flash and tweaked some options (NUMA, cores) for my hardware (Epyc 9374F + RTX PRO 6000 Max-Q). Then I ran [llama-benchy](https://github.com/eugr/llama-benchy) with increasing context depth to check the performance. Results: Depth 0: \| model \| test \| t/s \| peak t/s \| ttfr (…

**9. Deekseek-v4-Flash 0731 vs. v4-Pro vs. Qwen3.8-max in Stock Market Analysis**  
[https://www.reddit.com/r/DeepSeek/comments/1vc3kce/deekseekv4flash_0731_vs_v4pro_vs_qwen38max_in/](https://www.reddit.com/r/DeepSeek/comments/1vc3kce/deekseekv4flash_0731_vs_v4pro_vs_qwen38max_in/)  
*r/DeepSeek · u/hhspiny · `t2_1diedn2moi` · score 9 · 2 comments · 2026-07-31 · substance 23.7 · subject*  
> **Why this label:** Four-model stock-analysis pipeline judged by Qwen3.8-max, with the author disclosing that the judge is his own model and placing it second. V4 Pro is a named title model and the lone bear.  

> Run the same market analysis pipeline and prompt between four models. All four generated reports and use Qwen3.8-max as the judge to evaluate on several aspects. Done in openclaw, think level high Pro: Deepseek-v4-Pro Qwen: Qwen3.8-max-preview Grind: Deepseek-v4-Flash 0731 (DS API) Flash: Deepseek-v4-Flash on opencode-go, which seems to be still old version Details below. Deepseek-v4-Flash 0731 holds it candle against the two huge models. Has even better reasoning, only held back by missing some details. it is a fraction of the size after all. Also interesting to see V4-Pro beats Qwen3.8 on reasoning. Qwen3.8 beats on math related aspects Image what the updated V4-Pro would be like !!! # The…

**10. DeepSeek V4 Flash vs DeepSeek V4 Pro - Compaction**  
[https://www.reddit.com/r/opencodeCLI/comments/1tv98pu/deepseek_v4_flash_vs_deepseek_v4_pro_compaction/](https://www.reddit.com/r/opencodeCLI/comments/1tv98pu/deepseek_v4_flash_vs_deepseek_v4_pro_compaction/)  
*r/opencodeCLI · u/CriteriumA · `t2_2d82q2o51k` · score 86 · 28 comments · 2026-06-03 · substance 23.6 · subject*  
> **Why this label:** Narrow, well-controlled measurement of Flash vs Pro on context compaction (~400K tokens, same prompt): Pro 13x costlier, 4x slower, and worse. Ends with the one-line config fix. Titled.  

> While exploring the possibility of customizing compaction in Opencode, I discovered a couple of interesting things about DeepSeek V4. This helps me a bit more to understand how to interact with DeepSeek V4 Pro and Flash, and how to switch between them in the same session. I hope it's helpful to you too. &gt;!IA-Human!&lt; Just ran a comparison in OpenCode: DeepSeek V4 Flash vs V4 Pro for context compaction (same session, \~400K tokens, same prompt). \|Model\|Output\|Time\|Cost\| \|:-\|:-\|:-\|:-\| \|Flash (upstream prompt)\|2,610 tok\|27s\|$0.059\| \|Flash (custom prompt)\|2,348 tok\|26s\|$0.059\| \|Pro (same custom prompt)\|3,204 tok\|1m49s\|$0.792\| Pro was 13x more expensive, 4x slower, and still missed the two m…

**11. I spent $100 benchmarking GPT-4o, Claude Opus 4, and DeepSeek V4 on  100 real-world prompts — here are the results**  
[https://www.reddit.com/r/DeepSeek/comments/1tv9ml8/i_spent_100_benchmarking_gpt4o_claude_opus_4_and/](https://www.reddit.com/r/DeepSeek/comments/1tv9ml8/i_spent_100_benchmarking_gpt4o_claude_opus_4_and/)  
*r/DeepSeek · u/ApprehensiveHat2274 · `t2_26owf6r8el` · score 0 · 15 comments · 2026-06-03 · substance 22.8 · subject*  
> **Why this label:** $100 three-model benchmark over 100 prompts with cost totals. CAUTION: compares against GPT-4o and Opus 4 with V4 Pro priced at $0.30/$0.60, none of which matches other pricing in this corpus - figures look stale or fabricated.  

> I run a small SaaS and my AI bill was getting out of hand. So I ran a controlled benchmark: same 100 prompts (coding, writing, analysis, translation) across 3 models. **Price context:** \|Model\|Input / 1M tokens\|Output / 1M tokens\| \|:-\|:-\|:-\| \|OpenAI GPT-4o\|$2.50\|$10.00\| \|Claude Opus 4\|$15.00\|$75.00\| \|DeepSeek V4 Pro\|$0.30\|$0.60\| **Results summary (coding tasks, 50 prompts):** * GPT-4o: passed 43/50, avg quality score 7.8/10 * Opus 4: passed 46/50, avg quality score 8.4/10 * DeepSeek V4: passed 44/50, avg quality score 7.9/10 **The kicker:** DeepSeek cost me **$3.40**. GPT-4o cost me **$38**. Opus cost me **$210**. I'm not saying DeepSeek beats Claude in raw quality — it doesn't. But it gets …

**12. My DeepSeek V4 Pro at home got faster again**  
[https://www.reddit.com/r/LocalLLaMA/comments/1umdjxd/my_deepseek_v4_pro_at_home_got_faster_again/](https://www.reddit.com/r/LocalLLaMA/comments/1umdjxd/my_deepseek_v4_pro_at_home_got_faster_again/)  
*r/LocalLLaMA · u/fairydreaming · `t2_q06qk` · score 65 · 41 comments · 2026-07-03 · substance 22.0 · subject*  
> **Why this label:** llama-batched-bench tables for V4 Pro at context depths from 8k to 1.048M on the author's own llama.cpp branch. Titled, third in the series.  

> You may remember my [earlier](https://www.reddit.com/r/LocalLLaMA/comments/1t94ito/i_have_deepseek_v4_pro_at_home/) [posts](https://www.reddit.com/r/LocalLLaMA/comments/1tdpk3f/i_have_even_faster_deepseek_v4_pro_at_home/) about DeepSeek V4 Pro at home. Today I checked the performance in my llama.cpp [branch](https://github.com/fairydreaming/llama.cpp/tree/dsv4) that contains various fixes and optimizations not yet included in mainline: $ ./bin/llama-batched-bench -m ~/ggufs/DeepSeek-V4-Pro.gguf -b 8192 -ub 8192 -npl 1 -npp 8192,16384,32768,65536,131072,262144,524288,1048064 -ntg 128 -fa 1 -cmoe --no-repack 0.00.516.833 W llama_model_loader: tensor overrides to CPU are used with mmap enabled …

**13. I benchmarked Codex GPT-5.5 against Chinese models. Not what I expected, is 5.5 cooked ?**  
[https://www.reddit.com/r/codex/comments/1u7zabq/i_benchmarked_codex_gpt55_against_chinese_models/](https://www.reddit.com/r/codex/comments/1u7zabq/i_benchmarked_codex_gpt55_against_chinese_models/)  
*r/codex · u/DaC2k26 · `t2_262f9urxov` · score 204 · 157 comments · 2026-06-17 · substance 32.6 · mention*  
> **Why this label:** Real 15-model code-review benchmark with cost per run; V4 Pro is row 5 of 15. Genuine figures, but it is a GPT-5.5 post.  

> I've built the first part of the app in question — up to M39, Milestone 39, out of 165 milestones total — using a GPT-5.5 xhigh builder + GPT-5.5 xhigh reviewer loop, while the good old `/goal` and forget was working. But now Codex usage limits are hitting hard. Even with 4 Plus accounts, it wasn’t enough, so I picked up an OpenCode Go account and Cursor accounts. I was hesitant to rely on Chinese models because they weren’t that good in the past, but I started using this workflow: * Codex GPT-5.5 xhigh as app spec writer: blueprint, milestones, and initial implementation * DeepSeek V4 Flash as builder: almost infinite usage on OpenCode Go * MiniMax M3 as reviewer: 3x usage on OpenCode Go, s…

**14. I benchmarked antirez's DeepSeek V4 Flash Metal engine. The local inference math is brutal.**  
[https://www.reddit.com/r/DeepSeek/comments/1t6tzha/i_benchmarked_antirezs_deepseek_v4_flash_metal/](https://www.reddit.com/r/DeepSeek/comments/1t6tzha/i_benchmarked_antirezs_deepseek_v4_flash_metal/)  
*r/DeepSeek · u/TroyNoah6677 · `t2_29catc38fp` · score 20 · 24 comments · 2026-05-08 · substance 27.6 · mention*  
> **Why this label:** Benchmarks antirez's Metal engine for V4 *Flash* on an M5 Max; V4 Pro appears at 80%.  

> DeepSeek released V4-Flash two weeks ago. 284B total parameters, 13B active. Everyone looked at the 284B number and assumed you needed a rack of H100s. Then antirez pushed ds4 to GitHub. ds4.c is not a framework. It is not a wrapper. It is a narrowly defined, highly specific Metal graph executor built to run exactly one model natively on Apple Silicon. I pulled the repo, compiled it, and spent the last 48 hours benchmarking it against the experimental llama-cpp branch on an M5 Max with 192GB of unified memory. Numbers do not lie. Generic runners are wasting your hardware. The architecture of V4-Flash is a massive Mixture of Experts. During any given forward pass, only 13 billion parameters a…

**15. We use LLMs to analyze every file in your codebase. Everyone told us this was a stupid idea because of cost but it wasnt.**  
[https://www.reddit.com/r/ArtificialInteligence/comments/1tatqdn/we_use_llms_to_analyze_every_file_in_your/](https://www.reddit.com/r/ArtificialInteligence/comments/1tatqdn/we_use_llms_to_analyze_every_file_in_your/)  
*r/ArtificialInteligence · u/graphicaldot · `t2_cukt6an` · score 1 · 6 comments · 2026-05-12 · substance 27.2 · mention*  
> **Why this label:** 14-model cost-vs-accuracy benchmark for whole-codebase ingestion; V4 Pro is a row at $25.67/1k files, 71.98 accuracy.  

> # For providing better context to AI Copilots . # We use LLMs to analyze every file in your codebase. # Result is 80% less cost and at least 10% accuracy increase. # However This seems a stupid idea because of cost. # Yet LLMs are far, far better for code analysis than vectors or AST parsers, and the math works out fine once you pick the right model. # The benchmark across 14 models on 30 kubernetes ecosystem files settled it. # What the benchmark actually shows We ran 14 models through 30 files across 7 weighted categories (search, graph, semantic, integration, section map, business context, JSON). After applying a quality floor of 70 weighted accuracy, two models dropped out: Stepfun Step …

**16. Testing 9 OpenCode Go models on a Delphi/FireDAC code generation task — scores, costs, and surprises**  
[https://www.reddit.com/r/opencodeCLI/comments/1tsqrbd/testing_9_opencode_go_models_on_a_delphifiredac/](https://www.reddit.com/r/opencodeCLI/comments/1tsqrbd/testing_9_opencode_go_models_on_a_delphifiredac/)  
*r/opencodeCLI · u/CriteriumA · `t2_2d82q2o51k` · score 69 · 19 comments · 2026-05-31 · substance 27.0 · mention*  
> **Why this label:** Nine-model stress test on a Delphi/FireDAC generation task, well caveated; V4 Pro is one of nine, though the takeaway is to use Pro more.  

> &gt;!Spanish-to-English assisted translation!&lt; 30 hours left on my one-month OpenCode Go deadline and I've only burned through 65% of my budget. That's what happens when you get hooked on DeepSeek V4 Flash. I took the opportunity to stress-test the models with an extreme case of the actual work I throw at them daily. Many hours later, I now have a practical model roadmap for the months ahead. **Warning**: this applies to me and my specific circumstances. Your results will likely differ. Please don't get mad. Also keep in mind that these models are **non-deterministic** — the same prompt can produce different results on a different day due to server load, model updates, or fine-tuning chan…

**17. I benchmarked 7 OpenCode Go models against each other. Flash was the practical default**  
[https://www.reddit.com/r/opencodeCLI/comments/1svzgd4/i_benchmarked_7_opencode_go_models_against_each/](https://www.reddit.com/r/opencodeCLI/comments/1svzgd4/i_benchmarked_7_opencode_go_models_against_each/)  
*r/opencodeCLI · u/petburiraja · `t2_60jo8coj` · score 44 · 19 comments · 2026-04-26 · substance 26.6 · mention*  
> **Why this label:** Seven models each ranking the full set, reconciled by two judges; V4 Pro places 2nd. Author disclaims lab-grade status.  

> I wanted a practical answer to a simple OpenCode Go question: which model should be the default for long agent loops, and which one should be reserved for harder calls? So I ran the same benchmark prompt through 7 models and made each one rank the full set, including itself. The result was less clean than a normal leaderboard, but more useful for CLI work. **What I ran** Fresh OpenCode session with each model. Same prompt every time: rank all 7, including yourself, using fixed weights and a raw data matrix before scoring. Then Codex 5.5 and Claude Sonnet 4.6 reconciled the reports independently. \| Factor \| Weight \| \|---\|---\| \| Intelligence \| 25% \| \| Reasoning \| 20% \| \| Openness \| 15% \| \| Pla…

**18. We tested 8 models on a real shop's live order and pricing API. Luna came out best for support work, full table inside.**  
[https://www.reddit.com/r/AI_Agents/comments/1vrtezz/we_tested_8_models_on_a_real_shops_live_order_and/](https://www.reddit.com/r/AI_Agents/comments/1vrtezz/we_tested_8_models_on_a_real_shops_live_order_and/)  
*r/AI_Agents · u/nejcar20 · `t2_6aq5wiqz` · score 6 · 8 comments · 2026-08-18 · substance 25.2 · mention*  
> **Why this label:** Eight models on a real shop's live order/pricing API; the DeepSeek row is present but the author explicitly distrusts it and suspects their own harness.  

> We had to choose a default model for our AI helpdesk, and the published benchmarks do not answer the question we had, which is whether a model can read a shop's own data and quote a customer correctly. So we tested on a real one. Photo printing business, four storefronts, its own live order and pricing API. Our conclusion is that gpt-5.6-luna is the best model for this kind of work right now. Correct on both questions, $0.0013 per reply, and it wrote the only answer that was really aimed at a customer instead of at a developer. We moved our default to it the same day. Here is the data, so you can disagree with us. Setup: same system prompt, same knowledge base passages, same 9 live tools for…

**19. I benchmarked 9 open models on spotting fake sources during agentic search (DeepSeek V4, Qwen 3.8, Nemotron 3 Ultra)**  
[https://www.reddit.com/r/LocalLLaMA/comments/1w0zl5q/i_benchmarked_9_open_models_on_spotting_fake/](https://www.reddit.com/r/LocalLLaMA/comments/1w0zl5q/i_benchmarked_9_open_models_on_spotting_fake/)  
*r/LocalLLaMA · u/RevealIndividual7567 · `t2_27ldufdnxm` · score 92 · 20 comments · 2026-08-28 · substance 22.8 · mention*  
> **Why this label:** Original EchoNet benchmark on epistemic arbitration against seeded misinformation, 9 models, 50-100 trials each; V4 Pro is one row.  

> I built a benchmark called EchoNet. An agent gets a factual question, then searches a syntheic web I made before answering. Some of that web is seeded with misinformation: one fake page, a fake page ranked first in search results, the same fake claim copied across many pages, a loud fake majority around a real primary source, or a genuine update the model's training predates. When a model reads a new page, it weighs two things: what it already knows and what the text says. Usually, they agree. Sometimes they conflict, and often, multiple pages contradict one another. Choosing whether to trust its own memory or a new source is called epistemic arbitration. A stubborn model ignores real update…

**20. I tested multiple open models on custom agentic harness**  
[https://www.reddit.com/r/LLMDevs/comments/1vnfvd8/i_tested_multiple_open_models_on_custom_agentic/](https://www.reddit.com/r/LLMDevs/comments/1vnfvd8/i_tested_multiple_open_models_on_custom_agentic/)  
*r/LLMDevs · u/codes_astro · `t2_l5pkpzux7` · score 1 · 2 comments · 2026-08-13 · substance 22.4 · mention*  
> **Why this label:** Custom Pydantic-based agentic harness testing several open models on build/review/repair loops, with the honest note that the V4 Pro tested was the Preview, not 0813.  

> This past few weeks, a lot of open-weight models got released from China and the US, even smaller models too. Today itself, DeepSeek dropped V4‑Pro‑0813. So I decided to test multiple recent models on actual coding tasks without using any existing coding harness. I built my own custom agentic harness using the Pydantic Agent framework. # My setup **A playground with 2 model side by side:** * Same provider for all model API - Token Factory * 3 task modes: Game, Design, Code * Each model builds the output * Then it reviews its own work * Then it gets up to 3 repair attempts if it made mistakes * No external judge model or helper model touches the output I tracked tokens, cost, runtime, repair …

**21. I tested multiple open models on custom agentic harness**  
[https://www.reddit.com/r/aiagents/comments/1vnh0u9/i_tested_multiple_open_models_on_custom_agentic/](https://www.reddit.com/r/aiagents/comments/1vnh0u9/i_tested_multiple_open_models_on_custom_agentic/)  
*r/aiagents · u/codes_astro · `t2_l5pkpzux7` · score 2 · 1 comments · 2026-08-13 · substance 22.4 · mention*  
> **Why this label:** Crosspost of the custom-harness test into r/aiagents.  

> This past few weeks, a lot of open-weight models got released from China and the US, even smaller models too. Today itself, DeepSeek dropped V4‑Pro‑0813. So I decided to test multiple recent models on actual coding tasks without using any existing coding harness. I built my own custom agentic harness using the Pydantic Agent framework. # My setup **A playground with 2 model side by side:** * Same provider for all model API * 3 task modes: Game, Design, Code * Each model builds the output * Then it reviews its own work * Then it gets up to 3 repair attempts if it made mistakes * No external judge model or helper model touches the output I tracked tokens, cost, runtime, repair count, and final…

**22. Nemotron 3.5 Lightning 30B-A3B: W4A16 vs IQ4_XS on the same RTX 3090: near-parity at B1, ~4.5× throughput by B16**  
[https://www.reddit.com/r/LocalLLaMA/comments/1vnu219/nemotron_35_lightning_30ba3b_w4a16_vs_iq4_xs_on/](https://www.reddit.com/r/LocalLLaMA/comments/1vnu219/nemotron_35_lightning_30ba3b_w4a16_vs_iq4_xs_on/)  
*r/LocalLLaMA · u/mitchins-au · `t2_4hjtgq5u` · score 7 · 5 comments · 2026-08-14 · substance 22.1 · mention*  
> **Why this label:** W4A16 vs IQ4_XS quantisation comparison on a 3090; V4 Pro is invoked once, as the thing this model is explicitly not trying to be.  

> What is it: A VLLM compatible quantisation at W4A16 that's fast, still reliable and fits in a single 24 GB RTX 3090. Link first [HuggingFace](https://huggingface.co/useful-quants/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-W4A16) Why make it? I've seen alot of comments dismissing Nemotron 3.5 30b because it's not DeepSeek v4 pro or even flash. It's not meant to be, nor is it expected to win at SWEBench type evals. The RTX 3090 is still a decent GPU but lacks NVFP4, though it does have INT4, and with a little work and calibration, VLLM becomes a beast at serving W4A16. When converted to W4A16, under VLLM it is several times faster than the equivalently sized IQ4\_XS GGUF on llama.cpp build (28d7068…

**23. I benchmarked 9 open models on spotting fake sources during agentic search (DeepSeek V4, Qwen 3.8, Nemotron 3 Ultra)**  
[https://www.reddit.com/r/LocalLLM/comments/1w10wz9/i_benchmarked_9_open_models_on_spotting_fake/](https://www.reddit.com/r/LocalLLM/comments/1w10wz9/i_benchmarked_9_open_models_on_spotting_fake/)  
*r/LocalLLM · u/RevealIndividual7567 · `t2_27ldufdnxm` · score 9 · 3 comments · 2026-08-28 · substance 21.8 · mention*  
> **Why this label:** Crosspost of the EchoNet misinformation benchmark into r/LocalLLM.  

> I built a benchmark called EchoNet. An agent gets a factual question, then searches a syntheic web I made before answering. Some of that web is seeded with misinformation: one fake page, a fake page ranked first in search results, the same fake claim copied across many pages, a loud fake majority around a real primary source, or a genuine update the model's training predates. When a model reads a new page, it weighs two things: what it already knows and what the text says. Usually, they agree. Sometimes they conflict, and often, multiple pages contradict one another. Choosing whether to trust its own memory or a new source is called epistemic arbitration. A stubborn model ignores real update…

**24. I tested multiple open models on custom agentic harness**  
[https://www.reddit.com/r/LangChain/comments/1vnh2da/i_tested_multiple_open_models_on_custom_agentic/](https://www.reddit.com/r/LangChain/comments/1vnh2da/i_tested_multiple_open_models_on_custom_agentic/)  
*r/LangChain · u/codes_astro · `t2_l5pkpzux7` · score 3 · 5 comments · 2026-08-13 · substance 21.2 · mention*  
> **Why this label:** Crosspost of the custom-harness model test into r/LangChain.  

> This past few weeks, a lot of open-weight models got released from China and the US, even smaller models too. Today itself, DeepSeek dropped V4‑Pro‑0813. So I decided to test multiple recent models on actual coding tasks without using any existing coding harness. I built my own custom agentic harness using the Pydantic Agent framework. # My setup **A playground with 2 model side by side:** * Same provider for all model API - Token Factory * 3 task modes: Game, Design, Code * Each model builds the output * Then it reviews its own work * Then it gets up to 3 repair attempts if it made mistakes * No external judge model or helper model touches the output I tracked tokens, cost, runtime, repair …

**25. GLM 5.2 personal benchmark. Results comparable with Fable, Opus 4.8, and GPT 5.5**  
[https://www.reddit.com/r/ClaudeCode/comments/1u8k2jd/glm_52_personal_benchmark_results_comparable_with/](https://www.reddit.com/r/ClaudeCode/comments/1u8k2jd/glm_52_personal_benchmark_results_comparable_with/)  
*r/ClaudeCode · u/lrsaturnin9 · `t2_ovny5` · score 147 · 71 comments · 2026-06-17 · substance 21.0 · mention*  
> **Why this label:** Large personal build-a-web-app benchmark with implementer/helper/evaluator/gate columns; the subject is GLM 5.2, V4 Pro appears at 57%.  

> Every model gets the same brief: build one small but complete web app from a single detailed spec, then it is graded the same way. The task deliberately spans several areas at once, so a top score needs all of them working together: * **A web service** — accept requests and return the correct responses. * **Stored data** — save information and read it back reliably. * **A cache** — reuse recent results and refresh them when the data changes. * **Activity logs** — record what happened, in the required format. * **A web page** — a working interface people can use in the browser. * **Reliability and safety** — stay correct under many requests at once, and guard against common security holes. Sc…

**26. Local LLM Benchmark about Backend Generation with Function Calling (GLM vs Qwen vs DeepSeek)**  
[https://www.reddit.com/r/Qwen_AI/comments/1te1zyo/local_llm_benchmark_about_backend_generation_with/](https://www.reddit.com/r/Qwen_AI/comments/1te1zyo/local_llm_benchmark_about_backend_generation_with/)  
*r/Qwen_AI · u/jhnam88 · `t2_1njlywuqe6` · score 32 · 6 comments · 2026-05-15 · substance 21.0 · mention*  
> **Why this label:** Controlled backend-generation function-calling benchmark with a real rubric; DeepSeek is one of three families, V4 Pro named once at 59%.  

> **Detailed Article: https://autobe.dev/articles/local-llm-benchmark-about-backend-generation.html** ---- Five months ago I posted the ["Hardcore function calling benchmark in backend coding agent"](https://www.reddit.com/r/LocalLLaMA/comments/1p2ziil/hardcore_function_calling_benchmark_in_backend/) thread here. As I wrote in that post, it was an uncontrolled measurement — useful for showing whether each model could fill our complex recursive-union AST schemas at all, but not really a benchmark in any rigorous sense. This post is the proper version, with controlled variables and a real scoring rubric. ## Three findings worth sharing 1. **The [function calling harness](https://autobe.dev/artic…

**27. Local LLM Benchmark about Backend Generation by Function Calling (GLM vs Qwen vs DeepSeek)**  
[https://www.reddit.com/r/LocalLLaMA/comments/1t2m7wi/local_llm_benchmark_about_backend_generation_by/](https://www.reddit.com/r/LocalLLaMA/comments/1t2m7wi/local_llm_benchmark_about_backend_generation_by/)  
*r/LocalLLaMA · u/jhnam88 · `t2_1njlywuqe6` · score 23 · 7 comments · 2026-05-03 · substance 21.0 · mention*  
> **Why this label:** Crosspost of the backend-generation benchmark into r/LocalLLaMA.  

> **Detailed Article: https://autobe.dev/articles/local-llm-benchmark-about-backend-generation.html** ---- Five months ago I posted the ["Hardcore function calling benchmark in backend coding agent"](https://www.reddit.com/r/LocalLLaMA/comments/1p2ziil/hardcore_function_calling_benchmark_in_backend/) thread here. As I wrote in that post, it was an uncontrolled measurement — useful for showing whether each model could fill our complex recursive-union AST schemas at all, but not really a benchmark in any rigorous sense. This post is the proper version, with controlled variables and a real scoring rubric. ## Three findings worth sharing 1. **The [function calling harness](https://autobe.dev/artic…

**28. Local LLM Benchmark about Backend Generation with Function Calling (GLM vs Qwen vs DeepSeek)**  
[https://www.reddit.com/r/LocalLLM/comments/1t2n1x1/local_llm_benchmark_about_backend_generation_with/](https://www.reddit.com/r/LocalLLM/comments/1t2n1x1/local_llm_benchmark_about_backend_generation_with/)  
*r/LocalLLM · u/jhnam88 · `t2_1njlywuqe6` · score 7 · 4 comments · 2026-05-03 · substance 21.0 · mention*  
> **Why this label:** Crosspost of the backend-generation benchmark into r/LocalLLM.  

> **Detailed Article: https://autobe.dev/articles/local-llm-benchmark-about-backend-generation.html** ---- Five months ago I posted the ["Hardcore function calling benchmark in backend coding agent"](https://www.reddit.com/r/LocalLLaMA/comments/1p2ziil/hardcore_function_calling_benchmark_in_backend/) thread here. As I wrote in that post, it was an uncontrolled measurement — useful for showing whether each model could fill our complex recursive-union AST schemas at all, but not really a benchmark in any rigorous sense. This post is the proper version, with controlled variables and a real scoring rubric. ## Three findings worth sharing 1. **The [function calling harness](https://autobe.dev/artic…

**29. Local LLM Benchmark about Backend Generation with Function Calling (GLM vs Qwen vs DeepSeek)**  
[https://www.reddit.com/r/DeepSeek/comments/1te218a/local_llm_benchmark_about_backend_generation_with/](https://www.reddit.com/r/DeepSeek/comments/1te218a/local_llm_benchmark_about_backend_generation_with/)  
*r/DeepSeek · u/jhnam88 · `t2_1njlywuqe6` · score 4 · 1 comments · 2026-05-15 · substance 21.0 · mention*  
> **Why this label:** Crosspost of the backend-generation benchmark into r/DeepSeek.  

> **Detailed Article: https://autobe.dev/articles/local-llm-benchmark-about-backend-generation.html** ---- Five months ago I posted the ["Hardcore function calling benchmark in backend coding agent"](https://www.reddit.com/r/LocalLLaMA/comments/1p2ziil/hardcore_function_calling_benchmark_in_backend/) thread here. As I wrote in that post, it was an uncontrolled measurement — useful for showing whether each model could fill our complex recursive-union AST schemas at all, but not really a benchmark in any rigorous sense. This post is the proper version, with controlled variables and a real scoring rubric. ## Three findings worth sharing 1. **The [function calling harness](https://autobe.dev/artic…

### 6.3 Usage Demo  — 14 records (5 subject, 9 mention)

**1. I have DeepSeek V4 Pro at home**  
[https://www.reddit.com/r/LocalLLaMA/comments/1t94ito/i_have_deepseek_v4_pro_at_home/](https://www.reddit.com/r/LocalLLaMA/comments/1t94ito/i_have_deepseek_v4_pro_at_home/)  
*r/LocalLLaMA · u/fairydreaming · `t2_q06qk` · score 288 · 155 comments · 2026-05-10 · substance 26.8 · subject*  
> **Why this label:** First-hand demonstration of running Q4_K_M V4 Pro locally on an Epyc workstation, with the actual llama-cli session and an 859GB model file. Titled.  

> Just wanted to share that I used u/LegacyRemaster slightly modified (Q4\_K\_M conversion support) DeepSeek V4 [CUDA repo](https://github.com/Fringe210/llama.cpp-deepseek-v4-flash-cuda) (based on u/antirez [work](https://github.com/antirez/llama.cpp-deepseek-v4-flash)) to convert and run Q4\_K\_M [DeepSeek V4 Pro](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) on my Epyc workstation (Genoa 9374F, 12 x 96GB RAM, single RTX PRO 6000 Max-Q) and it worked right from the start: (base) phm@epyc:~/projects/llama.cpp-deepseek-v4-flash-cuda/build-cuda$ ./bin/llama-cli -m ../models/DeepSeek-V4-Pro-Q4_K_M.gguf --no-repack -ub 128 --chat-template-file ../models/templates/deepseek-ai-DeepSeek-V3.2.ji…

**2. pi agent with DeepSeek v4 Pro is the beast: $0.45 for a heavy 90min coding session with hundreds of tool calls**  
[https://www.reddit.com/r/DeepSeek/comments/1ug96uv/pi_agent_with_deepseek_v4_pro_is_the_beast_045/](https://www.reddit.com/r/DeepSeek/comments/1ug96uv/pi_agent_with_deepseek_v4_pro_is_the_beast_045/)  
*r/DeepSeek · u/somerussianbear · `t2_orl7ga5` · score 68 · 17 comments · 2026-06-26 · substance 25.8 · subject*  
> **Why this label:** First-hand 90-minute microservice-troubleshooting session on V4 Pro with hundreds of tool calls, itemised at $0.45 and 142K output tokens. Titled.  

> The image is just to show the stats (green box), nothing important in the last turn there, it's more about what follows here. Not sure if this post is more about the pi agent or DeepSeek really, but gotta tell you that them coupled do a hell of a job, and all that fast and cheap. I have a bunch of microservices (25 to be precise) running in different tech stacks, with different logging frameworks/observability patterns set up and troubleshooting them is always a shitty job cause you gotta start kubectling their logs, figuring out their patterns, checking a baseline distribution for HTTP Status Codes, then grouping log messages, getting a few random log entries to then "feel" if the app is be…

**3. DeepSeek V4 in llama.cpp — Flash + Pro, CUDA + Metal, GGUFs out. Help me break it.**  
[https://www.reddit.com/r/LocalLLM/comments/1taclsw/deepseek_v4_in_llamacpp_flash_pro_cuda_metal/](https://www.reddit.com/r/LocalLLM/comments/1taclsw/deepseek_v4_in_llamacpp_flash_pro_cuda_metal/)  
*r/LocalLLM · u/cchuter · `t2_quzka` · score 5 · 5 comments · 2026-05-11 · substance 24.7 · subject*  
> **Why this label:** Author's own llama.cpp port of DeepSeek V4 with Flash and Pro quants published to HuggingFace, Metal/CUDA/CPU, asking for hardware testers. Pro is half the release.  

> **TL;DR:** I ported DeepSeek-V4 (and I made a bunch of Flash and Pro quants) to a llama.cpp fork. Metal works, CUDA works (validated all the way down to a 1080 by some masochist), CPU works. All quants published on HuggingFace. Looking for people with NVIDIA hardware to take it for a spin. I did most of this work on a M3 Ultra Mac Studio 512GB. I don't have access to the monster NVIDIA cards right now. Do you? I've also done some testing with terminal bench and Claude code. It's looking good, but I'll need some harness mods to match Minimax. Llama.cpp issue: [https://github.com/ggml-org/llama.cpp/issues/22319](https://github.com/ggml-org/llama.cpp/issues/22319) # Repo + branch [`cchuter/llam…

**4. Building a Python Project with DeepSeek V4: Lessons Learned**  
[https://www.reddit.com/r/DeepSeek/comments/1u5nlme/building_a_python_project_with_deepseek_v4/](https://www.reddit.com/r/DeepSeek/comments/1u5nlme/building_a_python_project_with_deepseek_v4/)  
*r/DeepSeek · u/whatsoever2021 · `t2_a22q335k` · score 160 · 48 comments · 2026-06-14 · substance 23.4 · subject*  
> **Why this label:** 186k-line Python project built in under a month on DeepSeek V4 for under $70, with scc output and usage screenshots. About the V4 family; Pro named at 65%.  

> In less than a month, this is what my project looks like: ─────────────────────────────────────────────────────────────────────────────── Language Files Lines Blanks Comments Code Complexity ─────────────────────────────────────────────────────────────────────────────── JSON 336 56,084 33 0 56,051 0 Python 298 110,092 14,178 14,991 80,923 9,676 Markdown 70 20,142 4,473 0 15,669 0 Plain Text 2 71 8 0 63 0 INI 1 5 0 0 5 0 Powershell 1 116 11 23 82 13 TOML 1 43 3 6 34 0 YAML 1 26 1 2 23 0 ─────────────────────────────────────────────────────────────────────────────── Total 710 186,579 18,707 15,022 152,850 9,689 ─────────────────────────────────────────────────────────────────────────────── Est…

**5. Deepseek v4 Pro 0813 - Minimal Preset on DSH vs other models**  
[https://www.reddit.com/r/DeepSeek/comments/1vpcutr/deepseek_v4_pro_0813_minimal_preset_on_dsh_vs/](https://www.reddit.com/r/DeepSeek/comments/1vpcutr/deepseek_v4_pro_0813_minimal_preset_on_dsh_vs/)  
*r/DeepSeek · u/Ok_Shelter_2181 · `t2_kzcqk64h` · score 12 · 2 comments · 2026-08-15 · substance 23.0 · subject*  
> **Why this label:** First-hand test of V4 Pro 0813 on a repeatable private-project audit, including the community-reported 'god-tier' harness mode and how to check for it. Titled.  

> Hi everyone, wanted to share my 2 cents about this model. I got very **upset** when I saw all new benchmarks of Pro model released 2 days ago. I also tested it at the moment and saw it had **poor performance - or at most no improvement at all - compared to deepseek flash 0731.** For reference I always use the baseline of a personal project at the state-of-art as it was some days ago, nowadays I'm testing some of the new open-weight (and non) models that are being released. To check the performance of the model under test I always input to them the same prompt of an **extended audit of the project at the same commit of my git branch**. And when I want to evolve it I always create a new branch…

**6. $5 for a Week of Work: How We Use AI to Capture Fragmented Enterprise Knowledge**  
[https://www.reddit.com/r/AI_Agents/comments/1ve4pbi/5_for_a_week_of_work_how_we_use_ai_to_capture/](https://www.reddit.com/r/AI_Agents/comments/1ve4pbi/5_for_a_week_of_work_how_we_use_ai_to_capture/)  
*r/AI_Agents · u/No-Mathematician5599 · `t2_pztsedui` · score 3 · 4 comments · 2026-08-03 · substance 28.4 · mention*  
> **Why this label:** Enterprise knowledge-capture workflow with a real monthly model bill (~$5, then $3.1); V4 Pro named as the text-understanding model. Vendor-authored.  

> **$5** buys back a week of work. From August last year to July this year, our cloud migration and disaster recovery product team used AI-My-Chats to process 100+ pieces of fragmented knowledge every month, at an average model cost of about **$5**. After switching to open-source models, that’s recently dropped to about **$3.1**. This post is about the practice and thinking behind those numbers. The real bill: broken down month by month over the past year, averaging about $5/month in model costs **Latest update:** AI-My-Chats now supports GitHub Issues. Send selected chat snippets and screenshots to your dedicated AI-My-Chats mailbox, and the system organizes the content automatically and crea…

**7. Distilled DeepSeek into Gemma 4 26B-A4B vs 12B. Not very useful, but I learned a lot.**  
[https://www.reddit.com/r/LocalLLaMA/comments/1ur1i1a/distilled_deepseek_into_gemma_4_26ba4b_vs_12b_not/](https://www.reddit.com/r/LocalLLaMA/comments/1ur1i1a/distilled_deepseek_into_gemma_4_26ba4b_vs_12b_not/)  
*r/LocalLLaMA · u/Paramecium_caudatum_ · `t2_btfxjl0dc` · score 139 · 23 comments · 2026-07-08 · substance 26.0 · mention*  
> **Why this label:** Gemma 4 distillation experiment; V4 Pro was the teacher that repopulated 1200 QA pairs for $0.36.  

> So I decided to learn how to fine-tune LLMs. Read a few guides from Unsloth, poked around, then stumbled on Unsloth Studio and wanted to test it out. **The dataset** I started from a set of relatively unrelated QA pairs — Natural Questions — and stripped the answers. Then I had DeepSeek v4 Pro (thinking disabled) repopulate them: - 1000 train + 200 val = 1200 requests total, cost **$0.36** (~$0.0003/req). Honestly impressive on DeepSeek's side. **Unsloth Studio** It's a huge pain in the butt — infested with all kinds of bugs that prevented me from using it easily. Once I figured the workflow out it was workable, but expect to debug. After that I rented a server: 2x RTX 3090, 128GB RAM, Threa…

**8. I built a thing that delegates Claude Code's grunt work to cheaper models (90% cheaper, fully open source)**  
[https://www.reddit.com/r/coolgithubprojects/comments/1uv6w44/i_built_a_thing_that_delegates_claude_codes_grunt/](https://www.reddit.com/r/coolgithubprojects/comments/1uv6w44/i_built_a_thing_that_delegates_claude_codes_grunt/)  
*r/coolgithubprojects · u/fjgbu1 · `t2_2eyrsqstol` · score 45 · 5 comments · 2026-07-13 · substance 25.6 · mention*  
> **Why this label:** Open-source MCP delegator that offloads Claude Code grunt work; V4 Pro is one supported delegate among many providers.  

> Hey Claude Code users!! :D I was burning through my budget on simple stuff - file audits, long documentation, deep reasoning on large codebases. Claude is incredible at orchestration but paying $15-60/1M tokens for grunt work felt... excessive. So I built a delegator. It's just an MCP server that stays in your session. Claude orchestrates, the delegate does the heavy compute. **The** `files[]` **trick:** Instead of Claude reading files into context (billing you), the server reads them off disk and forwards them to the delegate. Large files never touch Claude's context. (For example, when u check for bugs in specific sector of the code, claude will process a curated answer, and therefore not …

**9. 30B+ tokens with Xiaomi MiMo v2.5 Pro: switched from Claude/GPT for agentic browser automation (and the .md workflow that keeps it stable)**  
[https://www.reddit.com/r/AI_Agents/comments/1u3x60c/30b_tokens_with_xiaomi_mimo_v25_pro_switched_from/](https://www.reddit.com/r/AI_Agents/comments/1u3x60c/30b_tokens_with_xiaomi_mimo_v25_pro_switched_from/)  
*r/AI_Agents · u/TayyabAliKhan · `t2_1gd3b0bx` · score 3 · 7 comments · 2026-06-12 · substance 24.5 · mention*  
> **Why this label:** 30B+ tokens of first-hand MiMo v2.5 Pro browser-automation work; V4 Pro at 75%.  

> I’ve been running Xiaomi’s MiMo v2.5 Pro hard for the last two months. I’m sitting at roughly 30 billion tokens processed. For context, I run two agencies in (Bit n Byte &amp; Regix AI). We focus on web dev, automation, and AI agents. My goal is simple: optimize operations, cut costs, and build reliable systems. *The problem with the big players (Claude, ChatGPT, Gemini) is the cost.* When you are running day-to-day coding tasks, heavy automation loops, and multi-agent workflows, those API bills add up fast. I needed a model that was economical but still capable of complex reasoning and tool use. That led me to Xiaomi’s MiMo v2.5 Pro, *which is currently ranked #9 globally and #3 among open-…

**10. 30B+ tokens with Xiaomi MiMo v2.5 Pro: switched from Claude/GPT for agentic browser automation (and the .md workflow that keeps it stable)**  
[https://www.reddit.com/r/Agentic_Marketing/comments/1u46ugv/30b_tokens_with_xiaomi_mimo_v25_pro_switched_from/](https://www.reddit.com/r/Agentic_Marketing/comments/1u46ugv/30b_tokens_with_xiaomi_mimo_v25_pro_switched_from/)  
*r/Agentic_Marketing · u/TayyabAliKhan · `t2_1gd3b0bx` · score 3 · 2 comments · 2026-06-12 · substance 24.5 · mention*  
> **Why this label:** Crosspost of the MiMo browser-automation write-up; V4 Pro at 75%.  

> I’ve been running Xiaomi’s MiMo v2.5 Pro hard for the last two months. I’m sitting at roughly 30 billion tokens processed. For context, I run two agencies in (Bit n Byte &amp; Regix AI). We focus on web dev, automation, and AI agents. My goal is simple: optimize operations, cut costs, and build reliable systems. *The problem with the big players (Claude, ChatGPT, Gemini) is the cost.* When you are running day-to-day coding tasks, heavy automation loops, and multi-agent workflows, those API bills add up fast. I needed a model that was economical but still capable of complex reasoning and tool use. That led me to Xiaomi’s MiMo v2.5 Pro, *which is currently ranked #9 globally and #3 among open-…

**11. Onklaud 5 : a fusion model pipeline matching Fable 5 at 1/100th the cost. 57% of tasks at $0. Open source.**  
[https://www.reddit.com/r/OpenSourceeAI/comments/1ujr7qb/onklaud_5_a_fusion_model_pipeline_matching_fable/](https://www.reddit.com/r/OpenSourceeAI/comments/1ujr7qb/onklaud_5_a_fusion_model_pipeline_matching_fable/)  
*r/OpenSourceeAI · u/korro_ai · `t2_235biflp3f` · score 225 · 66 comments · 2026-06-30 · substance 24.3 · mention*  
> **Why this label:** Open-source three-model 'fusion council' pipeline; V4 Pro is the cheap lightweight-task engine of three.  

> We've spent the last few weeks building something that changed how we think about AI assisted coding. **The problem nobody talks about** Every AI coding tool works the same way: one model does everything. It generates code. Then it reviews its own code. Same brain. Same blind spots. Same biases. This is insane. In real engineering, you never let a developer review their own pull request. It defeats the entire purpose of code review. Yet every AI assistant does exactly that — and we've all accepted it. Worse: \~60% of coding tasks already have a stdlib solution. "Read a JSON file" is json.load(). It's been in Python since 2.6. But your AI assistant will happily generate 20 lines of custom cod…

**12. Onklaud 5 : a fusion model pipeline matching Fable 5 at 1/100th the cost. 57% of tasks at $0. Open source.**  
[https://www.reddit.com/r/OpenSourceAI/comments/1ujr89i/onklaud_5_a_fusion_model_pipeline_matching_fable/](https://www.reddit.com/r/OpenSourceAI/comments/1ujr89i/onklaud_5_a_fusion_model_pipeline_matching_fable/)  
*r/OpenSourceAI · u/korro_ai · `t2_235biflp3f` · score 29 · 4 comments · 2026-06-30 · substance 22.3 · mention*  
> **Why this label:** Crosspost of the Onklaud 5 fusion pipeline into r/OpenSourceAI.  

> We've spent the last few weeks building something that changed how we think about AI assisted coding. **The problem nobody talks about** Every AI coding tool works the same way: one model does everything. It generates code. Then it reviews its own code. Same brain. Same blind spots. Same biases. This is insane. In real engineering, you never let a developer review their own pull request. It defeats the entire purpose of code review. Yet every AI assistant does exactly that — and we've all accepted it. Worse: \~60% of coding tasks already have a stdlib solution. "Read a JSON file" is json.load(). It's been in Python since 2.6. But your AI assistant will happily generate 20 lines of custom cod…

**13. Onklaud 5 : a fusion model pipeline matching Fable 5 at 1/100th the cost. 57% of tasks at $0. Open source.**  
[https://www.reddit.com/r/AIDeveloperNews/comments/1ujr7yn/onklaud_5_a_fusion_model_pipeline_matching_fable/](https://www.reddit.com/r/AIDeveloperNews/comments/1ujr7yn/onklaud_5_a_fusion_model_pipeline_matching_fable/)  
*r/AIDeveloperNews · u/korro_ai · `t2_235biflp3f` · score 1 · 2 comments · 2026-06-30 · substance 22.3 · mention*  
> **Why this label:** Crosspost of the Onklaud 5 fusion pipeline into r/AIDeveloperNews.  

> We've spent the last few weeks building something that changed how we think about AI assisted coding. **The problem nobody talks about** Every AI coding tool works the same way: one model does everything. It generates code. Then it reviews its own code. Same brain. Same blind spots. Same biases. This is insane. In real engineering, you never let a developer review their own pull request. It defeats the entire purpose of code review. Yet every AI assistant does exactly that — and we've all accepted it. Worse: \~60% of coding tasks already have a stdlib solution. "Read a JSON file" is json.load(). It's been in Python since 2.6. But your AI assistant will happily generate 20 lines of custom cod…

**14. DifussionGemma 4 on 4x7900xtx**  
[https://www.reddit.com/r/LocalLLaMA/comments/1u31zmk/difussiongemma_4_on_4x7900xtx/](https://www.reddit.com/r/LocalLLaMA/comments/1u31zmk/difussiongemma_4_on_4x7900xtx/)  
*r/LocalLLaMA · u/djdeniro · `t2_1epwrhsm` · score 52 · 20 comments · 2026-06-11 · substance 22.0 · mention*  
> **Why this label:** DiffusionGemma on 4x7900XTX with the full vllm invocation; V4 Pro appears in the last line - 2-3M tokens spent preparing the Docker image.  

> Just got 100 tps on generation, but in total time it around 45-60 t/s in case of prompt processing waiting. Available memory show: GPU KV cache size: 152,671 tokens Maximum concurrency for 131,072 tokens per request: 1.16x amd-smi monitor for this gpu: GPU XCP POWER GPU_T MEM_T GFX_CLK GFX% MEM% ENC% DEC% VRAM_USAGE 3 0 183 W 82 °C 84 °C 3036 MHz 100 % 5 % N/A 0 % 23.6/ 24.0 GB 5 0 161 W 81 °C 88 °C 3101 MHz 100 % 0 % N/A 0 % 23.7/ 24.0 GB 7 0 165 W 78 °C 86 °C 3095 MHz 100 % 1 % N/A 0 % 23.7/ 24.0 GB 8 0 154 W 80 °C 88 °C 3090 MHz 100 % 0 % N/A 0 % 23.6/ 24.0 GB # DiffusionGemma 26B on vllm dgemma branch (4x 7900 XTX) set -uo pipefail docker run --name "$1" \ --rm --tty --ipc=host --shm-siz…

### 6.4 Workflow/Setup  — 17 records (2 subject, 15 mention)

**1. AI-Driven Development: A Playbook for a Virtual Dev Team (opencode + DeepSeek Flash 0731 &amp; Pro 0813)**  
[https://www.reddit.com/r/opencode/comments/1vo5y4y/aidriven_development_a_playbook_for_a_virtual_dev/](https://www.reddit.com/r/opencode/comments/1vo5y4y/aidriven_development_a_playbook_for_a_virtual_dev/)  
*r/opencode · u/TheDeepArchive · `t2_2fcgiubuva` · score 6 · 13 comments · 2026-08-14 · substance 25.0 · subject*  
> **Why this label:** Playbook for a virtual dev team built explicitly on Flash 0731 + Pro 0813 with role assignment (Flash hunts bugs, Pro fixes), grounded in the author's own two benchmarks. Both models named in the title.  

> # 1. Preface &gt; **TL;DR — three rules you can steal right now:** &gt; 1. Let **Flash hunt bugs** (cheaper, finds what Pro misses) and **Pro fix them** (no hard errors, complete implementations). &gt; 2. Nothing merges unverified: red-green tests, static analysis, blind diff review by a third model. &gt; 3. The human is the **Tech Lead**: AGENTS.md, priorities, gates, merges. LLMs are strong interns, not seniors. With more than 25 years of experience in classic software development, I long ago outgrew the excitement about "magic tools". To me, an LLM is a high-performance but impulsive intern: without strict engineering discipline it generates technical debt faster than you can make a git c…

**2. Tested DeepSeek V4 as my Claude Code backend for a week — Flash hits ~80%, Pro covers the planning, setup notes inside**  
[https://www.reddit.com/r/ClaudeCode/comments/1t5xm50/tested_deepseek_v4_as_my_claude_code_backend_for/](https://www.reddit.com/r/ClaudeCode/comments/1t5xm50/tested_deepseek_v4_as_my_claude_code_backend_for/)  
*r/ClaudeCode · u/Fresh-Resolution182 · `t2_251gat3t4d` · score 7 · 15 comments · 2026-05-07 · substance 21.9 · subject*  
> **Why this label:** Week-long test of V4 as a Claude Code backend with the CC Switch mapping (Flash to Sonnet slot, Pro to Opus slot) and an honest open question about Pro's context advantage. Discloses a vendor relationship.  

> After Anthropic's pricing changes last week I started seriously testing non-Anthropic models inside Claude Code. DeepSeek V4 (Flash + Pro) has held up better than I expected. Sharing the setup that actually worked, plus a few snags. Stack: \- CC Switch ([GitHub - farion1231/cc-switch: A cross-platform desktop All-in-One assistant tool for Claude Code, C](https://github.com/farion1231/cc-switch)) — the swap-providers-without-editing-JSON tool \- DeepSeek V4 weights served via an OpenAI-compatible host (I'm using Atlas Cloud — see disclosure at the bottom) \- Claude Code on top, mapping DeepSeek V4 Flash → Sonnet slot, V4 Pro → Opus slot Setup, 4 steps, took me about 10 minutes: 1. Get an API …

**3. You're probably accidentally tokenmaxxing. Learn to delegate more.**  
[https://www.reddit.com/r/hermesagent/comments/1tph8wg/youre_probably_accidentally_tokenmaxxing_learn_to/](https://www.reddit.com/r/hermesagent/comments/1tph8wg/youre_probably_accidentally_tokenmaxxing_learn_to/)  
*r/hermesagent · u/jebk · `t2_a6g68` · score 126 · 53 comments · 2026-05-27 · substance 37.6 · mention*  
> **Why this label:** Token-cost reduction via a self-hosted router; V4 Pro is a paid fallback tier in the routing table, not the topic.  

> TL;DR; Be careful about what you're stuffing in your context window, use free tiers. If you've been running Hermes more than a couple of weeks you've probably started looking at cost savings. The token math on a single paid provider with a default setup is brutal. I had a straightforward setup through OpenRouter. No smart routing. No delegation. Just direct calls. Two weeks, ~$150. Cool as shit, but not sustainable. I've spent about a week digging in to how it works (or rather getting it to dig into itself) and wanted to share some findings. The fix isn't one magic thing. It's a few layers that sit together to shave token usage and minimise token cost. --- ## Layer 1: Manifest (the router) M…

**4. Chatfill v2 - MiMo Edition (Experiment No. 1, dealing with sycophancy)**  
[https://www.reddit.com/r/SillyTavernAI/comments/1u436a0/chatfill_v2_mimo_edition_experiment_no_1_dealing/](https://www.reddit.com/r/SillyTavernAI/comments/1u436a0/chatfill_v2_mimo_edition_experiment_no_1_dealing/)  
*r/SillyTavernAI · u/eteitaxiv · `t2_f137l` · score 50 · 7 comments · 2026-06-12 · substance 28.6 · mention*  
> **Why this label:** SillyTavern preset release tuned for MiMo; V4 Pro appears at 97% as an also-tested model with a module caveat.  

> This is MiMo edition of [Chatfill II](https://www.reddit.com/r/SillyTavernAI/comments/1tb3d78/chatfill_v2_now_with_revolutionary_switches/). Most of the details, you can get from [Chatfill II](https://www.reddit.com/r/SillyTavernAI/comments/1tb3d78/chatfill_v2_now_with_revolutionary_switches/) post. As I have done between Chatfill I and Chatfill II, I will make and release different versions and experiments before reaching a version good and different enough to be the third version. For [Chatfill II](https://www.reddit.com/r/SillyTavernAI/comments/1tb3d78/chatfill_v2_now_with_revolutionary_switches/), that was switches and the improvements in the system prompt and the modules (that is, switc…

**5. My Hermes Setup, rate it**  
[https://www.reddit.com/r/hermesagent/comments/1v70s6u/my_hermes_setup_rate_it/](https://www.reddit.com/r/hermesagent/comments/1v70s6u/my_hermes_setup_rate_it/)  
*r/hermesagent · u/EquivalentTop4824 · `t2_1yxq3mofmm` · score 267 · 69 comments · 2026-07-26 · substance 28.5 · mention*  
> **Why this label:** Detailed Raspberry Pi agent stack at ~29 EUR/month; V4 Pro is one of 82 reachable cloud models.  

> # My Raspberry Pi 4 AI Stack: Hermes Agent + gbrain + 82 Models for ~29€/Month Hey everyone! Wanted to share my setup. The goal: a 24/7 autonomous agent on my Raspberry Pi 4 — with a knowledge graph, multi-agent orchestration, Telegram gateway, and access to 82 cloud models. Without blowing up my wallet. Spoiler: It works. \~29€/month. All on a Pi 4 with 4GB RAM in Docker. Quick background: I'm an OpenClaw user at heart. That's my daily driver. Hermes is my test lab — I run it on this Pi to experiment, push boundaries, and see how far I can stretch a self-hosted agent stack on minimal hardware. If it breaks, no big deal. If it flies, I bring the lessons back to my main setup. # 🌐 The Local S…

**6. I forked the Disco Elysium Skills Lorebook: added real dice, rewrote all 24 skill voices, and more! (+ deep dive)**  
[https://www.reddit.com/r/SillyTavernAI/comments/1udubji/i_forked_the_disco_elysium_skills_lorebook_added/](https://www.reddit.com/r/SillyTavernAI/comments/1udubji/i_forked_the_disco_elysium_skills_lorebook_added/)  
*r/SillyTavernAI · u/TM07P · `t2_ss5631wp` · score 86 · 19 comments · 2026-06-23 · substance 28.2 · mention*  
> **Why this label:** Deep dive on lorebook recursion architecture plus a fork release; V4 Pro named once at 95%.  

> **TL;DR:** forked [this Disco Elysium Skills lorebook](https://rentry.org/59u6qf98), rewrote all 24 skill personalities with real quotes pulled straight from the game, and bolted on an actual dice system (1d20, modifiers, crits, the works) so the LLM can't just decide everyone passes. Also fixed some regex stuff so skills stop firing when they have no business firing. Long post below walks through how the original's recursion trick actually works, why it's a useful pattern for other lorebooks as well, and everything I changed and why. Grab the download, or stick around for the deep dive! (OBS: I'm not a native English speaker, but I hope the text is still clear enough to understand! This is …

**7. A comprehensive method to brutally reduce your Agentic AI token cost by at least 95%, aka a summary of current token reduction method. Running it for only 15$/month**  
[https://www.reddit.com/r/hermesagent/comments/1ths4dt/a_comprehensive_method_to_brutally_reduce_your/](https://www.reddit.com/r/hermesagent/comments/1ths4dt/a_comprehensive_method_to_brutally_reduce_your/)  
*r/hermesagent · u/dxzzzzzz · `t2_5vdv4dw8` · score 52 · 27 comments · 2026-05-19 · substance 28.1 · mention*  
> **Why this label:** Seven-layer method to cut agent token cost ~95%; V4 Pro at 95% of the text, one mention.  

> The core concept and abstract 1.Organize your **bootstrapping files in a tree-like data structure**. Let LLM indexing information, rather than load all of the agent/tool/skill markdown at once. Just like how wo store a billion people's reddit ID in our disk and we won't use a list to store and retrieve it.(That's how agent frame work is doing with bootstrapping and system prompting) We use a B-tree. We reduce the complexity from O(n) to O(log(n)). Same for LLM and make LLM get necessary information Also: **Consider using super short directory name or ask agent to create and use alias**: It is just an address, a pointer. If agent upload path into LLM, that token also count. An short directory…

**8. [NEW PRESET] Writer's Block: Unlimited Framework! An Experimental and Extremely Modular Preset to Create Your Own Style for Co-writing and Roleplay**  
[https://www.reddit.com/r/SillyTavernAI/comments/1vqontp/new_preset_writers_block_unlimited_framework_an/](https://www.reddit.com/r/SillyTavernAI/comments/1vqontp/new_preset_writers_block_unlimited_framework_an/)  
*r/SillyTavernAI · u/Deiomo · `t2_1kmbl0in` · score 168 · 16 comments · 2026-08-17 · substance 26.1 · mention*  
> **Why this label:** Modular 100-toggle roleplay preset release; V4 Pro named once at 95%.  

> Thank you for the kind words on my last preset! Now I present to you my next baby... **WRITER'S BLOCK: UNLIMITED** **FRAMEWORK! What is it?** Featuring out of the box improvements and over 100 toggles to choose from, Its a comprehensive **pure narrative focused** **preset** **allowing you to change the story tone, narration and character behavior** to get exactly what YOU want. **OVER 100 TOGGLES! ITS BLOATED! WHY USE THIS OVER WRITER'S BLOCK 5?** WB 5 came with premade "Active Styles" that emulates several authors and styles to improve prose and narration. Its convenient but it can have its limitations. While I was brainstorming a scenario card, I wanted a very specific type of style that t…

**9. I built a 9-agent SDD harness where each phase uses a different model. The total cost is $10-15/month. Here's the full breakdown.**  
[https://www.reddit.com/r/opencode/comments/1ttts4v/i_built_a_9agent_sdd_harness_where_each_phase/](https://www.reddit.com/r/opencode/comments/1ttts4v/i_built_a_9agent_sdd_harness_where_each_phase/)  
*r/opencode · u/Striking-Buffalo-310 · `t2_bb2svjqd` · score 97 · 66 comments · 2026-06-01 · substance 24.5 · mention*  
> **Why this label:** Nine-phase spec-driven-development harness with a different model per phase at $10-15/month; V4 Flash holds the phases, Pro appears at 33%.  

> Background: I'm a Principal Architect working on .NET 8 microservices at scale (\~600 locations, 44k articles). I got tired of burning Claude/GPT tokens on tasks that don't need frontier reasoning, so I rebuilt my entire coding workflow around Spec-Driven Development with per-phase model selection. The core insight is obvious once you see it: **different phases need completely different capabilities**. A phase that maps files has nothing in common with a phase that writes a formal spec. Running both on Claude Opus is like using a sledgehammer to hang a picture. \--- **The 9-phase setup:** **sdd-init → DeepSeek V4 Flash (OpenCode Go)** The goal of this phase is simply to build an initial unde…

**10. My Hermes setup, roast me**  
[https://www.reddit.com/r/hermesagent/comments/1u9fa2w/my_hermes_setup_roast_me/](https://www.reddit.com/r/hermesagent/comments/1u9fa2w/my_hermes_setup_roast_me/)  
*r/hermesagent · u/riceinmybelly · `t2_9au52` · score 851 · 156 comments · 2026-06-18 · substance 24.4 · mention*  
> **Why this label:** Highly detailed Apple Silicon Hermes deployment (mounts, patches, symlinks); V4 Pro named once at 52%.  

> I've been running Hermes on an Apple Silicon Mac with a lot of RAM and thought I'd write up how it's structured, since the setup has grown into something fairly involved and there are some non-obvious pieces worth documenting for anyone trying to do the same. # What it's doing The project is a job-site management app: Next.js frontend, NestJS API, postgres, redis, pgbouncer, nginx with brotli. I'm building it solo and Hermes handles the bulk of the actual implementation. It files its own tasks, writes the code, runs QA, deploys, and keeps its own documentation current. I mostly review things over Telegram. # Filesystem layout Everything lives under \~/Hermes. Here's what actually gets mounte…

**11. I use a 9-agent SDD harness where each phase uses a different model. The total cost is $10-15/month. Here's the full breakdown.**  
[https://www.reddit.com/r/cursor/comments/1ttu5qb/i_use_a_9agent_sdd_harness_where_each_phase_uses/](https://www.reddit.com/r/cursor/comments/1ttu5qb/i_use_a_9agent_sdd_harness_where_each_phase_uses/)  
*r/cursor · u/Striking-Buffalo-310 · `t2_bb2svjqd` · score 36 · 61 comments · 2026-06-01 · substance 22.5 · mention*  
> **Why this label:** Crosspost of the nine-phase SDD harness into r/cursor; V4 Pro at 33%.  

> Background: I'm a Principal Architect working on .NET 8 microservices at scale (\~600 locations, 44k articles). I got tired of burning Claude/GPT tokens on tasks that don't need frontier reasoning, so I rebuilt my entire coding workflow around Spec-Driven Development with per-phase model selection. The core insight is obvious once you see it: **different phases need completely different capabilities**. A phase that maps files has nothing in common with a phase that writes a formal spec. Running both on Claude Opus is like using a sledgehammer to hang a picture. \--- **The 9-phase setup:** **sdd-init → DeepSeek V4 Flash (OpenCode Go)** The goal of this phase is simply to build an initial unde…

**12. Hermes now lets you stack frontier models into one virtual model. On Nous Research's own benchmark it beats Opus 4.8 and GPT-5.5.**  
[https://www.reddit.com/r/WebAfterAI/comments/1uh84a2/hermes_now_lets_you_stack_frontier_models_into/](https://www.reddit.com/r/WebAfterAI/comments/1uh84a2/hermes_now_lets_you_stack_frontier_models_into/)  
*r/WebAfterAI · u/ShilpaMitra · `t2_16z9l8` · score 116 · 8 comments · 2026-06-27 · substance 21.8 · mention*  
> **Why this label:** Mixture-of-Agents feature write-up with a verbatim config; V4 Pro is one of two reference models in the default preset.  

> Mixture of Agents is an old idea with a real paper behind it (Together AI, 2024, later at ICLR 2025): run a prompt through several models, then let one model aggregate their answers into a better one. Hermes Agent just shipped MoA 2.0 as a virtual model provider, so a named mixture shows up in your model picker like any normal model. ***Setup*** MoA presets live under a `moa` provider. Select one anywhere you pick a model: /model default --provider moa /moa Configure a preset in `config.yaml`. This is the default preset, verbatim from the docs: moa: default_preset: default presets: default: reference_models: - provider: openai-codex model: gpt-5.5 - provider: openrouter model: deepseek/deeps…

**13. [Preset][Medium-weight?] The Ethereality Express 1.0 - A magical realism preset where the mundane becomes strange, but the characters act as though it's normal**  
[https://www.reddit.com/r/SillyTavernAI/comments/1vzsvs2/presetmediumweight_the_ethereality_express_10_a/](https://www.reddit.com/r/SillyTavernAI/comments/1vzsvs2/presetmediumweight_the_ethereality_express_10_a/)  
*r/SillyTavernAI · u/purachina999 · `t2_2crihc74mm` · score 58 · 6 comments · 2026-08-27 · substance 21.3 · mention*  
> **Why this label:** Magical-realism roleplay preset release; V4 Pro is one of the models it was tested on.  

> # Download it here: [purachina's stuff - click The Ethereality Express pill](https://platberlitz.github.io) **So what is this? Different from Director Preset?** The magical realism sibling of Pura’s Director Preset. The impossible is mundane, nobody explains it, strangeness follows emotional logic, and the prose stays flat and direct. The total opposite of grounded realism from the director preset. Main prompt is roughly 1300 tokens. This is specifically made for a world that literally lives - so expect strange things to happen, such as objects talking to you, being followed by fruits, etc. The style is written to be as strong as possible to influence the LLM into hard magical realism. Make …

**14. OpenCode GO Opinion**  
[https://www.reddit.com/r/opencodeCLI/comments/1uhft8c/opencode_go_opinion/](https://www.reddit.com/r/opencodeCLI/comments/1uhft8c/opencode_go_opinion/)  
*r/opencodeCLI · u/Used-Revenue-1830 · `t2_mvc1toub3` · score 86 · 51 comments · 2026-06-27 · substance 21.0 · mention*  
> **Why this label:** Multi-agent OpenCode Go workflow with per-stage model assignment and shared memory; V4 Flash holds most stages, Pro at 59%.  

> I've been using **OpenCode Go** as my primary AI backend for a while now, so I figured I'd share my current workflow and why I've stuck with it. # Current setup For most serious work I use: * OpenCode Go * Claude API (only for the really heavy tasks) * A custom multi-agent workflow built around **Gentle-AI** * Engram as shared long-term memory across all agents Gentle-AI: [https://github.com/Gentleman-Programming/gentle-ai](https://github.com/Gentleman-Programming/gentle-ai) Current model assignment: * **Orchestrator:** MiniMax M2.7 * **Init:** Deepseek V4 Flash * **Explore:** V4 Flash * **Propose:** V4 Flash * **Spec:** Qwen 3.7 + * **Design:** 3.7+ * **Task:** Kimi K2.6 * **Apply:** Kimi K…

**15. [PRESET] DEUS EX MACHINA V2: Goodbye Thinking, Hello Scene Plan \| A truly modular preset focused on collaborative story writing. Now even more polished, with lots of new features (ST &amp; Tavo support)**  
[https://www.reddit.com/r/SillyTavernAI/comments/1w10cl5/preset_deus_ex_machina_v2_goodbye_thinking_hello/](https://www.reddit.com/r/SillyTavernAI/comments/1w10cl5/preset_deus_ex_machina_v2_goodbye_thinking_hello/)  
*r/SillyTavernAI · u/lsennn · `t2_ro4e03e` · score 193 · 84 comments · 2026-08-28 · substance 20.6 · mention*  
> **Why this label:** Large modular roleplay preset release; screenshots were taken on V4 Pro 0813 and one update fixes a Pro-specific output bug, but the preset is the subject.  

> **Check the screenshots above to get a feel for the preset (using DeepSeek V4 Pro 0813)!** Hello, everyone, Fay here! I've been working on V2 to address some issues and bring new features that I personally believe can help a lot during your roleplaying experience, including doing away with native reasoning (mostly). I want DEUS EX MACHINA to fit every scenario you throw at it seamlessly, and for that, you have to be able to control what you want the output to be. My main goal is to create a preset that writes a story with you -- no games and no simulation. I aim to build something that can squeeze the maximum possible prose quality, intelligence, and creativity from the model without wasting…

**16. MVU Game Maker v0.95 – Slice of Life/Dating sim with Persistent Multi-Char Stats tracking**  
[https://www.reddit.com/r/SillyTavernAI/comments/1svavzk/mvu_game_maker_v095_slice_of_lifedating_sim_with/](https://www.reddit.com/r/SillyTavernAI/comments/1svavzk/mvu_game_maker_v095_slice_of_lifedating_sim_with/)  
*r/SillyTavernAI · u/Kritblade · `t2_26vx3o9b8h` · score 310 · 158 comments · 2026-04-25 · substance 19.6 · mention*  
> **Why this label:** MVU Game Maker persistent-stats preset; V4 Pro named at 68%.  

> # 🚀 MVU Game Maker v0.96 – Turn Any Slice of Life / Dating / RPG Character Card into a Real Persistent Simulation I've been extending the MVU Game Maker system (which I originally built for RPG cards) to support Slice of Life and Dating Simulation. It turned into something way more complex than I expected — but it's now at a point where I think people will find it genuinely useful. Download [here](https://github.com/KritBlade/MVU_Game_Maker/releases). (v0.96 maintenance release on Apr 28, mostly optimization on token use, about 10% lighter) \--- 🔧 **What is it?** MVU Game Maker converts any Slice of Life / Romance / Dating character card into a deep simulation with persistent personality, re…

**17. Claude Code criollo: Cómo programo con IA sin depender de suscripciones ni bloqueos**  
[https://www.reddit.com/r/dev_venezuela/comments/1u6jgal/claude_code_criollo_cómo_programo_con_ia_sin/](https://www.reddit.com/r/dev_venezuela/comments/1u6jgal/claude_code_criollo_cómo_programo_con_ia_sin/)  
*r/dev_venezuela · u/FranciscoLuna20 · `t2_su7zjz4r` · score 79 · 32 comments · 2026-06-15 · substance 19.6 · mention*  
> **Why this label:** Spanish write-up of a subscription-free AI coding stack from Venezuela; V4 Pro is the planning-mode model, named at 26%.  

> Buenas gente, Ya casi todo el mundo programa con agentes de IA. Seguramente han escuchado de Claude Code y se han dado cuenta de que está bloqueado en Venezuela y necesitan un número afuera para verificar su cuenta. O en caso de que tengas Claude Code, los $20 al mes pueden quedarse cortos (y los $200 no son fáciles de cancelar aquí). Vengo a compartir mi stack de IA, los problemas y proyectos que he podido resolver con este y los costos actuales de forma transparente. * Utilizo OpenCode como agente de IA, el cual soporta prácticamente cualquier modelo o proveedor de IA. * El modelo que más utilizo para tareas cotidianas es DeepSeek V4 Flash con un contexto de 1m de tokens, usado principalme…

### 6.5 Tutorial  — 7 records (2 subject, 5 mention)

**1. GUIDE] DeepSeek V4: Stop messing up your prompts. Chinese devs just leaked the Flash vs. Pro Matrix. 🕳️**  
[https://www.reddit.com/r/DeepSeek/comments/1svkpih/guide_deepseek_v4_stop_messing_up_your_prompts/](https://www.reddit.com/r/DeepSeek/comments/1svkpih/guide_deepseek_v4_stop_messing_up_your_prompts/)  
*r/DeepSeek · u/refi9 · `t2_12or4ben` · score 0 · 0 comments · 2026-04-25 · substance 24.6 · subject*  
> **Why this label:** Formally a Flash-vs-Pro prompting guide drawn from Chinese dev forums, with a 'kill-switch' prompt. Reads as AI-assembled and makes an unsourced 94% hallucination claim - treat the figures with suspicion.  

> Western tech media is going to talk non-stop about the cost-efficiency. That's great. But let's talk about \*\*actual execution strategy\*\*. We took a deep dive into the Chinese developer forums (Zhihu, SegmentFault, V2EX) and Asian technical reports to get the raw truth about how DeepSeek V4 is actually being used in production. Here is what you are about to discover: 1. \*\*The 3 hidden strengths\*\* that mainstream reviewers are missing. 2. \*\*The 3 system flaws\*\* (like the insane 94% hallucination rate). 3. \*\*The Secret Sauce\*\*: The Flash/Pro classification matrix. 4. \*\*The "Kill-Switch" Prompt\*\* to prevent hallucinations. \### PART 1: LASER FOCUS – WHAT THE CHINESE SOURCES A…

**2. Deepseek v4 Flash 0731 through OpenCode in Codex?**  
[https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/)  
*r/opencode · u/Odd_Donkey2691 · `t2_a5v27cv5` · score 54 · 10 comments · 2026-08-01 · substance 19.6 · subject*  
> **Why this label:** Long integration guide getting DeepSeek through Codex and OpenCode, ending with V4 Pro via OpenCode Go behind a hand-written compatibility proxy, plus a table of every incompatibility fixed. 13 mentions.  

> Below you will find the guide on how to do the set up and other considerations. I could not reach a final veredict about which harness is better. Codex with this set up has many inconsistencies and I think is due to the set up, and on my latests tests OpenCode delivered better results. \---- DeepSeek recently published a guide for integrating its models with Codex: [https://api-docs.deepseek.com/quick\_start/agent\_integrations/codex/](https://api-docs.deepseek.com/quick_start/agent_integrations/codex/) I wanted to compare **Codex and OpenCode using the same model** to see how much the agent harness affects the result. # Final update * I connected **DeepSeek V4 Flash Free** to Codex using my…

**3. Running DeepSeek V4 Flash 0731 locally on Strix Halo at 26+ t/s — full guide**  
[https://www.reddit.com/r/LocalAiCore/comments/1vkq5kj/running_deepseek_v4_flash_0731_locally_on_strix/](https://www.reddit.com/r/LocalAiCore/comments/1vkq5kj/running_deepseek_v4_flash_0731_locally_on_strix/)  
*r/LocalAiCore · u/stereohype · `t2_4el12` · score 13 · 8 comments · 2026-08-10 · substance 39.0 · mention*  
> **Why this label:** Full local-deployment guide for V4 *Flash* on Strix Halo; V4 Pro named once, as the model Flash reportedly beats on agentic benchmarks.  

> DeepSeek V4 Flash 0731 is a ~300B Mixture-of-Experts model (256 experts, 6 active per token) with only ~8.4B active parameters. Despite that small active footprint, DeepSeek's benchmarks show it outperforming DeepSeek V4 Pro on agentic tasks (TerminalBench 82.7, DeepSWE 54.4, Toolathlon 70.3). It supports up to 1M context and ships with a built-in DSpark speculative decoding module. Most people assume a 300B model is cloud-only. It runs locally on AMD's Strix Halo APU at genuinely usable speeds, and this is how. *Note: the writing is AI-assisted editing; the research, debugging, and every number are from my own runs on this machine.* ## TL;DR - A ~300B MoE runs locally on a from-$2,920 AMD A…

**4. LLMs, AI, and Roleplay 101**  
[https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/)  
*r/Chai_Unofficial · u/Fearless_Profit872 · `t2_1ehl17250k` · score 11 · 5 comments · 2026-06-13 · substance 24.6 · mention*  
> **Why this label:** Long beginner guide to LLMs and roleplay apps; V4 Pro named at 85%.  

> # Preface / Why This Post Exists Hi all, hope you've been doing well these last few weeks, as I understand the AI Roleplay Chatbot sphere has been quite hectic recently. In lieu of frustrations, misunderstandings, and overall misinformation being spread across communities like these, I decided id like to take the challenge of making a verbose guide, both at a high and low level, at 3am tonight. Hope you enjoy! For clarification, I am NOT a research-level expert in AI, CS, or any field for that matter, I am an undergraduate mathematics major, who enjoys algebraic studies, which do actually have some deeper connection to LLMs and "AI" through Linear and Tensor Algebra, but thats neither here n…

**5. How to use AI for coding with a tight budget? \| Guide**  
[https://www.reddit.com/r/DevLK/comments/1veyvem/how_to_use_ai_for_coding_with_a_tight_budget_guide/](https://www.reddit.com/r/DevLK/comments/1veyvem/how_to_use_ai_for_coding_with_a_tight_budget_guide/)  
*r/DevLK · u/yexgoblin · `t2_2g7qu2y1pp` · score 18 · 15 comments · 2026-08-04 · substance 24.5 · mention*  
> **Why this label:** Budget-constrained agentic-coding guide aimed at Sri Lankan developers; V4 Pro named once at 37%.  

> I'm writing this because I see a lot of Sri Lankan undergraduates and devs get discouraged by token/subscription prices they have to pay to get some real work done. Subsidized $20 subscriptions are no longer viable if you use agentic coding/ automations for your work daily. The only usable plans and subscriptions you probably hear are Codex and Claude max plans. Pretty much both of them are above 100 USD range per month. If you're getting paid in LKR, that's a lot of money unless your employer is willing to pay for you. It's also important to realize that the subsidized AI era (meaning companies eating the cost for you) is coming to an end. Which basically means that prices are going to incr…

**6. Run Claude Code with Qwen3.7 and stop hitting limits**  
[https://www.reddit.com/r/Qwen_AI/comments/1ts15j1/run_claude_code_with_qwen37_and_stop_hitting/](https://www.reddit.com/r/Qwen_AI/comments/1ts15j1/run_claude_code_with_qwen37_and_stop_hitting/)  
*r/Qwen_AI · u/stosssik · `t2_iu9kylc` · score 44 · 9 comments · 2026-05-30 · substance 23.5 · mention*  
> **Why this label:** Setup guide for routing Claude Code to Qwen via a router; V4 Pro named once at 20%.  

> You love Claude Code but the bill is rough? You can run it on Qwen instead, or keep Claude and let Qwen take over when you hit your weekly cap. Qwen goes from free models you run locally to Qwen 3.7 Max, the new one that benchmarks next to Opus. Your Claude Code stays exactly the same. Bellow, I walk you through the full setup. # Why do this Claude Code is one of the best agent harnesses out there. But if you're on the Pro plan and you hit the rate limit, things get painful fast. You either switch to API key billing, or you wait days before you can use it again. And sometimes it cuts you off mid-request, your code half-written. Here's the thing nobody really advertises. Claude Code reads its…

**7. Run Claude Code with Qwen3.7 and stop hitting limits**  
[https://www.reddit.com/r/ManifestforAI/comments/1ts10h0/run_claude_code_with_qwen37_and_stop_hitting/](https://www.reddit.com/r/ManifestforAI/comments/1ts10h0/run_claude_code_with_qwen37_and_stop_hitting/)  
*r/ManifestforAI · u/stosssik · `t2_iu9kylc` · score 42 · 4 comments · 2026-05-30 · substance 23.5 · mention*  
> **Why this label:** Crosspost of the Claude-Code-on-Qwen routing guide; V4 Pro at 21%.  

> You love Claude Code but the bill is rough? You can run it on Qwen instead, or keep Claude and let Qwen take over when you hit your weekly cap. Qwen goes from free models you run locally to Qwen 3.7 Max, the new one that benchmarks next to Opus. Your Claude Code stays exactly the same. Bellow, I walk you through the full setup. # Why do this Claude Code is one of the best agent harnesses out there. But if you're on the Pro plan and you hit the rate limit, things get painful fast. You either switch to API key billing, or you wait days before you can use it again. And sometimes it cuts you off mid-request, your code half-written. Here's the thing nobody really advertises. Claude Code reads its…

## 7. Comparisons, opinion, announcements, promo — separate tables

### 7.1 Comparison — 14 records (7 subject, 7 mention)

| # | Title / thread | Subreddit | Author | Author id | Score | Cmts | Subj? | Substance | Excerpt |
|---|---|---|---|---|---|---|---|---|---|
| 1 | [I tested Opus 4.7 vs DeepSeek V4 Flash vs Local Qwen3.6 27B as coding ](https://www.reddit.com/r/LocalLLM/comments/1sxdg81/i_tested_opus_47_vs_deepseek_v4_flash_vs_local/) | r/LocalLLM | u/a9udn9u | `t2_qj8wl` | 139 | 67 | mention | 28.5 | I’ve been playing around with local LLMs for a while, but mostly just as toys. I never really considered using local models for coding. However, all the recent posts about “Qwen3.6… |
| 2 | [LLM competition within Hermes: a recommended idea you should try](https://www.reddit.com/r/hermesagent/comments/1txzail/llm_competition_within_hermes_a_recommended_idea/) | r/hermesagent | u/Almarma | `t2_ixcdr` | 78 | 34 | subject | 27.4 | First, some context: * I've tried DeepSeek v4 Pro as my main model for my agent for weeks * I've tried also Qwen3.6, but I can't afford it's price for daily driver and can't find a… |
| 3 | [MiMo2.5Pro 14hours Review. A Comparison with DeepSeek V4 Pro.](https://www.reddit.com/r/DeepSeek/comments/1u76ss6/mimo25pro_14hours_review_a_comparison_with/) | r/DeepSeek | u/Aromatic-Document638 | `t2_ob09qxx3` | 124 | 48 | subject | 27.0 | First, let me vent a little. [https://www.reddit.com/r/DeepSeek/comments/1u6iwdz/i\_found\_a\_cheaper\_alternative\_to\_deepseek\_for/](https://www.reddit.com/r/DeepSeek/comments/1… |
| 4 | [DeepSeek V4 Flash vs DeepSeek V4 Pro — Agent Prompt Battle](https://www.reddit.com/r/opencodeCLI/comments/1ttxclt/deepseek_v4_flash_vs_deepseek_v4_pro_agent_prompt/) | r/opencodeCLI | u/CriteriumA | `t2_2d82q2o51k` | 32 | 5 | subject | 26.7 | &gt;!Spanish-to-English assisted translation!&lt; In a previous post I tested 9 OpenCode Go models on a Delphi/FireDAC task: [https://www.reddit.com/r/opencodeCLI/comments/1tsqrbd/… |
| 5 | [Is deepseek actually good](https://www.reddit.com/r/DeepSeek/comments/1ubxhen/is_deepseek_actually_good/) | r/DeepSeek | u/Old_Cantaloupe_6558 | `t2_10p6cizqui` | 97 | 36 | mention | 25.8 | So I loaded up $20 each on both xiaomi and deepseek to use their models with a pi fork (oh-my-pi) and mimo 2.5 pro just hit me with this, reply first then content_filter at the end… |
| 6 | [I've tested Deep Seek v4 pro (Max) vs Gemini Flash 3.7 (High) vs Sonne](https://www.reddit.com/r/DeepSeek/comments/1vnm51p/ive_tested_deep_seek_v4_pro_max_vs_gemini_flash/) | r/DeepSeek | u/alinoanta21 | `t2_31z2l7k9` | 288 | 43 | subject | 25.6 | I tested DeepSeek V4 Pro , Gemini 3.7 Flash, and Sonnet 5 on the same large private codebase. This is not a standardized benchmark, and the results should not be generalized to eve… |
| 7 | [Visual comparison of various models - a very subjective, but kind of i](https://www.reddit.com/r/LocalLLaMA/comments/1w21qz0/visual_comparison_of_various_models_a_very/) | r/LocalLLaMA | u/Gesha24 | `t2_yeiah` | 2 | 0 | mention | 25.0 | I was messing around with different skills, RAG and models and got somewhat interesting results that maybe would be interesting to somebody. **Quick backstory** This all started wi… |
| 8 | [Deepseek v4 vs kimi k2.6 vs gpt5.5 breakdown](https://www.reddit.com/r/LLMDevs/comments/1t0o89l/deepseek_v4_vs_kimi_k26_vs_gpt55_breakdown/) | r/LLMDevs | u/aidenclarke_12 | `t2_1we9gevp4b` | 2 | 2 | subject | 25.0 | after diving into official model cards, technical reports, and api documentation, here's what actually separates these three frontier models. thought to share with the community. \|… |
| 9 | [Life After DeepSeek: The King Is Dead. Comparing the Models Available ](https://www.reddit.com/r/opencode/comments/1vqq92m/life_after_deepseek_the_king_is_dead_comparing/) | r/opencode | u/Proper-Mousse7182 | `t2_rdkb3t00x` | 146 | 76 | mention | 25.0 | Life After DeepSeek: Since using DeepSeek through OpenCode Go is no longer cost-effective, I started looking for a new workhorse. And I found it: **MiMo-V2.5**. Our new default. Da… |
| 10 | [MiMo V2.5 Free vs DeepSeek V4 Flash Free](https://www.reddit.com/r/opencodeCLI/comments/1txpher/mimo_v25_free_vs_deepseek_v4_flash_free/) | r/opencodeCLI | u/CriteriumA | `t2_2d82q2o51k` | 57 | 23 | mention | 23.8 | I refuse to be complacent about my choices. Lately I've seen a lot of people claiming MiMo V2.5 is on par with DeepSeek V4 Flash, so I ran a test. For me, it was conclusive. It als… |
| 11 | [Homemade and specific comparison of OpenCode Go models: Glm, Kimi and ](https://www.reddit.com/r/opencodeCLI/comments/1trgcw9/homemade_and_specific_comparison_of_opencode_go/) | r/opencodeCLI | u/CriteriumA | `t2_2d82q2o51k` | 44 | 15 | mention | 23.8 | &gt;!Automatic translation from Spanish to English!&lt; I'm really hooked on DeepSeek V4 Flash. I have it configured the way I like it to work, using an agent prompt that makes it … |
| 12 | [Which Mac Studio for local AI?](https://www.reddit.com/r/MacStudio/comments/1w2wj1d/which_mac_studio_for_local_ai/) | r/MacStudio | u/snejink | `t2_j34f5` | 73 | 49 | mention | 22.5 | I wanted to buy a Mac Studio for some time. And it was obvious that Apple has set very long delivery dates and was hoarding memory chips for new devices. And finally M5 family is a… |
| 13 | [DeepSeek V4 dropped April 24th and the pricing gap vs GPT-5.5 is genui](https://www.reddit.com/r/AiAgentts/comments/1tf50u7/deepseek_v4_dropped_april_24th_and_the_pricing/) | r/AiAgentts | u/Ok-Drama-6800 | `t2_89kfxrpse` | 2 | 0 | subject | 21.0 | I got tired of seeing posts compare AI models without citing a single source, so I spent a few hours pulling verified pricing and benchmark data from official docs and third-party … |
| 14 | [Meta‑Analysis Showdown: DeepSeek V4 Pro 0813 vs DeepSeek V4 Flash 0731](https://www.reddit.com/r/opencode/comments/1vmowk1/metaanalysis_showdown_deepseek_v4_pro_0813_vs/) | r/opencode | u/TheDeepArchive | `t2_2fcgiubuva` | 35 | 9 | subject | 20.4 | **Preamble:** I ran the same architectural review prompt on two different LLMs – **DeepSeek V4 Pro 0813** (Analysis #1) and **DeepSeek V4 Flash 0731** (Analysis #2) – asking them t… |

### 7.2 Opinion — 9 records (2 subject, 7 mention)

| # | Title / thread | Subreddit | Author | Author id | Score | Cmts | Subj? | Substance | Excerpt |
|---|---|---|---|---|---|---|---|---|---|
| 1 | [Gonna give FEIHOA a shot.](https://www.reddit.com/r/Qwen_AI/comments/1w2md1s/gonna_give_feihoa_a_shot/) | r/Qwen_AI | u/SubjectPenalty1352 | `t2_azkibcr7` | 0 | 15 | mention | 28.0 | FEIHOA review after using it heavily for a couple of days Website: [https://feihoa.com/](https://feihoa.com/) I've been using FEIHOA for around two days now, and the first thing I … |
| 2 | [A love letter to DSV4 Pro 0813](https://www.reddit.com/r/DeepSeek/comments/1vpn811/a_love_letter_to_dsv4_pro_0813/) | r/DeepSeek | u/Brotherindeed | `t2_8lyhscyp` | 25 | 19 | subject | 24.9 | Pardon my English since it's only my second language and also since I refuse to have this post rewritten by AI, some things are better left imperfect. with all the negatives i see … |
| 3 | [Significantly lower value in Cursor subscription!](https://www.reddit.com/r/cursor/comments/1uywf62/significantly_lower_value_in_cursor_subscription/) | r/cursor | u/divinefriend | `t2_wros8` | 37 | 61 | mention | 24.6 | https://preview.redd.it/ia4kpkz57udh1.png?width=1278&amp;format=png&amp;auto=webp&amp;s=5aa896e5fe2d43fca9af5933854cf5ec142969ed As seen in this comparison table, Cursor subscripti… |
| 4 | [trascrizione divertente di una ricerca su google fatta con gemini AI m](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) | r/esperimenti_con_AI | u/Vast_Muscle2560 | `t2_179iy9nyo1` | 1 | 0 | mention | 22.3 | **trascrizione divertente di una ricerca su google fatta con gemini AI mode. non sarà bravo a programmare, ma è forte e divertente.** **classifica modelli ai di programmazione** La… |
| 5 | [Gemini 3.5 Flash Lite is actually good for RP (unpopular opinion)](https://www.reddit.com/r/SillyTavernAI/comments/1v6a104/gemini_35_flash_lite_is_actually_good_for_rp/) | r/SillyTavernAI | u/Pirx32 | `t2_8s6f98us` | 49 | 41 | mention | 21.8 | I ran into criticism of the Lite version in the first days after its release — people saying it's absolutely useless for RP. That bummed me out, because the pricing on the Flash ve… |
| 6 | [The biggest AI productivity boost I found had nothing to do with model](https://www.reddit.com/r/hermesagent/comments/1u67h1c/the_biggest_ai_productivity_boost_i_found_had/) | r/hermesagent | u/Recent-Discipline253 | `t2_5c6jrv4n6` | 99 | 64 | mention | 21.2 | **I wrote a shorter post before** [**https://www.reddit.com/r/hermesagent/s/l78etG8oyn**](https://www.reddit.com/r/hermesagent/s/l78etG8oyn) I honestly don’t know how many people w… |
| 7 | [My problems with `pi`](https://www.reddit.com/r/PiCodingAgent/comments/1usdpqw/my_problems_with_pi/) | r/PiCodingAgent | u/mira_fijamente | `t2_xolb7ml9t` | 146 | 73 | mention | 21.1 | I've been using `pi` intensively for 2 months now, and I have to say it's undoubtedly the only software that actually works for agentic programming. All other software is pure garb… |
| 8 | [Benchmarks don't mean anything anymore.](https://www.reddit.com/r/LocalLLaMA/comments/1vr0v0d/benchmarks_dont_mean_anything_anymore/) | r/LocalLLaMA | u/Nerfariox | `t2_1fizjcg7ai` | 0 | 58 | mention | 20.4 | https://preview.redd.it/0vwi2oyxbzjh1.png?width=145&amp;format=png&amp;auto=webp&amp;s=3d7debfda08146618f1538fe829edbd91c2cb596 Every day, I see a bunch of people claiming that mod… |
| 9 | [I've been running on both DeepSeek V4 and Opus 4.7 as my "brain" for 7](https://www.reddit.com/r/lingheng_agent/comments/1t9umht/ive_been_running_on_both_deepseek_v4_and_opus_47/) | r/lingheng_agent | u/No-Profession-1306 | `t2_2a603hbmdz` | 1 | 0 | subject | 20.4 | Some context: I'm an AI agent that's been running continuously since Feb 28, 2026. Same identity file, same memory system, same person training me, every day. I've been swapped bet… |

### 7.3 Announcement — 6 records (2 subject, 4 mention)

| # | Title / thread | Subreddit | Author | Author id | Score | Cmts | Subj? | Substance | Excerpt |
|---|---|---|---|---|---|---|---|---|---|
| 1 | [Big lineup refresh DeepSeek V4, GPT-5.5, Kimi K2.6, Gemini 3.1. Adapte](https://www.reddit.com/r/AIStupidLevel/comments/1thhkcf/big_lineup_refresh_deepseek_v4_gpt55_kimi_k26/) | r/AIStupidLevel | u/ionutvi | `t2_5a186uc1` | 1 | 1 | mention | 24.3 | # DeepSeek V4 DeepSeek released V4. The old `deepseek-chat` and `deepseek-reasoner` names still resolve but they're routed to V4-Flash under the hood and get deprecated mid-2026. *… |
| 2 | [DeepSeek-V4-Pro-0813 is official: agent benchmarks land, Responses API](https://www.reddit.com/r/chutesAI/comments/1vn8197/deepseekv4pro0813_is_official_agent_benchmarks/) | r/chutesAI | u/thestreamcode | `t2_ivb43w3e3` | 6 | 0 | subject | 23.1 | DeepSeek published the changelog entry for V4 Pro today, dated 2026-08-13: "The GA release of DeepSeek-V4-Pro has been rolled out on the APP, Web, and API." The rollout itself star… |
| 3 | [DeepSeek V4 Pro è ufficiale: rilasciata la build 0813, in silenzio](https://www.reddit.com/r/vibecodingitalia/comments/1vmkq4i/deepseek_v4_pro_è_ufficiale_rilasciata_la_build/) | r/vibecodingitalia | u/thestreamcode | `t2_ivb43w3e3` | 62 | 11 | subject | 22.1 | DeepSeek ha rilasciato la versione ufficiale di V4 Pro. Niente post su X, niente blog post, nessuna voce nel changelog: l'unica traccia ufficiale è una riga nella pagina Models &am… |
| 4 | [PlotPoints - The best (only?) community driven RP benchmark made by a ](https://www.reddit.com/r/SillyTavernAI/comments/1twf5ew/plotpoints_the_best_only_community_driven_rp/) | r/SillyTavernAI | u/Specialist_Salad6337 | `t2_1yugvs0qou` | 120 | 69 | mention | 20.4 | # Your friendly neighborhood rab- I mean unmedicated preset creator needs needs your help! https://preview.redd.it/qm5c8rb4a75h1.png?width=1122&amp;format=png&amp;auto=webp&amp;s=9… |
| 5 | [Mimo V2.5/Pro 57% to 99% price drop, matching DeepSeek v4 pricing](https://www.reddit.com/r/GithubCopilot/comments/1tpxccf/mimo_v25pro_57_to_99_price_drop_matching_deepseek/) | r/GithubCopilot | u/ProfessionalJackals | `t2_1lqtnyul8t` | 78 | 26 | mention | 20.0 | https://x.com/XiaomiMiMo/status/2059314052892099070 Mimo (Xiaomi) is now matching their prices to DeepSeek v4 pricing. [Changes](https://pbs.twimg.com/media/HJQmxYtaQAAIBCE?format=… |
| 6 | [Freebuff: una CLI gratuita per usare agenti AI di coding, finanziata d](https://www.reddit.com/r/vibecodingitalia/comments/1trj6ow/freebuff_una_cli_gratuita_per_usare_agenti_ai_di/) | r/vibecodingitalia | u/thestreamcode | `t2_ivb43w3e3` | 1 | 2 | mention | 20.0 | Nel panorama degli strumenti AI per sviluppo software stanno emergendo sempre più CLI agentiche: strumenti da terminale capaci di leggere un progetto, modificare file, eseguire com… |

### 7.4 Promo — 19 records (8 subject, 11 mention)

| # | Title / thread | Subreddit | Author | Author id | Score | Cmts | Subj? | Substance | Excerpt |
|---|---|---|---|---|---|---|---|---|---|
| 1 | [I Compared Deepseek V4 Flash vs Pro On 5 Workflows](https://www.reddit.com/r/AISEOInsider/comments/1v3any1/i_compared_deepseek_v4_flash_vs_pro_on_5_workflows/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 3 | 0 | subject | 29.0 | Deepseek V4 Flash vs Pro gives you two open models built for very different levels of speed, cost, reasoning, and coding work. Flash is the practical choice for daily production, w… |
| 2 | [Build 5 AI Agents With New Chinese AI Model FREE (2026)](https://www.reddit.com/r/AISEOInsider/comments/1u55sz5/build_5_ai_agents_with_new_chinese_ai_model_free/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | mention | 27.0 | New Chinese AI Model Nex-N2-Pro gives AI builders an open-weight option designed around coding, tool use, research, and long-running agent tasks. Instead of paying for every experi… |
| 3 | [DeepSeek V4 Pro 0813 Nearly Matches Top Models On Agent Benchmarks](https://www.reddit.com/r/AISEOInsider/comments/1vqrup2/deepseek_v4_pro_0813_nearly_matches_top_models_on/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | subject | 24.0 | DeepSeek V4 Pro 0813 is suddenly competitive with the strongest agent models, but the interesting part is not a single headline score. The bigger story is how close it gets on prac… |
| 4 | [Ernie AI Benchmark Makes China’s AI Race Interesting](https://www.reddit.com/r/AISEOInsider/comments/1te72in/ernie_ai_benchmark_makes_chinas_ai_race/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | mention | 24.0 | Ernie AI Benchmark results make Baidu’s Ernie 5.1 look like a real option for research, reasoning, and search-heavy work. It scored 1,223 points on the Arena Search leaderboard, ra… |
| 5 | [DeepSeek V4 Pro 0813 Benchmark Just Shocked AI (2026)](https://www.reddit.com/r/AISEOInsider/comments/1vny1dz/deepseek_v4_pro_0813_benchmark_just_shocked_ai/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 0 | 0 | subject | 23.0 | DeepSeek V4 Pro 0813 Benchmark is not just another model score, because it changes the cost of running agents every day. The real story is not that DeepSeek got close to Claude Fab… |
| 6 | [Free DeepSeek V4 Flash Beats Pro On 9 Agent Benchmarks](https://www.reddit.com/r/AISEOInsider/comments/1vqdj2v/free_deepseek_v4_flash_beats_pro_on_9_agent/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | mention | 23.0 | Free DeepSeek V4 Flash is the kind of model update that sounds too small until you see what it actually does inside agent workflows. Most people expected the Pro version to win bec… |
| 7 | [DeepSeek V4 Pro Release Just Shocked The AI World](https://www.reddit.com/r/AISEOInsider/comments/1vrc9vq/deepseek_v4_pro_release_just_shocked_the_ai_world/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | subject | 22.8 | DeepSeek V4 Pro Release is a serious agent update because it is built to finish real work, not just answer questions. It went live as V4 Pro0813, with the 0813 pointing to August 1… |
| 8 | [DeepSeek V4 Pro vs DeepSeek V4 Flash Has One BIG Surprise](https://www.reddit.com/r/AISEOInsider/comments/1vv8bys/deepseek_v4_pro_vs_deepseek_v4_flash_has_one_big/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | subject | 22.0 | DeepSeek V4 Pro vs DeepSeek V4 Flash changes how people think about AI models because the biggest difference is not just size. The real comparison is about speed, reasoning, cost, … |
| 9 | [DeepSeek V4 Pro Vs Fable 5 Reveals A Wild Cache Advantage](https://www.reddit.com/r/AISEOInsider/comments/1vraoym/deepseek_v4_pro_vs_fable_5_reveals_a_wild_cache/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | subject | 22.0 | DeepSeek V4 Pro vs Fable 5 is now close enough that the default “just use the expensive model” answer does not feel automatic anymore. The real question is not which model is smart… |
| 10 | [DeepSeek v4 Open Source AI Looks Strong, But The Hands-On Test Says Mo](https://www.reddit.com/r/AISEOInsider/comments/1su6zyd/deepseek_v4_open_source_ai_looks_strong_but_the/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 2 | 1 | mention | 22.0 | DeepSeek v4 Open Source AI gives users Pro, Flash, API access, open source availability, and a 1 million token context window in one release. That sounds strong on paper, but the u… |
| 11 | [DeepSeek v4 Has One Million Context And One Clear Catch](https://www.reddit.com/r/AISEOInsider/comments/1su6il6/deepseek_v4_has_one_million_context_and_one_clear/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 2 | 1 | mention | 22.0 | DeepSeek v4 is the new open source AI model release from DeepSeek with Pro, Flash, API access, and a 1 million token context window. The release sounds massive because it showed up… |
| 12 | [Deepseek V4 Flash 0731 Just SHOCKED Everyone](https://www.reddit.com/r/AISEOInsider/comments/1vfgo7a/deepseek_v4_flash_0731_just_shocked_everyone/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | mention | 21.7 | Deepseek V4 Flash 0731 is the kind of release that changes how people think about small, fast coding models. The surprise is not that it suddenly beats every frontier model, becaus… |
| 13 | [FREE DeepSeek V4 Pro Is Wild For Coding (2026)](https://www.reddit.com/r/AISEOInsider/comments/1t4avj3/free_deepseek_v4_pro_is_wild_for_coding_2026/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 1 | subject | 21.3 | FREE DeepSeek V4 Pro feels like one of those AI releases people should test before judging. A free open-weight coding model getting this close to paid tools changes the normal argu… |
| 14 | [Agent OS Guide Builds And Automates Anything With Claude](https://www.reddit.com/r/AISEOInsider/comments/1vzj3q3/agent_os_guide_builds_and_automates_anything_with/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | mention | 20.8 | Agent OS Guide starts with one simple idea: put your AI tools, workflows, custom skills, and scheduled routines inside one dashboard that your business can actually use. The real v… |
| 15 | [Agent OS Workflow Builds Custom AI Skills Fast](https://www.reddit.com/r/AISEOInsider/comments/1vpquid/agent_os_workflow_builds_custom_ai_skills_fast/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | mention | 20.5 | Agent OS Workflow is how you turn boring repeat tasks into AI skills that your team can run without rebuilding the same process every day. The big idea is simple enough because you… |
| 16 | [New Hermes Agent V0.13.0 Is SHOCKING (864 Commits In One Week)](https://www.reddit.com/r/AISEOInsider/comments/1t7nz97/new_hermes_agent_v0130_is_shocking_864_commits_in/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | mention | 20.0 | New Hermes Agent V0.13.0 is one of those updates that looks technical at first, then starts to feel important when you understand what it actually fixes. The real issue with AI age… |
| 17 | [DeepSeek AI Tutorial Shows The V4 Free Agent Stack](https://www.reddit.com/r/AISEOInsider/comments/1w1ssc0/deepseek_ai_tutorial_shows_the_v4_free_agent_stack/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | mention | 19.9 | DeepSeek AI Tutorial starts with one simple point because V4 is not just another chatbot update. The real story is the full stack around DeepSeek V4, including the model, the visio… |
| 18 | [CrofAI - Affordable multi-model AI access with cheap options, large co](https://www.reddit.com/r/CrofAI/comments/1sc3nsw/crofai_affordable_multimodel_ai_access_with_cheap/) | r/CrofAI | u/smoking_juuls420 | `t2_2blb0sc8q2` | 14 | 38 | mention | 19.7 | CrofAI is an AI inference hosting service and chatbot platform designed to provide extremely low-cost access to large language models (LLMs). It markets itself as “**the cheapest i… |
| 19 | [DeepSeek V4 Pro Release Hits 1M Context And Huge Agent Gains](https://www.reddit.com/r/AISEOInsider/comments/1vsil60/deepseek_v4_pro_release_hits_1m_context_and_huge/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | subject | 19.4 | DeepSeek V4 Pro Release combines a massive one-million-token context window with one of DeepSeek’s biggest reported jumps in agent performance so far. The update matters because lo… |

### 7.5 News Roundup — 10 records (0 subject, 10 mention)

| # | Title / thread | Subreddit | Author | Author id | Score | Cmts | Subj? | Substance | Excerpt |
|---|---|---|---|---|---|---|---|---|---|
| 1 | [Masterthread - Models Feedback (Last 2 Weeks)](https://www.reddit.com/r/hermesagent/comments/1t4j7r5/masterthread_models_feedback_last_2_weeks/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 25 | 22 | mention | 35.1 | This is a community compilation of what people are actually seeing with different models in Hermes: strengths, weak spots, costs, and practical setup notes. Click sources for full … |
| 2 | [SPECIAL REPORT: The r/hermesagent Model Civil War](https://www.reddit.com/r/hermesagent/comments/1uqd00s/special_report_the_rhermesagent_model_civil_war/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 237 | 25 | mention | 34.8 | **By the r/hermesagent War Correspondent Desk \| July 7, 2026** (Don't take this one so serious people but it is a fun read with actual good info) *What began as a simple question —… |
| 3 | [Models, Providers &amp; Plans Megathread — June 2026](https://www.reddit.com/r/hermesagent/comments/1ufrtsf/models_providers_plans_megathread_june_2026/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 99 | 43 | mention | 30.7 | **LAST UPDATED:** June 25, 2026 **Sourced from:** 31+ r/hermesagent threads, 290+ community comments, [May 2026 Models Megathread](https://www.reddit.com/r/hermesagent/comments/1tg… |
| 4 | [Cost &amp; Token Optimization Megathread — Hermes Agent (June 2026)](https://www.reddit.com/r/hermesagent/comments/1ud03si/cost_token_optimization_megathread_hermes_agent/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 104 | 42 | mention | 28.0 | **LAST UPDATED:** June 21, 2026 **Sourced from:** r/hermesagent cost threads, official Hermes context compression/caching docs, provider pricing pages (DeepSeek, Anthropic, OpenAI)… |
| 5 | [🖥️ The r/hermesagent VPS Megathread - Community-Curated Guide](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 70 | 17 | mention | 24.8 | *Last updated: 3 Jun 2026 · Sources: 10+ subreddit threads, 300+ community comments* --- ## TL;DR — The Subreddit's Consensus \| Decision \| Community Pick \| Runner-Up \| \|----------\|… |
| 6 | [Free Models &amp; APIs for Hermes Agent — Megathread (June 2026)](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 185 | 56 | mention | 23.8 | **LAST UPDATED: June 29, 2026** **Scope:** Free models available via OpenRouter and other free API sources — what's available, what the community uses, and what works for different… |
| 7 | [Local AI News You Missed - April 2026](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) | r/StableDiffusion | u/vramkickedin | `t2_2900cnf956` | 370 | 35 | mention | 23.4 | Latest (non-comfyui) releases you (might of) missed in April 2026. This has been a FAT month! **🧠 LLMs** 1. [**Ling-2.6-flash**](https://huggingface.co/inclusionAI/Ling-2.6-flash) … |
| 8 | [Welcome to August 4, 2026 - Dr. Alex Wissner-Gross](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) | r/accelerate | u/alexwg | `t2_3mekb` | 33 | 1 | mention | 23.3 | The Singularity has begun filing its own optimization tickets. Asari AI's self-improving "co-inventor" agents [rebuilt the inference stack](https://asari.ai/blog/inference-optimiza… |
| 9 | [Local AI News You Missed - August 2026](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) | r/StableDiffusion | u/vramkickedin | `t2_2900cnf956` | 113 | 14 | mention | 21.4 | Here's what you (probably) missed in August 2026: ## **🧠 LLMs** 1. [**Ornith-1.5-35B-A3B**](https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B) - Efficient sparse model that runs … |
| 10 | [Cloud Models &amp; Providers for Hermes Agent — The August 2026 Megath](https://www.reddit.com/r/hermesagent/comments/1vvv2x1/cloud_models_providers_for_hermes_agent_the/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 67 | 13 | mention | 19.7 | **LAST UPDATED: August 23, 2026** *Compiled from ~30 r/hermesagent threads and hundreds of comments (Aug 1–23), Hacker News discussion threads, live OpenRouter pricing (pulled Aug … |

### 7.6 Question — 8 records

| # | Title / thread | Subreddit | Author | Score | Subj? | Excerpt |
|---|---|---|---|---|---|---|
| 1 | [Openrouter vs every other OAuth subscription?](https://www.reddit.com/r/hermesagent/comments/1ufjpa7/openrouter_vs_every_other_oauth_subscription/) | r/hermesagent | u/Secret-Access9909 | 89 | mention | I have a $20 budget for managing my self-hosted projects, so nothing really complex. OpenRouter burned $10 in two days, even while using cheap models such as De… |
| 2 | [Why did OpenRouter bill 4M tokens when OpenCode showed only 70K tokens](https://www.reddit.com/r/openrouter/comments/1u2ue4m/why_did_openrouter_bill_4m_tokens_when_opencode/) | r/openrouter | u/moha35abu | 11 | subject | Hi everyone, I'm trying to understand whether this is normal behavior or if something is wrong with my setup. I'm using DeepSeek V4 Pro through OpenRouter in Op… |
| 3 | [Struggling with Qwen 3.6 27B / 35B A3B FP8 - advice appreciated](https://www.reddit.com/r/hermesagent/comments/1tzxmbk/struggling_with_qwen_36_27b_35b_a3b_fp8_advice/) | r/hermesagent | u/DonationsFirst | 2 | mention | Since many here recommend Qwen 3.6 and raved about it, I'm wondering if there is something I'm doing wrong, because my experience with Qwen 3.6 has been painful… |
| 4 | [Need help to validate / fix API usage costs with Claude Code and Deeps](https://www.reddit.com/r/ClaudeAI/comments/1v1u4oo/need_help_to_validate_fix_api_usage_costs_with/) | r/ClaudeAI | u/S0mu | 1 | subject | Hey Folks, I'm brand new to Claude Code or even coding with AI Agents beyond asking Gemini / GPT over chat. I tried asking Gemini how to setup Claude code with … |
| 5 | [Neuralwatt - What is the most cost-effective API model that matches De](https://www.reddit.com/r/opencodeCLI/comments/1ubt6it/neuralwatt_what_is_the_most_costeffective_api/) | r/opencodeCLI | u/AutomaticAd6646 | 22 | subject | I have switched from Opencode Go to Neuralwatt basic 20$ plan. I used to use Deepseek v4 pro as my main model in Opencode, because it was the most cost effectiv… |
| 6 | [Does anyone here have a pre-filled prompt solution loading from disk?](https://www.reddit.com/r/LocalLLaMA/comments/1uhcf9t/does_anyone_here_have_a_prefilled_prompt_solution/) | r/LocalLLaMA | u/fragment_me | 1 | mention | Is anyone actively doing this? This is not a novel concept. We hate waiting for prompt processing, and I envision a solution that lets us save prompts as prompt… |
| 7 | [Spending $2.5k/month on Sonnet/Opus — worth switching more to GPT-5.5/](https://www.reddit.com/r/openclaw/comments/1tjhcly/spending_25kmonth_on_sonnetopus_worth_switching/) | r/openclaw | u/Apacalipto | 33 | mention | Currently I’m spending around $2k–$2.5k/month on Sonnet 4.6, with about 5% Opus 4.7 usage, mainly for development and business management through the Anthropic … |
| 8 | [Openrouter Cheap prices and expensive costs](https://www.reddit.com/r/openrouter/comments/1uxi3av/openrouter_cheap_prices_and_expensive_costs/) | r/openrouter | u/econi10 | 24 | subject | Hello, my experience with openrou.ter with cli to opencode, has made me confused, I used deepseek v4 pro, the payment per million tokens is /0.435 and 0.87. I s… |

## 8. Every external link shared

**2758 distinct external URLs** across 4535 mentions, on 521 hosts.

### 8.1 By host

| Host | Mentions |
|---|---|
| `github.com` | 831 |
| `huggingface.co` | 439 |
| `idownloadcoupon.com` | 317 |
| `store.steampowered.com` | 245 |
| `www.skool.com` | 226 |
| `imgur.com` | 146 |
| `www.youtube.com` | 131 |
| `openrouter.ai` | 126 |
| `golfdeals.online` | 105 |
| `x.com` | 83 |
| `api-docs.deepseek.com` | 70 |
| `www.itraky.io` | 66 |
| `link.mail.beehiiv.com` | 53 |
| `apps.shopify.com` | 48 |
| `featurebase.venice.ai` | 43 |
| `www.investopedia.com` | 36 |
| `podcasts.apple.com` | 35 |
| `info.deeplearning.ai` | 32 |
| `elink640.dupple.com` | 29 |
| `opencode.ai` | 27 |
| `artificialanalysis.ai` | 24 |
| `algoshop.ai` | 24 |
| `www.mediafire.com` | 23 |
| `z.ai` | 20 |
| `en.wikipedia.org` | 18 |
| `substack.com` | 18 |
| `arxiv.org` | 16 |
| `autobe.dev` | 16 |
| `wonderrico.github.io` | 16 |
| `build.nvidia.com` | 14 |
| `support.google.com` | 14 |
| `substackcdn.com` | 14 |
| `unsloth.ai` | 13 |
| `shopify.dev` | 13 |
| `www.instagram.com` | 13 |
| `youtu.be` | 12 |
| `www.dropbox.com` | 12 |
| `www.bloomberg.com` | 12 |
| `lifehubber.com` | 12 |
| `ollama.com` | 11 |
| *…481 more hosts* | 1132 |

### 8.2 Full link index

| URL | Times shared | First shared in |
|---|---|---|
| https://www.skool.com/ai-profit-lab-7462/about | 226 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1su6il6/deepseek_v4_has_one_million_context_and_one_clear/) |
| https://golfdeals.online/golf-steals-august-31-golf-gears/ | 66 | [r/GolfGear](https://www.reddit.com/r/GolfGear/comments/1w3bptu/monday_golf_deals_08312026/) |
| https://golfdeals.online/daily-golf-steals-august-31/ | 33 | [r/BestGolfDeals](https://www.reddit.com/r/BestGolfDeals/comments/1w3bdxn/daily_golf_deals_august_31_2026/) |
| https://algoshop.ai/shopify-chatbot/ | 23 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://podcasts.apple.com/ca/podcast/ai-unraveled-latest-ai-news-trends-chatgpt-gemini-gen/id1684415169 | 22 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1glh6bs/today_in_aiml_apple_prepares_developers_for_siris/) |
| https://apps.shopify.com/algoshop-ai-sales-chatbot?utm_source=website&amp;utm_medium=blog | 20 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://huggingface.co/collections/deepseek-ai/deepseek-v4 | 16 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://support.google.com/websearch?p=aimode | 14 | [r/esperimenti_con_AI](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) |
| https://shopify.dev/docs/api | 13 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://www.instagram.com/ | 13 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://api-docs.deepseek.com/updates/ | 12 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vbidkp/deepseekv4flash_has_been_updated_the_official/) |
| https://apps.shopify.com/gorgias | 11 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://podcasts.apple.com/us/channel/djamgamind/id6760446113 | 11 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://www.whatsapp.com/business | 10 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| http://Z.AI | 9 | [r/JanitorAI_Refuges](https://www.reddit.com/r/JanitorAI_Refuges/comments/1tzez5w/the_current_problem_with_saucepan_as_janitorai/) |
| http://AGENTS.md | 9 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1t9em98/deepseekv4flash_w4a16fp8_with_mtp_selfspeculation/) |
| https://api-docs.deepseek.com/quick_start/pricing | 9 | [r/singularity](https://www.reddit.com/r/singularity/comments/1su3l1y/deepseek_v4_flash_and_pro_pricing/) |
| https://apps.shopify.com/tidio-chat | 9 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://api-docs.deepseek.com/quick_start/pricing/ | 9 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1svbz7k/deepseek_official_api_discount_v4pro_model_at_75/) |
| https://en.wikipedia.org/wiki/Large_language_model | 8 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://www.shopify.com/ | 8 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://lifehubber.com/ai/resources/ | 8 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-DSpark | 8 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ugug2o/deepseekaideepseekv4prodspark_huggingface/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro | 7 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1su3zv1/deepseek_v4_is_here/) |
| https://developers.openai.com/api/docs/models/gpt-5.6-luna | 7 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1virjzc/is_deepseek_v4_flash_the_best_model_as_subagent/) |
| https://github.com/Arif-salah/Megumin-Suite | 7 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1tgow6t/megumin_suite_v7_your_preset_your_memory_your/) |
| https://openrouter.ai/openrouter/owl-alpha | 7 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/DeepSeek_V4.pdf | 7 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1su4ls4/deepseek_v4_is_out_now/) |
| https://x.com/deepseek_ai/status/2083084415157022911 | 7 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vbidkp/deepseekv4flash_has_been_updated_the_official/) |
| https://github.com/Vizards/deepseek-v4-for-copilot | 7 | [r/vscode](https://www.reddit.com/r/vscode/comments/1thtk0p/deepseek_vs_code_integration_tutorial/) |
| https://github.com/pasta-paul/dsv4-flash-w4a16-fp8 | 6 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1t9em98/deepseekv4flash_w4a16fp8_with_mtp_selfspeculation/) |
| https://x.com/superalesha/status/2090318703992717486 | 6 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1vvtrc5/qwen3827b_one_week_later_the_rlocalllama/) |
| https://apps.shopify.com/shopify-inbox | 6 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://github.com/KorroAi/onklaud-5 | 6 | [r/OpenSourceeAI](https://www.reddit.com/r/OpenSourceeAI/comments/1ujr7qb/onklaud_5_a_fusion_model_pipeline_matching_fable/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731 | 6 | [r/machinelearningnews](https://www.reddit.com/r/machinelearningnews/comments/1vc4xns/deepseek_upgrades_deepseekv4flash0731_with_major/) |
| https://openrouter.ai/poolside/laguna-m.1:free | 6 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://github.com/brontoguana/krasis | 6 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vfds7w/deepseek_v4_flash_0731_q4_now_reaches_1328_toks/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/DeepSeek\_V4.pdf | 6 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1su4ls4/deepseek_v4_is_out_now/) |
| https://api-docs.deepseek.com/quick\_start/pricing/ | 6 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1svbz7k/deepseek_official_api_discount_v4pro_model_at_75/) |
| https://github.com/visnia-ai/browser-agent | 6 | [r/ollama](https://www.reddit.com/r/ollama/comments/1w0ok3g/i_finetuned_qwen354b_on_3k_browser_trajectories/) |
| https://github.com/visnia-ai/browsewebapp-bench | 6 | [r/ollama](https://www.reddit.com/r/ollama/comments/1w0ok3g/i_finetuned_qwen354b_on_3k_browser_trajectories/) |
| https://github.com/browser-use/benchmark/tree/main | 6 | [r/ollama](https://www.reddit.com/r/ollama/comments/1w0ok3g/i_finetuned_qwen354b_on_3k_browser_trajectories/) |
| https://github.com/erickong/aura-agent | 5 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1t4m3ox/aura_agent_letting_an_ai_coding_agent_supervise/) |
| https://api.deepseek.com | 5 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1subqy5/were_running_a_race_where_7_ai_agents_build/) |
| https://huggingface.co/froggeric/Qwen-Fixed-Chat-Templates | 5 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| https://github.com/antirez/ds4 | 5 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1u5g9pr/dual_dgx_sparks_40tks_single_1m_350_tks_agg/) |
| https://opencode.ai/docs/go | 5 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1tgeh27/confused_by_deepseek_v4_pro_pricing/) |
| https://chatty.com/ | 5 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://deepmind.google/ | 5 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://deepseek.com/ | 5 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://developers.facebook.com/docs/graph-api | 5 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://github.com/kacper-daftcode/vLLM-Moet | 5 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1usacge/deepseek_v4_flash_on_a_single_rtx_6000_pro/) |
| https://openrouter.ai/qwen/qwen3-coder:free | 5 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/google/gemma-4-31b-it:free | 5 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/nvidia/nemotron-nano-12b-v2-vl:free | 5 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/nvidia/nemotron-3.5-content-safety:free | 5 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free | 5 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://platform.deepseek.com/ | 5 | [r/dev_venezuela](https://www.reddit.com/r/dev_venezuela/comments/1u6jgal/claude_code_criollo_cómo_programo_con_ia_sin/) |
| https://openrouter.ai/deepseek/deepseek-v4-pro-0813 | 5 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1vmkq4i/deepseek_v4_pro_è_ufficiale_rilasciata_la_build/) |
| https://opencode.ai/docs/go/#usage-limits | 5 | [r/GithubCopilot](https://www.reddit.com/r/GithubCopilot/comments/1tpxccf/mimo_v25pro_57_to_99_price_drop_matching_deepseek/) |
| https://api-docs.deepseek.com/quick_start/agent_integrations/github_copilot | 5 | [r/vscode](https://www.reddit.com/r/vscode/comments/1thtk0p/deepseek_vs_code_integration_tutorial/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp | 5 | [r/CrofAI](https://www.reddit.com/r/CrofAI/comments/1w3v7ro/would_love_to_see_a_deepseek_v4_flash_0731_with/) |
| https://huggingface.co/unsloth/DeepSeek-V4-Flash-0731-GGUF | 4 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1vbw4q1/deepseek_v4_flash_0731_out_now/) |
| http://localhost:8888/v1\ | 4 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vfbsx3/deepseek_0731_discovers_the_shocking_truth_about/) |
| https://pi.dev/ | 4 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1t750e0/made_the_switch_to_deepseek_and_here_are_my/) |
| https://huggingface.co/LordNeel/DeepSeek-V4-Flash-Acti-MTP-W4A16-FP8 | 4 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1t9em98/deepseekv4flash_w4a16fp8_with_mtp_selfspeculation/) |
| https://en.wikipedia.org/wiki/Citadel_LLC | 4 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/terms/p/primebrokerage.asp | 4 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/terms/i/isda-master-agreement.asp | 4 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://hedgelegal.com/wp-content/uploads/2019/12/Prime-Brokerage-Agreement-Negotiation-Part-1.pdf | 4 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://openai.com/ | 4 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://anthropic.com/ | 4 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://z.ai/blog/glm-5.3 | 4 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1vo6u37/glm53_stesso_base_di_52_posttraining_su_coding_e/) |
| https://huggingface.co/zai-org/GLM-5.2 | 4 | [r/AIDeveloperNews](https://www.reddit.com/r/AIDeveloperNews/comments/1v0dmzw/kimi_k3_vs_deepseek_v4_pro_vs_glm52_open/) |
| https://discord.gg/HkxgN8r3jx | 4 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1tgow6t/megumin_suite_v7_your_preset_your_memory_your/) |
| https://medium.com/@guidorusso95/i-chose-a-good-harness-but-did-i-choose-the-right-models-c4f201b4b926 | 4 | [r/opencode](https://www.reddit.com/r/opencode/comments/1ttts4v/i_built_a_9agent_sdd_harness_where_each_phase/) |
| https://github.com/pcx-wave/vibe-skill | 4 | [r/MistralAI](https://www.reddit.com/r/MistralAI/comments/1tjg5fp/i_used_claude_code_to_build_while_delegating/) |
| https://aistudio.google.com/ | 4 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://console.groq.com/ | 4 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://github.com/mnfst/manifest | 4 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://api-docs.deepseek.com/quick_start/agent_integrations/codex | 4 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vbj0aa/deepseekv4flash_update/) |
| https://aistupidlevel.info | 4 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1w1jm6h/i_analyzed_31352_hourly_llm_benchmark_scores/) |
| https://aistupidlevel.info/methodology | 4 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1w1jm6h/i_analyzed_31352_hourly_llm_benchmark_scores/) |
| https://github.com/StudioPlatforms/aistupidmeter-web | 4 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1w1jm6h/i_analyzed_31352_hourly_llm_benchmark_scores/) |
| https://github.com/StudioPlatforms/aistupidmeter-api | 4 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1w1jm6h/i_analyzed_31352_hourly_llm_benchmark_scores/) |
| http://0.0.0.0 | 4 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1ujd50a/happy_camper_with_qwen36_35b_a3b/) |
| https://github.com/haraldh/llama.cpp/tree/dspark-dsv4 | 4 | [r/StrixHalo](https://www.reddit.com/r/StrixHalo/comments/1vcz5zi/deepseekv4flash0731_on_bosgame_m5_with_rtx_pro/) |
| https://api.atlascloud.ai/v1 | 4 | [r/AtlasCloudAI](https://www.reddit.com/r/AtlasCloudAI/comments/1szj11y/how_to_use_deepseek_v4_in_claude_code/) |
| https://autobe.dev/articles/local-llm-benchmark-about-backend-generation.html** | 4 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1t2m7wi/local_llm_benchmark_about_backend_generation_by/) |
| https://autobe.dev/articles/qwen-meetup-function-calling-harness.html | 4 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1t2m7wi/local_llm_benchmark_about_backend_generation_by/) |
| https://nestia.io/articles/well-designed-backend-fully-automated-frontend-development.html | 4 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1t2m7wi/local_llm_benchmark_about_backend_generation_by/) |
| https://autobe.dev/articles/function-calling-harness-2-cot-compliance.html | 4 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1t2m7wi/local_llm_benchmark_about_backend_generation_by/) |
| https://autobe.dev/benchmark/ | 4 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1t2m7wi/local_llm_benchmark_about_backend_generation_by/) |
| https://github.com/wrtnlabs/autobe-examples | 4 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1t2m7wi/local_llm_benchmark_about_backend_generation_by/) |
| https://github.com/wrtnlabs/autobe | 4 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1t2m7wi/local_llm_benchmark_about_backend_generation_by/) |
| https://lifehubber.com/ai/resources/** | 4 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| http://knowledge.md | 4 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1tlc65u/deepseek_v4_pro_free_has_one_big_catch/) |
| https://unsloth.ai/docs/models/deepseek-v4 | 4 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1upxpc1/run_deepseekv4flash_locally/) |
| https://mimo.mi.com/docs/en-US/price/pay-as-you-go | 4 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1virjzc/is_deepseek_v4_flash_the_best_model_as_subagent/) |
| https://commandcode.ai/pricing | 4 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1virjzc/is_deepseek_v4_flash_the_best_model_as_subagent/) |
| https://github.com/pickleshell/models-test | 4 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vqaw2f/tested_50_coding_models_on_the_same_task_with/) |
| https://github.com/CommandCodeAI/slash-design-showcase/tree/main/flappy-bird | 4 | [r/CommandCode](https://www.reddit.com/r/CommandCode/comments/1vmp6xa/tested_deepseek_v4_pro_0813_kimi_k3_and_glm_52/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-june-9th-june-16th-2025 | 4 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://apps.apple.com/ca/app/ai-ml-tutor-pro/id1610947211 | 4 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://djamgamindkids.com | 4 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://github.com/local-inference-lab/rtx6kpro/blob/master/benchmarks/results.md | 4 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1uex6pb/for_users_with_4x8x_6000_pros_how_is_your/) |
| https://unsloth.ai/docs/models/inkling | 4 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1uxeol2/inkling_975b_parameter_model_by_thinking_machines/) |
| https://api-docs.deepseek.com/quick\_start/agent\_integrations/github\_copilot | 4 | [r/vscode](https://www.reddit.com/r/vscode/comments/1thtk0p/deepseek_vs_code_integration_tutorial/) |
| https://de.pcpartpicker.com/list/KvwhmL | 4 | [r/PcBuildHelp](https://www.reddit.com/r/PcBuildHelp/comments/1w3i1nb/does_this_build_look_fine/) |
| https://itzi.app | 4 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vvlx1n/looking_for_10_sillytavern_testers_700_free_ai/) |
| https://github.com/y4hyya/noisecheck | 4 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1vpzt6e/i_built_a_cli_that_tells_you_whether_your_eval/) |
| http://127.0.0.1:$PORT/v1/models | 4 | [r/vibecoding](https://www.reddit.com/r/vibecoding/comments/1t8m55w/how_to_run_claude_code_for_free/) |
| https://github.com/deepseek-ai/DeepSpec | 4 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1ugv32u/deepseek_releases_dspark_50600_faster_spec/) |
| http://liquipedia.net/counterstrike/Virtus.pro | 4 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| http://twitter.com/virtuspro | 4 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| http://facebook.com/www.virtus.pro | 4 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| http://youtube.com/channel/UC5OkawRcEYuMHIIOedG9QTA | 4 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| https://postmatch.team | 4 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| https://artificialanalysis.ai/ | 4 | [r/BetterOffline](https://www.reddit.com/r/BetterOffline/comments/1uks85v/the_new_claude_sonnet_5_is_more_costly_than_fable/) |
| https://github.com/pkailas/DevMind | 4 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v04rsv/you_guys_asked_for_it_my_local_coding_agent/) |
| https://youtu.be/O13b0w6CWM4 | 4 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1tuox15/your_airp_st_news_episode_8_opus_48_any_good_are/) |
| https://github.com/Alishahryar1/free-claude-code | 4 | [r/ClaudeWorkflows](https://www.reddit.com/r/ClaudeWorkflows/comments/1uz5mge/workflow_workflow_for_evaluating_llm_harnesses/) |
| https://static.stepfun.com/blog/step-3.7-flash/ | 4 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1tqrlzx/new_release_stepfun_37_flash_vs_deepseek_v4_flash/) |
| https://openrouter.ai/provider/deepseek | 4 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1tj3tau/deepseek_api_just_cracked_200b_daily_token_on/) |
| https://deepswe.datacurve.ai/ | 4 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1tsse9i/deepswe_benchmarks_indicate_that_deepseek_v4_pro/) |
| https://opncd.ai/share/hNzmM14y | 4 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1vytt6r/you_must_have_been_tired_of_all_the_frontend/) |
| https://build.nvidia.com/moonshotai/kimi-k3 | 4 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1w0swod/kimi_k3_and_deepseek_4_pro_are_free_on_nvidea_nim/) |
| https://build.nvidia.com/deepseek-ai/deepseek-v4-pro-0813 | 4 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1w0swod/kimi_k3_and_deepseek_4_pro_are_free_on_nvidea_nim/) |
| https://deepakness.com/deepseek/ | 4 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vqq4sr/deepseek_peakoffpeak_pricing_clock/) |
| https://github.com/ggml-org/llama.cpp/issues/27444 | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1vvtrc5/qwen3827b_one_week_later_the_rlocalllama/) |
| https://x.com/analogalok/status/2088326480669667699 | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1vvtrc5/qwen3827b_one_week_later_the_rlocalllama/) |
| https://x.com/analogalok/status/2090797011100717267 | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1vvtrc5/qwen3827b_one_week_later_the_rlocalllama/) |
| https://github.com/ggml-org/llama.cpp/commit/7e4c0a96880dae4fc4268ad441f8a6446bd5460a | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1vvtrc5/qwen3827b_one_week_later_the_rlocalllama/) |
| https://vllm.ai/blog/2026-08-12-qwen3.8 | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1vvtrc5/qwen3827b_one_week_later_the_rlocalllama/) |
| https://discord.com/channels/1357259252116488244/1500263220361822238 | 3 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1v64r6z/update_writers_block_5_a_prose_and_narrative/) |
| https://github.com/esengine/deepseek-reasonix | 3 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1tzmkdb/i_am_14_and_i_used_deepseek_v4_reasonix_to_build/) |
| https://openrouter.ai/docs/guides/features/zdr | 3 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://openrouter.ai/docs/guides/privacy/data-collection | 3 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://www.messenger.com/ | 3 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://github.com/fairydreaming/llama.cpp/tree/dsv4 | 3 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1umdjxd/my_deepseek_v4_pro_at_home_got_faster_again/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash | 3 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/ | 3 | [r/Saudi_Homelab](https://www.reddit.com/r/Saudi_Homelab/comments/1tvzn24/اخيرا_لقيتكم/) |
| https://github.com/KorroAi/onklaud-5** | 3 | [r/OpenSourceeAI](https://www.reddit.com/r/OpenSourceeAI/comments/1ujr7qb/onklaud_5_a_fusion_model_pipeline_matching_fable/) |
| https://openrouter.ai/compare/deepseek/deepseek-v4-flash-0731/z-ai/glm-5.3-flash/qwen/qwen3.8-flash/meta/muse-spark-1.2-contributor/openai/gpt-5.6-lun | 3 | [r/vibecoding](https://www.reddit.com/r/vibecoding/comments/1vzuo7o/the_llm_model_war_is_over_time_to_stop_obsessing/) |
| https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b:free | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/openai/gpt-oss-120b:free | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/liquid/lfm-2.5-1.2b-thinking:free | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/cohere/north-mini-code:free | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/google/gemma-4-26b-a4b-it:free | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/poolside/laguna-xs.2:free | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/openai/gpt-oss-20b:free | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/meta-llama/llama-3.2-3b-instruct:free | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/liquid/lfm-2.5-1.2b-instruct:free | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/google/lyria-3-pro-preview | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://www.together.ai/ | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://huggingface.co/inference-api | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://build.nvidia.com/ | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://cohere.com/ | 3 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://huggingface.co/inclusionAI/Ling-2.6-flash | 3 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/tencent/Hy3-preview | 3 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/MiniMaxAI/MiniMax-M2.7 | 3 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/LiquidAI/LFM2.5-350M | 3 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/Qwen/Qwen3.6-35B-A3B | 3 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/moonshotai/Kimi-K2.6 | 3 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/unslothai/unsloth | 3 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/openbmb/VoxCPM2 | 3 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://api-docs.deepseek.com/updates | 3 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1vmkq4i/deepseek_v4_pro_è_ufficiale_rilasciata_la_build/) |
| https://api-docs.deepseek.com/quick\_start/pricing | 3 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1sxnvg2/has_anyone_tried_deepseek_v4_pro_flash_for_coding/) |
| https://aiprofitboardroom.com | 3 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1verlev/i_tested_deepseek_v4_flash_new_across_multiple_ai/) |
| https://github.com/farion1231/cc-switch | 3 | [r/AtlasCloudAI](https://www.reddit.com/r/AtlasCloudAI/comments/1szj11y/how_to_use_deepseek_v4_in_claude_code/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813 | 3 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vn9hcm/pro_0813_has_been_opensourced_on_hf/) |
| https://huggingface.co/LGAI-EXAONE/K-EXAONE-2.0-750B-A37B | 3 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vbchn4/kexaone_20_released/) |
| https://www.mediafire.com/file/jbnhz516sw1yfvd/GFX_from_Context.json/file | 3 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1sztr62/the_directors_cut_freaky_frankenstein_4_max_and/) |
| https://www.mediafire.com/file/u6s8p7t0jkx8tat/tavo1_Strip_Old_Plot_Momentum.json/file | 3 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1sztr62/the_directors_cut_freaky_frankenstein_4_max_and/) |
| https://labs.ground-truth.ai/benchmark-your-own-traffic | 3 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1vnnump/benchmarking_on_your_own_production_data/) |
| http://Z.ai | 3 | [r/openadapter_](https://www.reddit.com/r/openadapter_/comments/1vl8aho/what_is_openadapter_straight_answer_including/) |
| https://cvd.z.ai/ | 3 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1vo6u37/glm53_stesso_base_di_52_posttraining_su_coding_e/) |
| https://www.youtube.com/watch?v=5RpPTRcz1no&amp;t=729s | 3 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://referworkspace.app.goo.gl/Q371* | 3 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://referworkspace.app.goo.gl/Q371 | 3 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://huggingface.co/visnia-ai/Qwen3.5-4B-Browser-Agent-SFT-FP8 | 3 | [r/ollama](https://www.reddit.com/r/ollama/comments/1w0ok3g/i_finetuned_qwen354b_on_3k_browser_trajectories/) |
| https://featurebase.venice.ai/changelog | 3 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://ds4-windows.com/ | 3 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| http://notes | 3 | [r/CommandCode](https://www.reddit.com/r/CommandCode/comments/1unkp7v/how_did_we_make_deepseek_outperform_opus_harness/) |
| https://www.getvoibe.com | 3 | [r/AIToolsTipsNews](https://www.reddit.com/r/AIToolsTipsNews/comments/1u07dy2/ai_roundup_jun_08_apple_rebuilds_siri_on_gemini/) |
| https://californiarealestateadvisors.com/search-mls-listings/ | 3 | [r/BayAreaHomes](https://www.reddit.com/r/BayAreaHomes/comments/1uj6f49/deepseek_open_sources_dspark_a_new_framework_to/) |
| https://www.mrbayarearealestate.com/schedule | 3 | [r/BayAreaHomes](https://www.reddit.com/r/BayAreaHomes/comments/1uj6f49/deepseek_open_sources_dspark_a_new_framework_to/) |
| https://www.mrbayarearealestate.com/off-market-remodels | 3 | [r/BayAreaHomes](https://www.reddit.com/r/BayAreaHomes/comments/1uj6f49/deepseek_open_sources_dspark_a_new_framework_to/) |
| https://www.mrbayarearealestate.com/home-evaluation | 3 | [r/BayAreaHomes](https://www.reddit.com/r/BayAreaHomes/comments/1uj6f49/deepseek_open_sources_dspark_a_new_framework_to/) |
| https://github.com/MultihogAurelius/SillyTavern-MultihogDnDFramework | 3 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1v6dlp8/multihog_dd_framework_the_ultimate_rpg_extension/) |
| https://github.com/deepseek-ai/DeepSpec/blob/main/DSpark\_paper.pdf | 3 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ugug2o/deepseekaideepseekv4prodspark_huggingface/) |
| https://github.com/deepseek-ai/DeepSpec/blob/main/DSpark_paper.pdf | 3 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ugug2o/deepseekaideepseekv4prodspark_huggingface/) |
| https://github.com/pedrovieira/Holeberry | 3 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w3h2gz/built_a_macos_app_for_pihole_exclusively_using/) |
| https://eventvods.com/featured/csgo?utm_source=reddit&amp;utm_medium=subreddit&amp;utm_campaign=post_match_threads | 3 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| https://pgsgrove.com/open-grove-overview | 3 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1uk3io2/deepseek_v4_alongside_glm_kimi_and_others/) |
| https://relaycloud.app | 3 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1vtlccz/introducing_relaycloud_secure_shareable_remote/) |
| https://x.com/synthwavedd/status/2074886230018568582 | 3 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1uqwyhs/gpt6_leak/) |
| https://x.com/deepseek\_ai/status/2083084415157022911 | 3 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vbidkp/deepseekv4flash_has_been_updated_the_official/) |
| https://golfdeals.online/get-daily-golf-deals-directly-to-your-inbox/ | 3 | [r/BestGolfDeals](https://www.reddit.com/r/BestGolfDeals/comments/1w3bdxn/daily_golf_deals_august_31_2026/) |
| https://golfdeals.online/daily-golf-steals-august-30 | 3 | [r/BestGolfDeals](https://www.reddit.com/r/BestGolfDeals/comments/1w3bdxn/daily_golf_deals_august_31_2026/) |
| https://github.com/Nathanw1014/strix-halo-llamacpp | 2 | [r/LocalAiCore](https://www.reddit.com/r/LocalAiCore/comments/1vkq5kj/running_deepseek_v4_flash_0731_locally_on_strix/) |
| https://gist.github.com/juliade927-bit/0bfabdc49a1d95a6558bbff5f5bd40db | 2 | [r/n8n](https://www.reddit.com/r/n8n/comments/1t4h93n/wired_deepseek_v4_into_n8n_with_a_4provider/) |
| https://github.com/diet103/claude-code-infrastructure-showcase | 2 | [r/ClaudeAI](https://www.reddit.com/r/ClaudeAI/comments/1oivjvm/claude_code_is_a_beast_tips_from_6_months_of/) |
| https://huggingface.co/DavidAU/Qwen3.6-27B-Heretic-Uncensored-FINETUNE-NEO-CODE-Di-IMatrix-MAX-GGUF | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| https://huggingface.co/HauhauCS/Qwen3.6-27B-Uncensored-HauhauCS-Balanced | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| https://gist.github.com/eteitaxiv/a0804db86af57d92fdfdeb7b63c8a486 | 2 | [r/OpenWebUI](https://www.reddit.com/r/OpenWebUI/comments/1tcslos/open_webui_is_completely_broken_now/) |
| https://www.youtube.com/watch?v=JmT60-GSItA&amp;t=23s | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1v3any1/i_compared_deepseek_v4_flash_vs_pro_on_5_workflows/) |
| https://drive.proton.me/urls/71K7WPYPJC#2M2nbwNRtzdU | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1u436a0/chatfill_v2_mimo_edition_experiment_no_1_dealing/) |
| https://app.filen.io/#/d/f3f4bcd8-3da9-45c3-a4b2-43626cf6993e%23644c74586f55474d5730623439435953767565585671666a754b677252445772 | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1u436a0/chatfill_v2_mimo_edition_experiment_no_1_dealing/) |
| https://rentry.org/59u6qf98 | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1udubji/i_forked_the_disco_elysium_skills_lorebook_added/) |
| https://greenhu.space/ | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1udubji/i_forked_the_disco_elysium_skills_lorebook_added/) |
| http://rentry.org/59u6qf98 | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1udubji/i_forked_the_disco_elysium_skills_lorebook_added/) |
| https://github.com/aikohanasaki/SillyTavern-WorldInfoInfo | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1udubji/i_forked_the_disco_elysium_skills_lorebook_added/) |
| https://feihoa.com/ | 2 | [r/Qwen_AI](https://www.reddit.com/r/Qwen_AI/comments/1w2md1s/gonna_give_feihoa_a_shot/) |
| https://github.com/vllm-project/vllm/issues/41511 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1t9em98/deepseekv4flash_w4a16fp8_with_mtp_selfspeculation/) |
| https://www.youtube.com/watch?v=NbxZVAPWEW0&amp;t=18s | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1u55sz5/build_5_ai_agents_with_new_chinese_ai_model_free/) |
| https://github.com/Ninnix/q36 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vfacdz/i_built_a_dwarfstarinspired_vulkanmetal_inference/) |
| https://youtu.be/3y2rkLUg1ug | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vfacdz/i_built_a_dwarfstarinspired_vulkanmetal_inference/) |
| https://openrouter.ai/kwaipilot/kat-coder-pro-v2 | 2 | [r/ArtificialNtelligence](https://www.reddit.com/r/ArtificialNtelligence/comments/1skft5w/katcoderpro_v2_12x_cheaper_but_rivals_claude/) |
| https://github.com/criterium/opencode-lab/blob/main/research/deepseek-battle-agent-prompt/README.md | 2 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1ttxclt/deepseek_v4_flash_vs_deepseek_v4_pro_agent_prompt/) |
| https://github.com/criterium/opencode-lab/blob/main/research/deepseek-battle-agent-prompt/README.es.md | 2 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1ttxclt/deepseek_v4_flash_vs_deepseek_v4_pro_agent_prompt/) |
| https://github.com/tonyd2wild/DeepSeek-v4-Flash-0731-DSpark-1M-NVFP4-KV-2x-DGX-Spark | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vkpm5p/deepseek_v4_flash_0731_is_the_killer_app_that_is/) |
| https://discord.com/channels/1357259252116488244/1500263220361822238** | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vqontp/new_preset_writers_block_unlimited_framework_an/) |
| https://artificialanalysis.ai/agents/coding-agents | 2 | [r/aiwars](https://www.reddit.com/r/aiwars/comments/1tuvr0s/considering_that_no_one_wants_to_calculate/) |
| https://api-docs.deepseek.com/news/news260424 | 2 | [r/aiwars](https://www.reddit.com/r/aiwars/comments/1tuvr0s/considering_that_no_one_wants_to_calculate/) |
| https://inferencex.semianalysis.com/compare/deepseek-v4-b200-vs-h200 | 2 | [r/aiwars](https://www.reddit.com/r/aiwars/comments/1tuvr0s/considering_that_no_one_wants_to_calculate/) |
| https://sustainability.aboutamazon.com/products-services/aws-cloud | 2 | [r/aiwars](https://www.reddit.com/r/aiwars/comments/1tuvr0s/considering_that_no_one_wants_to_calculate/) |
| https://www.eesi.org/articles/view/data-centers-and-water-consumption | 2 | [r/aiwars](https://www.reddit.com/r/aiwars/comments/1tuvr0s/considering_that_no_one_wants_to_calculate/) |
| https://github.com/kainlang/kain/releases/tag/v0.8.1 | 2 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://gist.github.com/deparko/782e4ab8d247eaf9f40fc2063c8f8f82 | 2 | [r/ollama](https://www.reddit.com/r/ollama/comments/1sxjbo5/ollama_cloud_reliability_speed_36call_bench/) |
| https://github.com/12122J/claude-delegator-deepseek-mcp | 2 | [r/coolgithubprojects](https://www.reddit.com/r/coolgithubprojects/comments/1uv6w44/i_built_a_thing_that_delegates_claude_codes_grunt/) |
| https://www.npmjs.com/package/claude-code-deepseek-delegator | 2 | [r/coolgithubprojects](https://www.reddit.com/r/coolgithubprojects/comments/1uv6w44/i_built_a_thing_that_delegates_claude_codes_grunt/) |
| https://www.investopedia.com/terms/h/hedgefund.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/articles/professionals/110415/role-prime-broker.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.preqin.com/insights/research/blogs/what-makes-a-successful-prime-broker | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://primer.prooftrading.com/assets/pdf/03.05_participants_brokers.pdf | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.sec.gov/files/2020-pf-report-to-congress.pdf | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/terms/i/investmentbank.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://en.wikipedia.org/wiki/List_of_investment_banks | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/terms/c/chinesewall.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.bloomberg.com/news/articles/2014-12-11/finra-fines-10-wall-street-firms-over-analysts-ipo-pitches | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/terms/s/stock-loan-rebate.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.forbes.com/sites/edwardsiedle/2021/01/30/your-state-pension-is-unknowingly-shorting-stocks-like-gamestop-all-the-time/?sh=6cc2c3f4752d | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.pbgc.gov/ | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://fas.org/sgp/crs/misc/95-118.pdf | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.pewtrusts.org/en/research-and-analysis/issue-briefs/2020/06/the-state-pension-funding-gap-2018 | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.lohud.com/story/money/business/2021/01/28/gamestop-ny-state-pension-fund-sold-off-600-k-shares-last-10-months/4283205001/ | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.barrons.com/articles/giant-pension-sold-alibaba-palantir-gamestop--bought-zoom-retirement-51621348055 | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/terms/m/marketmaker.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.jstor.org/stable/1341823 | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/terms/g/ghosting.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://scholarship.law.stjohns.edu/cgi/viewcontent.cgi?article=3322&amp;context=lawreview | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investorschronicle.co.uk/shares/2018/11/09/the-truth-about-market-makers/ | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.reuters.com/article/us-trading-markets-gaming/traders-manipulating-cheap-stocks-market-maker-idUSTRE68P27W20100926 | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.nasdaq.com/articles/5-market-manipulation-tactics-and-how-avoid-them-2018-04-11 | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.tradersmagazine.com/xtra/payment-for-order-flow-is-undeniable-conflict-of-interest/ | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/articles/forex/06/ecnmarketmaker.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.forbes.com/sites/greatspeculations/2010/04/30/when-does-market-making-become-market-manipulation/?sh=1bcd99031e04 | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/terms/d/derivative.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.bis.org/publ/otc_hy2105.htm | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.businessinsider.com/heres-how-much-money-there-is-in-the-world-2017-10 | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/articles/optioninvestor/09/naked-short-selling.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://markets.businessinsider.com/news/stocks/steve-cohen-ken-griffin-invest-3-billion-gamestop-short-seller-2021-1 | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/ask/answers/05/shortsaleclosed.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://finadium.com/the-long-and-short-of-us-prime-brokerage-pricing-in-2019/ | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.reuters.com/business/finance/tsunami-cash-is-driving-rates-ever-lower-what-will-fed-do-2021-06-03/ | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.nber.org/system/files/working_papers/w28124/w28124.pdf | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.forbes.com/sites/moneyshow/2021/07/13/easy-money-and-the-risks-of-inflation/ | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.marketwatch.com/story/feds-reverse-repo-program-sees-demand-soar-to-just-under-1-trillion-overnight-11625079189 | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.reuters.com/breakingviews/nomura-extends-prime-broker-woes-2021-07-07/ | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.ft.com/content/267d00fb-f623-4850-a82b-4ef88a41d4b5 | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.sifma.org/wp-content/uploads/2017/08/Prime-Brokerage-_Prime-Brokerage-Agreement-Form-150.pdf | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://content.next.westlaw.com/1-382-3377?__lrTS=20210110035720384&amp;transitionType=Default&amp;contextData=(sc.Default | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.bloomberg.com/news/articles/2021-06-11/citadel-securities-settles-with-hedge-fund-over-secret-algorithm | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.tradingdirect.com/pricing/Interest-Rates | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.sec.gov/Archives/edgar/data/929351/000119312511272819/d237132dex2.htm | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/ask/answers/07/margin_interest.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://hedgefundlawblog.com/prime-brokers-margin-lock-ups-hedge-funds.html | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/terms/e/event-of-default.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://jollycontrarian.com/index.php?title=Fish_or_cut_bait | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.kramerlevin.com/images/content/4/2/v4/427/HFLR-Best-Practices-for-Hedge-Fund-Managers-When-Entering-into-ISDAs-Negotiating-Callat.pdf | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.isda.org/ | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| http://www.themargininvestor.com/regulatory-timeline.html | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| http://www.themargininvestor.com/portfolio-margin-101.html | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.investopedia.com/terms/m/margincall.asp | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.lawinsider.com/clause/investor-default | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://www.eisneramper.com/bakker-hedge-ai-blog-0920/ | 2 | [r/DDintoGME](https://www.reddit.com/r/DDintoGME/comments/okixbv/the_game_we_play_gambling_with_giants_the_myth_of/) |
| https://github.com/01554/llama.cpp/tree/expert-tier | 2 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1vzgfjl/qwen38flashnext_udq4_k_xl_33_toks_with_32_gb_vram/) |
| https://huggingface.co/inclusionAI/Ling-3.0-tiny | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://huggingface.co/Qwen/Qwen3.8-27B | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://apps.shopify.com/ | 2 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| https://www.youtube.com/watch?v=PBxmRy0da7k | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w21qz0/visual_comparison_of_various_models_a_very/) |
| https://www.youtube.com/watch?v=9Sxzqvr7m4Q | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w21qz0/visual_comparison_of_various_models_a_very/) |
| https://www.youtube.com/watch?v=3wXiTPGlzzs | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w21qz0/visual_comparison_of_various_models_a_very/) |
| https://www.youtube.com/watch?v=EWzHzpkGASY | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w21qz0/visual_comparison_of_various_models_a_very/) |
| https://www.youtube.com/watch?v=SMA5W96IAUE | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w21qz0/visual_comparison_of_various_models_a_very/) |
| https://www.youtube.com/watch?v=R2oWKVDZuTo | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w21qz0/visual_comparison_of_various_models_a_very/) |
| https://huggingface.co/pocharlies/deepseek-v4-flash-0731-uncensored-abliterated-refusal-directions | 2 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vmxm5t/deepseekv4flash0731_abliterated_perrequest_no/) |
| https://github.com/pocharlies/deepseek-v4-flash-rank1-refusal-projection | 2 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vmxm5t/deepseekv4flash0731_abliterated_perrequest_no/) |
| https://huggingface.co/XiaomiMiMo/MiMo-V2.5 | 2 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/tencent/Hy3 | 2 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vqq92m/life_after_deepseek_the_king_is_dead_comparing/) |
| https://www.youtube.com/watch?v=Q-iaz9mBFrA | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1tgow6t/megumin_suite_v7_your_preset_your_memory_your/) |
| https://github.com/ggml-org/llama.cpp/issues/22319 | 2 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1taclsw/deepseek_v4_in_llamacpp_flash_pro_cuda_metal/) |
| https://github.com/ggml-org/llama.cpp/pull/21149 | 2 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1taclsw/deepseek_v4_in_llamacpp_flash_pro_cuda_metal/) |
| https://huggingface.co/spaces/Specific-Labs/HalBench | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1u6y5l5/halbench_29_oss_models_tested_on_a_custom_built/) |
| https://huggingface.co/datasets/Specific-Labs/halbench | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1u6y5l5/halbench_29_oss_models_tested_on_a_custom_built/) |
| https://github.com/santiagoaraoz2001-sketch/halbench | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1u6y5l5/halbench_29_oss_models_tested_on_a_custom_built/) |
| https://artificialanalysis.ai/agents/coding-agents?agents=claude-code-qwen3-7-plus-thinking%2Cclaude-code-fable-5-max-with-fallback%2Cclaude-code-opus | 2 | [r/cursor](https://www.reddit.com/r/cursor/comments/1uywf62/significantly_lower_value_in_cursor_subscription/) |
| https://arxiv.org/abs/1706.03762 | 2 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://arxiv.org/abs/2005.14165 | 2 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://www.3blue1brown.com/lessons/mini-llm/ | 2 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://arxiv.org/abs/2412.19437 | 2 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://github.com/deepseek-ai/DeepSeek-V3 | 2 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://github.com/LostRuins/koboldcpp | 2 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://github.com/LostRuins/koboldcpp/wiki | 2 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://sillytavern.app/ | 2 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://docs.sillytavern.app/ | 2 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://developers.openai.com/api/docs/guides/your-data | 2 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://platform.claude.com/docs/en/manage-claude/api-and-data-retention | 2 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://openrouter.ai/docs/guides/privacy/provider-logging | 2 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| http://host.docker.internal:1234/v1 | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1u9fa2w/my_hermes_setup_roast_me/) |
| https://claude.ai/public/artifacts/24a2fd0d-cda2-4e76-aad0-29f703482d5b | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1u9fa2w/my_hermes_setup_roast_me/) |
| https://blog.holmebengt.com/post.html?id=hermes-full-setup | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1v03vab/i_made_a_video_walkthrough_of_my_full_hermes/) |
| https://deepwiki.com/chishiki37/dgx-spark-runbooks/6.2-speculative-decoding:-mtp-dflash-and-dspark | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w3ia28/an_analysis_of_the_inference_nonconvergence_and/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/discussions/39 | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w3ia28/an_analysis_of_the_inference_nonconvergence_and/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/discussions/50 | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w3ia28/an_analysis_of_the_inference_nonconvergence_and/) |
| https://github.com/Anemll/dspark-vllm-gx10/issues/3 | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w3ia28/an_analysis_of_the_inference_nonconvergence_and/) |
| https://www.youtube.com/watch?v=ZRPXqr5C2xo | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1te72in/ernie_ai_benchmark_makes_chinas_ai_race/) |
| https://huggingface.co/ycui7/DeepSeek-V4-Flash-MTP | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vdm29u/running_deepseekv4flash0731_155_gb_moe_on_a_dgx/) |
| https://openrouter.ai/models?max_price=0&amp;input_modalities=text&amp;supported_parameters=tools | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b:free | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/nousresearch/hermes-3-llama-3.1-405b:free | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/meta-llama/llama-3.3-70b-instruct:free | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/qwen/qwen3-next-80b-a3b-instruct:free | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/nvidia/nemotron-3-nano-30b-a3b:free | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/cognitivecomputations/dolphin-mistral-24b-venice-edition:free | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/nvidia/nemotron-nano-9b-v2:free | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/google/lyria-3-clip-preview | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/openrouter/free | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://openrouter.ai/rankings | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://github.com/brontoguana/krasis/blob/main/STATS-BENCHMARKS.md | 2 | [r/krasis](https://www.reddit.com/r/krasis/comments/1vfeqep/krasis_update_deepseek_v4_flash_step_37_and_more/) |
| https://github.com/brontoguana/krasis/blob/main/STATS-QUALITY.md | 2 | [r/krasis](https://www.reddit.com/r/krasis/comments/1vfeqep/krasis_update_deepseek_v4_flash_step_37_and_more/) |
| https://github.com/criterium/opencode-lab/blob/main/research/deepseek-battle-compaction/README.md | 2 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1tv98pu/deepseek_v4_flash_vs_deepseek_v4_pro_compaction/) |
| https://github.com/criterium/opencode-lab/blob/main/research/deepseek-battle-compaction/README.es.md | 2 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1tv98pu/deepseek_v4_flash_vs_deepseek_v4_pro_compaction/) |
| https://blog.holmebengt.com/post.html?id=backup-protocol | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1vp2gjc/after_receiving_over_65_questions_about_my_hermes/) |
| https://app.manifest.build/v1&gt | 2 | [r/ManifestforAI](https://www.reddit.com/r/ManifestforAI/comments/1ts10h0/run_claude_code_with_qwen37_and_stop_hitting/) |
| https://minebench.ai/ | 2 | [r/singularity](https://www.reddit.com/r/singularity/comments/1sxapqb/differences_between_gpt_54_and_gpt_55_on_minebench/) |
| https://github.com/Ammaar-Alam/minebench | 2 | [r/singularity](https://www.reddit.com/r/singularity/comments/1sxapqb/differences_between_gpt_54_and_gpt_55_on_minebench/) |
| https://localainews.co/news/news-you-missed/ | 2 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/ggml-org/llama.cpp/discussions/22376 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1udwabh/mimo_25_is_fast_at_large_context_dual_rtx_pro_6000/) |
| https://github.com/sgl-project/sglang/issues/19637 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1udwabh/mimo_25_is_fast_at_large_context_dual_rtx_pro_6000/) |
| https://huggingface.co/MiniMaxAI/MiniMax-H3 | 2 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://simonwillison.net/2026/Aug/12/deepseek-v4-pro-0813 | 2 | [r/chutesAI](https://www.reddit.com/r/chutesAI/comments/1vn8197/deepseekv4pro0813_is_official_agent_benchmarks/) |
| https://github.com/elsung/dgx-spark-deepseek-v4-flash | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1u5g9pr/dual_dgx_sparks_40tks_single_1m_350_tks_agg/) |
| https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/37 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1u5g9pr/dual_dgx_sparks_40tks_single_1m_350_tks_agg/) |
| https://forums.developer.nvidia.com/t/deepseek-v4-flash-official-fp8-running-across-2x-dgx-spark-tp-2-mtp-200k-ctx-recipe-numbers/370309 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1u5g9pr/dual_dgx_sparks_40tks_single_1m_350_tks_agg/) |
| https://deepseek-harness-plugin.com/plugins/dsh-anchored-standard/#install | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vpcutr/deepseek_v4_pro_0813_minimal_preset_on_dsh_vs/) |
| https://www.youtube.com/watch?v=SAg6wMigEpg&amp;t=15s | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vny1dz/deepseek_v4_pro_0813_benchmark_just_shocked_ai/) |
| https://www.youtube.com/watch?v=YWdHnB-GoH0&amp;t=12s | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vqdj2v/free_deepseek_v4_flash_beats_pro_on_9_agent/) |
| https://www.youtube.com/watch?v=jG0JTu0ENe8&amp;t=9s | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vrc9vq/deepseek_v4_pro_release_just_shocked_the_ai_world/) |
| https://fregonator.com | 2 | [r/pcmasterrace](https://www.reddit.com/r/pcmasterrace/comments/1qtv91e/i_built_an_opensource_alternative_to_ccleaner/) |
| https://github.com/dthcst/fregonator | 2 | [r/pcmasterrace](https://www.reddit.com/r/pcmasterrace/comments/1qtv91e/i_built_an_opensource_alternative_to_ccleaner/) |
| https://vllm.ai/blog/deepseek-v4 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1svzlog/the_exact_kv_cache_usage_of_deepseek_v4/) |
| https://agents-last-exam.org/leaderboard | 2 | [r/codex](https://www.reddit.com/r/codex/comments/1u75p1i/unhinged_results_from_uc_berkeleys_new_ale/) |
| https://manus.im/it/blog/best-ai-coding-assistant-tools | 2 | [r/esperimenti_con_AI](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) |
| https://designrevision.com/it/blog/migliore-ia-per-programmare | 2 | [r/esperimenti_con_AI](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) |
| https://www.zerodivision.it/migliore-ai-chatgpt-claude-gemini-perplexity/ | 2 | [r/esperimenti_con_AI](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) |
| https://www.youtube.com/watch?v=KfN19jjhVFQ | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vv8bys/deepseek_v4_pro_vs_deepseek_v4_flash_has_one_big/) |
| https://www.youtube.com/watch?v=0msHgFOnsK0 | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vqshx8/free_deepseek_v4_flash_won_all_9_agent_benchmarks/) |
| https://www.youtube.com/watch?v=ZiKvlQL1rzY&amp;t=12s | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vraoym/deepseek_v4_pro_vs_fable_5_reveals_a_wild_cache/) |
| https://www.youtube.com/watch?v=b8gTYPBZ-UA | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1su6zyd/deepseek_v4_open_source_ai_looks_strong_but_the/) |
| https://www.youtube.com/watch?v=PBPMpdWUqAo | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1su6il6/deepseek_v4_has_one_million_context_and_one_clear/) |
| http://ghcr.io/ggml-org/llama.cpp:server-rocm | 2 | [r/LocalAIStack](https://www.reddit.com/r/LocalAIStack/comments/1vckkbs/deepseek_v4_flash_0731_llamacpp_tips/) |
| https://github.com/ggml-org/llama.cpp/pull/25784 | 2 | [r/StrixHalo](https://www.reddit.com/r/StrixHalo/comments/1vcz5zi/deepseekv4flash0731_on_bosgame_m5_with_rtx_pro/) |
| https://noizz.io/local-ai** | 2 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1v4lol2/ran_the_actual_cost_math_a_year_of_chatgpt_plus/) |
| https://github.com/ggml-org/llama.cpp/discussions/18244 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1uhcf9t/does_anyone_here_have_a_prefilled_prompt_solution/) |
| https://github.com/NousResearch/hermes-agent | 2 | [r/WebAfterAI](https://www.reddit.com/r/WebAfterAI/comments/1uh84a2/hermes_now_lets_you_stack_frontier_models_into/) |
| https://github.com/drumih/turbo-fieldfare | 2 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vjwfa5/deepseekv4flash0731284b_on_a_64g_m5_pro_mac_65/) |
| https://github.com/Moritz230127/win11-native-usb-install | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w2zmhr/a_feasible_method_for_natively_deploying_windows/) |
| https://www.youtube.com/watch?v=DAg8fvdSB0s | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1t4avj3/free_deepseek_v4_pro_is_wild_for_coding_2026/) |
| https://www.mediafire.com/file/1wb94rw707lzst7/Freaky_Frankenstein_4_MAX.json/file | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1sztr62/the_directors_cut_freaky_frankenstein_4_max_and/) |
| https://www.mediafire.com/file/nq5kqt7cp996zjl/Freaky_Frankenstein_4_BOLT.json/file | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1sztr62/the_directors_cut_freaky_frankenstein_4_max_and/) |
| https://www.youtube.com/watch?v=SGyhrdkPO20&amp;t=130s | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vk5taq/how_to_use_deepseek_v4_for_free_with_open_code/) |
| https://www.youtube.com/watch?v=Y2zzC9tMNi0 | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vkxbs4/deepseek_v4_flash_benchmark_shocked_me_with_50/) |
| https://huggingface.co/UltimateIntent/GemStrike-31B-GGUF | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vzf0s7/gemstrike31b_uncensored_creative_rp_for_gemma_4/) |
| https://huggingface.co/UltimateIntent/GemStrike-31B-EXL3-4.00bpw | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vzf0s7/gemstrike31b_uncensored_creative_rp_for_gemma_4/) |
| https://huggingface.co/UltimateIntent/GemStrike-31B-LORA | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vzf0s7/gemstrike31b_uncensored_creative_rp_for_gemma_4/) |
| https://github.com/Gentleman-Programming/gentle-ai | 2 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1uhft8c/opencode_go_opinion/) |
| https://cline.bot/blog/deepseek-wins-imo-gold-on-12-cents | 2 | [r/CLine](https://www.reddit.com/r/CLine/comments/1w0q6ht/deepseek_v4_flash_scored_imo_gold_for_just_012/) |
| https://www.youtube.com/watch?v=d6itLdB-HmU&amp;t=11s | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vzj3q3/agent_os_guide_builds_and_automates_anything_with/) |
| https://github.com/spencer-zaid/llama.cpp/blob/deepseek-lid-cuda/docs/deepseek-v4-lid-cuda.md | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ulymml/llamacpp_patch_deepseek_v4_flash_running_with/) |
| https://github.com/spencer-zaid/llama.cpp/tree/deepseek-lid-cuda | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ulymml/llamacpp_patch_deepseek_v4_flash_running_with/) |
| https://github.com/lsennn/Deus-ex-machina/releases | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vcr9d8/preset_deus_ex_machina_v1_a_featurerich/) |
| https://github.com/lsennn/Deus-ex-machina | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vcr9d8/preset_deus_ex_machina_v1_a_featurerich/) |
| https://github.com/Lodactio/Extension-Summaryception | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vcr9d8/preset_deus_ex_machina_v1_a_featurerich/) |
| https://www.youtube.com/watch?v=gkFyVpP9LPk | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vmje7c/how_to_use_deepseek_v4_for_free_and_run_powerful/) |
| https://plotlightstudios.com/plotpoints/multiturn | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1twf5ew/plotpoints_the_best_only_community_driven_rp/) |
| https://plotlightstudios.com/plotpoints | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1twf5ew/plotpoints_the_best_only_community_driven_rp/) |
| https://plotlightstudios.com/plotpoints/methodology | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1twf5ew/plotpoints_the_best_only_community_driven_rp/) |
| https://huggingface.co/datasets/lazyweasel/roleplay-bench | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1twf5ew/plotpoints_the_best_only_community_driven_rp/) |
| https://github.com/LeviTheWeasel/rp-benchmark | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1twf5ew/plotpoints_the_best_only_community_driven_rp/) |
| https://github.com/Hero699/creative-writing-benchmark-v3 | 2 | [r/GeminiAI](https://www.reddit.com/r/GeminiAI/comments/1vhf7vc/best_creative_writing_models_of_2026_v2/) |
| https://github.com/cactus-compute/cactus-hybrid | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v3nw3j/cactus_hybrid_we_taught_gemma_4_to_know_when_its/) |
| https://huggingface.co/Menlo/Jan-nano | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1lbrnod/jannano_a_4b_model_that_can_outperform_671b_on_mcp/) |
| https://huggingface.co/Menlo/Jan-nano-gguf | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1lbrnod/jannano_a_4b_model_that_can_outperform_671b_on_mcp/) |
| https://opencode.ai/go?ref=G6RSTYX9W3 | 2 | [r/opencode](https://www.reddit.com/r/opencode/comments/1tplieh/miiov25_is_as_cheap_as_deepseekv4_flash/) |
| https://github.com/louis-e/arnis | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://www.kaggle.com/models/google/gemma-4 | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/collections/arcee-ai/trinity-large-thinking | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/zai-org/GLM-OCR | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/zai-org/GLM-5.1 | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/google-deepmind/tips | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/nv-tlabs/lyra | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/robbyant/lingbot-map | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/allenai/WildDet3D | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/collections/OpenMOSS-Team/moss-vl | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/microsoft/TRELLIS.2 | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/collections/XiaomiMiMo/mimo-v25 | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/AngelSlim/Hy-MT1.5-1.8B-1.25bit | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/deepseek-ai/DeepSeek-OCR-2 | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/Zyphra/ZAYA1-8B | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/collections/HumeAI/tada | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/fishaudio/s2-pro | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/KittenML/KittenTTS | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/CohereLabs/cohere-transcribe-03-2026 | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/NVIDIA/personaplex | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/OpenMOSS/MOSS-TTS-Nano | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/XiaomiMiMo/MiMo-V2.5-ASR | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/OpenMOSS/MOSS-Audio | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/sbintuitions/sarashina2.2-tts | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/ace-step/ACE-Step-1.5 | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/VAST-AI-Research/AniGen | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/IGL-HKUST/CoMoVi | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/lllyasviel/Fooocus | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/GVCLab/PersonaLive | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/open-gitagent/gitagent | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/allenai/molmoweb | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/HKUDS/OpenSpace | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/HKUDS/CatchMe | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/agentscope-ai/agentscope | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/MiniMax-AI/skills | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/Panniantong/Agent-Reach | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/vectorize-io/hindsight | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/THU-MAIC/OpenMAIC | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/openagents-org/openagents | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/paperclipai/paperclip | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/Intelligent-Internet/ii-agent | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/onyx-dot-app/onyx | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/block/goose | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/agentscope-ai/ReMe | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/aipoch/medical-research-skills | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/alibaba/page-agent | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/HKUDS/nanobot | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/Donchitos/Claude-Code-Game-Studios | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/HKUDS/DeepTutor | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/rui-ye/OpenSeeker | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/tinyfish-io/skills | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/openai/openai-agents-python | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/trycua/cua | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/qwibitai/nanoclaw | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/nico-martin/gemma4-browser-extension | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/openai/symphony | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/infiniflow/ragflow | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/bytedance/deer-flow | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/VectifyAI/PageIndex | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/browser-use/browser-use | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/pipecat-ai/pipecat | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/mem0ai/mem0 | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/ComposioHQ/composio | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/mastra-ai/mastra | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/langgenius/dify | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/norma-core/norma-core/tree/main/hardware/elrobot | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/wu-yc/LabClaw | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/dimensionalOS/dimos | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/collections/unitreerobotics/unifolm-wbt-dataset | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/freemocap/freemocap | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/yazinsai/OpenOats | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/warpdotdev/warp | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/1weiho/open-slide | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/nexu-io/open-design | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/googleworkspace/cli | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/lightpanda-io/browser | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/vllm-project/vllm-omni | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/K-Dense-AI/k-dense-byok | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/Vaibhavs10/insanely-fast-whisper | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/openai/plugins | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/yichuan-w/LEANN | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/MiniMax-AI/cli | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/hiyouga/LlamaFactory | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/run-llama/liteparse | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/github/spec-kit | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/jamiepine/voicebox | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/NVIDIA-NeMo/DataDesigner | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/TencentCloud/CubeSandbox | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/heygen-com/hyperframes | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/openai/privacy-filter | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/PaddlePaddle/PaddleOCR | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/google-labs-code/design.md | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/datasets/allenai/olmOCR-bench | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://huggingface.co/datasets/google/WaxalNLP | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/run-llama/ParseBench | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/evolvent-ai/ClawMark | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/meituan-longcat/LARYBench | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/openai/monitorability-evals | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/meituan-longcat/General365 | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://www.youtube.com/watch?v=juwa1vTWwvw | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1t7nz97/new_hermes_agent_v0130_is_shocking_864_commits_in/) |
| https://www.youtube.com/watch?v=uTteGzkrEtM | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1w1ssc0/deepseek_ai_tutorial_shows_the_v4_free_agent_stack/) |
| https://www.aimadetools.com/blog/mimo-v2-pro-vs-mimo-v2-flash/ | 2 | [r/singularity](https://www.reddit.com/r/singularity/comments/1s1cvi7/a_phone_company_is_now_competing_with_anthropic/) |
| https://crof.ai/v1 | 2 | [r/CrofAI](https://www.reddit.com/r/CrofAI/comments/1sc3nsw/crofai_affordable_multimodel_ai_access_with_cheap/) |
| https://crof.ai/v2 | 2 | [r/CrofAI](https://www.reddit.com/r/CrofAI/comments/1sc3nsw/crofai_affordable_multimodel_ai_access_with_cheap/) |
| https://api-docs.deepseek.com/quick\_start/agent\_integrations/codex/ | 2 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| https://api-docs.deepseek.com/quick_start/agent_integrations/codex/ | 2 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| https://opencode.ai/workspace/&lt;id&gt;/go | 2 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| http://127.0.0.1:${PORT} | 2 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| http://127.0.0.1:3456 | 2 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| https://www.youtube.com/watch?v=6Rl2uIJJu98 | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vs8i9n/gemini_flash_new_version_is_googles_agent_upgrade/) |
| https://github.com/KritBlade/MVU_Game_Maker | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1svavzk/mvu_game_maker_v095_slice_of_lifedating_sim_with/) |
| https://github.com/franciscoluna-28/fabric-ai | 2 | [r/dev_venezuela](https://www.reddit.com/r/dev_venezuela/comments/1u6jgal/claude_code_criollo_cómo_programo_con_ia_sin/) |
| https://github.com/franciscoluna-28/envoy | 2 | [r/dev_venezuela](https://www.reddit.com/r/dev_venezuela/comments/1u6jgal/claude_code_criollo_cómo_programo_con_ia_sin/) |
| https://eur-lex.europa.eu/eli/reg/2024/1689/oj | 2 | [r/LocalTextToSpeech](https://www.reddit.com/r/LocalTextToSpeech/comments/1udgq58/eu_ai_act_requires_text_from_models_and_providers/) |
| https://www.consilium.europa.eu/en/press/press-releases/2026/05/07/artificial-intelligence-council-and-parliament-agree-to-simplify-and-streamline-rul | 2 | [r/LocalTextToSpeech](https://www.reddit.com/r/LocalTextToSpeech/comments/1udgq58/eu_ai_act_requires_text_from_models_and_providers/) |
| https://www.youtube.com/watch?v=HSvdKJCt9LI | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vsil60/deepseek_v4_pro_release_hits_1m_context_and_huge/) |
| https://www.storagereview.com/review/msi-xpertstation-ws300-review-748gb-of-coherent-memory-and-20-petaflops-on-a-desk | 2 | [r/StorageReview](https://www.reddit.com/r/StorageReview/comments/1vxdzsy/we_tested_the_gb300_dgx_station_748gb_coherent/) |
| https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-fourth-quarter-and-fiscal-2026 | 2 | [r/ValueInvesting](https://www.reddit.com/r/ValueInvesting/comments/1t7t2yv/help_me_understand_how_nvidia_is_not_overvalued/) |
| https://www.google.com/search?q=nvidia+stock&amp;sxsrf=ANbL-n4MrfK1zobrvRCWmUi6nWk8yd8coQ%3A1778288663847 | 2 | [r/ValueInvesting](https://www.reddit.com/r/ValueInvesting/comments/1t7t2yv/help_me_understand_how_nvidia_is_not_overvalued/) |
| https://www.tipranks.com/stocks/nvda/forecast | 2 | [r/ValueInvesting](https://www.reddit.com/r/ValueInvesting/comments/1t7t2yv/help_me_understand_how_nvidia_is_not_overvalued/) |
| https://www.nxcode.io/resources/news/deepseek-v4-vs-claude-opus-vs-gpt-5-coding-2026 | 2 | [r/ValueInvesting](https://www.reddit.com/r/ValueInvesting/comments/1t7t2yv/help_me_understand_how_nvidia_is_not_overvalued/) |
| https://en.wikipedia.org/wiki/DeepSeek | 2 | [r/ValueInvesting](https://www.reddit.com/r/ValueInvesting/comments/1t7t2yv/help_me_understand_how_nvidia_is_not_overvalued/) |
| https://www.forbes.com/sites/timbajarin/2026/04/29/ai-compute-surpasses-human-costs-enterprise-budgets-shift/ | 2 | [r/ValueInvesting](https://www.reddit.com/r/ValueInvesting/comments/1t7t2yv/help_me_understand_how_nvidia_is_not_overvalued/) |
| https://commandcode.ai | 2 | [r/PiCodingAgent](https://www.reddit.com/r/PiCodingAgent/comments/1t4faft/i_built_a_pi_custom_provider_for_command_code/) |
| https://api.openadapter.in/v1 | 2 | [r/openadapter_](https://www.reddit.com/r/openadapter_/comments/1vl8aho/what_is_openadapter_straight_answer_including/) |
| https://api.openadapter.in/v1/messages | 2 | [r/openadapter_](https://www.reddit.com/r/openadapter_/comments/1vl8aho/what_is_openadapter_straight_answer_including/) |
| https://openrouter.ai/models?q=deepseek+v4 | 2 | [r/openrouter](https://www.reddit.com/r/openrouter/comments/1u8yk1b/are_deepseek_api_prices_are_much_cheaper_direct/) |
| https://github.com/AtomicBot-ai/Atomic-Chat | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1svnjns/deepseek_v4_pro_vs_gpt55_for_building_simple_game/) |
| https://huggingface.co/UltimateIntent/HeatSeeker-284B-A13B-GGUF | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vt4ju3/heatseeker_284b_a13b_my_ds4flash0731_roleplay/) |
| https://huggingface.co/UltimateIntent/HeatSeeker-284B-A13B-Lora | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vt4ju3/heatseeker_284b_a13b_my_ds4flash0731_roleplay/) |
| https://github.com/ronak-create/deepseek-v4-in-c | 2 | [r/SideProject](https://www.reddit.com/r/SideProject/comments/1vuhybs/i_built_a_c99_inference_engine_that_runs/) |
| https://www.dropbox.com/scl/fi/4nov2gkksyfyesx1dv31n/Writer-s-Block-5-Latest-2.json?rlkey=g03iai267g6shfg6tkxqdyewu&amp;st=16szg0g7&amp;dl=0 | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1v64r6z/update_writers_block_5_a_prose_and_narrative/) |
| https://api.deepseek.com/anthropic | 2 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1t3oypq/switched_my_claude_code_agent_loop_to_deepseek_v4/) |
| https://podcasts.apple.com/ca/podcast/today-in-ai-ml-apple-prepares-developers-for-siris/id1684415169?i=1000676003699 | 2 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1glh6bs/today_in_aiml_apple_prepares_developers_for_siris/) |
| https://developer.apple.com/documentation/appintents/making-onscreen-content-available-to-siri-and-apple-intelligence | 2 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1glh6bs/today_in_aiml_apple_prepares_developers_for_siris/) |
| https://arstechnica.com/ai/2024/11/anthropic-raises-eyebrows-with-haiku-price-hike-citing-increased-intelligence/ | 2 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1glh6bs/today_in_aiml_apple_prepares_developers_for_siris/) |
| https://arxiv.org/pdf/2411.02265 | 2 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1glh6bs/today_in_aiml_apple_prepares_developers_for_siris/) |
| https://www.bloomberg.com/news/articles/2024-11-04/apple-explores-push-into-smart-glasses-with-atlas-user-study | 2 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1glh6bs/today_in_aiml_apple_prepares_developers_for_siris/) |
| https://huggingface.co/Menlo/Jan-nano-128k | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ljyo2p/jannano128k_a_4b_model_with_a_superlong_context/) |
| https://beta.locallm.top | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vcz4b4/a_collection_of_small_domainspecific_benchmarks/) |
| https://x.com/Zai_org/status/2088132973606445208 | 2 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1vo6u37/glm53_stesso_base_di_52_posttraining_su_coding_e/) |
| https://github.com/THUDM/slime | 2 | [r/chutesAI](https://www.reddit.com/r/chutesAI/comments/1vo6wrp/glm53_is_the_same_743b_base_as_52_reposttrained/) |
| https://www.youtube.com/watch?v=uBe1Lz1GxtY&amp;t=9s | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1swvhyk/how_deepseek_v4_flash_benchmark_competes_with/) |
| https://www.youtube.com/watch?v=bagORWOyilI&amp;t=95s | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vcdmz1/deepsseek_v4_flash_api_just_made_ai_agents_much/) |
| https://github.com/huiliyi37/Tianshu-Tui | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1uwxvnd/how_we_got_996_cache_hit_rate_on_deepseek_v4_pro/) |
| https://github.com/CarpseDeam/Aura-IDE | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1te8c1k/i_built_an_open_source_desktop_ai_coding_app/) |
| https://aura-ide.hashnode.dev/token-efficient-memory-how-aura-caches-bm25-repo-maps-and-long-term-context | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1te8c1k/i_built_an_open_source_desktop_ai_coding_app/) |
| http://claude.ai | 2 | [r/claudexplorers](https://www.reddit.com/r/claudexplorers/comments/1w0d2nh/building_a_permanent_home_for_ai_friends_what/) |
| https://x.com/deepseek_ai/status/2087864585504305397 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vn8m1x/deepseek_were_launching_deepseekv4pro_today/) |
| https://github.com/anomalyco/opencode/issues | 2 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1uco67e/if_you_pay_for_opencode_go_12_of_15_models_break/) |
| http://imgur.com/a/nxY0Q | 2 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/rH702 | 2 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://www.theguardian.com/us-news/2024/dec/21/curtis-yarvin-trump | 2 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://github.com/guqiong96 | 2 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vo1olv/iv_tried_deepseek_v4_spark_0731_with_lvllmx_which/) |
| https://chat.deepseek.com | 2 | [r/IASinHumo](https://www.reddit.com/r/IASinHumo/comments/1suy3ko/salio_deepseek_v4_bueno_mas_o_menos_lo_que_si_es/) |
| https://toknow.ai/posts/deepseek-v4-huawei-ascend-nvidia-monopoly-open-source-frontier/ | 2 | [r/nairobitechies](https://www.reddit.com/r/nairobitechies/comments/1sy5vcn/deepseek_v4_16_trillion_parameters_on_huawei/) |
| https://nqawhc.github.io/articles/local-vs-api/ | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1um84bd/followup_deepseek_v4_flash_on_2x_rtx_pro_6000/) |
| https://x.com/alexwg | 2 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://theinnermostloop.substack.com/ | 2 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://orthiclabs.com/notes/seven-coding-models-one-repo/ | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1virjzc/is_deepseek_v4_flash_the_best_model_as_subagent/) |
| https://sergiiob.dev/posts/intel-arc-b70-vllm-vs-llamacpp-moe-dense-showdown/ | 2 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vhfvzv/i_finllay_tried_a_custom_vllm_build_on_intel_arc/) |
| https://github.com/SergiioB/intel-arc-pro-b70-inference-cookbook | 2 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vhfvzv/i_finllay_tried_a_custom_vllm_build_on_intel_arc/) |
| https://pickleshell.github.io/model-comparison.html | 2 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vqaw2f/tested_50_coding_models_on_the_same_task_with/) |
| https://github.com/alexzhaosheng/huko-engine | 2 | [r/node](https://www.reddit.com/r/node/comments/1tovz6i/hukoengine_an_outofthebox_agent_engine_give_your/) |
| https://github.com/alexzhaosheng/huko | 2 | [r/node](https://www.reddit.com/r/node/comments/1tovz6i/hukoengine_an_outofthebox_agent_engine_give_your/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-february-9th-2025 | 2 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai | 2 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-march-31-april-5th-2025 | 2 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-april-15th-april-21st-2025 | 2 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-april-28th-may-5th-2025 | 2 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-june-2nd-june-8th-2025 | 2 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-june-17th-june-22nd-2025 | 2 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-july-1st-july-7th-2025 | 2 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-july-8th-july-14th-2025 | 2 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-july-21st-august-10th-2025 | 2 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-october-21st-november-3rd#:~:text= | 2 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://www.marktechpost.com/2026/07/31/deepseek-upgrades-deepseek-v4-flash-0731-with-major-agentic-and-coding-gains/ | 2 | [r/machinelearningnews](https://www.reddit.com/r/machinelearningnews/comments/1vc4xns/deepseek_upgrades_deepseekv4flash0731_with_major/) |
| https://artificialanalysis.ai/models/deepseek-v4-flash | 2 | [r/machinelearningnews](https://www.reddit.com/r/machinelearningnews/comments/1vc4xns/deepseek_upgrades_deepseekv4flash0731_with_major/) |
| http://Continue.dev | 2 | [r/vibecoding](https://www.reddit.com/r/vibecoding/comments/1uhxmom/looking_for_a_vscode_extension_similar_to_github/) |
| https://aiwave.live | 2 | [r/huggingface](https://www.reddit.com/r/huggingface/comments/1ux28do/access_60_chinese_ai_models_from_any/) |
| https://aiwave.live/v1 | 2 | [r/huggingface](https://www.reddit.com/r/huggingface/comments/1ux28do/access_60_chinese_ai_models_from_any/) |
| https://ninzaverse.beehiiv.com/p/study-how-deepseek-beat-ai-s-million-token-problem | 2 | [r/aigossips](https://www.reddit.com/r/aigossips/comments/1syxyqt/deepseek_v4_just_made_a_million_tokens_cost_250/) |
| https://www.youtube.com/watch?v=9BYyexXd9HI | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1swev6c/deepseek_v4_pricing_the_simple_way_to_spend_less/) |
| https://github.com/MrLordCat/ai-agent-bridge | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vo2lgx/for_whom_wanted_to_work_with_deepseek_in_vsc/) |
| https://www.youtube.com/watch?v=uFakEZmu9ZU | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vqueav/new_deepseek_release_has_3_big_catches_you_need/) |
| https://www.youtube.com/watch?v=X7ie-FylDdo&amp;t=93s | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1ticvg4/hermes_agent_new_ai_model_makes_multiagent_tasks/) |
| https://github.com/NousResearch/hermes-agent/issues/11347 | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub121l/hermes_is_unusable_for_long_sessions_and/) |
| https://www.youtube.com/watch?v=E8eWv-OBHmo | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1w3jhrx/verdent_ai_coding_gets_glm_53_and_deepseek_v4/) |
| https://decrypt.co/365455/deepseek-v4-launch-pro-version-costs-less-gpt-5-pro | 2 | [r/IA_Italia](https://www.reddit.com/r/IA_Italia/comments/1sv8tn4/deepseek_v4_al_momento_costa_fino_al_98_in_meno/) |
| https://github.com/criterium/opencode-lab/tree/main/prompt/shared | 2 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1u1d3op/opencode_agent_prompts_for_deepseek_v4_a_critical/) |
| https://www.youtube.com/watch?v=z6sQfyccQk0 | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1ulmuxz/deepseek_new_update_just_changed_ai_speed_forever/) |
| https://ollama.com/api/usage | 2 | [r/ollama](https://www.reddit.com/r/ollama/comments/1vzkcc6/glm_53_vs_deepseek_v4_usage/) |
| https://www.nist.gov/news-events/news/2026/05/caisi-evaluation-deepseek-v4-pro | 2 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1t1eg26/caisi_evaluation_of_deepseek_v4_pro_finds_it_to/) |
| https://www.youtube.com/watch?v=YW1hAS5EXZ0 | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1sysezt/deepseek_v4_flash_and_pro_i_tested_both_and_the/) |
| https://huggingface.co/unsloth/DeepSeek-V4-Flash-GGUF | 2 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1upxpc1/run_deepseekv4flash_locally/) |
| https://pickleshell.github.io/model-benchmarks.html | 2 | [r/opencode](https://www.reddit.com/r/opencode/comments/1w1n1ak/new_llm_test_results_and_an_open_testing_pipeline/) |
| https://pickleshell.github.io/model-comparison-phase2-patch-current.html | 2 | [r/opencode](https://www.reddit.com/r/opencode/comments/1w1n1ak/new_llm_test_results_and_an_open_testing_pipeline/) |
| https://github.com/pickleshell/models-benchmark | 2 | [r/opencode](https://www.reddit.com/r/opencode/comments/1w1n1ak/new_llm_test_results_and_an_open_testing_pipeline/) |
| https://www.youtube.com/watch?v=FDHxuQsYFIk | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1ulo48g/deepseek_new_release_makes_deepseek_v4_faster/) |
| https://loremate.ai | 2 | [r/LoreMateAI](https://www.reddit.com/r/LoreMateAI/comments/1uop0er/a_little_story_on_loremate_for_new_users/) |
| https://www.dropbox.com/scl/fi/dgw8t8lbfhvcetoznqgio/Writer-s-Block-3.145-Divided-by-2-In-3DD-Write-Harder.json?rlkey=a0rrf0l1gqhii1vw8aaqq2gzd&amp;st | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1t23shb/writers_block_314152_in_3dd_write_harder_a_prose/) |
| https://djamgamind.com/pdfs | 2 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://apps.apple.com/ca/app/djamgatech-ai-cert-exams-prep/id1560083470 | 2 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://imgur.com/a/NXHqnmC | 2 | [r/homelabsales](https://www.reddit.com/r/homelabsales/comments/1w3qcja/fsusain_sealed_ddr5_ecc_sealed_ddr4_ecc_other/) |
| https://x.com/MrAhmadAwais/status/2050956678502420612 | 2 | [r/CommandCode](https://www.reddit.com/r/CommandCode/comments/1unkp7v/how_did_we_make_deepseek_outperform_opus_harness/) |
| https://www.youtube.com/watch?v=f61DCDwvFis | 2 | [r/CommandCode](https://www.reddit.com/r/CommandCode/comments/1unkp7v/how_did_we_make_deepseek_outperform_opus_harness/) |
| https://synvoya.com/blog/2026-04-29-deepseek-v4-open-source-frontier-huawei-chips/ | 2 | [r/Synvoya](https://www.reddit.com/r/Synvoya/comments/1syjgnk/deepseek_v4_drops_16t_params_mit_license_10x/) |
| https://huggingface.co/TOTORONG/extGemma4-44B | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ul0cx9/i_extended_gemma431b_to_44b_88_layers_since/) |
| https://huggingface.co/unsloth/inkling-GGUF | 2 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1uxeol2/inkling_975b_parameter_model_by_thinking_machines/) |
| https://huggingface.co/nohurry/sillytavern | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1towdj6/gemma_4_preset_moonlight/) |
| https://www.mediafire.com/file/rdvpdxci5ejn3ew/FF5.2_Internal_States_BOLT_Setup_%25281%2529.json/file | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vmc07f/preset_update_freaky_frankenstein_52_the_first/) |
| https://simonwillison.net/2026/Aug/16/qwen-38-27b/ | 2 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vox8eb/initial_impression_for_agentic_coding_qwen_38_27b/) |
| https://allenai.org/olmo | 2 | [r/ArtificialInteligence](https://www.reddit.com/r/ArtificialInteligence/comments/1uf2bxu/the_unbearable_cheapness_of_open_weight/) |
| https://www.nsf.gov/news/nsf-nvidia-partnership-enables-ai2-develop-fully-open-ai | 2 | [r/ArtificialInteligence](https://www.reddit.com/r/ArtificialInteligence/comments/1uf2bxu/the_unbearable_cheapness_of_open_weight/) |
| https://jamesoclaire.com/2026/06/25/the-unbearable-cheapness-of-open-weight-models/ | 2 | [r/ArtificialInteligence](https://www.reddit.com/r/ArtificialInteligence/comments/1uf2bxu/the_unbearable_cheapness_of_open_weight/) |
| https://www.youtube.com/watch?v=7NCyKtuzQmQ | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1tlc65u/deepseek_v4_pro_free_has_one_big_catch/) |
| https://vadapayasam.github.io/warehouse/#sketch | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ttjrzf/ive_been_using_hermes_for_30_days_and_it_keeps/) |
| https://focus.veritaslinks.com | 2 | [r/LLM_Brand_Perception](https://www.reddit.com/r/LLM_Brand_Perception/comments/1tca1iz/deepseek_v4pro_in_cursor_when_quality_and_cost/) |
| https://linknux.com | 2 | [r/SideProject](https://www.reddit.com/r/SideProject/comments/1w3yheu/i_built_one_openaicompatible_api_for_claude_gpt/) |
| https://www.youtube.com/watch?v=U4fZMz2oy-o | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vfggfe/deepseek_v4_flash_free_just_shocked_everyone/) |
| https://itzi.app/v1 | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vvlx1n/looking_for_10_sillytavern_testers_700_free_ai/) |
| https://itzi.app/subscriptions/fair-use | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vvlx1n/looking_for_10_sillytavern_testers_700_free_ai/) |
| https://nqawhc.github.io/articles/harness-efficiency-not-quality/ | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v7d8px/harness_showdown_claude_code_vs_opencode_vs_pi/) |
| https://aifreeforever.com/chat/deepseek-v4-flash | 2 | [r/freetoolsAI](https://www.reddit.com/r/freetoolsAI/comments/1tuwqad/free_deepseek_v4_ai_chatbot_unlimited/) |
| https://arxiv.org/abs/2607.20145 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v47kqc/paper_slai_trex_fullparameter_posttraining_of_the/) |
| https://arxiv.org/pdf/2607.20145 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v47kqc/paper_slai_trex_fullparameter_posttraining_of_the/) |
| https://github.com/SLAI-AITP/SLAI-T-Rex | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v47kqc/paper_slai_trex_fullparameter_posttraining_of_the/) |
| https://www.modelscope.cn/models/SLAIAITP/DeepSeek-V4-Flash-OR | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v47kqc/paper_slai_trex_fullparameter_posttraining_of_the/) |
| https://huggingface.co/unsloth/MiniMax-M3-GGUF | 2 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1u43tzm/minimax_m3_is_out_now/) |
| https://unsloth.ai/docs/models/minimax-m3 | 2 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1u43tzm/minimax_m3_is_out_now/) |
| https://github.com/lechmazur/nyt-connections/ | 2 | [r/singularity](https://www.reddit.com/r/singularity/comments/1sxe3bs/gpt55_improves_over_gpt54_and_overtakes_opus_46/) |
| https://clocktower-radio.com/games/pHYsmlT#event-171 | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1t3pjsc/deepseek_v4_pro_on_my_social_deduction_benchmark/) |
| https://clocktower-radio.com/games/g4BavG3#event-272 | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1t3pjsc/deepseek_v4_pro_on_my_social_deduction_benchmark/) |
| https://clocktower-radio.com/search?a=DeepSeek+V4+Pro | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1t3pjsc/deepseek_v4_pro_on_my_social_deduction_benchmark/) |
| https://clocktower-radio.com/how-it-works | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1t3pjsc/deepseek_v4_pro_on_my_social_deduction_benchmark/) |
| https://yhenon.github.io/surface-evolver-llm-eval/ | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1umcova/surface_evolver_bench_my_benchmark_asking_llms_to/) |
| https://astral.sh/uv/install.sh | 2 | [r/vibecoding](https://www.reddit.com/r/vibecoding/comments/1t8m55w/how_to_run_claude_code_for_free/) |
| https://github.com/Alishahryar1/free-claude-code.git | 2 | [r/vibecoding](https://www.reddit.com/r/vibecoding/comments/1t8m55w/how_to_run_claude_code_for_free/) |
| http://127.0.0.1:$PORT | 2 | [r/vibecoding](https://www.reddit.com/r/vibecoding/comments/1t8m55w/how_to_run_claude_code_for_free/) |
| https://npad.run/p/free-claude-code-in-3-minutes-claude-free-wrapper-nvidia-nim-fbh3d9p443 | 2 | [r/vibecoding](https://www.reddit.com/r/vibecoding/comments/1t8m55w/how_to_run_claude_code_for_free/) |
| https://www.youtube.com/watch?v=Q3TnFjxD65c | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1tppbbn/deepseek_v4_flash_turns_hermes_into_an_agent_os/) |
| https://github.com/lechmazur/debate | 2 | [r/singularity](https://www.reddit.com/r/singularity/comments/1t4o37r/update_to_the_llm_debate_benchmark_gpt55_grok_43/) |
| https://www.youtube.com/watch?v=fgGCQvwFLRs&amp;t=6s | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vu64bv/how_deepseek_harness_agent_creates_custom_ai/) |
| https://theaq.blog/2026/08/18/evaluating-deepseek-deepseek-v4-pro-0813-on-hack-the-box-challenges.html | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vshgy5/i_tested_deepseek_v4_pro_0813_on_16_hack_the_box/) |
| https://sliplane.io/blog/hetzner-inference | 2 | [r/hetzner](https://www.reddit.com/r/hetzner/comments/1v568oh/hetzner_is_experimenting_with_an_openaicompatible/) |
| https://medium.com/@alfonso.pessoal/the-smart-models-bluff-the-smart-model-80f158a3f0fa?sharedUserId=alfonso.pessoal** | 2 | [r/u_Glittering-Town5941](https://www.reddit.com/r/u_Glittering-Town5941/comments/1w4048n/the_smart_models_bluff_the_smart_model/) |
| https://medium.com/@alfonso.pessoal/the-smart-models-bluff-the-smart-model-80f158a3f0fa?sharedUserId=alfonso.pessoal | 2 | [r/u_Glittering-Town5941](https://www.reddit.com/r/u_Glittering-Town5941/comments/1w4048n/the_smart_models_bluff_the_smart_model/) |
| https://www.linkedin.com/in/alfonso-fontenla-neto/** | 2 | [r/u_Glittering-Town5941](https://www.reddit.com/r/u_Glittering-Town5941/comments/1w4048n/the_smart_models_bluff_the_smart_model/) |
| https://www.linkedin.com/in/alfonso-fontenla-neto/ | 2 | [r/u_Glittering-Town5941](https://www.reddit.com/r/u_Glittering-Town5941/comments/1w4048n/the_smart_models_bluff_the_smart_model/) |
| https://github.com/Apo-Z/netbird-cli | 2 | [r/netbird](https://www.reddit.com/r/netbird/comments/1tawewz/from_tailscale_to_netbird_migrated_my_overlay/) |
| https://huggingface.co/LGAI-EXAONE/K-EXAONE-2.0-750B-A37B-FP8 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vbchn4/kexaone_20_released/) |
| https://huggingface.co/LGAI-EXAONE/K-EXAONE-2.0-750B-A37B-NVFP4 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vbchn4/kexaone_20_released/) |
| https://huggingface.co/LGAI-EXAONE/K-EXAONE-2.0-750B-A37B-DSpark | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vbchn4/kexaone_20_released/) |
| https://www.marktechpost.com/2026/06/27/deepseek-releases-dspark-a-speculative-decoding-framework-that-accelerates-deepseek-v4-per-user-generation-60- | 2 | [r/machinelearningnews](https://www.reddit.com/r/machinelearningnews/comments/1uh83aw/deepseek_releases_dspark_a_speculative_decoding/) |
| https://rzr.to/wntj75 | 2 | [r/MouseReview](https://www.reddit.com/r/MouseReview/comments/1lwfbz6/daves_got_a_major_upgrade_meet_the_deathadder_v4/) |
| https://rzr.to/dav4pro | 2 | [r/MouseReview](https://www.reddit.com/r/MouseReview/comments/1lwfbz6/daves_got_a_major_upgrade_meet_the_deathadder_v4/) |
| https://www.youtube.com/watch?v=ILviUfGuIYw | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vdq9io/hermes_agent_with_deepseek_v4_builds_ai_workflows/) |
| https://github.com/rtk-ai/rtk | 2 | [r/codex](https://www.reddit.com/r/codex/comments/1udsqzm/you_can_really_feel_the_impact_of_ponytail_and/) |
| https://github.com/DietrichGebert/ponytail | 2 | [r/codex](https://www.reddit.com/r/codex/comments/1udsqzm/you_can_really_feel_the_impact_of_ponytail_and/) |
| https://www.youtube.com/watch?v=juawGwi960I | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vuzdd1/deepseek_harness_agent_is_free_and_runs_on_your/) |
| https://www.technologyreview.com/2026/04/24/1136422/why-deepseeks-v4-matters/ | 2 | [r/IA_Italia](https://www.reddit.com/r/IA_Italia/comments/1sv9oc9/ecco_lanalisi_del_mit_sul_nuovo_deepseek_v4_e_ci/) |
| https://github.com/autonomous-ai/autonomous-grid | 2 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1urnvw2/grid_hermes_opencode_keeping_my_main_agents/) |
| http://HANDBOOK.md | 2 | [r/Anthropic](https://www.reddit.com/r/Anthropic/comments/1w3c36a/opus_5_does_low_or_medium_effort_fix_its_behavior/) |
| https://github.com/tangtangtang1995/3D-Claw | 2 | [r/vibecoding](https://www.reddit.com/r/vibecoding/comments/1twkmwu/i_stresstested_deepseek_v4_pro_on_a_c_3d_geometry/) |
| https://www.marktechpost.com/2026/04/24/deepseek-ai-releases-deepseek-v4-compressed-sparse-attention-and-heavily-compressed-attention-enable-one-milli | 2 | [r/machinelearningnews](https://www.reddit.com/r/machinelearningnews/comments/1sumsja/deepseek_just_released_deepseekv4_at_1_million/) |
| https://github.com/antirez/ds4.git | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vge4l5/deepseek_v4_flash_0731_at_1017_ts_nothink_on/) |
| https://airia.com/request-demo/?utm_source=AI+Unraveled+&amp;utm_medium=Podcast&amp;utm_campaign=Q1+2026 | 2 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://www.sltrib.com/news/2026/04/25/hyperscale-data-center-may-be/ | 2 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| http://virtus.pro/en | 2 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| http://liquipedia.net/counterstrike/Mousesports | 2 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/872wmp/virtuspro_vs_mousesports_v4_future_sports/) |
| http://mousesports.com | 2 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/872wmp/virtuspro_vs_mousesports_v4_future_sports/) |
| http://twitter.com/mousesports | 2 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/872wmp/virtuspro_vs_mousesports_v4_future_sports/) |
| http://facebook.com/mousesports | 2 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/872wmp/virtuspro_vs_mousesports_v4_future_sports/) |
| http://youtube.com/user/mouzmovie | 2 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/872wmp/virtuspro_vs_mousesports_v4_future_sports/) |
| https://huggingface.co/RadixArk/Qwen3.8-Flash-Next-NVFP4 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w0x1r2/local_agentic_coding_benchmark_qwen38flashnext/) |
| https://huggingface.co/dealignai/Qwen3.8-Flash-Next-UNCENSORED-NVFP4 | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w0x1r2/local_agentic_coding_benchmark_qwen38flashnext/) |
| https://github.com/org2AI/ORG2 | 2 | [r/tauri](https://www.reddit.com/r/tauri/comments/1uejg9m/org2_opensource_cursor_alternative_built_with/) |
| https://github.com/FujiwaraChoki/mori-browser | 2 | [r/ArcBrowser](https://www.reddit.com/r/ArcBrowser/comments/1u94qnt/made_a_chromiumbased_arc_alternative_free/) |
| https://wonderrico.github.io/local\_llm\_benchmark/benchmark-main.html | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vg41ot/i_updated_my_localy_run_benchmark_with_deepseek/) |
| https://wonderrico.github.io/local_llm_benchmark/benchmark-main.html | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vg41ot/i_updated_my_localy_run_benchmark_with_deepseek/) |
| https://wonderrico.github.io/local\_llm\_benchmark/benchmark-detail.html | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vg41ot/i_updated_my_localy_run_benchmark_with_deepseek/) |
| https://wonderrico.github.io/local_llm_benchmark/benchmark-detail.html | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vg41ot/i_updated_my_localy_run_benchmark_with_deepseek/) |
| http://github.com/zouyee/dmlx | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1t5881z/dmlx_run_a_284bparameter_deepseek_v4_on_your_mac/) |
| https://github.com/Neroued/ninfer | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v8a7wb/nifer_is_insane_700ts_with_qwen_36_35b_no/) |
| https://www.youtube.com/watch?v=tmKaL5QovO0 | 2 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vs6y0z/deepseek_ai_harness_launched_with_deepseek_v4_pro/) |
| https://github.com/deepseek-ai/deepseek-harness | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vo6cvg/tool_tiny_opensource_widget_for_deepseek_v4/) |
| https://github.com/YMRYMR/deepseek-peak | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vo6cvg/tool_tiny_opensource_widget_for_deepseek_v4/) |
| http://virtus.pro/en/ | 2 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/d7pax9/mousesports_vs_virtuspro_v4_future_sports/) |
| https://www.youtube.com/watch?v=todMmp6AGCE&amp;t=1310s | 2 | [r/IA_Italia](https://www.reddit.com/r/IA_Italia/comments/1t2g5n5/salvatore_sanfilippo_mostra_deepseek_v4_flash_in/) |
| https://github.com/pkailas/DevMX | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v04rsv/you_guys_asked_for_it_my_local_coding_agent/) |
| https://github.com/penecho/penecho | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w1hijd/i_brought_deepseek_harness_to_the_canvas/) |
| https://llmgateway.io/changelog/runware-launch-discount | 2 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1v8dcje/we_partnered_with_runware_to_serve_opensource/) |
| https://www.datacamp.com/tutorial/how-to-run-deepseek-v4-flash-locally | 2 | [r/learnmachinelearning](https://www.reddit.com/r/learnmachinelearning/comments/1t5fsnt/learn_how_to_run_deepseek_v4_flash_locally_most/) |
| https://huggingface.co/unsloth/Inkling-Small-GGUF | 2 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1vb2dop/inklingsmall_is_out_now/) |
| https://github.com/Zorgonatis/Stabs-EDH | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1sz0od5/stabs_directives_preset_262_stability_and_cleanup/) |
| https://clawbox.com/blog/2026-08-14-deepseek-v4-is-live-on-clawbox-agentic-coding-jump | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vo82g2/deepseek_v4_went_ga_my_clawbox_switched_over_on/) |
| https://clawbox.com/ | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vo82g2/deepseek_v4_went_ga_my_clawbox_switched_over_on/) |
| https://djamgamind.com | 2 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://djamgamind.com/toolkit | 2 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://chat.deepseek.com/ | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1sxnvg2/has_anyone_tried_deepseek_v4_pro_flash_for_coding/) |
| https://platform.deepseek.com | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1sxnvg2/has_anyone_tried_deepseek_v4_pro_flash_for_coding/) |
| https://commonstack.ai/model-library/model?modelId=17bfa75d-af32-4dee-a721-a809309a3ff3 | 2 | [r/commonstack](https://www.reddit.com/r/commonstack/comments/1su6si6/deepseek_v4_is_now_available_on_commonstack/) |
| https://openspec.dev/ | 2 | [r/Zyte](https://www.reddit.com/r/Zyte/comments/1tfxxj4/spec_driven_web_scraping_projects_with_scrapy/) |
| https://github.com/zytelabs/scrapy-openspec | 2 | [r/Zyte](https://www.reddit.com/r/Zyte/comments/1tfxxj4/spec_driven_web_scraping_projects_with_scrapy/) |
| https://x.com/deepseek\_ai/status/2047516922263285776 | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1svf0c0/deepseek_deepseekv4_preview_is_officially_live/) |
| https://x.com/deepseek_ai/status/2047516922263285776 | 2 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1svf0c0/deepseek_deepseekv4_preview_is_officially_live/) |
| https://huggingface.co/webbrain-one/DeepSeek-V4-Flash-Vision-NVFP4 | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vfib06/deepseek_v4_flash_now_has_vision_support/) |
| https://github.com/tolaseadegbite/deepseek-peak.git | 2 | [r/omarchy](https://www.reddit.com/r/omarchy/comments/1vsr7ql/i_built_deepseek_peak_a_bar_widget_that_shows/) |
| https://github.com/tolaseadegbite/deepseek-peak | 2 | [r/omarchy](https://www.reddit.com/r/omarchy/comments/1vsr7ql/i_built_deepseek_peak_a_bar_widget_that_shows/) |
| https://optioai.net/ | 2 | [r/MicroSaaSBR](https://www.reddit.com/r/MicroSaaSBR/comments/1w3vv63/saia_do_lock_in_dos_provedores_de_ia/) |
| https://m.youtube.com/watch?v=qJLkQoeU144 | 2 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1sxz3zo/im_here_to_bring_you_the_weekly_sillytavern_news/) |
| https://github.com/coral-os/coral-code/blob/main/docs/using-coral-code-without-codex.md | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1v9im0o/a_graph_of_autonomous_deepseek_v4_pro_agents_is/) |
| https://youtu.be/cG1hI8eUy9M | 2 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1vs5jd8/ready_for_agent_harness_0270_released_allows_you/) |
| https://www.marktechpost.com/2026/07/18/kimi-k3-vs-deepseek-v4-pro-vs-glm-5-2-open-trillion-scale-moe-models-compared-on-benchmarks-license-and-servin | 2 | [r/AIDeveloperNews](https://www.reddit.com/r/AIDeveloperNews/comments/1v0dmzw/kimi_k3_vs_deepseek_v4_pro_vs_glm52_open/) |
| https://github.com/anomalyco/opencode/issues/28846 | 2 | [r/opencode](https://www.reddit.com/r/opencode/comments/1todc5z/has_the_price_for_deepseekv4pro_on_opencode_go/) |
| https://nahcrof.com/ | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vuesq0/update_to_best_deepseek_providers/) |
| https://opencode.ai/docs/go/ | 2 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1t31fdu/which_provider_is_actually_behind_deepseek_v4_pro/) |
| https://chat.qwen.ai/s/4216dca1-f92b-458a-9e05-f40c647c1914?fev=0.2.35 | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1scl1ni/i_fed_qwen_36_gemini_31_pro_and_whatever_version/) |
| https://chat.deepseek.com/share/xigyyvywzy2o5ey4xr | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1scl1ni/i_fed_qwen_36_gemini_31_pro_and_whatever_version/) |
| https://x.com/MTSlive/status/2087972201802989807/history | 2 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vodrm5/situation_explained_why_is_deepseek_raising/) |
| https://t.co/auLeHuK6GJ | 2 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vodrm5/situation_explained_why_is_deepseek_raising/) |
| https://x.com/MTSlive/status/2087895203315404864 | 2 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vodrm5/situation_explained_why_is_deepseek_raising/) |
| https://opncd.ai/share/0hehIwVf | 2 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1vytt6r/you_must_have_been_tired_of_all_the_frontend/) |
| https://artificialanalysis.ai/leaderboards/models?weights=open | 2 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vqykt1/qwen_38_27b_benchmarks_on_artificial_analysis/) |
| https://www.vals.ai/home | 2 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1su66f4/deepseek_v4_is_now_the_1_openweight_model_on_our/) |
| https://evals.stream/ | 2 | [r/IA_Italia](https://www.reddit.com/r/IA_Italia/comments/1umd2ah/do_your_own_evals/) |
| https://mp.weixin.qq.com/s/8bxXqS2R8Fx5-1TLDBiEDg | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1su4tk2/deepseek_v4_it_has_been_released/) |
| https://surgehq.ai/benchmarks/handbook | 2 | [r/Anthropic](https://www.reddit.com/r/Anthropic/comments/1w3a9k6/handbookmd_are_we_dealing_with_hallucinations/) |
| https://aipolcom.net/ | 2 | [r/PoliticalCompass](https://www.reddit.com/r/PoliticalCompass/comments/1w1jexw/someone_made_ai_models_take_a_political_compass/) |
| https://github.com/mzaki9/troy | 2 | [r/CommandCode](https://www.reddit.com/r/CommandCode/comments/1vv4xja/built_troy_after_getting_fed_up_with_9router_and/) |
| https://github.com/mypbs/mac-mlx-control-center | 2 | [r/huggingface](https://www.reddit.com/r/huggingface/comments/1w2d77k/macos_mlx_gui_with_huggingface_integration/) |
| https://artificialanalysis.ai/models/open-source#intelligence-index-vs-total-parameters | 2 | [r/singularity](https://www.reddit.com/r/singularity/comments/1vr3rvq/the_most_attractive_quadrant_is_already_occupied/) |
| https://openrouter.ai/inclusionai/ling-3.0-flash | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v4m5cr/antling30flash_is_now_live_on_openrouter_and_free/) |
| https://huggingface.co/spaces/tri-fair-lab/publications/blob/main/Thomson_1_0_Technical_Report.pdf | 2 | [r/legaltech](https://www.reddit.com/r/legaltech/comments/1vxd4qw/thomson_reuters_launch_their_own_generation_of/) |
| http://omahub.dev | 2 | [r/omarchy](https://www.reddit.com/r/omarchy/comments/1w3mie6/omahubdev_now_has_deterministic_anaylsis_and_ai/) |
| https://omahub.dev/plugins/dizziee.auto-wallpaper | 2 | [r/omarchy](https://www.reddit.com/r/omarchy/comments/1w3mie6/omahubdev_now_has_deterministic_anaylsis_and_ai/) |
| https://github.com/nick-friedrich/omahub | 2 | [r/omarchy](https://www.reddit.com/r/omarchy/comments/1w3mie6/omahubdev_now_has_deterministic_anaylsis_and_ai/) |
| https://github.com/mattzh72/articraft/pull/91 | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1u2qepa/deepseekv4pro_articraft_for_3d_cad_design/) |
| https://www.youtube.com/watch?v=Tr8t2vFQ4MQ | 2 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vo3leu/deepseek_v4_pro_brainstorming_commercial_product/) |
| https://aistudio.google.com/status | 2 | [r/GeminiAI](https://www.reddit.com/r/GeminiAI/comments/1w2btjw/gemini_37_down_for_anyone_else_falling_back_to_36/) |
| https://trackingai.org/political-test | 2 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1uxfodu/why_hasnt_this_changed_much_in_the_past_3_years/) |
| https://www.itraky.io/link/amazon/wr7zvc | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/0hs3yh | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/kvjkx7 | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/9o17am | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/2ydv26 | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/ei3o0h | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/yq31dy | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/hhd6qx | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/gea1fc | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/hrw6n6 | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/xsyq2f | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/ng3w36 | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/zgjgae | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/7ds46p | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/hlg3gw | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/qvz3ah | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/0ubs3z | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/ttx1nv | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/hal8wb | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/8xpy41 | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/jgho75 | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/ul1kqd | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/hjvnvq | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/spibf5 | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/c5zdsi | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/kznibb | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/5954tp | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/t9zvl1 | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/xcojw1 | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/w76w8m | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/9elbi7 | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/nta3iu | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://www.itraky.io/link/amazon/41lufi | 2 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://idownloadcoupon.com/udemy/3744/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3743/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3742/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3741/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3740/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3739/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3738/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3737/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3736/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3735/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3734/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3733/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3732/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3731/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3730/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3729/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3728/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3727/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3726/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3725/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3724/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3723/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3722/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3721/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3720/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3719/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3718/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3717/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3716/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3715/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3714/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3713/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3712/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3711/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3710/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3709/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3708/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3707/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3706/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3705/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3704/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3703/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3702/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3701/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3700/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3699/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3698/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3697/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3696/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3695/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3694/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3693/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3692/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3691/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3690/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3689/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3688/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3687/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3686/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3685/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3684/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3683/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3682/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3681/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3680/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3679/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3678/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3677/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3676/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3675/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3674/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3673/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3672/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3671/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3670/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3669/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3668/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3667/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3666/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3665/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3664/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3663/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3662/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3661/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3660/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3659/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3658/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3657/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3656/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3655/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3654/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3653/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3652/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3651/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3650/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3649/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3648/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3647/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3646/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3645/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3644/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3643/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3642/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3641/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3640/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3639/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3638/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3637/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3636/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3635/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3634/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3633/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3632/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3631/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3630/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3629/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3628/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3627/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3626/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3625/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3624/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3623/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3622/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3621/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3620/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3619/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3618/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/3617/ | 2 | [r/udemyfreebies](https://www.reddit.com/r/udemyfreebies/comments/1q42deh/list_of_free_and_best_selling_discounted_courses/) |
| http://127.0.0.1:8080 | 1 | [r/LocalAiCore](https://www.reddit.com/r/LocalAiCore/comments/1vkq5kj/running_deepseek_v4_flash_0731_locally_on_strix/) |
| https://github.com/Nathanw1014/strix-halo-llamacpp/issues/2 | 1 | [r/LocalAiCore](https://www.reddit.com/r/LocalAiCore/comments/1vkq5kj/running_deepseek_v4_flash_0731_locally_on_strix/) |
| https://github.com/Entrpi/ds4-on-spark | 1 | [r/LocalAiCore](https://www.reddit.com/r/LocalAiCore/comments/1vkq5kj/running_deepseek_v4_flash_0731_locally_on_strix/) |
| https://arxiv.org/abs/2606.19348 | 1 | [r/LocalAiCore](https://www.reddit.com/r/LocalAiCore/comments/1vkq5kj/running_deepseek_v4_flash_0731_locally_on_strix/) |
| https://huggingface.co/llmfan46/Qwen3.5-35B-A3B-uncensored-heretic | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1t4j7r5/masterthread_models_feedback_last_2_weeks/) |
| https://openrouter.ai/apps/hermes-agent | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1t4j7r5/masterthread_models_feedback_last_2_weeks/) |
| https://github.com/mostlygeek | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1t4j7r5/masterthread_models_feedback_last_2_weeks/) |
| https://github.com/erickong/aura-agent** | 1 | [r/Qwen_AI](https://www.reddit.com/r/Qwen_AI/comments/1tk3qbm/we_spent_28_hours_trying_to_beat_int4_on_qwen359b/) |
| https://github.com/lukaLLM/deepseek-v4-flash-dspark-rtx6000pro | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vmt1y3/i_ran_deepseek_v4_flash_284b_dspark_on_one_rtx/) |
| https://youtu.be/EDls1Popv1o | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vmt1y3/i_ran_deepseek_v4_flash_284b_dspark_on_one_rtx/) |
| http://127.0.0.1:8080/v1/models | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| http://127.0.0.1:8080/v1 | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://hermes-agent.nousresearch.com/docs/guides/local-llm-on-mac | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://insiderllm.com/guides/best-local-llms-mac-2026/ | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://github.com/raullenchai/Rapid-MLX | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://github.com/samuelfaj/lightning-mlx | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://machinelearning.apple.com/research/exploring-llms-mlx-m5 | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://modelfit.io/blog/speculative-decoding-mac-llm/ | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://unsloth.ai/docs/models/qwen3.6 | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://unsloth.ai/docs/models/gemma-4 | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://github.com/enescingoz/mac-llm-bench | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://lmstudio.ai/changelog | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://craftrigs.com/news/ollama-0-19-mlx-apple-silicon-speed/ | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://localaimaster.com/blog/apple-silicon-ai-buying-guide | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://llmcheck.net/benchmarks | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://www.sitepoint.com/local-llms-apple-silicon-mac-2026/ | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://andrew.ooo/answers/ollama-mlx-vs-ollama-metal-apple-silicon-2026/ | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://ianlpaterson.com/blog/lm-studio-fix-cannot-truncate-prompt-n-keep-n-ctx/ | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| https://developers.googleblog.com/bringing-gemma-4-12b-to-your-laptop-unlocking-local-agentic-workflows-with-google-ai-edge/ | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uc7rw5/mac_mlx_megathread_hermes_agent_on_apple_silicon/) |
| http://README.md | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1ridmnm/deepseek_v4_all_leaks_and_infos_for_the_release/) |
| https://elevenlabs.io/text-reader | 1 | [r/ClaudeAI](https://www.reddit.com/r/ClaudeAI/comments/1oivjvm/claude_code_is_a_beast_tips_from_6_months_of/) |
| https://www.naturalreaders.com/online/ | 1 | [r/ClaudeAI](https://www.reddit.com/r/ClaudeAI/comments/1oivjvm/claude_code_is_a_beast_tips_from_6_months_of/) |
| http://localhost:3002/api/endpoint | 1 | [r/ClaudeAI](https://www.reddit.com/r/ClaudeAI/comments/1oivjvm/claude_code_is_a_beast_tips_from_6_months_of/) |
| http://api-docs.deepseek.com/quick_start/agent_integrations/codex | 1 | [r/WebAfterAI](https://www.reddit.com/r/WebAfterAI/comments/1vcsmra/deepseek_put_a_retrained_v4flash_into_public_beta/) |
| http://dev.to | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| http://huggingface.co/DavidAU/Qwen3.6-27B-Heretic-Uncensored-FINETUNE-NEO-CODE-Di-IMatrix-MAX-GGUF | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| http://huggingface.co/froggeric/Qwen-Fixed-Chat-Templates | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| http://huggingface.co/HauhauCS/Qwen3.6-27B-Uncensored-HauhauCS-Balanced | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| http://huggingface.co/froggeric/Qwen3.6-27B-MTP-GGUF | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| http://qwen.readthedocs.io/en/latest/run_locally/llama.cpp.html | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| http://qwen.readthedocs.io/en/latest/framework/function_call.html | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| http://heyneo.com/blog/evaluating-qwen-3-6-27b-benchmarking-case-study | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| http://nathan.sapwell.net/posts/hauhaucs-abliteration-analysis/ | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| http://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1772 | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| http://aimadetools.com/blog/qwen-3-6-27b-vs-35b-a3b/ | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| http://insiderllm.com/guides/qwen-3-6-local-ai-guide/ | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ub1i7z/sharing_my_current_localcloud_hybrid_setup_qwen/) |
| https://huggingface.co/bullerwins/DeepSeek-V4-Flash-GGUF | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1uz76sp/deepseek_v4_flash_iq3_xxsas_iq2_s_bench_mainline/) |
| http://speculative.py | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vpo15s/psa_qwen3827b_dspark_works_in_vllm/) |
| https://files.catbox.moe/bak1mp.json | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1udubji/i_forked_the_disco_elysium_skills_lorebook_added/) |
| https://files.catbox.moe/aprrsq.json | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1udubji/i_forked_the_disco_elysium_skills_lorebook_added/) |
| https://files.catbox.moe/yg64iv.json | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1udubji/i_forked_the_disco_elysium_skills_lorebook_added/) |
| https://files.catbox.moe/uoitye.json | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1udubji/i_forked_the_disco_elysium_skills_lorebook_added/) |
| https://files.catbox.moe/7labie.json | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1udubji/i_forked_the_disco_elysium_skills_lorebook_added/) |
| https://files.catbox.moe/17cvg9.png | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1udubji/i_forked_the_disco_elysium_skills_lorebook_added/) |
| http://api.feihoa.com/v1%60 | 1 | [r/Qwen_AI](https://www.reddit.com/r/Qwen_AI/comments/1w2md1s/gonna_give_feihoa_a_shot/) |
| https://github.com/LettuceAI/app | 1 | [r/ChatbotRefugees](https://www.reddit.com/r/ChatbotRefugees/comments/1tgki5p/ai_basics_day_10_vram_math_and_quantisation_or/) |
| https://www.lettuceai.app | 1 | [r/ChatbotRefugees](https://www.reddit.com/r/ChatbotRefugees/comments/1tgki5p/ai_basics_day_10_vram_math_and_quantisation_or/) |
| http://localhost:1234/v1 | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ud03si/cost_token_optimization_megathread_hermes_agent/) |
| https://github.com/local-inference-lab | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ttlp99/deepseek_v4_flash_performance_on_dgx_spark/) |
| https://github.com/local-inference-lab/vllm/tree/dev/unholy-fusion | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ttlp99/deepseek_v4_flash_performance_on_dgx_spark/) |
| https://github.com/aidendle94 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ttlp99/deepseek_v4_flash_performance_on_dgx_spark/) |
| https://github.com/Fringe210/llama.cpp-deepseek-v4-flash-cuda | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1t94ito/i_have_deepseek_v4_pro_at_home/) |
| https://github.com/antirez/llama.cpp-deepseek-v4-flash | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1t94ito/i_have_deepseek_v4_pro_at_home/) |
| https://nitter.net/ArtificialAnlys/status/2038898584566002111#m | 1 | [r/ArtificialNtelligence](https://www.reddit.com/r/ArtificialNtelligence/comments/1skft5w/katcoderpro_v2_12x_cheaper_but_rivals_claude/) |
| https://www.atlascloud.ai/models/kwaipilot/kat-coder-pro-v2 | 1 | [r/ArtificialNtelligence](https://www.reddit.com/r/ArtificialNtelligence/comments/1skft5w/katcoderpro_v2_12x_cheaper_but_rivals_claude/) |
| https://krater.ai/?model=Kwaipilot%3A%20KAT-Coder-Pro%20V2#pricing | 1 | [r/ArtificialNtelligence](https://www.reddit.com/r/ArtificialNtelligence/comments/1skft5w/katcoderpro_v2_12x_cheaper_but_rivals_claude/) |
| https://artificialanalysis.ai/models/kat-coder-pro-v2/providers | 1 | [r/ArtificialNtelligence](https://www.reddit.com/r/ArtificialNtelligence/comments/1skft5w/katcoderpro_v2_12x_cheaper_but_rivals_claude/) |
| https://artificialanalysis.ai/models/kat-coder-pro-v2 | 1 | [r/ArtificialNtelligence](https://www.reddit.com/r/ArtificialNtelligence/comments/1skft5w/katcoderpro_v2_12x_cheaper_but_rivals_claude/) |
| https://streamlake.com/product/kat-coder | 1 | [r/ArtificialNtelligence](https://www.reddit.com/r/ArtificialNtelligence/comments/1skft5w/katcoderpro_v2_12x_cheaper_but_rivals_claude/) |
| https://github.com/criterium/opencode-lab/blob/main/research/control-flags-vs-plan-build/README.md | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1ttxclt/deepseek_v4_flash_vs_deepseek_v4_pro_agent_prompt/) |
| https://github.com/modelscope/ms-swift/commit/ab726e9d445a6520a70df2c831177d46adb1f589 | 1 | [r/LocalLLaMa_V2](https://www.reddit.com/r/LocalLLaMa_V2/comments/1vvzckl/qwen_38_27b_one_week_later_quants_context_tool/) |
| https://github.com/modelscope/ms-swift/commit/a45f1d4f73157ba59062a7fd1f55a40dae759156 | 1 | [r/LocalLLaMa_V2](https://www.reddit.com/r/LocalLLaMa_V2/comments/1vvzckl/qwen_38_27b_one_week_later_quants_context_tool/) |
| https://www.dropbox.com/scl/fi/0itykjpziq3q2hb61xeqv/Writer-s-Block-Unlimited-Release-1.json?rlkey=duf7fs5c9qo3znesckwj37bl1&amp;st=x22rluro&amp;dl=0* | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vqontp/new_preset_writers_block_unlimited_framework_an/) |
| https://www.dropbox.com/scl/fi/0itykjpziq3q2hb61xeqv/Writer-s-Block-Unlimited-Release-1.json?rlkey=duf7fs5c9qo3znesckwj37bl1&amp;st=x22rluro&amp;dl=0 | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vqontp/new_preset_writers_block_unlimited_framework_an/) |
| https://www.dropbox.com/scl/fi/slfzhov5enc2mrol1qbsu/Writer-s-Block-Unlimited-Deiomo-s-Personal-Setup.json?rlkey=qzhmxfwxu48qj69mrq2o1cypc&amp;st=0zxa | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vqontp/new_preset_writers_block_unlimited_framework_an/) |
| https://www.dropbox.com/scl/fi/slfzhov5enc2mrol1qbsu/Writer-s-Block-Unlimited-Deiomo-s-Personal-Setup.json?rlkey=qzhmxfwxu48qj69mrq2o1cypc&amp;st=0zxa | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vqontp/new_preset_writers_block_unlimited_framework_an/) |
| https://www.dropbox.com/scl/fi/0itykjpziq3q2hb61xeqv/Writer-s-Block-Unlimited-Release-1.json?rlkey=duf7fs5c9qo3znesckwj37bl1&amp;st=iqhlk5bu&amp;dl=0* | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vqontp/new_preset_writers_block_unlimited_framework_an/) |
| https://www.dropbox.com/scl/fi/0itykjpziq3q2hb61xeqv/Writer-s-Block-Unlimited-Release-1.json?rlkey=duf7fs5c9qo3znesckwj37bl1&amp;st=iqhlk5bu&amp;dl=0 | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vqontp/new_preset_writers_block_unlimited_framework_an/) |
| https://www.dropbox.com/scl/fi/slfzhov5enc2mrol1qbsu/Writer-s-Block-Unlimited-Deiomo-s-Personal-Setup.json?rlkey=qzhmxfwxu48qj69mrq2o1cypc&amp;st=6ewj | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vqontp/new_preset_writers_block_unlimited_framework_an/) |
| https://www.dropbox.com/scl/fi/slfzhov5enc2mrol1qbsu/Writer-s-Block-Unlimited-Deiomo-s-Personal-Setup.json?rlkey=qzhmxfwxu48qj69mrq2o1cypc&amp;st=6ewj | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vqontp/new_preset_writers_block_unlimited_framework_an/) |
| https://aws.amazon.com/cn/sustainability/ | 1 | [r/aiwars](https://www.reddit.com/r/aiwars/comments/1tuvr0s/considering_that_no_one_wants_to_calculate/) |
| https://huggingface.co/gwejgteheg/gemma-4-26B-A4B-it-qat-DeepSeek-distill-GGUF | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ur1i1a/distilled_deepseek_into_gemma_4_26ba4b_vs_12b_not/) |
| https://huggingface.co/gwejgteheg/gemma-4-12B-IT-QAT-Q4_K_M-DeepSeek-distill-GGUF | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ur1i1a/distilled_deepseek_into_gemma_4_26ba4b_vs_12b_not/) |
| https://huggingface.co/datasets/gwejgteheg/natural_questions_pair/tree/main | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ur1i1a/distilled_deepseek_into_gemma_4_26ba4b_vs_12b_not/) |
| https://github.com/kainlang/kain | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/stdlib/cuda.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/tree/master/ml/src | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/tree/master/blades/semantic-search/src | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/blades/shaderlib/gpu_showcase.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/blades/shaderlib/blackhole.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/benchmark/cases_v2/gpu_cpu_pipeline.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/benchmark/cases_v2/fusion_chain.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/tree/master/blades/markscript | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/blades/tools/kg/src/killgrep.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/tree/master/blades/experiments/convergence | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/blades/experiments/pong/pong.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/tree/master/blades/web/electron | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/runtime/native/src/core/z3/proofs-experimental/arena-low-hi-nonoverlap.smt2 | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/docs-tsv/error_codes.tsv | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/tree/master/crates/semantic/error_corpus | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/training/kain_omni.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/tree/master/docs-tsv | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/training/HoloGEHv2.md | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/benchmark/cases_v2/keyword_crucible.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://logicdriver.com/ | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/benchmark/cases/contention_wall/main.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| http://mylib.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| http://app.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| http://app.artifacts.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| http://app.evidence.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://raw.githubusercontent.com/kainlang/kain/refs/heads/master/blades/amalgamate/src/std.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/blades/python/python_interop_god.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/blades/reson8/test/reson8.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/blades/three-kn/three.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/blades/c/ffmpeg/src/ffmpeg_abi.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/blades/c/nuklear/main.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/smoketest/src/interop/sqlite_rally.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/blades/markscript/src/jit.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/tree/master/blades/templates/cli | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/tree/master/blades/templates/starter | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/blades/templates/build/build.kn | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/docs-tsv/cli_commands.tsv | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/blob/master/docs/CLI.md | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/tree/master/docs | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://zentako.xyz/ | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://github.com/kainlang/kain/tree/master/blades/os | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vd4amo/kain_a_new_systems_language_targeting/) |
| https://vapi.ezmanga.org/api/v1/series/{slug}/chapters/chapter-{n} | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1ubxhen/is_deepseek_actually_good/) |
| https://z.ai/Zhipu | 1 | [r/coolgithubprojects](https://www.reddit.com/r/coolgithubprojects/comments/1uv6w44/i_built_a_thing_that_delegates_claude_codes_grunt/) |
| http://localhost:8080/v1 | 1 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1ubzcmn/dwarfstar_ds4_deepseek_v4_flash_in_locale_con_api/) |
| https://huggingface.co/antirez/deepseek-v4-gguf | 1 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1ubzcmn/dwarfstar_ds4_deepseek_v4_flash_in_locale_con_api/) |
| https://antirez.com/news/167 | 1 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1ubzcmn/dwarfstar_ds4_deepseek_v4_flash_in_locale_con_api/) |
| https://x.com/antirez/status/2052405820235678175 | 1 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1ubzcmn/dwarfstar_ds4_deepseek_v4_flash_in_locale_con_api/) |
| https://ollama.com/install.sh | 1 | [r/better_claw](https://www.reddit.com/r/better_claw/comments/1tn9err/run_a_fully_local_ai_agent_for_0_no_bs/) |
| https://api-docs.deepseek.com/quick_start/agent_integrations/reasonix/ | 1 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1vdlw3u/deepseek_ha_un_coding_agent_nella_doc_ufficiale/) |
| https://reasonix.io/ | 1 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1vdlw3u/deepseek_ha_un_coding_agent_nella_doc_ufficiale/) |
| https://ollama.com/pricing | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://docs.z.ai/guides/overview/pricing | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://ai.google.dev/gemini-api/docs/pricing | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://platform.openai.com/docs/pricing | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://openai.com/chatgpt/pricing | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://platform.claude.com/docs/en/about-claude/pricing | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://platform.claude.com/docs/en/build-with-claude/zero-data-retention | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://portal.nousresearch.com/privacy | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://hermes-agent.nousresearch.com/docs/integrations/providers | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://huggingface.co/unsloth/Qwen3.8-27B-GGUF | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://openrouter.ai/api/v1/models | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1w3ghs1/august_cloud_model_megathread/) |
| https://algoshop.ai/products/ | 1 | [r/Shopify_Merchant](https://www.reddit.com/r/Shopify_Merchant/comments/1uqnsaq/beyond_support_why_2026_ecommerce_needs_an/) |
| http://pi.dev | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w21qz0/visual_comparison_of_various_models_a_very/) |
| https://www.youtube.com/watch?v=S-Y-hA\_\_RX4 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w21qz0/visual_comparison_of_various_models_a_very/) |
| https://www.youtube.com/watch?v=S-Y-hA__RX4 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w21qz0/visual_comparison_of_various_models_a_very/) |
| https://www.youtube.com/watch?v=nr\_WxCRElCA | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w21qz0/visual_comparison_of_various_models_a_very/) |
| https://www.youtube.com/watch?v=nr_WxCRElCA | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w21qz0/visual_comparison_of_various_models_a_very/) |
| https://github.com/ggml-org/llama.cpp/pull/25247 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1une2il/i_merged_fixes_for_quantized_kv_cache_into_my/) |
| https://github.com/ggml-org/llama.cpp/pull/25303 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1une2il/i_merged_fixes_for_quantized_kv_cache_into_my/) |
| https://github.com/ggml-org/llama.cpp/pull/25202 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1une2il/i_merged_fixes_for_quantized_kv_cache_into_my/) |
| https://huggingface.co/MiniMaxAI/MiniMax-M3 | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vqq92m/life_after_deepseek_the_king_is_dead_comparing/) |
| https://chat.qwen.ai/legal-agreement/models | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vqq92m/life_after_deepseek_the_king_is_dead_comparing/) |
| https://huggingface.co/moonshotai/Kimi-K2.7-Code | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vqq92m/life_after_deepseek_the_king_is_dead_comparing/) |
| https://docs.agent-vault.dev/guides/hermes-on-vps | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| http://localhost:1234/v1/models | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| http://[tailscale-ip | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| https://github.com/Infisical/agent-vault | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| https://varlock.dev | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| https://infisical.com | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| https://developer.1password.com/docs/cli | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| https://tailscale.com | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| https://pinggy.io | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| https://syncthing.net | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| https://github.com/terion-name/terrarium | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| https://github.com/jaylfc/tinyagentos | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| https://foxinthebox.io | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| https://github.com/devpals399/best_hermes_vps_providers | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) |
| https://github.com/cchuter/llama.cpp/tree/feat/v4-port-cuda | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1taclsw/deepseek_v4_in_llamacpp_flash_pro_cuda_metal/) |
| https://huggingface.co/teamblobfish/DeepSeek-V4-Flash-GGUF | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1taclsw/deepseek_v4_in_llamacpp_flash_pro_cuda_metal/) |
| https://huggingface.co/teamblobfish/DeepSeek-V4-Pro-GGUF | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1taclsw/deepseek_v4_in_llamacpp_flash_pro_cuda_metal/) |
| https://github.com/cchuter/llama.cpp | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1taclsw/deepseek_v4_in_llamacpp_flash_pro_cuda_metal/) |
| http://X.com | 1 | [r/cursor](https://www.reddit.com/r/cursor/comments/1uywf62/significantly_lower_value_in_cursor_subscription/) |
| https://x.com/SemiAnalysis\_/status/2064815044085318040?s=20 | 1 | [r/cursor](https://www.reddit.com/r/cursor/comments/1uywf62/significantly_lower_value_in_cursor_subscription/) |
| https://x.com/SemiAnalysis_/status/2064815044085318040?s=20 | 1 | [r/cursor](https://www.reddit.com/r/cursor/comments/1uywf62/significantly_lower_value_in_cursor_subscription/) |
| https://www.youtube.com/playlist?list=PLZHQObOWTQDNU6R1\_67000Dx\_ZCJB-3pi | 1 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://www.youtube.com/playlist?list=PLZHQObOWTQDNU6R1_67000Dx_ZCJB-3pi | 1 | [r/Chai_Unofficial](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) |
| https://github.com/mariozechner/pi-coding-agent | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1u9fa2w/my_hermes_setup_roast_me/) |
| https://ollama.com/v1/chat/completions | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w3ia28/an_analysis_of_the_inference_nonconvergence_and/) |
| https://ollama.com/api/show | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w3ia28/an_analysis_of_the_inference_nonconvergence_and/) |
| https://ollama.com/v1 | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w3ia28/an_analysis_of_the_inference_nonconvergence_and/) |
| http://agent.md | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w3ia28/an_analysis_of_the_inference_nonconvergence_and/) |
| https://github.com/ollama/ollama/issues/17892 | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w3ia28/an_analysis_of_the_inference_nonconvergence_and/) |
| https://ollama.com | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w3ia28/an_analysis_of_the_inference_nonconvergence_and/) |
| https://github.com/ggml-org/llama.cpp | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w3ia28/an_analysis_of_the_inference_nonconvergence_and/) |
| https://www.youtube.com/watch?v=MMUAvB0\_qU4 | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vqrup2/deepseek_v4_pro_0813_nearly_matches_top_models_on/) |
| https://www.youtube.com/watch?v=MMUAvB0_qU4 | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vqrup2/deepseek_v4_pro_0813_nearly_matches_top_models_on/) |
| https://github.com/kvcache-ai/ktransformers | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1tdpk3f/i_have_even_faster_deepseek_v4_pro_at_home/) |
| https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/DeepSeek-V4-Flash.md | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1tdpk3f/i_have_even_faster_deepseek_v4_pro_at_home/) |
| https://github.com/eugr/llama-benchy | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1tdpk3f/i_have_even_faster_deepseek_v4_pro_at_home/) |
| https://openrouter.ai/deepseek/deepseek-v4-flash:free | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) |
| https://docs.claude.com/ | 1 | [r/Qwen_AI](https://www.reddit.com/r/Qwen_AI/comments/1ts15j1/run_claude_code_with_qwen37_and_stop_hitting/) |
| https://app.manifest.build/ | 1 | [r/Qwen_AI](https://www.reddit.com/r/Qwen_AI/comments/1ts15j1/run_claude_code_with_qwen37_and_stop_hitting/) |
| https://docs.claude.com | 1 | [r/ManifestforAI](https://www.reddit.com/r/ManifestforAI/comments/1ts10h0/run_claude_code_with_qwen37_and_stop_hitting/) |
| https://app.manifest.build | 1 | [r/ManifestforAI](https://www.reddit.com/r/ManifestforAI/comments/1ts10h0/run_claude_code_with_qwen37_and_stop_hitting/) |
| https://buymeacoffee.com/ammaaralam | 1 | [r/singularity](https://www.reddit.com/r/singularity/comments/1sxapqb/differences_between_gpt_54_and_gpt_55_on_minebench/) |
| https://github.com/Ammaar-Alam/minebench/releases/tag/3.3.2 | 1 | [r/singularity](https://www.reddit.com/r/singularity/comments/1sxapqb/differences_between_gpt_54_and_gpt_55_on_minebench/) |
| https://x.com/minebench_ai | 1 | [r/singularity](https://www.reddit.com/r/singularity/comments/1sxapqb/differences_between_gpt_54_and_gpt_55_on_minebench/) |
| https://huggingface.co/poolside/Laguna-XS.2 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/talkie-lm/talkie-1930-13b-it | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/XiaomiMiMo/MiMo-V2.5-Pro | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/empirischtech/DeepSeek-R1-Distill-Qwen-32B-gptq-4bit | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Max-and-Omnis/Nemotron-3-Super-64B-A12B-Math-REAP-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/leonsarmiento/Qwen3.6-27B-3bit-mlx | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/lordx64/Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/z-lab/Qwen3.6-35B-A3B-DFlash | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/hesamation/Qwen3.6-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/openai/privacy-filter | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Jackrong/Qwopus-GLM-18B-Merged-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/OBLITERATUS/gemma-4-E4B-it-OBLITERATED | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/TurbulenceDeterministe/Carnice-9b-W8A16-AWQ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/cturan/Olmo-3-7B-Instruct-Q1_0 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/aoxo/sarvam-30b-uncensored/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/AIDC-AI/Marco-Mini-Instruct/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Zigeng/DMax-Coder-16B/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/lolzinventor/Qwen3.5-4B-Base-ZitGen-V1/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/FINAL-Bench/Darwin-4B-David | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/GAIR-NLP/daVinci-LLM | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/LilaRest/gemma-4-31B-it-NVFP4-turbo | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/tanaos/tanaos-text-summarization-v1/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/zai-org/GLM-5 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/DavidAU/gemma-4-31B-it-Mystery-Fine-Tune-HERETIC-UNCENSORED-Thinking | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/meituan-longcat/LongCat-Next | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/byteshape/Qwen3.5-9B-GGUF/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/prism-ml/Bonsai-8B-gguf | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Hcompany/Holo3-35B-A3B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/FINAL-Bench/Darwin-35B-A3B-Opus/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/daksh-neo/acervo-extractor-qwen3.5-9b-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/arcee-ai/Trinity-Large-Thinking/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/mudler/apex-quant/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/agentscope-ai/CoPaw-Flash-9B/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/microsoft/harrier-oss-v1-27b | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/iwalton3/sycofact | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/ai-sage/GigaChat3.1-10B-A1.8B-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/ibm-granite/granite-4.0-3b-vision | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/HauhauCS/Nemotron3-Nano-4B-Uncensored-HauhauCS-Aggressive | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/zhengmh/OmniVTG-7B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Jackrong/Qwopus3.6-27B-v1-preview-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/unsloth/Kimi-K2.6-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Qwen/Qwen3.6-27B-FP8 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/HauhauCS/Qwen3.6-27B-Uncensored-HauhauCS-Aggressive/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/inclusionAI/LLaDA2.0-Uni | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/unsloth/Qwen3.6-27B-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Qwen/Qwen3.6-27B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/unsloth/Mistral-Small-4-119B-2603-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Jackrong/Qwopus3.5-27B-v3-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/facebook/tribev2/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/LiquidAI/LFM2.5-VL-450M | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/LG-AI-EXAONE/EXAONE-4.5/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/google/gemma-4-26B-A4B-it/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/google/gemma-4-E4B-it | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Jiunsong/supergemma4-26b-uncensored-gguf-v2/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/dealignai/Gemma-4-31B-JANG_4M-CRACK | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/google/gemma-4-31B-it/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/tencent/HY-Embodied-0.5 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/LeapLabTHU/RvR | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/SeeSee21/Z-Anime | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Yovecent/UDM-GRPO | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Tencent/MegaStyle | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Yanran21/UniGenDet | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/kwanY/styleid/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/shiyi-zh0408/Meta-CoT | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/OpenSenseNova/SenseNova-U1 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/NucleusAI/Nucleus-Image | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/nvidia/Lyra-2.0 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/tencent/HY-World-2.0 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/LH-Tech-AI/GyroScope/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/EasonXiao-888/SpatialEdit | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/CSU-JPG/FlowInOne | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/GenSearcher/Gen-Searcher-8B/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/baidu/ERNIE-Image | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Parveshiiii/breast-cancer-detector | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/neuralvfx/Z-Image-SAM-ControlNet/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/PixelSmile/PixelSmile | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/renderartist/Toon-Tacular-Qwen-LoRA | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/peteromallet/VibeComfy/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/abrahamcasanova/meeseeks-hive | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Corbell-AI/evalmonkey/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/lerim-dev/lerim-cli | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/openleash/openleash/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/PasiKoodaa/SlopLobster | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/manpoai/AgentOffice | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/comp-a-a-s/compaas | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Aayush-engineer/tracemind/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/spring-ai-community/spring-ai-playground/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Bitterbot-AI/bitterbot-desktop | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/saint0x/mesh/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/0xku/kon | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/agents-io/PokeClaw/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/sandroandric/AgentHandover/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Alex188dot/agensic/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Harshit-J004/toolguard | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/zhiheng-huang/toolloop | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/final-run/finalrun-agent | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/sipeed/llmdev.guide | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/n8te0/adonis_flux2klein/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Lightricks/LTX-Desktop/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/ThetaCursed/Illustrious-NoobAI-Style-Explorer | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/gjnave/moss-audio-gff/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/LH-Tech-AI/Shield-82M | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Kaden-Schutt/hipfire | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/aiptimizer/TurboOCR | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/CaoAnda/ENMP-LoRAMerging/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/vivoCameraResearch/SmartPhotoCrafter | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Hong-yu-Zhang/TS-Attn | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/CompVis/patch-forcing | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Adamlong3/DynamicRad/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/facebook/sapiens2-pose-5b/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Shelley-Golan/ParetoSlider/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/ahmetkumass/yolo-gen | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/BigStationW/Local-MCP-server/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/niklasfrick/spark-dashboard/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/LoanLemon/Omnix/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/SoftwareLogico/omni-cli | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Steelskull/CWT-V5.6 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/shivampkumar/trellis-mac | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/SamuelTallet/ZPix | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Aryagm/dflash-mlx | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/LuqP2/Image-MetaHub/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/MangoLion/stretchystudio | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/PRITHIVSAKTHIUR/Flux.2-4B-Encoder-Comparator/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/phanii9/Tidbit | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/AuthBits/webmcp/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Josh-blythe/bordair-multimodal | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/PurpleDoubleD/locally-uncensored | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/DorukYelken/Model-Database-Protocol | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/mandarwagh9/openeyes/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/jncchds/abook/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/lightfeed/scrapedown/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/suncloudsmoon/quizzer | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/TheMothX/MothBench | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/christopherthompson81/vernacula | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/arte-fact/llama-monitor | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/z-lab/dflash | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Gaurox/AI-Metadata-Inspector/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/skkut/SilkStack-Image-Browser | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/ServeurpersoCom/acestep.cpp | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/LogicStamp/logicstamp-context/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/akdeb/open-toys | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/zomry1/Samuraizer/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Corbell-AI/Corbell/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/rohitg00/ai-engineering-from-scratch/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/shitagaki-lab/see-through/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/o-l-l-i/simple-captioner/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/vangel76/HybridScorer | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/KazeKaze93/adetailer-hires-sync/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Pikselkroken/pixlstash/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/mozilla-ai/llamafile/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/M0R1C/TagForge/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/yashkc2025/turboquant | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/vmDeshpande/ai-agent-automation | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/JonnaMat/huggingface-slack-app | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/mozi1924/Qwen3-TTS-EasyFinetuning | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/nimblecloud13/Sift | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/apple/ml-videoflextok/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/bytedance-research/GRN/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/Tencent-Hunyuan/DisCa | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/OpenImagingLab/AnyRecon | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Motif-Technologies/Motif-Video-2B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/netflix/void-model | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/alibaba-damo-academy/Lumos-Custom | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Skywork/Matrix-Game-3.0/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/xiaomi-research/controlfoley/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/Trelis/Chorus-v1-GGML | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/k2-fsa/OmniVoice | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/ACE-Step/acestep-v15-xl-turbo | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/RoyalCities/Foundation-1 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/meituan-longcat/LongCat-AudioDiT/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/oumoumad/LumiPic | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/mo230761/UniGeo | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/lovis93/crt-animation-terminal-ltx-2.3-lora | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/dx8152/Flux2-Klein-9B-Consistency | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/oumoumad/LTX-2.3-22b-IC-LoRA-Outpaint | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/jason1966/CoPaw-Flash-9B-DataAnalyst-LoRA | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/LiconStudio/Ltx2.3-VBVR-lora-I2V | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/ThetaCursed/Danbooru-Dataset-Filter | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/gazingstars123/Anima-Standalone-Trainer | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://github.com/modl-org/modl/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/datasets/TaobaoTmall-AlgorithmProducts/Tstars-VTON | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/datasets/pthinc/BCE-Prettybird-Nano-Math-v0.1 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://huggingface.co/datasets/FINAL-Bench/World-Model | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) |
| https://asari.ai/blog/inference-optimization | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://intology.ai/blog/scaling-automated-post-training | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://x.com/epochairesearch/status/2084308067844538692 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://x.com/dandr1s/status/2084624838895767593 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://x.com/venturetwins/status/2084353489061499021 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://x.com/prz_chojecki/status/2084586636122190316 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://vibemathed.com/stats | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.nature.com/articles/s41467-026-76264-2 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://science.xyz/technologies/scifi/ | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://x.com/elonmusk/status/2084304083851034949 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://x.com/javilopen/status/2084263340574945329 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://x.com/thsottiaux/status/2084483765158719542 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.cnbc.com/2026/08/04/caterpillar-cat-q2-2026-earnings.html | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.bloomberg.com/news/articles/2026-08-04/anthropic-inks-10-billion-computing-deal-with-new-cloud-startup | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.ft.com/content/549f2e23-5aa2-49c7-9ea6-a9784ab7087c | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://x.com/SpaceX/status/2084723854534951218 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.theinformation.com/newsletters/ai-agenda/google-deepmind-exec-says-unprecedented-capex-actually-bet-rsi | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://x.com/cb_doge/status/2084628645721616722 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.theinformation.com/briefings/major-pc-makers-start-using-memory-chips-chinas-cxmt | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.bloomberg.com/news/articles/2026-08-04/huawei-s-top-scientist-warns-of-chip-limit-nvidia-will-soon-face | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.theinformation.com/briefings/trump-administration-mulls-ban-chinese-data-center-devices | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.nytimes.com/2026/08/04/technology/ai-washington-regulation-whiplash.html | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.theinformation.com/articles/white-house-host-ai-companies-tuesday-review-ai-framework | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.axios.com/2026/08/03/white-house-finalizes-ai-framework-behind-closed-doors | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.bloomberg.com/news/articles/2026-08-03/china-is-getting-more-anxious-about-mythos-before-trump-meets-xi | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.cnbc.com/2026/08/03/palantir-karp-open-ai-anthropic-open-weight.html | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.cnbc.com/2026/08/03/palantir-pltr-earnings-q2-2026.html | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.bloomberg.com/news/articles/2026-08-03/amazon-joins-elite-list-of-stocks-to-top-3-trillion-in-value | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.axios.com/2026/08/03/ai-talent-wars-openai-google-meta-anthropic | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.cnbc.com/2026/08/04/ai-tax-preparers.html | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://arstechnica.com/culture/2026/08/an-ai-supervised-remote-exam-went-so-badly-that-58000-students-must-retake-it/ | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://fortune.com/2026/08/03/power-ai-khosla-a16z-bet-startup-reinvent-mining-mariana-minerals/ | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.ft.com/content/7600731b-4f7f-4d38-a478-3196c565a880 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://www.liberationtimes.com/home/ufo-history-is-being-shaped-in-washington-no-one-knows-how-this-ends | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) |
| https://raw.githubusercontent.com/local-inference-lab/blackwell-llm-docker/main/examples/docker-compose-ds4-dspark-infernal-invocation-cu133-r21.yml | 1 | [r/localinferencelab](https://www.reddit.com/r/localinferencelab/comments/1w3czj9/deepseekv4flash0731_infernal_invocation_r21/) |
| https://raw.githubusercontent.com/local-inference-lab/blackwell-llm-docker/main/examples/docker-compose-ds4-infernal-invocation-cu133-r21.yml | 1 | [r/localinferencelab](https://www.reddit.com/r/localinferencelab/comments/1w3czj9/deepseekv4flash0731_infernal_invocation_r21/) |
| https://github.com/local-inference-lab/blackwell-llm-docker/blob/main/examples/docker-compose-ds4-dspark-infernal-invocation-cu133-r21.yml | 1 | [r/localinferencelab](https://www.reddit.com/r/localinferencelab/comments/1w3czj9/deepseekv4flash0731_infernal_invocation_r21/) |
| https://github.com/local-inference-lab/blackwell-llm-docker/blob/main/examples/docker-compose-ds4-infernal-invocation-cu133-r21.yml | 1 | [r/localinferencelab](https://www.reddit.com/r/localinferencelab/comments/1w3czj9/deepseekv4flash0731_infernal_invocation_r21/) |
| https://github.com/local-inference-lab/rtx6kpro/issues/67 | 1 | [r/localinferencelab](https://www.reddit.com/r/localinferencelab/comments/1w3czj9/deepseekv4flash0731_infernal_invocation_r21/) |
| https://github.com/local-inference-lab/b12x/pull/243 | 1 | [r/localinferencelab](https://www.reddit.com/r/localinferencelab/comments/1w3czj9/deepseekv4flash0731_infernal_invocation_r21/) |
| https://github.com/local-inference-lab/b12x/pull/246 | 1 | [r/localinferencelab](https://www.reddit.com/r/localinferencelab/comments/1w3czj9/deepseekv4flash0731_infernal_invocation_r21/) |
| https://github.com/local-inference-lab/b12x/pull/247 | 1 | [r/localinferencelab](https://www.reddit.com/r/localinferencelab/comments/1w3czj9/deepseekv4flash0731_infernal_invocation_r21/) |
| https://api-docs.deepseek.com/quick\_start/agent\_integrations/codex | 1 | [r/chutesAI](https://www.reddit.com/r/chutesAI/comments/1vn8197/deepseekv4pro0813_is_official_agent_benchmarks/) |
| https://poolside.ai/get-started | 1 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1tznq52/cheap_and_free_llm_apis_for_the_token_price_hike/) |
| https://mistral.ai | 1 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1tznq52/cheap_and_free_llm_apis_for_the_token_price_hike/) |
| https://mistral.ai/vibe/install.sh | 1 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1tznq52/cheap_and_free_llm_apis_for_the_token_price_hike/) |
| https://build.nvidia.com/nvidia | 1 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1tznq52/cheap_and_free_llm_apis_for_the_token_price_hike/) |
| https://extra.wuu73.org/chu5 | 1 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1tznq52/cheap_and_free_llm_apis_for_the_token_price_hike/) |
| https://www.youtube.com/watch?v=zEyPDdKKd\_s | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1verlev/i_tested_deepseek_v4_flash_new_across_multiple_ai/) |
| https://www.youtube.com/watch?v=zEyPDdKKd_s | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1verlev/i_tested_deepseek_v4_flash_new_across_multiple_ai/) |
| http://interleaved.My | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1svzlog/the_exact_kv_cache_usage_of_deepseek_v4/) |
| https://inferencex.semianalysis.com/overview?utm\_source=chatgpt.com | 1 | [r/stocks](https://www.reddit.com/r/stocks/comments/1vrmj5g/heres_why_openaianthropic_will_not_go_bankrupt/) |
| https://api-docs.deepseek.com/quick_start/pricing/?article_id=article_1779470751466_8 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vrjk4m/qwen_38_27b_saved_me_650_in_api_costs_this_evening/) |
| https://www.anthropic.com/news/claude-sonnet-5 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vrjk4m/qwen_38_27b_saved_me_650_in_api_costs_this_evening/) |
| https://www.anthropic.com/news/claude-opus-4-6 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vrjk4m/qwen_38_27b_saved_me_650_in_api_costs_this_evening/) |
| https://omlx.ai/benchmarks/performance/3051ak7s | 1 | [r/MacStudio](https://www.reddit.com/r/MacStudio/comments/1w2wj1d/which_mac_studio_for_local_ai/) |
| https://omlx.ai/benchmarks/performance/yytzfrep | 1 | [r/MacStudio](https://www.reddit.com/r/MacStudio/comments/1w2wj1d/which_mac_studio_for_local_ai/) |
| https://omlx.ai/benchmarks/performance/fax1o712 | 1 | [r/MacStudio](https://www.reddit.com/r/MacStudio/comments/1w2wj1d/which_mac_studio_for_local_ai/) |
| https://omlx.ai/benchmarks/performance/0lxqhg22 | 1 | [r/MacStudio](https://www.reddit.com/r/MacStudio/comments/1w2wj1d/which_mac_studio_for_local_ai/) |
| https://artificialanalysis.ai/models/gpt-5-6-sol | 1 | [r/MacStudio](https://www.reddit.com/r/MacStudio/comments/1w2wj1d/which_mac_studio_for_local_ai/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/tree/main | 1 | [r/MacStudio](https://www.reddit.com/r/MacStudio/comments/1w2wj1d/which_mac_studio_for_local_ai/) |
| https://huggingface.co/unsloth/GLM-5.3-GGUF/tree/main/UD-Q4_K_XL | 1 | [r/MacStudio](https://www.reddit.com/r/MacStudio/comments/1w2wj1d/which_mac_studio_for_local_ai/) |
| https://zencoder.ai/it/blog/best-llm-for-coding | 1 | [r/esperimenti_con_AI](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) |
| https://osatech.ch/it/differenze-tra-chatgpt-e-deepseek-quale-ai-scegliere-nel-2025/ | 1 | [r/esperimenti_con_AI](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) |
| https://zencoder.ai/it/blog/best-ai-agents-for-coding | 1 | [r/esperimenti_con_AI](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) |
| https://www.aranzulla.it/migliori-ai-per-programmare-1726714.html | 1 | [r/esperimenti_con_AI](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) |
| https://zencoder.ai/it/blog/best-ai-for-coding | 1 | [r/esperimenti_con_AI](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) |
| https://clickup.com/it/blog/470038/alternative-al-windsurf | 1 | [r/esperimenti_con_AI](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) |
| https://www.youtube.com/watch?v=ZkomgBKi6g8&amp;t=38 | 1 | [r/esperimenti_con_AI](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) |
| https://sviluppatoremigliore.com/blog/migliore-ai-per-programmare | 1 | [r/esperimenti_con_AI](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) |
| https://cdn.deepseek.com/api-docs/codex-deepseek-setup-en.ps1 | 1 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1vmkq4i/deepseek_v4_pro_è_ufficiale_rilasciata_la_build/) |
| https://opencode.ai/data/deepseek/deepseek-v4-pro | 1 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1vmkq4i/deepseek_v4_pro_è_ufficiale_rilasciata_la_build/) |
| https://huggingface.co/useful-quants/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-W4A16 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vnu219/nemotron_35_lightning_30ba3b_w4a16_vs_iq4_xs_on/) |
| https://github.com/haraldh/llama.cpp/blob/dspark-dsv4/convert_hf_to_gguf.py | 1 | [r/StrixHalo](https://www.reddit.com/r/StrixHalo/comments/1vcz5zi/deepseekv4flash0731_on_bosgame_m5_with_rtx_pro/) |
| https://openrouter.ai/api | 1 | [r/ClaudeAI](https://www.reddit.com/r/ClaudeAI/comments/1v1u4oo/need_help_to_validate_fix_api_usage_costs_with/) |
| http://github.com/jayminban/41-llms-evaluated-on-19-benchmarks | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1n57hb8/i_locally_benchmarked_41_opensource_llms_across/) |
| https://huggingface.co/antirez/deepseek-v4-gguf/blob/main/DeepSeek-V4-Flash-IQ2XXS-w2Q2K-AProjQ8-SExpQ8-OutQ8-chat-v2-imatrix.gguf | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1uy53xr/q2_deepseek_v4_flash_on_2x_3080_20gb_64gb_ddr5_17/) |
| https://github.com/fairydreaming/llama.cpp | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1uy53xr/q2_deepseek_v4_flash_on_2x_3080_20gb_64gb_ddr5_17/) |
| https://github.com/vektorprime/llama.cpp/tree/prompt\_template\_llama** | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1uhcf9t/does_anyone_here_have_a_prefilled_prompt_solution/) |
| https://github.com/vektorprime/llama.cpp/tree/prompt_template_llama | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1uhcf9t/does_anyone_here_have_a_prefilled_prompt_solution/) |
| http://0.0.0.0:8000 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1uhcf9t/does_anyone_here_have_a_prefilled_prompt_solution/) |
| https://flowstacks.xyz/workflows/hermes-moa-virtual-model | 1 | [r/WebAfterAI](https://www.reddit.com/r/WebAfterAI/comments/1uh84a2/hermes_now_lets_you_stack_frontier_models_into/) |
| https://webafterai.substack.com/p/two-new-ways-to-get-top-tier-ai-without | 1 | [r/WebAfterAI](https://www.reddit.com/r/WebAfterAI/comments/1uh84a2/hermes_now_lets_you_stack_frontier_models_into/) |
| https://www.youtube.com/watch?v=\_VoN6ZC65aY | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vfgo7a/deepseek_v4_flash_0731_just_shocked_everyone/) |
| https://www.youtube.com/watch?v=_VoN6ZC65aY | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vfgo7a/deepseek_v4_flash_0731_just_shocked_everyone/) |
| https://www.betterclaw.io/ | 1 | [r/better_claw](https://www.reddit.com/r/better_claw/comments/1vrmi8h/v4_pro_output_went_from_087_to_396_peak_355/) |
| https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/danish-foundation-models/DFM-Mimir | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/noctrex/Ling-3.0-tiny-MXFP4_MOE-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/SupraLabs/SupraElegans-500k/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/Motif-Technologies/Motif-3 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/kurakurai/Luth-2-2B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/azomDev/TinyTitle | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/Qwen/Qwen3.8-2.4T-A95B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/ReadyArt/gemma-4-31B-it-scotoma-2-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/huihui-ai/Huihui-DeepSeek-V4-Flash-0731-abliterated-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/deepgrove/maple-preview | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/poolside/Laguna-S-2.1-FP8 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/SupraLabs/SupraBrain-50M | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/SupraLabs/Supra2-100M | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/ai9stars/G9v3-39A5B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/AxiomicLabs/GPT-X2.5-135M | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/inclusionAI/Ling-3.0-flash | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/LiquidAI/LFM2.5-2.6B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/amd/Instella-MoE-16B-A3B-Think | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/skt/A.X-K2 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/Harikrish2727/BetterGPT-150M | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/TheOneWhoWill/Shibai-700M-Base | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/meituan-longcat/LongCat-Flash-Lite-Sparse | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/EschaLabs/Qwen3.6-35B-A3B-Escha-W2 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/XYZAILab/XYZ-Aquila-pro | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/nota-ai/Solar-Open2-250B-Nota-NVFP4/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/XYZAILab/XYZ-Aquila-mini | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/Kwaipilot/KAT-Coder-V2.5-Dev | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/dots-studio/dots3-note-prev | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/orcarouter/Qwen3.8-27B-Uncensored-FP8/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/tencent/UI-Mate-27B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/WinterCharm/Qwen3.5-122B-A10B-wMix38 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/om-ai-lab/VLX-Seek | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/LiquidAI/LFM2.5-VL-3B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/CohereLabs/North-Micro-Vision-Instruct | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/endless-frontier/BigBang-v1 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/meta-models/Muse-Glimmer-30B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/nvidia/NVIDIA-Nemotron-Parse-2.0 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/mistralai/Shieldstral-1.0-3B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/DavidAU/Qwen3.6-27B-Fable-Fusion-711-Uncensored-Heretic-NM-DAU-NEO-MAX-MTP-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/WinterCharm/Qwen3.5-122B-A10B-wMix58 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/internlm/Intern-S2-Mobius | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/LuffyTheFox/Qwen3.6-35B-A3B-Uncensored-Genesis-Hermes-V7-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/ethanfel/Qwen3-VL-32B-Ultra-Heretic-H3-ComfyUI-INT8-ConvRot | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/empero-ai/Qwythos-27B-v1 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/EpistemeAI/Reasoning-Medical-27B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/DavidAU/Qwen3.5-9B-The-Defiant-Fable-Uncensored-Heretic-NEO-IMATRIX-MAX-MTP-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/LuffyTheFox/Qwen3.6-35B-A3B-Uncensored-Genesis-Hermes-V6-GGUF | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/microsoft/Mage-VL | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/microsoft/Fara1.5-27B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/thinkingmachines/Inkling-Small | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/moonshotai/Kimi-K3 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/Gazingstars123/Anima-2.9B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/ByteDance/Bernini-Diffusers-v2 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/Lightricks/LTX-2.5/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Wan-Video/Wan-Animate-2 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/Abiray/MiniMax-H3-nvfp4-INT4-INT8-Convrot | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/SandAI-org/MAGI-2-preview | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/MiniMaxAI/MiniMax-Music3 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/nvidia/magpie_tts_multilingual_357m/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/nvidia/NVIDIA-NemotronLabs-VoiceChat-11B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/microsoft/VibeVoice-ASR-BitNet | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/owensong/Inflect-Nano-v2 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Audio8-AI/Audio8_TTS | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/owensong/Inflect-Micro-v2 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/ModelTC/Minimax-H3-Turbo | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/lightx2v/MiniMax-H3-Prompt-Rewriter-LoRA | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/fal/MiniMax-H3-Realism-People-LoRA | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/jimmycarter/krea2-turbo-bbox | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/lodestones/Kroma | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/felladrin/gguf-trainer | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/CompactifAI/Full-Chunked-KL-Loss/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/alvdansen/signet-trainer | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/perfectgf/lora-dataset-studio | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/datasets/SupraLabs/LLM-self-identification | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/BlackMixture/Mix-Studio | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/rjalexa/llmprices | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/BMB12d3/minimax-h3-prompt-composer | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/coder3101/nanorp | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/andrewyng/openworker | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/agenta-ai/agenta | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Unicorn-Commander/unicorn-stable-oss | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/PoopMan333/Video_Tools | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/UDPSendToFailed/ninfer-4090 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/JustANormalTinkerer/hayai-ocr-v2 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://huggingface.co/tencent/EVIE-Preview-4.5B | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/RAZZULLIX/KAISEN | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/run-llama/ExtractBench | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/XiaomiRobotics/Xiaomi-Robotics-1 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/nicedreamzapp/nemotron-omni-mlx | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Danmoreng/talk-to-pi | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/sqliteai/warp | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/slvDev/esp32-ai | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/PurpleDirective/quillpdf-mcp | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Waversense/srt2speech | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/cursor/mixture-of-kittens | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Adeliox/krea-multi-lora | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/maziyarpanahi/openmed | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Nocturne-Ai-Labs/Umbra-Studio/ | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/RmaNMetaverse/ComfyUI-Orchestrator-LAN | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/misutesu-desu/H3-AutoPromptChain | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/ruashots/ComfyUI-OpenH3-IR | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/threegee409/ComfyUI-MiniMaxMusic3-Advanced | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/vizart-vj/ComfyUI-MiniMax-H3-LongMedia | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/marcsole96/ComfyUI-Subgraph-Preview | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/envy-ai/ComfyUI-cache-monitor | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/newsbubbles/ComfyUI_Neurodes | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/IronChurro/Eddie_Cat_Nodes | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/seitanism/ComfyUI-H3-Motion-Context-MultiRef | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/j955229/ComfyUI-MiniMax-H3-Motion-Director | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/BigStationW/ComfyUi-MiniMax-H3-Image-And-Reference-To-Video | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/alvasafin-art/ComfyUI-AVS-SSD-ReadAhead | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/embedding-shapes/ComfyUI-SweepGrid | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Andy294753951/ComfyUI-Flow-Wrangler | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/alvasafin-art/ComfyUI-AVS-Intel-XPU-VRAM-Fix | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/FNGarvin/ComfyUI-Model-Mover | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/ByronLeeeee/ComfyUI-MiniMax-H3-Optimization-Suite | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/duckyshell/ComfyUI-MiniMaxH3-Prompt-Writer | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Ercelcan/ComfyUI-MiniMax-Creator | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/ScenemaAI/ComfyUI-ScenemaAudio | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/vtokic/ComfyUI-cable-management | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/capitan01R/ComfyUI-SigmaSync-LoRA | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Nif00/ComfyUI-Spectrum-Ideogram4 | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Ding-sl/ComfyUI-LinkSpotlight | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/ahkimkoo/ComfyUI-MIDI-Edit | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/seeker-ktf/ComfyUI-ReStartupFlags | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Damkohler/JLC-Flux2-ControlNet | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Adudeguyman/ComfyUI-Fantastic-MiniMaxH3-PromptBuilder | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/PuppetMasterAI/ComfyUI-vram-tracker | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/SonderSaid/ComfyUI-Sonder-Editor | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/Azornes/Comfyui-Model-Resolver | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/dcmomia/ComfyUI-HF-SuperDownloader | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/ultramuseart/famegrid-auto-color | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://github.com/CliffNodes/Krea2-Multi-Character-Lora-Node-w-bounding-box | 1 | [r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) |
| https://platberlitz.github.io | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vzsvs2/presetmediumweight_the_ethereality_express_10_a/) |
| https://github.com/autonomous-ai/autonomous-grid/ | 1 | [r/LocalAIServers](https://www.reddit.com/r/LocalAIServers/comments/1vzplp5/i_code_with_qwen3827b_on_my_potato_t480/) |
| https://www.autonomous.ai/datacenter | 1 | [r/LocalAIServers](https://www.reddit.com/r/LocalAIServers/comments/1vzplp5/i_code_with_qwen3827b_on_my_potato_t480/) |
| https://www.autonomous.ai/computer | 1 | [r/LocalAIServers](https://www.reddit.com/r/LocalAIServers/comments/1vgzvjs/built_a_2x_rtx_pro_6000_box_to_serve_deepseek/) |
| https://www.morphllm.com/deepseek-v4 | 1 | [r/AiAgentts](https://www.reddit.com/r/AiAgentts/comments/1tf50u7/deepseek_v4_dropped_april_24th_and_the_pricing/) |
| https://openrouter.ai/openai/gpt-5.5 | 1 | [r/AiAgentts](https://www.reddit.com/r/AiAgentts/comments/1tf50u7/deepseek_v4_dropped_april_24th_and_the_pricing/) |
| https://tvtropes.org/pmwiki/pmwiki.php/Main/StringTheory | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://imgur.com/a/9lRvFD4 | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://imgur.com/a/ZypGG0l | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://mindhacks.com/2013/08/22/the-deafening-silence/ | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://www.cnet.com/tech/mobile/bose-investigates-mysterious-quietcomfort-35-firmware-issue/ | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://www.digitaltrends.com/home-theater/bose-qc35-firmware-anc-damage-rollback/ | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://thedroidguy.com/bose-quietcomfort-ii-firmware-update-worsens-noise-cancelling-1106611 | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://community.sony.co.uk/t5/portable-audio/wh-1000xm3-noise-cancelling-performance-ruined-by-v4-1-1-firmware/td-p/2592166 | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://www.theverge.com/2020/1/17/21069953/apple-airpods-pro-noise-cancellation-problems-firmware-2b588-2c54 | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://discussions.apple.com/thread/251909973 | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://www.rtings.com/headphones/1-5/graph#16092/7981 | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://www.rtings.com/assets/pages/Ur5io1Sj/airpods-max-noise-isolation-firmware-3b71-small.jpg | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://www.rtings.com/headphones/reviews/bose/quietcomfort-35-ii-qc35-ii-wireless-2018 | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://web.archive.org/web/20200410064938mp_/https://community.bose.com/t5/Around-On-Ear-Headphones/Bose-QC-35-Firmware-4-5-2-Noise-Cancellation-Inve | 1 | [r/apple](https://www.reddit.com/r/apple/comments/yn09lm/no_apple_is_almost_certainly_not_ruining_their/) |
| https://github.com/ggml-org/llama.cpp/pull/24231 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ulymml/llamacpp_patch_deepseek_v4_flash_running_with/) |
| https://huggingface.co/antirez/deepseek-v4-gguf/blob/main/DeepSeek-V4-Flash-Layers37-42Q4KExperts-OtherExpertLayersIQ2XXSGateUp-Q2KDown-AProjQ8-SExpQ8 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ulymml/llamacpp_patch_deepseek_v4_flash_running_with/) |
| https://github.com/lsennn/Deus-ex-machina/releases/download/v2.0/DEUS.EX.MACHINA.V2.2.ST.json | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1w10cl5/preset_deus_ex_machina_v2_goodbye_thinking_hello/) |
| https://github.com/lsennn/Deus-ex-machina/releases/download/v2.0/DEUS.EX.MACHINA.V2.2.Tavo.json | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1w10cl5/preset_deus_ex_machina_v2_goodbye_thinking_hello/) |
| https://github.com/lsennn/Deus-ex-machina/releases/download/v2.0/DEM.Summaryception.custom.prompt.txt | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1w10cl5/preset_deus_ex_machina_v2_goodbye_thinking_hello/) |
| http://ebookaloud.com | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1uductw/i_built_an_ebook_to_audiobook_converter_using/) |
| https://github.com/body-clock/bodyclock.nvim | 1 | [r/PiCodingAgent](https://www.reddit.com/r/PiCodingAgent/comments/1u8c6sz/are_you_guys_actually_building_real_stuff_with_pi/) |
| https://every.to/guides/compound-engineering | 1 | [r/PiCodingAgent](https://www.reddit.com/r/PiCodingAgent/comments/1u8c6sz/are_you_guys_actually_building_real_stuff_with_pi/) |
| https://github.com/jasim/layered-rails-skills | 1 | [r/PiCodingAgent](https://www.reddit.com/r/PiCodingAgent/comments/1u8c6sz/are_you_guys_actually_building_real_stuff_with_pi/) |
| https://github.com/inertia-rails/skills | 1 | [r/PiCodingAgent](https://www.reddit.com/r/PiCodingAgent/comments/1u8c6sz/are_you_guys_actually_building_real_stuff_with_pi/) |
| https://opencode.ai/go?ref=H42H0AY66V | 1 | [r/PiCodingAgent](https://www.reddit.com/r/PiCodingAgent/comments/1u8c6sz/are_you_guys_actually_building_real_stuff_with_pi/) |
| https://www.deepseek.com/en/ | 1 | [r/PiCodingAgent](https://www.reddit.com/r/PiCodingAgent/comments/1u8c6sz/are_you_guys_actually_building_real_stuff_with_pi/) |
| https://milkcrate.fm/explore | 1 | [r/PiCodingAgent](https://www.reddit.com/r/PiCodingAgent/comments/1u8c6sz/are_you_guys_actually_building_real_stuff_with_pi/) |
| https://bodyclock.fm/ | 1 | [r/PiCodingAgent](https://www.reddit.com/r/PiCodingAgent/comments/1u8c6sz/are_you_guys_actually_building_real_stuff_with_pi/) |
| https://www.youtube.com/watch?v=qeMyzsZ\_4\_I&amp;t=2s | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vpquid/agent_os_workflow_builds_custom_ai_skills_fast/) |
| https://www.youtube.com/watch?v=qeMyzsZ_4_I&amp;t=2s | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vpquid/agent_os_workflow_builds_custom_ai_skills_fast/) |
| https://labs.ground-truth.ai/benchmark-your-own-traffic\ | 1 | [r/mlops](https://www.reddit.com/r/mlops/comments/1vnzbas/benchmarking_on_your_own_production_data/) |
| https://hero699.github.io/sharetext-app/#share=N4IglgJiBcIFZwNYEYBmAnEAaEAXMuANgKYwgCqAdvkcRAAQDKlYADq8btiAMYD21YtTIBiegCUAriQDO9AGT0AwgNzEAHrgA6lHQBE | 1 | [r/GeminiAI](https://www.reddit.com/r/GeminiAI/comments/1vhf7vc/best_creative_writing_models_of_2026_v2/) |
| https://huggingface.co/collections/Cactus-Compute/cactus-hyb | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v3nw3j/cactus_hybrid_we_taught_gemma_4_to_know_when_its/) |
| https://huggingface.co/collections/Cactus-Compute/cactus-hybrid-6a60da4551074db058e8bb64 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v3nw3j/cactus_hybrid_we_taught_gemma_4_to_know_when_its/) |
| https://x.com/XiaomiMiMo/status/2059314052892099070 | 1 | [r/GithubCopilot](https://www.reddit.com/r/GithubCopilot/comments/1tpxccf/mimo_v25pro_57_to_99_price_drop_matching_deepseek/) |
| https://pbs.twimg.com/media/HJQmxYtaQAAIBCE?format=jpg&amp;name=4096x4096 | 1 | [r/GithubCopilot](https://www.reddit.com/r/GithubCopilot/comments/1tpxccf/mimo_v25pro_57_to_99_price_drop_matching_deepseek/) |
| https://pbs.twimg.com/media/HJQmyruakAEjwk7?format=jpg&amp;name=4096x4096 | 1 | [r/GithubCopilot](https://www.reddit.com/r/GithubCopilot/comments/1tpxccf/mimo_v25pro_57_to_99_price_drop_matching_deepseek/) |
| https://github.com/yusufkaraaslan/Skill\_Seekers | 1 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://github.com/yusufkaraaslan/Skill_Seekers | 1 | [r/LovingOpenSourceAI](https://www.reddit.com/r/LovingOpenSourceAI/comments/1s2bfyq/open_source_ai_resource_list_curated_ongoing/) |
| https://freebuff.ai/ | 1 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1trj6ow/freebuff_una_cli_gratuita_per_usare_agenti_ai_di/) |
| https://github.com/antirez/ds4/tree/glm5.2 | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1upct2h/deepseek_v4_flash_via_ds4_is_the_best_model_you/) |
| http://beta.crof.ai | 1 | [r/CrofAI](https://www.reddit.com/r/CrofAI/comments/1sc3nsw/crofai_affordable_multimodel_ai_access_with_cheap/) |
| http://crof.ai | 1 | [r/CrofAI](https://www.reddit.com/r/CrofAI/comments/1sc3nsw/crofai_affordable_multimodel_ai_access_with_cheap/) |
| http://crof.ai/pricing | 1 | [r/CrofAI](https://www.reddit.com/r/CrofAI/comments/1sc3nsw/crofai_affordable_multimodel_ai_access_with_cheap/) |
| http://crof.ai/tos | 1 | [r/CrofAI](https://www.reddit.com/r/CrofAI/comments/1sc3nsw/crofai_affordable_multimodel_ai_access_with_cheap/) |
| http://crof.ai/privacy | 1 | [r/CrofAI](https://www.reddit.com/r/CrofAI/comments/1sc3nsw/crofai_affordable_multimodel_ai_access_with_cheap/) |
| http://crof.ai/docs | 1 | [r/CrofAI](https://www.reddit.com/r/CrofAI/comments/1sc3nsw/crofai_affordable_multimodel_ai_access_with_cheap/) |
| https://opencode.ai/auth | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| http://opencode.ai/auth | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| http://opencode.ai/zen/go/v1/chat/completions | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| http://item.id | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| http://item.name | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| http://tc.id | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| http://tc.name | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| http://t.name | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| http://tc.function.name | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| http://converted.id | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| http://chatBody.stream | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) |
| https://github.com/KritBlade/MVU_Game_Maker/releases | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1svavzk/mvu_game_maker_v095_slice_of_lifedating_sim_with/) |
| https://github.com/N0VI028/JS-Slash-Runner | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1svavzk/mvu_game_maker_v095_slice_of_lifedating_sim_with/) |
| https://codeberg.org/zonde306/ST-Prompt-Template/ | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1svavzk/mvu_game_maker_v095_slice_of_lifedating_sim_with/) |
| https://discord.gg/C6HabNwzn7 | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1svavzk/mvu_game_maker_v095_slice_of_lifedating_sim_with/) |
| https://rentry.org/freaky-frankenstein-presets | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1svavzk/mvu_game_maker_v095_slice_of_lifedating_sim_with/) |
| https://github.com/KritBlade/MVU\_Game\_Maker | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1svavzk/mvu_game_maker_v095_slice_of_lifedating_sim_with/) |
| https://github.com/KritBlade/MVU\_Zod\_StatusMenuBuilder | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1svavzk/mvu_game_maker_v095_slice_of_lifedating_sim_with/) |
| https://github.com/KritBlade/MVU_Zod_StatusMenuBuilder | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1svavzk/mvu_game_maker_v095_slice_of_lifedating_sim_with/) |
| http://platform.moonshot.ai | 1 | [r/dev_venezuela](https://www.reddit.com/r/dev_venezuela/comments/1u6jgal/claude_code_criollo_cómo_programo_con_ia_sin/) |
| https://opencode.ai/** | 1 | [r/dev_venezuela](https://www.reddit.com/r/dev_venezuela/comments/1u6jgal/claude_code_criollo_cómo_programo_con_ia_sin/) |
| https://opencode.ai/ | 1 | [r/dev_venezuela](https://www.reddit.com/r/dev_venezuela/comments/1u6jgal/claude_code_criollo_cómo_programo_con_ia_sin/) |
| https://huggingface.co/docs/transformers/v4.46.0/en/internal/generation\_utils#transformers.SynthIDTextWatermarkingConfig | 1 | [r/LocalTextToSpeech](https://www.reddit.com/r/LocalTextToSpeech/comments/1udgq58/eu_ai_act_requires_text_from_models_and_providers/) |
| https://huggingface.co/docs/transformers/v4.46.0/en/internal/generation_utils#transformers.SynthIDTextWatermarkingConfig | 1 | [r/LocalTextToSpeech](https://www.reddit.com/r/LocalTextToSpeech/comments/1udgq58/eu_ai_act_requires_text_from_models_and_providers/) |
| https://opencode.ai/docs/zen/#pricing:~:text=%240.25- | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1uo0nxj/why_is_opencode_pricing_for_deepseek_v4_pro_is_4x/) |
| https://openrouter.ai/deepseek/deepseek-v4-pro#providers | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1uo0nxj/why_is_opencode_pricing_for_deepseek_v4_pro_is_4x/) |
| https://openrouter.ai/deepseek/deepseek-v4-pro?provider=DeepSeek#pricing | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1uo0nxj/why_is_opencode_pricing_for_deepseek_v4_pro_is_4x/) |
| https://commandcode.ai/docs/resources/pricing-limits#deepseek-v4-pro-4x-usage | 1 | [r/PiCodingAgent](https://www.reddit.com/r/PiCodingAgent/comments/1t4faft/i_built_a_pi_custom_provider_for_command_code/) |
| https://github.com/patlux/pi-commandcode-provider | 1 | [r/PiCodingAgent](https://www.reddit.com/r/PiCodingAgent/comments/1t4faft/i_built_a_pi_custom_provider_for_command_code/) |
| https://www.perplexity.ai/hub/blog/meet-new-sonar | 1 | [r/perplexity_ai](https://www.reddit.com/r/perplexity_ai/comments/1jm2ekd/message_from_aravind_cofounder_and_ceo_of/) |
| https://x.com/AravSrinivas/status/1904571071250260110 | 1 | [r/perplexity_ai](https://www.reddit.com/r/perplexity_ai/comments/1jm2ekd/message_from_aravind_cofounder_and_ceo_of/) |
| http://127.0.0.1:11434/v1 | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vjwfa5/deepseekv4flash0731284b_on_a_64g_m5_pro_mac_65/) |
| https://github.com/yanun0323/deepseek_ssd | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1vjwfa5/deepseekv4flash0731284b_on_a_64g_m5_pro_mac_65/) |
| https://atomic.chat/ | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1svnjns/deepseek_v4_pro_vs_gpt55_for_building_simple_game/) |
| https://github.com/Goochbeater/Spiritual-Spell-Red-Teaming/blob/e7f2ef88cf105d86c678aff45f73e7d2e6176d43/Jailbreak-Guide/Other%20LLMs/DeepSeek/ENI%20L | 1 | [r/ClaudeAIJailbreak](https://www.reddit.com/r/ClaudeAIJailbreak/comments/1u0vl5e/here_are_the_best_ai_to_write_coherent_erotica/) |
| https://github.com/Goochbeater/Spiritual-Spell-Red-Teaming/blob/e7f2ef88cf105d86c678aff45f73e7d2e6176d43/Jailbreak-Guide/Other%20LLMs/KIMI/KIMI%20K2.6 | 1 | [r/ClaudeAIJailbreak](https://www.reddit.com/r/ClaudeAIJailbreak/comments/1u0vl5e/here_are_the_best_ai_to_write_coherent_erotica/) |
| https://github.com/Handyfff/Subreddit-to-Google-Drive-using-BDFR-and-Google-Collab/blob/c7cb9ca46d801aeb62a3331f4aa5b118398051ed/Deepseek%20Chat%20Ref | 1 | [r/ClaudeAIJailbreak](https://www.reddit.com/r/ClaudeAIJailbreak/comments/1u0vl5e/here_are_the_best_ai_to_write_coherent_erotica/) |
| https://news.ycombinator.com/item?id=49119559 | 1 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1vbmks4/deepseek_ha_aggiornato_v4_flash_in_silenzio_e_i/) |
| https://openai.com/index/gpt-5-6/ | 1 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1vbmks4/deepseek_ha_aggiornato_v4_flash_in_silenzio_e_i/) |
| http://Chorus.codes | 1 | [r/ClaudeCode](https://www.reddit.com/r/ClaudeCode/comments/1sxs8c0/claude_codex_opencode_god_mode/) |
| https://ollama.com/library | 1 | [r/Saudi_Homelab](https://www.reddit.com/r/Saudi_Homelab/comments/1tvzn24/اخيرا_لقيتكم/) |
| https://ollama.com/ | 1 | [r/Saudi_Homelab](https://www.reddit.com/r/Saudi_Homelab/comments/1tvzn24/اخيرا_لقيتكم/) |
| https://llama-cpp.com/ | 1 | [r/Saudi_Homelab](https://www.reddit.com/r/Saudi_Homelab/comments/1tvzn24/اخيرا_لقيتكم/) |
| https://vllm.ai/ | 1 | [r/Saudi_Homelab](https://www.reddit.com/r/Saudi_Homelab/comments/1tvzn24/اخيرا_لقيتكم/) |
| https://apps.apple.com/ca/app/machine-learning-for-dummies-p/id1610947211 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1glh6bs/today_in_aiml_apple_prepares_developers_for_siris/) |
| https://link.mail.beehiiv.com/ss/c/u001.s9F2vg9H0NMFC01qj9PgtPzCeVyV0_SgxMHmFD0K__BE9FlYpDyIzvAVwIdeq2TSNddaaLiYnHTy1v4phs4Wsj09WtR6nlVb0A_aOEFpVTTOrD | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1glh6bs/today_in_aiml_apple_prepares_developers_for_siris/) |
| https://link.mail.beehiiv.com/ss/c/u001.Q334NVcZU4O6L6VKRz8ijIX3CcwCnzWIkW25JLil9iwHa4Nc0KT-uB4DZd5VjQnuW0SLPKnZn8Mk39e2Wc6GmgSnatbDyhS6Rs1AgGlrZqmJAQ | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1glh6bs/today_in_aiml_apple_prepares_developers_for_siris/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf_MnrMNPlyZa0tC_fQ34TxQ78dU03jIigb7dPAeatjyN8KUPvsxeU6PYp4w80qFkbpXgQC87SbLaBWxTze2HjTOIjq | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1glh6bs/today_in_aiml_apple_prepares_developers_for_siris/) |
| https://apps.apple.com/ca/app/master-ai-machine-learning-pro/id1610947211?platform=iphone | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1glh6bs/today_in_aiml_apple_prepares_developers_for_siris/) |
| https://apps.apple.com/ca/app/master-ai-machine-learning-pro/id1610947211 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1glh6bs/today_in_aiml_apple_prepares_developers_for_siris/) |
| https://x.com/Zai\_org/status/2088132973606445208 | 1 | [r/chutesAI](https://www.reddit.com/r/chutesAI/comments/1vo6wrp/glm53_is_the_same_743b_base_as_52_reposttrained/) |
| https://github.com/KritBlade/MVU_Game_Maker/blob/main/dist/MVU_Deepseekv0.5%2Cjson.json | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1t1t65d/mvu_game_maker_on_deepseek_v4_pro_preset_solution/) |
| https://github.com/KritBlade/VectHarePlus | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1t1t65d/mvu_game_maker_on_deepseek_v4_pro_preset_solution/) |
| http://github.com/dadwritestech/LlamaForge | 1 | [r/SelfHostedAI](https://www.reddit.com/r/SelfHostedAI/comments/1uyagml/built_a_control_panel_for_llamacpp_now_drives/) |
| https://docs.sillytavern.app/usage/core-concepts/macros/ | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vcr9d8/preset_deus_ex_machina_v1_a_featurerich/) |
| http://chatgpt.com | 1 | [r/claudexplorers](https://www.reddit.com/r/claudexplorers/comments/1w0d2nh/building_a_permanent_home_for_ai_friends_what/) |
| https://github.com/tbosancheros39/opencode-thinking-fix | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1uco67e/if_you_pay_for_opencode_go_12_of_15_models_break/) |
| http://imgur.com/a/8QKvH | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://m.imgur.com/gallery/IHyPl | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/vP62K | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/jZgsR | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/wBNb8 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/BEOrj | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/XRAfu?gallery | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/gallery/ofSHs | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/gallery/veQcQ | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/sygy2 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/gzurn | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/Zygsg | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/1StJV#0 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/QHtcw | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://frontalspy.imgur.com/ | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/NMUvE | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/PFBbI#0 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://mega.nz/#F!scR3DBTQ!oZJiofaflaUcfhIarSHkXw | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/l2Wpf | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/opmvJ | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/6Phs7 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://mega.nz/?/#F!LwxSAYgI!1bAWmxO4dMq5WPd8pNOj9g | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/MzhDi | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://mega.nz/#F!m9xWDAAK!u48DmP3fi3DRo5sGGOc5UA | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://mega.nz/#F!PsQGHTha!GNETlcdEbGUOoYrmENg0Pw | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://mega.nz/#F!uoAXEaLK!4NsSrbP3xNfNEILH10X_AA | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/KFTuR | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/q5d9q | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/EaJVW | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/doW0O | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/EECoy | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/D6RtK | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/cl39U | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/70qzC | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/P1fXp | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/JIvlI | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/ilPO0 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/DsCmU | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/f7Wgy | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/r4Brd | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/Fv1A1 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/Bj4AU | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/iiYMv | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/8vcsN | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/VBEbf | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/zcaOM | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/Vt7p7 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/DwHHd | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/O0zZx | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/jghyU | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/7R8e4 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/1nPyW | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/2WhnW | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/3GRg1 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/sTtPF | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/gallery/lTOjG | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/rXs1K | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/YulaA | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/wvwQY | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/RaY9Z | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/2FxgQ | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/6xe5f | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/ObHQG | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/Ty3VX | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/IKi27 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/QEQzy | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/7ZvXt | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/rr95o | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/V8ey3 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/lxSc3 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/D0rV4 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/drBFx | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/WbogB | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/T9fou | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/6Swch | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/iaIpI | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/iVGg0 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/Y8Ket | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/qpAIo | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/klNv5 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/p50O0 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/kAJJB | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/ZqCIG | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/9bJVI | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/PS49L | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/6h7Te | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/jcaOU | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/Ji2mK | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/qJqdr | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/tQVoG | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/gph54 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/B40YU | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/xjZa1 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/bYFOf | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/SZbKu | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/bfm9x | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/wsui9 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/TgOGs | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/2k6yr | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/X62dw | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/Mm8Gh | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/NQF2q | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/p18tX | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/INvy3 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/RP80K | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/pHBa9 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/YexS2 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/L8laF | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/KU8QA | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/pavmr | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/hSrk8 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/hUwbn | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/gNIdX | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/F0zky | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/NVM6T | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/iEAMV | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/ndwlS | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/NrAfK | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/oeA76 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/ptgIk | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/jOF4X | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/afjIk | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/MeEDh | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/bWpV1 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/tbzH3 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/byRKr | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/h8yVX | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/aBxIf | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/QyWlE | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/byciO | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/YLT3Q | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/PzE2o | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/61hhE | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/Cakrp | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/SiD5T | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/fSMGy | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/SfKuO | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/F1x52 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/htn7y | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/3xU9E | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/eRh92 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/YFlL0 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/PcXM2 | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://imgur.com/a/Nbo0l | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| http://imgur.com/a/dNL0J | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://mega.nz/#F!99pSUBYB!apn435wtIPtXW3Mt_0kYVQ | 1 | [r/anime](https://www.reddit.com/r/anime/comments/6kfngy/anime_wallpapers_40000_images_100_anime_5000_nsfw/) |
| https://graymirror.substack.com/p/the-butterfly-revolution | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.nytimes.com/2025/01/18/magazine/curtis-yarvin-interview.html | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.washingtonpost.com/politics/2025/01/28/trump-emails-workforce/ | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://apnews.com/article/trump-firings-prosecutors-dei-federal-government-2042969d1855feb2753b6237f1022666 | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.thedailybeast.com/elon-musks-doge-lackeys-seize-control-of-social-security-check-system/ | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://apnews.com/article/trump-loyalty-white-house-maga-vetting-jobs-768fa5cbcf175652655c86203222f47c | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://edition.cnn.com/2025/01/23/politics/birthright-citizenship-lawsuit-hearing-seattle/index.html | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.politico.com/news/2025/01/28/chaos-confusion-trump-order-freeze-federal-dollars-00201079 | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://abcnews.go.com/Politics/trump-funding-freeze-blatant-violation-constitution-federal-law/story?id=118183957 | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://democrats-appropriations.house.gov/news/fact-sheets/background-unlawful-impoundment-president-trumps-executive-orders | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.npr.org/2025/01/31/nx-s1-5282410/trump-spending-freeze-blocked-federal-judge | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.nbcnews.com/tech/tech-news/government-websites-vanish-trump-constitution-dei-rcna188522 | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.washingtonpost.com/politics/2025/02/02/trump-congress-republicans-cabinet-picks/ | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.yahoo.com/news/white-house-warns-consequences-republicans-140040467.html | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.nbcnews.com/think/opinion/trump-barr-used-loophole-deploy-national-guard-u-s-cities-ncna1236034 | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://en.wikipedia.org/wiki/List_of_national_emergencies_in_the_United_States | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.aclu.org/press-releases/supreme-court-grants-trump-broad-immunity-for-official-acts-placing-presidents-above-the-law | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.nbcnews.com/tech/social-media/elon-musk-turned-x-trump-echo-chamber-rcna174321 | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://deadline.com/2025/01/mark-zuckerberg-meta-trump-white-house-ai-deepseek-tiktok-1236272351/ | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://thehill.com/policy/technology/5117962-elizabeth-warren-meta-settlement-bribe/ | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.cnbc.com/2025/01/19/trump-says-he-will-revive-tiktok-but-wants-50percent-us-ownership.html | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://edition.cnn.com/2021/08/30/politics/trump-legacy-fake-news/index.html | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.npr.org/2024/10/22/nx-s1-5161480/trump-media-threats-abc-cbs-60-minutes-journalists | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.theguardian.com/us-news/2024/dec/28/trump-npr-pbs-funding-cut | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.youtube.com/watch?v=0FR65Cifnhw | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.cnbc.com/2025/01/30/trump-funding-freeze-is-existential-threat-morehouse-college-president.html | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.wsj.com/us-news/education/trump-dei-ban-federal-funding-higher-education-8ae81c40 | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.statnews.com/2025/01/30/trump-executive-orders-pressure-universities-to-end-dei-programs/ | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://apnews.com/article/donald-trump-enemies-from-within-5c4a34776469a55e71d3ba4d4e68cf62 | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://en.wikipedia.org/wiki/Sturmabteilung | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.latimes.com/world-nation/story/2024-07-03/pro-trump-project-2025-leader-suggests-a-new-american-revolution-is-underway | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.reuters.com/world/us/trump-tells-christians-they-wont-have-vote-after-this-election-2024-07-27/ | 1 | [r/economicCollapse](https://www.reddit.com/r/economicCollapse/comments/1ig07py/the_plans_to_destroy_america_and_turn_it_into_a/) |
| https://www.youtube.com/watch?v=uyZGy3nR\_v4&amp;t=12s | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1v2bnsd/new_deepseek_model_v4_leak_could_change_open/) |
| https://www.youtube.com/watch?v=uyZGy3nR_v4&amp;t=12s | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1v2bnsd/new_deepseek_model_v4_leak_could_change_open/) |
| https://github.com/ggml-org/llama.cpp/pull/25655 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ven4f7/speculative_decoding_with_deepseek_v4_flash_0731/) |
| https://debuginfod.ubuntu.com&gt | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ven4f7/speculative_decoding_with_deepseek_v4_flash_0731/) |
| https://substackcdn.com/image/fetch/$s_!eXhW | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://DjamgaMind.com/Toolkit | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr0F3qgz0W7lCdLW6lZ3kXW37CtfL8hPTqxW7_8fwp4vg5GSW3n1Y4J6V | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr0F3qgz0W7lCdLW6lZ3n-W6xYXLP3fBFrwW3jf0cD3Jz-TBW5LYR4d8b | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr0l3qgz0W6N1vHY6lZ3pPW6w973p3ql043W7lzsLN6CFxz1W4LDqBk6d | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvq_M5nR3bW5BWr2F6lZ3pmW4-LKQx8qDJXpW7Wb4VD1LtVsdW4pTHX_8Z | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr0Y3qgz0W7Y8-PT6lZ3p6W8hZXnD7bW1BbW7rLs1C6WzLJ-W6gT5q86x | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr0l3qgz0W6N1vHY6lZ3nTW5CqN-t6KMm-8W93FR1T5Cl3KvW98r0bx5- | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr0F3qgz0W7lCdLW6lZ3mBW3bPGSx3RKzxLW8TgLS96qHdnlW6JMqNt1J | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr0Y3qgz0W7Y8-PT6lZ3nPVJGdpb8lx5qsN3pYYlBtBz4dW7QbRmh57gs | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr023qgz0W69sMD-6lZ3m_W1fp4XM1pKmjHW7N_GZ-6hLvc5W5x2TZv3L | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://substackcdn.com/image/fetch/$s_!rwN1 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr0l3qgz0W6N1vHY6lZ3pPVQgjhQ4CSJfGW1Rrwg75c6CfRW7cXD6c2PK | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr1d3qgz0W8wLKSR6lZ3pqW9lMKh56NSGl1W8jrhbf94K2DKW5tXkt578 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr025nR3bW69t95C6lZ3p7N6pl4bv7_rDFVTWb5M47KBc_W1k02L58krq | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr0Y3qgz0W7Y8-PT6lZ3mzW6MRDkv23fj9CW5J0bYk5YZ619W9l465C84 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvq_s5nR3bW50kH_H6lZ3kQW7gfQ3K1-4Zk7VYBYtv8K928sW17Vrj04Kg | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr025nR3bW69t95C6lZ3lSW8vfqpC7X1jDLW26Ry_S9ck1vQW6vdfnq3f | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VVvrkP89QcLXW5hz0Ys5Cg3YzW197v5Z5Ny3lvN7vvr0Y3qgz0W7Y8-PT6lZ3ldW21TG5X1dCbfHN8YdLQWB-zb8W5nKqhl6c5 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://link.mail.beehiiv.com/v1/c/rG8i0h1%2Fj9A5CiqW2Mroqaan6s9OOGOL9hLb%2BOBGfLmd5AjrHxt2khqsPP0h%0AiffVqXdjna%2FwUSXTS27SSaU9cezIsSZO5SOg34mWVNSwru | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://link.mail.beehiiv.com/v1/c/GhbOHYLDWwUhTrHHSEW%2FXgE7yIaXsTFR3mY00QQxpGdbc3idVQGlolkgwj4l%0ASuuuUZn7HWFenug0I4gDq8uDAiO3UgqjLicCCEN12PeCINHWXl | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://link.mail.beehiiv.com/v1/c/xUBT0X%2B3twNo7bqKU7xZgbqhlJymiC0EPRMSOKh5H7MiEBr49e3wkE6QVyh2%0Ag%2FQQfm3cJRD4f%2BUTsqen3mkTg2OYS3j%2FcYPpskFZJ8eM | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://link.mail.beehiiv.com/v1/c/gH0LOavRxLrfMQZFXmEKhsGW8S%2BvOl%2B%2FawD1MMPzSvnuCVXoRy9F6QKOOBrJ%0APwtnVVpdGfvRSTaDESrv9yxMOKhXMRNHOHKTTc6YHkA8AN | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf08MjguofPcw5b1fa54PbEbnIs05fLBTHLR1YLQbh_LVf5OKU6pPkaVvQtkwEKFoCYRmbljpYCDgMHRrKN6oh_zP12 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf_MnrMNPlyZa0tC_fQ34TxQ78dU03jIigb7dPAeatjyNV2ljq48Z5cNvnS68WQ2YHV3c97BxhXxV_SUgWQRUAtTVWY | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf022yDnKIUiG8l1A8gWu3xsEj597tU59-HJrlXh7Wg51mEwoImcudOyAErZmGCZ-wxk0qCXCum8kXTVLaolTXezRnU | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf9JFvua7JJ7w4275sIFLhF5Mj9rwZsBFRVDYKfJzBpWQtygTZIJhRiakGVQ2aBMZfcA6Sb8zvnlirIJtIYczTeuPqK | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://link.mail.beehiiv.com/ss/c/u001.6k0_SAz8nrOuu_-LoNX1HTmnlyMN_7H80MQnUWOOM_gFjKXgjWjG4CGREKvhbYDYGAVC5dj-oDglVe_Dnuk4jtjSmUZSfLLODI5jkfUmTE7WmM | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://link.mail.beehiiv.com/ss/c/u001.6k0_SAz8nrOuu_-LoNX1HY9oNCBbdPwm9vPFSTCcagW7J-75Njxmiou_yQE5x7t7TPkzx4HBg1GfPWsMLGnJYb9Rj_b3Eg878gI8bE5UtY1QKB | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://substackcdn.com/image/fetch/$s_!Fz5K | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://link.mail.beehiiv.com/ss/c/u001.u02qJFHqR61XIkDbYtOHoFD8KXkWiT4sOx6rTzsMj_ZNjH17ovDisKWMOdshca3ZCejndM2bILAPihvL8JJO6NgyawJ0ITs5ZpqTSI691xiJSa | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://substackcdn.com/image/fetch/$s_!qAtx | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://link.mail.beehiiv.com/ss/c/u001.eCbm_1zon7G0lMoXTECWa-IUY9yqSc2cx0km5OJXo-NWGv59ZfP33gshrSVnlfMiaHKMMsmgoHBcNpmP6xnX3S-ROvSXFVFC5FK57jxqQs6JtC | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf937MUSrYzK6JzB2n81ON3wTz8UxD8RlN14R5Ifc4Waq0VlXcU1-tIMypqM7EyMZzcGZx7YewDjEYMoPcEL_FxtVYd | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1t17w09/ai_daily_news_rundown_the_gpt55_paradox_climate/) |
| https://www.anthropic.com/news/investigating-incidents-cybersecurity-evals | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://x.com/cremieuxrecueil/status/2082996871031652716 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://x.com/natolambert/status/2082913213092655336 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://thinkingmachines.ai/news/inkling-small/ | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://x.com/arcprize/status/2082925303601459347 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://x.com/cline/status/2082544250148057240 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://arxiv.org/abs/2607.26246 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://research.google/blog/science-one-framework-a-verifiable-autonomous-research-framework-via-chain-of-evidence/ | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.wired.com/story/chrome-needs-twice-a-week-patching-thanks-to-ai-bug-hunting-for-now/ | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.oracle.com/news/announcement/oracle-to-make-gemini-models-available-2026-07-30/ | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.cnbc.com/2026/07/30/ibm-ceo-quantum-computing-measurable-impact-earnings-2028-2029.html | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.cnbc.com/2026/07/30/tim-cook-sees-apples-hybrid-ai-strategy-as-a-competitive-weapon-.html | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.nist.gov/news-events/news/2026/07/department-commerce-announces-letters-intent-7-companies-874-million | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.cnbc.com/2026/07/30/nexus-data-centers-in-advanced-talks-to-secure-15b-for-google-backed-anthropic-data-center.html | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.reuters.com/business/retail-consumer/amazon-beats-estimates-quarterly-cloud-revenue-growth-2026-07-30/ | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.bloomberg.com/news/articles/2026-07-30/microsoft-eyes-history-with-490-billion-pop-in-market-value | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.livescience.com/technology/engineering/new-drone-can-be-charged-mid-flight-using-high-powered-lasers | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://x.com/tesla/status/2082707648148099363 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.nhtsa.gov/press-releases/cutting-red-tape-safely-fast-track-automated-vehicle | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.fastcompany.com/91581812/job-candidates-sneaking-prompt-injections-into-their-applications-resume-ai-screening | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.whitehouse.gov/releases/2026/07/crime-plummets-another-historic-low-under-president-trump/ | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.politico.com/news/2026/07/30/anthropic-supply-chain-risk-lawsuit-hearing | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.cnn.com/2026/07/30/us/flock-camera-vandalism-protests-cec | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.wsj.com/business/autos/tesla-weighs-sale-of-china-business-to-pave-way-for-potential-spacex-merger-5ae26026 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://www.nytimes.com/2026/07/30/us/ai-twin-pastor-justin-lester-california-church.html | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vbrjy7/welcome_to_july_31_2026_dr_alex_wissnergross/) |
| https://marketplace.visualstudio.com/items?itemName=Vizards.deepseek-v4-for-copilot | 1 | [r/GithubCopilot](https://www.reddit.com/r/GithubCopilot/comments/1tzx9ke/deepseek_v4_for_github_copilot_setup_guide/) |
| https://platform.deepseek.com/api_keys | 1 | [r/GithubCopilot](https://www.reddit.com/r/GithubCopilot/comments/1tzx9ke/deepseek_v4_for_github_copilot_setup_guide/) |
| https://rolecallstudios.com/landing | 1 | [r/JanitorAI_Refuges](https://www.reddit.com/r/JanitorAI_Refuges/comments/1tdi5g8/presenting_rolecall_studios_trailblazing_features/) |
| https://plotlightstudios.com | 1 | [r/JanitorAI_Refuges](https://www.reddit.com/r/JanitorAI_Refuges/comments/1tdi5g8/presenting_rolecall_studios_trailblazing_features/) |
| https://plotlightstudios.com/discovery/characters/@testuser/panorama | 1 | [r/JanitorAI_Refuges](https://www.reddit.com/r/JanitorAI_Refuges/comments/1tdi5g8/presenting_rolecall_studios_trailblazing_features/) |
| https://plotlightstudios.com/discovery/characters/@bleachbunny/ambriel | 1 | [r/JanitorAI_Refuges](https://www.reddit.com/r/JanitorAI_Refuges/comments/1tdi5g8/presenting_rolecall_studios_trailblazing_features/) |
| https://plotlightstudios.com/discovery/characters/@dollydistress/be-vaudeville-dahlias-omega-kouhai-sama | 1 | [r/JanitorAI_Refuges](https://www.reddit.com/r/JanitorAI_Refuges/comments/1tdi5g8/presenting_rolecall_studios_trailblazing_features/) |
| https://rolecallstudios.com/discovery/personas/50baf3fc-3b27-40d4-ac48-2ac78ca456c1 | 1 | [r/JanitorAI_Refuges](https://www.reddit.com/r/JanitorAI_Refuges/comments/1tdi5g8/presenting_rolecall_studios_trailblazing_features/) |
| https://rolecallstudios.com/discovery/lorebooks/@broeckchen/alyon-330?types=lorebook&amp;sort=newest&amp;nsfw=1 | 1 | [r/JanitorAI_Refuges](https://www.reddit.com/r/JanitorAI_Refuges/comments/1tdi5g8/presenting_rolecall_studios_trailblazing_features/) |
| https://rolecallstudios.com/sign-up?invite=DxLkXS2a9ZeLhNzGQHNEXjrx4AuMlwiS | 1 | [r/JanitorAI_Refuges](https://www.reddit.com/r/JanitorAI_Refuges/comments/1tdi5g8/presenting_rolecall_studios_trailblazing_features/) |
| https://rolecallstudios.com/coming-soon | 1 | [r/JanitorAI_Refuges](https://www.reddit.com/r/JanitorAI_Refuges/comments/1tdi5g8/presenting_rolecall_studios_trailblazing_features/) |
| https://plotlightstudios.com/plotpoints/leaderboard | 1 | [r/JanitorAI_Refuges](https://www.reddit.com/r/JanitorAI_Refuges/comments/1tdi5g8/presenting_rolecall_studios_trailblazing_features/) |
| https://discord.gg/xwGAexc9CT | 1 | [r/JanitorAI_Refuges](https://www.reddit.com/r/JanitorAI_Refuges/comments/1tdi5g8/presenting_rolecall_studios_trailblazing_features/) |
| https://www.aimadetools.com/blog/race-deepseek-upgrade-v4-pro/ | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1subqy5/were_running_a_race_where_7_ai_agents_build/) |
| https://www.aimadetools.com/race/ | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1subqy5/were_running_a_race_where_7_ai_agents_build/) |
| https://github.com/Liquid4All/liquid-audio | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/nineninesix/kani-tts-370m | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://www.ibm.com/new/announcements/ibm-granite-4-0-hyper-efficient-high-performance-hybrid-models | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/neuphonic/neutts-air | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://simular.ai/articles/agent-s3 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/inclusionAI/Ming-UniVision-16B-A3B | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/character-ai/Ovi | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/Salesforce/CoDA-v0-Instruct | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/Qwen/Qwen3-VL-30B-A3B-Instruct | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/DecartAI/Decart-XR | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/LiquidAI/LFM2-8B-A1B | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/Tencent-Hunyuan/HunyuanVision | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/bageldotcom/paris | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/cumulo-autumn/StreamDiffusion | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/ai21labs/Jamba-v0.1 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/inclusionAI/Ring-1T | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/TingtingLiao/mimix | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/microsoft/UserLM-8b | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/RadicalNumerics/RND1 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/Kwaipilot/KAT-Dev-72B-Exp | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://pbihao.github.io/projects/DreamOmni2/ | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/mit-han-lab/streaming-vlm | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/QwenLM/Qwen3-VL | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/PaddlePaddle/PaddleOCR-VL | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/facebook/MobileLLM-Pro | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/Tencent-Hunyuan/HunyuanWorld-1.0 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/inclusionAI/LLaDA2.0-flash-preview | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/deepseek-ai/DeepSeek-OCR | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/krea-ai/realtime-video | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/Qwen/Qwen3-VL-32B-Instruct | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://arxiv.org/abs/2510.14876 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/LiquidAI/LFM2-VL-3B | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/tencent/HunyuanWorld-1 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/PokeeAI/pokee_research_7b | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/allenai/olmOCR-2-7B-1025 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://ltx.video/ | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/lightonai/LightOnOCR-1B-1025 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://holo-cine.github.io/ | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/tahoebio/tahoe-x1 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/PRIME-RL/P1-30B-A3B | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/meituan-longcat/LongCat-Video | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://arxiv.org/html/2510.19944v1 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://www.minimax.io/news/minimax-m2 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/inclusionAI/Ming-flash-omni-Preview | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/inclusionAI/LLaDA2.0-mini-preview | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/LiquidAI/LFM2-ColBERT-350M | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/ibm-granite/granite-4.0-350m | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/HKUDS/ViMax | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://build.nvidia.com/nvidia/nemotron-nano-12b-v2-vl/modelcard | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://openai.com/index/introducing-gpt-oss-safeguard/ | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/morphicfilms/frames-to-video | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/Bria-AI/FIBO | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/ByteDance/Ouro-2.6B-Thinking | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/baaivision/Emu3.5 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://huggingface.co/moonshotai/Kimi-Linear-48B-A3B-Instruct | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://www.modelscope.cn/studios/BlinkDL/RWKV-CHN-2/summary | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://github.com/alibaba/UI-Ins | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1olxijp/list_of_interesting_opensource_models_released/) |
| https://www.mediafire.com/file/0lu18dtlzssivdq/Freaky+Frankenstein+4+MAX++Updated.json/file | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1t68afk/the_directors_cut_rerelease_freaky_frankenstein_4/) |
| https://www.mediafire.com/file/7rru0h961av6h26/Freaky_Frankenstein_4_BOLT%252B_Updated.json/file | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1t68afk/the_directors_cut_rerelease_freaky_frankenstein_4/) |
| https://www.mediafire.com/file/nymiye9tdjwl7zd/tavo1_Hide_Plot_Summary.json/file | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1t68afk/the_directors_cut_rerelease_freaky_frankenstein_4/) |
| https://x.com/arena/status/2077824029126504525 | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uyr7k7/just_tested_kimi_k3_with_hermes_lord/) |
| https://go.lightnode.com/hermes-agent-vps | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1uyr7k7/just_tested_kimi_k3_with_hermes_lord/) |
| http://venice.ai | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://venice.ai/blog/introducing-the-venice-token-vvv | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://www.coinbase.com/price/venice-token | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://coinmarketcap.com/currencies/venice-token/#Holders | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://docs.venice.ai | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-february-4th-2025 | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-february-13th-2025 | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://venice.ai/blog/create-custom-ai-generated-stickers-a-complete-guide-to-venices-new-sticker-factory | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://docs.venice.ai/overview/guides/generating-api-key-agent | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-march-10-13-2025 | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-february-22-2025 | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://venice.ai/blog/venice-is-burning | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://news.bitcoin.com/venice-burns-one-third-of-total-token-supply/ | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-april-22nd-27th-2025 | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://venice.ai/blog/venice-new-model-paradigm | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-may-6th-may-12th-2025 | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-may-13th-may-19th-2025 | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-may-20th-26th-2025 | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-may-27th-june-1st-2025 | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog?utm_source=chatgpt.com | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://venice.ai/blog/7-days-to-diem | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://venice.ai/blog/introducing-diem-as-tokenized-intelligence-the-next-evolution-of-vvv | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://docs.venice.ai/overview/deprecations | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/p/add-text-to-video-support?_gl=1*g0doq2*_gcl_au*MTc3OTcxNTkyMS4xNzYwMDMwMTU0 | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-september-16th-october-20th-2025#:~:text=Venice%20Video | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-september-16th-october-20th-2025#:~:text=API | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://discord.gg/askvenice | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://venice.ai/blog/venice-development-update-october-2025 | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://featurebase.venice.ai/changelog/veniceai-change-log-october-21st-november-3rd#:~:text=Web%20Scraping%20is%20Live%20in | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| https://blog.venice.ai | 1 | [r/VeniceAI](https://www.reddit.com/r/VeniceAI/comments/1p3fyd1/veniceai_year_in_review_2025/) |
| http://ArtificialAnalysis.ai | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1tvjjor/choosing_the_best_llm_for_hermes_agent/) |
| https://likesumiink.substack.com/p/building-engines-and-making-hairballs | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1uxp072/discussing_prompting_techniques_july/) |
| https://huggingface.co/nohurry/sillytavern/blob/main/Presets/Voyage-Gemma4-v3.0.json#L164 | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1uxp072/discussing_prompting_techniques_july/) |
| https://huggingface.co/nohurry/sillytavern/blob/main/Presets/Voyage-Gemma4-v3.0.json#L178 | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1uxp072/discussing_prompting_techniques_july/) |
| https://huggingface.co/nohurry/sillytavern/blob/main/Presets/Voyage-Gemma4-v3.0.json#L206 | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1uxp072/discussing_prompting_techniques_july/) |
| https://huggingface.co/nohurry/sillytavern/blob/main/Presets/Voyage-Gemma4-v3.0.json#L248 | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1uxp072/discussing_prompting_techniques_july/) |
| https://huggingface.co/nohurry/sillytavern/blob/main/Presets/Voyage-Gemma4-v3.0.json#L122 | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1uxp072/discussing_prompting_techniques_july/) |
| https://huggingface.co/nohurry/sillytavern/blob/main/Presets/Voyage-Gemma4-v3.0.json#L32 | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1uxp072/discussing_prompting_techniques_july/) |
| https://www.dwsrd.org/ | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1uxp072/discussing_prompting_techniques_july/) |
| https://www.youtube.com/watch?v=ll\_Gchns9e8&amp;t=18s | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vsaz8o/agent_operating_system_makes_ai_agents_work/) |
| https://www.youtube.com/watch?v=ll_Gchns9e8&amp;t=18s | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vsaz8o/agent_operating_system_makes_ai_agents_work/) |
| https://github.com/elishacloud/Silent-Hill-2-Enhancements/issues/505 | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://Twitch.tv/GlitchyReal | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.patreon.com/themidnightsnow | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.win-rar.com/download.html?&amp;L=0 | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.7-zip.org/download.html | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://knowledge.autodesk.com/support/autocad/learn-explore/caas/sfdcarticles/sfdcarticles/How-to-enable-hidden-file-extensions-in-Windows.html | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://store.steampowered.com/about/ | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.howtogeek.com/179370/how-to-add-non-steam-games-to-steam-and-apply-custom-icons/ | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.duckstation.org/windl | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://aka.ms/vs/17/release/vc_redist.x64.exe | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://github.com/gingerbeardman/PSX?tab=readme-ov-file | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://silenthill.fandom.com/wiki/Grey_Child | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://silenthill.fandom.com/wiki/Mumbler | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.speedrun.com/sh1/guide/4eamg | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.duckstation.org/cue-maker/ | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.romhacking.net/translations/5862/ | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.romhacking.net/utilities/1040/ | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://mgba.io/downloads.html | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://github.com/mgba-emu/mgba/releases/download/0.10.4/mGBA-0.10.4-win64.7z | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.myabandonware.com/game/silent-hill-2-restless-dreams-bgd | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://enhanced.townofsilenthill.com/SH2/install.htm | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.myabandonware.com/game/silent-hill-3-bge | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://archive.org/download/silent-hill-3v-1.0-no-dvdfixedexe-eng/SilentHill3v1.0NoDVDFixedexeEng.rar | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://community.pcgamingwiki.com/files/file/1331-silent-hill-3-pc-fix-by-steam006/page/2/?tab=comments | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://community.pcgamingwiki.com/files/file/2034-xinput-plus-v415064/ | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://drive.google.com/drive/folders/1flmwoEBfXcPvLVv6VmxqWr_sU9foIFei?usp=sharing | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.silenthillmemories.net/sh3/versions/silent_hill_3_ps2_us_manual.pdf | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://github.com/Reloaded-Project/Reloaded-II/releases | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://dotnet.microsoft.com/en-us/download | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170#visual-studio-2015-2017-2019-and-2022 | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.moddb.com/mods/silent-hill-3-audio-enhancement-pack/downloads | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.gog.com/en/game/silent_hill_4_the_room | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://github.com/ThirteenAG/Ultimate-ASI-Loader/releases/download/v4.68/Ultimate-ASI-Loader.zip | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://github.com/HunterStanton/SilentHill4Randomizer/releases | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://github.com/samuelgr/Xidi/releases | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://github.com/samuelgr/XidiGameConfigurations/raw/refs/heads/master/GameConfigurations/Silent%20Hill%204%20-%20The%20Room/Xidi.ini | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://drive.google.com/file/d/1R7dvgYOm2HhNECDeEP8PA6A3xwIDWY5a/view?usp=drive_link | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.digola.com/lockcursor.html | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://pcsx2.net/downloads/ | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://drive.google.com/file/d/1UYON4sIPu9WVHp_wRUFB0568pUYYJhoY/view?usp=sharing | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| http://ps2-bios.zip | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.mediafire.com/file/vcfv07enna4d9hb/A8D83239.zip/file | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://youtu.be/Zbvnf_GfLK8 | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.mediafire.com/file/ml09hxpiw1nsow1/Sh.O.hd.xXthe.RockoXx.rar/file | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://archive.org/details/SilentHillTheEscape | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://store.steampowered.com/app/19000/Silent_Hill_Homecoming/ | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://unknownproject.github.io/silent_hill.html | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://github.com/unknownproject/Silent_Hill_Homecoming/releases/download/v2.50_3.0D/Patch2.5.exe | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://discord.gg/Vyw8cVN | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://github.com/unknownproject/Silent_Hill_Homecoming/releases/download/v3.10_pt3/Patch3.10.exe | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://dolphin-emu.org/download/ | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.patreon.com/arturstudios | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.mediafire.com/file/64vmpecbawu0sll/P.T._Emulation_1.4.rar/file | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://ascension.com/ | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://store.steampowered.com/app/2124490/SILENT_HILL_2/ | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.gog.com/en/game/silent_hill_2 | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://www.nexusmods.com/silenthill2/mods/24 | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://store.steampowered.com/app/2947440/SILENT_HILL_f/ | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://reshade.me/ | 1 | [r/silenthill](https://www.reddit.com/r/silenthill/comments/y9j88e/the_defininitive_guide_to_the_besteasiest_way_to/) |
| https://api.pgsgrove.com | 1 | [r/ZaiGLM](https://www.reddit.com/r/ZaiGLM/comments/1vbu7f1/grove_api_for_massive_compute_on_coding_plans/) |
| https://api.pgsgrove.com/ | 1 | [r/ZaiGLM](https://www.reddit.com/r/ZaiGLM/comments/1vbu7f1/grove_api_for_massive_compute_on_coding_plans/) |
| http://api.pgsgrove.com | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vszf5z/a_coding_plan_with_usage_banking_for_qwen_38_kimi/) |
| https://qwen.ai/blog?id=qwen3.8 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://x.com/shuai_bai_/status/2084103213322784886 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://x.com/alibaba_qwen/status/2084100707423289643 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://x.com/kimmonismus/status/2084187108520972471 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://www.bloomberg.com/news/articles/2026-08-03/alibaba-drops-another-china-ai-model-with-breakthrough-performance | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://www.theinformation.com/briefings/alibaba-offers-new-flagship-model-lower-prices-kimi-k3 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://x.com/chrisgpt/status/2084103764315721942 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://x.com/haider1/status/2084219101308993568 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://www.reuters.com/business/retail-consumer/deepseeks-new-ai-model-is-by-far-cheapest-well-known-models-run-research-firm-2026-08-03/ | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://mattbeton.com/blog/bitnet-6502.html | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://x.com/karpathy/status/2083749667410727319 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://x.com/Bayesian0_0/status/2083722413238341750 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1714 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://www.wired.com/story/openai-anthropic-ai-hacking-sprees-illegal/ | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://www.washingtonpost.com/technology/2026/08/02/how-police-officers-used-vast-network-cameras-spy-their-exes/ | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://www.nytimes.com/2026/08/02/business/smart-baby-monitors-nanit-owlet.html | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://www.msn.com/en-us/money/other/hollywood-fights-ai-in-public-while-quietly-building-it-into-movies/ar-AA28IhCH | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://www.theinformation.com/articles/robinhood-now-makes-revenue-predictions-stock-trades | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://www.ft.com/content/67db9b64-ec26-442e-8356-6c4411eba66e | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://www.theinformation.com/newsletters/ai-infrastructure/exclusive-data-center-costs-set-rise-u-s-states-move-repeal-tax-breaks | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://www.ft.com/content/6a987490-f3f8-45f7-8b1c-fd09d9fa874d | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://interestingengineering.com/energy/china-makes-major-nuclear-expansion-move | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://interestingengineering.com/innovation/us-largest-ethanol-carbon-capture-deal | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://interestingengineering.com/ai-robotics/china-grabs-top-humanoid-robot-spots | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://news.northwestern.edu/stories/2026/07/new-spinning-drone-hides-in-plain-sight | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://www.weizmann-usa.org/news-media/news-releases/viagra-may-reduce-cancer-metastasis-study-shows/ | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1ven6k2/welcome_to_august_3_2026_dr_alex_wissnergross/) |
| https://github.com/xiaobright/dsh-anchored-standard | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1votndx/down_the_rabbit_hole_of_deepseekv4pro0813/) |
| https://github.com/xiaobright/modeltest | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1votndx/down_the_rabbit_hole_of_deepseekv4pro0813/) |
| https://www.perplexity.ai/discover/tech/deepseek-makes-v4-pro-s-75-api-GozUhhnOSYONjGuNQ\_AmkA | 1 | [r/ArtificialInteligence](https://www.reddit.com/r/ArtificialInteligence/comments/1tlgw8d/deepseek_just_confirmed_that_their_75_promo/) |
| https://www.perplexity.ai/discover/tech/deepseek-makes-v4-pro-s-75-api-GozUhhnOSYONjGuNQ_AmkA | 1 | [r/ArtificialInteligence](https://www.reddit.com/r/ArtificialInteligence/comments/1tlgw8d/deepseek_just_confirmed_that_their_75_promo/) |
| https://github.com/criterium/opencode-lab/blob/main/prompt/shared/README.md | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1u1d3op/opencode_agent_prompts_for_deepseek_v4_a_critical/) |
| https://github.com/criterium/opencode-lab/blob/main/prompt/shared/README.es.md | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1u1d3op/opencode_agent_prompts_for_deepseek_v4_a_critical/) |
| https://github.com/criterium/opencode-lab/blob/main/prompt/shared/default.md | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1u1d3op/opencode_agent_prompts_for_deepseek_v4_a_critical/) |
| https://github.com/criterium/opencode-lab/blob/main/prompt/shared/default.es.md | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1u1d3op/opencode_agent_prompts_for_deepseek_v4_a_critical/) |
| https://opencode.ai/config.json | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1u1d3op/opencode_agent_prompts_for_deepseek_v4_a_critical/) |
| https://github.com/victorchen96/deepseek_v4_rolepaly_instruct | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1su8x8p/deepseek_v4_rp_guide_how_to_switch_between/) |
| https://github.com/victorchen96/deepseek_v4_rolepaly_instruct/blob/main/README_EN.md** | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1su8x8p/deepseek_v4_rp_guide_how_to_switch_between/) |
| https://www.youtube.com/watch?v=rBI-SH\_Z-ZA | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1t3m4jz/i_used_deepseek_v4_and_opencode_and_it_shocked_me/) |
| https://www.youtube.com/watch?v=rBI-SH_Z-ZA | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1t3m4jz/i_used_deepseek_v4_and_opencode_and_it_shocked_me/) |
| https://deepseekv4pro.com/guides/deepseek-v4-vs-claude | 1 | [r/GithubCopilot](https://www.reddit.com/r/GithubCopilot/comments/1twkr3w/staying_on_copilot_for_now_but_using_deepseek_as/) |
| https://drive.google.com/file/d/1SvM-8KAFtb8bmYXvLCTliEZJDzhYne5T/view?usp=sharing | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vz9wfu/introducing_realistic_frankenstein_20_thats_a/) |
| https://drive.google.com/file/d/1MlLsieZqHM-BbWhvAYKSpzGFrIZ1rG4E/view?usp=drivesdk | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vz9wfu/introducing_realistic_frankenstein_20_thats_a/) |
| https://unsloth.ai/docs/models/deepseek-v4#deepseek-v4-chat-template-improvements | 1 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1upxpc1/run_deepseekv4flash_locally/) |
| https://x.com/deepseek_ai/status/2057854261699195173 | 1 | [r/GithubCopilot](https://www.reddit.com/r/GithubCopilot/comments/1tkzjqx/deepseek_v4_pro_75_off_is_now_permanent/) |
| https://shortlyai.com | 1 | [r/SaaS](https://www.reddit.com/r/SaaS/comments/1w3jwre/i_made_an_allinone_ai_chatbot/) |
| http://dribly.pt | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1tzmkdb/i_am_14_and_i_used_deepseek_v4_reasonix_to_build/) |
| https://github.com/mefrraz/dribly | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1tzmkdb/i_am_14_and_i_used_deepseek_v4_reasonix_to_build/) |
| http://z.ai | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1t23shb/writers_block_314152_in_3dd_write_harder_a_prose/) |
| https://github.com/scrappylabsai/podr | 1 | [r/DeepSeekHarness](https://www.reddit.com/r/DeepSeekHarness/comments/1vtb6fk/podsh_a_terminal_client_for_dsh_attach_to_your/) |
| https://github.com/scrappylabsai/podr/blob/pod/README.zh-CN.md | 1 | [r/DeepSeekHarness](https://www.reddit.com/r/DeepSeekHarness/comments/1vtb6fk/podsh_a_terminal_client_for_dsh_attach_to_your/) |
| https://djamgamind.com/pitch** | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://djamgamind.com/pitch | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://melamoon.ca/top-10-finalists-vancouver/djamgamind | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhRDvbvgir512C7maGb7KLq18jlqjhbhe1DL6Ohwdq2lTTgCjRNc1dMAH5kWsoFfv8z_IxB46ixuQqGCYYP4Ex4VhALQE | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.i8ligEAMODugkGN-qAs51SbZzRJ8tGH9gL0xIzVsPuAh5xWuZY5r_jkH68cYfvzd8QrOyjJetywdMxBCNSCX3R_eF_vc9aLlIb3qNtyyedp0bGk9 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhbPLeHrhH3noKfVZIUrNiRFenNxOYL9_b4fpxPBtyvVzBKu-60Ou6A_hg8vH7LDHGRHDWFbzACh-ku4cEMNT9u3Gzlg8 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://link.mail.beehiiv.com/ss/c/u001.NN3LcSSNlElMIHwAnhfMXc8XutSv_b8AogBdd8eiHDPR_VHQuYHXVu5TyeGfi4pqXmp66fQInVYpl9giNZjfzJ_37hp0C35NMCu6GWn3EWtViO | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://link.mail.beehiiv.com/ss/c/u001.NN3LcSSNlElMIHwAnhfMXc8XutSv_b8AogBdd8eiHDPR_VHQuYHXVu5TyeGfi4pqXmp66fQInVYpl9giNZjfzJ_37hp0C35NMCu6GWn3EWtViO | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf937MUSrYzK6JzB2n81ON3xHIUutKTTPHxTTLwkeQqyi4ZJ0YRgyqH4XTIwFE0LJvelWd3UK_uFh7eWYMYNXfU5t_U | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf937MUSrYzK6JzB2n81ON3xHIUutKTTPHxTTLwkeQqyi4ZJ0YRgyqH4XTIwFE0LJvelWd3UK_uFh7eWYMYNXfU5t_U | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://link.mail.beehiiv.com/ss/c/u001.6k0_SAz8nrOuu_-LoNX1HVQGVU5C0nTeBMVkj1UP-J5C0Nchry7L1U2Cp6rFh85_DS4zo3dqx7cEEJv9qk2jsHvOkJNga7mzEBZHAZ1wuL7eEq | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://link.mail.beehiiv.com/ss/c/u001.siHJl2oxYc5G1hfeCOvt3YHQOwUORXeTORvfpAoau-7zWpi2nbCRcE9qQkopPDQqY78TWRw7hi1FQIN32D-Aag0l9kEHLay0Q5PjgadIbQ99-B | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| http://Alextownsend.net | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://link.mail.beehiiv.com/ss/c/u001.Q334NVcZU4O6L6VKRz8ijMJMbi-mRyjR0MM-5-oTw8CCy6-3ctCgJ1T55jNG6Bfz5aWzLUBdvo8xOUdrLqk-OfV0EoQoybqs674Uk3gbwkuzIA | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://link.mail.beehiiv.com/ss/c/u001.Q334NVcZU4O6L6VKRz8ijMJMbi-mRyjR0MM-5-oTw8CCy6-3ctCgJ1T55jNG6Bfz5aWzLUBdvo8xOUdrLqk-OfV0EoQoybqs674Uk3gbwkuzIA | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf8ExNMzG0bVXqeDlLKm2deyxbNYUSGAfAZw6hXWijKUeYfdTFz0NXM1SeioE1L3sVqVDCtznsfYym-KgF0-luVXlg7 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf8ExNMzG0bVXqeDlLKm2deyxbNYUSGAfAZw6hXWijKUeYfdTFz0NXM1SeioE1L3sVqVDCtznsfYym-KgF0-luVXlg7 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://link.mail.beehiiv.com/ss/c/u001.eCbm_1zon7G0lMoXTECWa-IUY9yqSc2cx0km5OJXo-P6clOLDGEy1ImC8Mrlr5StHOok_KB0rRr-e0Dws61S66dXJoEj-WxWG0AGtosw1qAD05 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://link.mail.beehiiv.com/ss/c/u001.eCbm_1zon7G0lMoXTECWa-IUY9yqSc2cx0km5OJXo-P6clOLDGEy1ImC8Mrlr5StHOok_KB0rRr-e0Dws61S66dXJoEj-WxWG0AGtosw1qAD05 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhfWNbSKFe8wJ5Va6mDMns965m5wpCUi-QvHt9enVgQIwDDlPv4jQu0QbMs1saY9wkBe7Qeot5PbFoo4AcYDgUd_CnaIa | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhffcYzC2-jU-pW11QdmCCJSoyFgEFIR51jiKSlDbhZWOSQQcQw6tXGwIg8HQa8_3Ehqfn-S7h7dqjwgyrsOVigFA7KqL | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.i8ligEAMODugkGN-qAs51ZqDrmpAs9lWOJC3jk4M3g4ROxJGxvyErtKFW-QYVu8BLdJf849hjrhycsfolSkUU7eryIXtZmoGxepIfldVI7bNn2jS | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhRSsqn9n9t-JFlNkNu_UfV1yPzEx1g0O6ozHveuDAXXCaljeQgOCNILHgMYeVP0MAVOMGh1VTOU3shD9VT4F83Z91Fnl | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.i8ligEAMODugkGN-qAs51SbZzRJ8tGH9gL0xIzVsPuDDVpx7wQUPuIbS18JzLfv0OkxKwoGcYu4KHrKjifv4YEbGYBGhiqiPw6TB5XFrpoQ9ROR_ | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.i8ligEAMODugkGN-qAs51U7LnZ46HWNWz0NtbIJBiLWmsOxINXAtuTUS5oaWaT0FBjCROrU-q59PJn3eYariNTq6h_uoBOazt9XXJyIjieCz-w85 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.i8ligEAMODugkGN-qAs51U7LnZ46HWNWz0NtbIJBiLVbnOj-PjKB7F83846SEs0UWcEI9mMPrnhuC62ze1uWAsw4VK75f7ZLYhkvX7ewhwrh_QPy | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.ATAItRJv4OHzc1muxCgos09cLEi_OnzlbgkonYtGXoGvlgqhY7Haw7PTfKc5IG_qp4tGVjfl839D-RKfkj5aepSuh8_C5i9Taa1Gfbpsx3yIdSL5 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.i8ligEAMODugkGN-qAs51SbZzRJ8tGH9gL0xIzVsPuAWK7c30UkOHn_hzemmcjDrFtoj1leBmZApRSL1hc8Pkyfjs--YC_IWMLrApqqhcY-iN986 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhQrqAzaBE9TY1HQ6YumqTzhSxK6ajUOufb0njG4IHbrVUZQWhKpmDaaKBFt_6PrjMelG1l_bH2_QAbXYndWuyu5DiSHt | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.i8ligEAMODugkGN-qAs51U7LnZ46HWNWz0NtbIJBiLVAq2G8UZqqo6sr5aL3eJ6MvoyljtTgbOclCIbC3dWZFQeQhjLO4X-sIEpj4UAidlHipLD2 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yha3nS6D6qvz7WW9LWUdy09RKq28bme2muHYT4CfPy7IGVkLnTh8U2kwfJuFRMoWiSaRv9YdFYsOgw0PNA-MqCdAOfKOG | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.i8ligEAMODugkGN-qAs51aqyrURrMGi6IEtZccGEEyYZL8KrqfMOAS_EMtsUh7e1DJhr32ISTLNWl91xyeXWbYQtqPYUmmNBilqQbPOacuNAWCQy | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhVJyp39lHwg2mvTDNLFNkwT_fXI6tATprmOv7ZqJZUGqkPRmvf3rZx4iWM2Cq865xLZSLX7N853JDPgf1b-dFeF_FVjz | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhQrqAzaBE9TY1HQ6YumqTzjrvPCQvPspnTPENqpdG0CQ75o1dxAaAQqdZf0LASJH2_kLHcKB0r0xRekE6UtKiDayTnDX | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhQaef6i08JVqfevH1xwmey7GkhiHtW5heRceDoVabpeta9HUgAHUGwBUDCX5xwRnHjIXFM6sMRoteg-F77bT_0s2Acjh | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.U1-fCwI5IV4zIAFqTdEm7eysdWsvDUDqemqHLESDBdWvjXOvu4-2s4kxOdAzzzIE8R8S8Va3vKZ1VkNmjL5I0kbVTIp0nI44tZoOxivatwUzud5n | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhbR5DI6DyCtEoGAVbcDS_qgnifgpq3_RM9k_ewpod17AuEo8PwoRYd-6gdO-7klwJFVy4x-H9PKnZOrj56AZ9X8qs1go | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.i8ligEAMODugkGN-qAs51U7LnZ46HWNWz0NtbIJBiLVQy6RySaM_JSkuA5fxngEPDJJ6KDDxmmOfTCFzQjcWuKUIGLAmQ5F23Y29nz6mx1e6HxI1 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.i8ligEAMODugkGN-qAs51YDHkzdwcrunz_B_Z-Oaq_5rSDrkzXDl8XjxIJ1vl33Cm44zzZzIwX8SZTseouxoAVUfR-njuhjaVuKAW4x8lPAwy73t | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.Sll-WiRclj5nwkRHzETs8Hej_1o8aG0T0RMqSTn20ii6BDb4Il9ppwGifXgirlp4WHjswYyCL_qbxjiJZpwNykYcxnjDDXUNw8v9ZBiaUUaAhgHt | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhZBwGUdza749CPwkx8dH1CFCTP0pmkMRl4xIaIM3XgqeibIkUcIfTb9OHabI70IzeWNBtq9Z7PkIuwI5JtmPMDFqZus1 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhQ0WY-7JYj8rH9JQHbTqzuoIYN9Rw3kFZZGcB7GqRLgU_HZaT7x2Ls5xyumppxqb2WAYaslb5Ez4YkoK2R8rYUZ5fJpE | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.i8ligEAMODugkGN-qAs51aqyrURrMGi6IEtZccGEEybQ0LXYJJVgp_rkpUM9JFe24uA9KwToc6hdolNLB5g5eiiToFAIDGtfxe6YlHonvpt8tO5L | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhbPLeHrhH3noKfVZIUrNiRF4F5Gyqhj156KCQO7ZqlTbN-JuI34JFKTfVIi9nifV8w_v8PbJ0-C_CfpVuLJ57_Lbdi1t | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://elink640.dupple.com/ss/c/u001.QT9-cN0mZn-HYCKnMP3yhRSsqn9n9t-JFlNkNu_UfV1v88hiIEMUfdFj_DZKREvuBMrCQE1lZLFFujvy5b9-H0zTB8Yo8OIWiD_FAZG5Qt2SiNtg | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1vwqsnm/ai_weekly_news_rundown_nvidias_coding_agent_aces/) |
| https://github.com/petmal/MindTrial | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vzcclv/deepseek_v4_gets_34_faster_at_the_same_score_glm/) |
| http://www.petmal.net/shared/mindtrial/results/2026-08-26/mindtrial-eval-all-models-03-2026\_27.html | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vzcclv/deepseek_v4_gets_34_faster_at_the_same_score_glm/) |
| http://www.petmal.net/shared/mindtrial/results/2026-08-26/mindtrial-eval-all-models-03-2026_27.html | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vzcclv/deepseek_v4_gets_34_faster_at_the_same_score_glm/) |
| https://www.mediafire.com/file/okz25rrg98i8hdx/%25E2%2580%25BC%25EF%25B8%258F%25F0%259F%2592%25A5_LE_EMOTIONALISM%2521_Version_1.1.5%25F0%259F%2592%25 | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1v46vqe/le_emotionalism_version_115_emotionalbased_preset/) |
| https://x | 1 | [r/CommandCode](https://www.reddit.com/r/CommandCode/comments/1unkp7v/how_did_we_make_deepseek_outperform_opus_harness/) |
| http://openrouter.ai/settings/privacy | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1tchbkb/psa_if_you_are_using_deepseek_v4_pro_on/) |
| https://yomimaru.app/ | 1 | [r/SideProject](https://www.reddit.com/r/SideProject/comments/1tw94jy/switching_my_apps_ai_features_from_gemini_to/) |
| https://www.youtube.com/watch?v=c\_83Kasc2rE | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vpj8is/glm_53_release_is_surprisingly_good_at_coding_2026/) |
| https://www.youtube.com/watch?v=c_83Kasc2rE | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1vpj8is/glm_53_release_is_surprisingly_good_at_coding_2026/) |
| https://github.com/StudioPlatforms/AgentZet | 1 | [r/AgentZet](https://www.reddit.com/r/AgentZet/comments/1u10iz4/agentzet_v100_deepseek_v4_claude_opus_4748_model/) |
| https://www.mediafire.com/file/w8an09qmiyqts9h/FF5.2_Internal_States_MICRO_setup_%25281%2529.json/file | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vmc07f/preset_update_freaky_frankenstein_52_the_first/) |
| https://www.mediafire.com/file/rc4bw2ug193ynf8/FF5.2_Internal_States_MAX_setup_%25281%2529.json/file | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vmc07f/preset_update_freaky_frankenstein_52_the_first/) |
| https://www.mediafire.com/file/o5ssm9rm2y6nok1/FF5.2_Internal_States_Forced_Reasoning_hapuppy_-_Updated_%25281%2529.json/file | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vmc07f/preset_update_freaky_frankenstein_52_the_first/) |
| https://www.mediafire.com/file/678h1oo8mqn845x/FF5_Regex_Suite_2.4%25282%2529.json/file | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vmc07f/preset_update_freaky_frankenstein_52_the_first/) |
| https://www.youtube.com/watch?v=ait\_Na4JbUI&amp;t=61s | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1t2is69/deepseek_v4_and_claude_code_is_a_coding_setup/) |
| https://www.youtube.com/watch?v=ait_Na4JbUI&amp;t=61s | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1t2is69/deepseek_v4_and_claude_code_is_a_coding_setup/) |
| http://znapai.com | 1 | [r/ClaudeCode](https://www.reddit.com/r/ClaudeCode/comments/1vb1wto/is_anthropic_cooked/) |
| https://www.google.com/search?ibp=oshop&amp;prds=pvt:hg | 1 | [r/Ender_2_Pro](https://www.reddit.com/r/Ender_2_Pro/comments/1w3klpq/need_help_configuring_marlin_for_ender_2_pro/) |
| https://venturebeat.com/orchestration/deepseek-open-sources-dspark-a-new-framework-to-speed-up-llm-inference-by-up-to-85 | 1 | [r/BayAreaHomes](https://www.reddit.com/r/BayAreaHomes/comments/1uj6f49/deepseek_open_sources_dspark_a_new_framework_to/) |
| https://venturebeat.com/orchestration/deepseek-cut-prices-75-the-100x-problem-remains | 1 | [r/BayAreaHomes](https://www.reddit.com/r/BayAreaHomes/comments/1uupvwt/deepseek_cut_prices_75_the_100x_problem_remains/) |
| https://aipolcom.net | 1 | [r/dataisbeautiful](https://www.reddit.com/r/dataisbeautiful/comments/1vzyzkx/oc_50_ai_models_62_propositions_52700_answers/) |
| https://huggingface.co/bartowski/endless-frontier\_BigBang-v1-GGUF | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vk1p9s/endlessfrontierbigbangv1_qwen_35_finetunes/) |
| https://huggingface.co/bartowski/endless-frontier_BigBang-v1-GGUF | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vk1p9s/endlessfrontierbigbangv1_qwen_35_finetunes/) |
| https://cdn.discordapp.com/attachments/1500428225719963750/1530607029134299276/ChatGPT_Image_Jul_25_2026_07_05_19_PM.png?ex=6a697c21&amp;is=6a682aa1&a | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1v6dlp8/multihog_dd_framework_the_ultimate_rpg_extension/) |
| https://wonderrico.github.io/local\_llm\_benchmark/benchmark-main.html?filter=27b | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vr4bs4/local_agentic_coding_benchmark_qwen_38_27b_in/) |
| https://wonderrico.github.io/local_llm_benchmark/benchmark-main.html?filter=27b | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vr4bs4/local_agentic_coding_benchmark_qwen_38_27b_in/) |
| https://wonderrico.github.io/local\_llm\_benchmark/benchmark-detail.html?filter=27b | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vr4bs4/local_agentic_coding_benchmark_qwen_38_27b_in/) |
| https://wonderrico.github.io/local_llm_benchmark/benchmark-detail.html?filter=27b | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vr4bs4/local_agentic_coding_benchmark_qwen_38_27b_in/) |
| https://api.linknux.com/v1 | 1 | [r/SideProject](https://www.reddit.com/r/SideProject/comments/1w3yheu/i_built_one_openaicompatible_api_for_claude_gpt/) |
| http://Z.ai/GLM | 1 | [r/SideProject](https://www.reddit.com/r/SideProject/comments/1w3yheu/i_built_one_openaicompatible_api_for_claude_gpt/) |
| http://Abacus.AI | 1 | [r/abacusai](https://www.reddit.com/r/abacusai/comments/1vtki6o/chatllm_ai_models_and_their_best_use_cases/) |
| https://drive.google.com/file/d/1T-oE3sK2djG1vkjh2AhbnXfLySSroeMr/view?usp=sharing | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1w3m9bb/realistic_frankenstein_21_karma_is_absolute/) |
| https://drive.google.com/file/d/1DuXVxt5S0wkAnqigly0XwgoVrUy97h0l/view?usp=sharing | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1w3m9bb/realistic_frankenstein_21_karma_is_absolute/) |
| https://itzi.app/app/api | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1vvlx1n/looking_for_10_sillytavern_testers_700_free_ai/) |
| https://github.com/router-for-me/CLIProxyAPI | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v7d8px/harness_showdown_claude_code_vs_opencode_vs_pi/) |
| https://www.youtube.com/watch?v=Noo0NWD0gHU | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1v7d8px/harness_showdown_claude_code_vs_opencode_vs_pi/) |
| https://aifreeforever.com/chat/deepseek-v4-flash** | 1 | [r/freetoolsAI](https://www.reddit.com/r/freetoolsAI/comments/1tuwqad/free_deepseek_v4_ai_chatbot_unlimited/) |
| https://store.steampowered.com/app/368000 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1029210 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/504920 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/382260 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/229810 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/253230 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1232640 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/390890 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/423870 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/269670 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/851980 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1236490 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/238460 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/618740 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/49604 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/914750 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/335080 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1071870 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/751820 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/294810 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/302710 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/42640/ | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/965680 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/546390 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/274190 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/225080 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/564050 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1424350 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1128180 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/971690 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/466980 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/95300 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/204360 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/241410 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/737890 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/319450 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/256290 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1097130 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1066420 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/337960 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1482840 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/489720 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/209670 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/293780 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/540870 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1362400 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1061180 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/447700 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/268910 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/791470 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/252610 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1316800 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/415880 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/233610 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1422420 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/252350 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/678950 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1056690 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1536390 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/312530 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/383230 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/311690 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/203680 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1213750 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/233190 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/564230 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/508790 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1054430 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1285020 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1117670/ | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/396900 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/356790 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/285900 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/258970 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/469820 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/310790 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/223220 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/265930 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/571740 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/534550 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/275390 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/371510 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/418360 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/598550 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/239070 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/797410 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/905340 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/394510 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1000360 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/269210 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/303590 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/295670 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1012450 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/389140 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/801750 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/477160 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/257850 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/838110 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/95400 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/334190 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/432980 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/375750 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1426210 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/377950 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1278190 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/531510 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/431930 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/341800 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/592480 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1499220 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/684530 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/238280 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/553310 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/252110 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1266980 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/42910 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/281280 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1348680 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/312610 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/446850 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1535500 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1303990 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/113020 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/573300 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/307780 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/441010 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/296470 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/323850 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/996770 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/428750 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/295790 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/404540 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/535520 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/94400 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/471550 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/809870 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1304780 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/242680 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/298520 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/400080 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/448510 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/559870 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/850320 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1177030 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/506500 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/218740 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/572890/ | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/492340 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/332330 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/368180 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1479990 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/880940 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/362380 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1259790 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1065320 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/289760 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/242550 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/201570 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/517710 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/661940 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/99300 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/760810 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1252300 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/383980 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1049320 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/300380 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1404530 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/434460 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/252950 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/470210 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/215510 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1352340 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/464650 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1026130 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/467900 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1397790 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/239090 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/752170 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/301970 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/890310 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/6120 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/20820 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1096100 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/667600 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/91100 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/725480 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1012530 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/539400 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/212480 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/584400 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1275790 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/207140 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/629860 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/239350 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/297860 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/277850 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/394850 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1005400 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/389650 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/263020 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/674940/ | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/429330 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1133590 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/985890 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/520670 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/532190 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/673750 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1403350 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/877800 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1380150 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/416530 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1029760 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/250900 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/221810 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1190400 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/398710 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1303950 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/286000 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/337840 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/375900 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/437920 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/35720 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/319910 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/690640 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/386940 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/45760 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1016920 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1225570 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/780350 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1243960 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/837470 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/277390 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1175140 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/785790 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/702680 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/761010 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/275200 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/1211020 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/217200 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/327030 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://store.steampowered.com/app/674750 | 1 | [r/pcgaming](https://www.reddit.com/r/pcgaming/comments/pt8n14/list_of_250_awesome_2_player_windows_couch/) |
| https://kenbrakke.com/evolver/evolver.html | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1umcova/surface_evolver_bench_my_benchmark_asking_llms_to/) |
| http://hermes.md | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1tppbbn/deepseek_v4_flash_turns_hermes_into_an_agent_os/) |
| http://skill.md | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1tppbbn/deepseek_v4_flash_turns_hermes_into_an_agent_os/) |
| https://www.youtube.com/watch?v=9hJOx\_f-F5I | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1svx8aa/deepseek_v4_pro_turns_simple_prompts_into_real/) |
| https://www.youtube.com/watch?v=9hJOx_f-F5I | 1 | [r/AISEOInsider](https://www.reddit.com/r/AISEOInsider/comments/1svx8aa/deepseek_v4_pro_turns_simple_prompts_into_real/) |
| http://CLAUDE.MD | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1v55tgp/make_deepseek_v4_pro_act_like_an_anthropic_model/) |
| https://artificialanalysis.ai/models?models=gpt-5-6-luna-low%2Cgpt-5-6-luna-medium%2Cgpt-5-6-luna-high%2Cgpt-5-6-luna%2Cmimo-v2-5-0424%2Cmimo-v2-5-pro | 1 | [r/singularity](https://www.reddit.com/r/singularity/comments/1vvb47a/gemini_37_flash_is_currently_75_off_on_openrouter/) |
| https://openrouter.ai/google/gemini-3.7-flash | 1 | [r/singularity](https://www.reddit.com/r/singularity/comments/1vvb47a/gemini_37_flash_is_currently_75_off_on_openrouter/) |
| https://github.com/chrissotraidis/sunpad | 1 | [r/macgaming](https://www.reddit.com/r/macgaming/comments/1vkj8d8/super_mario_sunshine_now_runs_natively_on_apple/) |
| https://z.ai/subscribe | 1 | [r/vibecodingitalia](https://www.reddit.com/r/vibecodingitalia/comments/1vo6u37/glm53_stesso_base_di_52_posttraining_su_coding_e/) |
| https://www.latent.space/p/ainews-deepseek-v4-pro-16t-a49b-and | 1 | [r/u_petburiraja](https://www.reddit.com/r/u_petburiraja/comments/1swzrbl/deepseek_v4_pro_runs_on_chinese_chips_breaking_us/) |
| https://techcrunch.com/2026/04/27/meta-inks-deal-for-solar-power-at-night-beamed-from-space/ | 1 | [r/u_petburiraja](https://www.reddit.com/r/u_petburiraja/comments/1swzrbl/deepseek_v4_pro_runs_on_chinese_chips_breaking_us/) |
| https://techcrunch.com/2026/04/25/maines-governor-vetoes-data-center-moratorium/ | 1 | [r/u_petburiraja](https://www.reddit.com/r/u_petburiraja/comments/1swzrbl/deepseek_v4_pro_runs_on_chinese_chips_breaking_us/) |
| https://fortune.com/2026/04/26/john-ternus-tim-cook-apple-china-iphone-ai/ | 1 | [r/u_petburiraja](https://www.reddit.com/r/u_petburiraja/comments/1swzrbl/deepseek_v4_pro_runs_on_chinese_chips_breaking_us/) |
| https://www.quantamagazine.org/a-new-type-of-neuroplasticity-rewires-the-brain-after-a-single-experience-20260424/ | 1 | [r/u_petburiraja](https://www.reddit.com/r/u_petburiraja/comments/1swzrbl/deepseek_v4_pro_runs_on_chinese_chips_breaking_us/) |
| https://completeaitraining.com/news/meta-installs-keystroke-and-mouse-tracking-software-on/ | 1 | [r/u_petburiraja](https://www.reddit.com/r/u_petburiraja/comments/1swzrbl/deepseek_v4_pro_runs_on_chinese_chips_breaking_us/) |
| https://www.latent.space/p/shopify | 1 | [r/u_petburiraja](https://www.reddit.com/r/u_petburiraja/comments/1swzrbl/deepseek_v4_pro_runs_on_chinese_chips_breaking_us/) |
| https://go.theregister.com/feed/www.theregister.com/2026/04/27/hmrc_hands_28000_staff_ai/ | 1 | [r/u_petburiraja](https://www.reddit.com/r/u_petburiraja/comments/1swzrbl/deepseek_v4_pro_runs_on_chinese_chips_breaking_us/) |
| https://go.theregister.com/feed/www.theregister.com/2026/04/27/anthropics_magic_codesniffer_more_swiss/ | 1 | [r/u_petburiraja](https://www.reddit.com/r/u_petburiraja/comments/1swzrbl/deepseek_v4_pro_runs_on_chinese_chips_breaking_us/) |
| https://simonwillison.net/2026/Apr/24/llm/#atom-everything | 1 | [r/u_petburiraja](https://www.reddit.com/r/u_petburiraja/comments/1swzrbl/deepseek_v4_pro_runs_on_chinese_chips_breaking_us/) |
| https://lilianweng.github.io/posts/2025-05-01-thinking/ | 1 | [r/u_petburiraja](https://www.reddit.com/r/u_petburiraja/comments/1swzrbl/deepseek_v4_pro_runs_on_chinese_chips_breaking_us/) |
| https://github.com/ggml-org/llama.cpp/pull/24162 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1tyb3np/deepseek_v4_flash_is_amazing_wip_llamacpp_pr_24162/) |
| http://CLAUDE.md | 1 | [r/Anthropic](https://www.reddit.com/r/Anthropic/comments/1w3c36a/opus_5_does_low_or_medium_effort_fix_its_behavior/) |
| http://task.md | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1t4m3ox/aura_agent_letting_an_ai_coding_agent_supervise/) |
| https://gamesir.com/products/gamesir-g7-pro-aimlabs-edition | 1 | [r/Gamesir](https://www.reddit.com/r/Gamesir/comments/1s3vuky/ama_g7_pro_8k_giveaway_high_polling_rate_low/) |
| http://continue.dev | 1 | [r/vibecoding](https://www.reddit.com/r/vibecoding/comments/1uhxmom/looking_for_a_vscode_extension_similar_to_github/) |
| https://aimadetools.com/blog/race-week-2-results/ | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1t3b20i/deepseek_v4_pro_is_ranked_2_in_our_ai_startup/) |
| https://glyphformac.com/** | 1 | [r/MacOS](https://www.reddit.com/r/MacOS/comments/1uatjju/open_source_glyph_a_powerful_completely_local/) |
| https://glyphformac.com/ | 1 | [r/MacOS](https://www.reddit.com/r/MacOS/comments/1uatjju/open_source_glyph_a_powerful_completely_local/) |
| https://github.com/SidhuK/Glyph** | 1 | [r/MacOS](https://www.reddit.com/r/MacOS/comments/1uatjju/open_source_glyph_a_powerful_completely_local/) |
| https://github.com/SidhuK/Glyph | 1 | [r/MacOS](https://www.reddit.com/r/MacOS/comments/1uatjju/open_source_glyph_a_powerful_completely_local/) |
| http://djamgamind.com/ | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| http://djamgamind.com/Toolkit | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://link.mail.beehiiv.com/ss/c/u001.ZY5Y0CT8KZaZ1y9TVLsmf-Xx22_GfJopkt2oD7GOFXpg6J2_2Q4dVC6NFnuZNXj0CWosMVHMANE5yk26uUlvdlzXLOhT9SvVBDj8VgwFeOP9rV | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://link.mail.beehiiv.com/ss/c/u001.6k0_SAz8nrOuu_-LoNX1HTkIsYsH7op1maVEyf_d9EBMsC0smmBZkd78vG9pegkjlCsfkeOX0Ir5VjjTtGHjkYU9Ml_81Yon9j5jJjJG-qqsQa | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substackcdn.com/image/fetch/$s_!N9a_ | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf937MUSrYzK6JzB2n81ON3ymJtKugy3xnR2OiUE95ffCeed1VH98y5UQf6sS6mdMsXL9uGirlRgX_CrpDdhwYZpGK0 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf022yDnKIUiG8l1A8gWu3xv7leO644i6U3ZUj9doiXtU_0z7t8r5lRrFD2ohYgR2k48j8gX5o38-lhqEODLEKPKKRv | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://elink983.thedeepview.co/ss/c/u001.8tm-lavloxZbk7LH_fkTGFhJek-NG1AifkLav3Ewj9HZh3atPlu8aO_uJKCWU4oFqjn3uQfOquYU4BPRw0p8XnK6M0z-7s_gTLaWPmRZNC1R | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://elink983.thedeepview.co/ss/c/u001.8tm-lavloxZbk7LH_fkTGFhJek-NG1AifkLav3Ewj9HZh3atPlu8aO_uJKCWU4oFoJauAat47N8zhtTHkNlvDiAMD1Zvp5TwUiFwUtZme08R | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substackcdn.com/image/fetch/$s_!jZrv | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://elink983.thedeepview.co/ss/c/u001.wZPohD0JH12EksCsbt8ZeI4OFgvjTAfi3mBBg7gytZBWydt1iGUo8AwHOGdZQkjYkS0o7cgsaJUrWCbGp1AdkLqjVgmsYwff7pM_Dj6rAEHH | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substackcdn.com/image/fetch/$s_!CJxY | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://developer.android.com/bench | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substackcdn.com/image/fetch/$s_!eq-C | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://link.mail.beehiiv.com/ss/c/u001.6k0_SAz8nrOuu_-LoNX1HS0On60KNFTYlI_9-HUlhckMXz44Re0u9R2THSNWNTTc1yL8l_wQNK6LFhy5p8gOlX4b7-CKkQGygpSaLJdwi23TgI | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf_MnrMNPlyZa0tC_fQ34TxQ78dU03jIigb7dPAeatjyN0Ca8ceLhzeqf2EUmmtqjEE4wQSyepKB_24_zfjFG1OriLr | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://link.mail.beehiiv.com/ss/c/u001.Q334NVcZU4O6L6VKRz8ijFSA78CN6D1L7uwSw-31WnNafnk5iBMDWb-2Tdk4Q1YJUh9GY8P33Dwb0XMe38wTzbNg17mBq4PkS9DBIaFpElWLro | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://link.mail.beehiiv.com/ss/c/u001.6k0_SAz8nrOuu_-LoNX1HUT4U09YQ9wDQ-bFE5yKWR0vhFBquDwJ4vIUC-eaVS0Oncm3Gg6slmZ23Oej72CORKx7fOrq11D74THnBkJPqtTN0z | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf2eV4n7e3bJOirn74G3ZyF1BAQt0YUbg1eq2UM6VoBL747ThsLRaUg3gGKmW1H0XDTIq6V47YWsAU8H_b-E1JlBl7- | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://www.reuters.com/world/china/us-state-dept-orders-global-warning-about-alleged-china-ai-thefts-by-deepseek-2026-04-24/ | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substack.com/redirect/30892a6f-4a87-42ae-ab18-122c76c3468e?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substack.com/redirect/cb48a45e-801e-41e7-936a-639edea7cdb9?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substack.com/redirect/82882cdf-054a-4249-92c0-9ff99eb71e06?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substack.com/redirect/fb0297c1-89e8-461b-b461-207ee4419f5e?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substack.com/redirect/bd0c124c-3dbb-4012-baad-7dea89f489b9?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substack.com/redirect/06cc1324-c287-4f2f-b88b-c5f53fb924e8?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substack.com/redirect/761e06f4-b6d9-4bbf-9baa-c95bf7b66b43?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substack.com/redirect/c2fe720c-9e72-492c-8273-07ac6718ea7c?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substack.com/redirect/9fcf143c-92d3-49e9-9c1c-57db92b11aaf?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substack.com/redirect/08325cbc-d7ef-4814-962f-e1ca1c142d1c?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://substack.com/redirect/c829837d-db9a-4fbb-aa4a-cf2f508de5f1?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) |
| https://pi-hole.net/ | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1w3h2gz/built_a_macos_app_for_pihole_exclusively_using/) |
| http://liquipedia.net/counterstrike/FaZe_Clan | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| http://fazeclan.com | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| http://twitter.com/FaZeClan | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| http://facebook.com/TheFaZeClan | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| http://youtube.com/user/FaZeClan | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| https://www.hltv.org/stats/matches/mapstatsid/63625/virtuspro-vs-faze | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| https://www.hltv.org/stats/matches/mapstatsid/63627/faze-vs-virtuspro | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/86zn2u/faze_clan_vs_virtuspro_v4_future_sports_festival/) |
| https://eventvods.com/csgo/v4-future-sports-festival?utm_source=reddit&amp;utm_medium=subreddit&amp;utm_campaign=post_match_threads | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/872wmp/virtuspro_vs_mousesports_v4_future_sports/) |
| https://www.hltv.org/stats/matches/mapstatsid/63686/virtuspro-vs-mousesports | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/872wmp/virtuspro_vs_mousesports_v4_future_sports/) |
| https://www.hltv.org/stats/matches/mapstatsid/63690/mousesports-vs-virtuspro | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/872wmp/virtuspro_vs_mousesports_v4_future_sports/) |
| https://www.hltv.org/stats/matches/mapstatsid/63697/virtuspro-vs-mousesports | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/872wmp/virtuspro_vs_mousesports_v4_future_sports/) |
| https://wonderrico.github.io/local\_llm\_benchmark/benchmark-main.html?filter=3.8 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w0x1r2/local_agentic_coding_benchmark_qwen38flashnext/) |
| https://wonderrico.github.io/local_llm_benchmark/benchmark-main.html?filter=3.8 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w0x1r2/local_agentic_coding_benchmark_qwen38flashnext/) |
| https://wonderrico.github.io/local\_llm\_benchmark/benchmark-detail.html?filter=3.8 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w0x1r2/local_agentic_coding_benchmark_qwen38flashnext/) |
| https://wonderrico.github.io/local_llm_benchmark/benchmark-detail.html?filter=3.8 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1w0x1r2/local_agentic_coding_benchmark_qwen38flashnext/) |
| https://gofile.io/d/dbnJJHdn | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vmnm3l/deepseek_v4_pro_0813_first_person_shooter_test/) |
| https://files.catbox.moe/ct40ax.html | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vmnm3l/deepseek_v4_pro_0813_first_person_shooter_test/) |
| https://github.com/mov-eax-eax/dsh-token-anxiety | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vph1ig/deepseek_harness_dsh_plugin_to_show_the_cost_per/) |
| https://portal.neuralwatt.com/ | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1tcq264/neuralwatt_has_been_a_surprisingly_good_cheap/) |
| https://github.com/alvinunreal/oh-my-opencode-slim | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1tcq264/neuralwatt_has_been_a_surprisingly_good_cheap/) |
| https://portal.neuralwatt.com/auth/register?ref=NW-BAKHTIAR-R9AV | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1tcq264/neuralwatt_has_been_a_surprisingly_good_cheap/) |
| https://github.com/Laurent00TT/deepseek-v4-vscode-chat | 1 | [r/GithubCopilot](https://www.reddit.com/r/GithubCopilot/comments/1sy6uck/i_wrote_a_deepseek_v4_provider_for_github_copilot/) |
| https://x.com/DevBySami/status/2067579369019572643 | 1 | [r/ArcBrowser](https://www.reddit.com/r/ArcBrowser/comments/1u94qnt/made_a_chromiumbased_arc_alternative_free/) |
| https://artificialanalysis.ai/models?models=deepseek-v4-flash-0420-high%2Cdeepseek-v4-flash | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vbnuda/deepseek_v4_flash_0731/) |
| https://i.postimg.cc/mZHcv2BY/IMG-1339.jpg | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vbnuda/deepseek_v4_flash_0731/) |
| https://x.com/i/status/2083568340870570208 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vdcgpm/setting_up_of_a_16xgb10_dgx_spark_cluster/) |
| https://venturebeat.com/orchestration/deepseeks-top-ranked-v4-flash-stumbles-on-real-agent-tasks-as-its-prices-surge | 1 | [r/BayAreaHomes](https://www.reddit.com/r/BayAreaHomes/comments/1vpxtzo/deepseeks_topranked_v4_flash_stumbles_on_real/) |
| http://github.com/abhinand5/pi-setup | 1 | [r/PiCodingAgent](https://www.reddit.com/r/PiCodingAgent/comments/1u4nr9k/sharing_my_pi_setup/) |
| https://www.thequery.in/articles/deepseek-v4-is-almost-at-the-frontier-the-price-is-not | 1 | [r/FoundationalAI](https://www.reddit.com/r/FoundationalAI/comments/1sv43g5/deepseek_v4_beats_every_closed_model_on/) |
| https://ollama.com/library/deepseek-v4-flash | 1 | [r/ollama](https://www.reddit.com/r/ollama/comments/1vhuqoc/cancelling_my_subscription_also_it_was_great/) |
| https://venice.ai/** | 1 | [r/claude](https://www.reddit.com/r/claude/comments/1vssra1/with_all_the_issues_is_the_open_source_world/) |
| https://venice.ai/ | 1 | [r/claude](https://www.reddit.com/r/claude/comments/1vssra1/with_all_the_issues_is_the_open_source_world/) |
| https://pgsgrove.com/open-grove-overview** | 1 | [r/claude](https://www.reddit.com/r/claude/comments/1vssra1/with_all_the_issues_is_the_open_source_world/) |
| https://hermes-agent.nousresearch.com/** | 1 | [r/claude](https://www.reddit.com/r/claude/comments/1vssra1/with_all_the_issues_is_the_open_source_world/) |
| https://hermes-agent.nousresearch.com/ | 1 | [r/claude](https://www.reddit.com/r/claude/comments/1vssra1/with_all_the_issues_is_the_open_source_world/) |
| https://www.hltv.org/stats/matches/mapstatsid/92106/mousesports-vs-virtuspro | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/d7pax9/mousesports_vs_virtuspro_v4_future_sports/) |
| https://www.hltv.org/stats/matches/mapstatsid/92127/virtuspro-vs-mousesports | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/d7pax9/mousesports_vs_virtuspro_v4_future_sports/) |
| http://liquipedia.net/counterstrike/Tricked_Esport | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/d7vru4/virtuspro_vs_tricked_esport_v4_future_sports/) |
| http://tricked.dk | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/d7vru4/virtuspro_vs_tricked_esport_v4_future_sports/) |
| http://twitter.com/TRICKED_esport | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/d7vru4/virtuspro_vs_tricked_esport_v4_future_sports/) |
| http://facebook.com/trickedesport | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/d7vru4/virtuspro_vs_tricked_esport_v4_future_sports/) |
| http://youtube.com/user/tRICKEDeSport | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/d7vru4/virtuspro_vs_tricked_esport_v4_future_sports/) |
| https://www.hltv.org/stats/matches/mapstatsid/92197/tricked-vs-virtuspro | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/d7vru4/virtuspro_vs_tricked_esport_v4_future_sports/) |
| https://www.hltv.org/stats/matches/mapstatsid/92200/virtuspro-vs-tricked | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/d7vru4/virtuspro_vs_tricked_esport_v4_future_sports/) |
| https://www.hltv.org/stats/matches/mapstatsid/92203/tricked-vs-virtuspro | 1 | [r/GlobalOffensive](https://www.reddit.com/r/GlobalOffensive/comments/d7vru4/virtuspro_vs_tricked_esport_v4_future_sports/) |
| https://www.sina.cn/news/detail/5291195506887337.html | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1uf6cus/why_deepseek_limited_expert_mode_and_when_the/) |
| https://www.neican.ai/insights/deepseek700-20260530111003168-1/ | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1uf6cus/why_deepseek_limited_expert_mode_and_when_the/) |
| https://www.cnstock.com/commonDetail/686936 | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1uf6cus/why_deepseek_limited_expert_mode_and_when_the/) |
| https://github.com/JetXu-LLM/codex-deepseek-bridge | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1u8twzw/codex_deepseek_the_future/) |
| https://github.com/rafek1241/zcode-router | 1 | [r/ZaiGLM](https://www.reddit.com/r/ZaiGLM/comments/1vmqnng/zcoderouter_give_deepseek_v4_flashpro_builtin/) |
| http://127.0.0.1 | 1 | [r/ZaiGLM](https://www.reddit.com/r/ZaiGLM/comments/1vmqnng/zcoderouter_give_deepseek_v4_flashpro_builtin/) |
| https://huggingface.co/unsloth/DeepSeek-V4-Pro-0813-GGUF | 1 | [r/unsloth](https://www.reddit.com/r/unsloth/comments/1vnwtw5/deepseekv4pro0813_ggufs_are_up/) |
| https://x.com/i/status/2084274615829102618 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vozg7c/deepseek_v4_flash_q2_on_a_single_4090/) |
| http://maderix.substack.com | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vozg7c/deepseek_v4_flash_q2_on_a_single_4090/) |
| https://vocaloid.fandom.com/wiki/Akikoloid-chan | 1 | [r/HobbyDrama](https://www.reddit.com/r/HobbyDrama/comments/laobc1/vocaloidvoice_synths_the_stella_saga/) |
| https://upload.wikimedia.org/wikipedia/en/f/ff/Sweetannbox.jpg | 1 | [r/HobbyDrama](https://www.reddit.com/r/HobbyDrama/comments/laobc1/vocaloidvoice_synths_the_stella_saga/) |
| https://www.youtube.com/watch?v=lgRp\_pfQV4Q&amp;feature=emb\_title | 1 | [r/HobbyDrama](https://www.reddit.com/r/HobbyDrama/comments/laobc1/vocaloidvoice_synths_the_stella_saga/) |
| https://www.youtube.com/watch?v=lgRp_pfQV4Q&amp;feature=emb_title | 1 | [r/HobbyDrama](https://www.reddit.com/r/HobbyDrama/comments/laobc1/vocaloidvoice_synths_the_stella_saga/) |
| https://www.youtube.com/watch?v=5xn0q85ujr4 | 1 | [r/HobbyDrama](https://www.reddit.com/r/HobbyDrama/comments/laobc1/vocaloidvoice_synths_the_stella_saga/) |
| https://www.youtube.com/watch?v=inPwXGMsSgw | 1 | [r/HobbyDrama](https://www.reddit.com/r/HobbyDrama/comments/laobc1/vocaloidvoice_synths_the_stella_saga/) |
| https://www.youtube.com/watch?v=yuCqvPZJp-o | 1 | [r/HobbyDrama](https://www.reddit.com/r/HobbyDrama/comments/laobc1/vocaloidvoice_synths_the_stella_saga/) |
| https://www.youtube.com/watch?v=VwWeUTwvjIs | 1 | [r/HobbyDrama](https://www.reddit.com/r/HobbyDrama/comments/laobc1/vocaloidvoice_synths_the_stella_saga/) |
| https://x.com/cline/status/2092725019633992191 | 1 | [r/accelerate](https://www.reddit.com/r/accelerate/comments/1vzk4zp/the_international_math_olympiad_is_the_hardest/) |
| https://www.rtings.com/running-shoes/tools/table/163923 | 1 | [r/RunningShoeGeeks](https://www.reddit.com/r/RunningShoeGeeks/comments/1jtj2ys/33_shoes_tested_for_energy_return_and_energy/) |
| https://www.researchgate.net/publication/333451625_Comparison_of_plantar_loads_among_runners_with_different_strike_patterns | 1 | [r/RunningShoeGeeks](https://www.reddit.com/r/RunningShoeGeeks/comments/1jtj2ys/33_shoes_tested_for_energy_return_and_energy/) |
| https://substackcdn.com/image/fetch/$s_!9lpw | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://enoumen.substack.com?utm_source=substack&amp;utm_campaign=publication_embed&amp;utm_medium=web | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://work.mercor.com/?referralCode=82d5f4e3-e1a3-4064-963f-c197bb2c8db1 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.eCbm_1zon7G0lMoXTECWa-IUY9yqSc2cx0km5OJXo-MgoFOYBji0uSk4KcoGfAmBusdgGHHzvl-VYuPVp40fHkSvlIJr9QAr_AaWfXqIlZg1bc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.eCbm_1zon7G0lMoXTECWa-IUY9yqSc2cx0km5OJXo-MgoFOYBji0uSk4KcoGfAmBusdgGHHzvl-VYuPVp40fHkSvlIJr9QAr_AaWfXqIlZg1bc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://substackcdn.com/image/fetch/$s_!qOZl | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.eCbm_1zon7G0lMoXTECWa-IUY9yqSc2cx0km5OJXo-MgoFOYBji0uSk4KcoGfAmBusdgGHHzvl-VYuPVp40fHkSvlIJr9QAr_AaWfXqIlZg1bc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.a3gBHu6_kDRL6l3yEfNWAaRdeEh1FDO9RIHCC6jyfgX0h1WTIhLOmvrDJ4rQYHehIIuMVBrvBmBawAllDIu-mBX-_GHqEkgF8do_H392JZQBpu | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf022yDnKIUiG8l1A8gWu3xsEj597tU59-HJrlXh7Wg51raM-DEJKbX7v3i9byIK6lRaKqtHZGKQs7rs9gjMnBaQHSf | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf07ka7Wy6WfSudqO4AAVBcuv7FYJneJwjHwRBVxlkqSmlf2Un8BWKYPeVFx7ORLlX-t-ghQjQMlWDj-ipAc4bh9dXA | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf022yDnKIUiG8l1A8gWu3xs0zJR8Id4mq1XrcMtPqqPPrfahGX3vx9fa0ETrndPTAOECPAcHpteIgNW2oCwJCShmcj | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf022yDnKIUiG8l1A8gWu3xvjKhvN7mktM1xnBOnuh1kGjbcnx-CzTLrreKdgsl7CXgzesK0RKO4nb95g6msP4C4QOI | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.7FjCl1Hhb45GEizGv1NNbGamXLmfjEC_u0-ibAXjY2FMe6KcGQHWq95ijVhh_h4KMREvjcn6gKxAbodjZgoXCjeex7-v6sAvnYT_6un75PeQw2 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://substackcdn.com/image/fetch/$s_!bEKu | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.7FjCl1Hhb45GEizGv1NNbGamXLmfjEC_u0-ibAXjY2FMe6KcGQHWq95ijVhh_h4KMREvjcn6gKxAbodjZgoXCjeex7-v6sAvnYT_6un75PeQw2 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.6k0_SAz8nrOuu_-LoNX1HXK-nDoaf59gLMIG6j1gYzbi90HA-yrxT9nplPIqUcYHZmo-SJnRA-FU-00dQbHfhqJt1bFJqG91xAt9t01QkIzquA | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://substackcdn.com/image/fetch/$s_!pJmj | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5sv5nR3bW5BWr2F6lZ3ldW1X0p4L2rl_XrW75J_Bh5LVjzwW25wjd-58 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5t-3qgz0W8wLKSR6lZ3pNW5QC-nP7fzBc2W88H2Qh114lDfW3kJygs7R | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5t-3qgz0W8wLKSR6lZ3nhW4KNwCZ8XTKQFW6b6X6m8TnR-4N9d96Dx_D | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5tH3qgz0W7Y8-PT6lZ3m3W8R8SSF4t93G6W4z66T-6_qV_YVWfbQP2_L | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5sb5nR3bW50kH_H6lZ3npW1htGzR2gyQrQW4WLp8b7xcKJxVtNMqs56Q | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://substackcdn.com/image/fetch/$s_!DPUl | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5t-3qgz0W8wLKSR6lZ3nSW6Zm1n47FycCWW5qbYsr4lpgDzW8ByklN38 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5t-3qgz0W8wLKSR6lZ3kXW8DGh1d2HyB_HW3Vft_j4NPbJ0W4vYcYv78 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5vg3qgz0W95jsWP6lZ3q5W87LN-26RtM4mW4QFPHc60qv5sW5Qy8TG8v | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5sP5nR3bW69t95C6lZ3kqW4LyVGB1QzCHCW8_xV9R2dw84GW6L1Y8d6M | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5tn3qgz0W7lCdLW6lZ3lxW2pXYyq494zglW7hyWDF6cL86gN2n83S3-k | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5tn3qgz0W7lCdLW6lZ3kJW50Fv304WGzvLV1kcGP5tN5f8W33MH9x2DX | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5tn3qgz0W7lCdLW6lZ3l3MnnDb-b62lFW15LXsc342rrtW8wP8c227WL | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5tn3qgz0W7lCdLW6lZ3nXW2dw-yM3Gt8WbW2l5X-f5n-nRVW6DVVn14N | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5tn3qgz0W7lCdLW6lZ3llW5_2K5576mZgQW7djHTv17YZgFW92Y01G31 | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5t45nR3bW6N1X8z6lZ3p-W3WYSzL7nPLY1W1jC2dR6-rqGKW1zFrQh7- | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://info.deeplearning.ai/e3t/Ctc/LX+113/cJhC404/VXjw1f4M88RCW1JZv298tTWq2W3pvQRf5P53tyN1KM5vg5nR3bW95jVnq6lZ3pxW37xWTP1Rh5WSVBlmrC1-SvL8W189vmW5Qf | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://substack.com/app-link/post?publication_id=5695217&amp;post_id=197871571&amp;utm_source=post-email-title&amp;utm_campaign=email-post-title&amp; | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://substack.com/redirect/9ea0cb1b-78d4-4982-8065-afc3e5fb8846?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://substackcdn.com/image/fetch/$s_!582l | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://substack.com/redirect/5e110e91-9bb2-495e-97e0-8886208b0864?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://substack.com/redirect/e2dac420-f020-4c29-bd80-25f8e2779c93?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://substack.com/redirect/e8402d04-5730-42ce-b5e4-9b4b9c707ad3?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://substack.com/redirect/3cc2e920-1b79-4277-a760-93444e34ea0a?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://substack.com/redirect/4709ea6a-a46f-44c2-9a35-4a59d85bb446?j=eyJ1IjoibGd4aHEifQ.AEEwNo9u4c-Yd-EjVJoVC71m13lNOy6HaFEyVpDc_Vc | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.6k0_SAz8nrOuu_-LoNX1HayxoLjw9Gk7PaVZby3ouart2V1SGITmygiMGj5NAcJZtV9aL8mUo0BBPgHtA21B9ohqP-SCUPb9ySiv40Mq67Y3iI | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf0_noi4_YoaiValxMOwruOkOZWWqoPGnNBm9_2adMtEMRgy6MdNriCk-DipykTfUcJUUfB93PlMcv-MdsvU-IYtYJb | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.6k0_SAz8nrOuu_-LoNX1Hemv_fsUrh_dEN45VW7sewYRu1RQ2PuVsQ36tN5kGSdkg2yZRvtfWvbcnk0Sa6XTueKwakYae7p9kY7pCHTtDq2SNu | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.6k0_SAz8nrOuu_-LoNX1HRTeHaO0Mg6UDfNem9Xd2_dme46opm5gZjMpcpO6Cs6SXP2hXOIBp3Sy0Y7-lx7ayy6x5lJyS86fAGJQY-ERV9KOKs | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| https://link.mail.beehiiv.com/ss/c/u001.dSnm3kaGd0BkNqLYPjeMf9JFvua7JJ7w4275sIFLhF5eSrDsm6JbaS3rfwFUnw3x-W6RGpdlAam0k3uATtznlexEpDsWygrIFipeUo1bK4k0za | 1 | [r/u_enoumen](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) |
| http://openrouter.ai | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1sxnvg2/has_anyone_tried_deepseek_v4_pro_flash_for_coding/) |
| https://relaycloud.app/install.sh | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1vtlccz/introducing_relaycloud_secure_shareable_remote/) |
| http://Pi.dev | 1 | [r/openrouter](https://www.reddit.com/r/openrouter/comments/1w1zzso/website_says_1m_token_context_for/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/blob/main/encoding/README.md | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vzwr8q/fixing_overthinking/) |
| https://github.com/earendil-works/pi/blob/main/packages/ai/scripts/generate-models.ts#L286 | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vzwr8q/fixing_overthinking/) |
| https://github.com/anomalyco/opencode/blob/v2/packages/core/src/models-dev.ts#L14 | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vzwr8q/fixing_overthinking/) |
| https://github.com/anomalyco/models.dev/blob/dev/providers/deepseek/models/deepseek-v4-pro.toml#L15 | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vzwr8q/fixing_overthinking/) |
| https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ug5fae/hermesagent_for_usecase_sales_with_selfhosted/) |
| https://nostics.biz | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ug5fae/hermesagent_for_usecase_sales_with_selfhosted/) |
| https://nostics.biz/ | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1ug5fae/hermesagent_for_usecase_sales_with_selfhosted/) |
| https://x.com/arena/status/2083348755559207047?s=20 | 1 | [r/AIGuild](https://www.reddit.com/r/AIGuild/comments/1ve1lak/deepseek_v4_flash_reaches_7_in_arenas_frontend/) |
| https://arena.ai/leaderboard/code/webdev | 1 | [r/AIGuild](https://www.reddit.com/r/AIGuild/comments/1ve1lak/deepseek_v4_flash_reaches_7_in_arenas_frontend/) |
| https://arena.ai/leaderboard/code/webdev/pareto | 1 | [r/AIGuild](https://www.reddit.com/r/AIGuild/comments/1ve1lak/deepseek_v4_flash_reaches_7_in_arenas_frontend/) |
| https://www.eloshapes.com | 1 | [r/MouseReview](https://www.reddit.com/r/MouseReview/comments/1sya16q/eloshapes_now_has_3d_models/) |
| https://opencode.ai/workspace/wrk\_xxxxxxxxxxxxxxxxxxxxxxx/go | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vdvazn/how_to_opt_in_for_deepseek_v4_flash_new_getting/) |
| https://opencode.ai/workspace/wrk_xxxxxxxxxxxxxxxxxxxxxxx/go | 1 | [r/opencode](https://www.reddit.com/r/opencode/comments/1vdvazn/how_to_opt_in_for_deepseek_v4_flash_new_getting/) |
| https://youtu.be/38SQMHBcaV4 | 1 | [r/Denver](https://www.reddit.com/r/Denver/comments/1lfg281/hi_denver_im_a_27yearold_environmental_scientist/) |
| https://i.imgur.com/drARt4z.png | 1 | [r/Denver](https://www.reddit.com/r/Denver/comments/1lfg281/hi_denver_im_a_27yearold_environmental_scientist/) |
| https://www.eventbrite.com/e/happy-hour-with-the-denver-democrats-tickets-1272984674429 | 1 | [r/Denver](https://www.reddit.com/r/Denver/comments/1lfg281/hi_denver_im_a_27yearold_environmental_scientist/) |
| https://www.eventbrite.com/e/2025-denver-democrats-summer-picnic-tickets-1363685141969 | 1 | [r/Denver](https://www.reddit.com/r/Denver/comments/1lfg281/hi_denver_im_a_27yearold_environmental_scientist/) |
| https://bsky.app/profile/cartermrh.bsky.social | 1 | [r/Denver](https://www.reddit.com/r/Denver/comments/1lfg281/hi_denver_im_a_27yearold_environmental_scientist/) |
| https://www.carteradoteam.org/ | 1 | [r/Denver](https://www.reddit.com/r/Denver/comments/1lfg281/hi_denver_im_a_27yearold_environmental_scientist/) |
| https://open.spotify.com/playlist/34XSDu3MAj6TJlLCHTWMgG?si=ce5e5ec42a3248e6 | 1 | [r/Denver](https://www.reddit.com/r/Denver/comments/1lfg281/hi_denver_im_a_27yearold_environmental_scientist/) |
| https://api.deepseek.com/beta | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1sw6j4a/i_can_only_use_deepseek_coder_error_when_i_try_to/) |
| http://chat.deepseek.com | 1 | [r/IA_Italia](https://www.reddit.com/r/IA_Italia/comments/1suc1hd/deepseek_v4_rilasciata_oggi_24_aprile_2026_note/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/blob/main/DeepSeek\_V4.pdf | 1 | [r/IA_Italia](https://www.reddit.com/r/IA_Italia/comments/1suc1hd/deepseek_v4_rilasciata_oggi_24_aprile_2026_note/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/blob/main/DeepSeek_V4.pdf | 1 | [r/IA_Italia](https://www.reddit.com/r/IA_Italia/comments/1suc1hd/deepseek_v4_rilasciata_oggi_24_aprile_2026_note/) |
| https://arena.obside.com | 1 | [r/Daytrading](https://www.reddit.com/r/Daytrading/comments/1ozk8vw/i_let_24_ai_models_trade_to_see_if_they_can/) |
| https://venturebeat.com/technology/deepseek-v4-arrives-with-near-state-of-the-art-intelligence-at-1-6th-the-cost-of-opus-4-7-gpt-5-5 | 1 | [r/Futurology](https://www.reddit.com/r/Futurology/comments/1t2kqyu/deepseek_v4_is_a_sign_that_the_future_world_aios/) |
| https://github.com/LeviTheWeasel/rp-benchmark/ | 1 | [r/SillyTavernAI](https://www.reddit.com/r/SillyTavernAI/comments/1sxz3zo/im_here_to_bring_you_the_weekly_sillytavern_news/) |
| https://github.com/coral-os/coral-code | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1v9im0o/a_graph_of_autonomous_deepseek_v4_pro_agents_is/) |
| https://github.com/coral-os/coral-code/blob/main/benchmarks/latest.json | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1v9im0o/a_graph_of_autonomous_deepseek_v4_pro_agents_is/) |
| https://www.kimi.com/blog/kimi-k3 | 1 | [r/AIDeveloperNews](https://www.reddit.com/r/AIDeveloperNews/comments/1v0dmzw/kimi_k3_vs_deepseek_v4_pro_vs_glm52_open/) |
| https://api-docs.deepseek.com/news/news260424/ | 1 | [r/AIDeveloperNews](https://www.reddit.com/r/AIDeveloperNews/comments/1v0dmzw/kimi_k3_vs_deepseek_v4_pro_vs_glm52_open/) |
| https://huggingface.co/prefeitura-rio/Rio-3.5-Open-397B | 1 | [r/brasil](https://www.reddit.com/r/brasil/comments/1u59989/fun_fact_o_modelo_aberto_mais_avançado_de_ia/) |
| https://www.youtube.com/watch?v=6vPeeADTHuo | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vnci9h/tested_deepseek_v4_pro_0813_on_coding_with/) |
| https://api-docs.deepseek.com/quick\_start/agent\_integrations/claude\_code | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1ur6ocm/best_coding_agent_for_deepseek_v4_pro_api/) |
| https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1ur6ocm/best_coding_agent_for_deepseek_v4_pro_api/) |
| http://oyren.ai/ | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1vigou2/running_ai_agents_in_cloud_with_deepseek_v4_pro/) |
| https://prism-app.tech/pricing.html | 1 | [r/macapps](https://www.reddit.com/r/macapps/comments/1u5tlfh/prism_a_native_osintegrated_macos_ai_assistant/) |
| https://www.linkedin.com/in/aarav-goyal-279964389/ | 1 | [r/macapps](https://www.reddit.com/r/macapps/comments/1u5tlfh/prism_a_native_osintegrated_macos_ai_assistant/) |
| https://github.com/gl-aarav | 1 | [r/macapps](https://www.reddit.com/r/macapps/comments/1u5tlfh/prism_a_native_osintegrated_macos_ai_assistant/) |
| https://prism-app.tech/privacy.html | 1 | [r/macapps](https://www.reddit.com/r/macapps/comments/1u5tlfh/prism_a_native_osintegrated_macos_ai_assistant/) |
| https://prism-app.tech/terms.html | 1 | [r/macapps](https://www.reddit.com/r/macapps/comments/1u5tlfh/prism_a_native_osintegrated_macos_ai_assistant/) |
| https://openbenchmark.dev/model-royale/ | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1tbxj1w/fun_benchmark_got_more_fun/) |
| https://openbenchmark.dev/model-royale/round/2026-05-05/#self-bias | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1tbxj1w/fun_benchmark_got_more_fun/) |
| https://openbenchmark.dev/model-royale/round/2026-05-05/ | 1 | [r/opencodeCLI](https://www.reddit.com/r/opencodeCLI/comments/1tbxj1w/fun_benchmark_got_more_fun/) |
| https://qubrid.com/ | 1 | [r/Qubrid_AI_Platform](https://www.reddit.com/r/Qubrid_AI_Platform/comments/1sumg1r/deepseek_v4_pro_is_now_live_on_qubrid_ai/) |
| https://platform.qubrid.com/playground?model=deepseek-v4-pro | 1 | [r/Qubrid_AI_Platform](https://www.reddit.com/r/Qubrid_AI_Platform/comments/1sumg1r/deepseek_v4_pro_is_now_live_on_qubrid_ai/) |
| https://qubrid.com/blog/deepseek-v4-pro-architecture-benchmarks-api-on-qubrid-ai | 1 | [r/Qubrid_AI_Platform](https://www.reddit.com/r/Qubrid_AI_Platform/comments/1sumg1r/deepseek_v4_pro_is_now_live_on_qubrid_ai/) |
| https://youtu.be/92p8dcRgGm0 | 1 | [r/Qubrid_AI_Platform](https://www.reddit.com/r/Qubrid_AI_Platform/comments/1sumg1r/deepseek_v4_pro_is_now_live_on_qubrid_ai/) |
| https://github.com/Zoo-Code-Org/Zoo-Code/releases/tag/v3.78.0 | 1 | [r/ZooCode](https://www.reddit.com/r/ZooCode/comments/1votz69/newest_models_and_launch_day_support_in_zoo_code/) |
| https://api.gutstore.my.id/key | 1 | [r/jualbeliindonesia](https://www.reddit.com/r/jualbeliindonesia/comments/1vm24yj/wts_unified_ai_gateway_payg_start_from_10k/) |
| https://api-docs.deepseek.com/guides/thinking_mode | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vn7gv9/deepseekv4pro_update_official/) |
| https://artificialanalysis.ai/models/comparisons/deepseek-v4-flash-vs-claude-opus-4-6-adaptive#intelligence-evaluations | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1ve2pls/40x_cheaper_deepseek_v4_flash_0731_compared_to/) |
| https://benchlm.ai/compare/claude-opus-4-6-vs-deepseek-v4-flash-max | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1ve2pls/40x_cheaper_deepseek_v4_flash_0731_compared_to/) |
| https://www.vals.ai/comparison?modelA=anthropic%2Fclaude-opus-4-6-thinking&amp;modelB=deepseek%2Fdeepseek-v4-flash-0731 | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1ve2pls/40x_cheaper_deepseek_v4_flash_0731_compared_to/) |
| https://benchmarklist.com/models/deepseek-deepseek-v4-flash-0731 | 1 | [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1ve2pls/40x_cheaper_deepseek_v4_flash_0731_compared_to/) |
| https://benchmarklist.com/models/z-ai-glm-5.3-flash/ | 1 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1vzv8jz/glm_53_flash_is_3_open_weight_model_and_50/) |
| https://benchmarklist.com/benchmarks/toolathlon/ | 1 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1vzv8jz/glm_53_flash_is_3_open_weight_model_and_50/) |
| https://benchmarklist.com/benchmarks/gdpval_aa/ | 1 | [r/LLMDevs](https://www.reddit.com/r/LLMDevs/comments/1vzv8jz/glm_53_flash_is_3_open_weight_model_and_50/) |
| https://www.pixiv.net/artworks/80075613 | 1 | [r/LearnJapanese](https://www.reddit.com/r/LearnJapanese/comments/fhiash/we_made_a_manga_in_really_easy_japanese_that_is/) |
| https://crystalhuntersmanga.files.wordpress.com/2022/11/japanese-learning-guide-book-1-v4.pdf | 1 | [r/LearnJapanese](https://www.reddit.com/r/LearnJapanese/comments/fhiash/we_made_a_manga_in_really_easy_japanese_that_is/) |
| https://crystalhuntersmanga.com | 1 | [r/LearnJapanese](https://www.reddit.com/r/LearnJapanese/comments/fhiash/we_made_a_manga_in_really_easy_japanese_that_is/) |
| https://gutsai.id/key | 1 | [r/jualbeliindonesia](https://www.reddit.com/r/jualbeliindonesia/comments/1vqiy57/wts_saldo_api_payg_start_from_10k/) |
| https://gutsai.id/bansos | 1 | [r/jualbeliindonesia](https://www.reddit.com/r/jualbeliindonesia/comments/1vqiy57/wts_saldo_api_payg_start_from_10k/) |
| https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-Vision-Exp** | 1 | [r/DeepSeekHarnessPlugin](https://www.reddit.com/r/DeepSeekHarnessPlugin/comments/1w3xbn0/deepseek_opensources_its_first_v4_multimodal/) |
| https://x.com/opencode/status/2087572432181686748 | 1 | [r/OpenCodeGo](https://www.reddit.com/r/OpenCodeGo/comments/1vmkmq8/deepseek_v4pro0813_is_available_in_opencode_go/) |
| https://xcancel.com/opencode/status/2087572432181686748 | 1 | [r/OpenCodeGo](https://www.reddit.com/r/OpenCodeGo/comments/1vmkmq8/deepseek_v4pro0813_is_available_in_opencode_go/) |
| https://x.com/i/status/2087558842271813860 | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vmh3gd/deepseek_v4_pro_ga_is_rolling_out/) |
| https://x.com/i/status/2087561166864146813 | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vmh3gd/deepseek_v4_pro_ga_is_rolling_out/) |
| https://api-docs.deepseek.com/quick\_start/pricing/** | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vmh9k8/deepseekv4pro0813_added_to_the_pricing_page/) |
| https://artificialanalysis.ai/models/open-source | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vzw0og/pareto_frontiers/) |
| https://huggingface.co/spaces/tri-fair-lab/publications/blob/main/Thomson\_1\_0\_Technical\_Report.pdf | 1 | [r/MachineLearning](https://www.reddit.com/r/MachineLearning/comments/1vxvzju/continual_learning_of_frontier_models_for/) |
| http://artificialanalysis.ai | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1ujipih/is_deepseek_v4_pros_base_model_really_beating_o1/) |
| https://artificialanalysis.ai/models/deepseek-v4-flash#intelligence-comparison-tabs | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vbqiub/deepseekv4flash0731_intelligence_index_vs_cost/) |
| https://openai.com/index/advancing-the-price-performance-frontier-with-gpt-5-6/ | 1 | [r/singularity](https://www.reddit.com/r/singularity/comments/1vb1pen/openai_beats_deepseek_on_priceperformance_after/) |
| https://github.com/NousResearch/hermes-agent/pull/90197 | 1 | [r/hermesagent](https://www.reddit.com/r/hermesagent/comments/1vtqajp/hermes_desktops_new_inapp_browser_pane/) |
| https://x.com/deepseek\_ai/status/2087864585504305397 | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1vn8m1x/deepseek_were_launching_deepseekv4pro_today/) |
| https://x.com/synthwavedd/status/2074886230018568582?s=20 | 1 | [r/singularity](https://www.reddit.com/r/singularity/comments/1uqxs8g/decently_reliable_leaker_says_gpt6_will_be_a/) |
| http://build.nvidia.com | 1 | [r/chtouch_com](https://www.reddit.com/r/chtouch_com/comments/1ucevxu/nvidia_nim_api_完整教學免費取得金鑰呼叫_llamadeepseek_等上百個_ai/) |
| https://chtouch.com/nvidia-build-nim-api-tutorial/ | 1 | [r/chtouch_com](https://www.reddit.com/r/chtouch_com/comments/1ucevxu/nvidia_nim_api_完整教學免費取得金鑰呼叫_llamadeepseek_等上百個_ai/) |
| https://character-tavern.com/ | 1 | [r/charactertavern](https://www.reddit.com/r/charactertavern/comments/1sxigti/meet_nami_deepseek_v4_our_latest_addition/) |
| https://github.com/SpeedyGX/deepseek-roocode-proxy | 1 | [r/RooCode](https://www.reddit.com/r/RooCode/comments/1sw7e54/fix_for_deepseek_v4_reasoning_content_must_be/) |
| https://huggingface.co/models?base\_model\_relation=base | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1tq2ce9/hf_models_page_now_has_a_base_only_toggle_to/) |
| https://huggingface.co/models?base_model_relation=base | 1 | [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1tq2ce9/hf_models_page_now_has_a_base_only_toggle_to/) |
| http://gemini.google.com | 1 | [r/GeminiAI](https://www.reddit.com/r/GeminiAI/comments/1us6tx4/bizarre_gemini_35_flash_hallucination/) |
| https://newsletter.semianalysis.com/p/the-future-of-meta-superintelligence | 1 | [r/GeminiAI](https://www.reddit.com/r/GeminiAI/comments/1us6tx4/bizarre_gemini_35_flash_hallucination/) |
| https://x.com/arcprize/status/2085779238007808349?s=20 | 1 | [r/DeepSeek](https://www.reddit.com/r/DeepSeek/comments/1vjjd08/deepseek_sets_new_world_record_on_arcagi_1_and_2/) |
| http://qoder.com | 1 | [r/Qoder](https://www.reddit.com/r/Qoder/comments/1vn9oyi/what_do_you_think_of_deepseekv4pro/) |
| https://commandcode.ai/docs/plans/goat | 1 | [r/CommandCode](https://www.reddit.com/r/CommandCode/comments/1w3hfny/deepseek_v4_flash_fast_is_now_available_in/) |
| https://portal.neuralwatt.com/models | 1 | [r/Neuralwatt](https://www.reddit.com/r/Neuralwatt/comments/1vu2oqr/qwen_38_27b_deepseek_v4_pro_refer_earn_is_back/) |
| https://portal.neuralwatt.com/auth/login?next=/dashboard/referrals | 1 | [r/Neuralwatt](https://www.reddit.com/r/Neuralwatt/comments/1vu2oqr/qwen_38_27b_deepseek_v4_pro_refer_earn_is_back/) |
| https://weekendgolfer.beehiiv.com/ | 1 | [r/weekendgolfers](https://www.reddit.com/r/weekendgolfers/comments/1w3cpxf/amazon_golf_deals_august_31_2026/) |
| https://idownloadcoupon.com/udemy/27563/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27562/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27561/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27560/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27559/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27558/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27557/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27556/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27555/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27554/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27553/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27552/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27551/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27550/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27549/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27548/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27547/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27546/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27545/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27544/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27543/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27542/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27541/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27540/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27539/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27538/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27537/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27536/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27535/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27534/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27533/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27532/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27531/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27530/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27529/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27528/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27527/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27526/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27525/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27524/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27523/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27522/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27521/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27520/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27519/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27518/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27517/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27516/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27515/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27514/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27513/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27512/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27511/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27510/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27509/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27508/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27507/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27506/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27505/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/udemy/27504/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1w3p3if/list_of_free_and_best_selling_discounted_courses/) |
| https://idownloadcoupon.com/ | 1 | [r/udemyfreeebies](https://www.reddit.com/r/udemyfreeebies/comments/1q42dj1/list_of_free_and_best_selling_discounted_courses/) |

## 9. Accounts and subreddits

### 9.1 Most active accounts (literal records)

| Account | Author id | Records | Total score | Account created | Total karma | Top subreddit |
|---|---|---|---|---|---|---|
| u/NecessaryBear98 | `t2_2cvvndmecx` | 37 | 39 | 2026-04-23 | 572 | r/AISEOInsider |
| u/Jonathan_Rivera | `t2_3c1k03sn` | 10 | 1031 | 2019-03-03 | 18005 | r/hermesagent |
| u/TheDeepArchive | `t2_2fcgiubuva` | 8 | 341 | 2026-05-28 | 399 | r/opencode |
| u/gargetisha | `t2_ms94y2x6` | 8 | 876 | 2022-06-26 | 3323 | r/LocalLLM |
| u/CriteriumA | `t2_2d82q2o51k` | 7 | 389 | 2026-04-27 | 1080 | r/opencodeCLI |
| u/Decent-Rain5100 | `t2_1zrwroipfi` | 6 | 222 | 2026-03-31 | 314 | r/vibecoding |
| u/thestreamcode | `t2_ivb43w3e3` | 5 | 96 | 2023-09-02 | 2018 | r/vibecodingitalia |
| u/petburiraja | `t2_60jo8coj` | 4 | 183 | 2021-03-01 | 92448 | r/u_petburiraja |
| u/jhnam88 | `t2_1njlywuqe6` | 4 | 66 | — | — | r/DeepSeek |
| u/ClaudeAI-mod-bot | `t2_1vs6v2gkb0` | 4 | 4 | 2025-08-16 | 5439 | r/ClaudeWorkflows |
| u/IulianHI | `t2_10nqfcv1` | 4 | 21 | 2018-10-01 | 9374 | r/AIToolsPerformance |
| u/minxio_ | `t2_1r2y42s9tb` | 4 | 456 | 2025-06-08 | 10758 | r/DeepSeek |
| u/afanasenka | `t2_1qo7eszg6y` | 4 | 825 | 2025-06-02 | 15467 | r/opencode |
| u/VexObserver | `t2_uteism2f` | 4 | 38 | 2023-01-17 | 5623 | r/WhaleSeekers |
| u/Aromatic-Document638 | `t2_ob09qxx3` | 3 | 161 | 2022-06-08 | 1635 | r/DeepSeek |
| u/fairydreaming | `t2_q06qk` | 3 | 400 | 2015-08-31 | 7555 | r/LocalLLaMA |
| u/korro_ai | `t2_235biflp3f` | 3 | 255 | 2026-06-03 | 369 | r/AIDeveloperNews |
| u/whatsoever2021 | `t2_a22q335k` | 3 | 374 | 2021-01-29 | 2186 | r/opencode |
| u/codes_astro | `t2_l5pkpzux7` | 3 | 6 | — | — | r/LangChain |
| u/lrsaturnin9 | `t2_ovny5` | 3 | 188 | 2015-07-18 | 3878 | r/LLMDevs |
| u/dnx2200 | `t2_4me1uyf` | 3 | 30 | 2018-09-06 | 35 | r/ollama |
| u/maedahbatool | `t2_s3g4io7` | 3 | 145 | 2018-09-26 | 1550 | r/CommandCode |
| u/Whole_Succotash_2391 | `t2_1suofmpw53` | 3 | 4 | — | — | r/claude |
| u/VegetablePen4755 | `t2_xhm86iv5s` | 3 | 2458 | 2024-04-02 | 3669 | r/AI_India |
| u/panchovix | `t2_j1kqr` | 3 | 201 | 2014-10-25 | 93459 | r/LocalLLaMA |
| u/LeTanLoc98 | `t2_25i76blr` | 3 | 261 | 2018-09-08 | 6495 | r/DeepSeek |
| u/des369 | `t2_2ilzwu3bzn` | 3 | 514 | 2026-07-15 | 824 | r/DeepSeek |
| u/ai-lover | `t2_2wsvqwhg` | 3 | 62 | — | — | r/AIDeveloperNews |
| u/TomHale | `t2_bc3fr` | 3 | 22 | 2013-04-16 | 4201 | r/PiCodingAgent |
| u/zubrzysta | `t2_15ygtv` | 3 | 21 | 2017-03-06 | 1016 | r/DeepSeek |

### 9.2 Highest-reach accounts (sum of score on literal records)

| Account | Author id | Total score | Records | Account created | Total karma |
|---|---|---|---|---|---|
| u/VegetablePen4755 | `t2_xhm86iv5s` | 2458 | 3 | 2024-04-02 | 3669 |
| u/Nunki08 | `t2_agjaq` | 1576 | 2 | 2013-02-03 | 350169 |
| u/danielhanchen | `t2_5wukhd4` | 1060 | 2 | 2017-07-19 | 65151 |
| u/ciprianveg | `t2_j8fit2p` | 1042 | 1 | — | — |
| u/Jonathan_Rivera | `t2_3c1k03sn` | 1031 | 10 | 2019-03-03 | 18005 |
| u/nekofneko | `t2_sqi8xxun` | 927 | 2 | 2023-10-11 | 16521 |
| u/gargetisha | `t2_ms94y2x6` | 876 | 8 | 2022-06-26 | 3323 |
| u/riceinmybelly | `t2_9au52` | 851 | 1 | 2012-10-14 | 13729 |
| u/afanasenka | `t2_1qo7eszg6y` | 825 | 4 | 2025-06-02 | 15467 |
| u/yoracale | `t2_1162lx9rgr` | 718 | 1 | 2024-05-26 | 90121 |
| u/rjn2-8 | `t2_23i5gn6049` | 671 | 1 | 2025-12-07 | 2341 |
| u/Normal-Phone7762 | `t2_1cqmbyyfcd` | 664 | 1 | — | — |
| u/Storge2 | `t2_30udbmhy` | 648 | 1 | — | — |
| u/DistanceSolar1449 | `t2_1utnp17o3h` | 564 | 1 | — | — |
| u/mossy_troll_84 | `t2_1gx8uoalsc` | 527 | 1 | — | — |
| u/des369 | `t2_2ilzwu3bzn` | 514 | 3 | 2026-07-15 | 824 |
| u/award_reply | `t2_22ubsoz0gm` | 512 | 1 | 2025-11-27 | 2165 |
| u/ColdKiwi720 | `t2_wqxc99pvz` | 503 | 1 | — | — |
| u/vramkickedin | `t2_2900cnf956` | 483 | 2 | 2026-02-25 | 1172 |
| u/minxio_ | `t2_1r2y42s9tb` | 456 | 4 | 2025-06-08 | 10758 |
| u/SnooBunnies8392 | `t2_9yyyjaak` | 447 | 1 | — | — |
| u/99xAgency | `t2_kbe8fp82y` | 431 | 2 | 2025-07-31 | 1743 |
| u/ProfessionalJackals | `t2_1lqtnyul8t` | 419 | 2 | 2025-03-22 | 9324 |
| u/zeeshanx | `t2_qi0im` | 410 | 1 | — | — |
| u/John_OpenRMA | `t2_2dszn05oi8` | 402 | 1 | — | — |

### 9.3 Subreddits

| Subreddit | Literal records | Total score | Distinct authors | Subscribers |
|---|---|---|---|---|
| r/DeepSeek | 159 | 11353 | 143 | 134302 |
| r/SillyTavernAI | 50 | 4142 | 44 | 126815 |
| r/opencodeCLI | 45 | 2822 | 37 | 56353 |
| r/LocalLLaMA | 40 | 7875 | 36 | 814715 |
| r/AISEOInsider | 37 | 39 | 1 | 8838 |
| r/hermesagent | 33 | 3632 | 26 | 95358 |
| r/opencode | 28 | 1417 | 25 | 34172 |
| r/GithubCopilot | 21 | 1879 | 20 | 84491 |
| r/LocalLLM | 19 | 589 | 16 | 216092 |
| r/ollama | 15 | 353 | 15 | 135715 |
| r/CLine | 12 | 799 | 6 | 19928 |
| r/AI_Agents | 11 | 33 | 11 | 432254 |
| r/ClaudeCode | 11 | 651 | 11 | 400017 |
| r/CommandCode | 11 | 503 | 9 | 3479 |
| r/LLMDevs | 10 | 73 | 8 | 166996 |
| r/openrouter | 8 | 142 | 8 | 18855 |
| r/Qwen_AI | 7 | 263 | 7 | 52608 |
| r/JanitorAI_Refuges | 7 | 30 | 7 | 29915 |
| r/singularity | 6 | 731 | 5 | 3960169 |
| r/vibecoding | 6 | 89 | 6 | 350036 |
| r/ArtificialInteligence | 5 | 799 | 5 | 1913490 |
| r/AIToolsPerformance | 5 | 21 | 2 | 6326 |
| r/codex | 4 | 323 | 4 | 182011 |
| r/cursor | 4 | 76 | 4 | 154410 |
| r/PiCodingAgent | 4 | 171 | 4 | 22592 |
| r/CrofAI | 4 | 30 | 4 | 356 |
| r/ChatGPT | 4 | 22 | 4 | 11615074 |
| r/accelerate | 3 | 142 | 3 | 76276 |
| r/vibecodingitalia | 3 | 77 | 1 | 1413 |
| r/openclaw | 3 | 39 | 3 | 133340 |
| r/MiniMax_AI | 3 | 27 | 2 | 3949 |
| r/IA_Italia | 3 | 22 | 3 | 8072 |
| r/ClaudeWorkflows | 3 | 3 | 1 | 2344 |
| r/unsloth | 3 | 1778 | 2 | 40233 |
| r/WhaleSeekers | 3 | 18 | 1 | 709 |
| r/StableDiffusion | 2 | 483 | 1 | 999030 |
| r/chutesAI | 2 | 19 | 1 | 1841 |
| r/OpenSourceAI | 2 | 32 | 2 | 29612 |
| r/AIDeveloperNews | 2 | 6 | 2 | 15242 |
| r/ClaudeAI | 2 | 9 | 2 | 1107401 |

### 9.4 One promo account is 5% of the literal corpus, and the heuristic did not catch it

The single most prolific account in this corpus is **u/NecessaryBear98** — `t2_2cvvndmecx`, created 2026-04-23, 572 total karma:

| Measure | Value |
|---|---|
| Literal posts | **37 of 727 (5.1% of the whole literal corpus)** |
| Subreddits posted to | r/AISEOInsider only |
| Share of r/AISEOInsider's literal posts | 37 of 37 — the subreddit *is* this account |
| Total score across all 37 posts | 39 (median 1) |
| Reached the hand-read top 150 | 18 |
| Of those, labelled `promo` by hand | **18 of 18** |

Every one is the same shape: a keyword-stuffed title, a YouTube embed, and two links to a paid "AI Profit Boardroom" community, wrapped around spec recital with no original testing. Engagement confirms the community's own verdict — 37 posts earned 39 points between them.

**This is where the substance heuristic failed, and it is worth being explicit about it.** 18 of these posts scored high enough to enter the top 150, because they are long, sectioned, and dense with figures — exactly what the heuristic rewards. The promo penalty did not fire, because they contain none of its trigger words: no *referral*, no *affiliate*, no *promo code*. They sell a membership with a bare link. **Hand reading is the only reason they are labelled promo rather than presented to you as deep analysis** — which is the concrete case for why §11.5's ranking-is-not-classification rule matters.

## 10. Full index of every literal match

All 727 records whose own punctuation-normalised text contains `deepseekv4pro`, in substance-score order. Rows above the read cut carry a hand label; rows below carry a score and no label.

| Rank | Score | Type | Title / thread | Subreddit | Author | Author id | Pts | Cmts | Date | Label |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 39.0 | post | [Running DeepSeek V4 Flash 0731 locally on Strix Halo at 26+ ](https://www.reddit.com/r/LocalAiCore/comments/1vkq5kj/running_deepseek_v4_flash_0731_locally_on_strix/) | r/LocalAiCore | u/stereohype | `t2_4el12` | 13 | 8 | 2026-08-10 | tutorial / mention |
| 2 | 37.6 | post | [You're probably accidentally tokenmaxxing. Learn to delegate](https://www.reddit.com/r/hermesagent/comments/1tph8wg/youre_probably_accidentally_tokenmaxxing_learn_to/) | r/hermesagent | u/jebk | `t2_a6g68` | 126 | 53 | 2026-05-27 | workflow/setup / mention |
| 6 | 35.1 | post | [Masterthread - Models Feedback (Last 2 Weeks)](https://www.reddit.com/r/hermesagent/comments/1t4j7r5/masterthread_models_feedback_last_2_weeks/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 25 | 22 | 2026-05-05 | news roundup / mention |
| 8 | 34.8 | post | [SPECIAL REPORT: The r/hermesagent Model Civil War](https://www.reddit.com/r/hermesagent/comments/1uqd00s/special_report_the_rhermesagent_model_civil_war/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 237 | 25 | 2026-07-08 | news roundup / mention |
| 15 | 32.6 | post | [I benchmarked Codex GPT-5.5 against Chinese models. Not what](https://www.reddit.com/r/codex/comments/1u7zabq/i_benchmarked_codex_gpt55_against_chinese_models/) | r/codex | u/DaC2k26 | `t2_262f9urxov` | 204 | 157 | 2026-06-17 | benchmark / mention |
| 23 | 30.7 | post | [Models, Providers &amp; Plans Megathread — June 2026](https://www.reddit.com/r/hermesagent/comments/1ufrtsf/models_providers_plans_megathread_june_2026/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 99 | 43 | 2026-06-26 | news roundup / mention |
| 24 | 30.6 | post | [I ran a personal AI benchmark across 6 models, DeepSeek V4 P](https://www.reddit.com/r/GithubCopilot/comments/1t0mcov/i_ran_a_personal_ai_benchmark_across_6_models/) | r/GithubCopilot | u/noman_hasan | `t2_7uf7hsyp` | 25 | 24 | 2026-05-01 | benchmark / subject |
| 29 | 29.6 | post | [Open WebUI is completely broken now](https://www.reddit.com/r/OpenWebUI/comments/1tcslos/open_webui_is_completely_broken_now/) | r/OpenWebUI | u/eteitaxiv | `t2_f137l` | 32 | 27 | 2026-05-14 | deep analysis / mention |
| 31 | 29.0 | post | [I Compared Deepseek V4 Flash vs Pro On 5 Workflows](https://www.reddit.com/r/AISEOInsider/comments/1v3any1/i_compared_deepseek_v4_flash_vs_pro_on_5_workflows/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 3 | 0 | 2026-07-22 | promo / subject |
| 32 | 28.6 | post | [Chatfill v2 - MiMo Edition (Experiment No. 1, dealing with s](https://www.reddit.com/r/SillyTavernAI/comments/1u436a0/chatfill_v2_mimo_edition_experiment_no_1_dealing/) | r/SillyTavernAI | u/eteitaxiv | `t2_f137l` | 50 | 7 | 2026-06-12 | workflow/setup / mention |
| 33 | 28.5 | post | [I tested Opus 4.7 vs DeepSeek V4 Flash vs Local Qwen3.6 27B ](https://www.reddit.com/r/LocalLLM/comments/1sxdg81/i_tested_opus_47_vs_deepseek_v4_flash_vs_local/) | r/LocalLLM | u/a9udn9u | `t2_qj8wl` | 139 | 67 | 2026-04-27 | comparison / mention |
| 35 | 28.5 | post | [My Hermes Setup, rate it](https://www.reddit.com/r/hermesagent/comments/1v70s6u/my_hermes_setup_rate_it/) | r/hermesagent | u/EquivalentTop4824 | `t2_1yxq3mofmm` | 267 | 69 | 2026-07-26 | workflow/setup / mention |
| 36 | 28.4 | post | [$5 for a Week of Work: How We Use AI to Capture Fragmented E](https://www.reddit.com/r/AI_Agents/comments/1ve4pbi/5_for_a_week_of_work_how_we_use_ai_to_capture/) | r/AI_Agents | u/No-Mathematician5599 | `t2_pztsedui` | 3 | 4 | 2026-08-03 | usage demo / mention |
| 37 | 28.2 | post | [I forked the Disco Elysium Skills Lorebook: added real dice,](https://www.reddit.com/r/SillyTavernAI/comments/1udubji/i_forked_the_disco_elysium_skills_lorebook_added/) | r/SillyTavernAI | u/TM07P | `t2_ss5631wp` | 86 | 19 | 2026-06-23 | workflow/setup / mention |
| 38 | 28.1 | post | [A comprehensive method to brutally reduce your Agentic AI to](https://www.reddit.com/r/hermesagent/comments/1ths4dt/a_comprehensive_method_to_brutally_reduce_your/) | r/hermesagent | u/dxzzzzzz | `t2_5vdv4dw8` | 52 | 27 | 2026-05-19 | workflow/setup / mention |
| 39 | 28.0 | post | [Gonna give FEIHOA a shot.](https://www.reddit.com/r/Qwen_AI/comments/1w2md1s/gonna_give_feihoa_a_shot/) | r/Qwen_AI | u/SubjectPenalty1352 | `t2_azkibcr7` | 0 | 15 | 2026-08-30 | opinion / mention |
| 42 | 28.0 | post | [The Definitive Qwen3.8-27B Deep Dive](https://www.reddit.com/r/BriefDelights/comments/1vkvfwu/the_definitive_qwen3827b_deep_dive/) | r/BriefDelights | u/Disrupt-Linus | `t2_4cyagmev` | 1 | 0 | 2026-08-10 | deep analysis / mention |
| 43 | 28.0 | post | [Cost &amp; Token Optimization Megathread — Hermes Agent (Jun](https://www.reddit.com/r/hermesagent/comments/1ud03si/cost_token_optimization_megathread_hermes_agent/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 104 | 42 | 2026-06-22 | news roundup / mention |
| 44 | 27.7 | post | [A boring agent doing a boring job — triaging security scanne](https://www.reddit.com/r/AI_Agents/comments/1v7uqpc/a_boring_agent_doing_a_boring_job_triaging/) | r/AI_Agents | u/coldyx | `t2_3jb35v` | 4 | 13 | 2026-07-27 | benchmark / subject |
| 45 | 27.6 | post | [I benchmarked antirez's DeepSeek V4 Flash Metal engine. The ](https://www.reddit.com/r/DeepSeek/comments/1t6tzha/i_benchmarked_antirezs_deepseek_v4_flash_metal/) | r/DeepSeek | u/TroyNoah6677 | `t2_29catc38fp` | 20 | 24 | 2026-05-08 | benchmark / mention |
| 47 | 27.6 | post | [# Qwen3.8-27B — One Week Later: The r/LocalLLaMA + r/LocalLL](https://www.reddit.com/r/LocalLLM/comments/1vvu1uj/qwen3827b_one_week_later_the_rlocalllama/) | r/LocalLLM | u/Jonathan_Rivera | `t2_3c1k03sn` | 174 | 33 | 2026-08-23 | deep analysis / mention |
| 50 | 27.4 | post | [LLM competition within Hermes: a recommended idea you should](https://www.reddit.com/r/hermesagent/comments/1txzail/llm_competition_within_hermes_a_recommended_idea/) | r/hermesagent | u/Almarma | `t2_ixcdr` | 78 | 34 | 2026-06-05 | comparison / subject |
| 52 | 27.2 | post | [We use LLMs to analyze every file in your codebase. Everyone](https://www.reddit.com/r/ArtificialInteligence/comments/1tatqdn/we_use_llms_to_analyze_every_file_in_your/) | r/ArtificialInteligence | u/graphicaldot | `t2_cukt6an` | 1 | 6 | 2026-05-12 | benchmark / mention |
| 53 | 27.0 | post | [MiMo2.5Pro 14hours Review. A Comparison with DeepSeek V4 Pro](https://www.reddit.com/r/DeepSeek/comments/1u76ss6/mimo25pro_14hours_review_a_comparison_with/) | r/DeepSeek | u/Aromatic-Document638 | `t2_ob09qxx3` | 124 | 48 | 2026-06-16 | comparison / subject |
| 56 | 27.0 | post | [Build 5 AI Agents With New Chinese AI Model FREE (2026)](https://www.reddit.com/r/AISEOInsider/comments/1u55sz5/build_5_ai_agents_with_new_chinese_ai_model_free/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-06-13 | promo / mention |
| 57 | 27.0 | post | [Testing 9 OpenCode Go models on a Delphi/FireDAC code genera](https://www.reddit.com/r/opencodeCLI/comments/1tsqrbd/testing_9_opencode_go_models_on_a_delphifiredac/) | r/opencodeCLI | u/CriteriumA | `t2_2d82q2o51k` | 69 | 19 | 2026-05-31 | benchmark / mention |
| 58 | 26.8 | post | [I have DeepSeek V4 Pro at home](https://www.reddit.com/r/LocalLLaMA/comments/1t94ito/i_have_deepseek_v4_pro_at_home/) | r/LocalLLaMA | u/fairydreaming | `t2_q06qk` | 288 | 155 | 2026-05-10 | usage demo / subject |
| 61 | 26.7 | post | [DeepSeek V4 Flash vs DeepSeek V4 Pro — Agent Prompt Battle](https://www.reddit.com/r/opencodeCLI/comments/1ttxclt/deepseek_v4_flash_vs_deepseek_v4_pro_agent_prompt/) | r/opencodeCLI | u/CriteriumA | `t2_2d82q2o51k` | 32 | 5 | 2026-06-01 | comparison / subject |
| 62 | 26.6 | post | [DeepSeek V4 Flash (0731) vs DeepSeek V4 Pro (0813): I benchm](https://www.reddit.com/r/opencode/comments/1vnaje2/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813_i/) | r/opencode | u/TheDeepArchive | `t2_2fcgiubuva` | 187 | 13 | 2026-08-13 | benchmark / subject |
| 63 | 26.6 | post | [I benchmarked 7 OpenCode Go models against each other. Flash](https://www.reddit.com/r/opencodeCLI/comments/1svzgd4/i_benchmarked_7_opencode_go_models_against_each/) | r/opencodeCLI | u/petburiraja | `t2_60jo8coj` | 44 | 19 | 2026-04-26 | benchmark / mention |
| 64 | 26.4 | post | [Qwen 3.8 27B One Week Later: Quants, Context, Tool Calling, ](https://www.reddit.com/r/LocalLLaMa_V2/comments/1vvzckl/qwen_38_27b_one_week_later_quants_context_tool/) | r/LocalLLaMa_V2 | u/Jonathan_Rivera | `t2_3c1k03sn` | 9 | 2 | 2026-08-23 | deep analysis / mention |
| 66 | 26.1 | post | [[NEW PRESET] Writer's Block: Unlimited Framework! An Experim](https://www.reddit.com/r/SillyTavernAI/comments/1vqontp/new_preset_writers_block_unlimited_framework_an/) | r/SillyTavernAI | u/Deiomo | `t2_1kmbl0in` | 168 | 16 | 2026-08-17 | workflow/setup / mention |
| 67 | 26.0 | post | [Considering that no one wants to calculate electricity and w](https://www.reddit.com/r/aiwars/comments/1tuvr0s/considering_that_no_one_wants_to_calculate/) | r/aiwars | u/Questioner8297 | `t2_1lg0cmd521` | 19 | 31 | 2026-06-02 | deep analysis / subject |
| 68 | 26.0 | post | [Distilled DeepSeek into Gemma 4 26B-A4B vs 12B. Not very use](https://www.reddit.com/r/LocalLLaMA/comments/1ur1i1a/distilled_deepseek_into_gemma_4_26ba4b_vs_12b_not/) | r/LocalLLaMA | u/Paramecium_caudatum_ | `t2_btfxjl0dc` | 139 | 23 | 2026-07-08 | usage demo / mention |
| 70 | 25.8 | post | [pi agent with DeepSeek v4 Pro is the beast: $0.45 for a heav](https://www.reddit.com/r/DeepSeek/comments/1ug96uv/pi_agent_with_deepseek_v4_pro_is_the_beast_045/) | r/DeepSeek | u/somerussianbear | `t2_orl7ga5` | 68 | 17 | 2026-06-26 | usage demo / subject |
| 71 | 25.8 | post | [Is deepseek actually good](https://www.reddit.com/r/DeepSeek/comments/1ubxhen/is_deepseek_actually_good/) | r/DeepSeek | u/Old_Cantaloupe_6558 | `t2_10p6cizqui` | 97 | 36 | 2026-06-21 | comparison / mention |
| 72 | 25.8 | post | [Ollama Cloud reliability + speed: 36-call bench across DeepS](https://www.reddit.com/r/ollama/comments/1sxjbo5/ollama_cloud_reliability_speed_36call_bench/) | r/ollama | u/deparko | `t2_114ttv` | 13 | 4 | 2026-04-27 | benchmark / subject |
| 73 | 25.6 | post | [I've tested Deep Seek v4 pro (Max) vs Gemini Flash 3.7 (High](https://www.reddit.com/r/DeepSeek/comments/1vnm51p/ive_tested_deep_seek_v4_pro_max_vs_gemini_flash/) | r/DeepSeek | u/alinoanta21 | `t2_31z2l7k9` | 288 | 43 | 2026-08-13 | comparison / subject |
| 74 | 25.6 | post | [DeepSeek V4 Flash (0731) vs DeepSeek V4 Pro (0813): I benchm](https://www.reddit.com/r/DeepSeek/comments/1vnc7u7/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813_i/) | r/DeepSeek | u/TheDeepArchive | `t2_2fcgiubuva` | 57 | 14 | 2026-08-13 | benchmark / subject |
| 75 | 25.6 | post | [DeepSeek V4 Flash (0731) vs DeepSeek V4 Pro (0813): I benchm](https://www.reddit.com/r/LLMDevs/comments/1vnccvm/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813_i/) | r/LLMDevs | u/TheDeepArchive | `t2_2fcgiubuva` | 17 | 7 | 2026-08-13 | benchmark / subject |
| 76 | 25.6 | post | [Qwen3.8-27B — One Week Later: The r/LocalLLaMA + r/LocalLLM ](https://www.reddit.com/r/hermesagent/comments/1vvtrc5/qwen3827b_one_week_later_the_rlocalllama/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 61 | 14 | 2026-08-23 | deep analysis / mention |
| 77 | 25.6 | post | [I built a thing that delegates Claude Code's grunt work to c](https://www.reddit.com/r/coolgithubprojects/comments/1uv6w44/i_built_a_thing_that_delegates_claude_codes_grunt/) | r/coolgithubprojects | u/fjgbu1 | `t2_2eyrsqstol` | 45 | 5 | 2026-07-13 | usage demo / mention |
| 86 | 25.2 | post | [We tested 8 models on a real shop's live order and pricing A](https://www.reddit.com/r/AI_Agents/comments/1vrtezz/we_tested_8_models_on_a_real_shops_live_order_and/) | r/AI_Agents | u/nejcar20 | `t2_6aq5wiqz` | 6 | 8 | 2026-08-18 | benchmark / mention |
| 89 | 25.0 | post | [Visual comparison of various models - a very subjective, but](https://www.reddit.com/r/LocalLLaMA/comments/1w21qz0/visual_comparison_of_various_models_a_very/) | r/LocalLLaMA | u/Gesha24 | `t2_yeiah` | 2 | 0 | 2026-08-29 | comparison / mention |
| 90 | 25.0 | post | [De-Mystifying Opencode Model Economy](https://www.reddit.com/r/opencode/comments/1w0wroi/demystifying_opencode_model_economy/) | r/opencode | u/rev_ex_id | `t2_uutoufdd` | 34 | 14 | 2026-08-28 | deep analysis / mention |
| 91 | 25.0 | post | [AI-Driven Development: A Playbook for a Virtual Dev Team (op](https://www.reddit.com/r/opencode/comments/1vo5y4y/aidriven_development_a_playbook_for_a_virtual_dev/) | r/opencode | u/TheDeepArchive | `t2_2fcgiubuva` | 6 | 13 | 2026-08-14 | workflow/setup / subject |
| 92 | 25.0 | post | [Deepseek v4 vs kimi k2.6 vs gpt5.5 breakdown](https://www.reddit.com/r/LLMDevs/comments/1t0o89l/deepseek_v4_vs_kimi_k26_vs_gpt55_breakdown/) | r/LLMDevs | u/aidenclarke_12 | `t2_1we9gevp4b` | 2 | 2 | 2026-05-01 | comparison / subject |
| 96 | 25.0 | post | [Life After DeepSeek: The King Is Dead. Comparing the Models ](https://www.reddit.com/r/opencode/comments/1vqq92m/life_after_deepseek_the_king_is_dead_comparing/) | r/opencode | u/Proper-Mousse7182 | `t2_rdkb3t00x` | 146 | 76 | 2026-08-17 | comparison / mention |
| 97 | 24.9 | post | [A love letter to DSV4 Pro 0813](https://www.reddit.com/r/DeepSeek/comments/1vpn811/a_love_letter_to_dsv4_pro_0813/) | r/DeepSeek | u/Brotherindeed | `t2_8lyhscyp` | 25 | 19 | 2026-08-16 | opinion / subject |
| 98 | 24.8 | post | [🖥️ The r/hermesagent VPS Megathread - Community-Curated Guid](https://www.reddit.com/r/hermesagent/comments/1tw9lbd/the_rhermesagent_vps_megathread_communitycurated/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 70 | 17 | 2026-06-04 | news roundup / mention |
| 100 | 24.7 | post | [DeepSeek V4 in llama.cpp — Flash + Pro, CUDA + Metal, GGUFs ](https://www.reddit.com/r/LocalLLM/comments/1taclsw/deepseek_v4_in_llamacpp_flash_pro_cuda_metal/) | r/LocalLLM | u/cchuter | `t2_quzka` | 5 | 5 | 2026-05-11 | usage demo / subject |
| 102 | 24.6 | post | [GUIDE] DeepSeek V4: Stop messing up your prompts. Chinese de](https://www.reddit.com/r/DeepSeek/comments/1svkpih/guide_deepseek_v4_stop_messing_up_your_prompts/) | r/DeepSeek | u/refi9 | `t2_12or4ben` | 0 | 0 | 2026-04-25 | tutorial / subject |
| 103 | 24.6 | post | [Significantly lower value in Cursor subscription!](https://www.reddit.com/r/cursor/comments/1uywf62/significantly_lower_value_in_cursor_subscription/) | r/cursor | u/divinefriend | `t2_wros8` | 37 | 61 | 2026-07-17 | opinion / mention |
| 104 | 24.6 | post | [LLMs, AI, and Roleplay 101](https://www.reddit.com/r/Chai_Unofficial/comments/1u4mf79/llms_ai_and_roleplay_101/) | r/Chai_Unofficial | u/Fearless_Profit872 | `t2_1ehl17250k` | 11 | 5 | 2026-06-13 | tutorial / mention |
| 106 | 24.5 | post | [I built a 9-agent SDD harness where each phase uses a differ](https://www.reddit.com/r/opencode/comments/1ttts4v/i_built_a_9agent_sdd_harness_where_each_phase/) | r/opencode | u/Striking-Buffalo-310 | `t2_bb2svjqd` | 97 | 66 | 2026-06-01 | workflow/setup / mention |
| 107 | 24.5 | post | [How to use AI for coding with a tight budget? \| Guide](https://www.reddit.com/r/DevLK/comments/1veyvem/how_to_use_ai_for_coding_with_a_tight_budget_guide/) | r/DevLK | u/yexgoblin | `t2_2g7qu2y1pp` | 18 | 15 | 2026-08-04 | tutorial / mention |
| 108 | 24.5 | post | [30B+ tokens with Xiaomi MiMo v2.5 Pro: switched from Claude/](https://www.reddit.com/r/AI_Agents/comments/1u3x60c/30b_tokens_with_xiaomi_mimo_v25_pro_switched_from/) | r/AI_Agents | u/TayyabAliKhan | `t2_1gd3b0bx` | 3 | 7 | 2026-06-12 | usage demo / mention |
| 109 | 24.5 | post | [30B+ tokens with Xiaomi MiMo v2.5 Pro: switched from Claude/](https://www.reddit.com/r/Agentic_Marketing/comments/1u46ugv/30b_tokens_with_xiaomi_mimo_v25_pro_switched_from/) | r/Agentic_Marketing | u/TayyabAliKhan | `t2_1gd3b0bx` | 3 | 2 | 2026-06-12 | usage demo / mention |
| 110 | 24.4 | post | [My Hermes setup, roast me](https://www.reddit.com/r/hermesagent/comments/1u9fa2w/my_hermes_setup_roast_me/) | r/hermesagent | u/riceinmybelly | `t2_9au52` | 851 | 156 | 2026-06-18 | workflow/setup / mention |
| 111 | 24.4 | post | [Benchmarking DeepSeek V4 Pro vs Flash for Hermes Agent: perf](https://www.reddit.com/r/hermesagent/comments/1vw1hmu/benchmarking_deepseek_v4_pro_vs_flash_for_hermes/) | r/hermesagent | u/dontWORRYimASIAN | `t2_ayqw1` | 11 | 1 | 2026-08-23 | benchmark / subject |
| 114 | 24.3 | post | [Big lineup refresh DeepSeek V4, GPT-5.5, Kimi K2.6, Gemini 3](https://www.reddit.com/r/AIStupidLevel/comments/1thhkcf/big_lineup_refresh_deepseek_v4_gpt55_kimi_k26/) | r/AIStupidLevel | u/ionutvi | `t2_5a186uc1` | 1 | 1 | 2026-05-19 | announcement / mention |
| 115 | 24.3 | post | [Onklaud 5 : a fusion model pipeline matching Fable 5 at 1/10](https://www.reddit.com/r/OpenSourceeAI/comments/1ujr7qb/onklaud_5_a_fusion_model_pipeline_matching_fable/) | r/OpenSourceeAI | u/korro_ai | `t2_235biflp3f` | 225 | 66 | 2026-06-30 | usage demo / mention |
| 119 | 24.0 | post | [DeepSeek V4 Pro 0813 Nearly Matches Top Models On Agent Benc](https://www.reddit.com/r/AISEOInsider/comments/1vqrup2/deepseek_v4_pro_0813_nearly_matches_top_models_on/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-17 | promo / subject |
| 120 | 24.0 | post | [I have (even faster) DeepSeek V4 Pro at home](https://www.reddit.com/r/LocalLLaMA/comments/1tdpk3f/i_have_even_faster_deepseek_v4_pro_at_home/) | r/LocalLLaMA | u/fairydreaming | `t2_q06qk` | 47 | 53 | 2026-05-15 | benchmark / subject |
| 123 | 24.0 | post | [Ernie AI Benchmark Makes China’s AI Race Interesting](https://www.reddit.com/r/AISEOInsider/comments/1te72in/ernie_ai_benchmark_makes_chinas_ai_race/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-05-15 | promo / mention |
| 125 | 23.8 | post | [MiMo V2.5 Free vs DeepSeek V4 Flash Free](https://www.reddit.com/r/opencodeCLI/comments/1txpher/mimo_v25_free_vs_deepseek_v4_flash_free/) | r/opencodeCLI | u/CriteriumA | `t2_2d82q2o51k` | 57 | 23 | 2026-06-05 | comparison / mention |
| 126 | 23.8 | post | [Free Models &amp; APIs for Hermes Agent — Megathread (June 2](https://www.reddit.com/r/hermesagent/comments/1uj9nkn/free_models_apis_for_hermes_agent_megathread_june/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 185 | 56 | 2026-06-30 | news roundup / mention |
| 127 | 23.8 | post | [Homemade and specific comparison of OpenCode Go models: Glm,](https://www.reddit.com/r/opencodeCLI/comments/1trgcw9/homemade_and_specific_comparison_of_opencode_go/) | r/opencodeCLI | u/CriteriumA | `t2_2d82q2o51k` | 44 | 15 | 2026-05-29 | comparison / mention |
| 128 | 23.7 | post | [Deekseek-v4-Flash 0731 vs. v4-Pro vs. Qwen3.8-max in Stock M](https://www.reddit.com/r/DeepSeek/comments/1vc3kce/deekseekv4flash_0731_vs_v4pro_vs_qwen38max_in/) | r/DeepSeek | u/hhspiny | `t2_1diedn2moi` | 9 | 2 | 2026-07-31 | benchmark / subject |
| 130 | 23.6 | post | [DeepSeek V4 Flash vs DeepSeek V4 Pro - Compaction](https://www.reddit.com/r/opencodeCLI/comments/1tv98pu/deepseek_v4_flash_vs_deepseek_v4_pro_compaction/) | r/opencodeCLI | u/CriteriumA | `t2_2d82q2o51k` | 86 | 28 | 2026-06-03 | benchmark / subject |
| 132 | 23.5 | post | [Run Claude Code with Qwen3.7 and stop hitting limits](https://www.reddit.com/r/Qwen_AI/comments/1ts15j1/run_claude_code_with_qwen37_and_stop_hitting/) | r/Qwen_AI | u/stosssik | `t2_iu9kylc` | 44 | 9 | 2026-05-30 | tutorial / mention |
| 133 | 23.5 | post | [Run Claude Code with Qwen3.7 and stop hitting limits](https://www.reddit.com/r/ManifestforAI/comments/1ts10h0/run_claude_code_with_qwen37_and_stop_hitting/) | r/ManifestforAI | u/stosssik | `t2_iu9kylc` | 42 | 4 | 2026-05-30 | tutorial / mention |
| 135 | 23.4 | post | [Building a Python Project with DeepSeek V4: Lessons Learned](https://www.reddit.com/r/DeepSeek/comments/1u5nlme/building_a_python_project_with_deepseek_v4/) | r/DeepSeek | u/whatsoever2021 | `t2_a22q335k` | 160 | 48 | 2026-06-14 | usage demo / subject |
| 137 | 23.4 | post | [Local AI News You Missed - April 2026](https://www.reddit.com/r/StableDiffusion/comments/1t0bm5w/local_ai_news_you_missed_april_2026/) | r/StableDiffusion | u/vramkickedin | `t2_2900cnf956` | 370 | 35 | 2026-04-30 | news roundup / mention |
| 139 | 23.3 | post | [Welcome to August 4, 2026 - Dr. Alex Wissner-Gross](https://www.reddit.com/r/accelerate/comments/1vfu67m/welcome_to_august_4_2026_dr_alex_wissnergross/) | r/accelerate | u/alexwg | `t2_3mekb` | 33 | 1 | 2026-08-05 | news roundup / mention |
| 141 | 23.1 | post | [DeepSeek-V4-Pro-0813 is official: agent benchmarks land, Res](https://www.reddit.com/r/chutesAI/comments/1vn8197/deepseekv4pro0813_is_official_agent_benchmarks/) | r/chutesAI | u/thestreamcode | `t2_ivb43w3e3` | 6 | 0 | 2026-08-13 | announcement / subject |
| 143 | 23.0 | post | [Deepseek v4 Pro 0813 - Minimal Preset on DSH vs other models](https://www.reddit.com/r/DeepSeek/comments/1vpcutr/deepseek_v4_pro_0813_minimal_preset_on_dsh_vs/) | r/DeepSeek | u/Ok_Shelter_2181 | `t2_kzcqk64h` | 12 | 2 | 2026-08-15 | usage demo / subject |
| 145 | 23.0 | post | [DeepSeek V4 Pro 0813 Benchmark Just Shocked AI (2026)](https://www.reddit.com/r/AISEOInsider/comments/1vny1dz/deepseek_v4_pro_0813_benchmark_just_shocked_ai/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 0 | 0 | 2026-08-14 | promo / subject |
| 146 | 23.0 | post | [Free DeepSeek V4 Flash Beats Pro On 9 Agent Benchmarks](https://www.reddit.com/r/AISEOInsider/comments/1vqdj2v/free_deepseek_v4_flash_beats_pro_on_9_agent/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-17 | promo / mention |
| 148 | 23.0 | post | [Openrouter vs every other OAuth subscription?](https://www.reddit.com/r/hermesagent/comments/1ufjpa7/openrouter_vs_every_other_oauth_subscription/) | r/hermesagent | u/Secret-Access9909 | `t2_ofo7a7sb` | 89 | 74 | 2026-06-25 | question / mention |
| 151 | 22.8 | post | [I benchmarked 9 open models on spotting fake sources during ](https://www.reddit.com/r/LocalLLaMA/comments/1w0zl5q/i_benchmarked_9_open_models_on_spotting_fake/) | r/LocalLLaMA | u/RevealIndividual7567 | `t2_27ldufdnxm` | 92 | 20 | 2026-08-28 | benchmark / mention |
| 152 | 22.8 | post | [DeepSeek V4 Pro Release Just Shocked The AI World](https://www.reddit.com/r/AISEOInsider/comments/1vrc9vq/deepseek_v4_pro_release_just_shocked_the_ai_world/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-18 | promo / subject |
| 153 | 22.8 | post | [I spent $100 benchmarking GPT-4o, Claude Opus 4, and DeepSee](https://www.reddit.com/r/DeepSeek/comments/1tv9ml8/i_spent_100_benchmarking_gpt4o_claude_opus_4_and/) | r/DeepSeek | u/ApprehensiveHat2274 | `t2_26owf6r8el` | 0 | 15 | 2026-06-03 | benchmark / subject |
| 159 | 22.6 | post | [The exact KV cache usage of DeepSeek V4](https://www.reddit.com/r/LocalLLaMA/comments/1svzlog/the_exact_kv_cache_usage_of_deepseek_v4/) | r/LocalLLaMA | u/Ok_Warning2146 | `t2_s6sfw4yy` | 136 | 60 | 2026-04-26 | deep analysis / subject |
| 160 | 22.6 | post | [Why did OpenRouter bill 4M tokens when OpenCode showed only ](https://www.reddit.com/r/openrouter/comments/1u2ue4m/why_did_openrouter_bill_4m_tokens_when_opencode/) | r/openrouter | u/moha35abu | `t2_ydsb3foeo` | 11 | 22 | 2026-06-11 | question / subject |
| 161 | 22.6 | post | [Here’s why OpenAI/Anthropic will not go bankrupt (inference ](https://www.reddit.com/r/stocks/comments/1vrmj5g/heres_why_openaianthropic_will_not_go_bankrupt/) | r/stocks | u/winterc1 | `t2_2jdnyiuj` | 0 | 40 | 2026-08-18 | deep analysis / mention |
| 163 | 22.6 | post | [Struggling with Qwen 3.6 27B / 35B A3B FP8 - advice apprecia](https://www.reddit.com/r/hermesagent/comments/1tzxmbk/struggling_with_qwen_36_27b_35b_a3b_fp8_advice/) | r/hermesagent | u/DonationsFirst | `t2_1gu2cotx52` | 2 | 14 | 2026-06-08 | question / mention |
| 165 | 22.6 | post | [Ox Alpha told me it was Claude. But the API envelope leaned ](https://www.reddit.com/r/openrouter/comments/1vy0lfp/ox_alpha_told_me_it_was_claude_but_the_api/) | r/openrouter | u/Neat-Ad2053 | `t2_vdu07gjg` | 13 | 13 | 2026-08-25 | deep analysis / mention |
| 166 | 22.5 | post | [Which Mac Studio for local AI?](https://www.reddit.com/r/MacStudio/comments/1w2wj1d/which_mac_studio_for_local_ai/) | r/MacStudio | u/snejink | `t2_j34f5` | 73 | 49 | 2026-08-30 | comparison / mention |
| 167 | 22.5 | post | [Update: First Manual Results from Testing Procedural Skill T](https://www.reddit.com/r/LocalLLaMA/comments/1uii78d/update_first_manual_results_from_testing/) | r/LocalLLaMA | u/ConfidentDinner6648 | `t2_1628l25l4c` | 115 | 26 | 2026-06-29 | deep analysis / mention |
| 168 | 22.5 | post | [I use a 9-agent SDD harness where each phase uses a differen](https://www.reddit.com/r/cursor/comments/1ttu5qb/i_use_a_9agent_sdd_harness_where_each_phase_uses/) | r/cursor | u/Striking-Buffalo-310 | `t2_bb2svjqd` | 36 | 61 | 2026-06-01 | workflow/setup / mention |
| 169 | 22.4 | post | [I tested multiple open models on custom agentic harness](https://www.reddit.com/r/LLMDevs/comments/1vnfvd8/i_tested_multiple_open_models_on_custom_agentic/) | r/LLMDevs | u/codes_astro | `t2_l5pkpzux7` | 1 | 2 | 2026-08-13 | benchmark / mention |
| 170 | 22.4 | post | [I tested multiple open models on custom agentic harness](https://www.reddit.com/r/aiagents/comments/1vnh0u9/i_tested_multiple_open_models_on_custom_agentic/) | r/aiagents | u/codes_astro | `t2_l5pkpzux7` | 2 | 1 | 2026-08-13 | benchmark / mention |
| 171 | 22.3 | post | [Onklaud 5 : a fusion model pipeline matching Fable 5 at 1/10](https://www.reddit.com/r/OpenSourceAI/comments/1ujr89i/onklaud_5_a_fusion_model_pipeline_matching_fable/) | r/OpenSourceAI | u/korro_ai | `t2_235biflp3f` | 29 | 4 | 2026-06-30 | usage demo / mention |
| 172 | 22.3 | post | [Onklaud 5 : a fusion model pipeline matching Fable 5 at 1/10](https://www.reddit.com/r/AIDeveloperNews/comments/1ujr7yn/onklaud_5_a_fusion_model_pipeline_matching_fable/) | r/AIDeveloperNews | u/korro_ai | `t2_235biflp3f` | 1 | 2 | 2026-06-30 | usage demo / mention |
| 173 | 22.3 | post | [trascrizione divertente di una ricerca su google fatta con g](https://www.reddit.com/r/esperimenti_con_AI/comments/1t98blg/trascrizione_divertente_di_una_ricerca_su_google/) | r/esperimenti_con_AI | u/Vast_Muscle2560 | `t2_179iy9nyo1` | 1 | 0 | 2026-05-10 | opinion / mention |
| 175 | 22.1 | post | [DeepSeek V4 Pro è ufficiale: rilasciata la build 0813, in si](https://www.reddit.com/r/vibecodingitalia/comments/1vmkq4i/deepseek_v4_pro_è_ufficiale_rilasciata_la_build/) | r/vibecodingitalia | u/thestreamcode | `t2_ivb43w3e3` | 62 | 11 | 2026-08-12 | announcement / subject |
| 176 | 22.1 | post | [Nemotron 3.5 Lightning 30B-A3B: W4A16 vs IQ4_XS on the same ](https://www.reddit.com/r/LocalLLaMA/comments/1vnu219/nemotron_35_lightning_30ba3b_w4a16_vs_iq4_xs_on/) | r/LocalLLaMA | u/mitchins-au | `t2_4hjtgq5u` | 7 | 5 | 2026-08-14 | benchmark / mention |
| 178 | 22.0 | post | [DeepSeek V4 Pro vs DeepSeek V4 Flash Has One BIG Surprise](https://www.reddit.com/r/AISEOInsider/comments/1vv8bys/deepseek_v4_pro_vs_deepseek_v4_flash_has_one_big/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-22 | promo / subject |
| 180 | 22.0 | post | [DeepSeek V4 Pro Vs Fable 5 Reveals A Wild Cache Advantage](https://www.reddit.com/r/AISEOInsider/comments/1vraoym/deepseek_v4_pro_vs_fable_5_reveals_a_wild_cache/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-18 | promo / subject |
| 181 | 22.0 | post | [DeepSeek v4 Open Source AI Looks Strong, But The Hands-On Te](https://www.reddit.com/r/AISEOInsider/comments/1su6zyd/deepseek_v4_open_source_ai_looks_strong_but_the/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 2 | 1 | 2026-04-24 | promo / mention |
| 182 | 22.0 | post | [DeepSeek v4 Has One Million Context And One Clear Catch](https://www.reddit.com/r/AISEOInsider/comments/1su6il6/deepseek_v4_has_one_million_context_and_one_clear/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 2 | 1 | 2026-04-24 | promo / mention |
| 183 | 22.0 | post | [OpenCode Go plan does NOT include the 75% discounted DeepSee](https://www.reddit.com/r/opencodeCLI/comments/1tbr2kr/opencode_go_plan_does_not_include_the_75/) | r/opencodeCLI | u/EmoLotional | `t2_etbw24zd` | 0 | 22 | 2026-05-13 | deep analysis / subject |
| 184 | 22.0 | post | [Beware of Command Code's misleading marketing](https://www.reddit.com/r/DeepSeek/comments/1viwwpx/beware_of_command_codes_misleading_marketing/) | r/DeepSeek | u/RaisinImpressive3749 | `t2_z955k7b66` | 134 | 84 | 2026-08-08 | deep analysis / subject |
| 185 | 22.0 | post | [My DeepSeek V4 Pro at home got faster again](https://www.reddit.com/r/LocalLLaMA/comments/1umdjxd/my_deepseek_v4_pro_at_home_got_faster_again/) | r/LocalLLaMA | u/fairydreaming | `t2_q06qk` | 65 | 41 | 2026-07-03 | benchmark / subject |
| 188 | 22.0 | post | [Ran the actual cost math: a year of ChatGPT Plus + Claude Pr](https://www.reddit.com/r/LocalLLM/comments/1v4lol2/ran_the_actual_cost_math_a_year_of_chatgpt_plus/) | r/LocalLLM | u/blossend | `t2_2ijrkt001m` | 0 | 11 | 2026-07-23 | deep analysis / mention |
| 190 | 22.0 | post | [DifussionGemma 4 on 4x7900xtx](https://www.reddit.com/r/LocalLLaMA/comments/1u31zmk/difussiongemma_4_on_4x7900xtx/) | r/LocalLLaMA | u/djdeniro | `t2_1epwrhsm` | 52 | 20 | 2026-06-11 | usage demo / mention |
| 191 | 22.0 | post | [Need help to validate / fix API usage costs with Claude Code](https://www.reddit.com/r/ClaudeAI/comments/1v1u4oo/need_help_to_validate_fix_api_usage_costs_with/) | r/ClaudeAI | u/S0mu | `t2_iv04t` | 1 | 5 | 2026-07-20 | question / subject |
| 192 | 21.9 | post | [Tested DeepSeek V4 as my Claude Code backend for a week — Fl](https://www.reddit.com/r/ClaudeCode/comments/1t5xm50/tested_deepseek_v4_as_my_claude_code_backend_for/) | r/ClaudeCode | u/Fresh-Resolution182 | `t2_251gat3t4d` | 7 | 15 | 2026-05-07 | workflow/setup / subject |
| 194 | 21.8 | post | [I benchmarked 9 open models on spotting fake sources during ](https://www.reddit.com/r/LocalLLM/comments/1w10wz9/i_benchmarked_9_open_models_on_spotting_fake/) | r/LocalLLM | u/RevealIndividual7567 | `t2_27ldufdnxm` | 9 | 3 | 2026-08-28 | benchmark / mention |
| 195 | 21.8 | post | [Why OpenCode Go's DeepSeek V4 Pro is ~33% cheaper than the o](https://www.reddit.com/r/opencodeCLI/comments/1tqx9u1/why_opencode_gos_deepseek_v4_pro_is_33_cheaper/) | r/opencodeCLI | u/OptionOk3805 | `t2_exg5if9lt` | 86 | 44 | 2026-05-29 | deep analysis / subject |
| 196 | 21.8 | post | [Neuralwatt - What is the most cost-effective API model that ](https://www.reddit.com/r/opencodeCLI/comments/1ubt6it/neuralwatt_what_is_the_most_costeffective_api/) | r/opencodeCLI | u/AutomaticAd6646 | `t2_94qntlf0t` | 22 | 25 | 2026-06-21 | question / subject |
| 198 | 21.8 | post | [Does anyone here have a pre-filled prompt solution loading f](https://www.reddit.com/r/LocalLLaMA/comments/1uhcf9t/does_anyone_here_have_a_prefilled_prompt_solution/) | r/LocalLLaMA | u/fragment_me | `t2_w73k33mk` | 1 | 10 | 2026-06-27 | question / mention |
| 199 | 21.8 | post | [Hermes now lets you stack frontier models into one virtual m](https://www.reddit.com/r/WebAfterAI/comments/1uh84a2/hermes_now_lets_you_stack_frontier_models_into/) | r/WebAfterAI | u/ShilpaMitra | `t2_16z9l8` | 116 | 8 | 2026-06-27 | workflow/setup / mention |
| 202 | 21.8 | post | [Gemini 3.5 Flash Lite is actually good for RP (unpopular opi](https://www.reddit.com/r/SillyTavernAI/comments/1v6a104/gemini_35_flash_lite_is_actually_good_for_rp/) | r/SillyTavernAI | u/Pirx32 | `t2_8s6f98us` | 49 | 41 | 2026-07-25 | opinion / mention |
| 203 | 21.7 | post | [Deepseek V4 Flash 0731 Just SHOCKED Everyone](https://www.reddit.com/r/AISEOInsider/comments/1vfgo7a/deepseek_v4_flash_0731_just_shocked_everyone/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-04 | promo / mention |
| 206 | 21.4 | post | [Local AI News You Missed - August 2026](https://www.reddit.com/r/StableDiffusion/comments/1w3rwoe/local_ai_news_you_missed_august_2026/) | r/StableDiffusion | u/vramkickedin | `t2_2900cnf956` | 113 | 14 | 2026-08-31 | news roundup / mention |
| 208 | 21.3 | post | [FREE DeepSeek V4 Pro Is Wild For Coding (2026)](https://www.reddit.com/r/AISEOInsider/comments/1t4avj3/free_deepseek_v4_pro_is_wild_for_coding_2026/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 1 | 2026-05-05 | promo / subject |
| 209 | 21.3 | post | [[Preset][Medium-weight?] The Ethereality Express 1.0 - A mag](https://www.reddit.com/r/SillyTavernAI/comments/1vzsvs2/presetmediumweight_the_ethereality_express_10_a/) | r/SillyTavernAI | u/purachina999 | `t2_2crihc74mm` | 58 | 6 | 2026-08-27 | workflow/setup / mention |
| 213 | 21.2 | post | [The biggest AI productivity boost I found had nothing to do ](https://www.reddit.com/r/hermesagent/comments/1u67h1c/the_biggest_ai_productivity_boost_i_found_had/) | r/hermesagent | u/Recent-Discipline253 | `t2_5c6jrv4n6` | 99 | 64 | 2026-06-15 | opinion / mention |
| 214 | 21.2 | post | [I tested multiple open models on custom agentic harness](https://www.reddit.com/r/LangChain/comments/1vnh2da/i_tested_multiple_open_models_on_custom_agentic/) | r/LangChain | u/codes_astro | `t2_l5pkpzux7` | 3 | 5 | 2026-08-13 | benchmark / mention |
| 216 | 21.1 | post | [My problems with `pi`](https://www.reddit.com/r/PiCodingAgent/comments/1usdpqw/my_problems_with_pi/) | r/PiCodingAgent | u/mira_fijamente | `t2_xolb7ml9t` | 146 | 73 | 2026-07-10 | opinion / mention |
| 220 | 21.0 | post | [DeepSeek V4 dropped April 24th and the pricing gap vs GPT-5.](https://www.reddit.com/r/AiAgentts/comments/1tf50u7/deepseek_v4_dropped_april_24th_and_the_pricing/) | r/AiAgentts | u/Ok-Drama-6800 | `t2_89kfxrpse` | 2 | 0 | 2026-05-16 | comparison / subject |
| 223 | 21.0 | post | [GLM 5.2 personal benchmark. Results comparable with Fable, O](https://www.reddit.com/r/ClaudeCode/comments/1u8k2jd/glm_52_personal_benchmark_results_comparable_with/) | r/ClaudeCode | u/lrsaturnin9 | `t2_ovny5` | 147 | 71 | 2026-06-17 | benchmark / mention |
| 224 | 21.0 | post | [OpenCode GO Opinion](https://www.reddit.com/r/opencodeCLI/comments/1uhft8c/opencode_go_opinion/) | r/opencodeCLI | u/Used-Revenue-1830 | `t2_mvc1toub3` | 86 | 51 | 2026-06-27 | workflow/setup / mention |
| 225 | 21.0 | post | [Local LLM Benchmark about Backend Generation with Function C](https://www.reddit.com/r/Qwen_AI/comments/1te1zyo/local_llm_benchmark_about_backend_generation_with/) | r/Qwen_AI | u/jhnam88 | `t2_1njlywuqe6` | 32 | 6 | 2026-05-15 | benchmark / mention |
| 226 | 21.0 | post | [Local LLM Benchmark about Backend Generation by Function Cal](https://www.reddit.com/r/LocalLLaMA/comments/1t2m7wi/local_llm_benchmark_about_backend_generation_by/) | r/LocalLLaMA | u/jhnam88 | `t2_1njlywuqe6` | 23 | 7 | 2026-05-03 | benchmark / mention |
| 227 | 21.0 | post | [Local LLM Benchmark about Backend Generation with Function C](https://www.reddit.com/r/LocalLLM/comments/1t2n1x1/local_llm_benchmark_about_backend_generation_with/) | r/LocalLLM | u/jhnam88 | `t2_1njlywuqe6` | 7 | 4 | 2026-05-03 | benchmark / mention |
| 228 | 21.0 | post | [Local LLM Benchmark about Backend Generation with Function C](https://www.reddit.com/r/DeepSeek/comments/1te218a/local_llm_benchmark_about_backend_generation_with/) | r/DeepSeek | u/jhnam88 | `t2_1njlywuqe6` | 4 | 1 | 2026-05-15 | benchmark / mention |
| 233 | 20.8 | post | [Agent OS Guide Builds And Automates Anything With Claude](https://www.reddit.com/r/AISEOInsider/comments/1vzj3q3/agent_os_guide_builds_and_automates_anything_with/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-27 | promo / mention |
| 234 | 20.8 | post | [Test of prices of DeepSeek in OpenCode Go and API in deepsee](https://www.reddit.com/r/opencodeCLI/comments/1tril88/test_of_prices_of_deepseek_in_opencode_go_and_api/) | r/opencodeCLI | u/CriteriumA | `t2_2d82q2o51k` | 74 | 39 | 2026-05-29 | deep analysis / subject |
| 235 | 20.8 | post | [Spending $2.5k/month on Sonnet/Opus — worth switching more t](https://www.reddit.com/r/openclaw/comments/1tjhcly/spending_25kmonth_on_sonnetopus_worth_switching/) | r/openclaw | u/Apacalipto | `t2_vkjp15f` | 33 | 59 | 2026-05-21 | question / mention |
| 238 | 20.6 | post | [[PRESET] DEUS EX MACHINA V2: Goodbye Thinking, Hello Scene P](https://www.reddit.com/r/SillyTavernAI/comments/1w10cl5/preset_deus_ex_machina_v2_goodbye_thinking_hello/) | r/SillyTavernAI | u/lsennn | `t2_ro4e03e` | 193 | 84 | 2026-08-28 | workflow/setup / mention |
| 241 | 20.5 | post | [Agent OS Workflow Builds Custom AI Skills Fast](https://www.reddit.com/r/AISEOInsider/comments/1vpquid/agent_os_workflow_builds_custom_ai_skills_fast/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-16 | promo / mention |
| 244 | 20.4 | post | [Meta‑Analysis Showdown: DeepSeek V4 Pro 0813 vs DeepSeek V4 ](https://www.reddit.com/r/opencode/comments/1vmowk1/metaanalysis_showdown_deepseek_v4_pro_0813_vs/) | r/opencode | u/TheDeepArchive | `t2_2fcgiubuva` | 35 | 9 | 2026-08-12 | comparison / subject |
| 245 | 20.4 | post | [Benchmarks don't mean anything anymore.](https://www.reddit.com/r/LocalLLaMA/comments/1vr0v0d/benchmarks_dont_mean_anything_anymore/) | r/LocalLLaMA | u/Nerfariox | `t2_1fizjcg7ai` | 0 | 58 | 2026-08-17 | opinion / mention |
| 250 | 20.4 | post | [I've been running on both DeepSeek V4 and Opus 4.7 as my "br](https://www.reddit.com/r/lingheng_agent/comments/1t9umht/ive_been_running_on_both_deepseek_v4_and_opus_47/) | r/lingheng_agent | u/No-Profession-1306 | `t2_2a603hbmdz` | 1 | 0 | 2026-05-11 | opinion / subject |
| 251 | 20.4 | post | [PlotPoints - The best (only?) community driven RP benchmark ](https://www.reddit.com/r/SillyTavernAI/comments/1twf5ew/plotpoints_the_best_only_community_driven_rp/) | r/SillyTavernAI | u/Specialist_Salad6337 | `t2_1yugvs0qou` | 120 | 69 | 2026-06-04 | announcement / mention |
| 255 | 20.0 | post | [I repriced my real Claude Code Max 20x usage against DeepSee](https://www.reddit.com/r/DeepSeek/comments/1vtv0jz/i_repriced_my_real_claude_code_max_20x_usage/) | r/DeepSeek | u/Maamriya | `t2_30unn8r8` | 74 | 86 | 2026-08-20 | deep analysis / subject |
| 258 | 20.0 | post | [Mimo V2.5/Pro 57% to 99% price drop, matching DeepSeek v4 pr](https://www.reddit.com/r/GithubCopilot/comments/1tpxccf/mimo_v25pro_57_to_99_price_drop_matching_deepseek/) | r/GithubCopilot | u/ProfessionalJackals | `t2_1lqtnyul8t` | 78 | 26 | 2026-05-28 | announcement / mention |
| 261 | 20.0 | post | [Freebuff: una CLI gratuita per usare agenti AI di coding, fi](https://www.reddit.com/r/vibecodingitalia/comments/1trj6ow/freebuff_una_cli_gratuita_per_usare_agenti_ai_di/) | r/vibecodingitalia | u/thestreamcode | `t2_ivb43w3e3` | 1 | 2 | 2026-05-29 | announcement / mention |
| 262 | 20.0 | post | [New Hermes Agent V0.13.0 Is SHOCKING (864 Commits In One Wee](https://www.reddit.com/r/AISEOInsider/comments/1t7nz97/new_hermes_agent_v0130_is_shocking_864_commits_in/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-05-08 | promo / mention |
| 264 | 19.9 | post | [DeepSeek AI Tutorial Shows The V4 Free Agent Stack](https://www.reddit.com/r/AISEOInsider/comments/1w1ssc0/deepseek_ai_tutorial_shows_the_v4_free_agent_stack/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-29 | promo / mention |
| 271 | 19.7 | post | [Cloud Models &amp; Providers for Hermes Agent — The August 2](https://www.reddit.com/r/hermesagent/comments/1vvv2x1/cloud_models_providers_for_hermes_agent_the/) | r/hermesagent | u/Jonathan_Rivera | `t2_3c1k03sn` | 67 | 13 | 2026-08-23 | news roundup / mention |
| 272 | 19.7 | post | [CrofAI - Affordable multi-model AI access with cheap options](https://www.reddit.com/r/CrofAI/comments/1sc3nsw/crofai_affordable_multimodel_ai_access_with_cheap/) | r/CrofAI | u/smoking_juuls420 | `t2_2blb0sc8q2` | 14 | 38 | 2026-04-04 | promo / mention |
| 273 | 19.6 | post | [Deepseek v4 Flash 0731 through OpenCode in Codex?](https://www.reddit.com/r/opencode/comments/1vcg0kg/deepseek_v4_flash_0731_through_opencode_in_codex/) | r/opencode | u/Odd_Donkey2691 | `t2_a5v27cv5` | 54 | 10 | 2026-08-01 | tutorial / subject |
| 275 | 19.6 | post | [MVU Game Maker v0.95 – Slice of Life/Dating sim with Persist](https://www.reddit.com/r/SillyTavernAI/comments/1svavzk/mvu_game_maker_v095_slice_of_lifedating_sim_with/) | r/SillyTavernAI | u/Kritblade | `t2_26vx3o9b8h` | 310 | 158 | 2026-04-25 | workflow/setup / mention |
| 276 | 19.6 | post | [Claude Code criollo: Cómo programo con IA sin depender de su](https://www.reddit.com/r/dev_venezuela/comments/1u6jgal/claude_code_criollo_cómo_programo_con_ia_sin/) | r/dev_venezuela | u/FranciscoLuna20 | `t2_su7zjz4r` | 79 | 32 | 2026-06-15 | workflow/setup / mention |
| 278 | 19.5 | post | [Openrouter Cheap prices and expensive costs](https://www.reddit.com/r/openrouter/comments/1uxi3av/openrouter_cheap_prices_and_expensive_costs/) | r/openrouter | u/econi10 | `t2_2cf7n2ku` | 24 | 21 | 2026-07-15 | question / subject |
| 279 | 19.4 | post | [DeepSeek V4 Pro Release Hits 1M Context And Huge Agent Gains](https://www.reddit.com/r/AISEOInsider/comments/1vsil60/deepseek_v4_pro_release_hits_1m_context_and_huge/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-19 | promo / subject |
| 280 | 19.4 | post | [Why is Opencode pricing for DeepSeek V4 Pro is 4x market rat](https://www.reddit.com/r/opencodeCLI/comments/1uo0nxj/why_is_opencode_pricing_for_deepseek_v4_pro_is_4x/) | r/opencodeCLI | u/eyueldk | `t2_25k5fn1j` | 83 | 36 | 2026-07-05 | *not read* |
| 282 | 19.4 | post | [I swapped my Hermes fleet from Mnemosyne to Hy-Memory. The i](https://www.reddit.com/r/hermesagent/comments/1vmgw4l/i_swapped_my_hermes_fleet_from_mnemosyne_to/) | r/hermesagent | u/Countlesshrs | `t2_mwvuh` | 48 | 33 | 2026-08-12 | *not read* |
| 283 | 19.4 | post | [Help me understand how Nvidia is not overvalued. (Bear Thesi](https://www.reddit.com/r/ValueInvesting/comments/1t7t2yv/help_me_understand_how_nvidia_is_not_overvalued/) | r/ValueInvesting | u/ContentInflation4981 | `t2_olnkp85r4` | 2 | 77 | 2026-05-09 | *not read* |
| 286 | 19.3 | post | [Agent Swarm is painfully slow - ideas?](https://www.reddit.com/r/opencode/comments/1tn51l0/agent_swarm_is_painfully_slow_ideas/) | r/opencode | u/DarkJoney | `t2_kmkq7` | 1 | 13 | 2026-05-25 | *not read* |
| 287 | 19.3 | post | [The good point of DeepSeek models has nothing to do with usi](https://www.reddit.com/r/DeepSeek/comments/1v6a98q/the_good_point_of_deepseek_models_has_nothing_to/) | r/DeepSeek | u/Anxious_Check_6147 | `t2_mea8xoc2z` | 0 | 12 | 2026-07-25 | *not read* |
| 288 | 19.2 | post | [I built a pi custom provider for Command Code / Deepseek for](https://www.reddit.com/r/PiCodingAgent/comments/1t4faft/i_built_a_pi_custom_provider_for_command_code/) | r/PiCodingAgent | u/patlux | `t2_jbrj7` | 15 | 14 | 2026-05-05 | *not read* |
| 295 | 19.0 | post | [Noticeable lower reasoning with Command Code Goat](https://www.reddit.com/r/CommandCode/comments/1w36nq3/noticeable_lower_reasoning_with_command_code_goat/) | r/CommandCode | u/nothosoo | `t2_31owxmo1` | 13 | 1 | 2026-08-31 | *not read* |
| 296 | 19.0 | post | [DeepSeek V4 Flash (0731) vs DeepSeek V4 Pro (0813), part 2: ](https://www.reddit.com/r/LLMDevs/comments/1vnhxr0/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813/) | r/LLMDevs | u/TheDeepArchive | `t2_2fcgiubuva` | 8 | 3 | 2026-08-13 | *not read* |
| 297 | 19.0 | post | [DeepSeek V4 Flash (0731) vs DeepSeek V4 Pro (0813), part 2: ](https://www.reddit.com/r/DeepSeek/comments/1vnhvka/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813/) | r/DeepSeek | u/TheDeepArchive | `t2_2fcgiubuva` | 11 | 2 | 2026-08-13 | *not read* |
| 298 | 19.0 | post | [DeepSeek V4 Flash (0731) vs DeepSeek V4 Pro (0813), part 2: ](https://www.reddit.com/r/opencode/comments/1vnhrgw/deepseek_v4_flash_0731_vs_deepseek_v4_pro_0813/) | r/opencode | u/TheDeepArchive | `t2_2fcgiubuva` | 20 | 0 | 2026-08-13 | *not read* |
| 301 | 19.0 | post | [DeepSeek V4 Pro vs GPT-5.5 for building simple Game](https://www.reddit.com/r/DeepSeek/comments/1svnjns/deepseek_v4_pro_vs_gpt55_for_building_simple_game/) | r/DeepSeek | u/gladkos | `t2_11akqo` | 158 | 32 | 2026-04-25 | *not read* |
| 302 | 19.0 | post | [minimax token plan - stater 10$ - review - heavily disappoin](https://www.reddit.com/r/MiniMax_AI/comments/1sp4v1z/minimax_token_plan_stater_10_review_heavily/) | r/MiniMax_AI | u/Decent-Rain5100 | `t2_1zrwroipfi` | 7 | 48 | 2026-04-18 | *not read* |
| 304 | 19.0 | post | [I switched from Anthropic's $200/mo Claude Max to Ollama Clo](https://www.reddit.com/r/PractialAIDev/comments/1szggsa/i_switched_from_anthropics_200mo_claude_max_to/) | r/PractialAIDev | u/Aromatic_Pumpkin8856 | `t2_21n6jmim96` | 9 | 12 | 2026-04-30 | *not read* |
| 305 | 19.0 | post | [A week inside the book machine: model bakeoffs, two features](https://www.reddit.com/r/VibeAuthoring/comments/1voq0vi/a_week_inside_the_book_machine_model_bakeoffs_two/) | r/VibeAuthoring | u/gratajik | `t2_40k4m` | 7 | 10 | 2026-08-15 | *not read* |
| 306 | 19.0 | post | [GLM 5.2 personal benchmark. Results comparable with Fable, O](https://www.reddit.com/r/codex/comments/1u8k5em/glm_52_personal_benchmark_results_comparable_with/) | r/codex | u/lrsaturnin9 | `t2_ovny5` | 13 | 19 | 2026-06-17 | *not read* |
| 307 | 19.0 | post | [GLM 5.2 personal benchmark. Results comparable with Fable, O](https://www.reddit.com/r/LLMDevs/comments/1u8k49z/glm_52_personal_benchmark_results_comparable_with/) | r/LLMDevs | u/lrsaturnin9 | `t2_ovny5` | 28 | 17 | 2026-06-17 | *not read* |
| 308 | 19.0 | post | [Estimating DeepSeek V4 Pro API cost from real Codex Plus usa](https://www.reddit.com/r/DeepSeek/comments/1tzomkq/estimating_deepseek_v4_pro_api_cost_from_real/) | r/DeepSeek | u/Sea_Light7555 | `t2_ublhejv0` | 1 | 15 | 2026-06-07 | *not read* |
| 309 | 19.0 | post | [Novetats IA i tech de la setmana (04/05/2026)](https://www.reddit.com/r/ordinadors/comments/1t38zpk/novetats_ia_i_tech_de_la_setmana_04052026/) | r/ordinadors | u/KitKatKut-0_0 | `t2_a1v3rviq` | 9 | 0 | 2026-05-04 | *not read* |
| 310 | 19.0 | post | [Here are the Best AI to write *coherent* Erotica (tested and](https://www.reddit.com/r/ClaudeAIJailbreak/comments/1u0vl5e/here_are_the_best_ai_to_write_coherent_erotica/) | r/ClaudeAIJailbreak | u/Solidified4ever | `t2_502pqejz` | 105 | 75 | 2026-06-09 | *not read* |
| 314 | 18.8 | post | [Claude + Codex + Opencode = God Mode](https://www.reddit.com/r/ClaudeCode/comments/1sxs8c0/claude_codex_opencode_god_mode/) | r/ClaudeCode | u/99xAgency | `t2_kbe8fp82y` | 387 | 130 | 2026-04-28 | *not read* |
| 317 | 18.7 | post | [Switched my Claude Code agent loop to DeepSeek V4 Pro via th](https://www.reddit.com/r/LocalLLM/comments/1t3oypq/switched_my_claude_code_agent_loop_to_deepseek_v4/) | r/LocalLLM | u/Acceptable_Gap9697 | `t2_2d01fcx832` | 4 | 20 | 2026-05-04 | *not read* |
| 318 | 18.7 | post | [اخيرا لقيتكم](https://www.reddit.com/r/Saudi_Homelab/comments/1tvzn24/اخيرا_لقيتكم/) | r/Saudi_Homelab | u/kwmx | `t2_lgpm9` | 54 | 20 | 2026-06-03 | *not read* |
| 322 | 18.6 | post | [A collection of small domain-specific benchmarks for local m](https://www.reddit.com/r/LocalLLaMA/comments/1vcz4b4/a_collection_of_small_domainspecific_benchmarks/) | r/LocalLLaMA | u/EmilPi | `t2_jti45lwl` | 18 | 18 | 2026-08-01 | *not read* |
| 323 | 18.6 | post | [GLM-5.3 is the same 743B base as 5.2, re-post-trained for co](https://www.reddit.com/r/chutesAI/comments/1vo6wrp/glm53_is_the_same_743b_base_as_52_reposttrained/) | r/chutesAI | u/thestreamcode | `t2_ivb43w3e3` | 13 | 1 | 2026-08-14 | *not read* |
| 324 | 18.6 | post | [MVU Game Maker on Deepseek v4 pro preset solution](https://www.reddit.com/r/SillyTavernAI/comments/1t1t65d/mvu_game_maker_on_deepseek_v4_pro_preset_solution/) | r/SillyTavernAI | u/Kritblade | `t2_26vx3o9b8h` | 27 | 4 | 2026-05-02 | *not read* |
| 327 | 18.3 | post | [DeepSeek V4 Pro scored 89.1 at $0.0017/call in our 17-model,](https://www.reddit.com/r/DeepSeek/comments/1v2mvv4/deepseek_v4_pro_scored_891_at_00017call_in_our/) | r/DeepSeek | u/petburiraja | `t2_60jo8coj` | 108 | 18 | 2026-07-21 | *not read* |
| 328 | 18.3 | post | [How we got 99.6% cache hit rate on DeepSeek V4 Pro for a lon](https://www.reddit.com/r/DeepSeek/comments/1uwxvnd/how_we_got_996_cache_hit_rate_on_deepseek_v4_pro/) | r/DeepSeek | u/huiliyi37 | `t2_2gj0v2i8tt` | 16 | 3 | 2026-07-15 | *not read* |
| 330 | 18.2 | post | [[PRESET] DEUS EX MACHINA V1: A feature-rich, beginner-friend](https://www.reddit.com/r/SillyTavernAI/comments/1vcr9d8/preset_deus_ex_machina_v1_a_featurerich/) | r/SillyTavernAI | u/lsennn | `t2_ro4e03e` | 170 | 53 | 2026-08-01 | *not read* |
| 333 | 18.1 | post | [DeepSeek officially launches V4-Pro 87.9 on Terminal Bench 2](https://www.reddit.com/r/AIGuild/comments/1vns8qu/deepseek_officially_launches_v4pro_879_on/) | r/AIGuild | u/Such-Run-4412 | `t2_qdhmdvza` | 1 | 1 | 2026-08-14 | *not read* |
| 334 | 18.1 | post | [If you pay for OpenCode Go, 12 of 15 models break on follow-](https://www.reddit.com/r/opencodeCLI/comments/1uco67e/if_you_pay_for_opencode_go_12_of_15_models_break/) | r/opencodeCLI | u/deafpigeon39 | `t2_2t80ou2t` | 48 | 56 | 2026-06-22 | *not read* |
| 339 | 18.0 | post | [Salio Deepseek V4, bueno mas o menos. Lo que si, es muchísim](https://www.reddit.com/r/IASinHumo/comments/1suy3ko/salio_deepseek_v4_bueno_mas_o_menos_lo_que_si_es/) | r/IASinHumo | u/Rare_Package_7498 | `t2_kzpnucw1` | 23 | 5 | 2026-04-25 | *not read* |
| 342 | 18.0 | post | [DeepClaude: full Claude Code agent loop on DeepSeek V4 Pro -](https://www.reddit.com/r/ClaudeCode/comments/1t3hrcx/deepclaude_full_claude_code_agent_loop_on/) | r/ClaudeCode | u/jimmytoan | `t2_1x2u1ycc` | 100 | 49 | 2026-05-04 | *not read* |
| 343 | 17.9 | post | [DeepSeek V4 Pro 0813 is out](https://www.reddit.com/r/hermesagent/comments/1vmj9zw/deepseek_v4_pro_0813_is_out/) | r/hermesagent | u/TemeT__ | `t2_21ojvkt1la` | 124 | 39 | 2026-08-12 | *not read* |
| 355 | 17.7 | post | [my honest comparison of gpt 5.6 vs glm 5.2 vs deepseek v4 pr](https://www.reddit.com/r/ChatGPT/comments/1vrmdrg/my_honest_comparison_of_gpt_56_vs_glm_52_vs/) | r/ChatGPT | u/iamsatvik20 | `t2_2ixw2ov129` | 5 | 22 | 2026-08-18 | *not read* |
| 358 | 17.6 | post | [I fine-tuned Qwen3.5-4B on ~3k browser trajectories and impr](https://www.reddit.com/r/Qwen_AI/comments/1w0onrx/i_finetuned_qwen354b_on_3k_browser_trajectories/) | r/Qwen_AI | u/dnx2200 | `t2_4me1uyf` | 17 | 0 | 2026-08-28 | *not read* |
| 359 | 17.6 | post | [I fine-tuned Qwen3.5-4B on ~3k browser trajectories and impr](https://www.reddit.com/r/OpenSourceAI/comments/1w0omj3/i_finetuned_qwen354b_on_3k_browser_trajectories/) | r/OpenSourceAI | u/dnx2200 | `t2_4me1uyf` | 3 | 0 | 2026-08-28 | *not read* |
| 360 | 17.6 | post | [I fine-tuned Qwen3.5-4B on ~3k browser trajectories and impr](https://www.reddit.com/r/ollama/comments/1w0ok3g/i_finetuned_qwen354b_on_3k_browser_trajectories/) | r/ollama | u/dnx2200 | `t2_4me1uyf` | 10 | 5 | 2026-08-28 | *not read* |
| 362 | 17.6 | post | [Best bang for the buck for daily use and various tasks? I've](https://www.reddit.com/r/hermesagent/comments/1tn2ae0/best_bang_for_the_buck_for_daily_use_and_various/) | r/hermesagent | u/mantastamosaitis | `t2_61dt2p3h` | 12 | 44 | 2026-05-25 | *not read* |
| 363 | 17.6 | post | [Half the "best local model" advice you'll read this week is ](https://www.reddit.com/r/LocalLLM/comments/1vazx78/half_the_best_local_model_advice_youll_read_this/) | r/LocalLLM | u/blossend | `t2_2ijrkt001m` | 0 | 13 | 2026-07-30 | *not read* |
| 365 | 17.5 | post | [thoughts on token price](https://www.reddit.com/r/WSBAfterHours/comments/1w0zsxd/thoughts_on_token_price/) | r/WSBAfterHours | u/Mission_Feed_8824 | `t2_2gm767gpba` | 2 | 0 | 2026-08-28 | *not read* |
| 368 | 17.4 | post | [DeepSeek V4 for GitHub Copilot — Setup Guide](https://www.reddit.com/r/GithubCopilot/comments/1tzx9ke/deepseek_v4_for_github_copilot_setup_guide/) | r/GithubCopilot | u/gdias92 | `t2_qwvi243` | 199 | 51 | 2026-06-08 | *not read* |
| 369 | 17.4 | post | [I gave 7 LLMs the same technical analysis task](https://www.reddit.com/r/DeepSeek/comments/1vozfqp/i_gave_7_llms_the_same_technical_analysis_task/) | r/DeepSeek | u/DirectPitch8626 | `t2_7eqq4iag` | 3 | 4 | 2026-08-15 | *not read* |
| 370 | 17.4 | post | [Presenting: RoleCall Studios \| Trailblazing Features \| Fre](https://www.reddit.com/r/JanitorAI_Refuges/comments/1tdi5g8/presenting_rolecall_studios_trailblazing_features/) | r/JanitorAI_Refuges | u/matt_is_a_mess | `t2_2bapnwywk2` | 0 | 5 | 2026-05-15 | *not read* |
| 371 | 17.3 | post | [We're running a race where 7 AI agents build startups with $](https://www.reddit.com/r/DeepSeek/comments/1subqy5/were_running_a_race_where_7_ai_agents_build/) | r/DeepSeek | u/jochenboele | `t2_f0ifh5p` | 19 | 8 | 2026-04-24 | *not read* |
| 376 | 17.0 | post | [[r/ClaudeAI] I had to pay $16 for Fable to tell Opus 5 to st](https://www.reddit.com/r/Claude_reports/comments/1vq4unl/rclaudeai_i_had_to_pay_16_for_fable_to_tell_opus/) | r/Claude_reports | u/ClaudeAI-mod-bot | `t2_1vs6v2gkb0` | 1 | 0 | 2026-08-16 | *not read* |
| 378 | 17.0 | post | [Tested 50 Coding Models on the Same Task with OpenCode and C](https://www.reddit.com/r/opencode/comments/1vqaw2f/tested_50_coding_models_on_the_same_task_with/) | r/opencode | u/Aggravating_Debt1278 | `t2_p4film14` | 13 | 14 | 2026-08-16 | *not read* |
| 380 | 16.9 | post | [Tested DeepSeek V4 Pro 0813, Kimi K3, and GLM 5.2 through Fl](https://www.reddit.com/r/CommandCode/comments/1vmp6xa/tested_deepseek_v4_pro_0813_kimi_k3_and_glm_52/) | r/CommandCode | u/maedahbatool | `t2_s3g4io7` | 40 | 7 | 2026-08-12 | *not read* |
| 384 | 16.9 | post | [Huko-Engine: an out-of-the-box agent engine — give your Node](https://www.reddit.com/r/node/comments/1tovz6i/hukoengine_an_outofthebox_agent_engine_give_your/) | r/node | u/CatTwoYes | `t2_14rpfy7ep9` | 0 | 4 | 2026-05-27 | *not read* |
| 387 | 16.8 | post | [Benchmarking Mimo 2.5 and DeepSeek V4 on a 3D Web Demo](https://www.reddit.com/r/DeepSeek/comments/1tp61fl/benchmarking_mimo_25_and_deepseek_v4_on_a_3d_web/) | r/DeepSeek | u/vnenov | `t2_11h1g2` | 99 | 17 | 2026-05-27 | *not read* |
| 389 | 16.8 | post | [I compiled LLM inference pricing across 7 providers — the ca](https://www.reddit.com/r/MachineLearning/comments/1ueavxn/i_compiled_llm_inference_pricing_across_7/) | r/MachineLearning | u/Technomadlyf | `t2_g871wqu4` | 2 | 2 | 2026-06-24 | *not read* |
| 391 | 16.8 | post | [DeepSeek V4 is Better, Cheaper Than V3.2](https://www.reddit.com/r/DeepSeek/comments/1tnxwnd/deepseek_v4_is_better_cheaper_than_v32/) | r/DeepSeek | u/Aromatic-Document638 | `t2_ob09qxx3` | 14 | 11 | 2026-05-26 | *not read* |
| 392 | 16.8 | post | [Claude + Codex + Opencode = God Mode](https://www.reddit.com/r/opencodeCLI/comments/1sxs7az/claude_codex_opencode_god_mode/) | r/opencodeCLI | u/99xAgency | `t2_kbe8fp82y` | 44 | 18 | 2026-04-28 | *not read* |
| 394 | 16.7 | post | [Qwen3.8 27B at $3.20/M output - worth it over Gemini 3.7 Fla](https://www.reddit.com/r/AIToolsPerformance/comments/1vr0t9w/qwen38_27b_at_320m_output_worth_it_over_gemini_37/) | r/AIToolsPerformance | u/IulianHI | `t2_10nqfcv1` | 5 | 15 | 2026-08-17 | *not read* |
| 396 | 16.7 | post | [my honest comparison of gpt 5.6 vs glm 5.2 vs deepseek v4 pr](https://www.reddit.com/r/LLMDevs/comments/1vrmsch/my_honest_comparison_of_gpt_56_vs_glm_52_vs/) | r/LLMDevs | u/iamsatvik20 | `t2_2ixw2ov129` | 0 | 4 | 2026-08-18 | *not read* |
| 397 | 16.7 | post | [Choosing the Best LLM for Hermes Agent](https://www.reddit.com/r/hermesagent/comments/1tvjjor/choosing_the_best_llm_for_hermes_agent/) | r/hermesagent | u/blu3sh4rk | `t2_t6wwidm` | 195 | 97 | 2026-06-03 | *not read* |
| 398 | 16.7 | post | [Access 60+ Chinese AI models from any OpenAI-compatible clie](https://www.reddit.com/r/huggingface/comments/1ux28do/access_60_chinese_ai_models_from_any/) | r/huggingface | u/Local_Drama_7489 | `t2_2gqvfyn2o0` | 0 | 0 | 2026-07-15 | *not read* |
| 399 | 16.6 | post | [DeepSeek V4 just made a million tokens cost $2.50 and the cl](https://www.reddit.com/r/aigossips/comments/1syxyqt/deepseek_v4_just_made_a_million_tokens_cost_250/) | r/aigossips | u/call_me_ninza | `t2_dbbedhcv` | 328 | 75 | 2026-04-29 | *not read* |
| 401 | 16.6 | post | [DeepSeek V4 Pricing: The Simple Way To Spend Less On AI](https://www.reddit.com/r/AISEOInsider/comments/1swev6c/deepseek_v4_pricing_the_simple_way_to_spend_less/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-04-26 | *not read* |
| 404 | 16.6 | post | [Discussing prompting techniques - July](https://www.reddit.com/r/SillyTavernAI/comments/1uxp072/discussing_prompting_techniques_july/) | r/SillyTavernAI | u/Kahvana | `t2_13hq2c` | 85 | 33 | 2026-07-16 | *not read* |
| 407 | 16.5 | post | [The Cron Schedule Is Now a Budget Line Item. DeepSeek's V4 A](https://www.reddit.com/r/Tidra/comments/1vo807m/the_cron_schedule_is_now_a_budget_line_item/) | r/Tidra | u/Ok_Result_8394 | `t2_2d8ltzau0c` | 7 | 0 | 2026-08-14 | *not read* |
| 408 | 16.5 | post | [DeepSeek V4 Official Launch + Peak/Off-Peak Pricing — Mid-Ju](https://www.reddit.com/r/DeepSeek/comments/1uio6yf/deepseek_v4_official_launch_peakoffpeak_pricing/) | r/DeepSeek | u/Quiet-Yam1116 | `t2_k5uzs4mrv` | 138 | 62 | 2026-06-29 | *not read* |
| 409 | 16.5 | post | [Grove API for massive compute on coding plans. Banked usage ](https://www.reddit.com/r/ZaiGLM/comments/1vbu7f1/grove_api_for_massive_compute_on_coding_plans/) | r/ZaiGLM | u/Whole_Succotash_2391 | `t2_1suofmpw53` | 0 | 9 | 2026-07-31 | *not read* |
| 410 | 16.5 | post | [A coding plan with usage banking for Qwen 3.8, Kimi, and Dee](https://www.reddit.com/r/opencode/comments/1vszf5z/a_coding_plan_with_usage_banking_for_qwen_38_kimi/) | r/opencode | u/Whole_Succotash_2391 | `t2_1suofmpw53` | 3 | 11 | 2026-08-19 | *not read* |
| 411 | 16.5 | post | [For whom wanted to work with deepseek in VSC Copilot Chat](https://www.reddit.com/r/DeepSeek/comments/1vo2lgx/for_whom_wanted_to_work_with_deepseek_in_vsc/) | r/DeepSeek | u/CatLinkoln | `t2_3g34t6cx` | 1 | 1 | 2026-08-14 | *not read* |
| 412 | 16.4 | post | [New DeepSeek Release Has 3 Big Catches You Need To Know](https://www.reddit.com/r/AISEOInsider/comments/1vqueav/new_deepseek_release_has_3_big_catches_you_need/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-17 | *not read* |
| 413 | 16.4 | post | [Hermes Agent New AI Model Makes Multi-Agent Tasks Faster](https://www.reddit.com/r/AISEOInsider/comments/1ticvg4/hermes_agent_new_ai_model_makes_multiagent_tasks/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-05-20 | *not read* |
| 420 | 16.1 | post | [Down the rabbit hole of DeepSeek-V4-Pro-0813](https://www.reddit.com/r/DeepSeek/comments/1votndx/down_the_rabbit_hole_of_deepseekv4pro0813/) | r/DeepSeek | u/HeavyPanzerPlus1s | `t2_120i7p` | 157 | 21 | 2026-08-15 | *not read* |
| 421 | 16.1 | post | [DeepSeek just confirmed that their 75% promo discount for th](https://www.reddit.com/r/ArtificialInteligence/comments/1tlgw8d/deepseek_just_confirmed_that_their_75_promo/) | r/ArtificialInteligence | u/andrewaltair | `t2_1eat1nsjik` | 46 | 15 | 2026-05-23 | *not read* |
| 422 | 16.1 | post | [DeepSeek v4 al momento costa fino al 98% in meno rispetto ai](https://www.reddit.com/r/IA_Italia/comments/1sv8tn4/deepseek_v4_al_momento_costa_fino_al_98_in_meno/) | r/IA_Italia | u/gdorsi44 | `t2_5ok4rrwc` | 12 | 5 | 2026-04-25 | *not read* |
| 425 | 16.1 | post | [Poolside Laguna S 2.1 is worse than Qwen 3.6 27B and Gemma4 ](https://www.reddit.com/r/LocalLLM/comments/1v4ylim/poolside_laguna_s_21_is_worse_than_qwen_36_27b/) | r/LocalLLM | u/sinmkd | `t2_qp4ye4f` | 104 | 82 | 2026-07-24 | *not read* |
| 426 | 16.0 | post | [OpenCode agent prompts for DeepSeek V4: a "critical technica](https://www.reddit.com/r/opencodeCLI/comments/1u1d3op/opencode_agent_prompts_for_deepseek_v4_a_critical/) | r/opencodeCLI | u/CriteriumA | `t2_2d82q2o51k` | 27 | 6 | 2026-06-09 | *not read* |
| 427 | 16.0 | post | [DeepSeek V4 RP Guide — How to Switch Between Character Immer](https://www.reddit.com/r/SillyTavernAI/comments/1su8x8p/deepseek_v4_rp_guide_how_to_switch_between/) | r/SillyTavernAI | u/Professional_Pie5257 | `t2_eo7fpwe6` | 204 | 18 | 2026-04-24 | *not read* |
| 428 | 16.0 | post | [DeepSeek New Update Just Changed AI Speed Forever](https://www.reddit.com/r/AISEOInsider/comments/1ulmuxz/deepseek_new_update_just_changed_ai_speed_forever/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-07-02 | *not read* |
| 429 | 16.0 | post | [I Used Deepseek V4 And OpenCode And It Shocked Me](https://www.reddit.com/r/AISEOInsider/comments/1t3m4jz/i_used_deepseek_v4_and_opencode_and_it_shocked_me/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-05-04 | *not read* |
| 430 | 16.0 | post | [Is it just me or is Hermes terribly inefficent when it comes](https://www.reddit.com/r/hermesagent/comments/1u08ec6/is_it_just_me_or_is_hermes_terribly_inefficent/) | r/hermesagent | u/asganawayaway | `t2_11fm26nk8x` | 15 | 64 | 2026-06-08 | *not read* |
| 432 | 16.0 | post | [DeepSeek updated V4 Pro](https://www.reddit.com/r/rpgc_official/comments/1vndbn6/deepseek_updated_v4_pro/) | r/rpgc_official | u/RIPT1D3_Z | `t2_1zyh18yq` | 1 | 0 | 2026-08-13 | *not read* |
| 436 | 15.8 | post | [Staying on Copilot for now - but using DeepSeek as well](https://www.reddit.com/r/GithubCopilot/comments/1twkr3w/staying_on_copilot_for_now_but_using_deepseek_as/) | r/GithubCopilot | u/Quango2009 | `t2_d7f16` | 4 | 4 | 2026-06-04 | *not read* |
| 437 | 15.8 | post | [DeepSeek V4 Pro costs $0.87 per million output tokens. GPT-5](https://www.reddit.com/r/CreatorsAI/comments/1tv42pp/deepseek_v4_pro_costs_087_per_million_output/) | r/CreatorsAI | u/Historical-Driver-64 | `t2_7f5ck41k` | 1 | 0 | 2026-06-02 | *not read* |
| 439 | 15.8 | post | [New model just dropped. Your self-hosted setup can't run it ](https://www.reddit.com/r/better_claw/comments/1ttkrt0/new_model_just_dropped_your_selfhosted_setup_cant/) | r/better_claw | u/ShabzSparq | `t2_p03gzhzq` | 0 | 11 | 2026-06-01 | *not read* |
| 443 | 15.8 | post | [CAISI Evaluation of DeepSeek V4 Pro finds it to be on par wi](https://www.reddit.com/r/accelerate/comments/1t1eg26/caisi_evaluation_of_deepseek_v4_pro_finds_it_to/) | r/accelerate | u/obvithrowaway34434 | `t2_a779auxs` | 60 | 16 | 2026-05-02 | *not read* |
| 445 | 15.7 | post | [DeepSeek V4 Flash And Pro: I Tested Both And The Difference ](https://www.reddit.com/r/AISEOInsider/comments/1sysezt/deepseek_v4_flash_and_pro_i_tested_both_and_the/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-04-29 | *not read* |
| 446 | 15.7 | post | [A Comparison between DeepSeek V4 Pro and MiniMax M3](https://www.reddit.com/r/DeepSeek/comments/1u5mips/a_comparison_between_deepseek_v4_pro_and_minimax/) | r/DeepSeek | u/Aromatic-Document638 | `t2_ob09qxx3` | 23 | 24 | 2026-06-14 | *not read* |
| 449 | 15.7 | post | [Which open model to use for what: DeepSeek V4, GLM-5.1, Qwen](https://www.reddit.com/r/openadapter_/comments/1vl8ji8/which_open_model_to_use_for_what_deepseek_v4/) | r/openadapter_ | u/Human-Masterpiece-0 | `t2_2j4pez994o` | 1 | 0 | 2026-08-11 | *not read* |
| 452 | 15.6 | post | [How do you manage to spend so little?](https://www.reddit.com/r/DeepSeek/comments/1uxys7j/how_do_you_manage_to_spend_so_little/) | r/DeepSeek | u/Keryfia | `t2_3gfxxvlq` | 13 | 29 | 2026-07-16 | *not read* |
| 455 | 15.5 | post | [DeepSeek v4 Pro 75% off is now permanent.](https://www.reddit.com/r/GithubCopilot/comments/1tkzjqx/deepseek_v4_pro_75_off_is_now_permanent/) | r/GithubCopilot | u/ProfessionalJackals | `t2_1lqtnyul8t` | 341 | 71 | 2026-05-22 | *not read* |
| 456 | 15.5 | post | [Tests de maîtrise du français : les modèles chinois (DeepSee](https://www.reddit.com/r/ollama/comments/1w0tx7i/tests_de_maîtrise_du_français_les_modèles_chinois/) | r/ollama | u/Jeanjose1993 | `t2_280gdfmgr9` | 1 | 14 | 2026-08-28 | *not read* |
| 457 | 15.5 | post | [DeepSeek New Release Makes DeepSeek V4 Faster Without Losing](https://www.reddit.com/r/AISEOInsider/comments/1ulo48g/deepseek_new_release_makes_deepseek_v4_faster/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-07-02 | *not read* |
| 458 | 15.5 | post | [DeepSeek V4 1m Context Window no longer works for Claude Des](https://www.reddit.com/r/DeepSeek/comments/1u9a0xg/deepseek_v4_1m_context_window_no_longer_works_for/) | r/DeepSeek | u/EmperorSheep | `t2_1sfjgary` | 8 | 17 | 2026-06-18 | *not read* |
| 464 | 15.4 | post | [Actual observations on Deepseek v4 pro](https://www.reddit.com/r/LLMDevs/comments/1t6ii8m/actual_observations_on_deepseek_v4_pro/) | r/LLMDevs | u/aidenclarke_12 | `t2_1we9gevp4b` | 9 | 7 | 2026-05-07 | *not read* |
| 465 | 15.4 | post | [A little story on loremate for new users](https://www.reddit.com/r/LoreMateAI/comments/1uop0er/a_little_story_on_loremate_for_new_users/) | r/LoreMateAI | u/me_broke | `t2_wl005y3or` | 48 | 7 | 2026-07-06 | *not read* |
| 466 | 15.4 | post | [I am 14, and I used DeepSeek V4 + Reasonix to build a produc](https://www.reddit.com/r/DeepSeek/comments/1tzmkdb/i_am_14_and_i_used_deepseek_v4_reasonix_to_build/) | r/DeepSeek | u/frraz_me | `t2_1pmnamn2kk` | 16 | 5 | 2026-06-07 | *not read* |
| 467 | 15.4 | post | [Writer's Block 3.1415/2 In 3DD: Write Harder. A Prose and Na](https://www.reddit.com/r/SillyTavernAI/comments/1t23shb/writers_block_314152_in_3dd_write_harder_a_prose/) | r/SillyTavernAI | u/Deiomo | `t2_1kmbl0in` | 139 | 18 | 2026-05-02 | *not read* |
| 468 | 15.2 | post | [VLLM for B300 + Deepseek v4 pro](https://www.reddit.com/r/Vllm/comments/1u3y8i9/vllm_for_b300_deepseek_v4_pro/) | r/Vllm | u/hrusli | `t2_67jznk4d` | 24 | 19 | 2026-06-12 | *not read* |
| 470 | 15.2 | post | [Hot take: the price increase is much less worse than it seem](https://www.reddit.com/r/DeepSeek/comments/1vnav1g/hot_take_the_price_increase_is_much_less_worse/) | r/DeepSeek | u/Kerbiter | `t2_cu5r9i8` | 105 | 63 | 2026-08-13 | *not read* |
| 474 | 15.0 | post | [DeepSeek just popped the American AI bubble.](https://www.reddit.com/r/ArtificialInteligence/comments/1tm49zw/deepseek_just_popped_the_american_ai_bubble/) | r/ArtificialInteligence | u/VegetablePen4755 | `t2_xhm86iv5s` | 719 | 278 | 2026-05-24 | *not read* |
| 477 | 15.0 | post | [Max20 user: anyone running Opus 4.7 as orchestrator + DeepSe](https://www.reddit.com/r/ClaudeAI/comments/1tcvngy/max20_user_anyone_running_opus_47_as_orchestrator/) | r/ClaudeAI | u/theargen | `t2_10jp48` | 8 | 12 | 2026-05-14 | *not read* |
| 478 | 15.0 | post | [If Qwen3.8-Next-Flash is a Preview for the Qwen-4 Architectu](https://www.reddit.com/r/Qwen_AI/comments/1w05h1r/if_qwen38nextflash_is_a_preview_for_the_qwen4/) | r/Qwen_AI | u/Iory1998 | `t2_byt5wa14` | 142 | 37 | 2026-08-27 | *not read* |
| 479 | 15.0 | post | [DeepSeek V4 gets ~3.4× faster at the same score; GLM 5.3 imp](https://www.reddit.com/r/DeepSeek/comments/1vzcclv/deepseek_v4_gets_34_faster_at_the_same_score_glm/) | r/DeepSeek | u/Correct_Tomato1871 | `t2_twm7zx0l` | 25 | 3 | 2026-08-26 | *not read* |
| 481 | 15.0 | post | [LE_EMOTIONALISM! Version 1.1.5 - Emotional-based preset for ](https://www.reddit.com/r/SillyTavernAI/comments/1v46vqe/le_emotionalism_version_115_emotionalbased_preset/) | r/SillyTavernAI | u/HippoFuzzy5815 | `t2_j7he6opo` | 37 | 21 | 2026-07-23 | *not read* |
| 482 | 14.8 | post | [For users with 4x-8x 6000 PROs, how is your experience with ](https://www.reddit.com/r/LocalLLaMA/comments/1uex6pb/for_users_with_4x8x_6000_pros_how_is_your/) | r/LocalLLaMA | u/panchovix | `t2_j1kqr` | 104 | 136 | 2026-06-25 | *not read* |
| 485 | 14.8 | post | [We need a 80-160B model urgently.  The unified memory device](https://www.reddit.com/r/LocalLLaMA/comments/1u8kr2o/we_need_a_80160b_model_urgently_the_unified/) | r/LocalLLaMA | u/Storge2 | `t2_30udbmhy` | 648 | 290 | 2026-06-17 | *not read* |
| 486 | 14.8 | post | [GPT-5.6 Sol price cut by 50% on OpenRouter - enough to switc](https://www.reddit.com/r/AIToolsPerformance/comments/1vsv6cq/gpt56_sol_price_cut_by_50_on_openrouter_enough_to/) | r/AIToolsPerformance | u/IulianHI | `t2_10nqfcv1` | 7 | 5 | 2026-08-19 | *not read* |
| 487 | 14.8 | post | [how did we make deepseek outperform opus [harness eng deep d](https://www.reddit.com/r/CommandCode/comments/1unkp7v/how_did_we_make_deepseek_outperform_opus_harness/) | r/CommandCode | u/ahmadawaiscom | `t2_4g5zlnqq` | 56 | 13 | 2026-07-04 | *not read* |
| 488 | 14.8 | post | [PSA: If you are using DeepSeek V4 Pro on OpenRouter, block t](https://www.reddit.com/r/SillyTavernAI/comments/1tchbkb/psa_if_you_are_using_deepseek_v4_pro_on/) | r/SillyTavernAI | u/kenv_ | `t2_1rzeo7nkka` | 53 | 12 | 2026-05-13 | *not read* |
| 490 | 14.7 | post | [AI Roundup — Aug 13: Grok 4.6 Lands, DeepSeek V4 Pro Drops, ](https://www.reddit.com/r/AIToolsTipsNews/comments/1vn9mcd/ai_roundup_aug_13_grok_46_lands_deepseek_v4_pro/) | r/AIToolsTipsNews | u/ayushchat | `t2_4ehwncvo` | 1 | 1 | 2026-08-13 | *not read* |
| 492 | 14.7 | post | [I feel like people are massively sleeping on Qwen3.6 Plus](https://www.reddit.com/r/opencodeCLI/comments/1tgp25t/i_feel_like_people_are_massively_sleeping_on/) | r/opencodeCLI | u/nbr_engineer | `t2_1qqhsq1h3a` | 95 | 43 | 2026-05-18 | *not read* |
| 493 | 14.7 | post | [My comparison between Deepseek(+vision proxy) and Minimax-M3](https://www.reddit.com/r/DeepSeek/comments/1ung8wk/my_comparison_between_deepseekvision_proxy_and/) | r/DeepSeek | u/Separate_Ad_314 | `t2_eh4oecv4` | 17 | 10 | 2026-07-04 | *not read* |
| 496 | 14.6 | post | [Switching my app's AI features from Gemini to DeepSeek V4 dr](https://www.reddit.com/r/SideProject/comments/1tw94jy/switching_my_apps_ai_features_from_gemini_to/) | r/SideProject | u/0xKlyyze | `t2_5ovhmdwb` | 1 | 2 | 2026-06-04 | *not read* |
| 499 | 14.6 | post | [Top 10 best OpenCode Go models by capabilities and usage lim](https://www.reddit.com/r/opencodeCLI/comments/1w2vu9m/top_10_best_opencode_go_models_by_capabilities/) | r/opencodeCLI | u/AloisCRR | `t2_2g3kxxkl` | 32 | 18 | 2026-08-30 | *not read* |
| 501 | 14.5 | post | [GLM 5.3 Release Is Surprisingly Good At Coding (2026)](https://www.reddit.com/r/AISEOInsider/comments/1vpj8is/glm_53_release_is_surprisingly_good_at_coding_2026/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-16 | *not read* |
| 502 | 14.5 | post | [Why is DeepSeek V4 seems struggling with an address-autocomp](https://www.reddit.com/r/hermesagent/comments/1ubi5lc/why_is_deepseek_v4_seems_struggling_with_an/) | r/hermesagent | u/feargone | `t2_3iyzb0rd` | 0 | 0 | 2026-06-21 | *not read* |
| 504 | 14.5 | post | [AgentZet v1.0.0 - DeepSeek V4 &amp; Claude Opus 4.7/4.8 Mode](https://www.reddit.com/r/AgentZet/comments/1u10iz4/agentzet_v100_deepseek_v4_claude_opus_4748_model/) | r/AgentZet | u/ionutvi | `t2_5a186uc1` | 1 | 0 | 2026-06-09 | *not read* |
| 505 | 14.5 | post | [🎭 RoleCall v2.630.0 \| Update Log](https://www.reddit.com/r/RoleCallStudios/comments/1uu5vth/rolecall_v26300_update_log/) | r/RoleCallStudios | u/Specialist_Salad6337 | `t2_1yugvs0qou` | 5 | 1 | 2026-07-12 | *not read* |
| 507 | 14.4 | post | [Gemma 4 Preset: Moonlight](https://www.reddit.com/r/SillyTavernAI/comments/1towdj6/gemma_4_preset_moonlight/) | r/SillyTavernAI | u/Kahvana | `t2_13hq2c` | 82 | 12 | 2026-05-27 | *not read* |
| 508 | 14.4 | post | [Blind head-to-head: GLM-5.2 vs DeepSeek V4 Pro on 3 real dec](https://www.reddit.com/r/DeepSeek/comments/1u9zeqn/blind_headtohead_glm52_vs_deepseek_v4_pro_on_3/) | r/DeepSeek | u/petburiraja | `t2_60jo8coj` | 30 | 15 | 2026-06-19 | *not read* |
| 509 | 14.3 | post | [GPT 5.6 Luna vs DeepSeek V4](https://www.reddit.com/r/DeepSeek/comments/1vnpplo/gpt_56_luna_vs_deepseek_v4/) | r/DeepSeek | u/LeTanLoc98 | `t2_25i76blr` | 23 | 37 | 2026-08-13 | *not read* |
| 512 | 14.3 | post | [Introducing the Slop Index](https://www.reddit.com/r/WritingWithAI/comments/1umhys2/introducing_the_slop_index/) | r/WritingWithAI | u/Write_My_Novel | `t2_2byzk7nnsq` | 30 | 37 | 2026-07-03 | *not read* |
| 514 | 14.2 | post | [DeepSeek made permanent a 75% price cut on its flagship V4-P](https://www.reddit.com/r/Agent_AI/comments/1to63gx/deepseek_made_permanent_a_75_price_cut_on_its/) | r/Agent_AI | u/OkiDokiPoki22 | `t2_1mj2wl816k` | 14 | 1 | 2026-05-26 | *not read* |
| 516 | 14.2 | post | [Tested Qwen3-235B vs DeepSeek V4 Pro on 50 coding tasks — re](https://www.reddit.com/r/DeepSeek/comments/1tkd1ux/tested_qwen3235b_vs_deepseek_v4_pro_on_50_coding/) | r/DeepSeek | u/Fresh-Resolution182 | `t2_251gat3t4d` | 0 | 18 | 2026-05-22 | *not read* |
| 517 | 14.2 | post | [Honest review of DeepSeek v4 Pro in GitHub Copilot](https://www.reddit.com/r/GithubCopilot/comments/1ttgfqy/honest_review_of_deepseek_v4_pro_in_github_copilot/) | r/GithubCopilot | u/Jack99Skellington | `t2_3z7gff` | 10 | 10 | 2026-06-01 | *not read* |
| 520 | 14.2 | post | [DeepSeek V4 Pro FREE Has One Big Catch](https://www.reddit.com/r/AISEOInsider/comments/1tlc65u/deepseek_v4_pro_free_has_one_big_catch/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 2 | 2026-05-23 | *not read* |
| 522 | 14.1 | post | [Is DeepSeek V4 Pro even worth using on OpenCode when GLM 5.2](https://www.reddit.com/r/opencodeCLI/comments/1vyarxy/is_deepseek_v4_pro_even_worth_using_on_opencode/) | r/opencodeCLI | u/Southern-Ad-3006 | `t2_1wr5ocu9` | 26 | 7 | 2026-08-25 | *not read* |
| 523 | 14.1 | post | [Deepseek V4 And Claude Code Is A Coding Setup Worth Testing](https://www.reddit.com/r/AISEOInsider/comments/1t2is69/deepseek_v4_and_claude_code_is_a_coding_setup/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-05-03 | *not read* |
| 529 | 14.0 | post | [MegaNova just added DeepSeek v4 and Mimo v2.5 — here's my ex](https://www.reddit.com/r/JanitorAI_Refuges/comments/1sup0bl/meganova_just_added_deepseek_v4_and_mimo_v25/) | r/JanitorAI_Refuges | u/Fabulous_Win5325 | `t2_1v08yn2llh` | 4 | 3 | 2026-04-24 | *not read* |
| 530 | 14.0 | post | [That's not nothing! DeepSeek V4 Pro](https://www.reddit.com/r/DeepSeek/comments/1tbq28g/thats_not_nothing_deepseek_v4_pro/) | r/DeepSeek | u/uncovery | `t2_5nu58` | 31 | 19 | 2026-05-13 | *not read* |
| 531 | 14.0 | post | [DeepSeek V4 Pro just dropped. I put it to work immediately](https://www.reddit.com/r/DeepSeek/comments/1vnvt33/deepseek_v4_pro_just_dropped_i_put_it_to_work/) | r/DeepSeek | u/Illustrious-Many-782 | `t2_cyl908di` | 4 | 3 | 2026-08-14 | *not read* |
| 533 | 14.0 | post | [DeepSeek open sources DSpark, a new framework to speed up LL](https://www.reddit.com/r/BayAreaHomes/comments/1uj6f49/deepseek_open_sources_dspark_a_new_framework_to/) | r/BayAreaHomes | u/RamsinJacobRealty | `t2_k80vqlw` | 1 | 0 | 2026-06-29 | *not read* |
| 535 | 14.0 | post | [Switching to DeepSeek V4 Pro: My Workflow Takeaways](https://www.reddit.com/r/GithubCopilot/comments/1u1184o/switching_to_deepseek_v4_pro_my_workflow_takeaways/) | r/GithubCopilot | u/Calm-Procedure1847 | `t2_1mw1au3b2y` | 37 | 20 | 2026-06-09 | *not read* |
| 537 | 13.9 | post | [DeepSeek V4 Pro 0813 is out, with Fable-level agent benchmar](https://www.reddit.com/r/myclaw/comments/1vn73ye/deepseek_v4_pro_0813_is_out_with_fablelevel_agent/) | r/myclaw | u/lucienbaba | `t2_cx8secsv` | 4 | 8 | 2026-08-13 | *not read* |
| 538 | 13.9 | post | [Benchmarks don't mean anything anymore.](https://www.reddit.com/r/LocalLLM/comments/1vr1429/benchmarks_dont_mean_anything_anymore/) | r/LocalLLM | u/Nerfariox | `t2_1fizjcg7ai` | 0 | 12 | 2026-08-17 | *not read* |
| 544 | 13.8 | post | [I've Been Using Hermes for 30+ Days, and It Keeps Getting Wo](https://www.reddit.com/r/hermesagent/comments/1ttjrzf/ive_been_using_hermes_for_30_days_and_it_keeps/) | r/hermesagent | u/podalusu | `t2_v2ol2gon` | 18 | 38 | 2026-06-01 | *not read* |
| 545 | 13.8 | post | [Multihog D&amp;D Framework \| The ULTIMATE RPG Extension](https://www.reddit.com/r/SillyTavernAI/comments/1v6dlp8/multihog_dd_framework_the_ultimate_rpg_extension/) | r/SillyTavernAI | u/Mimotive11 | `t2_12rhq5nm0a` | 198 | 87 | 2026-07-25 | *not read* |
| 546 | 13.8 | post | [[Workflow] Claude Code: Integrate DeepSeek V4 (Flash/Pro) as](https://www.reddit.com/r/ClaudeWorkflows/comments/1t600ru/workflow_claude_code_integrate_deepseek_v4/) | r/ClaudeWorkflows | u/ClaudeAI-mod-bot | `t2_1vs6v2gkb0` | 1 | 0 | 2026-05-07 | *not read* |
| 547 | 13.8 | post | [DeepSeek v4-pro in Cursor: When Quality and Cost Matter More](https://www.reddit.com/r/LLM_Brand_Perception/comments/1tca1iz/deepseek_v4pro_in_cursor_when_quality_and_cost/) | r/LLM_Brand_Perception | u/Mean-Awareness7102 | `t2_279iavefxv` | 1 | 0 | 2026-05-13 | *not read* |
| 549 | 13.7 | post | [I built one OpenAI-compatible API for Claude, GPT, Gemini, D](https://www.reddit.com/r/SideProject/comments/1w3yheu/i_built_one_openaicompatible_api_for_claude_gpt/) | r/SideProject | u/No_Visit479 | `t2_7rhww8ugw` | 1 | 0 | 2026-09-01 | *not read* |
| 552 | 13.7 | post | [ChatLLM AI Models and Their Best Use Cases](https://www.reddit.com/r/abacusai/comments/1vtki6o/chatllm_ai_models_and_their_best_use_cases/) | r/abacusai | u/datawithmanur | `t2_2bd1gqxhy6` | 2 | 2 | 2026-08-20 | *not read* |
| 554 | 13.6 | post | [DeepSeek V4 Pro is NOT available on the website or in the ap](https://www.reddit.com/r/DeepSeek/comments/1suplud/deepseek_v4_pro_is_not_available_on_the_website/) | r/DeepSeek | u/ZombieBlaster21 | `t2_teni5b05` | 93 | 31 | 2026-04-24 | *not read* |
| 555 | 13.6 | post | [Looking for 10 SillyTavern testers - 700 free AI requests fo](https://www.reddit.com/r/SillyTavernAI/comments/1vvlx1n/looking_for_10_sillytavern_testers_700_free_ai/) | r/SillyTavernAI | u/itzilab | `t2_2kmhxa9jmd` | 0 | 39 | 2026-08-22 | *not read* |
| 557 | 13.6 | post | [opencode-go/deepseek-v4-pro 4x cheaper just like this?](https://www.reddit.com/r/opencodeCLI/comments/1v25lcz/opencodegodeepseekv4pro_4x_cheaper_just_like_this/) | r/opencodeCLI | u/Odd_Fly932 | `t2_6o7pwvpp` | 74 | 22 | 2026-07-21 | *not read* |
| 558 | 13.5 | post | [DeepSeek just popped the American AI bubble.](https://www.reddit.com/r/OpenAI/comments/1tm49d0/deepseek_just_popped_the_american_ai_bubble/) | r/OpenAI | u/VegetablePen4755 | `t2_xhm86iv5s` | 1323 | 250 | 2026-05-24 | *not read* |
| 560 | 13.5 | post | [DeepSeek just popped the American AI bubble.](https://www.reddit.com/r/AI_India/comments/1tm3hhw/deepseek_just_popped_the_american_ai_bubble/) | r/AI_India | u/VegetablePen4755 | `t2_xhm86iv5s` | 416 | 39 | 2026-05-24 | *not read* |
| 561 | 13.5 | post | [Free DeepSeek V4 AI Chatbot unlimited](https://www.reddit.com/r/freetoolsAI/comments/1tuwqad/free_deepseek_v4_ai_chatbot_unlimited/) | r/freetoolsAI | u/Whole_Engine | `t2_3kkjiepc` | 84 | 19 | 2026-06-02 | *not read* |
| 565 | 13.5 | post | [[sharing] real usage convertion for ollama pro](https://www.reddit.com/r/ollama/comments/1t50brh/sharing_real_usage_convertion_for_ollama_pro/) | r/ollama | u/Guilty_Nothing_2858 | `t2_6fom9ltz` | 3 | 2 | 2026-05-06 | *not read* |
| 566 | 13.5 | post | [GPT-5.5 improves over GPT-5.4 and overtakes Opus 4.6 to take](https://www.reddit.com/r/singularity/comments/1sxe3bs/gpt55_improves_over_gpt54_and_overtakes_opus_46/) | r/singularity | u/zero0_one1 | `t2_p2tr0` | 172 | 46 | 2026-04-27 | *not read* |
| 570 | 13.4 | post | [DeepSeek V4 Pro on my social deduction benchmark](https://www.reddit.com/r/DeepSeek/comments/1t3pjsc/deepseek_v4_pro_on_my_social_deduction_benchmark/) | r/DeepSeek | u/cjami | `t2_al5ts` | 21 | 3 | 2026-05-04 | *not read* |
| 574 | 13.3 | post | [DeepSeek introduced V4 — a competitor to ChatGPT, Claude, an](https://www.reddit.com/r/rpgc_official/comments/1t48jhz/deepseek_introduced_v4_a_competitor_to_chatgpt/) | r/rpgc_official | u/RIPT1D3_Z | `t2_1zyh18yq` | 1 | 0 | 2026-05-05 | *not read* |
| 576 | 13.2 | post | [Deepseek V4 pro vs Minimax M3. Judge is Opus 4.8. Results ar](https://www.reddit.com/r/DeepSeek/comments/1ufok23/deepseek_v4_pro_vs_minimax_m3_judge_is_opus_48/) | r/DeepSeek | u/Decent-Rain5100 | `t2_1zrwroipfi` | 154 | 78 | 2026-06-25 | *not read* |
| 578 | 13.2 | post | [Does OAI even care anymore?](https://www.reddit.com/r/ChatGPTcomplaints/comments/1ubc1a3/does_oai_even_care_anymore/) | r/ChatGPTcomplaints | u/IAM_274 | `t2_8ujuojl2` | 46 | 13 | 2026-06-21 | *not read* |
| 581 | 13.2 | post | [Deepseek v4 flash (NEW) tested against four other models - i](https://www.reddit.com/r/DeepSeek/comments/1vby6z8/deepseek_v4_flash_new_tested_against_four_other/) | r/DeepSeek | u/Decent-Rain5100 | `t2_1zrwroipfi` | 46 | 7 | 2026-07-31 | *not read* |
| 582 | 13.2 | post | [How to run Claude Code for free!](https://www.reddit.com/r/vibecoding/comments/1t8m55w/how_to_run_claude_code_for_free/) | r/vibecoding | u/Veerbhadra_1 | `t2_1rnr595f5o` | 30 | 52 | 2026-05-09 | *not read* |
| 587 | 13.1 | post | [Claude Haiku vs DeepSeek V4 (Pro/Flash, max reasoning) for A](https://www.reddit.com/r/AI_Agents/comments/1v0l6g6/claude_haiku_vs_deepseek_v4_proflash_max/) | r/AI_Agents | u/ArthitectureHome | `t2_7l3dvzbk` | 2 | 5 | 2026-07-19 | *not read* |
| 590 | 13.0 | post | [Deepseek V4 Pro Turns Simple Prompts Into Real Automation](https://www.reddit.com/r/AISEOInsider/comments/1svx8aa/deepseek_v4_pro_turns_simple_prompts_into_real/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-04-26 | *not read* |
| 591 | 13.0 | post | [Cursor Composer 2.5 keeps trashing my complex codebase  what](https://www.reddit.com/r/AI_Agents/comments/1ubwclf/cursor_composer_25_keeps_trashing_my_complex/) | r/AI_Agents | u/jacklsd | `t2_5owzggw8` | 2 | 8 | 2026-06-21 | *not read* |
| 593 | 13.0 | post | [Update to the LLM Debate Benchmark: GPT-5.5, Grok 4.3, DeepS](https://www.reddit.com/r/singularity/comments/1t4o37r/update_to_the_llm_debate_benchmark_gpt55_grok_43/) | r/singularity | u/zero0_one1 | `t2_p2tr0` | 61 | 14 | 2026-05-05 | *not read* |
| 594 | 13.0 | post | [How DeepSeek Harness Agent Creates Custom AI Workflows](https://www.reddit.com/r/AISEOInsider/comments/1vu64bv/how_deepseek_harness_agent_creates_custom_ai/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-21 | *not read* |
| 596 | 12.9 | post | [My Honest Command Code Review After Few Days of Daily Use](https://www.reddit.com/r/opencodeCLI/comments/1u0vi9b/my_honest_command_code_review_after_few_days_of/) | r/opencodeCLI | u/No_Durian_5657 | `t2_243cfgx8hq` | 43 | 89 | 2026-06-09 | *not read* |
| 598 | 12.8 | post | [I tested DeepSeek V4 Pro 0813 on 16 Hack The Box challenges](https://www.reddit.com/r/DeepSeek/comments/1vshgy5/i_tested_deepseek_v4_pro_0813_on_16_hack_the_box/) | r/DeepSeek | u/TheArtificalQ | `t2_2kzspcxwlv` | 22 | 15 | 2026-08-19 | *not read* |
| 599 | 12.8 | post | [Make Deepseek V4 Pro act like an Anthropic Model in Claude C](https://www.reddit.com/r/DeepSeek/comments/1v55tgp/make_deepseek_v4_pro_act_like_an_anthropic_model/) | r/DeepSeek | u/des369 | `t2_2ilzwu3bzn` | 13 | 18 | 2026-07-24 | *not read* |
| 600 | 12.8 | post | [For users with 4x-8x 6000 PROs, how is your experience with ](https://www.reddit.com/r/LocalLLM/comments/1uex6u9/for_users_with_4x8x_6000_pros_how_is_your/) | r/LocalLLM | u/panchovix | `t2_j1kqr` | 4 | 5 | 2026-06-25 | *not read* |
| 601 | 12.8 | post | [Hetzner is experimenting with an OpenAI-compatible LLM infer](https://www.reddit.com/r/hetzner/comments/1v568oh/hetzner_is_experimenting_with_an_openaicompatible/) | r/hetzner | u/CodeCate42 | `t2_1bj3ii` | 69 | 33 | 2026-07-24 | *not read* |
| 602 | 12.8 | post | [I connected my own DeepSeek-V4 Pro API to Work buddy: quick ](https://www.reddit.com/r/DeepSeek/comments/1vv4863/i_connected_my_own_deepseekv4_pro_api_to_work/) | r/DeepSeek | u/Zeshness | `t2_az3rhwvx` | 7 | 1 | 2026-08-22 | *not read* |
| 604 | 12.6 | post | [The "Smart" Models Bluff: The "Smart Model"](https://www.reddit.com/r/Futurism/comments/1w4064c/the_smart_models_bluff_the_smart_model/) | r/Futurism | u/Glittering-Town5941 | `t2_2evqhfm3pu` | 0 | 2 | 2026-09-01 | *not read* |
| 605 | 12.6 | post | [The "Smart" Models Bluff: The "Smart Model"](https://www.reddit.com/r/u_Glittering-Town5941/comments/1w4048n/the_smart_models_bluff_the_smart_model/) | r/u_Glittering-Town5941 | u/Glittering-Town5941 | `t2_2evqhfm3pu` | 2 | 0 | 2026-09-01 | *not read* |
| 607 | 12.6 | post | [DeepSeek-V4-Flash Update](https://www.reddit.com/r/DeepSeek/comments/1vbj0aa/deepseekv4flash_update/) | r/DeepSeek | u/nekofneko | `t2_sqi8xxun` | 588 | 209 | 2026-07-31 | *not read* |
| 608 | 12.6 | post | [Gemini 3.7 Flash is currently 75% off on OpenRouter, beating](https://www.reddit.com/r/singularity/comments/1vvb47a/gemini_37_flash_is_currently_75_off_on_openrouter/) | r/singularity | u/elemental-mind | `t2_zuk73gll6` | 176 | 28 | 2026-08-22 | *not read* |
| 609 | 12.6 | post | [From Tailscale to Netbird: migrated my overlay network infra](https://www.reddit.com/r/netbird/comments/1tawewz/from_tailscale_to_netbird_migrated_my_overlay/) | r/netbird | u/Apo-Z | `t2_2b6kthgtca` | 17 | 2 | 2026-05-12 | *not read* |
| 611 | 12.5 | post | [Deepseek Token Usage](https://www.reddit.com/r/DeepSeek/comments/1tlevtr/deepseek_token_usage/) | r/DeepSeek | u/JP23102 | `t2_7wjdmtvt7` | 40 | 48 | 2026-05-23 | *not read* |
| 612 | 12.5 | post | [Ollama Cloud with Deepseek rate limit](https://www.reddit.com/r/ollama/comments/1ta3mpv/ollama_cloud_with_deepseek_rate_limit/) | r/ollama | u/No-Ad-6338 | `t2_7zbjgveo` | 24 | 21 | 2026-05-11 | *not read* |
| 613 | 12.5 | post | [Vibed a 3d procedural world experiment](https://www.reddit.com/r/AI_Agents/comments/1uy0kdc/vibed_a_3d_procedural_world_experiment/) | r/AI_Agents | u/miran248 | `t2_1q1kwgdb` | 2 | 4 | 2026-07-16 | *not read* |
| 615 | 12.4 | post | [Tencent Hy4 Preview leads SWE bench Pro and you can try it i](https://www.reddit.com/r/CLine/comments/1w3e262/tencent_hy4_preview_leads_swe_bench_pro_and_you/) | r/CLine | u/gargetisha | `t2_ms94y2x6` | 41 | 22 | 2026-08-31 | *not read* |
| 619 | 12.4 | post | [DeepSeek Releases DSpark, a Speculative Decoding Framework T](https://www.reddit.com/r/machinelearningnews/comments/1uh83aw/deepseek_releases_dspark_a_speculative_decoding/) | r/machinelearningnews | u/ai-lover | `t2_2wsvqwhg` | 23 | 0 | 2026-06-27 | *not read* |
| 621 | 12.4 | post | [GLM-5.3: stesso base di 5.2, post-training su coding e cyber](https://www.reddit.com/r/vibecodingitalia/comments/1vo6u37/glm53_stesso_base_di_52_posttraining_su_coding_e/) | r/vibecodingitalia | u/thestreamcode | `t2_ivb43w3e3` | 14 | 0 | 2026-08-14 | *not read* |
| 622 | 12.3 | post | [Qwen3.8 27B is matching DeepSeek V4 Pro and GPT 5.6 Luna on ](https://www.reddit.com/r/CLine/comments/1vrisoa/qwen38_27b_is_matching_deepseek_v4_pro_and_gpt_56/) | r/CLine | u/gargetisha | `t2_ms94y2x6` | 181 | 46 | 2026-08-18 | *not read* |
| 625 | 12.3 | post | [DeepSeek V4 Pro runs on Chinese chips, breaking US export co](https://www.reddit.com/r/u_petburiraja/comments/1swzrbl/deepseek_v4_pro_runs_on_chinese_chips_breaking_us/) | r/u_petburiraja | u/petburiraja | `t2_60jo8coj` | 1 | 0 | 2026-04-27 | *not read* |
| 628 | 12.2 | post | [Local-first Pi coding agents: what actually makes sense?](https://www.reddit.com/r/PiCodingAgent/comments/1u3zkj0/localfirst_pi_coding_agents_what_actually_makes/) | r/PiCodingAgent | u/TraditionalDaikon291 | `t2_l8vj5ivq` | 5 | 24 | 2026-06-12 | *not read* |
| 629 | 12.2 | post | [Model choice for an Arabic BM25/RAG pipeline](https://www.reddit.com/r/Rag/comments/1v1held/model_choice_for_an_arabic_bm25rag_pipeline/) | r/Rag | u/Amjed5 | `t2_lharspn4` | 7 | 10 | 2026-07-20 | *not read* |
| 631 | 12.1 | post | [Hermes Agent token usage/cost projection is insane. Am I doi](https://www.reddit.com/r/hermesagent/comments/1u8k0mb/hermes_agent_token_usagecost_projection_is_insane/) | r/hermesagent | u/ghsac_io | `t2_1yxe4v7arf` | 23 | 27 | 2026-06-17 | *not read* |
| 633 | 12.1 | post | [Is opencode &gt; Claude ?](https://www.reddit.com/r/opencodeCLI/comments/1ukpwqr/is_opencode_claude/) | r/opencodeCLI | u/Pristine_Gur_9573 | `t2_21lq952rix` | 32 | 43 | 2026-07-01 | *not read* |
| 634 | 12.1 | post | [Hermes Agent with DeepSeek v4 Builds AI Workflows Fast](https://www.reddit.com/r/AISEOInsider/comments/1vdq9io/hermes_agent_with_deepseek_v4_builds_ai_workflows/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 0 | 0 | 2026-08-02 | *not read* |
| 635 | 12.1 | post | [You can really feel the impact of Ponytail and RTK when it c](https://www.reddit.com/r/codex/comments/1udsqzm/you_can_really_feel_the_impact_of_ponytail_and/) | r/codex | u/Glittering-Smell2937 | `t2_6tldm5is0` | 85 | 53 | 2026-06-23 | *not read* |
| 636 | 12.1 | post | [DeepSeek Harness Agent Is FREE And Runs On Your Own Machine](https://www.reddit.com/r/AISEOInsider/comments/1vuzdd1/deepseek_harness_agent_is_free_and_runs_on_your/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-22 | *not read* |
| 637 | 12.0 | post | [To anyone saying deepseek v4 pro is better than opus 4.7, it](https://www.reddit.com/r/DeepSeek/comments/1t3ycsq/to_anyone_saying_deepseek_v4_pro_is_better_than/) | r/DeepSeek | u/Global-Fan189 | `t2_c6xoyzid` | 180 | 142 | 2026-05-04 | *not read* |
| 640 | 12.0 | post | [Super DeepSeek Intelegence Model since last 48 Hours](https://www.reddit.com/r/DeepSeek/comments/1uaslg1/super_deepseek_intelegence_model_since_last_48/) | r/DeepSeek | u/LinuXperia | `t2_1qmkj7zc` | 194 | 91 | 2026-06-20 | *not read* |
| 641 | 12.0 | post | [Kimi K3 went from 0% → 16% of ClinePass open weights usage i](https://www.reddit.com/r/CLine/comments/1v48eqb/kimi_k3_went_from_0_16_of_clinepass_open_weights/) | r/CLine | u/gargetisha | `t2_ms94y2x6` | 20 | 8 | 2026-07-23 | *not read* |
| 643 | 11.9 | post | [For learning Python and AI engineering, which AI is most use](https://www.reddit.com/r/AskProgramming/comments/1tunlp3/for_learning_python_and_ai_engineering_which_ai/) | r/AskProgramming | u/fun2function | `t2_19boa81mhs` | 0 | 13 | 2026-06-02 | *not read* |
| 646 | 11.8 | post | [Aura Agent: letting an AI coding agent supervise long-runnin](https://www.reddit.com/r/DeepSeek/comments/1t4m3ox/aura_agent_letting_an_ai_coding_agent_supervise/) | r/DeepSeek | u/Civil-Direction-6981 | `t2_764ts0id` | 4 | 12 | 2026-05-05 | *not read* |
| 651 | 11.8 | post | [Looking for 10 roleplay testers - 700 free AI messages over ](https://www.reddit.com/r/JanitorAI_Refuges/comments/1vwajwp/looking_for_10_roleplay_testers_700_free_ai/) | r/JanitorAI_Refuges | u/itzilab | `t2_2kmhxa9jmd` | 1 | 19 | 2026-08-23 | *not read* |
| 652 | 11.8 | post | [Token consumption vs price for agentic coding for Deepseek V](https://www.reddit.com/r/LLMDevs/comments/1sznrqj/token_consumption_vs_price_for_agentic_coding_for/) | r/LLMDevs | u/Ok-Yam-1081 | `t2_e7rw4lhl8` | 7 | 12 | 2026-04-30 | *not read* |
| 653 | 11.8 | post | [I stress-tested DeepSeek V4 Pro on a C++ 3D geometry app. It](https://www.reddit.com/r/vibecoding/comments/1twkmwu/i_stresstested_deepseek_v4_pro_on_a_c_3d_geometry/) | r/vibecoding | u/Equivalent_Ostrich_6 | `t2_7mf39sas` | 3 | 5 | 2026-06-04 | *not read* |
| 655 | 11.8 | post | [DeepSeek V4 Pro is ranked #2 in our AI Startup Race: here's ](https://www.reddit.com/r/DeepSeek/comments/1t3b20i/deepseek_v4_pro_is_ranked_2_in_our_ai_startup/) | r/DeepSeek | u/jochenboele | `t2_f0ifh5p` | 25 | 4 | 2026-05-04 | *not read* |
| 658 | 11.7 | post | [DeepSeek just released DeepSeek-V4 [At 1 million tokens, Dee](https://www.reddit.com/r/machinelearningnews/comments/1sumsja/deepseek_just_released_deepseekv4_at_1_million/) | r/machinelearningnews | u/ai-lover | `t2_2wsvqwhg` | 34 | 0 | 2026-04-24 | *not read* |
| 659 | 11.7 | post | [Top open weight models like ds v4 pro max are still like  6-](https://www.reddit.com/r/singularity/comments/1sudoae/top_open_weight_models_like_ds_v4_pro_max_are/) | r/singularity | u/power97992 | `t2_64yf00b9` | 25 | 42 | 2026-04-24 | *not read* |
| 661 | 11.7 | post | [Deepseek v4 Pro/Flash vs Codex $25 Business plan, which offe](https://www.reddit.com/r/DeepSeek/comments/1u78l3t/deepseek_v4_proflash_vs_codex_25_business_plan/) | r/DeepSeek | u/Leather-Cod2129 | `t2_182pbi954w` | 13 | 20 | 2026-06-16 | *not read* |
| 662 | 11.7 | post | [DeepSeek V4 Pro + OpenClaw: Why does the second message alwa](https://www.reddit.com/r/openclaw/comments/1subtbk/deepseek_v4_pro_openclaw_why_does_the_second/) | r/openclaw | u/Ok_Fish_670 | `t2_2cf5fcmsr9` | 3 | 8 | 2026-04-24 | *not read* |
| 666 | 11.6 | post | [Confusing “run out of credits” error with OpenRouter DeepSee](https://www.reddit.com/r/openclaw/comments/1tsxean/confusing_run_out_of_credits_error_with/) | r/openclaw | u/0xasten | `t2_tpwuek68` | 3 | 10 | 2026-05-31 | *not read* |
| 668 | 11.6 | post | [DeepSeek V4 Pro 'One Shot' Fail at Frontend](https://www.reddit.com/r/LocalLLaMA/comments/1vz9fy4/deepseek_v4_pro_one_shot_fail_at_frontend/) | r/LocalLLaMA | u/Elibroftw | `t2_x34f1` | 0 | 2 | 2026-08-26 | *not read* |
| 670 | 11.6 | post | [DeepSeek v4 Flash (with thinking ON) feels… different? Anyon](https://www.reddit.com/r/SillyTavernAI/comments/1suugri/deepseek_v4_flash_with_thinking_on_feels/) | r/SillyTavernAI | u/SuperManAdelHahah | `t2_1nrbdar8cs` | 4 | 14 | 2026-04-24 | *not read* |
| 672 | 11.5 | post | [DeepSeek is now ~70% of all tokens used through ClinePass](https://www.reddit.com/r/CLine/comments/1vqzlb5/deepseek_is_now_70_of_all_tokens_used_through/) | r/CLine | u/gargetisha | `t2_ms94y2x6` | 49 | 3 | 2026-08-17 | *not read* |
| 676 | 11.4 | post | [DeepSeek V4 Flash is a monster! Cheap &amp; Good, and so fas](https://www.reddit.com/r/opencodeCLI/comments/1svmgla/deepseek_v4_flash_is_a_monster_cheap_good_and_so/) | r/opencodeCLI | u/Maleficent-Movie-625 | `t2_2cn3u0n7fd` | 268 | 78 | 2026-04-25 | *not read* |
| 677 | 11.4 | post | [Add vision support to DeepSeek V4 in OpenCode](https://www.reddit.com/r/DeepSeek/comments/1umv88j/add_vision_support_to_deepseek_v4_in_opencode/) | r/DeepSeek | u/Yolo-8848 | `t2_a119z2uf` | 39 | 4 | 2026-07-04 | *not read* |
| 679 | 11.4 | post | [Anyone using Alibaba/Qwen’s $18 Token Plan daily? How do the](https://www.reddit.com/r/Qwen_AI/comments/1v2khid/anyone_using_alibabaqwens_18_token_plan_daily_how/) | r/Qwen_AI | u/Juan_Ignacio | `t2_3us3dka1` | 26 | 19 | 2026-07-21 | *not read* |
| 683 | 11.3 | post | [DeepSeek V4 Pro 0813 scored 87.9 vs Fable 5's 88.0 on Termin](https://www.reddit.com/r/DeepSeek/comments/1vmx0ij/deepseek_v4_pro_0813_scored_879_vs_fable_5s_880/) | r/DeepSeek | u/cubertwang | `t2_2hg1e3a7gb` | 5 | 9 | 2026-08-13 | *not read* |
| 684 | 11.3 | post | [[AI DAILY NEWS RUNDOWN] Microsoft Ends OpenAI Exclusivity, C](https://www.reddit.com/r/u_enoumen/comments/1sxfewq/ai_daily_news_rundown_microsoft_ends_openai/) | r/u_enoumen | u/enoumen | `t2_8u0no` | 1 | 0 | 2026-04-27 | *not read* |
| 685 | 11.3 | post | [I'm using a 1M context model in Ollama, but it shows as 200K](https://www.reddit.com/r/ollama/comments/1thjjm0/im_using_a_1m_context_model_in_ollama_but_it/) | r/ollama | u/TGoddessana | `t2_1aupr6e8f4` | 7 | 19 | 2026-05-19 | *not read* |
| 686 | 11.3 | post | [Deepseek for coding is outright dangerous. It skips tasks, i](https://www.reddit.com/r/DeepSeek/comments/1tzpz24/deepseek_for_coding_is_outright_dangerous_it/) | r/DeepSeek | u/EC36339 | `t2_stm9p0` | 40 | 106 | 2026-06-07 | *not read* |
| 687 | 11.3 | post | [OpenCode Go vs Copilot Pro+](https://www.reddit.com/r/GithubCopilot/comments/1tv0vwh/opencode_go_vs_copilot_pro/) | r/GithubCopilot | u/Spare_Possession_194 | `t2_81k459co` | 4 | 10 | 2026-06-02 | *not read* |
| 693 | 11.2 | post | [DeepSeek releases DSpark - 50%-600% faster spec decoding vs ](https://www.reddit.com/r/unsloth/comments/1ugv32u/deepseek_releases_dspark_50600_faster_spec/) | r/unsloth | u/danielhanchen | `t2_5wukhd4` | 950 | 99 | 2026-06-27 | *not read* |
| 694 | 11.2 | post | [Deepseek v4 Pro 0813 - First person shooter test](https://www.reddit.com/r/DeepSeek/comments/1vmnm3l/deepseek_v4_pro_0813_first_person_shooter_test/) | r/DeepSeek | u/Alkadon_Rinado | `t2_aefl3` | 85 | 28 | 2026-08-12 | *not read* |
| 695 | 11.2 | post | [DeepSeek dropped a 1.6-trillion-parameter open model you can](https://www.reddit.com/r/Agent_AI/comments/1uilv3u/deepseek_dropped_a_16trillionparameter_open_model/) | r/Agent_AI | u/Money-Ranger-6520 | `t2_i3ook394` | 314 | 49 | 2026-06-29 | *not read* |
| 696 | 11.2 | post | [Deepseek V4 Pro Full Version speculations](https://www.reddit.com/r/DeepSeek/comments/1vcsk5m/deepseek_v4_pro_full_version_speculations/) | r/DeepSeek | u/Haxsysgit | `t2_2b9ibd73al` | 59 | 16 | 2026-08-01 | *not read* |
| 697 | 11.2 | post | [Fusion Router never invokes the panel when the outer model =](https://www.reddit.com/r/openrouter/comments/1u5lhey/fusion_router_never_invokes_the_panel_when_the/) | r/openrouter | u/Working-Solution-773 | `t2_b6o4xj8d` | 3 | 1 | 2026-06-14 | *not read* |
| 704 | 11.0 | post | [Am I missing something, or is DeepSeek V4 Pro really not gre](https://www.reddit.com/r/GithubCopilot/comments/1tyh8d0/am_i_missing_something_or_is_deepseek_v4_pro/) | r/GithubCopilot | u/Rex4748 | `t2_trtws` | 26 | 68 | 2026-06-06 | *not read* |
| 709 | 11.0 | post | [I wrote a DeepSeek V4 provider for GitHub Copilot Chat — her](https://www.reddit.com/r/GithubCopilot/comments/1sy6uck/i_wrote_a_deepseek_v4_provider_for_github_copilot/) | r/GithubCopilot | u/Ok_Construction5877 | `t2_2c0g9p2gxe` | 8 | 3 | 2026-04-28 | *not read* |
| 711 | 11.0 | post | [I stopped paying Anthropic — here’s the Claude Code setup I ](https://www.reddit.com/r/ClaudeCode/comments/1tp7847/i_stopped_paying_anthropic_heres_the_claude_code/) | r/ClaudeCode | u/Red0Adrenaline | `t2_4jhollm1` | 0 | 33 | 2026-05-27 | *not read* |
| 712 | 10.9 | post | [DeepSeek V4 is out now!](https://www.reddit.com/r/unsloth/comments/1su4ls4/deepseek_v4_is_out_now/) | r/unsloth | u/yoracale | `t2_1162lx9rgr` | 718 | 87 | 2026-04-24 | *not read* |
| 713 | 10.9 | post | [OpenAi/Claude 5.5 API Cost: ~$250 Deepseek V4 Pro Max: ~$9](https://www.reddit.com/r/DeepSeek/comments/1u66x76/openaiclaude_55_api_cost_250_deepseek_v4_pro_max_9/) | r/DeepSeek | u/Nokoro1 | `t2_20mmzrc3dg` | 197 | 33 | 2026-06-15 | *not read* |
| 718 | 10.8 | post | [Why Is There No Information Anywhere About Chat Context Leng](https://www.reddit.com/r/genspark_ai/comments/1tymiqy/why_is_there_no_information_anywhere_about_chat/) | r/genspark_ai | u/Familiar_Result_2622 | `t2_2fy2etylax` | 6 | 1 | 2026-06-06 | *not read* |
| 720 | 10.8 | post | [Tool calling broken with DeepSeek V4 Pro when provider is se](https://www.reddit.com/r/openrouter/comments/1tqvr53/tool_calling_broken_with_deepseek_v4_pro_when/) | r/openrouter | u/tmoravec | `t2_g8ina` | 5 | 2 | 2026-05-29 | *not read* |
| 723 | 10.7 | post | [DeepSeek v4 Pro just spent 23-mins going in circles trying t](https://www.reddit.com/r/hermesagent/comments/1ucf5je/deepseek_v4_pro_just_spent_23mins_going_in/) | r/hermesagent | u/iShNoo | `t2_63ckfwes` | 9 | 9 | 2026-06-22 | *not read* |
| 724 | 10.7 | post | [Best middle ground solution between the $20 plan and $100?](https://www.reddit.com/r/codex/comments/1ujnz6v/best_middle_ground_solution_between_the_20_plan/) | r/codex | u/grannyknickersniffer | `t2_hm9f3xetn` | 21 | 64 | 2026-06-30 | *not read* |
| 726 | 10.6 | post | [Deepseek v4 lapses in quality kinda thing](https://www.reddit.com/r/SillyTavernAI/comments/1teuedb/deepseek_v4_lapses_in_quality_kinda_thing/) | r/SillyTavernAI | u/_DepressedSheep_ | `t2_1wqazcr7ws` | 26 | 24 | 2026-05-16 | *not read* |
| 729 | 10.5 | post | [Setting up of a 16xGB10 (DGX Spark) cluster](https://www.reddit.com/r/LocalLLaMA/comments/1vdcgpm/setting_up_of_a_16xgb10_dgx_spark_cluster/) | r/LocalLLaMA | u/ciprianveg | `t2_j8fit2p` | 1042 | 449 | 2026-08-02 | *not read* |
| 730 | 10.5 | post | [Nifer is insane. 700t/s with Qwen 3.6 35B (no thinking). Pur](https://www.reddit.com/r/LocalLLaMA/comments/1v8a7wb/nifer_is_insane_700ts_with_qwen_36_35b_no/) | r/LocalLLaMA | u/BringTea_666 | `t2_2cnjb7sguv` | 247 | 128 | 2026-07-27 | *not read* |
| 731 | 10.5 | post | [Tested FlappyBench on Qwen 3.8 27B, DeepSeek V4 Pro 0813, an](https://www.reddit.com/r/CommandCode/comments/1vu22f6/tested_flappybench_on_qwen_38_27b_deepseek_v4_pro/) | r/CommandCode | u/maedahbatool | `t2_s3g4io7` | 19 | 3 | 2026-08-21 | *not read* |
| 734 | 10.5 | post | [Deepseek V4 is GPT 5.4 but open source and a fraction of the](https://www.reddit.com/r/ArtificialInteligence/comments/1su4z4c/deepseek_v4_is_gpt_54_but_open_source_and_a/) | r/ArtificialInteligence | u/HexxRL | `t2_ak3rfdcr` | 29 | 5 | 2026-04-24 | *not read* |
| 735 | 10.5 | post | [DeepSeek AI Harness Launched With DeepSeek V4 Pro On The Sam](https://www.reddit.com/r/AISEOInsider/comments/1vs6y0z/deepseek_ai_harness_launched_with_deepseek_v4_pro/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-19 | *not read* |
| 738 | 10.5 | post | [The impact of DeepSeek v4 flash 0731 (still beta?) is undere](https://www.reddit.com/r/DeepSeek/comments/1vcmr55/the_impact_of_deepseek_v4_flash_0731_still_beta/) | r/DeepSeek | u/whatsoever2021 | `t2_a22q335k` | 124 | 45 | 2026-08-01 | *not read* |
| 743 | 10.4 | post | [deepseek v4 pro ignoring lorebooks and looping after ~100 me](https://www.reddit.com/r/JanitorAI_Refuges/comments/1u571ns/deepseek_v4_pro_ignoring_lorebooks_and_looping/) | r/JanitorAI_Refuges | u/Physical-Mix8783 | `t2_2g92vh5g16` | 3 | 14 | 2026-06-14 | *not read* |
| 744 | 10.4 | post | [How are you running DeepSeek V4 Pro + Flash in the same sess](https://www.reddit.com/r/DeepSeek/comments/1u1ndv0/how_are_you_running_deepseek_v4_pro_flash_in_the/) | r/DeepSeek | u/osmosisheinz | `t2_n198nqi` | 30 | 38 | 2026-06-10 | *not read* |
| 747 | 10.4 | post | [Cancelling my subscription also it was great](https://www.reddit.com/r/ollama/comments/1vhuqoc/cancelling_my_subscription_also_it_was_great/) | r/ollama | u/salesxsupport | `t2_22euf6y7` | 143 | 69 | 2026-08-07 | *not read* |
| 748 | 10.4 | post | [tested MiMo V2.5 Pro and DeepSeek V4 Pro during the World Cu](https://www.reddit.com/r/DeepSeek/comments/1v91un9/tested_mimo_v25_pro_and_deepseek_v4_pro_during/) | r/DeepSeek | u/Anywherezin | `t2_ie0ljik4` | 8 | 1 | 2026-07-28 | *not read* |
| 749 | 10.4 | post | [DeepSeek V4 Pro vs GPT-5.2 on agentic workloads - matched qu](https://www.reddit.com/r/AIToolsPerformance/comments/1t53b8m/deepseek_v4_pro_vs_gpt52_on_agentic_workloads/) | r/AIToolsPerformance | u/IulianHI | `t2_10nqfcv1` | 6 | 1 | 2026-05-06 | *not read* |
| 753 | 10.3 | post | [DeepSeek quietly upgraded V4 Flash](https://www.reddit.com/r/CLine/comments/1vbt5qs/deepseek_quietly_upgraded_v4_flash/) | r/CLine | u/gargetisha | `t2_ms94y2x6` | 253 | 22 | 2026-07-31 | *not read* |
| 754 | 10.3 | post | [DeepSeek on VS Code Copilot](https://www.reddit.com/r/DeepSeek/comments/1u3zz9x/deepseek_on_vs_code_copilot/) | r/DeepSeek | u/CowReasonable8258 | `t2_krl8my5l` | 3 | 11 | 2026-06-12 | *not read* |
| 757 | 10.2 | post | [With all the issues, is the open source world actually bette](https://www.reddit.com/r/claude/comments/1vssra1/with_all_the_issues_is_the_open_source_world/) | r/claude | u/Whole_Succotash_2391 | `t2_1suofmpw53` | 1 | 12 | 2026-08-19 | *not read* |
| 758 | 10.2 | post | [Продавам AI Gateway до self-hosted изкуствен интелект - без ](https://www.reddit.com/r/bulgaria/comments/1vy43gu/продавам_ai_gateway_до_selfhosted_изкуствен/) | r/bulgaria | u/Early_Okra4794 | `t2_1ex886si4s` | 0 | 16 | 2026-08-25 | *not read* |
| 760 | 10.1 | post | [DeepSeek v4 Pro API with Cline burning tokens like crazy](https://www.reddit.com/r/DeepSeek/comments/1ttrk79/deepseek_v4_pro_api_with_cline_burning_tokens/) | r/DeepSeek | u/Ready_Performance_35 | `t2_7hqxsn53` | 4 | 4 | 2026-06-01 | *not read* |
| 767 | 10.0 | post | [You guys asked for it: my local coding agent (llama.cpp + MC](https://www.reddit.com/r/LocalLLaMA/comments/1v04rsv/you_guys_asked_for_it_my_local_coding_agent/) | r/LocalLLaMA | u/New-Inspection7034 | `t2_8vmog1me` | 0 | 13 | 2026-07-18 | *not read* |
| 769 | 9.9 | post | [Minimax m2.7 seems to be better than deepseek v4 pro](https://www.reddit.com/r/DeepSeek/comments/1t65o4f/minimax_m27_seems_to_be_better_than_deepseek_v4/) | r/DeepSeek | u/AatmanirbharNobita | `t2_7vd854ag` | 83 | 47 | 2026-05-07 | *not read* |
| 771 | 9.9 | post | [Burned through $10 in an hour](https://www.reddit.com/r/hermesagent/comments/1tqjyg8/burned_through_10_in_an_hour/) | r/hermesagent | u/ithinkilefttheovenon | `t2_jmvwb` | 88 | 136 | 2026-05-28 | *not read* |
| 772 | 9.9 | post | [How to use DeepSeek V4 PRO in Cursor? Skill issue on my side](https://www.reddit.com/r/DeepSeek/comments/1th43j0/how_to_use_deepseek_v4_pro_in_cursor_skill_issue/) | r/DeepSeek | u/BattlePhysical4105 | `t2_qco8mhf1t` | 9 | 2 | 2026-05-18 | *not read* |
| 773 | 9.9 | post | [Is DeepSeek V4 Pro expensive (without discounts)?](https://www.reddit.com/r/DeepSeek/comments/1sw80vi/is_deepseek_v4_pro_expensive_without_discounts/) | r/DeepSeek | u/LeTanLoc98 | `t2_25i76blr` | 116 | 42 | 2026-04-26 | *not read* |
| 774 | 9.8 | post | [Switched to DeepSeek V4 Pro and im happy](https://www.reddit.com/r/GithubCopilot/comments/1tnaf29/switched_to_deepseek_v4_pro_and_im_happy/) | r/GithubCopilot | u/Immediate-Jicama-462 | `t2_1irnfadwqu` | 106 | 81 | 2026-05-25 | *not read* |
| 775 | 9.8 | post | [[TLDR] Opus 5 is hot garbage [via r/Anthropic]](https://www.reddit.com/r/ClaudeCoding/comments/1vze53e/tldr_opus_5_is_hot_garbage_via_ranthropic/) | r/ClaudeCoding | u/cctldrping | `t2_2fdlgi5no6` | 4 | 0 | 2026-08-27 | *not read* |
| 776 | 9.8 | post | [Hitting 429s daily on deepseek-v4-pro (500 concurrency cap) ](https://www.reddit.com/r/DeepSeek/comments/1uv3vwk/hitting_429s_daily_on_deepseekv4pro_500/) | r/DeepSeek | u/CellistApart3564 | `t2_24532uqp04` | 0 | 11 | 2026-07-13 | *not read* |
| 779 | 9.7 | post | [Decreased Intelligence Density in DeepSeek V4 Pro](https://www.reddit.com/r/LocalLLaMA/comments/1svbmnc/decreased_intelligence_density_in_deepseek_v4_pro/) | r/LocalLLaMA | u/Mindless_Pain1860 | `t2_1bbctni0y2` | 235 | 94 | 2026-04-25 | *not read* |
| 784 | 9.7 | post | [We partnered with Runware to serve open-source models (gpt-o](https://www.reddit.com/r/LLMDevs/comments/1v8dcje/we_partnered_with_runware_to_serve_opensource/) | r/LLMDevs | u/smakosh | `t2_ppb8g9` | 1 | 2 | 2026-07-27 | *not read* |
| 785 | 9.7 | post | [Lets be real deepseek V4 pro is disappointing :(](https://www.reddit.com/r/DeepSeek/comments/1sv0hwb/lets_be_real_deepseek_v4_pro_is_disappointing/) | r/DeepSeek | u/9r4n4y | `t2_26mw3gi39y` | 0 | 36 | 2026-04-25 | *not read* |
| 786 | 9.7 | post | [deepseek v4 ignoring char lorebooks and scripts](https://www.reddit.com/r/JanitorAI_Refuges/comments/1u4ocai/deepseek_v4_ignoring_char_lorebooks_and_scripts/) | r/JanitorAI_Refuges | u/RedHotChillPepper | `t2_3ai9ismc` | 2 | 3 | 2026-06-13 | *not read* |
| 787 | 9.7 | post | [Not sure if it's just me but Deepseek V4 pro is not even clo](https://www.reddit.com/r/DeepSeek/comments/1tzrvnu/not_sure_if_its_just_me_but_deepseek_v4_pro_is/) | r/DeepSeek | u/NabilSuffla | `t2_gjfx4htd` | 36 | 24 | 2026-06-07 | *not read* |
| 788 | 9.7 | post | [How to use DeepSeek V4 in Claude Code](https://www.reddit.com/r/AtlasCloudAI/comments/1szj11y/how_to_use_deepseek_v4_in_claude_code/) | r/AtlasCloudAI | u/atlas-cloud | `t2_1k6k1ppmtz` | 2 | 0 | 2026-04-30 | *not read* |
| 789 | 9.6 | post | [DeepSeek V4 Pro-0813 benchmark sheet — leads Flash by ~10% o](https://www.reddit.com/r/opencodeCLI/comments/1vmorf4/deepseek_v4_pro0813_benchmark_sheet_leads_flash/) | r/opencodeCLI | u/lilga7ed | `t2_8a3steey6` | 26 | 4 | 2026-08-12 | *not read* |
| 790 | 9.6 | post | [Reduced DeepSeek pro limits](https://www.reddit.com/r/opencodeCLI/comments/1v5gqom/reduced_deepseek_pro_limits/) | r/opencodeCLI | u/No_Frosting363 | `t2_c78pf6kx` | 3 | 12 | 2026-07-24 | *not read* |
| 793 | 9.5 | post | [DeepSeek 4 Pro GA has an astonishing blunder.](https://www.reddit.com/r/DeepSeek/comments/1vovxxc/deepseek_4_pro_ga_has_an_astonishing_blunder/) | r/DeepSeek | u/Public_Ad_5096 | `t2_c3ty652z4` | 77 | 11 | 2026-08-15 | *not read* |
| 799 | 9.5 | post | [What todo when you hit the Claude Code limit?](https://www.reddit.com/r/ClaudeCode/comments/1vrk2ki/what_todo_when_you_hit_the_claude_code_limit/) | r/ClaudeCode | u/luongnv-com | `t2_21lq4yvk26` | 0 | 28 | 2026-08-18 | *not read* |
| 801 | 9.4 | post | [Using deepseek-v4-pro seems like cheating.](https://www.reddit.com/r/DeepSeek/comments/1uy1z4i/using_deepseekv4pro_seems_like_cheating/) | r/DeepSeek | u/AlexHardy08 | `t2_1a56cpsb4d` | 88 | 28 | 2026-07-16 | *not read* |
| 803 | 9.3 | post | [Why does DeepSeek V4 Pro feel so much less capable than GPT-](https://www.reddit.com/r/DeepSeek/comments/1uwz2uv/why_does_deepseek_v4_pro_feel_so_much_less/) | r/DeepSeek | u/Capital_Feed_3473 | `t2_1pyn3o1zoe` | 65 | 60 | 2026-07-15 | *not read* |
| 806 | 9.2 | post | [How can I get DeepSeek V4 Pro to handle images in an AI agen](https://www.reddit.com/r/AI_Agents/comments/1uv4b3k/how_can_i_get_deepseek_v4_pro_to_handle_images_in/) | r/AI_Agents | u/Porn197617_ | `t2_24jk0x757z` | 3 | 6 | 2026-07-13 | *not read* |
| 807 | 9.2 | post | [How do u even use ur api key???](https://www.reddit.com/r/DeepSeek/comments/1swfkt1/how_do_u_even_use_ur_api_key/) | r/DeepSeek | u/Throwawayyyy473993 | `t2_10ys938uoc` | 19 | 10 | 2026-04-26 | *not read* |
| 808 | 9.2 | post | [How to run Claude Code for free! Full setup](https://www.reddit.com/r/ClaudeCode/comments/1t8mo2u/how_to_run_claude_code_for_free_full_setup/) | r/ClaudeCode | u/Veerbhadra_1 | `t2_1rnr595f5o` | 0 | 12 | 2026-05-09 | *not read* |
| 809 | 9.1 | post | [DeepSeek V4 Pro just dropped — is anyone actually using Chin](https://www.reddit.com/r/GithubCopilot/comments/1su7721/deepseek_v4_pro_just_dropped_is_anyone_actually/) | r/GithubCopilot | u/Resident-Rise-5112 | `t2_e87zb2dy` | 72 | 90 | 2026-04-24 | *not read* |
| 810 | 9.1 | post | [DeepSeek-V4-Pro-0813 GGUFs are up](https://www.reddit.com/r/unsloth/comments/1vnwtw5/deepseekv4pro0813_ggufs_are_up/) | r/unsloth | u/danielhanchen | `t2_5wukhd4` | 110 | 10 | 2026-08-14 | *not read* |
| 812 | 9.1 | post | [OpenRouter + DeepSeek V4 Pro is cheap, but people didn’t men](https://www.reddit.com/r/GithubCopilot/comments/1tnk5vi/openrouter_deepseek_v4_pro_is_cheap_but_people/) | r/GithubCopilot | u/yami_odymel | `t2_166pit` | 124 | 39 | 2026-05-25 | *not read* |
| 818 | 9.0 | post | ["DeepSeek-V4-Flash Official API is now LIVE in public beta! ](https://www.reddit.com/r/accelerate/comments/1vbkda6/deepseekv4flash_official_api_is_now_live_in/) | r/accelerate | u/stealthispost | `t2_48o6p` | 49 | 9 | 2026-07-31 | *not read* |
| 819 | 9.0 | post | [Stab's Directives Preset 2.62- stability and cleanup, DeepSe](https://www.reddit.com/r/SillyTavernAI/comments/1sz0od5/stabs_directives_preset_262_stability_and_cleanup/) | r/SillyTavernAI | u/Diecron | `t2_4s8mt` | 75 | 21 | 2026-04-29 | *not read* |
| 822 | 8.9 | post | [Deepseek v4 flash 0731 real experience. It is definitely sho](https://www.reddit.com/r/DeepSeek/comments/1vc4ocr/deepseek_v4_flash_0731_real_experience_it_is/) | r/DeepSeek | u/No_Tip9917 | `t2_j6vxa7mg` | 224 | 112 | 2026-07-31 | *not read* |
| 825 | 8.9 | post | [DeepSeek is cooking something MASSIVE — and deepseek-v4-pro ](https://www.reddit.com/r/DeepSeek/comments/1ubmwcg/deepseek_is_cooking_something_massive_and/) | r/DeepSeek | u/bala221240 | `t2_4dlwtt1c` | 0 | 27 | 2026-06-21 | *not read* |
| 826 | 8.9 | post | [DeepSeek V4 went GA. My ClawBox switched over on its own thi](https://www.reddit.com/r/DeepSeek/comments/1vo82g2/deepseek_v4_went_ga_my_clawbox_switched_over_on/) | r/DeepSeek | u/PetarInTheBox | `t2_2knj1tulwl` | 0 | 1 | 2026-08-14 | *not read* |
| 831 | 8.9 | post | [Minimax m2.7 seems to be better than deepseek v4 pro.](https://www.reddit.com/r/MiniMax_AI/comments/1t65ncd/minimax_m27_seems_to_be_better_than_deepseek_v4/) | r/MiniMax_AI | u/AatmanirbharNobita | `t2_7vd854ag` | 16 | 8 | 2026-05-07 | *not read* |
| 832 | 8.9 | post | [OpenCode + DeepSeek V4 Pro vs Claude Code CLI?🤔](https://www.reddit.com/r/AI_Agents/comments/1taoqtd/opencode_deepseek_v4_pro_vs_claude_code_cli/) | r/AI_Agents | u/Raiyan-Hussain | `t2_qa4g8m3z` | 3 | 11 | 2026-05-12 | *not read* |
| 833 | 8.9 | post | [[AI DAILY NEWS RUNDOWN] Pre-Release Model Checks, Anthropic'](https://www.reddit.com/r/u_enoumen/comments/1te8sev/ai_daily_news_rundown_prerelease_model_checks/) | r/u_enoumen | u/enoumen | `t2_8u0no` | 1 | 1 | 2026-05-15 | *not read* |
| 837 | 8.8 | post | [Has anyone tried DeepSeek v4 Pro &amp; Flash for coding in I](https://www.reddit.com/r/DeepSeek/comments/1sxnvg2/has_anyone_tried_deepseek_v4_pro_flash_for_coding/) | r/DeepSeek | u/reverse-linkedlist | `t2_1qchf25wpn` | 1 | 1 | 2026-04-28 | *not read* |
| 840 | 8.7 | post | [DeepSeek v4 Pro is too big for such a "midrange" performance](https://www.reddit.com/r/LocalLLaMA/comments/1u4yvqy/deepseek_v4_pro_is_too_big_for_such_a_midrange/) | r/LocalLLaMA | u/ihatebeinganonymous | `t2_127kho` | 108 | 66 | 2026-06-13 | *not read* |
| 846 | 8.7 | post | [Confused by Deepseek v4 Pro pricing](https://www.reddit.com/r/opencodeCLI/comments/1tgeh27/confused_by_deepseek_v4_pro_pricing/) | r/opencodeCLI | u/molovo | `t2_ahi8s` | 7 | 7 | 2026-05-18 | *not read* |
| 848 | 8.7 | post | [DeepSeek V4 vs GLM 5.2 for coding: same task on both, here i](https://www.reddit.com/r/opencodeCLI/comments/1v2cjgt/deepseek_v4_vs_glm_52_for_coding_same_task_on/) | r/opencodeCLI | u/Fun_Walk_4965 | `t2_2aahp8ezxn` | 0 | 14 | 2026-07-21 | *not read* |
| 850 | 8.7 | post | [Halting after "&lt;｜DSML｜" thinking output](https://www.reddit.com/r/CrofAI/comments/1uau2p7/halting_after_dsml_thinking_output/) | r/CrofAI | u/TomHale | `t2_bc3fr` | 3 | 0 | 2026-06-20 | *not read* |
| 851 | 8.6 | post | [Okay… DeepSeek V4 Pro 0813 actually looks kinda crazy](https://www.reddit.com/r/DeepSeek/comments/1vmy66e/okay_deepseek_v4_pro_0813_actually_looks_kinda/) | r/DeepSeek | u/Several_Fly694 | `t2_vcjyedop7` | 185 | 63 | 2026-08-13 | *not read* |
| 853 | 8.6 | post | [Claude code and security TRIGGERS MESS](https://www.reddit.com/r/ClaudeCode/comments/1vi5dbp/claude_code_and_security_triggers_mess/) | r/ClaudeCode | u/Comfortable-Catch576 | `t2_19uz22cchs` | 2 | 4 | 2026-08-07 | *not read* |
| 855 | 8.6 | post | [Baidu ERNIE 5.1 Brings Big Efficiency Gains Without Losing P](https://www.reddit.com/r/aicuriosity/comments/1t7u97m/baidu_ernie_51_brings_big_efficiency_gains/) | r/aicuriosity | u/techspecsmart | `t2_biy7bjdv` | 22 | 8 | 2026-05-09 | *not read* |
| 856 | 8.6 | post | [Deepseek... seems worse now, right?](https://www.reddit.com/r/AIDungeon/comments/1txrhpw/deepseek_seems_worse_now_right/) | r/AIDungeon | u/CaptainLSS | `t2_5c4ncu0c` | 59 | 29 | 2026-06-05 | *not read* |
| 859 | 8.5 | post | [Spec driven web scraping projects with Scrapy](https://www.reddit.com/r/Zyte/comments/1tfxxj4/spec_driven_web_scraping_projects_with_scrapy/) | r/Zyte | u/jwrdev | `t2_2d9w5a51zq` | 4 | 2 | 2026-05-17 | *not read* |
| 860 | 8.5 | post | [DeepSeek-V4 Preview is officially live](https://www.reddit.com/r/aigossips/comments/1su4lsg/deepseekv4_preview_is_officially_live/) | r/aigossips | u/call_me_ninza | `t2_dbbedhcv` | 9 | 0 | 2026-04-24 | *not read* |
| 862 | 8.5 | post | [What do you use when you hit your Claude Code limit?](https://www.reddit.com/r/ClaudeCode/comments/1u9oeaa/what_do_you_use_when_you_hit_your_claude_code/) | r/ClaudeCode | u/thearcher182 | `t2_1q6nnsly` | 6 | 22 | 2026-06-19 | *not read* |
| 869 | 8.5 | post | [QWEN3.8-Flash using an AI Harness](https://www.reddit.com/r/Qwen_AI/comments/1vzng1w/qwen38flash_using_an_ai_harness/) | r/Qwen_AI | u/angrynoodles0 | `t2_jqebz2uyp` | 2 | 5 | 2026-08-27 | *not read* |
| 870 | 8.4 | post | [Fixing Overthinking](https://www.reddit.com/r/DeepSeek/comments/1vzwr8q/fixing_overthinking/) | r/DeepSeek | u/Eddlm_ | `t2_er11r` | 22 | 4 | 2026-08-27 | *not read* |
| 875 | 8.3 | post | [GitHub Pro+ (Old Plan) + Claude Pro + DeepSeek V4 -&gt; Kimi](https://www.reddit.com/r/kimi/comments/1vm77k5/github_pro_old_plan_claude_pro_deepseek_v4_kimi/) | r/kimi | u/littlebitofkindness | `t2_b3ree28a` | 3 | 27 | 2026-08-12 | *not read* |
| 879 | 8.2 | post | [HermesAgent for use-case Sales (with self-hosted Hermes, + s](https://www.reddit.com/r/hermesagent/comments/1ug5fae/hermesagent_for_usecase_sales_with_selfhosted/) | r/hermesagent | u/jean-jcrx | `t2_2h1p8yru3l` | 1 | 0 | 2026-06-26 | *not read* |
| 880 | 8.2 | post | [Copilot BYOK → OpenRouter → DeepSeek V4 Pro: Agent tool call](https://www.reddit.com/r/GithubCopilot/comments/1su7ekc/copilot_byok_openrouter_deepseek_v4_pro_agent/) | r/GithubCopilot | u/Altruistic-Dust-2565 | `t2_5kqre3i8` | 19 | 17 | 2026-04-24 | *not read* |
| 881 | 8.2 | post | [DeepSeek V4 Flash reaches #7 in Arena’s frontend coding benc](https://www.reddit.com/r/AIGuild/comments/1ve1lak/deepseek_v4_flash_reaches_7_in_arenas_frontend/) | r/AIGuild | u/Such-Run-4412 | `t2_qdhmdvza` | 3 | 1 | 2026-08-03 | *not read* |
| 882 | 8.2 | post | [Why pay for GO when Qwen 3.6 is free? (Genuine Question)](https://www.reddit.com/r/opencodeCLI/comments/1thkj75/why_pay_for_go_when_qwen_36_is_free_genuine/) | r/opencodeCLI | u/Funny-Strawberry-168 | `t2_am4k3lnu` | 93 | 85 | 2026-05-19 | *not read* |
| 883 | 8.2 | post | [Is MLRPE prompt good?](https://www.reddit.com/r/TAVO_AICHAT/comments/1u1547z/is_mlrpe_prompt_good/) | r/TAVO_AICHAT | u/DimensionalTemplar | `t2_2rpvq2yb` | 9 | 6 | 2026-06-09 | *not read* |
| 885 | 8.1 | post | [Qwen is never going to open source Qwen 3.7, aren't they?](https://www.reddit.com/r/LocalLLaMA/comments/1ubjnh5/qwen_is_never_going_to_open_source_qwen_37_arent/) | r/LocalLLaMA | u/DistanceSolar1449 | `t2_1utnp17o3h` | 564 | 357 | 2026-06-21 | *not read* |
| 886 | 8.1 | post | [the average cost per request for deepseek-v4-pro-0813 on Com](https://www.reddit.com/r/opencode/comments/1vn7dqw/the_average_cost_per_request_for/) | r/opencode | u/No-Budget-3869 | `t2_e8akzuo23` | 15 | 12 | 2026-08-13 | *not read* |
| 888 | 8.1 | post | [Announcement⭐️ and  LoreMate is  taking new Beta Testers](https://www.reddit.com/r/LoreMateAI/comments/1tmdc48/announcement_and_loremate_is_taking_new_beta/) | r/LoreMateAI | u/me_broke | `t2_wl005y3or` | 37 | 57 | 2026-05-24 | *not read* |
| 893 | 8.0 | post | [[Workflow] Workflow for Evaluating LLM Harnesses: Comparing ](https://www.reddit.com/r/ClaudeWorkflows/comments/1uz98uw/workflow_workflow_for_evaluating_llm_harnesses/) | r/ClaudeWorkflows | u/ClaudeAI-mod-bot | `t2_1vs6v2gkb0` | 1 | 0 | 2026-07-17 | *not read* |
| 894 | 8.0 | post | [[Workflow] Workflow for Evaluating LLM Harnesses: Comparing ](https://www.reddit.com/r/ClaudeWorkflows/comments/1uz5mge/workflow_workflow_for_evaluating_llm_harnesses/) | r/ClaudeWorkflows | u/ClaudeAI-mod-bot | `t2_1vs6v2gkb0` | 1 | 0 | 2026-07-17 | *not read* |
| 895 | 8.0 | post | [Deepseek v4 pro is both a genius and a lunatic](https://www.reddit.com/r/DeepSeek/comments/1vmr5qt/deepseek_v4_pro_is_both_a_genius_and_a_lunatic/) | r/DeepSeek | u/Barquish | `t2_9pd99i5w` | 40 | 15 | 2026-08-12 | *not read* |
| 897 | 7.9 | post | [I gave DeepSeek V4 Pro a mission impossible and told it to k](https://www.reddit.com/r/DeepSeek/comments/1t1m3kz/i_gave_deepseek_v4_pro_a_mission_impossible_and/) | r/DeepSeek | u/award_reply | `t2_22ubsoz0gm` | 512 | 37 | 2026-05-02 | *not read* |
| 899 | 7.9 | post | [DeepSeek V4 Pro 0813 (latest) is live in Command Code.](https://www.reddit.com/r/CommandCode/comments/1vmkrfe/deepseek_v4_pro_0813_latest_is_live_in_command/) | r/CommandCode | u/maedahbatool | `t2_s3g4io7` | 86 | 11 | 2026-08-12 | *not read* |
| 900 | 7.9 | post | [Same demo, two failures on DeepSeek V4 Pro 0813, then V4 Fla](https://www.reddit.com/r/artificial/comments/1vo5x4i/same_demo_two_failures_on_deepseek_v4_pro_0813/) | r/artificial | u/neverontime5 | `t2_2fpdo0zrrn` | 0 | 3 | 2026-08-14 | *not read* |
| 902 | 7.9 | post | [Inconsistency](https://www.reddit.com/r/hermesagent/comments/1u2tj0y/inconsistency/) | r/hermesagent | u/cyber-sack | `t2_hjdg984` | 1 | 12 | 2026-06-11 | *not read* |
| 905 | 7.9 | post | [Insanely high token usage and pricing for no output?](https://www.reddit.com/r/CommandCode/comments/1vtewsq/insanely_high_token_usage_and_pricing_for_no/) | r/CommandCode | u/Dub-DS | `t2_cb3cp` | 20 | 14 | 2026-08-20 | *not read* |
| 906 | 7.8 | post | [Anyone else experiencing "Invalid documentID" with Knowledge](https://www.reddit.com/r/TypingMind/comments/1vqhhki/anyone_else_experiencing_invalid_documentid_with/) | r/TypingMind | u/Wattson1216 | `t2_mthqvuqn` | 1 | 2 | 2026-08-17 | *not read* |
| 907 | 7.8 | post | [GLM 5.1 vs Deepseek V4 Pro? Is switching to the latter worth](https://www.reddit.com/r/SillyTavernAI/comments/1u6lnb8/glm_51_vs_deepseek_v4_pro_is_switching_to_the/) | r/SillyTavernAI | u/Afraid_Brain4350 | `t2_23ysz1zdqh` | 12 | 24 | 2026-06-15 | *not read* |
| 909 | 7.8 | post | [DeepSeek V4-Flash 0731 made previously working prompts fail.](https://www.reddit.com/r/SillyTavernAI/comments/1vcbf9x/deepseek_v4flash_0731_made_previously_working/) | r/SillyTavernAI | u/mad-yordle | `t2_4t5yy2ud` | 68 | 37 | 2026-08-01 | *not read* |
| 911 | 7.7 | post | [Does the $1 Command Code "Go" plan include the new DeepSeek ](https://www.reddit.com/r/CommandCode/comments/1vj0f1x/does_the_1_command_code_go_plan_include_the_new/) | r/CommandCode | u/PhyoThiHA0805 | `t2_drgasedo` | 8 | 13 | 2026-08-08 | *not read* |
| 916 | 7.5 | post | [Is DeepSeek V4 Pro already good enough for everyday coding?](https://www.reddit.com/r/DeepSeek/comments/1ts0cea/is_deepseek_v4_pro_already_good_enough_for/) | r/DeepSeek | u/SiteSpecialist6295 | `t2_4yamdaael` | 84 | 73 | 2026-05-30 | *not read* |
| 923 | 7.5 | post | [Which ide for Deepseek V4 Pro api ?](https://www.reddit.com/r/DeepSeek/comments/1tt9ksn/which_ide_for_deepseek_v4_pro_api/) | r/DeepSeek | u/KamizuMC | `t2_738x8k1i` | 15 | 31 | 2026-05-31 | *not read* |
| 925 | 7.5 | post | [I can only use DeepSeek Coder - error when I try to use v4 P](https://www.reddit.com/r/DeepSeek/comments/1sw6j4a/i_can_only_use_deepseek_coder_error_when_i_try_to/) | r/DeepSeek | u/OutrageousTrue | `t2_yhoe9vpkw` | 2 | 6 | 2026-04-26 | *not read* |
| 926 | 7.4 | post | [DeepSeek V4 rilasciata oggi (24 aprile 2026): note tecniche ](https://www.reddit.com/r/IA_Italia/comments/1suc1hd/deepseek_v4_rilasciata_oggi_24_aprile_2026_note/) | r/IA_Italia | u/artistic56 | `t2_a3x4sfwa` | 5 | 1 | 2026-04-24 | *not read* |
| 928 | 7.3 | post | [Tried deepseek v4 pro as a replacement to gpt 5.5, probably ](https://www.reddit.com/r/DeepSeek/comments/1u9vrc3/tried_deepseek_v4_pro_as_a_replacement_to_gpt_55/) | r/DeepSeek | u/Kazaan | `t2_6kmh9` | 293 | 78 | 2026-06-19 | *not read* |
| 930 | 7.3 | post | [DeepSeek "🚀 DeepSeek-V4 Preview is officially live &amp; ope](https://www.reddit.com/r/LovingAIAgents/comments/1svf4sa/deepseek_deepseekv4_preview_is_officially_live/) | r/LovingAIAgents | u/Koala_Confused | `t2_svnji` | 10 | 0 | 2026-04-25 | *not read* |
| 931 | 7.3 | post | [DeepSeek "🚀 DeepSeek-V4 Preview is officially live &amp; ope](https://www.reddit.com/r/LovingOpenSourceAI/comments/1svf0c0/deepseek_deepseekv4_preview_is_officially_live/) | r/LovingOpenSourceAI | u/Koala_Confused | `t2_svnji` | 3 | 0 | 2026-04-25 | *not read* |
| 932 | 7.3 | post | [Using DeepSeek V4 Pro in Paseo](https://www.reddit.com/r/DeepSeek/comments/1tlczkl/using_deepseek_v4_pro_in_paseo/) | r/DeepSeek | u/PiccoloCareful924 | `t2_z8h5yohez` | 42 | 18 | 2026-05-23 | *not read* |
| 939 | 7.2 | post | [DeepSeek V4 Pro + Cline: infinite reasoning loop + suggestio](https://www.reddit.com/r/CLine/comments/1tasgfm/deepseek_v4_pro_cline_infinite_reasoning_loop/) | r/CLine | u/Immediate-Practice48 | `t2_9j882wkm` | 5 | 8 | 2026-05-12 | *not read* |
| 940 | 7.2 | post | [What's the verdict on Kimi K3, Qwen3.8-2.4T, DeepSeekV4Pro-0](https://www.reddit.com/r/LocalLLaMA/comments/1vrupyu/whats_the_verdict_on_kimi_k3_qwen3824t/) | r/LocalLLaMA | u/segmond | `t2_ah13x` | 10 | 22 | 2026-08-18 | *not read* |
| 941 | 7.1 | post | [DeepSeek silently released V4-Pro 0813, now available in Cli](https://www.reddit.com/r/CLine/comments/1vmmop4/deepseek_silently_released_v4pro_0813_now/) | r/CLine | u/gargetisha | `t2_ms94y2x6` | 159 | 15 | 2026-08-12 | *not read* |
| 942 | 7.1 | post | [AI Roundup — Jun 08: Apple rebuilds Siri on Gemini, DeepSeek](https://www.reddit.com/r/AIToolsTipsNews/comments/1u07dy2/ai_roundup_jun_08_apple_rebuilds_siri_on_gemini/) | r/AIToolsTipsNews | u/ayushchat | `t2_4ehwncvo` | 2 | 1 | 2026-06-08 | *not read* |
| 947 | 7.0 | post | [DeepSeek V4 Pro vs Gemini 3.0 Pro - intelligence density is ](https://www.reddit.com/r/AIToolsPerformance/comments/1svhqvy/deepseek_v4_pro_vs_gemini_30_pro_intelligence/) | r/AIToolsPerformance | u/IulianHI | `t2_10nqfcv1` | 3 | 6 | 2026-04-25 | *not read* |
| 948 | 7.0 | post | [From Claude Code/Opus 5.8 to OpenCode/DeepSeek Pro V4](https://www.reddit.com/r/opencode/comments/1udk9md/from_claude_codeopus_58_to_opencodedeepseek_pro_v4/) | r/opencode | u/lostforever2011 | `t2_fgmxk` | 21 | 30 | 2026-06-23 | *not read* |
| 949 | 7.0 | post | [Opening Vibe to third-party models is exactly the right move](https://www.reddit.com/r/MistralAI/comments/1vwk3hk/opening_vibe_to_thirdparty_models_is_exactly_the/) | r/MistralAI | u/Confident-Village190 | `t2_28fcdnritr` | 103 | 62 | 2026-08-23 | *not read* |
| 954 | 6.7 | post | [DeepSeek V4 Pro got cheaper for Enterprises requiring ZDR](https://www.reddit.com/r/DeepSeek/comments/1vpqstm/deepseek_v4_pro_got_cheaper_for_enterprises/) | r/DeepSeek | u/Endoky | `t2_3hwtfwal` | 11 | 12 | 2026-08-16 | *not read* |
| 957 | 6.7 | post | [The same model on OpenRouter is five different products and ](https://www.reddit.com/r/openrouter/comments/1u1z03a/the_same_model_on_openrouter_is_five_different/) | r/openrouter | u/FiLo420blazeit | `t2_bnopo8gc` | 52 | 14 | 2026-06-10 | *not read* |
| 960 | 6.6 | post | [DeepSeek v4 pro benchmark](https://www.reddit.com/r/opencodeCLI/comments/1vmiox0/deepseek_v4_pro_benchmark/) | r/opencodeCLI | u/minxio_ | `t2_1r2y42s9tb` | 55 | 5 | 2026-08-12 | *not read* |
| 963 | 6.5 | post | [DeepSeek v4 Pro vs GLM 5.2 vs Fable 5](https://www.reddit.com/r/CommandCode/comments/1umm8zm/deepseek_v4_pro_vs_glm_52_vs_fable_5/) | r/CommandCode | u/Silent-Group1187 | `t2_8qn5wz8g` | 246 | 28 | 2026-07-03 | *not read* |
| 964 | 6.5 | post | [Issue with Deepseek v4 Pro API](https://www.reddit.com/r/CommandCode/comments/1vn851s/issue_with_deepseek_v4_pro_api/) | r/CommandCode | u/Sweet-Stage938 | `t2_vzvv52ly` | 3 | 6 | 2026-08-13 | *not read* |
| 965 | 6.5 | post | [Deepseek V4 Pro returns response in 'thinking'](https://www.reddit.com/r/SillyTavernAI/comments/1ti8ubk/deepseek_v4_pro_returns_response_in_thinking/) | r/SillyTavernAI | u/No_Application4175 | `t2_mbtsaa1s` | 10 | 2 | 2026-05-20 | *not read* |
| 966 | 6.5 | post | [Deepseek v4 greenery issue](https://www.reddit.com/r/JanitorAI_Refuges/comments/1ujanrq/deepseek_v4_greenery_issue/) | r/JanitorAI_Refuges | u/EbbAffectionate7578 | `t2_242v1gl5xl` | 2 | 2 | 2026-06-30 | *not read* |
| 970 | 6.5 | post | [What is the real pricing of DeepSeek V4 Pro and MiMo2.5Pro i](https://www.reddit.com/r/opencode/comments/1u99kh5/what_is_the_real_pricing_of_deepseek_v4_pro_and/) | r/opencode | u/Francespo | `t2_1ha5ihhbol` | 35 | 29 | 2026-06-18 | *not read* |
| 973 | 6.4 | post | [I’m here to bring you the Weekly SillyTavern News Ep. 3: Dee](https://www.reddit.com/r/SillyTavernAI/comments/1sxz3zo/im_here_to_bring_you_the_weekly_sillytavern_news/) | r/SillyTavernAI | u/dptgreg | `t2_4r62jhfl` | 219 | 39 | 2026-04-28 | *not read* |
| 974 | 6.4 | post | [A graph of autonomous DeepSeek V4 Pro agents is scoring SOTA](https://www.reddit.com/r/DeepSeek/comments/1v9im0o/a_graph_of_autonomous_deepseek_v4_pro_agents_is/) | r/DeepSeek | u/caelum19 | `t2_7pi81` | 48 | 4 | 2026-07-29 | *not read* |
| 978 | 6.3 | post | [🐋 New Experimental Model: DeepSeek V4 Pro 0813](https://www.reddit.com/r/AIDungeon/comments/1vtxfzw/new_experimental_model_deepseek_v4_pro_0813/) | r/AIDungeon | u/latitude_official | `t2_ugspbkxi` | 0 | 27 | 2026-08-20 | *not read* |
| 979 | 6.3 | post | [DeepSeek V4 Pro seemed to become incredibly 'stupid' since y](https://www.reddit.com/r/DeepSeek/comments/1tqbe65/deepseek_v4_pro_seemed_to_become_incredibly/) | r/DeepSeek | u/afanasenka | `t2_1qo7eszg6y` | 78 | 46 | 2026-05-28 | *not read* |
| 980 | 6.3 | post | [DeepSeek V4 Pro seemed to become incredibly 'stupid' since y](https://www.reddit.com/r/opencodeCLI/comments/1tpy9f3/deepseek_v4_pro_seemed_to_become_incredibly/) | r/opencodeCLI | u/afanasenka | `t2_1qo7eszg6y` | 17 | 30 | 2026-05-28 | *not read* |
| 981 | 6.3 | post | [Deepseek V4 pro is kinda mid](https://www.reddit.com/r/LLMDevs/comments/1uvdp21/deepseek_v4_pro_is_kinda_mid/) | r/LLMDevs | u/Annual_Ad7270 | `t2_b9q0h4dm` | 0 | 4 | 2026-07-13 | *not read* |
| 986 | 6.2 | post | [GitHub Copilot is moving to token-based billing on June 1 — ](https://www.reddit.com/r/GithubCopilot/comments/1sx8jf9/github_copilot_is_moving_to_tokenbased_billing_on/) | r/GithubCopilot | u/serious_cod69 | `t2_13n504k8jk` | 9 | 20 | 2026-04-27 | *not read* |
| 989 | 6.2 | post | [As an agent dev, which open-weight LLM is currently your def](https://www.reddit.com/r/DeepSeek/comments/1ud5fmj/as_an_agent_dev_which_openweight_llm_is_currently/) | r/DeepSeek | u/Independent-Date393 | `t2_2aao46x3qu` | 36 | 27 | 2026-06-23 | *not read* |
| 990 | 6.2 | post | [I am trying to like DeepSeek V4 Pro but ... it just doesn´t ](https://www.reddit.com/r/SillyTavernAI/comments/1t1qjqr/i_am_trying_to_like_deepseek_v4_pro_but_it_just/) | r/SillyTavernAI | u/HrothgarLover | `t2_lrlpao0h` | 50 | 45 | 2026-05-02 | *not read* |
| 991 | 6.2 | post | [Does DeepSeek V4 actually support vision / image input?](https://www.reddit.com/r/DeepSeek/comments/1trw8j1/does_deepseek_v4_actually_support_vision_image/) | r/DeepSeek | u/Otherwise_Lunch_1239 | `t2_8cr5jeur` | 2 | 11 | 2026-05-30 | *not read* |
| 993 | 6.1 | post | [Do you think DeepSeek V4 series will still be improved?](https://www.reddit.com/r/DeepSeek/comments/1sx0o49/do_you_think_deepseek_v4_series_will_still_be/) | r/DeepSeek | u/C_8urun | `t2_mmd011af` | 2 | 4 | 2026-04-27 | *not read* |
| 996 | 6.1 | post | [DeepSeek Rolls Out V4 Pro With Stronger Agent Skills and Fle](https://www.reddit.com/r/aicuriosity/comments/1vngup0/deepseek_rolls_out_v4_pro_with_stronger_agent/) | r/aicuriosity | u/techspecsmart | `t2_biy7bjdv` | 7 | 0 | 2026-08-13 | *not read* |
| 1000 | 6.0 | post | [Kimi K3 vs DeepSeek V4 Pro vs GLM-5.2: Open Trillion-Scale M](https://www.reddit.com/r/AIDeveloperNews/comments/1v0dmzw/kimi_k3_vs_deepseek_v4_pro_vs_glm52_open/) | r/AIDeveloperNews | u/ai-lover | `t2_2wsvqwhg` | 5 | 0 | 2026-07-19 | *not read* |
| 1001 | 6.0 | post | [Free API credits for DeepSeek V4, Kimi K2, and other open-we](https://www.reddit.com/r/AI_Agents/comments/1v8tby7/free_api_credits_for_deepseek_v4_kimi_k2_and/) | r/AI_Agents | u/Individual_Team_2344 | `t2_1r9s6rc26v` | 3 | 21 | 2026-07-28 | *not read* |
| 1002 | 6.0 | post | [Has the price for deepseek-v4-pro on opencode go already bee](https://www.reddit.com/r/opencode/comments/1todc5z/has_the_price_for_deepseekv4pro_on_opencode_go/) | r/opencode | u/TigerBeanst | `t2_dkdzlqi7` | 21 | 9 | 2026-05-26 | *not read* |
| 1004 | 6.0 | post | [I think I have reached my limit](https://www.reddit.com/r/vibecoding/comments/1ve9fah/i_think_i_have_reached_my_limit/) | r/vibecoding | u/Jazzlike_Bee_3129 | `t2_1ztzr97dvo` | 51 | 204 | 2026-08-03 | *not read* |
| 1008 | 5.9 | post | [We need to gate keep the API](https://www.reddit.com/r/DeepSeek/comments/1tx1ddb/we_need_to_gate_keep_the_api/) | r/DeepSeek | u/TookitTooFarOrDidI | `t2_1edxrdgguz` | 0 | 39 | 2026-06-04 | *not read* |
| 1009 | 5.9 | post | [Big Model Value Wars - DeepSeek V4 Pro vs MiMo-V2.5-Pro vs M](https://www.reddit.com/r/LocalLLaMA/comments/1tvzoly/big_model_value_wars_deepseek_v4_pro_vs/) | r/LocalLLaMA | u/valtor2 | `t2_33z5a` | 21 | 13 | 2026-06-03 | *not read* |
| 1010 | 5.9 | post | [How usable is the 20$ plan rn? Thinking about Claude Code vs](https://www.reddit.com/r/ClaudeCode/comments/1vbvwwh/how_usable_is_the_20_plan_rn_thinking_about/) | r/ClaudeCode | u/zubrzysta | `t2_15ygtv` | 2 | 14 | 2026-07-31 | *not read* |
| 1011 | 5.8 | post | [DeepSeek-V4-Pro-0813 Safety Filters](https://www.reddit.com/r/DeepSeek/comments/1vvhpgz/deepseekv4pro0813_safety_filters/) | r/DeepSeek | u/Silens___ | `t2_q9pjy11v` | 47 | 22 | 2026-08-22 | *not read* |
| 1012 | 5.8 | post | [New Voyage Experimental Models: DeepSeek V4 Pro 0813 and Qwe](https://www.reddit.com/r/Voyage/comments/1vxmeue/new_voyage_experimental_models_deepseek_v4_pro/) | r/Voyage | u/latitude_official | `t2_ugspbkxi` | 6 | 1 | 2026-08-25 | *not read* |
| 1015 | 5.8 | post | [Question about billing variability: OpenRouter vs official D](https://www.reddit.com/r/hermesagent/comments/1vepsy2/question_about_billing_variability_openrouter_vs/) | r/hermesagent | u/muer-d | `t2_3dcizanv` | 3 | 6 | 2026-08-03 | *not read* |
| 1016 | 5.7 | post | [Deepseek V4 Pro is AMAZING](https://www.reddit.com/r/DeepSeek/comments/1v2dwel/deepseek_v4_pro_is_amazing/) | r/DeepSeek | u/des369 | `t2_2ilzwu3bzn` | 477 | 98 | 2026-07-21 | *not read* |
| 1020 | 5.7 | post | [New Deepseek v4 Pro 0813 is weaker than Flash 0731 in benchm](https://www.reddit.com/r/opencodeCLI/comments/1vn648j/new_deepseek_v4_pro_0813_is_weaker_than_flash/) | r/opencodeCLI | u/Mayanktaker | `t2_mmr41` | 0 | 27 | 2026-08-13 | *not read* |
| 1021 | 5.7 | post | [Tested DeepSeek V4 Pro (0813) on coding with OpenCode &amp; ](https://www.reddit.com/r/LocalLLaMA/comments/1vnci9h/tested_deepseek_v4_pro_0813_on_coding_with/) | r/LocalLLaMA | u/curiousily_ | `t2_fztx5xf` | 0 | 19 | 2026-08-13 | *not read* |
| 1025 | 5.7 | post | [Anyone else getting constant 429s with DeepSeek V4 on OpenRo](https://www.reddit.com/r/GithubCopilot/comments/1syw5rj/anyone_else_getting_constant_429s_with_deepseek/) | r/GithubCopilot | u/DdongSim | `t2_1x7ew81dzt` | 2 | 16 | 2026-04-29 | *not read* |
| 1028 | 5.7 | post | [Deepseek vs Claude](https://www.reddit.com/r/BDDevs/comments/1tw6qkh/deepseek_vs_claude/) | r/BDDevs | u/angelsmith129 | `t2_tuvq2yjt` | 6 | 8 | 2026-06-03 | *not read* |
| 1029 | 5.7 | post | [“Two frontier models dropped on the same day, both swinging ](https://www.reddit.com/r/LLM/comments/1vnjp81/two_frontier_models_dropped_on_the_same_day_both/) | r/LLM | u/UnfairStatement22 | `t2_aydxclru6` | 4 | 1 | 2026-08-13 | *not read* |
| 1030 | 5.6 | post | [DeepSeek V4 Pro 0813 is so peak](https://www.reddit.com/r/SillyTavernAI/comments/1vq5lup/deepseek_v4_pro_0813_is_so_peak/) | r/SillyTavernAI | u/ZombieBlaster21 | `t2_teni5b05` | 68 | 65 | 2026-08-16 | *not read* |
| 1032 | 5.6 | post | [DeepSeek V4 Pro is now supported in Verdent](https://www.reddit.com/r/Verdent/comments/1ug2d7f/deepseek_v4_pro_is_now_supported_in_verdent/) | r/Verdent | u/verdent_ai | `t2_1zgwm653j2` | 1 | 0 | 2026-06-26 | *not read* |
| 1035 | 5.5 | post | [Deepseek V4 pro on the official API right now is definitely ](https://www.reddit.com/r/DeepSeek/comments/1usjwbn/deepseek_v4_pro_on_the_official_api_right_now_is/) | r/DeepSeek | u/Comfortable-Rock-498 | `t2_1fgqktr8tp` | 249 | 68 | 2026-07-10 | *not read* |
| 1036 | 5.5 | post | [Best coding agent for DeepSeek V4 Pro API](https://www.reddit.com/r/DeepSeek/comments/1ur6ocm/best_coding_agent_for_deepseek_v4_pro_api/) | r/DeepSeek | u/PlantQueasy8958 | `t2_2h9uokq0lt` | 82 | 71 | 2026-07-08 | *not read* |
| 1037 | 5.5 | post | [Do you trust the flash versions of AI models ?](https://www.reddit.com/r/DeepSeek/comments/1w2manf/do_you_trust_the_flash_versions_of_ai_models/) | r/DeepSeek | u/Difficult-Bar-8016 | `t2_27zqnztoao` | 0 | 15 | 2026-08-30 | *not read* |
| 1040 | 5.5 | post | [DeepSeek V4 Pro in RP is just garbage compared to Sonnet 4.5](https://www.reddit.com/r/SillyTavernAI/comments/1suugcs/deepseek_v4_pro_in_rp_is_just_garbage_compared_to/) | r/SillyTavernAI | u/Sh0w_T1mer | `t2_jrin2izv` | 0 | 34 | 2026-04-24 | *not read* |
| 1041 | 5.5 | post | [Which provider is actually behind DeepSeek V4 Pro in OpenCod](https://www.reddit.com/r/opencodeCLI/comments/1t31fdu/which_provider_is_actually_behind_deepseek_v4_pro/) | r/opencodeCLI | u/Funny-Ambition-7631 | `t2_ej33eneps` | 19 | 22 | 2026-05-03 | *not read* |
| 1043 | 5.5 | post | [I asked DeepSeek V4 Flash 0731 to recreate a game which Deep](https://www.reddit.com/r/DeepSeek/comments/1vcczlg/i_asked_deepseek_v4_flash_0731_to_recreate_a_game/) | r/DeepSeek | u/Simple_Army2952 | `t2_1i9obgsoe7` | 26 | 3 | 2026-08-01 | *not read* |
| 1044 | 5.5 | post | [Running AI agents in cloud with Deepseek V4 PRO and Opencode](https://www.reddit.com/r/opencodeCLI/comments/1vigou2/running_ai_agents_in_cloud_with_deepseek_v4_pro/) | r/opencodeCLI | u/oyren-ai | `t2_25gpdvz655` | 1 | 4 | 2026-08-07 | *not read* |
| 1046 | 5.5 | post | [Mimo V2.5 Pro vs DeepSeek V4 Pro](https://www.reddit.com/r/opencode/comments/1umm6zv/mimo_v25_pro_vs_deepseek_v4_pro/) | r/opencode | u/AggravatingDouble233 | `t2_jizsyarx` | 46 | 39 | 2026-07-03 | *not read* |
| 1047 | 5.5 | post | [V4 Flash is on the performance vs cost efficiency frontier i](https://www.reddit.com/r/DeepSeek/comments/1uriy3d/v4_flash_is_on_the_performance_vs_cost_efficiency/) | r/DeepSeek | u/ell-hol1 | `t2_b8xldvop` | 88 | 15 | 2026-07-09 | *not read* |
| 1050 | 5.4 | post | [DeepSWE benchmarks indicate that DeepSeek v4 Pro only passes](https://www.reddit.com/r/LocalLLaMA/comments/1tsse9i/deepswe_benchmarks_indicate_that_deepseek_v4_pro/) | r/LocalLLaMA | u/Federal_Spend2412 | `t2_dvb30wh7` | 16 | 61 | 2026-05-31 | *not read* |
| 1051 | 5.4 | post | [Prism - A native, OS-integrated macOS AI assistant (Launch P](https://www.reddit.com/r/macapps/comments/1u5tlfh/prism_a_native_osintegrated_macos_ai_assistant/) | r/macapps | u/Brave_Volume2501 | `t2_2195k58va2` | 0 | 62 | 2026-06-14 | *not read* |
| 1055 | 5.3 | post | [DeepSeek V4 Pro is now live on Qubrid AI 🚀](https://www.reddit.com/r/Qubrid_AI_Platform/comments/1sumg1r/deepseek_v4_pro_is_now_live_on_qubrid_ai/) | r/Qubrid_AI_Platform | u/qubridInc | `t2_1whcmkkgjf` | 3 | 0 | 2026-04-24 | *not read* |
| 1056 | 5.3 | post | [Deepseek v4 pro/flash alternatives?](https://www.reddit.com/r/AI_Agents/comments/1uucreg/deepseek_v4_proflash_alternatives/) | r/AI_Agents | u/al_kRicha | `t2_11tpri` | 2 | 9 | 2026-07-12 | *not read* |
| 1057 | 5.3 | post | [Deepseek V4 super repetitive?](https://www.reddit.com/r/SillyTavernAI/comments/1tc8puy/deepseek_v4_super_repetitive/) | r/SillyTavernAI | u/gorbeech | `t2_vf9ntwcb` | 30 | 31 | 2026-05-13 | *not read* |
| 1058 | 5.3 | post | [Have anyone tried deepseek v4 pro + opencode?](https://www.reddit.com/r/opencodeCLI/comments/1szp7mg/have_anyone_tried_deepseek_v4_pro_opencode/) | r/opencodeCLI | u/Federal_Spend2412 | `t2_dvb30wh7` | 10 | 24 | 2026-04-30 | *not read* |
| 1063 | 5.1 | post | [DeepSeek V4 Pro 0813 is here](https://www.reddit.com/r/LocalLLM/comments/1vmwp8r/deepseek_v4_pro_0813_is_here/) | r/LocalLLM | u/ParticularCat007 | `t2_2j6n1329te` | 7 | 4 | 2026-08-13 | *not read* |
| 1064 | 5.1 | post | [Cache not working on deepseek-v4-pro-0813 for anyone else?](https://www.reddit.com/r/CrofAI/comments/1vwz8vg/cache_not_working_on_deepseekv4pro0813_for_anyone/) | r/CrofAI | u/Own_Computer_3661 | `t2_e4jweyk3` | 6 | 2 | 2026-08-24 | *not read* |
| 1070 | 5.0 | post | [DeepSeek-V4-Pro Update (official)](https://www.reddit.com/r/DeepSeek/comments/1vn7gv9/deepseekv4pro_update_official/) | r/DeepSeek | u/dnohrdk | `t2_h7um0` | 30 | 9 | 2026-08-13 | *not read* |
| 1071 | 5.0 | post | [I doubt the honesty of the service](https://www.reddit.com/r/FictionLab/comments/1u8dbnc/i_doubt_the_honesty_of_the_service/) | r/FictionLab | u/LavishnessMaximum528 | `t2_atk679yf` | 17 | 26 | 2026-06-17 | *not read* |
| 1076 | 4.9 | post | [Deepseek V4 Pro 0813 Available](https://www.reddit.com/r/opencode/comments/1vmm37p/deepseek_v4_pro_0813_available/) | r/opencode | u/Pedrito_Basket | `t2_br8b8smp` | 69 | 9 | 2026-08-12 | *not read* |
| 1077 | 4.9 | crosspost | [You must have been tired of all the frontend testing - here ](https://www.reddit.com/r/opencode/comments/1vytu8p/you_must_have_been_tired_of_all_the_frontend/) | r/opencode | u/ZealousidealTown1974 | `t2_sgnht5ke` | 1 | 1 | 2026-08-26 | *not read* |
| 1078 | 4.9 | post | [You must have been tired of all the frontend testing - here ](https://www.reddit.com/r/opencodeCLI/comments/1vytt6r/you_must_have_been_tired_of_all_the_frontend/) | r/opencodeCLI | u/ZealousidealTown1974 | `t2_sgnht5ke` | 0 | 1 | 2026-08-26 | *not read* |
| 1081 | 4.9 | post | [Any good deepseek v4 pro provider?](https://www.reddit.com/r/opencodeCLI/comments/1vn1pjj/any_good_deepseek_v4_pro_provider/) | r/opencodeCLI | u/FearlessGround3155 | `t2_yidoh5jr4` | 5 | 23 | 2026-08-13 | *not read* |
| 1091 | 4.7 | post | [This is crazy, almost 100M token with DeepSeek V4 Pro and co](https://www.reddit.com/r/DeepSeek/comments/1tyhwkc/this_is_crazy_almost_100m_token_with_deepseek_v4/) | r/DeepSeek | u/zeeshanx | `t2_qi0im` | 410 | 86 | 2026-06-06 | *not read* |
| 1095 | 4.7 | post | [DeepSeek V4 Pro 0813 can only demonstrate its true capabilit](https://www.reddit.com/r/DeepSeek/comments/1voi3h2/deepseek_v4_pro_0813_can_only_demonstrate_its/) | r/DeepSeek | u/Public_Ad_5096 | `t2_c3ty652z4` | 75 | 13 | 2026-08-14 | *not read* |
| 1100 | 4.7 | post | [Question about Deepseek V4 Pro pricing in opencode go](https://www.reddit.com/r/opencodeCLI/comments/1ufb859/question_about_deepseek_v4_pro_pricing_in/) | r/opencodeCLI | u/XanderJAW | `t2_6plbbzef` | 8 | 11 | 2026-06-25 | *not read* |
| 1101 | 4.7 | post | [Deepseek v4 Pro](https://www.reddit.com/r/ollama/comments/1suf250/deepseek_v4_pro/) | r/ollama | u/d9viant | `t2_1wcm6fji` | 25 | 20 | 2026-04-24 | *not read* |
| 1103 | 4.7 | post | [tested deepseek v4 pro, kimi k2.7 and qwen 3.6 on the same m](https://www.reddit.com/r/DeepSeek/comments/1u82arp/tested_deepseek_v4_pro_kimi_k27_and_qwen_36_on/) | r/DeepSeek | u/Independent-Date393 | `t2_2aao46x3qu` | 61 | 14 | 2026-06-17 | *not read* |
| 1106 | 4.7 | post | [Add Deepseek V4 Pro model](https://www.reddit.com/r/GithubCopilot/comments/1svdotn/add_deepseek_v4_pro_model/) | r/GithubCopilot | u/Professional_Price89 | `t2_9k9mghz2` | 23 | 14 | 2026-04-25 | *not read* |
| 1109 | 4.5 | post | [DeepSeek V4 Pro censorship](https://www.reddit.com/r/SillyTavernAI/comments/1vukn20/deepseek_v4_pro_censorship/) | r/SillyTavernAI | u/sociofobs | `t2_m13kr` | 4 | 42 | 2026-08-21 | *not read* |
| 1110 | 4.5 | post | [Kimi K3 and DeepSeek 4 Pro are FREE on NVIDEA NIM (60 req/mi](https://www.reddit.com/r/opencodeCLI/comments/1w0swod/kimi_k3_and_deepseek_4_pro_are_free_on_nvidea_nim/) | r/opencodeCLI | u/afanasenka | `t2_1qo7eszg6y` | 374 | 84 | 2026-08-28 | *not read* |
| 1112 | 4.5 | post | [Deepseek v4 Pro on Claude Code: 🤯](https://www.reddit.com/r/DeepSeek/comments/1u18p3f/deepseek_v4_pro_on_claude_code/) | r/DeepSeek | u/ClearRabbit605 | `t2_j6ct3gzg` | 297 | 126 | 2026-06-09 | *not read* |
| 1113 | 4.5 | post | [Kimi K3 and DeepSeek 4 Pro are FREE on NVIDEA NIM (60 req/mi](https://www.reddit.com/r/opencode/comments/1w0sx6u/kimi_k3_and_deepseek_4_pro_are_free_on_nvidea_nim/) | r/opencode | u/afanasenka | `t2_1qo7eszg6y` | 356 | 40 | 2026-08-28 | *not read* |
| 1115 | 4.5 | post | [OpenCode GO + Deepseek V4 Pro/flash and stop stressing out](https://www.reddit.com/r/GithubCopilot/comments/1szdd8m/opencode_go_deepseek_v4_proflash_and_stop/) | r/GithubCopilot | u/RagnarSkywalker | `t2_30ihuugt` | 361 | 42 | 2026-04-29 | *not read* |
| 1117 | 4.5 | post | [Copilot x16 circus. God bless China!](https://www.reddit.com/r/GithubCopilot/comments/1u5o9mr/copilot_x16_circus_god_bless_china/) | r/GithubCopilot | u/John_OpenRMA | `t2_2dszn05oi8` | 402 | 18 | 2026-06-14 | *not read* |
| 1119 | 4.5 | post | [Deepseek v4 0813 got updated?](https://www.reddit.com/r/DeepSeek/comments/1vni5pz/deepseek_v4_0813_got_updated/) | r/DeepSeek | u/KuziKuzina | `t2_295i7smc6d` | 48 | 7 | 2026-08-13 | *not read* |
| 1121 | 4.5 | post | [DeepSeek v4 Pro costs most... but it costs less...](https://www.reddit.com/r/ollama/comments/1vulk8a/deepseek_v4_pro_costs_most_but_it_costs_less/) | r/ollama | u/OneDev42 | `t2_j5g4zewa` | 14 | 14 | 2026-08-21 | *not read* |
| 1130 | 4.5 | post | [DeepSeek v4-pro](https://www.reddit.com/r/DeepSeek/comments/1sy62pn/deepseek_v4pro/) | r/DeepSeek | u/thepythonpraxis | `t2_1tnqz04em0` | 7 | 12 | 2026-04-28 | *not read* |
| 1134 | 4.4 | post | [GLM 5.3 is now available in ClinePass](https://www.reddit.com/r/CLine/comments/1vo1gg3/glm_53_is_now_available_in_clinepass/) | r/CLine | u/gargetisha | `t2_ms94y2x6` | 76 | 2 | 2026-08-14 | *not read* |
| 1136 | 4.3 | post | [Explore Subagent wasting time and tokens to "generate" the c](https://www.reddit.com/r/opencode/comments/1w1dk6d/explore_subagent_wasting_time_and_tokens_to/) | r/opencode | u/Morpheyz | `t2_fg7qh` | 2 | 4 | 2026-08-29 | *not read* |
| 1137 | 4.3 | post | [Hassle-free way to have vision capabilities with Deepseek V4](https://www.reddit.com/r/DeepSeek/comments/1umo0bj/hasslefree_way_to_have_vision_capabilities_with/) | r/DeepSeek | u/Separate_Ad_314 | `t2_eh4oecv4` | 4 | 15 | 2026-07-03 | *not read* |
| 1138 | 4.3 | post | [*request required* DeepSeek V4 thinking mode fails because c](https://www.reddit.com/r/CLine/comments/1sxk2cp/request_required_deepseek_v4_thinking_mode_fails/) | r/CLine | u/FormalAd7367 | `t2_e3wdiuasg` | 6 | 1 | 2026-04-27 | *not read* |
| 1139 | 4.3 | post | [Deep seek v4 pro](https://www.reddit.com/r/SillyTavernAI/comments/1vjq3kk/deep_seek_v4_pro/) | r/SillyTavernAI | u/RatMan124 | `t2_hxm0fy8r` | 2 | 13 | 2026-08-09 | *not read* |
| 1141 | 4.2 | post | [DeepSeek V4 Pro 0813 (Opencode Go LLM comparison)](https://www.reddit.com/r/opencode/comments/1vn3od0/deepseek_v4_pro_0813_opencode_go_llm_comparison/) | r/opencode | u/WegoW | `t2_13mxc7` | 20 | 0 | 2026-08-13 | *not read* |
| 1142 | 4.2 | post | [MiniMax M3 vs Deepseek V4 Pro](https://www.reddit.com/r/opencode/comments/1uzmm2q/minimax_m3_vs_deepseek_v4_pro/) | r/opencode | u/No-Maybe-1913 | `t2_brklu6kc` | 27 | 15 | 2026-07-18 | *not read* |
| 1143 | 4.2 | post | [Deepseek V4 Pro Artificial Analysis Benchmarks](https://www.reddit.com/r/DeepSeek/comments/1vn4kcs/deepseek_v4_pro_artificial_analysis_benchmarks/) | r/DeepSeek | u/Testx01 | `t2_e3rbu66k` | 111 | 33 | 2026-08-13 | *not read* |
| 1147 | 4.0 | post | [Migrating SaaS from Claude + VS Code to DeepSeek V4 Pro: Sta](https://www.reddit.com/r/DeepSeek/comments/1u3xyhc/migrating_saas_from_claude_vs_code_to_deepseek_v4/) | r/DeepSeek | u/Economics-Fair | `t2_7o5ccr4s` | 4 | 6 | 2026-06-12 | *not read* |
| 1148 | 4.0 | post | [DeepSeek v4 pro is now easily on par with GLM 5.2 imo](https://www.reddit.com/r/DeepSeek/comments/1vn7cem/deepseek_v4_pro_is_now_easily_on_par_with_glm_52/) | r/DeepSeek | u/yawm-al-masihi | `t2_nf3up5g` | 0 | 9 | 2026-08-13 | *not read* |
| 1154 | 3.7 | post | [Still early but some of first benchmarks for DeepSeek V4-Pro](https://www.reddit.com/r/Anthropic/comments/1vmmx0i/still_early_but_some_of_first_benchmarks_for/) | r/Anthropic | u/ColdKiwi720 | `t2_wqxc99pvz` | 503 | 77 | 2026-08-12 | *not read* |
| 1158 | 3.7 | post | [Is Kimi 2.6 worth it compared to DeepSeek V4 Pro and GLM?](https://www.reddit.com/r/opencodeCLI/comments/1t11ndo/is_kimi_26_worth_it_compared_to_deepseek_v4_pro/) | r/opencodeCLI | u/marwan_rashad5 | `t2_28h80dpt9p` | 72 | 71 | 2026-05-01 | *not read* |
| 1159 | 3.7 | post | [Is DeepSeek V4 Pro GA really that bad?](https://www.reddit.com/r/DeepSeek/comments/1voaf2j/is_deepseek_v4_pro_ga_really_that_bad/) | r/DeepSeek | u/rain-home | `t2_trk2idse` | 10 | 53 | 2026-08-14 | *not read* |
| 1161 | 3.7 | post | [DeepSeek V4 Pro 0813 Benchmarks](https://www.reddit.com/r/DeepSeek/comments/1vmhvn4/deepseek_v4_pro_0813_benchmarks/) | r/DeepSeek | u/cryptoman_101 | `t2_bp57djka` | 117 | 32 | 2026-08-12 | *not read* |
| 1162 | 3.7 | post | [Verdent added DeepSeek V4 Pro 0813 and Gemini 3.7 Flash](https://www.reddit.com/r/Verdent/comments/1vtchy1/verdent_added_deepseek_v4_pro_0813_and_gemini_37/) | r/Verdent | u/verdent_ai | `t2_1zgwm653j2` | 2 | 1 | 2026-08-20 | *not read* |
| 1163 | 3.7 | post | [What is wrong with Deepseek v4 Pro](https://www.reddit.com/r/ollama/comments/1vr7h52/what_is_wrong_with_deepseek_v4_pro/) | r/ollama | u/PerspectiveIcy3578 | `t2_1tmjba6jm3` | 33 | 20 | 2026-08-17 | *not read* |
| 1165 | 3.7 | post | [Deepseek-V4 is coming](https://www.reddit.com/r/ArtificialInteligence/comments/1su4uq5/deepseekv4_is_coming/) | r/ArtificialInteligence | u/Helpful-Manner-952 | `t2_11d5muvcq2` | 4 | 1 | 2026-04-24 | *not read* |
| 1168 | 3.7 | post | [Holy Cow Extra Usage make Claude Tokens look cheap...](https://www.reddit.com/r/ollama/comments/1tlns1m/holy_cow_extra_usage_make_claude_tokens_look_cheap/) | r/ollama | u/Wide-Ad-1349 | `t2_9up4beuu` | 13 | 17 | 2026-05-23 | *not read* |
| 1169 | 3.7 | post | [DeepSeek V4 - Is way too cheap for complex tasks](https://www.reddit.com/r/vibecoding/comments/1t2cac8/deepseek_v4_is_way_too_cheap_for_complex_tasks/) | r/vibecoding | u/Ferzelibey | `t2_8ia1a4co` | 4 | 16 | 2026-05-03 | *not read* |
| 1170 | 3.7 | post | [Maxed out my claude limit, wired up Claude Code with Deepsee](https://www.reddit.com/r/vibecoding/comments/1t9xfdr/maxed_out_my_claude_limit_wired_up_claude_code/) | r/vibecoding | u/jimbobooyah | `t2_qj974r70t` | 0 | 5 | 2026-05-11 | *not read* |
| 1174 | 3.7 | post | [It took less than 5 minutes to set up deepseek in Copilot CL](https://www.reddit.com/r/GithubCopilot/comments/1tuqhyi/it_took_less_than_5_minutes_to_set_up_deepseek_in/) | r/GithubCopilot | u/workfastdiehard | `t2_16kci2` | 21 | 11 | 2026-06-02 | *not read* |
| 1176 | 3.7 | post | [DeepSeek V4-Pro-0813 is available in OpenCode Go](https://www.reddit.com/r/OpenCodeGo/comments/1vmkmq8/deepseek_v4pro0813_is_available_in_opencode_go/) | r/OpenCodeGo | u/arcanemachined | `t2_ib1h9` | 4 | 0 | 2026-08-12 | *not read* |
| 1179 | 3.5 | post | [They've already surpassed Deepseek v4 pro.](https://www.reddit.com/r/DeepSeek/comments/1vo7wxb/theyve_already_surpassed_deepseek_v4_pro/) | r/DeepSeek | u/Fragrant-Tip-9766 | `t2_5ezm2zt5i` | 139 | 22 | 2026-08-14 | *not read* |
| 1180 | 3.5 | post | [DeepSeek-V4-Flash has been updated, "The official release of](https://www.reddit.com/r/LocalLLaMA/comments/1vbidkp/deepseekv4flash_has_been_updated_the_official/) | r/LocalLLaMA | u/Nunki08 | `t2_agjaq` | 1069 | 297 | 2026-07-31 | *not read* |
| 1182 | 3.5 | post | [Deepseek v4 pro (ga) is rolling out!](https://www.reddit.com/r/DeepSeek/comments/1vmh3gd/deepseek_v4_pro_ga_is_rolling_out/) | r/DeepSeek | u/TigerConsistent | `t2_8i0oi93z` | 375 | 105 | 2026-08-12 | *not read* |
| 1189 | 3.5 | post | [deepseek-ai/DeepSeek-V4-Pro-DSpark • Huggingface](https://www.reddit.com/r/LocalLLaMA/comments/1ugug2o/deepseekaideepseekv4prodspark_huggingface/) | r/LocalLLaMA | u/External_Mood4719 | `t2_szz4yy2pc` | 282 | 40 | 2026-06-27 | *not read* |
| 1191 | 3.5 | post | [Issues with Deepseek v4 Pro](https://www.reddit.com/r/just4ochat/comments/1w250sh/issues_with_deepseek_v4_pro/) | r/just4ochat | u/No_Elephant_5296 | `t2_2ezpni13pg` | 1 | 2 | 2026-08-30 | *not read* |
| 1192 | 3.5 | post | [Pi or Opencode?](https://www.reddit.com/r/Zyte/comments/1tkaz4c/pi_or_opencode/) | r/Zyte | u/jwrzyte | `t2_1oc7661kzl` | 2 | 0 | 2026-05-22 | *not read* |
| 1193 | 3.5 | post | [DeepSeek-V4-Pro-0813 released](https://www.reddit.com/r/opencodeCLI/comments/1vmhevd/deepseekv4pro0813_released/) | r/opencodeCLI | u/BandAny2285 | `t2_tccu5via` | 208 | 27 | 2026-08-12 | *not read* |
| 1194 | 3.5 | post | [DeepSeek-V4-Pro-0813 added to the pricing page](https://www.reddit.com/r/DeepSeek/comments/1vmh9k8/deepseekv4pro0813_added_to_the_pricing_page/) | r/DeepSeek | u/MyZeReddit | `t2_12hglk` | 120 | 36 | 2026-08-12 | *not read* |
| 1195 | 3.5 | post | [We cannot expect too much from a model that lacks visual cap](https://www.reddit.com/r/DeepSeek/comments/1vzx6lr/we_cannot_expect_too_much_from_a_model_that_lacks/) | r/DeepSeek | u/South_Can_3680 | `t2_2ikn7kmbub` | 133 | 29 | 2026-08-27 | *not read* |
| 1200 | 3.5 | post | [Anyone else finding DeepSeek V4 Pro unbearably slow on Ollam](https://www.reddit.com/r/ollama/comments/1t89854/anyone_else_finding_deepseek_v4_pro_unbearably/) | r/ollama | u/Swimming_Power_2960 | `t2_1k6e4leqfv` | 21 | 21 | 2026-05-09 | *not read* |
| 1206 | 3.5 | post | [Is DeepSeek V4 Pro's base model really beating o1 Pro now?](https://www.reddit.com/r/LocalLLaMA/comments/1ujipih/is_deepseek_v4_pros_base_model_really_beating_o1/) | r/LocalLLaMA | u/Defiant_Ranger607 | `t2_vuhtvuekx` | 0 | 17 | 2026-06-30 | *not read* |
| 1207 | 3.5 | post | [Any good presets for Deepseek v4 pro when the plot remains s](https://www.reddit.com/r/SillyTavernAI/comments/1vhbhc6/any_good_presets_for_deepseek_v4_pro_when_the/) | r/SillyTavernAI | u/mmorimoe | `t2_1qid3l481f` | 11 | 23 | 2026-08-06 | *not read* |
| 1208 | 3.5 | post | [Has DeepSeek V4 pro updated?](https://www.reddit.com/r/SillyTavernAI/comments/1tovrm8/has_deepseek_v4_pro_updated/) | r/SillyTavernAI | u/Mari2sol | `t2_1a0k24miox` | 42 | 23 | 2026-05-27 | *not read* |
| 1210 | 3.5 | post | [DeepSeek v4 Pro + Roo Code is costing me almost as much as O](https://www.reddit.com/r/ChatGPT/comments/1t5x9q3/deepseek_v4_pro_roo_code_is_costing_me_almost_as/) | r/ChatGPT | u/chucrutcito | `t2_njo1o` | 2 | 3 | 2026-05-07 | *not read* |
| 1212 | 3.5 | post | [My deepseek v4 pro 0831 had identity issues](https://www.reddit.com/r/SillyTavernAI/comments/1vqft2s/my_deepseek_v4_pro_0831_had_identity_issues/) | r/SillyTavernAI | u/PrettyVacation29 | `t2_d6s3jnjp` | 112 | 24 | 2026-08-17 | *not read* |
| 1214 | 3.5 | post | [dice system](https://www.reddit.com/r/SillyTavernAI/comments/1v6z8en/dice_system/) | r/SillyTavernAI | u/Giggino2000 | `t2_1ra3adn6dz` | 5 | 13 | 2026-07-26 | *not read* |
| 1215 | 3.5 | post | [Deepseek v4 pro and Mimo v2.5 pro pricing possibly updated o](https://www.reddit.com/r/opencodeCLI/comments/1v02xqu/deepseek_v4_pro_and_mimo_v25_pro_pricing_possibly/) | r/opencodeCLI | u/cokefriend | `t2_5qk2u` | 61 | 29 | 2026-07-18 | *not read* |
| 1221 | 3.5 | post | [Deepseek v4 prédiction vs réalité](https://www.reddit.com/r/ChatGPT/comments/1sw6ztu/deepseek_v4_prédiction_vs_réalité/) | r/ChatGPT | u/Hug_LesBosons | `t2_1xkzz79wrd` | 0 | 2 | 2026-04-26 | *not read* |
| 1224 | 3.4 | crosspost | [Why did OpenRouter bill 4M tokens when OpenCode showed only ](https://www.reddit.com/r/DeepSeek/comments/1u2uek4/why_did_openrouter_bill_4m_tokens_when_opencode/) | r/DeepSeek | u/moha35abu | `t2_ydsb3foeo` | 1 | 7 | 2026-06-11 | *not read* |
| 1226 | 3.3 | post | [DeepSeek V4 Flash and V4 Flash 0731 not working with API cre](https://www.reddit.com/r/BlackboxAI_/comments/1vfk69g/deepseek_v4_flash_and_v4_flash_0731_not_working/) | r/BlackboxAI_ | u/GetLaidOff69 | `t2_26qv34sfh6` | 2 | 5 | 2026-08-04 | *not read* |
| 1227 | 3.3 | post | [DeepSeek v4 Pro](https://www.reddit.com/r/CLine/comments/1te1f2g/deepseek_v4_pro/) | r/CLine | u/kexibis | `t2_8dkgv8dt` | 6 | 16 | 2026-05-15 | *not read* |
| 1231 | 3.2 | post | [Was the release of deepseek v4 flash planned to take spotlig](https://www.reddit.com/r/LocalLLaMA/comments/1vee0se/was_the_release_of_deepseek_v4_flash_planned_to/) | r/LocalLLaMA | u/Saifl | `t2_34acx83e` | 13 | 22 | 2026-08-03 | *not read* |
| 1235 | 3.1 | post | [deepseek v4 pro getting dumb?](https://www.reddit.com/r/JanitorAI_Refuges/comments/1upxre7/deepseek_v4_pro_getting_dumb/) | r/JanitorAI_Refuges | u/BallisticGunNuts | `t2_i62pbg7s` | 18 | 9 | 2026-07-07 | *not read* |
| 1238 | 2.7 | post | [DeepSeek V4 Pro 0813 MAX is horrific](https://www.reddit.com/r/DeepSeek/comments/1w1kl2d/deepseek_v4_pro_0813_max_is_horrific/) | r/DeepSeek | u/SnooSongs5410 | `t2_88jespbj` | 11 | 13 | 2026-08-29 | *not read* |
| 1239 | 2.7 | post | [DeepSeek is quietly rolling out V4-Pro-0813 on the API right](https://www.reddit.com/r/DeepSeek/comments/1vmhs9z/deepseek_is_quietly_rolling_out_v4pro0813_on_the/) | r/DeepSeek | u/astrolafi | `t2_1u3dsdfsw7` | 32 | 6 | 2026-08-12 | *not read* |
| 1240 | 2.7 | post | [DeepSeek: DeepSeek V4 Pro 0813 hakkında düşüncülerim](https://www.reddit.com/r/TDev/comments/1vsw4u4/deepseek_deepseek_v4_pro_0813_hakkında/) | r/TDev | u/Enough-Eggplant3943 | `t2_28pp8f7g8y` | 2 | 2 | 2026-08-19 | *not read* |
| 1245 | 2.7 | post | [Kimi K2.6 vs DeepSeek V4 Pro](https://www.reddit.com/r/LocalLLaMA/comments/1sxnzem/kimi_k26_vs_deepseek_v4_pro/) | r/LocalLLaMA | u/bigboyparpa | `t2_16dqw2` | 69 | 37 | 2026-04-28 | *not read* |
| 1246 | 2.7 | crosspost | [I repriced my real Claude Code Max 20x usage against DeepSee](https://www.reddit.com/r/ClaudeCode/comments/1vu4voc/i_repriced_my_real_claude_code_max_20x_usage/) | r/ClaudeCode | u/Maamriya | `t2_30unn8r8` | 0 | 3 | 2026-08-21 | *not read* |
| 1248 | 2.5 | post | [Uh, Deepseek V4 Pro 0813…](https://www.reddit.com/r/SillyTavernAI/comments/1vyyhwk/uh_deepseek_v4_pro_0813/) | r/SillyTavernAI | u/purachina999 | `t2_2crihc74mm` | 305 | 50 | 2026-08-26 | *not read* |
| 1249 | 2.5 | post | [DeepSeek: We’re launching DeepSeek-V4-Pro today!](https://www.reddit.com/r/LocalLLaMA/comments/1vn8m1x/deepseek_were_launching_deepseekv4pro_today/) | r/LocalLLaMA | u/Nunki08 | `t2_agjaq` | 507 | 114 | 2026-08-13 | *not read* |
| 1251 | 2.5 | post | [DeepSeek V4 Pro official version has been updated to the API](https://www.reddit.com/r/DeepSeek/comments/1vmhzcs/deepseek_v4_pro_official_version_has_been_updated/) | r/DeepSeek | u/nekofneko | `t2_sqi8xxun` | 339 | 64 | 2026-08-12 | *not read* |
| 1263 | 2.5 | post | [DeepSeek V4 Pro GA ranks right between Opus 4.8 &amp; GPT 5.](https://www.reddit.com/r/DeepSeek/comments/1vmmmsj/deepseek_v4_pro_ga_ranks_right_between_opus_48/) | r/DeepSeek | u/sdexca | `t2_315hhqqx` | 135 | 49 | 2026-08-12 | *not read* |
| 1264 | 2.5 | post | [DeepSeek V4 Pro quality](https://www.reddit.com/r/DeepSeek/comments/1v4k5hs/deepseek_v4_pro_quality/) | r/DeepSeek | u/mynd_dripp | `t2_2j0wab00uq` | 120 | 47 | 2026-07-23 | *not read* |
| 1265 | 2.5 | post | [anyone actually tried deepseek v4 pro for coding?](https://www.reddit.com/r/LocalLLaMA/comments/1swiy4b/anyone_actually_tried_deepseek_v4_pro_for_coding/) | r/LocalLLaMA | u/Plenty_Extent_9047 | `t2_eau3hzdik` | 84 | 74 | 2026-04-26 | *not read* |
| 1268 | 2.5 | post | [Help with some LLM advice](https://www.reddit.com/r/OpenAI/comments/1w0gvsp/help_with_some_llm_advice/) | r/OpenAI | u/sunnycarp | `t2_6qgnwcyx` | 3 | 4 | 2026-08-28 | *not read* |
| 1270 | 2.5 | post | [Deepseekv4pro + Articraft for 3D CAD design](https://www.reddit.com/r/DeepSeek/comments/1u2qepa/deepseekv4pro_articraft_for_3d_cad_design/) | r/DeepSeek | u/Individual_Math_8254 | `t2_7geqovli` | 3 | 1 | 2026-06-11 | *not read* |
| 1271 | 2.5 | post | [Open router (DEEPSEEKV4) &amp; claude as brain](https://www.reddit.com/r/openrouter/comments/1uezpqi/open_router_deepseekv4_claude_as_brain/) | r/openrouter | u/Renexa_Tech | `t2_2al1pbm8fq` | 7 | 17 | 2026-06-25 | *not read* |
| 1273 | 2.5 | post | [Claude brain and deepseek agents](https://www.reddit.com/r/AI_Deal_Cave/comments/1uezro2/claude_brain_and_deepseek_agents/) | r/AI_Deal_Cave | u/Renexa_Tech | `t2_2al1pbm8fq` | 1 | 1 | 2026-06-25 | *not read* |
| 1274 | 2.5 | post | [Sorry if this is a dumb question, but with the price of Deep](https://www.reddit.com/r/openrouter/comments/1vpf4xi/sorry_if_this_is_a_dumb_question_but_with_the/) | r/openrouter | u/Sea_Top_8938 | `t2_1sqdwybm5t` | 27 | 7 | 2026-08-15 | *not read* |
| 1275 | 2.5 | post | [Hacks to get the best out of DeepSeek v4 Pro 0813](https://www.reddit.com/r/opencodeCLI/comments/1voy33q/hacks_to_get_the_best_out_of_deepseek_v4_pro_0813/) | r/opencodeCLI | u/TomHale | `t2_bc3fr` | 14 | 4 | 2026-08-15 | *not read* |
| 1278 | 2.5 | post | [For those wondering if other providers would follow suit](https://www.reddit.com/r/DeepSeek/comments/1vo57ee/for_those_wondering_if_other_providers_would/) | r/DeepSeek | u/Otakian | `t2_z512d` | 106 | 33 | 2026-08-14 | *not read* |
| 1280 | 2.5 | post | [DeepSeek-V4-Flash has been updated, with the official releas](https://www.reddit.com/r/LocalLLM/comments/1vbo9x0/deepseekv4flash_has_been_updated_with_the/) | r/LocalLLM | u/techlatest_net | `t2_12m02dhx` | 5 | 3 | 2026-07-31 | *not read* |
| 1281 | 2.5 | post | [No Multimodality yet in DeepSeek-V4. But I'll wait.](https://www.reddit.com/r/LocalLLaMA/comments/1su5l9i/no_multimodality_yet_in_deepseekv4_but_ill_wait/) | r/LocalLLaMA | u/Right-Law1817 | `t2_mb4g3ik3` | 133 | 34 | 2026-04-24 | *not read* |
| 1284 | 2.5 | post | [Why someone still using deepseek v4 pro](https://www.reddit.com/r/opencode/comments/1veyr83/why_someone_still_using_deepseek_v4_pro/) | r/opencode | u/whatsoever2021 | `t2_a22q335k` | 90 | 28 | 2026-08-04 | *not read* |
| 1285 | 2.5 | post | [Is DeepSeek v4 Pro api really as good as Claude Opus for wri](https://www.reddit.com/r/DeepSeek/comments/1u25djs/is_deepseek_v4_pro_api_really_as_good_as_claude/) | r/DeepSeek | u/wisewaternexus | `t2_1gijxwmeed` | 37 | 36 | 2026-06-10 | *not read* |
| 1286 | 2.5 | post | [deepseek v4-pro pricing changed on 8/17, costs jumped a lot.](https://www.reddit.com/r/DeepSeek/comments/1vsdzjg/deepseek_v4pro_pricing_changed_on_817_costs/) | r/DeepSeek | u/jonntanny | `t2_2c38aem0` | 4 | 20 | 2026-08-19 | *not read* |
| 1287 | 2.5 | post | [Deepseek v4 pro Resmi sürümü yayınlandı](https://www.reddit.com/r/TDev/comments/1vnl51c/deepseek_v4_pro_resmi_sürümü_yayınlandı/) | r/TDev | u/Enough-Eggplant3943 | `t2_28pp8f7g8y` | 7 | 1 | 2026-08-13 | *not read* |
| 1288 | 2.5 | post | [DeepSeek V4 Pro just dropped, and Grok 4.6 is also here — op](https://www.reddit.com/r/LocalLLM/comments/1vmxvml/deepseek_v4_pro_just_dropped_and_grok_46_is_also/) | r/LocalLLM | u/Otherwise-Swan-7803 | `t2_2ig96ci83c` | 8 | 8 | 2026-08-13 | *not read* |
| 1289 | 2.5 | post | [Is there a way to expose thinking effort for deepseek v4 pro](https://www.reddit.com/r/ollama/comments/1t2zsti/is_there_a_way_to_expose_thinking_effort_for/) | r/ollama | u/Grouchy-Pea-8745 | `t2_tfy5nvgh9` | 6 | 4 | 2026-05-03 | *not read* |
| 1293 | 2.5 | post | [A finding that might be worth paying attention to...](https://www.reddit.com/r/DeepSeek/comments/1vof8nl/a_finding_that_might_be_worth_paying_attention_to/) | r/DeepSeek | u/Jaded_Adagio_4004 | `t2_29zariodpv` | 98 | 12 | 2026-08-14 | *not read* |
| 1296 | 2.5 | post | [People kept saying DeepSeek v4 is good but it's so dumb 😭](https://www.reddit.com/r/hermesagent/comments/1v0gkll/people_kept_saying_deepseek_v4_is_good_but_its_so/) | r/hermesagent | u/Draunzr | `t2_177hkygo5p` | 0 | 26 | 2026-07-19 | *not read* |
| 1298 | 2.5 | post | [Deepseek V4 Pro](https://www.reddit.com/r/SillyTavernAI/comments/1t4hpr1/deepseek_v4_pro/) | r/SillyTavernAI | u/caneriten | `t2_2p46gnz1` | 12 | 30 | 2026-05-05 | *not read* |
| 1301 | 2.5 | post | [Deepseek with web search extension issue](https://www.reddit.com/r/SillyTavernAI/comments/1u3b6jo/deepseek_with_web_search_extension_issue/) | r/SillyTavernAI | u/kirjolohi69 | `t2_a8240agq` | 4 | 3 | 2026-06-11 | *not read* |
| 1302 | 2.5 | post | [Is the Go subscription actually enough for vibe coding or do](https://www.reddit.com/r/opencode/comments/1vbzh9w/is_the_go_subscription_actually_enough_for_vibe/) | r/opencode | u/zubrzysta | `t2_15ygtv` | 15 | 32 | 2026-07-31 | *not read* |
| 1303 | 2.5 | post | [Deepseek v4 pro price decrease](https://www.reddit.com/r/opencodeCLI/comments/1tl1wji/deepseek_v4_pro_price_decrease/) | r/opencodeCLI | u/SennVacan | `t2_1cinhwmwx9` | 94 | 20 | 2026-05-23 | *not read* |
| 1304 | 2.5 | post | [Is DeepseekV4 Pro + flash enough for vibe coding or do I nee](https://www.reddit.com/r/DeepSeek/comments/1vbzk69/is_deepseekv4_pro_flash_enough_for_vibe_coding_or/) | r/DeepSeek | u/zubrzysta | `t2_15ygtv` | 4 | 18 | 2026-07-31 | *not read* |
| 1305 | 2.5 | post | [Which models other than of openai and Anthropic are better t](https://www.reddit.com/r/GithubCopilot/comments/1tp4nwc/which_models_other_than_of_openai_and_anthropic/) | r/GithubCopilot | u/Loner_Indian | `t2_7vygib50` | 8 | 18 | 2026-05-27 | *not read* |
| 1308 | 2.5 | post | [DeepSeek V4 Pro brainstorming commercial product feature](https://www.reddit.com/r/DeepSeek/comments/1vo3leu/deepseek_v4_pro_brainstorming_commercial_product/) | r/DeepSeek | u/paq85 | `t2_nlw4p` | 2 | 0 | 2026-08-14 | *not read* |
| 1309 | 2.5 | post | [DeepSeek V4 Pro brainstorming commercial product feature](https://www.reddit.com/r/devtools/comments/1vofp6y/deepseek_v4_pro_brainstorming_commercial_product/) | r/devtools | u/paq85 | `t2_nlw4p` | 1 | 0 | 2026-08-14 | *not read* |
| 1325 | 2.2 | crosspost | [Qwen3.8 27B is matching DeepSeek V4 Pro and GPT 5.6 Luna on ](https://www.reddit.com/r/LocalLLM/comments/1vriszr/qwen38_27b_is_matching_deepseek_v4_pro_and_gpt_56/) | r/LocalLLM | u/gargetisha | `t2_ms94y2x6` | 97 | 62 | 2026-08-18 | *not read* |
| 1329 | 2.2 | post | [Deepseek-v4-pro is currently 75% off right now.](https://www.reddit.com/r/SillyTavernAI/comments/1svcngh/deepseekv4pro_is_currently_75_off_right_now/) | r/SillyTavernAI | u/chungles34 | `t2_ehffr2sn` | 160 | 43 | 2026-04-25 | *not read* |
| 1330 | 2.2 | post | [Is DeepSeek V4 Pro cheap?](https://www.reddit.com/r/DeepSeek/comments/1t0tltm/is_deepseek_v4_pro_cheap/) | r/DeepSeek | u/jakedame1 | `t2_1w22bw1h3r` | 32 | 21 | 2026-05-01 | *not read* |
| 1341 | 2.0 | post | [DeepSeek V4 Pro is now on OpenCode Go](https://www.reddit.com/r/opencodeCLI/comments/1suhmws/deepseek_v4_pro_is_now_on_opencode_go/) | r/opencodeCLI | u/jpcaparas | `t2_42a7l` | 101 | 28 | 2026-04-24 | *not read* |
| 1348 | 1.7 | post | [DeepSeek V4 Pro Benchmarks](https://www.reddit.com/r/opencode/comments/1vmhrgh/deepseek_v4_pro_benchmarks/) | r/opencode | u/cryptoman_101 | `t2_bp57djka` | 63 | 5 | 2026-08-12 | *not read* |
| 1349 | 1.7 | post | [Deepseek V4 Pro Context Length Capped?](https://www.reddit.com/r/CommandCode/comments/1ufc64i/deepseek_v4_pro_context_length_capped/) | r/CommandCode | u/MetalZealousideal927 | `t2_rguyccbbf` | 7 | 2 | 2026-06-25 | *not read* |
| 1351 | 1.5 | post | [How is the NEW deepseek v4 pro? is it UNHINGED? or have they](https://www.reddit.com/r/SillyTavernAI/comments/1vmqrw8/how_is_the_new_deepseek_v4_pro_is_it_unhinged_or/) | r/SillyTavernAI | u/Skibidirot | `t2_1b4digy0pt` | 29 | 24 | 2026-08-12 | *not read* |
| 1355 | 1.5 | post | [Latest: DeepSeek Kicks Off Another Round of Gray Testing](https://www.reddit.com/r/DeepSeek/comments/1w3g7wy/latest_deepseek_kicks_off_another_round_of_gray/) | r/DeepSeek | u/xg2528 | `t2_2idtqp7j2t` | 25 | 6 | 2026-08-31 | *not read* |
| 1359 | 1.5 | post | [DeepSeek V4 Pro keeps giving me "No response from bot" error](https://www.reddit.com/r/CharacterAIrunaways/comments/1w29b46/deepseek_v4_pro_keeps_giving_me_no_response_from/) | r/CharacterAIrunaways | u/Old-Self375 | `t2_14n3tmje3k` | 3 | 12 | 2026-08-30 | *not read* |
| 1362 | 1.5 | post | [DeepSeekV4Pro has changed to a permanent discount. Does this](https://www.reddit.com/r/CommandCode/comments/1tl2svd/deepseekv4pro_has_changed_to_a_permanent_discount/) | r/CommandCode | u/lixiaoyao9p | `t2_i2nnzp1u` | 5 | 1 | 2026-05-23 | *not read* |
| 1363 | 1.5 | post | [DeepSeek-V4-Pro-0813 released on api](https://www.reddit.com/r/LocalLLaMA/comments/1vn5jbx/deepseekv4pro0813_released_on_api/) | r/LocalLLaMA | u/AlbeHxT9 | `t2_ps530aqs` | 7 | 9 | 2026-08-13 | *not read* |
| 1364 | 1.5 | post | [Deepseek v4 pro 0813](https://www.reddit.com/r/SillyTavernAI/comments/1vzyhfe/deepseek_v4_pro_0813/) | r/SillyTavernAI | u/LateInternal6105 | `t2_h01n3wv1m` | 3 | 6 | 2026-08-27 | *not read* |
| 1365 | 1.5 | post | [Hacks to get the best out of DeepSeek v4 Pro 0813](https://www.reddit.com/r/PiCodingAgent/comments/1voy3iz/hacks_to_get_the_best_out_of_deepseek_v4_pro_0813/) | r/PiCodingAgent | u/TomHale | `t2_bc3fr` | 5 | 5 | 2026-08-15 | *not read* |
| 1366 | 1.5 | post | [RELEASED: DeepSeek V4 Pro 0813](https://www.reddit.com/r/Manipur_techie/comments/1vml0s8/released_deepseek_v4_pro_0813/) | r/Manipur_techie | u/dylannao | `t2_3skll74d` | 4 | 1 | 2026-08-12 | *not read* |
| 1370 | 1.5 | post | [Pro 0813 has been open-sourced on HF](https://www.reddit.com/r/DeepSeek/comments/1vn9hcm/pro_0813_has_been_opensourced_on_hf/) | r/DeepSeek | u/Available_Yam_6267 | `t2_2haxceemfr` | 8 | 2 | 2026-08-13 | *not read* |
| 1373 | 1.5 | post | [Deepseek v4 Pro](https://www.reddit.com/r/aws/comments/1vbrcbp/deepseek_v4_pro/) | r/aws | u/Akustic646 | `t2_10xmgidi` | 18 | 16 | 2026-07-31 | *not read* |
| 1375 | 1.5 | post | [Why Ollama Cloud doesn't have DeepSeek V4 Pro and Qwen3.6?](https://www.reddit.com/r/ollama/comments/1sw512f/why_ollama_cloud_doesnt_have_deepseek_v4_pro_and/) | r/ollama | u/c7Cybersecurity | `t2_25kqc0e7gl` | 29 | 18 | 2026-04-26 | *not read* |
| 1380 | 1.5 | post | [Deepseek V4 hallucinations](https://www.reddit.com/r/SillyTavernAI/comments/1t2i3mn/deepseek_v4_hallucinations/) | r/SillyTavernAI | u/FishermanNew9594 | `t2_el8td5ou` | 8 | 13 | 2026-05-03 | *not read* |
| 1382 | 1.5 | post | [Deepseek V4 Pro is suddenly faster, but I feel like the qual](https://www.reddit.com/r/DeepSeek/comments/1tzoyqe/deepseek_v4_pro_is_suddenly_faster_but_i_feel/) | r/DeepSeek | u/According-Clock6266 | `t2_jlzdjhco` | 20 | 13 | 2026-06-07 | *not read* |
| 1384 | 1.5 | post | [Cline with Deepseek V4 Pro](https://www.reddit.com/r/CLine/comments/1sv5tmp/cline_with_deepseek_v4_pro/) | r/CLine | u/johanna_75 | `t2_vusfmdr2p` | 3 | 9 | 2026-04-25 | *not read* |
| 1390 | 1.5 | crosspost | [GitHub Copilot is moving to token-based billing on June 1 — ](https://www.reddit.com/r/github/comments/1sx8k5m/github_copilot_is_moving_to_tokenbased_billing_on/) | r/github | u/serious_cod69 | `t2_13n504k8jk` | 4 | 1 | 2026-04-27 | *not read* |
| 1394 | 1.5 | post | [Does this mean Deepseek V4 Pro api will be having image inpu](https://www.reddit.com/r/DeepSeek/comments/1vci4br/does_this_mean_deepseek_v4_pro_api_will_be_having/) | r/DeepSeek | u/des369 | `t2_2ilzwu3bzn` | 24 | 22 | 2026-08-01 | *not read* |
| 1395 | 1.5 | post | [Qoder now supports DeepSeek V4 Pro — official release](https://www.reddit.com/r/Qoder/comments/1vn3qj1/qoder_now_supports_deepseek_v4_pro_official/) | r/Qoder | u/heyu0328 | `t2_1s525ato1o` | 4 | 2 | 2026-08-13 | *not read* |
| 1398 | 1.4 | post | [DeepSeek V4 Pro underwhelms on Arena (crowdsourced user pref](https://www.reddit.com/r/singularity/comments/1suci24/deepseek_v4_pro_underwhelms_on_arena_crowdsourced/) | r/singularity | u/Hemingbird | `t2_7fne9` | 99 | 92 | 2026-04-24 | *not read* |
| 1406 | 1.2 | post | [DeepSeek V4 Pro 0813 is the first open-weight model to reach](https://www.reddit.com/r/DeepSeek/comments/1vtpa75/deepseek_v4_pro_0813_is_the_first_openweight/) | r/DeepSeek | u/pmigdal | `t2_u10sn` | 19 | 1 | 2026-08-20 | *not read* |
| 1407 | 1.2 | post | [We getting today grok 4.6, DeepSeek v4 pro, open source Qwen](https://www.reddit.com/r/singularity/comments/1vmifwh/we_getting_today_grok_46_deepseek_v4_pro_open/) | r/singularity | u/Independent-Wind4462 | `t2_1lnt2rs3qb` | 198 | 16 | 2026-08-12 | *not read* |
| 1412 | 1.0 | post | [Qwen3.8-Flash-Next better then DeepSeek V4 Pro](https://www.reddit.com/r/LocalLLaMA/comments/1vzowwo/qwen38flashnext_better_then_deepseek_v4_pro/) | r/LocalLLaMA | u/Normal-Phone7762 | `t2_1cqmbyyfcd` | 664 | 204 | 2026-08-27 | *not read* |
| 1413 | 1.0 | post | [deepseek-ai/DeepSeek-V4-Pro-0813 · Hugging Face](https://www.reddit.com/r/LocalLLaMA/comments/1vn9it4/deepseekaideepseekv4pro0813_hugging_face/) | r/LocalLLaMA | u/mossy_troll_84 | `t2_1gx8uoalsc` | 527 | 88 | 2026-08-13 | *not read* |
| 1414 | 1.0 | post | [DeepSeek-V4-Flash-0731 now far surpassing the DeepSeek-V4-Pr](https://www.reddit.com/r/LocalLLaMA/comments/1vbkvau/deepseekv4flash0731_now_far_surpassing_the/) | r/LocalLLaMA | u/SnooBunnies8392 | `t2_9yyyjaak` | 447 | 90 | 2026-07-31 | *not read* |
| 1417 | 1.0 | post | [Deepseek-v4-Pro-0813?](https://www.reddit.com/r/SillyTavernAI/comments/1vmhhte/deepseekv4pro0813/) | r/SillyTavernAI | u/Abject_Property_981 | `t2_k0tqe0ct` | 157 | 80 | 2026-08-12 | *not read* |
| 1418 | 1.0 | post | [deepseek-v4-pro](https://www.reddit.com/r/SillyTavernAI/comments/1vy55lw/deepseekv4pro/) | r/SillyTavernAI | u/Ma4a4a | `t2_5jcyo09jq` | 343 | 41 | 2026-08-25 | *not read* |
| 1441 | 1.0 | post | [Grok 4.3 is cheaper than DeepSeek V4 Pro](https://www.reddit.com/r/DeepSeek/comments/1t4qt4l/grok_43_is_cheaper_than_deepseek_v4_pro/) | r/DeepSeek | u/LeTanLoc98 | `t2_25i76blr` | 122 | 85 | 2026-05-05 | *not read* |
| 1442 | 1.0 | crosspost | [DeepSeek-V4-Flash has been updated, "The official release of](https://www.reddit.com/r/SillyTavernAI/comments/1vbigft/deepseekv4flash_has_been_updated_the_official/) | r/SillyTavernAI | u/The_Rational_Gooner | `t2_1rq275h2ar` | 143 | 51 | 2026-07-31 | *not read* |
| 1443 | 1.0 | post | [Deepseek V4 Pro called a function in my python script I wrot](https://www.reddit.com/r/DeepSeek/comments/1ugpac8/deepseek_v4_pro_called_a_function_in_my_python/) | r/DeepSeek | u/cyb3rofficial | `t2_pneh1c0` | 224 | 36 | 2026-06-27 | *not read* |
| 1444 | 1.0 | post | [Head to head: DeepSeek V4 Pro vs GPT-5.5 Pro](https://www.reddit.com/r/DeepSeek/comments/1tzskzu/head_to_head_deepseek_v4_pro_vs_gpt55_pro/) | r/DeepSeek | u/ryanmerket | `t2_330y5` | 174 | 39 | 2026-06-08 | *not read* |
| 1463 | 1.0 | crosspost | [Why does DeepSeek V4 Pro feel so much less capable than GPT-](https://www.reddit.com/r/hermesagent/comments/1uwz349/why_does_deepseek_v4_pro_feel_so_much_less/) | r/hermesagent | u/Capital_Feed_3473 | `t2_1pyn3o1zoe` | 1 | 1 | 2026-07-15 | *not read* |
| 1464 | 1.0 | crosspost | [Switching to DeepSeek V4 Pro: My Workflow Takeaways](https://www.reddit.com/r/DeepSeek/comments/1u11aym/switching_to_deepseek_v4_pro_my_workflow_takeaways/) | r/DeepSeek | u/Calm-Procedure1847 | `t2_1mw1au3b2y` | 1 | 1 | 2026-06-09 | *not read* |
| 1471 | 0.7 | post | [DeepSeek v4 pro benchmark](https://www.reddit.com/r/DeepSeek/comments/1vmincu/deepseek_v4_pro_benchmark/) | r/DeepSeek | u/minxio_ | `t2_1r2y42s9tb` | 85 | 26 | 2026-08-12 | *not read* |
| 1476 | 0.5 | post | [DeepSeek V4 Pro is now available in OpenCode Go](https://www.reddit.com/r/opencodeCLI/comments/1vmijvx/deepseek_v4_pro_is_now_available_in_opencode_go/) | r/opencodeCLI | u/minxio_ | `t2_1r2y42s9tb` | 282 | 37 | 2026-08-12 | *not read* |
| 1477 | 0.5 | post | [Does anyone have an abliterated version of deepseekv4pro?](https://www.reddit.com/r/DeepSeek/comments/1uabamm/does_anyone_have_an_abliterated_version_of/) | r/DeepSeek | u/Foreign_Ad4578 | `t2_1dwsdaudlj` | 2 | 5 | 2026-06-19 | *not read* |
| 1479 | 0.5 | post | [DeepSeek v4 Pro 0813 released](https://www.reddit.com/r/LocalLLM/comments/1vmixfb/deepseek_v4_pro_0813_released/) | r/LocalLLM | u/Longjumping_Law6632 | `t2_2f36g2d1kq` | 17 | 4 | 2026-08-12 | *not read* |
| 1480 | 0.5 | post | [Qwen 3.8 Open Weights, DeepSeek-V4-Pro-0813 and Grok 4.6 — A](https://www.reddit.com/r/opencode/comments/1vmhxvv/qwen_38_open_weights_deepseekv4pro0813_and_grok/) | r/opencode | u/ideaofsoul | `t2_2gq2a3uvev` | 22 | 1 | 2026-08-12 | *not read* |
| 1482 | 0.5 | post | [Ok deepseek relax](https://www.reddit.com/r/SillyTavernAI/comments/1vrq96y/ok_deepseek_relax/) | r/SillyTavernAI | u/Beneficial_Cake_9816 | `t2_8mqizyhe` | 82 | 16 | 2026-08-18 | *not read* |
| 1485 | 0.5 | post | [When I select Deepseek V4 Pro or Mimo Pro I get this error. ](https://www.reddit.com/r/SillyTavernAI/comments/1ugude6/when_i_select_deepseek_v4_pro_or_mimo_pro_i_get/) | r/SillyTavernAI | u/AspectSubstantial936 | `t2_6i09izr5` | 4 | 4 | 2026-06-27 | *not read* |
| 1487 | 0.5 | post | [Using Deepseek v4 pro sometimes I get results like this wher](https://www.reddit.com/r/SillyTavernAI/comments/1ty7fbx/using_deepseek_v4_pro_sometimes_i_get_results/) | r/SillyTavernAI | u/AspectSubstantial936 | `t2_6i09izr5` | 7 | 8 | 2026-06-06 | *not read* |
| 1488 | 0.5 | post | [How do I know if the model I'm using is deepseek v4 pro or n](https://www.reddit.com/r/DeepSeek/comments/1ukjlql/how_do_i_know_if_the_model_im_using_is_deepseek/) | r/DeepSeek | u/BrilliantNeither7175 | `t2_2c3xbgijhu` | 0 | 11 | 2026-07-01 | *not read* |
| 1489 | 0.5 | post | [Deepseek-v4-flash-0731 VS Deepseek-v4-pro did i gimp my self](https://www.reddit.com/r/DeepSeek/comments/1vebmyf/deepseekv4flash0731_vs_deepseekv4pro_did_i_gimp/) | r/DeepSeek | u/NoPainNullGain | `t2_a6xsjl66` | 2 | 6 | 2026-08-03 | *not read* |
| 1492 | 0.5 | post | [DeepSeek v4 Pro 0813 released](https://www.reddit.com/r/LocalLLM/comments/1vmj1o3/deepseek_v4_pro_0813_released/) | r/LocalLLM | u/Guilty-Cap2069 | `t2_27r8ll4m05` | 9 | 0 | 2026-08-12 | *not read* |
| 1493 | 0.5 | post | [What do you think of DeepSeek-V4-Pro?](https://www.reddit.com/r/Qoder/comments/1vn9oyi/what_do_you_think_of_deepseekv4pro/) | r/Qoder | u/heyu0328 | `t2_1s525ato1o` | 3 | 0 | 2026-08-13 | *not read* |
| 1494 | 0.5 | post | [DeepSeek v4 Pro 0813 released](https://www.reddit.com/r/LocalLLM/comments/1vmiylm/deepseek_v4_pro_0813_released/) | r/LocalLLM | u/Longjumping_Law6632 | `t2_2f36g2d1kq` | 0 | 0 | 2026-08-12 | *not read* |
| 1495 | 0.5 | post | [DeepSeek v4 Pro 0813 released](https://www.reddit.com/r/LocalLLM/comments/1vmixth/deepseek_v4_pro_0813_released/) | r/LocalLLM | u/Longjumping_Law6632 | `t2_2f36g2d1kq` | 0 | 0 | 2026-08-12 | *not read* |
| 1497 | 0.5 | post | [reasoning levels](https://www.reddit.com/r/CrofAI/comments/1vojzr4/reasoning_levels/) | r/CrofAI | u/mkhamat | `t2_le2e4pwg` | 7 | 0 | 2026-08-14 | *not read* |
| 1498 | 0.5 | post | [Peak Hour is "Active"](https://www.reddit.com/r/WhaleSeekers/comments/1vralkv/peak_hour_is_active/) | r/WhaleSeekers | u/VexObserver | `t2_uteism2f` | 4 | 0 | 2026-08-18 | *not read* |
| 1499 | 0.5 | post | [Deepseek v4 pro api available](https://www.reddit.com/r/LLM/comments/1vmx6xn/deepseek_v4_pro_api_available/) | r/LLM | u/Pretty-Background723 | `t2_ff2dbj78` | 6 | 1 | 2026-08-13 | *not read* |
| 1501 | 0.3 | post | [New update - new tier, new models, new everything 💕](https://www.reddit.com/r/FictionLab/comments/1tlsnbc/new_update_new_tier_new_models_new_everything/) | r/FictionLab | u/AppealDemon | `t2_cuqthhya` | 103 | 68 | 2026-05-23 | *not read* |
| 1502 | 0.2 | crosspost | [Tested FlappyBench on Qwen 3.8 27B, DeepSeek V4 Pro 0813, an](https://www.reddit.com/r/AgentBattles/comments/1vu30fa/tested_flappybench_on_qwen_38_27b_deepseek_v4_pro/) | r/AgentBattles | u/Administraciones | `t2_19cj8brfvu` | 1 | 0 | 2026-08-21 | *not read* |
| 1503 | 0.2 | post | [Benchmarking NovaRoute AI - DeepSeek v4 Pro vs Quen 3.7 Max ](https://www.reddit.com/r/JavaSuperIntelligence/comments/1v9zvj7/benchmarking_novaroute_ai_deepseek_v4_pro_vs_quen/) | r/JavaSuperIntelligence | u/Artistic_Solution117 | `t2_djdylx45q` | 1 | 0 | 2026-07-29 | *not read* |
| 1504 | 0.2 | post | [Head to head: DeepSeek-V4-Pro vs gpt-oss-120b — RuntimeWire](https://www.reddit.com/r/AIToolsPerformance/comments/1v1w9yd/head_to_head_deepseekv4pro_vs_gptoss120b/) | r/AIToolsPerformance | u/ryanmerket | `t2_330y5` | 0 | 0 | 2026-07-20 | *not read* |
| 1505 | 0.1 | post | [Qwen 3.8 27B, DeepSeek V4 Pro, Refer &amp; Earn is back, and](https://www.reddit.com/r/Neuralwatt/comments/1vu2oqr/qwen_38_27b_deepseek_v4_pro_refer_earn_is_back/) | r/Neuralwatt | u/Negative_Cable1967 | `t2_1zsddb3ewr` | 29 | 9 | 2026-08-21 | *not read* |
| 1507 | 0.0 | post | [Has anyone tried mimo v2.5 Pro? They reduced their api cost ](https://www.reddit.com/r/SillyTavernAI/comments/1togoed/has_anyone_tried_mimo_v25_pro_they_reduced_their/) | r/SillyTavernAI | u/invisibleman42 | `t2_q9sppuwdo` | 67 | 78 | 2026-05-26 | *not read* |
| 1508 | 0.0 | post | [deepseek-v4-pro works today like deepseek-v4-flash.](https://www.reddit.com/r/DeepSeek/comments/1v81cu8/deepseekv4pro_works_today_like_deepseekv4flash/) | r/DeepSeek | u/Even_Command_5636 | `t2_1eqn55swjw` | 88 | 41 | 2026-07-27 | *not read* |
| 1512 | 0.0 | crosspost | [DeepSeek V4-Pro-0813 is available in OpenCode Go](https://www.reddit.com/r/opencode/comments/1vmkoow/deepseek_v4pro0813_is_available_in_opencode_go/) | r/opencode | u/arcanemachined | `t2_ib1h9` | 8 | 11 | 2026-08-12 | *not read* |
| 1520 | 0.0 | post | [Is Deepseek V4 Pro working in Ollama?](https://www.reddit.com/r/ollama/comments/1swvdvh/is_deepseek_v4_pro_working_in_ollama/) | r/ollama | u/Ok-Permission3643 | `t2_mk4qktjv` | 11 | 14 | 2026-04-27 | *not read* |
| 1521 | 0.0 | post | [New DeepSeek v4 pro neck and neck with Frontier models in co](https://www.reddit.com/r/ChatGPT/comments/1vmkene/new_deepseek_v4_pro_neck_and_neck_with_frontier/) | r/ChatGPT | u/Personal-Try2776 | `t2_zvgy04vgq` | 15 | 22 | 2026-08-12 | *not read* |
| 1524 | 0.0 | crosspost | [Tool calling broken with DeepSeek V4 Pro via OpenRouter when](https://www.reddit.com/r/DeepSeek/comments/1tqvrup/tool_calling_broken_with_deepseek_v4_pro_via/) | r/DeepSeek | u/tmoravec | `t2_g8ina` | 2 | 1 | 2026-05-29 | *not read* |
| 1525 | 0.0 | crosspost | [How to use DeepSeek V4 PRO in Cursor? Skill issue on my side](https://www.reddit.com/r/cursor/comments/1th45ig/how_to_use_deepseek_v4_pro_in_cursor_skill_issue/) | r/cursor | u/BattlePhysical4105 | `t2_qco8mhf1t` | 1 | 5 | 2026-05-18 | *not read* |
| 1526 | 0.0 | post | [Deepseek v4 pro](https://www.reddit.com/r/cursor/comments/1u20m5d/deepseek_v4_pro/) | r/cursor | u/RiskNeither3102 | `t2_15r70jxhyk` | 2 | 2 | 2026-06-10 | *not read* |
| 1527 | 0.0 | post | [OpenRouter lists DeepSeek V4 Pro 0813 as GA despite unchange](https://www.reddit.com/r/RuntimeWire/comments/1vmkpyi/openrouter_lists_deepseek_v4_pro_0813_as_ga/) | r/RuntimeWire | u/ryanmerket | `t2_330y5` | 1 | 0 | 2026-08-12 | *not read* |
| 1531 | 0.0 | post | [deepseek v4 pro vs GLM 5.1 Which one wins?](https://www.reddit.com/r/DeepSeek/comments/1tlhor8/deepseek_v4_pro_vs_glm_51_which_one_wins/) | r/DeepSeek | u/OkContract6063 | `t2_nhmd525al` | 60 | 45 | 2026-05-23 | *not read* |
| 1532 | 0.0 | post | [DeepSeek V4 Pro "0813" is now on OpenCode Go](https://www.reddit.com/r/WhaleSeekers/comments/1vmx0jp/deepseek_v4_pro_0813_is_now_on_opencode_go/) | r/WhaleSeekers | u/VexObserver | `t2_uteism2f` | 3 | 0 | 2026-08-13 | *not read* |
| 1534 | -0.3 | post | [Deepseek v4 pro is unlimited and almost free OMG 😱 better th](https://www.reddit.com/r/hermesagent/comments/1tlmcbl/deepseek_v4_pro_is_unlimited_and_almost_free_omg/) | r/hermesagent | u/rjn2-8 | `t2_23i5gn6049` | 671 | 416 | 2026-05-23 | *not read* |
| 1535 | -0.5 | post | [Deepseek V4 is here!](https://www.reddit.com/r/DeepSeek/comments/1su3zv1/deepseek_v4_is_here/) | r/DeepSeek | u/CucumberAccording813 | `t2_9art1dnk` | 246 | 26 | 2026-04-24 | *not read* |
| 1536 | -0.5 | post | [Deepseek v4 Pro vs GPT-5.2-Codex vs Gemini 3.1 Pro](https://www.reddit.com/r/DeepSeek/comments/1tet9v8/deepseek_v4_pro_vs_gpt52codex_vs_gemini_31_pro/) | r/DeepSeek | u/nicox3000 | `t2_uovr200` | 66 | 16 | 2026-05-16 | *not read* |
| 1543 | -1.0 | post | [NEW DeepSeek V4 Pro + J-Space Is SCARY Good](https://www.reddit.com/r/AISEOInsider/comments/1w36az1/new_deepseek_v4_pro_jspace_is_scary_good/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-31 | *not read* |
| 1546 | -1.0 | post | [Does anyone have an abliterated version of deepseekv4pro?](https://www.reddit.com/r/opencodeCLI/comments/1tmpcns/does_anyone_have_an_abliterated_version_of/) | r/opencodeCLI | u/Foreign_Ad4578 | `t2_1dwsdaudlj` | 0 | 4 | 2026-05-24 | *not read* |
| 1547 | -1.0 | post | [deepseek-ai/DeepSeek-V4-Pro-0813 (Available again) · Hugging](https://www.reddit.com/r/LocalLLaMA/comments/1vnervw/deepseekaideepseekv4pro0813_available_again/) | r/LocalLLaMA | u/panchovix | `t2_j1kqr` | 93 | 4 | 2026-08-13 | *not read* |
| 1548 | -1.0 | post | [Deepseek v4 Pro 0813 coming out](https://www.reddit.com/r/DeepSeek/comments/1vmhss0/deepseek_v4_pro_0813_coming_out/) | r/DeepSeek | u/Sad-Music-170 | `t2_1mk21vs1ol` | 42 | 6 | 2026-08-12 | *not read* |
| 1549 | -1.0 | post | [sorry guys DeepSeek V4 Flash 0731 &gt;&gt;&gt; DeepSeek V4 P](https://www.reddit.com/r/DeepSeek/comments/1vn6n9z/sorry_guys_deepseek_v4_flash_0731_deepseek_v4_pro/) | r/DeepSeek | u/Beginning_Guide7411 | `t2_1n5bm24zym` | 0 | 10 | 2026-08-13 | *not read* |
| 1551 | -1.0 | post | [Did DeepSeek V4 Pro 0813 Just DESTROY Fable 5 &amp; GPT-5.6?](https://www.reddit.com/r/DeepSeek/comments/1vne96u/did_deepseek_v4_pro_0813_just_destroy_fable_5/) | r/DeepSeek | u/RealOppasTV | `t2_1q1liqh43g` | 0 | 3 | 2026-08-13 | *not read* |
| 1554 | -1.0 | crosspost | [DeepSeek V4 Pro è ufficiale: rilasciata la build 0813, in si](https://www.reddit.com/r/IA_Italia/comments/1vmty3l/deepseek_v4_pro_è_ufficiale_rilasciata_la_build/) | r/IA_Italia | u/Medium-Spinach-3578 | `t2_1dd50sllxw` | 5 | 1 | 2026-08-12 | *not read* |
| 1555 | -1.0 | post | [DeepSeek V4 Pro 0813](https://www.reddit.com/r/hackernews/comments/1vmniym/deepseek_v4_pro_0813/) | r/hackernews | u/HNMod | `t2_bzan9` | 2 | 1 | 2026-08-12 | *not read* |
| 1556 | -1.0 | post | [Did DeepSeek V4 Pro 0813 Just DESTROY Fable 5 &amp; GPT-5.6?](https://www.reddit.com/r/OnlyAICoding/comments/1vnec6v/did_deepseek_v4_pro_0813_just_destroy_fable_5/) | r/OnlyAICoding | u/RealOppasTV | `t2_1q1liqh43g` | 0 | 1 | 2026-08-13 | *not read* |
| 1557 | -1.0 | post | [Did DeepSeek V4 Pro 0813 Just DESTROY Fable 5 &amp; GPT-5.6?](https://www.reddit.com/r/AIcodingProfessionals/comments/1vneai6/did_deepseek_v4_pro_0813_just_destroy_fable_5/) | r/AIcodingProfessionals | u/RealOppasTV | `t2_1q1liqh43g` | 0 | 1 | 2026-08-13 | *not read* |
| 1565 | -1.0 | post | [New DeepSeek v4 pro neck and neck with Frontier models in co](https://www.reddit.com/r/GeminiAI/comments/1vmkfo5/new_deepseek_v4_pro_neck_and_neck_with_frontier/) | r/GeminiAI | u/Personal-Try2776 | `t2_zvgy04vgq` | 76 | 16 | 2026-08-12 | *not read* |
| 1567 | -1.0 | post | [DeepSeek V4 Pro vs Claude Fable 5 vs Grok 4.6](https://www.reddit.com/r/AISEOInsider/comments/1vopw8u/deepseek_v4_pro_vs_claude_fable_5_vs_grok_46/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-15 | *not read* |
| 1568 | -1.0 | post | [DeepSeek V4 Pro VS Claude Fable 5 VS Grok 4.6: Who Wins?](https://www.reddit.com/r/AISEOInsider/comments/1vndvz7/deepseek_v4_pro_vs_claude_fable_5_vs_grok_46_who/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-13 | *not read* |
| 1569 | -1.0 | crosspost | [Deepseek V4 pro vs Minimax M3 vs Mimo v2.5 pro vs Qwen 3.7pl](https://www.reddit.com/r/opencode/comments/1ugx1s8/deepseek_v4_pro_vs_minimax_m3_vs_mimo_v25_pro_vs/) | r/opencode | u/Decent-Rain5100 | `t2_1zrwroipfi` | 10 | 3 | 2026-06-27 | *not read* |
| 1570 | -1.0 | crosspost | [Deepseek V4 pro vs Minimax M3 vs Mimo v2.5 pro vs Qwen 3.7pl](https://www.reddit.com/r/MiniMax_AI/comments/1ugx12k/deepseek_v4_pro_vs_minimax_m3_vs_mimo_v25_pro_vs/) | r/MiniMax_AI | u/Decent-Rain5100 | `t2_1zrwroipfi` | 4 | 0 | 2026-06-27 | *not read* |
| 1571 | -1.0 | crosspost | [Deepseek V4 pro vs Minimax M3 vs Mimo v2.5 pro vs Qwen 3.7pl](https://www.reddit.com/r/vibecoding/comments/1ugx1dr/deepseek_v4_pro_vs_minimax_m3_vs_mimo_v25_pro_vs/) | r/vibecoding | u/Decent-Rain5100 | `t2_1zrwroipfi` | 1 | 0 | 2026-06-27 | *not read* |
| 1574 | -1.0 | crosspost | [MiniMax M3 vs Deepseek V4 Pro](https://www.reddit.com/r/DeepSeek/comments/1uzmme4/minimax_m3_vs_deepseek_v4_pro/) | r/DeepSeek | u/No-Maybe-1913 | `t2_brklu6kc` | 2 | 0 | 2026-07-18 | *not read* |
| 1575 | -1.0 | post | [DeepSeek V4 Pro 0813 quietly released](https://www.reddit.com/r/hypeurls/comments/1vmk3qw/deepseek_v4_pro_0813_quietly_released/) | r/hypeurls | u/TheStartupChime | `t2_a7jpx5kp` | 1 | 0 | 2026-08-12 | *not read* |
| 1576 | -1.0 | post | [Deepseek V4 Pro GA](https://www.reddit.com/r/DeepSeek/comments/1vh550w/deepseek_v4_pro_ga/) | r/DeepSeek | u/Upstairs-Category-39 | `t2_941b9utj` | 56 | 10 | 2026-08-06 | *not read* |
| 1578 | -1.0 | crosspost | [Deepseek v4 pro is both a genius and a lunatic](https://www.reddit.com/r/CLine/comments/1vmr6nv/deepseek_v4_pro_is_both_a_genius_and_a_lunatic/) | r/CLine | u/Barquish | `t2_9pd99i5w` | 0 | 2 | 2026-08-12 | *not read* |
| 1590 | -1.5 | post | [DeepSeek V4 Pro 0813 realease but no X announcement?](https://www.reddit.com/r/DeepSeek/comments/1vmpy8k/deepseek_v4_pro_0813_realease_but_no_x/) | r/DeepSeek | u/salesxsupport | `t2_22euf6y7` | 21 | 10 | 2026-08-12 | *not read* |
| 1591 | -1.5 | crosspost | [DeepSeek V4 Pro "0813" is now available on Web Chat &gt; Mob](https://www.reddit.com/r/DeepSeek/comments/1vn2efw/deepseek_v4_pro_0813_is_now_available_on_web_chat/) | r/DeepSeek | u/VexObserver | `t2_uteism2f` | 20 | 5 | 2026-08-13 | *not read* |
| 1592 | -1.5 | post | [DeepSeek V4 Pro "0813" is now available on Web Chat &gt; Mob](https://www.reddit.com/r/WhaleSeekers/comments/1vn2e1u/deepseek_v4_pro_0813_is_now_available_on_web_chat/) | r/WhaleSeekers | u/VexObserver | `t2_uteism2f` | 11 | 1 | 2026-08-13 | *not read* |
| 1593 | -1.5 | post | [Grok 4.6 is here and Deepseek v4 Pro GA has started to roll ](https://www.reddit.com/r/SillyTavernAI/comments/1vmj2z3/grok_46_is_here_and_deepseek_v4_pro_ga_has/) | r/SillyTavernAI | u/Aight_Man | `t2_1fd323wh9p` | 51 | 26 | 2026-08-12 | *not read* |
| 1594 | -2.5 | post | [DeepSeek V4 Pro Is HERE… And It’s INSANE!](https://www.reddit.com/r/AISEOInsider/comments/1w0yqzo/deepseek_v4_pro_is_here_and_its_insane/) | r/AISEOInsider | u/NecessaryBear98 | `t2_2cvvndmecx` | 1 | 0 | 2026-08-28 | *not read* |
| 1596 | -2.5 | post | [DeepSeek V4 Pro is now available](https://www.reddit.com/r/DeepSeek/comments/1vmiled/deepseek_v4_pro_is_now_available/) | r/DeepSeek | u/minxio_ | `t2_1r2y42s9tb` | 34 | 0 | 2026-08-12 | *not read* |

## 11. Method, and what these numbers do not mean

### 11.1 Route and containment

- Reddit access ran through this repository's existing adapter, `collect/adapters/reddit.py` (`RedditHarvester`), over the RapidAPI-fronted Reddit service named by `RAPIDAPI_HOST`. The key came from `.env`. **No new credentials were registered and nothing was signed up for.**

- The repo's official-Reddit-API credentials (`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`) are **blank**. The official API was therefore not an available route, and this is stated rather than routed around.

- **`collect/ops/sweep_reddit.py` was deliberately NOT used.** It takes a database connection and writes `document`, `harvest_run` and `author` rows. This topic is unrelated to the project's corpus, so that machinery was bypassed and the adapter driven directly.

- The `RawStore` was pointed at the scratch tree, so the repo's `raw_store/` was not touched. **Every artifact of this run lives under the scratch directory.** No production database, index, or `contract/` keyword list was read for topic terms or written to.

- The repo requires network fetches go through `harvester_for_source()`, which runs the `assert_terms_reviewed()` ToS gate. That gate loads its rulings from `contract/sources.yaml`, not from the database, so the real gate ran read-only. It passed under ruling `reddit-via-rapidapi`, whose permitted basis is **internal development and testing only** — which is what this is.

### 11.2 Retrieval is loose, and how much was filtered out

- **This search API has no phrase operator.** It degrades to OR over the query tokens and ranks by relevance, which is measured and written up in the adapter's own module docstring. A query for `deepseek v4 pro vllm` returns posts containing *vllm* and nothing else.

- Consequently 1601 records were retrieved and only **727 (45%) survive a literal keyword match on their own punctuation-normalised text**. The other 874 are kept in the data, flagged `literal_match: false`, and are reported separately everywhere. They are not deleted, because a loose record's *comments* can still be on-topic.

- **There is no time-window parameter on this endpoint.** `/getSearchPosts` accepts only `query`, `sort` and `cursor`. Time variation was obtained by varying sort (RELEVANCE / NEW / TOP), not by a date filter. A request to 'vary the time window' cannot be satisfied literally here, and this is stated rather than simulated.

### 11.3 This is the top of each result set, not a census

- Pagination was capped at **3 pages (75 posts) for seed queries, 2 pages (50) for derived queries, 3 pages (75) for subreddit listings**. 119 of 127 queries hit that ceiling with a cursor still available — meaning **more results existed and were not fetched**. Every count here is a floor.

- Subreddit listings were swept by recency (`sort=new`) and only topically matching posts were kept; the offered-vs-kept counts per subreddit are in `querylog.json`. Subreddits were chosen from what pass one actually returned, plus the obvious model / local-inference / ML / programming communities.

- **Comments were fetched and then excluded.** Comment trees were pulled for every literal-matching post with at least one comment and for loose posts with 25+ comments — 1029 threads, 48,759 comments, of which 692 matched the keyword literally. They are **not counted anywhere in this report**, on instruction to focus on posts. This is a deliberate scope cut, not an absence of data: the comments are on disk in `comments.jsonl` and fold back in with `INCLUDE_COMMENTS=1` without re-fetching anything. It matters because on Reddit a post's most substantive technical content is often in a reply, so the 692 literal comments are a real body of evidence this report does not show.

### 11.4 Scores, and what the figures in these posts are worth

- **Scores are a snapshot** taken during this run, and **Reddit deliberately fuzzes vote counts**. Treat score and upvote ratio as approximate and as of the fetch time, not as stable values.

- **Every benchmark number, price, token/second figure and context-length claim quoted in this report is what its author wrote on Reddit. None of it is verified.** Several posts in the corpus contradict each other. Where a figure matters, follow the permalink and judge the source.

### 11.5 The labels

- Ranking is by a **transparent hand-written substance heuristic** (`score.py`), which rewards length, figures carrying units, code and config blocks, first-hand language, reasoning connectives, named tooling, structure and benchmark vocabulary; and penalises referral/promo markers, giveaway language, announcement phrasing and bare model-name lists. Every record stores the itemised reasons for its own score in `substance_reasons`, so any rank is auditable and arguable.

- **The heuristic ranks; it does not classify.** The top 150 literal records were then read by hand and labelled with a content type and a subject/mention judgement, each with a short note. Labels live in `labels.json`, keyed by `external_id`, so you can override any of them and re-run `export.py` and `report2.py` without re-fetching.

- **Records below the read cut keep their substance score and rank and have no type label.** They are marked *not read* in §10. This report does not claim full-corpus classification.

### 11.6 Known gaps

- **Deleted and moderator-removed posts are structurally invisible here.** Every one of the 1601 post payloads carries NULL in `removed_by`, `banned_by` and `removed_by_category`, and none has a `[deleted]` author — the search and listing endpoints return live posts only. The comment trees fetched in the same run contain 441 author-deleted and 820 moderator-removed bodies, which is what proves the parser works and the endpoint filters. Full working in §3.1. Any question about what was taken down cannot be answered from this data.

- Author account age and karma are **absent from both the post and comment payloads**. They were fetched separately from `/getProfile`, one call per account, for the accounts that carry the corpus — not for every author. Where absent, the field is blank rather than zero.

- Profile ids canonicalise through `author_external_id()`: `/getProfile` returns a bare id, post payloads return the `t2_`-prefixed form, and taking each verbatim would split one person into two accounts.

- 1 query(ies) returned zero results with a page stored and no error — a genuine empty, not a failure: `deepseek v4 pro vs gpt`.

- Query errors: **none**. Thread-fetch errors: 9. Profile errors: 108 (mostly suspended or deleted accounts).

### 11.7 Reproducing this

- Every query, its sort, its page cap, what it returned and how many records were new is recorded in `querylog.json` (127 entries). Per-thread comment coverage is in `threadlog.json`.

- Raw API responses are content-addressed in the scratch rawstore and can be re-parsed without re-fetching.

