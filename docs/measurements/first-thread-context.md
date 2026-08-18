# The first `thread_context` row

**Assembly is wired and the lane interface has one row in it. The write path
worked on its first call against a real database — and comparing the row to
Engineer 2's fixture found a divergence byte equality could not: her
`document_id`s strip the `t1_`/`t3_` prefixes that `collect/` stores.**

*Engineer 1 · staging · 2026-08-18*

---

## 1 · The row

```
id                       thread_context_eacc17c8af367044
thread_root_id           t3_1u1b22l
child_count              5
selection_method         specificity_x_log_engagement@observed
observed_children        195
hidden_children_min      623
hidden_branches_unsized  0
coverage_ratio           0.2383863          <- GENERATED, never written
pipeline_version         collect-0.1.0
member_document_ids      6
offset_map               6 segments
assembled_at             2026-08-18 09:58:11+00
```

**`coverage_ratio` reads 0.238 and that is an UPPER BOUND.** 195 observed
against a known minimum of 818, where the denominator uses a floor on hidden
comments — so this thread was seen at *at most* 24%, and the true figure is
lower by however much truncation did not admit to. The column comment says so;
this row is the first thing it says it about.

`hidden_branches_unsized` is 0 here, which is the fourteen-threads case rather
than the fifteenth. Recording it is what makes that distinguishable.

## 2 · The four things asked for

**Coverage columns written from `ThreadCoverage`.** It has been computing them
since the comment fetch landed with nowhere to put them; `observed_children`,
`hidden_children_min` and `hidden_branches_unsized` come straight off it.

**`coverage_ratio` is omitted from the insert, not passed as NULL.** A generated
column rejects an explicit value — NULL included — so omission is the only way
to write one. `as_row()` does not contain the key and a test asserts that,
because "we pass None" and "we omit it" look identical until Postgres refuses.

**`selection_method` carries the qualifier.** `specificity_x_log_engagement@observed`,
never the schema's bare default. The bare value asserts a global ranking and the
data cannot support one: siblings ordered rather than the tree, 30% of adjacent
pairs score inversions, a depth-2 comment at 610 under top-level comments at 6.
This row ranked 195 comments out of a known minimum 818, so `@observed` is the
literal truth about what was ranked.

**`extraction_version` does not exist**, and `pipeline_version` carries it in the
meantime. That is weaker in one specific way: `pipeline_version` changes for any
change to `collect/`, so it **over-identifies** — two byte-identical flattenings
can carry different versions. It never under-identifies, which is the direction
that matters, **provided `PIPELINE_VERSION` is bumped when the flattener
changes.** That proviso is the entire guarantee and it is a convention, not a
check. Still worth ruling on #5.

## 3 · The write path ran, and the round trip is on rows read back

Condition B by construction: a new writer, first call, real database. It
inserted without incident.

The round trip was then run on the row **read out of Postgres**, not on the
object that wrote it — `flattened_text_ref` resolved from the store,
`offset_map` from `jsonb`, `raw_text_of` rebuilt from the payload as `judge/`
would build it from `document`:

```
read back: 3550 chars, 6 segments, 6 documents
round trip over rows read from the database: 6 resolved, 0 failed
```

Every segment resolved through `judge/extract/verify.py:_resolve_raw_span` back
to raw text matching the flattened span exactly.

That distinction mattered: an in-memory round trip shares the Python objects
that produced it and can only fail on arithmetic. Reading back exercises the
`jsonb` round trip, the store ref, and the document-id lookup — and the last of
those is where §4 was found.

## 4 · The divergence byte equality could not catch

`collect/` stores fullnames. `RedditPost.external_id` is `t3_…` and
`RedditComment.external_id` is `t1_…`, both documented as *"the fullname, never
the bare id"*. So assembly produces:

```
reddit:t3_1u1b22l   reddit:t1_oqoc844   reddit:t1_oqocu7n   …
```

Her fixture carries:

```
reddit:1u1b22l      reddit:oqr6lad      reddit:oqosfnq      …
```

**Byte equality passed anyway**, and the reason is worth keeping: `document_id`
is an *input* to the flattener, not an output of it. The test hands the
flattener her ids and compares the text and the segment offsets — all of which
agree — so an id-convention difference is invisible to it by construction.

It would not have been invisible for long. `raw_text_of` is keyed by
`document_id`, so a map saying `reddit:oqosfnq` against a `document` table
holding `t1_oqosfnq` misses every lookup and returns `RAW_TEXT_MISSING` for
every quote in the thread — a total failure that looks like a storage problem
rather than a naming one.

**This is a `collect/` fact and hers regenerates**, which is the standing rule
and the first time it has had anything to apply to. Not an edit to her file: a
request, with the reason.

## 5 · What this row is not

**Not a selection anyone should trust yet.** The five children were ranked by
`specificity_score × log(1 + engagement)` over the 195 observed, and
`specificity_score`'s weights are provisional and uncalibrated. `@observed` is
the honest label for what happened; it is not a claim that these are the five
best comments in the thread.

**Not the same five Engineer 2 selected.** Her fixture picked six documents to
carry four hard cases — deep nesting, `[deleted]`, `[removed]`, an emoji in a
child. Mine picked by rank and got **zero substitutions**, so this row exercises
the flattener's identity path and nothing else. The substitution path is covered
by tests and by her fixture, not by this row.

**Not a licence to read `thread_context`.** One row, from one thread, whose
document ids disagree with her fixture's. §4 should land before extraction runs
against it.

## 6 · What would revise it

- **The id convention**, §4. Cheap, and it blocks everything downstream if left.
- **`extraction_version`**, #5. Until then `pipeline_version` over-identifies
  and the bump convention is the guarantee.
- **Calibrated specificity weights.** `@observed` says the ranking was local;
  it does not say the ranking was good.
- **A thread whose selection includes a substitution**, so the write path
  exercises what the flattener tests already do.
