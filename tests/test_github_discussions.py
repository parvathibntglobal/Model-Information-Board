"""GitHub Discussions (2026-10-26): searched, sieved, stored as GitHub documents.

No network: a recorded GraphQL transport. What matters is that a discussion
becomes a document exactly as an issue does - `owner/repo#N`, the numeric user
id as its author, a payload `github_issue_prose` reads - and that a refused or
throttled search is recorded as one, never as "no discussions".
"""

from __future__ import annotations

import inspect
import json
import pathlib

import httpx
import pytest

from collect.adapters import github as gh
from collect.adapters.github_discussions import (
    MAX_QUERY_CHARS,
    DiscussionHarvester,
    discussion_query,
)
from collect.assemble.prose import github_issue_prose
from collect.rawstore import RawStore

ROOT = pathlib.Path(__file__).resolve().parents[1]

NODES = [
    {"number": 41, "title": "Benchmarks: DeepSeek V4 Flash on a 3090",
     "body": "Getting 68 tok/s decode with deepseek-v4-flash at 16k context.",
     "url": "https://github.com/ggml-org/llama.cpp/discussions/41",
     "createdAt": "2026-10-25T10:00:00Z", "upvoteCount": 7,
     "repository": {"nameWithOwner": "ggml-org/llama.cpp"}, "category": {"name": "Q&A"},
     "author": {"login": "someone", "databaseId": 12345}, "comments": {"totalCount": 4}},
    {"number": 9, "title": "Flash attention question", "body": "Unrelated to any model name.",
     "url": "https://github.com/x/y/discussions/9", "createdAt": "2026-10-24T10:00:00Z",
     "upvoteCount": 0, "repository": {"nameWithOwner": "x/y"}, "category": {"name": "General"},
     "author": {"login": "other", "databaseId": 777}, "comments": {"totalCount": 0}},
    {},  # an item the token cannot see comes back empty
]
VARIANTS = ["DeepSeek V4 Flash", "deepseek-v4-flash"]


def _harvester(tmp_path, handler, slept=None):
    client = httpx.Client(transport=httpx.MockTransport(handler))

    class _NoWait:
        def wait(self, url):
            return 0.0

    return DiscussionHarvester(client=client, store=RawStore(tmp_path, remote=None),
                               limiter=_NoWait(),
                               sleeper=(slept.append if slept is not None else lambda s: None))


def _ok(request):
    sent = json.loads(request.content)
    assert "type: DISCUSSION" in sent["query"]
    return httpx.Response(200, json={"data": {
        "search": {"discussionCount": 945, "nodes": NODES},
        "rateLimit": {"cost": 1, "remaining": 4999, "resetAt": "2026-10-26T08:00:00Z"}}})


def test_the_query_is_one_spelling_newest_first_and_bounded():
    q = discussion_query("DeepSeek V4 Flash")
    assert q.startswith('"') and "in:title,body" in q and "sort:created-desc" in q
    assert len(q) <= MAX_QUERY_CHARS
    with pytest.raises(ValueError):
        discussion_query("x" * MAX_QUERY_CHARS)


def test_a_hit_that_names_the_model_is_stored_as_a_github_document(tmp_path):
    h = _harvester(tmp_path, _ok)
    run = h.harvest("DeepSeek V4 Flash", VARIANTS)
    assert run.total_count == 945
    assert run.retrieved == 2, "the empty node is not a hit"
    assert run.rejected == 1, "a hit that names no spelling of the model is not kept"
    [stored] = run.stored
    assert stored.external_id == "ggml-org/llama.cpp#41"
    assert stored.hit.author_external_id == "12345", "the numeric id, never the login"
    blob = h._store.get(stored.ref).decode("utf-8")
    assert "someone" not in blob, "the login is not retained"
    prose = github_issue_prose(blob)
    assert prose.startswith("Benchmarks: DeepSeek V4 Flash") and "68 tok/s" in prose


def test_a_refused_query_is_an_error_not_an_empty_board(tmp_path):
    h = _harvester(tmp_path, lambda r: httpx.Response(200, json={"errors": [{"message": "bad"}]}))
    run = h.harvest("DeepSeek V4 Flash", VARIANTS)
    assert run.http_errors == 1 and run.total_count is None and not run.stored


def test_a_throttle_is_retried_once_then_recorded(tmp_path):
    slept: list[float] = []
    throttled = httpx.Response(403, headers={"x-ratelimit-remaining": "0", "retry-after": "3"},
                               text="API rate limit exceeded")
    h = _harvester(tmp_path, lambda r: throttled, slept)
    run = h.harvest("DeepSeek V4 Flash", VARIANTS)
    assert run.search_calls == 2 and slept == [3.0]
    assert run.rate_limited and run.http_errors == 1 and run.total_count is None


def test_the_keep_cap_stops_at_the_newest(tmp_path):
    def many(request):
        nodes = [dict(NODES[0], number=n, url=f"https://github.com/a/b/discussions/{n}")
                 for n in range(1, 6)]
        search = {"discussionCount": 5, "nodes": nodes}
        return httpx.Response(200, json={"data": {"search": search}})

    client = httpx.Client(transport=httpx.MockTransport(many))
    h = DiscussionHarvester(client=client, store=RawStore(tmp_path, remote=None),
                            max_keep_per_query=2, sleeper=lambda s: None)
    h._limiter = type("W", (), {"wait": lambda self, u: 0.0})()
    run = h.harvest("DeepSeek V4 Flash", VARIANTS)
    assert [s.hit.number for s in run.stored] == [1, 2]


def test_issues_and_discussions_share_one_writer():
    """The method delegates, so the two arms cannot drift apart on authors,
    conflicts or provenance."""
    src = inspect.getsource(gh.GitHubHarvester.write_documents)
    assert "return write_issue_documents(" in src
    assert "INSERT INTO document" not in src


def test_the_fetch_names_the_arm_in_and_out_of_scope():
    src = (ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
    start = src.index('        if "github" in sources:')
    block = src[start:src.index('        if "reddit" in sources:')]
    assert "harvest_github_discussions(" in block
    assert block.count('"E2G", "Harvest · GitHub Discussions"') == 2, "error and skipped both named"
