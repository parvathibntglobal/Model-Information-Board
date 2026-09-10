"""The X adapter, via a RapidAPI scraper provider. Built to the credential.

WHAT IS FINISHED AND WHAT IS NOT
--------------------------------
Everything except the credential: the route, the host derivation, request
shaping, the document unit, thread linkage, parsing, the raw-store writes, the
`harvest_run` fields, the document drafts and the terms gate. **Nothing here
has ever made a request**, because `XHarvester` refuses to exist without a
RapidAPI key and none is configured.

    XCredentialMissing     no `RAPIDAPI_KEY`. The stop this module is built to.
    XConfigError           no `SCRAPER_PROVIDER`, so no host can be derived.
    TermsNotReviewedError  the ruling's preconditions are not satisfied.

Three refusals rather than one, and they are not redundant: a key without a
ruling must still refuse, or the first person to paste one harvests a platform
nobody has read the terms for. That is the exact sequence that produced a
1,297-post Reddit corpus with the gate never asked
(`reddit.harvester_for_source`).

⚠  THE THIRD REFUSAL CHANGED MEANING ON 2026-09-08 AND IS STILL LIVE.
   `x-via-rapidapi-scraper` now exists in `contract/sources.yaml`, so the gate
   no longer refuses for want of a ruling - it refuses when one of that
   ruling's live preconditions fails, and `credential_present: [true]` is one
   of them. So a keyless run refuses TWICE, at the gate and at the
   constructor, and the gate goes first on purpose: the answer to "why can't I
   harvest X" should never be "you need a key" when a term has not been read.

   A SWAPPED PROVIDER ALSO REFUSES THERE. `scraper_provider: [twitter241]` is
   pinned in the ruling, because a different provider is a different party's
   terms AND a different response envelope.

THE ROUTE IS A RAPIDAPI SCRAPER PROVIDER, NOT X'S OWN API
----------------------------------------------------------
`twitter241` on RapidAPI, which is the provider this project's own X sweep
already used - `articles/deepseek-v4-pro/REPORT.md` records it, driven through
the brand-visibility agent's provider with the same credentials.

So this is the SAME SHAPE AS REDDIT and it inherits Reddit's unresolved terms
condition rather than avoiding it. `contract/sources.yaml` records, for
`reddit-via-rapidapi`:

    Data API Terms 2.8 requires credentials issued by Reddit and prohibits
    masking the OAuth identity. A reseller route does not satisfy this
    regardless of use.

X's Developer Agreement has a clause of the same shape, and a reseller route
will not satisfy it either. **That is not a reason to build the other route** -
it is a condition to record and escalate, exactly as Reddit's is, and
`x-via-rapidapi-scraper` records it as unresolved rather than cleared.

RATIFIED 2026-09-08 ON AN INTERNAL-DEVELOPMENT-ONLY BASIS, WHICH IS A
PERMISSION AND NOT A CLEARANCE. The condition it rests on is that nothing is
published externally - a quote shown with a link to somebody outside the team -
and `contract/sources.yaml` defines that trigger, lists the four conditions
this ruling does not clear, and states plainly that NOTHING IN THE PIPELINE
WOULD NOTICE IF THE CONDITION WERE BREACHED. Read that block before treating
the passing gate as an all-clear: what the gate checks is `ENVIRONMENT`, and
publication is a property of who is looking at a page.

THE HOST IS DERIVED FROM `SCRAPER_PROVIDER` AND IS NOT HARDCODED
-----------------------------------------------------------------
    SCRAPER_PROVIDER=twitter241   ->   twitter241.p.rapidapi.com

`host_for()` is the whole of it. Moving to a different RapidAPI provider is
then an environment change rather than a code change, which is the point: the
provider is an operational choice and this module should follow it.

⚠  IT FOLLOWS THE VARIABLE, AND THE PARSER DOES NOT AUTOMATICALLY FOLLOW WITH
   IT. A different provider fronts a different response envelope, so a provider
   swap is a config change PLUS a re-check of `_tweet_results`. `observe_x_use`
   reports the provider on every run so the terms gate can pin the one that was
   reviewed - a swap then refuses at the gate instead of silently parsing
   nothing and reporting zero posts. That refusal is the feature.

⚠  RAPIDAPI_KEY IS SHARED WITH THE REDDIT PATH, and that is a fact worth
   knowing before a sweep: both platforms bill the same subscription, so an X
   sweep spends Reddit's monthly quota. `contract/sources.yaml` records the
   reading - 1,000,000 requests over a 23.893-day window - and records that the
   BILLED TIER IS STILL UNVERIFIED, because a gateway header is the gateway's
   view rather than proof of what RapidAPI bills. Nothing here makes that worse
   or better; it makes it shared.

THE DOCUMENT UNIT IS THE POST
-----------------------------
`x:2047527303824236545`. A reply is a post too, and its thread is carried by
`conversation_id_str`, so `thread_root_id` resolves without a second request;
a reply's parent comes from `in_reply_to_status_id_str`.

⚠  THE THREAD ROOT IS OFTEN A POST WE DO NOT HAVE. A conversation id names a
   post that may be outside the search window or from a protected account.
   `document.thread_root_id` carries no foreign key, so the row is written
   anyway and the dangling root is a **coverage fact** rather than a lost
   document - the same property `hackernews.drafts` records. What must not
   happen is the root being invented or the linkage dropped: one would fabricate
   a thread and the other would lose that this post is a reply.

TWO ARTIFACTS, AND THE PER-POST ONE IS RE-SERIALISED
-----------------------------------------------------
    search response      -> raw/   the discovery artifact, one per query page
    one tweet result      -> raw/   the per-document artifact; `document.text_ref`

`arxiv.py` spends a second request per document precisely to avoid
re-serialising, and this does the opposite, so the difference is stated: this
route is metered against a shared subscription whose real allowance nobody has
verified, and a scraper provider offers no per-post endpoint on the same terms
anyway. `github.fetch_comments` already established that a deterministic
re-serialisation of the platform's own record is acceptable for a per-document
artifact, and the invariant still holds:
`content_hash(resolve(text_ref)) == content_hash`.

WHAT THIS PROJECT ALREADY MEASURED ABOUT THE RESPONSE, AND IT IS A WARNING
---------------------------------------------------------------------------
From `articles/deepseek-v4-pro/REPORT.md`, found while running that sweep:

    X's GraphQL user object moved: `legacy` now comes back empty on search
    results, and followers, bio and verification live under
    `relationship_counts`, `profile_bio` and `verification`. `twitter241.py`
    still reads `user_legacy.followers_count`, so it records EVERY AUTHOR AS
    0 FOLLOWERS with an empty bio.

A silent zero from a moved field, in the exact shape rule 6 is about. So
`_author_of` reads the new paths first, falls back to `legacy`, and **counts
the fallbacks** on the run - `run.author_legacy_fallbacks`. A schema move then
shows up as a number rather than as a corpus of zeros.

Three more things that sweep measured and this adapter honours:

    SEARCH RELEVANCE IS LOOSE   993 posts returned, 573 survived a literal
                                match. `candidates` is a retrieval count and
                                never a mention count (rule 7).
    ~20 POSTS PER PAGE          2 pages returned 32-40. Not a documented
                                figure; the observed one.
    VIEWS ARE ABSENT ON SOME    "X does not always expose them", so an absent
                                view count stays None and never 0.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from collect.adapters.basis import observe_use_basis
from collect.adapters.documents import DocumentDraft, SweepCounts, WriteReport
from collect.config import settings
from collect.ids import stable_id
from collect.limiter import HostLimiter
from collect.rawstore import RAW, RawStore
from collect.usage import record_rapidapi_quota

log = logging.getLogger(__name__)

SOURCE_ID = "x"
DOCUMENT_SOURCE = "x"

#: The provider this project has actually used, and the default `SCRAPER_PROVIDER`
#: value in `.env.example`. A DEFAULT FOR THE DOCS, NOT A HARDCODED HOST - see
#: `host_for`, which derives the host from whatever the variable says.
DEFAULT_PROVIDER = "twitter241"

#: ⚠ UNVERIFIED, BECAUSE NO KEY EXISTS TO VERIFY IT WITH. The path is this
#: provider's search endpoint as documented on RapidAPI; nothing in this
#: repository has called it. The first real run must confirm it, and `_get`
#: counts a 404 as an http error precisely so a wrong path cannot read as a
#: query with no matches.
#:
#: The PARAMETERS are not guesses: `articles/deepseek-v4-pro/REPORT.md`'s query
#: log records 46 real queries against this provider with `type` of `Top` or
#: `Latest`, 2-3 pages each, returning 23-40 posts per query.
SEARCH_PATH = "/search-v2"

#: `type=` values the recorded sweep used. `Latest` is reverse-chronological and
#: `Top` is the provider's relevance order; the sweep ran both for its four
#: primary keywords and `Top` alone for its 32 derived ones.
SEARCH_TYPES = ("Top", "Latest")

#: Observed, not documented: 2 pages returned 32-40 posts. Requested per page.
COUNT_PER_PAGE = 20
DEFAULT_MAX_PAGES = 1

#: ⚠ NOT A MEASURED LIMIT FOR THIS PROVIDER. Reddit's RapidAPI route 429s at
#: the 32nd rapid call (measured 2026-08-14, working figure 25/min); this is the
#: same gateway and a different backend, so that figure is a neighbour's
#: measurement rather than this one's. Paced below it until a real run reads the
#: headers `_get` already captures.
MIN_INTERVAL_SECONDS = 2.4

#: The quota headers the RapidAPI gateway returns. Same three the Reddit adapter
#: captures, and captured here for the same reason: a docstring constant of
#: 1,000,000 stood unchecked against a plan believed to be 500,000 for a
#: fortnight. Every value is a dated observation from a response; absent stays
#: None.
_QUOTA_HEADERS = {
    "x-ratelimit-requests-limit": "quota_limit",
    "x-ratelimit-requests-remaining": "quota_remaining",
    "x-ratelimit-requests-reset": "quota_reset_seconds",
}


class XCredentialMissing(RuntimeError):
    """No `RAPIDAPI_KEY`, so no request may be made. THE DELIBERATE STOP."""


class XConfigError(RuntimeError):
    """The adapter cannot be built from the current settings."""


def host_for(provider: str | None = None) -> str:
    """`twitter241` -> `twitter241.p.rapidapi.com`. The only place a host is made.

    RapidAPI routes on the `X-RapidAPI-Host` header, so this is the value that
    decides which service answers - and it is derived from `SCRAPER_PROVIDER`
    rather than written down, so moving provider is an environment change.

    Raises rather than defaulting when the variable is unset. A default host
    would mean an unconfigured process quietly calls one particular vendor,
    which is the kind of definite value rule 6 forbids for a missing one.
    """
    name = provider if provider is not None else settings().scraper_provider
    if not name or not str(name).strip():
        raise XConfigError(
            "SCRAPER_PROVIDER is not set, so no RapidAPI host can be derived and "
            "no X request can be made. Set it in .env (see .env.example); the "
            f"provider this project has used is {DEFAULT_PROVIDER!r}, which "
            f"resolves to {DEFAULT_PROVIDER}.p.rapidapi.com. It is not defaulted "
            "here on purpose - an unconfigured process must not quietly call one "
            "particular vendor."
        )
    cleaned = str(name).strip()
    if "." in cleaned or "/" in cleaned:
        # A full host or URL pasted into the provider slot. Refused rather than
        # tolerated: `RAPIDAPI_HOST` in this project already had one bad paste
        # (a full endpoint URL where a bare host belonged), and a host header
        # carrying a URL matches no route.
        raise XConfigError(
            f"SCRAPER_PROVIDER={cleaned!r} looks like a host or a URL. It is the "
            "RapidAPI PROVIDER NAME - the subdomain - so `twitter241`, not "
            "`twitter241.p.rapidapi.com`."
        )
    return f"{cleaned}.p.rapidapi.com"


def key_for() -> tuple[str | None, str]:
    """X's RapidAPI key, and THE NAME OF THE VARIABLE IT CAME FROM.

    `X_RAPIDAPI_KEY` first, `RAPIDAPI_KEY` second. Returns `(key, source)` where
    `source` is the variable name, or `"unset"` when neither is set.

    WHY IT RETURNS THE SOURCE AND `host_for` DOES NOT
    -------------------------------------------------
    `host_for` can refuse a wrong value: `twitter241.p.rapidapi.com` visibly is
    not Reddit's host, so `reddit.py:host_for` raises on it and names the
    collision. **A key affords no such check.** It is 50 opaque characters, and
    the wrong one comes back as a gateway 403 - which `.env.example` already
    records as "a credential problem that looks like the platform refusing us".

    So this cannot validate, and it does not pretend to. It reports which
    variable supplied the key, so a 403 can say *"X_RAPIDAPI_KEY was used"* and
    the reader can check that one rather than guessing between two. Same move as
    `record_rapidapi_quota`'s `read_on`: when a value cannot be verified, name
    where it came from.

    THE FALLBACK IS DELIBERATE AND IS NOT THE OLD ASSUMPTION. One RapidAPI
    account subscribed to both providers has one key that works for both, and
    that setup must keep working. What was wrong before was not the sharing - it
    was asserting the sharing as a fact. Measured 2026-09-10 on this project's
    own `.env`: the two keys are different subscriptions, each 403 on the
    other's provider. `docs/measurements/quota-headers.jsonl`.
    """
    config = settings()
    if config.x_rapidapi_key:
        return config.x_rapidapi_key, "X_RAPIDAPI_KEY"
    if config.rapidapi_key:
        return config.rapidapi_key, "RAPIDAPI_KEY"
    return None, "unset"


@dataclass(frozen=True)
class XPost:
    """One post from a search page."""

    post_id: str
    text: str
    author_external_id: str | None
    author_handle: str | None
    created_at: str | None
    lang: str | None
    conversation_id: str | None
    replied_to_id: str | None
    metrics: dict[str, Any] | None
    #: True where the author's fields came from `legacy` rather than the current
    #: paths. See the module docstring: reading `legacy` on a search result is
    #: how every author became 0 followers.
    author_from_legacy: bool
    #: The tweet result object, re-serialised deterministically.
    payload: str

    @property
    def external_id(self) -> str:
        return self.post_id

    @property
    def url(self) -> str:
        """A permalink built from the id and the handle.

        ⚠  IT NEEDS THE HANDLE, and the handle is mutable. X redirects
        `/i/status/<id>` correctly regardless of author, so that form is used
        when the response did not supply a username - a URL that rots is worse
        than a URL that is less pretty.
        """
        if self.author_handle:
            return f"https://x.com/{self.author_handle}/status/{self.post_id}"
        return f"https://x.com/i/status/{self.post_id}"

    @property
    def sieve_text(self) -> str:
        return self.text

    @property
    def engagement(self) -> dict[str, Any]:
        """Absent metrics stay absent.

        The recorded sweep measured that views are missing on some posts - "X
        does not always expose them" - so a 0 here would say nobody saw it,
        and E3 ranks on `specificity x log(1 + engagement)`.
        """
        metrics = self.metrics or {}
        return {
            "score": metrics.get("favorite_count"),
            "comments": metrics.get("reply_count"),
            "reposts": metrics.get("retweet_count"),
            "quotes": metrics.get("quote_count"),
            "bookmarks": metrics.get("bookmark_count"),
            "views": metrics.get("view_count"),
        }


@dataclass
class XRun:
    """One query, what it cost, and what it produced."""

    query: str
    search_type: str
    started_at: datetime
    finished_at: datetime | None = None

    pages_fetched: int = 0
    pages_stored: int = 0
    search_calls: int = 0
    http_errors: int = 0

    discovery_refs: list[str] = field(default_factory=list)
    posts: list[XPost] = field(default_factory=list)
    verdicts: list[Any] = field(default_factory=list)
    survivors: list[XPost] = field(default_factory=list)
    stored: list[tuple[XPost, str, str]] = field(default_factory=list)

    #: Posts whose author fields came from `legacy`. A SCHEMA MOVE DETECTOR, and
    #: the reason it exists is in the module docstring: the previous provider
    #: code read a field that had moved and recorded every author as 0
    #: followers, silently, for the whole sweep.
    author_legacy_fallbacks: int = 0
    #: Tweet results the walker found and could not read an id from. Counted so
    #: "few posts" cannot be confused with "the envelope changed".
    unparseable_entries: int = 0

    #: The provider reports no grand total. None stays None rather than 0.
    result_count: int | None = None
    next_cursor: str | None = None

    #: RapidAPI gateway quota, read from the response headers. None means the
    #: response did not carry it - never a default.
    quota_limit: int | None = None
    quota_remaining: int | None = None
    quota_reset_seconds: int | None = None
    quota_exhausted: bool = False

    exhausted: bool = False
    truncated_by: str | None = None

    @property
    def items_fetched(self) -> int:
        return len(self.posts)

    @property
    def items_kept(self) -> int:
        return len(self.stored)

    def harvest_run_fields(self) -> dict[str, Any]:
        return {
            "id": stable_id("hr", SOURCE_ID, self.query, self.started_at.isoformat()),
            "source_id": SOURCE_ID,
            # THE WHOLE DENOMINATOR IN THE STRING: the query, the sort that
            # produced it, and the page size. `Top` and `Latest` return
            # different populations for one query, so a row that said only the
            # query could not say which it drew from.
            "query_key": (
                f"{self.query} type:{self.search_type} count:{COUNT_PER_PAGE}"
            ),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "items_fetched": self.items_fetched,
            "items_kept": self.items_kept,
            "http_errors": self.http_errors,
            "exhausted": True if self.exhausted else None,
            "truncated_by": self.truncated_by,
            "pipeline_version": settings().pipeline_version,
            # ── homeless, pending #5 ──
            "pages_fetched": self.pages_fetched,
            "pages_stored": self.pages_stored,
            # `harvest_run_truncated_ck` has no 'quota' value, and quota means
            # "stop until the reset" while rate-limit means "retry shortly".
            # Same treatment as the Reddit adapter.
            "quota_exhausted": self.quota_exhausted,
        }


class XHarvester:
    """Search posts, store the page, sieve, store each post.

    ⚠  CANNOT BE CONSTRUCTED WITHOUT A RAPIDAPI KEY. That is the stop, and it is
       in `__init__` rather than in `_get` deliberately: a harvester that exists
       and fails per request looks configured, and something will eventually
       call it in a loop and record 40 http errors as a platform outage.

       This is the opposite placement from the TERMS gate, which is in
       `harvester_for_source` so tests can build the object without fabricating
       a reviewed source row. The two differ because a missing credential is a
       fact about the process that no test needs to fake, while a ruling is a
       document whose fixture would read as a real review.
    """

    def __init__(
        self,
        *,
        client: httpx.Client,
        store: RawStore,
        api_key: str | None = None,
        provider: str | None = None,
        limiter: HostLimiter | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
        count: int = COUNT_PER_PAGE,
        clock=lambda: datetime.now(UTC),
        sleeper=time.sleep,
    ) -> None:
        if api_key is not None:
            key, key_source = api_key, "argument"
        else:
            key, key_source = key_for()
        if not key:
            raise XCredentialMissing(
                "Neither X_RAPIDAPI_KEY nor RAPIDAPI_KEY is set, so no X request "
                "can be made. The X route is a RapidAPI scraper provider "
                f"(SCRAPER_PROVIDER, default {DEFAULT_PROVIDER!r}) and NOT X's "
                "own API, so the credential is a RapidAPI key.\n"
                "SET X_RAPIDAPI_KEY. It used to say the credential was 'the same "
                "one the Reddit path uses, billing the same subscription' - that "
                "was an assumption, and it is false here: measured 2026-09-10, "
                "this project's Reddit key returns 403 on twitter241 and its X "
                "key returns 403 on reddit34. Two accounts, two meters. "
                "RAPIDAPI_KEY is still accepted as a fallback, because one "
                "account subscribed to both providers is a real setup - but it "
                "is a fallback and not the same thing.\n"
                "A KEY IS NOT A CLEARANCE. contract/sources.yaml's ruling "
                "x-via-rapidapi-scraper permits internal development and "
                "testing ONLY, and only while nothing is published externally; "
                "it does NOT clear the reseller-credential, author-display or "
                "deletion conditions it records as unresolved. Read it before "
                "the first sweep, not after."
            )
        self._key = key
        #: WHICH VARIABLE SUPPLIED THE KEY. Carried so a 403 names it - the one
        #: thing that separates "wrong key" from "provider refusing us", which
        #: the gateway's response cannot.
        self._key_source = key_source
        # Raises XConfigError when SCRAPER_PROVIDER is unset, which is a
        # different failure from a missing key and says so.
        self._host = host_for(provider)
        self._base = f"https://{self._host}"
        self._client = client
        self._store = store
        self._limiter = (
            HostLimiter(min_interval=MIN_INTERVAL_SECONDS) if limiter is None else limiter
        )
        self._max_pages = max_pages
        self._count = count
        self._clock = clock
        self._sleep = sleeper

    @property
    def host(self) -> str:
        """The RapidAPI host this harvester will call. Derived, never stored."""
        return self._host

    @property
    def auth_headers(self) -> dict[str, str]:
        """The two headers RapidAPI routes and authenticates on.

        A property rather than client-level defaults, so the key is applied by
        THIS adapter and a client shared with another platform never carries
        it. The Reddit adapter builds its own client for the same reason - and
        note the two use different capitalisation of the same header names,
        which HTTP treats as identical.
        """
        return {"X-RapidAPI-Key": self._key, "X-RapidAPI-Host": self._host}

    def search_params(
        self, query: str, *, search_type: str = "Top", cursor: str | None = None
    ) -> dict[str, Any]:
        """Exactly what a search request sends. Buildable with no network.

        Exposed as its own method so the request shape is testable and
        reviewable before a credential exists - which is the whole point of
        stopping at the credential rather than leaving a stub.
        """
        if search_type not in SEARCH_TYPES:
            raise ValueError(
                f"search_type must be one of {SEARCH_TYPES}, got {search_type!r}. "
                "Spelled out rather than passed through, so a typo is a local "
                "error and not a silently different query."
            )
        params: dict[str, Any] = {
            "query": query,
            "type": search_type,
            "count": self._count,
        }
        if cursor:
            params["cursor"] = cursor
        return params

    def _get(self, path: str, params: dict[str, Any], run: XRun):
        url = f"{self._base}{path}"
        self._limiter.wait(url)
        try:
            response = self._client.get(url, params=params, headers=self.auth_headers)
        except httpx.HTTPError as error:
            run.http_errors += 1
            log.error("x: request failed on %s: %s", path, error)
            return None

        # ALL THREE HEADERS, not the one we happen to act on.
        for header, attribute in _QUOTA_HEADERS.items():
            value = response.headers.get(header)
            if value is None:
                continue
            with suppress(ValueError):
                setattr(run, attribute, int(value))
        if run.quota_remaining is not None and run.quota_remaining <= 0:
            run.quota_exhausted = True

        # `read_on` NAMES THE METER. This said "same key as Reddit, so the
        # same file"; measured 2026-09-10, it is NOT the same key - the two arms
        # are separate RapidAPI subscriptions with separate limits (X 100,000,
        # Reddit 1,000,000), each returning 403 on the other's provider.
        #
        # ⚠ WHICH MAKES THE SHARED FILE WRONG RATHER THAN MERELY COARSE, AND
        #   THIS CHANGE DOES NOT FIX IT. `var/rapidapi-quota.json` holds ONE
        #   record, so this X reading overwrites the last Reddit one and vice
        #   versa, and the panel renders whichever landed last - under either
        #   heading. `read_on` lets a reader tell which; it cannot stop the
        #   overwrite. Keying the store by arm is a separate change, because it
        #   moves a file format and a rendered panel with it.
        #
        # Until this existed, an X-only run left the panel showing an older
        # Reddit number as though nothing had been spent.
        record_rapidapi_quota(
            remaining=run.quota_remaining,
            limit=run.quota_limit,
            read_on=SOURCE_ID,
        )

        if response.status_code == 429:
            run.truncated_by = "rate-limit"
            run.http_errors += 1
            log.warning(
                "x: 429 on %s; quota remaining=%s", path, run.quota_remaining
            )
            return None
        if response.status_code == 404:
            # NAMED, because this is the failure mode the unverified path has.
            # A 404 is a wrong endpoint, not a query with no matches, and
            # reading it as the second would report the platform as silent.
            run.http_errors += 1
            log.error(
                "x: HTTP 404 on %s at host %s. SEARCH_PATH is unverified in this "
                "repository - no request had ever been made when it was written. "
                "This is a wrong endpoint for provider %r, NOT an empty result "
                "set. Check the provider's RapidAPI docs and correct "
                "SEARCH_PATH.", path, self._host, settings().scraper_provider,
            )
            return None
        if response.status_code in (401, 403):
            # NAMED FOR THE SAME REASON AS THE 404 ABOVE, and it is the failure
            # this project actually had. A gateway 401/403 is a CREDENTIAL
            # problem wearing a refusal's clothes: it looks like the provider
            # declining us, and it is usually the wrong key reaching the right
            # host. Nothing in the response says which - `x-rapidapi-proxy-
            # response: true` marks it as the gateway's answer and not the
            # provider's, and that is all it marks.
            #
            # So the log names the VARIABLE. Measured 2026-09-10: this project's
            # two RapidAPI keys are different subscriptions, and each returns
            # 403 on the other's provider - the exact shape below.
            run.http_errors += 1
            log.error(
                "x: HTTP %s on %s at host %s, key from %s. A gateway 401/403 is "
                "a CREDENTIAL failure that reads as the provider refusing us. "
                "Check that %s holds a key subscribed to %r - RapidAPI keys are "
                "per-account and a key valid for another provider 403s here. "
                "proxy-response=%s",
                response.status_code, path, self._host, self._key_source,
                self._key_source, settings().scraper_provider,
                response.headers.get("x-rapidapi-proxy-response"),
            )
            return None
        if response.status_code != 200:
            run.http_errors += 1
            log.warning("x: HTTP %s on %s", response.status_code, path)
            return None
        return response

    def search(
        self, query: str, *, search_type: str = "Top", run: XRun | None = None
    ) -> XRun:
        """Issue the query, storing each page before anything is sieved."""
        run = (
            run
            if run is not None
            else XRun(query=query, search_type=search_type, started_at=self._clock())
        )
        cursor: str | None = None

        for page in range(1, self._max_pages + 1):
            response = self._get(
                SEARCH_PATH,
                self.search_params(query, search_type=search_type, cursor=cursor),
                run,
            )
            run.search_calls += 1
            run.pages_fetched = page
            if response is None:
                break

            # Stored BEFORE the sieve, so a rejected post's text survives and a
            # re-sieve is possible over what this run actually saw.
            stored = self._store.put(response.content, namespace=RAW)
            run.discovery_refs.append(stored.ref)
            run.pages_stored += 1

            try:
                payload = response.json()
            except ValueError:
                run.http_errors += 1
                log.error("x: search response for %r is not JSON", query)
                break

            found = 0
            for result in _tweet_results(payload):
                post = _post_of(result, run)
                if post is None:
                    run.unparseable_entries += 1
                    continue
                run.posts.append(post)
                found += 1
            run.result_count = (run.result_count or 0) + found

            cursor = _next_cursor(payload)
            run.next_cursor = cursor
            if not found or not cursor:
                run.exhausted = True
                break
        else:
            if run.next_cursor:
                run.truncated_by = run.truncated_by or "query-budget"

        run.finished_at = self._clock()
        return run

    def sieve_run(self, run: XRun, terms) -> XRun:
        """Apply the terms locally. NOT optional on this platform.

        The recorded sweep measured it: 993 posts returned, **573 survived a
        literal keyword match**. Retrieval here returns related posts as well
        as matches, so `candidates` is a retrieval count and the sieve is what
        counts mentions (rule 7).
        """
        from collect.adapters.queries.sieve import sieve

        for post in run.posts:
            verdict = sieve(terms, post.sieve_text)
            run.verdicts.append(verdict)
            if verdict.passed:
                run.survivors.append(post)
        return run

    def store_posts(self, run: XRun, posts) -> XRun:
        """Write each post's own payload. No request - the bytes are in hand."""
        for post in posts:
            put = self._store.put(post.payload, namespace=RAW)
            run.stored.append((post, put.ref, put.content_hash))
        return run

    def harvest(
        self,
        query: str,
        terms=None,
        *,
        search_type: str = "Top",
        run: XRun | None = None,
        max_store: int | None = None,
    ) -> XRun:
        run = self.search(query, search_type=search_type, run=run)
        if terms is not None:
            self.sieve_run(run, terms)
            survivors = run.survivors
        else:
            # NO SIEVE IS NOT AN EMPTY SIEVE. A caller with no rendered terms
            # keeps every candidate, and `verdicts` stays empty so
            # `sieve_pass_rate` is absent rather than 1.0 (rule 6).
            survivors = list(run.posts)
        if max_store is not None and len(survivors) > max_store:
            run.truncated_by = run.truncated_by or "query-budget"
            survivors = survivors[:max_store]
        self.store_posts(run, survivors)
        run.finished_at = self._clock()
        return run

    def drafts(self, run: XRun) -> list[DocumentDraft]:
        drafts = []
        for post, ref, chash in run.stored:
            drafts.append(
                DocumentDraft(
                    source=DOCUMENT_SOURCE,
                    external_id=post.external_id,
                    url=post.url,
                    text_ref=ref,
                    content_hash=chash,
                    created_at=post.created_at,
                    author_external_id=post.author_external_id,
                    author_handle=post.author_handle,
                    # X declares a language per post. Recorded, not detected -
                    # and carried rather than written, because
                    # `column_states.yaml` declares `document.lang` reserved.
                    lang=post.lang,
                    thread_root_external_id=post.conversation_id,
                    parent_external_id=post.replied_to_id,
                    engagement=post.engagement,
                )
            )
        return drafts

    def write_documents(
        self,
        conn,
        run: XRun,
        *,
        retrieval_provenance: str,
        harvest_run_id: str | None = None,
        batch: int = 500,
    ) -> WriteReport:
        from collect.adapters.documents import write_documents as write

        return write(
            conn,
            self.drafts(run),
            retrieval_provenance=retrieval_provenance,
            harvest_run_id=harvest_run_id,
            batch=batch,
        )

    def counts(self, run: XRun) -> SweepCounts:
        notes = [
            f"route: RapidAPI provider {settings().scraper_provider!r} at "
            f"{self._host} — NOT X's own API",
            "candidates are RETRIEVAL hits; the recorded sweep measured 993 "
            "returned against 573 surviving a literal match, so this is not a "
            "mention count",
        ]
        if run.author_legacy_fallbacks:
            notes.append(
                f"⚠ {run.author_legacy_fallbacks} post(s) had author fields only "
                "under `legacy`, which is the path that returned zeros for a "
                "whole sweep — check the response schema"
            )
        if run.unparseable_entries:
            notes.append(
                f"⚠ {run.unparseable_entries} entr(ies) matched the tweet shape "
                "and carried no readable id — the envelope may have changed"
            )
        if run.quota_limit is not None or run.quota_remaining is not None:
            notes.append(
                f"RapidAPI quota (SHARED WITH REDDIT): remaining="
                f"{run.quota_remaining} of limit={run.quota_limit}, reset in "
                f"{run.quota_reset_seconds}s — observed, not assumed"
            )
        return SweepCounts(
            platform=SOURCE_ID,
            requests_issued=run.search_calls,
            candidates=run.items_fetched,
            stored=run.items_kept,
            http_errors=run.http_errors,
            notes=notes,
        )


# ── parsing ──────────────────────────────────────────────────────────────
#
# THE ENVELOPE IS WALKED RATHER THAN INDEXED, and that is a decision with a
# cost. X's GraphQL search response nests tweets under
# instructions -> entries -> content -> itemContent -> tweet_results -> result,
# and a RapidAPI provider may wrap or flatten that. Indexing a fixed path
# against a shape nobody here has seen would produce zero posts on any
# variation, and zero posts reads as a platform with nothing to say.
#
# So: find every object that LOOKS like a tweet result - `rest_id` plus a
# `legacy` or `core` - wherever it sits. The cost is that a genuine change in
# what a tweet object looks like returns nothing rather than raising, which is
# why `unparseable_entries` is counted and reported.


def _tweet_results(payload: Any) -> list[dict[str, Any]]:
    """Every tweet-result object in the response, wherever the provider put it."""
    found: list[dict[str, Any]] = []
    seen: set[int] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("rest_id") and ("legacy" in node or "core" in node):
                if id(node) not in seen:
                    seen.add(id(node))
                    found.append(node)
                # Do not descend: a quoted or retweeted post hangs off this one
                # and is a different document that this query did not retrieve.
                return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)
    return found


def _next_cursor(payload: Any) -> str | None:
    """The `Bottom` cursor, wherever it sits. None where there is no next page."""
    cursors: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            kind = node.get("cursorType") or node.get("cursor_type")
            value = node.get("value")
            if kind and str(kind).casefold() == "bottom" and isinstance(value, str):
                cursors.append(value)
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return cursors[0] if cursors else None


def _author_of(result: dict[str, Any], run: XRun) -> tuple[str | None, str | None]:
    """`(author_external_id, handle)`, preferring the CURRENT paths.

    ⚠  `legacy` IS THE TRAP AND IT IS MEASURED. The recorded sweep found that
       `legacy` comes back empty on search results, and that the previous
       provider code read `user_legacy.followers_count` and therefore recorded
       every author as 0 followers for a whole sweep. A fallback that is not
       counted is the same defect with a different field.

    So the current paths are read first, `legacy` second, and every fallback
    increments `run.author_legacy_fallbacks`.
    """
    user = (
        (result.get("core") or {}).get("user_results", {}).get("result")
        or result.get("user_results", {}).get("result")
        or {}
    )
    if not isinstance(user, dict):
        return None, None

    # `rest_id` is the stable numeric account id and survives a rename, which is
    # the same reason Reddit keys on `t2_` and GitHub on `user.id`. Never the
    # screen name: a rename would split one person and a reused name merges two.
    external_id = user.get("rest_id") or user.get("id_str")

    handle = user.get("screen_name") or (user.get("core") or {}).get("screen_name")
    if not handle:
        legacy = user.get("legacy") or {}
        handle = legacy.get("screen_name")
        if handle:
            run.author_legacy_fallbacks += 1

    return (str(external_id) if external_id else None), handle


def _post_of(result: dict[str, Any], run: XRun) -> XPost | None:
    """One tweet result -> an `XPost`, or None where there is no readable id."""
    post_id = result.get("rest_id")
    legacy = result.get("legacy") or {}
    if not post_id:
        post_id = legacy.get("id_str")
    if not post_id:
        return None

    before = run.author_legacy_fallbacks
    author_id, handle = _author_of(result, run)
    from_legacy = run.author_legacy_fallbacks > before

    # A LONG POST'S TEXT IS NOT IN `full_text`. X truncates it there and puts
    # the whole thing under `note_tweet`; taking `full_text` would store a
    # truncated document that reads as complete, and a quote from its tail
    # would fail verification against text nobody has.
    note = (
        ((result.get("note_tweet") or {}).get("note_tweet_results") or {}).get("result")
        or {}
    )
    text = note.get("text") or legacy.get("full_text") or legacy.get("text") or ""

    views = (result.get("views") or {}).get("count")
    metrics = {
        "favorite_count": legacy.get("favorite_count"),
        "reply_count": legacy.get("reply_count"),
        "retweet_count": legacy.get("retweet_count"),
        "quote_count": legacy.get("quote_count"),
        "bookmark_count": legacy.get("bookmark_count"),
        # Absent on some posts by design; stays None. Stringified by the API,
        # so it is coerced here and left None where it will not coerce.
        "view_count": int(views) if isinstance(views, str) and views.isdigit() else views,
    }

    return XPost(
        post_id=str(post_id),
        text=text,
        author_external_id=author_id,
        author_handle=handle,
        created_at=legacy.get("created_at"),
        lang=legacy.get("lang"),
        conversation_id=(
            str(legacy["conversation_id_str"])
            if legacy.get("conversation_id_str")
            else None
        ),
        replied_to_id=(
            str(legacy["in_reply_to_status_id_str"])
            if legacy.get("in_reply_to_status_id_str")
            else None
        ),
        metrics=metrics,
        author_from_legacy=from_legacy,
        payload=json.dumps(result, sort_keys=True, ensure_ascii=False),
    )


def x_document_id(external_id: str) -> str:
    """`document.id` for an X post. The shared convention."""
    from collect.adapters.documents import document_id

    return document_id(DOCUMENT_SOURCE, external_id)


# ── the gated entry point ────────────────────────────────────────────────


def observe_x_use() -> dict[str, object]:
    """This run's live observations for the terms gate.

    THREE FACTS, and each one is a precondition a ruling should be able to pin:

        access_path        `rapidapi-reseller`, always. This route is NOT X's
                           own API and the ruling must not read as though it
                           were - Reddit's ruling records a reseller route as
                           an UNRESOLVED condition, and X's will too.
        scraper_provider   which provider, read from the environment. A ruling
                           reviewed for one provider stops applying when
                           somebody swaps it, rather than when somebody
                           remembers to revisit it - and a swap also changes the
                           response envelope the parser reads.
        credential_present whether a key exists at all.

    ⚠  FOUR FACTS SINCE 2026-09-08, AND `use_basis` IS THE FOURTH. This
       docstring used to say the basis was deliberately absent because "the
       basis belongs on the ruling, and this observes the ROUTE" - and then
       said what to do if a ruling ever rested on internal-development-only:
       share `observe_reddit_use`'s precondition rather than reimplement it
       here. `x-via-rapidapi-scraper` was ratified on that basis, so the
       sentence's own condition fired, and the shared observation now lives in
       `collect/adapters/basis.py` and is used by all three paths.

    ⚠  THE BASIS OBSERVATION IS A PROXY FOR `ENVIRONMENT` AND OBSERVES NOTHING
       ABOUT PUBLICATION, which is the condition the ruling actually turns on.
       `contract/sources.yaml`'s ENFORCEMENT block states that gap rather than
       letting this precondition imply a guard that does not exist.
    """
    config = settings()
    return {
        "access_path": "rapidapi-reseller",
        "scraper_provider": config.scraper_provider,
        # WHICH VARIABLE, not just whether one exists. `bool(rapidapi_key)` read
        # True while X's arm was 403ing on a Reddit key, because a key WAS
        # present - just not one subscribed to this provider. Presence was never
        # the question; provenance is.
        "credential_present": bool(key_for()[0]),
        "credential_source": key_for()[1],
        **observe_use_basis(),
    }


def harvester_for_source(source, *, rulings=None, **kwargs) -> XHarvester:
    """Build a harvester for a `source` row: ToS gate, then the credential.

    ⚠  BOTH REFUSALS ARE LIVE AND THE ORDER IS DELIBERATE. The terms gate runs
       FIRST, so the answer to "why can't I harvest X" is "nobody has read the
       terms" rather than "you need a key" - a key obtained to satisfy an error
       message is a key obtained before the question that matters was asked.
    """
    from collect.registry.assertions import assert_terms_reviewed, source_field

    source_id = source_field(source, "id", "?")
    assert_terms_reviewed(
        [source],
        rulings=rulings,
        observations={source_id: observe_x_use()},
    )
    return XHarvester(**kwargs)
