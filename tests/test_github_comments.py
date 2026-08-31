"""Comment fetching: the voices half, and why it is not a tidiness fix.

`coverage_ratio` reads 0.0 on all 71 github contexts with 149 comments recorded
as `hidden_children_min`. That number is honest - we read the issue body and
none of the thread - and what the thread holds is DISTINCT AUTHORS.

`n_eff` counts VOICES, not claims. One engineer posting five times is one voice;
a second person writing "same here, on 4.8 as well" is a second voice on the
same cell. That is the whole reason to fetch comments, and it is why this is
measured in distinct authors rather than in comments.
"""

from __future__ import annotations

import json

import httpx

from collect.adapters.github import GitHubHarvester, QueryRun


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        # `content` is only read for well-formed payloads; an unparseable one is
        # represented by making `.json()` raise, exactly as httpx does.
        self.content = b"" if isinstance(payload, Exception) else json.dumps(payload).encode()

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _comment(cid: int, login: str, body: str = "same here"):
    return {
        "id": cid,
        "user": {"login": login},
        "body": body,
        "html_url": f"https://github.com/o/r/issues/1#issuecomment-{cid}",
    }


class _Harvester(GitHubHarvester):
    """Only `_get` and `_store` are exercised; nothing else is constructed."""

    def __init__(self, pages):
        self._pages = list(pages)
        self.calls = []
        self._store = _Store()

    def _get(self, url, *, params=None, search: bool):
        self.calls.append((url, dict(params or {}), search))
        if not self._pages:
            return _Response([])
        return self._pages.pop(0)


class _Store:
    def __init__(self):
        self.put_blobs = []

    def put(self, data, *, namespace=None):
        text = data if isinstance(data, str) else data.decode()
        self.put_blobs.append(text)

        class _P:
            ref = "raw/sha256/aa/bb/" + str(abs(hash(text)))[:16]
            content_hash = str(abs(hash(text)))[:16]
            size = len(text)
            already_present = False

        return _P()


def _run():
    return QueryRun.__new__(QueryRun)


class TestItSpendsTheCoreBucketNotSearch:
    """Measured `GET /rate_limit`: search 30/minute, core 5,000/hour, SEPARATE.

    Discovery spends search. Comments spend core, which is otherwise used only
    for issue bodies. If this were routed through the search limiter it would
    make comment fetching compete with discovery for a 30/minute budget - and
    the whole argument for doing it now is that it does not.
    """

    def test_every_request_is_marked_search_false(self):
        run = _run()
        run.rest_calls = 0
        run.http_errors = 0
        h = _Harvester([_Response([_comment(1, "ana")])])
        h.fetch_comments("https://api.github.com/repos/o/r/issues/1", run)
        assert h.calls, "no request issued"
        for _url, _params, search in h.calls:
            assert search is False, (
                "a comment fetch routed through the SEARCH limiter would compete "
                "with discovery for 30 requests a minute"
            )

    def test_it_counts_against_rest_calls(self):
        run = _run()
        run.rest_calls = 0
        run.http_errors = 0
        h = _Harvester([_Response([_comment(1, "ana")])])
        h.fetch_comments("https://api.github.com/repos/o/r/issues/1", run)
        assert run.rest_calls == 1


class TestEachCommentIsItsOwnStoredPayload:
    """The content_hash ruling, one level down from `text_ref` naming the issue.

    A page holding forty comments would make forty documents share a hash and
    break dedupe exactly the way pointing `text_ref` at a search response would.
    """

    def test_one_put_per_comment_not_one_per_page(self):
        run = _run()
        run.rest_calls = 0
        run.http_errors = 0
        h = _Harvester(
            [_Response([_comment(1, "ana"), _comment(2, "bo"), _comment(3, "cy")])]
        )
        stored = h.fetch_comments("https://api.github.com/repos/o/r/issues/1", run)
        assert len(stored) == 3
        assert len(h._store.put_blobs) == 3
        assert len({s.content_hash for s in stored}) == 3

    def test_the_author_handle_is_carried_because_n_eff_counts_voices(self):
        run = _run()
        run.rest_calls = 0
        run.http_errors = 0
        h = _Harvester([_Response([_comment(1, "ana"), _comment(2, "ana"),
                                   _comment(3, "bo")])])
        stored = h.fetch_comments("https://api.github.com/repos/o/r/issues/1", run)
        # Three comments, TWO voices. That distinction is the point.
        assert len(stored) == 3
        assert len({s.author_handle for s in stored}) == 2


class TestFailureIsCoverageNotAnException:
    """A thread whose comments could not be fetched is a coverage fact.

    The issue body is still worth keeping, so this returns what it has and
    counts the failure rather than losing the document.
    """

    def test_a_non_200_returns_what_it_has_and_counts_the_error(self):
        run = _run()
        run.rest_calls = 0
        run.http_errors = 0
        h = _Harvester([_Response([], status_code=502)])
        assert h.fetch_comments("https://api.github.com/repos/o/r/issues/1", run) == []
        assert run.http_errors == 1

    def test_a_transport_error_does_not_propagate(self):
        class _Boom(_Harvester):
            def _get(self, url, *, params=None, search):
                raise httpx.ConnectError("no route")

        run = _run()
        run.rest_calls = 0
        run.http_errors = 0
        h = _Boom([])
        assert h.fetch_comments("https://api.github.com/repos/o/r/issues/1", run) == []
        assert run.http_errors == 1

    def test_unparseable_json_is_counted_not_raised(self):
        run = _run()
        run.rest_calls = 0
        run.http_errors = 0
        h = _Harvester([_Response(ValueError("not json"))])
        assert h.fetch_comments("https://api.github.com/repos/o/r/issues/1", run) == []
        assert run.http_errors == 1


class TestPaging:
    """One page holds every comment in the corpus today. That is a fact about
    80 documents, not a property of GitHub, so paging exists anyway."""

    def test_a_short_page_ends_the_fetch(self):
        run = _run()
        run.rest_calls = 0
        run.http_errors = 0
        h = _Harvester([_Response([_comment(1, "ana")]), _Response([_comment(2, "bo")])])
        stored = h.fetch_comments("https://api.github.com/repos/o/r/issues/1", run)
        assert len(stored) == 1, "a page shorter than per_page means there is no next"
        assert run.rest_calls == 1

    def test_a_full_page_asks_for_the_next(self):
        full = [_comment(i, f"u{i}") for i in range(GitHubHarvester.COMMENTS_PER_PAGE)]
        run = _run()
        run.rest_calls = 0
        run.http_errors = 0
        h = _Harvester([_Response(full), _Response([_comment(999, "zz")])])
        stored = h.fetch_comments("https://api.github.com/repos/o/r/issues/1", run)
        assert len(stored) == GitHubHarvester.COMMENTS_PER_PAGE + 1
        assert [c[1]["page"] for c in h.calls] == [1, 2]
