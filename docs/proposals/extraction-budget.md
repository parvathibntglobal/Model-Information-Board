# `EXTRACTION_DAILY_BUDGET_USD` — a starting figure

**Proposed: $30/night.** Roughly 3.8× the worst realistic night and about 1.0×
a ceiling built by assuming every estimate is wrong by 3× *and* that triage
drops nothing at all. NFR-3 requires the value to exist before the first paid
call; this is a number that can be raised, not an open question.

*Engineer 1 · 2026-08-18 · `.env` unchanged by this document*

---

## 0 · The four inputs do not have equal standing

| term | standing | provenance |
|---|---|---|
| price | **measured** | `model_version`, polled from OpenRouter 2026-08-17 |
| documents/night | **derived from measurements** | request cap ÷ per-model cost × measured yield |
| survival | **measured, three times, on three populations** | 19.9% / 23.8% / 78.0% — the spread is the finding |
| tokens/extraction | **estimated, never observed** | BUILD-PLAN's *"~2k"*, plus n=2 from real rows |

The budget is a product of four terms and one of them has never been measured.
That is the shape of the whole estimate and it is why the proposal is a ceiling
rather than a forecast.

---

## 1 · Price — measured, and the tier check matters

```
google/gemini-2.5-flash          the pinned extractor (EXTRACTOR_MODEL)
  price_in           0.300000    USD per 1M tokens
  price_out          2.500000
  price_cached_read  0.030000
  batch_discount     0.500
  provenance         polled
  source             https://openrouter.ai/api/v1/models
                     retrieved_at 2026-08-17T08:32:33Z
```

**Tier check: `price_tier` holds 0 rows for this model, and 0 rows in total.**
That check is not ceremony — `contract/tables.sql` warns that `price_in` goes
NULL when a `price_tier` row exists, and *"these are NOT the lowest tier"*. A
naive read of a tiered model would multiply by NULL and produce a budget of
zero, which fails in the unsafe direction. Here the flat price is authoritative.

Neither `batch_discount` (0.5) nor `price_cached_read` ($0.03) is used below.
Both would lower the figure and neither is wired, so leaving them out keeps the
estimate conservative.

## 2 · Documents per night — derived, and the population is stated

```
900 daily requests / 81.45 per model = 11 models a night   (contract/tables.sql)
6.4 distinct documents per request                          (measured, below)
```

The yield figure is measured and its population matters:

| sweep | calls | distinct documents | per call |
|---|---|---|---|
| substitution (search, deduplicated across queries) | 204 | 1,297 | **6.4** |
| unfiltered (listing, no query overlap) | 78 | 1,900 | 24.4 |

**6.4 is the right one and 24.4 is not.** The nightly evidence sweep is a
*search* path issuing many alias-scoped queries whose results overlap heavily —
2,876 posts returned collapsed to 1,297 distinct. The listing path has no
overlap by construction and its 24.4 describes a sweep we do not run nightly.
Using 24.4 would overstate documents by 3.8× before any other term.

| state | calls/night | documents/night |
|---|---|---|
| **current** — 7 models carry alias surfaces | 570 (under the 900 cap) | **3,649** |
| **tracked set** — 64 models | 900 (at the cap) | **5,760** |

The cap binds from 12 models onward, so 64 models does not cost 9× the current
state — it costs 1.6×, and the rest shows up as each model being swept less
often. That is the rotation problem from #33, not a budget problem.

## 3 · Survival — the term to be careful about

Three measured figures, same code, same population fingerprint, same gates:

| population | survival | what it is |
|---|---|---|
| unfiltered sample, 26 AI subreddits | **19.9%** | what a listing sweep produces |
| + the three unbuilt gates, optimistically | ~23.8% | E4 as specified, ceiling |
| model-name-retrieved corpus | **78.0%** | what a *search* sweep produces |

**The budget must use 78.0%, and that is the uncomfortable one.**

Extraction pays for whatever survives, so the higher number is the expensive
number — and the nightly sweep is the search path, which is the corpus that
produces 78.0%. The 19.9% figure describes a population the evidence pipeline
does not harvest. Budgeting on it would set a limit 3.9× too low and the stage
would degrade to triage-only on an ordinary night, which is precisely the
failure NFR-3's ceiling exists to avoid.

This is the 58.1pp retrieval-bias finding paying rent: **the same pipeline over
two populations differs by a factor of four, and which one you are budgeting for
is not a detail.**

The three unbuilt gates would lower the search-path figure too, and by how much
is unmeasured — the 23.8% ceiling was computed on the unfiltered sample. So
78.0% is itself conservative in the safe direction.

## 4 · Tokens — the weakest input, flagged as such

BUILD-PLAN says `docs/day × ~0.13 survival × ~2k tokens × price`. **Nobody has
measured a token count.** `judge/extract/runner.py` runs against a `FakeClient`,
so no real request has been sent and no usage figure exists anywhere.

What can be measured is what *would be sent*:

| | |
|---|---|
| system prompt + block markers | 2,344 chars ≈ **586 tokens** |
| flattened thread, row 1 | 3,550 chars ≈ 888 tokens |
| flattened thread, row 2 | 11,468 chars ≈ 2,867 tokens |

**n = 2**, at 4 characters per token, which is itself an approximation and not
this tokenizer's. Input therefore lands somewhere around 1,500–3,500 tokens and
**2,500 is used below**. Output is a structured claim against a 145-line schema;
**400 tokens** is assumed and nothing has produced one.

The `~0.13 survival` in BUILD-PLAN's formula is also now superseded — it is
below every figure measured.

**This term is why the proposal is 3× the worst case rather than 1.5×.** A
budget whose weakest input has n=2 and no observations should not be tight.

## 5 · Three figures

| | documents | survival | extractions | per night | per month |
|---|---|---|---|---|---|
| **1 · current**, 7 models | 3,649 | 78.0% | 2,846 | **$4.98** | $149 |
| **2 · tracked set**, 64 models | 5,760 | 78.0% | 4,493 | **$7.86** | $236 |
| **3 · ceiling** | 5,760 | **100%** | 5,760 | **$30.24** | $907 |

The ceiling assumes, simultaneously:

- **every document survives triage** — no gate drops anything;
- **3× the token estimate** — 7,500 in and 1,200 out;
- **the tracked set is full** at 64 models, saturating the request cap.

That is 3.8× scenario 2, and every one of those assumptions is individually
implausible. All three being wrong together is what the ceiling is for.

### Proposed: `EXTRACTION_DAILY_BUDGET_USD=30`

**A ceiling that is too high fails safe and one that is too low does not.**
NFR-3's mechanism degrades to triage-only rather than overrunning — so a
too-high ceiling costs money only if something else is already wrong, while a
too-low one blocks the stage it exists to protect and does so on an ordinary
night, silently, as an absence of claims.

$30 leaves 3.8× headroom over the realistic worst case and roughly 1.0× over a
ceiling built from three simultaneous 3× errors. **Raise it after the first
week of real token counts; do not tune it downward from a figure nobody has
observed.**

## 6 · What the number buys, and what it does not

**It caps spend.** That is the whole of it. NFR-3 is a cost control and this
figure satisfies it.

**It says nothing about whether the extraction is any good.** Not about
precision, not about recall, not about whether the extractor invents a
capability or misattributes a quote — quote verification catches fabricated
*spans* and nothing else, and `judge/CLAUDE.md` is explicit that the model
choosing capability, polarity and conditions is exactly what code cannot check.

**The thing that would answer that is the golden set, and it is unbuilt.**
`fixtures/golden/` holds two candidate pools I generated and no labels.
BUILD-PLAN's acceptance is *extraction F1 ≥ 0.85 on the golden set*; there is no
golden set, and building it is blocked on a labelled corpus that is blocked on
harvest producing documents for more than seven models.

So this budget protects against one failure mode — spending too much — and
leaves the more expensive one, spending anything at all on extraction nobody has
validated, entirely unaddressed. **A ceiling is not a quality gate**, and the
first paid call will be made against an extractor measured by nothing.

## 7 · What would revise it

- **One real extraction run.** It replaces the weakest term with an observation
  and would justify moving the figure in either direction.
- **The three unbuilt gates**, which lower survival on the search path by an
  unmeasured amount.
- **`batch_discount` or prompt caching**, both present in the price row and
  neither wired. Either would cut the figure materially.
- **A tiered extractor.** If `EXTRACTOR_MODEL` ever moves to a model with
  `price_tier` rows, §1's check has to be re-run — `price_in` will read NULL and
  the naive calculation gives zero.
