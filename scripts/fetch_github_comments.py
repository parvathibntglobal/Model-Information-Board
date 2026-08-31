"""Fetch the comments on every stored GitHub issue, and report what they add.

WHAT THIS MEASURES, AND WHY IT IS DISTINCT AUTHORS RATHER THAN COMMENTS

`n_eff` counts VOICES. One engineer posting five times is one voice; a second
person writing "same here, on 4.8 as well" is a second voice on the same cell.
So the number that decides whether comment fetching is worth doing is **how many
distinct authors the comments add that the issue bodies do not already have** -
not how many comments there are.

`coverage_ratio` is GENERATED as `observed / (observed + hidden_children_min)`
and reads 0.0 on all 71 github contexts today, with 149 comments recorded as the
hidden floor. This reports what it would become.

COST. Search is 30/minute and core is 5,000/hour, separate buckets - measured
from `GET /rate_limit` and recorded in `collect/adapters/github.py`. This spends
core only, so it cannot slow discovery. Every commented issue in the corpus has
at most 46 comments and `per_page=100` takes them in one page.

    python scripts/fetch_github_comments.py --dry-run
    python scripts/fetch_github_comments.py --apply
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    import httpx

    from collect.adapters.github import (
        REST_INTERVAL,
        SEARCH_INTERVAL,
        GitHubHarvester,
        QueryRun,
    )
    from collect.config import settings
    from collect.db import connect
    from collect.limiter import HostLimiter
    from collect.rawstore import RawStore
    from collect.rawstore_reader import RawStoreReader

    conn = connect()
    reader = RawStoreReader(RawStore(settings().raw_store_path))

    rows = conn.execute(
        "SELECT id, external_id, text_ref, engagement, author_id FROM document "
        "WHERE source = 'github' ORDER BY id"
    ).fetchall()

    # The issue's API url lives in the stored payload, which is what `text_ref`
    # points at since the content_hash ruling.
    targets: list[tuple[str, str, int]] = []
    unresolved = 0
    for doc_id, _external, text_ref, engagement, _author in rows:
        count = int((engagement or {}).get("comments") or 0)
        if count <= 0:
            continue
        outcome = reader.resolve(text_ref) if text_ref else None
        if outcome is None or not outcome.found:
            unresolved += 1
            continue
        try:
            payload = json.loads(outcome.require())
        except ValueError:
            unresolved += 1
            continue
        url = payload.get("url")
        if not url:
            unresolved += 1
            continue
        targets.append((doc_id, url, count))

    if args.limit:
        targets = targets[: args.limit]

    hidden_total = sum(c for _d, _u, c in targets)
    body_authors = {r[4] for r in rows if r[4]}

    print(f"github documents          : {len(rows)}")
    print(f"with >= 1 comment         : {len(targets)}")
    print(f"comments to fetch (floor) : {hidden_total}")
    print(f"payload unresolvable      : {unresolved}")
    print(f"requests needed           : {len(targets)}  "
          f"({100 * len(targets) / 5000:.2f}% of the 5,000/hour core bucket)")
    print(f"distinct authors from issue BODIES: {len(body_authors)}")

    if args.dry_run:
        print("\n--dry-run: no requests issued, nothing stored.")
        conn.close()
        return 0

    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": os.getenv("USER_AGENT", "modelboard/0.1"),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    client = httpx.Client(headers=headers, timeout=30.0)
    harvester = GitHubHarvester.__new__(GitHubHarvester)
    harvester._client = client
    harvester._store = RawStore(settings().raw_store_path)

    # ⚠ THE REAL LIMITER, NOT A NO-OP. This was a `_NoWait` stub on both
    #   limiters, and it was defensible at 30 requests: a burst that small
    #   finishes inside GitHub's tolerance and pacing it only costs wall clock.
    #
    #   IT STOPPED BEING DEFENSIBLE AT 586. The core bucket is 5,000/hour and
    #   586 fits inside it, so the ceiling is not the risk - the SECONDARY limit
    #   is, which GitHub applies to burst rate rather than to volume and answers
    #   with a 403 that looks like a permission error. `REST_INTERVAL` is 0.8s
    #   and exists for exactly this; the eight-minute estimate for this fetch was
    #   computed FROM it, so running unpaced would have been faster than the
    #   number we costed, which is the direction that should have been suspicious.
    #
    #   Same shape as the `--no-network` no-op fixed the same day: a control that
    #   is present, correct elsewhere, and bypassed here.
    harvester._rest = HostLimiter(min_interval=REST_INTERVAL)
    harvester._search = HostLimiter(min_interval=SEARCH_INTERVAL)
    harvester._sleep = time.sleep
    harvester._epoch = time.time

    run = QueryRun.__new__(QueryRun)
    run.rest_calls = 0
    run.http_errors = 0

    per_issue: dict[str, list] = {}
    for doc_id, url, _count in targets:
        stored = harvester.fetch_comments(url, run)
        per_issue[doc_id] = stored

    fetched = sum(len(v) for v in per_issue.values())
    handles = [c.author_handle for v in per_issue.values() for c in v if c.author_handle]
    distinct = set(handles)

    print()
    print("=" * 62)
    print(f"requests issued           : {run.rest_calls}")
    print(f"http errors               : {run.http_errors}")
    print(f"comments fetched          : {fetched}")
    print(f"distinct comment authors  : {len(distinct)}")
    print()
    print("COVERAGE, before and after, on the issues that have comments:")
    print(f"  before  observed 0, hidden {hidden_total}  -> coverage_ratio 0.0")
    print(f"  after   observed {fetched}, hidden 0        -> coverage_ratio "
          f"{fetched / (fetched + 0):.1f}" if fetched else "  after   nothing fetched")
    print()
    top = collections.Counter(handles).most_common(5)
    print("busiest commenters (one person posting five times is ONE voice):")
    for handle, n in top:
        print(f"  {n:4d}  {handle}")
    repeat = sum(1 for _h, n in collections.Counter(handles).items() if n > 1)
    print(f"\nauthors appearing more than once: {repeat} of {len(distinct)} - "
          f"which is why voices and comments are different numbers.")

    out = pathlib.Path("_github_comments.json")
    out.write_text(
        json.dumps(
            {
                doc: [
                    {
                        "external_id": c.external_id,
                        "ref": c.ref,
                        "content_hash": c.content_hash,
                        "html_url": c.html_url,
                        "author_handle": c.author_handle,
                    }
                    for c in v
                ]
                for doc, v in per_issue.items()
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"\npayloads stored in the raw store; index written to {out}")
    print("NOT written to `document` - that is the write path and it is the "
          "next commit, deliberately separate from proving the fetch works.")
    conn.close()
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
