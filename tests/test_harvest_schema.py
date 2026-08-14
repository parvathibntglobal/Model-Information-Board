"""FR-11: truncation is recorded, and the record says who did the truncating.

`harvest_run.truncated_by` is a closed set because FR-11's acceptance is a
check, and a check over arbitrary strings is not one.

Requires a database. See docs/dev-database.md.
"""

from __future__ import annotations

import pytest

from tests.conftest import assert_disposable, assert_safe_target

#: Caps we chose. Raising a budget moves these.
OURS = ("query-budget", "time-budget", "extraction-budget")

#: The platform stopping us. Raising a budget does not move these; only a
#: narrower query or a different access path does.
THEIRS = ("rate-limit", "result-ceiling")


@pytest.fixture
def conn(test_dsn):
    from collect.db import apply_schema, connect

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.execute(
            "INSERT INTO source "
            "  (id, platform, base_trust, tos_notes, provenance, "
            "   terms_ruling, terms_checked_on, terms_evidence) "
            "VALUES ('github', 'github', 0.95, 'fixture row: see contract/sources.yaml', "
            "        'seed', 'github-api-terms', DATE '2026-08-13', "
            "        '{\"access_path\": \"api\"}'::jsonb)"
        )
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _insert(connection, run_id: str, truncated_by: str | None):
    connection.execute(
        "INSERT INTO harvest_run (id, source_id, query_key, truncated_by, pipeline_version) "
        "VALUES (%s, 'github', 'q', %s, 'collect-0.1.0')",
        (run_id, truncated_by),
    )


@pytest.mark.parametrize("value", OURS + THEIRS)
def test_every_documented_reason_is_accepted(conn, value: str):
    _insert(conn, f"run_{value}", value)
    conn.commit()


def test_a_completed_harvest_records_no_reason(conn):
    _insert(conn, "run_complete", None)
    conn.commit()
    assert (
        conn.execute("SELECT truncated_by FROM harvest_run WHERE id='run_complete'").fetchone()[0]
        is None
    )


@pytest.mark.parametrize("value", ["made-up", "budget", "RESULT-CEILING", ""])
def test_an_undocumented_reason_is_refused(conn, value: str):
    """An unconstrained column is how a sixth reason gets added later without
    the coverage page knowing it exists."""
    import psycopg

    with pytest.raises(psycopg.errors.CheckViolation):
        _insert(conn, "run_bad", value)
    conn.rollback()


def test_the_platform_ceiling_has_somewhere_to_go(conn):
    """The gap this commit closes.

    GitHub Search returns at most 1,000 results per query. Measured against
    the real API, 9 of 10 template queries exceeded it, median 13,038. That
    is truncation by FR-11's definition and had no value to record.
    """
    _insert(conn, "run_ceiling", "result-ceiling")
    conn.commit()
    assert (
        conn.execute("SELECT truncated_by FROM harvest_run WHERE id='run_ceiling'").fetchone()[0]
        == "result-ceiling"
    )


def test_ours_and_theirs_are_both_representable(conn):
    """The distinction the coverage page renders differently.

    "We decided not to look further" and "we were not allowed to" are
    opposite statements about the same missing data.
    """
    for index, value in enumerate(OURS + THEIRS):
        _insert(conn, f"run_{index}", value)
    conn.commit()

    recorded = {
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT truncated_by FROM harvest_run WHERE truncated_by IS NOT NULL"
        ).fetchall()
    }
    assert recorded == set(OURS) | set(THEIRS)
