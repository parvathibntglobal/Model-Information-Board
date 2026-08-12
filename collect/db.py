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


def reset_schema(conn: psycopg.Connection[Any], *, environment: str) -> None:
    """Drop and recreate the public schema. Development only.

    Refuses outside development, because a helper that can wipe production
    on a typo eventually will.
    """
    if environment != "development":
        raise RuntimeError(
            f"reset_schema refuses to run with ENVIRONMENT={environment!r}. "
            "This drops every table."
        )
    conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    apply_schema(conn)


def table_exists(conn: psycopg.Connection[Any], name: str) -> bool:
    row = conn.execute("SELECT to_regclass(%s) IS NOT NULL", (name,)).fetchone()
    return bool(row and row[0])
