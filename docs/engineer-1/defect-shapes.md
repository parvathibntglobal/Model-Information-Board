# The defects, by shape

Around thirty defects were found in this lane in a fortnight. Read as a list
they teach almost nothing — the individual bug is never the one you meet next.
**Grouped by shape they are the most transferable thing this project produced.**

Ten shapes. Each has the sharpest instance, what it cost, and — the part that
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

## The single sentence underneath all ten

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

**The count** was **six** write-issuing functions with no production caller when
this was written, and is **five** as of 2026-08-20 — `load_source_rows` gained
`registry load-sources`, and the twelve rows are on staging:

```
write_authors          collect/assemble/authors.py
write_thread_context   collect/assemble/thread.py
mark_swept             collect/registry/openrouter.py
open_harvest_run       collect/ops/ledger.py
close_harvest_run      collect/ops/ledger.py
```

One consequence worth stating because it is not visible from the code:
`assert_no_phantom_sweeps` compares `last_swept_at` against `harvest_run`, and
**both operands are still pinned at zero** — `mark_swept` has no caller and no
sweep has written a `harvest_run` row — so it cannot fire in either direction.

`open_harvest_run` **can** now write: the `source` rows exist, and it was
exercised against staging for `github`, `reddit` and `blog:simonwillison.net`
inside a rolled-back transaction. What it lacks is a sweep to call it. Its
refusal message was itself stale for a few hours, which is §2a.

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
mechanical variants for a routing pointer.

**Then it happened again, twice more, and the third instance is the instructive
one.** Asking the same question while writing this record found
`alias_coverage()` also not consulting it — **17 of its 333 "models awaiting a
hand-written surface" were routes** — and fixing that made it the ruling's fourth
caller. `alias_coverage` now returns **316**, and `316 + 17 routes + 7 carrying
surfaces = 340` closes exactly.

**Why that one survived three rulings: the cost was a figure, not a verdict.**
The other instances produced a wrong *answer* about a model — a seat, a proposal,
an entity match — and a wrong answer eventually meets somebody who disagrees with
it. This produced a *number that was 5% too large*, in the direction that
overstates our own gap, and 333 was quoted as the headline constraint in two
documents and a measurement without anybody having reason to doubt it. **A ruling
whose violation shows up only in a denominator has no natural discoverer.**

The standing lesson, now written beside the predicate: **a ruling implemented as
a predicate needs its call sites enumerated somewhere**, because nothing about
`is_route` reveals which paths consult it — which is habit 10 (§2 above) applied
to a rule rather than to a writer.

**How to recognise it.** Never ask *"is this wired"* — the tools answer a
different question. **Count the rows.** `job_run` exists precisely so that *"has
this stage ever run **here**"* is a query rather than an investigation, and
`docs/measurements/unwired-tables.md` is that question asked table by table. An
import graph cannot answer it and a row count cannot be argued with.

---

## 2a · The refusal that outlived its premise

**The shape.** A refusal message is correct, legible, and names a remedy that has
since been applied. It is read by somebody who is already stuck, and it sends
them to the wrong place.

**Sharpest instance — `open_harvest_run`, 2026-08-20.** `source` held 0 rows
because `load_source_rows` had no caller (§2), so the writer refused upstream of
the foreign key and said so:

> *"`load_source_rows` is the loader that fills it — which has no caller yet.
> **Wire that first**."*

Exactly right for the whole build. Then `registry load-sources` landed, twelve
rows went into staging, and the sentence became advice to wire something already
wired — while remaining a perfectly accurate description of a foreign key.

**Why it is not just §2 again.** §2 is a guard that cannot fire. This one fires
correctly and *misdirects*, and the cost lands at the worst moment: a refusal is
read by someone mid-failure, who has the least budget for a wrong lead. A stale
docstring wastes a reader's afternoon; a stale refusal wastes it during an
incident.

**And the test pinned the wording, so it kept passing.**

```python
assert "load_source_rows" in str(refusal.value)
```

Habit 2 in its hardest form — *assert the state of the world, not the wording
that describes it.* Here the wording **was** the state for as long as the loader
had no caller, which is what made the assertion look like a state check. Nothing
failed when the world moved underneath it.

**The durable fix is which noun the message names.** It now names the **command**
— `registry load-sources` — plus the id shapes. A command is a stable public
surface; the internal function name was only ever relevant *while it had no
caller*, so naming it baked the temporary condition into the permanent message.
The test asserts the command is present **and that the function name is gone**,
because "add the new thing" leaves the stale thing in place.

**How to recognise it.** Two questions, and neither needs suspicion:

- **Does this message name a remedy, and is the remedy still outstanding?** Every
  refusal that says "do X first" is dated by X. When X lands, the message is a
  loose end and nothing links them.
- **Would this message be right if the thing it names were fixed?** If not, it is
  describing today rather than the failure — and the failure is what outlives.

Related to `#58b` — an invariant that outlived its premise — and distinct in what
outlived: there, an assertion about data; here, a sentence about the build.

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

## 5a · The match that ignored word boundaries, twice

**The shape.** A surface matched by containment rather than by boundary hits
inside longer words. It is shape 5's sibling: the same well-formed, confidently
wrong answer, arrived at by a substring rather than by a name.

**First instance, `resolve()` on movie posts, 2026-08-18.** A pure-code matcher
hit `free` inside *"freeze"* and `fusion` inside *"confusion"*, and it was
invisible on an AI corpus — the control experiment on unrelated posts is what
surfaced it (`docs/measurements/control-and-reshape.md`). It is quoted in
CLAUDE.md as the reason code-only extraction was refused.

**Second instance, in the tool built to sample for the golden set, 2026-08-20.**
The two-surface stratum was counted by substring containment and reported **43**
candidates. `re.finditer` with `` on both ends reported **2**, and **40 of the
41 dropped were `pro` inside "problem" and "process"**.

**The consequence is the one worth keeping: the stratum would have been NOISE
rather than empty**, and noise is worse. An empty stratum says *look somewhere
else*. A stratum of 43 rows where 41 are `pro`-in-`problem` says *here is your
sample*, and a labeller works through it before anyone asks what matched.

**AND THE BLAST RADIUS DEPENDS ON THE SURFACE LIST, NOT ON THE CORPUS**, which
is why this went unnoticed on one side and not the other. Re-run against the 105
alias surfaces in `model_alias`, over 57 stored documents:

```
>=2 surfaces, substring containment : 23
>=2 surfaces, word boundaries       : 22        one document, four owner-claims
```

Nearly harmless — because **every one of those 105 surfaces carries a digit**.
`gpt-4`, `opus 4.8`, `haiku-4.5` cannot hide inside an English word. The
0-of-41-with-a-family-surface measurement is the same fact from the other side:
the tracked-set artifact contains no bare family words, so the seated population
is structurally immune to the defect that cost the golden-set tool 41 of 43.

So the fix is `` on both ends in both places, and the lesson is that a
containment matcher is safe **only for as long as no digit-free surface enters
the list** — which is one reviewer accepting one `family_surface` away.

## 5b · The literal inside SQL, invisible to a search for the column

**The shape.** A value written as a string inside a SQL statement is not found by
a search for the Python form of the same assignment. It is shape 5 run backwards:
not a name matching in the wrong context, but the right name in a context the
tool does not read.

**Instance, 2026-08-20.** *"Only one writer passes `document.status`"* — reported
twice, from `grep "status" --include=*.py` and from `grep '"status"'`. Both found
`collect/assemble/article.py:184`, a dict value, and neither found
`collect/adapters/github.py:538`:

```sql
INSERT INTO document (id, source, …, engagement, status)
VALUES (%(id)s, %(source)s, …, %(engagement)s, 'kept')
```

**Two writers, both hardcoding a triage verdict on rows triage has never seen** —
and the second one is why 27 GitHub documents read `kept` with `triage_verdict`
NULL. The conclusion drawn from the miss was that changing the column default
would be sufficient; with both writers visible, the default is the third source of
the value and changing it alone fixes nothing.

**Already recorded once from the other direction.** §5 notes `write_authors`
having three apparent callers that *"were all prose"*, and that a column reached
through a built identifier is invisible to a search for its name. This is the same
sentence with the operand swapped, which is the argument for the habit below
rather than for another instance.

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
| 12 | **A containment match is a boundary match's false positive.** `\b` both ends, and ask whether any surface in the list is a word |
| 13 | **Grep the SQL too.** A column written as a literal inside a statement answers no search for the assignment |
| 14 | **`grep "<name>"` reads as presence. `grep "def <name>"` is the check.** A bare substring search matches any longer identifier containing the name — `_local_part` hits `def test_local_part` — so an absent symbol returns a line and looks defined. Verify a name by its DEFINITION, and when there is no definition, ask for a `file:line` before searching a second time: re-deriving an absence generates nothing |
| 15 | **A description is not a change.** ~20 measurement documents against ~10 code changes in one session, and every change that landed had a failing test to attach to. The ones that stayed documents were cross-lane, or had no reproduction to pin. So the ratio is not a work-rate observation, it is a diagnostic: **if the failing test cannot be written, the defect is not yet understood well enough to fix** — which is also why an asserted symbol with no `file:line` cannot become a change, only a search |

---

## Shapes 14 and 15 are one shape from two sides — 2026-08-21

Recorded together because they cost real turns in the same session and each one
hides the other.

**Three symbols were asserted that exist in no file, on no branch, in no
commit** — `_local_part`, `_seed_ids`, and a `mistralai/mistral-large-3` registry
row. Each time, a fix, a blast radius and a re-seed were designed on top of them,
and each time the design was coherent: the reasoning was sound and its subject
was absent.

**Two things let that run:**

- **from the asserting side**, `grep "_local_part"` returns
  `tests/test_registry_aliases.py:64: def test_local_part():` — a real line, in a
  real file, containing the name. Substring presence reads as definition. That is
  shape 14, and it is the same family as shape 12: *a containment match is a
  boundary match's false positive*, applied to identifiers instead of surfaces.
- **from the answering side**, I replied "it does not exist" five times and
  re-derived it from scratch each time instead of asking for the anchor once.
  Restating an absence is not evidence-generating. That is shape 15's other face:
  I produced descriptions where a question would have been cheaper.

**And scepticism was not a safe default either**, which is what made it
expensive: `cell_current` was raised the same way and is entirely real — a view in
`contract/tables.sql:648`, read by `judge/ask/answer.py`, with a stale-row hazard
nothing else would have surfaced. One of five was real. So each had to be
checked; the waste was in checking the same one five times.

**The rule, both directions:** cite a path or a symbol seen in a report, not one
inferred from a mechanism — and when given a name with no path, ask for the path
before the second search.

