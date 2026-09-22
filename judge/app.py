"""The Ask box.

Free text in, a structured requirement profile out. Ranking against real cells
arrives once collect/ is producing evidence; until then this runs on
hand-written cells, and the UX test could not tell the difference - which was
the point of shipping it first.

Nothing here touches the evidence pipeline. The answer path reads a
materialised view and nothing else, so a broken or stopped harvest never
degrades this surface.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import subprocess
import sys
import threading
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from judge import fetch_reaper, login
from judge.ask import requirements, spend
from judge.ask.profile import Assumption, RoleRequirement
from judge.ask.rank import guard_for
from judge.ask.understand import (
    InputShape,
    UnderstandingRefused,
    understand,
)
from judge.config import capabilities
from judge.extract.client import OpenRouterClient
from judge.gate import auth_state, rate_limit_ask, rate_limit_login, require_token
from judge.writeguard import describe, is_read_only_dsn

#: How many rows a list endpoint returns when the caller does not say.
#:
#: `/models` was 130 KB and `/capabilities/{key}` 56 KB, both the whole table in
#: one response, and both grow with the registry rather than with anything the
#: caller asked for. 100 covers the frontend's first screen comfortably.
#:
#: The default is a PAGE and not the whole set on purpose: a default of
#: everything means the first caller to hit a slow response is a user, and the
#: fix is a client change rather than a parameter.
DEFAULT_PAGE = 100
MAX_PAGE = 1000

#: Where `scripts/fetch_model.py` writes its per-run progress log, and where the
#: fetch-log endpoint reads it. Repo root / var / fetch (gitignored, local).
_REPO_ROOT = Path(__file__).resolve().parents[1]
_FETCH_DIR = _REPO_ROOT / "var" / "fetch"


class _Page(NamedTuple):
    items: list
    meta: dict


def _page(rows: list, *, limit: int, offset: int) -> _Page:
    """One window over `rows`, and enough metadata to know it is a window.

    `has_more` is stated rather than left to be inferred from
    `len(items) == limit`, which is wrong exactly once - on the last page that
    happens to be full - and wrong in the direction that makes a caller stop
    early or loop forever.
    """
    total = len(rows)
    limit = max(0, min(int(limit), MAX_PAGE))
    offset = max(0, int(offset))
    items = rows[offset : offset + limit] if limit else []
    return _Page(
        items=items,
        meta={
            "total": total,
            "limit": limit,
            "offset": offset,
            "returned": len(items),
            "has_more": offset + len(items) < total,
            "max_limit": MAX_PAGE,
        },
    )


#: Startup and refusal lines go to uvicorn's own logger rather than to
#: `logging.getLogger(__name__)`, and the NAME is the whole point.
#:
#: uvicorn configures handlers for `uvicorn`, `uvicorn.error` and
#: `uvicorn.access`, and configures NOTHING on the root logger. A module logger
#: therefore propagates to a root with no handler, falls through to
#: `logging.lastResort`, and is DROPPED below WARNING - so an `info` line
#: naming the database would never have reached the terminal that needed it.
#: Borrowing uvicorn's logger puts these lines in the same stream, at the same
#: level, as `Application startup complete`.
#:
#: Outside uvicorn - the tests import this module - the logger has no handler
#: and these calls are inert, which is the right behaviour there.
log = logging.getLogger("uvicorn.error")


def _log_database_target() -> None:
    """Say which database this process will read, once, at startup.

    WHAT THIS WOULD HAVE SAVED, 2026-09-11. A backend started as
    `uvicorn judge.app:app` rather than through `run-backend.py` has no
    DATABASE_URL at all, because that script is the only thing that loads
    `.env`. Every database-backed route then answers 503, the frontend renders
    "no database connection", and that message names nothing: it is the
    frontend's rendering of a failure it did not cause. Diagnosing it took
    process inspection and a timing measurement. One line here answers it
    before the first request arrives.

    THE CREDENTIALS ARE NOT LOGGED. `describe` returns host, port and database
    name and nothing else - the DSN itself never reaches a log record, here or
    in `_conn`.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        log.warning(
            "DATABASE_URL is not set in this process. Every database-backed "
            "route will answer 503 and NO connection will be attempted. `.env` "
            "is loaded by run-backend.py, not by this module, so a server "
            "started directly with `uvicorn judge.app:app` sees none of it."
        )
        return
    log.info(
        "database: %s - %s",
        describe(url),
        "sessions forced READ ONLY by the DSN"
        if is_read_only_dsn(url)
        else "READ-WRITE session",
    )


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Startup and shutdown. It exists for the one startup line above.

    `@app.on_event("startup")` would do the same and is deprecated in FastAPI
    0.139, which is what is installed here.
    """
    _log_database_target()
    yield


app = FastAPI(
    title="Model Information Board",
    description=(
        "What engineers actually say about AI models, and which cheaper one is safe for your task."
    ),
    version="0.1.0",
    lifespan=_lifespan,
    # EVERY ROUTE, rather than a decorator per handler. An app-wide dependency
    # cannot be forgotten on the next endpoint somebody adds, and forgetting one
    # is the whole failure mode here - the gap this closes was not a weak check,
    # it was no check anywhere. `/health` opts back out explicitly below, which
    # is a visible exception instead of an invisible omission.
    dependencies=[Depends(require_token)],
)


# ── CORS: off by default, and never `*` ───────────────────────────────────────
#
# THERE WAS NO CORS MIDDLEWARE HERE AT ALL, AND THAT WAS CORRECT UNTIL NOW.
# `web/vite.config.js` says why: "The backend runs no CORS middleware, so in dev
# we proxy rather than ask them to add one." One origin needs no header, and a
# header nobody needs is a door nobody is watching.
#
# A two-service deployment is two origins, and the browser refuses the call
# before this process ever sees it - so the failure is a console message on
# somebody else's machine and a board that renders empty. That is the "breaks
# silently" case, and it is why this is configured rather than discovered.
#
# `ALLOWED_ORIGINS` IS A LIST, NOT A WILDCARD, and the middleware is not
# installed at all when it is unset:
#
#   unset            no middleware. Same-origin deployments and local dev are
#                    unchanged, and nothing is loosened by accident.
#   a comma list     exactly those origins, credentials allowed.
#   "*"             REFUSED at startup, below.
#
# `*` is refused rather than warned about because it cannot do what a reader
# would assume: the CORS spec forbids `*` with credentials, so a wildcard here
# silently turns the credentialed requests OFF rather than opening them up. A
# setting whose effect is the opposite of its appearance is worse than no
# setting, and this API carries a bearer token on every route that is not
# `/health` or `/auth/login`.
_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in (os.getenv("ALLOWED_ORIGINS") or "").split(",")
    if origin.strip()
]
if "*" in _ALLOWED_ORIGINS:
    raise RuntimeError(
        "ALLOWED_ORIGINS contains '*'. The CORS spec forbids a wildcard origin "
        "with credentials, so this would disable the credentialed requests it "
        "looks like it is enabling - and every route here except /health and "
        "/auth/login carries a bearer token. Name the frontend's origin "
        "instead, e.g. https://<service>.up.railway.app (scheme and host, no "
        "trailing slash)."
    )
if _ALLOWED_ORIGINS:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_ALLOWED_ORIGINS,
        # The session token rides in an `Authorization` header, not a cookie,
        # so this is not strictly required today. It is set because
        # `judge/login.py` may move to a cookie and the failure if it does
        # would be a login that succeeds and a board that 401s.
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


class AskRequest(BaseModel):
    """What the user typed, plus anything they chose to pin down.

    Every field left None is guessed, and every guess comes back as an
    editable assumption. Guessing silently is the failure mode of every
    "AI picks for you" product.
    """

    task: str = Field(
        description="the work, in your own words",
        examples=[
            "summarize incoming support tickets into weekly themes, "
            "20k tickets a day, output must be valid JSON, internal tool"
        ],
    )
    input_tokens: int | None = None
    output_tokens: int | None = None
    tool_count: int | None = None
    requests_per_month: int | None = Field(
        default=None,
        description=(
            "REQUESTS, never per-role calls. Role volume is derived from "
            "runs_per_request, and multiplied exactly once."
        ),
    )
    regions: list[str] | None = None


class AskResponse(BaseModel):
    requirement: RoleRequirement
    guard: str | None = Field(
        default=None,
        description="the safety net a borderline-but-cheap pick would need",
    )
    note: str


@app.get("/health")
def health() -> dict[str, object]:
    """Liveness, and deliberately the one route that needs no token.

    A probe that needs a credential is a probe that has to carry one. It also
    reports `auth`, so "is this board exposed?" is answerable with one
    unauthenticated GET rather than inferred from config nobody can see.

    The exemption lives in `gate.EXEMPT_PATHS`, not in a `dependencies=[]` here:
    an app-level dependency in FastAPI runs for every route and a route cannot
    opt out of it. Writing `dependencies=[]` looks exactly like an exemption and
    is not one.
    """
    return {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "capabilities_loaded": len(capabilities()),
        "auth": auth_state(),
    }


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_at: int
    email: str


@app.post(
    "/auth/login",
    response_model=LoginResponse,
    dependencies=[Depends(rate_limit_login)],
)
def sign_in(req: LoginRequest) -> LoginResponse:
    """Exchange a password for a signed token.

    THE CREDENTIAL LIVES IN .env AND NOT IN THE BUNDLE. `web/src/auth.js` used
    to hold an email and an unsalted SHA-256 as literals, which shipped to every
    visitor and was checked in the browser - readable and skippable. The browser
    now sends a password once and holds only a token.

    ONE MESSAGE FOR EVERY FAILURE. A wrong address and a wrong password get the
    same 401 with the same text, and `authenticate()` checks both halves either
    way, so neither the wording nor the timing says whether an account exists.

    503 WHEN UNCONFIGURED, not a fallback to some default account. A missing
    AUTH_EMAIL is a missing decision; inventing a login here would be the exact
    "absent value becomes a definite one" that rule 6 forbids, with the
    definite value being who may read the board.
    """
    if not login.is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "sign-in is not configured on this server. It needs AUTH_EMAIL, "
                "AUTH_PASSWORD_HASH and SESSION_SECRET in .env - generate them with "
                "`python -m judge.credentials`. This is a missing decision rather "
                "than a fault, and every unauthenticated route still answers."
            ),
        )

    # THE PUBLISHED CREDENTIALS ARE A DEVELOPMENT AFFORDANCE AND NOTHING ELSE.
    # `.env.example` ships a working email, hash and signing secret so a fresh
    # clone can sign in without ceremony. The signing secret is the reason this
    # check exists: with it, anyone can mint a valid token for any account
    # without a password, so a deployment running on it has a login that checks
    # nothing. Refused here rather than warned about, because a warning in a
    # comment is what lets it travel.
    if login.uses_published_credentials() and not login.demo_login_allowed():
        raise HTTPException(
            status_code=503,
            detail=(
                "this server is running on the demo credentials published in "
                ".env.example, and ENVIRONMENT is not development. The signing "
                "secret is public, so any token can be forged and sign-in would "
                "check nothing. Either run `python -m judge.credentials` and replace "
                "all three values, or set ALLOW_DEMO_LOGIN=true if this really is a "
                "machine where that is fine."
            ),
        )

    if not login.authenticate(req.email, req.password):
        raise HTTPException(status_code=401, detail="Those details do not match an account.")

    email, _ = login.account()
    token, expires_at = login.issue(email)
    return LoginResponse(token=token, expires_at=expires_at, email=email)


@app.get("/capabilities")
def list_capabilities() -> list[dict[str, object]]:
    """The vocabulary, with the field that drives everything downstream.

    `silent` capabilities require positive consensus — absence of criticism is
    not evidence, because you would not find out you were wrong.
    """
    return [
        {
            "key": c.key,
            "failure_mode": c.failure_mode,
            "requires_positive_consensus": c.fails_silently,
            "sounds_like": list(c.sounds_like),
        }
        for c in capabilities().values()
    ]


@app.post("/ask/requirements", response_model=AskResponse)
def infer_requirements(req: AskRequest) -> AskResponse:
    """Q3 — turn a task description into a checkable requirement profile.

    Deterministic: the same task always produces the same requirements, so the
    reasoning is auditable rather than a model's mood on the day.
    """
    requirement = requirements.infer(
        req.task,
        input_tokens=req.input_tokens,
        output_tokens=req.output_tokens,
        tool_count=req.tool_count,
        regions=req.regions,
    )

    silent = requirement.silent_failure_capabilities
    note = (
        f"{len(silent)} of {len(requirement.capabilities)} capabilities fail silently "
        "and need positive consensus, not merely an absence of complaints."
        if silent
        else "All required capabilities fail loudly, so a validation retry is a real "
        "mitigation and weaker evidence is acceptable."
    )

    return AskResponse(
        requirement=requirement,
        guard=guard_for(requirement),
        note=note,
    )


# ── Q1: free text in, editable assumptions out ────────────────────────────


class UnderstandRequest(BaseModel):
    """Free text, and which of FR-28's three shapes it is.

    The shape is asked for rather than sniffed. They disagree about what
    SILENCE means - a task omitting tools probably needs none, an agent config
    omitting tools may be a config we were handed part of - and guessing which
    kind of document this is would be a silent guess about how to read every
    other silent guess.
    """

    text: str = Field(
        description="the task, product brief, or pasted agent config",
        examples=["summarise incoming support tickets into weekly themes"],
    )
    shape: InputShape = InputShape.TASK


class UnderstandResponse(BaseModel):
    """The profile, and every field we had to guess to build it.

    `assumptions` is not a diagnostic. It is the SAFETY MECHANISM: Q1 has
    nothing to verify its output against, unlike E5, so what makes it safe is
    that the user sees every guess before anything acts on one. A client that
    renders `profile` and drops `assumptions` has removed the guarantee, which
    is why the caveat travels in the same response rather than being available
    from a second call.
    """

    profile: dict
    assumptions: list[Assumption]
    caveat: str | None = Field(
        default=None,
        description="shown above the fields; None when the user stated everything",
    )
    input_tokens: int
    output_tokens: int


@app.post(
    "/ask/understand",
    response_model=UnderstandResponse,
    # The spend cap bounds the DAY. This bounds one caller, so a single client
    # in a loop cannot drain the whole day's allowance before anyone notices.
    dependencies=[Depends(rate_limit_ask)],
)
def understand_task(req: UnderstandRequest) -> UnderstandResponse:
    """Q1 - the first of the two stages permitted to call a model.

    THE BUDGET IS CHECKED HERE TOO. Q1 is the second place this system spends
    money and nothing was counting it - the same defect as the unwired cap, one
    layer over. An uncapped ask box is a bill somebody discovers monthly.

    A refusal is 422 rather than 500: Q1 declining is a decision about the
    input, not a fault. Same distinction the extraction budget draws between a
    stop and a failure.
    """
    # THE TOTAL IS PROCESS-WIDE, not per request. The previous version built a
    # fresh `Budget` here, so `spent_usd` was 0.0 at every check and the 429
    # branch below could not fire for any limit above one call's estimate - a
    # cap with a status code and a test that counted nothing. `judge/ask/spend.py`
    # holds the running total and the charge below records it.
    if not spend.is_configured():
        # An unset cap means nobody decided. `judge/cli.py` may read that as an
        # operator's choice, because a person typed the command; an anonymous
        # request to a public endpoint with no authentication is not a person
        # who decided. Refused rather than run uncapped.
        raise HTTPException(
            status_code=503,
            detail=(
                "the ask path is the one endpoint that spends money and no cap "
                "is configured, so it is refused rather than run uncapped. Set "
                "EXTRACTION_DAILY_BUDGET_USD. This is a missing decision, not a "
                "fault, and not a board with nothing on it - every other "
                "endpoint still answers."
            ),
        )
    try:
        spend.check_before_call()
    except spend.BudgetExhausted as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    # The client is held rather than built inline so the charge below can name
    # the model that actually ran. `Budget.spend_by_model` exists so a mid-run
    # model swap is visible (rule 7); charging a generic label would defeat it.
    client = OpenRouterClient.from_env()
    try:
        result = understand(req.text, client=client, shape=req.shape)
    except UnderstandingRefused as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        # A forged untrusted-block marker. Refused rather than sanitised, as
        # `wrap_untrusted` does for E5.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # CHARGED FROM WHAT THE CALL REPORTED, and this is the half that was
    # missing: without it every check above reads a total of zero forever.
    spend.charge(
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        model=client.model,
    )

    return UnderstandResponse(
        profile=result.profile.model_dump(),
        assumptions=result.assumptions,
        caveat=result.caveat,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )


# ── FR-30: editing an assumption re-runs the recommendation ───────────────


class ReviseRequest(BaseModel):
    """The profile as the user has corrected it.

    NO MODEL RUNS HERE, and that is the point of the endpoint existing
    separately. Q1 guessed; the user has now told us. Re-reading their edits
    through a language model would let it overrule a correction, which is the
    exact failure the editable field was introduced to prevent - and it would
    make the same input produce different requirements on different days.

    So this is Q3 onward, deterministic, over a profile the user owns.
    """

    profile: dict = Field(description="the profile, with the user's corrections applied")
    accepted_assumptions: list[str] = Field(
        default_factory=list,
        description=(
            "fields the user looked at and left alone. Distinct from fields "
            "they never saw - see the response's `still_guessed`."
        ),
    )


class ReviseResponse(BaseModel):
    requirement: RoleRequirement
    guard: str | None = None
    note: str

    still_guessed: list[str] = Field(
        default_factory=list,
        description=(
            "assumptions the user neither corrected nor explicitly accepted. "
            "Rule 6 on a review rather than on a value: a field nobody looked "
            "at is not a field somebody approved, and collapsing the two would "
            "let an unexamined guess acquire the standing of a confirmed one."
        ),
    )


@app.post("/ask/revise", response_model=ReviseResponse)
def revise(req: ReviseRequest) -> ReviseResponse:
    """Re-run the deterministic half after the user edits an assumption.

    FR-30. The editable field is what makes Q1 safe, and a field you can edit
    without anything changing is decoration.
    """
    task = req.profile.get("raw_text", "")
    if not str(task).strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "the revised profile carries no task text. Refused rather than "
                "re-run against an empty task, which would produce a "
                "recommendation about nobody's work."
            ),
        )

    requirement = requirements.infer(
        task,
        input_tokens=req.profile.get("input_tokens"),
        output_tokens=req.profile.get("output_tokens"),
        tool_count=req.profile.get("tool_count"),
        regions=req.profile.get("regions"),
    )

    guessed = [
        field
        for field, value in req.profile.items()
        if field not in req.accepted_assumptions
        and field != "raw_text"
        and value not in (None, [], {}, "")
    ]

    silent = requirement.silent_failure_capabilities
    note = (
        f"{len(silent)} of {len(requirement.capabilities)} capabilities fail silently "
        "and need positive consensus, not merely an absence of complaints."
        if silent
        else "All required capabilities fail loudly, so a validation retry is a real "
        "mitigation and weaker evidence is acceptable."
    )

    return ReviseResponse(
        requirement=requirement,
        guard=guard_for(requirement),
        note=note,
        still_guessed=sorted(guessed),
    )


# ── Q4–Q7: the requirement, ranked against real cells ─────────────────────


@app.post("/ask/recommend")
def recommend(req: AskRequest) -> dict:
    """The answer path, wired at last: task → requirement → ranked models.

    `judge/ask/answer.py`, `rank.py` and `AnswerStore` were all built and
    correct, and nothing read a cell through them — so the Ask box named no
    model. This is that missing caller.

    NO MODEL RUNS HERE. Q1 (`/ask/understand`) is the only LLM step in this
    path; from the requirement onward it is gating, banding and ranking — all
    named by rule 2 as code's job. The justification is assembled from the cells
    that produced it and carries their quote ids (rule 3, FR-34).

    CANDIDATES ARE THE EVIDENCED MODELS — the distinct models in `cell_current`
    (published + contested). A model with no cell cannot qualify and would only
    pad the answer with hundreds of `no_evidence` rows, so the honest shape when
    nothing is published yet is a NAMED ABSTENTION: `answer_for` returns
    `abstained=True` and lists the capabilities that lack evidence, which is a
    different and more useful answer than an empty list (FR-35).

    THE ANSWER IS PERSISTED before it is returned (FR-36), so "why not X?" is
    answerable against what we said at the time rather than what the cells would
    say tonight. This endpoint therefore WRITES (task_profile, role, answer);
    those are additive rows, and the commit is here because `answer_for` leaves
    the transaction to its caller.
    """
    from judge.ask.answer import answer_for
    from judge.store.answers import AnswerStore

    requirement = requirements.infer(
        req.task,
        input_tokens=req.input_tokens,
        output_tokens=req.output_tokens,
        tool_count=req.tool_count,
        regions=req.regions,
    )

    with _conn() as conn:
        store = AnswerStore(conn)
        profile_id = store.write_profile(
            raw_text=req.task,
            profile=requirement.model_dump(),
            inferred_fields=tuple(a.field for a in requirement.assumptions),
            complexity_tier=requirement.complexity_tier,
            error_cost=requirement.error_cost,
            requests_per_month=req.requests_per_month,
        )
        role_id = store.write_role(
            task_profile_id=profile_id,
            name="task",
            capability_needs={
                c.key: {"condition_bucket": c.condition_bucket, "failure_mode": c.failure_mode}
                for c in requirement.capabilities
            },
            error_cost=requirement.error_cost,
        )

        rows = conn.execute(
            """
            SELECT DISTINCT cc.model_version_id, mv.display_name
            FROM cell_current cc
            JOIN model_version mv ON mv.id = cc.model_version_id
            """
        ).fetchall()
        names = {mv_id: (display or mv_id) for mv_id, display in rows}

        answer = answer_for(
            conn,
            role_id=role_id,
            requirement=requirement,
            model_version_ids=list(names),
            display_names=names,
            assumptions=tuple(a.render() for a in requirement.assumptions),
        )
        conn.commit()

    def _cand(c) -> dict:
        return {
            "model_version_id": c.model_version_id,
            "display_name": names.get(c.model_version_id, c.model_version_id),
            "band": c.band,
            "reason": c.reason,
            "cost_per_task": c.cost_per_task,
            "quote_ids": list(c.quote_ids),
        }

    return {
        "abstained": answer.abstained,
        # NAMES THE MISSING CAPABILITY when abstaining, so "no answer" and "no
        # answer BECAUSE nobody has reported on X" are distinguishable (rule 4).
        "reason": answer.reason,
        "requirement": requirement.model_dump(),
        "guard": guard_for(requirement),
        # The ranked list is recommended + qualified ONLY. Unevidenced models
        # are shown in their own section, never mixed into the ranking — hiding
        # them makes the board quietly conservative, mixing them makes it dishonest.
        "recommended": [_cand(c) for c in answer.candidates if c.band == "recommended"],
        "qualified": [_cand(c) for c in answer.candidates if c.band == "qualified"],
        "rejected": [_cand(c) for c in answer.candidates if c.band == "rejected"],
        "no_evidence": [_cand(c) for c in answer.candidates if c.band == "no_evidence"],
        "considered": len(names),
    }


# ── the board's read surface ──────────────────────────────────────────────
#
# Five page modules existed with no endpoint and no caller, so nothing outside
# this repository could reach a single one of them. Tenth instance of that
# pattern here and the first where I built the module and the gap in the same
# week.
#
# EVERY RESPONSE CARRIES ITS CAVEAT IN THE SAME OBJECT. That is not an API
# style choice. This board's entire claim is that it distinguishes "nobody
# looked" from "nobody complained", and a client that fetches a page and
# renders only the findings has silently removed the distinction. Making the
# caveat a separate call would make dropping it the easy path.


class _ConnectionPool:
    """A few connections, kept open and handed round.

    ⚠ THE HANDSHAKE WAS THE PAGE'S BIGGEST SINGLE COST, and nothing was
      measuring it. Measured 2026-09-17 against the shared database:

          psycopg.connect        1.58s
          one trivial query      0.25s

      The database is remote, and `_conn()` dialled a new one for every request.
      `/admin/usage` opened FOUR - its own, plus one each inside
      `spend_ledger.read_everywhere`, `spend_ledger.report` and the meter read -
      so more than five seconds of a sixteen-second endpoint was TCP and TLS for
      connections that had just been thrown away.

    BOUNDED, AND SMALL ON PURPOSE. A hosted Postgres has a connection limit that
    is somebody else's to raise, and an unbounded pool trades a slow page for an
    outage under load. Eight is more than the admin page can use at once; past
    that, callers wait for a connection rather than opening a ninth.

    LIFO, because a connection just returned is the one most likely to still be
    alive - the server or something between it and us may have dropped the ones
    that have been idle longest, and reaching for the coldest first is how a pool
    finds that out the slow way.
    """

    #: Small enough to be a good guest on a shared database. See above.
    MAX = 8

    def __init__(self) -> None:
        self._free: list[object] = []
        self._lock = threading.Lock()
        self._slots = threading.Semaphore(self.MAX)
        self._url: str | None = None

    def take(self, url: str):
        """A live connection for this DSN. Blocks if all slots are in use."""
        # Imported here for the same reason `_open_connection` does: the app
        # module is imported by tooling that has no database driver installed.
        import psycopg

        from judge.store.claims import CONNECT_TIMEOUT_SECONDS

        self._slots.acquire()
        try:
            with self._lock:
                # A CHANGED DSN EMPTIES THE POOL. Tests point the app at a
                # different database mid-process, and handing back a connection
                # to the previous one would be a silent read of the wrong data -
                # far worse than the reconnection it saves.
                if url != self._url:
                    stale, self._free, self._url = self._free, [], url
                    for conn in stale:
                        with contextlib.suppress(Exception):
                            conn.close()
                conn = self._free.pop() if self._free else None
            if conn is not None:
                if self._is_usable(conn):
                    return conn
                with contextlib.suppress(Exception):
                    conn.close()
            return psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT_SECONDS)
        except BaseException:
            # The slot is only held by a connection that reached a caller.
            self._slots.release()
            raise

    @staticmethod
    def _is_usable(conn) -> bool:
        """Cheap liveness, and it must not raise.

        A pooled connection can be dead in a way `closed` does not show - the
        server restarted, a NAT dropped it, a transaction was left broken. The
        rollback both answers the question and clears any transaction state the
        last caller left behind, which is the other thing a reused connection
        must never carry.
        """
        if getattr(conn, "closed", True):
            return False
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            return False
        return True

    def give_back(self, conn, *, reusable: bool) -> None:
        try:
            if not reusable or not self._is_usable(conn) or len(self._free) >= self.MAX:
                with contextlib.suppress(Exception):
                    conn.close()
                return
            with self._lock:
                self._free.append(conn)
        finally:
            self._slots.release()


_POOL = _ConnectionPool()


@contextmanager
def _conn():
    """A pooled connection, committed on success and returned to the pool.

    SAME SHAPE AS BEFORE, deliberately: every call site says
    `with _conn() as conn:` and psycopg's own connection context manager also
    committed on a clean exit. What changes is the ending - the connection goes
    back to the pool instead of being closed.

    ⚠ A FAILED CONNECTION IS NOT REUSED. An exception may have left the session
      mid-transaction or the socket half-dead, and a pool's whole risk is handing
      that to the next request as if it were fresh. Cheap to reconnect; a wrong
      read is not cheap at all.
    """
    conn = _open_connection()
    reusable = True
    try:
        yield conn
        conn.commit()
    except BaseException:
        reusable = False
        with contextlib.suppress(Exception):
            conn.rollback()
        raise
    finally:
        _POOL.give_back(conn, reusable=reusable)


def _open_connection():
    """A read connection, or a 503 that says the board is not readable.

    503 rather than 500: no database is an operational state, not a fault in
    the request, and a page that cannot be read is different from a page with
    nothing on it - which is the same distinction every one of these modules
    is built around.

    AND IT SAYS SO IN THE LOG, SINCE 2026-09-11. This used to refuse in
    silence: the only trace of a board with no database was one uvicorn access
    line reading `503 Service Unavailable` - no DSN, no connection attempt, no
    traceback. Diagnosing it meant noticing that an error was ABSENT, and an
    absence we caused reading as a fact about the world is the shape this
    project keeps paying for.

    THE TWO SHAPES ARE LOGGED SEPARATELY BECAUSE THEY HAVE DIFFERENT FIXES.
    "no DSN" is a process that never loaded `.env`; "cannot connect" is a DSN
    pointed at something that is not answering. The first dials nothing, so it
    is instant - which is itself how the two were told apart by hand.
    """
    import os

    import psycopg

    from judge.store.claims import CONNECT_TIMEOUT_SECONDS

    # Same variable and the same refusal as `judge.store.claims.transaction`.
    # A default that quietly reaches localhost is how a read surface ends up
    # serving a database nobody meant to expose.
    url = os.getenv("DATABASE_URL")
    if not url:
        log.error(
            "refusing to read the board: DATABASE_URL is not set in this "
            "process, so nothing was dialled. If `.env` holds a DSN, this "
            "process did not load it - run-backend.py is what loads `.env`, "
            "and `uvicorn judge.app:app` started directly does not."
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "no database configured, so the board cannot be read. This is "
                "not the same as a board with nothing on it."
            ),
        )
    try:
        return _POOL.take(url)
    except psycopg.OperationalError as error:
        # LOGGED AND RE-RAISED, NOT CONVERTED. An unreachable database may well
        # deserve the same 503 as an unconfigured one, but that is a change to
        # what the API answers and it is not this change - the request still
        # fails exactly as it did, with a traceback, and now also with a line
        # naming the target and the timeout it waited out.
        first = str(error).strip().splitlines()
        log.error(
            "cannot connect to %s after %ss: %s: %s",
            describe(url),
            CONNECT_TIMEOUT_SECONDS,
            type(error).__name__,
            first[0] if first else "(no message)",
        )
        raise


@app.get("/faq")
def faq_page() -> dict:
    """The landing page's FAQ, from `contract/faq.yaml`, resolved against reality.

    NEEDS NO DATABASE, and that is deliberate: the FAQ is the one surface a
    visitor should still get when the board cannot be read, because half of
    what it explains is why an empty board is a real state.

    THREE OF THE ELEVEN ANSWERS ARE CLAIMS ABOUT MODELS, not descriptions of
    how the board works, and the landing demo answered them from demo data -
    "DeepSeek V4 Flash at $0.14 in and $0.28 out", "engineers most often report
    Claude Opus 5", "SWE-bench is not yet saturated". Pasting those onto a live
    page would put figures in front of a reader with no row behind them, which
    is rule 3, and it would be invisible because they read like every other
    sentence.

    So an entry marked `basis: live` is served with its `unestablished_answer`
    and `established: false` until something supports it. The demo wording rides
    along in `demo_answer` so the difference is auditable rather than lost - the
    frontend does not render it, and it is excluded from the JSON-LD, because
    telling an answer engine something we are not telling a reader is cloaking.

    The platform count is substituted rather than typed: see
    `judge.config.evidence_platforms`.
    """
    from judge.config import evidence_platforms, faq

    doc = faq()
    platforms = evidence_platforms()
    listed = ", ".join(platforms[:-1]) + f" and {platforms[-1]}" if len(platforms) > 1 \
        else (platforms[0] if platforms else "no platform")

    out = []
    for entry in doc.get("questions") or []:
        answer = entry.get("a")
        established = True
        if entry.get("a_template"):
            answer = entry["a_template"].format(n=len(platforms), platforms=listed)
        elif entry.get("basis") == "live":
            # NOTHING IS CONSULTED HERE YET, and the answer says so in words
            # rather than by omission. Wiring this to the corpus is a query per
            # claim - cheapest priced model that also carries reports, the
            # best-for section with the most reports - and each needs its own
            # ruling about what "enough reports to rank" means. Until that
            # ruling exists, `established: false` is the honest state, and it
            # is a state the page renders rather than hides.
            answer = entry.get("unestablished_answer") or entry.get("a") or ""
            established = False
        out.append({
            "id": entry.get("id"),
            "question": entry.get("q"),
            "answer": (answer or "").strip(),
            "basis": entry.get("basis", "policy"),
            "open": bool(entry.get("open")),
            "established": established,
            # What the demo asserted, named rather than silently dropped. A
            # reader never sees this; a reviewer comparing the two does.
            "claims": list(entry.get("claims") or ()),
        })

    return {
        "version": doc.get("version"),
        "updated": str(doc.get("updated") or ""),
        "schema_type": doc.get("schema_type", "FAQPage"),
        "platforms": list(platforms),
        "questions": out,
        # THE SUMMARY MUST READ CORRECTLY AT ZERO. "0 of them ask something the
        # board cannot answer, and say so instead of answering" is a sentence
        # about nothing, and the withheld case is the normal case now.
        "summary": (
            f"{len(out)} questions from contract/faq.yaml"
            + (f", {unestablished} of which ask something the board cannot yet answer "
               f"from evidence and say so instead of answering."
               if (unestablished := sum(1 for q in out if not q["established"]))
               else ". Every one describes how the board works, so every one is "
                    "answerable without consulting the corpus. The three that asked "
                    "about models are withheld — see `withheld` in contract/faq.yaml.")
        ),
    }


#: Comparison rows the landing demo showed that this board has NO SOURCE for.
#: Returned by name so the page can say why a column is missing, which is the
#: whole difference between an honest gap and a quietly shorter table.
COMPARE_UNSOURCED = {
    "licence": (
        "the registry has no licence column, so open-weight versus proprietary "
        "cannot be stated per model without inventing it"
    ),
    "benchmark_standing": (
        "no benchmark figures are stored, and a standing derived from reports "
        "would be a score this board does not compute"
    ),
    "one_line": (
        "the demo's blurb and differentiation lines were written by hand; a "
        "classifier does not produce them and this endpoint will not invent them"
    ),
}

#: How many models may be compared at once. The demo capped at three and the
#: reason is presentational rather than arbitrary: a fourth column stops fitting
#: and the table starts scrolling sideways, which is where a comparison stops
#: being read.
COMPARE_MAX = 3


@app.get("/compare")
def compare_page(ids: str = "") -> dict:
    """Two or three models side by side — registry facts and counted evidence.

    THE DEMO'S TABLE HAD NINE ROWS AND THIS ONE CANNOT HAVE ALL NINE. Verdict,
    best-for, cost, context and report counts all have a source. Licence,
    benchmark standing, the one-line blurb and the differentiation line do not:
    they were written by hand for the mock-up. They are returned in
    `unsourced` with the reason, so the page shows a shorter table AND says
    what is missing - rather than omitting rows and letting the reader assume
    the board compared everything it could.
    """
    from judge.pages.roster import RosterReader
    from judge.store.board_entries import evidence_for_model

    wanted = [i.strip() for i in ids.split(",") if i.strip()]
    if len(wanted) < 2:
        raise HTTPException(
            status_code=422,
            detail=(
                "a comparison needs at least two model ids in `ids`, "
                "comma-separated. One model is its own page, not a comparison."
            ),
        )
    if len(wanted) > COMPARE_MAX:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{len(wanted)} models asked for; {COMPARE_MAX} is the maximum. A "
                f"fourth column makes the table scroll sideways, which is where a "
                f"comparison stops being read."
            ),
        )

    with _conn() as conn:
        roster = {m["model_version_id"]: m for m in RosterReader(conn).all().models}
        # UNKNOWN IDS ARE NAMED, NOT DROPPED. A comparison that silently
        # renders two of the three asked for is a different comparison, and
        # the reader has no way to tell.
        missing = [i for i in wanted if i not in roster]
        found = [roster[i] for i in wanted if i in roster]
        evidence = {m["model_version_id"]: evidence_for_model(conn, m["model_version_id"])
                    for m in found}

    if len(found) < 2:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{missing!r} not in the registry, leaving fewer than two models to "
                f"compare. Refused rather than rendered: a one-column comparison "
                f"reads as a verdict on the model that is there."
            ),
        )

    models = []
    for m in found:
        ev = evidence.get(m["model_version_id"], {})
        # `evidence_for_model` returns the three discovered sections at the top
        # level - `best_for`, `capabilities`, `metrics` - not under a `sections`
        # key. Each item carries its own `reports` count and its quotes.
        best_for = [
            {"name": s.get("name") or s.get("slug"), "slug": s.get("slug"),
             "reports": s.get("reports", 0)}
            for s in (ev.get("best_for") or [])
        ]
        models.append({
            "model_version_id": m["model_version_id"],
            "display_name": m["display_name"],
            "provider": m["provider"],
            # ADVERTISED. Kept under its own key so no client can fold it in
            # beside a reported figure and lose which kind of claim it is.
            "advertised": {
                "price_in": m["price_in"],
                "price_out": m["price_out"],
                "price_cached_read": m["price_cached_read"],
                "context": m["advertised_context"],
                "max_output_tokens": m["max_output_tokens"],
                "tools": m["supports_tools"],
                "vision": m["supports_vision"],
                "structured_output": m["supports_structured_output"],
                "caching": m["supports_caching"],
                "lifecycle": m["lifecycle"],
            },
            # REPORTED. Counts of what people said, never a score.
            "reported": {
                "state": (m.get("evidence") or {}).get("state", "unreported"),
                "reports": (m.get("evidence") or {}).get("reports", 0),
                "capabilities": list((m.get("evidence") or {}).get("capabilities") or ()),
                "best_for": best_for,
                # The discovered sections in full, so the compare page can show
                # a metric figure with its basis rather than a bare number.
                "discovered": {
                    "best_for": ev.get("best_for") or [],
                    "capabilities": ev.get("capabilities") or [],
                    "metrics": ev.get("metrics") or [],
                },
            },
        })

    return {
        "models": models,
        "missing": missing,
        "unsourced": [{"row": k, "why": v} for k, v in COMPARE_UNSOURCED.items()],
        "summary": (
            f"{len(models)} models compared on advertised specification and counted "
            f"reports. Nothing here is a score: where every model has 0 reports the "
            f"comparison is a spec sheet, and it says so rather than ranking them."
        ),
    }


#: HOW THE SOURCE TEXT IS READ, filled by the composition root.
#:
#: `judge/` may not import `collect/` - `tests/test_lane_boundary.py` enforces
#: it - and `collect/rawstore.py` is the only reader of the payload store while
#: `collect/assemble/prose.py` is the only thing that turns a payload into what
#: a human wrote. So the reader is INJECTED: `run-backend.py`, which is outside
#: both lanes, fills this in at startup.
#:
#: Signature: `(source: str, text_ref: str) -> str`, raising on refusal.
#:
#: `None` MEANS UNWIRED, NOT EMPTY. A default that returned nothing would let a
#: process that forgot to wire a reader answer "no source text" for every quote
#: - indistinguishable from a corpus whose payloads are elsewhere, which is the
#: substitution `RefusingResolver` was written to stop.
SOURCE_TEXT_READER = None


@app.get("/documents/{document_id:path}/source")
def document_source(document_id: str) -> dict:
    """The text a quote was verified against, for one document.

    THE BOARD'S WHOLE CLAIM IS CHECKABILITY, and until now a reader could see a
    quote and a permalink but not the passage it came from. This serves the
    stored payload as prose - the same text the classifier was shown and the
    same text `verify` matched the quote against.

    THREE OUTCOMES, AND THEY ARE NOT THE SAME FACT:

      readable      the payload resolved and yielded prose.
      not_local     `text_ref` points at a payload this machine does not hold.
                    Documents harvested elsewhere are the normal case for a
                    shared corpus - it is an absence, not a corruption.
      not_prose     the payload resolved and its extractor refused it. This is
                    what the 2026-09-10 Reddit rows are: text stored where JSON
                    was expected. Saying which is how a reader learns the
                    difference between "we cannot reach it" and "we stored the
                    wrong thing".

    `quote` is echoed back when given, with `quote_found` saying whether it
    appears in the text verbatim. That is a live re-check of the verification
    claim rather than a restatement of it - and a false here is a finding worth
    surfacing, not an error to hide.
    """
    ref_row = None
    with _conn() as conn:
        ref_row = conn.execute(
            "SELECT source, url, text_ref FROM document WHERE id = %s",
            (document_id,),
        ).fetchone()

    if ref_row is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"{document_id!r} is not a document in this database. Refused "
                f"rather than answered empty: an unknown id and a document with "
                f"no readable payload are different facts."
            ),
        )
    source, url, text_ref = ref_row

    base = {"document_id": document_id, "source": source, "url": url}
    if not text_ref:
        return {**base, "state": "not_local", "text": None,
                "why": "this document row carries no text_ref, so no payload was ever stored"}

    # THE INJECTED READER. `judge/` may not import `collect/`, so the thing that
    # knows the store's layout and the source's prose extractor is filled in by
    # the composition root - see SOURCE_TEXT_READER above.
    reader = SOURCE_TEXT_READER
    if reader is None:
        return {**base, "state": "unwired", "text": None,
                "why": ("no source-text reader is wired into this process, so the "
                        "payload cannot be read here. This is a wiring gap, NOT a "
                        "document without text - `run-backend.py` fills it at "
                        "startup, and a --reload worker re-imports the app without "
                        "it.")}
    try:
        text = reader(source, text_ref)
    except FileNotFoundError as exc:
        return {**base, "state": "not_local", "text": None,
                "why": (f"the payload at {text_ref} is not in this machine's store "
                        f"({exc}). A document harvested on another machine is the "
                        f"normal case for a shared corpus.")}
    except Exception as exc:
        # The extractor refused it. This is what the 2026-09-10 Reddit rows are:
        # text stored where JSON was expected.
        return {**base, "state": "not_prose", "text": None,
                "why": (f"{source} payload refused by its own prose extractor: "
                        f"{str(exc).splitlines()[0][:160]}")}

    return {**base, "state": "readable", "text": text, "why": None,
            "characters": len(text)}


@app.get("/models")
def model_roster(limit: int = DEFAULT_PAGE, offset: int = 0, tracked: bool = False) -> dict:
    """The registry as a list, with what the provider advertises.

    ADDITIVE. Every other read surface in this file answers "what did people
    find out"; this one answers "what is on the tin" - price, context window,
    feature flags. Those are a vendor's claims about itself, they pass no gate
    and no voices stand behind them, so they are returned in their own shape
    and never merged into a capability row where a reader could mistake one
    kind of claim for the other.

    Rule 3 permits these figures: price and tokens are MEASURED, not
    synthesised. Rule 6 governs how they travel - a NULL price stays NULL all
    the way to the page, because five of these models are routers with no rate
    of their own and calling them free would be a definite value invented from
    a missing one.

    Ordered by name, never by price. A default sort by cost would be this
    endpoint making the recommendation the rest of the system refuses to make
    without evidence.
    """
    from judge.pages.roster import RosterReader

    with _conn() as conn:
        roster = RosterReader(conn).all()

    models = roster.models
    summary = roster.summary
    if tracked:
        # THE PAGE'S LIST, NOT THE REGISTRY'S. `model_version` holds 344 rows
        # because a router carries 344 models; the registry page answers "which
        # models does this board have opinions about", and a catalogue is not
        # that answer. The set lives in contract/tracked_models.yaml (rule 5)
        # rather than in the frontend, where it was a hardcoded array of two
        # that never called this endpoint at all.
        #
        # EVERY FIGURE STILL COMES FROM THE REGISTRY ROW. The contract names
        # WHICH models; it carries no price, no context and no flags, because a
        # price written into a config file has no provenance and cannot go
        # stale visibly.
        from judge.config import tracked_models

        by_id = {}
        for m in roster.models:
            by_id[m["canonical_id"]] = m
            by_id[m["model_version_id"]] = m
        models = []
        for want in tracked_models():
            found = by_id.get(want.registry) if want.registry else None
            if found is not None:
                # `tracked_kind` rides along so the page can say WHY a rate is
                # absent instead of leaving a reader to read "no rate" as free.
                models.append({**found, "tracked_kind": want.kind})
                continue
            # NOT IN THE REGISTRY, AND SHOWN ANYWAY. Dropping it would make the
            # page silently shorter than the list it is built from, and a
            # missing row reads as "not tracked" rather than "no rate is
            # published for this kind of model" - opposite claims (rule 6).
            # Every figure stays None; nothing is invented to fill the columns.
            models.append({
                "model_version_id": want.name,
                "display_name": want.name,
                "provider": None,
                "canonical_id": None,
                "price_in": None,
                "price_out": None,
                "price_cached_read": None,
                "advertised_context": None,
                "max_output_tokens": None,
                "supports_tools": None,
                "supports_vision": None,
                "tracked_kind": want.kind,
                "in_registry": False,
                "absent_because": want.absent_because,
            })
        evidenced = sum(1 for m in models if m.get("in_registry") is not False)
        # THE SUMMARY IS ARITHMETIC OVER THE ROWS, never a sentence about them.
        # The string it replaces ("Two models are being tracked") was hardcoded
        # in the frontend and had been wrong since the second model was added.
        #
        # IT DOES NOT MENTION PRICE, because the page no longer shows one. A
        # summary naming a figure that is not on the page sends a reader looking
        # for a column that is not there.
        # COUNTED, NOT CHARACTERISED. This used to end "the rest are image,
        # video and speech models it does not carry", which was true of one set
        # of rows and stopped being true the moment the set changed: there are
        # no video models left, and `google/gemini-3.1-flash-image` IS carried
        # and IS an image model. A sentence describing the rows is a sentence
        # that goes stale silently; a count cannot.
        absent = len(models) - evidenced
        summary = (
            f"{len(models)} models are tracked, chosen in "
            f"contract/tracked_models.yaml. "
            # "the registry the board polls" was true while every row came from
            # the poll. Three were seeded from contract/unpolled_models.yaml on
            # 2026-09-15 precisely because the poll will never carry them, so
            # that phrase described the registry by the one route that did not
            # supply them.
            + ("All have a registry row."
               if absent == 0 else
               f"{evidenced} have a registry row; "
               f"{absent} {'is' if absent == 1 else 'are'} not in it.")
        )

    page = _page(models, limit=limit, offset=offset)
    return {
        # `count` is the FULL registry size and always was. A page that reported
        # its own length here would answer "how many models are there" with "how
        # many did you ask for", which is rule 7 with the denominator swapped.
        "count": len(models),
        "priced_at": roster.priced_at,
        "summary": summary,
        "page": page.meta,
        "models": page.items,
    }


# `:path` because EVERY model id contains a slash - `google/gemini-2.5-flash`,
# `anthropic/claude-opus-5`. Without it FastAPI matches only up to the first
# separator and every real model page 404s, which is what the first live check
# against a database found. A URL-encoded %2F does not help: the ASGI server
# decodes before routing, so the slash is back by the time the path is matched.
# ⚠ REGISTERED BEFORE `/models/{model_version_id:path}`, AND IT MUST STAY THERE.
# FastAPI matches in registration order and `:path` is greedy, so the route
# below would swallow "openai/gpt-6-astra/evidence" as a model id and answer
# 404 for a model that exists. Found by calling it, not by reading it.
@app.get("/models/{model_version_id:path}/evidence")
def model_evidence(model_version_id: str) -> dict:
    """What has actually been said about ONE model, grouped by discovered section.

    The model page's half of the same corpus the board reads. The board groups by
    section and asks who has been reported doing this; this groups by model and
    asks what has been said about it. Same rows, different question — and neither
    is derived from the other, so a change to how the board sorts cannot move
    what a model page shows.

    Quotes come back in full because they ARE the page. Every one is verified by
    exact substring against the text the extractor was shown — the table CHECKs
    it — so what a reader sees is what an engineer wrote.

    AN EMPTY RESULT IS A REAL ANSWER. A tracked model nobody has discussed
    returns three empty sections, and that is a finding rather than a failure to
    load: absence is a state this board renders rather than hides.
    """
    from judge.store.board_entries import evidence_for_model

    with _conn() as conn:
        return evidence_for_model(conn, model_version_id)


@app.get("/models/{model_version_id:path}")
def model_page(model_version_id: str) -> dict:
    """FR-23 to FR-26. The full capability list, not the evidenced part.

    ⚠ CROSS-LANE EDIT. `judge/` is Engineer 2's and `CLAUDE.md` says to propose
    rather than edit. This was proposed in
    `docs/proposals/model-page-id-resolution.md` and then directed twice, so it
    is made HERE and flagged LOUDLY rather than quietly: revert it freely, the
    reasoning is in the proposal, and nothing in `collect/` depends on it.

    THE ID IS RESOLVED AND VALIDATED, WHICH IT WAS NOT.

    `cell.model_version_id` is the internal `mv_…` id, so a canonical id matched
    no row — and nothing checked, so it did not 404. It rendered. Called four
    ways against a live registry, every one returned 200 with an identical page:

        /models/mv_568e0eb3a95b5113          the real key
        /models/anthropic/claude-opus-5      what every caller actually holds
        /models/total-nonsense-not-a-model   not a model
        /models/                             the empty string

    All four: *"0 of 12 tracked capabilities have any reports at all."* **A typo
    and a real model were the same page.**

    That is FR-24 inverted. The rule that makes an empty page correct for a real
    model with no evidence makes it a fabrication for one that does not exist,
    and it is the one place this API breaks rule 4 — the rule the board is built
    on. `/capabilities/{capability_key}` already gets this right thirty lines
    down, and its refusal message is the argument for this one.

    BOTH SHAPES RESOLVE. The `mv_` id is a stable internal key existing links
    use; the canonical id is what the registry publishes and what `modelPath()`
    builds. Accepting only one of them would move the defect rather than close
    it.
    """
    from judge.pages.model import ModelPageReader

    with _conn() as conn:
        # One lookup, against the table `judge/pages/capability.py` already
        # reads. No `collect/` import: `stable_id` is not needed because the
        # database holds both columns.
        found = conn.execute(
            "SELECT id, canonical_id, display_name FROM model_version "
            "WHERE id = %s OR canonical_id = %s",
            (model_version_id, model_version_id),
        ).fetchone()
        if found is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"{model_version_id!r} is not a model in the registry. "
                    f"Refused rather than rendered empty: an unknown id would "
                    f"read 'nobody has reported on this model', which is "
                    f"indistinguishable from a model in the registry that "
                    f"nobody has discussed. Accepts the canonical id "
                    f"(anthropic/claude-opus-5) or the internal id (mv_…)."
                ),
            )
        mv_id, canonical_id, display_name = found

        page = ModelPageReader(conn).build(mv_id, display_name=display_name or "")
        quote_ids = tuple(q for c in page.capabilities for s in c.slices for q in s.quote_ids)
        quotes = ModelPageReader(conn).quotes_for(quote_ids)

    return {
        # BOTH, because the caller asked by one and the cells are keyed by the
        # other, and a client that cannot tell which it received cannot build a
        # link back.
        "model_version_id": page.model_version_id,
        "canonical_id": canonical_id,
        "display_name": display_name,
        "summary": page.summary,
        # #33 Q2: the THIRD silence. `tracked` false means we have never swept
        # this model, so the empty capabilities below are "we have not looked",
        # not "nobody reported problems". The UI must render this distinctly from
        # a tracked model with no evidence — rule 4 at the model level.
        "tracked": page.tracked,
        "swept_at": page.swept_at.isoformat() if page.swept_at is not None else None,
        "capabilities": [
            {
                "key": c.key,
                "failure_mode": c.failure_mode,
                "state": (
                    "unreported"
                    if c.unreported
                    else ("insufficient" if c.insufficient else "published")
                ),
                "headline": c.headline,
                "needs_positive_consensus": c.needs_positive_consensus,
                "conditions": [
                    {
                        "bucket": s.condition_bucket,
                        "status": s.status,
                        "phrase": s.consensus_phrase,
                        "note": s.conditional_note,
                        "voices": s.independent_voices,
                        "platforms": s.platform_count,
                        # FR-26: the ids travel WITH the phrase. A phrase
                        # without them is an unfalsifiable claim.
                        "quote_ids": list(s.quote_ids),
                    }
                    for s in c.slices
                ],
            }
            for c in page.capabilities
        ],
        "quotes": {
            qid: {
                "text": q.text,
                "permalink": q.permalink,
                "platform": q.platform,
                "claimed_at": q.claimed_at,
                # praise vs criticism, read straight from claim.polarity; and a
                # flag when a stored `positive` contradicts a listed pain point,
                # so the page shows the dispute instead of a false green.
                "polarity": q.polarity,
                "sign_disputed": q.sign_disputed,
            }
            for qid, q in quotes.items()
        },
        # Surfaced rather than hidden: a published phrase with no evidence
        # behind it is a rendering the client should refuse.
        "unbound_phrases": [s.capability_key for s in page.unbound_phrases()],
    }


# ── per-model fetch: run this model's evidence pipeline on demand ──────────
#
# TRIGGERED BY A CLICK, NEVER BY A READ. NFR-2 keeps the answer path off the
# pipeline, so GET /models is untouched; this is a distinct POST that starts an
# out-of-band job. The job runs in a SUBPROCESS (`scripts/fetch_model.py`), so
# judge/ never imports collect/ — the composition root does, in its own process.
# APPEND-ONLY: the script never drops or deletes; it adds this model's rows.


class FetchRequest(BaseModel):
    model_version_id: str


@app.post("/fetch/start")
def start_fetch(req: FetchRequest) -> dict:
    """Kick off a fresh fetch for one model and return its run id.

    Returns immediately; progress is written to var/fetch/<run_id>.jsonl by the
    subprocess and read back through /fetch/log. The run id has no slash (the
    model id's slashes are flattened) so it is a safe filename and query value.
    """
    mv = req.model_version_id.strip()
    if not mv:
        raise HTTPException(status_code=422, detail="model_version_id is required")

    # TIDY THE CORPSES BEFORE ADDING A LIVE ONE. A run whose process ended
    # without writing its end record reads as running forever - one had done so
    # for 70.5 hours when this was written - and the history is unreadable while
    # "running" means either "working now" or "died at some point since Friday".
    #
    # Here rather than on a schedule because it needs no scheduler and the
    # moment is exactly right: somebody is about to watch this page, and the
    # rows that would confuse them are about to be joined by a real one. It
    # never raises and never blocks the start - see `reap`.
    reaped: list[str] = []
    try:
        with _conn() as conn:
            reaped = [r.run_id for r in fetch_reaper.reap(conn)]
    except Exception:  # noqa: BLE001 - a tidy-up must not stop a fetch
        log.warning("could not reap abandoned runs before starting", exc_info=True)

    run_id = f"{mv.replace('/', '_')}-{uuid.uuid4().hex[:8]}"
    script = _REPO_ROOT / "scripts" / "fetch_model.py"
    # Detached: we do not wait. env carries DATABASE_URL / GITHUB_TOKEN etc.,
    # which run-backend.py loaded from .env into this process's environment.
    # ⚠ INHERITED, NOT DISCARDED, AND THAT IS THE POINT OF THE CHANGE.
    #   This was `stdout=DEVNULL, stderr=DEVNULL`, so a run started from the
    #   admin page threw away every word it said. The console that started the
    #   backend went silent for forty minutes and then the board had changed,
    #   and reading what happened meant opening `var/fetch/<run>.jsonl` and
    #   decoding it by eye. `fetch_model.py` now renders itself as it goes, and
    #   passing the streams through is what lets that reach a person.
    #
    #   THE RUN IS STILL DETACHED AND NOTHING IS READ BACK. These are not
    #   pipes: the child writes to the same console as the parent and nobody
    #   waits on it, so there is no buffer to fill and no reader to block. A
    #   PIPE here would deadlock the moment a long run filled it with nobody
    #   draining, which is the version of this change that looks equivalent
    #   and is not.
    #
    #   A BACKEND WITH NO CONSOLE - a service, a container - inherits whatever
    #   it was given, which is the right answer there too: the same place its
    #   own logs go. `FETCH_QUIET=1` turns the rendering off without changing
    #   how the process is spawned.
    subprocess.Popen(
        [sys.executable, str(script), mv, "--run-id", run_id],
        cwd=str(_REPO_ROOT),
        env=os.environ.copy(),
    )
    # NAMED IN THE RESPONSE, not done quietly. Marking another machine's run
    # dead is a visible change to shared history, and a caller that can see it
    # happened can disagree with it.
    return {"run_id": run_id, "model_version_id": mv, "reaped_runs": reaped}


class StopFetchRequest(BaseModel):
    run_id: str


@app.post("/fetch/stop")
def stop_fetch(req: StopFetchRequest) -> dict:
    """Ask a running fetch to stop at its next stage boundary.

    COOPERATIVE, NOT A KILL, and that is the whole design. The request is a
    file - `var/fetch/<run_id>.stop` - which the subprocess notices in
    `Progress.stage()`, so it stops between things it was going to report,
    writes its own `stopped` end record, and closes its database connection
    and HTTP client on the way out.

    WHY NOT SIGNAL THE PROCESS. Three reasons, each of which has already cost
    this project a run:

      * a metered request already spent is recorded by `record_rapidapi_quota`
        inside `_get`. Killing mid-request spends the quota and loses the
        reading, which is precisely the gap `collect/usage.py` exists to close.
      * a kill mid-transaction leaves the rollback to libpq's timeout rather
        than to `_safe_rollback`, and a half-finished `INSERT ... SELECT` is
        how the 2026-09-09 run ended.
      * the PID is not ours to hold. `start_fetch` discards the `Popen` handle
        and the backend restarts freely; a file survives both, so Stop works
        on a run this process never started.

    WHAT STOPPING DOES NOT DO IS UNDO. Every write in the pipeline is an
    append, so rows already stored stay stored - a stopped run leaves less
    evidence than a finished one, never wrong evidence. The end record says
    `stopped` rather than `error`, because abandoning a run deliberately and a
    run breaking are different facts (rule 4: a caused absence must say it was
    caused).

    Idempotent, and honest about a run that has already finished: the file is
    written either way, and `was_running` says whether anything will read it.
    """
    run_id = req.run_id.strip()
    if not run_id or "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=422, detail="bad run id")

    log = _FETCH_DIR / f"{run_id}.jsonl"
    already_ended = False
    if log.exists():
        already_ended = any(
            '"kind": "end"' in line or '"kind":"end"' in line
            for line in log.read_text(encoding="utf-8").splitlines()
        )
    try:
        _FETCH_DIR.mkdir(parents=True, exist_ok=True)
        (_FETCH_DIR / f"{run_id}.stop").write_text(
            datetime.now(UTC).isoformat(), encoding="utf-8"
        )
    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"could not record the stop request: {exc}. The run is still "
                   "going; nothing was changed.",
        ) from exc

    return {
        "run_id": run_id,
        "stop_requested": True,
        # False means the run had already written its end record, so the
        # request will never be read. Said rather than implied, so the UI does
        # not show "stopping..." forever over a run that finished a minute ago.
        "was_running": bool(log.exists() and not already_ended),
        "note": (
            "the run stops at its next stage boundary and writes a `stopped` "
            "end record. Rows already written are kept - every write here is "
            "an append, so a stopped run holds less evidence, never wrong "
            "evidence."
        ),
    }


@app.get("/fetch/log")
def fetch_log(run_id: str) -> dict:
    """The per-stage progress of a fetch, as the subprocess has written it so far.

    Polled by the model page. `done` flips true when the run writes its end
    record — that is how the UI knows to stop polling. An absent file means the
    run has not written its first line yet, which is not an error.

    THE LOCAL FILE FIRST, THE SHARED TABLE SECOND. A run started on THIS machine
    is on this disk and is read from there — no database round trip on a poll
    that fires every second, and no dependence on a database to watch a run that
    may be failing because of the database. A run id this machine has never seen
    belongs to somebody else's laptop, and `fetch_log` is where it can be read
    from; `source` says which happened, because "not started yet" and "ran
    elsewhere" are different answers and the UI must not conflate them.
    """
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=422, detail="bad run id")
    path = _FETCH_DIR / f"{run_id}.jsonl"
    if path.exists():
        records = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        done = any(r.get("kind") == "end" for r in records)
        # THE REAPER'S VERDICT, WHICH THIS ENDPOINT COULD NOT SEE UNTIL NOW.
        # `reap` writes to `fetch_log` and never to this file, so a run it had
        # already marked `abandoned` still answered `done: false` here and the
        # UI polled it forever. Only consulted once the file itself has gone
        # quiet past the reaper's threshold — see `_adopted_end_record`.
        adopted = None
        if not done:
            adopted = _adopted_end_record(run_id, records)
            if adopted is not None:
                records = [*records, adopted]
                done = True
        return {
            "run_id": run_id,
            "records": records,
            "started": True,
            "done": done,
            "source": "local file",
            # SAID, NOT SLIPPED IN. The last record is then not the run's own
            # words but another process's verdict about it, and a reader
            # deciding whether to trust "abandoned" needs to know which.
            **({"end_adopted_from": "shared table"} if adopted is not None else {}),
        }
    shared = _fetch_log_from_db(run_id)
    if shared:
        return {
            "run_id": run_id,
            "records": [r for r, _ in shared],
            "started": True,
            "done": any(r.get("kind") == "end" for r, _ in shared),
            "source": "shared table",
            "machine": shared[0][1],
        }
    return {"run_id": run_id, "records": [], "done": False, "started": False,
            "source": None}


def _adopted_end_record(run_id: str, records: list[dict]) -> dict | None:
    """The end record the SHARED TABLE holds for a run whose own FILE has none.

    ⚠ THE REAPER AND THE UI WERE LOOKING AT TWO DIFFERENT STORES, AND THAT IS
      WHY A DEAD RUN READ AS RUNNING FOR SIXTEEN HOURS.

    `fetch_reaper.reap` appends its `abandoned` record to the `fetch_log` TABLE
    and touches no file — grep it for `_FETCH_DIR` and there is nothing. Both
    readers above prefer the LOCAL FILE, for a good reason stated in
    `/fetch/log`: a poll that fires every second should not make a database
    round trip, and a run failing *because of* the database should still be
    watchable.

    So on the machine that started a run, the reaper's verdict was invisible.
    Measured 2026-09-16 on this machine:

        GET /fetch/log?run_id=anthropic_claude-fable-5-1-fcb1e17b
          source : local file
          done   : False          <- the UI polls forever
          records: 77

    while `fetch_log` held an `abandoned` end record for that exact run. The
    reaper had worked five days earlier and nothing could see it.

    WHY THIS DOES NOT UNDO "LOCAL FILE FIRST". The file still wins for every
    healthy run and for every poll of a live one: this is reached only when the
    file has NO end record AND the run has been silent longer than the reaper's
    own threshold. A run inside that window is plausibly alive, and asking the
    database about it would be both wrong and the round trip the rule exists to
    avoid.

    THE FILE IS STILL NOT REWRITTEN. The run's own account stays exactly as it
    left it — this adopts a record for the ANSWER, and the caller says so with
    `end_adopted_from` rather than passing it off as the run's own words.

    Returns None when the file is empty, when the run is still inside the
    silence window, or when the table has no end record either.
    """
    if not records:
        return None
    stamps = [r.get("at") for r in records if r.get("at")]
    if not stamps:
        return None
    last = _epoch_of(max(stamps))
    if last is None:
        return None
    quiet_for = datetime.now(UTC).timestamp() - last
    if quiet_for < fetch_reaper.DEFAULT_SILENT_FOR.total_seconds():
        return None
    for record, _machine in _fetch_log_from_db(run_id):
        if record.get("kind") == "end":
            return record
    return None


def _fetch_log_from_db(run_id: str) -> list[tuple[dict, str]]:
    """One run's lines from `fetch_log`, in the order they were written.

    ORDERED BY `seq`, NOT BY `at`. The log is a sequence — "E3 running" before
    "E3 error" is the entire meaning — and its timestamps are second-resolution,
    so several lines routinely share one. Ordering by time would scramble any
    run that moved faster than a second, which is most of them.

    Returns `[]` on any failure, because a log that cannot be read and a run
    that never happened are the same to this endpoint's caller; the caller
    distinguishes them through `source`.
    """
    try:
        with _conn() as conn:
            rows = conn.execute(
                "select payload, machine from fetch_log where run_id = %s "
                "order by seq",
                (run_id,),
            ).fetchall()
    except Exception:
        return []
    out: list[tuple[dict, str]] = []
    for payload, mach in rows:
        rec = payload if isinstance(payload, dict) else json.loads(payload)
        out.append((rec, str(mach)))
    return out


@app.get("/fetch/runs")
def fetch_runs(model_version_id: str) -> dict:
    """Every past fetch run for one model, newest first, with a one-line summary.

    Backs the fetch-log history in the admin console. The run logs ARE the store:
    this reads the same var/fetch/<run_id>.jsonl files /fetch/log serves, and a
    run's full log is still fetched by run_id through /fetch/log. No database.

    A run id is `<flattened model id>-<8 hex>`, so runs for one model share the
    flattened-id prefix. The 8-hex suffix is checked explicitly so a shorter
    model id can never claim a longer one's runs.
    """
    mv = model_version_id.strip()
    if not mv:
        raise HTTPException(status_code=422, detail="model_version_id is required")

    # REAP BEFORE RENDERING, WHICH IS THE CALLER `fetch_reaper` ALWAYS NAMED AND
    # NOBODY EVER WIRED. Its own docstring says "the caller is a fetch about to
    # start OR A PAGE ABOUT TO RENDER"; only the first existed, so nothing was
    # reaped unless somebody happened to start another fetch. Measured
    # 2026-09-16: three runs had read as `running` for ~16 hours because no
    # fetch had been started since they died.
    #
    # The moment somebody LOOKS is at least as right as the moment somebody
    # starts, and it comes first — a stale row confuses a reader when it is
    # read, not when it is joined by a newer one.
    #
    # CHEAP WHEN THERE IS NOTHING TO DO: `reap` runs one query and returns early
    # unless a run is actually past the threshold. Never raises, and wrapped
    # anyway — a history that will not load because a tidy-up failed is worse
    # than the stale row it was tidying.
    reaped: list[str] = []
    try:
        with _conn() as conn:
            reaped = [r.run_id for r in fetch_reaper.reap(conn)]
    except Exception:  # noqa: BLE001 - a tidy-up must not fail the render
        log.warning("could not reap abandoned runs before listing", exc_info=True)

    flat = mv.replace("/", "_")
    _HEX = set("0123456789abcdef")
    runs = []
    if _FETCH_DIR.exists():
        for path in _FETCH_DIR.glob(f"{flat}-*.jsonl"):
            suffix = path.stem[len(flat) + 1:]
            if len(suffix) != 8 or any(c not in _HEX for c in suffix):
                continue
            try:
                records = [
                    json.loads(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            except (OSError, ValueError):
                records = []
            end = next((r for r in records if r.get("kind") == "end"), None)
            # Same adoption as `/fetch/log`, and needed here for the same
            # reason: the reap above wrote to the table, not to this file, so
            # without this the row it just marked would still list as running.
            if end is None:
                end = _adopted_end_record(path.stem, records)
            stages = [r for r in records if r.get("kind") == "stage"]
            docs = sum(int(s.get("documents_inserted") or 0) for s in stages)
            runs.append({
                "run_id": path.stem,
                "started_at": path.stat().st_mtime,
                "done": end is not None,
                "status": (end or {}).get("status"),
                "detail": (end or {}).get("detail"),
                # distinct stage ids reached — a stage writes a running record and
                # then a terminal one, so counting rows would double it.
                "stages": len({s.get("id") for s in stages}),
                "documents_inserted": docs,
                "machine": None,   # this machine; see the note below
            })

    # RUNS FROM EVERY OTHER MACHINE, from `fetch_log`. Local files win on a
    # collision: they are the same run, and the local copy is the one that is
    # still being appended to while the run is live.
    seen = {r["run_id"] for r in runs}
    for run_id, machine_name, records in _fetch_runs_from_db(flat, _HEX):
        if run_id in seen:
            continue
        end = next((r for r in records if r.get("kind") == "end"), None)
        stages = [r for r in records if r.get("kind") == "stage"]
        first_at = next((r.get("at") for r in records if r.get("at")), None)
        runs.append({
            "run_id": run_id,
            # An ISO string, not an mtime float. Sorting mixes the two, so both
            # are normalised to a float below rather than compared as-is.
            "started_at": _epoch_of(first_at),
            "done": end is not None,
            "status": (end or {}).get("status"),
            "detail": (end or {}).get("detail"),
            "stages": len({s.get("id") for s in stages}),
            "documents_inserted": sum(
                int(s.get("documents_inserted") or 0) for s in stages
            ),
            # NAMED, because "a run you cannot see the files for" is a
            # different thing to a reader than one of their own.
            "machine": machine_name,
        })
    runs.sort(key=lambda r: r["started_at"] or 0, reverse=True)
    # NAMED IN THE RESPONSE, exactly as `/fetch/start` names it. Marking another
    # machine's run dead is a visible change to shared history, and doing it on
    # a page RENDER makes it easier to miss than doing it on a click - so the
    # page is told what it just did and can say so. `reaped_by` is on each
    # record too, so the write is attributable from the row as well as here.
    return {"model_version_id": mv, "runs": runs, "reaped_runs": reaped}


def _epoch_of(when: str | None) -> float | None:
    """An ISO-8601 stamp as epoch seconds, or None. Never raises.

    None rather than 0.0 for an unparseable date: 0.0 is 1970 and would sort a
    run to the bottom as though it were the oldest, which is a definite claim
    about when it ran (rule 6). The sort treats None as unknown instead.
    """
    if not when:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(when).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def _fetch_runs_from_db(flat: str, hex_chars: set[str]) -> list[tuple[str, str, list[dict]]]:
    """Other machines' runs for one model. `[]` when the table cannot be read."""
    try:
        with _conn() as conn:
            rows = conn.execute(
                "select run_id, machine, payload from fetch_log "
                "where run_id like %s order by run_id, seq",
                (f"{flat}-%",),
            ).fetchall()
    except Exception:
        return []
    grouped: dict[str, tuple[str, list[dict]]] = {}
    for run_id, machine_name, payload in rows:
        suffix = str(run_id)[len(flat) + 1:]
        # The same guard the file path uses: a shorter model id must never
        # claim a longer one's runs through a LIKE prefix.
        if len(suffix) != 8 or any(c not in hex_chars for c in suffix):
            continue
        rec = payload if isinstance(payload, dict) else json.loads(payload)
        entry = grouped.setdefault(str(run_id), (str(machine_name), []))
        entry[1].append(rec)
    return [(rid, mach, recs) for rid, (mach, recs) in grouped.items()]


@app.get("/capabilities/{capability_key}")
def capability_page(capability_key: str, limit: int = DEFAULT_PAGE, offset: int = 0) -> dict:
    """FR-25. Every model in the registry, not every model with a cell.

    PAGED, and the summary is deliberately NOT recomputed for the page. It says
    "0 of 342 models in the registry have any reports on this capability", and
    that sentence is about the registry - rewriting it per page would turn a
    statement about coverage into a statement about pagination, which is exactly
    the substitution rule 7 exists to catch.
    """
    from judge.config import capabilities
    from judge.pages.capability import CapabilityPageReader

    # Checked BEFORE connecting. An unknown key is a fact about the request,
    # establishable without a database - and answering 503 for it would tell
    # the caller the board is down when their key is simply wrong.
    if capability_key not in capabilities():
        raise HTTPException(
            status_code=404,
            detail=(
                f"{capability_key!r} is not a tracked capability. Refused rather "
                f"than rendered empty: an unknown key would read 'nobody has "
                f"reported on this', which is indistinguishable from a real "
                f"capability nobody has discussed."
            ),
        )

    with _conn() as conn:
        page = CapabilityPageReader(conn).build(capability_key)

    rows = [
        {
            "model_version_id": m.model_version_id,
            "display_name": m.display_name,
            "state": "unreported" if m.unreported else "reported",
            "conditional": m.conditional,
            "buckets": [{"bucket": b, "status": s} for b, s in m.buckets],
            "phrases": list(m.phrases),
            "voices": m.voices,
        }
        for m in page.models
    ]
    window = _page(rows, limit=limit, offset=offset)

    return {
        "key": page.key,
        "failure_mode": page.failure_mode,
        "summary": page.summary,
        "page": window.meta,
        "models": window.items,
    }


@app.get("/filtered")
def filtered_page(limit: int = 200) -> dict:
    """FR-18. What we threw away, and the rule that threw it."""
    from judge.pages.filtered import FilteredPage

    with _conn() as conn:
        report = FilteredPage(conn).report(limit=limit)

    return {
        "summary": report.summary,
        "truncated": report.truncated,
        "total_filtered": report.total_filtered,
        "total_documents": report.total_documents,
        "documents": [
            {
                "document_id": d.document_id,
                "url": d.url,
                "source": d.source,
                "status": d.status,
                "explained": d.explained,
                "headline": d.headline,
                "triggers": [{"rule": r, "explanation": e} for r, e in d.triggers],
            }
            for d in report.documents
        ],
    }


@app.get("/board")
def board_page() -> dict:
    """The three board sections, as the classifier DISCOVERED them.

    Ungated. `cell` publishes a verdict and clears a gate first; these are
    observations, and holding them back until four voices agreed would render
    three empty sections while the evidence sat in the database.

    `reports` IS A FLOOR AND SAYS SO. The vocabulary is open, so one section can
    arrive under two names until somebody merges them - which means the count is
    ">= N" rather than N. Shipping the qualifier with the number rather than
    beside it in a docstring is rule 7: a figure travels with what it counted.

    Nothing here ranks or scores. Sections are ordered by report count, which is
    a count, and each carries the models named in it and the quotes behind it.
    """
    from judge.store.board_entries import board_sections

    with _conn() as conn:
        sections = board_sections(conn)

    return {
        # The demo board's three tabs, in its own order: Best for, Capabilities,
        # Metrics. The frontend renders these keys directly.
        "jobs": sections["best_for"],
        "caps": sections["capability"],
        "mets": sections["metric"],
        "counts": {
            "jobs": len(sections["best_for"]),
            "caps": len(sections["capability"]),
            "mets": len(sections["metric"]),
        },
        # RULE 4, AND IT TRAVELS WITH ITS DENOMINATOR (rule 7). The metrics
        # tab is thinner than the stored rows because figures that cannot
        # support themselves are held back, and a page that simply showed
        # fewer rows would be making the opposite claim: that nobody measured
        # these models. Counted by reason so a reader can tell a prompt
        # problem from a labelling one.
        "metrics_withheld": sections.get("_withheld", {}),
        "report_counts_are_a_floor": True,
        "summary": (
            "Discovered from the evidence, not chosen from a list. Report counts "
            "are a floor: an open vocabulary can name one section two ways until "
            "the duplicates are merged."
        ),
    }


@app.get("/coverage")
def coverage_page() -> dict:
    """What the board does not know, and what it has not checked."""
    from judge.pages.coverage import CoveragePage

    with _conn() as conn:
        report = CoveragePage(conn).report()

    return {
        "summary": report.summary,
        "pipeline_version": report.pipeline_version,
        "measured_at_all": report.measured_at_all,
        "kinds": [
            {
                "kind": k.kind,
                "recognised": k.recognised,
                "measured": k.measured,
                "headline": k.headline,
                "rows": k.rows,
                "subjects": k.subjects,
                "truncated": k.truncated,
                "examples": list(k.examples),
            }
            for k in report.kinds
        ],
    }


@app.get("/changelog")
def changelog_page(days: int = 30) -> dict:
    """FR-27. What changed, and whether it was us or the world."""
    from judge.pages.changelog import ChangelogReader

    with _conn() as conn:
        log = ChangelogReader(conn).recent(days=days)

    return {
        "summary": log.summary,
        "window_days": log.window_days,
        "total_labels": log.total_labels,
        "by_driver": {
            driver: [
                {
                    "change_id": c.change_id,
                    "label_id": c.label_id,
                    "direction": c.direction,
                    "headline": c.headline,
                    "is_about_us": c.is_about_us,
                    "evidenced": c.evidenced,
                    "quote_ids": list(c.quote_ids),
                }
                for c in changes
            ]
            for driver, changes in log.by_driver().items()
        },
    }


# ── the admin usage page: OUR cap, OUR spend, both stages ─────────────────


@app.get("/admin/usage")
def admin_usage(hours: int = 24, days: int = 14) -> dict:
    """What we have spent today against the one shared daily cap.

    OURS, NOT THE PROVIDER'S. OpenRouter has its own ceilings - account credit
    and a per-key cap - and they are different numbers on a different schedule.
    This endpoint reports the limit WE set and the spend WE recorded, because
    that is the one a person can act on by changing a config value.

    ONE CAP, TWO STAGES. `EXTRACTION_DAILY_BUDGET_USD` is the total across
    extraction and the ask box together, not each. The limit is one figure and
    every usage figure is split by stage, so a reader can see which of the two
    consumed the day without the split implying two budgets.

    EVERY FIGURE CARRIES WHAT IT IS DRAWN FROM (rule 7). `covers_whole_window`
    is false when the ledger began after today did, in which case today's total
    is a floor rather than a total; `unwired_stages` names any stage that has
    never recorded at all, which is a wiring failure and not a quiet day. A page
    rendering either of those as a plain zero would be stating the most
    reassuring of two readings.
    """
    from judge import spend_ledger
    from judge.extract.budget import Budget

    configured = Budget.from_env()
    estimated = (
        configured.estimated_next_call_usd
        if configured is not None
        else Budget(limit_usd=None).estimated_next_call_usd
    )
    report = spend_ledger.report(
        daily_cap_usd=configured.limit_usd if configured is not None else None,
        estimated_call_usd=estimated,
        hours=max(1, min(hours, 168)),
        days=max(1, min(days, 90)),
    )

    # ALL-TIME per-model spend. `report.by_model_usd` is TODAY only (it shares the
    # cap window), so on a day with no calls it is empty. This cumulative total is
    # what "usage per model" means for a Gemini-vs-DeepSeek comparison, so it is
    # exposed separately and labelled all-time on the page.
    by_model_total: dict[str, float] = {}
    # TOKENS BESIDE THE DOLLARS, because a model with no published rate records
    # its tokens and $0.00 (`unpriced`). Shown as money alone it reads as free,
    # which is the one wrong conclusion available. Tokens are the measurement;
    # dollars are a multiplication that needs a multiplier we may not hold.
    by_model_tokens: dict[str, int] = {}
    unpriced_models: set[str] = set()
    # EVERY MACHINE, not this one. `read_all()` is the local file; the all-time
    # per-model figure beside a team total must cover the same population, or
    # the two numbers on one page disagree for a reason nothing states.
    all_calls, _ = spend_ledger.read_everywhere()
    for call in all_calls:
        by_model_total[call.model] = by_model_total.get(call.model, 0.0) + call.usd
        by_model_tokens[call.model] = (
            by_model_tokens.get(call.model, 0) + call.input_tokens + call.output_tokens
        )
        if call.unpriced:
            unpriced_models.add(call.model)

    def series(buckets):
        return [
            {
                "label": b.label,
                "starts_at": b.starts_at.isoformat(),
                "usd": round(b.usd, 6),
                "calls": b.calls,
                "by_stage": {k: round(v, 6) for k, v in b.by_stage.items()},
            }
            for b in buckets
        ]

    return {
        "summary": _usage_summary(report),
        # WHOSE SPEND THIS IS. A dollar total is meaningless without the
        # population it covers (rule 7), and that population is now variable:
        # every machine when the table is readable, one laptop when it is not.
        # `complete` false means the number is a FLOOR and the page must say so
        # rather than render a smaller figure in the same type as a whole one.
        # ⚠ NO MACHINE NAME LEAVES THIS ENDPOINT. The count is the figure rule 7
        #   asks for; the NAMES were never used for anything a reader acts on,
        #   and this is a web page. `machines` sent the whole roster - two
        #   personal hostnames beside four container ids - and `this_machine`
        #   named the host serving the page.
        #
        #   Parvathi, 2026-09-16: "do you think on a web admin page is it oky to
        #   show up these names? cant you remove this or any machine name from
        #   being showed up?"
        #
        #   ⚠ AND THIS IS THE SECOND ASK. The first removed one line - "Ledger
        #     totals cover all 2 machines (ANOOJ, LenovoPB)" - by moving the
        #     roster into a tooltip, which kept rendering the names on hover and
        #     left four other sites untouched. Fixing the instance and not the
        #     class is why it came back.
        #
        #   The columns stay in the database. Provenance is worth having and is
        #   queryable; what it is not is something to publish.
        "basis": {
            "complete": report.db_readable,
            "machine_count": len(report.machines),
            "note": (
                f"every machine that has recorded — {len(report.machines)} so far"
                if report.db_readable
                else "the shared table could not be read, so this covers THIS "
                     "MACHINE ONLY and is a floor. Other machines' spend is "
                     "missing from it, not absent from the world."
            ),
            "unpriced_calls_today": report.unpriced_today,
        },
        "cap": {
            "daily_usd": report.daily_cap_usd,
            "shared_by": list(spend_ledger.STAGES),
            "note": (
                "one cap for both stages together, not one each. Set by "
                "EXTRACTION_DAILY_BUDGET_USD; enforced against the shared ledger "
                "so it survives a restart and is seen by every worker."
            ),
            "resets_at": (report.day_starts_at.isoformat()),
            "timezone": "UTC - stated because a reader elsewhere reads midnight as their own",
        },
        "today": {
            "spent_usd": round(report.spent_today_usd, 6),
            "remaining_usd": None
            if report.remaining_usd is None
            else round(report.remaining_usd, 6),
            "fraction_used": None
            if report.fraction_used is None
            else round(report.fraction_used, 4),
            "calls": report.calls_today,
            "calls_remaining": report.calls_remaining,
            "unmetered_calls": report.unmetered_today,
            "is_a_floor_not_a_total": not report.covers_whole_window,
        },
        "by_stage": [
            {
                "stage": stage,
                "label": spend_ledger.STAGE_LABELS[stage],
                "spent_usd": round(report.by_stage_usd.get(stage, 0.0), 6),
                "calls": report.by_stage_calls.get(stage, 0),
                "ever_recorded": stage in report.stages_ever_recorded,
            }
            for stage in spend_ledger.STAGES
        ],
        "by_model": {k: round(v, 6) for k, v in report.by_model_usd.items()},
        "by_model_total": {k: round(v, 6) for k, v in by_model_total.items()},
        "by_model_tokens": dict(by_model_tokens),
        # Models whose tokens are recorded and whose price is not held here, so
        # their $0.00 means "no rate", never "no cost". `judge/extract/budget.py`
        # is where a rate is added.
        "unpriced_models": sorted(unpriced_models),
        "rates": {
            "usd_last_hour": None
            if report.usd_per_hour_recent is None
            else round(report.usd_per_hour_recent, 6),
            "hours_to_cap": None
            if report.hours_to_cap is None
            else round(report.hours_to_cap, 2),
            "price_in_per_million_usd": report.pricing_in_per_million,
            "price_out_per_million_usd": report.pricing_out_per_million,
            "measured_cost_per_call_usd": round(report.estimated_call_usd, 6),
        },
        "hourly": series(report.hourly),
        "daily": series(report.daily),
        "ledger": {
            "counting_since": None
            if report.first_seen_at is None
            else report.first_seen_at.isoformat(),
            "rows": report.total_rows,
            "unwired_stages": list(report.unwired_stages),
        },
        # ONE PANEL PER METER. Both tabs used to read `rapidapi`, so an X-only
        # sweep's reading rendered as Reddit's spend and vice versa.
        "rapidapi": _rapidapi_quota("reddit"),
        "rapidapi_x": _rapidapi_quota("x"),
        "everyone": _whole_key_spend(),
    }


# ── the admin pipeline page: what is in each stage, and what the last run did ─


@app.get("/admin/pipeline")
def admin_pipeline() -> dict:
    """The evidence pipeline, stage by stage — counts now, ledger for last run.

    Distinct from `/admin/usage`, which is money. This is EVIDENCE: how many
    rows sit in each stage, grouped by the status column that partitions it, and
    what the `job_run` ledger recorded on the last pass. Every number is
    COUNTED (rule 3), carries its population (rule 7), and a stage with no rows
    reports as NOT-YET-RUN rather than a clean zero (rule 4). Where a stage's
    discards are logged and never stored (a failed quote check, a sarcastic or
    promotional drop), it shows survivors and NAMES what it cannot count instead
    of implying none were dropped.
    """
    from judge.pages.pipeline_status import PipelineStatus

    with _conn() as conn:
        report = PipelineStatus(conn).report()

    return {
        "summary": report.summary,
        "pipeline_version": report.pipeline_version,
        "caveats": list(report.caveats),
        "stages": [
            {
                "id": s.id,
                "name": s.name,
                "lane": s.lane,
                "flow": s.flow,
                "unit": s.unit,
                "total": s.total,
                "measured": s.measured,
                "unreadable": s.unreadable,
                "caveat": s.caveat,
                "buckets": [
                    {"key": b.key, "label": b.label, "n": b.n, "tone": b.tone}
                    for b in s.buckets
                ],
            }
            for s in report.stages
        ],
        "runs_measured": report.runs_measured,
        "runs": [
            {
                "stage": r.stage,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "outcome": r.outcome,
                "running": r.running,
                "items_in": r.items_in,
                "items_out": r.items_out,
            }
            for r in report.runs
        ],
    }


# ── capability discovery review: the extractor proposes, an admin rules ───────


class CandidateRuleRequest(BaseModel):
    proposed_key: str
    ruling: str = Field(description="adopted | declined | merged")
    ruling_target: str | None = Field(
        default=None, description="the key it became; required for adopted/merged"
    )


class BoardEntryRuleRequest(BaseModel):
    """Rule every discovered entry under one slug.

    Deliberately NOT the same shape as CandidateRuleRequest, because the two
    rulings mean opposite things. A capability ruling ADMITS a key to the
    vocabulary; a board ruling CONSOLIDATES a section that is already showing.
    So `ruling_target` is required only for `merged` here, where
    CandidateRuleRequest also demands it for `adopted` - an adopted board
    section became nothing, it simply stays.
    """

    section: str = Field(description="best_for | capability | metric")
    slug: str
    ruling: str = Field(description="adopted | declined | merged")
    ruling_target: str | None = Field(
        default=None, description="the slug it folds into; required for merged"
    )
    #: WHICH ENTRIES, when the reviewer meant some of them rather than all.
    #:
    #: `None` is "the whole slug" and an EMPTY LIST IS AN ERROR, not a synonym
    #: for it. Those are different intents and only one of them is safe to guess
    #: at: a caller that sent [] believed it had a selection, and treating that
    #: as "all" would decline a whole section on a misclick. The store refuses
    #: it for the same reason.
    entry_ids: list[str] | None = Field(
        default=None,
        description="board_entry ids to rule; omit to rule the whole slug",
    )


class CandidateEditRequest(BaseModel):
    proposed_key: str
    new_key: str | None = None
    new_definition: str | None = None


class CandidateKeyRequest(BaseModel):
    proposed_key: str


@app.get("/admin/capability-candidates")
def admin_capability_candidates() -> dict:
    """Proposed capabilities awaiting a ruling, grouped by key.

    The model proposes; the admin rules. Adopting one is a
    contract/capabilities.yaml change (a PR), never a write here — the table has
    no FK to `capability` for exactly that reason. This surface records the
    decision and shows the evidence behind it.
    """
    from judge.store.capability_candidates import list_candidates

    with _conn() as conn:
        groups = list_candidates(conn)
    # Keyed `groups`, not `candidates`: the audit's web-read scanner credits a
    # `.candidates` field access to `answer.candidates` (the only column of that
    # name), turning this response shape into a phantom read of an unrelated
    # column. `groups` is what list_candidates returns anyway.
    return {
        "groups": groups,
        "summary": {
            "keys": len(groups),
            "proposals": sum(g["count"] for g in groups),
            "unruled_keys": sum(1 for g in groups if g["ruling"] is None),
        },
        "note": (
            "Counts are a floor: near-duplicate key phrasings are not yet "
            "clustered, so a capability proposed several ways is under-counted."
        ),
    }


# ── HOW EACH ARM REACHES ITS PLATFORM ─────────────────────────────────────
#
# ⚠ EVERY ROW CITES THE THING THAT MAKES IT TRUE, because "free" and "paid"
#   are claims about money and "scraping" is a claim about somebody's terms.
#   None of the three is inferable from `contract/sources.yaml` alone, so each
#   is stated here beside the file that settles it.
#
# ⚠ NO CREDENTIAL IS SHOWN, EVER — not the key, not a fingerprint, not a
#   prefix. `uses_credential` is a BOOLEAN and the page renders "uses a key" or
#   "no key". Parvathi, 2026-09-16: "no keys should be displayed just mention
#   using keys or not."
#
# `metered` is the honest name for "paid": what is measurable is that the arm
# draws down a RapidAPI quota, and `collect/usage.py` records it. The price per
# request is not in our config, so this does not claim an amount.
_ACCESS = {
    "github": {
        "method": "free API",
        "detail": "GitHub's own REST API, on the free tier.",
        "uses_credential": True,
        "credential_note": (
            "A token is sent. Anonymous access is 10 requests/minute, which the "
            "sweep refuses to run under."
        ),
        "evidence": "scripts/fetch_model.py:617 sends an Authorization header",
        "metered": False,
    },
    "reddit": {
        "method": "paid API",
        "detail": (
            "A RapidAPI reseller, verified by the ruling as a proxy of Reddit's "
            "official Data API rather than a scrape — t2_ fullnames, "
            "subreddit_id, Reddit's own cursor, 104 fields per post."
        ),
        "uses_credential": True,
        "credential_note": "A key is required; no request can be made without one.",
        "evidence": "contract/sources.yaml ruling `reddit-via-rapidapi`",
        "metered": True,
    },
    "x": {
        "method": "paid API",
        "detail": (
            "A RapidAPI reseller, and the ruling calls it a SCRAPER rather than "
            "an API proxy — the id is `x-via-rapidapi-scraper` and its "
            "access_path is `rapidapi-reseller`. Recorded as bought access to "
            "somebody else's scrape, which is not the same as our own."
        ),
        "uses_credential": True,
        "credential_note": "A key is required; no request can be made without one.",
        "evidence": "contract/sources.yaml ruling `x-via-rapidapi-scraper`",
        "metered": True,
    },
    "arxiv": {
        "method": "free API",
        "detail": "arXiv's public export API.",
        "uses_credential": False,
        "credential_note": "No key. The endpoint is open.",
        "evidence": "contract/sources.yaml `access_path: api`",
        "metered": False,
    },
    "devto": {
        "method": "free API",
        "detail": "dev.to's public article search API.",
        "uses_credential": False,
        "credential_note": "No key.",
        "evidence": "contract/sources.yaml `access_path: api`",
        "metered": False,
    },
    "hackernews": {
        "method": "free API",
        "detail": "Algolia's public index of Hacker News, not HN itself.",
        "uses_credential": False,
        "credential_note": "No key.",
        "evidence": "contract/sources.yaml `access_path: api`",
        "metered": False,
    },
    "huggingface": {
        "method": "free API",
        "detail": "Hugging Face's public API.",
        "uses_credential": False,
        "credential_note": "No key.",
        "evidence": "contract/sources.yaml `access_path: api`",
        "metered": False,
    },
    "blogs": {
        "method": "public feeds, then the article",
        "detail": (
            "The one arm that is not an API. A published RSS/Atom feed is read, "
            "then the articles it links. robots.txt is read and RE-READ on every "
            "run, and the feed path and each article path are tested against it "
            "— so this is gated by the publisher's own rules rather than by a "
            "contract we signed."
        ),
        "uses_credential": False,
        "credential_note": "No key. A feed served without login or payment.",
        "evidence": ("contract/sources.yaml rulings "
                     "`blog-class-a-self-hosted`, `blog-class-b-medium`"),
        "metered": False,
    },
}


#: The order a fetch runs them in. The parse below finds stages by scanning
#: source, which gives no ordering - and the id strings are not sortable
#: (`E3d` runs before `E3b`, `E5c` before `E5b`). Listed rather than derived,
#: because the true order is the order the calls execute and no regex knows it.
_STAGE_ORDER = (
    "?", "DB", "E1",
    "E2", "E2R", "E2A", "E2X", "E2B", "E2D", "E2H", "E2F",
    "E3", "E3d", "E3b", "E4", "E4b", "E5", "E5c", "E5b", "E6", "E7",
    "STOP",
)


def _fetch_stages_in_code() -> dict[str, str]:
    """`{stage id: name}` as `scripts/fetch_model.py` actually emits them.

    ⚠ PARSED FROM SOURCE, AND THAT IS THE POINT. A hand-kept list would be a
      second description of the pipeline, and this project has paid for that
      shape four times. The file that emits the stages is the only thing that
      knows which stages exist, so it is what gets read.

      Two call shapes: a literal `prog.stage("E4", "Triage", ...)`, and the
      per-platform harvest arms, which pass variables built from a table of
      `(platform, id, name, ...)` tuples. Both are matched; a third shape would
      go unfound, which is why the endpoint reports stages it cannot describe
      AND descriptions it cannot place.

    Returns `{}` when the file cannot be read, which the caller renders as a
    named failure rather than as "the pipeline has no stages".
    """
    import re

    src = (_REPO_ROOT / "scripts" / "fetch_model.py").read_text(encoding="utf-8")
    found: dict[str, str] = {}
    # prog.stage("E4", "Triage", ...)
    for sid, name in re.findall(r'prog\.stage\(\s*"([^"]+)",\s*"([^"]+)"', src):
        found.setdefault(sid, name)
    # ("devto", "E2D", "Harvest · dev.to", 2)
    for sid, name in re.findall(r'\(\s*"[a-z]+",\s*"(E2[A-Z])",\s*"([^"]+)"', src):
        found.setdefault(sid, name)
    return found


@app.get("/admin/stages")
def admin_stages() -> dict:
    """What happens at each stage of a fetch, in words rather than counts.

    THE COUNTS ARE ALREADY ON THE FETCH LOG, beside each stage as it runs. What
    the log cannot carry is what the stage is FOR: "E4b · 1 thread(s) held back"
    is a number and not an explanation.

    TWO SOURCES, DELIBERATELY. The LIST comes from `scripts/fetch_model.py`,
    which is what emits the stages; the WORDS come from
    `contract/pipeline_stages.yaml`, which is reviewable in a diff. Keeping them
    apart is what makes the drift visible in both directions:

      undescribed   a stage the code emits and the contract does not explain.
                    Rendered as unknown, never omitted.
      unemitted     a description for a stage nothing emits. Reported, because
                    a page describing a stage that never runs is worse than one
                    admitting a gap.

    NO FIGURES. Not one number in the payload, by design - see the contract
    file's own note on why a count here would be a figure with no denominator.
    """
    import yaml

    stages_in_code = _fetch_stages_in_code()
    described: dict[str, dict] = {}
    contract_error = None
    try:
        raw = yaml.safe_load(
            (_REPO_ROOT / "contract" / "pipeline_stages.yaml").read_text(encoding="utf-8")
        )
        described = {str(k): v for k, v in (raw or {}).get("stages", {}).items()}
    except Exception as exc:  # noqa: BLE001
        contract_error = str(exc)

    ids = [x for x in _STAGE_ORDER if x in stages_in_code]
    ids += sorted(set(stages_in_code) - set(_STAGE_ORDER))

    rows = []
    for sid in ids:
        words = described.get(sid) or {}
        rows.append({
            "id": sid,
            "name": stages_in_code.get(sid),
            "what": (words.get("what") or "").strip() or None,
            "why": (words.get("why") or "").strip() or None,
            "undescribed": not words,
        })

    return {
        "stages": rows,
        "count": len(rows),
        "source_of_list": "scripts/fetch_model.py",
        "source_of_words": "contract/pipeline_stages.yaml",
        "contract_unreadable": contract_error,
        # A description with nothing emitting it. Named rather than dropped.
        "described_but_not_emitted": sorted(set(described) - set(stages_in_code)),
        "note": (
            "Counts are not shown here on purpose - they are on the fetch log "
            "beside each stage, where they carry the run they belong to."
        ),
    }


#: Variables whose VALUE may never leave this process. The page says "set" or
#: "not set" and nothing else — not a prefix, not a length, not a fingerprint.
#:
#: MATCHED BY SUBSTRING, NOT BY EXACT NAME, deliberately. An exact list is a
#: list somebody forgets to extend, and the cost of forgetting is a published
#: credential. A non-secret caught by this reads as "set", which is a smaller
#: loss than the reverse by every measure.
_SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "DSN", "URL", "HASH")


def _is_secretish(name: str) -> bool:
    return any(marker in name.upper() for marker in _SECRET_MARKERS)


def _safe_detail(exc: BaseException) -> str:
    """An error message with everything private to this deployment removed.

    ⚠ AN EXCEPTION IS A PAYLOAD, AND THAT IS HOW A HOSTNAME GOT OUT. psycopg's
      OperationalError names the host it failed to resolve, so an endpoint that
      answered `503 the run log could not be read: {exc}` published the database
      hostname to anyone who could load the page while the database was down.

      Caught by this module's own sweep test in CI, where there is no database
      and every read fails exactly that way - which is the case nobody tests by
      hand, because locally the database answers. A message is as public as the
      page that renders it.

    Redacted by VALUE rather than by pattern: the DSN's host, user, password and
    port are known here, so they are removed wherever they appear, including
    inside a sentence no format string put them in.
    """
    text = f"{type(exc).__name__}: {exc}".strip()
    url = (os.getenv("DATABASE_URL") or "").strip()
    pieces: list[str] = []
    if url:
        pieces.append(url)
        try:
            parsed = urlparse(url)
        except ValueError:
            parsed = None
        if parsed is not None:
            # A password is redacted at ANY length; a one-character host is not
            # a real risk and blanket-replacing it would mangle every message.
            if parsed.password:
                pieces.append(parsed.password)
            pieces += [p for p in (parsed.hostname, parsed.username) if p and len(p) > 2]
            try:
                if parsed.port:
                    pieces.append(str(parsed.port))
            except ValueError:
                pass
    # Longest first, so redacting the host does not leave the full DSN
    # half-matched and partly readable.
    for piece in sorted(set(pieces), key=len, reverse=True):
        text = text.replace(piece, "<withheld>")
    # The checkout path names the account this runs under - the same objection
    # as a machine name, reached by a different route.
    return text.replace(str(_REPO_ROOT), "<repo>")


@app.get("/admin/models/propose")
def admin_models_propose(
    action: str, registry: str = "", name: str = "", kind: str = "text"
) -> dict:
    """What adding or dropping a tracked model would mean. Writes nothing.

    ⚠ A GET, AND THAT IS THE CONTRACT RATHER THAN AN OVERSIGHT. This surface
      composes a proposal and changes nothing - no file, no row, no alias. The
      thing it proposes is a change to `contract/tracked_models.yaml`, which is
      versioned config (rule 5), so it ends in a commit somebody reviews.

      `recallable` lists what the board used to show and no longer does, read
      from that file's git history - the only record of it. Two database
      proxies were measured and rejected: "has evidence" returns 71 models
      that were mostly never tracked, and "has seated aliases" returns 40.
      The history returns six.

      `add` is reached only through that list. The "Add a model" control was
      removed: it worked only for a model the registry already held, and even
      then the board did not change until the contract edit was committed and
      deployed - so a button reading "Add this model" left the models page
      saying 13. See the issue for what moving tracked membership into the
      database would cost.

      A button that wrote the board's model list somewhere else would put it in
      two places that can disagree, and the second copy would carry no review,
      no diff and no history. On the deployment it would be worse still: the
      filesystem is ephemeral, so a YAML edit made by the hosted UI dies at the
      next deploy while any rows it caused survive - the contract and the
      database disagreeing, which is the shape of the Recraft mess.

    ⚠ RUN AS A SUBPROCESS BECAUSE `judge/` MAY NOT IMPORT `collect/`. Both
      things the preview needs - `query_variants`, the project's own speller,
      and `model_version_id`, the id the registry keys on - live on the collect
      side. Same pattern as `/fetch/start` and `/admin/keywords`.
    """
    if action not in ("add", "untrack", "recallable"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"action must be `add`, `untrack` or `recallable`, not {action!r}"
            ),
        )
    if action != "recallable" and not registry.strip():
        raise HTTPException(
            status_code=400, detail=f"`{action}` needs a registry id"
        )

    script = _REPO_ROOT / "scripts" / "propose_model.py"
    args = [sys.executable, str(script), f"--{action}"]
    if registry.strip():
        args += ["--registry", registry]
    if action == "add":
        args += ["--name", name, "--kind", kind]
    try:
        done = subprocess.run(  # noqa: S603
            args,
            cwd=str(_REPO_ROOT),
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail="composing the proposal took longer than 120s and was abandoned",
        ) from exc

    # THE SCRIPT'S OWN REFUSALS COME BACK AS 400s, not as a 500. A canonical id
    # in the wrong shape is a caller's mistake and the script already says so in
    # a sentence; wrapping that in a server error would hide the sentence.
    try:
        payload = json.loads(done.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "the proposal script produced no readable output. "
                f"{_safe_detail(exc)}"
            ),
        ) from exc
    if "error" in payload:
        raise HTTPException(status_code=400, detail=payload["error"])
    if done.returncode != 0:
        raise HTTPException(
            status_code=502,
            detail=f"the proposal script exited {done.returncode}",
        )
    return payload


@app.get("/admin/runs")
def admin_runs(limit: int = 60) -> dict:
    """Every fetch run this database has seen, newest first.

    THE QUESTION THIS ANSWERS AND NOTHING ELSE DID. `/fetch/log` answers "how is
    THIS run going" and needs the run_id, which you have only if you started it.
    "What has been running, and did any of it finish?" had no reader at all — a
    run that died was found by someone noticing a stale page.

    ⚠ THE TRACKED MODELS ONLY, WHICH IS A NARROWER LIST THAN THE TABLE HOLDS.
      `fetch_log` keeps every run ever started, including runs against models
      since dropped from the board. A page listing those answers a question
      nobody has: the board shows 13 models, so this shows runs for those 13.
      How many rows that excluded is reported rather than silently dropped.

    ⚠ ALIVE IS A MEASUREMENT, NOT A STATUS. A run with no `end` record is not
      alive: a killed process writes nothing, and 22 of the 51 end records in
      this table were written by the reaper rather than by the run. So this
      reports SILENCE — the heartbeat beats every 60s and the gap since the last
      line is the evidence. `looks_dead` is that measurement, stated as such,
      and never merged with `status`.

    ⚠ NO MACHINE, NOT EVEN AS A RELATION. An earlier version reported "this
      machine" / "another host", which was already a relation rather than a
      name. It is gone entirely: this board is hosted and has one account, so
      every run a reader sees is simply a run of this board, and "another host"
      was a distinction with nothing on the other side of it. The `machine`
      column still exists and is still written; nothing reads it onto a page.
    """
    try:
        rows_limit = max(1, min(int(limit), 300))
    except (TypeError, ValueError):
        rows_limit = 60

    from judge.config import tracked_models

    # WHICH MODELS THE BOARD SHOWS, from the contract rather than from a list
    # kept here - rule 5, and the same source `/models?tracked=true` reads, so
    # dropping a model from the board drops its runs from this page too.
    tracked = tracked_models()
    wanted = {t.registry for t in tracked if t.registry}
    # ⚠ RULE 4. A tracked model with no registry id CANNOT match a run, because
    # a run is filed under one. Gemini 3.8 Flash is that case - the poll does not
    # carry it yet - so its absence from this page is caused by us and says so,
    # rather than reading as "it has never been fetched".
    unmatchable = sorted(t.name for t in tracked if not t.registry)

    try:
        with _conn() as conn:
            # `fetch_log.model_version_id` holds an `mv_` id on newer runs and a
            # bare canonical name on older ones, so BOTH spellings of every
            # tracked model are matched. Resolved by query rather than by
            # recomputing the id: the hash lives in `collect/ids.py` and the
            # lane boundary forbids importing it.
            ids = {
                row[0] for row in conn.execute(
                    "SELECT id FROM model_version WHERE canonical_id = ANY(%s)",
                    (list(wanted),),
                ).fetchall()
            } | wanted
            runs_raw = conn.execute(
                "SELECT run_id, min(at), max(at), count(*), "
                "       max(model_version_id) "
                "FROM fetch_log WHERE model_version_id = ANY(%s) "
                "GROUP BY run_id ORDER BY max(at) DESC LIMIT %s",
                (list(ids), rows_limit),
            ).fetchall()
            # ⚠ RULE 7 / RULE 4. The runs this page is NOT showing, counted, so
            # "52 runs" is not read as "every run there has ever been".
            untracked = conn.execute(
                "SELECT count(DISTINCT run_id) FROM fetch_log "
                "WHERE model_version_id IS NULL OR NOT (model_version_id = ANY(%s))",
                (list(ids),),
            ).fetchone()[0]
            ends = dict(
                conn.execute(
                    "SELECT run_id, payload FROM fetch_log WHERE kind = 'end'"
                ).fetchall()
            )
            # The LAST stage line per run — where an unfinished run got to,
            # which is the whole value of a row with no end record.
            lasts = dict(
                conn.execute(
                    "SELECT DISTINCT ON (run_id) run_id, payload FROM fetch_log "
                    "WHERE kind = 'stage' ORDER BY run_id, seq DESC"
                ).fetchall()
            )
            # Documents are reported per stage; a run's total is their sum.
            inserted = dict(
                conn.execute(
                    "SELECT run_id, sum((payload->>'documents_inserted')::int) "
                    "FROM fetch_log WHERE kind = 'stage' "
                    "  AND payload ? 'documents_inserted' GROUP BY run_id"
                ).fetchall()
            )
            names = dict(
                conn.execute(
                    "SELECT id, coalesce(display_name, canonical_id) "
                    "FROM model_version"
                ).fetchall()
            )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503, detail=f"the run log could not be read. {_safe_detail(exc)}"
        ) from exc

    now = datetime.now(UTC)
    runs = []
    for run_id, first_at, last_at, lines, mv in runs_raw:
        end = ends.get(run_id) or {}
        last = lasts.get(run_id) or {}
        silent = (now - last_at).total_seconds() if last_at else None
        finished = bool(end)
        runs.append(
            {
                "run_id": run_id,
                # `model_version_id` holds an mv_ id on newer runs and a bare
                # canonical name on older ones. Resolved where it resolves;
                # otherwise the raw value, which is already the name.
                "model": names.get(mv) or mv,
                "started_at": first_at.isoformat() if first_at else None,
                "last_at": last_at.isoformat() if last_at else None,
                "ran_minutes": (
                    round((last_at - first_at).total_seconds() / 60, 1)
                    if first_at and last_at
                    else None
                ),
                "lines": lines,
                "documents_inserted": inserted.get(run_id),
                "finished": finished,
                "status": end.get("status"),
                "detail": end.get("detail"),
                # ⚠ RULE 4. The reaper's verdict is not the run's own word, and a
                # reader deciding whether to trust "abandoned" needs to know
                # which of the two wrote it.
                "ruled_by_reaper": bool(end.get("reaped")),
                "last_stage": last.get("id"),
                "last_stage_name": last.get("name"),
                "last_stage_detail": last.get("detail"),
                # THE EVIDENCE, not a second status.
                "silent_minutes": (
                    round(silent / 60, 1) if silent is not None else None
                ),
                "missed_heartbeats": (
                    int(silent // 60)
                    if silent is not None and not finished
                    else None
                ),
                "looks_dead": bool(
                    not finished and silent is not None and silent > 180
                ),
            }
        )

    return {
        "runs": runs,
        "count": len(runs),
        "running_now": len(
            [r for r in runs if not r["finished"] and not r["looks_dead"]]
        ),
        "unfinished_and_silent": len([r for r in runs if r["looks_dead"]]),
        "heartbeat_seconds": 60,
        "reaper_threshold_minutes": 45,
        "note": (
            "A run with no end record is not necessarily alive — a killed "
            "process writes nothing. Missed heartbeats are the measurement. "
            "The reaper only rules `abandoned` after 45 minutes of silence, so "
            "between the two a corpse and a slow thread read the same."
        ),
        # ⚠ RULE 7. These runs out of what, and what was left out.
        "denominator": (
            "the shared fetch log, filtered to the models the board tracks. A "
            "run whose database write failed is in its own file and not here."
        ),
        "tracked_models": len(tracked),
        "tracked_models_matchable": len(wanted),
        "tracked_without_a_registry_id": unmatchable,
        **({"unmatchable_note": (
            "No run can be listed for "
            + ", ".join(unmatchable)
            + ": a run is filed under a registry id and "
            + ("these have" if len(unmatchable) > 1 else "this one has")
            + " none yet. That is an absence this page causes, not one it found."
        )} if unmatchable else {}),
        "runs_for_untracked_models": untracked,
        "excluded_note": (
            f"{untracked} further run(s) are in the log for models the board no "
            f"longer tracks. They are excluded, not missing."
        ),
    }


def _database_target(url: str | None) -> dict[str, object]:
    """The database NAME, and the host as a relation rather than an address.

    ⚠ NOT `writeguard.describe`, AND THE DIFFERENCE IS THE AUDIENCE. `describe`
      is right for what it is for - a log line, on the machine that wrote it -
      and it returns `host:port/dbname`. A page is not a log line: this one is
      served over the network, and the host is a reachable address, so printing
      it tells every reader where to point something. The same objection that
      removed laptop names from the usage panel applies harder to an address.

      What the reader actually needs is "is this the database I meant", and the
      NAME answers that. Whether it is local or remote answers the rest.
    """
    if not url or not url.strip():
        return {"database": None, "host": None, "unset": True}
    try:
        parsed = urlparse(url)
        if (parsed.scheme or "").strip().lower() not in ("postgres", "postgresql"):
            return {"database": None, "host": None,
                    "unreadable": "not a postgresql:// DSN"}
        name = (parsed.path or "").lstrip("/") or None
        host = (parsed.hostname or "").strip().lower()
    except ValueError as exc:
        return {"database": None, "host": None,
                "unreadable": _safe_detail(exc)}
    return {
        "database": name,
        # SAYS WHAT IT MEANS FOR THE READER. This read "a remote host", which is
        # a phrase about the SERVER and left a reader asking what it was being
        # told. What they can act on is that every query crosses a network -
        # measured here at 250ms per round trip, which is the whole reason the
        # admin page needed a connection pool.
        "host": (
            "this machine" if not host or host in ("localhost", "127.0.0.1", "::1")
            else "another machine, over the network"
        ),
        # SAID, so that a reader does not go looking for a field that was
        # deliberately left out and conclude it was forgotten.
        "host_withheld": (
            "The host and port are deliberately not shown: they are a reachable "
            "address, and this page is served over a network."
        ),
    }


@app.get("/admin/database")
def admin_database() -> dict:
    """Which database this is, what is in it, and whether its schema matches.

    ⚠ NO CREDENTIAL. `writeguard.describe` returns `host:port/dbname` and says in
      its own docstring why: "A DSN carries a password, so the string itself may
      not be logged". Nothing else about the connection is reported.
    """
    import yaml

    url = os.getenv("DATABASE_URL")
    out: dict[str, object] = {
        # 1 · WHICH DATABASE, AND CAN IT WRITE. The failure this answers: every
        # INSERT in a fetch refused with "cannot execute INSERT in a read-only
        # transaction" and no page said the connection was read-only.
        **_database_target(url),
        "read_only_dsn": is_read_only_dsn(url) if url else None,
        "read_only_note": (
            "A statement about the DSN, not about the server. A server-side "
            "default or a role setting can make a session read-only without "
            "appearing here — this answers only 'did we ask for read-only'."
        ),
        "environment": os.getenv("ENVIRONMENT", "development"),
    }

    # 2 · ROW COUNTS. The counts matter less than their RATIOS: thread_context
    # against thread_extraction is the unread backlog, and claim against
    # board_entry is how much of what was read reached a page.
    tables = (
        "model_version", "model_alias", "source",
        "document", "thread_context", "thread_extraction", "dedup_cluster",
        "claim", "board_entry", "cell", "capability_candidate",
        "harvest_run", "job_run", "fetch_log", "spend_ledger", "rapidapi_quota",
    )
    counts: dict[str, object] = dict.fromkeys(tables)
    applied: dict[str, str] = {}
    ledger_error = None
    try:
        with _conn() as conn:
            # ⚠ TWO QUERIES, NOT SIXTEEN, AND THE REASON IS LATENCY NOT TIDINESS.
            #   The database is remote: measured 2026-09-17 at 250ms per round
            #   trip and 1.58s to open a connection. A count per table is
            #   sixteen trips - four seconds of an endpoint that answered in
            #   under six - and the count itself is instant at these row counts.
            #
            #   ASKING WHICH TABLES EXIST FIRST IS WHAT KEEPS RULE 6. One query
            #   counting all sixteen would fail ENTIRELY if any one table were
            #   missing, and the obvious repair - fall back to zero - is exactly
            #   the conversion rule 6 bans: a table this build does not have and
            #   a table holding nothing are different facts. So existence is
            #   established separately, and a table that is absent stays `None`
            #   all the way to the page.
            present = [
                row[0] for row in conn.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = current_schema() "
                    "AND table_name = ANY(%s)",
                    (list(tables),),
                ).fetchall()
            ]
            if present:
                counted = conn.execute(
                    "SELECT " + ", ".join(
                        f'(SELECT count(*) FROM "{t}")' for t in present  # noqa: S608
                    )
                ).fetchone()
                counts.update(dict(zip(present, counted, strict=True)))
            # 4 · MIGRATIONS.
            try:
                applied = dict(
                    conn.execute(
                        "SELECT filename, content_hash FROM schema_migration"
                    ).fetchall()
                )
            except Exception as exc:  # noqa: BLE001
                conn.rollback()
                ledger_error = _safe_detail(exc)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503, detail=f"the database could not be read. {_safe_detail(exc)}"
        ) from exc

    out["counts"] = counts
    out["counts_absent_note"] = (
        "A null is a table this database does not have. It is not zero."
    )
    out["migrations"] = _migration_state(applied, ledger_error)

    # 5 · THE COLUMN CONTRACT.
    try:
        contract = yaml.safe_load(
            (_REPO_ROOT / "contract" / "column_states.yaml").read_text(
                encoding="utf-8"
            )
        ) or {}
        states: dict[str, int] = {}
        unreviewed = 0
        for table in (contract.get("columns") or {}).values():
            for column in (table or {}).values():
                state = (column or {}).get("state")
                if isinstance(state, str):
                    states[state] = states.get(state, 0) + 1
                if not (column or {}).get("reviewed"):
                    unreviewed += 1
        out["column_states"] = dict(sorted(states.items(), key=lambda kv: -kv[1]))
        # ⚠ RULE 7. "256 unreviewed" is a different fact at 370 columns than at
        # 260, so the figure travels with what it is out of.
        out["columns_unreviewed"] = unreviewed
        out["columns_total"] = sum(states.values())
        out["column_states_note"] = (
            "`write_only` is the bucket to read first: a column something "
            "computes and nothing reads, so a value going wrong in it would be "
            "noticed by nobody. `reserved` is declared and deliberately unused; "
            "`unwired` is declared and not connected yet — a different repair."
        )
    except Exception as exc:  # noqa: BLE001
        # ⚠ RULE 4. Said, not shown as zero columns.
        out["column_states"] = None
        out["column_states_unreadable"] = _safe_detail(exc)

    return out


def _migration_state(
    applied: dict[str, str], ledger_error: str | None
) -> dict[str, object]:
    """Files on disk against the ledger, in the three ways they can disagree.

    ⚠ THIS RECOMPUTES A HASH `collect/migrate.py` ALSO COMPUTES, AND MUST. The
      lane boundary forbids `judge/` importing `collect/`, so the rule "sha256
      of the file read as utf-8 text" is written twice. Verified against this
      database on 2026-09-17: all 18 shared filenames matched, so the two
      descriptions agree today.

      The mitigation for the day they stop agreeing is that this is the READER,
      and drift is REPORTED rather than acted on. A false alarm costs a look at
      two files; the reverse would be a silent wrong schema.
    """
    import hashlib

    directory = _REPO_ROOT / "contract" / "migrations"
    disk: dict[str, str] = {}
    try:
        for path in sorted(directory.glob("*.sql")):
            if path.name == "baseline.sql":
                continue
            disk[path.name] = hashlib.sha256(
                path.read_text(encoding="utf-8").encode("utf-8")
            ).hexdigest()
    except Exception as exc:  # noqa: BLE001
        return {"readable": False,
                "why": f"the migration files: {_safe_detail(exc)}"}

    if ledger_error is not None:
        # A database with no ledger has had no migrations applied — the same
        # statement, and `collect/migrate.py` says so where it creates the table
        # on demand. But a ledger that exists and refused to be READ is a
        # different fact, and this cannot tell the two apart, so it claims
        # neither.
        return {
            "readable": False,
            "why": f"the ledger could not be read: {ledger_error}",
            "files_on_disk": len(disk),
        }

    pending = sorted(set(disk) - set(applied))
    ahead = sorted(set(applied) - set(disk))
    drifted = sorted(n for n in set(disk) & set(applied) if disk[n] != applied[n])
    return {
        "readable": True,
        "files_on_disk": len(disk),
        "applied": len(applied),
        "agreeing": len(set(disk) & set(applied)) - len(drifted),
        # ON DISK, NOT APPLIED. The schema is behind the code, and the failure
        # shape is a column that does not exist, at request time.
        "pending": pending,
        # APPLIED, NOT ON DISK. Someone else's branch reached this database
        # first. Harmless to read, and the reason a count alone would mislead:
        # 18 files against 20 applied is not "2 pending".
        "applied_not_on_disk": ahead,
        # SAME NAME, DIFFERENT CONTENT. The one that is never benign: a file
        # edited after it was applied means the database ran something this
        # repo no longer contains.
        "drifted": drifted,
        "in_step": not pending and not drifted,
    }


def _what_the_extractor_is_asked() -> list[dict]:
    """Every field the extraction schema asks a model for, and the words it
    asks in — READ FROM THE SCHEMA AT REQUEST TIME, never transcribed.

    ⚠ RULE 11, WHICH IS WHY THIS IS NOT A PAGE SOMEBODY MAINTAINS. A copy of
      a prompt on an admin page is a count in prose with extra steps: it is
      true the day it is pasted and silently wrong afterwards, and the reader
      it misleads is the one person who went looking for the current wording.

      `axis_verbatim`'s description has been rewritten twice in a week - once
      because it said "REQUIRED" and "leave this empty" in one paragraph
      (0 absent, 19 unsupported of 22 on the run that followed), and once to
      say where a benchmark name stops. A transcription would be describing
      neither version by now.

    The descriptions ARE the prompt for these fields: they are what the
    provider is sent as the tool-call schema. So this is the instruction
    itself rather than a summary of it.
    """
    from judge.extract.schema import BoardEntry, ExtractedClaim

    out: list[dict] = []
    for model, where in ((ExtractedClaim, "claim"), (BoardEntry, "board entry")):
        for name, field in model.model_fields.items():
            if not field.description:
                continue
            out.append({
                "object": where,
                "field": name,
                "required": field.is_required(),
                "asks": field.description,
            })
    return out


#: The non-negotiables, by number and headline, read out of `CLAUDE.md`.
#:
#: ⚠ DOTALL, AND IT RETURNED 8 OF 12 WITHOUT IT. A headline wraps when it is
#:   long - rule 9's headline runs `A produced value has a named consumer,
#:   or a declared reason it has none.` across two lines, so a pattern whose
#:   `.` stopped at the line break
#:   silently skipped every rule from 9 up. Rule 12's own shape: it did not
#:   fail, it returned a shorter list that looked like the whole one.
_RULE_LINE = re.compile(r"^(\d+)\. \*\*(.+?)\*\*", re.MULTILINE | re.DOTALL)


def _the_rules() -> list[dict]:
    """The rule numbers and headlines, parsed from the file that holds them.

    HEADLINES ONLY, AND THE LINK IS THE POINT. The argument under each rule is
    what makes it followable and it is long; reproducing it here would make
    this endpoint a second copy of the document, which is the failure the
    rules themselves are about. A reader who needs the reasoning opens the
    file, and this page tells them the file exists, what is in it, and that
    nothing here was retyped.
    """
    path = Path(__file__).resolve().parents[1] / "CLAUDE.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        # Not on the container: `.dockerignore` ships the code and not the
        # repository. An empty list with `source_readable: false` beside it is
        # the honest answer; a hardcoded fallback would be the stale copy this
        # whole function exists to avoid (rule 6).
        return []
    start = text.find("## Non-negotiable rules")
    end = text.find("\n## ", start + 1) if start != -1 else -1
    if start == -1:
        return []
    body = text[start:end if end != -1 else len(text)]
    # A wrapped headline arrives with its indentation in the middle of it.
    return [{"n": int(n), "rule": " ".join(headline.split())}
            for n, headline in _RULE_LINE.findall(body)]


@app.get("/admin/settings")
def admin_settings(authorization: str | None = Header(default=None)) -> dict:
    """Who is signed in, what this is built on, and every operational cap.

    ⚠ NO SECRET VALUE LEAVES THIS FUNCTION. Anything whose NAME looks
      credential-shaped reports `set` or `not set` and nothing else — not a
      prefix, not a length, not a hash. `AUTH_PASSWORD_HASH` is in that set: a
      hash of a guessable password is not a safe thing to publish.

    THE CAPS ARE THE POINT. "What is the current LLM reading limit?" has been
    asked and answered by reading source. This answers it, and says whether the
    value is the DEFAULT or an OVERRIDE — which is how you would see that a
    `FETCH_MAX_THREADS=40` written in a file never reached the process.
    """
    import platform

    from judge import login

    # (name, default, what it does). The defaults are the ones the code falls
    # back to when the variable is unset, so `overridden` below is a fact.
    # A cap is listed (name, default, what it does). `EXTRACT_MAX_OUTPUT_TOKENS`
    # is the reason the fourth field exists: it contains "TOKEN", so the
    # substring guard below catches it and blanks it - correct as a DEFAULT, and
    # wrong for this one, which is a number with no secret in it. Rather than
    # weaken the guard, a cap can be RULED public by a person, here, one at a
    # time. The guard still refuses everything nobody has ruled on.
    cap_specs = (
        ("FETCH_MAX_THREADS", "25",
         "documents one fetch sends the model — the 'x of 25' on the button"),
        ("EXTRACT_TOTAL_TIMEOUT_SECONDS", "1200",
         "ceiling on one extraction call before it is abandoned"),
        ("EXTRACT_MAX_OUTPUT_TOKENS", "16384",
         "output ceiling per call; a truncated answer is refused, not trimmed",
         # RULED PUBLIC: a token COUNT, not a token. Nothing about it narrows a
         # guess at any credential.
         True),
        ("FETCH_HEARTBEAT_SECONDS", "60",
         "how often a live run says so — and how a dead one is detected"),
        ("FETCH_ABANDONED_AFTER_SECONDS", "2700",
         "silence before the reaper rules a run abandoned"),
        ("FETCH_MAX_GITHUB_SEARCHES", "60",
         "a runaway guard, not a budget — the GitHub API is free"),
        ("FETCH_X_PAGES", "3",
         "X pages per model; its quota is a tenth of Reddit's"),
        ("EXTRACTOR_MODEL", "deepseek/deepseek-v4-flash",
         "which model reads the evidence"),
        ("ENVIRONMENT", "development",
         "development turns the build-fixture guard off and opens this API"),
    )
    caps = []
    for spec in cap_specs:
        name, default, why = spec[0], spec[1], spec[2]
        ruled_public = spec[3] if len(spec) > 3 else False
        raw = os.getenv(name)
        secretish = _is_secretish(name) and not ruled_public
        caps.append(
            {
                "name": name,
                # The guard runs on every entry, so adding a credential to the
                # list above cannot publish it by accident - it would have to be
                # ruled public by hand, which is a decision with a name on it.
                "value": None if secretish else (raw if raw is not None else default),
                "default": None if secretish else default,
                "overridden": raw is not None and raw != default,
                "why": why,
            }
        )

    # CREDENTIALS: PRESENCE ONLY. Never a value, never a prefix, never a length.
    credentials = [
        {"name": name, "set": bool((os.getenv(name) or "").strip())}
        for name in (
            "DATABASE_URL", "API_TOKEN", "SESSION_SECRET", "AUTH_PASSWORD_HASH",
            "OPENROUTER_API_KEY", "RAPIDAPI_KEY", "GITHUB_TOKEN",
        )
    ]

    def _installed(package: str) -> str | None:
        try:
            from importlib.metadata import version

            return version(package)
        except Exception:  # noqa: BLE001
            # ⚠ RULE 6. Not installed and not askable read the same here, so
            # this claims neither — the page says "not reported".
            return None

    web: dict[str, str] = {}
    try:
        manifest = json.loads(
            (_REPO_ROOT / "web" / "package.json").read_text(encoding="utf-8")
        )
        declared = {
            **(manifest.get("dependencies") or {}),
            **(manifest.get("devDependencies") or {}),
        }
        web = {
            name: declared[name]
            for name in ("react", "react-dom", "react-router-dom", "vite")
            if name in declared
        }
    except Exception:  # noqa: BLE001
        web = {}

    def _git(*args: str) -> str | None:
        try:
            done = subprocess.run(  # noqa: S603
                ["git", *args],
                cwd=str(_REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:  # noqa: BLE001
            return None
        return (done.stdout.strip() or None) if done.returncode == 0 else None

    # WHO IS ACTUALLY HOLDING THIS SESSION, read from the caller's own token
    # rather than from configuration. `login.read` returns the email it signed,
    # or None; the shared API_TOKEN carries no identity, and that reads as such
    # rather than as the configured account.
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    signed_in_as = login.read(supplied) if supplied else None
    configured_email, configured_hash = login.account()

    return {
        "account": {
            # The email, which the person reading this page already typed.
            # Never the hash beside it.
            "signed_in_as": signed_in_as,
            "via": (
                "a signed session"
                if signed_in_as
                else (
                    "the shared API_TOKEN, which carries no identity"
                    if supplied
                    else "no credential — this API is open"
                )
            ),
            "configured_account": configured_email or None,
            "password_configured": bool(configured_hash),
            "sign_in_configured": login.is_configured(),
            "session_hours": round(login.ttl_seconds() / 3600, 1),
            "on_demo_credentials": login.uses_published_credentials(),
        },
        # Whether the board is exposed at all, and why. `auth_state` already
        # reports the demo-credentials case, which is the one that matters on
        # anything reachable.
        "auth": auth_state(),
        "runtime": {
            "python": platform.python_version(),
            "fastapi": _installed("fastapi"),
            "psycopg": _installed("psycopg"),
            "pydantic": _installed("pydantic"),
            "httpx": _installed("httpx"),
            "uvicorn": _installed("uvicorn"),
        },
        "web": web,
        "web_note": (
            "Declared in web/package.json — the range the build resolves, not "
            "the version a particular install pinned."
        ),
        # WHICH COMMIT IS RUNNING. "Is the host on the code I merged?" has been
        # unanswerable twice, and it is two git calls.
        "build": {
            "commit": _git("rev-parse", "--short", "HEAD"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "committed_at": _git("log", "-1", "--format=%cI"),
            # A deploy built from a dirty tree is not the commit it names.
            "uncommitted_changes": bool(_git("status", "--porcelain")),
        },
        "build_note": (
            "Read from the git checkout this process runs out of. A container "
            "built without the .git directory reports nulls, which means not "
            "askable — not that there is no commit."
        ),
        "caps": caps,
        "credentials": credentials,
        "credentials_note": (
            "Presence only. No value, prefix, length or hash of any credential "
            "is returned by this endpoint or rendered by this page."
        ),
    }


@app.get("/admin/sources")
def admin_sources() -> dict:
    """Every platform the harvest reaches, and how it reaches it.

    THE LIST COMES FROM THE CONTRACT, not from this file. `contract/sources.yaml`
    is what the harvest actually reads, so a platform added there appears here
    without an edit — and one that is described here but absent from the
    contract is reported as such rather than rendered as if it harvested.

    ⚠ NO CREDENTIAL IS RETURNED. Whether an arm uses a key is a boolean; the
      key, a fingerprint of it and any prefix are all absent. A page that shows
      even part of a credential has published it.

    WHAT "PAID" MEANS HERE. Two arms draw down a RapidAPI quota and
    `collect/usage.py` records the readings. The price per request is not in our
    config, so `metered: true` is the claim and a dollar figure is not.
    """
    # ⚠ THE YAML DIRECTLY, NOT `collect.registry.sources`. `judge/` may not
    #   import `collect/` - one-directional, and `tests/test_lane_boundary.py`
    #   enforces it. Same move `_rapidapi_meters` already makes for the quota
    #   file, and the same mitigation: this is a READER. It tolerates what it
    #   finds and invents nothing, so a contract change degrades to a thinner
    #   row rather than to a wrong one.
    import yaml

    try:
        doc = yaml.safe_load(
            (_REPO_ROOT / "contract" / "sources.yaml").read_text(encoding="utf-8")
        ) or {}
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"the sources contract could not be read: {exc}",
        ) from exc

    rulings = {str(r.get("id")): r for r in (doc.get("terms_rulings") or [])}
    platforms = list(doc.get("sources") or [])
    # ⚠ `feeds` IS A SEPARATE TOP-LEVEL KEY AND THIS ENDPOINT NEVER READ IT.
    #   `sources` holds the eight PLATFORMS - github, reddit, blogs, … - so the
    #   page rendered one row reading "blogs · public feeds, then the article"
    #   and could not name a single one of them. Eighteen feeds are seated and
    #   producing a real share of the corpus; which ones, and whether a given
    #   one has ever yielded anything, was answerable only by reading the
    #   contract file.
    feeds = list(doc.get("feeds") or [])

    rows: list[dict] = []
    for src in platforms:
        sid = str(src.get("id"))
        access = _ACCESS.get(sid)
        ruling_id = src.get("terms_ruling")
        ruling = rulings.get(str(ruling_id)) or {}
        rows.append({
            "id": sid,
            "platform": src.get("platform"),
            # The HOST, which is public and is how a reader checks the claim
            # above it. Not a credential and not a path with a key in it.
            "endpoint": src.get("endpoint"),
            "base_trust": src.get("base_trust"),
            "terms_ruling": ruling_id,
            "terms_reviewed_on": (
                str(ruling["reviewed_on"]) if ruling.get("reviewed_on") else None
            ),
            # ⚠ RULE 4. A `false` here means nobody has read the platform's terms
            # document - it does NOT mean the terms were read and found wanting.
            "terms_document_read": (
                (ruling.get("recorded_evidence") or {}).get("terms_document_read")
            ),
            **(access or {}),
            # DESCRIBED NOWHERE, said rather than rendered as a blank row. A
            # platform in the contract with no entry above is one this endpoint
            # has not been taught about, which is different from one that uses
            # no key.
            "undescribed": access is None,
        })

    # HOW MANY DOCUMENTS EACH FEED HAS ACTUALLY PRODUCED.
    #
    # ⚠ BEST-EFFORT, AND A FAILURE IS SAID RATHER THAN RENDERED AS ZEROS. This
    #   endpoint answered from the contract alone and so could not fail on the
    #   database; keeping that property matters more than the counts. If the
    #   read fails every feed reports `documents: None` and
    #   `counts_unreadable` carries the reason - because "this feed has
    #   harvested nothing" and "we could not ask" are opposite claims and a 0
    #   would make them identical (rule 6).
    harvested: dict[str, int] = {}
    counts_unreadable: str | None = None
    try:
        with _conn() as conn:
            for host, n in conn.execute(
                "SELECT substring(external_id from 'https?://([^/]+)') AS host, "
                "       count(*) "
                "FROM document WHERE source = 'blog' GROUP BY 1"
            ).fetchall():
                if host:
                    harvested[str(host)] = int(n)
    except Exception as exc:  # noqa: BLE001
        counts_unreadable = _safe_detail(exc)

    feed_rows: list[dict] = []
    for feed in feeds:
        fid = str(feed.get("id") or "")
        ruling_id = feed.get("terms_ruling")
        ruling = rulings.get(str(ruling_id)) or {}
        evidence = feed.get("terms_evidence") or {}
        # The host as the harvester stores it, which is what the count is keyed
        # on. `blog:medium.com/airbnb-engineering` is one feed on a shared host,
        # so the path is dropped and the count is the host's - said on the row
        # rather than silently attributed to this feed alone.
        host = fid.removeprefix("blog:").split("/")[0]
        shared_host = sum(
            1 for f in feeds
            if str(f.get("id") or "").removeprefix("blog:").split("/")[0] == host
        ) > 1
        feed_rows.append({
            "id": fid,
            "site": feed.get("site"),
            "endpoint": feed.get("endpoint"),
            "base_trust": feed.get("base_trust"),
            "provenance": feed.get("provenance"),
            # WHOSE NAME GOES ON A CLAIM FROM THIS FEED, and the reason
            # `entry` matters: it is the one value whose author is not wired
            # (#373), so a reader of this page can see which feeds are
            # affected without opening the issue.
            "byline_source": ((feed.get("measured") or {}).get("byline_source")),
            "terms_ruling": ruling_id,
            "terms_reviewed_on": (
                str(ruling["reviewed_on"]) if ruling.get("reviewed_on") else None
            ),
            # ⚠ RULE 4, AS ON THE PLATFORM ROWS. `false` means nobody read the
            # terms document - NOT that it was read and found wanting.
            "terms_document_read": evidence.get("terms_document_read"),
            "robots_allows_article_path": evidence.get("robots_allows_article_path"),
            # ⚠ `0` WHEN WE ASKED, `None` ONLY WHEN WE COULD NOT. The first
            # version was `harvested.get(host)`, which returns None for a feed
            # with no documents - so `mattrickard.com`, seated and genuinely
            # empty, reported the same value as a feed we failed to count.
            # That is precisely the conflation the comment above claims to
            # avoid, written four lines under it.
            "documents": (
                harvested.get(host, 0) if counts_unreadable is None else None
            ),
            "count_is_for_the_host": shared_host,
            "template_block": (feed.get("template_block") or {}).get("status"),
        })
    feed_rows.sort(key=lambda r: (-(r["documents"] or 0), r["id"]))

    described = {k for k in _ACCESS}
    in_contract = {str(x.get("id")) for x in platforms}
    return {
        "sources": rows,
        "count": len(rows),
        # UNDER THEIR OWN KEY, not appended to `sources`. A feed is not a
        # platform: it has no access method, no credential and no quota, and
        # eighteen of them in a list of eight platforms would make the
        # platform count meaningless.
        "blog_feeds": feed_rows,
        "blog_feed_count": len(feed_rows),
        "blog_counts_unreadable": counts_unreadable,
        "by_method": {
            m: sorted(r["id"] for r in rows if r.get("method") == m)
            for m in sorted({r.get("method") for r in rows if r.get("method")})
        },
        # BOTH DIRECTIONS OF DRIFT, because they are different problems. A
        # contract source with no description renders as unknown; a description
        # with no contract source is dead weight that would otherwise look live.
        "described_but_not_in_contract": sorted(described - in_contract),
        "credentials_note": (
            "Whether an arm uses a key is all that is recorded here. No key, "
            "fingerprint or prefix is returned by this endpoint."
        ),
    }


@app.get("/admin/keywords")
def admin_keywords() -> dict:
    """The search terms each platform is actually sent, per tracked model.

    ⚠ RUN AS A SUBPROCESS, AND THE BOUNDARY IS WHY. `judge/` may not import
      `collect/`, and `tests/test_lane_boundary.py` catches a lazy in-function
      import as readily as a top-level one - it caught this endpoint's first
      draft, which imported the GitHub query planner directly.

      The composition genuinely needs the collect lane: `plan_searches` builds
      the real GitHub queries, `club_surfaces` the one clubbed X query, and
      `_variants_for` and `_order_variants` decide the order every arm slices.
      Reimplementing any of it here would be a second description of the
      pipeline - and on a page whose whole claim is "these are the terms that go
      out", a copy is wrong the moment it drifts.

      So the same shape `POST /fetch/start` already uses: a script outside both
      lanes, run as a subprocess. `scripts/dump_keywords.py` carries the reason
      in its own docstring.

    THE COST, STATED. A process start and one SELECT per tracked model, so this
    is slower than an in-process call and it is not cached. An admin page that
    renders stale search terms would be worse than one that takes a moment.
    """
    import subprocess

    script = _REPO_ROOT / "scripts" / "dump_keywords.py"
    try:
        done = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(_REPO_ROOT),
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail="composing the search terms timed out after 180s",
        ) from exc

    if done.returncode != 0:
        # THE SCRIPT'S OWN WORDS, not a generic failure. It refuses for real
        # reasons - no database, an unreadable contract - and each needs a
        # different repair.
        detail = (done.stderr or "").strip().splitlines()
        raise HTTPException(
            status_code=503,
            detail=("the search terms could not be composed: "
                    + (detail[-1] if detail else f"exit {done.returncode}")),
        )
    try:
        return json.loads(done.stdout)
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"the search terms came back unreadable: {exc}",
        ) from exc


@app.get("/admin/prompts")
def admin_prompts() -> dict:
    """Every prompt the LIVE PIPELINE sends a model, COMPOSED not copied.

    ⚠ BUILT BY CALLING THE REAL BUILDERS. A page listing prompts is worth
      nothing if it lists a transcription: the copy drifts the first time
      somebody edits the prompt and not the page, and then the page is
      confidently wrong about the one thing it exists to show. So this calls
      `build_system_prompt` and `wrap_untrusted` exactly as `extract/runner.py`
      does, and renders what comes back.

      That is also why the capability list is read from `capabilities()` rather
      than passed a fixture - the CLOSED vocabulary is part of the prompt's
      text, so a prompt shown with a different list is a different prompt.

    ⚠ FOUR PROMPTS, NOT ONE. The extractor's system prompt is the one people
      mean, but a model in this pipeline reads three more strings and each can
      change its answer:

        - the USER MESSAGE, which is the document inside a delimited block;
        - the SCHEMA-VIOLATION retry, which quotes the validation error back;
        - the QUOTE-LENGTH retry, which replaces that generic complaint with a
          specific instruction naming the claim and its length.

      A "prompts" page showing only the system prompt would be describing a
      quarter of what the model reads.

    THE ASK BOX IS NAMED AND NOT SHOWN. `/ask/requirements`, `/ask/revise` and
    `/ask/recommend` are still wired here and `judge/ask/understand.py` still
    builds three prompts - but no page calls them: `askUnderstand` and friends
    exist in `web/src/api/index.js` and no component imports them. Retired in
    use rather than deleted, so it is listed as absent rather than omitted.

    NO SECRET IS REACHABLE. A prompt is a template; the harvested document goes
    into the block at call time and none of it is in this payload.
    """
    prompts: list[dict] = []
    placeholder = "«the flattened thread goes here»"

    try:
        from judge.extract.prompt import build_system_prompt, wrap_untrusted

        keys = sorted(capabilities().keys())
        prompts.append({
            "id": "extract-system",
            "title": "E5 · Extract — system prompt",
            "role": "system",
            "used_for": (
                "Every thread the board reads. This is the classifier: it "
                "DISCOVERS the board's sections from the evidence rather than "
                "choosing from a list, and files each claim with a verbatim "
                "quote."
            ),
            "built_by": "judge/extract/prompt.py:build_system_prompt",
            "called_from": "judge/extract/runner.py:278",
            "text": build_system_prompt(keys),
            # THE CLOSED HALF, NAMED. The prompt's asymmetry is its design - one
            # closed vocabulary, three open sections - and a reader who cannot
            # see which list was appended cannot check that the prompt they are
            # reading is the one that ran.
            "closed_vocabulary": keys,
        })

        # THE USER MESSAGE IS A PROMPT TOO, and it is the one carrying the
        # untrusted text. Shown with a placeholder where the document goes: the
        # shape is the instrument, the document is the input.
        prompts.append({
            "id": "extract-user",
            "title": "E5 · Extract — the document wrapper",
            "role": "user",
            "used_for": (
                "What the harvested thread is wrapped in before the model sees "
                "it. The delimiters are the first of five defences against a "
                "post that tries to give instructions; a document containing "
                "either marker is REFUSED rather than edited, because the "
                "extractor must read exactly what quote verification checks "
                "against."
            ),
            "built_by": "judge/extract/prompt.py:wrap_untrusted",
            "called_from": "judge/extract/runner.py:273",
            "text": wrap_untrusted(placeholder),
        })
    except Exception as exc:  # noqa: BLE001 - one failing must not blank the rest
        prompts.append({
            "id": "extract-system",
            "title": "E5 · Extract — system prompt",
            "unreadable": str(exc),
            "built_by": "judge/extract/prompt.py:build_system_prompt",
        })

    # ── THE TWO RETRIES, COMPOSED LIKE THE OTHERS ─────────────────────────
    #
    # These are appended to the user message on a failure, so the model reads
    # them exactly as it reads the system prompt - and until 2026-09-16 this
    # endpoint TRANSCRIBED them, because they were assembled inline in
    # `runner.py` with no builder to call.
    #
    # Parvathi asked what "transcribed, not composed" meant and whether the
    # model reads them. It does, and the caveat was describing a weakness in
    # this page rather than a property of the prompt - so the wording moved into
    # `prompt.py` and both are now composed. Nothing on this page is a copy.
    #
    # THE ARGUMENTS ARE ILLUSTRATIVE AND THE PAGE SAYS SO. A retry is built per
    # failure, so there is no single instance to show; what is fixed is the
    # WORDING, and that is what these render. The numbers below are the real
    # measured case from `_quote_length_correction`'s docstring - 14 claims lost
    # to two quotes 15 and 8 characters over - rather than invented ones.
    try:
        from judge.extract.prompt import (
            quote_length_correction,
            schema_violation_correction,
        )
        from judge.extract.schema import MAX_QUOTE_CHARS

        prompts.append({
            "id": "retry-schema",
            "title": "E5 \u00b7 Retry \u2014 schema violation",
            "role": "appended to the user message",
            "used_for": (
                "Sent once when the answer does not satisfy the tool schema. "
                "The validation error goes back VERBATIM rather than "
                "summarised - a model fixes a specific complaint better than a "
                "described one, and summarising would be this code guessing "
                "which part of the error mattered."
            ),
            "built_by": "judge/extract/prompt.py:schema_violation_correction",
            "called_from": "judge/extract/runner.py:_call_with_one_retry",
            "text": schema_violation_correction(
                "\u00abthe pydantic validation error, verbatim\u00bb"),
            "example_input": "The error text is the only variable part.",
        })
        prompts.append({
            "id": "retry-quote-length",
            "title": "E5 \u00b7 Retry \u2014 quote too long",
            "role": "appended to the user message",
            "used_for": (
                "Replaces the generic complaint when the only fault is an "
                "over-long quote. One extractor proposed 14 claims and lost all "
                "14 because two quotes were 15 and 8 characters over, and both "
                "had a sentence boundary well inside the limit - so a compliant "
                "span existed and the model did not pick it. The retry names "
                "each claim, its length and the limit instead of restating the "
                "rule."
            ),
            "built_by": "judge/extract/prompt.py:quote_length_correction",
            "called_from": "judge/extract/runner.py:_quote_length_correction",
            "text": quote_length_correction(
                [(11, 215), (12, 208)], [], MAX_QUOTE_CHARS),
            "example_input": (
                "Rendered with the real measured case - claims 11 and 12, at "
                "215 and 208 characters against the "
                f"{MAX_QUOTE_CHARS}-character limit. A live retry names "
                "whichever claims actually offended; every other word is fixed."
            ),
        })
    except Exception as exc:  # noqa: BLE001
        prompts.append({
            "id": "retry", "title": "E5 \u00b7 Retry corrections",
            "unreadable": str(exc),
            "built_by": "judge/extract/prompt.py",
        })

    # Read once per request on purpose (rule 11 - a cached copy is the
    # stale copy), but not twice in one response.
    rules = _the_rules()
    return {
        "prompts": prompts,
        "count": len(prompts),
        # ⚠ THE TOOL-CALL SCHEMA IS PART OF THE PROMPT, and it was the missing
        # half of this page. `prompts` above is the system message, the user
        # message and the two retry corrections; the FIELD DESCRIPTIONS are
        # sent in the same call and are what the model is actually asked to
        # fill in. A page listing four strings and omitting seventeen field
        # instructions describes a fraction of what the model reads.
        #
        # Read from the Pydantic model on every request, like everything else
        # here. `axis_verbatim` has been rewritten twice in a week; a
        # transcription would be describing neither version (rule 11).
        "schema_fields": _what_the_extractor_is_asked(),
        # NOT SENT TO A MODEL, and the page must say so. These are the
        # constraints the pipeline is built under, not instructions the
        # extractor reads - putting them on this page without that distinction
        # would imply the model has been told them.
        "rules": rules,
        "rules_source_readable": bool(rules),
        "read_from_source_at": datetime.now(UTC).isoformat(),
        # SAID, BECAUSE A LIST THAT LOOKS EXHAUSTIVE AND IS NOT IS WORSE THAN NO
        # LIST. Both groups are named so their absence is a statement.
        "not_shown": [
            {
                "what": "The Ask box — three prompts, one per input shape",
                "where": "judge/ask/understand.py:system_prompt",
                "why": (
                    "No page calls it. The routes are still wired here and the "
                    "client functions still exist in web/src/api/index.js, but "
                    "no component imports them - retired in use rather than "
                    "deleted."
                ),
            },
            {
                "what": "Three measurement scripts",
                "where": (
                    "scripts/classify_capability_reports.py, "
                    "scripts/measure_key_constraint.py, "
                    "scripts/capability_choice_pool.py"
                ),
                "why": (
                    "Run by hand to measure the pipeline, not paths a board "
                    "reader can trigger. Putting experiments beside production "
                    "under one heading would misread."
                ),
            },
        ],
    }


@app.get("/admin/board-entries")
def admin_board_entries() -> dict:
    """Discovered board sections awaiting consolidation, grouped by slug.

    THIS IS A CONSOLIDATION SURFACE, NOT A PUBLICATION GATE, and the difference
    from the capability review beside it is the whole point. A capability
    candidate is waiting OUTSIDE the vocabulary until somebody admits it. These
    are already on the board - the classifier discovered them and the board
    shows them - so an unruled row is live, not pending.

    What review is for is the failure mode an open vocabulary actually has:
    DUPLICATES. "function calling" and "tool calling" from two threads are one
    section under two names, and no code can decide that without a synonym table
    that silently merges two real sections the day it is wrong. So a person
    merges, and `documents` is the evidence they rule on.
    """
    from judge.store.board_entries import list_for_review

    with _conn() as conn:
        groups = list_for_review(conn)
    unruled = [g for g in groups if g["ruling"] is None]
    return {
        "groups": groups,
        "summary": {
            "sections": len(groups),
            "unruled": len(unruled),
            "entries": sum(g["entries"] for g in groups),
            "by_section": {
                s: sum(1 for g in groups if g["section"] == s)
                for s in ("best_for", "capability", "metric")
            },
        },
        "note": (
            "Unruled sections are ALREADY on the board - ruling consolidates, it "
            "does not publish. Counts are a floor: one section can arrive under "
            "two slugs until they are merged."
        ),
    }


@app.post("/admin/board-entries/rule")
def admin_rule_board_entry(req: BoardEntryRuleRequest) -> dict:
    """Adopt / decline / merge every entry under one slug."""
    from judge.store.board_entries import (
        RULINGS,
        SECTIONS,
        rule_entries,
        rule_entry_ids,
    )

    # Validated before a connection is opened, so a bad request fails fast and
    # without a database. Stated here AND in the store, so neither is the only
    # guard - the store is reachable from the pipeline too.
    if req.section not in SECTIONS:
        raise HTTPException(status_code=422, detail=f"section must be one of {SECTIONS}")
    if not req.slug.strip():
        raise HTTPException(status_code=422, detail="slug is required")
    if req.ruling not in RULINGS:
        raise HTTPException(status_code=422, detail=f"ruling must be one of {RULINGS}")
    if req.ruling == "merged" and not (req.ruling_target or "").strip():
        raise HTTPException(
            status_code=422,
            detail="merged requires a ruling_target: the slug this one folds into. "
                   "Without it the rows would be hidden rather than merged, which "
                   "loses the evidence instead of consolidating it.",
        )
    # AN EMPTY SELECTION IS REFUSED RATHER THAN WIDENED. `None` means the
    # reviewer asked for the section; `[]` means they thought they had ticked
    # something. Reading the second as the first is how one misclick declines a
    # capability, and the difference is invisible on the button.
    if req.entry_ids is not None and not req.entry_ids:
        raise HTTPException(
            status_code=422,
            detail="entry_ids was empty. To rule the whole section, omit the "
                   "field entirely - that is a different decision and has to be "
                   "asked for rather than fallen into.",
        )
    try:
        with _conn() as conn:
            if req.entry_ids:
                ruled = rule_entry_ids(
                    conn, ids=req.entry_ids,
                    ruling=req.ruling, ruling_target=req.ruling_target,
                )
            else:
                ruled = rule_entries(
                    conn, section=req.section, slug=req.slug,
                    ruling=req.ruling, ruling_target=req.ruling_target,
                )
            conn.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"section": req.section, "slug": req.slug, "ruling": req.ruling,
            "ruling_target": req.ruling_target, "rows_ruled": ruled}


@app.post("/admin/board-entries/unrule")
def admin_unrule_board_entry(req: BoardEntryRuleRequest) -> dict:
    """Undo a ruling, putting the section back on the board unchanged.

    `ruling` and `reviewed_at` are CHECKed to move together, so a reviewer
    cannot clear one by hand without violating the constraint. A review surface
    somebody cannot back out of is one they hesitate to use, which is how a
    board fills with rulings nobody was sure about.
    """
    from judge.store.board_entries import SECTIONS, unrule_entries, unrule_entry_ids

    if req.section not in SECTIONS:
        raise HTTPException(status_code=422, detail=f"section must be one of {SECTIONS}")
    # UNDO IS PER-QUOTE TOO, and it has to be. A per-quote decline whose only
    # undo was per-slug would be worse than no undo at all: backing out one
    # mistake would un-decline every other quote in the section, including the
    # ones somebody meant.
    if req.entry_ids is not None and not req.entry_ids:
        raise HTTPException(
            status_code=422,
            detail="entry_ids was empty. Omit the field to clear the whole section.",
        )
    with _conn() as conn:
        if req.entry_ids:
            cleared = unrule_entry_ids(conn, ids=req.entry_ids)
        else:
            cleared = unrule_entries(conn, section=req.section, slug=req.slug)
        conn.commit()
    return {"section": req.section, "slug": req.slug, "rows_cleared": cleared,
            "scope": "entries" if req.entry_ids else "section"}


@app.post("/admin/capability-candidates/rule")
def admin_rule_candidate(req: CandidateRuleRequest) -> dict:
    """Adopt / decline / merge every proposal for one key."""
    from judge.store.capability_candidates import RULINGS, rule_candidates

    # Validate BEFORE opening a connection, so a bad request fails fast and
    # without a database (and the constraints are stated once, here and in the
    # store, so neither is the only guard).
    if not req.proposed_key.strip():
        raise HTTPException(status_code=422, detail="proposed_key is required")
    if req.ruling not in RULINGS:
        raise HTTPException(status_code=422, detail=f"ruling must be one of {RULINGS}")
    if req.ruling in ("adopted", "merged") and not (req.ruling_target or "").strip():
        raise HTTPException(
            status_code=422, detail=f"{req.ruling} requires a ruling_target (what it became)"
        )
    with _conn() as conn:
        ruled = rule_candidates(
            conn, proposed_key=req.proposed_key, ruling=req.ruling,
            ruling_target=req.ruling_target,
        )
        conn.commit()
    return {"proposed_key": req.proposed_key, "ruling": req.ruling, "rows_ruled": ruled}


@app.post("/admin/capability-candidates/edit")
def admin_edit_candidate(req: CandidateEditRequest) -> dict:
    """Fix a proposed key's name and/or definition."""
    from judge.store.capability_candidates import edit_candidates

    if not req.proposed_key.strip():
        raise HTTPException(status_code=422, detail="proposed_key is required")
    with _conn() as conn:
        edited = edit_candidates(
            conn, proposed_key=req.proposed_key,
            new_key=req.new_key, new_definition=req.new_definition,
        )
        conn.commit()
    return {"proposed_key": req.new_key or req.proposed_key, "rows_edited": edited}


@app.post("/admin/capability-candidates/delete")
def admin_delete_candidate(req: CandidateKeyRequest) -> dict:
    """Discard a proposal that is noise (hard delete; declining keeps evidence)."""
    from judge.store.capability_candidates import delete_candidates

    if not req.proposed_key.strip():
        raise HTTPException(status_code=422, detail="proposed_key is required")
    with _conn() as conn:
        deleted = delete_candidates(conn, proposed_key=req.proposed_key)
        conn.commit()
    return {"proposed_key": req.proposed_key, "rows_deleted": deleted}


def _whole_key_spend() -> dict:
    """Total spent on the API KEY, by anyone, straight from the provider.

    Everything else on this page comes from `judge/spend_ledger.py`, which is a
    local file. The API key is not local. So the rest of the page is one
    machine's share of a key several people spend from - measured 2026-08-20,
    our ledger held $0.000000 while the key reported $0.0089013.

    One figure, from `GET /key`. A metadata call: zero tokens, $0.00.

    DELIBERATELY NOT THE PROVIDER'S LIMITS. Their account credit and per-key cap
    are different ceilings on a different schedule; ours is
    EXTRACTION_DAILY_BUDGET_USD. Usage answers who spent it, which is the
    question here. Restating their limits was tried and removed.

    UNREACHABLE IS NOT ZERO. `available: False` carries a reason, because a
    provider we cannot reach must never render as a key nobody has spent on -
    the most reassuring of the readings available, and rule 6 forbids the
    conversion.
    """
    from judge import key_usage

    usage = key_usage.fetch()
    if not usage.available:
        return {
            "available": False,
            "why": usage.unavailable_because,
            "headline": (
                "Total spend across all machines is UNKNOWN, which is not zero. "
                "Everything below is this machine only."
            ),
        }
    return {
        "available": True,
        "scope": "every machine using this API key",
        "total_usd": usage.total_usd,
        "today_usd": usage.today_usd,
        "headline": (
            "Spent on this key by anyone, reported by the provider. Everything "
            "below it is this machine's ledger only, which is why the two differ."
        ),
        "day_boundary_note": (
            "the provider's day window is its own and the API does not state "
            "whether it aligns with the 00:00 UTC our cap resets at, so this "
            "sits beside our figure rather than being compared to it"
        ),
    }


def _this_machine_name() -> str:
    """This host's name, used ONLY to compute a relation and never rendered.

    `reading_host` says "this machine" or "another host"; the comparison needs
    the name and the page does not. Kept as a one-line helper so the two call
    sites cannot drift, and so the name has exactly one place it is read.
    """
    from judge.spend_ledger import machine as _m

    return _m()


def _rapidapi_meters() -> dict[str, dict]:
    """Every arm's latest quota reading, keyed by `read_on`. `{}` when none.

    ⚠ THIS DUPLICATES `collect/usage.py:read_rapidapi_meters` AND MUST. `judge/`
      may not import `collect/` - the lane boundary is one-directional and an
      AST test enforces it - so the file's shape is described twice, which is
      exactly the "two descriptions of one thing" this project has paid for
      four times. The mitigation is that this is the READER: it tolerates every
      shape the writer has ever produced and invents nothing, so a writer change
      degrades to "no reading" rather than to a wrong one.

      Both shapes are handled. `{"meters": {...}}` since 2026-09-10; a bare
      single record before that, filed under its own `read_on`, or under
      `"unrecorded"` when it predates that field - which means the path was not
      recorded, not that no arm read it.
    """
    store = _REPO_ROOT / "var" / "rapidapi-quota.json"
    local: dict[str, dict] = {}
    try:
        raw = json.loads(store.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            meters = raw.get("meters")
            if isinstance(meters, dict):
                local = {k: v for k, v in meters.items() if isinstance(v, dict)}
            elif "quota_remaining" in raw or "quota_limit" in raw:
                local = {raw.get("read_on") or "unrecorded": raw}
    except (OSError, ValueError):
        local = {}

    # EVERY LOCAL READING IS STAMPED BEFORE THE MERGE, so the winner can say
    # where it came from. The file records no machine - it never needed to,
    # being one host's private note - so this supplies the one fact it is
    # missing and the shared rows already carry.
    from judge.spend_ledger import machine as _this_machine

    here = _this_machine()
    for row in local.values():
        row.setdefault("source", "this machine")
        row.setdefault("machine", here)

    # THE SHARED TABLE, MERGED IN BY NEWEST *READING*. The quota is a counter
    # the whole team draws down, so this machine's file is one view of it and
    # usually not the freshest. `at` is a fixed-width ISO-8601 UTC string, so
    # lexical order is chronological order - the same property the file reader
    # already relies on to pick a latest record.
    #
    # THE LOSER IS KEPT, NOT DISCARDED, under `also_held`. A stale local
    # reading beside a fresher shared one is the NORMAL case on a shared
    # subscription, and dropping it would make "this machine has never
    # fetched" and "this machine fetched earlier" render identically - which
    # is the same collapse rule 4 forbids one layer up.
    # ⚠ AND THEY ARE ONLY COMPARABLE IF THEY ARE READINGS OF THE SAME
    #   SUBSCRIPTION, WHICH NOTHING CHECKED UNTIL 2026-09-16.
    #
    #   `meter` says WHICH counter (reddit or x). It does not say WHOSE. The
    #   board is hosted, so a run starts from any browser, and `x.py:key_for`
    #   falls back `X_RAPIDAPI_KEY` -> `RAPIDAPI_KEY` - so two hosts with
    #   different env read different accounts on the same arm. Merged by
    #   recency, the fresher of two unrelated counters simply wins and the
    #   number moves for no reason a reader can see.
    #
    #   `key_fingerprint` is sha256(key)[:12] and is what makes that checkable.
    #   A DISAGREEMENT IS SHOWN, NOT RESOLVED: picking one would be asserting
    #   that one of two real subscriptions is the real one.
    #
    #   ABSENT IS UNKNOWN, NOT MISMATCHED (rule 6). Every row written before
    #   today has no fingerprint, and reading that as "a different account"
    #   would light this warning across the whole existing table.
    for meter, row in (_rapidapi_meters_from_db() or {}).items():
        row = {**row, "source": "shared table"}
        held = local.get(meter)
        if held is None:
            local[meter] = row
            continue
        a, b = row.get("key_fingerprint"), held.get("key_fingerprint")
        differ = bool(a) and bool(b) and a != b
        if str(row.get("at") or "") > str(held.get("at") or ""):
            local[meter] = {**row, "also_held": held}
        else:
            local[meter] = {**held, "also_held": row}
        if differ:
            local[meter]["subscriptions_differ"] = True
    return local


#: The shared-table read, as a constant SO IT CAN BE TESTED.
#:
#: `tests/conftest.py` stubs `_rapidapi_meters_from_db` to `lambda: None` for
#: every test that has imported `judge.app`, which is right - it stops ~3000
#: tests reaching a real database - and it also means the function cannot be
#: called in a test to check what it selects. The defect this guards against was
#: EXACTLY a missing column name in this string, so the string is the thing worth
#: pinning and a constant is how a test can see it.
_QUOTA_SELECT = (
    "select meter, quota_remaining, quota_limit, read_at, read_by, "
    "       source_run_id, machine, key_fingerprint, quota_reset_seconds "
    "  from rapidapi_quota"
)


def _rapidapi_meters_from_db() -> dict[str, dict] | None:
    """Every machine's latest reading, or None when the table cannot be read.

    None rather than `{}`: an unreachable database and a meter nobody has read
    are different facts, and only one of them means the panel is showing one
    laptop's view of a shared counter.
    """
    try:
        with _conn() as conn:
            # ⚠ `key_fingerprint` WAS NOT IN THIS SELECT, AND IT IS THE WHOLE
            #   OF #330's CHECK. The column was added to `rapidapi_quota` that
            #   same morning and `collect/usage.py` writes it on every metered
            #   call - but nothing read it back here, so `row.get(
            #   "key_fingerprint")` in `_rapidapi_meters` was always None,
            #   `differ` was always False, and `subscriptions_differ` could
            #   never become True for a shared-table row against a local one.
            #
            #   The feature was present in the schema, wired at the writer,
            #   tested at the comparison, and DEAD AT THE READER. Rule 9 from
            #   the other end: not a value with no consumer, but a consumer
            #   silently handed a constant None.
            rows = conn.execute(_QUOTA_SELECT).fetchall()
    except Exception:
        return None
    return {
        str(m): {
            "quota_remaining": rem,
            "quota_limit": lim,
            "at": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "read_on": str(m),
            "read_by": str(by),
            "source_run_id": run,
            "machine": str(mach),
            # None stays None. Every row written before 2026-09-16 has no
            # fingerprint, and reading that as "a different account" would light
            # the warning across the whole table (rule 6).
            "key_fingerprint": fp,
            # Seconds to this meter's reset, as read. NULL is "not
            # recorded", never "resets now" (rule 6).
            "quota_reset_seconds": reset,
        }
        for m, rem, lim, at, by, run, mach, fp, reset in rows
    }


#: WHAT IS MEASURED ABOUT EACH ARM'S WINDOW, AND WHAT IS NOT.
#:
#: An ANCHOR plus a PERIOD rather than a pair of dates, deliberately. Dates go
#: stale on a schedule - "next boundary 2026-10-11" is wrong from 11 October and
#: nothing would say so, which is the #334 class this panel has already produced
#: three instances of. An anchor and a period are true for as long as the period
#: is, and every boundary is arithmetic from them.
#:
#: reddit  MEASURED. 2,592,000 s between two dated boundaries, 2026-09-11 and
#:         2026-10-11, agreeing to the second.
#: x       NOT MEASURED. One boundary is dated and one boundary is not a period.
#:         `period_seconds: None` is the honest value and the panel renders the
#:         left end of the bar as undated rather than assuming reddit's 30 days -
#:         same gateway, different upstream (rule 6).
#:
#: docs/measurements/rapidapi-window-length.md
QUOTA_WINDOW = {
    "reddit": {
        "anchor": "2026-09-11T09:45:23+00:00",
        "period_seconds": 2_592_000,
        "measured": True,
        "source": "docs/measurements/rapidapi-window-length.md, two readings 22.7 days apart",
    },
    "x": {
        "anchor": "2026-09-29T06:23:49+00:00",
        "period_seconds": None,
        "measured": False,
        "source": "docs/measurements/rapidapi-window-length.md, one boundary only",
    },
}


def _quota_window(read_on: str, reading_at: str | None, reset_seconds: object) -> dict:
    """This arm's window, preferring the LIVE reading over the stored anchor.

    THE READING WINS WHEN IT HAS THE HEADER. `read_at + x-ratelimit-requests-reset`
    dates the next boundary directly, and it cannot go stale because it is
    recomputed from whatever was last read. The anchor below is the fallback for
    rows written before `quota_reset_seconds` existed - every row today.

    A PERIOD IS NOT INFERRED FROM A SINGLE BOUNDARY. `x` has one dated boundary
    and no period, so `period_seconds` is None and stays None until a second X
    reading dates a second one. Returning reddit's 30 days there would be the
    exact assumption the measurement refused to make.
    """
    from datetime import datetime, timedelta

    spec = QUOTA_WINDOW.get(read_on) or {}
    period = spec.get("period_seconds")
    out = {
        "period_seconds": period,
        "period_days": (period / 86400) if period else None,
        "period_measured": bool(spec.get("measured")),
        "source": spec.get("source"),
        "next_boundary": None,
        "previous_boundary": None,
        "boundary_from": None,
    }

    def _parse(value):
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None

    # 1. The live reading, when it carried the header.
    at = _parse(reading_at)
    if at is not None and isinstance(reset_seconds, int):
        nxt = at + timedelta(seconds=reset_seconds)
        out["next_boundary"] = nxt.isoformat()
        out["boundary_from"] = "this reading's x-ratelimit-requests-reset header"
        if period:
            out["previous_boundary"] = (nxt - timedelta(seconds=period)).isoformat()
        return out

    # 2. The anchor. With a period, roll it forward to the window we are in; a
    #    boundary in the past is not this window's and must not render as one.
    anchor = _parse(spec.get("anchor"))
    if anchor is None:
        return out
    if period:
        now = datetime.now(anchor.tzinfo)
        nxt = anchor
        while nxt <= now:
            nxt = nxt + timedelta(seconds=period)
        out["next_boundary"] = nxt.isoformat()
        out["previous_boundary"] = (nxt - timedelta(seconds=period)).isoformat()
        out["boundary_from"] = "the measured anchor and period, rolled forward"
    else:
        # NO PERIOD: the one dated boundary, and whether it has passed. Once it
        # has, this arm has nothing current to say and the panel must say THAT
        # rather than render a date that is behind us.
        now = datetime.now(anchor.tzinfo)
        out["next_boundary"] = anchor.isoformat() if anchor > now else None
        out["boundary_passed"] = anchor.isoformat() if anchor <= now else None
        out["boundary_from"] = "a single dated boundary; no period is known"
    return out


def _rapidapi_series(read_on: str) -> dict | None:
    """The reading history for one meter, or None when the table cannot be read.

    NONE AND EMPTY ARE DIFFERENT AND THE PANEL RENDERS THEM DIFFERENTLY. None is
    "the table could not be read"; `readings: 0` is "nothing has been recorded
    yet", which is the true state on the day the table ships and is a fact about
    our instrumentation rather than about consumption.

    A RATE NEEDS TWO POINTS AND CARRIES ITS SPAN. One reading gives no rate at
    all; a rate without the window it was measured over answers a question
    nobody asked, because this harvest is bursty (1,103 documents on one run,
    2 on the next).
    """
    try:
        with _conn() as conn:
            rows = conn.execute(
                "select read_at, quota_remaining from rapidapi_quota_reading "
                "where meter = %s and quota_remaining is not null "
                "order by read_at",
                (read_on,),
            ).fetchall()
    except Exception:
        return None

    out = {"readings": len(rows), "per_day": None, "span_days": None,
           "first_at": None, "last_at": None, "consumed": None}
    if not rows:
        return out
    out["first_at"] = rows[0][0].isoformat()
    out["last_at"] = rows[-1][0].isoformat()
    if len(rows) < 2:
        return out
    span = (rows[-1][0] - rows[0][0]).total_seconds()
    consumed = rows[0][1] - rows[-1][1]
    out["span_days"] = span / 86400
    out["consumed"] = consumed
    # A span of zero is real - several readings inside one second - and dividing
    # by it would render inf. Absent rather than infinite (rule 6).
    out["per_day"] = (consumed / (span / 86400)) if span > 0 else None
    return out


def _rapidapi_quota(read_on: str = "reddit") -> dict:
    """ONE ARM's RapidAPI quota panel - `reddit` or `x`, billed in REQUESTS.

    Shows the latest quota HEADER reading that arm persisted
    (`var/rapidapi-quota.json`), with WHEN it was read. RapidAPI cannot share an
    axis with the LLM cap: one is dollars per day against a limit we set, the
    other is requests against a limit somebody sells us. Same page, separate tab.

    ⚠ IT TAKES AN ARM BECAUSE THE ARMS ARE SEPARATELY METERED, AND UNTIL
      2026-09-10 IT DID NOT. This returned one dict, and `UsagePanel.jsx` fed it
      to BOTH the Reddit tab and the X tab with only the heading changed - so
      whichever arm read last was displayed as the other's spend. The X tab told
      the reader "one key meters both paths, so the figure is the X spend too",
      which was the inherited premise and is false: measured that day, the two
      keys are separate subscriptions with limits of 1,000,000 and 100,000, each
      403 on the other's provider.

      An arm with no reading now returns `instrumented: False` - "this arm has
      not been read" - instead of borrowing the other's number. That is rule 4
      at the panel: an absence must not render as a measurement.

    Two things this deliberately gets right, from the review that reverted an
    earlier attempt:
      * It shows RapidAPI's OWN header value cached with its date, not a figure
        recomputed here - so it is not a second source of truth for a quantity we
        do not own. When the reading moves, it is because the provider's number
        moved, not because we recalculated one.
      * It is shown 'as of' that date, never as live, because the quota moves
        only when a fetch runs and a dated reading on a live dashboard would
        otherwise read as current.

    Requests, not dollars: the plan's per-request price is not in config, so a
    dollar figure would be invented (rule 6). Requests USED is the spend on the
    key - `limit - remaining`.
    """
    arm_label = "X" if read_on == "x" else "Reddit"
    # "an X" / "a Reddit" - the article follows the label, not the code.
    arm_article = "an" if read_on == "x" else "a"
    base = {
        "unit": "requests",
        "arm": read_on,
        # ⚠ THIS SENTENCE HAS NOW BEEN WRONG TWICE, IN OPPOSITE DIRECTIONS, AND
        #   THE SECOND TIME LASTED THIRTY MINUTES. It first called the quota
        #   "monthly" with nothing behind it. #331 corrected that to "THE WINDOW
        #   LENGTH IS NOT MEASURED" at 12:15Z on 2026-09-16 — and it was
        #   measured at 12:45Z the same day, by two metered readings
        #   (docs/measurements/rapidapi-window-length.md, #333).
        #
        #   Both were true when written. Neither was about this file, which is
        #   why nothing here could catch either — see issue #334. The figures
        #   below are therefore stated per ARM and with their boundaries, so the
        #   next reader can check them against the world rather than trust the
        #   prose.
        "limits_status": (
            (
                # REDDIT: MEASURED. 2,592,000 s between two dated boundaries.
                "RapidAPI sells the Reddit path as a request quota per resetting "
                "window, and that window is MEASURED at exactly 30.000 days "
                "(2,592,000 s) — boundaries 2026-09-11 09:45:23 UTC and "
                "2026-10-11 09:45:22 UTC. That is 30 days, NOT a calendar month: "
                "it does not align to the 1st and the boundary rolls at 09:45 "
                "UTC, so anything costed per-month is out by up to a day."
                if read_on != "x" else
                # X: ONE BOUNDARY IS NOT A PERIOD. Not inherited from Reddit's.
                "RapidAPI sells the X path as a request quota per resetting "
                "window. Its next boundary is dated 2026-09-29 06:23:49 UTC, and "
                "ITS LENGTH IS NOT MEASURED — one boundary is not a period. "
                "Reddit's 30 days is deliberately NOT assumed here: same "
                "gateway, different upstream. One X reading after 29 September "
                "dates a second boundary and settles it, for one request."
            )
            + f" This is the last quota header {arm_article} {arm_label} fetch "
            "saw; it moves only when a fetch runs, not on a schedule. The Reddit "
            "and X arms are metered separately - this figure is this arm's alone."
        ),
    }
    # ⚠ `source_of_record` IS COMPUTED BELOW, NOT SET HERE, AND THAT IS THE FIX.
    #   It was the constant "var/rapidapi-quota.json, meters[...]" while
    #   `_rapidapi_meters` had already merged the shared table in - so a
    #   reading taken on ANOTHER machine could render under a caption naming
    #   this one's file. The panel then said, in one line, both that the
    #   subscription is shared and that the figure is local.
    meters = _rapidapi_meters()
    rec = meters.get(read_on)
    if not rec:
        # AN UNATTRIBUTED READING IS SURFACED, NOT DROPPED. A record written
        # before `read_on` existed is filed under `unrecorded`, and it is a real
        # header reading - so reporting this arm as simply "not read" would
        # convert evidence we HAVE into an absence, which is rule 4 pointed the
        # other way. It is also not attributable to this arm, so it must not be
        # displayed as this arm's figure. Both facts, stated: the arm is not
        # instrumented, AND an unattributed reading exists.
        orphan = meters.get("unrecorded")
        return {
            **base,
            "source_of_record": (
                "no reading for this arm, in this machine's "
                "var/rapidapi-quota.json or in the shared rapidapi_quota table"
            ),
            "instrumented": False,
            # KNOWN EVEN WITH NO READING. The window is a fact about the
            # subscription, not about whether we have read it lately.
            "window": _quota_window(read_on, None, None),
            "series": _rapidapi_series(read_on),
            "unattributed_reading": (
                None if not orphan else {
                    "quota_remaining": orphan.get("quota_remaining"),
                    "quota_limit": orphan.get("quota_limit"),
                    "as_of": orphan.get("at"),
                    "why_not_shown": (
                        "this reading predates the field that records which arm "
                        "took it, so it cannot be attributed to the Reddit or "
                        "the X meter. The two are separate subscriptions with "
                        "different limits, so showing it under either heading "
                        "would assert a path nobody recorded."
                    ),
                }
            ),
            "headline": (
                f"No quota reading recorded for the {arm_label} arm yet. "
                "RapidAPI's usage arrives in response headers, so this fills in "
                f"after the first {arm_label} fetch and updates on each one - it "
                "is not live. The other arm's reading is NOT shown here: the two "
                "are separate subscriptions with different limits, so borrowing "
                "it would put one meter's number under the other's heading."
            ),
        }
    limit = rec.get("quota_limit")
    remaining = rec.get("quota_remaining")
    # USED IS ONLY COMPUTABLE WITH BOTH HALVES. A reading that carries
    # `remaining` and no `limit` cannot yield "requests used", and the previous
    # stored limit must not stand in for it - not because the tier moves, but
    # because THE PREVIOUS READING MAY BE A DIFFERENT METER (see below).
    # `None` here, and the page says which figure is missing (rules 6, 7).
    #
    # ⚠ THIS COMMENT USED TO CONCLUDE "the tier changed", AND IT WAS WRONG.
    #   It read 998,076-of-1,000,000 on 2026-08-31 against 99,870 nine days
    #   later, found the 900k gap impossible, and inferred a tier change. The
    #   two figures were never one meter: the second was `read_on="x"`.
    #   Measured 2026-09-10 - Reddit's key reads limit=1,000,000 with 996,207
    #   remaining, and X's reads limit=100,000 with 99,868. No tier changed on
    #   either. The premise that made the inference look necessary was "one key
    #   meters both arms", asserted in `.env.example` and copied here; it is
    #   false on this project's own `.env`, where the two keys are separate
    #   subscriptions that each 403 on the other's provider.
    #
    #   Recorded rather than quietly deleted, because the arithmetic was
    #   CORRECT and the conclusion still wrong - the gap really is impossible
    #   for one meter. What was missing was the denominator's IDENTITY, which
    #   is rule 7 on a figure that had already survived inspection twice.
    used = limit - remaining if isinstance(limit, int) and isinstance(remaining, int) else None
    other = rec.get("also_held")
    source = str(rec.get("source") or "this machine")
    taken_on = str(rec.get("machine") or "an unrecorded machine")
    shared = source == "shared table"
    #: "this machine" / "another host" — the relation, never the name.
    here_or_there = ("this machine" if taken_on == _this_machine_name()
                     else "another host")
    return {
        **base,
        # ⚠ THE PROSE CARRIED THE HOSTNAME TOO, which is how it survived the
        #   first pass: the field-by-field sweep found `reading_machine` and
        #   missed a sentence with a name inside it. A test now greps the WHOLE
        #   payload rather than the fields it thought of.
        "source_of_record": (
            (f"the shared `rapidapi_quota` table, meter '{read_on}', last "
             f"written from {here_or_there}"
             if shared else
             f"this machine's var/rapidapi-quota.json, meters['{read_on}']")
            + " from RapidAPI's x-ratelimit-* headers - the provider's own "
              "number, shown with the date it was taken"
        ),
        "reading_source": source,
        # ⚠ THE RELATION, NOT THE NAME. "this machine" or "another host" is the
        #   whole of what a reader acts on - is my cached figure the stale one,
        #   or somebody else's - and it is the only part that survives onto a
        #   web page. The hostname itself said "ANOOJ" on an admin screen and
        #   bought nothing; `rapidapi_quota.machine` still records it.
        "reading_host": ("this machine" if taken_on == _this_machine_name()
                         else "another host"),
        # WHOSE COUNTER. sha256(key)[:12], never the key. None on readings taken
        # before 2026-09-16 or with no credential - "not recorded", never "a
        # different account".
        "key_fingerprint": rec.get("key_fingerprint"),
        # SET ONLY WHEN TWO READINGS NAME DIFFERENT SUBSCRIPTIONS, in which case
        # they are not a stale/fresh pair and the panel must not present them as
        # one counter. Absent fingerprints never set it (rule 6).
        "subscriptions_differ": bool(rec.get("subscriptions_differ")),
        # THE READING THIS ONE BEAT, kept rather than dropped. On a shared
        # subscription a stale local figure beside a fresher shared one is the
        # NORMAL case and not an error; the panel names both so a reader can
        # see that this machine has fetched, just not most recently.
        "also_held": (
            None if not isinstance(other, dict) else {
                "quota_remaining": other.get("quota_remaining"),
                "quota_limit": other.get("quota_limit"),
                "as_of": other.get("at"),
                "source": other.get("source"),
                "host": ("this machine"
                         if other.get("machine") == _this_machine_name()
                         else "another host"),
                "key_fingerprint": other.get("key_fingerprint"),
                "why_not_shown": (
                    "an older reading of the same meter. The quota only "
                    "decreases, so the newest reading is the truest one - this "
                    "is here to show the other side has also fetched, not as a "
                    "second figure to compare."
                ),
            }
        ),
        "instrumented": True,
        # THE WINDOW, COMPUTED RATHER THAN WRITTEN DOWN. Prefers this reading's
        # own reset header; falls back to the measured anchor and period. `x`
        # carries period_seconds: None and the panel renders that end of the bar
        # as undated rather than borrowing reddit's 30 days.
        "window": _quota_window(read_on, rec.get("at"),
                                rec.get("quota_reset_seconds")),
        # THE SERIES. `None` means the table could not be read; `readings: 0`
        # means nothing has been recorded yet, which is the true state the day
        # the table ships. Two different facts, rendered differently (rule 4).
        "series": _rapidapi_series(read_on),
        "quota_reset_seconds": rec.get("quota_reset_seconds"),
        "quota_limit": limit,
        "quota_remaining": remaining,
        "requests_used": used,
        "as_of": rec.get("at"),
        # WHAT KIND OF CALLER TOOK IT. `harvest`, `sweep` or `probe` — a probe's
        # reading is as real as a fetch's, and saying which stops "a fetch must
        # have run" being inferred from a number that moved.
        "read_by": rec.get("read_by"),
        # WHY THE DENOMINATOR IS ABSENT, in the payload rather than as a
        # frontend guess. Only set when it is.
        "limit_unknown_why": (
            None if isinstance(limit, int) else
            "this reading carried x-ratelimit-requests-remaining without "
            "x-ratelimit-requests-limit, so requests-used has no denominator "
            "and nothing here will supply one. An earlier stored limit is not "
            "it: the Reddit and X arms are metered SEPARATELY — measured "
            "2026-09-10, Reddit's key reads a limit of 1,000,000 and X's reads "
            "100,000 — so a limit read on one arm is not this figure's "
            "denominator unless read_on matches. It fills in on the next "
            "metered call on THIS arm that carries the header."
        ),
        # WHICH PATH TOOK THIS READING, AND IT IS NOW LOAD-BEARING RATHER THAN
        # COURTESY. This said "one key meters both the Reddit and the X harvest,
        # so the figure is shared and cannot be split by endpoint". The premise
        # was inherited from `.env.example` and is false here: measured
        # 2026-09-10, this project's two RapidAPI keys are separate
        # subscriptions with separate limits (1,000,000 and 100,000), and each
        # returns 403 on the other's provider.
        #
        # So `read_on` does not merely label the reader - it identifies WHICH
        # METER the figure belongs to, and a reading is meaningless without it.
        # The gateway meters the key; there are two keys.
        #
        # ⚠ THE ONE-SLOT DEFECT IS FIXED, and this comment said otherwise for
        #   six days. It read "the store is STILL ONE SLOT ... treat this panel
        #   as one arm's reading" - true when written, and false from the moment
        #   the store was keyed by arm. `collect/usage.py` now holds one record
        #   per meter in `meters[read_on]` and `rapidapi_quota` has `meter` as
        #   its PRIMARY KEY, so a Reddit reading and an X reading no longer
        #   overwrite each other. Verified 2026-09-16: two rows, reddit and x,
        #   carrying 1,000,000 and 100,000.
        #
        #   Left as a correction rather than deleted, because the instruction it
        #   gave - "treat this panel as one arm's reading" - is the opposite of
        #   what the panel now does, and anyone who read it once should see that
        #   it was retracted rather than find it quietly gone.
        #
        # A record written before this field existed reports None, which means
        # the path is UNRECORDED and not that nothing read it.
        "read_on": rec.get("read_on"),
        "headline": (
            "RapidAPI's own quota headers, recorded by whichever metered call last "
            "saw them and cached with that timestamp - so read it as of the time "
            "shown, not as a live figure. Every Reddit and X request now records "
            "its reading, so a sweep or a failed arm no longer leaves this stale. "
            "The two arms are metered separately: check 'read_on' to see which "
            "one this reading belongs to."
        ),
    }


def _usage_summary(report) -> str:
    """One sentence a person can act on, and it must not overstate.

    The ordering is deliberate: an unwired stage or a partial window changes
    what every other number on the page MEANS, so it is said first rather than
    appended after the reassuring part.
    """
    from judge import spend_ledger

    # AN EMPTY LEDGER IS NOT A WIRING GAP, and reporting it as one is the same
    # mistake pointed the other way. With zero rows every stage is "missing", so
    # the unwired check cannot tell a broken writer from a ledger that started
    # five minutes ago and has correctly recorded nothing yet. Both readings are
    # available and only one is alarming, so the empty case is answered first.
    if report.total_rows == 0:
        return (
            "No model call has been recorded since the ledger began. Nothing has "
            "been spent that this page can see - which is the expected state "
            "before the first extraction run or Ask-box submission, and is not a "
            "guarantee about spend that happened before the ledger existed."
        )
    if report.unwired_stages:
        missing = ", ".join(
            spend_ledger.STAGE_LABELS[s].split(" —")[0] for s in report.unwired_stages
        )
        verb = "have" if len(report.unwired_stages) > 1 else "has"
        return (
            f"{missing} {verb} never recorded a call while the other stage has, so "
            f"everything below is spend from one stage only. That is a wiring gap "
            f"rather than a quiet day, and the total is a floor."
        )
    if report.daily_cap_usd is None:
        return (
            f"No daily cap is configured, so nothing is limiting spend. "
            f"${report.spent_today_usd:.4f} recorded today over "
            f"{report.calls_today} calls across both stages."
        )
    floor = "" if report.covers_whole_window else (
        " The ledger started after today did, so this is a floor rather than a total."
    )
    return (
        f"${report.spent_today_usd:.4f} of the shared ${report.daily_cap_usd:.2f} "
        f"daily cap used across both LLM stages, over {report.calls_today} calls. "
        f"${(report.remaining_usd or 0.0):.4f} left, about "
        f"{report.calls_remaining} more calls at the measured "
        f"${report.estimated_call_usd:.5f} each.{floor}"
    )
