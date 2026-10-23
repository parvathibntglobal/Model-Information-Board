# Proposal: "Can I run it?" - a local LLM VRAM calculator under Tools

**Proposed 2026-10-23 by anooj, branch `feat/can-i-run-it`.** Three new
`contract/` files and one terms-ruling update, so this needs a second reviewer
before the code that reads them merges.

## What it is

A tool page under Tools (not the home page) at `/local-llm-vram-calculator`.
A reader picks their hardware - "RTX 3050 6GB", "Mac with 16 GB unified
memory", "2 x RTX 4090" - a quantization (Q4_K_M or Q8_0) and a context length,
and sees every open-weight model in three groups: **fits**, **tight**,
**won't fit**. Each row shows the model's **measured file size**, links to its
model page where we have one, and shows its API price where OpenRouter lists it,
so a model that does not fit still has an answer.

## The display rule (rule 3) - the decision this asks for

Rule 3 says every figure on a page is counted or measured. A VRAM total is
neither: it adds a KV cache (computed) and a runtime overhead (estimated) to the
weights. So:

> **The figure shown is the measured size of the exact GGUF file** - read from
> Hugging Face, in GiB, with the repo it came from named and linked. The total
> that decides the group is labelled **"estimate"**, and the page says in words
> what it adds: "file size, plus the memory the context needs, plus about 1 GB
> for the runtime". The group is a word, never a percentage.

Decided by anooj 2026-10-23. Proposed here because it is the first
page to place an estimate beside a measurement, and the wording that keeps the
two apart belongs in review, not in a component.

## The data, and where each part comes from

| Needed | Source | Status |
|---|---|---|
| Which models | `contract/local_models.yaml` - 50 reviewed entries | seeded, below |
| File size per quant | Hugging Face API, `api/models/<gguf repo>?blobs=true` | measured weekly |
| Layers, KV heads, head size, max context | the GGUF file's own header, ranged read | measured weekly |
| Hardware memory | `contract/local_hardware.yaml` - 51 devices | needs checking |
| Constants (cache bytes, overhead, Mac share, bands) | `contract/local_inference.yaml` | open questions |
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
"abliterated"/"uncensored" variants, text LLMs only. 52 tried, 50 kept (MiniMax H3's
repo is not one model's files; GLM 5.3 Flash is a 318 GiB server model).

28 of the 50 link to an OpenRouter id, by an **exact join**: the GGUF repo's
`base_model` equals the OpenRouter entry's `hugging_face_id`. No name matching.

**Each entry lists its exact files.** The seed script's first, looser match took
Qwen3.8 Flash Next's 2.6 GiB speculative-decoding helper (`mtp-...`) for a 177B
model, and a combined vision model for MiniMax H3. So the collector measures the
files the YAML names and searches for nothing; a file that disappears is
recorded missing, never replaced by a look-alike (rule 12).

## The arithmetic (judge/, computed where the list is built)

    weights   = measured file size (sum of parts)
    kv cache  = 2 x layers x kv_heads x head_dim x bytes(cache type) x context
    total     = weights + kv cache + runtime_overhead_gib x cards
    budget    = memory_gib x cards            (discrete)
              = memory_gib x apple_gpu_share  (unified)
    group     = fits if total <= fits_at_most x budget; tight if <= budget;
                won't fit otherwise

- **MoE** needs nothing special: the file holds every expert, and its size is
  what loads.
- **What the header states is used exactly; what it does not is an upper bound,
  labelled.** Measured over all 50 headers, 2026-10-23 (every header read; the
  largest metadata section 15.1 MiB, Gemma 4; no read past 16 MiB):

  | Header states | Models | Cache computed |
  |---|---|---|
  | one KV-head count, full attention | Llama, Qwen2.5/3, Phi, Mistral, SmolLM3, DeepSeek distills | exactly |
  | `full_attention_interval` (every Nth layer keeps a cache) | Qwen 3.5 / 3.6 / 3.8 (9) | exactly |
  | per-layer KV heads, 0 on state-space layers | Nemotron-H (2) | exactly |
  | per-layer KV heads + `sliding_window_pattern` | Gemma 4 (5) | exactly |
  | a sliding window but no pattern | Gemma 3 (4), gpt-oss (2) | upper bound |
  | latent attention (`kv_lora_rank`) | GLM 4.7 Flash | upper bound |

  An upper bound can only make a model look bigger; a guess could make it look
  smaller.
- **Head size, when the header omits `key_length`, is what llama.cpp itself
  allocates for that file: embedding length / head count.** That is the
  runtime's rule, not ours - it is what the file will cost when loaded. It also
  exposed a bad file: unsloth's Mistral Nemo states head size 160 where Nemo's
  is 128, an early conversion. The list uses bartowski's, which states 128 and
  is the same size to the byte. **A file whose header is wrong is replaced in
  the YAML, never corrected in code.**
- **A missing header field is "unknown", never 0** (rule 6): the row shows the
  file size and "context memory unknown", and is grouped on weights + overhead
  with that said.

## Open questions for review

1. **`apple_gpu_share: 0.75`.** macOS caps the GPU's share of unified memory and
   Apple publishes no figure. 0.75 is the commonly quoted cap on larger
   machines; smaller ones are reported lower. Keep 0.75, or take a lower figure
   for a conservative "fits"?
2. **`runtime_overhead_gib: 1.0`** is an estimate. Fine as a labelled estimate,
   or measure llama.cpp on one machine first?
3. **`local_hardware.yaml` is written from product names and not yet checked
   entry by entry** against the vendor pages it cites. A wrong figure there is a
   wrong "fits" on every model, so the review is the check.
4. **The terms ruling.** `contract/sources.yaml` `huggingface-api-terms` covers the
   API and says "re-review required before downloading weights". The header read
   is a ranged request on a weights file that stops at the first 4 MiB step past
   the metadata (at most 32 MiB). Proposed addition to that ruling, below.

### Proposed addition to `huggingface-api-terms`

> GGUF HEADER READS (2026-10-23, the local VRAM tool). Ranged GET requests on
> `huggingface.co/<repo>/resolve/main/<file>.gguf` for repos listed in
> contract/local_models.yaml, reading only the file's header - the key/value
> metadata - in steps of `header_read.chunk_bytes`, and stopping at the first
> step that completes it, or at `max_header_bytes`. The last step can run past
> the metadata by up to one step; those bytes are discarded unread. Tensors are
> never parsed or stored, and no file is downloaded whole. Size and file listing
> come from the documented API. robots.txt for huggingface.co allows `/`
> (checked 2026-10-23).

## What gets built after review

- `collect/local_models/`: a weekly poller (its own module: `collect/registry/`
  may not import adapters). Stores raw API responses in the raw store, upserts
  one row per model and quant.
- Table `local_model_file` (migration below), declared in `column_states.yaml`.
- `GET /local-models` (public read): files, sizes, header fields, measured-at,
  and the OpenRouter price joined by id. No score field.
- The page, with the arithmetic in the browser so changing hardware is instant.
- `.github/workflows/local-models-poll.yml`, weekly.

```sql
CREATE TABLE local_model_file (
  model_id         text NOT NULL,          -- contract/local_models.yaml id
  quant            text NOT NULL,          -- Q4_K_M | Q8_0
  gguf_repo        text NOT NULL,
  files            text[] NOT NULL,        -- as listed in the YAML
  bytes            bigint,                 -- sum of the files; NULL = one was missing
  missing_files    text[] NOT NULL DEFAULT '{}',
  header           jsonb,                  -- the fields read; NULL = header unread
  header_note      text,                   -- why unread, or what is unmodelled
  repo_sha         text,                   -- the repo commit the sizes were read at
  raw_ref          text,                   -- raw store ref of the API response
  measured_at      timestamptz NOT NULL,
  pipeline_version text NOT NULL,
  PRIMARY KEY (model_id, quant)
);
```

## Measurements behind this proposal (2026-10-23)

- `docs/measurements/local-models-seed-2026-10-23.py` / `.out.txt`: the seed
  resolution - each model's GGUF repo, exact files and measured sizes. Its output
  still shows unsloth's Mistral Nemo; the header check below replaced it with
  bartowski's (same sizes), so `local_models.yaml` differs from that one row.
- `docs/measurements/local-model-headers-2026-10-23.py` / `.out.txt` / `.json`:
  every listed model's header read in 4 MiB steps - fields, where the metadata
  ends, bytes transferred. The Nemo row there is unsloth's file, the one rejected.
