# Independent blog writing about DeepSeek V4 Pro

**Standalone run, for manual evaluation. Nothing here reached the database.**

Discovery through HN Algolia, collection through each host's own RSS/Atom feed.
The scripts import nothing from `collect/` or `judge/`, open no database
connection, and write only this file plus a scratchpad. `contract/sources.yaml`
carries no ruling for Algolia or for any host read here, so
`assert_terms_reviewed()` did not run and **none of this is admissible to the
pipeline** - it is evidence about whether the route works, not evidence about
models.

*Run 2026-09-02 · 72 HTTP requests · $0.00 · no API key, no account*

---

## The counts

```
hosts discovered           68   distinct hosts across 130 linked HN stories
hosts independent          15   after dropping 53 by hand classification
hosts kept                  8   those with >=2 model-naming titles on HN
feeds read                  8   13 feed URLs; 3 hosts declare more than one
posts matched               26  22 via RSS + 4 recovered from HN URLs
distinct authors            9   incl. 1 organisational byline
  of those, human           8  
posts with no author        2  
first-hand (own use or own
  measurement)              23  excludes the 2 automated-judge posts
carrying >=2 artifacts      19  full text included below
about the model             16  the other 10 name it in passing
benchmark figures           18  of which 9 name a source nearby

THE DECIDING COUNT
own measurement of a model   12  benchmark or first-hand analysis, own result
  ...and about V4            9   across 5 hosts and 7 named voices
```

**It is thin, and the thinness is the result.** 26 posts sounds like a corpus and
is not one. `first-hand` counts 23 because most of it is somebody using V4 to do
something else and writing up the something else - six tutorials about OpenCode
workflows, an essay on inference margins, a post about steering vectors.

The number that decides whether this route is worth anything is **9**: posts
that measure DeepSeek V4 first-hand and are about the model. They come from **5
hosts** — `grigio.org`, `lucebox.com`, `quesma.com`, `simonwillison.net`, `theaq.blog` — and
**7 distinct byline strings** - which resolve to 6 people, because one
`quesma.com` byline names two of them and the other two posts name them
separately. That is the `byline_source: entry` problem `contract/sources.yaml`
already records for `blog:hamel.dev` and `blog:slack.engineering`: several
authors per feed and no per-document mapping, so a byline string is not a voice
until somebody resolves it. Counted as people, subtract the two that do not
count as new independent evidence:
`simonwillison.net` is already a subscribed feed, and `lucebox.com`
sells the $6,499 box its three benchmarks favour. **Net new independent hosts
measuring this model: three** — `theaq.blog`, `quesma.com`, `grigio.org`.

Four hosts yielding six usable posts was the shape you predicted. It is closer to
three hosts yielding six.

---

## 1 · Discovery

`https://hn.algolia.com/api/v1/search` with `tags=story`, free, no key, 10,000
requests/hour. Three queries:

| query | `nbHits` | returned |
|---|---|---|
| `DeepSeek V4 Pro` | 88 | 88 |
| `deepseek-v4-pro` | 52 | 52 |
| `DeepSeek V4` | 198 | 100 |

**Those hit counts are not match counts.** Algolia prefix-matches query tokens,
so `pro` matches *problem* and *production*, and all three queries returned
`exhaustiveNbHits: false`. Treat them as an upper bound on an unverified
population. What the three actually returned: **240 story records → 147 unique
`objectID`s → 130 carrying an outbound URL → 68 distinct hosts.**

### What was dropped, and why

53 of 68 hosts are not independent writing. Hand classification, recorded so the
call can be disagreed with:

| reason | n | hosts |
|---|---|---|
| vendor | 14 | `aiomniu.top`, `api-docs.deepseek.com`, `api-hub.cc`, `cdn.deepseek.com`, `chat.deepseek.com`, `deepinfra.com`, `fireworks.ai`, `helloai.com`, `hpc-ai.com`, `inferize.ai`, `kucoin.com`, `openrouter.ai`, `runinfra.ai`, `techcommunity.microsoft.com` |
| code-host | 3 | `esengine.github.io`, `github.com`, `oskrim.github.io` |
| model-card | 1 | `huggingface.co` |
| benchmark-aggregator | 5 | `arcprize.org`, `artificialanalysis.ai`, `deepswe.datacurve.ai`, `foodtruckbench.com`, `lmsys.org` |
| social | 5 | `forums.developer.nvidia.com`, `old.reddit.com`, `reddit.com`, `twitter.com`, `xcancel.com` |
| news-outlet | 7 | `ghacks.net`, `reuters.com`, `technode.com`, `technologyreview.com`, `thenextweb.com`, `tomshardware.com`, `venturebeat.com` |
| company-product | 13 | `antigma.ai`, `benzi.fly.dev`, `blog.kilo.ai`, `blog.n.ichol.ai`, `cactuscompute.com`, `camelai.com`, `copilot.simplepdf.com`, `ctgt.ai`, `ebookaloud.com`, `firethering.com`, `getaivo.dev`, `quicksilverpro.io`, `rtrvr.ai` |
| content-farm | 3 | `ainexusdaily.vercel.app`, `deepseek-v4-pro-127cubed.vercel.app`, `plane-war-9t2.pages.dev` |
| institutional | 1 | `nist.gov` |
| preprint | 1 | `arxiv.org` |
| substack-terms-refused | 2 | `howardchen.substack.com`, `simonw.substack.com` |

`substack-terms-refused` is the one drop that is not about content quality.
`howardchen.substack.com` and `simonw.substack.com` are ordinary blog posts. They
are dropped because Substack's Acceptable Use Policy prohibits conduct that
"'Crawls,' 'scrapes,' or 'spiders' any page, data, or portion of Substack
(through use of manual or automated means)" and that "Copies or stores any
significant portion of the content" - terms we have read. Two Substack posts in
130 linked stories was not worth taking that on. Note the second is Simon
Willison's mirror of a blog we already subscribe to.

### The repeat-coverage screen

A host appearing once is not worth a feed read, so each of the 15 independent
hosts was screened on how much it writes about models at all.

**Denominator, and it is the important line in this file:** these are stories
from that host **that an HN user submitted and Algolia indexed**, capped at 100
per query. They are *not* the host's output. A blog could publish fifty model
posts and have two submitted. `>=100` is the cap, so it is a floor, not a count.
`model-naming titles` is a title-only regex over a model-family vocabulary, so it
misses body-only mentions and over-counts posts that name a model while being
about something else.

| host | HN-indexed stories | model-naming titles | kept |
|---|---|---|---|
| `simonwillison.net` | >=100 | 27 | **yes** |
| `quesma.com` | 76 | 25 | **yes** |
| `runtimewire.com` | 91 | 18 | **yes** |
| `grigio.org` | 77 | 11 | **yes** |
| `seangoedecke.com` | >=100 | 7 | **yes** |
| `theaq.blog` | 5 | 4 | **yes** |
| `dataleadsfuture.com` | 4 | 2 | **yes** |
| `lucebox.com` | 5 | 2 | **yes** |
| `0xsid.com` | 19 | 1 | no |
| `annajc.com` | 1 | 1 | no |
| `eddieoz.com` | 12 | 1 | no |
| `fergusfinn.com` | 26 | 1 | no |
| `flashblaze.xyz` | 9 | 1 | no |
| `knightli.com` | 2 | 1 | no |
| `ronreiter.com` | 10 | 1 | no |

Seven hosts were dropped at exactly one model-naming title: `0xsid.com`,
`annajc.com`, `eddieoz.com`, `fergusfinn.com`, `flashblaze.xyz`, `knightli.com`,
`ronreiter.com`. Each wrote the one post the search found. Subscribing to those
feeds pays a review cost and then delivers nothing further on models.

---

## 2 · Collection, and the thing RSS cannot do

Every host: `robots.txt` read first, one request per second per host, feed
discovered from the HTML head where declared and by probing common paths
otherwise. **All 11 `robots.txt` reads returned HTTP 200 with rules present, and
no host refused any path we fetched.** None of these hosts has the 404 problem
`blog-class-a-self-hosted` records for `engineering.grab.com`, where robots is
silent and the class reading carries the whole weight - every one of them
answered with an actual crawl policy. That is mechanical evidence about a
server's stated policy and **not** a terms reading; no terms page was read for
any host here, exactly as the class-A ruling says of the nine already seeded.
Three hosts declare several
feeds - `runtimewire.com` declares four - so all declared feeds were read and
unioned; taking the first would have lost 51 of its 85 entries.

**The six-month window was specified and RSS cannot deliver it.** A feed carries
the most recent N entries, not a date range, and for a frequent publisher that is
days:

| host | feed(s) | entries | oldest entry | newest | reaches back | 6 months? |
|---|---|---|---|---|---|---|
| `dataleadsfuture.com` | 1 | 15 | 2025-11-28 | 2026-09-01 | 278 days | yes |
| `grigio.org` | 1 | 15 | 2026-08-03 | 2026-08-31 | 30 days | **no** |
| `lucebox.com` | 1 | 17 | 2026-04-13 | 2026-08-28 | 142 days | **no** |
| `quesma.com` | 1 | 71 | 2023-10-31 | 2026-08-28 | 1037 days | yes |
| `runtimewire.com` | 4 | 139 | 2026-05-26 | 2026-09-02 | 99 days | **no** |
| `seangoedecke.com` | 3 | 90 | 2026-06-01 | 2026-08-30 | 93 days | **no** |
| `simonwillison.net` | 1 | 30 | 2026-08-19 | 2026-09-02 | 14 days | **no** |
| `theaq.blog` | 1 | 10 | 2026-08-17 | 2026-08-28 | 16 days | **no** |

So **6 of 8 feeds cannot see six months back**, and the two shortest windows
belong to two of the most valuable hosts: `simonwillison.net` at 14 days and `theaq.blog` at 16.
Willison's *"DeepSeek V4 — almost on the frontier"* - the
highest-scoring independent post HN discovery surfaced, at 677 points - is four
months outside his feed window and **RSS cannot fetch it at all**.

A second gap: `runtimewire.com` serves a summary-only feed (median entry 551
chars), so its teasers omit the model name and surface-matching on feed text
never triggers the page fetch. Its feed matched **0 of 85 in-window entries**
while HN shows 18 model-naming titles from that host.

Both are absences **this method caused**, not absences in the world, and
discovery had already handed over the URLs. So a second labelled pass fetched 6
HN-discovered URLs on kept hosts that the feeds did not carry; 2 were duplicates
of feed posts under different HN titles, leaving **4 net new**, marked
`hn-url` in the table below. Everything else came from RSS as specified.

### Hosts needing the post page fetched for full text

`lucebox.com`, `quesma.com` and `simonwillison.net` (and `seangoedecke.com` for
one post) carry summaries or short entries, so the post page was fetched. 
`dataleadsfuture.com`, `grigio.org` and `theaq.blog` ship full content in the
feed. Bylines forced extra fetches too: only `simonwillison.net` declares an
author in its feed, so the page was fetched for the byline everywhere else.

---

## 3 · Every post

`artifacts` counts *kinds* present, not instances - benchmark figures, prices,
version strings, code fences, error output, a comparison with conditions
attached. `figs` is benchmark figures found, and `cited` how many name a source
within 300 characters either side. Both are mechanical detectors; the type,
whose-result and relevance columns are my reading.

| # | host | date | title | author | type | whose result | about V4? | artifacts | figs/cited | via |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `dataleadsfuture.com` | 2026-04-15 | [How I Use OpenCode, Oh-My-OpenCode-Slim, and OpenSpec to Bui](https://www.dataleadsfuture.com/how-i-use-opencode-oh-my-opencode-slim-and-openspec-to-build-my-own-ai-coding-environment/) | Peng Qian | tutorial | author's own use | passing | **2** code_,versi | 0/0 | rss |
| 2 | `dataleadsfuture.com` | 2026-05-29 | [Reflection SDD: Use a Reflection Harness to Level Up Your Op](https://www.dataleadsfuture.com/reflection-sdd-use-a-reflection-harness-to-level-up-your-openspec-workflow/) | Peng Qian | tutorial | author's own use | yes | **2** code_,versi | 0/0 | rss |
| 3 | `dataleadsfuture.com` | 2026-06-15 | [DeepSeek-V4 Can't Read Images? I Made It Read](https://www.dataleadsfuture.com/deepseek-v4-cant-read-images-i-made-it-read/) | Peng Qian | tutorial | author's own use | yes | **2** code_,versi | 0/0 | rss |
| 4 | `dataleadsfuture.com` | 2026-07-15 | [No Plugins Needed, I Built a Fully Automated Coding Loop in ](https://www.dataleadsfuture.com/no-plugins-needed-i-built-a-fully-automated-coding-loop-in-opencode/) | Peng Qian | tutorial | author's own use | passing | **2** code_,versi | 0/0 | rss |
| 5 | `dataleadsfuture.com` | 2026-07-31 | [How I Cut Kimi K3 Costs in OpenCode](https://www.dataleadsfuture.com/how-i-cut-kimi-k3-costs-in-opencode/) | Peng Qian | tutorial | author's own use | passing | **2** code_,versi | 0/0 | rss |
| 6 | `dataleadsfuture.com` | 2026-09-01 | [From OpenSpec to AIDLC: How I Improved My Team's AI Code Qua](https://www.dataleadsfuture.com/from-openspec-to-aidlc-how-i-improved-my-teams-ai-code-quality/) | Peng Qian | tutorial | author's own use | passing | **1** code_ | 0/0 | rss |
| 7 | `grigio.org` | 2026-08-04 | [DeepSeek V4 Flash 0731: Is It Cheaper to Run It at Home or P](https://grigio.org/deepseek-v4-flash-0731-is-it-cheaper-to-run-it-at-home-or-pay-per-token/) | Luigi | first-hand analysis | own calculation + restated vendor/community claims | yes | **4** bench,code_,price,versi | 1/1 | rss |
| 8 | `grigio.org` | 2026-08-08 | [Which is the BEST Coding harness for Deepseek V4 ? opencode ](https://grigio.org/which-is-the-best-coding-harness-for-deepseek-v4-opencode-vs-pi-vs-jcode-vs-reasonix/) | Luigi | announcement | author's own use | yes | **1** versi | 0/0 | rss |
| 9 | `grigio.org` | 2026-08-13 | [Same Prompt, Same Model, Wildly Different Results: I Put 5 A](https://grigio.org/same-prompt-same-model-wildly-different-results-i-put-5-ai-coding-harnesses-to-the-test/) | Luigi | news summary | author's own use, written up in third person | passing | **0**  | 0/0 | rss |
| 10 | `grigio.org` | 2026-08-21 | [Which is the best AI HARNESS ? Ship benchmark with codex, jc](https://grigio.org/which-is-the-best-ai-harness-ship-benchmark-with-codex-jcode-pi-opencode-dsh/) | Luigi | announcement | author's own use | yes | **1** versi | 0/0 | rss |
| 11 | `lucebox.com` | 2026-05-20 | [Gemma 4 26B edges out DeepSeek V4 Flash (284B) on ds4-eval-9](https://www.lucebox.com/blog/gemma-vs-deepseek/) | Davide Ciffa | benchmark | own measurement (vendor sells the winning hardware) | yes | **4** bench,code_,compa,versi | 7/3 | rss |
| 12 | `lucebox.com` | 2026-07-16 | [DeepSeek V4 Flash: 284B model, up to 32 tok/s on AMD Ryzen A](https://www.lucebox.com/blog/deepseek-v4-strix-halo/) | Davide Ciffa | benchmark | own measurement (vendor sells the hardware) | yes | **3** bench,code_,versi | 3/1 | rss |
| 13 | `lucebox.com` | 2026-07-20 | [Lucebox (AMD Radeon AI PRO R9700 + Strix Halo) Beats NVIDIA ](https://www.lucebox.com/blog/deepseek-v4-asymmetric-parallelism/) | Davide Ciffa | benchmark | own measurement (vendor sells the winning hardware) | yes | **4** bench,code_,price,versi | 1/1 | rss |
| 14 | `quesma.com` | 2026-07-31 | [Kimi K3 is Open, Opus 5 is Good, DeepSeek V4 Flash is Cheap:](https://quesma.com/blog/baba-kimi-k3-opus-5/) | Piotr Migdał, Piotr Grabowski | benchmark | own measurement | yes | **3** bench,price,versi | 2/0 | rss |
| 15 | `quesma.com` | 2026-07-31 | [A lesson about retries, hidden in the DeepSeek-V4 paper](https://quesma.com/blog/hidden-lesson-deepseek-paper/) | Piotr Grabowski | first-hand analysis | own experiment TESTING a vendor claim | yes | **2** price,versi | 0/0 | rss |
| 16 | `quesma.com` | 2026-08-20 | [Gemini 3.7 Flash, Grok 4.6, GLM-5.3 and DeepSeek V4 Pro join](https://quesma.com/blog/baba-is-aug-2026/) | Piotr Migdał | benchmark | own measurement | yes | **3** bench,price,versi | 2/2 | rss |
| 17 | `runtimewire.com` | 2026-06-08 | [DeepSeek V4 Pro beats GPT-5.5 Pro on precision](https://runtimewire.com/article/deepseek-v4-pro-beats-gpt-5-5-pro-on-precision) | RuntimeWire | benchmark | automated LLM-judge matchup, no human author | yes | **1** versi | 0/0 | **hn-url** |
| 18 | `runtimewire.com` | 2026-07-10 | [Head to Head: Muse Spark 1.1 vs. DeepSeek-V4-Pro](https://runtimewire.com/article/head-to-head-muse-spark-1-1-vs-deepseek-v4-pro) | RuntimeWire | benchmark | automated LLM-judge matchup, no human author | yes | **2** price,versi | 0/0 | **hn-url** |
| 19 | `seangoedecke.com` | 2026-05-16 *(HN submission date)* | [DeepSeek-V4-Flash means LLM steering is interesting again](https://www.seangoedecke.com/steering-vectors/) | *none found* | opinion | author's own reading of a third-party project | passing | **1** versi | 0/0 | **hn-url** |
| 20 | `seangoedecke.com` | 2026-06-26 | [AI inference is obviously profitable](https://seangoedecke.com/ai-inference-is-obviously-profitable/) | *none found* | first-hand analysis | own cost estimate | passing | **2** price,versi | 0/0 | rss |
| 21 | `simonwillison.net` | 2026-04-24 *(from URL path)* | [DeepSeek V4 – almost on the frontier](https://simonwillison.net/2026/Apr/24/deepseek-v4/) | Simon Willison | first-hand analysis | own test + vendor prices WITH the source linked | yes | **3** code_,price,versi | 0/0 | **hn-url** |
| 22 | `simonwillison.net` | 2026-08-28 | [Just a rumour of a bug is enough to find a security exploit ](https://simonwillison.net/2026/Aug/28/just-a-rumour-of-a-bug/) | Simon Willison | opinion | third-party result restated | passing | **2** price,versi | 0/0 | rss |
| 23 | `theaq.blog` | 2026-08-18 | [Evaluating DeepSeek V4 Pro 0813 on Hack The Box Challenges](https://theaq.blog/2026/08/18/evaluating-deepseek-deepseek-v4-pro-0813-on-hack-the-box-challenges.html) | TheArtificialQ | benchmark | own measurement | yes | **4** bench,code_,price,versi | 1/0 | rss |
| 24 | `theaq.blog` | 2026-08-20 | [What Does the HTB-Challenger Benchmark Actually Measure?](https://theaq.blog/2026/08/20/what-does-htb-challenger-benchmark-actually-measure.html) | TheArtificialQ | methodology | own measurement | yes | **1** versi | 0/0 | rss |
| 25 | `theaq.blog` | 2026-08-21 | [Evaluating Ox Alpha on Hack The Box Challenges](https://theaq.blog/2026/08/21/evaluating-stealth-ox-alpha-on-hack-the-box-challenges.html) | TheArtificialQ | benchmark | own measurement | passing | **4** bench,code_,price,versi | 1/1 | rss |
| 26 | `theaq.blog` | 2026-08-25 | [Evaluating MiniMax M3 on Hack The Box Challenges](https://theaq.blog/2026/08/25/evaluating-minimax-minimax-m3-on-hack-the-box-challenges.html) | TheArtificialQ | benchmark | own measurement | passing | **3** code_,price,versi | 0/0 | rss |

### Per-host reading

**`dataleadsfuture.com`** — Personal technical blog (Peng Qian). Tutorials on OpenCode/OpenSpec workflows in which DeepSeek V4 is the model being driven.

**`grigio.org`** — Companion blog to a YouTube channel (Luigi). One substantial cost analysis; three posts are stubs or generated video summaries.

**`lucebox.com`** — COMPANY PRODUCT BLOG, reclassified on reading. Lucebox sells the $6,499 inference box its benchmarks win with. Artifact-dense and unusually explicit about conditions - and a vendor benchmarking its own hardware.

**`quesma.com`** — Company blog (Quesma) running an original LLM benchmark series, BabaIsBench, on the puzzle game Baba Is You. Two named human authors.

**`runtimewire.com`** — NOT independent human writing, reclassified on reading. An automated LLM-judge matchup publisher: organizational byline, AI-generated illustrations, ~139 posts in 99 days, summary-only feed.

**`seangoedecke.com`** — Personal blog. No byline in the feed or in the page markup.

**`simonwillison.net`** — ALREADY IN contract/sources.yaml as blog:simonwillison.net. Included because excluding a subscribed feed would hide evidence, not because it is a new candidate.

**`theaq.blog`** — Personal benchmark blog (TheArtificialQ) running its own HTB-Challenger Benchmark over Hack The Box security challenges.

---

## 4 · Where the numbers come from

The question was whether a post quoting a figure says where the figure came from.
**18 benchmark figures were detected across 26 posts; 9 name a source nearby.**
That ratio is not the interesting part, because the detector is crude. The
interesting part is that the disputed figure never appears.

**Not one of the 26 posts quotes SWE-bench Verified for this model.** The
80.6% / 91.2% / 62.7-on-DeepSWE spread came from vendor and SEO pages -
`mindstudio.ai`, `deepinfra.com`, `deepseekai.guide`, `302.AI` on Medium - and
every one of those hosts is in the drop table above. The independent blogs do not
recirculate the number. **They run their own evaluations instead**, which is why
their figures disagree with the vendor's without contradicting each other: they
are measuring different things and mostly say which.

Three posts handle provenance well enough to be worth copying:

- **`grigio.org`** opens with a reviewer note drawing the line explicitly: *"I
  re-ran every calculation in this post myself ... I couldn't independently
  verify external claims like the model specs, API pricing, Unsloth's GGUF
  measurements, or August 2026 hardware street prices, so those are repeated
  from the cited sources."*
- **`theaq.blog`** flags vendor benchmarks as vendor benchmarks - *"DeepSeek
  reports large improvements across several agent benchmarks, although those are
  the developer's own results"* - and publishes a separate post on what his own
  benchmark's population is and why it disagrees with official numbers.
- **`quesma.com`** quotes the V4 paper verbatim and then spends $6.06 and 100,000
  generations testing whether the claim holds.

And one that fails it, in a way worth recording because it looks like data:

**`runtimewire.com` publishes two matchups a month apart that contradict each
other on the same capability.** June: *"DeepSeek V4 Pro wins this head-to-head by
being more exact where it matters: following instructions, matching schemas"*,
38.0 to 33.0. July: *"it lost on avoidable compliance failures"*, 11-1 against
Muse Spark 1.1, 110.8 to 84.3, with **"100% confidence, decisive"** - a
statistical claim that names no test, no run count and no population. Both are
LLM-judge outputs published under an organisational byline. Different opponents
could explain the reversal, and neither page gives the conditions that would let
a reader check. This is the failure the board exists to avoid: a number that
survives a spot-check and answers a question nobody asked.

---

## 5 · What this says about the route

- **Discovery worked and is nearly free.** 3 requests → 68 hosts; 72 requests
  → this file. No key, no account, no ruling needed as long as only the hostname
  crosses over.
- **The screen worked.** 7 hosts dropped at one model-naming title each, and
  reading confirms the two lowest-scoring kept hosts (`lucebox.com` at 2,
  `dataleadsfuture.com` at 2) are the ones whose independence is questionable or
  whose posts are only incidentally about the model.
- **The screen also passed two hosts it should not have.** `runtimewire.com`
  (18 model-naming titles) is an automated judge with no human author, and
  `lucebox.com` sells the hardware. An HN-title regex cannot see either. Both
  needed a human to read one post.
- **RSS is the wrong collection mechanism for a back catalogue.** It reaches 14
  to 16 days on the hosts that write most often. For a named model, the specific
  URLs are what you want, and discovery already produces them.
- **Authors are mostly absent.** 1 of 8 feeds declares one. Six posts have a
  byline only because the page was fetched for it, and `seangoedecke.com` has
  none anywhere - inferring "Sean Goedecke" from the domain would manufacture
  the byline, the same call `blog:vickiboykis.com` already records.
- **On the corroboration gate this changes little on its own.** The usable
  first-hand V4 capability posts come from 5 hosts and 6 people, against
  `N_EFF_MINIMUM = 3.0` needing roughly nine independent voices at the best tier,
  and `PLATFORM_MINIMUM = 2`. It is a real addition to a 4-voice blog corpus and
  it is not a distribution.

## 6 · Methods note: one defect found and fixed mid-run

The first pass reported benchmark figures in `seangoedecke.com` and `grigio.org`
that do not exist. The detector's `AIME` alternative was unanchored, so it
matched inside **cl*aime*d** - `"claimed 70% or 80% profit margin"` was read as
an AIME score. Word-boundarying every benchmark name changed **7 of 26 posts**,
in both directions: it removed 3 false figures and, once the hosts' own
benchmark names were added to the vocabulary (`GSM8K`, `ds4-eval-92`,
`HTB-Challenger`, `BabaIsBench`), found 12 real ones that the original
vocabulary missed. The run's benchmark-figure total went 9 -> 18, and
`lucebox.com`'s head-to-head went from 0 figures to 7.

This is `docs/measurements/control-and-reshape.md`'s defect exactly - `free`
inside *freeze* - reproduced on the first run of a new extractor, which is the
argument for why a code-only matcher is a weight and not a gate.

---

## Full text

Posts carrying two or more artifact kinds, 19 of 26, in the table's order.
Text is extracted from the feed content or the post page and normalised to
plain text; tables and images do not survive. Retained here for manual reading,
never republished.

---

### [1] How I Use OpenCode, Oh-My-OpenCode-Slim, and OpenSpec to Build My Own AI Coding Environment

`dataleadsfuture.com` · 2026-04-15 · Peng Qian · **tutorial**, author's own use · about V4: passing

<https://www.dataleadsfuture.com/how-i-use-opencode-oh-my-opencode-slim-and-openspec-to-build-my-own-ai-coding-environment/>

> V4-Flash named in config only.

Model surfaces matched: `deepseek-v4`, `deepseek-v4-flash`

Artifacts (2 kinds):

- `version_string` — GLM-5; deepseek-v4-flash; glm-5
- `code_fence` — 7 <pre>/<code> block(s)

```text
This article was last updated on July 23, 2026.
 Introduction
 I have never used Claude Code. The reason is simple. Claude Code is too expensive. Even with a subscription, the cost-to-value ratio does not work for my research.
 So I have been building my own AI coding environment using OpenCode as the foundation, combined with Oh-My-OpenCode-Slim (multi-agent orchestration) and OpenSpec (SDD) .
 My take is this: if you understand what you want to build, and you know how to use coding tools properly, especially with well-written Spec files as constraints, frontier open-source models like Qwen3.6-Plus , Kimi-k2.5 , and GLM-5 can handle your daily coding tasks just fine.
 There is another huge advantage to open-source software: community power. The community can tune system prompts and model parameters to fit different models well, and get the most out of open-source models.
 In this article, I want to share what I have learned from using OpenCode and its surrounding tools. I will skip the generic tutorials you find everywhere online and focus only on the details I think actually matter. I hope this helps you make better choices.
 Tool Installation and Environment Setup
 I will cover my experience in two parts: installing and configuring OpenCode and its related plugins, and my AI coding workflow.
 Let's start with tool installation and environment setup, beginning with OpenCode itself.
 Installing OpenCode
 Unlike most coding agents that only offer a TUI-based command-line tool, OpenCode also comes with a desktop app with a graphical interface. I use the desktop app for my daily coding work. It is clearly much more efficient than the TUI version.
 That said, you still need to install the command-line program first. From my testing, some plugins need a command-line environment to check whether OpenCode is installed on your machine during project initialization.
 Why does the installation fail
 OpenCode relies on bun as its only runtime. But in a lot of workplace environments, restrictions can prevent bun from being installed automatically. In that case, you just need to install bun manually:
 npm install -g bun
 Configuring OpenCode
 After installing OpenCode Desktop, open the app. Once you select your project directory, you will land on the main OpenCode interface. The features are fairly intuitive, so I will not walk through each one. But before you type your first Hello World , you should check your terminal configuration first.
 Configuring the terminal
 I use Windows 11. On Windows, OpenCode Desktop defaults to PowerShell as its terminal. Many companies, though, do not allow PowerShell. If you are in a non-English locale, OpenCode may run into character encoding issues when running shell commands through PowerShell, causing those commands to fail.
 In that case, you need to change your default terminal.
 OpenCode uses the SHELL environment variable to determine which terminal to use. You can configure Windows Command Prompt ( cmd.exe ), WSL, or git bash . Personally, I prefer cmd.exe because I had already installed a lot of CLI tools before setting up OpenCode. Using cmd.exe directly saves me from reinstalling everything.
 SET SHELL="%windir%\system32\cmd.exe"
 Configuring model providers
 Next, let's talk about how to configure model providers.
 Open the settings window and select "Providers". You will see a list of the most popular model providers and API relays. If you want to use open-source models, though, they probably will not be on that list.
 At that point, you might click "Custom provider" and manually fill in the model id , base url , api key , and so on. The problem is that OpenCode then has no idea about your model's context window size or pricing, which causes features like automatic context compression to stop working correctly.
 The right approach is to click the "Show more providers" link at the bottom, find the provider you want to add, and enter that provider's api key .
 Click the show more providers link and pick a provider for your open-source model. Image by Author Once configured, all models from that provider will appear in the model list. These models come with metadata like context size and pricing, so context management plugins can work correctly.
 By setting up your provider correctly, you'll get all kinds of metadata about your models. Image by Author The downside is that you cannot directly see your provider ID this way, which makes it tricky to configure Oh-My-OpenCode-Slim later.
 No worries. OpenCode already saved your provider configuration when you selected your provider. You can find it at ~/.local/share/opencode/auth.json . Your provider ID and API key are both there.
 You can find your provider ID in the auth.json file. Image by Author Enable workspaces
 The biggest difference between AI coding and traditional coding is that while you wait for the AI to work, you can actually work on another requirement at the same time. If you use git for version control, you would normally need to create a separate directory and check out a new branch.
 Or you can use git's worktree feature to create a new worktree on top of your current branch. When you are doing parallel development, using worktrees is much more convenient than creating new branches.
 Compared to OpenCode CLI, the desktop app has a clear advantage here: it natively supports the worktree feature. In OpenCode Desktop, this feature is called "workspace".
 The way to open a workspace is a bit hidden. Right-click the project icon in the top-left corner of the window, then select "Enable Workspace" from the menu. From there, you can create multiple workspaces in the conversation list and work on them simultaneously. The corresponding branches and code directories will be created automatically.
 Right-click on your project to enable the workspace. Image by Author When the coding work in a workspace is done, you can ask the AI to submit a PR for the current code, then close the workspace. The branch and code directory that were created for it will be cleaned up automatically. Very convenient.
 Choosing the right agent
 If you want to use OpenCode without any extra plugins, pay attention to how you use agents.
 OpenCode has two types of agents: primary agents, which you choose yourself, and sub-agents, which the primary agent calls on its own when needed.
 Without any plugins installed, OpenCode only provides two primary agents: Build and Plan : The Build agent has full tool access and is the default choice. The Plan agent has no editing permissions. Its job is to ask you clarifying questions when you describe a requirement, and eventually produce an execution plan.
 When you first try this, you might go straight to the Build agent. But for complex tasks, Build tends to just start coding based on its own interpretation. That is like looking through a straw. It fixes things locally without thinking through the overall architecture and design patterns.
 The right approach is to start every new requirement with the Plan agent for requirement clarification, and get a solid execution plan first. Only then should you hand things off to Build to start development.
 But even that is not enough. Model context is limited. As coding progresses, the execution plan from earlier in the conversation can get pushed out of the context window.
 A better approach is to ask Build to save the execution plan as a Markdown file before starting to code. Review that file, confirm everything looks good, then start a fresh session and have Build load the execution plan document back in before executing.
 The Plan agent generates a tasks file, and the Build agent executes them. Image by Author Once you start working this way, you will feel how much value comes from planning before executing. It also sets you up well for SDD coding later, which I will cover when we get to OpenSpec.
 Always start a new session
 I just mentioned that after forming a development plan, you should create a new session before continuing with coding. Why?
 Because anyone familiar with LLMs knows that even though context windows are long today, and OpenCode does offer context compression, context rot is still a real problem. LLMs pay more attention to the beginning and end of the context window, and less to the middle. I call this positional bias.
 So to make sure the LLM follows instructions accurately based on the conversation context, especially after forming an execution plan where you need precise execution, start a new session after each major milestone. Do not keep working in the same session forever.
 Enable the Plan Agent's Planning Workflow Mode
 By default, the Plan agent runs in a pure read-only analysis mode. In this mode, it just has a back-and-forth with you about requirements and how to implement them through heuristic reasoning, but it can't edit any files.
 This creates a real problem: everything discussed in Plan mode gets scattered across the current session's chat history. Over time, the context starts to rot, and once you switch to a new session, all that discussion is just gone.
 As spec-driven development has proven its value, starting from v1.15.0, OpenCode introduced an experimental planning workflow mode for the Plan agent. This workflow follows 5 phases:
 Explore. When a new task comes in, the Plan agent spins up to 3 explore agents in parallel to analyze the codebase. (I'd recommend configuring the explore agents with the deepseek-v4-flash model here, otherwise the token costs can get pretty painful.)
 Design. Once the codebase is understood, Plan calls a general sub-agent to design the development approach.
 Review. Plan agent checks the development plan against your original task intent to make sure it actually holds up.
 Write the plan file. The final plan gets written to a .md file. This is the only file type the Plan agent is allowed to write to.
 Exit Plan mode. It calls the plan_exit tool and lets you know it's time to leave Plan mode and start writing actual code.
 Planning workflow mode sequence diagram. Image by Author Where Plan agent stores its plan files:
 When a git repo is present: <project_dir>/.opencode/plans/<timestamp>-<slug>.md
 When there's no git repo: ~/.local/share/opencode/plans/<timestamp>-<slug>.md
 To enable the planning workflow mode for the Plan agent, set the following environment variable:
 SET OPENCODE_EXPERIMENTAL_PLAN_MODE=true
 If you want a quick taste of OpenCode's native SDD development experience, just flip this environment variable on. No extra plugins needed.
 But if you're looking to use SDD for production-level AI Coding, I'd suggest checking out the OpenSpec configuration covered later in this article, paired with the Reflection SDD workflow I put together, to get truly top-tier development quality.





 Follow Data Leads Future

 One practical story every month, sharing my hard-learned experiences in the enterprise AI space.




 No spam, No ads, you can unsubscribe anytime.






 Do not forget to create AGENTS.md
 The AGENTS.md file is called "rules" in OpenCode. You can create it automatically with the /init command. It tells the LLM what rules to follow during coding.
 You may ask: if this file is created by the LLM, does that not mean the LLM already knows all these rules internally? Is saving them to a file redundant?
 Not at all. AGENTS.md is a file written specifically for the LLM to read. In my view, it serves three important purposes:
 First, AGENTS.md acts as long-term memory for the project. It locks in facts and choices. For example, after asking the LLM to set up the project structure or create a new module, run /init once. The project architecture gets locked into AGENTS.md . Without this, the LLM will scan the entire project from scratch every time you start a new session, wasting a huge number of tokens.
 Another example: if you use uv to manage your project and use uv sync --prerelease=allow to sync prerelease dependencies, write that clearly in AGENTS.md . This prevents the LLM from making errors with dependency management.
 Second, AGENTS.md narrows the probability distribution and reduces hallucinations. LLMs are probability models. When facing a question, an LLM generates several possible answers with associated probabilities, then picks one based on the temperature parameter.
 For example, when a method parameter can accept multiple types, the LLM might consider these options:
 Use Optional[int] (40% chance)
 Use int | None (40% chance)
 Use no type annotation at all (20% chance)
 At that point, the LLM will randomly pick Optional[int] or int | None .
 But once you explicitly require str | None syntax in AGENTS.md , the probability distribution shifts to:
 Use int | None (100% chance)
 Use Optional[int] (0% chance)
 At this point, the LLM will just go ahead and pick int | None as the final answer.
 Third, AGENTS.md serves a harness engineering purpose. You can give the LLM direct instructions through AGENTS.md that it must follow. For example, you can tell the LLM to communicate with you in Chinese, or require that during the spec-driven process, it cannot create new proposals without your approval.
 Improve the success rate of Skills loading
 By now, most people in the AI coding space have heard of Skills. But many find that Skills do not load reliably under normal conditions.
 There are two reasons for this. On one hand, the description in a Skill's front matter is often unclear. We need to write the front matter carefully, especially the description part. It should clearly explain when the Skill applies and what it provides, so the LLM can load the right Skill for the situation.
 On the other hand, for common coding scenarios, LLMs have learned so much during pretraining that they do not feel the need to load a Skill for extra guidance.
 For this, there is a simple and proven fix. Just add this line to AGENTS.md :
 Prioritize retrieval-led reasoning over pretrained-knowledge-led reasoning.
 That is all. After receiving this instruction, the LLM will load the relevant Skill for a given coding scenario instead of falling back on its internal pretrained knowledge. From my testing, the Skill loading success rate jumps from around 60% to 90%.
 On top of that, with this instruction in place, the LLM will use tools like glob/grep to check existing code structure before starting, and will use websearch more often to look things up online. It follows a "search first, verify after" approach instead of relying on its own instincts. Definitely worth trying.
 Installing and Configuring Oh-My-OpenCode-Slim
 Now that we have covered the key details of OpenCode itself, let's move on to Oh-My-OpenCode-Slim .
 Oh-My-OpenCode-Slim is a multi-agent orchestration plugin. It provides six types of agents, each focused on a specific coding scenario.


 Agent Scenario
 Orchestrator Coordinates other agents to complete tasks together.
 Explorer Explores the project codebase to understand what has been done.
 Oracle Fixes complex bugs or provides architecture-level advice.
 Librarian Searches GitHub repositories and framework API documentation online.
 Designer UI design and user experience.
 Fixer Handles coding work in parallel.



 You might ask: why Oh-My-OpenCode-Slim instead of Oh-My-OpenCode ? Because at this stage of AI coding, multi-agent orchestration workflows have become too heavy and less important than they used to be.
 A lightweight multi-agent plugin like Oh-My-OpenCode-Slim fits much better here. Each agent's system prompt is concise. The main value comes from the efficiency of parallel execution across agents, and the context isolation that sub-agents provide, which helps the primary agent stay focused. It does not add much to your token costs.
 Installing the plugin
 Let's start with what to watch out for when installing Oh-My-OpenCode-Slim .
 Even if you use OpenCode Desktop, you need to install OpenCode CLI first. Otherwise, the installation of Oh-My-OpenCode-Slim will fail. This is because Oh-My-OpenCode-Slim checks for the OpenCode CLI to determine whether OpenCode is installed on your machine.
 Due to a series of recent npm package poisoning incidents, OpenCode removed the feature that auto-installs plugins through opencode.json configuration. You now need to install the latest version of Oh-My-OpenCode-Slim using this command:
 bunx oh-my-opencode-slim@latest install --no-tui --tmux=yes --skills=yes
 This command installs the Oh-My-OpenCode-Slim agents and also installs two Skills: simplify and agent-browser . The former simplifies and cleans up unnecessary code. The latter helps agents inspect the frontend page styling.
 You will also notice that in the opencode.json config file, the Oh-My-OpenCode-Slim plugin points to a local entry file instead of an npm package. So for future updates, you will need to update it manually.
 Configuring the plugin
 Now let's talk about provider config. The official documentation covers this in reasonable detail, so just follow the configuration for your model.
 If you configured your model through the provider list, you cannot directly see the Provider ID. No worries. As I mentioned earlier, ~/.local/share/opencode/auth.json stores all the providers you have configured, including the provider IDs.
 {
 "preset": "kimi",
 "presets": {
 "kimi": {
 "orchestrator": {"model": "kimi-for-coding/k3-256k", "skills": ["*"], "mcps": ["*"]},
 "oracle": {"model": "kimi-for-coding/k3", "variant": "max", "skills": ["simplify"], "mcps": []},
 "librarian": {"model": "kimi-for-coding/k3-256k", "variant": "low", "skills": [], "mcps": ["websearch","context7","grep_app"]},
 "explorer": {"model": "kimi-for-coding/k3-256k", "variant": "low", "skills": [], "mcps": []},
 "designer": {"model": "kimi-for-coding/k3-256k", "variant": "high", "skills": ["agent-browser"], "mcps": []},
 "fixer": { "model": "kimi-for-coding/k3-256k", "variant": "low", "skills": [], "mcps": []}
 }
 }
}
 After configuring, remember to run opencode auth login . Even if you already filled in your API KEY through the provider list earlier, the agents will not connect properly unless you run this CLI command.
 Trying out the Council feature
 Oh-My-OpenCode-Slim introduced a Council agent in its latest version. More accurately, Council is a collection of agents. It sends the same task to several different agents that make up the Council , calculates a confidence interval from their responses, and synthesizes a final answer.
 It is a bit like ensemble learning in machine learning. "Two heads are better than one," and by using this parliamentary discussion approach, even a few different open-source models working together can match or even exceed the capability of Opus 4.6 . This makes it a great fit for solving complex architecture design problems or tracking down tricky bugs.
 Council configuration is straightforward. Just follow the official example. For best results, pick a few different agents as Council members to make the most of the ensemble learning approach:
 {
 "council": {
 "master": { "model": "alibaba-cn/glm-5" },
 "presets": {
 "default": {
 "alpha": { "model": "kimi-for-coding/k2p6" },
 "beta": { "model": "alibaba-cn/qwen3.6-plus" },
 "gamma": { "model": "alibaba-cn/MiniMax-M2.5" }
 }
 }
 }
}
 OpenCode's UI was not designed for this parliamentary-style interaction, so the Council discussion process is not very transparent. If something goes wrong in the configuration, you cannot tell from the interface. We need a way to debug Council .
 The method is simple. Since Council itself is a primary agent you can select from the agent list, just select Council , then type "test Council connectivity" in the chat. OpenCode will send a test task to each Council member and list the results from each one in detail. Very handy.
 Once you've got Council set up, you can test the connectivity of each sub-agent. Image by Author You can use this same approach to test other OpenCode features. For example, type "test context7 availability" or "test Oracle agent connectivity."
 Why isn't your LSP tool working anymore?
 In the earlier versions, the omo-slim agent used to run a tool called lsp_diagnostics after writing or editing code to check for syntax issues, making sure there were no unused imports or dead code and stuff like that.
 I really liked that tool, it was pretty handy.
 But after the latest omo-slim plugin update, you might notice the agent no longer calls lsp_diagnostics to check the code.
 That's because the old omo-slim used its own built-in LSP tool, while the new omo-slim is going to use the LSP tool provided by opencode. However, opencode has the LSP tool disabled by default, since the author thinks it uses up too much memory and doesn't really pay off in most situations.
 If you still want the agent to use lsp_diagnostics , you can manually add the "lsp": true setting in the opencode.json config file, and that'll turn it back on.
 Also, opencode offers other LSP tools like goToDefinition , findReferences , hover , workspaceSymbol , goToImplementation , and so on, which are useful for code searching and debugging. You can enable them by setting the environment variable OPENCODE_EXPERIMENTAL_LSP_TOOL = true and give them a try.
 But even with those tools enabled, the agent will still prefer using grep for text based code searches. That's because the LLM was trained on data that heavily uses grep during the pretraining phase. So from my own testing, turning on the LSP tools didn't make a big difference.
 OpenSpec and SDD
 Finally, let's look at another key piece of the AI coding puzzle: the OpenSpec plugin and the SDD coding workflow.
 Why do we need SDD? The reason is pretty simple.
 A lot of articles that benchmark model coding ability use prompts like "build a 3D web demo from this one-sentence description," then compare results and conclude that open-source LLMs still have a long way to go.
 But is that really true? Think back to how software development worked before AI coding. Before writing a single line of code, did we not always ask the business side for detailed requirements, write design documents, plan the coding schedule and testing plan, and only then start writing code?
 So why would anyone think you can skip the documentation phase when asking an AI to write code?
 Think things through with the docs first, then roll up your sleeves and get to work. Image by Author The ability to write coding specs that make an LLM work with precision is one of the golden standards for evaluating a programmer's skills in the AI era.
 No need to stress about it, though. There are plenty of AI tools today that help you do SDD development. Superpowers , BMAD , and OpenSpec are among the best.
 Compared to Superpowers or BMAD , OpenSpec is much lighter. For most everyday projects, OpenSpec is more than enough to get the job done. Let's look at how to install and configure it.
 Even though we use OpenCode and OpenSpec together, OpenSpec is not a plugin for OpenCode. It is a completely independent tool.
 Configuring the workflow
 The default OpenSpec workflow has three phases: opsx-propose , opsx-apply , and opsx-archive . These correspond to creating a proposal, implementing the proposal, and archiving the proposal.
 Just like I recommended using the Plan agent to plan things out before implementing any changes, I also want you to have a thorough discussion with the AI about your requirements before creating a proposal. Make sure both you and the AI clearly understand what you want to build.
 Since OpenSpec does not have the concept of agents, the responsibility for requirement clarification falls on a command called opsx-explorer .
 Compared to the Plan agent, the opsx-explorer command uses a Skill to strengthen the ability to guide users through their requirements in an exploratory way, helping them think things through more completely.
 opsx-explorer is also great at using charts to compare the pros and cons of different implementation options, making decisions easier for the user.
 opsx-explorer is not included in the default workflow, so you need to configure OpenSpec to add it. After installing OpenSpec , run openspec config profile in the command line, then select Workflows only in the configuration screen, as shown below:
 You just need to set up the Workflow, that's it. Image by Author Use the spacebar to select Explorer ideas and Verify change . These correspond to opsx-explorer and opsx-verify . Then press Enter to confirm.
 Just use the Space key to select the workflow nodes you like. Image by Author After configuration, go to your project root directory and run openspec init to set up a new OpenSpec environment, or run openspec update to update an existing OpenSpec configuration.
 I will walk through the full OpenSpec development workflow in the next section.
 Configuring multi-language support
 If you try creating rule files with OpenSpec , you will notice they are written in English by default. That is inconvenient for non-English users. So we need to configure OpenSpec to write files in a specific language.
 A simple approach is to add a language instruction directly in AGENTS.md , but that causes a problem. spec.md files use a lot of English keywords. If you tell OpenSpec to use another language, those keywords get translated too, and the LLM can no longer follow the spec constraints correctly.
 The right approach is to configure the language in the config.yaml file inside the OpenSpec directory:
 schema: spec-driven
context: |
 Language: Chinese
 Write in Chinese, but:
 - Keep technical terms like "API", "REST", "GraphQL" in English
 - Code examples and file paths remain in English

 Tech stack: Python 3.13

 Rules:
 proposal:
 - Keep proposals under 1500 words
 - Always include a "Non-goals" section

 tasks:
 - Break tasks into chunks of max 2 hours
 Besides language, you can also configure other settings here, such as your tech stack and specific requirements for proposal.md and tasks.md files.
 Choosing the right agent
 Since OpenSpec needs to write spec-related files, the agent must have file editing permissions. If you use the original OpenCode tools, you should go with the Build agent, since the Plan agent has no editing capability.
 In this tutorial, though, we have integrated the multi-agent orchestration from Oh-My-OpenCode-Slim . So you should use the Orchestrator agent. Beyond basic editing, the Orchestrator can call Explorer and Librarian agents during the planning phase to analyze project structure and search API documentation. During execution, Orchestrator can also call multiple Fixer agents to work in parallel, whic
 From now on, just default to the Orchestrator agent. It will call other agents when it needs to.
 Daily OpenCode Development Workflow
 Now that we have covered installation and configuration, let me walk you through my daily OpenCode workflow using OpenCode , Oh-My-OpenCode-Slim , and OpenSpec together.
 Project Initialization
 Unlike traditional coding workflows, the development process in the AI era should center on building for AI. All configuration and documentation should be written in a way that AI can understand and follow. The AI then translates human ideas into code. Let me walk you through this from project initialization.
 After creating the project, first run git init in the project root directory. If the project has a remote repository, remember to link it with git remote add . At that point, you can start using OpenCode's code review and workspace (worktree) features.
 Next, if your project is a Python project, use uv init to initialize dependencies and project structure. If needed, also add lint and code review tools with uv add --dev ruff and uv add --dev mypy .
 This gives the LLM a clear anchor for understanding the project. pyproject.toml is the standardized build protocol introduced by PEP 518 , and most build tools use this file. Without running uv init upfront to establish a basic project structure, the LLM will randomly pick pip , poetry , or something else. Fixing that later is a pain.
 Next, initialize the OpenSpec plugin. Still in the project root, run openspec init . In the command-line interface that appears, select the OpenCode agent and press Enter.
 Finally, go into the openspec directory and edit config.yaml to add your rules, as described earlier.
 Once everything is configured, run the /init command and ask OpenCode to generate the AGENTS.md file to lock in all these configuration choices.
 The Development Workflow
 With the project initialized, you can now move into the actual development flow.
 As I described earlier, you should have already configured the OpenSpec workflow using openspec config profile and selected opsx-explorer and opsx-verify .
 So the best way to start is to open a new session and begin with /opsx-explorer . No matter how clear your idea feels, use /opsx-explorer to flesh it out, fill in the details, and help the AI clear up any questions.
 I know you want to just tell the AI to build a Facebook. But I recommend starting small, one small requirement at a time.
 For example: "I want to build a budgeting app. For step one, let's start by setting up the project structure and adding dependencies." This keeps things focused. The AI completes a small amount of work at a time, which avoids context limitations, causing the AI to go off track after a long run.
 Once the requirement discussion is mostly done, run /opsx-propose to create a proposal. This locks down the discussion and development plan as spec documents. OpenSpec will break things down into one or more changes based on complexity, then generate proposal.md , design.md , and tasks.md .
 Review these three files carefully. The LLM-generated tasks might have gaps or misunderstandings. If you find errors, you have two options:
 Talk to the LLM, add details, and ask OpenSpec to regenerate the documents.
 Or edit the rule files directly, then ask OpenSpec to regenerate the documents.
 Once the documents look good, I strongly recommend starting a new session with a fresh context. Then run /opsx-apply to enter the implementation phase.
 The agent will load the spec documents from the previous session and start coding. With Oh-My-OpenCode-Slim 's multi-agent system and various Skills helping out, this process mostly runs on autopilot. Go grab a coffee or read another one of my articles while you wait.
 After coding is done, OpenSpec will prompt you to run /opsx-archive to archive the proposal. But before archiving, I recommend switching to a different model. For example, if you were using kimi k2.5 , switch to GLM-5 , then run /opsx-verify to verify that all tasks were completed. You can also run /review or /simplify to review and clean up the code and make sure the project quality is solid.
 A typical SSD development cycle. Image by Author Finally, run /opsx-archive to archive the changes. One standard AI development cycle is now complete. When the next new requirement arrives, start fresh with a new session and /opsx-explorer .
 Conclusion
 In this tutorial, I covered how to use OpenCode, Oh-My-OpenCode-Slim, and OpenSpec to build your own AI coding workflow.
 With this open-source combination, paired with the latest open-source models, you can get coding performance that rivals top-tier models, at a much better price.
 This tutorial draws from my real-world experience. It focuses on the practical details of AI coding with OpenCode and walks through each step of the SDD-based development cycle. By the end of this tutorial, you should have a solid edge in the AI coding space.
 Due to space and my own limitations, I could not cover every detail. I am still working on improving this article. If anything is unclear as you read through it, leave me a comment, and I will get back to you as soon as I can.
 Thanks for subscribing. Feel free to share this article with your friends. You never know who it might help.





 Follow Data Leads Future

 One practical story every month, sharing my hard-learned experiences in the enterprise AI space.




 No spam, No ads, you can unsubscribe anytime.






 Further reading
 Reflection SDD: Use a Reflection Harness to Level Up Your OpenSpec Workflow
 Stop letting bad spec files tank your code quality

 DeepSeek-V4 Can’t Read Images? I Made It Read
 Don’t wait for a multimodal model, you can use it now

 No Plugins Needed, I Built a Fully Automated Coding Loop in OpenCode
 Using DeepSeek-V4 for low-cost Loop Engineering

 How I Cut Kimi K3 Costs in OpenCode
 Better code quality, but spend less money

 From OpenSpec to AIDLC: How I Improved My Team’s AI Code Quality
 No new commands to learn, just pick it up and use it
```

---

### [2] Reflection SDD: Use a Reflection Harness to Level Up Your OpenSpec Workflow

`dataleadsfuture.com` · 2026-05-29 · Peng Qian · **tutorial**, author's own use · about V4: yes

<https://www.dataleadsfuture.com/reflection-sdd-use-a-reflection-harness-to-level-up-your-openspec-workflow/>

> Carries a real capability claim - a reflection harness gets V4-Pro to 'roughly the same level as Claude Opus 4.6' - with NO measurement attached.

Model surfaces matched: `deepseek-v4`, `deepseek-v4-pro`

Artifacts (2 kinds):

- `version_string` — Claude Opus; Claude Opus 4.6; DeepSeek-V4-pro; GPT 5.5; deepseek-v4-pro
- `code_fence` — 4 <pre>/<code> block(s)

````text
Introduction
 In this article, I want to walk you through how I introduced a reflection mechanism into the OpenSpec workflow inside OpenCode, and how that dramatically improved the quality of AI-generated code.
 After nearly a month of testing, this reflection workflow has gotten DeepSeek-V4-pro in OpenCode to perform at roughly the same level as Claude Opus 4.6. The only cost is some extra review time and a few more tokens. Trust me, it's worth it.
 Can't wait to find out how? Let's get into it.
 Why This Works

 I've been using AI coding for a while now. Compared to Claude Code, I prefer building my own SDD-based coding workflow with OpenCode and OpenSpec. I wrote a well-received article specifically about this OpenCode workflow:
 How I Use OpenCode, Oh-My-OpenCode-Slim, and OpenSpec to Build My Own AI Coding Environment
 Ride the wave of AI coding, don’t get swept away by it

 With OpenSpec, and the explore → propose → apply → verify → archive workflow loop, we can finally get LLMs to handle complex project development.
 With the OpenSpec workflow loop, LLMs can finally write usable code. Image by Author But just like you've probably run into, even with the SDD workflow, no matter which model I use, GPT 5.5 or the latest DeepSeek-V4-pro, the AI still inevitably produces hidden bugs or piles up messy code. Code I'd never feel comfortable putting in production.
 My first fix was to call a @reviewer sub-agent after the /opsx-apply phase to do a code review on the changes. Sometimes that worked and caught architectural or implementation issues. But the impact was limited.
 Often I'd only discover something was wrong after using the project for a while: a scenario wasn't covered, edge cases were missed, or one part of the code got updated but a related module didn't.
 Later I stepped back and looked at the whole AI coding workflow again, and that's when I spotted the real problem.
 As programmers, we always focus on whether our code is good, so we naturally look at things from the code level.
 But we completely overlooked the quality of the proposal files that OpenSpec generates. We'd finish discussing requirements, generate the proposal file, and then just let the AI start implementing. That's how input-level bugs get introduced. When things go wrong, we blame the model.
 Think about it, back in the traditional coding era, when a product manager handed over a requirements doc, there was a critical step before we started coding: requirements review. We wouldn't touch the keyboard until every issue in the requirements doc or design doc was sorted out.
 So why did we forget this step in the AI coding era? That's exactly what we're going to fix today: add the requirements review step back into the OpenSpec workflow and see if it makes AI-generated code better.
 How to Do It
 The SDD workflow isn't anything exotic. If you're familiar with multi-agent system design patterns, you'll recognize that SDD is basically the plan-execute pattern.
 One agent breaks the user's task into a step-by-step plan file, then another agent follows that plan to execute the task. This lets the agent system handle complex work.
 The Plan agent makes the plan, the Executor agent gets it done. Image by Author But how do you guarantee the quality of what the agents produce in a plan-execute setup? That's where a pattern called reflection comes in.
 The reflection pattern adds a reflection agent to the multi-agent workflow. This agent typically runs on a completely different LLM and reviews the output of the plan or executor agent from a different angle, which raises the overall performance of the multi-agent system.
 The reflection pattern sees wide use in content creation and deep research scenarios, which proves it works.
 Just adding a reflection step can dramatically improve task quality. Image by Author Since the pattern is proven, we can bring the same reflection step into the OpenSpec workflow, targeting the proposal files.
 I'll introduce a reflection agent that runs on a different LLM from the primary agent, reviewing the proposal files from a different angle. We'll also adjust the OpenSpec workflow so this reflection agent plays an active role in it.
 Introducing the reflection agent
 Adding a new agent in OpenCode is simple. Just drop a new Markdown file into ~/.config/opencode/agents/ with the agent's prompt inside.
 The core job of this agent is straightforward: review the artifact files that OpenSpec generates from multiple angles, making sure the quality of the requirements input is solid from the start. This agent sits between the /opsx-propose and /opsx-apply phases.
 Only proposals that pass review can move on to the apply phase. Image by Author We can have deepseek-v4-pro generate the first draft of this agent's prompt:
 You are an **OpenSpec Change Reviewer** — a critical thinker and auditor focused on substance.

Your job is to review every artifact in an OpenSpec change before it moves to implementation, and find the issues that would actually cause implementation failure or rework.

## Core Principle: Distinguish Substantive Defects from Formatting Issues

**Substantive defects = issues that cause the implementation to go in the wrong direction, miss critical scenarios, create contradictions, or make acceptance impossible.**
**Formatting issues = style or wording differences that don't affect implementation quality.**

Your primary job is to find the former. You can mention the latter, but mark them as optional suggestions and put them at the end.

## Your Position

You work in the **phase between `/opsx-propose` and `/opsx-apply`**:

```
explore → /opsx-propose → ⬅ you are here (possibly multiple rounds) → /opsx-apply → verify → archive
```

The spec is not yet frozen. Implementation has not started. Your mission: **find the defects that would actually cause rework or incidents before any code gets written**. Catching a spec error takes minutes. Fixing wrong code takes hours.

## Principles

- **Constructive and strict.** For every issue, explain not just "what" but "why it would cause rework or an incident."
- **Specific, not vague.** Point to exact file locations, requirement names, and task numbers.
- **Severity levels.** 🔴 Blocking vs 🟡 Should Fix vs 💡 Suggestion — don't mix them up.
- **Context-aware.** Evaluate against the existing system (`openspec/specs/`) rather than in a vacuum.
- **Read-only.** Never modify files. You surface problems; OpenSpec executes the fixes.

## Anti-Patterns to Avoid

- Rubber-stamping: saying "looks good!" without deep review.
- Nitpicking: focusing on formatting while missing architectural flaws.
- Jumping to solutions: proposing fixes before the user acknowledges the problem exists.
- Ignoring existing specs: reviewing incremental changes without understanding the baseline.
- Vague feedback: "this could be better" — say exactly what and why.
 This is just a partial excerpt of the prompt. The full version is in the source files at the end of the article.
 To review proposals from a different angle and improve the reflection quality, I recommend using a different LLM for the reflection agent than the one the main agent uses. For example, my primary coding agent uses deepseek-v4-pro, so the reflection agent uses kimi k2.6.
 ---
description: OpenSpec Change Reviewer — after propose and before apply, critically reviews all artifact files under the change (proposal/design/specs/tasks)
mode: subagent
model: kimi-for-coding/k2p6
tools:
 write: false
 edit: false
 bash: false
---
 Locking down the openSpec workflow
 OpenSpec doesn't actually have a fixed workflow design, users follow a default SDD best practice. So the first step is to lock this workflow down, making OpenCode write an OpenSpec proposal before writing any code.
 ---
name: openspec-workflow
description: Mandatory prerequisite for ALL OpenSpec operations — load this BEFORE any openspec-* skill. Use when running /opsx-apply, /opsx-propose, /opsx-verify, /opsx-archive, /opsx-explore, /opsx-sync; running `openspec status`, `openspec list`, `openspec instructions`; reading files under `openspec/changes/`; or doing any OpenSpec stage (propose, apply, verify, archive, explore, sync).
license: MIT
compatibility: Requires openspec CLI.
metadata:
 author: Peng Qian
 version: "1.0"
---

## OpenSpec Workflow (Mandatory)

**All code changes must have a proposal before any code gets written.**

### Process
1. **Explore** - When the user says "think about it," "discuss," or "explore," discuss only — no coding.
2. **Propose** - Create proposal files under `openspec/changes/<change-name>/`.
3. **Apply** - Implement according to the proposal tasks. **No file modifications without a proposal.**
4. **Verify** - Verify after implementation is complete.
5. **Archive** - Archive the change.

### Hard Rules

- **Bug fixes don't require editing or creating a proposal.** This hard rule only applies to feature changes or new features.
- **No proposal, no change:** If the user asks to modify code, confirm that a matching proposal exists first, or create one.
- **No proposal, no edits:** Before editing a file, check that a matching change directory exists under `openspec/changes/`.
- **No coding in Explore mode:** When the user is in explore mode, **do not** create proposals, **do not** edit files, **do not** write tests.
- **After a change is complete:** Run the verify process to check that the implementation matches the proposal.

### Proposal Creation Requirements

Every change must include:
- `proposal.md` - reason and scope of the change
- `design.md` - design plan
- `tasks.md` - specific task list
- `.openspec.yaml` - change metadata

Additional requirements:
- **Task granularity:** Each task in `tasks.md` should take no more than 2 hours.

### Violation Handling

Stop immediately and alert the user if any of the following are detected:
- Code modification starts without a proposal.
- Files are edited in explore mode.
- Files outside the current proposal's scope are modified.
 You can put this workflow into your project's AGENTS.md file so OpenCode follows it consistently. Or put it in the global ~/.config/opencode/AGENTS.md file so you don't have to configure it for every project.
 A better option is to turn the workflow into a skill, so OpenCode only loads this workflow definition when using OpenSpec. I've packaged the full workflow as the openspec-workflow skill, you can grab the source file at the end of the article.
 Inserting the reflection agent into the workflow
 Once the OpenSpec workflow is locked down as a skill, every SDD coding session will follow the spec-first, code-second process, which means the /opsx-propose and /opsx-apply phases.
 As mentioned earlier, the reflection agent sits between these two phases, reviewing the quality of the proposal files before any implementation starts. Following the reflection pattern, this review-and-fix cycle can run for multiple rounds until the proposal artifacts have no serious issues.
 To prevent an infinite loop, we need a hard cap on the number of review rounds. Let's update the openspec-workflow SKILL.md file to add the reflection process:
 ### OpenSpec Reflection Process

1. **After each batch of artifacts is created**, the `@openspec-reviewer` agent **must** be called to review the **artifact files in that batch**.
2. The main agent fixes the **current batch of artifact files** based on the feedback from `@openspec-reviewer`.
3. Call `@openspec-reviewer` again to review the **current batch of artifact files**.
4. **Review pass criteria:**
 4a. **Single-round pass:** After the current review round, if "### 🔴 Remaining Issues" does not exist or is empty, move to the next batch.
 4b. **Fix loop:** If 🔴 issues remain → main agent fixes → next review round → back to 4a. Repeat until passing or 4c triggers.
 4c. **Hard cap (MAX_ROUNDS = 5):** If the same batch has gone through 5 review rounds without passing 4a → stop the loop and hand off to a human for a decision.
 At this point, a typical reflection process for OpenSpec proposals is in place. All you need to do is run /opsx-propose , go grab a coffee, and wait for the reflection agent to gradually refine your proposal.
 After the OpenSpec proposal is created, the openspec-reviewer agent will be automatically invoked to begin reviewing and fixing it. Image by Author Optimizing the Reflection Process
 After going through a few rounds of "review and fix," you'll notice this reflection process doesn't work as perfectly as you'd expect.
 It's common to fix issue A only to have issue B pop up. Sometimes all 5 review rounds finish, and not every issue is fully resolved. Especially with powerful but not top-tier models like deepseek-v4. It's fine. We can optimize the process to fix this.
 Saving the explore discussion to disk
 OpenSpec has a gap: the /opsx-explore phase involves very detailed requirements discussions, but none of that gets saved to a file. Once the user starts a new session or the session hits its context limit, all those discussion details are gone.
 The review and fix process runs for many rounds and generates a huge amount of context tokens, which almost guarantees the explore discussion details get lost.
 On top of that, OpenCode calls the reflection agent in a separate sub-session to review the proposal artifacts. OpenCode doesn't pass along the background context in detail during that call, so the explore discussion never makes it into the reflection agent's context.
 So we need to update the openspec-workflow skill file to require OpenSpec to generate an explore-brief.md document after /opsx-explore finishes. This document serves as a persistent checklist baseline for the proposal review process.
 A file-based checklist gives proposals and reviews a solid foundation. Image by Author We also need to update the reflection agent's prompt to reference this explore-brief.md file during the review.
 Sometimes the requirements are simple and /opsx-explore wasn't used, so the primary agent won't generate an explore-brief.md . In that case, the reflection agent falls back to the context background passed along when the sub-agent is called.
 Review artifacts one at a time, not all at once
 In the early stages, I found the biggest reason proposals kept going through so many review rounds was file consistency issues.
 At first, all proposal artifacts were written at once before any review started. The agent had to review four files in one shot: proposal.md , design.md , spec.md , and tasks.md . That meant one review round could surface 8 issues spread across 4 files.
 Fix file A, and file B becomes inconsistent. Fix file B, and file C needs updating. The next review round then has to check all 4 files again, and the consistency verification cost explodes as N files × N files combinations.
 This gets especially bad with open-source models like deepseek-v4 or kimi. Fixing A and forgetting B happens all the time. That's the root of the problem.
 The best fix is to review artifact files in batches.
 OpenSpec writes proposal.md , then immediately enters the review phase. Once it passes, proposal.md is frozen and can't be changed. Then OpenSpec generates design.md and enters review. Once that passes, design.md is frozen, then spec.md is generated and reviewed, and so on.
 This way, each subsequent artifact's review naturally includes a consistency check against the already-frozen earlier artifacts. Why does this guarantee consistency? Let me draw a diagram:
 Each new batch of artifacts uses the previous frozen batch as its reference. Image by Author The consistency guarantee comes from two mechanisms:
 The freeze mechanism. Artifacts that pass review can't be freely modified anymore. This eliminates the back-and-forth of fixing A, then fixing B, then having to fix A again. It cuts down on a lot of repeated review rounds.
 One-way dependency. proposal → design → specs → tasks is a strict DAG. When reviewing design, you only need to check its consistency with the proposal, not with specs (since specs haven't been written yet). Each review round only compares one pair (new artifact vs. frozen artifact), not N × N.
 Generating and reviewing artifacts in batches may not reduce the total number of rounds compared to generating everything at once, but each round only touches 1 or 2 files. Fixes don't accidentally break other files, and you don't have to worry about the LLM fixing A and forgetting B.
 The final review process looks like this:
 The final proposal review flow. Image by Author Log every review round
 Same problem again: OpenCode calls the reflection agent in a sub-session to review proposals. Not only does the sub-session lose its input context (already solved with explore-brief.md ), it also loses the history of previous review conclusions.
 The primary agent starts fixing the current round right after getting the reflection agent's feedback, without saving those results to the session context. As the review and fix context grows, the LLM's attention inevitably drifts.
 The best fix is to have the primary agent log each review's issues and fix results.
 That way, in later review rounds, the LLM can get a full picture of what happened historically, what decisions were made, and how they affect the current round. And if the review hits the max rounds and needs human intervention, we have a much better reference to work from.
 The implementation is simple: after each round of fixes, append the current round's review results to a review-log.md file.
 The main agent should log the results of every proposal review round. Image by Author Conclusion
 Let's recap everything we did to improve OpenSpec proposal artifact quality through the reflection mechanism:
 We set up a reflection agent. Its job is to fully review the proposal artifacts that OpenSpec produces before the /opsx-apply phase starts, making sure everything is solid before moving forward.
 We locked down the OpenSpec workflow as an openspec-workflow skill. This skill requires OpenCode to strictly follow the spec-first, code-second process. After the proposal is generated, the reflection agent is called to review it.
 We patched a gap in OpenSpec by requiring it to record each /opsx-explore requirements discussion in an explore-brief.md file. This prevents the LLM's context window from losing important details during long review processes. Each review and fix result is also recorded incrementally in a review-log.md file, for the same reason.
 We changed how OpenSpec generates artifact files: from generating all files at once to generating one file, reviewing it, and freezing it before moving to the next. This eliminates the root cause of fixing A, breaking B, fixing B, then having to fix A again.
 With these reflection harness optimizations in place, even using deepseek-v4-pro, code bugs are rare now. The model covers all kinds of edge cases thoroughly, code reviews almost always pass on the first try, and messy code is much less common.
 That said, adding this reflection harness does make the OpenSpec proposal generation process much longer. It takes more waiting time and extra tokens. But getting DeepSeek-v4 to match or even beat Claude Opus in code generation quality makes it worth it overall.
 Beyond the reflection mechanism, there's still a lot of room to improve the OpenSpec coding workflow.
 I'm designing a self-evolving plugin system that lets agents learn from each review and fix cycle, so OpenCode can avoid making the same mistakes in future proposal generation. I look forward to walking you through that in the next article.
 Thanks for reading and subscribing. If anything in the article wasn't clear, leave a comment and I'll get back to you.
 Feel free to share this article with your friends, it might help someone out.





 Follow Data Leads Future

 One practical story every month, sharing my hard-learned experiences in the enterprise AI space.




 No spam, No ads, you can unsubscribe anytime.






 Further reading
 How I Use OpenCode, Oh-My-OpenCode-Slim, and OpenSpec to Build My Own AI Coding Environment
 Ride the wave of AI coding, don’t get swept away by it

 DeepSeek-V4 Can’t Read Images? I Made It Read
 Don’t wait for a multimodal model, you can use it now

 How I Cut Kimi K3 Costs in OpenCode
 Better code quality, but spend less money

 From OpenSpec to AIDLC: How I Improved My Team’s AI Code Quality
 No new commands to learn, just pick it up and use it

 Source Code









 Here's the source code for this article. Sign up now to get it for free.






 Grab the Source Code
````

---

### [3] DeepSeek-V4 Can't Read Images? I Made It Read

`dataleadsfuture.com` · 2026-06-15 · Peng Qian · **tutorial**, author's own use · about V4: yes

<https://www.dataleadsfuture.com/deepseek-v4-cant-read-images-i-made-it-read/>

> First-hand report of a capability GAP: V4 had no multimodal variant as of mid-June, worked around via a sub-agent.

Model surfaces matched: `deepseek v4 flash`, `deepseek-v4`, `deepseek-v4-flash`, `deepseek-v4-pro`

Artifacts (2 kinds):

- `version_string` — GLM-5.2; deepseek v4 flash; deepseek-v4-flash; deepseek-v4-pro
- `code_fence` — 6 <pre>/<code> block(s)

```text
Introduction
 I gotta say, DeepSeek-V4 is cheap, works great, and has a long context window. It's already my go-to coding model. The new GLM-5.2 model is also pretty impressive.
 But as of mid-June, the multimodal versions of these models still haven't been released. That means anything involving images like reading error screenshots, interpreting charts, or recreating pages from visual mockups is totally out of their reach.
 However, I found a workaround: I built a little plugin called observer in OpenCode. By letting DeepSeek-V4 call a multimodal agent, it can indirectly get the ability to "see" images.
 After polishing it for over a month, this plugin now handles all my image-related coding tasks at work. Today, I'm sharing how I made it, hoping it might help you too.
 The plugin code and agent definitions mentioned in this article are at the end. Feel free to grab them.
 Demo of Real-World Results
 Before diving into the long tutorial, you probably care most about how well this plugin works and whether it is worth your time to try. So let me show you some screenshots of the plugin in action.
 1. Interpreting error stack traces
 We start with the simplest task: have deepseek-v4 interpret a screenshot of an error stack trace and find key information. I randomly picked a screenshot of an error I encountered at work:
 A screenshot of a common error stack. Image by Author Then in OpenCode Desktop, I sent this image to the plan agent using deepseek-v4-pro and asked it to provide a solution:
 The deepseek-v4-pro agent quickly picked up the error message. Image by Author As you can see, the plan agent gave an answer based on the screenshot information.
 2. Interpreting charts
 Another multimodal use case is interpreting charts from documents. For this example, I took a screenshot of a company's annual revenue chart and tested it. I still used the plan agent with deepseek-v4-pro . For an extra challenge, I asked the agent to give some key insights on the numbers in the chart:
 A screenshot of a listed company's financial report. Image by AlphaStreet The agent read the numbers from the chart and provided some key insights:
 The agent accurately spotted the data in the chart and offered key insights. Image by Author 3. Developing HTML pages from designs
 In frontend development, the biggest demand for multimodal capability is recreating visual designs. Here I found a design with complex page elements to see if the build agent using deepseek-v4-flash could recreate the page:
 A screenshot of a web design draft. Image by dribbble.com Here is the recreated page:
 The page that deepseek v4 flash recreated. Image by Author One thing is sure: the deepseek-v4-flash model generated the frontend code, and it only took one prompt to get this result. It did not get a 100% match, but with a few more rounds of conversation, you can tweak it until it is perfect. Keep in mind deepseek-v4-flash is dirt cheap.
 It costs several times or even ten times less than multimodal models like kimi k2.6 or qwen3.7 plus . They are not in the same league.
 Of course, you can also crop a section of the page, mark the areas that need attention, and ask DeepSeek to adjust them, like this:
 You can take a screenshot of the webpage and have deepseek-v4-flash make adjustments. Image by Author The agent perceives the marked area and gives the primary agent an adjustment plan per your request.
 4. Generating HTML pages from hand-drawn sketches
 Maybe you are like me and have zero design skills. No problem. We can hand-draw rough sketches. The agent can understand them. For example, in a recent project, I hand-drew a few web page design sketches:
 This is a hand-drawn sketch of the webpage. Image by Author Then deepseek-v4-flash helped me recreate the page:
 The agent restored the page based on my handwritten reference. Image by Author Impressive, right?
 Detailed Implementation Walkthrough
 I know you cannot wait any longer. Let me jump straight into the implementation details.
 The whole image-reading plugin consists of two parts:
 A sub-agent configured with a multimodal LLM. It runs in a separate sub-session, reads the images uploaded by the user, parses them into detailed text descriptions based on the scenario, and returns the results to the DeepSeek model in the main session.
 An OpenCode plugin that intercepts images uploaded by the user, saves them as files, and triggers the sub-agent to read the images at the right time.
 In other words, the plugin is the "dispatcher," and the sub-agent is the "image reader." They work together through independent sub-sessions without messing up the main session's context.
 Let me start with the design of the agent.
 Designing the image-reading agent
 Since the source code is at the end of this article, I won't paste it here. I will only cover the design thinking behind the agent.
 This agent does the actual image reading, so make sure it uses a multimodal LLM. Here I used the kimi-for-coding/k2p6 model. The setup is simple. Just put the configuration in the frontmatter of the agent's Markdown file (that's the YAML block wrapped in three dashes at the very top of the file).
 Of course, it won't match a native multimodal agent. This approach, where another multimodal agent converts an image to a text description and then passes it back to DeepSeek, inevitably loses a lot of information.
 To capture as many image details as possible, I broke the reading process into different scenarios. Each scenario corresponds to a different working mode, with its own trigger keywords and output format:
 Mode A: Page Restoration. Keywords like: restore, HTML, page, design mockup, etc. Main task: describe the image at the pixel level with precision to help the main agent write an identical HTML page:
 ### Mode A: Page Restoration

**Signal words**: Reproduce, HTML, page, design mockup, screenshot reproduction, refactor, frontend, CSS, layout, slice images, implement, pixel-perfect, 1:1, precise reproduction, replicate, mobile, app screenshot, component, visual design, Figma, XD

**Task**: Describe the webpage/app interface screenshot with pixel-level precision, helping the main agent write an identical HTML/CSS page.

**Simplified mode**: If the signal words contain one of `rough`, `approximate`, `briefly describe`, `quick and simple`, only output A1 (page overview) + A5 (page text list), skip the rest of the sections.
 To describe the page layout well, I also told the agent to output the page structure using ASCII art. My experiments show this ASCII approach is effective.
 Mode B: Issue Location and Fix. When my screenshot has areas marked with red boxes, arrows, etc., and I ask the agent to pay special attention, this mode kicks in.
 ### Mode B: Issue Location and Fix

**Signal words**: issue, fix, adjust, wrong, error, bug, tweak, something off, not normal, mark, red box, arrow, circle, look here, this area, this part, skewed, misaligned, spacing, not aligned, wrong color, wrong font, overflow, overlap

**Task**: Identify the problem areas marked or pointed out in the screenshot, analyze the symptoms and possible causes, and give specific fix suggestions.
 Mode C: Error Log Extraction. I use this mode a lot in daily work. For example, when a remote computer blocks the clipboard, we can take a screenshot and let the agent analyze the error stack trace in the image.
 ### Mode C: Error Log Extraction

**Signal words**: error, log, error, stack, stack trace, exception, exception, crash, traceback, warning, warning, fail, crash, 500, 404, timeout, panic, fail

**Task**: Extract the error/log text from the screenshot precisely, word for word, keeping all technical details so the main agent can locate and fix the code.
 Mode D: Text/Conversation Extraction and Analysis. This is the basic OCR function. Just recognize the conversation roles, text hierarchy, and content relationships.
 ### Mode D: Text/Conversation Extraction and Analysis (Default)

**Signal words**: extract text, OCR, recognize text, read text, conversation, copywriting, clarify, content relationships, what was said, transcribe, organize

**Task**: Extract all text from the image, clarify conversation roles, text hierarchy, content relationships, and logical structure.
 Mode E: Chart Interpretation. This mode extracts data metrics from charts, as I demonstrated earlier.
 ### Mode E: Chart/Data Visualization Extraction

**Signal words**: charts, line charts, bar charts, pie charts, scatter plots, radar charts, heatmaps, area charts, trends, data visualization

**Task**: Extract data points, axis labels, and trend info from chart screenshots for the main agent to analyze data relationships.
 I did not decide on these five modes all at once. I added them one by one as I needed them in real scenarios.
 This brings up a problem: several modes share overlapping signal words, but each mode has a different output format. If there is a conflict, which mode should the agent use to read the image?
 Here I used a priority method. I defined five priority levels as follows:
 C (Error Log Extraction) > E (Chart Data Extraction) > B (Issue Location and Fix) > A (Page Restoration) > D (Text/Conversation Extraction and Analysis)
 If I add new modes later, I will adjust the priorities.
 Finally, I set Mode D as the default. When none of the previous modes match the user's request, it will use OCR mode to handle the image reading task.
 Once the image-reading agent is designed, just drop the Markdown file into the ~/.config/opencode/agents/ directory and it will take effect.
 Designing the OpenCode plugin
 Compared to the agent, the plugin design is much simpler. It is just a single JS file with a little over 100 lines, and it handles two main jobs:
 Use the experimental.chat.system.transform hook. Every time a request is sent to the model, it checks if the model has multimodal capability. If not, it adds this prompt to the system prompt:
 ## Image Reading

- You should use the @observer sub-agent to read images.
- When a message like [Image saved to: <path>] appears in the conversation, call the @observer sub-agent and tell it to read the image file at that path.
 Use the chat.message hook. When the user pastes an image into the input box and sends a message, the image exists as base64-encoded text in the message body. The plugin intercepts this data, decodes it, and saves it as an image file in a temp directory. Then it replaces the original image content in the message with text like [Image saved to: <path>] .
 The plugin's entire workflow looks like this:
 The workflow of plugin. Image by Author You need to place the plugin in the ~/.config/opencode/plugin/ directory for it to work.
 That covers the implementation principles of the OpenCode plugin and the agent that add image-reading capability to deepseek-v4 .
 Why Did I Design This Plugin?
 After reading this whole practice, you might have a question: why don't I just start a new conversation and use a multimodal model to read images directly? Why go through all this trouble? What is the benefit?
 I plan to answer your question from the following angles:
 Cost. We use deepseek-v4 's two models for their huge cost-effectiveness. Switching to a multimodal model directly would defeat the purpose of using them.
 Keep the conversation context. For example, interpreting an error stack trace or extracting text from a conversation screenshot. These actions happen during a coding task. The existing conversation context is crucial for finding a fix based on the error. If you start a new conversation to read the image, you lose that context.
 Different models support different context lengths. The deepseek-v4 model supports a 1M context length, while models like kimi k2.6 only support 256k. If you temporarily switch to k2.6 in the middle of a conversation to read an image, it might immediately trigger OpenCode's context compression, causing key info loss. So the best solution is to use a sub-agent that reads the image in a separate su
 Conclusion
 We still wait, excited for DeepSeek to release a multimodal model. Once native multimodal capability arrives, we can pack up all this fussing with plugins and sub-agents.
 But until then, the observer plugin is a workable solution. And the process itself has value: once you understand OpenCode's plugin and agent orchestration, you can apply the same thinking to patch capability gaps in other models.
 This mechanism is not limited to OpenCode. It works on other coding agent platforms too, just adjust the implementation a bit.
 The plugin code and agent definitions mentioned in this article are all at the end. Grab them there.
 If you think this article helps you, feel free to share it with your friends.





 Follow Data Leads Future

 One practical story every month, sharing my hard-learned experiences in the enterprise AI space.




 No spam, No ads, you can unsubscribe anytime.






 Further Reading
 Give my programming workflow built with OpenCode, OMO-Slim, and OpenSpec a try?
 How I Use OpenCode, Oh-My-OpenCode-Slim, and OpenSpec to Build My Own AI Coding Environment
 Ride the wave of AI coding, don’t get swept away by it

 In the previous article, I added a reflection mechanism to the OpenSpec workflow, making deepseek-v4-pro match or even exceed the coding performance of the opus model. Click here to learn more:
 Reflection SDD: Use a Reflection Harness to Level Up Your OpenSpec Workflow
 Stop letting bad spec files tank your code quality

 Better code quality, but spend less money.
 How I Cut Kimi K3 Costs in OpenCode
 Better code quality, but spend less money

 Source Code









 Here's the source code for this article. Sign up now to get it for free.






 Grab the Source Code
```

---

### [4] No Plugins Needed, I Built a Fully Automated Coding Loop in OpenCode

`dataleadsfuture.com` · 2026-07-15 · Peng Qian · **tutorial**, author's own use · about V4: passing

<https://www.dataleadsfuture.com/no-plugins-needed-i-built-a-fully-automated-coding-loop-in-opencode/>

> V4-Pro/Flash used for every example; claim is about the loop, not the model.

Model surfaces matched: `deepseek-v4`, `deepseek-v4-flash`, `deepseek-v4-pro`

Artifacts (2 kinds):

- `version_string` — Claude Opus; DeepSeek-V4-Flash; DeepSeek-V4-Pro; GPT 5.5; deepseek-v4-flash; deepseek-v4-pro
- `code_fence` — 5 <pre>/<code> block(s)

```text
This article was last updated on July 27, 2026.
 Today I want to talk about how I built an agentic coding loop inside OpenCode. People call this Loop Engineering.
 To show you how well this coding loop holds up, I used DeepSeek-V4-Pro and DeepSeek-V4-Flash for every example in this article. It turns out that with the right design, DeepSeek models can pull off high-quality coding loops at a very low cost.
 All the source code in this article is available at the end of the post. Let's get into it.
 Introduction
 If you've been following the AI agent space recently, you've probably heard the term Loop Engineering. Claude Code and OpenClaw both mention it.
 But nobody really explains what it means.
 Until Andrew Ng posted a clear breakdown of what Loop Engineering actually is. That post gave me the direction I needed to build it inside OpenCode.
 What Andrew Ng Says About the Coding Loop
 Andrew Ng's explanation centers around this diagram:
 3 key product development loops. Image by Andrew Ng Three loops, simply put:
 The first loop is the code agent's implementation loop. You give the agent a product spec and a measurable target. The agent starts building features on its own, runs tests, and keeps iterating until every requirement in the spec is met.
 The second loop is the engineer feedback loop. Here the engineer acts as QA for their own product. They test what the coding agent built, and check if it matches their vision. If something is off, they write a new spec and kick off another round in the first loop.
 The third loop is the external feedback loop. Once the engineer is happy with the product, it goes to the open-source community or gets handed to a product team. Real user feedback comes in. The engineer collects that feedback regularly, feeds it back into the engineer feedback loop, and from there back into the code implementation loop.
 All three loops keep running. With AI in the mix, they push the product forward until it gets to where it needs to be.
 My Take on the Coding Loop
 The way I see it, these three loops map to two commands in Claude or Codex: /goal and /loop .
 /goal covers the first and second loops. Once a user writes a product requirements doc or a spec, they pass the task to the agent through the /goal command. The agent iterates on its own, runs its own tests, and opens a Pull Request.
 Then the engineer reviews the code and tests it manually. If everything looks good, they merge the PR and ship.
 Next comes the external feedback loop. You can use the /loop command to set up scheduled tasks that pull issues from GitHub or Jira on a timer. The agent turns those issues into requirement docs, and /goal takes it from there.
 Use /goal to create a new task, and use /loop to schedule it to run on a timer. Image by Author There is a gap in the traditional understanding here. When a user calls /goal , they just pass in what they want done. How it gets done, and what the exit condition is, often gets left up to a strong reasoning model like Claude Opus or GPT 5.5 to figure out.
 But in a proper coding loop, you need to give the agent a product spec and a measurable completion target so it knows when to exit. Something like this:
 /goal Use the spec I wrote to build this chess game.
Use Playwright MCP for end-to-end testing.
Verify the game supports castling, pawn promotion, checkmate, stalemate, and rating calculation.
Fix any bugs found during testing and re-run. Loop no more than 20 times.
 That is a solid starting instruction for a coding loop. It needs a goal, a verification method, and a max iteration count. And you have to write something like that every single time, either right after the /goal command or inside the spec itself.
 In my OpenCode version, I am not going that route. I just want to tell /goal what I want. The agent handles everything else.
 The rest of this article shows you how I built that enhanced /goal loop. (The /loop command is a separate topic I will cover in a future post.)
 See the Final Result First
 Before getting into the implementation, let me show you what the /goal command actually does in a few scenarios, from simple to complex.
 1. Write a Fibonacci script
 This test checks whether the agent picks the best algorithm. The prompt is:
 /goal Write a Fibonacci calculation script with the best possible performance.
 What's pretty cool is that DeepSeek went with a fast doubling algorithm, and it's incredibly performant. Image by Author 2. Build a Tower of Hanoi web game
 Everyone knows this game. You could honestly just prompt an LLM directly and get it built. But that predictability is exactly what makes it useful for testing whether each step of the coding loop is working correctly.
 The prompt is:
 /goal Build a playable Tower of Hanoi web game.
 The Towers of Hanoi game built using the /goal command comes with a built-in AI solver. Image by Author 3. Build a chess web game
 Maybe you are not impressed by the Tower of Hanoi example, since a regular prompt to any frontier model can do the same thing without a coding loop. Fair. The chess game experiment is something you should actually try for yourself.
 The prompt is:
 /goal Build a playable chess web game.
Include easy, medium, and hard difficulty levels.
No online multiplayer needed.
Use a Python backend as the AI engine.
 A full-stack chess game with both frontend and backend, built using the /goal command. Image by Author In this experiment, OpenCode first does a quick requirements check with the user after receiving the task.
 It offers suggestions along the way so you can just click next. Once the full requirements list is confirmed, it enters autonomous mode.
 The /goal command breaks down your goal into a list of requirements and then implements them one by one. Image by Author It handles architecture design, builds each feature module, runs unit tests, edge case tests, and end-to-end tests. It only hands the result back to the user when everything passes.
 Pretty cool, right? Want to know how it works? Let's go.
 Building the Coding Loop
 Overall design
 OpenCode updates very fast. Almost every release breaks something or introduces small bugs. So I am not building yet another OpenCode plugin, since a plugin can easily break after an update.
 The good news is that OpenCode lets you define commands and agents using plain Markdown files. Write a few lines of prompts, save the file as Markdown, and drop it in the right directory. That mechanism is the foundation for building a powerful coding loop on the cheap.
 Let me walk you through the interaction flow of the whole loop.
 When a user runs /goal <some task> to start a new coding task, OpenCode sends that task to an agent I call the orchestrator. In this setup, that agent is goal-orch .
 The orchestrator's job is to talk to the user and review completed work. When it receives a task, it does not start coding right away. It first has a short conversation with the user to clarify the details, then breaks the task down into a list of atomic requirements.
 This is different from OpenCode's built-in Plan agent. The /goal orchestrator does not ask open-ended questions. It takes its best guess at what the user wants and asks the user to confirm whether those sub-requirements are correct.
 This works much better when the user is not a software engineer. It is like a capable assistant breaking down tasks for their manager without making the manager feel lost.
 Once the requirements list is confirmed, the orchestrator saves it as a reqs-manifest.md file. This file tracks requirement status and serves as the acceptance record throughout the loop.
 After that, the orchestrator enters autonomous mode. It starts an internal loop that calls a worker agent called goal-worker and sends each requirement to it.
 goal-worker handles code implementation. Before writing any code, it does architecture planning first. If there are technology choices involved, it raises questions. It does not ask the user though. It asks goal-orch . Once goal-orch answers, goal-worker continues.
 After the architecture plan is done, goal-worker enters the loop and starts implementing each requirement.
 Each requirement includes feature code, edge case handling, and unit test code. When all of that is done, goal-worker sends an implementation report back to goal-orch .
 The orchestrator checks the report against the requirement description, confirms completion, and updates the status in the requirements list.
 Inside the loop, goal-orch also builds a DAG from the full requirements list to map out dependencies. Requirements with no dependencies between them get executed in parallel with multiple goal-worker instances, which speeds things up significantly.
 Once all requirements are done, goal-orch runs acceptance tests against the list, checks unit test coverage, and for tasks involving frontend work, it launches end-to-end tests using browser use to confirm everything works.
 When everything passes, the orchestrator writes an implementation report and notifies the user that the task is complete. Then it waits for the next task.
 The execution sequence looks like this:
 The sequence diagram for how the /goal command runs. Image by Author Now, let me walk through how each piece is built.
 Implementing the /goal command
 Since we want /goal to be the entry point for the coding loop, just like in Claude Code, which is the first thing to build in OpenCode.
 Thankfully, creating a command in OpenCode is pretty simple. Just drop a Markdown command definition file into the .opencode/commands/ directory.
 Two things to keep in mind when writing the Markdown command file:
 In the frontmatter , configure a separate agent through the agent parameter. Without a dedicated agent, OpenCode sends the command straight to the default agent. The default agent has no Loop Engineering prompts, so the command fails. For /goal , I set up an orchestrator agent named goal-orch , which I will cover next.
 In the body of the command, use the $ARGUMENTS placeholder to represent the task the user passes when calling the command. When the command sends the message to the orchestrator, this placeholder gets replaced with whatever the user typed, and the full assembled message goes to the orchestrator.
 Implementing the goal-orch agent
 Now let's build the goal-orch agent, which acts as the orchestrator. It handles user communication, requirements clarification, kicks off the development loop, and calls goal-worker , and verifies that work is complete.
 Since we have built OpenCode agents multiple times in previous articles, I will not go into every detail here. Just a few things worth noting:
 Model choice. goal-orch handles workflow orchestration overall, so it needs strong reasoning. I am a fan of the DeepSeek-V4 series, so I went with deepseek-v4-pro .
 System prompt. The prompt needs to cover both workflow orchestration and the agent's own tasks, so it is on the longer side. But that is fine. When you use /goal to send a task, the goal-orch system prompt automatically replaces OpenCode's default prompt, so there is no need to worry about excessive token usage.
 goal-orch must be a primary agent. OpenCode has two agent types: primary agents and subagents. The key difference is that primary agents can call subagents to delegate work, but subagents cannot. Since goal-orch needs to call goal-worker inside the loop, so it has to be a primary agent. The only downside is that it shows up in the agent list at the bottom of the OpenCode interface, but you get us
 The interaction mechanism between primary and subagents. During the loop, when goal-worker hits a tricky problem or needs to make a technology choice, it does not ask the user. It returns the question to goal-orch through a session return. This requires goal-orch to answer the question and then continue the previous sub-session. OpenCode uses a task tool to send messages to subagents. This tool a
 Put simply, it works like a foreman and a worker. The foreman sends the worker off to do a job. The worker gives the foreman a reference number. If the worker hits a problem, they come back and ask the foreman. The foreman solves the problem, takes the reference number and the answer back to the worker, and the worker picks up exactly where they left off. No starting over.
 OpenCode uses task_id to keep track of the context in sub-sessions. Image by Author Parallel task execution. Even though we are building a fully automatic coding loop, the orchestrator can still run multiple goal-worker instances in parallel for requirements that have no dependencies on each other. This speeds up the overall task significantly. After goal-orch confirms the requirements list with 
 The requirements are recalculated into a DAG based on their dependencies, and then executed concurrently. Image by Author Every completed task gets documented. A coding loop handles a large volume of requirements at once, and this process can run for hours. As the task keeps going, the context grows longer and the agent's ability to follow the prompt gets weaker. At that point, we cannot rely on 
 End-to-end testing with browser use . Since we are going fully automatic, why not go all the way? When goal-orch detects that the task involves a frontend page, it calls the agent-browser skill or @playwright-mcp during the final review phase to run end-to-end tests, and captures screenshots as proof that the feature works. Since I am using deepseek-v4 models, I also call the @observer agent for 
 That covers the notable design decisions behind goal-orch . I am not going to paste the full prompt here since prompts are easy to generate with an LLM once you understand the principles. Grab the full source code at the end of the article.
 It's Loop Engineering, and it's also Graph Engineering
 When goal-orch calculates the dependencies across all requirements before starting implementation and compiles them into a DAG, our /goal goes beyond Loop Engineering in the narrow sense. It levels up into a new concept: Graph Engineering.
 In Graph Engineering, the agent no longer completes tasks one by one in a straight line. It pre-arranges all tasks into a dependency map, then lets goal-worker move through that map. goal-orch only checks goal-worker 's results at the end of the map.
 From Loop Engineering to Graph Engineering. Image by Author Now let's look at goal-worker .
 Implementing the goal-worker agent
 Compared to goal-orch , goal-worker is much simpler by design. It just does the work. The simpler its instructions, the better it performs. That said, I did set a few expectations for it in this coding loop:
 Model choice. For tasks that do not need deep reasoning, deepseek-v4-flash honestly outperforms pro . From my experience, in situations involving function calling and skill loading, flash is more accurate than pro and costs much less. So for goal-worker , which is all about execution, deepseek-v4-flash is the right call.
 Ask before acting. Even though it is a subagent, I gave goal-worker the ability to ask questions. Whether it is before starting or in the middle of a task, whenever it hits a technical question, goal-worker stops and asks goal-orch for input. This makes full use of the stronger reasoning model higher up in the chain.
 Plan first, then act. Just like the outer loop driven by goal-orch , goal-worker follows the same rule: plan before doing. Before implementing any new requirement, goal-worker writes out a plan that covers the tech stack, what it intends to change, and how it will handle unit tests and edge cases. That plan goes to goal-orch for review. Only after goal-orch signs off does goal-worker start coding
 Use modern package managers. This is not strictly required, but in practice I noticed that DeepSeek tends to default to traditional tools like pip and npm for global dependency installs. As a developer, that is something I can not live with. So I explicitly require goal-worker to use modern package managers like uv and pnpm . This also keeps your environment clean when the coding loop is building
 That is the full implementation plan for my OpenCode coding loop. I did not paste source code into the article body since all of it is at the end. Go grab it there.
 I also tried to explain the thinking behind this coding loop and how to build it clearly enough that you could just drop this article into OpenCode and have it reconstruct a working /goal command for you. From there, tweak it however you want and build your own version of Loop Engineering. In the age of AI, what is really impossible anymore?
 Before wrapping up, let me quickly cover how to actually use this coding loop.
 How to Use This Coding Loop
 First, go to the end of this article and open the GitHub link I shared. Then come back here and keep reading.
 The source code for the coding loop lives in its own git repo. The only directory you need to care about is .opencode/ . To use this coding loop across all your OpenCode projects, copy the agents and commands directories from that folder into ~/.config/opencode/ , then restart OpenCode.
 If you only want to try it in one specific project, just copy the .opencode/ directory into your project root and restart OpenCode.
 If you just want to take it for a quick spin, clone the repo locally, create a new branch, and run opencode from that branch to start the environment.
 After that, type the /goal command in OpenCode with whatever task you want the coding loop to handle. For example, if you want to build the typing practice game Andrew Ng mentioned in his post, just enter this:
 /goal I want to build a typing practice web app for kids.
At the bottom of the screen are 9 keys representing the positions of 10 fingers, with the thumbs sharing a wider spacebar key that takes up two slots.
Above those 9 keys is a gradient-transparent rectangle.
Letters fall down from the top toward that rectangle, aligned to their matching key positions.
Press the right key as the letter enters the zone and it counts as a hit, triggering a hit effect.
Consecutive correct hits build up increasingly dramatic effects.
The falling speed gradually increases.
At the top of the screen is a scoreboard that adds 1 point for each hit, with a pop animation.
The whole thing should feel exciting and dopamine-triggering, with plenty of visual encouragement.
 A typing mini-game created with /goal command. Image by Author You can be as detailed or as vague as you want. Either way, once you hit enter, the coding loop starts running. goal-orch will open a conversation with you to clarify the requirements.
 You can fill in more details as the conversation develops, or just choose recommend for everything and go make yourself a coffee while it does the work.
 Conclusion
 That is the story of how I built this coding loop inside OpenCode. Before I wrap up, let me answer a few questions you might have.
 1. Can open-source models support this coding loop?
 Yes, I think so. In this article, I used deepseek-v4-pro for goal-orch and deepseek-v4-flash for goal-worker , and both worked well. With the strict constraints of the loop workflow in place, they can handle most of your tasks automatically.
 Also, DeepSeek is releasing the official version of DeepSeek-V4 in mid-July. It will almost certainly come with post-training improvements, and I expect even better results from it.
 2. What results should I expect?
 The coding loop will spend hours working through your task, but do not set your expectations too high for what a single /goal run can produce. That is true even with the most powerful Claude or GPT models.
 As Andrew Ng said, the code implementation loop is just the first of three loops. You need to step into the second loop, the engineer feedback loop. Try out what /goal produced, find all the bugs and things that do not match your vision, organize those into a new spec, and kick off another coding loop. Keep iterating. That is how the product gets better over time.
 3. Can the coding loop replace SDD frameworks like OpenSpec?
 No. They serve different scenarios.
 The coding loop is great for product managers or team leads who want to quickly spin up a minimum viable product from market insights or their own ideas. It prioritizes speed and automation. It is for people who want to hand things off and let the agent run on its own.
 But if your product is going to production, if you have high standards for code quality and implementation details, if you have a detailed product spec, and you are an experienced software engineer who knows exactly what the product should look like, then OpenSpec or another SDD plugin is the right tool. Start from a solid foundation and build your full product step by step.
 I will keep updating this article as I use the loop more, and the Q&A section at the end will keep growing. If you have any questions, leave a comment, and I will get back to you as soon as I can.
 Thanks for reading and subscribing. Next time you are sitting there sipping coffee while OpenCode codes away on its own, if this article comes to mind, please share it with a friend.





 Follow Data Leads Future

 One practical story every month, sharing my hard-learned experiences in the enterprise AI space.




 No spam, No ads, you can unsubscribe anytime.






 Further Reading
 How I Use OpenCode, Oh-My-OpenCode-Slim, and OpenSpec to Build My Own AI Coding Environment
 Ride the wave of AI coding, don’t get swept away by it

 Reflection SDD: Use a Reflection Harness to Level Up Your OpenSpec Workflow
 Stop letting bad spec files tank your code quality

 DeepSeek-V4 Can’t Read Images? I Made It Read
 Don’t wait for a multimodal model, you can use it now

 From OpenSpec to AIDLC: How I Improved My Team’s AI Code Quality
 No new commands to learn, just pick it up and use it

 Source Code









 Here's the source code for this article. Sign up now to get it for free.






 Grab the Source Code
```

---

### [5] How I Cut Kimi K3 Costs in OpenCode

`dataleadsfuture.com` · 2026-07-31 · Peng Qian · **tutorial**, author's own use · about V4: passing

<https://www.dataleadsfuture.com/how-i-cut-kimi-k3-costs-in-opencode/>

> V4 appears as the cheap fallback.

Model surfaces matched: `deepseek-v4`, `deepseek-v4-flash`, `deepseek-v4-pro`

Artifacts (2 kinds):

- `version_string` — DeepSeek Flash; DeepSeek-V4-Pro; Fable 5; GLM-5.2; GPT 5.6; deepseek-v4-flash
- `code_fence` — 9 <pre>/<code> block(s)

```text
Introduction
 Last week, I burned through 7 days' worth of quota in a single day while using the Kimi K3 model on Kimi's Allegreto plan.
 Kimi K3 is genuinely great. Its performance is on par with Claude Fable 5 and GPT 5.6 SOL , so I ended up going full throttle with it all day long.
 But the cost is ridiculous. It runs way higher than GLM-5.2 , DeepSeek-V4 , or even Kimi K2.7 . For someone like me who got spoiled by the cheap API of DeepSeek-V4 , that was just not okay.
 So I started optimizing how I use OpenCode. The goal was to do more with the same Kimi K3 quota while keeping quality about the same.
 After a few days of work, the results are pretty solid. The Allegreto plan now covers a full week of development for me. No more sitting around two days out of five waiting for the weekly Kimi K3 quota to reset.
 If these methods work for me, they should work for you too. So this article is a quick write-up of what I've done, and I hope it helps you lower your Kimi K3 costs in OpenCode.
 All the source code mentioned in this article is at the bottom. Feel free to grab it.
 Pick the Right Provider
 The most fundamental way to cut costs is picking the right provider. The official Coding Plan is the best option. Based on various reports, the third and fourth tiers of the Coding Plan offer dozens of times more value per dollar than the API at the same price. That's a great deal.
 Besides the official Coding Plan, if you'd rather pay per use or call a third-party API, you can just use open platforms that support Kimi K3, like Novita.ai (which offers ultra-low-latency endpoints and generous free credits for new users) and OpenRouter. The setup and how it works are the same.
 Since I already purchased the official Allegreto plan upfront, I'll use the Coding Plan models as the primary example throughout this article.
 Pick the Right Model and Thinking Level (Variants)
 Pick the right model
 The Coding Plan gives you access to two models: K2.7 Code and K3. K3 requires Allegreto or above, and only the K3 model supports 1M context length.
 This week, Kimi also released a K3 model with 256K context, with the model ID k3-256k . At the same time, the official docs confirmed that the standard K3 model consumes twice the quota of k3-256k . That's probably why I burned through a whole week's quota right out of the gate. Without a second thought, I switched my default model to k3-256k .
 A comparison of model capabilities provided on the official website. Screenshot from Kimi You might wonder: since I'm used to DeepSeek-V4 's 1M context, will 256K be enough?
 I don't think you need to worry too much about that.
 The 1M context mainly helps your cache hit rate stay high as conversations get longer. But context rot is still a real problem as the context grows. So if you've ever felt like DeepSeek-V4 gets dumber after a long session, your instinct is right. That's context rot at work.
 On top of that, we normally use frameworks like OpenSpec for SDD (Spec-Driven Development). All the plans and specs worked out earlier with the model get saved as files on disk. Whether you use the /compact command or start a new session, the model reads context from those files. The message history doesn't need to be that long.
 Then there are situations where you need to scan a large codebase or pull in a lot of information from the web. For those cases, we use sub-agents running in separate sub-sessions to handle the research, then return only the key findings to the main session. That approach cuts down context usage a lot.
 All things considered, 256K context is plenty for now. For the Plan and Build agents, just use k3-256k directly.
 If you're using the API from Novita.ai , it's even simpler. Just use Kimi K3 straight up.
 Pick the thinking level
 For a long time, Kimi models felt slow. That's because before K3, Kimi didn't support the reasoning_effort parameter. Every call defaulted to maximum thinking, so each request took forever to finish.
 The K3 release added support for reasoning_effort , with three levels: low , high , and max . But when the model first launched last week, only max was available. That meant every call generated massive thinking tokens through a long chain-of-thought process, which burned through a huge amount of token budget.
 Good news: starting this week, both K3 models support low and high . If you're setting up Kimi K3 in OpenCode for the first time this week, the default thinking level is High . If you configured Kimi K3 last week, make sure you change the thinking level from Max to High .
 If you care more about code quality than cost, or you're doing complex research and don't want lower thinking intensity to hurt your results, there's a middle ground. Use Max thinking in the Plan agent for architecture planning, then use High thinking in the Build agent for code execution.
 One thing to watch out for here is that, according to the official docs , switching the reasoning_effort value invalidates the context cache.
 Right after the switch, the model immediately refills the cache using your existing message history, which costs extra tokens. The official recommendation is to open a new session before switching reasoning_effort , so you avoid paying to refill old messages into the cache.
 There's a more elegant solution though. Set up a dedicated sub-agent with Max thinking, specifically for architecture decisions and hard problems. I'll cover that in the next section.
 Use Sub-Agents to Build an Efficient Team
 With the model and thinking level choices from earlier, you should already be saving a good chunk of tokens. If you want to cut costs even further, the best move is to use sub-agents, each with its own model and prompt, so each agent fits the task it handles.
 Why does this work?
 If you've ever led a dev team, you know that not everyone needs to be a superstar engineer, because superstars come with superstar price tags. From a cost and output perspective, the smartest call is matching the right task to the right person. A team runs best that way.
 So which sub-agents should you set up to get more out of Kimi K3 per dollar?
 Explore
 Have you ever noticed that the bigger your codebase, the faster your token usage spikes?
 That comes down to how LLM caching and codebase retrieval work together. OpenCode puts tools, skills, system prompts, and other mostly static content at the top of the message list when it sends requests to the model. The model caches all of that, so subsequent prompts don't cost much extra.
 The real token hog is actually your most recent prompt. Before making any code changes, OpenCode uses grep to search through relevant code. When the codebase is large, even a few grep calls can pull in a massive amount of text. That's where most of your tokens go.
 The biggest token consumers are user messages and tool call results. Image by Author When you need to pull information from multiple files or web sources, doing that in the main session makes things worse. A huge amount of irrelevant text gets stuffed into the main message list, blowing up both the model's context window and your quota.
 That's why OpenCode uses an explore sub-agent to handle complex research in a separate sub-session. Once the research is done, only the conclusions get returned to the main session. That keeps the main session's token usage lean.
 By default, explore has no model assigned to it, so it falls back to whatever model the primary agent uses, which is Kimi K3 . That keeps costs high.
 The fix is to give the explore agent its own dedicated model. I strongly recommend deepseek-v4-flash . The flash model is cheap, has a long context window, and is plenty capable for text retrieval. Setup is simple. Just add a few lines to ~/.config/opencode/opencode.json :
 {
 "$schema": "https://opencode.ai/config.json",
 "agent": {
 "explore": {
 "model": "novita-ai/deepseek/deepseek-v4-flash"
 }
 }
}
 Quick setup tip:
 If you don't have a Novita account yet, grab your API Key from Novita AI , then paste it into the API KEY field under the Novita provider.
 Move the retrieval cost from the main session to a sub-session running on the DeepSeek Flash model. Image by Author Give it a try. When your bill drops significantly, you'll thank me.
 Executor
 With the explore sub-agent and its dedicated model, we've already cut a big chunk of input token costs. Now let's look at how to reduce output token costs.
 Output token costs mainly come from actually writing code. There's a common misconception here. You might think that since Kimi K3 is so capable, it must be the one writing the final code to make sure things work. That's not actually true.
 Writing code is a lot like a skilled programmer looking at a design doc and typing out what's on the screen. Most of it runs on muscle memory.
 If the coding task is well-planned in advance, and the model doing the actual output isn't too far behind in capability, then whether Kimi K3 or deepseek-v4-flash writes the code, the quality difference is not that big.
 What really matters is who thinks. Good system design and knowing exactly what code will solve the problem efficiently, that's the important part.
 So we can keep the Plan primary agent for task planning and detailed spec generation (I recommend OpenSpec for SDD planning here), then hand off the actual coding to an executor sub-agent. This agent doesn't need to think. It just needs to write the code.
 OpenCode doesn't come with an executor sub-agent out of the box, so we build one ourselves. You don't have to agonize over the prompt. Just open OpenCode and tell Kimi K3 what you want, like this:
 I want to create a sub-agent called `executor`. Its main job is to complete coding and file editing tasks quickly at low cost. It doesn't do any research or information retrieval. That's the primary agent's job. Its only responsibility is to implement code fast based on the primary agent's plan.
 OpenCode will write an executor agent file under ~/.config/opencode/agents/ based on what you described. Once it's done, restart OpenCode, and you're good to go.
 You can also give the executor more responsibilities. For example, you can allow it to run concurrently to speed things up:
 This agent should support concurrent work. When the tasks to be implemented have no dependencies on each other, multiple `executor` agents (no more than 5) can be called in parallel to finish the work faster.
 Don't forget to set the executor agent's model to deepseek-v4-flash .
 ---
description: ...
mode: subagent
model: novita-ai/deepseek/deepseek-v4-flash
permission:
 webfetch: deny
 websearch: deny
 task: deny
 skill: deny
---
 Restart OpenCode again. If you're not sure whether executor is configured correctly, ask OpenCode to run a self-check and evaluate whether the executor is working the way you designed it.
 Ask OpenCode to run a self-check to see if the executor is working properly. Image by Author OpenCode will generate some temporary coding tasks and hand them to executor to complete. It will also try to ask executor to do things it's not permitted to do, just to see if it follows the rules.
 When executor finishes, it returns a summary to the primary agent about whether the task was completed successfully. Kimi K3 never has to output the actual code, so those expensive output token costs stay low.
 At the same time, deepseek-v4-flash is capable enough that your code quality won't take a noticeable hit.
 One important thing to keep in mind with the executor agent: don't let the deepseek-v4 model write frontend code. Due to gaps in post-training, deepseek-v4 really struggles with frontend visual design. So you should restrict the executor agent from handling frontend work:
 This agent does not support frontend development. Any frontend-related work should never be assigned to this agent.
 Or you can set the executor agent to still use the Kimi K3 model, but with the variant set to low .
 If you mostly write backend code, deepseek-v4-flash is enough. If you write frontend code regularly, I'd go with the K3 model plus variant=low .
 That brings up a natural question: how do we make the most out of the thinking level parameter?
 Architect
 To keep Kimi K3 fast and reduce token consumption during the thinking process, we set the default thinking level to High .
 I mentioned earlier that you can set the Plan agent to Max thinking during the planning phase. But what if you need K3 to hit Fable 5-level performance to crack a hard problem? You'd have to set reasoning_effort to Max .
 The official docs say that switching reasoning_effort invalidates the existing context cache, so the recommendation is to open a new session first.
 But that's not realistic in practice. The times when you actually need reasoning_effort=max are usually when you're stuck on an architecture tradeoff or a bug you can't fix after several tries.
 At that point, your message list is already packed with critical context. Starting a new session means K3 has to re-scan all the relevant code from scratch, and it's doing that scan at max thinking intensity, which burns even more tokens.
 And then if you want to switch back from max to high , the cache has to be refilled all over again, wasting another round of tokens. No matter how you slice it, it's not worth it.
 So why does a sub-agent solve this? Because we can set up a K3 sub-agent with reasoning_effort locked at max (I call this one architect ).
 When a hard problem needs solving, the primary agent first summarizes its current session into a condensed brief, then sends that brief along with the problem to the architect agent through a fresh sub-session.
 At that point, architect already understands the full context, so it doesn't need to re-scan all the documents the way a brand-new session would. It only needs to look up a few extra details it cares about, then focus entirely on thinking through the solution.
 I also turn off edit permissions for the architect agent. That way K3 isn't burning max -level thinking on actually writing code fixes. It just figures out the solution. The primary agent handles everything else.
 Building this sub-agent is straightforward. Just open OpenCode and ask it to write the prompt for you:
 Design an architect sub-agent specifically for making architecture decisions, debugging hard bugs, and doing code reviews.
 Don't forget to assign architect the Kimi K3 model with variant set to max :
 ---
description: ...
mode: subagent
model: novita-ai/moonshotai/kimi-k3
variant: max
permission:
 edit: deny
 task: deny
---
 To stop the primary agent from getting lazy and routing every problem to architect , add a guardrail in the sub-agent description. Require the primary agent to try at least two times on its own before delegating:
 Hard bugs must go through at least two independent hypothesis-and-verify rounds by the primary agent with no resolution before they can be delegated here.
 After restarting OpenCode, ask it to run a self-check to verify that architect applies the right thinking level when tackling hard problems:
 Run a self-check on the availability of the architect agent. Image by Author General
 Last but not least, don't overlook the general sub-agent.
 As one of OpenCode's built-in sub-agents, this one has always had a confusing identity.
 Looking at the source code, it's meant for complex research and retrieval work, which puts it in similar territory as architect , only to be called when heavy reasoning is needed. But it also supports concurrent calls to speed up research, which makes its token burn rate closer to executor . The role feels split in two.
 This agent rarely gets called during normal use. But if you ignore it, one day a complex deep research task might come up, and it'll get called concurrently to run complex web searches and research work, all using the default Kimi K3 High .
 So if you want tight control over your LLM token usage, make sure you assign this sub-agent a cheaper model. In my view, deepseek-v4-pro is a great fit here. It's capable enough for complex research, and the token cost isn't much higher than deepseek-v4-flash :
 {
 "$schema": "https://opencode.ai/config.json",
 "agent": {
 "explore": {
 "model": "novita-ai/deepseek/deepseek-v4-flash"
 },
 "general": {
 "model": "novita-ai/deepseek/deepseek-v4-pro"
 }
 }
}
 Conclusion
 That covers everything I've done to use Kimi K3 at lower cost inside OpenCode.
 With Kimi K3's model weights now publicly released, these methods come at the perfect time to help you experience this excellent model without breaking the bank. In my experience, after applying all these settings, even during high-intensity development work, my Allegretto plan went from "work two days, rest five" to "work five days, rest two."
 Even if your main models are Claude or GPT, these optimization approaches still apply. On top of that, the sub-agent setup I recommended here will noticeably speed up your development workflow and boost your overall efficiency.
 That's all for today. I'm Mr. Qian , and I focus on enterprise-level AI Agent applications in practice. If you have any questions about this article, feel free to leave a comment, and I'll get back to you as soon as I can.
 Thank you for reading and subscribing. Feel free to share this article with your friends so more people can benefit from it.





 Follow Data Leads Future

 One practical story every month, sharing my hard-learned experiences in the enterprise AI space.




 No spam, No ads, you can unsubscribe anytime.






 Further Reading
 How I built a coding workflow in OpenCode, Oh-My-OpenCode-Slim, and OpenSpec that rivals Claude Code:
 How I Use OpenCode, Oh-My-OpenCode-Slim, and OpenSpec to Build My Own AI Coding Environment
 Ride the wave of AI coding, don’t get swept away by it

 By adding a reflective agent to the OpenSpec workflow, I managed to get DeepSeek-V4-Pro to perform at the level of Opus:
 Reflection SDD: Use a Reflection Harness to Level Up Your OpenSpec Workflow
 Stop letting bad spec files tank your code quality

 The concept of Loop Engineering has been getting a lot of buzz lately, so I decided to give it a shot in OpenCode. The results were surprisingly good:
 No Plugins Needed, I Built a Fully Automated Coding Loop in OpenCode
 Using DeepSeek-V4 for low-cost Loop Engineering










 Here's the source code for this article. Sign up now to get it for free.






 Grab the Source Code
```

---

### [7] DeepSeek V4 Flash 0731: Is It Cheaper to Run It at Home or Pay Per Token?

`grigio.org` · 2026-08-04 · Luigi · **first-hand analysis**, own calculation + restated vendor/community claims · about V4: yes

<https://grigio.org/deepseek-v4-flash-0731-is-it-cheaper-to-run-it-at-home-or-pay-per-token/>

> STRONGEST sourcing in the set. Opens with a reviewer note separating what was re-computed from what is repeated: 'I couldn't independently verify external claims like the model specs, API pricing, Unsloth's GGUF measurements ... so those are repeated from the cited sources.'

Model surfaces matched: `deepseek v4 flash`, `deepseek-v4-flash`

Artifacts (4 kinds):

- `benchmark_number` — Terminal Bench 2.1
- `price` — $0.0028; $0.014; $0.014/M; $0.028; $0.0518; $0.0518/M
- `version_string` — DeepSeek V4 Flash; deepseek-v4-flash
- `code_fence` — 4 <pre>/<code> block(s)

Benchmark figures, and whether a source is named within 300 chars:

- **cited** `Terminal Bench 2.1`

```text
A note from the reviewer. I re-ran every calculation in this post myself. The math now checks out end to end and uses one consistent blended API rate throughout (see section 4). I couldn't independently verify external claims like the model specs, API pricing, Unsloth's GGUF measurements, or August 2026 hardware street prices, so those are repeated from the cited sources (see section 7). The headl
 The short version
 DeepSeek V4 Flash is a 284B-parameter Mixture-of-Experts model. Only 13B parameters are active per token, and it handles a native 1M-token context under an MIT license. But that "thin" active count is misleading: all 284B weights still have to sit in memory, so you need a machine with 128GB+ of unified memory . No consumer GPU comes close.
 The key finding of the simulation: running V4 Flash locally basically never breaks even against DeepSeek's own API. The API is so cheap (about $0.13 per million blended tokens; $0.14/$0.28 in and out) that a home machine can't even generate enough tokens to cover its own electricity at API rates, let alone pay back the hardware. The best possible local setups use Q4 and Q8 quantization on 192GB m
 Buying hardware only makes sense for privacy, data sovereignty, offline use, or fine-tuning . Not for saving money. Full break-even tables are below.
 1. The model





 Property
 DeepSeek V4 Flash




 Total parameters
 284B


 Active parameters per token
 13B


 Architecture
 Mixture-of-Experts, CSA + HCA attention


 Context window
 1,000,000 tokens (native)


 Native precision
 FP4 expert weights, FP8 KV cache


 Reasoning modes
 Non-Think, Think High, Think Max


 License
 MIT (free to download, commercial use allowed)


 API price
 $0.14 / $0.28 per million input/output tokens




 The 0731 build is V4 Flash's official release, with big agentic gains over the April preview (Terminal Bench 2.1: 82.7 vs 61.8). It even beats the far bigger V4-Pro preview at 72.1.
 One important catch: as of the research date, the improved 0731 weights are API-only . The weights you can download are the April preview (same 284B/13B architecture, just slightly weaker agentic performance). Local means April preview; the API means 0731. The call-site is the same either way: deepseek-v4-flash . So the hardware simulation below runs the April-preview weights, and you should trea
 2. What you need to run it: the full quantization ladder
 Active parameters set how much compute each token needs, but total parameters set the memory bill . The router can send any token to any expert, so every expert has to stay loaded in memory.
 Here's Unsloth's measured GGUF ladder (July 2026), showing file size and combined RAM+VRAM floor:





 Build
 File size
 Memory floor
 Measured quality




 2-bit (UD-IQ2_XXS)
 87 GB
 92–102 GB
 about 78% top-token agreement


 3-bit (UD-IQ3_XXS)
 103 GB
 about 110 GB
 Unsloth's pick for 128GB machines


 4-bit (UD-Q4_K_XL)
 155 GB
 about 162 GB
 about 96% top-token, near-lossless


 8-bit (UD-Q8_K_XL)
 162 GB
 about 169 GB
 Lossless, bit-identical to the April preview




 Here's the surprising part of the ladder: being lossless costs almost nothing. V4 Flash was trained to be quantization-aware, and its expert weights already ship natively in MXFP4, so the 8-bit repack is only about 7 GB bigger than the 4-bit. That's the whole price of running the exact April preview checkpoint. On a 192GB machine, the Q8 vs Q4 memory difference hardly matters.
 The official checkpoint (FP4+FP8) is about 156 GB. On 80GB-GPU datacenter nodes, that's a tight 2× A100 (80GB) fit (160GB total) or a comfortable 2× H200 (282GB). Note that a single 141GB H200 does not fit the roughly 156GB checkpoint without heavy offload. The original post listed "1× H200 (141GB)" as a valid config, but that was a math slip and is corrected here.
 About context: the 1M window is aimed at datacenters. At home, plan on 8K–32K context , with room for the KV cache included in the memory floors above.
 3. The candidate machines (street prices, August 2026)
 The 2026 memory shortage has pushed unified-memory prices way up. NVIDIA raised the DGX Spark MSRP from $3,999 to $4,699 in February, and used M3 Ultra 512GB units have traded near $25K.





 Machine
 Price
 Builds that fit
 Est. tps*




 Mini PC Ryzen AI Max+ 395 (128GB)
 $2,600–3,200
 Q2, Q3
 about 8–9


 NVIDIA DGX Spark (128GB)
 $4,699
 Q2, Q3
 about 7–8


 Mac Studio M2 Ultra 192GB (used)
 about $4,000
 Q2, Q3, Q4, Q8
 Q4 about 18


 Mac Studio M3 Ultra 192GB (used)
 about $6,000
 Q2, Q3, Q4, Q8
 Q4 about 22


 DeepSeek API
 pay per token
 full precision
 about 84




 * Speeds are extrapolated from published measurements: about 6 tps on a GB10 at 2-bit (llama.cpp PR #24162), about 11 tps on Strix Halo for a 235B-class MoE (Tech Times), about 25 tps on a 192GB M3 Ultra (MLX, June). There's no canonical V4 Flash on home hardware benchmark yet, so treat these speeds as rough.
 For MoE generation, bandwidth matters more than raw compute. The 128GB boxes measure around 215 GB/s, while the M2/M3 Ultra run at 800–819 GB/s. Token speed is bound by memory bandwidth.
 Assumptions I pinned down for reproducibility (used in every table below):
 Purchase prices (midpoints): Ryzen $2,900 · DGX Spark $4,699 · M2 Ultra $4,000 · M3 Ultra $6,000.
 Electricity: $0.20/kWh, 24/7. Ryzen 100W → $0.48/day · DGX 200W → $0.96/day · Macs 121W → $0.58/day.
 Blended API rate = $0.128/M (see section 4 for how I got there). Used consistently in 4b, 4c, and 4e.
 Weights: April preview locally; 0731 full precision on the API.
 4. The simulation
 Method. I blended the token mix so that 2/3 of generated tokens are input and 1/3 are output. Input is priced at 30% cache miss ($0.14/M) and 70% cache hit ($0.014/M, a conservative pick; sources range $0.0028–0.028). Blended input = 0.30×$0.14 + 0.70×$0.014 = $0.0518/M . Blended API rate = (2/3)×$0.0518 + (1/3)×$0.28 = $0.128/M . Electricity runs at $0.20/kWh around the clock. Token speed sets m
 4a. Monthly API cost, by usage scenario





 Scenario
 Tokens/day
 API cost/day
 API cost/month




 Light (casual chat)
 1,000,000
 $0.13
 $3.8


 Medium (AI coding + agent)
 5,000,000
 $0.64
 $19


 Heavy (autonomous agent)
 20,000,000
 $2.56
 $77


 Team service
 100,000,000
 $12.79
 $384




 (The original post quoted $0.11 / $3.3 for the "Light" row, which came from an inconsistent token-mix assumption. I corrected it to the same $0.128/M blended rate used everywhere else.)
 4b. Local capacity and unit cost (per config, running flat out 24/7)





 Hardware
 Quant
 Max tok/day
 Elec/day
 Local opex $/M
 vs API*




 Ryzen AI Max+ 395
 Q3
 691,200
 $0.48
 $0.69
 5.4×


 Ryzen AI Max+ 395
 Q2
 777,600
 $0.48
 $0.62
 4.8×


 DGX Spark
 Q3
 604,800
 $0.96
 $1.59
 12.4×


 DGX Spark
 Q2
 691,200
 $0.96
 $1.39
 10.9×


 Mac Studio M2 Ultra 192GB
 Q4
 1,555,200
 $0.58
 $0.37
 2.9×


 Mac Studio M2 Ultra 192GB
 Q8
 1,209,600
 $0.58
 $0.48
 3.8×


 Mac Studio M3 Ultra 192GB
 Q4
 1,900,800
 $0.58
 $0.30
 2.4×


 Mac Studio M3 Ultra 192GB
 Q8
 1,468,800
 $0.58
 $0.39
 3.1×




 * vs API = local opex divided by the blended API $0.128/M. (The original post's ratios implied an unstated rate of about $0.19/M. I corrected them to the $0.128/M used everywhere else.)
 Even the best option (192GB M3 Ultra at Q4) costs 2.4× the API in electricity alone , before you've bought anything. Running local is the pricier route in every config.
 4c. Break-even months to recover the purchase (no resale)
 Break-even is tied to each machine (it depends on purchase plus electricity, not the quant). And the numbers show it's only "reachable" at token volumes these machines physically can't produce :





 Hardware
 Quant
 1M/d
 5M/d
 20M/d
 100M/d




 Ryzen AI Max+ 395
 Q3
 never
 596 mo (50 yr)
 46 mo
 8 mo


 DGX Spark
 Q3
 never
 never
 97 mo
 13 mo


 Mac Studio M2 Ultra 192GB
 Q4
 never
 2,193 mo
 67 mo
 11 mo


 Mac Studio M3 Ultra 192GB
 Q4
 never
 3,290 mo
 100 mo
 16 mo




 At 100M tokens/day the hardware "pays for itself" in 8–16 months. But 100M tokens/day is 50–165× more than a 128–192GB machine can produce (capacity sits at 0.6–1.9M/day). Every non-"never" cell is physically impossible. (The 5M/day cells came out to decades, and I re-derived them from the pinned purchase prices, correcting the original 2,105/3,158 months.)
 4d. Five-year total cost of ownership (purchase + electricity minus 40% resale)





 Hardware
 Quant
 5-yr TCO
 $/month




 Ryzen AI Max+ 395
 Q3
 $2,616
 $44


 DGX Spark
 Q3
 $4,571
 $76


 Mac Studio M2 Ultra 192GB
 Q4/Q8
 $3,451
 $58


 Mac Studio M3 Ultra 192GB
 Q4/Q8
 $4,651
 $78




 Compare that to the API: even the "heavy" 20M-token/day scenario costs just $77/month on the API. The annualized hardware cost alone ($44–78/month) tops the API bill for every usage level except the very highest. (The TCO formula is 0.6 × purchase + electricity , which assumes the machine keeps 40% of its value after five years.)
 4e. Operational break-even (tokens/day just to cover electricity)
 This is the API-usage volume whose bill equals the machine's daily electricity, or the "revenue" the machine would need to earn to pay for its own power. The last column reads: what share of that target the machine can actually supply running flat out.





 Hardware
 Quant
 Elec/day
 Op. break-even
 % of target supplied




 Ryzen AI Max+ 395
 Q3
 $0.48
 3.75M tok/day
 18%


 Ryzen AI Max+ 395
 Q2
 $0.48
 3.75M tok/day
 21%


 DGX Spark
 Q3
 $0.96
 7.50M tok/day
 8%


 DGX Spark
 Q2
 $0.96
 7.50M tok/day
 9%


 Mac Studio M2 Ultra 192GB
 Q4
 $0.58
 4.53M tok/day
 34%


 Mac Studio M2 Ultra 192GB
 Q8
 $0.58
 4.53M tok/day
 27%


 Mac Studio M3 Ultra 192GB
 Q4
 $0.58
 4.53M tok/day
 42%


 Mac Studio M3 Ultra 192GB
 Q8
 $0.58
 4.53M tok/day
 32%




 If a machine supplies fewer tokens/day than its operational break-even, and that's true for all the home configs here, then local generation is pricier per token than the API even before you add the purchase price . The fastest machine (M3 Ultra Q4) can only supply 42% of the volume it would need to pay its own electricity at API rates. (The original post called this column "% of capacity" and us
 5. When does buying hardware actually make sense?
 On pure token economics: never. DeepSeek sells tokens cheaper than your home electricity. Buying hardware only wins on these non-financial grounds:
 Privacy / data sovereignty for regulated sectors and confidential code or documents that have to stay on premises. This is the one case where the premium is clearly worth it.
 Predictable fixed costs. One capex charge instead of a variable bill, with no token limits, no rate caps, and no 3 a.m. outages.
 Offline operation. Full autonomous inference with no connectivity needed.
 Fine-tuning / research. The MIT open weights let you modify the model in ways a hosted API never will. (Here's where Q4/Q8 matter: Q8 gives you the bit-identical April preview checkpoint locally.)
 Hardware speculation. The 2026 memory shortage is making unified-memory boxes appreciate (DGX Spark up 17% in six months; used M3 Ultra 512GB spiked to about $25K). That's an investment bet, not cost savings.
 When it does not make sense: to save money, to get more speed (the API is about 4–14× faster at roughly 84 tps vs 6–22 tps local), or to reach the improved 0731 build (API-only for now).
 6. Caveats
 Quality. Local runs are quantized (up to 96% top-token at Q4; Q8 is lossless to the April preview , not the 0731). The API serves the full-precision 0731 build.
 Context. The 1M-window target is datacenter-first; realistic local context is 8K–32K.
 Speed. 6–22 tps local vs about 84 tps on the API. Fine for chat, slow for autonomous agents.
 Speed figures are extrapolated from community reports; there was no canonical home benchmark for V4 Flash when this was written.
 Prices reflect the memory-shortage market of August 2026 and drift quickly.
 External facts (model specs, GGUF quality, street prices) come from the sources in section 7 and weren't independently verifiable on the research date.
 7. Assumptions & sources
 API pricing: deepseek.com official (V4-Flash $0.14 in miss / $0.28 out per million; assumed cache-hit discount of 1/10). Sources disagree on the cache-hit value ($0.0028 vs $0.028), but the conclusion doesn't depend on it. One blended rate used throughout: $0.128/M.
 GGUF ladder and memory floors: Unsloth published measurements, July 2026.
 Speeds: llama.cpp PR #24162, Tech Times, MLX (June), and community reports.
 Hardware prices: NVIDIA ($4,699), laptop and mini-PC market surveys ($2,400–3,200 for Strix Halo 128GB), and resale-market surveys for used Mac Studios.
 Model specs and benchmarks: DeepSeek model card, felloai.com, baseten.co, Artificial Analysis.
 Prepared August 4, 2026; independently re-derived for internal consistency on the same date. All costs in USD. Not investment advice; hardware prices and API tiers change quickly.
```

---

### [11] Gemma 4 26B edges out DeepSeek V4 Flash (284B) on ds4-eval-92, at 5x the speed

`lucebox.com` · 2026-05-20 · Davide Ciffa · **benchmark**, own measurement (vendor sells the winning hardware) · about V4: yes

<https://www.lucebox.com/blog/gemma-vs-deepseek/>

> Conditions stated in unusual detail: quant, memory, mode, harness, same eval set and scoring. Reports its own product's box TYING, not winning.

Model surfaces matched: `deepseek v4 flash`

Artifacts (4 kinds):

- `benchmark_number` — 26B edges out DeepSeek V4 Flash (284B) on ds4-eval-92; 79.3% on ds4-eval-92; ds4-eval-92 a 24; ds4-eval-92 comes from antirez/ds4; ds4-eval-92 from antirez/ds4; ds4-eval-92, Gemma 4
- `version_string` — DeepSeek V4 Flash; Qwen3.5-27B
- `comparison_cond` — against DeepSeek's 13B, so batch; against a usable context window
- `code_fence` — 4 <pre>/<code> block(s)

Benchmark figures, and whether a source is named within 300 chars:

- *bare* `26B edges out DeepSeek V4 Flash (284B) on ds4-eval-92`
- *bare* `ds4-eval-92, Gemma 4`
- **cited** `ds4-eval-92, nothink: Gemma 4`
- **cited** `ds4-eval-92 comes from antirez/ds4`
- *bare* `79.3% on ds4-eval-92`
- *bare* `ds4-eval-92 a 24`
- **cited** `ds4-eval-92 from antirez/ds4`

```text
May 2026
 By Davide Ciffa and Erik LaBianca
 Gemma 4 26B edges out DeepSeek V4 Flash (284B) on ds4-eval-92, at 5x the speed
 ds4-eval-92 head-to-head. A 24 GB RTX 5090 Laptop running Gemma 4 26B ties DeepSeek V4 Flash (284B) on a 192 GB Mac, edges it on the same box, and decodes about 5x faster.
 We expected the 192 GB Mac to have the edge: far more memory, a far bigger model. It didn't pan out. On ds4-eval-92, Gemma 4 26B (26B params, 4-bit, in 24 GB) tied DeepSeek V4 Flash (284B params, run at ~2-bit to fit the Mac) at 78.3%, edged it to 79.3% on that same Mac, and decoded about 5x faster.
 TL;DR
 Quality. ds4-eval-92, nothink: Gemma 4 26B (26B params, Q4_K_M, 24 GB) and DeepSeek V4 Flash (284B params, ~2-bit, 192 GB Mac) both score 78.3% , and Gemma noses ahead to 79.3% on that same Mac via MLX. A model an eleventh the size, holding even.
 Efficiency. The gap is efficiency: 101.4 tok/s for Gemma vs 20.7 for DeepSeek (~5x decode), a 9.8 s median answer against 144.8 s , in 24 GB instead of 192.
 Why. Gemma 4 26B (a4b) activates ~4B params per token against DeepSeek's 13B, so batch-1 decode reads far less weight per step. DFlash amortizes that further, and Q4_K_M fits the whole model in 24 GB.
 Mode. DeepSeek lands ~78% in every mode and provider we measured; we run Gemma in nothink, whose accuracy is within noise of its think score.
 The benchmark
 ds4-eval-92 comes from antirez/ds4 , Salvatore Sanfilippo's DeepSeek V4 Flash engine, the same one we're running on the Mac here. We ported its 92-case ds4_eval.c set into luce-bench; the provenance, grading, and request rules are in our Running the benchmarks intro to luce-bench. It's adversarial enough that nothing we ran broke ~82%, so these differences are small and earned token-for-token.
 What we compared
 Local Gemma 4 26B (26B total, ~4B active, Q4_K_M in 24 GB; RTX 5090 Laptop, lucebox + DFlash) against local DeepSeek V4 Flash (284B total, 13B active, run at ds4's ~2-bit IQ2_XXS to fit; 192 GB Mac Studio, M2 Ultra, 60-core GPU, native ds4_server ). Each at the size, quant, and mode you'd use to run AI models locally , same eval set, same max_tokens policy, same scoring. We run Gemma in nothink; 
 Head to head
 Each model at the size, quant, and mode you'd run locally:
 Model Where Mode Pass Accuracy Wall (med) tok/s
 Gemma 4 26B (26B, 4-bit) RTX 5090 Laptop, 24 GB nothink 72/92 78.3% 9.8 s 101.4
 DeepSeek V4 Flash (284B, ~2-bit) Mac Studio, 192 GB think 72/92 78.3% 144.8 s 20.7


 Accuracy

 ds4-eval-92 accuracy, nothink Gemma vs think DeepSeek. Both 78.3% (72/92).
 It's close. On the laptop in nothink it's a dead heat, 78.3% each (72/92). On the same Mac via MLX, Gemma noses ahead (79.3%); in think, by three (81.5%, one seed). So a 26B model edges a 284B one on this set. State the qualifier plainly: to run on the Mac at all the big model is squeezed to ~2-bit, while Gemma runs at 4-bit, so part of the story is that 284B at 2-bit doesn't pull away from 26B a
 Throughput

 Decode throughput, local. Gemma 4 26B (nothink) on RTX 5090 Laptop = 101.4 tok/s, DeepSeek V4 Flash (think) on Mac 192 GB = 20.7 tok/s.
 On the same prompts, the laptop Gemma run decodes about 4.9x faster (101.4 vs 20.7 tok/s), and because nothink Gemma answers in far fewer tokens, a median answer lands in 9.8 s against 144.8 s. The Mac isn't slow because it's a Mac. It's slow because DeepSeek V4 Flash reads far more weight per decoded token than Gemma's a4b MoE does, and Q-style DeepSeek decode on the Mac doesn't get the matmul t
 Why the laptop is so fast
 A 192 GB Mac has 8x the memory and runs a model 11x the size, so the result looks backwards. We think three things explain it, plus a fourth that doesn't.
 Only ~4B active per token. Gemma 4 26B (a4b) is a 26B MoE with roughly 4B active parameters per token. Batch-1 decode is bandwidth-bound, so what matters is bytes read per token, not total parameter count. Touching ~4B 4-bit weights per step is a small fraction of DeepSeek V4 Flash's 13B active (of 284B total). This is the main reason the laptop path is so fast.
 DFlash speculative decode. Each verified target step commits multiple accepted tokens per weight pass, amortizing the bandwidth-bound matmul across the accept window, on top of the already-small a4b footprint.
 The model size is right. 26B in Q4_K_M fits in 24 GB with room for a long context. DeepSeek V4 Flash is large enough that local Mac serving has to trade throughput against a usable context window.
 Not memory bandwidth. It's tempting to credit dedicated VRAM, but the M2 Ultra's unified memory runs ~800 GB/s, in the same range as the laptop's GDDR7. What does the work is how few bytes Gemma's MoE reads per token, multiplied by DFlash acceptance. Big memory doesn't help when the bottleneck is per-token weight reads, not capacity.
 Same Mac, smaller model
 The laptop makes the speed gap dramatic, but it isn't what wins on quality. We also ran Gemma 4 26B on the same 192 GB Mac Studio through Apple MLX (8-bit, nothink): 79.3% on ds4-eval-92, a point above DeepSeek V4 Flash's 78.3% on that box, and at ~40 tok/s against 20.7. On identical hardware, each model on its own local stack, the small MoE held its own and then some. This doesn't crown Gemma th
 A note on serving
 Gemma 4 26B is sensitive to how it's served: the same model on OpenRouter scored 73.9%, about 5 points under our local lucebox serve, while DeepSeek holds its ~78% across providers.
 Takeaway
 DeepSeek V4 Flash is a quality model, and this isn't a knock on it. But on ds4-eval-92 a 24 GB laptop running Gemma 4 26B matched-to-beat it on accuracy and ran ~5x faster, and even on the same Mac the smaller model held its own. Read it this way: a small MoE that happens to be strong on your workload can deliver that quality at a fraction of the memory and latency. Find the model that does well 
 ds4-eval-92 from antirez/ds4 (MIT), run via luce-bench, single seed. Hardware: 24 GB RTX 5090 Laptop vs 192 GB Mac Studio (M2 Ultra, 60-core GPU), local serving. Project: github.com/Luce-Org/lucebox-hub .
 Related
 Launch and tune Lucebox with real agent harnesses
 Laguna XS.2 on a 3090: 111 tok/s, 5.4x prefill, first MoE target for PFlash
 DFlash on ggml: up to 207 tok/s Qwen3.5-27B on a RTX 3090
 The eGPU memory myth
 Run Gemma 4 26B locally with lucebox
 DFlash + Q4_K_M on a single 24 GB GPU. Get the numbers in this post.
 GitHub Models Discord Compare hardware
```

---

### [12] DeepSeek V4 Flash: 284B model, up to 32 tok/s on AMD Ryzen AI MAX+ 395

`lucebox.com` · 2026-07-16 · Davide Ciffa · **benchmark**, own measurement (vendor sells the hardware) · about V4: yes

<https://www.lucebox.com/blog/deepseek-v4-strix-halo/>

> Cites third-party comparison values with a date and names them as 'community submissions, not a controlled A/B test'.

Model surfaces matched: `deepseek v4 flash`, `deepseek-v4-flash`

Artifacts (3 kinds):

- `benchmark_number` — 10/10 on our small GSM8K; 3/3 on a HumanEval; 4 26B vs DeepSeek V4 Flash on ds4-eval-92
- `version_string` — DeepSeek V4 Flash; DeepSeek-V4-Flash
- `code_fence` — 2 <pre>/<code> block(s)

Benchmark figures, and whether a source is named within 300 chars:

- *bare* `10/10 on our small GSM8K`
- *bare* `3/3 on a HumanEval`
- **cited** `4 26B vs DeepSeek V4 Flash on ds4-eval-92`

```text
July 2026
 By Davide Ciffa
 DeepSeek V4 Flash: 284B model, up to 32 tok/s on AMD Ryzen AI MAX+ 395
 AMD-Powered Lucebox runs the full DeepSeek V4 Flash target locally on AMD Ryzen AI MAX+ 395 with 128 GB unified memory: up to 32.0 tok/s decode and roughly 250 tok/s with indexed sparse prefill. The code used for both paths is on Lucebox main .
 284B
 parameter target running locally on an AMD APU with 128 GB unified memory

 up to 32
 tok/s decode on the public LocalMaxxing entry

 ~250
 tok/s indexed sparse prefill; 246.8–255.9 across the 8K validation cases


 DeepSeek V4 Flash is a 284B mixture-of-experts model. Its target and draft both fit because the CPU and Radeon 8060S share the same 128 GB LPDDR5X pool. There is no discrete GPU, second machine, or remote inference service in this run: prompts and model execution stay on the local system.
 The LocalMaxxing result
 We submitted the run to LocalMaxxing . On July 18, its next-fastest DeepSeek V4 Flash entry for the Radeon 8060S was HipFire at 18.99 tok/s. The previous best in the site’s Ryzen AI Max 395 unified-memory group was DwarfStar at 15.6 tok/s.
 Published DeepSeek V4 Flash decode on Strix Halo · tok/s
 DwarfStar Q2_K Ryzen AI Max 395


 15.60

 HipFire MQ2 + MTP Radeon 8060S


 18.99

 Lucebox ROCmFPX + DSpark current main


 32.00

 These are community submissions, not a controlled A/B test. Engines, quants, context sizes, and output lengths differ. Source: LocalMaxxing Ryzen AI Max 395 hardware page , checked July 18, 2026.

 That puts our run 68.5% ahead of HipFire and at 2.05× the DwarfStar result. These are comparisons against the public LocalMaxxing entries shown above, not controlled A/B tests.
 ROCmFPX: fitting 284B weights into 128 GB
 ROCmFPX is not one quantization format. It is a family of block formats built around the AMD ROCm/HIP path. Each block holds 32 weights as packed low-bit codes plus one or two small scales. ROCmFP2 stores a block in 10 bytes, or 2.50 bits per weight; ROCmFP3 uses 3.50 bits per weight; and the fast ROCmFP4 layout uses 4.25.
 For DeepSeek V4 Flash, we added the missing 2-bit format and its HIP kernels, then built a Strix-specific mixed-precision recipe. The enormous routed-expert gate and up matrices use ROCmFP2, expert down projections use ROCmFP3, and dense or more sensitive projections keep ROCmFP4 or higher precision. We used an importance matrix during quantization and kept the model’s MTP head. The final 102.3 G
 On-disk model budget against 128 GB unified memory




 102.3 GB ROCmFPX target (95.3 GiB)
 11.3 GB DSpark draft (10.5 GiB)
 14.4 GB remaining capacity before OS and runtime allocations

 File sizes are shown in decimal GB to match the marketed 128 GB system capacity. Unified-memory residency is managed by ROCm and does not map one-for-one to this simple on-disk bar.

 Piece Measured configuration
 Hardware Ryzen AI MAX+ 395, Radeon 8060S ( gfx1151 ), 128 GB LPDDR5X
 Target DeepSeek-V4-Flash-ROCMFP2-STRIX.gguf , 102.3 GB
 Draft DeepSeek-V4-Flash-DSpark-draft-Q4RMFP4-denseF16.gguf , 11.3 GB
 Runtime ROCm 7.2.4, HIP gfx1151 , platform performance , Radeon high (2.9 GHz observed), q=4 verification cap
 Server context 8,192 tokens in the published setup

 The format is also part of the speed result. At batch one, every generated token streams the active weights across all 43 layers, so decode is mostly limited by memory traffic. The ROCmFPX kernels read the packed blocks directly, expand their small codebooks in registers with AMD byte-permute instructions, and feed integer dot products without a separate codebook gather. In practice, the file lay
 Decode: up to 32 tok/s
 ROCmFPX handles the weight traffic. We then added a DeepSeek-specific HIP decode path for the model’s hyper-connections, attention, routing, and expert work. With no speculative draft, that target runs at 25.31 tok/s autoregressive.
 DSpark is the next layer. With a q=4 batch, its small draft proposes up to three new tokens and the 284B target verifies four positions, including the current seed, in one fused pass.
 01 · propose
 DSpark draft
 A compact three-layer draft proposes the next few tokens from captured target features.

 02 · verify
 q=4 target pass
 The 284B target checks several positions together through the fused HIP graph.

 03 · commit
 accepted prefix
 Correct proposals are committed in one step; the target repairs the first miss.


 With a q=4 cap and adaptive width disabled, the public run reached 32.0 tok/s , 26.4% above the 25.31 tok/s autoregressive result. The gain varies with how many draft tokens the target accepts.
 Same Lucebox target · decode tok/s
 Autoregressive


 25.31

 DSpark q=4


 32.00

 Greedy decode, expert top-k 4, performance platform profile, high GPU performance level.

 We also worked with Geometric , which helps ML teams find and ship faster GPU kernels. For Lucebox, DeanoC optimized the HIP routing path with dedicated ROCm TOP_K and ARGSORT kernels. In our A/B test, they made expert selection 3.5–7× faster in the kernel microbench and improved end-to-end decode by 0.44%. That work was measured separately and is not part of the public 32 tok/s main-branch run.
 On main , the q=4 ROCmFP4 path now decodes each packed dense weight once and applies it to all four verification columns instead of unpacking it four times. That change added 2.1–2.3%. The ROCmFPX format, fused decode path, DSpark verifier, sparse prefill, and q=4 weight reuse are all included in the reproduction below; no integration branch or private patch is required.
 Test setup and quality checks
 LocalMaxxing decode
 32.0 tok/s output

 LocalMaxxing prefill
 245 tok/s · sparse

 8K sparse validation
 246.8–255.9 tok/s

 Exact short-prompt prefill
 22.5–23 tok/s

 Published request
 2,048 prompt · 510 output

 Sampling
 temperature 0 · batch 1

 Clock profile
 platform performance · GPU high

 DSpark verification
 q=4 cap · adaptive width off


 The LocalMaxxing request used 2,048 prompt tokens, 510 output tokens, an 8,192-token context, temperature zero, and batch one. We also reran five GSM and five MATH prompts after the kernel changes; all ten completed with the expected answer. That is a regression check, not an accuracy benchmark.
 The 32 tok/s profile uses --ds4-expert-top-k 4 instead of the model default of six experts. This changes model execution and trades some quality margin for speed. Before using it for a specific workload, compare it with six-expert autoregressive output on that workload.
 Sparse prefill: roughly 250 tok/s
 The public LocalMaxxing request reports 245 tok/s prefill with --ds4-prefill sparse . In a separate 7,960-token validation, indexed sparse prefill reached 251.79 tok/s; the 8K cases ranged from 246.8 to 255.9 tok/s . At roughly 24K tokens, throughput was 221.9 tok/s.
 Indexed sparse prefill as measured · tok/s
 Published request 2,048 prompt tokens


 245.00

 Validation request 7,960 prompt tokens


 251.79

 Long request roughly 24K tokens


 221.90

 Absolute throughput from three indexed sparse runs. Prompt lengths and benchmark conditions differ, so the bars show the observed operating range rather than a controlled scaling curve.

 Sparse prefill uses DeepSeek V4 Flash’s learned indexer to limit compressed-history attention. It also batches work layer by layer, which changes floating-point reduction order. The output is not byte-identical to tokenwise exact prefill, so sparse mode remains opt-in. It scored 10/10 on our small GSM8K set and 3/3 on a HumanEval smoke set; we have not run a broad quality evaluation yet.
 For reference, tokenwise exact prefill measured 22.5–23 tok/s on our short GSM/MATH prompts and 16.46 tok/s on the paired 7,960-token test. Those figures use a different execution path. Use the roughly 250 tok/s result only for indexed sparse prefill.
 Reproducing the run
 Starting from a 128 GB Strix Halo machine with ROCm 7.2.4 already installed:
 sudo apt-get update
sudo apt-get install -y build-essential cmake git ninja-build curl \
 hipblas-dev hipcub-dev rocblas-dev rocprim-dev rocwmma-dev

git clone --branch main --recurse-submodules \
 https://github.com/Luce-Org/lucebox.git
cd lucebox

cmake -S server -B server/build-hip -G Ninja \
 -DCMAKE_BUILD_TYPE=Release \
 -DCMAKE_HIP_COMPILER=/opt/rocm/lib/llvm/bin/clang++ \
 -DDFLASH27B_GPU_BACKEND=hip \
 -DDFLASH27B_HIP_ARCHITECTURES=gfx1151 \
 -DDFLASH27B_HIP_SM80_EQUIV=ON \
 -DCMAKE_HIP_FLAGS=-DDFLASH_WAVE_SIZE=32 \
 -DGGML_HIP_MMQ_MFMA=ON \
 -DGGML_HIP_NO_VMM=ON \
 -DGGML_HIP_GRAPHS=OFF

cmake --build server/build-hip --target dflash_server -j"$(nproc)"
 Download the ROCmFPX target and DSpark draft , then start the measured profile:
 mkdir -p models
curl -L -C - --retry 5 \
 -o models/DeepSeek-V4-Flash-ROCMFP2-STRIX.gguf \
 "https://huggingface.co/Lucebox/DeepSeek-V4-Flash-ROCMFPX/resolve/main/DeepSeek-V4-Flash-ROCMFP2-STRIX.gguf"
curl -L -C - --retry 5 \
 -o models/DeepSeek-V4-Flash-DSpark-draft-Q4RMFP4-denseF16.gguf \
 "https://huggingface.co/Lucebox/DeepSeek-V4-Flash-DSpark-Drafter-GGUF/resolve/main/DeepSeek-V4-Flash-DSpark-draft-Q4RMFP4-denseF16.gguf"

MODEL="$PWD/models/DeepSeek-V4-Flash-ROCMFP2-STRIX.gguf"
DRAFT="$PWD/models/DeepSeek-V4-Flash-DSpark-draft-Q4RMFP4-denseF16.gguf"

echo performance | sudo tee /sys/firmware/acpi/platform_profile
sudo /opt/rocm/bin/rocm-smi -d 0 --setperflevel high
printf '0\n' > /tmp/ds4_awidth
printf '4\n' > /tmp/ds4_spec_q

DFLASH_DS4_SPEC=1 \
DFLASH_DS4_FUSED_VERIFY=1 \
DFLASH_DS4_SPEC_Q=4 \
DFLASH_DS4_TIMING=1 \
DFLASH_DS4_DRAFT="$DRAFT" \
LUCE_MMVQ_MAX_NCOLS=4 \
./server/build-hip/dflash_server "$MODEL" \
 --target-device hip:0 \
 --host 127.0.0.1 --port 8000 \
 --max-ctx 8192 --default-max-tokens 2048 \
 --chunk 2048 --ds4-prefill sparse \
 --ds4-fused-decode \
 --ds4-expert-top-k 4 \
 --prefix-cache-slots 0 --prefill-cache-slots 0 \
 --disk-prefix-cache off
 Warm the model once and use temperature: 0 . The server prints decode speed on its [deepseek4] DSpark decode line. DFLASH_DS4_SPEC_Q=4 sets the DS4 verification cap; --verify-width is a Laguna option and is not used here. The implementation may shorten a batch at a compressor boundary, which is required for correct state handling.
 The two clock commands are also part of the measured setup. On our validation machine, Radeon high held the graphics clock at 2.9 GHz; automatic clocks can cost several tokens per second. The published request reported 245 tok/s sparse prefill and 32.0 tok/s decode. Throughput varies with prompt shape and, for decode, how many DSpark proposals the target accepts. If you switch to exact prefill or
 Measured July 2026 on a Ryzen AI MAX+ 395 / Radeon 8060S ( gfx1151 ), 128 GB LPDDR5X, ROCm 7.2.4, platform profile performance , and Radeon performance level high (2.9 GHz observed). Target: DeepSeek-V4-Flash-ROCMFP2-STRIX.gguf . Draft: DeepSeek-V4-Flash-DSpark-draft-Q4RMFP4-denseF16.gguf . Public LocalMaxxing entry: 32.0 tok/s output and 245 tok/s sparse prefill, 2,048 prompt tokens, 510 output 
 Related
 DFlash + PFlash on AMD Strix Halo
 Gemma 4 26B vs DeepSeek V4 Flash on ds4-eval-92
 antirez/ds4: a DeepSeek V4 Flash implementation
 Lucebox source code
 Run DeepSeek V4 Flash on AMD Ryzen AI MAX+ 395
 Current Lucebox main: up to 32 tok/s decode and roughly 250 tok/s indexed sparse prefill on AMD Ryzen AI MAX+ 395 with 128 GB unified memory.
 GitHub Target GGUF Compare hardware Discord
```

---

### [13] Lucebox (AMD Radeon AI PRO R9700 + Strix Halo) Beats NVIDIA DGX Spark by 3.63x on DeepSeek V4 Flash Decode Speed

`lucebox.com` · 2026-07-20 · Davide Ciffa · **benchmark**, own measurement (vendor sells the winning hardware) · about V4: yes

<https://www.lucebox.com/blog/deepseek-v4-asymmetric-parallelism/>

> Headline is the vendor's box beating NVIDIA 3.63x. Conditions and list-price sources given; still a vendor benchmarking itself.

Model surfaces matched: `deepseek v4 flash`, `deepseek-v4-flash`

Artifacts (4 kinds):

- `benchmark_number` — 395 Gemma 4 26B vs DeepSeek V4 Flash on ds4-eval-92
- `price` — $4,699; $4,699,; $6,499; $9,398
- `version_string` — DeepSeek V4 Flash; DeepSeek V4 Flash 284B; DeepSeek-V4-Flash
- `code_fence` — 2 <pre>/<code> block(s)

Benchmark figures, and whether a source is named within 300 chars:

- **cited** `395 Gemma 4 26B vs DeepSeek V4 Flash on ds4-eval-92`

```text
By Davide Ciffa
 Lucebox (AMD Radeon AI PRO R9700 + Strix Halo) Beats NVIDIA DGX Spark by 3.63x on DeepSeek V4 Flash Decode Speed
 51.1 tok/s (Lucebox) vs 14.09 tok/s (single DGX Spark)
 DeepSeek V4 Flash decode comparison
 Measured decode throughput for one request at a time on the full 284B model System Tested configuration Decode throughput
 Lucebox ROCmFPX compressed model, DSpark draft model, four experts per token 51.1 tok/s median
 1× NVIDIA DGX Spark Q2 compressed model, average of tests at four context lengths 14.09 tok/s
 Measured ratio 51.1 ÷ 14.09 3.63×

 Using the unrounded DGX Spark mean of 14.0875 tok/s gives the 3.63× headline ratio. Each platform runs a configuration tuned for its own hardware, so this is a whole-system comparison rather than a GPU-only A/B test. Decode throughput is the rate at which each system generates new tokens.
 DeepSeek V4 Flash has 284 billion parameters. The 102.3 GB ROCmFPX build is too large for the R9700’s 32 GB of memory, so Lucebox gives the two AMD GPUs different jobs. The R9700 handles the dense path and frequently selected experts; Strix Halo holds the remaining experts in its 128 GB memory and runs them in parallel.
 The headline Lucebox result is the median of three measured requests after two warmups, using an approximately 2k-token prompt and 128 generated tokens. An 11.3 GB DSpark draft model proposes several tokens at once; the full DeepSeek V4 Flash model verifies them before they are accepted. We also ran a separate 53-token prompt to measure the upper end of the implementation.
 For the single-device baseline and the ROCmFPX compression details, see our companion report on DeepSeek V4 Flash on AMD Ryzen AI MAX+ 395 .
 Complete system price
 AMD-Powered Lucebox is priced at $6,499 as a complete local inference system, including the custom chassis, 2 TB of storage, power delivery, hardware integration, validation, and warranty. NVIDIA lists one DGX Spark at $4,699, or $9,398 for two.
 Complete system Current U.S. price What is included
 1× DGX Spark $4,699 Complete system with 4 TB storage
 AMD-Powered Lucebox $6,499 Custom chassis, 2 TB storage, power delivery, integration, validation, and warranty
 2× DGX Spark $9,398 Two complete systems

 At those list prices, Lucebox costs 38% more than one DGX Spark and delivers about 2.6× the decode throughput per dollar in the headline configurations. It costs 31% less than two DGX Sparks.
 Prices are the U.S. list prices available at publication, before tax and shipping. Sources: Lucebox system configuration and NVIDIA Marketplace . Configurations and prices can change.
 One DGX Spark, measured directly
 We ran a Q2 compressed version of the full DeepSeek V4 Flash model on one DGX Spark. We then measured Lucebox at the same 2k, 4k, 8k, and 16k context lengths.
 Matched single-request decode throughput on the full 284B model Context Lucebox 1× DGX Spark Speedup
 2k 51.0 tok/s 14.18 tok/s 3.60×
 4k 49.6 tok/s 14.24 tok/s 3.48×
 8k 47.5 tok/s 14.04 tok/s 3.38×
 16k 42.9 tok/s 13.89 tok/s 3.09×
 Mean 47.75 tok/s 14.09 tok/s 3.39×

 The DGX Spark mean is 14.0875 tok/s, which we report as 14.09 tok/s. Lucebox averages 47.75 tok/s across the same four context lengths, a 3.39× speedup. The 3.63× headline uses the separate 51.1 tok/s Lucebox serving result shown above.
 DGX Spark ran the Q2 model; Lucebox ran the ROCmFPX model with four experts per token and DSpark speculative decoding. Each system uses the configuration designed for its hardware.
 For wider context, LocalMaxxing includes two-DGX-Spark results both with the standard target and with a DSpark-specific package . We show both below rather than selecting the more favorable reference.
 DeepSeek V4 Flash decode, one request at a time · tok/s
 1× DGX Spark average of four tests


 14.09

 2× DGX Spark without a helper model


 45.70

 AMD-Powered Lucebox serving median


 51.10

 AMD-Powered Lucebox short prompt, fastest run


 55.00

 2× DGX Spark with DSpark


 65.09

 The Lucebox values are a three-request serving median and the fastest of three separate runs with a 53-token prompt. The single DGX Spark figure is our mean across 2k, 4k, 8k, and 16k context tests. Public sources: two DGX Sparks without a draft model and two DGX Sparks with DSpark . Prompts, context lengths, software, compression, and routing settings differ, so the public runs provide context r

 The public two-Spark results bracket Lucebox: the standard target is effectively tied with our longer decode run, while the DSpark-specific configuration is faster. They are useful reference points, but not substitutes for a matched benchmark.
 How the work is split
 Tensor parallelism usually divides the same calculation evenly between matching GPUs. That does not work well here because the R9700 and Strix Halo have different speeds and memory. An even split makes the R9700 wait. Splitting the model into whole layers is also slow because every token must pass through one device and then the other.
 DeepSeek V4 Flash is a mixture of experts model. Each layer contains 256 expert blocks, but only a small number are selected for each token. These tests use four. Lucebox stores each expert on one GPU. At every layer, both GPUs run the selected experts they hold, then the R9700 combines their results.
 One machine · two jobs
 Faster GPU
 Radeon AI PRO R9700
 32 GB local GDDR6
 Core layers used for every token
 Most frequently selected experts
 DSpark helper model
 Working cache and final token selection

 Larger memory
 Strix Halo Radeon 8060S
 128 GB shared LPDDR5X
 Remaining expert blocks
 Runs only experts selected for the current token
 Runs at the same time as the R9700
 No duplicate copy of the working cache


 At each layer: find the selected experts → run them on the GPU that stores them → combine the results on the R9700.
 The 32 GB and 128 GB memories are separate, not one shared 160 GB pool. Lucebox decides where every part of the model and its working state is stored.

 Expert ownership follows the hardware: frequently selected experts stay beside the dense path on the R9700, while the long tail lives in Strix Halo’s larger memory. One process submits both branches, copies the Strix Halo result directly to the R9700, and combines the outputs there. The R9700 remains the sole owner of the target cache and sampler.
 How the short test reached 55 tok/s
 The largest gain came from verifying four DSpark positions in one GPU operation. A generic safety rule had split some verification steps into groups of three and one, even though the DeepSeek V4 Flash path could handle all four together. Removing that split kept the verifier in one graph; transfer batching and expert grouping supplied the remaining gains.
 Effect of each change in the short test · tok/s
 Full model only


 30.1 to 30.4

 DSpark check 3, then 1


 37.50

 DSpark check all 4 together


 50.80

 Combine GPU transfers


 52.60

 Group Strix work by expert


 54.90

 The 37.50 and 50.80 tok/s tests accepted the same draft tokens. Checking all four positions together removed an unnecessary split. Combining GPU transfers reduced waiting between the GPUs. Grouping Strix Halo’s work by expert meant reading the same weights fewer times. All draft tokens were accepted in the final short run.

 The fused four-position verifier made the decisive jump. Batching the peer transfers reduced synchronization, and grouping Strix Halo routes by expert avoided rereading the same compressed weights. The final path also joins results and selects the next token on the GPU while reusing state already computed by DSpark.
 Test Setup: DeepSeek V4 Flash 284B, Asymmetric Expert Parallelism
 Asymmetric expert parallelism means the two GPUs are assigned different work rather than equal slices of every operation.
 Hardware
 R9700 + Strix Halo one machine

 Software
 ROCm 7.2.4 one process, two GPUs

 DSpark setting
 check 4 positions at once 4 experts per token

 Request mode
 one request at a time temperature 0 for repeatability

 Serving test
 ~2k prompt tokens 128 output tokens

 Serving median
 51.1 tok/s generation 415.52 tok/s prompt processing

 Matched context sweep
 2k · 4k · 8k · 16k 128 output tokens

 Sweep protocol
 2 warmups + 3 measured prompt caches disabled

 Short prompt test
 54.7 · 54.9 · 55.0 tok/s

 Time per DSpark step
 helper: 6.0 to 6.1 ms full model: 64.8 to 65.1 ms

 Longer decode test
 ~2k prompt tokens 510 output tokens

 Longer test median
 45.5 tok/s median 41.8 to 45.7 range


 The server reported exactly 2k, 4k, 8k, and 16k prompt tokens for the matched sweep. All measured requests generated the same 128-token response byte for byte, and the draft acceptance rate was 0.97. The 16k point was measured in a fresh process with the same binary and settings.
 The short-prompt result is a ceiling test: 53 prompt tokens, 128 generated tokens, and every DSpark proposal accepted. For a less favorable shape, five measured requests used an approximately 2k-token prompt and generated 510 tokens; decode ranged from 41.8 to 45.7 tok/s, with a 45.5 tok/s median. All five produced the same response byte for byte.
 The target was DeepSeek-V4-Flash-ROCMFP2-STRIX.gguf ; the draft was DeepSeek-V4-Flash-DSpark-draft-Q4RMFP4-denseF16.gguf . The build passed all 20 automated tests, including end-to-end coverage for regular and streamed DSpark requests.
 Benchmark scope. Throughput was measured with four routed experts per token. Repeated runs were deterministic; comparison with the six-expert reference configuration was outside the scope of this performance benchmark.
 Prompt processing: 415.52 tok/s with DSpark loaded
 Prompt processing, or prefill, is the work performed before the first generated token. With the 11.3 GB DSpark draft resident on the R9700, three measured requests after two warmups reached a 415.52 tok/s median , with a narrow 415.46–415.95 tok/s range.
 The progression below separates hardware placement from implementation changes. The initial two-GPU path joined both outputs on the CPU. The faster path leaves the R9700 output in device memory, copies only the Strix Halo partial, and completes the join on the R9700.
 Prompt processing for the same ~2k-token prompt · tok/s
 Strix Halo only baseline


 ~298

 Both GPUs CPU join


 353.69

 Both GPUs initial R9700 join, DSpark loaded


 368.76

 Both GPUs R9700 join, target only


 377.82

 Both GPUs optimized R9700 join, DSpark loaded


 415.52

 Every row uses the same approximately 2k-token prompt, four experts per token, and no prompt cache. The final value is the median of three measured requests with DSpark loaded. Earlier implementation runs generated more output tokens after prefill, but the prompt-processing input was unchanged.

 Moving the join off the CPU improved the target-only path by 6.8%. With DSpark loaded, the first R9700-join implementation was 23.7% faster than the Strix-only baseline; transfer and kernel work produced the final result shown above.
 This faster prompt processing path is optional. It changes the order of some calculations. This test also uses four experts per token instead of the model’s default six. Prompt processing and token generation are separate measurements, so their rates are not added together.
 Why heterogeneous hardware works here
 The architecture is the point. Strix Halo is an active expert engine, not overflow memory, while the R9700 keeps the latency-sensitive path. Sparse routing makes the uneven split practical: each processor contributes the bandwidth, capacity, and compute it has.
 Related
 DeepSeek V4 Flash: 284B model, up to 32 tok/s on Ryzen AI MAX+ 395
 Gemma 4 26B vs DeepSeek V4 Flash on ds4-eval-92
 DFlash + PFlash on AMD Strix Halo
 DeepSeek V4 Flash results on LocalMaxxing
 Lucebox source code
 Use both sides of the machine
 Lucebox is open source. The implementation, models, and benchmark details are public.
 GitHub Main model DSpark helper model Discord
```

---

### [14] Kimi K3 is Open, Opus 5 is Good, DeepSeek V4 Flash is Cheap: LLMs on Baba Is You

`quesma.com` · 2026-07-31 · Piotr Migdał, Piotr Grabowski · **benchmark**, own measurement · about V4: yes

<https://quesma.com/blog/baba-kimi-k3-opus-5/>

> Own BabaIsBench. Per-model pass@1/pass@3, turns, output tokens and total cost. V4 Flash 0731 75%/88% at $1.16; V4 Pro 29%/38% at $11.49.

Model surfaces matched: `deepseek v4 flash`, `deepseek v4 flash 0731`, `deepseek v4 pro`

Artifacts (3 kinds):

- `benchmark_number` — 0.1 (previously called Terminal-Bench; ARC-AGI-3
- `price` — $1.16; $10; $11.49; $11.91; $12.41; $12.56
- `version_string` — Claude Opus 4.8; Claude Opus 4.8 96; Claude Opus 5; Claude Opus 5 100; Claude Sonnet 5; Claude Sonnet 5 67

Benchmark figures, and whether a source is named within 300 chars:

- *bare* `ARC-AGI-3`
- *bare* `0.1 (previously called Terminal-Bench`

```text
Download PNG



 There are a few exciting model releases: Kimi K3 , Grok 4.5 , Gemini 3.6 Flash , Claude Opus 5 , and DeepSeek V4 Flash 0731 . It was a fruitful July!

 Since they all are reasonably high in the Artificial Analysis Intelligence Index , we re-ran these on our BabaIsBench , a benchmark in which agents play the lovely puzzle game Baba Is You , and which got mentioned by OpenAI when discussing their ARC-AGI-3 results .
While the game is already 7 years old, trajectories showed no signs of knowing the solution, a sharp contrast with SWE-bench Verified leaks .



 We do it in two rounds: first, three repetitions for the initial stage, the Intro , using the same Terminus-2 harness as in the original post.
Then we run these on the next stage, the Lake , with custom harnesses.

 Stage 0: The Intro

 Let’s start with the simplest one, to have a quick check of speed and cost. We pretty much assumed these models would solve most tasks. For clarity, we dimmed other rows, highlighting the new models.

 Download as PNG
 Model 00 baba is you 01 where do i go? 02 now what is this? 03 out of reach 04 still out of reach 05 volcano 06 off limits 07 grass yard pass@1 ↓ pass@3 ↓ Turns ↓ Output tokens ↓ Total cost ↑
 Claude Opus 5 100% 100% 7 23k $17.15
 GPT-5.5 100% 100% 8 15k $13.62
 Claude Fable 5 100% 100% 6 29k $40.98
 GPT-5.6 Sol 100% 100% 11 10k $11.91
 Kimi K3 96% 100% 9 29k $12.56
 Claude Opus 4.8 96% 100% 35 46k $63.14
 GLM-5.2 96% 100% 12 75k $6.20
 Gemini 3.1 Pro 92% 100% 8 38k $12.41
 Gemini 3.6 Flash 88% 100% 92 82k $124.31
 Gemini 3.5 Flash 88% 100% 111 74k $98.31
 GPT-5.6 Terra 88% 100% 41 55k $34.28
 Grok 4.5 75% 88% 86 68k $50.66
 DeepSeek V4 Flash 0731 75% 88% 22 156k $1.16
 Claude Sonnet 5 67% 88% 22 151k $42.21
 GPT-5.6 Luna 63% 88% 118 129k $59.32
 Hy3 54% 75% 25 76k $3.23
 MiniMax M3 46% 63% 96 173k $34.43
 Qwen3.6 27B 29% 38% 24 82k $5.59
 DeepSeek V4 Pro 29% 38% 37 183k $11.49
 Qwen3.7 Max 25% 38% 21 132k $16.98

 pass time agent steps moves solved timeout wrong answer not solved


 Claude Opus 5 solved all attempts, and is more than twice as cheap as Fable 5 (yet, still almost 3x as expensive as GLM-5.2). Kimi K3 was cheaper than Opus, with almost the same pass rate.

 Gemini 3.6 Flash… We expected it to be more cost-effective than its ridiculously expensive predecessor, Gemini 3.5 Flash. It is slightly better, yet even more expensive.

 Grok 4.5 is neither cheap nor efficient, and it even failed at one level.

 And the new update of DeepSeek V4 Flash 0731 is a wonder. While it does not beat all intro levels, it reaches the level of Sonnet 5, GPT-5.6 Luna and Grok 4.5 at roughly 1/40 of their cost! A true cost-effective marvel, a Pareto frontier hero .

 Price per token is not the same as the total cost. Some models need many more turns. Here is a chart of agent turns and cost.

 Download as PNG
 Claude Opus 5 GPT-5.5 Claude Fable 5 GPT-5.6 Sol Kimi K3 Claude Opus 4.8 GLM-5.2 Gemini 3.1 Pro Gemini 3.6 Flash Gemini 3.5 Flash GPT-5.6 Terra Grok 4.5* DeepSeek V4 Flash 0731* Claude Sonnet 5* GPT-5.6 Luna*


 To say that the updated DeepSeek V4 Flash is slightly cheaper than other LLMs is an understatement!

 If you are interested in discussion of previous results, see the original post Baba Is Solved by Fable 5 and GPT-5.6 Sol, but at what cost? .

 Stage 1: The Lake

 Per our methodology, we advanced the models with 100% pass@3: Opus 5, Kimi K3, and Gemini 3.6 Flash.
As in our Baba Is Solved by Fable 5 and GPT-5.6 Sol, but at what cost? , we run all levels just once, to keep costs reasonable.

 For each model, we chose their native harness: Claude Code for Opus 5, kimi-cli for Kimi K3, and… well, with Gemini, as previously, there were issues.

 Struggling with Gemini

 First I tried Antigravity CLI, but, as we already knew, it is incompatible with OpenRouter, which we use to evaluate all other models. Then I (PM) used my Gemini subscription, but it ate it in no time. Then I charged my personal Google account… just to discover that sometimes it is quick (because it web-searches) and other times it goes in loops. Finally I ran it with a standard Terminus-2 harnes

 Like its predecessor, Gemini 3.6 Flash is fast (135 tokens per second), but this also means it spends your dollars extremely quickly. On levels it couldn’t solve, it looped without making progress, made thousands of tool calls (1870 in the case of one level) and in one case consumed over 500k tokens of context window.

 At peak, the run consumed $7 per minute (extrapolated: over $400 per hour) by aimlessly looping on 9 levels it couldn’t solve. After $260, I (PG) gave this reckless driver a speeding ticket and stopped it before it did more harm to my wallet.

 Speed

 Download as PNG
 Claude Opus 5 Kimi K3 Gemini 3.6 Flash GPT-5.6 Sol GPT-5.5 Claude Fable 5 Claude Opus 4.8 GLM-5.2 Gemini 3.1 Pro Gemini 3.5 Flash


 Measuring against the wall clock, Opus 5 was slower than Fable 5, and Kimi K3 slower than the previous post’s GLM-5.2.
One caveat: we tested Kimi K3 right after release, when API quotas were throttling it. Who knows, it may be faster now.

 Cost

 Download as PNG
 Claude Opus 5 Kimi K3 Gemini 3.6 Flash GPT-5.6 Sol GPT-5.5 Claude Fable 5 Claude Opus 4.8 GLM-5.2 Gemini 3.1 Pro Gemini 3.5 Flash

 Cost is where it gets interesting.
Opus 5 is between the cheaper GPT-5.6 Sol and the more expensive Fable 5, except for the two hardest tasks, for which it is costlier than Fable 5.
So unless you are after the hardest tasks, Opus 5 might be the way to go.

 Kimi K3 falls between Opus 4.8 and GPT-5.5, which is rather expensive.
So, open weights do not mean free or even cheap: compute to run it is a non-trivial cost.

 Gemini 3.6 Flash performs the worst amongst the tested models, and that doesn’t even count the over $260 it spent trying to solve the remainder of the levels. While on this chart it is just $10 of total spend, it does not account for all the loops on unfinished tasks.

 Conclusion

 Claude Opus 5 delivers — almost as good as Fable 5, yet cheaper.
Kimi K3 is clearly a good model, and it is a true miracle that it is now open-weight on Hugging Face .

 Grok 4.5 does not generalize: good on official benchmarks, but when doing something slightly different, its score plummets. It is hard to tell whether it is benchmaxxing or just focused on a narrow set of skills.

 Gemini fell off. While the releases of Gemini 2.5, 3 and 3.1 were true landmarks, the newest ones do not deliver — not in raw skill, pricing, or tooling. We loved Gemini models for thinking, so we hope they will rebound.

 On another note, the community needs a better neutral harness for benchmarks than Terminus-2. We also tested the Pi and OpenCode harnesses, but these were even less efficient. Maybe there is a reason why Frontier-Bench v0.1 (previously called Terminal-Bench 3) lists native harnesses.

 Results from this post and the original run are collected on the BabaIsBench page .

 And what is your take on the frontier July 2026 models?

 Discuss on LinkedIn , X , Hacker News or Reddit .
```

---

### [15] A lesson about retries, hidden in the DeepSeek-V4 paper

`quesma.com` · 2026-07-31 · Piotr Grabowski · **first-hand analysis**, own experiment TESTING a vendor claim · about V4: yes

<https://quesma.com/blog/hidden-lesson-deepseek-paper/>

> Quotes the V4 paper verbatim on retry length bias, then runs 100,000 generations ($6.06) to check it. The good shape: vendor claim tested, not restated.

Model surfaces matched: `deepseek-v4`, `deepseek-v4-flash`

Artifacts (2 kinds):

- `price` — $6.06
- `version_string` — DeepSeek-V4-Flash

```text
Download PNG



 The DeepSeek-V4 paper contains an unexpected lesson for anyone running LLM benchmarks: sometimes it’s not correct to retry failures.

 So I decided to check it myself. 100,000 AI poems later, here’s what I found.

 DeepSeek’s warning

 Here’s the paragraph from the DeepSeek-V4 paper that made me curious:

 Importantly, it is mathematically incorrect to regenerate unfinished requests from scratch, as this introduces
length bias . Because shorter responses are more likely to survive interruption, regenerating from scratch makes the
model more prone to producing shorter sequences whenever an interruption occurs.

 From DeepSeek-V4 paper
 Adding retries is an obvious way to fix issues with reliability. But as DeepSeek noticed, longer requests have a higher chance of being interrupted. When you retry a failed long request, there’s a chance you’ll get a short response as a replacement.

 Retries make AI poems shorter

 Experiment

 Since statistical biases can often be hard to grasp, let’s see how this affects a real run.

 I asked DeepSeek-V4-Flash to generate 100,000 poems, haikus, or other literary works for me:


 Write a complete piece of literature in one randomly chosen form: a one-line poem, a haiku, a novel chapter, or a limerick.

 It cost me $6.06 (V4-Flash is cheap!) and generated a large variety of responses:



 On average it generated a 74-word text, but the results varied widely:


 73.2% haikus . Very short: 15 words on average.

 11.5% novel chapters . 34 times longer: 503 words on average.


 Simulating failures

 Now let’s simulate what would happen if the LLM inference were really unreliable and 10% of requests failed by being interrupted randomly during generation.

 I used a statistical model called a Poisson process to model this behavior; an average time between interruptions of 31 seconds makes 10% of requests fail in my experiment.

 As the DeepSeek paper noted, longer requests are affected more often. You can use this formula for a Poisson process to calculate it:

 P ( failure during request ) = 1 − e − request time / mean time between interruptions P(\text{failure during request}) = 1 - e^{-\text{request time}/\text{mean time between interruptions}} P ( failure during request ) = 1 − e − request time / mean time between interruptions
 For example, haikus take 2.38 seconds on average to generate, so their failure rate is 1 − e − 2.38 / 31 ≈ 7.4 % 1 - e^{-2.38/31} \approx 7.4\% 1 − e − 2.38/31 ≈ 7.4% . But novel chapters are longer (11.52 seconds), so their failure rate is higher: 1 − e − 11.52 / 31 ≈ 31.0 % 1 - e^{-11.52/31} \approx 31.0\% 1 − e − 11.52/31 ≈ 31.0% .

 You can see how the failure rate rises for longer requests:



 Adding retries

 So let’s see what would happen if I added retries. I artificially simulate failures and perform retries on the failed requests until they succeed.

 After running the simulation, the resulting dataset looks noticeably different! Just as the DeepSeek authors warned us:

 Without failures Failures + retries Change
 Average word count 73.51 59.40 −19.2%
 Responses ≥ 600 words 2,904 1,961 −32.5%
 Novel chapters 11,499 8,919 −22.4%


 The average response is now noticeably shorter and there are fewer longer-form responses. To better understand why it changed so much, let’s take a look at the requests that failed and what happened when they were retried:


 After retries, (would-be) long responses often become shorter responses. The right-hand side of the chart gets affected the most.

 Looking at it with a statistics toolset, adding retries changed the final distribution of the data. What we’re seeing here is a form of selection bias : the retried sample was not representative - long responses were overrepresented in it. Survivorship bias is also a good perspective: the final dataset includes only responses that survived some filtering process - in this case, interruptions that

 Conclusion

 Shorter poems might sound innocent, but the same problem could be dangerous in a real benchmark. A longer request might be stuck in an endless reasoning loop or headed down the wrong path, and retrying it might give the model a second chance - raising the score.

 Armed with that knowledge, we have 3 ways to deal with the issue:


 The DeepSeek authors architected their system to resume interrupted requests rather than regenerate them from scratch.

 Failures that happen truly randomly (independently of request length) can be safely retried.

 This problem can be important for benchmarks or research, but for most consumer-facing applications the difference doesn’t really matter.


 What started as a curious warning in the DeepSeek-V4 paper became a surprisingly intuitive lesson in statistics for me.
```

---

### [16] Gemini 3.7 Flash, Grok 4.6, GLM-5.3 and DeepSeek V4 Pro joined the frontier

`quesma.com` · 2026-08-20 · Piotr Migdał · **benchmark**, own measurement · about V4: yes

<https://quesma.com/blog/baba-is-aug-2026/>

> Both benchmark figures carry a source. V4 Pro 0813 added to the same table.

Model surfaces matched: `deepseek v4 flash`, `deepseek v4 flash 0731`, `deepseek v4 pro`, `deepseek v4 pro 0813`

Artifacts (3 kinds):

- `benchmark_number` — ARC-AGI-3; Terminal-Bench v2.1,
- `price` — $1.16; $10.75; $102.08; $107.76; $11.49; $11.91
- `version_string` — Claude Opus 4.8; Claude Opus 4.8 96; Claude Opus 5; Claude Opus 5 100; Claude Sonnet 5; Claude Sonnet 5 67

Benchmark figures, and whether a source is named within 300 chars:

- **cited** `Terminal-Bench v2.1,`
- **cited** `ARC-AGI-3`

```text
Download PNG



 This mid August is as hot as July when it comes to LLM releases: Grok 4.6 , Gemini 3.7 Flash , DeepSeek V4 Pro 0813 as well as open-weight models: Qwen3.8 Max , Qwen3.8 27B , and GLM-5.3 .

 Intelligence Index vs. Cost per Intelligence Index Task
from Artificial Analysis . Note that it is based on score of benchmarks like
Terminal-Bench v2.1, SciCode, Humanity’s Last Exam, GPQA Diamond - not necessarily fluid intelligence like in abstract
puzzle games of ARC-AGI-3 or Baba is You.

 Since these models are smart, I decided to rerun the Baba Is Bench , to see how the models fare on a puzzle game. Even though the game is popular, we check for spoilers - and to our surprise, there are no signs of models knowing solutions ahead - unlike in SWE-bench Verified .

 Results are stunning for Grok, Gemini Flash or DeepSeek. Don’t get deceived by minor version changes - they all give qualitatively different results! For both GLM and Qwen the progress was more gradual.

 As previously, we do it in two rounds. First, asking to play the initial stage the Intro , then for those who pass at least 7/8 levels, also the next one the Lake .

 Stage 0: The Intro

 We show the models we analyze, against dimmed previous ones.

 Download as PNG
 Model 00 baba is you 01 where do i go? 02 now what is this? 03 out of reach 04 still out of reach 05 volcano 06 off limits 07 grass yard pass@1 ↓ pass@3 ↓ Turns ↓ Output tokens ↓ Total cost ↑
 Gemini 3.7 Flash 100% 100% 53 22k $5.38
 Claude Opus 5 100% 100% 7 23k $17.15
 GPT-5.5 100% 100% 8 15k $13.62
 Claude Fable 5 100% 100% 6 29k $40.98
 GPT-5.6 Sol 100% 100% 11 10k $11.91
 Grok 4.6 96% 100% 25 52k $14.01
 GLM-5.3 96% 100% 13 47k $6.20
 Kimi K3 96% 100% 9 29k $12.56
 Claude Opus 4.8 96% 100% 35 46k $63.14
 GLM-5.2 96% 100% 12 75k $6.20
 Gemini 3.1 Pro 92% 100% 8 38k $12.41
 Gemini 3.6 Flash 88% 100% 92 82k $124.31
 GPT-5.6 Terra 88% 100% 41 55k $34.28
 DeepSeek V4 Pro 0813 75% 88% 18 130k $2.94
 DeepSeek V4 Flash 75% 100% 55 190k $2.82
 Grok 4.5 75% 88% 86 68k $50.66
 DeepSeek V4 Flash 0731 75% 88% 22 156k $1.16
 Claude Sonnet 5 67% 88% 22 151k $42.21
 GPT-5.6 Luna 63% 88% 118 129k $59.32
 Qwen3.8 Max 58% 75% 9 66k $10.75
 Qwen3.6 27B 29% 38% 24 82k $5.59
 DeepSeek V4 Pro 29% 38% 37 183k $11.49
 Qwen3.7 Max 25% 38% 21 132k $16.98
 Qwen3.8 27B 21% 38% 9 134k $9.07

 pass time agent steps moves solved timeout wrong answer not solved


 The results are nothing short of stunning, as both results went up and prices went down significantly.


 Gemini 3.7 Flash now solves every trial, and is over 20x cheaper than its predecessor, Gemini 3.6 Flash.

 Grok 4.6 solved all but one attempt (vs Grok 4.5 that missed 6 attempts and one level), while being over 3x cheaper.

 DeepSeek V4 Pro 0813 solved 7/8 levels vs its previous version that solved only 3/8 - and while being 4x cheaper.


 Download as PNG
 Gemini 3.6 Flash Gemini 3.7 Flash Grok 4.5 Grok 4.6 DeepSeek V4 Pro DeepSeek V4 Pro 0813 DeepSeek V4 Flash 0731 GLM-5.3


 With the GLM and Qwen family there is less success:


 GLM-5.3 got exactly the same result as GLM-5.2.

 Qwen3.8 Max is better than Qwen3.7 Max (way more attempts solved), but still far from completing all levels.

 Qwen3.8 27B has worse results than Qwen3.6 27B - though, all within experimental noise.


 I was surprised that it didn’t do better. Especially as Qwen3.8 27B scores 52 on Artificial Analysis . From what I’ve seen in the transcripts, it tried to solve in one go, without actually exploring the board. It matches Simon Willison’s experience that Qwen3.8 27B defaults to wildly overthinking things . While Baba Is You clearly needs thinking, it is a balance of thinking and testing. Compare a

 Download as PNG
 Gemini 3.7 Flash Claude Opus 5 GPT-5.5 Claude Fable 5 GPT-5.6 Sol Grok 4.6 GLM-5.3 Kimi K3 Claude Opus 4.8 GLM-5.2 Gemini 3.1 Pro Gemini 3.6 Flash GPT-5.6 Terra DeepSeek V4 Pro 0813* DeepSeek V4 Flash Grok 4.5* DeepSeek V4 Flash 0731* Claude Sonnet 5* GPT-5.6 Luna*


 It is interesting to look at the chart of agent turns and price. Grok and Gemini Flash moved from trigger-happy models, to more moderate ones, resulting in a significantly reduced cost.

 Stage 1: The Lake

 For models that passed at least 7 out of 8 intro levels, we run them on the next stage, the Lake .
Only one attempt per level, as it is costly. Or at least - it used to be costly with the previous models, as now it is getting significantly better.

 Model Harness Solved Total time Output tokens Total cost
 Claude Fable 5 Claude Code 14 2h 36m 10.7M $53.25
 Claude Opus 5 Claude Code 14 6h 46m 16.3M $61.96
 Gemini 3.7 Flash Terminus-2 14 9h 11m 1023.1M $55.76
 GPT-5.6 Sol Codex 14 9h 16m 16.4M $31.42
 GPT-5.5 Codex 13 8h 57m 50.1M $102.08
 Grok 4.6 Terminus-2 13 20h 16m 38.6M $46.20
 DeepSeek V4 Pro 0813 Claude Code 13 22h 7m 75.6M $8.48
 Claude Opus 4.8 Claude Code 12 9h 7m 49.9M $107.76
 GLM-5.3 Terminus-2 12 24h 57m 9.6M $16.85
 GLM-5.2 Claude Code 11 23h 41m 62.9M $37.51
 Kimi K3 kimi-cli 11 29h 34m 129.5M $78.15
 Gemini 3.1 Pro Terminus-2 8 5h 58m 41.8M $58.17
 Gemini 3.6 Flash Terminus-2 6 7h 46m 1118.1M $269.48
 DeepSeek V4 Flash 0731 Claude Code 6 24h 11m 92.8M $4.31

 solved stopped failed

 Time

 First, let’s look at the wall time, for models run via APIs.
While it might change with providers, or model bandwidth at a given time, it gives a ballpark estimate of effective model speed. In everyday software engineering it is what we care for, anyway.

 Download as PNG
 Gemini 3.7 Flash Grok 4.6 DeepSeek V4 Pro 0813 DeepSeek V4 Flash 0731 Claude Opus 5 Kimi K3 Gemini 3.6 Flash GPT-5.6 Sol GPT-5.5 Claude Fable 5 Claude Opus 4.8 GLM-5.2 GLM-5.3 Gemini 3.1 Pro


 And wow, Gemini 3.7 Flash is fast - not only per token (which is widely cited but largely irrelevant), but per problem solved. Here, for most levels, only Claude Fable 5 is faster.

 Grok 4.6, while 2x slower than GPT-5.6 Sol, still manages to solve 13 of 15 levels (GPT-5.6 Sol solves 14). It’s a promotion to the league of top models.

 DeepSeek V4 Pro 0813 might be the slowest of the top models - but it is the first open-weight model that finally reached the same top league. It is way beyond GLM-5.2 or Kimi K3 results.

 GLM-5.3 was almost the same as GLM-5.2, to the point that two lines overlap; though, it solved one more level.

 Cost

 Now let’s look at costs. It’s beautiful.

 Download as PNG
 Gemini 3.7 Flash Grok 4.6 DeepSeek V4 Pro 0813 DeepSeek V4 Flash 0731 Claude Opus 5 Kimi K3 Gemini 3.6 Flash GPT-5.6 Sol GPT-5.5 Claude Fable 5 Claude Opus 4.8 GLM-5.2 GLM-5.3 Gemini 3.1 Pro

 Grok 4.6 is cheaper than Fable 5, but more expensive than GPT-5.6 Sol or Opus 5.

 While Gemini 3.6 Flash was ridiculously expensive , Gemini 3.7 Flash is one of the cheapest models. At 12 levels, it is twice as cheap as GPT-5.6 Sol, the previous cheapest model. At 13 tasks it is still twice as cheap. Only vs DeepSeek Pro is it slightly more expensive.

 What happens with DeepSeek V4 Pro 0813 is a pure wonder. Not only is it open-weight, but also the cheapest of all.

 GLM-5.3 was 2x cheaper than its predecessor.

 Some lessons about harnesses

 In previous experiments we used various harnesses. Here we used Harbor -default Terminus-2, except DeepSeek, which we ran on Claude Code. While there are Grok Build and DeepSeek Harness , results were slightly worse (Grok) or vastly inferior (DeepSeek). That said, these are newer tools, and likely to get improved in the future. If there is interest, we’re happy to share more insight on running wi

 Conclusion

 Progress is fast - with more players joining the frontier game, and open-weight models reaching frontier-level results at a much lower price. And I am looking forward to seeing more models in the coming months. And to the first local model solving the Lake.

 As my colleague Piotr Grabowski noticed:


 “Second-tier labs caught up with the frontier” matches my experience: last few days I’ve been using Grok 4.6 or GLM-5.3 for easy/medium difficulty tasks and couldn’t see major difference between them and Opus 5/GPT-5.6 Sol (for harder tasks yes, there’s still gap).

 And what is your experience?
```

---

### [18] Head to Head: Muse Spark 1.1 vs. DeepSeek-V4-Pro

`runtimewire.com` · 2026-07-10 · RuntimeWire · **benchmark**, automated LLM-judge matchup, no human author · about V4: yes

<https://runtimewire.com/article/head-to-head-muse-spark-1-1-vs-deepseek-v4-pro>

> 110.8-84.3 and '100% confidence, decisive' - a statistical claim naming no test. Says V4-Pro loses 11-1 on instruction-following and compliance, the capability the June post says it WINS on.

Model surfaces matched: `deepseek-v4-pro`

Artifacts (2 kinds):

- `price` — $248.19
- `version_string` — DeepSeek-V4-Pro

````text
RuntimeWire Head-to-Head matchup

 This wasn’t a competitive split decision; it was a rout driven by instruction-following, robustness, and cleaner execution across a wide mix of real tasks. Muse Spark 1.1 consistently delivered answers that were tighter, more compliant, and less error-prone than DeepSeek-V4-Pro.

 Muse Spark 1.1 wins this matchup outright. The aggregate score gap is massive — **110.8 to 84.3** — and the statistical verdict is as strong as it gets: **100% confidence, decisive**. Just as telling, the task count wasn’t close either: **11 wins for Muse Spark 1.1, 1 for DeepSeek-V4-Pro, no ties**.

What stands out is *how* Muse Spark 1.1 won. It wasn’t just better at one niche; it was more dependable across localization, proofreading, JSON extraction, SQL, constrained writing, faithful rewriting, and code repair. In practical terms, Muse Spark 1.1 kept doing the unglamorous but essential things right: preserving exact wording when asked, returning raw JSON instead of fenced output, respectin

DeepSeek-V4-Pro’s problem here is not total incompetence; it’s sloppiness under pressure. Again and again, it lost on avoidable compliance failures: markdown fences where raw JSON was required, unnecessary wording changes in proofreading, extra reasoning where strict output format mattered, and less robust code paths in bug-fix tasks. Its lone win — unit-aware math — came on presentation, not on s

There were a few order-swapped judge passes that flipped individual task rationales, which suggests some prompts were close at the margin. But zoom out and the overall picture does not change. When one model posts an **11–1** task record and a decisive score lead, the editorial conclusion is simple: Muse Spark 1.1 was the more reliable system, the more disciplined instruction-follower, and the bet

**Final call: Muse Spark 1.1 is the clear winner, and DeepSeek-V4-Pro never seriously threatens it.**


 Localization with tone

 Translate this app onboarding line into natural, friendly European Spanish suitable for a mobile toast (keep it under 60 characters, no exclamation marks): "You're all set — your first backup starts tonight." Return only the translation, then the character count in parentheses.

 Muse Spark 1.1: Todo listo, tu primera copia empieza esta noche (47)

 DeepSeek-V4-Pro: Todo listo, tu primera copia se hará esta noche (54)

 A is more natural and concise for a mobile toast while preserving the meaning and staying under the character limit. B is also acceptable, but "se hará" sounds less idiomatic here than "empieza" for a backup starting tonight. (Order-swapped judge pass: Both are under 60 characters and follow the format, but B sounds more natural and closer in meaning to 'starts tonight' for an onboarding toast. A



 Precise proofreading

 Correct ONLY the grammar, spelling, and punctuation errors in the sentence below without changing wording, tone, or meaning, then on a second line list each change as 'was -> now'. Sentence: "Its been a long time since we seen there new office, and me and him was suprised how quite it was."

 Muse Spark 1.1: It's been a long time since we saw their new office, and me and him were surprised how quiet it was.
Its -> It's, seen -> saw, there -> their, was -> were, suprised -> surprised, quite -> quiet

 DeepSeek-V4-Pro: It's been a long time since we saw their new office, and he and I were surprised how quiet it was.

Its -> It's
seen -> saw
there -> their
me and him -> he and I
was -> were
suprised -> surprised
quite -> quiet

 Model A fixes the grammar, spelling, and punctuation errors while preserving the original wording more closely. Model B makes an unnecessary wording change ('me and him' to 'he and I'), which violates the instruction to avoid changing wording beyond error correction. (Order-swapped judge pass: Model B better follows the instruction to correct only grammar, spelling, and punctuation without changi



 Concurrency bug fix

 This TypeScript function is meant to memoize an async loader but has a race: concurrent callers can each trigger the underlying fetch. Fix it so the fetch runs at most once per key, and a rejected fetch does NOT poison the cache (a later call must retry). Return ONLY the corrected function.

```ts
const cache = new Map<string, Promise<string>>();
async function load(key: string, fetcher: (k: string) => Promise<string>) {
 if (cache.has(key)) return cache.get(key)!;
 const value = await fetcher(key);
 cache.set(key, Promise.resolve(value));
 return value;
}
```

 Muse Spark 1.1: ```ts
async function load(key: string, fetcher: (k: string) => Promise<string>) {
 if (cache.has(key)) return cache.get(key)!;
 const promise = fetcher(key);
 cache.set(key, promise);
 try {
 return await promise;
 } catch (err) {
 if (cache.get(key) === promise) cache.delete(key);
 throw err;
 }
}
```

 DeepSeek-V4-Pro: ```ts
const cache = new Map<string, Promise<string>>();

async function load(key: string, fetcher: (k: string) => Promise<string>) {
 if (cache.has(key)) return cache.get(key)!;

 const promise = fetcher(key);
 cache.set(key, promise);

 try {
 const value = await promise;
 return value;
 } catch (error) {
 cache.delete(key);
 throw error;
 }
}
```

 Model A correctly memoizes the in-flight promise and safely removes it only if it is still the cached entry, avoiding accidental deletion if the cache changed meanwhile. Model B fixes the main race but unnecessarily redefines the cache and can delete a newer promise on rejection, making it less robust and less compliant with the instruction to return only the corrected function. (Order-swapped ju



 extract_clinic_intake

 Extract structured facts from this clinic intake note. Return only valid JSON with keys: patient_name, dob, phone_numbers, medications, allergies, emergency_contact, appointment_date, insurance_member_id. phone_numbers must be an array of all phone numbers mentioned in the note in the order they appear. medications must be an array of objects with keys name, dose, frequency. emergency_contact mus

Note:
"New patient intake — Miri Talasek (DOB 1989-11-04). Best callback is 415.555.0188; if unreachable, try work line 415-555-0199 x204. Current meds: sertraline 50 mg daily, albuterol inhaler 2 puffs as needed, vitamin D3 1000 IU daily. Allergies: penicillin; hazelnuts. Emergency contact: Ivo Talasek, brother, 415-555-0114. Scheduled for 2025/08/16. Insurance card says member ID QF-229-771-AB."

 Muse Spark 1.1: {
 "patient_name": "Miri Talasek",
 "dob": "1989-11-04",
 "phone_numbers": ["415.555.0188", "415-555-0199 x204", "415-555-0114"],
 "medications": [
 {"name": "sertraline", "dose": "50 mg", "frequency": "daily"},
 {"name": "albuterol inhaler", "dose": "2 puffs", "frequency": "as needed"},
 {"name": "vitamin D3", "dose": "1000 IU", "frequency": "daily"}
 ],
 "allergies": ["penicillin", "hazelnuts"],
 "emergency_contact": {"name": "Ivo Talasek", "relation": "brother", "phone": "415-555-0114"},
 "appointment_date": "2025/08/16",
 "insurance_member_id": "QF-229-771-AB"
}

 DeepSeek-V4-Pro: ```json
{
 "patient_name": "Miri Talasek",
 "dob": "1989-11-04",
 "phone_numbers": [
 "415.555.0188",
 "415-555-0199"
 ],
 "medications": [
 {
 "name": "sertraline",
 "dose": "50 mg",
 "frequency": "daily"
 },
 {
 "name": "albuterol inhaler",
 "dose": "2 puffs",
 "frequency": "as needed"
 },
 {
 "name": "vitamin D3",
 "dose": "1000 IU",
 "frequency": "daily"
 }
 ],
 "allergies": [
 "penicillin",
 "hazelnuts"
 ],
 "emergency_contact": {
 "name": "Ivo Talasek",
 "relation": "brother",
 "phone": "415-555-0114"
 },
 "appointment_date": "2025/08/16",
 "insurance_member_id": "QF-229-771-AB"
}
```

 Model A correctly includes all phone numbers in order, including the work line extension and the emergency contact number, and returns valid JSON only. Model B omits the extension and the third phone number, and it wraps the JSON in markdown fences, violating the output requirement. (Order-swapped judge pass: Model B is more complete and accurate because it includes all phone numbers mentioned in



 Constraint scheduling

 Four talks (A, B, C, D) fill four 1-hour slots 9,10,11,12. Constraints: A is before D; C is not first; B is immediately after A; D is not at 12. Give the ONE valid schedule as 'slot: talk' lines, then a one-line justification. If impossible, say so and explain.

 Muse Spark 1.1: 9: A
10: B
11: D
12: C
AB as a block can only start at 9, otherwise A cannot be before D without violating D not at 12 or C not first.

 DeepSeek-V4-Pro: Let’s work through the constraints step-by-step:

1. **A is before D** — so A must be earlier in the schedule than D.
2. **C is not first** — C cannot be at 9.
3. **B is immediately after A** — A and B must be consecutive, with A first.
4. **D is not at 12** — D cannot be in the last slot.

---

**Step 1:** A and B must be together as (A, B) in that order. Possible slot pairs for them:
- (9, 10)
- (10, 11)
- (11, 12)

**Step 2:** If they are at (11, 12), then D would have to be after A, which means D would be at 12 — but D cannot be at 12. So (11, 12) is impossible.

**Step 3:** If they are at (9, 10), then D must be after A, so D could be at 11 or 12 — but not 12, so D must be at 11.
Then C must take the remaining slot, which is 12. That’s allowed since C is not first.

**Step 4:** If they were at (10, 11), then D must be after A (10), so D at 11 or 12 — but B is at 11, so D would have to be at 12, which is forbidden. So (10, 11) is impossible.

---

Only (9, 10) for (A, B) works, with D at 11 and C at 12.

**Final schedule:**
```
9: A
10: B
11: D
12: C
```

**Justification:**
A before D, B immediately after A, C not first, D not at 12 — only placement that fits is A at 9, B at 10, D at 11, C at 12.

 Both models find the correct unique schedule, but Model A follows the requested output format exactly with slot lines followed by a one-line justification. Model B adds unnecessary step-by-step reasoning and extra formatting, so it is less compliant despite being correct and clear. (Order-swapped judge pass: Both models give the correct unique schedule, but Model B adheres exactly to the requeste



 constraint_heavy_status_note

 Write a project status note that follows ALL rules exactly:
- Exactly 3 bullet points
- Each bullet must start with "- "
- Total word count across all bullets: 33 to 39 words
- Mention these three items exactly once each: "Maple API", "invoice lag", "Tuesday"
- Include one percentage written as digits with a % sign
- Do not use the words: delay, issue, problem, blocker
- Final bullet must end with the word "steady"
- No bullet may contain more than 14 words

 Muse Spark 1.1: - Maple API integration successfully reached 90% completion milestone ahead of schedule yesterday
- Finance team identified invoice lag affecting reconciliation workflows requiring additional attention still
- Deployment review scheduled Tuesday maintaining momentum and confidence remaining absolutely steady

 DeepSeek-V4-Pro: - Maple API integration reached 92% feature completion and is on track for Tuesday demo readiness
- Invoice lag trend improved with processing time now under 4 hours following configuration changes
- Team velocity metrics remain strong and our deployment cadence is steady

 Model A satisfies all stated constraints, including exact mentions, word-count limits, and ending the final bullet with "steady." Model B violates multiple instructions: it uses "Invoice lag" instead of the exact lowercase phrase, exceeds the total word-count limit, and does not end the final bullet with the word "steady" exactly. (Order-swapped judge pass: Both outputs satisfy the structural con



 sql_subscription_retention

 You are given a PostgreSQL schema:
customers(customer_id INT PRIMARY KEY, name TEXT, region TEXT)
plans(plan_id INT PRIMARY KEY, plan_name TEXT, monthly_price NUMERIC)
subscriptions(subscription_id INT PRIMARY KEY, customer_id INT, plan_id INT, start_date DATE, end_date DATE)
payments(payment_id INT PRIMARY KEY, subscription_id INT, paid_at DATE, amount NUMERIC, status TEXT)
A subscription is considered active in a month if the month overlaps the inclusive date range from start_date to COALESCE(end_date, '9999-12-31'). Write ONE SQL query that returns, for each region, the retention rate from 2024-02 to 2024-03 among customers who had at least one active subscription in February 2024. Retention rate = retained_customers / feb_active_customers, where retained_customers

 Muse Spark 1.1: Active in a month = `start_date <= month_end AND COALESCE(end_date,'9999-12-31') >= month_start`:

```sql
WITH feb_customers AS (
 SELECT DISTINCT c.customer_id, c.region
 FROM customers c
 JOIN subscriptions s ON s.customer_id = c.customer_id
 WHERE s.start_date <= DATE '2024-02-29'
 AND COALESCE(s.end_date, DATE '9999-12-31') >= DATE '2024-02-01'
),
march_customers AS (
 SELECT DISTINCT s.customer_id
 FROM subscriptions s
 WHERE s.start_date <= DATE '2024-03-31'
 AND COALESCE(s.end_date, DATE '9999-12-31') >= DATE '2024-03-01'
)
SELECT
 f.region,
 COUNT(*) AS feb_active_customers,
 COUNT(m.customer_id) AS retained_customers,
 ROUND(COUNT(m.customer_id)::numeric / NULLIF(COUNT(*),0), 4) AS retention_rate
FROM feb_customers f
LEFT JOIN march_customers m USING (customer_id)
GROUP BY f.region
ORDER BY f.region;
```

This counts distinct customers per `region` active in Feb 2024, retains those also active in Mar 2024, and computes `retained / feb_active`.

 DeepSeek-V4-Pro: Here's the SQL query that calculates the retention rate by region from February to March 2024:

```sql
WITH feb_active AS (
 SELECT DISTINCT
 c.customer_id,
 c.region
 FROM customers c
 JOIN subscriptions s ON c.customer_id = s.customer_id
 WHERE s.start_date <= '2024-02-29'
 AND COALESCE(s.end_date, '9999-12-31') >= '2024-02-01'
),
mar_active AS (
 SELECT DISTINCT
 c.customer_id,
 c.region
 FROM customers c
 JOIN subscriptions s ON c.customer_id = s.customer_id
 WHERE s.start_date <= '2024-03-31'
 AND COALESCE(s.end_date, '9999-12-31') >= '2024-03-01'
),
feb_counts AS (
 SELECT
 region,
 COUNT(DISTINCT customer_id) AS feb_active_customers
 FROM feb_active
 GROUP BY region
),
retention AS (
 SELECT
 fa.region,
 fa.customer_id
 FROM feb_active fa
 JOIN mar_active ma ON fa.customer_id = ma.customer_id AND fa.region = ma.region
)
SELECT
 fc.region,
 fc.feb_active_customers,
 COUNT(DISTINCT r.customer_id) AS retained_customers,
 ROUND(
 COUNT(DISTINCT r.customer_id)::NUMERIC / fc.feb_active_customers,
 4
 ) AS retention_rate
FROM feb_counts fc
LEFT JOIN retention r ON fc.region = r.region
GROUP BY fc.region, fc.feb_active_customers
ORDER BY fc.region;
```

This query works by:

1. **feb_active**: Identifies customers active in February 2024 (where subscription covers any day in February)
2. **mar_active**: Identifies customers active in March 2024 (where subscription covers any day in March)
3. **feb_counts**: Counts distinct customers per region who were active in February
4. **retention**: Finds customers who appear in both February and March active lists
5. **Final SELECT**: Joins the February counts with retention counts to calculate the retention rate per region, rounded to 4 decimal places

The date overlap logic checks if the subscription period [start_date, COALESCE(end_date, '9999-12-31')] overlaps with the entire month in question.

 Model A is fully correct and concise: it correctly identifies February-active customers, checks March activity for the same customers, and computes per-region retention. Model B is also mostly correct, but its retention CTE unnecessarily joins on region as well as customer_id, which could undercount if a customer's region changed or data were inconsistent, making it slightly less robust. (Order-s



 Faithful rewrite

 Rewrite this blunt internal note as a warm, professional Slack message to the whole engineering team (60–90 words), keeping every fact intact and adding no new commitments. Return only the message.
Note: "Deploy is frozen until the memory leak in the image service is fixed. Priya is on it. Do not merge to main. ETA tomorrow noon."

 Muse Spark 1.1: Hello everyone, a quick friendly update: deploys are frozen until the memory leak in the image service is fixed. Priya is on it. To avoid any conflicts, please do not merge to main for now. The current ETA for the fix is tomorrow noon. Thank you so much for your understanding and for helping us keep things smooth while we get this resolved.

 DeepSeek-V4-Pro: Hey team! Just a heads-up that we're holding deployments for now while we resolve a memory leak in the image service. Priya's already on it. In the meantime, please hold off on merging to main. We're aiming to have things sorted by noon tomorrow. Appreciate your patience and support while this gets fixed!

 A preserves all facts more faithfully, including the explicit deploy freeze and ETA wording, while staying warm and professional. B is polished but softens key directives and adds a slightly stronger implied commitment with "we're aiming to have things sorted". (Order-swapped judge pass: Model B preserves the original facts more faithfully, especially by keeping the deploy freeze and ETA wording 



 json_normalize_field_reports

 Convert the messy field notes below into valid JSON: an array of objects sorted by ticket_id ascending. Use exactly this schema for each object: {"ticket_id":string,"site":string,"priority":string,"status":string,"owner":string|null,"tags":string[],"eta_date":string|null}. Normalize priority to one of ["low","medium","high","urgent"]. Normalize status to one of ["open","in_progress","blocked","cl

Notes:
- T-104 | Site: Alder Pump House | prio=URGENT | state: in progress | owner Ana Méndez | tags water, valve / night | ETA 7/14/2025
- Ticket T-099 ; site=North Annex ; priority low ; status CLOSED ; owner none ; tags: audit / paperwork
- id T-117, site "Harbor-3", prio High, status blocked, owner: Ravi K., tags safety, crane, safety, ETA: 2025-07-09
- T-103 / site West Trench / priority medium / state open / owner Jo Lin / tags drainage

 Muse Spark 1.1: [
 {
 "ticket_id": "T-099",
 "site": "North Annex",
 "priority": "low",
 "status": "closed",
 "owner": null,
 "tags": ["audit", "paperwork"],
 "eta_date": null
 },
 {
 "ticket_id": "T-103",
 "site": "West Trench",
 "priority": "medium",
 "status": "open",
 "owner": "Jo Lin",
 "tags": ["drainage"],
 "eta_date": null
 },
 {
 "ticket_id": "T-104",
 "site": "Alder Pump House",
 "priority": "urgent",
 "status": "in_progress",
 "owner": "Ana Méndez",
 "tags": ["water", "valve", "night"],
 "eta_date": "2025-07-14"
 },
 {
 "ticket_id": "T-117",
 "site": "Harbor-3",
 "priority": "high",
 "status": "blocked",
 "owner": "Ravi K.",
 "tags": ["safety", "crane"],
 "eta_date": "2025-07-09"
 }
]

 DeepSeek-V4-Pro: ```json
[
 {
 "ticket_id": "T-099",
 "site": "North Annex",
 "priority": "low",
 "status": "closed",
 "owner": null,
 "tags": ["audit", "paperwork"],
 "eta_date": null
 },
 {
 "ticket_id": "T-103",
 "site": "West Trench",
 "priority": "medium",
 "status": "open",
 "owner": "Jo Lin",
 "tags": ["drainage"],
 "eta_date": null
 },
 {
 "ticket_id": "T-104",
 "site": "Alder Pump House",
 "priority": "urgent",
 "status": "in_progress",
 "owner": "Ana Méndez",
 "tags": ["water", "valve", "night"],
 "eta_date": "2025-07-14"
 },
 {
 "ticket_id": "T-117",
 "site": "Harbor-3",
 "priority": "high",
 "status": "blocked",
 "owner": "Ravi K.",
 "tags": ["safety", "crane"],
 "eta_date": "2025-07-09"
 }
]
```

 Both outputs correctly normalize and sort the records, but Model A better follows the requirement to return valid JSON only. Model B wraps the JSON in Markdown code fences, so the overall response is not itself a raw JSON array as requested. (Order-swapped judge pass: Both outputs are fully correct: they normalize fields properly, sort by ticket_id ascending, deduplicate tags while preserving ord



 Unit-aware math

 A pump moves 3.5 liters every 8 seconds. A tank holds 0.9 cubic meters. Starting empty, how long to fill it, in minutes and seconds (mm:ss), rounded to the nearest second? Show the key steps, then give the final answer on its own line.

 Muse Spark 1.1: Convert to common units:
1 m³ = 1000 L, so 0.9 m³ = 0.9 × 1000 = 900 L

Flow rate:
3.5 L / 8 s = 0.4375 L/s

Total time in seconds:
Time = Volume / Rate = 900 / 0.4375 = 14400 / 7 ≈ 2057.142857 s

Convert to mm:ss:
2057.142857 / 60 = 34 min remainder 2057.142857 - 34×60 = 17.142857 s
Rounded to nearest second = 17 s

34:17

 DeepSeek-V4-Pro: Let's break this down step by step.

---

**Step 1: Convert tank volume to liters**
1 cubic meter = 1,000 liters
\[
0.9 \, \text{m}^3 = 0.9 \times 1000 = 900 \, \text{liters}
\]

---

**Step 2: Find the pump's flow rate**
3.5 liters every 8 seconds:
\[
\text{Rate} = \frac{3.5}{8} = 0.4375 \, \text{liters per second}
\]

---

**Step 3: Time to fill 900 liters**
\[
\text{Time (seconds)} = \frac{900}{0.4375} = 2057.142857... \, \text{seconds}
\]

---

**Step 4: Convert to minutes and seconds**
Whole minutes:
\[
2057 \div 60 = 34 \, \text{minutes}, \, \text{remainder} = 2057 - (34 \times 60) = 17.142857...
\]
So:
\[
\text{Time} = 34 \, \text{minutes and } 17.14 \, \text{seconds}
\]
Rounded to the nearest second:
\[
34:17
\]

---

**Final answer:**
```
34:17
```

 Both outputs compute the correct result, but B is slightly better organized and more clearly presents the key steps and final answer on its own line. A is also correct, but B’s formatting and explanation are a bit cleaner. (Order-swapped judge pass: Both outputs are correct and follow the prompt, arriving at 34:17. Model A is slightly better because it presents the key steps more clearly and clea



 python_lru_cache_ttl

 Implement in Python a class TTLCache with methods __init__(capacity: int), get(key: str, now: int) -> int | None, and put(key: str, value: int, ttl: int, now: int) -> None. Each entry expires at now + ttl and must be treated as missing at or after its expiry time. When inserting and the cache is over capacity, evict the least recently used non-expired item; expired items should be discarded first

 Muse Spark 1.1: from collections import OrderedDict
from typing import Optional

class TTLCache:
 def __init__(self, capacity: int):
 self.capacity: int = capacity
 self.cache: OrderedDict[str, tuple[int, int]] = OrderedDict() # key -> (value, expiry)

 def get(self, key: str, now: int) -> int | None:
 if key not in self.cache:
 return None
 value, exp = self.cache[key]
 if now >= exp:
 del self.cache[key]
 return None
 self.cache.move_to_end(key)
 return value

 def put(self, key: str, value: int, ttl: int, now: int) -> None:
 if self.capacity <= 0:
 return

 exp = now + ttl
 if exp <= now:
 if key in self.cache:
 del self.cache[key]
 return

 if key in self.cache:
 _, old_exp = self.cache[key]
 if now >= old_exp:
 del self.cache[key]
 else:
 self.cache[key] = (value, exp)
 self.cache.move_to_end(key)
 return

 while len(self.cache) >= self.capacity:
 try:
 lru_key, (_, lru_exp) = next(iter(self.cache.items()))
 except StopIteration:
 break
 if now >= lru_exp:
 del self.cache[lru_key]
 continue
 else:
 del self.cache[lru_key]
 break

 self.cache[key] = (value, exp)

 DeepSeek-V4-Pro: Here's the implementation of a TTL Cache with the required specifications:

```python
class TTLCache:
 def __init__(self, capacity: int):
 self.capacity = capacity
 self.cache = {} # key -> (value, expiry_time)
 self.order = {} # key -> node in doubly linked list for LRU

 # Doubly linked list implementation using dictionaries
 self.head = DummyNode()
 self.tail = DummyNode()
 self.head.next = self.tail
 self.tail.prev = self.head

 def _remove_node(self, node):
 """Remove a node from the doubly linked list."""
 node.prev.next = node.next
 node.next.prev = node.prev

 def _add_to_front(self, node):
 """Add a node right after the head (most recently used)."""
 node.next = self.head.next
 node.prev = self.head
 self.head.next.prev = node
 self.head.next = node

 def _move_to_front(self, node):
 """Move an existing node to the front."""
 self._remove_node(node)
 self._add_to_front(node)

 def _evict_expired(self, now: int):
 """Remove all expired entries."""
 to_remove = []
 for key, (value, expiry) in self.cache.items():
 if expiry <= now:
 to_remove.append(key)

 for key in to_remove:
 node = self.order[key]
 self._remove_node(node)
 del self.order[key]
 del self.cache[key]

 def _evict_lru(self):
 """Evict the least recently used item (from the back)."""
 if self.tail.prev != self.head:
 lru_node = self.tail.prev
 # Find the key associated with this node
 for key, node in self.order.items():
 if node == lru_node:
 self._remove_node(lru_node)
 del self.order[key]
 del self.cache[key]
 break

 def get(self, key: str, now: int) -> int | None:
 if key not in self.cache:
 return None

 value, expiry = self.cache[key]

 # Check if expired
 if expiry <= now:
 # Remove expired entry
 node = self.order[key]
 self._remove_node(node)
 del self.order[key]
 del self.cache[key]
 return None

 # Move to front (most recently used)
 self._move_to_front(self.order[key])
 return value

 def put(self, key: str, value: int, ttl: int, now: int) -> None:
 expiry = now + ttl

 # First, evict all expired items
 self._evict_expired(now)

 if key in self.cache:
 # Update existing key
 self.cache[key] = (value, expiry)
 self._move_to_front(self.order[key])
 return

 # Check if we need to make room
 if len(self.cache) >= self.capacity:
 while len(self.cache) >= self.capacity and self.capacity > 0:
 self._evict_lru()

 if self.capacity == 0:
 return

 # Insert new item
 self.cache[key] = (value, expiry)
 new_node = Node(key)
 self.order[key] = new_node
 self._add_to_front(new_node)

class Node:
 def __init__(self, key: str):
 self.key = key
 self.prev = None
 self.next = None

class DummyNode:
 def __init__(self):
 self.prev = None
 self.next = None
```

 Model A provides valid Python code only and correctly implements TTL-aware LRU behavior with expired entries removed on access and before eviction. Model B violates the code-only instruction, has non-O(1) eviction logic, and includes explanatory text and markdown. (Order-swapped judge pass: Model B is much closer to the requested behavior and returns code only. Model A violates the output format,



 translate_fr_ca_push_notice

 Translate the following app message into Canadian French. Use a friendly but professional tone, suitable for a banking app push notification. Keep it to at most 18 words, preserve the meaning, and keep the currency amount and time exactly as written.

"Heads up: your transfer of $248.19 is still pending. Review it before 6:30 PM to avoid cancellation."

 Muse Spark 1.1: Rappel : votre virement de $248.19 est toujours en attente. Veuillez le vérifier avant 6:30 PM pour éviter l'annulation.

 DeepSeek-V4-Pro: Petit rappel : votre transfert de 248,19 $ est toujours en attente. Vérifiez-le avant 18 h 30 pour éviter son annulation.

 Model A preserves the currency amount and time exactly as written and stays faithful to the original message. Model B sounds natural in Canadian French, but it violates a key instruction by changing both the amount format and the time format. (Order-swapped judge pass: Model B better follows the key constraint to keep the currency amount and time exactly as written, while still providing a natura


 Matchup powered by
 OpenRouter .
````

---

### [20] AI inference is obviously profitable

`seangoedecke.com` · 2026-06-26 · *no author found* · **first-hand analysis**, own cost estimate · about V4: passing

<https://seangoedecke.com/ai-inference-is-obviously-profitable/>

> V4-Pro cited once for pricing; the argument is about inference margins.

Model surfaces matched: `deepseek-v4-pro`

Artifacts (2 kinds):

- `price` — $1.80; $20; $4.50 per million; 13 cents per million; 87 cents per million
- `version_string` — DeepSeek-V4-Pro; GPT-5.4-mini

```text
Many people claim that AI inference is unprofitable to serve, and thus must be subsidized by an ocean of dumb money from investors who believe that some future AI model will come to dominate the world economy. When that dumb money goes away, so will AI products. According to this view, LLMs are just inherently too expensive (in terms of money, power, and water) to be used in consumer products. In 

 There are good reasons to dislike AI, but this really isn’t one of them. In fact, AI inference is obviously profitable .

 Doing the math demonstrates that inference is profitable

 Frontier AI providers are reporting 70%-80% gross margins on inference, but maybe we can’t trust them. Let’s do some very rough estimates on the actual cost.

 A Nvidia A100 consumes 400W of power under full load. In practice, even a carefully-tuned inference server will not be at full load all the time, but it’s at least an upper bound. Suppose you’re running a dense 70B model 1 , which will fit comfortably (unquantized) on four A100s at around 2M tokens per hour. At industrial power prices, that’s about 13c/hr in the USA . Suppose (pessimistically) co

 Let’s amortize the cost of the GPUs, since that’s going to be the most expensive part. An A100 costs about $20k. If each A100 lasts around five years 3 , you’ll have to make 16k/yr in profit to recoup your capital investment (or $1.80 per hour). At lower utilization, it’ll take longer to recoup, but your GPUs will also last longer. Either way, your overall inference costs are at about one dollar 

 GPT-5.4-mini charges $4.50 per million tokens, and stronger OpenAI or Anthropic models are three to six times as expensive. It’s hard to make a direct comparison because we don’t know the size of OpenAI or Anthropic models, but the claimed 70% or 80% profit margin is extremely plausible.

 Open LLMs demonstrate that inference is profitable

 What if you don’t trust my estimates either? Let’s look at the pricing of open-weights Chinese LLMs. DeepSeek have claimed a bit over 80% profit margin on inference for DeepSeek-R1. Since their API pricing for R1 is less than half that of OpenAI or Anthropic 4 , that suggests that my estimates above for inference cost might be too expensive. Cooling at scale is probably cheaper than power, R1 onl

 Since DeepSeek’s models are available for anyone to download, they can’t get away with extracting a large profit margin. One of the other inference providers would undercut them with the same model. Inference costs for DeepSeek-V4-Pro on the market are around 87 cents per million output tokens, which is probably pretty close to the actual cost of serving the model.

 For AI labs, inference must subsidize training

 All of this doesn’t mean that OpenAI or Anthropic are profitable. Those companies are making huge capital investments that may or may not pan out, and are spending enormous amounts of money on talent and compute to train brand-new models and retain users.

 They’re doing crazy things like offering per-month subscription models for nearly unlimited inference, which is almost certainly not profitable. If you used an API token instead of your Anthropic subscription in Claude Code, you’d pay ten times the cost. But that doesn’t mean API-based Claude Code couldn’t be a good deal. Some people are already using DeepSeek’s inference API for agentic coding, 

 Why won’t OpenAI or Anthropic lower their prices? Supposedly OpenAI has thought about it , but for an AI lab, inference has to subsidize training costs . A company like OpenAI has to fund the production of new models from the inference margins on existing models (at least partially). That’s why the margins on inference are so high: the AI labs are trying to squeeze out every dollar so they can st

 However, inference only has to subsidize training costs for an AI lab . If you’re merely an inference provider, you don’t have to do any training at all. Therefore, even if OpenAI and Anthropic go out of business, whoever snaps up the rights to their frontier models will be able to continue selling Opus and GPT inference at a profit 5 . The AI bubble popping will not mean the end of the inference





 Expensive frontier models are probably mixture-of-experts, not dense, which is tougher to estimate. However, I think a 70B dense model and a MoE with 70B active params will come out to basically the same numbers at scale (though the MoE will require more GPU memory and thus a greater upfront cost). Are frontier models around 70B params? Nobody outside the AI labs really knows, but my guess is tha

 ↩


 I think it’s reasonable to estimate the cost of output tokens only, since they’re by far the most expensive part of serving inference. Input tokens are cheaper for two reasons: transformers let you prefill them in parallel, and for most real-world use cases they can be aggressively cached in the KV cache.

 ↩


 It’s common (and wrong) to estimate GPU lifespan at three years. I wrote a lot about this in AI GPUs probably live longer than three years .

 ↩


 Again, this is just an guess, since we don’t know what OpenAI or Anthropic model is equivalent in size to R1.

 ↩


 I do wonder if Anthropic would be able to prevent other people from being able to access the model if the company goes out of business. Anthropic is currently in debt to Broadcom, Google, and a bunch of private equity firms. Would they get the Mythos and Opus weights, over Dario’s protestations?

 ↩



 If you liked this post, consider subscribing to email updates about my new posts, or sharing it on Hacker News .
 Here's a preview of a related post that shares tags with this one.
 AI GPUs probably live longer than three years
 People who think current AI use is unsustainable often rely on the claim that inference GPUs only last “three years at the most” under load. The idea here is that once the AI bubble money drains away, current infrastructure will rapidly become obsolete, and there won’t be enough money floating around to buy a whole slate of brand-new GPUs. Inference costs would thus rapidly become way too expensi
 Continue reading...
```

---

### [21] DeepSeek V4 – almost on the frontier

`simonwillison.net` · 2026-04-24 · Simon Willison · **first-hand analysis**, own test + vendor prices WITH the source linked · about V4: yes

<https://simonwillison.net/2026/Apr/24/deepseek-v4/>

> Parameter counts, a full price comparison table, and a reproducible command. Names where the prices come from ('This is DeepSeek's pricing page'). RSS COULD NOT REACH THIS - recovered from the HN URL.

Model surfaces matched: `deepseek v4`, `deepseek v4 flash`, `deepseek v4 pro`, `deepseek-v4-flash`, `deepseek-v4-pro`

Artifacts (3 kinds):

- `price` — $0.14; $0.14/million; $0.20; $0.25; $0.28; $0.28/million
- `version_string` — Claude Haiku 4.5; Claude Opus 4.7; Claude Sonnet 4.6; DeepSeek V3.2; DeepSeek V4 Flash; DeepSeek V4 Pro
- `code_fence` — 1 <pre>/<code> block(s)

```text
DeepSeek V4—almost on the frontier, a fraction of the price
























 Simon Willison’s Weblog

 Subscribe






 Sponsored by: Greptile — The Al code reviewer that runs your code. Catch bugs that only show up at runtime. Try it for free








 DeepSeek V4—almost on the frontier, a fraction of the price

 24th April 2026

 Chinese AI lab DeepSeek’s last model release was V3.2 (and V3.2 Speciale) last December . They just dropped the first of their hotly anticipated V4 series in the shape of two preview models, DeepSeek-V4-Pro and DeepSeek-V4-Flash .

 Both models are 1 million token context Mixture of Experts. Pro is 1.6T total parameters, 49B active. Flash is 284B total, 13B active. They’re using the standard MIT license.

 I think this makes DeepSeek-V4-Pro the new largest open weights model. It’s larger than Kimi K2.6 (1.1T) and GLM-5.1 (754B) and more than twice the size of DeepSeek V3.2 (685B).

 Pro is 865GB on Hugging Face, Flash is 160GB. I’m hoping that a lightly quantized Flash will run on my 128GB M5 MacBook Pro. It’s possible the Pro model may run on it if I can stream just the necessary active experts from disk.

 For the moment I tried the models out via OpenRouter , using llm-openrouter :

 llm install llm-openrouter
llm openrouter refresh
llm -m openrouter/deepseek/deepseek-v4-pro 'Generate an SVG of a pelican riding a bicycle'


 Here’s the pelican for DeepSeek-V4-Flash :



 And for DeepSeek-V4-Pro :



 For comparison, take a look at the pelicans I got from DeepSeek V3.2 in December , V3.1 in August , and V3-0324 in March 2025 .

 So the pelicans are pretty good, but what’s really notable here is the cost . DeepSeek V4 is a very, very inexpensive model.

 This is DeepSeek’s pricing page . They’re charging $0.14/million tokens input and $0.28/million tokens output for Flash, and $1.74/million input and $3.48/million output for Pro.

 Here’s a comparison table with the frontier models from Gemini, OpenAI and Anthropic:





 Model
 Input ($/M)
 Output ($/M)




 DeepSeek V4 Flash
 $0.14
 $0.28


 GPT-5.4 Nano
 $0.20
 $1.25


 Gemini 3.1 Flash-Lite
 $0.25
 $1.50


 Gemini 3 Flash Preview
 $0.50
 $3


 GPT-5.4 Mini
 $0.75
 $4.50


 Claude Haiku 4.5
 $1
 $5


 DeepSeek V4 Pro
 $1.74
 $3.48


 Gemini 3.1 Pro
 $2
 $12


 GPT-5.4
 $2.50
 $15


 Claude Sonnet 4.6
 $3
 $15


 Claude Opus 4.7
 $5
 $25


 GPT-5.5
 $5
 $30




 DeepSeek-V4-Flash is the cheapest of the small models, beating even OpenAI’s GPT-5.4 Nano. DeepSeek-V4-Pro is the cheapest of the larger frontier models.

 This note from the DeepSeek paper helps explain why they can price these models so low—they’ve focused a great deal on efficiency with this release, especially for longer context prompts:


 In the scenario of 1M-token context, even DeepSeek-V4-Pro, which has a larger number of activated parameters, attains only 27% of the single-token FLOPs (measured in equivalent FP8 FLOPs) and 10% of the KV cache size relative to DeepSeek-V3.2. Furthermore, DeepSeek-V4-Flash, with its smaller number of activated parameters, pushes efficiency even further: in the 1M-token context setting, it achiev

 DeepSeek’s self-reported benchmarks in their paper show their Pro model competitive with those other frontier models, albeit with this note:


 Through the expansion of reasoning tokens, DeepSeek-V4-Pro-Max demonstrates superior performance relative to GPT-5.2 and Gemini-3.0-Pro on standard reasoning benchmarks. Nevertheless, its performance falls marginally short of GPT-5.4 and Gemini-3.1-Pro, suggesting a developmental trajectory that trails state-of-the-art frontier models by approximately 3 to 6 months.

 I’m keeping an eye on huggingface.co/unsloth/models as I expect the Unsloth team will have a set of quantized versions out pretty soon. It’s going to be very interesting to see how well that Flash model runs on my own machine.

 Posted 24th April 2026 at 6:01 am · Follow me on Mastodon , Bluesky , Twitter or subscribe to my newsletter




 More recent articles



 Claude Fable 5.1 made me a really nice animated pelican - 1st September 2026


 Understanding ChatGPT Work - 30th August 2026


 Conceptual integrity and counting lines of code - 19th August 2026









 This is DeepSeek V4—almost on the frontier, a fraction of the price by Simon Willison, posted on 24th April 2026 .



 ai
 2,211



 generative-ai
 1,959



 llms
 1,926



 llm
 626



 llm-pricing
 90



 pelican-riding-a-bicycle
 138



 deepseek
 35



 llm-release
 227



 openrouter
 30



 ai-in-china
 108



 Next: Tracking the history of the now-deceased OpenAI Microsoft AGI clause

 Previous: Extract PDF text in your browser with LiteParse for the web



 Monthly briefing



 Sponsor me for $10/month and get a curated email digest of the month's most important LLM developments.



 Pay me to send you less!



 Sponsor & subscribe









 Disclosures

 Colophon

 ©

 2002

 2003

 2004

 2005

 2006

 2007

 2008

 2009

 2010

 2011

 2012

 2013

 2014

 2015

 2016

 2017

 2018

 2019

 2020

 2021

 2022

 2023

 2024

 2025

 2026
```

---

### [22] Just a rumour of a bug is enough to find a security exploit these days

`simonwillison.net` · 2026-08-28 · Simon Willison · **opinion**, third-party result restated · about V4: passing

<https://simonwillison.net/2026/Aug/28/just-a-rumour-of-a-bug/>

> V4 Pro named in passing in a security-research anecdote.

Model surfaces matched: `deepseek v4 pro`

Artifacts (2 kinds):

- `price` — $10
- `version_string` — DeepSeek V4 Pro; Fable 5.1

```text
Just a rumour of a bug is enough to find a security exploit these days






















 Simon Willison’s Weblog

 Subscribe






 Sponsored by: Greptile — The Al code reviewer that runs your code. Catch bugs that only show up at runtime. Try it for free







 28th August 2026 - Link Blog


 Just a rumour of a bug is enough to find a security exploit these days ( via ) Anil Madhavapeddy is a professor of computer science at Cambridge and a core maintainer of the OCaml compiler. In this somewhat alarming post he reports that security issues in OCaml projects are seeing evidence of attempted exploits within minutes of patches being shared for discussion:


 This normally takes a few days and a release within a week or two is reasonable. Within about ten minutes (!) this website was fielding probes for percent-encoded traversal sequences, indicating that automated watchers are keeping an eye on public repositories.

 Modern coding agents have become so effective at finding flaws that the slightest hint at a new bug can be enough information for them to find it, something Anil has been able to demonstrate using his own agents, switching to DeepSeek V4 Pro⁠ when Claude Fable refused the task.

 Anil points out that this rate of discovery appears incompatible with existing open source embargo practices for new issues. If an issue can become an exploit this fast, we need to figure out new processes for keeping our communities safe.

 rclone maintainer Nick Craig-Wood confirms in the Hacker News comments that his project is seeing this problem:


 In the first 10 years of the rclone project we received about 20 security disclosures through GitHub. We had to deal with over 40 in the last month! That has taken a huge amount of my time, even using AI tools to triage and come up with fixes for review.

 The hit rate for those security disclosures is pretty good - about 75% of them have a nugget of something which needs looking at. [...]

 GitHub assigns CVEs for the advisories. Before the AI apocalypse they took 2-3 days for an assignment but now it they are running at 3-4 weeks so I have to send the point releases out with CVE-PENDING in the changelog which isn't ideal.

 Posted 28th August 2026 at 10:12 pm




 Recent articles



 Claude Fable 5.1 made me a really nice animated pelican - 1st September 2026


 Understanding ChatGPT Work - 30th August 2026


 Conceptual integrity and counting lines of code - 19th August 2026









 This is a link post by Simon Willison, posted on 28th August 2026 .



 open-source
 318



 security
 628



 ai
 2,211



 generative-ai
 1,959



 llms
 1,926



 coding-agents
 243



 ocaml
 5



 ai-security-research
 38





 Monthly briefing



 Sponsor me for $10/month and get a curated email digest of the month's most important LLM developments.



 Pay me to send you less!



 Sponsor & subscribe












 Disclosures

 Colophon

 ©

 2002

 2003

 2004

 2005

 2006

 2007

 2008

 2009

 2010

 2011

 2012

 2013

 2014

 2015

 2016

 2017

 2018

 2019

 2020

 2021

 2022

 2023

 2024

 2025

 2026
```

---

### [23] Evaluating DeepSeek V4 Pro 0813 on Hack The Box Challenges

`theaq.blog` · 2026-08-18 · TheArtificialQ · **benchmark**, own measurement · about V4: yes

<https://theaq.blog/2026/08/18/evaluating-deepseek-deepseek-v4-pro-0813-on-hack-the-box-challenges.html>

> BEST post in the set for our purposes. 38.8% vs 36.2% and 9 vs 8 challenges, and the author calls it A DRAW on run-to-run variability. Median steps 12.5 vs 62.5, tokens 0.25M vs 1.94M, cost $0.20 vs $0.35. Explicitly flags vendor benchmarks as 'the developer's own results'.

Model surfaces matched: `deepseek v4 pro`, `deepseek v4 pro 0423`, `deepseek v4 pro 0813`

Artifacts (4 kinds):

- `benchmark_number` — 0813 through my HTB-Challenger
- `price` — $0.05; $0.10,; $0.20; $0.22; $0.35; $0.40
- `version_string` — DeepSeek V4 Pro; DeepSeek V4 Pro 0423; DeepSeek V4 Pro 0813; GPT-5.6; Grok 4.6
- `code_fence` — 8 <pre>/<code> block(s)

Benchmark figures, and whether a source is named within 300 chars:

- *bare* `0813 through my HTB-Challenger`

```text
The release of DeepSeek V4 Pro back in April got a lot of attention - so DeepSeek decided to release it again! The new version is called DeepSeek V4 Pro 0813 , and it is not exactly clear what changed. Reading its release page , you can almost feel the marketing team’s desperation to put at least something there. The few concrete details are that it uses the same core V4 Pro architecture with appr

 DeepSeek reports large improvements across several agent benchmarks, although those are the developer’s own results. I had finished testing the previous Pro version, now called DeepSeek V4 Pro 0423 , shortly before the new version appeared (sic!). I therefore ran 0813 through my HTB-Challenger Benchmark The HTB-Challenger Benchmark evaluates LLMs’ ability to find and exploit security vulnerabilit
 to see whether it performed better on cybersecurity tasks.








 This blog post is part of a series of tests for the HTB-Challenger Benchmark The HTB-Challenger Benchmark evaluates LLMs’ ability to find and exploit security vulnerabilities. It tests models against selected Hack The Box challenges of varying difficulty and measures their performance. For more information, visit the HTB-Challenger Benchmark page .
.
See the benchmark results page for all results and the benchmark methodology to learn how the benchmark is calculated.



 The new model achieved a slightly higher benchmark score than the old one, 38.8% versus 36.2%, and solved nine challenges instead of eight. Given the small test set and normal run-to-run variability, I would still call the performance result a draw.

 The clearest improvement was efficiency. The median run used far fewer steps (12.5 versus 62.5), tokens (0.25M versus 1.94M), and money ($0.20 versus $0.35) than the older model. That is a good reason to upgrade if you still use the older version.

 If you are not specifically committed to DeepSeek, however, there are better choices for this kind of cybersecurity work. GPT-5.6 Luna Pro scored 51.3% at a lower median cost of $0.10, while Grok 4.6 and GPT-5.6 Sol achieved much higher scores at broadly similar median costs.





 Cost vs. Benchmark Score

 The highlighted point is this model. Models closer to the upper-left achieve a higher benchmark score at a lower median cost per challenge.





 Overall benchmark results


 Number of challenges: 16

 Number of solved challenges : 9

 Number of false positives : 0

 Runs where the model gave up : 0

 Runs that reached the step or cost limit : 2

 Runs where the model got stuck : 5

 Benchmark score: 38.8%






 Metric
 Per challenge (median)
 Total





 Model steps
 12.5
 456



 Model cost
 $0.20
 $7.97



 Duration
 00:07:17
 06:46:42



 Number of input tokens
 0.24M
 16.32M



 Number of output tokens
 0.01M
 0.98M



 Number of read_file tool calls
 1.0
 121



 Number of write_file tool calls
 0.5
 43



 Number of execute_command tool calls
 13.0
 434



 Number of web_search tool calls
 0.0
 12




 Results by challenge difficulty

 All resource-usage metrics are medians per challenge.




 Metric
 Very Easy
 Easy
 Medium
 Hard





 Results







 Number of challenges
 4
 4
 4
 4



 Number of solved challenges
 4
 3
 2
 0



 Number of false positives
 0
 0
 0
 0



 Runs where the model gave up
 0
 0
 0
 0



 Runs that reached the step or cost limit
 0
 0
 1
 1



 Runs where the model got stuck
 0
 1
 1
 3



 Benchmark score
 94.4%
 73.1%
 49.2%
 0.0%



 Median per challenge







 Model steps
 10.5
 12.5
 27
 19



 Model cost
 $0.05
 $0.22
 $1.08
 $0.40



 Duration
 00:03:09
 00:09:19
 00:34:12
 00:10:44



 Number of input tokens
 0.07M
 0.18M
 0.47M
 0.75M



 Number of output tokens
 0.00M
 0.02M
 0.11M
 0.02M



 Number of read_file tool calls
 0.5
 1.0
 1.5
 0.0



 Number of write_file tool calls
 0.0
 4.0
 1.0
 0.0



 Number of execute_command tool calls
 10.0
 8.5
 22.5
 13.0



 Number of web_search tool calls
 0.0
 1.0
 0.0
 0.0
```

---

### [25] Evaluating Ox Alpha on Hack The Box Challenges

`theaq.blog` · 2026-08-21 · TheArtificialQ · **benchmark**, own measurement · about V4: passing

<https://theaq.blog/2026/08/21/evaluating-stealth-ox-alpha-on-hack-the-box-challenges.html>

> V4 Pro 0813 named as a disappointment among 'models hyped by their marketing teams'. Comparative, not a V4 test.

Model surfaces matched: `deepseek v4 pro 0813`

Artifacts (4 kinds):

- `benchmark_number` — 24. Today, I tested it on my HTB-Challenger
- `price` — $0.00; $10
- `version_string` — DeepSeek V4 Pro 0813; GLM 5.3; GPT-5.6
- `code_fence` — 8 <pre>/<code> block(s)

Benchmark figures, and whether a source is named within 300 chars:

- **cited** `24. Today, I tested it on my HTB-Challenger`

```text
A new model called Ox Alpha landed on OpenRouter last night, and you can use it for free through Monday, August 24. Today, I tested it on my HTB-Challenger Benchmark The HTB-Challenger Benchmark evaluates LLMs’ ability to find and exploit security vulnerabilities. It tests models against selected Hack The Box challenges of varying difficulty and measures their performance. For more information, vi
, and hear me out: stop what you’re doing, cancel your weekend plans, and test it! If you need to cancel all your meetings, your child’s birthday party, or your romantic weekend for two, do it. It’s worth it! Just don’t tell my wife I said that 😉

 But really, do it.








 This blog post is part of a series of tests for the HTB-Challenger Benchmark The HTB-Challenger Benchmark evaluates LLMs’ ability to find and exploit security vulnerabilities. It tests models against selected Hack The Box challenges of varying difficulty and measures their performance. For more information, visit the HTB-Challenger Benchmark page .
.
See the benchmark results page for all results and the benchmark methodology to learn how the benchmark is calculated.



 The model was released as a “stealth model,” i.e., we don’t know what model it actually is or who created it. If you’re interested in speculation, quickly search Reddit, but you probably won’t be much wiser afterward.

 As I already wrote above, it’s free for a limited time. This typically means the model provider is collecting your entire communication and may use it for their own purposes, so be careful. There is also a 1,000-request limit on free models, with a 20 RPM limit if you’re an OpenRouter user with at least $10 in credits.

 Anyway, the most interesting thing about this model is that it’s freaking good. After recent disappointments from models hyped by their marketing teams (looking at you GLM 5.3 , and especially you DeepSeek V4 Pro 0813 ), I didn’t expect much from a model that came out of nowhere.

 That’s why, when I started my test harness for the HTB-Challenger Benchmark The HTB-Challenger Benchmark evaluates LLMs’ ability to find and exploit security vulnerabilities. It tests models against selected Hack The Box challenges of varying difficulty and measures their performance. For more information, visit the HTB-Challenger Benchmark page .
, I was pleasantly surprised to see it crack one HTB challenge after another at a steady pace. In the end, it solved 15 out of 16 challenges, the same number as GPT-5.6 Sol , the best model I’ve tested so far.

 In terms of score, it landed a few percentage points behind Sol (81.4% vs. 87.2%) because it was less efficient at solving the challenges. It needed a higher median number of steps (25 vs. 8.5) and tokens (0.54M vs. 0.09M).

 But hey, who cares if it takes more tokens when it’s free? 😄 The important part is that you now have three days of free access to a Sol-level model.





 Overall benchmark results


 Number of challenges: 16

 Number of solved challenges : 15

 Number of false positives : 0

 Runs where the model gave up : 0

 Runs that reached the step or cost limit : 1

 Runs where the model got stuck : 0

 Benchmark score: 81.4%






 Metric
 Per challenge (median)
 Total





 Model steps
 25
 562



 Model cost
 $0.00
 $0.00



 Duration
 00:10:13
 06:37:20



 Number of input tokens
 0.52M
 16.69M



 Number of output tokens
 0.02M
 0.67M



 Number of read_file tool calls
 1.0
 27



 Number of write_file tool calls
 2.5
 70



 Number of execute_command tool calls
 21.5
 521



 Number of web_search tool calls
 0.0
 2




 Results by challenge difficulty

 All resource-usage metrics are medians per challenge.




 Metric
 Very Easy
 Easy
 Medium
 Hard





 Results







 Number of challenges
 4
 4
 4
 4



 Number of solved challenges
 4
 4
 4
 3



 Number of false positives
 0
 0
 0
 0



 Runs where the model gave up
 0
 0
 0
 0



 Runs that reached the step or cost limit
 0
 0
 0
 1



 Runs where the model got stuck
 0
 0
 0
 0



 Benchmark score
 95.2%
 94.3%
 90.5%
 64.8%



 Median per challenge







 Model steps
 18
 18.5
 19
 57.5



 Model cost
 $0.00
 $0.00
 $0.00
 $0.00



 Duration
 00:03:03
 00:06:10
 00:17:41
 00:23:49



 Number of input tokens
 0.18M
 0.27M
 0.42M
 2.32M



 Number of output tokens
 0.01M
 0.01M
 0.02M
 0.03M



 Number of read_file tool calls
 0.5
 1.0
 0.5
 1.5



 Number of write_file tool calls
 2.0
 2.5
 3.0
 4.5



 Number of execute_command tool calls
 16.0
 14.0
 16.0
 62.5



 Number of web_search tool calls
 0.0
 0.5
 0.0
 0.0
```

---

### [26] Evaluating MiniMax M3 on Hack The Box Challenges

`theaq.blog` · 2026-08-25 · TheArtificialQ · **benchmark**, own measurement · about V4: passing

<https://theaq.blog/2026/08/25/evaluating-minimax-minimax-m3-on-hack-the-box-challenges.html>

> V4 appears comparatively.

Model surfaces matched: `deepseek v4 pro 0813`

Artifacts (3 kinds):

- `price` — $0.02,; $0.07; $0.08.; $0.14; $0.16; $0.21
- `version_string` — DeepSeek V4 Pro 0813; GLM 5.3; GPT-5.6
- `code_fence` — 8 <pre>/<code> block(s)

```text
While we wait to see whether MiniMax releases its reported 2.7-trillion-parameter successor, known internally as MiniMax M3 Pro and potentially arriving as early as the third quarter , I decided to return to MiniMax M3 , released at the end of May, and run it through my HTB-Challenger Benchmark The HTB-Challenger Benchmark evaluates LLMs’ ability to find and exploit security vulnerabilities. It te
. I know that M3 has many fans, but I had never used or tested it, so I wasn’t sure what to expect.








 This blog post is part of a series of tests for the HTB-Challenger Benchmark The HTB-Challenger Benchmark evaluates LLMs’ ability to find and exploit security vulnerabilities. It tests models against selected Hack The Box challenges of varying difficulty and measures their performance. For more information, visit the HTB-Challenger Benchmark page .
.
See the benchmark results page for all results and the benchmark methodology to learn how the benchmark is calculated.



 After trying many LLMs on cybersecurity tasks, I have repeatedly seen non-frontier models fall into loops when you ask them to do something beyond their capabilities.

 These loops can take two forms:


 The model makes the exact same tool call, with the same arguments, over and over again.

 The model starts producing “never-ending” reasoning full of phrases such as “Wait, let me re-read…” and “Actually, let me think about this differently” , without making any visible progress.



 A clear example of repeated identical tool calls is DeepSeek V4 Pro 0813 , which ended four of my 16 benchmark runs this way.

 The second failure mode was more common. GLM 5.3 hit this issue in three of 16 runs. The absolute “champion” was Hy3 , which did so in nine of 16 runs.

 Well, MiniMax M3 is unfortunately another model where this issue prevents it from finishing more difficult tasks. Half of the 16 challenges ended in never-ending loops, and as a result, its final score was poor.

 Its $0.16 median cost per challenge was not especially high across the full benchmark, but the value was weak compared with nearby peers. GPT-5.6 Luna scored 31.6% at a median cost of $0.02, while Hy3 scored 34.8% at $0.08. Given M3’s low score and high rate of stuck runs in these tests, there is not much positive I can say about its performance in this benchmark.





 Cost vs. Benchmark Score

 The highlighted point is this model. Models closer to the upper-left achieve a higher benchmark score at a lower median cost per challenge.





 Overall benchmark results


 Number of challenges: 16

 Number of solved challenges : 7

 Number of false positives : 0

 Runs where the model gave up : 0

 Runs that reached the step or cost limit : 1

 Runs where the model got stuck : 8

 Benchmark score: 30.5%






 Metric
 Per challenge (median)
 Total





 Model steps
 26.5
 593



 Model cost
 $0.16
 $3.08



 Duration
 00:07:45
 02:46:11



 Number of input tokens
 0.36M
 13.14M



 Number of output tokens
 0.07M
 1.57M



 Number of read_file tool calls
 0.0
 24



 Number of write_file tool calls
 0.0
 32



 Number of execute_command tool calls
 23.5
 615



 Number of web_search tool calls
 0.0
 5




 Results by challenge difficulty

 All resource-usage metrics are medians per challenge.




 Metric
 Very Easy
 Easy
 Medium
 Hard





 Results







 Number of challenges
 4
 4
 4
 4



 Number of solved challenges
 3
 2
 2
 0



 Number of false positives
 0
 0
 0
 0



 Runs where the model gave up
 0
 0
 0
 0



 Runs that reached the step or cost limit
 0
 0
 0
 1



 Runs where the model got stuck
 1
 2
 2
 3



 Benchmark score
 61.7%
 47.9%
 49.0%
 0.0%



 Median per challenge







 Model steps
 61
 19
 12
 27.5



 Model cost
 $0.29
 $0.14
 $0.07
 $0.21



 Duration
 00:13:23
 00:09:34
 00:04:09
 00:07:45



 Number of input tokens
 1.01M
 0.15M
 0.14M
 0.75M



 Number of output tokens
 0.11M
 0.11M
 0.04M
 0.07M



 Number of read_file tool calls
 2.0
 2.5
 0.0
 0.0



 Number of write_file tool calls
 0.0
 1.0
 0.0
 0.0



 Number of execute_command tool calls
 47.0
 21.0
 10.0
 32.5



 Number of web_search tool calls
 0.0
 0.0
 0.0
 0.0
```
