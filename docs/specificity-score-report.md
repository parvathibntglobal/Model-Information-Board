# `specificity_score` — what it needs, and what it does not unblock

**A design report and three requests for agreement.**

> **STATUS — resolved.** All three §7 items were agreed by Engineer 2, who added
> a fourth constraint: the two specificity measurements must never be
> **compared** either, not merely never merged, because a reader seeing 0.7 in
> both will want them to mean the same thing. Implemented in
> `collect/triage/specificity.py`; the weights and floor are in
> `contract/harvest.yaml`; the components are stored on `document`. E3 remains
> untouched, for the reason in §3.

> The headline is a correction to something I said myself. I called
> `specificity_score` the blocker on everything downstream of harvest. **It is
> not.** Building it unblocks E4's floor and leaves E3 exactly where it is.

*Engineer 1 · assessed at commit `299d021`*

> Written for someone who was not in the room. Nothing here assumes you
> followed the session that produced it.

---

## Summary

| | Status |
|---|---|
| `document.specificity_score` | column exists, **no writer, no reader** |
| Named consumers | E3 child ranking · E4 specificity floor — **both in `collect/`** |
| Read by `judge/` | **no.** `f_specificity` is a different measurement (§2) |
| Deterministic | **yes**, all five components are countable (§4) |
| Inputs that exist today | version-named, code containers — near free |
| Inputs to build | numbers-with-units, error strings |
| Blocks E3 | **no.** E3 is blocked on comment fetching and issue #5 (§3) |
| Needs Engineer 2's agreement | three items, §7 |

Nothing here needed deciding except §7, and §7 was the reason this was a
document rather than a commit. It has since been agreed — see the status note
above, and §7 for what each item became.

---

## 1 · Status: it does not exist, and nothing reads it either

`document.specificity_score real` (`contract/tables.sql:206`) is nullable, has
no writer and has no reader. `collect/adapters/github.py:471` writes `document`
rows today and leaves the column out of the INSERT entirely, so every row in
the store carries NULL. `collect/assemble/` and `collect/triage/` are both
empty directories.

It is named in four places and implemented in none:

| Where | What it says |
|---|---|
| `contract/tables.sql:206` | `numbers · error strings · code · version named. Reused by E3 for child ranking.` |
| `contract/tables.sql:278` | `thread_context.selection_method` defaults to `'specificity_x_log_engagement'` |
| `collect/CLAUDE.md:35` | `score = specificity_score × log(1 + engagement)` |
| `collect/adapters/reddit.py:406` | the `assemble_thread` refusal, reason 1 of 2 |

---

## 2 · `judge/` does not read it, and that settles the lane question

This is worth being exact about, because "both lanes read it" was the reason to
think it might be shared.

`judge/` ranks with `claim_weight.f_specificity`, computed by
`judge/vet/weight.py:130`. That is a **different measurement of a different
thing at a different granularity**:

| | `document.specificity_score` | `claim_weight.f_specificity` |
|---|---|---|
| granularity | one document | one claim |
| inputs | numbers · error strings · code · version named | `version_named` · `has_numbers` · `has_conditions` · `has_repro_steps` |
| where inputs come from | the text, counted | 2 of 4 from the extractor; 2 have no source at all |
| range | to be decided (§5) | 0.3 – 1.0 |
| consumers | E3 ranking, E4 floor | `w_final` |

A grep for `specificity_score` across `judge/` returns nothing. So:

- it is a column on `document`, which `collect/` fills and `judge/` only reads
- both named consumers are `collect/`
- FR-14, FR-15 and FR-16 are marked **E1** in `BUILD-PLAN.md:340`, and the plan
  already names `triage/gates.py` as the home
- every input it needs already lives in `collect/`

**It belongs in `collect/`.** What is shared is the contract, not the number —
see §7.

---

## 3 · It is not the blocker on assembly. Reason 2 is

I filed `specificity_score` as *the* thing stopping thread assembly. Checking
the rest of the chain says otherwise.

The score's only named consumer is E3 child ranking. **No adapter fetches child
documents on any platform:**

| Platform | Children today |
|---|---|
| GitHub | none. `write_documents` writes one document per issue; `comment_count` is stored as engagement and nothing else |
| Blogs | none, deliberately — `include_comments=False`, `collect/adapters/blog/options.py:45` |
| Reddit | none stored. The comment endpoints were probed; assembly is refused |

And `collect/adapters/reddit.py:395` refuses for **two** reasons, of which the
scorer is only the first. Reason 2 is that the selection cannot be bounded:

- one `getPostComments` call returned **200 of 4,833** comments (4%)
- Reddit orders **siblings**, not the tree — 30% of adjacent pairs are score
  inversions, and a depth-2 comment scoring 610 sits under top-level comments
  scoring 6, so the last-seen score bounds nothing unseen
- coverage is not fully knowable: of 252 `more` markers, 126 report a hidden
  count and 126 report none, so any coverage figure is a **lower bound**
- it needs `thread_context.observed_children`, `hidden_children_min` and
  `coverage_ratio`, proposed on issue #5 and not in the contract

**So: implement the scorer and `assemble_thread` still raises, on reason 2.**
The real prerequisite list for E3 is comment fetching on at least one platform,
plus three columns from issue #5. Both are larger than the scorer.

What the scorer *does* unblock is **E4's floor**, which needs only root
documents — all of which exist in the store today. That is the consumer to
wire, and it is why E3 stays untouched in the plan below.

### The ordering also has to change

`docs/logic-and-workflow.md:316` says the score *"is already computed in E4 …
so reuse it"*, and the column comment says *"Reused by E3 for child ranking."*
But the pipeline is **E3 assemble → E4 triage** (`BUILD-PLAN.md:46`). E3 cannot
reuse what E4 has not computed yet.

The resolution is forced: child selection happens inside E3, so the score is
computed **per document at ingest**, before E3 ranks. E4 is a second reader,
not the producer. The doc sentence should be corrected when this lands.

---

## 4 · Deterministic: yes. Five booleans, counted, no model

Rule 2 is satisfiable without argument here — every component is counting.
What differs is how much has to be built.

| Component | Exists today | Notes |
|---|---|---|
| **version named** | **yes** | `collect/registry/aliases.py:102` — `classify_specificity` returns `snapshot` / `version` / `family`. Count `version` and `snapshot`; **not `family`** — a bare `sonnet` names a line, not a tier, and counting it would credit a document that never said which model |
| **code** | **yes, nearly free** | `collect/adapters/queries/sieve.py:246` — `_EXCLUSIONS` already detects `fenced-code`, `indented-code`, `inline-code`, `html-pre-code`. Today they are substituted away; `author_prose_aligned` already keeps offsets. Exposing them as spans rather than a substitution is a small in-lane accessor |
| **numbers** | **no** | The definition is the work, not the regex. Bare digits are noise — issue numbers, dates, and version tokens already counted above. The signal is **numbers-with-units**: `tests/test_blog_parse.py:153` pins `"1.8s"` as the case and `collect/CLAUDE.md:77` says the same |
| **error strings** | **no** | The real work, and the part most worth reviewing. Tractable shapes: `Traceback (most recent call last)`, class names ending `Error` / `Exception`, `KeyError:`-style prefixes, HTTP status codes |
| **conditions** | **no** | Named in the E4 floor (`docs/logic-and-workflow.md:345`). `contract/conditions.yaml` gives the bands but no text detectors, and the extractor's `conditions` object is claim-level and arrives too late to gate on |

**One shortcut I want to name so nobody takes it later.** Issue #9 identified
20 error-string-shaped terms already sitting in `contract/queries.yaml`
(`invalid json`, `failed to parse`, `not in the schema`, …). Reusing them as
the error-string detector would couple a **document-level property** to the
**capability vocabulary** — editing one capability's terms would silently
re-rank thread children in every other capability. The detector should be
vocabulary-independent.

---

## 5 · The composite, and the two rules that constrain it

### The primitive is the booleans; the score is a projection

The E4 floor is *"no numbers, no error strings, no code, no conditions, no
version named → opinion, not evidence"* — a five-way boolean AND, not a
threshold on a continuous score. E3 wants a scalar; **E4 wants the
components.** Storing only the composite makes E4's gate unreconstructible
after the fact and loses the audit trail. Hence: store both.

### Rule 3 — it may rank, it may never render

`specificity_score` is a synthesised number. It is an internal ranking key and
must not reach a page, a tooltip or an evidence drill-down. The drill-down
shows the **components**, which are counted.

### Rule 6 — NULL is not zero, and this bites on day one

Every `document` row already written carries `specificity_score = NULL`. If E3
later ranks by `specificity_score × log(1 + engagement)` and coalesces NULL to
0, every pre-scorer document sorts last **while looking scored**. NULL means
*not yet measured* and stays distinguishable from *measured as zero* through
every layer that reads it — including the E4 floor, which must not read an
unscored document as "no signals present" and drop it.

### One ambiguity the spec does not settle

*"Retained at ~0.15 weight, not sent to the extractor"*
(`docs/logic-and-workflow.md:345`). A document not sent to the extractor
produces no claim, and weights are claim-level — there is nothing for the 0.15
to attach to. Someone needs to say what that sentence means before the floor
is wired. My reading is that it describes a retained-but-unextracted status
rather than a weight, but that is a guess and it is in the shared doc.

---

## 6 · Two findings on the `judge/` side, found while checking §2

Both are Engineer 2's lane. Raising rather than touching.

### 6.1 · `version_named` and `has_conditions` have no source

`weight.compute()` requires four booleans. Two of them do not exist anywhere
that could supply them:

- not in `ExtractedClaim` — `judge/extract/schema.py:93` carries only
  `has_repro_steps` and `has_numbers`
- not in the `claim` table — `contract/tables.sql:331` carries the same two

Both are code-derivable and neither needs a model: `version_named` from
`claim.specificity IN ('snapshot','version')`, `has_conditions` from whether
the `conditions` jsonb has any dimension set to something other than
`unknown`. Today they are caller-supplied with nothing to supply them, so
`f_specificity` cannot be computed for a real claim.

### 6.2 · Two LLM booleans reach weighting unchecked

`has_numbers` and `has_repro_steps` are emitted by the extractor and flow
into `f_specificity` → `w_final` with no code check. Rule 2 says a model may
not participate in weighting; the governing form is **an LLM may propose, it
may never decide**, and here nothing decides after the proposal.

The document-level `has_numbers` this report proposes is the obvious check: it
is the same question asked of the same text by code. Two shapes are available
and the choice is Engineer 2's — code overrides the extractor, or a
disagreement is recorded and surfaced the way `signal_in_excluded` is. I have
no measurement that argues for either.

`has_repro_steps` has no countable equivalent and is the one weighted double.
That is worth knowing even if the answer is to leave it.

---

## 7 · What needed your agreement — all three agreed

Three items. Nothing in §8 required permission to *build*; these required
agreement to *land*.

The flagging rule covers a change made inside one lane that touches the shared
file. **These were not that.** A contract key and five new columns on `document`
alter the interface both lanes read, so they wanted agreement rather than
notice — which is why §8 was not written at the time. The module depends on 7.1
and 7.2, so building first would have presented a decision on exactly the two
things this document existed to ask about.

**All three were agreed.** What each became is recorded under it.

### 7.1 · New contract keys

Rule 5 puts the component weights and the floor definition in versioned YAML,
not code. `sieve.locality_window` in `contract/harvest.yaml` is the precedent
and the shape to copy — number, plus the reasoning beside it, plus what would
revise it.

**Proposed home: a `specificity:` block in `contract/harvest.yaml`.**
`locality_window` already lives there and is the same shape at the same stage
— a threshold governing how the sieve reads a document. A new
`contract/triage.yaml` for one key invites the question of what else belongs
in it, and the answer today is nothing. If triage grows enough config to earn
a file, splitting is easy; creating it now means two files with a boundary
neither of us could articulate.

> **Agreed.** `specificity.weights` and `specificity.floor_clears_on` are in
> `contract/harvest.yaml`. The floor is expressed as the components that
> *clear* it rather than as a cutoff on the composite: the floor is a five-way
> OR, and a threshold on the weighted sum is a different rule that merely
> agrees with it today. An absent weight raises rather than defaulting to
> zero — unlike `locality_window`, whose absence legitimately disables it.

### 7.2 · Storing the components, not just the composite

Five boolean columns on `document` alongside `specificity_score`, per §5.
Contract change. The alternative — composite only — means E4's gate cannot be
reconstructed from the row and the evidence drill-down has nothing countable
to show.

> **Agreed, and it gained a second consumer.** Engineer 2 is wiring
> `document.has_numbers` as a **falsifier** against the extractor's
> self-reported `claim.has_numbers`, so it has to be readable from `judge/` as a
> stored column rather than only as an input to the composite. Her precision is
> carried in the module docstring and pinned by a test: **it falsifies, it
> cannot confirm.** False here makes a claim asserting `true` a fabrication;
> true here says nothing about whether that particular quote contains a
> number.

### 7.3 · The naming collision

Two things called specificity, at different granularities, with different
ranges and different trustworthiness of inputs (§2). Nobody is confused today.
Someone will unify them in month three, and unifying them would put an
LLM-emitted boolean into thread-child ranking.

Proposal: a comment in both `judge/vet/weight.py` and
`collect/triage/specificity.py` stating they are different measurements and
must not be merged, and a note in `contract/tables.sql` beside both columns.
Cheap, and it is the kind of thing that only works if both lanes wrote it.

> **Agreed, and strengthened: never merged AND never compared.** A reader
> seeing 0.7 in both will want them to mean the same thing. The note is in
> `collect/triage/specificity.py` and beside the columns in
> `contract/tables.sql`, and `tests/test_specificity.py` asserts the two ranges
> genuinely differ so that anyone unifying them breaks a test. **The matching
> sentence in `judge/vet/weight.py` is not written** — that file is Engineer
> 2's lane and the sentence is hers to add. Proposed text is in the PR.

---

## 8 · The plan, as built

| Step | Scope |
|---|---|
| 1 | `collect/triage/specificity.py` — five detectors returning five booleans, plus the composite |
| 2 | Component weights and the floor to `contract/`, **flagged**, provisional beside the numbers |
| 3 | Wire **E4's floor only** — root documents, which exist today |
| 4 | Backfill from the raw store, not by re-fetching — payloads are immutable and content-hash addressed |
| 5 | **E3 untouched.** It is blocked on comment fetching and issue #5, not on this |

Steps 1 to 3 and 5 are done. **Step 4, the backfill, is not run** — it writes to
every `document` row in the store, and it is also the calibration measurement,
so it is worth running once deliberately rather than as a side effect of a
merge. Until it runs, existing rows stay NULL and the floor reads them as
UNKNOWN, which is the designed behaviour rather than a gap.

Rough shape: version-named and code are near-free reuse. Numbers is half a day,
most of it deciding what counts. Error strings is the real work.

### What is provisional, and what would revise it

The **weighting** is judgement, not measurement — there is no corpus with
labelled specificity to fit it against, exactly as there was no corpus of real
positives when the locality window was picked. The first version says so
beside the numbers.

What would revise it: the ~10–15% triage survival figure, once the floor has
run against the 174 GitHub candidates and 111 blog articles already in the
store. That number is an estimate to calibrate, not a specification, and the
floor is the gate that most moves it. If the floor drops 90% of documents, the
weighting is wrong or the detectors are — and that measurement is cheap,
because it is a re-scoring of documents already on disk rather than a fetch.

---

## Appendix · Provenance of the Reddit proximity figures

**Unrelated to `specificity_score`.** Recorded here because the measurement
writeup carrying these figures lives outside the repo, and this is the nearest
durable place for a fact that will otherwise be rediscovered the hard way.

The Reddit proximity split — the 300-character model-or-framework proxy, 132
carriers of 975 documents — corrected against the stored pages:

| | count | share |
|---|---|---|
| model-only | 57 | 43% |
| framework-only | 4 | 3% |
| **both** | **1** | **1%** |
| **neither** | **70** | **53%** |

`both` and `neither` had been inferred from the reported 43% and 3% as a single
54% residual assigned to `neither`. **An inferred zero in `both` claims a
cleaner separation between model and framework than the data shows, which is
the wrong direction to be wrong in** — `both` is the one bucket that records
the proxy failing to separate them.

**`reddit_slice_store` holds three runs of `reddit_slice.py`, not one.**
Response bytes differ between runs, so content-hash addressing did not collapse
them. The 975-document set is the **sweep half of the last run, pages 109–157
by write order**. Re-sieving the whole store, or either earlier run, reproduces
**39.7% / 2.7%** instead of 43% / 3% — a number that disagrees silently, which
is the failure this note exists to prevent.
