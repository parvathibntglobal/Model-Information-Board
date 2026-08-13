"""The structured shapes the answer path works in.

Q1 produces a TaskProfile. Q2 splits it into Roles. Q3 gives each Role a
RoleRequirement. Q4 onward consume those and never mutate them.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ErrorCost = Literal["experimental", "internal", "customer-facing", "irreversible"]
FailureMode = Literal["silent", "loud"]


class Assumption(BaseModel):
    """Something the user did not say, that we guessed.

    Guessing silently is the failure mode of every "AI picks for you" product.
    Guess, show the guess, let one click fix it — so every one of these renders
    as an editable field, and editing one re-runs Q3 through Q7.
    """

    field: str
    value: Any
    why: str = Field(description="what in the text, or what default, produced this")
    editable: bool = True

    def render(self) -> str:
        return f"{self.field}: {self.value}"


class CapabilityNeed(BaseModel):
    """One capability this role is gated on."""

    key: str
    triggered_by: str = Field(description="the phrase in the task text that raised it")
    failure_mode: FailureMode
    condition_bucket: str = Field(
        description="the slice to read the cell at, e.g. tool_count:6-15"
    )

    @property
    def requires_positive_consensus(self) -> bool:
        """Silent failures cannot be cleared by absence of criticism.

        A summary quietly missing a critical fact produces no error and no
        alert — wrong data enters the system looking correct and stays. So
        "nobody complained" is not evidence; only positive reports are.
        """
        return self.failure_mode == "silent"


class HardConstraints(BaseModel):
    """Binary filters for Q4. No partial credit, no scoring."""

    needs_tools: bool = False
    tool_count: int | None = None
    needs_structured_output: bool = False
    needs_vision: bool = False
    min_context_tokens: int | None = Field(
        default=None,
        description="matched against REPORTED effective context, never advertised",
    )
    max_latency_ms: int | None = None
    regions: list[str] = Field(default_factory=list)


class RoleRequirement(BaseModel):
    """What one role needs, and how strong the evidence must be."""

    capabilities: list[CapabilityNeed]
    hard: HardConstraints
    complexity_tier: int = Field(ge=1, le=5)
    error_cost: ErrorCost
    cost_dominates: bool = False

    dropped_constraints: list[str] = Field(
        default_factory=list,
        description=(
            "Requirements the task does NOT have, named explicitly. Every one "
            "widens the cheap end of the field, and carrying one you do not "
            "need is the most common way to overpay."
        ),
    )
    assumptions: list[Assumption] = Field(default_factory=list)

    @property
    def silent_failure_capabilities(self) -> list[str]:
        return [c.key for c in self.capabilities if c.requires_positive_consensus]

    @property
    def suppress_unevidenced(self) -> bool:
        """At `irreversible` — writes, sends, payments, deletions — unevidenced
        candidates are suppressed entirely rather than shown, and the honest
        answer is often "don't change this one".
        """
        return self.error_cost == "irreversible"


class Role(BaseModel):
    """One unit of work inside a task or product brief."""

    name: str
    runs_per_request: int = Field(
        default=1,
        ge=1,
        description=(
            "How often this role executes per user request. Multiplies every "
            "saving — and is multiplied exactly once, in Q6."
        ),
    )
    dependents: list[str] = Field(
        default_factory=list,
        description="roles downstream of this one; feeding many is a reason not to touch it",
    )
    requirement: RoleRequirement | None = None

    @property
    def is_orchestrator(self) -> bool:
        """Never downgrade one without a warning.

        Two conditions, and both matter. It runs ONCE, so the saving is tiny
        even at frontier prices. And something DEPENDS on it, so degrading its
        planning poisons every role beneath — one dependent is enough for that,
        which is why the threshold is one and not two.
        """
        return bool(self.dependents) and self.runs_per_request == 1


class TaskProfile(BaseModel):
    """The whole ask, after Q1 and Q2."""

    raw_text: str
    roles: list[Role]

    requests_per_month: int | None = Field(
        default=None,
        description=(
            "THE VOLUME INVARIANT: the user always states REQUESTS. Role volume "
            "is always derived. Q6 multiplies by runs_per_request; nothing else may."
        ),
    )

    @model_validator(mode="after")
    def _roles_are_named_uniquely(self) -> TaskProfile:
        names = [r.name for r in self.roles]
        if len(names) != len(set(names)):
            dupes = sorted({n for n in names if names.count(n) > 1})
            raise ValueError(f"duplicate role names: {dupes}")
        return self

    def ordered_by_leverage(self, monthly_saving: dict[str, float]) -> list[Role]:
        """Roles in the order advice should be given.

        Ordered by how much moving each one actually saves, never by how
        important the role sounds. A page-summariser running 10x per request is
        worth ten times what the synthesiser running once is worth — and that
        multiplier is invisible unless the brief was decomposed first.
        """
        return sorted(
            self.roles,
            key=lambda r: monthly_saving.get(r.name, 0.0),
            reverse=True,
        )
