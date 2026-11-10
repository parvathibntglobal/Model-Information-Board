"""GET-only calls to the RapidAPI service that fronts Reddit (`reddit34`).

Every failure raises `RedditError`, so a failure can never be read as "no
posts". The provider's quirks this handles, each measured:

    HTTP 429         after 32 rapid calls, no Retry-After (MIB, 2026-08-14).
                     Waited out once (60s, what cleared it then), then raised.
    "data not found" HTTP 200, `success: false`. Transient as often as real
                     (see __init__.py). Retried twice, then raised.
    other `success: false`
                     a refused request (e.g. a bad parameter). Raised at once
                     with the provider's message; retrying cannot change it.

The quota headers are read on every response and kept, so a run can say how
much of the shared monthly quota is left.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

LISTING = "/getPostsBySubreddit"

# The listing's own spelling. MIB measured that `NEW` (search's spelling)
# returns HTTP 200 with no `posts` key, which would read as an empty week.
SORT_NEW = "new"

PER_PAGE = 25  # what the provider returns; not a parameter

# 20 a minute. The subscription is shared with MIB's Reddit sweep, which paces
# at 25; 429 arrives at the 32nd rapid call. Below both, so the two together
# are less likely to trip it, not guaranteed not to.
MIN_INTERVAL_SECONDS = 3.0
BACKOFF_SECONDS = 60.0
EMPTY_RETRIES = 2
TIMEOUT_SECONDS = 60.0

DATA_NOT_FOUND = "data not found"

_QUOTA_HEADERS = {
    "x-ratelimit-requests-remaining": "quota_remaining",
    "x-ratelimit-requests-limit": "quota_limit",
    "x-ratelimit-requests-reset": "quota_reset_seconds",
}


class RedditError(RuntimeError):
    pass


def host_for(provider: str | None, rapidapi_host: str | None) -> str:
    """The RapidAPI host for Reddit. Same order as MIB's `reddit.host_for`.

    1. REDDIT_PROVIDER, as `<provider>.p.rapidapi.com`.
    2. RAPIDAPI_HOST, only when it names a Reddit provider. One that names
       another vendor (X's `twitter241`) is refused: Reddit's paths sent there
       404, which reads like Reddit changing its API.
    3. Neither: refused. No provider is defaulted in code.
    """
    if provider and provider.strip():
        return f"{provider.strip()}.p.rapidapi.com"
    shared = (rapidapi_host or "").strip()
    if shared and "reddit" in shared.lower():
        return shared
    if shared:
        raise RedditError(
            f"RAPIDAPI_HOST is {shared!r}, which is not a Reddit provider. Set "
            "REDDIT_PROVIDER (the board uses 'reddit34') in .env.")
    raise RedditError("neither REDDIT_PROVIDER nor RAPIDAPI_HOST is set in .env; "
                      "no Reddit host to call (the board uses 'reddit34')")


class RedditClient:
    def __init__(
        self,
        api_key: str,
        host: str,
        user_agent: str,
        *,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not api_key or not api_key.strip():
            raise RedditError("RAPIDAPI_KEY is empty; set it in .env (see .env.example)")
        if not host or "/" in host:
            raise RedditError(f"host must be a bare host such as "
                              f"'reddit34.p.rapidapi.com', got {host!r}")
        if not user_agent or not user_agent.strip():
            raise RedditError("USER_AGENT is empty; set it in .env (see .env.example)")
        self.base = f"https://{host}"
        self._http = http or httpx.Client(timeout=TIMEOUT_SECONDS)
        self._headers = {"x-rapidapi-key": api_key, "x-rapidapi-host": host,
                         "User-Agent": user_agent, "Accept": "application/json"}
        self._sleep = sleep
        self._clock = clock
        self._last: float | None = None
        self.requests = 0
        self.rate_limited = 0
        self.empty_retries = 0
        # None until a response carries the header: unread is not a value.
        self.quota_remaining: int | None = None
        self.quota_limit: int | None = None
        self.quota_reset_seconds: int | None = None

    def _send(self, path: str, params: dict[str, Any]) -> httpx.Response:
        if self._last is not None:
            wait = MIN_INTERVAL_SECONDS - (self._clock() - self._last)
            if wait > 0:
                self._sleep(wait)
        try:
            response = self._http.get(self.base + path, params=params, headers=self._headers)
        except httpx.HTTPError as exc:
            raise RedditError(f"{path}: {type(exc).__name__}: {exc}") from exc
        finally:
            self._last = self._clock()
            self.requests += 1
        for header, attr in _QUOTA_HEADERS.items():
            value = response.headers.get(header)
            if value is not None and value.strip().isdigit():
                setattr(self, attr, int(value))
        return response

    def _data(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """The response's `data` mapping, or RedditError. Never an empty stand-in."""
        backed_off = False
        empties = 0
        while True:
            response = self._send(path, params)
            if response.status_code == 429 and not backed_off:
                self.rate_limited += 1
                backed_off = True
                self._sleep(BACKOFF_SECONDS)
                continue
            if response.status_code != 200:
                raise RedditError(f"{path} {params}: HTTP {response.status_code}: "
                                  f"{response.text[:200]!r}")
            try:
                body = response.json()
            except ValueError as exc:
                raise RedditError(f"{path} {params}: response is not JSON") from exc
            data = body.get("data") if isinstance(body, dict) else None
            if isinstance(data, dict):
                return data
            if data == DATA_NOT_FOUND and empties < EMPTY_RETRIES:
                empties += 1
                self.empty_retries += 1
                continue
            if data == DATA_NOT_FOUND:
                raise RedditError(
                    f"{path} {params}: '{DATA_NOT_FOUND}' on {empties + 1} tries. The "
                    "provider sends this as a transient decline as well as for a "
                    "real empty, so it is NOT read as zero posts")
            raise RedditError(f"{path} {params}: refused: {str(data)[:200]!r}")

    def newest_posts(
        self, subreddit: str, cursor: str | None = None
    ) -> tuple[list[dict[str, Any]], str | None]:
        """One page of a subreddit's newest posts and the cursor to the next
        (None when the provider sends none: the listing has no older page)."""
        params: dict[str, Any] = {"subreddit": subreddit, "sort": SORT_NEW}
        if cursor:
            params["cursor"] = cursor
        data = self._data(LISTING, params)
        if "posts" not in data:
            # MIB's `NEW` spelling bug looked exactly like this: HTTP 200, no
            # posts key. An empty week is `posts: []`, never a missing key.
            raise RedditError(f"{LISTING} {params}: response has no 'posts' key "
                              f"(keys: {sorted(data)})")
        posts = [p.get("data", p) if isinstance(p, dict) else p
                 for p in data.get("posts") or ()]
        return posts, (data.get("cursor") or None)
