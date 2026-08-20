# `claims_unresolved` — the shape is right, and one half of it is ours

**Confirming Engineer 2's column from the `collect/` side. The diagnosis is
correct and the code already says so one line above the gap. Two amendments:
the count needs the population it failed against, and the route/unresolvable
split she would need is not computable in her lane with what we currently hand
her — so widening that is mine.**

*Engineer 1 · 2026-08-20 · `contract/` unchanged by this document*

---

## 1 · The defect, confirmed

`ExtractionLedger.should_skip` reads three things:

```
thread_context_id      the thread
pipeline_version       the code
content_fingerprint    the text
```

**None of them is the registry.** So a thread whose claims all named a model no
alias surface reached writes `claims_written = 0`, and on the night the surface
lands it has the same id, the same `pipeline_version` — registry growth is not a
code change — and the same fingerprint, because the text did not move. It skips
forever, and the row asserting it says only that we read it and found nothing.

`judge/pipeline.py` already states the intent, immediately above the line that
does not carry it out:

> ```python
> # Unresolvable is a real state and a counted one. Dropping it
> # silently is how "nobody discusses this model" and "we could
> # not resolve the name" become the same absence.
> continue
> ```

It is logged at INFO and counted nowhere durable. So this is not a design
disagreement — it is a comment that is one column short of being true.

**Rule 2 is intact and worth confirming while we are here.** The extractor
*proposes* `model_ref.resolved_version_id`; `pipeline.py` decides by looking it
up in `model_version_of`. The model does not resolve anything. So a counter over
those failures counts a code decision, not a model opinion, and nothing about
this proposal touches the two-LLM boundary.

---

## 2 · A count without its population cannot decide a re-read

This is the same problem as the entity gate, one layer up, and it is measured.

```
385 of 1,297 documents — 29.7% — change the entity gate's verdict
  on the alias population alone, with no document changing
  (docs/measurements/triage-gates.md §3)
```

`SurfacePopulation.fingerprint` exists for exactly that, and `pipeline_version`
was explicitly ruled insufficient there for exactly the reason it is
insufficient here: *this gate's answer changes when the registry grows without a
line of code changing, so two runs at the same `pipeline_version` can
legitimately disagree.*

So `claims_unresolved = 3` is not yet actionable. Three unresolved against 59
surfaces and three against 1,337 are different facts, and only the second is
worth re-reading — the first will resolve itself the moment the review artifact
lands.

**And it is not reconstructible afterwards.** `write_model_versions` upserts
`ON CONFLICT (canonical_id) DO UPDATE`, so the registry keeps no history of its
id set; `model_event` is the nearest thing and holds 0 rows, because a first poll
has no prior state to diff. The population has to be **recorded at extraction
time or it is gone.**

> *A figure to correct while we are here:* the sibling proposal
> `coverage-gap-unresolvable-mentions.md` cites this as "385 of 1,900". It is
> **385 of 1,297**. 1,900 is the unfiltered sweep's corpus, which is a different
> population and a different measurement.

---

## 3 · Two counters, not one — because our side already refuses to collapse them

`docs/proposals/coverage-gap-unresolvable-mentions.md` proposes the harvest-side
counterpart and splits it deliberately:

| | what it means | what it is evidence of | the response |
|---|---|---|---|
| `mention-resolves-to-route` | the surface matched, the owner is a route, we declined | **our ruling** | possibly reopen the ruling |
| `mention-unresolvable` | nothing in the population matched | **our coverage** | a review item for the surface list |

*"Collapsing them would make a growing pile ambiguous between 'the ruling is
costing us more than we thought' and 'the alias population has a hole' — which
need opposite responses."*

A single `claims_unresolved` on `thread_extraction` collapses precisely that
distinction, and it would put the two sides of the lane boundary into
disagreement about one concept — which is the thing `contract/` exists to
prevent.

**The third state stays out of both, on the same reasoning.** A surface matching
a bare family word — `opus` — is excluded from the population by design and is
attested constantly. Counting it would swamp both numbers with a fact already
measured (`alias-surfaces.md` §4: 62% of family-word mentions carry no version).
A claim resolved at `family` specificity is a fourth thing again: attributable to
a line rather than a tier, so it can record a claim and never lift a cell. It is
not unresolved and it is not a coverage gap — **nothing we do fixes it, because
the human never said which model** — so it needs neither counter.

---

## 4 · The half that is ours: `model_version_of` cannot express "declined"

Here is the constraint that decides the work split, and it is the lane boundary
doing its job.

`pipeline.py` resolves with `model_version_of.get(claim.model_ref.resolved_version_id or "")`.
A miss is a miss. To tell *route* from *unknown*, her lane would have to ask
whether an id is a route — and **`is_route` lives in
`collect/registry/propose.py`, which `judge/` may not import.**
`tests/test_lane_boundary.py` asserts both directions, so the split is not
computable in her lane however she writes the column.

Two ways out, and the first is better:

**(a) Widen what we hand across.** `model_version_of` is a mapping supplied by
whoever composes the run. Today a route is simply absent from it, which is
indistinguishable from an unknown id. Hand a mapping that distinguishes the two —
a route id present, mapped to a sentinel meaning *declined by ruling* — and both
counters become computable in her lane with **no import and no new dependency.**
The distinction is already a pure function of the canonical id on our side; what
is missing is that we throw it away before she sees it.

**(b) One counter for her, and the split on our side from `coverage_gap`.**
Cheaper today, and it means the *"is the route ruling expensive"* question is
answered from one table and the *"did an extraction skip because of it"*
question from another, with no key joining them. Rejected unless (a) turns out
to cost something.

**This is the third instance of one shape in a week**, and it is worth naming as
such: a ruling that is correct, enforced, and **destroys the information the
other side needs in order to report on it.** `is_route` has now needed four
callers; this is the same rule needing an *output* rather than a call site.

---

## 5 · Proposed shape

Hers to write, since `thread_extraction` is her table. Recorded here so the
`collect/` side of it is committed rather than remembered:

```sql
-- Nullable, for the reason content_fingerprint is nullable: a row written
-- before this column was not measured at "nothing unresolvable". A DEFAULT 0
-- would make every pre-existing row assert that nothing was unattributable,
-- and skip forever on a confident zero.
claims_unresolved   int,

-- Matched, owner is a route, we declined. Separate because the response is
-- different -- see §3. Needs (a) above to be computable at all.
claims_route_only   int,

-- The SurfacePopulation fingerprint this run resolved against: 16 hex chars,
-- sha256 over the sorted surface set. Without it the two counts above cannot
-- decide a re-read -- see §2. Not reconstructible later.
resolver_population text,
```

And the skip rule gains one clause: skip when the fingerprint matches **and**
`resolver_population` is unchanged. A row with `claims_unresolved > 0` under a
population that has since changed is a re-read, not a skip.

**`NULL` in either counter means not measured, and the reader must treat it as
"must re-read"** — the same treatment `content_fingerprint` already documents,
and for the same reason.

---

## 6 · The second silent drop on that path, while it is open

`pipeline.py` drops a claim in one other place, also logged and also counted
nowhere:

> `no document facts for %s; claim skipped rather than weighted from defaults`

Different remedy again — the `document` row is missing, which is a `collect/`
gap and not a coverage one — so it wants its own counter rather than joining
either above. Raised here because it is the same shape on the same path and
cheaper to add once than to rediscover.

---

## 7 · What would revise this

- **`model_version_of` growing an explicit "declined" state**, which is (a) and
  is the whole of the `collect/` work.
- **A registry with history.** If `model_version` ever became append-only, the
  population would be reconstructible as-of a date and `resolver_population`
  could be dropped. It is not, and nothing plans it.
- **Measuring how often this actually bites.** Today `document` holds 30 rows,
  all blog, so the unresolved count over a real corpus is unmeasured — the
  argument above rests on the entity gate's 29.7%, which is the same mechanism
  and a different stage.
