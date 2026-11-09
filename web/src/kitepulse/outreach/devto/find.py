"""Find dev.to articles for outreach. Reads only; writes no database.

    py -3.12 web/src/kitepulse/outreach/devto/find.py
    py -3.12 web/src/kitepulse/outreach/devto/find.py --tag claudecode
    py -3.12 web/src/kitepulse/outreach/devto/find.py --problem agent-stuck
    py -3.12 web/src/kitepulse/outreach/devto/find.py --phrase "usage limit"

Output:

    var/outreach/devto-<UTC stamp>.jsonl      one line per matched article, kept and dropped
    var/outreach/devto-<UTC stamp>.run.json   what ran, what was read per tag, what did not
    and a readable list on stdout.

Exits 1 if any tag failed, so a failure is never read as an empty week.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]  # devto -> outreach -> kitepulse -> src -> web -> repo

# Run as a script by its path: make `devto` (this folder), `common` (its
# sibling) and `collect` (for the User-Agent) importable.
for _p in (str(HERE.parent), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import config  # noqa: E402

from devto import SOURCE  # noqa: E402
from devto.client import DevtoClient  # noqa: E402
from devto.finder import FindResult, find_devto  # noqa: E402
from devto.parse import COMMUNITY  # noqa: E402

CONFIG_DIR = HERE / "config"
DEFAULT_OUT = REPO_ROOT / "var" / "outreach"
DEFAULT_MAX_PAGES = 3  # pages of 1,000 per tag; the busiest chosen tag needed 2


def _user_agent() -> str:
    from collect.config import settings  # reads .env; the only collect/ import

    return settings().user_agent


def _age(created: datetime, now: datetime) -> str:
    hours = int((now - created).total_seconds() // 3600)
    return f"{hours}h" if hours < 48 else f"{hours // 24}d"


def _print(result: FindResult, *, now: datetime, out_files: list[Path]) -> None:
    kept, dropped = result.kept, result.dropped
    print(f"\ndev.to: {result.articles_read} articles read, {len(result.threads)} matched, "
          f"{len(kept)} kept, {len(dropped)} dropped ({result.requests} API requests)\n")
    for r in result.tags:
        state = f"FAILED: {r.error}" if r.error else f"{r.articles} articles"
        print(f"  {r.tag:<22} {state}")
    print()
    for th in kept:
        print(f"[{_age(th.created_at, now):>4}] {th.title or '(no title)'}")
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
    if result.errors:
        print("\nFAILED tags (their articles are NOT in the output):")
        for line in result.errors:
            print(f"  - {line}")
    print("\nWritten:")
    for f in out_files:
        print(f"  {f}")


def cmd_find(args: argparse.Namespace) -> int:
    tags = config.names("tags.yaml", "tags", CONFIG_DIR)
    if args.tag:
        tags = [args.tag]

    queries = config.queries(SOURCE, CONFIG_DIR)
    if args.problem:
        queries = [q for q in queries if q.problem == args.problem]
        if not queries:
            print(f"no phrases for problem {args.problem!r} in queries.yaml", file=sys.stderr)
            return 2
    if args.phrase:
        queries = [config.Query(problem=args.problem or "adhoc", phrase=args.phrase)]

    now = datetime.now(UTC)
    result = find_devto(
        DevtoClient(_user_agent()),
        tags=tags,
        queries=queries,
        pace=config.pace(SOURCE, CONFIG_DIR),
        community=config.community(COMMUNITY, CONFIG_DIR),
        now=now,
        max_pages=args.max_pages,
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    jsonl = out_dir / f"{SOURCE}-{stamp}.jsonl"
    run = out_dir / f"{SOURCE}-{stamp}.run.json"
    with jsonl.open("w", encoding="utf-8") as fh:
        for th in result.threads:
            fh.write(json.dumps(th.record(), ensure_ascii=False) + "\n")
    run.write_text(json.dumps({
        "source": SOURCE,
        "ran_at": now.isoformat(),
        "queries": [{"problem": q.problem, "phrase": q.phrase} for q in queries],
        "tags": [{"tag": r.tag, "articles": r.articles, "complete": r.complete,
                  "error": r.error} for r in result.tags],
        "articles_read": result.articles_read,
        "matched": len(result.threads),
        "kept": len(result.kept),
        "dropped": dict(Counter(th.drop_reason for th in result.dropped)),
        "checks_not_run": result.checks_not_run,
        "api_requests": result.requests,
    }, indent=2), encoding="utf-8")

    _print(result, now=now, out_files=[jsonl, run])
    return 1 if result.errors else 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="find.py", description="Find dev.to articles for outreach (reads only)."
    )
    parser.add_argument("--tag", help="read only this tag instead of tags.yaml")
    parser.add_argument("--problem", help="only this problem key from queries.yaml")
    parser.add_argument("--phrase", help="match this one phrase instead of queries.yaml")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES,
                        help="most pages of 1,000 articles per tag")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    return cmd_find(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
