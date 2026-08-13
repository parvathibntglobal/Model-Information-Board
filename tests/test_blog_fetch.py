"""The fetch path: conditional GET, two raw artifacts, and the homeless outcome.

Driven entirely through `httpx.MockTransport` against the recorded fixtures in
`fixtures/blog/`, so the suite does not depend on anyone's site being up. The
client is built by `build_client`, so the User-Agent gate is in the loop.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from collect.adapters.blog.fetch import BlogFetcher, fetcher_for_source
from collect.adapters.blog.limiter import HostLimiter
from collect.adapters.blog.robots import RobotsGate
from collect.adapters.blog.validators import FeedValidators, InMemoryValidatorStore
from collect.http import build_client
from collect.rawstore import RAW, RawStore, parse_ref
from collect.registry.assertions import TermsNotReviewedError

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "blog"
UA = "modelboard/0.1 (+https://modelboard.invalid/about)"
FEED_URL = "https://notes.example.invalid/feed.xml"
XML = {"content-type": "application/rss+xml"}
HTML = {"content-type": "text/html; charset=utf-8"}


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class Recorder:
    """A recorded site. Routes by path; records every request it served."""

    def __init__(self, routes: dict[str, httpx.Response], *, robots: bytes | None = b""):
        self.routes = routes
        self.robots = robots
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert request.headers["User-Agent"] == UA, "every request carries the UA (NFR-5)"

        if request.url.path == "/robots.txt":
            if self.robots is None:
                return httpx.Response(404)
            return httpx.Response(200, content=self.robots, headers={"content-type": "text/plain"})

        response = self.routes.get(request.url.path)
        if response is None:
            return httpx.Response(404)
        # Conditional GET is the server's decision, so it is made here.
        if request.headers.get("if-none-match") and response.headers.get("etag") == request.headers[
            "if-none-match"
        ]:
            return httpx.Response(304, headers={"etag": response.headers["etag"]})
        return httpx.Response(
            response.status_code, content=response.content, headers=dict(response.headers)
        )

    @property
    def paths(self) -> list[str]:
        return [str(request.url.path) for request in self.requests]


def build(
    recorder: Recorder, tmp_path: Path, **kwargs
) -> tuple[BlogFetcher, RawStore, InMemoryValidatorStore]:
    client = build_client(user_agent=UA, transport=httpx.MockTransport(recorder))
    store = RawStore(tmp_path / "raw_store")
    validators = kwargs.pop("validators", None)
    if validators is None:
        validators = InMemoryValidatorStore()
    fetcher = BlogFetcher(
        client=client,
        store=store,
        robots=RobotsGate(client, user_agent=UA, clock=lambda: 0.0),
        # A real clock and a real sleep would make the suite slow to prove
        # arithmetic; the limiter's own test covers the waiting.
        limiter=HostLimiter(min_interval=0.0, clock=lambda: 0.0, sleeper=lambda _s: None),
        validators=validators,
        pipeline_version="collect-test",
        clock=lambda: datetime(2026, 8, 13, 9, 0, tzinfo=UTC),
        **kwargs,
    )
    return fetcher, store, validators


def rss_site(**headers) -> Recorder:
    return Recorder(
        {
            "/feed.xml": httpx.Response(
                200, content=fixture("feed_rss.xml"), headers={**XML, **headers}
            ),
            "/posts/summariser-swap": httpx.Response(
                200, content=fixture("article.html"), headers=HTML
            ),
            "/posts/tool-calling-notes": httpx.Response(
                200, content=fixture("article_with_comments.html"), headers=HTML
            ),
        }
    )


# ── the happy path, and what lands in the store ──────────────────────────


def test_feed_and_articles_are_stored_as_separate_raw_artifacts(tmp_path):
    """Two artifacts. `text_ref` names the article, never the feed.

    A feed covers many entries, so pointing `text_ref` at it would stop
    `content_hash` identifying one document — breaking dedupe, and breaking
    NFR-6, where one post's takedown would tombstone a blob holding all of them.
    """
    fetcher, store, _ = build(rss_site(), tmp_path)
    run = fetcher.harvest_feed(FEED_URL)

    assert run.outcome == "fetched"
    assert run.feed.artifact is not None
    assert store.get(run.feed.artifact.ref) == fixture("feed_rss.xml")

    stored = [article for article in run.articles if article.stored]
    assert len(stored) == 2
    refs = {article.artifact.ref for article in stored}
    assert len(refs) == 2, "two distinct articles, two distinct refs"
    assert run.feed.artifact.ref not in refs

    for article in stored:
        namespace, hash_hex = parse_ref(article.artifact.ref)
        assert namespace is RAW, "fetched payloads are irreplaceable, never evictable"
        assert article.artifact.content_hash == hash_hex


def test_nothing_flattened_is_written_by_harvest(tmp_path):
    """Extraction is E3's. Harvest stores what arrived and stops."""
    fetcher, store, _ = build(rss_site(), tmp_path)
    fetcher.harvest_feed(FEED_URL)
    flattened = store.root / "flattened"
    assert not flattened.exists()


def test_yield_counts_are_the_fr10_figures(tmp_path):
    fetcher, _, _ = build(rss_site(), tmp_path)
    run = fetcher.harvest_feed(FEED_URL)
    assert run.items_fetched == 2
    assert run.items_kept == 2
    assert run.http_errors == 0


def test_re_fetching_unchanged_bytes_is_a_no_op_in_the_store(tmp_path):
    """Content addressing makes a repeat harvest idempotent (NFR-4)."""
    fetcher, _, _ = build(rss_site(), tmp_path)
    first = fetcher.harvest_feed(FEED_URL)
    second = fetcher.harvest_feed(FEED_URL)
    assert first.feed.artifact.ref == second.feed.artifact.ref
    assert second.feed.artifact.already_present


# ── conditional GET ──────────────────────────────────────────────────────


def test_validators_are_stored_and_sent_back(tmp_path):
    site = rss_site(etag='W/"abc123"', **{"last-modified": "Tue, 04 Aug 2026 09:15:00 GMT"})
    fetcher, _, validators = build(site, tmp_path)

    first = fetcher.harvest_feed(FEED_URL)
    assert first.outcome == "fetched"
    saved = validators.load(FEED_URL)
    assert saved == FeedValidators(
        etag='W/"abc123"', last_modified="Tue, 04 Aug 2026 09:15:00 GMT"
    )

    second = fetcher.harvest_feed(FEED_URL)
    assert second.outcome == "not-modified"
    feed_requests = [r for r in site.requests if r.url.path == "/feed.xml"]
    assert feed_requests[1].headers["if-none-match"] == 'W/"abc123"'
    assert feed_requests[1].headers["if-modified-since"] == "Tue, 04 Aug 2026 09:15:00 GMT"


def test_304_stores_nothing_and_fetches_no_articles(tmp_path):
    site = rss_site(etag='W/"abc123"')
    fetcher, store, _ = build(site, tmp_path)
    fetcher.harvest_feed(FEED_URL)
    before = sorted(p.name for p in (store.root / "raw").rglob("*") if p.is_file())

    run = fetcher.harvest_feed(FEED_URL)
    assert run.outcome == "not-modified"
    assert run.feed.artifact is None
    assert run.articles == []
    after = sorted(p.name for p in (store.root / "raw").rglob("*") if p.is_file())
    assert before == after


def test_a_304_that_omits_the_etag_does_not_clear_it(tmp_path):
    """Rule 6 in the small: absent is not "no validator".

    Clearing on a silent 304 would turn every second run into a full re-fetch,
    and it would look like conditional GET simply not working.
    """
    validators = InMemoryValidatorStore({FEED_URL: FeedValidators(etag='W/"abc123"')})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(304)  # no ETag echoed back

    fetcher, _, store_of_validators = build(
        Recorder({}, robots=None), tmp_path, validators=validators
    )
    fetcher._client = build_client(user_agent=UA, transport=httpx.MockTransport(handler))
    fetcher._robots = RobotsGate(fetcher._client, user_agent=UA, clock=lambda: 0.0)

    run = fetcher.harvest_feed(FEED_URL)
    assert run.outcome == "not-modified"
    assert store_of_validators.load(FEED_URL) == FeedValidators(etag='W/"abc123"')


def test_empty_validators_send_no_conditional_headers(tmp_path):
    """`If-None-Match: ""` gets 304s for content we have never seen."""
    site = rss_site()
    fetcher, _, _ = build(site, tmp_path)
    fetcher.harvest_feed(FEED_URL)
    feed_request = next(r for r in site.requests if r.url.path == "/feed.xml")
    assert "if-none-match" not in feed_request.headers
    assert "if-modified-since" not in feed_request.headers


# ── robots ───────────────────────────────────────────────────────────────


def test_a_disallowed_feed_is_blocked_not_errored(tmp_path):
    """`robots-blocked` is a choice we made; `error` is a request that failed.

    Counting a skip as an HTTP error would make the FR-10 alert fire on our own
    politeness.
    """
    site = rss_site()
    site.robots = fixture("robots_disallow.txt")
    fetcher, _, _ = build(site, tmp_path)

    # The feed itself is not under /posts/, so it is fetched; the articles are.
    run = fetcher.harvest_feed(FEED_URL)
    assert run.outcome == "fetched"
    assert run.items_fetched == 2
    assert run.items_kept == 0
    assert run.http_errors == 0
    assert run.robots_blocked == 2
    assert all(article.outcome == "robots-blocked" for article in run.articles)
    assert "/posts/summariser-swap" not in site.paths


def test_unreachable_robots_blocks_the_whole_feed(tmp_path):
    site = rss_site()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(503)
        return site(request)

    client = build_client(user_agent=UA, transport=httpx.MockTransport(handler))
    fetcher = BlogFetcher(
        client=client,
        store=RawStore(tmp_path / "raw_store"),
        robots=RobotsGate(client, user_agent=UA, clock=lambda: 0.0),
        limiter=HostLimiter(min_interval=0.0, clock=lambda: 0.0, sleeper=lambda _s: None),
        pipeline_version="collect-test",
    )
    run = fetcher.harvest_feed(FEED_URL)
    assert run.outcome == "robots-blocked"
    assert run.items_fetched == 0
    assert run.http_errors == 0, "we declined to ask; nothing failed"
    assert "/feed.xml" not in [str(r.url.path) for r in site.requests]


# ── redirects ────────────────────────────────────────────────────────────


def test_a_redirect_is_re_gated_against_the_new_origin(tmp_path):
    """The bypass `follow_redirects=True` would have opened.

    The first host's robots.txt says nothing about the second host, and httpx
    would have followed without asking.
    """
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(f"{request.url.host}{request.url.path}")
        if request.url.path == "/robots.txt":
            if request.url.host == "elsewhere.example.invalid":
                return httpx.Response(200, content=b"User-agent: *\nDisallow: /\n",
                                      headers={"content-type": "text/plain"})
            return httpx.Response(404)
        if request.url.host == "notes.example.invalid":
            return httpx.Response(301, headers={"location": "https://elsewhere.example.invalid/feed.xml"})
        return httpx.Response(200, content=fixture("feed_rss.xml"), headers=XML)

    client = build_client(user_agent=UA, transport=httpx.MockTransport(handler))
    fetcher = BlogFetcher(
        client=client,
        store=RawStore(tmp_path / "raw_store"),
        robots=RobotsGate(client, user_agent=UA, clock=lambda: 0.0),
        limiter=HostLimiter(min_interval=0.0, clock=lambda: 0.0, sleeper=lambda _s: None),
        pipeline_version="collect-test",
    )
    run = fetcher.harvest_feed(FEED_URL)

    assert run.outcome == "robots-blocked"
    assert "elsewhere.example.invalid/robots.txt" in seen
    assert "elsewhere.example.invalid/feed.xml" not in seen


def test_a_redirect_chain_is_bounded(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "/feed.xml?hop"})

    client = build_client(user_agent=UA, transport=httpx.MockTransport(handler))
    fetcher = BlogFetcher(
        client=client,
        store=RawStore(tmp_path / "raw_store"),
        robots=RobotsGate(client, user_agent=UA, clock=lambda: 0.0),
        limiter=HostLimiter(min_interval=0.0, clock=lambda: 0.0, sleeper=lambda _s: None),
        max_redirects=2,
        pipeline_version="collect-test",
    )
    run = fetcher.harvest_feed(FEED_URL)
    assert run.outcome == "error"
    assert "redirects" in run.feed.detail


# ── what is not an article ───────────────────────────────────────────────


def test_a_pdf_link_is_not_stored_as_an_article(tmp_path):
    site = rss_site()
    site.routes["/posts/summariser-swap"] = httpx.Response(
        200, content=b"%PDF-1.7\n", headers={"content-type": "application/pdf"}
    )
    fetcher, _, _ = build(site, tmp_path)
    run = fetcher.harvest_feed(FEED_URL)

    failed = [a for a in run.articles if a.url and a.url.endswith("summariser-swap")]
    assert failed[0].outcome == "error"
    assert "application/pdf" in failed[0].detail
    assert run.items_kept == 1


def test_an_oversized_article_is_refused_before_it_is_stored(tmp_path):
    site = rss_site()
    site.routes["/posts/summariser-swap"] = httpx.Response(
        200, content=b"x" * 5000, headers=HTML
    )
    fetcher, store, _ = build(site, tmp_path, max_article_bytes=1000)
    run = fetcher.harvest_feed(FEED_URL)

    refused = [a for a in run.articles if a.url and a.url.endswith("summariser-swap")][0]
    assert refused.outcome == "error"
    assert refused.artifact is None
    assert run.http_errors == 1


def test_a_missing_article_counts_as_an_http_error_not_a_missing_feed(tmp_path):
    site = rss_site()
    del site.routes["/posts/tool-calling-notes"]
    fetcher, _, _ = build(site, tmp_path)
    run = fetcher.harvest_feed(FEED_URL)

    assert run.outcome == "fetched", "the feed was read; one article was not"
    assert run.items_fetched == 2
    assert run.items_kept == 1
    assert run.http_errors == 1


# ── the harvest_run row, and the field with nowhere to go ─────────────────


def test_harvest_run_fields_map_onto_the_columns_that_exist(tmp_path):
    fetcher, _, _ = build(rss_site(), tmp_path)
    fields = fetcher.harvest_feed(FEED_URL).harvest_run_fields()

    assert fields["source_id"] == "blogs"
    assert fields["query_key"] == FEED_URL
    assert fields["items_fetched"] == 2
    assert fields["items_kept"] == 2
    assert fields["truncated_by"] is None
    assert fields["pipeline_version"] == "collect-test"
    # A feed has no end. `exhausted` means "reached the end of its results and
    # must not be resumed", which is a statement about pagination.
    assert fields["exhausted"] is None


def test_the_304_and_the_broken_parser_differ_only_in_outcome(tmp_path):
    """The FR-10 collision, stated as a test.

    Both rows are `items_fetched=0, items_kept=0`. Without `outcome` a broken
    parser hides among unchanged feeds indefinitely, and FR-10's acceptance —
    break a selector, alert within one cycle — passes on a fresh feed and fails
    silently on a cached one.
    """
    site = rss_site(etag='W/"abc123"')
    fetcher, _, _ = build(site, tmp_path)
    fetcher.harvest_feed(FEED_URL)
    unchanged = fetcher.harvest_feed(FEED_URL).harvest_run_fields()

    empty_site = Recorder({"/feed.xml": httpx.Response(200, content=b"", headers=XML)}, robots=None)
    broken, _, _ = build(empty_site, tmp_path)
    yielded_nothing = broken.harvest_feed(FEED_URL).harvest_run_fields()

    countable = {"items_fetched", "items_kept", "http_errors", "truncated_by", "exhausted"}
    assert {key: unchanged[key] for key in countable} == {
        key: yielded_nothing[key] for key in countable
    }
    assert unchanged["outcome"] == "not-modified"
    assert yielded_nothing["outcome"] == "fetched"


# ── the ToS gate ─────────────────────────────────────────────────────────


def test_the_source_entry_point_refuses_an_unreviewed_source(tmp_path):
    """NFR-5. With `contract/sources.yaml` as it stands, blogs is unreviewed."""
    import yaml

    from collect.config import CONTRACT_DIR

    loaded = yaml.safe_load((CONTRACT_DIR / "sources.yaml").read_text(encoding="utf-8"))
    blogs = next(source for source in loaded["sources"] if source["id"] == "blogs")

    with pytest.raises(TermsNotReviewedError) as excinfo:
        fetcher_for_source(
            blogs,
            client=build_client(user_agent=UA, transport=httpx.MockTransport(rss_site())),
            store=RawStore(tmp_path / "raw_store"),
            robots=RobotsGate(
                build_client(user_agent=UA, transport=httpx.MockTransport(rss_site())),
                user_agent=UA,
            ),
        )
    assert "blogs" in str(excinfo.value)


def test_no_client_can_be_built_without_an_identifying_user_agent():
    """The gate the three library bypasses would have walked around."""
    from collect.http import UserAgentError

    with pytest.raises(UserAgentError):
        build_client(user_agent="")
    with pytest.raises(UserAgentError):
        build_client(user_agent="modelboard/0.1 (+https://your-contact-url.example)")
