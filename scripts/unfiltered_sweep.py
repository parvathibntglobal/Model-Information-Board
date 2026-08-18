"""The unfiltered sweep: recent posts, no query terms, for one calibration.

    py -3 scripts/unfiltered_sweep.py --out ./_unfiltered_sweep

WHY IT EXISTS. Every other corpus on disk was retrieved by queries containing
model names, so it is pre-selected for the property the entity gate tests. A
survival rate measured against it is an upper bound and the entity gate's is
severely so, and a 2sigma baseline collected there would move when the gates
land rather than when the world changes. Design and the argument in
`docs/unfiltered-sweep-design.md`.

`/getPostsBySubreddit` TAKES NO QUERY, which is the whole point: there is no
ranking to bias the window, and "the last N posts in r/X" is a definition rather
than a result. `/getSearchPosts` scoped to a subreddit is NOT a substitute — the
index ranks, and ranking is the selection effect this exists to escape.

    ⚠  ITS `sort` IS LOWERCASE, unlike `/getSearchPosts`, which takes
       RELEVANCE / NEW / TOP in caps. `sort=NEW` returns HTTP 200 with
       `success: false, data: "sort value is wrong"` and zero posts — a
       silent empty sweep, not an error. Probed 2026-08-18.

WHAT THIS SAMPLE IS, AND WHAT IT IS NOT
----------------------------------------
It measures **survival within the subreddits we would actually harvest**. It
does NOT measure survival over Reddit, and must never be quoted as if it did.
Every available basis for choosing subreddits biases upward; these were
nominated by breadth of query coverage in the 2026-08-17 slice, which is less
circular than post count and is not uncircular. Two high-ranking nominees were
excluded as content marketing. See `docs/proposals/reddit-sweep-contract.md` §2.

EQUAL DRAW, NOT PROPORTIONAL. Sampling in proportion to volume would make
r/ClaudeAI roughly half the sample and the figure a fact about one subreddit.

STORED OUTSIDE `raw/`, WITH A DELETION DATE
--------------------------------------------
These documents are a **measurement population, not evidence**, and most of them
are about nothing — that is what they are for. Mixing them into `raw/` would make
every later count a blend of two selection rules, which is the defect this sweep
exists to fix, one layer down.

The `reddit-via-rapidapi` ruling covers this sweep on the same terms as an
evidence sweep — purpose is self-declared and an exempt category is one
everything gets filed under — and the retention difference is handled as a
property of the sample: separate storage, and `delete_after` written into the
manifest at collection.

NO MODEL PARTICIPATES.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect.adapters.reddit import (  # noqa: E402
    build_client,
    observe_reddit_use,
)
from collect.config import settings  # noqa: E402
from collect.registry.assertions import assert_terms_reviewed  # noqa: E402
from collect.registry.sources import load_sources  # noqa: E402

LISTING_PATH = "/getPostsBySubreddit"

#: Lowercase. See the module docstring — the caps form fails silently.
SORT = "new"

#: Proposed in `docs/proposals/reddit-sweep-contract.md` §2.4, pending the
#: contract change. Passed explicitly rather than read from a default, so
#: nothing picks up a list nobody agreed to.
SUBREDDITS = (
    "ClaudeAI", "ClaudeCode", "LocalLLaMA", "singularity", "OpenAI",
    "GithubCopilot", "codex", "ChatGPT", "Anthropic", "GeminiAI",
    "Bard", "LocalLLM",
)

PAGES_PER_SUBREDDIT = 7          # 7 x 25 = 175 per subreddit, ~2,100 total
SECONDS_PER_CALL = 2.5           # 24/min, under the 429 observed at 32
RETENTION_DAYS = 90


def sweep(out_dir: Path, subreddits, pages: int, population: str = "sample") -> int:
    contract = load_sources()
    row = next((s for s in contract.platforms if s["id"] == "reddit"), None)
    if row is None:
        print("contract/sources.yaml has no `reddit` source row", file=sys.stderr)
        return 2

    # THE GATE. A measurement sweep is a fetch, and the ruling covers it on
    # exactly the same terms as an evidence sweep.
    observations = {"reddit": observe_reddit_use()}
    assert_terms_reviewed([row], rulings=contract.rulings, observations=observations)
    print(f"terms gate : passed, {row['terms_ruling']} "
          f"({observations['reddit']['use_basis']})")

    out_dir.mkdir(parents=True, exist_ok=True)
    posts_file = (out_dir / "posts.jsonl").open("w", encoding="utf-8")
    calls_file = (out_dir / "calls.jsonl").open("w", encoding="utf-8")

    host = settings().rapidapi_host
    seen: set[str] = set()
    calls = 0
    quota: int | None = None
    started = datetime.now(tz=UTC)

    try:
        with build_client() as client:
            for subreddit in subreddits:
                cursor = None
                for page in range(1, pages + 1):
                    params = {"subreddit": subreddit, "sort": SORT}
                    if cursor:
                        params["cursor"] = cursor
                    response = client.get(f"https://{host}{LISTING_PATH}", params=params)
                    calls += 1
                    remaining = response.headers.get("x-ratelimit-requests-remaining")
                    if remaining is not None:
                        quota = int(remaining)

                    body = response.json()
                    ok = bool(body.get("success"))
                    data = body.get("data") if ok else {}
                    entries = (data or {}).get("posts") or []
                    cursor = (data or {}).get("cursor")

                    calls_file.write(json.dumps({
                        "subreddit": subreddit,
                        "page": page,
                        "status": response.status_code,
                        "success": ok,
                        # NULL where the header was absent: unread is not zero.
                        "quota_remaining": quota if remaining is not None else None,
                        "posts": len(entries),
                        # A `success: false` body is not an error and not an
                        # empty subreddit. Recorded verbatim so the two stay
                        # distinguishable after the fact.
                        "refusal": None if ok else body.get("data"),
                    }) + "\n")

                    for entry in entries:
                        d = entry.get("data") or {}
                        pid = d.get("id")
                        if not pid or pid in seen:
                            continue
                        seen.add(pid)
                        ts = d.get("created_utc")
                        posts_file.write(json.dumps({
                            "external_id": pid,
                            "subreddit": d.get("subreddit"),
                            "url": "https://www.reddit.com" + (d.get("permalink") or ""),
                            "created_at": (
                                datetime.fromtimestamp(ts, tz=UTC).date().isoformat()
                                if ts else None
                            ),
                            "author": d.get("author"),
                            "author_fullname": d.get("author_fullname"),
                            "is_self": d.get("is_self"),
                            "score": d.get("score"),
                            "num_comments": d.get("num_comments"),
                            "title": d.get("title") or "",
                            "selftext": d.get("selftext") or "",
                        }, ensure_ascii=False) + "\n")

                    print(f"  {subreddit:<16} page {page}/{pages}  "
                          f"{len(entries):>2} posts  quota {quota}")
                    if not cursor or not entries:
                        break
                    time.sleep(SECONDS_PER_CALL)
    finally:
        posts_file.close()
        calls_file.close()

    finished = datetime.now(tz=UTC)
    manifest = {
        # EXPLICIT, not inferred from the directory name. A control corpus that
        # later gets read as a sample is the exact defect the separate store
        # prevents, and a path is a weaker signal than a field.
        "population": population,
        "purpose": "measurement population for triage survival calibration",
        "not_evidence": (
            "These documents are a denominator, not evidence. Most are about "
            "nothing, none is quoted, none is published. Never merge into raw/."
        ),
        "terms_ruling": row["terms_ruling"],
        "use_basis": observations["reddit"]["use_basis"],
        "collected_on": started.date().isoformat(),
        "delete_after": (started.date() + timedelta(days=RETENTION_DAYS)).isoformat(),
        "retention_reason": (
            "Data API Terms 3.2 is unresolved against NFR-4's immutable store. "
            "This sample is outside raw/ precisely so it can carry a deletion "
            "date, which is how the retention difference is handled without a "
            "second terms ruling."
        ),
        "endpoint": LISTING_PATH,
        "sort": SORT,
        "subreddits": list(subreddits),
        "pages_per_subreddit": pages,
        "draw": "equal",
        "posts": len(seen),
        "calls": calls,
        "quota_remaining": quota,
        "seconds": round((finished - started).total_seconds(), 1),
        "measures": (
            "survival WITHIN THESE SUBREDDITS. Not survival over Reddit. Every "
            "available basis for choosing them biases upward; these were "
            "nominated by breadth of query coverage in the 2026-08-17 slice."
        ),
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\nswept     : {len(seen)} distinct posts from {len(subreddits)} subreddits")
    print(f"            {calls} calls, {manifest['seconds']}s, quota remaining {quota}")
    print(f"            delete after {manifest['delete_after']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pages", type=int, default=PAGES_PER_SUBREDDIT)
    ap.add_argument("--subreddits", nargs="*", default=list(SUBREDDITS))
    ap.add_argument(
        "--population", default="sample",
        help="`sample` or `control`. Recorded in the manifest so a control "
             "corpus cannot later be read as a sample.")
    args = ap.parse_args(argv)
    return sweep(args.out, tuple(args.subreddits), args.pages, args.population)


if __name__ == "__main__":
    sys.exit(main())
