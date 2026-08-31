"""The GitHub adapter. Search, sieve, then fetch only what survived.

THE ORDER IS THE POINT
----------------------
Search, **sieve, fetch** — not search, fetch, sieve. The search response already
carries each issue's title and body, so it is the same gift a full-text RSS feed
gives the blog adapter: the body arrives before the request that would fetch it.
So the sieve runs on what search returned and only survivors cost a REST call.

That matters because of what issue #4 measured: the fetch half is the expensive
one — 672,000 REST calls and 134 hours for 708 queries, against 24 minutes of
search. Filtering before fetching is where the cost actually goes away, and it
turns Engineer 2's `yields_claim_when` argument into a budget saving rather than
a lament.

A REJECTED DOCUMENT IS STILL STORED — FOR THE PAGES THAT WERE STORED.
---------------------------------------------------------------------
"Sieve, then fetch" reads as though a rejected hit leaves no trace. It does:
`search()` writes the search response to `raw/` **before** `harvest()` sieves
anything, so every rejected hit's title and body are already on disk with the
rest of its page.

That is what the locality window in `contract/harvest.yaml` rests on. A window
that turns out too tight is fixed by RE-SIEVING the stored pages, not by
re-fetching them, because the text the sieve rejected is still there. Nobody
can see that from the call order, and the inference the other way — that
rejection discards — would make the whole recoverability argument false.

Recovery is also cheaper than a re-run: re-sieving costs nothing, and a
document the new window newly KEEPS costs one targeted REST call for its body.
It never costs a re-search, which is the rate-limited half — 30/minute against
core's 5,000/hour.

⚠ THE QUALIFIER IS LOAD-BEARING, so it is in the heading rather than a
footnote. **Only page 1 is stored** (`if page == 1` below). At `max_pages=1` —
the default, and every run so far — page 1 IS the result set, so the claim is
unconditionally true today. Raise `max_pages` and hits from pages 2+ are
sieved and never written: still filtered, no longer recoverable without a
re-search.

The unqualified sentence is what a reader infers from this docstring, and the
inference was made. Writing "recoverable" without "for the pages that were
stored" is the failure, not raising `max_pages`.

**Storing every page was the other option and was not taken.** It would make
the limit vanish, but `discovery_ref` is singular and would have to become
plural, and nothing else wants that. Recording what was stored is the rule 6
treatment: a re-sieve that can say *"this run stored page 1 of 4"* is a
re-sieve nobody over-trusts. `pages_fetched` / `pages_stored` on `harvest_run`
are proposed on issue #5 for exactly that, because documentation reaches
whoever reads it and not whoever raises `max_pages` at 6pm to clear a
result-ceiling — which is the obvious move in that moment, and trades
recoverability away with no signal at all.

TWO ARTIFACTS, SAME SHAPE AS BLOGS
----------------------------------
    search response  -> raw/   the discovery artifact, one per query
    issue payload    -> raw/   the per-document artifact; `document.text_ref`

`text_ref` names the issue, never the search page: one search response covers a
hundred issues, so pointing `text_ref` at it would stop `content_hash`
identifying one document — breaking dedupe and NFR-6 the same way it would for a
feed.

RATE LIMITS, OBSERVED RATHER THAN ASSUMED
-----------------------------------------
`GET /rate_limit` on 2026-08-13: search **30/minute**, core **5,000/hour**. They
are separate buckets, so they get separate limiters. The recorded terms note is
where those numbers live; this module reads them from settings rather than
restating them, so a limit change is a config change.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from collect.adapters.queries.github import SearchRequest
from collect.adapters.queries.sieve import SieveVerdict, SieveYield, tally
from collect.config import settings
from collect.ids import stable_id
from collect.limiter import HostLimiter
from collect.rawstore import RAW, RawStore

log = logging.getLogger(__name__)

#: Observed 2026-08-13 and recorded in `contract/sources.yaml`: search
#: 30/minute, core 5,000/hour, separate buckets.
SEARCH_LIMIT_PER_MINUTE = 30
CORE_LIMIT_PER_HOUR = 5000

#: Pace below the ceiling, not at it. The first live run paced at exactly
#: 60/30 = 2.0s, spent its whole minute on 30 searches, and the two probe
#: searches that followed were throttled — a limit hit not because the budget
#: was wrong but because there was no room in it for a retry or an afterthought.
#: 0.9 leaves three requests a minute spare.
SEARCH_HEADROOM = 0.9
SEARCH_INTERVAL = 60.0 / (SEARCH_LIMIT_PER_MINUTE * SEARCH_HEADROOM)
REST_INTERVAL = 60.0 / (CORE_LIMIT_PER_HOUR * SEARCH_HEADROOM / 60.0)

#: A throttle answers with one of these. 429 is the documented form; GitHub also
#: returns 403 for both primary and secondary rate limits, which is why the
#: status alone is not enough to tell a throttle from a permission error.
THROTTLE_STATUSES = frozenset({403, 429})

#: How long to wait for a reset before giving up and recording the truncation.
#: Longer than a search window, shorter than a coffee.
MAX_BACKOFF_SECONDS = 90.0
MAX_ATTEMPTS = 2

#: GitHub returns at most 1,000 results per search, 100 per page. `result-ceiling`
#: in `harvest_run.truncated_by` exists for the queries that hit it.
PER_PAGE = 100
RESULT_CEILING = 1000

GITHUB_SOURCE_ID = "github"
DOCUMENT_SOURCE = "github"


def github_author_id(hit: Any) -> str | None:
    """The `author.id` a hit attributes to, or None where there is no identity.

    Keyed on `user.id`, the stable numeric account id — NOT `user.login`. A login
    is renameable, so keying on it makes a renamed account a new author and a
    reused name two people merged into one. Reddit's `t2_` canonicalisation
    exists for the same reason and this is the symmetric case.

    **None must survive to the column.** Every fallback available here is worse
    than NULL: the login splits one person across a rename, and any sentinel
    merges every deleted account into a single `author` row that the gate then
    counts as a voice corroborating itself.
    """
    return github_author_id_for(
        getattr(hit, "author_external_id", None), getattr(hit, "author", None)
    )


def github_author_id_for(external_id: Any, handle: str | None) -> str | None:
    """The same id, from the two values rather than from a hit object.

    EXTRACTED SO COMMENTS AND ISSUES CANNOT DISAGREE ABOUT WHO AN AUTHOR IS.
    `SearchHit` calls the handle `author` and `StoredComment` calls it
    `author_handle`, so a duck-typed `getattr(hit, "author")` would silently
    return None for every comment - producing a `handle_hash` of None on rows
    that have a handle, and two different `author.id` values for one person
    depending on which path found them. That is the over-clustering failure in
    reverse: the same account split in two, corroborating itself.
    """
    from collect.assemble.authors import AuthorRow, hash_handle

    if not external_id:
        return None
    return AuthorRow(
        source=DOCUMENT_SOURCE,
        external_id=str(external_id),
        handle_hash=hash_handle(handle),
    ).id


@dataclass(frozen=True)
class SearchHit:
    """One search result. Carries the body, which is why the sieve can run first."""

    api_url: str
    html_url: str
    repo: str
    number: int
    title: str
    body: str
    created_at: str | None
    #: The login. MUTABLE — GitHub allows renames, so this is not an identity.
    #: Kept because it is the only handle available and `author.handle_hash`
    #: needs it transiently; nothing retains it past that.
    author: str | None
    #: The account's STABLE numeric id, which survives a rename. This is
    #: GitHub's equivalent of Reddit's `t2_` and the adapter was discarding it —
    #: `user.login` was the only thing kept, which is the exact failure the
    #: Reddit canonicalisation exists to avoid. None when the API omits `user`,
    #: which happens for a deleted account (rule 6: absent, not guessed).
    author_external_id: str | None
    comment_count: int
    reactions: int

    @property
    def external_id(self) -> str:
        """`owner/repo#123` — the publisher's own identity for the issue."""
        return f"{self.repo}#{self.number}"

    @property
    def sieve_text(self) -> str:
        return f"{self.title}\n{self.body}"


@dataclass(frozen=True)
class StoredIssue:
    external_id: str
    html_url: str
    ref: str
    content_hash: str
    size: int
    already_present: bool
    hit: SearchHit


@dataclass
class StoredComment:
    """One GitHub issue comment, stored as its own payload.

    `author_handle` IS CARRIED AND IS NOT STORED TO THE DATABASE BY THIS CLASS.
    It exists because `n_eff` counts distinct VOICES and the comment author is
    the whole point of fetching comments at all - a second person on a thread is
    a second voice, the same person twice is still one. `collect/assemble/
    authors.py` hashes it; per the 2026-08-18 ruling the handle itself is
    retained nowhere, and it reaches `handle_hash` transiently.

    `author_external_id` IS `user.id`, NOT `user.login`, for the reason Reddit's
    `t2_` canonicalisation exists: a numeric id survives a rename and a reused
    login merges two people, which is the over-clustering `collect/CLAUDE.md`
    calls the worse of the two failures. It was absent from this class until
    2026-08-30, which meant a comment could not have become a voice even after
    it was written - `document.author_id` references `author.id` and there was
    nothing to reference.

    `author_type` IS THE API'S OWN ANSWER TO "IS THIS A BOT", and see `is_bot`.
    """

    external_id: str
    issue_api_url: str
    html_url: str
    author_handle: str | None
    #: `user.id`. None for a deleted account, which gets no author row rather
    #: than a shared sentinel - a sentinel would merge every deleted account
    #: into one voice that then corroborates itself.
    author_external_id: str | None
    #: `user.type`, verbatim: "User", "Bot", "Organization", or None when the
    #: payload carried no user at all. NOT normalised to a boolean here, because
    #: the ruling on what to do with a bot is Engineer 2's and a boolean would
    #: bake half of it in.
    author_type: str | None
    #: `created_at`, so a comment document carries when the human wrote it.
    #: `weight.recency_factor` subtracts this from `as_of`, and a missing date
    #: sends the claim down the "no document facts" path rather than being
    #: dated from a default.
    created_at: str | None
    #: The comment body, for assembly. Held rather than re-read from the store,
    #: because the fetch already parsed the payload once.
    body: str | None
    ref: str
    content_hash: str
    already_present: bool

    @property
    def is_bot(self) -> bool:
        """Whether GitHub says this account is a bot.

        ⚠ KEYED ON `user.type`, AND THE `[bot]` SUFFIX IS ONLY A CORROBORATION.
          Measured over the 148 comments already fetched: `user.type == "Bot"`
          and `login.endswith("[bot]")` agree on all 148, 23 Bot and 125 User,
          with no disagreement in either direction.

          THAT AGREEMENT HAS A DENOMINATOR OF TWO, NOT 148. The 23 bot comments
          come from exactly two accounts - `github-actions[bot]` and
          `linear[bot]` - so what is measured is that two GitHub Apps follow
          GitHub's own naming convention, which they do because the platform
          renders it. 148 is the comment count and the wrong denominator to
          quote (rule 7).

          So the suffix is not sufficient and is not used as the test. It is a
          STRING HEURISTIC over a name a human can choose: a person may register
          `notabot` or a helpful maintainer may be called `releasebot`, and
          neither is a GitHub App. `user.type` is the platform DECLARING what
          the account is, which is a field rather than an inference - the same
          distinction as `document.has_numbers` counting versus the extractor
          asserting. `bot_suffix_disagrees` reports any row where the two part
          company, so the day one does, it is a finding rather than a silent
          reclassification.
        """
        return (self.author_type or "").casefold() == "bot"

    @property
    def bot_suffix_disagrees(self) -> bool:
        """`user.type` and the `[bot]` suffix pointing different ways.

        Zero on the 148 comments measured. Counted anyway, because it is the
        only thing that would tell us the heuristic and the field have diverged
        - and the population that would show it is the one we have not fetched.
        """
        handle = (self.author_handle or "").casefold()
        return self.is_bot != handle.endswith("[bot]")


@dataclass
class QueryRun:
    """What one query cost and what it produced. The FR-10 row, plus the sieve."""

    request: SearchRequest

    #: None means WE DO NOT KNOW, which is what a throttled query leaves behind.
    #: It was `int = 0` for the first live run, and a rate-limited query then
    #: reported "zero matches" — the same shape as the 304 read as a dead feed
    #: and the non-XML page read as an empty one. Rule 6 in the harvest layer:
    #: an absent answer must not become a definite one.
    total_count: int | None = None
    retrieved: int = 0
    truncated_by: str | None = None
    search_calls: int = 0
    rest_calls: int = 0
    http_errors: int = 0
    discovery_ref: str | None = None
    verdicts: list[SieveVerdict] = field(default_factory=list)
    stored: list[StoredIssue] = field(default_factory=list)

    #: What retrieval returned and the sieve rejected, with the group that
    #: failed. Kept because "the query was wrong" and "this document is
    #: off-topic" are different findings and the `missing` group is what tells
    #: them apart — and because a rejection nobody can inspect is indistinguishable
    #: from a query that returned nothing.
    rejected: list[tuple[str, str, tuple[str, ...]]] = field(default_factory=list)

    #: The platform stopped us. Distinct from `retrieved == 0`, which is the
    #: platform answering "nothing matches".
    rate_limited: bool = False
    backoff_waits: list[float] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None

    @property
    def sieve_yield(self) -> SieveYield:
        return tally(self.request.query_key, self.verdicts)

    @property
    def kept(self) -> int:
        return len(self.stored)


class GitHubHarvester:
    """Issues one query, sieves what came back, fetches what survived."""

    def __init__(
        self,
        *,
        client: httpx.Client,
        store: RawStore,
        search_limiter: HostLimiter | None = None,
        rest_limiter: HostLimiter | None = None,
        max_pages: int = 1,
        max_fetch_per_query: int | None = None,
        pipeline_version: str | None = None,
        sleeper=time.sleep,
        epoch=time.time,
    ) -> None:
        self._client = client
        self._store = store
        self._search = (
            HostLimiter(min_interval=SEARCH_INTERVAL) if search_limiter is None else search_limiter
        )
        self._rest = (
            HostLimiter(min_interval=REST_INTERVAL) if rest_limiter is None else rest_limiter
        )
        self._max_pages = max_pages
        self._max_fetch = max_fetch_per_query
        self.pipeline_version = pipeline_version or settings().pipeline_version
        self._sleep = sleeper
        self._epoch = epoch

        #: Every run this harvester performed, whether or not the caller kept it.
        #:
        #: The first live run's report showed `http_errors: 0` while a query had
        #: been throttled, because the totals were summed over the list the
        #: caller happened to hold and the probe run was not in it. An instrument
        #: that under-reports its own failures is worse than no instrument, so the
        #: ledger lives here and cannot be forgotten by a call site.
        self.ledger: list[QueryRun] = []

    def _remember(self, run: QueryRun) -> None:
        if not any(existing is run for existing in self.ledger):
            self.ledger.append(run)

    def totals(self) -> dict[str, Any]:
        """Aggregate over every run performed, not over what the caller kept."""
        return {
            "queries": len(self.ledger),
            "search_calls": sum(r.search_calls for r in self.ledger),
            "rest_calls": sum(r.rest_calls for r in self.ledger),
            "http_errors": sum(r.http_errors for r in self.ledger),
            "rate_limited_queries": sum(1 for r in self.ledger if r.rate_limited),
            "backoff_seconds": round(sum(sum(r.backoff_waits) for r in self.ledger), 1),
            "unknown_total_count": sum(1 for r in self.ledger if r.total_count is None),
            "retrieved": sum(r.retrieved for r in self.ledger),
            "sieve_kept": sum(r.sieve_yield.kept for r in self.ledger),
            "stored": sum(len(r.stored) for r in self.ledger),
        }

    # ── search ───────────────────────────────────────────────────────────

    def _get(
        self, url: str, *, params: dict[str, Any] | None = None, search: bool
    ) -> httpx.Response:
        (self._search if search else self._rest).wait(url)
        return self._client.get(url, params=params)

    @staticmethod
    def is_throttled(response: httpx.Response) -> bool:
        """Did the platform stop us, or refuse us for another reason?

        A 403 is GitHub's answer to both a rate limit and a permission problem,
        so the status alone cannot tell them apart. Three signals, any of which
        settles it: an exhausted remaining count, a `retry-after`, or the
        message itself.
        """
        if response.status_code not in THROTTLE_STATUSES:
            return False
        if response.status_code == 429:
            return True
        if response.headers.get("x-ratelimit-remaining") == "0":
            return True
        if response.headers.get("retry-after"):
            return True
        return "rate limit" in response.text[:500].lower()

    def _backoff_seconds(self, response: httpx.Response) -> float:
        """How long the platform says to wait, bounded.

        `retry-after` is seconds; `x-ratelimit-reset` is an absolute epoch, so it
        needs the clock rather than arithmetic on a duration. Both are honoured
        because GitHub uses the first for secondary limits and the second for
        primary ones.
        """
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return min(float(retry_after), MAX_BACKOFF_SECONDS)
            except ValueError:
                pass

        reset = response.headers.get("x-ratelimit-reset")
        if reset:
            try:
                wait = float(reset) - self._epoch()
                if wait > 0:
                    return min(wait + 1.0, MAX_BACKOFF_SECONDS)
            except ValueError:
                pass
        return min(SEARCH_INTERVAL * 2, MAX_BACKOFF_SECONDS)

    def _search_page(
        self, request: SearchRequest, page: int, run: QueryRun
    ) -> httpx.Response | None:
        """One search request, retried once if the platform throttled it.

        Returns None when the throttle survived the backoff. The caller must not
        treat that as an empty result set — that conflation is the defect this
        method exists to remove.
        """
        for attempt in range(1, MAX_ATTEMPTS + 1):
            response = self._get(
                "https://api.github.com/search/issues",
                params={"q": request.query, "per_page": PER_PAGE, "page": page},
                search=True,
            )
            run.search_calls += 1

            if response.status_code == 200:
                return response

            if self.is_throttled(response):
                wait = self._backoff_seconds(response)
                run.backoff_waits.append(wait)
                log.warning(
                    "search throttled (%s) on attempt %d/%d, waiting %.1fs: %s",
                    response.status_code, attempt, MAX_ATTEMPTS, wait, request.query[:80],
                )
                if attempt < MAX_ATTEMPTS:
                    self._sleep(wait)
                    continue
                run.rate_limited = True
                run.truncated_by = "rate-limit"
                run.http_errors += 1
                return None

            run.http_errors += 1
            log.error("search failed %s: %s", response.status_code, response.text[:200])
            return None
        return None  # pragma: no cover - loop always returns

    def search(self, request: SearchRequest, run: QueryRun) -> list[SearchHit]:
        """Issue the query, store the discovery artifact, return the hits.

        `run.total_count` stays None unless the platform actually told us a
        number. A throttled query leaves it None and sets `truncated_by` to
        `rate-limit`, so "we were not allowed to look" is never written as
        "nothing matched".
        """
        self._remember(run)
        hits: list[SearchHit] = []
        for page in range(1, self._max_pages + 1):
            response = self._search_page(request, page, run)
            if response is None:
                return hits

            payload = response.json()
            if page == 1:
                run.total_count = payload.get("total_count", 0)
                stored = self._store.put(response.content, namespace=RAW)
                run.discovery_ref = stored.ref

            items = payload.get("items", [])
            hits.extend(self._hit_of(item) for item in items)
            if len(items) < PER_PAGE:
                break

        run.retrieved = len(hits)
        if run.total_count is None:
            return hits
        if run.total_count > RESULT_CEILING:
            run.truncated_by = "result-ceiling"
        elif run.total_count > run.retrieved:
            # We chose to stop, which is a different statement from the platform
            # stopping us, and `truncated_by` keeps them apart.
            run.truncated_by = "query-budget"
        return hits

    @staticmethod
    def _hit_of(item: dict[str, Any]) -> SearchHit:
        html_url = item.get("html_url", "")
        parts = html_url.split("/")
        repo = "/".join(parts[3:5]) if len(parts) > 5 else ""
        return SearchHit(
            api_url=item.get("url", ""),
            html_url=html_url,
            repo=repo,
            number=int(item.get("number", 0)),
            title=item.get("title") or "",
            body=item.get("body") or "",
            created_at=item.get("created_at"),
            author=(item.get("user") or {}).get("login"),
            author_external_id=(
                str((item.get("user") or {}).get("id"))
                if (item.get("user") or {}).get("id") is not None
                else None
            ),
            comment_count=int(item.get("comments") or 0),
            reactions=int((item.get("reactions") or {}).get("total_count") or 0),
        )

    # ── sieve, then fetch ────────────────────────────────────────────────

    def harvest(self, request: SearchRequest, *, run: QueryRun | None = None) -> QueryRun:
        """One query, end to end. Only sieve survivors cost a REST call.

        `run` EXISTS SO THE LEDGER CAN BE TWO-PHASE, and that is the whole reason
        for the parameter. `harvest_run_fields` derives the row id from
        `run.started_at`, and `started_at` is minted when the `QueryRun` is
        constructed — so a caller that cannot construct it cannot open a
        `harvest_run` row *before* the fetch. Opening it afterwards would give up
        the one property the two-phase writer exists for: **a process that dies
        cannot write its own failure**, so a killed sweep has to leave
        `finished_at IS NULL` behind.

        Passing a run in keeps the id derivation exactly as it was and moves
        nothing else. Omitting it behaves as before.
        """
        run = run if run is not None else QueryRun(request=request)
        self._remember(run)
        hits = self.search(request, run)

        survivors: list[SearchHit] = []
        for hit in hits:
            verdict = request.sieve(hit.sieve_text)
            run.verdicts.append(verdict)
            if verdict.passed:
                survivors.append(hit)
            else:
                run.rejected.append((hit.html_url, hit.title, verdict.missing))

        if self._max_fetch is not None and len(survivors) > self._max_fetch:
            log.warning(
                "query-budget: %d survivors, fetching %d", len(survivors), self._max_fetch
            )
            run.truncated_by = run.truncated_by or "query-budget"
            survivors = survivors[: self._max_fetch]

        for hit in survivors:
            stored = self.fetch_issue(hit, run)
            if stored is not None:
                run.stored.append(stored)

        run.finished_at = datetime.now(UTC)
        return run

    def fetch_issue(self, hit: SearchHit, run: QueryRun) -> StoredIssue | None:
        """Fetch the issue itself — the per-document artifact `text_ref` names."""
        try:
            response = self._get(hit.api_url, search=False)
        except httpx.HTTPError as error:
            run.http_errors += 1
            log.error("fetch failed for %s: %s", hit.html_url, error)
            return None

        run.rest_calls += 1
        if response.status_code != 200:
            run.http_errors += 1
            log.error("fetch %s returned %s", hit.html_url, response.status_code)
            return None

        stored = self._store.put(response.content, namespace=RAW)
        return StoredIssue(
            external_id=hit.external_id,
            html_url=hit.html_url,
            ref=stored.ref,
            content_hash=stored.content_hash,
            size=stored.size,
            already_present=stored.already_present,
            hit=hit,
        )

    # ── comments: the voices half ────────────────────────────────────────
    #
    # WHY THIS IS NOT A TIDINESS FIX. `coverage_ratio` reads 0.0 on all 71 github
    # contexts with 149 comments recorded as `hidden_children_min`, and that
    # number is honest rather than cosmetic: we read the issue body and none of
    # the thread. What the thread holds is DISTINCT AUTHORS, and `n_eff` counts
    # VOICES - one engineer posting five times is one voice, and a second person
    # writing "same here, on 4.8 as well" is a second voice on the same cell.
    #
    # WHY IT IS FREE. `GET /rate_limit`, measured: search 30/minute, core
    # 5,000/hour, SEPARATE BUCKETS. Discovery spends search; this spends core,
    # which is otherwise used only for issue bodies. The whole current corpus is
    # 32 requests - every commented issue has at most 46 comments and
    # `per_page=100` takes them in one page - which is 0.64% of one hour.
    #
    # So this rides the existing sweep and cannot slow discovery down. That is
    # the exact opposite of Reddit, where the equivalent is 132,442 unread
    # comments and a real cost.

    #: One page holds every comment on every issue in the corpus (max observed
    #: 46). Paging is still implemented, because "max observed" is a fact about
    #: 80 documents and not a property of GitHub.
    COMMENTS_PER_PAGE = 100

    def fetch_comments(
        self,
        issue_api_url: str,
        run: QueryRun,
        *,
        max_pages: int = 5,
    ) -> list[StoredComment]:
        """Every comment on one issue, stored individually.

        STORED PER COMMENT, not as one page blob, and for the reason the
        content_hash ruling settled: `text_ref` names the per-document artifact
        so `content_hash` identifies ONE document. A page holding forty comments
        would make forty documents share a hash and break dedupe the same way a
        search response would - `github.py`'s own argument for why `text_ref`
        names the issue rather than the search page, one level down.

        Returns [] rather than raising on an HTTP failure: a thread whose
        comments could not be fetched is a coverage fact, and the issue body is
        still worth keeping. The failure is counted on `run`.
        """
        stored: list[StoredComment] = []
        for page in range(1, max_pages + 1):
            url = f"{issue_api_url}/comments"
            try:
                response = self._get(
                    url,
                    params={"per_page": self.COMMENTS_PER_PAGE, "page": page},
                    search=False,
                )
            except httpx.HTTPError as error:
                run.http_errors += 1
                log.error("comment fetch failed for %s: %s", url, error)
                return stored

            run.rest_calls += 1
            if response.status_code != 200:
                run.http_errors += 1
                log.error("comment fetch %s returned %s", url, response.status_code)
                return stored

            try:
                payload = response.json()
            except ValueError:
                run.http_errors += 1
                log.error("comment fetch %s returned unparseable JSON", url)
                return stored
            if not isinstance(payload, list) or not payload:
                return stored

            for comment in payload:
                if not isinstance(comment, dict) or comment.get("id") is None:
                    continue
                # EACH COMMENT IS ITS OWN STORED PAYLOAD. `json.dumps` with
                # sorted keys so the same comment re-fetched hashes identically
                # and the content-addressed store deduplicates it.
                blob = json.dumps(comment, sort_keys=True, ensure_ascii=False)
                put = self._store.put(blob, namespace=RAW)
                user = comment.get("user") or {}
                stored.append(
                    StoredComment(
                        external_id=f"gh-comment:{comment['id']}",
                        issue_api_url=issue_api_url,
                        html_url=comment.get("html_url") or "",
                        author_handle=user.get("login"),
                        # `user.id`, stringified. Absent for a deleted account.
                        author_external_id=(
                            str(user["id"]) if user.get("id") is not None else None
                        ),
                        author_type=user.get("type"),
                        created_at=comment.get("created_at"),
                        body=comment.get("body"),
                        ref=put.ref,
                        content_hash=put.content_hash,
                        already_present=put.already_present,
                    )
                )

            if len(payload) < self.COMMENTS_PER_PAGE:
                return stored
        return stored

    # ── the write path ───────────────────────────────────────────────────

    def write_documents(
        self,
        conn,
        run: QueryRun,
        *,
        batch: int = 500,
        harvest_run_id: str | None = None,
    ) -> dict[str, int]:
        """Insert one `document` per stored issue, WITH `author_id`. Absent values stay NULL.

        **`author_id` was omitted here until 2026-08-21 and it was the whole
        column: 0 of 27 `github` document rows carried an author.** The id was
        never missing — `SearchHit.author_external_id` has held `user.id` since
        the adapter stopped keeping `user.login` alone — it simply was not being
        written. `judge/curate/gate.py:count` dedups voices off
        `claim.author_id`, so a NULL there is not an unknown author, it is no
        voice at all.

        `user.id` and not `user.login`, for the reason Reddit's `t2_`
        canonicalisation exists: the numeric id survives a rename, a login does
        not, and a reused login merges two people — the over-clustering
        `collect/CLAUDE.md` calls the worse of the two failures.

        AUTHORS ARE WRITTEN FIRST, because `document.author_id` references
        `author.id`. A hit from a deleted account has no `user.id`, gets no
        author row, and keeps `author_id` NULL rather than sharing one — a
        sentinel would merge every deleted account into a single voice that then
        corroborates itself.

        `ON CONFLICT DO NOTHING` on `(source, external_id)`: two queries in one
        sweep legitimately return the same issue, and the second is not an error.

        BATCHED, BECAUSE THE ROUND TRIP DOMINATES — the same shape and the same
        fix as `assemble.authors.write_authors`, which took ten minutes for 4,391
        rows at roughly 130ms of latency each and 3.8 seconds batched. This path
        has never run against a remote instance with volume: every run so far has
        been one query against a local Postgres, where 130ms is 1ms and the shape
        is invisible. Inside the nightly chain it presents as a chain that appears
        to hang.

        `seen` and `inserted` are now separate, and that was a second defect
        rather than a consequence of batching. The old counter incremented once
        per row and called the total `written`, so a sweep whose queries
        legitimately returned the same issue twice reported writing it twice. A
        conflict affects no rows, so `cur.rowcount` over the batch counts the
        inserts that actually happened.
        """
        from collect.assemble.authors import from_github, write_authors

        hits = [issue.hit for issue in run.stored]
        extraction = from_github(hits)
        author_counts = write_authors(conn, extraction.rows, batch=batch)

        rows = [
            {
                "id": stable_id("doc", DOCUMENT_SOURCE, issue.external_id),
                "source": DOCUMENT_SOURCE,
                "external_id": issue.external_id,
                "url": issue.html_url,
                "created_at": issue.hit.created_at,
                "text_ref": issue.ref,
                "content_hash": issue.content_hash,
                "engagement": json.dumps(
                    {"comments": issue.hit.comment_count, "reactions": issue.hit.reactions}
                ),
                "author_id": github_author_id(issue.hit),
                # RETRIEVAL PROVENANCE. github is the only source that renders a
                # query, so it is the only one that can carry a run id — and the
                # two columns move together or the CHECK refuses the row.
                #
                # `not_recorded` when no id was passed, NOT `no_run_for_source`:
                # a run exists for every github document, so the honest reading
                # of a missing id is that this caller did not supply one. A
                # default claiming github has no runs would be false and
                # unfalsifiable from the row.
                "harvest_run_id": harvest_run_id,
                "retrieval_provenance": (
                    "run_recorded" if harvest_run_id else "not_recorded"
                ),
            }
            for issue in run.stored
        ]
        statement = (
            "INSERT INTO document (id, source, external_id, url, created_at, fetched_at, "
            "text_ref, content_hash, engagement, author_id, status, "
            "harvest_run_id, retrieval_provenance) "
            "VALUES (%(id)s, %(source)s, %(external_id)s, %(url)s, %(created_at)s, now(), "
            "%(text_ref)s, %(content_hash)s, %(engagement)s, %(author_id)s, 'kept', "
            "%(harvest_run_id)s, %(retrieval_provenance)s) "
            "ON CONFLICT (source, external_id) DO NOTHING"
        )
        inserted = 0
        with conn.cursor() as cur:
            for start in range(0, len(rows), batch):
                cur.executemany(statement, rows[start:start + batch])
                inserted += max(0, cur.rowcount)

        # AND ATTRIBUTE THE ROWS THAT ALREADY EXISTED. `ON CONFLICT DO NOTHING`
        # is right for every other column and wrong for this one: the 27 github
        # documents written before `author_id` existed would otherwise stay
        # anonymous through every future sweep, because the conflict is silent
        # and the row looks written. Guarded by `author_id IS NULL`, so a real
        # attribution is never replaced by a later parse. Same fix, same
        # reasoning, as `reddit_write.write_documents`.
        attributions = [
            {"id": r["id"], "author_id": r["author_id"]}
            for r in rows if r["author_id"] is not None
        ]
        attributed = 0
        if attributions:
            with conn.cursor() as cur:
                for start in range(0, len(attributions), batch):
                    cur.executemany(
                        "UPDATE document SET author_id = %(author_id)s "
                        "WHERE id = %(id)s AND author_id IS NULL",
                        attributions[start:start + batch],
                    )
                    attributed += max(0, cur.rowcount)
        return {
            "inserted": inserted,
            "seen": len(rows),
            "authors_attached_to_existing": max(0, attributed - inserted),
            "authors_inserted": author_counts["inserted"],
            "distinct_authors": extraction.distinct_authors,
            # NAMED RATHER THAN DROPPED. A hit from a deleted account has no
            # `user.id` and therefore no voice; the count separates "few voices"
            # from "few ATTRIBUTABLE voices", which are different findings.
            "documents_without_author": sum(1 for r in rows if r["author_id"] is None),
            "unattributable": extraction.unattributable,
        }

    #: What `filter_reasons` records for a comment whose author GitHub declares
    #: a bot. Named rather than inlined so `/filtered` and this write path
    #: cannot disagree about the string, and so a grep finds both.
    BOT_AUTHOR_REASON = "bot_author"

    def write_comments(
        self,
        conn,
        comments: Sequence[StoredComment],
        *,
        issue_document_id_by_api_url: dict[str, str],
        harvest_run_id: str | None = None,
        batch: int = 500,
    ) -> dict[str, int]:
        """Insert one `document` per stored comment, linked to its issue.

        148 COMMENTS WERE FETCHED AND NOTHING STORED THEM. That is what this
        closes. The value is voices: 65 distinct human comment authors against
        45 issue-body authors, and `n_eff` counts authors rather than claims, so
        comments roughly double the voice pool on the platform where the
        publishable evidence is.

        ⚠ A BOT IS NOT A VOICE, AND THIS PATH REFUSES TO MAKE ONE.

        `github-actions[bot]` is the single busiest commenter in the corpus at
        22 of 148, and `linear[bot]` brings the pair to 23. Nothing filters bots
        anywhere today. A bot comment reaching `n_eff` would be an automated
        account corroborating a cell, which is the failure the voice count
        exists to prevent, arriving through a door nobody had shut.

        WHAT THIS DOES, AND WHAT IT DELIBERATELY DOES NOT DECIDE. The ruling on
        bots - drop at collection, or weight at E6 - is Engineer 2's, and
        `judge/vet/reject.py` is her file. So this stores the row and refuses to
        make it a voice, which is the only option that keeps both rulings open:

            status            'filtered', not 'kept'
            filter_reasons    ['bot_author'], so /filtered names the rule
            author_id          NULL, so no `author` row and no voice
            the payload        kept, so a ruling either way is applied to data
                               we already hold rather than to a re-fetch

        DROPPING THE ROW ENTIRELY WOULD PREJUDGE IT. "Rejected is not deleted"
        is this project's rule for exactly this case: a filter you cannot
        inspect cannot be trusted, and a bot comment that never reached the
        table cannot be re-weighted the day the ruling says weight it.

        ⚠ `author_id` NULL IS NOT ENOUGH ON ITS OWN, which is why assembly
          excludes bots too. `judge/store/cells.py` maps a NULL author to
          `ANONYMOUS_VOICE:platform` - one shared voice per platform - so a bot
          left in an assembled thread could still be quoted and still contribute
          that shared voice. The guard that matters is `assemble_issue_thread`
          refusing bots as members; this one stops the row being an author.
        """
        from collect.assemble.authors import AuthorRow, hash_handle, write_authors

        linked = [c for c in comments if c.issue_api_url in issue_document_id_by_api_url]
        skipped_unlinked = len(comments) - len(linked)

        humans = [c for c in linked if not c.is_bot]
        bots = [c for c in linked if c.is_bot]
        disagreements = sum(1 for c in linked if c.bot_suffix_disagrees)

        # AUTHORS FIRST, because `document.author_id` references `author.id`.
        # Humans only - see the docstring.
        author_rows = [
            AuthorRow(
                source=DOCUMENT_SOURCE,
                external_id=str(c.author_external_id),
                handle_hash=hash_handle(c.author_handle),
            )
            for c in humans
            if c.author_external_id
        ]
        author_counts = write_authors(conn, author_rows, batch=batch)

        rows = []
        for comment in linked:
            issue_document_id = issue_document_id_by_api_url[comment.issue_api_url]
            is_bot = comment.is_bot
            rows.append(
                {
                    "id": stable_id("doc", DOCUMENT_SOURCE, comment.external_id),
                    "source": DOCUMENT_SOURCE,
                    "external_id": comment.external_id,
                    "url": comment.html_url,
                    "created_at": comment.created_at,
                    "text_ref": comment.ref,
                    "content_hash": comment.content_hash,
                    # THE THREAD LINKS, and this is the first github row to
                    # carry either. Every github document before this had
                    # `parent_id IS NULL` and `thread_root_id IS NULL`, because
                    # every one was an issue body with no fetched children.
                    "parent_id": issue_document_id,
                    "thread_root_id": issue_document_id,
                    "author_id": (
                        None
                        if is_bot or not comment.author_external_id
                        else github_author_id_for(comment.author_external_id, comment.author_handle)
                    ),
                    "status": "filtered" if is_bot else "kept",
                    "filter_reasons": [self.BOT_AUTHOR_REASON] if is_bot else None,
                    "harvest_run_id": harvest_run_id,
                    "retrieval_provenance": (
                        "run_recorded" if harvest_run_id else "not_recorded"
                    ),
                }
            )

        statement = (
            "INSERT INTO document (id, source, external_id, url, created_at, fetched_at, "
            "text_ref, content_hash, parent_id, thread_root_id, author_id, status, "
            "filter_reasons, harvest_run_id, retrieval_provenance) "
            "VALUES (%(id)s, %(source)s, %(external_id)s, %(url)s, %(created_at)s, now(), "
            "%(text_ref)s, %(content_hash)s, %(parent_id)s, %(thread_root_id)s, "
            "%(author_id)s, %(status)s, %(filter_reasons)s, "
            "%(harvest_run_id)s, %(retrieval_provenance)s) "
            "ON CONFLICT (source, external_id) DO NOTHING"
        )
        inserted = 0
        with conn.cursor() as cur:
            for start in range(0, len(rows), batch):
                cur.executemany(statement, rows[start:start + batch])
                inserted += max(0, cur.rowcount)

        return {
            "seen": len(comments),
            "linked": len(linked),
            # NAMED, not folded into `seen`. A comment whose issue is not in the
            # map is a plumbing fault - the caller built the map - and a comment
            # written by a bot is a ruling. Counting them together would let a
            # broken map read as a well-filtered sweep.
            "skipped_no_issue": skipped_unlinked,
            "inserted": inserted,
            "human": len(humans),
            "bot_filtered": len(bots),
            "bot_accounts": len({c.author_handle for c in bots if c.author_handle}),
            "bot_suffix_disagreements": disagreements,
            "unattributable": sum(1 for c in humans if not c.author_external_id),
            "authors_inserted": author_counts.get("inserted", 0),
        }

    def harvest_run_fields(self, run: QueryRun) -> dict[str, Any]:
        """The `harvest_run` row, plus the two fields with nowhere to live yet."""
        return {
            "id": stable_id("hr", GITHUB_SOURCE_ID, run.request.query_key,
                            run.started_at.isoformat()),
            "source_id": GITHUB_SOURCE_ID,
            "query_key": run.request.query_key,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "items_fetched": run.retrieved,
            "items_kept": run.kept,
            "http_errors": run.http_errors,
            # NULL where the platform never told us, which is what a throttle
            # leaves behind. `false` would assert there is more to fetch and
            # `true` would assert the query finished; neither is known.
            "exhausted": None if run.total_count is None else run.total_count <= run.retrieved,
            "truncated_by": run.truncated_by,
            "pipeline_version": self.pipeline_version,
            # ── proposed, not in contract/tables.sql ──
            "outcome": self.outcome_of(run),
            "sieve_pass_rate": round(run.sieve_yield.pass_rate, 3),
        }

    @staticmethod
    def outcome_of(run: QueryRun) -> str:
        """The proposed `harvest_run.outcome` value for this run.

        **CORRECTED 2026-08-20, BY THE FIRST REAL SWEEP.** This returned
        `fetched`, from the set proposed on #5
        (`fetched | not-modified | robots-blocked | error`). That set never
        landed: `harvest_run_outcome_ck` allows `ok | refused | error`, aligned
        with `job_run` and with `chain.py`'s OK/REFUSED/ERROR by migration
        `20260818T1520`. So every close raised, **121 rows were opened and none
        closed**, and the run reported success — two vocabularies for one column,
        with nothing checking they stayed in step. Same defect the other lane
        already fixed once, in `a289adf`.

        The distinctions #5 wanted are not lost, they are carried by the columns
        that already hold them: `truncated_by = 'rate-limit'` separates a throttle
        from an error, and `items_fetched = 0` separates "ran and found nothing"
        from a NULL that means it never came back.

        `refused` is not returned here. A query that reaches this adapter has
        passed the terms gate; a refusal happens upstream and never builds a run.
        Named so the absence is a decision rather than an oversight.
        """
        if run.rate_limited:
            return "error"
        if run.http_errors:
            return "error"
        return "ok"
