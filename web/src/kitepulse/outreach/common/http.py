"""A read-only HTTP client for one site: GET only, robots.txt obeyed, paced.

(The one exception is GitHub's GraphQL endpoint, which takes every request,
reads included, as a POST. `github/client.py` sends it through `_paced` and
refuses any document that is not a query; the guard test allows a POST there
and nowhere else.)

robots.txt is read once per client, before the first other request:

    200            its rules apply to every later request
    401, 403       everything is disallowed (Python's robotparser convention)
    other 4xx      no rules: everything is allowed (RFC 9309, section 2.3.1.3)
    5xx, network   an error. Never read as "no rules".

Python's `urllib.robotparser` does not expand a `*` inside a path. The wildcard
rules seen on the sites we read (Discourse's `/*?api_key*`, `/t/*/*.rss`;
dev.to's `/search?q=*`) cover nothing these clients request.

Any non-200 response, a non-JSON body or a disallowed path raises `FetchError`,
so a failure can never be read as "no results".
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any
from urllib import robotparser

import httpx

ROBOTS = "/robots.txt"
TIMEOUT_SECONDS = 60.0


class FetchError(RuntimeError):
    pass


class RobotsDisallowed(FetchError):
    pass


class ReadOnlyClient:
    def __init__(
        self,
        base_url: str,
        user_agent: str,
        *,
        min_interval: float,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not user_agent or not user_agent.strip():
            # No anonymous requests: an empty User-Agent is a config error,
            # not something to fill in with a made-up default.
            raise FetchError("USER_AGENT is empty; set it in .env (see .env.example)")
        self.base = base_url.rstrip("/")
        self._ua = user_agent
        self._min_interval = min_interval
        self._http = http or httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=True)
        self._headers = {"User-Agent": user_agent, "Accept": "application/json"}
        self._sleep = sleep
        self._clock = clock
        self._last: float | None = None
        self._robots: robotparser.RobotFileParser | None = None
        self.requests = 0

    def _paced(self, path: str, send: Callable[[], httpx.Response]) -> httpx.Response:
        """Wait out the interval, send, count. Every request goes through here."""
        if self._last is not None:
            wait = self._min_interval - (self._clock() - self._last)
            if wait > 0:
                self._sleep(wait)
        try:
            return send()
        except httpx.HTTPError as exc:
            raise FetchError(f"{self.base}{path}: {type(exc).__name__}: {exc}") from exc
        finally:
            self._last = self._clock()
            self.requests += 1

    def _fetch(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        return self._paced(path, lambda: self._http.get(
            self.base + path, params=params, headers=self._headers))

    def _rules(self) -> robotparser.RobotFileParser:
        if self._robots is None:
            response = self._fetch(ROBOTS)
            rules = robotparser.RobotFileParser()
            if response.status_code == 200:
                rules.parse(response.text.splitlines())
            elif response.status_code in (401, 403):
                rules.disallow_all = True
            elif 400 <= response.status_code < 500:
                rules.allow_all = True
            else:
                raise FetchError(
                    f"{self.base}{ROBOTS}: HTTP {response.status_code}; not reading a "
                    "site whose robots.txt cannot be read"
                )
            self._robots = rules
        return self._robots

    def allows(self, path: str) -> bool:
        return self._rules().can_fetch(self._ua, self.base + path)

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.allows(path):
            raise RobotsDisallowed(f"{self.base}{ROBOTS} disallows {path}; not requested")
        response = self._fetch(path, params)
        if response.status_code != 200:
            raise FetchError(
                f"{self.base}{path}: HTTP {response.status_code}: {response.text[:200]!r}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise FetchError(f"{self.base}{path}: response is not JSON") from exc
