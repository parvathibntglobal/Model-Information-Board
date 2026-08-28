"""The Reddit adapter, via RapidAPI. Search, sieve, then fetch what survived.

WHAT THIS IS AND IS NOT
-----------------------
Fetch, and — since 2026-08-18 — assembly. `assemble_thread` refused for
eighteen days because a selection that cannot state what it saw would write
"the top 5 children" when it means "the top 5 of the 4% we happened to fetch".
#54 landed the coverage columns, so it can now state it. The rules live in
`collect/assemble/thread.py`; this module fetches and hands over.

WHERE `document.author_id` IS WRITTEN: `reddit_write.py`, SINCE 2026-08-21
--------------------------------------------------------------------------
There was no Reddit document writer, so nothing set it - **0 of 6 reddit
`document` rows carried an author** against 30 of 31 blog rows, and
`blog/write.py` was the only module in the repository that set the column.
`collect/adapters/reddit_write.py` now does, canonicalising through
`author_external_id` below and refusing a row where the account is gone.

**The 33 existing rows are still NULL.** `scripts/backfill_authors.py` sources
the id from the stored payload rather than re-fetching, and reported 33
candidates with 0 attributable on 2026-08-21 because every reddit and github
payload is absent from the local raw store - the database is remote and its
store is on that host. Run it there.

The rest of this section is why the column matters, and it is unchanged.

The handles exist: `RedditComment.author` is parsed and the stored API payload
carries one per comment - the 1u1b22l thread has **152 distinct commenters**. So
this is a writer gap and not missing data.

It is load-bearing downstream. `judge/curate/gate.py:count` dedups voices off
`claim.author_id`, which comes from `document.author_id`, so every Reddit claim
currently collapses into one voice: the four on staging show
`independent_voices = 1` for a thread with 152 authors. Reddit is also the only
platform in the corpus with more than one author, so it is the only one that can
supply voice diversity at all.

Sourcing a handle from the payload at read time - as
`scripts/extraction_reading_pool.py` does for a labelling artifact - is fine for
something a human reads and wrong for anything that reaches a cell, because a
cell needs a stable identity that `author_identity_cluster` can merge.

WHY THIS PLATFORM IS DIFFERENT, AND WHAT THAT CLAIM IS ACTUALLY WORTH
----------------------------------------------------------------------
**RETRIEVAL DOES NOT GUARANTEE THE PHRASE. THE SIEVE CARRIES IT.** That is the
instruction; everything below is why.

Phrases DO NOT bind here. Two earlier versions of this docstring said they
did — the first without qualification, the second calling it phrase-dependent
with the cause left open. Both were wrong in the same direction, and both rested
on common phrases whose containment relevance ranking supplies for free.

The comparison that stands, measured 2026-08-14: `"context window"` returned
248 posts with the phrase present in 96%; `"window context"` returned 239 with
10%; the two result sets shared **2 ids out of 485**. Compare GitHub, where
`"sonnet claude 5"` returned 545 against the correct order's 540 with
near-total overlap, which is what proved its index ranks rather than binds.
That comparison still separates the two indexes — Reddit's word-order
sensitivity is real. It is not the same thing as binding a phrase.

The generalisation does not stand. Re-measured 2026-08-17 over the 19 distinct
quoted phrases of the substitution sweep, containment of the quoted phrase in
what came back:

    "went back to"                    75 posts        100%
    "reverted to"                     75               36%
    "switched back"                   75               25%
    "rolled back"                     75               24%
    "instead of opus 5"                9               67%
    "replaced gemini 2.5 flash"        6                0%
    "replaced opus 5"                  2                0%
    "switched from opus 5"             2                0%
    ------------------------------------------------------
    all 19 phrases                   357               43%

**Binding is a property of the phrase, not of the platform.** A rare phrase
does not return zero — it returns loosely matched posts, which is the shape
that reads as evidence and is not.

THE DIAGNOSIS IS SETTLED, AND IT IS THE WORSE OF THE TWO. It was left open on
2026-08-17 between "the platform ignored the phrase" and "our matcher is
stricter than the platform's". A variant probe the same day decided it.

Enumerating the looser variants of each phrase — `reverted back to`,
`reverted it to`, `switched it back`, `rolled everything back` and 14 more —
and checking what the non-containing posts actually carry:

    base phrase        n    exact    all words    >=1 word    neither
    "reverted to"     75      36%          37%        100%         0%
    "switched back"   75      25%          29%        100%         0%
    "rolled back"     75      24%          24%        100%         0%
    "went back to"    75     100%         100%        100%         0%

Enumerated variants explained almost nothing: 0 hits on three families and 1 on
the fourth. So it is not looser phrase semantics.

**THERE IS NO PHRASE OPERATOR. IT DEGRADES TO OR OVER THE TOKENS.** Every post
carries at least one word of the phrase and only a quarter carry all of them —
`"rolled back"` returns posts containing `back` without `rolled`. And this
explains the `kubernetes OR terraform` result below by the same mechanism: if
the API supports no operators and ranks by relevance over tokens, then a literal
`OR` is just another token and documents containing both real words rank highest,
which is exactly the 229-of-241 that was recorded as "narrows toward AND".

`"went back to"` at 100% is not the exception that saves the theory. It is a
very common English collocation, so relevance ranking returns it anyway — and
that is the same reason `"context window"` scored 96%. **That 96% was never
evidence of a phrase operator**, which is what made it generalise so badly.

CONSEQUENCE FOR THE CONTRACT, since acted on. The flag used to read
`requires: phrase_binding` and said a query is meaningless where phrases do not
bind — which implied some platform binds them, and on this evidence none does.
It is now `direction: decided_at_extraction`, naming where direction IS decided
rather than the capability whose absence stops it. Raised on #18, renamed with
Engineer 2 in the same change as her doc corrections.

The instruction is unchanged and now rests on a measurement rather than on a
choice between two explanations: retrieval does not guarantee the phrase, and
the sieve carries it.

A BARE TERM AFTER A QUOTED PHRASE IS NOT A FILTER
-------------------------------------------------
Measured the same day, over 44 `"phrase" alias` queries:

    contain the appended alias        7% of 2,031 posts
    overlap with the bare phrase      Jaccard 0.00-0.01 — near-disjoint sets
    phrase containment                DEGRADES, 43% alone -> 32% appended

It reweights rather than restricts. **Do not append an alias to scope a query
to a model** — it neither scopes nor preserves the phrase. Whatever scoping a
query needs has to survive the sieve instead.

WHAT DOES NOT WORK, MEASURED THE SAME DAY
-----------------------------------------
    OR is not boolean       `kubernetes OR terraform` returned 241 posts of
                            which 229 contain BOTH terms and 7 terraform
                            alone. Recorded as "narrows toward AND"; better
                            explained by the no-operator finding above, where
                            `OR` is simply a third token and both-word
                            documents rank highest. Either way: do not render
                            it.
    no result total         nothing reports a count; "how many matched" is
                            answerable only by paging to exhaustion, unlike
                            GitHub's `total_count`
    ceiling ~250 per sort   10 pages of 25, ending with `cursor: null`.
                            Different sorts return near-disjoint slices
                            (NEW ∩ TOP = 1 of ~250), so the ceiling is a
                            window onto a larger corpus, not the corpus
    trailing numerals fine  no issue-number pathology; Reddit has no issue
                            numbers to collide with

TWO LIMITS, AND ONLY ONE OF THEM FITS THE SCHEMA
------------------------------------------------
    per-minute   429 after 32 rapid calls, "exceeded the rate limit per
                 minute for your plan, PRO". Clears in ~60s. **No
                 `Retry-After` header**, so the backoff cannot be read off the
                 response and is assumed here.
    monthly      ALL THREE are now read by `_get` and recorded per call —
                 `_QUOTA_HEADERS`. Read 2026-08-18:
                     -limit      1000000
                     -remaining   998660
                     -reset      2064366  = 23.893 days, resets 2026-09-11
                 This docstring previously asserted the same 1,000,000 and
                 `-reset (~28 days)` as though both were observations. Neither
                 was, five documents cited this line as their source, and the
                 reset was wrong by four days. The limit was right, which is
                 the outcome that teaches nothing unless it is written down.
                 1 unit per request exactly, over 558 requests and per
                 individual call over the last 186.

                 STILL OPEN: the plan page says 500,000. A gateway header is
                 not proof of the billed tier, and no request can settle that
                 — the value would come from the party in doubt. See
                 docs/measurements/reddit-rate-and-quota.md §1.4.

                 NO PER-MINUTE HEADER EXISTS. All 16 response headers were
                 captured; the monthly triple is the only rate-limit family.
                 So the `< 32` below cannot be replaced by a reading.

`harvest_run.truncated_by` has no `'quota'` value, so an exhausted month
currently has nowhere to be recorded. It is proposed on issue #5. Until it
lands this adapter refuses to mislabel it as `'rate-limit'` — see
`RedditRun.harvest_run_fields`, which carries it homeless the same way the
blog adapter carries `outcome`.

'DATA NOT FOUND' MEANS ZERO RESULTS, NOT AN ERROR
-------------------------------------------------
The API answers a query with no matches by returning `success: false` and
`data: "data not found"` with HTTP 200. A nonsense query returns it; 25
back-to-back calls produced none. Reading it as a failure would make "nobody
discussed this" indistinguishable from "the call broke" — the collision this
project keeps finding, and the reason `total_count` is `int | None` on GitHub.
"""

from __future__ import annotations

import logging
import time
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from collect.adapters.queries.sieve import SieveVerdict, SieveYield, tally
from collect.config import settings
from collect.ids import stable_id
from collect.limiter import HostLimiter
from collect.rawstore import RAW, RawStore

log = logging.getLogger(__name__)

SOURCE_ID = "reddit"
SEARCH_PATH = "/getSearchPosts"
COMMENTS_PATH = "/getPostComments"

#: A subreddit listing. TAKES NO QUERY, which is the whole reason it exists here
#: beside `SEARCH_PATH`: `scripts/unfiltered_sweep.py` refuses `/getSearchPosts`
#: because *"the index ranks, and ranking is the selection effect this exists to
#: escape."*
#:
#: THE DIFFERENCE IS THE KIND OF TRUNCATION, NOT WHETHER THERE IS ONE. Both stop
#: early. A search stops at the most RELEVANT n — GitHub's `max_pages = 1` makes
#: every rate there a top-100-by-relevance figure, an upper bound, because the
#: index chose the hundred. A listing sorted NEW stops at the most RECENT n, and
#: recency is unrelated to whether a post carries evidence — so a rate over it
#: estimates the population instead of ceilinging it.
LISTING_PATH = "/getPostsBySubreddit"

#: `sort` for the listing. Recency is load-bearing, not a default: `TOP` or
#: `HOT` would reintroduce a ranking cut through the back door and the
#: denominator would stop being stateable.
#:
#: LOWERCASE, AND IT IS THE ENDPOINT'S SPELLING RATHER THAN A STYLE CHOICE.
#: `/getSearchPosts` takes `RELEVANCE`/`NEW`/`TOP` and this one takes `new` --
#: measured, because `NEW` returns HTTP 200 with a body carrying no `posts` key,
#: which this adapter reads as "nothing more to read" and records as exhausted.
#: A silent zero, on a sweep whose whole output is a rate. Found by a one-page
#: smoke run before the real one, which is the argument for smoke runs.
LISTING_SORT = "new"

#: Observed 2026-08-14: 429 after 32 rapid calls, message "exceeded the rate
#: limit per minute for your plan, PRO". Kept under it rather than at it.
SEARCH_PER_MINUTE = 25

#: There is no `Retry-After` on the 429, so this is assumed rather than read.
#: 60s is what cleared it in the probe.
BACKOFF_SECONDS = 60.0

#: 25 per page, and the ceiling arrives at 10 pages with `cursor: null`.
#: Defaults to one page for the same reason GitHub's does: a page is stored
#: whole, and pages beyond the first are not stored at all today.
PAGE_SIZE = 25

#: Response header -> run attribute. The whole rate-limit triple, captured on
#: every call. `-limit` and `-reset` were named in this module's docstring and
#: read by nothing until 2026-08-18; a map rather than three hand-written reads
#: so adding a fourth header is one line and cannot be half-done.
_QUOTA_HEADERS = {
    "x-ratelimit-requests-remaining": "quota_remaining",
    "x-ratelimit-requests-limit": "quota_limit",
    "x-ratelimit-requests-reset": "quota_reset_seconds",
}
DEFAULT_MAX_PAGES = 1

#: Reddit's own sorts. `BEST` is rejected by the comments endpoint, which
#: accepts `confidence, top, new` — spelled out rather than passed through, so
#: a typo is a local error and not a silently different query.
SEARCH_SORTS = frozenset({"RELEVANCE", "NEW", "TOP"})


class RedditConfigError(RuntimeError):
    """The adapter cannot be built from the current settings."""


class AssemblyNotBuilt(NotImplementedError):
    """Thread assembly is refused rather than approximated. See the message."""


@dataclass(frozen=True)
class RedditPost:
    """One search hit, flattened out of Reddit's `kind`/`data` envelope."""

    external_id: str            # t3_… — the fullname, never the bare id
    url: str
    title: str
    selftext: str
    author: str | None
    author_fullname: str | None  # t2_… — stable across renames
    subreddit: str
    created_utc: float | None
    score: int | None
    num_comments: int | None
    upvote_ratio: float | None
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def sieve_text(self) -> str:
        """What the sieve reads. Title and body, the same gift a full-text
        feed gives the blog adapter — so the sieve runs before any fetch."""
        return "\n".join(filter(None, (self.title, self.selftext)))

    @property
    def created_at(self) -> datetime | None:
        """A real UTC timestamp, or None. Never the fetch time (rule 6).

        `created_utc` is an epoch float here, which is the single measurement
        that kept this platform viable: a relative string would have left
        every Reddit document with a NULL `created_at`, and FR-4's window
        resolution and the 30-day decay half-life both read it.
        """
        if self.created_utc is None:
            return None
        return datetime.fromtimestamp(self.created_utc, tz=UTC)

    @property
    def engagement(self) -> dict[str, Any]:
        """`document.engagement`'s documented shape: score, comments, ratio."""
        return {
            "score": self.score,
            "comments": self.num_comments,
            "upvote_ratio": self.upvote_ratio,
        }


def author_external_id(post_or_fullname: RedditPost | str | None) -> str | None:
    """Canonical `t2_…`, from a post or from either id spelling.

    THE NORMALISATION IS THE POINT. A post carries `author_fullname:
    't2_2ii4xgakc7'`; `getProfile` carries `id: '2ii4xgakc7'` for the same
    person. `author` is UNIQUE (source, external_id), so taking each
    endpoint's field verbatim writes two rows for one engineer — which splits
    a voice, and FR-17 then counts it twice while believing it counts once.

    Usernames are not usable as the id: Reddit allows renames, and a renamed
    account would arrive as a new author while a reused name would merge two.
    The second is the over-clustering `collect/CLAUDE.md` calls worse.
    """
    value = (
        post_or_fullname.author_fullname
        if isinstance(post_or_fullname, RedditPost)
        else post_or_fullname
    )
    if not value:
        return None
    return value if value.startswith("t2_") else f"t2_{value}"


@dataclass
class RedditRun:
    """One query, what it cost, and the two things `harvest_run` cannot hold."""

    query: str
    sort: str
    started_at: datetime
    finished_at: datetime | None = None

    #: Pages actually requested, and pages written to `raw/`. They differ the
    #: moment `max_pages` rises above one, and the difference is exactly what
    #: makes "recoverable by re-sieving" true or false for this run. Proposed
    #: as `harvest_run.pages_fetched` / `pages_stored` on issue #5; carried
    #: here meanwhile so the number exists before the column does.
    pages_fetched: int = 0
    pages_stored: int = 0

    discovery_refs: list[str] = field(default_factory=list)
    posts: list[RedditPost] = field(default_factory=list)
    verdicts: list[SieveVerdict] = field(default_factory=list)
    survivors: list[RedditPost] = field(default_factory=list)

    search_calls: int = 0
    http_errors: int = 0
    rate_limited: int = 0
    backoff_seconds: float = 0.0

    #: None means WE DO NOT KNOW. Reddit reports no total at all, so this is
    #: None on every run — recorded as a fact about the platform rather than
    #: written as 0, which would read as "no matches".
    total_count: int | None = None

    exhausted: bool = False
    truncated_by: str | None = None

    #: Set when the MONTHLY quota is exhausted. Deliberately not folded into
    #: `truncated_by`: that CHECK has no 'quota' value, and 'rate-limit' means
    #: "retry shortly" while this means "stop until the reset". A scheduler
    #: told the first when the second is true retries against a wall.
    quota_exhausted: bool = False
    quota_remaining: int | None = None

    #: THE MONTHLY LIMIT AS THE RESPONSE STATED IT, not as anybody wrote it
    #: down. Added 2026-08-18 because the previous version of this adapter read
    #: `-remaining` and nothing else, so a docstring constant of 1,000,000 stood
    #: unchecked against a plan believed to be 500,000 for a fortnight. Read on
    #: 2026-08-18 as 1,000,000 — the constant was right and the method was not.
    #: None means the response did not carry it (rule 6: unread is not a value).
    quota_limit: int | None = None

    #: SECONDS until the window resets, verbatim from the header. Stored as the
    #: duration and not as a date: a date computed once and left in prose is
    #: stale within the month, which is what `(~28 days)` in this module's
    #: docstring turned out to be — the header says 2,064,366s, i.e. 23.9 days.
    quota_reset_seconds: int | None = None

    @property
    def items_fetched(self) -> int:
        return len(self.posts)

    @property
    def items_kept(self) -> int:
        return len(self.survivors)

    @property
    def sieve_yield(self) -> SieveYield:
        """Retrieved, phrase-containing, sieve-passing — all three.

        The middle number matters most on this platform, because binding is a
        property of the phrase rather than of the platform: `"went back to"`
        came back at 100% containment and `"rolled back"` at 24%, so identical
        `candidates` figures can mean very different things. Without it a query
        that retrieved 75 posts carrying nothing looks like a query that
        retrieved 75 posts carrying the phrase.

        Left as None when the query quoted nothing — there is no phrase to
        comply with, which is not the same as zero compliance (rule 6).
        """
        from collect.adapters.queries.sieve import count_phrase_present, quoted_phrases

        phrases = quoted_phrases(self.query)
        present: int | None = None
        if phrases and self.posts:
            texts = [post.sieve_text for post in self.posts]
            # Every quoted phrase must be present, matching how the query reads.
            present = sum(
                1
                for text in texts
                if all(count_phrase_present(p, [text]) for p in phrases)
            )
        return tally(self.query, self.verdicts, phrase_present=present)

    def harvest_run_fields(self) -> dict[str, Any]:
        """The row this run would write, and the fields with nowhere to go.

        `quota_exhausted`, `pages_fetched` and `pages_stored` are returned
        rather than dropped, for the same reason the blog adapter returns
        `outcome`: a value the schema cannot hold is a gap to argue about, not
        a value to discard quietly. All three are on issue #5.
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
            "exhausted": self.exhausted,
            "truncated_by": self.truncated_by,
            "pipeline_version": settings().pipeline_version,
            # ── homeless, pending #5 ──────────────────────────────────────
            "quota_exhausted": self.quota_exhausted,
            "pages_fetched": self.pages_fetched,
            "pages_stored": self.pages_stored,
        }


@dataclass
class ThreadFetch:
    """One `getPostComments` call: what was stored, and what was withheld.

    Deliberately NOT a `RedditRun`. A run is one query returning many posts; this
    is one post returning many comments, and `items_kept` has no meaning here
    because nothing is sieved. Reusing the run type would have made
    `sieve_yield` answerable on an object that never sieved anything.
    """

    thread_url: str
    started_at: datetime
    finished_at: datetime | None = None

    #: Written to raw/ BEFORE the tree is parsed, so a parse change is a
    #: re-parse rather than a re-fetch. Same reason search stores page 1 first.
    ref: str | None = None
    content_hash: str | None = None

    comments: tuple = ()
    coverage: Any = None

    http_errors: int = 0
    rate_limited: int = 0
    backoff_seconds: float = 0.0
    quota_remaining: int | None = None
    #: Same triple as `RedditRun`. A comment fetch is a metered call and its
    #: quota reading is as good as a search's — the 10-request gap in
    #: `docs/measurements/reddit-rate-and-quota.md` §1.1 is most likely a
    #: comment fetch, and is unattributable precisely because nothing recorded
    #: this. Present here so `_quota_sink` can forward them instead of setting
    #: them on a throwaway object.
    quota_limit: int | None = None
    quota_reset_seconds: int | None = None
    #: Set when the URL was not a thread permalink. Distinct from an HTTP error:
    #: nothing was wrong with the network, the input named the wrong thing.
    not_a_thread: bool = False

    @property
    def stored(self) -> bool:
        return self.ref is not None

    def document_rows(self) -> list[dict[str, Any]]:
        """One `document` row per comment. NO thread_context row.

        Assembly is refused, so nothing here selects children, orders them, or
        writes `flattened_text`. These are documents with a parent and a root,
        which is what makes the tree reconstructable later from stored data
        rather than from a second fetch.
        """
        rows = []
        for comment in self.comments:
            rows.append({
                "source": SOURCE_ID,
                "external_id": comment.external_id,
                "url": comment.url,
                "parent_id": comment.parent_id,
                "thread_root_id": comment.thread_root_id,
                "created_at": comment.created_at,
                "author_external_id": author_external_id(comment.author_fullname),
                "engagement": comment.engagement,
                "text_ref": self.ref,
                "content_hash": self.content_hash,
            })
        return rows


class RedditHarvester:
    """Search, store the page, sieve it, and keep what survived.

    THE ORDER IS THE SAME AS GITHUB'S, and for the same reason: the search
    response already carries each post's title and selftext, so the sieve runs
    on what search returned and nothing is fetched to find out it was
    irrelevant. The page is written to `raw/` BEFORE the sieve, so a rejected
    post's text is still on disk — for the pages that were stored, which is
    page 1 today.
    """

    def __init__(
        self,
        *,
        client: httpx.Client,
        store: RawStore,
        limiter: HostLimiter | None = None,
        max_pages: int = DEFAULT_MAX_PAGES,
        clock=lambda: datetime.now(UTC),
        sleeper=time.sleep,
        host: str | None = None,
    ) -> None:
        """`host` defaults to `RAPIDAPI_HOST` and may be supplied explicitly.

        THE DEFAULT IS THE PRODUCTION PATH AND THE ARGUMENT IS THE TESTABLE ONE.
        Reading the setting here and only here meant a test of the CONSTRUCTOR
        depended on the machine being configured for RapidAPI — which passed on
        a laptop with a `.env` and failed in CI, where it was the first thing to
        notice the difference. The tests in question were about the terms gate
        and about where that gate fires; neither is about whether RapidAPI is
        configured, and neither should have been able to fail for that reason.

        Unset and unsupplied still refuses, so nothing reaches the network
        without a host.
        """
        self._client = client
        self._store = store
        self._limiter = (
            HostLimiter(min_interval=60.0 / SEARCH_PER_MINUTE)
            if limiter is None
            else limiter
        )
        self._max_pages = max_pages
        self._clock = clock
        self._sleep = sleeper
        self._host = host if host is not None else settings().rapidapi_host
        if not self._host:
            raise RedditConfigError(
                "RAPIDAPI_HOST is not set. It must be a bare host such as "
                "'reddit34.p.rapidapi.com' — RapidAPI routes on the "
                "x-rapidapi-host header, so a full URL addresses no route."
            )
        self._base = f"https://{self._host}"

    # ── one page ─────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict[str, str], run: RedditRun):
        """One request, rate-limited, with the 429 handled explicitly."""
        url = f"{self._base}{path}"
        self._limiter.wait(url)
        response = self._client.get(url, params=params)
        run.search_calls += 1

        # ALL THREE, not the one we happen to act on. Reading `-remaining`
        # alone is how `-limit` stayed a docstring constant with five citations
        # (docs/measurements/reddit-rate-and-quota.md §1.2). Every value here is
        # a dated observation from this response; absent stays None.
        for header, attribute in _QUOTA_HEADERS.items():
            value = response.headers.get(header)
            if value is None:
                continue
            with suppress(ValueError):
                setattr(run, attribute, int(value))

        if response.status_code == 429:
            # No Retry-After is sent, so the wait is assumed. Counted rather
            # than swallowed: a throttled query that reported nothing would be
            # indistinguishable from a query with no matches.
            run.rate_limited += 1
            run.truncated_by = "rate-limit"
            run.backoff_seconds += BACKOFF_SECONDS
            log.warning("reddit: 429 on %r, sleeping %.0fs", params, BACKOFF_SECONDS)
            self._sleep(BACKOFF_SECONDS)
            return None

        if response.status_code != 200:
            run.http_errors += 1
            log.warning("reddit: HTTP %s on %r", response.status_code, params)
            return None
        return response

    def search(self, query: str, *, sort: str = "RELEVANCE") -> RedditRun:
        """Page the search, storing each page before anything is sieved."""
        if sort not in SEARCH_SORTS:
            raise ValueError(f"sort must be one of {sorted(SEARCH_SORTS)}, got {sort!r}")

        run = RedditRun(query=query, sort=sort, started_at=self._clock())
        cursor: str | None = None

        for page in range(1, self._max_pages + 1):
            params = {"query": query, "sort": sort}
            if cursor:
                params["cursor"] = cursor

            response = self._get(SEARCH_PATH, params, run)
            run.pages_fetched = page
            if response is None:
                break

            payload = response.json()
            data = payload.get("data")
            if not isinstance(data, dict):
                # 'data not found' is ZERO RESULTS, not a failure. Exhausted,
                # no error, nothing truncated.
                run.exhausted = True
                break

            # Stored BEFORE the sieve, so a rejected post's text survives.
            stored = self._store.put(response.content, namespace=RAW)
            run.discovery_refs.append(stored.ref)
            run.pages_stored += 1

            items = data.get("posts") or []
            run.posts.extend(_post_of(item) for item in items)
            cursor = data.get("cursor")

            if not items or not cursor:
                run.exhausted = True
                break
        else:
            # Ran out of pages before the platform ran out of results.
            if cursor:
                run.truncated_by = "result-ceiling"

        run.finished_at = self._clock()
        return run

    def list_subreddit(
        self, subreddit: str, *, pages: int, sort: str = LISTING_SORT
    ) -> RedditRun:
        """Page a subreddit listing, storing each page before anything is sieved.

        `query_key` is `subreddit:<name> sort:<sort> pages:<n>` — the WHOLE
        denominator in the string, so a `harvest_run` row says what population it
        drew from and nobody has to reconstruct it. GitHub's rows say
        `haiku-4.5 recall type:issue` and say nothing about the top-100 ceiling
        that governs every rate computed from them; this does not repeat that.

        `exhausted` means the subreddit ran out of posts before we ran out of
        pages — a listing that reached the end. `truncated_by = 'result-ceiling'`
        means the opposite: OUR page limit stopped us with posts still available,
        which is the recency cut and the denominator above.

        QUOTA IS NOT `truncated_by`. `harvest_run_truncated_ck` has no `'quota'`
        value, so an exhausted monthly quota is recorded on `quota_exhausted` and
        the gap is named in the sweep report. `rate-limit` would be wrong and
        expensively so: it means retry in ~60s, quota means stop for 23.893 days,
        and a scheduler told the first when the second is true spends the
        exhausted quota discovering it. Proposed as a sixth value in PR #161.
        """
        run = RedditRun(query=f"subreddit:{subreddit} sort:{sort} pages:{pages}",
                        sort=sort, started_at=self._clock())
        cursor: str | None = None

        for page in range(1, pages + 1):
            params = {"subreddit": subreddit, "sort": sort}
            if cursor:
                params["cursor"] = cursor

            response = self._get(LISTING_PATH, params, run)
            run.pages_fetched = page
            if response is None:
                break

            payload = response.json()
            data = payload.get("data")
            if not isinstance(data, dict):
                # `success: false` with `data: "data not found"` is ZERO RESULTS
                # at HTTP 200. Not an error, and not an empty subreddit either —
                # the two are indistinguishable here, so this records the only
                # one it can defend: nothing more to read.
                run.exhausted = True
                break

            # Stored BEFORE the sieve, so a rejected post's text survives and a
            # later re-sieve is possible over what this run actually saw.
            stored = self._store.put(response.content, namespace=RAW)
            run.discovery_refs.append(stored.ref)
            run.pages_stored += 1

            items = data.get("posts") or []
            run.posts.extend(_post_of(item) for item in items)
            cursor = data.get("cursor")

            if not items or not cursor:
                run.exhausted = True
                break
        else:
            # Our page budget ran out first. THE RECENCY CUT, recorded.
            if cursor:
                run.truncated_by = "result-ceiling"

        run.finished_at = self._clock()
        return run

    def sieve_run(self, run: RedditRun, terms) -> RedditRun:
        """Apply a rendered term set to what search returned. No fetching."""
        from collect.adapters.queries.sieve import sieve

        for post in run.posts:
            verdict = sieve(terms, post.sieve_text)
            run.verdicts.append(verdict)
            if verdict.passed:
                run.survivors.append(post)
        return run

    # ── comments: fetch and store, never assemble ────────────────────────

    def fetch_comments(self, post) -> ThreadFetch:
        """Fetch one thread's comments, store the payload, parse the tree.

        STORE THEN PARSE. The response is written to `raw/` before the tree is
        walked, so changing the parser is a re-parse of local bytes rather than
        another call against a monthly quota whose limit nobody has read. Same
        order as `search`.

        Takes the POST, not a URL, because the URL to fetch is `permalink` and
        not `document.url` — for a link post those differ and the second one
        names an image. See `reddit_comments.permalink_of`.

        Writes no `thread_context`. `assemble_thread` still refuses.
        """
        from collect.adapters.reddit_comments import parse_thread, permalink_of

        url = permalink_of(post)
        fetch = ThreadFetch(thread_url=url or "", started_at=self._clock())
        if url is None:
            fetch.not_a_thread = True
            fetch.finished_at = self._clock()
            log.warning(
                "reddit: %r has no thread permalink, so it has no comments to "
                "fetch. This is not an error - a link post's url is the linked "
                "content.", getattr(post, "external_id", post),
            )
            return fetch

        response = self._get(COMMENTS_PATH, {"post_url": url}, _quota_sink(fetch))
        fetch.finished_at = self._clock()
        if response is None:
            return fetch

        stored = self._store.put(response.content, namespace=RAW)
        fetch.ref = stored.ref
        fetch.content_hash = stored.content_hash

        parsed = parse_thread(response.json(), url=url)
        fetch.comments = parsed.comments
        fetch.coverage = parsed.coverage
        log.info(
            "reddit: %s -> %s", url, parsed.coverage.describe(),
        )
        return fetch

    # ── assembly, refused ────────────────────────────────────────────────

    def assemble_thread(
        self,
        post: RedditPost,
        *,
        thread=None,
        version_aliases=(),
        max_children: int = 5,
    ):
        """Build the `thread_context` row for a fetched thread.

        BUILT 2026-08-18, after eighteen days of refusing. The refusal's last
        reason went when #54 landed `observed_children`, `hidden_children_min`,
        `hidden_branches_unsized` and `coverage_ratio` — a selection can now say
        what it saw instead of writing "the top 5 children" when it means "the
        top 5 of the 4% we happened to fetch".

        The rules live in `collect/assemble/thread.py`, which is where the
        reasoning is. Two things worth knowing at the call site:

        **`selection_method` never gets the schema's default.** The bare
        `specificity_x_log_engagement` asserts a global ranking, and 200 of
        4,833 comments with 30% sibling inversions is not one. It writes
        `@observed`.

        **This touches no database.** It returns an `AssembledThread`; writing
        is `write_thread_context`, so the caller can look at the segments before
        they become rows.

        Args:
            post: the root post, already stored as a `document`.
            thread: a `ParsedThread`. Fetched here when not supplied.
            version_aliases: surfaces for `names_version`, which feeds the
                specificity score child ranking uses. Empty is legitimate and
                narrows the score rather than breaking it.
        """
        from collect.adapters.reddit_comments import parse_thread, permalink_of
        from collect.assemble.thread import assemble

        if thread is None:
            url = permalink_of(post)
            if url is None:
                raise AssemblyNotBuilt(
                    f"{post.external_id!r} has no thread permalink, so it has no "
                    "comment tree to assemble. A link post's url is the linked "
                    "content - this is not an error, and fetch_comments reports "
                    "it as `not_a_thread` rather than failing."
                )
            fetch = self.fetch_comments(post)
            if fetch.ref is None:
                raise AssemblyNotBuilt(
                    f"no stored payload for {post.external_id!r}: nothing to "
                    "assemble. This is a fetch problem, not an assembly one."
                )
            # Re-read from raw/ rather than holding the parse in memory: the
            # payload is written BEFORE it is parsed precisely so a parse change
            # is a re-parse and not a re-fetch, and assembly is a parse change.
            import json as _json

            thread = parse_thread(
                _json.loads(self._store.get_text(fetch.ref)), url=url
            )

        return assemble(
            thread,
            root_text=post.sieve_text,
            # BOTH ids from one place. `assemble` used to build the child ids
            # itself, so root and children followed two conventions chosen in
            # two modules — see `assemble`'s docstring for what that cost.
            root_document_id=reddit_document_id(post.external_id),
            child_document_id=lambda c: reddit_document_id(c.external_id),
            store=self._store,
            version_aliases=version_aliases,
            max_children=max_children,
        )



def _quota_sink(fetch: ThreadFetch):
    """Adapt a ThreadFetch to the counter surface `_get` writes to.

    `_get` increments `search_calls` and sets `truncated_by`, neither of which a
    thread fetch has. Rather than widen `_get` or duplicate it, this forwards the
    fields both share and absorbs the two that do not apply — so the 429 handling,
    the quota read and the error counting stay in ONE place.

    EVERY FIELD `_get` WRITES NEEDS A FORWARDER HERE. A missing one is not an
    error: `setattr` succeeds against the throwaway `_Sink` instance and the
    value is dropped where nobody looks. That is how `quota_limit` and
    `quota_reset_seconds` would have been lost on comment fetches when they were
    added on 2026-08-18, so they are forwarded below and
    `tests/test_reddit_fetch.py` asserts the sink covers the whole map.
    """

    class _Sink:
        search_calls = 0
        truncated_by = None

        @property
        def quota_remaining(self):
            return fetch.quota_remaining

        @quota_remaining.setter
        def quota_remaining(self, value):
            fetch.quota_remaining = value

        @property
        def quota_limit(self):
            return fetch.quota_limit

        @quota_limit.setter
        def quota_limit(self, value):
            fetch.quota_limit = value

        @property
        def quota_reset_seconds(self):
            return fetch.quota_reset_seconds

        @quota_reset_seconds.setter
        def quota_reset_seconds(self, value):
            fetch.quota_reset_seconds = value

        @property
        def http_errors(self):
            return fetch.http_errors

        @http_errors.setter
        def http_errors(self, value):
            fetch.http_errors = value

        @property
        def rate_limited(self):
            return fetch.rate_limited

        @rate_limited.setter
        def rate_limited(self, value):
            fetch.rate_limited = value

        @property
        def backoff_seconds(self):
            return fetch.backoff_seconds

        @backoff_seconds.setter
        def backoff_seconds(self, value):
            fetch.backoff_seconds = value

    return _Sink()


def _post_of(item: dict[str, Any]) -> RedditPost:
    """Flatten one `{kind: 't3', data: {...}}` envelope."""
    data = item.get("data", item)
    permalink = data.get("permalink") or ""
    return RedditPost(
        # The fullname, not the bare id: `document.external_id` is UNIQUE per
        # source, and `t3_abc` is what every other endpoint refers to it by.
        external_id=data.get("name") or f"t3_{data.get('id')}",
        url=data.get("url") or f"https://www.reddit.com{permalink}",
        title=data.get("title") or "",
        selftext=data.get("selftext") or "",
        author=data.get("author"),
        author_fullname=data.get("author_fullname"),
        subreddit=data.get("subreddit") or "",
        created_utc=data.get("created_utc"),
        score=data.get("score"),
        num_comments=data.get("num_comments"),
        upvote_ratio=data.get("upvote_ratio"),
        raw=data,
    )


def build_client(**kwargs) -> httpx.Client:
    """An httpx client carrying the RapidAPI headers and the lane's UA gate.

    Goes through `collect.http.build_client`, so the identifying User-Agent
    check is in the loop exactly as it is for every other adapter.
    """
    from collect.http import build_client as _build

    config = settings()
    if not config.rapidapi_key:
        raise RedditConfigError(
            "RAPIDAPI_KEY is not set, so no Reddit request can be made. It is "
            "not in .env.example yet — that edit is pending the terms ruling."
        )
    if not config.rapidapi_host:
        raise RedditConfigError("RAPIDAPI_HOST is not set.")

    headers = {
        "x-rapidapi-key": config.rapidapi_key,
        "x-rapidapi-host": config.rapidapi_host,
    }
    headers.update(kwargs.pop("headers", {}))
    return _build(headers=headers, **kwargs)


def reddit_document_id(external_id: str) -> str:
    """`document.id` for a Reddit post or comment. THE convention, one place.

    The fullname is kept whole — `t3_1u1b22l`, not `1u1b22l`. Engineer 2's
    fixture strips the `t1_`/`t3_` prefixes, which byte equality could not catch
    because the two lanes never compared ids until they did. Recorded here so
    the next disagreement is a diff against a named function rather than against
    an f-string in whichever module happened to need one.
    """
    return f"reddit:{external_id}"


#: The basis `reddit-via-rapidapi` rests on, as the ruling names it.
INTERNAL_DEVELOPMENT_ONLY = "internal-development-only"


def observe_reddit_use() -> dict[str, object]:
    """This run's live observations for the terms gate.

    The ruling permits internal development and testing, and nothing else. That
    is a fact about the DEPLOYMENT rather than about the request, so it is
    observed here and re-read on every run — the ruling then stops applying when
    the deployment changes, rather than when somebody remembers to revisit it.

    IT IS A PROXY, AND THE GAP IS THE POINT OF SAYING SO. `ENVIRONMENT` is the
    only signal the process actually has. It catches the case that matters most
    — a production deployment silently inheriting a development-only ruling —
    and it does NOT catch a staging instance that has acquired external users or
    started charging for something. Those remain conditions a person has to
    honour, which is exactly why the ruling records them as unresolved instead of
    treating them as handled.

    A basis is therefore a shorter fuse than `review_valid_days`, not a
    substitute for reading the terms again.
    """
    environment = settings().environment
    return {
        "use_basis": (
            INTERNAL_DEVELOPMENT_ONLY
            if environment != "production"
            else f"not-internal (ENVIRONMENT={environment})"
        )
    }


def harvester_for_source(source, *, rulings=None, **kwargs) -> RedditHarvester:
    """Build a harvester for a `source` row, ToS gate included.

    THE ENTRY POINT ANYTHING THAT FETCHES REDDIT MUST USE. Until 2026-08-18 this
    lane had no such entry point at all: `assert_terms_reviewed` was called from
    `blog/fetch.py` and `scripts/harvest_github.py` and from nowhere on the
    Reddit path, so the 1,297-post corpus every measurement here rests on was
    gathered without the gate ever being asked. The gate was working correctly
    and refusing Reddit the whole time; nothing consulted it.

    THE GATE FIRES HERE AND NOT IN `RedditHarvester.__init__`, for the reason
    `blog.fetch.fetcher_for_source` already documents: a constructor check
    forces every test to fabricate a reviewed source row, and **a fixture that
    fakes a ruling is worse than no gate, because it reads as one**. Tests
    construct `RedditHarvester` directly and get no gate, which is honest;
    anything that reaches the network comes through here.

    Not in `_get` either. That would fire per request and would need the source
    row threaded through `search` and `fetch_comments`, neither of which carries
    one — a lot of plumbing to check the same fact several hundred times a run.
    """
    from collect.registry.assertions import assert_terms_reviewed, source_field

    source_id = source_field(source, "id", "?")
    assert_terms_reviewed(
        [source],
        rulings=rulings,
        observations={source_id: observe_reddit_use()},
    )
    return RedditHarvester(**kwargs)
