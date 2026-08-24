# What the frontend shows: two lines, and a rollup cannot add a third

**Measured against `52.17.75.29/Model-information-Board`. The board renders two
sentences, both of them "not yet corroborated", on one model out of 342.**

```
model_version rows                342
models with any cell at all         1     anthropic/claude-fable-5
cell rows                           2     both `insufficient`
published cells                     0
```

`anthropic/claude-fable-5`, the only page with anything on it:

```
capabilities                12
  reported (has a cell)      2
  unreported                10
  insufficient               2
  PUBLISHED                  0
  silent_and_unreported      4    capabilities needing positive consensus,
                                  where absence must not read as criticism

  code.generation  "One person mentioned code generation - not yet corroborated"
  over_refusal     "One person mentioned over-refusal - not yet corroborated"
```

**Every other model page — 341 of them — renders 12 unreported capabilities and
no cell.**

*Engineer 1 · 2026-08-21 · no writes, no model calls*

---

## 1 · The rollup: what it would add, and why I did not spend on it

The rollup's ceiling is computable without running it, and it is **zero published
cells.**

Blog claims extracted, across both runs: **176** (36 Willison + 140 from six
feeds). Of those:

```
resolve to exactly one model_version        9
  ...of which mis-resolved by the
     version-substring defect               7    GPT-5.6 -> gpt-5 (x4),
                                                 Claude Opus 4.8 -> opus-4 AND 4.8
  correctly resolvable                      2    both anthropic/claude-haiku-4.5
```

So a maximally successful, honest rollup stores **2 claims**, adds **2 cells** on
`anthropic/claude-haiku-4.5`, takes models-with-a-cell from 1 to 2, and prints
two more *"One person mentioned … — not yet corroborated"* lines. `n_eff` per
claim is ~0.012–0.07 against `N_EFF_MINIMUM = 3.0`.

**Nothing becomes published. Not one cell, on any arithmetic.**

### What I did not do, and the cost of doing it

I did not execute the store. Two reasons, and the second is the real one:

- **the saved runs do not carry what `StoredClaim` needs.** It takes an
  `ExtractedClaim` object and a `VerifiedQuote`; the run JSONs carry quote text
  without offsets. Storing means re-extraction — ~$0.005 for the two documents
  that matter, or ~$0.27 for both corpora.
- **`compute()` still refuses.** `has_numbers` and `has_conditions` are NULL on
  119 of 120 blog documents, so no blog claim can be weighted, and
  `CellStore.weighted_claims_for` inner-joins `claim_weight` — an unweighted
  claim is excluded rather than counted at zero. **The triage writer does not
  exist**, and that is a piece of work rather than a step inside a rollup.

So the rollup is blocked behind the missing triage writer, and its reward on the
far side is two more insufficient lines. Stated rather than attempted, because
"$0.27 and a new write path for two uncorroborated sentences" is a decision
rather than a task.

**Correction to the framing:** the number was **176 blog claims, not 28.** 28 was
a pre-rename figure from the first Willison run and has been superseded twice
(28 → 36 → 176).

---

## 2 · Why a further sweep does not help

**Written down before anyone asks for one on the strength of a claim count.**

```
last sweep       9 feeds, 105 articles, 89 new documents, ~230 requests
extraction       75 documents -> 140 claims, $0.2238
STORED                                        0
```

**140 claims stored zero, and 133 of them resolve to no model.** More documents
produce more claims that fail at the same step. The mechanism, with the number
against each part:

| why a claim cannot reach a cell | claims | does a sweep help? |
|---|---:|---|
| the subject is a category noun — `LLM` 15, `AI` 6, `model` 4, `agents` 4, `LLMs` 3 | **80** | **No.** This is how people write. More writers write it more |
| bare family mention — `Codex` 11, `Claude` 6, `Gemini` 4, `ChatGPT` 3 | **26** | **No.** Blocked by a ruling, not by corpus size |
| a product that is not a model — `Claude Code`, `FastAPI`, `Cognition`, `MiniLM` | ~15 | **No.** They will never be `model_version` rows |
| a model the registry does not have | ~12 | **No**, and see below |
| resolves, then mis-resolves on the substring defect | 7 | **No.** A code fix |

**On the registry, I have to correct myself.** I twice attributed non-resolution
to *"the 10-model seed fixture"*. It is not that: `model_version` holds **342
rows, all `provenance='polled'`** — the OpenRouter poller has landed and the
seed fixture is gone. The registry contains `openai/gpt-5`,
`anthropic/claude-haiku-4.5`, `qwen/qwen-2.5-*`. What it does not contain is
`Qwen 3.8 27B`, `GPT-5.6 Sol Ultra`, `Fable 5`, `Muse Glimmer` — because those
do not exist upstream. **Part of the unresolved rate is the test corpus being
partly synthetic**, which is a property of the fixture world and not of the
medium, and I should not have folded it in with `LLM` and `AI`.

That correction cuts both ways and does not change the conclusion: the synthetic
names will not resolve however many feeds are swept either.

### So the number on screen moves when one of these changes

```
1. the family-word ruling            up to 26 claims, and it needs a
                                     family-shaped destination first
2. the version-substring fix         7 claims, and it stops 4 FALSE
                                     attributions being written
3. the triage writer                 unblocks weighting for every claim
4. the corpus names versions         not ours to change
```

**None of them is a sweep.** Three are code or ruling changes and the fourth is a
property of what people write. A tenth feed adds documents, claims, cost and
requests, and adds nothing to the board.

---

## 3 · What the two rendered sentences are worth

Worth saying, because "two insufficient lines" reads like nothing and is not:

**The phrases are correct and they are doing rule 4's job.** *"One person
mentioned code generation — not yet corroborated"* is distinguishable from
*"nobody has publicly discussed this"* and from *"engineers report problems"*.
Three states, three different sentences, on a board with almost no evidence —
that is the part of the design that is working, and it is working on the smallest
possible input.

**And `silent_and_unreported = 4` is the number a reader should be shown.** Four
of `claude-fable-5`'s twelve capabilities fail silently — a wrong answer that
looks right — and have no evidence at all. That is the honest headline for this
model today, and it is more useful than either rendered phrase.

---

## What changed

Nothing was written. The measurements are reads.

The two write paths this points at — the triage writer, and the resolver's
longest-match fix — are each their own change, and the second is proposed to
Engineer 2 rather than taken because it alters attribution corpus-wide.
