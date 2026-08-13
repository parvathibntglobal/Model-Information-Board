"""Nothing in the blog path may reach the network by any route but `build_client`.

This is the third of the three enforcements, and the only one that catches a
regression the other two have no name for. The AST test in
`test_lane_boundary.py` sees imports it was told to look for; this severs the
transports themselves:

    socket.socket                 anything that opens a TCP connection
    socket.create_connection      urllib's route
    urllib.request.urlopen        feedparser's own fetch, RobotFileParser.read()
    urllib3.PoolManager.request   trafilatura's downloader
    urllib3.HTTPConnectionPool    trafilatura's downloader, lower down
    httpx.HTTPTransport.handle_request   real httpx, as opposed to MockTransport

Then it runs the whole fetch path against recorded fixtures. If any library
reaches for the network — now or after an upgrade that changes its default — the
suite says which one instead of quietly making a request from CI.

`pycurl` is not patched because it is not installed; trafilatura prefers it when
it is, so `test_pycurl_is_not_installed` fails loudly if it ever arrives as a
transitive dependency, rather than this file silently covering one transport
less.
"""

from __future__ import annotations

import socket
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from collect.adapters.blog.fetch import BlogFetcher
from collect.adapters.blog.limiter import HostLimiter
from collect.adapters.blog.parse import extract_article_text, parse_feed
from collect.adapters.blog.robots import RobotsGate
from collect.http import build_client
from collect.rawstore import RawStore

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "blog"
UA = "modelboard/0.1 (+https://modelboard.invalid/about)"
FEED_URL = "https://notes.example.invalid/feed.xml"


class NetworkReached(AssertionError):
    """Something tried to open a connection outside `build_client`."""


@pytest.fixture
def no_network(monkeypatch):
    """Sever every transport a library could use, and name the one that tried."""

    def forbid(what: str):
        def raiser(*args, **kwargs):
            raise NetworkReached(
                f"{what} was called. Something in the blog path is fetching outside "
                "collect.http.build_client, which means a request without the "
                "identifying User-Agent NFR-5 requires. Check for feedparser.parse "
                "given a URL, trafilatura.fetch_url, or RobotFileParser.read()."
            )

        return raiser

    monkeypatch.setattr(socket, "socket", forbid("socket.socket"))
    monkeypatch.setattr(socket, "create_connection", forbid("socket.create_connection"))
    monkeypatch.setattr(urllib.request, "urlopen", forbid("urllib.request.urlopen"))
    monkeypatch.setattr(
        httpx.HTTPTransport, "handle_request", forbid("httpx.HTTPTransport.handle_request")
    )

    try:  # urllib3 is trafilatura's transport, and it is present via httpx's deps
        import urllib3

        monkeypatch.setattr(urllib3.PoolManager, "request", forbid("urllib3.PoolManager.request"))
        monkeypatch.setattr(
            urllib3.HTTPConnectionPool, "urlopen", forbid("urllib3.HTTPConnectionPool.urlopen")
        )
    except ImportError:  # pragma: no cover - urllib3 absent
        pass

    return forbid


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def recorded(request: httpx.Request) -> httpx.Response:
    routes = {
        "/robots.txt": (200, fixture("robots_allow.txt"), "text/plain"),
        "/feed.xml": (200, fixture("feed_rss.xml"), "application/rss+xml"),
        "/posts/summariser-swap": (200, fixture("article.html"), "text/html"),
        "/posts/tool-calling-notes": (200, fixture("article_with_comments.html"), "text/html"),
    }
    route = routes.get(request.url.path)
    if route is None:
        return httpx.Response(404)
    status, body, content_type = route
    return httpx.Response(status, content=body, headers={"content-type": content_type})


# ── the fixture works ────────────────────────────────────────────────────


def test_the_fixture_itself_bites(no_network):
    """A test that cannot fail proves nothing. This is the one that proves it can."""
    with pytest.raises(NetworkReached):
        urllib.request.urlopen("http://127.0.0.1:1/")


def test_pycurl_is_not_installed():
    """trafilatura prefers pycurl when present, and this file does not patch it.

    If pycurl ever arrives as a transitive dependency, fail here rather than
    let the no-network guarantee quietly cover one transport less.
    """
    with pytest.raises(ImportError):
        import pycurl  # noqa: F401


# ── the libraries, handed bytes ──────────────────────────────────────────


def test_parse_feed_makes_no_request(no_network):
    parsed = parse_feed(fixture("feed_rss.xml"), feed_url=FEED_URL)
    assert len(parsed.entries) == 2


def test_extract_article_makes_no_request(no_network):
    """trafilatura resolves nothing over the wire when handed bytes.

    Worth asserting rather than assuming: its metadata and date extraction have
    had URL-fetching code paths, and `url=` is passed in here.
    """
    text = extract_article_text(fixture("article.html"), url="https://notes.example.invalid/x")
    assert text and "1.8s" in text


# ── the whole fetch path ─────────────────────────────────────────────────


def test_the_fetch_path_only_reaches_the_injected_transport(no_network, tmp_path):
    client = build_client(user_agent=UA, transport=httpx.MockTransport(recorded))
    fetcher = BlogFetcher(
        client=client,
        store=RawStore(tmp_path / "raw_store"),
        robots=RobotsGate(client, user_agent=UA, clock=lambda: 0.0),
        limiter=HostLimiter(min_interval=0.0, clock=lambda: 0.0, sleeper=lambda _s: None),
        pipeline_version="collect-test",
        clock=lambda: datetime(2026, 8, 13, 9, 0, tzinfo=UTC),
    )

    run = fetcher.harvest_feed(FEED_URL)

    assert run.outcome == "fetched"
    assert run.items_fetched == 2
    assert run.items_kept == 2


def test_a_real_client_would_be_caught(no_network):
    """Proof that the transport patch covers httpx itself, not just the libraries.

    Without this, the test above would pass for a fetch path that had quietly
    stopped using the injected transport.
    """
    client = build_client(user_agent=UA)
    with pytest.raises(NetworkReached):
        client.get("https://notes.example.invalid/feed.xml")
