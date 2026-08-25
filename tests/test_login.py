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


def test_nothing_configured_in_development_falls_back_to_the_demo_login(monkeypatch):
    """A fresh clone signs in with no .env at all.

    THIS TEST USED TO ASSERT THE OPPOSITE, and the reversal is the point.

    It required all three variables and expected 503 naming them, on the
    grounds that a missing AUTH_EMAIL is a missing decision. That is right
    about a secret and wrong here: `.env` is gitignored, so it never updates
    from a pull, and anyone who made theirs before the demo credentials landed
    had a stale copy git could not fix and would not mention. They were told to
    generate credentials when the fix was to re-copy a file.

    The fallback is not an invented value - it is the pair published in
    .env.example, printed in judge/login.py, announced by /health, and refused
    outside development by the test below.
    """
    for key in ("AUTH_EMAIL", "AUTH_PASSWORD_HASH", "SESSION_SECRET"):
        monkeypatch.delenv(key, raising=False)

    r = _client().post(
        "/auth/login", json={"email": login.DEMO_EMAIL, "password": "modelboard-demo"}
    )
    assert r.status_code == 200


def test_nothing_configured_OUTSIDE_development_still_refuses(monkeypatch):
    """The fallback is a development affordance and stops at the boundary."""
    for key in ("AUTH_EMAIL", "AUTH_PASSWORD_HASH", "SESSION_SECRET"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ENVIRONMENT", "staging")

    r = _client().post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 503
    assert "AUTH_EMAIL" in r.json()["detail"]


def test_a_half_configured_account_does_not_get_a_demo_password(monkeypatch):
    """An email with no hash must not silently acquire the demo one.

    That would be a login the operator never configured, attached to an address
    they did choose - which looks configured and is not.
    """
    monkeypatch.setenv("AUTH_EMAIL", "someone@example.com")
    monkeypatch.delenv("AUTH_PASSWORD_HASH", raising=False)

    r = _client().post(
        "/auth/login", json={"email": "someone@example.com", "password": "modelboard-demo"}
    )
    assert r.status_code == 503


def test_a_configured_account_is_not_overridden_by_the_fallback(monkeypatch):
    """Setting your own credentials must actually replace the demo ones."""
    monkeypatch.setenv("AUTH_EMAIL", "real@example.com")
    monkeypatch.setenv("AUTH_PASSWORD_HASH", login.hash_password("a-real-password"))
    monkeypatch.setenv("SESSION_SECRET", "a-real-secret")
    c = _client()

    assert c.post(
        "/auth/login", json={"email": login.DEMO_EMAIL, "password": "modelboard-demo"}
    ).status_code == 401
    assert c.post(
        "/auth/login", json={"email": "real@example.com", "password": "a-real-password"}
    ).status_code == 200


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


# ── the credentials that ship in the repo ───────────────────────────────────


DEMO_PASSWORD = "modelboard-demo"


@pytest.fixture
def _published(monkeypatch):
    """Exactly what a fresh clone gets from .env.example."""
    monkeypatch.setenv("AUTH_EMAIL", login.DEMO_EMAIL)
    monkeypatch.setenv("AUTH_PASSWORD_HASH", login.DEMO_PASSWORD_HASH)
    monkeypatch.setenv("SESSION_SECRET", login.DEMO_SESSION_SECRET)


def test_the_shipped_password_actually_works(_published):
    """If this fails, every collaborator's first five minutes are wasted."""
    r = _client().post(
        "/auth/login", json={"email": login.DEMO_EMAIL, "password": DEMO_PASSWORD}
    )
    assert r.status_code == 200


def test_the_shipped_credentials_are_recognised_as_published(_published):
    assert login.uses_published_credentials() is True


def test_generated_credentials_are_not(monkeypatch):
    monkeypatch.setenv("AUTH_PASSWORD_HASH", login.hash_password("something-else"))
    monkeypatch.setenv("SESSION_SECRET", "a-real-secret")
    assert login.uses_published_credentials() is False


def test_the_shipped_credentials_are_REFUSED_outside_development(_published, monkeypatch):
    """The published SESSION_SECRET lets anyone forge a token for any account.

    A deployment running on it has a sign-in that checks nothing, so this
    refuses rather than warning - a warning in a comment is what lets it travel.
    """
    monkeypatch.setenv("ENVIRONMENT", "staging")
    r = _client().post(
        "/auth/login", json={"email": login.DEMO_EMAIL, "password": DEMO_PASSWORD}
    )
    assert r.status_code == 503
    assert "judge.credentials" in r.json()["detail"]


def test_replacing_only_the_password_is_not_enough(_published, monkeypatch):
    """The secret is the dangerous half, so a fresh password alone must not pass.

    Someone hardening a deployment reaches for the password first. If that
    silenced the refusal, the forgeable secret would survive the one moment
    anybody was looking at this.
    """
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("AUTH_PASSWORD_HASH", login.hash_password("a-new-password"))

    r = _client().post(
        "/auth/login", json={"email": login.DEMO_EMAIL, "password": "a-new-password"}
    )
    assert r.status_code == 503


def test_health_reports_that_the_demo_login_is_in_use(_published):
    body = _client().get("/health").json()
    assert "demo_credentials" in body["auth"]


# ── ALLOW_DEMO_LOGIN: the flag that used to be ENVIRONMENT's second job ─────


def test_staging_locked_the_demo_login_out_which_is_the_bug_this_fixes(
    _published, monkeypatch
):
    """ENVIRONMENT=staging is CORRECT when reading the shared database.

    It turns the build-fixture guard back on. It also, as a side effect nobody
    chose, refused the shipped login - two correct settings, one variable.
    """
    monkeypatch.setenv("ENVIRONMENT", "staging")
    r = _client().post(
        "/auth/login", json={"email": login.DEMO_EMAIL, "password": DEMO_PASSWORD}
    )
    assert r.status_code == 503


def test_ALLOW_DEMO_LOGIN_true_restores_it_without_touching_the_fixture_guard(
    _published, monkeypatch
):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("ALLOW_DEMO_LOGIN", "true")

    r = _client().post(
        "/auth/login", json={"email": login.DEMO_EMAIL, "password": DEMO_PASSWORD}
    )
    assert r.status_code == 200
    # and the flag it used to be tangled with is untouched
    import os

    assert os.environ["ENVIRONMENT"] == "staging"


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_the_affirmative_spellings_all_work(_published, monkeypatch, value):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_DEMO_LOGIN", value)
    assert login.demo_login_allowed() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off"])
def test_it_can_be_turned_OFF_even_in_development(monkeypatch, value):
    """The override points both ways, so a shared dev box can refuse it."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ALLOW_DEMO_LOGIN", value)
    assert login.demo_login_allowed() is False


def test_an_unrecognised_value_falls_back_to_ENVIRONMENT_rather_than_to_true():
    """`ALLOW_DEMO_LOGIN=maybe` must not read as permission.

    The safe direction for a value nobody can parse is the derived default,
    not the permissive one.
    """
    import os

    os.environ["ENVIRONMENT"] = "production"
    os.environ["ALLOW_DEMO_LOGIN"] = "maybe"
    try:
        assert login.demo_login_allowed() is False
    finally:
        os.environ.pop("ALLOW_DEMO_LOGIN", None)


def test_env_example_does_not_switch_it_on():
    """Copying the shipped file must not be able to enable this.

    Turning it on has to be something a person typed, which is the entire
    difference between this and the flag it replaced.
    """
    import pathlib

    text = pathlib.Path(__file__).resolve().parents[1].joinpath(".env.example").read_text(
        encoding="utf-8"
    )
    active = [
        line for line in text.splitlines()
        if line.strip().startswith("ALLOW_DEMO_LOGIN=")
    ]
    assert active == [], active
