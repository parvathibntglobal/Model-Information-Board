"""Harvest the seated developer forums' newest topics into `document`.

    .venv/Scripts/python.exe scripts/harvest_forums.py --max-new-topics 150

THE NIGHTLY READ OF A FORUM THAT MAY NOT BE SEARCHED (2026-10-26). The Google
AI Developers Forum's robots.txt disallows `/search`, and Google's terms make
robots.txt the permission (contract/sources.yaml, ruling
`google-ai-developers-forum`). So there is no per-model search: each night this
reads the newest-created topics, skips the ones already stored, and stores each
new topic's opening post. Each model's fetch then reads the threads that name
it, like any other unread thread.

Every `forum:` platform row in contract/sources.yaml is read; each passes its
own terms gate on THIS run's robots.txt observations before its first request.
Writes are append-only (`ON CONFLICT DO NOTHING`), and preflight runs first
because this writes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.adapters.blog.robots import RobotsGate  # noqa: E402
from collect.adapters.discourse import (  # noqa: E402
    DOCUMENT_SOURCE,
    DiscourseForum,
    forum_for_source,
)
from collect.config import settings  # noqa: E402
from collect.http import build_client  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.registry.sources import load_sources  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pages", type=int, default=10,
                        help="listing pages read per forum, 30 topics each, newest first")
    parser.add_argument("--max-new-topics", type=int, default=150,
                        help="new topics fetched per forum per run (two requests each); "
                             "the rest are counted as deferred and read next run")
    parser.add_argument("--dry-run", action="store_true",
                        help="observe and list, fetch and write nothing")
    args = parser.parse_args(argv)

    contract = load_sources()
    forums = [s for s in contract.platforms if s.get("platform") == "forum"]
    if not forums:
        print("no forum source in contract/sources.yaml; nothing to read")
        return 0
    store = RawStore(Path(settings().raw_store_path))
    failed: list[str] = []

    with build_client(timeout=30.0) as client:
        robots = RobotsGate(client, user_agent=settings().user_agent)
        conn = None
        if not args.dry_run:
            from collect.db import connect
            from collect.ops.preflight import PreflightRefused, preflight
            from collect.registry.policy import load_registry_policy

            observations = {
                s["id"]: DiscourseForum(s["endpoint"], client=client, store=store,
                                        robots=robots).observe()
                for s in forums
            }
            conn = connect()
            try:
                print(preflight(conn, environment=settings().environment,
                                policy=load_registry_policy(), sources=forums,
                                rulings=contract.rulings, observations=observations).summary())
            except PreflightRefused as refusal:
                print(str(refusal), file=sys.stderr)
                conn.close()
                return 1
        try:
            held: frozenset[str] = frozenset()
            loaded: set[str] = set()
            if conn is not None:
                held = frozenset(r[0] for r in conn.execute(
                    "SELECT external_id FROM document WHERE source = %s", (DOCUMENT_SOURCE,)))
                loaded = {r[0] for r in conn.execute(
                    "SELECT id FROM source WHERE id = ANY(%s)", ([s["id"] for s in forums],))}
            for source in forums:
                sid = source["id"]
                # As harvest_blogs: a forum merged but not yet loaded with
                # `registry load-sources` is refused by name, before any request.
                if conn is not None and sid not in loaded:
                    print(f"  {sid}: REFUSED - no `source` row; run "
                          "`python -m collect.cli registry load-sources` first")
                    failed.append(sid)
                    continue
                try:
                    forum = forum_for_source(source, rulings=contract.rulings, client=client,
                                             store=store, robots=robots)
                except Exception as error:  # noqa: BLE001 - a refusal is reported, not raised
                    print(f"  {sid}: REFUSED {type(error).__name__}: {str(error)[:200]}")
                    failed.append(sid)
                    continue
                if args.dry_run:
                    from collect.adapters.discourse import ForumRun

                    listed = forum.newest(ForumRun(host=forum.host), pages=args.pages)
                    print(f"  {sid}: {len(listed)} topic(s) listed; dry run, nothing fetched")
                    continue
                run = forum.harvest(pages=args.pages, held=held, max_new=args.max_new_topics)
                report = forum.write_documents(conn, run)
                conn.commit()
                print(f"  {sid}: listed {run.listed}, already stored {run.already_stored}, "
                      f"stored {len(run.stored)}, inserted {report.inserted}, "
                      f"deferred {run.deferred}, http errors {run.http_errors}, "
                      f"robots-blocked {run.robots_blocked}")
                if run.http_errors and not run.stored:
                    failed.append(sid)
        finally:
            if conn is not None:
                conn.close()

    if failed:
        print(f"\n{len(failed)} forum(s) not read: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
