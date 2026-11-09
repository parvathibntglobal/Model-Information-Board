"""The Finder (ARCHITECTURE.md 5.1) plus the code filters (5.2a), for GitHub
Discussions. No model.

Per phrase: search the week, confirm each hit with the shared matcher. Then
deduplicate (one discussion can match several phrases) and filter. A phrase
that fails is reported and the others still run; a discussion found only by a
failed phrase is not in the output, and the run says so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from common import filters
from common import thread as t
from common.config import Community, Pace, Query
from common.match import matches

from .client import PER_PAGE, GithubClient, GithubError
from .parse import repo_of, thread_of


@dataclass
class PhraseReport:
    """What one phrase's search returned: the denominator for its matches."""

    problem: str
    phrase: str
    reported: int = 0         # GitHub's discussionCount
    retrieved: int = 0
    confirmed: int = 0        # hits the shared matcher confirmed in title + body
    complete: bool = False
    error: str | None = None


@dataclass
class FindResult:
    threads: list[t.Thread]
    phrases: list[PhraseReport] = field(default_factory=list)
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
        return [f"phrase {r.phrase!r}: {r.error}" for r in self.phrases if r.error]


def find_github(
    client: GithubClient,
    *,
    queries: list[Query],
    pace: Pace,
    community: Community,
    now: datetime,
    max_pages: int,
) -> FindResult:
    result = FindResult(threads=[])
    days = pace.max_thread_age_days
    since = now - timedelta(days=days)

    # 1. Search each phrase; keep only hits the shared matcher confirms.
    nodes: dict[str, dict] = {}
    threads: dict[str, t.Thread] = {}
    for q in queries:
        report = PhraseReport(problem=q.problem, phrase=q.phrase)
        result.phrases.append(report)
        try:
            hits, report.reported, report.complete = client.search_week(
                q.phrase, since=since, max_pages=max_pages)
        except GithubError as exc:
            report.error = str(exc)
            continue
        report.retrieved = len(hits)
        if not report.complete:
            result.checks_not_run.append(
                f"phrase {q.phrase!r}: stopped at the page limit ({max_pages} pages of "
                f"{PER_PAGE}); {report.reported - report.retrieved} of {report.reported} "
                "results GitHub reported were NOT read"
            )
        for node in hits:
            if not matches(q.phrase, f"{node.get('title') or ''}\n{node.get('bodyText') or ''}"):
                continue
            report.confirmed += 1
            nodes.setdefault(node["id"], node)
            th = threads.get(node["id"])
            if th is None:
                th = threads[node["id"]] = thread_of(node, fetched_at=now)
            if q.problem not in th.matched_problems:
                th.matched_problems.append(q.problem)
            th.matched_phrases.append(q.phrase)
    result.threads = sorted(threads.values(), key=lambda th: th.created_at, reverse=True)

    # 2. Filters that need nothing beyond the search result.
    for node_id, th in threads.items():
        node = nodes[node_id]
        reason = (
            filters.community_not_allowed(community)
            or filters.closed(bool(node.get("closed") or node.get("locked")
                                   or (node.get("repository") or {}).get("isArchived")))
            or filters.too_old(th, now=now, max_age_days=days)
            or filters.no_text(th)
        )
        if reason:
            th.drop(reason)
            continue
        if flag := filters.community_flag(community):
            th.flags.append(flag)
        if node.get("isAnswered"):          # None: the category takes no answers
            th.flags.append(t.ANSWERED)
        owner = repo_of(node).split("/")[0]
        if th.author and owner and th.author.lower() == owner.lower():
            th.flags.append(t.POSTED_BY_REPO_OWNER)

    # 3. Already answered by us. A discussion with no comments has no team
    #    comment, so only discussions with comments are read.
    if not pace.team_accounts:
        result.checks_not_run.append(
            "already_answered: no team accounts in pace.yaml, so discussions where the "
            "team has already commented are NOT filtered out"
        )
    else:
        to_read = [nid for nid, th in threads.items() if th.status == t.STATUS_FOUND
                   and (nodes[nid].get("comments") or {}).get("totalCount")]
        try:
            authors = client.comment_authors(to_read)
        except GithubError as exc:
            authors = {}
            result.checks_not_run.append(
                f"already_answered: the comment-author query failed ({exc}); NO "
                "discussion was checked for a team comment"
            )
        for nid, (names, complete) in authors.items():
            th = threads[nid]
            if reason := filters.already_answered(names, pace.team_accounts):
                th.drop(reason)
            elif not complete:
                th.flags.append(t.TEAM_CHECK_PARTIAL)

    failed = [r.phrase for r in result.phrases if r.error]
    if failed:
        result.checks_not_run.append(
            f"{len(failed)} of {len(result.phrases)} phrases failed; discussions only "
            "they would have found are NOT in the output"
        )
    result.checks_not_run.append(
        "comments: phrases are matched against the opening post only, not the replies"
    )
    result.checks_not_run.append(
        "repo rules: each repo may have its own code of conduct; only GitHub's "
        "Acceptable Use Policies are recorded in communities.yaml"
    )
    result.checks_not_run.append(
        "pace_cap: no record of posted replies exists yet, so the weekly cap is not applied"
    )
    result.requests = client.requests
    return result
