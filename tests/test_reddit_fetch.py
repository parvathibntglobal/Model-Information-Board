"""The Reddit fetch path, and the assembly it refuses to fake.

Driven through `httpx.MockTransport` against recorded shapes, so the suite
does not depend on RapidAPI being up or on quota. The shapes are the ones
measured on 2026-08-14 — `kind`/`data` envelopes, `t2_`/`t3_` fullnames,
`created_utc` as an epoch float — reduced to the fields the adapter reads.

The two that matter most here are the ones that were measured rather than
assumed: the page is stored BEFORE the sieve runs, and `'data not found'` is
**transient rather than zero results** — which is a correction, made 2026-08-28
after a query with 175 results returned it and then recovered on five
consecutive retries. This file asserted the old reading until then.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest

from collect.adapters.queries.contract import TermSet
from collect.adapters.reddit import (
    RedditHarvester,
    RedditPost,
    author_external_id,
)
from collect.limiter import HostLimiter
from collect.rawstore import RAW, RawStore, parse_ref

UA = "modelboard/0.1 (+https://modelboard.invalid/about)"
HOST = "reddit34.p.rapidapi.com"


def post(**overrides):
    data = {
        "name": "t3_abc123",
        "id": "abc123",
        "title": "Claude dropped the cancellation clause from every summary",
        "selftext": "We moved the digest job over and it lost the detail.",
        "author": "someone",
        "author_fullname": "t2_zzz999",
        "subreddit": "LocalLLaMA",
        "permalink": "/r/LocalLLaMA/comments/abc123/x/",
        "url": "https://www.reddit.com/r/LocalLLaMA/comments/abc123/x/",
        "created_utc": 1786702495.0,
        "score": 42,
        "num_comments": 7,
        "upvote_ratio": 0.93,
    }
    data.update(overrides)
    return {"kind": "t3", "data": data}


def page(posts, cursor=None):
    return {"success": True, "data": {"posts": posts, "cursor": cursor}}


NO_RESULTS = {"success": False, "data": "data not found"}


def harvester(handler, tmp_path, **kwargs):
    from collect.http import build_client

    client = build_client(
        user_agent=UA,
        transport=httpx.MockTransport(handler),
        headers={"x-rapidapi-key": "test", "x-rapidapi-host": HOST},
    )
    return RedditHarvester(
        client=client,
        store=RawStore(tmp_path / "raw_store"),
        limiter=HostLimiter(min_interval=0.0, clock=lambda: 0.0, sleeper=lambda _s: None),
        clock=lambda: datetime(2026, 8, 14, 9, 0, tzinfo=UTC),
        sleeper=lambda _s: None,
        **kwargs,
    )


def responder(*pages, status=200):
    """Serves each page in turn, then repeats the last."""
    seen = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-rapidapi-host"] == HOST
        assert request.headers["User-Agent"] == UA, "the UA gate is in the loop"
        index = min(seen["n"], len(pages) - 1)
        seen["n"] += 1
        body = pages[index]
        return httpx.Response(
            status,
            json=body,
            headers={"x-ratelimit-requests-remaining": "999900"},
        )

    return handler


@pytest.fixture(autouse=True)
def _host_configured(monkeypatch):
    from collect import config

    monkeypatch.setenv("RAPIDAPI_HOST", f"https://{HOST}/getPopularPosts?sort=new")
    monkeypatch.setenv("RAPIDAPI_KEY", "test")
    config.settings.cache_clear()
    yield
    config.settings.cache_clear()


# ── the shape ─────────────────────────────────────────────────────────────


def test_a_post_flattens_out_of_the_kind_data_envelope(tmp_path):
    run = harvester(responder(page([post()])), tmp_path).search("claude")
    assert len(run.posts) == 1
    p = run.posts[0]
    assert p.external_id == "t3_abc123", "the fullname, not the bare id"
    assert p.subreddit == "LocalLLaMA"
    assert p.engagement == {"score": 42, "comments": 7, "upvote_ratio": 0.93}


def test_created_at_is_a_real_utc_timestamp(tmp_path):
    """The measurement that kept this platform viable.

    A relative string would leave every Reddit document with a NULL
    created_at, and FR-4's window resolution and the 30-day decay half-life
    both read it.
    """
    run = harvester(responder(page([post()])), tmp_path).search("claude")
    created = run.posts[0].created_at
    # Round-tripped rather than hand-computed: the property that matters is
    # that no timezone was invented on the way through, and a hand-written
    # wall-clock value tests my arithmetic instead.
    assert created.timestamp() == 1786702495.0
    assert created.tzinfo is UTC
    assert created.year == 2026


def test_a_missing_timestamp_stays_missing(tmp_path):
    """Rule 6. Never the fetch time — a guessed date resolves the wrong window."""
    run = harvester(responder(page([post(created_utc=None)])), tmp_path).search("claude")
    assert run.posts[0].created_at is None


# ── author identity ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value,expected",
    [
        ("t2_zzz999", "t2_zzz999"),      # a post's author_fullname
        ("zzz999", "t2_zzz999"),         # getProfile's bare `id`
        (None, None),
        ("", None),
    ],
)
def test_the_author_id_is_canonicalised(value, expected):
    """`getProfile` returns `id` bare; posts return it prefixed.

    Taking each verbatim writes two `author` rows for one engineer, which
    splits a voice — and FR-17 then counts it twice believing it counts once.
    """
    assert author_external_id(value) == expected


def test_the_canonical_id_comes_off_a_post_too():
    assert author_external_id(_a_post()) == "t2_zzz999"


def _a_post() -> RedditPost:
    from collect.adapters.reddit import _post_of

    return _post_of(post())


# ── 'data not found' is TRANSIENT, not zero results ───────────────────────


def test_an_empty_response_is_retried_before_it_is_believed(tmp_path):
    """It is not an error, and it is not exhaustion either.

    **This test asserted `run.exhausted is True` until 2026-08-28, and that was
    the falsified belief rather than a wrong assertion.** Measured that day: a
    query which had just returned 175 candidates came back `success: false` /
    `data: "data not found"`, then returned 25 posts on five consecutive
    retries. The body is identical to a genuine zero, so it cannot be read as
    one.

    What it cost before it was found: two of seventeen surfaces in a model-only
    sweep reported zero candidates for models that demonstrably have discussion.
    A surface that silently returns nothing looked exactly like a model nobody
    discusses.
    """
    run = harvester(responder(NO_RESULTS), tmp_path).search("zzzz nonexistent")
    assert run.posts == []
    assert run.http_errors == 0, "still not an error"
    # THE CLAIM THAT CHANGED. `exhausted` is a statement about the platform
    # running out of results; `empty_response` is a statement about us being
    # unable to read a page. Only the second is defensible here.
    assert run.exhausted is False
    assert run.empty_response == 1
    assert run.empty_retries == 2, "retried before believed, and the cost counted"
    assert run.truncated_by is None


def test_a_transient_empty_response_recovers_on_retry(tmp_path):
    """The case the retry exists for: empty once, then real posts."""
    # `responder` serves each page in turn and then repeats the last, so this is
    # exactly: empty first, real posts on the retry.
    run = harvester(responder(NO_RESULTS, page([post()])), tmp_path).search("opus 4.8")
    assert len(run.posts) == 1, "the retry's posts, not the empty page's"
    assert run.empty_response == 0, "it recovered, so nothing was unreadable"
    assert run.empty_retries == 1
    # The RETRY's page is the one stored. Storing the empty response would file a
    # discovery_ref that does not contain the documents it is provenance for.
    assert run.pages_stored == 1


def test_a_real_http_error_is_an_error(tmp_path):
    run = harvester(responder(page([]), status=500), tmp_path).search("claude")
    assert run.http_errors == 1
    assert run.posts == []


def test_a_429_is_a_throttle_and_never_an_empty_result(tmp_path):
    """No Retry-After is sent, so the backoff is assumed — and counted."""
    run = harvester(responder({}, status=429), tmp_path).search("claude")
    assert run.rate_limited == 1
    assert run.truncated_by == "rate-limit"
    assert run.backoff_seconds > 0
    assert run.total_count is None, "a throttled query never learned a total"


# ── store before sieve ────────────────────────────────────────────────────


def test_the_page_is_stored_before_anything_is_sieved(tmp_path):
    """The recoverability argument behind the locality window rests on this."""
    h = harvester(responder(page([post()])), tmp_path)
    run = h.search("claude")

    assert run.pages_stored == 1
    namespace, _ = parse_ref(run.discovery_refs[0])
    assert namespace is RAW
    stored = json.loads(h._store.get(run.discovery_refs[0]))
    assert stored["data"]["posts"][0]["data"]["id"] == "abc123"


def test_a_rejected_post_is_still_in_the_stored_page(tmp_path):
    """Sieve, then fetch — but the text of what was rejected is on disk."""
    h = harvester(responder(page([post(title="unrelated"), post()])), tmp_path)
    run = h.search("claude")
    terms = TermSet(
        subject=("claude",), topic=("summary",), signal=("lost the detail",)
    ).substitute("claude")
    h.sieve_run(run, terms)

    assert len(run.posts) == 2
    assert len(run.survivors) < 2, "at least one was rejected"
    stored = json.loads(h._store.get(run.discovery_refs[0]))
    assert len(stored["data"]["posts"]) == 2, "both are still stored"


def test_pages_fetched_and_stored_are_both_recorded(tmp_path):
    """They differ once max_pages rises, and the difference is the claim.

    `harvest_run` has nowhere to put them yet — proposed on #5 — so they are
    carried in the run and returned homeless rather than dropped.
    """
    run = harvester(responder(page([post()])), tmp_path).search("claude")
    fields = run.harvest_run_fields()
    assert fields["pages_fetched"] == fields["pages_stored"] == 1


# ── what the schema cannot hold ───────────────────────────────────────────


def test_the_run_reports_no_total_rather_than_zero(tmp_path):
    """Reddit reports no count at all. None means unknown, 0 means no matches."""
    run = harvester(responder(page([post()])), tmp_path).search("claude")
    assert run.total_count is None


def test_quota_is_carried_homeless_rather_than_called_a_rate_limit(tmp_path):
    """'rate-limit' means retry; a monthly cap means stop until the reset.

    `truncated_by` has no 'quota' value, so this adapter refuses to mislabel
    it and returns the fact separately — the same shape as the blog adapter's
    `outcome`. Proposed on #5.
    """
    run = harvester(responder(page([post()])), tmp_path).search("claude")
    fields = run.harvest_run_fields()
    assert "quota_exhausted" in fields
    assert fields["truncated_by"] != "quota", "not a legal value in the CHECK"
    assert run.quota_remaining == 999900, "read from the response header"


# ── the whole rate-limit triple ───────────────────────────────────────────


def test_every_rate_limit_header_is_captured_not_only_remaining(tmp_path):
    """`-limit` and `-reset` reach the run, not just `-remaining`.

    The regression this pins: for a fortnight the adapter read `-remaining` and
    nothing else, so `x-ratelimit-requests-limit: 1000000` sat in the module
    docstring as an unread constant and collected five citations, against a plan
    believed to be 500,000. Read live on 2026-08-18 it was in fact 1,000,000 —
    which is the uncomfortable outcome, because a right answer from a wrong
    method is the one nobody goes back and checks.
    """
    from collect.adapters.reddit import _QUOTA_HEADERS

    headers = {
        "x-ratelimit-requests-remaining": "998660",
        "x-ratelimit-requests-limit": "1000000",
        "x-ratelimit-requests-reset": "2064366",
    }
    assert set(headers) == set(_QUOTA_HEADERS), (
        "a header was added to the map without a case here"
    )

    def handler(request):
        return httpx.Response(200, json=page([post()]), headers=headers)

    run = harvester(handler, tmp_path).search("claude")
    assert run.quota_remaining == 998660
    assert run.quota_limit == 1000000, "the limit is an observation, not a constant"
    assert run.quota_reset_seconds == 2064366, "seconds, not a computed date"


def test_an_absent_limit_header_stays_none_rather_than_becoming_zero(tmp_path):
    """Rule 6 at the layer that would make an unread limit look like no limit."""

    def handler(request):
        return httpx.Response(
            200,
            json=page([post()]),
            headers={"x-ratelimit-requests-remaining": "998660"},
        )

    run = harvester(handler, tmp_path).search("claude")
    assert run.quota_remaining == 998660
    assert run.quota_limit is None, "absent is not 0 and not 1,000,000"
    assert run.quota_reset_seconds is None


def test_the_quota_sink_forwards_every_field_get_writes(tmp_path):
    """A comment fetch must not silently drop a header a search keeps.

    `_quota_sink` hands `_get` a throwaway `_Sink`, so `setattr` for a field with
    no forwarder SUCCEEDS and the value vanishes. Nothing raises. This asserts
    the sink covers the whole map, so the next header added to `_QUOTA_HEADERS`
    cannot be captured on searches and lost on comment fetches.
    """
    from datetime import UTC, datetime

    from collect.adapters.reddit import _QUOTA_HEADERS, ThreadFetch, _quota_sink

    fetch = ThreadFetch(thread_url="https://x", started_at=datetime.now(tz=UTC))
    sink = _quota_sink(fetch)

    for index, attribute in enumerate(_QUOTA_HEADERS.values(), start=1):
        setattr(sink, attribute, index)
        assert getattr(fetch, attribute) == index, (
            f"_quota_sink drops {attribute}: it set an attribute on the throwaway "
            f"_Sink instead of forwarding to ThreadFetch, and nothing raised"
        )


# ── the refusal ───────────────────────────────────────────────────────────


def test_an_unset_host_refuses_rather_than_guessing(tmp_path, monkeypatch):
    """UNCONFIGURED NOW MEANS BOTH VARIABLES, and that is the fix, not a leak.

    This used to empty `RAPIDAPI_HOST` alone, because that was the only setting
    Reddit read. It is not any more: `REDDIT_PROVIDER` supplies the host, added
    after .env declared `RAPIDAPI_HOST` twice - once per provider - and the last
    declaration won, sending Reddit's paths to X's host for a 404 on every
    search. Emptying one of two sources no longer leaves the arm unconfigured,
    so the test empties both.
    """
    from collect import config
    from collect.adapters.reddit import RedditConfigError

    # Emptied, not deleted: `settings()` reloads .env, and dotenv only
    # declines to override a key that is already in os.environ. Deleting it
    # would let the real .env value back in and the test would pass for the
    # wrong reason.
    monkeypatch.setenv("RAPIDAPI_HOST", "")
    monkeypatch.setenv("REDDIT_PROVIDER", "")
    config.settings.cache_clear()
    with pytest.raises(RedditConfigError, match="REDDIT_PROVIDER"):
        harvester(responder(page([])), tmp_path)
    config.settings.cache_clear()


def test_the_shared_host_variable_is_refused_when_it_names_another_vendor(tmp_path, monkeypatch):
    """The 404 that read as a moved endpoint.

    Both hosts are real and both answer, so no response could distinguish "the
    Reddit API changed" from "we asked X's host for Reddit's path". The refusal
    is what makes the difference visible without a request.
    """
    from collect import config
    from collect.adapters.reddit import RedditConfigError

    monkeypatch.setenv("REDDIT_PROVIDER", "")
    monkeypatch.setenv("RAPIDAPI_HOST", "twitter241.p.rapidapi.com")
    config.settings.cache_clear()
    with pytest.raises(RedditConfigError, match="404"):
        harvester(responder(page([])), tmp_path)
    config.settings.cache_clear()


def test_a_full_url_in_the_host_variable_is_normalised(tmp_path):
    """.env carries a full endpoint URL today; a host header holding one
    matches no route, and the failure would read as 'the API is down'."""
    from collect.config import settings

    assert settings().rapidapi_host == HOST


def test_an_unknown_sort_is_refused_locally(tmp_path):
    h = harvester(responder(page([post()])), tmp_path)
    with pytest.raises(ValueError, match="sort must be one of"):
        h.search("claude", sort="BEST")
