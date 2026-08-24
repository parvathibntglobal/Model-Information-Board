# 195 comments, 152 authors — and the binding constraint is not what we assumed

**The thread is stored. Concentration stopped binding, exactly as predicted. It
is not `platform_count` that took over — it is `n_eff`, and it is not close.**

```
documents   64 -> 254        reddit  6 -> 196
author rows  1 -> 153        reddit  0 -> 152 distinct authors
```

And the survival estimate met a corpus for the first time: **8.7%, below the
10–15% band, and an upper bound.** The reason 178 of 195 comments drop is the
inherited-subject problem, which extraction solves by inheriting and triage
solves by discarding.

*Engineer 1 · 2026-08-21 · no model calls; writes to `52.17.75.29`*

---

## 1 · Why all 195 and not the selected five

`scripts/export_thread_contexts.py` wrote documents for
`assembled.member_document_ids` — the children `assemble/thread.py` selected for
flattening. Five of 195. It answered one question with the other:

```
selection for extraction   which children does the extractor read?
                           a ranking problem, bounded by prompt budget
storage as evidence        who spoke in this thread?
                           a counting problem, bounded by nothing
```

The 190 unselected comments are not weaker evidence — **they are the voices**,
and `judge/curate/gate.py` counts people rather than passages. Five documents can
carry at most five voices in a thread with 151.

### The write, measured

```
payload   fixtures/reddit/thread-1u1b22l-getPostComments.json
comments  195      coverage: observed=195 hidden_min=623 reported_total=785

items to write            196   (root + 195 comments)
carrying author_fullname  193
WITHOUT one                 3   -> no author row, no shared row
distinct author ids       152
```

```
                 BEFORE                          AFTER
blog     docs=31   with_author=30  distinct=1     unchanged
github   docs=27   with_author=0   distinct=0     unchanged
reddit   docs=6    with_author=0   distinct=0     docs=196 with_author=193 distinct=152
TOTAL    docs=64   with_author=30                 docs=254 with_author=223
author rows: 1 {blog: 1}                          153 {blog: 1, reddit: 152}
```

The 31 still without an author are 27 GitHub (payloads absent from this host),
3 authorless Reddit comments, and 1 blog article — each named, none shared.

### A defect the first run exposed

`documents_inserted` was **190 of 196**. The other 6 already existed, so
`ON CONFLICT DO NOTHING` conflicted them away — **and they kept `author_id`
NULL**, permanently, however often the writer re-ran, because a silent conflict
looks exactly like a successful write.

`ON CONFLICT DO NOTHING` is right for every column except this one. NULL in
`author_id` was never a value anybody chose; it is the absence the writer exists
to close. `write_documents` now issues the guarded update
(`WHERE author_id IS NULL`, so a real attribution is never overwritten) and
reports `authors_attached_to_existing` separately — because a re-run that
attributes 6 old rows and inserts 0 is doing real work, and one "written"
counter would show it as a no-op. The second run:

```
documents_inserted             0
authors_attached_to_existing   6      -> reddit with_author 187 -> 193
```

**21 tests.** The one that carries the point builds 115 authorless comments — the
corpus-wide count — and asserts no author rows, no shared id, and
`unattributable == 115`.

---

## 2 · `alias_match_count` in the sweep, and why it was fixed in the export

**A list matching nothing records identically to a list matching everything.**
That is the defect, and it has now appeared in two places with two different
surfaces:

```
export_thread_contexts.py   recorded the alias TUPLE in provenance and read it
                            as a scoring input. `version_aliases()` returned 35
                            strings for weeks and matched ZERO documents.
harvest_github.py           printed `aliases : 35 [...]` — the LENGTH of the
                            list. 35 aliases that match nothing print the same
                            as 35 that match everything.
```

It was fixed in the export and not carried because the export is where it *hurt*
— a provenance block claiming an input that did nothing made a staging row look
reproducible when it was not. The sweep's version looked like a log line rather
than a record, so it read as cosmetic. It is not: a sweep retrieving on dead
variants looks exactly like a healthy one, because the aliases are in the query
string either way and the query still returns results.

`alias_match_count` now lives in `collect/triage/specificity.py` — **one
implementation, two callers** — beside `names_version`, which is what it counts.
The sweep computes it and prints it with its population:

```
=== aliases: 35 declared, N matched M stored docs (x%) ===
  ZERO. The variants contributed nothing to what came back; `names_version`
  scored False on every stored document and any ranking that read it ran on a
  dead input.
```

Recorded as `aliases_matched_stored_documents` and `aliases_matched_of`, and
**the population is in the key** — `QueryRun` retains verdicts (which carry
matched *terms*, not bodies) and `stored` (which carries the hit), so the bodies
available are the ones the sieve KEPT, not every candidate. Calling it "of
candidates" would be the same error one level up.

> **This is the same family as this script's own recorded lesson**, four lines
> below where the new code sits: *"The first run reported 77% topic, which
> counted topic matches only among documents where subject ALSO matched. That is
> bounded by the subject rate and cannot measure topic at all."* A figure
> computed over the wrong population reads as a measurement of the right one.
> Rule 7, three instances now, all in this lane.
>
> The transferable form: **`len(x)` is never evidence that `x` did anything.**
> If a list is an input, the number to record is how many times it hit.

---

## 3 · `n_eff` and `max_author_share`, separately

### First: the gate has not moved, and the reason is a second column

`judge/store/cells.py` reads **`claim.author_id`**, not `document.author_id`.
They are separate columns; the claim's is copied from the document's when the
claim is written. So:

```
claim_author=None   doc=reddit:t3_1u1b22l   doc_author=au_cb8cc58deb4cccf6
claim_author=None   doc=reddit:t3_1u1b22l   doc_author=au_cb8cc58deb4cccf6
claim_author=None   doc=reddit:t3_1u1b22l   doc_author=au_cb8cc58deb4cccf6
claim_author=None   doc=reddit:t1_oqorjbe   doc_author=au_46c344476caaa0d3
```

Measured, unchanged: **n_eff 0.0121, max_author_share 1.000, voices 1** on both
cells. Backfilling `claim.author_id` is a `judge/` change and is not mine to
make; it is one guarded UPDATE and it is the last link in this chain.

### The counterfactual, with propagation

```
code.generation@context_size:unknown
   claims=2  voices=2  n_eff=0.0242  platforms=1  max_author_share=0.500
over_refusal@context_size:unknown
   claims=2  voices=1  n_eff=0.0121  platforms=1  max_author_share=1.000
```

**`max_author_share`: 1.000 -> 0.500.** The four claims sit on two documents by
two different people, which nothing could see before.

### Which condition binds, at every voice count

`check_gate` tests three things independently. Holding per-voice weight at the
only value the table has ever produced (0.012105):

```
   1 voices  n_eff=0.0121  share=1.000 cap=0.50  NOT_ENOUGH_WEIGHT, ONE_PLATFORM_ONLY, SINGLE_AUTHOR_DOMINATES
   2 voices  n_eff=0.0242  share=0.500 cap=0.50  NOT_ENOUGH_WEIGHT, ONE_PLATFORM_ONLY
   5 voices  n_eff=0.0605  share=0.200 cap=0.20  NOT_ENOUGH_WEIGHT, ONE_PLATFORM_ONLY
  50 voices  n_eff=0.6053  share=0.020 cap=0.20  NOT_ENOUGH_WEIGHT, ONE_PLATFORM_ONLY
 152 voices  n_eff=1.8400  share=0.007 cap=0.20  NOT_ENOUGH_WEIGHT, ONE_PLATFORM_ONLY
```

**Concentration stops binding at two voices** — `AUTHOR_CAP_BELOW_FIVE_VOICES`
is 0.5 and a share of exactly 0.5 passes. Your prediction holds, and it holds
earlier than expected: it took 2 authors, not 150.

**And what takes over is `NOT_ENOUGH_WEIGHT`, not `ONE_PLATFORM_ONLY`.** The two
are not comparable in difficulty:

| condition | what it needs | distance |
|---|---|---|
| `SINGLE_AUTHOR_DOMINATES` | 2 distinct authors in a cell | **cleared** |
| `ONE_PLATFORM_ONLY` | claims on 2 platforms | one storage step — the 36 blog claims are extracted, verified, and sitting in a JSON file |
| `NOT_ENOUGH_WEIGHT` | `n_eff >= 3.0` | **248 distinct voices at tier D.** With two platforms and 152 voices it still fails: 1.84 |

So `platform_count` was the wrong guess and so was mine. **The binding
constraint is the weight magnitude, and no amount of attribution reaches it.**

---

## 4 · Triage: the estimate meets a corpus, and it is 8.7%

Run read-only over the 195 comments — nothing written, `triage_verdict` is still
NULL on 254 of 254 rows.

```
documents   195
kept         17
dropped     178
SURVIVAL    8.7%   (population c511fceb6b7fb3df, 1385 surfaces)

dropped no-resolvable-entity   177
dropped too-short-no-artifact   74
GATES THAT COULD NOT RUN:  wrong-language (195), known-bot (195)
GATES WITH NOTHING TO RUN ON: pure-link-post (195), out-of-window (195)
```

**8.7% is below the 10–15% band, and it is an UPPER BOUND** — two gates could not
run and two had nothing to run on, and documents those would have dropped are
counted as kept. The true figure is lower.

**Denominator, and it is not the estimate's population.** 195 comments from ONE
thread, one subreddit, one model announcement, fetched by one `getPostComments`
call — and 195 of a reported 785, so 24.8% of even that thread. The estimate is
*"~10–15% of documents retrieved from the sources we sweep"*. This is not a
sample of those sources; it is one thread. What it establishes is that the figure
is now **measurable**, and that the first measurement came in under the band.

### The 177, and they are the inherited-subject problem

`no-resolvable-entity` drops **177 of 195 — 91%**. In an announcement thread the
root names the model and the comments say *"it's much faster"*. Those comments
name no entity, so triage discards them.

**That is the same phenomenon `subject_inherited` was built to describe, handled
in the opposite direction.** Extraction inherits the subject from the thread root
and records that it did. Triage drops the document before extraction ever sees
it. Two stages, one phenomenon, opposite treatments — and only one of them is
written down as a decision.

This is the finding that matters for `n_eff`, because it changes the ceiling:

```
distinct authors across all 195 comments      151
distinct authors among the 17 survivors        17

n_eff ceiling, after triage    17 x 0.012105 = 0.206   vs 3.0  FAILS by 15x
n_eff ceiling, no triage      151 x 0.012105 = 1.828   vs 3.0  FAILS
```

**Triage makes the binding constraint nine times worse.** Neither figure passes,
so this is not an argument for loosening triage — it is the measurement showing
that 152 stored authors are not 152 potential voices, and that the gap between
"authors in the corpus" and "voices in a cell" is a factor of nine on this
thread.

### The other denominators that just moved

```
triage denominator      64 -> 254 documents.  triage_verdict NULL on 254 of 254.
specificity_score       NULL on 254 of 254. The selector recomputes in Python.
names_version           populated on 7 of 254 rows (1 blog + the original 6).
                        The 190 new rows have it NULL, so the triage signals
                        were never computed for them either.
sweep re-run cost       ONE getPostComments call for this thread. Reddit's
                        working figure is 25 search req/min; comment fetches are
                        per-thread, so 196 documents cost one request. The corpus
                        did not get more expensive to rebuild — it got 4x larger
                        for the same call.
```

The re-run cost is the one that is better than expected, and it is worth saying
why: the payload was already stored. This was a **re-parse**, not a re-fetch,
which is the convention this lane holds and the reason it cost nothing.

---

## 5 · What this does NOT change: extraction still reads five

Stated plainly because the next reader will expect a yield change and there is
not one.

```
thread_context by selection_method
  whole_document                          contexts=31  member_documents=31
  issue_body_only                         contexts=27  member_documents=27
  specificity_x_log_engagement@observed   contexts=2   member_documents=12
```

**Unchanged.** Two Reddit contexts, 12 member documents between them — root plus
five children each. The `offset_map` is untouched, the flattened text is
untouched, so the extractor's input is byte-identical and **no claim yield
changes at all.**

189 of the 196 stored Reddit documents are **evidence for the gate, not input to
the extractor**. They exist so a claim drawn from a selected comment can be
counted against a corpus that knows how many people were in the room. Anyone
reading a document count as an extraction input will read this wrongly.

Whether extraction *should* read more children is a separate question with a
separate cost — prompt budget, and `max_thread_share`, which is still an
outstanding ask with E2.

---

## 6 · What is next, revised by the measurement

| | |
|---|---|
| **1. backfill `claim.author_id`** | one guarded UPDATE in `judge/`. Until it runs, none of this reaches the gate — `document.author_id` is populated and the gate does not read it. |
| **2. store the blog claims** | `ONE_PLATFORM_ONLY` cleared, on 36 claims already extracted and verified. |
| **3. finish `f_specificity`** | three of four inputs dead, one value ever produced. It is 0.58 of the 0.1009 multiplier, and **it must be fixed before anyone argues about `N_EFF_MINIMUM`** — tuning a threshold against a known-broken factor leaves the gate wrong once the factor is fixed. |
| **4. rule on the inherited subject in triage** | 177 of 195 documents turn on it, and the two stages currently disagree by accident rather than by decision. |

**Not next: loosening the gate.** Two conditions are one step away and the third
is a factor of 15 away for a reason we have already diagnosed and not fixed.

---

## What changed

| file | change |
|---|---|
| `scripts/write_reddit_thread.py` | **new** — writes root + all 195 comments with `author_id`, census before and after |
| `collect/adapters/reddit_write.py` | `write_documents` now attaches authors to rows that already existed, reported separately |
| `collect/triage/specificity.py` | `alias_match_count` moved here — one implementation, two callers |
| `scripts/export_thread_contexts.py` | imports it instead of defining its own |
| `scripts/harvest_github.py` | computes and prints the match count with its population; records `aliases_matched_stored_documents` and `aliases_matched_of` |
| `tests/test_author_attribution.py` | 21 tests (3 new: a conflicting row still gets its author) |

546 tests pass across the touched modules. `judge/` unmodified.
