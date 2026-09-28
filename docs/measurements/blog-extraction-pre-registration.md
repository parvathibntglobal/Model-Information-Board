# Pre-registration: extraction over the 30 blog documents

**Written before any model call, so nothing below can be edited into agreement
with what arrives. Two outcomes are GUARANTEED and neither is a defect in
extraction — recorded here so that a run producing good claims and publishing
nothing is not read as a failure.**

*Engineer 1 · 2026-08-20 · agreed with Engineer 2 before the run ·
`postgresql://example_user@203.0.113.5:5432/Model-information-Board`*

---

## 1 · Nothing publishes, and it is the corpus rather than a gap

**The `dc:creator` fix landed, so this is now arithmetic over real rows rather
than a statement about a missing writer.** On staging: `author` holds **1 row**,
**30 of 30** blog documents carry an `author_id`, and there is **1 distinct
author** across all thirty.

```
n_eff             sums claim weights over representatives, one per voice_id
                  -> 1 voice, so n_eff <= 1.0 whatever the claims say
N_EFF_MINIMUM     3.0                       (gate.py:24)

max_author_share  max(per_author) / n_eff = 1.0
AUTHOR_CAP        0.50 below five voices    (gate.py:26)
                  -> 1.0 > 0.50, so the diversity rule trips INDEPENDENTLY

platform_count    1 — every one of the thirty is `blog`
PLATFORM_MINIMUM  2                         (gate.py:25)
```

**Three gates, each failed on its own, and none of them is about extraction
quality.** Thirty perfect first-hand capability observations from one byline would
fail all three identically. `insufficient` is the correct output for this corpus.

**Why this is written down in advance:** a run producing good claims and
publishing nothing reads as an extraction failure. It is not one. It is a true
result carrying a false meaning — the mirror of the over-read, where a true quote
carries a false claim.

**And it is falsifiable.** If a cell from these thirty ever reports
`independent_voices > 1`, a voice has been invented: an `entry`-byline path
attributing articles to the wrong author, or an anonymous row shared between
documents. The count is a check now, not only an outcome.

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
