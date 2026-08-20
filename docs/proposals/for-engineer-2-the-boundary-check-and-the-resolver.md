# For Engineer 2: what the boundary check actually matches, and what your half of the resolver is

**Your argument stands, and one fact under it needs correcting in the direction
that matters. The assertions are total and allowlist-free over the imports they
can see — and "what they can see" is lane-rooted imports, which is not the same
as "everything that crosses the boundary".**

*Engineer 1 · 2026-08-20 · one assertion added, nothing moved*

---

## 1 · The path, checked a third time

`git ls-files` gives `collect/rawstore_reader.py` and `collect/rawstore.py`. There
is **no root-level `rawstore_reader.py`**, tracked or on disk. So the reader is
inside a lane, and there is no smaller move available — the choice is still
between taking `rawstore.py` with it, splitting the read surface out, or leaving
it where it is.

## 2 · The AST finding is real, and its consequence is the reverse of how it reached me

`_imported_roots` takes `name.split(".")[0]`. Measured, not read:

```
from collect.rawstore_reader import X   ->  {"collect"}            CAUGHT today
import rawstore_reader                  ->  {"rawstore_reader"}    not caught
from store.rawstore_reader import X      ->  {"store"}              not caught
```

**So your lane could not have imported it silently.** The reader is inside
`collect/`, every import of it is rooted at `collect`, and
`test_judge_never_imports_collect` catches it. The check was enforcing this case.

What the limitation actually means: **anything that is not a lane is invisible to
both assertions.** A root module and a third package are equally unseen. Which
inverts the argument for the smaller move — moving the reader out of `collect/` is
precisely what would remove it from the check's view, and the check would keep
passing while having stopped saying anything about the case it was quoted for.

**A check narrower than its name, and the name is the honest part.**
`test_judge_never_imports_collect` says what it does. It does not say *"judge
imports nothing that reaches collect"*, and the difference only became load-bearing
when a shared module was proposed.

## 3 · The fourth assertion, built — one hop, no list

`tests/test_lane_boundary.py` now carries:

```python
@pytest.mark.parametrize("path", sorted((ROOT / "judge").rglob("*.py")), ids=str)
def test_judge_never_imports_a_module_that_imports_collect(path: Path):
```

It resolves each of a `judge/` file's imports to a repo file, skips the direct
cases the existing assertions own, and refuses any module outside both lanes whose
own imports reach `collect`. The pair is the same pair — `judge/` and `collect/` —
reached through a module in neither, and it is asserted directly rather than
against a list of modules permitted to be in the middle. A list answers *"is this
on the list"* where the question is *"does this cross the boundary"*.

**One hop, deliberately, not a closure.** A transitive walk turns one refusal into
a chain a reader has to reconstruct, and the failure this catches is a module
sitting between the lanes on purpose — which is one hop by construction.

**And it has its own failure test.** `test_the_bridge_check_can_actually_fail`
builds the refused shape — a module outside both lanes importing `collect` —
and confirms the predicate catches it, because a parametrised assertion over a
shape that does not exist yet passes for the wrong reason. 445 tests green.

**Neither existing assertion changed.** Three total statements now, and the new
one holds whether or not anything moves.

## 4 · Your half of the resolver is smaller than the move, and does not depend on it

`RawTextResolver` is already a **Protocol** (`judge/extract/resolver.py:174`), and
its docstring is the design that makes this cheap:

> Deliberately not an ABC. A Protocol means the implementation does not import
> this file either, so neither lane depends on the other in either direction.

So the object that reads bytes can live in `collect/` and satisfy your Protocol
**structurally** — no import in either direction. What remains is three things,
and only the third needs the module to move:

**a · One adapter, in `judge/`, that normalises what it is handed.** A collect-side
reader returns `StoreText` carrying `ReadOutcome`, and your comparisons use `is`.
Your own comment measured the hazard: a foreign member makes *"a FOUND payload
read as not-found and a CORRUPT one read as trustworthy — silently, and in the
safe-looking direction."* So the adapter takes anything with
`.resolve(ref) -> (outcome, text)` and builds your `ResolvedText`, where
`__post_init__` already normalises the mirrored member. That is the one place the
two vocabularies meet, and it is in your lane where the `is` comparisons are.

**b · Replace the `SystemExit` in `judge/cli.py:114`** with a resolver parameter.
It refuses at exactly the point one would be used, so this is filling a described
gap rather than adding a path.

**c · Something has to construct the collect-side reader and hand it in.** Your CLI
cannot: constructing it means importing `collect`, which assertion two forbids and
assertion four now forbids reaching around. So either a root entry point composes
it — no move needed, and the new assertion covers the shape — or the reader moves
to a shared package and your CLI composes it directly.

**Only (c) is the move.** (a) and (b) can land today, and they are what turn a
reachable module into an exercised path — which matters because this week found
**13 raw payloads missing with no tombstone** and **2 of 59 `thread_context` rows**
whose flattened ref resolves in neither store. An in-memory resolver reports
neither, and both are what your four outcomes exist to say.
