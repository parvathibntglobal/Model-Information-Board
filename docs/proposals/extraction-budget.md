# `EXTRACTION_DAILY_BUDGET_USD` — a starting figure

**Proposed: $30/night.** Roughly 3.2× the worst realistic night and **0.84× a
ceiling** built by assuming every estimate is wrong by 3× *and* that triage drops
nothing at all. NFR-3 requires the value to exist before the first paid call;
this is a number that can be raised, not an open question.

> **Tokens measured 2026-08-19 and every cost figure below moved up ~19%**, so
> the ceiling now exceeds $30 rather than sitting just under it. The
> recommendation is unchanged in this pass and the reasons are in §5. Note also
> that `.env` carries `EXTRACTION_DAILY_BUDGET_USD = 1.00`, not `30`, and the two
> have never been reconciled. `docs/measurements/extraction-token-counts.md`.

*Engineer 1 · 2026-08-18 · `.env` unchanged by this document*
*Token figures revised 2026-08-19 from the first live run — n=3 calls on one thread*

---

## 0 · The four inputs do not have equal standing

| term | standing | provenance |
|---|---|---|
| price | **measured** | `model_version`, polled from OpenRouter 2026-08-17 |
| documents/night | **derived from measurements** | request cap ÷ per-model cost × measured yield |
| survival | **measured, three times, on three populations** | 19.9% / 23.8% / 78.0% — the spread is the finding |
| tokens/extraction | **measured, n=3 on ONE thread** | first live run 2026-08-19 — 2,010 in / 589 out |

The budget is a product of four terms, and until 2026-08-19 one of them had
never been measured. It has now been measured **once, on one thread** — so it
has moved from "never observed" to "observed with no spread", which is a
different weakness rather than none. The proposal stays a ceiling rather than a
forecast: a point estimate with n=3 does not tell you where a busy night sits.

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

## 4 · Tokens — MEASURED 2026-08-19, and the old estimate was right for the wrong reason

**Superseded by the first live extraction run.** Measured, as means over
**n = 3 calls against ONE thread** — that is the entire population, and it is
not a sample of the corpus (rule 7):

| | estimated | measured | error |
|---|---|---|---|
| input tokens | 1,300 | **2,010** | **55% high** |
| output tokens | 800 | **589** | **26% low** |
| cost per thread | $0.00239 | **$0.00208** | 13% |
| threads per $1.00 | ~418 | **~481** | |

### The agreement is a coincidence, not a validation

13% apart on cost looks like a method that works. **It is not, and this is the
part to read before reusing the approach.** The two errors ran in opposite
directions and partly cancelled: input was half again as large as assumed,
output a quarter smaller, and the product landed close by arithmetic accident.

The conversion the estimate rested on — **4 characters per token**, flagged
below as "an approximation and not this tokenizer's" — is simply wrong for this
input. Nothing about the near-match supports it, and the next figure derived
that way inherits no confidence from this one.

### What was estimated, kept for the record

| | |
|---|---|
| system prompt + block markers | 2,344 chars ≈ 586 tokens |
| flattened thread, row 1 | 3,550 chars ≈ 888 tokens |
| flattened thread, row 2 | 11,468 chars ≈ 2,867 tokens |

**n = 2**, at 4 characters per token. That reasoning put input at 1,500–3,500
and used **2,500** in §5; output was assumed at **400**.

**Note the two estimates disagreed with each other.** §5's scenarios were built
on 2,500 in / 400 out — $0.00175 per thread — while
`judge/extract/budget.py` enforced on 1,300 / 800 — $0.00239. So the repo held
two per-thread figures differing by 37%, and the measurement lands *between*
them: 19% **above** §5's and 13% **below** the guard's. §5 is recomputed
accordingly, and it moves **up**.

The `~0.13 survival` in BUILD-PLAN's formula is also superseded — it is below
every figure measured.

**This term was why the proposal is 3× the worst case rather than 1.5×.** With
n = 3 on a single thread there is still no measured *spread*, so the headroom
argument stands: what is now known is a point, not a distribution.

## 5 · Three figures

**Recomputed on the measured $0.00208 per thread.** The bracketed figures are
what this table said when it was built on the unmeasured 2,500 in / 400 out.

| | documents | survival | extractions | per night | per month |
|---|---|---|---|---|---|
| **1 · current**, 7 models | 3,649 | 78.0% | 2,846 | **$5.91** *(was $4.98)* | $177 |
| **2 · tracked set**, 64 models | 5,760 | 78.0% | 4,493 | **$9.33** *(was $7.86)* | $280 |
| **3 · ceiling** | 5,760 | **100%** | 5,760 | **$35.86** *(was $30.24)* | $1,076 |

**Every figure moved up by 19%**, because §5 had been built on the lower of the
repo's two disagreeing estimates. The measurement is *below* the guard's
estimate and *above* this table's, so "we measured tokens and costs fell" would
be the wrong summary — it depends entirely on which estimate you were holding.

The ceiling assumes, simultaneously:

- **every document survives triage** — no gate drops anything;
- **3× the measured tokens** — 6,030 in and 1,767 out *(was 7,500 / 1,200,
  which is 3× the old estimate and is no longer 3× anything measured)*;
- **the tracked set is full** at 64 models, saturating the request cap.

That is 3.8× scenario 2 — unchanged, because scenario 2 and the ceiling scale
together off the same per-thread figure. What changed is the absolute level, and
therefore whether $30 covers it. Every one of those assumptions is individually
implausible; all three being wrong together is what the ceiling is for.

### Proposed: `EXTRACTION_DAILY_BUDGET_USD=30`

**A ceiling that is too high fails safe and one that is too low does not.**
NFR-3's mechanism degrades to triage-only rather than overrunning — so a
too-high ceiling costs money only if something else is already wrong, while a
too-low one blocks the stage it exists to protect and does so on an ordinary
night, silently, as an absence of claims.

$30 leaves 3.2× headroom over the realistic worst case *(was 3.8×)* and **0.84×
over the ceiling — it no longer covers it.** The ceiling moved to $35.86 when
the tokens were measured, so the "roughly 1.0×" claim this section made is now
false by arithmetic rather than by judgement.

**Recorded, not resolved, and the recommendation is unchanged in this pass.**
Two reasons. The ceiling is deliberately three simultaneous implausible errors,
so failing to cover it is not the same as being too low for an ordinary night —
scenario 2 at $9.33 still has 3.2× headroom. And the figure actually in force is
not $30: `.env` carries `EXTRACTION_DAILY_BUDGET_USD = 1.00`, which predates
this document and was never reconciled with it. Changing either number is a
decision, and one that should be taken against both figures at once rather than
as a side effect of a token measurement.

**Raise it after a week of real token counts across threads of differing length;
do not tune it downward from a figure with n = 3 on one thread.**

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

---

## 8 · For Engineer 2, before §4's estimate hardens into a constant

**Not a change to this proposal. A pattern that has now happened twice, and
§4's `~2k tokens` is positioned to be the third.**

On 2026-08-18 the Reddit quota limit was read off a response for the first time.
It had been `1,000,000` in six places — an adapter docstring, `.env.example`,
`contract/sources.yaml`, two design documents and the terms ruling — and every
one of those traced back to a single docstring line added in the same commit as
the fetch path, never to an observation. The plan page said 500,000. The
arithmetic gave it away independently: `733 of 1,140 consumed` produced
**−499,267** when the denominator was swapped, and a figure that goes negative
when its denominator changes was a subtraction from a constant rather than a
count.

**The reading agreed with the constant. It was 1,000,000.** That is the part
worth carrying over here, because a wrong constant gets caught eventually and a
*right* one never does — nothing prompts anyone to revisit a number that keeps
producing plausible answers. The method was unsound for a fortnight and the
output looked fine the whole time.

### Why this lands on §4 specifically

§0's table already says `tokens/extraction` is **estimated, never observed**,
sourced to BUILD-PLAN's *"~2k"* plus n=2. That is the honest version and it is
exactly the state `1,000,000` was in before it acquired citations. The failure
mode is not the estimate; it is what happens next:

| stage | quota limit | `~2k tokens` |
|---|---|---|
| stated once, labelled | docstring, with `-limit` named beside it | §4, labelled "weakest input" |
| cited elsewhere | five documents | **four, and one of them was a test fixture** |
| load-bearing | headroom in two sweep designs | `EXTRACTION_DAILY_BUDGET_USD` |
| checkable by | one call | **one real extraction run — DONE 2026-08-19** |

### Resolved 2026-08-19, and this section predicted it correctly

The run happened, and the row above is the only one this section got wrong: it
said "pending" on citations at a moment when the figure had **already** reached
four places, including `tests/test_extraction_budget.py`'s `completion()`
default — a per-thread figure inside a test, in a docstring calling it "the
figure the budget decision was made on". Three different per-thread numbers for
one quantity by the time anyone looked.

The prediction that a right-looking constant never gets revisited was also
correct, and sharper than written. **The estimate came within 13% on cost and was
wrong on both terms** — input 55% high, output 26% low, errors cancelling. Had
nobody run the check, the agreement would have been read as validating chars/4
indefinitely. `docs/measurements/extraction-token-counts.md`.

Once `30` is in `.env` and a document says "3.2× the worst realistic night", the
`~2k` stops being visible as the term carrying the uncertainty. It becomes a
property of the budget rather than an input to it, and the budget will keep
looking right whether the true figure is 2k or 6k, because a ceiling absorbs
error silently in the direction that does not alarm anyone.

### The check that catches it, and it needs no suspicion

Rule 7's version: ask what the denominator is and where it came from. The
quota-limit version: **ask which of these numbers has been read, and off what.**
For §4 that question has a concrete answer and a cheap price — one real
extraction run, already §7's first bullet. It is worth doing *before* the figure
is committed rather than after, on the evidence that the last unsourced constant
survived five citations and a fortnight and was only caught because somebody
asked what a percentage was a percentage of.

Not urgent for the same reason the quota was not: the margin is generous, ~3.2×
over an ordinary night, so being 3× wrong on tokens does not breach *that*.
Cheap now, and the expensive version is the one where the constant is right and
nobody rechecks.

**That last sentence is what happened.** The estimate was within 13% on cost and
wrong on both terms, so it would have gone on looking right. The check cost one
run.

Full write-up of the quota case, including what one live call could and could not
settle: `docs/measurements/reddit-rate-and-quota.md` §1.4.
