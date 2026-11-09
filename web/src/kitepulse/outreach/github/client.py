"""GitHub GraphQL, read-only: discussion search and comment authors.

Every request is a POST to /graphql (that is how GraphQL takes reads), paced
and counted by `common/http.py`. `graphql()` refuses any document that does not
start with `query`, so nothing sent from here can change anything on GitHub.

A response with `errors` fails, even when it also carries data: GitHub returns
partial data beside RESOURCE_LIMITS_EXCEEDED, and a partial page read as a
whole one would be a silent gap.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any

from common.http import FetchError, ReadOnlyClient

BASE_URL = "https://api.github.com"
GRAPHQL = "/graphql"

# Search is limited to 30 requests a minute (observed on MIB's harvest token,
# contract/sources.yaml); one every 2 seconds stays under it.
MIN_INTERVAL_SECONDS = 2.0
PER_PAGE = 25            # 100 with bodyText exceeded GitHub's resource limit
TEAM_CHECK_BATCH = 10    # discussions per comment-author query
COMMENTS_READ = 50       # top-level comments read per discussion
REPLIES_READ = 20        # replies read per comment
RETRY_STATUSES = (502, 503, 504)
MAX_QUERY_CHARS = 256    # GitHub refuses a longer search string

TOKEN_ENV = "KP_GITHUB_TOKEN"

GithubError = FetchError

SEARCH = """
query($q: String!, $first: Int!, $after: String) {
  search(query: $q, type: DISCUSSION, first: $first, after: $after) {
    discussionCount
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on Discussion {
        id number title url createdAt closed locked isAnswered bodyText
        repository { nameWithOwner isArchived }
        category { name }
        author { login }
        comments { totalCount }
      }
    }
  }
}
"""

COMMENT_AUTHORS = """
query($ids: [ID!]!, $comments: Int!, $replies: Int!) {
  nodes(ids: $ids) {
    ... on Discussion {
      id
      comments(first: $comments) {
        totalCount
        nodes {
          author { login }
          replies(first: $replies) { totalCount nodes { author { login } } }
        }
      }
    }
  }
}
"""


def token_from_env() -> str:
    """Kite Pulse's own token. No fallback to MIB's GITHUB_TOKEN: borrowing it
    silently would spend MIB's budget under MIB's name."""
    token = (os.environ.get(TOKEN_ENV) or "").strip()
    if not token:
        raise GithubError(
            f"{TOKEN_ENV} is not set. GitHub's GraphQL API needs a token: create a "
            "fine-grained token with 'Public repositories (read-only)' and no "
            f"permissions, and put it in .env as {TOKEN_ENV}=..."
        )
    return token


def search_string(phrase: str, *, since: datetime) -> str:
    if '"' in phrase:
        raise GithubError(f"phrase {phrase!r} contains a double quote")
    q = f'"{phrase}" in:title,body created:>={since.date().isoformat()} sort:created-desc'
    if len(q) > MAX_QUERY_CHARS:
        raise GithubError(f"search string is {len(q)} characters; GitHub's limit is "
                          f"{MAX_QUERY_CHARS}")
    return q


def created_at(node: dict[str, Any]) -> datetime:
    value = node.get("createdAt")
    if not isinstance(value, str):
        raise GithubError(f"discussion {node.get('url')} has no createdAt")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class GithubClient(ReadOnlyClient):
    def __init__(self, user_agent: str, token: str, **kwargs: Any) -> None:
        super().__init__(BASE_URL, user_agent, min_interval=MIN_INTERVAL_SECONDS, **kwargs)
        if not token or not token.strip():
            raise GithubError(f"{TOKEN_ENV} is empty")
        self._post_headers = {**self._headers, "Authorization": f"Bearer {token.strip()}"}

    def _post_query(self, body: dict[str, Any]) -> Any:
        # The one POST in outreach (tests/test_kp_outreach_guards.py pins it).
        return self._http.post(self.base + GRAPHQL, json=body, headers=self._post_headers)

    def graphql(self, document: str, variables: dict[str, Any]) -> dict[str, Any]:
        if not document.lstrip().startswith("query"):
            raise GithubError("only GraphQL queries are sent; this document is not one")
        if not self.allows(GRAPHQL):
            raise GithubError(f"{BASE_URL}/robots.txt disallows {GRAPHQL}; not requested")
        body = {"query": document, "variables": variables}
        for attempt in (1, 2):
            response = self._paced(GRAPHQL, lambda: self._post_query(body))
            if response.status_code in RETRY_STATUSES and attempt == 1:
                continue      # GitHub search answers 502 now and then; once more
            break
        if response.status_code != 200:
            hint = ""
            if response.status_code in (403, 429):
                hint = (f" (rate limited? retry-after={response.headers.get('retry-after')}, "
                        f"remaining={response.headers.get('x-ratelimit-remaining')})")
            raise GithubError(f"GitHub GraphQL: HTTP {response.status_code}{hint}: "
                              f"{response.text[:200]!r}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise GithubError("GitHub GraphQL: response is not JSON") from exc
        if payload.get("errors"):
            first = payload["errors"][0]
            raise GithubError(f"GitHub GraphQL: {len(payload['errors'])} error(s), first: "
                              f"{first.get('type')}: {first.get('message')}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise GithubError("GitHub GraphQL: response has no data")
        return data

    def search_week(
        self, phrase: str, *, since: datetime, max_pages: int
    ) -> tuple[list[dict[str, Any]], int, bool]:
        """Discussions GitHub returns for the quoted phrase since `since`:
        (nodes, GitHub's reported total, whether every page was read)."""
        q = search_string(phrase, since=since)
        out: list[dict[str, Any]] = []
        after: str | None = None
        total = 0
        for _ in range(max_pages):
            search = self.graphql(SEARCH, {"q": q, "first": PER_PAGE, "after": after})["search"]
            total = int(search["discussionCount"])
            for node in search["nodes"]:
                if not node or not node.get("id"):
                    raise GithubError(f"search {q!r} returned an empty node")
                # The date qualifier was applied, or the phrase fails.
                if created_at(node) < since - timedelta(days=1):
                    raise GithubError(f"search {q!r} returned {node['url']}, created "
                                      f"{node['createdAt']}: the date qualifier was ignored")
            out.extend(search["nodes"])
            info = search["pageInfo"]
            if not info["hasNextPage"]:
                return out, total, True
            after = info["endCursor"]
        return out, total, False

    def comment_authors(self, ids: Iterable[str]) -> dict[str, tuple[set[str], bool]]:
        """Per discussion id: every comment and reply author read, and whether
        every comment and reply was read (False: a long discussion)."""
        ids = list(ids)
        out: dict[str, tuple[set[str], bool]] = {}
        for i in range(0, len(ids), TEAM_CHECK_BATCH):
            batch = ids[i:i + TEAM_CHECK_BATCH]
            data = self.graphql(COMMENT_AUTHORS, {
                "ids": batch, "comments": COMMENTS_READ, "replies": REPLIES_READ})
            for node in data["nodes"]:
                if not node or not node.get("id"):
                    raise GithubError("comment-author query returned an empty node")
                comments = node["comments"]
                names: set[str] = set()
                complete = comments["totalCount"] <= len(comments["nodes"])
                for c in comments["nodes"]:
                    if login := (c.get("author") or {}).get("login"):
                        names.add(login)
                    replies = c["replies"]
                    complete = complete and replies["totalCount"] <= len(replies["nodes"])
                    for r in replies["nodes"]:
                        if login := (r.get("author") or {}).get("login"):
                            names.add(login)
                out[node["id"]] = (names, complete)
            missing = set(batch) - out.keys()
            if missing:
                raise GithubError(f"comment-author query did not return {sorted(missing)}")
        return out
