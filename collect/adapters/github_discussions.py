"""GitHub Discussions: what engineers write in repos' discussion boards.

ADDED 2026-10-26, as the first of the discussion platforms scoped that day.
Measured then: 618 discussions created in 30 days across 18 LLM repos
(GraphQL search; llama.cpp 120, zed 122, codex 149, open-webui 103), with
llama.cpp's Q&A and Show-and-tell carrying first-hand benchmark tables.

SAME TERMS, SAME DOCUMENT SHAPE AS GITHUB ISSUES. Discussions sit under the
GitHub Acceptable Use Policy the `github` source already records, reached
through the same API (`access_path: api`), so the terms gate is the one
`harvest_github` runs. A discussion is written exactly as an issue is: one
`document` per discussion, `source = 'github'`, `external_id` = `owner/repo#N`
- issues, pull requests and discussions share ONE number sequence per repo, so
the two cannot collide - through `github.write_issue_documents`.

THE STORED PAYLOAD CARRIES `title` AND `body`, so `assemble.prose.
github_issue_prose` turns it into text unchanged, and a quote verifies against
the author's prose, never against JSON. The opening post only, as for issues:
replies are other voices and are not fetched yet (rule 9: nothing is stored
that nothing reads).

SEARCH. GraphQL `search(type: DISCUSSION)`, one query per spelling of the
model, `in:title,body`, newest first, across all of GitHub. Not scoped to a
repo list: GitHub caps a search query at 256 characters, which ten `repo:`
qualifiers exceed, and the active boards move between repos. What keeps the
results on-subject is the sieve every GitHub hit already passes: the hit must
name the model in one of its spellings (`sieve.matches`).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from collect.adapters.github import (
    MAX_ATTEMPTS,
    SEARCH_INTERVAL,
    GitHubHarvester,
    SearchHit,
    StoredIssue,
)
from collect.adapters.queries.github import github_alias_form
from collect.adapters.queries.sieve import matches, normalize
from collect.limiter import HostLimiter
from collect.rawstore import RAW, RawStore

log = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.github.com/graphql"

#: Results asked for per search. GraphQL search pages at 100; one page of the
#: newest is what a per-model fetch needs, and it costs one point.
PER_QUERY = 50

#: GitHub refuses a search query longer than this many characters.
MAX_QUERY_CHARS = 256

_QUERY = """
query($q: String!, $first: Int!) {
  search(query: $q, type: DISCUSSION, first: $first) {
    discussionCount
    nodes {
      ... on Discussion {
        number title body url createdAt upvoteCount
        repository { nameWithOwner }
        category { name }
        author { login ... on User { databaseId } }
        comments { totalCount }
      }
    }
  }
  rateLimit { cost remaining resetAt }
}
"""


def discussion_query(surface: str) -> str:
    """`"<alias>" in:title,body sort:created-desc` - one spelling, newest first."""
    query = f'"{github_alias_form(surface)}" in:title,body sort:created-desc'
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"discussion query is {len(query)} characters; GitHub's limit is "
                         f"{MAX_QUERY_CHARS}: {query[:80]}")
    return query


@dataclass
class DiscussionRun:
    """One discussion search: what came back, what passed, what was stored."""

    query: str
    total_count: int | None = None
    retrieved: int = 0
    search_calls: int = 0
    http_errors: int = 0
    rate_limited: bool = False
    rejected: int = 0
    stored: list[StoredIssue] = field(default_factory=list)


def _hit_of(node: dict[str, Any]) -> SearchHit | None:
    """A Discussion node as the `SearchHit` the GitHub writer already takes.
    None for a node that is not a discussion (search can return an empty `{}`
    for an item the token cannot see)."""
    if not node or not node.get("url") or node.get("number") is None:
        return None
    author = node.get("author") or {}
    uid = author.get("databaseId")
    return SearchHit(
        api_url=node["url"],
        html_url=node["url"],
        repo=(node.get("repository") or {}).get("nameWithOwner") or "",
        number=int(node["number"]),
        title=node.get("title") or "",
        body=node.get("body") or "",
        created_at=node.get("createdAt"),
        author=author.get("login"),
        # `databaseId` is GitHub's numeric user id - the same id REST calls
        # `user.id` - so a person is one author across issues and discussions.
        author_external_id=str(uid) if uid is not None else None,
        comment_count=int((node.get("comments") or {}).get("totalCount") or 0),
        reactions=int(node.get("upvoteCount") or 0),
    )


class DiscussionHarvester:
    """Searches discussions, sieves on the model's spellings, stores survivors."""

    def __init__(self, *, client: httpx.Client, store: RawStore,
                 limiter: HostLimiter | None = None, max_keep_per_query: int = 25,
                 sleeper=time.sleep, epoch=time.time) -> None:
        self._client = client
        self._store = store
        self._limiter = HostLimiter(min_interval=SEARCH_INTERVAL) if limiter is None else limiter
        self._max_keep = max_keep_per_query
        self._sleep = sleeper
        # Throttle detection and back-off are the issues adapter's, reused so
        # the two arms cannot disagree about what a throttle looks like.
        self._throttle = GitHubHarvester(client=client, store=store, sleeper=sleeper, epoch=epoch)
        self.ledger: list[DiscussionRun] = []

    def totals(self) -> dict[str, int]:
        """Over every run performed, not over what the caller kept."""
        return {
            "queries": len(self.ledger),
            "search_calls": sum(r.search_calls for r in self.ledger),
            "http_errors": sum(r.http_errors for r in self.ledger),
            "rate_limited_queries": sum(1 for r in self.ledger if r.rate_limited),
            "retrieved": sum(r.retrieved for r in self.ledger),
            "rejected": sum(r.rejected for r in self.ledger),
            "stored": sum(len(r.stored) for r in self.ledger),
        }

    def _search(self, run: DiscussionRun) -> dict[str, Any] | None:
        """One GraphQL search, retried once on a throttle. None when it failed:
        the caller must not read that as "no discussions"."""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._limiter.wait(GRAPHQL_URL)
            response = self._client.post(GRAPHQL_URL, json={
                "query": _QUERY, "variables": {"q": run.query, "first": PER_QUERY}})
            run.search_calls += 1
            if response.status_code == 200:
                payload = response.json()
                if payload.get("errors"):
                    # GraphQL answers 200 with `errors` for a refused query.
                    run.http_errors += 1
                    log.error("discussion search refused: %s", str(payload["errors"])[:200])
                    return None
                return payload
            if self._throttle.is_throttled(response):
                if attempt < MAX_ATTEMPTS:
                    self._sleep(self._throttle._backoff_seconds(response))
                    continue
                run.rate_limited = True
            run.http_errors += 1
            log.error("discussion search failed %s: %s", response.status_code, response.text[:200])
            return None
        return None  # pragma: no cover - the loop always returns

    def harvest(self, surface: str, variants: list[str]) -> DiscussionRun:
        """Search one spelling; keep hits that name ANY spelling of the model."""
        run = DiscussionRun(query=discussion_query(surface))
        self.ledger.append(run)
        payload = self._search(run)
        if payload is None:
            return run
        search = (payload.get("data") or {}).get("search") or {}
        run.total_count = search.get("discussionCount")
        hits = [h for h in (_hit_of(n) for n in search.get("nodes") or []) if h is not None]
        run.retrieved = len(hits)
        for hit in hits:
            text = normalize(f"{hit.title}\n{hit.body}")
            if not any(matches(v, text) for v in variants):
                run.rejected += 1
                continue
            if len(run.stored) >= self._max_keep:
                break
            run.stored.append(self._store_hit(hit))
        return run

    def _store_hit(self, hit: SearchHit) -> StoredIssue:
        """The discussion's own payload - `title` and `body` at the top, which
        is what `github_issue_prose` reads - stored once, content-addressed."""
        blob = json.dumps({
            "kind": "discussion",
            "url": hit.html_url,
            "repository": hit.repo,
            "number": hit.number,
            "title": hit.title,
            "body": hit.body,
            "created_at": hit.created_at,
            "author_id": hit.author_external_id,
            "comments": hit.comment_count,
            "upvotes": hit.reactions,
        }, sort_keys=True, ensure_ascii=False).encode("utf-8")
        put = self._store.put(blob, namespace=RAW)
        return StoredIssue(external_id=hit.external_id, html_url=hit.html_url, ref=put.ref,
                           content_hash=put.content_hash, size=put.size,
                           already_present=put.already_present, hit=hit)
