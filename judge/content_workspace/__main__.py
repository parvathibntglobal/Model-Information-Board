"""`python -m judge.content_workspace setup | seed | status`

setup   apply the workspace's migrations to CONTENT_WORKSPACE_DATABASE_URL
seed    add platforms and notes from config/seed_platforms.yaml that the
        database does not hold yet (never overwrites an edited note)
status  applied migrations and row counts
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

from judge.content_workspace import db, store


def main(argv: list[str]) -> int:
    load_dotenv()
    if len(argv) != 1 or argv[0] not in ("setup", "seed", "status"):
        print(__doc__)
        return 2
    conn = db.connect()
    try:
        if argv[0] == "setup":
            applied = db.migrate(conn)
            print(f"applied {len(applied)} migration(s): {', '.join(applied) or 'none pending'}")
        elif argv[0] == "seed":
            if db.pending(conn):
                conn.rollback()
                print("migrations are pending: run `setup` first")
                return 1
            added = store.load_seed(conn)
            conn.commit()
            print(f"added {added['platforms']} platform(s) and {added['notes']} note(s)")
        else:
            pending = [p.name for p in db.pending(conn)]
            print(f"pending migrations: {', '.join(pending) or 'none'}")
            if not pending:
                for table in ("cw_platform", "cw_note", "cw_note_edit", "cw_draft",
                              "cw_check_run"):
                    n = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                    print(f"{table}: {n}")
            conn.rollback()
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
