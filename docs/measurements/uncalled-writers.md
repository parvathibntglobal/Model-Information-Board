# Writers that exist and have never been called

**Audited after the `in_window` defect, which was a correct writer whose sole
caller had never run. Two more have the same shape — `mark_swept` and
`write_authors` — and both had already left residue on staging from being
exercised by hand. Eleven of twelve tables are empty.**

*Engineer 1 · staging · no fetch · 2026-08-18*

> The `in_window` defect was not "the code is wrong". `recompute_window` is
> correct and tested; nothing had run it, so 340 rows carried a schema default
> that reads exactly like a computed answer. This is a search for the same
> shape elsewhere.

---

## 1 · Every write-issuing function in `collect/`, and its callers

Fifteen functions issue `INSERT`, `UPDATE` or `DELETE`. Counting **real call
sites** — docstring mentions excluded, which matters because three of
`write_authors`' apparent callers are prose:

| writer | production callers | rows on staging |
|---|---|---|
| `write_model_versions` | `ops/chain.py:242` | 340 |
| `migrate` | `cli.py` (×2) | 0 |
| `recompute_window` | `cli.py:188` | 340 ✔ *ran today* |
| `load_source_rows` | `cli.py`, `ops/` | **0** |
| `write_documents` | `scripts/harvest_github.py:187` | **0** |
| `write_events` | `openrouter.py:553` | **0** |
| `append_prices` | `openrouter.py:523` | **0** |
| `_sync_alias`, `_upsert_model`, `_write_price_tiers`, `_record_event`, `_record_prices` | `load_seed()` | **0** |
| **`mark_swept`** | **none** | — |
| **`write_authors`** | **none** *(3 docstring mentions)* | 0 *(4,391 deleted 2026-08-18)* |

**Only `model_version` has rows.** `model_alias`, `model_event`,
`pricing_history`, `price_tier`, `source`, `document`, `author`,
`thread_context`, `harvest_run`, `watermark` and `schema_migration` are all
empty.

---

## 2 · Three distinct conditions, and only the first is what was expected

The audit found the shape the `in_window` defect suggested, and two others that
are worth separating because they need different responses.

### A · No caller at all — `mark_swept`, `write_authors`

`mark_swept` is referenced twice in the tree and both are in
`tests/test_registry_openrouter.py`, one of which asserts only that the function
exists. `write_authors` has three apparent callers in `collect/` and **all three
are docstrings** describing the batching incident.

Neither is dead code — both are correct, tested, and needed. They are writers
waiting for a caller that has not been built: the rotation for one, the assembly
path for the other.

### B · A caller that has never run against a real database

`write_documents` has exactly one caller, `scripts/harvest_github.py`, and
`document` holds 0 rows. `load_source_rows` has callers and `source` holds 0.
`migrate` has ten and `schema_migration` holds 0.

**This is the more common condition and the harder one to see**, because a
caller exists, so every audit that greps for callers reports it as wired. The
`in_window` defect was exactly this: `recompute_window` had a CLI command, and
nobody had typed it.

### C · Residue from being exercised by hand

Both of the writers in A have written to staging anyway, from ad-hoc Python
calls, and both left a value that reads as a measurement:

| | |
|---|---|
| `write_authors` | 4,391 author rows against 0 documents — deleted 2026-08-18, `docs/measurements/staging-author-residue.md` |
| `mark_swept` | **one row**: `anthropic/claude-opus-5`, `last_swept_at = 2026-08-17 08:33:59` — 81 seconds after its `first_seen_at` |

`last_swept_at` is the column whose own schema comment says **"NULLABLE, AND
NULL MEANS NEVER SWEPT. Not 'swept long ago' and not 'swept now'"**. One model
claimed to have been swept when nothing has ever swept anything — and it is the
most-discussed model in the corpus, so it is the row a rotation would have
skipped and the coverage page would have shown as current.

Cleared:

```
cleared 1 of 1; last_swept_at non-null now 0
NULL is the truthful value: nothing has ever swept anything.
```

---

## 3 · Why the residue keeps appearing, and what would stop it

Three incidents now, all the same mechanism: a writer with no caller gets
exercised from a Python prompt against `DATABASE_URL`, because that is the only
way to see it work. The rows outlive the test.

`reset_schema` is guarded three ways against exactly this database. **The
writers are guarded none.** That asymmetry is the whole story — the destructive
path was hardened after a near miss, and the constructive paths were never
considered dangerous.

They are, in one specific way: **a written row is indistinguishable from a
computed one.** That is the same sentence as the `in_window` finding and the
same sentence as `phrase_present = None` versus `0`.

Not proposing a guard here — `assert_no_fixtures` and `assert_contract_backed`
already exist for provenance and are now wired through `ops/preflight.py`, and
the right fix is probably to give these writers a CLI command so they stop being
exercised by hand. That is a build decision, not a measurement.

**What is proposed is narrower:** `model_version.last_swept_at` should be
covered by preflight the way seeded rows are. A non-NULL `last_swept_at` while
no sweep exists is a detectable contradiction, and it is the column FR-1's
coverage surface reads.

---

## 4 · What this does not say

**It does not say these writers are wrong.** Every one is tested, and
`write_model_versions` — the one with a real caller on a real path — has written
340 correct rows. The finding is about what has *run*, not about what works.

**It does not say the empty tables are a defect.** `thread_context` is empty
because `assemble_thread` refuses, deliberately, and `harvest_run` is empty
because no harvest has run against staging. Those are known states with reasons.

The distinction worth keeping: an empty table whose writer has a caller nobody
has invoked is a **schedule** problem; an empty table whose writer has no caller
is a **build** problem; and a table with rows from a hand-run is neither — it is
a measurement hazard, and it is the only one of the three that can produce a
wrong number today.
