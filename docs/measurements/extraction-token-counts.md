# Extraction token counts — the first live run, and an estimate that was right for the wrong reason

*2026-08-19 · first real extraction calls · figures reported from the run, recomputed and cross-checked here*

---

## 0 · The population, first, because it is small

**n = 3 calls against ONE thread.** Both token figures below are means over
those three. That is the entire population — it is not a sample of the corpus,
not a sample of threads, and it measures no spread at all.

Rule 7, and it matters more here than usual: the thing a budget guard wants is a
figure at or above a *typical* call, and a mean of three calls on one thread
cannot tell you where typical sits. Every number on this page carries that
denominator or it is not evidence.

## 1 · What was measured

| | estimated | measured | error |
|---|---|---|---|
| input tokens | 1,300 | **2,010** | **55% high** |
| output tokens | 800 | **589** | **26% low** |
| cost per thread | $0.00239 | **$0.00208** | 13% |
| threads per $1.00/day | ~418 | **~481** | |

Priced at `Pricing(price_in=0.30, price_out=2.50)` per 1M tokens — Gemini 2.5
Flash from `contract/seed_models.yaml`, itself a build fixture sourced to
Google's pricing page on 2026-08-13. **So the cost column is a measured token
count times a seeded price, not a billed amount.**

## 2 · The agreement is a coincidence — this is the finding

13% apart on cost reads as a validated estimate. **It is not.**

The two errors ran in opposite directions and partly cancelled. Input was half
again as large as assumed; output was a quarter smaller; the product landed
close by arithmetic accident. Either error alone would have been visible as a
miss — together they produced a number that looks like confirmation.

The conversion the estimate rested on was **4 characters per token**, and
`docs/proposals/extraction-budget.md` §4 already flagged it as "an
approximation and not this tokenizer's". It is simply wrong for this input.
**Nothing about the near-match supports the method**, and a future figure
derived by chars/4 inherits no confidence from this one.

Written down because the failure mode is specific and quiet: the next person
reads `estimated $0.00239, measured $0.00208` as evidence that estimating this
way works, and reuses it. The check that catches this needs no suspicion — ask
whether the *terms* agreed, not whether the totals did.

## 3 · There were TWO estimates, and they disagreed with each other

This is the part that made the error hard to see.

| source | input | output | per thread |
|---|---|---|---|
| `judge/extract/budget.py` (enforced) | 1,300 | 800 | $0.00239 |
| `extraction-budget.md` §5 (scenarios) | 2,500 | 400 | $0.00175 |
| **measured** | **2,010** | **589** | **$0.00208** |

Two per-thread figures differing by **37%**, in the same repo, one enforcing a
cap and one sizing the budget. The measurement lands *between* them.

So **"we measured tokens and the cost fell" is only true if you were holding the
guard's estimate.** Against §5's, cost *rose* 19%, and every scenario in that
table moved up. Which direction the news runs depends entirely on which estimate
you had in hand — which is what having two of them costs.

## 4 · One figure I could not reconcile, stated rather than smoothed

The run was reported as **$0.00212 per thread, ~472 threads per $1.00**. At
2,010 in / 589 out and the seeded price, the arithmetic gives **$0.002076 and
~481**:

```
2010 × 0.30/1e6  +  589 × 2.50/1e6  =  0.000603 + 0.0014725  =  $0.0020755
```

A gap of $0.000044 per thread. It would be explained by ~607 output tokens
rather than 589, or ~2,158 input rather than 2,010 — so the likeliest causes are
that the cost came from the provider's own billing rather than from
tokens × seeded price, or that a component not in `output_tokens` (thinking
tokens are billed as output on this model) is included in the charge and not in
the count.

**Not resolved, and not averaged away.** `$0.00208` is used everywhere in the
repo because it is the figure that follows from the numbers we hold and can be
recomputed from them; `tests/test_extraction_budget.py` pins it. If the billed
figure is authoritative, the token counts are incomplete and the fix is to
record what the provider charged alongside what it reported — which is
`Budget.charge`'s existing distinction between estimated and measured, one layer
further out.

## 5 · What this does NOT license

**The constants are no longer a generous bound.** `budget.py`'s comment used to
say the estimate was "deliberately generous", because too low lets a run
overshoot the cap while too high only stops early. A mean is neither: roughly
half of calls will exceed it, and the old input figure was 55% *under* the truth,
which is the unsafe direction. With n = 3 on one thread there is no p95 to use
instead. **What would restore the property is a spread across threads of
differing length** — the two flattened rows in §4 of the proposal differ by 3.2×
in characters, so the spread is likely wide.

**No budget change.** `EXTRACTION_DAILY_BUDGET_USD = 1.00` stands, and it is
slightly more generous than modelled: it now buys ~481 threads a night rather
than the ~418 assumed. Separately and pre-existing: the proposal recommends
`30` and `.env` carries `1.00`, and those two have never been reconciled.

## 6 · Where the numbers are cited

Every one of these was updated in the same commit, and the point of listing them
is that a figure with four homes goes stale in three of them.

| | what it said | now |
|---|---|---|
| `judge/extract/budget.py` | `1300` / `800` | `2010` / `589`, with the coincidence recorded |
| `extraction-budget.md` §4 | the chars/4 derivation | measured, with the old derivation kept for the record |
| `extraction-budget.md` §5 | $4.98 / $7.86 / $30.24 | $5.91 / $9.33 / $35.86 |
| `extraction-budget.md` §5 recommendation | "roughly 1.0× over a ceiling" | 0.84× — no longer covers it, recorded not resolved |
| `CLAUDE.md` rule 2 | "the whole corpus extracts for $2.12" | $1.84, **and its denominator: 887 threads** |
| `tests/test_extraction_budget.py` | `completion(inp=1292, out=500)`, "~610 threads" | the measured call, ~481 |

`contract/` quotes no per-thread or token cost figure — checked, and the only
token figures there are `harvest.yaml`'s dedupe `min_tokens_for_signature` and
capability search topics, which are unrelated.

The test file was the interesting one: it carried a *third* figure, ~610 threads
per dollar, from a fixture default of 1,292 / 500 that no run had produced, in a
docstring calling it "the figure the budget decision was made on". Three
per-thread figures for one quantity, and the one in the test was the one nobody
would have thought to check.
