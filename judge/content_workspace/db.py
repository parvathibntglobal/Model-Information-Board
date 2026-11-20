"""The content workspace's database: the BOARD'S (anooj, 2026-11-19).

The workspace's tables (cw_*) live in the board's database, created by the
board's own migration (contract/migrations/20261119T1200_content_workspace.sql,
applied by `python -m collect.cli db migrate`) and declared in
contract/tables.sql and contract/column_states.yaml like every other table.
Until 2026-11-19 they lived in a separate database with its own ledger; that
database, its variable and its runner are gone.

They are still NOT evidence: nothing on the board's pages or pipeline reads a
cw_* table, and no cw_* table references a board table.

Connecting is judge/'s own path to the board (DATABASE_URL, the timeout and
`DatabaseNotConfigured` from judge/store/claims.py), never collect/'s: judge/
does not import collect/ (tests/test_lane_boundary.py). A missing DATABASE_URL
refuses rather than guessing. A workspace table that is missing means the migration has not run on
this database, and `missing_tables` says which, by name (rule 4: an absence we
can explain is never reported as an empty workspace).

Writes through the CLI are gated by judge/content_workspace/__main__.py (the
writeguard); the web app writes through its own connection like every admin
page.
"""

from __future__ import annotations

import os
from typing import Any

#: Every table the workspace owns, created by 20261119T1200_content_workspace.sql.
TABLES = ("cw_platform", "cw_note", "cw_note_edit", "cw_draft", "cw_check_run",
          "cw_writer_run", "cw_result", "cw_tick", "cw_media")

MIGRATE_HINT = ("run `python -m collect.cli db migrate` on this database "
                "(contract/migrations/20261119T1200_content_workspace.sql)")


def connect(dsn: str | None = None) -> Any:
    """A connection to the board's database (DATABASE_URL unless `dsn` is
    given). The caller owns the transaction."""
    import psycopg

    from judge.store.claims import CONNECT_TIMEOUT_SECONDS, DatabaseNotConfigured

    url = dsn or os.getenv("DATABASE_URL")
    if not url:
        raise DatabaseNotConfigured(
            "DATABASE_URL is unset. The content workspace's tables are in the board's "
            "database; refusing to guess at a connection.")
    return psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT_SECONDS)


def missing_tables(conn: Any) -> list[str]:
    """The workspace tables this database does not have, in TABLES order."""
    return [t for t in TABLES
            if conn.execute("SELECT to_regclass(%s)", (f"public.{t}",)).fetchone()[0] is None]
