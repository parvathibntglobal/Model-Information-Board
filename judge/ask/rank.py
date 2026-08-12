"""Q5 and Q7 — the evidence gate, then ranking.

THE ORDER IS THE POINT. Capability decides who is eligible; cost only breaks
the tie between survivors. A cheap model that engineers report failing is
rejected at any price.

Four bands, and two rules about the third one that pull against each other
deliberately:

  ▸ NEVER mix "no evidence" into the ranked list. Absence of evidence rendering
    as evidence of capability is the most dangerous failure this system could
    have.

  ▸ But DO show it. Silently hiding unproven models makes the board
    conservative in a way that quietly costs money — the cheapest option is
    often the newest. "No evidence" means YOU are the test. It is an
    instruction, not a gap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from judge.ask.cost import CostEstimate
from judge.ask.profile import CapabilityNeed, RoleRequirement
from judge.curate.gate import CellStatus


class Band(str, Enum):
    RECOMMENDED = "recommended"
    ALSO_WORKS = "also_works"
    NO_EVIDENCE = "no_evidence"
    DOESNT_QUALIFY = "doesnt_qualify"


class DisqualifyReason(str, Enum):
    BELOW_BAR = "below_bar"
    MISSING_FEATURE = "missing_feature"
    CONTEXT_TOO_SMALL = "context_too_small"
    RETIRED = "retired"
    SILENT_CAPABILITY_UNPROVEN = "silent_capability_unproven"
    POSSIBLY_CHANGED = "possibly_changed"


@dataclass(frozen=True)
class CellView:
    """What the answer path sees of one cell. Read-only, from cell_current."""

    capability_key: str
    condition_bucket: str
    status: CellStatus
    direction: str
    consensus_phrase: str
    voices: int
    positive: int
    negative: int
    quote_ids: list[str]
    pessimistic_direction: str | None = None
    """For contested cells: the direction of the less flattering camp."""


@dataclass(frozen=True)
class CapabilityVerdict:
    need: CapabilityNeed
    cell: CellView | None
    passed: bool
    reason: str

    @property
    def is_unevidenced(self) -> bool:
        return self.cell is None or self.cell.status is CellStatus.INSUFFICIENT


@dataclass
class Candidate:
    model_version_id: str
    display_name: str
    cost: CostEstimate | None = None
    verdicts: list[CapabilityVerdict] = field(default_factory=list)
    band: Band = Band.NO_EVIDENCE
    disqualified_by: DisqualifyReason | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def quote_ids(self) -> list[str]:
        out: list[str] = []
        for v in self.verdicts:
            if v.cell:
                out.extend(v.cell.quote_ids)
        return out

    @property
    def weakest(self) -> CapabilityVerdict | None:
        """Named in every answer, even when everything passes comfortably.

        It is the thing that will actually break in production.
        """
        evidenced = [v for v in self.verdicts if v.cell and not v.is_unevidenced]
        if not evidenced:
            return None
        return min(evidenced, key=lambda v: v.cell.voices if v.cell else 0)

    @property
    def surviving_criticisms(self) -> list[CellView]:
        """Criticisms that did NOT disqualify it. Shown anyway.

        A minority report is worth reading before you commit.
        """
        return [
            v.cell
            for v in self.verdicts
            if v.passed and v.cell and v.cell.negative > 0
        ]


def gate(
    requirement: RoleRequirement,
    cells: dict[tuple[str, str], CellView],
    *,
    possibly_changed: bool = False,
) -> list[CapabilityVerdict]:
    """Q5 — read each required capability AT THE TASK'S CONDITION BUCKET.

    A 12-tool task looks up `tool_count:6-15`, never the model's flattering
    overall average.
    """
    verdicts: list[CapabilityVerdict] = []

    for need in requirement.capabilities:
        if possibly_changed:
            verdicts.append(
                CapabilityVerdict(
                    need,
                    None,
                    False,
                    "this model may have changed since these reports — every cell "
                    "drops to no-evidence until it is re-harvested",
                )
            )
            continue

        cell = cells.get((need.key, need.condition_bucket))

        if cell is None or cell.status is CellStatus.INSUFFICIENT:
            passed = False
            reason = f"nobody has published enough about {need.key} at {need.condition_bucket}"

        elif cell.status is CellStatus.CONTESTED:
            # Qualifies only if the PESSIMISTIC branch clears. When credible
            # engineers disagree inside one bucket, assume the worse reading.
            pessimistic = cell.pessimistic_direction or cell.direction
            passed = pessimistic == "positive"
            reason = (
                "contested, but the less favourable reading still clears"
                if passed
                else "contested, and the less favourable reading does not clear"
            )

        elif cell.direction == "negative":
            passed = False
            reason = cell.consensus_phrase

        else:
            passed = True
            reason = cell.consensus_phrase

        # A silent-failure capability cannot be cleared by absence of criticism.
        if passed and need.requires_positive_consensus:
            if cell is None or cell.positive == 0:
                passed = False
                reason = (
                    f"{need.key} fails silently — you would not find out it was "
                    "wrong, so it needs positive reports, not merely an absence "
                    "of complaints"
                )

        verdicts.append(CapabilityVerdict(need, cell, passed, reason))

    return verdicts


def band_for(
    candidate: Candidate, requirement: RoleRequirement
) -> tuple[Band, DisqualifyReason | None]:
    """Assign one candidate to a band. Called after `gate`."""
    failed = [v for v in candidate.verdicts if not v.passed]

    if not failed:
        return Band.ALSO_WORKS, None  # RECOMMENDED is decided in rank(), by cost

    unevidenced = [v for v in failed if v.is_unevidenced]

    if len(unevidenced) == len(failed):
        # Nothing is known against it — it is untested, not rejected.
        if requirement.suppress_unevidenced:
            return Band.DOESNT_QUALIFY, DisqualifyReason.SILENT_CAPABILITY_UNPROVEN
        return Band.NO_EVIDENCE, None

    silent_failures = [
        v for v in failed if not v.is_unevidenced and v.need.requires_positive_consensus
    ]
    reason = (
        DisqualifyReason.SILENT_CAPABILITY_UNPROVEN
        if silent_failures
        else DisqualifyReason.BELOW_BAR
    )
    return Band.DOESNT_QUALIFY, reason


def rank(candidates: list[Candidate]) -> list[Candidate]:
    """Q7 — order the qualified by cost, and only the qualified.

    Ties break by evidence strength, then cost, never randomly. Order must be
    stable across reloads or people stop trusting it.
    """
    qualified = [c for c in candidates if c.band is Band.ALSO_WORKS]

    qualified.sort(
        key=lambda c: (
            c.cost.per_request if c.cost else float("inf"),
            -sum(v.cell.voices for v in c.verdicts if v.cell),
            c.model_version_id,
        )
    )

    if qualified:
        qualified[0].band = Band.RECOMMENDED

    unevidenced = sorted(
        (c for c in candidates if c.band is Band.NO_EVIDENCE),
        key=lambda c: (c.cost.per_request if c.cost else float("inf"), c.model_version_id),
    )
    rejected = sorted(
        (c for c in candidates if c.band is Band.DOESNT_QUALIFY),
        key=lambda c: (c.disqualified_by or "", c.model_version_id),
    )

    return qualified + unevidenced + rejected


def guard_for(requirement: RoleRequirement) -> str | None:
    """A safety net for a borderline-but-cheap pick.

    Cheap plus a guard usually beats expensive plus a hope — but only if the
    guard matches the failure mode. A validation retry catches malformed JSON
    in seconds; it catches nothing at all when a summary quietly omits a fact.
    """
    silent = requirement.silent_failure_capabilities
    if silent:
        return (
            f"{', '.join(silent)} fails silently. Sample 2% of output into a review "
            "queue for the first two weeks; alert if the flagged rate exceeds 1%."
        )
    if requirement.hard.needs_structured_output:
        return (
            "Output is machine-parsed, so failures are loud. Add schema validation "
            "with one retry — that mitigation is why weaker evidence is acceptable here."
        )
    if requirement.hard.needs_tools:
        return "Add a tool-call validator and cap retries, so a bad argument fails fast."
    return None
