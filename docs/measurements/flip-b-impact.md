# Flipping (b): 47 documents lost against 2,330 corrected

*2026-09-17 · anooj + Claude · read-only over the stored corpus · no model calls, $0.00*

**The near-miss rule now refuses. Measured before it was flipped, on every
readable document in the corpus — not on the documents the check had already
kept.**

## The population, and how it was gathered

```
document rows with a text_ref            14,351
  reached and read as prose              10,131      the denominator below
  payload absent from this raw store,
    or not prose                          4,220
```

**10,131 is the denominator for every figure on this page**, and it is not the
corpus. The 4,220 are mostly payloads this machine's `raw_store` does not hold —
it is a partial mirror of staging, not staging — so they are absent from the
*measurement*, not from the database. A figure computed on a complete mirror
would be larger; it would not obviously be differently shaped, and nobody should
assume that from here.

Readable, by source:

```
reddit 5,513 · github 3,387 · hackernews 646 · devto 297 · blog 120 · huggingface 91 · x 77
```

Population fingerprint `ac0acff10dfbf54a`. Per-document detail, with every
document id and the two classes apart, in
[`flip-b-impact-2026-09-17.json`](flip-b-impact-2026-09-17.json).

## What changes

```
documents with a near miss               2,377      23.5% of 10,131 readable
  keep a correct attribution, shed a
    wrong one                            2,330
  resolve to NOTHING and drop as
    `no-resolvable-entity`                  47
```

**No model gains an attribution.** The rule only subtracts, so every figure
below is a removal. That is worth stating because "corrected" reads like a
transfer and it is not one: the evidence does not move to the right model, it
stops being filed against the wrong one.

### Models that lose a wrong attribution — the document survives

38 models, 2,965 removals. The head:

| model | documents |
|---|---:|
| `anthropic/claude-opus-4` | **1,010** |
| `anthropic/claude-sonnet-4` | **658** |
| `openai/gpt-5` | **617** |
| `z-ai/glm-5` | 196 |
| `anthropic/claude-fable-5` | 157 |
| `openai/gpt-4` | 137 |
| `moonshotai/kimi-k2` | 57 |
| `minimax/minimax-m2` | 24 |
| `deepseek/deepseek-v4-pro` | 18 |
| `deepseek/deepseek-chat` | 15 |

The shape is the one the 2026-09-08 proposal predicted: **the `.0` of every
active line is the victim.** `claude-opus-4` was accumulating documents whose
text discusses 4.1, 4.5, 4.6, 4.7 and 4.8. Those cells were not empty and not
wrong by a little.

### Models that lose documents entirely — 47 documents, 17 models

| model | documents |
|---|---:|
| `openai/gpt-5` | 11 |
| `anthropic/claude-opus-5` | 10 |
| `anthropic/claude-sonnet-4` | 8 |
| `openai/gpt-4` | 7 |
| `anthropic/claude-sonnet-4.5` | 3 |

These had no clean surface: every surface that matched did so inside a longer
version string, so after (b) they resolve to nothing and `NO_ENTITY` drops them.
**Losing them is the right direction.** They discuss models we do not track,
`near-miss-not-registered` now names the surface, and that count is the registry
work-list. The alternative was filing them against a model they are not about.

## Why these figures differ from the 2026-09-08 ones

That measurement reported **1,641 of 5,010 (32.8%)**; this one reports **2,377
of 10,131 (23.5%)**. Both are correct for their population and neither
supersedes the other as a rate:

- the corpus roughly doubled — 14,351 document rows now against ~6,500 then;
- this run reads every source, and the raw-store mirror it reads is this
  machine's;
- Fable 5.1 was registered in between, and two Fable 5 surfaces misseated on it
  were retired on 2026-09-17, which changes what resolves.

The absolute counts are what the ruling was made on. **The rate is not
comparable across the two and should not be quoted as a trend.**

## What is still not refused

`fable 5-preview` resolves. The rule requires a **digit** after the separator,
so a word suffix passes. Widening it would have to defend `gpt-4-turbo` and
`opus-5-thinking`, where the suffix sometimes names a different model and
sometimes a mode of the same one — **so widening means re-measuring, not
re-reasoning.** Recorded as a known exclusion in
`tests/test_near_miss_resolution.py`.

## Rule 8, and why this was not a shortcut

The near miss shipped as a **recorded field** on 2026-09-08 and became a **gate**
on 2026-09-17, which is the one-way direction the rule requires. The evidence
that promoted it was measured on a population the check did not choose: every
readable document, including the ones it had already kept.

The order mattered here rather than being a formality. The recorded field is
what produced the count that made the trade visible — 47 against 2,330 — and
before it existed the same question had been answered by a regex from outside
the resolver that reported 20 where the exact method reports 1,641. A floor 80×
low would have argued for a very different decision.
