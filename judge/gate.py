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

#: THE PUBLIC READS (2026-10-15, Parvathi): what the published pages - home,
#: Models, the tools, Compare, Blogs, FAQ, the glossary - read, reachable WITHOUT a token so
#: a visitor who has not signed in can use them. The sign-in wall now guards
#: only the signed-in surfaces: the Board, the old model pages and Admin.
#:
#: GET ONLY, AND EACH ONE CHECKED FOR WHAT IT SENDS. Every path here returns
#: counts, advertised specs or reviewed copy over the PUBLIC view - no quote,
#: link or handle from a withheld source - except two, which are handled:
#:   /compare      carries quotes and post links; for an anonymous caller the
#:                 endpoint strips them and forces the public view
#:                 (judge/app.py: compare_page).
#:   /blog-posts   only its default, `include=public` - the APPROVED posts as
#:                 they were reviewed. `include=all` (drafts, the review queue)
#:                 still needs a token.
#: Anything not listed - the Board's endpoints, a model's evidence, every
#: write, every admin route - is unchanged: it needs a token.
PUBLIC_READ_PATHS = frozenset({
    "/reports", "/model-catalog", "/faq", "/models", "/freshness",
    "/seo/indexable", "/blog-posts", "/compare",
    # 2026-10-20: the Discussions page - topics and APPROVED posts only
    # (judge/discussions.py public_view; the review queue is /discussions/review).
    "/discussions",
    # 2026-10-20: the glossary index (judge/glossary.py) - reviewed copy, no source text.
    "/glossary-terms",
    # 2026-10-21 (PROPOSED): the evidence feed and a model's APPROVED summary
    # (judge/feed/). Our paraphrases, tags, dates and sources - an official
    # embed for Reddit and X, a link otherwise - and never a quote, under
    # contract/publication.yaml `evidence_feed`. Drafts (/feed/summaries)
    # still need a token. /feed/models (2026-10-23) is the seated ids the
    # pages link into the feed for - model ids only.
    "/feed", "/feed/summary", "/feed/models",
    # 2026-10-23: the local VRAM tool (judge/local_models.py) - file sizes and
    # header fields measured from Hugging Face, prices from our own registry,
    # and contract constants. No quote or text from any source.
    "/local-models",
    # 2026-10-29 (PROPOSED): the home page's updates strip (judge/updates.py
    # published) - the words of updates a person approved AND published, their
    # kind and publish time. Nothing from Manage: no reviewer, draft or style.
    "/updates/published",
    # 2026-10-30 (PROPOSED, Parvathi): the AI benchmarks page
    # (judge/benchmarks.py charts) - per value the shown figure, its benchmark,
    # the board's rank and "out of", and the source's name, link and date. No
    # value a person has not checked (`needs_review`), no source's spelling of a
    # model, no other source's value. The sources' terms: one accepted-risk note
    # in contract/benchmarks/sources.yaml (#589); the page stays out of search
    # engines. Removing this line takes the page behind the sign-in at once.
    "/ai-benchmarks",
    # 2026-10-30 (PROPOSED): the verified-facts box inside a migration guide
    # (judge/migrations.py `guide`) - the registry's published facts for the
    # guide's two models, a checklist worded by contract/migrations.yaml, and
    # counts of board entries. No quote, post text or source from any platform.
    "/guide-facts",
    # 2026-10-30 (PROPOSED, Parvathi): the public AI updates page (judge/updates.py
    # approved) - the words of every update a person APPROVED in Manage, its
    # kind, label and date. Nothing else from Manage: no reviewer, style,
    # status or draft, and no update nobody approved.
    "/updates/approved",
})
#: /glossary-terms/<slug> (2026-10-20): one glossary paragraph - reviewed copy
#: from glossary.yaml, no quote, link or handle from any source.
PUBLIC_READ_PREFIXES = ("/model-catalog/", "/glossary-terms/")

#: THE ONE PUBLIC WRITE (2026-10-20, Parvathi): a reader posting to the
#: Discussions page. POST only, rate-limited per address (rate_limit_discussion),
#: and what it writes is stored `pending` - shown to nobody until a person
#: approves it in Admin. Every other write still needs a token.
PUBLIC_WRITE_PATHS = frozenset({"/discussions/posts"})


def is_public_read(request: Request) -> bool:
    """True when this request may be served to a caller with no token."""
    if request.method not in ("GET", "HEAD"):
        return False
    path = request.url.path
    if path not in PUBLIC_READ_PATHS and not path.startswith(PUBLIC_READ_PREFIXES):
        return False
    # the approved posts only; drafts and the review queue still need a token
    return path != "/blog-posts" or request.query_params.get("include", "public") == "public"


def is_public_write(request: Request) -> bool:
    """True for the one write a caller with no token may make."""
    return request.method == "POST" and request.url.path in PUBLIC_WRITE_PATHS


def require_token(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    """FastAPI dependency. Raises, or returns None and lets the route run."""
    if request.url.path in EXEMPT_PATHS:
        return

    # A PUBLIC READ WITH NO VALID TOKEN IS SERVED AS ANONYMOUS, and says so on
    # the request, so an endpoint that holds more than counts (/compare) can
    # strip it. A valid token still marks the caller as signed in. An invalid
    # or expired one is treated as no token here rather than refused: a stale
    # session in a browser must not break the public pages.
    request.state.anonymous = False
    if is_public_read(request) or is_public_write(request):
        supplied_public = ""
        if authorization and authorization.lower().startswith("bearer "):
            supplied_public = authorization[7:].strip()
        expected_public = _token()
        signed_in = bool(supplied_public) and (
            (bool(expected_public) and hmac.compare_digest(supplied_public, expected_public))
            or bool(login.read(supplied_public))
        )
        request.state.anonymous = not signed_in and bool(expected_public or _environment() != DEV)
        if not signed_in:
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


def rate_limit_discussion(request: Request) -> None:
    """A reader may post a few times an hour from one address, no more.

    The one public write (PUBLIC_WRITE_PATHS) is the one an anonymous script
    can hammer, so it gets its own bucket: posting cannot exhaust the sign-in
    allowance, and the other way round. The default is the contract's
    (contract/discussions.yaml `limits.posts_per_hour`); DISCUSSION_RATE_PER_HOUR
    overrides it, and 0 turns it off deliberately.
    """
    default = 5
    try:
        from judge.discussions import settings

        default = settings()["limits"]["posts_per_hour"]
    except Exception:  # noqa: BLE001 - an unreadable contract must not open the door wider
        pass
    limit = _int_env("DISCUSSION_RATE_PER_HOUR", default)
    if limit <= 0:
        return

    # WHO IS POSTING. Hosted, every request reaches us from the platform's
    # proxy, so the socket peer is the same for every reader and one bucket
    # would throttle the whole site to `limit` posts an hour. The RIGHTMOST
    # X-Forwarded-For entry is the one the proxy itself appended - the reader
    # can forge entries to its left, never that one. With no header (a local
    # run, no proxy) it is the socket peer, as for the other limiters.
    forwarded = [h.strip() for h in (request.headers.get("x-forwarded-for") or "").split(",")
                 if h.strip()]
    who = forwarded[-1] if forwarded else (request.client.host if request.client else "unknown")
    key = f"discussion:{who}"
    # AND A CEILING FOR THE WHOLE SITE, so a flood is bounded even if the
    # per-address key is wrong somewhere. DISCUSSION_RATE_TOTAL_PER_HOUR.
    total_key, total_limit = "discussion:*", _int_env("DISCUSSION_RATE_TOTAL_PER_HOUR", 100)
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS

    with _hits_lock:
        everyone = _hits.setdefault(total_key, deque())
        while everyone and everyone[0] < cutoff:
            everyone.popleft()
        if total_limit > 0 and len(everyone) >= total_limit:
            retry = int(everyone[0] - cutoff) + 1
            raise HTTPException(
                status_code=429,
                detail="Posting is busy right now. Try again in a few minutes.",
                headers={"Retry-After": str(retry)},
            )
        seen = _hits.setdefault(key, deque())
        while seen and seen[0] < cutoff:
            seen.popleft()
        if len(seen) >= limit:
            retry = int(seen[0] - cutoff) + 1
            raise HTTPException(
                status_code=429,
                detail=(
                    f"{limit} posts an hour from one address is the limit. "
                    f"Try again in {(retry + 59) // 60} min."
                ),
                headers={"Retry-After": str(retry)},
            )
        seen.append(now)
        everyone.append(now)


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
