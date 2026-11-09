"""Find GitHub Discussions for outreach. Reads only; writes no database.

    py -3.12 web/src/kitepulse/outreach/github/find.py
    py -3.12 web/src/kitepulse/outreach/github/find.py --problem agent-stuck
    py -3.12 web/src/kitepulse/outreach/github/find.py --phrase "usage limit"

Needs KP_GITHUB_TOKEN in .env (see github/__init__.py); never MIB's GITHUB_TOKEN.

Output:

    var/outreach/github-<UTC stamp>.jsonl      one line per matched discussion, kept and dropped
    var/outreach/github-<UTC stamp>.run.json   what ran, what each phrase returned, what did not
    and a readable list on stdout.

Exits 1 if any phrase failed, so a failure is never read as an empty week.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]  # github -> outreach -> kitepulse -> src -> web -> repo

# Run as a script by its path: make `github` (this folder), `common` (its
# sibling) and `collect` (for the User-Agent and .env) importable.
for _p in (str(HERE.parent), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import config  # noqa: E402

from github import SOURCE  # noqa: E402
from github.client import GithubClient, GithubError, token_from_env  # noqa: E402
from github.finder import FindResult, find_github  # noqa: E402
from github.parse import COMMUNITY  # noqa: E402

CONFIG_DIR = HERE / "config"
DEFAULT_OUT = REPO_ROOT / "var" / "outreach"
DEFAULT_MAX_PAGES = 8  # pages of 25 per phrase; the busiest shipped phrase needed 3


def _user_agent() -> str:
    # The only collect/ import. settings() also loads .env into the
    # environment, which is where KP_GITHUB_TOKEN is read from.
    from collect.config import settings

    return settings().user_agent


def _age(created: datetime, now: datetime) -> str:
    hours = int((now - created).total_seconds() // 3600)
    return f"{hours}h" if hours < 48 else f"{hours // 24}d"


def _print(result: FindResult, *, now: datetime, out_files: list[Path]) -> None:
    kept, dropped = result.kept, result.dropped
    print(f"\nGitHub Discussions: {len(result.threads)} matched, {len(kept)} kept, "
          f"{len(dropped)} dropped ({result.requests} API requests)\n")
    for r in result.phrases:
        state = (f"FAILED: {r.error}" if r.error else
                 f"{r.confirmed} confirmed of {r.retrieved} read "
                 f"(GitHub reported {r.reported})")
        print(f"  {r.phrase!r:<26} {state}")
    print()
    for th in kept:
        print(f"[{_age(th.created_at, now):>4}] {th.community}: {th.title or '(no title)'}")
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
        print("\nFAILED phrases (what only they would find is NOT in the output):")
        for line in result.errors:
            print(f"  - {line}")
    print("\nWritten:")
    for f in out_files:
        print(f"  {f}")


def cmd_find(args: argparse.Namespace) -> int:
    queries = config.queries(SOURCE, CONFIG_DIR)
    if args.problem:
        queries = [q for q in queries if q.problem == args.problem]
        if not queries:
            print(f"no phrases for problem {args.problem!r} in queries.yaml", file=sys.stderr)
            return 2
    if args.phrase:
        queries = [config.Query(problem=args.problem or "adhoc", phrase=args.phrase)]

    user_agent = _user_agent()
    try:
        client = GithubClient(user_agent, token_from_env())
    except GithubError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    now = datetime.now(UTC)
    result = find_github(
        client,
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
        "phrases": [{"problem": r.problem, "phrase": r.phrase, "reported": r.reported,
                     "retrieved": r.retrieved, "confirmed": r.confirmed,
                     "complete": r.complete, "error": r.error} for r in result.phrases],
        "matched": len(result.threads),
        "kept": len(result.kept),
        "dropped": dict(Counter(th.drop_reason for th in result.dropped)),
        "flags": dict(Counter(f for th in result.kept for f in th.flags)),
        "checks_not_run": result.checks_not_run,
        "api_requests": result.requests,
    }, indent=2), encoding="utf-8")

    _print(result, now=now, out_files=[jsonl, run])
    return 1 if result.errors else 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="find.py", description="Find GitHub Discussions for outreach (reads only)."
    )
    parser.add_argument("--problem", help="only this problem key from queries.yaml")
    parser.add_argument("--phrase", help="search this one phrase instead of queries.yaml")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES,
                        help="most pages of 25 discussions per phrase")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    return cmd_find(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
