# What GitHub needs before a sweep: a renderer, 32 requests, and a ceiling

**Three questions, measured on 1,019 harvest runs and 44,848 candidates.** The
renderer answer is strong, the comment answer is cheap, and the scale answer is
the one that should change what we do next.

*Engineer 1 · 2026-08-28. Report before building, as asked.*

---

## 1 · The renderer: hyphenate, and keep the concatenated form as a low-priority tail

Not a rule — a measurement over every GitHub run ever made:

```
surface form                  runs   fetched   kept   per run
hyphenated                     551    40,909    173     74.2
concatenated-with-numeral      436     2,439      8      5.6
other (spaced, etc.)            32     1,500      0     46.9
```

**Hyphenated returns 13.2× more per request.** `claude-sonnet-4.5` and
`sonnet-4.5` fetch ~100 each; `claudesonnet4.5` fetches **0** on run after run.

### The part that stops this being "drop the concatenated form"

Uniqueness, per document rather than per request:

```
found ONLY by concatenated     4
found by both                  0
found ONLY by hyphenated      48
```

**4 documents exist only because the concatenated form ran.** So it is not
waste, it is *expensive*: 109 requests per unique document against hyphenated's
11.5, a 9.5× cost difference. And "found by both = 0" is itself the finding —
the two forms retrieve **disjoint sets**. They are not redundant, they are
differently productive.

### What the renderer should emit, per surface

```
1  hyphenated, vendor-qualified      claude-sonnet-4.5      first, always
2  hyphenated, bare                  sonnet-4.5             first, always
3  concatenated-with-numeral         claudesonnet4.5        LAST, and only when
                                                            the search budget is
                                                            not the binding
                                                            constraint
4  spaced, WHERE A TRAILING NUMERAL  claude sonnet 5        never emitted — it
   WOULD COLLIDE                                             collects issue #5,
                                                             89 of 123 results
```

**Correction to an earlier draft of this section, which said "spaced: not
emitted, 0 kept in 32 runs".** That conflated two populations. `github_alias_form`
deliberately KEEPS a space where no trailing numeral collides — `gpt-4.1 mini`
renders unchanged, because the numeral is not the last token — and that
reasoning is sound and untouched. The 32-run "other" bucket in the table above
is aliases with neither a hyphen nor a letter-digit boundary, which is a
different set from "spaced aliases in general". n=32 is also too small to
retire a form on. What is retired is the spaced form **of an alias ending in a
numeral**, and that was retired on the issue-#5 measurement, not on this one.

**Why this is a priority order and not a filter.** Rule 8: a check whose error
rate has not been measured against a population it did not choose ships as a
weight, never a gate. Here the error rate *has* been measured — 4 documents in
436 runs — so this is a weight with a number attached, and dropping form 3
entirely would discard a measured 7.7% of the corpus to save requests we are
not currently short of. Emit it, rank it last, and let the budget decide.

**Contrast with Reddit, because the same alias needs opposite treatment.**
Reddit needed the vendor's own marketing spelling — `qwen3.8-27b` hyphenated
matched 116 of 175 titles against 42 for the spaced form, because that is how
the vendor's announcement wrote it and how people copy it. GitHub's preference
is about the **index**, not about convention: the search tokeniser splits on
hyphens, so a hyphenated alias becomes matchable terms while a concatenated one
is a single rare token that matches nothing.

**So the renderer cannot be one function with a platform flag.** Reddit asks
*"how do humans write this"*; GitHub asks *"how does this tokenise"*. Same
alias, different question, different answer.

## 2 · Comment fetching: 32 requests, and it does not compete with search

```
github documents             80
with >= 1 comment            32
comments in total           159
per commented issue          median 3, max 46
```

Every one fits in a single page at `per_page=100`, so the whole current corpus
is **32 requests** on `GET /repos/{owner}/{repo}/issues/{n}/comments`.

**It rides the existing sweep and costs it nothing**, because the buckets are
separate and `github.py` already says so from a measured `GET /rate_limit`:

> *"search **30/minute**, core **5,000/hour**. They are separate buckets, so
> they get separate limiters."*

Discovery is search-bucket. Comments are core-bucket. **32 of 5,000 per hour is
0.64%**, and the core bucket is otherwise used only for issue-body fetches.

At scale the shape holds: a 1,000-issue corpus at the observed 40% commented
rate is ~400 requests, still 8% of one hour. **Comment fetching is never the
constraint on this platform** — which is exactly the opposite of Reddit, where
132,442 unread comments are a real cost.

### What it buys, and it is the thing n_eff counts

`coverage_ratio` is **0.0 on all 71** GitHub contexts, with 149 comments
recorded as `hidden_children_min`. Each comment is a potential distinct author,
and `n_eff` counts *voices*, not claims — one engineer posting five times is
one voice. An issue thread is where a *"same here, on 4.8 as well"* lives, and
that is a second voice on a cell rather than a second claim on one voice.

**Do it. It is the cheapest voice-count improvement available on any platform.**

## 3 · Scale: GitHub is structurally thin, and the ceiling is close

```
distinct query_keys            591
runs                         1,019      (1.7 per query — mostly repeats)
candidates fetched          44,848
kept                           181
documents surviving             80
pooled keep rate             0.404%
queries that ever kept anything  88 of 591  (15%)
```

**85% of the query set has never produced a single kept document.**

### The ceiling, and it is arithmetic rather than a worry

`max_pages = 1` and `PER_PAGE = 100`, so **each distinct query can ever return
at most 100 candidates**. The current query space is therefore capped at

```
591 queries x 100 = 59,100 candidate slots
44,848 already fetched          = 76% consumed
~14,000 remaining               x 0.404% = ~57 more documents
```

**Re-running the existing sweep to exhaustion yields roughly 57 more documents.**
Not 500. The 1.7-runs-per-query figure says we are already mostly re-fetching
the same top-100.

### Breaking the ceiling requires fixing a storage defect first

Raising `max_pages` is the obvious move and `github.py` warns against it in its
own heading:

> *"**Only page 1 is stored**… Raise `max_pages` and hits from pages 2+ are
> sieved and never written: still filtered, no longer recoverable without a
> re-search."*

So `max_pages=5` would give 295,500 candidate slots and ~1,190 documents at the
current rate — and would silently destroy the recoverability property that makes
a widened sieve cheap. **`discovery_ref` is singular and would have to become
plural.** That is a schema change and a real piece of work, and it is the
prerequisite for GitHub at scale rather than a nice-to-have.

## 4 · What this means for the tier ruling, and it is the honest headline

**GitHub is thin, and that makes the tier ruling matter more, not less.**

At 0.404% and a query space 76% consumed, the realistic near-term GitHub corpus
is **80 documents now, ~137 after exhausting the current queries**, and ~1,200
only after a schema change. Meanwhile:

```
n_eff 3.0 at tier D   ->  138 voices on ONE cell
n_eff 3.0 at tier B   ->   13 voices
```

**137 GitHub documents cannot produce 138 voices on a single
(model, capability, condition_bucket).** Not approximately — the whole corpus is
smaller than one cell's requirement. So no amount of GitHub retrieval publishes
a cell while the tier mapping stands.

Under a tier-B mapping, 13 voices on one cell is reachable from a corpus this
size *if* comment fetching lands, because comments are where the additional
distinct authors are.

**That is the dependency in one line: comment fetching is worth doing now and
is cheap; more retrieval is not worth paying for until the tier ruling lands;
and the ceiling fix is only worth doing if the answer is that GitHub is the
channel we are betting on.**

## 5 · What I would build, in order

```
1  the per-platform renderer, GitHub arm     priority order above, form 4 dropped
2  comment fetching                          32 requests, rides the core bucket,
                                             turns coverage_ratio 0.0 into a real
                                             number and adds distinct authors
3  NOTHING ELSE until the tier ruling        ~57 more documents is not worth a
                                             sweep, and 1,190 needs a schema
                                             change nobody has agreed to
```

Items 1 and 2 are both this lane's and neither needs a contract change. Item 3
is a decision, not a task.
