# `entity.py:_local_part` — there is nothing there, and why that took five turns

**`entity.py` contains no `_local_part`, no `local_part`, and no `split()` of any
kind. Its resolution path is `normalize` (a regex substitution) and
`haystack.find(needle)`. Nothing truncates anything.**

**And nothing in `collect/` splits on a hyphen** except
`triage/gates.py:244` — `doc.lang.split("-", 1)[0]`, turning `en-GB` into `en`
for the language gate. Correct and unrelated.

The three real local-part derivations already split on `/`:

```
collect/registry/aliases.py:97    canonical_id.split("/")[-1]
collect/registry/propose.py:242   canonical_id.split("/", 1)[-1]
collect/registry/propose.py:302   canonical_id.split("/", 1)[-1]
```

**So "split on `/` rather than `-`" is already the state of the code, in all three
places, and none of them runs at match time.** There is no fix to make.

*Engineer 1 · 2026-08-21 · reads only, nothing changed*

---

## The two cases that must not regress — measured, and both already refused

Nothing changed, so nothing regressed. Recording what they do so the question is
answered rather than deferred:

```
~anthropic/claude-opus-latest    mech: ['claude opus latest', 'claude-opus-latest',
                                       'claudeopuslatest']       resolves -> None
~anthropic/claude-haiku-latest   mech: ['anthropic claude haiku latest', …]
                                                                 resolves -> None
openrouter/free                  mech: ['free', 'free models router', …]
                                 rule: NONE (guard 5 refuses routed ids)
                                                                 resolves -> None
openrouter/fusion                mech: ['fusion']                resolves -> None
openrouter/auto-beta             mech: ['auto beta', 'auto-beta', …]
                                                                 resolves -> None
```

**Both shapes derive surfaces from the local part and both resolve to `None`
today**, which is right for opposite reasons:

- a `~vendor/model-latest` pointer is a **moving target**. Attributing a claim to
  `claude-opus-latest` attributes it to whatever ships next, which is worse than
  refusing;
- an `openrouter/*` router is **not a model**, and its derived surfaces are the
  dangerous kind — `free`, `fusion` — single common words. `fusion` inside
  *"confusion"* is a defect this project has already recorded. `rule_variants`
  returns nothing for routed ids by design (guard 5), and resolution refuses
  them.

So the reason the current form exists holds, and it holds without a change.

## The uncounted population is zero

```
readable thread contexts scanned          120
containing "mistral" at all                 5
containing any `mistral[ -]*large[ -]*3`    0
```

**No stored document writes `mistral large 3` in any spacing.** So the population
of documents that would newly resolve under the proposed fix is **zero**, and it
would be zero even if the fix existed — there is no `mistralai/mistral-large-3`
row for anything to resolve *to*. The registry holds `mistral-large`,
`mistral-large-2407`, `mistral-large-2512`.

The concern was worth raising and the answer is a clean negative: the case that
motivated it does not occur in this corpus.

## No version bump, so `cell_current` stays a recorded hazard

Nothing changed, `PIPELINE_VERSION` is untouched at `collect-0.1.0`, and the
stale-cell analysis stays what it was: real, inert while every cell is
`insufficient` (`cell_current` returns 0 rows), and fixed by reconciling `cell`
against `claim` in `rebuild_all` rather than by filtering the view.
`docs/proposals/for-engineer-2-stale-cells-not-a-view-filter.md`.

---

## The five-way split, recorded where the defect was described

Five things were named across these turns. **One was real, and the shape of the
four misses is the useful part: every one placed a truncation at MATCH time, and
there is no truncation at match time.**

| named | status |
|---|---|
| `cell_current` has no version filter | **REAL.** A view in `contract/tables.sql:648`, read by `judge/ask/answer.py`. The hazard is real, its shape is a stale row rather than a version collision, and it is inert while every cell is `insufficient` |
| `entity.py:_local_part` truncates at match time | **absent.** `entity.py` has no `local_part` and **no `split()` of any kind** |
| `_seed_ids()` reads the tracked-set proposal | **absent.** Zero occurrences in the tree; zero in `git log --all -S` on any branch |
| `mistralai/mistral-large-3` | **absent.** The registry holds `mistral-large`, `-2407`, `-2512` |
| a vendor name that is also a family word excludes its own models | **false.** Measured below |

### The vendor / family-word mechanism, measured

The narrow statement offered was: *`mistral` is a family word, so `mistralai`'s
models are excluded from the population, and it is live.* Checked:

```python
def _admissible(surface: str) -> bool:
    cleaned = surface.strip().casefold()
    return len(cleaned) >= MIN_SURFACE_CHARS and cleaned not in FAMILY_WORDS
```

**Exact membership, not substring.** So:

```
'mistral'   in FAMILY_WORDS   True     the bare word is excluded, as intended
'mistralai' in FAMILY_WORDS   False    the vendor is not a family word
mistralai models in registry            18
...resolving from their canonical id    18   of 18
```

**No exclusion, on any model, by any vendor.** The rule removes one bare token —
which is its entire job, because `mistral` alone names a line rather than a
tier — and leaves `mistral large`, `mistral-large-2512` and the other 18
untouched. A vendor prefix would have to *be* a family word exactly, and none is.

**The true version of the concern is smaller and already open:** a document that
writes only *"Mistral"* resolves to nothing, exactly as *"Claude"* and *"Codex"*
do. That is the family-word ruling with Engineer 2, worth 26 of 133 unresolved
claims, and it is not vendor-specific.

### Both misses pointed the same way

The two premises about `_local_part` were that it runs at resolution time and
that fixing it at both call sites would fix resolution. **Both assumed the
truncation exists, and both were reached from where the name looked defined
rather than from where anything is called.** The generalisation offered — *infer
what a function does from its call sites, not its definition* — is right and
holds one step further back here: the definition did not exist either, so there
were no call sites to read. The check that settles it is `grep "def <name>"`,
which returns nothing, rather than `grep "<name>"`, which returns a substring
hit on `test_local_part`.

## Why this took five turns, and the answer is about my process

The framing offered was: *the inference was that `_local_part` running at both
sites meant both sites were wrong; the file showed one was fine; reading the
artifact settled what reading the code did not.*

**That is not what happened, and the real version is more useful.** The symbol
never existed at either site, and what settled it *was* reading the code — `grep`
plus `git log --all -S` across every branch. No artifact was involved.

What actually cost the turns:

**1. I answered "it does not exist" five times and re-derived it from scratch each
time, instead of asking for a `file:line` on the first.** Restating an absence
generates no new information. The second search could not tell me anything the
first had not, and the fifth was pure repetition. **The move I should have made at
turn one: ask for the anchor — a line number, a traceback, a failing assertion.**
That is the same standard I had already written down for what makes a fix land,
and I did not apply it to the question of whether there was anything to fix.

**2. A substring grep makes the symbol look present.** This is worth keeping:

```
$ grep -rn "_local_part" tests/
tests/test_registry_aliases.py:64:def test_local_part():
```

**`_local_part` is a substring of `test_local_part`, so a bare grep returns a
hit.** Anyone checking that way sees a match and concludes the symbol exists. The
check that distinguishes them is `grep -w` or grepping the *definition* —
`def _local_part` — which returns nothing.

**3. And scepticism was not a safe default either, which is why each one had to be
checked.** `cell_current` was raised the same way and is entirely real: a view in
`contract/tables.sql`, read by `judge/ask/answer.py`, with a genuine stale-row
hazard I would not have found otherwise. So "the named thing probably does not
exist" would have been wrong on that one and expensive.

**The transferable rule, and it is cheap:** verify a name by its *definition*
rather than by substring, and when a definition cannot be found, **ask for the
anchor before searching a second time.** Checking is cheap; re-checking is the
waste.
