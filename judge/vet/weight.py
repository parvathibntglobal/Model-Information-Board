"""E6 step 2 — how much a claim may move a cell.

Seven factors, multiplied. Every one is stored separately, because
"why does this page say that?" must be answerable with a table of contributing
claims and their itemised weights. Auditability is the feature.

The product is capped at 0.95 (the best possible platform is GitHub at 0.95,
everything else tops out at 1.0). That cap is load-bearing arithmetic for the
publication gate — see curate/gate.py.

No language model participates in this file.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Literal

from judge.config import capabilities

EvidenceTier = Literal["A", "B", "C", "D", "E", "F"]

# ── tier: how reproducible is this? ──────────────────────────────────────
TIER_WEIGHT: dict[str, float] = {
    "A": 1.00,  # published harness/prompts, N runs, numbers; or a GitHub repro
    "B": 0.65,  # detailed first-hand build report: task, versions, conditions
    "C": 0.35,  # qualitative first-hand with conditions
    "D": 0.12,  # bare first-hand opinion
    "E": 0.04,  # hearsay, summarising someone else
    "F": 0.02,  # vendor marketing — capability FACTS only, never quality
}

# ── platform: GitHub is the failure channel, blogs the positive one ──────
PLATFORM_WEIGHT: dict[str, float] = {
    "github": 0.95,
    "blog": 0.90,
    "reddit": 0.85,
}

RELEVANCE_WEIGHT = {"central": 1.0, "passing": 0.4}
FUZZINESS_WEIGHT = {"snapshot": 1.0, "version": 0.6, "family": 0.3}

# ── recency: what goes stale, and how fast ───────────────────────────────
HALF_LIFE_DAYS_FAST = 30  # latency, cost, rate limits — these move weekly
HALF_LIFE_DAYS_MEDIUM = 120  # tool calling, instructions, extraction
HALF_LIFE_DAYS_SLOW = 180  # everything else

_FAST_DECAY = {"ops.latency_ttft"}
_MEDIUM_DECAY = {
    "tool_calling.schema_accuracy",
    "tool_calling.long_chain_reliability",
    "instruction.adherence",
    "format.structured_output",
    "extraction.faithfulness",
}

LAUNCH_WINDOW_DAYS = 21
LAUNCH_FLOOR = 0.45


@dataclass(frozen=True)
class WeightFactors:
    """The itemised breakdown. Persisted to claim_weight, one column each."""

    f_evidence: float
    f_platform: float
    f_specificity: float
    f_relevance: float
    f_recency: float
    f_launch: float
    f_fuzziness: float

    @property
    def w_final(self) -> float:
        return (
            self.f_evidence
            * self.f_platform
            * self.f_specificity
            * self.f_relevance
            * self.f_recency
            * self.f_launch
            * self.f_fuzziness
        )

    def as_row(self) -> dict[str, float]:
        return {**asdict(self), "w_final": self.w_final}

    def explain(self) -> str:
        """Human-readable, for the evidence drill-down."""
        parts = [f"{k[2:]} {v:.2f}" for k, v in asdict(self).items()]
        return " x ".join(parts) + f" = {self.w_final:.3f}"


def half_life_for(capability_key: str) -> int:
    if capability_key in _FAST_DECAY:
        return HALF_LIFE_DAYS_FAST
    if capability_key in _MEDIUM_DECAY:
        return HALF_LIFE_DAYS_MEDIUM
    return HALF_LIFE_DAYS_SLOW


def recency_factor(*, claim_date: date, as_of: date, capability_key: str) -> float:
    """Exponential decay. Half the weight per half-life."""
    age_days = max((as_of - claim_date).days, 0)
    return 0.5 ** (age_days / half_life_for(capability_key))


def launch_factor(*, claim_date: date, release_date: date | None) -> float:
    """The launch-window discount. COMPUTED ONCE, AT EXTRACTION, AND FROZEN.

    The first three weeks after a release produce the most content and the
    least signal — vendor posts, embargo reviews, hot takes from people who ran
    three prompts. Volume in that window measures hype, not truth.

    Freezing matters. If this were recomputed at aggregation time, then once
    the model turned 22 days old `days_since_release / 21` would exceed 1 for
    every claim — INCLUDING the day-three hype post — and the discount would
    silently delete itself.

    What legitimately strengthens over time is the CELL, as later un-discounted
    claims arrive. Not the hype post.
    """
    if release_date is None:
        return 1.0
    days = max((claim_date - release_date).days, 0)
    return LAUNCH_FLOOR + (1 - LAUNCH_FLOOR) * min(1.0, days / LAUNCH_WINDOW_DAYS)


def specificity_factor(
    *,
    version_named: bool,
    has_numbers: bool,
    has_conditions: bool,
    has_repro_steps: bool,
) -> float:
    """Real experience carries numbers and error strings; slop carries adjectives.

    A repro is weighted double the other signals: a two-line GitHub comment with
    reproduction steps is the most valuable document type there is, and it
    would otherwise score poorly on every naive heuristic.
    """
    score = 0.0
    if version_named:
        score += 0.2
    if has_numbers:
        score += 0.2
    if has_conditions:
        score += 0.2
    if has_repro_steps:
        score += 0.4
    return 0.3 + 0.7 * score


def compute(
    *,
    evidence_tier: EvidenceTier,
    platform: str,
    capability_key: str,
    relevance: str,
    specificity: str,
    claim_date: date,
    release_date: date | None,
    as_of: date,
    version_named: bool,
    has_numbers: bool,
    has_conditions: bool,
    has_repro_steps: bool,
    superseded_snapshot: bool = False,
    possibly_changed: bool = False,
) -> WeightFactors:
    """Compute all seven factors for one claim.

    `superseded_snapshot` and `possibly_changed` both discount recency hard:
    a quote about a model that has since been replaced, or replaced silently
    behind the same name, may describe something that no longer exists.
    """
    if capability_key not in capabilities():
        raise ValueError(
            f"unknown capability {capability_key!r} — it must exist in "
            "contract/capabilities.yaml, and every capability there must have "
            "a harvest query"
        )

    recency = recency_factor(
        claim_date=claim_date, as_of=as_of, capability_key=capability_key
    )
    if superseded_snapshot or possibly_changed:
        recency *= 0.35

    return WeightFactors(
        f_evidence=TIER_WEIGHT[evidence_tier],
        f_platform=PLATFORM_WEIGHT.get(platform, 0.5),
        f_specificity=specificity_factor(
            version_named=version_named,
            has_numbers=has_numbers,
            has_conditions=has_conditions,
            has_repro_steps=has_repro_steps,
        ),
        f_relevance=RELEVANCE_WEIGHT[relevance],
        f_recency=recency,
        f_launch=launch_factor(claim_date=claim_date, release_date=release_date),
        f_fuzziness=FUZZINESS_WEIGHT[specificity],
    )


MAX_POSSIBLE_WEIGHT = TIER_WEIGHT["A"] * PLATFORM_WEIGHT["github"] * 1.0 * 1.0 * 1.0 * 1.0 * 1.0
"""0.95 — the ceiling on a single claim.

Every other factor tops out at 1.0, so the platform base is the binding cap.
This is why `n_eff >= 3.0` in the publication gate already implies four or more
claims, and why a separate "voices >= 3" condition would be dead text.
"""


def is_recent_enough_to_matter(
    *, claim_date: date, as_of: date, capability_key: str, floor: float = 0.05
) -> bool:
    """Whether a claim still carries meaningful weight.

    Useful for pruning display lists. Confidence is allowed to go down — a
    board that only accumulates certainty is broken.
    """
    return recency_factor(
        claim_date=claim_date, as_of=as_of, capability_key=capability_key
    ) >= floor


def days_until_negligible(capability_key: str, floor: float = 0.05) -> timedelta:
    """How long until a claim about this capability decays below `floor`."""
    from math import log2

    half_life = half_life_for(capability_key)
    return timedelta(days=int(-log2(floor) * half_life))
