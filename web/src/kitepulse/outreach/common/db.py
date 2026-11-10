"""Kite Pulse outreach's own database: connect, and refuse MIB's.

Outreach keeps its rows in a SEPARATE Postgres database, named by
`KP_OUTREACH_DATABASE_URL` (local: `kite_pulse_outreach_local`). There is no
fallback to MIB's `DATABASE_URL`: borrowing it silently would put outreach
tables in MIB's database, which ARCHITECTURE.md section 1 rules out.

Two refusals, in the order a mistake would hit them:

1. Before connecting: the DSN names the same host, port and database as
   `DATABASE_URL`. Fails early and says which variable is wrong.
2. After connecting, from the OPEN connection: the database holds one of MIB's
   tables. A DSN can be spelled many ways (an alias, an IP, a proxy); the
   tables cannot, so this is the check that actually holds
   (docs/defect-two-names-for-one-database.md).
"""

from __future__ import annotations

import os
from typing import Any

ENV = "KP_OUTREACH_DATABASE_URL"
MIB_ENV = "DATABASE_URL"

# Tables only MIB's database has. Any one of them means "this is MIB's".
MIB_TABLES = ("document", "claim", "thread_context", "spend_ledger", "schema_migration")

CONNECT_TIMEOUT_SECONDS = 10


class OutreachDbError(RuntimeError):
    pass


def dsn_from_env() -> str:
    dsn = (os.environ.get(ENV) or "").strip()
    if not dsn:
        raise OutreachDbError(
            f"{ENV} is not set. Put the outreach database's URL in .env, e.g. "
            f"{ENV}=postgresql://postgres:<password>@localhost:5432/kite_pulse_outreach_local "
            f"(see .env.example). It never falls back to {MIB_ENV}."
        )
    return dsn


def _target(dsn: str) -> tuple[str, str, str]:
    from psycopg.conninfo import conninfo_to_dict

    parts = conninfo_to_dict(dsn)
    host = (parts.get("host") or "localhost").lower()
    if host in ("127.0.0.1", "::1"):
        host = "localhost"
    return host, str(parts.get("port") or "5432"), str(parts.get("dbname") or "")


def refuse_mib_dsn(dsn: str, mib_dsn: str | None) -> None:
    if mib_dsn and _target(dsn) == _target(mib_dsn):
        raise OutreachDbError(
            f"{ENV} names the same database as {MIB_ENV} ({'/'.join(_target(dsn))}). "
            "Outreach needs its own database; see web/src/kitepulse/outreach/setup_db.py."
        )


def refuse_mib_tables(conn: Any) -> None:
    found = [name for name in MIB_TABLES
             if conn.execute("SELECT to_regclass(%s)", (f"public.{name}",)).fetchone()[0]]
    if found:
        raise OutreachDbError(
            f"database {conn.info.dbname!r} on {conn.info.host}:{conn.info.port} holds MIB "
            f"tables ({', '.join(found)}); outreach refuses to use MIB's database"
        )


def connect(dsn: str | None = None) -> Any:
    """A connection to the outreach database, checked to not be MIB's."""
    import psycopg

    dsn = dsn or dsn_from_env()
    refuse_mib_dsn(dsn, os.environ.get(MIB_ENV))
    conn = psycopg.connect(dsn, connect_timeout=CONNECT_TIMEOUT_SECONDS)
    try:
        refuse_mib_tables(conn)
        conn.rollback()        # the check opened a transaction; start clean
    except BaseException:
        conn.close()
        raise
    return conn
