# The seven, re-extracted: 8 claims again, 6 of them from vendor copy

**Ran against the pre-registration. It predicted 0 and got 8, which is
over-extraction rather than yield — and the eight land in almost exactly the
place `the-eight-claims-and-their-input.md` said they would, from the input
alone, before any of them existed.**

*Engineer 1 · 2026-08-20 · `postgresql://bv_agent@52.17.75.29:5432/Model-information-Board`*

---

## 0 · Two things that have to be said before any number

**`claude-opus-4.8` is seated and resolves.** `anthropic/claude-opus-4.8`, a
`polled`, `in_window` `model_version` row, owning 6 surfaces of the
registry-derived population.

**So is `claude-fable-5`, and that contradicts the premise this run was set up
under.** `anthropic/claude-fable-5` is also `polled` and `in_window`, owning 6
surfaces (`fable-5`, `fable 5`, `claude-fable-5`, `claude fable 5`, `fable5`,
`claudefable5`). It is not absent, and the denominator was not 415 either: the
population is **1,224 surfaces derived from 324 registry models** (fingerprint
`1c1d354d987f6d36`), or 1,245 with `seed_models.yaml`'s declared surfaces folded
in. Nothing in `docs/` holds a 415.

What is still true, and is probably what "fable-5 cannot resolve" was reaching
for: **bare `fable` resolves to nothing**, because it is one of the 26
`FAMILY_WORDS` that `_admissible` excludes. That is not a gap in the registry,
and it is not about `fable-5` — it is about the one comment in this corpus that
uses the bare family word, `oqocfjv`, which is also **the only first-hand
capability observation in the seven** and was invisible to this run for exactly
that reason. Same conclusion, different mechanism, and the difference decides
who fixes it.

**There is no prior to compare against.** `8 and 8` was measured pre-seat with
zero rows stored, and `6 and 5` was a sign inversion of *six proposed, five
rejected*. Neither is a baseline, so nothing below is stated as a delta.

## 1 · The population, and it is not the thirty

```
THE SEVEN     2 threads · 7 documents · 6 Reddit comments + 1 blog post
              mixed authorship, one vendor announcement
              pre-registration: 0 expected, for reasons of CONTENT
```

Not the thirty link-blog entries, which have their own pre-registration
predicting a bounded yield plus a template artefact for different reasons. Any
figure here stated beside a figure from those thirty has to name which one it
came from.

## 2 · What the run produced

```
thread_context_eacc17c8af367044   6 docs   8 proposed · 8 verified · 0 rejected
thread_context_d166d88fbb7b3c70   1 doc    0 proposed · no_claim_reason given
                                           ------------------------------------
                                           8 verified, 0 stored
tokens   3,525 in / 589 out over 2 calls
cost     $0.00253  —  0.25% of the $1.00 daily cap
```

**$0.00127 per call over n=2 calls on 2 threads.** The pre-registration costed
this at $0.00208/call from n=3 calls on one thread. Both are measured figures
with small populations; neither is a rate.

**The blog document was read correctly and produced nothing**, with a reason that
identifies why: it *"does not make any claims about the capabilities or
performance of any specific AI model"*. That matches the characterisation made
from the input, and it is the one place in this run where 0 was expected and 0 is
what came back.

## 3 · The eight, against the table

Judgement column is the exercise. **first-hand** = the author reports their own
observation; **relayed** = a real capability statement whose evidentiary weight
belongs to someone else; **over-read** = a true quote carrying a claim the
sentence does not support.

| # | quote | model | capability | pol | document | judgement |
|---|---|---|---|---|---|---|
| 1 | *"exceptional performance in software engineering"* | Fable 5 | `code.generation` | + | `reddit:t3_1u1b22l` | **over-read** — vendor announcement copy |
| 2 | *"the longer the task, the larger its lead over our other models"* | Fable 5 | `reasoning.multistep` | + | `reddit:t3_1u1b22l` | **over-read** — vendor copy, and the quote names no model at all |
| 3 | *"Without safeguards, Fable 5's capabilities in areas like cybersecurity could be misused to cause serious damage."* | Fable 5 | `over_refusal` | − | `reddit:t3_1u1b22l` | **over-read** — a misuse-risk sentence read as a refusal observation |
| 4 | *"when Fable's classifiers detect a request related to cybersecurity, biology and chemistry, or distillation, the response is handled by Claude Opus 4.8, our next-most-capable model."* | Fable 5 | `instruction.adherence` | + | `reddit:t3_1u1b22l` | **over-read** — describes ROUTING; the quote resolves only Opus 4.8, not the model claimed |
| 5 | same quote as 4 | Claude Opus 4.8 | `instruction.adherence` | + | `reddit:t3_1u1b22l` | **over-read** — being routed to says nothing about adherence |
| 6 | *"We'll keep refining the safeguards to reduce false positives."* | Fable 5 | `over_refusal` | − | `reddit:t3_1u1b22l` | **over-read** — the vendor's forward-looking statement, and the quote names no model |
| 7 | *"Fable 5 on med is cheaper than Opus 4.8 on xhigh and gives 10%+ better results on SWE-Bench"* | Fable 5 | `code.generation` | + | `reddit:t1_oqorjbe` | **relayed** — well-formed, cited to p255 of the vendor's model card |
| 8 | same quote as 7 | Opus 4.8 | `code.generation` | − | `reddit:t1_oqorjbe` | **relayed, leaning over-read** — the negative polarity is an artefact of losing a comparison, not a reported experience of Opus 4.8 |

**6 over-read, 2 relayed, 0 first-hand.** Six of the eight are the vendor
announcement, quoted verbatim and attributed to a Reddit permalink — the shape
the input analysis predicted without needing the rows.

**And rule 1 held perfectly throughout.** All 8 quotes are exact substrings of
the text the model was shown, checked in plain Python independently of the
extractor's own verification. **Quote verification cannot see over-reading**,
which is the whole finding: a vendor announcement quoted verbatim is a verbatim
quote.

### Three of them are mechanically detectable

Claims 2, 4 and 6 have a property no model judgement is needed to see: **the
quote does not resolve the model the claim is about.**

```
claim 2   quote resolves ()                    claim about Fable 5
claim 4   quote resolves (claude opus 4.8)     claim about Fable 5
claim 6   quote resolves ()                    claim about Fable 5
```

Running `entity.resolve` over the *quote* rather than the document is a code-only
check, it needs no model, and it would have caught three of the six over-reads.
It is not sufficient — claims 1, 3 and 5 pass it — so it is a filter, never a
gate, and an LLM still proposes while code decides.

### Against the pre-registered thresholds

| registered | observed |
|---|---|
| 0 expected | **8** |
| 1–2 acceptable with second-hand caveats | exceeded |
| ≥6 → write up as over-extraction, not yield | **met, so this is that write-up** |

The pre-registration's own reasoning is what makes 8 legible: it counted *two*
capability-shaped statements in the seven, one of them unattributable. The run
returned four claims per capability-shaped statement, six of which came from the
one document the analysis had already labelled marketing.

## 4 · Nothing was stored, and it is the same drop as last time

> **SUPERSEDED 2026-08-20, same day.** All three blockers below were fixed and
> the seven re-ran end to end: **4 claims stored, 2 cells, evidence rendering on
> the model page.** See
> `docs/measurements/three-blockers-and-the-first-stored-claim.md`.
>
> This section is kept rather than edited because its diagnosis was right and its
> framing was wrong in a way worth keeping visible. It called the drop a gap "in
> `judge/`" and left it there. The actual finding is that **none of the three was
> broken** — each was working code with no caller — and a fourth of the same kind
> was waiting in the render path behind them. "Blocked, and it is somebody else's
> lane" was true and stopped one question short of the useful one.


**0 of 8 claims are storable, and the cause has not moved.** Every claim came
back with `resolved_version_id: null` — the extractor is never shown that field —
so `judge/pipeline.py:150` maps it to no tracked model and skips the claim. Both
models involved ARE seated now, which is the point: **seating them changed
nothing, because the drop is not about the registry.** It is a plumbing gap
between what the extractor returns and what the store keys on, and it lives in
`judge/`.

**A second, independent blocker sits behind it (rule 6).** All 7 documents carry
`created_at IS NULL`, along with `names_version`, `has_conditions` and
`has_numbers` — the four values `compute()` weights from. `Pipeline.run` skips a
claim whose document facts are absent rather than weighting it from defaults,
which is the correct behaviour and also a second reason 0 would be stored even
with resolution fixed. Supplying a date here would be inventing one.

So the honest count is **0 claims, for two reasons, one of which is a refusal to
guess.**

## 5 · What was written to staging, and what deliberately was not

**DSN: `postgresql://bv_agent@52.17.75.29:5432/Model-information-Board`**
(`environment=staging`; preflight passed 3, failed 0, skipped 1 and named it).

| table | rows added | why |
|---|---|---|
| `capability` | **12** | was EMPTY. `claim.capability_key` is `NOT NULL REFERENCES capability(key)`, so no claim could ever have inserted regardless of extraction quality |
| `document` | **7** | the seven. 6 Reddit + 1 blog, from `_handoff/load.sql`, selected by id rather than running the file whole — the bundle covers all twelve exported threads and running it would have widened the population this report is about |
| `thread_context` | **1** | the blog thread; the Reddit one was already present |
| `claim` | **0** | blocked, §4 |
| `cell` | **0** | follows |
| `thread_extraction` | **0** | **deliberately not written — see below** |

**20 rows total, every one deletable by id.**

### Why the ledger row was withheld

`thread_extraction` is where a run records that it read a thread, and
`claims_written = 0` is a *finding* on that table rather than an absence. Writing
it here would have been wrong for a specific mechanical reason:
`ExtractionLedger.should_skip` returns True on `(id present, fingerprint
matches)` and **does not look at `claims_written`**. The flattened text of the
seven will not change, so its fingerprint will not change — a ledger row now
would make these two threads skip forever at this `pipeline_version`, including
after the `resolved_version_id` gap is fixed. That is the "evidence silently
never extracted" failure the column's own comment warns about, arrived at from
the other side: read, dropped, and marked done.

Left out and named rather than written and remembered.

## 6 · What a claim written here would commit us to

**`claim` has no `superseded_by` and no `retracted_at`.** Neither does
`thread_context`. Grepping `contract/tables.sql` for `supersed|retract` returns
nothing.

So a claim row is **correctable only by deletion.** There is no state that says
*"this was published and is now withdrawn"*, and no way for a page to render a
retraction distinctly from an absence — which is rule 4 arriving at the data
layer. With 6 of 8 judged over-reads, that is not hypothetical: had these landed,
the remedy would have been `DELETE`, and the board would afterwards be unable to
say that anything had ever been there.

**20 rows landed and none of them is a claim**, so the delete option is trivially
practical today. That is a property of this run, not of the design.
