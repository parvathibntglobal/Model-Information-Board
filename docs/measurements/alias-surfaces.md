# How people actually write model names

**5.5 surfaces per model was what eleven hand-curated models happened to get.
The corpus attests a median of 2 — and 8 of the 11 primary surfaces have never
been observed at all.**

*Engineer 1 · 5,546 stored documents · 340-model registry · no fetch · 2026-08-17*

> `alias_rows` asks a human for the prose forms a model is discussed under —
> `opus 5`, `opus5`, the bare `opus`. That was judgement supplied from
> imagination, because there was no corpus to check it against. There is one now.

---

## 0 · How to read a zero in this document

Two different facts print identically in a table, so they are written
differently here:

| written | means |
|---|---|
| **0** | measured, and the count came back zero. Only used where the form is as visible to the detector as the forms that did match — the two rows in §1 |
| **not measured** | the detector cannot see this shape, or the corpus contains no document that could have carried it. There is no observation, and no zero |

`deepseek r1` is **not measured** (§5). It is not measured as zero. Someone will
eventually prune an alias, a model or a capability on the strength of a zero, and
the distinction has to survive into whatever they read.

## 1 · The finding, in two rows

| model | hand-written **primary** | mentions | attested alternative | mentions |
|---|---|---|---|---|
| `anthropic/claude-opus-5` | `claude opus 5` | **0** | `opus 5` | **1,445** |
| `anthropic/claude-sonnet-5` | `claude sonnet 5` | **0** | `sonnet 5` | **166** |

The form the contract nominates as primary is one nobody in 5,546 documents was
observed writing. The form people do write sits in the variant list.

Both are airtight: `claude opus 5` and `opus 5` are equally detectable by the same
pattern, so this is a difference in usage rather than in instrumentation. These
are the **measured zeros** of §0, and the only two in this document.

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
- **17 of 72** models are attested under three or more surfaces. That is the number that invited reading `check_spelling_coverage`'s floor of **three** as unmet by 55 — a reading the ruling below rejects, because the floor counts renderings and not attestations.
- **18 models appear under exactly one surface.**

### What that does not prove — and the ruling on #33

The floor is right as a *retrieval* policy: issuing a spelling nobody types costs
a query and misses nothing, so an unattested variant is waste rather than error.
What the measurement establishes is that the floor does not describe observed
usage, which is a reason to argue for it on retrieval grounds — not a reason to
lower it, and not a reason to raise it either.

**Ruled: the floor stays at three, and it keeps counting renderings.** A floor
counting *attested* surfaces would fail 55 of these 72 models, and every one of
those failures would be fixed by a person inventing a spelling to satisfy the
gate. A check whose remedy is fabrication is worse than no check. Spaced,
hyphenated and concatenated are derivable from the id, so the floor as written is
always satisfiable without judgement — for every multi-token id, which is 154 of
the 155 in the registry slice; the exception is `openrouter/auto`, a router rather
than a model.

The **family surface** stays required-but-`INCOMPLETE`-able rather than gating.
A bare `opus` is attested constantly (§4) and attributable to no single model, so
a gate demanding one could only be satisfied by asserting an attribution the data
refuses. It is a permanent `INCOMPLETE` slot in the proposer instead, which is a
gap a reviewer can see and act on.

The reasoning sits beside the gate, in `collect/registry/aliases.py`.

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

### So it stops being judgement, and becomes a third proposer input

`collect/registry/propose.py` now derives it: `claude-opus-5` → `opus-5` →
`opus 5`, rendered the same three ways as any mechanical form. It is kept apart
from `attested` because **one is observed and the other is derived from an
observed rule** — `opus 4.6` at 398 mentions is a fact about that model, and
`fable 5` is a fact about the rule. A derived surface never becomes a model's
primary and never changes its `status`, or a derivation would be readable off the
output as a measurement.

Over the 155 ids this extract names, run without fetching anything:

| | |
|---|---|
| models the rule fires on | **14** |
| surfaces derived | 42 |
| of those, also attested | **24**, carrying **4,087 mentions** |
| fired but unattested | 2 — `anthropic/claude-fable-5`, `anthropic/claude-opus-5-fast` |

The rule refuses more often than it fires, and each refusal is a place it would
have stopped being mechanical: `gemini-2.5-flash` would leave `2.5 flash` when the
form people write is `flash 2.5`, a reordering; `mistral-large-3` would need
`large` to be known as a tier word; `claude-haiku-4-5-20251001` would derive a
date stamp nobody types; `claude-opus-5:batch` would derive `opus 5:batch`, and
stripping the route suffix instead would hand `opus 5` to two canonical ids at
once — the collision the seed load already refuses. **A refusal is not a claim
that no vendor-dropped form exists**, which is why those models keep their
`INCOMPLETE` slots rather than gaining a silence.

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

- **letter-prefixed versions** — `deepseek r1`, `deepseek reasoner`. So `deepseek r1` is **not measured**: the pattern cannot see that shape, so no count was taken. It is not measured as zero, and nothing here says anybody does or does not write it (§0).
- **bare family forms**, measured separately in §4 rather than folded in.
- **models absent from this corpus.** 268 of 340 registry models are `mechanical-only` — recall **not measured**, which is a different cell from a model measured at zero.

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

### 6.1 · `alias_rows` gives one reason for two rows, and it is inverted on GitHub

**No behaviour changed by this section.** It checks a docstring against the
numbers, from figures already in this repository — there is still no GitHub
surface extract, and the one named in §7 would settle it properly.

`alias_rows` adds two rows nobody declared — the canonical id and its local part
— and dismisses both with one sentence:

> Neither earns a search query: `anthropic/claude-opus-5` and
> `claude-haiku-4-5-20251001` are strings that appear in configs and API logs, not
> in the prose this lane harvests.

**The behaviour is right and the reason is wrong**, differently on each platform.

*Where it holds.* Both examples it picks are the two shapes this corpus finds
absent from Reddit prose: **0 of 10,255 attested mentions** carry a vendor-namespaced
slash form, and **18 of 10,255** carry a date-shaped token at all, one of them
Anthropic's shape. Those two rows earn no Reddit query, measured.

*Where it is inverted.* On GitHub, configs are not somewhere else — they are
inside the documents this lane harvests, and matching them is a deliberate design
decision in this lane:

> `subject` and `topic` establish ABOUTNESS and may match anywhere: a config line
> naming a model is real evidence the model was in use, and worth retrieving.
> — `collect/adapters/queries/sieve.py`

The rest lines up with that rather than with the docstring. GitHub's **52.7%
subject match** is justified in `docs/logic-and-workflow.md` by models being
"named in configs, `model=` parameters and dependency manifests". `names_version`
is present in **48.3%** of GitHub documents against **6.3%** of blog articles, and
`docs/measurements/specificity-backfill.md` §3 says that name "usually arrives in
a config block rather than a sentence". Both GitHub regression fixtures in
`fixtures/github/` name their model exactly one way — `vertex_ai/gemini-2.5-pro`,
`model="gemini/gemini-2.5-flash-preview-04-17"` — in a config line, inside a fence.
So on GitHub the id spelling is not what we fail to match; it is much of what we
match on.

*What weakens this, said here rather than left for someone to find.* The 52.7%
comes from a corpus retrieved for **one model and three capabilities**, using that
model's declared variants — so a document matching a subject term is partly the
query coming back, and the rate is not a clean estimate of how GitHub names models
in general. What survives that objection is the *shape*: whatever the rate, the
place a GitHub document carries the name is a config line, and the spelling a
config line carries is the id's. The two fixtures are two documents, not a sample.

*One refinement the docstring's bundling hides.* The two rows do not deserve the
same verdict even on GitHub. Configs carry a **routing** prefix — `vertex_ai/`,
`gemini/`, `openrouter/` — which is not the vendor namespace the registry spells,
so `google/gemini-2.5-flash` matches a config line no better on GitHub than on
Reddit. It is the **local part** that earns the query. One reason covering both
rows is what let that difference stay invisible.

*And it is not perfectly right for Reddit either.* Surfaces that are exactly a
model's id local part carry **1,408 mentions, 13.7% of the 10,255 attested here**,
across 34 surfaces — and for `openai/gpt-5` the local part `gpt-5` at 311 mentions
is the model's **most** mentioned surface, ahead of the spaced `gpt 5` at 38 and
the concatenated `gpt5` at 50. Anthropic ids are the exception rather than the
rule: `claude-opus-5` is unattested while `gpt-5`, `gpt-5.5`, `gemini-2.5-flash`
and `glm-4.6` are all attested under their id spelling. That costs nothing today
only because the seed file declares those local parts by hand, so they are
search-eligible through the declared list rather than through the auto-added row.
`collect/registry/policy.py` states the same reason more strongly still — "nobody
types them into a Reddit post" — and `gpt-5` is a counterexample with 311 mentions.

*A figure to correct while we are here.* The **6.6%** in `contract/harvest.yaml` is
a **blog** figure — articles naming a model the registry carries, against 24.3%
naming any versioned model — and it measures registry coverage rather than a sieve
subject rate. Reddit has no published subject-match figure at all. The Reddit half
of the argument stands on this extract instead, which is a stronger basis for it.

**So: yes, inverted for one platform, and this is a second independent argument for
per-platform rendering** — reached from alias surfaces rather than from the query
budget. The two arguments do not share a premise: one says the budget is spent on
spellings a platform will not match, this one says the *shape* that matches differs
per platform, and they happen to point at the same change.

## 7 · What would revise it

- **A GitHub and blog surface extract.** Same code, different corpus, and the prediction in §6 is testable — including §6.1, which argues from existing figures rather than from a measurement of GitHub surfaces.
- **A detector that reaches letter-prefixed versions.** `deepseek r1` and `gpt-4o` shapes are **not measured** today rather than measured low.
- **More models discussed.** 268 of 340 are not measured, so nothing here says what the tail is written as.
- **A vendor-drop rule for a second vendor.** §3's rule is derived from Anthropic-shaped ids and fires on 14 of 155. Whether `flash 2.5` and `large 3` are real forms is a question for a corpus, not for this module.
