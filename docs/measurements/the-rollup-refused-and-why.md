# The rollup is refused, and the refusal is the answer

**`platform_count` cannot reach 2 on any cell, and the 36 blog claims were never
the thing in the way.**

I did not store them, and that is a decision rather than an omission: **4 of the
5 that resolve are resolved WRONGLY**, and writing them would put false
attributions in `claim`. The measurement that was wanted — is `platform_count`
2? — is answered without the write, and the answer does not depend on it.

```
blog claims                                        36
resolve to exactly one model_version                5
   ...of those, resolved CORRECTLY                  1
reddit claims already stored                        4   anthropic/claude-fable-5
cells that could reach platform_count = 2           0
```

**`platform_count` is 2 corpus-wide and 1 on every cell.** You asked for those to
be stated as different things; they are, and only the second one governs
publication.

*Engineer 1 · 2026-08-21 · no model calls, no writes*

---

## 0 · Five figures in the request that do not match the measurements

Stated first and once, because four of them change conclusions downstream.

| in the request | measured | where |
|---|---|---|
| 28 blog claims | **36** | corrected last turn; 28 was the pre-rename run |
| survival 6.2% | **8.7%** (17 of 195) | `TriageRun`, population `c511fceb6b7fb3df` |
| 172 dropped on model-entity | **177** | `no-resolvable-entity` |
| n_eff 3.0 before triage, 2.0 after | **1.828 before, 0.206 after** | 151 authors → 17 survivors at 0.012105 per voice |
| "the 21 we measured" | **21 is yours**, from the inheritance ruling; my parallel count was **168 of 195 (86.2%)** | `inherited-subjects-and-family-claims.md` |

The n_eff pair matters most. The direction you describe is right and the
magnitude is not: it is not 3.0 falling to 2.0, it is **1.828 falling to 0.206**
— neither figure passes, and the fall is a factor of nine rather than a third. A
gate that was 1.6× short becomes 15× short.

---

## 1 · Why the rollup is refused

### Only 5 of 36 blog claims resolve to a model at all

```
resolve to exactly one model_version     5
resolve to MORE than one                 2
resolve to nothing                      29
```

The 29 are not marginal cases. They are the corpus:

```
Qwen 3.8 27B  11     Codex 3     Anthropic 2   Claude 2   Claude Code 2
Muse Glimmer 1  OpenAI 1  Google 1  Fable 1  Gemini 3.7 Flash 1
Qwen 2  AI-assisted coding tools 1  GPT-Live 1
```

**`Qwen 3.8 27B` accounts for 11 of them and is not in the registry**, because
the registry is still `contract/seed_models.yaml` — the 10-model build fixture,
listed in root `CLAUDE.md` as removable "when OpenRouter polling lands". A corpus
about models the registry does not contain cannot produce cells, and no amount of
extraction changes that.

### And 4 of the 5 that resolve are resolved wrongly

```
GPT-5.6 Sol Ultra   -> openai/gpt-5   via the surface 'gpt-5'
GPT-5.6 Luna        -> openai/gpt-5   via the surface 'gpt-5'
GPT-5.6 Sol Pro     -> openai/gpt-5   via the surface 'gpt-5'
Claude Opus 4.8     -> claude-opus-4 AND claude-opus-4.8
Claude Haiku 4.5    -> anthropic/claude-haiku-4.5        <- the only correct one
```

**`gpt-5` matches inside `gpt-5.6`, and `opus 4` matches inside `opus 4.8`.** The
boundary check passes because `.` is a boundary character, so a shorter version
surface is a boundary-valid substring of a longer one.

So storing these would file three engineers' first-hand reports about **GPT-5.6**
as claims about **GPT-5** — a different model, on a board whose entire purpose is
telling models apart. That is rule 1's failure mode one level up: the quote is
verbatim, the attribution is wrong, and verification cannot see it because
verification checks the quote.

**I could not find this recorded.** The known boundary defect is `free` inside
*"freeze"* and `fusion` inside *"confusion"* — a version surface inside another
version surface is the same mechanism between two things that are both real
models, which is why it produces a plausible row instead of an obvious one.

> **This is why the rollup was not run rather than run-and-noted.** One correct
> claim and four wrong ones is not a corpus with a caveat; it is four false
> attributions and a footnote nobody re-reads. The write is cheap and reversing
> a published misattribution is not.

---

## 2 · Which capabilities have claims on both platforms: none

```
REDDIT, stored           anthropic/claude-fable-5   over_refusal        n=2
                         anthropic/claude-fable-5   code.generation     n=2

BLOG, resolvable         anthropic/claude-haiku-4.5 instruction.adherence
                         openai/gpt-5               code.generation      (x3, mis-resolved)
                         openai/gpt-5               summarization.fidelity (mis-resolved)
```

**`code.generation` has claims on both platforms — on different models.** A cell
is `(model_version, capability, condition_bucket)`, so `fable-5/code.generation`
and `gpt-5/code.generation` are two cells, each with one platform.

**No `model_version` appears on both platforms. Zero cells can reach
`platform_count = 2`.**

So the two statements you asked me to separate:

```
platform_count = 2 CORPUS-WIDE     true the moment any blog claim is stored,
                                   and it publishes nothing
platform_count = 2 ON A CELL       false, on every cell, and it is what
                                   check_gate reads
```

The corpus-wide figure is the more flattering one and the less meaningful one —
the same shape as `35 aliases declared` standing in for `35 aliases that matched`.

### And you are right that 2 would not publish anything anyway

Even granting a two-platform cell, with the per-voice weight the table actually
produces:

```
n_eff needed                            3.0
per-voice weight (tier D, observed)      0.012105
voices required                        247.8
```

One blog voice added to a Reddit cell is **two voices, n_eff ~0.024**. The
overlap you doubted does not exist, and if it did it would move `n_eff` by 0.012.

---

## 3 · The survival finding, recorded properly

**First measurement of E4 against a real corpus, and it corrects a target that
has been quoted for weeks.**

```
population   195 comments, ONE thread (t3_1u1b22l, r/ClaudeAI, one announcement)
             195 of a reported 785 -> the thread itself is 24.8% observed
fingerprint  c511fceb6b7fb3df, 1385 surfaces

kept          17
dropped      178
SURVIVAL     8.7%          UPPER BOUND
```

**8.7%, against a 10–15% target.** And the target's population is different in a
way that decides the comparison:

> **The estimate was written for POSTS. This is COMMENTS.** A comment is a
> document with its subject removed — the root carries the subject and the reply
> carries the opinion. So the dominant drop is not quality, it is
> **attribution**: `no-resolvable-entity` takes 177 of 195, and
> `too-short-no-artifact` takes 74.

That is why the population matters more than the rate here. 8.7% on comments and
10–15% on posts are not the same measurement disagreeing; they are two
measurements of different things, and the estimate has still never been tested on
the population it was written for.

The figure is an upper bound for a second, unrelated reason: `wrong-language` and
`known-bot` **could not run** (no detector, no list) on all 195, and
`pure-link-post` and `out-of-window` had nothing to run on. Documents those would
have dropped are counted as kept.

### The n_eff reversal belongs here

```
distinct authors across all 195 comments      151      n_eff ceiling 1.828
distinct authors among the 17 survivors        17      n_eff ceiling 0.206
```

**A voice count measured on documents triage is about to reject is not a voice
count.** 151 authors is a fact about the thread; 17 is the fact about the cell,
and the second is the one the gate reads. Survivors concentrate — every one of
the 17 is a distinct author, so the survival step removes 134 voices and no
duplicates.

Both figures fail `N_EFF_MINIMUM = 3.0`, so this is not an argument for loosening
triage. It is the reason "152 authors stored" must never be quoted as "152
voices": the gap between them is a factor of nine on this thread, and it is
measured rather than assumed.

**And on the claims that actually exist, triage changes nothing** — both
claim-bearing documents survive it cleanly. The ceiling moved; the reading did
not. Those are different facts and the writeup keeps them apart.

---

## 4 · Inheritance: the population is 0, not 177

The rule, from the ruling: *a comment that resolves to nothing inherits its
thread root's subject, **if the root resolves to exactly one model** and the
comment names no other.*

```
CONDITION 2 - comment names no other model
   177 of 177 satisfy it   (trivially: they name none at all)
   139 distinct authors among them

CONDITION 1 - root resolves to exactly one model
   FAILS
```

**So the fraction of the 177 the ruling would reach is 0%.** Not because of the
second condition — which is what settled the ruling, and which holds here on
everything — but because the **first** condition fails on the root. And it fails
for two reasons, both of which are defects rather than facts about the thread:

**(a) The root's actual subject is not in the registry.** The post announces
`Claude Fable 5` (9 mentions) and `Claude Mythos 5` (6 mentions). Both resolve to
nothing.

**(b) The only model that resolves is a one-word aside, and it resolves to two.**

```
'opus' appears at ONE offset in the root: 1078
  "...the response is handled by Claude Opus 4.8, our next-most-capable model."

that single mention matched 13 surfaces owned by 2 model_versions:
  claude opus 4.8 / opus 4.8 / ...  -> anthropic/claude-opus-4.8
  claude opus 4   / opus 4   / ...  -> anthropic/claude-opus-4
```

So if condition 1 were "fixed" by taking the longest match, inheritance would
attribute **139 authors' opinions about Fable 5 to Claude Opus 4.8** — a model
named once, in a sentence about which requests get *refused and handed off*.

**That is a stronger argument than the one the ruling was made on, and it points
the same way.** The recorded concern was that the rule recovers vendor
announcement prose — true, and a quality objection. This is a correctness
objection: on the one thread we hold in full, the inherited subject would be the
**wrong model**, and there would be 139 voices of it.

The ruling stands and now has a second, independent reason. Worth adding to it,
because the first reason ("mostly vendor prose") invites the reply *"then filter
for non-vendor threads"*, and this one does not.

---

## 5 · What is actually in the way, in order

Neither `platform_count` nor `n_eff` is blocked by corpus size, extraction, or
attribution. What blocks them, measured:

| | | |
|---|---|---|
| 1 | **the registry is a 10-model build fixture** | 29 of 36 blog claims name a model it does not contain. `contract/seed_models.yaml` is scheduled for removal "when OpenRouter polling lands", and that is now the gating item for cells rather than a tidy-up |
| 2 | **a shorter version surface matches inside a longer one** | `gpt-5` in `gpt-5.6`, `opus 4` in `opus 4.8`. Produces confident wrong attributions, and it is why the rollup is refused rather than caveated |
| 3 | **nothing writes `collect/triage/`'s output** | `triage_verdict`, `specificity_score`, `has_numbers`, `has_conditions` NULL on 254 of 254. `compute()` refuses on the last two, so no claim can be weighted, so no claim reaches a cell |
| 4 | **`n_eff` needs 248 voices at tier D** | and `f_specificity` — 0.58, the only value it has ever held, three of four inputs dead — is 0.58 of the 0.1009 multiplier. Fix it before arguing about the threshold |

**(2) is new and it is the one to do first**, because every later measurement
rests on attribution being right. (1) and (3) are known and scheduled. (4) is
last on purpose.

---

## What changed

Nothing was written. The rollup was refused for the reason in §1, and the two
write paths this points at — the surface-matching fix and the triage writer — are
each their own piece of work rather than something to attach to a measurement.

**Proposed to Engineer 2, not taken:** `resolve()` returning a longest-match-wins
result, or the caller taking `hits[0]` — it already sorts longest-first for
exactly this reason, and nothing uses that property. That is a one-line change
with a corpus-wide effect on attribution, which is the definition of something to
propose rather than take.
