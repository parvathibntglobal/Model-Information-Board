"""E7 — turning counts into the sentence on the page.

TEMPLATE-ASSEMBLED FROM COUNTS. Never model-written, never a score.

There is no defensible arithmetic that turns "drops details past 50k" into 78
rather than 74. A score would also destroy the threshold and the condition that
made the quote useful in the first place — which is exactly the information a
reader needs.

Two rules this module exists to enforce:

  ▸ Silence is reported as silence, and must look nothing like criticism.
    "Nobody has discussed this" and "engineers report problems" are opposite
    states. Blurring them lets absence of evidence read as evidence of
    capability — the most dangerous failure available here.

  ▸ Conditional consensus is preserved, never flattened. "Fine under 5 tools,
    breaks above 10" is the whole answer; averaging says "mediocre", which is
    true-ish, useless, and buries the rule.
"""

from __future__ import annotations

from dataclasses import dataclass

from judge.curate.gate import (
    GENERALLY_PRAISED_AGREEMENT,
    GENERALLY_PRAISED_VOICES,
    WIDELY_PRAISED_AGREEMENT,
    WIDELY_PRAISED_VOICES,
    CellCounts,
    CellStatus,
    check_gate,
)

# Human-readable names for capability keys. Kept here rather than in the
# contract because it is presentation, and collect/ never needs it.
CAPABILITY_LABELS: dict[str, str] = {
    "instruction.adherence": "following instructions",
    "format.structured_output": "structured output",
    "tool_calling.schema_accuracy": "tool calling",
    "tool_calling.long_chain_reliability": "long tool chains",
    "context.effective_window": "long documents",
    "summarization.fidelity": "summarization",
    "extraction.faithfulness": "extraction",
    "code.editing_diff_fidelity": "code editing",
    "code.generation": "code generation",
    "reasoning.multistep": "multi-step reasoning",
    "over_refusal": "over-refusal",
    "ops.latency_ttft": "latency",
}

CONDITION_LABELS: dict[str, str] = {
    "tool_count:none": "with no tools",
    "tool_count:1-5": "with up to 5 tools",
    "tool_count:6-15": "with 6 or more tools",
    "tool_count:16+": "with 16 or more tools",
    "context_size:<8k": "on short inputs",
    "context_size:8k-32k": "on inputs up to 32k",
    "context_size:32k-128k": "on inputs up to 128k",
    "context_size:128k+": "past 128k",
    "schema_enforced:on": "with structured output enabled",
    "schema_enforced:off": "without structured output",
    # No capability is reasoning_effort-dominant yet, so these are unreachable
    # today. They are here because `condition_label` falls back to the raw
    # bucket string, and the day E2 moves `ops.latency_ttft` onto this
    # dimension the fallback would put `reasoning_effort:max` on a page.
    "reasoning_effort:off": "with thinking off",
    "reasoning_effort:low": "at low reasoning effort",
    "reasoning_effort:medium": "at medium reasoning effort",
    "reasoning_effort:high": "at high reasoning effort",
    "reasoning_effort:max": "at maximum reasoning effort",
    "reasoning_effort:auto": "with the effort chosen by the provider",
}


def label(capability_key: str) -> str:
    return CAPABILITY_LABELS.get(capability_key, capability_key)


def condition_label(bucket: str) -> str:
    return CONDITION_LABELS.get(bucket, bucket)


@dataclass(frozen=True)
class Consensus:
    """What one cell says, and what earned it."""

    phrase: str
    status: CellStatus
    voices: int
    positive: int
    negative: int
    quote_ids: list[str]
    conditional_note: str | None = None
    """Set when sibling buckets disagree — the sentence that carries the rule."""

    @property
    def is_silence(self) -> bool:
        return self.voices == 0


def describe(
    counts: CellCounts,
    *,
    capability_key: str,
    status: CellStatus,
    severity_hint: str | None = None,
) -> Consensus:
    """Build the sentence for one cell. Deterministic given the counts."""
    what = label(capability_key)

    if counts.independent_voices == 0:
        return Consensus(
            phrase=f"Nobody has publicly discussed {what}",
            status=CellStatus.INSUFFICIENT,
            voices=0,
            positive=0,
            negative=0,
            quote_ids=[],
        )

    if not check_gate(counts).passed:
        n = counts.independent_voices
        who = "One person" if n == 1 else f"{n} people"
        return Consensus(
            phrase=f"{who} mentioned {what} — not yet corroborated",
            status=CellStatus.INSUFFICIENT,
            voices=n,
            positive=counts.positive,
            negative=counts.negative,
            quote_ids=counts.quote_ids,
        )

    if status is CellStatus.CONTESTED:
        return Consensus(
            phrase=f"Mixed reports on {what}",
            status=status,
            voices=counts.independent_voices,
            positive=counts.positive,
            negative=counts.negative,
            quote_ids=counts.quote_ids,
        )

    positive_direction = counts.direction == "positive"
    strong = (
        counts.independent_voices >= WIDELY_PRAISED_VOICES
        and counts.agreement >= WIDELY_PRAISED_AGREEMENT
    )
    moderate = (
        counts.independent_voices >= GENERALLY_PRAISED_VOICES
        and counts.agreement >= GENERALLY_PRAISED_AGREEMENT
    )

    if positive_direction:
        phrase = (
            f"Widely praised for {what}"
            if strong
            else f"Generally praised for {what}"
            if moderate
            else f"Reported to work for {what}"
        )
    else:
        # `severity` earns its keep here and ONLY here — phrase selection.
        # It is never averaged, never summed, never displayed as a number.
        emphatic = severity_hint == "severe" and strong
        phrase = (
            f"Repeatedly and strongly criticised for {what}"
            if emphatic
            else f"Repeatedly criticised for {what}"
            if strong or moderate
            else f"Reported to struggle with {what}"
        )

    return Consensus(
        phrase=phrase,
        status=status,
        voices=counts.independent_voices,
        positive=counts.positive,
        negative=counts.negative,
        quote_ids=counts.quote_ids,
    )


def conditional_note(
    buckets: dict[str, Consensus], *, capability_key: str
) -> str | None:
    """The sentence that survives what a score would have destroyed.

    When sibling condition buckets of the same capability point different ways,
    that is not a contradiction to average away — it is the finding:

        "Praised for tool calling with up to 5 tools; two engineers report
         schema failures with 6 or more."

    Returns None when the buckets agree, or when only one has evidence.
    """
    published = {
        b: c
        for b, c in buckets.items()
        if c.status in (CellStatus.PUBLISHED, CellStatus.CONTESTED) and c.voices
    }
    if len(published) < 2:
        return None

    positive = {b: c for b, c in published.items() if c.positive > c.negative}
    negative = {b: c for b, c in published.items() if c.negative >= c.positive}
    if not positive or not negative:
        return None

    what = label(capability_key)
    good = ", ".join(condition_label(b) for b in sorted(positive))
    bad_bucket, bad = sorted(negative.items())[0]
    n = bad.negative
    who = "one engineer reports" if n == 1 else f"{n} engineers report"

    return (
        f"Praised for {what} {good}; "
        f"{who} problems {condition_label(bad_bucket)}."
    )


def reported_context_phrase(
    *, advertised: int | None, reported_low: int | None, reported_high: int | None
) -> str | None:
    """Advertised versus what practitioners actually report.

    A range with the quotes behind it, never a fitted curve — and the answer
    path matches against the REPORTED limit, never the advertised one.
    """
    if advertised is None or reported_low is None:
        return None

    def fmt(n: int) -> str:
        return f"{n // 1000}k" if n < 1_000_000 else f"{n / 1_000_000:g}M"

    if reported_high and reported_high != reported_low:
        window = f"~{fmt(reported_low)}-{fmt(reported_high)}"
    else:
        window = f"~{fmt(reported_low)}"

    return (
        f"Advertised {advertised:,} - practitioners report degradation past {window}"
    )
