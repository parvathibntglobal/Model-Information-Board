# For Engineer 2: a comparison is a property of a conversation, not a message

**The stratum is a result, not a sampling failure — and it points at the labelling
unit rather than at the harvest.**

```
7 of 12 threads    carry two model surfaces
2 of 812 comments  carry two model surfaces
```

*Engineer 1 · 2026-08-20 · corroborated independently against
`postgresql://example_user@203.0.113.5:5432/Model-information-Board`*

---

## 1 · What those two numbers mean together

A comparison needs two models in view. At comment level that essentially never
happens — **2 of 812, 0.2%** — and at thread level it is the common case: **7 of
12, 58%**. So *"the corpus is too small"* is the wrong diagnosis and more harvest
is the wrong remedy. The comparison is there; it is distributed across the
messages of a conversation instead of sitting inside one.

**Independent corroboration, different corpus, different platform mix.** Over 57
stored documents on staging — 30 blog articles, 27 GitHub issue bodies, each a
whole post rather than a comment:

```
>=2 model surfaces, word-boundary matched : 22 of 57   (39%)   —  18 github, 4 blog
```

Whole posts behave like your threads, not like your comments. Two corpora, two
platforms, one shape: **the unit that carries a comparison is bigger than a
message.**

## 2 · The extractor already sees them. That is not the gap

`judge/` reads a `thread_context`, and a `thread_context` is the flattened
conversation with its `offset_map`. So a thread-level comparison is **already
visible to E5** — nothing in the harvest or the assembly is hiding it.

**What is unestablished is attribution**: given *"we moved off X to Y and it fixed
the tool loop"*, does the extractor put the criticism on X and the praise on Y, or
does it attach both to whichever surface is nearer the quote? That is what a
golden set measures, and it is the open question. Visibility is not.

Worth saying because three pieces of work assumed a unit without fixing one — the
phrase-binding measurement, the direction-blind rendering, and the
`requires: phrase_binding` ruling were all about the *shape* of a comparison, and
none of them established the *unit* at which it appears. It appears at thread
level. That was not known when any of the three landed.

## 3 · The question that is yours, asked directly

**Does the golden set want thread-level items for the two-surface stratum?**

It cannot be comment-level: a comment-level item for that stratum is either
unavailable (2 of 812) or, worse, one of the two — a sample of size 2 standing in
for a phenomenon that occurs 58% of the time one level up.

But a thread-level item is **a different labelling task**, not a bigger one:

| | comment-level item | thread-level item |
|---|---|---|
| text the labeller reads | one message | a whole conversation, 5–6 messages |
| judgement | does this sentence praise or criticise this model | does the conversation attribute this claim to **this** side of the comparison |
| failure it can catch | polarity, sarcasm, condition | **attribution across speakers**, plus all of the above |
| cost per item | minutes | materially more, and harder to keep consistent between labellers |

So it changes what the sample looks like and what an accuracy figure over it
means. **Your call** — I am not going to build a pool shaped by a guess about the
labelling task. If you want them, say so and say how many, and I will produce
thread-level items with the flattened text and the `offset_map` so a labeller sees
exactly what the extractor sees.

## 4 · One correction that changes the stratum from empty to trustworthy

**The 43 was noise, and noise is worse than empty.** Substring containment
reported 43 two-surface candidates; `re.finditer` with `\b` on both ends reported
**2**, and **40 of the 41 dropped were `pro` inside "problem" and "process"**.

An empty stratum says *look somewhere else*. A stratum of 43 rows where 41 are
`pro`-in-`problem` says *here is your sample*, and a labeller works through it
before anyone asks what matched. So the zero is not just honest, it is the version
of the number that could be acted on.

**Second instance of that class.** The first was `resolve()` matching `free`
inside *"freeze"* and `fusion` inside *"confusion"* — invisible on an AI corpus
until the movie-post control ran, and quoted in CLAUDE.md as the reason code-only
extraction was refused. Now recorded as shape 5a in
`docs/engineer-1/defect-shapes.md`, with habit 12.

**And the reason it cost you 41 of 43 and cost me 1 of 23 is the surface list, not
the corpus.** My re-run moved 23 → 22 because **every one of the 105 alias
surfaces in `model_alias` carries a digit** — `gpt-4`, `opus 4.8`, `haiku-4.5`
cannot hide inside an English word. Your pool included `pro`, a bare word. That is
the same fact as the 0-of-41 family-surface measurement from the other side: the
tracked-set artifact holds no digit-free surfaces, so the seated population is
structurally immune to a defect your pool was fully exposed to.

**Which means containment is safe only until one bare family word enters the
list** — one reviewer accepting one `family_surface`. That is a reason to fix the
matcher in both places rather than to rely on the surface list staying clean.
