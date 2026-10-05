# Comment selection: code ranking vs an LLM selector vs reading everything

Measured 2026-10-05. Scripts: `scripts/measure_comment_selection.py`,
`scripts/summarise_comment_selection.py`. Raw per-thread results stay on the
machine that ran them (`_comment_selection/20261005T071435Z/`, not committed:
they hold platform quotes and document ids).

## The question

A team suggestion: let a model choose which Reddit replies reach the extractor,
instead of `collect/assemble/ranking.py`'s weighted score.

**Rule 2 forbids shipping that as asked** - "no model participates in ...
ranking, filtering". A model choosing which comments the extractor sees is a
model filtering evidence. This measurement ships nothing; it exists so the
decision about the rule is made on numbers.

## Design

Three arms on the same threads, the same extractor (`deepseek/deepseek-v4-flash`):

| arm | what reaches the extractor |
|---|---|
| A, code ranking | top 25 comments by `rank_children` (production, `child_ranking.max_children`) |
| B, LLM selector | up to 25 comments chosen by the same model reading the post and every comment |
| C, everything | every comment - the arm rule 2 already allows: one model proposes, code verifies |

**Population: 51 Reddit threads**, every thread on this machine whose post and
more than 25 comments were readable in the local raw store (at or below 25, A
and B select the same comments). Not a sample of Reddit; a sample of what was
harvested and kept here. Median 64 readable comments per thread.

**Accuracy is a proxy, stated.** No human labels exist. "Evidence-bearing
comment" = a comment the extractor produced a verified quote from in arm C
(union of two draws). Recall = share of those a selection kept.

## Results

| | A, code ranking | B, LLM selector | C, everything |
|---|---|---|---|
| Evidence-bearing comments kept, pooled (of 769 in 43 threads) | 397 (51.6%) | 432 (56.2%) | - |
| Same, mean per thread (43 threads) | 62.4% | 66.6% | - |
| Verified quotes from comments, total over 51 threads | 544 (1 draw) | 617 (1 draw) | 712 (mean of 2 draws) |
| Cost per thread, list price x measured tokens | $0.00389 | $0.00543 (+39%) | $0.00511 (+31%) |
| of which the selector call | - | $0.00079 median | - |
| Median seconds per extraction | 58 | 72 (+6 for selection) | 85 |

8 of the 51 threads had no evidence-bearing comment in C and are excluded from
recall. A and B shared a median 44% of their selections.

## Why the A-vs-B difference is NOT established

1. **The reference disagrees with itself more than A and B differ.** Two C draws
   on identical input agree on a median Jaccard of **0.45** (43 threads).
2. **Paired, it is a coin flip.** B kept more evidence than A on 20 threads and
   less on 14 (9 tied); two-sided sign test **p = 0.39**.
3. **The reference is incomplete.** 138 of the 383 evidence-bearing comments A's
   own extraction found (36%), and 150 of B's 419, are absent from C - partly
   extractor nondeterminism, partly the next point.
4. **Reading everything breaks on long threads.** 10 of 102 C extractions hit the
   16,384-token output ceiling and produced nothing; 8 of 51 threads had at least
   one truncated C draw. 25 of 102 C draws returned zero quotes.
5. **Same-model bias favours B.** The selector and the extractor that defines the
   reference are the same model, so "what it thinks is useful" and "what it
   extracts from" are correlated by construction.
6. Single draw each for A and B; 5 calls failed and were retried (billed, not in
   the cost figures).

## What it does show

- The selection method is not the bottleneck. The extractor's own run-to-run
  variance (Jaccard 0.45) is larger than any selection difference measured here.
- Reading more comments yields more evidence roughly in proportion to cost
  (C: +31% quotes for +31% cost over A), and stays inside rule 2 - but needs
  chunking before it is usable on long threads, where it truncates.
- An LLM selector costs ~$0.0008 per thread on its own and +39% per thread end to
  end, for a gain this run cannot distinguish from noise.

## If the team wants a decisive answer

Raise the draws, not the arms: at least 3 draws per arm, and more threads than
the 51 readable on one machine. The rule-compliant alternative worth measuring
the same way is a larger `max_children` (for example 40) or a chunked
read-everything arm.

Spend: $0.997 against a $1.00 ceiling (estimate beforehand was $0.65).
