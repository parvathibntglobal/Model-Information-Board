"""The Reddit adapter, via RapidAPI. Search, sieve, then fetch what survived.

WHAT THIS IS AND IS NOT
-----------------------
This is the FETCH PATH only. Thread assembly — the comment tree, child
selection and `offset_map` — is refused explicitly by `assemble_thread` rather
than half-built, because two things it needs do not exist yet. See the refusal
for what they are.

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
    monthly      `x-ratelimit-requests-limit: 1000000`, `-remaining`,
                 `-reset` (~28 days). Readable on EVERY response, so quota is
                 knowable before a sweep rather than only after it stops.

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
    ) -> None:
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
        self._host = settings().rapidapi_host
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

        remaining = response.headers.get("x-ratelimit-requests-remaining")
        if remaining is not None:
            with suppress(ValueError):
                run.quota_remaining = int(remaining)

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

    def sieve_run(self, run: RedditRun, terms) -> RedditRun:
        """Apply a rendered term set to what search returned. No fetching."""
        from collect.adapters.queries.sieve import sieve

        for post in run.posts:
            verdict = sieve(terms, post.sieve_text)
            run.verdicts.append(verdict)
            if verdict.passed:
                run.survivors.append(post)
        return run

    # ── assembly, refused ────────────────────────────────────────────────

    def assemble_thread(self, post: RedditPost):
        """Refused. Two things it needs do not exist, and a stub would hide it.

        Raises:
            AssemblyNotBuilt: always, with what is missing.
        """
        raise AssemblyNotBuilt(
            "Thread assembly is not built, and is refused rather than "
            "approximated because a partial selection is indistinguishable "
            "from a complete one once it is a row.\n"
            "\n"
            "  The scorer is no longer the reason. collect/triage/"
            "specificity.py implements specificity_score, so child ranking "
            "has a scorer to call. ONE REASON REMAINS AND IT IS SUFFICIENT.\n"
            "\n"
            "  The selection cannot be bounded. One getPostComments call "
            "returned 200 of 4,833 comments (4%), and Reddit orders SIBLINGS "
            "rather than the tree: 30% of adjacent pairs are score "
            "inversions, and a depth-2 comment scoring 610 sits under "
            "top-level comments scoring 6. So the last-seen score bounds "
            "nothing unseen, and 'page until the top five are stable' has no "
            "cheap stopping rule.\n"
            "\n"
            "  Nor is coverage fully knowable: of 252 'more' markers on that "
            "thread, 126 report a hidden count (4,730 total, largest 3,180) "
            "and 126 report none. Any coverage figure is a LOWER BOUND on "
            "what is missing.\n"
            "\n"
            "  `thread_context.observed_children`, `hidden_children_min` and "
            "`coverage_ratio` are proposed on issue #5 so the selection can "
            "state what it saw. Until those exist, this would write 'the top "
            "5 children' when it means 'the top 5 of the 4% we happened to "
            "fetch'."
        )


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
