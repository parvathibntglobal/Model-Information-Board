# Pre-registration: extraction over the 30 blog documents

**Written before any model call, so nothing below can be edited into agreement
with what arrives. Two outcomes are GUARANTEED and neither is a defect in
extraction — recorded here so that a run producing good claims and publishing
nothing is not read as a failure.**

*Engineer 1 · 2026-08-20 · agreed with Engineer 2 before the run ·
`postgresql://bv_agent@52.17.75.29:5432/Model-information-Board`*

---

## 1 · Guaranteed outcome one: every cell will be `insufficient`

**Not a prediction. Arithmetic, for three independent reasons, and fixing the
first two does not remove the third.**

**`author` holds 0 rows and `author_id` is NULL on all 57 documents.**
`gate.py:116` sums weights over representatives keyed by `voice_id`, and
`gate.py:131` derives `max_author_share` from per-author counts. With no author
there is nothing to count, so `n_eff` has no input.

**And fixing that does not reach the bar, because this is a one-author corpus.**
30 link-blog entries from one byline is **one voice**, however many claims come
out of them. `n_eff` needs roughly 3.0 — about four independent voices — and a
single author cannot produce a second one.

**And `platform_count >= 2` needs a second platform inside the same cell** — one
model, one capability, one condition bucket. The GitHub documents are a second
platform in the corpus and would have to land in the *same* cell to count.

So: **no cell can publish from this corpus.** `insufficient` is the correct
output and it is not a bar that better extraction clears.

**Why this is stated in advance:** a run producing good claims and publishing
nothing reads as an extraction failure. That is a true result carrying a false
meaning — the mirror of the over-read, where a true quote carries a false claim.

## 2 · Guaranteed outcome two: over-extraction from our own template

**27 of 30 flattened documents carry a "Recent articles" block from the site
template, every one of those blocks names models, and 13 documents name a model
only there** (`blog-corpus-characterisation.md §1`).

**So the specific prediction, before the run:** claims will be produced about
models the document's own text never discusses, quoting another post's headline,
and **they will pass verification** — because the sentence really is in the text
the extractor was shown. The most likely three, since they appear across the
corpus:

```
"Qwen 3.8 27B is excellent, but it defaults to wildly overthinking things"
"One-shotting a Raccoon Heist game using Claude Fable 5"
"Now we have a timeline of the OpenAI accidental attack against Hugging Face"
```

**If those quotes appear attributed to unrelated posts, the run measured our
flattener and not the extractor.** That is not a yield figure and must not be
recorded as one.

**Recommendation: do not run until the block is stripped.** The fix is in
`collect/` — `assemble_article` flattens what trafilatura returns under
`DEFAULT_EXTRACTION`, and the recent-articles list is surviving it — and it is
mine. A run before that costs $0.062 to measure a defect already measured for
free.

## 3 · What the corpus could support, if it were clean

**At most 4 documents** carry a first-hand capability observation
(`introducing-muse-glimmer`, `openclaw`, `alchemy-utils`, `deepseek-v4-pro-0813`
— each with at least one `I ran|tried|found` construction). **23 carry relayed
claims** — announcement, model card, benchmark, or template — and **3 name no
model at all**.

Capabilities plausibly reachable, from the article bodies rather than the
template: **verbosity / overthinking** and **cost or tier comparison**. Nothing
in this corpus speaks to tool-calling schema accuracy or effective context
window, so a claim at those keys from these 30 documents is itself a signal to
check.

**So the honest expected yield is 0–4 claims** over 30 documents, all
`insufficient`, and 0 is a legitimate result.

## 4 · What would be over-extraction rather than yield

Stated in advance so the distinction is not made after the fact:

| observation | reading |
|---|---|
| more than ~6 claims | over-extraction. There are 4 first-hand documents and 30 chances to borrow from a template |
| any claim quoting the three headlines above, on a post about something else | the template defect, not yield |
| a claim at `tool_calling.*` or `context.*` | nothing in the corpus supports it |
| a claim whose quote is a vendor's or benchmark's words presented as the author's report | the vendor-announcement shape from the seven, one platform over |
| 0 claims | a legitimate result on a link-blog corpus, and not a broken extractor |

## 5 · Cost, named rather than absorbed

**30 documents × $0.00208 measured per call ≈ $0.062.** Against the $1.00
`EXTRACTION_DAILY_BUDGET_USD` that is **6.2% of the daily cap in one run** — not a
rounding error, and worth spending only once the template block is out. The
$0.00208 is itself from n=3 calls on one thread
(`docs/measurements/extraction-token-counts.md`), so it is a measured figure with
a small population, not a rate.

## 6 · This is a different population from the seven

```
the seven      1 Reddit thread (6 comments) + 1 blog post, mixed authorship
these thirty   30 link-blog entries, ONE author, ONE site
```

The seven predicted zero for reasons of **content** — three billing, one vendor
announcement, one relayed benchmark, one naming no model, two capability-shaped
of which one was unattributable. These thirty predict a bounded yield plus a
template artefact, for different reasons, one of which is our own defect.

**The zero-expected does not carry over and the numbers are not comparable.** Any
figure from this run stated beside a figure from the seven has to name which
population it came from.
