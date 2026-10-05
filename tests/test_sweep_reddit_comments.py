"""The listing sweep stores each survivor's comments, not only its post.

Until 2026-10-05 `collect/ops/sweep_reddit.py` wrote posts and nothing under
them, so every thread it produced assembled as `post_body_only`: 17 of the 1,507
roots it wrote on staging had any comment document. These tests pin the four
outcomes of the comment fetch apart, because one of them - a FAILED fetch - is
an absence we caused and must not read like a thread nobody answered.

No database: the harvester, the writer and the ledger are fakes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from collect.adapters.reddit import ThreadFetch
from collect.ops import sweep_reddit as mod


@dataclass
class Post:
    external_id: str
    sieve_text: str = "a post about a model"
    raw: dict = field(default_factory=dict)


@dataclass
class Comment:
    external_id: str
    raw: dict = field(default_factory=dict)


@dataclass
class Run:
    posts: list
    query: str = "r/ClaudeAI"
    survivors: list = field(default_factory=list)
    verdicts: list = field(default_factory=list)
    pages_fetched: int = 1
    http_errors: int = 0
    rate_limited: int = 0
    quota_exhausted: bool = False
    quota_remaining: int | None = None
    quota_limit: int | None = None
    exhausted: bool = True
    truncated_by: str | None = None

    def harvest_run_fields(self) -> dict:
        return {}


class Stored:
    def __init__(self, n: int) -> None:
        self.ref = f"raw/{n}"
        self.content_hash = f"h{n}"


class Store:
    def __init__(self) -> None:
        self.puts: list[bytes] = []

    def put(self, data: bytes, namespace=None) -> Stored:
        self.puts.append(data)
        return Stored(len(self.puts))


def _fetch(**kw) -> ThreadFetch:
    return ThreadFetch(thread_url="u", started_at=datetime.now(UTC), **kw)


class Harvester:
    def __init__(self, posts, fetches) -> None:
        self._store = Store()
        self._posts = posts
        self._fetches = fetches
        self.asked: list[str] = []

    def list_subreddit(self, name, *, pages, sort):
        return Run(posts=list(self._posts))

    def fetch_comments(self, post):
        self.asked.append(post.external_id)
        return self._fetches[post.external_id]


class Conn:
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


class Contract:
    sweep_subreddits = {
        "members": ["ClaudeAI"],
        "pages_per_subreddit": 1,
        "posts_per_page": 25,
        "sort": "new",
    }


@dataclass
class Verdict:
    passed: bool = True
    topic: bool = False
    signal: bool = False


@pytest.fixture
def writes(monkeypatch):
    calls: list[dict] = []

    def write_documents(conn, items, *, retrieval_provenance, harvest_run_id, refs):
        calls.append({"items": list(items), "run": harvest_run_id, "refs": dict(refs)})
        return {"documents_inserted": len(items)}

    class Opened:
        id = 77

    import importlib

    # The package re-exports the FUNCTION `sieve`, shadowing the submodule on
    # attribute access, so the module is fetched by name.
    sieve_mod = importlib.import_module("collect.adapters.queries.sieve")
    import collect.adapters.reddit_write as writer_mod
    import collect.ops.ledger as ledger_mod

    monkeypatch.setattr(writer_mod, "write_documents", write_documents)
    monkeypatch.setattr(ledger_mod, "open_harvest_run", lambda conn, fields: Opened())
    monkeypatch.setattr(ledger_mod, "close_harvest_run", lambda *a, **k: None)
    monkeypatch.setattr(sieve_mod, "sieve", lambda terms, text: Verdict())
    monkeypatch.setattr(mod, "_seated_term_sets", lambda conn: {"m": ((), (object(),))})
    monkeypatch.setattr(mod, "sweep_budget", lambda cadence: (900, 35))
    return calls


def test_every_survivor_gets_a_comment_fetch_and_its_comments_are_written(writes):
    posts = [Post("t3_a"), Post("t3_b"), Post("t3_c"), Post("t3_d")]
    harvester = Harvester(posts, {
        "t3_a": _fetch(comments=(Comment("t1_x"), Comment("t1_y"))),
        "t3_b": _fetch(),                       # the platform says: no comments
        "t3_c": _fetch(http_errors=1),          # we failed to ask
        "t3_d": _fetch(not_a_thread=True),      # a link post, no thread
    })

    report = mod.sweep_reddit(Conn(), harvester, contract=Contract())

    assert harvester.asked == ["t3_a", "t3_b", "t3_c", "t3_d"]
    # First write: the posts. Second: one thread, post first, carrying the run id.
    assert [p.external_id for p in writes[0]["items"]] == ["t3_a", "t3_b", "t3_c", "t3_d"]
    assert len(writes) == 2
    thread = writes[1]
    assert [i.external_id for i in thread["items"]] == ["t3_a", "t1_x", "t1_y"]
    assert thread["run"] == 77
    assert set(thread["refs"]) == {"t3_a", "t1_x", "t1_y"}

    assert report.comment_requests == 3          # the link post costs no request
    assert report.threads_with_comments == 1
    assert report.threads_without_comments == 1
    assert report.threads_not_a_thread == 1
    assert report.comment_fetch_failures == ["t3_c"]
    assert report.http_errors == 1


def test_a_failed_fetch_is_named_in_the_summary(writes):
    harvester = Harvester([Post("t3_c")], {"t3_c": _fetch(http_errors=1)})
    report = mod.sweep_reddit(Conn(), harvester, contract=Contract())
    text = report.summary()
    assert "1 FAILED fetch(es)" in text
    assert "t3_c" in text


def test_comment_payloads_are_stored_as_the_platform_sent_them(writes):
    harvester = Harvester(
        [Post("t3_a", raw={"title": "p"})],
        {"t3_a": _fetch(comments=(Comment("t1_x", raw={"body": "café"}),))},
    )
    mod.sweep_reddit(Conn(), harvester, contract=Contract())
    # post payload, then the comment's - house spelling, non-ASCII kept.
    assert harvester._store.puts[-1] == '{"body": "café"}'.encode()
