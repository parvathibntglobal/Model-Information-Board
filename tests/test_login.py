"""Sign-in, with the credential on the server rather than in the bundle.

`web/src/auth.js` held the email and an unsalted SHA-256 of the password as
literals. It shipped to every visitor and was checked in the browser, so it was
readable, crackable and skippable. These tests pin the properties that make the
replacement worth the change - not "does login work", which any version would
pass, but the specific ways the old one was wrong.
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from judge import gate, login
from judge.app import app
from judge.ask import spend

PASSWORD = "correct-horse-battery-staple"
EMAIL = "demo@modelboard.dev"


@pytest.fixture(autouse=True)
def _configured(monkeypatch):
    monkeypatch.setenv("AUTH_EMAIL", EMAIL)
    monkeypatch.setenv("AUTH_PASSWORD_HASH", login.hash_password(PASSWORD))
    monkeypatch.setenv("SESSION_SECRET", "test-secret-not-a-real-one")
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LOGIN_RATE_PER_HOUR", "1000")
    gate._reset_for_tests()
    yield
    gate._reset_for_tests()


def _client() -> TestClient:
    return TestClient(app)


# ── hashing ─────────────────────────────────────────────────────────────────


def test_the_hash_is_salted_so_two_identical_passwords_differ():
    """The old one was unsalted SHA-256, which is a rainbow-table lookup."""
    assert login.hash_password(PASSWORD) != login.hash_password(PASSWORD)


def test_both_hashes_still_verify():
    for _ in range(2):
        assert login.verify_password(PASSWORD, login.hash_password(PASSWORD))


def test_a_wrong_password_does_not_verify():
    assert not login.verify_password("nearly-right", login.hash_password(PASSWORD))


def test_a_malformed_hash_is_false_rather_than_an_exception():
    """A corrupted .env must fail sign-in, not 500 the endpoint."""
    for junk in ("", "not-a-hash", "sha256$1$2$3", "pbkdf2_sha256$notanint$a$b"):
        assert login.verify_password(PASSWORD, junk) is False


# ── tokens ──────────────────────────────────────────────────────────────────


def test_a_token_round_trips_to_its_owner():
    token, _ = login.issue(EMAIL)
    assert login.read(token) == EMAIL


def test_a_tampered_payload_is_rejected():
    """The signature is over the payload, so editing the claims breaks it."""
    token, _ = login.issue(EMAIL)
    payload, _, signature = token.partition(".")
    forged = payload[:-2] + ("aa" if not payload.endswith("aa") else "bb")
    assert login.read(f"{forged}.{signature}") is None


def test_an_expired_token_is_rejected():
    token, expires = login.issue(EMAIL, now=time.time() - 100_000)
    assert login.read(token) is None
    assert expires < time.time()


def test_a_token_signed_with_another_secret_is_rejected(monkeypatch):
    token, _ = login.issue(EMAIL)
    monkeypatch.setenv("SESSION_SECRET", "a-different-secret")
    assert login.read(token) is None


def test_garbage_is_rejected_without_raising():
    for junk in ("", "no-dot", "a.b", "....", "x" * 500):
        assert login.read(junk) is None


# ── the endpoint ────────────────────────────────────────────────────────────


def test_signing_in_returns_a_usable_token():
    r = _client().post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert login.read(body["token"]) == EMAIL
    assert body["expires_at"] > time.time()


def test_the_password_is_never_echoed_back():
    r = _client().post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert PASSWORD not in r.text


def test_a_wrong_password_and_a_wrong_email_are_indistinguishable():
    """Different messages would say whether an account exists."""
    c = _client()
    wrong_pw = c.post("/auth/login", json={"email": EMAIL, "password": "nope"})
    wrong_em = c.post("/auth/login", json={"email": "nobody@x.dev", "password": PASSWORD})

    assert wrong_pw.status_code == wrong_em.status_code == 401
    assert wrong_pw.json()["detail"] == wrong_em.json()["detail"]


def test_the_email_is_case_insensitive():
    r = _client().post("/auth/login", json={"email": EMAIL.upper(), "password": PASSWORD})
    assert r.status_code == 200


def test_unconfigured_sign_in_refuses_rather_than_inventing_an_account(monkeypatch):
    """Rule 6, where the definite value would be who may read the board."""
    monkeypatch.delenv("AUTH_EMAIL", raising=False)
    r = _client().post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 503
    assert "AUTH_EMAIL" in r.json()["detail"]


# ── the token actually opens the gate ───────────────────────────────────────


def test_a_session_token_is_accepted_where_API_TOKEN_would_be(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "a-static-token")
    c = _client()

    assert c.get("/capabilities").status_code == 401

    token = c.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()["token"]
    ok = c.get("/capabilities", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200


def test_an_expired_session_does_not_open_the_gate(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "a-static-token")
    stale, _ = login.issue(EMAIL, now=time.time() - 100_000)
    r = _client().get("/capabilities", headers={"Authorization": f"Bearer {stale}"})
    assert r.status_code == 401


def test_login_itself_is_reachable_without_a_token(monkeypatch):
    """Otherwise it is a closed loop: a credential needed to get a credential."""
    monkeypatch.setenv("API_TOKEN", "a-static-token")
    r = _client().post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200


def test_sign_in_attempts_are_rate_limited(monkeypatch):
    """Brute force is the only attack this route is exposed to."""
    monkeypatch.setenv("LOGIN_RATE_PER_HOUR", "3")
    c = _client()
    body = {"email": EMAIL, "password": "wrong"}

    codes = [c.post("/auth/login", json=body).status_code for _ in range(4)]

    assert codes[:3] == [401, 401, 401]
    assert codes[3] == 429


def test_the_login_limiter_does_not_share_a_bucket_with_the_ask_box(monkeypatch):
    """Ordinary Ask traffic must not lock somebody out of signing in."""
    monkeypatch.setenv("ASK_RATE_PER_HOUR", "1")
    monkeypatch.setenv("LOGIN_RATE_PER_HOUR", "5")
    # The ask handler refuses at 503 before reaching a model, so this exercises
    # the LIMITERS without needing an API key. `spend` caches its cap in a
    # module global, so this is patched rather than unset in the environment.
    monkeypatch.setattr(spend, "is_configured", lambda: False)
    c = _client()

    for _ in range(3):
        c.post("/ask/understand", json={"text": "x", "shape": "task"})

    assert c.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code == 200
