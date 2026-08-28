# The column audit: 306 columns, four states, and a fifth the four cannot see

**The recollection was two instances. The enumeration is 75 written-and-unread,
18 unwritten-and-read, and 45 neither — and `harvest_run` is 10 of the 75, which
is most of the table.**

*Engineer 1 · 2026-08-28 · `scripts/audit_columns.py`, full result in
`docs/measurements/column-audit.json`. Column list from the live schema so
migrations are included; evidence from static analysis of non-test source*

---

## 1 · The four states

```
30 base tables, 306 columns

  written + read        168    54.9%
  written, UNREAD        75    24.5%
  neither                45    14.7%
  UNWRITTEN, read        18     5.9%
```

**`cell_current` is excluded and that is not a judgement call.** It is a VIEW with
18 columns, and a view is never written — leaving it in put 11 columns in
"unwritten, read" and 7 in "neither" as artifacts of the method rather than
findings. 324 columns in the raw output, 306 after the view comes out.

`SELECT *` reaches only two tables (`model_version`, `source`), so it is not
quietly satisfying the read side anywhere that matters.

## 2 · `harvest_run` is the finding, and it is worse than the two instances suggested

```
harvest_run — 10 of 15 columns written and never read

  source_id  query_key  items_fetched  items_kept  http_errors
  exhausted  truncated_by  pages_fetched  pages_stored  sieve_pass_rate
```

**The retrieval ledger is write-only in its entirety.** Not one column of it is
read by anything in `collect/`, `judge/`, `scripts/` or `web/src`. Every figure in
`model-name-versus-capability-retrieval.md` came out of this table by ad-hoc
query, including the truncation split — and `truncated_by` had already recorded
`result-ceiling` on 126 runs while that document spent a paragraph inferring the
same fact from `items_fetched`.

`claim` is second at 15 columns, all extraction outputs nothing consumes:
`speaking`, `evidence_tier`, `extractor_confidence`, `is_sarcastic`,
`has_repro_steps`, `specificity`, `resolution_confidence`, `relevance` and more.

## 3 · The third state is diagnostic, and it names the unwired stages

18 columns are read by code and written by nothing. They are not a scattering —
they cluster on exactly the stages `chain.py` carries as `run=None`:

```
document      triage_verdict, filter_reasons        <- Stage("triage", run=None)
coverage_gap  id, subject, detail, observed_at      <- Stage("write-coverage-gaps", run=None)
dedup_cluster id, reach                             <- Stage("assemble-dedupe", run=None)
audit         id, verdict
golden_label  document_id, label
thread_context coverage_ratio                       <- GENERATED, correctly unwritten
watermark     cursor
claim         created_at                            <- DEFAULT now(), correctly unwritten
```

**A reader with no writer is a stronger signal than an unread column**, because
somebody has already decided the value matters. `document.triage_verdict` has a
consumer and no producer, which is `Stage("triage", run=None)` visible from the
schema side rather than from the chain.

Two are correct and should be declared rather than fixed:
`thread_context.coverage_ratio` is a GENERATED column and `claim.created_at`
defaults to `now()`. A guard that flagged those would be wrong.

## 4 · The fifth state, which the four cannot see

**The four states are facts about CODE. They say nothing about whether a column
is populated.** Crossing the audit with the data:

```
of the 75 written-and-unread columns, on non-empty base tables:
  written in code AND 0 rows populated                    9

  author            account_created_at, identity_cluster_id, karma
  claim             family
  harvest_run       pages_fetched, pages_stored
  model_alias       family
  model_version     deprecation_date
  task_profile      requests_per_month
```

**This is exactly why `pages_fetched` is a different defect from `truncated_by`,
and the audit alone cannot tell them apart.** Both classify as "written,
unread". In the data:

```
harvest_run.truncated_by     421 of 1,019 populated   41.3%   -> written, unread
harvest_run.pages_fetched      0 of 1,019 populated    0.0%   -> written by CODE
                                                                that never ran
```

`collect/adapters/reddit.py` populates `pages_fetched`; Reddit has never written
a `harvest_run` row. `collect/adapters/github.py` has written 1,019 and
populates neither. The static audit sees a writer and reports the column
written. **A guard built on the four states alone would pass this column
forever.**

So the honest taxonomy is 4 × 2: state in code, crossed with populated in data.
The second half needs a database and row counts, and it is a *report* rather
than a test — see §6.

## 5 · Write-only is often correct, which is why "every column is read" is the wrong assertion

Of the 75, a substantial share are deliberately write-only and a guard demanding
readers would be wrong about all of them:

```
document.content_hash          content addressing. Written to be matched on,
                               not selected.
claim.pipeline_version         diffability. Every derived row carries it so a
                               scoring change is re-runnable (CLAUDE.md
                               conventions). Read by a human diffing runs.
source.tos_notes               a human-readable record. Its reader is a person
                               opening the row, and rightly so.
source.terms_ruling            read by assert_terms_reviewed through the YAML,
                               not through the column - a real reader the static
                               audit cannot see.
thread_extraction.extracted_at ledger. "We read it and found nothing" is the
                               whole point of the row.
```

`source.terms_ruling` is the instructive one: it *has* a reader, and the reader
goes via `contract/sources.yaml` rather than a SELECT, so the audit calls it
unread. **The method's false-positive rate is not zero and the direction is
knowable** — it under-counts reads that route through YAML, generated columns,
and anything built dynamically.

## 6 · What it costs to keep running, and the shape it should assert

**The script:** 171 lines, runs in about four seconds, needs a live database only
for the column list. Deriving columns from `contract/tables.sql` plus
`contract/migrations/*.sql` instead would make the static half need no database
at all, which is what a CI test wants.

**The assertion should not be "every column is read".** Some are write-only on
purpose and §5 lists five. The property worth guarding is the one that actually
failed here:

> **A column's state is DECLARED somewhere rather than DISCOVERED.**

Proposed shape — a manifest beside the schema, and a test that compares
discovered state to declared:

```yaml
# contract/column_states.yaml
harvest_run:
  truncated_by:   {state: read,       why: "quote it beside any retrieval rate"}
  pages_fetched:  {state: write_only, why: "re-sieve provenance; github must populate"}
  content_hash:   {state: write_only, why: "content addressing, matched not selected"}
document:
  triage_verdict: {state: read,       why: "consumer exists; writer is Stage(triage)"}
thread_context:
  coverage_ratio: {state: generated}
```

```
test_every_column_declares_its_state
  1. discover the state of all 306 columns
  2. FAIL on any column with no entry            <- the property that makes it a
                                                    guard rather than a snapshot
  3. FAIL where discovered != declared
```

**Step 2 is the whole value.** It is the same arrangement as `cli.py`'s AST
guard, where read-only commands must be listed explicitly so an unclassified one
fails rather than running unguarded — and that guard exists because *"a
behavioural test over existing commands cannot see a path that never had a
check."* A snapshot test over today's 306 columns would pass forever and say
nothing about the 307th.

**Cost to adopt:** one pass declaring 306 entries, which is a couple of hours of
reading and is the actual price. After that, a new column costs one line, and
the line is where the intent gets written down instead of discovered nine months
later.

**The populated-in-data half stays a report, not a test.** It depends on row
counts, so it would fail on an empty CI database and pass on a full one — a test
that green-lights the `pages_fetched` defect on the machine where it matters
least. It belongs in the nightly alert set beside triage survival, where "written
in code, absent in data" is a finding somebody can act on.

## 7 · What I am not claiming

The audit does not establish that 75 columns are defects. It establishes that
**75 columns have no reader in the repository and nobody has written down which
of those is intentional** — and that the same is true of 45 columns with neither
a reader nor a writer. The habit claim that prompted this now has a denominator:
306 columns audited, 138 in a state nobody declared.

Whether that is a habit or a young schema is a judgement. What is no longer a
judgement is the count.
