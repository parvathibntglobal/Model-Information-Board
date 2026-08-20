# For Engineer 2: should `family` be derived from the canonical id, or stay a curation decision?

**The question is one level up from where I first put it.** I asked whether a model
is worth seating without a family surface. The real gap is upstream of the
artifact: **`family` is hand-curated, only `seed_models.yaml` populates it, and the
poller never writes it** — so all 342 registry rows carry NULL and there is
nothing for a family surface to be derived *from*.

*Engineer 1 · 2026-08-20 · a question, not a proposal · `contract/` unchanged*

**DSN for every figure:** `postgresql://bv_agent@52.17.75.29:5432/Model-information-Board`,
read-only. No writes behind this document.

---

## 1 · Why it is NULL, and it is deliberate rather than an oversight

`collect/registry/openrouter.py:166` names it explicitly:

```python
#: Never set from the feed. `family`, `lifecycle` and `regions` are not in it,
UNAVAILABLE = ("family", "lifecycle", "regions", "slot")
```

So `family` is in the same class as `lifecycle` — a field the feed does not carry
and the poller refuses to invent. The only writer is `load.py:265`, taking
`model.family` from a `SeedModel`, and the only source of a `SeedModel` is
`contract/seed_models.yaml`. **11 rows could have a family; 342 rows have NULL,
and 0 do.**

Consequence for the seating work: every alias row the 41 attested seats produce
carries `family = NULL`, and nothing anywhere can group by family today.

## 2 · The two sides, stated fairly

**For deriving it.** `anthropic/claude-opus-4.8` → `claude` is mechanical. The
vendor prefix is structured, the local part is structured, and a rule reads it
without judgement. It would populate 342 rows tonight instead of 11 by hand over
weeks, and it would make family-specificity resolution possible at all.

**Against deriving it.** `z-ai/glm-5.3` → `glm` is a guess. Nothing establishes
that `glm` is a family in the sense `claude` is a family — it may be the whole
product name, in which case the "family" is a synonym for the model and the
grouping does no work.

**And the value of what it buys is low at your gate**, which is the part only you
can weigh: a family surface only ever produces **family-specificity** mentions,
and a family-specificity mention records a claim and never lifts a cell — it is
not independent corroboration. So a derived family costs retrieval breadth and
buys nothing toward publication.

## 3 · The measurement: no rule reproduces our own eleven

I tested three candidate rules against the 11 curated values — the only ground
truth that exists, and the population is exactly those 11:

| canonical id | curated | `first-token` | `alpha-prefix` | `alpha-prefix+version` |
|---|---|---|---|---|
| `anthropic/claude-opus-5` | `claude` | ✓ | `claude-opus` ✗ | `claude-opus-5` ✗ |
| `google/gemini-2.5-pro` | `gemini` | ✓ | ✓ | `gemini-2.5` ✗ |
| `anthropic/claude-sonnet-5` | `claude` | ✓ | `claude-sonnet` ✗ | ✗ |
| `deepseek/deepseek-r1` | `deepseek` | ✓ | ✓ | `deepseek-r1` ✗ |
| **`mistral/mistral-large-2411`** | **`mistral-large`** | `mistral` ✗ | ✓ | ✗ |
| `google/gemini-2.5-flash` | `gemini` | ✓ | ✓ | ✗ |
| `anthropic/claude-haiku-4-5-20251001` | `claude` | ✓ | `claude-haiku` ✗ | ✗ |
| **`openai/gpt-4.1-mini`** | **`gpt-4.1`** | `gpt` ✗ | `gpt` ✗ | ✓ |
| `mistral/mistral-large-3` | `mistral-large` | ✗ | ✓ | ✗ |
| `deepseek/deepseek-v3` | `deepseek` | ✓ | ✓ | ✗ |
| `deepseek/deepseek-v4-flash` | `deepseek` | ✓ | ✓ | ✗ |
| | | **8 of 11** | **7 of 11** | **1 of 11** |

**The best rule reproduces 8 of 11, and the three misses are the informative
part.** The curated set uses **three different granularities**, picked per vendor
by what that vendor's naming actually means: `claude` groups opus/sonnet/haiku
across versions, `mistral-large` is a product line, and `gpt-4.1` is a *version*
line. A human chose each. No single rule can, because they are not the same kind
of thing.

## 4 · What the 41 look like on that axis

| | of the 41 | what derivation does |
|---|---|---|
| **clean** — one alpha token then a version | **15** | both rules agree: `gpt`, `glm`, `grok` |
| **multi-word alpha prefix** | **22** | the rules *disagree*: `claude` vs `claude-opus`, so the choice is a judgement |
| **version-first or interleaved** | **4** | derivation yields a non-family token: `qwen3`, `qwen2.5`, `o4` |

So **26 of 41 are cases where a derivation is either ambiguous or wrong**, and 15
are unambiguous *as a string operation*. Seven vendors: anthropic 13, openai 12,
z-ai 6, google 4, qwen 3, x-ai 2, meta-llama 1.

**And even the clean 15 are not safe, which is the finding I did not expect.**
`openai/gpt-4.1` is in the clean bucket and `first-token` gives `gpt` — while the
curated family for `openai/gpt-4.1-mini` is **`gpt-4.1`**. Derive one and curate
the other and the same line carries two families. `family` is a **grouping key**,
so two granularities in one column do not look wrong in a row-by-row read; they
silently split one group in two, or merge two into one. **Mixing derived and
curated values is worse than either alone.**

## 5 · What I would do, and it is yours to decide

**The artifact should carry the field, not the loader infer it** — which is what
the structural spread in §4 says under the rule we agreed: heterogeneous means
per-model. Concretely:

- `to_yaml` emits a **derived `family:` proposal** per entry, marked as derived, in
  the same slot discipline as every other value in that file. Code proposes; a
  reviewer accepts. That is the same split rule 2 imposes on the model, applied to
  a regex.
- The loader writes `family` only from an **accepted** value, and leaves NULL
  otherwise. NULL is honest — rule 6 — and it is what all 342 rows say today.
- **Never a mixed column.** If derivation is adopted it should backfill all 342 at
  one granularity in one migration, not arrive per-seat.

**If you want it derived anyway**, the case is defensible on the 15 clean ones and
the exceptions are nameable — the 22 multi-word and the 4 interleaved, listed by
id in `seating-the-attested-set.md`. That is a real option and cheaper than
curation; it just has to be all-or-nothing per granularity.

## 6 · What this does not block

**Nothing.** The loader ships without family surfaces, and the reason is
structural rather than optimistic: `model_alias` is append-only, so a family row
added in October is an `INSERT` beside the existing rows, not a rewrite of them.
Seating 41 models with their version and snapshot surfaces is 41 models more than
today, and the missing family alias is a **coverage** loss — mentions written as a
bare `sonnet` are not retrieved — not a **correctness** one. Nothing published
becomes wrong for want of it.

So this question wants an answer before we decide the *column*, and not before the
sweep starts.
