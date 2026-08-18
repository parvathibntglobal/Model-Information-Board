"""`job_run`: the row exists before the work, and two states never collapse.

The load-bearing tests are the ones separating **did not finish** from
**ran and raised**. A killed process cannot write its own failure, so the first
is carried by an absence — and a reader that folds them together has thrown away
which repair to do: find out why the process died, or read the stage's error.
"""

from __future__ import annotations

import pytest

from collect.db import connect, schema_sql
from collect.ops.ledger import (
    ERROR,
    OK,
    REFUSED,
    close_run,
    last_run,
    open_run,
    unfinished,
)
from tests.conftest import assert_disposable, assert_safe_target


@pytest.fixture
def ledger(test_dsn):
    """A disposable database with the contract schema applied.

    Same three guards as every other write-path fixture — this drops the schema
    it points at, and `TEST_DATABASE_URL` is separate from `DATABASE_URL`
    precisely because a variable that can wipe a working database on a typo
    eventually will.
    """
    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        connection.execute(schema_sql())
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


# ── the row exists before the work ───────────────────────────────────────


def test_the_row_is_written_before_the_stage_does_anything(ledger):
    """A row written only on success leaves nothing when a process is killed,
    and a night with no rows reads as a night that never started."""
    run = open_run(ledger, "sweep-github")
    row = ledger.execute(
        "SELECT stage, finished_at, outcome FROM job_run WHERE id = %s", (run.id,)
    ).fetchone()
    assert row[0] == "sweep-github"
    assert row[1] is None
    assert row[2] is None


def test_an_open_row_survives_the_callers_rollback(ledger):
    """A stage that rolls back must still leave evidence that it ran."""
    run = open_run(ledger, "triage")
    ledger.rollback()
    assert ledger.execute(
        "SELECT count(*) FROM job_run WHERE id = %s", (run.id,)
    ).fetchone()[0] == 1


# ── the two states, and the constraint that keeps them apart ─────────────


def test_an_unfinished_run_is_not_a_failed_one(ledger):
    """The distinction the whole table is arranged around."""
    killed = open_run(ledger, "sweep-blogs")
    raised = open_run(ledger, "sweep-reddit")
    close_run(ledger, raised, outcome=ERROR, detail="ConnectionError: refused")

    still_open = {stage for _id, stage, _at in unfinished(ledger)}
    assert still_open == {"sweep-blogs"}
    assert killed.id not in {r[0] for r in []}  # readability: killed stays open

    outcomes = dict(
        ledger.execute("SELECT stage, outcome FROM job_run").fetchall()
    )
    assert outcomes["sweep-blogs"] is None, "killed: no outcome, not 'error'"
    assert outcomes["sweep-reddit"] == ERROR


def test_the_schema_refuses_an_outcome_without_a_finish(ledger):
    """`job_run_finish_ck`. A row cannot claim it concluded and not say when."""
    import psycopg

    with pytest.raises(psycopg.errors.CheckViolation), ledger.transaction():
        ledger.execute(
            "INSERT INTO job_run (id, stage, outcome, pipeline_version) "
            "VALUES (%s, %s, %s, %s)",
            ("jr_x", "triage", OK, "test"),
        )


def test_the_schema_refuses_a_finish_without_an_outcome(ledger):
    """The other direction of the same constraint."""
    import psycopg

    with pytest.raises(psycopg.errors.CheckViolation), ledger.transaction():
        ledger.execute(
            "INSERT INTO job_run (id, stage, finished_at, pipeline_version) "
            "VALUES (%s, %s, now(), %s)",
            ("jr_y", "triage", "test"),
        )


def test_the_outcome_vocabulary_is_the_chains(ledger):
    """`ok | refused | error`, verbatim from `collect/ops/chain.py`.

    The first CHECK said `failed` and would have needed a writer translating
    between two words for one concept. Migration 20260818T1520 corrected it.
    """
    import psycopg

    from collect.ops import chain

    assert {OK, REFUSED, ERROR} == {chain.OK, chain.REFUSED, chain.ERROR}
    with pytest.raises(psycopg.errors.CheckViolation), ledger.transaction():
        ledger.execute(
            "INSERT INTO job_run (id, stage, finished_at, outcome, pipeline_version) "
            "VALUES (%s, %s, now(), %s, %s)",
            ("jr_z", "triage", "failed", "test"),
        )


# ── counts stay NULL where nothing was counted ───────────────────────────


def test_a_refused_stage_records_null_counts_not_zero(ledger):
    """Rule 6. A stage that refused counted nothing; 0 asserts it counted."""
    run = open_run(ledger, "assemble-flatten")
    close_run(ledger, run, outcome=REFUSED, detail="not built")
    row = ledger.execute(
        "SELECT items_in, items_out FROM job_run WHERE id = %s", (run.id,)
    ).fetchone()
    assert row == (None, None)


def test_counts_are_recorded_when_a_stage_actually_counted(ledger):
    run = open_run(ledger, "triage")
    close_run(ledger, run, outcome=OK, counts={"items_in": 1925, "items_out": 565})
    row = ledger.execute(
        "SELECT items_in, items_out FROM job_run WHERE id = %s", (run.id,)
    ).fetchone()
    assert row == (1925, 565)


# ── the question the three findings needed ───────────────────────────────


def test_last_run_is_none_for_a_stage_that_has_never_run(ledger):
    """"Has this ever run against THIS database" — a query, not an audit.

    `in_window`, `mark_swept` and the three writers greping as wired each cost a
    manual investigation to establish exactly this.
    """
    assert last_run(ledger, "never-existed") is None


def test_last_run_reports_a_refusal_rather_than_hiding_it(ledger):
    """A stage that ran and refused HAS run. The row is the evidence, and it
    exists whether or not the stage succeeded — which is why the question is
    answerable at all."""
    run = open_run(ledger, "poll-registry")
    close_run(ledger, run, outcome=REFUSED, detail="no OpenRouter key")
    answer = last_run(ledger, "poll-registry")
    assert answer is not None
    assert answer[1] == REFUSED
