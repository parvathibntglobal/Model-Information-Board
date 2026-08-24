# I starved the population, and every resolution figure this week was low

**The largest error I have made in this project. `RegistrySurfaceResolver` has a
`from_connection` that builds the population from `canonical_id` and
`display_name`. I never used it. I hand-built a population from a LEFT JOIN on
`model_alias`, and 301 models with no curated alias row contributed no surface at
all.**

```
                              my query   production (from_connection)
surfaces in the population       1,342         1,224
owning models                      342           321
claims resolving, of 176             9            25
```

Fewer surfaces, better ones — derived per model rather than read from a sparse
curated table.

*Engineer 1 · 2026-08-21 · reads, plus one rolled-back write*

---

## 1 · What was wrong

```python
# what I did, in every measurement this week
rows = conn.execute("SELECT mv.id, ma.surface FROM model_version mv "
                    "LEFT JOIN model_alias ma ON ma.model_version_id = mv.id")
pop  = build_population([(r[0], r[1]) for r in rows])

# collect/surface_resolver.py, which existed the whole time
rows = conn.execute("SELECT canonical_id, display_name FROM model_version")
pop  = build_population([(r[0], r[1]) for r in rows])
```

`build_population` **derives** surfaces from a canonical id and a display name.
Feeding it `ma.surface` means feeding it `None` for every model nobody curated —
so 301 models were absent from the population, and the resolver I handed to the
pipeline could not see them.

**`model_alias` is not the resolution input.** It holds curated surfaces for the
seated tracked set. Resolution derives from the registry row.

### So the 301 ruling is yours, and I have taken it

**All 342 models are resolvable. 301 lack *curated* surfaces, which is a
different statement and not a coverage gap.** This is the 55-to-77 ruling working
exactly as written — the sweep covers a few, the registry resolves everything —
rather than contradicting it. Recorded as a banner on all four documents where I
claimed otherwise.

---

## 2 · What actually resolves, and the models I called fictional

```
Qwen 3.8 27B                            -> qwen/qwen3.8-27b            (11 claims)
GPT-5.6 Sol Ultra                       -> openai/gpt-5.6-sol
Codex Desktop running GPT-5.6 Sol Ultra -> openai/gpt-5.6-sol
GPT-5.6 Sol Pro                         -> openai/gpt-5.6-sol-pro
GPT-5.6 Luna                            -> openai/gpt-5.6-luna
Claude Haiku 4.5                        -> anthropic/claude-haiku-4.5
Opus 4.6                                -> anthropic/claude-opus-4.6
Claude Fable 5, Opus 5, or Sonnet 5     -> anthropic/claude-fable-5
Gemini 3.7 Flash                        -> google/gemini-3.7-flash
Claude Sonnet 4.5                       -> anthropic/claude-sonnet-4.5
```

**Every model I described as "fixture-world", "synthetic" or "never listed
upstream" is a real registry row.** `qwen/qwen3.8-27b` alone accounts for 11 of
the claims I filed under *"a model that does not exist upstream — nothing to
fix"*.

### And it means the six deleted claims were correct

`GPT-5.6 Sol Ultra` resolves to **`openai/gpt-5.6-sol`**. The
`openai/gpt-5` attribution that put *"I'm now generating my summaries using
GPT-5.6 Luna"* on the GPT-5 page was **produced by my starved population**, not by
the resolver. The rollup passed a hand-built resolver instead of
`from_connection`.

So:

- the mis-attribution was real and visible on the page — that part stands;
- **its cause was my harness, not the production resolver**;
- and the six claims I deleted would have resolved correctly. They were real
  evidence, removed for a defect in the measurement of them.

Re-running the rollup through `from_connection` is the repair. It was attempted
and died on `httpx.RemoteProtocolError` mid-batch; the transaction rolled back
whole, so the database is unchanged at **6 claims / 4 cells / 3 models**. Not
retried in this pass.

---

## 3 · The guard still earns its place, and `Mistral Large 3` is why

Against the **production** population the guard fires twice, and both are correct:

```
GPT-5.6           -> REFUSED   no `gpt-5.6` row exists; the -sol/-luna/-sol-pro
                               variants do. Which one did the writer mean?
Mistral Large 3   -> REFUSED   see below
```

### `Mistral Large 3` inverts the premise it was raised under

The claim was that longest-match-first *would have ranked `mistral-large-3`
correctly* and that something truncated it first. Measured:

```
mistral models in the registry:
  mistralai/mistral-large · mistral-large-2407 · mistral-large-2512
  mistralai/mistral-large-3   DOES NOT EXIST

"Mistral Large 3" hits:  ('mistral large', 'mistral-large', 'mistrallarge')
longest hit owner:       mistralai/mistral-large
```

**There is no `mistral-large-3` row to rank.** Before the guard, `Mistral Large 3`
resolved to `mistralai/mistral-large` — a different, older model. After the
guard it is refused and counted.

**So the guard fixes this case rather than breaking it**, and there is no
"fix breaking what it was built to fix" line to write, because the break did not
happen. `propose.py` already documents why no `mistral large 3` surface is
derived: `large` is not a family word, so deriving the vendor-dropped form would
be inventing tier vocabulary. That is a deliberate refusal, recorded, and the
guard is consistent with it.

### `local_part` does not truncate a version

```python
def local_part(canonical_id: str) -> str:
    """`anthropic/claude-opus-5` → `claude-opus-5`."""
    return canonical_id.split("/")[-1]
```

It strips the **vendor prefix** and nothing else. Two call sites, both in
`collect/registry/aliases.py`:

```
:114  classify_specificity - snapshot detection, compares against the local part
:210  alias_rows           - seeds the surface list with canonical id + local part
```

**Blast radius: seeding and specificity classification only. Nothing reads it at
resolution time** — `RegistrySurfaceResolver` calls `normalize` and
`entity.resolve`, never `local_part`. There is no `_local_part`.

---

## 4 · Not done, and why

**`PIPELINE_VERSION` is not bumped and nothing is re-seeded.** Both rest on a
`local_part` truncation that does not exist, and on a `mistral-large-3` row that
does not exist. Bumping a version stamp and re-seeding are hard to reverse and
would be done here on a premise the code contradicts. I could not identify what
the "32" refers to either — the figures in play are 342 models, 41 curated, 176
claims, 6 stored, 4 cells.

**Say which 32 and what should be re-seeded and I will do it.** If the intent is
"re-derive surfaces for every model now that resolution is understood", that is a
real and useful job — and it is a *proposer run plus review*, not a re-seed, and
it does not need a version bump because resolution is derived at read time rather
than stored.

## 5 · The eight, and why five did move

The premise was that none moved. Five did, under the starved population:

```
GPT-5.6 Sol Ultra / Sol Pro / Luna / GPT-5.6 / "Codex Desktop running…"
    openai/gpt-5  ->  REFUSED     5 changed
Claude Haiku 4.5, Opus 4.6              unchanged, and correct
"Claude Fable 5, Opus 5, or Sonnet 5"   unchanged, and still wrong
```

Under the **production** population the answer changes again: four of those five
resolve correctly to the `gpt-5.6-*` rows and only bare `GPT-5.6` is refused. So
the guard's apparent 5-of-8 effect was mostly my starved population being
corrected by a second mechanism, which is exactly the kind of agreement that
should have made me check the first one.

## 6 · Unchanged and unscoped: the raw store

3 of 32 contexts unresolvable, and Engineer 2 still cannot run against staging
directly. Nothing this week touched it. Agreed as the thing to scope properly
after the presentation, and it is the only item on this list that has not moved
in either direction.

## 7 · PR #137

**`CLEAN`, `MERGEABLE`, `test pass`.** Reported in full last turn and unchanged:
the conflict was one add/add on `scripts/labelling_pools.py`, resolved to the
corrected side; the CI failure was the **Lint** step — `ruff check .`, `I001`
import order and `F841` a dead `haystack` left over from the boundary fix — both
in the change, both fixed, branch lint-clean.
