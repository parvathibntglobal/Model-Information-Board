"""The Finder (ARCHITECTURE.md 5.1) plus the code filters (5.2a), for Reddit.
No model.

Per subreddit: page through the newest posts until the age window ends, match
every phrase against each post in the window, then filter the matches. A
subreddit that fails is reported and the others still run; its silence never
reads as "no threads there".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from common import filters
from common import thread as t
from common.config import Community, Pace, Query
from common.match import matches

from .client import PER_PAGE, RedditClient, RedditError
from .parse import created_at, thread_of


@dataclass
class SubredditReport:
    """What was read in one subreddit: the denominator for its matches."""

    name: str
    pages: int = 0
    posts_in_window: int = 0
    posts_without_body: int = 0
    reached_window_end: bool = False
    error: str | None = None


@dataclass
class FindResult:
    threads: list[t.Thread]
    subreddits: list[SubredditReport] = field(default_factory=list)
    checks_not_run: list[str] = field(default_factory=list)
    requests: int = 0

    @property
    def kept(self) -> list[t.Thread]:
        return [th for th in self.threads if th.status == t.STATUS_FOUND]

    @property
    def dropped(self) -> list[t.Thread]:
        return [th for th in self.threads if th.status == t.STATUS_DROPPED]

    @property
    def errors(self) -> list[str]:
        return [f"r/{s.name}: {s.error}" for s in self.subreddits if s.error]


def _read_subreddit(
    client: RedditClient, sub: Community, *, queries: list[Query], pace: Pace,
    now: datetime, max_pages: int, report: SubredditReport,
) -> list[t.Thread]:
    cutoff = now - timedelta(days=pace.max_thread_age_days)
    found: list[t.Thread] = []
    closed_ids: set[str] = set()
    cursor: str | None = None

    for _ in range(max_pages):
        posts, cursor = client.newest_posts(sub.key, cursor)
        report.pages += 1
        for post in posts:
            if created_at(post) < cutoff:
                continue  # outside the window: not read, not counted
            report.posts_in_window += 1
            if not (post.get("selftext") or "").strip():
                report.posts_without_body += 1
            text = f"{post.get('title') or ''}\n{post.get('selftext') or ''}"
            hits = [q for q in queries if matches(q.phrase, text)]
            if not hits:
                continue
            th = thread_of(post, fetched_at=now)
            for q in hits:
                if q.problem not in th.matched_problems:
                    th.matched_problems.append(q.problem)
                th.matched_phrases.append(q.phrase)
            # Only when the field is sent and true; the listing sent neither on
            # 2026-11-10, and an absent field is not "open" (see checks_not_run).
            if post.get("locked") is True or post.get("archived") is True:
                closed_ids.add(th.ext_id)
            found.append(th)

        # Newest first, so one post older than the window means the rest are too.
        if any(created_at(p) < cutoff for p in posts):
            report.reached_window_end = True
            break
        if not posts or not cursor:
            report.reached_window_end = True  # the subreddit has no older posts
            break

    for th in found:
        reason = (
            filters.community_not_allowed(sub)
            or filters.closed(th.ext_id in closed_ids)
            or filters.too_old(th, now=now, max_age_days=pace.max_thread_age_days)
            or filters.no_text(th)
        )
        if reason:
            th.drop(reason)
        elif flag := filters.community_flag(sub):
            th.flags.append(flag)
    return found


def find_reddit(
    client: RedditClient,
    *,
    subreddits: list[Community],
    queries: list[Query],
    pace: Pace,
    now: datetime,
    max_pages: int,
) -> FindResult:
    result = FindResult(threads=[])
    for sub in subreddits:
        report = SubredditReport(name=sub.key)
        result.subreddits.append(report)
        try:
            result.threads.extend(_read_subreddit(
                client, sub, queries=queries, pace=pace, now=now,
                max_pages=max_pages, report=report))
        except (RedditError, ValueError) as exc:
            # Posts matched before the failure go with the subreddit: a
            # half-read subreddit is reported as failed, not as a short list.
            report.error = str(exc)
            continue
        if not report.reached_window_end:
            result.checks_not_run.append(
                f"r/{sub.key}: stopped at the page limit ({max_pages} pages of "
                f"{PER_PAGE}, {report.posts_in_window} posts); older posts inside the "
                f"{pace.max_thread_age_days}-day window were NOT read"
            )
        if report.posts_without_body:
            result.checks_not_run.append(
                f"r/{sub.key}: {report.posts_without_body} of {report.posts_in_window} "
                "posts came without body text, so they were matched on the title alone"
            )
    result.requests = client.requests

    result.threads.sort(key=lambda th: th.created_at, reverse=True)
    result.checks_not_run.append(
        "closed: the listing sends no locked or archived field, so a locked thread "
        "is NOT dropped; the reviewer sees it is locked when opening it"
    )
    if pace.team_accounts:
        result.checks_not_run.append(
            "already_answered: NOT BUILT for Reddit (reading a thread's comments is one "
            "more call per thread on the shared RapidAPI quota), so threads where the "
            "team has already replied are NOT filtered out, team_accounts notwithstanding"
        )
    else:
        result.checks_not_run.append(
            "already_answered: no team accounts in pace.yaml (and the check is not "
            "built for Reddit), so threads where the team has already replied are "
            "NOT filtered out"
        )
    result.checks_not_run.append(
        "replies: only each post's title (and body, when sent) is matched; comments "
        "are not read"
    )
    result.checks_not_run.append(
        "pace_cap: no record of posted replies exists yet, so the weekly cap is not applied"
    )
    return result
