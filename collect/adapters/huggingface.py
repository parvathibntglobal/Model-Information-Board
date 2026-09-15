"""The Hugging Face adapter, via the Hub API. Repos, then discussions, then comments.

THE DOCUMENT UNIT IS THE COMMENT INSIDE A DISCUSSION
-----------------------------------------------------
`huggingface:67a6c3556bc21667a66598fa` is one comment event. The discussion is
written too, as the thread root, exactly as Hacker News writes its story anchor
and `github.write_comments` writes the issue body.

Not the model card. A card is vendor copy - the publisher describing their own
release - and this board is about what *engineers* report, so a corpus of README
text would be a corpus of marketing with our own trust weight on it. The
Articles-page sweep already found the shape: of 295 repos matching one model,
**291 were community re-uploads** whose cards are derived from the original, so
card text corroborates itself across hundreds of rows.

⚠  THERE IS NO FULL-TEXT SEARCH OVER DISCUSSIONS, SO DISCOVERY IS REPO-SCOPED
------------------------------------------------------------------------------
The Hub API searches REPOS (`/api/models?search=`). Discussions are listed per
repo (`/api/models/{repo}/discussions`) and read one at a time
(`/api/models/{repo}/discussions/{num}`). There is no endpoint that searches
discussion bodies across the Hub.

**That makes an empty result on this platform structural rather than silent**,
and the distinction is rule 4 exactly:

    a model with NO Hugging Face repo has no discussion surface here at all.
    Zero documents is then "this platform has nothing to say about this model
    BECAUSE the model is not hosted here" - not "engineers reported no
    problems", and not "the adapter failed".

`HfRun.repos_matched` is carried for that reason: a run with 0 repos and a run
with 12 repos and 0 discussions are different findings, and one figure cannot
hold both. Anything reporting this platform must print both numbers.

THE COMMENT PAYLOAD IS RE-SERIALISED, AND THIS IS THE ONE DEVIATION
--------------------------------------------------------------------
    repo search response       -> raw/   discovery artifact
    discussions list response  -> raw/   discovery artifact
    discussion response        -> raw/   the THREAD's payload; the root's text_ref
    one `events[]` element     -> raw/   the COMMENT's text_ref

`docs/engineer-1/ruling-what-content-hash-identifies.md` wants `content_hash` to
be the hash of the bytes the platform gave us, unmodified. **The Hub publishes
no per-comment endpoint**, so the bytes for one comment do not exist as a
response, and the only alternative to re-serialising is pointing every comment
in a thread at the thread payload - which makes forty documents share one hash
and breaks dedupe and NFR-6, the failure `github.py` refuses `text_ref` on a
search page for.

So the comment's payload is `json.dumps(event, sort_keys=True,
ensure_ascii=False)`, which is **precisely what `github.fetch_comments` already
does** for the same reason, and the invariant that matters still holds:
`content_hash(resolve(text_ref)) == content_hash`, because the store hashes
exactly the bytes it was handed. What is lost is byte-identity with the wire for
that sub-object; what is kept is one hash per document. The enclosing
discussion's real bytes are stored as well, so nothing is unrecoverable.

Stated as a deviation rather than buried, because a reader comparing this to
`arxiv.py` - which spends a second request precisely to avoid re-serialising -
should see that the two differ because the platforms differ, not because two
people decided separately.

NO CREDENTIAL, AND NONE IS OPTIONAL-BUT-EXPECTED EITHER
--------------------------------------------------------
This adapter reads **no token**. Nothing here consults `HF_TOKEN` or any other
credential, and `collect/config.py` does not define one - the only setting this
module touches is `pipeline_version`, for the `harvest_run` row.

Proven rather than asserted: the 2026-09-07 control run against
`deepseek-ai/DeepSeek-R1` walked 2 repos, listed 100 discussions and stored 8
documents, unauthenticated
(`docs/measurements/new-adapter-smoke-hf-control-2026-09-07.json`).

**If a token is ever added it must stay optional**, and the reason is rule 6
rather than convenience: a token would raise the anonymous rate limit and admit
private and gated repos, so a run WITH one and a run WITHOUT one draw from
different populations. That difference has to be recorded on the run rather
than inferred from whether the environment happened to carry a key - otherwise
two `harvest_run` rows with the same `query_key` mean different things and
nothing on either says so.

AUTHOR IDENTITY: `author._id`, WHICH IS A REAL STABLE ID
---------------------------------------------------------
`{"_id": "63142785289cf15634cccc72", "name": "karmikovic", "type": "user"}`.
The `_id` survives a rename; `name` does not. Same reasoning as Reddit's `t2_`
and GitHub's `user.id`, and unlike arXiv this platform actually provides one.

⚠  `author.type` IS DECLARED AND HAS NO BOT VALUE. It carries `user` or `org`,
   plus `isPro`, `isHf`, `isHfAdmin`, `isMod`. **None of those is "is this an
   automated account"**, so the `known-bot` gate cannot be derived from this
   platform's own fields the way GitHub's `user.type == "Bot"` can. It is
   recorded on the row as-is and no bot inference is made here (rule 2's
   spirit: propose, never decide; and rule 8: an unmeasured check is not a
   gate).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from collect.adapters.basis import observe_use_basis
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

SOURCE_ID = "huggingface"
DOCUMENT_SOURCE = "huggingface"

BASE_URL = "https://huggingface.co/api"
MODEL_SEARCH_PATH = "/models"
DISCUSSIONS_PATH = "/models/{repo}/discussions"
DISCUSSION_PATH = "/models/{repo}/discussions/{num}"

#: Repos per search page, and discussions per list page (the Hub serves 50).
REPO_LIMIT = 20
DISCUSSIONS_PER_PAGE = 50

#: No published read limit for anonymous Hub API calls. Politeness, not a
#: budget - and named as unread rather than written down as a figure.
MIN_INTERVAL_SECONDS = 1.0

#: `events[].type` values. Only `comment` carries text a human wrote; the rest
#: are state changes (`status-change`, `title-change`, commits on a PR) and are
#: counted rather than stored as documents, because a status change is not
#: something anybody said.
COMMENT_EVENT = "comment"

#: A comment the Hub marks hidden. Kept as a row with a reason rather than
#: dropped - "rejected is not deleted", and the ruling on what to do with a
#: hidden comment is not this module's to make.
HIDDEN_REASON = "hidden_by_platform"

#: ⚠ AND `hidden` IS NOT THE ONLY WAY A COMMENT ARRIVES WITH NO TEXT. Found by
#: the 2026-09-07 smoke run rather than by reading the code: one event on a
#: DeepSeek-R1 discussion carried `data.latest.raw` empty with `hidden` false,
#: so it was written `status='kept'` and then REFUSED by `huggingface_prose` -
#: a row that looks like evidence and has none. Two conditions, two reasons,
#: both stored rather than dropped.
NO_TEXT = NO_TEXT_REASON


class HuggingFaceConfigError(RuntimeError):
    """The adapter cannot be built from the current settings."""


@dataclass(frozen=True)
class HfRepo:
    """One model repo from a Hub search. Discovery only — never a document."""

    repo_id: str
    author_org: str | None
    downloads: int | None
    likes: int | None
    last_modified: str | None
    tags: tuple[str, ...]

    @property
    def url(self) -> str:
        return f"https://huggingface.co/{self.repo_id}"

    @property
    def sieve_text(self) -> str:
        """The repo NAME and tags, which is all a search result carries.

        Used to decide whether to spend a discussions request on this repo. It
        is a routing decision rather than a relevance verdict about a document -
        no `document` row is ever created from this text.
        """
        return "\n".join((self.repo_id, " ".join(self.tags)))


@dataclass(frozen=True)
class HfComment:
    """One `comment` event inside a discussion."""

    event_id: str
    repo_id: str
    discussion_num: int
    author_external_id: str | None
    author_handle: str | None
    #: `user` or `org`. Recorded verbatim; see the module docstring on why this
    #: cannot answer "is this a bot".
    author_type: str | None
    created_at: str | None
    #: `data.latest.raw` — the markdown the person wrote. Held for the sieve,
    #: never written to the database in place of the payload.
    body: str | None
    hidden: bool
    #: The bytes stored for THIS comment: the event, re-serialised. See the
    #: module docstring for why this is the one re-serialised payload here.
    payload: str

    @property
    def has_text(self) -> bool:
        """Did the platform give this event any text at all?

        Separate from `hidden`, because the two are different states that reach
        the same place: a hidden comment was suppressed, and an empty one was
        never text. Both must be `status='filtered'` - a row with no text that
        reads as kept is a document nobody wrote.
        """
        return bool(self.body and self.body.strip())

    @property
    def external_id(self) -> str:
        return self.event_id

    @property
    def url(self) -> str:
        return (
            f"https://huggingface.co/{self.repo_id}/discussions/"
            f"{self.discussion_num}#{self.event_id}"
        )

    @property
    def sieve_text(self) -> str:
        return self.body or ""


@dataclass(frozen=True)
class HfDiscussion:
    """One discussion — the thread root, and a document in its own right."""

    repo_id: str
    num: int
    title: str
    author_external_id: str | None
    author_handle: str | None
    created_at: str | None
    status: str | None
    is_pull_request: bool
    comments: tuple[HfComment, ...] = ()

    @property
    def external_id(self) -> str:
        """`deepseek-ai/DeepSeek-R1#129` — the publisher's own identity."""
        return f"{self.repo_id}#{self.num}"

    @property
    def url(self) -> str:
        return f"https://huggingface.co/{self.repo_id}/discussions/{self.num}"

    @property
    def sieve_text(self) -> str:
        """The TITLE only.

        A discussion whose title names the model is a candidate; whether it
        carries evidence is a question about its comments, and each comment is
        sieved on its own text. Passing a title's verdict down to its comments
        would make `candidates` mean "comments in threads about X" while reading
        as "comments mentioning X" - the same trap `hackernews.HnComment
        .sieve_text` records.
        """
        return self.title


@dataclass
class HfRun:
    """One model surface, and everything the three-level walk cost."""

    query: str
    started_at: datetime
    finished_at: datetime | None = None

    search_calls: int = 0
    list_calls: int = 0
    detail_calls: int = 0
    http_errors: int = 0
    pages_stored: int = 0

    discovery_refs: list[str] = field(default_factory=list)

    #: ⚠ BOTH OF THESE MUST BE REPORTED. Zero repos and zero discussions are
    #: different findings - see the module docstring on structural absence.
    repos_matched: list[HfRepo] = field(default_factory=list)
    repos_walked: list[str] = field(default_factory=list)
    discussions_listed: int = 0
    discussions: list[HfDiscussion] = field(default_factory=list)

    verdicts: list[Any] = field(default_factory=list)
    #: Comment events that were not `type: comment` - state changes, commits.
    #: Counted so "few comments" cannot be confused with "few events".
    non_comment_events: int = 0
    hidden_comments: int = 0
    #: Comment events the platform returned with no text. Counted apart from
    #: `hidden_comments`: one was suppressed and one was never text.
    empty_comments: int = 0

    stored_discussions: list[tuple[HfDiscussion, str, str]] = field(default_factory=list)
    stored_comments: list[tuple[HfComment, str, str]] = field(default_factory=list)

    #: `count` from the discussions list — the repo's total, which the Hub does
    #: report. None means the response did not carry it.
    discussion_total: int | None = None

    truncated_by: str | None = None

    @property
    def items_fetched(self) -> int:
        """Comment events seen, which is the candidate population."""
        return sum(len(d.comments) for d in self.discussions)

    @property
    def items_kept(self) -> int:
        return len(self.stored_comments)

    def harvest_run_fields(self) -> dict[str, Any]:
        return {
            "id": stable_id("hr", SOURCE_ID, self.query, self.started_at.isoformat()),
            "source_id": SOURCE_ID,
            # THE WHOLE WALK IN THE STRING. A `harvest_run` row saying only
            # `Fable 5.1` could not say that discovery was repo-scoped, which is
            # the fact that decides whether an empty result means anything.
            "query_key": (
                f"repo-search:{self.query} repos:{len(self.repos_walked)} "
                f"discussions:{self.discussions_listed}"
            ),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "items_fetched": self.items_fetched,
            "items_kept": self.items_kept,
            "http_errors": self.http_errors,
            # NULL: exhaustion of a three-level walk is not a single fact, and
            # the Hub reports a total per repo rather than for the walk.
            "exhausted": None,
            "truncated_by": self.truncated_by,
            "pipeline_version": settings().pipeline_version,
            "pages_stored": self.pages_stored,
        }


class HuggingFaceHarvester:
    """Search repos, list their discussions, read each one, store the comments."""

    def __init__(
        self,
        *,
        client: httpx.Client,
        store: RawStore,
        limiter: HostLimiter | None = None,
        repo_limit: int = REPO_LIMIT,
        clock=lambda: datetime.now(UTC),
        sleeper=time.sleep,
    ) -> None:
        self._client = client
        self._store = store
        self._limiter = (
            HostLimiter(min_interval=MIN_INTERVAL_SECONDS) if limiter is None else limiter
        )
        self._repo_limit = repo_limit
        self._clock = clock
        self._sleep = sleeper

    def _get(self, path: str, params: dict[str, Any] | None, run: HfRun):
        url = f"{BASE_URL}{path}"
        self._limiter.wait(url)
        try:
            response = self._client.get(url, params=params)
        except httpx.HTTPError as error:
            run.http_errors += 1
            log.error("huggingface: request failed on %s: %s", path, error)
            return None
        if response.status_code != 200:
            run.http_errors += 1
            log.warning("huggingface: HTTP %s on %s %r", response.status_code, path, params)
            return None
        return response

    # ── level 1: repos ───────────────────────────────────────────────────

    def search_repos(self, query: str, *, run: HfRun | None = None) -> HfRun:
        """Find model repos whose id or tags match. Discovery, not documents."""
        run = run if run is not None else HfRun(query=query, started_at=self._clock())
        response = self._get(
            MODEL_SEARCH_PATH,
            {"search": query, "limit": self._repo_limit, "full": "false"},
            run,
        )
        run.search_calls += 1
        if response is None:
            return run
        stored = self._store.put(response.content, namespace=RAW)
        run.discovery_refs.append(stored.ref)
        run.pages_stored += 1
        try:
            payload = response.json()
        except ValueError:
            run.http_errors += 1
            log.error("huggingface: repo search for %r is not JSON", query)
            return run
        if not isinstance(payload, list):
            run.http_errors += 1
            return run
        run.repos_matched = [_repo_of(item) for item in payload if isinstance(item, dict)]
        return run

    # ── level 2: discussions on one repo ─────────────────────────────────

    def list_discussions(self, repo_id: str, run: HfRun, *, page: int = 0) -> list[dict]:
        """One page of a repo's discussions. Stored before anything is read."""
        response = self._get(
            DISCUSSIONS_PATH.format(repo=repo_id), {"p": page}, run
        )
        run.list_calls += 1
        if response is None:
            return []
        stored = self._store.put(response.content, namespace=RAW)
        run.discovery_refs.append(stored.ref)
        run.pages_stored += 1
        try:
            payload = response.json()
        except ValueError:
            run.http_errors += 1
            return []
        if not isinstance(payload, dict):
            run.http_errors += 1
            return []
        if isinstance(payload.get("count"), int):
            run.discussion_total = payload["count"]
        rows = payload.get("discussions") or []
        run.discussions_listed += len(rows)
        return [r for r in rows if isinstance(r, dict)]

    # ── level 3: one discussion, with its comments ───────────────────────

    def fetch_discussion(
        self, repo_id: str, num: int, run: HfRun
    ) -> tuple[HfDiscussion, str, str] | None:
        """Read one discussion. Its payload is the THREAD ROOT's `text_ref`.

        Each `comment` event is stored as its own payload here rather than in a
        later pass, so a comment's `text_ref` and the discussion's are written
        from the same response - two documents that could otherwise disagree
        about what a thread contained.
        """
        response = self._get(
            DISCUSSION_PATH.format(repo=repo_id, num=num), None, run
        )
        run.detail_calls += 1
        if response is None:
            return None
        stored = self._store.put(response.content, namespace=RAW)
        try:
            payload = response.json()
        except ValueError:
            run.http_errors += 1
            log.error("huggingface: discussion %s#%s is not JSON", repo_id, num)
            return None
        if not isinstance(payload, dict):
            run.http_errors += 1
            return None

        comments: list[HfComment] = []
        for event in payload.get("events") or []:
            if not isinstance(event, dict):
                continue
            if event.get("type") != COMMENT_EVENT:
                run.non_comment_events += 1
                continue
            comment = _comment_of(event, repo_id=repo_id, num=num)
            if comment is None:
                continue
            if comment.hidden:
                run.hidden_comments += 1
            if not comment.has_text:
                run.empty_comments += 1
            comments.append(comment)

        discussion = _discussion_of(payload, repo_id=repo_id, num=num, comments=comments)
        return discussion, stored.ref, stored.content_hash

    # ── the walk ─────────────────────────────────────────────────────────

    def harvest(
        self,
        query: str,
        terms=None,
        *,
        run: HfRun | None = None,
        max_repos: int = 3,
        max_discussions: int = 5,
    ) -> HfRun:
        """Repos -> discussions -> comments, bounded on every level.

        `max_repos` and `max_discussions` are budgets WE chose, so exceeding
        either sets `truncated_by = 'query-budget'` rather than
        `'result-ceiling'` - "we decided not to look further", which somebody
        can revisit, against "we were not allowed to", which they cannot.

        The bounds are not optional: this walk is 1 + R + (R x D) requests, so
        an unbounded run over a popular model is thousands of calls against an
        API that publishes no limit for us to respect.
        """
        from collect.adapters.queries.sieve import sieve

        run = self.search_repos(query, run=run)

        repos = run.repos_matched
        if terms is not None:
            # A repo that does not match is not walked. This is routing, not a
            # document verdict - no row is created or refused by it.
            repos = [r for r in repos if sieve(terms, r.sieve_text).passed]
        if len(repos) > max_repos:
            run.truncated_by = run.truncated_by or "query-budget"
            repos = repos[:max_repos]

        for repo in repos:
            run.repos_walked.append(repo.repo_id)
            listed = self.list_discussions(repo.repo_id, run)
            candidates = listed
            if terms is not None:
                candidates = [
                    d
                    for d in listed
                    if sieve(terms, str(d.get("title") or "")).passed
                ]
            if len(candidates) > max_discussions:
                run.truncated_by = run.truncated_by or "query-budget"
                candidates = candidates[:max_discussions]

            for row in candidates:
                num = row.get("num")
                if not isinstance(num, int):
                    continue
                fetched = self.fetch_discussion(repo.repo_id, num, run)
                if fetched is None:
                    continue
                discussion, ref, chash = fetched
                run.discussions.append(discussion)
                run.stored_discussions.append((discussion, ref, chash))

                for comment in discussion.comments:
                    if terms is not None:
                        verdict = sieve(terms, comment.sieve_text)
                        run.verdicts.append(verdict)
                        if not verdict.passed:
                            continue
                    put = self._store.put(comment.payload, namespace=RAW)
                    run.stored_comments.append((comment, put.ref, put.content_hash))

        run.finished_at = self._clock()
        return run

    # ── the write path ───────────────────────────────────────────────────

    def drafts(self, run: HfRun) -> list[DocumentDraft]:
        drafts: list[DocumentDraft] = []
        for discussion, ref, chash in run.stored_discussions:
            drafts.append(
                DocumentDraft(
                    source=DOCUMENT_SOURCE,
                    external_id=discussion.external_id,
                    url=discussion.url,
                    text_ref=ref,
                    content_hash=chash,
                    created_at=discussion.created_at,
                    author_external_id=discussion.author_external_id,
                    author_handle=discussion.author_handle,
                    lang=None,
                    thread_root_external_id=discussion.external_id,
                    # The Hub publishes no reaction or view count on a
                    # discussion, so there is nothing to record. Absent, not 0.
                    engagement={"score": None, "comments": len(discussion.comments)},
                )
            )
        for comment, ref, chash in run.stored_comments:
            drafts.append(
                DocumentDraft(
                    source=DOCUMENT_SOURCE,
                    external_id=comment.external_id,
                    url=comment.url,
                    text_ref=ref,
                    content_hash=chash,
                    created_at=comment.created_at,
                    author_external_id=comment.author_external_id,
                    author_handle=comment.author_handle,
                    lang=None,
                    thread_root_external_id=f"{comment.repo_id}#{comment.discussion_num}",
                    parent_external_id=f"{comment.repo_id}#{comment.discussion_num}",
                    engagement={"score": None, "comments": None},
                    status=(
                        "kept" if comment.has_text and not comment.hidden else "filtered"
                    ),
                    filter_reasons=_filter_reasons(comment),
                )
            )
        return drafts

    def write_documents(
        self,
        conn,
        run: HfRun,
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

    def counts(self, run: HfRun) -> SweepCounts:
        notes = [
            f"discovery is REPO-SCOPED: {len(run.repos_matched)} repo(s) matched, "
            f"{len(run.repos_walked)} walked, {run.discussions_listed} discussion(s) "
            "listed",
        ]
        if not run.repos_matched:
            notes.append(
                "no repo matched, so this platform has NO discussion surface for "
                "this surface — a structural absence, not silence about the model"
            )
        if run.non_comment_events:
            notes.append(
                f"{run.non_comment_events} event(s) were state changes rather than "
                "comments and are not documents"
            )
        if run.hidden_comments:
            notes.append(
                f"{run.hidden_comments} comment(s) are hidden by the platform and "
                "are stored as status='filtered'"
            )
        if run.empty_comments:
            notes.append(
                f"{run.empty_comments} comment event(s) carried no text at all and "
                "are stored as status='filtered' — a different state from hidden"
            )
        return SweepCounts(
            platform=SOURCE_ID,
            requests_issued=run.search_calls + run.list_calls + run.detail_calls,
            candidates=run.items_fetched,
            stored=run.items_kept,
            http_errors=run.http_errors,
            notes=notes,
        )


# ── parsing ──────────────────────────────────────────────────────────────


def _filter_reasons(comment: HfComment) -> tuple[str, ...] | None:
    """Every reason this comment is not evidence, not just the first.

    Both are recorded where both apply, for the reason `triage.triage` runs
    every gate rather than short-circuiting: a row that names one trigger when
    it hit two cannot be sorted by how close it came to passing.
    """
    reasons = []
    if comment.hidden:
        reasons.append(HIDDEN_REASON)
    if not comment.has_text:
        reasons.append(NO_TEXT)
    return tuple(reasons) or None


def _repo_of(item: dict[str, Any]) -> HfRepo:
    return HfRepo(
        repo_id=str(item.get("id") or ""),
        author_org=item.get("author"),
        downloads=item.get("downloads") if isinstance(item.get("downloads"), int) else None,
        likes=item.get("likes") if isinstance(item.get("likes"), int) else None,
        last_modified=item.get("lastModified"),
        tags=tuple(str(t) for t in (item.get("tags") or ())),
    )


def _comment_of(event: dict[str, Any], *, repo_id: str, num: int) -> HfComment | None:
    event_id = event.get("id")
    if not event_id:
        return None
    author = event.get("author") or {}
    data = event.get("data") or {}
    latest = data.get("latest") or {}
    return HfComment(
        event_id=str(event_id),
        repo_id=repo_id,
        discussion_num=num,
        # `_id` and not `name`: the id survives a rename and a reused name
        # merges two people, which is the worse of the two failures.
        author_external_id=str(author.get("_id")) if author.get("_id") else None,
        author_handle=author.get("name"),
        author_type=author.get("type"),
        created_at=event.get("createdAt"),
        body=latest.get("raw"),
        hidden=bool(data.get("hidden")),
        # sorted keys so the same comment re-fetched hashes identically and the
        # content-addressed store deduplicates it — `github.fetch_comments`'s
        # own construction, for the same reason.
        payload=json.dumps(event, sort_keys=True, ensure_ascii=False),
    )


def _discussion_of(
    payload: dict[str, Any], *, repo_id: str, num: int, comments: list[HfComment]
) -> HfDiscussion:
    author = payload.get("author") or {}
    return HfDiscussion(
        repo_id=repo_id,
        num=num,
        title=str(payload.get("title") or ""),
        author_external_id=str(author.get("_id")) if author.get("_id") else None,
        author_handle=author.get("name"),
        created_at=payload.get("createdAt"),
        status=payload.get("status"),
        is_pull_request=bool(payload.get("isPullRequest")),
        comments=tuple(comments),
    )


def huggingface_document_id(external_id: str) -> str:
    """`document.id` for an HF discussion or comment. The shared convention."""
    from collect.adapters.documents import document_id

    return document_id(DOCUMENT_SOURCE, external_id)


# ── the gated entry point ────────────────────────────────────────────────


def observe_huggingface_use() -> dict[str, object]:
    """This run's live observations for the terms gate."""
    # ⚠ `use_basis` ADDED 2026-09-15. This ruling NAMED
    # `internal-development-only` and did not check it, so on 2026-09-14 one
    # container refused Reddit and harvested here under the identical sentence.
    # `TermsRuling.basis` always said a named basis SHOULD be a live
    # precondition; the loader now refuses one that is not.
    return {"access_path": "api", **observe_use_basis()}


def harvester_for_source(source, *, rulings=None, **kwargs) -> HuggingFaceHarvester:
    """Build a harvester for a `source` row, ToS gate included.

    ⚠  IT WILL REFUSE UNTIL A RULING EXISTS. Draft in
       `docs/proposals/for-engineer-2-five-new-platform-sources.md`.
    """
    from collect.registry.assertions import assert_terms_reviewed, source_field

    source_id = source_field(source, "id", "?")
    assert_terms_reviewed(
        [source],
        rulings=rulings,
        observations={source_id: observe_huggingface_use()},
    )
    return HuggingFaceHarvester(**kwargs)
