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


def _client() -> TestClient:
    return TestClient(app)


# ── the three states ────────────────────────────────────────────────────────


def test_development_without_a_token_stays_open():
    """Otherwise a fresh clone cannot be run, and this file gets deleted."""
    assert _client().get("/capabilities").status_code == 200


def test_a_set_token_is_required_everywhere():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        assert _client().get("/capabilities").status_code == 401


def test_a_set_token_admits_the_right_bearer():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        r = _client().get("/capabilities", headers={"Authorization": "Bearer s3cret"})
        assert r.status_code == 200


def test_a_wrong_token_is_401_not_403():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        r = _client().get("/capabilities", headers={"Authorization": "Bearer nope"})
        assert r.status_code == 401
        assert r.headers.get("WWW-Authenticate") == "Bearer"


def test_no_token_outside_development_refuses_rather_than_serving():
    """The state that stops local convenience reaching a server.

    503, not 401: nothing is wrong with the request. Nobody decided.
    """
    with pytest.MonkeyPatch.context() as m:
        m.setenv("ENVIRONMENT", "staging")
        r = _client().get("/capabilities")
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
