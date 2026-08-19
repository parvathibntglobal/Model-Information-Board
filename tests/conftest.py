"""Database access for the write-path tests, and the guards around it.

Two jobs, and the first one matters more than it looks.

**Silence is the defect.** Six real defects survived a green suite because
`tests/test_registry_load_db.py` skipped for want of a database, and a skip
reads as success. It gets worse as the suite grows: 247 passed with 9 silent
skips looks healthier than the 139 that originally hid the bugs. So a missing
database is a **failure** by default, not a skip. `ALLOW_MISSING_TEST_DB=1`
degrades it to a skip for a laptop that genuinely has no server, and says so
loudly in the run summary, because an override whose consequence is invisible
becomes permanent the first time somebody puts it in a shell profile.

**The suite destroys the database it points at.** `conn` runs
DROP SCHEMA public CASCADE before every test. Pointed at anything real, that
is a very bad afternoon. Three layers stop it, cheapest and clearest first.

A CONVENTION, WRITTEN DOWN BECAUSE A FOURTH INSTANCE IS COMING
--------------------------------------------------------------
**Test the world's assumptions, not the code's.** Three defects have now
survived a green suite in the same way, and the suite was green each time
because every test shared an assumption with the code under test.

    #21  `test_assembly_refuses_and_says_what_is_missing` asserted
         `"specificity_score" in message` with the comment "the scorer that
         does not exist". That asserts the MENTION, not the CLAIM: it passes
         whether or not the scorer exists. When the scorer landed, the refusal
         went on asserting something false and 878 tests stayed green.

    #16  `sieve_any` silently dropped its `window` argument. No test had ever
         passed `window` to `sieve_any`, so the fix had no guard either. Found
         by AST-walking every keyword-only parameter against every call site,
         after a regex attempt gave a false negative.

    #22  `names_version` passed raw text to `sieve.matches`, whose own
         docstring says "already-normalised text" and which does not casefold.
         Every capitalised model name was missed — 1 of 111 blog articles
         scored where the figure is 7. All 45 tests passed, because every one
         used a lowercase model name.

    #58  A check scoped to the file its author was thinking about reported
         clean. Widened to the whole tree, the regex silently stopped matching
         and it printed ONE file where there were two — which looked exactly
         like a pass. Caught because a line of OUTPUT was missing, not because
         anything failed.

         **Distinct from the three above, and the distinction is the point.**
         In #21 the assertion was weaker than its name. Here the assertion was
         fine and THE INPUT SILENTLY EMPTIED: a check over an empty set passes,
         and a check over a set that used to have two members and now has one
         passes just as quietly. Nothing was asserted about how much was
         checked.

         The habit it adds is 4 below. A check that iterates must say how many
         things it iterated over, and something must care about that number —
         otherwise "checked 0 files, all clean" and "checked 200 files, all
         clean" are the same output.

    #54  `columns()` in the equivalence test compared name, type, nullability
         and default — enough until `thread_context.coverage_ratio` became the
         schema's first GENERATED ALWAYS column. A generated column and a plain
         one of the same type differ in NOTHING that query selected, because a
         generated column has no default. The migration was edited to create it
         plain and all 21 tests passed.

         Same family as #16 — an option never exercised — except the option was
         a *property of the data*, not an argument. And the cost would have been
         specific: `coverage_ratio` is GENERATED so it cannot drift from its
         inputs, so the test would have signed off on precisely the drift the
         column exists to prevent.

    #57  Byte equality between two independent flatteners passed on 2,481
         characters and 20 segments — and did not notice that their
         `document_id`s used different conventions. `collect/` stores
         fullnames (`t1_…`); the reference fixture stripped them.

         **A VARIABLE THE TEST PROVIDES IS A VARIABLE THE TEST CANNOT CHECK.**
         `document_id` is an INPUT to the flattener, not an output: the test
         handed it the fixture's ids and compared the text and the offsets, so
         a disagreement about ids was invisible by construction. Not a weak
         assertion and not an empty input — the assertion was exactly as strong
         as it looked, over exactly the data it claimed, and the defect was in
         the part the test supplied.

         It surfaced by writing a row and reading it back: `raw_text_of` is
         keyed by `document_id`, so the mismatch returns `RAW_TEXT_MISSING` for
         every quote in the thread — a naming failure presenting as a storage
         failure.

         The habit is 5 below. Where two components must agree about a value,
         the test cannot be the one that supplies it to both.

    #58b An assertion in the fixture builder read
         `flat_len == raw_len or raw_len == 1`, which held for every
         substitution that existed — emoji, one raw character each — and broke
         the first time it saw a shrinking one, `&gt;` at four raw characters
         to one flat. It rejected a CORRECT map.

         **The inverse of every shape above.** Those are checks that fail to
         check: an assertion weaker than its name, an option never exercised,
         an input that emptied, a value the test supplied. This one checked
         confidently and checked the wrong thing — an invariant describing the
         fixture rather than the property — and nothing revealed it until the
         world widened by one document.

         There is no habit that would have caught it early, and pretending
         otherwise would be the fifth shape again. What there is: an invariant
         derived from the data in front of you is a description, and it should
         be written as one until something independent agrees with it.

    #59  Two tests constructed a `RedditHarvester` and asserted things about
         the TERMS GATE and about where that gate fires. Both passed on a
         laptop and failed in CI with `RAPIDAPI_HOST is not set`, because the
         constructor read the setting and the laptop had a `.env`.

         **A variable the test does not provide and does not know it depends
         on.** The inverse of #57: there, a value the test supplied to both
         sides was one it could not check; here, a value it supplied to
         neither was one it did not know was in play. Both are the test's
         relationship to a variable rather than to an assertion.

         What makes it expensive is what it was asserting. Neither test was
         about whether RapidAPI is configured, so neither should have been
         able to fail for that reason — and until CI ran, both had been
         asserting something about a configured machine rather than about the
         code.

         The fix is not to configure CI. It is to let the test supply what it
         depends on: `host` became a constructor argument, defaulting to the
         setting so the production guard is unchanged.

         `tests/test_reddit_fetch.py` had already solved this with an
         `autouse` fixture setting the host for every test in the file, which
         is why that file passed in CI and mine did not. The pattern existed;
         the new file did not adopt it.

    ci.yml
         `test_no_run_step_carries_a_hash_that_yaml_would_eat` was written for
         exactly the defect that killed CI at step 2 - a `#` in a plain `run:`
         scalar, which YAML reads as a comment and truncates. It ran at step 5,
         inside `pytest -q`: after Install, after the dev-extras assertion,
         after the database. **Correct, present, and three steps too late.**

         So the guard existed and the job still failed at `Assert the dev extras
         actually arrived`, with bash reporting `unexpected EOF while looking
         for matching` under a step name that says nothing about YAML. Whoever
         read that log first had to rediscover the cause with the test that
         names it sitting unrun in the same repository.

         **A GUARD'S POSITION IN A SEQUENCE IS PART OF WHETHER IT WORKS.** A
         check that needs a database cannot guard the database setup. A check
         that needs the install cannot guard the install. Ordering is not
         packaging - it decides which failures a guard is still upstream of,
         and a guard downstream of the thing it protects reports on a corpse.

         **Distinct from the two failures it resembles, and the distinctions
         are the point.** `assert_no_fixtures` had NO CALLER for weeks (#27):
         nothing ran it, so it could not fire. `#58b`'s invariant OUTLIVED ITS
         PREMISE: it ran, and checked something that had stopped being true.
         This one has a caller, runs, and is true - it is simply sequenced
         behind the failure it describes. Every habit below passes on it.
         Habit 3 in particular: break the YAML and the test does fail. It just
         never runs in the job that matters, and no property of the test can
         reveal that, because the property is not in the test.

         Fixed by giving it its own step immediately after checkout, before
         Install - it needs PyYAML and a file, so it can run first. Mutation-
         checked 2026-08-19: the `# noqa` was reintroduced and both workflow
         tests failed, at step 3, on a named assertion about YAML.

         The habit is 7 below. Found by Engineer 2.

    migrations
         **The five NOT NULL mismatches between the chain and `tables.sql` are
         all in one direction**, reported by Engineer 2 and recorded here
         separately from the check that found them, because it is worth knowing
         on its own: every mismatch is the chain being STRICTER than the
         declaration, so nothing writes past a constraint the schema does not
         have. The drift is uniformly conservative.

         That is a different fact from "the check has a gap", and the two get
         confused because they arrived together. A conservative drift costs a
         confusing schema and refuses nothing it should accept; the gap in the
         check (habit 8) is about what the next drift could be. Neither implies
         the other, and the direction is the part that stops being true first —
         it holds because nobody has yet loosened the chain relative to the
         declaration, not because anything enforces it.

         NOT REPRODUCED HERE. The count and the direction are hers; this entry
         records them rather than confirming them, and the check needs a
         database to run.

Ten shapes of the same mistake: asserting the text of a claim instead of its
truth; never exercising an option; never leaving the input shape the author had
in mind; **never checking that the check had anything to check**; comparing a
thing on every axis except the one that is new; **checking agreement on
everything except the value the test itself provided**; **describing the
data confidently and calling it the property**; **passing because the
machine is configured rather than because the code is correct**; and **running
the right check too late in the sequence to guard the thing it guards**. What
each cost was not a wrong answer but a MISSING one, which is the class this
project keeps paying for — rule 6's expensive case, where the defect surfaces
as an absence with nothing to disagree with.

Three habits that would have caught all three, cheapest first:

  1. **Where a callee's docstring states a precondition, the precondition is a
     test case.** `matches` says "already-normalised" — so pass it something
     unnormalised and assert what happens. Not a comment; a test.
  2. **Assert the state of the world, not the wording that describes it.** If a
     message claims something is absent, assert the absence too, from the
     contract or by import. A message and the fact it asserts drift apart.
  3. **Break it on purpose and watch the test fail.** Every fix above was
     confirmed by reverting it. A test that has never failed has not been
     tested. This is the one that found #54: the generated column was reverted
     to a plain one and the suite stayed green, which is how the gap in
     `columns()` became visible rather than theoretical.
  6. **Run the suite without your `.env`.** It is the cheapest audit there is
     and CI is otherwise the only thing that performs it — by accident, on
     whatever happens to break first. `env -u` the credentials, or copy the
     tree somewhere without a dotenv, before the pipeline tells you.
  5. **Where two components must agree about a value, do not let the test
     supply it to both.** Round-trip through the real carrier instead — write
     the row, read it back, and let the second component look the value up the
     way it will in production. #57's ids agreed with nothing and the test
     could not tell, because the test was the only thing that knew them.
  4. **A check that iterates must count what it iterated over, and something
     must assert the count.** #58's regex silently matched nothing and the
     check reported clean. `parametrize` over a discovered file list has the
     same hazard — an empty list is a green run — which is why
     `test_there_are_python_files_to_check` exists in
     `tests/test_lane_boundary.py` and why every new sweep of the tree needs
     its equivalent. **Zero checked and zero failed look identical in a test
     runner.**
  7. **Ask where a guard runs, not only whether it passes.** For each check,
     name the failure it is meant to catch and the step that would produce it -
     if the check runs after that step, it is documentation, not a guard. The
     question is cheap and nothing else asks it: a guard three steps too late
     is green, correct, and mutation-checkable, and every one of the six habits
     above passes on it. What it cannot do is fail first, which is the only
     thing that makes a log readable. Cheapest form of the fix is usually to
     give the check the narrowest possible dependencies and move it earlier -
     `test_ci_workflow.py` needs a YAML parser and a file, so it now runs
     before the install rather than inside the suite that depends on it.

  8. **A guard that enumerates attributes covers the attributes somebody
     thought of, and the list grows by incident.** Habit 7 asks WHERE a guard
     runs; this asks WHAT it looks at. Both are properties of the guard rather
     than of the code it guards, which is why the seven habits above pass on
     them.

     The worked example is `columns()` in `tests/test_migrations.py`, the
     equivalence check between the migration chain and `contract/tables.sql`.
     It selects six attributes:

         table_name, column_name, data_type, is_nullable, column_default,
         is_generated, generation_expression

     The last two were added after #54 — a GENERATED column created plain, 21
     tests green — so the list has already grown once, by incident. What it
     still cannot see is **the parameters of a type rather than the type**:
     `character_maximum_length`, `numeric_precision`, `numeric_scale`,
     collation, identity. `information_schema` reports `numeric(12,6)` and
     `numeric(10,2)` both as `data_type = 'numeric'`, so they compare EQUAL.

     **That gap is live rather than latent, and it is on the prices.**
     `model_version.price_in` is `numeric(12,6)`, `batch_discount` is
     `numeric(4,3)`; a migration declaring either at a different precision
     passes this check. Width is the harmless half of the same blindness and is
     currently unreachable — every column in `contract/` is `text` (checked for
     `varchar`, `char(`, `character varying`: zero matches), which is also why
     the id-length guard is a test over `stable_id` and not a column type.
     `tests/test_ids.py` holds both halves.

     The habit: when a guard compares a list of properties, ask what the thing
     being compared HAS that the list omits — and write the omission down beside
     the guard, because the next person to extend it will extend it by incident
     too.

Owned by neither lane, like `test_queries_contract.py` — it describes how both
lanes write tests, and it breaks for both.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENV_TEST = ROOT / ".env.test"

ALLOW_MISSING = "ALLOW_MISSING_TEST_DB"
DSN_VAR = "TEST_DATABASE_URL"

#: Written by scripts/dev-postgres.ps1, in its own schema so that it survives
#: the DROP SCHEMA public CASCADE the fixture runs on every test.
SENTINEL = "modelboard_meta.disposable"

_override_used = False


# ── resolving the DSN ─────────────────────────────────────────────────────


def _from_env_test() -> str | None:
    """Read TEST_DATABASE_URL out of .env.test, if the bring-up script wrote one.

    Deliberately not python-dotenv: this must work before any dependency is
    importable, and it is four lines.
    """
    if not ENV_TEST.exists():
        return None
    # utf-8-sig, not utf-8: Windows PowerShell 5.1's `Set-Content -Encoding
    # utf8` writes a BOM, which would otherwise make the first key parse as
    # "﻿TEST_DATABASE_URL" and silently fail to match.
    for line in ENV_TEST.read_text(encoding="utf-8-sig").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == DSN_VAR and value.strip():
            return value.strip()
    return None


def test_database_url() -> str | None:
    """The environment wins; .env.test is the convenience fallback."""
    return os.getenv(DSN_VAR) or _from_env_test()


_MISSING_MESSAGE = f"""
The registry write-path tests have no database, so the write path is NOT covered.

This is a failure rather than a skip on purpose. Six defects in `collect/`
reached a commit because these exact tests skipped silently while the suite
reported green.

To fix it:
    pwsh scripts/dev-postgres.ps1        # creates a disposable local instance
                                         # and writes .env.test

To acknowledge it and move on:
    set {ALLOW_MISSING}=1                # the run will say the write path is uncovered

See docs/dev-database.md.
""".strip()


# ── the three safety layers ───────────────────────────────────────────────


class UnsafeTestDatabase(RuntimeError):
    """The target is not a database this suite is allowed to destroy."""


def assert_safe_target(dsn: str) -> None:
    """Layers 1 and 2, checked **before** a connection is opened.

    Ordering is deliberate. These two need no database, so a DSN pointing at
    RDS is rejected without ever authenticating against it. Layered so the
    message matches the mistake: somebody who pointed TEST_DATABASE_URL at a
    real server should be told "this is not localhost", not "no sentinel
    table found", which reads like a setup problem rather than the near miss
    it is.
    """
    parts = urlsplit(dsn)

    if parts.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise UnsafeTestDatabase(
            f"Refusing to run destructive tests against {parts.hostname!r}. "
            f"These tests DROP SCHEMA public CASCADE, and {DSN_VAR} must point "
            "at a local disposable instance. See docs/dev-database.md."
        )

    dbname = parts.path.lstrip("/")
    if not dbname.endswith("_test"):
        raise UnsafeTestDatabase(
            f"Refusing to run destructive tests against database {dbname!r}: "
            "the name must end with '_test'. These tests DROP SCHEMA public "
            "CASCADE. See docs/dev-database.md."
        )


def assert_disposable(conn: Any, dsn: str) -> None:
    """Layer 3, the one that actually works, checked once connected.

    Layers 1 and 2 are guessable: somebody runs a local proxy, or names a
    real database `modelboard_test`. The sentinel requires a deliberate act,
    and it records the DSN it was created for, so copying the table into a
    real database to unblock yourself does not work either.

    Callers must run `assert_safe_target` first; this re-runs it so the
    function is safe on its own.
    """
    assert_safe_target(dsn)

    marked = conn.execute("SELECT to_regclass(%s) IS NOT NULL", (SENTINEL,)).fetchone()
    if not (marked and marked[0]):
        raise UnsafeTestDatabase(
            f"Refusing to run destructive tests against {dsn}: no {SENTINEL} "
            "table, so this instance was not created by scripts/dev-postgres.ps1. "
            "These tests DROP SCHEMA public CASCADE. If this really is a "
            "throwaway database, run the script against it rather than creating "
            "the table by hand."
        )

    rows = conn.execute(f"SELECT dsn FROM {SENTINEL}").fetchall()  # noqa: S608
    if not any(_same_target(dsn, recorded[0]) for recorded in rows):
        raise UnsafeTestDatabase(
            f"Refusing to run destructive tests against {dsn}: the {SENTINEL} "
            f"mark was created for a different target ({[r[0] for r in rows]}). "
            "A sentinel copied into another database does not make that "
            "database disposable."
        )


def _same_target(left: str, right: str) -> bool:
    """Compare host, port and database name, ignoring credentials and options."""
    a, b = urlsplit(left), urlsplit(right)
    return (a.hostname, a.port, a.path) == (b.hostname, b.port, b.path)


# ── fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def test_dsn() -> str:
    """The DSN for destructive tests, or a loud failure explaining its absence."""
    global _override_used

    dsn = test_database_url()
    if dsn:
        return dsn

    if os.getenv(ALLOW_MISSING):
        _override_used = True
        pytest.skip(
            f"WRITE PATH NOT COVERED: no {DSN_VAR}, and {ALLOW_MISSING} is set. "
            "These tests were not run.",
            allow_module_level=True,
        )

    pytest.fail(_MISSING_MESSAGE, pytrace=False)
    raise AssertionError("unreachable")  # pragma: no cover


# ── the blog parse path's optional dependencies ───────────────────────────
#
# `feedparser` and `trafilatura` are needed by exactly one module,
# `collect/adapters/blog/parse.py`. Without them installed, the four test
# modules that genuinely parse feeds raised at import time, pytest reported
# `Interrupted: 5 errors during collection`, and NOTHING RAN — six hundred
# tests with no relationship to feed parsing, silently not executed.
#
# So those four skip instead, and say so loudly. Same reasoning as the
# database banner above and the same danger: a skip reads as success, so an
# uncovered path that announces itself in the summary is the only acceptable
# version of one.

FEED_LIBRARIES = ("feedparser", "trafilatura")
_feed_skip_used = False


def missing_feed_libraries() -> list[str]:
    """Which of the blog parse path's libraries are not installed."""
    from importlib.util import find_spec

    missing = []
    for name in FEED_LIBRARIES:
        try:
            found = find_spec(name) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            found = False
        if not found:
            missing.append(name)
    return missing


def require_feed_libraries() -> None:
    """Skip the calling module if the blog parse path cannot be imported.

    Called ABOVE the imports it guards, which is why those imports sit below
    it rather than at the top of the file: the point is to skip before the
    ImportError, not to catch one afterwards.
    """
    missing = missing_feed_libraries()
    if not missing:
        return

    global _feed_skip_used
    _feed_skip_used = True
    pytest.skip(
        f"BLOG PARSE PATH NOT COVERED: {', '.join(missing)} not installed. "
        "These tests were not run.",
        allow_module_level=True,
    )


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """Say it in the summary, not only in a skip reason nobody reads.

    Skip reasons need `-rs` to show. An override that hides its own
    consequence is how the next set of defects gets through.
    """
    if _override_used:
        terminalreporter.write_sep("=", "WRITE PATH NOT COVERED", red=True, bold=True)
        terminalreporter.write_line(
            f"  The registry write-path tests did not run: {ALLOW_MISSING} is set "
            f"and {DSN_VAR} is unset."
        )
        terminalreporter.write_line(
            "  A green result here does NOT mean the database write path works. "
            "Run scripts/dev-postgres.ps1."
        )

    if _feed_skip_used:
        terminalreporter.write_sep("=", "BLOG PARSE PATH NOT COVERED", red=True, bold=True)
        terminalreporter.write_line(
            f"  Not installed: {', '.join(missing_feed_libraries())}. The blog "
            "feed parsing and fetch tests did not run."
        )
        terminalreporter.write_line(
            "  A green result here does NOT mean the blog adapter works — and "
            "blogs are the only positive-evidence channel. Run: "
            "pip install -e '.[blog]'  (or the project's full dev install)."
        )
