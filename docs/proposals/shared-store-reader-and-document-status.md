# Two queued items: where the shared reader lives, and what `document.status` defaults to

**Both are shared-surface changes, so both are proposed rather than taken. One
premise in each turned out to be wrong, and in both cases the correction makes the
change cheaper.**

*Engineer 1 · 2026-08-20 · `contract/` and the lane boundary · nothing taken*

---

## 1 · `RawStoreReader` sits where its only consumer cannot import it

Confirmed, mechanism and all. `tests/test_lane_boundary.py:259`:

```python
@pytest.mark.parametrize("path", sorted((ROOT / "judge").rglob("*.py")), ids=str)
def test_judge_never_imports_collect(path: Path):
    assert "collect" not in _imported_roots(path), f"{path} imports collect/"
```

**No exception list, by design** — its own docstring records that
`judge/store/claims.py` duplicates connection handling rather than reuse
`collect/db.py`, and calls voluntary compliance with an unenforced rule *"exactly
the state that decays quietly"*. The rule was added on 2026-08-18 precisely
because it had been unenforced.

So `collect/rawstore_reader.py` is unreachable from the lane that defines the
interface it implements — `judge/extract/resolver.py` holds the `resolve(ref) ->
ResolvedText` Protocol, and `collect/` wrote the store side of it.

### What each option costs

| option | cost | what it does to the invariant |
|---|---|---|
| **add to an exception list** | one line | **weakens the check to a list.** The next exception is argued against a precedent rather than against the rule, and the rule's value is that it has none |
| **top-level module** (`rawstore_reader.py` at root) | move the file, update ~4 importers, one line in the lane test's path globs | keeps the invariant absolute. Imports read `import rawstore_reader`, which says nothing about ownership |
| **a third package** (`store/`, sibling to `contract/`) | a directory, an `__init__`, the same importer updates | keeps the invariant absolute **and names the thing**: a shared surface, owned by neither lane, changed on purpose like `contract/` |

**My recommendation is the third**, and the reason is `contract/`'s own precedent
rather than tidiness. `contract/` works because it is *visibly* shared — CLAUDE.md
says it should change perhaps five times in eight weeks, each time on purpose —
and that discipline attaches to a directory, not to a file sitting in someone's
lane. A top-level module has the same import properties and none of the social
ones: nothing about `rawstore_reader.py` at root says "changing this affects two
people".

**What it is not:** an exception list. The asymmetry audit found three unenforced
invariants and enforcing them was the fix; the first exception would start the
same decay from the other end.

### The larger cost is not the move

**She has been running `judge extract` against an in-memory resolver, so the real
`resolve` path has never executed.** That is the thing to fix, and the move is
what unblocks it. Worth stating plainly: until a run reads text through
`RawStoreReader`, the store side is covered by its own unit tests and by nothing
that resembles production. Two facts from this week say why that matters —
**13 raw payloads are missing with no tombstone**, and 2 of 59 `thread_context`
rows have a `flattened_text_ref` that resolves in neither store. An in-memory
resolver cannot see either.

## 2 · `document.status` defaults to `'kept'`, and the coupling is not the one expected

**The defect is real.** `contract/tables.sql:106`:

```sql
status  text NOT NULL DEFAULT 'kept',
CONSTRAINT document_status_ck CHECK (status IN ('kept','filtered','rejected','tombstoned'))
```

Only `collect/assemble/article.py:184` passes a value, and it passes `'kept'`. So
the 27 GitHub documents took the default — and `triage_verdict` is NULL on all 27,
meaning **the column asserts a triage verdict on rows triage has never seen.**

**Three corrections to the premise, all of which make this easier:**

1. **`pending` is not in the CHECK.** The vocabulary is
   `kept | filtered | rejected | tombstoned`. Adding `pending` is a migration,
   not a default change.
2. **Nothing reads `status != 'kept'`.** Zero matches across `.py`, `.yaml` and
   `.sql`. Nothing reads `status = 'kept'` either — **the column has no reader in
   either lane today.**
3. **Her placeholder check does not key on `!= 'kept'`.**
   `judge/extract/placeholder.py:70` is `status == PLACEHOLDER_STATUS`, and
   `PLACEHOLDER_STATUS` is **`'removed'`**. So changing the default cannot flip
   any row into that branch, for any new value other than `'removed'` itself.

**So the change does not have to land with her column — but it wants the same
migration.** `is_placeholder_status` is written as the strong test with the
body-text match as the fallback, *"so the upgrade is deleting a branch rather than
rewriting a rule"*, and it cannot become the strong test until the CHECK permits
`'removed'`. Two values want adding to one constraint:

```sql
-- one migration, two callers, and neither can act without it
ALTER TABLE document DROP CONSTRAINT document_status_ck;
ALTER TABLE document ADD  CONSTRAINT document_status_ck
  CHECK (status IN ('pending','kept','filtered','rejected','tombstoned','removed'));
ALTER TABLE document ALTER COLUMN status SET DEFAULT 'pending';
```

**What `pending` must mean, written down before anything sets it:** *triage has not
run on this row.* Not "triage ran and was unsure" — that is what `filtered` and
`rejected` are for. So the honest transition is `pending → {kept, filtered,
rejected}` written by triage, and a row that stays `pending` is a row the pipeline
has not reached, which is a coverage fact rather than a verdict.

**And the backfill is the part to get right.** The 57 existing rows are all
`'kept'` and none has been triaged, so leaving them is asserting the same thing
the default asserted. `UPDATE document SET status = 'pending' WHERE triage_verdict
IS NULL` in the same migration — which today is all 57, and which is a statement a
reader can check rather than a value they inherit.

**Yours to say:** whether `'removed'` goes in the same constraint change (I think
yes — one migration is cheaper than two and your consumer is already written), and
whether anything in the answer path is about to start reading `status` in a way
that a `pending` majority would surprise.
