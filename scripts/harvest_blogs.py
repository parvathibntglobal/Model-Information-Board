"""Harvest the seeded blog feeds into `document` and `thread_context`.

The caller `assemble_article` did not have. Same shape as
`scripts/harvest_github.py`: the terms gate fires per source, the write happens
in one transaction, and the report names what was skipped rather than only what
succeeded.

    .venv/Scripts/python.exe scripts/harvest_blogs.py --dry-run
    .venv/Scripts/python.exe scripts/harvest_blogs.py --limit 3

WHY A SCRIPT AND NOT A CHAIN STAGE
----------------------------------
Honest about what does not exist: `collect/ops/chain.py` has no sweep stage for
any platform, so there is nothing for a blog assemble stage to follow.
`docs/ops-nightly-chain.md` already lists that as a gap. A stage added now would
have to invent the sweep it depends on, which is a bigger design move than this
lane should make unilaterally.

So this is the same standing as GitHub's harvest: a real, callable path that a
person runs, and that becomes a stage when the sweep does.

PREFLIGHT RUNS HERE, because this writes. Issue #27 closed with the rule that
write paths gate and read paths do not, and a script that writes is a write path
whatever it is spelled as.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.adapters.blog.fetch import (  # noqa: E402
    NotAFetchTargetError,
    fetcher_for_source,
)
from collect.adapters.blog.robots import RobotsGate  # noqa: E402
from collect.adapters.blog.write import write_blog_run  # noqa: E402
from collect.config import settings  # noqa: E402
from collect.http import build_client  # noqa: E402
from collect.rawstore import RawStore  # noqa: E402
from collect.registry.sources import load_sources  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=0,
                        help="stop after N feeds. 0 means every feed.")
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch and assemble, write nothing, report what would land")
    args = parser.parse_args(argv)

    contract = load_sources()
    store = RawStore(Path(settings().raw_store_path))
    feeds = contract.feeds[: args.limit] if args.limit else contract.feeds

    conn = None
    if not args.dry_run:
        from collect.db import connect
        from collect.ops.preflight import PreflightRefused, preflight
        from collect.registry.policy import load_registry_policy

        conn = connect()
        try:
            report = preflight(
                conn,
                environment=settings().environment,
                policy=load_registry_policy(),
                sources=list(feeds),
                rulings=contract.rulings,
                observations={},
            )
            print(report.summary())
        except PreflightRefused as refusal:
            print(str(refusal), file=sys.stderr)
            conn.close()
            return 1

    totals = {"feeds": 0, "refused": 0, "articles": 0, "documents": 0,
              "contexts": 0, "nothing_extracted": 0, "already_present": 0}

    try:
        with build_client() as client:
            robots = RobotsGate(client, user_agent=settings().user_agent)
            for feed in feeds:
                feed_id = feed["id"]
                try:
                    fetcher = fetcher_for_source(
                        feed, robots=robots, rulings=contract.rulings,
                        client=client, store=store,
                    )
                except NotAFetchTargetError:
                    print(f"  {feed_id:38s} SKIP not a fetch target")
                    continue
                except Exception as error:  # noqa: BLE001 - a refusal reports
                    totals["refused"] += 1
                    print(f"  {feed_id:38s} REFUSED {type(error).__name__}")
                    continue

                run = fetcher.harvest_feed(feed["endpoint"])
                totals["feeds"] += 1
                if run.outcome != "fetched":
                    print(f"  {feed_id:38s} {run.outcome}")
                    continue

                if args.dry_run:
                    stored = sum(1 for a in run.articles if a.stored)
                    print(f"  {feed_id:38s} would assemble {stored} article(s)")
                    totals["articles"] += stored
                    continue

                report = write_blog_run(conn, run, store=store)
                conn.commit()
                totals["articles"] += report.articles_seen
                totals["documents"] += report.documents_inserted
                totals["contexts"] += report.contexts_inserted
                totals["nothing_extracted"] += report.nothing_extracted
                totals["already_present"] += report.already_present
                print(f"  {feed_id:38s} {report.summary()}")
    finally:
        if conn is not None:
            conn.close()

    print()
    for key, value in totals.items():
        print(f"  {key:20s} {value}")
    if args.dry_run:
        print("\ndry run: nothing was written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
