# Master-idea corpus checks, 2026-11-03

Two read-only measurements on the shared database, taken to test whether our
own corpus carries the story the web research found. Counts only; no post text
is recorded here (Reddit, X and Bluesky text is not ours to publish).

**Population, both checks:** the 3,998 documents behind at least one published
(not declined) `board_entry`. Their post text was readable from this machine
for **1,671** (raw_blob or the local raw store); the other 2,327 - including
1,230 of the 1,627 Reddit documents - have no stored text reachable here, and
neither do their flattened threads. The counts below are word matches, not
readings of meaning (rule 7).

## 1. The five pains (`master-idea-pains-2026-11-03.py`)

Documents whose readable text matches each pain's word pattern, of 1,671:

| Pain | Documents |
|---|---|
| price on the label vs real cost | 203 |
| rationing (rate limits, quotas, weekly limits) | 129 |
| staying put ("stick with", "went back to") | 38 |
| not knowing / drift ("nerfed", "got worse") | 30 |
| exhaustion | 15 |
| overwhelm ("too many models") | 4 |

Collection is per model, so posts about one model come in and general
"too many models" posts mostly do not - the low overwhelm count is partly how
we collect, not only what people write.

## 2. Is there a monthly Field Index in it? (`field-index-switching-2026-11-03.py`)

A candidate = one sentence with a switching verb ("switched to", "moved from",
"went back to", "replaced X with", "instead of", ...) and at least two model
names from a fixed list.

- in a published quote: **36** of 3,998 documents
- in the readable post text: **42** of 1,671 documents
- either: **69** documents, **67** distinct people; **37** dated October 2026
- by source: dev.to 25, Hacker News 13, GitHub 12, X 8, Reddit 7, Bluesky 3, arXiv 1

**Precision, read by hand on the first 14 candidates: 3 are a person saying
they moved between models.** The rest are comparisons ("instead of",
benchmark "swapped places"), vendor statements ("50% price reduction when
migrating"), or two names for one model ("Claude" and "Opus").

At about 3 in 14, October's 37 candidates are roughly **7 real switch
reports** - an estimate from a 14-sentence sample, not a count. Too few for a
monthly index that names pairs. The October bump also follows when we
collected, not only when people moved.

**What a Field Index would need first:** the extractor recording a switch
(from, to, why) as a field - which existed once as `comparison_target` and
was dropped before any column (rule 9's first instance) - and collection that
asks for switching posts rather than only per-model queries. Both are
proposals for the team, not changes made here.
