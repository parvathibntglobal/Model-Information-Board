# Scoping the shared raw-store reader — where it lives, what moves, and the third assertion

**Option 1 agreed: one reader, both lanes reach the same bytes. This scopes it and
moves nothing.**

*Engineer 1 · 2026-08-20 · report before the rename · nothing taken*

---

## 1 · The reader cannot move alone, and that decides most of the rest

`collect/rawstore_reader.py:137` imports four names from the store:

```python
from collect.rawstore import PayloadCorrupt, PayloadMissing, PayloadTombstoned, RawStore
```

So a shared package containing only the reader would have to import back into
`collect/` — which makes the shared package a **wrapper over a lane**, and puts
the corridor in the worst possible direction: everything `collect` exports becomes
reachable from `judge` through one hop that no assertion sees. That option is out
before the naming question starts.

## 2 · Where it lives

**Nothing currently assumes `contract/` holds no Python** — no test globs it for
`.py`, no tooling asserts it. But two things make it the wrong home anyway, and
one of them is mechanical:

```toml
# pyproject.toml:73
[tool.setuptools.packages.find]
include = ["collect*", "judge*"]
```

**`contract/` is not a package and is not packaged.** Neither would a new
top-level directory be, until that list gains it — which is a one-line change and
a real trap either way: a package missing from `include` works in an editable
checkout and **vanishes from a built wheel**, so the failure appears at deploy and
not in the suite.

| home | cost | what it does to the thing |
|---|---|---|
| **`contract/`** | one line in `include`, plus `__init__.py` | `contract/` is YAML and SQL reviewed by two people — data with no call sites. Giving it importable Python means it has callers, and a directory with callers is refactored on the callers' schedule. Root CLAUDE.md's *"interface between two people"* stops describing it |
| **new top-level package** | one line in `include`, plus `__init__.py`, plus one new assertion (§4) | keeps `contract/` data-only and names the new thing for what it is: shared *code*, owned by neither lane. My lean too |
| a module at root (`rawstore.py`) | no `include` change needed — top-level modules need `py-modules`, which is not configured, so **this also needs packaging work** | same import properties, none of the social ones. Nothing about a file at root says two people depend on it |

**Recommend a new top-level package.** `store/` is the obvious name; `rawstore/`
collides confusingly with the module it contains.

## 3 · What moves, and the blast radius of each shape

Measured, not estimated:

```
importers of collect.rawstore          26 files   (9 collect, 5 scripts, 12 tests)
importers of collect.rawstore_reader    3 files   (collect/assemble/issue.py, itself, its test)
                                                  + 1 PROSE mention in judge/extract/resolver.py
sizes                                  rawstore.py 451 lines · rawstore_reader.py 273
```

**A · move both files whole.** Shared surface is 724 lines *including the write
path* — `put`, `evict`, tombstone-writing. Blast radius **29 files**. And it hands
`judge/` a byte-writing API: the lane test's table assertions catch a write to
`document`, and nothing would catch `RawStore.put` into the flattened namespace.

**B · split the read surface out, and leave a re-export behind.** Shared gets
`Namespace`, `RAW`/`FLATTENED`, `build_ref`/`parse_ref`, the three payload
exceptions, the byte-reading half of `RawStore`, and `RawStoreReader`. `collect/`
keeps `put`, `evict`, tombstoning, `EvictionRefused`, `TombstoneRefused` — and
`collect/rawstore.py` **stays, re-exporting the shared names**, so:

```
blast radius:  3 files, not 29   (the 26 collect.rawstore importers never move)
shared surface: read-only by construction — judge cannot write bytes because the
                write half is not there
```

**Recommend B.** It costs a real split of a 451-line module, and it buys a shared
surface as narrow as the assertion guarding it, which is the property being asked
for. A is cheaper today and makes the shared package the widest thing in the repo.

**One caution about the re-export**, since this project has been bitten by it: a
re-export makes `collect.rawstore` an import chain rather than a definition, and
*an import chain is no evidence of a call path* (habit 10). The equivalence to
assert is that `collect.rawstore.RawStore is store.rawstore.RawStore` — one class,
not two that pass the same tests.

## 4 · The third assertion, narrow rather than permissive

The corridor risk is not that a lane imports the shared package — that is the
point of it. It is that **lane-specific things get passed through it**. So the
assertion goes on the package, not on the lanes:

```python
@pytest.mark.parametrize("path", sorted((ROOT / "store").rglob("*.py")), ids=str)
def test_the_shared_store_imports_neither_lane(path: Path):
    """A shared surface that can reach a lane is a corridor between them."""
    reached = {"collect", "judge"} & _imported_roots(path)
    assert not reached, f"{path} imports {sorted(reached)}"
```

**Three total statements, none weakened.** `test_collect_never_imports_judge` and
`test_judge_never_imports_collect` glob `collect/` and `judge/`; a new top-level
package is in neither glob, so both keep their current meaning and their empty
allowlists. Modelled on `test_registry_never_imports_harvest` — a specific pair,
asserted directly, over one directory.

**And deliberately not a second assertion listing which symbols a lane may
import.** That is an allowlist wearing different clothes, and it grows one
reasonable case at a time — the exact failure the exception was rejected to avoid.
The structural version is enough: a package that can reach neither lane can only
hold things that depend on neither, so nothing lane-specific can be smuggled
through it.

## 5 · A fourth thing the move buys, and it is a live hazard

`judge/extract/resolver.py:92` documents a duplication that exists **only** because
of the boundary:

> `collect/rawstore_reader.py` defines `ReadOutcome` mirroring this, deliberately,
> because neither lane may import the other. StrEnum members of DIFFERENT classes
> compare equal by value and are never identical:
>
>     ReadOutcome.MISSING == Outcome.MISSING   -> True
>     ReadOutcome.MISSING is Outcome.MISSING   -> False
>
> Every comparison below and in `store_is_untrustworthy` uses `is`, so a foreign
> member would make a FOUND payload read as not-found and a CORRUPT one read as
> **trustworthy** — silently, and in the safe-looking direction. Measured, not
> supposed.

One shared enum deletes that, and the `__post_init__` normalisation written to
survive it. Worth counting alongside the extraction path, because it is a
correctness hazard rather than a convenience.

## 6 · What this unblocks, and one thing it does not

It unblocks the resolver wiring — the pipeline takes text inlined today, and
`judge/cli.py` refuses rather than reading a `flattened_text_ref`. Two facts from
this week say why that matters: **13 raw payloads are missing with no tombstone**,
and **2 of 59 `thread_context` rows** have a flattened ref that resolves in
neither store. An in-memory resolver cannot see either, and both are exactly what
`RawStoreReader`'s outcome vocabulary exists to report.

It does not, by itself, give the pipeline a resolver parameter. That is a separate
change in `judge/`, and it is the one that turns a reachable module into an
exercised path.
