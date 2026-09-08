"""The Hacker News adapter, via the Algolia HN Search API.

THE DOCUMENT UNIT IS THE COMMENT INSIDE A SUBJECT THREAD, NOT THE STORY
------------------------------------------------------------------------
`hackernews:49593453` is a comment. This is the decision that decides what the
corpus can answer, and it is not a detail that surfaces later - a story-only
harvest builds a corpus of *links people submitted* and calls it a corpus of
*what engineers report*.

The measurement is already in this repository. `scripts/fetch_hackernews_
articles.py` recorded it for one model: the busiest thread was **a bare GitHub
link at 678 points whose evidence - a quoted price, the pricing URL, an expiry
date, a routing claim - was entirely in its comments**. A story-only fetch
returns the link and loses the argument.

So: search comments, and pull each comment's SUBJECT STORY as its thread root.

    document (comment)    the evidence. status='kept', one per Algolia hit.
    document (story)      the SUBJECT ANCHOR. Written so `thread_root_id` and
                          `parent_id` resolve to rows rather than to dangling
                          ids, exactly as `github.write_comments` writes the
                          issue body and links its comments to it.

**Stories are counted separately from comments in every report.** They are
context rather than retrieved evidence: nothing sieved them, they were not
returned by the query, and pooling them into a "documents stored" figure would
inflate it with rows the query never found (rule 7).

`thread_root_id` IS LOAD-BEARING, RULED 2026-09-08
---------------------------------------------------
It was an open question whether this linkage was load-bearing or decorative,
and the answer is load-bearing: the subject gate may now read the thread root's
text on platforms that put the subject line in a separate record, which today
is this platform alone. `collect/triage/gates.py:Document.thread_subject_text`
carries it, and that module's docstring holds the argument and the 11-of-511
measurement behind it.

AND THE JOIN EXISTS, AS OF 2026-09-08. `collect/triage/run.py` reads the story
row this adapter writes, through `thread_root_id` to that row's `text_ref` to
the raw store to `hackernews_prose`. The root therefore needs NO extra column
and this adapter stores nothing new for it; `collect/ops/chain.py` carries
`Stage("triage", run=_triage_stage)`.

⚠  NO HACKER NEWS DOCUMENT IS STORED ON STAGING, so the join has never run on a
   real HN corpus. The 2026-09-07 smoke run wrote to the disposable local
   instance and that has since been reset; staging holds github 3,382, reddit
   2,999, blog 121 and zero hackernews. The join is proven by
   `tests/test_triage_stored.py` against a real database on rows that file
   inserts, and the first HN sweep is what will produce a survival figure for
   this platform. Saying which of the two is true matters, because "the join
   works" and "the join has run on this platform's corpus" are different claims
   and only the first is established.

⚠  `nbHits` IS NOT A MATCH COUNT, AND IT IS OFF BY A LOT
---------------------------------------------------------
Algolia prefix-matches every token, so `Fable 5.1` is matched as
`fable` + `5` + `.` + `1` - the API's own `_highlightResult` names those four
matched words. Measured 2026-09-07: `nbHits` for that query is **1,062**
comments, and the surface appears verbatim in a small fraction of them.

`run.total_hits` therefore carries the platform's number labelled as a
RETRIEVAL total, and the sieve produces the mention count. A report quoting
1,062 as "1,062 people discussed Fable 5.1" would be the exact failure rule 7
describes: a real value silently answering a question it was not asked.

⚠  PAGINATION IS CAPPED AT 1,000 HITS AND THE API DOES NOT SAY SO
------------------------------------------------------------------
`paginationLimitedTo` is 1,000 for this index. A query with `nbHits` of 2,016
still reports the pages it will serve and hands back 1,000 records **with no
error** - so exhaustion and truncation look identical from the response. Any
query whose `nbHits` exceeds `HITS_CAP` sets
`harvest_run.truncated_by = 'result-ceiling'`, which is the "the platform
stopped us" half of that column rather than the "we chose to stop" half.

Bisecting the window by `created_at_i` is how the standalone script got under
the cap. It is deliberately NOT done here: it multiplies requests and it is
only needed for a full-corpus sweep, which this adapter does not yet drive.
The ceiling is recorded so the next person sees it before they trust a total.

TWO ARTIFACTS, AND THE SECOND ONE IS PER COMMENT
------------------------------------------------
    search response        -> raw/   the discovery artifact, one per query page
    /items/{objectID}      -> raw/   the per-document artifact; `text_ref`

`text_ref` names the item endpoint's response for ONE comment. The alternative
- re-serialising the Algolia hit - was rejected: `content_hash` would then
fingerprint bytes we assembled rather than bytes the platform sent
(`docs/engineer-1/ruling-what-content-hash-identifies.md`). Hugging Face has no
per-comment endpoint and has to re-serialise; Hacker News has one, so it uses
it.

The extra request is free in the sense that matters: the Algolia API is
unauthenticated and publishes no quota, and this lane paces at
`MIN_INTERVAL_SECONDS` regardless.

`is_self_post` IS DERIVABLE HERE AND WAS NOT BEING DERIVED
----------------------------------------------------------
`triage.gates.pure_link_post` reads `Document.is_self_post` and reports
NOT_APPLICABLE when it is None - which `NotRun` documents as **permanent, a
property of the document**. On a blog article that is true and always will be.
On Hacker News it was neither: a story with a `url` and no `text` IS a link
post, and nothing was mapping it.

That mattered more here than anywhere else, because the case the gate exists
for is the case this platform produced: **a bare GitHub link at 678 points
whose evidence was entirely in its comments.**

    story with `text`                a self post (Ask HN, a text submission)
    story with `url` and no `text`   a LINK POST
    a comment                        NOT_APPLICABLE, and permanently so

The third row is the one worth spelling out. A comment is neither a link post
nor a self post - the distinction is about how a SUBMISSION carries its
content - so None here is the honest answer rather than a gap, and it is the
same None a blog article gets for the same reason.

⚠  THIS IS A MAPPING AND NOT A GATE DECISION. It says what the platform's own
   fields mean; whether a link post with no commentary should be dropped is
   `pure_link_post`'s rule and is unchanged. On Reddit that rule keeps a link
   post WITH commentary - 392 of 536 in the substitution corpus carry
   `selftext` - and the equivalent on Hacker News is a story whose `text` is
   present, which is exactly what `is_self_post` True means here.

AUTHOR IDENTITY: THE USERNAME, AND WHY THAT IS DEFENSIBLE HERE
---------------------------------------------------------------
Every other platform in this corpus hands over a numeric account id because
usernames can change. **Hacker News offers no way to change a username** - it
is not a field the API omits, it is a feature the site does not have - so the
username is the account's permanent identifier and there is nothing more stable
to prefer.

That is a documented ABSENCE rather than an id we were given, so it is stated
here and not assumed: if HN ever ships renames, every author row written by this
adapter becomes ambiguous, and this paragraph is where somebody will look.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from collect.adapters.documents import (
    NO_TEXT_REASON,
    DocumentDraft,
    SweepCounts,
    WriteReport,
)
from collect.config import settings
from collect.ids import stable_id
from collect.limiter import HostLimiter
from collect.rawstore import RAW, RawStore

log = logging.getLogger(__name__)

SOURCE_ID = "hackernews"
DOCUMENT_SOURCE = "hackernews"

BASE_URL = "https://hn.algolia.com/api/v1"
SEARCH_PATH = "/search"
#: Relevance-ranked. `/search_by_date` is the same index ordered by time and is
#: the right endpoint for an exhaustive window sweep; this adapter is driven per
#: model surface, where relevance is what a bounded fetch wants.
SEARCH_BY_DATE_PATH = "/search_by_date"
ITEM_PATH = "/items/{id}"

#: Algolia's `paginationLimitedTo` for this index. See the module docstring.
HITS_CAP = 1000
PER_PAGE = 50
DEFAULT_MAX_PAGES = 1

#: Unauthenticated and free, with no published limit. Politeness, not a budget.
MIN_INTERVAL_SECONDS = 1.0

#: The Algolia tag that restricts a search to comments. Left OFF entirely
#: returns stories and comments both, which is what the standalone article
#: script wanted; this adapter's unit is the comment, so it is set.
COMMENT_TAG = "comment"

#: A comment whose text the API returns as None or empty. HN blanks the text of
#: dead and flagged comments while keeping the record, so this is a real state
#: and not a parse failure.
#:
#: THE STRING IS SHARED WITH HUGGING FACE, which reaches the same condition by
#: another route. Two spellings of one filter reason is what
#: `documents.NO_TEXT_REASON` exists to prevent.
DEAD_COMMENT_REASON = NO_TEXT_REASON


@dataclass(frozen=True)
class HnComment:
    """One Algolia comment hit, flattened.

    `comment_text` is HTML - `&#x27;` for an apostrophe, `<p>` between
    paragraphs. It is NOT unescaped here: prose is derived at assembly
    (`collect/assemble/prose.py:hackernews_prose`), and unescaping in the
    fetcher would put a transformation between the bytes and the hash.
    """

    object_id: str
    author: str | None
    comment_text: str | None
    created_at: str | None
    created_at_i: int | None
    parent_id: str | None
    story_id: str | None
    story_title: str | None
    story_url: str | None

    @property
    def external_id(self) -> str:
        return self.object_id

    @property
    def url(self) -> str:
        """The comment's permalink on news.ycombinator.com.

        Algolia does not return one, so it is constructed from the id - the one
        derived value in this class, and it is derived from an id rather than
        from content, so it is stable.
        """
        return f"https://news.ycombinator.com/item?id={self.object_id}"

    @property
    def sieve_text(self) -> str:
        """What the sieve reads.

        ⚠  THE COMMENT TEXT ALONE, WITHOUT THE STORY TITLE, AND THAT IS A
        DELIBERATE CHOICE WITH A COST. A comment inside a thread about a model
        routinely does not name the model - it says "it" - so sieving on the
        comment alone rejects exactly the replies that carry the detail.

        Including `story_title` would fix the recall and break the meaning: a
        200-comment thread whose title names the model would pass every comment
        in it, and the sieve's `candidates` figure would become "comments in
        threads about X" while reading as "comments mentioning X". Those are
        different populations and the second is what a claim needs.

        So the sieve stays strict here, and SUBJECT-THREAD membership is carried
        by `thread_root_id` instead - a structural fact, recorded on the row,
        for `judge/` to use when it decides what a thread is about. The Reddit
        phase-one pass reached the same conclusion from the other direction: 3
        of its 7 surviving items were only phase one when their comments were
        read TOGETHER.
        """
        return self.comment_text or ""

    @property
    def is_self_post(self) -> None:
        """Always None. A comment is neither a link post nor a self post.

        Stated as a property rather than left absent so the answer is the
        adapter's rather than a default's - and so `pure_link_post` reporting
        NOT_APPLICABLE for an HN comment is a mapping somebody made, not a
        field nobody wired.
        """
        return None

    @property
    def engagement(self) -> dict[str, Any]:
        """HN does not expose comment scores, to anyone, by design.

        Keys present and None rather than an empty dict, so a reader sees that
        the platform withholds the figure rather than that this comment scored
        zero (rule 6). `points` is populated for STORIES only.
        """
        return {"score": None, "comments": None}


@dataclass(frozen=True)
class HnStory:
    """One story, fetched as a comment's subject anchor."""

    item_id: str
    title: str | None
    url: str | None
    author: str | None
    text: str | None
    points: int | None
    created_at: str | None
    created_at_i: int | None
    child_count: int

    @property
    def external_id(self) -> str:
        return self.item_id

    @property
    def hn_url(self) -> str:
        return f"https://news.ycombinator.com/item?id={self.item_id}"

    @property
    def is_self_post(self) -> bool | None:
        """True for a text submission, False for a link post, None if neither.

        `triage.gates.pure_link_post`'s input. See the module docstring for why
        this exists and what it is not.

        None IS REACHABLE AND IS NOT A BUG: an item with no `text` AND no `url`
        is neither, and the honest answer is that this record does not say. A
        `False` there would call it a link post with no link, and
        `pure_link_post` would then drop it for having no commentary about
        nothing.
        """
        has_text = bool(self.text and self.text.strip())
        if has_text:
            return True
        if self.url:
            return False
        return None

    @property
    def engagement(self) -> dict[str, Any]:
        return {"score": self.points, "comments": self.child_count}


@dataclass(frozen=True)
class StoredItem:
    """One comment or story whose own item payload is in the store."""

    external_id: str
    ref: str
    content_hash: str
    size: int
    already_present: bool


@dataclass
class HnRun:
    """One query, what it cost, and what it produced."""

    query: str
    started_at: datetime
    finished_at: datetime | None = None

    pages_fetched: int = 0
    pages_stored: int = 0
    search_calls: int = 0
    item_calls: int = 0
    http_errors: int = 0

    discovery_refs: list[str] = field(default_factory=list)
    comments: list[HnComment] = field(default_factory=list)
    verdicts: list[Any] = field(default_factory=list)
    survivors: list[HnComment] = field(default_factory=list)

    #: Comment documents, and story documents, kept apart. See the module
    #: docstring: a story is context and was never retrieved by the query, so
    #: one pooled "stored" figure would overstate what the query found.
    stored_comments: list[tuple[HnComment, StoredItem]] = field(default_factory=list)
    stored_stories: list[tuple[HnStory, StoredItem]] = field(default_factory=list)

    #: `nbHits`, verbatim, and it is a RETRIEVAL total over prefix-matched
    #: tokens - never a mention count. None means the response did not carry it.
    total_hits: int | None = None
    pages_available: int | None = None

    #: Comments the API returned with no text. A real HN state (dead/flagged),
    #: counted rather than dropped silently.
    without_text: int = 0

    exhausted: bool = False
    truncated_by: str | None = None

    @property
    def items_fetched(self) -> int:
        return len(self.comments)

    @property
    def items_kept(self) -> int:
        """Comment documents only. Stories are not what the query retrieved."""
        return len(self.stored_comments)

    def harvest_run_fields(self) -> dict[str, Any]:
        return {
            "id": stable_id("hr", SOURCE_ID, self.query, self.started_at.isoformat()),
            "source_id": SOURCE_ID,
            # THE WHOLE DENOMINATOR IN THE STRING: the query, the tag that
            # restricted it to comments, and the page size. A `harvest_run` row
            # that says only `Fable 5.1` cannot say it excluded stories.
            "query_key": f"{self.query} tags:{COMMENT_TAG} per_page:{PER_PAGE}",
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "items_fetched": self.items_fetched,
            "items_kept": self.items_kept,
            "http_errors": self.http_errors,
            "exhausted": (
                None
                if self.total_hits is None
                else self.total_hits <= self.items_fetched
            ),
            "truncated_by": self.truncated_by,
            "pipeline_version": settings().pipeline_version,
            "pages_fetched": self.pages_fetched,
            "pages_stored": self.pages_stored,
        }


class HackerNewsHarvester:
    """Search comments, store the page, sieve, then fetch each item by id."""

    def __init__(
        self,
        *,
        client: httpx.Client,
        store: RawStore,
        limiter: HostLimiter | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
        per_page: int = PER_PAGE,
        by_date: bool = False,
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
        self._search_path = SEARCH_BY_DATE_PATH if by_date else SEARCH_PATH
        self._clock = clock
        self._sleep = sleeper

    def _get(self, path: str, params: dict[str, Any] | None, run: HnRun):
        url = f"{BASE_URL}{path}"
        self._limiter.wait(url)
        try:
            response = self._client.get(url, params=params)
        except httpx.HTTPError as error:
            run.http_errors += 1
            log.error("hackernews: request failed on %s %r: %s", path, params, error)
            return None
        if response.status_code != 200:
            run.http_errors += 1
            log.warning("hackernews: HTTP %s on %s %r", response.status_code, path, params)
            return None
        return response

    def search(self, query: str, *, run: HnRun | None = None) -> HnRun:
        """Issue the query, storing each page before anything is sieved."""
        run = run if run is not None else HnRun(query=query, started_at=self._clock())

        for page in range(self._max_pages):
            params = {
                "query": query,
                "tags": COMMENT_TAG,
                "hitsPerPage": self._per_page,
                "page": page,
            }
            response = self._get(self._search_path, params, run)
            run.search_calls += 1
            run.pages_fetched = page + 1
            if response is None:
                break

            try:
                payload = response.json()
            except ValueError:
                run.http_errors += 1
                log.error("hackernews: search response for %r is not JSON", query)
                break

            stored = self._store.put(response.content, namespace=RAW)
            run.discovery_refs.append(stored.ref)
            run.pages_stored += 1

            if isinstance(payload.get("nbHits"), int):
                run.total_hits = payload["nbHits"]
            if isinstance(payload.get("nbPages"), int):
                run.pages_available = payload["nbPages"]

            hits = payload.get("hits") or []
            for hit in hits:
                if not isinstance(hit, dict) or not hit.get("objectID"):
                    continue
                comment = _comment_of(hit)
                if not comment.comment_text:
                    run.without_text += 1
                run.comments.append(comment)

            if len(hits) < self._per_page:
                run.exhausted = True
                break

        if run.total_hits is not None and run.total_hits > HITS_CAP:
            # THE PLATFORM STOPPING US, not a budget we chose. See the module
            # docstring: the response gives no error when it truncates.
            run.truncated_by = "result-ceiling"
        run.finished_at = self._clock()
        return run

    def sieve_run(self, run: HnRun, terms) -> HnRun:
        """Apply the terms to comment text only. See `HnComment.sieve_text`."""
        from collect.adapters.queries.sieve import sieve

        for comment in run.comments:
            verdict = sieve(terms, comment.sieve_text)
            run.verdicts.append(verdict)
            if verdict.passed:
                run.survivors.append(comment)
        return run

    def fetch_item(self, item_id: str, run: HnRun) -> tuple[StoredItem, dict] | None:
        """Fetch one item — the per-document artifact `text_ref` names."""
        response = self._get(ITEM_PATH.format(id=item_id), None, run)
        run.item_calls += 1
        if response is None:
            return None
        stored = self._store.put(response.content, namespace=RAW)
        try:
            payload = response.json()
        except ValueError:
            log.warning("hackernews: item %s payload is not JSON", item_id)
            payload = {}
        return (
            StoredItem(
                external_id=item_id,
                ref=stored.ref,
                content_hash=stored.content_hash,
                size=stored.size,
                already_present=stored.already_present,
            ),
            payload if isinstance(payload, dict) else {},
        )

    def harvest(self, query: str, terms=None, *, run: HnRun | None = None,
                max_fetch: int | None = None, with_stories: bool = True) -> HnRun:
        """One query, end to end: comments, then each comment's subject story.

        `with_stories=False` skips the anchors. Offered because a caller
        measuring retrieval does not need them, and because the story fetch is
        one request per DISTINCT story rather than per comment - deduplicated
        here, since a thread that contributes six comments must not be fetched
        six times.
        """
        run = self.search(query, run=run)
        if terms is not None:
            self.sieve_run(run, terms)
            survivors = run.survivors
        else:
            survivors = list(run.comments)

        if max_fetch is not None and len(survivors) > max_fetch:
            log.warning("hackernews: %d survivors, fetching %d", len(survivors), max_fetch)
            run.truncated_by = run.truncated_by or "query-budget"
            survivors = survivors[:max_fetch]

        for comment in survivors:
            fetched = self.fetch_item(comment.external_id, run)
            if fetched is not None:
                run.stored_comments.append((comment, fetched[0]))

        if with_stories:
            wanted = {
                c.story_id
                for c, _ in run.stored_comments
                if c.story_id and c.story_id != c.external_id
            }
            for story_id in sorted(wanted):
                fetched = self.fetch_item(story_id, run)
                if fetched is None:
                    continue
                run.stored_stories.append((_story_of(story_id, fetched[1]), fetched[0]))

        run.finished_at = self._clock()
        return run

    # ── the write path ───────────────────────────────────────────────────

    def drafts(self, run: HnRun) -> list[DocumentDraft]:
        """Story anchors FIRST, then comments.

        ORDER MATTERS FOR READABILITY OF THE RESULT, not for correctness -
        `document.thread_root_id` and `parent_id` carry no foreign key, so a
        comment can be written before its story without the database objecting.
        That is worth knowing rather than relying on: it means a run that failed
        to fetch a story still stores its comments, and the dangling root id is
        a coverage fact rather than a lost document.
        """
        drafts: list[DocumentDraft] = []
        for story, stored in run.stored_stories:
            drafts.append(
                DocumentDraft(
                    source=DOCUMENT_SOURCE,
                    external_id=story.external_id,
                    url=story.hn_url,
                    text_ref=stored.ref,
                    content_hash=stored.content_hash,
                    created_at=story.created_at_i or story.created_at,
                    author_external_id=story.author,
                    author_handle=story.author,
                    lang=None,
                    # A story is its own root. `parent_id` stays NULL, because
                    # inventing a self-reference makes "is this a root"
                    # unanswerable - `reddit_write.document_row`'s reasoning.
                    thread_root_external_id=story.external_id,
                    engagement=story.engagement,
                    # THE COLUMN EXISTS SINCE 2026-09-08, so the mapping this
                    # module already computed finally lands. A story with
                    # `text` is a self post; one with a `url` and no `text` is
                    # a link post - and the link post is the case the gate is
                    # for, because the busiest thread in the measured corpus
                    # was a bare GitHub link at 678 points.
                    is_self_post=story.is_self_post,
                )
            )
        for comment, stored in run.stored_comments:
            drafts.append(
                DocumentDraft(
                    source=DOCUMENT_SOURCE,
                    external_id=comment.external_id,
                    url=comment.url,
                    text_ref=stored.ref,
                    content_hash=stored.content_hash,
                    created_at=comment.created_at_i or comment.created_at,
                    author_external_id=comment.author,
                    author_handle=comment.author,
                    lang=None,
                    thread_root_external_id=comment.story_id,
                    parent_external_id=comment.parent_id,
                    # None, AND PERMANENTLY SO. A comment is neither a link
                    # post nor a self post - the distinction is about how a
                    # SUBMISSION carries its content - so this is the honest
                    # answer rather than a gap, and it is the same None a blog
                    # article gets for the same reason.
                    is_self_post=None,
                    engagement=comment.engagement,
                    # A comment HN blanked keeps its row and says why. Rejected
                    # is not deleted: a filter nobody can inspect cannot be
                    # trusted, and the payload is already stored either way.
                    status="kept" if comment.comment_text else "filtered",
                    filter_reasons=(
                        None if comment.comment_text else (DEAD_COMMENT_REASON,)
                    ),
                )
            )
        return drafts

    def write_documents(
        self,
        conn,
        run: HnRun,
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

    def counts(self, run: HnRun) -> SweepCounts:
        notes = [
            "the document unit is the COMMENT; story rows are subject anchors "
            f"and are counted apart ({len(run.stored_stories)} stored)",
        ]
        if run.total_hits is not None:
            notes.append(
                f"nbHits = {run.total_hits}, which is a prefix-matched RETRIEVAL "
                "total and not a mention count"
            )
        if run.truncated_by == "result-ceiling":
            notes.append(
                f"nbHits exceeds Algolia's {HITS_CAP}-hit pagination cap, so this "
                "query cannot be paged to exhaustion"
            )
        if run.without_text:
            notes.append(
                f"{run.without_text} comment(s) came back with no text (dead or "
                "flagged) and are stored as status='filtered'"
            )
        return SweepCounts(
            platform=SOURCE_ID,
            requests_issued=run.search_calls + run.item_calls,
            candidates=run.items_fetched,
            stored=run.items_kept,
            http_errors=run.http_errors,
            notes=notes,
        )


def _comment_of(hit: dict[str, Any]) -> HnComment:
    def _text(key: str) -> str | None:
        value = hit.get(key)
        return value if isinstance(value, str) and value.strip() else None

    def _id(key: str) -> str | None:
        value = hit.get(key)
        return str(value) if value is not None else None

    created_i = hit.get("created_at_i")
    return HnComment(
        object_id=str(hit["objectID"]),
        author=_text("author"),
        comment_text=_text("comment_text"),
        created_at=_text("created_at"),
        created_at_i=int(created_i) if isinstance(created_i, int | float) else None,
        parent_id=_id("parent_id"),
        story_id=_id("story_id"),
        story_title=_text("story_title"),
        story_url=_text("story_url"),
    )


def _story_of(item_id: str, payload: dict[str, Any]) -> HnStory:
    created_i = payload.get("created_at_i")
    points = payload.get("points")
    return HnStory(
        item_id=item_id,
        title=payload.get("title"),
        url=payload.get("url"),
        author=payload.get("author"),
        text=payload.get("text"),
        points=int(points) if isinstance(points, int | float) else None,
        created_at=payload.get("created_at"),
        created_at_i=int(created_i) if isinstance(created_i, int | float) else None,
        child_count=len(payload.get("children") or ()),
    )


def is_self_post_of(payload: dict[str, Any]) -> bool | None:
    """`is_self_post` from a STORED Hacker News item payload.

    The form that matters for triage, because the gates run over stored rows
    rather than over a live run's objects: a projection built from
    `document.text_ref` reads the payload, not an `HnStory`. Same three answers
    as `HnStory.is_self_post`, from the same two fields, in one place so the two
    cannot drift - `has_artifact` records what two definitions of one concept
    cost.

    A COMMENT PAYLOAD ANSWERS None, and it is identified by its own `type`
    rather than by the absence of a `url`: a link post also has no `text`, so
    an absence test would call every comment a link post and hand
    `pure_link_post` a verdict on a record the rule is not about.
    """
    if str(payload.get("type") or "").casefold() == "comment":
        return None
    text = payload.get("text")
    if text and str(text).strip():
        return True
    if payload.get("url"):
        return False
    return None


def hackernews_document_id(external_id: str) -> str:
    """`document.id` for an HN comment or story. The shared convention."""
    from collect.adapters.documents import document_id

    return document_id(DOCUMENT_SOURCE, external_id)


# ── the gated entry point ────────────────────────────────────────────────


def observe_hackernews_use() -> dict[str, object]:
    """This run's live observations for the terms gate.

    `access_path: api` is the Algolia search API and the HN item API, never
    news.ycombinator.com's HTML. Recorded per run because it is the fact the
    ruling turns on: HN's own guidance points at these endpoints for exactly
    this purpose, and a run that started scraping the site would be under a
    different set of terms without anybody editing the ruling.
    """
    return {"access_path": "api"}


def harvester_for_source(source, *, rulings=None, **kwargs) -> HackerNewsHarvester:
    """Build a harvester for a `source` row, ToS gate included.

    ⚠  IT WILL REFUSE UNTIL A RULING EXISTS, and this platform's gap is already
       written down: `scripts/fetch_hackernews_articles.py` says in its own
       docstring that it does not route through a gated entry point, that
       `assert_terms_reviewed()` therefore did not run, and that
       **`contract/sources.yaml` carries no ruling for Algolia/HN at all** - so
       that data is publishable on the Articles page and is NOT admissible to
       the pipeline.

       This adapter is the admissible path, and it stays refused until the
       ruling lands. Draft in
       `docs/proposals/for-engineer-2-five-new-platform-sources.md`.
    """
    from collect.registry.assertions import assert_terms_reviewed, source_field

    source_id = source_field(source, "id", "?")
    assert_terms_reviewed(
        [source],
        rulings=rulings,
        observations={source_id: observe_hackernews_use()},
    )
    return HackerNewsHarvester(**kwargs)
