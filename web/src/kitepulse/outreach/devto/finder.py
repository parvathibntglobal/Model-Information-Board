"""The Finder (ARCHITECTURE.md 5.1) plus the code filters (5.2a), for dev.to.
No model.

Per tag: read the week's articles. Then deduplicate (an article carries up to
four tags), match every phrase against title + description, and filter. A tag
that fails is reported and the others still run; its silence never reads as
"no articles there".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from common import filters
from common import thread as t
from common.config import Community, Pace, Query
from common.match import matches

from .client import DevtoClient, DevtoError
from .parse import thread_of


@dataclass
class TagReport:
    """What was read for one tag: the denominator for its matches."""

    tag: str
    articles: int = 0
    complete: bool = False
    error: str | None = None


@dataclass
class FindResult:
    threads: list[t.Thread]
    tags: list[TagReport] = field(default_factory=list)
    articles_read: int = 0          # distinct articles, after deduplication
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
        return [f"tag {r.tag}: {r.error}" for r in self.tags if r.error]


def find_devto(
    client: DevtoClient,
    *,
    tags: list[str],
    queries: list[Query],
    pace: Pace,
    community: Community,
    now: datetime,
    max_pages: int,
) -> FindResult:
    result = FindResult(threads=[])
    days = pace.max_thread_age_days

    # 1. Each tag's week, deduplicated by article id.
    articles: dict[int, dict] = {}
    for tag in tags:
        report = TagReport(tag=tag)
        result.tags.append(report)
        try:
            listed, report.complete = client.tag_week(
                tag, days=days, now=now, max_pages=max_pages)
        except DevtoError as exc:
            report.error = str(exc)
            continue
        report.articles = len(listed)
        for article in listed:
            articles.setdefault(int(article["id"]), article)
        if not report.complete:
            result.checks_not_run.append(
                f"tag {tag}: stopped at the page limit ({max_pages} pages of 1,000); "
                "the rest of its week was NOT read"
            )
    result.articles_read = len(articles)

    # 2. Phrases, against the title and the listing's description.
    for article in articles.values():
        text = f"{article.get('title') or ''}\n{article.get('description') or ''}"
        hits = [q for q in queries if matches(q.phrase, text)]
        if not hits:
            continue
        th = thread_of(article, fetched_at=now)
        for q in hits:
            if q.problem not in th.matched_problems:
                th.matched_problems.append(q.problem)
            th.matched_phrases.append(q.phrase)
        result.threads.append(th)
    result.threads.sort(key=lambda th: th.created_at, reverse=True)

    # 3. Filters that need nothing beyond the listing.
    for th in result.threads:
        reason = (
            filters.community_not_allowed(community)
            or filters.too_old(th, now=now, max_age_days=days)
            or filters.no_text(th)
        )
        if reason:
            th.drop(reason)
        elif flag := filters.community_flag(community):
            th.flags.append(flag)

    # 4. Already answered by us. An article whose listing says 0 comments has
    #    no team comment, so only articles with comments are read.
    if not pace.team_accounts:
        result.checks_not_run.append(
            "already_answered: no team accounts in pace.yaml, so articles where the "
            "team has already commented are NOT filtered out"
        )
    else:
        for th in result.threads:
            if th.status != t.STATUS_FOUND:
                continue
            if not articles[int(th.ext_id)].get("comments_count"):
                continue
            authors = client.comment_authors(int(th.ext_id))
            if reason := filters.already_answered(authors, pace.team_accounts):
                th.drop(reason)

    result.checks_not_run.append(
        "article body: only the title and the listing's description are matched; "
        "the article itself and its comments are not read"
    )
    result.checks_not_run.append(
        "pace_cap: no record of posted replies exists yet, so the weekly cap is not applied"
    )
    result.requests = client.requests
    return result
