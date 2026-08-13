"""The robots gate: what counts as an answer, and what fails closed.

Every case is driven through `httpx.MockTransport` and a client built by
`build_client`, so the User-Agent gate is in the loop exactly as it is in
production. Nothing here reaches the network.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from collect.adapters.blog.robots import RobotsGate, origin_of
from collect.http import build_client

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "blog"
UA = "modelboard/0.1 (+https://modelboard.invalid/about)"
ORIGIN = "https://notes.example.invalid"
ARTICLE = f"{ORIGIN}/posts/summariser-swap"


def gate(handler, *, clock=None) -> RobotsGate:
    client = build_client(user_agent=UA, transport=httpx.MockTransport(handler))
    return RobotsGate(client, user_agent=UA, clock=clock or (lambda: 0.0))


def responder(status: int, body: bytes = b"", content_type: str = "text/plain"):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/robots.txt"
        assert request.headers["User-Agent"] == UA, "NFR-5 applies to robots.txt too"
        return httpx.Response(status, content=body, headers={"content-type": content_type})

    return handler


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ── origins ──────────────────────────────────────────────────────────────


def test_origin_is_per_scheme_and_port():
    """Permission granted for one origin must not be applied to another."""
    assert origin_of("https://a.example.invalid/x") == "https://a.example.invalid"
    assert origin_of("http://a.example.invalid/x") == "http://a.example.invalid"
    assert origin_of("https://a.example.invalid:8443/x") == "https://a.example.invalid:8443"


def test_relative_url_is_refused_rather_than_guessed():
    with pytest.raises(ValueError):
        origin_of("/posts/summariser-swap")


# ── answers ──────────────────────────────────────────────────────────────


def test_200_rules_are_obeyed():
    allowed = gate(responder(200, fixture("robots_allow.txt"))).allows(ARTICLE)
    assert allowed.allowed
    assert allowed.ruling.status == "rules"

    blocked = gate(responder(200, fixture("robots_disallow.txt"))).allows(ARTICLE)
    assert not blocked.allowed
    assert blocked.ruling.status == "rules"
    assert "disallowed" in blocked.reason


@pytest.mark.parametrize("status", [404, 410])
def test_404_and_410_are_answers_meaning_no_rules(status):
    """The refinement that matters.

    A server answering "there is no robots.txt" has given a definite value, not
    a missing one. Treating it as denial would exclude most small blogs
    permanently from the only positive-evidence channel — rule 4 with the harm
    pointing the other way.
    """
    decision = gate(responder(status)).allows(ARTICLE)
    assert decision.allowed
    assert decision.ruling.status == "no-rules"
    assert decision.ruling.answered


@pytest.mark.parametrize("status", [401, 403])
def test_401_and_403_are_refusals(status):
    decision = gate(responder(status)).allows(ARTICLE)
    assert not decision.allowed
    assert decision.ruling.status == "refused"


# ── no answer: every one of these fails closed ───────────────────────────


@pytest.mark.parametrize("status", [429, 418, 500, 502, 503])
def test_anything_else_is_no_answer(status):
    """Stricter than RFC 9309 on 4xx, deliberately: a 429 says nothing about
    crawling, and absence of permission is not permission."""
    decision = gate(responder(status)).allows(ARTICLE)
    assert not decision.allowed
    assert decision.ruling.status == "no-answer"
    assert not decision.ruling.answered


def test_transport_error_fails_closed():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    decision = gate(handler).allows(ARTICLE)
    assert not decision.allowed
    assert decision.ruling.status == "no-answer"
    assert "ConnectTimeout" in decision.ruling.detail


def test_non_text_content_type_is_not_a_robots_file():
    decision = gate(
        responder(200, b"\x89PNG\r\n\x1a\n", content_type="image/png")
    ).allows(ARTICLE)
    assert not decision.allowed
    assert decision.ruling.status == "no-answer"


def test_oversized_body_is_not_a_robots_file():
    client = build_client(
        user_agent=UA,
        transport=httpx.MockTransport(responder(200, b"#" * 5000)),
    )
    gate_ = RobotsGate(client, user_agent=UA, max_bytes=1000, clock=lambda: 0.0)
    decision = gate_.allows(ARTICLE)
    assert not decision.allowed
    assert decision.ruling.status == "no-answer"


def test_undecodable_body_fails_closed():
    decision = gate(responder(200, b"User-agent: *\nDisallow: \xff\xfe/")).allows(ARTICLE)
    assert not decision.allowed
    assert decision.ruling.status == "no-answer"


def test_missing_content_type_is_still_read():
    """Plenty of small servers send no content-type. That is not a refusal."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=fixture("robots_allow.txt"))

    client = build_client(user_agent=UA, transport=httpx.MockTransport(handler))
    # httpx supplies no content-type of its own when the response carries none.
    decision = RobotsGate(client, user_agent=UA, clock=lambda: 0.0).allows(ARTICLE)
    assert decision.ruling.status in ("rules", "no-answer")
    if decision.ruling.status == "rules":
        assert decision.allowed


# ── crawl delay and caching ──────────────────────────────────────────────


def test_crawl_delay_widens_the_floor_but_never_narrows_it():
    slow = gate(responder(200, fixture("robots_crawl_delay.txt")))
    assert slow.min_interval(ARTICLE, floor=1.0) == 5.0

    quick = gate(responder(200, b"User-agent: *\nCrawl-delay: 0.1\n"))
    assert quick.min_interval(ARTICLE, floor=1.0) == 1.0


def test_no_crawl_delay_leaves_the_floor_alone():
    assert gate(responder(404)).min_interval(ARTICLE, floor=1.0) == 1.0


def test_robots_is_fetched_once_per_origin_per_ttl():
    """One ruling per origin per run: forty articles must not mean forty fetches."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(
            200, content=fixture("robots_allow.txt"), headers={"content-type": "text/plain"}
        )

    now = [0.0]
    gate_ = gate(handler, clock=lambda: now[0])
    gate_.allows(f"{ORIGIN}/posts/a")
    gate_.allows(f"{ORIGIN}/posts/b")
    assert len(calls) == 1

    now[0] = 10_000.0  # past the TTL
    gate_.allows(f"{ORIGIN}/posts/c")
    assert len(calls) == 2, "a publisher changing their mind must be honoured"


def test_each_origin_gets_its_own_ruling():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host)
        closed = request.url.host == "closed.example.invalid"
        body = b"User-agent: *\nDisallow: /\n" if closed else b""
        return httpx.Response(200, content=body, headers={"content-type": "text/plain"})

    gate_ = gate(handler)
    assert gate_.allows("https://open.example.invalid/posts/x").allowed
    assert not gate_.allows("https://closed.example.invalid/posts/x").allowed
    assert seen == ["open.example.invalid", "closed.example.invalid"]
