"""The robots.txt gate. Consulted before every request, including redirects.

WHY THE STDLIB PARSER BUT NOT ITS FETCH
---------------------------------------
`urllib.robotparser` is the right parser and the wrong client:
`RobotFileParser.read()` calls `urllib.request.urlopen`, which is a third path
around `build_client` alongside feedparser's and trafilatura's. So robots.txt is
fetched with the lane's own client and handed to `RobotFileParser.parse()`.
`read()` is never called.

WHAT AN ANSWER IS, AND WHAT IS NOT AN ANSWER
--------------------------------------------
Fail closed on *no answer*; fail open only on an explicit "there are no rules".
The distinction is rule 6, and getting it backwards is expensive in both
directions:

    200                     obey what it says
    401, 403                a refusal. Disallowed entirely
    404, 410                the server answered: there are no rules. Allowed
    5xx, timeout, refused   no answer. Disallowed for this host, this run
    other 4xx               no answer. Disallowed
    non-text, oversized,    no answer. Disallowed
    undecodable

A 404 is a **definite value**, not a missing one. Treating it as denial would
exclude most small blogs permanently — and blogs are the only positive-evidence
channel, so silent-failure capabilities could never reach positive consensus.
That is rule 4 with the harm pointing the other way.

RFC 9309 would allow all on any 4xx. We are deliberately stricter: a 429 or a
418 is not a statement about crawling, and `assert_terms_reviewed`'s reasoning
applies — absence of permission is not permission.

WHAT THIS CANNOT YET RECORD
---------------------------
A host skipped for an unreachable robots.txt is a silence the schema has
nowhere to hold. `coverage_gap.kind` is a closed CHECK set of four and none of
them fit; `harvest_run.http_errors` is the wrong counter, because our fetch did
not fail, we declined to make it. Until the proposed `harvest_run.outcome`
column exists, the ruling is logged at ERROR *and* returned in the run result,
so nothing swallows it. This is the one place in the fetch path that produces a
gap the database cannot represent, and it is on the list sent to Engineer 2.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

log = logging.getLogger(__name__)

#: `rules`     a robots.txt was served and parsed
#: `no-rules`  the server said there is no robots.txt (404, 410)
#: `refused`   the server refused to serve it (401, 403) — treated as a full deny
#: `no-answer` nothing usable came back. Fail closed
RobotsStatus = Literal["rules", "no-rules", "refused", "no-answer"]

#: robots.txt files are a few kilobytes. Anything past this is not a robots.txt,
#: and reading it into memory to find that out is the mistake.
MAX_ROBOTS_BYTES = 512_000

#: One hour. Long enough that a sweep does not re-fetch per article, short
#: enough that a publisher changing their mind is honoured the same day.
DEFAULT_TTL_SECONDS = 3600.0

#: Politeness floor from collect/CLAUDE.md: roughly one request per second.
#: `Crawl-delay` may widen it. Nothing narrows it.
DEFAULT_MIN_INTERVAL = 1.0


@dataclass(frozen=True)
class RobotsRuling:
    """What one origin's robots.txt said, or why we could not find out."""

    origin: str
    status: RobotsStatus
    detail: str
    crawl_delay: float | None = None
    http_status: int | None = None
    fetched_at: float = 0.0

    #: Excluded from equality: it is a parser, and two rulings are the same
    #: ruling when they say the same thing about the same origin.
    parser: RobotFileParser | None = field(default=None, compare=False, repr=False)

    @property
    def answered(self) -> bool:
        """Did the server tell us anything at all?"""
        return self.status != "no-answer"


@dataclass(frozen=True)
class RobotsDecision:
    """Whether one URL may be fetched, and which ruling decided it."""

    url: str
    allowed: bool
    reason: str
    ruling: RobotsRuling


def origin_of(url: str) -> str:
    """`https://host:port` — the scope a robots.txt covers.

    Per-scheme and per-port on purpose: `http://host` and `https://host` are
    different origins for robots purposes, and treating them as one would apply
    permission granted for one to the other.
    """
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        raise ValueError(f"not an absolute URL: {url!r}")
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


class RobotsGate:
    """Fetches, caches and applies robots.txt for a run.

    The client is injected rather than built here: there is exactly one place
    in this lane that builds an HTTP client, and a gate that built its own
    would be a fourth way to make an unidentified request.
    """

    def __init__(
        self,
        client: httpx.Client,
        *,
        user_agent: str,
        max_bytes: int = MAX_ROBOTS_BYTES,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        clock=time.monotonic,
    ) -> None:
        self._client = client
        self._user_agent = user_agent
        self._max_bytes = max_bytes
        self._ttl = ttl_seconds
        self._clock = clock
        self._cache: dict[str, RobotsRuling] = {}

    # ── the ruling ───────────────────────────────────────────────────────

    def ruling_for(self, url: str) -> RobotsRuling:
        """The cached ruling for this URL's origin, fetching it if needed."""
        origin = origin_of(url)
        cached = self._cache.get(origin)
        if cached is not None and self._clock() - cached.fetched_at < self._ttl:
            return cached
        ruling = self._fetch_ruling(origin)
        self._cache[origin] = ruling
        return ruling

    def _fetch_ruling(self, origin: str) -> RobotsRuling:
        robots_url = f"{origin}/robots.txt"
        try:
            response = self._client.get(robots_url, follow_redirects=True)
        except httpx.HTTPError as error:
            return self._no_answer(
                origin,
                f"{type(error).__name__} fetching {robots_url}: {error}",
            )

        status = response.status_code

        if status in (401, 403):
            return RobotsRuling(
                origin=origin,
                status="refused",
                detail=f"{robots_url} returned {status}: access to the rules was refused, "
                "which is a refusal to be crawled.",
                http_status=status,
                fetched_at=self._clock(),
            )

        if status in (404, 410):
            return RobotsRuling(
                origin=origin,
                status="no-rules",
                detail=f"{robots_url} returned {status}: the server answered, and the "
                "answer is that there are no rules.",
                http_status=status,
                fetched_at=self._clock(),
            )

        if status != 200:
            return self._no_answer(
                origin,
                f"{robots_url} returned {status}, which says nothing about crawling.",
                http_status=status,
            )

        content_type = response.headers.get("content-type", "")
        media_type = content_type.split(";")[0].strip().lower()
        if media_type and not media_type.startswith("text/"):
            return self._no_answer(
                origin,
                f"{robots_url} returned content-type {media_type!r}, which is not a "
                "robots.txt.",
                http_status=status,
            )

        body = response.content
        if len(body) > self._max_bytes:
            return self._no_answer(
                origin,
                f"{robots_url} returned {len(body)} bytes, past the {self._max_bytes}-byte "
                "limit. Not a robots.txt.",
                http_status=status,
            )

        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as error:
            return self._no_answer(
                origin,
                f"{robots_url} is not valid UTF-8 ({error}), so its rules cannot be read.",
                http_status=status,
            )

        parser = RobotFileParser()
        parser.parse(text.splitlines())
        return RobotsRuling(
            origin=origin,
            status="rules",
            detail=f"{robots_url} parsed, {len(text.splitlines())} line(s).",
            crawl_delay=self._crawl_delay_from(parser),
            http_status=status,
            fetched_at=self._clock(),
            parser=parser,
        )

    def _no_answer(
        self, origin: str, detail: str, *, http_status: int | None = None
    ) -> RobotsRuling:
        # Logged at ERROR, not WARNING: this excludes a host from the corpus,
        # and an exclusion nobody is told about reads as "nobody wrote about
        # this" on the page (rule 4).
        log.error(
            "robots.txt unreachable for %s, so nothing will be fetched from it this run. "
            "An unreachable robots.txt is not permission. %s",
            origin,
            detail,
        )
        return RobotsRuling(
            origin=origin,
            status="no-answer",
            detail=detail,
            http_status=http_status,
            fetched_at=self._clock(),
        )

    def _crawl_delay_from(self, parser: RobotFileParser) -> float | None:
        """`Crawl-delay`, or a delay derived from `Request-rate`, in seconds."""
        try:
            delay = parser.crawl_delay(self._user_agent)
        except Exception:  # pragma: no cover - defensive: parser internals
            delay = None
        if delay is not None:
            try:
                return float(delay)
            except (TypeError, ValueError):  # pragma: no cover - malformed value
                return None

        try:
            rate = parser.request_rate(self._user_agent)
        except Exception:  # pragma: no cover - defensive: parser internals
            rate = None
        if rate and getattr(rate, "requests", 0) > 0 and getattr(rate, "seconds", 0) > 0:
            return float(rate.seconds) / float(rate.requests)
        return None

    # ── the decision ─────────────────────────────────────────────────────

    def allows(self, url: str) -> RobotsDecision:
        """May this exact URL be fetched?"""
        ruling = self.ruling_for(url)

        if ruling.status == "refused":
            return RobotsDecision(url, False, "robots.txt access refused", ruling)

        if ruling.status == "no-answer":
            return RobotsDecision(
                url,
                False,
                "robots.txt gave no answer, and an unreachable robots.txt is not permission",
                ruling,
            )

        if ruling.status == "no-rules":
            return RobotsDecision(url, True, "no robots.txt: no rules to break", ruling)

        parser = ruling.parser
        if parser is None:  # pragma: no cover - only reachable via a corrupt ruling
            return RobotsDecision(url, False, "ruling carries no parsed rules", ruling)

        allowed = parser.can_fetch(self._user_agent, url)
        return RobotsDecision(
            url,
            allowed,
            "allowed by robots.txt" if allowed else "disallowed by robots.txt",
            ruling,
        )

    def min_interval(self, url: str, *, floor: float = DEFAULT_MIN_INTERVAL) -> float:
        """Seconds to leave between requests to this host.

        The floor is ours and the delay is theirs, and the larger wins. A
        publisher asking for 10 seconds gets 10; one asking for 0.1 still gets
        our 1, because their robots.txt is permission to go slower, not an
        instruction to go faster.
        """
        delay = self.ruling_for(url).crawl_delay
        return max(floor, delay) if delay is not None else floor
