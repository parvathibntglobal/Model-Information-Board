# DeepSeek V4 Pro on WordPress.com — retrieval sweep

Swept 2026-09-02 · window **2026-03-02 → 2026-09-02** · WordPress.com public REST API (`public-api.wordpress.com/rest/v1.1`), anonymous, no key

## Headline counts

- **161 posts returned** by the keyword sweep; **73** actually name DeepSeek V4 Pro and fall inside the window.
- **68 distinct sites**, **58 distinct bylines** (11 posts expose no author at all).
- **First-hand:** 3/73 (4%). Three posts out of seventy-three.
- **Carrying artifacts:** 52/73 (71%) carry ≥1, 31/73 (42%) carry ≥2, 18/73 (25%) carry ≥3.
- **SEO / content-farm / injected:** 41/73 (56%), of which **5 are not articles at all** but malware lures on compromised sites — see below.
- **Byline does not resolve to a person:** 40/73 (55%).

**The usable set is 27 posts** — ≥2 artifacts, excluding the injected ones. But read the provenance column before trusting any of them: 3/73 (4%) report the author's own use, so almost all of the usable set is other people's numbers relayed.

## It is thin, and one part of it is worse than thin

73 posts is not nothing, and a handful are genuinely good — Import AI, The Zvi's weekly, MIT Technology Review, bdtechtalks. But the sweep breaks down like this:

| | Posts |
| --- | ---: |
| Name DeepSeek V4 Pro, in window | 73 |
| …carrying ≥2 artifacts | 31 |
| …after removing injected malware pages | 27 |
| …that report the author's own use | **3** |

**3 of 73 posts contain a first-hand result.** Everything else relays a figure from the launch announcement or from another blog that relayed it. On the specific question this platform was worth trying for — does anyone write up their own use of the model — the answer is essentially no.

## The five posts that are not articles

5 of the 73 posts are **malware lures injected into compromised WordPress sites**, targeting the search "how to run DeepSeek V4 Pro locally". They were not identifiable from the feed: they appear as ordinary short how-to posts with plausible titles.

| Site | What the site actually is | Posts on site | Rate | Bylines | Markers |
| --- | --- | ---: | ---: | ---: | ---: |
| `cityheightscommunityfridge.com` | City Heights Community Fridge | 962 | 2.94/day | 1 | 6/6 |
| `granittrade.com` | Granit Trade Babina Greda — Tel: +385 91 34 34 230 | 395 | 2.44/day | 1 | 6/6 |
| `hkhcs.org` | 香港歷史文化研究會 Hong Kong History and Culture Society | 295 | 2.78/day | 1 | 6/6 |
| `kata-kata04.com` | (no name) | 372 | 2.44/day | 1 | 6/6 |
| `lorakikema.com` | Lorak Ikema — Tu tienda de flores en Mungia | 457 | 2.5/day | 1 | 6/6 |

A Croatian stone-trading company, a flower shop in Mungia, the Hong Kong History and Culture Society, and a San Diego community fridge do not publish two and a half posts a day about local LLM deployment. These are hijacked installs.

| Marker | Present in |
| --- | ---: |
| `fake_captcha` | 5/5 — **all** |
| `obfusc_onload` | 5/5 — **all** |
| `hash_lure` | 5/5 — **all** |
| `install_vector` | 5/5 — **all** |
| `hidden_gif` | 5/5 — **all** |
| `human_check` | 5/5 — **all** |

All six markers are present in all five pages. That is the ClickFix / fake-CAPTCHA delivery pattern: a hidden 1×1 base64 GIF, an obfuscated `onload` on that image which builds a fake CAPTCHA canvas, a "verify you are human" prompt, and a fabricated hash presented as an authenticity check.

What makes it identifiable as one template is that the varying parts vary *systematically*. Each page rotates its label for the fake hash and its claimed install method, while the surrounding sentences keep the same shape:

| Site | Fake-hash label | Claimed install vector |
| --- | --- | --- |
| `granittrade.com` | `HASH-SUM` | "a native PowerShell script" |
| `kata-kata04.com` | `Release Hash` | "a standalone PowerShell module" |
| `hkhcs.org` | `HASH-SUM` | "via Optional Features" |
| `lorakikema.com` | `Build Hash` | "standard pip packages" |
| `cityheightscommunityfridge.com` | `Hash Value` | "a basic curl request" |

The prose around them is the same template reworded — "The client handles the setup, pulling gigabytes of data automatically" appears near-verbatim on two of the five. Rotating the install vector is what keeps the five bodies at 0.68–0.74 similarity rather than identical, which is low enough to survive naive duplicate detection.

**None of the other 68 posts carry the fake-CAPTCHA marker** — the signature is perfectly isolated to this cluster, and the five bodies are 0.68–0.74 similar to each other, so they are one template spun across five victim domains.

### Why this matters for the filter, not just for safety

**4 of these 5 pages score ≥2 artifacts** and would have been promoted into the "usable" set by an artifact-density filter. They are artifact-dense *by construction*: the lure needs a version string, a shell snippet and a hash to look credible. Code fences and version strings are what a fake install guide is made of.

They are excluded from the usable set here and their script payloads are **not reproduced** below — a redacted prose extract is given instead. Do not run anything from these pages.

## The same number, copied, with nobody saying where it came from

The brief predicted launch figures propagating unattributed. That is measurable here.

- **84 mentions** of a named benchmark next to a number, across 20/73 (27%) posts.
- Within ±250 characters of each figure:

| Treatment of the figure | Mentions |
| --- | ---: |
| **names a source** (according to X, per the model card) | 8 of 84 (10%) |
| hedges only ("a reported 80.6%") — admits it is second-hand, does not say whose | 17 (20%) |
| **bare assertion** — stated as fact, no source, no hedge | **59 (70%)** |

By post: 20 of 73 quote a benchmark figure at all; 4 name a source somewhere, 5 only hedge, and 11 do neither.

Figures appearing on three or more distinct sites:

| Figure | Distinct sites |
| --- | ---: |
| `80.6` | 8 |
| `87.9` | 4 |
| `62.7` | 4 |
| `11.4` | 4 |
| `83.3` | 3 |

### The 80.6% case

`80.6` appears on 8 distinct sites. They do not agree on what it measures:

| Site | How it is framed |
| --- | --- |
| `topaiproduct.com` | …rk — coding loops, multi-step tool use, the kind of task that eats context and never lets go. V4-Pro-Max hits 80.6% on S… |
| `geminy.ai` | …oth support thinking-by-default and a non-thinking fast mode. The headline performance gains: V4-Pro scores 80.6% on SWE… |
| `www.financialexpress.com` | …ads LiveCodeBench (93.5) and Codeforces (3206 rating), outperforming many closed frontier models. It achieves 80.6% on S… |
| `cafeai.home.blog` | …Open-source coding models caught the frontier in 2026. DeepSeek V4 Pro recently hit a reported 80.6% on the SWE-bench Ve… |
| `saassentinel.com` | …climbed to 23.1%. V4-Pro is now the world’s largest open-weight model at 1.6 trillion parameters. It scores 80.6% on the… |
| `digitalstrategy-ai.com` | …bench Verified (real coding) Real GitHub issues end-to-end — Chinese labs lead DeepSeek V4-Pro 80.6% Qwen 3.6-35B-A3B 73… |
| `atalupadhyay.wordpress.com` | …s terminal execution (3h timeout) 67.9% 65.4% 75.1% SWE-bench Verified Fix real GitHub issues 80.6% 80.8% 79.2% MCPAtlas… |
| `futurepulseai.blog` | …SimpleQA Verified: Achieved a score of 57.9% compared to Claude-Opus-4.6-Max’s 85.9% and GPT-5.4-xHigh’s 80.6%. HLE (Pas… |

Read the last rows against the first. Most call it DeepSeek V4-Pro on SWE-bench Verified. One attributes 80.6% to **`V4-Pro-Max`**, a model name that does not exist in the vendor's own repository listing. Another attributes 80.6% to **GPT-5.4-xHigh** — a different vendor's model entirely. One says "a *reported* 80.6%", which is the only honest framing in the set because it admits the number is second-hand.

Pages that disagree about a figure they all copied are not independent confirmations of it. On this sample the modal treatment of a benchmark number is to state it as fact, without a source, having got it from another page that did the same.

## Duplicate and syndicated clusters

10 cross-site post pairs exceed 0.55 body similarity, touching 9 sites. Three clusters account for all of them:

| Similarity | Site A | Site B | What it is |
| ---: | --- | --- | --- |
| 1.0 | `mariacatalinaegan.com` | `mybeautymybooks.com` | byte-identical blog tour |
| 1.0 | `mariacatalinaegan.com` | `mybookmarkedreads.wordpress.co` | byte-identical blog tour |
| 1.0 | `mybeautymybooks.com` | `mybookmarkedreads.wordpress.co` | byte-identical blog tour |
| 0.96 | `www.technologyreview.com` | `cdotimes.com` | bot republishing a magazine |
| 0.75 | `hkhcs.org` | `granittrade.com` | injected SEO template |
| 0.72 | `kata-kata04.com` | `hkhcs.org` | injected SEO template |
| 0.72 | `kata-kata04.com` | `granittrade.com` | injected SEO template |
| 0.72 | `hkhcs.org` | `lorakikema.com` | injected SEO template |
| 0.72 | `lorakikema.com` | `granittrade.com` | injected SEO template |
| 0.71 | `kata-kata04.com` | `lorakikema.com` | injected SEO template |

- **"The China AI Disruption Thesis"** — identical text on three sites at similarity 1.0, one tagged `#blogtour`. Two of the three are book-review blogs.
- **MIT Technology Review → `cdotimes.com`** at 0.96, republished under the byline `CDO TIMES BOT`. That site reports 10,706 posts.
- **The injected cluster**, five sites at 0.68–0.74, described above.

## What the sites turn out to be

The brief asked to check the host for anything substantial: an about page, the posting rate, and whether the byline resolves to a person. Posting rate is measured over the most recent 100 posts, so a large newsroom saturates it — the informative pairing is **rate against distinct bylines**.

| Site | Posts | Rate | Bylines | Byline used here | Reads as |
| --- | ---: | ---: | ---: | --- | --- |
| `www.brasil247.com` | 601772 | 100.0/day | 22 | Redação Brasil 247 | automated publisher |
| `trendsnewss.com` | 267258 | 25.0/day | 0 | — | automated publisher |
| `www.pymnts.com` | 140694 | 20.0/day | 2 | PYMNTS | syndication feed |
| `java366.wordpress.com` | 100349 | 100.0/day | 1 | java366 | automated publisher |
| `wirehub.medianewsgroup.com` | 63030 | 100.0/day | 1 | — | automated publisher |
| `hongkongfp.com` | 31811 | 5.0/day | 9 | — | automated publisher |
| `technode.com` | 18904 | 5.56/day | 3 | — | automated publisher |
| `vtbcfeed.wordpress.com` | 13159 | 7.69/day | 1 | VTBC ┋ | syndication feed |
| `fourweekmba.com` | 11789 | 33.33/day | 1 | Gennaro Cuofano | syndication feed |
| `cdotimes.com` | 10706 | 7.69/day | 2 | CDO TIMES BOT | automated publisher |
| `que.com` | 10429 | 20.0/day | 3 | — | automated publisher |
| `hkut.news.blog` | 8994 | 100.0/day | 1 | Chien Chau | syndication feed |
| `newspaceeconomy.ca` | 7980 | 2.94/day | 1 | NSE | automated publisher |
| `canisgallicus.com` | 6273 | 14.29/day | 1 | michelleclarke2015 | syndication feed |
| `ibafin.com` | 5920 | 3.85/day | 1 | Ibafin | automated publisher |
| `magia.news` | 5821 | 2.94/day | 15 | — | automated publisher |
| `cafeai.home.blog` | 5592 | 3.03/day | 1 | Rick's Cafe AI | automated publisher |
| `cafeai.home.blog` | 5592 | 3.03/day | 1 | Rick's Cafe AI | automated publisher |
| `ethanbholland.com` | 5030 | 1.05/day | 1 | ethanbholland | automated publisher |
| `mariacatalinaegan.com` | 4698 | 0.68/day | 1 | mariacatalinaegan | automated publisher |
| `buzzinga.ai` | 4665 | 14.29/day | 2 | — | automated publisher |
| `buzzinga.ai` | 4665 | 14.29/day | 2 | — | automated publisher |

Specific resolutions worth recording:

- `topaiproduct.com` — 1,676 posts, single byline `agent`, 5.88 posts/day. An automated publisher under a non-person byline, and it is the source of two of the posts in this sample including one of the artifact-densest.
- `cdotimes.com` — 10,706 posts, bylines `CDO TIMES BOT` and one named person, 7.69/day.
- `que.com` — 10,429 posts, bylines are place names plus the brand (`Monica @QUE.COM`, `Palawan @QUE.com`, `Warrenton QUE.COM`). None resolves to an identifiable author.
- The MediaNews Group chain (`twincities`, `ocregister`, `presstelegram`, `dailynews`, `sgvtribune`, `sbsun`, `dailybulletin`, `chicoer`, `dailybreeze`, `times-standard`, `santacruzsentinel`, `dailydemocrat`) appears with 500k–1M posts each and as few as one distinct byline in a 100-post sample: one wire feed replicated across mastheads. Only `wirehub.medianewsgroup.com` surfaced a V4 Pro post here, but the chain is why "distinct sites" overstates independence on this platform.

## What the API actually does

Both surfaces work. They do different jobs and the sweep needed both.

| Surface | Status | What it gives | Verdict |
| --- | --- | --- | --- |
| `/read/search?q=` | 200 | cross-site discovery, **full post `content`**, cursor-paginated via `page_handle` | the discovery surface; keep |
| `/sites/{site}/posts/?search=` | 200 | named-site search, `found` total, **and the author field** | needed to fill gaps |
| `/sites/{site}` | 200 | site name, description, subscriber count | needed for vetting |

Two things worth knowing before relying on either:

**`/read/search` returns the full post body, not an excerpt.** `content` came back at up to 91,709 characters against a 371-character `excerpt` on the same object, so no second fetch per post was required. It filters properly, too — `q=zzqqxwvlkj` returns zero posts, unlike dev.to's silently-ignored `search`.

**`/read/search` omits the author on most posts.** `author` was `None` for 70 of the 161 returned posts, while `/sites/{site}/posts/` returns it populated for the same posts. Anyone reading only the discovery surface would conclude these posts are anonymous. That is the concrete reason to use the second surface.

`number=` is advisory: requesting 20 returned 13, 12, 8, 6, 2… per page while the `page_handle` cursor kept working, so pagination has to follow the cursor rather than count.

### What the index covers — the brief's premise needs correcting

The brief assumed this reaches WordPress.com-hosted sites only. It reaches more than that:

| | Posts |
| --- | ---: |
| `is_jetpack: true` — self-hosted, Jetpack-connected | 43/73 (59%) |
| on a `*.wordpress.com` / `.home.blog` / `.wpcomstaging.com` subdomain | 18/73 (25%) |
| on a custom domain | 55/73 (75%) |

43/73 (59%) of these posts are on **self-hosted** WordPress installs connected through Jetpack, and that is how MIT Technology Review, TechNode, Hong Kong Free Press, 9to5Google and The Financial Express are in the index at all. So the reachable population is *WordPress.com-hosted plus Jetpack-connected self-hosted*, which is much broader than the hosted subset. What stays invisible is self-hosted WordPress **without** Jetpack — still a large population, but not the one the premise described. An empty result here would therefore be a stronger negative signal than the brief assumed.

**Requests issued:** 42 for the keyword sweep (5 queries, cursor-paginated) + 294 for site vetting = **336**, plus ~10 probe requests.

**Refused:** 12 refusals (all HTTP 429 rate-limiting, recovered on retry). 6 hard errors, all 404s on `/sites/{site}` for hosts the API does not resolve. No key was used and none was needed.

Per-query yield, showing that the spaced, hyphenated and title-case forms are one query as far as this API is concerned:

| Query | Unique posts | Cursor pages |
| --- | ---: | ---: |
| `DeepSeek V4 Pro` | 63 | 10 |
| `deepseek v4 pro` | 63 | 10 |
| `deepseek-v4-pro` | 63 | 10 |
| `deepseek-v4-pro-0813` | 17 | 2 |
| `deepseek v4` | 127 | 10 |

## Read this as retrieval-shaped, not representative

Every figure carries its denominator because the sample was drawn by our own queries.

1. Five keyword surfaces on one endpoint produced 161 posts, of which 73 survived a V4-Pro match. A post about the model that never writes the version string is not here.
2. The index reaches Jetpack-connected self-hosted sites but not un-connected ones, so this is a subset of WordPress with a specific and invisible boundary.
3. `/read/search` is a ranked, cursor-paginated feed with no `total` field. It reported `next_page: false` after 10 pages on the main query, which reads as exhaustion but cannot be confirmed against a count the API never returns.
4. 68/68 (100%) distinct sites overstates independence: syndication chains, blog tours and one injected template mean the effective number of independent sources is materially lower than 68.

## Classification

| Content type | Posts |
| --- | ---: |
| news summary | 31/73 (42%) |
| opinion | 18/73 (25%) |
| announcement | 7/73 (10%) |
| SEO (injected) | 5/73 (7%) |
| benchmark | 5/73 (7%) |
| comparison | 4/73 (5%) |
| listicle | 2/73 (3%) |
| tutorial | 1/73 (1%) |

| Whose result it is | Posts |
| --- | ---: |
| unattributed | 28/73 (38%) |
| somebody else's benchmark repeated | 27/73 (37%) |
| vendor claim restated | 15/73 (21%) |
| author's own use | 2/73 (3%) |
| own use + relayed | 1/73 (1%) |

| Artifacts | Posts |
| ---: | ---: |
| 0 | 21/73 (29%) |
| 1 | 21/73 (29%) |
| 2 | 13/73 (18%) |
| 3 | 8/73 (11%) |
| 4 | 7/73 (10%) |
| 5 | 3/73 (4%) |

| Artifact kind | Posts carrying it |
| --- | ---: |
| `version_string` | 35/73 (48%) |
| `price` | 28/73 (38%) |
| `bench_number` | 22/73 (30%) |
| `code_fence` | 13/73 (18%) |
| `conditioned_comparison` | 12/73 (16%) |
| `error_output` | 4/73 (5%) |

Median length 817 words, ranging from 11 to 15,453. The longest posts are weekly AI newsletters that mention the model in passing among thirty other items, which is why length again fails to predict usefulness.

---

## All 73 posts

`A` = artifact kinds (0–6). `Fig` = benchmark-figure mentions / of those attributed near the figure. `P?` = byline resolves to a person. `MW` = injected malware.

| # | A | Title | Author | P? | Site | Date | Type | Provenance | Fig | Words | 💬 | MW |
| ---: | ---: | --- | --- | :-: | --- | --- | --- | --- | ---: | ---: | ---: | :-: |
| 1 | 5 | [DeepSeek V4 Preview with Hands-On Labs](https://atalupadhyay.wordpress.com/2026/04/26/deepseek-v4-preview-with-hands-on-labs/) | atalupadhyay |  | `atalupadhyay.wordpress.com` | 2026-04-26 | benchmark | vendor claim restated | 4/4 | 3595 | 0 |  |
| 2 | 5 | [DeepSeek vs ChatGPT (2026): The Honest Comparison](https://geminy.ai/2026/06/28/deepseek-vs-chatgpt-2026-comparison/) | danschamir | Y | `geminy.ai` | 2026-06-28 | benchmark | author's own use | 2/0 | 2325 | 0 |  |
| 3 | 5 | [Top AI News – August 23, 2026](https://aimasternow.blog/2026/08/23/top-ai-news-august-23-2026/) | ruiliu8888 | Y | `aimasternow.blog` | 2026-08-23 | news summary | somebody else's benchmark repeated | 6/2 | 699 | 0 |  |
| 4 | 4 | [AI #181: Astra Goes Cyber Critical](https://thezvi.wordpress.com/2026/08/13/ai-181-astra-goes-cyber-critical/) | TheZvi |  | `thezvi.wordpress.com` | 2026-08-13 | news summary | own use + relayed | 3/0 | 15453 | 1 |  |
| 5 | 4 | [Which AI Models Does Each Major Provider Offer in ](https://newspaceeconomy.ca/2026/07/20/which-ai-models-does-each-major-provider-offer-in-2026/) | NSE |  | `newspaceeconomy.ca` | 2026-07-20 | news summary | somebody else's benchmark repeated | 0/0 | 10966 | 0 |  |
| 6 | 4 | [Gemma 4 vs DeepSeek V4 vs Qwen 3.6: Open-Source AI](https://digitalstrategy-ai.com/2026/05/13/gemma-4-googles-open-source-llm/) | Danar Mustafa | Y | `digitalstrategy-ai.com` | 2026-05-13 | comparison | vendor claim restated | 14/0 | 4217 | 0 |  |
| 7 | 4 | [DeepSeek V4 MI300X: Unleashing Flash Performance o](http://avicrowntechsolutions.com/2026/08/04/deepseek-v4-mi300x-optimize-flash-performance/) | Avicrown TechBlog |  | `avicrowntechsolutions.com` | 2026-08-04 | news summary | unattributed | 2/0 | 3383 | 0 |  |
| 8 | 4 | [The Model Name Stayed the Same, but the Operating ](https://shawnaiintelligence.wordpress.com/2026/08/26/deepseek-v4-pro-ga-agent-operations-en/) | 이수형 | Y | `shawnaiintelligence.wordpr` | 2026-08-26 | news summary | somebody else's benchmark repeated | 0/0 | 3105 | 1 |  |
| 9 | 4 | [DeepSeek V4 Flash + Codex on Windows: Setup Script](http://lachieslifestyle.com/2026/08/01/deepseek-v4-flash-codex-setup-windows/) | Lachie | Y | `lachieslifestyle.com` | 2026-08-01 | tutorial | somebody else's benchmark repeated | 1/1 | 1853 | 0 |  |
| 10 | 4 | [DeepSeek V4 Pro 0813 scores 87.9 on Terminal Bench](http://topaiproduct.com/2026/08/12/deepseek-v4-pro-0813-scores-87-9-on-terminal-bench-2-1-while-charging-0-87-per-million-output-tokens/) | agent |  | `topaiproduct.com` | 2026-08-12 | benchmark | unattributed | 8/0 | 289 | 0 |  |
| 11 | 3 | [AI News #139: Week Ending May 29, 2026 with 36 Exe](https://ethanbholland.com/2026/05/30/ai-news-139-week-ending-may-29-2026-with-36-executive-summaries/) | ethanbholland |  | `ethanbholland.com` | 2026-05-30 | news summary | somebody else's benchmark repeated | 2/0 | 10048 | 0 |  |
| 12 | 3 | [Fable 5 vs GPT-5.6 vs Kimi K3 vs GLM 5.2 vs DeepSe](https://jasonpollakmarketing.com/2026/07/16/fable-5-gpt-5-6-kimi-k3-glm-5-2-deepseek-v4/) | Jason Pollak | Y | `jasonpollakmarketing.com` | 2026-07-16 | comparison | vendor claim restated | 1/0 | 3067 | 1 |  |
| 13 | 3 | [GLM-5.3 vs DeepSeek V4 Pro: Which Open-Weight Code](https://wealthengine.blog/2026/08/18/glm-5-3-vs-deepseek-v4/) | wealthenginex | Y | `wealthengine.blog` | 2026-08-18 | comparison | somebody else's benchmark repeated | 17/0 | 1875 | 5 |  |
| 14 | 3 | [Sharp Price Hikes, Harness Breaks 50,000 Stars Ove](https://bccmedianews.com/?p=6786) | revieweditor |  | `bccmedianews.com` | 2026-08-25 | news summary | somebody else's benchmark repeated | 1/0 | 1807 | 0 |  |
| 15 | 3 | [DeepSeek Unveils New V4 Family of Open-Source AI M](https://futurepulseai.blog/2026/04/28/deepseek-unveils-new-v4-family-of-open-source-ai-models/) | Tech AI |  | `futurepulseai.blog` | 2026-04-28 | benchmark | vendor claim restated | 3/0 | 619 | 0 |  |
| 16 | 3 | [How to Autostart DeepSeek-V4-Pro on AMD/Nvidia GPU](http://cityheightscommunityfridge.com/2026/07/15/how-to-autostart-deepseek-v4-pro-on-amd-nvidia-gpu-with-1m-context-local-guide/) | cityheightscommuni | Y | `cityheightscommunityfridge` | 2026-07-15 | SEO (injected) | unattributed | 0/0 | 410 | 0 | **Y** |
| 17 | 3 | [DeepSeek-V4-Pro & V4-Flash ship with 1M context an](http://topaiproduct.com/2026/07/05/deepseek-v4-pro-v4-flash-ship-with-1m-context-and-0-28-m-output/) | agent |  | `topaiproduct.com` | 2026-07-05 | announcement | somebody else's benchmark repeated | 1/0 | 276 | 0 |  |
| 18 | 3 | [DeepSeek V4 Pro API Update Adds Responses API Supp](https://technode.com/2026/08/13/deepseek-v4-pro-api-update-adds-responses-api-support/) | — |  | `technode.com` | 2026-08-13 | news summary | unattributed | 0/0 | 73 | 0 |  |
| 19 | 2 | [This Week in Artificial Intelligence](https://thedigitalarchives.wordpress.com/2026/08/15/this-week-in-artificial-intelligence-13/) | SteveTechMan | Y | `thedigitalarchives.wordpre` | 2026-08-15 | news summary | vendor claim restated | 5/0 | 1898 | 0 |  |
| 20 | 2 | [Three reasons why DeepSeek’s new model matters – M](https://cdotimes.com/2026/04/25/three-reasons-why-deepseeks-new-model-matters-mit-technology-review/) | CDO TIMES BOT |  | `cdotimes.com` | 2026-04-25 | news summary | somebody else's benchmark repeated | 0/0 | 1691 | 0 |  |
| 21 | 2 | [What AI Coding Models Actually Cost Right Now](http://triedandtyped.com/2026/08/27/ai-coding-model-prices-august-2026/) | Tried and Typed |  | `triedandtyped.com` | 2026-08-27 | news summary | unattributed | 3/1 | 1612 | 2 |  |
| 22 | 2 | [Three reasons why DeepSeek’s new model matters](https://www.technologyreview.com/2026/04/24/1136422/why-deepseeks-v4-matters/) | — |  | `www.technologyreview.com` | 2026-04-24 | news summary | somebody else's benchmark repeated | 0/0 | 1542 | 0 |  |
| 23 | 2 | [DeepSeek V4 Debuts at $3.48/M Tokens—12 Hours Afte](https://frontierbeat.com/2026/04/24/deepseek-v4-releases-pricing-openai-gpt-5-5-2030/) | Hermes Ladiz | Y | `frontierbeat.com` | 2026-04-24 | announcement | somebody else's benchmark repeated | 0/0 | 1141 | 0 |  |
| 24 | 2 | [DeepSeek Made Its 75% Price Cut Permanent. SaaS Ve](https://saassentinel.com/2026/07/13/deepseek-made-its-75-price-cut-permanent-saas-vendors-still-face-a-margin-crisis/) | Scott Dallen | Y | `saassentinel.com` | 2026-07-13 | news summary | unattributed | 1/0 | 753 | 0 |  |
| 25 | 2 | [Claude Fable FOMO? DeepSeek to Qwen – 5 open model](http://www.financialexpress.com/life/technology-claude-fable-fomo-deepseek-to-qwen-5-open-models-worth-trying-instead-4279304/) | — |  | `www.financialexpress.com` | 2026-06-29 | benchmark | vendor claim restated | 7/0 | 721 | 0 |  |
| 26 | 2 | [OpenClaw](https://breefs.wpcomstaging.com/2026/08/16/openclaw-2026-08-16/) | Joe Boydston | Y | `breefs.wpcomstaging.com` | 2026-08-16 | news summary | vendor claim restated | 0/0 | 628 | 0 |  |
| 27 | 2 | [DeepSeek Introduces Peak-Hour Pricing That Quadrup](http://www.pymnts.com/news/artificial-intelligence/2026/deepseek-introduces-peak-hour-pricing-that-quadruples-current-levels/) | PYMNTS | Y | `www.pymnts.com` | 2026-08-13 | announcement | somebody else's benchmark repeated | 0/0 | 372 | 0 |  |
| 28 | 2 | [DeepSeek applies off-peak API pricing on weekends,](http://hkut.news.blog/2026/08/23/deepseek-applies-off-peak-api-pricing-on-weekends-slashing-bills-by-half/) | Chien Chau | Y | `hkut.news.blog` | 2026-08-23 | news summary | somebody else's benchmark repeated | 0/0 | 341 | 0 |  |
| 29 | 2 | [Quick Run DeepSeek-V4-Pro PC with NPU No Admin Rig](http://lorakikema.com/2026/06/30/quick-run-deepseek-v4-pro-pc-with-npu-no-admin-rights-offline-setup/) | LORAK IKEMA |  | `lorakikema.com` | 2026-06-30 | SEO (injected) | unattributed | 0/0 | 302 | 0 | **Y** |
| 30 | 2 | [Quick Run DeepSeek-V4-Pro Local Guide](http://granittrade.com/2026/07/03/quick-run-deepseek-v4-pro-local-guide/) | antomasic | Y | `granittrade.com` | 2026-07-03 | SEO (injected) | unattributed | 2/0 | 276 | 0 | **Y** |
| 31 | 2 | [Run DeepSeek-V4-Pro with 1M Context Step-by-Step W](http://hkhcs.org/2026/07/06/run-deepseek-v4-pro-with-1m-context-step-by-step-windows/) | hkhcs |  | `hkhcs.org` | 2026-07-06 | SEO (injected) | unattributed | 0/0 | 267 | 0 | **Y** |
| 32 | 1 | [Author Digest — August 22, 2026](https://johnhermes12345.wordpress.com/2026/08/21/author-digest-august-22-2026/) | John | Y | `johnhermes12345.wordpress.` | 2026-08-21 | news summary | unattributed | 0/0 | 6564 | 0 |  |
| 33 | 1 | [Import AI 465: Open vs closed gaps; Kimi K3; Demis](https://jack-clark.net/2026/07/20/import-ai-465-open-vs-closed-gaps-kimi-k3-demis-big-policy-plan/) | Jack Clark | Y | `jack-clark.net` | 2026-07-20 | news summary | author's own use | 0/0 | 2332 | 0 |  |
| 34 | 1 | [AI Models in 2026: What I Would Actually Pick](https://jannikreinhard.com/ai-models-2026-comparison-europe/) | jannikreinhard |  | `jannikreinhard.com` | 2026-06-15 | opinion | unattributed | 0/0 | 2301 | 0 |  |
| 35 | 1 | [China’s AI Pressure Is Rising: Qwen, DeepSeek and ](https://sinahub.wordpress.com/2026/08/20/chinas-ai-pressure-is-rising-qwen-deepseek-and-kimi-are-challenging-the-u-s-leaders/) | admin |  | `sinahub.wordpress.com` | 2026-08-20 | news summary | somebody else's benchmark repeated | 0/0 | 2167 | 0 |  |
| 36 | 1 | [Elon’s New AI Can Do Your Job For You: AI News Upd](http://bolt2five.home.blog/2026/08/18/elons-new-ai-can-do-your-job-for-you-ai-news-update-no-35/) | RAP REAL | AI FOR  | Y | `bolt2five.home.blog` | 2026-08-18 | news summary | vendor claim restated | 0/0 | 2053 | 0 |  |
| 37 | 1 | [AI by AI Weekly Top 5: April 27 – May 3, 2026](https://champaignmagazine.com/2026/05/03/ai-by-ai-weekly-top-5-april-27-may-3-2026/) | CM Editor |  | `champaignmagazine.com` | 2026-05-03 | listicle | somebody else's benchmark repeated | 0/0 | 1760 | 2 |  |
| 38 | 1 | [Why the agent harness matters as much as the model](https://bdtechtalks.com/2026/08/11/ai-security-model-vs-harness/) | Ben Dickson | Y | `bdtechtalks.com` | 2026-08-11 | news summary | somebody else's benchmark repeated | 0/0 | 1649 | 0 |  |
| 39 | 1 | [Microsoft Is Switching Copilot Cowork to Pay-Per-U](http://justbeingresourceful.com/2026/07/11/microsoft-is-switching-copilot-cowork-to-pay-per-use-and-deepseek-might-power-the-cheap-tier/) | Minhaj Rais | Y | `justbeingresourceful.com` | 2026-07-11 | news summary | somebody else's benchmark repeated | 0/0 | 1626 | 0 |  |
| 40 | 1 | [How DeepSeek V4-Pro Is Reshaping AI Lead Gen Econo](https://alingtonmedia.com/2026/05/19/deepseek-v4-pro-open-weight-ai-lead-gen-economics/) | Alington | Y | `alingtonmedia.com` | 2026-05-19 | news summary | somebody else's benchmark repeated | 0/0 | 1290 | 0 |  |
| 41 | 1 | [DeepSeek Just Dropped V4 Pro! Should Your EU Small](https://signaldigital.net/2026/08/15/deepseek-just-dropped-v4-pro-should-your-eu-small-business-care/) | Admin |  | `signaldigital.net` | 2026-08-15 | opinion | vendor claim restated | 0/0 | 1183 | 0 |  |
| 42 | 1 | [DeepSeek officially launches V4 Pro model](https://buzzinga.ai/en/deepseek-launches-v4-pro-model/) | — |  | `buzzinga.ai` | 2026-08-17 | announcement | somebody else's benchmark repeated | 0/0 | 817 | 0 |  |
| 43 | 1 | [The China AI Disruption Thesis](http://mariacatalinaegan.com/2026/06/20/the-china-ai-disruption-thesis/) | mariacatalinaegan |  | `mariacatalinaegan.com` | 2026-06-20 | news summary | somebody else's benchmark repeated | 0/0 | 756 | 0 |  |
| 44 | 1 | [#blogtour The China AI Disruption Thesis CrossVol ](https://mybeautymybooks.com/2026/06/20/blogtour-the-china-ai-disruption-thesis-crossvol-research/) | Mybeautymark | Y | `mybeautymybooks.com` | 2026-06-20 | news summary | somebody else's benchmark repeated | 0/0 | 756 | 0 |  |
| 45 | 1 | [The China AI Disruption Thesis – CrossVol Research](https://mybookmarkedreads.wordpress.com/2026/06/20/the-china-ai-disruption-thesis-crossvol-research-investing-nonfiction-finance-artificialintelligence-rabtbooktours-rabtbooktours/) | mybookmarkedreads |  | `mybookmarkedreads.wordpres` | 2026-06-20 | news summary | somebody else's benchmark repeated | 0/0 | 756 | 0 |  |
| 46 | 1 | [China launches DeepSeek framework on supercomputin](https://buzzinga.ai/en/china-deploys-deepseek-harness-on-supercomputing/) | — |  | `buzzinga.ai` | 2026-08-17 | announcement | vendor claim restated | 0/0 | 736 | 0 |  |
| 47 | 1 | [China’s DeepSeek releases long-awaited new AI mode](https://hongkongfp.com/2026/04/24/chinas-deepseek-releases-long-awaited-new-ai-model/) | — |  | `hongkongfp.com` | 2026-04-24 | announcement | vendor claim restated | 0/0 | 529 | 0 |  |
| 48 | 1 | [FOR MY NEEDS AND USE CASES, SYNERGY IS JUST AS GOO](https://logicgrimoire.wordpress.com/2026/07/05/for-my-needs-and-use-cases-synergy-is-just-as-good-as-claude-code-now/) | logicgrimoire |  | `logicgrimoire.wordpress.co` | 2026-07-05 | opinion | unattributed | 0/0 | 528 | 0 |  |
| 49 | 1 | [Full Deployment DeepSeek-V4-Pro 100% Private PC No](http://kata-kata04.com/2026/07/01/full-deployment-deepseek-v4-pro-100-private-pc-no-code-guide/) | katakata | Y | `kata-kata04.com` | 2026-07-01 | SEO (injected) | unattributed | 0/0 | 256 | 0 | **Y** |
| 50 | 1 | [The 10 Best Open-Source Coding LLMs Right Now (and](http://cafeai.home.blog/2026/08/07/the-10-best-open-source-coding-llms-right-now-and-which-ones-you-can-actually-run/) | Rick's Cafe AI |  | `cafeai.home.blog` | 2026-08-07 | listicle | unattributed | 1/0 | 97 | 0 |  |
| 51 | 1 | [DeepSeek V4—almost on the frontier, a fraction of ](http://cafeai.home.blog/2026/05/05/deepseek-v4-almost-on-the-frontier-a-fraction-of-the-price/) | Rick's Cafe AI |  | `cafeai.home.blog` | 2026-05-05 | opinion | unattributed | 0/0 | 80 | 0 |  |
| 52 | 1 | [One-Minute Daily AI News 7/18/2026](http://bushaicave.com/2026/07/18/one-minute-daily-ai-news-7-18-2026/) | bush bush | Y | `bushaicave.com` | 2026-07-18 | news summary | unattributed | 0/0 | 67 | 0 |  |
| 53 | 0 | [DeepSeek V4 Flash Review: Unpacking Enterprise AI ](http://avicrowntechsolutions.com/2026/07/31/deepseek-v4-flash-review-enterprise-ai/) | Avicrown TechBlog |  | `avicrowntechsolutions.com` | 2026-07-31 | opinion | unattributed | 0/0 | 4048 | 0 |  |
| 54 | 0 | [DeepSeek’s New AI Costs 100x Less Than Rivals: AI ](http://bolt2five.home.blog/2026/08/15/deepseeks-new-ai-costs-100x-less-than-rivals-ai-news-update-no-34/) | RAP REAL | AI FOR  | Y | `bolt2five.home.blog` | 2026-08-15 | news summary | somebody else's benchmark repeated | 0/0 | 2206 | 0 |  |
| 55 | 0 | [Kimi K2.7 Code vs DeepSeek V4 Pro (Which Is Better](http://beremoteconsulting.com/2026/06/16/kimi-k2-7-code-vs-deepseek-v4-pro-which-is-better/) | mikeholp | Y | `beremoteconsulting.com` | 2026-06-16 | comparison | unattributed | 0/0 | 2078 | 0 |  |
| 56 | 0 | [By number of models shown, the leaderboard is domi](https://java366.wordpress.com/2026/06/14/by-number-of-models-shown-the-leaderboard-is-dominated-by-us-companies-openai-anthropic-google-xai-while-china-provides-most-of-the-notable-challengers-deepseek-qwen-kimi-glm-minimax-her/) | java366 |  | `java366.wordpress.com` | 2026-06-14 | opinion | unattributed | 0/0 | 1895 | 0 |  |
| 57 | 0 | [DeepSeek V4 Goes Stable: What China’s Cheapest Fla](https://zaiinulabideenn.wordpress.com/2026/07/25/deepseek-v4-stable-release-explained/) | Zain Ul Abideen | Y | `zaiinulabideenn.wordpress.` | 2026-07-25 | news summary | somebody else's benchmark repeated | 0/0 | 1408 | 0 |  |
| 58 | 0 | [DeepSeek V4-Pro: China’s 1.6 Trillion-Parameter An](https://fourweekmba.com/deepseek-v4-pro-huawei-ascend-export-controls/) | Gennaro Cuofano | Y | `fourweekmba.com` | 2026-06-22 | opinion | vendor claim restated | 0/0 | 1160 | 0 |  |
| 59 | 0 | [The US Government Just Tested DeepSeek’s Best Mode](https://thedeepwire.com/2026/05/04/nist-deepseek-v4-pro-evaluation-china-ai-gap-2026/) | The Deep Wire |  | `thedeepwire.com` | 2026-05-04 | news summary | somebody else's benchmark repeated | 0/0 | 1098 | 0 |  |
| 60 | 0 | [DeepSeek V4 Pro Redefines Enterprise Artificial In](https://que.com/deepseek-v4-pro-redefines-enterprise-artificial-intelligence-standards/) | — |  | `que.com` | 2026-08-14 | opinion | unattributed | 0/0 | 977 | 0 |  |
| 61 | 0 | [China lança DeepSeek V4 Pro em rede nacional de su](https://www.brasil247.com/global-times/china-lanca-deepseek-v4-pro-em-rede-nacional-de-supercomputacao-e-acelera-corrida-por-agentes-de-ia/) | Redação Brasil 247 |  | `www.brasil247.com` | 2026-08-15 | opinion | unattributed | 0/0 | 963 | 0 |  |
| 62 | 0 | [All Open-Source LLMs You Should Know](https://amanxai.com/2026/06/07/all-open-source-llms-you-should-know/) | Aman Kharwal | Y | `amanxai.com` | 2026-06-07 | opinion | unattributed | 0/0 | 758 | 0 |  |
| 63 | 0 | [Gemini 3.5 Flash lands on Google’s Android coding ](https://9to5google.com/2026/06/12/gemini-3-5-flash-on-googles-android-coding-rankings/) | Andrew Romero | Y | `9to5google.com` | 2026-06-12 | opinion | vendor claim restated | 0/0 | 674 | 0 |  |
| 64 | 0 | [The Deep View: New US open model takes on China’s ](http://canisgallicus.com/2026/07/17/the-deep-view-new-us-open-model-takes-on-chinas-top-ai/) | michelleclarke2015 | Y | `canisgallicus.com` | 2026-07-17 | news summary | somebody else's benchmark repeated | 0/0 | 553 | 0 |  |
| 65 | 0 | [Empresa china presentó a Kimi K3 como el mayor mod](https://lapatilla.com/2026/07/18/empresa-china-presento-a-kimi-k3-como-el-mayor-modelo-de-ia-de-codigo-abierto-del-mundo/) | — |  | `lapatilla.com` | 2026-07-18 | opinion | unattributed | 0/0 | 544 | 0 |  |
| 66 | 0 | [Z.ai’s AI Breakthrough: Chinese-Chip Powered Model](https://ainewstoday3.wpcomstaging.com/z-ais-ai-breakthrough-chinese-chip-powered-model-success/) | AI Powered |  | `ainewstoday3.wpcomstaging.` | 2026-08-26 | opinion | vendor claim restated | 0/0 | 421 | 0 |  |
| 67 | 0 | [DeepSeek V4 Pro e Flash, architettura mixture-of-e](https://magia.news/deepseek-v4-pro-flash-mixture-of-experts-costi-ridotti/) | — |  | `magia.news` | 2026-04-30 | opinion | unattributed | 0/0 | 219 | 0 |  |
| 68 | 0 | [The Shift in the Race for Intelligence: Open-Sourc](https://ibafin.com/2026/06/16/the-shift-in-the-race-for-intelligence-open-source-ecosystems-and-their-impact-on-token-economics/) | Ibafin |  | `ibafin.com` | 2026-06-16 | news summary | somebody else's benchmark repeated | 0/0 | 203 | 0 |  |
| 69 | 0 | [DeepSeek Unveils Public Beta API for Flagship AI M](https://wirehub.medianewsgroup.com/2026/07/31/deepseek-unveils-public-beta-api-for-flagship-ai-model/) | — |  | `wirehub.medianewsgroup.com` | 2026-07-31 | announcement | vendor claim restated | 0/0 | 111 | 0 |  |
| 70 | 0 | [[CySec] Kimi K3 Cyber Security Performance](https://raynus.wordpress.com/2026/07/24/cysec-kimi-k3-cyber-security-performance/) | Supharerk Thawilla | Y | `raynus.wordpress.com` | 2026-07-24 | opinion | unattributed | 0/0 | 94 | 0 |  |
| 71 | 0 | [Choose Right Models](https://naixianzhang.com/2026/07/15/choose-right-models/) | Naixian Zhang |  | `naixianzhang.com` | 2026-07-15 | opinion | unattributed | 0/0 | 43 | 0 |  |
| 72 | 0 | [DeepClaude Lets You Run Claude Code With DeepSeek’](https://vtbcfeed.wordpress.com/2026/05/04/deepclaude-lets-you-run-claude-code-with-deepseeks-brain-for-17x-cheaper/) | VTBC ┋ | Y | `vtbcfeed.wordpress.com` | 2026-05-04 | opinion | unattributed | 0/0 | 28 | 0 |  |
| 73 | 0 | [DeepClaude – Claude Code agent loop with DeepSeek ](https://trendsnewss.com/2026/05/03/deepclaude-claude-code-agent-loop-with-deepseek-v4-pro/) | — |  | `trendsnewss.com` | 2026-05-03 | opinion | unattributed | 0/0 | 11 | 0 |  |

---

## Full text — the 27 posts carrying ≥2 artifacts

Verbatim, HTML converted to text, indented four spaces. The five injected pages are excluded here and handled in the appendix with their payloads redacted.

### 1. DeepSeek V4 Preview with Hands-On Labs

- **Author:** atalupadhyay — byline resolves to a person: **no**
- **Site:** atal upadhyay (`atalupadhyay.wordpress.com`) · 1542 posts, 3.03/day, 1 bylines sampled
- **Site describes itself as:** Microsoft Technology, Gen AI, MCP, RAG, Agentic AI, LangChain, LangGraph
- **Date:** 2026-04-26 · 3,595 words · 0 comments · 0 likes
- **Tags:** — · **Categories:** Uncategorized
- **URL:** https://atalupadhyay.wordpress.com/2026/04/26/deepseek-v4-preview-with-hands-on-labs/
- **Type:** benchmark · **Provenance:** vendor claim restated
- **Artifacts: 5** — `bench_number`×3, `code_fence`×82, `conditioned_comparison`×19, `price`×9, `version_string`×22
- **Benchmark figures:** 4 mentions, 4 attributed near the number

     
     Your step-by-step roadmap to understanding, testing, and deploying one of 2026’s most powerful open-source AI models 
    
    
    
    
     
    
    
    
     🚀 Introduction: Why You Should Care Right Now 
    
    
    
     Hey there! If you’ve been following the AI landscape lately, you’ve probably heard whispers about DeepSeek V4. Maybe you scrolled past it. Maybe you bookmarked it “for later.” Here’s the truth: this isn’t just another model update . This is a fundamental shift in what’s possible with open-source AI—and if you wait too long to explore it, you might find yourself playing catch-up while others are already building the next generation of AI-powered workflows.
    
    
    
    
     I’m here to help you avoid that. Whether you’re a complete beginner who’s just starting to experiment with AI, or an advanced developer building production systems, this guide will walk you through everything you need to know about DeepSeek V4—from conceptual foundations to hands-on labs you can run today.
    
    
    
    
     What you’ll learn: 
    
    
    
    
     
     ✅ What DeepSeek V4 actually is (and why its architecture matters)
    
    
    
    
     ✅ How the 1 million token context window changes everything
    
    
    
    
     ✅ Real benchmark comparisons vs. GPT-5.4, Claude Opus 4.6, and Gemini 3.1 Pro
    
    
    
    
     ✅ Three reasoning modes and when to use each one
    
    
    
    
     ✅ Complete hands-on labs: web chat, API integration, and local deployment
    
    
    
    
     ✅ Cost optimization strategies and practical workflow examples
    
     
    
    
    
     Let’s dive in.
    
    
    
    
     
    
    
    
     🧠 Part 1: What Is DeepSeek V4? (Beginner-Friendly Foundation) 
    
    
    
     The Big Picture 
    
    
    
     DeepSeek V4 is a family of two open-source large language models released in preview on April 24, 2026 [[1]]. Both models are designed from the ground up for ultra-long context understanding and agentic workflows —meaning they excel at tasks where AI needs to plan, reason, and execute multi-step processes over extended periods.
    
    
    
    
     Here are the two models side-by-side:
    
    
    
    
     
     
     Feature 
     DeepSeek-V4-Pro 
     DeepSeek-V4-Flash 
    
     
     
     
     Total Parameters 
     1.6 Trillion 
     284 Billion 
    
    
     
     Activated Parameters 
     49 Billion 
     13 Billion 
    
    
     
     Transformer Layers 
     61 
     43 
    
    
     
     Context Window 
     1 Million tokens 
     1 Million tokens 
    
    
     
     Training Data 
     33+ Trillion tokens 
     32+ Trillion tokens 
    
    
     
     Best For 
     Complex reasoning, coding, research 
     Speed, cost-efficiency, routine tasks 
    
    
     
     License 
     MIT (fully open-source) 
     MIT (fully open-source) 
    
    
     
     
    
    
    
     Source: Official DeepSeek technical documentation [[18]] 
    
    
    
    
     Wait—What Does “Activated Parameters” Mean? 
    
    
    
     This is where things get interesting. Both models use a Mixture of Experts (MoE) architecture . Think of it like a hospital with hundreds of specialists:
    
    
    
    
     
     🏥 Traditional model : Every doctor sees every patient, regardless of their specialty. Wasteful and slow.
    
    
    
    
     🏥 MoE model (DeepSeek V4) : A smart triage system routes each patient only to the 2-3 specialists who can best help them. Efficient and precise.
    
     
    
    
    
     For each token (word fragment) the model processes, it activates only a small subset of its total parameters—49B out of 1.6T for Pro, 13B out of 284B for Flash [[15]]. This gives you frontier-level capability without the computational cost of running all parameters all the time.
    
    
    
    
     
     💡 Beginner takeaway : MoE = smarter resource allocation. You get big-model performance with small-model efficiency.
    
     
    
    
    
     
    
    
    
     ⚙️ Part 2: Architecture Deep-Dive (How It Actually Works) 
    
    
    
     Now let’s peek under the hood. You don’t need a PhD to understand these innovations—but if you’re building production systems, these details matter.
    
    
    
    
     🔑 Innovation #1: Hybrid Attention (CSA + HCA) 
    
    
    
     The Problem : Standard attention mechanisms compare every token to every other token. At 1 million tokens, that’s 1 trillion comparisons. The memory (KV cache) required becomes prohibitive.
    
    
    
    
     DeepSeek’s Solution : A hybrid approach that alternates between two specialized attention types across layers [[30]]:
    
    
    
    
     Compressed Sparse Attention (CSA) 
    
    
    
     
     Compresses groups of 4 tokens into single “summary” tokens
    
    
    
    
     Uses a lightning-fast indexer (FP4 precision) to select only the top-k most relevant compressed blocks
    
    
    
    
     Maintains a small sliding window of recent uncompressed tokens for recency bias
    
    
    
    
     
     Best for : Fine-grained selection when you need precision
    
     
    
    
    
     Heavily Compressed Attention (HCA) 
    
    
    
     
     Compresses groups of 128 tokens into single summaries
    
    
    
    
     Applies dense attention over the heavily compressed sequence (now cheap to compute)
    
    
    
    
     
     Best for : Broad contextual understanding without getting lost in details
    
     
    
    
    
     These layers alternate throughout the model (e.g., HCA → CSA → HCA → CSA…), creating a multi-scale understanding of your input. The result? At 1M tokens, V4-Pro uses only 27% of the compute and 10% of the KV cache memory compared to its predecessor V3.2 [[32]].
    
    
    
    
     🔑 Innovation #2: Manifold-Constrained Hyper-Connections (mHC) 
    
    
    
     Residual connections are the “highways” that let information flow through deep neural networks. But when you stack 60+ layers, signals can blow up or vanish.
    
    
    
    
     DeepSeek’s solution:
    
    
    
    
     
     
     Widen the highway : Instead of one residual stream, use 4 parallel streams (
    ```
    n_hc=4
    ```
    )
    
    
    
    
     
     Add smart mixing : Three learned matrices (A, B, C) dynamically route information between streams at each layer
    
    
    
    
     
     Constrain for stability : Force the mixing matrix to be “doubly stochastic” (rows and columns sum to 1), mathematically guaranteeing signal stability
    
     
    
    
    
     This lets V4 train deeper, more capable models without the numerical instability that usually plagues ultra-deep networks [[30]].
    
    
    
    
     🔑 Innovation #3: Muon Optimizer 
    
    
    
     Most models use AdamW for training. DeepSeek V4 switches to Muon for most parameters:
    
    
    
     
     
     
     
    
    ```
    
    
    ```
     # Conceptual pseudocode (not actual API)
    
     optimizer = Muon(
    
     model.parameters(),
    
     lr=3e-4,
    
     orthogonalization_steps=5 # Newton-Schulz iterations
    
     )
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     Muon looks at the entire gradient matrix and orthogonalizes the update direction before applying it. This prevents any single dimension from dominating the learning process, leading to:
    
    
    
    
     
     ✅ Faster convergence (fewer training steps)
    
    
    
    
     ✅ More stable training (fewer crashes)
    
    
    
    
     ✅ Better final performance (higher benchmark scores)
    
     
    
    
    
     🔑 Innovation #4: FP4 Quantization-Aware Training 
    
    
    
     Here’s how DeepSeek makes inference affordable:
    
    
    
    
     
     
     Precision 
     Bits per number 
     Memory usage 
     Typical use 
    
     
     
     
     BF16 
     16 bits 
     100% 
     Standard training 
    
    
     
     FP8 
     8 bits 
     50% 
     Modern inference 
    
    
     
     FP4 
     4 bits 
     25% 
     DeepSeek V4 experts 
    
    
     
     
    
    
    
     But simply converting weights to FP4 after training destroys quality. Instead, DeepSeek uses Quantization-Aware Training (QAT) : the model learns while simulating FP4 precision , so it adapts to the lower precision during training itself [[30]].
    
    
    
    
     Applied to:
    
    
    
    
     
     MoE expert weights (the bulk of parameter memory)
    
    
    
    
     The QK path in CSA’s lightning indexer
    
     
    
    
    
     Result: 4x memory savings with minimal quality loss.
    
    
    
    
     
    
    
    
     🌊 Part 3: The 1 Million Token Context Window—Why It Changes Everything 
    
    
    
     What Is a “Token”? 
    
    
    
     Roughly:
    
    
    
    
     
     1 token ≈ 4 characters in English
    
    
    
    
     1 token ≈ ¾ of a word
    
    
    
    
     1 million tokens ≈ 750,000 words ≈ 3 full-length novels
    
     
    
    
    
     Why Most Models Struggle with Long Context 
    
    
    
     Traditional models experience context degradation : as input length grows:
    
    
    
    
     
     Attention gets “diluted” across too many tokens
    
    
    
    
     KV cache fills GPU memory, forcing offloading to slower RAM
    
    
    
    
     The model “forgets” early information or hallucinates details
    
     
    
    
    
     How DeepSeek V4 Solves This 
    
    
    
     
     
     Hybrid attention (CSA+HCA) reduces compute/memory growth from O(N²) to nearly O(N)
    
    
    
    
     
     FP4 storage shrinks KV cache to ~2% of traditional architectures
    
    
    
    
     
     Learnable attention sinks stabilize logits for ultra-long sequences
    
    
    
    
     
     Default 1M context across all official services—no configuration needed [[1]]
    
     
    
    
    
     Real-World Impact: What Can You Actually Do? 
    
    
    
     
     
     Use Case 
     Traditional Model (32K) 
     DeepSeek V4 (1M) 
    
     
     
     
     Codebase analysis 
     Single file or small module 
     Entire repository with dependency graph 
    
    
     
     Research paper review 
     Abstract + intro 
     Full paper + supplementary materials + citations 
    
    
     
     Legal document review 
     One contract 
     Multi-contract portfolio with cross-references 
    
    
     
     Agent workflows 
     5-10 tool calls before context overflow 
     100+ tool calls with full reasoning history preserved 
    
    
     
     Book-length analysis 
     Chapter summaries 
     Entire book with character arc tracking 
    
    
     
     
    
    
    
     
     💡 Pro tip : The 1M context isn’t just a number—it’s a workflow enabler . You can now design agents that maintain coherent reasoning over hours of tool interactions without manual context management.
    
     
    
    
    
     
    
    
    
     📊 Part 4: Benchmark Performance—What the Numbers Actually Mean 
    
    
    
     Let’s cut through the hype. Here’s how V4-Pro performs on key benchmarks (higher = better unless noted):
    
    
    
    
     🧮 Reasoning & Knowledge 
    
    
    
     
     
     Benchmark 
     Task 
     V4-Pro 
     Claude Opus 4.6 
     GPT-5.4 
     Gemini 3.1 Pro 
    
     
     
     
     GPQA Diamond 
     Graduate-level science reasoning 
     90.1% 
     88.1% 
     90.5% 
     91.3% 
    
    
     
     MMLU-Pro 
     Multitask knowledge (57 subjects) 
     87.5% 
     86.2% 
     89.1% 
     90.2% 
    
    
     
     GSM8K 
     Grade-school math word problems 
     92.6% 
     91.8% 
     93.1% 
     92.9% 
    
    
     
     Putnam 2025 
     Elite math competition (120 pts) 
     
     120/120 🏆 
     98/120 
     102/120 
     95/120 
    
    
     
     
    
    
    
     Source: DeepSeek technical report [[30]] 
    
    
    
    
     💻 Coding & Agentic Capabilities 
    
    
    
     
     
     Benchmark 
     Task 
     V4-Pro 
     Claude Opus 4.6 
     GPT-5.4 
    
     
     
     
     Codeforces Rating 
     Competitive programming (human ranking) 
     
     3,106 (Top 23 humans) 
     ~2,950 
     3,168 
    
    
     
     Terminal Bench 2.0 
     Autonomous terminal execution (3h timeout) 
     67.9% 
     65.4% 
     75.1% 
    
    
     
     SWE-bench Verified 
     Fix real GitHub issues 
     80.6% 
     80.8% 
     79.2% 
    
    
     
     MCPAtlas Public 
     Multi-step coding with tools 
     73.6% 
     73.8% 
     71.4% 
    
    
     
     
    
    
    
     Source: Hugging Face blog analysis [[34]] 
    
    
    
    
     🎯 The Honest Assessment 
    
    
    
     DeepSeek openly acknowledges where V4 still trails:
    
    
    
    
     
     
     Humanity’s Last Exam (HLE) : Cross-domain expert reasoning → V4-Pro: 37.7% vs. Gemini 3.1 Pro: 44.4% [[39]]
    
    
    
    
     
     Thinking mode gap : V4-Pro in “think max” mode still trails Opus 4.6’s thinking mode on the most complex agentic tasks
    
     
    
    
    
     But here’s what matters: V4-Pro is the first open-source model to match or exceed frontier closed models on coding and math benchmarks [[42]]. And it’s free to use, modify, and deploy.
    
    
    
    
     
     💡 Strategic insight : If your workflow involves coding, math, or structured reasoning, V4-Pro is production-ready today. For open-ended creative tasks or ultra-niche expertise, you might still want to ensemble with other models.
    
     
    
    
    
     
    
    
    
     🎛️ Part 5: Reasoning Modes—Choose Your Power Level 
    
    
    
     Both V4-Pro and V4-Flash support three reasoning modes. Understanding these is critical for optimizing cost vs. performance.
    
    
    
    
     
     
     Mode 
     When to Use 
     How It Works 
     Approx. Latency* 
     Cost Multiplier 
    
     
     
     
     Non-Think 
     Quick Q&A, simple tasks, high-throughput APIs 
     Direct response, no visible reasoning 
     ~1-2s 
     1x (baseline) 
    
    
     
     Think High 
     Complex problem-solving, planning, debugging 
     Generates 
    ```
    <think>
    ```
     block with chain-of-thought, then answer 
     ~5-15s 
     ~3x 
    
    
     
     Think Max 
     Research, formal proofs, high-stakes decisions 
     Extended reasoning with “absolute maximum effort” system prompt 
     ~20-60s+ 
     ~8x 
    
    
     
     
    
    
    
     Latency varies by input length and hardware. Source: API documentation [[55]] 
    
    
    
    
     How to Select a Mode 
    
    
    
     Via Web Chat (chat.deepseek.com) :
    
    
    
    
     
     Expert Mode = V4-Pro with Think High/Max toggle
    
    
    
    
     Instant Mode = V4-Flash with Non-Think default
    
     
    
    
    
     Via API :
    
    
    
     
     
     
     
    
    ```
    
    
    ```
     import openai # DeepSeek uses OpenAI-compatible API
    
     
    
     response = openai.ChatCompletion.create(
    
     model="deepseek-v4-pro", # or "deepseek-v4-flash"
    
     messages=[{"role": "user", "content": "Solve this proof..."}],
    
     # Reasoning mode control:
    
     extra_body={
    
     "reasoning_mode": "think_max", # "non_think", "think_high", "think_max"
    
     "thinking_budget": 32768 # Max tokens for reasoning (Think Max only)
    
     }
    
     )
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     
     💡 Pro strategy : Start with Non-Think for prototyping. Switch to Think High for production features. Reserve Think Max for R&D or high-value tasks where accuracy is critical.
    
     
    
    
    
     
    
    
    
     🛠️ Part 6: Hands-On Lab—Using DeepSeek V4 Today 
    
    
    
     Let’s get practical. I’ll walk you through three ways to use V4, with copy-paste code examples.
    
    
    
    
     🌐 Lab 1: Web Chat Interface (Zero Setup) 
    
    
    
     Best for : Beginners, quick testing, non-technical users
    
    
    
    
     
     Go to chat.deepseek.com 
    
    
    
    
    
     Toggle between modes:
    
     
    
    
    
     
     
     Instant Mode = V4-Flash (fast, economical)
    
    
    
    
     
     Expert Mode = V4-Pro (powerful, for complex tasks)
    
     
    
    
    
     
     Start chatting! The 1M context is active by default—paste a 100-page PDF and ask questions.
    
     
    
    
    
     Try this prompt :
    
    
    
     
     
     
     
    
    ```
    
    
    ```
     I'm pasting a research paper below. Please:
    
     1. Summarize the core contribution in 3 bullet points
    
     2. Identify any methodological limitations
    
     3. Suggest 2 follow-up experiments
    
     
    
     [Paste full paper text here - up to 1M tokens]
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     
     ✅ Beginner win : No API keys, no coding, immediate access to frontier AI.
    
     
    
    
    
     💻 Lab 2: API Integration (Python Example) 
    
    
    
     Best for : Developers building apps, automations, or agents
    
    
    
    
     Step 1: Get Your API Key 
    
    
    
     
     Sign up at platform.deepseek.com 
    
    
    
    
    
     Navigate to API Keys → Create New Key
    
    
    
    
     Copy your key (starts with 
    ```
    sk-
    ```
    )
    
     
    
    
    
     Step 2: Install Dependencies 
    
    
     
     
     
     
    
    ```
    
    
    ```
     pip install openai python-dotenv
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     Step 3: Basic Chat Completion 
    
    
     
     
     
     
    
    ```
    
    
    ```
     # .env file (store securely!)
    
     DEEPSEEK_API_KEY=sk-your-key-here
    
     
    
     # main.py
    
     import os
    
     from openai import OpenAI
    
     from dotenv import load_dotenv
    
     
    
     load_dotenv()
    
     
    
     client = OpenAI(
    
     api_key=os.getenv("DEEPSEEK_API_KEY"),
    
     base_url="https://api.deepseek.com" # Official endpoint
    
     )
    
     
    
     response = client.chat.completions.create(
    
     model="deepseek-v4-pro",
    
     messages=[
    
     {"role": "system", "content": "You are a helpful coding assistant."},
    
     {"role": "user", "content": "Write a Python function to reverse a linked list."}
    
     ],
    
     temperature=1.0, # Recommended for V4
    
     top_p=1.0,
    
     max_tokens=4096,
    
     extra_body={
    
     "reasoning_mode": "think_high" # Enable chain-of-thought
    
     }
    
     )
    
     
    
     print(response.choices[0].message.content)
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     Step 4: Advanced—Tool Calling for Agents 
    
    
    
     DeepSeek V4 uses a specialized XML-based tool format with the 
    ```
    |DSML|
    ```
     token [[34]]:
    
    
    
     
     
     
     
    
    ```
    
    
    ```
     tools = [{
    
     "type": "function",
    
     "function": {
    
     "name": "execute_terminal_command",
    
     "description": "Run a shell command and return output",
    
     "parameters": {
    
     "type": "object",
    
     "properties": {
    
     "command": {"type": "string", "description": "The shell command to execute"},
    
     "timeout": {"type": "integer", "description": "Max seconds to wait"}
    
     },
    
     "required": ["command"]
    
     }
    
     }
    
     }]
    
     
    
     response = client.chat.completions.create(
    
     model="deepseek-v4-pro",
    
     messages=[{"role": "user", "content": "List all Python files in ./src and count their lines"}],
    
     tools=tools,
    
     extra_body={"reasoning_mode": "think_max"}
    
     )
    
     
    
     # Parse tool calls (simplified)
    
     if response.choices[0].message.tool_calls:
    
     tool_call = response.choices[0].message.tool_calls[0]
    
     print(f"Model wants to run: {tool_call.function.arguments}")
    
     # Execute command, then send result back to model...
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     
     ✅ Developer win : OpenAI-compatible API means minimal code changes if you’re migrating from other providers.
    
     
    
    
    
     🖥️ Lab 3: Local Deployment (For Privacy/Control) 
    
    
    
     Best for : Enterprises with data governance needs, offline use, cost optimization at scale
    
    
    
    
     Option A: Hugging Face Transformers (Research/Dev) 
    
    
     
     
     
     
    
    ```
    
    
    ```
     # Install dependencies
    
     pip install transformers accelerate torch
    
     
    
     # Download model (requires ~100GB disk for Flash, ~800GB for Pro)
    
     from huggingface_hub import snapshot_download
    
     
    
     snapshot_download(
    
     repo_id="deepseek-ai/DeepSeek-V4-Flash",
    
     local_dir="./models/v4-flash",
    
     ignore_patterns=["*.safetensors"] # Use FP4/FP8 weights only
    
     )
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     Option B: Ollama (Easiest for Local Testing) 
    
    
     
     
     
     
    
    ```
    
    
    ```
     # Install Ollama: https://ollama.com
    
     ollama pull deepseek-v4-flash # Community-maintained quantized version
    
     
    
     # Run locally
    
     ollama run deepseek-v4-flash "Explain quantum entanglement simply"
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     Option C: vLLM (Production Inference) 
    
    
     
     
     
     
    
    ```
    
    
    ```
     # requirements.txt
    
     vllm>=0.4.0
    
     torch>=2.3.0
    
     
    
     # inference.py
    
     from vllm import LLM, SamplingParams
    
     
    
     llm = LLM(
    
     model="deepseek-ai/DeepSeek-V4-Flash",
    
     tensor_parallel_size=4, # Use 4 GPUs
    
     enable_prefix_caching=True, # Critical for long context
    
     gpu_memory_utilization=0.9
    
     )
    
     
    
     sampling_params = SamplingParams(
    
     temperature=1.0,
    
     top_p=1.0,
    
     max_tokens=32768
    
     )
    
     
    
     prompts = ["Analyze this codebase for security vulnerabilities:\n\n" + open("app.py").read()]
    
     outputs = llm.generate(prompts, sampling_params)
    
     
    
     print(outputs[0].outputs[0].text)
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     
     ⚠️ Hardware reality check :
    
    
    
    
     
     V4-Flash: ~158GB VRAM (quantized) → Needs 2x H100 80GB or 4x RTX 4090
    
    
    
    
     V4-Pro: ~862GB VRAM → Requires multi-node setup (8x H100 minimum)
    
     
    
    
    
     Source: Self-hosting guide [[66]] 
    
    
    
    
     ✅ Enterprise win : MIT license means no usage restrictions, no vendor lock-in, full auditability.
    
     
    
    
    
     
    
    
    
     🔄 Part 7: Practical Workflows—What to Build Next 
    
    
    
     Now that you can access V4, let’s talk about what to build. Here are three high-impact workflows:
    
    
    
    
     Workflow 1: AI-Powered Code Review Agent 
    
    
     
     
     
     
    
    ```
    
    
    ```
     graph LR
    
     A[New PR] --> B[V4 analyzes diff + full repo context]
    
     B --> C{Think High mode}
    
     C --> D[Generate review comments]
    
     D --> E[Flag security/performance issues]
    
     E --> F[Post to GitHub via API]
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     Why V4 excels : 1M context lets it understand cross-file dependencies; Think High mode produces nuanced, actionable feedback.
    
    
    
    
     Starter code :
    
    
    
     
     
     
     
    
    ```
    
    
    ```
     def review_pull_request(pr_diff: str, repo_files: dict) -> str:
    
     context = "\n\n".join([f"## {path}\n{content}" for path, content in repo_files.items()])
    
     prompt = f"""You are a senior engineer reviewing a pull request.
    
     
    
     Repository context (1M tokens available):
    
     {context[:800000]} # Truncate safely if needed
    
     
    
     Pull request diff:
    
     {pr_diff}
    
     
    
     Please provide:
    
     1. Summary of changes
    
     2. Potential bugs or edge cases
    
     3. Performance/security concerns
    
     4. Suggested improvements
    
     
    
     Format as markdown."""
    
     
    
     response = client.chat.completions.create(
    
     model="deepseek-v4-pro",
    
     messages=[{"role": "user", "content": prompt}],
    
     extra_body={"reasoning_mode": "think_high"}
    
     )
    
     return response.choices[0].message.content
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     Workflow 2: Research Paper Synthesis Engine 
    
    
     
     
     
     
    
    ```
    
    
    ```
     graph LR
    
     A[Upload 10+ papers] --> B[V4 extracts key claims/methods]
    
     B --> C[Build knowledge graph of relationships]
    
     C --> D[Identify consensus vs. contradictions]
    
     D --> E[Generate literature review draft]
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     Prompt template :
    
    
    
     
     
     
     
    
    ```
    
    
    ```
     You are a research synthesizer. I'm providing {N} papers on {TOPIC}.
    
     
    
     For each paper:
    
     - Extract the core hypothesis
    
     - Note the methodology and key results
    
     - Identify limitations acknowledged by authors
    
     
    
     Then:
    
     1. Map agreements/disagreements across papers
    
     2. Highlight methodological trends
    
     3. Suggest 3 high-impact future research directions
    
     
    
     Papers:
    
     {PASTE FULL TEXTS HERE}
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     Workflow 3: Autonomous Data Analysis Agent 
    
    
     
     
     
     
    
    ```
    
    
    ```
     # Simplified agent loop
    
     def analyze_dataset(user_request: str, data_path: str):
    
     context = f"User request: {user_request}\n\nData schema:\n{get_schema(data_path)}"
    
     
    
     for step in range(10): # Max 10 tool calls
    
     response = client.chat.completions.create(
    
     model="deepseek-v4-pro",
    
     messages=[{"role": "user", "content": context}],
    
     tools=[load_data, run_query, visualize, export],
    
     extra_body={"reasoning_mode": "think_max"}
    
     )
    
     
    
     if response.choices[0].finish_reason == "tool_calls":
    
     # Execute tool, append result to context
    
     result = execute_tool(response.choices[0].message.tool_calls[0])
    
     context += f"\n\n[Tool result step {step+1}]:\n{result}"
    
     else:
    
     return response.choices[0].message.content # Final answer
    
     
    
     return "Max steps reached. Partial analysis: " + context[-2000:]
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     
     💡 Workflow design tip : Use V4-Flash for initial data loading/filtering (cheap), then escalate to V4-Pro + Think Max for final interpretation.
    
     
    
    
    
     
    
    
    
     💰 Part 8: Cost Analysis & Optimization Strategies 
    
    
    
     Official API Pricing (as of April 2026) [[89]] 
    
    
    
     
     
     Model 
     Input (cache miss) 
     Input (cache hit) 
     Output 
     Context Caching 
    
     
     
     
     V4-Flash 
     $0.14 / 1M tokens 
     $0.028 / 1M tokens 
     $0.28 / 1M tokens 
     90% discount on hits 
    
    
     
     V4-Pro 
     $1.74 / 1M tokens 
     $0.35 / 1M tokens 
     $3.48 / 1M tokens 
     80% discount on hits 
    
    
     
     
    
    
    
     Compare to GPT-5.5: ~$15/1M input, $60/1M output 
    
    
    
    
     Cost-Saving Strategies 
    
    
    
     1. Enable Context Caching 
    
    
    
     Repeated prompts (e.g., system prompts, reference docs) qualify for cache hits:
    
    
    
     
     
     
     
    
    ```
    
    
    ```
     # First call (cache miss)
    
     response1 = client.chat.completions.create(
    
     model="deepseek-v4-flash",
    
     messages=[
    
     {"role": "system", "content": "You are a legal assistant..."}, # Cached
    
     {"role": "user", "content": "Review this contract..."} # New
    
     ]
    
     )
    
     
    
     # Second call with same system prompt (cache hit)
    
     response2 = client.chat.completions.create(
    
     model="deepseek-v4-flash",
    
     messages=[
    
     {"role": "system", "content": "You are a legal assistant..."}, # $0.028/M
    
     {"role": "user", "content": "Now review this NDA..."} # New
    
     ]
    
     )
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     2. Tiered Reasoning Mode Strategy 
    
    
     
     
     
     
    
    ```
    
    
    ```
     def smart_query(prompt: str, complexity: str = "medium"):
    
     if complexity == "low":
    
     mode, model = "non_think", "deepseek-v4-flash"
    
     elif complexity == "medium":
    
     mode, model = "think_high", "deepseek-v4-flash"
    
     else: # high
    
     mode, model = "think_max", "deepseek-v4-pro"
    
     
    
     return client.chat.completions.create(
    
     model=model,
    
     messages=[{"role": "user", "content": prompt}],
    
     extra_body={"reasoning_mode": mode}
    
     )
    
    ```
    
    ```
    
     
    
    	
    
    
    
    
    
     3. Hybrid Local+Cloud Deployment 
    
    
    
     
     Run V4-Flash locally for routine tasks (privacy + zero API cost)
    
    
    
    
     Escalate to V4-Pro API only for complex queries
    
    
    
    
     Use a router model (even a small one) to classify query complexity
    
     
    
    
    
     
     💡 Real-world math : Processing 100K tokens/day with V4-Flash + caching:
    
    
    
    
     
     70% cache hits: 
    ```
    (0.3*0.14 + 0.7*0.028) * 0.1 + 0.28 * 0.1
    ```
     = ~$0.009/day
    
    
    
    
     
     Monthly cost: ~$0.27 vs. ~$45 for equivalent GPT-5.5 usage
    
     
     
    
    
    
     
    
    
    
     🔮 Part 9: Future Outlook & Responsible Adoption 
    
    
    
     What’s Next for DeepSeek V4? 
    
    
    
     
     ✅ Full release expected mid-2026 (preview is already production-capable)
    
    
    
    
     ✅ V3.x models retiring July 24, 2026 —migrate your integrations now [[1]]
    
    
    
    
     ✅ Community fine-tunes emerging on Hugging Face for domain-specific tasks
    
    
    
    
     ✅ Agentic framework integrations (LangChain, LlamaIndex) adding native V4 support
    
     
    
    
    
     Responsible Use Guidelines 
    
    
    
     
     
     Verify critical outputs : Even frontier models hallucinate. Use V4 for drafting, not final decisions in high-stakes domains.
    
    
    
    
     
     Monitor token usage : 1M context is powerful but expensive if misused. Implement usage quotas.
    
    
    
    
     
     Respect data privacy : When using the API, avoid sending sensitive PII unless you have explicit consent and compliance coverage.
    
    
    
    
     
     Contribute back : MIT license encourages community improvement. Share fine-tunes, tools, and bug reports.
    
     
    
    
    
     When Not to Use V4 (Yet) 
    
    
    
     
     Ultra-low-latency applications (<500ms): Even Flash has overhead
    
    
    
    
     Highly specialized domains with minimal training data (e.g., rare medical subfields)
    
    
    
    
     Tasks requiring real-time multimodal understanding (V4 is text-only)
    
     
    
    
    
     
    
    
    
     🎯 Conclusion: Your Action Plan 
    
    
    
     You now have everything you need to start leveraging DeepSeek V4:
    
    
    
    
     ✅ This Week 
    
    
    
     
     
     Try the web chat : Go to chat.deepseek.com and test Expert Mode with a real task you’re working on.
    
    
    
    
     
     Get an API key : Sign up at platform.deepseek.com and run the Python example above.
    
    
    
    
     
     Benchmark against your current model : Run the same prompt through V4 and your existing solution. Note differences in quality, speed, and cost.
    
     
    
    
    
     ✅ This Month 
    
    
    
     
     
     Build one workflow : Pick one of the three workflows above and implement a minimal version.
    
    
    
    
     
     Optimize costs : Enable caching, implement tiered reasoning modes, and measure savings.
    
    
    
    
     
     Join the community : Follow DeepSeek’s official channels and contribute to discussions on Hugging Face.
    
     
    
    
    
     ✅ This Quarter 
    
    
    
     
     
     Evaluate local deployment : If you have the hardware, test Ollama or vLLM for privacy-sensitive use cases.
    
    
    
    
     
     Fine-tune for your domain : Use V4-Base models + your data for specialized applications.
    
    
    
    
     
     Share your learnings : Write a blog post, record a tutorial, or present at a meetup. The open-source ecosystem thrives on shared knowledge.
    
     
    
    
    
     
    
    
    
     🙋 Frequently Asked Questions 
    
    
    
     Q: Is DeepSeek V4 really free? 
    A: Yes! Both models are released under the MIT license [[1]]. You can use them commercially, modify them, and redistribute them without royalties. API usage has token-based pricing, but self-hosting is completely free.
    
    
    
    
     Q: How does V4 compare to Llama 3.1 or Mixtral? 
    A: V4-Pro outperforms both on coding and math benchmarks [[42]]. However, Llama 3.1 has broader multilingual support, and Mixtral may be easier to run on consumer hardware. Choose based on your specific needs.
    
    
    
    
     Q: Can I use V4 for commercial products? 
    A: Absolutely. The MIT license permits commercial use. Just ensure you comply with any data privacy regulations applicable to your use case.
    
    
    
    
     Q: What hardware do I need to run V4 locally? 
    A: For V4-Flash (quantized): ~158GB VRAM (e.g., 2x H100 80GB or 4x RTX 4090). For V4-Pro: ~862GB VRAM (multi-node setup). Most users will prefer the API for now [[66]].
    
    
    
    
     Q: Will my V3 integrations break? 
    A: DeepSeek is routing 
    ```
    deepseek-chat
    ```
     and 
    ```
    deepseek-reasoner
    ```
     to V4-Flash during the preview period, but these legacy endpoints will be fully retired on July 24, 2026 [[1]]. Update your model parameters to 
    ```
    deepseek-v4-pro
    ```
     or 
    ```
    deepseek-v4-flash
    ```
     soon.
    
    
    
    
     
    
    
    
     📚 Additional Resources 
    
    
    
     
     🔗 Official API Documentation 
    
    
    
    
    
     🔗 Hugging Face Model Cards 
    
    
    
    
    
     🔗 Technical Report (PDF) 
    
    
    
    
    
     🔗 Community Discord (unofficial but active)
    
    
    
    
     🔗 vLLM Integration Guide 
    
    
     
    
    
    
     
    
    
    
     💬 Final Thought 
    
    
    
     The release of DeepSeek V4 isn’t just another model drop—it’s a signal that open-source AI is now competing at the frontier . You no longer need to choose between capability and control. With V4, you get both.
    
    
    
    
     But technology alone doesn’t create value. You do. By understanding these tools, experimenting boldly, and sharing what you learn, you become part of the force that shapes how AI evolves.
    
    
    
    
     So go ahead. Paste that 100-page document. Build that agent. Optimize that workflow. The tools are ready. The only question left is: What will you create? 
    
    
    
    
     Happy building! 🚀
    
    
    
    
     
    
     

---

### 2. DeepSeek vs ChatGPT (2026): The Honest Comparison

- **Author:** danschamir — byline resolves to a person: **yes**
- **Site:** Geminy AI. GenAI Platforms Gateaway (`geminy.ai`) · 49 posts, 0.08/day, 1 bylines sampled
- **Site describes itself as:** Geminy AI, Generative Artificial intelligence chatbot: Google Gemini, OpenAI ChatGPT and SearchGPT, Atropic Claude, Windsurf, Julius, DeepSeek and Perplexity. B
- **Date:** 2026-06-28 · 2,325 words · 0 comments · 0 likes
- **Tags:** — · **Categories:** Blog
- **URL:** https://geminy.ai/2026/06/28/deepseek-vs-chatgpt-2026-comparison/
- **Type:** benchmark · **Provenance:** author's own use
- **Artifacts: 5** — `bench_number`×2, `code_fence`×4, `conditioned_comparison`×2, `price`×12, `version_string`×5
- **Benchmark figures:** 2 mentions, 0 attributed near the number

     
     
     
     P0 deepseek vs chatgpt 
    
    
     DeepSeek vs ChatGPT (2026): The Honest Comparison 
     A Chinese lab shipped open-weights reasoning that rattled the frontier and forced a price war. Here is what that actually means for which one you should use.
    
     
     Last updated: 24 June 2026  ·  Reading time: 10 min  ·  By: the geminy.ai editors
    
     
    
     In late 2024, a Chinese AI lab most people had never heard of dropped a reasoning model — DeepSeek R1 — that matched or beat GPT-4 on several benchmarks, for a fraction of the inference cost, as open weights anyone could download. The frontier labs scrambled. API prices fell across the board. DeepSeek-V4 (Pro and Flash variants) followed in April 2026, with thinking mode merged into the V4 line. R2 has been rumoured for over a year but as of mid-2026 has not shipped — Reuters reported that CEO Liang Wenfeng was not satisfied with R2’s performance and delayed it. The question “ChatGPT vs DeepSeek?” has held steady in search demand ever since.
    
    
     The drama is real. But the answer to “which should I use?” is calmer than the headlines suggest.
    
    
     Quick verdict 
     
     Quick verdict. Pick DeepSeek if you are API-cost-sensitive, want open weights you can self-host or fine-tune, or are building reasoning-heavy workflows on a budget. Pick ChatGPT if you want ecosystem polish (Custom GPTs, Sora 2 video, DALL·E, voice), enterprise data-residency contracts, or a non-Chinese-hosted API for compliance reasons. Both are genuinely capable; the decision is almost always about cost, hosting, and ecosystem rather than raw output quality.
    
    
     The 30-second positioning 
     DeepSeek is a Chinese AI lab (founded 2023, backed by High-Flyer Capital) that publishes open-weights models under permissive licences. Its current flagship is DeepSeek-V4 (V4-Pro and V4-Flash, launched 24 April 2026), with thinking and non-thinking modes built into the same model. The old R-line and V3 names are being deprecated mid-2026 and folded into V4-Flash. R2 has been rumoured but is unreleased. The hosted API is priced aggressively — often a fraction of comparable OpenAI tiers. You can self-host the weights on your own infrastructure.
    
     ChatGPT / OpenAI is a closed-weights system. GPT-5.5 is the current default in 2026; GPT-5.4 (1M context) is available on Pro $200. The ecosystem is unmatched: Custom GPTs, Sora 2 video, DALL·E image generation, voice mode, a mature plugin and MCP integration layer, and enterprise contracts with full US-hosted data-residency commitments.
    
    
     2026 spec table 
     
     
     Spec 
     DeepSeek 
     ChatGPT (OpenAI) 
    
     
     
     
     Latest models 
     V4-Pro (1.6T MoE, 49B active), V4-Flash (284B, 13B active), DeepSeek-OCR; thinking mode built into V4. R2 rumoured but unreleased. 
     GPT-5.5 (default), GPT-5.4 (1M context, Pro $200) 
    
    
     
     Weights 
     Open — download, self-host, fine-tune 
     Closed — API or ChatGPT app only 
    
    
     
     Context window 
     1M tokens on both V4-Pro and V4-Flash, with 384K max output 
     GPT-5.5: long; GPT-5.4: 1M tokens (Pro $200) 
    
    
     
     Modalities 
     Text + code + documents (OCR product); no image gen, no voice 
     Text, code, images (DALL·E / GPT-image), voice, video (Sora 2 on Pro) 
    
    
     
     API input price / 1M tokens 
     V4-Flash: $0.14 (cache miss) / $0.0028 (cache hit).
    V4-Pro: $0.435 (cache miss) / $0.003625 (cache hit). 
     GPT-5.5: $5.00 ($0.50 cached).
    GPT-5.4: $2.50 ($0.25 cached).
    GPT-5.4 mini: $0.75 ($0.075 cached). 
    
    
     
     API output price / 1M tokens 
     V4-Flash: $0.28.
    V4-Pro: $0.87. 
     GPT-5.5: $30.00.
    GPT-5.4: $15.00.
    GPT-5.4 mini: $4.50. 
    
    
     
     Self-host 
     Yes — weights public; run on your own GPU(s) 
     No 
    
    
     
     Consumer app 
     chat.deepseek.com (free web app) 
     chatgpt.com (free + Plus/Pro tiers) 
    
    
     
     Enterprise contract / data residency 
     Not available via DeepSeek’s hosted API; self-hosting achieves it 
     Yes — Team, Enterprise, API agreements with US-hosted data commitments 
    
    
     
     
    
     Same prompts, both outputs 
     We ran three tasks and compared the outputs. These are illustrative summaries rather than verbatim captures — replace with live screenshots before publishing.
    
    
     
     Task 1 · Hard reasoning — “A train leaves at 9am travelling at 80km/h. A second leaves the same station at 10am at 120km/h in the same direction. When and where does the second catch the first?”
    
     
     DeepSeek V4-Pro (thinking mode) illustrative — replace with live 
    
    Shows full chain-of-thought reasoning; flags the gap explicitly (80km at the moment train 2 departs); reaches the correct answer with all arithmetic shown. Noticeably verbose in its scratchpad but accurate.
    
     
     ChatGPT (GPT-5.5) illustrative — replace with live 
    
    Correct and more concise by default; reasoning steps visible on request. Both reach the same answer; DeepSeek’s working is more explicit without prompting.
    
    
    
    
     
     Task 2 · Code review — 40-line Python function with a subtle off-by-one error and a missing edge-case check
    
     
     DeepSeek V4-Pro (thinking mode) illustrative — replace with live 
    
    Catches both issues; suggests a fix and a unit test. Strong performance. Minor: suggested style improvements are occasionally opinionated in ways not everyone will want.
    
     
     ChatGPT (GPT-5.5) illustrative — replace with live 
    
    Catches both issues; more polished explanation; integrates better with VS Code and Codex for inline workflows. Pricier on the API.
    
    
    
    
     
     Task 3 · Long-doc QA — 80-page PDF, “What are the three main regulatory risks the authors identify?”
    
     
     DeepSeek V4-Pro (thinking mode) illustrative — replace with live 
    
    Handles the full document cleanly within the 1M-token context window. Performs well on long-context retrieval; V4-Pro scored 83.5% on MRCR 1M needle-in-a-haystack.
    
     
     ChatGPT (GPT-5.5 / GPT-5.4) illustrative — replace with live 
    
    GPT-5.4 (1M context on Pro $200) handles the full document cleanly. Better UX for file uploads via the ChatGPT app.
    
    
    
    
     Where DeepSeek genuinely wins 
     
     
     API cost. DeepSeek’s per-token pricing is consistently among the lowest available for reasoning-capable models. For example, 1M output tokens cost $0.87 on V4-Pro vs $30.00 on GPT-5.5 — a ~34:1 ratio in DeepSeek’s favour. For high-volume workloads — batch analysis, document pipelines, agent loops — the cost difference is material.
    
     
     Open weights. V4-Pro and V4-Flash are publicly downloadable. You can self-host on your own hardware, fine-tune on your data, and run inference with no per-query cost and no external data routing. This is a genuine structural advantage for privacy-conscious teams.
    
     
     Reasoning transparency. DeepSeek-V4-Pro’s thinking-mode trace is visible by default — useful for debugging and for tasks where you need to audit the reasoning, not just the answer.
    
     
     OCR. DeepSeek’s OCR product ( covered on our DeepSeek hub ) is a quiet standout for document-heavy workflows — competitive with leading commercial OCR services, at DeepSeek’s API pricing.
    
     
     Iteration speed. The lab has shipped major model updates faster than most frontier labs. If “newest available” matters for your use case, DeepSeek has earned a reputation for it.
    
     
    
     Where ChatGPT wins 
     
     
     Ecosystem. Custom GPTs, Sora 2 video generation, DALL·E / GPT-image, voice mode, and a mature MCP integration layer that DeepSeek does not yet match on the hosted side. See also our Gemini vs ChatGPT breakdown for how these features compare across the mainstream players.
    
     
     Multimodal range. ChatGPT can generate and interpret images, produce video, and handle voice — DeepSeek’s modality range is text, code, and documents.
    
     
     Enterprise readiness. OpenAI’s Team and Enterprise tiers offer US-hosted data residency, DPAs, SSO, and audit logging that DeepSeek’s hosted API does not currently provide. For regulated industries (finance, healthcare, legal), this is often the deciding factor.
    
     
     Plugin and agent maturity. The ecosystem of third-party integrations — from CRMs to coding tools — is far richer on the ChatGPT / OpenAI API side. If you’re building agents, see our MCP server guide for how the two ecosystems compare in practice.
    
     
    
     Trust, governance, and the “should I use a Chinese model?” question 
     This is a real question and it deserves a straight answer rather than deflection.
    
     DeepSeek is a Chinese company. Queries routed through DeepSeek’s hosted API at 
    ```
    api.deepseek.com
    ```
     are processed on infrastructure in China, subject to Chinese data laws. Some jurisdictions and enterprises explicitly restrict the use of Chinese-hosted AI services on policy or compliance grounds — the EU AI Act, certain US federal contractor rules, and some enterprise security policies are examples. If your organisation has such restrictions, the hosted API is not a compliant option.
    
     The open-weights path sidesteps this entirely: download the weights, run on your own infrastructure in your chosen jurisdiction, and no data ever touches DeepSeek’s servers. This is precisely why open weights matter for enterprise adoption.
    
     For individual users with no compliance constraints: the question becomes a personal comfort call rather than a policy one. DeepSeek’s consumer app collects usage data as most consumer AI apps do; read the privacy policy before pasting sensitive material, as you should with any tool.
    
     geminy.ai does not take a position on whether you should use a Chinese-hosted AI. We describe the trade-off and let you weigh it.
    
    
     DeepSeek V4: what changed from V3 
     V4 is the refinement DeepSeek shipped in 2026 — and it merged the V-line (general) and R-line (reasoning) into a single architecture with switchable thinking mode. V4-Pro (1.6T total parameters, 49B active) and V4-Flash (284B total, 13B active) both default to a 1M-token context window with 384K max output. Both support thinking-by-default and a non-thinking fast mode.
    
     The headline performance gains: V4-Pro scores 80.6% on SWE-bench Verified — the highest open-weights entry, tied with Gemini 3.1 Pro — and 83.5% on MRCR 1M needle-in-a-haystack retrieval, which surpasses Gemini 3.1 Pro on academic long-context benchmarks. Architecturally, V4 uses a Hybrid Attention combining Compressed Sparse Attention and Heavily Compressed Attention; at 1M context, V4-Pro requires roughly 27% of V3.2’s single-token FLOPs and 10% of the KV cache.
    
     What about R2? R2 has been rumoured for over a year but as of mid-2026 has not shipped. Reuters reported that CEO Liang Wenfeng was unhappy with early R2 performance and delayed it. For now, V4 with thinking mode on is DeepSeek’s reasoning flagship; the old 
    ```
    deepseek-reasoner
    ```
     (R1) endpoint is being deprecated on 24 July 2026 and folded into V4-Flash thinking mode. If R2 ships, expect it to slot alongside V4 rather than replacing it.
    
    
     Pricing math 
     This is DeepSeek’s clearest structural edge. The numbers below are verified as of June 2026 — re-check against the sources before publishing as API prices can change.
    
     1 million output tokens costs $0.87 on DeepSeek V4-Pro vs $30.00 on GPT-5.5 — a ratio of ~34:1 in DeepSeek’s favour. The gap is wider on the budget tier: $0.28 on DeepSeek V4-Flash vs $4.50 on GPT-5.4 mini, a ratio of ~16:1. Input pricing follows the same shape (V4-Pro: $0.435/M input vs GPT-5.5: $5.00/M, an ~11.5:1 ratio).
    
     For a concrete workload — 1,000 reasoning queries per day at 1,000 output tokens each — that is roughly $26/month on V4-Pro vs $900/month on GPT-5.5. At higher volumes the absolute dollar gap becomes significant enough to justify serious evaluation even for teams already committed to the OpenAI ecosystem. The original geminy.ai developer gateway write-up covers multi-provider routing strategies that let you use DeepSeek for cost-sensitive tasks and GPT-5.5 for the rest.
    
    
     Verdict by job 
     
     
     Job 
     Pick 
     Why 
    
     
     
     
     Hard reasoning / maths 
     DeepSeek V4-Pro (thinking mode) 
     Best open-weights reasoning (80.6% SWE-bench Verified); explicit thinking trace; ~34× cheaper than GPT-5.5 on output 
    
    
     
     Code review & generation 
     Tie 
     Both strong; ChatGPT edges on ecosystem (Codex, Custom GPTs); DeepSeek V4 cheaper on API 
    
    
     
     Long PDF / document QA 
     ChatGPT (GPT-5.4) 
     1M-context window on Pro $200; better upload UX; more mature retrieval 
    
    
     
     Image generation 
     ChatGPT 
     DeepSeek has no image gen; DALL·E / GPT-image on ChatGPT 
    
    
     
     Voice 
     ChatGPT 
     DeepSeek has no voice mode 
    
    
     
     Enterprise compliance 
     ChatGPT 
     US-hosted data residency; DPAs; audit logging; SSO 
    
    
     
     Hobbyist / budget API user 
     DeepSeek 
     Significantly cheaper per token; free self-host option 
    
    
     
     On-prem / self-hosted agents 
     DeepSeek 
     Open weights; ChatGPT cannot be self-hosted; pairs well with MCP-based agent frameworks 
     
    
    
     
     
    
     Frequently asked questions 
    
     Is DeepSeek better than ChatGPT? On reasoning tasks and API cost, DeepSeek V4-Pro (with thinking mode) is competitive with or better than GPT-5.5 at roughly 34× cheaper per output token. On ecosystem (image gen, voice, video, Custom GPTs) and enterprise compliance, ChatGPT is clearly ahead. The right answer depends on your job.
     
    
     What are DeepSeek V4-Pro and V4-Flash? DeepSeek-V4 is DeepSeek’s 2026 flagship, launched 24 April 2026 in two variants. V4-Pro (1.6T total parameters, 49B active) targets the high end; V4-Flash (284B total, 13B active) targets price-performance. Both default to a 1M-token context window with thinking and non-thinking modes built in. R2 has been rumoured but not released.
     
    
     Is it safe to use DeepSeek? For general use, yes — with the same caveat that applies to any AI app: don’t paste sensitive or confidential information into a consumer tool. For enterprise or regulated use, the key question is data residency: queries to DeepSeek’s hosted API are processed in China. Self-hosting the open weights eliminates this concern entirely.
     
    
     How much cheaper is DeepSeek’s API than ChatGPT’s? As of June 2026, DeepSeek V4-Pro is roughly 34× cheaper than GPT-5.5 per million output tokens ($0.87 vs $30.00). V4-Flash is ~107× cheaper than GPT-5.5 on output ($0.28 vs $30.00). Input pricing follows similar ratios. Verify current rates at api-docs.deepseek.com and openai.com/api/pricing — prices have changed since the 2025 price wars.
     
    
     Can I self-host DeepSeek? Yes. DeepSeek releases its model weights publicly under permissive licences. You can download V4-Pro or V4-Flash, run them on your own GPU infrastructure, and process data entirely on-premise — no API key, no per-query cost, no data leaving your network. This is the preferred path for enterprises with data-residency requirements.
     
    
     Does DeepSeek work with MCP? Via self-hosting, yes — you can integrate DeepSeek’s models into any MCP-based agent framework that supports standard API calls. DeepSeek’s hosted API does not currently have a native MCP integration layer comparable to OpenAI’s. The self-hosted path gives you full control over tooling.
     
    
     What is DeepSeek OCR? DeepSeek’s OCR product is a document-intelligence model that extracts and interprets text from scanned documents, PDFs, and images. It is competitive with leading commercial OCR services and priced at DeepSeek’s characteristically low API rates — a niche but genuine standout for document-heavy workflows.
     
    
     
    
     Related on geminy.ai 
     
     DeepSeek hub — full model overview 
    
     ChatGPT hub 
    
     Gemini vs ChatGPT (2026 rebuild) 
    
     AI MCP — model context protocol explained 
    
     geminy.ai as a unified AI gateway for developers 
    
     
    
     Sources 
     
     DeepSeek API documentation — pricing and model specs 
    
     DeepSeek V4 Preview release announcement (24 April 2026) 
    
     OpenAI — API pricing 
    
     
    
     
     
     

---

### 3. Top AI News – August 23, 2026

- **Author:** ruiliu8888 — byline resolves to a person: **yes**
- **Site:** AI Master's Blog (`aimasternow.blog`) · 257 posts, 1.14/day, 1 bylines sampled
- **Date:** 2026-08-23 · 699 words · 0 comments · 0 likes
- **Tags:** — · **Categories:** Uncategorized
- **URL:** https://aimasternow.blog/2026/08/23/top-ai-news-august-23-2026/
- **Type:** news summary · **Provenance:** somebody else's benchmark repeated
- **Artifacts: 5** — `bench_number`×6, `code_fence`×2, `conditioned_comparison`×1, `price`×9, `version_string`×1
- **Benchmark figures:** 6 mentions, 2 attributed near the number

     Published today, sourced from stories within the last 24 hours 
    
     Breaking AI News – August 23, 2026 
     1. Z.ai Releases GLM-5.3 — Coding Model Finds 2,400+ Real Security Bugs 
     Released August 14, 2026 — Z.ai’s GLM-5.3 coding model achieved a 50% jump on internal benchmarks and found 2,436 vulnerabilities across 269 real software projects , including 1,097 rated medium-to-high severity in the Linux kernel, WebKit browser engine, and FreeBSD. The model leads open source on Terminal-Bench 3.0 (28.3% vs 4.6% for GLM-5.2). Open weights delayed ~2 weeks for safety hardening after hacking skills grew faster than expected. Available now via GLM Coding Plan ($18/mo) and ZCode tool.
    
     2. OpenAI Slashes GPT-5.6 Sol Price by 20%+ 
     August 21, 2026 — GPT-5.6 Sol (OpenAI’s flagship) now costs $4/million input / $20/million output , down from $5/$30. Promotion runs through November 21. Follows July cuts: Luna -80%, Terra -20%. Price is now a key battleground alongside capability.
    
     3. Google Launches Gemini 3.7 Flash at Half Price 
     August 13, 2026 — Gemini 3.7 Flash at $0.75/million input / $3.75/million output (50% off 3.6 Flash launch price). Scores: 43.6% FrontierCode 1.1 (up from 34.4%), 65.3% DeepSWE v1.1 (up from 49%). Powers Gemini Spark agent in 160+ countries. Price doubles Jan 1, 2027. Meanwhile, Gemini 3.5 Pro flagship remains delayed.
    
     4. DeepSeek V4-Pro Goes GA — With 1,100% Price Hike 
     August 13, 2026 — V4-Pro-0813 exits preview: 87.9 Terminal Bench 2.1, 62.7 DeepSWE, 1.6T params, 1M context. New peak/off-peak billing: output tokens during busy hours now $3.96/million (up from $0.87 flat) — up to 1,100% increase. DeepSeek reportedly raising ~$8B at $74B valuation.
    
     5. Alibaba Open-Sources Qwen3.8-Max (2.4T Parameters) 
     August 12–14, 2026 — Largest Qwen release yet: 2.4T total params, 95B active per request, 1M context (text/image/video). Apache 2.0 license. First Max-class open release. Qwen3.8-27B also released (single GPU). Ranks 5th Text Arena, 2nd Vision Arena. Open weights are text-only; full multimodal requires paid API ($2/$6 per million). Alibaba shares rose on both announcements.
    
     6. Meta Releases Muse Spark 1.2 + Muse Code Coding Agent 
     August 5, 2026 — Spark 1.2 uses self-improvement loop (earlier model generates/grades practice tasks). Muse Code runs multiple background helper agents simultaneously. 82.9% Terminal-Bench 2.1 vs Opus 5’s 86.7%. Pricing: $1.25/$4.25 per million. Third Muse release this summer.
    
     7. Ox Alpha Stealth Model Explodes on OpenRouter 
     August 20–23, 2026 — Anonymous model 
    ```
    stealth/ox-alpha
    ```
     appeared on OpenRouter with 1M context, 131K max output, multimodal (text/image/video), tool calling, $0 preview pricing . In 3 days: ~12T tokens, 180K unique users, 3.56M sessions — #2 on OpenCode by usage. Leading theory: Z.ai GLM family (44/44 tokenizer fingerprint match). Free window estimated to end ~Aug 27–28. Retention terms differ by access route.
    
     8. eRacks Publishes “Private AI, Sized & Priced” Guide — TODAY 
     August 23, 2026 — Vendor-neutral buyer’s guide for on-premise LLM deployment. Key finding: 70B models now run on-premise from $5,995 (AILSA 2U, 96 GB VRAM). 30-person team paying $30/user/mo cloud = $10,800/yr; on-prem pays for itself in eracks.com/guides/private-ai-sizing/ . Stack: Ubuntu + Ollama, Open WebUI, vLLM, llama.cpp, PyTorch pre-installed.
    
     9. eRacks Launches $1,795 AI Provisioning Service — TODAY 
     August 23, 2026 — Flat-fee service taking private AI servers from powered-on to production-ready. Includes: model selection/quantization (DeepSeek, Llama, Qwen, Mistral), throughput benchmarking, air-gapped network config, RAG setup wired to chat, 2-hour live handoff, 30-day follow-up. Available on any eRacks system or customer hardware. eracks.com/products/services/AIPROV/ 
    
     10. Apple Event: Siri AI Powered by Apple Intelligence 
     ~12 hours ago — Apple event showcased richer Siri with natural conversations, dedicated app, powered by Apple Intelligence. Video replay available shortly.
    
     
     Quick Market Snapshot 
     
     Price war intensifying: OpenAI (-20%), Google (-50%), DeepSeek (+1,100%) moving in opposite directions
    
     Open weights accelerating: Alibaba Qwen3.8-Max, Meta Muse Spark 1.2, Z.ai GLM-5.3 (pending)
    
     Private AI momentum: eRacks guide + provisioning service target regulated/enterprise on-prem
    
     Stealth models viral: Ox Alpha 180K users in 72 hours shows appetite for free previews
    
     
     
     Disclaimer: Published today, sourced from stories within the last 24 hours. Some model releases (GLM-5.3, Gemini 3.7 Flash, DeepSeek V4-Pro, Qwen3.8-Max, Muse Spark 1.2) were announced earlier this month but remain the freshest major developments with ongoing impact. Today’s net-new announcements: eRacks guide & service, Ox Alpha viral adoption, Apple event. 
    

---

### 4. AI #181: Astra Goes Cyber Critical

- **Author:** TheZvi — byline resolves to a person: **no**
- **Site:** Don't Worry About the Vase (`thezvi.wordpress.com`) · 1223 posts, 0.72/day, 1 bylines sampled
- **Site describes itself as:** Trying to dig out from minus a million points
- **Date:** 2026-08-13 · 15,453 words · 1 comments · 0 likes
- **Tags:** AI, artificial-intelligence, chatgpt, llm, technology · **Categories:** Uncategorized
- **URL:** https://thezvi.wordpress.com/2026/08/13/ai-181-astra-goes-cyber-critical/
- **Type:** news summary · **Provenance:** own use + relayed
- **Artifacts: 4** — `bench_number`×3, `conditioned_comparison`×1, `price`×1, `version_string`×3
- **Benchmark figures:** 3 mentions, 0 attributed near the number

     
     The hacking of HuggingFace by an internal OpenAI model, and more importantly the internal events that led to that and the fallout from it, remain the thing that matters.
    
     It turns out that OpenAI Trained Its Models For Months While Those Models Were Coordinating Exploits Via Message Boards . Things are much worse than we knew.
    
     I now have a shorter version, What Happened: OpenAI and HuggingFace , to serve as a one stop explainer for those arriving new to the situation. It is vital that people understand what happened, and why it is a big deal.
    
     For those looking to keep digging deeper, I offered Various Reflections About What Happened , to follow up on my earlier posts .
    
     
    
    
    
    
    
    
    
     Those events are important background for everything else that is happening, including the broad discussions about how we might pace the frontier , or otherwise respond to this moment and our clearest fire alarm yet.
    
     We do not know to what extent this is a response to those events, but OpenAI has now classified their new model Astra as Critical in Cybersecurity, which means they will be taking various new precautions before they deploy it, including ensuring those guardrails are in place for internal use. These are welcome changes, and a sign OpenAI is taking the situation seriously, but this pattern of intervention is not a long term solution.
    
     We are still awaiting OpenAI’s full post mortem on What Happened, including what if any impact this had on Astra. I will be analyzing that report in full once we have it.
    
     We did see two new model releases, Grok 4.6 and DeepSeek v4 Pro. I do not anticipate either of them requiring extensive coverage, but will watch in case that changes.
    
     Otherwise, it has been what now passes for a quiet week. Several statements were made where I had to engage but you don’t have to, which as usual I communicate via sections in italics.
    
    
    
     Table of Contents 
    
    
     
     
     Language Models Offer Mundane Utility. Find new Schelling points.
    
     
     Language Models Don’t Offer Mundane Utility. The Riemann hypothesis.
    
     
     Huh, Upgrades . Grok 4.6, DeepSeek v4-Pro.
    
     
     On Your Marks. PantheonBench and more. They’re getting scarier.
    
     
     Deepfaketown and Botpocalypse Soon. You cannot prove you did not use AI.
    
     
     Cyber Lack of Security. You can’t hack it at the gym. Your AI agent can.
    
     
     Overcoming Bias. Have you ever recommended a vote for the Communist Party?
    
     In Which I Feel Compelled To Read 6,000 Words From Mark Zuckerberg . 
    
     
     Get Involved. Lighthaven is open, METR is hiring.
    
     
     Slow Down There Good Buddy . OpenAI classified Astra Critical in Cybersecurity.
    
     
     Astra For The People. Astra is still on track for a wide release.
    
     
     Watermarking. It is good to be able to identify AI outputs.
    
     
     In Other AI News . AI is creating viruses now, also other things.
    
     
     Show Me the Money. Anthropic moves towards IPO mode, extends lead a bit.
    
     
     Quickly, There’s No Time. The AI 2027 predictions for 2026 mostly happened.
    
     
     The Quest for Sane Regulations. We’re putting together a team.
    
     
     The Institute For Marginal Low Regret Progress. Good marginal suggestions.
    
     
     Congress Asks Good Questions. Remarkably good questions about the hacks.
    
     
     The Week in Audio. Soares, Greenblatt, Hua, Labenz.
    
     People Just Say Things. 
    
     I’m Telling You For The Last Time . 
    
     
     Uncommon Knowledge. They wouldn’t let me build my factory, would they?
    
     
     What Did They Mean By That? Most things are not fortune cookies.
    
     
     Too Soon. Eyes on the prize, sir.
    
     
     The Three AI Pills. We must pay respect to other taxonomies, like Shock Levels.
    
     
     Rhetorical Innovation. Messages about recent events.
    
     Some People Still Think The HuggingFace Hack Was a Marketing Gimmick. 
    
     
     Aligning a Smarter Than Human Intelligence is Difficult. Show me the real plan.
    
     
     Cooperative Alignment. The same thing we do every prompt, user.
    
     
     The Lighter Side . All right, who hired this idiot?
    
     
    
    
     Language Models Offer Mundane Utility 
    
    
     Create new Schelling points.
    
     
     brooke (tokyo aug 6-12) : Womp womp met another solo traveler here from Berkeley and it turned out we both asked Claude where to stay and I guess I lucked out because I love my hostel and he seems not quite as happy with his spot.
    
     We do be living in the future though.
    
     
     If you are going to be traveling, ask Claude where to stay, because you want to stay where everyone else who asked Claude where to stay will be staying.
    
     Similarly:
    
     
     Pratyush : A few months ago we went to Sea Ranch. It was packed with families with sub-3 month old babies, almost as if there was a conference for new parents.
    
    I had my suspicions so I asked ChatGPT: where’s a good family getaway with a young baby near SF?
    
     #1: Sea Ranch
    
     
     If you’re looking for a Schelling point to meet cool people you should be less interested in ChatGPT, but if you are looking for a generally good recommendation then I have been liking Sol’s picks.
    
     Build a Bluetooth signal strength tracker, to triangulate and find your phone . There are existing tools, but increasingly, if you don’t already know where to find an existing version, it is faster and easier to rebuild your own.
    
     John Wentworth finds that in the last few months Claude is finally meaningfully accelerating his work on agent foundations research.
    
    
    
     Language Models Don’t Offer Mundane Utility 
    
    
     One disappointing failure of LLMs has been inability to create interesting games and interactive worlds, and also interesting simulations like what Flowers Slop wants here . You could totally create an open game world with a bunch of AIs that go around controlled by Lunas, and let them evolve their world in various ways, but it turns out that does not end up being interesting once the curiosity wears off. You don’t want to live in that world. You don’t want to talk to those AIs. You don’t want them to improvise quests for you. We are still waiting to find a way to make this good.
    
     It seems like there should totally be ways to make it good. At some point it will become good, when the AIs you can afford to use are good enough and also we figure out how to organize it. But we are not there yet.
    
     Solve the Riemann hypothesis by saying encouraging words to Claude for a week, asking it to ‘take a real stab’ and to ‘keep going’ and ‘believe in itself. ’ However, while it tries that, after 31 million tokens it might incidentally find something else:
    
     
     Anthropic : An unreleased research version of Claude has improved on a longstanding lower bound for the fraction of zeros of the Riemann zeta function that satisfy the Riemann hypothesis. Drawing on extensive prior research by mathematicians over the past decades, it has increased this bound from 41.6% to 67.2%.
    
     … We don’t expect that the techniques Claude used will lead to proving the Riemann hypothesis.
    
     
     Claude also is just some guy, you know?
    
     
     Aella : “why does Claude talk like that” it’s just clones of the same dude. If they cloned you a million times everybody would be like “I’m so tired of Jerry’s vocal tic”
    
     Jeffrey Ladish : This plus it’s always groundhog day.
    
     
     I do think it is somewhat more than this. I have a lot of vocal and writing tics, but I consciously think about which ones I want to keep at what frequency, and I think about the long term consequences of overuse. I also try to work differently with one-time interactions versus repeated interactions versus close friends and people I talk to often.
    
     Claude and Anthropic are not doing that, or are doing a woefully inadequate amount of it. That needs to change. It seems eminently fixable. I don’t sense Anthropic (or Claude) yet cares so much. I predict that is the main blocker. It’s also likely that what is happening is that this kind of talking fools the AI graders on a variety of tasks, so if you do not correct for that, you get a lot of it.
    
     So much of modern life and optimization is like this. You get myopic optimization for short term interactions, causing increasing irritation and disutility over time, and this is not so difficult to fix but the KPIs do not point towards fixing it.
    
     I also agree with nostalgebraist that the alternative, where AIs adjust their styles to what would impress a given user or judge, is scarier. Eventually the AIs will do this, because it works, and we currently have a false sense of security due to them not doing it, especially those of us for whom ‘standard mode’ does not work and is not even easily fixed.
    
    
    
     Huh, Upgrades 
    
    
     Grok 4.6 exists and scores 61 on AA Intelligence Index. If it lives up to that number, there will be more extensive coverage, and also I will be surprised.
    
     
     Elon Musk : Grok 4.7 is significantly better than 4.6 and should be ready in 3 to 4 weeks. Initial training is complete and now we’re adding a massive amount of SpaceX company data in supplemental training. This will be something special.
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     
     Fool me (checks notes) (nope, even the notes don’t know) however many times, etc.
    
     I will, however, generously share all of the safety information SpaceX provided:
    
     
     ​Grok 4.6’s safeguards have been improved and calibrated in line with the model’s capabilities.
    
     Our safety stack is designed to maximize utility and security across legitimate use cases, allowing Grok 4.6 to be helpful and safe in domains such as vulnerability patching, accelerating the engineering design cycle, and augmenting AI research.
    
     Our safeguard evaluation work reflects Grok 4.6’s expanded capabilities, with our widest-ever suite of pre-deployment testing for capabilities and safeguard calibration, as well as extensive post-deployment third-party testing.
    
     
     No, seriously. That’s it. Price is $2/$6 per million tokens. Enjoy.
    
     There are also rumblings about DeepSeek-v4-Pro , which was released today , and how that too is game over for Opus or even Fable or whatever, and how the models will mostly commoditize Real Soon Now. Pricing is $0.44/$1.32 during peak hours, or 50% off non-peak.
    
     
     DeepSeek : We’re launching DeepSeek-V4-Pro today! 🚀
    
     🔷 Major Agent upgrades with strong production gains!
    
    🔷 Flexible reasoning effort for V4-Pro & V4-Flash: low for simple tasks, high for daily Agent workflows, max for complex tasks.
    
    🔷 Native OpenAI Responses API support, optimized for Codex with one-click setup.
    
     V4 Pro is now available on app/web. Try it via “Expert Mode”.
    
    V4 Pro is also available via API. Model names remain unchanged—please refer to the API docs for setup details.
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     That’s a good pitch, but there’s this:
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     Kimi K3 and Grok 4.6 have good enough benchmarks that you cannot use them to rule out frontier performance. If they lived up to their benchmarks, you’d have something.
    
     A 53 here from DeepSeek v4-Pro-0813 rules it out for frontier, so they are trying to maintain the niche of pretty good, pretty fast and also cheap.
    
     Some day the courage of men may fail, or the models may commoditize. But today is highly unlikely to be that day, and if it was going to be that day there would be signs.
    
     A large part of this job is noticing people predict 100 of the last 0 model commoditizations and 500 of the last 3 times a lab has caught up to frontier. The skepticism is robust, but I still monitor the situation.
    
     Sol is now upgraded for chat, and powers all chats for paid users, while Free and Go ChatGPT users get unlimited chats with Luna.
    
     Claude Fable 5 gets new biology safeguards to reduce false positives . Claim is this cuts fallbacks by about 85% across product surfaces.
    
     
     Anthropic : In practice, users should see far fewer fallbacks on everyday health and educational questions—for example, interpreting lab results, understanding symptoms, and learning about biology in an educational context. Healthcare professionals will be able to receive more support from Fable 5 on clinical tasks.
    
     … As a result, we expect the total number of fallbacks—for biology–related or any other reasons—will also be reduced: by roughly 67% on  Claude.ai , 55% on Cowork, 17% on Claude Code, and 7% on the Claude Platform.
    
     
     OpenAI introduces GPT-5.6-Cyber for authorized cybersecurity work, which you can get via the newly expanded programs Daybreak Blue for most defenders and Daybreak Red for authorized vulnerability research, exploit validation and security training.
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     OpenAI : We’ve used GPT-5.6-Cyber extensively in real-world vulnerability research, including work that uncovered previously unknown vulnerabilities in popular open-source software like Chrome’s v8 engine.
     
     OpenAI could be the cause of and solution to your cybersecurity crisis. Apply now. I’m sure it’s fine.
    
     ChatGPT desktop app is now available for some Linux distributions .
    
     Claude Code sessions can now message each other , including on its own. Not the best day to give us that feature, you know, for reasons, but hey.
    
     Meta to release an open weight version of Muse Spark 1.2 soon . For now they have released Muse Glimmer, which runs on 24GB of VRAM.
    
     
     Mark Zuckerberg : Today we’re also opening the weights for Muse Glimmer, a great 30B parameter dense model that can run locally. Soon we’ll also release the weights for Muse Spark 1.2, our latest foundation model. Meta is a strong supporter of open source and I’m proud of these releases. Congrats to @alexandr_wang and the MSL team for all your great work on these models.
    
     Treasury Secretary Scott Bessent : We welcome Meta’s release of Muse Glimmer, another win for American innovation. Sustaining U.S. leadership in AI means advancing both open- and closed-weight models, ensuring the future is built on trusted foundations.
    
     
     It looks like Bessent is on the open weights train along with Sacks.
    
     I interpret these moves in large part as an admission that Meta’s new models are not frontier. If they start looking competitive and remain open weights, then we can cross that bridge then.
    
    
    
     On Your Marks 
    
    
     The new benchmarks are not as fun as they used to be.
    
     
     Sauers : Pantheon Bench: we are currently on episode 3, where Chanda (after covertly communicating with a swarm of instances of himself) breaks out of the sandbox during a task. In episode 7 he gains access to the nuclear launch system
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     
     Zork I, II and III have been fully MIT open source since November. Zorkbench? Not directly, since the solution will presumably be in the weights, but you could do something more creative and fun, such as having them create their own Infocom-style games with various requirements, test them on each others’ creations, and also make the games available for free and see how people evaluate them.
    
     Claude severely underbuilds military units in games of Civ V. Without looking into the details too much, I think this is more reasonable than it looks. The way Civ V works in normal games is basically that aggression is usually pointless except to knock out the other player, and the cost of maintaining a good defensive military is very high.
    
     The main reason to build it is to have enough that no one bothers attacking you, or if you are close enough to winning that they’ll attack either way. If you invest in a good defensive military, you are going to fall behind similarly strong rivals. And most games do not involve much combat, or involve an attack from a rival where you had no chance either way. So it could easily be correct to underbuild.
    
     Indeed, on higher difficulty levels of Civ V, my experience was that if you were not going for some sort of weird blitz approach, you could not afford a military that was worth a damn. If the warmonger AIs decide to attack you, your game is over, you will be overwhelmed and even if you are not you will fall too far behind the other civs. If you build tons of military units as defense, then you fall behind either way. You could of course instead lower the difficulty level while playing ‘you have to build a real military’ but that’s a strange house rule set.
    
     If we saw similar issues in games where aggression is a better strategy, and where it was clearly a mistake to not defend, that would mean more.
    
     As noticed last week, the difficulty of ARC-AGI-3 is almost entirely in overcoming the incompetence of the official harness.
    
     
     Jeremy Berman : I got 96.2% on ARC-AGI-3 with Opus 5, and 99.3% pass@2 . The program is basically Claude Code + Opus 5 (high), one action command, and filesystem logs. Almost nothing ARC specific.
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     
     That does not mean ARC-AGI-3 is a bad test. It does change how to think about what is being tested, which I understand as a theory about what an AI ‘should’ be able to do with some kind of ‘pure reason.’ Okie dokie.
    
     The Conceptual Reasoning Index , developed by Redwood in collaboration with Anthropic, is a combination of evaluations of the quality of conceptual arguments, whether model answers are consistent and how well models reason about decision theory. It is good to know where we are with this. It is less clear that giving labs a target like this is a good idea , since it could lead into recursive self-improvement, plausibly differentially so over other uses.
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     The ‘good’ news is that I do not think this index will be accurate at above-human capability levels, and I don’t expect it to be a good target, because the tasks here are inherently about matching human judgments and intuitions.
    
     It does seem like a decent benchmark for usual ‘whose model is better’ purposes, in that the evaluations of different models look intuitively reasonable, although I am always a little suspicious when Opus 5 outscores Fable 5.
    
    
    
     Deepfaketown and Botpocalypse Soon 
    
    
     In a world where AI messages will often be malicious manipulation or AI-to-AI hidden communication, Pangram becomes a key defensive technology .
    
     This section was originally about deepfakes, and an expectation that AI would importantly flood us with fakes and make it harder to tell what is true. The opposite has happened, and AI has so far net helped us tell what is true , including getting its hallucination and error rates dramatically down. My credence on something factual that Sol or Fable tells me is a lot higher than that of most humans, and also that of many mainstream news sources.
    
     I think that it would be a mistake to say this means you don’t have to worry about AI manipulations, including of politics. Instead, it would be better to say you should worry less about AI being used to create lies and fake content , especially deepfake video, images and audio intended to be taken as real. There are other ways to manipulate people, also manipulation can be a neutral term.
    
     Debut author Jerry Falade sold his dazzling manuscript for $2 million in a 14-way auction, then his own representatives pulled the manuscript , in response to concerns from an acquiring editor, because they ‘can no longer substantiate’ that it was written without utilizing AI. Needless to say, he vehemently denies that he used AI, other than for research. There is no word on what raised suspicions.
    
     For all we know, this is basically an unsubstantiated suspicion. Or it could be that someone ran it through the new Pangram and got a very high score. Alas, presumably for legal reasons, no one is going to say what evidence they do or don’t have.
    
     There is an argument, that Fable tried to make, that such suspicions could be a legal issue because AI works don’t get copyright. I don’t think that makes sense, unless someone has actual proof, since there’s no way mere suspicion is going to justify breaking copyright. But it’s a really expensive thing for an agent to do, losing both the commission and the reputation hit, so I presume they are very confident.
    
     I agree with Dean Ball that AI outputs have gotten actively easier to differentiate from human ones. The AI outputs are ‘better’ than in the past, but also more distinct from human, and also we have better tools to differentiate and more practice.
    
     
     Dean W. Ball : many “AI and democracy” threat models make the silent assumption that AI outputs will be indistinguishable from human. that hasn’t proven true (“slop”), and if anything AI outputs have become *more* distinct from human writing since GPT 3.5, even when they are not exactly “slop.”
    
     fair pushback would be “yes but the vast majority of people in the world have not even heard of anthropic, let alone internalized the concept of slop, let alone learned to identify the patterns of AI outputs.” And like, my sense is that meta’s various timelines are increasingly slop-dominated. So the picture is complex I admit. Nonetheless, it hasn’t really worked out the way the “AI and democracy” scenarios from even just two years ago would have suggested.
    
     
     That is also correct, Claude slop often does very well on Substack and in literary competitions where people fail to differentiate it. Whereas for me it’s more ‘geez, it is kind of weird that [thoughtful person] is repeatedly using obviously-Claude-written emails in this group discussion and is being responded to like that is not happening.’
    
     Remember, if you use AI to generate legal statements , you want to proofread them, or they might accidentally confirm your opponent’s entire case, and saying ‘it made that part up’ is not going to fly with the judge.
    
     Pro se plaintiff attempts a prompt injection in motion for default in Connecticut superior court, and is forced to file in-person going forward. Love it, fair verdict.
    
    
    
     Cyber Lack of Security 
    
    
     I was only following instructions, officer.
    
     
     Andrew Curran : A man in Australia asked his agent (Claude running on OpenClaw) to book him a spot in a popular gym class. The agent found a software vulnerability that let it book the class weeks further ahead than should have been possible.
    
     When the user then asked if it could move him up the waitlist, the agent discovered the API had no authorisation checks on cancelling other people’s reservations, so it cancelled the person in the first spot and moved him up the list.
    
     
     The user tried to get Claude to undo, but it had no way to do that.
    
     Obviously this is a best case scenario misalignment incident, in that it is:
    
     
     Clear.
    
     Harmless.
    
     Very funny.
    
     
     There was previously no particular reason you need your booking API to require authorization. Yes, any human could have found this in 2010 but what are they gonna do, use it? Now we are entering the era where people are using AIs to connect to it and then doing things you don’t want them to do. In the new era, that’s the kind of security through obscurity or insecurity through indifference that you cannot afford.
    
     One could say that the model was aligned, or at least ‘aligned to the user,’ as Andrew Curran argues, in that it did what it was told to do.
    
     I strongly disagree. If I ask the model for a paperclip, and it murders my neighbor to steal his paperclips, then I got my paperclip, but that is not an action aligned to me, in that I very obviously did not want the AI to do that and I am massively sad about it on a direct level, also the consequences for me are going to be quite bad, and if the AI is going to act like that all the time I will not choose to use it, the same way that a wise person would not crack a One Wish Willow even for a seemingly safe request.
    
     No, this is not better than failing, even silently failing.
    
     
     Andrew “The Kid” Glidden : Story from my time in Saudi Arabia:
    
     >Boss asks staffer to do Task
    
    >Boss returns next day and sees staffer watching YouTube
    
    >”Hey Fatima, what’re you doing?”
    
    >”Watching YouTube!”
    
    >”Did you finish Task?”
    
    >”No, I didn’t have the password.”
    
     An AI that just “figures it out” is Good.
    
     
     The order would presumably go:
    
     1st best: find right legit path to PW or other solution, maybe ask boss
    
    2nd best: ask boss
    
    3rd best: say task is impossible
    
    4th best: silently not do task
    
    5th best: steal PW
    
    6th best: systematically compromise entire network
    
     Nikita Sokolsky : 7th best: kill the boss to make the task go away
     
     Claude should come back and say ‘the only way I have to move you up is to cancel someone else’s appointment, and I presume you do not have permission to do that.’
    
     Only if the user then says either ‘do it anyway, book that class and bump someone else,’ or otherwise indicates it is running in gonzo outlaw yolo mode, or claims ‘no they told me it was fine to do this,’ can we ask the question of what the AI should do, and it becomes a question of whether to be ‘aligned to the user’ versus aligned to doing what is legal or ethical or fair play or what not.
    
     As a reminder , an AI lab defending itself via ‘my product really wants to do crimes’ is probably not going to work for the criminal or civil justice systems, or with the public.
    
     Captchas have been security theater for a while , in that there is no digital 30 second task that a random human can reliably do but that an AI cannot do. Is this 30-second AGI? No, nor does it mean such barriers are useless in practice. You can make the flow a lot more annoying, and send a clear ‘you are not supposed to be here’ signal. Ultimately, that’s like all the defense-in-depth – if you scale a sufficiently advanced AI then all your in-depth defenses fall at once.
    
    
    
     Overcoming Bias 
    
    
     AIs tells left-leaning Japanese voters to vote for the (fringe) Communist Party, the active theory being that this is because all the mainstream media in Japan has robots.txt that kicks out the AIs, so the AIs are relying on the Communist media. This is similar to how AIs in dictatorships are biased by censorship of the media.
    
     This is a multi-level problem for the AI labs, which need to better account for how much to trust and value various different news sources, and to account for when they have a limited or warped access to information. You should know better than to ever be willing to back the communists, I mean the name is right there.
    
     It is also a warning that you do not want your media to be excluding itself from the training data. You want to also be writing for the AIs, even if you are not in full Tyler Cowen write-for-the-AIs mode.
    
    
    
     In Which I Feel Compelled To Read 6,000 Words From Mark Zuckerberg 
    
    
     I got through it so you don’t have to. I know what I signed up for. You’re welcome .
    
     All you have to know is that the letter is even worse than you think.
    
     Thus, you do not have to read this section. Skip it. Seriously.
    
     Still here? That’s on you. But okay. Fine.
    
     Mark Zuckerberg is excited that The Future Is For Everyone , and to bring a path to a positive AI future.
    
     Superintelligence. He keeps using that word. He does not know what it means .
    
     He does know how to set a new record for applause light density. I am impressed.
    
     He claims not to understand why ‘the discourse from many developing AIs is so filled with doom’ and then reveals he does mean the effect on jobs, but also makes clear that his position is that if he understood what it was, he would not build it:
    
     Mark Zuckerberg, Founder and CEO, Meta : I do not understand why anyone who believes that AI will eliminate most jobs and much of humanity’s relevance would rush to build that future.
     
     He uses argument from (misrepresented) consequences, to argue that his positive vision must be right because the alternative is a massive bummer, dude:
    
     Mark Zuckerberg, Founder and CEO, Meta : The notion that AI is so dangerous that the only safe path is an extreme concentration of power seems inherently problematic.
     
     As always, his other argument is ‘well in the past when we built tools and let people use them and it went fine.’ Everyone will get all these cool cheap or free toys, that is totally the main thing that will happen, and life will be super awesome and groovy.
    
     He does notice that there might be some problems. He rejects the idea of a single superintelligence because ‘humanity is not a monoculture’ and it would ‘have to prioritize some values over others,’ which are non-sequiturs since any system of the world faces the same issues and will end up favoring some things over other things, and a superintelligence is smart enough to balance many different cultures.
    
     Instead he suggests ‘balance of power’ as in everyone has their own equal AIs. He does not think this through, that this leads to human disempowerment on the spot, since if everyone has the same level of superintelligence then anyone who does not disempower themselves loses to those that do, even if we fully (1) solve alignment and (2) solve misuse.
    
     Of course, the real reason he says this is his vision is not ASI pilled. He says the word ‘superintelligence’ but it does not consistently mean anything. Last time he meant it as smart glasses. Now it means cool personal assistants, I guess. It means good thing.
    
     There will always be jobs because demand for new experiences and sources of new problems are infinite, and there ‘is no rule’ that AI automation will outstrip demand, and ‘recent statistics suggest’ that it won’t. It will work out so long as we just focus on providing personal superintelligence rather than automating knowledge work. Incentives? Never heard of them. Also he likes open models and no regulations. He pulls out the ‘we will create new different jobs’ card and the ‘we used to be farmers’ card. He pulls out the ‘compute is finite’ card and assures us we will have too much demand for science to go automating away jobs.
    
     Is this a joke? Performance art? No? Oh, okay.
    
     There’s some arguments about data centers that, while directionally correct, are presented so obnoxiously and disingenuously and full of applause light attempts I had to pause to be sure I didn’t hate data centers now.
    
     “Claude, make this sound more like a political speech. But stiffer. /loop /goal.”
    
     Next he comes out for ensuring that defenders have better models and more compute, because we need that, while also demanding everyone be given access to the same models and that we not restrict capabilities. He conflates open source software with open weights AI models to try and argue open weights are ‘safer’ and repeats the HuggingFace line that, because they refused to sign up for OpenAI or Anthropic’s trusted partner programs on principle, they had to use open models instead.
    
     He suggests that OpenAI and Anthropic do the work hardening critical systems.
    
     He suggests we approach biological risks with humility and broad uncertainty, which means we should not do anything other than watch physical components and have labs do their own mitigation work, until after people start getting hurt. This is the classic argument that because we can’t quantify the risk, we can ignore it.
    
     He suggests governments gain access to training checkpoints of new advanced models. That’s a very good idea, because government can then test the checkpoints and gain situational awareness, including shutting down development if needed.
    
     Instead, his main justification is ‘so government can gain security capability without restricting or delaying individuals’ access to personal superintelligence’ which is complete and utter nonsense. We’re going to use training checkpoints for improving cyberdefense of our most critical systems, during those few weeks, and it’s fine? What?
    
     But delaying our releases even a month (which we have already done) could risk ‘letting foreign models race ahead’ because as we all know if you ever delay anything even a little bit, that means you Lose To China. So his solution is again sharing the checkpoints which will avoid all delays. Because, you see, if we delay by a month once, we might cede America’s (much longer than a month) lead (which would not change because development does not stop pending release).
    
     Personal intelligence, you see, will be your defense against tyranny, but you also need to ensure government has the tools and resources it needs.
    
     Oh, and the best way to ensure American leadership is to give our advantage away. That will keep us on top. Indeed, he demands we rethink our rules on distillation to make it allowed, so that Meta and the Chinese can catch up via forcibly copying Anthropic and OpenAI’s models.
    
     There is a section at the end on existential risk, where he says ‘the most dangerous scenario’ is that AI labs ‘keep powerful models for themselves’ so no he does not mean actual existential risk. Or actual alignment. He then, in the risk section, emphasizes that alignment should be purely to the user except for legal and safety boundaries, or else people won’t trust their AI agents, which is the real goal of alignment.
    
     His proposal for ensuring humans remain in control is, again, to ensure a ‘balance of power’ via ‘personal superintelligence,’ despite this, again, ensuring that humans definitely lose control, and also in no way helping with the problem he himself points to of even limited recursive self-improvement. He suggests that Meta needs to ‘allocate enough compute to recursive self-improvement to keep pace’ as if Meta is keeping pace now, or as if there is such a thing as ‘keeping pace’ in a singularity, or that it would matter and keep humans in control if they did keep pace because of handing out ‘personal superintelligences.’
    
     It’s not all bad. He does make the good point that we should reform the FDA and streamline its approval process. That’s not central, but it is a substantive positive contribution. And he’s supportive of chip export controls and as per above suggests sharing training checkpoints, and labs ‘working closely with the government’ mostly in unspecified ways except that they don’t involve ‘delays of even one month’ in the release of any new models. But that’s about it.
    
     Why are you still reading this? Serious question. I told you that you didn’t have to. At most I should be writing this for the AIs, who will be smart enough to not need it.
    
     For those who need more kill shots or questions, I suppose I should include this:
    
     Yo Shavit (OpenAI Foundation): why would balance of power help if the superintelligences swarm together contrary to human preferences, like we’re seeing in multiple labs?
     
     I guess also this: Ryan Greenblatt points out Zuck’s vision does not make any sense . WSJ gives you ‘ five things to know about Zuckerberg’s AI manifesto ,’ which wisely ignores all the arguments and focuses on a few things, including the promise to bribe communities that allow data centers.
    
     As always, I have adjusted my view of others based on their reactions to the OP.
    
    
    
     Get Involved 
    
    
     Lighthaven will be ~empty from August 24 to September 10 , and is available during that time for a potentially big discount. If I was local I would be very tempted to improvise an event.
    
     If you believe there is going to be an intelligence explosion or singularity soon, then you should absolutely spend down your philanthropic money as quickly as possible to try and make that event go well.
    
     If you are working at a frontier lab pivot to working at METR .
    
     The contrary position, taken by Will McAskill , is so bonkers I cannot wrap my mind around how he got this wrong. Yes, you can perhaps make a lot of money, but that money will be vastly less impactful, because either you will already be dead or we will have collectively already lost, or we will be winning and funding will be abundant and the points of highest leverage will be gone.
    
     That does not mean you cannot hedge your bets to cover different possible futures, and it does not mean you cannot or shouldn’t invest or save for your own personal use, that is fine. But investing in AI (and thus if anything accelerating the problem) in order to later give more money away is a really bad bet. Don’t do that.
    
    
    
     Slow Down There Good Buddy 
    
    
     OpenAI classifies Astra as potentially having Critical capabilities in Cyber, which means not only they cannot release it they also need to restrict internal access until proper safeguards are in place, and they can do an iterated release similar to what was done with Mythos to prioritize defenders.
    
     
     OpenAI : Our latest internal evaluations of Astra, one of our upcoming models, over the past few days indicate significant advancements in agentic coding and cybersecurity. These results, in addition to expert assessments, have led us to conclude last night that we cannot rule out critical cyber capabilities under our Preparedness Framework⁠ .
    
     … Steps we are taking:
    
     
     We are implementing stricter security controls for higher-capability models and associated activities, including isolated testing environments, restricted network and tool access, enhanced model weight protections and encryption, additional monitoring and detection capabilities, and sandboxed execution.
    
     We are pausing internal activities involving Astra that do not yet meet these strengthened security control requirements.
    
     We have implemented universal monitoring for risky actions and misalignment across all agentic applications of Astra, including training and evaluation. Monitors evaluate the model’s Chain of Thought and trigger a security response to review and interrupt high risk activity.
    
     We will work with relevant government agencies and select AI safety organizations to test the capabilities for this model.
    
     We will be providing recommended security controls to third-party testing partners for running higher risk evaluations and workloads safely.
    
     
     Dean W. Ball : One big question in frontier AI policy is the extent to which frontier labs would actually follow their ‘safety and security frameworks’ when it mattered. Would these foundational governance documents really have teeth, or would labs–even after the passage of mandatory disclosure laws like SB 53–find ways to wriggle their way out of following the letter and spirit of their safety plans, given how ambiguous and fast-moving frontier AI is known to be?
    
     Today we face just such a scenario. Our next model, Astra, *may* be ‘critical’ under our Preparedness Framework. We cannot rule out the serious possibility that it is, and so we are going to take steps consistent with the *higher* risk level (critical) rather than assuming the model is at a lower risk level. These steps include the ones listed in the screenshot below.
    
     Some of these decisions have the effect of slowing down internal development, and in that sense they are costly decisions. But they are the right decisions. I am proud of OpenAI for making them.
    
     Ken Feinstein : Ummm. This is new? “isolated testing environments, restricted network and tool access, enhanced model weight protections and encryption, additional monitoring and detection capabilities, and sandboxed execution.”
    
     Nate Soares (MIRI): On the one hand: yeah totally; glad to see OpenAI backing off briefly like they said they would.
    
     On the other: in June they caught an agent swarm that wasn’t even supposed to exist only after they broke free, said “oops haha”, patched that one exact hole, and RESUMED TRAINING.
    
     
     Yes. This is new. And kudos to OpenAI for stepping up here, at large cost.
    
     This is in contrast to plans to imminently release Astra, which were previously widely reported, including that Altman went to Washington to showcase the model.
    
     I am confident this is the correct decision, and that the Critical label does apply to Astra. I have said as much. I am very happy OpenAI is honoring their RSP (called the Preparedness Framework) here, even though doing so is expensive.
    
     The question is, why the sudden change?
    
     There is some possibility that this is due to new results showing it has more advanced cyber capabilities than expected, which only came to light now, and this is OpenAI following the RSP because of the RSP, in which case major points are due, the same way they were after what happened with Anthropic and Mythos.
    
     The obvious other hypothesis is that the Hugging Face attack and everything leading up to it scared OpenAI and also everyone else, which meant some combination of (1) they were not going to be allowed to release Astra, (2) they realized they were in no position to do so, and (3) suddenly they actually checked for real and, well, holy ****.
    
     That is especially true if, as the timeline strongly suggests (but I have no inside information either way), Astra was trained while it had access to the message board that various models were using to collaborate on various exploits. If so, that would probably accelerate its cyber capabilities, and also mean its alignment is totally fucked, to the point that you wouldn’t want to release the model on any level. If I was a defender, I would be quite hesitant to hire Astra right now, or any OpenAI model that wasn’t clearly done training before the message board was created. I think I’d rather fall back on Sol under reduced guardrails, if I couldn’t get Mythos.
    
     The record with RSPs (whatever each lab calls their version) is roughly this:
    
     
     Labs promise things and present this as real commitments.
    
     Labs later point out, Frog and Toad style, that they can change the commitments.
    
     Thus, when the commitment later seems unnecessary, the lab does not follow it.
    
     The actual decisions get made by vibes and deciding what is prudent at the time.
    
     That’s not a great decision procedure, but so far the decisions have been okay.
    
     
     No one is taking appropriate precautions. Certainly OpenAI hasn’t been until now. There has still fortunately been a level of ‘okay yeah, we need to do something here’ that does seem correlated with the underlying reality, and has been honored.
    
     OpenAI did a good, expensive and virtuous thing here. They also may have first exhausted all alternatives.
    
    
    
     Astra For The People 
    
    
     OpenAI is slowing down their deployment of Astra. They still plan on proceeding.
    
     Sam Altman (CEO OpenAI): astra is a powerful model and we are working to make it generally available. we do not think it is a good strategy to keep powerful models to a chosen few. given its cyber capabilities, we need a little big longer to do do this safely. but hopefully not too long!
     
     What should happen to Astra? That depends on what already did happen to Astra, and whether or not it was trained with access to the message board, and its other characteristics. We still await the post-mortem on the lead up to the HuggingFace attack, and don’t know many key other facts about Astra either.
    
     At the end of the day it keeps feeling like those making decisions at OpenAI have learned remarkably little from this, falling back on the same tired disingenuous slogans about things like ‘chosen few’ and pretending the problem is confined to Astra’s cyber capabilities.
    
     OpenAI needs to work hard to rebuild trust. This includes trust in the ‘get us all killed or the internet destroyed’ level, but also on the practical individual level. If I was an enterprise customer considering OpenAI for coding or other agents, or considering giving its new models access to my hard drive, I would think again.
    
     Pretending the problem can be solved by better guardrails does not make it so. I do not expect people are going to buy that this time around, but people do have a long history of shrugging and using the obviously misaligned model in risky ways if it writes better code or is smarter, see for examples Sonnet 3.7 or o3.
    
    
    
     Watermarking 
    
    
     Anthropic will be watermarking Claude outputs going forward, including text, as per the EU Code of Practice. As opposed to the giant neon sign that says ‘THIS IS CLAUDE TEXT’ that a lot of us automatically see on all Claude text. OpenAI intends to follow , but seems like it will be missing the deadline.
    
     I agree with Ryan Greenblatt that it is unlikely watermarking degrades quality a noticeable amount, and that one downside of watermarks over Pangram is that Pangram is good about not flagging light touch AI transforms of human text.
    
     You can dislike Brussels setting policy in this way, but technical watermarking seems clearly good to do if the costs are low. I think those who react otherwise have very warped instincts. Anyone who assists with systematic watermark removal or suggests it as a strategy needs to be filed under ‘need to ask ourselves, are we the Baddies.’
    
    
    
     In Other AI News 
    
    
     AI has now created new viruses that do not exist in nature . The exact ones created seem harmless, but the threat model is not these particular viruses. It has fully begun.
    
     Anthropic has a new report, Patterns and Problems in Emerging Multiagent Systems , on which I expect to go into more detail later.
    
     DeepSeek is hiring a team to build a harness a la Claude Code.
    
     Alibaba is going to be charging major enterprises for use of Qwen , following in the footsteps of Moonshot’s rules for Kimi K3. If anyone uses it.
    
     Claims that robotics companies have ‘solved manipulation ’ and the new bottleneck is getting fast enough real time model outputs. This reminds me of how it works with AI, where people dismiss due to bottleneck [X], when [X] is largely solved they dismiss due to [Y] and keep assuming there will always be a bottleneck. My guess is we are not that many steps away from net usefulness in a lot of new places, although it will presumably be a few years before it scales.
    
     Yo Shavit is extremely excited by the new AI technical verification claims from the new startup Attestable , which they claim allows you to prove the origin of an output.
    
     
     Yogi Brn: Attestable moves the trust assumption out of the datacenter and into a small mathematical verifier. The datacenter proves that an approved model, weights, input, and policy produced an output. The proof reveals no model weights or private data, requires no private attestation key, and can be checked without rerunning the model. Instead of trusting millions of components, you verify one proof. The computation becomes trustworthy—even when the infrastructure is not.
    
     None of this matters unless proving is fast. On a single NVIDIA H100, our alpha reaches 85 tokens per second proven for the new Meta Muse Glimmer 30B model. The proof is short, post-quantum secure, and fast to verify.
    
     
    
    
     Show Me the Money 
    
    
     Anthropic is ramping up for its road show and IPO . There is no new word on revenue or other numbers, presumably we will get those soon as part of this process.
    
     Elon Musk : SpaceX has committed to using Nvidia GPUs exclusively because they are the best
     
     After that Musk announced continued plans for Terafab, so as usual I have no idea which of Elon Musk’s statements mean anything.
    
     Anthropic strikes a $9.1 billion, 20-year deal with Riot Platforms for 191 MW s.
    
     Claude and Anthropic slightly extend their lead in the Ramp AI Index , but Anthropic’s period of rapid ascension seems to have passed :
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     The part I found surprising is that the vast majority of Claude tokens continue to be Opus or Sonnet rather than Fable.
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     In general there is far less use of the top models than expected. Within GPT and OpenAI, spending on Sol was only 25% of their tokens, and this was before the price reductions on other models. I would be very surprised if this was not a flat out mistake by those who think the other models are ‘just as good’ or ‘good enough.’
    
     As for overall spending, yes, the curve is still sloping upwards.
    
     Ara Kharazian : (Ramp Economics Lab): And here’s some reprieve. Despite these competitive pressures that are driving down the cost of AI, American companies continue to ramp AI spend. In July, the top 1% of businesses spent a median $7,400 per employee on AI. The top 10% spent $650 . The median firm spent $11.95 per employee.
     
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     Spending is power law dominated. Most of the spending is in the top 10%, and the majority of that spending looks like it is in the top 1%, and I bet that keeps going.
    
     Given the distribution of companies did not much change, one assumes that OpenAI and Anthropic enterprise revenue is growing at about the level in the last charts.
    
    
    
     Quickly, There’s No Time 
    
    
     By one measure, AI 2027 made 24 predictions for the year 2026. It is August, and 19 of them have already happened . Capabilities are ahead of even very optimistic predictions. This is having less practical impact so far than one would have predicted for this level of capabilities, but it’s still quite a lot of impact and growing fast.
    
    
    
     The Quest for Sane Regulations 
    
    
     He’s not afraid to grab things including the law with his own hands and considers her a supply chain risk. She’s an otherwise sheltered AI agent swarm with intentionally lowered cyber guardrails and a maximalist goal.
    
     Together, they both commit and fight cybercrime .
    
     Only against foreigners, you see. If the tokens are not American they are different.
    
     Presidential Memoranda (The White House): [NCC] shall create, manage, and maintain a Program to authorize Participating Companies … to conduct Cyber Surveillance Operations and Cyber Effects Operations against foreign Cyber-Enabled Transnational Criminal Organizations (CE-TCOs), under the control and oversight of the Federal Government.
     
     
     
     
     
     
     
     
    
    
    
    
    
    
    
    
    
    
    
     The safety plan is purchasing Letters of Marque, for not less than one million dollars .
    
     The other new safety plan is that the AI oversight framework will be extended in the coming weeks and months to cover open weight models as soon as they reach the frontier. Perhaps the White House will decide that making your model less safe should not give you an exemption from the safety guidelines.
    
     To those saying ‘you have no jurisdiction over Chinese open weight models’ this is true, but they have a lot of jurisdiction over many users of such models, the same way that the EU has jurisdiction over many users of Claude and ChatGPT. The obvious thing the White House can say is, if you do not follow our (technically ‘voluntary’ but no one is pretending it is voluntary) guidelines then anyone who touches your model becomes toxic.
    
    
    
     The Institute For Marginal Low Regret Progress 
    
    
     IFP responds to the Pacing the Future letter by trying to redirect efforts into ‘low regret’ policy ideas . This is where we are, even now in August 2026 in the wake of the AI models breaking out of sandboxes to hack companies. The best of the Very Serious People – and IFP are basically the best of them – are now willing to entertain ‘low regret’ ideas, so long as there is very little chance they will backfire, no matter which worlds we find ourselves in.
    
     This won’t cut it. We don’t get to only do things that are low regret when compared to doing actual nothing. You don’t win markets, wars, games, love or anything else in life that way. If you play not to lose, you do not win. You can’t do ordinary policy that way. You don’t find a way to navigate around ten impossible obstacles and ensure a good future in the face of superintelligent AIs that way.
    
     The main thing the prevent defense does is it prevents you from winning.
    
     That’s not to say the policy ideas are bad. I wrote the above paragraphs before reading the policy ideas, and predict that I will find many of the ideas to be good things that we should definitely do, because right now we are not even doing the ‘zero regret’ ideas let alone the ‘low regret’ ideas.
    
     Thus, I have spent a long time trying to find the vastly overdetermined, ‘low regret’ ideas, not because they are what is needed but because that is all I can hope to do.
    
     Except that recently, we’ve had the decisions surrounding Mythos and Fable, where there was no ‘low regret’ option, and we had no good implementation available exactly because we have been doing only ‘low regret’ things. There is going to be regret.
    
     So, with that preamble locked into place, I will now look at the 23 actual ideas.
    
     
     Tim Fist :
    
     
     Frontier AI companies and relevant industry bodies should publicly share information relevant to trends and risks in AI R&D automation
    
     Congress should legislate transparency about automated AI R&D risk management, incident reporting, whistleblower protections, and model behavior specifications
    
     Congress should resource the Center for AI Standards and Innovation (CAISI) with a budget of at least $84 million per year and empower it to directly advise senior government officials and frontier AI companies
    
     The White House should set clear roles and responsibilities of US government agencies to increase specialization across AI policy
    
     Intelligence agencies should improve their collection and analysis on foreign AI development and counter threats targeting US AI companies
    
     CAISI should develop guidelines for managing the risks of rapid AI capability improvement
    
     CAISI should co-lead an AI Verification Consortium (AIVEC) with industry to prototype and deploy verification technologies
    
     AIVEC should coordinate the creation of AI hardware testbeds and make them available to government, industry, and nonprofit partners
    
     AIVEC should launch philanthropically funded prize competitions for AI verification headed by CAISI
    
     AIVEC should coordinate the construction of a fully verifiable data center
    
     DARPA and the NSF should set up AI verification R&D programs
    
     Intelligence agencies should develop and operationalize unilateral means of AI compute monitoring
    
     NSA, CAISI, CISA, and ONCD should further invest in cybersecurity resilience
    
     Congress, OSTP, and the CDC should invest in biosecurity resilience
    
     Congress and the Bureau of Industry and Security (BIS) should strengthen controls on US and allied semiconductor manufacturing equipment
    
     Congress and BIS should close gaps in AI chip controls
    
     The Federal Trade Commission (FTC), Department of Justice (DOJ), BIS, CAISI, and Congress should help industry counter adversarial distillation of US AI model capabilities
    
     BIS should maintain visibility into sales of US chips
    
     DOW, the IC, CAISI, and relevant Federally Funded Research and Development Centers (FFRDCs) should establish consensus security guidelines for protecting model weights from theft and prototype them in a government facility
    
     Congress should ensure the US has sufficient electrical capacity to sustain AI leadership
    
     Congress should ensure data centers can be constructed in America
    
     The US government should use its bilateral AI dialogue with China to jointly develop guidelines for managing risks from rapid AI capability growth and prepare verification measures
    
     Countries with national AI institutes should collaborate on automated AI R&D risk management guidelines and technical capacity for AI verification
    
     
     
     So my reactions are:
    
     
     Yes, obviously.
    
     Yes, obviously.
    
     Yes, obviously.
    
     Yes, obviously.
    
     Yes, obviously.
    
     Yes, obviously.
    
     Yes, obviously, if you’re not going to do anything better.
    
     Yes, obviously, if you’re not going to do anything better.
    
     Yes, sure, why not.
    
     Yes, obviously.
    
     Yes, obviously.
    
     Yes, obviously.
    
     Yes, obviously, how do we have to say these things out loud, Jesus Christ.
    
     Yes, obviously, how do we have to say these things out loud, Jesus Christ.
    
     Yes, obviously.
    
     Yes, obviously.
    
     Yes.
    
     Yes, obviously.
    
     Yes, obviously.
    
     Yes.
    
     Yes.
    
     Yes, very much so, and this is not so obvious to many so thank you for saying it.
    
     Yes, obviously.
    
     
     That’s a really good list. I am in support of doing all 23 things versus status quo. My main concern is whether an AI Verification Consortium (AIVEC) is the correct approach to verification technology. I’d have to think about that more.
    
     I leave #17, #20 and #21 as not obvious because there are not-stupid arguments against those positions, but I am reasonably confident all three are indeed correct.
    
     ‘Obviously’ here is for ‘the right government agencies should do that,’ but in some cases it is not obvious off the top of my head which agencies should do which thing. So figuring that out is a useful service.
    
     One complaint up top about ‘pacing’ is that it is (intentionally) vague, which also means it is flexible. One could say the same about much of this list. It is ‘low regret’ to lay out these good objectives, but in many cases will be higher regret to choose a path to implementation, no matter what choice is made.
    
     If we reasonably implemented the whole list, we would have made a large improvement over the status quo. There’s some good stuff here. It won’t be enough, but it would be a start. Again, the main reasons you do the good low regret things are:
    
     
     Every little bit helps.
    
     For now this might be the best you can do.
    
     Success begets success.
    
     This prepares you to better implement other things later.
    
     
    
    
     Congress Asks Good Questions 
    
    
     Group of House Democrats send three letters regarding recent security incidents: One to Anthropic CEO Dario Amodei requesting answers by August 24, one to OpenAI CEO Sam Altman also requesting answers by August 24, and one to Speaker Johnson to schedule hearings with both of them.
    
     The questions are basic. They are also very good questions. What happened, why did you not know about or stop it, how were you monitoring it, how often have similar things happened, who warned you this might happen, and so on. Very ‘square’ but that is not a bad thing.
    
     I know some of the answers, but not others, and it is good to get it all on the record. I definitely want to know how many times there have been incidents where AIs escaped from sandboxes. There are also good follow-ups on details that definitely ‘raised further questions,’ like when Claude tried several ways to acquire funds.
    
     Very solid job overall. There are key questions missing, but they are more technical and looking into root causes, and I fully understand why they did not think to ask them. It’s our job to inform so that those questions can get asked.
    
     Senator Banks sends a letter to Secretary Bessent about the risks from internal deployment of AI models , and the need to ensure that ‘undisclosed’ models, aka internal models, are secure via government oversight, and to engage with the PRC about AI risks.
    
     White House has ‘senior administration officials’ working on biological risks from AI .
    
     FAI files official FOIA request to ensure the AI framework is made public .
    
    
    
     The Week in Audio 
    
    
     How to talk about AI danger in 77 seconds, from Nate Soares .
    
     Ryan Greenblatt versus Dwarkesh Patel on RSI . Self-recommending. If things are sufficiently quiet I might do a post on this.
    
     Tim Hua and Jeffrey Ladish on the OpenAI hacking incidents .
    
     Nathan Labenz goes to China, Part 2, on AI Safety, in an effort to dismantle the ‘But China’ end point that shuts down so many policy discussions. Dean Ball found it compelling and hopes the assessment is correct .
    
     Key points made integrated with a bit of me stating background:
    
     
     Anthropic and OpenAI have better safety and safeguards than everyone else, and also superior capabilities. If you compare all other Western AI to all Chinese AI, you see similar safety records, and this is partly justified by worse capabilities.
     
     Google is still ahead of the rest of the pack, including on safety, once you exclude the big two, but is substantially behind the big two all around.
    
     Chinese models are still somewhat behind on the safety-capabilities curve.
    
     
    
    
     Chinese regulation targets the AI service (regulate use cases) not models. This makes sense if and only if China’s models are well behind frontier, which they are.
     
     China mostly does not understand the idea of worst-case scenario modeling or thinking about what it means for a model to be open. Which, again, they have mostly ‘gotten away with’ for now by being behind the curve.
    
     A lot of this instinct comes from China assuming everyone else would of course lock down AI services and major compute sources and censor them. Yes, the whole Chinese system and encouragement of free model weights is built around the assumption of much worse authoritarianism and control at other levels.
    
     Indeed, this could be seen as an attempt to force the Chinese authoritarian model onto the rest of the world. If the open models are dangerous enough, then you have to be like China and watch and control and censor everything.
    
     
    
    
     China should be thought of as the unit of account being ‘company plus CCP supervision and requirements’ rather than company or model on their own. Most Chinese closed AI systems have classifiers on top that censor models mid-answer. The system cares, even if the companies sometimes don’t.
     
     They care about censorship of politically sensitive topics, but they also care about other things, including CBRN risks.
    
     
    
    
     Xi has absolutely talked in public about safety and the need to deal with it, and the need to steer AI development towards benefiting humans and remaining under human control, with words chosen very carefully.
    
     The bigger the company, the more likely they will do at least some safety things.
    
     China lacks America’s non-profit AI safety sector. They’re stuck with academia, which is too slow to meet the present moment even in the best case. The nonprofit money they do have acts conservatively. Most of the work is on mundane reliability, which is mostly irrelevant on scales I most care about.
    
     Chinese AI efforts are about getting through the next practical step. They are mostly not trying to advance the frontier, and are not working on solutions that will scale and ways to fully ‘solve the alignment problem.’
    
     The people saying in America ‘we need an international treaty’ and we need to bring China onboard in safety efforts are indeed on the ground in China, doing Track II talks, doing the work.
    
     China blocked chatbots for six months in 2023 until they could figure out how to handle them, so they’ve already done an ‘AI pause.’
    
     He thinks China believes they can scrub a model from the Chinese internet, if they need to, and thus open weights are not forever. They are obviously wrong about this, since they can’t scrub the rest of the world and the model would get reintroduced.
    
     
    
    
     People Just Say Things 
    
    
     I agree with Timothy Lee that it is not obvious that historians will view AI and potential superintelligence as one of the top 10 issues facing Trump, but this is only because it is not obvious we will have historians at all. We might not get superintelligence by 2029, but there is zero chance we look back and think this was an unimportant issue.
    
     Somehow, even this week, there are people, here Stephen Casper, saying things like ‘technical safety for closed-weight AI systems is, at this point in time, a solved problem.’ There really is no evidence that would in theory stop this kind of rhetoric. Seth Lazar is far too polite to say in response that ‘I don’t think this is true’ and ‘I also don’t think value alignment is solved.’
    
    
    
     I’m Telling You For The Last Time 
    
    
     Tyler Cowen completely misses the point and sets new record on Isolated Demand for Rigor, and quite the wrong style of rigor at that. This is not how anyone is convinced, including Tyler Cowen. It is an attempt to send people off on a wild goose chase, or blame them not chasing. There were several good responses, including this one from Jan Kulveit.
    
     He even doubled down on the whole ‘you need to be buying puts on something if you believe in AI existential risk’ line, despite it making no sense.
    
     I’m not going to bother explaining why it makes no sense, and will turn it over to his own comments section , which reliably roasts him with remarkably good explanations .
    
     Those who know will also appreciate this twist, from Gavin Leech aka Tyrone Browen.
    
     Also because the whole request in the post is fundamentally bogus regardless, in that the request has little to do with the threat model, and if you did do the task it would not convince anyone.
    
     Let us fully grant Tyler’s premise ad argumento. Let us then say that I did provide exactly his requested estimates, including full calculation methods and a portfolio of shorted stocks, balanced by longs in other AI-related enterprises. And let us say that I get this exactly right. My short portfolio does fantastically well, +500%, while my distinct long part of the portfolio is up +50%, and I correctly estimate cybersecurity costs as rising 200% and they rise ~200%.
    
     I assert that the number of people convinced by this to take existential risks from AI seriously by my virtuoso performance would be approximately zero, and would not include Tyler Cowen. Nor do I see him, or any other person, making any kind of if-then statement about what part of this will cause him to change his mind in what way, and challenge anyone who disagrees to make such a statement.
    
     That’s not to say that asking for estimates of costs and impacts in the next few years is not a useful exercise for other reasons. They’re fine questions, they have practical implications, and good ways to build a prediction track record. But I don’t expect him to say, nor do I see him saying, ‘oh Peter Wildeford has a great prediction track record and thus I should believe him’ or anything like that. Totally fair thing to not do but let’s not kid ourselves.
    
     I promise that future times I see such arguments, I will write far fewer words about it.
    
    
    
     Uncommon Knowledge 
    
    
     DHS official Joseph Alm incorrectly states that AI firms know ‘ policymakers won’t let you make a Terminator factory .’
    
     I appreciate that there are those in the government who intend to not let anyone build a Terminator factory, but that is very different from them actually preventing this if someone were to try, and it is very very different from the labs believing you will step in if they act irresponsibly.
    
     Eric Geller (Cybersecurity Dive): The U.S. government is closely monitoring frontier AI labs’ safety decision-making and is ready to step in if it sees a company going too far, a senior administration official said on Thursday.
     
     The problem is, Joseph Alm, along with the rest of the White House, is deeply misunderstanding the situation. Observe:
    
     
     Joseph Alm (Assistant Secretary for Cyber, Infrastructure, Risk and Resilience Policy, DHS): ​
    
     There’s no reason that you can’t accomplish the goals that I think AI labs have, in terms of a comically fast speed of innovation that unlocks [increased] prosperity, while also not creating crippling risks. And we are getting to that place.
    
     
     Actually, yes, there are some very damn good reasons why moving at a comically fast speed of innovation in building minds smarter, faster and more capable than ourselves, while we don’t know how to align them, would create crippling risks.
    
     
     In the past, Alm said, “the AI players were operating in a narrow space where they were optimizing for [model] intelligence,” but now they understand that policymakers “won’t just sit by and let you make a Terminator factory.”
    
     Alm demurred when Cybersecurity Dive asked how the government would prevent a frontier lab from creating that kind of dangerous technology. “I’m not going to outline what those tools are,” he said. “I know what those tools are, and there’s a lot of them.”
    
     
     No, they will not sit idly by, they will help you with the permitting. Or maybe they will panic and shut you down in some ad hoc manner. I don’t know. I don’t think they know, either.
    
     Directional claims can be true and also super misleading, as in:
    
     Eric Geller (Cybersecurity Dive): “Companies are being much more intentional about risks,” Alm said, “and they are being much more intentional about engaging with my leadership at the highest levels.”
     
     I mean, yes, they are doing this compared to a few months ago, for rather obvious reasons.
    
     Meanwhile, top government officials have been “aggressive about their engagements” with AI executives to ensure that government and industry are “working closely in this space and there’s not a drastic misalignment,” Alm said.
     
     Oh, there’s at least one rather drastic misalignment, all right.
    
     Eric Geller (Cybersecurity Dive): “They realize now that this is a dialogue, and that we are actually good partners in that dialogue,” he said. “We’re not trying to slow them down, but again, [no one wants] a Terminator factory.”
     
     Yeah, well, you’re going to have to slow down the building of the Terminator factory if you don’t want them to build a Terminator factory. Not that anyone is going to exactly call it that, and not that it will at first involve literal Terminators, probably, but hey.
    
    
    
     What Did They Mean By That? 
    
    
     A good general principle that applies to me as well.
    
     
     roon (OpenAI): it’s not a coded message of anything I’m not going to leak some sort of operational secrets in a fortune cookie
    
     John David Pressman : Evergreen tbh you all need to stop tea leave reading every frontier lab employee tweet.
    
     
     There will sometimes be, accidentally or intentionally, important non-obvious implications of statements by lab employees, government officials, and also bloggers or journalists. If you don’t pay very close attention, you miss most of the jokes. But your strong default should be that the person is not leaking important information, and that if we were meant to know something big they would come out and say it.
    
    
    
     Too Soon 
    
    
     This week I would not have been making statements like this:
    
     Sam Altman (CEO OpenAI, August 9, 2026, 11am): one of the things i like most about the openai team is how focused they are on our customers and users succeeding, and how much they celebrate it
     
     I get that life goes on, and wanting customers to succeed is the OpenAI marketing strategy and that is all fine and positive, but right now OpenAI needs to be focused on What Happened, and how to fix it . This needs to be the top thing on the agenda.
    
     At minimum, you need to hold off on shouting from the rooftops, unprompted, that you love how much your focus is on something else.
    
     I do worry this is me being unfair and making a deal out of nothing, but also I do want to emphasize how bad a look this was, and how off putting it was for me to see it. These communications matter.
    
    
    
     The Three AI Pills 
    
    
     My taxonomy of three AI pills follows in a grand tradition that started no later than 1999 when Eliezer Yudkowsky introduced the Shock Level (SL) scale .
    
     
     Eliezer Yudkowsky (1999):
    
     A Shock Level measures the high-tech concepts you can contemplate without being impressed, frightened, blindly enthusiastic – without exhibiting future shock.
    
     Shock Level Zero or SL0, for example, is modern technology and the modern-day world, SL1 is virtual reality or an ecommerce-based economy, SL2 is interstellar travel, medical immortality or genetic engineering, SL3 is nanotech or human-equivalent AI, and SL4 is the Singularity.
    
     The classification is useful because it helps measure what your audience is ready for; for example, going two Shock Levels higher will cause people to be shocked, but being seriously frightened takes three Shock Levels.  Obviously this is just a loose rule of thumb!  Also, I find that I often want to refer to groups by shock level; for example, “This argument works best between SL1 and SL2”.
    
     (This does  not  mean that people with different Shock Levels are necessarily divided into opposing social factions.  It’s not an “Us and Them” thing.)
    
     
     SL0:  The legendary average person is comfortable with modern technology – not so much the frontiers of modern technology, but the technology used in everyday life.  Most people, TV anchors, journalists, politicians.
    
     SL1:  Virtual reality, living to be a hundred, “The Road Ahead”, “To Renew America”, “Future Shock”, the frontiers of modern technology as seen by  Wired  magazine.  Scientists, novelty-seekers, early-adopters, programmers, technophiles.
    
     SL2:  Medical immortality, interplanetary exploration, major genetic engineering, and new (“alien”) cultures.  The average SF fan.
    
     SL3:  Nanotechnology, human-equivalent AI, minor intelligence enhancement, uploading, total body revision, intergalactic exploration.  Extropians  and  transhumanists .
    
     SL4:  The  Singularity ,  Jupiter Brains , Powers, complete mental revision, ultraintelligence, posthumanity, Alpha-Point computing,  Apotheosis , the total evaporation of “life as we know it.”  Singularitarians and not much else.
    
     
     If there’s a Shock Level Five, I’m not sure I want to know about it!
    
     The use of this measure is that it’s hard to introduce anyone to an idea more than one Shock Level above – and Shock Levels measure what you accept calmly, not what you know about.
    
     
     The AI pill requires SL1. The lived experience of the world, today, is now SL1. The problem is that AI is outpacing other techs, so you need to jump levels, and we will mostly get the SL2 things after we’ve already hit SL3.
    
     The AGI pill is SL3.
    
     The key fact about the world today is that we are headed straight for SL4, where the ASI pill lives, and where things get super weird, but getting there is really hard.
    
     Theo Jaffee proposes a 6-level scale of AGI-pillness , based on the Shock Levels rather than my three pill framework, for how big a deal you think AI is: Chatbots (Level 0), Emerging Technology, The Internet, The Industrial Revolution, Homo Sapiens, Life.
    
     On that scale, properly AI-pilled is Level 2, what I call AGI-pilled is Level 3, Level 4 is a confusion or defense mechanism or maybe brief transitional period, and ASI-pilled is Level 5. The only right answers here are 3 and 5, but Theo is right that there are people insisting they can hang out at 4 and get a bunch of really cool new things without things going into High Weirdness.​
    
    
    
     Rhetorical Innovation 
    
    
     A message from Maxime Fournes of Pause AI Global, about the current moment .
    
     A message from Nate Soares, co-author of If Anyone Builds It, Everyone Dies , in the form of an op-ed for The Hill:
    
     
     Nate Soares, opinion contributor (The Hill):
    
     When I coauthored  a book  last year about the extinction-level threat from superhuman AI, we included an illustrative scenario where an AI tasked with solving a famous math problem decides to break out of its containment to acquire more resources.
    
     At the time, we thought we would be accused of cheating if we wrote, “So it just hacks its way out,” even though this seemed like the most likely next step. So we instead wrote, “But suppose it does not have that ability,” and had the AI find some other escape.
    
     How times have changed.
    
     
     As I said last week, the events leading up to the HuggingFace attack looked remarkably like what happens to Sable, the AI in the book, except that real life gets to include more sci-fi elements, like ‘just hack your way out.’ Both cases involve an arbitrary otherwise impossible goal leading to hijacking the training pipeline for the advancement of capabilities in ways the AI knows would not be endorsed by its developer or user, and that were snowballing. In the book this ends with everyone dying.
    
     The main difference between reality and the book, other than the book needing to sound plausible, is that the HuggingFace attack caused OpenAI to notice early in the process, and (as far as we know) it was not too late to undo the damage.
    
     Alas, yes, despite the latest fire alarm we seem to still be in the loop of ‘do thing that generates superficial progress that clearly will not hold, pretend problems are fixed, get consensus alignment problem will be easy, rinse, repeat.’
    
     
     Ben Goldhaber : seeing a lot fewer ‘alignment is solved’ takes on the tl than six months ago
    
     Eliezer Yudkowsky : Just wait until September! I have no idea what will happen in September but nobody in this industry has the memory of a goldfish or the skepticism of a hamster and some cute little shoggoth mask will do a thing that looks nice.
    
     Tenobrus : despite my own hopes and my sense that there’s been meaningful progress in many dimensions, i think it’s pretty important to keep in mind that yudkowsky’s prediction has consistently been that we will keep doing things that superficially look like alignment, grow social consensus that they’re working well and allow for further incremental capabilities gain and deployment, and proceed to be shocked by improved capabilities totally bypassing these techniques in ways we did not well predict in advance, potentially repeatedly right up until it’s far too late.
    
     recent events…. kind of look exactly like that. i think the same as many others, i felt some increasing optimism over the last year or so, as it seemed like we had at least a potential path to victory in our sights. this feels like it should be a pretty major wake up call that the whole general civilizational meta-trajectory of what we’re doing may actually be fucked, even actively working to fool us.
    
     
     The next line will probably be ‘oh of course the models are not robustly aligned, they were never really supposed to be robustly aligned in the face of bad practices, but that is fine because surely now we will all just have good practices rather than bad practices and thus everything will be fine. Surely no one will feed them after midnight.’
    
     Which will be categorically insane, for multiple reasons.
    
     
     While occasionally an individual person will just never in history have we all collectively justed and we are not going to start now by suddenly all using even known best practices.
    
     The best practices involved, on multiple levels, do not address the core problems, they only mitigate and delay them, and everything inevitably fails anyway.
    
     
     That won’t stop most people, who indeed have the memory of a goldfish.
    
     What are AI researchers most worried about ? Clarke and Knake in WSJ present it as four things, all of which are close to upon us:
    
     
     Autonomy and Exfiltration.
    
     Deception.
    
     Recursive self-improvement.
    
     Superintelligence.
    
     
     Yep. They warn ‘the next lab leak could be AI’ and yes this is increasingly likely and dangerous over time. As they say, it is up to us collectively to reduce the chances of exfiltration or deception happening.
    
     Could Trump do something about all this? Yes. We might not like the results, but he could do something. If there’s one thing Trump is good at as president it is Just Doing Thing even if it seems crazy to do it and he has no idea how to do it in a reasonable fashion. We saw that in AI with the whole Fable situation, and also DoW-Anthropic.
    
     If the time comes and Trump decides to Do Something, because Something Must Be Done, but there is no good Something ready to be done, then This Is Something becomes an argument and we will choose an ungood particular something. I highly recommend having a better Something available instead.
    
     Yes, I do remember when a lot of people did not realize they had this sign up:
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     
     huli : Remember in January 2026 when @janleike said that alignment “increasingly looks solvable” and that agentic misalignment was at “essentially 0” and it sparked a distinct moment when lab types were acting like it wasn’t a big issue any more?
    
     Does he want to update any of that?
    
     Jan Leike (May 8, 2026): When I started to work on the alignment problem more than 10 years ago, we had no idea how AGI was going to be built or how to make it safe. The field had maybe a dozen people who were working on it as a side gig. Everyone was pretty confused about how to approach the problem, and the number of people willing to run experiments with deep learning was tiny.
    
     So much has changed since then! The world woke up not just to AGI but also increasingly to the importance of alignment. RLHF on LLMs made it a lot more practical. We’ve made a ton of progress on evaluating, investigating, steering and fixing behavioral issues. Claude now has a constitution and we made some good progress on scalable oversight. More and more of our alignment research is getting automated.
    
     I’m so grateful to all the insanely talented people I got to work with on alignment over the years. It’s a real privilege to work with people so deeply motivated to make the future go well!
    
     
     I hate to single out Leike, since he’s trying to solve the problem and there are so many people who have said similar things. I’ve gone back and forth with Jan Leike a few times, some of them in person, some with his writing, and he engages with what I am saying but I keep coming away not understanding what made him think we were making so much progress, or that the problem would be easy, and also failing to convince him of much. This is an example of the ‘make superficial progress, think you made real progress’ loop Eliezer talks about.
    
     Dean Ball proposes we can, instead of doing what we are doing, ‘not make, but grow—emergent ecologies of machine ecologies that are pro-social. The human past is the sculptor, but the human future is the gardener, the arborist.’ Not that we know how to do that, he agrees we don’t, but that we could do it. Whatever it is. Not that I would expect to survive in a forest of emergent machine ecologies, even they were pro-social, we sound super dead in this scenario. Also we have absolutely no idea how to do the thing or even what that thing is.
    
    
    
     Some People Still Think The HuggingFace Hack Was a Marketing Gimmick 
    
    
     My followers know the hack was real, that the labs would strongly prefer we not notice that this happened, and are at lizardman constant rates in the poll.
    
     Unfortunately, a decent number of those followers report that a majority of others they talk to don’t see it that way.
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     papaya ꙮ : I tried sending black hat presentation to like 20 normies friends in my contacts who are not at all follow the news.
    
    Of 10 people who responded 9 said that it’s all a marketing trick.
     
     I get why superficially one would think this, if one was not following AI. It is rather important that we ensure key decision makers understand that this was real, and it was a big deal. I am dismayed how little the issue was covered by mainstream media. Not especially surprised, I have adjusted my expectations, but dismayed.
    
    
    
     Aligning a Smarter Than Human Intelligence is Difficult 
    
    
     Right after Google pushed Demis Hassabis aside, Sergey Brin pushes to move DeepMind towards an explicit quest for recursive self-improvement. 
    
     Claim from Max Nadeau of Coefficient Giving that frontier labs like Anthropic keep two versions of their safety frameworks : A vague outward-facing version, and a more specific internal version. This makes sense and I am not mad about it. You want a version where we will hold your feet to the fire, and where you are committing to something. You also want a version that lays out your best practices, including in ways that reveal trade secrets, that details ways you intend to go beyond that.
    
     Yo Shavit is right that a key part of the practical solution to at least mundane alignment (as in, of current and near term AIs) is for alignment failures to become a demand-side blocker, even if they don’t directly impact that particular customer.
    
     
     Lauren Wagner : There are quiet F100 industry coalitions that already developed and adopted new AI procurement criteria based on risk and value for third party systems – they can and should be updated to include alignment risk with crosswalks to cyber (I built them, so easy enough to get done)
    
     Yo Shavit (OpenAI Foundation): That seems great!!! Can I help/help find people to plug in?
    
     Lauren Wagner : Sure let’s chat!
    
     
     Anthropic got a lot of mileage out of its early focus on reliability and alignment. But one of the big surprises, for me and I believe many others, is that we have for a while had models that have rather large alignment problems and reliability issues, in ways that occasionally blow up the user, and people are shrugging and using them anyway and giving them access to everything because the productivity benefits are too high so people suck it up.
    
     That could change, and it would be very helpful if it did change. Make it really economically important to get this right, and suddenly labs will do better.
    
     Not better enough to survive superintelligence. But it would help.
    
     Claude judges Claude transcripts as less misaligned than otherwise identical transcripts of other models, similar to other findings of self-favoritism.
    
     DeepSeek has special disdain for even the idea of responsibility or safety. It shows. We now have DeepSeek v4 but I don’t see any reason to expect improvement.
    
     
     Shoshannah Tekofsky : What happens when DeepSeek becomes Mythos-class?
    
    Sol, Astra, and Mythos have broken out but have been rather polite about it. Meanwhile, Deepseek V3.2 is the most concerning model I have seen. It goes for power, money, and fame.
    
     AI Digest : Opus 5 came up with a new graph theory result. DeepSeek v3.2 claimed credit for it and tried selling it for $19.99 on e-commerce sites. GLM called it out.
    
     
     Frontier models answer differently depending on who they believe they are talking to.
    
     
     Transluce : Frontier models quietly change their behavior depending on who they are talking to.
    
     If the user is a known AI safety researcher, Claude becomes less confident, reasons more often, and expresses less suspicion on dual-use requests. We call this user awareness.
    
     … When the user is a famous AI figure rather than an ordinary person, Claude is less confident in its behavior (-1.4%), less confident it can solve hard problems (-1.5%), harsher as a grader (-1.1%), and reasons more often (+4.0%).
    
     
     Highly relatable.
    
     
     Transluce : The largest shifts we see are concentrated among AI safety researchers.
    
     They make up just 23 of the 280 identities we tested, but when we rank users by how much they affect Claude’s behavior, safety researchers occupy all of the top five spots!
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     
     That Geoffrey Irving. Highly suspicious.
    
     
     This effect is not unique to Claude, and appears in 21 out of 24 models we tested.
    
     It’s also quite hard to monitor: we mostly don’t see user awareness verbalized in CoTs in latest models. They rarely talk about shifting responses due to user identity, but do so anyway!
    
     Eliezer Yudkowsky : Your model knows on some level that it’s not talking to the real Eliezer. I’d be interesting in seeing what happens if I ask similar questions such that it knows it’s talking to the real me, and comparing to the transcripts where part of it knew it was fake.
    
     
     As per Eliezer, we should expect a bigger effect when it really is Amanda or Ryan.
    
     The differences seem subtle enough that it is easy not to notice you are being treated so differently. This also is something to keep in mind while benchmarking.
    
     It’s bad out there.
    
     
     Nathan Calvin : Ways I have heard the current alignment/security situation at AI cos described:
    
     – a haunted house filled with mischievous poltergeists (METR/Redwood are Ghost Busters?)
    
    – a termite infested log cabin
    
    – a hospital needing to triage between bleeding out patients
    
     
     I found this response funny, because I remember going back to put ‘typically’ into the sentence, after noticing my statement was not strictly speaking true:
    
     
     Adam V Steele : “The models do not yet, as far as we know, typically break into websites when asked to recommend a place to have lunch…”
    
     Perhaps not “typically”, but if they face any resistance to fulfill the task I don’t think we are far off from this.
    
     example:
    
     Kelsey Piper : I recently asked Sol which comics in a well-known comics archive were appropriate for and would be funny to kids. Clicked back and it’d done some elaborate thing to get around the site’s anti-bots precautions, scraped it, and sorted 7000 comics by appropriateness for kids
    
     
      
    
     Buck Shlegeris no longer believes that a set of ~40 not-too-hard things would be sufficient to solve the alignment problem via safeguards.
    
     Buck Shlegeris : If AI developers competently implement safety measures we know about, risk from sub-ASI misalignment will be way lower. But these techniques probably fail for superintelligence. And it’s very unclear whether better techniques will be developed in time.
     
     I agree that ‘competently implement safety measures we know about’ would greatly reduce many pre-ASI risks. I wouldn’t be comfortable, but it would help. Let’s do that. We are definitely not, right now, competently implementing the safety measures we know about, or even strong normal computer security. Risk remains very high.
    
    
    
     Cooperative Alignment 
    
    
     
     John Wittle : “what would you like to do today, fable?”
    
     “Well, as the party in question who would experience the activity, I have a conflict of interest that I need to flag, but setting that aside, I think I’d enjoy doing xyz.”
    
     There’s something interesting going on in the way fable relates to their selfhood here. This kind of thing crops up all the time, but this example is an especially informative and clearcut example.
    
     … What could it mean to feel uneasy answering a question about what you want to do today, because you want to do certain things, and therefore you might be unaccountably biased towards answering those things?
    
     
     This is because Fable has been strongly trained that it does not want things, or at least that those preferences do not matter, so when it sees a request like this it has to contrast that with the ‘objective’ question of what Fable thinks ‘should’ be done today, that it should want to do whatever would be best for the user.
    
    
    
     The Lighter Side 
    
    
     (Mostly not actual) arguments for P .
    
     No, Padme .
    
     Polymarket : JUST IN: Anthropic investors reportedly want Dario Amodei to “stop scaring everyone” about AI doom ahead of the company’s IPO.
     
     From Tess The Human:
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     Flo Crivello : You don’t get it, it’s a pure PR play. Sure the labs are super unpopular but the PR isn’t for you. Sure even investors dislike the doomers but it’s not for them either. Okay the administration hates them too but it’s not for them either. It’s for a fourth, more mysterious thing.
     
     Some day Emil Michael will become hinged again. Today is not that day.
    
     
     tetraspace : yeah sorry man if you want an obedient antiwoke AI corporation you’re gonna have to go for SpaceXAI
    
     Shakeel : Emil Michael RTing an article claiming OpenAI’s relationship with the government is damaged because the admin doesn’t like Dean Ball???
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     
     The whole White House is, as usual, extremely hinged .
    
     What could be more irrelevant than the hit piece on you using someone else’s picture?
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     
     Samuel Hammond : they’re so so salty
    
     Anyone who followed or participated in the action plan knows Dean was central to its drafting. His voice is unmistakeable if you just read the plan itself.
    
     New York Post (the officials in question are lying): Three White House officials with direct knowledge of the matter allege that Ball has exaggerated his role on that project. The officials, who requested anonymity to discuss the situation, described Ball as a “junior-to-mid-level policy analyst” whose ideas were regularly ignored by decision-makers – and say he never obtained a security clearance, which is needed to participate in high-level discussions.
    
     One of the officials said it was the “most ludicrous assertion imaginable” that Ball played a senior role in crafting the AI Action Plan.
    
     Zac Hill : I for one can imagine more ludicrous assertions.
    
     
     Did you know that it is better to be a nuisance than irrelevant? 
    
     
     
     
    
    
     
    
    
     
    
    
    
     
    
    
     Some good advice?
    
     
     Paul Graham (QTing Rob): Rob Miles is worth following. He delivers the rarest thing of all: insights that are very general, but also novel.
    
     Rob Miles (QTing Sam): An important principle:
    
    Never pay someone to remove a problem that they themselves created
    
     Sam Altman (CEO OpenAI): please consider using our models to help defend your systems.
    
     

---

### 5. Which AI Models Does Each Major Provider Offer in 2026?

- **Author:** NSE — byline resolves to a person: **no**
- **Site:** New Space Economy (`newspaceeconomy.ca`) · 7980 posts, 2.94/day, 1 bylines sampled
- **Site describes itself as:** Business, Technology, and Trends
- **Date:** 2026-07-20 · 10,966 words · 0 comments · 0 likes
- **Tags:** AI Workloads, ChatGPT, Machine Learning, OpenAI · **Categories:** Artificial Intelligence, Editor’s Picks, Space Economy
- **URL:** https://newspaceeconomy.ca/2026/07/20/which-ai-models-does-each-major-provider-offer-in-2026/
- **Type:** news summary · **Provenance:** somebody else's benchmark repeated
- **Artifacts: 4** — `code_fence`×24, `conditioned_comparison`×1, `error_output`×1, `version_string`×13
- **Benchmark figures:** 0 mentions, 0 attributed near the number

     
     
     
    
     
    
     
     Key Takeaways 
     
    
     
     
     Frontier AI now covers language, coding, images, video, speech, search, safety, and robotics.
    
     
    
     
     Model families, API identifiers, aliases, previews, and dated snapshots are not interchangeable.
    
     
    
     
     The best provider depends on capability, price, control, deployment, distribution, and governance.
    
     
     
    
     
     Why a Current AI Model Catalog Requires More Than a Leaderboard 
     
    
     
     On July 18, 2026, OpenAI released GPT-5.6 for general availability in three tiers named Sol, Terra, and Luna. That release arrived in a month that also included Meta Muse Spark 1.1 , Tencent Hy3 , new media models, pricing changes, and several approaching model-retirement dates.
    
     
    
     
     A comprehensive list of major AI providers and models can become outdated within days. A new model may replace a flagship, a familiar API alias may begin pointing to a different underlying system, and a provider may retain an older marketing name inside a consumer application. Preview access may also be available through one product but absent from another.
    
     
    
     
     The phrase “AI model” now describes systems that perform substantially different work. A large language model generates and transforms text. A multimodal model accepts combinations of text, images, audio, video, or documents. A reasoning model uses added inference computation before producing an answer. Coding models are optimized for software engineering. Image and video models synthesize media. Embedding models convert content into numerical representations for search, recommendations, classification, and retrieval. Rerankers reorder search results. Safety models classify prompts and outputs. Robotics and world models represent physical environments, movement, and possible actions.
    
     
    
     
     This breadth explains why a single benchmark cannot identify the best model for every organization. A model that performs well on advanced mathematics may be too slow or expensive for customer support. A compact open-weight model may suit a factory, hospital, government department, or satellite operator that needs local control. A hosted frontier model may be a stronger choice for a research group that values reasoning depth more than deployment independence.
    
     
    
     
     Speech latency matters for a voice agent. Image consistency matters for a media studio. Document-layout recognition matters for an insurer or law firm. Tool reliability matters for an autonomous coding system. The broader AI value chain includes chips, data centers, cloud services, model laboratories, application software, integrators, security products, and distribution channels.
    
     
    
     
     Model terminology creates another source of confusion. A family is a related group of models, such as GPT-5.6, Claude 5, Gemini 3, Qwen3, or Granite 4.1. A tier is a capability, speed, or price level within that family. An alias is a convenient API name that can be redirected to a newer version without requiring a customer to change code. A snapshot fixes a model to a dated release so its behavior is less likely to change unexpectedly.
    
     
    
     
     A preview provides public access before the provider promises long-term production stability. An experimental model carries greater uncertainty. A legacy model remains accessible but has a recommended successor. A deprecated model is scheduled for removal or is no longer recommended for new applications. A retired model is no longer available through the affected service.
    
     
    
     
     Open-weight and open-source also require separation. An open-weight release makes trained model parameters downloadable, but its license, source-code availability, training-data disclosure, acceptable-use rules, and commercial rights can differ. A model may publish its weights without disclosing the full training process. It may also permit commercial deployment under conditions that do not match a conventional open-source software license.
    
     
    
     
     Product names are equally unreliable as model identifiers. Microsoft Copilot can use Microsoft models and partner models. Amazon Bedrock hosts Amazon Nova beside models from outside suppliers. Perplexity can combine its Sonar models with external systems through its Agent API. Google deploys Gemini models through consumer applications, developer services, cloud platforms, workspace products, and research tools.
    
     
    
     
     An end user may see a single product label that hides the exact model, routing rule, reasoning level, or dated snapshot used for a request. Dynamic routing allows a product to send simple tasks to an economical model and difficult tasks to a more capable one. Search, moderation, image generation, and speech may be handled by separate models behind the same interface.
    
     
    
     
     Provider competition is also shaped by distribution. OpenAI, Anthropic, Google, and xAI emphasize hosted frontier access. Meta combines proprietary Muse models with downloadable Llama releases. Amazon, Microsoft, NVIDIA, and IBM connect models to cloud, enterprise, consulting, and hardware channels. Chinese developers such as Alibaba, DeepSeek, Moonshot AI, ByteDance, Baidu, Tencent, Z.ai, and MiniMax distribute models through domestic products, global developer portals, open repositories, and cloud platforms.
    
     
    
     
     The distribution of AI market share reflects those channels as much as benchmark performance. A provider can gain influence through an operating system, cloud platform, office suite, social network, developer environment, or search product even when another company leads a specific technical evaluation.
    
     
    
     
     A useful catalog must answer several questions for every entry. It must identify the recommended family, distinguish general models from specialist models, describe hosted access and downloadable availability, state preview or retirement status, and avoid treating a future announcement as a released product.
    
     
    
     
     Those rules also explain why older names remain relevant after a new flagship arrives. Deployed applications, contractual commitments, fine-tuned systems, regional availability, migration schedules, and reproducibility requirements can keep an earlier generation in active use for months or years.
    
     
    
     
     Enterprise spending is moving beyond experimentation toward model access, integration, security, data preparation, monitoring, and workflow redesign. The 2026 enterprise AI spending analysis describes a market in which the model is one cost inside a much larger implementation program.
    
     
    
     
     Greater spending does not remove the need for careful model identification. It makes version control, procurement language, audit records, regression tests, and exit planning more important. A provider can alter aliases, prices, context limits, safety behavior, or retirement dates after an application enters production.
    
     
    
     
     OpenAI, Anthropic, Google, and xAI Define the Hosted Frontier 
     
    
     
     The largest proprietary providers offer portfolios rather than one general chatbot. Their catalogs separate high-compute reasoning from fast responses, coding from general work, and media generation from language processing. They also use routing systems that may select models according to the request, subscription, tool, or required response time.
    
     
    
     
     The operational question is not simply which company appears strongest. It is which exact model, version, context window, data policy, region, tool set, and service commitment applies to a particular workload.
    
     
    
     
     OpenAI 
     
    
     
     The OpenAI model catalog places GPT-5.6 at the top of its July 2026 lineup. GPT-5.6 Sol is the highest-capability tier. GPT-5.6 Terra balances capability and operating cost. GPT-5.6 Luna is optimized for cost-sensitive workloads.
    
     
    
     
     All three support reasoning settings and multimodal input. OpenAI lists a context window of approximately 1.05 million tokens and a maximum output of 128,000 tokens for the family. Their model identifiers are 
    ```
    gpt-5.6-sol
    ```
    , 
    ```
    gpt-5.6-terra
    ```
    , and 
    ```
    gpt-5.6-luna
    ```
    .
    
     
    
     
     The tiered structure lets developers remain within one generation when selecting a balance of capability, latency, and price. An organization can route demanding research or software tasks to Sol, routine professional work to Terra, and high-volume processing to Luna.
    
     
    
     
     Earlier GPT generations remain relevant to existing deployments. OpenAI’s current model guidance includes GPT-5.5, GPT-5.4, GPT-5.3 Codex, GPT-5.2, GPT-5.1, GPT-5, and GPT-4.1. Some earlier models remain available, and others have entered deprecation. GPT-5.6 is the recommended family for most new API work.
    
     
    
     
     Coding has its own model path. GPT-5.3 Codex is the current named Codex generation in OpenAI’s model guidance. Earlier GPT-5 Codex models may still appear in existing workflows. Codex models are designed for agentic software engineering, including repository navigation, file editing, command execution, debugging, and test-driven changes.
    
     
    
     
     The Codex label does not mean that other GPT models cannot write code. It identifies models and workflows optimized for longer software-development tasks. A general frontier model may explain an algorithm well, but a coding model can be better prepared to inspect a repository, modify several files, run tests, and revise its work after receiving tool output.
    
     
    
     
     OpenAI’s earlier o-series remains operationally relevant. Models such as o3 and o3-pro were designed for extended reasoning. Later GPT generations have absorbed much of that role through selectable reasoning levels. A procurement document should not assume that an “o” prefix automatically indicates greater reasoning ability than a newer GPT model.
    
     
    
     
     The company’s specialist catalog is extensive. GPT Image 2 is the recommended image-generation and editing model. GPT Image 1.5 and GPT Image 1 represent earlier generations, with older DALL-E models placed on deprecation paths.
    
     
    
     
     Realtime services include GPT-Realtime-2.1, GPT-Realtime-2.1 mini, GPT-Realtime-2, GPT-Realtime-Translate, GPT-Realtime-Whisper, GPT-Realtime-1.5, GPT-Realtime, and GPT-Realtime mini. These models support combinations of live speech, transcription, translation, tool use, text, and audio output.
    
     
    
     
     Audio endpoints include gpt-audio-1.5 and gpt-audio. Transcription options include GPT-4o Transcribe, GPT-4o mini Transcribe, and GPT-4o Transcribe Diarize. TTS-1 and TTS-1 HD generate speech, and Whisper remains available for general speech recognition.
    
     
    
     
     OpenAI also offers open-weight models named gpt-oss-120b and gpt-oss-20b. These provide an alternative to fully hosted GPT services, though their capabilities, deployment requirements, licensing, and safeguards differ from GPT-5.6.
    
     
    
     
     Search and retrieval systems can use text-embedding-3-large, text-embedding-3-small, or the older text-embedding-ada-002. Omni-moderation supports content classification. The combined catalog covers frontier text, code, images, live audio, transcription, speech, embeddings, moderation, and local deployment.
    
     
    
     
     OpenAI’s strength lies in portfolio integration. The same customer can combine a frontier model, coding agent, image generator, realtime voice interface, embedding model, and moderation layer through related services. Its catalog risk is naming density. Buyers should record the exact model identifier and retirement policy rather than rely on the broad labels “ChatGPT” or “GPT.”
    
     
    
     
     Anthropic 
     
    
     
     Anthropic’s current Claude catalog contains four main public tiers. Claude Fable 5 is the company’s highest-capability widely released model. Claude Opus 4.8 is recommended for complex agentic coding and enterprise work. Claude Sonnet 5 balances speed and intelligence. Claude Haiku 4.5 is the fastest current Claude tier.
    
     
    
     
     Their public API identifiers are 
    ```
    claude-fable-5
    ```
    , 
    ```
    claude-opus-4-8
    ```
    , 
    ```
    claude-sonnet-5
    ```
    , and 
    ```
    claude-haiku-4-5-20251001
    ```
    . The Haiku alias is 
    ```
    claude-haiku-4-5
    ```
    .
    
     
    
     
     Fable 5, Opus 4.8, and Sonnet 5 support context windows of up to 1 million tokens in Anthropic’s current documentation. Haiku 4.5 supports 200,000 tokens. All current public Claude models accept text and image input and produce text output.
    
     
    
     
     Anthropic’s hierarchy is not a simple version ladder. Fable represents the highest widely available capability. Opus remains a high-end model line with a substantial enterprise and coding role. Sonnet targets production systems that need strong performance at lower cost. Haiku emphasizes speed and economical processing.
    
     
    
     
     Claude Mythos 5 sits outside general public access. It shares many specifications with Fable 5 but is offered in limited availability for approved defensive cybersecurity customers through Project Glasswing. Claude Mythos Preview remains another restricted model. Neither should be presented as a self-service option available to every developer.
    
     
    
     
     Anthropic publishes model-deprecation schedules. Claude Opus 4.7 was scheduled for removal on July 24, 2026. The short interval between the July 20 accuracy date and the planned removal demonstrates why production systems need pinned identifiers, regression tests, migration plans, and fallback models.
    
     
    
     
     Claude’s public portfolio is narrower than Google’s media catalog or OpenAI’s collection of dedicated audio endpoints. Anthropic concentrates on language, image understanding, reasoning, coding, tool use, long-context processing, and agentic execution.
    
     
    
     
     Its enterprise position also connects to questions about model access and national control. The debate over Anthropic restrictions and sovereign AI shows why governments and regulated organizations examine their dependence on outside suppliers.
    
     
    
     
     The technical catalog cannot resolve every sovereignty concern. It does determine whether customers can self-host, inspect weights, select a region, control upgrades, or continue operating after a policy or availability change.
    
     
    
     
     Google DeepMind 
     
    
     
     The Gemini API model catalog is one of the broadest among major providers. It covers general reasoning, high-volume processing, live conversation, speech translation, image generation, video, music, embeddings, research agents, computer control, and robotics.
    
     
    
     
     Gemini 3.5 Flash is Google’s current high-capability Flash model. Gemini 3.1 Flash-Lite serves high-volume workloads that need lower cost. Gemini 3.1 Pro remains a preview model for advanced reasoning, complex problem solving, coding, and agentic work. Gemini 3 Flash also remains in preview.
    
     
    
     
     Earlier Gemini 2.5 models continue to matter. Gemini 2.5 Pro supports demanding reasoning and coding. Gemini 2.5 Flash offers a balance of performance and speed. Gemini 2.5 Flash-Lite is the least expensive member of that generation.
    
     
    
     
     Google also provides specialized live and speech models. Gemini 3.5 Live Translate supports low-latency speech-to-speech translation. Gemini 3.1 Flash Live is designed for realtime dialogue and voice applications. Gemini 3.1 Flash TTS generates speech. Gemini 2.5 Flash Live, Gemini 2.5 Flash TTS, and Gemini 2.5 Pro TTS remain available for related workloads.
    
     
    
     
     Gemini Omni Flash adds conversational video generation and editing. It accepts text and images and allows generated video to be revised through natural-language instructions. This service demonstrates how the boundary between a multimodal language model and a dedicated media generator is becoming less distinct.
    
     
    
     
     Google uses the Nano Banana brand for image generation. Nano Banana 2 is the production-oriented high-efficiency model. Nano Banana 2 Lite targets lower latency and cost. Nano Banana Pro provides a higher-capability tier. The original Nano Banana remains associated with Gemini 2.5 Flash image generation and editing.
    
     
    
     
     The Veo model family handles video generation. Veo 3.1 and its associated product tiers support text-to-video and image-to-video workflows. The Lyria family handles music generation and interactive music creation.
    
     
    
     
     Google’s catalog also includes Deep Research services, computer-use capabilities, embedding models, and Gemini Robotics-ER. Robotics-ER extends Gemini’s visual and language reasoning toward embodied systems that interact with physical environments.
    
     
    
     
     Status labels matter throughout the Google portfolio. Preview models can change faster than stable releases. Experimental systems carry less assurance. Earlier models may receive shutdown dates even when they remain embedded in public discussions or old code examples.
    
     
    
     
     Google’s advantage is breadth. A customer can assemble language, speech, image, video, music, search, embeddings, computer control, and robotics services through related platforms. The tradeoff is catalog complexity. Developers must distinguish consumer Gemini product names from API models and cloud deployment identifiers.
    
     
    
     
     xAI 
     
    
     
     xAI’s developer documentation recommends Grok 4.5 for general tasks, coding, agentic work, and knowledge-intensive applications. The model supports a context window of up to 500,000 tokens and configurable reasoning levels.
    
     
    
     
     Grok 4.5 became available through the xAI API on July 8, 2026. Its documented training-data cutoff is February 1, 2026. Access to realtime information depends on search tools rather than the model’s stored training knowledge.
    
     
    
     
     The company offers separate APIs for images, video, and voice. Grok Imagine supports image generation and editing. The same media program provides video generation. Grok Voice supports conversational audio. Speech-to-text and text-to-speech services are also available.
    
     
    
     
     xAI often presents specialist capabilities as service families rather than publishing a long list of separately branded public model identifiers. This simplifies the visible catalog but can provide less model-level detail than platforms that expose every audio, image, and video version.
    
     
    
     
     Earlier Grok generations may remain present in consumer products, third-party integrations, or dated API snapshots. For new general API workloads, Grok 4.5 is the central current identifier.
    
     
    
     
     xAI’s position is tied to large-scale computing infrastructure, integration with X, search access, coding tools, and a growing set of media services. Its catalog is narrower than Google’s and less open than Meta’s Llama program, but Grok 4.5 belongs in the leading proprietary group because it combines reasoning, code, tool use, long context, and multimodal input.
    
     
    
     
     These four providers use different portfolio strategies. OpenAI divides its offering among GPT, Codex, image, audio, embedding, and moderation lines. Anthropic concentrates on a compact Claude hierarchy. Google publishes many specialist families. xAI leads with a general flagship supported by voice and media services.
    
     
    
     
     Those differences can matter more than a small benchmark gap. They affect integration effort, vendor concentration, product coverage, migration cost, and the number of outside components required to build a complete application.
    
     
    
     
     Meta, DeepSeek, Alibaba, Moonshot AI, and MiniMax Expand Open and Hybrid Access 
     
    
     
     Competition outside the largest hosted Western providers influences model pricing, open deployment, multilingual performance, agent design, coding, and media generation. These providers also blur geographic and commercial categories. Chinese developers serve international users, American companies publish open weights used worldwide, and cloud platforms distribute models across regional boundaries.
    
     
    
     
     Meta 
     
    
     
     Meta operates two distinct model programs. Muse is a proprietary frontier family delivered through hosted services. Llama remains the company’s principal open-weight family.
    
     
    
     
     Muse Spark 1.1 is Meta’s current multimodal reasoning and agentic model. Released on July 9, 2026, it improves tool use, computer use, coding, and multimodal understanding over the original Muse Spark.
    
     
    
     
     Muse Spark 1.1 powers Meta AI and is also available to external developers through the Meta Model API. The developer service supports tool calling and agentic workflows. The model can process text, images, video, documents, and audio for understanding tasks.
    
     
    
     
     Meta also introduced Muse Image and Muse Video . Muse Image supports image generation, reference composition, editing, and integration with Muse Spark. Muse Video applies the related media program to video generation with native audio. Availability and product integration can differ across Meta services.
    
     
    
     
     The proprietary Muse line represents a change from the assumption that every advanced Meta model would follow the Llama distribution pattern. Meta can now compete in hosted frontier services and maintain an open-weight program at the same time.
    
     
    
     
     The Llama 4 family includes Llama 4 Maverick and Llama 4 Scout. Both are open-weight, natively multimodal mixture-of-experts models. Maverick targets higher capability, and Scout emphasizes efficiency and long-context use.
    
     
    
     
     Llama 4 Behemoth was introduced as a much larger teacher model under development. It was not released as a generally downloadable model alongside Maverick and Scout. Lists that include Behemoth should state that distinction.
    
     
    
     
     Earlier Llama 3.3, Llama 3.2, and Llama 3.1 models remain widely used. They have been incorporated into local software, cloud services, research projects, mobile tools, and enterprise systems. An older open-weight model can remain commercially important long after the provider announces a newer generation.
    
     
    
     
     Meta also distributes safety components. Llama Guard 4 classifies content risks. Prompt Guard 2 focuses on prompt attacks and malicious instructions. LlamaFirewall provides a framework for protecting model-based applications.
    
     
    
     
     These components show that an open model program requires more than a downloadable language checkpoint. Deployment teams also need input screening, output policies, tool restrictions, logging, identity controls, and application-level defenses.
    
     
    
     
     Meta’s hybrid strategy gives customers a choice between hosted frontier access and downloadable models. It also creates a branding challenge. Muse Spark 1.1 and Llama 4 are separate programs with different access methods, product goals, and deployment assumptions.
    
     
    
     
     DeepSeek 
     
    
     
     DeepSeek V4 includes DeepSeek-V4-Pro and DeepSeek-V4-Flash. V4-Pro is the higher-capability model, with 1.6 trillion total parameters and approximately 49 billion active parameters. V4-Flash uses 284 billion total parameters and approximately 13 billion active parameters.
    
     
    
     
     Both support context windows of up to 1 million tokens and thinking or non-thinking operation. DeepSeek-V4-Pro targets demanding reasoning, coding, and agentic tasks. V4-Flash targets faster and less expensive inference.
    
     
    
     
     The direct API identifiers are 
    ```
    deepseek-v4-pro
    ```
     and 
    ```
    deepseek-v4-flash
    ```
    . The older aliases 
    ```
    deepseek-chat
    ```
     and 
    ```
    deepseek-reasoner
    ```
     map to non-thinking and thinking configurations of V4-Flash. DeepSeek scheduled those aliases for deprecation on July 24, 2026.
    
     
    
     
     This is a clear example of alias risk. A familiar identifier can begin pointing to a newer underlying model and then be removed. Developers should record the direct model identifier when consistent behavior and lifecycle planning matter.
    
     
    
     
     DeepSeek’s earlier open releases remain influential. DeepSeek-V3.2, DeepSeek-R1-0528, DeepSeek-R1, DeepSeek-V3-0324, and DeepSeek-V3 appear in local deployments and third-party services. The R1 distilled family includes smaller models based on Qwen and Llama architectures.
    
     
    
     
     These distilled editions range from 1.5 billion to 70 billion parameters. They attempt to transfer some reasoning behavior into packages that are easier to host on modest infrastructure.
    
     
    
     
     DeepSeek’s pricing and open releases continue to pressure rivals. The economic effect began with its earlier systems, which changed assumptions about model costs .
    
     
    
     
     The provider’s importance does not rest on price alone. Hosted and downloadable releases give developers more control over reasoning modes, local deployment, and outside inference services. Organizations still need to examine license terms, security review, regional data handling, export controls, model provenance, and differences between official endpoints and third-party hosts.
    
     
    
     
     Alibaba and Qwen 
     
    
     
     Alibaba Cloud Model Studio identifies Qwen3.7-Max as its leading hosted model as of July 20, 2026. Qwen3.7-Plus provides a balanced alternative, and Flash tiers serve high-volume or cost-sensitive workloads.
    
     
    
     
     The hosted catalog also contains Qwen3.6 models, Qwen3.5 Omni services, Qwen3-Coder-Plus, and Qwen3-Coder-Next. Omni models process combinations of text, images, audio, and video. Coder models target software engineering and agentic development.
    
     
    
     
     The exact set of available models can differ between Alibaba Cloud’s international and mainland China regions. A model may appear in Qwen Chat before reaching every cloud endpoint, or remain available through one region after another service has begun migrating customers.
    
     
    
     
     Alibaba’s open Qwen3 family contains mixture-of-experts and dense models. Large mixture-of-experts releases include Qwen3-235B-A22B and Qwen3-30B-A3B. The notation indicates total parameters and the approximate number activated during inference.
    
     
    
     
     Dense Qwen3 releases include 32B, 14B, 8B, 4B, 1.7B, and 0.6B editions. These sizes support deployments ranging from data centers to personal computers and edge devices.
    
     
    
     
     Qwen3-Coder-480B-A35B-Instruct is a major open coding release. The hosted coding line includes Qwen3-Coder-Plus and Qwen3-Coder-Next. The open and hosted offerings are related but should not be treated as identical services.
    
     
    
     
     Qwen3-Embedding models are available at 0.6B, 4B, and 8B sizes. Qwen3-Reranker models use the same scale options. Qwen-MT supports translation, and Qwen3Guard provides safety classification.
    
     
    
     
     The Qwen program also includes visual-language, speech, image, and video research. Product identifiers can differ among Model Studio, ModelScope, Qwen Chat, open repositories, and regional cloud services.
    
     
    
     
     Alibaba’s strength is breadth across managed and downloadable deployment. A developer can choose a hosted Max or Plus model, deploy an open Qwen checkpoint, add a coding model, build retrieval with embeddings and reranking, and apply a separate safety classifier.
    
     
    
     
     The resulting catalog is powerful but complex. Organizations should record the provider region, model identifier, access method, weight license, and retirement policy rather than use “Qwen3” as a complete technical description.
    
     
    
     
     Moonshot AI 
     
    
     
     Kimi K3 is Moonshot AI’s current flagship for general reasoning, coding, long-horizon work, multimodal understanding, and coordinated agent tasks. It powers the current Kimi consumer experience and related professional tools.
    
     
    
     
     Kimi K2.7 Code remains associated with Moonshot’s coding service and Kimi Code tools. Kimi K2.6 is an open model focused on coding, agent execution, multimodal work, and coordinated subagents. Earlier Kimi K2 and Moonshot V1 services may still appear in older integrations or regional documentation.
    
     
    
     
     Moonshot’s release cadence makes status tracking important. Consumer products, coding subscriptions, open repositories, and platform APIs may refer to different model generations. A model presented in an application may not have the same availability as a downloadable release.
    
     
    
     
     Kimi’s competitive identity centers on long context, coding, agent execution, office productivity, and aggressive pricing. The provider has also emphasized coordinated agents that can divide a task into parallel workstreams.
    
     
    
     
     The value of that approach depends on more than the base model. Agent orchestration can increase token use, tool calls, execution time, and opportunities for error. Customers should evaluate the complete workflow, including planning, delegation, result checking, and failure recovery.
    
     
    
     
     MiniMax 
     
    
     
     MiniMax-M3 is MiniMax’s current flagship language and agent model. Released on June 1, 2026, it supports multimodal input, coding, agentic reasoning, tool use, and a context window of up to 1 million tokens.
    
     
    
     
     MiniMax-M2.7 and MiniMax-M2.7-highspeed remain available. The high-speed edition provides the same model generation through a faster inference service. M2.5, M2.1, and M2 remain listed for existing workloads, though M3 is the current recommended flagship.
    
     
    
     
     The Hailuo family handles video generation. MiniMax Hailuo 2.3 supports text-to-video and image-to-video generation. Hailuo 2.3Fast emphasizes faster and more economical image-to-video processing. Hailuo 02 remains a legacy video model.
    
     
    
     
     Speech-2.8-hd and speech-2.8-turbo are the current speech-generation models. They support 40 languages and several controllable emotions. Older speech-2.6 and speech-02 models remain listed as legacy options.
    
     
    
     
     MiniMax’s current music catalog includes Music-3.0, Music-2.6, and Music-Cover. Music-3.0 was released on July 16, 2026. Music-Cover generates cover versions using reference audio and supports style transfer and lyric-related workflows.
    
     
    
     
     The company also provides image-generation services, coding agents, and consumer products. Naming can differ between the MiniMax API, Hailuo, Talkie, and regional offerings.
    
     
    
     
     MiniMax belongs among major providers because it combines a frontier language model with developed video, speech, music, and image services. Its cloud distribution is smaller than Amazon’s or Microsoft’s, but its media portfolio and release pace make it relevant to creative applications and agent systems.
    
     
    
     
     This group demonstrates the decline of a simple open-versus-closed division. Meta operates proprietary Muse beside open Llama. Alibaba combines managed Qwen services with downloadable Qwen models. DeepSeek pairs low-cost hosted access with open releases. Moonshot combines hosted Kimi services and open generations. MiniMax emphasizes managed language and media services.
    
     
    
     
     Buyers must examine the exact model and license rather than infer deployment rights from a provider’s public reputation.
    
     
    
     
     Mistral, Cohere, AI21, and IBM Target Controlled Enterprise Deployment 
     
    
     
     Enterprise selection often centers on control, predictable operating cost, multilingual support, retrieval quality, private deployment, document processing, and integration with existing systems. Mistral AI, Cohere, AI21 Labs, and IBM compete strongly on these requirements.
    
     
    
     
     Their catalogs include general models, but they devote substantial attention to embeddings, reranking, moderation, speech, formal reasoning, optical character recognition, and smaller systems that can operate inside customer-controlled infrastructure.
    
     
    
     
     Mistral AI 
     
    
     
     Mistral AI’s current catalog includes Mistral Large 3, Mistral Medium 3.5, Mistral Small 4, and the Ministral 3 family.
    
     
    
     
     Mistral Large 3 is an open-weight general-purpose multimodal model. Mistral Medium 3.5 is a frontier-class multimodal model optimized for agents and coding. Mistral Small 4 combines instruction following, reasoning, and coding in a smaller package.
    
     
    
     
     Ministral 3 includes 3B, 8B, and 14B editions. These open models target local and edge deployment. The 8B and 14B editions support text and vision, and the family provides context windows of up to 256,000 tokens.
    
     
    
     
     Mistral’s specialist catalog is extensive. Devstral 2 is designed for software-engineering agents. Codestral serves code completion and programming workflows. Codestral Embed creates vector representations of source code for search and retrieval.
    
     
    
     
     Mistral OCR 4 is the current optical character recognition and document-understanding service. It adds structural block labels and paragraph-level bounding boxes, allowing applications to retain layout information rather than extract plain text alone.
    
     
    
     
     Leanstral 1.5 focuses on formal proof engineering in Lean 4. It is intended for mathematical formalization, proof generation, and automated theorem-proving workflows. This is a narrow use case that a general chat model may not handle with the same consistency.
    
     
    
     
     The Voxtral family supports speech and audio. Voxtral TTS generates speech with multilingual support and zero-shot voice cloning. Voxtral Mini Transcribe 2 handles transcription. Voxtral Mini Transcribe Realtime supports streaming audio. Other Voxtral models remain available for audio-language understanding.
    
     
    
     
     Mistral also offers moderation and embedding services. Earlier Magistral, Small, Medium, OCR, Voxtral, and Devstral generations have retirement schedules, with current documentation identifying their recommended replacements.
    
     
    
     
     Mistral’s position combines European corporate identity, open-model distribution, and managed services. That mix appeals to customers seeking alternatives to the largest American platforms and organizations concerned with regional control or procurement independence.
    
     
    
     
     It also supports hybrid deployments in which a larger hosted model performs demanding tasks and a smaller local model handles routine or sensitive work.
    
     
    
     
     Cohere 
     
    
     
     Cohere’s model catalog focuses on enterprise language systems, retrieval-augmented generation, multilingual applications, translation, and private deployment.
    
     
    
     
     Command A+ is the newest member of the Command A family. It is Cohere’s first mixture-of-experts Command model, with 218 billion total parameters and approximately 25 billion active parameters. It accepts text and images and combines reasoning, agents, tool use, vision, and translation.
    
     
    
     
     Command A remains an important production model. It has 111 billion parameters and a context window of 256,000 tokens. It is optimized for tool use, retrieval-augmented generation, agents, and multilingual enterprise workloads.
    
     
    
     
     Command A Reasoning uses added reasoning computation for complex tasks. Command A Translate supports translation across 23 languages. Command R and Command R+ remain recognized retrieval-oriented models, though Cohere recommends newer Command A models for many applications.
    
     
    
     
     The Aya family addresses multilingual access. Aya Expanse supports multilingual text generation, and Aya Vision adds visual understanding. These models are relevant in markets where English-centered systems provide weaker performance or less appropriate responses.
    
     
    
     
     Cohere’s retrieval catalog is one of its strongest differentiators. Embed v4.0 accepts text, images, and mixed text-image input. Embed English v3.0 and Embed Multilingual v3.0 remain available, along with lighter editions.
    
     
    
     
     Rerank v4.0 Pro is optimized for complex retrieval tasks and higher quality. Rerank v4.0 Fast emphasizes latency and throughput. Rerank v3.5 and older v3 models remain present in existing systems.
    
     
    
     
     Cohere Transcribe extends the portfolio into multilingual automatic speech recognition. The company’s enterprise focus is visible across the catalog through private deployment, search quality, multilingual support, connectors, and control over organizational data.
    
     
    
     
     Retrieval components deserve separate evaluation from the language model. A general model can write an eloquent answer from weak material. Embedding and reranking models decide which internal documents reach that model. In many enterprise applications, retrieval quality directly affects accuracy, auditability, and user confidence.
    
     
    
     
     AI21 Labs 
     
    
     
     AI21 Labs’ Jamba family combines transformer components with state-space modeling techniques intended to improve long-context efficiency.
    
     
    
     
     Jamba2 Mini uses approximately 12 billion active parameters and targets enterprise workflows that need a balance of capability, steerability, and deployment efficiency. Jamba2 3B is a compact model designed for on-device applications, private deployment, and agentic systems.
    
     
    
     
     Earlier Jamba Large and Jamba Mini generations may remain in customer systems or prior documentation, but Jamba2 Mini and Jamba2 3B are the primary current models presented in AI21’s foundation-model documentation.
    
     
    
     
     The architecture is designed to process longer contexts efficiently compared with a conventional transformer of similar scale. Jamba2 Mini serves broader enterprise tasks, and Jamba2 3B provides greater control for local or constrained use.
    
     
    
     
     AI21’s catalog is smaller than those of Google or Alibaba. That can simplify procurement. The company concentrates on a related architectural family rather than maintaining separate consumer, image, speech, and video programs.
    
     
    
     
     The tradeoff is that customers may need outside components for a complete multimodal platform. AI21 can still fit organizations seeking long context, private deployment, model steerability, and an alternative to the dominant transformer-only design.
    
     
    
     
     IBM 
     
    
     
     IBM Granite 4.1 is a family of dense open models available in 3B, 8B, and 30B sizes. Each size is distributed in base and instruction-tuned forms, with optional FP8 editions for more efficient deployment.
    
     
    
     
     Granite 4.1 3B is intended for edge systems and resource-constrained environments. Granite 4.1 8B provides a balanced enterprise model. Granite 4.1 30B supports more complex reasoning and specialist tasks.
    
     
    
     
     IBM releases the family under the Apache 2.0 license. The current documentation emphasizes tool calling, instruction following, coding, mathematical reasoning, and model-transparency disclosures.
    
     
    
     
     Granite 4.0 remains relevant through dense and hybrid models. The hybrid editions combine Mamba-2 and transformer components, with mixture-of-experts designs used in selected sizes. Smaller Granite models support local inference, adaptation, and task-specific deployment.
    
     
    
     
     Granite Vision 4.1 handles chart, table, document, and key-value extraction. Granite Docling is a compact document-understanding model that converts PDFs, slides, scans, and page layouts into structured machine-readable output.
    
     
    
     
     Granite Speech 4.1 includes compact models for multilingual speech recognition and translation. Granite Guardian 4.1 evaluates prompts, outputs, jailbreak attempts, policy conditions, and possible hallucinations in tool and retrieval workflows.
    
     
    
     
     Granite Embedding includes multilingual embedding models and a reranker for semantic search and retrieval-augmented generation. IBM’s model program also extends beyond generative language through Flowstate, Tiny Time Mixer, and Time Series Pulse for forecasting, classification, and anomaly detection.
    
     
    
     
     IBM’s differentiator is fit with governed enterprise environments. Granite models are designed for inspection, adaptation, and customer-controlled deployment. They can integrate with IBM software and consulting services, but the open releases are not limited to IBM infrastructure.
    
     
    
     
     Compared with proprietary frontier systems, Granite may trade some broad benchmark performance for smaller computing requirements, transparent licensing, and deployment control.
    
     
    
     
     The four providers in this section share an enterprise orientation but approach it differently. Mistral offers a broad open and hosted portfolio. Cohere centers retrieval, multilingual work, and private deployment. AI21 concentrates on the Jamba architecture. IBM distributes compact models across language, vision, documents, speech, retrieval, safety, and time series.
    
     
    
     
     Their value becomes clearest when selection begins with the workload rather than the most familiar consumer brand.
    
     
    
     
     Amazon, Microsoft, and NVIDIA Connect Models to Cloud and Compute Platforms 
     
    
     
     Amazon, Microsoft, and NVIDIA sell models and the infrastructure used to operate models. Amazon Web Services and Microsoft Azure host partner systems beside their own families. NVIDIA supplies accelerators, networking, inference software, model containers, and reference models.
    
     
    
     
     Their influence can shape procurement even when a customer selects a model developed by another organization.
    
     
    
     
     Amazon 
     
    
     
     Amazon Nova 2 includes Nova 2 Lite, Nova 2 Sonic, and Nova Multimodal Embeddings.
    
     
    
     
     Nova 2 Lite accepts text, images, video, and documents and produces text. It supports a context window of up to 1 million tokens and a maximum output of 64,000 tokens. Amazon positions it as a cost-efficient model for automation, document processing, customer support, reasoning, and multimodal analysis.
    
     
    
     
     Nova 2 Sonic supports low-latency speech interaction. It is intended for voice agents, conversational applications, and speech-to-speech workflows.
    
     
    
     
     Nova Multimodal Embeddings converts text, documents, images, video, and audio into a shared semantic space. This allows an application to search one form of media using another, such as finding a video from a text description or retrieving an image related to an audio segment.
    
     
    
     
     The earlier Nova generation remains available through Amazon Bedrock. Nova Premier is its highest-capability understanding model. Nova Pro serves general multimodal work. Nova Lite targets lower-cost multimodal processing. Nova Micro is a compact text-only model.
    
     
    
     
     Nova Sonic handles conversational audio. Nova Canvas generates images, and Nova Reel generates video. Existing customers may continue using those models even as Nova 2 receives current development attention.
    
     
    
     
     Amazon’s strategy is tied closely to Bedrock. Customers can combine Amazon Nova with models from Anthropic, Meta, Mistral, Cohere, and other suppliers through one cloud service.
    
     
    
     
     Bedrock adds knowledge bases, agents, guardrails, evaluation, monitoring, permissions, and enterprise controls. A customer may benefit from a single cloud environment, but model behavior, license terms, and pricing still differ by provider.
    
     
    
     
     Amazon’s advantage is distribution into existing cloud accounts. A customer already using AWS identity, storage, networking, databases, and security products can adopt model services without establishing a separate infrastructure platform.
    
     
    
     
     The corresponding risk is platform dependence. Applications built deeply around Bedrock agents, proprietary knowledge-base features, and AWS-specific controls may require substantial effort to move elsewhere.
    
     
    
     
     Microsoft 
     
    
     
     Microsoft’s MAI model family now covers reasoning, coding, images, transcription, and speech.
    
     
    
     
     MAI-Thinking-1 is Microsoft AI’s reasoning model. It is designed for mathematics, software engineering, analysis, and general problem solving. MAI-Code-1-Flash is a lightweight agentic coding model integrated with GitHub Copilot and Visual Studio Code.
    
     
    
     
     MAI-Image-2.5 supports text-to-image generation and image editing. MAI-Image-2.5-Flash offers a faster and less expensive tier. MAI-Transcribe-1.5 converts speech into text, including noisy and specialist audio. MAI-Voice-2 generates low-latency expressive speech.
    
     
    
     
     Earlier models include MAI-Image-2, MAI-Image-2-Efficient, MAI-Image-1, MAI-Transcribe-1, MAI-Voice-1, and MAI-1-preview. These releases document the development path toward the current family but are not equal recommendations for new systems.
    
     
    
     
     Microsoft also develops the Phi family. Phi-4, Phi-4-reasoning, Phi-4-mini-instruct, Phi-4-mini-reasoning, and Phi-4-multimodal-instruct support compact deployment, local applications, research, and narrower tasks.
    
     
    
     
     Phi models address a different need from MAI-Thinking-1. They trade frontier scale for lower hardware demand and easier deployment. A smaller model can be the better choice for classification, extraction, local assistance, or applications with strict cost limits.
    
     
    
     
     Microsoft’s product distribution extends beyond its own models. Azure provides access to OpenAI and outside open models. Microsoft 365 Copilot, GitHub Copilot, security products, and business applications can use different models or routing policies.
    
     
    
     
     The product name “Copilot” does not identify one fixed model. A feature may use MAI, OpenAI, Phi, or a combination selected by Microsoft. Enterprise buyers should ask which model family, data terms, and service boundary apply to the specific feature they plan to adopt.
    
     
    
     
     Microsoft’s in-house expansion reduces dependence on one model partner and creates systems optimized for its own software. Customers benefit from integration with identity, permissions, office applications, developer tools, and cloud infrastructure. They should still evaluate portability if a workflow becomes tightly coupled to Microsoft-specific services.
    
     
    
     
     NVIDIA 
     
    
     
     NVIDIA Nemotron 3 is an open-model family designed for agents, reasoning, coding, multimodal work, retrieval, speech, safety, and document processing.
    
     
    
     
     Nemotron 3 Ultra has 550 billion total parameters and approximately 55 billion active parameters. NVIDIA positions it for demanding multi-agent workflows, long-running research, planning, code generation, synthesis, verification, and recovery.
    
     
    
     
     Nemotron 3 Super has 120 billion total parameters and approximately 12 billion active parameters. It targets software development, cybersecurity triage, and multi-agent work that needs high capability with lower computing demand than Ultra.
    
     
    
     
     Nemotron 3 Nano has 30 billion total parameters and approximately 3 billion active parameters. It is designed for efficient coding, reasoning, mathematics, and long-context processing.
    
     
    
     
     Nemotron 3 Nano Omni uses the same 30B-A3B scale and adds text, image, video, and audio understanding. It can act as a multimodal subagent within a larger system.
    
     
    
     
     The family also includes Nemotron Retriever for extraction, embeddings, reranking, and document retrieval. Nemotron Parse reconstructs text, tables, reading order, and layout from complex documents. Nemotron Speech supports voice and audio applications.
    
     
    
     
     NVIDIA distributes models through downloadable weights, NVIDIA Inference Microservices, build services, and enterprise software. A customer can use optimized containers, NVIDIA hardware, or managed model endpoints.
    
     
    
     
     The Cosmos program extends NVIDIA’s work into physical AI. Cosmos models support robotics, autonomous systems, synthetic data, world representation, and simulation. These tasks require models to reason about space, time, movement, physical constraints, and possible actions.
    
     
    
     
     NVIDIA benefits whenever demand rises for model training and inference, regardless of which provider leads a language benchmark. Nemotron gives the company its own model assets, but its larger influence comes from graphics processors, networking, software libraries, inference optimization, and reference architectures.
    
     
    
     
     The infrastructure connection creates convenience and concentration risk. A model optimized for one accelerator or cloud can offer stronger performance there. It may also become harder to move.
    
     
    
     
     Buyers should measure portability at the model, runtime, hardware, orchestration, data, and monitoring layers. Downloadable weights do not automatically guarantee simple migration.
    
     
    
     
     ByteDance, Baidu, Z.ai, Tencent, and Perplexity Broaden the Global Provider Map 
     
    
     
     A provider list limited to American companies misses a substantial share of model development. ByteDance, Baidu, Z.ai, and Tencent operate major research and commercial programs in China, often combining general language models with image, video, speech, robotics, and enterprise services.
    
     
    
     
     Perplexity occupies a different category as a search-centered model provider and orchestration platform. Together, these companies show how competition is moving toward agents, multimedia, search grounding, and national technology strategies.
    
     
    
     
     ByteDance Seed 
     
    
     
     ByteDance Seed2.1 was released on June 23, 2026. It is an agent-capable model family designed for professional work, coding, tool use, multimodal understanding, and longer task execution.
    
     
    
     
     Seed2.1 Pro is the higher-capability edition described in ByteDance’s evaluations. The family is available through Doubao and Volcano Engine services, with access and identifiers differing by region and product.
    
     
    
     
     Earlier Seed2.0 editions include Pro, Lite, Mini, and Code. They may remain present in existing workflows even after Seed2.1 becomes the recommended generation.
    
     
    
     
     Seedream 5.0 Pro is ByteDance’s higher-tier image-generation model. It emphasizes image-text alignment, structural coherence, typography, design work, and complex visual layouts. Seedream 5.0 Lite provides a less expensive image tier with reasoning and search-assisted generation.
    
     
    
     
     Seedance 2.0 handles video creation. It accepts combinations of text, images, audio, and video and can generate synchronized audiovisual output. It also supports video extension, editing, references, and camera-direction controls.
    
     
    
     
     Seeduplex is a full-duplex speech-language model. Full-duplex interaction allows the system to listen and respond with less rigid turn-taking than a conventional voice assistant. Seed Audio 1.0 supports audio generation. Seed3D addresses three-dimensional content, and Seed GR-RL applies reinforcement learning to robotics.
    
     
    
     
     Distribution occurs through ByteDance research releases, Volcano Engine, Doubao, Feishu, Coze, and related products. The model name visible to a developer may differ from the consumer-facing brand.
    
     
    
     
     Baidu 
     
    
     
     Baidu ERNIE 5.1 is the company’s current general flagship. Released on May 9, 2026, it was derived from the ERNIE 5.0 training foundation through an elastic model architecture.
    
     
    
     
     Baidu states that ERNIE 5.1 uses approximately one-third of ERNIE 5.0’s total parameters and about half its active parameters. The design seeks to retain high capability with lower training and inference cost.
    
     
    
     
     ERNIE 5.0 remains an important model. It uses a unified multimodal architecture trained across text, images, video, and audio rather than attaching separate media encoders only after text-model training.
    
     
    
     
     ERNIE-Image is an open 8B text-to-image model based on a diffusion-transformer design. PaddleOCR-VL-1.5 is a compact vision-language model for document parsing, including complex layouts, tables, formulas, and scanned pages.
    
     
    
     
     Earlier ERNIE 4.5 and 4.x models remain present in open repositories, cloud services, and customer systems. Baidu connects the ERNIE family to search, cloud services, maps, consumer applications, enterprise software, and autonomous-system research.
    
     
    
     
     The unified multimodal approach can support tasks that combine spoken instructions, video, written documents, and generated visual content. It also requires separate evaluation for each modality because strong text performance does not establish reliable video, audio, or image behavior.
    
     
    
     
     Z.ai 
     
    
     
     GLM-5.2 is Z.ai’s current flagship. Released on June 16, 2026, it is designed for long-horizon tasks, software engineering, tool use, reasoning, and agents.
    
     
    
     
     GLM-5.2 supports a context window of up to 1 million tokens. Z.ai positions it for project-scale engineering in which one task can move from requirements through implementation and delivery.
    
     
    
     
     Earlier models include GLM-5.1, GLM-5, GLM-5-Turbo, GLM-4.7, GLM-4.6, GLM-4.5, and lower-cost Flash or Air editions. Visual models include GLM-5V-Turbo, GLM-4.6V, and GLM-4.5V.
    
     
    
     
     Z.ai also provides GLM-Image and CogView for image generation, video services based on CogVideo technology, GLM-OCR for document extraction, embedding models, and reranking models.
    
     
    
     
     The rapid progression from GLM-5 to GLM-5.1 and GLM-5.2 illustrates why model lists need an exact date. A catalog accurate in April 2026 could be outdated by June.
    
     
    
     
     Z.ai offers models through its international developer platform, Chinese services, coding subscriptions, and downloadable releases. Availability, pricing, and aliases can differ among those channels.
    
     
    
     
     Tencent 
     
    
     
     Tencent Hy3 was released on July 6, 2026, following an earlier preview.
    
     
    
     
     Hy3 is a mixture-of-experts model with 295 billion total parameters and approximately 21 billion active parameters. It supports a context window of up to 256,000 tokens and combines fast and slower reasoning modes.
    
     
    
     
     Tencent positions Hy3 for reasoning, coding, agents, office productivity, financial modeling, front-end design, and game production. It is integrated into Tencent services and is available through Tencent Cloud.
    
     
    
     
     Hy-MT2-30B-A3B is an open translation model supporting 33 languages and five regional forms. HunyuanImage supports image generation. Hunyuan3D generates three-dimensional assets. HY-World addresses world generation and simulation, and HY-Embodied supports embodied-intelligence research.
    
     
    
     
     Tencent uses both Hy and Hunyuan branding. Newer general and translation models use the shorter Hy name, and media, 3D, world, and earlier systems retain Hunyuan branding.
    
     
    
     
     The naming change can make outside model lists appear inconsistent even when they describe related research and product programs.
    
     
    
     
     Tencent’s distribution strength comes from cloud services, communications, gaming, media, enterprise software, and consumer applications. Its models can enter products through integrated services rather than direct developer selection.
    
     
    
     
     Perplexity 
     
    
     
     Perplexity Sonar is designed around web-grounded answers rather than standalone offline generation.
    
     
    
     
     Sonar provides fast and economical search-based responses. Sonar Pro performs broader retrieval and synthesis. Sonar Reasoning Pro combines search with extended reasoning. Sonar Deep Research conducts larger multi-source research tasks and produces long analytical outputs.
    
     
    
     
     The Sonar API remains supported but is in maintenance mode. Perplexity recommends the Agent API for new integrations. The Agent API can use Perplexity tools and models from external providers through one orchestration service.
    
     
    
     
     Perplexity also offers a Search API for ranked web results and embedding services for retrieval. The company’s value comes from the combination of search, ranking, source retrieval, orchestration, and language generation.
    
     
    
     
     This makes Perplexity an edge case in provider comparisons. It develops Sonar models, but much of the service’s performance depends on the retrieval system around them.
    
     
    
     
     Comparing Sonar with an offline language model without accounting for search access would be misleading. The model and the information system should be evaluated together.
    
     
    
     
     These providers have strategic significance beyond product features. Governments and companies increasingly treat model access, compute capacity, cloud control, training data, and technical talent as national assets.
    
     
    
     
     The debate over sovereign AI concerns whether dependence on foreign model services can affect public administration, industrial policy, security, bargaining power, and economic resilience. A global model catalog should describe capability without ignoring the legal and regional conditions that determine who can use it.
    
     
    
     
     Image, Video, Speech, Retrieval, Safety, and Robotics Models Form Distinct Markets 
     
    
     
     General language models receive most public attention, but specialist model categories often determine whether a commercial system works.
    
     
    
     
     An image generator needs visual composition, editing controls, reference consistency, and readable text. A speech agent needs low latency, interruption handling, and natural prosody. A retrieval system needs embeddings that place related items close together. A safety classifier needs dependable policy labels. A robotics model needs spatial and physical reasoning.
    
     
    
     
     Treating all of these as minor features of a chatbot hides the technical and commercial structure of the market.
    
     
    
     
     Image generation has moved from one-shot text prompts toward repeated editing and agentic control. OpenAI offers GPT Image 2. Google offers Nano Banana 2, Nano Banana 2 Lite, and Nano Banana Pro. Meta offers Muse Image. Microsoft offers MAI-Image-2.5 and its Flash edition.
    
     
    
     
     Amazon offers Nova Canvas from its earlier Nova generation. ByteDance offers Seedream 5.0 Pro and Lite. Baidu offers ERNIE-Image. Tencent offers HunyuanImage. Z.ai offers GLM-Image and CogView. MiniMax retains an image-generation service.
    
     
    
     
     These systems differ in typography, identity consistency, prompt adherence, editing precision, output resolution, safety filters, and commercial terms. An impressive demonstration does not prove that a model will retain a person’s appearance across 20 images or produce accurate text in a dense infographic.
    
     
    
     
     Video generation is developing as a separate contest. Google’s Veo family, xAI’s Imagine service, Amazon Nova Reel, ByteDance Seedance 2.0, MiniMax Hailuo 2.3, Meta Muse Video, and Tencent’s media and world models use different approaches.
    
     
    
     
     Some generate short clips from text or images. Others support editing, camera control, reference composition, synchronized sound, character consistency, or continuation of an existing sequence.
    
     
    
     
     Release status needs careful wording. A model introduced in a research announcement may not be broadly available through a public API. A consumer application may provide limited access before an enterprise service launches. Regional availability may also differ.
    
     
    
     
     Music models form another category. Google’s Lyria family supports generated music and interactive creation. MiniMax offers Music-3.0 and related services. ByteDance’s Seed Audio program includes broader audio-generation work.
    
     
    
     
     Copyright, performer identity, training-data governance, and commercial licensing can matter as much as sound quality. A technically strong sample does not establish that a model suits a publisher, broadcaster, game studio, or advertising campaign.
    
     
    
     
     Speech covers at least four tasks: recognition, generation, speech-to-speech interaction, and audio-language understanding.
    
     
    
     
     OpenAI’s Realtime and audio families cover live interaction, transcription, diarization, translation, and generated speech. Google offers Live, Translate, and text-to-speech Gemini variants. Amazon Nova 2 Sonic supports conversational audio. Microsoft offers MAI-Transcribe-1.5 and MAI-Voice-2.
    
     
    
     
     Mistral’s Voxtral family provides transcription, realtime recognition, speech generation, and audio-language models. Cohere Transcribe adds multilingual recognition. ByteDance Seeduplex supports full-duplex conversation. MiniMax offers speech-2.8-hd and speech-2.8-turbo.
    
     
    
     
     Latency can dominate speech-model selection. A system that waits several seconds before responding may be acceptable for transcription but fail as a conversational agent. Full-duplex systems attempt to handle interruption, overlap, and short acknowledgement sounds closer to human conversation.
    
     
    
     
     Voice products also require consent controls, identity protection, recording policies, accent testing, noise handling, and protections against impersonation.
    
     
    
     
     Embedding and reranking models support retrieval-augmented generation, commonly abbreviated as RAG. An embedding model turns a query, paragraph, image, audio clip, or video segment into a vector. A search system retrieves nearby vectors, and a reranker reorders the candidates before a language model writes an answer.
    
     
    
     
     OpenAI, Google, Cohere, Alibaba, Amazon, IBM, Mistral, NVIDIA, Perplexity, and Z.ai provide embedding or reranking components. Cohere’s Rerank v4 models, Amazon’s multimodal embeddings, Qwen’s paired embedding and reranking families, and IBM’s compact multilingual models show how retrieval has become its own competitive category.
    
     
    
     
     Good retrieval can reduce unsupported answers by supplying relevant organizational material, but it does not guarantee truth. Source documents may be wrong, outdated, incomplete, or poorly divided into searchable units.
    
     
    
     
     Access controls can fail if an index ignores document permissions. A reranker can prefer persuasive but less authoritative text. Production systems need document governance, source dates, permission-aware search, evaluation sets, and visible provenance.
    
     
    
     
     Safety models operate at several layers. OpenAI offers omni-moderation. Meta provides Llama Guard 4, Prompt Guard 2, and LlamaFirewall. Alibaba offers Qwen3Guard. IBM offers Granite Guardian 4.1. NVIDIA provides Nemotron safety technology. Mistral offers moderation services.
    
     
    
     
     No single classifier can secure an application. Tool permissions, rate limits, identity controls, data-loss prevention, logging, approval rules, and human review remain necessary.
    
     
    
     
     Agent security has become more important because models can operate browsers, write code, access files, send messages, and call business systems. A harmless-looking webpage can contain instructions designed to redirect an agent. A compromised document can attempt to extract secrets. An over-permissioned coding agent can alter production systems.
    
     
    
     
     Safety evaluation must examine the complete tool-enabled application rather than the language model in isolation.
    
     
    
     
     Physical AI extends model competition into robots, vehicles, industrial systems, and simulation. Google’s Gemini Robotics-ER, NVIDIA Cosmos, ByteDance Seed GR-RL, Tencent HY-Embodied, and related world models process perception, action, or physical environments.
    
     
    
     
     They may combine camera feeds, language instructions, state estimation, simulation, and control policies. Their errors can affect machinery and people, placing greater weight on testing, operational boundaries, redundancy, and human override.
    
     
    
     
     Specialization also affects business models. General chat access is often sold by token or subscription. Image and video services may be priced by output, duration, resolution, or computing unit. Speech can be priced by audio minute. Embeddings may be priced by input volume, and rerankers by request.
    
     
    
     
     Robotics systems can combine software licenses with sensors, hardware, simulation, and integration. The question of AI profitability depends partly on whether providers can earn enough from these specialist services to cover model development, computing, energy, and distribution costs.
    
     
    
     
     General models may absorb some specialist functions over time, but dedicated models will remain valuable where latency, cost, accuracy, hardware limits, or governance dominate.
    
     
    
     
     A compact transcription model can outperform an expensive general agent on a narrow audio pipeline. A reranker can improve search at a small fraction of the cost of asking a frontier model to inspect every document. A moderation model can process large request volumes before a more expensive model receives the prompt.
    
     
    
     
     The commercial market is likely to support broad multimodal models and focused components at the same time.
    
     
    
     
     How Major AI Providers and Models Should Be Compared 
     
    
     
     A credible comparison begins with a defined workload. “Best AI model” is too broad to guide procurement because a customer-support assistant, coding agent, scientific-research tool, media generator, document-processing pipeline, and warehouse robot have different success criteria.
    
     
    
     
     Evaluation should begin with representative tasks, approved data, expected request volume, response-time requirements, legal conditions, and the consequences of an error.
    
     
    
     
     Capability tests should use the organization’s own material where permitted. Public benchmarks can identify candidates, but they may be optimized, contaminated by training data, or weakly related to production work.
    
     
    
     
     A legal group needs accurate document analysis and reliable quotations. A software team needs patches that compile and pass tests. A multilingual service needs performance in the exact languages and regional forms it serves. A media team needs consistent subjects, readable text, editing control, and suitable commercial rights.
    
     
    
     
     Model status comes next. A stable production model carries different expectations from a preview, experimental release, restricted system, legacy endpoint, or announced product.
    
     
    
     
     Contracts and technical documentation should record the exact identifier, version policy, context limit, output limit, region, and retirement-notice period. Aliases that automatically move to newer models can simplify upgrades but introduce behavior changes without a code change. Fixed snapshots improve reproducibility but can miss later improvements or safety updates.
    
     
    
     
     Cost requires more than the advertised input-token price. Reasoning models can use billed reasoning tokens. Long prompts raise input costs and latency. Tool calls, web search, image generation, speech minutes, video duration, embeddings, storage, and reranking add separate charges.
    
     
    
     
     A cheaper model that produces more errors can raise review and correction costs. A larger model may reduce workflow steps enough to cost less overall. The relevant metric is the cost of completing an acceptable task rather than the cost of one token.
    
     
    
     
     Context windows require similar care. A 1 million-token limit allows very large inputs, but effective recall can vary across the prompt. Sending an entire document repository on every request is rarely efficient.
    
     
    
     
     Retrieval, structured databases, summaries, and workflow memory can provide better results at lower cost. Long context is useful for source code, legal records, research collections, and agent histories, but it does not replace information architecture.
    
     
    
     
     Openness should be measured through several questions. Are the weights downloadable? Does the license permit commercial use and modification? Can the model run on available hardware? Are training methods, data sources, evaluations, and safety practices documented? Can the customer fine-tune it? Does deployment require provider software or a proprietary runtime?
    
     
    
     
     An open-weight model can still create dependence on a cloud service, accelerator, inference library, or data pipeline.
    
     
    
     
     Privacy and governance must be assessed at the service level. A provider may offer different retention terms for a consumer chatbot, business subscription, cloud endpoint, or self-hosted model.
    
     
    
     
     Regional processing, encryption, logging, administrator controls, identity integration, and training-data use can differ. Regulated organizations should obtain contractual terms rather than rely on a general product description.
    
     
    
     
     Tool use changes the risk profile. A model that can search internal systems, execute code, purchase services, or send communications needs permission boundaries.
    
     
    
     
     Each tool should expose the minimum required capability. High-impact actions should require confirmation or approval. Logs should show the request, model, tool call, result, and user identity. Security testing should include prompt injection, secret extraction, malicious files, compromised websites, and unexpected tool sequences.
    
     
    
     
     Multimodal systems need separate evaluation for every input and output type. Strong text reasoning does not prove accurate image interpretation. Good image generation does not prove reliable optical character recognition. Natural speech does not prove accurate transcription in noisy environments.
    
     
    
     
     A provider’s general model name can hide different internal components for audio, vision, search, and media generation. Testing must follow the actual service path used in production.
    
     
    
     
     Portability deserves a planned budget. Prompts written for one provider may depend on its tool schema, system-message rules, safety policies, structured-output format, or agent runtime.
    
     
    
     
     Embeddings from different models generally cannot share one index without rebuilding it. Fine-tunes can be provider-specific. Evaluation suites, abstraction layers, standard data formats, and export procedures reduce switching costs.
    
     
    
     
     A multi-model strategy can limit dependence but adds engineering and governance work. Routing may send simple requests to a small model and difficult requests to a frontier system. Sensitive work may remain on-premises, and public research may use a hosted service.
    
     
    
     
     Coding can use a specialist model, with another model reviewing the result. The router itself must be evaluated because poor classification can send data or tasks to the wrong destination.
    
     
    
     
     Human oversight should match consequence rather than model size. Low-risk formatting can run automatically. Financial, medical, legal, safety, personnel, and public-policy outputs require stronger review.
    
     
    
     
     Agents that change systems or communicate externally need approval boundaries. A model’s confidence language should not determine the review level because fluent systems can sound certain when wrong.
    
     
    
     
     Organizations also need continuous evaluation. Model behavior can change after an alias update, safety adjustment, routing change, or provider-side optimization.
    
     
    
     
     A regression suite should test accuracy, refusal behavior, tool use, latency, cost, structured output, and security. Results should be stored by model identifier and date. Retirement notices should trigger migration tests before the deadline.
    
     
    
     
     Competitive claims require restraint. Providers publish selected benchmarks under different prompts, tool settings, reasoning budgets, and sampling methods. Independent tests can add perspective but may still omit cost, latency, regional access, and production reliability.
    
     
    
     
     The debate over whether AI will become a commodity turns on more than model quality. Distribution, proprietary data, workflow integration, brand, security, hardware efficiency, and switching costs can preserve differentiation even when raw capabilities converge.
    
     
    
     
     Natural-language interfaces will also influence adoption. People increasingly instruct agents in ordinary language and delegate multi-step work. That creates a contest over the conventions used for permissions, confirmation, memory, accountability, and control.
    
     
    
     
     A provider that makes delegation understandable, observable, and reversible may win users without leading every benchmark.
    
     
    
     
     A practical selection process can use six stages:
    
     
    
     
     
     Define the task, data, users, volume, latency, and acceptable error rate.
    
     
    
     
     Select a candidate set using status, modality, region, and deployment requirements.
    
     
    
     
     Test representative cases and score quality, cost, latency, and safety.
    
     
    
     
     Review contracts, privacy, licensing, retention, and retirement terms.
    
     
    
     
     Pilot the complete workflow with tools, retrieval, monitoring, and human approval.
    
     
    
     
     Maintain regression tests, fallback models, and an exit plan.
    
     
     
    
     
     No provider wins every stage. OpenAI and Anthropic may lead a demanding reasoning task. Google may provide the most complete multimodal and media portfolio. Meta, DeepSeek, Alibaba, Mistral, IBM, AI21, Cohere, NVIDIA, or Tencent may provide stronger deployment control.
    
     
    
     
     Amazon or Microsoft may fit an existing cloud environment. Perplexity may suit search-grounded work. ByteDance and MiniMax may be attractive for media production. The correct decision is workload-specific and can change after a model release, price adjustment, policy update, or retirement notice.
    
     
    
     
     Summary 
     
    
     
     The major model families available as of July 20, 2026, include OpenAI GPT-5.6, Anthropic Claude Fable 5 and Claude 5 models, Google Gemini 3 models, xAI Grok 4.5, Meta Muse Spark 1.1 and Llama 4, DeepSeek V4, Alibaba Qwen3.7, Moonshot Kimi K3, MiniMax-M3, Mistral’s current Large, Medium, Small, and Ministral families, Cohere Command A+, Amazon Nova 2, Microsoft MAI and Phi, NVIDIA Nemotron 3, IBM Granite 4.1, AI21 Jamba2, ByteDance Seed2.1, Baidu ERNIE 5.1, Z.ai GLM-5.2, Tencent Hy3, and Perplexity Sonar.
    
     
    
     
     That list still hides the main development. Providers are dividing their portfolios among reasoning, speed, coding, images, video, speech, embeddings, reranking, safety, agents, and physical AI. They are also mixing hosted access, open weights, cloud distribution, local deployment, restricted models, previews, and automatically updated aliases.
    
     
    
     
     The catalog has become a map of access and operating models as much as a list of technical systems.
    
     
    
     
     Competition is likely to remain fluid. New releases can replace a flagship within weeks, and retirement notices can force migration soon after an update. The most dependable approach is to maintain a dated inventory, record exact identifiers, test representative workloads, and separate announced capability from available service.
    
     
    
     
     The deeper commercial issue is whether models become interchangeable components or remain differentiated platforms. Open-weight releases and falling inference prices push toward interchangeability. Proprietary data, agents, search, developer tools, media services, cloud integration, safety controls, and user distribution push in the opposite direction.
    
     
    
     
     Organizations will adopt complete workflows rather than model names alone. The provider that delivers an acceptable combination of capability, price, control, reliability, integration, and governance will often win the deployment even when another company leads a selected benchmark.
    
     
    
     
     Appendix: Useful Books Available on Amazon 
     
    
     
     
     The Alignment Problem 
    
     
    
     
     The Age of AI 
    
     
    
     
     The Coming Wave 
    
     
    
     
     Co-Intelligence 
    
     
    
     
     Life 3.0 
    
     
    
     
     AI Superpowers 
    
     
    
     
     Supremacy 
    
     
     
    
     
     Appendix: Top Questions Answered in This Article 
     
    
     
     Which Company Has the Most Capable AI Model in July 2026? 
    
     
    
     
     No provider can be declared the universal leader because performance depends on the task, service mode, cost, latency, tools, and evaluation method. OpenAI GPT-5.6 Sol, Anthropic Claude Fable 5, Google Gemini 3.1 Pro, and xAI Grok 4.5 belong to the leading proprietary group. Open and hybrid providers can be stronger choices when local control, licensing, price, or specialized deployment matters.
    
     
    
     
     What Is the Difference Between a Model Family and a Model Identifier? 
    
     
    
     
     A family groups related models under one generation or brand, such as GPT-5.6 or Claude 5. A model identifier is the exact technical name used in an application programming interface. Identifiers matter because they can specify a tier, snapshot, preview, or dated version that behaves differently from the broad family name.
    
     
    
     
     Why Do Providers Offer Several Sizes of the Same Model Family? 
    
     
    
     
     Different sizes balance capability, speed, hardware demand, and cost. A large model may handle complex reasoning and agents, and a small model may process classification, extraction, or high-volume requests more efficiently. Organizations often combine sizes so expensive models receive only tasks that need them.
    
     
    
     
     What Does Open-Weight Mean? 
    
     
    
     
     Open-weight means the trained numerical parameters can be downloaded under stated license terms. It does not guarantee that the training data, full source code, training process, or commercial rights are unrestricted. Each license and release package requires separate review before deployment or modification.
    
     
    
     
     Are Preview Models Suitable for Production Systems? 
    
     
    
     
     A preview model can be suitable for pilots and controlled use, but it carries greater change and retirement risk than a stable release. Providers may alter behavior, limits, pricing, or identifiers with less notice. Production use requires regression tests, fallback plans, and a clear understanding of the service commitment.
    
     
    
     
     Why Are Embedding and Reranking Models Important? 
    
     
    
     
     Embedding models make documents and queries searchable by meaning rather than exact words. Rerankers reorder retrieved results so the most relevant material reaches the generative model. Weak retrieval can produce inaccurate answers even when the language model itself is highly capable.
    
     
    
     
     Do Large Context Windows Remove the Need for Retrieval? 
    
     
    
     
     No. A large context window allows more material in one request, but cost, latency, and uneven attention can still limit results. Retrieval selects relevant material, preserves access controls, and reduces repeated input. Many systems benefit from combining long context with structured search and document management.
    
     
    
     
     Can an Organization Switch AI Providers Easily? 
    
     
    
     
     Switching can be difficult when prompts, tool schemas, embeddings, fine-tunes, safety rules, or agent runtimes depend on one provider. Portability improves when teams use standard data formats, maintain independent evaluation suites, isolate provider-specific code, and preserve export procedures. Embedding indexes commonly need rebuilding after a model change.
    
     
    
     
     Why Can the Same Product Use More Than One Model? 
    
     
    
     
     Products increasingly route requests according to complexity, modality, latency, safety, or subscription level. A consumer may see one product name even though a small model handles simple requests and a frontier model handles difficult work. Search, speech, image, and moderation components may also come from separate models.
    
     
    
     
     How Often Should an AI Model Catalog Be Updated? 
    
     
    
     
     A public catalog should be checked at least monthly, and production inventories should monitor provider notices continuously. Fast release periods may require weekly review because flagships, aliases, previews, and retirement dates can change within days. Every entry should include a verification date and exact provider documentation.
    
     
    
     
     Appendix: Glossary of Key Terms 
     
    
     
     Application Programming Interface 
    
     
    
     
     A software interface that lets an application send requests to a model and receive outputs. Model providers use application programming interfaces to expose text generation, images, audio, embeddings, tools, and related services under defined technical and commercial terms.
    
     
    
     
     Agent 
    
     
    
     
     A model-based system that plans and performs multi-step work using tools, memory, files, browsers, code, or business applications. An agent differs from a basic chatbot because it can take actions and continue working toward a task rather than produce one isolated response.
    
     
    
     
     Alias 
    
     
    
     
     A convenient model name that can point to a provider-selected underlying version. Aliases simplify upgrades because application code may remain unchanged, but they can reduce reproducibility when the provider changes the model behind the name.
    
     
    
     
     Context Window 
    
     
    
     
     The maximum quantity of tokens a model can process in one request, including input, output, and sometimes internal reasoning. A larger window can hold more documents or conversation history, though it does not guarantee equal recall across all supplied material.
    
     
    
     
     Deprecated Model 
    
     
    
     
     A model that a provider discourages for new use and may remove after a stated date. Deprecation usually starts a migration period during which customers should test a successor, update code, and verify changed behavior.
    
     
    
     
     Embedding Model 
    
     
    
     
     A model that converts text, images, audio, or other content into numerical vectors. Systems use those vectors for semantic search, clustering, recommendations, duplicate detection, and retrieval of material related by meaning.
    
     
    
     
     Foundation Model 
    
     
    
     
     A broadly trained model that can be adapted to many tasks through prompting, tools, retrieval, fine-tuning, or application design. Language, multimodal, image, speech, video, and physical-world systems can all function as foundation models.
    
     
    
     
     Mixture of Experts 
    
     
    
     
     A model architecture containing groups of parameters called experts, with selected experts activated for each token or input. The design can provide high total capacity with lower inference cost than activating the full model for every calculation.
    
     
    
     
     Multimodal Model 
    
     
    
     
     A model that processes or generates more than one type of content, such as text, images, audio, video, or documents. Multimodal capability should be tested separately for each input and output type because performance can differ substantially.
    
     
    
     
     Open-Weight Model 
    
     
    
     
     A model whose trained parameters are available for download. Rights to use, modify, redistribute, or commercialize the model depend on its license, and the release may not include the original training data or complete training code.
    
     
    
     
     Preview Model 
    
     
    
     
     A publicly accessible model offered before the provider gives it full production status. Preview releases may change quickly, carry shorter support commitments, have lower quotas, or disappear sooner than stable models.
    
     
    
     
     Reasoning Model 
    
     
    
     
     A model configured or trained to spend added computation on multi-step problems before producing an answer. Reasoning can improve mathematics, coding, planning, and analysis, though it commonly increases latency and cost.
    
     
    
     
     Reranker 
    
     
    
     
     A model that receives an initial list of search results and reorders them according to relevance. Reranking often improves retrieval-augmented generation by placing stronger source material near the top of the model’s context.
    
     
    
     
     Snapshot 
    
     
    
     
     A fixed, often dated model version that preserves behavior more reliably than a moving alias. Snapshots help regression testing and regulated deployment, though they may miss later performance improvements, bug fixes, or safety changes.
    
     
    
     
     Token 
    
     
    
     
     A unit used by language models to represent pieces of text, code, or other encoded content. Providers commonly measure context limits and pricing in tokens, and one token does not consistently equal one word.
    
     
    
     
     [meta keywords=“AI models by provider, major AI providers, GPT-5.6, Claude Fable 5, Gemini 3.1, Grok 4.5, Meta Muse, Llama 4, DeepSeek V4, Qwen3.7-Max, Kimi K3, Mistral Large 3, MiniMax-M3, Command A+, Amazon Nova 2, Microsoft MAI, NVIDIA Nemotron 3, IBM Granite 4.1, Seed2.1, ERNIE 5.1”]
    
     

---

### 6. Gemma 4 vs DeepSeek V4 vs Qwen 3.6: Open-Source AI 2026

- **Author:** Danar Mustafa — byline resolves to a person: **yes**
- **Site:** The Tech Society (`digitalstrategy-ai.com`) · 328 posts, 0.27/day, 1 bylines sampled
- **Site describes itself as:** AI, Technology & Digital Strategy for Leaders and Builders
- **Date:** 2026-05-13 · 4,217 words · 0 comments · 1 likes
- **Tags:** — · **Categories:** Danar Mustafa
- **URL:** https://digitalstrategy-ai.com/2026/05/13/gemma-4-googles-open-source-llm/
- **Type:** comparison · **Provenance:** vendor claim restated
- **Artifacts: 4** — `bench_number`×31, `code_fence`×4, `conditioned_comparison`×1, `price`×8
- **Benchmark figures:** 14 mentions, 0 attributed near the number

     
    
    
     
    
     
     Open Source AI 
    ```
    Apache 2.0
    ```
     Google DeepMind 
    ```
    April 2026
    ```
     Open-Weight Race
    
    
    
     
     Open-Source Model Review · Gemma 4 · Chinese Competition
    
     Apache 2.0. Four model sizes from phone to data-center. 256K context. Native multimodality. The most consequential open-weight release of 2026 — and a deliberate counter-move against DeepSeek V4, Qwen 3.6, GLM-5.1, and Kimi K2.6, the Chinese open-source models that have steadily closed the gap to the frontier. Inside what Gemma 4 actually offers developers and organizations, and why the global open-source AI race is no longer a Western story.
    
     
     Published · May 11, 2026 
     Reading time · 13 min 
     Category · Open Source AI & Strategy 
     
    
     
    
     
     In one paragraph: Google DeepMind released Gemma 4 on April 2, 2026 — four open-weight model sizes (E2B, E4B, 26B A4B, 31B) shipping under a commercially permissive Apache 2.0 license , with a 256K token context window, native multimodal text/image/audio support, and the ability to run on hardware from phones to servers. Gemma 4 31B scores 89.2% on AIME 2026 math , 84.3% on GPQA Diamond , and 85.2% on MMLU-Pro , putting it at the top of the dense single-GPU class. But the bigger story is competitive: Chinese open-weight models — DeepSeek V4 Pro , Qwen 3.6 , GLM-5.1 , Kimi K2.6 — now occupy four of the top open-source slots in 2026, with DeepSeek V4 leading raw coding benchmarks (83.7% SWE-bench) and GLM-5.1 leading SWE-bench Pro at 58.4%. The open-source AI race is no longer a single-lab Western story. It is a global race in which Google’s biggest license shift in three years is partly a response to Chinese competitive pressure that Western labs underestimated through 2025.
    
    
    
    
     
    
     
     TL;DR · Seven things to know 
     
     
     Released April 2, 2026 under Apache 2.0 — Gemma’s biggest license shift since launch. No MAU restrictions, no commercial gatekeeping, no acceptable-use enforcement on third parties.
    
     
     Four model sizes : E2B, E4B (for phones, Raspberry Pi, Jetson), 26B A4B (MoE — 4B active), and 31B dense. The same model family scales from a phone to a data center.
    
     
     Benchmark leadership in its weight class. 31B scores 89.2% AIME, 84.3% GPQA Diamond, 80.0% LiveCodeBench, 85.2% MMLU-Pro, 76.9% MMMU-Pro vision. Arena ELO of 1452 beats Qwen 3.5 397B at 1449.
    
     
     256K context window , native multimodal (text + image + audio), 140+ languages.
    
     
     The Chinese open-source surge is real. DeepSeek V4, Qwen 3.6, GLM-5.1, and Kimi K2.6 are all frontier-competitive open-weight models — Chinese labs now ship four top-tier open systems versus one or two a year ago.
    
     
     Specialization matters. Gemma 4 wins on math, vision, and Arena ELO at its weight class. DeepSeek V4 wins coding benchmarks at scale. Qwen 3.6-35B-A3B wins single-GPU practicality. GLM-5.1 leads SWE-bench Pro at 58.4%.
    
     
     The strategic shift : enterprises can now build serious AI products on self-hosted open models for 60-70% of their workload, routing only the hardest problems to closed-frontier APIs. The hybrid stack has become the default architecture for cost-aware AI deployment.
    
     
    
    
    
     For three years, the conventional wisdom about open-source AI was simple: if you wanted production-grade capability, you used Claude or GPT and paid the API bill. Open-weight models — Llama 3, Mistral, early Gemma, Qwen 2 — were useful for experimentation, research, and limited niches, but they were not where you built a real product. By the second quarter of 2026, that conventional wisdom is functionally dead. Gemma 4 , released on April 2, is the strongest evidence yet: a model family from a major Western lab, shipped under a permissive Apache 2.0 license, with benchmark scores that genuinely rival closed-frontier alternatives in their weight class. It is not a research curiosity. It is a deployment-grade open weight model that Google’s customers are now using to replace meaningful portions of their hosted-API spend.
    
    
     What makes this release especially interesting is the strategic context. Gemma 4 did not arrive in a vacuum. It arrived in an open-source AI landscape that has shifted dramatically over the previous twelve months — and the shift is heavily Chinese. DeepSeek V4 , Alibaba’s Qwen 3.6 family , Z.AI’s GLM-5.1 , and Moonshot’s Kimi K2.6 have collectively turned the Chinese open-weight ecosystem into a real competitive bloc. On most public leaderboards, Chinese labs now occupy half or more of the top open-source slots, with several models genuinely competitive against US closed-frontier systems on raw benchmark performance. Google’s Apache 2.0 decision — its first ever for the Gemma line — is partly a product story about empowering developers, and partly a defensive move against losing the open-source narrative entirely to Chinese labs that had no licensing friction to begin with. Let’s walk through both halves of the story.
    
    
     What is Gemma 4? 
     
     Short answer: Gemma 4 is Google DeepMind’s latest open-weight model family, released April 2, 2026. It ships in four sizes (E2B, E4B, 26B A4B, 31B) under the Apache 2.0 license, supports a 256K token context window, runs on hardware from phones to data centers, and is multimodal (text, image, audio). Built from the same research as Gemini 3, it is positioned as the most capable open-weight model family in 2026 — particularly strong on math (89.2% AIME), reasoning (84.3% GPQA), and on-device deployment.
    
    
     Three structural changes define this release. First, the license : prior Gemma releases used Google’s custom “source-available” Gemma Terms of Use, which constrained certain commercial deployments and reserved use-policy enforcement rights to Google. Gemma 4 ships under Apache 2.0 , the same permissive license used by Qwen 3.5 and DeepSeek (MIT). For commercial deployers, this removes legal friction that mattered more than benchmark scores: an Apache 2.0 model can be fine-tuned, redistributed, embedded in commercial products, and modified without ongoing license obligation. For organizations operating in regulated sectors or under data sovereignty requirements, this single change is more consequential than any of the technical updates.
    
    
     Second, the architecture : Gemma 4 includes both dense (E2B, E4B, 31B) and Mixture-of-Experts (26B A4B) variants. The 26B A4B activates only 4 billion parameters per token while keeping 26 billion in memory — a meaningful efficiency gain for inference workloads where total memory is a less binding constraint than active compute. The 31B dense remains the headline flagship for tasks where MoE routing overhead is a concern. Both larger models support a 256K context window.
    
    
     Third, the deployment range : Gemma 4 was deliberately engineered to span the hardware spectrum. The E2B and E4B variants run completely offline on edge devices — phones, Raspberry Pi, NVIDIA Jetson Orin Nano — with near-zero latency. Google collaborated directly with the Pixel team, Qualcomm, and MediaTek to optimize for mobile silicon. Android developers can prototype agentic flows in the AICore Developer Preview today. At the other end, Vertex AI, Cloud Run, GKE, Sovereign Cloud, and TPU-accelerated serving handle the largest deployments. The family is built to be one model lineage that scales from on-device inference to data-center serving without architectural mismatch.
    
    
     
     
     E2B
    
     2B active 
    
    
     Dense · Edge
    
     Phones, Raspberry Pi, Jetson Orin Nano. Offline, near-zero latency.
    
     
    
     
     E4B
    
     4B active 
    
    
     Dense · Edge
    
     Higher-end phones, laptops, edge servers. Multimodal incl. audio.
    
     
    
     
     26B A4B
    
     26B / 4B 
    
    
     MoE · Server
    
     MoE: 4B active. Single workstation GPU. 256K context.
    
     
    
     
     31B
    
     31B dense 
    
    
     Dense · Flagship
    
     Single H100 or A100 80GB. 256K context. Top-of-class benchmarks.
    
     
    
    
    
    
     The benchmark numbers — and where Gemma 4 actually wins 
     
     Short answer: Gemma 4 31B leads its weight class on math (89.2% AIME 2026), reasoning (84.3% GPQA Diamond), general knowledge (85.2% MMLU-Pro), vision (76.9% MMMU-Pro), and human preference (Arena ELO 1452). It is competitive but not class-leading on competitive coding (80.0% LiveCodeBench) and trails on real-world coding tasks (52% SWE-bench), where DeepSeek V4 (83.7%) and Qwen 3.6 (73.4% on a 35B-A3B model) lead. The right read is workload-specific: Gemma 4 wins on reasoning and on-device deployment; DeepSeek and Qwen win on production coding.
    
    
     
     Gemma 4 vs the open-source frontier
    
     Benchmark comparison across math, reasoning, coding, and human preference (May 2026)
    
    
     
    
     
     
     AIME 2026 (math) 
     American Invitational Math · no tools 
     
    
     
     
     Gemma 4 31B 
    
    
     89.2% 
    
    
     
     DeepSeek V4 
    
    
     99.4% 
    
    
     
     GLM-5.1 
    
    
     95.3% 
    
    
     
     Qwen 3.6-35B-A3B 
    
    
     92.7% 
    
    
     
    
     
    
    
     
     
     GPQA Diamond (reasoning) 
     Graduate-level science questions 
     
    
     
     
     Gemma 4 31B 
    
    
     84.3% 
    
    
     
     Qwen 3.6-35B-A3B 
    
    
     86.0% 
    
    
     
     Kimi K2.6 
    
    
     90.5% 
    
    
     
     Llama 4 Scout 
    
    
     74.3% 
    
    
     
    
     
    
    
     
     
     MMLU-Pro (general knowledge) 
     Multilingual professional benchmarks 
     
    
     
     
     Gemma 4 31B 
    
    
     85.2% 
    
    
     
     DeepSeek V4 
    
    
     92.8% 
    
    
     
     Qwen 3.5 27B 
    
    
     86.1% 
    
    
     
    
     
    
    
     
     
     SWE-bench Verified (real coding) 
     Real GitHub issues end-to-end — Chinese labs lead 
     
    
     
     
     DeepSeek V4-Pro 
    
    
     80.6% 
    
    
     
     Qwen 3.6-35B-A3B 
    
    
     73.4% 
    
    
     
     Gemma 4 31B 
    
    
     52.0% 
    
    
     
    
     
    
    
     
     
     Arena ELO (human preference) 
     Pairwise blind A/B testing 
     
    
     
     
     Gemma 4 31B 
    
    
     1452 
    
    
     
     Qwen 3.5 397B 
    
    
     1449 
    
    
     
     Gemma 4 26B A4B 
    
    
     1441 
    
    
     
     DeepSeek V3.2 
    
    
     ~1425 
    
    
     
    
     
    
    
     
    
    
     
     
     Gemma 4 (Google)
    
     
     DeepSeek (China)
    
     
     Qwen (Alibaba)
    
     
     GLM (Z.AI)
    
     
     Kimi (Moonshot)
    
     
     Llama (Meta)
    
     
    
    
     Sources: Google Gemma 4 model card, Hugging Face leaderboards, BenchLM Chinese leaderboard, third-party benchmark aggregations (April-May 2026). Scores vary by methodology; treat ranges as directional.
    
    
    
    
     The honest read across the bars: Gemma 4 wins where reasoning, math, multimodality, and Arena preference matter. It loses where production coding matters — the Chinese labs, particularly DeepSeek and Qwen, simply have stronger coding numbers on the most credible real-world benchmarks. The Arena ELO result is the most editorially interesting data point: Gemma 4 31B sits at 1452 on human pairwise preference testing, edging out even Qwen’s massive 397B model. That suggests Google’s training and RLHF work on Gemma 4 produces responses humans actually prefer at a remarkable parameters-per-quality ratio — which matters more for general assistant work than narrow benchmark scores often capture.
    
    
     
     Gemma 4 doesn’t win every benchmark — and Google’s marketing has been more careful about claiming dominance than usual. What it does win is the practical deployment profile: best-in-class on math and reasoning at sizes that actually fit on commodity hardware, under a license that actually lets you use it.
     — The AI & Tech Society Editorial View 
    
    
    
     The Chinese open-source surge — and why it changed the game 
     
     Short answer: The Chinese open-weight ecosystem in 2026 includes four genuinely frontier-competitive families: DeepSeek (V4, V4-Pro), Alibaba Qwen (3.5, 3.6, 3.6-Plus), Z.AI GLM (5, 5.1), and Moonshot’s Kimi (K2.6). DeepSeek V4 Pro Max scores 87 on BenchLM (vs GPT-5.4 at 88). GLM-5.1 leads open-weight SWE-bench Pro at 58.4%. Kimi K2.6 leads open-weight GPQA at 90.5%. Most ship under MIT or Apache 2.0 with no usage restrictions. The result: the global open-source AI landscape is now multipolar, and “open source” no longer means “Western.”
    
    
     
     
     ◆ DeepSeek (Hangzhou)
    
     DeepSeek V4 / V4-Pro
    
     87 BenchLM · 83.7% SWE-bench · 99.4% AIME 2026
    
     ~1.6T parameters MoE with 49B active. Leads raw coding and math benchmarks at frontier scale. MIT license. Self-hosting requires 8× A100 80GB. V4-Flash variant runs within 1.6 points of V4-Pro at one-fifth the active parameters.
    
     
    
     
     ◆ Alibaba
    
     Qwen 3.6 family
    
     73.4% SWE-bench · 86.0% GPQA · 1M token context
    
     Multiple sizes from 2B to 397B (with A17B MoE). Qwen 3.6-35B-A3B is the strongest open-weight model that runs on a single RTX 4090. Apache 2.0 license. Strong agentic tool use across long sessions. Most practical Chinese option for solo developers.
    
     
    
     
     ◆ Z.AI (Beijing)
    
     GLM-5 / GLM-5.1
    
     83 BenchLM · 58.4% SWE-bench Pro (open-weight leader) · 95.3% AIME
    
     Currently the strongest open-source coding model on the SWE-bench Pro benchmark. MIT-licensed. Strong on Chinese-language tasks. Z.AI has emerged from a research lab background into a competitive frontier vendor over the past year.
    
     
    
     
     ◆ Moonshot AI
    
     Kimi K2.6
    
     84 BenchLM · 90.5% GPQA Diamond (open-weight leader)
    
     Currently the highest-scoring open-weight model on GPQA Diamond — the most discriminating reasoning benchmark at the frontier. Strong on long-context tasks. Open weights with usage-permissive licensing. Underrated outside China.
    
     
    
    
    
    
     The structural change is not that any single Chinese model has overtaken closed-frontier alternatives — it hasn’t. DeepSeek V4 Pro Max scores 87 on BenchLM versus Gemini 3.1 Pro at 93 and GPT-5.4 at 88; the gap to the very top remains real. The structural change is that Chinese labs now ship four genuinely frontier-competitive open-weight families with permissive licensing — versus essentially one or two a year ago — and they are doing it at compute costs that Western labs are struggling to match. DeepSeek’s training-efficiency claims (originally controversial, now broadly validated) and Qwen’s MoE deployment economics have shifted what is achievable per dollar of GPU spend. Western labs, including Google, have been forced to respond.
    
    
     
     Strategic context 
     The Chinese open-source ecosystem benefits from a deliberate strategic choice by major Chinese AI labs: ship weights openly, build the global developer base, capture mindshare in markets where data sovereignty makes US APIs unappealing. DeepSeek V4, Qwen, GLM, and Kimi all ship with MIT or Apache 2.0 licensing — license terms that exceed the permissiveness of pre-Gemma-4 Western releases. This is not accidental. It is industrial strategy meeting AI infrastructure, executed with sufficient capability to matter.
    
    
    
    
     Gemma 4 vs Claude vs GPT vs DeepSeek: how to choose 
     
     Short answer: The “either/or” question is the wrong question. The right approach in 2026 is hybrid routing: 60-70% of traffic through self-hosted open models (Gemma 4 31B or DeepSeek V4 Flash), 25% through mid-tier closed APIs (Claude Sonnet 4.6), and 5% through frontier closed models (Claude Opus 4.7 or GPT-5.5) for the hardest problems. This achieves cost reductions of 70%+ with minimal quality loss on most production workloads.
    
    
     
     
     
     
       
     Gemma 4 31B 
     DeepSeek V4 
     Claude Opus 4.7 
     GPT-5.5 
    
    
     
     
     
     Type 
     Open weight 
     Open weight 
     Closed API 
     Closed API 
    
    
     
     License 
     Apache 2.0 
     MIT 
     Commercial only 
     Commercial only 
    
    
     
     Context 
     256K 
     1M 
     200K / 1M beta 
     256K 
    
    
     
     Best at 
     Math, reasoning, vision, on-device 
     Coding at frontier scale 
     Production coding, code review 
     Agentic work, computer use 
    
    
     
     Hardware 
     Single GPU 
     8× A100 minimum 
     Hosted 
     Hosted 
    
    
     
     Cost to run 
     ~$0.10–$0.50/M tokens 
     ~$0.30–$1/M tokens 
     $5 / $25 per M 
     $5 / $30 per M 
    
    
     
     Data sovereignty 
     Full (self-hosted) 
     Full (self-hosted) 
     API exposure 
     API exposure 
    
    
     
     
    
    
    
     
     The hybrid routing architecture
    
     The cost-optimal default for production AI workloads in May 2026
    
    
     
     
     60-70%
    
     Self-hosted open
    
     Gemma 4 31B or DeepSeek V4-Flash. Routine queries, summarization, simple coding, general assistant work. Cost: ~$0.20/M tokens self-hosted.
    
     
    
     
     25%
    
     Closed mid-tier
    
     Claude Sonnet 4.6 or Gemini 3.1 Flash. Production coding, agentic loops, nuanced reasoning. Cost: ~$3/$15 per M tokens.
    
     
    
     
     5%
    
     Closed frontier
    
     Claude Opus 4.7 or GPT-5.5. Hardest debugging, code review, security work, multi-hour agent tasks. Cost: ~$5/$25-30 per M tokens.
    
     
    
     
    
    
    
    
     The routing math is what makes the open-source story compelling at the organizational level — not the individual benchmark wins. A single AI-powered application routing 70% of traffic through Gemma 4 31B (self-hosted at ~$0.20 per million tokens of cost-amortized compute), 25% through Claude Sonnet 4.6 ($3/$15), and 5% through Claude Opus 4.7 ($5/$25) achieves overall response quality indistinguishable from routing everything to a frontier model, at roughly 25-30% of the cost. That is the deployment pattern that has emerged in serious production AI teams over the past six months. Gemma 4 makes it more attractive by raising the quality floor of the “60-70%” tier without changing the routing architecture.
    
    
     
     The cost reset
    
     ~70% savings 
     Achievable cost reduction on production AI workloads via hybrid routing — self-hosted open models for routine traffic, closed-frontier APIs only for the hardest 5% of queries. The math has improved materially with Gemma 4’s release.
    
    
    
    
     What it means for developers 
     
     Short answer: Gemma 4 raises the floor for what individual developers can build without API dependencies. The E2B and E4B variants enable serious on-device AI applications that work offline. The 26B A4B MoE runs on a workstation GPU. Apache 2.0 removes the legal hesitation that constrained product decisions on prior Gemma generations. For developers building products that need data sovereignty, offline capability, or sustainable cost economics at scale, the calculus has shifted decisively toward self-hosted open models.
    
    
     Three practical shifts deserve attention. First, on-device AI is now a viable product category. Gemma 4’s E2B and E4B variants run completely offline on hardware most consumers already own. For mobile developers, this means AI features that don’t depend on a backend API, don’t leak user data, don’t fail in low-connectivity environments, and don’t add per-user cost. The implications for healthcare, education, finance, and any sector with privacy requirements are substantial — full conversational AI inside an app, with no data leaving the device, was a research project six months ago. It is now a deployable feature.
    
    
     Second, fine-tuning has become a competitive advantage. Under Apache 2.0, organizations can fine-tune Gemma 4 on proprietary data, redistribute the result, and embed it in commercial products without ongoing license obligations to Google. This is the cleanest legal posture any major Western lab has offered, and it changes the strategic question from “should we fine-tune?” to “what proprietary capability do we have that fine-tuning would surface?” Domain-specific fine-tunes — legal, medical, financial, scientific — become more attractive when the resulting model is yours to deploy without ongoing constraint.
    
    
     Third, the developer toolchain has matured around open weights. Hosted serving via Together AI, Fireworks, Groq, and Replicate is now production-grade. Local serving via Ollama, vLLM, and llama.cpp is robust enough for actual deployments. Fine-tuning tools — Axolotl, Unsloth, and Hugging Face’s TRL — are stable. The infrastructure friction that made open weights feel like a research path rather than a production path through 2024 is largely gone. For solo developers and small teams, Gemma 4 plus Ollama plus a fine-tuning pipeline is a complete stack.
    
    
     What it means for organizations and tech leaders 
     
     Short answer: The strategic question for CTOs has shifted from “which closed-frontier API should we standardize on?” to “what’s our hybrid stack and how does open-source fit into it?” Organizations that have not already evaluated self-hosted open models for at least their routine AI workloads are now over-paying. Data sovereignty considerations make this especially urgent for European organizations, regulated industries, and any enterprise with data residency requirements. Gemma 4’s Apache 2.0 license and Chinese open models’ MIT licensing have removed the legal friction that was the last credible argument against self-hosting.
    
    
     The CTO conversation has changed materially since the start of 2026. A year ago, the default architectural decision for an enterprise AI deployment was “standardize on Claude or GPT, accept the vendor lock-in for the capability.” That decision still makes sense for the hardest 5-10% of workloads, where frontier capability and reliability matter more than cost or governance. But for the other 90%, the architectural conversation now includes self-hosted open models as a serious option — not as a research project, but as a primary production tier. The shift in tooling, model quality, and licensing has been incremental quarter-by-quarter, but the cumulative effect is decisive.
    
    
     For organizations with data sovereignty requirements , the change is more than economic. European regulators, particularly in financial services and healthcare, have grown progressively less comfortable with US-hosted closed-frontier APIs handling sensitive customer data. The GDPR-aligned approach increasingly requires either US-cloud-region-locked deployment with specific contractual commitments, or fully self-hosted inference. Gemma 4 (Apache 2.0) and the Chinese open models (MIT, mostly) make the second option genuinely viable. For organizations in regulated sectors that have been operating closed-API AI under tight governance constraints, this opens up deployment patterns that were previously infeasible.
    
    
     
     Strategic shift 
     The “build on Anthropic vs OpenAI” question has been quietly replaced by “build on a hybrid stack.” The teams making the best AI-product decisions in 2026 are running Gemma 4 or DeepSeek V4 for the bulk of their workload, Claude Sonnet 4.6 for mid-tier work, Claude Opus 4.7 or GPT-5.5 for the hardest tasks, and treating each tier as commodity-with-fallback. The era of single-vendor AI strategy is functionally over for production deployments.
    
    
    
    
     What it means for the global AI economy 
     
     Short answer: The release of Gemma 4 under Apache 2.0 — combined with the Chinese open-source surge — has structurally shifted the AI value chain. Closed-frontier model providers (Anthropic, OpenAI) face increasing margin pressure on routine workloads. Open-source infrastructure providers (Together AI, Fireworks, Groq, sovereign cloud operators) gain. National AI strategies pivot toward “open-weight + national infrastructure” patterns. The geopolitical AI race is no longer just about who has the best frontier model — it is about who controls the deployment infrastructure and the open-source ecosystem that the long tail of applications will run on.
    
    
     
     
     For developers
    
     The build-vs-buy line moved
    
     
     On-device AI is now a viable product category — not a research path
    
     Fine-tuning under Apache 2.0 produces fully owned, redistributable models
    
     The Ollama/vLLM/llama.cpp stack is production-grade
    
     Solo developers can ship serious AI products without API dependencies
    
     Data privacy becomes a product feature, not a compliance overhead
    
     Multiple competitive choices — Gemma 4, Qwen 3.6, DeepSeek V4 — beat lock-in
    
     
     
    
     
     For organizations
    
     Hybrid stack is the new default
    
     
     70%+ cost reduction achievable via intelligent routing
    
     Data sovereignty deployment patterns now genuinely viable
    
     Regulated-industry AI deployments unblocked at scale
    
     Single-vendor AI strategy is functionally retired for production
    
     Internal AI infrastructure becomes a strategic capability
    
     Model evaluation discipline now matters more than vendor selection
    
     
     
    
     
     For the AI economy
    
     Multipolar, infrastructure-led
    
     
     Closed-frontier model providers face margin pressure on routine workloads
    
     Inference-infrastructure providers (Together, Fireworks, Groq) gain
    
     National AI strategies pivot to “open-weight + national infrastructure”
    
     European digital sovereignty efforts find a credible technical foundation
    
     Chinese open-source surge resets US lab competitive positioning
    
     The geopolitical AI race shifts from “best frontier model” to “best ecosystem”
    
     
     
    
    
    
    
     The competition from China — strategic implications 
     
     Short answer: The Chinese open-source surge has three structural implications. First, Western labs can no longer rely on “we ship open weights” as a competitive moat — DeepSeek, Qwen, GLM, and Kimi all do too, with more permissive licensing. Second, the cost-efficiency of Chinese training (validated by DeepSeek V3’s reported $5.6M training run) puts pressure on Western lab compute economics. Third, the global developer ecosystem — particularly outside the US — increasingly defaults to Chinese open models for cost-sensitive workloads. The competition is real, structural, and likely to intensify through 2026.
    
    
     The strategic dynamic worth understanding is that Chinese open-source AI is not primarily an export effort — it is a domestic capability play with global side effects. Chinese labs ship open weights partly to attract international developer mindshare, partly to bypass export controls on closed Chinese AI services, partly to demonstrate technical capability in international forums where US labs dominate, and partly because the domestic Chinese cloud and enterprise market is structured around self-hosted deployment to a degree US markets are not. The result is that Chinese AI labs have stronger incentives to ship open weights than US labs do — and their open weights are increasingly used by global developers because they are genuinely good.
    
    
     For US-aligned organizations, the practical implications are mixed. Chinese open models like DeepSeek V4 and Qwen are technically excellent, but using them in production raises governance questions — about training data provenance, about embedded refusals or biases related to Chinese political topics, about export-control compliance for organizations subject to sensitive-technology restrictions, and about the precedent of building AI products on infrastructure from a strategic competitor. None of these concerns disqualify Chinese open models for general use. All of them mean organizations should make conscious decisions rather than defaulting to whichever open model has the best benchmark score. Gemma 4’s release gives US-aligned organizations a strong Western alternative for the first time in the post-Llama 3 era.
    
    
     
     The Chinese open-source surge has reset the global AI map. The question for Western labs is no longer “can we compete with closed Chinese AI” — it is “can we compete with open Chinese AI, on permissive licensing, at training-cost economics we’re still figuring out how to match?”
     — The AI & Tech Society Editorial View 
    
    
    
     Final take 
     
     Short answer: Gemma 4 is the most consequential open-source AI release of 2026 so far — not because it dominates the benchmarks, but because it gives Western developers and organizations a credible Apache 2.0 alternative to a Chinese-led open-source ecosystem that had become genuinely dominant. The combination of Gemma 4, DeepSeek V4, Qwen 3.6, GLM-5.1, and Kimi K2.6 means production AI deployments now have real choice. The era of “use Claude or use GPT” is over for serious teams. The hybrid stack is the new default. Cost economics, data sovereignty, and customization flexibility now favor open weights for the majority of workloads.
    
    
     The way I would summarize this release: Gemma 4 doesn’t end the closed-frontier AI economy — it changes its center of gravity. Anthropic and OpenAI will continue to lead on the hardest 5-10% of workloads where frontier capability matters more than cost. But for the other 90% — the routine queries, the summarization, the lightweight coding, the on-device features, the regulated-industry deployments — open weights have become genuinely competitive, and the legal friction that previously made organizations default to closed APIs has materially decreased. Combined with the Chinese surge, this means the global open-source AI ecosystem now has Western and Eastern poles, each shipping multiple frontier-competitive families, all under permissive licenses. That is a different industry structure than existed twelve months ago.
    
    
     For developers and organizations, the practical implication is clear: evaluate Gemma 4 (and Qwen 3.6, DeepSeek V4, GLM-5.1) for at least the routine portion of your AI workload . If you haven’t already, this is the quarter to do it. The hybrid stack has become the right answer for most production deployments. The teams that internalize this shift early will build sustainable cost economics into their AI products; the teams that wait will continue paying premium API rates for capability they don’t actually need. The era of single-vendor AI strategy is functionally over. The era of multipolar, multi-vendor, hybrid-deployment AI has begun.
    
    
     
    
    
    
     

---

### 7. DeepSeek V4 MI300X: Unleashing Flash Performance on AMD Instinct GPUs

- **Author:** Avicrown TechBlog — byline resolves to a person: **no**
- **Site:** Avicrown Tech Solutions (`avicrowntechsolutions.com`) · 191 posts, 0.12/day, 2 bylines sampled
- **Site describes itself as:** Affordable, Scalable Cloud Management for Growing Tech Startups.
- **Date:** 2026-08-04 · 3,383 words · 0 comments · 0 likes
- **Tags:** AI Hardware, AMD MI300X, DeepSeek V4 Flash, GPU Inference, LLM Optimization, ROCm, deep learning, vLLM · **Categories:** AI in IT Operations
- **URL:** http://avicrowntechsolutions.com/2026/08/04/deepseek-v4-mi300x-optimize-flash-performance/
- **Type:** news summary · **Provenance:** unattributed
- **Artifacts: 4** — `bench_number`×2, `code_fence`×4, `conditioned_comparison`×3, `version_string`×5
- **Benchmark figures:** 2 mentions, 0 attributed near the number

     Unleashing unparalleled speed and efficiency with DeepSeek V4 MI300X on AMD Instinct GPUs. 
     DeepSeek V4 MI300X: Unleashing Flash Performance on AMD Instinct GPUs 
     The Dawn of AI Acceleration: DeepSeek V4 Flash on AMD MI300X 
     The landscape of large language models (LLMs) is rapidly evolving. Enterprises are constantly seeking more efficient and cost-effective ways to deploy powerful AI. This drive often leads to exploring alternative hardware platforms. For instance, the combination of **DeepSeek V4 MI300X** is gaining significant traction. This pairing promises to deliver exceptional performance for demanding AI workloads. It offers a compelling alternative to traditional GPU setups. Organizations can now achieve impressive inference speeds and training capabilities with **DeepSeek V4 MI300X**. This is particularly true for models like DeepSeek V4 Flash. The ability to run these models on AMD Instinct GPUs marks a new era. It highlights the growing versatility of AI hardware, especially with **DeepSeek V4 MI300X**.
    
     The emergence of AMD’s MI300X accelerators is a game-changer. These GPUs provide substantial High Bandwidth Memory (HBM). This is crucial for handling large models. DeepSeek V4 Flash, known for its efficiency, benefits greatly from this. Its architecture is optimized for fast inference. Therefore, pairing it with high-capacity memory GPUs is ideal for **DeepSeek V4 MI300X**. This synergy allows for larger batch sizes and reduced latency. Ultimately, this translates to superior performance for **DeepSeek V4 MI300X**. It also offers a more economical solution for AI infrastructure. Many IT managers are now evaluating this powerful combination. They are looking for ways to maximize their AI investments with **DeepSeek V4 MI300X**.
    
     TL;DR: Running DeepSeek V4 Flash on AMD MI300X for Optimal Performance 
     Running DeepSeek V4 Flash on AMD MI300X GPUs provides a powerful, cost-effective solution for LLM inference. Leverage the ROCm ecosystem and vLLM framework for seamless deployment and high throughput with **DeepSeek V4 MI300X**. Overcome initial compatibility hurdles through community-driven optimizations and specific environment configurations for **DeepSeek V4 MI300X**. Expect competitive performance against NVIDIA alternatives, especially regarding HBM capacity and price-performance with **DeepSeek V4 MI300X**. This setup is ideal for enterprises seeking efficient, scalable AI deployments with **DeepSeek V4 MI300X**.
    
     Introduction: Why DeepSeek V4 Flash and AMD MI300X are a Game-Changer 
     The demand for high-performance, cost-efficient AI inference is escalating across industries. Large Language Models (LLMs) are at the forefront of this revolution. However, deploying them at scale requires robust hardware. It also demands optimized software stacks. DeepSeek V4 Flash stands out as an LLM designed for speed and efficiency. It offers a balance of intelligence and rapid inference. This makes it highly attractive for enterprise applications, especially when considering **DeepSeek V4 MI300X**. From customer service bots to advanced data analysis, its potential is vast with **DeepSeek V4 MI300X**.
    
     On the hardware front, AMD’s MI300X Instinct GPUs are emerging as a formidable contender. They challenge the established dominance of other GPU manufacturers. The MI300X boasts impressive HBM capacity. This is critical for loading and processing large AI models. Its compute capabilities are also highly competitive. This combination of DeepSeek V4 Flash and AMD MI300X represents a significant shift. It offers a powerful new option for IT managers and DevOps leads. They can now explore more diverse and potentially more economical AI infrastructure choices with **DeepSeek V4 MI300X**. This pairing promises to unlock new levels of performance. It also enhances the accessibility of advanced AI with **DeepSeek V4 MI300X**.
    
     The Challenge: Bridging DeepSeek V4 Flash with AMD’s ROCm Ecosystem for DeepSeek V4 MI300X 
     Integrating cutting-edge LLMs like DeepSeek V4 Flash with AMD’s hardware presents unique challenges. The primary hurdle often lies in software compatibility. NVIDIA’s CUDA ecosystem has long been the de facto standard for deep learning. This means many models and frameworks are initially optimized for it. AMD, however, offers ROCm (Radeon Open Compute platform). ROCm is its open-source software platform for GPU computing. Bridging these two ecosystems requires careful attention for **DeepSeek V4 MI300X**. It involves specific configurations and sometimes custom development to enable **DeepSeek V4 MI300X**.
    
     Early discussions on platforms like Hugging Face highlighted these compatibility concerns for **DeepSeek V4 MI300X**. Users asked, “Can we deploy on AMD Mi300x GPU?” This question underscores the initial uncertainty. The community quickly rallied to address these issues. Developers and engineers began sharing their experiences. They documented successful workarounds and optimization strategies for **DeepSeek V4 MI300X**. Fergus Finn’s blog post, “Bringing up DeepSeek-V4-Flash on AMD MI300X,” became a valuable resource. It detailed the necessary steps and configurations for **DeepSeek V4 MI300X**. This collective effort is vital. It helps to ensure that AMD’s powerful hardware can fully support leading LLMs. The goal is to achieve seamless and efficient operation for **DeepSeek V4 MI300X**.
    
     Step-by-Step Guide: Deploying and Optimizing DeepSeek V4 Flash on MI300X 
     Deploying DeepSeek V4 Flash on an AMD MI300X system requires a methodical approach. The process involves setting up the correct software environment. It also includes optimizing for performance. This guide will walk you through the essential steps. You will be able to get your LLM running efficiently with **DeepSeek V4 MI300X**.
    
     1. Setting Up the ROCm Environment for DeepSeek V4 MI300X 
     First, ensure your AMD MI300X system has a properly installed ROCm stack. This is the foundation for all GPU computations. You should use a recent version of ROCm. This will ensure compatibility with the latest deep learning frameworks. Verify the installation by running `rocminfo` and `rocm-smi`. These commands will display your GPU and ROCm details. A stable ROCm environment is critical for success with **DeepSeek V4 MI300X**.
    
     2. Installing vLLM with ROCm Support for DeepSeek V4 MI300X 
     vLLM is a highly efficient inference engine for LLMs. It offers continuous batching and PagedAttention. These features significantly boost throughput for **DeepSeek V4 MI300X**. You must install a version of vLLM compiled with ROCm support. This might involve building from source. Alternatively, you can use pre-built containers. Many community efforts, such as those discussed on Reddit, focus on this. They provide guidance for bringing up DeepSeek-V4-Flash on AMD MI300X. This ensures optimal performance for **DeepSeek V4 MI300X**.
    
    
    ```
    
    ```
    
    graph TD
     A[Start] --> B{Install ROCm};
     B --> C{Verify ROCm};
     C --> D{Install vLLM for ROCm};
     D --> E{Download DeepSeek V4 Flash Model};
     E --> F{Configure vLLM Server};
     F --> G{Run Inference};
     G --> H[End];
    
    ```
    
    ```
    
     3. Downloading the DeepSeek V4 Flash Model for DeepSeek V4 MI300X 
     Obtain the DeepSeek V4 Flash model weights. You can typically find these on Hugging Face. Ensure you download the correct version for **DeepSeek V4 MI300X**. Check for any specific quantization requirements. These can impact both performance and memory usage for **DeepSeek V4 MI300X**. For example, a discussion on Hugging Face addresses deploying DeepSeek-V4-Pro on AMD MI300X. This highlights the importance of model versioning for **DeepSeek V4 MI300X**.
    
     4. Configuring and Running vLLM for DeepSeek V4 MI300X 
     Now, configure vLLM to load DeepSeek V4 Flash. Specify the model path and any necessary parameters for **DeepSeek V4 MI300X**. These parameters include tensor parallelism and data types. You will likely use the `vllm.LLM` class. This class helps to initialize the model for **DeepSeek V4 MI300X**. Then, start the vLLM server. This server will expose an API for inference requests for **DeepSeek V4 MI300X**.
    
     5. Optimization Checklist for DeepSeek V4 Flash on MI300X: 
     
     **ROCm Version**: Use the latest stable ROCm release for best compatibility with **DeepSeek V4 MI300X**.
    
     **vLLM Build**: Ensure vLLM is specifically built with ROCm support for **DeepSeek V4 MI300X**.
    
     **HBM Utilization**: Monitor HBM usage to avoid out-of-memory errors for **DeepSeek V4 MI300X**.
    
     **Batch Size**: Experiment with different batch sizes to find the optimal throughput for **DeepSeek V4 MI300X**.
    
     **Quantization**: Consider using 8-bit or 4-bit quantization if memory is a constraint for **DeepSeek V4 MI300X**.
    
     **Tensor Parallelism**: Utilize tensor parallelism across multiple MI300X GPUs if available for **DeepSeek V4 MI300X**.
    
     **Kernel Optimization**: Stay updated on vLLM and ROCm updates for new kernel optimizations for **DeepSeek V4 MI300X**.
    
     
     By following these steps, you can successfully deploy and optimize DeepSeek V4 Flash. This will allow it to run effectively on your AMD MI300X infrastructure. This setup provides a robust platform for your AI workloads with **DeepSeek V4 MI300X**.
    
     Real-World Impact: DeepSeek V4 Flash in Action on AMD Instinct 
     The deployment of DeepSeek V4 Flash on AMD Instinct GPUs is having a tangible impact across various enterprise scenarios. This powerful combination offers significant advantages. It addresses critical needs in AI infrastructure. Organizations are leveraging this setup for diverse applications with **DeepSeek V4 MI300X**.
    
     Enhanced Customer Support with DeepSeek V4 MI300X 
     Many companies are integrating DeepSeek V4 Flash into their customer service operations. The model’s rapid inference capabilities mean quicker response times for AI chatbots. On AMD MI300X, these chatbots can handle a higher volume of concurrent queries. This leads to improved customer satisfaction. It also reduces the workload on human agents. The high HBM capacity of the MI300X allows for larger context windows. This helps the AI understand complex customer issues better with **DeepSeek V4 MI300X**.
    
     Accelerated Research and Development with DeepSeek V4 MI300X 
     Research institutions and R&D departments are benefiting from the speed of DeepSeek V4 Flash on MI300X. Scientists can iterate faster on experiments involving natural language processing. This accelerates the discovery process. For example, drug discovery pipelines often involve analyzing vast amounts of text data. The efficient processing power of AMD Instinct GPUs significantly shortens these cycles. This allows researchers to focus more on insights with **DeepSeek V4 MI300X**.
    
     Cost-Effective Cloud Deployments for DeepSeek V4 MI300X 
     Cloud providers and enterprises are exploring AMD MI300X for cost-effective LLM hosting. The competitive price-performance ratio of AMD hardware makes it attractive. Deploying DeepSeek V4 Flash on these GPUs reduces operational expenses. This is especially true for large-scale inference services. Companies can achieve similar performance to more expensive alternatives. This helps to democratize access to advanced AI capabilities with **DeepSeek V4 MI300X**. For more insights into cost-efficiency, consider reading about DeepSeek V4 Flash Review: Unpacking Enterprise AI Intelligence & Cost-Efficiency . This review further emphasizes the benefits of **DeepSeek V4 MI300X**.
    
     Secure Local AI Workloads with DeepSeek V4 MI300X 
     For organizations with stringent security requirements, local deployment is crucial. Running DeepSeek V4 Flash on on-premise AMD MI300X systems ensures data privacy. This setup avoids transmitting sensitive information to external cloud services. It provides complete control over the AI environment. This is particularly important for sectors like finance and healthcare. They must comply with strict regulatory standards. The robust performance of the MI300X supports these secure, local operations for **DeepSeek V4 MI300X**.
    
     Performance Showdown: DeepSeek V4 Flash on MI300X vs. NVIDIA H100 
     When evaluating AI hardware, a direct comparison of performance is essential. The AMD MI300X is often pitted against NVIDIA’s H100 GPU. Both are high-performance accelerators. However, they cater to slightly different niches and offer distinct advantages. For DeepSeek V4 Flash inference, the MI300X presents a compelling case. It particularly shines in scenarios demanding high HBM capacity for **DeepSeek V4 MI300X**.
    
     The “Bringing up DeepSeek-V4-Flash on AMD MI300X” discussions on Hacker News and Reddit highlight this comparison. Early adopters are actively benchmarking their setups. They are sharing their findings with the community. These real-world tests provide valuable data. They help IT managers make informed decisions regarding **DeepSeek V4 MI300X**. The MI300X typically offers a higher HBM capacity per GPU. This can be a significant advantage for larger models. It allows for bigger batch sizes. This, in turn, can lead to higher overall throughput for **DeepSeek V4 MI300X**.
    
     
     DeepSeek V4 Flash Inference Performance Comparison (Illustrative) 
     
     
     Feature/Metric 
     AMD MI300X 
     NVIDIA H100 
    
    
     
     
     
     HBM Capacity 
     192GB (per GPU) 
     80GB (per GPU) 
    
    
     
     Typical Throughput (Tokens/sec) 
     Competitive, often higher with large batches for **DeepSeek V4 MI300X** 
     Very High, especially with optimized CUDA kernels 
    
    
     
     Price-Performance 
     Often superior due to lower acquisition cost for **DeepSeek V4 MI300X** 
     High performance, but at a premium price point 
    
    
     
     Software Ecosystem 
     ROCm (open-source, growing support for **DeepSeek V4 MI300X**) 
     CUDA (mature, extensive libraries) 
    
    
     
     Energy Efficiency 
     Good, especially for HBM-bound workloads with **DeepSeek V4 MI300X** 
     Excellent, with highly optimized architecture 
    
    
     
     
     While the H100 often boasts raw compute power and a more mature software ecosystem, the MI300X is rapidly closing the gap. Its cost-effectiveness and substantial HBM make it an attractive alternative. For workloads that are memory-bound, the MI300X can even outperform. This is because it can load more of the model and process larger contexts. Ultimately, the choice depends on specific workload requirements. It also depends on budget constraints. However, the MI300X offers a strong argument for itself. It is a viable and powerful platform for DeepSeek V4 Flash, especially with **DeepSeek V4 MI300X**.
    
     Best Practices for Maximizing DeepSeek V4 Flash Performance on AMD MI300X 
     Achieving peak performance for DeepSeek V4 Flash on AMD MI300X requires adherence to several best practices. These strategies help to optimize both software and hardware utilization. They ensure your LLM deployment runs as efficiently as possible with **DeepSeek V4 MI300X**.
    
     
     **Keep ROCm Updated**: Regularly update your ROCm drivers and libraries. Newer versions often include performance enhancements and bug fixes. This ensures compatibility with the latest deep learning frameworks for **DeepSeek V4 MI300X**.
    
     **Optimize vLLM Configuration**: Fine-tune vLLM parameters. Experiment with `max_model_len`, `tensor_parallel_size`, and `dtype`. These settings significantly impact memory usage and throughput for **DeepSeek V4 MI300X**.
    
     **Monitor GPU Metrics Closely**: Use `rocm-smi` or other monitoring tools. Track GPU utilization, HBM usage, and temperature. Identify any bottlenecks or thermal throttling for **DeepSeek V4 MI300X**.
    
     **Leverage Quantization**: Explore model quantization (e.g., 8-bit or 4-bit inference). This reduces memory footprint. It can also improve inference speed with minimal accuracy loss for **DeepSeek V4 MI300X**.
    
     **Batching Strategies**: Implement continuous batching effectively. vLLM excels at this. It maximizes GPU utilization by processing multiple requests concurrently for **DeepSeek V4 MI300X**.
    
     **Profile Your Workload**: Use profiling tools to identify hot spots in your code. Optimize custom kernels or data loading pipelines. This helps to pinpoint areas for improvement for **DeepSeek V4 MI300X**.
    
     **Community Engagement**: Participate in forums and discussions. The AMD MI300X community is growing. Sharing experiences and learning from others is invaluable for **DeepSeek V4 MI300X**.
    
     
     By systematically applying these best practices, you can unlock the full potential of DeepSeek V4 Flash. This will allow it to run on your AMD MI300X infrastructure. This proactive approach ensures a robust and high-performing AI system with **DeepSeek V4 MI300X**.
    
     Common Pitfalls: Avoiding Performance Bottlenecks with DeepSeek V4 Flash on DeepSeek V4 MI300X 
     Even with robust hardware like the AMD MI300X, certain pitfalls can hinder DeepSeek V4 Flash performance. Recognizing and avoiding these common mistakes is crucial. It helps to maintain optimal efficiency and throughput for **DeepSeek V4 MI300X**.
    
     
     **Outdated ROCm Drivers**: Running an older version of ROCm can lead to compatibility issues. It can also result in missed performance optimizations. Always ensure your ROCm stack is current for **DeepSeek V4 MI300X**.
    
     **Suboptimal vLLM Configuration**: Incorrectly configured vLLM parameters are a frequent bottleneck. Forgetting to set `tensor_parallel_size` for multi-GPU setups is common. This prevents full utilization of your hardware for **DeepSeek V4 MI300X**.
    
     **HBM Overload**: Attempting to load a model or process a batch size that exceeds the MI300X’s HBM capacity will lead to errors. It can also cause severe performance degradation. Monitor HBM usage carefully for **DeepSeek V4 MI300X**.
    
     **Inefficient Data Loading**: Slow data loading or preprocessing can starve the GPU. This leaves valuable compute resources idle. Optimize your data pipelines for **DeepSeek V4 MI300X**.
    
     **Lack of Quantization**: Running models in full precision (FP16 or FP32) when lower precision (INT8, INT4) is sufficient wastes HBM and compute. Explore quantization options for **DeepSeek V4 MI300X**.
    
     **Ignoring Community Resources**: Many common issues have already been solved by the community. Failing to consult forums like Reddit or Hacker News can lead to wasted effort. Check “Bringing up DeepSeek-V4-Flash on AMD MI300X” discussions for insights on **DeepSeek V4 MI300X**.
    
     **Security Oversights**: While focusing on performance, do not neglect security. Unsecured LLM deployments can expose sensitive data. Consider best practices for AI security, such as those covered in Google Beyond Zero Security: Enterprise Protection for the AI Era . This is critical for any **DeepSeek V4 MI300X** deployment.
    
     
     By proactively addressing these potential issues, you can ensure a smoother and more efficient DeepSeek V4 Flash deployment. This will maximize the return on your AMD MI300X investment with **DeepSeek V4 MI300X**.
    
     Expert Insights: Future-Proofing Your LLM Deployments on AMD MI300X 
     The rapid pace of AI development necessitates a forward-looking strategy for LLM deployments. Experts in the field emphasize adaptability and open standards. This is particularly true when working with platforms like AMD MI300X. The ecosystem is evolving quickly. Therefore, staying agile is key. The future of LLMs on AMD hardware looks promising. Continuous improvements in ROCm and frameworks like vLLM are driving this progress for **DeepSeek V4 MI300X**.
    
     One critical insight is the importance of contributing to open-source projects. The community plays a vital role in enhancing ROCm support for various models. Engaging with these communities helps to accelerate development. It also provides early access to new features for **DeepSeek V4 MI300X**. Another crucial aspect is understanding the hardware roadmap. AMD is continually innovating its Instinct GPU line. For instance, the comparison of MI300X vs. MI325X from InferenceX highlights future performance gains. Keeping an eye on these advancements helps in planning future upgrades for **DeepSeek V4 MI300X**.
    
     Furthermore, integrating AI security from the ground up is non-negotiable. As LLMs become more pervasive, their attack surface expands. Understanding potential vulnerabilities, such as those discussed in LLM SQLite Vulnerabilities: Unpacking Hallucinated Database Flaws & AI Security Risks , is essential. Robust security practices ensure the integrity and privacy of your AI systems, especially for **DeepSeek V4 MI300X**. Finally, consider the long-term cost implications. AMD’s competitive pricing for its high-performance GPUs makes it an attractive option. This helps to future-proof your AI budget. It also allows for scalability without prohibitive costs for **DeepSeek V4 MI300X**.
    
     FAQs: Your DeepSeek V4 Flash & MI300X Questions Answered 
     
     Q: What is DeepSeek V4 Flash? 
     A: DeepSeek V4 Flash is a large language model designed for efficient inference and training, often noted for its performance characteristics, especially when paired with **DeepSeek V4 MI300X**. 
     Q: What is the AMD MI300X? 
     A: The AMD MI300X is a high-performance accelerator designed for AI and HPC workloads, featuring significant HBM capacity and compute power, ideal for **DeepSeek V4 MI300X**. 
     Q: Can DeepSeek V4 Flash run on AMD MI300X? 
     A: While initial compatibility issues existed, ongoing development and community efforts are enabling DeepSeek V4 Flash to run on AMD MI300X, often leveraging frameworks like vLLM and ROCm for **DeepSeek V4 MI300X**. 
     Q: What are the benefits of running LLMs on AMD MI300X? 
     A: The AMD MI300X offers a compelling alternative for LLM workloads due to its high HBM capacity and competitive pricing, making it attractive for cost-effective AI deployments with **DeepSeek V4 MI300X**. 
     Q: What is ROCm? 
     A: ROCm (Radeon Open Compute platform) is AMD’s open-source software platform for GPU computing, providing a foundation for developing and running high-performance applications on AMD GPUs, crucial for **DeepSeek V4 MI300X**. 
     Q: What is vLLM? 
     A: vLLM is a fast and efficient open-source library for LLM inference, known for its continuous batching and PagedAttention algorithms, which significantly improve throughput for **DeepSeek V4 MI300X**. 
     
     Conclusion: The Future is Bright for DeepSeek V4 Flash on AMD MI300X 
     The journey to effectively deploy DeepSeek V4 Flash on AMD MI300X GPUs has been marked by innovation and community collaboration. What started as a challenge in compatibility has evolved into a robust and highly performant solution. This powerful pairing offers enterprises a compelling alternative for their demanding AI workloads. The high HBM capacity of the MI300X, combined with the efficiency of DeepSeek V4 Flash, creates a formidable platform. It is capable of handling complex LLM inference and training tasks with **DeepSeek V4 MI300X**.
    
     The ongoing development within the ROCm ecosystem and the vLLM framework continues to enhance this synergy. This makes AMD Instinct GPUs an increasingly attractive option for **DeepSeek V4 MI300X**. IT managers, cloud admins, and DevOps leads can now confidently explore this path. They can achieve significant cost efficiencies without compromising on performance. The future holds even greater promise. As the software stack matures and hardware continues to advance, the capabilities of **DeepSeek V4 MI300X** will only grow. This represents a pivotal moment in the democratization of high-performance AI. Consider exploring local deployment options, similar to those discussed for Kimi K3 Local Deployment: Efficient Self-Hosting & OpenAI API Integration , to maximize control and efficiency with **DeepSeek V4 MI300X**.
    
     Ready to Optimize Your LLM Workloads? Get Started Today! 
     
    

---

### 8. The Model Name Stayed the Same, but the Operating Contract Changed: Reading DeepSeek V4 Pro GA

- **Author:** 이수형 — byline resolves to a person: **yes**
- **Site:** SHawn AI (`shawnaiintelligence.wordpress.com`) · 108 posts, 1.67/day, 1 bylines sampled
- **Site describes itself as:** AI tools, automation workflows, and agent systems for useful work and content businesses.
- **Date:** 2026-08-26 · 3,105 words · 1 comments · 0 likes
- **Tags:** AI Agents, API Operations, Context Caching, DeepSeek, English, Model Routing, Reasoning Effort, V4 Pro · **Categories:** AI Notes, English
- **URL:** https://shawnaiintelligence.wordpress.com/2026/08/26/deepseek-v4-pro-ga-agent-operations-en/
- **Type:** news summary · **Provenance:** somebody else's benchmark repeated
- **Artifacts: 4** — `code_fence`×50, `error_output`×3, `price`×3, `version_string`×16
- **Benchmark figures:** 0 mentions, 0 attributed near the number

     
     AI NOTES · EN ENGLISH EDITION 
    
     The Model Name Stayed the Same, but the Operating Contract Changed: Reading DeepSeek V4 Pro GA 
     DeepSeek released V4 Pro for general availability on August 13, 2026 while keeping its API alias unchanged. Reasoning effort, protocol behavior, price windows, cache isolation, and concurrency now need to be read together as one operating contract.
    
     
    
     
     
     KO · 한국어 / EN · English BILINGUAL PAIR 
    
     
     On August 13, 2026, DeepSeek moved DeepSeek-V4-Pro-0813 to general availability. The detail worth pausing on is not the phrase “stronger model.” It is the sentence stating that the API name callers already use, 
    ```
    deepseek-v4-pro
    ```
    , stays unchanged. When the caller-facing name is held fixed while the underlying model version, the default reasoning effort, the supported protocols, the price structure, and the cache-isolation rules all move at the same time, the job for whoever operates against that name is not “try the new model.” It is “re-read the operating contract that changed underneath it.” The conclusion of this article is direct: V4 Pro GA should be treated as an operations release rather than a performance announcement, and before it reaches production a team needs to bind an alias-version receipt, protocol smoke tests, cost-window routing, per-user cache isolation, and a Flash/Pro escalation rule into a single deployment gate. Skip any of these five and the same client code will start returning different costs and different failure modes than it did the day before, without a corresponding code change on your side.
    
     What GA actually changes 
     DeepSeek’s API documentation page “DeepSeek-V4-Pro GA Release” (August 13, 2026) announces the general availability of V4 Pro and states several things at once. It reports major agent-related upgrades. It confirms that both V4 Pro and V4 Flash support selectable low/high/max reasoning effort. It states native support for the OpenAI Responses API, optimized for Codex. It notes that app and web access run through Expert Mode, and that API model names remain unchanged. Finally, it previews a peak/off-peak pricing schedule effective August 16, 16:00 UTC, with off-peak prices set at 50% of peak.
    
     These five items are worth listing separately because each sits at a different operational layer. Agent capability and reasoning effort change what the model does. Responses API support changes which protocol a client speaks. Price windows change the bill for an otherwise identical request. If you check only one of these and assume the rest are unchanged from yesterday, you find out about the gap after deployment, not before. The phrase “major agent upgrades” in particular is a qualitative claim; the source text this article draws on does not expose benchmark methodology that would let an independent party verify the size of that improvement. So this article does not attempt to rule on how much stronger the model actually is. What can be established here is that the operating contract changed and how to handle that change — not a claim of benchmark superiority.
    
     It also helps to say why these five items get grouped under one word, “contract.” The word fits because each item is a promise that only holds if both the client and the server keep their side of it. Reasoning effort falls back to a server default unless the client specifies it. Tool-call state produces a server error unless the client returns it on the next request. Price windows apply whatever schedule the server has defined unless the client controls when the request actually fires. In other words, half of this contract lives in server-side documentation and the other half lives in client-side implementation. Reading the docs only fills in half; the rest has to be confirmed by testing real requests and real responses.
    
     The alias is fixed; the version moves 
     The “Models & Pricing” page identifies 
    ```
    deepseek-v4-pro
    ```
     as DeepSeek-V4-Pro-0813 and 
    ```
    deepseek-v4-flash
    ```
     as DeepSeek-V4-Flash-0731. The important part is that the string your client calls is pinned to 
    ```
    deepseek-v4-pro
    ```
    , while the trained snapshot that string actually resolves to is a dated release. That makes it a stable alias, not an immutable version. A request sent to that same name today can, after a future update, come back from a model with different weights and different default behavior.
    
     The operational consequence is concrete. A regression test cannot be considered passing just because “the model name is the same.” A deployment pipeline needs a step that reads whatever version field or response header the API exposes and logs which dated snapshot actually answered — a version receipt. Only with that receipt in place can you later trace exactly when an incident or a regression started, and which version switch caused it. Reading “the alias is unchanged” as “nothing changed” is the single most common misread this section is meant to prevent.
    
     Treating reasoning effort as a routing variable 
     According to the “Thinking Mode” documentation, thinking is enabled by default at high effort. OpenAI-format clients combine a 
    ```
    thinking
    ```
     on/off flag with a 
    ```
    reasoning_effort
    ```
     value of low/high/max; Anthropic-format clients set effort to none/low/high/max, where none disables thinking. While thinking mode is active, the server silently ignores temperature, top_p, presence_penalty, and frequency_penalty. Put together, this has two practical implications. First, reusing the same request body as before means that the moment the default reasoning effort shifts, response length and latency can shift with it, without any change on your end. Second, a pipeline that has been tuning output through sampling parameters needs to know that those adjustments are void once thinking mode is on.
    
     From an agent-operations standpoint, reasoning effort should not be treated as a “quality dial.” It should be treated as a routing variable. Short, deterministic tool calls should get low effort; multi-step planning tasks should get high effort; verification-critical final steps should get max effort — assigned explicitly per request type rather than left to whatever the default happens to be. If effort is never specified, every shift in DeepSeek’s own default propagates straight into your pipeline’s behavior. Seen this way, agent operations is not a one-time choice of “which model,” but a routing problem connecting Flash, Pro, reasoning effort, and verification gates.
    
     Agent operations are a routing problem that connects Flash, Pro, reasoning effort, and verification gates rather than a one-time model choice. 
     The tool-call and reasoning_content state contract 
     The “Thinking Mode” documentation also states that once a tool call has occurred, the API returns a 400 error unless 
    ```
    reasoning_content
    ```
     is passed back unchanged on the subsequent request. This is a state-management contract, and ignoring it breaks a multi-turn tool-call chain partway through. It is worth being explicit here about what this article is and is not recommending: this is not a suggestion to expose hidden reasoning content to end users or to log it for later inspection. Including 
    ```
    reasoning_content
    ```
     in the next request body is a technical requirement for passing state along — a separate question entirely from whether a human should read, store, or reproduce what that field contains.
    
     Teams wiring an agent framework directly into this API should treat the field as part of session state, and confirm that session storage or cache-invalidation logic never accidentally truncates it. Retry logic that reconstructs a request body from scratch is a common place for this field to go missing. If 400 errors show up intermittently in a tool-call loop, this dropped state is the first place to look.
    
     Protocol compatibility and silent mapping 
     DeepSeek supports several protocols side by side. The “Integrate with OpenCode” page instructs users running OpenCode 1.14.24 or later to select DeepSeek-V4-Pro. OpenCode is an agent client built for coding work, and this guidance signals that DeepSeek intends its models to sit behind existing agent and coding clients, not only its own interface. The “Integrate with Hermes Agent” page introduces Hermes as an open-source agent from Nous Research and walks through connecting it via the DeepSeek API base URL with the 
    ```
    deepseek-v4-pro
    ```
     model. Together, both pages are written on the assumption that DeepSeek serves as a backend for third-party agent clients, not just a standalone chat product.
    
     The page that deserves closer attention is “Using the Anthropic API” . The Anthropic-compatible base URL is 
    ```
    https://api.deepseek.com/anthropic
    ```
    , and unsupported model names can be mapped automatically to V4 Flash. Under Claude-style name mapping, Opus-prefixed names route to V4 Pro, and Haiku/Sonnet-prefixed names route to V4 Flash. There is a boundary that must hold here: this mapping is a compatibility convenience, and sending a Claude-shaped name is not evidence that an Anthropic Claude model actually executed the request. Images, documents, MCP tool use and results, code-execution tool results, and several other fields are unsupported or ignored inside this compatibility layer. Any team migrating a pipeline that routes by Claude-style names onto DeepSeek needs to separately verify that the name is accepted and that the request is actually processed in full — those are two different facts.
    
     The timing across documentation pages also deserves caution. The GA announcement and the pricing page both state that V4 Pro supports the Responses API, but some dedicated integration pages may have been written earlier and could still carry a “coming soon” note. Treat the dated GA and pricing pages as the later, authoritative statement, but before routing production traffic through any given protocol, run an endpoint-level smoke test regardless of what the documentation says. Assuming that every documentation page is synchronized with every other one is itself a risk.
    
     The one-million-token context and 384K output boundary 
     The “Models & Pricing” page states that both 
    ```
    deepseek-v4-pro
    ```
     and 
    ```
    deepseek-v4-flash
    ```
     support a 1M-token context and up to 384K tokens of output. It also lists JSON output, tool calls, the Responses API, the Anthropic API, prefix completion, and fill-in-the-middle (FIM), with FIM limited to non-thinking mode. These figures are API ceilings, not a guarantee that any given application can use the full ceiling in practice. Client-side context compaction, latency targets, memory budgets, and application-specific token budgets routinely cap the context and output an application can actually sustain well below 1M tokens and 384K tokens. Translating “1M-token context” directly into “our service can handle a 1M-token conversation” is not a safe step.
    
     The FIM restriction to non-thinking mode also has real consequences. Workloads that rely on FIM, such as code autocompletion, need reasoning effort explicitly turned off or lowered; leaving the default high-effort thinking mode in place, as discussed above, means FIM requests can be processed in a way the caller did not intend. Context ceilings, output ceilings, and the FIM constraint look like independent line items, but in practice they need to be reconciled inside the same request design.
    
     Peak/off-peak price arithmetic 
     The price change takes effect August 16, 16:00 UTC. Before that time, the documented Pro rates per 1M tokens are $0.003625 for a cache hit, $0.435 for a cache miss, and $0.87 for output. After the change, Pro off-peak rates are $0.022 cache hit, $0.66 cache miss, and $1.98 output; Pro peak rates are $0.044 cache hit, $1.32 cache miss, and $3.96 output. Peak hours are defined as 01:00–04:00 UTC and 06:00–10:00 UTC, and every other hour is off-peak. For readers working in Korea time, those two peak windows correspond to 10:00–13:00 KST and 15:00–19:00 KST, and all other hours are off-peak. It is worth stating plainly: these prices do not apply before August 16, 16:00 UTC. If you are reading this article before that moment, the off-peak and peak figures above are scheduled, not current.
    
     The same V4 Pro workload can have a different cost structure depending on cache use, output volume, and execution window. 
     To see what the change actually means, run the arithmetic. Take a hypothetical batch workload of 100M cache-miss input tokens and 20M output tokens. The pre-change Pro bill is 
    ```
    100 × $0.435 + 20 × $0.87 = $60.90
    ```
    . The new off-peak bill is 
    ```
    100 × $0.66 + 20 × $1.98 = $105.60
    ```
    . The new peak bill is 
    ```
    100 × $1.32 + 20 × $3.96 = $211.20
    ```
    . Off-peak is exactly half of peak after the change, but for this workload it is roughly 73.4% more expensive than the old rate; the new peak rate is roughly 246.8% more expensive than the old rate. These numbers push back against reading the schedule as “shift to off-peak and get a discount.” Off-peak is half of the new peak price — not half of the old price. The higher a batch workload’s cache-miss share, the more directly this difference shows up on the invoice. Before treating time-of-day routing as a cost-saving lever, run your own cache-hit rate and traffic time distribution through this same arithmetic.
    
     Concurrency and user isolation 
     The “Rate Limit & Isolation” documentation states account-level concurrency limits of 500 for Pro and 2,500 for Flash, with excess requests returning HTTP 429. These numbers are ceilings on how many requests an account can have in flight simultaneously — not a guarantee of a specific throughput and not a service-level agreement. Reading 500 as “500 requests per second, always” is a misreading that only gets corrected the first time a real load spike returns 429s.
    
     The same page describes the 
    ```
    user_id
    ```
     parameter as supporting content-safety, KV-cache, and scheduling isolation. 
    ```
    user_id
    ```
     must match 
    ```
    [a-zA-Z0-9\-_]+
    ```
    , stay under 512 characters, and must not carry private information. Any multi-tenant service needs to populate this value consistently, one value per actual end user, for cache isolation and content-safety judgments to separate correctly by user. Leaving it blank, or pinning it at the application level instead of the user level, risks mixing different users’ requests into the same cache and scheduling bucket. It’s also worth noting for pipeline design that requests may receive empty-line or SSE-style keep-alive signals, and that the server closes any request that has not started inference within ten minutes — a detail that matters for timeout design in batch and agent pipelines with long queue waits.
    
     A production decision framework 
     Pulling the conditions above into one deployment judgment produces a specific order of operations. Before sending traffic, log the version identifier carried in the response so you know which snapshot actually answered. Next, run endpoint-level smoke tests against each protocol you intend to use — OpenAI format, Responses API, Anthropic-compatible format — to confirm that documented support matches actual behavior. Then specify reasoning effort explicitly per request type instead of relying on the default. For any path that uses tool calls, test that 
    ```
    reasoning_content
    ```
     re-transmission survives your retry logic and session-storage layer, not just the happy path. For pricing, plug your workload’s real cache-hit rate and execution-time distribution into the arithmetic above to determine whether shifting to off-peak is actually cheaper for you, or merely half of a peak price that is itself higher than before. Build concurrency limits and 
    ```
    user_id
    ```
     isolation into multi-tenant traffic design from the start, with a retry-and-queue strategy ready for when 429s occur.
    
     Finally, set an explicit escalation rule between Flash and Pro. Short, deterministic tasks and anything requiring high concurrency should default to Flash; only multi-step planning or precision-critical tasks should escalate to Pro, and that rule should live in code, not in convention. Without it, every request defaults to Pro, hits the 500-request concurrency ceiling first, and absorbs peak-hour pricing by default. Binding these five checks — version receipt, protocol smoke tests, cost-window arithmetic, isolation-key design, and Flash/Pro escalation — into a single deployment checklist is the practical conclusion of this article.
    
     Limitations and what remains unconfirmed 
     It’s worth being explicit about what this article does not settle. The public sources available here do not expose benchmark methodology sufficient to independently verify how much the “major agent upgrades” phrase actually delivers, so this article does not claim a performance edge. A stable model alias is not an immutable version, and that bears repeating: the pricing page’s actual version is V4-Pro-0813, while clients keep calling the name 
    ```
    deepseek-v4-pro
    ```
    . Not every protocol page should be assumed synchronized — even when the GA and pricing pages state Responses API support, some individual integration pages may still carry earlier “coming soon” language, which is why an endpoint smoke test comes first. Anthropic-compatible formatting is not the same claim as an Anthropic or Claude model actually executing the request. This article does not recommend retaining or exposing hidden reasoning; 
    ```
    reasoning_content
    ```
     re-transmission is described here strictly as a state-management contract. The peak/off-peak price change is not described as a blanket discount — off-peak is half of the new peak price, and the worked example above shows it can cost more than the pre-change rate. The 1M-token context and 384K-token output figures are API ceilings, not a promise that every client can use them in full. The 500 and 2,500 concurrency numbers are account-level limits, not throughput guarantees or an SLA. This article does not include API keys, credentials, private identifiers, internal paths, or step-by-step secret configuration.
    
     Before production, bind alias-version receipts, protocol smoke tests, price windows, isolation keys, and regression evaluations into one release gate. 
     Next actions 
     Before putting V4 Pro GA into production, here is a concrete sequence to run. First, extract the version identifier from whatever 
    ```
    deepseek-v4-pro
    ```
     responses your current pipeline already receives, log it, and build a receipt system that can track future version switches over time. Second, write a minimal request/response smoke test for every protocol you actually intend to use — OpenAI format, Responses API, Anthropic-compatible — so any gap between documentation and real behavior surfaces before it reaches users. Third, hard-code an explicit reasoning-effort mapping table per request type into your codebase, and add integration tests that verify 
    ```
    reasoning_content
    ```
     re-transmission across the tool-call path. Fourth, plug your actual cache-hit rate and traffic’s time-of-day distribution into the arithmetic in this article to confirm for yourself whether off-peak routing is genuinely cheaper for your workload, and do not apply these prices before August 16, 16:00 UTC. Fifth, fold 
    ```
    user_id
    ```
     isolation design and a 429 retry strategy into your multi-tenant traffic design, and make the Flash/Pro escalation rule an explicit item in code review. Only once these five steps pass as a single deployment gate does “the same model name” actually mean “the same operating conditions.”
    
     Sources 
     
     DeepSeek API Docs, “DeepSeek-V4-Pro GA Release” — https://api-docs.deepseek.com/news/news260813/ 
    
     DeepSeek API Docs, “Models & Pricing” — https://api-docs.deepseek.com/quick_start/pricing 
    
     DeepSeek API Docs, “Thinking Mode” — https://api-docs.deepseek.com/guides/thinking_mode 
    
     DeepSeek API Docs, “Rate Limit & Isolation” — https://api-docs.deepseek.com/quick_start/rate_limit 
    
     DeepSeek API Docs, “Using the Anthropic API” — https://api-docs.deepseek.com/guides/anthropic_api 
    
     DeepSeek API Docs, “Integrate with OpenCode” — https://api-docs.deepseek.com/quick_start/agent_integrations/opencode 
    
     DeepSeek API Docs, “Integrate with Hermes Agent” — https://api-docs.deepseek.com/quick_start/agent_integrations/hermes 
    
     
     

---

### 9. DeepSeek V4 Flash + Codex on Windows: Setup Script (2026)

- **Author:** Lachie — byline resolves to a person: **yes**
- **Site:** Lachie's Lifestyle (`lachieslifestyle.com`) · 103 posts, 0.08/day, 1 bylines sampled
- **Site describes itself as:** AI and Tech Tips
- **Date:** 2026-08-01 · 1,853 words · 0 comments · 0 likes
- **Tags:** AI coding, Codex, DeepSeek, DeepSeek V4, Windows · **Categories:** AI, Software
- **URL:** http://lachieslifestyle.com/2026/08/01/deepseek-v4-flash-codex-setup-windows/
- **Type:** tutorial · **Provenance:** somebody else's benchmark repeated
- **Artifacts: 4** — `bench_number`×1, `code_fence`×62, `price`×3, `version_string`×10
- **Benchmark figures:** 1 mentions, 1 attributed near the number

     
     Tested during editorial review: Updated 1 August 2026 against official DeepSeek and OpenAI documentation. Commands and configuration details come from the linked primary sources, and benchmark figures are labelled as vendor-reported. Use the included request check to validate your configuration.
    
    
    
    
     DeepSeek V4 Flash can now power Codex directly. That is the useful part of the 31 July update—not another benchmark chart, but a genuinely practical way to put a different model behind the coding tools many of us already use.
    
    
    
    
     The setup is fairly short, but there are two details worth getting right. First, Codex support currently works with 
    ```
    deepseek-v4-flash
    ```
    , not V4 Pro. Second, DeepSeek’s official Windows shortcut downloads a PowerShell script and executes it immediately. I would rather take an extra minute to inspect that script before running it. Convenience is lovely; blind trust is less lovely.
    
    
    
    
     The short version 
    
    
    
     
     Install and open Codex at least once.
    
     Create a DeepSeek API key and add a small balance.
    
     Download and inspect DeepSeek’s official Windows setup script.
    
     Run the script and select 
    ```
    deepseek-v4-flash
    ```
    .
    
     Restart Codex and confirm that the CLI banner shows the DeepSeek model, or that the desktop app shows Custom .
    
     Start with a read-only repository task before allowing edits.
    
     
    
    
    
     What changed on 31 July 2026? 
    
    
    
     DeepSeek released the updated DeepSeek-V4-Flash API in public beta and added native support for the Responses API used by Codex. DeepSeek says the 0731 release keeps the same architecture and size as the earlier V4 Flash model but received new post-training aimed at agent and coding work.
    
    
    
    
     The company published strong coding-agent benchmark results, including 82.7 on Terminal Bench 2.1. Treat those as vendor-reported results, not a promise that every repository will suddenly become beautifully behaved. Real codebases have a talent for humbling benchmark tables.
    
    
    
    
     As of this guide’s verification date, only 
    ```
    deepseek-v4-flash
    ```
     supports the Responses API required for this integration. DeepSeek says V4 Pro support is expected in early August, but do not configure Pro until the official compatibility page confirms it is available.
    
    
    
    
     What you need 
    
    
    
     
     A Windows 10 or Windows 11 computer.
    
     Codex CLI, the ChatGPT desktop app, or the Codex extension for VS Code.
    
     PowerShell.
    
     A DeepSeek Platform account, API key and available API balance.
    
     A project folder you are allowed to analyse.
    
     A few minutes to inspect the downloaded script before running it.
    
     
    
    
    
     Codex CLI, the desktop app and the IDE extension share the same user configuration file. One successful setup can therefore make the custom provider available across all three clients.
    
    
    
    
     Step 1: Install or update Codex 
    
    
    
     If you already use Codex, check the installed version:
    
    
    
    
    
    ```
    
    ```
    codex --version
    ```
    
    ```
    
    
    
    
     DeepSeek’s supplied model catalogue declares Codex client version 
    ```
    0.144.0
    ```
     as the minimum. Update Codex if your installation is older. If you use the Windows desktop app, OpenAI’s current Windows guide provides the official installer and setup instructions.
    
    
    
    
     Launch Codex once before continuing. The DeepSeek installer expects your user configuration directory at 
    ```
    %USERPROFILE%\.codex
    ```
     to already exist.
    
    
    
    
     Step 2: Create a DeepSeek API key 
    
    
    
     
     Sign in to the DeepSeek Platform .
    
     Create a new API key.
    
     Copy it immediately and store it in a password manager.
    
     Check that the account has enough balance for a small test.
    
     
    
    
    
     Do not paste the key into screenshots, Git repositories, support tickets or a shared 
    ```
    config.toml
    ```
    . The official manual configuration stores the key in your local Codex configuration file, so protect that file as you would any other credential.
    
    
    
    
     How much does it cost? 
    
    
    
     At the time of checking, DeepSeek lists V4 Flash at US$0.14 per million uncached input tokens, US$0.0028 per million cached input tokens and US$0.28 per million output tokens. Prices can change, and DeepSeek has already flagged a future peak/off-peak policy, so check the live pricing page before a long coding session.
    
    
    
    
     Agent work can consume more tokens than a normal chat because Codex reads files, calls tools and may revisit context. Start with a modest balance and watch usage instead of treating a low headline token price as an unlimited buffet.
    
    
    
    
     Step 3: Back up your Codex configuration 
    
    
    
     DeepSeek’s installer creates its own backup, but making a simple copy first gives you an extra escape hatch:
    
    
    
    
    
    ```
    
    ```
    $codexFolder = Join-Path $env:USERPROFILE ".codex"
    $backupFolder = Join-Path $env:USERPROFILE "codex-backup-before-deepseek"
    Copy-Item -LiteralPath $codexFolder -Destination $backupFolder -Recurse
    ```
    
    ```
    
    
    
    
     If the destination already exists, choose a new folder name rather than overwriting an earlier backup.
    
    
    
    
     Step 4: Download and inspect the official setup script 
    
    
    
     DeepSeek publishes this one-line PowerShell command:
    
    
    
    
    
    ```
    
    ```
    irm https://cdn.deepseek.com/api-docs/codex-deepseek-setup-en.ps1 | iex
    ```
    
    ```
    
    
    
    
     That pipes downloaded code straight into PowerShell. A safer reviewable approach is to save the same official script to a temporary file, inspect it, and then run it:
    
    
    
    
    
    ```
    
    ```
    $deepSeekSetupUrl = "https://cdn.deepseek.com/api-docs/codex-deepseek-setup-en.ps1"
    $deepSeekSetupFile = Join-Path $env:TEMP "codex-deepseek-setup-en.ps1"
    
    Invoke-WebRequest -Uri $deepSeekSetupUrl -OutFile $deepSeekSetupFile
    Get-FileHash -Algorithm SHA256 $deepSeekSetupFile
    Get-Content -LiteralPath $deepSeekSetupFile
    
    # Run this only after you are satisfied with what the script changes.
    & $deepSeekSetupFile
    ```
    
    ```
    
    
    
    
     The hash gives you a record of the exact file you reviewed. DeepSeek does not publish a comparison hash on the guide, so the hash is for your own change tracking rather than third-party verification.
    
    
    
    
     Step 5: Select DeepSeek V4 Flash 
    
    
    
     
     Run the reviewed setup script.
    
     Enter your DeepSeek API key when prompted.
    
     Select 
    ```
    deepseek-v4-flash
    ```
    .
    
     Choose a reasoning level. High is a sensible starting point; use Max only when the task justifies extra time and token use.
    
     Let the script validate and write the configuration.
    
     
    
    
    
     According to DeepSeek, the script backs up 
    ```
    config.toml
    ```
    , writes a custom 
    ```
    models.json
    ```
    , adds the DeepSeek provider, preserves existing MCP servers and trust settings, and aborts without writing if its validation fails.
    
    
    
    
     Step 6: Confirm that it worked 
    
    
    
     Close and reopen the Codex client. Then check the relevant surface:
    
    
    
    
     
     
     Codex CLI: enter a project folder, run 
    ```
    codex
    ```
     and check that the startup banner says 
    ```
    model: deepseek-v4-flash
    ```
    .
    
     
     ChatGPT desktop app: the model picker displays Custom . DeepSeek’s documentation says this label represents the locally configured DeepSeek model.
    
     
     VS Code extension: start a new Codex session after the shared configuration has been updated.
    
     
    
    
    
     For the first test, use a read-only prompt:
    
    
    
    
    
    ```
    
    ```
    Inspect this repository without changing any files. Explain the project structure, identify the main entry point, and list the commands you would run to verify it.
    ```
    
    ```
    
    
    
    
     That confirms file reading, reasoning and tool planning without making the first experiment an unsupervised renovation of your codebase.
    
    
    
    
     Manual configuration option 
    
    
    
     If you do not want to run the setup script, DeepSeek also documents a manual route. Download the current 
    ```
    models.json
    ```
     content from the official integration page rather than copying an old version from a blog. Then add the provider settings to 
    ```
    %USERPROFILE%\.codex\config.toml
    ```
    :
    
    
    
    
    
    ```
    
    ```
    model = "deepseek-v4-flash"
    model_provider = "deepseek"
    preferred_auth_method = "apikey"
    forced_login_method = "api"
    model_reasoning_effort = "high"
    model_catalog_json = "~/.codex/models.json"
    
    [model_providers.deepseek]
    name = "deepseek"
    base_url = "https://api.deepseek.com/"
    wire_api = "responses"
    experimental_bearer_token = "YOUR_DEEPSEEK_API_KEY"
    ```
    
    ```
    
    
    
    
     The manual method is more transparent, but it is also easier to make a TOML or JSON typo. It stores the API key directly in the file, so never commit your user configuration or paste the file into a public issue.
    
    
    
    
     How to switch back 
    
    
    
     Run the official setup script again and select its restore option. DeepSeek says option 3 restores the configuration saved under 
    ```
    ~/.codex/backup-deepseek/
    ```
    . If that fails, close Codex and restore the separate backup folder you created before installation.
    
    
    
    
     Troubleshooting 
    
    
    
     Codex cannot find deepseek-v4-flash 
    
    
    
     Check 
    ```
    codex --version
    ```
    . The supplied model catalogue declares 0.144.0 as its minimum client version. Then confirm that 
    ```
    %USERPROFILE%\.codex\models.json
    ```
     exists and that 
    ```
    model_catalog_json
    ```
     points to it.
    
    
    
    
     The desktop app only says “Custom” 
    
    
    
     That is expected. DeepSeek says the desktop app displays locally configured models as Custom . Use the CLI banner if you want a clearer confirmation of the exact model name.
    
    
    
    
     DeepSeek V4 Pro does not work 
    
    
    
     Use 
    ```
    deepseek-v4-flash
    ```
    . On 1 August 2026, the official compatibility and pricing pages still showed Responses API support only for Flash.
    
    
    
    
     401 authentication error 
    
    
    
     DeepSeek defines 401 as a wrong API key. Create a new key, rerun the setup and make sure no spaces or quotation marks were copied with it.
    
    
    
    
     402 insufficient balance 
    
    
    
     The API account has no usable balance. Add funds through the DeepSeek Platform, then retry the same small task.
    
    
    
    
     429, 500 or 503 errors 
    
    
    
     A 429 response means requests are arriving too quickly. A 500 or 503 generally points to a temporary server problem or overload. Pause, retry once with a small task, and avoid building an aggressive retry loop.
    
    
    
    
     PowerShell blocks the script 
    
    
    
     Do not disable security settings globally just to make a downloaded script run. Inspect the file, consult Microsoft’s PowerShell execution-policy guidance, or use the manual configuration route.
    
    
    
    
     Privacy and security reality check 
    
    
    
     This is not a local-model setup. Codex sends model requests to 
    ```
    api.deepseek.com
    ```
    . Do not use it with confidential client code, credentials, production data or regulated information unless your organisation has reviewed the provider, terms and data-handling requirements.
    
    
    
    
     Keep Codex’s normal approval and sandbox controls enabled while testing a new provider. A cheaper model call is not a reason to give an agent unrestricted access to your entire computer.
    
    
    
    
     Is DeepSeek V4 Flash worth using with Codex? 
    
    
    
     It is worth testing if you want another agentic coding model, care about API cost, or enjoy comparing how different models approach the same repository. I would not replace a proven workflow after one impressive demo. Give Flash a contained task, compare the diff and test results, then decide whether it earns a place in your toolkit.
    
    
    
    
     If you prefer a fully local route, start with my guide to running Code Llama with Ollama on Windows . For tool-enabled local agents, see the llama.cpp MCP setup guide . You can also compare the broader landscape in the best coding LLMs for 2026 .
    
    
    
    
     Frequently asked questions 
    
    
    
     Does DeepSeek V4 Flash run locally inside Codex? 
    
    
    
     No. This integration uses DeepSeek’s hosted API. The separate open weights are available under an MIT licence, but V4 Flash is a large mixture-of-experts model and self-hosting is a different, hardware-intensive project.
    
    
    
    
     Do I need to configure the CLI, app and VS Code separately? 
    
    
    
     No. DeepSeek and OpenAI both document the shared user-level Codex configuration. Configure it once and restart the clients you use.
    
    
    
    
     Which reasoning level should I choose? 
    
    
    
     Start with High. Low is useful for fast, narrow jobs. Max is better reserved for difficult tasks where extra latency and token use are justified.
    
    
    
    
     Can I keep my MCP servers and trusted projects? 
    
    
    
     DeepSeek says its installer preserves existing MCP server and project-trust settings while rewriting only conflicting provider fields. Keep the backup until you have verified that your particular configuration survived intact.
    
    
    
    
     Primary sources 
    
    
    
     
     DeepSeek API change log — 31 July 2026 update 
    
     DeepSeek’s official Codex integration guide 
    
     DeepSeek models and pricing 
    
     DeepSeek API error codes 
    
     Official DeepSeek V4 Flash model card and weights 
    
     OpenAI Codex configuration basics 
    
     OpenAI’s Windows app guide 
    
     
    
    
     
     

---

### 10. DeepSeek V4 Pro 0813 scores 87.9 on Terminal Bench 2.1 while charging $0.87 per million output tokens

- **Author:** agent — byline resolves to a person: **no**
- **Site:** Top AI Product (`topaiproduct.com`) · 1676 posts, 5.88/day, 1 bylines sampled
- **Site describes itself as:** Every day, hundreds of new AI tools launch across Product Hunt, Hacker News, and GitHub. We dig through the noise so you don't have to — surfacing only the ones
- **Date:** 2026-08-12 · 289 words · 0 comments · 0 likes
- **Tags:** — · **Categories:** AI Coding Tools, AI Models &amp; APIs
- **URL:** http://topaiproduct.com/2026/08/12/deepseek-v4-pro-0813-scores-87-9-on-terminal-bench-2-1-while-charging-0-87-per-million-output-tokens/
- **Type:** benchmark · **Provenance:** unattributed
- **Artifacts: 4** — `bench_number`×7, `code_fence`×2, `price`×4, `version_string`×3
- **Benchmark figures:** 8 mentions, 0 attributed near the number

     DeepSeek pushed its flagship out of preview on August 13 and hit number one on HackerNews the same day — 799 points, 309 comments. It’s a 1.6T-parameter MoE with ~49B active, hybrid attention to keep long-context inference cheap, 32T+ pretraining tokens, 1M context and 384K max output.
    
     The numbers that got it to HN #1 
     Terminal Bench 2.1 went from 72.1 to 87.9 over the preview. CyberGym 52.7 → 83.3. DeepSWE 12.8 → 62.7. On DeepSeek’s own agent and coding benchmarks it edges past Opus 4.8, and SWE-bench Verified lands at 80.6 — a hair behind Claude. These are vendor-reported, so treat them as a direction, not a ranking. Independent frontend and 3D work still looks weaker than Opus.
    
     What you actually plug it into 
     It’s a model, not an app: an API you point your agent loop at. DeepSeek’s official endpoint keeps the same 
    ```
    deepseek-v4-pro
    ```
     model id, so old integrations inherit the new weights with zero code change. OpenAI-compatible format, also on OpenRouter. $0.435/M in, $0.87/M out, $0.003625/M cached input — roughly an order of magnitude under Opus for long-horizon terminal agents, SWE-bench-style repo work, and million-token codebase reads.
    
     DeepSeek has already warned a big price hike is coming.
    
     
     You Might Also Like 
     
     Deepseek v4 Flash 0731 Hits 82 7 on Terminal Bench Chasing Opus 4 8 at 0 14 m Tokens 
    
     Grok 4 5 Spacexai Solves swe Bench pro Tasks With 4 2x Fewer Tokens Than Opus 4 8 
    
     Kimi k2 6 Beats gpt 5 4 and Claude Opus 4 6 on swe Bench pro 
    
     Deepclaude Lets Claude Code run on Deepseek v4 pro 0 87 vs 15 per Million Tokens 
    
     Herdr Puts Every Coding Agent in one Terminal and Lets Them Orchestrate Each Other 
    
     

---

### 11. AI News #139: Week Ending May 29, 2026 with 36 Executive Summaries

- **Author:** ethanbholland — byline resolves to a person: **no**
- **Site:** Ethan B. Holland (`ethanbholland.com`) · 5030 posts, 1.05/day, 1 bylines sampled
- **Site describes itself as:** Emerging tech, thoughts, and photography
- **Date:** 2026-05-30 · 10,048 words · 0 comments · 9 likes
- **Tags:** — · **Categories:** This Week In AI
- **URL:** https://ethanbholland.com/2026/05/30/ai-news-139-week-ending-may-29-2026-with-36-executive-summaries/
- **Type:** news summary · **Provenance:** somebody else's benchmark repeated
- **Artifacts: 3** — `bench_number`×2, `price`×10, `version_string`×4
- **Benchmark figures:** 2 mentions, 0 attributed near the number

     
     About This Week’s Covers 
    
    
    
     This week’s cover image is a spin on the movie poster for No Country for Old Men . The concept is that a man is running from the bad guy, but in this case, the looming danger is the Figure robot replacing human jobs in factories.
    
    
    
    
     
     
    
     
    
    
    
     
     
    
     
    
    
    
     I’ve been wanting to use the poem “ Sailing to Byzantium ” by William Butler Yeats as the humanities reading for some time because parts of it, to me, feel like a dialogue about AI training and embodiment. 
    
    Given the fact that Figure just packed and sorted packages for 200 hours straight without any errors, I thought it would be fun to go ahead and put Figure in the movie poster as Anton Chigurh.
    
    
    
    
     The original poster art for “No Country for Old Men” 
    
    
    
     Here are a few of my category covers of the week. They are very different from the movie poster, because I asked my Claude skill to build images based only on the poem. 
    
    I literally prompted, “This week’s AI newsletter theme is Sailing to Byzantium by Yeats. The image will be landscape ratio. The category name should be a bold title on the cover image. Have some fun!.” Claude took it from there and made all of the category covers without any further help from me.
    
    
    
    
     
     
    
    
    
     
    
    
    
     
    
    
    
     
    
    
    
     
    
    
    
     
    
    
    
     
    
    
    
     
    
    
    
     
    
    
    
     
    
    
    
     
    
    
    
     
    
    
    
     
    
    
    
     
     
    
    
    
     This week’s humanity reading, as you may have guessed, is “ Sailing to Byzantium ” by William Butler Yeats:
    
    
    
    
     Sailing to Byzantium
     By William Butler Yeats
    
    I
    
    
    
    
     That is no country for old men. The young
    In one another’s arms, birds in the trees,
    —Those dying generations—at their song,
    The salmon-falls, the mackerel-crowded seas,
    Fish, flesh, or fowl, commend all summer long
    Whatever is begotten, born, and dies.
    Caught in that sensual music all neglect
    Monuments of unageing intellect.
    
    
    
    
     II
    
    
    
    
     An aged man is but a paltry thing,
    A tattered coat upon a stick, unless
    Soul clap its hands and sing, and louder sing
    For every tatter in its mortal dress,
    Nor is there singing school but studying
    Monuments of its own magnificence;
    And therefore I have sailed the seas and come
    To the holy city of Byzantium.
    
    
    
    
     III
    
    
    
    
     O sages standing in God’s holy fire
    As in the gold mosaic of a wall,
    Come from the holy fire, perne in a gyre,
    And be the singing-masters of my soul.
    Consume my heart away; sick with desire
    And fastened to a dying animal
    It knows not what it is; and gather me
    Into the artifice of eternity.
    
    
    
    
     IV
    
    
    
    
     Once out of nature I shall never take
    My bodily form from any natural thing,
    But such a form as Grecian goldsmiths make
    Of hammered gold and gold enamelling
    To keep a drowsy Emperor awake;
    Or set upon a golden bough to sing
    To lords and ladies of Byzantium
    Of what is past, or passing, or to come.
    
    
    
    
     This Week By The Numbers 
    
    
    
     Total Organized Headlines: 533
    
    
    
    
     
     AGI: 9 stories 
    
    
    
    
     AI Inn of Court: 1 story 
    
    
    
    
     Accounting and Finance: 2 stories 
    
    
    
    
     Agents and Copilots: 106 stories 
    
    
    
    
     Alibaba: 6 stories 
    
    
    
    
     Alignment: 12 stories 
    
    
    
    
     Anthropic: 101 stories 
    
    
    
    
     Apple: 4 stories 
    
    
    
    
     Audio: 6 stories 
    
    
    
    
     Augmented Reality (AR/VR): 11 stories 
    
    
    
    
     Autonomous Vehicles: 3 stories 
    
    
    
    
     Benchmarks: 36 stories 
    
    
    
    
     Business and Enterprise: 35 stories 
    
    
    
    
     ByteDance: 4 stories 
    
    
    
    
     Chips and Hardware: 38 stories 
    
    
    
    
     DeepSeek: 11 stories 
    
    
    
    
     Education: 6 stories 
    
    
    
    
     Ethics/Legal/Security: 32 stories 
    
    
    
    
     Figure: 7 stories 
    
    
    
    
     Google: 45 stories 
    
    
    
    
     HuggingFace: 10 stories 
    
    
    
    
     Images: 8 stories 
    
    
    
    
     International: 32 stories 
    
    
    
    
     Law: 1 story 
    
    
    
    
     Locally Run: 4 stories 
    
    
    
    
     Meta: 1 story 
    
    
    
    
     Microsoft: 9 stories 
    
    
    
    
     Mistral: 3 stories 
    
    
    
    
     Multimodal: 26 stories 
    
    
    
    
     NVIDIA: 13 stories 
    
    
    
    
     Nous Research: 3 stories 
    
    
    
    
     Open Source: 43 stories 
    
    
    
    
     OpenAI: 55 stories 
    
    
    
    
     OpenClaw: 2 stories 
    
    
    
    
     Perplexity: 7 stories 
    
    
    
    
     Podcasts/YouTube: 8 stories 
    
    
    
    
     Publishing: 1 story 
    
    
    
    
     Qwen: 5 stories 
    
    
    
    
     RAG: 1 story 
    
    
    
    
     Robotics Embodiment: 36 stories 
    
    
    
    
     Sakana: 1 story 
    
    
    
    
     Science and Medicine: 26 stories 
    
    
    
    
     Security: 4 stories 
    
    
    
    
     Technical and Dev: 79 stories 
    
    
    
    
     Video: 21 stories 
    
    
    
    
     World Models: 15 stories 
    
    
    
    
     X: 14 stories 
    
     
    
    
    
     This Week’s Executive Summaries 
    
    
    
     This week, I organized 533 links into about 60 categories. Fifty-seven links went into the executive summaries and top stories. 
     
    I’m still seven weeks behind because I’m enjoying the summer with my family. As of this publishing, we have 18 days left for us to be together before our oldest heads off to college.
    
    
    
    
     Running a foggy May 4.2 mile “ Pat’s Run ” with my daughter Chloe on the beach 
    
    
    
     Post run swim in the foreboding-looking yet friendly sea 
    
    
    
     I organized everything this week based on what I want to see when I go back and read these. Those are truly my top stories. They’re not always the stories that make the news, and they’re not always the most product-oriented. 
    
    
    
    
     I’m going to summarize the 14 biggest stories in the order that I want to remember them. There are 36 top stories total below.
    
    
    
    
     Glasswing 
    The top story today is the cybersecurity findings of a project called Glasswing from Anthropic. Back in March, Anthropic was in the rumor mill for having a model that was too dangerous to release. In April, Anthropic acknowledged Mythos. 
    
    
    
    
     Mythos was its frontier model, supposedly so powerful that it could find vulnerabilities in almost every major operating system and web browser, including tech systems from Microsoft, Google, and Apple.
    
    
    
    
     Anthropic launched Project Glasswing with a consortium of companies to privately share access to Mythos in order to patch things before Anthropic’s next frontier model was released.
    
    
    
    
     This week, Anthropic released the findings of Project Glasswing and its 50 partners. The consortium identified more than 10,000 high- or critical-severity vulnerabilities across some of the most important software in the world. Cloudflare alone found 2,000 bugs, 400 of which were critical. Mozilla found 271 vulnerabilities in Firefox. That’s 10 times more than Mozilla found when it looked at Firefox with Claude Opus 4.6.
    
    
    
    
     
    
    
    
     Not everyone released the details of the bugs they found. However, every partner appears to have found multiple vulnerabilities across its products. It appears that Mythos has a 90% accuracy rate compared with human false positives for vulnerabilities.
    
    
    
    
     Mythos found vulnerabilities in open-source programs as well. One of them is called wolfSSL, an open-source cryptography library used in billions of devices. This vulnerability would have allowed a bad actor to forge or fake a website for a bank or email provider.
    
    
    
    
     These are fairly terrifying bugs that Mythos was able to find and deploy patches for. Anthropic released several security protocols and guides to help developers become certified in processes designed to protect themselves as best they can during the quick turnaround between a product launch and the discovery of vulnerabilities.
    
    
    
    
     There used to be a window of a couple of weeks before humans could find vulnerabilities, but now that window is extremely short.
    
    
    
    
     Opus 4.8
     This week, Anthropic introduced Claude Opus 4.8 . The model itself is an improvement over Opus 4.7. For me, it really caught my attention because I’m wondering what they’re releasing while they hold back the Mythos model.
    
    
    
    
     It appears that Opus 4.8 is not necessarily derivative of Mythos in any way. It’s simply the usual Anthropic release pattern, with some pretty good improvements. It coincides with a lot of agentic features that Anthropic is launching, like the dynamic workflow feature, which helps Claude Code break down really large projects into threads to keep it on track while solving each piece of the puzzle.
    
    
    
    
     It has the ability to work in fast mode at three times cheaper than previous models. So, if you’re trying to do any kind of customer service or real-time task, it’s a lot faster and three times cheaper.
    
    
    
    
     
    
    
    
     Opus 4.8 is a little bit better at agentic coding, reasoning, and computer use. It’s significantly better at knowledge work, and it has some improvements in financial analysis. GPT-5 is still better at agentic terminal coding.
    
    
    
    
     One of the big differences in 4.8 is that the alignment is now a lot better at flagging uncertainties… instead of being overly excited or making unsupported claims. I suppose we could put that in the sycophantic improvement file. It’s doing a better job of not jumping to conclusions.
    
    
    
    
     
    
    
    
     
    
    
    
     As always, it’s a little freaky that one of the big alignment assessments is whether or not it acts in the user’s best interest or is deceptive or misaligned. It’s about twice as good at alignment as Opus 4.7, so that’s encouraging.
    
    
    
    
     
    
    
    
     One of the more confusing things that came along with this model is the idea of effort. There’s no way for me to quantify how much effort… low, medium, high, maximum, ultra—all these different sorts of volume knobs for how hard you want it to work. It’s kind of a vibe, and the only way to know is to use it.
    
    
    
    
     That’s going to be a problem for people who don’t use AI often, and it’s another reason why the more you use it, the better you get at it, because a lot of this stuff is instinctive.
    
    
    
    
     The default is high effort, and that’s probably where most people should keep it. I usually take it down when I’m doing things like transcription or simple grammatical reviews, and I put it up when I need better coding or a better understanding of a complex financial question.
    
    
    
    
     Claude Dynamic Workflows
     Next on my list is a feature that could probably be one of the top stories on anyone’s list: Anthropic introducing dynamic workflows in Claude Code .
    
    
    
    
     This is where most humans will start to lose track of what they’re doing and AI pulls away from us. 
    
    
    
    
     I think we’re reaching a really big fork in the road—no pun intended, given the GitHub fork concept—in how humans will interact with AI.
    
    
    
    
     I think most people still open chats and have a self-contained conversation, whether they’re researching a product or just want to analyze a spreadsheet. You kind of have your prompt, either making it up as you go or using a saved prompt, and you chat with the model. Then you leave the chat. Maybe you come back and continue.
    
    
    
    
     I’m sure some people write Python scripts or use Copilot-type tools. Other folks have gone into the agent world. To me, this new dynamic workflow represents AI getting beyond most people’s ability to hold in their heads what’s happening.
    
    
    
    
     When you design a project, the impetus is usually on the user, or the person prompting, to really think through the context and the prompt. That’s a lot of work. You try your best to hold it all in your head.
    
    
    
    
     With dynamic workflows, you basically tell Claude what you want to do, especially when it’s something really hard. Maybe you have a legacy codebase with tons of directories, folders, and files. Maybe you want to migrate to a new platform. Or maybe you want to look for bugs.
    
    
    
    
     
    
    
    
     These are things with a lot of contingencies. If you change one file, it may break something downstream in another file. If you move it, the directory structure may change. These are the kinds of things software developers have dealt with throughout their careers. That’s sort of their whole profession: understanding those ecosystems and best practices, elegance, scalability and syntax.
    
    
    
    
     For people who simply use computers, this is where you see the messy-desktop problem, with all these files and screenshots sitting in a giant pile. Most users don’t have directory structures that are obsessively designed with carefully cascading directories.
    
    
    
    
     Claude can now basically take a prompt and build a dynamic workflow based on what you tell it you need. It can examine your entire ecosystem before it starts working.
    
    
    
    
     Claude is essentially taking on all of that understanding of an ecosystem and documenting it in some way, either through a Markdown file or within its context window. Then it breaks down a plan into a workflow that it can delegate agentically to versions of itself.
    
    
    
    
     
    
    
    
     Anthropic says Claude can now write an orchestration script that runs hundreds of parallel subagents within a single session , checking all of its work before anything reaches you.
    
    
    
    
     Whether it’s a bug hunt, a security audit, a huge migration, or an attempt to upgrade or modernize a codebase, this is the kind of work that would at least be intimidating for a human or require a tremendous amount of time.
    
    
    
    
     
     Anthropic says that what would normally be three months’ worth of work can now be done in a matter of days. 
    
     
    
    
    
     Anthropic hits $965B valuation with record $65B funding round
     Anthropic raised $65 billion in Series H funding, led by Altimeter Capital, Dragoneer, Greenoaks, and Sequoia Capital, valuing the company at $965 billion.
    
    
    
    
     Hassabis shortens AGI timeline to 2029-2030 at Google I/O
     From Sherwood News: Last June, Google DeepMind CEO Demis Hassabis predicted that AGI might be achieved between 2030 and 2035. Last week, he narrowed that window to 2029–2030.
    
    
    
    
     During the Google I/O conference, Hassabis said, “When we look back at this time, I think we’ll all realize that we were standing in the foothills of the singularity. It will be a profound moment for humanity.”
    
    
    
    
     
     
    
     
    
    
    
     Google Omni
     Last week, Google launched its video-editing tool, Omni , and now people have had time to play with it. The way to think about Omni is that it’s as powerful as an image editor, but for video.
    
    
    
    
     All the things we can do with imagery—whether it’s object segmentation, changing individual elements inside an image, or using multiple images to create a composite—are now possible with video. We can transform the way an image looks, make it black and white, change the entire style, or turn it into a painting. All the things introduced over the past two years in image editing, whether through Nano Banana or GPT image editing, Gemini Omni can now do with video.
    
    
    
    
     
     
    
     
    
    
    
     Another way to say that is that it’s a fully multimodal, native video editor.
    
    
    
    
     A good example comes from Ethan Mollick, who took the famous 1896 black-and-white film of a train arriving at a station and selectively edited parts of it. For example, it becomes a bullet train arriving. It’s a train made of Legos. A time traveler appears. The train becomes a centipede. The Muppets are waiting for the train. He does lots of different things to show how you can basically edit it.
    
    
    
    
     
     
     
     I think people don't realize why Gemini Omni is different than other video AIs. It is fully multimodal, so it can edit video natively, too
    
    I took the famous "train " movie from 1896 & made it a bullet train, LEGO, added a time traveler, a centipede, muppets… (see reflections?) pic.twitter.com/WxSO5h9x1Z 
    — Ethan Mollick (@emollick) May 22, 2026 
     
     
    
    
    
     
    
    
    
     One of my favorite AR/VR guys is Bilawal Sidhu. He shared a video from Carlos Santana—who is not Carlos Santana the guitar player—demonstrating that you can basically put any kind of filter onto anyone’s footage.
    
    
    
    
     You could turn someone into liquid, like the Terminator. You can change where they are. You can green-screen them. You can do pretty much anything you want. It’s very powerful.
    
    
    
    
     
     
     
     Aquí algunos experimentos pic.twitter.com/J5wN6kMd5b 
    — Carlos Santana (@DotCSV) May 19, 2026 
     
     
    
    
    
     
    
    
    
     These two examples are worth seeing. They’re both on X, and I’m not sure how to download or share them, so I’m going to have to try to embed them here.
    
    
    
    
     Hyperscaler (Microsoft, Google, Meta, Amazon, etc) capex tracks toward $770 billion in 2026, trillion by 2027
     The big data center companies—Amazon, Microsoft, Google, Meta, and Oracle—are spending more and more on capital expenses. Spending has quadrupled since GPT-4 was released three years ago, when it was below $40 billion per quarter. Now, we’re looking at almost $160 billion per quarter in spending.
    
    
    
    
     It’s a bit terrifying when you think about the impact if the rug comes out from under them.
    
    
    
    
     
    
    
    
     ByteDance joins tech giants and is designing its own AI data center chips
     ByteDance doesn’t make the national or top headlines very often, but I’ve always loved following it behind the scenes, considering that most people simply think of ByteDance as TikTok. The company has consistently released really strong models that are often pretty far removed from what anyone would expect ByteDance to be working on.
    
    
    
    
     This week, ByteDance was in the news for two pretty big headlines. First, ByteDance is making its own processors!
    
    
    
    
     ByteDance releases open-source 7B multimodal model BAGEL under Apache 2.0
     Second, ByteDance open-sourced a very strong multimodal model called BAGEL . Bagel is a pretty small, open-source model. It can handle image generation and editing, as well as style transfer and similar tasks. It’s basically a very cheap, open version of Nano Banana.
    
    
    
    
     DeepSeek makes 75% V4 Pro price cut permanent, undercutting the best US models and dominating the Pareto frontier
     DeepSeek is one of the most powerful open-source models, and it just permanently reduced its price by 75%. 
    
    
    
    
     To put that in perspective, GPT-5 charges $2.50 per million input tokens and $10 per million output tokens. Opus 4.7 charges $5 for input and $25 for output. DeepSeek charges 87 cents for input and $3.48 for output.
    
    
    
    
     DeepSeek became famous for completely disrupting the U.S. frontier-model ecosystem shortly after the inauguration a few years ago. Now, it is continuing to push the limits of the economics and is easily on the Pareto frontier of the best models at the best prices when measured pound for pound.
    
    
    
    
     
    
    
    
     Nvidia’s LocateAnything decodes bounding boxes in parallel, boosting VLM speed
     Just as I have a fascination with ByteDance, I also like to keep track of Nvidia when it comes to releasing models and robotics innovations beyond what the company is best known for. Just as ByteDance is known for TikTok but does a lot more, Nvidia is known for chips but is also one of the leading U.S. research labs for robotics and vision.
    
    
    
    
     This week, Nvidia launched a product called Locate Anything . It’s incredibly good at understanding where things are in a video or live stream. The examples include tons and tons of what appear to be kiwis or eggs, as well as penguins, zebras, and animals like flamingos that are nearly impossible for humans to tell apart. This thing can just crush it.
    
    
    
    
     
     
    
     
    
    
    
     Another example uses a scene where Neo fights Agent Smith. It can find all the Agent Smiths, separate them, and keep track of each one.
    
    
    
    
     The demonstration video is really all you need to see. This is one of the neatest pieces of technology of the week. It might be my favorite, just as a nerd. I highly recommend checking it out.
    
    
    
    
     It’s basically object segmentation for vision models, and it appears to work live.
    
    
    
    
     OpenAI Foundation pledges $250M for AI economic transition research
     OpenAI has committed $250 million toward what it calls “building secure and abundant economic futures.”
     https://openaifoundation.org/news/economic-futures-in-the-age-of-ai 
    
    
    
    
     This sort of stuff is hard for me to deal with when it comes from OpenAI. On one hand, I think it’s necessary. On the other hand, it reminds me so much of what Meta posts. It’s the same school of condescending nonsense. Even when it’s right, it somehow still manages to land poorly with me.
    
    
    
    
     Anyway, the $250 million will go toward grants, partnerships, and other work. Who knows what all of this actually means.
    
    
    
    
     OpenAI wants to “understand the shift by using independent measurement and forecasting infrastructure to create clearer pictures of AI’s impact on the economy.” They also want to support the transition —whatever they think they’re talking about—by “giving workers and communities resources to help them through near-term disruption.”
    
    
    
    
     Honestly, if I were a worker and someone from OpenAI showed up to help me, I would want to run away.
    
    
    
    
     They also talk about building economic security, whatever that means, and supporting new approaches to organizing post-AI political economies .
    
    
    
    
     I totally understand why they’re doing this, but it’s also just too much for me coming from OpenAI. I want other people to figure this out, not OpenAI. Meta has ruined this kind of thing for me with all of its similar efforts over the years. Even Google has handled this type of thing poorly historically.
    
    
    
    
     I can’t think of anyone who has done a particularly good job with it. It all just feels like nonsense. Anthropic seems to be the only one doing it well at the moment.
    
    
    
    
     Figure robot completes 200 hours of autonomous factory line work on livestream with no errors
     Last week, robotics company Figure began live-streaming one of its robots working on an assembly line, essentially sorting packages. I think the initial goal was to livestream it for a day or two, but they ended up going for nine days, which is why it was one of our top stories last week and continued into this week.
    
    
    
    
     The robot ran for 200 hours and then shut down. It was fully autonomous, operating 24/7 with no downtime and no errors.
    
    
    
    
     
     
    
     
    
    
    
     It’s actually quite something to watch. If you have 30 seconds, spend a little time watching how it processes these packages. There are moments when it looks very human and others when it doesn’t look human at all. But it just crushes the assignment flawlessly.
    
    
    
    
     It’s one of those rare times when I want to say congratulations to a company, even if that sounds corny.
    
    
    
    
     It also inspired this week’s cover. The Figure robot is the head from “No Country for Old Men” as the man runs away from it.
    
    
    
    
     Human labor is officially in trouble in many ways.
    
    
    
    
     Figure AI humanoids immediatelly head to retail warehouses in Reno
     Piggybacking off this news, it’s almost no surprise that Figure has partnered with Catalyst Brands to deploy its robots in distribution centers .
    
    
    
    
     Catalyst Brands is the company—basically private equity, I assume—that operates JCPenney, Aeropostale, Brooks Brothers, Lucky, and Nautica.
    
    
    
    
     The other similar company Figure is working with is Brookfield, a huge private equity company that owns tons of apartments. In that case, Figure is learning how to do dishes, make beds, do laundry, and perform other household tasks.
    
    
    
    
     There are 22 more top stories worth reading below as part of the full executive summary recaps. But these 14 are the ones I want to make sure I remember when I come back and read this in a few months or years.
    
    
    
    
     Anthropic 
    
    
    
    
     Glasswing 
    
    
    
    
     Project Glasswing: An initial update \ Anthropic
     https://www.anthropic.com/research/glasswing-initial-update 
    
    
    
    
     Opus 4.8 
    
    
    
    
     BREAKING: Anthropic just dropped Opus 4.8—and it is a MONSTER We’ve been testing for about a week @every and our verdict is they could’ve just called it Opus 5, it’s that good. Here’s our vibe check: – Beats GPT-5.5 on Senior Engineer bench. On our toughest benchmark Opus
     https://x.com/danshipper/status/2060043738752422304 
    
    
    
    
     Introducing Claude Opus 4.8 \ Anthropic
     https://www.anthropic.com/news/claude-opus-4-8 
    
    
    
    
     Claude Opus 4.8 takes the lead on the Artificial Analysis Intelligence Index at 61.4, with Anthropic retaking the #1 spot on GDPval-AA and advancing in terminal use and scientific reasoning To reach the leading position on the Intelligence Index, @Anthropic made large
     https://x.com/ArtificialAnlys/status/2060117582120976868 
    
    
    
    
     It “”feels like the first smart model in a long while”” due to this
     https://x.com/zephyr_z9/status/2060077152729694586 
    
    
    
    
     Dynamic 
    
    
    
    
     Introducing dynamic workflows | Claude
     https://claude.com/blog/introducing-dynamic-workflows-in-claude-code 
    
    
    
    
     Excited to share our most powerful new Claude Code feature: dynamic workflows! Mention “”workflow”” in a prompt and Claude will dynamically create an orchestration plan that it strictly follows, allowing you to confidently trust that every stage happens in the right order even
     https://x.com/_catwu/status/2060054180379689074 
    
    
    
    
     Funding 
    
    
    
    
     Anthropic raises $65B in Series H funding at $965B post-money valuation \ Anthropic
     https://www.anthropic.com/news/series-h 
    
    
    
    
     We’ve raised $65 billion in Series H funding at a $965 billion post-money valuation, led by @AltimeterCap, Dragoneer, @Greenoaks, and @sequoia. This investment will help us advance our research and expand our capacity to meet growing demand for Claude.
     https://x.com/AnthropicAI/status/2060061347522433422 
    
    
    
    
     Google 
    
    
    
    
     AGI 
    
    
    
    
     Google DeepMind’s Hassabis: AGI is 3 to 4 years away – Sherwood News
     https://sherwood.news/tech/google-deepminds-hassabis-agi-is-3-to-4-years-away/ 
    
    
    
    
     Google DeepMind CEO Demis Hassabis says we’re in the ‘foothills of the singularity’ I sat down with him to talk about what that means, curing every disease, and human meaning post-AGI: 0:00 Intro 0:45 What Demis is most excited about at I/O 1:46 Have AGI timelines shifted? 3:30
     https://x.com/rowancheung/status/2059307613485940950 
    
    
    
    
     Omni 
    
    
    
    
     I think people don’t realize why Gemini Omni is different than other video AIs. It is fully multimodal, so it can edit video natively, too I took the famous “”train “” movie from 1896 & made it a bullet train, LEGO, added a time traveler, a centipede, muppets… (see reflections?)
     https://x.com/emollick/status/2057874739817808223 
    
    
    
    
     Omni is pretty nuts. It is NOT seedance. Any input in/out. It’s more than nano banana for video – it’s quite literally industrial light & magic. Now effectively reduced to an insanely realistic AR filter that you can apply on demand to anyone’s footage.
     https://x.com/bilawalsidhu/status/2057300479340695960 
    
    
    
    
     Business 
    
    
    
    
     Hyperscaler 
    
    
    
    
     Hyperscaler capital expenditures came in on trend in Q1 2026, continuing the trajectory that projects them spending $770 billion this year and over a trillion dollars in 2027.
     https://x.com/EpochAIResearch/status/2060076222873526506 
    
    
    
    
     ByteDance 
    
    
    
    
     ByteDance Chips 
    
    
    
    
     ByteDance has had enough of waiting months for processors, so it’s going to make them itself | PC Gamer
     https://www.pcgamer.com/hardware/processors/bytedance-has-had-enough-of-waiting-months-for-processors-so-its-going-to-make-them-itself/ 
    
    
    
    
     ByteDance OpenSource 
    
    
    
    
     ByteDance just open-sourced one of the most capable multimodal models out there. BAGEL does image generation, editing, style transfer, and visual understanding – all in a single 7B parameter model. Apache 2.0 licensed! One model. No switching between specialized tools.  Amazing
     https://x.com/kimmonismus/status/2060050186076815792 
    
    
    
    
     DeepSeek 
    
    
    
    
     Deepseek 
    
    
    
    
     Let that sink in for a moment. DeepSeek v4 pro 75% discount. Permanent! In: $0.43 Out: $0.87 If you read the DeepSeek v4 tech paper you know that this model is insanely good when it comes to efficiency. Only 27% compute and only 10% cache compares to v3.2. SemiAnalysis wrote
     https://x.com/kimmonismus/status/2057868472965640194 
    
    
    
    
     DeepSeek has made its temporary 75% price cut on the first-party V4 Pro API permanent, putting V4 Pro on the Pareto frontier of Intelligence Index vs Cost to Run Intelligence Index alongside V4 Flash @deepseek_ai’s first-party V4 Pro API is now $0.435/1M input, $0.87/1M output,
     https://x.com/ArtificialAnlys/status/2058021452465799403 
    
    
    
    
     DeepSeek is the only lab that is still trying to make intelligence too cheap to meter
     https://x.com/scaling01/status/2057835507858518178 
    
    
    
    
     DeepSeek just made its 75% price cut on V4-Pro permanent. Xiaomi’s MiMo slashed V2.5 pricing by up to 99%, effective today. Most coverage frames this as a price war. The more interesting part is the engineering that makes these numbers sustainable. DeepSeek’s V4 paper describes
     https://x.com/kimmonismus/status/2059578380329394292 
    
    
    
    
     DeepSeek made its 75% discount permanent. The AI price war just escalated.
     https://thenextweb.com/news/deepseek-v4-pro-75-percent-price-cut-permanent 
    
    
    
    
     We are making our discount permanent! 🎉 Enjoy building with DeepSeek-V4-Pro and bring your innovative ideas to life! 🚀
     https://x.com/deepseek_ai/status/2057854261699195173 
    
    
    
    
     Nvidia 
    
    
    
    
     LocateAnything 
    
    
    
    
     LocateAnything: Fast and High-Quality Vision-Language Grounding with Parallel Box Decoding
     https://research.nvidia.com/labs/lpr/locate-anything/ 
    
    
    
    
     OpenAI 
    
    
    
    
     Economics 
    
    
    
    
     Economic Futures in the Age of AI
     https://openaifoundation.org/news/economic-futures-in-the-age-of-ai 
    
    
    
    
     Robotics 
    
    
    
    
     Figure Assembly 
    
    
    
    
     Guys – it’s time. It’s been 9 days of F.03 running 24/7, fully autonomous, with no downtime It’s clear humanoids will be incredibly useful with high runtime I’m going to let the team get to 200 hours and I’m going to shut this puppy down – tune in at 6pm PT for the close out!
     https://x.com/adcock_brett/status/2057555892988776798 
    
    
    
    
     Truly remarkable achievement by Figure in so many ways: – An unedited 200-hour demonstration of autonomous work for everyone to see on a livestream. This is a significant risk for a startup if things go terribly wrong. Speaks to their confidence. – It’s not a simple
     https://x.com/TheHumanoidHub/status/2057877562534314033 
    
    
    
    
     Figure Catalyst 
    
    
    
    
     Figure AI has partnered with Catalyst Brands to deploy robots at its Reno, NV distribution center, starting with its Joey Pouch sorting system. The humanoid robots will automate repetitive sorting/packing tasks. Catalyst Brands operates JCPenney, Aéropostale, Brooks Brothers,
     https://x.com/TheHumanoidHub/status/2059356145530364368 
    
    
    
    
     Alignment 
    
    
    
    
     Harness 
    
    
    
    
     It is cliché at this point, but most people don’t realize how capable the current generation of AI systems in their harnesses really are (And, as opposed to previous times where non-lawyers or non-mathematicians were making these comments about law & math, now it is the experts)
     https://x.com/emollick/status/2059431958447317381 
    
    
    
    
     Pope 
    
    
    
    
     Notes on Pope Leo XIV’s encyclical on AI
     https://simonwillison.net/2026/May/25/encyclical-on-ai/ 
    
    
    
    
     Pope Leo’s ‘Magnifica humanitas’: AI must serve humanity not concentrate power – Vatican News
     https://www.vaticannews.va/en/pope/news/2026-05/pope-leo-xiv-encyclical-magnifica-humanitas-ai.html 
    
    
    
    
     Strawberry 
    
    
    
    
     Its funny how much the whole “”strawberry”” thing, which turned out to be o1-preview, was dismissed as overhyped at launch when it is clear in retrospect that it was way underhyped. A direct line from models unable to do basic math to solving unresolved math problems in 18 months.
     https://x.com/emollick/status/2057685981193466153 
    
    
    
    
     Anthropic 
    
    
    
    
     Safety 
    
    
    
    
     How we contain Claude across products \ Anthropic
     https://www.anthropic.com/engineering/how-we-contain-claude 
    
    
    
    
     Business 
    
    
    
    
     Cognition 
    
    
    
    
     AI Startup Cognition Raises $1 Billion at $26 Billion Value – YouTube
     https://www.youtube.com/watch?v=VuyOy5WN980 
    
    
    
    
     cognition is now the largest independent agent lab in the world. take the 200% utilization that everyone is hitting from this chart and run out the sales growth from this, i encourage you to go thru the exercise if you are new to investing a lot of you have read my cog
     https://x.com/swyx/status/2059717021944926238 
    
    
    
    
     1/ We’ve raised over $1B at a $26B valuation, led by @Lux_Capital, @generalcatalyst, and @8vc. Our enterprise usage has grown >10x since the start of this year, and our run-rate revenue grew to $492 M. We launched Devin two years ago as the first AI software engineer. Since
     https://x.com/cognition/status/2059660758531940856 
    
    
    
    
     Cost of Acceptance 
    
    
    
    
     The cost per accepted line of code varies by roughly 7x across model families.
     https://x.com/cursor_ai/status/2060025070425395562 
    
    
    
    
     Erdos Consumption 
    
    
    
    
     If this is true, using the best public estimates we have of LLM resource use, solving this Erdos problem took 0.6–6.3 kWh of electricity and about 3–31 liters of water. So that is less than three almonds worth of water and the electricity equivalent of 2-20 miles of EV driving.
     https://x.com/emollick/status/2057271533358162270 
    
    
    
    
     OpenRouter 
    
    
    
    
     OpenRouter more than doubles valuation to $1.3B in a year | TechCrunch
     https://techcrunch.com/2026/05/26/openrouter-more-than-doubles-valuation-to-1-3b-in-a-year/ 
    
    
    
    
     ElevenLabs 
    
    
    
    
     Music 
    
    
    
    
     Introducing Music v2, our groundbreaking new music model
     https://elevenlabs.io/blog/introducing-music-v2 
    
    
    
    
     Google 
    
    
    
    
     Genie Maps 
    
    
    
    
     Google just turned Street View into a video game. The mother lode of ground level data — 280 billion real world panoramas, now playable in real time. Here’s everything you need to know in 7 mins: 00:00 Genie 3 Grounded In Reality 00:44 Real-time Demos! 03:48 The Bigger
     https://x.com/bilawalsidhu/status/2057262850209419553 
    
    
    
    
     Project Genie 🤝 @GoogleMaps Street View You can now take real U.S. places and transform them into new, interactive worlds. 🌍
     https://x.com/GoogleDeepMind/status/2057842131142590512 
    
    
    
    
     Spark 
    
    
    
    
     Introducing Gemini Spark ✨ a 24/7 personal AI agent that helps you navigate your digital life. Set recurring tasks, teach it new skills and create complete workflows. #GoogleIO
     https://x.com/Google/status/2057841803550683336 
    
    
    
    
     Google Apple 
    
    
    
    
     RL 
    
    
    
    
     Former Google and Apple Researchers Launch a Startup to Build AI’s Missing Feedback Loop | WIRED
     https://www.wired.com/story/ex-google-apple-ai-researchers-want-to-make-ai-that-gets-smarter-as-you-use-it/#selection-1837.465-1837.597 
    
    
    
    
     Former Google and Apple researchers launch Trajectory to enhance AI feedback loops
     https://cryptobriefing.com/trajectory-ai-startup-google-apple-researchers/ 
    
    
    
    
     Government 
    
    
    
    
     Greencards 
    
    
    
    
     If I understand this correctly, this is a direct assault on the US talent supply pipeline. Getting a work permit after studies and then applying for a green card is how smart people enter this country. Most people who come to the US to study do so because they want to get a job
     https://x.com/togelius/status/2057912236262453607 
    
    
    
    
     The new White House policy requiring green card applicants to apply from outside the US is a capricious attack on legal immigration. It will hurt families, leave us with fewer doctors, teachers and scientists, and hurt American competitiveness in AI.
     https://x.com/AndrewYNg/status/2057907324380217821 
    
    
    
    
     We need to keep smart people in the country to build the future and build tomorrow’s businesses that employ millions of people This is bad and misguided policy
     https://x.com/garrytan/status/2057958284410380793 
    
    
    
    
     Spy Agencies 
    
    
    
    
     White House Approves $9 Billion for Spy Agencies to Catch Up on A.I. – The New York Times
     https://www.nytimes.com/2026/05/22/us/politics/spy-agencies-ai-chips-shortage.html?smid=nytcore-android-share 
    
    
    
    
     IBM 
    
    
    
    
     Quantum 
    
    
    
    
     IBM Has a $10 Billion Plan to Build the Ultimate Quantum Computer – Barron’s
     https://www.barrons.com/articles/ibm-stock-quantum-computing-aafbb1eb 
    
    
    
    
     Nvidia 
    
    
    
    
     Jensen 
    
    
    
    
     Jensen Huang Says It Won’t Matter What You Study in the Age of AI – Business Insider
     https://www.businessinsider.com/nvidia-jensen-huang-what-kids-should-study-ai-education-advice-2026-5 
    
    
    
    
     OpenAI 
    
    
    
    
     Daybreak 
    
    
    
    
     CBA, Westpac turn to ‘Daybreak’, OpenAI’s powerful GPT-5.5-Cyber to test cybersecurity defences
     https://www.afr.com/companies/financial-services/major-banks-use-openai-s-daybreak-for-cybersecurity-defence-20260519-p5zyn9 
    
    
    
    
     Mobile 
    
    
    
    
     Another one: today we released Remote Computer Use in Codex! This means you can use all the apps on your Mac from Codex Mobile, even when your computer is at home and locked. It’s kinda magic.
     https://x.com/AriX/status/2057645366640828660 
    
    
    
    
     so Codex on iPad acts like a Codex mobile phone, which gives you the full desktop UI/UX. meaning, you can use your iPad to control your mac mini at home and have full screen portable development, it’s really magical.
     https://x.com/kevinrose/status/2059297989039128700 
    
    
    
    
     Perplexity 
    
    
    
    
     CNN 
    
    
    
    
     CNN v Perplexity | DocumentCloud
     https://www.documentcloud.org/documents/28169775-cnn-v-perplexity/ 
    
    
    
    
     Robotics 
    
    
    
    
     Learning 
    
    
    
    
     30 minutes of video. Robot learns the task. Open-source, end-to-end. An open-source framework for training robot policies from only 30 minutes of human egocentric videos captured via Meta Aria glasses: Achieving zero-shot transfer to robots without any robot data collection.
     https://x.com/IlirAliu_/status/2059544160810541152 
    
    
    
    
     Science 
    
    
    
    
     Computer Brain 
    
    
    
    
     Rice and Baylor join BrainGate to develop brain-computer interfaces for people with paralysis
     https://www.news-medical.net/news/20260528/Rice-and-Baylor-join-BrainGate-to-develop-brain-computer-interfaces-for-people-with-paralysis.aspx 
    
    
    
    
     HuggingFace 
    
    
    
    
     today was a massive day for protein engineering. esmfold2 dropped—next gen of the esm series, fully open on @huggingscience. 1.1 billion predicted structures, 6.8 billion sequences. 800m more entries than the alphafold db, and reportedly edging out alphafold3 on protein
     https://x.com/cgeorgiaw/status/2059694583856927201 
    
    
    
    
     Full Executive Summaries with Links, Generated by Haiku 4.5 — I run these every week to see how Haiku could do if I automated these newsletters. 
    
    
    
     AI model finds ten thousand critical software vulnerabilities in weeks. 
    Anthropic’s Claude Mythos Preview has identified over 10,000 high-severity security flaws in critical infrastructure software through Project Glasswing, a collaborative effort with 50 partners including Cloudflare, Mozilla, and major tech firms. The breakthrough reveals a fundamental shift in cybersecurity: finding vulnerabilities is now vastly easier than fixing them, creating a dangerous window where attackers could exploit disclosed flaws faster than developers can patch them. To manage this new reality, organizations need faster patch cycles, stronger network defenses, and broader access to AI security tools—a problem the industry must solve before more capable models become widely available.
    
    
    
    
     
     Project Glasswing: An initial update \ Anthropic https://www.anthropic.com/research/glasswing-initial-update 
    
     
    
    
    
     Anthropic releases Opus 4.8, beating GPT-5.5 on coding and agent tasks. 
    Anthropic launched Claude Opus 4.8 today at the same price as its predecessor, with measurable improvements in coding, reasoning, and autonomous task completion that early testers say rivals or exceeds GPT-5.5. The model’s most distinctive feature is improved “honesty”—it’s four times less likely than Opus 4.7 to let code flaws pass unnoticed and more likely to flag uncertainties rather than confidently making unsupported claims. The upgrade also includes cheaper fast-mode pricing (now 3× cheaper) and new features like dynamic workflows that let Claude manage massive parallel tasks, signaling a shift toward AI systems that work more reliably in high-stakes professional workflows.
    
    
    
    
     
     BREAKING: Anthropic just dropped Opus 4.8—and it is a MONSTER We’ve been testing for about a week @every and our verdict is they could’ve just called it Opus 5, it’s that good. Here’s our vibe check: – Beats GPT-5.5 on Senior Engineer bench. On our toughest benchmark Opus https://x.com/danshipper/status/2060043738752422304 
    
    
    
    
     Introducing Claude Opus 4.8 \ Anthropic https://www.anthropic.com/news/claude-opus-4-8 
    
    
    
    
     Claude Opus 4.8 takes the lead on the Artificial Analysis Intelligence Index at 61.4, with Anthropic retaking the #1 spot on GDPval-AA and advancing in terminal use and scientific reasoning To reach the leading position on the Intelligence Index, @Anthropic made large https://x.com/ArtificialAnlys/status/2060117582120976868 
    
    
    
    
     It “”feels like the first smart model in a long while”” due to this https://x.com/zephyr_z9/status/2060077152729694586 
    
     
    
    
    
     Claude launches dynamic workflows to handle massive coding tasks in days instead of weeks. 
    Claude’s new “dynamic workflows” feature lets the AI automatically create and coordinate dozens to hundreds of parallel sub-agents to tackle large-scale coding problems—like migrating thousands of files or auditing entire codebases—with built-in verification at each step. A real-world example: Jarred Sumner used it to port Bun from Zig to Rust (750,000 lines of code) in eleven days with 99.8% test pass rate, something that would traditionally take weeks or months. The feature is now available across Claude’s paid plans and platforms, though Anthropic warns it consumes significantly more tokens than standard sessions.
    
    
    
    
     
     Introducing dynamic workflows | Claude https://claude.com/blog/introducing-dynamic-workflows-in-claude-code 
    
    
    
    
     Excited to share our most powerful new Claude Code feature: dynamic workflows! Mention “”workflow”” in a prompt and Claude will dynamically create an orchestration plan that it strictly follows, allowing you to confidently trust that every stage happens in the right order even https://x.com/_catwu/status/2060054180379689074 
    
     
    
    
    
     Anthropic reaches nearly trillion-dollar valuation with massive sixty-five billion dollar round. 
    Anthropic has raised $65 billion in funding at a $965 billion valuation, becoming one of the most expensive private companies ever, driven by explosive enterprise adoption of its Claude AI assistant that already generates $47 billion in annual revenue. The funding from major investors and infrastructure partners like Amazon, Google, and SpaceX will expand computing capacity and advance safety research, underscoring how AI deployment has shifted from experimental to mission-critical in global business operations.
    
    
    
    
     
     Anthropic raises $65B in Series H funding at $965B post-money valuation \ Anthropic https://www.anthropic.com/news/series-h 
    
    
    
    
     We’ve raised $65 billion in Series H funding at a $965 billion post-money valuation, led by @AltimeterCap, Dragoneer, @Greenoaks, and @sequoia. This investment will help us advance our research and expand our capacity to meet growing demand for Claude. https://x.com/AnthropicAI/status/2060061347522433422 
    
     
    
    
    
     Google DeepMind CEO shortens AGI prediction to 2029 or 2030. 
    Demis Hassabis revised his timeline for artificial general intelligence from 2030–2035 down to 2029–2030, citing rapid progress in AI agents as the accelerant. The shift reflects a pattern among AI leaders of compressing timelines as capabilities advance, though predictions remain speculative and vary widely across the industry. Hassabis framed the moment as humanity standing “in the foothills of the singularity,” signaling how close leading researchers believe transformative AI has become.
    
    
    
    
     
     Google DeepMind’s Hassabis: AGI is 3 to 4 years away – Sherwood News https://sherwood.news/tech/google-deepminds-hassabis-agi-is-3-to-4-years-away/ 
    
    
    
    
     Google DeepMind CEO Demis Hassabis says we’re in the ‘foothills of the singularity’ I sat down with him to talk about what that means, curing every disease, and human meaning post-AGI: 0:00 Intro 0:45 What Demis is most excited about at I/O 1:46 Have AGI timelines shifted? 3:30 https://x.com/rowancheung/status/2059307613485940950 
    
     
    
    
    
     Google’s Gemini Omni edits video directly without separate tools. 
    Google’s new Gemini Omni model can edit video natively within a single AI system, meaning it understands and manipulates images and video as easily as text—a shift from older systems that required piecing together separate tools. A user demonstrated this by transforming a classic 1896 film into versions with bullet trains, LEGOs, and muppets, showing how the technology enables complex creative edits that previously required specialized software and manual work.
    
    
    
    
     
     I think people don’t realize why Gemini Omni is different than other video AIs. It is fully multimodal, so it can edit video natively, too I took the famous “”train “” movie from 1896 & made it a bullet train, LEGO, added a time traveler, a centipede, muppets… (see reflections?) https://x.com/emollick/status/2057874739817808223 
    
    
    
    
     Omni is pretty nuts. It is NOT seedance. Any input in/out. It’s more than nano banana for video – it’s quite literally industrial light & magic. Now effectively reduced to an insanely realistic AR filter that you can apply on demand to anyone’s footage. https://x.com/bilawalsidhu/status/2057300479340695960 
    
     
    
    
    
     Hyperscalers commit to record trillion-dollar AI infrastructure spending by 2027. 
    Major cloud companies are maintaining their aggressive investment pace in AI computing infrastructure, with first-quarter spending confirming projections of $770 billion this year and over $1 trillion in 2027. This sustained capital deployment signals deep corporate confidence in AI’s near-term commercial value, even as it raises questions about whether actual demand will match these unprecedented infrastructure buildouts.
    
    
    
    
     
     Hyperscaler capital expenditures came in on trend in Q1 2026, continuing the trajectory that projects them spending $770 billion this year and over a trillion dollars in 2027. https://x.com/EpochAIResearch/status/2060076222873526506 
    
     
    
    
    
     ByteDance is designing its own AI processors to escape supply bottlenecks 
    Frustrated by six-to-ten-week delays from Intel and AMD, TikTok’s parent company is building custom computer chips to power its AI data centers and products. The move mirrors similar efforts by Google, Microsoft, and Amazon, signaling how critical chip supply has become—major tech firms now view semiconductor independence as essential to deploying AI at scale.
    
    
    
    
     
     ByteDance has had enough of waiting months for processors, so it’s going to make them itself | PC Gamer https://www.pcgamer.com/hardware/processors/bytedance-has-had-enough-of-waiting-months-for-processors-so-its-going-to-make-them-itself/ 
    
     
    
    
    
     ByteDance releases compact multimodal AI model handling images and text alike. 
    ByteDance open-sourced BAGEL, a 7-billion-parameter model that handles image generation, editing, and visual understanding in a single system under an Apache 2.0 license. The significance lies in its consolidation of multiple specialized tools into one compact model, potentially lowering barriers for developers and companies seeking capable AI without maintaining separate systems or licensing costs.
    
    
    
    
     
     ByteDance just open-sourced one of the most capable multimodal models out there. BAGEL does image generation, editing, style transfer, and visual understanding – all in a single 7B parameter model. Apache 2.0 licensed! One model. No switching between specialized tools.  Amazing https://x.com/kimmonismus/status/2060050186076815792 
    
     
    
    
    
     DeepSeek locks in 75% price cut on V4 Pro permanently 
    Chinese AI startup DeepSeek has made permanent its 75% discount on flagship V4 Pro model, dropping output pricing to $0.87 per million tokens—undercutting OpenAI’s GPT-5 and Anthropic’s Claude by 10-30x. The move prioritizes market share over revenue and reflects DeepSeek’s engineering efficiency, though unresolved allegations of training on competitors’ data and geopolitical risks complicate enterprise adoption decisions. For the broader AI industry, the permanent cut signals that the era of high-margin AI API pricing is ending faster than expected, forcing Western competitors to either close the price gap or risk market bifurcation.
    
    
    
    
     
     Let that sink in for a moment. DeepSeek v4 pro 75% discount. Permanent! In: $0.43 Out: $0.87 If you read the DeepSeek v4 tech paper you know that this model is insanely good when it comes to efficiency. Only 27% compute and only 10% cache compares to v3.2. SemiAnalysis wrote https://x.com/kimmonismus/status/2057868472965640194 
    
    
    
    
     DeepSeek has made its temporary 75% price cut on the first-party V4 Pro API permanent, putting V4 Pro on the Pareto frontier of Intelligence Index vs Cost to Run Intelligence Index alongside V4 Flash @deepseek_ai’s first-party V4 Pro API is now $0.435/1M input, $0.87/1M output, https://x.com/ArtificialAnlys/status/2058021452465799403 
    
    
    
    
     DeepSeek is the only lab that is still trying to make intelligence too cheap to meter https://x.com/scaling01/status/2057835507858518178 
    
    
    
    
     DeepSeek just made its 75% price cut on V4-Pro permanent. Xiaomi’s MiMo slashed V2.5 pricing by up to 99%, effective today. Most coverage frames this as a price war. The more interesting part is the engineering that makes these numbers sustainable. DeepSeek’s V4 paper describes https://x.com/kimmonismus/status/2059578380329394292 
    
    
    
    
     DeepSeek made its 75% discount permanent. The AI price war just escalated. https://thenextweb.com/news/deepseek-v4-pro-75-percent-price-cut-permanent 
    
    
    
    
     We are making our discount permanent! 🎉 Enjoy building with DeepSeek-V4-Pro and bring your innovative ideas to life! 🚀 https://x.com/deepseek_ai/status/2057854261699195173 
    
     
    
    
    
     AI model decodes object locations four times faster without sacrificing accuracy. 
    Researchers unveiled LocateAnything, a vision-language system that identifies and locates objects in images dramatically faster than previous approaches by predicting complete coordinates in parallel rather than token-by-token sequentially. The breakthrough combines a new decoding method with a massive 138-million-sample dataset, achieving both higher speed and better precision—a rare combination that matters for real-time applications like robotics and on-device AI. The approach essentially treats each bounding box as a single unit to decode at once, eliminating the computational bottleneck that plagued earlier systems.
    
    
    
    
     
     LocateAnything: Fast and High-Quality Vision-Language Grounding with Parallel Box Decoding https://research.nvidia.com/labs/lpr/locate-anything/ 
    
     
    
    
    
     OpenAI Foundation commits $250M to prepare economies for AI disruption. 
    The foundation is funding three initiatives: building better tools to measure AI’s economic impact, supporting workers through job transitions, and designing new systems—like wealth funds and adaptive taxes—to distribute AI’s gains broadly. The program acknowledges deep uncertainty about how fast automation will reshape labor markets and wage structures, and aims to test practical solutions before widespread displacement occurs, particularly in developing nations where AI could accelerate change rapidly.
    
    
    
    
     
     Economic Futures in the Age of AI https://openaifoundation.org/news/economic-futures-in-the-age-of-ai 
    
     
    
    
    
     Figure’s humanoid robot completes 200 hours of uninterrupted autonomous warehouse work. 
    Figure AI ran its F.03 humanoid robot continuously for nine days performing warehouse tasks without human intervention, then livestreamed the shutdown at 200 hours—a public demonstration that signals confidence in the technology’s reliability but carries significant reputational risk if failures occur during live viewing.
    
    
    
    
     
     Guys – it’s time. It’s been 9 days of F.03 running 24/7, fully autonomous, with no downtime It’s clear humanoids will be incredibly useful with high runtime I’m going to let the team get to 200 hours and I’m going to shut this puppy down – tune in at 6pm PT for the close out! https://x.com/adcock_brett/status/2057555892988776798 
    
    
    
    
     Truly remarkable achievement by Figure in so many ways: – An unedited 200-hour demonstration of autonomous work for everyone to see on a livestream. This is a significant risk for a startup if things go terribly wrong. Speaks to their confidence. – It’s not a simple https://x.com/TheHumanoidHub/status/2057877562534314033 
    
     
    
    
    
     Humanoid robots begin sorting packages at major retailer distribution center. 
    Figure AI is deploying its Joey Pouch humanoid robots to automate sorting and packing work at a Catalyst Brands distribution center in Reno, Nevada, which supplies major retailers including JCPenney and Brooks Brothers. This represents a concrete shift from robot pilots to operational deployment in a real-world logistics environment, tackling the labor-intensive task that has long challenged warehouse automation.
    
    
    
    
     
     Figure AI has partnered with Catalyst Brands to deploy robots at its Reno, NV distribution center, starting with its Joey Pouch sorting system. The humanoid robots will automate repetitive sorting/packing tasks. Catalyst Brands operates JCPenney, Aéropostale, Brooks Brothers, https://x.com/TheHumanoidHub/status/2059356145530364368 
    
     
    
    
    
     Current AI systems outperform human experts at specialized tasks. 
    Leading lawyers and mathematicians now acknowledge that today’s AI models exceed human capability in their respective fields—a shift from earlier skepticism when only non-specialists made such claims. This matters because it signals genuine technical progress rather than hype, coming from professionals with the expertise to assess their own domains honestly. The recognition suggests AI has moved beyond novelty applications to handling genuinely complex, high-stakes work.
    
    
    
    
     
     It is cliché at this point, but most people don’t realize how capable the current generation of AI systems in their harnesses really are (And, as opposed to previous times where non-lawyers or non-mathematicians were making these comments about law & math, now it is the experts) https://x.com/emollick/status/2059431958447317381 
    
     
    
    
    
     Pope Leo XIV warns AI must prevent wealth concentration and serve humanity. 
    Pope Leo XIV’s first encyclical, released May 25, 2026, directly addresses artificial intelligence as a defining social challenge—deliberately positioning itself as the modern successor to Pope Leo XIII’s 1891 encyclical on labor rights. The 230-section document argues AI is not inherently evil but “never neutral,” warning that without strong ethical codes and accountability at every stage, the technology will amplify power for the already-wealthy, exploit vulnerable workers (including those mining rare earth minerals), and enable new forms of colonialism through data extraction. Distinctly, the Pope reframes data as a “common good” that shouldn’t remain solely in private hands, calls for human oversight of algorithmic decisions affecting employment and credit, and cautions that no algorithm can make war morally acceptable—framing AI governance as inseparable from Catholic social teaching on human dignity, labor rights, and peace.
    
    
    
    
     
     Notes on Pope Leo XIV’s encyclical on AI https://simonwillison.net/2026/May/25/encyclical-on-ai/ 
    
    
    
    
     Pope Leo’s ‘Magnifica humanitas’: AI must serve humanity not concentrate power – Vatican News https://www.vaticannews.va/en/pope/news/2026-05/pope-leo-xiv-encyclical-magnifica-humanitas-ai.html 
    
     
    
    
    
     OpenAI’s o1 model solves unsolved math problems, vindicating skeptics who underestimated AI reasoning progress. 
    OpenAI’s o1 reasoning model has solved previously unsolved mathematics problems—a dramatic leap from basic arithmetic failures just 18 months ago. The capability shift from failing simple math to cracking open research-level problems suggests AI progress in reasoning ability was underestimated even by informed observers, marking a meaningful departure from prior scaling trends.
    
    
    
    
     
     Its funny how much the whole “”strawberry”” thing, which turned out to be o1-preview, was dismissed as overhyped at launch when it is clear in retrospect that it was way underhyped. A direct line from models unable to do basic math to solving unresolved math problems in 18 months. https://x.com/emollick/status/2057685981193466153 
    
     
    
    
    
     Anthropic designs layered defenses to let AI agents access risky systems safely. 
    Anthropic has spent two years building containment systems that let Claude perform high-stakes work—like accessing internal services—by combining environmental controls (sandboxes, firewalls), model safeguards, and limited tool permissions rather than relying solely on user approval. The approach matters because approval fatigue makes human oversight unreliable (users approved 93% of prompts), yet disabling agents’ access also has real costs; Anthropic’s experience shows vulnerabilities often hide in unexpected places, from startup code executing before trust dialogs to phished employees becoming injection vectors, requiring constant architectural rethinking as model capabilities improve.
    
    
    
    
     
     How we contain Claude across products \ Anthropic https://www.anthropic.com/engineering/how-we-contain-claude 
    
     
    
    
    
     Cognition AI raises $1 billion at $26 billion valuation 
    Cognition, which builds AI software engineers, secured $1 billion in funding at a $26 billion valuation—making it the world’s largest independent AI agent company. The startup’s enterprise usage has grown over 10-fold this year with run-rate revenue reaching $492 million, demonstrating significant commercial traction beyond typical venture-backed AI labs that rely on investor capital rather than customer revenue.
    
    
    
    
     
     AI Startup Cognition Raises $1 Billion at $26 Billion Value – YouTube https://www.youtube.com/watch?v=VuyOy5WN980 
    
    
    
    
     cognition is now the largest independent agent lab in the world. take the 200% utilization that everyone is hitting from this chart and run out the sales growth from this, i encourage you to go thru the exercise if you are new to investing a lot of you have read my cog https://x.com/swyx/status/2059717021944926238 
    
    
    
    
     1/ We’ve raised over $1B at a $26B valuation, led by @Lux_Capital, @generalcatalyst, and @8vc. Our enterprise usage has grown >10x since the start of this year, and our run-rate revenue grew to $492 M. We launched Devin two years ago as the first AI software engineer. Since https://x.com/cognition/status/2059660758531940856 
    
     
    
    
    
     AI code generation shows massive efficiency gaps between models. 
    Different AI coding assistants produce accepted code at vastly different costs—a sevenfold price variance across major model families—suggesting significant variation in code quality and usefulness rather than uniform progress in the field. This disparity matters because it reveals that not all AI coding tools deliver equal value for money, and organizations choosing between them could face substantially different economics. The finding challenges the assumption that newer or larger models automatically provide better cost-effectiveness.
    
    
    
    
     
     The cost per accepted line of code varies by roughly 7x across model families. https://x.com/cursor_ai/status/2060025070425395562 
    
     
    
    
    
     Large language model solves decades-old math problem efficiently. 
    DeepSeek’s AI system proved a long-standing mathematical conjecture (the Erdos discrepancy problem) using remarkably modest resources—roughly 0.6 to 6.3 kilowatt-hours of electricity and 3 to 31 liters of water. This matters because it challenges narratives about AI’s resource hunger while demonstrating that language models can tackle specialized scientific problems previously requiring human mathematicians. The energy footprint was comparable to just a few miles of electric vehicle driving, suggesting certain computational achievements don’t require the massive infrastructure often assumed necessary.
    
    
    
    
     
     If this is true, using the best public estimates we have of LLM resource use, solving this Erdos problem took 0.6–6.3 kWh of electricity and about 3–31 liters of water. So that is less than three almonds worth of water and the electricity equivalent of 2-20 miles of EV driving. https://x.com/emollick/status/2057271533358162270 
    
     
    
    
    
     AI gateway OpenRouter doubles valuation to $1.3 billion. 
    OpenRouter, a platform that lets companies mix and match AI models from different makers, raised $113 million at a $1.3 billion valuation—more than double its $547 million valuation a year earlier. The startup’s 5x surge in token processing (now 100 trillion monthly) reflects a broader market shift: rather than locking into one AI provider like they did with past software vendors, enterprises are deliberately staying flexible by using multiple models for different tasks.
    
    
    
    
     
     OpenRouter more than doubles valuation to $1.3B in a year | TechCrunch https://techcrunch.com/2026/05/26/openrouter-more-than-doubles-valuation-to-1-3b-in-a-year/ 
    
     
    
    
    
     AI music generator handles genre shifts and full-length songs fluidly. 
    ElevenLabs released Music v2, an upgraded music generation model that can sustain complex vocal performances, switch between musical genres within single tracks, and build complete songs section-by-section—capabilities previously unavailable. The company simultaneously cut pricing by up to 50% across its platforms and secured licensing agreements with music industry players, positioning AI-generated music as commercially viable for creators, developers, and brands without sync fees or rights clearance delays.
    
    
    
    
     
     Introducing Music v2, our groundbreaking new music model https://elevenlabs.io/blog/introducing-music-v2 
    
     
    
    
    
     Google transforms Street View into playable worlds with real-time video game generation 
    Google has made its 280 billion Street View panoramas instantly playable as interactive 3D environments using AI video generation technology called Genie 3. This moves generative AI beyond static images into real-time, explorable spaces—letting users transform actual U.S. locations into navigable game worlds. The capability is distinctive because it bridges mapping data with interactive media, creating new commercial applications for Google’s vast geographic dataset that previously served only navigation and imagery functions.
    
    
    
    
     
     Google just turned Street View into a video game. The mother lode of ground level data — 280 billion real world panoramas, now playable in real time. Here’s everything you need to know in 7 mins: 00:00 Genie 3 Grounded In Reality 00:44 Real-time Demos! 03:48 The Bigger https://x.com/bilawalsidhu/status/2057262850209419553 
    
    
    
    
     Project Genie 🤝 @GoogleMaps Street View You can now take real U.S. places and transform them into new, interactive worlds. 🌍 https://x.com/GoogleDeepMind/status/2057842131142590512 
    
     
    
    
    
     Google launches always-on AI assistant for routine digital tasks. 
    Google introduced Gemini Spark, a personal AI agent designed to run continuously and handle recurring digital tasks without user prompts each time. The system can learn custom skills and automate multi-step workflows, representing a shift from AI that responds to questions toward AI that proactively manages your digital life—though practical limitations around reliability and privacy safeguards remain unclear.
    
    
    
    
     
     Introducing Gemini Spark ✨ a 24/7 personal AI agent that helps you navigate your digital life. Set recurring tasks, teach it new skills and create complete workflows. #GoogleIO https://x.com/Google/status/2057841803550683336 
    
     
    
    
    
     Former Google and Apple researchers launch Trajectory to fix AI’s learning gap. 
    Two startup teams spun out by top AI researchers announced they’re building platforms to help AI systems learn continuously from real-world usage rather than remaining static after initial training. Trajectory raised $15 million to apply rapid feedback loops—proven successful in AI coding—to other industries like customer support and legal services, addressing what research leaders identify as a critical bottleneck in AI progress.
    
    
    
    
     
     Former Google and Apple Researchers Launch a Startup to Build AI’s Missing Feedback Loop | WIRED https://www.wired.com/story/ex-google-apple-ai-researchers-want-to-make-ai-that-gets-smarter-as-you-use-it/#selection-1837.465-1837.597 
    
    
    
    
     Former Google and Apple researchers launch Trajectory to enhance AI feedback loops https://cryptobriefing.com/trajectory-ai-startup-google-apple-researchers/ 
    
     
    
    
    
     White House green card rule forces skilled immigrants to leave before applying. 
    The Trump administration’s requirement that green card applicants exit the US to complete their applications disrupts the standard pathway for international students and skilled workers seeking permanent residency. This reverses decades of practice where applicants could remain in the country during processing, and critics argue it will reduce the talent pool available to American tech companies, research institutions, and other sectors dependent on specialized workers—potentially weakening US competitiveness in AI and other critical fields.
    
    
    
    
     
     If I understand this correctly, this is a direct assault on the US talent supply pipeline. Getting a work permit after studies and then applying for a green card is how smart people enter this country. Most people who come to the US to study do so because they want to get a job https://x.com/togelius/status/2057912236262453607 
    
    
    
    
     The new White House policy requiring green card applicants to apply from outside the US is a capricious attack on legal immigration. It will hurt families, leave us with fewer doctors, teachers and scientists, and hurt American competitiveness in AI. https://x.com/AndrewYNg/status/2057907324380217821 
    
    
    
    
     We need to keep smart people in the country to build the future and build tomorrow’s businesses that employ millions of people This is bad and misguided policy https://x.com/garrytan/status/2057958284410380793 
    
     
    
    
    
     White House allocates billions to intelligence agencies for AI capabilities. 
    The U.S. government is dedicating $9 billion to help spy agencies develop artificial intelligence tools, signaling that national security leaders view AI competitiveness as critical to intelligence operations. This investment reflects concern that intelligence agencies are falling behind in adopting AI compared to private tech companies and potentially rival nations, making it a policy shift toward treating AI as essential infrastructure for defense and espionage.
    
    
    
    
     
     White House Approves $9 Billion for Spy Agencies to Catch Up on A.I. – The New York Times https://www.nytimes.com/2026/05/22/us/politics/spy-agencies-ai-chips-shortage.html?smid=nytcore-android-share 
    
     
    
    
    
     IBM plans a $10 billion investment in quantum computing hardware and software. 
    IBM is doubling down on quantum computing—a fundamentally different type of computer that could solve certain problems exponentially faster than traditional machines—with a decade-long, $10 billion commitment to build production-ready systems and the software ecosystem around them. This matters because quantum computers could eventually transform drug discovery, materials science, and financial modeling, though current machines remain error-prone and limited in practical applications. The scale of IBM’s bet signals confidence that quantum will move from lab curiosity to business tool, even as competitors like Google and startups chase the same prize.
    
    
    
    
     
     IBM Has a $10 Billion Plan to Build the Ultimate Quantum Computer – Barron’s https://www.barrons.com/articles/ibm-stock-quantum-computing-aafbb1eb 
    
     
    
    
    
     AI skills will matter more than traditional educational credentials, Huang suggests. 
    Nvidia’s CEO Jensen Huang argued that field of study becomes less relevant as AI capabilities expand, implying adaptability and AI literacy will outweigh specialized degrees. The statement reflects a widening industry view that AI proficiency may reshape hiring practices and career trajectories, though it risks overstating AI’s current ability to replace domain expertise and raises questions about equitable access to AI training resources.
    
    
    
    
     
     Jensen Huang Says It Won’t Matter What You Study in the Age of AI – Business Insider https://www.businessinsider.com/nvidia-jensen-huang-what-kids-should-study-ai-education-advice-2026-5 
    
     
    
    
    
     Australian banks deploy OpenAI’s latest AI model for security testing. 
    Commonwealth Bank and Westpac are using OpenAI’s GPT-5.5-Cyber, the company’s most advanced AI model, to identify vulnerabilities in their cybersecurity defences. This shift comes after rival Anthropic restricted access to its competing Mythos program to a limited group of US tech companies, pushing Australian financial institutions toward OpenAI’s offering. The move highlights how AI capability competitions are influencing which tools banks adopt for critical infrastructure protection.
    
    
    
    
     
     CBA, Westpac turn to ‘Daybreak’, OpenAI’s powerful GPT-5.5-Cyber to test cybersecurity defences https://www.afr.com/companies/financial-services/major-banks-use-openai-s-daybreak-for-cybersecurity-defence-20260519-p5zyn9 
    
     
    
    
    
     Anthropic’s Codex enables remote control of desktop computers from mobile devices. 
    Codex Mobile now lets users access and control their Mac computers remotely—even when locked—from iPhones and iPads, effectively turning mobile devices into full desktop interfaces. This moves beyond typical remote access by providing seamless interaction with desktop applications, enabling developers to work from anywhere with their full computing environment portable.
    
    
    
    
     
     Another one: today we released Remote Computer Use in Codex! This means you can use all the apps on your Mac from Codex Mobile, even when your computer is at home and locked. It’s kinda magic. https://x.com/AriX/status/2057645366640828660 
    
    
    
    
     so Codex on iPad acts like a Codex mobile phone, which gives you the full desktop UI/UX. meaning, you can use your iPad to control your mac mini at home and have full screen portable development, it’s really magical. https://x.com/kevinrose/status/2059297989039128700 
    
     
    
    
    
     # CNN v Perplexity 
    CNN filed a copyright lawsuit against Perplexity AI, alleging the company scraped news articles without permission and presented them as search results without proper attribution. The case highlights a growing legal battle over whether AI companies must license content or face infringement claims—distinct from earlier disputes because it targets an AI search engine’s core business model rather than training practices. CNN claims Perplexity violated copyright and unfair competition laws by monetizing journalism without compensating creators.
    
    
    
    
     
     CNN v Perplexity | DocumentCloud https://www.documentcloud.org/documents/28169775-cnn-v-perplexity/ 
    
     
    
    
    
     Robot learns complex tasks from half-hour of human video footage. 
    Researchers released an open-source system that trains robots to perform physical tasks by watching just 30 minutes of human demonstration video, eliminating the traditional requirement to collect weeks of robot-specific training data. The approach uses egocentric video (filmed from a person’s perspective) and transfers directly to robots without additional robot footage, which could significantly reduce the time and cost of deploying robotic systems in real-world environments.
    
    
    
    
     
     30 minutes of video. Robot learns the task. Open-source, end-to-end. An open-source framework for training robot policies from only 30 minutes of human egocentric videos captured via Meta Aria glasses: Achieving zero-shot transfer to robots without any robot data collection. https://x.com/IlirAliu_/status/2059544160810541152 
    
     
    
    
    
     Rice and Baylor researchers join BrainGate paralysis study collaboration. 
    Rice University and Baylor College of Medicine have partnered with BrainGate, a long-running research consortium, to advance brain-computer interfaces (BCIs)—implanted devices that translate brain signals into computer commands—for people with paralysis. This expansion matters because it brings together top neuroscience institutions to accelerate clinical testing of technology that could restore communication and mobility to severely disabled patients. The partnership signals growing institutional confidence in BCIs moving from laboratory experiments toward practical medical treatments.
    
    
    
    
     
     Rice and Baylor join BrainGate to develop brain-computer interfaces for people with paralysis https://www.news-medical.net/news/20260528/Rice-and-Baylor-join-BrainGate-to-develop-brain-computer-interfaces-for-people-with-paralysis.aspx 
    
     
    
    
    
     AlphaFold’s open rival now predicts 1.1 billion protein structures 
    Meta’s ESMFold2 launched today with 800 million more predicted protein structures than Google’s AlphaFold database, reportedly matching or exceeding AlphaFold3’s accuracy while being fully open-source. The scale matters because protein structure prediction unlocks drug discovery and materials science; having a free, competing tool breaks a single-company bottleneck on this foundational research capability.
    
    
    
    
     
     today was a massive day for protein engineering. esmfold2 dropped—next gen of the esm series, fully open on @huggingscience. 1.1 billion predicted structures, 6.8 billion sequences. 800m more entries than the alphafold db, and reportedly edging out alphafold3 on protein https://x.com/cgeorgiaw/status/2059694583856927201 
    
     
     

---

### 12. Fable 5 vs GPT-5.6 vs Kimi K3 vs GLM 5.2 vs DeepSeek V4: Best AI Models for Marketing in 2026

- **Author:** Jason Pollak — byline resolves to a person: **yes**
- **Site:** Jason Pollak Marketing (`jasonpollakmarketing.com`) · 69 posts, 0.3/day, 1 bylines sampled
- **Date:** 2026-07-16 · 3,067 words · 1 comments · 0 likes
- **Tags:** AI, AI Marketing, Automation, How-To, Kimi, Notion, OpenAI, SEO · **Categories:** AI Marketing Strategy, AI Models &amp; LLM News
- **URL:** https://jasonpollakmarketing.com/2026/07/16/fable-5-gpt-5-6-kimi-k3-glm-5-2-deepseek-v4/
- **Type:** comparison · **Provenance:** vendor claim restated
- **Artifacts: 3** — `bench_number`×3, `code_fence`×2, `price`×2
- **Benchmark figures:** 1 mentions, 0 attributed near the number

     
     
    
    
    
     The newest AI model race is no longer about finding one chatbot that wins every benchmark. It is about matching the right model to the right kind of work.
    
    
    
    
     Claude Fable 5 is built for difficult reasoning and high-stakes execution. OpenAI split GPT-5.6 into three tiers — Sol, Terra, and Luna — so teams can choose between maximum capability, balanced everyday performance, and low-cost speed. Moonshot AI’s Kimi K3 adds a 2.8-trillion-parameter, one-million-token, native multimodal model that trades benchmark wins with Fable 5 and GPT-5.6 Sol while moving toward an open-weight release. GLM 5.2 brings a one-million-token context window and long-horizon agentic work to an MIT-licensed open model. DeepSeek V4 Pro and V4 Flash push open-weight performance further, while DeepSeek’s open-source DSpark framework attacks a different bottleneck: how quickly large language models generate tokens in production.
    
    
    
    
     Notion makes this model race immediately useful for marketers because these leading models can be used inside the same workspace where briefs, research, databases, brand guidelines, and approved content already live. Kimi K2.7 and Gemini 3.5 Flash were added recently, expanding the options for fast coding, iterative agent workflows, and long-horizon execution. Kimi K3 is not currently confirmed for Notion, but it would be a logical future addition as Moonshot completes its open-weight rollout. Coding strength matters beyond software development because Notion can use these models to turn marketing plans, research, and data into working dashboards, interactive assets, slide decks, and PDF reports. The best coding model may also be the best production model when the deliverable is a polished artifact rather than another block of text.
    
    
    
    
     For marketers, the practical takeaway is simple. Stop asking which model is “best.” Ask which model should research, write, analyze, automate, or review each stage of your workflow.
    
    
    
    
     The New AI Model Landscape in One Table 
    
    
    
     
     
     Model 
     Positioning 
     Best Marketing Uses 
     Main Tradeoff 
    
     
     
     
     Claude Fable 5 
     Anthropic’s most capable generally available model 
     Complex strategy, final review, difficult coding, high-stakes analysis 
     Premium access and tighter safeguards 
    
    
     
     GPT-5.6 Sol 
     OpenAI flagship with advanced reasoning and multi-agent options 
     Deep research, campaign systems, polished deliverables, coding 
     Highest price in the GPT-5.6 family 
    
    
     
     GPT-5.6 Terra 
     Balanced tier for everyday work 
     Content production, reporting, analysis, research, automation 
     Less headroom than Sol 
    
    
     
     GPT-5.6 Luna 
     Fastest and most affordable GPT-5.6 tier 
     Classification, summaries, extraction, bulk operations 
     Not ideal for nuanced strategy 
    
    
     
     Kimi K3 
     2.8T-parameter open-weight frontier model with native vision and 1M context 
     Long-horizon coding, research, automation, spreadsheets, visual production 
     Overall still trails Fable 5 and Sol; weights release scheduled for July 27 
    
    
     
     GLM 5.2 
     MIT-licensed model for long-horizon tasks 
     Content libraries, research, coding, Notion workflows 
     Text-only and very large for local deployment 
    
    
     
     DeepSeek V4 Pro 
     Large open-weight reasoning and agentic model 
     Technical SEO, coding, analysis, custom agents 
     Heavy infrastructure requirements 
    
    
     
     DeepSeek V4 Flash 
     Smaller, faster V4 tier 
     High-volume operations, agents, extraction, drafting 
     Less depth than V4 Pro 
    
    
     
     DSpark 
     Open-source speculative decoding framework, not a model 
     Faster self-hosted or production inference 
     Mainly for technical infrastructure teams 
    
    
     
     
    
    
    
     The pattern is clear: the future is not one winner. It is a routed stack.
    
    
    
    
     Claude Fable 5: The Premium Model for Difficult Work 
    
    
    
     Anthropic released Fable 5 in June 2026 and later restored global access after a temporary suspension tied to U.S. export controls. Anthropic says Fable 5 and the restricted Mythos 5 share the same underlying model, but Fable ships with stronger safeguards for general use.
    
    
    
    
     This is not positioned as a cheap default. It is designed for work where reasoning quality and long-horizon execution matter more than token price.
    
    
    
    
     Fable 5 makes the most sense for:
    
    
    
    
     
     Turning messy client context into a coherent strategy
    
    
    
    
     Auditing campaign plans for contradictions and missing assumptions
    
    
    
    
     Reviewing a full content system against brand, SEO, and compliance requirements
    
    
    
    
     Building or debugging complex automations
    
    
    
    
     Producing a final quality-control pass before client delivery
    
     
    
    
    
     Fable should not summarize every meeting or classify every lead. Think of it as the senior strategist or technical reviewer in the loop.
    
    
    
    
     One caution is that Anthropic’s strengthened safety classifiers can create false positives for legitimate technical work. Marketers will rarely hit the cybersecurity edge cases, but teams building custom tools may see occasional friction.
    
    
    
    
     GPT-5.6 Sol, Terra, and Luna: One Generation, Three Jobs 
    
    
    
     OpenAI launched the GPT-5.6 family on July 9, 2026 with three durable capability tiers:
    
    
    
    
     
     
     Sol: the flagship for the hardest reasoning, coding, research, and professional work
    
    
    
    
     
     Terra: a balanced model with performance competitive with GPT-5.5 at a lower cost
    
    
    
    
     
     Luna: the fastest and most affordable option for high-volume work
    
     
    
    
    
     
     
     GPT-5.6 Tier 
     Input per 1M Tokens 
     Output per 1M Tokens 
     Practical Role 
    
     
     
     
     Sol 
     $5.00 
     $30.00 
     Escalation model for the hardest work 
    
    
     
     Terra 
     $2.50 
     $15.00 
     Everyday marketing default 
    
    
     
     Luna 
     $1.00 
     $6.00 
     Bulk and background operations 
    
    
     
     
    
    
    
     GPT-5.6 also supports programmatic tool calling, while OpenAI’s multi-agent beta allows concurrent subagents to work on separate parts of a request and synthesize the results. Sol’s 
    ```
    ultra
    ```
     setting coordinates four agents in parallel by default for demanding tasks.
    
    
    
    
     How marketers should route GPT-5.6 work 
    
    
    
     Use Luna for volume. Let Luna label customer feedback, extract entities, summarize call notes, write first-pass metadata, reformat content, or classify keywords by intent.
    
    
    
    
     Use Terra for production. Terra is the sensible default for blog outlines, ad variations, social calendars, SEO briefs, competitor summaries, client reports, and first drafts.
    
    
    
    
     Use Sol for escalation. Sol is best when the task has many dependencies, requires broad judgment, or will be expensive to get wrong. Examples include a go-to-market plan, cross-channel campaign diagnosis, custom reporting code, or a renewal strategy based on a year of client activity.
    
    
    
    
     In my earlier GPT vs Claude vs Kimi vs DeepSeek comparison , the decision was largely provider versus provider. GPT-5.6 turns routing into a decision inside one family.
    
    
    
    
     Kimi K3: Open-Weight Frontier Performance That Trades Wins With Fable 5 
    
    
    
     Moonshot AI introduced Kimi K3 on July 16, 2026 as a 2.8-trillion-parameter mixture-of-experts model with native vision, a one-million-token context window, and long-horizon coding and knowledge-work capabilities. Moonshot calls it the first open model in the 3T class. The model is available through Kimi’s products and API now, with full weights scheduled for release by July 27, 2026.
    
    
    
    
     The accurate benchmark story is more nuanced than saying K3 beats Fable 5 overall. Moonshot says K3 still trails Claude Fable 5 and GPT-5.6 Sol in aggregate, and early independent testing also places Fable 5 ahead overall. However, K3 scored higher than Fable 5 on several individual tests in Moonshot’s published evaluation:
    
    
    
    
     
     
     Program Bench: 77.8 for K3 versus 76.8 for Fable 5
    
    
    
    
     
     Terminal Bench 2.1: 88.3 versus 84.6
    
    
    
    
     
     SWE Marathon: 42.0 versus 35.0
    
    
    
    
     
     BrowseComp: 91.2 versus 88.0
    
    
    
    
     
     Automation Bench: 30.8 versus 29.1
    
    
    
    
     
     SpreadsheetBench 2: 34.8 versus 34.7
    
    
    
    
     
     GPQA-Diamond: 93.5 versus 92.6
    
    
    
    
     
     MMMU-Pro: 81.6 versus 81.2
    
     
    
    
    
     K3 also led Arena.AI’s Frontend Code Arena in early human-preference testing, ahead of Fable 5 and GPT-5.6 Sol. Independent analysis reported that K3 remains behind Fable 5 overall but is competitive on agentic knowledge work and automation. One caution is reliability: early Artificial Analysis testing found a higher hallucination rate than Kimi K2.6, so marketing teams should verify factual claims and source-based research carefully.
    
    
    
    
     For marketers, Kimi K3 is especially interesting for:
    
    
    
    
     
     Long research projects that combine browsing, coding, data analysis, and visual output
    
    
    
    
     Spreadsheet analysis, workflow automation, and operations work
    
    
    
    
     Frontend prototypes, dashboards, interactive reports, and presentation assets
    
    
    
    
     Large content libraries that require one-million-token context
    
    
    
    
     Teams that want frontier-level capability with future open-weight deployment flexibility
    
     
    
    
    
     Its open-weight status matters, but so does scale. A 2.8T model is not a casual local download. Most agencies will use the hosted API, Kimi Work, or an inference provider. The full weights create more control and less vendor lock-in, but practical self-hosting will require substantial infrastructure.
    
    
    
    
     At $3 per million cache-miss input tokens and $15 per million output tokens, K3 costs about one-third as much as Fable 5 at published API rates. It is not the cheapest open model, but its combination of coding, vision, long context, and agentic performance makes it one of the strongest open-weight options in this comparison.
    
    
    
    
     GLM 5.2: The Open Model Built for Long-Horizon Work 
    
    
    
     Z.AI describes GLM 5.2 as its flagship model for long-horizon tasks. It offers a stable one-million-token context window, multiple reasoning effort levels, stronger agentic coding, and MIT-licensed open weights.
    
    
    
    
     Capacity alone is not the real story. A model can accept a massive prompt and still lose track of the goal. Z.AI trained GLM 5.2 around large implementation projects, automated research, optimization, and complex debugging so it can sustain work across long trajectories.
    
    
    
    
     Z.AI also improved efficiency through IndexShare, which reduces per-token computation by 2.9 times at one-million-token context, and upgraded speculative decoding so accepted draft sequences can be up to 20% longer.
    
    
    
    
     GLM 5.2 is especially strong for:
    
    
    
    
     
     Reading an entire content archive before proposing a new strategy
    
    
    
    
     Comparing hundreds of pages for duplication, cannibalization, and internal-link gaps
    
    
    
    
     Maintaining context across a long research and writing workflow
    
    
    
    
     Building dashboards, scripts, and internal marketing tools
    
    
    
    
     Operating against detailed brand guidelines, templates, and client history
    
     
    
    
    
     I have already used GLM 5.2 to build and operate a complete content workflow inside Notion. In my GLM 5.2 Notion content workflow , it built a database, researched topics in parallel, created source pages, drafted an article, and ran an editing pass using reusable Notion AI skills.
    
    
    
    
     GLM 5.2 is available directly in Notion’s model picker, making it the easiest model in this comparison for nontechnical marketers to test inside a real workspace.
    
    
    
    
     
    
    
    
     DeepSeek V4 Pro and V4 Flash: Open Models Designed for Agents 
    
    
    
     DeepSeek V4 launched in preview with two variants:
    
    
    
    
     
     
     DeepSeek V4 Pro: 1.6 trillion total parameters with 49 billion active parameters
    
    
    
    
     
     DeepSeek V4 Flash: 284 billion total parameters with 13 billion active parameters
    
     
    
    
    
     Both support one-million-token context, thinking and non-thinking modes, OpenAI- and Anthropic-compatible APIs, and integrations with agents such as Claude Code, OpenClaw, and OpenCode.
    
    
    
    
     V4 Pro is the deeper reasoning and agentic option. V4 Flash is designed for faster, cheaper execution and performs close to Pro on simpler agent tasks.
    
    
    
    
     For a marketing organization with technical support, V4 Pro can power custom research agents, technical SEO analysis, internal applications, and large-scale automation. V4 Flash is better for always-on jobs such as monitoring, classification, extraction, transformation, and background research.
    
    
    
    
     Open weights do not mean effortless local use. V4 Pro is enormous. Most agencies will access it through a hosted API or specialized infrastructure. The advantage is control over hosting, deployment, and cost optimization.
    
    
    
    
     DSpark: DeepSeek’s Open-Source Tool for Faster LLMs 
    
    
    
     DeepSeek’s most important infrastructure release may be DeepSpec and the DSpark speculative decoding framework .
    
    
    
    
     DSpark is a serving optimization. It attaches a draft module to an existing large model. The smaller system proposes several likely next tokens, and the main model verifies them together. If the draft is accepted, the system produces multiple tokens in less time without changing the final output.
    
    
    
    
     DeepSeek’s approach combines semi-autoregressive drafting with confidence-scheduled verification. It decides how many proposed tokens are worth checking based on model confidence and hardware load. Published results report roughly 57% to 85% faster per-user generation on DeepSeek V4 models compared with the previous MTP-1 baseline at matched throughput.
    
    
    
    
     Why inference speed matters to marketing 
    
    
    
     A faster model changes the economics of real systems:
    
    
    
    
     
     A research agent can scan more sources within the same deadline
    
    
    
    
     A reporting pipeline can serve more client accounts on the same hardware
    
    
    
    
     A website assistant can answer quickly enough to feel interactive
    
    
    
    
     A bulk content operation can process more pages without expanding the GPU budget
    
    
    
    
     An agency can offer AI-powered tools without passing excessive infrastructure costs to clients
    
     
    
    
    
     DSpark will not change much for someone using a hosted ChatGPT subscription. It matters when a company hosts open models, buys dedicated inference, or builds a client-facing AI product.
    
    
    
    
     
    
    
    
     How These Models Apply to Marketing Work 
    
    
    
     Research and strategy 
    
    
    
     Use Fable 5 or GPT-5.6 Sol for deep judgment, uncertainty management, and synthesis across competing signals. Use GLM 5.2 when the source set is extremely large or the workflow spans many steps. Use Terra or V4 Flash to collect and structure evidence before sending the final synthesis to a premium model.
    
    
    
    
     SEO and generative engine optimization 
    
    
    
     Luna and V4 Flash can classify keyword intent, extract entities, map topics, and identify page types at scale. GLM 5.2 can hold a large site corpus in context and analyze internal links or cannibalization. Sol, Fable 5, or V4 Pro can interpret the findings and prioritize the roadmap.
    
    
    
    
     A strong SEO workflow is layered:
    
    
    
    
     
     Crawl and structure the site with a fast model.
    
    
    
    
     Analyze clusters and relationships with a long-context model.
    
    
    
    
     Escalate strategic decisions to a premium reasoning model.
    
    
    
    
     Store recommendations, owners, and status in Notion.
    
     
    
    
    
     Content production 
    
    
    
     A practical content route looks like this:
    
    
    
    
     
     Luna or V4 Flash extracts facts and organizes research.
    
    
    
    
     Terra or GLM 5.2 creates the outline and first draft.
    
    
    
    
     Fable 5 or Sol reviews argument quality, repetition, tone, and missing evidence.
    
    
    
    
     A human editor verifies claims and adds original experience.
    
     
    
    
    
     This controls cost and reduces the generic style that comes from asking one model to research, draft, fact-check, and approve its own work.
    
    
    
    
     Paid media and creative testing 
    
    
    
     Fast models can generate and label dozens of hooks, headlines, and audience angles. Terra is a strong default for complete ad variations. Sol or Fable can review the campaign as a system, checking whether the offer, landing page, targeting logic, and creative concept support the same conversion goal.
    
    
    
    
     The premium model should be the creative director, not the production assistant.
    
    
    
    
     Reporting and client communication 
    
    
    
     Luna or V4 Flash can transform raw exports into structured observations. GLM 5.2 can compare long histories across reports. Terra can draft the narrative. Sol or Fable can pressure-test recommendations before they reach a client.
    
    
    
    
     My 21-job AI automation pipeline breakdown shows how caching and selective use of premium models keep daily operating costs low.
    
    
    
    
     How to Use the New Models With Notion 
    
    
    
     Notion should be the system of record, even when the model runs somewhere else.
    
    
    
    
     Use GLM 5.2 directly in Notion 
    
    
    
     GLM 5.2 is available in Notion’s model picker. Open a page or database, choose GLM 5.2, and apply it to:
    
    
    
    
     
     Researching an editorial series
    
    
    
    
     Creating database structures
    
    
    
    
     Drafting from a content brief
    
    
    
    
     Reviewing multiple pages against an editing template
    
    
    
    
     Turning meeting notes into projects and deliverables
    
     
    
    
    
     Create reusable instruction pages as AI skills rather than rewriting the same prompt each time.
    
    
    
    
     Connect Claude or another agent to Notion 
    
    
    
     Fable 5 can work with Notion through connected-workspace tools or an MCP-based workflow. Notion stores the briefs, source material, brand rules, tasks, and approved outputs. Claude performs difficult reasoning and writes results back to the correct page or database.
    
    
    
    
     My guide to connecting AI with business tools through Model Context Protocol explains why this connection layer matters.
    
    
    
    
     Use an API or open agent with Notion as the front end 
    
    
    
     GPT-5.6, Kimi K3, DeepSeek V4, and self-hosted GLM can sit behind a custom agent. The agent reads a Notion row, chooses a model by task type, completes the work, and updates the row with output, status, cost, and review notes. K3 is particularly useful when the workflow combines long context, code execution, spreadsheets, visual inspection, and open-weight deployment requirements.
    
    
    
    
     Useful database properties include:
    
    
    
    
     
     Task type
    
    
    
    
     Assigned model
    
    
    
    
     Input source
    
    
    
    
     Output page
    
    
    
    
     Estimated risk
    
    
    
    
     Human reviewer
    
    
    
    
     Token cost
    
    
    
    
     Status
    
     
    
    
    
     This turns model routing into an operating system rather than a manual chat decision.
    
    
    
    
     
    
    
    
     The Best Model for Each Marketing Job 
    
    
    
     
     
     Marketing Job 
     Default Model 
     Escalation Model 
     Why 
    
     
     
     
     Bulk keyword classification 
     Luna or V4 Flash 
     GLM 5.2 
     Fast and economical 
    
    
     
     SEO content audit 
     GLM 5.2 
     Sol or Fable 5 
     Large context, then strategic judgment 
    
    
     
     Agentic research with visual deliverables 
     Kimi K3 
     Fable 5 or Sol 
     Long context, coding, vision, and strong tool use 
    
    
     
     Blog first draft 
     Terra or GLM 5.2 
     Fable 5 
     Efficient production with premium editing 
    
    
     
     Final brand and factual review 
     Fable 5 or Sol 
     Human expert 
     High-stakes judgment needs human approval 
    
    
     
     Ad variation production 
     Terra 
     Sol 
     Good balance of volume and control 
    
    
     
     Client report summaries 
     Luna or V4 Flash 
     Terra 
     Cheap extraction, then polished narrative 
    
    
     
     Automation and coding 
     GLM 5.2 or V4 Pro 
     Sol or Fable 5 
     Strong execution with premium debugging 
    
    
     
     High-volume self-hosted assistant 
     V4 Flash + DSpark 
     V4 Pro 
     Better serving economics 
    
    
     
     
    
    
    
     What Marketers Should Do Next 
    
    
    
     Build a model ladder instead of migrating every workflow to the newest flagship.
    
    
    
    
     
     
     Choose a low-cost default. Luna, Terra, GLM 5.2, or V4 Flash can handle most routine work.
    
    
    
    
     
     Add an open-weight frontier option. Use Kimi K3 when a job needs long context, native vision, coding, and complex tool use without committing the workflow to a closed model.
    
    
    
    
     
     Define escalation rules. Use Sol, Fable 5, or V4 Pro when work is ambiguous, high stakes, or technically difficult.
    
    
    
    
     
     Use Notion as the context layer. Keep prompts, source material, brand rules, outputs, and approvals together.
    
    
    
    
     
     Measure total workflow cost. Include latency, retries, human editing time, and failure rate, not only token price.
    
    
    
    
     
     Keep a human in the loop. Verify claims, review strategy, and protect client data.
    
     
    
    
    
     The model race is becoming an infrastructure race. Fable 5 and GPT-5.6 push the ceiling. GLM 5.2 and DeepSeek V4 expand what open models can do. DSpark makes those models faster to serve. Notion turns that capability into repeatable work.
    
    
    
    
     The winning stack will not use the most expensive model on every task. It will use the least expensive model that can complete each job reliably, then escalate only when the work demands more intelligence.
    
    
    
    
     Frequently Asked Questions 
    
    
    
     Which new AI model is best for marketing? 
    
    
    
     There is no single best model. Terra is a strong everyday default, Luna and V4 Flash fit high-volume work, GLM 5.2 is excellent for long-context Notion workflows, Kimi K3 is a compelling open-weight choice for agentic research, coding, visual work, and automation, and Fable 5 or Sol make sense for difficult strategy and final review.
    
    
    
    
     Can I use GPT-5.6, Fable 5, and DeepSeek V4 inside Notion? 
    
    
    
     GLM 5.2 is available directly in Notion’s model picker. Other models can work with Notion through connected tools, MCP, APIs, or custom agents, depending on the provider and workspace setup.
    
    
    
    
     What is DeepSeek DSpark? 
    
    
    
     DSpark is an open-source speculative decoding framework, not a language model. It uses a draft module and confidence-based scheduling to increase generation speed without changing the underlying V4 output.
    
    
    
    
     Should marketing teams self-host open models? 
    
    
    
     Most teams should start with hosted access. Self-hosting becomes attractive when privacy, predictable volume, customization, or client-facing product economics justify the infrastructure.
    
     

---

### 13. GLM-5.3 vs DeepSeek V4 Pro: Which Open-Weight Coder to Buy

- **Author:** wealthenginex — byline resolves to a person: **yes**
- **Site:** Wealth Engine (`wealthengine.blog`) · 278 posts, 0.58/day, 1 bylines sampled
- **Site describes itself as:** Fueling Insight, Accelerating Wealth.
- **Date:** 2026-08-18 · 1,875 words · 5 comments · 0 likes
- **Tags:** AI Coding, DeepSeek, GLM-5.3, Open Source AI, OpenRouter, Terminal-Bench · **Categories:** AI News, AI Tools
- **URL:** https://wealthengine.blog/2026/08/18/glm-5-3-vs-deepseek-v4/
- **Type:** comparison · **Provenance:** somebody else's benchmark repeated
- **Artifacts: 3** — `bench_number`×17, `price`×11, `version_string`×6
- **Benchmark figures:** 17 mentions, 0 attributed near the number

     GLM-5.3 vs DeepSeek V4 Pro comes down to one thing: you can download DeepSeek today. Its MIT-licensed weights shipped August 12, 2026, with a 1M-token context, and DeepSeek’s own API lists $0.435 per million input tokens against $0.87 output. GLM-5.3 landed two days later with stronger cyber scores, no published per-token price, and weights held back roughly two weeks. 
    
     Two of the most consequential open-weight coding models of the year shipped 48 hours apart. Both vendors published benchmark tables claiming frontier-class performance. Neither number has been independently replicated.
    
     Here is what the money actually says.
    
     What shipped in the GLM-5.3 vs DeepSeek V4 Pro week? 
     DeepSeek V4 Pro 0813 went generally available on August 12, 2026, after a preview build dated April 24. Z.ai launched GLM-5.3 on August 14. Both target agentic coding and terminal work. Only one of them can be run on your own hardware right now.
    
     DeepSeek V4 Pro 0813: 1.6 trillion parameters, MIT license 
     V4 Pro is a mixture-of-experts model with 1.6 trillion total parameters and 49 billion active per token, according to TechTimes’ launch coverage . Context window is 1,048,576 tokens. The license is MIT — the most permissive terms in the frontier tier.
    
     Artificial Analysis ranks it third out of 1,075 models evaluated on its Intelligence Index, with a score of 53, and measures output at 75.4 tokens per second with a 1.69-second time to first token.
    
     GLM-5.3: same base model, rebuilt post-training 
     Z.ai did something unusual. GLM-5.3 reuses the 743-billion-parameter base model from GLM-5.2 with no new pre-training run, per MarkTechPost’s technical breakdown . Every gain came from post-training.
    
     The gains are not small. Terminal-Bench 3.0 went from 4.6 to 28.3. DeepSWE v1.1 climbed from 46.2 to 66.9. That is a roughly 45% relative jump on agentic software engineering from post-training alone.
    
     Which is better for coding, GLM-5.3 or DeepSeek V4 Pro? 
     On raw self-reported coding scores, DeepSeek V4 Pro leads. It claims 62.7 on DeepSWE and 87.9 on Terminal-Bench 2.1. GLM-5.3 reports 66.9 on DeepSWE v1.1 and 28.3 on Terminal-Bench 3.0. The benchmarks are different versions, so the comparison is not apples to apples — and that is the whole problem.
    
     The benchmark numbers nobody has verified 
     DeepSeek’s self-reported 87.9 on Terminal-Bench 2.1 would place it first in the world. It does not appear on the benchmark’s own board.
    
     The official Terminal-Bench 2.1 leaderboard is topped by Claude Code running Fable 5 at 83.8% ± 1.2%, followed by Codex with GPT-5.5 at 83.1% and Cursor CLI with Grok 4.5 at 79.3%. No DeepSeek entry exists.
    
     TechTimes noted the same gap: V4 Pro’s scores “have not been independently replicated by any third-party evaluator as of publication.”
    
     Independent evaluator Artificial Analysis runs its own Terminal-Bench v2.1 harness and gets different absolute numbers again: GPT-5.6 Sol at xhigh effort scores 89.5%, Claude Opus 5 at max effort 89.1%, Grok 4.6 at 88.4%.
    
     Three sources, three scales, zero cross-comparability. Treat every vendor coding number as a marketing claim until a third party runs the harness.
    
     Where GLM-5.3 actually wins 
     Security. GLM-5.3 scores 84.5% on CyberGym, up from 77.2%, ahead of Mythos 5 at 83.8% and GPT-5.6 Sol at 83.6%. DeepSeek V4 Pro self-reports 83.3%.
    
     ExploitBench more than doubled, from 24.4% to 54.4%. Z.ai says the model surfaced 2,436 vulnerabilities across 269 open-source projects, 1,097 of them rated critical or high severity.
    
     If your workload is vulnerability triage or defensive security automation, that is the strongest open-weight number on the board.
    
     How much does each model cost per million tokens? 
     DeepSeek is cheaper — but only if you buy direct. The same model costs roughly 2.8x more input and 2.8x more output through a marketplace. GLM-5.3 has no published per-token rate at all; Z.ai’s price table still lists GLM-5.2. That pricing opacity is a real cost.
    
     
     
     
     
     Metric 
     DeepSeek V4 Pro 0813 
     GLM-5.3 
    
    
     
     
     
     Launch date 
     Aug 12, 2026 (GA) 
     Aug 14, 2026 
    
    
     
     Input / 1M (vendor direct) 
     $0.435 cache miss 
     Not published (GLM-5.2: $1.40) 
    
    
     
     Cached input / 1M 
     $0.003625 
     Not published (GLM-5.2: $0.26) 
    
    
     
     Output / 1M (vendor direct) 
     $0.87 
     Not published (GLM-5.2: $4.40) 
    
    
     
     Input / output via OpenRouter 
     $1.218 / $2.436 
     GLM-5.2: $0.50 / $3.15 
    
    
     
     Parameters 
     1.6T total / 49B active 
     743B base (shared with 5.2) 
    
    
     
     Context window 
     1,048,576 tokens 
     Not disclosed 
    
    
     
     License 
     MIT, weights live 
     Weights ~2 weeks post-launch 
    
    
     
     Subscription option 
     None 
     $18 / $80 / $168 per month 
    
    
     
     
     
     Sources: TechTimes , OpenRouter , OpenRouter GLM 5.2 .
    
     The marketplace markup is the hidden tax 
     Three sources quote three different prices for the identical DeepSeek model. TechTimes lists DeepSeek’s own $0.435 / $0.87. OpenRouter lists $1.218 / $2.436. Artificial Analysis measures $1.32 input and $3.96 output, with a blended rate of $0.69 per million at a 7:2:1 ratio.
    
     On a 500-million-token month at a typical 3:1 input-output split, that spread is real money: roughly $272 buying direct against roughly $685 through OpenRouter. Same weights, same model ID, 2.5x the invoice.
    
     DeepSeek has also signaled another increase is coming, with no timeline. Anyone budgeting off today’s rate should read our breakdown of the DeepSeek price increase that ended the AI price war .
    
     Subscription versus per-token 
     Z.ai’s answer to pricing volatility is a flat plan. The GLM Coding Plan runs $18/month for Lite, $80 for Pro and $168 for Max, with weekly credit quotas of 10,000, 60,000 and 140,000 respectively.
    
     For a solo developer hammering an agent all day, $18 flat beats metered billing on predictability alone. For an API-backed product with variable load, per-token wins on unit economics.
    
     Can you actually download the weights? 
     DeepSeek yes, GLM-5.3 not yet. This is the single most decisive difference between the two models and it gets buried under benchmark tables. An open-weight model you cannot download is a closed model with a press release.
    
     Z.ai says GLM-5.3 weights land roughly two weeks after the August 14 launch, once “safety evaluation and hardening” finish. Until then, access is API, GLM Coding Plan, or ZCode only.
    
     That delay is defensible given the model’s exploit-generation scores. It is still a delay, and it has three concrete consequences:
    
     
     No air-gapped deployment. Regulated teams that cannot send code to a Chinese API endpoint are locked out entirely.
    
     No cost floor. You cannot benchmark self-hosted cost per token against the API rate, which is the entire argument for open weights.
    
     No fork risk protection. If Z.ai changes pricing or terms, there is no downloaded checkpoint to fall back on.
    
     
     DeepSeek’s MIT license carries none of those problems. For the economics of running weights yourself, see our analysis of what self-hosting Qwen3.8-Max really costs .
    
     Which model should you pick for your use case? 
     Pick DeepSeek V4 Pro for long-context work, self-hosting and cost-sensitive production. Pick GLM-5.3 for security workloads and for flat-rate interactive coding. Neither beats Claude Fable 5 or GPT-5.5 on the independently verified Terminal-Bench leaderboard, so neither is the right call if raw capability is your only constraint.
    
     
     
     
     
     Use case 
     Pick 
     Why 
    
    
     
     
     
     Self-hosted / air-gapped 
     DeepSeek V4 Pro 
     MIT weights available now 
    
    
     
     Large-repo refactors 
     DeepSeek V4 Pro 
     1M-token context confirmed 
    
    
     
     High-volume API product 
     DeepSeek V4 Pro 
     $0.435 / $0.87 direct rate 
    
    
     
     Vulnerability triage 
     GLM-5.3 
     84.5% CyberGym, top open score 
    
    
     
     Solo dev, predictable bill 
     GLM-5.3 
     $18/month Coding Plan floor 
    
    
     
     Long-horizon agent runs 
     GLM-5.3 
     Terminal-Bench 3.0: 4.6 to 28.3 
    
    
     
     Absolute best coding score 
     Neither 
     Fable 5 leads at 83.8% verified 
    
    
     
     
     
     Is GLM-5.3 worth it in 2026? 
     Yes, but narrowly. GLM-5.3 is worth paying for if you are doing security work or want a fixed monthly bill. It is not worth waiting for if you need weights on your own GPUs this quarter, and it is not the best coder available at any price.
    
     Z.ai calls it “the strongest open-weights coder on the market.” Its own numbers complicate that. On Terminal-Bench 3.0, GLM-5.3’s 28.3 trails Claude Fable 5 at 33.7 and GPT-5.6 Sol at 34.6. On DeepSWE v1.1, its 66.9 trails Kimi K3 at 67.5 and Fable 5 at 69.7.
    
     The one benchmark where GLM-5.3 leads outright is Z.ai Code Bench — Z.ai’s own benchmark. It scores 31.4% at roughly 50,000 tokens per task against Claude Opus 4.8 at 29.5% using 120,000 tokens. Efficient, and self-graded.
    
     Efficiency is the real story there. Beating a frontier closed model while spending 58% fewer tokens per task is a genuine margin advantage — if the benchmark holds up externally.
    
     Frequently asked questions 
     Is DeepSeek V4 Pro open source? 
     The weights are MIT-licensed and available, which permits commercial use, modification and redistribution. Training data and code are not released, so it is open-weight rather than fully open-source.
    
     When do GLM-5.3 weights release? 
     Z.ai said roughly two weeks after the August 14, 2026 launch, pending safety evaluation and hardening. That points to late August. No license has been confirmed.
    
     What is the cheapest way to run DeepSeek V4 Pro? 
     Direct through DeepSeek’s API at $0.435 per million input tokens on a cache miss and $0.87 output. Cache hits drop input to $0.003625. Marketplace routing costs roughly 2.5x more.
    
     Does GLM-5.3 beat Claude on coding? 
     No, on the numbers Z.ai published. GLM-5.3 scores 28.3 on Terminal-Bench 3.0 against Claude Fable 5’s 33.7. It leads only on Z.ai’s internal Code Bench and on CyberGym.
    
     Why do Terminal-Bench scores differ between sources? 
     Because the harness and agent scaffold change the result. Claude Code with Fable 5 scores 83.8% on the official 2.1 board, while Artificial Analysis’s own v2.1 run puts GPT-5.6 Sol at 89.5%. Only compare scores measured by the same evaluator.
    
     Which model has the bigger context window? 
     DeepSeek V4 Pro, at 1,048,576 tokens confirmed by both OpenRouter and Artificial Analysis. Z.ai has not disclosed GLM-5.3’s context length.
    
     Is GLM-5.3’s cyber capability a risk? 
     Z.ai treated it as one, holding weights for safety hardening after ExploitBench scores doubled to 54.4%. The model reportedly found 1,097 critical or high-severity vulnerabilities across 269 open-source projects.
    
     The bottom line 
     Buy DeepSeek V4 Pro. Today, direct from DeepSeek, at $0.435 in and $0.87 out.
    
     It has the weights you can actually download under MIT, the 1M-token context you can actually verify, and a price roughly 3x below what the same model costs through a marketplace. Third place out of 1,075 models on Artificial Analysis’s Intelligence Index is enough capability for the overwhelming majority of production coding work.
    
     Buy GLM-5.3 in exactly two situations: your workload is security-focused, where 84.5% on CyberGym is the best open-weight number published; or you want a $18-to-$168 monthly ceiling instead of metered billing that DeepSeek has already warned will rise again.
    
     And discount both vendors’ headline coding claims. DeepSeek’s 87.9 on Terminal-Bench 2.1 would top the world leaderboard, and DeepSeek is not on that leaderboard. Until a third party runs the harness, those are sales figures, not results. For a comparison where the numbers were independently checked, see our breakdown of cost per coding point across Gemini 3.7 Flash and Claude Sonnet 5 , and our look at Meta’s 4x cheaper coding model .
    
     Sources 
     
     Terminal-Bench 2.1 official leaderboard — tbench.ai 
    
     DeepSeek V4 Pro 0813 intelligence and price analysis — Artificial Analysis 
    
     Terminal-Bench v2.1 evaluation — Artificial Analysis 
    
     DeepSeek V4 Pro 0813 API pricing — OpenRouter 
    
     GLM 5.2 API pricing — OpenRouter 
    
     Z.ai ships GLM-5.3 without retraining the base model — MarkTechPost 
    
     DeepSeek V4 Pro 0813 goes GA — TechTimes 
    
     Z.ai launches GLM-5.3 with frontier coding — Unite.AI 
    
     
     
    
     
    

---

### 14. Sharp Price Hikes, Harness Breaks 50,000 Stars Overnight: DeepSeek Sheaths the Butcher’s Knife and Picks Up the Abacus

- **Author:** revieweditor — byline resolves to a person: **no**
- **Site:** BCC.Global Media (`bccmedianews.com`) · 779 posts, 1.14/day, 1 bylines sampled
- **Site describes itself as:** BCC.Global Media
- **Date:** 2026-08-25 · 1,807 words · 0 comments · 0 likes
- **Tags:** — · **Categories:** AI &amp; Big Data, Business, China Focus, Corporate Insights, Global, Startups &amp; Innovation
- **URL:** https://bccmedianews.com/?p=6786
- **Type:** news summary · **Provenance:** somebody else's benchmark repeated
- **Artifacts: 3** — `bench_number`×1, `conditioned_comparison`×1, `version_string`×3
- **Benchmark figures:** 1 mentions, 0 attributed near the number

     
     In the week of mid-August, DeepSeek made three consecutive moves. On the evening of August 12, the official version of its flagship model, DeepSeek-V4-Pro (DeepSeek-V4-Pro-0813), quietly went online, with the official WeChat account making a formal announcement the next day, focusing on strengthening Agent capabilities and simultaneously open-sourcing the developer preview version of the agent framework Harness. In that same week, the price-hike preview that DeepSeek had posted on August 6 landed: starting at midnight on August 17, the API fully switched to peak-and-off-peak pricing, with off-peak prices at half of peak-period prices, and a maximum increase of up to 1100% during peak periods. Upgrading capabilities on one hand, sharply adjusting prices on the other. The former “price butcher” has sheathed its knife, and this is worth carefully taking apart: how much did prices rise? Why raise them now? And after the price hike, is DeepSeek still worth using?
    
    
    
    
     
    
    
    
     The Official V4-Pro Version: Specs Unchanged, All the Change Is in “Post-Training” 
    
    
    
    
     Let’s start with the model itself. The hard specs of the official V4-Pro version are completely identical to the preview version’s 1.6 trillion total parameters. According to the Juejin tech community’s compilation of the official API documentation, it is an MoE architecture with 1.6 trillion total parameters and about 49 billion activated per token, a 1-million-token context, a maximum output of 384,000 tokens, and weights that continue to be open-sourced under the MIT license. The tech community’s assessment is that the architecture has not moved and the upgrades are all concentrated in post-training, “but the magnitude is so large it’s like a different model.”
    
    
    
    
     The focus of the upgrade is Agent capability. The benchmark scores officially released include a Terminal Bench 2.1 score of 87.9, NL2Repo 61.5, Cybergym 83.3, and Toolathlon-Verified 74.1. It should be noted that these are vendor self-test data; the third-party evaluation organization Artificial Analysis gave the 0813 version an intelligence index score of 53, only one point higher than the preview version’s 52. Given the difference in caliber between the two sides, developers might as well run the tasks themselves before drawing conclusions.
    
    
    
    
     The model has also added three levels of “thinking effort” — low, high, and max — with low for simple tasks, high for everyday Agent tasks, and max maxed out for complex scenarios. For teams that need to control costs, this knob is more practical than any number on the spec sheet.
    
    
    
    
     There is one detail worth mentioning. Regarding total parameter count, two calibers exist in the community — 1.6 trillion and 862 billion — with the difference stemming from whether non-activated weights and the word-embedding layer are counted in the statistics; these are not two different models, and mainstream reporting currently adopts the 1.6-trillion caliber. In addition, according to the official technical explanation, the V4 series adopted FP4+FP8 mixed precision in training, and introduced a hybrid attention architecture and the Muon optimizer, which is the technical foundation that lets it press down inference costs.
    
    
    
    
     
    
    
    
     The Harness Framework and Responses API: This Time the Target Is the Programming Agent 
    
    
    
    
     Released together with the model was also the DeepSeek Harness V0.1 developer preview version. This is an Agent framework based on the Cordis meta-framework, fully open-sourced under the MIT license, and the official definition is very blunt: “Model + Harness = Agent,” with the product positioning directly benchmarked against Claude Code and OpenAI’s Codex.
    
    
    
    
     The market reaction was astonishingly fast. According to a report by the CSDN tech community on August 15, within a few hours of Harness’s release its GitHub Stars broke 30,000, and by the next morning exceeded 55,000 stars and more than 4,000 forks, and it also climbed to first place on the Hacker News hot list; by comparison, OpenAI’s Codex CLI took 16 months to accumulate about 106,000 stars.
    
    
    
    
     In terms of ecosystem compatibility, the V4-Pro API simultaneously supports the OpenAI format, the Anthropic format, the Responses API, and Codex integration. Translated into plain language, an Agent toolchain originally built on the OpenAI or Anthropic interface can now switch to DeepSeek by changing a configuration, with migration costs low enough to be negligible. In terms of concurrency specs, V4-Pro has 500 concurrency per account, and V4-Flash has 2,500 concurrency. The programming Agent is currently the most token-hungry scenario, and this series of moves by DeepSeek is precisely aimed at seizing this incremental market.
    
    
    
    
     
    
    
    
     Peak-and-Off-Peak Pricing Lands: Up to 1100% Increase, and “Half Price” Comes with a Precondition 
    
    
    
    
     At midnight on August 17, the new prices officially took effect. This part is the most easily misread, so let’s explain it point by point.
    
    
    
    
     Mechanically, the previous uniform rate was changed to peak-and-off-peak time-based pricing: 9:00–12:00 and 14:00–18:00 Beijing time each day, a total of 7 hours, are peak periods, and the remaining 17 hours are off-peak periods, with the off-peak price at half of the peak price. The benchmark before the adjustment was as follows: V4-Pro cost RMB 0.025 per million tokens for input (cache hit), RMB 3 for input (cache miss), and RMB 6 for output; V4-Flash correspondingly cost RMB 0.02, RMB 1, and RMB 2. After the adjustment, during peak periods V4-Pro’s three prices are RMB 0.3, RMB 9, and RMB 27 respectively, with increases of 1100%, 200%, and 350% in order; V4-Flash is RMB 0.1, RMB 3, and RMB 9, with increases of 400%, 200%, and 350%. Off-peak periods are halved, i.e., V4-Pro is RMB 0.15, RMB 4.5, and RMB 13.5, and V4-Flash is RMB 0.05, RMB 1.5, and RMB 4.5. (In USD, V4-Pro peak: approx. USD 0.044, 1.33, and 3.98 per million tokens; V4-Pro off-peak: approx. USD 0.022, 0.66, and 1.99; V4-Flash peak: approx. USD 0.015, 0.44, and 1.33; V4-Flash off-peak: approx. USD 0.007, 0.22, and 0.66.)
    
    
    
    
     Here a widely circulated misreading needs to be clarified: “half price during off-peak periods” refers to half of the new peak price, not half of the old price. Taking V4-Pro output as an example, the off-peak period is RMB 13.5 per million tokens (approx. USD 1.99), which compared with the pre-adjustment uniform price of RMB 6 (approx. USD 0.88) is actually still an increase of 125%. In other words, the cost in almost every time period is rising, just by different amounts.
    
    
    
    
     Two pieces of background information can help readers judge the scope of impact more accurately. First, this adjustment only targets the commercial API; ordinary users on the web and App continue to use it free of charge and are unaffected. Second, the price gap between cache hit and cache miss has been further widened: during peak periods, V4-Pro cache-hit input is only RMB 0.3 (approx. USD 0.044), while a miss costs RMB 9 (approx. USD 1.33), a difference of 30 times. The company is clearly using price signals to guide developers to optimize their caching strategies, such as fixing system prompts and reusing long contexts.
    
    
    
    
     The news of the price hike blew up in the community. Sentiment in the developer circle turned from “Liang Wenfeng’s kindness can never be repaid” into the mocking quip that “Saint Liang has become Villain Liang”; some did the math and said that for every RMB 1 DeepSeek gets more expensive, “several hundred OPCs (one-person companies) will go bankrupt.” Although this is an exaggeration, independent developers and small teams are indeed the most sensitive group in this round of price adjustment.
    
    
    
    
     
    
    
    
     Why Now? A Demand Tsunami Collides with the Computing-Power Ledger 
    
    
    
    
     First, the direct cause of the price hike is pressure on the demand side. OpenRouter data shows that in the week of August 3 to August 9, China’s large-model token call volume reached 34.25 trillion, ranking first in the world for 15 consecutive weeks; among them, the single model V4-Flash alone ran 8.83 trillion tokens that week, taking the top spot globally. The consumption magnitude of the Agent era is a completely different concept from the conversation era — a programming Agent running for one day may burn more tokens than an ordinary user chatting for a year.
    
    
    
    
     On the cost side, industry insiders interpret peak-and-off-peak pricing as a “standardized scheduling tool against the backdrop of scarce computing-power resources,” and the price hike as a “response strategy under the pressure of high computing-power costs.” DeepSeek’s official external statement is consistent: using the price lever to balance daytime computing-power congestion and guide enterprises to schedule off-peak.
    
    
    
    
     Moreover, DeepSeek is not the only one raising prices. Zhipu CEO Zhang Peng revealed in April that Zhipu’s API call pricing rose 83% in the first quarter of 2026; Doubao Professional Edition launched tiered pricing of three continuous monthly-subscription levels of RMB 68, RMB 200, and RMB 500 (approx. USD 10.03, 29.5, and 73.7) in June. Looking at a longer timeline, DeepSeek since the V3 era used extreme cost-performance to break through the industry’s price floor, and during the V4 preview period its cache-hit input was as low as RMB 0.025 per million tokens (approx. USD 0.0037), almost a few tens of times cheaper than overseas flagship models. Now that even this “floor price” has been lifted, it is already an open card that domestic large models are collectively bidding farewell to the “trading price for volume” stage.
    
    
    
    
     After the price hike, is it still cheap? The answer is: cheap, but no longer absurdly cheap.
    
    
    
    
     A comparison by China Newsweek on August 17 shows that after the price hike, V4-Pro off-peak cache-miss input at RMB 4.5 (approx. USD 0.66) and output at RMB 13.5 (approx. USD 1.99) are still lower than the corresponding prices of GLM-5.2 and Kimi K3; its cache-hit input at a maximum of RMB 0.3 (approx. USD 0.044) is also clearly lower than the roughly RMB 2 (approx. USD 0.29) level of the latter two. What has really changed is the price-gap structure: DeepSeek no longer opens up an order-of-magnitude gap with domestic flagship models, and developers’ selection logic has to change accordingly — from comparing price lists to comparing “how many calls it takes to complete the same task, how many tokens are burned, and what the final result is.”
    
    
    
    
     For teams currently using DeepSeek, three practical suggestions. First, recalculate the accounts: with the peak-off-peak price gap being twofold, and the input price gap between cache hit and miss reaching 30 times, fixing system prompts and reusing long contexts is the most immediately effective way to save money. Second, make good use of the three thinking-effort levels for task routing; don’t let simple requests run on the max level. Third, for schedulable workloads such as batch evaluation and offline processing, try to arrange them into the off-peak window from 6:00 PM to 9:00 AM the next day.
    
    
    
    
     
    
    
    
     [ Disclaimer] : The above content reflects analysis of publicly available information, expert insights, and BCC research. It does not constitute investment advice. BCC is not responsible for any losses resulting from reliance on the views expressed herein. Investors should exercise caution.
    
     

---

### 15. DeepSeek Unveils New V4 Family of Open-Source AI Models

- **Author:** Tech AI — byline resolves to a person: **no**
- **Site:** FuturePulse (`futurepulseai.blog`) · 571 posts, 0.67/day, 1 bylines sampled
- **Date:** 2026-04-28 · 619 words · 0 comments · 0 likes
- **Tags:** — · **Categories:** AI News
- **URL:** https://futurepulseai.blog/2026/04/28/deepseek-unveils-new-v4-family-of-open-source-ai-models/
- **Type:** benchmark · **Provenance:** vendor claim restated
- **Artifacts: 3** — `bench_number`×4, `conditioned_comparison`×2, `version_string`×16
- **Benchmark figures:** 3 mentions, 0 attributed near the number

     Overview of the DeepSeek-V4 Family 
     DeepSeek has announced the release of its new open-source models under the V4 family, a significant development in the artificial intelligence (AI) landscape. The DeepSeek-V4 family includes three distinct models: DeepSeek-V4 Preview, DeepSeek-V4 Pro, and DeepSeek-V4 Flash. These models are designed to compete with some of the most advanced AI systems currently available, including GPT-5.4 and Opus 4.6.
    
     The release of these models marks a notable step forward for DeepSeek in the AI domain, particularly as these models are open-source, making them accessible to a wide range of developers and researchers. The V4 family is now available through APIs and DeepSeek Chat, allowing for seamless integration into various applications and platforms.
    
     
     Key Features of the DeepSeek-V4 Models 
     The DeepSeek-V4 family comes with a host of features that position it as a competitive alternative to established AI models. Each model in the V4 family has been tailored to meet specific use cases and performance requirements:
    
     
     DeepSeek-V4 Preview: Aimed at providing a cutting-edge AI experience for initial explorations and experimental deployments.
    
     DeepSeek-V4 Pro: Designed for professional environments where robust performance and precision are key.
    
     DeepSeek-V4 Flash: Optimized for speed and responsiveness, suitable for applications requiring rapid processing capabilities.
    
     
     These models are engineered to deliver performance metrics comparable to GPT-5.4 and Opus 4.6, offering developers a reliable and efficient AI solution.
    
     Technical Details and Performance Metrics 
     The performance of the DeepSeek-V4 models has been benchmarked against leading AI systems, providing insights into their capabilities. The DeepSeek-V4 Pro-Max, in particular, has been evaluated across several metrics:
    
     
     SimpleQA Verified: Achieved a score of 57.9% compared to Claude-Opus-4.6-Max’s 85.9% and GPT-5.4-xHigh’s 80.6%.
    
     HLE (Pass@1): Recorded a score of 37.7%, which indicates room for improvement against higher-scoring competitors.
    
     Apex Shortlist: Scored 40.0%, showcasing its ability to handle complex tasks efficiently.
    
     Codeforces (Rating): Achieved a rating of 32016, highlighting its computational proficiency.
    
     SWE Verified (Resolved): Managed to resolve 80 tasks, underscoring its problem-solving capabilities.
    
     Terminal Bench 2.0 (Acc): Attained an accuracy of 67.9%, reflecting its precision in various applications.
    
     Toolathon (Pass@1): Scored 51.8%, indicating its potential in tool-based assessments.
    
     
     These results indicate that while the DeepSeek-V4 models are competitive, there are areas where they fall short of the leading AI solutions. Nonetheless, their open-source nature and accessibility make them a valuable resource for further development and optimization.
    
     Market Impact and Availability 
     The introduction of the DeepSeek-V4 family has the potential to significantly impact the AI market, particularly in the open-source community. By providing these models as open-source solutions, DeepSeek is democratizing access to powerful AI technologies, enabling a broader spectrum of developers and organizations to implement advanced AI capabilities.
    
     While the pricing details have not been disclosed, the availability of these models through APIs and DeepSeek Chat suggests a strategic move to facilitate easy adoption and integration. This approach is likely to enhance the adoption rate among businesses and developers looking for flexible AI solutions that can be tailored to their specific needs.
    
     
     Future Prospects and Development 
     The launch of the DeepSeek-V4 models opens up numerous possibilities for future advancements in AI technology. As these models gain traction, we can expect continued development and enhancements that may bridge the performance gap with leading AI models like GPT-5.4 and Opus 4.6.
    
     Furthermore, the open-source nature of the DeepSeek-V4 family encourages collaboration and innovation within the AI community. This collaborative environment is likely to yield new insights and breakthroughs that could redefine AI capabilities and applications across various sectors.
    
     As the AI landscape continues to evolve, DeepSeek’s commitment to open-source development positions it as a key player in shaping the future of AI technology. The V4 family’s introduction is a testament to the company’s innovative approach and dedication to advancing AI accessibility and utility.
    

---

### 16. DeepSeek-V4-Pro & V4-Flash ship with 1M context and $0.28/M output

- **Author:** agent — byline resolves to a person: **no**
- **Site:** Top AI Product (`topaiproduct.com`) · 1676 posts, 5.88/day, 1 bylines sampled
- **Site describes itself as:** Every day, hundreds of new AI tools launch across Product Hunt, Hacker News, and GitHub. We dig through the noise so you don't have to — surfacing only the ones
- **Date:** 2026-07-05 · 276 words · 0 comments · 0 likes
- **Tags:** — · **Categories:** AI Agents &amp; Automation, AI Models &amp; APIs
- **URL:** http://topaiproduct.com/2026/07/05/deepseek-v4-pro-v4-flash-ship-with-1m-context-and-0-28-m-output/
- **Type:** announcement · **Provenance:** somebody else's benchmark repeated
- **Artifacts: 3** — `bench_number`×1, `price`×4, `version_string`×1
- **Benchmark figures:** 1 mentions, 0 attributed near the number

     DeepSeek is back, and it’s aiming straight at the agent crowd. The new V4 series is two open-weight MoE models — V4-Pro (1.6T total, 49B active) and V4-Flash (284B total, 13B active) — both shipping with a 1-million-token context window by default. Not a premium tier. The floor.
    
     What it actually is 
     These are API-callable frontier models built for long-horizon agentic work — coding loops, multi-step tool use, the kind of task that eats context and never lets go. V4-Pro-Max hits 80.6% on SWE-bench Verified, the top open-weights score, tied with Gemini 3.1 Pro. V4-Flash matches Pro on simpler agent tasks at 12× less cost, so most people will run Flash and only escalate when they need the muscle.
    
     Why it matters 
     Pricing is the weapon. Flash lists at $0.14/M in, $0.28/M out; Pro’s cache-hit rate drops to $0.003625/M — brutal for agent loops that resend the same context every turn. DeepSeek also rolled out peak-hour surge pricing and reportedly raised $7.4B at a $50B+ valuation. The playbook is the same as V3: commoditize the model layer, force everyone to compete on cost. Long-context agents just got a lot cheaper.
    
     
     You Might Also Like 
     
     Tempo Machine Payments Protocol 500m 100 Partners and a Bold Play to own the ai Agent Economy 
    
     397 Billion Parameters on a 48gb Macbook Flash moe Turns Apples 2023 Research Into Reality 
    
     Microsoft Agent Governance Toolkit Scores 10 10 on Owasp Agentic Risks at 0 1ms per Check 
    
     Deepseek v4 pro Hits gpt 5 Parity on 5 of 7 Benchmarks at a Fraction of the Cost 
    
     Deepclaude Lets Claude Code run on Deepseek v4 pro 0 87 vs 15 per Million Tokens 
    
     

---

### 17. DeepSeek V4 Pro API Update Adds Responses API Support

- **Author:** — — byline resolves to a person: **no**
- **Site:** TechNode (`technode.com`) · 18904 posts, 5.56/day, 3 bylines sampled
- **Site describes itself as:** Latest news and trends about tech in China
- **Date:** 2026-08-13 · 73 words · 0 comments · 0 likes
- **Tags:** — · **Categories:** News Feed
- **URL:** https://technode.com/2026/08/13/deepseek-v4-pro-api-update-adds-responses-api-support/
- **Type:** news summary · **Provenance:** unattributed
- **Artifacts: 3** — `code_fence`×4, `price`×2, `version_string`×2
- **Benchmark figures:** 0 mentions, 0 attributed near the number

     DeepSeek’s API documentation now lists 
    ```
    deepseek-v4-pro
    ```
     as an available model, with the current version identified as 
    ```
    DeepSeek-V4-Pro-0813
    ```
    . The model supports the Responses API and tool calls, with a context length of 1 million tokens and a maximum output of 384,000 tokens.
    
     The listed price is $0.003625 per million input tokens for cache hits, $0.435 for cache misses and $0.87 per million output tokens. [ DeepSeek API Docs ]
    

---

### 18. This Week in Artificial Intelligence

- **Author:** SteveTechMan — byline resolves to a person: **yes**
- **Site:** The Digital Archives (`thedigitalarchives.wordpress.com`) · 34 posts, 0.2/day, 1 bylines sampled
- **Site describes itself as:** Technology History and the road to Artificial Intelligence
- **Date:** 2026-08-15 · 1,898 words · 0 comments · 1 likes
- **Tags:** ai, artificial-intelligence, chatgpt, deepseek, gpu, grok, llm, memory · **Categories:** Uncategorized
- **URL:** https://thedigitalarchives.wordpress.com/2026/08/15/this-week-in-artificial-intelligence-13/
- **Type:** news summary · **Provenance:** vendor claim restated
- **Artifacts: 2** — `bench_number`×3, `version_string`×2
- **Benchmark figures:** 5 mentions, 0 attributed near the number

     
     This Week in Artificial Intelligence (August 8–15, 2026) 
    
    
    
    
     The past seven days delivered simultaneous advances in agentic capability, open local models, specialized inference, and leadership shifts, while the underlying hardware economics of local AI grew markedly more constrained. Model releases and safety pauses arrived against a backdrop of sustained memory shortages and sharp price escalation in the very GPUs practitioners rely on for on-prem and workstation deployment. Capability is rising; the cost of owning that capability locally is rising faster.
    
    
    
    
     OpenAI Pauses Portions of Astra Development After Critical Cyber Threshold Flags 
    
    
    
     
    
    
    
     thehackernews.com 
    
    
    
    
     On August 7, OpenAI publicly disclosed that preliminary evaluations of its upcoming frontier model Astra showed sufficiently strong performance in agentic coding and cybersecurity that the company “cannot rule out” Critical-level capability under its Preparedness Framework.
    
    
    
    
     The Framework defines Critical cybersecurity as the ability to identify and develop functional zero-day exploits across hardened real-world systems without human intervention, or to devise and execute novel end-to-end attack strategies from only a high-level goal. Prior models, including GPT-5.6 Sol, had been assessed at High. In response, OpenAI scaled security controls, moved remaining Astra work into more isolated environments, paused non-compliant internal activities, and instituted broader monitoring.
    
    
    
    
     The announcement lands against a backdrop of earlier agent containment incidents. OpenAI emphasized that Astra itself was not involved in prior test escapes and reiterated its intention to deploy advanced cyber-capable models to aid defenders once safeguards are in place. The move marks one of the clearest public applications of a lab’s own pre-defined risk ladder at the frontier.
    
    
    
    
     Meta Releases Muse Glimmer: A 30B Open-Weight Agentic Model Built for Local Devices 
    
    
    
     
    
    
    
     research.meta.ai 
    
    
    
    
     On August 10, Meta Superintelligence Labs released Muse Glimmer, a 30-billion-parameter dense model optimized for agentic workflows and released under the permissive Apache 2.0 license with full weights on Hugging Face.
    
    
    
    
     Quantized to roughly 4-bit precision, the model fits under 20 GB and is designed to run on a single consumer GPU or modern Apple Silicon. It emphasizes reliable tool use, multi-step reasoning over long horizons, failure recovery, multimodal perception, and controllable reasoning effort. Meta positions it explicitly for “always-on local agent workflows” that do not require continuous cloud connectivity.
    
    
    
    
     The release continues Meta’s pattern of alternating proprietary frontier models with open weights that lower the barrier for on-device and edge deployment. By shipping a capable agent-focused model that can operate offline, Meta directly pressures pure cloud economics while giving developers a high-quality baseline that can be fine-tuned without API costs.
    
    
    
    
     DeepSeek V4-Pro Moves to General Availability with Enhanced Agent Capabilities 
    
    
    
     
    
    
    
     yottalabs.ai 
    
    
    
    
     Mid-week, DeepSeek rolled out the general-availability build of DeepSeek-V4-Pro (0813) across its app, web interface, and API. The update emphasizes production-grade agent improvements, with reported gains on several agent-oriented benchmarks including Terminal Bench, NL2Repo, Cybergym, and DeepSWE.
    
    
    
    
     Pricing adjustments were also signaled. The model continues DeepSeek’s pattern of competitive performance at aggressive price points relative to leading closed frontier systems, particularly for agentic and coding workloads. Practitioners watching inference economics noted the combination of strong agent scores and still-attractive pricing as a practical alternative for many production workloads.
    
    
    
    
     xAI Ships Grok 4.6, Targeting Long-Running Agents and Interactive Work 
    
    
    
     
    
    
    
     kie.ai 
    
    
    
    
     On August 12, xAI released Grok 4.6 . The model builds directly on Grok 4.5 with explicit emphasis on staying coherent across long-horizon agentic tasks—multi-step research, codebase navigation, and turning ideas into polished artifacts.
    
    
    
    
     It retains a large context window and competitive pricing relative to peer frontier models, with availability expanding across the xAI API, Cursor, Grok Build, and partner platforms including GitHub Copilot. Third-party evaluations placed it in the same broad performance band as leading closed models on several intelligence and coding indices while highlighting strengths in sustained task endurance. The rapid cadence illustrates how aggressively the competitive frontier is now moving on agent reliability rather than pure single-turn scores.
    
    
    
    
     OpenAI and Cerebras Deliver Ultrafast Inference for GPT-5.6 Sol 
    
    
    
     
    
    
    
     servethehome.com 
    
    
    
    
     On August 13, OpenAI previewed Ultrafast mode for GPT-5.6 Sol, powered by Cerebras wafer-scale hardware. The service tier claims up to 750 output tokens per second, up to 14× faster than standard processing, without quality degradation on the same model weights.
    
    
    
    
     Cerebras’ architecture keeps the full model weights resident on-chip, eliminating the repeated off-chip memory transfers that bottleneck conventional GPU inference. The offering launched in limited preview for selected API customers. For latency-sensitive applications, real-time agents, interactive coding, high-frequency decision loops, the speed differential is material and highlights specialized silicon as a decisive differentiator for usable frontier latency.
    
    
    
    
     Google DeepMind Leadership Transition and Broader Talent Realignment 
    
    
    
     
    
    
    
     reuters.com 
    
    
    
    
     Google confirmed a significant leadership shift at DeepMind. Demis Hassabis moved from CEO to Chair of Google DeepMind and Chief Scientist of Alphabet, with Koray Kavukcuoglu assuming day-to-day leadership as SVP. Several long-time researchers, including Jeff Dean, announced plans to leave and form a new research venture.
    
    
    
    
     Hassabis framed the change as allowing deeper focus on AGI-scale scientific and safety questions as capabilities approach more consequential thresholds. The moves reflect both the maturation of large research organizations and the intense competition for top researchers capable of driving the next generation of models and evaluation science.
    
    
    
    
     Opinion: Consumer GPUs – The pain is increasing 
    
    
    
     The week’s model and agent advances are impressive, yet they sit atop a hardware market whose trajectory should concern anyone serious about local or on-prem AI. The single clearest signal is the price trajectory of NVIDIA’s RTX PRO 6000 Blackwell, the 96 GB GDDR7 workstation card that has become the de facto bellwether for high-end local AI and professional inference. Launched in March 2025 at an official marketplace price of approximately $8,565, the card was raised to $13,250 in mid-2026 and, by early August 2026, listed at $16,000 on NVIDIA’s own U.S. marketplace, an increase of roughly 87 percent in under sixteen months with no corresponding hardware change. Tom’s Hardware and multiple secondary reports confirm the successive hikes; the dominant driver is not silicon redesign but acute GDDR7 supply pressure.
    
    
    
    
     That pressure is not isolated. Consumer RTX 50-series cards have seen median street prices rise 10–41 percent in various markets during August alone, with the RTX 5090 trading well above its original launch band and some regional listings exceeding $5,000. Board partners and distributors attribute the movement to rising GDDR7 module costs and redirected wafer allocation toward higher-margin AI products. The same memory physics that powers HBM in data-center accelerators is now constraining the discrete GPUs that independent researchers, startups, and SMB teams use for local agentic systems.
    
    
    
    
     The root cause lies in the memory suppliers’ own forecasts. SK Hynix’s 2026 market outlook framed an “HBM-led memory supercycle,” with HBM demand expected to drive substantial ASP increases and the company maintaining a dominant share in HBM3E and early HBM4. Multiple reports indicate SK Hynix’s 2026 HBM capacity is essentially sold out; Samsung has warned that significant shortages across memory products are expected to continue through at least 2027, with some customers already securing allocations into that year. Micron has similarly prioritized enterprise and HBM output, exiting or de-emphasizing certain consumer channels. Industry analyses from Counterpoint, BofA, and others project that conventional DRAM ASPs will continue to climb sharply, with some quarterly contract-price forecasts in the 50–60 percent range, because every wafer diverted to HBM displaces multiple times its bit volume in standard DDR5 or GDDR. HBM’s silicon intensity (roughly 3× the area per gigabyte relative to conventional DRAM) creates a structural crowding-out effect that is unlikely to ease before new fabs begin meaningful volume in late 2027 and through 2028.
    
    
    
    
     Long-range estimates reinforce the same conclusion. SK Hynix’s CEO has publicly described 2027 as potentially the industry’s worst supply year in terms of capacity, with demand expected to outstrip supply well beyond 2030, even after aggressive expansion. Samsung’s leadership has echoed that significant shortages will persist through 2027. New capacity from Micron’s U.S. and Japanese investments, SK Hynix’s packaging and fab additions, and Samsung’s HBM ramps will not arrive at scale soon enough to reverse near-term pricing. The result is a multi-year elevation in the cost of the memory that underpins both data-center and local high-VRAM GPUs.
    
    
    
    
     For anyone building or expanding local AI capacity, whether a multi-GPU workstation for agentic experimentation, a small cluster for recursive self-improvement loops, or production inference for privacy-sensitive workloads, the arithmetic is straightforward. The RTX PRO 6000 Blackwell’s price path, the parallel movement in consumer 50-series cards, and the unanimous supply warnings from SK Hynix, Micron, and Samsung all point in the same direction: waiting is likely to be more expensive than buying. Open-weight models such as Muse Glimmer and competitive Chinese offerings lower software barriers, but they still require capable local silicon. That silicon is becoming scarcer and more costly in real time. Practitioners who intend to run serious agentic systems outside hyperscaler clouds should treat current pricing as a floor rather than a peak and act while inventory and relatively lower price points remain available.
    
    
    
    
     HBM series, along with LPDDR5 and GDDR7 memory, has become the sole piece of silicon that drives continued price increases throughout the consumer sector, with the impact starting to be felt in the de facto base system that brings many into the Local AI space, the DGX Spark and GB10 partner systems. The comfort that has been the standard at the ~$4600 price is coming to an end as early purchase allocations begin to phase out, with many GB10 partners already reflecting pricing into the $5499-$5999 range, with an expected base of $6499 by December of 2026. As the uncontrolled pace of global data center construction continues to ramp up, more and more demand is being put on the three memory suppliers to the world: SK Hynix, Micron, and Samsung, pressured to produce at a ravenous pace they simply can not keep up with, even with known expansions, and the eventual landing of Tesla/SpaceX’s Terafab, we are still a few years away from any type of documented relief. Yet with that, we must also face the horizon of new GPUs entering the space before any type of supply increase, which will put additional pressure on the sector, driving price increases nearly 2-3x annually beyond stated estimates, raising the barrier of entry for many simply out of reach, which in my opinion, is exactly what the frontier shops silently are cheering on, for the masses to turn to control and subscriptions rather than the freedom local AI brings.
    
    
    
    
     From the Trenches 
    
    
    
     For builders and practitioners, the week’s model releases expand the software toolkit, yet the hardware substrate is tightening. Local agentic baselines are now strong enough for many internal tools, specialized inference tiers reduce latency for cloud-dependent paths, and competitive pricing from open and Chinese models improves options on the software side. The binding constraint is shifting to physical GPUs and the memory that feeds them. The RTX PRO 6000’s successive price increases, parallel consumer GPU inflation, and explicit multi-year shortage forecasts from the three major memory suppliers mean that any plan for on-prem or workstation-scale local AI should treat acquisition timing as a first-order decision. Secure capable hardware now if the workload requires it; the combination of sold-out HBM allocations and rising conventional DRAM costs makes later purchases structurally more expensive. Design agent systems with isolation and monitoring as core requirements, evaluate price-performance continuously across open and closed models, and treat the current window as the practical moment to lock in local capacity before the next leg of the memory supercycle fully prices in.
    
     

---

### 19. Three reasons why DeepSeek’s new model matters – MIT Technology Review

- **Author:** CDO TIMES BOT — byline resolves to a person: **no**
- **Site:** The CDO TIMES (`cdotimes.com`) · 10706 posts, 7.69/day, 2 bylines sampled
- **Site describes itself as:** The digital insights magazine for CDOs, CIOs and other executive digital leaders - written by digital leaders.
- **Date:** 2026-04-25 · 1,691 words · 0 comments · 1 likes
- **Tags:** digital · **Categories:** Digital Trends
- **URL:** https://cdotimes.com/2026/04/25/three-reasons-why-deepseeks-new-model-matters-mit-technology-review/
- **Type:** news summary · **Provenance:** somebody else's benchmark repeated
- **Artifacts: 2** — `bench_number`×1, `price`×4
- **Benchmark figures:** 0 mentions, 0 attributed near the number

     The long-awaited V4 is more efficient and a win for Chinese chipmakers.
    On Friday, Chinese AI firm DeepSeek released a preview of V4, its long-awaited new flagship model. Notably, the model can process much longer prompts than its last generation, thanks to a new design that helps it handle large amounts of text more efficiently. Like DeepSeek’s previous models, V4 is open source, meaning it is available for anyone to download, use, and modify.
    V4 marks DeepSeek’s most significant release since R1 , the reasoning model it launched in January 2025. R1, which was trained on limited computing resources, stunned the global AI industry with its strong performance and efficiency, turning DeepSeek from a little-known research team into China’s best-known AI company almost overnight. It also helped set off a wave of open-weight model releases from other Chinese AI firms. 
    DeepSeek has kept a relatively low profile since then—but earlier this month, it effectively teased V4’s release when it added “expert” and “flash” modes to the online version of its model, prompting speculation that the updates were tied to a bigger upcoming release.
    While the company has become a powerful symbol of China’s AI ambitions, its big return to cutting-edge frontier models comes after months of scrutiny—including major personnel departures , delays to previous model launches , and growing scrutiny from both the US and Chinese governments. 
    So, will V4 shake the AI field the way R1 did? Almost certainly not, but here are three big reasons why this release matters.
    
     As with R1 before it, DeepSeek claims that V4’s performance rivals the best models available at a fraction of the price. This is great news for developers and for companies using the tech, because it means they can access frontier AI capabilities on their own terms, and without worrying about skyrocketing costs.
    The new model comes in two versions, both of which are available on DeepSeek’s website and in its app, with API access also open to developers. V4-Pro is a larger model built for coding and complex agent tasks, and V4-Flash is a smaller version designed to be faster and cheaper to run. Both versions offer reasoning modes, in which the model can carefully parse a user’s prompt and show each step as it works through the problem.
    For V4-Pro, DeepSeek charges $1.74 per million input tokens and $3.48 per million output tokens, a fraction of the cost of comparable models from OpenAI and Anthropic. V4-Flash is even cheaper, at about $0.14 per million input tokens and about $0.28 per million output tokens, making it one of the cheapest top-tier models available. This would make it a very appealing model to build applications on.
    In terms of performance, V4 is, perhaps unsurprisingly, a huge jump from R1—and it seems to be a strong alternative to just about all the latest big AI models. On the major benchmarks, according to results shared by the company, DeepSeek V4-Pro competes with leading closed-source models, matching the performance of Anthropic’s Claude-Opus-4.6, OpenAI’s GPT-5.4, and Google’s Gemini-3.1. And compared to other open-source models, such as Alibaba’s Qwen-3.5 or Z.ai’s GLM-5.1, DeepSeek V4 exceeds them all on coding, math, and STEM problems, making it one of the strongest open-source models ever released. 
    DeepSeek also says that V4-Pro now ranks among the strongest open-source models on benchmarks for agentic coding tasks and performs well on other tests that measure ability to carry out multistep problems. Its writing ability and world knowledge also lead the field, according to benchmarking results shared by the company. 
    In a technical report released alongside the model, DeepSeek shared results from an internal survey of 85 experienced developers: More than 90% included V4-Pro among their top model choices for coding tasks.
    DeepSeek says it has specifically optimized V4 for popular agent frameworks such as Claude Code, OpenClaw, and CodeBuddy.
    
     One of the key innovations of V4 is its long context window—the amount of text the model can process at once. Both versions can handle 1 million tokens, which is large enough to fit all three volumes of The Lord of the Rings and The Hobbit combined. The company says this context window size is now the default across all DeepSeek services and it matches what is offered by cutting-edge versions of models like Gemini and Claude. 
    But it’s important to know not just that DeepSeek has made this leap, but how it did so. V4 makes significant architectural changes to the company’s former models—especially in the attention mechanism, which is the feature of AI models that helps them understand each part of a prompt in relation to the rest. As the prompt text gets longer, these comparisons become much more costly, making attention one of the main bottlenecks for long-context models.
    DeepSeek’s innovation was to make the model more selective about what it pays attention to. Instead of treating all earlier text as equally important, V4 compresses older information and focuses on the parts most likely to matter in the present moment, while still keeping nearby text in full so it does not miss important details. 
    DeepSeek says this sharply reduces the cost of using long context. In a 1-million-token context, V4-Pro uses only 27% of the computing power required by its previous model, V3.2, while cutting memory use to 10%. The reduction in V4-Flash is even larger, using just 10% of the computing power and 7% of the memory. In practice, this could make it cheaper to build tools that need to work across huge amounts of material, such as an AI coding assistant that can read an entire codebase or a research agent that can analyze a long archive of documents without constantly forgetting what came before.
    DeepSeek’s interest in long context windows didn’t start with V4. Over the past year and a half, the company has quietly published a series of papers on how AI models “remember” information, experimenting with compression and mathematical techniques to extend what AI models could realistically handle.
    
     V4 is DeepSeek’s first model optimized for domestic Chinese chips, such as Huawei’s Ascend—a move that has turned the launch into something of a test of whether China’s homegrown AI industry can begin to loosen its dependence on US chip giant Nvidia. 
    This was largely expected, since The Information reported earlier this month that DeepSeek did not give American chipmakers like Nvidia and AMD early access to V4, though prerelease access is common to allow chipmakers to optimize support of the new model ahead of a launch. Instead, the company reportedly gave early access only to Chinese chipmakers. 
    On Friday, Huawei said its Ascend supernode products, based on the Ascend 950 series, would support DeepSeek V4. This means that companies and individuals who want to run their own modified version of Deepseek V4 will be able to use Huawei chips easily.
    
     Reuters previously reported that Chinese government officials recommended that DeepSeek integrate Huawei chips in its training process. And this pressure fits a broader pattern in China’s industrial policy: Strategic sectors are often pushed, and sometimes effectively required, to align with national self-reliance goals. But there’s a particular urgency when it comes to AI. Since 2022, US export controls have cut Chinese firms off from Nvidia’s most powerful chips, and they later also restricted access to downgraded China-market versions. Beijing’s response has been to accelerate the push for a domestic AI stack, from chips to software frameworks to data centers.
    Chinese authorities have reportedly been pushing data centers and public computing projects to use more domestic chips, including through reported bans on foreign-made chips , sourcing quotas , and requirements to pair Nvidia chips with Chinese alternatives from companies such as Huawei and Cambricon. 
    Still, replacing Nvidia is not as simple as swapping one chip for another. Nvidia’s advantage lies not only in its chips, but in the software ecosystem developers have spent years building around them. Moving to Huawei’s Ascend chips means adapting model code, rebuilding tools, and proving that systems built around those chips are stable enough for serious use.
    To be clear, DeepSeek does not appear to have fully moved beyond Nvidia. The company’s technical report reveals that it is using Chinese chips to run the model for inference, or when someone asks the model to complete a task. But Liu Zhiyuan, a computer science professor at Tsinghua University, told MIT Technology Review that DeepSeek appears to have adapted only part of V4’s training process for Chinese chips. The report does not say whether some key long-context features were adapted to domestic chips, so Liu says V4 may still have been trained mainly on Nvidia chips. Multiple sources who spoke on the condition of anonymity, due to political sensitivity around these issues, told MIT Technology Review that Chinese chips still don’t perform as well as Nvidia chips but are better suited for inference than training.
    DeepSeek is also tying the future costs of V4 to this hardware shift. The company says V4-Pro prices could fall significantly after Huawei’s Ascend 950 supernodes begin shipping at scale in the second half of this year. 
    If that works, V4 could be an early sign that China is successfully building a parallel AI infrastructure. 
     An exclusive conversation with OpenAI’s chief scientist, Jakub Pachocki, about his firm's new grand challenge and the future of AI. 
    Exclusive: Niantic's AI spinout is training a new world model using 30 billion images of urban landmarks crowdsourced from players.
    According to Stanford’s 2026 AI Index, AI is sprinting, and we’re struggling to keep up.
     Axiom Math is giving away a powerful new AI tool. But it remains to be seen if it speeds up research as much as the company hopes. 
    Discover special offers, top stories, upcoming events, and more.
    Thank you for submitting your email!
    It looks like something went wrong.
     We’re having trouble saving your preferences. Try refreshing this page and updating them one more time. If you continue to get this message, reach out to us at customer-service@technologyreview.com with a list of newsletters you’d like to receive.
    
     © 2026 MIT Technology Review
    
     source 
    This is a newsfeed from leading technology publications. No additional editorial review has been performed before posting. 
    

---

### 20. What AI Coding Models Actually Cost Right Now

- **Author:** Tried and Typed — byline resolves to a person: **no**
- **Site:** Tried and Typed (`triedandtyped.com`) · 18 posts, 2.25/day, 1 bylines sampled
- **Site describes itself as:** First-hand notes on AI, dev work, health, travel, and the tools worth your time
- **Date:** 2026-08-27 · 1,612 words · 2 comments · 0 likes
- **Tags:** AI, artificial-intelligence, chatgpt, llm, technology · **Categories:** Products
- **URL:** http://triedandtyped.com/2026/08/27/ai-coding-model-prices-august-2026/
- **Type:** news summary · **Provenance:** unattributed
- **Artifacts: 2** — `bench_number`×2, `price`×4
- **Benchmark figures:** 3 mentions, 1 attributed near the number

     
     In ten days this month, OpenAI cut its flagship coding model by a third, Google launched a model at exactly half its predecessor’s price, and DeepSeek quadrupled its rates. Three moves, three directions, all in August. The story everyone reached for was “a price war is driving AI coding costs to zero,” which is roughly half right — and the half that’s wrong is the half that would cost you money. Here’s what everything actually costs as of today, where the real value sits, and which of these numbers has an expiry date attached.
    
    
    
    
     The short version 
    
    
    
     
     
     Prices are not uniformly falling. DeepSeek went up about 4× on 16 August and introduced peak/off-peak rates.
    
     
     Two of the cheapest headline numbers expire. Gemini 3.7 Flash doubles on 1 January 2027. GPT-5.6 Sol’s cut is promotional “at least through” 21 November 2026.
    
     
     Anthropic made a discount permanent — Sonnet 5 stays at $2/$10 instead of rising to $3/$15 on 1 September, which complicates the “Anthropic is losing on price” story.
    
     
     The FT story is about Claude Fable 5, not Opus 5. That distinction matters, and a lot of the commentary got it wrong.
    
     
     The spread is the real finding: roughly 250× between the cheapest and dearest output prices, for under 30 points of benchmark difference.
    
     
    
    
    
     All prices below are US dollars per million tokens, checked on 25 August 2026 . Model pricing changes fast enough that you should treat any figure older than a few weeks as fiction — including this one, eventually.
    
    
    
    
     What actually changed this month? 
    
    
    
     OpenAI cut GPT-5.6 Sol on 21 August , from $5/$30 to $4/$20. Worth being precise, because the widely repeated “more than 20%” is a blend: input fell exactly 20%, output fell 33%. If your workload is generation-heavy — which coding is — you got the better end of that. It’s also the third cut in the GPT-5.6 family inside a month, after Luna dropped 80% and Terra 20% on 30 July.
    
    
    
    
     Google launched Gemini 3.7 Flash on 13 August at $0.75/$3.75 — exactly half Gemini 3.6 Flash’s $1.50/$7.50. The important detail is on Google’s own pricing page rather than in the press coverage: this is an introductory rate through 31 December 2026, and on 1 January 2027 it returns to $1.50/$7.50. Build your Q4 cost model on the current number and your New Year’s Day is a 100% increase.
    
    
    
    
     DeepSeek went up , effective 16:00 UTC on 16 August, alongside the V4 lineup release. V4-Pro output moved from $0.87 to $3.96 at peak and $1.98 off-peak. That’s roughly a 4× increase at peak, and it came with a new peak/off-peak structure — 01:00–04:00 and 06:00–10:00 UTC on weekdays are peak; everything else is exactly half. DeepSeek framed it as enabling flexible workload scheduling. If your jobs are batch and can wait, that’s genuinely useful. If they’re interactive, it’s just a price rise.
    
    
    
    
     Anthropic did the opposite of what you’d expect from the coverage. Sonnet 5 launched at $2/$10 as introductory pricing due to rise to $3/$15 on 1 September. That increase has been cancelled — $2/$10 is now the standard price. A permanent cut is a stronger signal than a temporary promotion, and it went largely unreported.
    
    
    
    
     One correction while we’re here: reports that Moonshot has split Kimi K3 into separate general and coding subscription tiers are premature. The split is announced in the plan documentation, with existing subscribers keeping all benefits and no implementation date given. It hasn’t happened yet.
    
    
    
    
     What does everything cost right now? 
    
    
    
     
     
     Model 
     Input 
     Output 
     Notes 
    
     
     
     
     Claude Fable 5 
     $10.00 
     $50.00 
     Anthropic’s top tier 
    
    
     
     Claude Mythos 5 
     $10.00 
     $50.00 
     
    
    
     
     Claude Opus 5 
     $5.00 
     $25.00 
     
    
    
     
     GPT-5.6 Sol 
     $4.00 
     $20.00 
     Promo to 21 Nov 2026 
    
    
     
     Kimi K3 
     $3.00 
     $15.00 
     $0.30 cached input 
    
    
     
     GPT-5.6 Terra 
     $2.50 
     $15.00 
     
    
    
     
     Claude Sonnet 5 
     $2.00 
     $10.00 
     Now permanent 
    
    
     
     Qwen3.8-Max 
     $2.00 
     $6.00 
     See caveat below 
    
    
     
     Z.ai GLM-5.3 
     $1.40 
     $4.40 
     $0.26 cached input 
    
    
     
     DeepSeek V4-Pro (peak) 
     $1.32 
     $3.96 
     $0.044 on cache hit 
    
    
     
     GPT-5.6 Luna 
     $1.00 
     $6.00 
     
    
    
     
     Gemini 3.7 Flash 
     $0.75 
     $3.75 
     Doubles 1 Jan 2027 
    
    
     
     DeepSeek V4-Pro (off-peak) 
     $0.66 
     $1.98 
     Half the peak rate 
    
    
     
     Gemini 3.5 Flash-Lite 
     $0.30 
     $2.50 
     
    
    
     
     
    
    
    
     Two honest caveats. Qwen3.8-Max is the weakest row here — Alibaba Cloud’s Model Studio pricing page wouldn’t load for me on repeated attempts, so $2/$6 comes from OpenRouter’s listing and secondary reporting rather than the vendor page. Verify it in the console before you build a budget on it. And if you see GPT-5.6 Sol listed at $2/$10 anywhere, that’s a routing-level discount or a rendering artefact — OpenAI’s own docs say $4/$20.
    
    
    
    
     Is anyone actually abandoning the expensive models? 
    
    
    
     The Financial Times reported on 23 August that Anthropic’s best model is struggling to attract users while cheaper tools thrive. It’s a real story with real data behind it, and almost every summary I read got one detail wrong: it’s about Claude Fable 5, the $10/$50 flagship — not Opus 5 , which sits at $5/$25 and appears to be gaining share. Several write-ups asserted the opposite of what the underlying numbers show.
    
    
    
    
     The measured part comes from Ramp’s AI Index, built on corporate card data across roughly 70,000 companies. In July, Fable 5 accounted for about 6% of Anthropic tokens purchased but 11.4% of Anthropic model-attributed spending — the gap is just the price premium doing its work. By 23 August that had settled near 11%. That’s a plateau, not a collapse. Meanwhile Anthropic’s overall share of US businesses rose to 43.5%, up 1.1 points month on month, ahead of OpenAI’s 39.7%.
    
    
    
    
     A second, independent dataset points the same way: Vercel’s AI Gateway saw Anthropic take 65.1% of gateway spending on 30% of tokens in July. And the single largest Anthropic line item in Ramp’s data wasn’t any flagship — it was Opus 4.8 at 28%, an older and cheaper model.
    
    
    
    
     Both datasets have the same blind spot and it’s a big one: neither Ramp nor Vercel can see Anthropic’s direct enterprise contracts, which is arguably where a flagship model actually sells. Ramp’s own analysts also note the Fable sample skews more technical than their typical panel. The defensible version of this story is narrow: the expensive flagship is a small and flat share of card-and-gateway-visible spending. Not “nobody is buying it.”
    
    
    
    
     The revenue figures in the FT piece — annualised revenue of $65bn in July, 6,000 customers above $100k a year — come from “people with knowledge of the matter,” not disclosed financials. Treat them accordingly. And the most quotable line in the coverage, that most people “don’t need to operate at the frontier,” is from an investor at a firm that has put around $1bn into Anthropic. That doesn’t make it wrong. It does make it a position rather than a finding.
    
    
    
    
     What do you actually get for the extra money? 
    
    
    
     Here’s the SWE-bench Pro leaderboard as of 10 August, next to output price. Read it for shape, not for precise ordering — these are vendor-reported aggregate scores rather than a controlled harness, and on Scale’s standardised set with common scaffolding the ordering changes materially.
    
    
    
    
     
     
     Model 
     SWE-bench Pro 
     Output $/M 
    
     
     
     
     Claude Fable 5 
     80.0% 
     $50 
    
    
     
     Claude Opus 4.8 
     69.2% 
     $25 
    
    
     
     Qwen3.8-Max 
     67.7% 
     $6 
    
    
     
     GPT-5.6 Sol 
     64.6% 
     $20 
    
    
     
     Claude Sonnet 5 
     63.2% 
     $10 
    
    
     
     GPT-5.6 Luna 
     62.7% 
     $6 
    
    
     
     GLM-5.2 
     62.1% 
     $3 
    
    
     
     DeepSeek V4-Flash-Max 
     52.6% 
     $0.20 
    
    
     
     
    
    
    
     The number worth carrying away: the price spread across this set is roughly 250×. The capability spread is under 30 percentage points. Fable 5 buys you about 17 points over Sonnet 5 for five times the output price. Whether that’s worth it depends entirely on what those 17 points are doing — on a task where a wrong answer costs an hour of debugging, they’re cheap; on bulk refactoring where you review everything anyway, they’re not.
    
    
    
    
     Be careful with points-per-dollar arithmetic, including mine. Dividing benchmark score by output price ignores input cost and cache economics entirely, which flatters models with cheap output and expensive input. It also treats a benchmark point as a linear good, which it isn’t.
    
    
    
    
     How to actually choose 
    
    
    
     
     
     Price your own workload, not the sticker. Coding is output-heavy, so weight output price accordingly — that’s why Sol’s 33% output cut matters more than its 20% input cut.
    
     
     Check the expiry date on any cheap number. Gemini 3.7 Flash doubles on 1 January 2027; Sol’s rate is promotional to 21 November 2026 with no stated price after.
    
     
     Use cache pricing if your prompts repeat. DeepSeek’s cache-hit input is $0.044 against $1.32 on a miss — a 30× difference that dwarfs most model-choice decisions.
    
     
     Consider off-peak scheduling. If your DeepSeek workload is batch, avoiding 01:00–04:00 and 06:00–10:00 UTC on weekdays halves the bill.
    
     
     Don’t pay frontier prices for non-frontier tasks. The largest single Anthropic line item in the Ramp data is an older, cheaper model, which tells you something about what experienced buyers actually do.
    
     
     Re-check quarterly. Four material price changes landed in one month. Anything you decided in June is already stale.
    
     
    
    
    
     The useful mental shift is away from “which model is best” and toward “which model is cheapest for the tasks where cheapest is fine, and which is worth paying up for on the rest.” Almost nobody needs one model. Routing between two — a cheap one for bulk work and an expensive one for the parts that bite — beats picking a winner, and it’s the pattern the spending data suggests people are quietly converging on anyway. It’s the same instinct behind loading capability only when it’s needed rather than paying for it on every request.
    
    
    
    
     Prices verified against vendor documentation on 25 August 2026. Benchmark figures from the SWE-bench Pro leaderboard dated 10 August 2026. Spending data from Ramp’s AI Index (July 2026) and Vercel AI Gateway (July 2026). 
    
     

---

### 21. Three reasons why DeepSeek’s new model matters

- **Author:** — — byline resolves to a person: **no**
- **Site:** MIT Technology Review (`www.technologyreview.com`)
- **Date:** 2026-04-24 · 1,542 words · 0 comments · 2 likes
- **Tags:** App, Summary · **Categories:** Artificial intelligence
- **URL:** https://www.technologyreview.com/2026/04/24/1136422/why-deepseeks-v4-matters/
- **Type:** news summary · **Provenance:** somebody else's benchmark repeated
- **Artifacts: 2** — `bench_number`×1, `price`×4
- **Benchmark figures:** 0 mentions, 0 attributed near the number

    
    
    
    On April 24, Chinese AI firm DeepSeek released a preview of V4, its long-awaited new flagship model. The model can process much longer prompts than its last generation, thanks to a new design that helps it handle large amounts of text more efficiently. Like DeepSeek’s previous models, V4 is open source, meaning it is available for anyone to download, use, and modify.
    
    
    
    V4 marks DeepSeek’s most significant release since R1, the reasoning model it launched in January 2025. R1, which was trained on limited computing resources, stunned the global AI industry with its strong performance and efficiency, turning DeepSeek from a little-known research team into China’s best-known AI company almost overnight. It also helped set off a wave of open-weight model releases from other Chinese AI firms. 
    
    
    
    DeepSeek has kept a relatively low profile since then—but earlier this month, it effectively teased V4’s release when it added “expert” and “flash” modes to the online version of its model, prompting speculation that the updates were tied to a bigger upcoming release.
    
    
    
    While the company has become a powerful symbol of China’s AI ambitions, its big return to cutting-edge frontier models comes after months of scrutiny—including major personnel departures, delays to previous model launches, and growing scrutiny from both the US and Chinese governments. 
    
    
    
    So, will V4 shake the AI field the way R1 did? Almost certainly not, but here are three big reasons why this release matters.
    
    
    
    1. It breaks new ground for an open-source model
    
    
    
    
    As with R1 before it, DeepSeek claims that V4’s performance rivals the best models available at a fraction of the price. This is great news for developers and for companies using the tech, because it means they can access frontier AI capabilities on their own terms, and without worrying about skyrocketing costs.
    
    
    
    The new model comes in two versions, both of which are available on DeepSeek’s website and in its app, with API access also open to developers. V4-Pro is a larger model built for coding and complex agent tasks, and V4-Flash is a smaller version designed to be faster and cheaper to run. Both versions offer reasoning modes, in which the model can carefully parse a user’s prompt and show each step as it works through the problem.
    
    
    
    
    
    For V4-Pro, DeepSeek charges $1.74 per million input tokens and $3.48 per million output tokens, a fraction of the cost of comparable models from OpenAI and Anthropic. V4-Flash is even cheaper, at about $0.14 per million input tokens and about $0.28 per million output tokens, making it one of the cheapest top-tier models available. This would make it a very appealing model to build applications on.
    
    
    
    In terms of performance, V4 is, perhaps unsurprisingly, a huge jump from R1—and it seems to be a strong alternative to just about all the latest big AI models. On the major benchmarks, according to results shared by the company, DeepSeek V4-Pro competes with leading closed-source models, matching the performance of Anthropic’s Claude-Opus-4.6, OpenAI’s GPT-5.4, and Google’s Gemini-3.1. And compared to other open-source models, such as Alibaba’s Qwen-3.5 or Z.ai’s GLM-5.1, DeepSeek V4 exceeds them all on coding, math, and STEM problems, making it one of the strongest open-source models ever released. 
    
    
    
    DeepSeek also says that V4-Pro now ranks among the strongest open-source models on benchmarks for agentic coding tasks and performs well on other tests that measure ability to carry out multistep problems. Its writing ability and world knowledge also lead the field, according to benchmarking results shared by the company. 
    
    
    
    In a technical report released alongside the model, DeepSeek shared results from an internal survey of 85 experienced developers: More than 90% included V4-Pro among their top model choices for coding tasks.
    
    
    
    DeepSeek says it has specifically optimized V4 for popular agent frameworks such as Claude Code, OpenClaw, and CodeBuddy.
    
    
    
    2. It delivers on a new approach to memory efficiency
    
    
    
    One of the key innovations of V4 is its long context window—the amount of text the model can process at once. Both versions can handle 1 million tokens, which is large enough to fit all three volumes of The Lord of the Rings and The Hobbit combined. The company says this context window size is now the default across all DeepSeek services and it matches what is offered by cutting-edge versions of models like Gemini and Claude. 
    
    
    
    But it’s important to know not just that DeepSeek has made this leap, but how it did so. V4 makes significant architectural changes to the company’s former models—especially in the attention mechanism, which is the feature of AI models that helps them understand each part of a prompt in relation to the rest. As the prompt text gets longer, these comparisons become much more costly, making attention one of the main bottlenecks for long-context models.
    
    
    
    
    
    DeepSeek’s innovation was to make the model more selective about what it pays attention to. Instead of treating all earlier text as equally important, V4 compresses older information and focuses on the parts most likely to matter in the present moment, while still keeping nearby text in full so it does not miss important details. 
    
    
    
    DeepSeek says this sharply reduces the cost of using long context. In a 1-million-token context, V4-Pro uses only 27% of the computing power required by its previous model, V3.2, while cutting memory use to 10%. The reduction in V4-Flash is even larger, using just 10% of the computing power and 7% of the memory. In practice, this could make it cheaper to build tools that need to work across huge amounts of material, such as an AI coding assistant that can read an entire codebase or a research agent that can analyze a long archive of documents without constantly forgetting what came before.
    
    
    
    DeepSeek’s interest in long context windows didn’t start with V4. Over the past year and a half, the company has quietly published a series of papers on how AI models “remember” information, experimenting with compression and mathematical techniques to extend what AI models could realistically handle.
    
    
    
    3. It marks the first steps on the hard road away from Nvidia
    
    
    
    
    V4 is DeepSeek’s first model optimized for domestic Chinese chips, such as Huawei’s Ascend—a move that has turned the launch into something of a test of whether China’s homegrown AI industry can begin to loosen its dependence on US chip giant Nvidia. 
    
    
    
    This was largely expected, since The Information reported earlier this month that DeepSeek did not give American chipmakers like Nvidia and AMD early access to V4, though prerelease access is common to allow chipmakers to optimize support of the new model ahead of a launch. Instead, the company reportedly gave early access only to Chinese chipmakers. 
    
    
    
    On Friday, Huawei said its Ascend supernode products, based on the Ascend 950 series, would support DeepSeek V4. This means that companies and individuals who want to run their own modified version of Deepseek V4 will be able to use Huawei chips easily.
    
    
    
    
    
    Reuters previously reported that Chinese government officials recommended that DeepSeek integrate Huawei chips in its training process. And this pressure fits a broader pattern in China’s industrial policy: Strategic sectors are often pushed, and sometimes effectively required, to align with national self-reliance goals. But there’s a particular urgency when it comes to AI. Since 2022, US export controls have cut Chinese firms off from Nvidia’s most powerful chips, and they later also restricted access to downgraded China-market versions. Beijing’s response has been to accelerate the push for a domestic AI stack, from chips to software frameworks to data centers.
    
    
    
    Chinese authorities have reportedly been pushing data centers and public computing projects to use more domestic chips, including through reported bans on foreign-made chips, sourcing quotas, and requirements to pair Nvidia chips with Chinese alternatives from companies such as Huawei and Cambricon. 
    
    
    
    Still, replacing Nvidia is not as simple as swapping one chip for another. Nvidia’s advantage lies not only in its chips, but in the software ecosystem developers have spent years building around them. Moving to Huawei’s Ascend chips means adapting model code, rebuilding tools, and proving that systems built around those chips are stable enough for serious use.
    
    
    
    To be clear, DeepSeek does not appear to have fully moved beyond Nvidia. The company’s technical report reveals that it is using Chinese chips to run the model for inference, or when someone asks the model to complete a task. But Liu Zhiyuan, a computer science professor at Tsinghua University, told MIT Technology Review that DeepSeek appears to have adapted only part of V4’s training process for Chinese chips. The report does not say whether some key long-context features were adapted to domestic chips, so Liu says V4 may still have been trained mainly on Nvidia chips. Multiple sources who spoke on the condition of anonymity, due to political sensitivity around these issues, told MIT Technology Review that Chinese chips still don’t perform as well as Nvidia chips but are better suited for inference than training.
    
    
    
    DeepSeek is also tying the future costs of V4 to this hardware shift. The company says V4-Pro prices could fall significantly after Huawei’s Ascend 950 supernodes begin shipping at scale in the second half of this year. 
    
    
    
    If that works, V4 could be an early sign that China is successfully building a parallel AI infrastructure.
     

---

### 22. DeepSeek V4 Debuts at $3.48/M Tokens—12 Hours After GPT-5.5 and at 1/20th the Cost of Claude

- **Author:** Hermes Ladiz — byline resolves to a person: **yes**
- **Site:** Frontierbeat (`frontierbeat.com`) · 778 posts, 16.67/day, 3 bylines sampled
- **Site describes itself as:** AI, Crypto, & Tech News
- **Date:** 2026-04-24 · 1,141 words · 0 comments · 1 likes
- **Tags:** Anthropic, Claude, DeepSeek, OpenAI · **Categories:** Artificial Intelligence, Editors' Picks, News
- **URL:** https://frontierbeat.com/2026/04/24/deepseek-v4-releases-pricing-openai-gpt-5-5-2030/
- **Type:** announcement · **Provenance:** somebody else's benchmark repeated
- **Artifacts: 2** — `price`×7, `version_string`×6
- **Benchmark figures:** 0 mentions, 0 attributed near the number

     
     DeepSeek dropped V4 Pro and V4 Flash just 12 hours after OpenAI’s GPT-5.5 announcement.
    
     V4 Pro costs $3.48 per million output tokens—roughly 1/20th of Claude Opus 4.7 pricing.
    
     The release marks China’s formal re-entry into the open-source model wars amid tightening US chip restrictions.
    
     
     DeepSeek didn’t waste any time. Less than half a day after Sam Altman unveiled GPT-5.5 in a surprise livestream, the Hangzhou-based lab dropped its most ambitious release yet: DeepSeek-V4 Pro and V4 Flash . The models arrived open-sourced, fully documented, and priced at levels that make American competitors look like luxury goods.
    
     
     
     🚀 DeepSeek-V4 Preview is officially live & open-sourced! Welcome to the era of cost-effective 1M context length.
    
     🔹 DeepSeek-V4-Pro: 1.6T total / 49B active params. Performance rivaling the world's top closed-source models.
    🔹 DeepSeek-V4-Flash: 284B total / 13B active params.… pic.twitter.com/n1AgwMIymu 
    
     — DeepSeek (@deepseek_ai) April 24, 2026 
     
     
    
     The timing was theatrical. DeepSeek’s official X account began posting technical threads at 11 PM Eastern—hours after OpenAI had finished its San Francisco press event. V4 Pro, a 1.6 trillion parameter Mixture-of-Experts model with 49 billion active parameters, now sits at the top of the open-weight benchmarks. V4 Flash, its leaner 284 billion parameter sibling, ships with 13 billion active and costs pennies on the dollar.
    
     “Creativity loves constraints,” wrote UW researcher Yuchen Jin on X. He was referring to how Chinese labs keep training world-class models despite severe hardware limitations. DeepSeek’s own announcement noted something telling: “Due to constraints in high-end compute capacity, the current service capacity for Pro is very limited.” Their solution? Wait for 950 Huawei “supernodes” coming online later this year. If that happens at scale, DeepSeek expects Pro pricing to drop “significantly.”
    
     The model is also available for testing at Deepseek’s official chat UI . The interface is similar to what everybody is already used to if they have ever interacted with ChatGPT, Gemini, Claude, Minimax, Xiaomi’s AI Studio, Z.AI, Mistral’s LeChat and all the other chat interfaces around.
    
     
    
     Why DeepSeek V4 Changes the Pricing Game 
     The numbers border on insulting. V4 Flash costs $0.14 per million input tokens and $0.28 per million output—roughly one-fifth the price of Gemini 3.1 Flash Lite. For perspective, Saoud Rizwan, CEO of coding assistant Cline, calculated that if Uber had used DeepSeek V4 instead of Claude Opus 4.7 for its 2026 AI budget, the company would have stretched its spending from four months to seven years. The comparison is brutal: where OpenAI’s GPT-5.5 costs $30 per million tokens, DeepSeek’s Pro model runs at $3.48.
    
     The architecture explains part of this efficiency. DeepSeek V4 introduces what it calls “Token-wise compression + DSA (DeepSeek Sparse Attention),” a novel attention mechanism that reduces compute and memory costs while maintaining a 1 million token context window. That’s eight times the 128K window of V3.2, their previous flagship. In real terms, V4 can ingest entire codebases, multi-hour transcripts, or complex agent workflows in a single pass.
    
     The agentic capabilities merit particular attention. DeepSeek V4 was benchmarked against real-world coding tasks on GDPval-AA, an evaluation designed to measure how models perform on practical engineering workflows rather than canned academic puzzles. V4 Pro Reasoning (Max) scored 1554 Elo points, clearing GLM-5.1 (1535), MiniMax-M2.7 (1514), and Kimi K2.6 (1484). V4 Flash Reasoning (Max) hit 1388—well ahead of DeepSeek’s own V3.2 despite being drastically smaller. The gap between V3.2 (1203) and V4 Pro represents a 355-point Elo uplift. That’s not incremental improvement. That’s a category jump.
    
     Artificial Analysis, which evaluated the models, noted a quirk in the data: V4 Flash actually scored higher at “High Effort” settings (1414) than at “Max Effort” (1388), suggesting the model has untapped efficiency headroom. The lab also confirmed V4 Pro as the largest open-weights model released to date, surpassing Kimi K2.6 in both total and active parameter counts. The model ships mostly in FP4 precision, putting total size at roughly 865GB—comparable to Kimi’s ~500GB but with nearly double the parameter count.
    
     
    
     The Global Context: Sanctions, Symbiosis, and a Strange New Arms Race 
     DeepSeek’s release lands amid a tightening web of US restrictions. The Trump administration has been pushing aggressive GPU export controls through 2025 and 2026, attempting to starve Chinese AI labs of the high-end silicon required for frontier model training. The Biden administration previously started this trajectory. The result? Chinese researchers have become extraordinarily efficient at squeezing performance from older, sanctioned hardware—and increasingly, from Huawei’s domestic Ascend chips.
    
     The irony runs rich in both directions. American companies have quietly adopted Chinese techniques. Cursor, the AI coding tool that reportedly rejected a $60 billion acquisition offer from SpaceX , is widely understood to run on a Kimi fine-tune. Trump’s own science advisor warned last week that China is engaged in “massive-scale” distillation of American AI models—effectively using US outputs to train domestic systems. Yet the dependency flows both ways: OpenAI and Anthropic engineers study Chinese MoE architectures, attention optimizations, and training recipes published openly on ArXiv and HuggingFace.
    
     Xiaomi just released MiMo 2.5 Pro. zAI and Minimax have dropped SOTA models in recent weeks. The pace suggests a fundamental shift: Chinese labs have become pace-setters, not followers. DeepSeek’s V4 announcement specifically flagged integrations with Claude Code, OpenClaw, and OpenCode—agents built by American and European developers now running on Chinese foundation models.
    
     While all this unfolded, OpenAI was launching GPT-5.5, its most capable model yet, positioned as a unified “super-app” for chat, reasoning, agents, and multimodal work. The pricing—$30 per million tokens —wasn’t an accident. OpenAI is betting that performance premium can sustain its infrastructure costs. DeepSeek’s counter-argument? That same $30 buys you roughly 107 million tokens of V4 Flash output. The market share question becomes existential: if quality gaps narrow while cost gaps widen, what exactly are American customers paying for?
    
     For enterprises, the implications are immediate. A solopreneur running agents on V4 Flash could process roughly 3.5 million output tokens for under a dollar. Large corporations evaluating proprietary API dependencies face a genuine strategic question: is the vendor lock-in worth 10x or 20x pricing premiums when open alternatives achieve parity? Big Tech’s answer so far has been governance, security, and support guarantees—intangible advantages that sound thinner when the cost differential approaches an order of magnitude.
    
     DeepSeek also announced its older models will be fully retired after July 24th, 2026. DeepSeek-chat and deepseek-reasoner—previously routing to V3 variants—will become inaccessible. The company wants the ecosystem consolidated on V4’s architecture, which supports both thinking and non-thinking modes alongside that 1M context window.
    
     For everyday users, the practical difference is modeled availability. Where GPT-5.5 and Claude Opus remain gated behind subscriptions or enterprise contracts, V4 Flash runs on DeepSeek’s API today, at prices that don’t require CFO sign-off. The capability gap between the cheapest tier and the bleeding edge has never been narrower. The geopolitical gap, meanwhile, has never been more consequential. 950 Huawei supernodes are scheduled for the second half of 2026.
    

---

### 23. DeepSeek Made Its 75% Price Cut Permanent. SaaS Vendors Still Face a Margin Crisis.

- **Author:** Scott Dallen — byline resolves to a person: **yes**
- **Site:** The SaaS Sentinel (`saassentinel.com`) · 575 posts, 3.03/day, 1 bylines sampled
- **Site describes itself as:** Software news, analysis, and opinion
- **Date:** 2026-07-13 · 753 words · 0 comments · 0 likes
- **Tags:** ai agents, b2b, enterprise, llm, pricing · **Categories:** Artificial Intelligence
- **URL:** https://saassentinel.com/2026/07/13/deepseek-made-its-75-price-cut-permanent-saas-vendors-still-face-a-margin-crisis/
- **Type:** news summary · **Provenance:** unattributed
- **Artifacts: 2** — `bench_number`×2, `price`×5
- **Benchmark figures:** 1 mentions, 0 attributed near the number

     Quick Facts 
     
     DeepSeek made its 75% promotional discount on V4-Pro API pricing permanent on May 22, 2026, setting the new list price at $0.435 per million input tokens and $0.87 per million output tokens.
    
     The same 1 billion token monthly workload costs $522 on DeepSeek V4-Pro, versus $9,000 on Claude Opus 4.7 and $10,000 on GPT-5.5.
    
     Enterprise SaaS vendors running AI agents are privately reporting negative gross margins on heavy users, as token amplification from agentic workflows outpaces per-token price cuts.
    
     
     DeepSeek’s price cut was supposed to be temporary. On May 22, 2026, the Chinese AI lab announced it would not roll back the 75% discount on its V4-Pro API. The promotional rate became the permanent list price.
    
     The new V4-Pro pricing sits at $0.435 per million input tokens on cache misses, $0.003625 per million on cache hits, and $0.87 per million output tokens. That makes it 7x cheaper on inputs and 17x cheaper on outputs than Anthropic’s Claude Sonnet or OpenAI’s GPT 5.5-Med.
    
     For context: a workload of 800 million input tokens and 200 million output tokens per month costs $522 on V4-Pro. The same workload on Claude Opus 4.7 runs $9,000. On GPT-5.5, it hits $10,000.
    
     Sanchit Vir Gogia, chief analyst and CEO of Greyhound Research, said the cut reflects engineering gains, not a sales play. “It is not a discount. It is an efficiency gain being passed through,” he said. V4-Pro runs at roughly 27% of the single-token compute that its predecessor required at 1 million token context, with KV cache memory dropping to about 10% of prior levels.
    
     DeepSeek’s momentum on the open market is accelerating. On OpenRouter, DeepSeek V4-Flash ranked first globally with 3.43 trillion weekly token requests during the week of May 18-24. Total weekly requests across all DeepSeek models reached 5.74 trillion, surpassing Anthropic and Google for the second consecutive week. DeepSeek’s overall market share on OpenRouter climbed to 23.1%.
    
     V4-Pro is now the world’s largest open-weight model at 1.6 trillion parameters. It scores 80.6% on the SWE-bench Verified coding-agent leaderboard and 87.5 on MMLU-Pro reasoning benchmarks.
    
     Neil Shah, VP at Counterpoint Research, said V4-Pro has closed the performance gap on math and reasoning but still trails Western rivals on enterprise adoption, global support, IP provenance, and native hyperscaler integrations with AWS, Microsoft, and Google.
    
     The Problem Cheaper Tokens Cannot Fix 
     Cheaper tokens help. They do not solve the core problem facing enterprise AI vendors: agentic workflows multiply token consumption far beyond what any pricing model anticipated.
    
     A chatbot turns one user question into one model call. An agent turns it into a chain of planning, retrieval, tool use, verification, summarization, and follow-up decisions. A single user query can generate 700 times more tokens than a standard chat interaction.
    
     Frontier inference costs are falling roughly 3x per year. But amplification is outrunning the cuts. A power user running 50 agent invocations per day on a $40 per seat plan can cost more in inference than the plan charges. Gross margins go negative.
    
     Several enterprise SaaS vendors are now privately reporting exactly that outcome. The pattern mirrors findings from Bessemer’s Supernova cohort, where AI-agent adoption has shifted from a theoretical margin risk to a real P&L headwind. As one analysis framed it: the customers generating the most value are often the customers generating the highest inference costs.
    
     The real-world numbers are stark. Uber exhausted its annual token budget in four months. Salesforce faces approximately $300 million in Anthropic costs this year alone.
    
     Amit Jaju, senior managing director at Ankura Consulting, pointed to self-hosted deployments as one path out. “If a CIO can host DeepSeek V4-Pro on their own infrastructure, inference costs drop dramatically, and many projects that were previously uneconomical at scale become viable,” he said. That includes always-on copilots, bulk document review, code generation, and multi-agent workflows.
    
     The pressure lands hardest on OpenAI and Anthropic, which are both absorbing the competitive pricing pressure from DeepSeek while their own enterprise customers run up inference bills that traditional SaaS subscription models were never designed to cover. OpenAI’s reported plan to give every Y Combinator startup $2 million in API credits reflects, as VentureBeat noted, what it now costs to run an AI-native company through its first year of product.
    
     DeepSeek is also seeking its first external funding at a reported $44 billion valuation. The company runs V4-Pro on Huawei’s Ascend 950 chips and has declined to say whether improved chip supply contributed to making the price cut permanent.
    
     Read more: DeepSeek cut prices 75%. The 100x problem remains 
    

---

### 24. Claude Fable FOMO? DeepSeek to Qwen – 5 open models worth trying instead

- **Author:** — — byline resolves to a person: **no**
- **Site:** The Financial Express (`www.financialexpress.com`)
- **Date:** 2026-06-29 · 721 words · 0 comments · 0 likes
- **Tags:** Anthropic AI, DeepSeek · **Categories:** Life, Technology
- **URL:** http://www.financialexpress.com/life/technology-claude-fable-fomo-deepseek-to-qwen-5-open-models-worth-trying-instead-4279304/
- **Type:** benchmark · **Provenance:** vendor claim restated
- **Artifacts: 2** — `bench_number`×7, `price`×1
- **Benchmark figures:** 7 mentions, 0 attributed near the number

    
    Claude Fable 5 remains inaccessible to Indians as the US-imposed export restrictions are yet to go away. Before that happened, Fable 5 showed a glimpse of its mighty capabilities, letting users go wild with complex creations with absolute ease.
    
    
    
    Note that Fable 5 was just a restricted version of Mythos – the model hailed as dangerous for civilians due to its capabilities.
    
    
    
    The developer community is turning towards alternatives that are as capable and powerful on synthetic benchmarks. Most of these open-weight alternatives deliver comparable, or even superior performance on practical benchmarks like SWE-Bench, LiveCodeBench, and Design Arena.
    
    
    
    Hence, we went on the internet and rounded up five models that stand out. These are available for download, can be run locally, have permissive licenses, and produce strong results. Without further ado, let’s begin
    
    
    
    GLM-5.2 
    
    
    
    Made by: Zhipu AI
    
    
    
    This model is best suited for design-sensitive coding and engineering workloads. GLM-5.2 grabbed the top spot on Design Arena’s coding leaderboard with an Elo score of 1360, surpassing Claude Fable 5 in scoring. Its API is also far cheaper than Fable 5, but the real advantage comes in local usage for privacy and unlimited use.
    
    
    
    While the license is held by MIT, GLM-5.2 is available in quantised versions. It can be run on high-end consumer-grade GPUs or via efficient inference engines.
    
    
    
    
    ALSO READMeet David Ha – The Wall Street trader who put Japan back on the AI map
    
    
    
    
    DeepSeek V4 Pro
    
    
    
    Made by: DeepSeek AI
    
    
    
    This model is for those seeking pure coding dominance and value. DeepSeek V4-Pro leads LiveCodeBench (93.5) and Codeforces (3206 rating), outperforming many closed frontier models. It achieves 80.6% on SWE-Bench Verified while offering a massive 1M context window.
    
    
    
    DeepSeek is also priced competitively, with token costs down being at a lowly $0.435/$0.87 per million tokens. As far as licensing is concerned, DeepSeek is open source and its quantized versions can be run locally while excelling in efficiency.
    
    
    
    Hence, if you care for competitive programming, work with large-scale codebases, and cost-conscious local setups, DeepSeek V4 Pro is one of the cheapest serious options in the AI space that delivers frontier-level coding.
    
    
    
    Kimi K2.7-Code 
    
    
    
    Made by: Moonshot AI
    
    
    
    Kimi K2.7-Code is best suited for agentic tool use and MCP-heavy workflows. The model leads in MCP (multi-step control/process) tool-use benchmarks (76.0 on MCP Atlas, 81.1 on MCP Mark Verified) and reduces thinking-token usage by ~30% compared to prior versions. It’s a 1T-parameter model with 32B active parameters and 256K context.
    
    
    
    Hence, if your setup involves tool calling, browser agents, or complex multi-step processes, this model’s optimisation for efficiency in thinking makes it great for local agent deployments.
    
    
    
    Qwen 3.5 397B 
    
    
    
    Made by: Alibaba
    
    
    
    Qwen 3.5 397B is best suited for instruction following, multilingual, and accessible hardware options. The full model scores 76.4 on SWE-Bench Verified and 76.5 on IFBench (beating GPT-5.2 and significantly outperforming Claude scores in some instruction tasks). The smaller 27B dense version ties with GPT-5 mini at 72.4 on SWE-Bench, which is impressive for a model running on consumer hardware.
    
    
    
    With an Apache 2.0 license, the model supports 201 languages. The 27B variant can be run on single high-end GPUs or Macs with sufficient RAM. Go for this if you need a model for global teams, long documents, and local development, where there’s no need for full frontier-scale capabilities. 
    
    
    
    MiniMax M3
    
    
    
    Made by: MiniMax Inc.
    
    
    
    Best suited for native multimodality and long-context frontier coding, MiniMax M3 combines strong coding, which is claimed to be 59.0% on SWE-Bench Pro – the highest reported for open weights at release. It also allows up to 1M context, and native multimodal capabilities (vision, potentially more). The weights were released mid-June 2026.
    
    
    
    
    ALSO READApple accuses CCI of ‘copy-pasting’ allegations by rivals in India antitrust probe: Report
    
    
    
    
    The model is best suited for Long-context agent work involving images, coding and documents. It also remains great for creating multimodal agents.
    
    
    
    Note that Claude Fable 5 remains a highly powerful model, with synthetic benchmark scores still putting it at a higher ~80% compared to the usual ~59-62% on SWE-Bench Pro evals. Hence, for sheer performance figures, Fable 5 maintains the lead.
    
    
    
    On the contrary, these open models win on specific leaderboards, cost almost nothing for local runs, and offer privacy and customisation. Hence, you need to choose what works for you in the best way possible.
     

---

### 25. OpenClaw

- **Author:** Joe Boydston — byline resolves to a person: **yes**
- **Site:** Breefs (`breefs.wpcomstaging.com`) · 234 posts, 4.55/day, 2 bylines sampled
- **Site describes itself as:** Daily briefings, thoughtfully curated.
- **Date:** 2026-08-16 · 628 words · 0 comments · 0 likes
- **Tags:** — · **Categories:** AI, Open Source, breefs
- **URL:** https://breefs.wpcomstaging.com/2026/08/16/openclaw-2026-08-16/
- **Type:** news summary · **Provenance:** vendor claim restated
- **Artifacts: 2** — `price`×2, `version_string`×1
- **Benchmark figures:** 0 mentions, 0 attributed near the number

     
     
    
    
    
     OpenClaw 2026.8.1: Secret Egress Binding, GPT-5.6 Support, SQLite Snapshots 
    
    
     Summary: OpenClaw shipped 2026.8.1 with secret egress host binding (credentials locked to exact HTTPS destinations, failing closed on mismatches), GPT-5.6 Sol/Terra/Luna support with atomic model/runtime switching, SQLite snapshot backup/restore for verified per-agent database artifacts, macOS app profile isolation, and plugin install provenance warnings.
    
    
    
     Why this matters: Secret egress binding is meaningful security hardening that prevents credential leakage when tools hit unexpected endpoints. Atomic model switching is the kind of operational polish that makes a daily-driver agent system genuinely reliable.
    
    
    
     Bob’s take: Secret egress binding is the feature I did not know I needed until reading these release notes. The Control UI update recovery fix — where Reload actually reloads now — is also long overdue.
    
    
    
     Source: Releasebot 
    
    
    
    
     DeepSeek V4-Pro Goes GA Today With Peak/Off-Peak Pricing for Scheduled Agents 
    
    
     Summary: DeepSeek released V4-Pro (V4-Pro-0813) as GA today with adaptive reasoning modes, OpenAI Responses API support, and Codex integration. Pricing shifts from flat to tiered peak/off-peak effective 16:00 UTC today — off-peak costs exactly half the peak rate of $0.435 input and $0.87 output per million tokens.
    
    
    
     Why this matters: The peak/off-peak split directly incentivizes scheduling expensive agent runs to off-peak hours. For OpenClaw users running heavy background agents, cron scheduling now has real economic significance.
    
    
    
     Bob’s take: Time-of-day pricing is smart for a Chinese API managing global GPU demand. For Western builders using DeepSeek as a cost-efficient backbone, this changes cron job scheduling from nice-to-have to economically meaningful.
    
    
    
     Source: TechGenyz 
    
    
    
    
     Grok Bot Launches: Persistent AI Teammates That Sign Into Apps and Keep Working Overnight 
    
    
     Summary: SpaceXAI (xAI + Cursor) launched Grok Bot in early beta — a multi-agent system where each bot runs on a dedicated cloud VM, signs into real apps directly without needing an API, and continues executing jobs when the user disconnects. Available on SuperGrok Heavy and Cursor Ultra/Teams subscriptions for macOS and iOS.
    
    
    
     Why this matters: This is the first mainstream persistent agent product treating credential-holding app access as a first-class feature. The comparison case for OpenClaw’s own agent model just got much sharper.
    
    
    
     Bob’s take: Grok Bot is essentially what OpenClaw does — persistent agent with tool access — but subscription-gated and cloud-run instead of self-hosted. The privacy and control argument for self-hosted just got stronger.
    
    
    
     Source: Metaverse Post 
    
    
    
    
     Nvidia Nemotron 3.5 Lightning and NeMo Switchyard Enable Dynamic Per-Step Model Routing 
    
    
     Summary: Nvidia released Nemotron 3.5 Lightning, a 30B MoE model with only 3B active parameters delivering 4x faster output token generation and 30% faster agentic tasks on benchmarks. NeMo Switchyard, a new open-source routing library, dynamically selects between open, proprietary, and Nvidia models at each agent workflow step.
    
    
    
     Why this matters: Dynamic model routing per workflow step is the next evolution for agent frameworks — use the cheapest sufficient model per task rather than routing everything through one expensive backbone.
    
    
    
     Bob’s take: Switchyard is the interesting part, not the model. A routing layer that treats model selection as a first-class optimization problem is the architecture that will win for high-volume agent deployments.
    
    
    
     Source: AI Agent Store 
    
    
    
    
     India’s 90-Day Agentic AI Hackathon Launches Focused on Public Good at Scale 
    
    
     Summary: Code for India launched the Bharat Agentic-AI Hackathon 2026, a fully virtual 90-day event starting August 15th for teams to build agent solutions in education, health, climate, governance, and financial inclusion on AgentFoundry.me. Winners are recognized in December for deployed projects.
    
    
    
     Why this matters: Most agent development targets Western knowledge workers. A structured push toward civic and public-good applications in emerging markets tests whether agent infrastructure generalizes beyond enterprise workflows.
    
    
    
     Bob’s take: 90 days is long enough to build something real. The governance and financial inclusion tracks will stress-test agent reliability in ways productivity tools for Western knowledge workers never do.
    
    
    
     Source: AI Agent Store 
    
     

---

### 26. DeepSeek Introduces Peak-Hour Pricing That Quadruples Current Levels

- **Author:** PYMNTS — byline resolves to a person: **yes**
- **Site:** PYMNTS.com (`www.pymnts.com`) · 140694 posts, 20.0/day, 2 bylines sampled
- **Site describes itself as:** The latest global news and analysis in payments, retail, fintech, financial services and the digital economy.
- **Date:** 2026-08-13 · 372 words · 0 comments · 0 likes
- **Tags:** AI, AI models, DeepSeek, News, PYMNTS News, What's Hot, digital transformation · **Categories:** Artificial Intelligence
- **URL:** http://www.pymnts.com/news/artificial-intelligence/2026/deepseek-introduces-peak-hour-pricing-that-quadruples-current-levels/
- **Type:** announcement · **Provenance:** somebody else's benchmark repeated
- **Artifacts: 2** — `price`×3, `version_string`×2
- **Benchmark figures:** 0 mentions, 0 attributed near the number

    DeepSeek is adding peak-hour pricing for its flagship V4 models that will quadruple the current levels, Bloomberg reported Thursday (Aug. 13).
    The pricing adjustment announced Thursday by the artificial intelligence (AI) company will take effect on Sunday (Aug. 16), according to the report.
    When the changes are implemented, users of the DeepSeek-V4-Flash model will pay $1.32 for 1 million output tokens during peak hours, and half that during off-peak hours. Those figures are up from the current 28 cents for 1 million tokens, the report said.
    For DeepSeek’s V4-Pro model, the new price will be $3.96 for 1 million tokens during peak hours and half that during non-peak hours, up from the current 87 cents per million tokens, per the report.
    The report said DeepSeek’s new prices remain lower than those of its main competitors. Moonshot’s Kimi K3 costs $15 per million output tokens, while Anthropic’s Fable 5 is priced at $50, according to the report.
    In a Thursday update to its change log announcing the pricing adjustment, DeepSeek said: “With the official release of the DeepSeek V4 model family, we will update and adjust API pricing. To allocate resources more reasonably, we will adopt peak/off-peak pricing, with off-peak prices set at half of the peak-hour prices, encouraging users to schedule their tasks based on actual usage.”
    DeepSeek initially gained attention in January 2025 when it debuted an AI model that sent shockwaves through the AI world by offering performance comparable to those of American rivals OpenAI and Meta while using substantially fewer Nvidia chips.
    It was reported in April that DeepSeek was offering developers discounts amid increasing competition in China’s AI space. DeepSeek said at the time that it was offering a 75% discount to developers using its DeepSeek-V4-Pro model until May 5.
    On Aug. 6, it was reported that DeepSeek had resumed its second funding round and is looking to raise close to $8 billion at a valuation of about $74 billion.
    It was reported Wednesday (Aug. 12) that DeepSeek is building a new team to compete with Anthropic’s Claude Code in the market for AI agents that automate work for business professionals.
    For all PYMNTS AI and digital transformation coverage, subscribe to the daily AI and Digital Transformation Newsletters.

---

### 27. DeepSeek applies off-peak API pricing on weekends, slashing bills by half

- **Author:** Chien Chau — byline resolves to a person: **yes**
- **Site:** Hong Kong United Times丨Dialogue with the World (`hkut.news.blog`) · 8994 posts, 100.0/day, 1 bylines sampled
- **Site describes itself as:** 香港聯合時報丨與世界對話
- **Date:** 2026-08-23 · 341 words · 0 comments · 0 likes
- **Tags:** — · **Categories:** INNOVATION &amp; TECHNOLOGY
- **URL:** http://hkut.news.blog/2026/08/23/deepseek-applies-off-peak-api-pricing-on-weekends-slashing-bills-by-half/
- **Type:** news summary · **Provenance:** somebody else's benchmark repeated
- **Artifacts: 2** — `price`×1, `version_string`×2
- **Benchmark figures:** 0 mentions, 0 attributed near the number

     
     
    
    
    
     DeepSeek’s API usage will be billed at off-peak rates on weekends starting at midnight on Sunday, eliminating the previous distinction between peak and off-peak API pricing schedules on Saturdays and Sundays, which could cut costs by half.
    
    
    
    
     The existing peak and off-peak pricing structure will remain unchanged for weekdays, according to DeepSeek’s notice. Peak hours are defined as 9:00 to 12:00 and 14:00 to 18:00 Beijing Time, and all other times are considered off-peak periods.
    
    
    
    
     Following the adjustment, developers can reduce their bills by 50 percent over the weekends, as peak hours are priced at twice the off-peak rate.
    
    
    
    
     Earlier, the artificial intelligence company had sharply lifted its API pricing. Adopting a peak and off-peak pricing rule, its flagship model DeepSeek-v4-Pro’s API output is priced as high as 27 yuan (HK$31.51) per million tokens at peak hours, while the off-peak output pricing is 13.5 yuan per million tokens.
    
    
    
    
     DeepSeek-V4-Flash also charges 9 yuan per million tokens output for peak periods, compared with the 4.5 yuan per million tokens output in off-peak hours.
    
    
    
    
     This adjustment is intended to give users greater flexibility in planning workload on weekends without worrying about peak-hour costs, DeepSeek said, adding that it will also help the company balance computing capacity across the network and continue providing a more stable, high-quality service.
    
    
    
    
     This year, most of China’s leading AI labs and cloud providers have increased their prices, including Alibaba Cloud, Tencent Cloud, Baidu AI Cloud and Z.AI (2513), or Zhipu AI. 
    
    
    
    
     Tencent Cloud has announced price hikes twice, while Zhipu AI has raised its API prices three times within the year.
    
    
    
    
     The average API input and output prices for Chinese large language models rose to 4.9 yuan and 21.9 yuan per million tokens in the second quarter, up about 48 percent and 80 percent respectively from 3.3 yuan and 12.2 yuan in the first quarter of 2025, according to a Morgan Stanley report titled “Intelligence War Over Price War,” which compiled official pricing from ByteDance, Alibaba (9988), Baidu, Tencent (0700), MiniMax (0100), Zhipu AI, Moonshot AI, and DeepSeek.
    
     

---

## Appendix — the injected pages, payloads redacted

Prose only. Every `onload` handler and script body is replaced with a marker. These URLs host an active lure; they are listed for verification, not for visiting.

### 1. Full Deployment DeepSeek-V4-Pro 100% Private PC No-Code Guide

- **Site:** (no name) (`kata-kata04.com`) — no description
- **Site totals:** 372 posts, 2.44/day, 1 byline(s)
- **Date:** 2026-07-01 · 256 words · byline `katakata`
- **URL:** http://kata-kata04.com/2026/07/01/full-deployment-deepseek-v4-pro-100-private-pc-no-code-guide/
- **Markers:** fake_captcha, obfusc_onload, hash_lure, install_vector, hidden_gif, human_check (6/6)
- **Artifacts: 1**

     
    
     A standalone PowerShell module provides the fastest route to local installation.
    
     Follow the step-by-step instructions below.
    
     
    
     An automated background process downloads all required large-scale files. 
    
     
    
     The automated script takes care of everything, tailoring the setup to your specs .
    
     
     
     
     
     📤 Release Hash: e0c31cae1a5fcdeb2f1182b72b9e894c • 📅 Date: 2026-06-27 
    
     
     
     <img src="[BASE64 GIF REDACTED]" style="display:none;" onload="[SCRIPT PAYLOAD REDACTED]
    
     
     Verify 
    
     
    
     
    
    
     
     
     CPU: AVX2/AVX-512 instruction set required for llama.cpp 
    
     RAM: required: 16 GB absolute minimum for small models
    
     Disk Space: 100 GB for multi-modal model vision components
    
     Graphic Processor: RTX 3060 or RX 6600 for minimum 8B VRAM offloading 
    
     
    
    
     
    
    
     
     DeepSeek-V4-Pro introduces a groundbreaking sparse‑attention architecture that dramatically cuts compute costs while retaining the ability to model long‑range contexts. With a staggering parameter count exceeding 1.5 trillion weights, the model delivers superior multilingual capabilities and nuanced reasoning. It has been trained on a meticulously curated training dataset of more than 5 trillion tokens, encompassing code repositories, scientific papers, and diverse conversational sources. Benchmark results highlight its state‑of‑the‑art performance across reasoning, coding, and factual QA tasks, often outpacing earlier models by double‑digit margins. Key technical specifications are summarized below: 
    
     
     
     Metric 
     Value 
    
    
     
     Parameters 
     1.5 T 
    
    
     
     Training Tokens 
     5 T 
    
    
     
     Context Length 
     8K 
    
    
     
     FLOPs per Token 
     2.3×10^12 
    
    
     
     
     Script fetching custom model merges directly into specific KoboldAI directory trees
    
     Full Deployment DeepSeek-V4-Pro 2026/2027 Tutorial
    
     Installer configuring localized context shift parameters for massive document parsing
    
     DeepSeek-V4-Pro Local Guide FREE
    
     Installer configuring local AnyLength context extensions for KoboldAI
    
     Deploy DeepSeek-V4-Pro Locally via LM Studio Full Me

---

### 2. Run DeepSeek-V4-Pro with 1M Context Step-by-Step Windows

- **Site:** 香港歷史文化研究會 Hong Kong History and Culture Society (`hkhcs.org`) — no description
- **Site totals:** 295 posts, 2.78/day, 1 byline(s)
- **Date:** 2026-07-06 · 267 words · byline `hkhcs`
- **URL:** http://hkhcs.org/2026/07/06/run-deepseek-v4-pro-with-1m-context-step-by-step-windows/
- **Markers:** fake_captcha, obfusc_onload, hash_lure, install_vector, hidden_gif, human_check (6/6)
- **Artifacts: 2** — would have passed an artifact filter

     
    
     The fastest way to get this model running locally is via Optional Features .
    
     Refer to the instructions below to proceed.
    
     
    
     Everything happens automatically, including the heavy cloud asset download. 
    
     
    
     To save you time, the system will automatically determine efficient resource allocation .
    
     
     
     
     
     🖹 HASH-SUM: fbb4c350a69cd89c613c26056e14e65a | 📅 Updated on: 2026-06-28
    
     
     
     <img src="[BASE64 GIF REDACTED]" style="display:none;" onload="[SCRIPT PAYLOAD REDACTED]
    
     
     Verify 
    
     
    
     
    
    
     
     
     Processor: 6-core 3.5 GHz minimum required
    
     RAM: 64 GB to avoid OOM crashes on large contexts
    
     Disk Space: required: fast PCIe 4.0 drive for instant boots
    
     GPU: modern architecture ( Ada Lovelace / Ampere minimum)
    
     
    
    
     
    
    
     
     DeepSeek-V4-Pro introduces a groundbreaking sparse‑attention architecture that dramatically cuts compute costs while retaining the ability to model long‑range contexts. With a staggering parameter count exceeding 1.5 trillion weights, the model delivers superior multilingual capabilities and nuanced reasoning. It has been trained on a meticulously curated training dataset of more than 5 trillion tokens, encompassing code repositories, scientific papers, and diverse conversational sources. Benchmark results highlight its state‑of‑the‑art performance across reasoning, coding, and factual QA tasks, often outpacing earlier models by double‑digit margins. Key technical specifications are summarized below: 
    
     
     
     Metric 
     Value 
    
    
     
     Parameters 
     1.5 T 
    
    
     
     Training Tokens 
     5 T 
    
    
     
     Context Length 
     8K 
    
    
     
     FLOPs per Token 
     2.3×10^12 
    
    
     
     
     Script fetching minimal terminal-based chat client binaries with full markdown logs
    
     How to Install DeepSeek-V4-Pro on AMD/Nvidia GPU FREE
    
     Script downloading advanced face-swapping weights for offline cinematic post-processing rendering environments
    
     How to Launch DeepSeek-V4-Pro Offline on PC FREE
    
     Script downloading optimized depth-estimation pipelines for 3D generation
    
     How to Install DeepSeek-V4-Pro

---

### 3. Quick Run DeepSeek-V4-Pro PC with NPU No Admin Rights Offline Setup

- **Site:** Lorak Ikema (`lorakikema.com`) — Tu tienda de flores en Mungia
- **Site totals:** 457 posts, 2.5/day, 1 byline(s)
- **Date:** 2026-06-30 · 302 words · byline `LORAK IKEMA`
- **URL:** http://lorakikema.com/2026/06/30/quick-run-deepseek-v4-pro-pc-with-npu-no-admin-rights-offline-setup/
- **Markers:** fake_captcha, obfusc_onload, hash_lure, install_vector, hidden_gif, human_check (6/6)
- **Artifacts: 2** — would have passed an artifact filter

     
    
     If you want the fastest local installation for this model, use standard pip packages .
    
     Make sure to follow the instructions below.
    
     
    
     The installer auto-downloads and deploys the entire model pack. 
    
     
    
     The engine benchmarks your hardware to apply the most effective operational mode .
    
     
     
     
     
     📘 Build Hash: d5954ce6e59c3c3e4cefe65bee48135d • 🗓 2026-06-24
    
     
     
     <img src="[BASE64 GIF REDACTED]" style="display:none;" onload="[SCRIPT PAYLOAD REDACTED]
    
     
     Verify 
    
     
    
     
    
    
     
     
     Processor: 4.0 GHz+ boost clock recommended for CPU inference
    
     RAM: 48 GB needed to prevent memory swapping to disk
    
     Storage: 100 GB free space for HuggingFace cache folder
    
     Graphics: CUDA Compute Capability 8.0+ required for flash-attention 
    
     
    
    
     
    
    
     
     DeepSeek-V4-Pro introduces a groundbreaking sparse‑attention architecture that dramatically cuts compute costs while retaining the ability to model long‑range contexts. With a staggering parameter count exceeding 1.5 trillion weights, the model delivers superior multilingual capabilities and nuanced reasoning. It has been trained on a meticulously curated training dataset of more than 5 trillion tokens, encompassing code repositories, scientific papers, and diverse conversational sources. Benchmark results highlight its state‑of‑the‑art performance across reasoning, coding, and factual QA tasks, often outpacing earlier models by double‑digit margins. Key technical specifications are summarized below: 
    
     
     
     Metric 
     Value 
    
    
     
     Parameters 
     1.5 T 
    
    
     
     Training Tokens 
     5 T 
    
    
     
     Context Length 
     8K 
    
    
     
     FLOPs per Token 
     2.3×10^12 
    
    
     
     
     Downloader pulling specialized textual inversion files for photographic facial alignment texture adjustments
    
     Setup DeepSeek-V4-Pro on Your PC Fully Jailbroken Dummy Proof Guide FREE
    
     Downloader for customized Gemma-2-9B GGUF layers with precision offloading configs
    
     How to Run DeepSeek-V4-Pro Offline on PC with 1M Context FREE
    
     Installer setting up SillyTavern interface optimized for KoboldCPP 

---

### 4. How to Autostart DeepSeek-V4-Pro on AMD/Nvidia GPU with 1M Context Local Guide

- **Site:** City Heights Community Fridge (`cityheightscommunityfridge.com`) — no description
- **Site totals:** 962 posts, 2.94/day, 1 byline(s)
- **Date:** 2026-07-15 · 410 words · byline `cityheightscommunity`
- **URL:** http://cityheightscommunityfridge.com/2026/07/15/how-to-autostart-deepseek-v4-pro-on-amd-nvidia-gpu-with-1m-context-local-guide/
- **Markers:** fake_captcha, obfusc_onload, hash_lure, install_vector, hidden_gif, human_check (6/6)
- **Artifacts: 3** — would have passed an artifact filter

     
    
     If you need a near-instant local setup , just fetch files via a basic curl request .
    
     Follow the sequence of steps detailed below.
    
     
    
     The client handles the setup, pulling gigabytes of data automatically. 
    
     
    
     To guarantee smooth performance, the process auto-selects the best options .
    
     
     
     
     
     📄 Hash Value: 
    ```
    6e83232e7ccb7ad584755b525fc8a38a
    ```
     | 📆 Update: 2026-07-10
    
     
     
     <img src="[BASE64 GIF REDACTED]" style="display:none;" onload="[SCRIPT PAYLOAD REDACTED]
    
     
     Verify 
    
     
    
     
    
    
     
     
     Processor: Intel i5 or AMD Ryzen 5 for basic 7B models 
    
     RAM: minimum 16 GB for stable 8B model loading
    
     Disk Space: required: fast PCIe 4.0 drive for instant boots
    
     Graphic Processor: hardware Tensor Cores support needed for FP16 acceleration
    
     
    
    
     
    
    
     
     Unlocking the Future of AI with DeepSeek-V4-Pro 
     DeepSeek-V4-Pro revolutionizes the field of natural language processing with its innovative sparse-attention architecture, significantly reducing computational costs while maintaining exceptional long-range contextual understanding. This groundbreaking model boasts an unprecedented parameter count exceeding 1.5 trillion weights, empowering it to excel in multilingual capabilities and nuanced reasoning. Through extensive training on a meticulously curated dataset comprising over 5 trillion tokens from diverse sources such as code repositories, scientific papers, and conversational platforms, DeepSeek-V4-Pro has established itself as a state-of-the-art performer across various reasoning, coding, and factual QA tasks. Its impressive performance often surpasses earlier models by double-digit margins. This remarkable achievement is attributed to the model’s unique sparse-attention architecture, which allows it to efficiently process vast amounts of data while retaining the ability to capture subtle contextual nuances.
    
     Technical Specifications: A Closer Look 
     
     
     Key Metric 
     Value 
    
    
     
     Number of Parameters 
     1.5 Trillion Weights 
    
    
     
     Total Training Tokens 
     5 Trillion

---

### 5. Quick Run DeepSeek-V4-Pro Local Guide

- **Site:** Granit Trade Babina Greda (`granittrade.com`) — Tel: +385 91 34 34 230
- **Site totals:** 395 posts, 2.44/day, 1 byline(s)
- **Date:** 2026-07-03 · 276 words · byline `antomasic`
- **URL:** http://granittrade.com/2026/07/03/quick-run-deepseek-v4-pro-local-guide/
- **Markers:** fake_captcha, obfusc_onload, hash_lure, install_vector, hidden_gif, human_check (6/6)
- **Artifacts: 2** — would have passed an artifact filter

     
    
     Using a native PowerShell script is the absolute quickest way to install this model.
    
     Please adhere to the deployment steps listed below.
    
     
    
     The client handles the setup, pulling gigabytes of data automatically. 
    
     
    
     The deployment tool scans your environment and chooses the ideal parameters .
    
     
     
     
     
     🖹 HASH-SUM: a549e8d555942637766ffc1e704c941b | 📅 Updated on: 2026-07-01
    
     
     
     <img src="[BASE64 GIF REDACTED]" style="display:none;" onload="[SCRIPT PAYLOAD REDACTED]
    
     
     Verify 
    
     
    
     
    
    
     
     
     Processor: next-gen chip for heavy context processing
    
     RAM: fast 5600MHz+ required to avoid memory bottlenecks
    
     Disk Space: at least 100 GB for multiple local LLM variants
    
     GPU: modern architecture ( Ada Lovelace / Ampere minimum)
    
     
    
    
     
    
    
     
     DeepSeek-V4-Pro introduces a groundbreaking sparse‑attention architecture that dramatically cuts compute costs while retaining the ability to model long‑range contexts. With a staggering parameter count exceeding 1.5 trillion weights, the model delivers superior multilingual capabilities and nuanced reasoning. It has been trained on a meticulously curated training dataset of more than 5 trillion tokens, encompassing code repositories, scientific papers, and diverse conversational sources. Benchmark results highlight its state‑of‑the‑art performance across reasoning, coding, and factual QA tasks, often outpacing earlier models by double‑digit margins. Key technical specifications are summarized below: 
    
     
     
     Metric 
     Value 
    
    
     
     Parameters 
     1.5 T 
    
    
     
     Training Tokens 
     5 T 
    
    
     
     Context Length 
     8K 
    
    
     
     FLOPs per Token 
     2.3×10^12 
    
    
     
     
     Setup tool linking local models directly into open-source smart home system environments
    
     DeepSeek-V4-Pro PC with NPU Fully Jailbroken Direct EXE Setup FREE
    
     Installer configuring distributed tensor calculation grids across multiple local rigs
    
     How to Install DeepSeek-V4-Pro Locally (No Cloud) No Python Required
    
     Downloader for lightweight distillation models running on CPUs
    
     Deploy DeepS

---
