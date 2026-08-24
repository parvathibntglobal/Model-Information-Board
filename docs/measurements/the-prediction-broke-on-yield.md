# The prediction broke on yield and held on overlap

**140 claims from 75 documents — and corporate engineering blogs produced 33 of
them, against a prediction of near-zero. Both of us were wrong about that.**

**And no two-platform cell, because 133 of the 140 claims name no resolvable
model.** Corporate blogs do make capability observations. They make them about
*"our LLM"*, *"Codex"*, *"AI"* — a capability claim with no subject, which
passes extraction and dies at resolution.

```
PREDICTED   low yield; split stays Willison-dominated; zero-overlap survives
MEASURED    140 claims, 43 of 75 documents         PREDICTION BROKEN
            corporate blogs: 33 claims             PREDICTION BROKEN
            two-platform cells: 0                  PREDICTION HELD
            claims resolving to one model: 4 of 140
```

*Engineer 1 · 2026-08-21 · 75 documents, 527,847 in / 26,197 out, **$0.2238***

---

## 1 · The prediction, and where I agreed wrongly

I agreed with it and cited support: *8 of 75 non-Willison documents name any
model, and the corporate blogs name one each with zero resolving.* That
measurement was right. **The inference from it was wrong**, and the error is
worth naming because it is easy to repeat:

> **"Names a model" predicts CELL yield, not CLAIM yield.** The extractor is
> perfectly willing to produce a claim from a document that never names a
> version — *"we swapped our LLM and latency halved"* is a capability
> observation, and it becomes a claim with `surface: "LLM"`. I used a
> document-level naming rate to predict claim count and it predicts something
> else entirely.

So the corporate feeds are not quiet about model behaviour. They are quiet about
*which model*, which is a different failure and the one that matters for the
gate.

## 2 · What was measured

```
documents extracted            75      (43 produced at least one claim)
claims verified               140
retries                        22
provider unavailable            1      recorded as unattempted, not as zero
cost                       $0.2238

  vickiboykis.com      practitioner   20 docs   43 claims
  jxnl.co              practitioner   20 docs   37 claims
  hamel.dev            practitioner   12 docs   27 claims
  engineering.grab.com CORPORATE      10 docs   17 claims
  slack.engineering    CORPORATE       8 docs   11 claims
  engineering.atspotify CORPORATE      5 docs    5 claims
```

**Twelve capability keys appeared**, against nine on Willison's corpus:
`code.generation` 47, `instruction.adherence` 22, `extraction.faithfulness` 16,
`context.effective_window` 11, `reasoning.multistep` 11, `ops.latency_ttft` 8,
`summarization.fidelity` 8, `tool_calling.long_chain_reliability` 6,
`code.editing_diff_fidelity` 4, `format.structured_output` 4, `over_refusal` 2,
`tool_calling.schema_accuracy` 1.

**`format.structured_output` and `tool_calling.schema_accuracy` appear for the
first time in this project**, both from feeds Willison's corpus could not supply.
So the capability split is *not* Willison-dominated: he contributed 36 claims
across 9 keys, these six writers contributed 140 across 12.

### The corporate blogs specifically

`code.generation` at Spotify and Grab, `over_refusal` at Slack,
`extraction.faithfulness` six times at Grab. A corporate engineering blog does
write about model capability — it writes about it as a system-integration
problem, which is why `extraction.faithfulness` and `format.structured_output`
show up there and not in a link blog.

**The stated break condition was hit at the capability level.** Five corporate
claims on a capability Reddit also carries:

```
engineering.atspotify.com  code.generation  surface "Claude"
engineering.grab.com       code.generation  surface "AI"
engineering.grab.com       code.generation  surface "Claude Design"
engineering.grab.com       code.generation  surface "GPT-4-32k"
slack.engineering          over_refusal     surface "model"
```

## 3 · And it still is not a cell

```
REDDIT cells    anthropic/claude-fable-5 / code.generation
                anthropic/claude-fable-5 / over_refusal

BLOG cells that resolve at all (4 of 140 claims)
                anthropic/claude-haiku-4.5 / ops.latency_ttft     slack
                openai/gpt-4 / code.generation                    grab
                openai/gpt-4 / instruction.adherence              hamel
                openai/gpt-4 / summarization.fidelity             jxnl

TWO-PLATFORM CELLS: NONE
```

**133 of 140 claims resolve to nothing.** The surfaces:

```
LLM 15 · Codex 11 · Claude 6 · AI 6 · Claude Code 5 · MiniLM 5 · model 4 · Gemini 4
```

Four of the five break-condition claims name `Claude`, `AI`, `Claude Design` or
`model` — none of which is a model version. The fifth names `GPT-4-32k` and
resolves to `openai/gpt-4`, a different model from Reddit's `claude-fable-5`.

So the zero-overlap premise **survives, and its mechanism has changed twice
now**:

| stage | what was blocking the overlap |
|---|---|
| before this sweep | the corpus was one writer |
| after last turn | the platforms discussed the same capabilities about different *models* |
| after this run | **most blog claims have no model at all** — 95% name a generic or family surface |

That third one is the real obstacle and it is not a corpus problem. `LLM`,
`AI`, `Codex` and `model` will never resolve, however many feeds are swept,
because the writers did not name a version. **A capability claim with no subject
cannot join a cell**, and there are 133 of them.

> Worth stating as its own thing: this is the family-specificity problem arriving
> from a new direction. The recorded worry was `family` surfaces like `sonnet`
> being *over*-credited. Here the surface is not even a family — it is a
> category. `resolve()` correctly returns nothing, and the claim is correctly
> unusable, so nothing is broken. What is new is the **rate**: 95%, on the
> platform that is supposed to be the positive-evidence channel.

## 4 · The token estimate was wrong by 1.7×, and the reason is the corpus

```
estimated   312,266 input tokens   $0.135      at 5.83 chars/token
actual      527,847 input tokens   $0.2238     1.69x
```

Two causes, and only one of them was avoidable:

**22 retries.** 75 documents cost 97 calls, and the system prompt plus tool
schema (11,186 chars, ~1,919 tokens) is charged on every attempt. That is
+42,000 tokens I did not budget.

**And 5.83 chars/token is a figure about a different corpus.** Backing out the
prompt overhead: 527,847 − (97 × 1,919) = 341,704 content tokens for 981,558
characters — **2.87 chars/token, not 5.83.** Half.

> **A chars-per-token ratio travels with the text it was measured on.** 5.83 was
> measured on Reddit comments and Willison's link-blog prose. These are
> engineering posts full of code blocks, config, identifiers and JSON, and code
> tokenises at roughly half the density of prose. Using one corpus's ratio to
> budget another's is rule 7 in a place I did not expect it — the figure is real,
> it is just answering a question about different text.
>
> For next time: **2.9 chars/token for code-heavy technical posts, 5.8 for
> prose.** Both need re-measuring rather than trusting, and a mixed corpus needs
> the pessimistic one.

Cost remains inside the cap: $0.2238 of $1.00, plus ~$0.03 wasted on the crashed
first attempt (§5).

## 5 · The crash, and what it cost

The first attempt died on document 21 of 75:

```
KeyError: 'choices'   judge/extract/client.py
```

**A provider error arrives as HTTP 200 with an `error` body**, so
`raise_for_status()` passes and `body["choices"]` raises a `KeyError` out of the
middle of a corpus run. Twenty completed documents were lost because nothing had
been written yet — the exact failure recorded two days ago as *persist any run
that enters an argument*, reproduced by me while acting on it.

Two fixes, both taken:

- **`ExtractorUnavailable`**, a typed exception carrying whatever the provider
  said. A `KeyError` is the wrong shape twice: it names a dict key rather than
  the upstream failure, and it is indistinguishable from a schema change on our
  side. The caller now records the document as **unattempted rather than as
  producing nothing** — rule 4 in the harvest layer, and exactly one document hit
  it on the successful run.
- **a per-document ledger**, appended as each document completes, so a re-run
  skips what is recorded and pays for nothing twice.

---

## 6 · The two sweep findings, and neither is named as given

Both underlying gaps are real. Neither name exists in the repository, and one
symptom did not occur — recorded that way rather than tidied into agreement.

### `refresh_stale` — the gap is real, the mechanism is different

`grep refresh_stale` returns nothing. And no feed failed on a connect timeout:
the sweep reported **9 feeds, 0 refused, 0 errors**. The 5-second connect
failures are not in this run.

**What is real, and it is the gap you describe:**

```
FeedRun.outcome vocabulary:  fetched · not-modified · error · robots-blocked
```

`not-modified` exists and is **unreachable across runs**, because validators live
in `InMemoryValidatorStore` and the durable columns are an unagreed contract
change. So a feed with nothing new returns `fetched`, exactly like a feed with
everything new.

And worse, measured here: **`netflixtechblog.com` and
`medium.com/airbnb-engineering` returned `fetched` with 0 articles.** A feed that
has gone silent and a feed with nothing new are *both* `fetched, 0 articles` —
indistinguishable, and 2 of 9 sources are currently in that state with nobody
able to say which it is. A nightly chain would report success.

So: real gap, real consequence, and the fix is the two `watermark` columns rather
than a new function. It is the same blocked contract change as the 304 cost.

### The frozen accumulator — the shape is real, the instance is not this one

`HarvestReport` does not exist. `FeedRun` **is** `@dataclass(frozen=True)`, and
`BlogAssembleReport` is mutable and per-feed; `harvest_blogs.py` accumulates into
a dict and printed all 9 sources. **8 reported as 1 did not happen in this run.**

But the shape did, one field over: `totals` in `harvest_blogs.py` carries
`feeds, refused, articles, documents, contexts, nothing_extracted,
already_present, members_unresolved, unreadable_after_write` — and **not
`author_rows`, not `authors_attached_to_existing`.** Those are computed per feed
and discarded, which is why the authors going 1 → 14 was invisible in the run
output and I had to query the database to find it.

> **An accumulator that silently keeps only some fields is the same shape as one
> that keeps only the last**, and it is the same shape as a comparison that finds
> no rows and reports no differences: *the absence of a number reads as the
> absence of the thing.* Worth the line you asked for, attached to the instance
> that exists rather than the one that does not.

---

## What changed

| file | change |
|---|---|
| `judge/extract/client.py` | `ExtractorUnavailable`; a provider error with no `choices` raises it instead of `KeyError` |
| `docs/measurements/eight-feeds-extraction.json` + `.jsonl` | the run, and the per-document ledger it is resumable from |

**Not changed:** nothing was written to `claim`. 133 of 140 claims have no
resolvable model and the other 7 include the `gpt-5`-inside-`gpt-5.6`
substring defect, so storing them would file unattributable and mis-attributed
claims. Same refusal as last turn, now on a larger corpus.

**The next cheap test is no longer a sweep.** Six writers and 140 claims did not
produce a two-platform cell, and a seventh will not either. What would: fixing
the resolver so a version surface stops matching inside a longer one, and then a
Reddit sweep aimed at the models the blogs actually name — of which the most
common is `LLM`, which is not a model.
