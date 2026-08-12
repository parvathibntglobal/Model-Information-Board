# fixtures/

**Both engineers write here.** Everything in this directory is a build
fixture — load-bearing while building, and removed or superseded before
launch.

## `hand_cells.yaml` — Engineer 2, week 2

Hand-written cells for ~15 models × 12 capabilities, so the Ask box works
before any real evidence exists. It is your opinion, and that is fine — the
UX test in week 3 cannot tell the data is fake, and that is the whole point.

**Loads with `provenance: hand_curated`. Deleted in week 8**, with a startup
assertion so it can never be served as evidence.

## `golden/` — labelled in week 3, before any extraction runs

Needs no code, which is exactly why it slips if you leave it inside a build
week. It gates extractor selection: you cannot choose one on measured
F1-per-dollar without a set to measure against, and choosing by assertion
undermines the one component the whole guarantee rests on.

| Set | Size | Protects |
|---|---|---|
| `extraction/` | 80 | Flattened threads with hand-written expected claims — the Reader |
| `entity_resolution/` | 200 | Mentions. A claim on the wrong snapshot is worse than no claim |
| `filter/` | 200 | Documents: slop / genuine / genuine-but-AI-polished |

**Engineer 2 owns the labelling. Engineer 1 cross-labels ~50 items.**

That cross-labelling is not a formality — it produces an agreement number. If
two people who both read the spec disagree on what counts as good evidence,
the criteria are not yet clear enough to automate. Far cheaper to learn in
week 3 than week 6.

> **What "slop" means here:** content generated to farm engagement — *not*
> "written with AI help". A real engineer's genuine writeup polished by a
> model must survive. Label on **falsifiability**: slop is unfalsifiable by
> construction. Getting this wrong is how the filter removes exactly the
> signal it exists to protect.

**Precision over recall.** Falsely dropping one rare tier-A report costs far
more than low-weighted slop slipping through.

## `threads/` — built together, around week 4

Twenty real threads with the claims they should produce, hand-written.
Engineer 1 flattens them; Engineer 2 extracts from them.

The fastest way to find a `document` / `thread_context` contract mismatch
while fixing it still costs an hour instead of a week.

## Growing the golden sets

Do not build large sets up front. **Every production miss becomes an entry.**
A filter that wrongly rejected a good GitHub comment, an extraction that
attached a claim to the wrong model — those are worth more than fifty
synthetic examples, because they are the failures that actually happen.
