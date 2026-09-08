# Discovered capabilities: the cell question, answered

**2026-09-08, anooj.** A reading of `judge/extract/prompt.py`'s capability-
proposal path against the schema, to answer one question: does a discovered
capability carry a canonical, or do three engineers describing one behaviour
produce three cells with one voice each?

**Answer: they carry a canonical, and it is enforced by a foreign key, not by
the prompt. Three engineers describing one behaviour produce ZERO cells** — not
three. The cell space cannot be reached without a human ruling.

But the question is the right one and it has two real failures either side of
the place it was aimed. §3 and §4. Neither is the reason the board cannot
publish — §5.

---

## 1 · Why three cells cannot happen

Three separations, and the load-bearing one is in the DDL.

**(a) The prompt separates the fields.** A quote that fits no key does not get
classified into the nearest one. `judge/extract/prompt.py`:

> *Do not stretch a quote to fit a capability. Forcing a quote into the nearest
> key fabricates consensus about something the writer never discussed.*

Claims go in `claims[].capability`, and `build_system_prompt` appends *"Use
these keys and no others"*. Discoveries go in a **different field**,
`proposed_capabilities`.

**(b) The schema makes the vocabulary a foreign key.**

```sql
claim.capability_key  text NOT NULL REFERENCES capability(key)
cell.capability_key   text NOT NULL REFERENCES capability(key)
cell PRIMARY KEY (model_version_id, capability_key, condition_bucket)
```

So a claim cannot exist under an unregistered key, and a cell is keyed on the
same reference. **An invented key cannot become a cell — the insert fails.**

**(c) `capability_candidate` deliberately has no such FK.**

```sql
proposed_key  text NOT NULL          -- no REFERENCES
document_id   text NOT NULL REFERENCES document(id)
```

`judge/app.py`'s own words: *"Adopting one is a `contract/capabilities.yaml`
change (a PR), never a write here — the table has no FK to `capability` for
exactly that reason."*

**So the canonical is `ruling_target`, supplied by a person.**
`rule_candidates` takes `adopted | declined | merged`, requires a
`ruling_target` for the first two, and its docstring notes the target is checked
against `capability` *"precisely so a ruling cannot grow the vocabulary
sideways"*. Three descriptions ruled to one target become **one key, one cell,
three voices** — which is the outcome the question was hoping for, reached by a
human rather than by the model.

That is also rule 2 holding exactly where it should: **an LLM may propose, it
may never decide.** The vocabulary is the sharpest case of that, and the FK is
what makes it structural rather than remembered.

## 2 · What that means for the end-to-end run

A discovered capability produces, today:

```
3 documents describe one behaviour
   -> 3 rows in capability_candidate     (evidence, quotes verified)
   -> 0 claims                            (no key to hang them on)
   -> 0 cells                             (nothing to aggregate)
   -> the review page shows the proposals awaiting a ruling
```

**Zero cells with one voice is better than three**, and it is the correct
behaviour. But zero cells also means zero publishable, and §3 is why that
persists after a ruling.

## 3 · The first real failure: adoption does not backfill claims

**Nothing turns an adopted candidate's quotes into claims.** I looked for it and
it does not exist: `rule_candidates` writes `ruling` and `ruling_target` onto
the candidate rows and stops. Adoption is a `capabilities.yaml` PR, which adds
the key — and the evidence that motivated it is still sitting in
`capability_candidate`, which no cell reads.

So the sequence after a successful adoption is:

```
key adopted, capabilities.yaml merged   -> the vocabulary has it
quotes still in capability_candidate    -> no claim, so no cell
                                        -> STILL NOTHING PUBLISHABLE
```

**The documents must be re-extracted** to produce claims under the new key.
Nothing says so anywhere, and it is the kind of gap that reads as a bug six
weeks later when a newly-adopted capability shows an empty column.

**The mitigating fact is cost, and it is decisive.** A re-extraction of the
whole corpus is **$1.84** — 887 threads at the measured $0.00208 each
(`docs/measurements/extraction-token-counts.md`). So the fix is not an
expensive backfill path; it is one line in the adoption flow saying *re-run E5
over the documents that proposed this key*, and a note on the review page that
adoption is not retroactive. **I would not build a claim-backfill from
candidates**: it would put a claim in the database that no extraction produced
under the current vocabulary, and `pipeline_version` would lie about what made
it.

## 4 · The second real failure, and it IS the question one stage earlier

`list_candidates` groups by **exact `proposed_key` string**, and says so in its
own output:

> `count_is_a_floor`: *"distinct proposed_key strings; near-duplicate phrasings
> are not yet clustered, so this under-counts a capability proposed several
> ways"*

So three engineers describing one behaviour most likely produce **three
different proposed keys** — `output.verbosity`, `response.length`,
`token.overspend` — and therefore **three groups of one document each**. The
reviewer sees three weak signals instead of one strong one.

**That is the "three cells with one voice each" failure, displaced from the
board onto the review queue.** It does not corrupt anything, because nothing
reaches a cell — but it suppresses vocabulary growth at exactly the sizes that
matter: a proposal backed by one document looks like noise and gets declined,
where the same evidence pooled to three documents looks like a capability.

And the direction of the error is the dangerous one. Under-clustering here is
**over-declining**: real capabilities are refused for want of evidence that
exists and is not grouped. Note this is the *opposite* preference from
`collect/CLAUDE.md`'s dedupe rule — there, over-clustering is worse, because
merging two independent reports destroys corroboration. Here the two candidates
are not evidence about a model, they are votes for a word, so pooling them is
what makes the vote countable. **The two rules do not conflict; they are about
different objects, and it is worth writing that down before somebody applies
the dedupe reasoning to this queue.**

**What I would do about it:** nothing automatic. Cluster the *definitions* for
the reviewer's eye — show near-duplicate proposals side by side with a combined
document count, labelled as a suggestion — and leave the pooling decision to
the person, because a cluster is a claim about meaning and rule 2 applies.
That is a review-page change, so it is yours.

## 5 · Does this decide whether the end-to-end run can publish anything?

**No. The binding constraint is still the weight scale, and it is 30–60× away.**

`docs/proposals/for-the-team-the-publication-gate-is-uncalibrated.md`: `n_eff`
must reach **3.0** to publish; real forum claims weigh **~0.015**; the best cell
in the project — sonnet-5 · `reasoning.multistep`, 7 voices, 2 platforms — sits
at **n_eff 0.1409**. At 0.015/claim a cell needs ~200 distinct voices and the
best has 7. That was measured twice independently on the same arithmetic, at
**0 of 96 cells**; the table now holds **105 cells and still publishes 0**
(counted 2026-09-08). The corpus grew, the published count did not move, which
is the shape of a constraint that collection cannot close.

So the honest ordering of what stops the board publishing:

1. **the weight scale** — 30–60×, and no amount of collection closes it;
2. **the entity gate and the registry** — 33% of documents dropped, and
   `Fable 5.1` filed against Fable 5
   (`docs/proposals/for-the-team-alias-precision-and-four-registrations.md`);
3. **adoption not backfilling claims** — §3, worth one line and a re-run;
4. **candidate under-clustering** — §4, worth a review-page change.

Items 3 and 4 are real and cheap. Neither is why the board is silent. **If both
were fixed tomorrow the number of published cells would still be zero**, and I
would rather say that than let two tractable fixes read as the unblocking.

## 6 · The table is empty, so §3 and §4 are design notes

Counted rather than left open:

```
capability_candidate rows on staging   0
claims                               211
cells                                105
cells published                        0
```

**No capability has ever been discovered.** `store_proposals` is called from the
extract runner and the review page exists, so the path is wired — it has simply
never fired. That changes the urgency of §3 and §4 and not their substance:
both are design notes today rather than costs being paid, and both should be
settled before the first proposal arrives rather than after, because §4's
failure mode is a *declined* proposal and a declined proposal leaves no trace of
what it would have been.

It also sharpens §5. 105 cells exist and **0 publish**, with no discovered
capability involved at all. Whatever is stopping the board, it is not this
path.

---

*Read from `judge/extract/prompt.py`, `judge/extract/schema.py`,
`judge/store/capability_candidates.py`, `judge/app.py` and
`contract/tables.sql` at `fix/recover-triage-contract-and-two-fixes`. No code
changed; §3 and §4 are proposals for `judge/`, which is not my lane.*
