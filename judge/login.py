"""Sign-in, with the credential on the server instead of in the bundle.

WHAT THIS REPLACES. `web/src/auth.js` held an email and an unsalted SHA-256 of
the password as literals. It shipped in the JavaScript, so the credential was
readable by anyone who opened the page, and the check ran in the browser, so it
was skippable from the console. Its own header said so. Moving the secret to
`.env` is the whole point of this module: the browser now sends a password and
receives a token, and never holds the thing that proves who you are.

THREE CHOICES WORTH THE WORDS.

**PBKDF2 from hashlib, not bcrypt or argon2.** Those are better and both are a
new dependency. This is one account for a demo board; the property that matters
is that a leaked `.env` does not hand over a reusable password, and 600k
iterations of PBKDF2-SHA256 gives that. `hash_password()` is here so the hash is
generated the same way it is checked - a hash produced by a different tool with
different parameters is the classic way this goes wrong quietly.

**A signed token, not a session table.** The token carries its own expiry and an
HMAC over it, so there is nothing to store and nothing to clean up. The cost is
real and is stated rather than hidden: a signed token cannot be revoked before
it expires. For one demo account with a short life that is the right trade; for
per-user accounts it is not, and the fix then is a session table, not a longer
secret.

**`SESSION_SECRET` unset means sign-in is unavailable, not that it is open.**
Generating a random secret at startup would look like it worked, then invalidate
every token on restart - the same class of "a missing value quietly becoming a
definite one" that rule 6 forbids. It refuses and says which variable is absent.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

ITERATIONS = 600_000
ALGORITHM = "pbkdf2_sha256"
DEFAULT_TTL_HOURS = 12


def hash_password(password: str, *, salt: str | None = None) -> str:
    """`pbkdf2_sha256$iterations$salt$hash`, the format `verify` expects."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time, and False rather than raising on a malformed hash."""
    try:
        algorithm, iterations, salt, expected = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), int(iterations)
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(digest.hex(), expected)


# ── configuration ───────────────────────────────────────────────────────────


def _secret() -> str:
    return (os.getenv("SESSION_SECRET") or "").strip()


def account() -> tuple[str, str]:
    """(email, password_hash) from the environment. Empty strings when unset."""
    return (
        (os.getenv("AUTH_EMAIL") or "").strip().lower(),
        (os.getenv("AUTH_PASSWORD_HASH") or "").strip(),
    )


def is_configured() -> bool:
    email, password_hash = account()
    return bool(email and password_hash and _secret())


def ttl_seconds() -> int:
    raw = (os.getenv("SESSION_TTL_HOURS") or "").strip()
    try:
        return max(1, int(float(raw or DEFAULT_TTL_HOURS) * 3600))
    except ValueError:
        return DEFAULT_TTL_HOURS * 3600


# ── tokens ──────────────────────────────────────────────────────────────────


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue(email: str, *, now: float | None = None) -> tuple[str, int]:
    """A signed token and the unix time it stops being valid."""
    secret = _secret()
    if not secret:
        raise RuntimeError("SESSION_SECRET is unset")

    expires = int((now if now is not None else time.time()) + ttl_seconds())
    payload = _b64(json.dumps({"sub": email, "exp": expires}, separators=(",", ":")).encode())
    signature = _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}", expires


def read(token: str, *, now: float | None = None) -> str | None:
    """The email a valid token belongs to, or None.

    SIGNATURE FIRST, THEN EXPIRY. Checking expiry first would answer questions
    about tokens nobody signed.
    """
    secret = _secret()
    if not secret or not token or "." not in token:
        return None

    payload, _, signature = token.partition(".")
    expected = _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return None

    try:
        claims = json.loads(_unb64(payload))
    except (ValueError, json.JSONDecodeError):
        return None

    if float(claims.get("exp", 0)) <= (now if now is not None else time.time()):
        return None
    return str(claims.get("sub") or "") or None


def authenticate(email: str, password: str) -> bool:
    """One account, and both halves are always checked.

    A short-circuit on the email would make a wrong address measurably faster
    than a wrong password, which is a free answer to "does this account exist".
    """
    configured_email, password_hash = account()
    if not configured_email or not password_hash:
        return False

    email_ok = hmac.compare_digest((email or "").strip().lower(), configured_email)
    password_ok = verify_password(password or "", password_hash)
    return email_ok and password_ok
