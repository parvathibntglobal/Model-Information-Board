"""V2EX: a Chinese developer community's AI boards, topic and replies as a thread.

ADDED 2026-10-26, the fourth discussion source scoped that day and the one
non-English source that fits the stack's rule - official APIs and public feeds,
robots.txt respected. (Qiita's API is disallowed by its own robots.txt and its
tag feed carries ~140-character summaries; Zenn has no official API and its
feed carries ~300-character summaries; both were left for a team decision.)

THE ROUTE. V2EX's documented v1 API (v2ex.com/help/api), anonymous:
`/api/topics/show.json?node_name=<board>` - the board's ten newest topics, with
the author's markdown in `content` - and `/api/replies/show.json?topic_id=<id>`
for the replies. The help page states 600 requests an hour per IP; a night here
is about 55. robots.txt disallows only /backstage/, /signin, /signout and
/settings. No terms of service exist at /tos or /terms (2026-10-26).

WHY REPLIES, WHEN THE GITHUB AND FORUM ARMS TAKE ONLY OPENING POSTS. A V2EX
topic is short - median about 100 characters across the five boards on
2026-10-26 - and usually a question; the first-hand answers are in the replies.
Each reply is its own document and its own voice, a child of the topic's
thread (`thread_root_external_id`), so extraction reads the thread.

ONE LIMIT, STATED: a thread is assembled once, so replies that arrive after
the night a topic is first read are not in it. Topics already stored are not
re-read.

Authors are V2EX's numeric member id, never the username, which can change.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from collect.adapters.basis import observe_use_basis
from collect.adapters.documents import DocumentDraft, WriteReport
from collect.limiter import HostLimiter
from collect.rawstore import RAW, RawStore

log = logging.getLogger(__name__)

SOURCE_ID = "v2ex"
DOCUMENT_SOURCE = "v2ex"
BASE_URL = "https://www.v2ex.com"
TOPICS_PATH = "/api/topics/show.json"
REPLIES_PATH = "/api/replies/show.json"

#: 600 an hour per IP is the stated limit; one every two seconds is 1,800 an
#: hour of headroom we never use, at about 55 requests a night.
MIN_INTERVAL_SECONDS = 2.0


def _iso(epoch: Any) -> str | None:
    try:
        return datetime.fromtimestamp(int(epoch), tz=UTC).isoformat()
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class StoredItem:
    """One topic or reply, its payload in the store."""

    kind: str  # "topic" | "reply"
    item_id: int
    topic_id: int
    url: str
    created_at: str | None
    member_id: int | None
    member_name: str | None
    replies: int
    ref: str
    content_hash: str

    @property
    def external_id(self) -> str:
        return f"t{self.item_id}" if self.kind == "topic" else f"r{self.item_id}"

    def draft(self) -> DocumentDraft:
        is_reply = self.kind == "reply"
        return DocumentDraft(
            source=DOCUMENT_SOURCE,
            external_id=self.external_id,
            url=self.url,
            text_ref=self.ref,
            content_hash=self.content_hash,
            created_at=self.created_at,
            author_external_id=str(self.member_id) if self.member_id is not None else None,
            author_handle=self.member_name,
            # The boards are Chinese-language but a post's language is not
            # measured here, so it stays unknown rather than assumed (rule 6).
            lang=None,
            engagement=None if is_reply else {"comments": self.replies},
            thread_root_external_id=f"t{self.topic_id}" if is_reply else None,
            parent_external_id=f"t{self.topic_id}" if is_reply else None,
        )


@dataclass
class V2exRun:
    nodes: list[str]
    requests: int = 0
    http_errors: int = 0
    listed: int = 0
    already_stored: int = 0
    deferred: int = 0
    topics: list[StoredItem] = field(default_factory=list)
    replies: list[StoredItem] = field(default_factory=list)


class V2exHarvester:
    """The newest topics on each board, each with its replies."""

    def __init__(self, *, client: httpx.Client, store: RawStore,
                 limiter: HostLimiter | None = None) -> None:
        self._client = client
        self._store = store
        self._limiter = (HostLimiter(min_interval=MIN_INTERVAL_SECONDS)
                         if limiter is None else limiter)

    def _get(self, path: str, params: dict, run: V2exRun) -> list | None:
        url = f"{BASE_URL}{path}"
        self._limiter.wait(url)
        run.requests += 1
        try:
            response = self._client.get(url, params=params)
        except httpx.HTTPError as error:
            run.http_errors += 1
            log.error("v2ex: %s failed: %s", path, error)
            return None
        if response.status_code != 200:
            run.http_errors += 1
            log.error("v2ex: HTTP %s on %s %r - NOT an empty board", response.status_code,
                      path, params)
            return None
        try:
            payload = response.json()
        except ValueError:
            run.http_errors += 1
            return None
        if not isinstance(payload, list):
            # The API answers an error as an object (`{"status": "error", ...}`).
            run.http_errors += 1
            log.error("v2ex: %s answered %s", path, str(payload)[:200])
            return None
        return payload

    def _put(self, payload: dict) -> tuple[str, str]:
        put = self._store.put(json.dumps(payload, sort_keys=True, ensure_ascii=False)
                              .encode("utf-8"), namespace=RAW)
        return put.ref, put.content_hash

    def harvest(self, nodes: list[str], *, held: frozenset[str], max_topics: int) -> V2exRun:
        run = V2exRun(nodes=list(nodes))
        for node in nodes:
            topics = self._get(TOPICS_PATH, {"node_name": node}, run)
            if topics is None:
                continue
            for t in topics:
                if t.get("id") is None or t.get("deleted"):
                    continue
                run.listed += 1
                if f"t{t['id']}" in held:
                    run.already_stored += 1
                    continue
                if len(run.topics) >= max_topics:
                    run.deferred += 1
                    continue
                self._store_topic(t, node, run)
        return run

    def _store_topic(self, t: dict, node: str, run: V2exRun) -> None:
        member = t.get("member") or {}
        topic_id = int(t["id"])
        url = t.get("url") or f"{BASE_URL}/t/{topic_id}"
        ref, digest = self._put({
            "kind": "v2ex_topic", "id": topic_id, "node": node, "url": url,
            "title": t.get("title") or "", "content": t.get("content") or "",
            "created": t.get("created"), "member_id": member.get("id"),
            "replies": t.get("replies") or 0,
        })
        run.topics.append(StoredItem(
            kind="topic", item_id=topic_id, topic_id=topic_id, url=url,
            created_at=_iso(t.get("created")), member_id=member.get("id"),
            member_name=member.get("username"), replies=int(t.get("replies") or 0),
            ref=ref, content_hash=digest))
        if not t.get("replies"):
            return
        replies = self._get(REPLIES_PATH, {"topic_id": topic_id}, run)
        for r in replies or []:
            if r.get("id") is None or not (r.get("content") or "").strip():
                continue
            rm = r.get("member") or {}
            rref, rdigest = self._put({
                "kind": "v2ex_reply", "id": r["id"], "topic_id": topic_id,
                "content": r.get("content") or "", "created": r.get("created"),
                "member_id": rm.get("id"),
            })
            run.replies.append(StoredItem(
                kind="reply", item_id=int(r["id"]), topic_id=topic_id,
                url=f"{url}#r_{r['id']}", created_at=_iso(r.get("created")),
                member_id=rm.get("id"), member_name=rm.get("username"), replies=0,
                ref=rref, content_hash=rdigest))

    @staticmethod
    def write_documents(conn, run: V2exRun, *, retrieval_provenance: str = "not_recorded",
                        batch: int = 500) -> WriteReport:
        """Topics first: a reply's `thread_root_id` names its topic's document."""
        from collect.adapters.documents import write_documents as write

        drafts = [s.draft() for s in run.topics] + [s.draft() for s in run.replies]
        return write(conn, drafts, retrieval_provenance=retrieval_provenance,
                     harvest_run_id=None, batch=batch)


def observe_v2ex_use() -> dict[str, object]:
    """This run's live observations for the terms gate."""
    return {"access_path": "api", "api_version": "v1", **observe_use_basis()}


def harvester_for_source(source, *, rulings=None, **kwargs) -> V2exHarvester:
    """Build a harvester for the `v2ex` source row, terms gate included."""
    from collect.registry.assertions import assert_terms_reviewed, source_field

    assert_terms_reviewed([source], rulings=rulings,
                          observations={source_field(source, "id", "?"): observe_v2ex_use()})
    return V2exHarvester(**kwargs)
