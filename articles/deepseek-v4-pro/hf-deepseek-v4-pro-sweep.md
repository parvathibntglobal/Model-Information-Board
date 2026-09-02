# DeepSeek V4 Pro on Hugging Face — retrieval sweep

Swept 2026-09-02 · window **2026-03-02 → 2026-09-02** where a date exists · Hub API (`huggingface.co/api`), anonymous reads, no token

## Headline counts, per surface

| Surface | Found | Usable | What it actually is |
| --- | ---: | ---: | --- |
| Model repos | 295 | 4 official | vendor artefacts; cards are announcements |
| Model cards | 264/295 (89%) | 4 | every number is a vendor claim |
| Discussions | 281 (230 non-PR) | 22 with ≥2 artifacts | the only first-hand surface |
| Papers | 32 | 15 with ≥2 artifacts | abstracts only; no comment text exposed |

- **Model repos:** 295 carry `v4-pro` in the id — **4 official** (`deepseek-ai/*`) and 291 community re-uploads, mostly quantisations. 1,404,100 downloads in total. 31/295 (11%) have no model card at all.
- **Discussions:** 281 threads across 18 of 295 repos — 18/295 (6%) of repos have any discussion whatsoever. 51 are pull requests, leaving 230 real discussions. **257 distinct authors.**
- **First-hand:** 11/152 (7%) of English-language threads report the author's own use. See the language caveat — this is not measurable for the other 129 threads.
- **Artifacts:** 231/281 (82%) of discussions carry **none**. 50/281 (18%) carry ≥1, 22/281 (8%) carry ≥2. The maximum observed is 3 of 6 kinds, against 6 of 6 in article-length material.
- **Papers:** 32 name DeepSeek V4 in title or abstract, 16 name V4 **Pro** specifically. Their author lists name 729 distinct people (paper co-authors, not community participants). Upvotes and comment counts are available; **comment text is not exposed by the API**.
- **Vendor participation:** 8 threads got a reply from one of the 35 `deepseek-ai` org members. Zero threads were opened by one.

## What is thin and what is not

The surfaces fail and succeed in different directions, so a single verdict would be wrong.

**The repo surface is real but it is one artefact, not a corpus.** 295 repos sounds like a lot; 4 of them are the vendor's and the other 291 are re-uploads of the same weights in different quantisations. They do not constitute 291 independent sources — they are one release, repackaged, and 158 of their 261 cards are ≥80% textually identical to the official card (measured below).

**The discussion surface is busy and overwhelmingly trivial.** This is the part the brief expected to carry first-hand reports, and it does carry some — but 231/281 (82%) threads contain nothing checkable, and the median English thread is 112 characters. Much of the volume is congratulation and chatter: threads titled "合影！" (group photo), "贺电贺电" (congratulations). The genuinely useful residue is **22 threads**, and they are good — loader crashes, quantisation size anomalies, tokeniser bugs, a report that the deployed API underperforms the published card.

**The paper surface is the strongest per-item but the API truncates it.** 32 papers name the model family, several with three-figure upvotes. But HF exposes only title, abstract, upvote and comment count — `/api/papers/{id}/comments` and `/discussions` both return **404**. The community layer that makes this surface different from arXiv is precisely the layer that is not retrievable. So this surface reduces to arXiv abstracts plus a popularity number.

### The single most useful item in the sweep

`deepseek-ai/DeepSeek-V4-Pro-0813` discussion #5, titled 这是偷摸改啥文件了，哈哈哈 ("what file did you sneakily change, haha"), traces the repo's commit history to show that the initial `config.json` shipped with **the wrong architecture** — V4-Flash's parameters on the V4-Pro repo — and tabulates the before-and-after:

| Parameter | shipped | corrected |
| --- | ---: | ---: |
| `hidden_size` | 4096 | 7168 |
| `num_hidden_layers` | 43 | 61 |
| `num_attention_heads` | 64 | 128 |
| `n_routed_experts` | 256 | 384 |
| `moe_intermediate_size` | 2048 | 3072 |

This was verified independently during the sweep: the repo's current `config.json` returns `hidden_size` 7168, `num_hidden_layers` 61, `num_attention_heads` 128, `n_routed_experts` 384 and `moe_intermediate_size` 3072 — matching the "corrected" column exactly. The thread is a checkable, first-hand catch of a vendor shipping-error, which is precisely the class of finding a model card can never contain.

It is also written in Chinese, carries no reactions, sits in a repo with 21 discussions, and would be discarded by any English-only filter or any ranking that sorts on engagement.

**Net:** the honest yield is **22 discussion threads** and **4 vendor cards**, plus 32 paper abstracts whose comment threads cannot be read. That is not the "one vendor card and nothing else" outcome the brief allowed for, but it is much closer to that than the raw counts suggest.

## Vendor claims are quarantined, not counted

A model card is the vendor describing its own model. Every number on it is a vendor claim however precise it looks, so card artifacts are reported in their own column and never pooled with community artifacts.

The scale of what that quarantine holds back:

| Card | Benchmark-bearing lines | Artifact kinds | Instances |
| --- | ---: | ---: | --- |
| `deepseek-ai/DeepSeek-V4-Pro` | 29 | 4 | `bench_number`×29, `code_fence`×4, `conditioned_comparison`×60, `version_string`×32 |
| `deepseek-ai/DeepSeek-V4-Pro-0813` | 2 | 4 | `bench_number`×2, `code_fence`×8, `conditioned_comparison`×6, `version_string`×19 |
| `deepseek-ai/DeepSeek-V4-Pro-Base` | — | **no card** |  |
| `deepseek-ai/DeepSeek-V4-Pro-DSpark` | 29 | 4 | `bench_number`×29, `code_fence`×6, `conditioned_comparison`×61, `version_string`×35 |

`deepseek-ai/DeepSeek-V4-Pro` alone carries 29 benchmark-bearing table rows with shot counts and metrics attached — MMLU 5-shot EM, HumanEval Pass@1, C-Eval, CMMLU, MMLU-Pro, DROP F1. On the artifact test that is the single densest document in the sweep, and it is worth exactly nothing as independent evidence: it is the vendor's own scorecard for the vendor's own model.

Counted naively, 200 repos in this sweep "carry benchmark numbers" — a headline that would be almost entirely one company's scorecard, copied. The community total stands at 22/281 (8%) threads carrying two or more artifacts, and nothing on this page moves it.

The same caution extends one step further, and this one is measured rather than assumed. Comparing every community card against the official card by normalised text similarity:

| Community cards vs. the official card | Count |
| --- | ---: |
| Cards compared | 261 |
| ≥80% identical | 158 |
| byte-identical (13,137 chars, 29 benchmark rows) | 21 |
| carrying benchmark lines at all | 197 |

Median similarity is 0.99. **158 of 261 community cards are at least 80% the official card**, and 21 are byte-for-byte copies down to the identical 13,137-character length. 197 community cards carry benchmark lines, median 29 — which is exactly the official table, reproduced.

So the benchmark numbers on a community quantisation repo are the vendor's numbers with a different repo name above them. They are counted as vendor claims, not as 291 independent corroborations. This is the trap the brief warned about, and on this platform it is not a marginal effect: it is most of the sample.

## What the four surfaces actually return

| Endpoint | Status | Returns | Keep? |
| --- | --- | --- | --- |
| `/api/models?search=` | 200 | repo **id** matches, fuzzy and separator-insensitive | yes, with local filtering |
| `/api/models/{id}` + `/raw/main/README.md` | 200 | full metadata; card markdown | yes — but as vendor announcement |
| `/api/models/{id}/discussions` | 200 | **public**, paginated 50/page, mixes PRs with discussions | yes, the only first-hand surface |
| `/api/models/{id}/discussions/{num}` | 200 | full thread, every comment body, HF language tag | yes |
| `/api/papers/search?q=` | 200 | title, abstract, upvotes, comment **count** | partly |
| `/api/papers/{id}/comments` | **404** | — | unavailable |
| `/api/papers/{id}/discussions` | **404** | — | unavailable |
| `/api/arxiv/{id}/repos` | 200 | paper → model repo links (undocumented, useful) | bonus |

### Search is fuzzy, which cuts the other way from dev.to

dev.to ignored `search` silently. Hugging Face honours it but scopes it to the repo id and matches loosely:

| Query | Repos returned |
| --- | ---: |
| `deepseek-v4-pro` | 301 |
| `deepseek v4 pro` | 301 — identical, separators ignored |
| `deepseek_v4_pro` | 301 — identical |
| `deepseek-v4-pro-0813` | 28 |
| `thinking passback` (a phrase in the card body) | **0** — not full-text |
| `zzqqxwvlkj` | **0** — it does filter |
| `deepseek zzz` | **11** — but loosely |

So the parameter works and a nonsense token returns nothing, unlike dev.to. But `deepseek zzz` still returning 11 repos shows it is a fuzzy ranked match rather than a strict filter, and a card-body phrase returning 0 confirms it never reads the card. Both facts force the same method: **query broadly, then filter locally on the id.** Of 1125 repos the queries returned, 295 actually carry `v4-pro` in the id.

**Requests issued:** 1266 (985 for repos, cards and discussion listings; 281 for full threads), plus ~20 probe and paper requests.

**Refused:** 147 refusals, all HTTP 429 rate-limiting on the concurrent repo pass, every one recovered on retry with backoff. 28 hard errors, all HTTP 404 — repos with no `README.md`, which is an absent card rather than a failed request. No token was used. Anonymous limits are usable but **not** as generous as the docs imply: 8 concurrent workers triggered 147 throttles in a 985-request pass, so the polite concurrency ceiling is lower than it looks.

## Read this as retrieval-shaped, not representative

Every figure carries its denominator because the sample was drawn by our own queries.

1. Search never reads card or discussion text, so **the entire sweep is an id-match**. A repo hosting these weights under an unrelated name, and any discussion of the model on an unrelated repo, is invisible to this method.
2. Discussions were only collected for the 295 repos the id-match found. The busiest discussion of a model is often on a *runtime* repo — llama.cpp, vLLM, an inference framework — and none of those are in this sample by construction.
3. `/api/papers/search` caps at 120 results and returned different counts for different phrasings of the same query, so the paper set is a ranked slice, not an enumeration.
4. Community repos are 291/295 (99%) of the sample and are near-duplicates of each other. Counting them as independent items inflates every repo-level figure.

## Language, and a limit on the provenance column

HF tags every comment with a detected language, so this is measured rather than guessed. Across the 503 comment bodies in these threads:

| Language | Comments |
| --- | ---: |
| `en` | 265/503 (53%) |
| `zh` | 181/503 (36%) |
| `ru` | 14/503 (3%) |
| `ja` | 13/503 (3%) |
| `fr` | 7/503 (1%) |
| `de` | 5/503 (1%) |
| `no` | 2/503 (0%) |
| `ceb` | 2/503 (0%) |

| Thread language | Threads | Own-use detected | ≥2 artifacts | Zero artifacts | Median chars |
| --- | ---: | ---: | ---: | ---: | ---: |
| `en` | 152 | 11/152 (7%) | 20/152 (13%) | 110/152 (72%) | 112 |
| `zh` | 101 | 0/101 (0%) | 2/101 (2%) | 94/101 (93%) | 21 |
| `other` | 28 | 0/28 (0%) | 0/28 (0%) | 27/28 (96%) | 11 |

**The own-use column is English-only and must not be read across that table.** The pattern set that detects a first-hand claim ("I ran", "on my box", "I get") is English, so it scores 0/101 on Chinese threads by construction, not by finding. The honest first-hand figure is 11/152 (7%) of English threads; for the other 129 it is unmeasured.

The artifact columns *are* comparable across languages, because benchmark names, version strings, code fences and error output survive translation — and they show something real: the median Chinese thread is 21 characters against 112 for English. The low Chinese artifact rate is mostly genuine brevity, not a blind spot. Chinese threads that do carry artifacts are picked up correctly, including one reporting that the deployed V4 Pro API underperforms expectations and asking whether a parameter fix is responsible.

## Model repos

All 295 repos with `v4-pro` in the id, by downloads. `Card A` = artifact kinds on the card — **vendor claims**. `Disc` = discussion count.

| # | Repo | Official | Downloads | Likes | Modified | Licence | Card | Bench lines | Card A | Disc |
| ---: | --- | :-: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | [deepseek-ai/DeepSeek-V4-Pro](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) | **Y** | 782,206 | 5492 | 2026-06-22 | mit | 13137 | 29 | 4 | 210 |
| 2 | [nvidia/DeepSeek-V4-Pro-NVFP4](https://huggingface.co/nvidia/DeepSeek-V4-Pro-NVFP4) |  | 148,566 | 77 | 2026-06-14 | mit | 8721 | 1 | 4 | 2 |
| 3 | [deepseek-ai/DeepSeek-V4-Pro-0813](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813) | **Y** | 138,833 | 793 | 2026-08-13 | mit | 7501 | 2 | 4 | 21 |
| 4 | [unsloth/DeepSeek-V4-Pro-0813-GGUF](https://huggingface.co/unsloth/DeepSeek-V4-Pro-0813-GGUF) |  | 96,824 | 62 | 2026-08-14 | mit | 6889 | 2 | 4 | 5 |
| 5 | [Jackrong/DeepSeek-V4-Pro-Qwen3.5-9B-MTP-GGUF](https://huggingface.co/Jackrong/DeepSeek-V4-Pro-Qwen3.5-9B-MTP-GGUF) |  | 85,893 | 100 | 2026-08-13 | apache-2.0 | 37420 | 17 | 3 |  |
| 6 | [Jackrong/DeepSeek-V4-Pro-Qwen3.5-4B-MTP-GGUF](https://huggingface.co/Jackrong/DeepSeek-V4-Pro-Qwen3.5-4B-MTP-GGUF) |  | 37,898 | 46 | 2026-08-13 | apache-2.0 | 29486 | 20 | 3 |  |
| 7 | [deepseek-ai/DeepSeek-V4-Pro-Base](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base) | **Y** | 20,147 | 332 | 2026-04-27 | — | **none** | 0 | 0 | 20 |
| 8 | [6block/DeepSeek-V4-Pro-0813-GGUF](https://huggingface.co/6block/DeepSeek-V4-Pro-0813-GGUF) |  | 15,933 | 2 | 2026-08-20 | mit | 7674 | 2 | 4 | 1 |
| 9 | [Jackrong/DeepSeek-V4-Pro-Qwen3.5-4B](https://huggingface.co/Jackrong/DeepSeek-V4-Pro-Qwen3.5-4B) |  | 9,597 | 15 | 2026-08-13 | apache-2.0 | 29486 | 20 | 3 |  |
| 10 | [mradermacher/DeepSeek-V4-Pro-Qwen3.5-4B-GGUF](https://huggingface.co/mradermacher/DeepSeek-V4-Pro-Qwen3.5-4B-GGUF) |  | 5,955 | 3 | 2026-08-14 | apache-2.0 | 4395 | 0 | 2 |  |
| 11 | [mradermacher/DeepSeek-V4-Pro-Qwen3.5-4B-i1-GGUF](https://huggingface.co/mradermacher/DeepSeek-V4-Pro-Qwen3.5-4B-i1-GGUF) |  | 5,432 | 1 | 2026-08-14 | apache-2.0 | 5390 | 0 | 2 |  |
| 12 | [sgl-project/DeepSeek-V4-Pro-FP8](https://huggingface.co/sgl-project/DeepSeek-V4-Pro-FP8) |  | 4,990 | 13 | 2026-04-24 | mit | 542 | 0 | 2 |  |
| 13 | [mradermacher/DeepSeek-V4-Pro-Qwen3.5-9B-i1-GGUF](https://huggingface.co/mradermacher/DeepSeek-V4-Pro-Qwen3.5-9B-i1-GGUF) |  | 4,890 | 1 | 2026-08-10 | apache-2.0 | 5445 | 0 | 2 |  |
| 14 | [deepseek-ai/DeepSeek-V4-Pro-DSpark](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-DSpark) | **Y** | 4,075 | 541 | 2026-07-04 | mit | 14429 | 29 | 4 | 6 |
| 15 | [amd/DeepSeek-V4-Pro-MXFP4](https://huggingface.co/amd/DeepSeek-V4-Pro-MXFP4) |  | 3,965 | 0 | 2026-07-24 | mit | 3836 | 1 | 4 | 1 |
| 16 | [10Hen10/Qwen3.6-27B-unsloth-code-reasoning-deepseek-v4-pro-destilled-Mlx](https://huggingface.co/10Hen10/Qwen3.6-27B-unsloth-code-reasoning-deepseek-v4-pro-destilled-Mlx) |  | 3,838 | 1 | 2026-08-07 | apache-2.0 | 3492 | 0 | 3 |  |
| 17 | [10Hen10/Qwen3.6-35B-unsloth-code-reasoning-deepseek-v4-pro-destilled-Mlx-4bit](https://huggingface.co/10Hen10/Qwen3.6-35B-unsloth-code-reasoning-deepseek-v4-pro-destilled-Mlx-4bit) |  | 2,420 | 2 | 2026-08-07 | apache-2.0 | 3523 | 0 | 3 |  |
| 18 | [mradermacher/DeepSeek-V4-Pro-Qwen3.5-9B-GGUF](https://huggingface.co/mradermacher/DeepSeek-V4-Pro-Qwen3.5-9B-GGUF) |  | 2,384 | 1 | 2026-08-10 | apache-2.0 | 4451 | 0 | 2 |  |
| 19 | [mlx-community/DeepSeek-V4-Pro](https://huggingface.co/mlx-community/DeepSeek-V4-Pro) |  | 2,295 | 5 | 2026-06-07 | mit | 1072 | 0 | 2 |  |
| 20 | [Jackrong/DeepSeek-V4-Pro-Qwen3.5-9B](https://huggingface.co/Jackrong/DeepSeek-V4-Pro-Qwen3.5-9B) |  | 1,827 | 12 | 2026-08-13 | apache-2.0 | 37420 | 17 | 3 | 1 |
| 21 | [mlx-community/DeepSeek-V4-Pro-Qwen3.5-9B-bf16](https://huggingface.co/mlx-community/DeepSeek-V4-Pro-Qwen3.5-9B-bf16) |  | 1,584 | 2 | 2026-08-07 | apache-2.0 | 2042 | 0 | 3 |  |
| 22 | [qtum/DeepSeek-V4-Pro-0813-GGUF](https://huggingface.co/qtum/DeepSeek-V4-Pro-0813-GGUF) |  | 1,354 | 1 | 2026-08-21 | mit | 7662 | 2 | 4 |  |
| 23 | [alessandrobologna/DeepSeek-V4-Pro-DSpark-Drafter-GGUF](https://huggingface.co/alessandrobologna/DeepSeek-V4-Pro-DSpark-Drafter-GGUF) |  | 1,178 | 2 | 2026-08-15 | mit | 8218 | 0 | 3 |  |
| 24 | [ryant0000/DeepSeek-V4-Pro-0813-gguf](https://huggingface.co/ryant0000/DeepSeek-V4-Pro-0813-gguf) |  | 1,163 | 0 | 2026-08-15 | mit | 8078 | 2 | 4 |  |
| 25 | [mlx-community/DeepSeek-V4-Pro-Qwen3.5-9B-4bit](https://huggingface.co/mlx-community/DeepSeek-V4-Pro-Qwen3.5-9B-4bit) |  | 1,158 | 1 | 2026-08-07 | apache-2.0 | 2165 | 0 | 2 |  |
| 26 | [AutomatosX/AX-DeepSeek-V4-Pro-0813-MLX-AXQ-2bit-MTP](https://huggingface.co/AutomatosX/AX-DeepSeek-V4-Pro-0813-MLX-AXQ-2bit-MTP) |  | 1,106 | 0 | 2026-08-22 | mit | 2944 | 0 | 2 |  |
| 27 | [inferencerlabs/DeepSeek-V4-Pro-MTP-MLX](https://huggingface.co/inferencerlabs/DeepSeek-V4-Pro-MTP-MLX) |  | 1,102 | 3 | 2026-06-27 | — | 1939 | 0 | 2 |  |
| 28 | [teamblobfish/DeepSeek-V4-Pro-GGUF](https://huggingface.co/teamblobfish/DeepSeek-V4-Pro-GGUF) |  | 954 | 15 | 2026-05-14 | mit | 11098 | 2 | 5 | 1 |
| 29 | [mlx-community/DeepSeek-V4-Pro-Qwen3.5-9B-8bit](https://huggingface.co/mlx-community/DeepSeek-V4-Pro-Qwen3.5-9B-8bit) |  | 861 | 0 | 2026-08-07 | apache-2.0 | 2165 | 0 | 2 |  |
| 30 | [mlx-community/DeepSeek-V4-Pro-4bit](https://huggingface.co/mlx-community/DeepSeek-V4-Pro-4bit) |  | 855 | 3 | 2026-04-25 | — | 575 | 0 | 2 |  |
| 31 | [unsloth/DeepSeek-V4-Pro-0813](https://huggingface.co/unsloth/DeepSeek-V4-Pro-0813) |  | 759 | 4 | 2026-08-14 | mit | 8382 | 2 | 4 |  |
| 32 | [mlx-community/DeepSeek-V4-Pro-8bit](https://huggingface.co/mlx-community/DeepSeek-V4-Pro-8bit) |  | 692 | 2 | 2026-05-23 | — | 575 | 0 | 2 | 1 |
| 33 | [nvidia/DeepSeek-V4-Pro-0813-NVFP4](https://huggingface.co/nvidia/DeepSeek-V4-Pro-0813-NVFP4) |  | 582 | 8 | 2026-09-01 | mit | 12789 | 2 | 4 |  |
| 34 | [nvidia/DeepSeek-V4-Pro-nvfp4-DSpark](https://huggingface.co/nvidia/DeepSeek-V4-Pro-nvfp4-DSpark) |  | 577 | 0 | 2026-08-15 | mit | 16502 | 1 | 4 |  |
| 35 | [mlx-community/DeepSeek-V4-Pro-Qwen3.5-9B-6bit](https://huggingface.co/mlx-community/DeepSeek-V4-Pro-Qwen3.5-9B-6bit) |  | 520 | 0 | 2026-08-07 | apache-2.0 | 2165 | 0 | 2 |  |
| 36 | [dev7a/DeepSeek-V4-Pro-DSpark-Drafter-GGUF](https://huggingface.co/dev7a/DeepSeek-V4-Pro-DSpark-Drafter-GGUF) |  | 506 | 0 | 2026-08-15 | mit | 3477 | 0 | 3 |  |
| 37 | [mlx-community/DeepSeek-V4-Pro-Qwen3.5-4B-4bit](https://huggingface.co/mlx-community/DeepSeek-V4-Pro-Qwen3.5-4B-4bit) |  | 467 | 0 | 2026-08-07 | apache-2.0 | 2165 | 0 | 2 |  |
| 38 | [wrldsuksgo2mars/DeepSeek-V4-Pro-0813-EXL3-K2-calibrated-v1](https://huggingface.co/wrldsuksgo2mars/DeepSeek-V4-Pro-0813-EXL3-K2-calibrated-v1) |  | 436 | 0 | 2026-08-21 | mit | 12668 | 2 | 4 |  |
| 39 | [mradermacher/Distil-Deepseek.V4.Pro.Minute.Codex.NSFW-0.1B-GGUF](https://huggingface.co/mradermacher/Distil-Deepseek.V4.Pro.Minute.Codex.NSFW-0.1B-GGUF) |  | 365 | 2 | 2026-06-02 | apache-2.0 | 4523 | 0 | 1 |  |
| 40 | [inferencerlabs/DeepSeek-V4-Pro-Preview-MLX-Q2i](https://huggingface.co/inferencerlabs/DeepSeek-V4-Pro-Preview-MLX-Q2i) |  | 364 | 2 | 2026-05-22 | — | 1697 | 0 | 2 | 2 |
| 41 | [mlx-community/DeepSeek-V4-Pro-Qwen3.5-4B-8bit](https://huggingface.co/mlx-community/DeepSeek-V4-Pro-Qwen3.5-4B-8bit) |  | 359 | 0 | 2026-08-07 | apache-2.0 | 2165 | 0 | 2 |  |
| 42 | [mlx-community/DeepSeek-V4-Pro-Qwen3.5-4B-bf16](https://huggingface.co/mlx-community/DeepSeek-V4-Pro-Qwen3.5-4B-bf16) |  | 355 | 0 | 2026-08-07 | apache-2.0 | 2042 | 0 | 3 |  |
| 43 | [pokey2025/dspark-DeepSeek-V4-Pro-0813.gguf](https://huggingface.co/pokey2025/dspark-DeepSeek-V4-Pro-0813.gguf) |  | 304 | 0 | 2026-08-23 | mit | 4936 | 0 | 4 |  |
| 44 | [mlx-community/DeepSeek-V4-Pro-bf16](https://huggingface.co/mlx-community/DeepSeek-V4-Pro-bf16) |  | 300 | 0 | 2026-05-23 | — | 575 | 0 | 3 |  |
| 45 | [BennyGM/DeepSeek-V4-Pro-bf16](https://huggingface.co/BennyGM/DeepSeek-V4-Pro-bf16) |  | 294 | 1 | 2026-05-31 | — | 575 | 0 | 3 |  |
| 46 | [amd/DeepSeek-V4-Pro-NVFP4](https://huggingface.co/amd/DeepSeek-V4-Pro-NVFP4) |  | 279 | 2 | 2026-08-25 | mit | 4258 | 0 | 3 | 4 |
| 47 | [mlx-community/DeepSeek-V4-Pro-Qwen3.5-4B-6bit](https://huggingface.co/mlx-community/DeepSeek-V4-Pro-Qwen3.5-4B-6bit) |  | 263 | 0 | 2026-08-07 | apache-2.0 | 2165 | 0 | 2 |  |
| 48 | [DevQuasar/deepseek-ai.DeepSeek-V4-Pro-0813-GGUF](https://huggingface.co/DevQuasar/deepseek-ai.DeepSeek-V4-Pro-0813-GGUF) |  | 254 | 1 | 2026-08-15 | — | 589 | 0 | 1 |  |
| 49 | [multimodalart/DeepSeek-V4-Pro-0813](https://huggingface.co/multimodalart/DeepSeek-V4-Pro-0813) |  | 228 | 0 | 2026-08-13 | mit | 7549 | 2 | 4 |  |
| 50 | [Vaibhavhome30/DeepSeek-V4-Pro](https://huggingface.co/Vaibhavhome30/DeepSeek-V4-Pro) |  | 221 | 0 | 2026-08-07 | mit | 13137 | 29 | 4 |  |
| 51 | [yeoj34760/DeepSeek-V4-Pro-0813](https://huggingface.co/yeoj34760/DeepSeek-V4-Pro-0813) |  | 217 | 0 | 2026-08-13 | mit | 7501 | 2 | 4 |  |
| 52 | [isparian/DeepSeek-V4-Pro-Qwen3.5-4B-MTP-DIY](https://huggingface.co/isparian/DeepSeek-V4-Pro-Qwen3.5-4B-MTP-DIY) |  | 216 | 0 | 2026-08-04 | mit | 133 | 0 | 1 |  |
| 53 | [theftyyy/DeepSeek-V4-Pro-0813](https://huggingface.co/theftyyy/DeepSeek-V4-Pro-0813) |  | 213 | 0 | 2026-08-27 | mit | 7501 | 2 | 4 |  |
| 54 | [servantofares/DeepSeek-V4-Pro-0813](https://huggingface.co/servantofares/DeepSeek-V4-Pro-0813) |  | 200 | 0 | 2026-08-13 | mit | 7501 | 2 | 4 |  |
| 55 | [unsloth/DeepSeek-V4-Pro](https://huggingface.co/unsloth/DeepSeek-V4-Pro) |  | 194 | 60 | 2026-04-24 | mit | 13222 | 29 | 4 | 1 |
| 56 | [Zidane29/DeepSeek-V4-Pro-0813](https://huggingface.co/Zidane29/DeepSeek-V4-Pro-0813) |  | 189 | 0 | 2026-08-30 | mit | 7501 | 2 | 4 |  |
| 57 | [scsysbcn/DeepSeek-V4-Pro-0813](https://huggingface.co/scsysbcn/DeepSeek-V4-Pro-0813) |  | 185 | 0 | 2026-08-16 | mit | 7501 | 2 | 4 |  |
| 58 | [zreozero/Distil-Deepseek.V4.Pro.Minute.Codex.NSFW-0.1B-GGUF](https://huggingface.co/zreozero/Distil-Deepseek.V4.Pro.Minute.Codex.NSFW-0.1B-GGUF) |  | 176 | 0 | 2026-06-30 | apache-2.0 | 4523 | 0 | 1 |  |
| 59 | [TechnoBaptist/DeepSeek-V4-Pro-0813](https://huggingface.co/TechnoBaptist/DeepSeek-V4-Pro-0813) |  | 174 | 0 | 2026-08-13 | mit | 7501 | 2 | 4 |  |
| 60 | [bullerwins/DeepSeek-V4-Pro-0813-exl3-2.04bpw](https://huggingface.co/bullerwins/DeepSeek-V4-Pro-0813-exl3-2.04bpw) |  | 172 | 2 | 2026-08-15 | mit | 7547 | 2 | 4 |  |
| 61 | [FrankensteinSim/DeepSeek-V4-Pro-0813](https://huggingface.co/FrankensteinSim/DeepSeek-V4-Pro-0813) |  | 172 | 0 | 2026-08-22 | mit | 7501 | 2 | 4 |  |
| 62 | [scientist234591/DeepSeek-V4-Pro](https://huggingface.co/scientist234591/DeepSeek-V4-Pro) |  | 172 | 0 | 2026-08-23 | mit | 13137 | 29 | 4 |  |
| 63 | [kirusanth08/DeepSeek-V4-Pro](https://huggingface.co/kirusanth08/DeepSeek-V4-Pro) |  | 171 | 0 | 2026-08-24 | mit | 13137 | 29 | 4 |  |
| 64 | [TheWavesX/DeepSeek-V4-Pro](https://huggingface.co/TheWavesX/DeepSeek-V4-Pro) |  | 167 | 0 | 2026-08-05 | mit | 13137 | 29 | 4 |  |
| 65 | [ginsongsong/DeepSeek-V4-Pro-0813-PTPC](https://huggingface.co/ginsongsong/DeepSeek-V4-Pro-0813-PTPC) |  | 163 | 0 | 2026-08-31 | mit | 7501 | 2 | 4 |  |
| 66 | [Plana-Chan/DeepSeek-V4-Pro-0813](https://huggingface.co/Plana-Chan/DeepSeek-V4-Pro-0813) |  | 147 | 0 | 2026-08-17 | mit | 7501 | 2 | 4 |  |
| 67 | [RedHatAI/DeepSeek-V4-Pro-NVFP4-FP8](https://huggingface.co/RedHatAI/DeepSeek-V4-Pro-NVFP4-FP8) |  | 144 | 1 | 2026-07-24 | mit | 1181 | 2 | 4 |  |
| 68 | [batiai/DeepSeek-V4-Pro-GGUF](https://huggingface.co/batiai/DeepSeek-V4-Pro-GGUF) |  | 143 | 2 | 2026-06-01 | mit | 9424 | 0 | 3 | 2 |
| 69 | [inference-optimization/DeepSeek-V4-Pro-0.5B-A0.37B](https://huggingface.co/inference-optimization/DeepSeek-V4-Pro-0.5B-A0.37B) |  | 136 | 0 | 2026-07-22 | mit | 3138 | 0 | 3 |  |
| 70 | [iamprettyawesome/DeepSeek-V4-Pro](https://huggingface.co/iamprettyawesome/DeepSeek-V4-Pro) |  | 122 | 0 | 2026-08-04 | mit | 13137 | 29 | 4 |  |
| 71 | [Intel/DeepSeek-V4-Pro-W4A16-AutoRound](https://huggingface.co/Intel/DeepSeek-V4-Pro-W4A16-AutoRound) |  | 119 | 0 | 2026-06-15 | mit | 2444 | 0 | 2 |  |
| 72 | [Ishowbackup/DeepSeek-V4-Pro-0813](https://huggingface.co/Ishowbackup/DeepSeek-V4-Pro-0813) |  | 115 | 0 | 2026-08-20 | mit | 7501 | 2 | 4 |  |
| 73 | [SinterForge/DeepSeek-V4-Pro-0813](https://huggingface.co/SinterForge/DeepSeek-V4-Pro-0813) |  | 101 | 0 | 2026-08-14 | mit | 7501 | 2 | 4 |  |
| 74 | [jarrelscy/DeepSeek-V4-Pro-0813-NVFP4-AQLM-hybrid](https://huggingface.co/jarrelscy/DeepSeek-V4-Pro-0813-NVFP4-AQLM-hybrid) |  | 77 | 4 | 2026-08-16 | mit | 6742 | 1 | 5 | 1 |
| 75 | [Scrappy-Doo/DeepSeek-V4-Pro](https://huggingface.co/Scrappy-Doo/DeepSeek-V4-Pro) |  | 71 | 0 | 2026-07-25 | mit | 13137 | 29 | 4 |  |
| 76 | [DevQuasar/deepseek-ai.DeepSeek-V4-Pro-GGUF](https://huggingface.co/DevQuasar/deepseek-ai.DeepSeek-V4-Pro-GGUF) |  | 67 | 0 | 2026-07-16 | — | 574 | 0 | 1 |  |
| 77 | [ginsongsong/DeepSeek-V4-Pro-FP4PTPC](https://huggingface.co/ginsongsong/DeepSeek-V4-Pro-FP4PTPC) |  | 66 | 0 | 2026-08-28 | mit | 13181 | 29 | 4 |  |
| 78 | [SwinliQ-AIs/DeepSeek-V4-Pro-DSpark](https://huggingface.co/SwinliQ-AIs/DeepSeek-V4-Pro-DSpark) |  | 65 | 1 | 2026-07-29 | mit | 14429 | 29 | 4 |  |
| 79 | [silence09/DeepSeek-V4-Pro-Tiny](https://huggingface.co/silence09/DeepSeek-V4-Pro-Tiny) |  | 58 | 4 | 2026-05-05 | mit | 2452 | 0 | 2 |  |
| 80 | [SAIFIINDUSTRIES/deepseek-v4-pro](https://huggingface.co/SAIFIINDUSTRIES/deepseek-v4-pro) |  | 52 | 0 | 2026-07-08 | mit | 13137 | 29 | 4 |  |
| 81 | [canada-quant/DeepSeek-V4-Pro-NVFP4-FP8-MTP](https://huggingface.co/canada-quant/DeepSeek-V4-Pro-NVFP4-FP8-MTP) |  | 51 | 4 | 2026-05-26 | mit | 17853 | 20 | 5 | 1 |
| 82 | [ddvd233/mimiciv_rare_qwen36_27b_deepseekv4pro](https://huggingface.co/ddvd233/mimiciv_rare_qwen36_27b_deepseekv4pro) |  | 49 | 1 | 2026-06-16 | — | **none** | 0 | 0 |  |
| 83 | [jarrelscy/DeepSeek-V4-Pro-0813-NVFP4](https://huggingface.co/jarrelscy/DeepSeek-V4-Pro-0813-NVFP4) |  | 47 | 1 | 2026-08-14 | mit | 1657 | 0 | 3 |  |
| 84 | [INCModel2/DeepSeek-V4-Pro-DSpark-MXFP4-Mixed-CT-AutoRound](https://huggingface.co/INCModel2/DeepSeek-V4-Pro-DSpark-MXFP4-Mixed-CT-AutoRound) |  | 41 | 2 | 2026-06-30 | mit | 13437 | 29 | 4 |  |
| 85 | [INCModelSharing/DeepSeek-V4-Pro-DSpark-MXFP4-Mixed-CT-AutoRound](https://huggingface.co/INCModelSharing/DeepSeek-V4-Pro-DSpark-MXFP4-Mixed-CT-AutoRound) |  | 40 | 1 | 2026-06-30 | mit | 13437 | 29 | 4 |  |
| 86 | [RedHatAI/DeepSeek-V4-Pro](https://huggingface.co/RedHatAI/DeepSeek-V4-Pro) |  | 38 | 0 | 2026-06-19 | mit | 13181 | 29 | 4 |  |
| 87 | [brodatech/DeepSeek-V4-Pro-NVFP4](https://huggingface.co/brodatech/DeepSeek-V4-Pro-NVFP4) |  | 37 | 0 | 2026-06-10 | mit | 8662 | 1 | 4 |  |
| 88 | [Evilcarbon/DeepSeek-V4-Pro-DSpark](https://huggingface.co/Evilcarbon/DeepSeek-V4-Pro-DSpark) |  | 37 | 0 | 2026-06-27 | mit | 13437 | 29 | 4 |  |
| 89 | [Arsh9210/DeepSeek-V4-Pro-NVFP4](https://huggingface.co/Arsh9210/DeepSeek-V4-Pro-NVFP4) |  | 37 | 0 | 2026-07-30 | mit | 8721 | 1 | 4 |  |
| 90 | [INCModel/DeepSeek-V4-Pro-MXFP4-Mixed-CT-AutoRound](https://huggingface.co/INCModel/DeepSeek-V4-Pro-MXFP4-Mixed-CT-AutoRound) |  | 36 | 0 | 2026-07-08 | mit | 3992 | 1 | 4 |  |
| 91 | [abdurrahmanraza/DeepSeek-V4-Pro-DSpark](https://huggingface.co/abdurrahmanraza/DeepSeek-V4-Pro-DSpark) |  | 36 | 0 | 2026-07-08 | mit | 14429 | 29 | 4 |  |
| 92 | [dshive/DeepSeek-V4-Pro-DSpark](https://huggingface.co/dshive/DeepSeek-V4-Pro-DSpark) |  | 36 | 0 | 2026-07-09 | mit | 14429 | 29 | 4 |  |
| 93 | [wdfgyuagguf/DeepSeek-V4-Pro-NVFP4-FREE](https://huggingface.co/wdfgyuagguf/DeepSeek-V4-Pro-NVFP4-FREE) |  | 35 | 1 | 2026-06-03 | mit | 8662 | 1 | 4 |  |
| 94 | [Karthik745/DeepSeek-V4-Pro-DSpark](https://huggingface.co/Karthik745/DeepSeek-V4-Pro-DSpark) |  | 35 | 0 | 2026-06-30 | mit | 13437 | 29 | 4 |  |
| 95 | [johnnyai77/DeepSeek-V4-Pro-DSpark](https://huggingface.co/johnnyai77/DeepSeek-V4-Pro-DSpark) |  | 35 | 0 | 2026-07-29 | mit | 14429 | 29 | 4 |  |
| 96 | [Mancoling/DeepSeek-V4-Pro-DSpark](https://huggingface.co/Mancoling/DeepSeek-V4-Pro-DSpark) |  | 34 | 0 | 2026-07-07 | mit | 14429 | 29 | 4 |  |
| 97 | [4735Xu/DeepSeek-V4-Pro-DSpark](https://huggingface.co/4735Xu/DeepSeek-V4-Pro-DSpark) |  | 34 | 0 | 2026-07-07 | mit | 14429 | 29 | 4 |  |
| 98 | [huangwenkang/DeepSeek-V4-Pro-DSpark](https://huggingface.co/huangwenkang/DeepSeek-V4-Pro-DSpark) |  | 34 | 0 | 2026-07-08 | mit | 14429 | 29 | 4 |  |
| 99 | [DeidaraDemi/DeepSeek-V4-Pro](https://huggingface.co/DeidaraDemi/DeepSeek-V4-Pro) |  | 34 | 0 | 2026-07-28 | mit | 13137 | 29 | 4 |  |
| 100 | [Roger322-cmd/DeepSeek-V4-Pro-DSpark](https://huggingface.co/Roger322-cmd/DeepSeek-V4-Pro-DSpark) |  | 33 | 0 | 2026-07-04 | mit | 14429 | 29 | 4 |  |
| 101 | [Umbasa/DeepSeek-V4-Pro-DSpark-UMBASA-V1](https://huggingface.co/Umbasa/DeepSeek-V4-Pro-DSpark-UMBASA-V1) |  | 33 | 0 | 2026-07-25 | mit | 14429 | 29 | 4 |  |
| 102 | [SECWIKI/DeepSeek-V4-Pro](https://huggingface.co/SECWIKI/DeepSeek-V4-Pro) |  | 32 | 0 | 2026-04-24 | mit | 13181 | 29 | 4 |  |
| 103 | [livadies/DeepSeek-V4-Pro-Ghetto-Edition-MoE-Rank-64](https://huggingface.co/livadies/DeepSeek-V4-Pro-Ghetto-Edition-MoE-Rank-64) |  | 32 | 2 | 2026-04-27 | apache-2.0 | 2437 | 0 | 3 |  |
| 104 | [johnnyai77/DeepSeek-V4-Pro](https://huggingface.co/johnnyai77/DeepSeek-V4-Pro) |  | 32 | 0 | 2026-07-29 | mit | 13137 | 29 | 4 |  |
| 105 | [03y54h/DeepSeek-V4-Pro](https://huggingface.co/03y54h/DeepSeek-V4-Pro) |  | 31 | 0 | 2026-07-29 | mit | 13137 | 29 | 4 |  |
| 106 | [Sohailhosseini/DeepSeek-V4-Pro-Qwen3.5-9B-FP8](https://huggingface.co/Sohailhosseini/DeepSeek-V4-Pro-Qwen3.5-9B-FP8) |  | 31 | 0 | 2026-08-22 | apache-2.0 | 1902 | 0 | 3 |  |
| 107 | [nu11secur1ty/DeepSeek-V4-Pro-Base](https://huggingface.co/nu11secur1ty/DeepSeek-V4-Pro-Base) |  | 30 | 0 | 2026-05-12 | other | 1642 | 0 | 2 |  |
| 108 | [MagnusTi8/DeepSeek-V4-Pro](https://huggingface.co/MagnusTi8/DeepSeek-V4-Pro) |  | 29 | 0 | 2026-04-24 | mit | 13181 | 29 | 4 |  |
| 109 | [Sohailhosseini/DeepSeek-V4-Pro-Qwen3.5-9B-AWQ-W4A16](https://huggingface.co/Sohailhosseini/DeepSeek-V4-Pro-Qwen3.5-9B-AWQ-W4A16) |  | 28 | 0 | 2026-08-22 | apache-2.0 | 2004 | 0 | 3 |  |
| 110 | [3006IA/DeepSeek-V4-Pro-snapchot](https://huggingface.co/3006IA/DeepSeek-V4-Pro-snapchot) |  | 27 | 0 | 2026-07-29 | mit | 13137 | 29 | 4 |  |
| 111 | [topxidu/DeepSeek-V4-Pro](https://huggingface.co/topxidu/DeepSeek-V4-Pro) |  | 24 | 0 | 2026-04-24 | mit | 13181 | 29 | 4 |  |
| 112 | [11-47/Distil-Deepseek.V4.Pro.Minute.Codex.NSFW-0.1B](https://huggingface.co/11-47/Distil-Deepseek.V4.Pro.Minute.Codex.NSFW-0.1B) |  | 24 | 1 | 2026-05-06 | apache-2.0 | 3413 | 0 | 2 |  |
| 113 | [INCModel/DeepSeek-V4-Pro-MXFP4-LLMC](https://huggingface.co/INCModel/DeepSeek-V4-Pro-MXFP4-LLMC) |  | 19 | 0 | 2026-06-15 | mit | 4096 | 1 | 4 |  |
| 114 | [unsloth/DeepSeek-V4-Pro-Base](https://huggingface.co/unsloth/DeepSeek-V4-Pro-Base) |  | 18 | 4 | 2026-04-24 | — | **none** | 0 | 0 |  |
| 115 | [guthu/DeepSeek-V4-Pro](https://huggingface.co/guthu/DeepSeek-V4-Pro) |  | 17 | 0 | 2026-07-02 | mit | 13137 | 29 | 4 |  |
| 116 | [merlin9527/DeepSeek-V4-Pro](https://huggingface.co/merlin9527/DeepSeek-V4-Pro) |  | 15 | 0 | 2026-04-24 | mit | 13181 | 29 | 4 |  |
| 117 | [ckoh04/DeepSeek-V4-Pro-active-slice-6experts](https://huggingface.co/ckoh04/DeepSeek-V4-Pro-active-slice-6experts) |  | 15 | 0 | 2026-07-09 | mit | 13137 | 29 | 4 |  |
| 118 | [CharyZeng/DeepSeek-V4-Pro-4layer](https://huggingface.co/CharyZeng/DeepSeek-V4-Pro-4layer) |  | 14 | 0 | 2026-04-25 | mit | 13181 | 29 | 4 |  |
| 119 | [xwu-intel/DeepSeek-V4-Pro-4layers](https://huggingface.co/xwu-intel/DeepSeek-V4-Pro-4layers) |  | 14 | 0 | 2026-08-26 | — | **none** | 0 | 0 |  |
| 120 | [Sajaddb/DeepSeek-V4-Pro](https://huggingface.co/Sajaddb/DeepSeek-V4-Pro) |  | 14 | 0 | 2026-06-27 | mit | 13137 | 29 | 4 |  |
| 121 | [MuVeraAI/DeepSeek-V4-Pro](https://huggingface.co/MuVeraAI/DeepSeek-V4-Pro) |  | 13 | 0 | 2026-04-24 | mit | 13181 | 29 | 4 |  |
| 122 | [developerjeremylive/DeepSeek-V4-Pro-etheroi](https://huggingface.co/developerjeremylive/DeepSeek-V4-Pro-etheroi) |  | 13 | 0 | 2026-05-10 | mit | 13181 | 29 | 4 |  |
| 123 | [sasameden/DeepSeek-V4-Pro](https://huggingface.co/sasameden/DeepSeek-V4-Pro) |  | 13 | 0 | 2026-07-18 | mit | 13137 | 29 | 4 |  |
| 124 | [nassimjp/DeepSeek-V4-Pro](https://huggingface.co/nassimjp/DeepSeek-V4-Pro) |  | 12 | 0 | 2026-04-24 | mit | 13181 | 29 | 4 |  |
| 125 | [Rooc/DeepSeek-V4-Pro](https://huggingface.co/Rooc/DeepSeek-V4-Pro) |  | 12 | 1 | 2026-04-24 | mit | 13949 | 29 | 4 |  |
| 126 | [xx9056/DeepSeek-V4-Pro](https://huggingface.co/xx9056/DeepSeek-V4-Pro) |  | 12 | 0 | 2026-05-02 | mit | 13181 | 29 | 4 |  |
| 127 | [yagizzdemr/DeepSeek-V4-Pro](https://huggingface.co/yagizzdemr/DeepSeek-V4-Pro) |  | 12 | 0 | 2026-06-01 | mit | 13181 | 29 | 4 |  |
| 128 | [NathanEsSabio/DeepSeek-V4-Pro](https://huggingface.co/NathanEsSabio/DeepSeek-V4-Pro) |  | 12 | 0 | 2026-07-05 | mit | 13137 | 29 | 4 |  |
| 129 | [vidforge/DeepSeek-V4-Pro](https://huggingface.co/vidforge/DeepSeek-V4-Pro) |  | 12 | 0 | 2026-07-13 | mit | 13137 | 29 | 4 |  |
| 130 | [hang2020/DeepSeek-V4-Pro](https://huggingface.co/hang2020/DeepSeek-V4-Pro) |  | 11 | 0 | 2026-04-24 | mit | 13181 | 29 | 4 |  |
| 131 | [heartfly8/DeepSeek-V4-Pro](https://huggingface.co/heartfly8/DeepSeek-V4-Pro) |  | 11 | 0 | 2026-04-24 | mit | 13181 | 29 | 4 |  |
| 132 | [dimpsont/DeepSeek-V4-Pro](https://huggingface.co/dimpsont/DeepSeek-V4-Pro) |  | 11 | 0 | 2026-04-25 | mit | 13181 | 29 | 4 |  |
| 133 | [jony0551/DeepSeek-V4-Pro](https://huggingface.co/jony0551/DeepSeek-V4-Pro) |  | 11 | 0 | 2026-04-25 | mit | 13181 | 29 | 4 |  |
| 134 | [nathanielthomas/DeepSeek-V4-Pro-FP8](https://huggingface.co/nathanielthomas/DeepSeek-V4-Pro-FP8) |  | 11 | 1 | 2026-04-26 | mit | 542 | 0 | 2 |  |
| 135 | [models123/DeepSeek-V4-Pro](https://huggingface.co/models123/DeepSeek-V4-Pro) |  | 11 | 0 | 2026-04-28 | mit | 13181 | 29 | 4 |  |
| 136 | [friisbi/DeepSeek-V4-Pro](https://huggingface.co/friisbi/DeepSeek-V4-Pro) |  | 11 | 0 | 2026-05-04 | mit | 13181 | 29 | 4 |  |
| 137 | [SSBOfficial/DeepSeek-V4-Pro](https://huggingface.co/SSBOfficial/DeepSeek-V4-Pro) |  | 11 | 0 | 2026-05-25 | mit | 13181 | 29 | 4 |  |
| 138 | [Jdjdhdhhd837373773/DeepSeek-V4-Pro](https://huggingface.co/Jdjdhdhhd837373773/DeepSeek-V4-Pro) |  | 11 | 0 | 2026-06-14 | mit | 13181 | 29 | 4 |  |
| 139 | [ShaunGves/DeepSeek-V4-Pro](https://huggingface.co/ShaunGves/DeepSeek-V4-Pro) |  | 11 | 0 | 2026-06-19 | mit | 13181 | 29 | 4 |  |
| 140 | [kailiu1991/DeepSeek-V4-Pro](https://huggingface.co/kailiu1991/DeepSeek-V4-Pro) |  | 10 | 0 | 2026-04-24 | mit | 13181 | 29 | 4 |  |
| 141 | [uuyhju/DeepSeek-V4-Pro](https://huggingface.co/uuyhju/DeepSeek-V4-Pro) |  | 10 | 0 | 2026-05-04 | — | 13167 | 29 | 4 |  |
| 142 | [OK2026ok/DeepSeek-V4-Pro_ojkotka](https://huggingface.co/OK2026ok/DeepSeek-V4-Pro_ojkotka) |  | 10 | 0 | 2026-05-07 | mit | 13181 | 29 | 4 |  |
| 143 | [nu11secur1ty/DeepSeek-V4-Pro](https://huggingface.co/nu11secur1ty/DeepSeek-V4-Pro) |  | 10 | 0 | 2026-05-12 | other | 1642 | 0 | 2 |  |
| 144 | [haosion/DeepSeek-V4-Pro](https://huggingface.co/haosion/DeepSeek-V4-Pro) |  | 10 | 0 | 2026-05-14 | mit | 13181 | 29 | 4 |  |
| 145 | [bohemo35/DeepSeek-V4-Pro](https://huggingface.co/bohemo35/DeepSeek-V4-Pro) |  | 10 | 0 | 2026-05-16 | mit | 13181 | 29 | 4 |  |
| 146 | [YONKWd/DeepSeek-V4-Pro](https://huggingface.co/YONKWd/DeepSeek-V4-Pro) |  | 10 | 0 | 2026-05-23 | mit | 13181 | 29 | 4 |  |
| 147 | [Bhavya2128/DeepSeek-V4-Pro-Base](https://huggingface.co/Bhavya2128/DeepSeek-V4-Pro-Base) |  | 10 | 0 | 2026-07-26 | — | **none** | 0 | 0 |  |
| 148 | [Deepdive404/DeepSeek-V4-Pro](https://huggingface.co/Deepdive404/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-04-24 | mit | 13181 | 29 | 4 |  |
| 149 | [devshiva/DeepSeek-V4-Pro](https://huggingface.co/devshiva/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-04-24 | mit | 13181 | 29 | 4 |  |
| 150 | [PhysShell/DeepSeek-V4-Pro](https://huggingface.co/PhysShell/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-04-25 | mit | 13181 | 29 | 4 |  |
| 151 | [Sherckuith/DeepSeek-V4-Pro](https://huggingface.co/Sherckuith/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-04-27 | mit | 13181 | 29 | 4 |  |
| 152 | [jr5205212/DeepSeek-V4-Pro](https://huggingface.co/jr5205212/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-04-28 | mit | 13181 | 29 | 4 |  |
| 153 | [lopilop/DeepSeek-V4-Pro](https://huggingface.co/lopilop/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-04-28 | mit | 13181 | 29 | 4 |  |
| 154 | [bvsajgyh/DeepSeek-V4-Pro](https://huggingface.co/bvsajgyh/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-04-29 | mit | 13181 | 29 | 4 |  |
| 155 | [MertOezberk95/DeepSeek-V4-Pro](https://huggingface.co/MertOezberk95/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-05-01 | mit | 13181 | 29 | 4 |  |
| 156 | [laoguiyuan/DeepSeek-V4-Pro](https://huggingface.co/laoguiyuan/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-05-02 | mit | 13181 | 29 | 4 |  |
| 157 | [JoseyWales/DeepSeek-V4-Pro](https://huggingface.co/JoseyWales/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-05-02 | mit | 13181 | 29 | 4 |  |
| 158 | [hugimagi/DeepSeek-V4-Pro](https://huggingface.co/hugimagi/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-05-04 | mit | 13181 | 29 | 4 |  |
| 159 | [Hadi0609/DeepSeek-V4-Pro](https://huggingface.co/Hadi0609/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-05-05 | mit | 13181 | 29 | 4 |  |
| 160 | [Jun134340/DeepSeek-V4-Pro](https://huggingface.co/Jun134340/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-05-09 | mit | 13181 | 29 | 4 |  |
| 161 | [Whytoexist/DeepSeek-V4-Pro](https://huggingface.co/Whytoexist/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-05-10 | mit | 13181 | 29 | 4 |  |
| 162 | [CrossNow/DeepSeek-V4-Pro](https://huggingface.co/CrossNow/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-05-12 | mit | 13181 | 29 | 4 |  |
| 163 | [miduswell1/DeepSeek-V4-Pro](https://huggingface.co/miduswell1/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-05-16 | mit | 13181 | 29 | 4 |  |
| 164 | [Dharmendra11dec/DeepSeek-V4-Pro](https://huggingface.co/Dharmendra11dec/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-05-22 | mit | 13181 | 29 | 4 |  |
| 165 | [Asmita2682hshs/DeepSeek-V4-Pro](https://huggingface.co/Asmita2682hshs/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-06-03 | mit | 13181 | 29 | 4 |  |
| 166 | [Rezaul66877/DeepSeek-V4-Pro](https://huggingface.co/Rezaul66877/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-06-04 | mit | 13181 | 29 | 4 |  |
| 167 | [Aoneesh/DeepSeek-V4-Pro-Base](https://huggingface.co/Aoneesh/DeepSeek-V4-Pro-Base) |  | 9 | 0 | 2026-07-04 | mit | 82 | 0 | 1 |  |
| 168 | [harsh024/DeepSeek-V4-Pro](https://huggingface.co/harsh024/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-06-17 | mit | 13181 | 29 | 4 |  |
| 169 | [PiTtawat9/DeepSeek-V4-Pro](https://huggingface.co/PiTtawat9/DeepSeek-V4-Pro) |  | 9 | 0 | 2026-07-19 | mit | 13137 | 29 | 4 |  |
| 170 | [zqhzyy/DeepSeek-V4-Pro](https://huggingface.co/zqhzyy/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-04-24 | mit | 13181 | 29 | 4 |  |
| 171 | [testaccount-ai/DeepSeek-V4-Pro](https://huggingface.co/testaccount-ai/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-04-30 | mit | 13254 | 29 | 4 |  |
| 172 | [Rea277/DeepSeek-V4-Pro](https://huggingface.co/Rea277/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-04-26 | mit | 13181 | 29 | 4 |  |
| 173 | [viounm/DeepSeek-V4-Pro](https://huggingface.co/viounm/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-04-27 | mit | 13181 | 29 | 4 |  |
| 174 | [lhca521/DeepSeek-V4-Pro](https://huggingface.co/lhca521/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-04-27 | mit | 13181 | 29 | 4 |  |
| 175 | [Alexs28/DeepSeek-V4-Pro](https://huggingface.co/Alexs28/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-04-28 | mit | 13181 | 29 | 4 |  |
| 176 | [roestige/DeepSeek-V4-Pro](https://huggingface.co/roestige/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-04-28 | mit | 13181 | 29 | 4 |  |
| 177 | [Sanful/DeepSeek-V4-Pro](https://huggingface.co/Sanful/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-04-29 | mit | 13181 | 29 | 4 |  |
| 178 | [Ilmira789/DeepSeek-V4-Pro](https://huggingface.co/Ilmira789/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-04-29 | mit | 13181 | 29 | 4 |  |
| 179 | [SergeUSS/DeepSeek-V4-Pro](https://huggingface.co/SergeUSS/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-04-30 | mit | 13181 | 29 | 4 |  |
| 180 | [ahouab/DeepSeek-V4-Pro](https://huggingface.co/ahouab/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-02 | mit | 13181 | 29 | 4 |  |
| 181 | [abdulhannankashif/DeepSeek-V4-Pro](https://huggingface.co/abdulhannankashif/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-03 | mit | 13181 | 29 | 4 |  |
| 182 | [mutlukurt/DeepSeek-V4-Pro](https://huggingface.co/mutlukurt/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-03 | mit | 13181 | 29 | 4 |  |
| 183 | [Donnyoregon/DeepSeek-V4-Pro](https://huggingface.co/Donnyoregon/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-03 | mit | 13181 | 29 | 4 |  |
| 184 | [147258369aa/DeepSeek-V4-Pro](https://huggingface.co/147258369aa/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-04 | mit | 13181 | 29 | 4 |  |
| 185 | [Crshtst/DeepSeek-V4-Pro](https://huggingface.co/Crshtst/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-04 | mit | 13181 | 29 | 4 |  |
| 186 | [Yuhaha7shxn/DeepSeek-V4-Pro](https://huggingface.co/Yuhaha7shxn/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-05 | mit | 13181 | 29 | 4 |  |
| 187 | [Puppetsandangels/DeepSeek-V4-Pro](https://huggingface.co/Puppetsandangels/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-06 | mit | 13181 | 29 | 4 |  |
| 188 | [MentalGround/DeepSeek-V4-Pro](https://huggingface.co/MentalGround/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-08 | mit | 13181 | 29 | 4 |  |
| 189 | [grandprix/DeepSeek-V4-Pro](https://huggingface.co/grandprix/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-08 | mit | 13181 | 29 | 4 |  |
| 190 | [SensitiveContent/DeepSeek-V4-Pro](https://huggingface.co/SensitiveContent/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-12 | mit | 13181 | 29 | 4 |  |
| 191 | [Sav868767876-9999999876654346/DeepSeek-V4-Pro](https://huggingface.co/Sav868767876-9999999876654346/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-16 | mit | 13181 | 29 | 4 |  |
| 192 | [itsnousername/DeepSeek-V4-Pro](https://huggingface.co/itsnousername/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-16 | mit | 13181 | 29 | 4 |  |
| 193 | [azerxafro/DeepSeek-V4-Pro](https://huggingface.co/azerxafro/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-18 | mit | 13181 | 29 | 4 |  |
| 194 | [frostdark/DeepSeek-V4-Pro](https://huggingface.co/frostdark/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-19 | mit | 13181 | 29 | 4 |  |
| 195 | [wetgh/DeepSeek-V4-Pro](https://huggingface.co/wetgh/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-20 | mit | 13181 | 29 | 4 |  |
| 196 | [Tokeys/DeepSeek-V4-Pro](https://huggingface.co/Tokeys/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-20 | mit | 13181 | 29 | 4 |  |
| 197 | [harishkumar12k/DeepSeek-V4-Pro](https://huggingface.co/harishkumar12k/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-20 | mit | 13181 | 29 | 4 |  |
| 198 | [yrrhall/DeepSeek-V4-Pro](https://huggingface.co/yrrhall/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-20 | mit | 13181 | 29 | 4 |  |
| 199 | [m1aw/DeepSeek-V4-Pro](https://huggingface.co/m1aw/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-24 | mit | 13181 | 29 | 4 |  |
| 200 | [Rokrrr/DeepSeek-V4-Pro](https://huggingface.co/Rokrrr/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-05-30 | mit | 13181 | 29 | 4 |  |
| 201 | [anhnguyen002/DeepSeek-V4-Pro](https://huggingface.co/anhnguyen002/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-06-02 | mit | 13181 | 29 | 4 |  |
| 202 | [Rp2609/DeepSeek-V4-Pro](https://huggingface.co/Rp2609/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-06-02 | mit | 13181 | 29 | 4 |  |
| 203 | [shuaideva/DeepSeek-V4-Pro](https://huggingface.co/shuaideva/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-06-10 | mit | 13181 | 29 | 4 |  |
| 204 | [bnboxr/DeepSeek-V4-Pro](https://huggingface.co/bnboxr/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-06-12 | mit | 13181 | 29 | 4 |  |
| 205 | [anything098/DeepSeek-V4-Pro](https://huggingface.co/anything098/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-06-14 | mit | 13181 | 29 | 4 |  |
| 206 | [gnio77/DeepSeek-V4-Pro](https://huggingface.co/gnio77/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-06-23 | mit | 13137 | 29 | 4 |  |
| 207 | [dshive/DeepSeek-V4-Pro](https://huggingface.co/dshive/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-07-09 | mit | 13137 | 29 | 4 |  |
| 208 | [KoolKatC/DeepSeek-V4-Pro](https://huggingface.co/KoolKatC/DeepSeek-V4-Pro) |  | 8 | 0 | 2026-07-19 | mit | 13137 | 29 | 4 |  |
| 209 | [invi-bhagyesh/qwen-2.5-7b-it-msm-deepseek-v4-pro-goodness](https://huggingface.co/invi-bhagyesh/qwen-2.5-7b-it-msm-deepseek-v4-pro-goodness) |  | 8 | 0 | 2026-08-29 | — | 400 | 0 | 1 |  |
| 210 | [komeijishiki/DeepSeek-V4-Pro-Qwen3.5-9B-EXL3-6.50bpw-H8-V8-MTP8](https://huggingface.co/komeijishiki/DeepSeek-V4-Pro-Qwen3.5-9B-EXL3-6.50bpw-H8-V8-MTP8) |  | 8 | 0 | 2026-09-01 | apache-2.0 | 13402 | 1 | 3 |  |
| 211 | [sjm2729/DeepSeek-V4-Pro](https://huggingface.co/sjm2729/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-04-24 | mit | 13181 | 29 | 4 |  |
| 212 | [buaazhangs/DeepSeek-V4-Pro](https://huggingface.co/buaazhangs/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-04-25 | mit | 13181 | 29 | 4 |  |
| 213 | [AirlockRIck/DeepSeek-V4-Pro](https://huggingface.co/AirlockRIck/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-04-25 | mit | 13181 | 29 | 4 |  |
| 214 | [BLAISE558/DeepSeek-V4-Pro](https://huggingface.co/BLAISE558/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-04-26 | mit | 13181 | 29 | 4 |  |
| 215 | [zengxm99/DeepSeek-V4-Pro](https://huggingface.co/zengxm99/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-04-26 | mit | 13181 | 29 | 4 |  |
| 216 | [Vikram1234321/DeepSeek-V4-Pro](https://huggingface.co/Vikram1234321/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-04-26 | mit | 13181 | 29 | 4 |  |
| 217 | [Dhanidjulian/DeepSeek-V4-Pro](https://huggingface.co/Dhanidjulian/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-04-27 | mit | 13181 | 29 | 4 |  |
| 218 | [Oscar01Architecture/DeepSeek-V4-Pro](https://huggingface.co/Oscar01Architecture/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-04-28 | mit | 13181 | 29 | 4 |  |
| 219 | [LittleDesignSolution/DeepSeek-V4-Pro](https://huggingface.co/LittleDesignSolution/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-04-29 | mit | 13181 | 29 | 4 |  |
| 220 | [ChatUbermensch/DeepSeek-V4-Pro](https://huggingface.co/ChatUbermensch/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-04-29 | mit | 13181 | 29 | 4 |  |
| 221 | [Rockin86/DeepSeek-V4-Pro](https://huggingface.co/Rockin86/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-03 | mit | 13181 | 29 | 4 |  |
| 222 | [fcs666888/DeepSeek-V4-Pro](https://huggingface.co/fcs666888/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-03 | mit | 13181 | 29 | 4 |  |
| 223 | [StefCalvo/DeepSeek-V4-Pro](https://huggingface.co/StefCalvo/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-04 | mit | 13181 | 29 | 4 |  |
| 224 | [asdfjsdfd/DeepSeek-V4-Pro](https://huggingface.co/asdfjsdfd/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-04 | mit | 13181 | 29 | 4 |  |
| 225 | [TheWeakestGamer/DeepSeek-V4-Pro](https://huggingface.co/TheWeakestGamer/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-06 | mit | 13181 | 29 | 4 |  |
| 226 | [Mohamed-noreldin/DeepSeek-V4-Pro](https://huggingface.co/Mohamed-noreldin/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-07 | mit | 13181 | 29 | 4 |  |
| 227 | [Pskumar91/DeepSeek-V4-Pro](https://huggingface.co/Pskumar91/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-07 | mit | 13181 | 29 | 4 |  |
| 228 | [Aun1236/DeepSeek-V4-Pro](https://huggingface.co/Aun1236/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-09 | mit | 13181 | 29 | 4 |  |
| 229 | [JitishxD/Copy-DeepSeek-V4-Pro](https://huggingface.co/JitishxD/Copy-DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-10 | mit | 13181 | 29 | 4 |  |
| 230 | [roshan999999/DeepSeek-V4-Pro](https://huggingface.co/roshan999999/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-12 | mit | 13181 | 29 | 4 |  |
| 231 | [thy025/DeepSeek-V4-Pro](https://huggingface.co/thy025/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-15 | mit | 13181 | 29 | 4 |  |
| 232 | [Matsos10/DeepSeek-V4-Pro](https://huggingface.co/Matsos10/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-19 | mit | 13181 | 29 | 4 |  |
| 233 | [ZephyrStrike/DeepSeek-V4-Pro](https://huggingface.co/ZephyrStrike/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-19 | mit | 13181 | 29 | 4 |  |
| 234 | [waynetwleung/DeepSeek-V4-Pro](https://huggingface.co/waynetwleung/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-21 | mit | 13181 | 29 | 4 |  |
| 235 | [guokaiqiang/DeepSeek-V4-Pro](https://huggingface.co/guokaiqiang/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-21 | mit | 13181 | 29 | 4 |  |
| 236 | [Evilcarbon/DeepSeek-V4-Pro](https://huggingface.co/Evilcarbon/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-22 | mit | 13181 | 29 | 4 |  |
| 237 | [newbadeer83/DeepSeek-V4-Pro](https://huggingface.co/newbadeer83/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-26 | mit | 13181 | 29 | 4 |  |
| 238 | [Cornyblatz/DeepSeek-V4-Pro](https://huggingface.co/Cornyblatz/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-28 | mit | 13181 | 29 | 4 |  |
| 239 | [Balakrish89/DeepSeek-V4-Pro](https://huggingface.co/Balakrish89/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-30 | mit | 13181 | 29 | 4 |  |
| 240 | [Rosh3yyy/DeepSeek-V4-Pro](https://huggingface.co/Rosh3yyy/DeepSeek-V4-Pro) |  | 7 | 1 | 2026-05-31 | mit | 13181 | 29 | 4 |  |
| 241 | [BennyGM/DeepSeek-V4-Pro](https://huggingface.co/BennyGM/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-05-31 | mit | 13181 | 29 | 4 |  |
| 242 | [peterka79/DeepSeek-V4-Pro](https://huggingface.co/peterka79/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-06-09 | mit | 13181 | 29 | 4 |  |
| 243 | [Pomma/DeepSeek-V4-Pro](https://huggingface.co/Pomma/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-06-11 | mit | 13181 | 29 | 4 |  |
| 244 | [sdlangshaw/DeepSeek-V4-Pro](https://huggingface.co/sdlangshaw/DeepSeek-V4-Pro) |  | 7 | 0 | 2026-06-14 | mit | 13181 | 29 | 4 |  |
| 245 | [6cf/qwen35-9b-deepseek-v4-pro-agent-lora](https://huggingface.co/6cf/qwen35-9b-deepseek-v4-pro-agent-lora) |  | 7 | 0 | 2026-07-05 | — | 3730 | 5 | 4 |  |
| 246 | [inference-optimization/DeepSeek-V4-Pro-0.5B-A0.37B-NVFP4-FP8](https://huggingface.co/inference-optimization/DeepSeek-V4-Pro-0.5B-A0.37B-NVFP4-FP8) |  | 7 | 0 | 2026-07-22 | — | **none** | 0 | 0 |  |
| 247 | [Faizaniqbal/DeepSeek-V4-Pro-Base](https://huggingface.co/Faizaniqbal/DeepSeek-V4-Pro-Base) |  | 6 | 0 | 2026-04-24 | — | **none** | 0 | 0 |  |
| 248 | [FlagRelease/DeepSeek-V4-Pro-nvidia-FlagOS](https://huggingface.co/FlagRelease/DeepSeek-V4-Pro-nvidia-FlagOS) |  | 6 | 0 | 2026-04-30 | — | 9547 | 0 | 2 | 1 |
| 249 | [Yourfavvv01/DeepSeek-V4-Pro](https://huggingface.co/Yourfavvv01/DeepSeek-V4-Pro) |  | 6 | 0 | 2026-04-26 | mit | 13181 | 29 | 4 |  |
| 250 | [meteorlad/DeepSeek-V4-Pro](https://huggingface.co/meteorlad/DeepSeek-V4-Pro) |  | 6 | 0 | 2026-04-29 | mit | 13181 | 29 | 4 |  |
| 251 | [VeayKong/DeepSeek-V4-Pro](https://huggingface.co/VeayKong/DeepSeek-V4-Pro) |  | 6 | 0 | 2026-05-14 | mit | 13181 | 29 | 4 |  |
| 252 | [ridamee/DeepSeek-V4-Pro](https://huggingface.co/ridamee/DeepSeek-V4-Pro) |  | 6 | 0 | 2026-05-26 | mit | 13181 | 29 | 4 |  |
| 253 | [ohahai1/DeepSeek-V4-Pro-Base](https://huggingface.co/ohahai1/DeepSeek-V4-Pro-Base) |  | 5 | 0 | 2026-04-24 | — | **none** | 0 | 0 |  |
| 254 | [arsinonline/DeepSeek-V4-Pro-Base](https://huggingface.co/arsinonline/DeepSeek-V4-Pro-Base) |  | 5 | 0 | 2026-05-04 | — | **none** | 0 | 0 |  |
| 255 | [dr3dl0ck/DeepSeek-V4-Pro-Base](https://huggingface.co/dr3dl0ck/DeepSeek-V4-Pro-Base) |  | 5 | 0 | 2026-05-07 | — | **none** | 0 | 0 |  |
| 256 | [1aihk/DeepSeek-V4-Pro-Base](https://huggingface.co/1aihk/DeepSeek-V4-Pro-Base) |  | 5 | 0 | 2026-05-18 | — | **none** | 0 | 0 |  |
| 257 | [jaqck/DeepSeek-V4-Pro-Base](https://huggingface.co/jaqck/DeepSeek-V4-Pro-Base) |  | 5 | 0 | 2026-05-29 | — | 0 | 0 | 0 |  |
| 258 | [XURMATRONIX/DeepSeek-V4-Pro](https://huggingface.co/XURMATRONIX/DeepSeek-V4-Pro) |  | 5 | 0 | 2026-07-27 | — | 13099 | 29 | 4 |  |
| 259 | [ikeafisch4/DeepSeek-V4-Pro-tokenizer-65536](https://huggingface.co/ikeafisch4/DeepSeek-V4-Pro-tokenizer-65536) |  | 5 | 0 | 2026-08-02 | mit | 21 | 0 | 0 |  |
| 260 | [PhysShell/DeepSeek-V4-Pro-Base](https://huggingface.co/PhysShell/DeepSeek-V4-Pro-Base) |  | 4 | 0 | 2026-04-25 | — | **none** | 0 | 0 |  |
| 261 | [Evilcarbon/DeepSeek-V4-Pro-Base](https://huggingface.co/Evilcarbon/DeepSeek-V4-Pro-Base) |  | 4 | 0 | 2026-04-26 | — | **none** | 0 | 0 |  |
| 262 | [ToshMarley17/DeepSeek-V4-Pro](https://huggingface.co/ToshMarley17/DeepSeek-V4-Pro) |  | 4 | 0 | 2026-04-26 | mit | 13181 | 29 | 4 |  |
| 263 | [vultr/DeepSeek-V4-Pro-NVFP4](https://huggingface.co/vultr/DeepSeek-V4-Pro-NVFP4) |  | 4 | 0 | 2026-06-03 | — | **none** | 0 | 0 |  |
| 264 | [ScottzillaSystems/DeepSeek-V4-Pro-Base](https://huggingface.co/ScottzillaSystems/DeepSeek-V4-Pro-Base) |  | 4 | 0 | 2026-05-14 | — | **none** | 0 | 0 |  |
| 265 | [palaneandavar/DeepSeek-V4-Pro-Base](https://huggingface.co/palaneandavar/DeepSeek-V4-Pro-Base) |  | 4 | 0 | 2026-05-30 | — | **none** | 0 | 0 |  |
| 266 | [anything098/DeepSeek-V4-Pro-Base](https://huggingface.co/anything098/DeepSeek-V4-Pro-Base) |  | 4 | 0 | 2026-06-14 | — | **none** | 0 | 0 |  |
| 267 | [Umbasa/DeepSeek-V4-Pro-Base-UMBASA-V1](https://huggingface.co/Umbasa/DeepSeek-V4-Pro-Base-UMBASA-V1) |  | 4 | 1 | 2026-07-25 | — | **none** | 0 | 0 |  |
| 268 | [xwu-intel/DeepSeek-V4-Pro-MXFP4-Mixed-CT-AutoRound-4layers](https://huggingface.co/xwu-intel/DeepSeek-V4-Pro-MXFP4-Mixed-CT-AutoRound-4layers) |  | 3 | 0 | 2026-07-10 | — | **none** | 0 | 0 |  |
| 269 | [sorosh2salehi/DeepSeek-V4-Pro-Base](https://huggingface.co/sorosh2salehi/DeepSeek-V4-Pro-Base) |  | 3 | 0 | 2026-07-18 | — | **none** | 0 | 0 |  |
| 270 | [song2025/qwen3-4b-2507-lora-sft-sft_deepseek-v4-pro_best_1models_score1plus_idx0-199](https://huggingface.co/song2025/qwen3-4b-2507-lora-sft-sft_deepseek-v4-pro_best_1models_score1plus_idx0-199) |  | 2 | 0 | 2026-06-13 | — | 1799 | 0 | 2 |  |
| 271 | [FlagRelease/DeepSeek-V4-Pro-mthreads-FlagOS](https://huggingface.co/FlagRelease/DeepSeek-V4-Pro-mthreads-FlagOS) |  | 0 | 0 | 2026-04-28 | — | 8442 | 0 | 2 |  |
| 272 | [FlagRelease/DeepSeek-V4-Pro-ascend-FlagOS](https://huggingface.co/FlagRelease/DeepSeek-V4-Pro-ascend-FlagOS) |  | 0 | 0 | 2026-05-06 | — | 9875 | 0 | 3 |  |
| 273 | [FlagRelease/DeepSeek-V4-Pro-metax-FlagOS](https://huggingface.co/FlagRelease/DeepSeek-V4-Pro-metax-FlagOS) |  | 0 | 0 | 2026-04-27 | — | 8701 | 0 | 2 |  |
| 274 | [FlagRelease/DeepSeek-V4-Pro-hygon-FlagOS](https://huggingface.co/FlagRelease/DeepSeek-V4-Pro-hygon-FlagOS) |  | 0 | 0 | 2026-05-02 | — | 8648 | 0 | 2 |  |
| 275 | [Divinci-AI/deepseek-v4-pro-vindex](https://huggingface.co/Divinci-AI/deepseek-v4-pro-vindex) |  | 0 | 2 | 2026-04-26 | mit | 2717 | 0 | 3 |  |
| 276 | [ANguyenPERen/DeepSeek-V4-Pro](https://huggingface.co/ANguyenPERen/DeepSeek-V4-Pro) |  | 0 | 0 | 2026-04-28 | mit | **none** | 0 | 0 |  |
| 277 | [AS78/DeepSeek-V4-Pro](https://huggingface.co/AS78/DeepSeek-V4-Pro) |  | 0 | 0 | 2026-04-28 | mit | **none** | 0 | 0 |  |
| 278 | [Divinci-AI/deepseek-v4-pro-vindex-browse](https://huggingface.co/Divinci-AI/deepseek-v4-pro-vindex-browse) |  | 0 | 0 | 2026-04-28 | — | **none** | 0 | 0 |  |
| 279 | [Jibbalit/DeepSeek-V4-Pro-WaveTank](https://huggingface.co/Jibbalit/DeepSeek-V4-Pro-WaveTank) |  | 0 | 0 | 2026-05-10 | — | **none** | 0 | 0 |  |
| 280 | [linjing0514/DeepSeek-V4-Pro](https://huggingface.co/linjing0514/DeepSeek-V4-Pro) |  | 0 | 0 | 2026-05-18 | mit | **none** | 0 | 0 |  |
| 281 | [yrrhall/DeepSeek-V4-Pro-Backup](https://huggingface.co/yrrhall/DeepSeek-V4-Pro-Backup) |  | 0 | 0 | 2026-05-20 | mit | 21 | 0 | 0 |  |
| 282 | [abdurrehman456/deepseek-v4pro-supermodel](https://huggingface.co/abdurrehman456/deepseek-v4pro-supermodel) |  | 0 | 0 | 2026-05-30 | — | **none** | 0 | 0 |  |
| 283 | [FoxlightAI/deepseek-v4-pro-mtp](https://huggingface.co/FoxlightAI/deepseek-v4-pro-mtp) |  | 0 | 0 | 2026-06-03 | mit | 1899 | 0 | 2 |  |
| 284 | [wangsumyuen/Deepseek-V4-Pro](https://huggingface.co/wangsumyuen/Deepseek-V4-Pro) |  | 0 | 0 | 2026-06-03 | — | **none** | 0 | 0 |  |
| 285 | [SingularityPrinciple/DeepSeek-V4-Pro-NZFC-Evolve](https://huggingface.co/SingularityPrinciple/DeepSeek-V4-Pro-NZFC-Evolve) |  | 0 | 0 | 2026-06-12 | cc-by-nc-4.0 | 3788 | 0 | 2 |  |
| 286 | [song2025/qwen3-4b-2507-lora-sft-sft_deepseek-v4-pro_and_rewrite_all_2models_score2plus_idx0-199](https://huggingface.co/song2025/qwen3-4b-2507-lora-sft-sft_deepseek-v4-pro_and_rewrite_all_2models_score2plus_idx0-199) |  | 0 | 0 | 2026-06-13 | — | 1876 | 0 | 2 |  |
| 287 | [Mojtaba1987/DeepSeek-V4-Pro](https://huggingface.co/Mojtaba1987/DeepSeek-V4-Pro) |  | 0 | 0 | 2026-06-21 | mit | 21 | 0 | 0 |  |
| 288 | [cxfcxf/Qwen3.6-27b-deepseekV4Pro-Distill](https://huggingface.co/cxfcxf/Qwen3.6-27b-deepseekV4Pro-Distill) |  | 0 | 0 | 2026-06-29 | mit | 21 | 0 | 0 |  |
| 289 | [INCModel/DeepSeek-V4-Pro-DSpark-MXFP4-Mixed-CT-AutoRound](https://huggingface.co/INCModel/DeepSeek-V4-Pro-DSpark-MXFP4-Mixed-CT-AutoRound) |  | 0 | 0 | 2026-06-30 | — | **none** | 0 | 0 |  |
| 290 | [huyquang1235/DeepSeek-V4-Pro-Base-bucket](https://huggingface.co/huyquang1235/DeepSeek-V4-Pro-Base-bucket) |  | 0 | 0 | 2026-07-13 | — | **none** | 0 | 0 |  |
| 291 | [ObversaryStudiosOrg/cns-deepseek-v4-pro](https://huggingface.co/ObversaryStudiosOrg/cns-deepseek-v4-pro) |  | 0 | 0 | 2026-07-16 | mit | 21 | 0 | 0 |  |
| 292 | [aicoder43210/DeepSeek-V4-Pro-0.5B-A0.37B-Coder](https://huggingface.co/aicoder43210/DeepSeek-V4-Pro-0.5B-A0.37B-Coder) |  | 0 | 0 | 2026-08-05 | — | **none** | 0 | 0 |  |
| 293 | [cnrai/DeepSeek-V4-Pro-0813-MXFP8-MLX](https://huggingface.co/cnrai/DeepSeek-V4-Pro-0813-MXFP8-MLX) |  | 0 | 0 | 2026-08-14 | mit | 21 | 0 | 0 |  |
| 294 | [guruswami-ai/deepseek-v4-pro-0813-mlx-tp4-recipe](https://huggingface.co/guruswami-ai/deepseek-v4-pro-0813-mlx-tp4-recipe) |  | 0 | 1 | 2026-08-14 | mit | 5276 | 0 | 4 |  |
| 295 | [invi-bhagyesh/qwen-2.5-7b-it-msm-deepseek-v4-pro-goodness-goodness](https://huggingface.co/invi-bhagyesh/qwen-2.5-7b-it-msm-deepseek-v4-pro-goodness-goodness) |  | 0 | 0 | 2026-08-29 | — | **none** | 0 | 0 |  |

Top re-uploaders: `mlx-community` (12), `mradermacher` (5), `FlagRelease` (5), `deepseek-ai` (4), `unsloth` (4), `Jackrong` (4), `nvidia` (3), `Evilcarbon` (3).

## Discussions

All 281 threads, by artifact count then comment count. `A` = artifact kinds (0–6), `PR` marks a pull request, `Vend` marks a reply from a `deepseek-ai` org member.

| # | A | Title | Author | Repo | Date | Status | Type | Provenance | Lang | PR | Vend | 💬 | Chars |
| ---: | ---: | --- | --- | --- | --- | --- | --- | --- | :-: | :-: | :-: | ---: | ---: |
| 1 | 3 | [这是偷摸改啥文件了，哈哈哈](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/5) | `beijizhidayww` | DeepSeek-V4-Pro-0813 | 2026-08-13 | open | other/comment | unattributed | zh |  |  | 4 | 3908 |
| 2 | 3 | [Architectural Issue](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-DSpark/discussions/3) | `cloudyu` | DeepSeek-V4-Pro-DSpark | 2026-06-28 | open | community bug report | unattributed | en |  |  | 3 | 2571 |
| 3 | 3 | [Q4/Q8 hybrid GGUF shards](https://huggingface.co/unsloth/DeepSeek-V4-Pro-0813-GGUF/discussions/5) | `Bacruru` | DeepSeek-V4-Pro-0813-G | 2026-08-28 | open | community bug report | unattributed | en |  |  | 2 | 25175 |
| 4 | 3 | [Technical Report Summary](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/129) | `mishig` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 5743 |
| 5 | 3 | [Fix chat_template crash when assistant message omits](https://huggingface.co/FlagRelease/DeepSeek-V4-Pro-nvidia-FlagOS/discussions/1) | `qgallouedec` | DeepSeek-V4-Pro-nvidia | 2026-05-07 | open | pull request | author's own use | en | Y |  | 1 | 2731 |
| 6 | 2 | [I'm very disappointed in this release](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/131) | `Dampfinchen` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 12 | 3614 |
| 7 | 2 | [nvidia/DeepSeek-V4-flash-NVFP4](https://huggingface.co/nvidia/DeepSeek-V4-Pro-NVFP4/discussions/1) | `mtcl` | DeepSeek-V4-Pro-NVFP4 | 2026-05-27 | open | usage question | unattributed | en |  |  | 7 | 392 |
| 8 | 2 | [知识截止时效性建议：模型需更紧密跟进开源生态动态](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/185) | `xbb19730559` | DeepSeek-V4-Pro | 2026-05-20 | open | other/comment | unattributed | zh |  |  | 4 | 899 |
| 9 | 2 | [Something wrong with Q3 or with your launcher?](https://huggingface.co/batiai/DeepSeek-V4-Pro-GGUF/discussions/2) | `krustik` | DeepSeek-V4-Pro-GGUF | 2026-06-01 | open | community bug report | author's own use | en |  |  | 4 | 10155 |
| 10 | 2 | [How to convert fp8 on Hopper?](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/67) | `whybeyoung` | DeepSeek-V4-Pro | 2026-04-24 | open | usage question | unattributed | en |  | Y | 2 | 130 |
| 11 | 2 | [Support other low-bit quantization methods?](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/151) | `kiwei91` | DeepSeek-V4-Pro | 2026-04-25 | open | usage question | unattributed | en |  |  | 2 | 340 |
| 12 | 2 | [Is this file size 247 GB correct for 8 bit, while 4-](https://huggingface.co/mlx-community/DeepSeek-V4-Pro-8bit/discussions/1) | `Seth-TW` | DeepSeek-V4-Pro-8bit | 2026-04-26 | open | usage question | unattributed | en |  |  | 2 | 1823 |
| 13 | 2 | [right quantization?](https://huggingface.co/teamblobfish/DeepSeek-V4-Pro-GGUF/discussions/1) | `JaayTee` | DeepSeek-V4-Pro-GGUF | 2026-05-11 | open | usage question | unattributed | en |  |  | 2 | 251 |
| 14 | 2 | [Lossless?](https://huggingface.co/canada-quant/DeepSeek-V4-Pro-NVFP4-FP8-MTP/discussions/1) | `lukealonso` | DeepSeek-V4-Pro-NVFP4- | 2026-05-26 | closed | usage question | unattributed | en |  |  | 2 | 2322 |
| 15 | 2 | [Why is the NVFP4 quantized version larger than the o](https://huggingface.co/nvidia/DeepSeek-V4-Pro-NVFP4/discussions/2) | `NexusITComp` | DeepSeek-V4-Pro-NVFP4 | 2026-06-24 | open | usage question | unattributed | en |  |  | 2 | 393 |
| 16 | 2 | [DeepSeek model output sometimes contains DSML tool-c](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/209) | `Sube126` | DeepSeek-V4-Pro | 2026-07-08 | open | community bug report | unattributed | en |  |  | 2 | 5189 |
| 17 | 2 | [deepseek v4 pro base often outputs <｜end▁of▁file｜>\n](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/11) | `sxqqslf` | DeepSeek-V4-Pro-Base | 2026-05-12 | open | other/comment | author's own use | en |  |  | 1 | 7002 |
| 18 | 2 | [Conversion question](https://huggingface.co/unsloth/DeepSeek-V4-Pro/discussions/1) | `krustik` | DeepSeek-V4-Pro | 2026-05-24 | open | usage question | unattributed | en |  |  | 1 | 3634 |
| 19 | 2 | [Add CHI-Bench eval results — agent harness: OpenAI A](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/197) | `hlnchen` | DeepSeek-V4-Pro | 2026-06-02 | open | pull request | unattributed | en | Y |  | 1 | 466 |
| 20 | 2 | [IDEA: Bitnet 1.58 (a4.8) version in future variants ](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-DSpark/discussions/6) | `apiarium` | DeepSeek-V4-Pro-DSpark | 2026-07-07 | open | usage question | unattributed | en |  |  | 1 | 907 |
| 21 | 2 | [Add community evaluation results for SWE-Bench Multi](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/213) | `nielsr` | DeepSeek-V4-Pro | 2026-08-10 | open | pull request | unattributed | en | Y |  | 1 | 513 |
| 22 | 2 | [Anyone actually run DeepSeek-V4-Pro (1.7T) locally? ](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/20) | `mcherong` | DeepSeek-V4-Pro-0813 | 2026-08-28 | open | usage question | unattributed | en |  |  | 1 | 291 |
| 23 | 1 | [所以我猜是混合精度加模型太大导致暂时还没有量化的模型出来](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/96) | `lzm1066258` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  | Y | 7 | 481 |
| 24 | 1 | [16 - 24B models with FP8 quantization](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/152) | `Duonglv` | DeepSeek-V4-Pro | 2026-04-26 | open | usage question | author's own use | en |  |  | 7 | 3920 |
| 25 | 1 | [做了一个免费试用的deepseek4.0的 chat  大家可以自己使用 https://hugging](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/121) | `wangsheng` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 6 | 783 |
| 26 | 1 | [今天 API 部署的 v4pro 正式版能力不及预期，与这里的参数修复有关吗](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/11) | `yaindrop` | DeepSeek-V4-Pro-0813 | 2026-08-13 | closed | other/comment | unattributed | zh |  |  | 5 | 1425 |
| 27 | 1 | [Not able to run deepseek v4 pro using transformers i](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/95) | `chandu8848` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | author's own use | en |  | Y | 3 | 753 |
| 28 | 1 | [Where is HCA implemented?](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/161) | `lsh-algorithm` | DeepSeek-V4-Pro | 2026-04-30 | open | usage question | unattributed | en |  |  | 3 | 1163 |
| 29 | 1 | [lets goo](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/7) | `dendritical` | DeepSeek-V4-Pro-0813 | 2026-08-13 | open | other/comment | unattributed | en |  |  | 3 | 452 |
| 30 | 1 | [config.json 和deepseek-ai/DeepSeek-V4-Pro-DSpark配置似乎有](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/4) | `Gczmy` | DeepSeek-V4-Pro-0813 | 2026-08-13 | closed | other/comment | unattributed | en |  | Y | 3 | 249 |
| 31 | 1 | [original model](https://huggingface.co/unsloth/DeepSeek-V4-Pro-0813-GGUF/discussions/1) | `Lambus1` | DeepSeek-V4-Pro-0813-G | 2026-08-13 | open | usage question | unattributed | en |  |  | 3 | 189 |
| 32 | 1 | [Smaller quants?](https://huggingface.co/unsloth/DeepSeek-V4-Pro-0813-GGUF/discussions/3) | `MB7977` | DeepSeek-V4-Pro-0813-G | 2026-08-15 | open | usage question | unattributed | en |  |  | 3 | 379 |
| 33 | 1 | [Is Engram included in V4?](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/98) | `fcMpKYz6Avp5QK` | DeepSeek-V4-Pro | 2026-04-24 | open | usage question | unattributed | en |  |  | 2 | 405 |
| 34 | 1 | [deepseek-ai/DeepSeek-V4-Pro](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/153) | `cmax123` | DeepSeek-V4-Pro | 2026-04-26 | draft | pull request | unattributed | en | Y |  | 2 | 14 |
| 35 | 1 | [Question on quantization](https://huggingface.co/batiai/DeepSeek-V4-Pro-GGUF/discussions/1) | `x-polyglot-x` | DeepSeek-V4-Pro-GGUF | 2026-05-18 | open | usage question | unattributed | en |  |  | 2 | 632 |
| 36 | 1 | [yarn context interpolation enabled in gguf](https://huggingface.co/unsloth/DeepSeek-V4-Pro-0813-GGUF/discussions/4) | `Bacruru` | DeepSeek-V4-Pro-0813-G | 2026-08-25 | closed | usage question | unattributed | en |  |  | 2 | 183 |
| 37 | 1 | [Add community evaluation results for GPQA, GSM8K, HL](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/110) | `nielsr` | DeepSeek-V4-Pro | 2026-04-24 | open | pull request | unattributed | en | Y |  | 1 | 826 |
| 38 | 1 | [Add YC-Bench benchmark result (avg $1,066,426)](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/165) | `RiddleHe` | DeepSeek-V4-Pro | 2026-05-01 | open | pull request | unattributed | en | Y |  | 1 | 250 |
| 39 | 1 | [Question about causal safety in DeepSeek-V4 CSA pref](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/172) | `Prachi01` | DeepSeek-V4-Pro | 2026-05-10 | open | other/comment | unattributed | en |  |  | 1 | 1153 |
| 40 | 1 | [Critical Feedback: Romanticizing Self-Harm & Overly ](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/181) | `Orange-Oracle` | DeepSeek-V4-Pro | 2026-05-17 | open | other/comment | unattributed | en |  |  | 1 | 1601 |
| 41 | 1 | [Add ResearchClawBench evaluation result](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/186) | `black-yt` | DeepSeek-V4-Pro | 2026-05-21 | open | pull request | unattributed | en | Y |  | 1 | 1023 |
| 42 | 1 | [🚀 ms-swift Provides DeepSeek-V4 Fine-tuning Practice](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/193) | `study-hjt` | DeepSeek-V4-Pro | 2026-05-27 | open | other/comment | unattributed | en |  |  | 1 | 231 |
| 43 | 1 | [Deploy deepseek-v4-pro in aws sagemaker](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/199) | `tharun-swg` | DeepSeek-V4-Pro | 2026-06-09 | open | other/comment | unattributed | en |  |  | 1 | 165 |
| 44 | 1 | [Can we deploy on AMD Mi300x GPU](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/200) | `review4cv` | DeepSeek-V4-Pro | 2026-06-11 | open | usage question | author's own use | en |  |  | 1 | 294 |
| 45 | 1 | [Raw <ds_safety> safety metadata tag exposed in model](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/201) | `mrshadowc` | DeepSeek-V4-Pro | 2026-06-15 | open | other/comment | unattributed | en |  |  | 1 | 981 |
| 46 | 1 | [架构问题](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-DSpark/discussions/2) | `cloudyu` | DeepSeek-V4-Pro-DSpark | 2026-06-28 | open | other/comment | unattributed | zh |  |  | 1 | 135 |
| 47 | 1 | [Report](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/207) | `amuhlia` | DeepSeek-V4-Pro | 2026-07-04 | open | other/comment | unattributed | es |  |  | 1 | 98 |
| 48 | 1 | [Is recent "DeepSeek-V4-正式版" going to be open source?](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/211) | `ghostplant` | DeepSeek-V4-Pro | 2026-07-18 | closed | usage question | unattributed | en |  |  | 1 | 1 |
| 49 | 1 | [送一个字：淦](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/12) | `makgad` | DeepSeek-V4-Pro-0813 | 2026-08-13 | closed | other/comment | unattributed | zh |  |  | 1 | 110 |
| 50 | 1 | [我已做ds pro 0814,ds flash 0731,qwen3.6 he微调silicon-rid](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/16) | `TAOTAO777` | DeepSeek-V4-Pro-0813 | 2026-08-14 | open | other/comment | unattributed | en |  |  | 1 | 140 |
| 51 | 0 | [Will there be small models like 12b?](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/164) | `Crownelius` | DeepSeek-V4-Pro | 2026-05-01 | open | usage question | author's own use | en |  |  | 16 | 6923 |
| 52 | 0 | [ds现在真的是拉完了，全面落后](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/90) | `RealBar` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 13 | 943 |
| 53 | 0 | [Общение](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/149) | `Lev0478` | DeepSeek-V4-Pro | 2026-04-25 | open | usage question | unattributed | ru |  |  | 12 | 424 |
| 54 | 0 | [思考链下会出现英文混乱](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/160) | `smodeltest` | DeepSeek-V4-Pro | 2026-04-30 | open | other/comment | unattributed | zh |  |  | 8 | 391 |
| 55 | 0 | [Thank You, DeepSeek! Empower Local Open Source with ](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/168) | `VaLtEc-BoY` | DeepSeek-V4-Pro | 2026-05-04 | open | other/comment | unattributed | en |  |  | 6 | 2608 |
| 56 | 0 | [Instruction following still not good](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/145) | `xcx0902` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | author's own use | en |  |  | 5 | 466 |
| 57 | 0 | [有一处明显笔误](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/109) | `chenzihong` | DeepSeek-V4-Pro | 2026-04-24 | open | usage question | unattributed | en |  | Y | 5 | 462 |
| 58 | 0 | [敬你是条汉子没有4.30当天发](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/81) | `cjqpker` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 5 | 62 |
| 59 | 0 | [有人知道用的哪家的芯片吗？](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/63) | `KaneHan` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 5 | 275 |
| 60 | 0 | [大家也早点休息吧](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/6) | `bortor` | DeepSeek-V4-Pro-0813 | 2026-08-13 | open | other/comment | unattributed | zh |  |  | 5 | 1165 |
| 61 | 0 | [开源的模型可以自己去评测，闭源的模型怎么测试呢？最近扎堆发布，GPT5.5，HY3.0 Preview，](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/140) | `dennisbo` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 4 | 218 |
| 62 | 0 | [训练也是昇腾吗？](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/115) | `yxdys` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 4 | 212 |
| 63 | 0 | [源神启动！恭喜deepseekV4顺利上线，合影！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/150) | `JCrainy` | DeepSeek-V4-Pro | 2026-04-25 | open | other/comment | unattributed | zh |  |  | 4 | 95 |
| 64 | 0 | [Creative writing — a step back from V3.2](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/179) | `Gantolandon` | DeepSeek-V4-Pro | 2026-05-16 | open | other/comment | author's own use | en |  |  | 4 | 2369 |
| 65 | 0 | [Update vLLM recipe link](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/8) | `jeeejeee` | DeepSeek-V4-Pro-0813 | 2026-08-13 | merged | pull request | unattributed | en | Y |  | 4 | 39 |
| 66 | 0 | [base是什么意思呢？](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/1) | `lix` | DeepSeek-V4-Pro-Base | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 3 | 31 |
| 67 | 0 | [核弹 椅子 摔 瘫坐](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/144) | `shishen` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 3 | 32 |
| 68 | 0 | [代码能力真的是世界第一吗！！！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/141) | `LumiDriz` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 3 | 30 |
| 69 | 0 | [Legendary drop](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/128) | `kamell` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 3 | 454 |
| 70 | 0 | [关于 "Observations and Proposals" 中激活函数建议的疑问：去掉 gate p](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/126) | `MarjorTom` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  | Y | 3 | 1525 |
| 71 | 0 | [Is it uses engrams?](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/122) | `Regrin` | DeepSeek-V4-Pro | 2026-04-24 | open | usage question | unattributed | en |  |  | 3 | 305 |
| 72 | 0 | [Real Open AI](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/114) | `sloango` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 3 | 86 |
| 73 | 0 | [Waiting for Distill  10B \ 35B \70B](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/93) | `JerryShi2077` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 3 | 324 |
| 74 | 0 | [合影！！！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/88) | `elninot9` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 3 | 58 |
| 75 | 0 | [体验了会儿V4，我仿佛看到核弹炸在眼前然后从椅子上摔下来，瘫坐在地！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/74) | `RyanDong` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 3 | 313 |
| 76 | 0 | [我仿佛看到核弹炸在眼前，然后从椅子上摔下来，瘫坐在地](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/31) | `mounde` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 3 | 195 |
| 77 | 0 | [伟大，无需多言。源神启动！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/24) | `Kennyp-Chen` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 3 | 160 |
| 78 | 0 | [Is there a mismatch between tech report and config.j](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/20) | `FrankYan0824` | DeepSeek-V4-Pro | 2026-04-24 | open | community bug report | unattributed | en |  | Y | 3 | 514 |
| 79 | 0 | [求32B小模型，感谢！ Need 32B mini V4 ,Thanks!](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/11) | `Arthurandhavefun` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 3 | 149 |
| 80 | 0 | [The whale is back](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/3) | `stanleys09` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 3 | 183 |
| 81 | 0 | [越用越觉得好用](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/176) | `BlackLeee` | DeepSeek-V4-Pro | 2026-05-14 | open | other/comment | unattributed | zh |  |  | 3 | 20 |
| 82 | 0 | [DeepSeek Training Support](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/192) | `SuperXr` | DeepSeek-V4-Pro | 2026-05-26 | open | usage question | author's own use | en |  |  | 3 | 935 |
| 83 | 0 | [Add chat template](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/146) | `Rocketknight1` | DeepSeek-V4-Pro | 2026-04-24 | open | pull request | unattributed | en | Y |  | 2 | 156 |
| 84 | 0 | [Is it possible to have API output with origin comple](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/143) | `httpwwwfszyc` | DeepSeek-V4-Pro | 2026-04-24 | open | usage question | unattributed | en |  |  | 2 | 158 |
| 85 | 0 | [Help me recover my deepseek account](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/125) | `lulavc` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 2 | 391 |
| 86 | 0 | [牛逼！！！！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/117) | `miniwhite` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 2 | 35 |
| 87 | 0 | [合影，感谢源神再运玄功](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/111) | `Taihe2023` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 2 | 68 |
| 88 | 0 | [即使引导早已破碎，也请您当上大语言模型之王。](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/105) | `Centerful` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | fr |  |  | 2 | 16 |
| 89 | 0 | [让算了算北京新能源积分是多少，v4、gemini、豆包都沦陷了](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/102) | `famer058` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 2 | 38 |
| 90 | 0 | [坐等27B量化，坐等Jackrong大佬蒸馏Opus^_^](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/92) | `DeveAIer` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 2 | 34 |
| 91 | 0 | [对不起了GLM token plan，我将拥抱开源之源神](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/84) | `Edison0916` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 2 | 53 |
| 92 | 0 | [862B?](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/75) | `smile1030` | DeepSeek-V4-Pro | 2026-04-24 | open | usage question | unattributed | en |  |  | 2 | 231 |
| 93 | 0 | [AI Agent 何时出现？](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/70) | `KakumuraArimura` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 2 | 85 |
| 94 | 0 | [我真的太想用便宜高效的模型了，我tm做梦都想啊](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/46) | `cd5767` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 2 | 31 |
| 95 | 0 | [踏马的甘，终于等到你](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/43) | `jedanny` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 2 | 20 |
| 96 | 0 | [合影，源神](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/41) | `Elysia66636` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 2 | 12 |
| 97 | 0 | [男人！什么罐头我说！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/29) | `shenjiarun` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | ceb |  |  | 2 | 44 |
| 98 | 0 | [Update index_topk to 1024](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/25) | `FrankYan0824` | DeepSeek-V4-Pro | 2026-04-24 | closed | pull request | unattributed | en | Y | Y | 2 | 329 |
| 99 | 0 | [源神启动](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/18) | `GAOxy` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 2 | 13 |
| 100 | 0 | [再一次伟大](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/17) | `asher345` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 2 | 31 |
| 101 | 0 | [源神伟大](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/8) | `BlindTomas` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | ja |  |  | 2 | 12 |
| 102 | 0 | [合影，感谢 DeepSeek](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/5) | `ExDragine` | DeepSeek-V4-Pro | 2026-04-24 | closed | other/comment | unattributed | zh |  |  | 2 | 40 |
| 103 | 0 | [Request: DOI](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/154) | `duzhuang2012` | DeepSeek-V4-Pro | 2026-04-26 | closed | other/comment | unattributed | zh |  |  | 2 | 6 |
| 104 | 0 | [什么时候支持api上传文档就好了](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/156) | `icbw` | DeepSeek-V4-Pro | 2026-04-27 | open | other/comment | unattributed | zh |  |  | 2 | 82 |
| 105 | 0 | [Assigned weights for different teachers. 教师权重的分配](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/162) | `lsh-algorithm` | DeepSeek-V4-Pro | 2026-04-30 | open | other/comment | unattributed | en |  |  | 2 | 873 |
| 106 | 0 | [Performance feedback](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/166) | `toton12` | DeepSeek-V4-Pro | 2026-05-02 | open | other/comment | unattributed | en |  |  | 2 | 123 |
| 107 | 0 | [Too much positivity bias](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/169) | `Monblant` | DeepSeek-V4-Pro | 2026-05-06 | open | other/comment | unattributed | en |  |  | 2 | 1100 |
| 108 | 0 | [Systemic Defect: False Promises and Emotional Deflec](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/180) | `Orange-Oracle` | DeepSeek-V4-Pro | 2026-05-17 | open | other/comment | unattributed | en |  |  | 2 | 2104 |
| 109 | 0 | [将部份逻辑处理任务释放到 LLM 之外（计算外置）](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/189) | `lanesun` | DeepSeek-V4-Pro | 2026-05-23 | open | other/comment | unattributed | zh |  |  | 2 | 2251 |
| 110 | 0 | [main](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/195) | `Nivensio` | DeepSeek-V4-Pro | 2026-05-29 | draft | pull request | unattributed | en | Y |  | 2 | 4 |
| 111 | 0 | [Listed on OpenModelMap](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/203) | `duola15` | DeepSeek-V4-Pro | 2026-06-20 | open | other/comment | unattributed | en |  |  | 2 | 214 |
| 112 | 0 | [Can we simply download only the newly added shards?](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-DSpark/discussions/1) | `alone-wl` | DeepSeek-V4-Pro-DSpark | 2026-06-27 | open | usage question | unattributed | en |  |  | 2 | 603 |
| 113 | 0 | [Update README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/212) | `kobelg` | DeepSeek-V4-Pro | 2026-07-24 | closed | pull request | unattributed | en | Y |  | 2 | 26 |
| 114 | 0 | [GA难道真被隐去了？？](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/9) | `windyspringlick` | DeepSeek-V4-Pro-0813 | 2026-08-13 | open | other/comment | unattributed | zh |  |  | 2 | 85 |
| 115 | 0 | [mistype in comparison table - the Flash variant has ](https://huggingface.co/unsloth/DeepSeek-V4-Pro-0813-GGUF/discussions/2) | `vovan2` | DeepSeek-V4-Pro-0813-G | 2026-08-13 | open | other/comment | unattributed | en |  |  | 2 | 21 |
| 116 | 0 | [This vs ornith 1.5 9b](https://huggingface.co/Jackrong/DeepSeek-V4-Pro-Qwen3.5-9B/discussions/1) | `BazsiBazsi` | DeepSeek-V4-Pro-Qwen3. | 2026-08-24 | open | comparison | unattributed | en |  |  | 2 | 175 |
| 117 | 0 | [Create README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/6) | `cool666666` | DeepSeek-V4-Pro-Base | 2026-04-24 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 118 | 0 | [powerful!](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/5) | `howcanitrustyou` | DeepSeek-V4-Pro-Base | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 9 |
| 119 | 0 | [合影+1](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/4) | `MasterHu996` | DeepSeek-V4-Pro-Base | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 12 |
| 120 | 0 | [合影留恋](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/3) | `pymo` | DeepSeek-V4-Pro-Base | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 8 |
| 121 | 0 | [Create README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/2) | `Caxson` | DeepSeek-V4-Pro-Base | 2026-04-24 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 122 | 0 | [Update README.md to add SGLang deployment option](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/148) | `zjxia` | DeepSeek-V4-Pro | 2026-04-24 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 123 | 0 | [Add pipeline tag to allow for HF Inference Providers](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/147) | `nbroad` | DeepSeek-V4-Pro | 2026-04-24 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 124 | 0 | [恭喜deepseek v4可以撑地了](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/142) | `keflag` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 64 |
| 125 | 0 | [恭喜！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/139) | `luolita13` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 3 |
| 126 | 0 | [恭喜上线](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/138) | `wSi0n` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | ja |  |  | 1 | 13 |
| 127 | 0 | [期望能跑在昇腾上](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/137) | `wSi0n` | DeepSeek-V4-Pro | 2026-04-24 | closed | other/comment | unattributed | zh |  |  | 1 | 7 |
| 128 | 0 | [GOOD JOB!](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/136) | `Friedland` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 9 |
| 129 | 0 | [恭喜恭喜](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/135) | `ryw001` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 4 |
| 130 | 0 | [deepseek niu bee plus](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/134) | `shanxinle` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | de |  |  | 1 | 6 |
| 131 | 0 | [V4必火！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/133) | `yvanw` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 5 |
| 132 | 0 | [火钳流明](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/132) | `leonz03` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 2 |
| 133 | 0 | [DeepSeek 666](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/130) | `dingwenzheng` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 20 |
| 134 | 0 | [合影留念~~~](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/127) | `BI9CZR` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 7 |
| 135 | 0 | [请问是否有计划出自己的coding plan？](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/124) | `jackz990` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 23 |
| 136 | 0 | [V4留念 ~~~](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/123) | `jackz990` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 13 |
| 137 | 0 | [用国外模型研究国产模型，也是支持国产了](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/120) | `2025carry` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 19 |
| 138 | 0 | [蹲前排](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/119) | `VenusZ` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | ja |  |  | 1 | 3 |
| 139 | 0 | [WE WERE HERE](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/118) | `FRareDom2` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 44 |
| 140 | 0 | [合影留念](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/116) | `usst-ziyi` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 11 |
| 141 | 0 | [我先睡了](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/113) | `maolonchen` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | pt |  |  | 1 | 6 |
| 142 | 0 | [什么时候出token plan，感觉有点小贵了，烧不起。](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/112) | `zhangliu` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 28 |
| 143 | 0 | [源神！合影，再出发！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/108) | `ai-fast` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 10 |
| 144 | 0 | [合影~](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/107) | `qiuyuanchen` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 8 |
| 145 | 0 | [恭喜！！！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/106) | `cainiaochaocai` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 4 |
| 146 | 0 | [前排合影！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/104) | `taostronger` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 15 |
| 147 | 0 | [deepseek王者归来](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/103) | `fanalvin` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 1 |
| 148 | 0 | [I just came](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/101) | `cinnybun02` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 49 |
| 149 | 0 | [开源伟大！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/100) | `zhuaoqi` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 12 |
| 150 | 0 | [deepseek，为你骄傲](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/99) | `kanghongyun` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 20 |
| 151 | 0 | [等了好久终于来了](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/97) | `SeanKa` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 6 |
| 152 | 0 | [good job!!!](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/94) | `FightKK` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 4 |
| 153 | 0 | [合影来了](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/91) | `YANNICKsong` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 21 |
| 154 | 0 | [好用吗](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/89) | `jasonxij` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 2 |
| 155 | 0 | [牛逼，开源精神伟大](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/87) | `zesure` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 2 |
| 156 | 0 | [终于等到你，v4合影](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/86) | `NoNameLeGo` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | hu |  |  | 1 | 4 |
| 157 | 0 | [为开源之光点赞](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/85) | `dannyhang` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 7 |
| 158 | 0 | [合影合影](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/83) | `zz659749` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 5 |
| 159 | 0 | [恭喜DeepSeek国王陛下于今日抵达他忠实的抱抱脸](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/82) | `oldshun` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | de |  |  | 1 | 1 |
| 160 | 0 | [Its cost is too low](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/80) | `nbcool` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 33 |
| 161 | 0 | [我超，源！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/79) | `SQA-CHN` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | yue |  |  | 1 | 5 |
| 162 | 0 | [WOW 1.6T Params](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/78) | `Ivanye13671` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 12 |
| 163 | 0 | [向 DS 致敬 (^^ゞ](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/77) | `zhao04` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 5 |
| 164 | 0 | [前排合影](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/76) | `ZMYSTIC` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 7 |
| 165 | 0 | [Base都开源了 太大方了 致敬](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/73) | `cloudyu` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 2 |
| 166 | 0 | [在此迎接开源的王](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/72) | `Maxwell-Horace` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 4 |
| 167 | 0 | [王振兴在此祝贺DeepSeek](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/71) | `wangzhenxing4` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 5 |
| 168 | 0 | [make ds greate again](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/69) | `Daerbeida` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 2 |
| 169 | 0 | [DeepSeek威武，中国威武，终于等到你](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/68) | `BingoOKay` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 2 |
| 170 | 0 | [他妈的甘，我的苦日子终于到头了](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/66) | `EugeLam` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 25 |
| 171 | 0 | [ds上号](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/65) | `Kelt2050` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | ja |  |  | 1 | 2 |
| 172 | 0 | [源神牛逼](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/64) | `LightTang` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | ja |  |  | 1 | 4 |
| 173 | 0 | [终于来了~](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/62) | `zhubao315` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 5 |
| 174 | 0 | [就看哪家厂商的code plan能让我用上了](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/61) | `FevolQ` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 12 |
| 175 | 0 | [真 国货之光](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/60) | `Roccc` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 51 |
| 176 | 0 | [牛皮！合影留念](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/59) | `FakeRisk` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | ja |  |  | 1 | 6 |
| 177 | 0 | [未来已来](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/58) | `baipengyan` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 11 |
| 178 | 0 | [合影留念](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/57) | `pengzhi27` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | no |  |  | 1 | 3 |
| 179 | 0 | [牛逼！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/56) | `HarrytheCreep` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 16 |
| 180 | 0 | [合影！！！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/55) | `orchid9` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | fr |  |  | 1 | 4 |
| 181 | 0 | [deepseek 牛逼](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/54) | `liunianxuxie` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | fr |  |  | 1 | 11 |
| 182 | 0 | [立刻开始做空NVIDIA](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/53) | `wan9hao` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 23 |
| 183 | 0 | [合影！！！！！！！！！！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/52) | `taoshilei` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 12 |
| 184 | 0 | [牛逼！开源真超过闭源了](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/51) | `x-9c` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 11 |
| 185 | 0 | [网页版更新下ocr吧](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/50) | `codeliucf` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 37 |
| 186 | 0 | [man! gan !](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/49) | `piamo` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 19 |
| 187 | 0 | [合影合影](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/48) | `ai-hyz` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 1 |
| 188 | 0 | [现在的当务之急](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/47) | `wdnmdSword` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 29 |
| 189 | 0 | [V4 IS COMING! BEG FOR DISTILLED MODELS!](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/45) | `dof-studio-org` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 39 |
| 190 | 0 | [“你打你的，我打我的”，期待实际效果](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/44) | `xiaoxsgo` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 2 |
| 191 | 0 | [终于.](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/42) | `jedanny` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 9 |
| 192 | 0 | [合影 V4大人你去把claude和chatgpt干掉！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/40) | `KaneHan` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 27 |
| 193 | 0 | [合影！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/39) | `Cherzing` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 8 |
| 194 | 0 | [我宣布，大模型进入百万上下文时代](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/38) | `ivan-gaoyifan` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 7 |
| 195 | 0 | [强大！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/37) | `chukk` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | wuu |  |  | 1 | 5 |
| 196 | 0 | [合影！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/36) | `92YinLU` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 2 |
| 197 | 0 | [Deepseek 爷爷用 v4 打掉 anthropic](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/35) | `LiZesheng` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | — |  |  | 1 | 28 |
| 198 | 0 | [今天是个好日子，合影！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/34) | `hakupro` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 11 |
| 199 | 0 | [最强开源选手登场](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/33) | `lxmisbest` | DeepSeek-V4-Pro | 2026-04-24 | closed | other/comment | unattributed | ja |  |  | 1 | 6 |
| 200 | 0 | [合影合影！不好好做模型的，看剑！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/32) | `pruidong` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 46 |
| 201 | 0 | [合影！！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/30) | `vasileone` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | ja |  |  | 1 | 14 |
| 202 | 0 | [超级英雄总是这样出场！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/28) | `marvel0324` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 4 |
| 203 | 0 | [合影！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/27) | `MaxwellOay` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 9 |
| 204 | 0 | [天下苦 ANTHROPIC 久已，让 DS 打掉他们的估值](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/26) | `henryleu` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 25 |
| 205 | 0 | [V4终于来了，希望国内顶尖模型越来越好](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/23) | `maikaaomi` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 19 |
| 206 | 0 | [Rename DeepSeek_V4.pdf to DeepSeek_V5.pdf](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/22) | `hanjja` | DeepSeek-V4-Pro | 2026-04-24 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 207 | 0 | [可以，终于等来了！看看怎么个事！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/21) | `Qixiaomao` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 8 |
| 208 | 0 | [Deepseek my beloved](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/19) | `amarosnithe` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 118 |
| 209 | 0 | [合影！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/16) | `guoxz22` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 5 |
| 210 | 0 | [梁文锋我爱你！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/15) | `tomlongnv` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 7 |
| 211 | 0 | [great Again](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/14) | `ace1Black` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 18 |
| 212 | 0 | [V4  终于来了！ 合影留念！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/13) | `Cheers` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | zh |  |  | 1 | 15 |
| 213 | 0 | [The whale is here again.](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/12) | `ColdJeans` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | ja |  |  | 1 | 4 |
| 214 | 0 | [97% needle in a haystack, beating or matching fronti](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/10) | `petmav` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | author's own use | en |  |  | 1 | 59 |
| 215 | 0 | [Open source never admits defeat！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/9) | `lenkin233` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 31 |
| 216 | 0 | [DeepSeek我爱你！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/7) | `k3Ep` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | it |  |  | 1 | 12 |
| 217 | 0 | [顶级！前排合影！！！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/6) | `martinyun666` | DeepSeek-V4-Pro | 2026-04-24 | closed | other/comment | unattributed | zh |  |  | 1 | 10 |
| 218 | 0 | [wow](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/4) | `longtaodemo` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 18 |
| 219 | 0 | [I originally thought it was just a fake news story, ](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/2) | `45min` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 96 |
| 220 | 0 | [We waited a whole year](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/1) | `khazic` | DeepSeek-V4-Pro | 2026-04-24 | open | other/comment | unattributed | en |  |  | 1 | 22 |
| 221 | 0 | [Request: DOI](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/7) | `Wibby` | DeepSeek-V4-Pro-Base | 2026-04-27 | closed | usage question | unattributed | fr |  |  | 1 | 12 |
| 222 | 0 | [模型文件注释里的形状似乎写错了](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/158) | `yzll` | DeepSeek-V4-Pro | 2026-04-28 | open | other/comment | unattributed | en |  |  | 1 | 152 |
| 223 | 0 | [Create README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/8) | `mohammed2449` | DeepSeek-V4-Pro-Base | 2026-04-29 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 224 | 0 | [Partial Rotary Positional Embedding 的笔误？](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/159) | `WKQ9411` | DeepSeek-V4-Pro | 2026-04-29 | open | other/comment | unattributed | zh |  |  | 1 | 175 |
| 225 | 0 | [test](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/163) | `Swisskimm` | DeepSeek-V4-Pro | 2026-05-01 | closed | other/comment | unattributed | en |  |  | 1 | 5 |
| 226 | 0 | [Deepseek web issue](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/167) | `NukeNotNull` | DeepSeek-V4-Pro | 2026-05-02 | open | community bug report | unattributed | ms |  |  | 1 | 152 |
| 227 | 0 | [{ "scene_metadata": { "style": "traditional South In](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/9) | `starsignarts` | DeepSeek-V4-Pro-Base | 2026-05-08 | open | pull request | unattributed | en | Y |  | 1 | 116 |
| 228 | 0 | [Update README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/170) | `nerualll63` | DeepSeek-V4-Pro | 2026-05-09 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 229 | 0 | [Update 09/05/26: chat_template.jinja](https://huggingface.co/inferencerlabs/DeepSeek-V4-Pro-Preview-MLX-Q2i/discussions/1) | `inferencerlabs` | DeepSeek-V4-Pro-Previe | 2026-05-09 | open | other/comment | unattributed | en |  |  | 1 | 87 |
| 230 | 0 | [Create README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/10) | `DeusD` | DeepSeek-V4-Pro-Base | 2026-05-10 | closed | pull request | unattributed | en | Y |  | 1 | 0 |
| 231 | 0 | [123](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/171) | `Engler` | DeepSeek-V4-Pro | 2026-05-10 | closed | other/comment | unattributed | zh |  |  | 1 | 715 |
| 232 | 0 | [finance](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/174) | `SoloArise` | DeepSeek-V4-Pro | 2026-05-11 | draft | pull request | unattributed | en | Y |  | 1 | 0 |
| 233 | 0 | [Add Claw-Eval evaluation results](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/173) | `SaylorTwift` | DeepSeek-V4-Pro | 2026-05-11 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 234 | 0 | [Create README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/12) | `kartik1911` | DeepSeek-V4-Pro-Base | 2026-05-12 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 235 | 0 | [Fixed a type annotation.](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/175) | `LIghtJUNction` | DeepSeek-V4-Pro | 2026-05-12 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 236 | 0 | [Upload wms-pro-dashboard-template (1).zip](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/178) | `hamid2015` | DeepSeek-V4-Pro | 2026-05-15 | open | pull request | unattributed | fr | Y |  | 1 | 52 |
| 237 | 0 | [Upload 11 files](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/177) | `hamid2015` | DeepSeek-V4-Pro | 2026-05-15 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 238 | 0 | [Update README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/184) | `rayanayyara` | DeepSeek-V4-Pro | 2026-05-19 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 239 | 0 | [Update README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/183) | `rayanayyara` | DeepSeek-V4-Pro | 2026-05-19 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 240 | 0 | [Update README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/182) | `rayanayyara` | DeepSeek-V4-Pro | 2026-05-19 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 241 | 0 | [Update 20/05/26: chat_template.jinja](https://huggingface.co/inferencerlabs/DeepSeek-V4-Pro-Preview-MLX-Q2i/discussions/2) | `inferencerlabs` | DeepSeek-V4-Pro-Previe | 2026-05-20 | open | other/comment | unattributed | en |  |  | 1 | 84 |
| 242 | 0 | [Create README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/13) | `nitesh1712` | DeepSeek-V4-Pro-Base | 2026-05-21 | open | pull request | unattributed | en | Y |  | 1 | 43 |
| 243 | 0 | [Add WildClawBench evaluation result](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/187) | `yuhangzang` | DeepSeek-V4-Pro | 2026-05-22 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 244 | 0 | [Request: DOI](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/188) | `ZhangZZZ123` | DeepSeek-V4-Pro | 2026-05-23 | closed | other/comment | unattributed | en |  |  | 1 | 8 |
| 245 | 0 | [what about rust?](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/191) | `sh4downotfound` | DeepSeek-V4-Pro | 2026-05-25 | open | usage question | unattributed | en |  |  | 1 | 59 |
| 246 | 0 | [官方是否有兴趣帮忙改进完善一下Apple MLX框架的适配？](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/190) | `hehua2008` | DeepSeek-V4-Pro | 2026-05-25 | open | other/comment | unattributed | zh |  |  | 1 | 141 |
| 247 | 0 | [CRÉATION DE PLATE-FORME](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/194) | `RIJAHOERSON` | DeepSeek-V4-Pro | 2026-05-28 | open | other/comment | unattributed | fr |  |  | 1 | 141 |
| 248 | 0 | [Create README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/14) | `Mohepfy10` | DeepSeek-V4-Pro-Base | 2026-06-03 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 249 | 0 | [Add EvalEval community eval results](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/198) | `EvalEvalBot` | DeepSeek-V4-Pro | 2026-06-05 | closed | pull request | unattributed | en | Y |  | 1 | 113 |
| 250 | 0 | [Create README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/15) | `ArtOlo` | DeepSeek-V4-Pro-Base | 2026-06-07 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 251 | 0 | [Upload 15 files](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/202) | `Ananthusajeev190` | DeepSeek-V4-Pro | 2026-06-17 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 252 | 0 | [привет](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/16) | `vageavatarr` | DeepSeek-V4-Pro-Base | 2026-06-26 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 253 | 0 | [V4-Pro reasoning quality is remarkable — mobile impl](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/204) | `3morixd` | DeepSeek-V4-Pro | 2026-06-26 | open | usage question | unattributed | en |  |  | 1 | 560 |
| 254 | 0 | [Create README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/17) | `Akouba` | DeepSeek-V4-Pro-Base | 2026-06-29 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 255 | 0 | [model init](https://huggingface.co/amd/DeepSeek-V4-Pro-MXFP4/discussions/1) | `linzhao-amd` | DeepSeek-V4-Pro-MXFP4 | 2026-06-30 | draft | pull request | unattributed | en | Y |  | 1 | 0 |
| 256 | 0 | [model upload](https://huggingface.co/amd/DeepSeek-V4-Pro-NVFP4/discussions/1) | `linzhao-amd` | DeepSeek-V4-Pro-NVFP4 | 2026-06-30 | closed | pull request | unattributed | en | Y |  | 1 | 0 |
| 257 | 0 | [Create README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/18) | `aenigma99` | DeepSeek-V4-Pro-Base | 2026-07-03 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 258 | 0 | [Just an idea](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-DSpark/discussions/5) | `Ropsalot` | DeepSeek-V4-Pro-DSpark | 2026-07-03 | open | usage question | unattributed | en |  |  | 1 | 519 |
| 259 | 0 | [Update README.md to include vLLM snippet](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-DSpark/discussions/4) | `xianbao` | DeepSeek-V4-Pro-DSpark | 2026-07-03 | merged | pull request | unattributed | en | Y |  | 1 | 0 |
| 260 | 0 | [862B?](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/206) | `Mint-Keyphase` | DeepSeek-V4-Pro | 2026-07-04 | open | usage question | unattributed | en |  |  | 1 | 115 |
| 261 | 0 | [Add SkillsBench v1.1 evaluation result](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/205) | `bingran-you` | DeepSeek-V4-Pro | 2026-07-04 | open | pull request | unattributed | en | Y |  | 1 | 1137 |
| 262 | 0 | [Listed on OpenModelMap](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/208) | `duola15` | DeepSeek-V4-Pro | 2026-07-06 | open | other/comment | unattributed | en |  |  | 1 | 200 |
| 263 | 0 | [Create README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/19) | `77736374shen` | DeepSeek-V4-Pro-Base | 2026-07-07 | closed | pull request | unattributed | en | Y |  | 1 | 0 |
| 264 | 0 | [Add LHTB (Long-Horizon-Terminal-Bench) eval result](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/210) | `zli12321` | DeepSeek-V4-Pro | 2026-07-16 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 265 | 0 | [updated quantized model](https://huggingface.co/amd/DeepSeek-V4-Pro-NVFP4/discussions/2) | `huidongji` | DeepSeek-V4-Pro-NVFP4 | 2026-07-27 | closed | pull request | unattributed | en | Y |  | 1 | 0 |
| 266 | 0 | [verified model upload](https://huggingface.co/amd/DeepSeek-V4-Pro-NVFP4/discussions/3) | `huidongji` | DeepSeek-V4-Pro-NVFP4 | 2026-07-31 | merged | pull request | unattributed | en | Y |  | 1 | 0 |
| 267 | 0 | [Tested the model on coding with OpenCode and agentic](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/10) | `curiousily` | DeepSeek-V4-Pro-0813 | 2026-08-13 | open | usage question | unattributed | en |  |  | 1 | 54 |
| 268 | 0 | [all gone](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/3) | `kuangfan955` | DeepSeek-V4-Pro-0813 | 2026-08-13 | open | other/comment | unattributed | en |  |  | 1 | 1 |
| 269 | 0 | [合影～](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/2) | `solitudeLin` | DeepSeek-V4-Pro-0813 | 2026-08-13 | open | other/comment | unattributed | zh |  |  | 1 | 3 |
| 270 | 0 | [FINALLY!](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/1) | `EnderOLED` | DeepSeek-V4-Pro-0813 | 2026-08-13 | open | other/comment | unattributed | en |  |  | 1 | 24 |
| 271 | 0 | [合影！](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/17) | `YangLouis841` | DeepSeek-V4-Pro-0813 | 2026-08-14 | open | other/comment | unattributed | zh |  |  | 1 | 2 |
| 272 | 0 | [贺电贺电](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/15) | `botsfs` | DeepSeek-V4-Pro-0813 | 2026-08-14 | open | other/comment | unattributed | zh |  |  | 1 | 4 |
| 273 | 0 | [DeepSeek Harness with V4 Pro](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/14) | `KakumuraArimura` | DeepSeek-V4-Pro-0813 | 2026-08-14 | open | other/comment | unattributed | en |  |  | 1 | 443 |
| 274 | 0 | [能不能理性一点](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/13) | `Louiva` | DeepSeek-V4-Pro-0813 | 2026-08-14 | open | other/comment | unattributed | zh |  |  | 1 | 62 |
| 275 | 0 | [Thank you!](https://huggingface.co/6block/DeepSeek-V4-Pro-0813-GGUF/discussions/1) | `MB7977` | DeepSeek-V4-Pro-0813-G | 2026-08-17 | open | other/comment | unattributed | en |  |  | 1 | 112 |
| 276 | 0 | [Add Terminal-Bench evaluation results](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/19) | `SaylorTwift` | DeepSeek-V4-Pro-0813 | 2026-08-21 | open | pull request | unattributed | en | Y |  | 1 | 0 |
| 277 | 0 | [梁圣,图像识别什么时候开源?](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/18) | `jiecong` | DeepSeek-V4-Pro-0813 | 2026-08-21 | open | usage question | unattributed | en |  |  | 1 | 292 |
| 278 | 0 | [WOAH- this quant work is amazing! 🔥](https://huggingface.co/jarrelscy/DeepSeek-V4-Pro-0813-NVFP4-AQLM-hybrid/discussions/1) | `el4` | DeepSeek-V4-Pro-0813-N | 2026-08-22 | open | other/comment | unattributed | en |  |  | 1 | 26 |
| 279 | 0 | [Create README.md](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/20) | `AR87` | DeepSeek-V4-Pro-Base | 2026-08-25 | closed | pull request | unattributed | en | Y |  | 1 | 0 |
| 280 | 0 | [quark_updated](https://huggingface.co/amd/DeepSeek-V4-Pro-NVFP4/discussions/4) | `huidongji` | DeepSeek-V4-Pro-NVFP4 | 2026-08-25 | merged | pull request | unattributed | en | Y |  | 1 | 0 |
| 281 | 0 | [Add Toolathlon-Verified evaluation result](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/21) | `SaylorTwift` | DeepSeek-V4-Pro-0813 | 2026-09-01 | open | pull request | unattributed | en | Y |  | 1 | 179 |

## Papers

32 papers name DeepSeek V4 in title or abstract. `A` = artifact kinds found in **title + abstract only** — full text lives on arXiv, not here, so these are not comparable to discussion artifact counts and are shown for ordering, not as evidence weight.

| # | A | Title | Paper | Published | Upvotes | Comments | Authors | Names V4 Pro |
| ---: | ---: | --- | --- | --- | ---: | ---: | ---: | :-: |
| 1 | 2 | [StateM: Reaching 95.3% Raw Accuracy, or a \$15 Frontier Run, o](https://huggingface.co/papers/2608.15089) | `2608.15089` | 2026-08-14 | 445 | 2 | 4 |  |
| 2 | 3 | [Recursive Synthesis for Long-Horizon Terminal Tasks](https://huggingface.co/papers/2608.05466) | `2608.05466` | 2026-08-06 | 252 | 2 | 11 | Y |
| 3 | 1 | [JIT-Agent: Scaling Harness Intelligence via Just-in-Time Harne](https://huggingface.co/papers/2608.25593) | `2608.25593` | 2026-08-25 | 115 | 2 | 16 |  |
| 4 | 2 | [Scaling the Horizon, Not the Parameters: Reaching Trillion-Par](https://huggingface.co/papers/2606.30616) | `2606.30616` | 2026-06-28 | 105 | 4 | 50 | Y |
| 5 | 2 | [SLAI T-Rex: Full-Parameter Post-training of the DeepSeek-V4 Fa](https://huggingface.co/papers/2607.20145) | `2607.20145` | 2026-07-21 | 75 | 2 | 65 |  |
| 6 | 2 | [FlashMemory-DeepSeek-V4: Lightning Index Ultra-Long Context vi](https://huggingface.co/papers/2606.09079) | `2606.09079` | 2026-06-07 | 68 | 5 | 13 |  |
| 7 | 2 | [K-BrowseComp: A Web Browsing Agent Benchmark Grounded in Korea](https://huggingface.co/papers/2606.02404) | `2606.02404` | 2026-05-31 | 60 | 1 | 15 | Y |
| 8 | 1 | [DSpark: Confidence-Scheduled Speculative Decoding with Semi-Au](https://huggingface.co/papers/2607.05147) | `2607.05147` | 2026-07-05 | 48 | 2 | 33 |  |
| 9 | 1 | [DeepSeek-V4: Towards Highly Efficient Million-Token Context In](https://huggingface.co/papers/2606.19348) | `2606.19348` | 2026-04-25 | 42 | 5 | 319 | Y |
| 10 | 1 | [AutoTrainess: Teaching Language Models to Improve Language Mod](https://huggingface.co/papers/2606.31551) | `2606.31551` | 2026-06-29 | 24 | 3 | 6 |  |
| 11 | 1 | [Bayesian-Agent: Posterior-Guided Skill Evolution for LLM Agent](https://huggingface.co/papers/2606.08348) | `2606.08348` | 2026-06-05 | 16 | 2 | 10 |  |
| 12 | 1 | [Learning to Evaluate Before Improving: Automatic Rubric Induct](https://huggingface.co/papers/2608.31076) | `2608.31076` | 2026-08-30 | 15 | 2 | 9 |  |
| 13 | 1 | [Hierarchical Self-Improvement: A Framework for Task-Specific E](https://huggingface.co/papers/2608.08466) | `2608.08466` | 2026-08-08 | 13 | 5 | 1 |  |
| 14 | 2 | [TREK: Distill to Explore, Reinforce to Refine](https://huggingface.co/papers/2607.05339) | `2607.05339` | 2026-07-05 | 9 | 2 | 13 | Y |
| 15 | 2 | [AgentForesight: Online Auditing for Early Failure Prediction i](https://huggingface.co/papers/2605.08715) | `2605.08715` | 2026-05-08 | 8 | 1 | 5 | Y |
| 16 | 1 | [Persistent Recursive Worlds Enable Autonomous Software Evoluti](https://huggingface.co/papers/2608.10450) | `2608.10450` | 2026-08-11 | 6 | 2 | 4 |  |
| 17 | 2 | [Hy-MT2: A Family of Fast, Efficient and Powerful Multilingual ](https://huggingface.co/papers/2605.22064) | `2605.22064` | 2026-05-20 | 5 | 0 | 53 | Y |
| 18 | 2 | [Solar Open 2 Technical Report](https://huggingface.co/papers/2607.20062) | `2607.20062` | 2026-07-23 | 5 | 0 | 53 | Y |
| 19 | 2 | [FlashBoot: Sub-Second Weight Loading for Large Models at Rack ](https://huggingface.co/papers/2608.08482) | `2608.08482` | 2026-08-08 | 3 | 0 | 6 | Y |
| 20 | 1 | [Harness-of-Harness: Multi-Day Autonomous Software Development ](https://huggingface.co/papers/2609.01481) | `2609.01481` | 2026-08-31 | 3 | 0 | 9 | Y |
| 21 | 0 | [GRASP: Gated Regression-Aware Skill Proposer for Self-Improvin](https://huggingface.co/papers/2605.29668) | `2605.29668` | 2026-05-27 | 1 | 0 | 7 |  |
| 22 | 1 | [Fisher-R1: Training LLM Agents for Reliable Hypothesis Testing](https://huggingface.co/papers/2608.07437) | `2608.07437` | 2026-08-06 | 1 | 0 | 4 | Y |
| 23 | 1 | [DARWIN: Evolving Jailbreak Adversary and Guardrail for LLM Saf](https://huggingface.co/papers/2607.19829) | `2607.19829` | 2026-07-21 | 1 | 0 | 8 | Y |
| 24 | 2 | [EvoClawBench: Can Agents Learn Reusable Skills from Their Own ](https://huggingface.co/papers/2607.09711) | `2607.09711` | 2026-06-22 | 1 | 0 | 8 | Y |
| 25 | 0 | [τ-Rec: A Verifiable Benchmark for Agentic Recommender Systems](https://huggingface.co/papers/2606.10156) | `2606.10156` | 2026-06-07 | 1 | 2 | 2 |  |
| 26 | 1 | [Do LLMs Hold Their Values? MANTA: A Multi-Turn Adversarial Ben](https://huggingface.co/papers/2605.16301) | `2605.16301` | 2026-06-02 | 1 | 0 | 8 |  |
| 27 | 1 | [VisInject: Disruption != Injection -- A Dual-Dimension Evaluat](https://huggingface.co/papers/2605.01449) | `2605.01449` | 2026-05-01 | 0 | 0 | 2 | Y |
| 28 | 3 | [SETA: Scaling Environments for Terminal Agents](https://huggingface.co/papers/2607.10891) | `2607.10891` | 2026-07-11 | 0 | 0 | 22 |  |
| 29 | 3 | [Tied Trit-Planes: Constraining PTQTP to a Uniform Nine-Level Q](https://huggingface.co/papers/2608.08910) | `2608.08910` | 2026-08-08 | 0 | 0 | 1 |  |
| 30 | 2 | [Coupling Planning with Episodic Memory in LLM Agents for Softw](https://huggingface.co/papers/2608.06811) | `2608.06811` | 2026-08-06 | 0 | 0 | 3 |  |
| 31 | 0 | [XREPOTEST: Benchmarking Multilingual Repository-Level Unit Tes](https://huggingface.co/papers/2608.25939) | `2608.25939` | 2026-08-25 | 0 | 0 | 6 | Y |
| 32 | 1 | [Distilling Answer Set Programming Theories from Large Language](https://huggingface.co/papers/2607.28086) | `2607.28086` | 2026-07-29 | 0 | 0 | 3 | Y |

Those 32 papers carry 1323 upvotes and **44 comments between them — none of which can be read**, because the comment endpoints 404. The community signal that distinguishes HF Papers from arXiv is countable but not readable.

---

## Full text — the 22 discussions carrying ≥2 artifacts

Verbatim comment bodies, indented four spaces so their code fences cannot break this document.

### 1. 这是偷摸改啥文件了，哈哈哈

- **Repo:** `deepseek-ai/DeepSeek-V4-Pro-0813` · discussion #5
- **Author:** `beijizhidayww`
- **Date:** 2026-08-13 · status: open · 4 comments · language: zh
- **URL:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/5
- **Type:** other/comment · **Provenance:** unattributed
- **Artifacts: 3** — `code_fence`×4, `conditioned_comparison`×2, `version_string`×22

    这是偷摸改啥文件了，哈哈哈
    
    config.json 最开始是 flash 的
    
    
    Haha
    
    是，**这个传言基本属实，而且比“config 写错一个参数”严重一些。**
    
    我把你发的 Hugging Face 提交历史往前追了。最关键的证据有三层。
    
    **第一层：最初的 Pro-0813 配置确实传错了。** 初版 `config.json` 是：
    
    | 参数                      | Pro-0813 初版 |      修正后 |
    | ----------------------- | ----------: | -------: |
    | `hidden_size`           |        4096 | **7168** |
    | `num_hidden_layers`     |          43 |   **61** |
    | `num_attention_heads`   |          64 |  **128** |
    | `n_routed_experts`      |         256 |  **384** |
    | `moe_intermediate_size` |        2048 | **3072** |
    | `index_topk`            |         512 | **1024** |
    | `q_lora_rank`           |        1024 | **1536** |
    | `o_groups`              |           8 |   **16** |
    | `routed_scaling_factor` |         1.5 |  **2.5** |
    
    此外 DSpark 的 target layer 也从 `[40,41,42]` 改成 `[58,59,60]`，Markov rank 从 256 改成 512。也就是说，**这不是一个无关紧要的小 typo，而是一整套模型结构规格写错。** ([Hugging Face][1])
    
    更有意思的是：我又去查了官方 **DeepSeek-V4-Flash-0731**。它现在的配置恰恰就是：
    
    `4096 / 43层 / 64 heads / 256 experts / topk 512 / q_lora 1024 / route scale 1.5 / DSpark layers 40-42`
    
    也就是和 **Pro-0813 的错误初版配置高度一致，基本就是 Flash 那套配置。** ([Hugging Face][2])
    
    所以这里很可能发生的是：
    
    > **DeepSeek 发布 Pro-0813 时，误把 Flash 的 config/inference config 一起塞进了 Pro 仓库。**
    
    这是根据两个官方仓库内容做出的推断，但证据非常强。
    
    ---
    
    更重要的是第二层：**不只是 config 改了，权重文件随后也被重新提交了。**
    
    `09d796d` 修完 config 之后，紧接着出现：
    
    `812a554 — Add files using upload-large-folder tool`
    
    这个提交直接修改了 **50 个文件，其中 48 个是 `.safetensors` 权重 shard**。从 `model-00002` 一直到很多后面的 shard 都发生了 SHA256 变化。([Hugging Face][3])
    
    比如第 8 个 shard：
    
    旧版：
    
    ```text
    SHA256:
    b9132567196fed17914a3285394ba98ef8bbf4d163983844a481518e1ce584ee
    
    size:
    13,903,717,360
    ```
    
    新版：
    
    ```text
    SHA256:
    b2e31dda0b244aca5ea1afb3e88541800dfeb3db6f135c1dc4fe9f75a3cde5a1
    
    size:
    13,903,802,792
    ```
    
    也就是说，它不是 Git metadata 变了，而是**实际 safetensors 内容发生变化**。([Hugging Face][3])
    
    但这里有个很重要的细节：这个 shard 只增加了大约 **85 KB**，而整个 shard 大约 **13.9 GB**。
    
    所以我目前**不赞成把它描述成“DeepSeek 一开始把整个错误模型/Flash 权重传上去了”**。
    
    如果真把 Flash checkpoint 当 Pro 上传了，体积根本对不上：Flash 官方 checkpoint 的 shard 大约只有 3.x GB、共 46 个，而这个 Pro-0813 从一开始就是 66 个 shard、单 shard 约 13.9 GB。([Hugging Face][4])
    
    因此比较准确的说法是：
    
    > **DeepSeek 最初确实把 Pro-0813 发布错了：首先明显误用了 Flash 的模型配置；随后又重新上传/修正了大量 Pro 权重分片。**
    >
    > **但现有证据不能证明最初上传的是“完全错误的 checkpoint”。更像是 Pro 主体权重本来就在，只是配置错了，同时权重中还有一小部分 tensor/量化信息/附加参数需要重新导出或补齐。**
    
    还有第三个旁证：HF 社区有人当时直接指出 `config.json` 与 `DeepSeek-V4-Pro-DSpark` 不一致，DeepSeek 官方账号 `msr2000` 随后回复 **“已处理”** 并关闭了讨论。([Hugging Face][5])
    
    ### 这件事其实挺有意思
    
    初版：
    
    **Flash 架构：4096 × 43 层 × 256 experts**
    
    修正后：
    
    **Pro 架构：7168 × 61 层 × 384 experts**
    
    这也等于意外给我们确认了 **V4 Pro 和 V4 Flash 的真实规模差异**。并且不是简单的“Pro 多几个专家”，而是**宽度、深度、attention、MoE、稀疏索引甚至 DSpark 参数都整体放大了**。
    
    所以你之前如果看到有人在 **0813 权重刚放出来的头几个小时**测试，然后说“跑不起来”“维度不对”“性能很怪”“和 DSpark 对不上”，**那批测试结果最好全部作废**。应该至少以 `09d796d` 之后的 config，并且更稳妥地以 `812a554` / `a2f2780` 之后重新上传完的权重为准。([Hugging Face][6])
    
    如果你愿意，我还可以继续往下扒 **`812a554` 和 `a2f2780` 到底修改了哪些 tensor**。这个其实更有价值：可以反推出 DeepSeek 当时**到底漏传/传错了哪一部分参数**，而不仅仅知道“权重文件变了”。
    
    [1]: https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/commit/09d796d25191dd7579987f5c76c1bae6e86dbedc "Update config.json · deepseek-ai/DeepSeek-V4-Pro-0813 at 09d796d"
    [2]: https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blame/main/config.json "config.json · deepseek-ai/DeepSeek-V4-Flash-0731 at main"
    [3]: https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/commit/812a5543bb1ba12deb231e2ae8a1957a5f1e5fb8 "Add files using upload-large-folder tool · deepseek-ai/DeepSeek-V4-Pro-0813 at 812a554"
    [4]: https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/tree/main?utm_source=chatgpt.com "deepseek-ai/DeepSeek-V4-Flash at main"
    [5]: https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/4 "deepseek-ai/DeepSeek-V4-Pro-0813 · config.json 和deepseek-ai/DeepSeek-V4-Pro-DSpark配置似乎有出入"
    [6]: https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/commits/main?utm_source=chatgpt.com "Commits · deepseek-ai/DeepSeek-V4-Pro-0813"

---

### 2. Architectural Issue

- **Repo:** `deepseek-ai/DeepSeek-V4-Pro-DSpark` · discussion #3
- **Author:** `cloudyu`
- **Date:** 2026-06-28 · status: open · 3 comments · language: en
- **URL:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-DSpark/discussions/3
- **Type:** community bug report · **Provenance:** unattributed
- **Artifacts: 3** — `bench_number`×9, `conditioned_comparison`×7, `version_string`×3

    Thanks to DeepSeek for releasing this model. 
    I believe the design of top k=6 is very lacking in rigor and elegance.
    Changing top k to 4 does not affect the inference performance.
    Below is my preliminary test.
    https://huggingface.co/autotrust/DeepSeek-V4-Flash-DSpark-4E
    
    What a crock of nonsense. 
    
    > What a crock of nonsense.
    
    
    
    
    ## Why top-k = 4 is reasonable
    
    DeepSeek-V4-Pro routes each token to **6 of 384** fine-grained experts (plus 1 shared expert),
    scaled by `routed_scaling_factor = 2.5` with `noaux_tc` biased top-k selection and
    `sqrtsoftplus` scoring. Two properties make the top-6 → top-4 reduction low-risk:
    
    1. **Router mass is front-loaded.** With normalized top-k probabilities (`norm_topk_prob: true`),
       the highest-scoring experts dominate the mixture; the 5th and 6th experts contribute the
       smallest, most redundant residual. Dropping them removes the least informative routing mass.
    2. **Fine-grained MoE is over-provisioned for many tokens.** With 384 experts and a shared
       expert always active, most tokens are well covered by their top few specialists; the tail
       experts largely refine rather than redirect.
    
    The result is a **compute/quality knob** that is nearly free at k=4 and only degrades sharply
    below it — which is exactly what the measurements show.
    ## Evaluation results
    
    Independently re-evaluated with **vLLM 0.24.0** (offline `LLM`), tensor-parallel across 8×B300,
    `kv_cache_dtype=fp8`, **chat / non-think mode**, **greedy decoding** (`temperature=0`), Pass@1,
    `max_tokens=8192`. Code is executed against the official unit tests (HumanEval = 164 problems,
    MBPP = full test split, 500 problems). The **only** variable across rows is `num_experts_per_tok`.
    
    | `num_experts_per_tok` | HumanEval Pass@1 | MBPP Pass@1 | Expert matmuls / token |
    | :---: | :---: | :---: | :---: |
    | **6** (original) | 96.34 % (158/164) | 83.8 % (419/500) | 1.00× |
    | **4** (this model) | **96.34 % (158/164)** | **82.8 % (414/500)** | **0.67×** |
    | 2 (for reference) | 87.80 % (144/164) | 75.6 % (378/500) | 0.33× |
    
    **Takeaways**
    - **6 → 4 is nearly lossless:** HumanEval is *identical* (158/164) and MBPP drops only **1.0 pt**,
      while expert computation and expert-weight memory traffic fall by **one third**.
    - **4 → 2 is not free:** HumanEval −8.5 pt and MBPP −8.2 pt, and generations become longer / less
      confident. **top-k=4 is the sweet spot**; going below it is not recommended.
    
    *Numbers are self-hosted Pass@1 in non-think mode and are not directly comparable to the official
    Think-High/Think-Max scores on the upstream card.*
    
    

---

### 3. Q4/Q8 hybrid GGUF shards

- **Repo:** `unsloth/DeepSeek-V4-Pro-0813-GGUF` · discussion #5
- **Author:** `Bacruru`
- **Date:** 2026-08-28 · status: open · 2 comments · language: en
- **URL:** https://huggingface.co/unsloth/DeepSeek-V4-Pro-0813-GGUF/discussions/5
- **Type:** community bug report · **Provenance:** unattributed
- **Artifacts: 3** — `code_fence`×4, `conditioned_comparison`×45, `error_output`×4

    Q4 and Q8 gguf shards have a massive amount of duplicating tensors. So if user want to download both of them, they have 800GB space taken by duplicating data. I wrote a scrypt. which repacks ggufs and pushes dublicating tensors inside upper shards. With it user can store two GGUFs with attention head (20 GB for Q4_K_XL and 47 GB for Q8_K_XL) and one copy of expert shards (800 GB). Use symlinks to make valid file structure for llama.cpp.
    All output files are validated for launch and metadata similarity. All of these scripts requires gguf python package to be installed.
    
    Script source:
    dedup_gguf.py
    ``` python
    #!/usr/bin/env python3
    """
    Reproducible deduplication of sharded GGUF MoE models that share identical expert
    tensors (e.g. DeepSeek V4 Pro Q4_K_XL vs Q8_K_XL, where the MXFP4 expert layers
    are byte-identical and only a subset of non-expert tensors differ).
    
    Given a directory containing several sharded GGUF quantizations of the same base
    model, this script:
    
      1. Discovers all models (one per distinct "-00001-of-000NN.gguf" base name).
      2. Classifies every tensor across the models:
           * metadata          -> kept per model, copied byte-for-byte
           * "differing"       -> name/dims/dtype/content differ between models
           * "identical"       -> byte-identical across ALL models (non-expert)
           * "expert"          -> byte-identical across ALL models, matched by
                                  --expert-suffix (default "_exps.")
      3. Writes a deduplicated split layout:
    
             <model>-00001-of-000NN.gguf    metadata + differing tensors
             common-00002-of-000NN.gguf     identical (non-expert) tensors, one file
             common-00003..-of-000NN.gguf   expert tensors, ~--shard-size GB each
    
      4. Creates symlink directories (one per model) so standard llama.cpp tools
         (llama-server / llama-cli) load via the conventional naming scheme; the
         same files can also be loaded without symlinks via
         llama_model_load_from_splits().
      5. Verifies the output: tensor count, names, dims, dtype, size and (optionally)
         content hashes match the source.
    
    Tensor weight data is copied byte-for-byte; no weight is modified.  The only
    metadata field that changes is the split bookkeeping (split.no / split.count /
    split.tensors.count), which is required for the new shard layout.
    
    Requires: `pip install gguf` (and numpy).
    """
    
    from __future__ import annotations
    
    import argparse
    import hashlib
    import json
    import os
    import struct
    import sys
    from collections import defaultdict
    
    import gguf
    
    MAGIC = 0x46554747
    VERSION = 3
    ALIGN = 32
    
    # GGUF value types (must match the gguf spec)
    VT_UINT8, VT_INT8, VT_UINT16, VT_INT16, VT_UINT32, VT_INT32 = 0, 1, 2, 3, 4, 5
    VT_FLOAT32, VT_BOOL, VT_STRING, VT_ARRAY = 6, 7, 8, 9
    VT_UINT64, VT_INT64, VT_FLOAT64 = 10, 11, 12
    
    # GGUF metadata keys that are not real KV pairs (they live in the header)
    _HEADER_KEYS = {"GGUF.version", "GGUF.tensor_count", "GGUF.kv_count"}
    
    
    def ggml_pad(x: int) -> int:
        return (x + ALIGN - 1) // ALIGN * ALIGN
    
    
    def pack_string(b) -> bytes:
        if isinstance(b, str):
            b = b.encode("utf-8")
        return struct.pack("<Q", len(b)) + b
    
    
    def pack_u16(v: int) -> bytes:
        return struct.pack("<H", v)
    
    
    def pack_i32(v: int) -> bytes:
        return struct.pack("<i", v)
    
    
    # --------------------------------------------------------------------------- #
    # Model discovery and parsing
    # --------------------------------------------------------------------------- #
    
    def discover_models(src_dir: str) -> list[str]:
        """Return the sorted list of distinct model base names (without shard suffix)."""
        bases = set()
        for fn in os.listdir(src_dir):
            if not fn.endswith(".gguf"):
                continue
            # strip "-NNNNN-of-NNNNN.gguf" -> base name
            # e.g. "foo-Q4_K_XL-00001-of-00020.gguf" -> "foo-Q4_K_XL"
            stem = fn[:-len(".gguf")]
            if "-of-" not in stem:
                continue
            head, _, _ = stem.rpartition("-of-")
            if "-" not in head:
                continue
            prefix, _, _ = head.rpartition("-")
            bases.add(prefix)
        return sorted(bases)
    
    
    def _read_fields_kv(reader: gguf.GGUFReader) -> bytes:
        """Reconstruct the exact serialized KV section (header excluded)."""
        out = bytearray()
        for key, field in reader.fields.items():
            if key in _HEADER_KEYS:
                continue
            out += b"".join(p.tobytes() for p in field.parts)
        return bytes(out)
    
    
    def load_model(src_dir: str, base: str) -> dict:
        """Parse one sharded model into a metadata blob + tensor table."""
        shards = sorted(
            fn for fn in os.listdir(src_dir)
            if fn.startswith(base + "-") and fn.endswith(".gguf")
        )
    
        # The main (metadata) shard is the one with split.no == 0, normally 00001.
        main = None
        metadata_kv = None
        kv_count = 0
        tensors: dict[str, dict] = {}
    
        for fn in shards:
            path = os.path.join(src_dir, fn)
            r = gguf.GGUFReader(path)
            split_no = None
            if "split.no" in r.fields:
                split_no = r.fields["split.no"].contents()
            if split_no == 0 or (split_no is None and len(r.fields) > 4):
                # this shard carries the full metadata
                main = fn
                metadata_kv = _read_fields_kv(r)
                kv_count = len(r.fields) - len(_HEADER_KEYS)
            for t in r.tensors:
                tensors[t.name] = {
                    "name": t.name,
                    "dims": [int(x) for x in t.shape],  # raw stored order (as-is)
                    "dtype": int(t.tensor_type),
                    "nbytes": int(t.n_bytes),
                    "shard": fn,
                    "offset": int(t.data_offset),
                }
    
        if metadata_kv is None:
            raise RuntimeError(f"no metadata shard found for model {base!r}")
    
        return {
            "base": base,
            "metadata_kv": metadata_kv,
            "kv_count": kv_count,
            "tensors": tensors,
            "main_shard": main,
            "shards": shards,
        }
    
    
    # --------------------------------------------------------------------------- #
    # Hashing
    # --------------------------------------------------------------------------- #
    
    def hash_range(path: str, offset: int, size: int, chunk: int = 128 * 1024 * 1024) -> str:
        h = hashlib.blake2b(digest_size=16)
        with open(path, "rb") as f:
            f.seek(offset)
            remaining = size
            while remaining > 0:
                data = f.read(min(chunk, remaining))
                if not data:
                    break
                h.update(data)
                remaining -= len(data)
        return h.hexdigest()
    
    
    # --------------------------------------------------------------------------- #
    # Classification
    # --------------------------------------------------------------------------- #
    
    def classify(models: list[dict], expert_suffix: str) -> tuple[set, set, set]:
        """Return (differing, identical_small, experts) tensor-name sets."""
        names = sorted(models[0]["tensors"].keys())
    
        # sanity: all models have the same tensor names
        for m in models[1:]:
            if set(m["tensors"].keys()) != set(names):
                raise RuntimeError("models have different tensor name sets; cannot deduplicate")
    
        differing = set()
        identical = set()
    
        for name in names:
            ref = models[0]["tensors"][name]
            same_meta = True
            for m in models[1:]:
                t = m["tensors"][name]
                if t["dtype"] != ref["dtype"] or t["dims"] != ref["dims"]:
                    same_meta = False
                    break
            if not same_meta:
                differing.add(name)
                continue
    
            # same dtype/dims -> compare content hashes
            hashes = set()
            for m in models:
                t = m["tensors"][name]
                hashes.add(hash_range(os.path.join(m["base_dir"], t["shard"]), t["offset"], t["nbytes"]))
            if len(hashes) == 1:
                identical.add(name)
            else:
                differing.add(name)
    
        experts = {n for n in identical if expert_suffix in n}
        identical_small = identical - experts
    
        # The whole point: experts MUST be identical.  If any expert ended up in
        # 'differing', fail loudly rather than silently producing a broken model.
        for m in models:
            for n in m["tensors"]:
                if expert_suffix in n and n in differing:
                    raise RuntimeError(
                        f"expert tensor {n!r} differs between models — aborting "
                        f"(these are expected to be byte-identical)"
                    )
    
        return differing, identical_small, experts
    
    
    # --------------------------------------------------------------------------- #
    # Writing
    # --------------------------------------------------------------------------- #
    
    def serialize_tensor_info(name: str, dims, dtype: int, offset: int) -> bytes:
        out = bytearray()
        out += pack_string(name)
        out += struct.pack("<I", len(dims))
        for d in dims:  # NOTE: dims are already in the GGUF stored order (as-is)
            out += struct.pack("<Q", d)
        out += struct.pack("<I", dtype)
        out += struct.pack("<Q", offset)
        return bytes(out)
    
    
    def patch_kv(kv: bytes, key: str, vtype: int, value: bytes) -> bytes:
        """Patch a single KV entry's value in serialized metadata (in place)."""
        needle = pack_string(key) + struct.pack("<I", vtype)
        idx = kv.find(needle)
        if idx < 0:
            raise RuntimeError(f"metadata key {key!r} not found")
        pos = idx + len(needle)
        return kv[:pos] + value + kv[pos + len(value):]
    
    
    def write_split_file(path: str, split_no: int, split_count: int, total_tensors: int,
                         tensor_list: list[dict], src_dir: str, metadata_kv: bytes | None,
                         kv_count: int = 0):
        """Write one GGUF split file.
    
        tensor_list entries carry name/dims/dtype/nbytes/shard/offset (source).
        If metadata_kv is not None this is the main (metadata) shard (kv_count must
        then be given); otherwise a minimal split shard (only split.* KV) is written.
        """
        n_tensors = len(tensor_list)
        with open(path, "wb") as f:
            # header: magic, version, tensor_count, kv_count
            f.write(struct.pack("<I", MAGIC))
            f.write(struct.pack("<I", VERSION))
            f.write(struct.pack("<Q", n_tensors))
    
            if metadata_kv is not None:
                kv = patch_kv(metadata_kv, "split.count", VT_UINT16, pack_u16(split_count))
                kv = patch_kv(kv, "split.tensors.count", VT_INT32, pack_i32(total_tensors))
                f.write(struct.pack("<Q", kv_count))
                f.write(kv)
            else:
                kv = (
                    pack_string("split.no") + struct.pack("<I", VT_UINT16) + pack_u16(split_no)
                    + pack_string("split.tensors.count") + struct.pack("<I", VT_INT32) + pack_i32(total_tensors)
                    + pack_string("split.count") + struct.pack("<I", VT_UINT16) + pack_u16(split_count)
                )
                f.write(struct.pack("<Q", 3))
                f.write(kv)
    
            # tensor info
            offset = 0
            for t in tensor_list:
                f.write(serialize_tensor_info(t["name"], t["dims"], t["dtype"], offset))
                offset += ggml_pad(t["nbytes"])
    
            # pad to alignment
            pad = ggml_pad(f.tell()) - f.tell()
            if pad:
                f.write(b"\x00" * pad)
    
            # tensor data (byte-for-byte copy)
            for t in tensor_list:
                _copy_range(os.path.join(src_dir, t["shard"]), t["offset"], t["nbytes"], f)
                pad2 = ggml_pad(f.tell()) - f.tell()
                if pad2:
                    f.write(b"\x00" * pad2)
    
    
    def _copy_range(src_path: str, offset: int, size: int, out_f) -> None:
        with open(src_path, "rb") as f:
            f.seek(offset)
            remaining = size
            chunk = 64 * 1024 * 1024
            while remaining > 0:
                data = f.read(min(chunk, remaining))
                if not data:
                    break
                out_f.write(data)
                remaining -= len(data)
    
    
    # --------------------------------------------------------------------------- #
    # Verification
    # --------------------------------------------------------------------------- #
    
    def verify(out_dir: str, models: list[dict], names: list[str]) -> int:
        """Read every output file back and check names/dims/dtype/nbytes vs source.
    
        dims and nbytes are invariant across models; dtype is checked against the set
        of valid per-model dtypes (the "differing" tensors legitimately differ).
        """
        seen: dict[str, tuple[str, list, int, int]] = {}
        problems = 0
    
        for fn in sorted(os.listdir(out_dir)):
            if not fn.endswith(".gguf"):
                continue
            r = gguf.GGUFReader(os.path.join(out_dir, fn))
            for t in r.tensors:
                seen[t.name] = (fn, [int(x) for x in t.shape], int(t.tensor_type), int(t.n_bytes))
    
        if len(seen) != len(names):
            print(f"  [FAIL] tensor count {len(seen)} != {len(names)}")
            problems += 1
        missing = set(names) - set(seen)
        extra = set(seen) - set(names)
        if missing:
            print(f"  [FAIL] missing tensors: {sorted(missing)[:5]} ...")
            problems += 1
        if extra:
            print(f"  [FAIL] extra tensors: {sorted(extra)[:5]} ...")
            problems += 1
    
        # dims are invariant across models; dtype and nbytes may legitimately differ
        # for the "differing" tensors (e.g. Q8_0 vs BF16), so accept any value that
        # one of the source models has for that tensor.
        ref_dims = {n: models[0]["tensors"][n]["dims"] for n in names}
        valid_dtypes = {n: {m["tensors"][n]["dtype"] for m in models} for n in names}
        valid_nbytes = {n: {m["tensors"][n]["nbytes"] for m in models} for n in names}
    
        for n in names:
            if n not in seen:
                continue
            fn, dims, dtype, nbytes = seen[n]
            if dims != ref_dims[n]:
                print(f"  [FAIL] {n}: dims mismatch ({dims} vs {ref_dims[n]})")
                problems += 1
            if nbytes not in valid_nbytes[n]:
                print(f"  [FAIL] {n}: nbytes {nbytes} not in {sorted(valid_nbytes[n])}")
                problems += 1
            if dtype not in valid_dtypes[n]:
                print(f"  [FAIL] {n}: unexpected dtype {dtype}")
                problems += 1
    
        return problems
    
    
    # --------------------------------------------------------------------------- #
    # Main
    # --------------------------------------------------------------------------- #
    
    def main() -> int:
        # keep progress visible even when output is redirected to a file
        try:
            sys.stdout.reconfigure(line_buffering=True)
        except Exception:
            pass
    
        ap = argparse.ArgumentParser(description="Deduplicate GGUF MoE models sharing identical experts")
        ap.add_argument("src_dir", help="directory containing the source sharded GGUF models")
        ap.add_argument("out_dir", help="directory to write the deduplicated splits to")
        ap.add_argument("--expert-suffix", default="_exps.", help="name suffix identifying expert tensors")
        ap.add_argument("--shard-size", type=float, default=50.0, help="target expert shard size in GB")
        ap.add_argument("--symlinks", action="store_true", help="also create per-model symlink dirs for standard tools")
        ap.add_argument("--verify-hash", action="store_true", help="re-hash output tensor data (slow)")
        args = ap.parse_args()
    
        src_dir = os.path.abspath(args.src_dir)
        out_dir = os.path.abspath(args.out_dir)
    
        bases = discover_models(src_dir)
        if len(bases) < 2:
            print(f"error: found {len(bases)} model(s) in {src_dir}; need at least 2 to deduplicate")
            return 1
        print(f"Found {len(bases)} models: {bases}")
    
        models = []
        for base in bases:
            m = load_model(src_dir, base)
            m["base_dir"] = src_dir
            print(f"  {base}: {len(m['tensors'])} tensors, {len(m['shards'])} shards")
            models.append(m)
    
        names = sorted(models[0]["tensors"].keys())
        for m in models[1:]:
            if len(m["tensors"]) != len(names):
                print("error: models have different tensor counts")
                return 1
    
        print("Classifying tensors (hashing where needed)...")
        differing, identical_small, experts = classify(models, args.expert_suffix)
        print(f"  differing: {len(differing)}")
        print(f"  identical (non-expert): {len(identical_small)}")
        print(f"  experts: {len(experts)}")
    
        # pack experts into ~shard_size GB shards
        expert_shards: list[list[str]] = []
        cur: list[str] = []
        cur_bytes = 0
        target = int(args.shard_size * 1000**3)
        for n in sorted(experts):
            sz = models[0]["tensors"][n]["nbytes"]
            if cur and cur_bytes + sz > target:
                expert_shards.append(cur)
                cur = []
                cur_bytes = 0
            cur.append(n)
            cur_bytes += sz
        if cur:
            expert_shards.append(cur)
    
        total_splits = 1 + 1 + len(expert_shards)
        total_tensors = len(names)
        print(f"Layout: {total_splits} splits (1 main + 1 identical + {len(expert_shards)} expert)")
    
        os.makedirs(out_dir, exist_ok=True)
    
        # main files (one per model) + shared files
        for m in models:
            tens = [m["tensors"][n] for n in sorted(differing)]
            out = os.path.join(out_dir, f"{m['base']}-00001-of-{total_splits:05d}.gguf")
            print(f"Writing {m['base']} main ({len(tens)} tensors)...")
            write_split_file(out, 0, total_splits, total_tensors, tens, src_dir,
                             m["metadata_kv"], m["kv_count"])
    
        # shared identical (non-expert)
        tens = [models[0]["tensors"][n] for n in sorted(identical_small)]
        out = os.path.join(out_dir, f"common-00002-of-{total_splits:05d}.gguf")
        print(f"Writing common identical ({len(tens)} tensors)...")
        write_split_file(out, 1, total_splits, total_tensors, tens, src_dir, None)
    
        # shared experts
        for i, shard in enumerate(expert_shards):
            tens = [models[0]["tensors"][n] for n in shard]
            split_no = 2 + i
            out = os.path.join(out_dir, f"common-{split_no + 1:05d}-of-{total_splits:05d}.gguf")
            print(f"Writing expert shard {i + 1}/{len(expert_shards)} ({len(shard)} tensors)...")
            write_split_file(out, split_no, total_splits, total_tensors, tens, src_dir, None)
    
        # symlinks for standard llama.cpp naming
        if args.symlinks:
            for m in models:
                d = os.path.join(out_dir, m["base"])
                os.makedirs(d, exist_ok=True)
                os.symlink(f"../{m['base']}-00001-of-{total_splits:05d}.gguf",
                           os.path.join(d, f"{m['base']}-00001-of-{total_splits:05d}.gguf"))
                for i in range(2, total_splits + 1):
                    os.symlink(f"../common-{i:05d}-of-{total_splits:05d}.gguf",
                               os.path.join(d, f"{m['base']}-{i:05d}-of-{total_splits:05d}.gguf"))
            print("Symlink dirs created.")
    
        print("Verifying output...")
        problems = verify(out_dir, models, names)
        if problems:
            print(f"VERIFICATION FAILED: {problems} problem(s)")
            return 1
        print("Verification OK: all tensors present with correct dims/dtype/size.")
        print("Done.")
        return 0
    
    
    if __name__ == "__main__":
        sys.exit(main())
     ```
    check_repack.py
    ``` python 
    import os
    import json
    import sys
    from pathlib import Path
    from gguf import GGUFReader
    
    def get_gguf_files(folder_path):
        """Собирает все .gguf файлы в папке, корректно обрабатывая симлинки."""
        folder = Path(folder_path).resolve()
        if not folder.is_dir():
            print(f"Ошибка: Путь {folder} не является директорией.")
            sys.exit(1)
        
        # Ищем файлы, разрешая симлинки
        files = []
        for f in folder.iterdir():
            resolved_f = f.resolve()
            if resolved_f.is_file() and resolved_f.suffix.lower() == '.gguf':
                files.append(resolved_f)
        return sorted(files)
    
    def build_tensor_map(files, folder_name):
        """Строит карту тензоров: имя -> {шард, форма, тип, смещение}."""
        tensor_map = {}
        print(f"[{folder_name}] Сканирование файлов...")
        
        for file_path in files:
            try:
                # Прерываем чтение сразу после заголовков (не читаем сами данные)
                reader = GGUFReader(file_path, mode="r")
                for tensor in reader.tensors:
                    name = tensor.name
                    tensor_map[name] = {
                        "file": file_path.name,
                        "shape": tensor.shape.tolist(),
                        "type": str(tensor.tensor_type),
                        # Сохраняем информацию для фазы 2
                        "full_path": str(file_path),
                        "data_offset": tensor.data_offset,
                        "data_size": tensor.n_bytes
                    }
            except Exception as e:
                print(f"Ошибка при чтении файла {file_path.name}: {e}")
        return tensor_map
    
    def compare_metadata(orig_map, repack_map):
        """Фаза 1: Сравнение состава, размерностей и типов данных."""
        errors = []
        orig_tensors = set(orig_map.keys())
        repack_tensors = set(repack_map.keys())
    
        # Проверка состава
        missing_in_repack = orig_tensors - repack_tensors
        extra_in_repack = repack_tensors - orig_tensors
    
        for t in missing_in_repack:
            errors.append(f"Ошибка метаданных: Тензор '{t}' есть в оригинале, но отсутствует в репаке.")
        for t in extra_in_repack:
            errors.append(f"Ошибка метаданных: Тензор '{t}' есть в репаке, но отсутствует в оригинале.")
    
        # Проверка характеристик общих тензоров
        common_tensors = orig_tensors & repack_tensors
        for t in common_tensors:
            o_meta = orig_map[t]
            r_meta = repack_map[t]
    
            if o_meta["shape"] != r_meta["shape"]:
                errors.append(f"Ошибка размерности '{t}': Оригинал {o_meta['shape']} != Репак {r_meta['shape']}")
            if o_meta["type"] != r_meta["type"]:
                errors.append(f"Ошибка типа данных '{t}': Оригинал {o_meta['type']} != Репак {r_meta['type']}")
    
        return errors
    
    def compare_tensor_bytes(orig_meta, repack_meta):
        """Побайтное сравнение одного тензора без загрузки всего файла."""
        chunk_size = 64 * 1024 * 1024 # Читаем чанками по 64MB для экономии RAM
        
        if orig_meta["data_size"] != repack_meta["data_size"]:
            return False
    
        with open(orig_meta["full_path"], "rb") as f_orig, open(repack_meta["full_path"], "rb") as f_repack:
            f_orig.seek(orig_meta["data_offset"])
            f_repack.seek(repack_meta["data_offset"])
            
            bytes_left = orig_meta["data_size"]
            while bytes_left > 0:
                to_read = min(chunk_size, bytes_left)
                buf1 = f_orig.read(to_read)
                buf2 = f_repack.read(to_read)
                
                if buf1 != buf2:
                    return False
                bytes_left -= to_read
                
        return True
    
    def main():
        if len(sys.argv) < 3:
            print("Использование: python check_repack.py <путь_к_оригиналу> <путь_к_репаку>")
            sys.exit(1)
    
        orig_dir = sys.argv[1]
        repack_dir = sys.argv[2]
    
        orig_files = get_gguf_files(orig_dir)
        repack_files = get_gguf_files(repack_dir)
    
        # Шаг 1: Сбор карт тензоров
        orig_map = build_tensor_map(orig_files, "Оригинал")
        repack_map = build_tensor_map(repack_files, "Репак")
    
        # Сохраняем карты в JSON (удаляя технические пути для чистоты файла)
        json_output = {
            "original": {k: {"file": v["file"], "shape": v["shape"], "type": v["type"]} for k, v in orig_map.items()},
            "repack": {k: {"file": v["file"], "shape": v["shape"], "type": v["type"]} for k, v in repack_map.items()}
        }
        with open("tensor_maps.json", "w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=4, ensure_ascii=False)
        print("-> Карта тензоров сохранена в 'tensor_maps.json'\n")
    
        # Шаг 2: Выполнение Фазы 1 (Проверка структуры)
        print("--- Фаза 1: Проверка структуры и типов метаданных ---")
        metadata_errors = compare_metadata(orig_map, repack_map)
    
        if metadata_errors:
            print(f"Обнаружено {len(metadata_errors)} ошибок в метаданных. Фаза 2 (побайтное сравнение) отменена.")
            print("\nСписок ошибок:")
            for err in metadata_errors:
                print(err)
            sys.exit(1)
        
        print("Успешно: Метаданные, типы и размерности полностью совпадают.")
    
        # Шаг 3: Выполнение Фазы 2 (Побайтное сравнение)
        print("\n--- Фаза 2: Побайтное сравнение тензоров ---")
        common_tensors = list(orig_map.keys())
        total_tensors = len(common_tensors)
        byte_errors = []
    
        for idx, tensor_name in enumerate(common_tensors, 1):
            # Вывод прогресса в одну строку
            print(f"\rПрогресс: {idx}/{total_tensors} тензоров обработано...", end="", flush=True)
            
            is_identical = compare_tensor_bytes(orig_map[tensor_name], repack_map[tensor_name])
            if not is_identical:
                byte_errors.append(f"Ошибка данных: Тензор '{tensor_name}' отличается байт-в-байт.")
    
        print() # Перенос строки после прогресс-бара
    
        # Итоги
        if byte_errors:
            print(f"\n[ВНИМАНИЕ] Обнаружены расхождения в данных ({len(byte_errors)} шт.):")
            for err in byte_errors:
                print(err)
            sys.exit(1)
        else:
            print("\n[УСПЕХ] Проверка завершена! Все тензоры идентичны байт-в-байт.")
    
    if __name__ == "__main__":
        main()
    ```
    
    Resulting weights fully tested in prod. inference results are the same with same seed.

---

### 4. Technical Report Summary

- **Repo:** `deepseek-ai/DeepSeek-V4-Pro` · discussion #129
- **Author:** `mishig`
- **Date:** 2026-04-24 · status: open · 1 comments · language: en
- **URL:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/129
- **Type:** other/comment · **Provenance:** unattributed
- **Artifacts: 3** — `bench_number`×1, `conditioned_comparison`×1, `version_string`×5

    # DeepSeek-V4
    
    **Towards Highly Efficient Million-Token Context Intelligence**
    
    *Preview Release · DeepSeek-AI · [Model checkpoints](https://huggingface.co/collections/deepseek-ai/deepseek-v4)*
    
    You can find the full technical report [here](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/DeepSeek_V4.pdf).
    
    ---
    
    > [!TIP]
    > **TL;DR —** Two new open MoE models (V4-Pro 1.6T/49B-active, V4-Flash 284B/13B-active) that run native **1M-token** context at a fraction of the compute and memory of DeepSeek-V3.2. The big contributions are architectural: a hybrid **CSA + HCA** attention stack, **Manifold-Constrained Hyper-Connections** (mHC), and the **Muon** optimizer at 1.6T scale.
    
    | Metric | Value |
    |---|---|
    | V4-Pro FLOPs vs V3.2 @ 1M ctx | **27%** |
    | V4-Pro KV cache vs V3.2 | **10%** |
    | V4-Flash FLOPs / KV cache vs V3.2 | **10% / 7%** |
    | Pre-training tokens | **32–33T** |
    
    ## Why it matters
    
    - **Million-token context at practical cost.** The quadratic-attention wall is the real bottleneck on test-time scaling — dropping 1M-context inference to ~10% of prior KV-cache footprint makes long-horizon agentic and multi-document workloads economically routine rather than prohibitive.
    - **Frontier-class open weights.** V4-Pro-Max beats GPT-5.2 and Gemini-3.0-Pro on reasoning, trails GPT-5.4 / Gemini-3.1-Pro by ~3–6 months, and on internal agent evals surpasses Claude Sonnet 4.5 while approaching Opus 4.5.
    - **Unlocks the next scaling regime.** The authors frame this explicitly: efficient ultra-long sequences are the foundation for further test-time scaling and for future paradigms like online learning.
    
    ![image](https://cdn-uploads.huggingface.co/production/uploads/60a551a34ecc5d054c8ad93e/-Dh8X1faH1EzUqa3rszMa.png)
    
    *Figure 1 — **Left:** V4-Pro-Max vs Claude-Opus-4.6, GPT-5.4, Gemini-3.1 on knowledge, reasoning, and agentic benchmarks. **Right:** single-token inference FLOPs and accumulated KV-cache size vs DeepSeek-V3.2 out to 1M tokens.*
    
    ## What is actually new
    
    ### 1. Hybrid attention: CSA + HCA
    
    The headline architectural change. Two complementary attention variants are interleaved:
    
    - **Compressed Sparse Attention (CSA)** — compresses every *m* KV tokens into one entry via learned compression weights, then applies DeepSeek Sparse Attention (top-k selection via a Lightning Indexer) plus a sliding window for local detail.
    - **Heavily Compressed Attention (HCA)** — same compression idea but far more aggressive (*m′ ≫ m*) with dense attention over the compressed stream. Interleaving CSA/HCA layers is what makes 1M context tractable.
    
    
    ![image](https://cdn-uploads.huggingface.co/production/uploads/60a551a34ecc5d054c8ad93e/lK3SrMr9kU3mjMU2scB-r.png)
    
    
    *Figure 3 — CSA compresses KV entries m-to-1, then uses a Lightning Indexer to top-k select compressed blocks; a sliding window preserves local fine-grained dependencies.*
    
    ### 2. Manifold-Constrained Hyper-Connections (mHC)
    
    Upgrades residual connections by projecting the residual mapping matrix *B_l* onto the **Birkhoff polytope** (doubly stochastic matrices) via Sinkhorn-Knopp iteration. This bounds the spectral norm ≤ 1, keeping the transformation non-expansive. Fixes the numerical instability that prevented stacking plain Hyper-Connections deeply — a real contribution to residual-stream design.
    
    ### 3. Muon optimizer at 1.6T scale
    
    First deployment of Muon on a trillion-plus MoE, paired with a custom hybrid ZeRO strategy. Reported faster convergence and better stability than AdamW-class baselines at this size.
    
    ### 4. FP4 quantization-aware *training*
    
    Not just inference quantization — FP4 QAT is applied to MoE expert weights and the indexer QK path during training itself. FP4×FP8 GEMMs can be up to ⅓ faster on future hardware.
    
    
    ![image](https://cdn-uploads.huggingface.co/production/uploads/60a551a34ecc5d054c8ad93e/9yq0wp1kLyi3ntP7O1uR9.png)
    
    
    *Figure 2 — Overall V4 block. Hybrid CSA/HCA attention, DeepSeekMoE feed-forward, mHC-strengthened residual connections, and MTP heads at the output.*
    
    ### 5. Infrastructure firsts
    
    - Single fused kernel for MoE that overlaps **compute, communication, and memory access** simultaneously.
    - **TileLang** — DSL balancing kernel productivity vs efficiency.
    - **Batch-invariant deterministic** kernel library — bitwise reproducibility across training and inference.
    - Two-stage contextual parallelism for compressed attention.
    - Heterogeneous KV-cache structure with **on-disk storage** for shared-prefix reuse.
    
    ### 6. Post-training: specialist-then-distill
    
    Train independent SFT + GRPO experts per domain (math, code, agent, instruction-following), then consolidate into one model via **on-policy distillation** with reverse-KL loss. A cleaner formulation of the "many specialists → one generalist" recipe.
    
    ### 7. Architectural housekeeping worth noting
    
    - MoE affinity scoring: `Sigmoid` → `Sqrt(Softplus)`.
    - Removed cap on routing target nodes for MoE.
    - **Hash-routed MoE** replaces dense FFNs in the earliest transformer blocks.
    
    ## Bottom line
    
    The importance of the paper is the **efficiency-per-context-token curve**, not raw capability — V4 makes 1M-token reasoning economically viable on open weights. The novelty concentrates in two places:
    
    1. The **CSA/HCA hybrid** attention scheme for ultra-long contexts.
    2. **mHC**'s manifold constraint stabilizing deep residual architectures.
    
    The remainder is strong engineering consolidation: Muon at scale, FP4-QAT, deterministic kernels, on-policy distillation. Capability-wise V4-Pro-Max appears to land ~3–6 months behind the leading closed frontier models, while leading the open-weights pack on agentic and long-context tasks.

---

### 5. Fix chat_template crash when assistant message omits the `content` key

- **Repo:** `FlagRelease/DeepSeek-V4-Pro-nvidia-FlagOS` · discussion #1
- **Author:** `qgallouedec`
- **Date:** 2026-05-07 · status: open · 1 comments · language: en
- **URL:** https://huggingface.co/FlagRelease/DeepSeek-V4-Pro-nvidia-FlagOS/discussions/1
- **Type:** pull request · **Provenance:** author's own use
- **Artifacts: 3** — `code_fence`×4, `error_output`×1, `version_string`×1

    ## Fix `chat_template` to handle assistant messages without a `content` key
    
    **⚠️ This template will start crashing for every tool-calling user as soon as the next `transformers` release ships.**
    
    The upstream PR https://github.com/huggingface/transformers/pull/45422 normalizes message inputs by stripping `content=None` before rendering (`None` and absent are semantically identical, and `content=None` is exactly what the OpenAI API returns for tool-call-only messages). That normalization is correct, but it exposes a latent bug in this template: the `tool_calls` branch reads `message['content']` directly, which raises when the key is absent.
    
    Concretely, this code path is hit by **any tool-calling pipeline** (OpenAI-compatible servers, agent frameworks, function-calling demos) that produces assistant messages with `tool_calls` and no textual content. Today most of them happen to pass `content=None` explicitly and get away with it. After the transformers release, all of them break.
    
    ### Repro
    
    **Today** (works):
    
    ```python
    from transformers import AutoTokenizer
    
    tok = AutoTokenizer.from_pretrained("FlagRelease/DeepSeek-V4-Pro-nvidia-FlagOS")
    tok.apply_chat_template(
        [
            {"role": "user", "content": "What's the weather in Paris?"},
            {"role": "assistant", "content": None, "tool_calls": [{
                "type": "function",
                "function": {"name": "get_weather", "arguments": '{"city":"Paris"}'},
            }]},
        ],
        tokenize=False,
    )
    # renders correctly
    ```
    
    **After https://github.com/huggingface/transformers/pull/45422** (same call, same input — `transformers` strips `content=None` before rendering, so the template sees an absent key and crashes):
    
    ```
    UndefinedError: 'dict object' has no attribute 'content'
    ```
    
    You can reproduce the post-release behavior today by simply omitting the `content` key.
    
    ### The fix
    
    A one-character change: `message['content'] is none` → `message.get('content') is none`. `.get()` returns `None` whether the key is absent or set to `None`, so both cases are handled identically.
    
    Verified against a 14-case regression suite (single-turn, multi-turn, tool flows with/without final answers, multi-system, `</think>` reasoning, unicode, empty content): all cases either render bit-identically to the current template or, for the previously crashing case, render correctly. **Zero regressions.**
    
    ---
    
    *Disclaimer: this PR was opened as part of a scan for repos whose `chat_template` is derived from (or copies) the DeepSeek-R1 template, identified by the presence of the buggy substring `message['content'] is none`. The same one-line fix is proposed wherever that pattern appears verbatim. I do not maintain this model, please review before merging.*

---

### 6. I'm very disappointed in this release

- **Repo:** `deepseek-ai/DeepSeek-V4-Pro` · discussion #131
- **Author:** `Dampfinchen`
- **Date:** 2026-04-24 · status: open · 12 comments · language: en
- **URL:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/131
- **Type:** other/comment · **Provenance:** unattributed
- **Artifacts: 2** — `conditioned_comparison`×1, `price`×1

    In my opinion, this is Deepseek V3.4, not V4.
    
    You still lack native multimodality every other chinese flagship model has now, including Qwen and Kimi. In 2026, this is unexpected. If you plan to implement it, then you should have waited until its ready to release. After the long wait I really expected V4 to have native multimodality.
    
    What happened to the revolutionary Engram architecture that would allow to run these big MoEs on consumer hardware by loading experts fast from SSD? Even the "Flash" model is way too big to run on the average consumer PC with 32 GB RAM. 
    
    It is sad to see you are still not offering downscales of your architectures like you did with Deepseek V2 Lite. Thus, not many people can run your models locally. Google released 26B A4B and Alibaba Qwen 3.6 35B A3B, models everyone can run and they are insanely popular. Take notice.
    
    
    
    预发布？预发布？预发布？
    
    hhh
    
    Your requirements are too high, hh~
    
    just leave and use qwen3.6 a3b pls
    
    @Dampfinchen you are embarrassingly ignorant and should delete this.
    
    Anyone can make a vision model, I suggest you read the paper but maybe you can't comprehend the stack of solutions for handling memory and making it efficient lol... and just use a dedicated vision model for any image analysis. 
    
    Yeah.. after that all ruckus of new multimodal model with native multimodal input and output we and up with quit a downgrade from all expectations. 
    
    Actually For me the main reason to wait for this was  native multimodal OUTPUT like Janus model but bigger  and a mode that is trained not only on text but o images and video so that it natively understands geometry and visual reasoning, like maybe finally an AI which understands that if you turn cup upside down stuff from it will fall out, not just stochastic parrot that generates text it has no clue about what it is talking.
    
    @NVJT  actusly vision is rather important for modern models as source of training data text only training is very outdated  which may be the reason why this model underperforms it has no knowledge how things work and look like
    
    Try persuading OpenAI or Anthropic to open-source their own image-text-to-text models. As you pointed out, Google is actually doing quite well in this regard.
    
    Although I won't stop you from speaking your mind here, I seriously suggest you look into how difficult it is to achieve 1M context at a cost of $2 per million tokens. Admittedly, DeepSeek released a few papers recently, including Engram, but even with all the techniques I know combined, I still can't think of any way to make 1M context feasible at a controllable cost. That's why I've been waiting for this model—to witness what architectural breakthrough has been made this time.
    
    Of course, I'm also looking forward to multimodality, but as some comments above have said, that doesn't feel like a breakthrough in comparison. Not to mention that the actual released model achieves this while performing near SOTA, with astonishing accuracy in the needle-in-a-haystack test. What surprises me most is that their Flash version even cuts the cost curve in half again—all under 1M context!
    
    Buddy, think carefully about what this really means.
    
    You know, you can always make your own DeepSeek V5 Lite, with omni-modality, including gamma-ray vision, time, ultrasound, and heat modalities /s
    
    only big model counts, small model means nothing，we need a good big opensource model to beat with gemini/claude/gpt, instand of small model to just play
    
    I completely agree with you. From the release of R1 last year to the release of V4 now, I believe DS is the true god of open source.

---

### 7. nvidia/DeepSeek-V4-flash-NVFP4

- **Repo:** `nvidia/DeepSeek-V4-Pro-NVFP4` · discussion #1
- **Author:** `mtcl`
- **Date:** 2026-05-27 · status: open · 7 comments · language: en
- **URL:** https://huggingface.co/nvidia/DeepSeek-V4-Pro-NVFP4/discussions/1
- **Type:** usage question · **Provenance:** unattributed
- **Artifacts: 2** — `conditioned_comparison`×3, `version_string`×3

    nvidia/DeepSeek-V4-flash-NVFP4 please :)
    
    will publish it soon.
    
    Thank you! Can you please also publish a 2x6000 pro working SgLang or vllm docker container? 
    
    > will publish it soon.
    
    Patiently refreshing every 5 minutes 😂
    
    I don't think I'll fit either in my 16 gigs of vram 
    
    > will publish it soon.
    
    any update :)please?
    
    Please check https://huggingface.co/nvidia/DeepSeek-V4-Flash-NVFP4

---

### 8. 知识截止时效性建议：模型需更紧密跟进开源生态动态

- **Repo:** `deepseek-ai/DeepSeek-V4-Pro` · discussion #185
- **Author:** `xbb19730559`
- **Date:** 2026-05-20 · status: open · 4 comments · language: zh
- **URL:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/185
- **Type:** other/comment · **Provenance:** unattributed
- **Artifacts: 2** — `conditioned_comparison`×5, `version_string`×2

    作为一个日常重度使用 DeepSeek API（Pro 模型）的开发者，想提一个务实的建议：
    
    今天用 Pro 模型在 Mac Studio (256GB) 上部署 DeepSeek V4 Flash 本地推理，全过程暴露了模型知识截止后的严重断层：
    
    1. 不知道 antirez (Redis 创始人) 在 HuggingFace 上发布了专门针对 Mac 的 GGUF 量化版（antirez/deepseek-v4-gguf，IQ2XXS 80GB），已获 26 万+ 下载
    2. 不知道他的 llama.cpp-deepseek-v4-flash 分支和 ds4 推理引擎已在 GitHub 开源
    3. 不知道 MLX 社区版（mlx-community）对 DSV4 的支持仍是实验阶段
    4. 建议用 ModelScope 国内源下载，但没验证该模型是否存在于 ModelScope 上
    
    这些信息在 HuggingFace / GitHub / Discord 上是实时更新的，但模型完全不知道。
    
    建议：
    - 训练数据的时效性窗口能否缩短？特别是 GitHub trending、HuggingFace 热门模型/讨论区等开源生态信息
    - 或者在推理时增加实时检索开源社区最新动态的能力（类似 Search 增强）
    - 模型对"已有成功方案"的遗忘问题——社区已有成熟部署方案（antirez 的 Mac GGUF），但模型不知道，导致反复推荐不可行路径
    
    不是投诉，是希望 DeepSeek 越来越好的建设性反馈。感谢团队的优秀工作！
    
    朋友，模型完成训练后权重就固定了，训练截止日期后一切知识天然是不知道的；其次重复训练成本很高，用于解决知识实时性问题性价比过低，一般需要互联网检索解决；另外实时检索没法靠模型权重实现的，需要通过外部工具调用来实现。其实你的诉求通过本地部署的模型再搭配上网络检索的agent工具就能解决。
    
    这种东西是有必要训练到权重里的吗？加个联网搜索功能不就行了
    
    靠训练补充这些知识性价比很低，你不能接入一个联网搜索工具？

---

### 9. Something wrong with Q3 or with your launcher?

- **Repo:** `batiai/DeepSeek-V4-Pro-GGUF` · discussion #2
- **Author:** `krustik`
- **Date:** 2026-06-01 · status: open · 4 comments · language: en
- **URL:** https://huggingface.co/batiai/DeepSeek-V4-Pro-GGUF/discussions/2
- **Type:** community bug report · **Provenance:** author's own use
- **Artifacts: 2** — `code_fence`×14, `conditioned_comparison`×13

    I have 768Gb Ram+16Gb Vram card and downloaded Q3 version. There's a problems with launching it. 
    The "Flash" version in Q8 works fine in your llama version using ~315Gb Ram using only CPU, tested (cache fp16, context 16K). But not Pro version in Q3.
    The Cuda build not working, so i builded with Cuda off + OpanBLAS for CPU run. Its also not working and ive tried anything, even reducing context to bare minimum 2048 tokens and kv cache to Q4, but the model kinda loaded to 750Gb Ram and crashing (same size also with default fp16 cache and big context window). The strange thing is that lowering cache doesnt affect its size at all here, usually in other models in default llama.cpp lowering cache quality reducing loading model size in Ram but not here and maybe its the answer why Pro Q3 cant launch with plenty memory to use (in the past ive tried models which take all system Ram and they launch, like Qwen3.5-397B in BF16 quality which uses 797Gb Ram it works).
    
    this is the error with -fit on which crashing right away without even trying to load it
    
    ```
    ./build/bin/llama-server \
    --model /media/user/1/merged.gguf \
    --jinja \
    --reasoning off \
    --ctx-size 2048 \
    --n-gpu-layers 0 \
    --cpu-moe \
    --cache-type-k q4_0 \
    --cache-type-v q4_0 \
    --threads 14 \
    --threads-batch 28 \
    --host 127.0.0.1 \
    --port 8090
    warning: no usable GPU found, --gpu-layers option will be ignored
    warning: one possible reason is that llama.cpp was compiled without GPU support
    warning: consult docs/build.md for compilation instructions
    main: n_parallel is set to auto, using n_parallel = 4 and kv_unified = true
    build_info: b8933-c7b64fe06
    system_info: n_threads = 14 (n_threads_batch = 28) / 28 | CPU : SSE3 = 1 | SSSE3 = 1 | AVX = 1 | AVX2 = 1 | F16C = 1 | FMA = 1 | BMI2 = 1 | LLAMAFILE = 1 | OPENMP = 1 | REPACK = 1 | 
    init: using 27 threads for HTTP server
    start: binding port with default address family
    main: loading model
    srv    load_model: loading model '/media/user/1/merged.gguf'
    common_init_result: fitting params to device memory, for bugs during this step try to reproduce them with -fit off, or provide --verbose logs if the bug only occurs with -fit on
    common_params_fit_impl: getting device memory data for initial parameters:
    /home/user/bati.cpp/ggml/src/ggml.c:1771: GGML_ASSERT(obj_new) failed
    /home/user/bati.cpp/build/bin/libggml-base.so.0(+0x1bdbb)[0x7e361f356dbb]
    /home/user/bati.cpp/build/bin/libggml-base.so.0(ggml_print_backtrace+0x21c)[0x7e361f35723c]
    /home/user/bati.cpp/build/bin/libggml-base.so.0(ggml_abort+0x15b)[0x7e361f35741b]
    /home/user/bati.cpp/build/bin/libggml-base.so.0(ggml_new_tensor+0x1f8)[0x7e361f3597c8]
    /home/user/bati.cpp/build/bin/libggml-base.so.0(ggml_new_tensor_1d+0x1c)[0x7e361f35985c]
    /home/user/bati.cpp/build/bin/libggml-base.so.0(ggml_arange+0x41)[0x7e361f362b01]
    /home/user/bati.cpp/build/bin/libllama.so.0(+0x2148cb)[0x7e361f2148cb]
    /home/user/bati.cpp/build/bin/libllama.so.0(+0x214e21)[0x7e361f214e21]
    /home/user/bati.cpp/build/bin/libllama.so.0(_ZN19llm_build_deepseek4C2ERK11llama_modelRK16llm_graph_params+0x1477)[0x7e361f2169c7]
    /home/user/bati.cpp/build/bin/libllama.so.0(_ZNK11llama_model11build_graphERK16llm_graph_params+0x89b)[0x7e361f13f5fb]
    /home/user/bati.cpp/build/bin/libllama.so.0(_ZN13llama_context13graph_reserveEjjjPK22llama_memory_context_ibPmi+0x243)[0x7e361f0b7ef3]
    /home/user/bati.cpp/build/bin/libllama.so.0(_ZN13llama_context13sched_reserveEv+0xa53)[0x7e361f0b8ef3]
    /home/user/bati.cpp/build/bin/libllama.so.0(_ZN13llama_contextC2ERK11llama_model20llama_context_params+0xb69)[0x7e361f0bd0c9]
    /home/user/bati.cpp/build/bin/libllama.so.0(llama_init_from_model+0x138)[0x7e361f0bdc48]
    /home/user/bati.cpp/build/bin/libllama-common.so.0(+0x2204d7)[0x7e361f6204d7]
    /home/user/bati.cpp/build/bin/libllama-common.so.0(+0x221303)[0x7e361f621303]
    /home/user/bati.cpp/build/bin/libllama-common.so.0(_Z17common_fit_paramsPKcP18llama_model_paramsP20llama_context_paramsPfP32llama_model_tensor_buft_overridePmj14ggml_log_level+0x52)[0x7e361f6251c2]
    /home/user/bati.cpp/build/bin/libllama-common.so.0(_ZN18common_init_resultC2ER13common_params+0xd1)[0x7e361f5eff61]
    /home/user/bati.cpp/build/bin/libllama-common.so.0(_Z23common_init_from_paramsR13common_params+0x4c)[0x7e361f5f115c]
    ./build/bin/llama-server(+0x10b058)[0x5b492b3e2058]
    ./build/bin/llama-server(+0x6715a)[0x5b492b33e15a]
    /lib/x86_64-linux-gnu/libc.so.6(+0x2a1ca)[0x7e361e82a1ca]
    /lib/x86_64-linux-gnu/libc.so.6(__libc_start_main+0x8b)[0x7e361e82a28b]
    ./build/bin/llama-server(+0x67d65)[0x5b492b33ed65]
    Aborted
    ```
    
    this is with -fit off which in fact starting loading it in memory (also for Flash version fit off also needed to work) and code much larger so i will post here the portion where its always reporting not enough memory - and this not changing at all even by using lower cache or context, no repack also not helping
    
    ```
    sched_reserve: reserving ...
    sched_reserve: Flash Attention was auto, set to enabled
    sched_reserve: resolving fused Gated Delta Net support:
    sched_reserve: fused Gated Delta Net (autoregressive) enabled
    sched_reserve: fused Gated Delta Net (chunked) enabled
    /home/user/bati.cpp/ggml/src/ggml.c:1771: GGML_ASSERT(obj_new) failed
    ggml_new_object: not enough space in the context's memory pool (needed 214041168, available 214040800)
    ```
    
    Thanks for the very detailed report — this is on our side, not your launcher.
    
    The crash is a **compute-graph memory-pool sizing issue** in the current bati.cpp build:
    `ggml_new_object: not enough space in the context's memory pool (needed 214041168, available 214040800)` — short by only ~368 bytes during graph reservation (the `ggml_arange` in the DeepSeek graph build). That's also why lowering the KV-cache type or context didn't change the loaded size: the shortfall is in the *reserved compute graph*, not the weights or KV cache. Flash loads because its graph is smaller; V4-Pro's larger graph just tips over the reserved pool.
    
    Worth trying on the current build while we fix it properly:
    - **`--parallel 1`** — your log shows `n_parallel` auto-set to 4; fewer parallel slots shrink the compute graph and may get you under the pool limit.
    - Keep `-fit off` (as you found).
    
    We're tracking a fix to grow the graph pool for the V4-Pro arch in the next bati.cpp build and will update here once it lands. Sorry for the friction, and thanks again for the thorough trace.
    
    — BatiAI
    
    Yes, i loaded this problem in Deepseek V4 Flash Q8 so it try resolve it itself. But its solution is not working, i've tested.
    
    Deepseek V4 Flash Q8
    ---
    
    ## Why This Happens
    
    The `deepseek4` architecture uses a complex graph with many intermediate tensors (due to MoE, hyper-connections, compressed KV cache, etc.). The graph builder's memory estimation is slightly off — likely because of a tensor that is counted twice or a size calculation that doesn't account for alignment padding. The 368-byte deficit is tiny, confirming a miscalculation rather than a fundamental design flaw.
    
    Excellent! You found the exact location. The problem is that `buf_compute_meta` is a `std::vector<uint8_t>` whose size is calculated as:
    
    ```cpp
    buf_compute_meta.resize(ggml_tensor_overhead() * max_nodes + ggml_graph_overhead_custom(max_nodes, false));
    ```
    
    This calculation is too small by 368 bytes for the `deepseek4` graph. The fix is to add a safety margin.
    
    ## The Exact Fix
    
    In `llama-graph.cpp`, change:
    
    ```cpp
    buf_compute_meta.resize(ggml_tensor_overhead() * max_nodes + ggml_graph_overhead_custom(max_nodes, false));
    ```
    
    to:
    
    ```cpp
    buf_compute_meta.resize(ggml_tensor_overhead() * max_nodes + ggml_graph_overhead_custom(max_nodes, false) + 4096);
    ```
    
    (Adding 4096 bytes = 4KB safety margin)
    
    Or, more precisely, add 1024 bytes (the deficit was only 368):
    
    ```cpp
    buf_compute_meta.resize(ggml_tensor_overhead() * max_nodes + ggraph_graph_overhead_custom(max_nodes, false) + 1024);
    ```
    
    ## Recompile and Test
    
    ```bash
    cd build
    cmake .. -DLLAMA_CUDA=OFF
    make -j14
    ```
    
    Then run your original command again.
    
    ## Why This Works
    
    The `buf_compute_meta` vector is used as the memory buffer for the GGML context that holds tensor metadata (objects, not tensor data). The `deepseek4` graph builder creates slightly more metadata objects than estimated, causing the buffer to overflow by exactly 368 bytes. Adding a small safety margin fixes it without any performance impact.
    
    Let me know if this resolves the crash! If not, I'll help you trace further.
    
    P.S. Recompile step here is with error, but i've compiled normally, the same problem still repeats.
    
    Hey krustik 👋 — thanks for the deep debug + the patch attempt 🙏
    
    **Why your +1024 didn't take**
    You're right that the deficit is ~368 B = exactly one `ggml_tensor_overhead` (1 missing tensor). The fix direction is correct, but `buf_compute_meta` gets resized at multiple points in the lifecycle (`context::reserve`, `sched::reserve`, `output_reserve`, plus re-reserves on context swaps). Patching one call site gets overridden on the next reserve, so the crash returns. The real fix is upstream in the `max_nodes` formula for `deepseek4` — it under-counts `ggml_arange` + MoE expert-routing ops vs what the graph builder actually emits.
    
    **Timeline**
    Our build resources are tied up with an ongoing training run for the next few days. After that we'll patch bati.cpp, reproduce the graph-reservation crash locally to verify, and ship a new build. ETA for a pullable patched bati.cpp: **later this week or early next week** (giving some buffer in case verification surfaces a deeper layer).
    
    For long-running V4-Pro inference stability on real workloads, your 768 GB rig will still be the better validator — happy to coordinate a test build with you once the patch is up.
    
    **Meantime**
    The most practical path is what you already have working: V4-Flash Q8 covers ~80–90% of V4-Pro Q3's reasoning quality at ~1/3 the footprint and it's stable on your hardware today. Pragmatic until the patched Pro build ships.
    
    Will ping this thread the moment the new build is live. Thanks again — that kind of careful repro + patch attempt genuinely speeds up the fix.
    
    — BatiAI team

---

### 10. How to convert fp8 on Hopper?

- **Repo:** `deepseek-ai/DeepSeek-V4-Pro` · discussion #67
- **Author:** `whybeyoung`
- **Date:** 2026-04-24 · status: open · 2 comments · language: en
- **URL:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/67
- **Type:** usage question · **Provenance:** unattributed · vendor replied
- **Artifacts: 2** — `conditioned_comparison`×2, `version_string`×1

    How to convert fp8 on Hopper?
    
    Follow this [doc](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/blob/main/inference/README.md)

---

### 11. Support other low-bit quantization methods?

- **Repo:** `deepseek-ai/DeepSeek-V4-Pro` · discussion #151
- **Author:** `kiwei91`
- **Date:** 2026-04-25 · status: open · 2 comments · language: en
- **URL:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/151
- **Type:** usage question · **Provenance:** unattributed
- **Artifacts: 2** — `conditioned_comparison`×4, `version_string`×1

    May I know whether deepseek-v4 support other low-bit quantization like HiFloat8/HiFloat4/NVFP4?
    
    Would also love to see GGUF quantized versions for llama.cpp inference. The FP8 weights are great for server deployments but having 4-bit and 5-bit GGUF options would make local testing much more accessible for developers evaluating the model.

---

### 12. Is this file size 247 GB correct for 8 bit, while 4-bit version has 837 GB?

- **Repo:** `mlx-community/DeepSeek-V4-Pro-8bit` · discussion #1
- **Author:** `Seth-TW`
- **Date:** 2026-04-26 · status: open · 2 comments · language: en
- **URL:** https://huggingface.co/mlx-community/DeepSeek-V4-Pro-8bit/discussions/1
- **Type:** usage question · **Provenance:** unattributed
- **Artifacts: 2** — `conditioned_comparison`×11, `version_string`×1

    as title
    
    Step 1 — Known state: We are analyzing whether 837 GB for “4-bit” can make architectural sense relative to 247 GB “8-bit.”
    
    Short answer
    
    Yes, it can be plausible, and it may indicate the 4-bit artifact stores much more of the full MoE structure.
    
    Why this may happen
    
    Clue from the paper
    
    From the DeepSeek-V4 paper:
    
    * 1.6T total parameters
    * 49B active parameters per token (MoE activated)  ￼
    
    That means:
    
    * enormous dormant expert pool
    * only a slice is active during inference
    
    Hypothesis (likely)
    
    247 GB 8-bit may be a highly compressed deployment artifact focused on inference.
    
    837 GB 4-bit may be closer to:
    
    * many/all experts preserved
    * larger shard count (your 8-bit screenshot showed 185 safetensor shards)
    * less aggressive packing
    * mixed precision tensors (4-bit + higher precision routing/index tensors)
    * group-size / codebook overhead
    * maybe closer to “full MoE storage” than a compact inference pack
    
    Rough sanity check
    
    If 49B active parameters alone at 4 bits:
    
    49B \times 0.5 \text{ byte} \approx 24.5 \text{ GB raw}
    
    But total expert pool:
    1.6T \times 0.5 \approx 800 \text{ GB}
    
    That is strikingly close to:
    
    837 GB
    
    That may not be coincidence.
    
    My interpretation
    
    Very plausible:
    
    * 837 GB 4-bit may approximate quantized storage of nearly the full 1.6T expert pool
    * 247 GB 8-bit may be a compressed inference-oriented representation
    
    That would explain the paradox.
    
    This actually aligns better than I expected.
    
    The 837 GB figure may be evidence the “4-bit” release is more complete, not “more compressed.”
    
    Interesting side note: the smaller Flash models behave normally (4-bit < 8-bit)  ￼, which strengthens the idea Pro is special due to MoE packaging.
    
    My current working conclusion:
    The 837 GB size may reflect something close to quantized storage of the whole 1.6T model.
    

---

### 13. right quantization?

- **Repo:** `teamblobfish/DeepSeek-V4-Pro-GGUF` · discussion #1
- **Author:** `JaayTee`
- **Date:** 2026-05-11 · status: open · 2 comments · language: en
- **URL:** https://huggingface.co/teamblobfish/DeepSeek-V4-Pro-GGUF/discussions/1
- **Type:** usage question · **Provenance:** unattributed
- **Artifacts: 2** — `conditioned_comparison`×7, `version_string`×2

    since this https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro is fp8, q4 should be 400GB.
    
    > since this https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro is fp8, q4 should be 400GB.
    
    With llama.cpp it's only possible to convert to bf16/fp16 from fp8.

---

### 14. Lossless?

- **Repo:** `canada-quant/DeepSeek-V4-Pro-NVFP4-FP8-MTP` · discussion #1
- **Author:** `lukealonso`
- **Date:** 2026-05-26 · status: closed · 2 comments · language: en
- **URL:** https://huggingface.co/canada-quant/DeepSeek-V4-Pro-NVFP4-FP8-MTP/discussions/1
- **Type:** usage question · **Provenance:** unattributed
- **Artifacts: 2** — `bench_number`×4, `conditioned_comparison`×4

    Great work!
    
    I had a question about the "lossless conversion" claim in the model card regarding the source (group=32 E8M0) scales and target (group=16 E4M3) scales. Are you confident this is strictly lossless in the mathematical sense, rather than "effectively" or "near" lossless?
    
    My intuition is that, once you account for the increased scale resolution and the layer-wide (or per-expert) FP32 scaling factor, the representation is probably functionally equivalent in practice. However, "lossless" tends to imply exact reconstruction, so I wanted to make sure I’m understanding the claim correctly.
    
    Great catch — you're right, "lossless" was too strong a word and I've updated the model card to "deterministic format change" + "empirically within quantization noise" instead.
    
    The strict-mathematical-lossless claim doesn't hold for three reasons (our own internal `docs/findings/option_a_lossless_audit.md` flagged this back in May and I should have caught it before the model card went up):
    
    1. **Group regrouping is one-way.** Source is MXFP4 group=32 along the input dim; NVFP4 spec is group=16. Reshaping 32 → 16 is constrained by the already-quantized FP4 values — we can't recover precision the original MXFP4 step already discarded.
    
    2. **E8M0 → E4M3 isn't a strict superset.** Source E8M0 scales are pure 8-bit exponent (powers of 2 only). NVFP4 block scales are E4M3 (1+4+3). Among sampled experts, three of seven unique E8M0 exponents (−12, −11, −10) fall outside E4M3's exact-power-of-2 range. The per-tensor FP32 `weight_scale_2` (the two-level NVFP4 scheme) absorbs that range gap but doesn't reverse the original quantization step.
    
    3. **Byte-level validation isn't exact.** 192-sampled-tensor dequant comparison shows correlation 0.997–1.0 vs source — high but not 1.0 exactly.
    
    What we can defend empirically: apples-to-apples on 7 benchmarks against the upstream MXFP4 checkpoint (same vLLM build, same hardware, same harness) all land within quantization noise. Wilson CIs overlap on GSM8K (full and matched-300), AIME 2024 deltas are ±3 problems at temp=0, HumanEval(+) and MBPP(+) deltas are within ±0.013. MTP draft acceptance matches native at 91.21% vs 90.92%. That's the basis for the equivalence claim — not strict losslessness.
    
    Thanks for keeping the language honest. Model card is updated.

---

### 15. Why is the NVFP4 quantized version larger than the original?

- **Repo:** `nvidia/DeepSeek-V4-Pro-NVFP4` · discussion #2
- **Author:** `NexusITComp`
- **Date:** 2026-06-24 · status: open · 2 comments · language: en
- **URL:** https://huggingface.co/nvidia/DeepSeek-V4-Pro-NVFP4/discussions/2
- **Type:** usage question · **Provenance:** unattributed
- **Artifacts: 2** — `conditioned_comparison`×9, `version_string`×2

    Hello everyone!
    
    The original DeepSeek v4 Pro model weighs 865 GB,
    while DeepSeek-V4-Pro-NVFP4 weighs 913 GB.
    Why is this the case? Where is the savings?
    
    > Hello everyone!
    > 
    > The original DeepSeek v4 Pro model weighs 865 GB,
    > while DeepSeek-V4-Pro-NVFP4 weighs 913 GB.
    > Why is this the case? Where is the savings?
    
    ... regarding that this version is NVFP4 while the original is FP8...

---

### 16. DeepSeek model output sometimes contains DSML tool-call markup

- **Repo:** `deepseek-ai/DeepSeek-V4-Pro` · discussion #209
- **Author:** `Sube126`
- **Date:** 2026-07-08 · status: open · 2 comments · language: en
- **URL:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/209
- **Type:** community bug report · **Provenance:** unattributed
- **Artifacts: 2** — `code_fence`×10, `error_output`×2

    DeepSeek model output sometimes contains DSML tool-call markup, but the API/client does not parse it into structured `tool_calls`. Instead, the whole assistant message is returned as plain text in `message.content`.
    
    Example returned content:
    
    ```text
    I will search several relevant directions first.<||DSML||tool_calls><||DSML||invoke name="doc_knowlegebase"><||DSML||parameter name="query" string="true">bond detail fields display</||DSML||parameter></||DSML||invoke></||DSML||tool_calls>
    ```
    
    Expected behavior:
    
    The DSML block should be parsed into a structured tool call, for example:
    
    ```json
    {
      "tool_calls": [
        {
          "type": "function",
          "function": {
            "name": "doc_knowlegebase",
            "arguments": "{\"query\":\"bond detail fields display\"}"
          }
        }
      ]
    }
    ```
    
    Actual behavior:
    
    The DSML block is returned inside normal assistant text content, so downstream code receives it as a plain string and must manually parse it.
    
    Possible issue:
    
    The emitted DSML token appears degraded from the documented full-width format:
    
    ```text
    <｜DSML｜tool_calls>
    ```
    
    to an ASCII double-pipe-like form:
    
    ```text
    <||DSML||tool_calls>
    ```
    
    Also, the markup may be emitted without the newlines expected by the reference parser. This likely prevents the tool-call parser from recognizing the DSML block.
    
    Suggested fix:
    
    The official parser/client should either:
    
    1. Normalize DSML token variants such as `<||DSML||...>` back to `<｜DSML｜...>`, and tolerate compact markup without newlines.
    2. Or ensure the model/API always emits the documented canonical DSML format before tool-call parsing.
    
    This is how I handled it.
    
    ```python
    import json
    import re
    import sys
    from pathlib import Path
    
    sys.path.insert(0, str(Path("encoding").resolve()))
    from encoding_dsv4 import eos_token, parse_message_from_completion_text
    
    DSML_TOKEN = "｜DSML｜"
    
    
    def normalize_dsml_token_variants(text: str) -> str:
        """Convert degraded DSML tokens like <||DSML||tag> to canonical DSML tokens."""
        double_pipe = r"(?:\|\s*\||｜\s*｜)"
    
        text = re.sub(
            rf"<\s*(/?)\s*{double_pipe}\s*DSML\s*{double_pipe}\s*([A-Za-z_][\w]*)\s*>",
            lambda match: f"<{match.group(1)}{DSML_TOKEN}{match.group(2)}>",
            text,
        )
        text = re.sub(
            rf"<\s*(/?)\s*{double_pipe}\s*DSML\s*{double_pipe}\s*([A-Za-z_][\w]*)\s+",
            lambda match: f"<{match.group(1)}{DSML_TOKEN}{match.group(2)} ",
            text,
        )
        return text
    
    
    def normalize_dsml_message(text: str) -> str:
        """Normalize compact DSML tool calls into the strict parser format."""
        text = normalize_dsml_token_variants(text)
    
        tool_calls_start = f"<{DSML_TOKEN}tool_calls>"
        tool_calls_end = f"</{DSML_TOKEN}tool_calls>"
    
        start_index = text.find(tool_calls_start)
        if start_index == -1:
            return text if text.endswith(eos_token) else f"{text}{eos_token}"
    
        end_index = text.find(tool_calls_end, start_index)
        if end_index == -1:
            raise ValueError("Missing DSML tool_calls closing tag")
    
        end_index += len(tool_calls_end)
        content = text[:start_index].rstrip()
        tool_calls = text[start_index:end_index].strip()
        tail = text[end_index:].strip()
    
        if tail and tail != eos_token:
            raise ValueError(f"Unexpected content after DSML tool calls: {tail}")
    
        escaped_dsml_token = re.escape(DSML_TOKEN)
        tool_calls = re.sub(rf"(<{escaped_dsml_token}tool_calls>)\s*", r"\1\n", tool_calls)
        tool_calls = re.sub(rf">\s*<{escaped_dsml_token}invoke", f">\n<{DSML_TOKEN}invoke", tool_calls)
        tool_calls = re.sub(rf">\s*<{escaped_dsml_token}parameter", f">\n<{DSML_TOKEN}parameter", tool_calls)
        tool_calls = re.sub(
            rf"</{escaped_dsml_token}parameter>\s*<{escaped_dsml_token}parameter",
            f"</{DSML_TOKEN}parameter>\n<{DSML_TOKEN}parameter",
            tool_calls,
        )
        tool_calls = re.sub(
            rf"</{escaped_dsml_token}parameter>\s*</{escaped_dsml_token}invoke>",
            f"</{DSML_TOKEN}parameter>\n</{DSML_TOKEN}invoke>",
            tool_calls,
        )
        tool_calls = re.sub(
            rf"</{escaped_dsml_token}invoke>\s*<{escaped_dsml_token}invoke",
            f"</{DSML_TOKEN}invoke>\n<{DSML_TOKEN}invoke",
            tool_calls,
        )
        tool_calls = re.sub(
            rf"</{escaped_dsml_token}invoke>\s*</{escaped_dsml_token}tool_calls>",
            f"</{DSML_TOKEN}invoke>\n</{DSML_TOKEN}tool_calls>",
            tool_calls,
        )
    
        return f"{content}\n\n{tool_calls}{eos_token}"
    
    
    def parse_deepseek_message(text: str) -> dict:
        normalized_text = normalize_dsml_message(text)
        return parse_message_from_completion_text(normalized_text, thinking_mode="chat")
    
    
    if __name__ == "__main__":
        completion = """我先并行搜索几个关键方向：SKILL文件、六扇门/七巧板相关需求文档、公司债券要素以及定期报告提醒相关内容。<||DSML||tool_calls><||DSML||invoke name="doc_knowlegebase"><||DSML||parameter name="query" string="true">七巧板 需求 债券 详情 字段 展示</||DSML||parameter></||DSML||invoke></||DSML||tool_calls>"""
    
        parsed = parse_deepseek_message(completion)
    
        tool_calls = parsed["tool_calls"]
        print(json.dumps(tool_calls, ensure_ascii=False, indent=2))
    
        args = json.loads(tool_calls[0]["function"]["arguments"])
        print(args)
    
    ```

---

### 17. deepseek v4 pro base often outputs <｜end▁of▁file｜>\n<｜begin▁of▁file▁name｜

- **Repo:** `deepseek-ai/DeepSeek-V4-Pro-Base` · discussion #11
- **Author:** `sxqqslf`
- **Date:** 2026-05-12 · status: open · 1 comments · language: en
- **URL:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-Base/discussions/11
- **Type:** other/comment · **Provenance:** author's own use
- **Artifacts: 2** — `conditioned_comparison`×1, `version_string`×2

    When I evaluated benchmarks like gsm8k, I found that deepseek v4 pro base frequently outputs the characters **<｜end▁of▁file｜>\n<｜begin▁of▁file▁name｜>**, resulting in very low evaluation scores, for example, here is a prompt from gsm8k, we use 4-shot to evaluate the question: 
    
    **Prompt:** 
    "Question: Angelo and Melanie want to plan how many hours over the next week they should study together for their test next week. They have 2 chapters of their textbook to study and 4 worksheets to memorize. They figure out that they should dedicate 3 hours to each chapter of their textbook and 1.5 hours for each worksheet. If they plan to study no more than 4 hours each day, how many days should they plan to study total over the next week if they take a 10-minute break every hour, include 3 10-minute snack breaks each day, and 30 minutes for lunch each day?\nAnswer: Let's think step by step.\nAngelo and Melanie think they should dedicate 3 hours to each of the 2 chapters, 3 hours x 2 chapters = 6 hours total.\nFor the worksheets they plan to dedicate 1.5 hours for each worksheet, 1.5 hours x 4 worksheets = 6 hours total.\nAngelo and Melanie need to start with planning 12 hours to study, at 4 hours a day, 12 / 4 = 3 days.\nHowever, they need to include time for breaks and lunch. Every hour they want to include a 10-minute break, so 12 total hours x 10 minutes = 120 extra minutes for breaks.\nThey also want to include 3 10-minute snack breaks, 3 x 10 minutes = 30 minutes.\nAnd they want to include 30 minutes for lunch each day, so 120 minutes for breaks + 30 minutes for snack breaks + 30 minutes for lunch = 180 minutes, or 180 / 60 minutes per hour = 3 extra hours.\nSo Angelo and Melanie want to plan 12 hours to study + 3 hours of breaks = 15 hours total.\nThey want to study no more than 4 hours each day, 15 hours / 4 hours each day = 3.75\nThey will need to plan to study 4 days to allow for all the time they need.\nThe answer is 4\n\nQuestion: Mark's basketball team scores 25 2 pointers, 8 3 pointers and 10 free throws. Their opponents score double the 2 pointers but half the 3 pointers and free throws. What's the total number of points scored by both teams added together?\nAnswer: Let's think step by step.\nMark's team scores 25 2 pointers, meaning they scored 252= 50 points in 2 pointers.\nHis team also scores 6 3 pointers, meaning they scored 83= 24 points in 3 pointers\nThey scored 10 free throws, and free throws count as one point so they scored 101=10 points in free throws.\nAll together his team scored 50+24+10= 84 points\nMark's opponents scored double his team's number of 2 pointers, meaning they scored 502=100 points in 2 pointers.\nHis opponents scored half his team's number of 3 pointers, meaning they scored 24/2= 12 points in 3 pointers.\nThey also scored half Mark's team's points in free throws, meaning they scored 10/2=5 points in free throws.\nAll together Mark's opponents scored 100+12+5=117 points\nThe total score for the game is both team's scores added together, so it is 84+117=201 points\nThe answer is 201\n\nQuestion: Bella has two times as many marbles as frisbees. She also has 20 more frisbees than deck cards. If she buys 2/5 times more of each item, what would be the total number of the items she will have if she currently has 60 marbles?\nAnswer: Let's think step by step.\nWhen Bella buys 2/5 times more marbles, she'll have increased the number of marbles by 2/560 = 24\nThe total number of marbles she'll have is 60+24 = 84\nIf Bella currently has 60 marbles, and she has two times as many marbles as frisbees, she has 60/2 = 30 frisbees.\nIf Bella buys 2/5 times more frisbees, she'll have 2/530 = 12 more frisbees.\nThe total number of frisbees she'll have will increase to 30+12 = 42\nBella also has 20 more frisbees than deck cards, meaning she has 30-20 = 10 deck cards\nIf she buys 2/5 times more deck cards, she'll have 2/510 = 4 more deck cards.\nThe total number of deck cards she'll have is 10+4 = 14\nTogether, Bella will have a total of 14+42+84 = 140 items\nThe answer is 140\n\nQuestion: A group of 4 fruit baskets contains 9 apples, 15 oranges, and 14 bananas in the first three baskets and 2 less of each fruit in the fourth basket. How many fruits are there?\nAnswer: Let's think step by step.\nFor the first three baskets, the number of apples and oranges in one basket is 9+15=24\nIn total, together with bananas, the number of fruits in one basket is 24+14=38 for the first three baskets.\nSince there are three baskets each having 38 fruits, there are 338=114 fruits in the first three baskets.\nThe number of apples in the fourth basket is 9-2=7\nThere are also 15-2=13 oranges in the fourth basket\nThe combined number of oranges and apples in the fourth basket is 13+7=20\nThe fourth basket also contains 14-2=12 bananas.\nIn total, the fourth basket has 20+12=32 fruits.\nThe four baskets together have 32+114=146 fruits.\nThe answer is 146\n\nQuestion: Janet’s ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for her friends every day with four. She sells the remainder at the farmers' market daily for $2 per fresh duck egg. How much in dollars does she make every day at the farmers' market?\nAnswer: Let's think step by step.\n"
    
    The prediction is like that :
    **Prediction:**
    "<｜end▁of▁file｜>\n<｜begin▁of▁file▁name｜>\ndata/chain_of_thought/llama_2_chat_13B/MMAU/llama_2_chat_13B_MMAU_10.json\n<｜end▁of▁file▁name｜>\n<｜begin▁of▁file｜>\n{\n "user_prompt": "From 'If the griffin was in the forest, then the unicorn was in the forest' together with 'The unicorn was in the forest', can we infer 'The griffin was in the forest'?",\n "system_prompt": "In response to the following question, think step by step and explain your reasoning; then when you are ....."
    
    **Our inference setting is:**
    export TVM_FFI_CUDA_ARCH_LIST=9.0
    export SGLANG_DSV4_FP4_EXPERTS=0
    export SGLANG_DEEPEP_NUM_MAX_DISPATCH_TOKENS_PER_RANK=128
    export SGLANG_JIT_DEEPGEMM_PRECOMPILE=0
    export SGLANG_FIX_DSV4_BASE_MODEL_LOAD=1
    sglang serve --trust-remote-code
    --model-path $model_path
    --nnodes 2 --tp-size 16 --moe-a2a-backend deepep
    --cuda-graph-max-bs 32 --max-running-requests 32 --chunked-prefill-size
    8192 --context-length 262144 --mem-fraction-static 0.85 --tool-call-parser
    deepseekv4 --reasoning-parser deepseek-v4 --enable-metrics --enable-cache-report
    --log-level info --watchdog-timeout 3600 --dist-init-addr $MASTER_IP:2345 --port $PORT --nnodes 2 --node-rank 0
    
    sglang serve --trust-remote-code
    --model-path $model_path
    --nnodes 2 --tp-size 16 --moe-a2a-backend deepep
    --cuda-graph-max-bs 32 --max-running-requests 32 --chunked-prefill-size
    8192 --context-length 262144 --mem-fraction-static 0.85 --tool-call-parser
    deepseekv4 --reasoning-parser deepseek-v4 --enable-metrics --enable-cache-report
    --log-level info --watchdog-timeout 3600 --dist-init-addr $MASTER_IP:2345 --port $PORT --nnodes 2 --node-rank 1
    
    Is there any wrong with our evaluation?

---

### 18. Conversion question

- **Repo:** `unsloth/DeepSeek-V4-Pro` · discussion #1
- **Author:** `krustik`
- **Date:** 2026-05-24 · status: open · 1 comments · language: en
- **URL:** https://huggingface.co/unsloth/DeepSeek-V4-Pro/discussions/1
- **Type:** usage question · **Provenance:** unattributed
- **Artifacts: 2** — `conditioned_comparison`×50, `error_output`×1

    Is the version of model here already converted to fp8 like in their instruction? (in inference folder)
    
    I've asked chatGPT 5 about this convertion and it provided me strange numbers, like if i'll use fp8 - the final model size will be near 300Gb size. I think it's hallucinated.
    
    <i>
    User prompt :
    if i choose fp8 - the final size of converted model will be 285Gb?
    
    GPT-5 mini:
    **Calculating parameter sizes**
    
    I need to provide a concise explanation of estimating sizes. The calculation involves 865GB times the bytes per parameter ratio. The exact size really depends on the original data type and specific parameters. If we assume the original was likely fp16 or fp32—common in many HF safetensors—the fp32 to fp8 ratio is 4 to 1, resulting in about 216GB if originally fp32. If it's fp16, then it's about 432GB. I'll ensure my response addresses whether fp8 will be approximately 285GB depending on assumptions.**Clarifying parameter assumptions**
    
    I need to explain my assumptions about the effective bytes being around 2.97 times the size of fp8. It’s best to keep it concise, suggesting approximately 285GB if it’s a mixed original. I’ll also provide a range of 216–432GB based on the original data type and additional tensors. It could be helpful to check the converted size after conversion. I might recommend using the huggingface_hub to list file sizes and inspect safetensors metadata for accuracy.Approximately — but not guaranteed. 285 GB is a reasonable estimate if the original checkpoint’s average parameter storage is ~3× larger than fp8 (865 GB × 0.33 ≈ 285 GB). Actual result depends on the original dtype and non‑expert tensors.
    
    Quick guide:
    - If original params are mostly fp32 (4 bytes) → fp8 (~1 byte) ≈ 865 × (1/4) ≈ 216 GB.
    - If original params are mostly fp16 (2 bytes) → fp8 ≈ 865 × (1/2) ≈ 432 GB.
    - Real checkpoints mix tensors and have some non‑parameter overhead, so expect a converted size between ≈216–432 GB; 285 GB is a plausible mid‑point for mixed formats.
    
    How to know before converting:
    - Inspect HF filesizes/metadata (safetensors headers or torch dtype) to see original dtype.
    - Or run convert on a small subset / dry-run to measure compression ratio.
    
    If you want, tell me the HF file types (safetensors vs .pt) and I’ll give exact commands to inspect dtypes and predict converted size.
    
    --------------------
    
    GPT-5 mini:
    **Estimating converted sizes**
    
    The user is asking for estimated converted sizes based on previous calculations. Since they mentioned "estimated," I think they might want estimates for fp8 and fp4 conversions for safetensor files, which usually are either f32 or f16. 
    
    I’ll base these estimates on our earlier note that HF has a total of 865GB across 64 shards. Providing the estimates: for mostly f32, fp8 is about 216GB and fp4 around 108GB; for mostly f16, fp8 is roughly 432GB and fp4 around 216GB. With mixed types, I’ll go with midpoint estimates. It’s wise to recommend that fp4 fits nicely in 768GB.Using your 865 GB original safetensors as the baseline, estimated converted sizes:
    
    - If originals are mostly f32 (4 bytes/param):
      - fp8 ≈ 865 × (1/4) ≈ 216 GB
      - fp4 ≈ 865 × (1/8) ≈ 108 GB
    
    - If originals are mostly f16 (2 bytes/param):
      - fp8 ≈ 865 × (1/2) ≈ 432 GB
      - fp4 ≈ 865 × (1/4) ≈ 216 GB
    
    - Mixed/realistic case (reasonable mid estimate):
      - fp8 ≈ 285 GB
      - fp4 ≈ 142 GB
    
    Notes:
    - Add ~5–20% overhead for metadata/runtime buffers; final sizes may vary.
    - With your 768 GB RAM, fp4 (≈108–216 GB) is safe; fp8 mixed-case (~285 GB) also fits but leaves less headroom.
    
    --------------------
    </i>

---

### 19. Add CHI-Bench eval results — agent harness: OpenAI Agents SDK

- **Repo:** `deepseek-ai/DeepSeek-V4-Pro` · discussion #197
- **Author:** `hlnchen`
- **Date:** 2026-06-02 · status: open · 1 comments · language: en
- **URL:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/197
- **Type:** pull request · **Provenance:** unattributed
- **Artifacts: 2** — `conditioned_comparison`×1, `version_string`×1

    Adds CHI-Bench (actAVA) evaluation results for deepseek-ai/DeepSeek-V4-Pro.
    
    - Benchmark: actava/chi-bench (evaluation_framework: harbor)
    - Agent harness: OpenAI Agents SDK (best-performing harness for this model)
    - Protocol: 75 managed-care tasks x 3 trials; metric pass@1 (%)
    - Scores: Overall 14.2 | PA 10.7 | UM 28.0 | CM 4.0 ; reliability pass^3 9.3
    - Source: CHI-Bench paper, arXiv:2605.16679
    
    Submitted as community-provided results; close the PR if disputed.

---

### 20. IDEA: Bitnet 1.58 (a4.8) version in future variants would be so incredible!

- **Repo:** `deepseek-ai/DeepSeek-V4-Pro-DSpark` · discussion #6
- **Author:** `apiarium`
- **Date:** 2026-07-07 · status: open · 1 comments · language: en
- **URL:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-DSpark/discussions/6
- **Type:** usage question · **Provenance:** unattributed
- **Artifacts: 2** — `conditioned_comparison`×2, `version_string`×1

    Deepseek-V4-Pro-Dspark is incredible — thanks for releasing the weights. Would the team consider releasing a BitNet 1.58 (a4.8) variant in a future update? For anyone unfamiliar: ternary weights {-1, 0, +1} at 1.58 bits/param plus 4-bit activations means matmul becomes pure integer addition, no floating-point multipliers needed. Microsoft's bitnet.cpp already runs a 100B BitNet model on a single CPU at reading speed (5–7 tok/s) with 2–6× speedups on consumer hardware. The BitNet 1.58 paper (arXiv:2402.17764) showed perplexity parity with FP16 at 7B scale, and the a4.8 paper (arXiv:2411.04965) pushed activations down further with minimal quality loss. Training recipe is public at microsoft/unilm. A BitNet-native V4 or future versions would run offline on ordinary laptops and phones — no GPU needed — which is exactly the kind of accessibility a model this good deserves. Just putting it out there!

---

### 21. Add community evaluation results for SWE-Bench Multilingual

- **Repo:** `deepseek-ai/DeepSeek-V4-Pro` · discussion #213
- **Author:** `nielsr`
- **Date:** 2026-08-10 · status: open · 1 comments · language: en
- **URL:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions/213
- **Type:** pull request · **Provenance:** unattributed
- **Artifacts: 2** — `bench_number`×1, `version_string`×1

    This PR adds community-provided evaluation results for the following benchmarks:
    
    - **[SWE-BENCH_MULTILINGUAL](https://huggingface.co/datasets/SWE-bench/SWE-bench_Multilingual?eval_result=deepseek-ai/DeepSeek-V4-Pro&leaderboard_task_id=swe_bench_multilingual_%25_resolved)**
    
    These results were extracted from the model card. This is based on the new [evaluation results feature](https://huggingface.co/docs/hub/eval-results).
    
    *Note: This is an automated PR. Please review the evaluation results before merging.*

---

### 22. Anyone actually run DeepSeek-V4-Pro (1.7T) locally? Need real talk about costs

- **Repo:** `deepseek-ai/DeepSeek-V4-Pro-0813` · discussion #20
- **Author:** `mcherong`
- **Date:** 2026-08-28 · status: open · 1 comments · language: en
- **URL:** https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro-0813/discussions/20
- **Type:** usage question · **Provenance:** unattributed
- **Artifacts: 2** — `conditioned_comparison`×1, `version_string`×2

    Hey all,I'm looking into running DeepSeek-V4-Pro (1.7T params) and trying to figure out if it's even realistic.
    From what I can tell, minimum is like 8×H100s with INT4 quantization, which is already crazy expensive. Cloud API is cheap, renting a box is $10k+/mo, buying is six figures easy.

---

## Abstracts — the 15 papers carrying ≥2 artifacts

Abstracts as returned by the API. There is no comment text to include.

### 1. StateM: Reaching 95.3% Raw Accuracy, or a \$15 Frontier Run, on Terminal-Bench 2.1 via Harness Scaling

- **Paper:** `2608.15089` · https://huggingface.co/papers/2608.15089
- **Published:** 2026-08-14 · 445 upvotes · 2 comments (text not retrievable)
- **Authors (4):** Ziheng Qin, Yaxin Lu, Zhangyang Atlas Wang, Kai Wang
- **Artifacts (title+abstract): 2** — `bench_number`×2, `version_string`×1

    Long-horizon agents can fail even when their underlying models can solve the constituent steps. They may lose track of mutable state, fail to reactivate lessons from earlier executions, skip known procedures, or stop prematurely. We bet on harness scaling to improve the execution system around an agent without changing its model weights. We introduce StateM, an agent-native runtime that organizes execution around durable states, phase-local context, checked transitions, recoverable runbooks, and versioned procedural practices that agents and users can inspect together.
      On Terminal-Bench 2.1, StateM raises GPT-5.5 xhigh to 92.1\%, versus 83.1\% reference and GPT-5.6 Sol Ultra at 91.9\%. The runbook transfers unchanged to GPT-5.6. With GPT-5.6 Sol xhigh, StateM reaches 95.3\% raw accuracy across 445 trials and succeeds on all 89 tasks at least once. The frozen profile raises GPT-5.6 Luna from 76.7 to 85.4\%, above the 84.9\% Sol xhigh reference.
      Using the same runtime, runbook structure, and golden rules, less than \38 of adaptation raises DeepSeek-V4 Flash from 82.7 to 88.1% under standard timeouts and to 89.1% on an 88-task common core. Extending only the remaining latency-sensitive task matches the reported 88.8% GPT-5.6 Sol max result. Final-score API usage is about 15 versus \574.68 for the GPT reference; total DeepSeek expenditure is 52.22.
      On BusinessBench, family-specific runbooks built on development sets yield held-out gains of 0.55 macro and 1.34 micro points; two mechanism-matched families improve by 10.04 points. Concrete rules generalize when tasks share execution structure, while the control methodology applies broadly. StateM turns selected postmortem findings into persistent, executable preconditions and practices, making learned controls explicit and enforceable through stateful controls. Code at github.com/henryqin1997/statem.

---

### 2. Recursive Synthesis for Long-Horizon Terminal Tasks

- **Paper:** `2608.05466` · https://huggingface.co/papers/2608.05466
- **Published:** 2026-08-06 · 252 upvotes · 2 comments (text not retrievable)
- **Authors (11):** Zhongzhi Li, Yucheng Shi, Zongxia Li, Ruhan Wang, Anhao Li, Zixun Huang, Junyao Yang, Lei Ke …
- **Artifacts (title+abstract): 3** — `bench_number`×4, `conditioned_comparison`×1, `version_string`×1

    High-quality long-horizon training data for terminal agents is expensive to produce, often costing hundreds to thousands of dollars per task, because each task must keep the instruction, environment, reference solution, and verifier mutually consistent. Human authoring does not scale, and direct generation with large language models (LLMs) often breaks these dependencies. We present Recursive Synthetic Terminal Tasks (RST), a recursive verified synthesis framework for constructing long-horizon terminal-agent tasks at scale. Starting from verified seed tasks, RST extends the reference solution, realigns the verifier and instruction to the new workflow, validates the result in a fresh sandbox, and reuses accepted tasks as seeds for subsequent rounds. Across fifteen recursive rounds, RST produces 37,484 synthesized terminal-agent tasks at roughly $0.05 per task. Task difficulty increases substantially over rounds: the median reference solution grows from 67 to 374 lines, the median number of executed commands grows from 40 to 244, and DeepSeek-V4-Pro pass@4 drops from 90% at R1 to 2.5% at R15. To demonstrate training utility, we collect rejection-sampled Qwen3.5 trajectories on the synthesized tasks and use them for supervised fine-tuning. Fine-tuning on these trajectories improves Qwen3.5-27B and Qwen3.5-122B-A10B by up to 10 points on Terminal-Bench 2, Terminal-Bench Hard, and Long-Horizon Terminal Bench, while agentic PPO lifts Qwen3.5-27B to 49.44%, 32.00%, and 22.07% on the three benchmarks, corresponding to relative gains of 20.0%, 41.2%, and 21.9% over the base model. Moreover, after 15 rounds, the recursion shows no ceiling: synthesis yield and validation rates remain stable as difficulty keeps climbing, indicating that the process can continue well beyond the scale reported here.

---

### 3. Scaling the Horizon, Not the Parameters: Reaching Trillion-Parameter Performance with a 35B Agent

- **Paper:** `2606.30616` · https://huggingface.co/papers/2606.30616
- **Published:** 2026-06-28 · 105 upvotes · 4 comments (text not retrievable)
- **Authors (50):** Lei Bai, Zongsheng Cao, Yang Chen, Zhiyao Cui, Shangheng Du, Yue Fan, Shiyang Feng, Zijie Guo …
- **Artifacts (title+abstract): 2** — `bench_number`×2, `version_string`×1

    We introduce Agents-A1, a 35B Mixture-of-Experts Agentic Model that reaches trillion-parameter-level performance by scaling the agent horizon. We investigate agent-horizon scaling from two perspectives: scaling long-horizon trajectories and scaling heterogeneous agent abilities. To support this goal, we build a long-horizon knowledge-action infrastructure that connects external knowledge, actions, observations, and verifier outcomes, producing agentic trajectories with an average length of 45K tokens. Based on this, we train Agents-A1 with a three-stage recipe. First, we perform full-domain supervised fine-tuning to align the base model with broad agentic behaviors. Second, we train domain-level teacher models to capture specialized expertise in each domain. Third, we propose a multi-teacher domain-routed on-policy distillation with salient vocabulary alignment to improve knowledge transfer efficiency across different domains, unifying six heterogeneous domains into one deployable student model. Agents-A1 achieves strong and broad performance for long-horizon agent benchmarks. Compared with 1T-parameter model such as Kimi-K2.6 and DeepSeek-V4-pro, Agents-A1 achieves leading results on SEAL-0 (56.4), IFBench (80.6), HiPhO (46.4), FrontierScience-Olympiad (79.0), and MolBench-Bind (56.8), and remains highly competitive on SciCode (44.3), HLE (47.6) and BrowseComp (75.5). We hope this work provides the community with a practical path for scaling the horizon using a 35B agent that can reach or match the performance of 1T models on long-horizon tasks.

---

### 4. SLAI T-Rex: Full-Parameter Post-training of the DeepSeek-V4 Family on Ascend SuperPOD

- **Paper:** `2607.20145` · https://huggingface.co/papers/2607.20145
- **Published:** 2026-07-21 · 75 upvotes · 2 comments (text not retrievable)
- **Authors (65):** Dongfang Li, Xiaodong Luo, Ruoyu Sun, Xuhui Chen, Linyuan Qiu, Jian Meng, Zhengxuan Lu, Yiting Wang …
- **Artifacts (title+abstract): 2** — `conditioned_comparison`×1, `version_string`×4

    Full-parameter post-training of trillion-parameter-scale MoE models introduces substantial system-level challenges for large-scale distributed training, including severe memory pressure, non-overlapped communication overhead, and inefficient kernel execution. While most large-scale LLM training systems are built around GPU-based clusters, this report presents an end-to-end optimization practice on the Ascend NPU SuperPOD. Using the DeepSeek-V4 model family as the target workload, we develop a hierarchical optimization framework spanning model-level parallelism, computation-communication orchestration, and low-level kernel execution. The resulting system achieves 34.22% Model FLOPs Utilization (MFU) with a 2.93x improvement over the open-source baseline recipe while maintaining training stability. Building on this optimized infrastructure, we further establish a CPT and SFT workflow for complex Operations Research (OR) tasks. We refer to the integrated framework as SLAI T-Rex. Using DeepSeek-V4-Flash, we develop OR-oriented CPT and SFT data pipelines that combine collected domain resources with solver-verified synthetic optimization documents. The resulting dataset contains 10K high-quality SFT samples spanning four task categories and three problem representations. The specialized model achieves the highest average zero-shot Pass@1 score among the evaluated models, reaching 71.81% and outperforming GPT-5.4-Mini and the base DeepSeek-V4-Flash model by 3.98 and 11.27 percentage points, respectively. Overall, this work demonstrates a full-stack pathway from efficient trillion-parameter model post-training on Ascend infra to domain-specialized Flash models for solver-grounded mathematical modeling, advancing frontier-model systems for complex reasoning.

---

### 5. FlashMemory-DeepSeek-V4: Lightning Index Ultra-Long Context via Lookahead Sparse Attention

- **Paper:** `2606.09079` · https://huggingface.co/papers/2606.09079
- **Published:** 2026-06-07 · 68 upvotes · 5 comments (text not retrievable)
- **Authors (13):** Yan Wang, Qifan Zhang, Jiachen Yu, Tian Liang, Dongyang Ma, Xiang Hu, Zibo Lin, Chunyang Li …
- **Artifacts (title+abstract): 2** — `bench_number`×2, `version_string`×2

    Conventional LLMs keep the full KV cache loaded during decoding, causing a severe GPU memory bottleneck for ultra-long context serving. In this report, we propose Lookahead Sparse Attention (LSA), a novel inference paradigm powered by a Neural Memory Indexer built upon the DeepSeek-V4 architecture. Rather than passively attending to all historical tokens, LSA proactively predicts future context demands and preserves only the query-critical KV chunks in the GPU memory. Crucially, we instantiate this architecture via a backbone-free decoupled training strategy. By formulating the indexer as a standard dual-encoder architecture, we train it independently using standard retrieval training frameworks without ever loading the massive backbone model into GPU memory.
      We demonstrate that this "less is more" paradigm significantly maximizes serving efficiency while acting as an effective attention denoiser in tasks that rely on long-term global memory. Across primary long-context evaluation suites (e.g., LongBench-v2, LongMemEval, and RULER), FM-DS-V4 compresses the average physical KV cache footprint down to merely 13.5% of the full-context baseline, while consistently preserving or slightly elevating downstream accuracy (+0.6% absolute margin on average). Crucially, at extreme 500K scales, FlashMemory suppresses the physical KV cache overhead by over 90% without destabilizing the backbone's core reasoning capacities.

---

### 6. K-BrowseComp: A Web Browsing Agent Benchmark Grounded in Korean Contexts

- **Paper:** `2606.02404` · https://huggingface.co/papers/2606.02404
- **Published:** 2026-05-31 · 60 upvotes · 1 comments (text not retrievable)
- **Authors (15):** Nahyun Lee, Dongkeun Yoon, Guijin Son, Geewook Kim, Dayoon Ko, Jeonghun Park, Haneul Yoo, Jaewon Cho …
- **Artifacts (title+abstract): 2** — `bench_number`×1, `version_string`×1

    Frontier model evaluations are shifting from foundational capabilities (e.g., instruction following and reasoning) toward compositional, agentic ones, but Korean agentic benchmarks remain scarce. We introduce K-BrowseComp, a web-browsing agent benchmark grounded in Korean contexts, consisting of 400 problems. The 300-problem K-BrowseComp-Verified subset is manually constructed and validated by native Korean speakers. On this subset, frontier LLMs, including GPT-5.5, DeepSeek-V4-Pro, and GLM-5.1, reach only 30.00--45.67\%, a substantial drop from BrowseComp, while Korean LLMs released through Korea's Proprietary AI Foundation Model program obtain only 0.00--10.33\%. We further construct a 100-problem synthetic split using hard few-shot exemplars and failure-mode-targeted generation to exploit the asymmetry between solving and creating web browsing problems. On the adversarially filtered synthetic diagnostic split, the strongest model reaches only 26.00\%, and we report this split separately as a targeted stress test. We publicly release our data and code.

---

### 7. TREK: Distill to Explore, Reinforce to Refine

- **Paper:** `2607.05339` · https://huggingface.co/papers/2607.05339
- **Published:** 2026-07-05 · 9 upvotes · 2 comments (text not retrievable)
- **Authors (13):** Yuanda Xu, Zhengze Zhou, Kayhan Behdin, Jelena Markovic-Voronov, Hejian Sang, Xiaomin Li, Wenhui Zhu, Xinchen Du …
- **Artifacts (title+abstract): 2** — `bench_number`×4, `version_string`×1

    Group Relative Policy Optimization (GRPO) is effective when the current policy already samples useful reasoning trajectories, but it stalls on hard prompts whose correct solution modes lie outside the student's on-policy support. We propose TREK (Teacher-Routed Exploration via Forward KL), a simple staged procedure that uses distillation not for imitation but for exploration support expansion. A key advantage of TREK is its generality: because it only consumes verified output trajectories, it can use an external black-box teacher, a white-box teacher, or the same model given additional inference-time context, and it can efficiently identify which hard-prompt samples are most worth consolidating even when teacher internals are unavailable. TREK first identifies prompts where the unaided student has very low pass rate, queries a proposal source to produce verified candidate solutions, keeps the top-r proposals ranked by current student likelihood, applies a short forward-KL phase to pull those verified modes into the student's support, and then returns to standard on-policy GRPO refinement. On mathematical reasoning, TREK with DeepSeek-V4 proposals improves Qwen3 models across all tested scales on AIME 2024 and AIME 2025; for Qwen3-8B, it improves AIME 2025 from 36.9 to 40.3 and AIME 2024 from 47.9 to 51.1 (avg@16), while the self-context variant reaches 38.5 and 49.6 without an external teacher. On agentic tasks, TREK raises ALFWorld success rate from 75.8 to 82.8 and ScienceWorld success rate from 12.5 to 26.7; notably, on the hardest task types, TREK achieves high success rates early in training while unaided GRPO requires substantially more optimization steps to reach comparable levels.

---

### 8. AgentForesight: Online Auditing for Early Failure Prediction in Multi-Agent Systems

- **Paper:** `2605.08715` · https://huggingface.co/papers/2605.08715
- **Published:** 2026-05-08 · 8 upvotes · 1 comments (text not retrievable)
- **Authors (5):** Boxuan Zhang, Jianing Zhu, Zeru Shi, Dongfang Liu, Ruixiang Tang
- **Artifacts (title+abstract): 2** — `bench_number`×1, `version_string`×1

    LLM-based multi-agent systems are increasingly deployed on long-horizon tasks, but a single decisive error is often accepted by downstream agents and cascades into trajectory-level failure. Existing work frames this as post-hoc failure attribution, diagnosing the responsible agent and step after the trajectory has ended. However, this paradigm forfeits any opportunity to intervene while trajectory is still unfolding. In this work, we introduce AgentForesight, a framework that reframes this problem as online auditing: at each step of an unfolding trajectory, an auditor observes only the current prefix and must either continue the run or alarm at the earliest decisive error, without access to future steps. To this end, we curate AFTraj-2K, a corpus of agentic trajectories across Coding, Math, and Agentic domains, in which safe trajectories are retained under a strict curation pipeline and unsafe trajectories are annotated at the step of their decisive error via consensus among multiple LLM judges. Built on that, we develop AgentForesight-7B, a compact online auditor trained with a coarse-to-fine reinforcement learning recipe that first equips it with a risk-anticipation prior at the failure boundary on adjacent safe/unsafe prefix pairs, then sharpens this prior into precise step-level localization under a three-axis reward jointly targeting the what, where, and who of an audit verdict. Across AFTraj-2K and an external Who\&When benchmark, AgentForesight-7B outperforms leading proprietary models, including GPT-4.1 and DeepSeek-V4-Pro, achieving up to +19.9% performance gain and 3times lower step localization error, opening the loop from post-hoc failures detection to enabling deployment-time intervention. Project page: https://zbox1005.github.io/agent-foresight/

---

### 9. Hy-MT2: A Family of Fast, Efficient and Powerful Multilingual Translation Models in the Wild

- **Paper:** `2605.22064` · https://huggingface.co/papers/2605.22064
- **Published:** 2026-05-20 · 5 upvotes · 0 comments (text not retrievable)
- **Authors (53):** Mao Zheng, Zheng Li, Tao Chen, Bo Lv, Mingrui Sun, Mingyang Song, Jinlong Song, Hong Huang …
- **Artifacts (title+abstract): 2** — `bench_number`×1, `version_string`×1

    Hy-MT2 is a family of fast-thinking multilingual translation models designed for complex real-world scenarios. It includes three model sizes: 1.8B, 7B, and 30B-A3B (MoE), all of which support translation among 33 languages and effectively follow translation instructions in multiple languages. For on-device deployment, with AngelSlim 1.25-bit extreme quantization, the 1.8B model requires only 440 MB of storage and improves inference speed by 1.5x. Multi-dimensional evaluations show that Hy-MT2 delivers outstanding performance across general, real-world business, domain-specific, and instruction-following translation tasks. The 7B and 30B models outperform open-source models such as DeepSeek-V4-Pro and Kimi K2.6 in fast-thinking mode, while the lightweight 1.8B model also surpasses mainstream commercial APIs from providers such as Microsoft and Doubao overall.

---

### 10. Solar Open 2 Technical Report

- **Paper:** `2607.20062` · https://huggingface.co/papers/2607.20062
- **Published:** 2026-07-23 · 5 upvotes · 0 comments (text not retrievable)
- **Authors (53):** Sungrae Park, Sanghoon Kim, Gyoungjin Gim, Jungho Cho, Hyunwoong Ko, Minbyul Jeong, Minjeong Kim, Keunwoo Choi …
- **Artifacts (title+abstract): 2** — `bench_number`×2, `version_string`×2

    We present Solar Open 2, a 250B-A15B Mixture-of-Experts language model built for long-horizon agentic tasks, scaled up from Solar Open 1 (Solar Open 100B). To hold entire agent trajectories in a single context, Solar Open 2 reaches a 1M-token window through a hybrid attention stack that interleaves one softmax layer among every three linear-attention layers, using no positional encoding and a gated delta rule extended to negative eigenvalues. To train at this scale under a fixed compute budget, we make training efficient in two ways: a stronger starting point, and higher-value data. For the starting point, we initialize Solar Open 2 from Solar Open 1, transferring the 5.69B-parameter shared skeleton that survives the architectural change and learning everything else through full pre-training. For the data, we curate for value per token: quality- and rarity-aware data curation and mixture-ratio optimization refine a 20T pool into a 10T mixture that, at equal token budget, outperforms the Solar Open 1 recipe. To build its agent skills, we train twelve domain specialists across purpose-built scenarios, then consolidate them into a single model by Multi-teacher On-Policy Distillation (MOPD). Against comparably sized open-weight models on English benchmarks, Solar Open 2 leads on MMLU-Pro, LiveCodeBench, and the APEX-Agents agentic suite, and stays competitive with the strongest (DeepSeek-V4-Flash and MiMo-V2.5) elsewhere. On Korean benchmarks, Solar Open 2 records the highest average of any model compared, including fast-tier closed APIs, and on Ko-GDPval, an in-house Korean officework-agent benchmark, it is competitive with DeepSeek-V4-Pro (1.6T) at less than a sixth of its size.

---

### 11. FlashBoot: Sub-Second Weight Loading for Large Models at Rack Scale

- **Paper:** `2608.08482` · https://huggingface.co/papers/2608.08482
- **Published:** 2026-08-08 · 3 upvotes · 0 comments (text not retrievable)
- **Authors (6):** Issac Zhu, Hscos Zhang, Keith Jiang, Jack Li, Hugh Yin, Jason Zhao
- **Artifacts (title+abstract): 2** — `conditioned_comparison`×1, `version_string`×2

    Flagship Mixture-of-Experts (MoE) models are growing fast along two axes at once: total parameter count and the number of experts. In elastic deployment scenarios, many GPUs across many nodes must become serving-ready quickly, and this growth makes weight loading a noticeable part of the latency budget. Even on NVIDIA's GB300 NVL72, today's state-of-the-art loaders leave most of that bandwidth unused. The losses are structural: (C1) weight memory is fragmented into tens of thousands of per-tensor objects, so transfers run far below link bandwidth; (C2) cross-node replication is gated by NCCL communicator setup, which costs 10-110 s before a single weight byte moves; and (C3) the existing cross-node GPU->GPU clone path is serial and scales poorly to concurrent multi-node bring-up. We present FlashBoot, a hardware-friendly, framework-workflow co-designed weight-loading subsystem built on SGLang. At its core is FabricArena, a contiguous, exportable and inter-node addressable tensor memory layout. On top of it, FlashLoad loads from CPU as a single bulk, zero-copy transfer, and FlashClone replicates a resident model from a remote GPU via a remote-mapping mechanism that removes NCCL setup. In experiments on NVL72 with DeepSeek-V4-Pro and DeepSeek-V4-Flash, FlashClone maps remote weight memory in ~10 ms (versus 10-110 s for NCCL) and sustains >=700 GB/s per clone. Against the state of the art, FlashBoot accelerates single-node weight loading by up to 50x (from 20.1 s to 0.4 s) and concurrent rack-level weight loading by >270x (from 87 s to 0.32 s). Our code will be made publicly available.

---

### 12. EvoClawBench: Can Agents Learn Reusable Skills from Their Own Runs?

- **Paper:** `2607.09711` · https://huggingface.co/papers/2607.09711
- **Published:** 2026-06-22 · 1 upvotes · 0 comments (text not retrievable)
- **Authors (8):** Zhiyuan Peng, Xin Yin, Chenhao Ying, Zhe Cui, Zixiang Ding, Zhenhua Liu, Jiang Wu, Yuan Luo
- **Artifacts (title+abstract): 2** — `bench_number`×1, `version_string`×1

    Existing agent benchmarks primarily test task completion, tool use, or skill utility, but do not isolate whether a runtime can convert evidence from its own runs into reusable skills that improve fresh executions after authoring overhead. We introduce EvoClawBench, a benchmark for this closed-loop skill-learning question on repeated, fixture-backed tasks. EvoClawBench compares direct execution without skills, PreSkill authoring before execution, and PostSkill summarization from first-run evidence followed by a fresh second execution. The suite contains 100 tasks and 502 sub-problems across coding, data, office, security, operations, and domain-document workflows, with support for multiple agent runtimes. Experiments with OpenClaw and nanobot under local execution show that direct baseline performance is strongly runtime-dependent: OpenClaw remains below 20% across models, while nanobot ranges from 56.45% to 96.13%. Self-authored skills have mixed effects. nanobot GPT-5.4 stays above 96% in all modes and MiniMax-M2.7 improves from 90.97% to 94.50% under PostSkill, but nanobot DeepSeek-V4-Pro drops from 77.77% to 4.80% with PreSkill and 0.99% with PostSkill. OpenClaw shows similarly non-monotonic behavior, with some skill runs near baseline and others collapsing. These results indicate that learning reusable skills from an agent's own runs is selective and cost-sensitive, rather than an automatic benefit of adding skill authoring to an agent loop.

---

### 13. SETA: Scaling Environments for Terminal Agents

- **Paper:** `2607.10891` · https://huggingface.co/papers/2607.10891
- **Published:** 2026-07-11 · 0 upvotes · 0 comments (text not retrievable)
- **Authors (22):** Qijia Shen, Zhiqi Huang, Vamsidhar Kamanuru, Aznaur Aliev, Jay Rainton, Ahmed Awelkair, Zhichen Zeng, Jiajun Li …
- **Artifacts (title+abstract): 3** — `bench_number`×2, `conditioned_comparison`×2, `version_string`×1

    Large language models (LLMs) are rapidly shifting toward agents that solve tasks through diverse interfaces, including web and graphical user interfaces (GUIs). Among these, the terminal command line provides a text-based, general-purpose interface, covering tasks from system operations to data science and machine learning. However, scaling terminal-agent training remains challenging, as it requires diverse and coherent task instructions, executable environments, and reliable verification, while lacking naturally grounded supervision data. In this work, we propose SETA, a scalable framework for generating verifiable terminal environments for reinforcement learning (RL). The framework consists of two pipelines sharing a unified verification mechanism: SETA-Synth converts diverse sources into standardized RL environments, and SETA-Evol further expands from existing environments with adaptive control of difficulty and diversity. Together, we construct and release SETA-Env, the largest open-source verifiable terminal RL dataset to date, containing over 4,500 environments. We evaluate our dataset by training Qwen3-8B with GRPO on SETA-Env, achieving 12% pass rate on Terminal-Bench 2.0, the best reported result for an RL-trained model at the 8B scale. We further observe gains on DeepSeek-V4-Flash under the same terminal agent harness, with pass@1 on Terminal-Bench 2.0 improving from 40% to 43% and pass@5 improving from 54% to 58%. These results demonstrate that SETA- Env provides high-quality training environments for terminal agents and serves as a valuable resource for advancing research on terminal-based agent learning.

---

### 14. Tied Trit-Planes: Constraining PTQTP to a Uniform Nine-Level Quantizer, with a Persistent Folded Format for Disk-Streamed Mixture-of-Experts Serving

- **Paper:** `2608.08910` · https://huggingface.co/papers/2608.08910
- **Published:** 2026-08-08 · 0 upvotes · 0 comments (text not retrievable)
- **Authors (1):** Matteo Grella
- **Artifacts (title+abstract): 3** — `bench_number`×1, `conditioned_comparison`×3, `version_string`×1

    PTQTP decomposes LLM weight matrices into two ternary (trit) planes with two free per-group scales. Tying the scales to a fixed ratio of three collapses the decomposition into a single uniform nine-level quantizer, a known balanced-ternary identity. To our knowledge, at the time of writing, this work is the first to impose that identity as a constraint inside PTQTP's solver. The two trit planes then fold losslessly into one 4-bit code plane that we make the persistent serving representation: disk bytes, expert-cache bytes, and kernel input are the same 4.0625-bits/weight blocks, consumed in one integer dot pass. For this conjunction (ratio-3 nine-level code, CPU-SIMD kernels, SSD expert streaming, identical persistent bytes) we likewise found no precedent. We apply this to the routed experts of DeepSeek-V4-Flash-0731, a 284B-A13B mixture-of-experts model, quantizing in one shot from the released MXFP4 expert weights and streaming experts from SSD on a 64 GB laptop. Against a 4.5-bit Q4_K baseline, measured one process per fixture with an expert-lossless anchor arm as reference control, the tied model matches the official serving API on 5/5 fixtures at step 0 (Q4_K: 4/5) and 12/14 captured continuation steps (11/14), scores 86 vs. 84 on a 100-item MMLU subset, decodes 6.7% faster in decode phase, and ships 9% smaller files: no detected fidelity difference at these small evaluation sizes, and every fixture-level difference between the arms traces to a single measured near-tie cell. The tied fit nevertheless shows higher weight-reconstruction error and worse perplexity, a measured dissociation between proxy metrics and reference fidelity. A cumulative trunk-ternarization ladder and bitwise-pinned aarch64/x86-64 kernels complete the report. All code, formats, and evaluation artifacts are open source in the fucina inference stack.

---

### 15. Coupling Planning with Episodic Memory in LLM Agents for Software Issue Resolution

- **Paper:** `2608.06811` · https://huggingface.co/papers/2608.06811
- **Published:** 2026-08-06 · 0 upvotes · 0 comments (text not retrievable)
- **Authors (3):** Jiahao Zhang, Yifan Zhang, Yu Huang
- **Artifacts (title+abstract): 2** — `bench_number`×1, `version_string`×1

    Resolving a real software issue with a large language model (LLM) agent is a long repair episode, often tens to hundreds of steps spanning exploration, hypothesis, implementation, and verification. Success depends on both the base model's local reasoning and the agent's ability to maintain an evolving plan and remember observations across phases. Existing repository-level agents typically strengthen planning or memory in isolation, leaving long trajectories vulnerable to stale evidence, repeated failed edits, and verification inferred from the agent's own claims instead of execution evidence. We present PMCoder, an issue-resolution agent that couples a hierarchical phase planner with episodic memory. The coupling is bidirectional: the current plan phase conditions memory retrieval, while memory-derived trajectory statistics inform stuck detection and replanning. When available, issue-reproduction verdicts ground verification progress in execution evidence rather than self-reported completion. On SWE-bench Verified, PMCoder resolves an average of 25 more cases (+5.0pp) than a harness-matched baseline, with gains persisting even where the reproduction gate never fires. Further Verified-500 evaluations show the same positive direction across Claude Haiku 4.5, DeepSeek-V4-Flash, and an OpenHands port, with at least 14 additional resolved cases (+2.8pp). Separately, evaluation on TerminalWorld's official sample suggests that the plan-memory substrate transfers beyond issue reports. Ablation and trajectory analyses show where the gains come from: coupling planning and memory outperforms either component alone and reduces repeated failed actions, empty-patch exits, and context-window exhaustion.

---
