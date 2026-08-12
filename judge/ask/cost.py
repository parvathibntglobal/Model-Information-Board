"""Q6 — what this actually costs YOU, not the sticker price.

Two corrections regularly flip the ordering, and both are why per-token price
is the wrong number to rank on:

  ▸ OUTPUT VERBOSITY. Models differ several-fold in output length for the same
    task. A model cheaper per token that writes three paragraphs where another
    writes a label is more expensive.

  ▸ RETRY RATE. A model with reported schema failures costs meaningfully more
    than sticker once the second attempt is counted.

Both are ESTIMATES until telemetry exists. They are shown as estimates, not
hidden — see `CostEstimate.caveats`.

THE VOLUME INVARIANT: the user always states REQUESTS; role volume is always
derived. The multiplication by runs_per_request happens exactly once, here.
A role-scoped volume arriving at this function would report a 10x role at 100x
cost and invert the very ordering Q2 exists to establish.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_VERBOSITY = 1.0
DEFAULT_RETRY_RATE = 0.0


@dataclass(frozen=True)
class Pricing:
    """Per 1M tokens, from the registry. Measured, not estimated."""

    price_in: float
    price_out: float
    price_cached_read: float | None = None
    batch_discount: float | None = None


@dataclass(frozen=True)
class Workload:
    """The shape of one call, plus how often it happens."""

    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    runs_per_request: int = 1
    requests_per_month: int | None = None
    batch_eligible: bool = False

    def __post_init__(self) -> None:
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached_input_tokens cannot exceed input_tokens")


@dataclass(frozen=True)
class CostEstimate:
    per_call: float
    per_request: float
    monthly: float | None
    caveats: tuple[str, ...] = field(default_factory=tuple)
    """Stated on the page. An estimate presented as a measurement is a lie."""

    def cheaper_than(self, other: CostEstimate) -> float | None:
        """How many times cheaper this is. None when the comparison is degenerate."""
        if self.per_request <= 0:
            return None
        return other.per_request / self.per_request

    def format_multiple(self, other: CostEstimate) -> str | None:
        m = self.cheaper_than(other)
        if m is None or m < 1.05:
            return None
        return f"{m:.0f}x cheaper" if m >= 2 else f"{m:.1f}x cheaper"


def estimate(
    *,
    pricing: Pricing,
    workload: Workload,
    verbosity_multiplier: float | None = None,
    expected_retry_rate: float | None = None,
) -> CostEstimate:
    """Cost for this workload on this model.

    Args:
        verbosity_multiplier: how much longer this model's output runs for the
            same task. None means unknown, and the estimate says so.
        expected_retry_rate: fraction of calls needing a second attempt, from
            reported schema-failure evidence. None means unknown.
    """
    caveats: list[str] = []

    if verbosity_multiplier is None:
        verbosity_multiplier = DEFAULT_VERBOSITY
        caveats.append(
            "output length assumed equal across models — no verbosity evidence yet, "
            "so a wordy model may cost more than this suggests"
        )
    if expected_retry_rate is None:
        expected_retry_rate = DEFAULT_RETRY_RATE
        caveats.append(
            "no retry rate assumed — a model with reported schema failures will "
            "cost more than this"
        )

    uncached = max(workload.input_tokens - workload.cached_input_tokens, 0)
    cached_rate = (
        pricing.price_cached_read
        if pricing.price_cached_read is not None
        else pricing.price_in
    )

    tokens_cost = (
        uncached * pricing.price_in
        + workload.cached_input_tokens * cached_rate
        + workload.output_tokens * verbosity_multiplier * pricing.price_out
    ) / 1_000_000

    per_call = tokens_cost * (1 + expected_retry_rate)

    if workload.batch_eligible and pricing.batch_discount:
        per_call *= 1 - pricing.batch_discount
        caveats.append(f"batch discount of {pricing.batch_discount:.0%} applied")

    per_request = per_call * workload.runs_per_request

    monthly = (
        per_request * workload.requests_per_month
        if workload.requests_per_month is not None
        else None
    )

    return CostEstimate(
        per_call=per_call,
        per_request=per_request,
        monthly=monthly,
        caveats=tuple(caveats),
    )


def retry_rate_from_evidence(schema_failure_reports: int, total_voices: int) -> float | None:
    """A crude retry rate from reported schema failures.

    Deliberately crude, and returns None below three voices — inventing a
    precise multiplier from two anecdotes would be exactly the fake precision
    this system exists to avoid. Capped at 0.5: beyond that the model is not a
    candidate anyway.
    """
    if total_voices < 3:
        return None
    return min(0.5, schema_failure_reports / total_voices)


def monthly_saving(
    *, current: CostEstimate, candidate: CostEstimate
) -> float | None:
    """What moving this one role saves per month.

    This is the number advice is ordered by — `runs_per_request` is already
    baked into both sides, which is what makes a 10x-per-request role sort
    above a once-per-request one.
    """
    if current.monthly is None or candidate.monthly is None:
        return None
    return max(current.monthly - candidate.monthly, 0.0)
