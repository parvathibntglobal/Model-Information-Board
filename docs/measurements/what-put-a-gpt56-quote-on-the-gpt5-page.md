# What put a GPT-5.6 quote on the GPT-5 page

**I passed the wrong column. `build_population` documents its first argument as
`canonical_id`; I gave it `model_version.id`.**

```python
# collect/triage/entity.py
def build_population(models: Sequence[tuple[str, str | None]], declared=()):
    """...
    models: (canonical_id, display_name) from `model_version`.
    """

# what my rollup passed
conn.execute("SELECT mv.id, ma.surface FROM model_version mv "
             "LEFT JOIN model_alias ma ON ma.model_version_id = mv.id")
```

*Engineer 1 · 2026-08-21 · reads only*

---

## The proof, and it is not the extractor

The population my rollup handed to `RegistrySurfaceResolver`:

```
surfaces total                        1,342
surfaces containing a gpt-5.6 form        0      <- none existed
surfaces normalising to `gpt5`            3      'gpt 5', 'gpt-5', 'gpt5'
surfaces derived from an mv_ id            0      the guards threw them away

resolve("GPT-5.6 Sol Ultra") in that population
    -> ('gpt 5', 'gpt-5', 'gpt5')    ONE owner: openai/gpt-5
```

So the chain, end to end:

1. **the extractor was right.** It reported `surface: "GPT-5.6 Luna"` faithfully.
   Nothing about the quote or its attribution to a *surface* is wrong.
2. **the resolver was right given its input.** One owner, no ambiguity, no prefix
   continuation to catch — because the better candidate, `openai/gpt-5.6-luna`,
   **was not in the population at all.**
3. **the population was wrong, and I built it.** Feeding `mv.id` where
   `canonical_id` belongs meant `build_population` derived from strings like
   `mv_3ada7776822f837f`, which its own guards correctly discarded. The only real
   surfaces left were the 105 curated `model_alias` rows — and `gpt-5` is one of
   them while `gpt-5.6-sol` is not.

**So it is neither the substring defect nor an extractor problem.** It is one
wrong column in a query I wrote, and it produced a confident, single-owner,
plausible answer — which is why nothing downstream could see it.

> The substring defect is real and separately measured, and it did **not** cause
> this. Under the production population `GPT-5.6 Sol Ultra` resolves to
> `openai/gpt-5.6-sol` and the guard does not fire. I attributed this to the
> substring defect and that was wrong: two mechanisms that produce the same
> wrong-model symptom, and I picked the one I had just been looking at.

**The six deleted claims were therefore correct evidence**, removed for a defect
in my measurement of them. Repair is a rollup through
`RegistrySurfaceResolver.from_connection`.

---

## `_local_part` and `_seed_ids` do not exist

Searched the whole tree, `.py` only, excluding the venv:

```
_local_part   0 occurrences   (one TEST is named `test_local_part`)
_seed_ids     0 occurrences
```

**So there is nothing to fix at two sites, and nothing to say about whether a
correction was reverted, never merged, or made elsewhere — there is no symbol by
that name to have been corrected.** If `_seed_ids` is real under another name,
naming it gets a straight answer; I could not find it from the description.

**And `entity.py` has no local-part logic at all**, so no version-truncating
derivation runs at resolution time. `RegistrySurfaceResolver` calls `normalize`
and `entity.resolve`; neither touches a canonical id's vendor prefix. The alias
table and the resolver do **not** share a truncation, because there is no
truncation.

### But there ARE two implementations, and that is the drift shape

Not `_local_part`, and not at resolution time — but the finding you were looking
for exists one file over:

```python
# collect/registry/aliases.py:97   a FUNCTION, 2 call sites (:114, :210)
def local_part(canonical_id: str) -> str:
    return canonical_id.split("/")[-1]

# collect/registry/propose.py:302  a LOCAL VARIABLE, same idea, different split
local_part = canonical_id.split("/", 1)[-1]
```

**They disagree on any id with two or more slashes:**

```
'a/b/c'   aliases.local_part -> 'c'        propose -> 'b/c'
```

**Live instances: 0.** `SELECT count(*) FROM model_version WHERE canonical_id
LIKE '%/%/%'` returns **0**, so every id in the registry today has exactly one
slash and the two agree on all 342.

**Not unified, deliberately.** Picking a winner requires knowing which is right
for a three-part id, and no such id exists to test against — `openai/gpt-5` is
unambiguous, `provider/org/model` is hypothetical, and "strip the vendor prefix"
argues for `org/model` while the function's own docstring argues for `model`.
Choosing now would be inventing a convention the registry has not supplied, which
is the same refusal `propose.py` already records about `mistral large 3`.

**Recorded as latent duplication with zero live divergence**, which is the honest
state: a second copy is a hazard whether or not it currently disagrees, and the
day a three-part id arrives the two will silently differ. The cheap guard is a
test asserting they agree, not a refactor that picks a semantics.
