# Engineer 2 — `judge/` handover

What this lane is, what was built, and the mistakes that cost the most. Written
so somebody could pick this up, or do the same job on a different project, and
not repeat the expensive parts.

*2026-08-19 · 35 modules, ~7,900 lines, ~360 tests in 24 files*

---

## 1 · The boundary, and why it matters more than it sounds

```
collect/  ──►  document + thread_context (carrying offset_map)  ──►  judge/
```

`collect/` fills those tables. **`judge/` reads them and never writes to them.**
Nothing flows back. An AST test asserts both directions — neither lane may
import the other — and that assertion shapes more design than anything else in
this document.

**The consequence people miss:** an exception raised in one lane cannot be
caught in the other, because the exception *type* has nowhere to live that both
can see. When `judge/` needed to distinguish three outcomes from a store read,
the answer was a returned **value**, not a raised exception (`resolver.py`). A
stdlib exception is the one exception — `UnicodeDecodeError` crosses fine,
because neither side has to import anything to catch it. That took a week to
notice.

---

## 2 · What was built

| stage | modules | job |
|---|---|---|
| **E5 extract** | `prompt` `client` `schema` `runner` `verify` `budget` `resolver` `placeholder` | prose → structured claim with a verified quote **(LLM)** |
| **E6 vet** | `reject` `weight` | discard promotional content; weight what survives |
| **E7 curate** | `gate` `phrases` `labels` `nightly` `thread_coverage` `reported_context` | count people, apply the gate, say it in words |
| **E8 publish** | `pages/{model,capability,filtered,coverage,changelog}` | five pages, ten HTTP endpoints |
| **Q1–Q7 answer** | `understand` `requirements` `rank` `cost` `answer` `profile` | task → ranked recommendation **(LLM, Q1 only)** |
| **storage** | `claims` `cells` `extractions` `answers` | every table this lane owns |
| **entry** | `cli` `app` `pipeline` | `judge extract`, `judge rebuild-cells`, FastAPI |

---

## 3 · The seven rules, and where each is actually enforced

Rules live in `CLAUDE.md`. **A rule that isn't enforced in code is a rule that
gets refactored away**, so each one has a location:

| rule | enforced by |
|---|---|
| 1 · no claim without a verified verbatim quote | `verify.py` three steps + `claim_verified_ck` CHECK in the schema |
| 2 · exactly two LLM stages | `understand.py` and `runner.py` are the only callers; tests assert no other module reaches a client |
| 3 · no synthesised number | `phrases.py` assembles from counts; `reported_context.derive` takes `min()`, never `avg()` |
| 4 · silence is not criticism | `pages/model.py` enumerates `capabilities.yaml`, not the rows returned |
| 5 · config in YAML | `contract/*.yaml`, read by `judge/config.py` |
| 6 · a missing value never becomes a definite one | `Verdict.UNKNOWN`, `ratio: None`, `Outcome` as a 4-state enum, `RefusingResolver` |
| 7 · a figure travels with its denominator | every `summary()` in `pages/`; `held_rate()` returns a triple, not a percentage |

**Rule 6 is the one this project broke most.** It was written after a hard
filter read an absent `supports_tools` as "cannot" and took a candidate list
from eleven models to one. Anything three-state exists because of that.

---

## 4 · The defect catalogue — read this part

Fourteen-plus instances of the same family in one fortnight. **None of them was
carelessness; every one was a correct-looking thing pointed slightly wrong.**

### 4.1 A module with no caller (~14 instances)

Built, tested, correct, and unreachable. `assert_no_fixtures`. The budget cap.
`coverage_gap`'s writer. `label_change`'s writer. Q1. All five page modules.
`Pipeline` itself, instantiated only in a test.

**The check that finds it:** `grep -rl <ClassName> <package>` and *read which
files come back*. If only its own file appears, nothing calls it.

**The check that does NOT find it:** "does every table have a writer?" — the
writer *class* existing is not the writer being *called*. I answered that
question yes, twice, and was wrong both times.

**And it caught me too:** I grepped for `AnswerStore`, got the file back, and
read it as wired. It matched the **module docstring**, which mentioned it while
explaining that nothing called it. Use `grep "AnswerStore("` — the call, not
the name.

### 4.2 A substring check matching your own prose (4 instances, all mine)

- banning `"complete"` failed on `"completeness"` — in the sentence required
- banning `"commit"` failed on a docstring saying *"never commits"*
- banning `"localhost"` failed on a comment about not defaulting to localhost
- banning `"RawStore"` failed on a comment explaining why it isn't used

**Fix:** strip comments and docstrings before asserting on source.
`_code_only()` in `tests/test_resolver.py`. A module may name a thing to
explain why it doesn't use it, and a raw substring check cannot tell that from
depending on it.

### 4.3 A variable the test supplies is a variable the test cannot check

The recurring one, and it has the widest reach:

- `ThreadInput` takes text as a parameter → the pipeline test proves the types
  line up and says nothing about reading from a database
- `document_id` is an *input* to a flattener → two independent implementations
  matched byte-for-byte and both used bare ids where the database holds `t1_`
  fullnames
- **the fixture id was `mv1`** → every real model page 404ed on the slash in
  `google/gemini-2.5-flash`, while the endpoint tests passed

**The tell:** the test and the code agree because the *test chose the value*.
Round-trip through the real carrier instead.

### 4.4 A check positioned where it cannot fire

`test_no_run_step_carries_a_hash_that_yaml_would_eat` catches the YAML-`#` bug
and runs at step 5 of a CI job the bug kills at step 2. Correct, present, and
three steps too late.

**Name the failure a check is meant to catch and the step that would produce
it. If the check runs after that step, it is documentation.**

### 4.5 Absence read as agreement

A comparison that returns "identical" because it found *no rows to compare*.
An empty column list for a table that isn't there. A gate allowlist that was
empty and therefore blocked nothing.

**These don't fail — they agree**, which is worse than an error, because a
confident pass needs a reason to distrust.

### 4.6 A test pointed the wrong way in time

I wrote `assert not hasattr(ReadOutcome, "CORRUPT")` to record a drift as a
fact. That test goes **red the moment somebody fixes it** — so whoever makes
the change has to delete a passing assertion to do it. That is how a temporary
state becomes permanent. Deleted.

### 4.7 Checking a premise is not checking the claim

I verified that `PayloadCorrupt` is raised only inside `put()` — correct, by
AST walk — and concluded a fourth outcome was unnecessary. The reachable case
was a **decode failure**, which nobody had mentioned. I confirmed exactly what
I was pointed at while the claim was larger than the premise.

### 4.8 Rule 7 applies to claims about risk, which contain no figure

*"Any branch older than the fix carries this defect"* is true, has no
denominator, and reads as a statement about what **is**. The population was 1
of 69. Same failure, same fix, and the rule as originally written can't catch
it because a reader looks for a figure and finds none.

---

## 5 · Precautions — the things that cost money or trust

### 5.1 Never share `.env`

Six live credentials: `DATABASE_URL` (production, remote), `OPENROUTER_API_KEY`
(spends money), `GITHUB_TOKEN`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`,
`RAPIDAPI_KEY`. Send `.env.example`. A frontend developer needs
`DATABASE_URL` pointing at their own local Postgres and nothing else.

### 5.2 `DATABASE_URL` is production. Never point a test or a first run at it

Use the local disposable instance (`scripts/dev-postgres.ps1`, port 5433,
`.env.test`). Every DB test runs `DROP SCHEMA public CASCADE`. The fixture
refuses any database lacking a `modelboard_meta.disposable` sentinel — do not
work around that guard.

**The test suite wipes the local database.** If you seed it and then run the
suite, your seed is gone. That looked like two bugs once and was neither.

**And you cannot run the DB suite while the dev backend is pointed at that same
database.** Found 2026-08-20: with `uvicorn` connected to `modelboard_test`, a
full run produced 7 failures and 15 errors across migrations, cell writes, blog
fetch and harvest schema - every one of which passes in isolation and passes
again with the server stopped (1,969 passed). `DROP SCHEMA public CASCADE`
against a database another process holds open does not fail cleanly; it fails as
a scattering of unrelated-looking assertion errors. **Stop the backend before a
full run**, or the suite will send you hunting a defect that is not there.

### 5.3 The spend cap must be wired, not documented

**And "wired" means one durable total, not one per caller.** Corrected
2026-08-20: `EXTRACTION_DAILY_BUDGET_USD` was read by extraction and by the ask
box into two separate in-memory counters, so the configured dollar was a dollar
PER STAGE, PER PROCESS - roughly $2 before counting `--workers`, and zero again
after a restart. The check also ran against a `Budget` rebuilt per HTTP request,
so `spent_usd` was always 0.0 and the 429 branch was unreachable. `charge()` had
exactly one caller, in `pipeline.py`.

`judge/spend_ledger.py` is the fix: an append-only record of every paid call,
read by both stages, so one cap means one cap and survives a restart. The
durable home is a table and `contract/` is shared, so it is proposed rather than
assumed.

**The test that catches this class needs more than one request.** Every existing
test made a single call, which is exactly the population where a per-request
counter looks correct.

`EXTRACTION_DAILY_BUDGET_USD` sat in two comments and nowhere in code for
weeks. It now binds in `budget.py`: the check runs **before** the call, because
spend cannot be undone, and `from_env()` returns `None` rather than an uncapped
budget so a forgotten variable can't read as a decision.

Measured cost: **$0.0021 per thread** — 2,010 in / 589 out, Gemini 2.5 Flash.
$1.00 ≈ 470 threads. Set a tighter cap for any experiment; I used $0.10.

### 5.4 Never let the pipeline guess a model

If a claim resolves to no `model_version` row, it is **skipped and logged**.
Guessing is worse than dropping. Consequence: the seeded model list caps what
can be extracted, so **low yield is a registry problem before it is a prompt
problem.** The first live run produced 8 verified claims and stored 0 for
exactly this reason.

### 5.5 Ask a language model for text, never for arithmetic

The first live run failed on five of six claims because `quote_offset` was off
by 1–3 characters. **The quotes were correct every time.** Models cannot count
characters. `verify.py::_locate` now searches for the quote and code derives
the span; the model's offset is a hint used only to disambiguate a repeated
quote. This is *more* rule-1 compliant, not less.

### 5.6 Inline every `$ref` in a tool schema

A schema can be valid, internally consistent, and **opaque to the model**.
Gemini returned `claims: [null, null, null, null]` — four claims it found and
couldn't construct, because `claims.items` was a `$ref`. `tool_schema_for`
inlines definitions now. The failure looks like a schema violation rather than
a lookup that didn't happen.

### 5.7 Pre-register what a run means before running it

`docs/measurements/first-extraction-run.md` was written before the first live
call: what's measured, what `insufficient` will mean and why, and **who owns
each failure mode** — Reddit failing while blogs pass is my prompt; blogs
failing while Reddit passes is the other lane's flattener. Committing that in
advance is what stops a result being explained afterwards.

---

## 6 · Requirements to run

```bash
pip install -e ".[dev]"                    # Python 3.11, Postgres 17, psycopg3
pwsh scripts/dev-postgres.ps1              # local disposable DB, port 5433
```

**Windows PowerShell 5.1 is the floor** — `pwsh` (7) is not required, despite
what older docs said. The script hangs at `pg_ctl -w start` when stdout is
captured; verify from `pg.log` and stop the wrapper. A stale `postmaster.pid`
after a crash presents as a hang: confirm the PID is dead, move the file aside,
restart.

`psycopg` has **no default `connect_timeout`** — a dead instance costs 250s per
attempt and reads as a hanging suite. Always pass it.

Verify: `python -m pytest -q` → **1,932 tests, 0 failures**, and
`python -m ruff check .`.

---

## 7 · What is not done

| item | owner | note |
|---|---|---|
| **Alias review — 23 launch-window entries** | E2 | *the* blocker. 7 of 340 models have surfaces, so a harvest finds almost nothing and extraction has nothing to read |
| `provisional AND mentions > 0` check | E1 to land, E2 designed | a flag nothing clears becomes permanent |
| End-to-end run reading input **from the database** | E2 | needs the shared reader wired; this is the acceptance test for the lane interface, not an improvement on it |
| Renderable path | blocked on a fresh export | a quote with no permalink must not render at all |
| Fifth `label_change.driver` for retention expiry | proposed | `new-evidence` would attribute a deletion to engineers going quiet |
| Auth, pagination | not started | do not deploy publicly as-is |

---

## 8 · If you take this over, do these four things first

1. **Run the caller check.** `grep -rl <ClassName> judge` for every store and
   page class. Anything appearing only in its own file is unreachable.
2. **Run the suite against a real database**, not just the fake-client tests.
   160 tests error without one, by design — a write path covered only by a skip
   is a write path nobody has run.
3. **Hit every endpoint against a real database.** That is how the `:path`
   routing bug was found, and no unit test could have.
4. **Read `judge/CLAUDE.md`.** The odd-looking decisions are load-bearing and
   the reasons are there — particularly the three E8 conditions, which all bite
   only when somebody builds the publisher.

The single most useful habit: **when a check agrees with you, ask what
population it looked at.** Every expensive mistake in this fortnight was a
correct answer to a question nobody had asked.
