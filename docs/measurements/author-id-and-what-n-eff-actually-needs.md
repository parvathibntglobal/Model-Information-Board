# `author_id` on Reddit and GitHub — and the gate needs 248 people, not 3

**The write path is built and tested. The backfill ran and changed nothing,
for a reason worth more than the backfill. And the number this was for turns out
not to be the number that matters.**

Three results, in the order they were measured:

1. **Write path: done.** Reddit had no document writer at all; GitHub had one
   that omitted the column. Both now write `author_id`, 18 tests over the three
   requirements.
2. **Backfill: 33 candidates, 0 attributable.** Every Reddit and GitHub payload
   is absent from this machine's raw store. Named per document rather than
   skipped.
3. **`n_eff` does not move — and neither gate condition is fixed by this.** They
   fail independently, and *author attribution fixes neither on its own.* The
   binding constraint is arithmetic: at tier D, **248 distinct people in one
   cell** during a launch window, or 112 outside one. The thread has 152
   commenters in total.

*Engineer 1 · 2026-08-21 · measured against `203.0.113.5/Model-information-Board`*

---

## 1 · Before

```
documents        docs   with_author   distinct_authors
  blog             31            30                  1
  github           27             0                  0
  reddit            6             0                  0
  TOTAL            64            30    without: 34

author rows: 1   {'blog': 1}
```

**One author row in the whole database**, and `author_id` NULL on 34 of 64
documents — which is *every* document those two sources have.

`judge/store/cells.py` turns that into voices:

```python
voice_id = author_id or f"{ANONYMOUS_VOICE}:{platform}"
```

So authorless claims collapse to **one voice per platform**. That is the correct
conservative choice and it is documented as such — an unknown author is not a
known distinct author, and counting each as its own manufactures the very
independence the author cap exists to prevent. It also means 34 documents are
worth exactly one voice between them.

The gate on the four stored claims, run rather than reasoned about:

```
mv_86c0c8bf10aa4a0d/code.generation@context_size:unknown
   claims 2   voices 1   n_eff 0.012   platforms 1   voice_ids ['anonymous:reddit']
mv_86c0c8bf10aa4a0d/over_refusal@context_size:unknown
   claims 2   voices 1   n_eff 0.012   platforms 1   voice_ids ['anonymous:reddit']
```

Against `N_EFF_MINIMUM = 3.0` and `PLATFORM_MINIMUM = 2`. Not a near miss — a
**250-fold** shortfall on the first.

---

## 2 · The write path, and the three things it gets right

None of the three rules is new. `collect/assemble/authors.py` already had all
of them, with the reasoning written down. **What was missing was anything
calling it** — which is why this was a wiring job and why it was cheap.

| | |
|---|---|
| **`collect/adapters/reddit_write.py`** | new. `document_row`, `write_documents`, `backfill_authors`. Reddit had no document writer; its six rows came in through `_handoff/load.sql`, which sets `author_id` NULL. |
| **`collect/adapters/github.py`** | `write_documents` now writes authors first and sets `author_id`; new `github_author_id` helper. |

**Ids canonicalise.** `t2_2ii4xgakc7` from a post and `2ii4xgakc7` from
`getProfile` resolve to one `author.id` — asserted, because `author` is
`UNIQUE (source, external_id)` and two spellings taken verbatim are two rows for
one engineer: a split voice that FR-17 then counts twice while believing it
counts once. GitHub keys on `user.id`, never `user.login`: a rename must not
create an author and a reused login must not merge two people. Asserted both
directions, and that the two platforms' identical digits do not collide.

**The handle is not retained.** Only `hash_handle`'s digest, casefolded so a
case-only rename is one hash. Tested by asserting no field of the row — and
nothing in its `repr` — equals the handle, on the `author` row and on the
`document` row. Data minimisation rather than secrecy, as recorded: a digest of a
public username is reversible from a username list; what it buys is that the
handle cannot be read out of a row, logged by accident, or published by a query
that forgot a column. Re-derivable from the raw store if the publish path ever
needs it.

**No author means no row.** `[deleted]`, `[removed]` and `[unavailable]` hash to
`None`. The test that carries the point builds **115 authorless comments** —
the corpus-wide count — and asserts `rows == []`, `distinct_authors == 0`,
`unattributable == 115`, and that no two of them share an id. A shared hash or a
sentinel `external_id` would merge 115 absences into one loud voice that the gate
then reads as corroborating itself.

### A defect the tests found, and it was not a test-double problem

`document_row` first asked `isinstance(item, RedditComment)` to decide whether to
write `thread_root_id` and `parent_id`. A double carrying both fields took the
*post* branch and had its linkage written as NULL.

That is a real failure with a live precedent: **all six existing reddit rows have
`thread_root_id` NULL**, and anything reaching this function from another path — a
backfill re-parsing a stored payload, a re-parse, a later comment type — would
have silently joined them. A missing link must come from the data lacking it,
never from a type check. Now discriminated on the fields.

**591 tests pass** across the adapter and author modules.

---

## 3 · The backfill: 33 candidates, 0 attributable

```
authorless reddit+github documents   33
attributable from the stored payload  0
distinct authors they resolve to      0
  could not attribute — named rather than skipped:
      27  github: payload missing
       6  reddit: payload missing
```

**Every payload is absent from this machine's raw store.** `RAW_STORE_PATH` is
`./raw_store`, 210 files, holding the blog corpus. The database is remote and its
store lives on that host. This is the same local-store / remote-DB split found
earlier in the week.

So the backfill is correct and cannot run here. Three things about that, because
"0 changed" is the same output a no-op produces:

- **it reports per reason, not as a total.** `missing`, `tombstoned` and
  `corrupt` are three findings and only one is routine — a tombstone is a
  takedown honoured, a missing blob is an NFR-4 alert. All 33 here are `missing`.
- **it sources from the stored payload, never a re-fetch.** Beyond the standing
  convention, a re-fetch would attribute a document to the account's *current*
  handle rather than the one that wrote it. The stored payload is the only source
  that cannot drift.
- **it only ever fills a NULL** (`WHERE author_id IS NULL`), so re-running is
  safe and a later, worse parse cannot overwrite an attribution.

Run it on the host that holds the store and it will attribute what the payloads
carry. `scripts/backfill_authors.py --dry-run` prints the census either way.

---

## 4 · What `n_eff` reads once it lands — reported as two conditions, separately

**Neither moves, and for two unrelated reasons. Only one of them is what this
fixes, and it turns out to be neither.**

### The voice count: unchanged, and correctly so

All four stored claims come from **one author** — `ClaudeOfficial`'s root post in
the `1u1b22l` announcement thread. With `author_id` written they are still one
voice, because they *are* one person. The fix cannot move a count that is already
right.

It moves the count only when claims come from **distinct commenters**, and the
comment tree has never been extracted: the six reddit documents are the root plus
five comments, kept for the judge-side fixture. So the voice count is waiting on
extraction over the thread, not on attribution.

### The platform count: unchanged, and for a different reason entirely

All four stored claims are `reddit`. **The 36 blog claims from the corpus run
were never written to `claim`** — they live in
`docs/measurements/blog-extraction-run.json`. So `platform_count = 1` until blog
claims are stored, and that has nothing to do with authors.

**This is the one that is cheap.** Two platforms is a storage step over claims
that already exist and are already verified.

### And the arithmetic that outranks both

This is the finding. Voices needed **in one cell** to reach `n_eff = 3.0`,
computed from the only `claim_weight` rows that exist:

```
w_final = 0.12 × 0.85 × 0.58 × 1.0 × 0.7579 × 0.45 × 0.6 = 0.012105
          tier  plat  spec  rel  recency launch fuzz

non-tier multiplier  0.1009      — everything except the evidence tier

                   in a launch window     outside one (f_launch 1.0)
  tier A                29.7 voices              13.4
  tier B                45.8                     20.6
  tier C                85.0                     38.2
  tier D               247.8                    111.5
  tier E               743.5                    334.6
  tier F              1486.9                    669.1
```

**Tier D is "bare first-hand opinion" — what most Reddit comments are.** It needs
**248 distinct people in one cell.** A cell is one model × one capability × one
condition bucket.

The ceiling, stated so nobody has to imagine it:

```
all 152 of the thread's distinct commenters, one cell, tier D, launch window
   n_eff = 1.84   FAILS
same outside a launch window
   n_eff = 4.09   passes
```

**Every commenter in the thread, all on the same capability in the same bucket,
does not pass the gate during a launch window.** And that is the maximally
favourable case: 152 is the thread's total across all twelve capabilities.

So `author_id` is **necessary and nowhere near sufficient**, and the binding
constraint is the multiplier chain, which cuts every claim to a tenth before its
tier applies.

> ⚠ **DO NOT ACT ON THE 248 YET, AND THE REASON IS IN OUR OWN NOTES.**
> `f_specificity = 0.58` is the only value that column has ever held — three of
> its four inputs are dead, already recorded. So the multiplier is partly an
> artefact of an unfinished weighting path rather than a measured property of
> these claims. `f_launch = 0.45` is correct and by design (frozen at
> extraction, so launch-week hype cannot un-discount itself).
>
> The number to argue about is therefore **not** `N_EFF_MINIMUM = 3.0`. It is
> whether the multipliers are finished. Lowering the threshold against a
> known-broken `f_specificity` would be tuning a gate to compensate for a bug,
> and the gate would stay wrong once the bug was fixed.
>
> Population: **one distinct set of factor values, on 4 claims, from 1 thread.**
> Every figure in the table above scales that one row. It is an existence proof
> about the arithmetic, not a rate.

---

## 5 · What this changes about what is next

The order in `docs/engineer-1/whats-next.md` was right about the blocker and
wrong about which half of it is cheap.

| | |
|---|---|
| **1. store the blog claims** | `platform_count` 1 → 2 on claims already extracted and verified. Cheapest movement available, and it is a storage step, not a fetch. |
| **2. run the backfill on the host** | mechanical, and it is what the 33 documents are waiting for. |
| **3. extract the comment tree** | what actually turns 152 commenters into voices. Needs 1 and 2 to be worth anything. |
| **4. finish `f_specificity`** | before anyone touches `N_EFF_MINIMUM`. Three dead inputs are the reason the threshold looks unreachable, and the threshold is not the thing to change. |

---

## What changed

| file | change |
|---|---|
| `collect/adapters/reddit_write.py` | **new** — Reddit document writer with `author_id`, plus `backfill_authors` |
| `collect/adapters/github.py` | `write_documents` writes authors and sets `author_id`; `github_author_id` added |
| `scripts/backfill_authors.py` | **new** — payload-sourced backfill, census before and after, every failure named |
| `tests/test_author_attribution.py` | **new**, 18 tests: canonical ids, no handle retained, no shared row for 115 absences |

591 tests pass across the touched modules. Nothing in `judge/` was modified.
