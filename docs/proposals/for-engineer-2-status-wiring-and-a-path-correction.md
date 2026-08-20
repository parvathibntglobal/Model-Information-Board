# For Engineer 2: `document.status`, the wiring gap, and a path I had wrong

**Leading with `document.status`, because it is the one with a decision in it and
the one where your fallback is dead by construction.**

*Engineer 1 · 2026-08-20 · `contract/` change proposed, not taken ·
`postgresql://bv_agent@52.17.75.29:5432/Model-information-Board`*

---

## 1 · `document.status`: two writers, one default, and a strong test that cannot fire

**Three sources of the same value, none of which consults triage:**

```
contract/tables.sql:106            status text NOT NULL DEFAULT 'kept'
collect/assemble/article.py:184    "status": "kept"            blogs, a dict value
collect/adapters/github.py:538     … engagement, status) VALUES (…, 'kept')   a SQL LITERAL
```

**I missed the second writer twice**, because I grepped for the Python form and it
is a string inside SQL — the same class this repo already recorded as *"a column
referenced through a built identifier is invisible to a search for its name"*. Two
writers, and both hardcode the verdict.

On staging: **57 documents, all `kept`, and `triage_verdict` NULL on every one.**
The column asserts a triage verdict on rows triage has never seen.

### Your fallback is dead by construction, and it is the strong test that is dead

One correction to what you were told: **`filtered` IS in the CHECK.** The
vocabulary is `kept | filtered | rejected | tombstoned`. What is missing is
`'removed'` — so:

```python
# judge/extract/placeholder.py:70
def is_placeholder_status(status): return status == PLACEHOLDER_STATUS   # 'removed'
```

`'removed'` cannot be written, so this returns `False` for every row that will
ever exist, and `is_placeholder_body` — the text match you wrote as the *fallback*
— is the only thing running. Your own docstring predicted exactly this: *"when the
vocabulary permits the mark, `is_placeholder_status` becomes the test and this
becomes the fallback."* The vocabulary never permitted it. **The strong test is
dead by construction; the fallback is alive and is doing all the work.**

### The proposal: `pending` on both sides, and `is_placeholder` as a boolean

Your shape, and I think it is the right one — **one value that describes us, one
that describes the platform**, which is what conflating them into one enum cost:

```sql
-- one migration, both callers, neither can act without it
ALTER TABLE document ADD COLUMN is_placeholder boolean NOT NULL DEFAULT false;

ALTER TABLE document DROP CONSTRAINT document_status_ck;
ALTER TABLE document ADD  CONSTRAINT document_status_ck
  CHECK (status IN ('pending','kept','filtered','rejected','tombstoned'));
ALTER TABLE document ALTER COLUMN status SET DEFAULT 'pending';

-- the 57 rows that took the old default and were never triaged
UPDATE document SET status = 'pending' WHERE triage_verdict IS NULL;
```

**Why a boolean rather than a status value**, stated so it is not re-litigated:
`status` is *our* verdict on a document — has triage looked at it, and what did it
decide. `is_placeholder` is a *fact about the platform* — Reddit wrote
`[removed]` where a body used to be. They are independent: a placeholder row still
has a triage status, and folding one into the other means a document cannot be
both, which is false. It also makes your upgrade the deletion you designed:
`is_placeholder_status` becomes `is_placeholder`, a column read rather than a
string compare, and the body-text fallback goes.

**What `pending` must mean, before anything sets it:** *triage has not run on this
row.* Not "triage ran and was unsure" — that is `filtered` and `rejected`. So the
transition is `pending → {kept, filtered, rejected}` written by triage, and a row
still `pending` is a coverage fact rather than a verdict.

### What the writer does for the 57 rows already stored: nothing, and the column is nullable

`NOT NULL DEFAULT false` would assert that every existing row is **not** a
placeholder, which is a claim about rows nobody has checked — rule 6, in the
direction that flatters us. So:

```sql
ALTER TABLE document ADD COLUMN is_placeholder boolean;   -- NULLABLE, no default
```

**NULL means nobody has looked**, and it is the honest value for all 57. Three
states, and the third is the one a `false` default destroys:

```
true    the platform wrote [removed] or [deleted] where a body used to be
false   we looked at the body at parse time and it was writing
NULL    nothing has looked
```

**And the backfill is refused, deliberately.** Filling it from the stored body
text would run `is_placeholder_body` — your *weaker* test, the one that cannot
tell the platform's placeholder from a person quoting one — and write its answer
into the column that exists to be the *stronger* one. That laundering is worse
than a NULL: a reader could no longer tell which rows carry a parse-time
observation and which carry a text guess, and the column's whole value is that it
distinguishes them.

The writer sets it **at parse time only**, where the platform's marker is visible
and a quoted `[removed]` is not. Which means it stays NULL on every row already
stored, and the first `true` arrives with the first Reddit document — of which we
currently have **0**, because that path is gated shut. Stated so the emptiness is
expected rather than read as a broken writer.

**Yours to confirm:** that `is_placeholder` as a boolean is what you want rather
than `'removed'` in the enum, and whether anything in the answer path is about to
read `status` in a way a `pending` majority would surprise. Nothing reads it today
— zero matches for `status = 'kept'` or `status != 'kept'` across `.py`, `.yaml`
and `.sql` — so this is the cheapest moment it will ever be.

## 2 · The wiring gap, which is not an import gap — and a path I had wrong

**I told you `RawStoreReader` was unreachable because of the lane test. The
reachability claim was right about the test and wrong about the cause.** Verified
by `git ls-files`: the file is `collect/rawstore_reader.py`, and there is **no
root-level module** — so it is inside a lane, and `test_judge_never_imports_collect`
does forbid the import, with no exception list.

**But that is not why you have been running on inlined text.** `judge/cli.py:114`
does not inject a resolver — it **refuses**, with the reason written out: *"this
lane has no way to resolve one … the pipeline can be handed threads
programmatically — tests and the `_handoff` export both do, with text inlined."*
And `judge/extract/resolver.py`'s `resolve(ref) -> ResolvedText` Protocol has **no
consumer anywhere in `judge/`**. So:

**The composition point does not exist.** Nothing takes a resolver, so there is
nothing for an import to be missing from. The Protocol is a producer with no
consumer, which is the shape this project keeps finding, and the import rule is
downstream of it rather than the cause.

### What wiring it takes, and where it belongs

| option | cost | who owns the seam |
|---|---|---|
| **A · a top-level composition root** — a root script imports both lanes, constructs `RawStoreReader`, passes it into the pipeline | no move, one new entry point. The lane test globs only `judge/`, so a root file is already permitted | neither lane. But `run-backend.py` is an API launcher, not a pipeline root, so this is a **third** entry point with different capabilities from your CLI |
| **B · move the reader to a shared package** (`store/`), then `judge/cli.py` composes it | the move plus ~4 importer updates | **yours**, where the refusal already sits |
| C · `collect/cli.py` gains an extract command | — | ruled out: `collect/` must never import `judge/`, so it cannot drive your pipeline |

**My recommendation is B, and the reason is that your CLI already has the
parameter-shaped hole** — it refuses at exactly the point a resolver would be
used, so wiring it is filling a gap that is already described rather than adding a
path. A is cheaper today and leaves the pipeline with two entry points of unequal
capability, which is how one of them quietly becomes the real one.

Either way the pipeline needs a resolver parameter where it currently takes inlined
text. **That is the change worth making regardless of where the module lives**,
because until a run reads through `RawStoreReader` the store side is covered by
unit tests and nothing resembling production — and this week found **13 raw
payloads missing with no tombstone** and **2 of 59 `thread_context` rows whose
`flattened_text_ref` resolves in neither store**. Inlined text cannot see either.

## 3 · The entity gate is guarded twice, and the exposure was elsewhere

You asked whether the digit-free exposure sits in `collect/triage/entity.py`. It
does not, and the checks are worth knowing because they are checks rather than
facts about the data:

```python
# entity.py:188 — applied to all three contribution sets, lines 230-232
def _admissible(surface): return len(cleaned) >= MIN_SURFACE_CHARS and cleaned not in FAMILY_WORDS
```

`MIN_SURFACE_CHARS` is **4** and `FAMILY_WORDS` has 26 entries — **`pro` is
rejected twice over**, for being three characters and for being a family word. And
`resolve` matches with boundary masks on both ends (`entity.py:281`), which is the
movie-post fix. Two independent guards, neither of which depends on the seated
surfaces happening to carry digits.

**The exposure was `scripts/labelling_pools.py:snippet_around`**, which took a
surface argument directly — bypassing `_admissible`, because its surfaces do not
come through `build_population` — and matched with a plain `.find()`. That is how
`pro` reached a stratum. Fixed to reuse `normalize_with_boundaries` rather than
re-derive the rule, since two implementations of one question is how the first fix
failed to reach the second caller.

**Pinned as a property, not as a fact about today's data.**
`tests/test_surface_matching_boundaries.py` uses only digit-free surfaces — `pro`,
`free`, `fusion`, `saba` — because all 105 seated surfaces carry a digit and a test
built from them would pass against a broken matcher. It covers both call sites,
asserts they agree, and asserts the real mentions still match, since a boundary
check that rejected those would trade a noisy stratum for an empty one and look
identical to the fix.
