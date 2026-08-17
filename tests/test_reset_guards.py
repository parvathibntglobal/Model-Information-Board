"""`reset_schema`'s three layers. Requires a database.

`TEST_DATABASE_URL` had four guards and `DATABASE_URL` had none, on the one
function in `collect/` that destroys data. These cover the two that were added.

Per `tests/conftest.py`: each guard is also exercised in the direction that
would let it through, so a test that has never failed is not the only evidence
it works. See `test_the_host_guard_is_not_reading_the_dsn_argument` in
particular — that is the property the guard exists for.
"""

from __future__ import annotations

import pytest

from collect.db import LOCAL_HOSTS, UnsafeReset, _is_local, apply_schema, connect, reset_schema
from tests.conftest import assert_disposable, assert_safe_target


@pytest.fixture
def conn(test_dsn):
    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


# ── layer 1: the host, read from the connection ──────────────────────────


@pytest.mark.parametrize("host", [*LOCAL_HOSTS, "", None, "/var/run/postgresql"])
def test_local_hosts_and_sockets_are_local(host):
    assert _is_local(host)


@pytest.mark.parametrize("host", [
    "52.17.75.29", "db.internal", "10.0.0.5", "rds.amazonaws.com",
    "localhost.evil.com", "127.0.0.1.nip.io",
])
def test_everything_else_is_not(host):
    """`localhost.evil.com` is the one worth having a case for.

    A substring or `startswith` test would pass it. Membership does not.
    """
    assert not _is_local(host)


def test_the_host_guard_is_not_reading_the_dsn_argument(conn, monkeypatch):
    """THE PROPERTY THE GUARD EXISTS FOR.

    The host comes from `conn.info`, which describes the socket that is actually
    open. A guard reading a DSN string could be handed a different URL than the
    one connected — which is the same defect shape as asserting a message
    mentions a claim rather than that the claim is true (#21).

    Simulated by making the OPEN connection report a remote host while every
    argument stays local. The refusal must still fire.
    """
    class RemoteInfo:
        host = "52.17.75.29"

    monkeypatch.setattr(type(conn), "info", property(lambda self: RemoteInfo()))
    with pytest.raises(UnsafeReset, match="not localhost"):
        reset_schema(conn, environment="development")


def test_the_host_refusal_does_not_blame_the_environment(conn, monkeypatch):
    """Layer 1 before layer 2, so the message names the real objection."""
    class RemoteInfo:
        host = "db.internal"

    monkeypatch.setattr(type(conn), "info", property(lambda self: RemoteInfo()))
    with pytest.raises(UnsafeReset) as excinfo:
        reset_schema(conn, environment="staging")
    message = str(excinfo.value)
    assert "not localhost" in message
    assert "ENVIRONMENT was not consulted" in message, (
        "somebody pointed at a real server must not be told 'wrong environment'"
    )


# ── layer 2: the environment ─────────────────────────────────────────────


@pytest.mark.parametrize("environment", ["staging", "production", "Development", ""])
def test_a_non_development_environment_refuses(conn, environment):
    with pytest.raises(UnsafeReset, match="ENVIRONMENT"):
        reset_schema(conn, environment=environment)


# ── layer 3: the rows ────────────────────────────────────────────────────


def test_an_empty_local_development_database_resets(conn):
    """The direction that must still work, or the guards are just a wall."""
    reset_schema(conn, environment="development")
    conn.commit()
    remaining = conn.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
    ).fetchone()
    assert remaining[0] > 0, "the schema was reapplied"


def test_a_single_row_anywhere_refuses(conn):
    """The habit case: a local instance somebody loaded, then reset."""
    conn.execute(
        "INSERT INTO capability (key, failure_mode, version) "
        "VALUES ('tool_calling.schema_accuracy', 'loud', 'v1')"
    )
    conn.commit()
    with pytest.raises(UnsafeReset) as excinfo:
        reset_schema(conn, environment="development")
    message = str(excinfo.value)
    assert "hold rows" in message
    assert "capability (1 rows)" in message, "the message names what would be lost"


def test_the_row_guard_counts_rather_than_trusting_reltuples(conn):
    """`reltuples` is -1 until the first ANALYZE, so it cannot be the test.

    A guard reading the estimate would let a freshly-loaded table through — the
    rows are there and the statistics are not. Absence of an estimate is not
    absence of rows (rule 6).
    """
    conn.execute(
        "INSERT INTO capability (key, failure_mode, version) "
        "VALUES ('format.structured_output', 'loud', 'v1')"
    )
    conn.commit()
    estimate = conn.execute(
        "SELECT reltuples::bigint FROM pg_class WHERE relname = 'capability'"
    ).fetchone()[0]
    assert estimate <= 0, "no ANALYZE has run, so the estimate is useless here"
    with pytest.raises(UnsafeReset, match="hold rows"):
        reset_schema(conn, environment="development")


def test_the_refusal_is_typed_so_a_caller_can_tell_it_apart(conn):
    """Refused and failed-halfway need different responses."""
    conn.execute(
        "INSERT INTO capability (key, failure_mode, version) "
        "VALUES ('reasoning.multistep', 'silent', 'v1')"
    )
    conn.commit()
    with pytest.raises(UnsafeReset):
        reset_schema(conn, environment="development")
    assert issubclass(UnsafeReset, RuntimeError), "still catchable as before"
