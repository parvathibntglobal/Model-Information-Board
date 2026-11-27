"""Instagram: a named account's newest posts, for the Industry AI observer.

ADDED 2026-11-25 (anooj: "for instagram we have a rapid api key, same as reddit
and X, so it should also go in with them"). The observer only - no keyword
search, no evidence for the board.

THE ROUTE. A RapidAPI scraper provider selected by `INSTAGRAM_PROVIDER`
(`instagram-looter2` today), NOT Meta's own Graph API - the reseller shape of the
Reddit and X arms, and the same open question they carry (ruling
`instagram-via-rapidapi-scraper`, contract/sources.yaml). Two endpoints:

    GET /id?username=<u>               -> {"user_id": ...}; a name that does not
                                          exist answers 200 with `errorMessage`
                                          and NO user_id (checked 2026-11-25)
    GET /user-feeds2?id=<id>&count=12  -> data.user.edge_owner_to_timeline_media
                                          .edges[].node, newest first

The watch list stores each account's numeric id beside its handle, so a run
spends ONE request per account (the feed), never the lookup. A handle is a name
that can change hands; the id is the account (Bluesky's DID reasoning).

PROVIDER RELIABILITY, MEASURED. Through this provider's hashtag endpoint the
2026-11-04..17 trial got captions on 4-5 Nov only; 6 Nov answered HTTP 500 and
every run 9-17 Nov came back with posts but NO captions (memory of the trial,
`_instagram_trial/summary.csv`). On 2026-11-25 the account feed answered with
12 of 12 posts captioned. So a page whose posts carry no caption is recorded
as `uncaptioned`, never read as "this account posted nothing about AI".

WHAT IS STORED. The feed page as returned, in the raw store, BEFORE any sieve
(the lane passes its LOCAL store: scripts/run_industry_ai.py `raw_store`).

QUOTA. 15,000 requests a month on this plan (x-ratelimit-requests-limit, read
2026-11-25). Every response's quota header is recorded under the `instagram`
meter (`collect/usage.py`), as the Reddit and X arms do.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from collect.adapters.basis import observe_use_basis
from collect.config import settings
from collect.http import ANSWERED_STATUSES
from collect.limiter import HostLimiter
from collect.rawstore import RAW, RawStore
from collect.usage import record_rapidapi_quota

log = logging.getLogger(__name__)

SOURCE_ID = "instagram"
ID_PATH = "/id"
FEED_PATH = "/user-feeds2"
#: Posts asked per feed page: the newest twelve.
PER_PAGE = 12
MIN_INTERVAL_SECONDS = 1.0

#: One retry, after this wait, for a failure that may pass (#652's X rule): a 429
#: that is not quota exhaustion, a 5xx, a timeout. Never 400/401/403/404: waiting
#: does not fix a wrong key, a refused route or a wrong id.
TRANSIENT_RETRIES = 1
TRANSIENT_RETRY_WAIT_SECONDS = 5.0
_TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})


class InstagramConfigError(RuntimeError):
    """No provider or no key: nothing can be asked, and nothing is guessed."""


def host_for(provider: str | None = None) -> str:
    """`instagram-looter2` -> `instagram-looter2.p.rapidapi.com`. NOT DEFAULTED: an
    unconfigured process must not call one particular vendor (rule 6)."""
    p = (provider if provider is not None else settings().instagram_provider) or ""
    p = p.strip()
    if not p:
        raise InstagramConfigError(
            "INSTAGRAM_PROVIDER is not set, so no RapidAPI host can be derived and "
            "Instagram is not read. Set it to the provider name (instagram-looter2)."
        )
    if "." in p or "/" in p:
        raise InstagramConfigError(
            f"INSTAGRAM_PROVIDER={p!r} looks like a host or a URL. It is the provider "
            "NAME (instagram-looter2); the host is derived from it."
        )
    return f"{p}.p.rapidapi.com"


def key_for() -> tuple[str | None, str]:
    """(key, the variable it came from). INSTAGRAM_RAPIDAPI_KEY first, then
    RAPIDAPI_KEY - one RapidAPI account may subscribe to several providers, and
    a key cannot be checked by looking at it, so the source is named instead."""
    config = settings()
    if config.instagram_rapidapi_key:
        return config.instagram_rapidapi_key, "INSTAGRAM_RAPIDAPI_KEY"
    return config.rapidapi_key, "RAPIDAPI_KEY"


@dataclass
class InstagramRun:
    """One account's feed read: what it cost and what came back."""

    query: str
    started_at: datetime
    finished_at: datetime | None = None
    calls: int = 0
    http_errors: int = 0
    failures: list = field(default_factory=list)
    #: Attempts made again after a failure that may pass. DECLARED UNREAD (rule 9):
    #: nothing reads it yet; its intended reader is the run log's per-platform watch
    #: line, once a run shows retries worth reporting. `recovered` below is read.
    retries: int = 0
    #: Failed attempts a retry recovered from; `failure_of` subtracts them.
    recovered: int = 0
    #: Failed requests the provider ANSWERED about what was asked
    #: (`collect.http.ANSWERED_STATUSES`): the account or query is wrong or gone,
    #: the provider is up. Read by collect/industry_ai/harvest.py
    #: `provider_failed` (#688 review), so a run of gone accounts does not stop
    #: the watch list.
    answered_errors: int = 0
    #: Pages that answered 200 with no feed in them (rule 4: not "no posts").
    empty_response: int = 0
    #: Posts that came back with no caption: the provider's 9-17 Nov fault.
    uncaptioned: int = 0
    quota_exhausted: bool = False
    quota_remaining: int | None = None
    quota_limit: int | None = None
    quota_reset_seconds: int | None = None
    posts: list[dict[str, Any]] = field(default_factory=list)
    discovery_ref: str | None = None


def _int_header(response: httpx.Response, name: str) -> int | None:
    value = response.headers.get(name)
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def nodes_of(payload: Any) -> list[dict[str, Any]] | None:
    """The post nodes of a /user-feeds2 page; None when the page carries no feed
    at all (an error body, a changed shape) - never an empty list for that."""
    try:
        edges = payload["data"]["user"]["edge_owner_to_timeline_media"]["edges"]
    except (KeyError, TypeError):
        return None
    if not isinstance(edges, list):
        return None
    return [e["node"] for e in edges if isinstance(e, dict) and isinstance(e.get("node"), dict)]


def caption_of(node: dict[str, Any]) -> str:
    edges = (node.get("edge_media_to_caption") or {}).get("edges") or []
    if edges and isinstance(edges[0], dict):
        return str((edges[0].get("node") or {}).get("text") or "")
    return ""


class InstagramHarvester:
    """Read one account's newest posts by its numeric id; store the page first."""

    def __init__(self, *, client: httpx.Client, store: RawStore,
                 limiter: HostLimiter | None = None,
                 clock=lambda: datetime.now(UTC), sleeper=time.sleep) -> None:
        self._client = client
        self._store = store
        self._limiter = (HostLimiter(min_interval=MIN_INTERVAL_SECONDS)
                         if limiter is None else limiter)
        self._clock = clock
        self._sleep = sleeper
        self._host = host_for()
        key, self._key_source = key_for()
        if not key:
            raise InstagramConfigError(
                "no RapidAPI key (INSTAGRAM_RAPIDAPI_KEY or RAPIDAPI_KEY), so Instagram is not read"
            )
        self._headers = {"x-rapidapi-key": key, "x-rapidapi-host": self._host}

    def _get(self, path: str, params: dict[str, Any], run: InstagramRun):
        """One GET, retried once on a failure that may pass. Every failed attempt is
        recorded; a recovered one is counted in `recovered`. None on failure."""
        url = f"https://{self._host}{path}"
        for attempt in range(TRANSIENT_RETRIES + 1):
            self._limiter.wait(url)
            run.calls += 1
            try:
                response = self._client.get(url, params=params, headers=self._headers)
            except httpx.TimeoutException as error:
                cause, transient, response = type(error).__name__, True, None
            except httpx.HTTPError as error:
                cause, transient, response = type(error).__name__, False, None
            else:
                self._read_quota(response, run)
                if response.status_code == 200:
                    if attempt:
                        run.recovered += attempt
                    return response
                cause = f"HTTP {response.status_code}"
                transient = response.status_code in _TRANSIENT_STATUSES
                if response.status_code == 429 and run.quota_exhausted:
                    transient = False  # waiting does not refill a spent quota
            run.http_errors += 1
            run.failures.append(cause)
            if response is not None and response.status_code in ANSWERED_STATUSES:
                run.answered_errors += 1
            if not transient or attempt == TRANSIENT_RETRIES:
                log.error("instagram: %s on %s - NOT an empty result", cause, path)
                return None
            run.retries += 1
            self._sleep(TRANSIENT_RETRY_WAIT_SECONDS)
        return None

    def _read_quota(self, response: httpx.Response, run: InstagramRun) -> None:
        run.quota_remaining = _int_header(response, "x-ratelimit-requests-remaining")
        run.quota_limit = _int_header(response, "x-ratelimit-requests-limit")
        run.quota_reset_seconds = _int_header(response, "x-ratelimit-requests-reset")
        if run.quota_remaining == 0:
            run.quota_exhausted = True
        record_rapidapi_quota(
            remaining=run.quota_remaining, limit=run.quota_limit, read_on=SOURCE_ID,
            api_key=key_for()[0], reset_seconds=run.quota_reset_seconds,
        )

    def user_feed(self, user_id: str, *, query: str | None = None) -> InstagramRun:
        """The account's newest PER_PAGE posts. The page is stored before anything
        reads it; a page with no feed in it counts as `empty_response`."""
        run = InstagramRun(query=query or user_id, started_at=self._clock())
        response = self._get(FEED_PATH, {"id": user_id, "count": PER_PAGE}, run)
        if response is not None:
            run.discovery_ref = self._store.put(response.content, namespace=RAW).ref
            try:
                nodes = nodes_of(response.json())
            except ValueError:
                nodes = None
            if nodes is None:
                run.empty_response += 1
            else:
                run.posts = nodes
                run.uncaptioned = sum(not caption_of(n).strip() for n in nodes)
        run.finished_at = self._clock()
        return run

    def user_id(self, username: str) -> str | None:
        """The account's numeric id, or None when the name resolves to no account.
        Used to build the watch list; a run reads ids from the contract."""
        run = InstagramRun(query=f"id:{username}", started_at=self._clock())
        response = self._get(ID_PATH, {"username": username}, run)
        if response is None:
            raise RuntimeError(f"instagram: the id lookup for {username!r} failed "
                               f"({', '.join(run.failures)}) - unknown, not 'no account'")
        uid = (response.json() or {}).get("user_id")
        return str(uid) if uid else None


# ── the gated entry point ────────────────────────────────────────────────


def observe_instagram_use() -> dict[str, object]:
    """This run's live observations for the terms gate (the X arm's four facts)."""
    key, source = key_for()
    return {
        "access_path": "rapidapi-reseller",
        "instagram_provider": settings().instagram_provider,
        "credential_present": bool(key),
        "credential_source": source,
        **observe_use_basis(),
    }


def harvester_for_source(source, *, rulings=None, **kwargs) -> InstagramHarvester:
    """Build a harvester for the `instagram` source row: terms gate first, then
    the provider and key (the X arm's order, for its reason)."""
    from collect.registry.assertions import assert_terms_reviewed, source_field

    source_id = source_field(source, "id", "?")
    assert_terms_reviewed([source], rulings=rulings,
                          observations={source_id: observe_instagram_use()})
    return InstagramHarvester(**kwargs)
