"""Postgres access.

A connection helper and a schema applier. No ORM, no migration framework —
`contract/tables.sql` is the schema, and it is shared code: read it, never
rewrite it from here.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from collect.config import TABLES_SQL, settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    import psycopg


class DatabaseNotConfigured(RuntimeError):
    """DATABASE_URL is unset. Nothing that touches Postgres can run."""


def schema_sql() -> str:
    """The contract schema, verbatim."""
    return TABLES_SQL.read_text(encoding="utf-8")


def connect(url: str | None = None) -> psycopg.Connection[Any]:
    """Open a connection. Caller owns the transaction."""
    import psycopg

    dsn = url or settings().database_url
    if not dsn:
        raise DatabaseNotConfigured(
            "DATABASE_URL is not set. Copy .env.example to .env and fill it in."
        )
    return psycopg.connect(dsn)


@contextmanager
def transaction(url: str | None = None) -> Iterator[psycopg.Connection[Any]]:
    """Connect, run, commit — or roll back and re-raise."""
    conn = connect(url)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def apply_schema(conn: psycopg.Connection[Any]) -> None:
    """Create every table in `contract/tables.sql`.

    Fails loudly if objects already exist. That is deliberate: silently
    tolerating a partially-applied schema is how two environments drift.
    """
    conn.execute(schema_sql())


#: Hosts `reset_schema` will destroy. An empty host or a path is a unix socket,
#: which is on this machine by definition.
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


class UnsafeReset(RuntimeError):
    """`reset_schema` refused. The target is not something to drop."""


def _is_local(host: str | None) -> bool:
    if not host:
        return True  # unix socket: same machine
    return host.startswith("/") or host in LOCAL_HOSTS


def reset_schema(conn: psycopg.Connection[Any], *, environment: str) -> None:
    """Drop and recreate the public schema. Local, empty databases only.

    THREE LAYERS, CHEAPEST AND MOST FUNDAMENTAL FIRST. `tests/conftest.py` has
    had layers like these since the six defects that a green suite hid; this
    path had none at all, which was the asymmetry: `TEST_DATABASE_URL` was
    guarded four ways and `DATABASE_URL` not once.

    1. HOST, READ FROM `conn.info` AND NOT FROM A DSN A CALLER PASSED.
       That is the property that makes it a guard rather than a courtesy: it
       describes the socket that is actually open, so handing in a different URL
       than the one connected cannot defeat it. Checked first so the message
       names the real objection - somebody pointed at a real server should be
       told "this is not localhost", not "wrong environment", which reads like a
       config problem rather than the near miss it is.

    2. ENVIRONMENT, unchanged, and deliberately not first. It is a string
       anyone can set, so it cannot be the outermost guard on the one function
       here that destroys data.

    3. ROWS. A reset on an empty database is recoverable; on a populated one it
       is the incident. This also catches the ordinary case the other two miss
       entirely - a local instance in development that somebody loaded and then
       reset out of habit.

    Raises:
        UnsafeReset: on any of the three. Never a bare RuntimeError, so a caller
            can distinguish "refused" from "the drop failed halfway".
    """
    host = conn.info.host
    if not _is_local(host):
        raise UnsafeReset(
            f"reset_schema refuses against host {host!r}: this is not localhost. "
            "It runs DROP SCHEMA public CASCADE. The host is read from the open "
            "connection, not from any DSN passed in, so this cannot be overridden "
            f"by argument. ENVIRONMENT was not consulted (it says {environment!r}) "
            "because a variable anyone can set is not a guard on the destructive "
            "path."
        )

    if environment != "development":
        raise UnsafeReset(
            f"reset_schema refuses to run with ENVIRONMENT={environment!r}. "
            "This drops every table."
        )

    populated = conn.execute(
        """
        SELECT c.relname, c.reltuples::bigint
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'r'
        ORDER BY c.relname
        """
    ).fetchall()
    # reltuples is an estimate and is -1 before the first ANALYZE, so it can
    # only nominate candidates. Absence of an estimate is not absence of rows
    # (rule 6), so every table is counted exactly rather than trusted.
    with_rows: list[tuple[str, int]] = []
    for name, _estimate in populated:
        count = conn.execute(
            f'SELECT count(*) FROM "{name}"'  # noqa: S608 - name from pg_class
        ).fetchone()
        if count and count[0]:
            with_rows.append((name, count[0]))

    if with_rows:
        listed = ", ".join(f"{name} ({n} rows)" for name, n in with_rows[:6])
        more = "" if len(with_rows) <= 6 else f", and {len(with_rows) - 6} more"
        raise UnsafeReset(
            f"reset_schema refuses: {len(with_rows)} table(s) in this database "
            f"hold rows - {listed}{more}. This drops every table. An empty "
            "database is recoverable from contract/tables.sql; a populated one "
            "is not. Empty it deliberately, or use scripts/dev-postgres.ps1 "
            "-Destroy for a throwaway instance."
        )

    conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    apply_schema(conn)


def table_exists(conn: psycopg.Connection[Any], name: str) -> bool:
    row = conn.execute("SELECT to_regclass(%s) IS NOT NULL", (name,)).fetchone()
    return bool(row and row[0])
