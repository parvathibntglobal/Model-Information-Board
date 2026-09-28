# Flipping (b): 33 documents lost against 2,322 corrected

*2026-09-17 · anooj + Claude · read-only over the stored corpus · no model calls, $0.00*

**The near-miss rule now refuses. Measured before it was flipped, on every
readable document in the corpus — not on the documents the check had already
kept.**

> ⚠ **THE FIRST VERSION OF THIS PAGE SAID 47 AND 2,330, AND ITS CONCLUSION ABOUT
> THE 47 WAS WRONG.** It read: *"Losing them is the right direction. They
> discuss models we do not track."* **14 of those 47 were `X.0`** — `"Sonnet 5.0
> is another disaster"` names Sonnet 5, and the rule refused it. So nearly a
> third of everything the gate would have dropped was a model we **do** track.
>
> The sentence was inherited from the 2026-09-08 proposal rather than checked
> against the documents. **Reading eight of the 47 falsified it**; no amount of
> re-reading the rule would have. `_SAME_VERSION` now excludes `.0`, and every
> figure below is from the corrected rule.

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
*measurement*, not from the database.

Readable, by source:

```
reddit 5,513 · github 3,387 · hackernews 646 · devto 297 · blog 120 · huggingface 91 · x 77
```

Population fingerprint `ac0acff10dfbf54a`. Per-document detail, with every
document id, its refused surfaces and the two classes apart, in
[`flip-b-impact-2026-09-17.json`](flip-b-impact-2026-09-17.json).

## What changes

```
documents with a near miss               2,355      23.2% of 10,131 readable
  keep a correct attribution, shed a
    wrong one                            2,322
  resolve to NOTHING and drop as
    `no-resolvable-entity`                  33
```

**No model gains an attribution.** The rule only subtracts, so every figure
below is a removal. Worth stating because "corrected" reads like a transfer and
is not one: the evidence does not move to the right model, it stops being filed
against the wrong one.

### Models that lose a wrong attribution — the document survives

38 models, 2,950 removals. The head:

| model | documents |
|---|---:|
| `anthropic/claude-opus-4` | **1,007** |
| `anthropic/claude-sonnet-4` | **653** |
| `openai/gpt-5` | **617** |
| `z-ai/glm-5` | 195 |
| `anthropic/claude-fable-5` | 156 |
| `openai/gpt-4` | 137 |
| `moonshotai/kimi-k2` | 57 |

**The `.0` of every active line is the victim.** `claude-opus-4` was
accumulating a thousand documents whose text discusses 4.1, 4.5, 4.6, 4.7 and
4.8.

### Models that lose documents entirely — 33 documents, 15 models

| model | documents |
|---|---:|
| `openai/gpt-5` | 10 |
| `anthropic/claude-opus-5` | 6 |
| `openai/gpt-4` | 5 |
| `anthropic/claude-sonnet-4` | 4 |
| `anthropic/claude-sonnet-4.5` | 3 |

These have no clean surface, so `NO_ENTITY` drops them. `hackernews:49112867` is
the shape that is right: *"Advancing the price-performance frontier with
GPT‑5.6"* refused against `openai/gpt-5`, because 5.6 is not 5.

**They are not uniformly documents about untracked models**, which is what the
first version of this page claimed. What can be said is narrower and is what the
`near-miss-not-registered` flag is for: each one names a surface we do not hold,
the flag now names it, and that count is the registry work-list.

## The two classes the rule gets wrong, one fixed and one recorded

| continuation | example | documents | ruling |
|---|---|---:|---|
| `X.0` | `Sonnet 5.0` | 17 (14 of them drops) | **FIXED** — `.0` restates the version, it does not advance it |
| `X-0731` | `DeepSeek-V4-Flash-0731` | 22 | **recorded, not ruled on** |

The dated-snapshot case is left as it was, deliberately. `5.0` and `5` are the
same number and that is settled; whether a dated build may speak for its line is
a different question, and deciding it inside a regex would decide it silently.
22 documents currently lose an attribution to the line they are about.

**A measurement error worth recording, because it nearly buried the `.0` class.**
The first count of it read a 2-character window and reported 47 `.0` documents.
A 2-character window cannot evaluate `(?!\d)` — it runs off the end and the
lookahead passes vacuously — so every `-0731` snapshot was counted as a `.0`.
Widening the window to 3 split them: 17 and 22. The same off-by-one lived in the
rule itself, which is why the fix is a window change as much as a pattern change.

## Why these figures differ from the 2026-09-08 ones

That measurement reported **1,641 of 5,010 (32.8%)**; this one reports **2,355
of 10,131 (23.2%)**. Both are correct for their population and neither
supersedes the other as a rate:

- the corpus roughly doubled — 14,351 document rows now against ~6,500 then;
- this run reads every source, from this machine's raw-store mirror;
- Fable 5.1 was registered in between, and two Fable 5 surfaces misseated on it
  were retired on 2026-09-17, which changes what resolves;
- this run excludes `.0`, and that measurement did not.

**The rate is not comparable across the two and should not be quoted as a
trend.** The absolute counts are what the ruling was made on.

## What is still not refused

`fable 5-preview` resolves — the rule requires a **digit** after the separator.
Widening it would have to defend `gpt-4-turbo` and `opus-5-thinking`, where the
suffix sometimes names a different model and sometimes a mode of the same one,
**so widening means re-measuring, not re-reasoning.**

## Rule 8, and the part that nearly went wrong

The near miss shipped as a **recorded field** on 2026-09-08 and became a **gate**
on 2026-09-17, which is the one-way direction the rule requires, and the
evidence came from a population the check did not choose.

What rule 8 does *not* guarantee, and this change demonstrates: **a measured
gate can still be a wrong gate.** The 47-document figure was measured correctly
and its interpretation was inherited. The thing that caught it was reading the
documents the gate would drop — which is cheap, was not part of the process, and
is the step worth adding for the next gate.
