# Reopening the family-word ruling — and the numbers move the question

**The reopening is right that the exclusion has been the binding constraint four
times. The numbers say it is not what stops this corpus reaching a cell, and
that the blocker is one level down: a family claim has nowhere to be stored.**

```
133 of 140 blog claims resolve to no model
  53  contain a family word by substring     a family ruling could reach these
  26  are a BARE family mention              Codex 11 · Claude 6 · Gemini 4 ·
                                             ChatGPT 3 · Mistral 1 · Deepseek 1
  80  contain no family word at all          LLM 15 · AI 6 · model 4 · agents 4 ·
                                             LLMs 3 · Lucy 3 · "JetBrains' model" 3
```

**60% of the unresolved claims are unreachable by any ruling about
`FAMILY_WORDS`**, because people wrote a category noun rather than a family.
`LLM`, `AI`, `model`, `agents`, `today's models`, `embedding models`,
`stronger model` — 80 claims whose subject is not a model name at all.

**Resolver unchanged. This is your ruling.**

*Engineer 1 · 2026-08-21 · 140 claims, 6 feeds, 75 documents, one draw*

---

## 1 · The four instances, with the two I have to correct

| | claimed | measured |
|---|---|---|
| `oqocfjv` | binding | **agreed** — recorded, and the ranking moved rank 3 → 8 when the selector was fixed |
| "62.5% on the first blog run" | binding | **I cannot source this figure.** No run of mine reports 62.5%. The first blog run was 8 claims from 4 of 30 documents |
| "172 of 195 comments dropped on model-entity" | binding | **177 of 195**, and 104 of those on that gate *alone* |
| "133 of 140 blog claims resolving to nothing" | binding | **agreed, and it is mine** — but only 26 of the 133 are bare family mentions |

So the pattern is real and the fourth instance is weaker evidence for it than it
looks. Three of the four are about **unresolvable subjects**; only one of them is
specifically about **family words being excluded**.

### The correction, and it is about the list rather than any member of it

**Only `oqocfjv` is a clean family-word instance. The other three are three
different things, and the list was assembled by anooj from measurements each of
which was correct on its own terms.**

```
oqocfjv          a family word excluded from the population       CLEAN
"62.5%"          5 claims on the first blog run; not a
                 family-word figure, and not one I can source     DIFFERENT THING
177 comments     dropped for naming NO MODEL AT ALL - category
                 nouns, not families                              DIFFERENT THING
133 blog claims  only 26 (20%) are bare family mentions;
                 80 contain no family word                        DIFFERENT THING
```

**The shape, and it is worth more than the correction:** four measurements each
concluded *"the cost is small"*, each about a different slice, and nobody added
them up. Adding them up was the right instinct — the composition argument is how
you find a constraint that no single measurement can see. What went wrong is that
**the four instances were not instances of one thing.** A pattern assembled from
cases that turn out to be four different phenomena reads as four confirmations
and is one observation plus three coincidences.

The tell was available and cheap: **each member of the list should name the same
mechanism**, and *"dropped for naming no model at all"* is not *"dropped because
a family word was excluded from the population"*. Nothing about the reasoning
required a new measurement to check — only asking, of each item, whether it was
the same failure.

Recorded here rather than in the writeup because this is the file someone reads
when they next want to reopen the exclusion, and the list is what would persuade
them.

**And the composition argument still stands.** Four measurements each said the
cost was small, and each measured a different slice. Nobody added them up until
now, which is exactly the failure the reopening names. The correction is to the
size of the effect, not to the shape of the reasoning.

---

## 2 · What a family-specificity claim does end to end

Traced through the code rather than reasoned about. **It stops at the first
step, and not where the ruling put it.**

### Storage: it cannot be stored, and the resolver is not why

```
claim.specificity      NOT NULL, and 'family' is a permitted value
claim.family           nullable text — the column exists
claim.model_version_id NOT NULL          <-- here
```

`judge/pipeline.py:372`:

```python
if model_version_id is None:
    log.info("claim references %r which resolves to no tracked model", surface)
    continue
```

**A family is a COLUMN on `model_version`, not a ROW.** `model_version.family`
exists; there is no `model_version` row meaning *"the Claude family"*. So a
family claim needs a foreign key to something that does not exist, and
`Pipeline.run` drops it before any weighting.

> **This is the finding that changes the question.** Emptying `FAMILY_WORDS`
> would make `resolve("Claude")` return surfaces — and the claim would still be
> dropped one line later, because those surfaces belong to specific versions and
> picking one would be the attribution error the exclusion exists to prevent.
> Picking none leaves `model_version_id` NULL, which the schema refuses.
>
> **So the resolver is not the binding constraint. The absence of a
> family-shaped destination is.** Changing the resolver alone produces exactly
> the same zero, one line further down.

### Weighting: reachable only hypothetically, and the number is known

If a destination existed, `judge/vet/weight.py`:

```
f_fuzziness   snapshot 1.0 · version 0.6 · family 0.3
```

Against the only multiplier chain the table has produced (0.1009 non-tier, tier
D 0.12), a family claim at `f_fuzziness` 0.3 instead of 0.6 halves an already
tiny weight: **per-voice ~0.006**, so `N_EFF_MINIMUM = 3.0` would need roughly
**496 distinct voices in one cell.**

### Counting: `gate.count` would count it, and that is the real hazard

`count()` dedups on `voice_id` and knows nothing about specificity. So family
claims **would** count toward `independent_voices`, `platform_count` and
`max_author_share` — at 0.3 fuzziness but a full head each.

The recorded worry was this and it is arithmetic, not judgement: **26 bare
family mentions across 6 feeds are up to 26 voices generated by nobody naming a
version.** `WIDELY_PRAISED_VOICES = 5`. A cell could reach "widely praised"
on five people who each wrote *"Claude"*.

### Rendering: it would render, and the page has no vocabulary for it

`judge/curate/phrases.py` assembles from counts and `CAPABILITY_LABELS`.
Nothing in `describe()` or `condition_label()` takes specificity as an input, so
a family-backed cell renders identically to a version-backed one:
*"Generally praised for code generation"* — with no way for a reader to see that
none of the voices said which model.

**That is rule 4's shape rather than rule 4 itself**: not silence reading as
criticism, but *imprecision reading as precision*. And it is the one part of the
chain with no measurement behind it, because no family claim has ever been
stored.

---

## 3 · So: what would the page show, and is it worth more than nothing?

You asked whether *"one person said Codex is slow"* with no path to publication
is worth more than nothing or worse. Traced, the answer has three parts and only
the third is a judgement call:

**It cannot reach a cell today** — no destination row, and `N_EFF_MINIMUM` would
need ~496 family voices even if there were one. So the realistic options are not
*publish* versus *discard*.

**The two options that are actually available:**

| | what the reader sees | what it costs |
|---|---|---|
| **discard** (today) | nothing. The coverage page says *"nobody has publicly discussed this"* for a capability 26 people discussed without naming a version | rule 4 at its largest scale — an absence that is really an unresolved subject. **This is the current behaviour and it is the strongest argument for reopening** |
| **record, never publish** | still nothing on a model page, but the coverage page could distinguish *"no evidence"* from *"26 unattributable mentions"* | a `specificity='family'` destination, and a coverage-page vocabulary for it. No gate change |

**My recommendation, and it is narrower than the reopening asks for:** the
valuable half is the **coverage page**, not the model page. *"26 mentions of
`Codex` that name no version"* is a true, countable, publishable statement that
costs no gate change, cannot corroborate anything, and directly fixes the rule-4
problem the exclusion currently creates. *"One person said Codex is slow"* on a
model page is worse than nothing, because a reader cannot tell it from a
version-specific report and the page has no way to say so.

**Three things that need your ruling and are not mine to decide:**

1. **is there a family destination at all** — a `model_version`-shaped row, a
   separate `model_family` table, or a nullable `claim.model_version_id` with a
   `family` fallback. Each is a contract change and they are not equivalent.
2. **does a family claim count as a voice** — it would today, and 26 voices from
   6 feeds against `WIDELY_PRAISED_VOICES = 5` is the risk in one line.
3. **can a phrase carry specificity** — if a family-backed cell can render, the
   phrase assembler needs a form that says so, and that is your file.

**What is NOT in question, and I want to be explicit because the reopening could
be read as arguing it:** the original ruling was right that a family claim cannot
corroborate a version claim. Nothing measured here disputes that. What is
disputed is only whether *discarding* it is the right way to honour it.

---

## 4 · And 60% of the problem is not this ruling at all

Whatever is decided, **80 of 133 unresolved claims stay unresolved**:

```
LLM 15 · AI 6 · model 4 · agents 4 · LLMs 3 · Lucy 3 · "JetBrains' model" 3 ·
Cognition 2 · "today's models" 2 · Modern BERT 2 · embedding models 2 ·
Language models 2 · stronger model 2 · FastAPI 2
```

These are category nouns, products that are not models (`FastAPI`, `Cognition`,
`Claude Code`), and models absent from a 10-entry seed registry (`Lucy`,
`MiniLM`, `Modern BERT`). No ruling about `FAMILY_WORDS` reaches any of them.

**Two of those three causes have known fixes already queued** — retiring
`contract/seed_models.yaml` for OpenRouter polling, and the version-substring
defect (`gpt-5` inside `gpt-5.6`, `opus 4` inside `opus 4.8`). The third —
*people write "our LLM"* — is not a defect and has no fix. It is a property of
the medium, and it caps what a blog corpus can ever contribute to a cell.

That last one is worth its own line in whatever you decide: **the
positive-evidence channel mostly does not name its subject.** 95% of blog claims
in this run named no resolvable model, and that is the number to hold beside any
estimate of what blogs will eventually publish.

Two false positives in the 53, named so the figure is not over-read: `MiniLM`
matches `mini` and `Jarvis Pro` matches `pro`. Both would resolve to the wrong
family, which is the substring defect arriving inside the family question.
