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

import json
import logging
import os
import subprocess
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

from fastapi import Depends, FastAPI, HTTPException
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


def _conn():
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
        return psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT_SECONDS)
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
    subprocess.Popen(
        [sys.executable, str(script), mv, "--run-id", run_id],
        cwd=str(_REPO_ROOT),
        env=os.environ.copy(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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
        return {
            "run_id": run_id,
            "records": records,
            "started": True,
            "done": any(r.get("kind") == "end" for r in records),
            "source": "local file",
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
    return {"model_version_id": mv, "runs": runs}


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
        "basis": {
            "complete": report.db_readable,
            "machines": list(report.machines),
            "machine_count": len(report.machines),
            "this_machine": spend_ledger.machine(),
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
    for meter, row in (_rapidapi_meters_from_db() or {}).items():
        row = {**row, "source": "shared table"}
        held = local.get(meter)
        if held is None:
            local[meter] = row
        elif str(row.get("at") or "") > str(held.get("at") or ""):
            local[meter] = {**row, "also_held": held}
        else:
            local[meter] = {**held, "also_held": row}
    return local


def _rapidapi_meters_from_db() -> dict[str, dict] | None:
    """Every machine's latest reading, or None when the table cannot be read.

    None rather than `{}`: an unreachable database and a meter nobody has read
    are different facts, and only one of them means the panel is showing one
    laptop's view of a shared counter.
    """
    try:
        with _conn() as conn:
            rows = conn.execute(
                "select meter, quota_remaining, quota_limit, read_at, read_by, "
                "       source_run_id, machine from rapidapi_quota"
            ).fetchall()
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
        }
        for m, rem, lim, at, by, run, mach in rows
    }


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
        "limits_status": (
            f"RapidAPI sells the {arm_label} path as a monthly request quota. "
            f"This is the last quota header {arm_article} {arm_label} fetch saw; it "
            f"moves "
            "only when a fetch runs, not on a schedule. The Reddit and X arms "
            "are metered separately - this figure is this arm's alone."
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
    return {
        **base,
        "source_of_record": (
            (f"the shared `rapidapi_quota` table, meter '{read_on}', last written "
             f"from {taken_on}"
             if shared else
             f"this machine's var/rapidapi-quota.json, meters['{read_on}'], "
             f"written on {taken_on}")
            + " from RapidAPI's x-ratelimit-* headers - the provider's own "
              "number, shown with the date it was taken"
        ),
        "reading_source": source,
        "reading_machine": taken_on,
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
                "machine": other.get("machine"),
                "why_not_shown": (
                    "an older reading of the same meter. The quota only "
                    "decreases, so the newest reading is the truest one - this "
                    "is here to show the other side has also fetched, not as a "
                    "second figure to compare."
                ),
            }
        ),
        "instrumented": True,
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
        # ⚠ AND THE STORE IS STILL ONE SLOT, which is the defect this field now
        #   exposes rather than fixes. `var/rapidapi-quota.json` holds ONE
        #   record, so a Reddit reading and an X reading overwrite each other
        #   and the page shows whichever landed last under a heading that reads
        #   as "the quota". Keying the store by `read_on` is the fix; until it
        #   lands, treat this panel as one arm's reading and check this field
        #   before quoting the number.
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
