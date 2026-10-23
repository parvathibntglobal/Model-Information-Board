# Proposal: "Can I run it?" - a local LLM VRAM calculator under Tools

**Proposed 2026-10-23 by anooj, branch `feat/can-i-run-it`. Revised the same
day after Parvathi's review on #559** (each change is marked *Revised*). Three
new `contract/` files, one line in `indexing.yaml`, a migration, and a proposed
amendment to a terms ruling, so it needs a second reviewer before it merges.

## What it is

A tool page under Tools (not the home page) at `/local-llm-vram-calculator`.
A reader picks their hardware - "RTX 3050 6GB", "Mac with 16 GB unified
memory", "2 x RTX 4090" - a quantization (Q4_K_M or Q8_0), a context length and
a KV-cache type, and sees every listed open-weight model in a group: **fits**,
**tight**, **can't tell**, **won't fit**. Each row shows the model's **measured
file size**, links the repo it was measured in, links its model page where we
have one, and shows its API price where OpenRouter lists it - so a model that
does not fit still has an answer.

## The display rule (rule 3)

*Revised.* The first draft showed a computed total ("≈ 6.58 GiB estimate") and
a KV-cache figure. Rule 3 allows neither without an amendment, and the review
said so. Now:

> **The only figure a row shows is the measured size of the exact GGUF file**,
> in GiB, with the repo and commit it came from linked. The group is a word.
> What the group adds to the file is said in words - "plus the memory an 8K
> context needs, and the runtime" - and no total, cache size, overhead or Mac
> share is shown as a number. No amendment to rule 3 is needed.

Ordering within a group is by file size, largest first - the figure on the row,
so the order can be checked against it.

**Units: GiB throughout.** A GPU maker's "8 GB" is 8 GiB; Hugging Face prints
decimal GB (Qwen3 8B Q4_K_M is "5.03 GB" there and 4.68 GiB here). The page says
which it uses.

## The data, and where each part comes from

| Needed | Source | Status |
|---|---|---|
| Which models | `contract/local_models.yaml` - 50 reviewed entries | seeded, below |
| File size per quant | Hugging Face API, `api/models/<gguf repo>?blobs=true` | measured weekly |
| Layers, KV heads, head size, max context, key-projection shape | the GGUF file's own header and tensor list, ranged read | measured weekly |
| Hardware memory | `contract/local_hardware.yaml` - 54 devices | 48 checked, 6 AMD not |
| Constants | `contract/local_inference.yaml` | below |
| API price | our OpenRouter registry, by exact id | already polled |

**No Hugging Face token.** Gated vendor repos (Llama, Gemma) would need one and a
licence accepted per model on the team's account. The GGUF repos are not gated,
and their file header carries the same architecture fields `config.json` would.
So one file is the source of both the size shown and the arithmetic behind it.

### How the 50 models were chosen

The families asked for (Llama, Qwen, Gemma, Phi, Mistral) plus DeepSeek distills,
gpt-oss, GLM, Nemotron and SmolLM, picked from the most-downloaded GGUF repos of
unsloth, ggml-org, bartowski and lmstudio-community (60 each, Hugging Face API,
`sort=downloads`, 2026-10-23). Vendor models only: no community fine-tunes, no
"abliterated"/"uncensored" variants, and **text weights only** (*Revised*:
several are multimodal - Gemma 3 4B and up, Gemma 4, Mistral Small 3.2,
Ministral 3, Llama 4 Scout - and only their text files are listed; a vision
projector is not counted). 52 tried, 50 kept (MiniMax H3's repo is not one
model's files; GLM 5.3 Flash is a 318 GiB server model).

28 of the 50 link to an OpenRouter id, by an **exact join**: the GGUF repo's
`base_model` equals the OpenRouter entry's `hugging_face_id`. No name matching.

**Each entry lists its exact files.** The seed script's first, looser match took
Qwen3.8 Flash Next's 2.6 GiB speculative-decoding helper (`mtp-...`) for a 177B
model, and a combined vision model for MiniMax H3. So the collector measures the
files the YAML names and searches for nothing; a file that disappears is
recorded missing, never replaced by a look-alike (rule 12).

## The arithmetic (judge/local_models.py and web/src/vram/estimate.js)

    weights   = measured file size (sum of parts)
    context   = bytes per element x (full-attention elements x tokens
                + windowed elements x min(tokens, window))
                + the fixed recurrent state of state-space layers
    need      = weights + context + runtime_overhead_gib x cards
    budget    = memory_gib x cards                      (a graphics card)
              = memory_gib x the Mac's share by size    (a Mac)
    group     = won't fit   if weights + runtime alone exceed the budget
                can't tell  if the context is unknown (rule 6, *Revised*)
                fits        if need <= fits_at_most x budget
                tight       if need <= budget
                won't fit   otherwise

- **MoE** needs nothing special: the file holds every expert, and its size is
  what loads.
- **An unknown context is never counted as zero** (*Revised*, rule 6). The first
  draft grouped such a row on weights + overhead, which could say "fits". Now
  it is "can't tell" - unless the file and runtime alone already exceed the
  budget, which is "won't fit" whatever the context is.
- **State-space layers** (*Revised*). Qwen 3.5/3.6/3.8 and Nemotron-H keep a
  fixed recurrent state, in f32: (conv_kernel - 1) x (inner + 2 x groups x
  state) + state x inner elements per layer - 156,893,184 bytes (about 150 MiB)
  for Qwen3.6 27B's 48 such layers, the figure the review found. It is added.
  Nemotron-H's layers are told apart by llama.cpp's own test: no KV heads AND no
  feed-forward width is a state-space layer; no KV heads with a feed-forward
  width is a plain feed-forward layer.

### What the header settles, measured over the 50 files (2026-10-23)

| Header states | Models | Context computed |
|---|---|---|
| one KV-head count, full attention | Llama 3.x, Qwen2.5/3, Phi, Mistral, SmolLM3, DeepSeek distills | exactly |
| a window of 0, or at or past the model's maximum context | Phi-4 reasoning plus (0), Phi-4 mini (262144) | exactly, as full attention |
| `full_attention_interval` (every Nth layer keeps a cache; the rest are state-space) | Qwen 3.5 / 3.6 / 3.8 (8) | exactly, plus their state |
| per-layer KV heads and feed-forward widths | Nemotron-H (2) | exactly, plus their state |
| per-layer KV heads + `sliding_window_pattern`, and separate windowed head sizes | Gemma 4 (5) | exactly - see below |
| a sliding window but no pattern | Gemma 3 (4), gpt-oss (2) | upper bound |
| latent attention (`kv_lora_rank`) | GLM 4.7 Flash | upper bound |
| attention llama.cpp sets in code (`attention_not_in_header`) | Llama 4 Scout - chunked attention on 3 of every 4 layers | upper bound (*Revised*: was "exact") |
| an indexer and per-layer compression (`unmodelled_attention_keys`) | Qwen3.8 Flash Next | **can't tell** (*Revised*: was "exact"; not even a bound) |

**41 exact, 8 upper bound, 1 can't tell** (*Revised* from 43 / 7 / 0;
`tests/test_local_models.py` recomputes it). An upper bound can only make a
model look bigger; a guess could make it look smaller.

**Gemma 4, spelled out** (*Revised*: the review asked how each field is used).
A windowed layer (`sliding_window_pattern` true) caches its last `sliding_window`
tokens with `key_length_swa` / `value_length_swa`; a global layer caches every
token with `key_length` / `value_length` and its own KV-head count from the
per-layer array. E2B and E4B state `shared_kv_layers` (20 and 18): their last N
layers reuse an earlier layer's cache and add none, which is how llama.cpp
allocates them.

### Head size, and the check against the file itself

When the header omits `key_length`, llama.cpp allocates embedding length / head
count, so that is what the file costs when loaded. *Revised*: it is now
**checked against the file's own key projection** - the tensor list, which sits
between the metadata and the tensor data, gives layer 0's (or the first
attention layer's) `attn_k` shape: KV heads x the real head size. A disagreement
makes the row "can't tell", with the two numbers named (rule 12).

The review suggested comparing with `rope.dimension_count` instead. Measured, it
fails both ways: unsloth's broken Mistral Nemo states `rope.dimension_count:
160`, which *agrees* with its wrong 5120 / 32, and Phi-4 mini legitimately
rotates 96 of its 128 dimensions. The key projection catches the first (1024 =
8 x 128, not 160) and passes the second (fused q/k/v 5120 = 24 x 128 + 2 x 8 x
128). `docs/measurements/local-model-tensor-check-2026-10-23.*`.

**Mistral Nemo uses bartowski's file**, which states `key_length` 128, names its
base model, and matches its key projection. *Revised*: it is NOT "the same size
to the byte" as unsloth's, as the first draft said - the two agree to two
decimals in GiB (6.96 / 12.13) and differ by 3,680 bytes (Q4_K_M 7,477,208,192
against 7,477,204,512). Measured and committed, as the review asked.

**A file whose header is wrong is replaced in the YAML, never corrected in code.**

## The constants (contract/local_inference.yaml)

- **The Mac's GPU share, by memory size** (*Revised*: was one 0.75). Apple
  publishes no figure. Each row says what it rests on:

  | Memory | Share | Evidence |
  |---|---|---|
  | under 64 GiB | 0.66 | an 8 GB M1 reports `recommendedMaxWorkingSetSize = 5726.63 MB`, two thirds of 8 GiB (llama.cpp issue #5207). No report found for 16-48 GB; they take this, the lower share |
  | 64 GiB and up | 0.75 | reported as about three quarters (a 64 GB Mac allows about 48 GB); not published by Apple |

  llama.cpp prints the real figure at startup; a measurement on a given size
  replaces its row.
- **`runtime_overhead_gib: 1.0`**, a labelled estimate, never shown. It also
  stands in for the VRAM a desktop's display and OS hold, which is unmeasured
  (*Revised*: the hardware file no longer claims the whole memory is free).
- **`kv_cache_bytes`**: f16 2.0, q8_0 1.0625 (34 bytes per 32). Confirmed in review.

## The hardware (contract/local_hardware.yaml)

*Revised.* Each device cites the page its figure is checked on, not one page per
vendor. 54 devices: the review's 41 spot-checks matched; the rest were checked by
fetching each page (Intel B580 and A770, T4, L4, A100 40/80, H100, the RTX 3050
Laptop 4GB, and the Mac Studio's 256 and 512 GB, all added or re-cited). Added:
RTX 4070 Ti (12 GB), Macs with 256 and 512 GB. **The six AMD cards are not yet
checked**: amd.com timed out on every product page, for us and for the reviewer,
and the file says so.

## The terms ruling

*Revised.* The review counted three gaps against `huggingface-api-terms`. One is
already closed on `main`: the ruling was amended 2026-10-19 to
`public-derived-publication`, so external publication is within it. The other
two are written into the ruling as a **proposed** amendment (`contract/sources.yaml`,
marked not in force until reviewed):

- the second access path - ranged reads on `/resolve/<commit>/<file>.gguf`,
  listed files only, header and tensor list only, discarded overshoot, no whole
  file, a range-ignoring response refused;
- what is published - a size, a repo name and a link, no text from any file;
- **robots.txt and the Terms of Service, read 2026-10-23** and quoted: robots
  allows `/`; the Terms (effective 2022-09-15) have no clause on scraping or
  automated access, and their "may not reproduce, republish" clause covers
  Hugging Face's own materials, not users' uploaded Content.

`recorded_evidence` is left at `false` on purpose: the terms check compares it
with the source's own `terms_evidence`, and flipping one side would refuse the
existing Hugging Face harvester in the scheduled fetch. Both change together, in
review.

## What is built (same branch)

- `collect/local_models/`: the header reader (metadata and tensor list, never
  tensor data) and a weekly poller - its own package, since `collect/registry/`
  may not import adapters. Stores the raw API responses, upserts one row per
  model and quant.
- Table `local_model_file` (`contract/migrations/20261023T1000_local_model_file.sql`),
  declared in `column_states.yaml`.
- `GET /local-models` (public read): files, sizes, each model's memory shape,
  hardware with each Mac's share, constants, API price. No score field, no total.
- The page, grouping in the browser so changing hardware is instant.
- `.github/workflows/local-models-poll.yml`, weekly.

## Measurements behind this proposal (2026-10-23)

- `docs/measurements/local-models-seed-2026-10-23.py` / `.out.txt`: the seed
  resolution - each model's GGUF repo, exact files and measured sizes. Its output
  still shows unsloth's Mistral Nemo; `local_models.yaml` uses bartowski's.
- `docs/measurements/local-model-headers-2026-10-23.py` / `.out.txt` / `.json`:
  every listed model's header read in 4 MiB steps - fields, where the metadata
  ends, bytes transferred. The Nemo row there is unsloth's file, the one rejected.
- `docs/measurements/local-model-tensor-check-2026-10-23.py` / `.out.txt`: the
  key-projection shapes of both Nemo files, Phi-4 mini, Llama 3.1 8B and Gemma 4
  12B, and both Nemo files' exact byte sizes.

## Second review (#559, 2026-10-23), and what changed

- **A bound can prove "fits", never "won't fit"** (rule 6). An upper-bound
  context that does not fit now gives "can't tell", with the row saying the
  model's real need is smaller. Before, Gemma 3 27B on one 24 GiB card at 32K
  read "won't fit" although llama.cpp fits it.
- **A failed poll keeps last week's row.** A non-200 from the Hub API, a
  dropped connection, or a header read that fails for a reason that is not about
  the file (rate limit, server error, a 206 at the wrong offset, a step longer
  than asked) is TRANSIENT: nothing about the files is written, an existing row
  is kept as it was, and the run counts it (`kept_after_failure`). Only a real
  absence from a successful listing writes `missing_files`.
- **The reader cannot be stopped by one file.** Every malformed header is
  `NotGGUF` (a Unicode digit in a tensor name, an unknown type); non-finite
  floats are dropped before jsonb; each ranged step must start where it was
  asked and return no more than asked; the number of steps is bounded.
- **The terms check: recorded, not enforced** (anooj's decision). The ruling's
  `access_path` lists `gguf-header-range` and says why the poller is not put
  through `assert_terms_reviewed`: terms findings inform and never gate what is
  built.
- **Rule 9.** The API no longer sends `files`, `original`, `architecture` or a
  per-quant date; `files` is write-only in `column_states.yaml`, and
  `missing_files` is read - the not-shown notice says a file is gone from its
  repository rather than "not measured".
- **Windowed layers hold window + 512** (`window_extra_tokens`, llama.cpp's
  default n_ubatch), so "exact" stays exact for Gemma 4. Cell padding is not
  counted and says so.
- **The count runs on the polled headers**
  (`docs/measurements/local-model-headers-polled-2026-10-23.json`): the listed
  bartowski Nemo, with the tensor list, so the head-size check runs on the 49
  files that have a key projection. Still 41 / 8 / 1.
- **Accessibility:** the choice rows are radio groups with arrow keys and one
  tab stop; the group counts are announced (`aria-live`); links that open a new
  tab say so; the not-shown notice uses display names.
