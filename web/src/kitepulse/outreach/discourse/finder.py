"""The Finder (ARCHITECTURE.md 5.1) plus the code filters (5.2a), for Discourse
forums. No model.

Per forum: page through the newest-created topics until the age window ends,
match every phrase against each topic in the window, then filter the matches.
A forum that fails is reported and the others still run; its silence never
reads as "no threads there".
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from common import filters
from common import thread as t
from common.config import Community, Pace, Query
from common.match import matches

from .client import DiscourseClient, DiscourseError
from .parse import created_at, thread_of


@dataclass
class ForumReport:
    """What was read on one forum: the denominator for its matches."""

    host: str
    pages: int = 0
    topics_in_window: int = 0
    topics_without_excerpt: int = 0
    reached_window_end: bool = False
    error: str | None = None


@dataclass
class FindResult:
    threads: list[t.Thread]
    forums: list[ForumReport] = field(default_factory=list)
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
        return [f"{f.host}: {f.error}" for f in self.forums if f.error]


def _read_forum(
    client: DiscourseClient, forum: Community, *, queries: list[Query], pace: Pace,
    now: datetime, max_pages: int, report: ForumReport,
) -> list[t.Thread]:
    cutoff = now - timedelta(days=pace.max_thread_age_days)
    found: list[t.Thread] = []
    closed_ids: set[str] = set()

    for page in range(max_pages):
        data = client.latest_topics(page)
        report.pages += 1
        listing = data["topic_list"]
        topics = listing.get("topics") or []
        usernames = {u["id"]: u["username"] for u in data.get("users") or ()
                     if "id" in u and "username" in u}

        for topic in topics:
            if created_at(topic) < cutoff:
                continue  # outside the window: not read, not counted
            report.topics_in_window += 1
            if not topic.get("excerpt"):
                report.topics_without_excerpt += 1
            text = f"{topic.get('title') or ''}\n{topic.get('excerpt') or ''}"
            hits = [q for q in queries if matches(q.phrase, text)]
            if not hits:
                continue
            th = thread_of(topic, base_url=client.base, host=forum.key,
                           usernames=usernames, fetched_at=now)
            for q in hits:
                if q.problem not in th.matched_problems:
                    th.matched_problems.append(q.problem)
                th.matched_phrases.append(q.phrase)
            if topic.get("closed") or topic.get("archived"):
                closed_ids.add(th.ext_id)
            found.append(th)

        # Pinned topics sit at the top whatever their age, so only unpinned
        # ones say whether the listing has passed the window.
        unpinned = [tp for tp in topics if not (tp.get("pinned") or tp.get("pinned_globally"))]
        if any(created_at(tp) < cutoff for tp in unpinned):
            report.reached_window_end = True
            break
        if not topics or not listing.get("more_topics_url"):
            report.reached_window_end = True  # the forum has no older topics
            break

    for th in found:
        reason = (
            filters.community_not_allowed(forum)
            or filters.closed(th.ext_id in closed_ids)
            or filters.too_old(th, now=now, max_age_days=pace.max_thread_age_days)
            or filters.no_text(th)
        )
        if reason:
            th.drop(reason)
        elif flag := filters.community_flag(forum):
            th.flags.append(flag)

    if pace.team_accounts:
        for th in found:
            if th.status != t.STATUS_FOUND:
                continue
            authors, complete = client.topic_authors(int(th.root_id))
            if reason := filters.already_answered(authors, pace.team_accounts):
                th.drop(reason)
            elif not complete:
                th.flags.append(t.TEAM_CHECK_PARTIAL)
    return found


def find_discourse(
    clients: Mapping[str, DiscourseClient],
    *,
    forums: list[Community],
    queries: list[Query],
    pace: Pace,
    now: datetime,
    max_pages: int,
) -> FindResult:
    """`clients` maps each forum's key (its host) to a client for it."""
    result = FindResult(threads=[])
    for forum in forums:
        client = clients[forum.key]
        report = ForumReport(host=forum.key)
        result.forums.append(report)
        try:
            result.threads.extend(_read_forum(
                client, forum, queries=queries, pace=pace, now=now,
                max_pages=max_pages, report=report))
        except DiscourseError as exc:
            # Threads matched before the failure are dropped with the forum:
            # a half-read forum is reported as failed, not as a short list.
            report.error = str(exc)
        result.requests += client.requests

        if report.error:
            continue
        if not report.reached_window_end:
            result.checks_not_run.append(
                f"{forum.key}: stopped at the page limit ({max_pages} pages, "
                f"{report.topics_in_window} topics); older topics inside the "
                f"{pace.max_thread_age_days}-day window were NOT read"
            )
        if report.topics_without_excerpt:
            result.checks_not_run.append(
                f"{forum.key}: {report.topics_without_excerpt} of "
                f"{report.topics_in_window} topics had no excerpt, so they were "
                "matched on the title alone"
            )

    result.threads.sort(key=lambda th: th.created_at, reverse=True)
    if not pace.team_accounts:
        result.checks_not_run.append(
            "already_answered: no team accounts in pace.yaml, so threads where the "
            "team has already replied are NOT filtered out"
        )
    result.checks_not_run.append(
        "replies: only each topic's title and listing excerpt are matched; replies "
        "and the rest of the opening post are not read"
    )
    result.checks_not_run.append(
        "pace_cap: no record of posted replies exists yet, so the weekly cap is not applied"
    )
    return result
