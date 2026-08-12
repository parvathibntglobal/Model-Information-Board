# Phase 1 defect report — the collection lane

**Six defects in the registry write path, plus one packaging finding.**

*Engineer 1 · branch `phase1-collection-foundation` · fixes in commit `4bd322d`*

> Written for someone who was not in the room. Nothing here assumes you
> followed the session that produced it.

---

## The one sentence that explains all six

**All six defects existed because the write path had never been executed
against a database.**

The suite reported **139 passed, 9 skipped**, and had done since the code was
committed. The nine skipped tests were `tests/test_registry_load_db.py` — the
only tests covering the write path — and they skipped because no Postgres
existed on the development machine. **All six defects lived under exactly those
nine tests.**

The suite was green because the tests that would have caught the bugs were the
tests that could not run.

Once Postgres was stood up, those nine tests **passed unmodified**, so they
covered none of the six. Every fix below needed a new test.

**Current state: 247 passed, 0 skipped, on Python 3.11.9.**

---

## The six defects

### 1 · Alias ids were keyed on `release_date`

*`collect/ids.py`, `collect/registry/aliases.py`, `collect/registry/load.py`*

**What it was.** `model_alias_id()` folded `valid_from` — which is the model's
`release_date` — into the primary key. `_insert_alias` then inserted blind
against `ON CONFLICT (id) DO NOTHING`, never reading the table.

**What it would have caused.** Correcting any release date minted a fresh id
for every alias of that model. They all inserted successfully, the old rows
kept `valid_until = NULL`, and two live rows ended up claiming the same surface
over overlapping windows. A quote saying *"sonnet"* would then resolve to two
model versions with no rule for choosing between them. `find_collisions` could
not see it, because it only ever inspected the parsed YAML and never the table.

FR-4 exists to make old aliases keep resolving old quotes. This broke that
quietly, and only on the day someone fixed a date — which is exactly the kind
of routine correction nobody watches.

**What now catches it.** `_sync_alias` reads before it writes. For a given
`normalized` plus `model_version_id` it finds the live rows, sets `valid_until`
on any it supersedes, then appends. Setting `valid_until` is the only write
issued against an existing row, and it is the one write FR-4 permits, because
closing an interval does not rewrite what that row asserted about its own
window.

Ids are now keyed on a **content key**: everything the row asserts —
surface, variants, provider hint, family, specificity, confidence — and
deliberately *not* the window it asserts it over. A corrected date is therefore
a no-op, while a genuine change to what the alias claims mints a new id.

Six tests, including the acceptance case: load, change a release date, load
again, and `GROUP BY normalized, model_version_id HAVING count(*) > 1` over
live rows returns empty.

### 2 · The upsert reverted `provenance` and `in_window`

*`collect/registry/load.py`*

**What it was.** `updatable` was built as every column except `id` and
`canonical_id`, so `ON CONFLICT DO UPDATE` overwrote `provenance` with
`'seed'` on every single run.

**What it would have caused.** Week 5 replaces `contract/seed_models.yaml` with
OpenRouter polling writing into the same table. After that, **one stray
`registry load-seed` flips ten polled rows back to `provenance = 'seed'`**, and
`assert_no_fixtures` then refuses to boot production over models that are
perfectly real. The same mechanism forced `in_window` back to whatever the seed
load had computed.

**What now catches it.** A pre-flight query raises `ProvenanceDowngradeError`
before any write, naming every affected row rather than whichever one the loop
reached first. `in_window` is in a `_NEVER_UPDATED` tuple, excluded from both
the update set and the change report.

**The guard is directional**, and that matters: it refuses `polled → seed`
only. Promotion the other way must keep working, because the week 5 poller
takes ownership of exactly the ten rows the seed file already contains.

Twelve tests, including one that plants a sentinel price and asserts it
survives the refusal, proving nothing was written before the raise.

### 3 · `model_event` ids collapsed, and `occurred_at` was never set

*`collect/registry/load.py`*

**What it was.** The event id was `hash(model_version_id, type, detail)` where
`detail` was a constant string like `"google/gemini-2.5-flash: ['price_in']"` —
carrying no values and no timestamp. `occurred_at` was not in the INSERT column
list at all.

**What it would have caused.** **Every price change after the first was
silently discarded** by `ON CONFLICT (id) DO NOTHING`. `pricing_history`
recorded the move; `model_event` did not; and alerting reads events. FR-3's
acceptance criterion — *a price change is detected within 24h* — failed on its
own terms, for every model, from the second change onward.

**What now catches it.** Event ids are random. Folding the observed values in
would not have fixed it: a price going 1.00 to 2.00, and later 1.00 to 2.00
again, is the same tuple and still collapses. Only a timestamp separates them,
and an id built from a timestamp is a UUID with extra steps — it gives up the
re-run idempotency that determinism was for and buys nothing back.

The reasoning generalises. **A deterministic id encodes "this is the same
fact". An event is not a fact, it is an occurrence**, and two identical
transitions on different days are two occurrences. So idempotency moved to the
*condition* that decides whether an occurrence happened, which compares the
stored `model_version` row against the incoming one and is directly testable.

`occurred_at` is now a real timestamp rather than a restatement of when the
code ran: for a price change it is the `pricing_history.observed_at` that
revealed it, so the event and its audit row agree; for `new-model` it is the
release date.

Eleven tests. Four price moves produce four events with four distinct ids.

#### 3a · A price that never moved was reported as a change

`_record_prices` decided whether a change had occurred by asking
`pricing_history`. A model whose history row was missing therefore reported a
change for a price that had never moved. Deleting `pricing_history` and
reloading used to raise ten price-change events. It now raises zero, while
still rebuilding all ten baseline rows.

Whether prices moved is a question about `model_version`, and `_changed_fields`
already answered it.

#### 3b · All-NULL `pricing_history` rows

A model with no prices — an open-weight model priced by the serving host rather
than the provider — accumulated one row of three NULLs per nightly run,
forever. Three NULLs assert nothing. Now skipped outright.

### 4 · `in_window` was hardcoded `true`

*`collect/registry/load.py`, new `collect/registry/window.py`*

**What it was.** `model_row()` wrote `"in_window": True` for every model, with
a comment deferring the real computation to week 5.

**What it would have caused.** The answer path filters on `in_window`, so every
out-of-window model stayed permanently visible and eligible for
recommendation. **Three of the ten seeded models** fall outside an 18-month
window as of 2026-08-12: `mistral-large-2411`, `deepseek-v3` and
`deepseek-r1` — the last by 23 days.

**What now catches it.** `window.py` computes it from `release_date` against a
boundary derived from `in_window_months` in `contract/registry.yaml`. Calendar
months, not 30-day approximations, clamped to the target month's length so 31
March minus one month is 28 February, or 29 in a leap year.

`as_of` is an explicit parameter rather than a call to `date.today()` inside
the function. **A test that reads the clock to check a boundary passes today
and fails in three months**, which is worse than no test. Every date in the
test file is pinned.

**Ownership is settled: the nightly `registry recompute-window` job owns the
column.** `in_window` is a function of `release_date` and *today*, so its
correct value changes on days when nothing is loaded at all. If both the loader
and the job wrote it, the value would depend on whichever ran last. The loader
supplies it on INSERT only, because the column is `NOT NULL` and a fresh row
needs a correct value immediately; it never writes it again.

Twenty tests. One of them recomputes at two different dates and watches
`deepseek-r1` cross the boundary, which demonstrates the job is not optional
rather than asserting that it is.

### 5 · `find_collisions` was time-blind

*`collect/registry/aliases.py`*

**What it was.** It grouped rows by `normalized` alone and raised on any
surface claimed by two models, ignoring `valid_from` and `valid_until`
entirely.

**What it would have caused.** FR-4 exists precisely for `-latest` aliases,
which legitimately point at one snapshot in March and a different one in June.
Those are disjoint windows and one unambiguous answer at any instant.
**The seed load would have failed the moment anyone added the alias the
requirement was written for.**

**What now catches it.** Two rows collide only when their half-open
`[valid_from, valid_until)` windows overlap. A NULL bound widens the window —
unknown start is open at the start, NULL `valid_until` is still current —
because an unknown bound should make the check raise rather than quietly permit
an ambiguity.

Half-open is the load-bearing part, and it is what makes defect 1's fix
possible: when one alias closes exactly as its replacement opens,
`a.valid_until == b.valid_from` and the two do not overlap. That handover is
the whole point of an append-only table, and it must not read as a collision.

Ten tests, including both acceptance cases and six parametrised interval rules
each asserted symmetrically.

### 6 · Alias expansion overran the query budget by 2.9x

*`collect/registry/aliases.py`, `collect/registry/policy.py`*

**What it was.** 44 alias rows, each mechanically expanded into spacing,
hyphenation and concatenation forms, giving 146 distinct search strings.

**What it would have caused.** **1752 queries per platform against a planned
600** — roughly 58 minutes per sweep on GitHub's 30 requests per minute rather
than the 20 the plan assumes. 516 of those queries were spent on
`provider/model` strings like `anthropicclaudeopus5` that no human types into a
Reddit post.

**What now catches it.** Search eligibility and attribution eligibility are
separate flags on the alias row. **Every alias stays attribution-eligible** —
an exact mention of `anthropic/claude-haiku-4-5-20251001` in a pasted config
must still resolve at snapshot specificity, and dropping that row would lose a
claim. Only hand-declared surfaces become queries.

Result: **54 strings, 648 queries, about 22 minutes**, with attribution keys
unchanged at 44 — asserted by comparing key sets under both policies.

Eleven rows lose search: ten provider-prefixed forms, plus
`claude-haiku-4-5-20251001`, which carries no provider prefix and would have
been missed by a naive "strip the prefix" rule.

**The honest number is 648, not 600.** The rule was not tuned to hit the plan's
figure. The plan assumed five variants per model; the YAML declares six for
four of the ten. If 600 exactly is wanted, the edit is to the seed file.

Moving breadth from code to a hand-written list would have left the guarantee
unchecked, so `check_spelling_coverage` now requires every model to declare a
spaced, a hyphenated and a concatenated form, failing the load otherwise.
Exactly one model currently fails: see contract sign-off item 10.

Sixteen tests, with the budget **pinned rather than bounded**. Widening the
alias list is legitimate; when someone does it, the test fails with the new
number instead of silently absorbing it.

---

## Also found, not fixed · `pyproject.toml` declares no package discovery

`pip install -e .` fails outright: setuptools refuses the flat layout with four
top-level directories and no discovery configuration. Nobody can install this
repository.

Not fixed here because `pyproject.toml` is outside the collection lane. It is
item 1 of `docs/contract-signoff-phase1.md`, with a warning attached: once
packaging works, `pip install -e .` **without** `[dev]` will silently drop
`ruff`, `mypy` and `pytest-asyncio`. The current generated-requirements
workaround cannot do that, so the fix introduces a new failure mode as it
removes an old one.

---

## Corrections made along the way

These are recorded because they say what standard the document was held to. A
review written without running the code got most of it right and some of it
wrong, and so did the engineer fixing it.

### To the review

| Claim | Outcome |
|---|---|
| Two findings, withdrawn by the reviewer before work began | Not investigated |
| `pyproject.toml` has a stray trailing comma in `testpaths` | **Retracted.** The file parses as TOML and `testpaths = ['tests']` is clean |
| `simhash>=2.1` is a C++ extension that will not build on Python 3.14 | **Wrong.** `simhash` 2.1.2 is pure Python: one `__init__.py`, no compiled extension anywhere in the package. The C++ one is `simhash-py`. The move to 3.11 was still right, for a different reason — `trafilatura` and `pydantic-core` do ship compiled extensions, and 3.11 is the declared floor |
| Defect 3 "collapses on the fourth move" | **Worse than stated.** It collapses on the **second**. Every price change after the first is discarded, for every model |
| Defect 6 costs "up to 2,640 queries" | **Measured 1752.** `query_variants` deduplicates, so most surfaces yielded three forms rather than five. Still 2.9x over budget |
| Defect 4 puts "two models out of window" | **Three.** `deepseek-r1` at 2025-01-20 is 23 days the wrong side of the boundary. Engineer 1's own earlier report also said two; the reviewer's three was right |
| "Refuse when the existing row carries `provenance = 'polled'`" | **Made directional.** An unconditional refusal would have blocked the migration it was written to protect: the week 5 poller takes ownership of exactly the ten rows the seed file contains, so it could never have written any of them. Now refuses `polled → seed` only |
| "Drop `valid_from` from the alias id input" | **Insufficient alone.** That leaves the id as `(normalized, model_version_id)`, which is not unique across successive rows — a genuine alias change would collide on the primary key and be discarded by `ON CONFLICT DO NOTHING`. Replaced with a content key: everything the row asserts, excluding the window |
| Task ordering | **A dependency was missing from the task list.** The half-open interval rule had to land *before* the alias-id fix, or the handover it creates — old row closing the same day the new one opens — would have read as a collision and failed its own acceptance test |

### To this engineer's own work

| Error | Correction |
|---|---|
| Three tests moved a price with `UPDATE model_version` | **That simulates the change backwards** and tests a state that cannot occur. It leaves `pricing_history` holding a value the loader never wrote, so no history row is due and no event fires. A real provider change arrives in the **incoming** data. The tests now write a modified copy of the seed file per iteration, which is what the week 5 poller will actually see |
| A test asserted the old query budget was "over 3x" the new one | It is 2.8x, and the test failed. The invented threshold was replaced with the pinned figure of 151 strings. Budget tests are pinned, not bounded, throughout |
| An earlier draft of this report said the nine skipped tests "were not merely unrun, they were too shallow to catch any of it" | **That outran the evidence.** They were never run in isolation against the pre-fix code paths. The supported statement is the one at the top: they passed unmodified, and therefore covered none of the six |

---

## One thing for Engineer 2 to check

`judge/` landed 62 tests in `d0be8e6`. **If any of them need a database, they
have exactly the same exposure**: skipping silently while the suite reports
green. Worth checking before week 4, when quote verification starts writing.
The mechanism that hid six defects in this lane is not specific to this lane.

`TEST_DATABASE_URL` — deliberately distinct from `DATABASE_URL`, because these
tests drop and recreate the public schema — is what unblocks it.
