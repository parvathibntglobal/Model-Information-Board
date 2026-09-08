# 1,234 Reddit payloads are not in this host's raw store

**2026-09-08, anooj. A data finding, separate from the triage run** — it turned
up while triage ran for the first time, but it is not a triage problem and it
should not be read as one. **Nobody needs to act on the triage numbers to act
on this.**

Read §1 for the scope, because the headline is easy to overstate and I do not
want to.

---

## 1 · What is actually established, and what is not

**Established:** 1,234 of 2,999 Reddit `document` rows — **41.1%** — point at a
`text_ref` that is not present in **this machine's** raw store, and there is no
tombstone for any of them. `collect/rawstore.py` says what that means in its own
words:

> missing with no tombstone. NFR-4 rebuild-from-raw is no longer guaranteed.
> This is corruption or a bug, not a takedown.

**Not established: that the bytes are gone.** `RAW_STORE_PATH=./raw_store` is
**per-machine and gitignored** — it has never travelled through the repo. This
host holds 11,740 files and **0 tombstones**. So the honest statement is *absent
from this host*, and the first question for the team is the one I cannot answer
from here:

> **Does anyone else's `raw_store/` have these 1,234 objects?**

If yes, this is a distribution problem and NFR-4 holds. If no, 1,234 Reddit
documents can never be re-verified or re-extracted without re-fetching, and
re-fetching is subject to `reddit-via-rapidapi`. **Please check your own store
before anyone re-fetches anything.** Every row carries its `content_hash`
(1,233 distinct), so the objects are identifiable by hash on any machine — I've
listed how to check in §5.

Per source, for context — this is a Reddit problem and not a store problem:

| source | rows | readable | absent | absent % |
|---|---|---|---|---|
| **reddit** | 2,999 | 1,765 | **1,234** | **41.1%** |
| github | 3,382 | 3,373 | 9 | 0.3% |
| blog | 121 | 120 | 1 | 0.8% |

## 2 · The correlation is total, and it names the writer

Split by `retrieval_provenance`:

| provenance | rows | absent | absent % |
|---|---|---|---|
| `run_recorded` | 1,507 | **0** | **0.0%** |
| `not_recorded` | 1,492 | **1,234** | **82.7%** |

**Every document written by a path that opened a `harvest_run` has its payload.
Every missing payload belongs to a path that did not.** Zero exceptions in
either direction, over 2,999 rows.

By fetch day, the same picture:

```
2026-08-20    absent    0    present     6
2026-08-24    absent    0    present   190
2026-08-27    absent  806    present    47
2026-08-28    absent  210    present  1520
2026-08-31    absent  218    present     2
```

The 27th and the 31st are the ad-hoc days. **57 of the missing rows are posts
and 1,177 are comments** — and "57 roots" is the same figure
`contract/migrations/20260828T1600_correct_the_853_mislabelled_reddit_rows.sql`
records for the per-model fetch's Reddit arm (57 roots, 796 comments, 853 rows).
That is a match on shape, not proof of identity: the migration rewrote the
provenance of those rows, so the two populations can no longer be distinguished
by column. **Stated as a lead for whoever knows that arm, not as a conclusion.**

## 3 · A second bucket, and it is a different defect

248 more Reddit rows have a payload that **is present and is not a payload**:

```
text_ref  raw/sha256/08/a6/08a610…
bytes     'Fable 5 on med is cheaper than Opus 4.8 on xhigh and gives 10%+ …'
```

That is **stored prose**, not the platform's JSON. `collect/assemble/prose.py`
already records this: *"246 reddit rows still point at pre-extracted prose whose
payload was never stored, and they will refuse here."* I measure **248**. They
refuse correctly and are counted, not guessed.

It matters separately because it is an **NFR-6** problem rather than an NFR-4
one: `content_hash` on those rows fingerprints bytes **we assembled**, so the
hash moves whenever the extractor changes. The 1,234 have the opposite property
— their hashes are of platform bytes and are still trustworthy, which is what
makes them recoverable in principle.

**Together: 1,482 of 2,999 Reddit rows — 49.4% — cannot yield verifiable prose
from a stored payload on this host.**

## 4 · The survival figure, and why it is the most flattering number in the table

Reddit's **89.8%** is real arithmetic and it is not a fact about Reddit. Split
the same way:

| provenance | rows | absent | not prose | **triaged** | kept | survival |
|---|---|---|---|---|---|---|
| `not_recorded` | 1,492 | 1,234 | 248 | **10** | 8 | 80.0% |
| `run_recorded` | 1,507 | 0 | 0 | **1,507** | 1,354 | **89.8%** |
| all | 2,999 | 1,234 | 248 | 1,517 | 1,362 | 89.8% |

**The `not_recorded` half contributes 10 documents of 1,517 — 0.7% — to that
denominator.** So "Reddit 89.8%" is, to three significant figures, the survival
of the `run_recorded` population alone.

And that population is not a neutral sample of the other one. `run_recorded`
means a query was rendered and its id stored, and those queries **contain model
names** — which is precisely what `no-resolvable-entity` tests. The gate that
drops 31.5% of the corpus overall drops 1 of 1,517 here.

So the figure is doubly selected: it survives on the half of Reddit whose
payloads we still have, and that half is the half retrieved by queries
pre-filtered for the gate. Rule 7's exact shape — a real value answering a
question it was not asked. **The denominator to quote is 1,517 of 2,999
`run_recorded`-dominated documents, or don't quote it.** I've since put that
caveat in `docs/triage-first-run-2026-09-08.md` §1; it belongs here too because
this document is where the reason lives.

## 5 · What I'm asking for

1. **Check your `raw_store/` for these objects** before anything else. The
   1,233 distinct hashes are listed in
   `docs/measurements/reddit-absent-payloads-2026-09-08.json` (this run). One
   command per store; if you have them, the fix is a copy, not a re-fetch.
2. **Whoever knows the per-model fetch's Reddit arm**: did it write `document`
   rows without persisting to `raw/`, or to a store that isn't `./raw_store`?
   The provenance correlation is total, so the answer is almost certainly in
   that path.
3. **A decision on the 248 prose-as-payload rows.** They are a known, recorded
   defect and they are still there. Re-fetch fixes both buckets for the rows
   that are still fetchable; nothing else does.

**I have not re-fetched anything and I am not proposing to yet.** A re-fetch
spends the shared RapidAPI quota, and `reddit-via-rapidapi` permits it on an
internal-development basis — but doing it before question 1 is answered would
spend quota to recover objects somebody may already have on disk.

---

*Measured 2026-09-08 on `DATABASE_URL` (shared staging) against this host's
`./raw_store`. Every count above is over the 2,999 stored Reddit rows, which is
not a sample of Reddit. Raw figures:
`docs/measurements/reddit-absent-payloads-2026-09-08.json`.*
