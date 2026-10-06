# Interactive blogs

**Proposed 2026-10-06 by anooj + Claude.** Today's posts (GPT-6 Luna, document
synthesis, seven formats) read as ~10-minute essays. This scopes a second kind of
post - one the reader interacts with - and what every technique must respect.

## The principle: the model picks the block, code fills the data

A post today is prose the model wrote once. An interactive post is prose plus
**live blocks**. The generator chooses *which* block goes *where* and what
question it answers; code fills the data from the database **when the page
loads**. That is rule 2 ("an LLM may propose, it may never decide") applied to
layout: the model never types a number into a chart, so every chart and counter
is a real count or a measured price, and a post written in October is still
right in December.

Mechanically: the post format already has blocks (`h2`, `p`, `table`, `tree`,
`quote`, `code`, the format's special). New block types - `chart`,
`live_count`, `model_card`, `calculator`, `filter` - carry a **data query id**,
not data, and the page fills them from endpoints that exist: `/models`,
`/compare`, `/board`, `/capabilities/{key}`, `/models/{id}/evidence`.

## Techniques

### A. Linking inside the text
1. **Smart entity links** - model, capability and benchmark names link to their
   pages; "X vs Y" links to the comparison page once it is published. Generated
   from the post's own provenance, never hand-written.
2. **Hover model cards** - price, context window, reports, last fetched.
3. **Evidence drawer** - a claim opens to the verbatim quotes behind it.
4. **"Where is this number from?"** - every figure says what was counted, over
   what population, as of when (rule 7, made visible).
5. **Counter-evidence toggle** - "show reports that disagree".

### B. Live data inside the post
6. **Live counters** - "28 reports from 19 engineers - updated today".
7. **Embedded mini-board** - the capability section in its three groups:
   working, problems, not discussed (rule 4).
8. **"Since this was written"** - new reports and price changes since publication.
9. **Living posts** - a model changelog whose sections refill weekly.

### C. Comparison posts
10. **Model picker** - swap either model in "A vs B".
11. **Workload filter** - coding agent, RAG, extraction, support bot.
12. **Clickable decision tree** - step-by-step, ending on a phrase assembled
    from counts, never a score (rule 3).
13. **Side-by-side evidence** - capabilities aligned across two models.

### D. Illustrative / data-story posts (the model writes only captions)
14. Price vs context scatter (measured).
15. Reports over time, release date marked.
16. Working vs problems per capability - counts with their totals.
17. Model x capability grid - counts, three distinct states, silence visible.
18. A model's life story - release, price changes, reports, deprecation.
19. Migrations "moved from X to Y" - from the substitution evidence E5 extracts.
20. Benchmark table - sortable, every figure linked to its quote.

### E. Calculators (the reader's inputs x measured prices)
21. **Cost calculator** - tokens/day and cache-hit rate to monthly cost; the
    formula is shown - the reader's arithmetic, not our rating.
22. **Will my document fit?** - advertised window vs where problems are reported.
23. **Migration checklist** - reported breakages for a from/to pair.

### F. Reader participation (later; each adds obligations)
24. "Useful? / Matched your experience?" - feedback only, never evidence.
25. Watch a model - needs email infrastructure and consent.
26. "Guess the model" from anonymised quotes - a publication question.

### G. Navigation and format
27. Section-following table of contents; jump to the verdict or the evidence.
28. Audience tabs - engineer view and decision-maker view.
29. "How we know" - one real quote traced from harvest to verification.
30. Copy-ready configs with a "tested by N reports" badge.

## What every interactive block must respect

- **Counts and measured prices only** - no synthesised score, rating or
  percentage without its denominator (rules 3 and 7).
- **The model proposes, code decides** (rule 2).
- **Publication.** Live widgets on the public site read the public view, which
  withholds Reddit, X and arXiv (`contract/publication.yaml`). The prose may draw
  on them (the derived-posts exception) while the live counts beside it do not,
  so every widget carries the "some sources are not shown" notice.
- **Search engines** do not run JavaScript reliably: the key facts and a static
  fallback stay in the server-rendered HTML.
- **Silence is not criticism** (rule 4): any grid or chart keeps "not
  discussed" distinct from "problems reported".

## Phases

| Phase | Builds | Why in this order |
|---|---|---|
| 1 | entity links, model cards, number provenance (1, 2, 4) and a path to the evidence (3) | uses data already served; upgrades existing posts |
| 2 | a `chart` block and one data-story format (14-17) | the "purely illustrative blog" |
| 3 | comparison interactivity, workload filter (10-13) | needs the published comparison page |
| 4 | calculators, live and living posts (6-9, 21-23) | more computation and freshness work |
| 5 | participation (24-26) | moderation, consent, terms |

## Phase 1, as built on 2026-10-06

Opt-in per post: a post with `"interactive": true` gets the enhancements; the
rest render as before, so the change can be reviewed on one post first. The
example is `head-to-head-deepseek-deepseek-v4-flash-z-ai-glm-5`.

- **Entity links** - each tracked model's name (as the page lists it) becomes a
  link to its evidence on the board, first mention per paragraph, longest name
  first so "GPT-6.1 Sol Pro" is never split into "GPT-6.1 Sol".
- **Model cards** - on hover or keyboard focus: list price in/out per 1M tokens,
  advertised context, board entries, and a link to read them. Figures come from
  `/models?tracked=1` at page load, not from the post.
- **Number provenance** - a verbatim «» fragment says it is quoted from a
  practitioner report; a dollar figure outside quotes says it is the registry
  list price at generation (the generator refuses any number found neither in
  the sources nor in the price sheet, which is what makes that claim true).
- **Path to the evidence** - the model card's "read the N reports" opens the
  model's board view; a per-claim drawer (3) needs claims mapped to board
  entries, which the generator does not record yet - Phase 1b.
