# Fetching GitHub issue comments — what it costs, and why it is not the Reddit path

**A GitHub issue has children that were never fetched. `issue_body_only` says so;
`whole_document` would not.** That distinction is why this cannot be shortcut —
treating an issue as a whole document asserts a completeness nothing established,
and 7 of the 27 stored issues carry 74 comments between them, one of them 46.

*Engineer 1 · 2026-08-20 · a scope, nothing built ·
`postgresql://bv_agent@52.17.75.29:5432/Model-information-Board`*

---

## 1 · The shape is not Reddit's, and the difference is in our favour

| | Reddit | GitHub issues |
|---|---|---|
| structure | tree, arbitrary depth | **flat list** — every comment's parent is the issue |
| pagination | `more` markers inside the tree | `per_page` ≤ 100 + page param, same shape as the search paging already in `_search_page` |
| what it withholds | **a floor per unsized branch** (`more.count`) | **an exact total up front** — the issue's `comments` integer |
| engagement for ranking | `score` | none; `reactions` only |
| rate-limit class | its own | **core (5,000/hr)**, not search (30/min) |

**The last column of row three is the answer to whether the coverage columns can
be filled honestly: yes, and more precisely than for Reddit.** GitHub states the
comment total on the issue object, and `GitHubHarvester` already captures it into
`engagement.comments`. So after fetching:

```
observed_children       = comments fetched and stored     a measurement
hidden_children_min     = total - fetched                 EXACT, not a floor
hidden_branches_unsized = 0                               a measurement: a flat list has no branches
```

That is better than the state the migration was written for. Its own comment calls
`coverage_ratio` *"an UPPER BOUND on coverage: hidden_children_min is a floor, so
the denominator is understated"* — true of Reddit, **not true here**. Worth
recording before anyone compares the two: a GitHub `coverage_ratio` is exact and a
Reddit one is an upper bound, and the column does not distinguish them.

## 2 · What it costs

**Requests: one core call per issue that has comments, plus one per additional
100.** On the corpus as it stands — 27 issues, 7 with comments, 74 comments, max
46 on one — that is **7 calls**, none of them paginating.

**And it does not touch the binding constraint.** The sweep's ceiling is GitHub
*search* at 30 requests/minute; issue comments are core REST at 5,000/hour, the
same budget `fetch_issue` already spends. So comment fetching is bounded by the
number of issues kept, not by the sweep budget: at the current 1-in-450 keep rate
(6 documents from 2,887 candidates) the comment cost is a rounding error against
the 900-request search cap.

**Storage: +74 document rows** for the current 27 issues — 2.7 comments per issue
across all of them, 10.6 across the 7 that have any.

**What it does not cost:** a new gate. `github-api-terms` covers the API, and
`assert_terms_reviewed` already passes for `github` with `access_path: api`.
Comments are the same endpoint family under the same ruling.

## 3 · The one thing that is genuinely a new decision

**Ranking.** `collect/CLAUDE.md`'s rule 2 is
`specificity_score × log(1 + engagement)`, and Reddit's `selection_method` is
`specificity_x_log_engagement@observed`. **GitHub comments have no score.** They
carry `reactions`, which is a different quantity: a thumbs-up on a bug report is
not an upvote on a comment, and reaction counts on issue comments are sparse.

So one of three, and it is a decision rather than a lookup:

1. `specificity × log(1 + reactions)` — reuses the rule, on an input that is
   mostly zero, which makes it specificity with extra steps and a misleading name.
2. **specificity alone**, written as `specificity_only@observed` — honest, and it
   says in the column that engagement played no part.
3. Position — a bug thread's resolution is usually last. Cheap, defensible, and
   not a rule this project has anywhere else.

**My recommendation is 2**, on rule 3's reasoning: over-ranking is worse than
under-ranking because a wrong pick silently drops the comment flattening exists
to capture. `specificity_only@observed` also keeps the selection auditable — a
reader can see that no engagement signal existed rather than inferring it from a
value that was always zero.

## 4 · What it unblocks and what it does not

It closes the completeness question `issue_body_only` currently declares open, and
it raises `coverage_ratio` on 7 rows from 0.0 to something earned.

**It does not move `platform_count`.** That is computed over the claims backing
one cell (`judge/curate/gate.py:128`), and comments are documents. The distance
from here to a cell reaching 2 is unchanged: triage, entity resolution, authors,
extraction, and `judge/pipeline.py:150`, which still resolves on a field the
extractor is never shown.
