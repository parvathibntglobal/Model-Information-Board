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

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Literal, NamedTuple

from judge.config import capabilities

EvidenceTier = Literal["A", "B", "C", "D", "E", "F"]

# ═══════════════════════════════════════════════════════════════════════════
# A WEIGHTING OR COUNTING INPUT MAY NOT HAVE A SILENT DEFAULT
# ═══════════════════════════════════════════════════════════════════════════
#
# **`f_specificity` held one value, 0.580, across every row `claim_weight` has
# ever contained.** Not a narrow range - one value, `SELECT DISTINCT` returns a
# single row. Every weight this system has computed came from a factor that had
# never varied, because three of its four inputs were dead: `version_named` and
# `has_conditions` arrived as a dataclass default and `has_numbers` still does.
# Only `has_repro_steps` was live, and it was False on all four stored claims.
#
# That is the argument for this section. A silent default in a weighting factor
# is indistinguishable from a measurement: the column has a value, the
# breakdown renders, `explain()` prints seven numbers, and one of them is a
# constant nobody chose.
#
# Ruled 2026-08-21: EITHER SOMETHING WRITES IT, OR `compute()` REFUSES AND THE
# ABSENCE IS VISIBLE. This is rule 6 applied to the machinery rather than to the
# data - a missing input is never silently converted into a definite one.
#
# `compute()` takes 12 required inputs and 5 are supplied by nothing that runs.
# The refusal names WHICH and WHAT SHOULD WRITE IT, because a refusal that sends
# somebody to this file when the gap is in an adapter costs more than it saves.


class _Unsupplied:
    """Not a value. Nothing wrote this.

    `__bool__` raises on purpose. The whole failure being fixed here is a
    `False` that meant "nobody measured", so this must not be quietly usable in
    a boolean position anywhere downstream.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSUPPLIED"

    def __bool__(self) -> bool:
        raise TypeError(
            "UNSUPPLIED is not a value and cannot be tested for truth. Something "
            "read a weighting input that nothing wrote - see judge/vet/weight.py"
        )


UNSUPPLIED = _Unsupplied()
"""Pass this rather than a plausible value when nothing supplied one."""

#: The two failures are different and the refusal must say which.
#:
#:   WRONG_WRITER   something writes it, and what it writes is a constant. The
#:                  value is present, defensible-looking, and the same every
#:                  time. `evidence_tier` is this: `judge/pipeline.py` passes a
#:                  module-level literal to every claim in the corpus.
#:
#:   NOT_CARRIED    the `document` table has the value and nothing builds the
#:                  object that would carry it here. `DocumentFacts` has exactly
#:                  one constructor in the repository and it is
#:                  `tests/test_pipeline_db.py`; `run_all` takes `facts` as a
#:                  parameter and the nightly job that would populate it does
#:                  not exist. Fixing this is an ingest/plumbing job, NOT a
#:                  change to this file.
WRONG_WRITER = "wrong writer"
NOT_CARRIED = "not carried"


class _Gap(NamedTuple):
    kind: str
    writer: str
    fix: str


#: Per input: which failure, who is responsible, and what closing it means.
#: Read by the refusal so the message is actionable rather than merely correct.
INPUT_GAPS: dict[str, _Gap] = {
    "evidence_tier": _Gap(
        kind=WRONG_WRITER,
        writer=(
            "contract/harvest.yaml evidence_tier_rules, via "
            "weight.evidence_tier_for(speaking, has_repro_steps=, has_numbers=)"
        ),
        fix=(
            "the ladder is missing a key for this `speaking` value or for this "
            "combination of the two booleans, the contract block is absent, or "
            "one of the booleans was never written. It was a module literal "
            '`"D"` until 2026-08-21 - applied to every claim in the corpus, '
            "including three that quote a launch post and should be F, a 6x "
            "over-weight - and keyed on `speaking` alone until 2026-08-30, "
            "which put B and C out of reach of any corpus. Add the key rather "
            "than restoring a default"
        ),
    ),
    "platform": _Gap(
        kind=NOT_CARRIED,
        writer="document.source, via judge/pipeline.py DocumentFacts",
        fix="build DocumentFacts from the document table - nothing does today",
    ),
    "claim_date": _Gap(
        kind=NOT_CARRIED,
        writer="document.created_at, via judge/pipeline.py DocumentFacts",
        fix="build DocumentFacts from the document table - nothing does today",
    ),
    "has_numbers": _Gap(
        kind=NOT_CARRIED,
        writer="document.has_numbers, written by collect/triage/",
        fix=(
            "build DocumentFacts from the document table. The column IS "
            "populated - True on 6 of 7 non-NULL rows - so this one is carriage "
            "and not measurement. It may NOT be derived from the claim: rule 2 "
            "forbids weighting on the extractor's own boolean. Since 2026-08-30 "
            "this column has a SECOND job - it vetoes a tier promotion that "
            "`claim.has_numbers` proposes, and it can only veto, never confirm "
            "(collect/triage/specificity.py). That is the caller's rule, not "
            "this factor's: `f_specificity` still reads the counted column "
            "alone"
        ),
    ),
    "has_conditions": _Gap(
        kind=NOT_CARRIED,
        writer="document.has_conditions, written by collect/triage/",
        fix=(
            "build DocumentFacts from the document table - AND note the column "
            "is False on all 7 populated rows and NULL on 57, so carrying it "
            "changes nothing until something sets it True. It may NOT be "
            "derived from claim.conditions: an absent condition is not a stated "
            "absence (rule 6)"
        ),
    ),
    "version_named": _Gap(
        kind=NOT_CARRIED,
        writer="derived from claim.model_ref.specificity in judge/pipeline.py",
        fix="already closed 2026-08-21 - this entry exists so a revert is named",
    ),
    "relevance": _Gap(
        kind=NOT_CARRIED,
        writer="claim.relevance, from the extractor",
        fix="supplied today",
    ),
    "specificity": _Gap(
        kind=NOT_CARRIED,
        writer="claim.model_ref.specificity, from the extractor",
        fix="supplied today",
    ),
    "capability_key": _Gap(
        kind=NOT_CARRIED,
        writer="claim.capability, from the extractor",
        fix="supplied today",
    ),
    "has_repro_steps": _Gap(
        kind=NOT_CARRIED,
        writer="claim.has_repro_steps, from the extractor",
        fix="supplied today",
    ),
}


class UnsuppliedWeightInput(Exception):
    """A weighting input nothing wrote. Names the input, the writer and the fix.

    Raised rather than defaulted, per the 2026-08-21 ruling. `run_all` catches
    per thread and logs a refusal, so a batch reports which input is missing
    instead of producing weights from constants.
    """

    def __init__(self, missing: Sequence[str]) -> None:
        self.missing = tuple(missing)
        lines = [
            f"refusing to weight: {len(self.missing)} input(s) were UNSUPPLIED. "
            "A weighting input may not have a silent default (ruled 2026-08-21)."
        ]
        for name in self.missing:
            gap = INPUT_GAPS.get(name)
            if gap is None:
                lines.append(f"  {name}: UNSUPPLIED, and no writer is recorded for it")
                continue
            lines.append(f"  {name}  [{gap.kind}]")
            lines.append(f"      should be written by: {gap.writer}")
            lines.append(f"      to close it: {gap.fix}")
        lines.append(
            "  THE GAP IS NOT IN THIS FILE. Every entry above names the module "
            "that should supply the value; weight.py only refuses to invent one."
        )
        super().__init__("\n".join(lines))


# ── tier: how reproducible is this? ──────────────────────────────────────
TIER_WEIGHT: dict[str, float] = {
    "A": 1.00,  # published harness/prompts, N runs, numbers; or a GitHub repro
    "B": 0.65,  # detailed first-hand build report: task, versions, conditions
    "C": 0.35,  # qualitative first-hand with conditions
    "D": 0.12,  # bare first-hand opinion
    "E": 0.04,  # hearsay, summarising someone else
    "F": 0.02,  # vendor marketing — capability FACTS only, never quality
}

class TierVerdict(NamedTuple):
    """A tier, plus the signals that could not be confirmed on the way to it.

    TWO RETURN VALUES BECAUSE RULE 6 ASKS FOR TWO. `tier` is what the weight
    uses. `unconfirmed` is the caveat: which promotion signals were absent
    rather than false, so a run can report "n claims stayed at D because
    nothing had counted their numbers" instead of publishing a D that reads as
    a judgement. A single return value would make those two indistinguishable
    in exactly the way rule 4 forbids one stage later.
    """

    tier: EvidenceTier | _Unsupplied
    unconfirmed: tuple[str, ...] = ()


def promotable_numbers(
    claim_has_numbers: bool | None | _Unsupplied,
    document_has_numbers: bool | None | _Unsupplied,
) -> bool | _Unsupplied:
    """May `has_numbers` lift this claim's tier? The falsifier, applied once.

    `claim.has_numbers` is the extractor's self-report and reaches `w_final`
    with no code check. `document.has_numbers` is the same question asked of the
    same text by code, and `collect/triage/specificity.py` fixes its standing:

        document False  ->  the claim's `true` is a fabrication. There are no
                            numbers in the document for the quote to contain.
        document True   ->  says NOTHING about whether THIS quote holds one.

    So this is an AND read as a veto, never as a confirmation. Code can block a
    promotion; code never grants one. Reading the True case as confirmation
    would launder an unverified extractor boolean into a verified one, which is
    worse than not checking at all - and it is one of the two reasons the ladder
    caps at B.

    ABSENT IS NEITHER. A NULL on either side returns UNSUPPLIED - the documents
    written before `collect/triage/` existed carry NULL in all six columns, and
    coalescing that either way turns "nobody counted" into a decision.
    `evidence_tier_for` then withholds the promotion AND names the signal, which
    is rule 6's "say so" rather than rule 6's silent exclusion.
    """
    if (
        claim_has_numbers is UNSUPPLIED
        or document_has_numbers is UNSUPPLIED
        or claim_has_numbers is None
        or document_has_numbers is None
    ):
        return UNSUPPLIED
    return bool(claim_has_numbers) and bool(document_has_numbers)


def evidence_tier_for(
    speaking: str,
    *,
    has_repro_steps: bool | None | _Unsupplied,
    has_numbers: bool | None | _Unsupplied,
) -> TierVerdict:
    """(speaking, repro steps, numbers) -> a tier, from `contract/harvest.yaml`.

    NOT A CONSTANT IN THIS FILE. It is a ruling about what a vendor's own words
    are worth and about what separates a build report from an opinion, and rule
    5 puts that in versioned YAML - see `evidence_tier_rules` there.

    KEYED ON THREE INPUTS SINCE 2026-08-30, AND THAT IS THE WHOLE CHANGE.
    `speaking` alone answered WHOSE claim it is; `TIER_WEIGHT`'s glosses grade
    HOW CHECKABLE it is. Keying one on the other made B and C unreachable by
    construction - 0 of 197 stored claims reached them - because an engineer
    with a published harness and an engineer with a hunch were both
    `own-experience`. Both booleans were already on the claim, feeding
    `f_specificity` at 1.6x and the tier at nothing.

    ⚠ `has_numbers` HERE IS THE FALSIFIED BOOLEAN, not the extractor's raw one.
    Callers pass `promotable_numbers(claim.has_numbers, document.has_numbers)` -
    the self-report vetoed by the code-side count. It is a separate function
    rather than an argument pair here so the two callers (`judge/pipeline.py`,
    `judge/reweight.py`) share one definition of the veto instead of writing it
    twice and drifting.

    ⚠ AN ABSENT BOOLEAN WITHHOLDS A PROMOTION. IT DOES NOT REFUSE THE CLAIM.
    This is the one place the 2026-08-21 "refuse rather than default" ruling is
    deliberately not applied, and the reason is rule 8. Refusing would make
    `compute()` raise and the claim would be DROPPED - a wrong gate, whose false
    positives are invisible because the document simply is not there, and an
    absence we caused reads as one we found. Withholding leaves the claim on the
    board at the tier it already had, which is a wrong WEIGHT: visible,
    rankable, and the evidence that decides whether the rung was right.

    Not silent, though. The absent signal is named in `TierVerdict.unconfirmed`
    and the callers count it, so "stayed at D" and "could not be promoted from D"
    stay distinguishable - rule 4 one stage before the page.

    STILL RETURNS `UNSUPPLIED` when `speaking` itself is unmapped or the contract
    block is absent, so `compute()` refuses and names the gap. That case is a
    contract that does not price a value the extractor can emit, and inventing a
    tier for it is the exact defect the 2026-08-21 ruling was written for:
    `DEFAULT_EVIDENCE_TIER` was a literal "D" applied to every claim in the
    corpus, including three that quote a launch post.
    """
    from judge.config import evidence_tier_rules

    rung = evidence_tier_rules().get(speaking)

    # A flat tier - `relayed-from-elsewhere` and `vendor-about-own-product`.
    # Neither has rungs, so neither reads the booleans: numbers in a relay are
    # still someone else's numbers, and numbers in a launch post are still the
    # vendor's. Returning before the booleans are examined is deliberate -
    # reporting a missing signal nothing would have read is a caveat about
    # nothing, and it would put a vendor claim in the "could not be promoted"
    # count when no promotion was ever on offer.
    if isinstance(rung, str):
        return TierVerdict(rung if rung in TIER_WEIGHT else UNSUPPLIED)  # type: ignore[arg-type]

    if not isinstance(rung, dict):
        return TierVerdict(UNSUPPLIED)

    unconfirmed: list[str] = []
    signals = 0
    for name, value in (("has_repro_steps", has_repro_steps), ("has_numbers", has_numbers)):
        if value is UNSUPPLIED or value is None:
            unconfirmed.append(name)
            continue
        signals += int(bool(value))

    key = ("neither", "one_of_the_two", "repro_steps_and_numbers")[signals]
    tier = rung.get(key)
    if tier not in TIER_WEIGHT:
        return TierVerdict(UNSUPPLIED, tuple(unconfirmed))
    return TierVerdict(tier, tuple(unconfirmed))  # type: ignore[arg-type]


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
    evidence_tier: EvidenceTier | _Unsupplied,
    platform: str | _Unsupplied,
    capability_key: str | _Unsupplied,
    relevance: str | _Unsupplied,
    specificity: str | _Unsupplied,
    claim_date: date | _Unsupplied,
    release_date: date | None,
    as_of: date,
    version_named: bool | _Unsupplied,
    has_numbers: bool | _Unsupplied,
    has_conditions: bool | _Unsupplied,
    has_repro_steps: bool | _Unsupplied,
    superseded_snapshot: bool = False,
    possibly_changed: bool = False,
) -> WeightFactors:
    """Compute all seven factors for one claim.

    `superseded_snapshot` and `possibly_changed` both discount recency hard:
    a quote about a model that has since been replaced, or replaced silently
    behind the same name, may describe something that no longer exists.
    """
    # REFUSE BEFORE COMPUTING ANYTHING. Ruled 2026-08-21: a weighting input may
    # not have a silent default. The check is first so no factor is derived from
    # a constant before the caller learns which input is missing.
    missing = [
        name
        for name, value in (
            ("evidence_tier", evidence_tier),
            ("platform", platform),
            ("capability_key", capability_key),
            ("relevance", relevance),
            ("specificity", specificity),
            ("claim_date", claim_date),
            ("version_named", version_named),
            ("has_numbers", has_numbers),
            ("has_conditions", has_conditions),
            ("has_repro_steps", has_repro_steps),
        )
        if value is UNSUPPLIED
    ]
    if missing:
        raise UnsuppliedWeightInput(missing)

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
