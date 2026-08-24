# What is next in `collect/`, picked rather than continued

**One author. Sixty-four documents. A gate that needs three effective voices
across two platforms.**

That is the whole argument. Extraction now works — 36 verified claims from 30
blog documents, storage path proved, salvage in, capability choice with a
labeller — and **none of it can produce a single publishable cell**, because
every claim in the corpus comes from the same person.

*Engineer 1 · 2026-08-21 · measured against `52.17.75.29/Model-information-Board`*

---

## 1 · The measurement that decides the order

```
documents by source        docs   with author_id   distinct authors   with url
  blog                       31              30                  1         31
  github                     27               0                  0         27
  reddit                      6               0                  0          6
                            ---             ---                ---
                             64              30                  1         64

author rows in the database   1
claim rows                    4
cell rows                     2
```

Against `judge/curate/gate.py`:

```
N_EFF_MINIMUM      = 3.0     weighted independent voices
PLATFORM_MINIMUM   = 2       distinct platforms
```

**We have 1 voice on 1 platform.** Not 1 short — 2 voices and 1 platform short,
with no path to either from the blog feed, because the blog feed is one person
writing. Every cell is `insufficient` and correctly says so. The board is
honest and empty.

**`author_id` is NULL on 34 of 64 documents, and on 33 of those it is every
document the source has.** An anonymous document cannot be a voice: it cannot be
counted, cannot be de-duplicated against another claim by the same person, and
cannot be attributed on a page. So 33 documents that are already fetched,
already stored, already parsed are worth zero to the gate.

That is the constraint, it is in this lane, and it is the cheapest thing on this
list.

---

## 2 · The pick: `author_id` on Reddit and GitHub documents

**`document.author_id` is written by `collect/adapters/blog/write.py` and by
nothing else.** Already recorded as a finding; now it is the blocker.

Why this first, in the order the reasons matter:

1. **It is the only item that changes what the gate can see.** Everything else on
   this list improves claims we already cannot publish.
2. **The data is already local.** Reddit's payloads carry `author` — verified
   earlier: all 195 comments in the harvested thread have it, and the 3 without
   `author_fullname` are `[deleted]`, so they have neither. GitHub issue payloads
   carry `user`. This is a write path, not a fetch.
3. **Reddit is where multiple humans are.** 6 documents today from a thread whose
   raw payload holds 195 comments. Blog is structurally one voice per feed;
   Reddit is structurally many. Two platforms with real authors clears
   `PLATFORM_MINIMUM` and makes `N_EFF_MINIMUM` reachable.
4. **It is reversible and testable without a model call.**

**Cost:** two `write.py` paths, an `author` upsert reusing
`collect/assemble/authors.py` (`handle_hash`, and **do not store the handle** —
that ruling stands, the username is re-derivable from the raw store at render
time), and a backfill over 33 existing documents from their stored payloads
rather than a re-fetch.

**What it does not fix, said plainly:** three voices on two platforms is the
*floor* for a cell to publish at all. `WIDELY_PRAISED_VOICES = 5`. One Reddit
thread will not build a board; it will make the gate's arithmetic non-trivial
for the first time, which is the point.

---

## 3 · Second: triage has never run

```
triage_verdict:   NULL on 64 of 64 documents
```

Every document that has reached extraction reached it **unfiltered**. So:

- the ~10–15% survival estimate has never been measured against the corpus we
  actually sweep — it remains an estimate, and its population is still
  unnamed at the point it is quoted;
- `document.specificity_score` is NULL on every row and the selector recomputes
  it in Python, so the stored column is decorative;
- the sieve is the component with the most code and the least evidence in this
  lane.

Second rather than first because it *reduces* the corpus, and reducing a corpus
that already cannot fill a cell is the wrong direction this week. It becomes
urgent the moment Reddit ingestion grows, which is the item above.

---

## 4 · What I am deliberately not doing next, and why

| | why not now |
|---|---|
| **capability descriptions into the prompt** (largest lever on extraction quality) | It changes what the extractor emits, and round 3 is drawn from the current extractor. Doing it now makes the golden set measure a superseded model. It is blocked *behind* round 3's labelling, not deferred. And it is E2's file. |
| **a new capability key** | The evidence for it was withdrawn (`the-effort-dimension.md` §4) and the instrument that would settle it is with a labeller. |
| **the remaining `compute()` gaps** — `claim_date` and `platform` still come from a dataclass whose only constructor is a test | Real, and it is weighting work on 4 claims. It refuses loudly now rather than defaulting silently, which was the dangerous half. |
| **OpenRouter polling / retiring `seed_models.yaml`** | The fixture is 10 models and the registry has 324. It is not currently costing anything, and it is a whole subsystem. |
| **`subject_inherited` column** | Derived in code and proposed. Waiting on E2, correctly. |
| **anything in `judge/`** | I have been in that lane on instruction for several turns. With extraction working and the capability question out for labelling, the reason to be there has run out. |

---

## 5 · The one-line version

**Extraction is no longer the bottleneck; attribution is.** Thirty-three
documents are already on disk and worth nothing to the gate because nobody knows
who wrote them, and that is a `write.py` change in this lane rather than a
question for anyone else.
