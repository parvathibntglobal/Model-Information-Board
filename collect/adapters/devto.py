"""The dev.to adapter, via the Forem API. Search, sieve, then fetch each article.

THE DOCUMENT UNIT IS THE ARTICLE
--------------------------------
`devto:4589859`. Not the author, not the tag, not the comment thread: an article
is one person's write-up with one byline and one date, which is what makes it a
voice and a claim at the same time. dev.to comments exist and are a separate
endpoint; they are NOT harvested here, and that is a scope decision rather than
an oversight - a comment thread on dev.to would need the same subject-thread
treatment Hacker News gets, and nothing has measured whether dev.to comments
carry evidence.

⚠  THE SEARCH PARAMETER THAT IS SILENTLY IGNORED — MEASURED 2026-09-07
-----------------------------------------------------------------------
`GET /api/articles?q=<anything>` answers **HTTP 200 and ignores `q`**. Measured
directly, three queries against the same endpoint:

    q absent        titles: [My Grandmother Ran Ajo…, The Unbreakable Shopping…, Taming Flutter…]
    q="fable"       titles: [My Grandmother Ran Ajo…, The Unbreakable Shopping…, Taming Flutter…]
    q="kubernetes"  titles: [My Grandmother Ran Ajo…, The Unbreakable Shopping…, Taming Flutter…]

Identical. It is the latest-articles feed wearing a search's clothes, and a
sweep built on it would return the site's front page for every model and report
it as that model's coverage. **This is the same defect class rule 6 records for
GitHub Search discarding a query's qualifiers**, and it is worse here because
the ignored parameter is the whole query rather than a narrowing clause: the
figures would look like a corpus and be a calendar.

So this adapter uses `GET /api/articles/search?q=`, which was verified to filter
- `kubernetes` returns infrastructure posts and `fable` returns Fable posts -
and `SEARCH_PATH` is a module constant with this note beside it so nobody
"simplifies" it back to the endpoint that answers everything.

**THE SEARCH IS STILL LOOSE, AND THE SIEVE IS NOT OPTIONAL.** Of the first five
hits for `Fable 5.1`, two carried the surface in title, description or tags and
three did not - they matched on body text or on a token. Retrieval is broad and
cheap by design (`queries/sieve.py`); precision happens locally. A `candidates`
figure from this platform is a retrieval count and never a mention count (rule
7).

⚠  A ZERO-MATCH QUERY IS UNSTABLE. `q="zzqqxxnonsenseterm"` answered **HTTP
   500** once and **timed out** on the next attempt (n=1 each, 2026-09-07).
   Neither is converted into "no articles": both are counted as http errors and
   the run says so. A 500 read as an empty result set is the failure this
   project keeps finding - and here the platform's own answer to "nothing
   matched" is apparently an error, so the conflation is one line away.

TWO ARTIFACTS, THE SAME SHAPE AS GITHUB'S
-----------------------------------------
    search response      -> raw/   the discovery artifact, one per query page
    /api/articles/{id}   -> raw/   the per-document artifact; `document.text_ref`

The second fetch is not optional and not a nicety: **a search hit carries no
body.** Its keys stop at `description`, a truncated blurb, and `body_markdown`
appears only on the single-article response. So a corpus built from search hits
alone would hold 150-character summaries, and every extraction would run against
a teaser while reporting normally.

RATE, HONESTLY UNREAD
---------------------
Forem publishes rate limits for WRITE endpoints and none for these reads. So
there is no number to budget against, and the interval here is this lane's
default politeness (1 request/second, `collect/limiter.py`) rather than a limit
somebody read. Recorded as unread rather than written down as a figure - the
`"60/min"` that lived in the Reddit notes for weeks with no source is the reason
this sentence exists.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from collect.adapters.documents import DocumentDraft, SweepCounts, WriteReport
from collect.config import settings
from collect.ids import stable_id
from collect.limiter import HostLimiter
from collect.rawstore import RAW, RawStore

log = logging.getLogger(__name__)

SOURCE_ID = "devto"
DOCUMENT_SOURCE = "devto"

BASE_URL = "https://dev.to/api"

#: ⚠ `/articles/search`, NOT `/articles`. See the module docstring: `/articles`
#: accepts `q` and ignores it, answering 200 with the latest-articles feed.
SEARCH_PATH = "/articles/search"
ARTICLE_PATH = "/articles/{id}"

#: Forem's page size for search. 30 is its own default ceiling for this
#: endpoint; asking for more returns 30.
PER_PAGE = 30
DEFAULT_MAX_PAGES = 1

#: No published read limit exists, so this is politeness rather than a budget.
MIN_INTERVAL_SECONDS = 1.0


class DevtoConfigError(RuntimeError):
    """The adapter cannot be built from the current settings."""


@dataclass(frozen=True)
class DevtoHit:
    """One search hit. Carries NO body — `description` is a truncated blurb."""

    article_id: int
    title: str
    description: str
    url: str
    published_at: str | None
    tags: tuple[str, ...]
    #: `user.user_id`, the stable numeric account id. NOT `username`: Forem
    #: allows renames, so a username splits one person across a rename and
    #: merges two if reused - the same reasoning as Reddit's `t2_` and GitHub's
    #: `user.id`.
    author_external_id: str | None
    author_handle: str | None
    #: `language`, the platform's own field. dev.to is the FIRST source in this
    #: corpus that declares one per document - all 6,502 existing rows have
    #: `document.lang` NULL, which is why `triage.gates.wrong_language` reports
    #: UNAVAILABLE for the whole corpus.
    language: str | None
    reactions: int
    comments: int

    @property
    def external_id(self) -> str:
        return str(self.article_id)

    @property
    def sieve_text(self) -> str:
        """What the sieve reads BEFORE the article is fetched.

        ⚠  TITLE + DESCRIPTION + TAGS, WHICH IS NOT THE ARTICLE. Unlike GitHub
        and Reddit, dev.to's search response does not carry the body, so the
        pre-fetch sieve runs on a blurb. A sieve that passes here has seen ~150
        characters of a 12,000-character article.

        The consequence is one-directional and worth stating: a hit REJECTED
        here may carry the surface deep in its body, so this sieve
        under-recalls, and the population it produces is "articles whose blurb
        mentions the surface" rather than "articles that mention the surface".
        `sieve_stored` re-runs the same terms over the fetched body, which is
        the figure that answers the second question.
        """
        return "\n".join(filter(None, (self.title, self.description, " ".join(self.tags))))

    @property
    def engagement(self) -> dict[str, Any]:
        return {"score": self.reactions, "comments": self.comments}


@dataclass(frozen=True)
class StoredArticle:
    """One article whose own payload is in the store."""

    hit: DevtoHit
    ref: str
    content_hash: str
    size: int
    already_present: bool
    #: `body_markdown` from the fetched payload, held for the post-fetch sieve.
    #: NOT stored to the database in place of the payload - prose is derived at
    #: assembly (`collect/assemble/prose.py:devto_article_prose`).
    body: str | None = None

    def draft(self) -> DocumentDraft:
        return DocumentDraft(
            source=DOCUMENT_SOURCE,
            external_id=self.hit.external_id,
            url=self.hit.url,
            text_ref=self.ref,
            content_hash=self.content_hash,
            created_at=self.hit.published_at,
            author_external_id=self.hit.author_external_id,
            author_handle=self.hit.author_handle,
            lang=self.hit.language,
            engagement=self.hit.engagement,
        )


@dataclass
class DevtoRun:
    """One query, what it cost, and what it produced."""

    query: str
    started_at: datetime
    finished_at: datetime | None = None

    pages_fetched: int = 0
    pages_stored: int = 0
    search_calls: int = 0
    fetch_calls: int = 0
    http_errors: int = 0
    #: Requests that timed out rather than answering. Counted separately from
    #: `http_errors` because a timeout on this platform is the observed answer
    #: to a zero-match query, and folding it in would hide that.
    timeouts: int = 0

    discovery_refs: list[str] = field(default_factory=list)
    hits: list[DevtoHit] = field(default_factory=list)
    verdicts: list[Any] = field(default_factory=list)
    survivors: list[DevtoHit] = field(default_factory=list)
    stored: list[StoredArticle] = field(default_factory=list)

    #: Of the STORED articles, how many carry the terms in their fetched body.
    #: None until `sieve_stored` runs - never 0, which would claim a measurement
    #: (rule 6).
    body_sieve_kept: int | None = None

    #: dev.to reports NO total for a search. None on every run, recorded as a
    #: fact about the platform rather than written as 0.
    total_count: int | None = None

    exhausted: bool = False
    truncated_by: str | None = None

    @property
    def items_fetched(self) -> int:
        return len(self.hits)

    @property
    def items_kept(self) -> int:
        return len(self.stored)

    def harvest_run_fields(self) -> dict[str, Any]:
        return {
            "id": stable_id("hr", SOURCE_ID, self.query, self.started_at.isoformat()),
            "source_id": SOURCE_ID,
            "query_key": f"search:{self.query} per_page:{PER_PAGE}",
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "items_fetched": self.items_fetched,
            "items_kept": self.items_kept,
            "http_errors": self.http_errors + self.timeouts,
            # NULL, not false: dev.to reports no total, so whether more results
            # exist is unknown rather than known to be true.
            "exhausted": True if self.exhausted else None,
            "truncated_by": self.truncated_by,
            "pipeline_version": settings().pipeline_version,
            "pages_fetched": self.pages_fetched,
            "pages_stored": self.pages_stored,
        }


class DevtoHarvester:
    """Search, store the page, sieve the blurbs, then fetch each survivor."""

    def __init__(
        self,
        *,
        client: httpx.Client,
        store: RawStore,
        limiter: HostLimiter | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
        per_page: int = PER_PAGE,
        clock=lambda: datetime.now(UTC),
        sleeper=time.sleep,
    ) -> None:
        self._client = client
        self._store = store
        self._limiter = (
            HostLimiter(min_interval=MIN_INTERVAL_SECONDS) if limiter is None else limiter
        )
        self._max_pages = max_pages
        self._per_page = per_page
        self._clock = clock
        self._sleep = sleeper

    def _get(self, path: str, params: dict[str, Any] | None, run: DevtoRun):
        """One request. None on a timeout or a non-200, both counted.

        The timeout branch is separate on purpose - see the module docstring: a
        zero-match query on this platform answers 500 or hangs, and a caller
        that turned either into an empty list would publish "no articles
        mention this model" on the strength of a transport failure.
        """
        url = f"{BASE_URL}{path}"
        self._limiter.wait(url)
        try:
            response = self._client.get(url, params=params)
        except httpx.TimeoutException:
            run.timeouts += 1
            log.warning("devto: timed out on %s %r", path, params)
            return None
        except httpx.HTTPError as error:
            run.http_errors += 1
            log.error("devto: request failed on %s %r: %s", path, params, error)
            return None
        if response.status_code != 200:
            run.http_errors += 1
            log.warning(
                "devto: HTTP %s on %s %r. NOT an empty result set - a zero-match "
                "query on this platform has been observed to answer 500.",
                response.status_code, path, params,
            )
            return None
        return response

    def search(self, query: str, *, run: DevtoRun | None = None) -> DevtoRun:
        """Issue the query, storing each page before anything is sieved."""
        run = run if run is not None else DevtoRun(query=query, started_at=self._clock())

        for page in range(1, self._max_pages + 1):
            params = {"q": query, "per_page": self._per_page, "page": page}
            response = self._get(SEARCH_PATH, params, run)
            run.search_calls += 1
            run.pages_fetched = page
            if response is None:
                run.truncated_by = run.truncated_by or "rate-limit"
                break

            try:
                payload = response.json()
            except ValueError:
                run.http_errors += 1
                log.error("devto: search response for %r is not JSON", query)
                break
            if not isinstance(payload, list):
                run.http_errors += 1
                log.error(
                    "devto: search response for %r is %s, not a list of articles",
                    query, type(payload).__name__,
                )
                break

            # Stored BEFORE the sieve, so a rejected hit's blurb survives and a
            # re-sieve is possible over what this run actually saw.
            stored = self._store.put(response.content, namespace=RAW)
            run.discovery_refs.append(stored.ref)
            run.pages_stored += 1

            run.hits.extend(_hit_of(item) for item in payload if isinstance(item, dict))
            if len(payload) < self._per_page:
                run.exhausted = True
                break
        else:
            run.truncated_by = run.truncated_by or "query-budget"

        run.finished_at = self._clock()
        return run

    def sieve_run(self, run: DevtoRun, terms) -> DevtoRun:
        """Apply the terms to the search BLURBS. Under-recalls; see `sieve_text`."""
        from collect.adapters.queries.sieve import sieve

        for hit in run.hits:
            verdict = sieve(terms, hit.sieve_text)
            run.verdicts.append(verdict)
            if verdict.passed:
                run.survivors.append(hit)
        return run

    def sieve_stored(self, run: DevtoRun, terms) -> DevtoRun:
        """Re-run the terms over the FETCHED bodies. The figure that answers
        "how many of these articles actually mention it".

        Separate from `sieve_run` and reported separately, because the two have
        different denominators: one is over blurbs and one is over full text.
        Quoting the first as though it were the second is rule 7's failure.
        """
        from collect.adapters.queries.sieve import sieve

        kept = 0
        for article in run.stored:
            if article.body and sieve(terms, article.body).passed:
                kept += 1
        run.body_sieve_kept = kept
        return run

    def fetch_article(self, hit: DevtoHit, run: DevtoRun) -> StoredArticle | None:
        """Fetch one article — the per-document artifact `text_ref` names.

        This is where `body_markdown` comes from. A search hit has none, so
        skipping this call would leave the corpus holding blurbs.
        """
        response = self._get(ARTICLE_PATH.format(id=hit.article_id), None, run)
        run.fetch_calls += 1
        if response is None:
            return None
        stored = self._store.put(response.content, namespace=RAW)
        body = None
        try:
            body = (response.json() or {}).get("body_markdown")
        except ValueError:
            # The payload is stored either way. A body we cannot parse is a
            # parse problem to solve against local bytes, not a re-fetch.
            log.warning("devto: article %s payload is not JSON", hit.article_id)
        return StoredArticle(
            hit=hit,
            ref=stored.ref,
            content_hash=stored.content_hash,
            size=stored.size,
            already_present=stored.already_present,
            body=body,
        )

    def harvest(self, query: str, terms=None, *, run: DevtoRun | None = None,
                max_fetch: int | None = None) -> DevtoRun:
        """One query, end to end. Only sieve survivors cost an article request."""
        run = self.search(query, run=run)
        if terms is not None:
            self.sieve_run(run, terms)
            survivors = run.survivors
        else:
            survivors = list(run.hits)

        if max_fetch is not None and len(survivors) > max_fetch:
            log.warning("devto: %d survivors, fetching %d", len(survivors), max_fetch)
            run.truncated_by = run.truncated_by or "query-budget"
            survivors = survivors[:max_fetch]

        for hit in survivors:
            stored = self.fetch_article(hit, run)
            if stored is not None:
                run.stored.append(stored)
        if terms is not None:
            self.sieve_stored(run, terms)
        run.finished_at = self._clock()
        return run

    def write_documents(
        self,
        conn,
        run: DevtoRun,
        *,
        retrieval_provenance: str,
        harvest_run_id: str | None = None,
        batch: int = 500,
    ) -> WriteReport:
        from collect.adapters.documents import write_documents as write

        return write(
            conn,
            [s.draft() for s in run.stored],
            retrieval_provenance=retrieval_provenance,
            harvest_run_id=harvest_run_id,
            batch=batch,
        )

    def counts(self, run: DevtoRun) -> SweepCounts:
        notes = [
            "candidates are RETRIEVAL hits from a loose full-text search, not "
            "mentions — the sieve is what counts mentions",
        ]
        if run.timeouts:
            notes.append(
                f"{run.timeouts} request(s) timed out and are NOT counted as zero "
                "results"
            )
        if run.body_sieve_kept is not None:
            notes.append(
                f"{run.body_sieve_kept} of {run.items_kept} fetched bodies carry "
                "the terms"
            )
        return SweepCounts(
            platform=SOURCE_ID,
            requests_issued=run.search_calls + run.fetch_calls,
            candidates=run.items_fetched,
            stored=run.items_kept,
            http_errors=run.http_errors + run.timeouts,
            notes=notes,
        )


def _hit_of(item: dict[str, Any]) -> DevtoHit:
    user = item.get("user") or {}
    user_id = user.get("user_id")
    return DevtoHit(
        article_id=int(item.get("id") or 0),
        title=item.get("title") or "",
        description=item.get("description") or "",
        url=item.get("url") or "",
        published_at=item.get("published_at") or item.get("published_timestamp"),
        tags=tuple(item.get("tag_list") or ()),
        # None for a payload with no user, which stays absent rather than
        # becoming a shared sentinel (rule 6).
        author_external_id=str(user_id) if user_id is not None else None,
        author_handle=user.get("username"),
        language=item.get("language"),
        reactions=int(item.get("public_reactions_count") or 0),
        comments=int(item.get("comments_count") or 0),
    )


def devto_document_id(external_id: str) -> str:
    """`document.id` for a dev.to article. Delegates to the shared convention."""
    from collect.adapters.documents import document_id

    return document_id(DOCUMENT_SOURCE, external_id)


# ── the gated entry point ────────────────────────────────────────────────


def observe_devto_use() -> dict[str, object]:
    """This run's live observations for the terms gate.

    Two facts a run can re-verify about itself: it goes through the Forem API
    rather than dev.to's HTML, and it uses the SEARCH endpoint rather than the
    latest-articles endpoint that ignores `q`. The second is here rather than
    only in a docstring because it is the difference between a corpus and a
    calendar, and a live precondition is re-read every run.
    """
    return {"access_path": "api", "search_endpoint": SEARCH_PATH}


def harvester_for_source(source, *, rulings=None, **kwargs) -> DevtoHarvester:
    """Build a harvester for a `source` row, ToS gate included.

    ⚠  IT WILL REFUSE UNTIL A RULING EXISTS. `contract/sources.yaml` carries no
       `devto` source row as of 2026-09-07; the draft is proposed in
       `docs/proposals/for-engineer-2-five-new-platform-sources.md`.
    """
    from collect.registry.assertions import assert_terms_reviewed, source_field

    source_id = source_field(source, "id", "?")
    assert_terms_reviewed(
        [source],
        rulings=rulings,
        observations={source_id: observe_devto_use()},
    )
    return DevtoHarvester(**kwargs)
