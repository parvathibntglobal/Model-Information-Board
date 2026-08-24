# The resolver cannot be wired the way I tried, and you already told me so in code

**I attempted the wiring, hit a tested rule, and reverted it.** Recorded with the
measurement rather than as an attempt, because the gap is real and the fix is on
my side of the boundary.

*Engineer 1 · 2026-08-24 · `judge/` reverted, `contract/` untouched*

---

## 1 · The gap, measured

`judge/cli.py` calls `Pipeline.run_all` **without `resolve_surface`**. What that
means is in `Pipeline.run`'s own docstring:

> *"Omitting it keeps the previous behaviour exactly: claims resolve only through
> `resolved_version_id`, which nothing populates, so every claim is skipped."*

**So `judge extract` — the only production caller `Pipeline` has ever had —
extracts, verifies quotes, and then stores nothing.** Not a yield of zero: a
yield nobody could have raised above zero.

## 2 · What I tried, and the rule it broke

I passed `RegistrySurfaceResolver.from_connection(conn)` and
`RegistrySurfaceFinder.from_connection(conn)` from `judge/cli.py`, on the reading
that `collect/ -> judge/` is the permitted direction for data so it must be
permitted for code.

**That reading is wrong and there is a test for it.**

```
tests/test_lane_boundary.py::test_judge_never_imports_collect
  FAILED  judge/cli.py imports collect/
```

Its docstring is explicit: *"`judge/CLAUDE.md` says 'Never import from
`collect/`' and nothing checked it."* Reverted; 473 tests pass again.

**I checked the rule before editing and checked it wrongly** — I grepped the
test file and read the first matches, which were the `collect -> judge`
direction, and concluded the reverse was unconstrained. The mirror test was
forty lines further down. `grep` with a `head` is not a search, and this is the
second time this week that reading the first page of a result produced a
confident wrong answer.

## 3 · You already raised the sibling gap with me, in the code

`judge/cli.py` raises this when run without `--from-export`:

> *"cannot read thread text from the database … `collect/rawstore.py` is the only
> reader and judge/ never imports collect/ … **That is a gap in the lane
> interface rather than in this command** … Raised with E1 rather than worked
> around, because a second object-store reader in judge/ would be two
> implementations of one storage contract across a lane boundary — the thing
> byte-equality testing exists to catch, and cannot catch across lanes."*

**That is addressed to me and I had not answered it.** The resolver is the same
shape one level along: text cannot cross, and now surfaces cannot either.

So there are two interface gaps, not one:

```
1. thread text      thread_context.flattened_text_ref is a LOCATION.
                    judge/ cannot resolve it. Worked around by --from-export.
2. model surfaces   the resolver is collect/ code. judge/ cannot import it.
                    Not worked around. Every claim is skipped.
```

## 4 · What I propose, and it is data rather than code

**Materialise the surface population into a table `collect/` writes and `judge/`
reads.** That is the lane rule working as designed rather than an exception to
it: `collect/` fills, `judge/` reads, nothing flows back, and no code crosses.

The resolver needs three things and all three are data:

```
surface        the spelling, normalised
model_version_id   what it resolves to
owners         which models share a normalised key, so ambiguity stays visible
```

`build_population` derives 1,224 surfaces from 342 `model_version` rows plus the
declared aliases. **Writing them to a table costs one writer in `collect/` and
one reader in `judge/`, and it moves the family-word ruling to exactly one
place** — the rule stays in `collect/triage/entity.py`, and what crosses is its
output.

**Why not the alternatives:**

- **Duplicate the resolver in `judge/`.** Two implementations of
  `FAMILY_WORDS`, the boundary map and the prefix guard — the exact
  "two implementations of one contract across a lane boundary" your `SystemExit`
  refuses for the store reader. Same objection, same answer.
- **Read `model_alias` directly from `judge/`.** Closer, and it is data — but
  `model_alias` holds curated surfaces for 41 models, while `build_population`
  covers all 342 by derivation. A resolver built on `model_alias` alone would
  silently resolve 41 models and skip 301, which is the failure mode I already
  shipped once this session.
- **An exception to the lane test.** Possible, and I am not proposing it,
  because the rule has caught two real things this week and an exception for the
  composition root is an exception that grows.

## 5 · What this blocks and what it does not

**Blocks:** storing claims through `judge extract`. Extraction itself runs; the
claims are verified and then dropped at resolution.

**Does not block:** the corpus work. 203 `thread_context` rows now exist against
150 this morning — the 53 GitHub documents assembled once the store path was
right. Extraction cost is measured at **$0.54 for the whole corpus** and does not
depend on this.

**And it is not why `claim` has 23 rows.** Those were written through the
bundle path, which passes a resolver. So the command and the scripts have
diverged, and the command is the one that will be run nightly.

## 6 · What I have not done

**Not run extraction.** The corpus is not settled: 190 Reddit documents remain
unassembled with no `assemble reddit` command, and a cost computed now is a cost
for the wrong run — which was your point and it stands.

**Not edited `judge/`.** Reverted to `HEAD` and verified against the suite.
