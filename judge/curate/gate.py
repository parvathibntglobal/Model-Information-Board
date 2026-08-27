"""E7 — counting voices and the publication gate.

Pure code. No language model, and no score is displayed.

THE ARITHMETIC MATTERS. A single claim cannot exceed w = 0.95 (the platform
base caps it), so `n_eff >= 3.0` already demands four or more claims, and five
or six at realistic weights. A separate `voices >= 3` condition would be dead
text — which is why it is not in the gate.

The author cap is conditional for the same reason. It exists to stop one loud
account carrying a cell. Below five voices that risk is already bounded by the
two-platform rule; a flat 20% cap would need five exactly-equal authors, and
real weights are never equal, so it would only ever permit cells you rarely
have.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

N_EFF_MINIMUM = 3.0
PLATFORM_MINIMUM = 2
AUTHOR_CAP_BELOW_FIVE_VOICES = 0.50
AUTHOR_CAP_AT_FIVE_PLUS = 0.20
VOICES_FOR_TIGHTER_CAP = 5

WIDELY_PRAISED_VOICES = 5
WIDELY_PRAISED_AGREEMENT = 0.80
GENERALLY_PRAISED_VOICES = 3
GENERALLY_PRAISED_AGREEMENT = 0.70


class CellStatus(StrEnum):
    PUBLISHED = "published"
    CONTESTED = "contested"
    INSUFFICIENT = "insufficient"


class GateFailure(StrEnum):
    NOT_ENOUGH_WEIGHT = "not_enough_weight"
    ONE_PLATFORM_ONLY = "one_platform_only"
    SINGLE_AUTHOR_DOMINATES = "single_author_dominates"


@dataclass(frozen=True)
class WeightedClaim:
    """What curation sees. Already verified, already vetted, already weighted."""

    claim_id: str
    voice_id: str
    """The AUTHOR IDENTITY CLUSTER, not the account.

    One engineer who files a GitHub issue and posts the same finding on Reddit
    is ONE voice — which is precisely the condition the two-platform rule
    exists to demand. Clustering happens in collect/; unresolved identities
    stay separate, so voice counts are an upper bound.
    """
    platform: str
    weight: float
    polarity: str
    severity: str | None
    quote_id: str
    created_at: date
    condition_bucket: str


@dataclass
class CellCounts:
    """Everything the gate and the phrase need, all of it counted."""

    n_eff: float = 0.0
    independent_voices: int = 0
    platform_count: int = 0
    positive: int = 0
    negative: int = 0
    max_author_share: float = 0.0
    quote_ids: list[str] = field(default_factory=list)
    freshest_at: date | None = None
    median_age_days: int | None = None

    @property
    def agreement(self) -> float:
        """Share of voices pointing the same way as the majority."""
        total = self.positive + self.negative
        if not total:
            return 0.0
        return max(self.positive, self.negative) / total

    @property
    def direction(self) -> str:
        return "positive" if self.positive >= self.negative else "negative"


def count(claims: list[WeightedClaim], *, as_of: date | None = None) -> CellCounts:
    """Count PEOPLE, not posts.

    A voice contributes once, at its highest-weighted claim. Someone who posts
    five times about the same capability is still one person, and letting the
    five sum would let one enthusiast clear the gate alone.
    """
    if not claims:
        return CellCounts()

    as_of = as_of or datetime.now().date()

    by_voice: dict[str, WeightedClaim] = {}
    for c in claims:
        best = by_voice.get(c.voice_id)
        if best is None or c.weight > best.weight:
            by_voice[c.voice_id] = c

    representatives = list(by_voice.values())
    n_eff = sum(c.weight for c in representatives)

    per_author: dict[str, float] = defaultdict(float)
    for c in representatives:
        per_author[c.voice_id] += c.weight

    ages = sorted((as_of - c.created_at).days for c in claims)
    median_age = ages[len(ages) // 2] if ages else None

    return CellCounts(
        n_eff=n_eff,
        independent_voices=len(representatives),
        platform_count=len({c.platform for c in representatives}),
        positive=sum(1 for c in representatives if c.polarity == "positive"),
        negative=sum(1 for c in representatives if c.polarity == "negative"),
        max_author_share=(max(per_author.values()) / n_eff) if n_eff else 0.0,
        quote_ids=[c.quote_id for c in sorted(claims, key=lambda c: -c.weight)],
        freshest_at=max(c.created_at for c in claims),
        median_age_days=median_age,
    )


@dataclass(frozen=True)
class GateResult:
    passed: bool
    failures: tuple[GateFailure, ...] = ()

    def explain(self) -> str:
        if self.passed:
            return "clears the publication gate"
        return "; ".join(_GATE_EXPLANATIONS[f] for f in self.failures)


_GATE_EXPLANATIONS = {
    GateFailure.NOT_ENOUGH_WEIGHT: (
        f"weighted evidence below {N_EFF_MINIMUM} — needs roughly four or more "
        "solid claims, since no single claim exceeds 0.95"
    ),
    GateFailure.ONE_PLATFORM_ONLY: (
        "all evidence comes from one platform; a published claim must not rest "
        "on a single source of truth"
    ),
    GateFailure.SINGLE_AUTHOR_DOMINATES: (
        "one voice carries too much of the total weight"
    ),
}


def author_cap_for(voices: int) -> float:
    return (
        AUTHOR_CAP_AT_FIVE_PLUS
        if voices >= VOICES_FOR_TIGHTER_CAP
        else AUTHOR_CAP_BELOW_FIVE_VOICES
    )


def check_gate(counts: CellCounts) -> GateResult:
    """Publish a consensus phrase only if all three conditions hold."""
    failures: list[GateFailure] = []

    if counts.n_eff < N_EFF_MINIMUM:
        failures.append(GateFailure.NOT_ENOUGH_WEIGHT)
    if counts.platform_count < PLATFORM_MINIMUM:
        failures.append(GateFailure.ONE_PLATFORM_ONLY)
    if counts.max_author_share > author_cap_for(counts.independent_voices):
        failures.append(GateFailure.SINGLE_AUTHOR_DOMINATES)

    return GateResult(passed=not failures, failures=tuple(failures))


def classify(counts: CellCounts, *, dissent_threshold: float = 0.70) -> CellStatus:
    """Published, contested, or not enough to say anything.

    `contested` is reached when credible voices disagree INSIDE the same
    condition bucket — genuine disagreement, not a condition mismatch. With no
    first-party testing, contested is where it honestly stays: both sides are
    shown and no resolution is attempted.

    Contested rate is tracked and deliberately NOT minimised. A suspiciously
    low rate means real disagreement is being hidden.
    """
    if not check_gate(counts).passed:
        return CellStatus.INSUFFICIENT
    # NO SENTIMENT IS NOT DISAGREEMENT. A cell whose voices are all neutral (or
    # that otherwise has zero positive and zero negative) clears the weight gate
    # but has no direction to publish, and `agreement` is 0/0 = 0.0 — which the
    # dissent check below would misread as maximal disagreement and mark
    # CONTESTED. It is discussed-without-sentiment, so it stays INSUFFICIENT:
    # there is nothing to say as praise or criticism, and nothing is in dispute.
    if counts.positive + counts.negative == 0:
        return CellStatus.INSUFFICIENT
    if counts.agreement < dissent_threshold:
        return CellStatus.CONTESTED
    return CellStatus.PUBLISHED
