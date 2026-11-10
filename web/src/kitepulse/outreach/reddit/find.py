"""Find Reddit posts for outreach. Reads Reddit only.

    py -3.12 web/src/kitepulse/outreach/reddit/find.py
    py -3.12 web/src/kitepulse/outreach/reddit/find.py --subreddit ClaudeCode
    py -3.12 web/src/kitepulse/outreach/reddit/find.py --phrase "usage limit" --no-db

Needs RAPIDAPI_KEY, and REDDIT_PROVIDER or a Reddit RAPIDAPI_HOST, in .env -
the board's own Reddit settings, so this spends the board's RapidAPI quota.

Output:

    var/outreach/reddit-<UTC stamp>.jsonl      one line per matched post, kept and dropped
    var/outreach/reddit-<UTC stamp>.run.json   what ran, what did not, counts, quota left
    a readable list on stdout, and new threads in the outreach database
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]  # reddit -> outreach -> kitepulse -> src -> web -> repo

# Run as a script by its path: make `reddit` (this folder), `common` (its
# sibling) and `collect` (for .env settings) importable.
for _p in (str(HERE.parent), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import config, store  # noqa: E402

from reddit import SOURCE  # noqa: E402
from reddit.client import RedditClient, RedditError, host_for  # noqa: E402
from reddit.finder import FindResult, find_reddit  # noqa: E402

CONFIG_DIR = HERE / "config"
DEFAULT_OUT = REPO_ROOT / "var" / "outreach"
# 25 posts a page. r/ClaudeCode's week to 2026-11-10 was 650 posts in 27 pages
# (32 calls with 5 empty-response retries), measured by the first run. The
# other four subreddits are unmeasured. A subreddit cut off by this is named
# under "Checks NOT run".
DEFAULT_MAX_PAGES = 50


def _client() -> RedditClient:
    from collect.config import settings  # reads .env; the only collect/ import

    s = settings()
    return RedditClient(s.rapidapi_key or "", host_for(s.reddit_provider, s.rapidapi_host),
                        s.user_agent)


def _age(created: datetime, now: datetime) -> str:
    hours = int((now - created).total_seconds() // 3600)
    return f"{hours}h" if hours < 48 else f"{hours // 24}d"


def _quota(client: RedditClient) -> str:
    if client.quota_remaining is None:
        return "not reported by any response"
    of = f" of {client.quota_limit:,}" if client.quota_limit is not None else ""
    reset = (f", resets in {client.quota_reset_seconds / 86400:.1f} days"
             if client.quota_reset_seconds is not None else "")
    return f"{client.quota_remaining:,}{of} left{reset} (shared with the board's Reddit sweep)"


def _print(result: FindResult, client: RedditClient, *, now: datetime,
           out_files: list[Path]) -> None:
    kept, dropped = result.kept, result.dropped
    print(f"\nReddit: {len(result.threads)} posts matched, {len(kept)} kept, "
          f"{len(dropped)} dropped ({result.requests} API requests, "
          f"{client.empty_retries} empty-response retries, {client.rate_limited} rate-limited)\n")
    for s in result.subreddits:
        state = (f"FAILED: {s.error}" if s.error else
                 f"{s.posts_in_window} posts read in {s.pages} pages")
        print(f"  r/{s.name:<24} {state}")
    print()
    for th in kept:
        print(f"[{_age(th.created_at, now):>4}] {th.community}  {th.title or '(no title)'}")
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
        print("\nFAILED subreddits (their posts are NOT in the output):")
        for line in result.errors:
            print(f"  - {line}")
    print(f"\nRapidAPI quota: {_quota(client)}")
    print("\nWritten:")
    for f in out_files:
        print(f"  {f}")


def cmd_find(args: argparse.Namespace) -> int:
    subs = config.communities(CONFIG_DIR)
    if args.subreddit:
        subs = [s for s in subs if s.key.lower() == args.subreddit.lower()]
        if not subs:
            print(f"no subreddit {args.subreddit!r} in communities.yaml", file=sys.stderr)
            return 2

    queries = config.queries(SOURCE, CONFIG_DIR)
    if args.problem:
        queries = [q for q in queries if q.problem == args.problem]
        if not queries:
            print(f"no phrases for problem {args.problem!r} in queries.yaml", file=sys.stderr)
            return 2
    if args.phrase:
        queries = [config.Query(problem=args.problem or "adhoc", phrase=args.phrase)]

    try:
        client = _client()
    except RedditError as exc:
        print(f"Reddit: not run. {exc}", file=sys.stderr)
        return 2
    now = datetime.now(UTC)
    result = find_reddit(
        client,
        subreddits=subs,
        queries=queries,
        pace=config.pace(SOURCE, CONFIG_DIR),
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
        "subreddits": [{
            "subreddit": s.name,
            "pages": s.pages,
            "posts_in_window": s.posts_in_window,
            "posts_without_body": s.posts_without_body,
            "reached_window_end": s.reached_window_end,
            "error": s.error,
        } for s in result.subreddits],
        "matched": len(result.threads),
        "kept": len(result.kept),
        "dropped": dict(Counter(th.drop_reason for th in result.dropped)),
        "checks_not_run": result.checks_not_run,
        "api_requests": result.requests,
        "empty_response_retries": client.empty_retries,
        "rate_limited": client.rate_limited,
        # As the last response stated them; null when no response carried one.
        "quota_remaining": client.quota_remaining,
        "quota_limit": client.quota_limit,
        "quota_reset_seconds": client.quota_reset_seconds,
    }, indent=2), encoding="utf-8")

    _print(result, client, now=now, out_files=[jsonl, run])
    saved = store.save_and_report(result.threads, skip_reason=store.skip_reason(
        no_db=args.no_db, phrase=args.phrase))
    return 1 if result.errors or not saved else 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="find.py", description="Find Reddit posts for outreach (reads only)."
    )
    parser.add_argument("--subreddit", help="only this subreddit (as in communities.yaml)")
    parser.add_argument("--problem", help="only this problem key from queries.yaml")
    parser.add_argument("--phrase", help="match this one phrase instead of queries.yaml")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES,
                        help="most listing pages (25 posts each) per subreddit")
    parser.add_argument("--no-db", action="store_true",
                        help="write the JSONL only, not the outreach database")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    return cmd_find(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
