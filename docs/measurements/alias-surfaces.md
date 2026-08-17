# How people actually write model names

**5.5 surfaces per model was what eleven hand-curated models happened to get.
The corpus attests a median of 2 — and 8 of the 11 primary surfaces have never
been observed at all.**

*Engineer 1 · 5,546 stored documents · 340-model registry · no fetch · 2026-08-17*

> `alias_rows` asks a human for the prose forms a model is discussed under —
> `opus 5`, `opus5`, the bare `opus`. That was judgement supplied from
> imagination, because there was no corpus to check it against. There is one now.

---

## 1 · The finding, in two rows

| model | hand-written **primary** | mentions | attested alternative | mentions |
|---|---|---|---|---|
| `anthropic/claude-opus-5` | `claude opus 5` | **0** | `opus 5` | **1,445** |
| `anthropic/claude-sonnet-5` | `claude sonnet 5` | **0** | `sonnet 5` | **166** |

The form the contract nominates as primary is one nobody in 5,546 documents was
observed writing. The form people do write sits in the variant list.

Both are airtight: `claude opus 5` and `opus 5` are equally detectable by the same
pattern, so this is a difference in usage rather than in instrumentation.

## 2 · Surfaces per model

Over the 72 registry models the corpus discusses:

| distinct surfaces | models |
|---|---|
| 1 | 18 |
| 2 | **37** |
| 3 | 15 |
| 4 | 2 |

**min 1 · median 2 · mean 2.01 · max 4**

- The eleven hand-curated models carry **5.5 each** — about **2.75×** what the corpus attests.
- **17 of 72** models reach `check_spelling_coverage`'s floor of **three**. The floor is unmet by 55 of the models anyone actually discusses.
- **18 models appear under exactly one surface.**

### What that does not prove

The floor may still be right as a *retrieval* policy — issuing a spelling nobody
types costs a query and misses nothing, so an unattested variant is waste rather
than error. What the measurement establishes is that the floor is not describing
observed usage, so it should be argued for on retrieval grounds or lowered. That
is a contract decision and it is on #33.

## 3 · Four verdicts, and the fourth is the useful one

A three-way split called `opus 5` *"uncarried"* while the registry holds
`anthropic/claude-opus-5`. That is wrong in the way that matters, and hides the
list this measurement exists to produce.

| verdict | surfaces | mentions | meaning |
|---|---|---|---|
| `resolved` | 83 | 2,646 | a mechanical variant reaches it |
| `attested-gap` | **62** | **4,556** | **the model is carried; the surface is missing** |
| `attested-gap-ambiguous` | 49 | 1,530 | several registry models could be meant |
| `unknown-model` | 255 | 1,523 | names nothing the registry carries — a poller finding |

**The largest single category by mentions is `attested-gap`.** 4,556 mentions of
models the registry already holds, under surfaces no derivation reaches. That is
the hand-written alias list, measured instead of imagined.

Top of it: `opus 5` (1,445) · `sonnet 4.5` (416) · `opus 4.6` (398) ·
`opus 4.8` (370) · `opus 4.7` (325) · `opus 4.5` (206) · `sonnet 5` (166) ·
`sonnet 4.6` (142) · `opus-4` (107) · `haiku 4.5` (83).

The pattern is one rule: **people drop the vendor word.** `opus 5`, not
`claude opus 5`. That is a single piece of judgement the corpus has now supplied,
and it generalises across every Anthropic model in the list.

## 4 · The family form is the most common and the least useful

Engineer 2's ruling on #33 is that a family-specificity claim never counts as
independent corroboration. The corpus says that is where most mentions land.

Family words with **no version token adjacent**:

| family | bare | with a version | bare share |
|---|---|---|---|
| `claude` | 8,149 | 351 | **96%** |
| `deepseek` | 1,240 | 31 | **98%** |
| `kimi` | 353 | 8 | **98%** |
| `mistral` | 335 | 32 | **91%** |
| `codex` | 796 | 242 | 77% |
| `gemini` | 2,048 | 1,375 | 60% |
| `opus` | 968 | 3,202 | 23% |
| `gpt` | 652 | 2,341 | 22% |
| **total** | **16,174** | **9,754** | **62%** |

**62% of family-word mentions carry no version.** So the most frequent way a
model is referred to is the one that resolves at a specificity which can record a
claim and cannot lift a cell. Her framing — *cheap to hold, safe to hold badly* —
is exactly what this shows: the tail is enormous and its ceiling is low.

It also explains why the family surface can never be auto-proposed. `claude` is
attested 8,149 times and attributable to no single model.

## 5 · What the detector cannot see

The pattern is a vendor or family word followed by a version token. It therefore
misses:

- **letter-prefixed versions** — `deepseek r1`, `deepseek reasoner`. So the 0 mentions against `deepseek r1` is a detector limit, not evidence about usage.
- **bare family forms**, measured separately in §4 rather than folded in.
- **models absent from this corpus.** 268 of 340 registry models are `mechanical-only` — recall unmeasured, not zero.

The headline "82% of hand-written surfaces never observed" is therefore an
overstatement and is not claimed. The two rows in §1 are, because both forms are
equally visible to the same pattern.

## 6 · Reddit only

All 5,546 documents are Reddit posts and comments. Blogs and GitHub carry
different naming conventions — a GitHub issue names a model in a config line,
where the id spelling `claude-opus-5` is likely the common form and the corpus
here says it is unattested. **So this measures how people write model names in
Reddit prose, and the id-spelling variants it finds unattested may be exactly
what the other two channels use.** That is the most likely way these numbers
mislead, and it is a reason to keep mechanical variants rather than prune to what
is attested.

## 7 · What would revise it

- **A GitHub and blog surface extract.** Same code, different corpus, and the prediction above is testable.
- **A detector that reaches letter-prefixed versions.** `deepseek r1` and `gpt-4o` shapes are invisible today.
- **More models discussed.** 268 of 340 are unmeasured, so nothing here says what the tail is written as.
