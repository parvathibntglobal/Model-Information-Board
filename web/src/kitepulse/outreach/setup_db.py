"""Create Kite Pulse outreach's database and apply its migrations.

    py -3.12 web/src/kitepulse/outreach/setup_db.py            create if missing, migrate
    py -3.12 web/src/kitepulse/outreach/setup_db.py --status   applied / pending, no change

The database is named by KP_OUTREACH_DATABASE_URL in .env and is NOT MIB's
(common/db.py refuses MIB's, by URL and by its tables). Locally it sits on the
same Postgres server as MIB's, as its own database:

    localhost:5432
    |-- model_information_board_local   MIB, never touched by this script
    `-- kite_pulse_outreach_local       outreach

WHAT IT DOES, in order:

1. If the database does not exist and its host is local, CREATE DATABASE it
   (connecting to the server's `postgres` database to do so). A missing
   database on any other host is an error: creating databases on a shared
   server is a person's decision, not a script's.
2. Create the ledger, kp_outreach_migration, if missing.
3. Apply each file in migrations/ not yet in the ledger, in filename order.
   The file and its ledger row go in ONE transaction, so a file can never be
   applied without being recorded, or recorded without being applied.

A file already applied whose content has changed STOPS the run, and so does a
ledger row whose file is gone. Neither is re-hashed or skipped: a changed
applied migration means this database and the file disagree, and finding out
how is an investigation (CLAUDE.md, "resolving a mismatch").
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]  # outreach -> kitepulse -> src -> web -> repo

for _p in (str(HERE), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import db  # noqa: E402

MIGRATIONS_DIR = HERE / "migrations"
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")

LEDGER_SQL = """
CREATE TABLE IF NOT EXISTS kp_outreach_migration (
  filename   text        PRIMARY KEY,
  sha256     text        NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now()
)
"""


@dataclass(frozen=True)
class Migration:
    filename: str
    sha256: str
    sql: str


def migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    files = sorted(directory.glob("*.sql"))
    if not files:
        raise db.OutreachDbError(f"no migrations in {directory}")
    return [Migration(f.name, hashlib.sha256(f.read_bytes()).hexdigest(),
                      f.read_text(encoding="utf-8")) for f in files]


def pending(files: list[Migration], ledger: dict[str, str]) -> list[Migration]:
    """Files not yet applied. Raises if the ledger and the files disagree."""
    on_disk = {m.filename: m for m in files}
    gone = sorted(set(ledger) - set(on_disk))
    if gone:
        raise db.OutreachDbError(
            f"applied but no longer in {MIGRATIONS_DIR.name}/: {', '.join(gone)}. "
            "Restore the file; never delete an applied migration.")
    changed = [m.filename for m in files if m.filename in ledger
               and ledger[m.filename] != m.sha256]
    if changed:
        raise db.OutreachDbError(
            f"applied, and the file has changed since: {', '.join(changed)}. "
            "Undo the edit and add a new migration instead; nothing was applied.")
    return [m for m in files if m.filename not in ledger]


def _database_exists(dsn: str) -> bool:
    import psycopg
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    name = conninfo_to_dict(dsn).get("dbname")
    with psycopg.connect(make_conninfo(dsn, dbname="postgres"), autocommit=True,
                         connect_timeout=db.CONNECT_TIMEOUT_SECONDS) as conn:
        return conn.execute("SELECT 1 FROM pg_database WHERE datname = %s",
                            (name,)).fetchone() is not None


def _create_database(dsn: str) -> str:
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    parts = conninfo_to_dict(dsn)
    name, host = parts.get("dbname"), (parts.get("host") or "localhost")
    if not name:
        raise db.OutreachDbError(f"{db.ENV} names no database")
    if host not in LOCAL_HOSTS:
        raise db.OutreachDbError(
            f"database {name!r} does not exist on {host}, which is not local. Create it "
            "there by hand (a person's decision on a shared server), then run this again.")
    with psycopg.connect(make_conninfo(dsn, dbname="postgres"), autocommit=True,
                         connect_timeout=db.CONNECT_TIMEOUT_SECONDS) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8'").format(sql.Identifier(name)))
    return name


def _ledger(conn) -> dict[str, str]:
    return dict(conn.execute("SELECT filename, sha256 FROM kp_outreach_migration").fetchall())


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="setup_db.py", description=__doc__.split("\n")[0])
    parser.add_argument("--status", action="store_true",
                        help="show applied and pending migrations; change nothing")
    args = parser.parse_args(argv)

    from collect.config import settings  # loads .env; the only collect/ import

    settings()
    try:
        dsn = db.dsn_from_env()
        db.refuse_mib_dsn(dsn, os.environ.get(db.MIB_ENV))
        files = migrations()

        if not _database_exists(dsn):
            if args.status:
                print(f"database does not exist yet; {len(files)} migration(s) pending")
                return 0
            print(f"created database {_create_database(dsn)}")

        with db.connect(dsn) as conn:
            print(f"database {conn.info.dbname} on {conn.info.host}:{conn.info.port}")
            if args.status:
                exists = conn.execute(
                    "SELECT to_regclass('kp_outreach_migration')").fetchone()[0]
                ledger = _ledger(conn) if exists else {}
                todo = pending(files, ledger)
                for m in files:
                    print(f"  {'pending' if m in todo else 'applied'}  {m.filename}")
                return 0

            with conn.transaction():
                conn.execute(LEDGER_SQL)
            todo = pending(files, _ledger(conn))
            for m in todo:
                with conn.transaction():
                    conn.execute(m.sql)
                    conn.execute("INSERT INTO kp_outreach_migration (filename, sha256) "
                                 "VALUES (%s, %s)", (m.filename, m.sha256))
                print(f"  applied  {m.filename}")
            print(f"{len(todo)} applied, {len(files) - len(todo)} already in place")
    except db.OutreachDbError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
