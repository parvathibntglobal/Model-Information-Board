# Three blockers, none of them broken, and the first claim ever stored

**All three were code that existed, worked, and had never been called. So was a
fourth, found in the render path once the first three were cleared. Nothing
regressed — the path had never been walked end to end, and each blocker was the
next thing to fail once the previous one stopped failing first.**

*Engineer 1 · 2026-08-20 · `postgresql://example_user@203.0.113.5:5432/Model-information-Board`*

---

## 0 · Stated before the numbers

**`oqocfjv` — *"Fable uses up more tokens than a old Porsche gas"* — is the only
first-hand capability observation in this corpus, and it did not survive.** Bare
`fable` is one of the 26 hardcoded `FAMILY_WORDS` that `entity._admissible`
excludes, so it is not in the 1,224-surface population, resolves to nothing, and
**no seating fixes it.** That exclusion is what keeps `pro` out of "problem" and
`free` out of "freeze"; its price is this comment.

So the shape of the result was known in advance: **claims from the vendor
announcement and the relayed benchmark, and nothing from the one person actually
reporting an experience.** That is what happened, and it is reported below as
that rather than as yield.

## 1 · What each blocker actually was

**The diagnosis matters more than the fix, because three unrelated failures on
one path is a signature.** None of these was a regression. Each is a seam where
two working halves were never joined, and they surfaced one at a time because
each was hidden behind the one before it.

### Blocker 1 — `resolved_version_id`, and `resolve()` was never called

`resolved_version_id` occurs in **exactly two non-test places in the
repository**: the field declaration in `judge/extract/schema.py:28`, with a
`None` default, and the read in `judge/pipeline.py:150`. Nothing between them
ever wrote it.

- **Is `resolve()` called at all?** No — not anywhere in `judge/`. Grepping the
  lane for entity resolution returns `judge/extract/resolver.py`, which is a
  *text-store* reader protocol and has nothing to do with model identity, plus
  `_resolve_raw_span`, which translates offsets.
- **What does it receive?** Nothing. The extraction prompt never mentions the
  field, so the model was never asked to fill it and correctly returned null on
  all eight claims.
- **Where is the id lost?** It is not lost — **it was never produced.**
  `pipeline.py:150` reads `model_version_of.get(claim.model_ref.resolved_version_id
  or "")`, which is `.get("")` on every claim, returns None, logs *"resolves to
  no tracked model"*, and skips. `collect/triage/entity.resolve()` has worked the
  whole time and resolves this very text against 1,224 surfaces. It was simply
  on the other side of a lane boundary with nothing bridging it.

**So the registry was never the cause, and the log line pointed at it anyway.**
That is the expensive part: the message reads as a registry gap, which is where
two people then went looking.

**Fixed** by naming the dependency instead of importing across the boundary —
the arrangement `judge/extract/resolver.py` already argues for, and the same
shape as `ExtractionClient`. `judge.pipeline.SurfaceResolver` is a Protocol
`judge/` declares; `collect/surface_resolver.py` satisfies it, the second code
interface across the boundary after `rawstore_reader.py`. Resolution is **code's,
not the model's** (rule 2): asking the extractor for a canonical id would make an
LLM decide identity, and would need the whole population in its context to do
worse than a dict lookup.

**An ambiguous surface returns None and is counted.** 49 surfaces in the
substitution corpus have between 2 and 25 candidate models; resolving one to
whichever id sorts first would attach a real quote to the wrong model, which is
worse than dropping it — an unresolved claim is a counted absence, a mis-resolved
one is evidence against a model nobody discussed.

### Blocker 2 — `created_at`, and every production writer already sets it

**The column is populated nearly everywhere.** Measured across staging:

```
github   27 of 27   collect/adapters/github.py:535, from item["created_at"]
blog     30 of 30   collect/adapters/blog/write.py:68, from published_at
reddit    0 of  6   ← the only gap
```

**No adapter omits it.** The omitting writer is
**`scripts/export_thread_contexts.py`**, which generated `_handoff/load.sql`, and
it omits it two different ways in one file: the Reddit `INSERT` leaves the column
out of the statement entirely, and the blog `INSERT` names it and passes an
explicit `NULL`. Every Reddit body in the payload carries `created_utc`, and
`ReditComment.created_at` already turns it into a UTC datetime — the export loop
just did not copy it across.

`Pipeline.run` then skipped every claim rather than weighting from a default,
which is the correct behaviour and is why this presented as silence rather than
as wrong dates.

**Fixed** in two places: the export script now carries `created_at` through the
adapter's own property (so there is one definition of what a Reddit timestamp
is), and the seven existing rows were backfilled from **measured** sources —
`created_utc` from the stored payload for the six comments, and the page's own
declared date (`2026-04-06`, read by trafilatura from the stored HTML) for the
blog document. The triage flags `has_numbers`, `has_conditions`, `has_code`,
`has_error_strings` and `names_version` were computed from the document text by
`collect/triage/specificity.py` rather than allowed to default to False, which
would have been rule 6 by another route.

Staging is now `31/31` blog, `27/27` github, `6/6` reddit.

### Blocker 3 — `capability`, and the loader was written for exactly this

**The loader exists, works, and its only caller was a person with a terminal.**
`collect/registry/capabilities.py` is wired to `collect/cli.py registry
load-capabilities`, and its own module docstring opens with *"The table that
blocks `claim`… `capability` holds 0 rows. So no claim can be inserted at all,
for any model, from any platform, however good the extraction"* — and cites
`docs/measurements/unwired-tables.md` calling it *"the smallest unblocking task
in the repository"*.

So it did not fail to exist and it did not fail to work. **It was never run
against staging**, because nothing automated ran it: the nightly chain had 13
stages and none of them loaded capabilities, and neither `db init` nor `db
migrate` does.

**This is issue #27's shape exactly** — not a broken check, a check with no
caller — with one difference worth recording: #27's absence was silent, and this
one presents as an extractor that produces good claims which then vanish.

**Fixed** by adding a `load-capabilities` stage to the nightly chain, needing
`preflight` and placed before the sweeps: an empty `capability` does not degrade
extraction, it refuses every insert at the foreign key, so it belongs upstream of
anything that could produce a claim. The loader is idempotent, so a nightly
re-run reports `unchanged`.

### Blocker 4 — the render path, found only because the first three were cleared

`judge/pages/model.py` selected **`c.claim_date`, a column that has never existed
on `claim`**, so the model page raised `UndefinedColumn` the first time a cell
had a quote to show — which was the first time any claim was stored.

**The near-miss is the finding.** `claim.created_at` *does* exist and would have
run silently. It is the moment **we extracted**, not the moment somebody wrote
the sentence. Every quote would have rendered as fresh, the page would have
disagreed with the recency the weighting decays, and it fails in the flattering
direction. The date a claim was made lives on `document.created_at` — which is
already what `Pipeline.run` passes as `claim_date`. Fixed to read that, with the
reasoning left in the docstring because a plausible wrong column is worse than a
missing one.

**Four blockers, four "never called". None of them was a bug.**

## 2 · The re-run, against the pre-registration

Same seven documents, two threads, all four fixes in place.

```
thread_context_eacc17c8af367044   4 proposed · 4 verified · 4 STORED · 2 cells
thread_context_d166d88fbb7b3c70   0 proposed · no_claim_reason given
tokens/spend                      $0.0019 of the $1.00 cap over 2 calls
surface resolution                1 of 1 distinct surface resolved,
                                  0 unmatched, 0 ambiguous
```

| registered | observed |
|---|---|
| 0 expected | **4** |
| 1–2 acceptable with second-hand caveats | **exceeded** |
| ≥6 → over-extraction rather than yield | not reached |

**4 sits above the acceptable band and below the over-extraction threshold, and
the composition is the reason that arithmetic is not reassuring:**

| # | quote | model | capability | pol | document | judgement |
|---|---|---|---|---|---|---|
| 1 | *"exceptional performance in software engineering"* | claude-fable-5 | `code.generation` | + | `reddit:t3_1u1b22l` | **over-read** — vendor announcement copy |
| 2 | *"So when Fable's classifiers detect a request related to cybersecurity, biology and chemistry, or distillation, the response is handled by Claude Opus 4.8, our next-most-capable model."* | claude-fable-5 | `over_refusal` | − | `reddit:t3_1u1b22l` | **over-read** — describes routing, not refusal |
| 3 | *"We'll keep refining the safeguards to reduce false positives."* | claude-fable-5 | `over_refusal` | − | `reddit:t3_1u1b22l` | **over-read** — the vendor's forward-looking statement |
| 4 | *"gives 10%+ better results on SWE-Bench"* | claude-fable-5 | `code.generation` | + | `reddit:t1_oqorjbe` | **relayed** — cited to p255 of the vendor's model card |

**3 over-read, 1 relayed, 0 first-hand.** Three of the four are the vendor
announcement. The fourth is the relayed benchmark. **`oqocfjv` produced nothing,
exactly as stated up front.**

**So the board's first four stored claims are three pieces of marketing and one
citation of a model card, and the one engineer in the corpus reporting his own
experience is not represented.** That is the result. It is not a yield figure and
it must not be quoted as one.

Two smaller observations from the same run:

- **The claim count is not stable across runs.** The previous run over identical
  input produced 8; this one produced 4, from the same model at the same
  settings. Both drew 6-of-8 and 3-of-4 from the same vendor announcement, so the
  *proportion* held and the *count* did not. Any single-run count from this
  corpus is one sample.
- **`extractor_disagreements` fired three times**, all on the root post: the
  extractor said `has_numbers` where the code-side count disagreed. Free
  extraction-quality signal, working as designed.

## 3 · What renders

`GET /models/anthropic/claude-fable-5` returns 200 with evidence attached:

```
summary      "2 of 12 tracked capabilities have any reports at all. 4 of the 10
              unreported fail silently, where an absence of complaints is not
              evidence of safety."

code.generation   insufficient · "1 person has reported on this, which is not
                  yet enough to publish a finding."
                  phrase: "One person mentioned code generation — not yet corroborated"
over_refusal      insufficient · same shape
                  phrase: "One person mentioned over-refusal — not yet corroborated"

4 quotes, each with a real permalink, platform, and claimed_at of 2026-06-09
```

**Both cells are `insufficient` and nothing publishes**, which the pre-registration
predicted on three independently failing gates: `n_eff` 0.012 against a 3.0
minimum, `platform_count` 1 against a minimum of 2, `max_author_share` 1.0
against a 0.50 cap. **`insufficient` here is correct output, not a defect.**

Rule 4 is holding at the display layer: the 10 unreported capabilities render as
*"Nobody has reported on this"*, and the four silent-failure ones carry the
stronger sentence about absence of complaints not being reassurance.

`claimed_at = 2026-06-09` is worth noting as a check that passed: those are the
timestamps backfilled from the stored payload in blocker 2, so the page is
reading measured dates rather than extraction time.

### One thing now visible that should not stay

Quote 4's permalink renders as **`https://www.reddit.com/r/ClaudeAI/x/`**. That is
the synthetic per-comment URL `_handoff/manifest.json` warned about — the
`getPostComments` payload carries no per-comment permalink, so the export used a
stand-in. **It is now rendering on a page as though it were a real link.** The
manifest predicted exactly this: *"a synthetic URL in a url column is
indistinguishable from a real one downstream"*. Not fixed here; named because it
is on a page now rather than in a column.

## 4 · Rows on staging, and the delete

**DSN: `postgresql://example_user@203.0.113.5:5432/Model-information-Board`**

| table | rows | added by |
|---|---|---|
| `capability` | 12 | the loader, now chain-wired |
| `document` | 7 new (+7 updated in place) | the seven; the update is the `created_at` backfill |
| `thread_context` | 1 | the blog thread |
| `thread_extraction` | 2 | the ledger, one per thread |
| `claim` | **4** | this run |
| `claim_weight` | 4 | derived, one per claim |
| `cell` | 2 | rebuilt whole from claims |

**32 rows added in total; 12 of them are on the claim path.**

**There is still no `superseded_by` and no `retracted_at`** — grepping
`contract/tables.sql` for `supersed|retract` returns nothing. So a wrong claim
here is correctable **only by deletion**, and there is no state that renders a
retraction differently from an absence.

Rehearsed, in a rolled-back transaction: `DELETE FROM claim` removes all 4 and
cascades `claim_weight` to 0 (`claim_id … ON DELETE CASCADE`, tables.sql:518).
`cell` does not reference `claim`, so the 2 cells need `CellStore.rebuild_all`
afterwards or they will describe claims that no longer exist.

**With 3 of the 4 judged over-reads, that delete is the likely next action and it
is one statement plus a rebuild.** Saying so while it is still cheap is the
point of counting.
