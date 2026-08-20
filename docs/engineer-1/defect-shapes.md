# The defects, by shape

Around thirty defects were found in this lane in a fortnight. Read as a list
they teach almost nothing — the individual bug is never the one you meet next.
**Grouped by shape they are the most transferable thing this project produced.**

Nine shapes. Each has the sharpest instance, what it cost, and — the part that
matters — **how to recognise a new one**, because the point is to catch the next
one and not to remember these.

*Verified against `origin/main` at `225b126`. The canonical catalogue is the
docstring of `tests/conftest.py`, which carries eleven habits and is the version
that gets updated; this groups them and adds what happened outside the test
suite.*

> **Not confirmed — "around thirty".** There is no defect register in this
> repository, so the count is an estimate assembled from what is written down:
> 13 named incidents in `tests/conftest.py`, 4 in
> `docs/measurements/migration-path-first-use.md` §2, the 11 rule-6 conversions
> in §6 below, plus the write-batching and residue incidents. Several overlap and
> some were fixed in the same commit that introduced them, so **the true number is
> not recoverable and nothing here depends on it.** The shapes are the claim; the
> count is scene-setting, and it is the one figure in this directory without a
> population.

---

## The single sentence underneath all nine

**What each one cost was not a wrong answer but a missing one.**

That is rule 6's expensive case. A wrong answer gets argued with; an absence
gets accepted, because there is nothing on the page to disagree with. Nine
defects in one fortnight were caught **by a person reading a number that was
wrong in a way that read as an answer** — and under cron there is no person,
which is the entire reason `ops/chain.py` reports refusals instead of running
what it can.

If you remember one thing: **ask what this would look like if it silently did
nothing.** Every shape below is an answer to that question.

---

## 1 · The check that cannot fail

**The shape.** The assertion is weaker than its name, or the condition it names
cannot arise, so it passes in both worlds.

**Sharpest instance — #21.** A test named
`test_assembly_refuses_and_says_what_is_missing` asserted
`"specificity_score" in message`, with the comment *"the scorer that does not
exist"*. That asserts **the mention, not the claim**: it passes whether or not
the scorer exists. When the scorer landed, the refusal went on asserting
something false and **878 tests stayed green**.

**The family — "condition B", found when the first migration landed.** Three
tests and one production function turned out to be assertions that could not
fail because the condition they named could not arise:

- `only_chain` — *"a migration creates what `tables.sql` does not describe"*. At
  chain length zero the chain **is** the baseline, so it was an assertion about
  the empty set.
- `describe()` in production: `if self.pending_filenames: return …` came before
  `if not self.ledger_present: return "NO LEDGER"`, so **a pre-ledger database
  with work to do reported only the work.** Unreachable while `pending` was
  always empty.

**The inverse, and it is worth its own name — #58b.** An invariant in the
fixture builder read `flat_len == raw_len or raw_len == 1`. True of every
substitution that existed — emoji, one raw character each — and it **rejected a
correct map** the first time it saw a shrinking one (`&gt;`, four raw characters
to one). Every shape above is a check that fails to check; this one checked
confidently and checked the wrong thing.

**How to recognise it.** Ask *"what would have to be true for this to fail?"* and
then ask whether that is currently possible. If the answer is no, the test is
documentation. Then **break it on purpose and watch it fail** — every fix in this
file was confirmed by reverting it, and a test that has never failed has not been
tested. For #58b specifically: **an invariant derived from the data in front of
you is a description, and should be written as one until something independent
agrees with it.**

---

## 2 · The guard with no caller

**The shape.** Correct code, correct rule, tested — and nothing calls it. The
guard cannot fire, and its absence looks exactly like its passing.

**Sharpest instance — `in_window`.** `recompute_window` is correct and tested,
and **nothing had ever run it**, so 340 rows carried a schema default that reads
exactly like a computed answer. Not "the code is wrong"; the code was right and
had never executed.

**The count, today, verified on `origin/main`** by AST sweep plus per-symbol grep
— **six write-issuing functions have no production caller**:

```
write_authors          collect/assemble/authors.py
write_thread_context   collect/assemble/thread.py
mark_swept             collect/registry/openrouter.py
load_source_rows       collect/registry/sources.py
open_harvest_run       collect/ops/ledger.py
close_harvest_run      collect/ops/ledger.py
```

Two consequences worth stating because neither is visible from the code:
`assert_no_phantom_sweeps` compares `last_swept_at` against `harvest_run` and
**both operands are pinned at zero**, so it cannot fire in either direction; and
`load_source_rows` having no caller is why `source` holds 0 rows, which is why
`open_harvest_run` refuses with a sentence naming the loader rather than emitting
a foreign-key error.

**Two sub-shapes, and the distinction is the expensive part.**

**An import chain is no evidence of a call path** (habit 10). `job_run`'s ledger
is imported by `collect/ops/chain.py`, so **every wiring check found it** — grep,
the AST sweeps, the lane-boundary test all walk the module graph. What nothing
asked is whether the chain's stages *call* the writer. Three of them ran and
wrote nothing, so a green nightly reported success for producing no rows.

**A ruling with a caller is not a ruling with every caller.** `is_route` — "routes
are not models" — had callers in `collect/triage/entity.py` and `tracked.select`,
and not in `propose()`, **the primary output of the module the ruling lives in**.
So the narrowed path was protected and the un-narrowed path proposed six
mechanical variants for a routing pointer. Fixed; and the same question asked
again for this record found `alias_coverage()` still not consulting it, which is
why the headline "333 models with no alias surface" is really 316 models and 17
routes (`../how-it-works.md` §3.2.1).

**How to recognise it.** Never ask *"is this wired"* — the tools answer a
different question. **Count the rows.** `job_run` exists precisely so that *"has
this stage ever run **here**"* is a query rather than an investigation, and
`docs/measurements/unwired-tables.md` is that question asked table by table. An
import graph cannot answer it and a row count cannot be argued with.

---

## 3 · The guard in the wrong place in the sequence

**The shape.** The check is correct, present, mutation-checkable, and **runs after
the thing it guards**. It reports on a corpse.

**Sharpest instance — `ci.yml`.**
`test_no_run_step_carries_a_hash_that_yaml_would_eat` was written for exactly the
defect that killed CI: a `#` in a plain `run:` scalar, which YAML reads as a
comment and truncates. It ran at **step 5, inside `pytest -q`** — after Install,
after the dev-extras assertion, after the database. So a quoting bug still failed
the job at *"Assert the dev extras actually arrived"*, with bash reporting
`unexpected EOF while looking for matching` under a step name that says nothing
about YAML. **Whoever read that log first had to rediscover the cause with the
test that names it sitting unrun in the same repository.**

Fixed by giving it its own step immediately after checkout: it needs a YAML
parser and a file, so it can run first.

**How to recognise it.** For each check, **name the failure it is meant to catch
and the step that would produce it.** If the check runs after that step, it is
documentation. Every one of the other habits passes on this defect — it has a
caller, it runs, it is true, and breaking the YAML does make it fail. What it
cannot do is fail *first*, and **no property of the test can reveal that, because
the property is not in the test.** Cheapest fix is usually to give the check the
narrowest possible dependencies and move it earlier.

---

## 4 · The guard that enumerates attributes

**The shape.** A comparison covers the attributes somebody thought of, and the
list grows by incident rather than by audit.

**Sharpest instance — #54.** `columns()` in `tests/test_migrations.py` compared
name, type, nullability and default — enough until
`thread_context.coverage_ratio` became the schema's first `GENERATED ALWAYS`
column. **A generated column and a plain one of the same type differ in nothing
that query selected**, because a generated column has no default. The migration
was edited to create it plain and **all 21 tests passed**.

The cost would have been specific rather than general: `coverage_ratio` is
generated *so that it cannot drift from its inputs*, so the test would have
signed off on precisely the drift the column exists to prevent.

**The gap that is still live, and it is on the prices.** The list now selects
seven attributes and still cannot see **the parameters of a type rather than the
type**: `information_schema` reports `numeric(12,6)` and `numeric(10,2)` both as
`data_type = 'numeric'`, so they compare **equal**. `model_version.price_in` is
`numeric(12,6)` and `batch_discount` is `numeric(4,3)`; a migration declaring
either at a different precision passes.

**How to recognise it.** When a guard compares a list of properties, ask **what
the thing being compared HAS that the list omits** — and write the omission down
beside the guard, because the next person will extend it by incident too. The
tell for #54 was that the file's coverage had grown twice by incident and never
once by audit.

---

## 5 · The name that answers a different question

**The shape.** A name match tells you a string exists. It does not tell you the
object exists, and it tells you nothing about whether anything reads it. One
tool, three questions, and grep answers only the first.

**Sharpest instance — four of five broken checks in one week**, all a name
matching in the wrong context:

```
"pending"             LabelState.PENDING — a different column on a different table
"outcome"             job_run.outcome, AND a table named `outcome`
harvest_run_source    an INDEX, harvest_run_source_query_idx
AnswerStore           a docstring
```

**Why this is worse than a shape error**, and it is the observation worth
keeping: *a name matching in the wrong context is the cheapest false positive to
produce and the most expensive to distrust, because the result is well-formed.*
A shape error produces something visibly malformed — a truncated string, a count
that does not add up — and you doubt it on sight. **A name collision produces a
plausible, correctly-typed, confidently-wrong answer, and everything downstream
inherits the confidence.**

**The other direction ran the same week.** `write_authors` had three apparent
callers and **all three were prose**; a column referenced through a built
identifier is invisible to a search for its name — which is how *"nothing uses
this column"* and *"no such column exists"* became the same answer.

**And once more, writing this document.** The caller inventory in §2 came from an
AST sweep, and it reported `ops/ledger.py:close_run` as called from
`assemble/flatten.py` — which has a **local closure of the same name** doing
something unrelated. The tool written to avoid the shape reproduced it. Recorded
because it is the cheapest possible proof that this is not about carelessness.

**The adjacent shape — habit 9.** A helper **named for what it returns is read as
a statement about what it covers**. `columns()` returns column tuples and nobody
misread it; readers, across four separate turns, treated *"the comparison
compares columns"* as an answer to *"does it cover tables"*. It is not an answer,
it is a different question the name invites you to stop asking. **The fix is not
a rename** — `columns()` is well named. The fix is that a module of comparison
helpers states its own scope, in prose, next to the code.

**How to recognise it.** **Name the question before choosing the tool, and say in
the finding which question you answered.**

```
is this string in the tree     grep answers this
does the object exist          the CATALOG answers this — query by TYPE as well
                               as by name; relkind stops an index answering a
                               question about tables
is it written                  count the rows, then read the ledger
is it read                     no cheap answer. An AST call graph is closer than
                               grep and still not proof. Say which you established
```

---

## 6 · The absent value that became a definite one

**The shape.** Rule 6. A missing value is silently converted into a definite one,
and the result surfaces as an absence with nothing to disagree with.

**Sharpest instance — the one the rule was written from.** `judge/`'s hard filter
read an absent `supports_tools` as *"cannot"* and took a candidate list **from 11
models to 1**. It surfaced as ten models simply not being there.

**The same shape, eleven more times.** Both lanes, because the rule is the
project's rather than this lane's — the sharpest instance above is the other
lane's, and so is the last row here. Each fix is now load-bearing:

| where | absent was becoming | what it is now |
|---|---|---|
| five `supports_*` columns, `DEFAULT false` | "the provider says no" | explicit `None` where the feed is silent |
| OpenRouter router prices at `-1` per token | −1,000,000 USD/Mtok, overflowing `numeric(12,6)` | `None` — a sentinel meaning *not published* stays unknown |
| `in_window` schema default on 340 rows | a computed answer | recomputed nightly; `assert_no_phantom_sweeps` for the checkable sibling |
| `SieveYield.phrase_present = 0` | "no candidate carried the phrase" — a finding | `None` for not-measured |
| `TrackedModel.mentions = 0` | "we looked and found nothing" | `None`; unmeasured models are **unrankable** |
| `hidden_children_min = 0` for a blog | "nothing was withheld" | `None` — true of the platform, false of us |
| `FloorVerdict` two-state | an unscored document *failing* the floor | tri-state; `UNKNOWN` records itself as `specificity-unscored` |
| `unavailable` as one list | "cannot run" and "nothing to run on" | `NotRun` with two members — one falls to zero as the build catches up, the other **grows** with the corpus |
| Reddit `"data not found"` | an error | HTTP 200 with zero results |
| a blog 304 | zero items fetched | its own outcome, all the way to `harvest_run_fields` |
| `Budget.from_env()` with no variable set | an uncapped budget | `None`, so the caller must decide |

**How to recognise it.** Two questions. *"Can this field be absent, and does the
code distinguish absent from false?"* And the harder one: *"if this were absent,
would the output look like a considered answer?"* If yes, that is the expensive
case — **the defect presents as a considered answer**, which is why every one of
the twelve above had to be found by somebody reading a number rather than by a
failing test.

---

## 7 · The real value answering a question it was not asked

**The shape.** Rule 7, and the sibling of §6. The number is real, the measurement
is correct, and it answers a narrower question than the one it is being used for.
**This class survives inspection** — a spot-check confirms the figure.

**Sharpest instance — `52.7%` subject match.** Quoted as evidence for GitHub's
role in the corpus and written into `docs/logic-and-workflow.md` §6 as a
justification. The corpus had been retrieved **for one model using that model's
own variants**, so a document matching a subject term is partly the query coming
back. The *shape* survived — GitHub names models in configs rather than
describing them in prose — and the rate did not.

**Four more, each load-bearing before anyone checked:** `"context window"` in 96%
of returns and `"went back to"` in 100%, both collocation frequency read as
operator behaviour; `sonnet 4.5` at **426 mentions of which 394 were
substitution-slice**, a slice measurement doing duty as a corpus measurement
**inside the argument for the ranking method itself**; and the specificity floor's
`7.7%`, which is a property of the 59 alias surfaces loaded that day as much as
of the corpus — the same documents give 3.8% and 0.8%.

**The form with no number in it at all**, which is why the rule as first written
missed it: *"any branch older than the fix carries this defect"* is a true
statement about what **could** be wrong, and with no population attached it reads
as a statement about what **is**. The population was **1 of 69 branches**, and it
was the one already being deleted.

**The adjacent shape — a proviso read as a general claim.**
`collect/assemble/thread.py` said `pipeline_version` *"never under-identifies,
which is the direction that matters, **provided `PIPELINE_VERSION` is bumped when
the flattener changes**"*. It under-identified the same day: what changed was
`collect/triage/specificity.py`, **the scorer that picks which children get
flattened** — a path the sentence does not mention. One id, two different
selections, and `ON CONFLICT DO NOTHING` kept the stale row. **Both engineers read
the proviso as a caveat on a general claim; it was the entire extent of what had
been checked.**

**How to recognise it.** **The check needs no suspicion.** Ask what the
denominator is and where it came from. If the answer is not beside the figure,
the figure is not yet evidence. For a guarantee rather than a figure: ask what
the proviso ranges over, and assume it ranges over exactly what it names.

---

## 8 · The input that silently emptied

**The shape.** The assertion is fine and the input became empty. **A check over
an empty set passes.**

**Sharpest instance — #58.** A check scoped to the file its author was thinking
about reported clean. Widened to the whole tree, the regex silently stopped
matching and **printed ONE file where there were two** — which looked exactly
like a pass. It was caught because **a line of output was missing**, not because
anything failed.

**How to recognise it.** *"Zero checked and zero failed look identical in a test
runner."* So: **a check that iterates must count what it iterated over, and
something must assert the count.** `parametrize` over a discovered file list has
the same hazard — an empty list is a green run — which is why
`test_there_are_python_files_to_check` exists in `tests/test_lane_boundary.py`,
and why every new sweep of the tree needs its equivalent.

---

## 9 · The test's relationship to a variable

**The shape.** Not about the assertion at all. About a value the test supplied,
or failed to supply, without knowing it mattered.

**Sharpest instance — #57, a value supplied to both sides.** Byte equality between
two independent flatteners passed on **2,481 characters and 20 segments** — and
did not notice that their `document_id`s used different conventions: `collect/`
stores fullnames (`t1_…`), the reference fixture stripped them.

**A variable the test provides is a variable the test cannot check.**
`document_id` is an **input** to the flattener, not an output. The test handed it
the fixture's ids and compared the text and the offsets, so a disagreement about
ids was **invisible by construction** — not a weak assertion and not an empty
input. It surfaced by writing a row and reading it back: `raw_text_of` is keyed by
`document_id`, so the mismatch returns `RAW_TEXT_MISSING` for every quote in the
thread — **a naming failure presenting as a storage failure.**

**The inverse — #59, a value supplied to neither.** Two tests constructed a
`RedditHarvester` and asserted things about the terms gate. Both passed on a
laptop and failed in CI with `RAPIDAPI_HOST is not set`, because the constructor
read the setting and the laptop had a `.env`. **Neither test was about whether
RapidAPI is configured, so neither should have been able to fail for that
reason** — and until CI ran, both had been asserting something about a configured
machine rather than about the code. The fix is not to configure CI: `host` became
a constructor argument defaulting to the setting, so the production guard is
unchanged. The pattern already existed one file over, in an `autouse` fixture;
the new file had not adopted it.

**The third member — a docstring precondition nobody tested.** `names_version`
passed raw text to `sieve.matches`, **whose own docstring says "already-normalised
text"** and which does not casefold. Every capitalised model name was missed — **1
of 111 blog articles scored where the figure is 7** — and all 45 tests passed
because every one used a lowercase model name. Same family: `sieve_any` silently
dropped its `window` argument, and **no test had ever passed `window` to
`sieve_any`**, so the fix had no guard either. Found by AST-walking every
keyword-only parameter against every call site, after a regex attempt gave a
false negative.

**How to recognise it.** Three habits, and they are the cheapest three in the
file:

1. **Where a callee's docstring states a precondition, the precondition is a test
   case.** Not a comment — a test. Pass it something unnormalised and assert what
   happens.
2. **Where two components must agree about a value, do not let the test supply it
   to both.** Round-trip through the real carrier: write the row, read it back,
   and let the second component look the value up the way it will in production.
3. **Run the suite without your `.env`.** The cheapest audit there is, and CI is
   otherwise the only thing that performs it — by accident, on whatever happens
   to break first.

---

## The two that are not shapes, and are worth a paragraph each

**The performance defect that only a remote could show.** `write_authors` took
**ten minutes for 4,391 rows** against a remote instance — roughly 130ms of
latency each and almost no work — and **3.8 seconds batched**. Two other writers
had the same shape and had never met volume: `github.write_documents`, never run
against a remote at all, and `openrouter.write_model_versions`, 340 rows nightly.
**Every run so far had been local, where 130ms is 1ms**, which is exactly why it
survived. `tests/test_write_batching.py` pins **the shape and not the timing** —
counting statements against a fake connection fails on a per-row loop wherever it
runs, and a latency assertion would pass on a laptop.

**The residue that would have made the one measurement it enabled wrong.** That
run left **4,391 `author` rows against 0 `document` rows**, all with one
`first_seen_at` identical to the microsecond — one transaction, run by hand,
because `write_authors` has no CLI command. Nothing referenced them and nothing
read them, so deleting cost nothing. **What would have cost something is leaving
them**: the measurement they were written to enable is `overlap_by_handle`, the
one that decides whether FR-17 has anything to match, and 4,391 handles from a
corpus that no longer exists would have answered it wrong. Deleted 2026-08-18,
recorded in `docs/measurements/staging-author-residue.md` **because the rows are
gone and the way they arose is not.**

---

## The habits, in one place

Ordered cheapest first, which is how they should be applied. Numbers are
`tests/conftest.py`'s, which is the version that gets updated.

| | habit |
|---|---|
| 1 | Where a callee's docstring states a precondition, **the precondition is a test case** |
| 2 | Assert the state of the world, **not the wording that describes it** |
| 3 | **Break it on purpose and watch the test fail.** A test that has never failed has not been tested |
| 4 | A check that iterates **must count what it iterated over**, and something must assert the count |
| 5 | Where two components must agree about a value, **do not let the test supply it to both** |
| 6 | **Run the suite without your `.env`** |
| 7 | **Ask where a guard runs**, not only whether it passes |
| 8 | A guard that enumerates attributes **covers the attributes somebody thought of** — write down what it omits |
| 9 | A helper **named for what it returns** is read as a statement about what it covers |
| 10 | **An import chain is no evidence of a call path.** Count the rows |
| 11 | **Name the question before choosing the tool**, and say which question you answered |
