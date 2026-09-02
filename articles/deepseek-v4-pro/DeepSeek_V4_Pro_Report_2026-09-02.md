# DeepSeek V4 Pro — Social Tracking Report

**Model tracked:** `DeepSeek V4 Pro` (checkpoint `deepseek-v4-pro-0813`)
**Platforms:** Instagram, TikTok
**Collected:** 2026-09-02T05:22:00.581Z → 2026-09-02T05:47:03.518Z (UTC)
**Keywords:** `deepseek-v4-pro`, `deepseekv4pro`, `deepseek-v4-pro-0813`
**Generated:** 2026-09-02T05:56:59.913Z

---

## 1. Executive summary

| Metric | Value |
|---|--:|
| **On-target posts (V4 Pro)** | **514** |
| — Instagram | 377 |
| — TikTok | 137 |
| TikTok views (on-target) | 1,719,640 |
| Likes (all on-target) | 88,245 |
| Comments (all on-target) | 4,480 |
| Shares (TikTok) | 6,706 |
| Saves (TikTok) | 18,018 |
| Posts mentioning V4 **Flash** (sibling) | 261 |
| Posts mentioning V4, variant unspecified | 385 |
| Other DeepSeek posts (non-V4, context) | 1,539 |
| **Total DeepSeek posts captured** | **2,699** |
| Date range of on-target posts | 2026-04-24 → 2026-09-02 |
| Instagram API calls (whole experiment) | 462 / 600 |
| TikTok API calls (whole experiment) | 216 / 250 |

### Headline findings

1. **514 posts specifically reference DeepSeek V4 Pro** across both platforms — 377 on Instagram and 137 on TikTok. TikTok carries the reach: **1,719,640 views** on on-target videos versus Instagram, where the hashtag feed exposes no view count at all.
2. **"V4 Pro" long predates the `0813` checkpoint.** On-target posts run from **2026-04-24**, and the busiest month is **2026-08** (335 posts). `0813` is a dated checkpoint of an existing model line, not the model's debut — so this dataset captures an ongoing conversation, not a single launch spike.
3. **Reach is extremely top-heavy.** Median on-target TikTok video: **687.5 views**; the single top video: **751,276 views** — 43.7% of all on-target TikTok reach by itself. Aggregate view counts here describe a handful of breakout videos, not typical performance.
4. **The V4 family is discussed as a set, not a single model.** Alongside the 514 Pro posts, the sweep captured 261 Flash-specific and 385 variant-unspecified V4 posts. Head-to-head comparison (Pro 0813 vs Flash 0731, or against rival models) is a recurring content format, which is why tier precedence matters — see §2.2.
5. **The conversation is commercial before it is technical.** The dominant themes across on-target posts are **API / deployment** (228), **Pricing / cost** (221), **Coding / dev use** (152) — see §7 for the full breakdown.
6. **Reach is decoupled from audience size.** Of 73 on-target TikTok posts with a known follower count, **18 (24.7%) exceeded 10× their creator's follower count** — the clearest case, [@sxechina](https://www.tiktok.com/@sxechina/video/7643412561517464854), drew 751,276 views from 26,090 followers (29×). On TikTok this topic is distributed by the algorithm, not by existing followings, so small accounts are credible carriers of model news.
7. **Instagram engagement figures are a floor, not a total.** Instagram's hashtag feed exposes a like count on only 48.8% of returned posts; the rest report zero because the count is *hidden*, not absent. Instagram totals in this report are lower bounds.

---

## 2. Method

### 2.1 How posts were found

This run is **post-centric**, unlike the account-centric creator catalog in the rest of this repo. Two providers were swept:

- **Instagram** — `instagram-looter2` `/tag-feeds?query=<tag>`, paginated via `end_cursor`. This endpoint was undocumented in the existing codebase and was mapped during this run (the provider has **no** keyword/caption post search — hashtags are the only post-level surface).
- **TikTok** — `tiktok-scraper7` `/feed/search` (full-text keyword search over captions) **and** `/challenge/posts` (hashtag feed, via `/challenge/info` → `challenge_id`). Keyword search is the stronger surface because it matches caption text, not just tags.

| Platform | Surface | Pages | Returned | On-target (Pro) | Notes |
|---|---|--:|--:|--:|---|
| Instagram | `#deepseekv4pro` | 2 | 44 | 44 | library size 89 |
| Instagram | `#deepseekv4` | 12 | 366 | 138 | library size 840 |
| Instagram | `#deepseekv4flash` | 1 | 23 | 4 | library size 65 |
| Instagram | `#deepseekv4proopensource` | 1 | 1 | 1 | library size 1 |
| Instagram | `#deepseekv4pro課程` | 1 | 1 | 1 | library size 1 |
| Instagram | `#deepseekv4flash實測` | 1 | 1 | 0 | library size 1 |
| Instagram | `#deepseekv4flash0731實測` | 1 | 1 | 0 | library size 1 |
| Instagram | `#deepseek` | 40 | 1311 | 242 | library size 165,298 |
| Instagram | `#deepseekai` | 10 | 352 | 10 | library size 12,619 |
| Instagram | `#deepseekv4promax` | 1 | 0 | 0 | library size — |
| TikTok | `search:"deepseek v4 pro"` | 8 | 130 | 30 | keyword search |
| TikTok | `search:"deepseekv4pro"` | 8 | 135 | 31 | keyword search |
| TikTok | `search:"deepseek-v4-pro-0813"` | 6 | 97 | 30 | keyword search |
| TikTok | `search:"deepseek v4 pro 0813"` | 5 | 84 | 27 | keyword search |
| TikTok | `search:"deepseek v4"` | 8 | 125 | 9 | keyword search |
| TikTok | `#deepseekv4pro` | 3 | 25 | 25 | hashtag views 83,796 |
| TikTok | `#deepseekv4` | 8 | 110 | 18 | hashtag views 1,063,633 |
| TikTok | `#deepseekv4flash` | 2 | 16 | 0 | hashtag views 31,218 |
| TikTok | `#deepseekv4pro0813` | 0 | 0 | 0 | no such hashtag |
| TikTok | `search:"deepseek pro"` | 6 | 101 | 34 | keyword search |
| TikTok | `search:"deepseek 0813"` | 5 | 86 | 6 | keyword search |
| TikTok | `search:"deepseek v4 pro review"` | 5 | 82 | 23 | keyword search |
| TikTok | `search:"deepseek v4 pro benchmark"` | 5 | 83 | 25 | keyword search |
| TikTok | `search:"deepseek v4 pro coding"` | 5 | 92 | 24 | keyword search |
| TikTok | `search:"深度求索 v4 pro"` | 4 | 75 | 27 | keyword search |
| TikTok | `search:"deepseek v4 pro vs"` | 5 | 85 | 36 | keyword search |
| TikTok | `#deepseek` | 10 | 176 | 3 | hashtag views 3,050,805,018 |

### 2.2 How relevance was decided

Every separator in a caption — space, hyphen, punctuation, emoji, CJK — is normalised to a single space, and the model patterns allow optional whitespace between tokens. So `DeepSeek-V4-Pro`, `deepseek v4 pro`, `DeepSeek V4Pro` and `#deepseekv4pro` all match one pattern, **while word boundaries survive** (see the precision note below). Matches are then assigned to **precedence-ordered tiers**, so each post is counted exactly once:

| Tier | Meaning | Count |
|---|---|--:|
| `pro` | Names the **V4 Pro** checkpoint specifically — the tracking target | **514** |
| `flash` | Names sibling **V4 Flash** (0731), not Pro | 261 |
| `v4` | DeepSeek **V4** family, variant unspecified | 385 |
| `other` | DeepSeek, but not V4 (R1, V3 …) — context only | 1,539 |

A post naming **both** Pro and Flash (a comparison video) is counted as `pro`, since the Pro reference is what is being tracked. Posts with no DeepSeek reference anywhere were dropped at collection time and are not in this file.

**Precision note.** Separator-folding must not destroy word boundaries. A first version of the matcher collapsed captions to bare alphanumerics, which made *"DeepSeek V4 for **pro**gramming"* match the `v4…pro` pattern — inflating the on-target count by 21 posts (~7%). Every Pro pattern now terminates in a word boundary, so `pro` cannot match inside *programming*, *product*, *professional*, *problem* or *project*. This is locked down by `scripts/test_matcher.js` (23 cases, including that false-positive class); re-classification runs off the stored captions via `scripts/retier_artifact.js`, so matcher fixes never require re-spending API budget.

---

## 3. Volume & engagement

### 3.1 On-target (V4 Pro) by platform

| Metric | Instagram | TikTok |
|---|--:|--:|
| Posts | 377 | 137 |
| Views | n/a¹ | 1,719,640 |
| Likes | 10,943² | 77,302 |
| Comments | 2,038 | 2,442 |
| Shares | n/a¹ | 6,706 |
| Saves | n/a¹ | 18,018 |
| Median views | n/a¹ | 687.5 |
| Mean views | n/a¹ | 12,552 |

¹ Instagram's hashtag feed returns no view, share, or save counts.
² Like count visible on only **48.8%** of Instagram posts returned (Instagram hides it on the rest) — treat as a **floor**.

### 3.2 Posting timeline (on-target, by month)

| Month | IG | TikTok | Total | Views | Likes | |
|---|--:|--:|--:|--:|--:|---|
| 2026-04 | 63 | 19 | **82** | 236,788 | 15,448 | `██████` |
| 2026-05 | 29 | 17 | **46** | 909,652 | 37,701 | `████` |
| 2026-06 | 4 | 12 | **16** | 32,462 | 829 | `█` |
| 2026-07 | 16 | 14 | **30** | 40,387 | 1,000 | `██` |
| 2026-08 | 261 | 74 | **335** | 500,333 | 33,264 | `██████████████████████████` |
| 2026-09 | 4 | 1 | **5** | 18 | 3 | `█` |

### 3.3 Recent activity (on-target, last 30 dated days)

| Date | IG | TikTok | Total | Views | Likes | |
|---|--:|--:|--:|--:|--:|---|
| 2026-08-03 | 2 | 1 | **3** | 245 | 2 | `█` |
| 2026-08-04 | 2 | 0 | **2** | 0 | 4 | `█` |
| 2026-08-05 | 0 | 1 | **1** | 115 | 10 | `█` |
| 2026-08-06 | 0 | 1 | **1** | 337 | 4 | `█` |
| 2026-08-07 | 0 | 2 | **2** | 688 | 9 | `█` |
| 2026-08-08 | 1 | 0 | **1** | 0 | 37 | `█` |
| 2026-08-10 | 1 | 0 | **1** | 0 | 0 | `█` |
| 2026-08-11 | 1 | 0 | **1** | 0 | 3 | `█` |
| 2026-08-12 | 9 | 3 | **12** | 1,082 | 41 | `████` |
| 2026-08-13 | 56 | 14 | **70** | 102,077 | 2,722 | `██████████████████████████` |
| 2026-08-14 | 40 | 10 | **50** | 27,875 | 1,186 | `███████████████████` |
| 2026-08-15 | 31 | 4 | **35** | 7,951 | 344 | `█████████████` |
| 2026-08-16 | 30 | 6 | **36** | 1,203 | 354 | `█████████████` |
| 2026-08-17 | 16 | 6 | **22** | 23,478 | 2,203 | `████████` |
| 2026-08-18 | 18 | 3 | **21** | 12,077 | 605 | `████████` |
| 2026-08-19 | 8 | 4 | **12** | 7,924 | 335 | `████` |
| 2026-08-20 | 5 | 0 | **5** | 0 | 7 | `██` |
| 2026-08-21 | 6 | 1 | **7** | 1,485 | 81 | `███` |
| 2026-08-22 | 5 | 0 | **5** | 0 | 2 | `██` |
| 2026-08-23 | 4 | 2 | **6** | 1,708 | 91 | `██` |
| 2026-08-24 | 6 | 1 | **7** | 74,590 | 2,038 | `███` |
| 2026-08-25 | 6 | 0 | **6** | 0 | 4 | `██` |
| 2026-08-26 | 3 | 1 | **4** | 200,509 | 20,767 | `█` |
| 2026-08-27 | 5 | 2 | **7** | 1,931 | 478 | `███` |
| 2026-08-28 | 0 | 2 | **2** | 6,223 | 204 | `█` |
| 2026-08-29 | 1 | 4 | **5** | 2,109 | 116 | `██` |
| 2026-08-30 | 1 | 2 | **3** | 617 | 8 | `█` |
| 2026-08-31 | 3 | 2 | **5** | 688 | 22 | `██` |
| 2026-09-01 | 3 | 0 | **3** | 0 | 2 | `█` |
| 2026-09-02 | 1 | 1 | **2** | 18 | 1 | `█` |

---

## 4. Top posts — DeepSeek V4 Pro

### 4.1 TikTok (ranked by views)

| # | Creator | Date | Views | Likes | Comments | Shares | ER | Post | Caption |
|---|---|---|--:|--:|--:|--:|--:|---|---|
| 1 | @sxechina | 2026-05-24 | 751,276 | 32,180 | 816 | 3,632 | 5.71% | [open](https://www.tiktok.com/@sxechina/video/7643412561517464854) | DeepSeek Makes 75% Price Cut PERMANENT. 88 Cents Per Million Tokens #news #technology #china #ai #deepseek De… |
| 2 | @kz_lemon4ik | 2026-08-26 | 200,509 | 20,315 | 430 | 801 | 12.36% | [open](https://www.tiktok.com/@kz_lemon4ik/video/7678404666404654369) | glm 5.3 flash, ox alpha, deepseek v4 pro flash сравнение |
| 3 | @barneslucas_ | 2026-04-24 | 132,358 | 5,007 | 232 | 249 | 4.91% | [open](https://www.tiktok.com/@barneslucas_/video/7632405284085910804) | DeepSeek V4-Pro is the cheapest SOTA model at 1/20th the cost of Opus4.7 #deepseek #claude #aitools #claudeco… |
| 4 | @sky.wav | 2026-08-13 | 80,963 | 1,973 | 47 | 120 | 3.12% | [open](https://www.tiktok.com/@sky.wav/video/7673455428180757782) | Surprisingly, DeepSeek V4 Flash 0731 beats the Pro 0813 at canvas coding #deepseekv4 #deepseekvschatgpt #aimo… |
| 5 | @ks40m | 2026-08-24 | 74,590 | 2,025 | 181 | 269 | 4.43% | [open](https://www.tiktok.com/@ks40m/video/7677584894347824391) | Deepseek v4 Pro làm AutoCAD đỉnh quá @AI nào hay? #AI #autocad #kysuxaydung #deepseek #kysunhatban |
| 6 | @vietnhan.nguyen2711 | 2026-05-23 | 45,143 | 1,163 | 51 | 133 | 3.77% | [open](https://www.tiktok.com/@vietnhan.nguyen2711/video/7643035872073403664) | DeepSeek V4-Pro: Flagship xịn ngang Opus nhưng giá chỉ bằng "bát trà đá" #DeepSeekV4Pro #OpenAI #Anthropic #A… |
| 7 | @escbasexyz | 2026-05-23 | 40,346 | 976 | 48 | 107 | 3.31% | [open](https://www.tiktok.com/@escbasexyz/video/7642892200824605960) | 💸 DeepSeek-V4-Pro không còn giảm giá tạm thời nữa: mức 75% off sẽ thành giá API chính thức. 📊 DeepSeek đang… |
| 8 | @future.with.ai98 | 2026-04-24 | 29,572 | 710 | 38 | 39 | 3.39% | [open](https://www.tiktok.com/@future.with.ai98/video/7632174089372830984) | China just dropped DeepSeek V4 🚀 It includes four new models: Pro, Flash, V4 Pro Base and Flash Base. This c… |
| 9 | @asepclaude.code | 2026-05-27 | 29,229 | 1,272 | 63 | 69 | 6.00% | [open](https://www.tiktok.com/@asepclaude.code/video/7644519848092945672) | POV: AI lagi perang harga dan kita pusing mau pakai model yang mana😝 DeepSeek V4 Pro → diskon 75% permanen, … |
| 10 | @gu.ferrey | 2026-04-28 | 26,104 | 1,326 | 70 | 461 | 12.50% | [open](https://www.tiktok.com/@gu.ferrey/video/7633613339079281927) | Te enseño cómo correr OpenClaw sin pagar un centavo. DeepSeek V4 Pro + Nvidia API = asistente de IA gratis qu… |
| 11 | @gigaqian | 2026-08-02 | 24,869 | 1,584 | 87 | 82 | 8.58% | [open](https://www.tiktok.com/@gigaqian/video/7669579546022235406) | DeepSeek just released a new version of their V4 Flash model with a massive upgrade in agentic performance! T… |
| 12 | @sky.wav | 2026-07-01 | 23,063 | 668 | 21 | 38 | 4.25% | [open](https://www.tiktok.com/@sky.wav/video/7657413372455046422) | Speed vs Quality test 🔥 #glm52 #fable5 #deepseek #aitest #aimodel run a test between OS model with /design f… |
| 13 | @baodiep244 | 2026-06-09 | 22,622 | 615 | 21 | 40 | 4.24% | [open](https://www.tiktok.com/@baodiep244/video/7649511064329096462) | The Open-Source AI Shake: DeepSeek V4 Pro at 1.6T Parameters Redefines Open AI — But Do Benchmarks Matter? He… |
| 14 | @justinbuilds.mov | 2026-04-24 | 18,353 | 940 | 51 | 60 | 6.98% | [open](https://www.tiktok.com/@justinbuilds.mov/video/7632302915465596174) | Deepseek V4 Pro beats Claude, Gemini, and ChatGPT |
| 15 | @wingtech.vn | 2026-05-24 | 16,939 | 447 | 23 | 70 | 3.70% | [open](https://www.tiktok.com/@wingtech.vn/video/7643295185689906452) | DeepSeek vừa cắt giá API 75% — và đây là giá VĨNH VIỄN 😳 V4 Pro giờ rẻ hơn GPT-5.5 với Claude Opus tới 20-30… |
| 16 | @courspora | 2026-08-17 | 14,925 | 736 | 21 | 61 | 8.69% | [open](https://www.tiktok.com/@courspora/video/7675031875374550293) | info free ai model deepseek v4 pro yang terbaru buat kebutuhan ngoding buat yang kehabisan token wkwk #vibeco… |
| 17 | @ai_programer | 2026-05-10 | 14,320 | 129 | 3 | 18 | 1.60% | [open](https://www.tiktok.com/@ai_programer/video/7638257790779149584) | DeepSeek写代码4.72亿Token成本实测用DeepSeek V4Pro在ClaudeCode里写了一天代码，缓存命中很高，成本低得离谱。下一期看看它到底写出了什么工具 #ai #软件开发 #程序员 #编程 |
| 18 | @vibewp.vn | 2026-08-18 | 11,007 | 519 | 31 | 53 | 8.19% | [open](https://www.tiktok.com/@vibewp.vn/video/7675203828538510600) | KiraAI.vn đang mở miễn phí API DeepSeek V4 Pro và V4 Flash#kiraai |
| 19 | @sky.wav | 2026-08-14 | 10,990 | 137 | 9 | 25 | 1.85% | [open](https://www.tiktok.com/@sky.wav/video/7673727865661263126) | Gemini 3.7 Flash vs DeepSeek v4 Pro tested both models with same prompt on highest reasoning > 3.7 flash took… |
| 20 | @aidev.news | 2026-08-13 | 10,112 | 260 | 13 | 11 | 3.35% | [open](https://www.tiktok.com/@aidev.news/video/7673393754182585620) | DeepSeek thả model mạnh nhất của họ mà không một dòng thông báo — và giá đầu ra rẻ hơn Claude Opus 5 gần 30 l… |
| 21 | @botplease.me | 2026-08-17 | 7,978 | 316 | 9 | 35 | 6.47% | [open](https://www.tiktok.com/@botplease.me/video/7673812753705897233) | DeepSeek อัพเดทใหม่แล้ว รอบนี้มีทั้ง DeepSeek V4 Pro และ DeepSeek Harness ที่เป็น Open Source Agent Framework… |
| 22 | @torticodeyt | 2026-08-15 | 6,178 | 252 | 2 | 5 | 5.08% | [open](https://www.tiktok.com/@torticodeyt/video/7674309006743080214) | El cache de DeepSeek Pro te va a costar más de 12 veces en hora pico. El 16 de agosto a las 16 UTC. El modelo… |
| 23 | @carlos_bumeran | 2026-08-14 | 5,701 | 207 | 4 | 17 | 5.30% | [open](https://www.tiktok.com/@carlos_bumeran/video/7673977499344194836) | DeepSeek V4 PRO ya llegó: ¿qué cambia para agentes y Codex? 🤖 #InteligenciaArtificial #Programacion #ClaudeC… |
| 24 | @future.with.ai98 | 2026-08-19 | 5,695 | 232 | 3 | 21 | 7.52% | [open](https://www.tiktok.com/@future.with.ai98/video/7675716247861939463) | DeepSeek V4 Pro just became ridiculously easy to access. It’s available through Arena AI, alongside 50+ power… |
| 25 | @ai.sang.nay | 2026-07-05 | 5,439 | 135 | 0 | 13 | 3.86% | [open](https://www.tiktok.com/@ai.sang.nay/video/7659017026832207125) | Một model AI top giờ tải free về máy: DeepSeek V4-Pro, license MIT, 1.6T params nhưng chỉ 49B chạy mỗi token.… |
| 26 | @marcobuilds | 2026-08-13 | 5,185 | 190 | 16 | 47 | 7.23% | [open](https://www.tiktok.com/@marcobuilds/video/7673529595060096289) | Claude e ChatGPT hanno un rivale che costa quasi zero. Si chiama DeepSeek V4 Pro, è open weight (pesi scarica… |
| 27 | @robsoliveirah | 2026-04-27 | 5,118 | 159 | 12 | 28 | 6.51% | [open](https://www.tiktok.com/@robsoliveirah/video/7633528583884934408) | Como usar o DEEPSEEK V4 PRO e outros modelos gratuitos dentro do Claude Code sem gastar NADA! #CLAUDECODE #de… |
| 28 | @denyme301 | 2026-04-26 | 4,958 | 61 | 2 | 2 | 1.59% | [open](https://www.tiktok.com/@denyme301/video/7632795657056668929) | DeepSeek V4-Pro-Max against GLM-5.1 on 500 real prompts from the same dataset. Same questions, two models — h… |
| 29 | @future.with.ai98 | 2026-08-14 | 4,516 | 127 | 4 | 7 | 4.01% | [open](https://www.tiktok.com/@future.with.ai98/video/7673881969729555719) | China just dropped DeepSeek V4 Pro. And the price-to-performance could be ridiculous. It’s competing with fro… |
| 30 | @kcdew | 2026-07-02 | 4,505 | 2 | 0 | 0 | 0.04% | [open](https://www.tiktok.com/@kcdew/video/7657913749252181255) | ฝนตกรถติดเป็นอะไรที่แก้ยากมากภูเก็ต #creatorsearchinsights #deepseekv4pro #chatbot #ai |

### 4.2 Instagram (ranked by likes + comments)

| # | Creator | Date | Likes | Comments | Post | Caption |
|---|---|---|--:|--:|---|---|
| 1 | @devcode.ai | 2026-04-27 | 5,493 | 112 | [open](https://www.instagram.com/p/DXoZrjnDmo2/) | DeepSeek V4 baru aja rilis, dan kali ini perang harga AI bakal makin rusak! 🔥 DeepSeek V4 hadir buat buktiin kalau model open-so… |
| 2 | @devzonex.dev | 2026-08-17 | 1,121 | 1,799 | [open](https://www.instagram.com/p/DcJNkt5TVb8/) | DeepSeek V4 Pro Free ✅ You can create api and plug it directly in Claude Code 🚀 Comment "pro" to get link in your DM #deepseekv4… |
| 3 | @infomoney | 2026-05-23 | 1,228 | 30 | [open](https://www.instagram.com/p/DYsMDZhltfh/) | PREÇOS EM UM QUARTO DE SEU NÍVEL ORIGINAL A startup chinesa de inteligência artificial DeepSeek anunciou um corte permanente de 7… |
| 4 | @tech_wizzdom | 2026-04-27 | 648 | 17 | [open](https://www.instagram.com/p/DXn6pqJFU7u/) | DeepSeek R1 was one of the most hyped models last year - because it delivered the power of flagship models at a fraction of the c… |
| 5 | @appcrunktechnologies | 2026-08-26 | 450 | 0 | [open](https://www.instagram.com/p/DcglvtEAUEC/) | AI is getting smaller, smarter, faster — and much more accessible. 🚀 From cloud AI to edge AI, intelligence is moving closer to … |
| 6 | @jarrus.ai | 2026-08-16 | 292 | 18 | [open](https://www.instagram.com/p/DcGIrR8l_bc/) | DeepSeek, küresel AI fiyat savaşını başlatan şirketti. Şimdi o savaşı kendi eliyle bitiriyor. 6 Ağustos'ta fiyat sayfasına sessiz… |
| 7 | @businessfocus.io | 2026-04-24 | 298 | 10 | [open](https://www.instagram.com/p/DXgxCNZDZqH/) | DeepSeek V4重磅發布免費開源！單挑GPT-5.5顛覆成本底線 估值直逼2000億 阿里騰訊雷軍爭相入局背後藏隱憂？【 @businessfocus.io 】【#BF社會熱話】 AI界再度拋出震撼彈！中國人工智能巨頭DeepSeek（深度求索）無預警… |
| 8 | @aiadventureryt | 2026-08-14 | 276 | 4 | [open](https://www.instagram.com/p/DcBuJvSlGUX/) | DeepSeek V4-Pro went GA yesterday. 1.6 trillion parameters. 1M token context as the default across every service, not a paid add-… |
| 9 | @aifocus.io | 2026-04-25 | 209 | 0 | [open](https://www.instagram.com/p/DXiUg67FM7j/) | 【 @aifocus.io 】GPT大戰DeepSeek 新模型同時發布！OpenAI收費翻倍 vs 中國國產開源免費，邊個先係Agent真王者？ 2026年4月24日，全球AI界迎來史無前例大地震 ！OpenAI與中國大模型黑馬DeepSeek竟然極度默契… |
| 10 | @distributionshow | 2026-08-14 | 75 | 1 | [open](https://www.instagram.com/p/DcBvQvhjM6m/) | DeepSeek has launched V4 Pro, its new flagship AI model, with a major jump in capability over the cheaper V4 Flash. The model is … |
| 11 | @dll.technology | 2026-08-13 | 74 | 1 | [open](https://www.instagram.com/p/Db_Wu0jDSw-/) | DeepSeek yeni amiral gemisi modelini duyurdu. Aynı gün fiyatlara zam geldi. V4 Pro 12 Ağustos'ta genel kullanıma açıldı. 1,6 tril… |
| 12 | @triwicaksono_com | 2026-08-29 | 64 | 0 | [open](https://www.instagram.com/p/DcncsJViYId/) | Sesuai dugaan, Ox-Alpha itu AI Model dari GLM 🔥 Dan sekarang resmi diannounce sebagai GLM 5.3 dan GLM 5.3 Flash. Akses langsung … |
| 13 | @_aixlab_ | 2026-08-14 | 46 | 0 | [open](https://www.instagram.com/p/DcBO5NRjKEc/) | Çinin aparıcı AI şirkətlərindən DeepSeek rəsmi olaraq V4 Pro modelini təqdim edib. Bununla yanaşı, şirkət V4 Pro və V4 Flash API … |
| 14 | @moescapeai | 2026-04-30 | 42 | 0 | [open](https://www.instagram.com/p/DXxIX-_D4x-/) | 📢 Price Update: DeepSeek V4 Pro Hey Moescaper Great news! We’ve reduced the price of DeepSeek V4 Pro and promo & earned Mochi ar… |
| 15 | @fortuneinsight | 2026-08-14 | 37 | 1 | [open](https://www.instagram.com/p/DcBelNwgPGt/) | 內地人工智能大模型DeepSeek宣布，隨着DeepSeek V4全系列模型正式版上線，將會由下周一（8月17日）零時起調整API定價。為了更合理地調配系統資源，DeepSeek將引入峰谷定價機制，閒時價格定為高峰時段的一半，以鼓勵用戶根據實際需求調整使用時… |
| 16 | @software.engineer.tn | 2026-08-08 | 37 | 0 | [open](https://www.instagram.com/p/DbyUJI4Co2r/) | Deepseek V4 Pro Flash just dropped! 🤯 A Chinese AI lab released a model reportedly 99% more powerful than Anthropic's top AI, ma… |
| 17 | @sartechlabs | 2026-05-25 | 27 | 1 | [open](https://www.instagram.com/p/DYxVN5tmbWg/) | 🚀 കിടിലൻ AI മോഡലായ DeepSeek V4 Pro-യുടെ വില കമ്പനി 75% കുറച്ചു! ഈ price drop ഇനി permanent ആണ്! നേരത്തെ നൽകിയിരുന്ന ഡിസ്കൗണ്ട് ന… |
| 18 | @aiproductlabs | 2026-05-23 | 24 | 0 | [open](https://www.instagram.com/p/DYqt7MkjXOW/) | DeepSeek has permanently reduced API pricing for DeepSeek-V4-Pro by up to 75%, making high-performance reasoning models significa… |
| 19 | @camacarinoticias | 2026-08-13 | 17 | 0 | [open](https://www.instagram.com/p/Db_RSiwv2px/) | A corrida pela liderança da Inteligência Artificial ganhou um novo capítulo de peso! A startup chinesa DeepSeek lançou nesta quin… |
| 20 | @jarrus.tech | 2026-08-16 | 15 | 1 | [open](https://www.instagram.com/p/DcGI3wjF5Iz/) | DeepSeek started the global AI price war. Now it's ending it itself. On August 6 the company quietly added a line to its pricing … |
| 21 | @md.vip.official | 2026-04-27 | 11 | 4 | [open](https://www.instagram.com/p/DXoUqfmkeif/) | 💥 英偉達 (Nvidia) 霸權迎來最大危機？DeepSeek-V4 出招，API 平過 GPT 九成！😱 近期 AI 圈最震撼嘅大新聞，絕對非 DeepSeek-V4 莫屬！佢唔單止係一個勁揪嘅新 Model，更加係中美 AI 算力博弈嘅超級轉捩點。… |
| 22 | @pro_pakistani | 2026-04-25 | 11 | 0 | [open](https://www.instagram.com/p/DXjT1Z7j_01/) | Chinese AI company DeepSeek has released a preview of its latest model, called DeepSeek-V4, more than a year after it gained atte… |
| 23 | @lightningsolutions.dev | 2026-08-12 | 11 | 0 | [open](https://www.instagram.com/p/Db9O68DASLI/) | 🔥 ¿Tenemos un nuevo rey en el mundo de los Agentes de IA? Los nuevos benchmarks oficiales de DeepSeek-V4-Pro acaban de salir y l… |
| 24 | @akshaybandivadekr | 2026-04-24 | 10 | 0 | [open](https://www.instagram.com/p/DXhq9ToCIsN/) | 🤯 DeepSeek just dropped a 1.6 TRILLION parameter model — and it's cheaper than Claude Haiku. Here's what you need to know about … |
| 25 | @startup360.ir | 2026-08-19 | 10 | 0 | [open](https://www.instagram.com/p/DcOg5HJjNf-/) | چرا هوش مصنوعی ارزان چین مایه نگرانی سیلیکون‌ولی شده است؟ به گزارش بلومبرگ، شرکت‌های چینی مانند DeepSeek، Alibaba و Moonshot با و… |
| 26 | @arbenidas_ | 2026-08-13 | 9 | 1 | [open](https://www.instagram.com/p/Db_bRUBmnjx/) | El 13 de agosto salieron dos modelos. No el mismo trabajo. DeepSeek-V4-Pro es GA. El id sigue: deepseek-v4-pro. Effort low / high… |
| 27 | @melihmacit.ai | 2026-08-24 | 9 | 0 | [open](https://www.instagram.com/p/Dca7_QxDFWs/) | DeepSeek V4 Pro sessizce yayınlandı ve token başına fiyat çıtasını bir kademe daha aşağı çekti: 1 milyon token için sadece $0.435… |
| 28 | @llatarochnoticias | 2026-08-13 | 8 | 1 | [open](https://www.instagram.com/p/Db-4tE4jWSQ/) | DeepSeek lanzó DeepSeek-V4-Pro-0813 en versión GA para app, web y API, con mejoras enfocadas en agentes, desarrollo de software y… |
| 29 | @renatoserra.bcosta | 2026-04-28 | 9 | 0 | [open](https://www.instagram.com/p/DXqArJ9EVX_/) | O DeepSeek V4-Pro chegou e a pergunta é uma só: a sua IA atual está te cobrando caro por algo que você pode ter de um jeito muito… |
| 30 | @amcfoss | 2026-08-21 | 9 | 0 | [open](https://www.instagram.com/p/DcTng_aE-m2/) | 🚀 *AGENT HARNESS & FOUNDATION MODELS* Dive into *DeepSeek’s Code Clash* as we unpack the world of *DeepSeek Harness & V4-Pro*! �… |

---

## 5. Top creators (on-target posts)

### 5.1 TikTok — by views

| # | Creator | Followers | On-target posts | Views | Views ÷ followers | Likes | Comments |
|---|---|--:|--:|--:|--:|--:|--:|
| 1 | [@sxechina](https://www.tiktok.com/@sxechina) | 26,090 | 2 | 755,578 | 29.0× | 32,338 | 818 |
| 2 | [@kz_lemon4ik](https://www.tiktok.com/@kz_lemon4ik) | 169,986 | 1 | 200,509 | 1.2× | 20,315 | 430 |
| 3 | [@barneslucas_](https://www.tiktok.com/@barneslucas_) | 773 | 1 | 132,358 | 171.2× | 5,007 | 232 |
| 4 | [@sky.wav](https://www.tiktok.com/@sky.wav) | 9,783 | 3 | 115,016 | 11.8× | 2,778 | 77 |
| 5 | [@ks40m](https://www.tiktok.com/@ks40m) | 20,831 | 2 | 76,990 | 3.7× | 2,067 | 189 |
| 6 | [@vietnhan.nguyen2711](https://www.tiktok.com/@vietnhan.nguyen2711) | 791 | 1 | 45,143 | 57.1× | 1,163 | 51 |
| 7 | [@escbasexyz](https://www.tiktok.com/@escbasexyz) | 3,967 | 2 | 44,841 | 11.3× | 1,035 | 49 |
| 8 | [@future.with.ai98](https://www.tiktok.com/@future.with.ai98) | 19,632 | 4 | 41,130 | 2.1× | 1,140 | 48 |
| 9 | [@asepclaude.code](https://www.tiktok.com/@asepclaude.code) | 155 | 1 | 29,229 | 188.6× | 1,272 | 63 |
| 10 | [@gu.ferrey](https://www.tiktok.com/@gu.ferrey) | 25,430 | 1 | 26,104 | 1.0× | 1,326 | 70 |
| 11 | [@gigaqian](https://www.tiktok.com/@gigaqian) | 159,832 | 1 | 24,869 | 0.2× | 1,584 | 87 |
| 12 | [@baodiep244](https://www.tiktok.com/@baodiep244) | 16,744 | 1 | 22,622 | 1.4× | 615 | 21 |
| 13 | [@justinbuilds.mov](https://www.tiktok.com/@justinbuilds.mov) | 16,201 | 1 | 18,353 | 1.1× | 940 | 51 |
| 14 | [@wingtech.vn](https://www.tiktok.com/@wingtech.vn) | 1,538 | 1 | 16,939 | 11.0× | 447 | 23 |
| 15 | [@courspora](https://www.tiktok.com/@courspora) | 23,189 | 1 | 14,925 | 0.6× | 736 | 21 |
| 16 | [@ai_programer](https://www.tiktok.com/@ai_programer) | 35,911 | 1 | 14,320 | 0.4× | 129 | 3 |
| 17 | [@vibewp.vn](https://www.tiktok.com/@vibewp.vn) | 536 | 1 | 11,007 | 20.5× | 519 | 31 |
| 18 | [@aidev.news](https://www.tiktok.com/@aidev.news) | 4,129 | 1 | 10,112 | 2.4× | 260 | 13 |
| 19 | [@botplease.me](https://www.tiktok.com/@botplease.me) | 20,643 | 1 | 7,978 | 0.4× | 316 | 9 |
| 20 | [@torticodeyt](https://www.tiktok.com/@torticodeyt) | 22,209 | 1 | 6,178 | 0.3× | 252 | 2 |
| 21 | [@carlos_bumeran](https://www.tiktok.com/@carlos_bumeran) | 5,366 | 1 | 5,701 | 1.1× | 207 | 4 |
| 22 | [@ai.sang.nay](https://www.tiktok.com/@ai.sang.nay) | 1,546 | 1 | 5,439 | 3.5× | 135 | 0 |
| 23 | [@marcobuilds](https://www.tiktok.com/@marcobuilds) | 8,570 | 1 | 5,185 | 0.6× | 190 | 16 |
| 24 | [@robsoliveirah](https://www.tiktok.com/@robsoliveirah) | 321 | 1 | 5,118 | 15.9× | 159 | 12 |
| 25 | [@denyme301](https://www.tiktok.com/@denyme301) | 19 | 1 | 4,958 | 260.9× | 61 | 2 |

### 5.2 Instagram — by likes + comments

| # | Creator | Followers | On-target posts | Likes | Comments |
|---|---|--:|--:|--:|--:|
| 1 | [@devcode.ai](https://www.instagram.com/devcode.ai/) ✓ | 26,616 | 1 | 5,493 | 112 |
| 2 | [@devzonex.dev](https://www.instagram.com/devzonex.dev/) | 8,858 | 1 | 1,121 | 1,799 |
| 3 | [@infomoney](https://www.instagram.com/infomoney/) ✓ | 2,846,835 | 1 | 1,228 | 30 |
| 4 | [@tech_wizzdom](https://www.instagram.com/tech_wizzdom/) | 535,436 | 1 | 648 | 17 |
| 5 | [@appcrunktechnologies](https://www.instagram.com/appcrunktechnologies/) | 105 | 1 | 450 | 0 |
| 6 | [@jarrus.ai](https://www.instagram.com/jarrus.ai/) ✓ | 40,149 | 1 | 292 | 18 |
| 7 | [@businessfocus.io](https://www.instagram.com/businessfocus.io/) ✓ | 289,338 | 1 | 298 | 10 |
| 8 | [@aiadventureryt](https://www.instagram.com/aiadventureryt/) | 139,909 | 1 | 276 | 4 |
| 9 | [@aifocus.io](https://www.instagram.com/aifocus.io/) | 12,654 | 1 | 209 | 0 |
| 10 | [@distributionshow](https://www.instagram.com/distributionshow/) | 141,383 | 1 | 75 | 1 |
| 11 | [@dll.technology](https://www.instagram.com/dll.technology/) | 1,407 | 1 | 74 | 1 |
| 12 | [@triwicaksono_com](https://www.instagram.com/triwicaksono_com/) ✓ | 18,351 | 1 | 64 | 0 |
| 13 | [@_aixlab_](https://www.instagram.com/_aixlab_/) | 1,058 | 1 | 46 | 0 |
| 14 | [@moescapeai](https://www.instagram.com/moescapeai/) | 26,645 | 1 | 42 | 0 |
| 15 | [@fortuneinsight](https://www.instagram.com/fortuneinsight/) | 68,609 | 1 | 37 | 1 |
| 16 | [@software.engineer.tn](https://www.instagram.com/software.engineer.tn/) | 23,735 | 1 | 37 | 0 |
| 17 | [@sartechlabs](https://www.instagram.com/sartechlabs/) | 19,994 | 1 | 27 | 1 |
| 18 | [@aiproductlabs](https://www.instagram.com/aiproductlabs/) | 25,508 | 1 | 24 | 0 |
| 19 | [@thefacts.digital](https://www.instagram.com/thefacts.digital/) | 133 | 3 | 18 | 0 |
| 20 | [@pro_pakistani](https://www.instagram.com/pro_pakistani/) ✓ | 193,644 | 2 | 17 | 0 |
| 21 | [@camacarinoticias](https://www.instagram.com/camacarinoticias/) ✓ | 184,975 | 1 | 17 | 0 |
| 22 | [@jarrus.tech](https://www.instagram.com/jarrus.tech/) | 112 | 1 | 15 | 1 |
| 23 | [@md.vip.official](https://www.instagram.com/md.vip.official/) | 1,248 | 1 | 11 | 4 |
| 24 | [@lightningsolutions.dev](https://www.instagram.com/lightningsolutions.dev/) | 26 | 1 | 11 | 0 |
| 25 | [@akshaybandivadekr](https://www.instagram.com/akshaybandivadekr/) | 1,315 | 1 | 10 | 0 |

_Instagram handles are shown only where the owner id was resolved within budget (§8.4); unresolved owners are excluded from this table but still counted everywhere else._

---

## 6. Context: the wider V4 conversation

### 6.1 Top V4 **Flash** posts (sibling model — for comparison)

| # | Creator | Date | Views | Likes | Comments | Shares | ER | Post | Caption |
|---|---|---|--:|--:|--:|--:|--:|---|---|
| 1 | @sustainment | 2026-08-09 | 303,122 | 28,347 | 568 | 2,278 | 12.34% | [open](https://www.tiktok.com/@sustainment/video/7671866754812972310) | "just be open source" brutal Many still assume the frontier is entirely closed-source, with GPT-5.6 Sol and C… |
| 2 | @wuy.iz | 2026-05-15 | 156,085 | 7,227 | 76 | 505 | 7.02% | [open](https://www.tiktok.com/@wuy.iz/video/7640178888445922581) | Dùng DeepSeek V4 Flash, Qwen3.6 Plus,... MIỄN PHÍ 100% Anh em dev đang tốn hàng chục đô mỗi tháng cho các too… |
| 3 | @sky.wav | 2026-07-31 | 119,378 | 3,071 | 142 | 215 | 3.32% | [open](https://www.tiktok.com/@sky.wav/video/7668631522345340182) | DeepSeek-V4-Flash 0731 is now live compare it with GPT-5.6 Luna!! The AI price war is ON. > DeepSeek just dro… |
| 4 | @josevizner | 2026-08-21 | 59,252 | 3,619 | 84 | 188 | 7.19% | [open](https://www.tiktok.com/@josevizner/video/7676467078546722071) | ÚLTIMA HORA: DeepSeek la vuelve a liar. Saca un modelo nuevo que revoluciona el avance de la IA DeepSeek ha s… |
| 5 | @jceronch | 2026-08-01 | 55,630 | 2,721 | 61 | 349 | 9.10% | [open](https://www.tiktok.com/@jceronch/video/7668847284796312853) | 🚀 DeepSeek V4 Flash GRATIS 🤖 Si buscas una alternativa libre a Cursor o Claude Desktop, OpenCode te permite… |
| 6 | @sustainment | 2026-08-16 | 44,710 | 3,942 | 145 | 430 | 11.87% | [open](https://www.tiktok.com/@sustainment/video/7674601533605940502) | Art by @Kedr.bit GPT-5.6 Luna was supposed to be a "cost-efficient" model, but when compared to DeepSeek V4 F… |
| 7 | @future.with.ai98 | 2026-04-26 | 41,033 | 1,200 | 28 | 185 | 5.99% | [open](https://www.tiktok.com/@future.with.ai98/video/7633039478814264584) | DeepSeek V4 Flash just made Hermes free forever 🚀 Install Ollama, select DeepSeek V4 Flash and launch Hermes… |
| 8 | @momus.ai | 2026-08-26 | 30,140 | 850 | 157 | 13 | 3.90% | [open](https://www.tiktok.com/@momus.ai/video/7678368309045218591) | Replying to @Momus - Local AI Lab Been trying out a DeepSeek V4 Flash 1M profile on a single ASUS Ascent GX10… |
| 9 | @jceronch | 2026-08-13 | 28,520 | 1,256 | 49 | 163 | 7.77% | [open](https://www.tiktok.com/@jceronch/video/7673654877448342804) | ¡Conecté 5 inteligencias artificiales en tiempo real a Blender! 🤖🔥 Todo corriendo en vivo gracias al protoc… |
| 10 | @estevao.soares | 2026-08-13 | 27,766 | 1,800 | 78 | 294 | 10.82% | [open](https://www.tiktok.com/@estevao.soares/video/7673590416754642196) | Minhas primeiras impressões do DeepSeek v4 Flash. Ontem saiu também a versão Pro, assim que testar eu compart… |

### 6.2 Top V4 (variant unspecified) posts

| # | Creator | Date | Views | Likes | Comments | Shares | ER | Post | Caption |
|---|---|---|--:|--:|--:|--:|--:|---|---|
| 1 | @sky.wav | 2026-06-05 | 387,651 | 13,814 | 184 | 703 | 5.05% | [open](https://www.tiktok.com/@sky.wav/video/7647846884333079830) | very impressive results - Compared it with 3 frontier models: DeepSeek V4, MiniMax M3, and Qwen 3.7 Max on 2 … |
| 2 | @kz_lemon4ik | 2026-04-25 | 243,949 | 23,983 | 546 | 1,568 | 11.74% | [open](https://www.tiktok.com/@kz_lemon4ik/video/7632770362933300502) | Вышел DeepSeek V4 |
| 3 | @ia360.kl | 2026-05-23 | 68,005 | 2,995 | 15 | 177 | 5.59% | [open](https://www.tiktok.com/@ia360.kl/video/7643024113405005088) | IA Révolution : 3 articles scientifiques, puis un modèle inconnu. L'homme derrière ? Liang Wenfeng, celui qui… |
| 4 | @ai.arenalab | 2026-08-20 | 63,353 | 842 | 57 | 29 | 1.71% | [open](https://www.tiktok.com/@ai.arenalab/video/7676211791805828385) | Same prompt. Four models. One winner. "Single-file HTML/CSS/JavaScript animation of a basketball falling thro… |
| 5 | @chinabymonica | 2026-04-25 | 50,332 | 3,409 | 114 | 673 | 11.13% | [open](https://www.tiktok.com/@chinabymonica/video/7632656963444231455) | DeepSeek V4 Just Killed Nvidia's Real Moat. #deepseek #nvidia#ai #deepseekv4 #chinaai #llm #opensourceai #chi… |
| 6 | @calebwritescode | 2026-05-07 | 50,281 | 3,029 | 24 | 126 | 7.63% | [open](https://www.tiktok.com/@calebwritescode/video/7637005355712630029) | DeepSeek released their new flagship model V4 which yet again shocks the world but not in training cost but t… |
| 7 | @sky.wav | 2026-06-19 | 34,632 | 909 | 45 | 83 | 3.56% | [open](https://www.tiktok.com/@sky.wav/video/7653007161529879830) | Tested Gemini 3.1 Pro, GPT-5.5, DeepSeek V4 & Claude Fable 5 on the Same Prompt - Which model actually wins? … |
| 8 | @andrhlt | 2026-03-02 | 29,246 | 1,479 | 51 | 81 | 6.52% | [open](https://www.tiktok.com/@andrhlt/video/7612710171416055071) | DeepSeek v4 tomorrow AND better than Opus 4.6?? #claude #codex #developer #vibecode #deepseek |
| 9 | @sky.wav | 2026-06-04 | 27,914 | 377 | 5 | 15 | 1.81% | [open](https://www.tiktok.com/@sky.wav/video/7647443814629510402) | Compared MiniMax M3 against three other frontier open-source models: DeepSeek V4, Qwen 3.7 Max, and MiMo 2.5 … |
| 10 | @bycloud_ai | 2026-06-17 | 27,057 | 1,161 | 39 | 51 | 5.77% | [open](https://www.tiktok.com/@bycloud_ai/video/7652424312552475921) | How did deepseek made V4 so cheap? Insane pricing👀 #DeepSeekV4 #AI #LLM #OpenSourceAI #MachineLearning |

---

## 7. What the conversation is about

### 7.1 Themes (on-target posts)

Deterministic keyword buckets over captions — this measures *subject matter*, not sentiment. A post can match several themes, so shares sum past 100%.

| Theme | Posts | Share of on-target | TikTok views |
|---|--:|--:|--:|
| API / deployment | 228 | 44.4% | 900,329 |
| Pricing / cost | 221 | 43.0% | 1,046,867 |
| Coding / dev use | 152 | 29.6% | 352,187 |
| Agents / automation | 110 | 21.4% | 46,772 |
| Open source / weights | 85 | 16.5% | 45,357 |
| Benchmarks / evals | 57 | 11.1% | 251,954 |
| Model comparison | 53 | 10.3% | 900,631 |
| Tutorial / how-to | 31 | 6.0% | 27,718 |

### 7.2 Hashtags co-occurring with V4 Pro posts

| Hashtag | Posts | Share |
|---|--:|--:|
| `#deepseek` | 385 | 74.9% |
| `#ai` | 183 | 35.6% |
| `#deepseekv4` | 143 | 27.8% |
| `#artificialintelligence` | 99 | 19.3% |
| `#llm` | 82 | 16.0% |
| `#technews` | 80 | 15.6% |
| `#deepseekv4pro` | 69 | 13.4% |
| `#machinelearning` | 56 | 10.9% |
| `#inteligenciaartificial` | 51 | 9.9% |
| `#ainews` | 45 | 8.8% |
| `#openai` | 45 | 8.8% |
| `#aiagents` | 44 | 8.6% |
| `#aitools` | 40 | 7.8% |
| `#opensource` | 39 | 7.6% |
| `#ia` | 36 | 7.0% |
| `#opensourceai` | 35 | 6.8% |
| `#claude` | 32 | 6.2% |
| `#aimodels` | 31 | 6.0% |
| `#generativeai` | 30 | 5.8% |
| `#anthropic` | 25 | 4.9% |
| `#chatgpt` | 24 | 4.7% |
| `#gemini` | 24 | 4.7% |
| `#aiagent` | 23 | 4.5% |
| `#tecnologia` | 23 | 4.5% |
| `#v4pro` | 20 | 3.9% |
| `#api` | 20 | 3.9% |
| `#nvidia` | 19 | 3.7% |
| `#futureofai` | 19 | 3.7% |
| `#coding` | 19 | 3.7% |
| `#innovation` | 16 | 3.1% |

### 7.3 Caption script mix (on-target)

| Script | Posts | Share |
|---|--:|--:|
| Latin/other | 391 | 76.1% |
| CJK | 48 | 9.3% |
| Thai | 23 | 4.5% |
| Korean | 23 | 4.5% |
| Arabic | 16 | 3.1% |
| Cyrillic | 13 | 2.5% |

---

## 8. Limitations

1. **Instagram like counts are largely hidden.** Only 48.8% of Instagram hashtag-feed posts carried a visible like count. Instagram totals in this report are therefore **lower bounds**, and Instagram posts are ranked on the engagement that *is* visible.
2. **Instagram has no caption search.** The provider exposes hashtag feeds only, so an Instagram post discussing V4 Pro **without** a DeepSeek hashtag is invisible to this method. TikTok's `/feed/search` does match caption text, which is why TikTok coverage is more complete.
3. **`#deepseek` was sampled, not exhausted.** That tag holds ~165,298 posts; **40 pages (1,311 posts)** were swept to catch V4 Pro posts that skipped the V4-specific tags — a 0.79% sample. Deeper sweeps would raise Instagram counts further; the on-target total here is a floor.
4. **Instagram author handles cost one API call each.** `/tag-feeds` returns only a numeric `owner_id`, so handles were resolved for the highest-priority posts within budget; the rest show as `id:<owner_id>`.
5. **TikTok follower counts cover the top creators only.** `/feed/search` and `/challenge/posts` return no follower count, so it was fetched per-author (most-viewed first) within budget: **73 of 137 on-target TikTok posts (53.3%)** carry one. The "views ÷ followers" column and headline finding 6 are computed only over that subset.
6. **TikTok search pages overlap** (~30% repeats between consecutive cursors). Deduplication is by `video_id`, so counts here are of distinct posts.
7. **Engagement is a point-in-time snapshot** taken at collection. Launch-window content is still accruing views; re-running the tracker will move these numbers.
8. **No sentiment analysis.** Posts are classified by *which model they name* and *what they discuss* (§7.1), not by whether they praise or criticise it. A high post count is attention, not approval.
9. **Themes are keyword buckets, not a classifier.** §7.1 uses fixed regex families over caption text. Captions are often short or emoji-heavy, so themes under-count rather than over-count, and a post may land in several buckets.
10. **Reach is not deduplicated across surfaces.** A post found under several hashtags is stored once (deduped by post id), but view/like totals are per-post snapshots and are not adjusted for audience overlap between creators.

---

## 9. Reproducing this run

```bash
# 1. collect — writes output/deepseek_v4_pro_raw_<date>.json
node scripts/track_model.js --max-owners 110

# 2. deepen — extra surfaces + deeper paging, MERGED into the same artifact
node scripts/track_model.js --deep --merge --max-owners 150

# 3. enrich — TikTok follower counts for the most-viewed authors
node scripts/enrich_authors.js --max 60

# 4. verify + re-classify (free: no API calls, runs off stored captions)
node scripts/test_matcher.js
node scripts/retier_artifact.js

# 5. render this report, and persist to Postgres
node scripts/report_model.js
node scripts/persist_model_posts.js
```

Each stage is separable on purpose. Collection is the only step that spends API budget, so classification, analysis and rendering all run off the stored artifact — a matcher change costs nothing to apply retroactively (§2.2).

### Outputs

| Artifact | Contents |
|---|---|
| `C:/Users/anooj/Instagram tracker/output/deepseek_v4_pro_raw_2026-09-02.json` | **2,699 posts** — full metrics, captions, URLs, per-surface provenance |
| `model_mentions` (Postgres) | same rows, keyed `(model, platform, post_id)` for longitudinal re-runs |
| this file | the analysis |

### Code added for this experiment

| File | Role |
|---|---|
| `src/providers/rapidapi_instagram_tagfeed.js` | Instagram `/tag-feeds` adapter (hashtag post feed + owner resolution) |
| `src/providers/rapidapi_tiktok_search.js` | TikTok `/feed/search` + `/challenge/posts` adapter |
| `src/model_tracking/matcher.js` | boundary-aware model-name matcher, tiered |
| `scripts/track_model.js` | cross-platform collection orchestrator |
| `scripts/enrich_authors.js` | TikTok follower-count enrichment |
| `scripts/retier_artifact.js` | free re-classification of a stored artifact |
| `scripts/test_matcher.js` | 23-case matcher regression suite |
| `scripts/report_model.js` | this report |
| `scripts/persist_model_posts.js` | Postgres persistence (`model_mentions`) |

Re-running the tracker on a later date produces a second dated artifact and a second set of `model_mentions` rows, making view/like growth measurable over time.
