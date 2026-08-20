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

    # ── the write path ───────────────────────────────────────────────────

    def write_documents(self, conn, run: QueryRun, *, batch: int = 500) -> dict[str, int]:
        """Insert one `document` per stored issue. Absent values stay NULL.

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
            }
            for issue in run.stored
        ]
        statement = (
            "INSERT INTO document (id, source, external_id, url, created_at, fetched_at, "
            "text_ref, content_hash, engagement, status) "
            "VALUES (%(id)s, %(source)s, %(external_id)s, %(url)s, %(created_at)s, now(), "
            "%(text_ref)s, %(content_hash)s, %(engagement)s, 'kept') "
            "ON CONFLICT (source, external_id) DO NOTHING"
        )
        inserted = 0
        with conn.cursor() as cur:
            for start in range(0, len(rows), batch):
                cur.executemany(statement, rows[start:start + batch])
                inserted += max(0, cur.rowcount)
        return {"inserted": inserted, "seen": len(rows)}

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
