"""Who may call this API, and how often.

WHY THIS EXISTS. Every route in `judge/app.py` was reachable by anyone who could
open a socket to it. Not a weak check - `Depends`, `HTTPBearer`, `Security` and
`OAuth2` appear nowhere in the file, so there was no gate to tighten. Two of
those routes make that expensive rather than merely untidy:

    /admin/usage      reports spend on the OpenRouter key, including a
                      cross-machine total for "every machine using this API key"
    /ask/understand   is the one endpoint that spends money, and its cap is
                      per-process, so an open one is an open wallet

AN UNSET TOKEN IS A MISSING DECISION, AND THE ANSWER DEPENDS ON WHERE YOU ARE.

`judge/ask/spend.py` already draws this distinction and it is the right one: a
person typing a command has decided something; an anonymous HTTP request has
not. So the rule here is not "default open" or "default closed", it is:

    API_TOKEN set                       every route needs a bearer token
    unset, ENVIRONMENT=development      open, and /health SAYS it is open
    unset, anywhere else                refused, because nobody chose

The middle case is what keeps a fresh clone usable - the thing that would
otherwise make people delete this file on day one. The third is what stops the
middle case from following someone to a server by accident, which is exactly how
an unauthenticated board reaches the internet.

`/health` is always reachable. A liveness probe that needs a credential is a
liveness probe that reports the credential, and it deliberately reports the auth
state so "is this thing exposed" is answerable without guessing.

WHAT THIS IS NOT. A shared bearer token is one secret for all callers, with no
identity, no revocation and no audit. It is the smallest thing that closes an
open door, not an authentication system - see `web/src/auth.js`, which says the
same about its own half. Sessions with per-user identity replace both.
"""
from __future__ import annotations

import hmac
import os
import time
from collections import deque
from threading import Lock

from fastapi import Header, HTTPException, Request

from judge import login

DEV = "development"


def _token() -> str:
    return (os.getenv("API_TOKEN") or "").strip()


def _environment() -> str:
    return (os.getenv("ENVIRONMENT") or DEV).strip().lower()


def auth_state() -> dict[str, object]:
    """What `/health` reports, so exposure is answerable rather than assumed."""
    state: dict[str, object] = {}

    # Reported whether or not it is currently refusing, because "are we on the
    # published demo login" is a question an operator should be able to answer
    # from outside the box rather than by reading someone's .env.
    if login.uses_published_credentials():
        state["demo_credentials"] = (
            "sign-in is using the credentials published in .env.example. The signing "
            "secret is public, so any token can be forged - fine locally, never on "
            "anything reachable. Replace with `python -m judge.credentials`."
        )
        state["demo_login_allowed"] = login.demo_login_allowed()

    if _token():
        return {**state, "required": True, "reason": "API_TOKEN is set"}
    if _environment() == DEV:
        return {
            **state,
            "required": False,
            "reason": (
                "no API_TOKEN and ENVIRONMENT=development, so this API is OPEN. "
                "Set API_TOKEN before exposing it to anything but localhost."
            ),
        }
    return {
        **state,
        "required": True,
        "reason": f"no API_TOKEN and ENVIRONMENT={_environment()}, so every route refuses",
    }


#: Reachable without a token. `dependencies=[]` on a route does NOT remove an
#: app-level dependency in FastAPI - app-level ones always run - so the
#: exemption has to be made here, by path. Found by the test that asserted
#: /health still answered with a token set; it did not.
#:
#: `/auth/login` is exempt for the obvious reason: it is where a caller GETS a
#: credential, so requiring one to reach it would be a closed loop. It is also
#: the one unauthenticated route that can be brute-forced, which is why it is
#: rate-limited separately.
EXEMPT_PATHS = frozenset({"/health", "/auth/login"})


def require_token(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    """FastAPI dependency. Raises, or returns None and lets the route run."""
    if request.url.path in EXEMPT_PATHS:
        return

    expected = _token()

    if not expected:
        if _environment() == DEV:
            return
        raise HTTPException(
            status_code=503,
            detail=(
                f"no API_TOKEN is set and ENVIRONMENT is {_environment()!r}, so this "
                "API refuses rather than serving the board to anyone who can reach "
                "it. This is a missing decision, not a fault. Set API_TOKEN, or set "
                "ENVIRONMENT=development if this really is a local machine."
            ),
        )

    supplied = ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()

    if not supplied:
        raise HTTPException(
            status_code=401,
            detail="this API needs `Authorization: Bearer <token>`.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # TWO KINDS OF BEARER, and the order matters only for cost.
    #
    #   the static API_TOKEN   one shared secret for machine callers, and for a
    #                          deployment that wants the whole board closed
    #   a signed session       what /auth/login issues to a person
    #
    # compare_digest first, so a wrong token takes the same time as a
    # nearly-right one; `login.read` verifies its own HMAC the same way.
    if hmac.compare_digest(supplied, expected):
        return

    if login.read(supplied):
        return

    raise HTTPException(
        status_code=401,
        detail="that token is not valid, or it has expired. Sign in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ── rate limiting the one endpoint that spends money ────────────────────────
#
# IN-PROCESS AND PER-MACHINE, and that is a real limit rather than a shortcut
# nobody noticed. Two workers are two allowances, and a restart forgets
# everything. It is the same shape as the spend cap, which `/admin/usage`
# already labels "this machine's ledger only" - so this shares that honesty
# rather than implying a guarantee it cannot make.
#
# It still does the job it is here for: an open ask box is a stranger spending
# your OpenRouter balance, and a fixed window per client stops one caller
# draining the daily cap in a loop. A shared limiter belongs with the shared
# ledger in `model_call`, which is already on the list as a contract change.

_WINDOW_SECONDS = 3600
_hits: dict[str, deque[float]] = {}
_hits_lock = Lock()


def _limit() -> int:
    raw = (os.getenv("ASK_RATE_PER_HOUR") or "").strip()
    if not raw:
        return 20
    try:
        return max(0, int(raw))
    except ValueError:
        return 20


def rate_limit_ask(request: Request) -> None:
    """Fixed window per client, on `/ask/understand` only.

    Keyed on the socket peer. Behind a proxy every caller shares one key, which
    throttles everyone together instead of nobody - the safe direction to be
    wrong in, and the reason this does not read X-Forwarded-For: a header the
    client controls is a rate limit the client controls.
    """
    limit = _limit()
    if limit <= 0:
        return

    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS

    with _hits_lock:
        seen = _hits.setdefault(key, deque())
        while seen and seen[0] < cutoff:
            seen.popleft()
        if len(seen) >= limit:
            retry = int(seen[0] - cutoff) + 1
            raise HTTPException(
                status_code=429,
                detail=(
                    f"{limit} model-backed requests an hour from one caller is the "
                    "limit on this endpoint, and it is the only one that spends "
                    "money. Nothing is wrong with your request. Try again in "
                    f"{retry}s, or raise ASK_RATE_PER_HOUR."
                ),
                headers={"Retry-After": str(retry)},
            )
        seen.append(now)


def rate_limit_login(request: Request) -> None:
    """Brute force is the only attack /auth/login is exposed to, so bound it.

    A separate bucket from the ask limiter, because they defend different
    things: that one protects a budget, this one protects a password. Sharing a
    counter would let ordinary use of the Ask box exhaust the sign-in allowance,
    which is a lockout caused by unrelated traffic.
    """
    limit = _int_env("LOGIN_RATE_PER_HOUR", 10)
    if limit <= 0:
        return

    key = f"login:{request.client.host if request.client else 'unknown'}"
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS

    with _hits_lock:
        seen = _hits.setdefault(key, deque())
        while seen and seen[0] < cutoff:
            seen.popleft()
        if len(seen) >= limit:
            retry = int(seen[0] - cutoff) + 1
            raise HTTPException(
                status_code=429,
                detail=(
                    f"{limit} sign-in attempts an hour from one address is the limit. "
                    f"Try again in {retry}s."
                ),
                headers={"Retry-After": str(retry)},
            )
        seen.append(now)


def _int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _reset_for_tests() -> None:
    with _hits_lock:
        _hits.clear()
