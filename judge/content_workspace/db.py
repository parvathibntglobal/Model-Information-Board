"""The content workspace's own database: connect, refuse the board's, migrate.

The workspace keeps its rows (notes, drafts, check runs) in a SEPARATE
Postgres database named by `CONTENT_WORKSPACE_DATABASE_URL`, as Kite Pulse
outreach does. They are not evidence, nothing on the board reads them, and
keeping them apart means this feature needs no change to `contract/` and no
migration on the shared staging database. There is no fallback to
`DATABASE_URL`: borrowing it would put workspace tables in the board's
database.

Two refusals, in the order a mistake would hit them:

1. Before connecting: the DSN names the same host, port and database as one
   of the board's (`DATABASE_URL`, `RAILWAY_DATABASE_URL`,
   `STAGING_DATABASE_URL`).
2. After connecting: the database holds one of the board's tables. A DSN can
   be spelled many ways; the tables cannot.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ENV = "CONTENT_WORKSPACE_DATABASE_URL"
BOARD_ENVS = ("DATABASE_URL", "RAILWAY_DATABASE_URL", "STAGING_DATABASE_URL")

# Tables only the board's database has. Any one of them means "this is MIB's".
BOARD_TABLES = ("document", "claim", "thread_context", "spend_ledger", "schema_migration")

MIGRATIONS = Path(__file__).parent / "migrations"
LEDGER = "cw_schema_migration"
CONNECT_TIMEOUT_SECONDS = 10


class WorkspaceDbError(RuntimeError):
    """The workspace database is not configured, or is the board's."""


def dsn_from_env() -> str:
    dsn = (os.environ.get(ENV) or "").strip()
    if not dsn:
        raise WorkspaceDbError(
            f"{ENV} is not set. Create a database for the workspace and put its URL "
            f"in .env, e.g. {ENV}=postgresql://postgres:postgres@localhost:5433/"
            "mib_content_workspace, then run `python -m judge.content_workspace setup`. "
            "It never falls back to the board's DATABASE_URL."
        )
    return dsn


def _target(dsn: str) -> tuple[str, str, str]:
    from psycopg.conninfo import conninfo_to_dict

    parts = conninfo_to_dict(dsn)
    host = (parts.get("host") or "localhost").lower()
    if host in ("127.0.0.1", "::1"):
        host = "localhost"
    return host, str(parts.get("port") or "5432"), str(parts.get("dbname") or "")


def refuse_board_dsn(dsn: str, environ: dict[str, str] | None = None) -> None:
    environ = os.environ if environ is None else environ
    for name in BOARD_ENVS:
        other = (environ.get(name) or "").strip()
        if other and _target(dsn) == _target(other):
            raise WorkspaceDbError(
                f"{ENV} names the same database as {name} ({'/'.join(_target(dsn))}). "
                "The workspace needs its own database."
            )


def refuse_board_tables(conn: Any) -> None:
    found = [name for name in BOARD_TABLES
             if conn.execute("SELECT to_regclass(%s)", (f"public.{name}",)).fetchone()[0]]
    if found:
        raise WorkspaceDbError(
            f"database {conn.info.dbname!r} holds the board's tables ({', '.join(found)}); "
            "the content workspace refuses to use the board's database"
        )


def connect(dsn: str | None = None) -> Any:
    """A connection to the workspace database, checked not to be the board's.
    The caller owns the transaction."""
    import psycopg

    dsn = dsn or dsn_from_env()
    refuse_board_dsn(dsn)
    conn = psycopg.connect(dsn, connect_timeout=CONNECT_TIMEOUT_SECONDS)
    try:
        refuse_board_tables(conn)
        conn.rollback()
    except BaseException:
        conn.close()
        raise
    return conn


def pending(conn: Any) -> list[Path]:
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {LEDGER} ("
        " filename text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
    )
    done = {r[0] for r in conn.execute(f"SELECT filename FROM {LEDGER}").fetchall()}
    return [p for p in sorted(MIGRATIONS.glob("*.sql")) if p.name not in done]


def migrate(conn: Any) -> list[str]:
    """Apply every migration not yet in the ledger, each with its ledger row in
    one transaction. Returns the file names applied."""
    applied = []
    for path in pending(conn):
        with conn.transaction():
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute(f"INSERT INTO {LEDGER} (filename) VALUES (%s)", (path.name,))
        applied.append(path.name)
    conn.commit()
    return applied
