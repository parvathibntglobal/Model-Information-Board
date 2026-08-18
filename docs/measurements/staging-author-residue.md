# 4,391 authors against 0 documents

**Residue of the write-batching incident, deleted 2026-08-18. Recorded here
because the rows are gone and the way they arose is not.**

*Engineer 1 · staging · no fetch · 2026-08-18*

> Nothing referenced them and nothing read them, so deleting cost nothing. What
> would have cost something is leaving them: the one measurement they were
> written to enable is the one they would have made wrong.

---

## 1 · What was there

| | |
|---|---|
| `author` rows | **4,391** — 4,233 reddit, 158 github |
| `document` rows | **0** |
| `document.author_id` non-null | **0** |
| `claim.author_id` non-null | **0** |
| `author_identity_cluster` rows | **0** |
| distinct `first_seen_at` | **1** — `2026-08-17 10:38:18.163003+00`, identical to the microsecond |
| `karma`, `account_created_at`, `identity_cluster_id` | NULL on all 4,391 |
| `handle_hash` | present on all 4,391 |

One timestamp to the microsecond means one transaction: a single
`write_authors` call, not an accumulation.

## 2 · How it arose

`write_authors` has no CLI command and no script. It is reachable only from a
Python call, so this was run by hand.

4,391 is a number that already appears twice in the tree, in
`collect/adapters/github.py` and the docstring of `tests/test_write_batching.py`:

> `write_authors` took ten minutes for 4,391 rows against a remote instance,
> roughly 130ms of latency each and almost no work, and 3.8 seconds batched.

So these rows *are* that run. Somebody exercised the author writer against a
remote instance to see what it did, it took ten minutes, and that produced the
batching fix in #45. The rows stayed.

The documents they were derived from did not, because they were never in this
database: that corpus lived in the scratch database
`scripts/substitution_slice.py` records as since reset. **Two runs, two
databases, and only one of them staging.** Nothing was lost and nothing was
wrong — an author writer was tested and the test data outlived the test.

## 3 · Why it was worth removing rather than leaving

Nothing reads `author` today. `author_id` appears as a foreign key on `document`
and `claim`, and the key points *at* author, so childless rows are referentially
fine. `judge/curate/gate.py` counts voices from `WeightedClaim.voice_id`, which
arrives via claim → author; with zero claims it never reaches them.

The exposure is one measurement, and it is the measurement these rows exist for.
`collect/assemble/authors.py` is explicit that it is FR-17's precondition and not
FR-17:

> write the rows, measure the overlap, and let the measurement decide whether
> FR-17 has anything to match

Run against staging as it stood, that overlap would have been computed over 158
GitHub authors and 4,233 Reddit authors **drawn from different sweeps of
different corpora**. Any cross-platform overlap it found would be a fact about
two unrelated runs. Any absence of overlap — the likelier outcome, and the one
the module already predicts — would have read as evidence that FR-17 has nothing
to match, which is exactly the conclusion the measurement is supposed to reach
honestly or not at all.

That is rule 7 with no percentage sign: a real count answering a question it was
not asked.

## 4 · Deleted, not marked

Marking was the alternative and it is worse here.

`author` has no `provenance` or `status` column — see `contract/tables.sql`. So
marking these rows means adding a column to a **shared table** to record a
one-off incident on one environment. That is a contract change, it would need a
migration, and it would put a permanent field on every future author row to
describe forty minutes in August.

The record belongs in version control, which is where this file is. The rows
belonged in a scratch database, which no longer exists.

The delete ran inside a transaction and re-checked the reference counts
immediately before issuing it rather than trusting the reads above — between a
check and a delete, a write can land.

```
deleted 4391 of 4391; author now holds 0
```

## 5 · What this does not license

**It does not say author rows are disposable.** They will be load-bearing the
moment `document` is populated, and FR-17's counting rule depends on them being
complete rather than convenient. What made these removable is that they had no
documents, no claims, no clusters, and a corpus that no longer exists — all four,
not any one.

**It does not make `write_authors` safe to run against staging by hand.** The
next person doing it should write the documents in the same transaction or use a
throwaway instance. `scripts/dev-postgres.ps1` exists for that.

## 6 · What would revise it

- **A real harvest run.** Once `document` is populated from a sweep whose authors
  are written alongside it, the FR-17 overlap measurement becomes meaningful for
  the first time, and §3's objection disappears.
- **A CLI entry point for the author writer.** It has none, which is why this ran
  from a Python prompt. A command that takes documents and writes their authors
  in one transaction would make the incident unrepeatable rather than merely
  documented.
