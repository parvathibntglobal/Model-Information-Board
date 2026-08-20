# The first GitHub sweep, and what its numbers are measured over

**Two runs, two populations, and one figure that is a tautology rather than a
result.** Recorded because both were about to be compared to earlier measurements
that answer different questions.

*Engineer 1 · 2026-08-20 · `postgresql://bv_agent@52.17.75.29:5432/Model-information-Board`
except where the local harness is named · code on branch `load-tracked-set`, not
yet on `origin/main`*

---

## 1 · The two runs, with their populations

| | run A, local harness | run B, staging |
|---|---|---|
| DSN | `localhost:5433/modelboard_harvest_test` | `52.17.75.29/Model-information-Board` |
| model | `google/gemini-2.5-flash` (seed) | `openai/gpt-4` (seated) |
| aliases | 6, from `seed_models.yaml` in memory | from `model_alias` |
| entries | 6 (3 capabilities) | 18 (daily cadence) |
| requests issued | 38 | 32 |
| candidates | **638** | **2,887** |
| kept | 0 | 6 |
| documents stored | 0 | 6 |
| throttling | none | three 403s, 16–22s backoffs |

Run B was preceded by a run that died at ~121 queries on a dropped connection
after storing 21 documents; its group counters were lost with it, so it is not a
population in this table. **Staging holds 27 GitHub documents from the two
surviving runs together.**

## 2 · The 96% is the seating, not the corpus, and not comparable to 52.7%

**A document retrieved by a query containing the alias mentions the alias by
construction.** The search string *is* the alias, and the sieve's `subject` group
is ALL-OF — so a document that was retrieved and stored has matched a subject term
twice over: once to be returned by GitHub and once to survive the sieve.

So a near-100% "mentions a tracked model" rate over **stored documents** measures
the retrieval query and the keeping rule. It is a tautology of the selection.
Anything materially below 100% is a defect worth chasing, not a rate worth
quoting.

**The 52.7% measured earlier is over candidates RETRIEVED, before the sieve** —
"how often does GitHub's search return something that actually names the model I
searched for". Different population, different question, and the two must not be
placed in a sequence as though one improved on the other:

```
52.7%  subject match  /  636 candidates retrieved for one model, pre-sieve
61.1%  subject match  /  2,887 candidates retrieved for one model, pre-sieve   (run B)
~100%  mentions alias /  6 documents stored, post-sieve                        (by construction)
```

**Nothing in the database records the third figure**, which is the other reason not
to quote it: `names_version` is NULL on all 27 GitHub documents, so no document is
yet *known* to mention a tracked model. The entity gate has not run.

## 3 · The signal group, and a correction to what the counter measures

Signal is the binding group and it is rare at both scales:

| population | signal hits | rate |
|---|---|---|
| 638 candidates (run A) | 7 | **1.1%** |
| 2,887 candidates (run B) | 21 | **0.7%** |
| **3,525 combined** | **28** | **0.79%** |

So the answer is stable across a 4.5× larger denominator, which is the finding.
**It is not zero.**

**And "0 in author prose" is the opposite of what was measured.** The counter is
`signal_in_excluded_docs`, and it counts documents whose signal terms appear
**only** inside quoted or fenced spans — the containment rule's own failure case.
It read **0 of 638**, which means *no* document's signal was confined to code or
quotes: every signal hit that fired was in author prose. A zero there is the
containment rule finding nothing to exclude, not a vocabulary that never fires in
sentences.

**A per-term breakdown — "12 of 15 terms firing" — is not something either run
produced.** Both report group-level hits. Recorded as a gap: the sieve returns
matched terms per verdict (`SieveVerdict.signal`), so the count is available and
is not being aggregated. Worth adding before the vocabulary is judged.

## 4 · The cap, and why the earlier timing figures are void

`harvest.yaml`: *"Requests per sweep, per cadence. The ceiling, not the target."*
Daily is **900 requests / 35 minutes** — both halves, and the contract says why
the minute figure is checked separately: *"the minute figure is the one that
survives a rate-limit change."*

Run B proved that inside 32 requests: three 403s with 16–22s backoffs. **So every
projection built from per-request latency is void**, including the 63.6-minute and
79-minute figures. Requests and minutes come apart exactly where a throttle
appears, which is why the contract caps both.

The daily plan across 40 seated models is **2,144 requests**, 2.4× the cap. A
sweep therefore covers part of the population and must name the rest: 13 models
fit, 27 unreached.

## 5 · Assembly: 27 of 27, and the third shape is not in the data yet

Every stored GitHub document now has a `thread_context`.

```
59 thread_context rows:  30 whole_document (blog) · 27 issue_body_only (github)
                          2 specificity_x_log_engagement@observed (reddit)
coverage_ratio:  20 NULL (no comments — empty tree) · 7 at 0.0
hidden_children_min:  74 comments unread across 7 issues, max 46 on one
```

**A GitHub issue with comments would be a third shape and is not what is
stored.** `GitHubHarvester` records `comment_count` into `engagement` and never
fetches a comment, so all 27 rows carry `parent_id IS NULL`: each document is the
issue body alone, structurally the blog case. Building a tree assembler now would
build it against no data.

What the assembler does instead is record what it did not read.
`hidden_children_min = comment_count` puts `coverage_ratio` at **0.0** — we read
the root and none of the thread — where `0` would have produced NULL, *"an empty
tree"*, which an issue with 46 comments is not. `selection_method` is
`issue_body_only` rather than `whole_document` because the blog value is true of a
blog and would be false here, and because these rows must be findable again the
day comments are harvested.

## 6 · What `platform_count` reads: nothing yet, and that is not 1

`judge/curate/gate.py:128` computes it as `len({c.platform for c in
representatives})` over the **claims** backing one cell. `claim` holds 0 rows and
`cell` holds 0, so there is no cell for a platform_count to belong to — it is
neither 1 nor 2.

What assembly changed is upstream of it and real: `judge/` reads
`thread_context`, so before this the 27 GitHub documents were **invisible to
extraction**. The corpus now carries two platforms of assembled context, and the
gate will read 2 the first time a cell is built from claims spanning both.

What remains between here and that figure, measured on all 27:

```
triage_verdict  NULL ×27      names_version NULL ×27      author_id NULL ×27
claim 0                       cell 0
```

Plus `judge/pipeline.py:150`, which still resolves on `resolved_version_id` — a
field the extractor is never shown — and drops every claim.
