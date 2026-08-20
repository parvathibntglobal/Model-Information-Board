# The measurements that changed a decision

Ten measurements, each of which **reversed a design decision rather than
confirming one**. Eight of the ten reversed something already written and
shipped, which is the argument for measuring earlier rather than for measuring
more.

*Verified against `origin/main` at `225b126`. Figures are cited to
`docs/measurements/`, not re-derived, except where marked **re-derived**.*

---

## How to read every figure here

Rule 7 applies to all of them, so each entry has the same four parts:

| | |
|---|---|
| **the figure** | the number, as it should be quoted |
| **the population** | what was counted, how it was gathered, and when |
| **what it changed** | the decision that was different afterwards |
| **what it does not support** | where the number stops being evidence |

The fourth part is the one that earns the format. Three figures in one fortnight
turned out to be measuring the instrument rather than the world, and each was
load-bearing in an argument before anybody checked what it counted. The method
that catches it is in `docs/measurements/README.md` and costs two API calls:
**vary the query, not the world.**

**The corpora are gitignored.** `_substitution_slice/`, `_unfiltered_sweep/`,
`_control_sweep/`, `_blog_so_sweep/` and `raw_store/` are on one machine. A
clone reproduces none of them, and the 285-document store behind §4 is already
gone. Nothing here was re-run for this document except where it says otherwise.

---

## 1 · Phrase binding — the one that invalidated a whole file

**The figures.**

| probe | result |
|---|---|
| `(a OR b)` grouping, `wildcard*` on GitHub | **silently discarded.** No error. Nine of ten templates exceeded the 1,000-result ceiling at a median of **13,038** matches |
| `"claude sonnet 5"` vs `"sonnet claude 5"` | **540 vs 545**, near-total overlap |
| `"claude sonnet 5"` vs `"claude sonnet 7"` at `org:openai` | **123 vs 96** — a version numeral nothing uses returns plenty, because it matches the *issue number* |
| `"gemini flash" "dropped a detail"` | 8 results, **7 contain the phrase nowhere** |
| 19 quoted phrases on Reddit | phrase present in **43% of 357 posts**; every post carries ≥1 word, ~a quarter carry all |
| 44 `"phrase" alias` queries | appended alias present in **7% of 2,031 posts**; Jaccard 0.00–0.01 against the bare phrase; phrase containment **degrades** 43% → 32% |

**The population.** GitHub Search and the Reddit RapidAPI proxy, 2026-08-13 to
2026-08-17, probe queries issued deliberately. Not a corpus — a set of controls,
each chosen so that a null result and a positive result mean different things.

**What it changed.** Twelve rendered query templates were **deleted from
`contract/queries.yaml`**, and the file now carries term sets as data with no
query strings at all. The `subject`/`topic`/`signal` split, the sieve's existence
as the largest module in the lane, and `direction: decided_at_extraction` all
descend from this. `harvest.yaml`'s "narrower scope" budget lever was removed as
inert by the same kind of probe: one repo and two repos both cost 896 requests.

**What it does not support.** It says nothing about *recall* — only that
adjacency, word order and therefore direction are not expressible in a query on
either index measured. And two figures from this family were **misread for a
week and are the reason the fourth column exists**: `"context window"` present
in 96% of 248 posts and `"went back to"` in 100% of 75 were read as evidence of a
phrase operator. They were measuring **collocation frequency** — a common
English pair is returned by relevance ranking whether or not anything honoured
the quotes. The variant probe settled it: 19 enumerated looser forms, 0 hits on
three families.

> The flag in the contract was renamed from `phrase_binding` to
> `decided_at_extraction` for exactly this reason. The old name asserted a cause
> the measurements contradicted — it implied *some* index binds phrases, and none
> that has been measured does.

---

## 2 · Reddit's rate limit — folklore, and wrong in the unsafe direction

**The figure.** **429 after 32 rapid calls**, message *"exceeded the rate limit
per minute for your plan, PRO"*, clearing in ~60s, **with no `Retry-After`
header**. Monthly quota triple read in full: limit 1,000,000, remaining 998,660,
reset 2,064,366 s = **23.893 days**. **Exactly 1 unit per request**, confirmed
over 558 requests and per individual call over the last 186.

**The population.** One live probe, 2026-08-14, plus header capture on every call
since. All 16 response headers captured; the monthly triple is the only
rate-limit family present.

**What it changed.** `collect/CLAUDE.md` said **60 req/min**, and four other
files attributed that number to `BUILD-PLAN.md`, **which has never contained it
in any commit**. 60/min would have failed in the first minute of every sweep. The
working figure is `SEARCH_PER_MINUTE = 25`, chosen *under* the break point rather
than at it. The docstring's "~28 days" was wrong by four days, which mattered
because five documents cited that line as their source.

**What it does not support.** **32 is where it broke, not what the plan
permits.** No header states an allowance, so the allowance is *unread*, and
writing 32 — or 25 — anywhere as "the limit" would convert an inference into a
recorded fact. And the gateway's 1,000,000 is not proof of the billed tier: the
plan page says 500,000, and no request can settle that, because the value would
come from the party in doubt.

> The shape worth keeping: **the constant was right and the method was wrong**,
> which is the outcome least likely to teach the lesson. Same shape as the
> extraction token estimate that was right for the wrong reason.

---

## 3 · Alias surfaces — the hand-written list, measured instead of imagined

**The figures.**

```
anthropic/claude-opus-5     primary `claude opus 5`      0 mentions
                            variant `opus 5`         1,445 mentions
anthropic/claude-sonnet-5   primary `claude sonnet 5`    0 mentions
                            variant `sonnet 5`         166 mentions

surfaces per discussed model    min 1 · median 2 · mean 2.01 · max 4
the 11 hand-curated models      5.5 each — about 2.75× what the corpus attests
`attested-gap`                  62 surfaces, 4,556 mentions — the largest
                                verdict by mentions, and it is ONE rule
family words with no version    16,174 of 25,928 — 62%
```

**The population.** 5,546 stored Reddit documents, 340-model registry,
2026-08-17, no fetch. 10,255 attested mentions over 449 surfaces; **7,202
attributable** over 145 surfaces, where attributable means the `resolved` and
`attested-gap` verdicts, which name exactly one registry model each.
`attested-gap-ambiguous` (49 surfaces, 1,530 mentions, 2–25 candidate models
each) and `unknown-model` (255 surfaces, 1,523 mentions) are **excluded**, so
every per-model count is a **lower bound**.

**What it changed.** Three things. `alias_rows` had asked a human for the prose
forms a model is discussed under — judgement supplied from imagination, because
there was no corpus. Now: the vendor-drop rule (`claude-opus-5` → `opus 5`) is a
**third proposer input**, derived from a measured rule and kept apart from
attestation, because `opus 4.6` at 398 mentions is a fact about that model and
`fable 5` is a fact about the rule. The `family_surface` slot became a permanent
`INCOMPLETE` rather than a gate. And #33 was ruled: **the spelling floor stays at
three and keeps counting renderings, never attestations** — a floor counting
attested surfaces would fail 55 of 72 models, and every failure would be fixed by
somebody inventing a spelling. **A check whose remedy is fabrication is worse
than no check.**

**What it does not support.** Reddit prose only. A GitHub issue names a model in a
config line, where the id spelling is the likely form and this corpus finds id
spellings unattested — so the variants it finds unattested may be exactly what
the other two channels use. The detector needs a vendor or family word followed
by a version token, so `deepseek r1` is **not measured**, not measured at zero.
**268 of 340 registry models are absent from the extract: recall unmeasured.**
And the headline *"82% of hand-written surfaces never observed"* was withdrawn
before anybody used it — it compared one platform's prose against a list built
partly for another platform's configs.

> **Re-derived for this document.** The committed extract
> (`fixtures/openrouter/observed-surfaces.json`, 449 rows) folds to 72 models and
> **7,202 attributable mentions**, and reproduces the rank bands in §9 exactly.
>
> **Not confirmed — the 5,546 documents.** They are not in the database:
> `document` holds **30 rows, all blog** (queried 2026-08-20). So every mention
> count here is confirmed **at the extract** and unconfirmable **at the source** —
> nothing available can re-run the detector, check its recall, or find the
> document a surface came from. That bears hardest on the two measured zeros,
> which are the only claim in this entry resting on the detector having *looked*
> rather than on arithmetic over what it recorded.

---

## 4 · The specificity backfill — and a defect in the thing being measured

**The figures.**

| | github | blogs | both |
|---|---|---|---|
| n | 174 | 111 | 285 |
| floor clear rate | **98.9%** | **82.0%** | **92.3%** |
| `names_version` | 48.3% | **6.3%** | 31.9% |
| `has_error_strings` | 42.0% | **3.6%** | 27.0% |
| `has_code` | 91.4% | 54.1% | 76.8% |
| `has_numbers` | 50.0% | 56.8% | 52.6% |
| `has_conditions` | 20.7% | 16.2% | 18.9% |
| mean composite | 0.527 | 0.286 | — |

**The floor drops 7.7%.**

**The population.** 174 GitHub candidates and 111 blog articles re-scored from the
raw store, 2026-08-17, no fetch — **under the 59 hand-written alias surfaces
loaded that day.**

**What it changed.** Three decisions. `docs/logic-and-workflow.md` credited "the
hard gates plus the specificity floor" with removing the overwhelming majority of
junk; the floor removes 7.7%, so **it is a backstop and not a filter**, and if
survival is to reach 10–15% the hard gates have to do nearly all of it — which is
why the hard gates were built next. #24 was ruled from the channel split: **the
composite may not compare across channels, ever**, because `has_error_strings`
and `names_version` are 0.45 of the weight and both are largely a proxy for
*medium* (42.0% vs 3.6%, 48.3% vs 6.3%). A cross-channel sort by specificity is a
sort by "is this GitHub" with extra steps, and it would demote **the only
positive-evidence channel** — rule 4 arriving somewhere new. And the run found
`names_version` passing raw text to a matcher documented as taking normalised
text: it scored **1 of 111 blog articles where the figure is 7**, with all 45
tests passing because every one used a lowercase model name.

**What it does not support.** The 7.7% **is not reproducible**: the floor takes
`version_aliases` as a parameter, so the same documents give **3.8%** under those
59 surfaces and **0.8%** under the 1,337-surface registry union — a factor of
four, identical documents. **That raw store no longer exists on any machine.** It
remains the only calibration this stage has, which is the reason to state its
parameter rather than quietly retire it.

### 4a · The term-group yields, over the same 285 documents

| group | terms | matching nothing | top term's share |
|---|---|---|---|
| subject | 59 | **30 (51%)** | `gemini-2.5-flash` at 28% |
| topic | 88 | **25 (28%)** | `context` at 13% |
| signal | 207 | **186 (90%)** | `good enough` at 19% |

**11 of 26 query entries have no signal term that matched anything** — a
capability query whose entire signal group is dead cannot produce a claim from
this corpus at all, which is the empty-cell failure one layer earlier than the
gate.

**What it does not support.** 285 documents is small: `should have been null`
matching zero of them is weak evidence that the term is dead and strong evidence
only that the corpus is small. **Treat the zero list as a candidate list, not a
deletion list.** And the GitHub half is narrower than it looks — those 174 were
retrieved for three capabilities and one model, so signal terms belonging to the
other eighteen entries never had a fair chance there. The blog 111 are
unfiltered, so blogs are the fairer test of recall.

> **Not confirmed — there is no three-channel yield measurement.** Reddit has
> never been sieved for per-channel yield. The channel comparison above is two
> channels, and the third is inferred from the alias extract (§3), which is a
> different question measured on a different corpus. Anybody quoting "the
> per-channel yields" is quoting GitHub and blogs.

---

## 5 · Dedupe — the number survived and the design did not

**The figure.** MinHash + LSH separates duplicates from strangers **better at
every length**, including the long bands simhash was specified to own.
**simhash's margin at 400–800 tokens is one bit of 64.** Re-run in simhash's
conventional word-3-gram tf-weighted form, its margins were 0–12 bits.

**The population.** 6,824 stored documents; **79 ground-truth duplicate pairs**
and 951 stranger pairs drawn from 3,767 Reddit documents, 2026-08-17.

**What it changed.** `collect/CLAUDE.md` specified **two methods** — MinHash below
~200 tokens, simhash above, on the reasoning that simhash is built for long
documents. The two-method design is gone and **`document.simhash` stays NULL as a
measured decision, not an unimplemented column.** `min_tokens_for_signature: 200`
survived, but it now means something different: a **floor** below which no
signature is computed, not a switch between methods. The band the data supports
is (50, 200); 200 is the top of it, chosen because over-merging destroys
corroboration and a higher floor merges fewer documents.

**What it does not support.** 79 true pairs is thin, and **all of them are Reddit
self-syndication and crossposts.** The corpus contains **no blog syndication at
all** — and FR-16's own example is *"one blog syndicated four times"*, so the
channel the requirement is about is unmeasured. The two bands between 50 and 200
carry n=2 and n=4 true pairs, which is too thin to claim either way. Nothing here
says anything about the cross-platform case FR-17 is about: **zero exact-duplicate
groups spanned two document kinds.**

---

## 6 · The blog symbol census — both candidate rules were wrong

**The figure.** **Zero of the five entities** reached the flattener across 53
articles / 519,997 characters. My own counter-examples — `°`, `©`, `®`, `™` —
occurred **zero** times. The dominant symbol class is **box-drawing characters
inside fenced code blocks**, from **2 documents out of 106**.

**The population.** Two populations, and mixing them differs by a factor of two,
so each figure says which: **A** = 53 articles / 519,997 chars, under the
per-feed cap of 8; **B** = 106 articles, every one the fetch path stored,
re-extracted with no network calls. 9 feeds, live, 2026-08-18. Two feeds returned
no articles and it is not a failure — they are `blog-class-b-medium`, whose
ruling sets `fetch_articles: false`.

**What it changed.** `FlatteningRules` became **per-platform**, with
`decode_entities = False` for blogs, because trafilatura has already decoded and
**decodes twice** (isolated against bare lxml: `type &amp;gt; here` → `type >
here`). And it stopped a second change from being made: the `So` symbol rule was
**not** narrowed, because the corpus refused both candidate replacements.
Narrowing from a corpus of two would have repeated the original mistake in the
other direction.

**What it does not support.** *"Rules are wrong"* is a **severity** finding here,
not a frequency one — 2 documents of 106 is not a rate, and the reason it matters
is that substitution inside a fence destroys a directory tree. And the entity
finding does not make blog text safe: it makes this module's entity pass a no-op
in the ordinary case and **a third decode** where it is not. Rule 1 cannot catch
that, because both sides of the check sit downstream of the decode
(`how-it-works.md` §5.3).

---

## 7 · The population problem — a verdict that is not a property of the document

**The figure.** Same 1,297 documents, same code, only the surfaces differ:

| population | surfaces | survival | entity gate drops |
|---|---|---|---|
| hand-written, 11 seeded models | 59 | 53.4% | 552 |
| registry union | 1,337 | 83.1% | 105 |

**385 documents — 29.7% of the corpus — change verdict on the alias population
alone**, with nothing about any document different.

**The population.** 1,297 distinct Reddit posts recovered from 120 raw payloads in
`_substitution_slice/`, retrieved 2026-08-17 by the substitution sweep.
**Every post was retrieved by a query containing model names**, so the corpus is
pre-filtered for exactly what the entity gate tests.

**What it changed.** `SurfacePopulation.fingerprint` exists because of this
number. A triage verdict is **not reproducible from the document** — it is
reproducible from *(document, population)* — and `pipeline_version` cannot
substitute, because this gate's answer changes when the registry grows without a
line of code changing. Two runs at the same `pipeline_version` can legitimately
disagree. It also settled that the **declared** surface list is not redundant: 27
hand-written surfaces are reachable by no derivation (`flash 2.5`, `r1`,
`mistral large 3`), and a registry-only population rejects 39 documents naming
`deepseek r1`.

**What it does not support.** Neither survival figure calibrates anything. Two of
six gates never ran, and the corpus was retrieved by model-name queries. It ranks
the gates against each other and exposes the population effect; **it calibrates
nothing**, and the 83.1% has since moved twice (§8).

---

## 8 · The retrieval bias — 58.1 percentage points, and the control that earned its place

**The figures**, identical code, identical gates, identical surface population,
after both fixes below:

| corpus | what it is | survival |
|---|---|---|
| **A** | model-name-retrieved slice, 1,297 Reddit posts | **78.0%** |
| **B** | unfiltered, 26 AI subreddits × 75, no query terms | **19.9%** |
| **C** | Tier 1 general-technical control (programming, webdev) | **0.4%** |
| **D** | Tier 2 non-technical control (movies, cooking, AskReddit) | **0.0%** |

**retrieval bias A → B: 58.1pp · topicality bound B → C: 19.5pp**, so **19.5 of
B's 19.9 points are topicality** and the pipeline's own discrimination on a
technically-literate population is 0.4%.

**The population.** B: 1,925 posts over 11 subreddits × 175 in the first sweep,
then 26 × 75; `/getPostsBySubreddit`, sort `new`, no query terms, 2026-08-18, 78
calls. C and D: 750 control posts, 30 calls. **Survival within those
subreddits** — never survival over Reddit, which is not sampled. Every basis for
choosing subreddits biases upward.

**What it changed.** Two code fixes and one ruling. **The entity matcher crossed
word boundaries**: `saba` matched inside "wa[s a ba]d", `fusion` inside
"con[fusion]", `free` inside "[free]ze". Space-stripping is load-bearing and
could not be dropped, so `normalize_with_boundaries` now removes separators for
matching and *remembers* them for bounding. And **routes were ruled not to be
models**, worth 10.6 points of B's survival on its own. It also killed the
practice of quoting a survival figure from a search corpus: **every one ever
published was too high by roughly a factor of 2.5**, and a 2σ baseline built on
one would have been calibrated against a population that does not exist.

**What it does not support.** Both remaining figures are still **upper bounds** —
three of six gates do not exist. And the sampling lesson is larger than the
figure: the design report predicted a design effect of 1.5–3 and sized n=2,000
against it; **measured, it is 14.5**. Survival by subreddit ranged from **15.4%
(r/singularity) to 59.4% (r/LocalLLaMA)** over 175 posts each. **Effective n is
132, not 1,925**, and the 95% CI widens from ±2.1pp to **±7.9pp**. The subreddit
is the unit of variation, so more pages buys almost nothing and more subreddits
is the only thing that buys precision — and the subreddit list is now the
dominant uncertainty.

> **This is the entry to read if you read one.** The predictions were committed
> **before** fetching — Tier 2 under 1%, Tier 1 at 3–8% — and both missed in the
> same direction (5.0%, 17.8%). Tier 1 alone would have read as *"the technical
> control is higher than expected, interesting"*. **Tier 2 at 5% on posts about
> movies is not interesting, it is broken.** The control found a real defect by
> failing its own prediction, on the first run, and Tier 2 at exactly 0.0% now is
> the first demonstration that these gates can return a true zero.

### 8a · The figure trail, so an older number can be reconciled

| corpus | before either fix | boundary fix only | + routes excluded |
|---|---|---|---|
| A · model-name-retrieved | 83.1% | 81.5% | **78.0%** |
| B · unfiltered | 33.7% (11 × 175) | 29.8% | **19.9%** (26 × 75) |
| C · Tier 1 | 17.8% | 9.1% | **0.4%** |
| D · Tier 2 | 5.0% | 1.3% | **0.0%** |
| bias A → B | 49.5pp | 51.7pp | **58.1pp** |

### 8b · The survival ceiling — quoted as current, marked stale

> **Not confirmed — the ~23.8% E4 ceiling.**
> `docs/proposals/extraction-budget.md` §3 lists it in a table headed *"three
> measured figures"*, between 19.9% and 78.0%. It is **not a third
> measurement**: it is a projection of what all six gates plus the floor would
> remove, and `docs/measurements/control-and-reshape.md` §6 explicitly marks it
> **"to be re-measured"** after the two fixes in §8. So one document carries it
> as stale and another quotes it as current, and I could not reconstruct its
> derivation from either.
>
> Two things follow. The budget sized on it is unaffected, because the budget
> must use **78.0%** — the search path is what the nightly sweep runs, and
> budgeting on 19.9% would set a limit 3.9× too low and degrade extraction to
> triage-only on an ordinary night. And **a figure marked stale in the document
> that owns it, quoted as current in the document that uses it, is the drift
> shape this directory exists to interrupt.** Re-running the ceiling is on the
> list in `control-and-reshape.md` §7.

---

## 9 · The tracked set — the count came from the corpus, not the budget

**The figures.**

```
900 daily requests / 81.45 per model = 11 models a night
340 in the feed → a full rotation takes 31 days, against a 30-day half-life
  on ops.latency_ttft — the sweep loses to the decay curve

rank band   mentions added   share of 7,202
  1-10           4,840         67.2%
 11-20           1,336         18.6%
 21-30             571          7.9%
 31-40             268          3.7%     ← flattens here; marginal model = 21
 41-50             117          1.6%
 51-72              70          1.0%
```

Ranks 1–40 carry **97.4%**. A floor of **20 mentions** covers 97.7%.

**The population.** The 7,202 attributable mentions of §3 — Reddit prose only,
lower bound, 2026-08-17 — against the 340-row registry.

**What it changed.** The count stopped being a round number. *"50"* had been
proposed; the curve put it at 40-odd and the floor at 20, and the staleness bound
affords 77, **so the budget is not binding and the number can be argued from the
corpus.** It also fixed the ranking key: **by mentions, not by release date**,
because 11 of the 340 ids are `~vendor/…-latest` pointers whose `release_date` is
when the pointer moved. A date sort seats those and drops
`anthropic/claude-sonnet-4.5`, sixteen months old and still discussed. And
`mentions = None` means **unmeasured, never 0** — 268 of 340 models are absent
from the extract, so an unobserved model is *unrankable* and can enter only by
the launch-window rule.

**What it does not support.** It ranks **Reddit discussion**, not importance,
quality or use, and it will under-rank models discussed mainly in GitHub issues —
where the naming convention differs and this detector is blind to it. **The
discussed population is 72**, which is the ceiling on ranking by mentions: a
target of 77 cannot be filled by this measurement even in principle.

> **Re-derived for this document**, against the live registry: the rank bands
> reproduce exactly. The **count does not** — `select()` returns **63** at the
> published `as_of` of 2026-08-18 and **62** at 2026-08-20. The first difference
> is the route ruling, which postdates the measurement; the second is the launch
> window sliding by two days. `docs/measurements/tracked-set.md` says 64. **A
> tracked-set count needs its `as_of` the way every other figure needs its
> population**, or it drifts downward on its own and looks like attrition.

---

## 10 · The substitution zero — the most instructive figure, because it was not one

**The figure.** `substitution_kept: 0`.

**What it actually was.** **Unknown, not zero.** The probe took
`entry.terms.topic[0]` — one topic term per entry. The negative entry's first
term is `switched back`, which carries no `{alias_b}`, so **all four model pairs
rendered the same query and the run measured one query four times.** The positive
entry used 1 of its 6 terms.

**Re-run properly:** 146 queries, 1,678 distinct Reddit documents, 9.5 minutes —
and still nothing passed the sieve, which made the zero a **measured** zero for
the first time. Then re-sieved against the corrected term shape: 168 queries,
1,297 distinct documents, **0 → 2 documents on version-only surfaces, 1 → 4 with
surfaces as declared.**

**The population.** Reddit via RapidAPI, 2026-08-17. Two runs, and **they are not
paired**: the first run's 1,678 documents are gone — its script was never
committed and its corpus lived in a scratch database since reset. So the second
is a *re-retrieve and sieve*, not a re-sieve. Two seed models retired between the
runs, so 8 were live rather than 10.

**What it changed.** `scripts/substitution_slice.py` is committed, in two stages,
so the next shape change costs zero requests. `subject` now requires **both**
aliases, because `replaced {alias_b}` in `topic` measured **0% containment** —
the noun phrase between verb and model is unbounded ("replaced our X
deployment", "replaced the X calls"), and no enumeration reaches an unbounded
gap. Requiring both models is what lets `topic` stay loose.

**What it does not support.** 4 documents is not a yield rate. And the reason this
entry is here is not the number: **a zero from a harness nobody has shown can
produce a one is indistinguishable from a broken harness.** The control that
caught it was one synthetic document pushed through all four term shapes, and
every measurement in this file that reports a zero now states whether the
instrument could have seen a one.

---

## Figures this lane depends on and did not measure

Recorded so they are not read as ours.

| figure | whose | what to know |
|---|---|---|
| extraction tokens **2,010 in / 589 out**, $0.00208/thread | E2's first live run | **n = 3 calls against ONE thread.** The old estimate was right for the wrong reason — two errors in opposite directions partly cancelled, so a 13% agreement on cost validates nothing. No artifact of the run is in the tree; it ran against a disposable local instance on purpose |
| **8 proposed / 8 verified / 0 rejected** | E2, same run | after two schema defects were fixed. The first real evidence that the offset map and the flattener agree with a real model |
| **5 NOT NULL mismatches** between the migration chain and `tables.sql` | E2 | all in one direction — the chain is **stricter** than the declaration, so the drift is uniformly conservative. Not reproduced here; recorded because the direction is the part that stops being true first |
