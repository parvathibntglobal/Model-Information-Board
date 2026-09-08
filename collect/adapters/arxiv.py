"""The arXiv adapter. Search the Atom API, sieve, then fetch each paper by id.

THE DOCUMENT UNIT IS ONE PAPER'S ABSTRACT ENTRY, VERSIONED
-----------------------------------------------------------
`arxiv:2609.03450v1`. The version is part of the id and not stripped, because a
v2 is a different text: the abstract is what this platform contributes, and an
author who revises it after a reviewer's comment has published a second
document. Stripping the version would make an edit overwrite the evidence it
replaced, and `document` is append-only with `ON CONFLICT DO NOTHING`, so the
first version would silently win forever.

**A PAPER IS NOT AN ENGINEER'S REPORT, AND THE CORPUS SHOULD SAY SO.** The
sweep already run for the Articles page measured it: for one model, the phrase
appeared in **0 of 43 titles** and every mention was inside an abstract, as a
model *evaluated, benchmarked, or used as a baseline or judge*. That is a
third-party measurement of someone else's model, not `own-experience`, and
`judge/vet/weight.py` tiers on exactly that distinction. So this platform is
expected to produce third-party evidence, and a weighting that treated an
abstract as a practitioner report would over-credit it. Recorded here because
the adapter is where somebody will be standing when they wonder why arXiv
claims weigh little.

TWO ARTIFACTS, THE SAME SHAPE AS GITHUB'S
-----------------------------------------
    search feed   -> raw/   the discovery artifact, one per query page
    id_list feed  -> raw/   the per-document artifact; `document.text_ref`

`text_ref` names the single-entry feed for ONE paper and never the search page:
one search response covers a hundred entries, so pointing `text_ref` at it
would stop `content_hash` identifying one document - breaking dedupe and NFR-6
the same way it would for a feed. That is `github.py`'s argument, unchanged.

The second fetch is a real request and it is not free (see the rate note), so
the alternative was considered and rejected: slicing the `<entry>` element out
of the search feed and hashing that. It would halve the requests and it would
make `content_hash` the hash of bytes WE assembled rather than bytes the
platform sent, which is the ruling this project already had to repair twice
(`docs/engineer-1/ruling-what-content-hash-identifies.md`). One request per
kept paper is the price of the hash meaning what it says.

RATE, AS ARXIV STATES IT
------------------------
arXiv's API Terms of Use ask for **no more than one request every three
seconds** and a single connection at a time. That is a published number rather
than an observed one, so it is honoured as given: `MIN_INTERVAL_SECONDS = 3.0`,
one sequential pass, identifying User-Agent through `collect.http.build_client`.

⚠  HTTP, NOT HTTPS, IS A 301 AND AN EMPTY BODY. Measured 2026-09-07:
   `http://export.arxiv.org/api/query` returns `301` with `len=0` and no
   redirect is followed by default, so the run reads as an empty result set.
   The base URL here is https for that reason. The failure mode is the one this
   project keeps recording - a transport answer read as a statement about the
   corpus - so `_get` counts a non-200 as an http error and never as zero hits.

XML, PARSED WITH THE STANDARD LIBRARY
-------------------------------------
`xml.etree.ElementTree`, not `feedparser`: `tests/test_lane_boundary.py` allows
exactly one importer of `feedparser` (`adapters/blog/parse.py`) because that
library fetches as well as parses, and arXiv's Atom is a search response rather
than a blog feed - routing it through the blog parser would couple two unrelated
shapes to reuse an entry mapper that does not fit.

ElementTree does not resolve external entities, so the remaining XML risk is an
expansion bomb from a compromised arXiv. Responses are bounded by
`MAX_RESULTS_PER_PAGE` and read as a whole into memory by httpx before parsing;
that is the bound, and it is stated rather than assumed.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from xml.etree import ElementTree

import httpx

from collect.adapters.basis import observe_use_basis
from collect.adapters.documents import DocumentDraft, SweepCounts, WriteReport
from collect.config import settings
from collect.ids import stable_id
from collect.limiter import HostLimiter
from collect.rawstore import RAW, RawStore

log = logging.getLogger(__name__)

SOURCE_ID = "arxiv"
DOCUMENT_SOURCE = "arxiv"

BASE_URL = "https://export.arxiv.org/api/query"

#: arXiv's published API Terms of Use. Not measured by us - it is a stated
#: limit, and a stated limit is honoured rather than probed.
MIN_INTERVAL_SECONDS = 3.0

#: Their guidance is to page in slices of 2,000 at most and to prefer small
#: pages. 50 keeps one response small enough to parse and hash cheaply and is
#: far below anything they object to.
MAX_RESULTS_PER_PAGE = 50
DEFAULT_MAX_PAGES = 1

_ATOM = "{http://www.w3.org/2005/Atom}"
_OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"
_ARXIV = "{http://arxiv.org/schemas/atom}"

#: arXiv answers a malformed query with HTTP 200 and a feed holding one entry
#: whose title is exactly this. Counted as a refused query rather than as a
#: document, because storing it would put an error message in the corpus.
ERROR_ENTRY_TITLE = "Error"


class ArxivConfigError(RuntimeError):
    """The adapter cannot be built from the current settings."""


@dataclass(frozen=True)
class ArxivPaper:
    """One `<entry>`, flattened out of the Atom envelope.

    `raw` is not kept. The entry's bytes are re-fetched by id for the
    per-document artifact, so holding a parsed copy here would invite somebody
    to store it - which is the artifact choice this module rejects in its
    docstring.
    """

    #: `2609.03450v1` — the versioned arXiv id, which is the external id.
    external_id: str
    abs_url: str
    title: str
    summary: str
    published: str | None
    updated: str | None
    #: Author names in order. arXiv publishes NO stable author identifier, so
    #: these are names and nothing more - see `author_external_id` below.
    authors: tuple[str, ...]
    primary_category: str | None
    comment: str | None

    @property
    def sieve_text(self) -> str:
        """What the sieve reads: title and abstract.

        The same gift a full-text feed gives the blog adapter - the abstract
        arrives in the search response, so the sieve runs before the per-paper
        request rather than after it.
        """
        return f"{self.title}\n{self.summary}"

    @property
    def author_external_id(self) -> None:
        """Always None. arXiv publishes no stable author id, and that is a fact.

        A name is not an identity here for the two reasons this repository
        already recorded: `vickiboykis.com`-style renames split one person, and
        a reused name merges two - and over-clustering is the worse of the two
        failures (`collect/CLAUDE.md`). arXiv makes it worse than Reddit's
        username case, because a paper has MANY authors and the corpus question
        is which of them wrote the sentence being quoted, which no arXiv field
        answers.

        So every arXiv document is `unattributable` and is counted as such.
        That is not a small consequence: `judge/curate/gate.py` dedups voices
        off `claim.author_id` and a NULL is no voice, so arXiv can corroborate
        the PLATFORM half of the publication gate and never the VOICE half.
        Stated as a property rather than left to be discovered from a count of
        zero authors.
        """
        return None

    @property
    def engagement(self) -> dict[str, Any]:
        """arXiv publishes no engagement signal at all.

        `{}` would read as "measured, and every figure is zero"; the keys are
        present with None values so a reader of `document.engagement` sees that
        this platform HAS no score rather than that this paper scored nothing
        (rule 6). E3's ranking is `specificity x log(1 + engagement)`, and an
        arXiv document must not sort last because a platform has no votes.
        """
        return {"score": None, "comments": None, "citations": None}


@dataclass
class ArxivRun:
    """One query, what it cost, and what it produced."""

    query: str
    started_at: datetime
    finished_at: datetime | None = None

    pages_fetched: int = 0
    pages_stored: int = 0
    search_calls: int = 0
    fetch_calls: int = 0
    http_errors: int = 0

    discovery_refs: list[str] = field(default_factory=list)
    papers: list[ArxivPaper] = field(default_factory=list)
    verdicts: list[Any] = field(default_factory=list)
    survivors: list[ArxivPaper] = field(default_factory=list)
    stored: list[StoredPaper] = field(default_factory=list)

    #: `opensearch:totalResults`, verbatim. arXiv DOES report a total, unlike
    #: Reddit - so None here means the response did not carry one, never zero.
    total_results: int | None = None

    #: The query was refused by arXiv (the `Error` entry). Distinct from
    #: `total_results == 0`, which is the platform saying nothing matched.
    query_refused: bool = False
    refusal_detail: str | None = None

    exhausted: bool = False
    truncated_by: str | None = None

    @property
    def items_fetched(self) -> int:
        return len(self.papers)

    @property
    def items_kept(self) -> int:
        return len(self.stored)

    def harvest_run_fields(self) -> dict[str, Any]:
        """The `harvest_run` row this run would write.

        `query_key` carries the WHOLE denominator - the rendered arXiv query
        string - so the row says what population it drew from without anybody
        reconstructing it (rule 7).
        """
        return {
            "id": stable_id("hr", SOURCE_ID, self.query, self.started_at.isoformat()),
            "source_id": SOURCE_ID,
            "query_key": self.query,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "items_fetched": self.items_fetched,
            "items_kept": self.items_kept,
            "http_errors": self.http_errors,
            "exhausted": (
                None
                if self.total_results is None
                else self.total_results <= self.items_fetched
            ),
            "truncated_by": self.truncated_by,
            "pipeline_version": settings().pipeline_version,
            # ── homeless, pending #5 ──
            "pages_fetched": self.pages_fetched,
            "pages_stored": self.pages_stored,
        }


@dataclass(frozen=True)
class StoredPaper:
    """One paper whose own single-entry feed is in the store."""

    paper: ArxivPaper
    ref: str
    content_hash: str
    size: int
    already_present: bool

    def draft(self) -> DocumentDraft:
        return DocumentDraft(
            source=DOCUMENT_SOURCE,
            external_id=self.paper.external_id,
            url=self.paper.abs_url,
            text_ref=self.ref,
            content_hash=self.content_hash,
            created_at=self.paper.published,
            author_external_id=None,
            author_handle=None,
            # arXiv's Atom carries no per-entry language. NULL, not "en":
            # nearly every paper is in English and "nearly every" is not a
            # value to write into a column a gate reads.
            lang=None,
            engagement=self.paper.engagement,
        )


class ArxivHarvester:
    """Search, store the page, sieve it, then fetch each survivor by id.

    THE ORDER IS GITHUB'S AND REDDIT'S: search, **sieve, fetch**. The search
    response already carries every entry's title and abstract, so the sieve runs
    on what search returned and only survivors cost a second request - which
    matters more here than anywhere else in this lane, because the second
    request is rate-limited to one per three seconds.

    The page is written to `raw/` BEFORE the sieve, so a rejected paper's
    abstract is still on disk and a window that turns out too tight is fixed by
    re-sieving rather than re-searching.
    """

    def __init__(
        self,
        *,
        client: httpx.Client,
        store: RawStore,
        limiter: HostLimiter | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
        page_size: int = MAX_RESULTS_PER_PAGE,
        clock=lambda: datetime.now(UTC),
        sleeper=time.sleep,
    ) -> None:
        self._client = client
        self._store = store
        self._limiter = (
            HostLimiter(min_interval=MIN_INTERVAL_SECONDS) if limiter is None else limiter
        )
        self._max_pages = max_pages
        self._page_size = min(page_size, MAX_RESULTS_PER_PAGE)
        self._clock = clock
        self._sleep = sleeper

    # ── one request ──────────────────────────────────────────────────────

    def _get(self, params: dict[str, Any], run: ArxivRun) -> httpx.Response | None:
        """One request, rate-limited. None on anything that is not a 200.

        A non-200 is counted and returns None. The caller must not read that as
        an empty result set: a 301 from the http scheme returns a zero-length
        body, and reading it as "no papers" is the transport answer becoming a
        statement about the corpus.
        """
        self._limiter.wait(BASE_URL)
        try:
            response = self._client.get(BASE_URL, params=params)
        except httpx.HTTPError as error:
            run.http_errors += 1
            log.error("arxiv: request failed for %r: %s", params, error)
            return None
        if response.status_code != 200:
            run.http_errors += 1
            log.warning("arxiv: HTTP %s on %r", response.status_code, params)
            return None
        return response

    # ── search ───────────────────────────────────────────────────────────

    def search(self, query: str, *, run: ArxivRun | None = None) -> ArxivRun:
        """Issue the query, store each page before anything is sieved.

        `query` is an arXiv `search_query` expression, e.g.
        `all:"Fable 5.1"`. It is passed through verbatim rather than assembled
        here: arXiv's field prefixes and its quoting rules are the platform's
        syntax, and a helper that built them would be a second place where a
        query means something.

        `run` may be supplied so a caller can open the `harvest_run` row BEFORE
        the fetch - the two-phase ledger property `github.harvest` documents: a
        process that dies cannot write its own failure, so the row has to exist
        first.
        """
        run = run if run is not None else ArxivRun(query=query, started_at=self._clock())

        for page in range(self._max_pages):
            params = {
                "search_query": query,
                "start": page * self._page_size,
                "max_results": self._page_size,
                # Newest first. The board is about what is being said now, and
                # `contract/harvest.yaml`'s recency decay reads `created_at`.
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            response = self._get(params, run)
            run.search_calls += 1
            run.pages_fetched = page + 1
            if response is None:
                run.truncated_by = run.truncated_by or "rate-limit"
                break

            feed = _parse_feed(response.content)
            if feed is None:
                run.http_errors += 1
                log.error("arxiv: response for %r is not parseable Atom", query)
                break

            refusal = _error_entry(feed)
            if refusal is not None:
                # arXiv said no. NOT stored and NOT counted as a document: an
                # error message in the corpus is a document nobody wrote.
                run.query_refused = True
                run.refusal_detail = refusal
                log.warning("arxiv: refused %r — %s", query, refusal)
                break

            stored = self._store.put(response.content, namespace=RAW)
            run.discovery_refs.append(stored.ref)
            run.pages_stored += 1

            total = feed.findtext(f"{_OPENSEARCH}totalResults")
            if total is not None and total.strip().isdigit():
                run.total_results = int(total.strip())

            entries = feed.findall(f"{_ATOM}entry")
            run.papers.extend(_paper_of(entry) for entry in entries)

            if len(entries) < self._page_size:
                run.exhausted = True
                break
        else:
            if run.total_results is not None and run.total_results > run.items_fetched:
                # OUR page budget stopped us, not the platform. Different
                # statement, different repair.
                run.truncated_by = "query-budget"

        run.finished_at = self._clock()
        return run

    def sieve_run(self, run: ArxivRun, terms) -> ArxivRun:
        """Apply a rendered term set to what search returned. No fetching."""
        from collect.adapters.queries.sieve import sieve

        for paper in run.papers:
            verdict = sieve(terms, paper.sieve_text)
            run.verdicts.append(verdict)
            if verdict.passed:
                run.survivors.append(paper)
        return run

    # ── the per-document artifact ────────────────────────────────────────

    def fetch_paper(self, paper: ArxivPaper, run: ArxivRun) -> StoredPaper | None:
        """Fetch one paper's own single-entry feed — what `text_ref` names.

        `id_list` rather than a `search_query`, so the response is exactly this
        paper and the bytes stored are the platform's answer about one document.
        """
        response = self._get({"id_list": paper.external_id}, run)
        run.fetch_calls += 1
        if response is None:
            return None
        stored = self._store.put(response.content, namespace=RAW)
        return StoredPaper(
            paper=paper,
            ref=stored.ref,
            content_hash=stored.content_hash,
            size=stored.size,
            already_present=stored.already_present,
        )

    def harvest(self, query: str, terms=None, *, run: ArxivRun | None = None,
                max_fetch: int | None = None) -> ArxivRun:
        """One query, end to end. Only sieve survivors cost a second request."""
        run = self.search(query, run=run)
        if terms is not None:
            self.sieve_run(run, terms)
            survivors = run.survivors
        else:
            # NO SIEVE IS NOT AN EMPTY SIEVE. A caller with no rendered terms
            # keeps every candidate, and the run's `verdicts` stays empty so
            # `sieve_pass_rate` is absent rather than 1.0 (rule 6).
            survivors = list(run.papers)

        if max_fetch is not None and len(survivors) > max_fetch:
            log.warning("arxiv: %d survivors, fetching %d", len(survivors), max_fetch)
            run.truncated_by = run.truncated_by or "query-budget"
            survivors = survivors[:max_fetch]

        for paper in survivors:
            stored = self.fetch_paper(paper, run)
            if stored is not None:
                run.stored.append(stored)
        run.finished_at = self._clock()
        return run

    # ── the write path ───────────────────────────────────────────────────

    def write_documents(
        self,
        conn,
        run: ArxivRun,
        *,
        retrieval_provenance: str,
        harvest_run_id: str | None = None,
        batch: int = 500,
    ) -> WriteReport:
        """One `document` per stored paper, through the shared writer."""
        from collect.adapters.documents import write_documents as write

        return write(
            conn,
            [s.draft() for s in run.stored],
            retrieval_provenance=retrieval_provenance,
            harvest_run_id=harvest_run_id,
            batch=batch,
        )

    def counts(self, run: ArxivRun) -> SweepCounts:
        """The four figures the test-run report needs, from one run."""
        notes = []
        if run.query_refused:
            notes.append(f"arXiv refused the query: {run.refusal_detail}")
        if run.total_results is not None:
            notes.append(f"opensearch:totalResults = {run.total_results}")
        return SweepCounts(
            platform=SOURCE_ID,
            requests_issued=run.search_calls + run.fetch_calls,
            candidates=run.items_fetched,
            stored=run.items_kept,
            http_errors=run.http_errors,
            notes=notes,
        )


# ── parsing ──────────────────────────────────────────────────────────────


def _parse_feed(payload: bytes) -> ElementTree.Element | None:
    try:
        return ElementTree.fromstring(payload)
    except ElementTree.ParseError:
        return None


def _error_entry(feed: ElementTree.Element) -> str | None:
    """arXiv's own refusal, or None. HTTP 200 with an `Error` entry.

    A malformed `search_query` answers 200 and a feed with one entry titled
    `Error`, whose summary is the message. Read as a document, that entry
    becomes a corpus row saying "incorrect id format"; read as an empty feed, a
    refused query reads as a query with no matches. Neither is true, so it is
    named.
    """
    entries = feed.findall(f"{_ATOM}entry")
    if len(entries) != 1:
        return None
    title = (entries[0].findtext(f"{_ATOM}title") or "").strip()
    if title != ERROR_ENTRY_TITLE:
        return None
    return (entries[0].findtext(f"{_ATOM}summary") or "").strip() or "no detail given"


def arxiv_id_of(abs_url: str) -> str:
    """`http://arxiv.org/abs/2609.03450v1` -> `2609.03450v1`.

    The version suffix is KEPT. See the module docstring: a v2 abstract is a
    different document, and `ON CONFLICT DO NOTHING` would let the first
    version win forever if the two shared an id.
    """
    return abs_url.rstrip("/").rsplit("/", 1)[-1]


def _paper_of(entry: ElementTree.Element) -> ArxivPaper:
    abs_url = (entry.findtext(f"{_ATOM}id") or "").strip()
    authors = tuple(
        (name.text or "").strip()
        for name in entry.findall(f"{_ATOM}author/{_ATOM}name")
        if (name.text or "").strip()
    )
    primary = entry.find(f"{_ARXIV}primary_category")
    return ArxivPaper(
        external_id=arxiv_id_of(abs_url),
        # https, so the stored url is the one a reader can open. arXiv's own
        # `<id>` is http and redirects.
        abs_url=abs_url.replace("http://arxiv.org/", "https://arxiv.org/"),
        title=" ".join((entry.findtext(f"{_ATOM}title") or "").split()),
        summary=(entry.findtext(f"{_ATOM}summary") or "").strip(),
        published=(entry.findtext(f"{_ATOM}published") or "").strip() or None,
        updated=(entry.findtext(f"{_ATOM}updated") or "").strip() or None,
        authors=authors,
        primary_category=primary.get("term") if primary is not None else None,
        comment=(entry.findtext(f"{_ARXIV}comment") or "").strip() or None,
    )


# ── the gated entry point ────────────────────────────────────────────────


def observe_arxiv_use() -> dict[str, object]:
    """This run's live observations for the terms gate. TWO facts since the ruling.

    `access_path` is the one fact a run can re-verify about itself: everything
    here goes through the Atom API and never through arxiv.org's HTML. That is
    the same observation `scripts/harvest_github.py` supplies for GitHub, and it
    is the precondition the API terms turn on - arXiv's own terms distinguish
    API access from crawling the site.

    `use_basis` ARRIVED WITH THE RULING ON 2026-09-08. `arxiv-api-terms` rests
    on `internal-development-only`, and `TermsRuling.basis` requires a named
    basis to also be a live precondition "so the fuse is checked rather than
    remembered" - so the ruling stops applying when the deployment stops being
    internal rather than when somebody remembers to revisit it. Shared with the
    Reddit and X paths through `collect/adapters/basis.py` rather than
    reimplemented, because three copies of one check drift.

    ⚠  THE BASIS OBSERVATION IS A PROXY FOR `ENVIRONMENT` AND OBSERVES NOTHING
       ABOUT PUBLICATION, which is the condition the ruling actually turns on.
       `contract/sources.yaml`'s ENFORCEMENT block states that gap rather than
       letting this precondition imply a guard that does not exist.
    """
    return {"access_path": "api", **observe_use_basis()}


def harvester_for_source(source, *, rulings=None, **kwargs) -> ArxivHarvester:
    """Build a harvester for a `source` row, ToS gate included.

    THE ENTRY POINT ANYTHING THAT FETCHES ARXIV MUST USE, for the reason
    `reddit.harvester_for_source` records: this lane once had no such entry
    point on the Reddit path, and a 1,297-post corpus was gathered without the
    gate ever being asked - the gate was working correctly and refusing Reddit
    the whole time, and nothing consulted it.

    ⚠  THE RULING EXISTS SINCE 2026-09-08 AND IT IS A CONDITION, NOT A
       CLEARANCE. `contract/sources.yaml` carries an `arxiv` source row and
       `arxiv-api-terms`, ratified on an internal-development-only basis. What
       it rests on is that NOTHING IS PUBLISHED EXTERNALLY - a quote shown with
       a link to somebody outside the team - and what it explicitly does NOT
       settle is the robots question: `export.arxiv.org` still answers
       `Disallow: /` on the host serving the documented API, no arXiv terms
       document has been read, and both facts are recorded in the ruling rather
       than resolved by it.

       So this no longer raises for want of a ruling; it raises when a live
       precondition fails - `access_path` and `use_basis`. Read
       `contract/sources.yaml`'s ENFORCEMENT block before treating a passing
       gate as an all-clear: it says, in as many words, that nothing in the
       pipeline would notice if the publication condition were breached.

    The gate fires here and not in `__init__`, so the mechanics stay testable
    against recorded fixtures without a test fabricating a reviewed source row -
    **a fixture that fakes a ruling is worse than no gate, because it reads as
    one**.
    """
    from collect.registry.assertions import assert_terms_reviewed, source_field

    source_id = source_field(source, "id", "?")
    assert_terms_reviewed(
        [source],
        rulings=rulings,
        observations={source_id: observe_arxiv_use()},
    )
    return ArxivHarvester(**kwargs)
