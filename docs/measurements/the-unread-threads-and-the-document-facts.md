# The unread threads concentrate on models that already have cells, and the document facts move seven claims

**Two measurements taken 2026-08-31, in the order that made the second one
cheaper.** The first asks what $2.14 of extraction buys before spending it. The
second writes six columns that had been computed and never stored, and reports
what they change.

*Engineer 1 · 2026-08-31.*

---

## 0 · The board moved while this was being measured, and by how much

Every figure below carries an as-of, because the staging database took a
harvest, an extraction and a rollup at **04:39 UTC on the morning of the
measurement** — while these numbers were being collected.

```
                     stated in the brief   observed at run
  document                       2,980           3,061      +81
  claim                            197             199       +2
  cell                              94              96       +2
  thread_context                     —           1,725
```

Nothing here contradicts the brief; the brief was taken before that run. It is
recorded because a reader comparing the two would otherwise find four
discrepancies and no explanation, and because **a measurement against a shared
database is a measurement against a moving population** — which is a denominator
fact, not a footnote.

## 1 · Where the unread threads would land

`scripts/unread_thread_distribution.py`, read-only.

**Population: 1,510 thread contexts** with no `thread_extraction` row and a
flattened text readable from the local raw store. 20 more are unreadable here —
a property of this checkout, not of the corpus. Surfaces: 1,247 over 324 models,
population fingerprint `b5744297e9210497`.

### 1.1 · Capability cannot be known; the model half can

A claim is a (model, capability) pair and the extractor assigns the capability,
so only the model half is knowable in advance. It is `triage/entity.resolve` over
the flattened text — the same deterministic surface match the entity gate already
runs. **No model participates, and this is not a forecast.** It is a bound in one
direction:

    names no model that has a cell  ->  CANNOT add a voice to an existing cell
    names a model that has cells    ->  MAY add a voice; may open a new
                                        capability on that model instead

Reported as two bounds. A midpoint would be a synthesised number (rule 3).

### 1.2 · The result

```
  names a model that has cells        1,435    95.0%
  no surface matched                     64     4.2%
  names only models with no cells         9     0.6%
  surface matched, no known owner         2     0.1%

  UPPER BOUND, could add a voice to an existing cell   1,435 / 1,510 = 95.0%
  HARD FLOOR, cannot                                      75 / 1,510 =  5.0%
```

**The money buys voices, not a spread into new cells.** Of 2,678 model-mentions
across the unread threads, 86.9% fall on the 34 models that already have cells,
and the top ten models carry 66.1%. Only one celled model
(`google/gemini-3.5-flash-lite`, 1 cell) is named by no unread thread at all.

The models with the most unread threads are the models with the most cells:

```
  anthropic/claude-fable-5        339 unread   62 extracted   8 cells
  anthropic/claude-opus-4.8       298           27           5
  anthropic/claude-opus-4.6       265           28           7
  anthropic/claude-sonnet-4.6     165           22           8
  anthropic/claude-haiku-4.5      157           14           4
  qwen/qwen3.8-27b                148           68           9
```

The largest uncelled model is `openai/gpt-5` at 57 unread threads, and the 76
uncelled models carry 351 mentions between them — 13.1%.

### 1.3 · The correction that was needed to believe any of it

The first run put `anthropic/claude-opus-4` top with **577 unread threads and no
cells**, which would have been the headline. It is an artifact.

`normalize_with_boundaries` treats `.` as a word end, so the surface `opus 4`
matches inside `opus 4.6` with both boundary checks satisfied:

```
  'opus 4.8 is great'   ->  owners {claude-opus-4, claude-opus-4.8}
  'gpt-5.6-sol ...'     ->  owners {gpt-5, gpt-5.6-sol}
```

Neither surface nor owner is wrong. **One text span is attributed to two
models**, which makes a thread name more models than the writer did. Corrected
by keeping a surface only where it has an occurrence no LONGER matched surface
covers — tested per occurrence, so a document saying both `opus 4` and `opus 4.6`
in different places keeps both.

```
                          attribution A   attribution B
  claude-opus-4                     577              10
  openai/gpt-5                      319              57
  claude-sonnet-4                   203              19
  threads naming 1 model            448             797
  threads naming 4+ models          273             102
```

**This is NOT a defect in `resolve`, and it must not be fixed there.** `resolve`
answers "does this document name any model", which is the entity gate's question
and for which counting both is correct. The narrower question — *which* model
does this thread name — is this script's, and the subsetting lives with it.

The bound survives the correction (95.1% → 95.0%), but it would have been worth
nothing unchecked: 797 of 1,510 threads name exactly ONE model under B, against
448 under A. Had the typical thread named four models, "names a model with cells"
would be near-certain arithmetic rather than a finding.

### 1.4 · What it implies for the $2.14

**Spend it.** The failure mode the brief worried about — 1,505 threads spreading
into ~940 new cells at two voices each, moving nothing toward publishing — is not
what the corpus looks like. At most 5.0% of the unread threads can even open a
new cell, and 86.9% of model-mentions land on models already on the board.

Two caveats travel with that, and neither is small:

- **This is the model half only.** A thread naming `claude-fable-5` may still
  produce a claim about a capability that model has no cell for. The upper bound
  is an upper bound.
- **95% of threads reaching a celled model is not 95% of threads producing a
  claim.** 114 of 206 extractions so far wrote zero claims. The yield question is
  separate from the concentration question and this measures only the second.

## 2 · The document facts

`collect/triage/store.py`, `scripts/backfill_document_facts.py`, and the
`score-documents` stage in `collect/ops/chain.py`.

### 2.1 · It was not a broken writer. There was no writer

`collect/triage/specificity.py` has computed the five components since it was
built, is tested, and is contract-backed. **Nothing stored the result.** All four
`document` INSERTs name the same columns and not one of the six is among them:

```
  collect/adapters/blog/write.py:89
  collect/adapters/github.py:814, :971
  collect/adapters/reddit_write.py:72
  collect/assemble/article.py:document_row     builds no component either
```

The seven populated rows came from `scripts/export_thread_contexts.py`, which
hand-builds INSERT text for one thread and one article. That is why the count was
seven while the corpus passed three thousand, and why it would have stayed seven.

Same family as issue #27 and as `load-capabilities`: **not a broken check, a
check with no caller.**

### 2.2 · The answer is both, and the forward half is a chain stage

A backfill lifts the stored corpus; without a forward path the next harvest
re-creates the gap. The forward path is `score-documents`, wired into
`collect/ops/chain.py` — **not six more columns on four adapter INSERTs**:

- one registry read per run, not four that can diverge;
- a triage concern stays out of three platform adapters;
- backfill and forward path call the SAME function, so they cannot disagree
  about what a component means.

It needs only `preflight`, because it scores STORED rows — the night every sweep
fails is the night it has most to do.

**It is a recorded field, not a gate**, which is why it could be wired while the
rest of `triage` still waits on the bot list and the language detector.
`document.status` and `filter_reasons` stay with that stage (rule 8).

### 2.3 · The rate, and what was written

```
  documents in `document`      3,061
  carrying the columns now     1,955      was 7
  still NULL                   1,106
```

Over the 1,955 populated rows — **not over 3,061**:

```
                     populated   has_numbers   has_conditions   still NULL
  blog                     121        100%             15%              0
  github                    71         82%             59%              9
  reddit                 1,763         64%              8%          1,097
  ----------------------------------------------------------------------
  has_numbers AND has_conditions      191    9.8%
  exactly one of the two            1,127   57.6%
  neither                             637   32.6%
```

**1,106 documents were left NULL, not written False.** Their payloads are not in
this host's raw store — 1,097 reddit, 9 github, all fetched on another machine.
Writing False for text nobody read would say "this document contains no numbers"
about a document nobody opened, and `judge/`'s numbers rung reads False as a
veto: the invented value would hold claims at D silently. Rule 6 exactly, and the
same error one stage earlier than the one this column exists to prevent. Finish
them by running the backfill from a host holding those payloads; it is
idempotent and a re-run here now scores 0 and exits 0.

### 2.3b · The weight moved on 45 claims, which is the larger effect

`scripts/measure_document_facts_gap.py`, over the 199 claims at `e5.1`:

```
  f_specificity MOVES                45   22.6%
      0.44 -> 0.58    34
      0.30 -> 0.44    11
  columns present and genuinely False 130   65.3%
  document columns still NULL          24   12.1%   (reddit; 15 are sonnet-5)
```

Those 45 were priced as though both booleans were False. They are not. **This is
a weight, visible and rankable, which is where rule 8 wants an unmeasured signal
— unlike the tier, it moves every claim whose document really carries numbers or
conditions, not only the seven the extractor also flagged.**

It also names a residue the run did not explain: **19 rows do not reproduce their
stored `f_specificity`** from `(version_named, False, False, has_repro_steps)`.
Something other than the original None-slip moved them. Reported rather than
smoothed over.

`measure_document_facts_gap.py` had been crashing on Windows at exactly that
warning — `cp1252` cannot encode `U+26A0` — **after** printing every other
figure, so the run looked complete and the one warning the block exists to raise
was the only output lost. Now ASCII.

### 2.4 · The numbers rung is reachable, and it moves seven claims

**Not 197.** The brief's expectation was that writing these columns makes every
subsequent extraction eligible for C at 0.35 against D's 0.12. The mechanism is
narrower than that in two ways, both in `contract/harvest.yaml`:

**`has_conditions` does not key the tier at all.** C's rung is
`one_of_the_two` over `(has_repro_steps, has_numbers)` — the contract says so
explicitly, and says why: `has_conditions` was False on all 7 populated rows, so
keying C on it would have made C unreachable the same way `speaking` made B
unreachable. Writing `has_conditions` changes `f_specificity`, a weight. It
changes no tier.

**`document.has_numbers` is a veto, not a promoter.** The rung needs
`claim.has_numbers` AND `document.has_numbers`. Code can block a promotion; code
never grants one.

So the ceiling is `claim.has_numbers`, which the extractor sets. Measured
against the columns as now written:

```
  claims at e5.1                                    199   D 159 · E 29 · F 11
    speaking = own-experience                       156   the only value with rungs
      claim.has_numbers  doc.has_numbers   count
        false              true              100
        false              false              25
        false              NULL               24
        true               true                7   <- the whole promotable set
  claims promoted D -> C by this backfill             7   3.5% of 199
```

Thirteen of the 20 claims carrying `claim.has_numbers` are
`relayed-from-elsewhere` or `vendor-about-own-product`, which have no rungs — a
relay's numbers are still someone else's.

**The 1,106 unscored documents cost zero promotions.** Of the 24 own-experience
claims whose document is still NULL, all 24 have `claim.has_numbers` false, so
not one of them would promote even with the column written. The withholding is
real and named; today it is not load-bearing. That could change with the next
extraction, which is the reason to finish the backfill rather than the reason to
panic about it.

**Seven is small and it is not nothing: it is the first non-D claim the board has
ever had.** Before this, 0 of 197 reached A, B or C, and the reason was that no
value the extractor could emit mapped above D. The rung now exists and is
occupied. The board reads `D 159 · E 29 · F 11` until a reweight runs.

### 2.5 · B is unreachable, and section 3 is why

## 3 · `has_repro_steps` is False on 199 of 199 because nobody asked

The field appears **nowhere in the extraction prompt**, and the tool schema hands
the model a bare boolean:

```
  judge/extract/prompt.py     grep -ci repro  ->  0

  ExtractedClaim.model_json_schema()["properties"]["has_repro_steps"]
      {"default": false, "title": "Has Repro Steps", "type": "boolean"}
```

No description, not in `required`, defaults to False. Every other field the tier
or the weight reads carries one — `quote` gets ninety words, `is_sarcastic` gets
two sentences.

**So 0 of 199 measures how often an unasked optional boolean takes its default.**
It is not evidence about the corpus and must not be quoted as any (rule 7).

The sharper form of the finding: `has_numbers` has the **identical** schema
defect — no description, default False, not required — and comes back True on 20
of 199. The model does fill an undescribed boolean when the name alone carries
the question. `has_numbers` is self-evident from four words of title case;
`has_repro_steps` is a judgement, and the model declines it silently by taking
the default.

Since the 2026-08-30 re-key this is **half the ladder**: B needs both booleans,
so B is unreachable by construction while one of them can never be True, and C is
reachable only through the numbers rung measured in §2.4.

Proposed to Engineer 2 rather than taken, because the fix is two edits in
`judge/`: `docs/proposals/for-engineer-2-has-repro-steps-is-a-question-nobody-asked.md`.

## 4 · What broke on the way, recorded because both were silent

**A savepoint is not a commit.** The first writer used `with conn.transaction():`.
`collect.db.connect` leaves autocommit off and the SELECT has already opened a
transaction, so a nested `transaction()` is a SAVEPOINT whose release commits
nothing. The sweep ran to completion, incremented `written`, and stored zero
rows — **a write path that reports success and writes nothing.** Every other
writer in `collect/` calls `conn.commit()`; this one now does too, and
`tests/test_triage_store.py` counts commits rather than counting `run.written`,
because only the first of those separates a working writer from that one.

**And it left row locks behind.** The failed run's backend sat `idle in
transaction` on the shared staging database holding UPDATE locks on ~900 rows,
and two later backends blocked on it for minutes with no error — the sweep simply
appeared slow. Found in `pg_stat_activity`, not by anything failing. If a write
against staging seems to hang, that view is the first place to look.

**A long CPU pass between opening a connection and using it is a dropped
connection.** Scoring all 1,948 documents and then writing them left the link
idle for five minutes and the server closed it — at the END of the expensive
part. Scoring and writing are now interleaved at 100 rows, and the script resumes
across a dropped link, which is safe ONLY because the SELECT and the UPDATE both
guard on `has_numbers IS NULL`.

## 5 · Contract entries changed, and they are marked unreviewed

`contract/column_states.yaml` declared all six columns `reserved` or `unwired`,
and three carried a `known_gap` reading *"collect/triage/specificity.py computes
it and nothing writes the column"* — true when written, false as of today. A
stale `known_gap` is worse than a failing test: it is a false statement in the
contract, and `known_gap` makes the discovered-state check SKIP the column.

Updated to the discovered state with `reviewed: false`, which the file's own
header defines as *"a snapshot, not a decision — nobody has ruled on it."*
**The state is a fact; whether these belong there is E2's call.** `contract/` gets
two eyes.

`specificity_score` is declared `write_only` with no `known_gap`, deliberately:
it should start failing the day something reads it.

### Reproducing

```
python scripts/unread_thread_distribution.py
python scripts/backfill_document_facts.py            # dry run, writes nothing
python scripts/backfill_document_facts.py --write
python scripts/measure_document_facts_gap.py         # what the columns moved
```
