"""The blog fetch path: robots, politeness, conditional GET, two raw artifacts.

WHAT THIS STAGE PRODUCES, AND WHAT IT DELIBERATELY DOES NOT
-----------------------------------------------------------
Harvest fetches and stores. It does not normalise, extract or flatten.

    feed response bytes     -> raw/   the discovery artifact
    article response bytes  -> raw/   the per-document artifact
    parsed entry metadata   -> in memory, for E3

`document.text_ref` points at the **article** bytes, and `content_hash` is that
article's hash. It cannot point at the feed payload: one feed covers many
entries, so `content_hash` would stop identifying one document — which breaks
dedupe, and breaks NFR-6, where a takedown for one post would land a tombstone
on a blob holding forty.

The extracted plain text is not written here. It is derived and regenerable, so
it belongs in `flattened/` behind `thread_context.flattened_text_ref`, which is
assemble's artifact. `parse.extract_article_text` exists for E3 to call.

Consequence, stated because it is a decision and not a detail: **a document
exists only where the article fetch succeeded.** A discovered entry we could not
fetch is a gap, not a document with a feed-shaped body — including for
full-content feeds, where the alternative is storing bytes we serialised
ourselves into the one namespace that forbids derived content.

THREE THINGS THIS PATH REFUSES TO DO
------------------------------------
1. **Follow a redirect without re-checking robots.txt.** `httpx`'s
   `follow_redirects=True` would move us to a different host, and possibly a
   different origin, with the first host's permission. Every hop is gated, and
   `follow_redirects=False` is passed per request so a client built with the
   opposite default cannot re-enable it.

2. **Read an unbounded body.** A feed URL that turns out to be a video is a
   memory problem discovered by running out of it.

3. **Turn a 304 into an empty result.** `not-modified` is its own outcome all
   the way out to `harvest_run_fields`, because zero-items-fetched is precisely
   what FR-10 exists to alarm on. See `FeedRun.harvest_run_fields`.

WHERE THE ToS GATE SITS
-----------------------
`fetcher_for_source` asserts NFR-5's per-source terms review and is the entry a
driver uses. The constructor is mechanics and does not, so the mechanics can be
tested against recorded fixtures without a test pretending a reading task was
done. With `contract/sources.yaml` as it stands, `fetcher_for_source("blogs")`
refuses — correctly, and until the source ruling lands.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urljoin

import httpx

from collect.adapters.blog.limiter import HostLimiter
from collect.adapters.blog.parse import FeedEntry, ParsedFeed, parse_feed
from collect.adapters.blog.robots import RobotsGate, RobotsRuling
from collect.adapters.blog.validators import (
    FeedValidators,
    InMemoryValidatorStore,
    ValidatorStore,
)
from collect.config import settings
from collect.ids import stable_id
from collect.rawstore import RAW, RawStore

log = logging.getLogger(__name__)

#: The closed set proposed for `harvest_run.outcome`. Two of these — the 304 and
#: the robots skip — are silences the schema cannot represent today, which is
#: the whole reason the column is being proposed rather than assumed.
Outcome = Literal["fetched", "not-modified", "robots-blocked", "error"]

#: A feed or an article past this is not the thing we asked for.
MAX_FEED_BYTES = 8 * 1024 * 1024
MAX_ARTICLE_BYTES = 8 * 1024 * 1024

#: Articles only. A feed linking a PDF or a video is not an article, and
#: storing it as one would put binary into a text pipeline.
ARTICLE_MEDIA_TYPES: frozenset[str] = frozenset(
    {"text/html", "application/xhtml+xml"}
)

#: What a feed reader asks for. Sending nothing is not neutral: servers
#: content-negotiate on it, and a real feed answered **406 Not Acceptable** to a
#: request with no `Accept` during the first live assessment. A 406 arrives here
#: as an `error` outcome, which is indistinguishable from the feed being broken,
#: so the absent header would have read as a dead source.
FEED_ACCEPT = "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8"

#: Same reasoning, different resource. Asking for HTML also makes the
#: `ARTICLE_MEDIA_TYPES` check a statement about what we requested rather than
#: about whatever the server felt like sending.
ARTICLE_ACCEPT = "text/html, application/xhtml+xml;q=0.9, */*;q=0.8"

#: Enough for a canonical-URL or www-to-apex hop. Past that it is a loop or a
#: tracker, and each hop costs a robots ruling.
MAX_REDIRECTS = 3

#: The statuses that actually relocate a resource. Spelled out rather than
#: taken from `httpx.Response.is_redirect`, which is true for **304**: it tests
#: `300 <= code <= 399`, and 304 is in that range without being a redirect.
#: Trusting it made every conditional GET fail as "304 with no Location", which
#: is the FR-10 collision arriving as an HTTP error instead of a 304 — the
#: opposite of what this path exists to keep distinguishable.
REDIRECT_STATUSES: frozenset[int] = frozenset({301, 302, 303, 307, 308})

BLOG_SOURCE_ID = "blogs"


@dataclass(frozen=True)
class StoredArtifact:
    """A payload that reached `raw/`, and the two columns it fills."""

    url: str
    ref: str  # -> document.text_ref
    content_hash: str  # -> document.content_hash
    size: int
    already_present: bool
    http_status: int
    fetched_at: datetime


@dataclass(frozen=True)
class FeedFetch:
    """One feed request. `entries` is empty for every outcome but `fetched`."""

    feed_url: str
    outcome: Outcome
    detail: str
    http_status: int | None = None
    artifact: StoredArtifact | None = None
    parsed: ParsedFeed | None = None
    validators: FeedValidators | None = None
    robots: RobotsRuling | None = None

    @property
    def entries(self) -> list[FeedEntry]:
        return list(self.parsed.entries) if self.parsed else []


@dataclass(frozen=True)
class ArticleFetch:
    """One article request, and the entry it came from."""

    entry: FeedEntry
    url: str | None
    outcome: Outcome
    detail: str
    http_status: int | None = None
    artifact: StoredArtifact | None = None
    robots: RobotsRuling | None = None

    @property
    def stored(self) -> bool:
        return self.artifact is not None


@dataclass(frozen=True)
class FeedRun:
    """Everything `harvest_run` wants about one feed, plus what it cannot hold."""

    feed_url: str
    started_at: datetime
    finished_at: datetime
    outcome: Outcome
    feed: FeedFetch
    articles: list[ArticleFetch] = field(default_factory=list)
    pipeline_version: str = ""

    @property
    def items_fetched(self) -> int:
        """Entries the feed offered. Zero on a 304 — see `harvest_run_fields`."""
        return len(self.feed.entries)

    @property
    def items_kept(self) -> int:
        """FR-10's yield figure: entries whose article actually reached `raw/`."""
        return sum(1 for article in self.articles if article.stored)

    @property
    def http_errors(self) -> int:
        """Requests that failed. A robots skip is not an error — we chose it."""
        failed = 1 if self.feed.outcome == "error" else 0
        return failed + sum(1 for article in self.articles if article.outcome == "error")

    @property
    def robots_blocked(self) -> int:
        blocked = 1 if self.feed.outcome == "robots-blocked" else 0
        return blocked + sum(1 for a in self.articles if a.outcome == "robots-blocked")

    def harvest_run_fields(self) -> dict[str, object]:
        """The row this run would write, and the one field with nowhere to go.

        Every key but `outcome` maps onto a column that exists today. `outcome`
        is the proposed `harvest_run.outcome`, and it is returned rather than
        dropped for a specific reason:

        **A 304 and a broken parser are the same row without it.** Conditional
        GET makes `items_fetched=0, items_kept=0` the normal outcome for an
        unchanged feed, and FR-10's entire job is noticing `items_kept` go to
        zero. Its acceptance — break a selector, alert within one cycle — would
        pass on a fresh feed and fail silently on a cached one.

        `truncated_by` cannot carry it: the set is closed, and a 304 was not cut
        short. Writing no row cannot either: then "unchanged" and "the job never
        ran" are the same absence.

        `exhausted` stays NULL. It means "this query reached the end of its
        results and must not be resumed", and a feed has no end — it is current
        or it is stale. Setting it true would assert something about pagination
        that was never paginated.
        """
        return {
            "id": stable_id("hr", BLOG_SOURCE_ID, self.feed_url, self.started_at.isoformat()),
            "source_id": BLOG_SOURCE_ID,
            "query_key": self.feed_url,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "items_fetched": self.items_fetched,
            "items_kept": self.items_kept,
            "http_errors": self.http_errors,
            "exhausted": None,
            "truncated_by": None,
            "pipeline_version": self.pipeline_version,
            # ── proposed column, not yet in contract/tables.sql ──
            "outcome": self.outcome,
        }


@dataclass(frozen=True)
class _Fetched:
    """Internal: a response that passed the gates, or the reason it did not."""

    outcome: Outcome
    detail: str
    response: httpx.Response | None = None
    robots: RobotsRuling | None = None
    http_status: int | None = None


class BlogFetcher:
    """Fetches feeds and articles politely, and stores what came back.

    Everything it needs is injected: the client (built once, by
    `collect.http.build_client`), the store, the robots gate, the limiter and
    the validator store. Nothing is constructed here, so there is no path by
    which this class makes a request the UA gate did not see.
    """

    def __init__(
        self,
        *,
        client: httpx.Client,
        store: RawStore,
        robots: RobotsGate,
        limiter: HostLimiter | None = None,
        validators: ValidatorStore | None = None,
        max_feed_bytes: int = MAX_FEED_BYTES,
        max_article_bytes: int = MAX_ARTICLE_BYTES,
        max_redirects: int = MAX_REDIRECTS,
        pipeline_version: str | None = None,
        clock=lambda: datetime.now(UTC),
    ) -> None:
        self._client = client
        self._store = store
        self._robots = robots
        # `is None`, not `or`. An injected collaborator that happens to be
        # empty is still the collaborator the caller chose: `or` swaps a
        # freshly-created validator store for the caller's own the moment the
        # caller's is empty, which is every first run. Found by a test that
        # asserted the ETag it had just saved.
        self._limiter = HostLimiter() if limiter is None else limiter
        self._validators = InMemoryValidatorStore() if validators is None else validators
        self._max_feed_bytes = max_feed_bytes
        self._max_article_bytes = max_article_bytes
        self._max_redirects = max_redirects
        self._pipeline_version = pipeline_version or settings().pipeline_version
        self._clock = clock

    # ── the gated request ────────────────────────────────────────────────

    def _get(self, url: str, *, headers: dict[str, str] | None = None) -> _Fetched:
        """One GET, with robots checked on every hop and politeness observed."""
        current = url
        ruling: RobotsRuling | None = None

        for hop in range(self._max_redirects + 1):
            decision = self._robots.allows(current)
            ruling = decision.ruling
            if not decision.allowed:
                return _Fetched(
                    outcome="robots-blocked",
                    detail=f"{current}: {decision.reason} ({ruling.detail})",
                    robots=ruling,
                    http_status=ruling.http_status,
                )

            self._limiter.wait(current, min_interval=self._robots.min_interval(current))

            try:
                response = self._client.get(
                    current, headers=headers, follow_redirects=False
                )
            except httpx.HTTPError as error:
                return _Fetched(
                    outcome="error",
                    detail=f"{type(error).__name__} fetching {current}: {error}",
                    robots=ruling,
                )

            if response.status_code in REDIRECT_STATUSES:
                location = response.headers.get("location")
                if not location:
                    return _Fetched(
                        outcome="error",
                        detail=f"{current} returned {response.status_code} with no Location",
                        robots=ruling,
                        http_status=response.status_code,
                    )
                # Resolved against the URL we actually requested, and re-gated
                # on the next pass: a redirect is a different resource, possibly
                # on a different origin, and the first host's robots.txt says
                # nothing about it.
                current = urljoin(current, location)
                log.debug("blog fetch: hop %d -> %s", hop + 1, current)
                continue

            return _Fetched(
                outcome="fetched",
                detail=f"{current} returned {response.status_code}",
                response=response,
                robots=ruling,
                http_status=response.status_code,
            )

        return _Fetched(
            outcome="error",
            detail=f"{url}: more than {self._max_redirects} redirects",
            robots=ruling,
        )

    def _store_payload(self, url: str, response: httpx.Response) -> StoredArtifact:
        stored = self._store.put(response.content, namespace=RAW)
        return StoredArtifact(
            url=url,
            ref=stored.ref,
            content_hash=stored.content_hash,
            size=stored.size,
            already_present=stored.already_present,
            http_status=response.status_code,
            fetched_at=self._clock(),
        )

    # ── feeds ────────────────────────────────────────────────────────────

    def fetch_feed(self, feed_url: str) -> FeedFetch:
        """Conditional GET on one feed. Stores the payload only when it changed."""
        known = self._validators.load(feed_url) or FeedValidators()
        fetched = self._get(
            feed_url, headers={"Accept": FEED_ACCEPT, **known.request_headers()}
        )

        if fetched.outcome != "fetched" or fetched.response is None:
            return FeedFetch(
                feed_url=feed_url,
                outcome=fetched.outcome,
                detail=fetched.detail,
                http_status=fetched.http_status,
                robots=fetched.robots,
                validators=known if not known.is_empty else None,
            )

        response = fetched.response
        status = response.status_code

        if status == 304:
            # The server confirmed nothing changed. Validators are NOT cleared:
            # a 304 need not resend them, and absent is not "no validator"
            # (rule 6). Nothing is stored, because nothing arrived.
            refreshed = known.merge(FeedValidators.from_response_headers(response.headers))
            self._validators.save(feed_url, refreshed)
            return FeedFetch(
                feed_url=feed_url,
                outcome="not-modified",
                detail=f"{feed_url} returned 304: unchanged since the last run",
                http_status=status,
                validators=refreshed,
                robots=fetched.robots,
            )

        if status >= 400:
            return FeedFetch(
                feed_url=feed_url,
                outcome="error",
                detail=f"{feed_url} returned {status}",
                http_status=status,
                robots=fetched.robots,
                validators=known if not known.is_empty else None,
            )

        body = response.content
        if len(body) > self._max_feed_bytes:
            return FeedFetch(
                feed_url=feed_url,
                outcome="error",
                detail=(
                    f"{feed_url} returned {len(body)} bytes, past the "
                    f"{self._max_feed_bytes}-byte feed limit"
                ),
                http_status=status,
                robots=fetched.robots,
            )

        artifact = self._store_payload(feed_url, response)
        # The response's own content-type goes through: it is what makes
        # "this feed is malformed" distinguishable from "we did not tell
        # feedparser what this is". See `_HEADER_ONLY_BOZO` in parse.py.
        parsed = parse_feed(
            body, feed_url=feed_url, content_type=response.headers.get("content-type")
        )

        if parsed.malformed:
            # Recorded, not raised. A feed with one bad character still yields
            # its entries, and refusing the lot would lose them; a feed that
            # yields nothing is visible as zero entries with a reason attached.
            log.warning(
                "blog feed %s is malformed (%s) — %d entr(ies) parsed anyway",
                feed_url,
                parsed.malformed_detail,
                len(parsed.entries),
            )
        if parsed.unidentifiable:
            log.warning(
                "blog feed %s: %d entr(ies) had neither a guid nor a link and cannot "
                "become documents",
                feed_url,
                parsed.unidentifiable,
            )

        refreshed = known.merge(FeedValidators.from_response_headers(response.headers))
        self._validators.save(feed_url, refreshed)

        return FeedFetch(
            feed_url=feed_url,
            outcome="fetched",
            detail=f"{feed_url} returned {status}, {len(parsed.entries)} entr(ies)",
            http_status=status,
            artifact=artifact,
            parsed=parsed,
            validators=refreshed,
            robots=fetched.robots,
        )

    # ── articles ─────────────────────────────────────────────────────────

    def fetch_article(self, entry: FeedEntry) -> ArticleFetch:
        """Fetch one entry's article and store the bytes `text_ref` will name."""
        url = entry.fetchable_url
        if not url:
            return ArticleFetch(
                entry=entry,
                url=None,
                outcome="error",
                detail=f"entry {entry.entry_id!r} carries no link to fetch",
            )

        fetched = self._get(url, headers={"Accept": ARTICLE_ACCEPT})
        if fetched.outcome != "fetched" or fetched.response is None:
            return ArticleFetch(
                entry=entry,
                url=url,
                outcome=fetched.outcome,
                detail=fetched.detail,
                http_status=fetched.http_status,
                robots=fetched.robots,
            )

        response = fetched.response
        status = response.status_code

        if status >= 400:
            return ArticleFetch(
                entry=entry,
                url=url,
                outcome="error",
                detail=f"{url} returned {status}",
                http_status=status,
                robots=fetched.robots,
            )

        media_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if media_type and media_type not in ARTICLE_MEDIA_TYPES:
            return ArticleFetch(
                entry=entry,
                url=url,
                outcome="error",
                detail=(
                    f"{url} returned content-type {media_type!r}, which is not an article. "
                    f"Expected one of {sorted(ARTICLE_MEDIA_TYPES)}."
                ),
                http_status=status,
                robots=fetched.robots,
            )

        body = response.content
        if len(body) > self._max_article_bytes:
            return ArticleFetch(
                entry=entry,
                url=url,
                outcome="error",
                detail=(
                    f"{url} returned {len(body)} bytes, past the "
                    f"{self._max_article_bytes}-byte article limit"
                ),
                http_status=status,
                robots=fetched.robots,
            )

        return ArticleFetch(
            entry=entry,
            url=url,
            outcome="fetched",
            detail=f"{url} returned {status}, {len(body)} bytes stored",
            http_status=status,
            artifact=self._store_payload(url, response),
            robots=fetched.robots,
        )

    # ── one feed, end to end ─────────────────────────────────────────────

    def harvest_feed(self, feed_url: str, *, fetch_articles: bool = True) -> FeedRun:
        """Fetch a feed and its entries' articles. One `harvest_run` worth of work."""
        started_at = self._clock()
        feed = self.fetch_feed(feed_url)

        articles: list[ArticleFetch] = []
        if fetch_articles and feed.outcome == "fetched":
            articles = [self.fetch_article(entry) for entry in feed.entries]

        return FeedRun(
            feed_url=feed_url,
            started_at=started_at,
            finished_at=self._clock(),
            # The run's outcome is the feed's: a feed that 304s did no article
            # work, and a feed that was fetched is a run that happened even if
            # every article 404d — those failures are `http_errors`, which is a
            # different statement from "this run did not read the feed".
            outcome=feed.outcome,
            feed=feed,
            articles=articles,
            pipeline_version=self._pipeline_version,
        )


def fetcher_for_source(source, **kwargs) -> BlogFetcher:
    """Build a fetcher for a `contract/sources.yaml` source, ToS gate included.

    The entry point a driver uses. `assert_terms_reviewed` fires here rather
    than in the constructor so that the mechanics can be tested against
    recorded fixtures without a test having to fabricate a reviewed source row —
    a fixture that fakes a ruling is worse than no gate, because it reads as one.

    With `contract/sources.yaml` as it stands this refuses for `blogs`, and
    should: NFR-5 wants the terms read and recorded per source, and that ruling
    is outstanding.
    """
    from collect.registry.assertions import assert_terms_reviewed

    assert_terms_reviewed([source])
    return BlogFetcher(**kwargs)
