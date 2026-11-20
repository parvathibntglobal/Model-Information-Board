"""`python -m judge.content_workspace <command>`

Its tables are cw_* tables in the BOARD'S database (DATABASE_URL), created by
`python -m collect.cli db migrate` (contract/migrations/
20261119T1200_content_workspace.sql). There is no separate setup any more.

THE WRITE GATE. `seed`, `ingest` and `media-add` write (cw_* tables only, never
a board table). Each runs judge/writeguard.py's check first, the way
scripts/retriage_seated_models.py --apply does: ENVIRONMENT=development with a
DATABASE_URL that is not this machine is refused. `--development-write` is the
deliberate way past it from a development machine. No fixture check is needed
on that path: a cw_* write cannot put a seeded or hand-curated board row
anywhere. `status`, `material` and `draft-json` only read and are not gated.

seed                  add platforms and notes from config/seed_platforms.yaml that the
                      database does not hold yet (never overwrites an edited note)
status                row counts of every cw_* table
material DRAFT [--instructions TEXT] [--out FILE]
                      the writer's whole input for one draft, as JSON: what a
                      proposal written in Claude Code is written from
ingest DRAFT FILE --author MODEL [--instructions TEXT]
                      a proposal written in Claude Code (JSON: text, title,
                      first_comment, editor_note) through the same checks as an
                      API proposal, recorded as a run the page lists
media-add DRAFT FILE --kind KIND --made-with TEXT [--note TEXT]
                      store a media file made in Claude Code (a PNG or PDF,
                      checked from its contents) for the page to show
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from judge.content_workspace import db, store, writer

#: The commands that write (cw_* tables only). Gated; see the module docstring.
WRITE_COMMANDS = ("seed", "ingest", "media-add")

DEV_WRITE_HELP = ("write to a database that is not this machine while ENVIRONMENT="
                  "development (judge/writeguard.py would refuse it otherwise)")


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m judge.content_workspace", add_help=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sd = sub.add_parser("seed")
    sd.add_argument("--development-write", action="store_true", help=DEV_WRITE_HELP)
    sub.add_parser("status")
    m = sub.add_parser("material")
    m.add_argument("draft", type=int)
    m.add_argument("--instructions")
    m.add_argument("--out")
    i = sub.add_parser("ingest")
    i.add_argument("draft", type=int)
    i.add_argument("file")
    i.add_argument("--author", required=True)
    i.add_argument("--instructions")
    i.add_argument("--development-write", action="store_true", help=DEV_WRITE_HELP)
    dj = sub.add_parser("draft-json")
    dj.add_argument("draft", type=int)
    dj.add_argument("--out")
    md = sub.add_parser("media-add")
    md.add_argument("draft", type=int)
    md.add_argument("file")
    md.add_argument("--kind", required=True)
    md.add_argument("--made-with", required=True)
    md.add_argument("--note")
    md.add_argument("--development-write", action="store_true", help=DEV_WRITE_HELP)
    return ap


def write_gate(cmd: str, development_write: bool, dsn: str | None) -> str | None:
    """Why a write command is refused, or None when it may run. Read-only
    commands always pass."""
    if cmd not in WRITE_COMMANDS or development_write:
        return None
    from judge.writeguard import UnsafeWriteRefused, check

    try:
        check(dsn, command=f"python -m judge.content_workspace {cmd}")
    except UnsafeWriteRefused as e:
        return str(e)
    return None


def main(argv: list[str]) -> int:
    load_dotenv()
    args = _parser().parse_args(argv)
    refused = write_gate(args.cmd, getattr(args, "development_write", False),
                         os.environ.get("DATABASE_URL"))
    if refused:
        print(refused)
        return 2
    conn = db.connect()
    try:
        missing = db.missing_tables(conn)
        conn.rollback()
        if missing:
            print(f"this database has no {', '.join(missing)}: {db.MIGRATE_HINT}")
            return 1
        if args.cmd == "seed":
            added = store.load_seed(conn)
            conn.commit()
            print(f"added {added['platforms']} platform(s), {added['notes']} note(s), "
                  f"{added['platform_lists']} format/topic entries")
        elif args.cmd == "status":
            for table in db.TABLES:
                n = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                print(f"{table}: {n}")
            conn.rollback()
        elif args.cmd == "material":
            out = json.dumps(writer.export(conn, args.draft, args.instructions),
                             ensure_ascii=False, indent=1)
            conn.rollback()
            if args.out:
                Path(args.out).write_text(out, encoding="utf-8")
                print(f"wrote {args.out}")
            else:
                print(out)
        elif args.cmd == "ingest":
            answer = json.loads(Path(args.file).read_text(encoding="utf-8"))
            run = writer.ingest(conn, args.draft, answer, author=args.author,
                                instructions=args.instructions, by=f"claude-code ({args.author})")
            conn.commit()
            print(f"run {run['id']}: {run['state']}")
            for r in run["reasons"]:
                print(f"  refused: {r}")
            if run["fit"]:
                print(f"  fit check: {run['fit']['summary']}")
                for res in run["fit"]["results"]:
                    if res["outcome"] in ("fail", "warn", "unchecked"):
                        print(f"    {res['outcome']}: {res['rule'][:70]} - {res['detail']}")
            return 0 if run["state"] == "proposed" else 3
        elif args.cmd == "draft-json":
            d = store.draft(conn, args.draft)
            p = store.platform(conn, d["platform_key"])
            conn.rollback()
            out = json.dumps({"draft": d, "platform": {"key": p["key"], "name": p["name"]}},
                             ensure_ascii=False, indent=1, default=str)
            if args.out:
                Path(args.out).write_text(out, encoding="utf-8")
                print(f"wrote {args.out}")
            else:
                print(out)
        elif args.cmd == "media-add":
            from judge.content_workspace import media, settings

            m = media.add(conn, args.draft, data=Path(args.file).read_bytes(),
                          filename=Path(args.file).name, kind=args.kind,
                          made_with=args.made_with, note=args.note,
                          by="claude-code", s=settings.load())
            conn.commit()
            size = (f"{m['pages']} page(s)" if m["pages"] else f"{m['width']}x{m['height']}")
            print(f"media {m['id']}: {m['kind']} {m['filename']} ({size}, "
                  f"{m['size_bytes']:,} bytes) for draft {m['draft_id']}")
    except store.WorkspaceRequestError as e:
        conn.rollback()
        print(f"refused: {e}")
        return 2
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
