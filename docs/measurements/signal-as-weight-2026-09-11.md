# Signal demoted from a gate to a weight — the measurement, and what it costs

*2026-09-11 · `collect/adapters/queries/sieve.py:GATING_GROUPS`. The vocabulary
is untouched: 198 terms, none added, none removed.*

---

## 0 · The decision in one table

Population: the **772 documents** present in both the model-only Reddit sweep
(`model_only_sweep_corrected.jsonl`) and the withheld-keys capability-discovery
run (`docs/measurements/model-only-classification-withheld.jsonl`,
`google/gemini-2.5-flash`, 774 documents, $0.4407).

| sieve verdict | n | discovery pass says "capability report" | rate |
|---|---|---|---|
| kept — subject+topic+signal | 32 | 29 | **90.6%** |
| **refused on signal alone** | **291** | **254** | **87.3%** |

**Fisher exact, two-tailed: p = 0.78.** Among documents already clean on
subject and topic, signal was not separating capability reports from
non-reports. Its precision was 90.6% against an **87.6% base rate** — three
points above answering "yes" to everything — and it bought that by discarding
**254 of the 283 reports (89.8%)**.

Restricted to the 183 of 254 whose quotes verify by exact substring (rule 1),
signal still refused 183 against the 24 verified reports it kept: **88%**.

**Rule 8 permits this direction and only this direction.** *"An unmeasured
check ships as a weight, not a gate… weight first and gate later on evidence,
never the reverse."* Signal was gating on a vocabulary last edited 2026-08-14,
fitted against the twelve fixed capability keys, never re-fitted after
capability discovery existed.

## 1 · What changed in the code

```
GATING_GROUPS = ("subject", "topic", "locality")     # signal deliberately absent
passed = not [m for m in missing if m in GATING_GROUPS]
```

`missing` **still names signal** when it is absent — `tally` counts it,
`sieve_any` ranks on it, `scripts/harvest_github.py` reports it. Only its power
to refuse is gone. Added: `SieveVerdict.signal_score` (a COUNT of distinct
signal terms in the author's own prose, never a synthesised figure — rule 3),
`signal_present`, `describe()`, and `SieveYield.kept_with_signal`.

**Locality is unchanged and still requires all three groups.** It measures the
distance from a topic hit to a *signal* hit; with no signal there is no
distance and no proximity claim to refuse.

## 2 · What the sieve keeps now

| population | before (gate) | after (weight) | |
|---|---|---|---|
| **1,925-post listing sweep** (`_unfiltered_sweep`, 2026-08-18) | 3 = 0.16% | **73 = 3.79%** | **×24.3** |
| **75-post three-sort probe** (2026-09-11) | 0 | **10 = 13.3%** | 0 → double digits |

Per sort on the 75: NEW 3/25, RELEVANCE 6/25, TOP 1/25.

⚠ The 75-post figure is a **lower bound**, recomputed from the stored
`sieve_any` verdict — which was chosen by fewest-missing under the old rule, so
a term set missing only `signal` could have lost a tie-break to one missing
`subject`. It cannot overcount.

**This is the number that answers the question.** Reddit was returning 0 of 75
and 3 of 1,925 not because the platform is thin but because a vocabulary fitted
elsewhere was refusing it. 169 of the 198 signal terms fire nowhere in those
1,925 posts, and all 100 of the surviving `dead_both` terms fire zero times.

**And the weight survived the demotion.** Of the 73 now kept, 3 carry
`signal_score >= 1`. On the stance pair in `tests/test_queries_render.py` the
score separates perfectly — 1 where the entry's stance matches the document, 0
where it does not, on all four combinations — so the information signal carried
is intact and is now available for ranking instead of spent on refusal.

## 2b · GitHub and blogs — measured, and my inference was wrong

*Added 2026-09-11 after §5 flagged this as the biggest gap. Stored documents on
staging, text resolved from the local raw store, both gates on the same
documents.*

| source | documents | kept (gate) | kept (weight) | multiple | extraction cost delta |
|---|---|---|---|---|---|
| **github** | 3,382 | 8 = 0.24% | **218 = 6.45%** | **×27.25** | +$0.57 |
| **blog** | 121 | 0 = 0.00% | **12 = 9.92%** | n/a (gate kept none) | +$0.12 |
| reddit (§2) | 1,925 | 3 = 0.16% | 73 = 3.79% | ×24.3 | +$0.20 |

**THE INFERENCE IN THE FIRST DRAFT OF THIS PAGE WAS WRONG, AND IT IS WORTH
KEEPING THE CORRECTION VISIBLE.** It said: *signal is 5× more alive on GitHub
— 16.25% of candidates carry some signal term against 3.4% of Reddit posts —
so the demotion should move GitHub proportionally less.* It moves GitHub
**more**: ×27.25 against Reddit's ×24.3.

The error is rule 7's exact shape and I flagged the figure as an inference
without catching it. **16.25% counts candidates carrying ANY of the 198 terms.
The gate is per-entry ANY-OF over a median of 8 terms, with locality on top.**
The aggregate liveness of the vocabulary was never the quantity that predicts
the gate's behaviour — it is a real number answering a question it was not
asked, and the per-entry rate (0.39% on GitHub, `signal-vocabulary-ruling.md`
§3) was the one to reason from all along.

**Blogs kept ZERO documents under the gate**, across the whole 121-document
corpus. `signal_in_excluded` and the essay-register argument in
`signal-vocabulary-ruling.md` §2 both pointed here; this is the count.

Two notes on the population: 9 GitHub and 1 blog document could not be
resolved from the raw store (one raised the `missing with no tombstone` NFR-4
warning, which is a pre-existing store defect and not caused by this change),
and they are excluded from the numerator and the denominator alike. And 8 of
GitHub's 218 carry `signal_score >= 1`; blogs carry none.

## 2c · X — the gate refuses everything, so pagination cannot help

*Added 2026-09-14. `scripts/measure_signal_demotion_x.py`,
`docs/measurements/signal-as-weight-x-2026-09-14.json`.*

**X has zero rows in `document`.** The adapter has never completed a write, so
unlike GitHub and blogs there is no stored corpus to measure. What exists is the
post text captured by the two X retrieval probes of 2026-09-11, run for a
different purpose (boolean-OR reach, and surface clubbing).

| | |
|---|---:|
| posts captured by the two probes | **127** |
| of those, naming a seeded surface | 72 |
| **kept by the gate (signal gating)** | **0** |
| kept by the weight (signal demoted) | **6** |
| of those 6, `signal_score >= 1` | 0 |

**This is the operationally important one even though it is the smallest
population.** X has been investigated twice as a credentials problem and once as
a pagination problem. Neither could have produced a document: **the sieve refuses
every X post we have ever seen**, so a fixed credential returns more posts that
are all discarded, and pagination multiplies a zero. The demotion is what takes
X off zero.

⚠ **THE POPULATION IS NOT X, AND THE DENOMINATOR HERE IS DOING REAL WORK**
(rule 7). These 127 posts are what two probe runs returned for five seeded
Fable 5.1 surfaces on one day, selected by `Latest`. `6/127` is **not** an X
retrieval rate and must not be quoted as one. What the table supports is the
qualitative claim and nothing finer: under the gate the number is zero, and zero
does not improve with more requests.

**Correcting a figure I stated earlier in conversation:** I said "0 of 280 X
posts". The zero is right; **280 is not a population I can source** — the probe
files carry 127 distinct posts. Recorded because an unsourced denominator is the
rule-7 failure this project keeps finding, and it is worse when it is mine.

## 3 · What it costs

Per-document cost from the measured regression, **n = 195 real extractions**
(`comments-shapes-and-the-legacy-weights.md` §4), not the superseded n=3 rate:

```
input_tokens = 2,683 + 0.6016 x chars       output = 636 tokens/call
priced at contract/seed_models.yaml: $0.30 in / $2.50 out per 1M
```

| | before | after | delta |
|---|---|---|---|
| extraction calls, one nightly sweep | 3 | 73 | **+70** |
| cost, one nightly sweep | $0.0091 | $0.2096 | **+$0.20** |
| **cost, 30 nights** | | | **+$6.01** |

Cross-check: the implied rate is **$0.00287/document** against the measured
corpus mean of **$0.00299** over 207 extractions — 4% apart, so the regression
is being applied to documents of a typical size.

**After triage, which sits between the sieve and extraction**, at the recorded
~10–15% survival: **+7 to +10 documents a night**, **+$0.60 to +$0.90 a month**.

Two caveats travel with every figure above: it is a measured token count times
a **seeded** price, not a billed amount; and the 1,925-post sweep is one
night's shape, so the monthly figures assume the sweep runs nightly, which it
does not today — nothing schedules the chain.

## 4 · The honest cost, which is not the dollars

**A vague positive now reaches extraction.** `"claude-sonnet-5 summarization is
great, no complaints"` names the model and names the capability; the only thing
that ever refused it was the absence of a signal term. It is kept now, with
`signal_score = 0`, and it pays for a call. That is what the other 12.7% looks
like, and the layer that must still refuse it is the extractor —
`contract/queries.yaml`'s third rule, *"DESCRIBES BEHAVIOUR, NOT SENTIMENT"*, is
about exactly that sentence.

**The author-prose exclusion no longer changes any pass/fail outcome.** It was
built so a signal term inside a blockquote could not carry a document; with
signal not gating, its only remaining effect is on `signal_score`. That is a
real reduction in what it does and the tests now say so rather than asserting a
refusal that no longer happens. The exclusions were measured to cost 15%, not
90% (`the-signal-group.md` §3) — cheap to keep, and they now feed the weight.

## 5 · What is NOT established

- **That the classifier is right.** `is_capability_report` is
  `google/gemini-2.5-flash`'s reading. It proposes; nothing here decides. The
  87.3% is what a discovery pass *found*, not ground truth.
- **That the kept documents yield claims.** This measures what reaches
  extraction, not what survives it. The extractor's own refusal rate on this
  wider intake is unmeasured and is the next thing worth measuring.
- **That the 101 dead terms should be cut.** `docs/signal-vocabulary-ruling.md`
  §4 says DELETE waits for the fuller corpus, and this change makes deletion
  *less* urgent rather than more: a dead ANY-OF term that cannot refuse
  anything costs nothing but a substring test.
- **Anything about the contract.** `contract/queries.yaml` is unedited. Its
  description of `terms.signal` as "ANY-OF. Carries the stance" is still true
  of the GROUP; it no longer implies a refusal, and a one-line wording change
  saying so is worth a PR with two eyes on it. Not taken here.
