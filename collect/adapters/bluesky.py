"""Bluesky: posts engineers write about the models they use.

ADDED 2026-10-26, the second discussion platform scoped that day. Measured then,
through this endpoint, for posts dated 2026-10-19..26: "Claude Code" 2,939,
DeepSeek 3,241, Qwen 641, GLM 543, MiniMax 523 (`hitsTotal`); of the top 25
English Qwen posts read by hand, about 7 were first-hand usage reports.

THE ROUTE. Bluesky's public AppView, `app.bsky.feed.searchPosts`, with no
credential: the developer docs say these endpoints "do not support
authentication" and carry "generous rate-limits". `api.bsky.app` answers it;
the cached host `public.api.bsky.app` refused search with 403 on 2026-10-26,
which is why the endpoint is named here rather than left to a default.

TERMS (`contract/sources.yaml`, ruling `bluesky-appview-terms`). The Terms of
Service carry no clause on reading or scraping; robots.txt allows everything.
The developer guidelines carry three obligations for a service that only
reads, all recorded in the ruling: delete content a user asks to have deleted,
publish a monitored contact address, and keep records of requests.

WHAT IS STORED. Each post as the search returned it, one payload per post -
`text_ref` names the post, never the search page, for the content-hash reason
every adapter here follows. `document.author_id` comes from the DID, the
account's permanent identifier; a handle is a domain name that can change
hands, so it is never the identity (the reasoning behind Reddit's `t2_` and
GitHub's numeric id).

NO DOCUMENTED READ LIMIT, so the 1 request a second here is this lane's default
politeness (`collect/limiter.py`), not a figure somebody read.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from collect.adapters.basis import observe_use_basis
from collect.adapters.documents import DocumentDraft, SweepCounts, WriteReport
from collect.adapters.queries.sieve import matches, normalize
from collect.config import settings
from collect.ids import stable_id
from collect.limiter import HostLimiter
from collect.rawstore import RAW, RawStore

log = logging.getLogger(__name__)

SOURCE_ID = "bluesky"
DOCUMENT_SOURCE = "bluesky"

#: `api.bsky.app`, NOT `public.api.bsky.app`: the second answered searchPosts
#: with 403 on 2026-10-26.
BASE_URL = "https://api.bsky.app/xrpc"
SEARCH_PATH = "/app.bsky.feed.searchPosts"

#: searchPosts' own maximum page size.
PER_PAGE = 100
MIN_INTERVAL_SECONDS = 1.0


@dataclass(frozen=True)
class BlueskyHit:
    """One post from a search response. The text is in the hit: no second fetch."""

    uri: str
    did: str | None
    handle: str | None
    text: str
    created_at: str | None
    lang: str | None
    likes: int
    replies: int
    #: The post object exactly as the search returned it, stored as its payload.
    raw: dict[str, Any]

    @property
    def external_id(self) -> str:
        """The `at://` URI - the platform's own permanent identity for a post."""
        return self.uri

    @property
    def url(self) -> str:
        """The post's public page: `bsky.app/profile/<did>/post/<rkey>`."""
        rkey = self.uri.rsplit("/", 1)[-1]
        return f"https://bsky.app/profile/{self.did}/post/{rkey}"


@dataclass(frozen=True)
class StoredPost:
    hit: BlueskyHit
    ref: str
    content_hash: str
    already_present: bool

    def draft(self) -> DocumentDraft:
        return DocumentDraft(
            source=DOCUMENT_SOURCE,
            external_id=self.hit.external_id,
            url=self.hit.url,
            text_ref=self.ref,
            content_hash=self.content_hash,
            created_at=self.hit.created_at,
            # The DID: permanent, and the same across handle changes.
            author_external_id=self.hit.did,
            author_handle=self.hit.handle,
            lang=self.hit.lang,
            engagement={"score": self.hit.likes, "comments": self.hit.replies},
        )


@dataclass
class BlueskyRun:
    """One query, what it cost, and what it produced."""

    query: str
    started_at: datetime
    finished_at: datetime | None = None
    search_calls: int = 0
    http_errors: int = 0
    #: `hitsTotal` as the platform reported it; None when it did not answer.
    total_count: int | None = None
    hits: list[BlueskyHit] = field(default_factory=list)
    rejected: int = 0
    stored: list[StoredPost] = field(default_factory=list)
    discovery_ref: str | None = None

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
            "query_key": f"searchPosts:{self.query} sort:latest limit:{PER_PAGE}",
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "items_fetched": self.items_fetched,
            "items_kept": self.items_kept,
            "http_errors": self.http_errors,
            "exhausted": None,
            "truncated_by": "query-budget" if (self.total_count or 0) > len(self.hits) else None,
            "pipeline_version": settings().pipeline_version,
        }


def _hit_of(post: dict[str, Any]) -> BlueskyHit | None:
    """A searchPosts item as a hit; None for one carrying no URI or no text."""
    record = post.get("record") or {}
    uri, text = post.get("uri"), record.get("text")
    if not uri or not isinstance(text, str):
        return None
    author = post.get("author") or {}
    langs = record.get("langs") or []
    return BlueskyHit(
        uri=uri,
        did=author.get("did"),
        handle=author.get("handle"),
        text=text,
        created_at=record.get("createdAt"),
        lang=langs[0] if langs else None,
        likes=int(post.get("likeCount") or 0),
        replies=int(post.get("replyCount") or 0),
        raw=post,
    )


def search_query(surface: str) -> str:
    """The surface as a phrase, so `GPT 5.5` is not three separate words."""
    return f'"{surface.strip()}"'


class BlueskyHarvester:
    """Search one spelling, keep the posts that name the model, store each one."""

    def __init__(self, *, client: httpx.Client, store: RawStore,
                 limiter: HostLimiter | None = None, max_keep_per_query: int = 50,
                 clock=lambda: datetime.now(UTC), sleeper=time.sleep) -> None:
        self._client = client
        self._store = store
        self._limiter = (HostLimiter(min_interval=MIN_INTERVAL_SECONDS)
                         if limiter is None else limiter)
        self._max_keep = max_keep_per_query
        self._clock = clock
        self._sleep = sleeper

    def search(self, run: BlueskyRun) -> dict[str, Any] | None:
        """One page, newest first. None on any failure - never an empty page."""
        url = f"{BASE_URL}{SEARCH_PATH}"
        self._limiter.wait(url)
        run.search_calls += 1
        try:
            response = self._client.get(url, params={"q": run.query, "sort": "latest",
                                                     "limit": PER_PAGE})
        except httpx.HTTPError as error:
            run.http_errors += 1
            log.error("bluesky: search failed for %r: %s", run.query, error)
            return None
        if response.status_code != 200:
            run.http_errors += 1
            log.error("bluesky: HTTP %s for %r - NOT an empty result set",
                      response.status_code, run.query)
            return None
        try:
            payload = response.json()
        except ValueError:
            run.http_errors += 1
            return None
        run.discovery_ref = self._store.put(response.content, namespace=RAW).ref
        return payload

    def harvest(self, surface: str, variants: list[str] | None = None) -> BlueskyRun:
        """One spelling, end to end. A post is kept only if it names ANY
        spelling of the model (`variants`, defaulting to `surface` alone)."""
        run = BlueskyRun(query=search_query(surface), started_at=self._clock())
        payload = self.search(run)
        if payload is not None:
            total = payload.get("hitsTotal")
            run.total_count = int(total) if isinstance(total, int) else None
            run.hits = [h for h in (_hit_of(p) for p in payload.get("posts") or []) if h]
            terms = variants or [surface]
            for hit in run.hits:
                if not any(matches(t, normalize(hit.text)) for t in terms):
                    run.rejected += 1
                    continue
                if len(run.stored) >= self._max_keep:
                    break
                run.stored.append(self._store_post(hit))
        run.finished_at = self._clock()
        return run

    def _store_post(self, hit: BlueskyHit) -> StoredPost:
        import json

        blob = json.dumps(hit.raw, sort_keys=True, ensure_ascii=False).encode("utf-8")
        put = self._store.put(blob, namespace=RAW)
        return StoredPost(hit=hit, ref=put.ref, content_hash=put.content_hash,
                          already_present=put.already_present)

    def write_documents(self, conn, run: BlueskyRun, *, retrieval_provenance: str,
                        harvest_run_id: str | None = None, batch: int = 500) -> WriteReport:
        from collect.adapters.documents import write_documents as write

        return write(conn, [s.draft() for s in run.stored],
                     retrieval_provenance=retrieval_provenance,
                     harvest_run_id=harvest_run_id, batch=batch)

    def counts(self, run: BlueskyRun) -> SweepCounts:
        return SweepCounts(
            platform=SOURCE_ID,
            requests_issued=run.search_calls,
            candidates=run.items_fetched,
            stored=run.items_kept,
            http_errors=run.http_errors,
            notes=[f"{run.rejected} of {run.items_fetched} retrieved posts named no "
                   "spelling of the model and were not kept"],
        )


# ── the gated entry point ────────────────────────────────────────────────


def observe_bluesky_use() -> dict[str, object]:
    """This run's live observations for the terms gate: the public AppView API,
    on the search endpoint, under the use basis."""
    return {"access_path": "api", "search_endpoint": SEARCH_PATH, **observe_use_basis()}


def harvester_for_source(source, *, rulings=None, **kwargs) -> BlueskyHarvester:
    """Build a harvester for the `bluesky` source row, terms gate included."""
    from collect.registry.assertions import assert_terms_reviewed, source_field

    source_id = source_field(source, "id", "?")
    assert_terms_reviewed([source], rulings=rulings,
                          observations={source_id: observe_bluesky_use()})
    return BlueskyHarvester(**kwargs)
