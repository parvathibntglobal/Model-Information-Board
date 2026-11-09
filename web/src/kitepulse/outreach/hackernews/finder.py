"""The Finder (ARCHITECTURE.md 5.1) plus the code filters (5.2a), for Hacker
News. No model.

Output is a list of `Thread`s, kept and dropped, and the list of checks that
did NOT run. A check that did not run is named, never counted as a pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from common import filters
from common import thread as t
from common.config import Community, Pace, Query

from .client import HackerNewsClient
from .parse import thread_of


@dataclass
class FindResult:
    threads: list[t.Thread]
    checks_not_run: list[str] = field(default_factory=list)
    requests: int = 0

    @property
    def kept(self) -> list[t.Thread]:
        return [th for th in self.threads if th.status == t.STATUS_FOUND]

    @property
    def dropped(self) -> list[t.Thread]:
        return [th for th in self.threads if th.status == t.STATUS_DROPPED]


def find_hackernews(
    client: HackerNewsClient,
    *,
    queries: list[Query],
    pace: Pace,
    community: Community,
    now: datetime,
    max_pages: int = 1,
) -> FindResult:
    since = int((now - timedelta(days=pace.max_thread_age_days)).timestamp())

    # 1. Search every phrase; one Thread per HN item, recording every phrase
    #    and problem that found it.
    by_id: dict[str, t.Thread] = {}
    for q in queries:
        for hit in client.search_recent(q.phrase, since_epoch=since, max_pages=max_pages):
            th = by_id.get(str(hit["objectID"])) or thread_of(hit, fetched_at=now)
            by_id.setdefault(th.ext_id, th)
            if q.problem not in th.matched_problems:
                th.matched_problems.append(q.problem)
            if q.phrase not in th.matched_phrases:
                th.matched_phrases.append(q.phrase)
    threads = sorted(by_id.values(), key=lambda th: th.created_at, reverse=True)

    # 2. Filters that need nothing beyond the hit.
    for th in threads:
        reason = (
            filters.community_not_allowed(community)
            or filters.too_old(th, now=now, max_age_days=pace.max_thread_age_days)
            or filters.no_text(th)
        )
        if reason:
            th.drop(reason)
        elif flag := filters.community_flag(community):
            th.flags.append(flag)

    checks_not_run: list[str] = []

    # 3. Already answered by us: one thread read per story, kept threads only.
    if not pace.team_accounts:
        checks_not_run.append(
            "already_answered: no team accounts in pace.yaml, so threads where the "
            "team has already replied are NOT filtered out"
        )
    else:
        authors_by_story: dict[str, set[str]] = {}
        for th in threads:
            if th.status != t.STATUS_FOUND or th.root_id is None:
                continue
            if th.root_id not in authors_by_story:
                authors_by_story[th.root_id] = client.thread_authors(th.root_id)
            if reason := filters.already_answered(
                authors_by_story[th.root_id], pace.team_accounts
            ):
                th.drop(reason)

    checks_not_run.append(
        "pace_cap: no record of posted replies exists yet, so the weekly cap is not applied"
    )
    return FindResult(threads=threads, checks_not_run=checks_not_run, requests=client.requests)
