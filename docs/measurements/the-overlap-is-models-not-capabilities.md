# The platforms discuss the same capabilities about different models

**The zero overlap is real and it is not where it was expected. Blogs and Reddit
overlap completely on *what* they discuss; they overlap on *nothing* about which
model they discuss it about — and that is what `PLATFORM_MINIMUM` actually
assumes.**

```
BLOG      9 distinct capabilities, 36 claims
REDDIT    2 distinct capabilities,  4 claims
INTERSECTION  {code.generation, over_refusal}   -> NOT empty. Reddit is a SUBSET.

model_versions on both platforms                 -> 0
cells reaching platform_count = 2                -> 0
```

*Engineer 1 · 2026-08-21 · no model calls, no writes*

---

## 1 · The premise as stated is inverted, and the finding survives it

The proposition was: *blogs carry 6 capabilities, Reddit carries 2, intersection
empty — `over_refusal` on Reddit and not on blogs.* Measured:

```
BLOG                                        REDDIT
  code.generation                    9        code.generation    2
  reasoning.multistep                7        over_refusal       2
  instruction.adherence              6
  code.editing_diff_fidelity         4
  tool_calling.long_chain_reliability 2
  summarization.fidelity             2
  over_refusal                       2   <-- present on blogs
  extraction.faithfulness            2
  ops.latency_ttft                   2
```

Nine, not six. And `over_refusal` **is** on blogs, so both of Reddit's
capabilities appear there: the intersection is not empty, it is **complete on
Reddit's side**. Reddit discusses a strict subset of what blogs discuss.

So the reasoning offered for the gap — *a link blog does not write about a model
refusing a request, and a launch thread does not write about code generation* —
is contradicted twice by this corpus. A link blog wrote about refusals (2
claims). A launch thread wrote about code generation (2 claims).

**The zero overlap is at the CELL, and a cell is `(model_version, capability,
condition_bucket)`:**

```
REDDIT   anthropic/claude-fable-5     over_refusal, code.generation
BLOG     anthropic/claude-haiku-4.5   instruction.adherence
         openai/gpt-5                 code.generation, summarization.fidelity
```

`code.generation` has claims on both platforms — about **Fable 5** on Reddit and
**GPT-5** on blogs. Two cells, one platform each.

---

## 2 · So the finding about the gate's premise is sharper, not weaker

`PLATFORM_MINIMUM = 2` requires two platforms **in one cell**. The premise it
rests on is *"the same model and capability get discussed on more than one
platform"*, and the measured obstacle is not subject matter:

> **The platforms agree on the vocabulary and disagree on the subject.** They
> discuss the same capabilities and different models. So `PLATFORM_MINIMUM` is
> not failing because a link blog and a launch thread are about different things
> — it is failing because they are about different *releases*, and a corpus
> assembled at one moment catches each platform mid-conversation about whatever
> shipped most recently for its audience.

That is a different problem from the one the premise anticipates, and it has a
different remedy. Two platforms discussing different capabilities is a corpus you
cannot fix by collecting more of the same — the channels genuinely differ. Two
platforms discussing different *models* is a **timing and breadth** problem:
blogs cover whatever the author reviewed this week, Reddit covers whatever
launched. Overlap arrives as both widen, and it needs no change to the gate.

**Two caveats that keep this from being over-read**, both mine:

- **the blog side is 5 resolvable claims of 36**, and 4 of those 5 are
  mis-resolved by the version-substring defect (`gpt-5` inside `gpt-5.6`). So the
  blog column of that table is one defensible row — `claude-haiku-4.5` — and the
  rest is a matcher artefact. The zero overlap is not in doubt; its *shape* is
  measured through a broken resolver.
- **denominator**: 40 claims total, one blog feed, one Reddit thread, one
  extractor, one draw. This is a statement about two documents' worth of
  conversation, not about the platforms.

---

## 3 · Inheritance, reopened and answered with the data

**Granted in full, inheritance multiplies `n_eff` by 6.1× and still does not
reach the gate. So the question of whether it recovers good evidence or bad is
moot on this corpus.**

### The recoverable population is 104, not 145 or 177

```
dropped on no-resolvable-entity                177
  ...ONLY that gate — genuinely recoverable    104
  ...also failing another gate                  73   (short, no artifact)
distinct authors among the recoverable          86
```

The 73 matter: `triage` runs every gate without short-circuiting, so a comment
that fails both the entity gate and `too-short-no-artifact` is not saved by
resolving its entity. Inheritance reaches 104 comments, and **86 voices**.

### What that does to the gate

```
current survivors            17 voices  ->  n_eff 0.206
+ the recoverable           103 voices  ->  n_eff 1.247      6.1x
N_EFF_MINIMUM                                     3.0        STILL FAILS
```

Your fivefold estimate is right in magnitude — **6.1×** — and the destination is
still short by a factor of 2.4. A rule that multiplies the binding number six
times and leaves it failing is not the rule that unblocks the board.

### And what it recovers, measured rather than characterised

Of the 104 recoverable comments:

```
carrying NONE of has_numbers / has_code / has_error_strings / has_conditions
                                                       75 of 104   (72%)
median body length (all 177 inheritable)                90 chars
under 120 characters                                    64%
has_error_strings                                        0%
has_conditions                                           1%
```

**72% carry no specificity signal of any kind.** Median 90 characters. Zero error
strings across 177 comments. This is reaction, not observation — *"yeah wondering
too"*, *"Also curious to know"*, *"Hi anthropic, what happens after June 22"*.

### The answer

**It is evidence that inheritance recovers the population we least want, and the
data adds a third thing the ruling did not have: most of what it recovers is not
a claim at all.**

The standing ruling's objection was that the rule recovers *vendor announcement
prose*. That is a quality objection and it invites the reply *"then exclude
announcement threads"*. The measurement says the recovered material is thinner
than that: not vendor prose, which at least asserts something checkable, but
sub-100-character reaction to vendor prose.

**Three independent reasons now, and they fail the rule at three different
layers:**

| | reason | layer |
|---|---|---|
| 1 | 32 of 53 candidates name a second model (the original ruling) | the rule's own second condition |
| 2 | the root does not resolve to exactly one model — Fable 5 is not in the registry, and the one model that resolves resolves to two | the rule's **first** condition, so the population is 0 |
| 3 | 72% of what it would recover carries no specificity signal, median 90 chars | what the rule is *for* |

And **the fourth is that it does not reach the gate**: 1.247 against 3.0.

**Not built, and the recommendation is unchanged.** What changed is that the
ruling no longer depends on a judgement about announcement threads — it has a
measurement at each of the three conditions and an arithmetic result underneath
them.

> One thing this does NOT establish, said because it is the obvious next move:
> that inheritance would fail on a non-announcement thread. We hold one thread in
> full. Reason 3 is a fact about *this* thread's comment mix and reason 2 is a
> fact about *this* root. Only reason 1, which is yours, was measured across
> more than one. If inheritance is reopened again, it should be reopened on a
> thread that is not a launch post — and we do not have one.

---

## 4 · Corrections to figures carried into this turn

| stated | measured |
|---|---|
| blogs carry 6 capabilities | **9** |
| intersection empty | **{code.generation, over_refusal}** — Reddit is a subset |
| `over_refusal` on Reddit and not blogs | on **both**; 2 claims each |
| 145 of 172 at 84% | **104 of 177** recoverable (59%); the 84% figure is the share carrying **no specificity signal**, which is a different quantity |
| multiplies n_eff ~fivefold | **6.1×**, 0.206 → 1.247, still failing 3.0 |
| 253 documents, 40 survived | **254 documents, 31 kept** — and 27 of those are `unavailable` rather than judged |
| `triage_verdict` "exists now" | **NULL on 254 of 254.** Nothing writes it; the inventory computes verdicts at render time and says so |

The 84% is worth keeping: it is the sharpest number in §3 and it answers the
question that was actually asked. It is just not the recovery rate.
