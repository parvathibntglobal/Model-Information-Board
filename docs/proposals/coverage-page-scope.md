# The coverage page is for checks that ran, and 316 is not one of them

**One fix, not two. `316` is neither "not loaded" nor "loaded but unseated" —
it is a **roster reachability** figure, and the coverage page has no kind for
it. `missing-spelling` is not that kind and must not be widened into it.
Proposed: a seventh kind, `undeclared-model`.**

*Engineer 1 · 2026-08-20 · verified against a fresh local board*

---

## 1 · What the coverage page is actually for

Read off the live page rather than inferred. Every kind reports **three states**,
and the third is the whole design:

```
recognised: true   measured: false
headline:   "not measured — either every model is fully spelled,
             or nothing checked the spellings"
```

And the page's own summary, verbatim, on a board where nothing has run:

> *No coverage measurement has ever run. Nothing below is a finding about the
> board's coverage — it is the absence of any check, and it must not be read as
> completeness.*

**So the page answers one question per kind: did a check run, and what did it
find.** Every kind is a property of *something we did* — a load, a sieve, a
resolution attempt — keyed to the thing it was done to. The six recognised kinds
are all of that shape:

| kind | the check that produces it |
|---|---|
| `unsourced-field` | the seed load, FR-2 |
| `missing-spelling` | `check_spelling_coverage` over declared surfaces |
| `out-of-window` | the window recompute |
| `unknown-release-date` | the load, where no date could be established |
| `mention-resolves-to-route` | entity resolution, declining a router |
| `mention-unresolvable` | entity resolution, matching nothing |

## 2 · Which of the two readings is right: neither

**"Not loaded"** is closer, and it is still wrong in a way that matters. The 316
are polled, stored, in the registry and in the window. Nothing failed to load
them. What they lack is a **declaration in `contract/seed_models.yaml`**, which
is a different fact about a different file.

**"Loaded but unseated"** is a third question entirely — that is
`Selection.rejected` in `tracked.py`, and it has its own artifact and its own
grounds. A model can be declared and unseated, undeclared and seated by the
launch window, or neither.

So the three are orthogonal and a reader seeing "333 gaps" gets none of them:

```
340 in the registry
 └─  17  routes, which must never have a surface
 └─   7  declared in seed_models.yaml
 └─ 316  polled, in the window, and UNSEARCHABLE — no surface exists
```

**A reader seeing "316 coverage gaps" concludes "we checked 316 models and found
problems". Nothing checked anything.** It is a set difference against an
eleven-entry build fixture, which is why the function it comes from was renamed
in this change from `alias_coverage(models, known)` to
`undeclared_models(models, declared)`: both halves of the old signature described
something other than what they did, and the output was quoted as a coverage
figure on the strength of the name.

## 3 · Why `missing-spelling` must not absorb it

It is the tempting fix and it conflates two states with different remedies.

| | means | remedy |
|---|---|---|
| `missing-spelling` | a **declared** model missing one of the three renderings — spaced, hyphenated, concatenated | edit the existing entry; the surfaces are there and one form is absent |
| `undeclared-model` | **no surfaces at all**, so no alias row, so no query is ever issued | review the tracked-set artifact and declare it |

Widening the first to cover the second would produce a single number that mixes
*"`gpt-4.1-mini` has no concatenated form"* with *"nothing in the system has ever
been able to search for `qwen3.8-27b`"*, and the first is waste against a budget
while the second is a model the board cannot see. `check_spelling_coverage`'s own
ruling turns on that distinction: the floor counts **renderings** and is *"always
satisfiable without judgement"* precisely because the model is already declared.
An undeclared model cannot satisfy it at all, so failing it under the same kind
would report a gate failure where no gate applies.

## 4 · Proposed: a seventh kind

```python
"undeclared-model": (
    "a polled model with no declared surface, so no sweep can look for it",
    "either every model is declared, or nothing compared the feed to the "
    "declarations",
),
```

`subject` is the canonical id. `detail` names the comparison, because the figure
is meaningless without it — *"absent from contract/seed_models.yaml, 11
declarations"* — and the count moves when the declarations do, not when the world
does.

**Two things it inherits for free.** The page already reports an unrecognised
kind rather than filtering it, so the row is legible the day before this lands.
And it already distinguishes *not measured* from *measured zero*, which is the
distinction this kind most needs: **316 and "nobody has compared the feed to the
declarations" are the same output today**, and only one of them is a finding.

**What it needs that does not exist:** a writer. `coverage_gap` has none —
`load.py:coverage_gaps()` builds objects for four kinds and nothing inserts them,
and `undeclared_models` has no production caller either. So this proposal is one
line in `KNOWN_KINDS` and a writer that is the same missing writer four other
kinds are waiting on.

## 5 · What would revise it

- **A decision that `seed_models.yaml` is not the declaration source.** The
  tracked-set artifact is the reviewed list, and once its entries load into
  `model_alias` the comparison should be against **alias rows** rather than
  against a build fixture — at which point the kind stays and its `detail`
  changes.
- **`model_alias` having rows at all.** It holds 0 today, so "undeclared" and
  "unsearchable" coincide. They come apart the moment a reviewed surface lands
  without a corresponding seed entry.
