"""Developer forums on Discourse: the newest topics, each one's opening post.

ADDED 2026-10-26 for the Google AI Developers Forum (discuss.ai.google.dev),
the third discussion platform scoped that day and the largest forum measured:
3,022 topics in 30 days (`/categories.json` `topics_month`), gemini-api 1,712.

WHY A NIGHTLY LISTING AND NOT A PER-MODEL SEARCH. The forum's robots.txt
disallows `/search` for every generic bot, and Google's terms forbid automated
access only "in violation of the machine-readable instructions on our web pages
(for example, robots.txt files ...)" (policies.google.com/terms, effective
2026-07-30). So the route is what robots.txt allows: the newest-created topic
listing (`/latest.json?order=created`), each topic's JSON (`/t/<id>.json`),
and the opening post's markdown (`/raw/<id>/1`). All three are re-tested
against robots.txt on every run (`observe`), because the terms make robots.txt
the permission - a host that disallows one tomorrow is obeyed that night.

WHAT IS STORED. One payload per topic: its title and the opening post's raw
markdown - what its author typed, which is what a quote must verify against -
plus the forum-local user id. Replies are other voices and are not fetched yet
(rule 9). `document.source` is `forum`; `external_id` is `<host>/t/<id>`, and
the author is `<host>:<user_id>` because a Discourse user id means nothing
outside its own forum.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

from collect.adapters.basis import observe_use_basis
from collect.adapters.blog.robots import RobotsGate
from collect.adapters.documents import DocumentDraft, WriteReport
from collect.limiter import HostLimiter
from collect.rawstore import RAW, RawStore

log = logging.getLogger(__name__)

DOCUMENT_SOURCE = "forum"
LISTING_PATH = "/latest.json"
ACCESS_PATH = "discourse-json"


@dataclass(frozen=True)
class TopicRef:
    """One row of the newest-created listing."""

    topic_id: int
    slug: str
    title: str
    created_at: str | None
    posts_count: int


@dataclass(frozen=True)
class StoredTopic:
    host: str
    topic: TopicRef
    user_id: int | None
    url: str
    ref: str
    content_hash: str

    @property
    def external_id(self) -> str:
        return f"{self.host}/t/{self.topic.topic_id}"

    def draft(self) -> DocumentDraft:
        return DocumentDraft(
            source=DOCUMENT_SOURCE,
            external_id=self.external_id,
            url=self.url,
            text_ref=self.ref,
            content_hash=self.content_hash,
            created_at=self.topic.created_at,
            # Forum-local, so qualified by the forum: user 5 here is not user 5
            # anywhere else.
            author_external_id=(f"{self.host}:{self.user_id}"
                                if self.user_id is not None else None),
            author_handle=None,
            lang=None,
            engagement={"comments": max(0, self.topic.posts_count - 1)},
        )


@dataclass
class ForumRun:
    host: str
    listing_calls: int = 0
    topic_calls: int = 0
    http_errors: int = 0
    robots_blocked: int = 0
    listed: int = 0
    already_stored: int = 0
    deferred: int = 0
    stored: list[StoredTopic] = field(default_factory=list)


class DiscourseForum:
    """One Discourse forum, read only where its robots.txt allows."""

    def __init__(self, base_url: str, *, client: httpx.Client, store: RawStore,
                 robots: RobotsGate, limiter: HostLimiter | None = None) -> None:
        self.base = base_url.rstrip("/")
        self.host = urlparse(self.base).hostname or self.base
        self._client = client
        self._store = store
        self._robots = robots
        self._limiter = HostLimiter() if limiter is None else limiter

    # ── the live observations the terms gate reads ────────────────────────

    def observe(self) -> dict[str, object]:
        """Re-test, on this run, every path this adapter will request."""
        listing = self._robots.allows(f"{self.base}{LISTING_PATH}")
        topic = self._robots.allows(f"{self.base}/t/1.json")
        raw = self._robots.allows(f"{self.base}/raw/1/1")
        return {
            "access_path": ACCESS_PATH,
            "robots_status": listing.ruling.status,
            "listing_path_allowed": listing.allowed,
            "topic_path_allowed": topic.allowed,
            "raw_path_allowed": raw.allowed,
            **observe_use_basis(),
        }

    # ── requests ──────────────────────────────────────────────────────────

    def _get(self, path: str, run: ForumRun, *,
             params: dict | None = None) -> httpx.Response | None:
        url = f"{self.base}{path}"
        if not self._robots.allows(url).allowed:
            run.robots_blocked += 1
            log.warning("%s: robots.txt disallows %s; not requested", self.host, path)
            return None
        self._limiter.wait(url, min_interval=self._robots.min_interval(url))
        try:
            response = self._client.get(url, params=params)
        except httpx.HTTPError as error:
            run.http_errors += 1
            log.error("%s: %s failed: %s", self.host, path, error)
            return None
        if response.status_code != 200:
            run.http_errors += 1
            log.error("%s: HTTP %s on %s", self.host, response.status_code, path)
            return None
        return response

    def newest(self, run: ForumRun, *, pages: int) -> list[TopicRef]:
        """Newest-created topics, `pages` pages of the listing."""
        topics: list[TopicRef] = []
        for page in range(pages):
            response = self._get(LISTING_PATH, run, params={
                "order": "created", "ascending": "false", "page": page})
            run.listing_calls += 1
            if response is None:
                break
            rows = ((response.json() or {}).get("topic_list") or {}).get("topics") or []
            for row in rows:
                if row.get("archetype", "regular") != "regular" or row.get("id") is None:
                    continue
                topics.append(TopicRef(topic_id=int(row["id"]), slug=row.get("slug") or "",
                                       title=row.get("title") or "",
                                       created_at=row.get("created_at"),
                                       posts_count=int(row.get("posts_count") or 1)))
            if len(rows) < 30:
                break
        run.listed = len(topics)
        return topics

    def fetch(self, topic: TopicRef, run: ForumRun) -> StoredTopic | None:
        """The topic's JSON for its author, then the opening post's markdown."""
        meta = self._get(f"/t/{topic.topic_id}.json", run)
        run.topic_calls += 1
        if meta is None:
            return None
        posts = ((meta.json() or {}).get("post_stream") or {}).get("posts") or []
        first = next((p for p in posts if p.get("post_number") == 1), None)
        raw = self._get(f"/raw/{topic.topic_id}/1", run)
        run.topic_calls += 1
        if raw is None or first is None:
            return None
        url = f"{self.base}/t/{topic.slug}/{topic.topic_id}" if topic.slug else \
            f"{self.base}/t/{topic.topic_id}"
        payload = {
            "kind": "discourse_topic",
            "forum": self.host,
            "topic_id": topic.topic_id,
            "url": url,
            "title": topic.title,
            "raw": raw.text,
            "created_at": first.get("created_at") or topic.created_at,
            "user_id": first.get("user_id"),
            "posts_count": topic.posts_count,
        }
        put = self._store.put(json.dumps(payload, sort_keys=True, ensure_ascii=False)
                              .encode("utf-8"), namespace=RAW)
        return StoredTopic(host=self.host, topic=topic, user_id=first.get("user_id"),
                           url=url, ref=put.ref, content_hash=put.content_hash)

    def harvest(self, *, pages: int, held: frozenset[str], max_new: int) -> ForumRun:
        """The newest topics not already stored, at most `max_new` of them."""
        run = ForumRun(host=self.host)
        for topic in self.newest(run, pages=pages):
            if f"{self.host}/t/{topic.topic_id}" in held:
                run.already_stored += 1
                continue
            if len(run.stored) >= max_new:
                run.deferred += 1
                continue
            stored = self.fetch(topic, run)
            if stored is not None:
                run.stored.append(stored)
        return run

    @staticmethod
    def write_documents(conn, run: ForumRun, *, retrieval_provenance: str = "not_recorded",
                        batch: int = 500) -> WriteReport:
        from collect.adapters.documents import write_documents as write

        return write(conn, [s.draft() for s in run.stored],
                     retrieval_provenance=retrieval_provenance, harvest_run_id=None,
                     batch=batch)


def forum_for_source(source, *, rulings=None, client: httpx.Client, store: RawStore,
                     robots: RobotsGate, **kwargs: Any) -> DiscourseForum:
    """Build the forum reader for a `forum:` source row, terms gate included:
    the ruling's preconditions are this run's own robots.txt observations."""
    from collect.registry.assertions import assert_terms_reviewed, source_field

    forum = DiscourseForum(source_field(source, "endpoint"), client=client, store=store,
                           robots=robots, **kwargs)
    assert_terms_reviewed([source], rulings=rulings,
                          observations={source_field(source, "id", "?"): forum.observe()})
    return forum
