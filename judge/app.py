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

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from judge.ask import requirements
from judge.ask.profile import Assumption, RoleRequirement
from judge.ask.rank import guard_for
from judge.ask.understand import (
    InputShape,
    UnderstandingRefused,
    understand,
)
from judge.config import capabilities
from judge.extract.budget import Budget
from judge.extract.client import OpenRouterClient

app = FastAPI(
    title="Model Information Board",
    description=(
        "What engineers actually say about AI models, and which cheaper one is safe for your task."
    ),
    version="0.1.0",
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
    return {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "capabilities_loaded": len(capabilities()),
    }


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


@app.post("/ask/understand", response_model=UnderstandResponse)
def understand_task(req: UnderstandRequest) -> UnderstandResponse:
    """Q1 - the first of the two stages permitted to call a model.

    THE BUDGET IS CHECKED HERE TOO. Q1 is the second place this system spends
    money and nothing was counting it - the same defect as the unwired cap, one
    layer over. An uncapped ask box is a bill somebody discovers monthly.

    A refusal is 422 rather than 500: Q1 declining is a decision about the
    input, not a fault. Same distinction the extraction budget draws between a
    stop and a failure.
    """
    budget = Budget.from_env()
    if budget is not None:
        try:
            budget.check_before_call()
        except Exception as exc:  # BudgetExhausted
            raise HTTPException(status_code=429, detail=str(exc)) from exc

    try:
        result = understand(req.text, client=OpenRouterClient.from_env(), shape=req.shape)
    except UnderstandingRefused as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        # A forged untrusted-block marker. Refused rather than sanitised, as
        # `wrap_untrusted` does for E5.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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


# `:path` because EVERY model id contains a slash - `google/gemini-2.5-flash`,
# `anthropic/claude-opus-5`. Without it FastAPI matches only up to the first
# separator and every real model page 404s, which is what the first live check
# against a database found. A URL-encoded %2F does not help: the ASGI server
# decodes before routing, so the slash is back by the time the path is matched.
@app.get("/models/{model_version_id:path}")
def model_page(model_version_id: str) -> dict:
    """FR-23 to FR-26. The full capability list, not the evidenced part."""
    from judge.pages.model import ModelPageReader

    with _conn() as conn:
        page = ModelPageReader(conn).build(model_version_id)
        quote_ids = tuple(q for c in page.capabilities for s in c.slices for q in s.quote_ids)
        quotes = ModelPageReader(conn).quotes_for(quote_ids)

    return {
        "model_version_id": page.model_version_id,
        "summary": page.summary,
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
            }
            for qid, q in quotes.items()
        },
        # Surfaced rather than hidden: a published phrase with no evidence
        # behind it is a rendering the client should refuse.
        "unbound_phrases": [s.capability_key for s in page.unbound_phrases()],
    }


@app.get("/capabilities/{capability_key}")
def capability_page(capability_key: str) -> dict:
    """FR-25. Every model in the registry, not every model with a cell."""
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

    return {
        "key": page.key,
        "failure_mode": page.failure_mode,
        "summary": page.summary,
        "models": [
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
        ],
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
