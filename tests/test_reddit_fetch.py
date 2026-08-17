"""The Reddit fetch path, and the assembly it refuses to fake.

Driven through `httpx.MockTransport` against recorded shapes, so the suite
does not depend on RapidAPI being up or on quota. The shapes are the ones
measured on 2026-08-14 — `kind`/`data` envelopes, `t2_`/`t3_` fullnames,
`created_utc` as an epoch float — reduced to the fields the adapter reads.

The two that matter most here are the ones that were measured rather than
assumed: `'data not found'` is zero results and not an error, and the page is
stored BEFORE the sieve runs.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest

from collect.adapters.queries.contract import TermSet
from collect.adapters.reddit import (
    AssemblyNotBuilt,
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


# ── 'data not found' is zero results ──────────────────────────────────────


def test_no_matches_is_not_an_error(tmp_path):
    """The collision this project keeps finding, avoided by measurement.

    A nonsense query returns success:false / 'data not found' with HTTP 200.
    Reading it as a failure makes "nobody discussed this" indistinguishable
    from "the call broke".
    """
    run = harvester(responder(NO_RESULTS), tmp_path).search("zzzz nonexistent")
    assert run.posts == []
    assert run.http_errors == 0, "not an error"
    assert run.exhausted is True
    assert run.truncated_by is None


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


# ── the refusal ───────────────────────────────────────────────────────────


def test_assembly_refuses_and_says_what_is_missing(tmp_path):
    """A stub that returned a partial selection would be the silent failure.

    'The top 5 children' and 'the top 5 of the 4% we fetched' are different
    claims, and once written to a row they are indistinguishable.
    """
    h = harvester(responder(page([post()])), tmp_path)
    with pytest.raises(AssemblyNotBuilt) as excinfo:
        h.assemble_thread(_a_post())

    message = str(excinfo.value)
    assert "4%" in message and "4,833" in message, "the coverage measurement"
    assert "SIBLINGS" in message, "why the selection cannot be bounded"
    assert "126 report none" in message, "coverage is a lower bound"
    assert "issue #5" in message, "where the columns are proposed"


def test_the_refusal_does_not_still_blame_the_missing_scorer(tmp_path):
    """The previous version of this test asserted the MENTION, not the CLAIM.

    It read `assert "specificity_score" in message` with the comment "the
    scorer that does not exist". That passes whether or not the scorer exists,
    so when `collect/triage/specificity.py` landed the refusal went on
    asserting something false and 878 tests stayed green. Same shape as every
    other defect in this repo: a check that cannot fail for the reason it was
    written.

    So this asserts the state of the world instead of the text.
    """
    import importlib

    scorer = importlib.import_module("collect.triage.specificity")
    assert callable(scorer.score_document), "the scorer exists"

    h = harvester(responder(page([post()])), tmp_path)
    with pytest.raises(AssemblyNotBuilt) as excinfo:
        h.assemble_thread(_a_post())
    message = str(excinfo.value)

    assert "no implementation" not in message, (
        "the refusal claims the scorer is unimplemented and it is implemented"
    )
    assert "fetch_comments" in message, (
        "comment fetching landed, so the refusal must stop implying the children "
        "are unavailable and rest only on the bounding problem"
    )
    assert "cannot be bounded" in message, (
        "the ONE remaining reason must be stated, or the refusal has lost its "
        "grounds while still refusing"
    )

    # An earlier version of this test also asserted `"no longer the reason" in
    # message`. That pinned a PHRASE, and it broke the moment the refusal was
    # legitimately reworded to say two reasons had gone rather than one — a test
    # failing because prose improved is the same weakness in the other
    # direction, and the convention in tests/conftest.py says assert the world.
    # What is asserted above is the world: the scorer imports, the fetcher is
    # named, the surviving reason is stated, and the retired claim is absent.


def test_the_columns_the_refusal_calls_missing_are_genuinely_missing():
    """The other half of asserting the claim.

    The refusal rests on three `thread_context` columns being unavailable. If
    issue #5 lands them and nobody revisits this, the refusal starts citing a
    gap that has been filled — the failure this file just had. Read from the
    contract rather than trusted.
    """
    from collect.config import CONTRACT_DIR

    schema = (CONTRACT_DIR / "tables.sql").read_text(encoding="utf-8")
    for column in ("observed_children", "hidden_children_min",
                   "hidden_branches_unsized", "coverage_ratio"):
        assert column not in schema, (
            f"{column} is in contract/tables.sql now, so the refusal's remaining "
            "reason is stale and assemble_thread needs revisiting"
        )


def test_an_unset_host_refuses_rather_than_guessing(tmp_path, monkeypatch):
    from collect import config
    from collect.adapters.reddit import RedditConfigError

    # Emptied, not deleted: `settings()` reloads .env, and dotenv only
    # declines to override a key that is already in os.environ. Deleting it
    # would let the real .env value back in and the test would pass for the
    # wrong reason.
    monkeypatch.setenv("RAPIDAPI_HOST", "")
    config.settings.cache_clear()
    with pytest.raises(RedditConfigError, match="bare host"):
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
