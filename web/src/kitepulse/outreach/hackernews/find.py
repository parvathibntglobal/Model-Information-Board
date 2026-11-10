"""Find Hacker News threads for outreach. Reads only; writes no database.

    py -3.12 web/src/kitepulse/outreach/hackernews/find.py
    py -3.12 web/src/kitepulse/outreach/hackernews/find.py --problem claude-limits
    py -3.12 web/src/kitepulse/outreach/hackernews/find.py --phrase "claude code stuck"

Output:

    var/outreach/hackernews-<UTC stamp>.jsonl      one line per thread, kept and dropped
    var/outreach/hackernews-<UTC stamp>.run.json   what ran, what did not, counts
    and a readable list on stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]  # hackernews -> outreach -> kitepulse -> src -> web -> repo

# Run as a script by its path: make `hackernews` (this folder), `common` (its
# sibling) and `collect` (for the User-Agent) importable.
for _p in (str(HERE.parent), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import config, store  # noqa: E402

from hackernews import SOURCE as HN  # noqa: E402
from hackernews.client import HackerNewsClient  # noqa: E402
from hackernews.finder import FindResult, find_hackernews  # noqa: E402

CONFIG_DIR = HERE / "config"
DEFAULT_OUT = REPO_ROOT / "var" / "outreach"


def _user_agent() -> str:
    from collect.config import settings  # reads .env; the only collect/ import

    return settings().user_agent


def _age(created: datetime, now: datetime) -> str:
    hours = int((now - created).total_seconds() // 3600)
    return f"{hours}h" if hours < 48 else f"{hours // 24}d"


def _print(result: FindResult, *, now: datetime, out_files: list[Path]) -> None:
    kept, dropped = result.kept, result.dropped
    print(f"\nHacker News: {len(result.threads)} items found, {len(kept)} kept, "
          f"{len(dropped)} dropped ({result.requests} API requests)\n")
    for th in kept:
        title = th.title or "(no title)"
        print(f"[{_age(th.created_at, now):>4}] {th.kind:<7} {title}")
        print(f"       {th.url}")
        print(f"       matched: {', '.join(th.matched_problems)} / "
              f"{' | '.join(repr(p) for p in th.matched_phrases)}")
        if th.body:
            snippet = " ".join(th.body.split())[:160]
            print(f"       \"{snippet}{'...' if len(th.body) > 160 else ''}\"")
        if th.flags:
            print(f"       flags: {', '.join(th.flags)}")
        print()
    if dropped:
        reasons = Counter(th.drop_reason for th in dropped)
        print("Dropped: " + ", ".join(f"{r} {n}" for r, n in reasons.most_common()))
    print("\nChecks NOT run:")
    for line in result.checks_not_run:
        print(f"  - {line}")
    print("\nWritten:")
    for f in out_files:
        print(f"  {f}")


def cmd_find(args: argparse.Namespace) -> int:
    queries = config.queries(HN, CONFIG_DIR)
    if args.problem:
        queries = [q for q in queries if q.problem == args.problem]
        if not queries:
            print(f"no phrases for problem {args.problem!r} in queries.yaml", file=sys.stderr)
            return 2
    if args.phrase:
        queries = [config.Query(problem=args.problem or "adhoc", phrase=args.phrase)]

    now = datetime.now(UTC)
    result = find_hackernews(
        HackerNewsClient(_user_agent()),
        queries=queries,
        pace=config.pace(HN, CONFIG_DIR),
        community=config.community(HN, CONFIG_DIR),
        now=now,
        max_pages=args.max_pages,
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    jsonl = out_dir / f"{HN}-{stamp}.jsonl"
    run = out_dir / f"{HN}-{stamp}.run.json"
    with jsonl.open("w", encoding="utf-8") as fh:
        for th in result.threads:
            fh.write(json.dumps(th.record(), ensure_ascii=False) + "\n")
    run.write_text(json.dumps({
        "source": HN,
        "ran_at": now.isoformat(),
        "queries": [{"problem": q.problem, "phrase": q.phrase} for q in queries],
        "found": len(result.threads),
        "kept": len(result.kept),
        "dropped": dict(Counter(th.drop_reason for th in result.dropped)),
        "checks_not_run": result.checks_not_run,
        "api_requests": result.requests,
    }, indent=2), encoding="utf-8")

    _print(result, now=now, out_files=[jsonl, run])
    saved = store.save_and_report(result.threads, skip_reason=store.skip_reason(
        no_db=args.no_db, phrase=args.phrase))
    return 0 if saved else 1


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="find.py", description="Find Hacker News threads for outreach (reads only)."
    )
    parser.add_argument("--problem", help="only this problem key from queries.yaml")
    parser.add_argument("--phrase", help="search this one phrase instead of queries.yaml")
    # 4: the busiest shipped phrase, 'claude code stuck', had 67 hits over 2
    # pages on 2026-11-09, and the default of 1 dropped 17 without a word.
    # A phrase still cut off is named under "Checks NOT run".
    parser.add_argument("--max-pages", type=int, default=4, help="pages of 50 per phrase")
    parser.add_argument("--no-db", action="store_true",
                        help="write the JSONL only, not the outreach database")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    return cmd_find(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
