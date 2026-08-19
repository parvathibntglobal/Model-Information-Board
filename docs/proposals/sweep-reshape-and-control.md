# The sweep, reshaped to 26 × 75 — and a control that attacks the bias

**Two proposals. The first buys ±5.0pp for the same 78 calls. The second is the
first measurement in this project that attacks bias rather than precision, and
it is designed here before it is run.**

*Engineer 1 · 2026-08-18 · `contract/` untouched*

---

## Part 1 · Reshape to 26 × 75

### Why width and not depth

`ICC = 0.0778`, measured. The ceiling is `1/ICC ≈ 12.9` effective units per
subreddit **however deep the draw**, so 11 subreddits cap at ~142 and the sweep
measured 132. Depth is exhausted; only width is left.

| shape | calls | half-width |
|---|---|---|
| 11 × 175 *(run 2026-08-18)* | 78 | ±7.3pp |
| **26 × 75** | **78** | **±5.0pp** |
| 41 × 75 | 123 | ±4.0pp |
| 72 × 75 | 216 | ±3.0pp |

**Stop at 26.** Beyond it the budget triples to sharpen a figure whose dominant
uncertainty is *which subreddits are on the list*, not sampling error — and
Part 2 is the cheaper way to attack that.

### The fifteen additions, nominated by breadth

Same treatment as the eleven: ranked by **distinct queries answered** in the
2026-08-17 slice (113 queries, 275 subreddits), because breadth is less tied to
any one model than post count is. **Breadth nominates; a person decides.**

| rank | subreddit | queries | rank | subreddit | queries |
|---|---|---|---|---|---|
| 13 | `openclaw` | 14 | 23 | `ChatGPTcomplaints` | 11 |
| 14 | `vibecoding` | 14 | 24 | `claudexplorers` | 11 |
| 15 | `claude` | 14 | 25 | `ClaudeWorkflows` | 8 |
| 16 | `SillyTavernAI` | 13 | 26 | `cursor` | 8 |
| 17 | `google_antigravity` | 13 | 27 | `GoogleGeminiAI` | 7 |
| 19 | `accelerate` | 12 | 28 | `opencodeCLI` | 7 |
| 21 | `DeepSeek` | 11 | 29 | `AI_Agents` | 7 |
| 22 | `hermesagent` | 11 | | | |

Eleven current + fifteen = **26**.

### Exclusions, with reasons

Two more content-marketing venues surfaced in the nomination range, and they
rank high for the same reason the first two did — **they blanket-post about
every model, which is exactly what breadth rewards**:

| excluded | evidence |
|---|---|
| `AIPulseDaily` | *"Top 10 AI Updates Today — Feb 17, 2026 \| The Week That Won't Stop"* — daily aggregation, not reports from use |
| `ThinkingDeeplyAI` | *"[DEEP DIVE]…"*, *"100 tips for mastering…"*, *"Stop Paying for Research Reports — This Deep Research Mega-Prompt…"* — listicles and prompt-selling |

Carried forward from the first list: `u_enoumen` (a user profile page, `u_`
prefix), `AISEOInsider` (SEO listicles).

And one exclusion that is not a judgement:

| excluded | reason |
|---|---|
| `Anthropic` | returned `data not found` on page one of the 2026-08-18 sweep while the other eleven each returned 175. **Not empty — unavailable to `/getPostsBySubreddit`.** Recheck before re-adding. |

One borderline call recorded rather than hidden: **`accelerate` is included**
though its posts are closer to benchmark news (*"GLM-5.2 is now 1st on Design
Arena"*) than to reports from use. It is a genuine community rather than a
marketing account, and the exclusion criterion is deliberately narrow —
*content marketing*, not *content I would rather have*. If it turns out to
depress or inflate survival it will be visible per subreddit, which is how it
should be settled.

### The circularity, carried forward unchanged

```yaml
# WHAT A FIGURE MEASURED HERE MEANS, AND WHAT IT DOES NOT
#
# Survival measured over these subreddits is SURVIVAL WITHIN THE SUBREDDITS WE
# WOULD HARVEST. It is not survival over Reddit and must never be quoted as
# such. Every available basis for choosing them biases upward — these were
# nominated by how many distinct model-pair queries each answered in the
# 2026-08-17 slice, which is less circular than post count and is not
# uncircular.
#
# WIDENING NARROWS THE INTERVAL AND DOES NOT TOUCH THE BIAS. A wider list of AI
# subreddits is still a list of AI subreddits. The control set below is the
# only thing here that bounds the bias rather than the error bar.
#
# EQUAL DRAW, NOT PROPORTIONAL. Proportional draw would make r/ClaudeAI roughly
# half the sample and the figure a fact about one subreddit.

sweep_subreddits:
  version: "2.0"
  chosen_on: 2026-08-__
  draw: equal
  posts_per_subreddit: 75
  members: [ ...the 26... ]
  excluded:
    - {id: Anthropic,        reason: "data not found on page one, 2026-08-18; unavailable, not empty"}
    - {id: u_enoumen,        reason: "a user profile page, not a subreddit"}
    - {id: AISEOInsider,     reason: "SEO listicles about models, not reports from use"}
    - {id: AIPulseDaily,     reason: "daily AI-news aggregation"}
    - {id: ThinkingDeeplyAI, reason: "listicles and prompt-selling"}
```

---

## Part 2 · The control, designed before it is run

### What it measures — and yes, that framing is right

Your reading is correct and worth stating precisely.

The eleven were selected, directly or at one remove, for having answered
model-name queries. So survival within them is inflated by **topicality**, and
33.7% is a joint property of the pipeline and the population with no way to
separate the two. A control holds the pipeline constant and changes the
population, which is the only operation that separates them.

One refinement: it does not measure "how much of 33.7% is bias" as a subtraction
— populations are not additive that way. It **bounds** it. If a topically
neutral population survives at *x*, then roughly `33.7 − x` is what topicality
buys, and *x* is what the pipeline lets through regardless of subject.

This is the same technique as *"vary the query, not the world"* in
`docs/measurements/README.md`, applied one level up: **vary the population, not
the pipeline, and see whether the answer moves.**

### Which subreddits — both, and they are not the same instrument

"Non-AI" has a range, and the two ends answer different questions. The calls are
cheap enough to take both, but they should be labelled differently because only
one of them is a measurement.

**Tier 1 — general technical.** `programming`, `webdev`, `devops`, `rust`,
`golang`, `sysadmin`.
People writing about software who are mostly not writing about models. This
bounds **how much of the survival rate is AI-topicality specifically**, holding
technical-ness roughly constant. **This is the informative control.**

**Tier 2 — non-technical.** `AskReddit`, `todayilearned`, `movies`, `cooking`.
This bounds almost nothing about the pipeline's discrimination, because the
answer is nearly certain in advance. Its value is different and still real: it
is an **instrument control** — it establishes that the gates can return
near-zero at all.

That distinction matters because of a specific failure this project has already
had once: `substitution-slice.md` §1 opens *"a zero from a harness nobody has
shown can produce a one is indistinguishable from a broken harness"*. The mirror
applies here — **a filter nobody has shown can produce a near-zero is
indistinguishable from a filter that passes everything**, and every corpus
measured so far has survived at 24% or more.

So: Tier 1 measures the bias, Tier 2 proves the instrument. Ten subreddits, 75
posts each, 30 calls, about 90 seconds.

### Predictions, committed before the run

Recorded here so the numbers are read against a prediction rather than explained
afterwards.

| population | predicted survival | reasoning |
|---|---|---|
| **Tier 2** non-technical | **< 1%** | the entity gate should reject essentially everything; nothing names a model |
| **Tier 1** general technical | **3–8%** | engineers discussing code, occasionally naming a model. The `<15 tokens` and link-post gates behave much as they do now; the entity gate does nearly all the work |
| *the eleven, measured* | 33.7% | for comparison |

**What each outcome would mean:**

- **Tier 1 at 3–8%** — as predicted. Roughly 26–31 of the 33.7 points are
  topicality, and the pipeline's own discrimination is the remainder. The
  eleven are doing almost all the work, and the survival figure is close to
  meaningless without its population attached — which is what rule 7 already
  says and this would make quantitative.
- **Tier 1 at ~25–30%** — the gates are **not** discriminating on topic and
  something is wrong. The most likely culprit is the entity gate matching
  spuriously: 1,337 surfaces at a 4-character floor, matched by normalised
  substring, against text that never mentions a model. `cursor`, `codex`,
  `command` and `nova` shapes are where I would look first.
- **Tier 2 above 5%** — the instrument is broken, and no figure from any sweep
  should be trusted until it is understood. This is the outcome that would
  invalidate the 49.5pp bias measurement itself.
- **Tier 2 at ~0% and Tier 1 at 3–8%** — the expected result, and the one that
  makes the 49.5pp figure safe to quote.

I expect the expected result. The value is not in being surprised; it is that
**this is currently an assumption load-bearing in three documents**, and it
costs 30 calls to stop being one.

### Storage — same treatment, confirmed

Yes, and for a stronger reason than the sweep.

A control corpus is **maximally not-evidence**: it is deliberately drawn from
places nobody would harvest, and its documents are about cooking and sysadmin
work. Mixing it into `raw/` would put documents in the evidence store that no
ruling covers, from subreddits nobody reviewed, purely to compute one
percentage.

- separate directory, `_control_sweep/`, gitignored alongside the others;
- `delete_after` in its manifest, same 90-day retention;
- the same `reddit-via-rapidapi` ruling and the same live basis check — purpose
  is self-declared, and this is a fetch;
- and one addition: the manifest should record `population: control` explicitly,
  because a control corpus that later gets read as a sample is the exact defect
  the separate store prevents, and a directory name is a weaker signal than a
  field.

---

## What I would do, in order

1. **The control** — 30 calls, ~90 seconds, and it is the only thing here that
   bounds the bias rather than the error bar. It also gates whether the 49.5pp
   figure is safe to keep quoting.
2. **The reshape** — free at the current budget, and it halves the interval on
   everything this stage produces afterwards.

That is deliberately the opposite of the order they are written in. Precision
around a number whose bias is unbounded is the less useful purchase.
