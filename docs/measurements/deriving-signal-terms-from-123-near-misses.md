# The 123 unselected near-misses suggest a direction, not a list — and the reason is structural

**No term is proposed here.** The first pass returned link-blog navigation, the
second returned topic nouns, and the reason neither returned signal terms is the
same reason the 8★ layer ships as a weight: **the rarity that makes a signal term
valuable is what makes it invisible to a frequency count on 123 documents.**

*Engineer 1 · 2026-08-28 · read-only, no model call. GitHub's 504 deliberately
excluded — see §1*

---

## 0 · The population, and a correction to my own count

```
corpus                    documents   near-misses   population kind
Blog articles (flattened)       190        35        UNSELECTED
Reddit listing (today)        2,000        88        UNSELECTED
                                          ---
                                          123
```

**123, not the 126 I reported.** The earlier figure counted a document as a
near-miss if *any* (surface, entry) pair near-missed, even when another pair
passed. A document that already yields a claim is not material for deriving terms
we lack, so this pass excludes it: near-miss now means **near-missed and passed
nothing.** Reddit moves 91 → 88, blogs stay 35.

## 1 · Why GitHub's 504 are out of the first pass

Every GitHub candidate is in the corpus **because it matched an alias query**,
and 63.9% of them clear the subject group against 23.7% on blogs and 10.9% on
Reddit. Its near-misses are therefore drawn from documents already selected by
the vocabulary we are trying to extend, so deriving from them recovers what we
have rather than what we lack. They are richer material for a *second* pass,
once there is something to compare against.

## 2 · The first pass returned boilerplate, and that is a method finding

Document-frequency n-grams over the 123, excluding existing terms:

```
16  wildly overthinking things        <- the only behaviour predicate in the top 20
16  things th august
15  openai accidental attack
15  against hugging face
15  face th august
15  recent articles
10  raccoon heist game
10  one-shotting raccoon heist
```

**Fifteen of the 35 blog near-misses share "hugging face" because one link blog
cross-references one story.** `author_prose()` strips code, quotes and URLs — it
does not strip site navigation, and the per-feed `template_block` rules that
would are **not applied to these flattened texts**. Four of nine feeds are still
`status: unverified` on those rules, so the stripping cannot simply be turned on.

So: **the near-miss corpus needs template stripping before it can be derived
from**, and that is a prerequisite nobody had costed.

## 3 · The second pass returned topic nouns, not signal terms

A cross-corpus filter — keep only phrases appearing in **both** blog and Reddit
near-misses, on the reasoning that a phrase used on two platforms is unlikely to
be one blog's boilerplate:

```
1-grams (1,871 survive)   out, work, while, because, run, prompt, through,
                          running, something, without, coding, actually
                          -> function words. Nothing usable.

2-grams (127 survive)     tool calls, coding agents, reasoning tokens,
                          reasoning effort, reasoning levels, follow-up prompts,
                          single prompt, before committing, figuring out
                          -> TOPIC nouns, with two exceptions
```

**Almost everything that survived is topic-shaped, and topic already hits.** The
near-misses are documents where topic *fired* and signal did not, so a phrase
common enough to survive a frequency filter across 123 documents is, almost by
definition, the topic language that already worked.

## 4 · The structural reason, and it is the 8★ argument again

A signal term is a **predicate about behaviour** — `truncates at`, `returns
empty`, `loses recall`, `wildly overthinking`. Two properties follow:

```
they are SPECIFIC   an engineer describes one failure in their own words, so
                    fifty engineers produce fifty phrasings
they are RARE       any single phrasing appears in one or two documents
```

A frequency count needs a phrase in ≥3 of 123 documents to clear noise. **A
signal term that appeared in 3 of 123 documents would be a common phrasing, and
common phrasings are what we already have** — `truncat` alone supplies 34.2% of
all GitHub firings. The terms we lack are in the tail by construction, and a
123-document corpus has no tail.

This is the same shape as the 8★ weight decision (`docs/weight-before-drop.md`):
the property that makes the signal selective is what makes it unmeasurable at
this corpus size. **It is not an argument against deriving. It is an argument
that the corpus has to arrive first.**

## 5 · What the 123 DO establish

Three things, and none of them is a term:

**A shape, not words.** `reasoning tokens` / `reasoning effort` / `reasoning
levels` are three surface forms of one family, and `coding agent` / `coding
agents` differ by a plural the sieve's final-word stem already handles. So the
unit of extension is a **family with a stem**, not a string — which is what
`queries.yaml` learned once already, when 275 of 275 multi-word terms failed to
match their own plural.

**One real candidate, and it is worth naming precisely because it is one.**
`overthinking` appears as `wildly overthinking things` and `defaults to wildly
overthinking` across 16 documents. It is a behaviour predicate, it fits no
existing capability key cleanly, and it is the single term this whole pass
produced. **One term from 123 documents is the yield to plan against**, not a
list.

**And a prerequisite:** template stripping, per §2.

## 6 · Is 123 enough? No, and here is what would be

**It suggests a direction and it cannot produce a list.** Anyone building a gate
on the output of this pass would be gating on one term and a hypothesis about
shapes.

What would change it, in order of cost:

```
template stripping applied to near-miss text     needed regardless; 4 of 9 feeds
                                                 need their rules verified first
more UNSELECTED corpus                           nightly listing sweeps at 88
                                                 near-misses per run reach ~900
                                                 in ten nights. The sweep is now
                                                 wired, so this accrues for free
GitHub's 504 as a SECOND pass                    biased, and the bias is
                                                 measurable once an unselected
                                                 baseline exists to compare to
reading rather than counting                     see below
```

**The last one is the honest option and it needs a ruling.** Signal terms are
predicates, and finding predicates in prose is a reading task rather than a
counting one. Rule 2 permits exactly this shape — *an LLM may propose, it may
never decide* — so a model could propose candidate terms from near-miss text and
code could verify each against the corpus by exact match before any of them
reached `contract/queries.yaml`. That is the same proposer/checker split rule 1
rests on.

**I am not proposing it, because it adds a model call to a lane whose first line
is that it never makes one.** `collect/CLAUDE.md` opens with *"This lane never
calls a language model. Not once."* The near-misses live in `collect/`; the only
two stages permitted a model are `judge/extract/` and `judge/ask/`. So the
proposal would have to be a `judge/` stage reading a `collect/` artifact, which
is a lane question before it is a method one — and it is not mine to settle
alone.

## 7 · What I would do next, and it is not the derivation

**Nothing, and let the corpus accrue.** The listing sweep is wired into the
nightly chain as of today, so unselected near-misses arrive at roughly 88 a night
at no marginal cost. Ten nights is ~900, which is where a frequency count starts
to have a tail to look at.

The cheap work in the meantime is **template stripping** — needed regardless,
blocking on four feeds' `template_block` verification, and entirely within this
lane.
