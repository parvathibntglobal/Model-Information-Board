"""HTTP calls to the Algolia HN Search API. GET only."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

BASE_URL = "https://hn.algolia.com/api/v1"
SEARCH_BY_DATE = "/search_by_date"
ITEM = "/items/{id}"

PER_PAGE = 50
MIN_INTERVAL_SECONDS = 1.0
TIMEOUT_SECONDS = 20.0


class HackerNewsError(RuntimeError):
    pass


class HackerNewsClient:
    def __init__(
        self,
        user_agent: str,
        *,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not user_agent or not user_agent.strip():
            # No anonymous requests: an empty User-Agent is a config error,
            # not something to fill in with a made-up default.
            raise HackerNewsError("USER_AGENT is empty; set it in .env (see .env.example)")
        self._http = http or httpx.Client(timeout=TIMEOUT_SECONDS)
        self._headers = {"User-Agent": user_agent}
        self._sleep = sleep
        self._clock = clock
        self._last: float | None = None
        self.requests = 0

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._last is not None:
            wait = MIN_INTERVAL_SECONDS - (self._clock() - self._last)
            if wait > 0:
                self._sleep(wait)
        response = self._http.get(BASE_URL + path, params=params, headers=self._headers)
        self._last = self._clock()
        self.requests += 1
        if response.status_code != 200:
            raise HackerNewsError(
                f"HN Algolia HTTP {response.status_code} for {path}: {response.text[:200]!r}"
            )
        return response.json()

    def search_recent(
        self, phrase: str, *, since_epoch: int, max_pages: int = 1
    ) -> tuple[list[dict[str, Any]], int, bool]:
        """Stories and comments matching `phrase`, newest first, created after
        `since_epoch`: (hits, Algolia's reported nbHits, whether every page was
        read). nbHits is an estimate (Algolia marks it non-exhaustive), so it is
        reported as Algolia's figure, never as a count of what exists."""
        hits: list[dict[str, Any]] = []
        total = 0
        for page in range(max_pages):
            data = self._get(
                SEARCH_BY_DATE,
                {
                    "query": phrase,
                    "tags": "(story,comment)",
                    "numericFilters": f"created_at_i>{since_epoch}",
                    "hitsPerPage": PER_PAGE,
                    "page": page,
                },
            )
            hits.extend(data.get("hits") or [])
            total = int(data.get("nbHits") or len(hits))
            if page + 1 >= int(data.get("nbPages") or 0):
                return hits, total, True
        return hits, total, False

    def thread_authors(self, story_id: str) -> set[str]:
        """Every author who has posted anywhere in the story's thread."""
        authors: set[str] = set()
        stack = [self._get(ITEM.format(id=story_id))]
        while stack:
            node = stack.pop()
            if node.get("author"):
                authors.add(node["author"])
            stack.extend(node.get("children") or ())
        return authors
