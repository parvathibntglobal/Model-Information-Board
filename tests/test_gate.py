"""The API gate: who may call, and how often.

Before this, `Depends`, `HTTPBearer`, `Security` and `OAuth2` appeared nowhere
in `judge/app.py`. Anyone who could open a socket got the whole board, including
`/admin/usage`, which reports spend on the OpenRouter key.

The tests worth having are about the THREE-STATE rule, because a two-state one
(open or closed) is what would have shipped by accident: unset-in-development
has to stay open or nobody can run a fresh clone, and unset-anywhere-else has to
refuse or that convenience follows someone to a server.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from judge import gate
from judge.app import app
from judge.ask import spend


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.delenv("ASK_RATE_PER_HOUR", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    gate._reset_for_tests()
    yield
    gate._reset_for_tests()


#: Any route behind the gate that answers without a database. `/capabilities`
#: played this part until it was removed 2026-10-08 (no page called it).
# `/faq` played this part until 2026-10-15, when it became a public read
# (judge/gate.py: PUBLIC_READ_PATHS). `/admin/settings` answers without a
# database too, and stays behind the gate.
GATED = "/admin/settings"


def _client() -> TestClient:
    return TestClient(app)


# ── the three states ────────────────────────────────────────────────────────


def test_development_without_a_token_stays_open():
    """Otherwise a fresh clone cannot be run, and this file gets deleted."""
    assert _client().get(GATED).status_code == 200


def test_a_set_token_is_required_everywhere():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        assert _client().get(GATED).status_code == 401


def test_a_set_token_admits_the_right_bearer():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        r = _client().get(GATED, headers={"Authorization": "Bearer s3cret"})
        assert r.status_code == 200


def test_a_wrong_token_is_401_not_403():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        r = _client().get(GATED, headers={"Authorization": "Bearer nope"})
        assert r.status_code == 401
        assert r.headers.get("WWW-Authenticate") == "Bearer"


def test_no_token_outside_development_refuses_rather_than_serving():
    """The state that stops local convenience reaching a server.

    503, not 401: nothing is wrong with the request. Nobody decided.
    """
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ENVIRONMENT", "staging")
        r = _client().get(GATED)
        assert r.status_code == 503
        assert "missing decision" in r.json()["detail"]


# ── /health is the one exception, and says so ───────────────────────────────


def test_health_never_needs_a_token_even_when_one_is_set():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        assert _client().get("/health").status_code == 200


def test_health_answers_whether_the_board_is_exposed():
    """One unauthenticated GET, rather than inferring it from config."""
    body = _client().get("/health").json()
    assert body["auth"]["required"] is False
    assert "OPEN" in body["auth"]["reason"]

    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        assert _client().get("/health").json()["auth"]["required"] is True


def test_health_still_refuses_to_leak_the_token_itself():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret-do-not-print")
        assert "s3cret-do-not-print" not in _client().get("/health").text


# ── the money endpoint ──────────────────────────────────────────────────────


def test_admin_usage_is_behind_the_gate():
    """It reports spend on the key, including a cross-machine total."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        assert _client().get("/admin/usage").status_code == 401


def test_the_ask_rate_limit_binds_and_names_itself():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ASK_RATE_PER_HOUR", "2")
        # The handler refuses with 503 before it reaches a model, which is
        # what makes this test meaningful: the limiter is a route dependency so
        # it runs BEFORE the handler, and a 429 on the third call proves it
        # bound without any request having been allowed to spend anything.
        #
        # Patched rather than unset via the environment: `spend` caches
        # `Budget.from_env()` in a module global on first use, so by the time
        # this test runs the cap is already resolved and deleting the variable
        # changes nothing.
        m.setattr(spend, "is_configured", lambda: False)
        c = _client()
        body = {"text": "summarise tickets", "shape": "task"}

        first = [c.post("/ask/understand", json=body).status_code for _ in range(2)]
        third = c.post("/ask/understand", json=body)

        assert 429 not in first
        assert third.status_code == 429
        assert "spends money" in third.json()["detail"]
        assert third.headers.get("Retry-After")


def test_the_rate_limit_can_be_turned_off_deliberately():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ASK_RATE_PER_HOUR", "0")
        m.setattr(spend, "is_configured", lambda: False)
        c = _client()
        body = {"text": "summarise tickets", "shape": "task"}
        codes = [c.post("/ask/understand", json=body).status_code for _ in range(4)]
        assert 429 not in codes


# ── the public reads (2026-10-15) ─────────────────────────────────────────


def test_a_public_read_needs_no_token_even_when_one_is_set():
    """The published pages are opened by visitors who have not signed in."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        assert _client().get("/faq").status_code == 200


def test_a_stale_token_on_a_public_read_is_served_not_refused():
    """A browser holding an expired session must not lose the public pages."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        r = _client().get("/faq", headers={"Authorization": "Bearer stale"})
        assert r.status_code == 200


def test_only_reads_are_public():
    """A write to a public path is not a public read. (Asked of the gate's own
    rule: FastAPI answers 405 for a method a route lacks before any dependency
    runs, so an HTTP POST here would not reach the gate at all.)"""
    from starlette.requests import Request

    def req(method, path, query=b""):
        return Request({"type": "http", "method": method, "path": path,
                        "query_string": query, "headers": []})

    assert gate.is_public_read(req("GET", "/faq"))
    assert not gate.is_public_read(req("POST", "/faq"))
    assert not gate.is_public_read(req("GET", "/blog-posts", b"include=all"))
    assert gate.is_public_read(req("GET", "/model-catalog/anthropic/claude-opus-5"))
    assert not gate.is_public_read(req("GET", "/board"))


def test_blog_drafts_are_not_a_public_read():
    """`/blog-posts` is public for the APPROVED posts only; `include=all` -
    drafts and the review queue - still needs a token."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        assert _client().get("/blog-posts?include=all").status_code == 401


def test_the_board_and_a_models_evidence_stay_behind_the_gate():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        assert _client().get("/board").status_code == 401
        assert _client().get("/models/anthropic/claude-opus-5/evidence").status_code == 401


def test_the_public_list_names_only_reads_that_were_checked():
    """Adding a path here publishes it. Each one was checked for what it sends
    (judge/gate.py); a new one has to be checked the same way."""
    assert {
        "/reports", "/model-catalog", "/faq", "/models", "/freshness",
        "/seo/indexable", "/blog-posts", "/compare", "/discussions",
    } == gate.PUBLIC_READ_PATHS
    assert gate.PUBLIC_READ_PREFIXES == ("/model-catalog/",)


def test_an_anonymous_comparison_carries_counts_and_no_words():
    """What /compare sends a visitor: every quote, post link and Board link
    emptied, the counts left as they were."""
    from judge.app import _counts_only

    payload = {"models": [{"reported": {
        "polarity": {"positive": 3, "negative": 1},
        "discovered": {"best_for": [{
            "slug": "coding-agent", "reports": 4,
            "quotes": [{"quote": "it worked", "url": "https://example.com/p/1"}],
            "board_path": "jobs/coding-agent", "board_model_path": "jobs/coding-agent/m",
        }], "metrics": [{"figures": [{"value": "$5", "url": "https://x", "document_id": "d1"}]}]},
    }}]}
    out = _counts_only(payload)
    row = out["models"][0]["reported"]["discovered"]["best_for"][0]
    assert row["quotes"] == [] and row["board_path"] is None and row["board_model_path"] is None
    assert row["reports"] == 4
    fig = out["models"][0]["reported"]["discovered"]["metrics"][0]["figures"][0]
    assert fig["url"] is None and fig["document_id"] is None and fig["value"] == "$5"
    assert out["models"][0]["reported"]["polarity"] == {"positive": 3, "negative": 1}
    assert "it worked" not in str(out)


def test_an_anonymous_comparison_says_how_many_platforms_but_not_which():
    """No per-platform split on a public endpoint (contract/sources.yaml:
    `per_platform_counts_shown: false`): the number of platforms survives,
    because the page shows it; which ones, and how many documents each, do not."""
    from judge.app import _no_platform_split

    payload = {"models": [{"reported": {"polarity": {
        "positive": 3,
        "platforms": [
            {"source": "hackernews", "documents": 36},
            {"source": "devto", "documents": 12},
        ],
    }}}]}
    out = _no_platform_split(payload)
    platforms = out["models"][0]["reported"]["polarity"]["platforms"]
    assert len(platforms) == 2
    assert platforms == [{"source": None, "documents": None}] * 2
    assert out["models"][0]["reported"]["polarity"]["positive"] == 3
    assert "hackernews" not in str(out) and "36" not in str(out)
