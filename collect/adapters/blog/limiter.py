"""Per-host politeness. One request at a time, spaced.

Per *host*, not global: forty feeds on forty hosts should not serialise behind
each other, and two feeds on one host must not double that host's rate. The
`robots.txt` `Crawl-delay` widens the interval for the host that asked for it
and no other.

The clock and the sleep are injected so the tests measure the arithmetic rather
than waiting for it. A limiter tested with real sleeps is a limiter that is
eventually tested with `min_interval=0`, which is not the same code path.
"""

from __future__ import annotations

import logging
import time
from urllib.parse import urlsplit

log = logging.getLogger(__name__)

#: collect/CLAUDE.md: blogs are RSS and sitemaps, "be polite, ~1 req/sec".
DEFAULT_MIN_INTERVAL = 1.0


class HostLimiter:
    """Spaces requests per host. Not thread-safe, and does not need to be.

    The blog sweep is a single sequential pass by design: concurrency here buys
    minutes on a weekly job and risks looking like a scraper to forty small
    sites at once.
    """

    def __init__(
        self,
        *,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        clock=time.monotonic,
        sleeper=time.sleep,
    ) -> None:
        self.min_interval = min_interval
        self._clock = clock
        self._sleeper = sleeper
        self._last_request: dict[str, float] = {}

    @staticmethod
    def host_of(url: str) -> str:
        parts = urlsplit(url)
        return (parts.hostname or "").lower()

    def wait(self, url: str, *, min_interval: float | None = None) -> float:
        """Block until this host may be hit again. Returns seconds waited.

        The timestamp is recorded when the wait ends — i.e. at the moment the
        caller is about to issue the request — so the interval measures
        request-start to request-start and a slow response does not shorten the
        gap to the next one.
        """
        interval = (
            self.min_interval
            if min_interval is None
            else max(self.min_interval, min_interval)
        )
        host = self.host_of(url)
        now = self._clock()
        last = self._last_request.get(host)

        waited = 0.0
        if last is not None:
            remaining = interval - (now - last)
            if remaining > 0:
                log.debug("host limiter: sleeping %.3fs before %s", remaining, host)
                self._sleeper(remaining)
                waited = remaining
                now = self._clock()

        self._last_request[host] = now
        return waited
