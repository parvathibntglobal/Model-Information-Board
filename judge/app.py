"""The Ask box.

Free text in, a structured requirement profile out. Ranking against real cells
arrives once collect/ is producing evidence; until then this runs on
fixtures/hand_cells.yaml, and the UX test cannot tell the difference — which is
the point of shipping it first.

Nothing here touches the evidence pipeline. The answer path reads a
materialised view and nothing else, so a broken or stopped harvest never
degrades this surface.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

from judge.ask import requirements
from judge.ask.profile import RoleRequirement
from judge.ask.rank import guard_for
from judge.config import capabilities

app = FastAPI(
    title="Model Information Board",
    description=(
        "What engineers actually say about AI models, and which cheaper one is "
        "safe for your task."
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
