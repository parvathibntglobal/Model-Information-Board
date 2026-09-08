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
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import NamedTuple

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from judge import login
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


app = FastAPI(
    title="Model Information Board",
    description=(
        "What engineers actually say about AI models, and which cheaper one is safe for your task."
    ),
    version="0.1.0",
    # EVERY ROUTE, rather than a decorator per handler. An app-wide dependency
    # cannot be forgotten on the next endpoint somebody adds, and forgetting one
    # is the whole failure mode here - the gap this closes was not a weak check,
    # it was no check anywhere. `/health` opts back out explicitly below, which
    # is a visible exception instead of an invisible omission.
    dependencies=[Depends(require_token)],
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
    """
    import os

    import psycopg

    from judge.store.claims import CONNECT_TIMEOUT_SECONDS

    # Same variable and the same refusal as `judge.store.claims.transaction`.
    # A default that quietly reaches localhost is how a read surface ends up
    # serving a database nobody meant to expose.
    url = os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(
            status_code=503,
            detail=(
                "no database configured, so the board cannot be read. This is "
                "not the same as a board with nothing on it."
            ),
        )
    return psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT_SECONDS)


@app.get("/models")
def model_roster(limit: int = DEFAULT_PAGE, offset: int = 0) -> dict:
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

    page = _page(roster.models, limit=limit, offset=offset)
    return {
        # `count` is the FULL registry size and always was. A page that reported
        # its own length here would answer "how many models are there" with "how
        # many did you ask for", which is rule 7 with the denominator swapped.
        "count": len(roster.models),
        "priced_at": roster.priced_at,
        "summary": roster.summary,
        "page": page.meta,
        "models": page.items,
    }


# `:path` because EVERY model id contains a slash - `google/gemini-2.5-flash`,
# `anthropic/claude-opus-5`. Without it FastAPI matches only up to the first
# separator and every real model page 404s, which is what the first live check
# against a database found. A URL-encoded %2F does not help: the ASGI server
# decodes before routing, so the slash is back by the time the path is matched.
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
    return {"run_id": run_id, "model_version_id": mv}


@app.get("/fetch/log")
def fetch_log(run_id: str) -> dict:
    """The per-stage progress of a fetch, as the subprocess has written it so far.

    Polled by the model page. `done` flips true when the run writes its end
    record — that is how the UI knows to stop polling. An absent file means the
    run has not written its first line yet, which is not an error.
    """
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise HTTPException(status_code=422, detail="bad run id")
    path = _FETCH_DIR / f"{run_id}.jsonl"
    if not path.exists():
        return {"run_id": run_id, "records": [], "done": False, "started": False}
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
    }


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
            })
    runs.sort(key=lambda r: r["started_at"], reverse=True)
    return {"model_version_id": mv, "runs": runs}


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
    for call in spend_ledger.read_all():
        by_model_total[call.model] = by_model_total.get(call.model, 0.0) + call.usd

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
        "rapidapi": _rapidapi_quota(),
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


def _rapidapi_quota() -> dict:
    """The other paid API - Reddit via RapidAPI, billed as a REQUEST quota.

    Shows the latest quota HEADER reading a Reddit fetch persisted
    (`var/rapidapi-quota.json`), with WHEN it was read. RapidAPI cannot share an
    axis with the LLM cap: one is dollars per day against a limit we set, the
    other is requests against a limit somebody sells us. Same page, separate tab.

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
    base = {
        "unit": "requests",
        "limits_status": (
            "RapidAPI sells the Reddit path as a monthly request quota. This is "
            "the last quota header a Reddit fetch saw; it moves only when a fetch "
            "runs, not on a schedule."
        ),
        "source_of_record": (
            "var/rapidapi-quota.json, written by a Reddit fetch from RapidAPI's "
            "x-ratelimit-* headers - the provider's own number, cached with its date"
        ),
    }
    store = _REPO_ROOT / "var" / "rapidapi-quota.json"
    try:
        rec = json.loads(store.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {
            **base,
            "instrumented": False,
            "headline": (
                "No quota reading recorded yet. RapidAPI's usage arrives in "
                "response headers, so this fills in after the first Reddit fetch "
                "and updates on each one - it is not live."
            ),
        }
    limit = rec.get("quota_limit")
    remaining = rec.get("quota_remaining")
    used = limit - remaining if isinstance(limit, int) and isinstance(remaining, int) else None
    return {
        **base,
        "instrumented": True,
        "quota_limit": limit,
        "quota_remaining": remaining,
        "requests_used": used,
        "as_of": rec.get("at"),
        "headline": (
            "RapidAPI's own quota headers, read on the last Reddit fetch and "
            "cached with that timestamp - so read it as of the time shown, not "
            "as a live figure."
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
