# The pre-registered blog run: 8 claims, and the first first-hand evidence

**Against the pre-registration: the template prediction is clean (0 hits), the
voice check holds (1 author, every cell insufficient), no unsupported capability
keys — and the yield is 8, above the 6 the pre-registration calls
over-extraction.**

The result that matters is not the count. **All 8 read as the author's own runs**,
and the Reddit thread produced 4 claims of which 4 were relayed vendor copy and 0
were first-hand. This corpus supplies the half of the distinction the board is
built on and the seven had none of.

And **5 of the 8 name a family word, so 5 of 8 resolve to nothing.**

*Engineer 1 · 2026-08-21 · pre-registered in
`blog-extraction-pre-registration.md`, written before any model call · run in
`blog-extraction-run.txt`, claims in `blog-extraction-run.json` · 48,945 in /
4,484 out tokens*

> ⚠ **TOKEN FIGURES ON THIS PAGE WERE LOW, AND IN THE FLATTERING DIRECTION.**
> `run.input_tokens` took the FINAL completion only, so one call per retry went
> unbilled in our own numbers. Corrected 2026-08-21 in
> `judge/extract/runner.py`; the figures below are left as recorded with the
> correction beside them, because editing a measurement in place hides that it
> moved.
>
> | | reported | corrected | |
> |---|---:|---:|---|
> | corpus run, 30 docs, 6 retries | 75,985 in / 5,679 out | ~91,200 / ~6,800 | **83% of true** |
> | cost | $0.0370 | **$0.0444** | **+20%** |
>
> Method: the 6 uncounted calls are the first attempt of each retried document.
> A retry carries the correction text and so is larger than the call it follows,
> which makes scaling by the per-document average an upper bound.
> `docs/measurements/salvage-the-five-and-the-yield-movement.md` §2.

---

## 0 · The pre-registration said do not run until the block was stripped, and it was still there

> **Recommendation: do not run until the block is stripped.** … A run before that
> costs $0.062 to measure a defect already measured for free.

Checked before spending: **29 of the 30 readable blog `thread_context` rows still
carried `## Recent articles`**, and 29 contained one of the three headlines the
pre-registration named. The strip landed in the *parser* (`fbbfe94`); these rows
were flattened before it, so the stored text predates the fix.

So the block was stripped **in memory**, with `parse.strip_template_block` and
the two headings `contract/sources.yaml` verified over 62 pages — not re-fetched,
not rewritten into the store. Effect: **29 of 30 shortened, 8,118 bytes removed,
mean 280, none emptied.**

That is safe for verification because the block is terminal. The strip removes a
suffix, every offset before the cut is unchanged, and a blog `thread_context`
carries exactly one identity segment (`flat == raw`, one member) whose end is
clamped. A quote from retained text maps to the same raw span; a quote from the
block cannot be found at all.

One document was skipped: `blog:sha256:053141a14a3c0a43`, a malformed
`text_ref`. 30 ran.

---

## 1 · Against the table

| pre-registration | prediction | measured | verdict |
|---|---|---|---|
| §1 independent voices | 1, and >1 falsifies | **1** distinct `author_id` across 4 documents | **holds** |
| §1 cell status | every cell `insufficient` | 1 voice, so yes, regardless of claims | **holds** |
| §2 template quotes on unrelated posts | the three headlines will appear | **0** | **clean** |
| §3 yield | 0–4 claims | **8** | **over the band** |
| §4 more than ~6 | over-extraction | 8 | **triggered** |
| §4 `tool_calling.*` / `context.*` | nothing supports them | **none** | **holds** |
| §4 vendor's words as the author's report | the shape from the seven | none — see §3 | **clean** |

### §2 is the one worth dwelling on

Zero template quotes on unrelated posts, and zero headline quotes even on the
three posts that legitimately own those headlines (`qwen-38-27b`,
`moonlight-mayhem`, `openai-timeline`). The prediction was specific — *"claims
will be produced about models the document's own text never discusses, quoting
another post's headline, and they will pass verification"* — and stripping first
made it moot rather than testing it.

**So this run does not test the template prediction; it avoids it.** That is the
right trade and it is not a confirmation. The prediction stands untested and
would fire again on any corpus flattened before `fbbfe94`.

### §3 and §4: 8 is over the line, and the line was drawn against a defect

The pre-registration's rationale for the >6 threshold:

> more than ~6 claims → over-extraction. **There are 4 first-hand documents and
> 30 chances to borrow from a template**

The second clause no longer applies — the template is gone and produced nothing.
So 8 claims came from **4 documents' own text**, at 2 per document.

I am not going to explain the miss away: **8 is above 6 and the pre-registration
says that reading is over-extraction.** What I can also say is that the threshold
was calibrated against a contamination path that this run removed, so what it is
now measuring is claims-per-document rather than borrowing. Both statements are
true and only the first was pre-committed.

**The document count was right and the documents were wrong.** §3 named the four:
`introducing-muse-glimmer`, `openclaw`, `alchemy-utils`, `deepseek-v4-pro-0813`.
Four documents produced claims:

```
alchemy-utils                    3      <- on the list
florian-herrengt                 2
moonlight-mayhem                 2
sqlite-text-history-prototype    1
```

**1 of 4 overlaps.** Same number, different documents — the count matched by
coincidence and the identification did not. That is worth more than the count
agreeing would have been.

---

## 2 · One document lost to the schema, not to having nothing to say

`introducing-muse-glimmer` — one of the four the pre-registration named —
returned:

```
extraction failed the schema after 2 attempts: 1 validation error
claims.0.quote  String should have at most 200 characters
  input_value='Muse Glimmer achieves st...s from start to finish.'
```

`MAX_QUOTE_CHARS = 200`. The extractor chose a longer span, twice, and the
document produced nothing. **That is not a no-claim result and must not be
counted as one** — it is a document lost to a length ceiling, and it is the one
the pre-registration listed first.

**CORRECTED 2026-08-21: it is 2 of 30, and the second is worse.** A targeted
re-run of `qwen-38-27b` — 12,508 characters, the longest document in the corpus —
shows the extractor proposed **at least 12 claims** and every one was discarded,
because `claims.10.quote` and `claims.11.quote` exceeded 200 characters. Its
`no_claim_reason` reads *"extractor returned nothing parseable against the
schema"*, which is why the first run recorded it as a clean zero.

**Schema validation is all-or-nothing per document.** Two long quotes destroyed
ten valid ones, on the document whose title is
*"Qwen 3.8 27B is excellent, but it defaults to wildly overthinking things"* —
the capability the pre-registration named as one of two this corpus could support.
`docs/proposals/for-engineer-2-a-speaking-field-on-modelref.md` §0.

Worth knowing before the prompt changes: *"Choose the SHORTEST span that carries
the claim"* is already in the prompt and did not prevent this.

---

## 3 · What the eight actually are

| post | capability | pol | surface | quote |
|---|---|---|---|---|
| alchemy-utils | `code.generation` | + | `Codex` | *"I tasked Codex and GPT-5.6 Sol Ultra with building a prototype"* |
| alchemy-utils | `code.generation` | + | `GPT-5.6 Sol Ultra` | same sentence |
| alchemy-utils | `code.editing_diff_fidelity` | + | `Codex` | *"I had Codex optimize it and got it down to around 35 seconds."* |
| florian-herrengt | `code.editing_diff_fidelity` | − | `Fable` | *"Unfortunately, it seems like not even Fable can figure it out."* |
| florian-herrengt | `summarization.fidelity` | − | `Claude` | *"Neither of you has any idea whether any of it is true but Claude seems very confident."* |
| moonlight-mayhem | `code.generation` | + | `GPT-5.6 Sol Ultra` | *"It produced a much better game!"* |
| moonlight-mayhem | `code.editing_diff_fidelity` | − | `Codex` | *"Despite reviewing screenshots during development Codex failed to spot and correct this bug."* |
| sqlite-text-history-prototype | `code.generation` | + | `GPT-5.6 Sol Pro` | *"It churned away for 38 minutes and delivered this answer plus the files you see in this folder.\n\nThe approach works really well!"* |

**These are first-hand.** *"I tasked"*, *"I had Codex optimize it"*, *"It churned
away for 38 minutes"*, *"Codex failed to spot and correct this bug"* — an
author's own runs, with durations and outcomes. Four negative, four positive.

Set against the Reddit thread on the same prompt: **4 claims, 4 relayed vendor
copy, 0 first-hand.** The two corpora sit on opposite sides of the distinction
the prompt change is meant to teach, which is exactly what a baseline needs.

`§3` predicted the reachable capabilities would be *verbosity / overthinking* and
*cost or tier comparison*. **Neither appeared, and the reason is now known rather
than open:** the 12 keys handed to the extractor contain exactly one `ops` key,
`ops.latency_ttft` — time to first token. **There is no key for token spend,
output length or reasoning-effort cost.** `deepseek-v4-pro-0813`'s stated reason
on re-run was that the observation was *"too vague to map to a specific
capability"*, and it left `unclassified` **empty** — the escape hatch the prompt
provides for a quote that fits no key, and the signal designed to reveal that the
vocabulary is short. What appeared was
`code.generation`, `code.editing_diff_fidelity` and `summarization.fidelity` —
all plausible from the text, none predicted. The prediction was wrong in a
direction that costs nothing, and it is a miss.

---

## 4 · 5 of 8 resolve to nothing

```
'Codex'              family     -> NONE
'GPT-5.6 Sol Ultra'  version    -> mv_0510680735d3c79a
'Codex'              family     -> NONE
'Fable'              family     -> NONE
'Claude'             family     -> NONE
'GPT-5.6 Sol Ultra'  version    -> mv_0510680735d3c79a
'Codex'              family     -> NONE
'GPT-5.6 Sol Pro'    version    -> mv_0bf4520bbecebdf1

3 of 8 resolve.  5 of 8 are family words.
```

**This is the FAMILY_WORDS cost, measured on the only corpus that produces
first-hand evidence, and it is 62.5% of that corpus's yield.** Not one comment
(`oqocfjv`) — five claims of eight, from an author writing about his own runs,
naming `Codex`, `Fable` and `Claude` the way people actually do.

`collect/triage/entity.py`'s ruling stands: admitting bare `Fable` would attribute
it to whatever the seed file maps, and that is the misattribution the ruling
refuses. **Recorded, not acted on.** The order is already fixed — the counting
rule first, the resolution path second — and this is evidence for the size of the
prize, not a reason to reverse it.

---

## 5 · Cost, and what it bought

| | |
|---|---|
| documents | 30 |
| tokens | 48,945 in / 4,484 out |
| pre-registered estimate | 30 × $0.00208 ≈ **$0.062**, 6.2% of the $1.00 daily cap |

The token figures are the first per-document numbers from a real multi-document
run; the $0.00208 estimate came from n=3 calls on one thread. 48,945/30 = **1,631
input tokens per document**, against the 1,817 the single Reddit thread used —
close, and the estimate holds at this scale.

Nothing was written to the database. Inserting 30 documents' worth of claims
beside the four on staging would have made the labelling baseline
non-comparable, and the voice check needed the count rather than the rows.

---

## What this feeds

`fixtures/golden/extraction-reading-round2--unlabelled.jsonl` — **48 rows**,
built by `scripts/extraction_reading_pool.py`:

```
blog/claim              8
blog/document          30
reddit-thread/claim     4
reddit-thread/document  6
```

Every row carries an author. Round 1's section A is gone. The taxonomy is the
3×4, and `_meta.INCOMPARABILITY` says why round 2 must not be lined up against
round 1's 0.421.
