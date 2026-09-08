# Near-miss resolution is silent misattribution, with a live example

**2026-09-08, anooj.** `Fable 5.1` resolves to `anthropic/claude-fable-5`. Not a
miss — a wrong answer, filed, with nothing on the row to disagree with. This is
the alias-precision case and it now has a measurement and a victim.

Two asks: **a near-miss must refuse rather than resolve** (§2, and §3 says what
that costs), and **four registrations** (§4) which are the ceiling on everything
else.

---

## 1 · The defect, measured

`fable 5` is a registered surface of `anthropic/claude-fable-5`. `fable 5.1` is
not registered at all. The resolver matches the former inside the latter:

```python
resolve("Claude Code fable 5.1 is seriously flawed", pop)
    -> ('fable 5', 'fable-5', 'fable5')   owners: anthropic/claude-fable-5
```

**Measured EXACTLY, now that the resolver can see source offsets** (§3a — the
first figures below were a regex estimate from outside the resolver, stated as a
floor, and they were one). Two classes, and they must not be pooled:

| | staging documents | share of 5,010 readable |
|---|---|---|
| **certainly wrong** — no clean surface, so every model it resolves to is wrong | **20** | 0.4% |
| **additionally misattributed** — names a real model AND picks up a wrong one | **1,621** | 32.4% |
| **total carrying a wrong attribution** | **1,641** | **32.8%** |

**Which models collect evidence they were never given:**

| filed against | documents |
|---|---|
| `anthropic/claude-opus-4` | **763** |
| `anthropic/claude-sonnet-4` | **632** |
| `openai/gpt-5` | **390** |
| `openai/gpt-4` | 137 |
| `z-ai/glm-5` | 46 |
| `moonshotai/kimi-k2` | 29 |

`docs/measurements/staging-misattributions-2026-09-08.json` — **every one listed
with its `document_id` and `url`**, the two classes apart, so they can be
corrected rather than counted.

**The 20 is the number I estimated and it held. The 1,621 is the one I missed**,
and it is the one that matters: a document saying *"Sonnet 4.5 handled this
better than Sonnet 4"* is correctly about 4.5 and additionally filed against 4,
so `claude-opus-4` and `claude-sonnet-4` accumulate hundreds of documents whose
text discusses 4.1, 4.6 or 4.8. Those cells are not empty and not wrong-by-a-
little; they are substantially made of other models' evidence.

The new-platform corpus figure was **36 of 192 (18.8%)** by the estimate, high
because that corpus was harvested for a `.1` model.

**Why it is worse than a miss.** A miss drops a document and
`no-resolvable-entity` counts it. A near-miss files Fable 5.1's evidence into
Fable 5's cell, where it becomes a consensus phrase somebody reads as being
about Fable 5. There is no counter, no flag, and nothing on the claim that says
the subject was reached by a prefix. Rule 6's shape at the resolution layer: a
definite answer invented from an absent one.

## 2 · The mechanism, and it is not the boundary map

`normalize` strips every non-alphanumeric, so **`fable 5.1` and `fable 51`
normalise to the same string** — `fable51`. What separates them is the boundary
mask: the dot in `5.1` was a separator, so `ends[]` is True after the `5`, and
`fable5` is an admissible match. In `fable 51` there is no separator, `ends[]`
is False, and it correctly does not match.

```
"fable 5"    in "we ran fable 5"       -> matches   correct
"fable 5"    in "we ran fable 5.1"     -> matches   WRONG
"fable 5"    in "fable 51"             -> no match  correct
"fable 5"    in "fable 5-preview"      -> matches   WRONG
"fable 5"    in "fable 5x"             -> no match  correct
```

So the boundary map is doing exactly its job. **A version dot is a word
boundary and is not a version boundary**, and nothing in the resolver knows the
difference. It is the `free`/`freeze` and `fusion`/`confusion` defect that
`normalize_with_boundaries` was built for, one level down: solved for words,
unsolved for versions.

## 3 · What it takes to make a near-miss refuse — (a) and (c) are DONE

**Three changes. (a) and (c) landed 2026-09-08; (b) is the one awaiting a
ruling.**

**(a) DONE — `normalize_with_offsets` returns source offsets.**
`normalize_with_boundaries` now delegates to it and drops the fourth value, so
there is one implementation and the mask and the offset map cannot disagree
about where a character came from. `sources[i]` is the index in the original of
normalised character `i`, so `text[sources[j] + 1:]` is what followed a match —
the thing the resolver previously could not see.

This was the blocker, and the reason is the best evidence for it: the earlier
estimate re-located each surface with a separator-flexible regex from OUTSIDE
the resolver, and **that cannot locate a surface which matched only in
normalised space** — `fable5` against `"fable 5.1"`. It skipped 126 of 192 and
3,035 of 5,010 documents. **It reported 20 and the exact method reports 1,641.**
The floor was 80× off.

This is the same artifact `offset_map` already is elsewhere in the pipeline, for
the same reason, and `collect/CLAUDE.md`'s first rule applies: *it is roughly
ten lines while you are already walking the string, and impossible to
reconstruct afterwards.*

**(b) A right-edge version rule in `resolve`.** With offsets, after an
admissible match at `[i..j]`, look at the original character following the
match's source span:

```
next char is `.` or `-` followed by a digit   -> NEAR MISS
next char is a digit                          -> NEAR MISS
anything else                                 -> a hit, as today
```

`fable 5` in `fable 5.1` and `fable 5-1` refuse; `fable 5 is fine` and
`fable 5, and opus` resolve.

**A DIGIT IS REQUIRED AFTER THE SEPARATOR, so `fable 5-preview` still
resolves.** An earlier draft of this section claimed it refused; it does not,
and the difference matters because the 1,641-document figure was measured on the
narrow rule. Widening to any word suffix would also have to defend `gpt-4-turbo`
and `opus-5-thinking`, where the suffix sometimes names a different model and
sometimes a mode of the same one — so widening means re-measuring, not
re-reasoning. Recorded as a known exclusion in
`tests/test_near_miss_resolution.py`.

**(c) DONE — the near miss is NAMED and COUNTED, and resolution is unchanged.**
`resolve_with_near_misses` returns a `Resolution(hits, near_misses)` where
`hits` is byte-for-byte what `resolve` returns, near misses included. The gate
puts `near-miss-not-registered` on `TriageResult.flags` — the non-dropping
channel — when EVERY matched surface is a near miss, and
`TriageStoreRun.by_flag` counts it per source and reports it in `describe()`
as "FLAGGED, NOT DROPPED".

Two details that took a correction each. A surface appearing once as
`fable 5.1` and once as `fable 5` is a **hit**, not a near miss — one real
mention is a mention, so the rule is *every* admissible occurrence continued,
not any. And `Resolution.only_near_misses` compares the two SETS: my first
version tested `not self.hits`, which is never true because `near_misses` is a
**subset** of `hits` — so it silently returned False on the very document that
motivated the change. Third instance in three days of reading a subset as a
disjoint set, and the reason `Resolution.owners()` now answers at the model
level rather than the surface level.

It is named rather than silent because:

- rule 4 — a document dropped for naming an unregistered model is an absence we
  caused, and it must not read like a platform having nothing to say;
- the count **is the registry work-list**. 35 documents refused on `fable 5.1`
  is precisely the signal that says register Fable 5.1, and it arrives without
  anybody going looking.

**Which direction is safer, since both are wrong.** Refusing loses the
document; resolving corrupts a cell. Refusing-and-counting is strictly better,
because the loss is visible and carries its own fix, while the misattribution
has neither. That asymmetry is the argument, not caution.

**Rule 8's order, followed.** (a) and (c) are recorded fields: resolution is
unchanged, the misattribution is still happening, and it is now counted where
somebody can act on it. (b) — subtracting `near_misses` from `hits` — is **one
line** and is the ruling I am asking for, on the evidence §1 now carries.

**What flipping (b) would cost, so the ruling is not blind.** 20 documents
would stop resolving entirely and be dropped as `no-resolvable-entity` — those
are the certainly-wrong ones and losing them is right. The other 1,621 would
keep their correct attribution and lose the wrong one, which is the whole
point. So the trade is 20 documents dropped against 1,641 corrected, and the 20
are documents about models we do not track.

## 4 · Four registrations, and they are the ceiling on everything else

**Four of 28 Hacker News story titles resolve to a tracked model.** That is the
binding constraint on the thread-subject join, on the entity gate, and on
anything the board can say about the models people are actually discussing.

| register | evidence in the corpus | consequence today |
|---|---|---|
| **GPT-6 Astra** | an HN story titled `GPT-6 Astra` with **2,063 comments**, another `A Figma clone built by GPT-6 Astra`, a third `GPT-6 Astra soundly defeats Fable 5.1…` | resolves to **nothing**. Its 2,063-comment thread contributes **0** inherited comments. Registering it alone roughly **doubles the corpus-wide inheritance figure** |
| **Claude Fable 5.1** | HN story `Claude Fable 5.1 and Claude Mythos 5.1` (1,377 comments); `Claude Code fable 5.1 is seriously flawed` | resolves to **Fable 5** — 35 documents misattributed |
| **Claude Mythos 5.1** | the same title, second model | resolves to nothing |
| **Gemini 3.8 Flash** | HN story `Gemini 3.8 Flash and 3.8 Flash Cyber` (**664 comments**) | resolves to nothing |

**Note what `GPT Astra 6` did.** I harvested it as given and it retrieved **0
documents containing its own query phrase on every platform** — the real name is
`GPT-6 Astra`. A wrong surface is not a quiet failure: it returns loosely
matched documents that look like a corpus and are about nothing, and only the
`surf` column in the harvest report says so.

**These are polled models, not hand-curated ones.** `model_version` holds 342
rows, all `provenance='polled'`, so the fix is presumably that the OpenRouter
poller has not seen these yet — or that they are not on OpenRouter at all,
which is a different problem and the more likely one for `GPT-6 Astra` and
`Claude Mythos 5.1`. **I have not established which**, and it matters: one is a
polling cadence question and the other needs a curated surface with
`provenance` saying so.

**HELD 2026-09-08, pending that determination.** No rows added, no surfaces
curated. `model_version` is the registry and `assert_no_fixtures` exists
precisely to stop hand-written models arriving beside polled ones — and
guessing which of the four are polled-and-late would produce the same class of
defect as the one §1 measures: a definite value invented where the answer was
absent.

**What settles it:** whether each of the four appears in OpenRouter's model
list. If it does, this is a polling cadence question and nothing needs
curating. If it does not, it needs a curated surface carrying `provenance` that
says so. Somebody should read the poller's source list rather than infer it
from the registry's contents.

## 5 · Why this is first

Everything downstream is capped by it. `no-resolvable-entity` drops 33.3% of the
new corpus and 31.5% of staging; the subject join lifts one thread and no
others; and the 18.8% that *do* resolve include documents filed against the
wrong model. **The gates are working. The registry is three model-generations
behind the conversation**, and no amount of gate work reaches past that.

---

*Corpus: `docs/new-platform-corpus-and-triage-2026-09-08.md`. Measurements:
`near-miss-misattribution-2026-09-08.json`, `hn-subject-join-2026-09-08.json`.
Population fingerprint `b5744297e9210497` (342 polled rows, 1,247 surfaces).*
