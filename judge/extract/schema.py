"""The claim record — what E5 emits, and the only thing it may emit.

The extractor returns this and nothing else. No free-text channel, no "notes"
field, no way to take an action. That constraint is half the prompt-injection
defence; the other half is that every claim carries a quote which is then
verified in ordinary Python (see verify.py).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Polarity = Literal["positive", "negative"]
Severity = Literal["mild", "clear", "severe"]
Relevance = Literal["central", "passing"]
Specificity = Literal["snapshot", "version", "family"]
EvidenceTier = Literal["A", "B", "C", "D", "E", "F"]

MAX_QUOTE_CHARS = 200


class ModelRef(BaseModel):
    """Which model the claim is about, and how sure we are."""

    surface: str = Field(description="exactly as the human wrote it")
    resolved_version_id: str | None = None
    specificity: Specificity
    resolution_confidence: float = Field(ge=0.0, le=1.0)


class Conditions(BaseModel):
    """What makes claims comparable.

    "Tool calling is unreliable" means something different at 40 tools than at
    5. Without these we would be stacking incomparable statements and calling
    the result consensus.

    Every field is optional, because a human writing a forum post owes us
    nothing. Absent means absent — never guessed into a band.
    """

    tool_count: int | None = None
    context_size: int | None = Field(default=None, description="input tokens, if stated")
    structured_mode: bool | None = Field(
        default=None, description="was provider-side schema enforcement on"
    )
    framework: str | None = Field(default=None, description="LangChain, raw API, ...")
    hosted_by: str | None = Field(
        default=None,
        description="for open weights, latency and price belong to the HOST, not the model",
    )
    domain: str | None = None


class ExtractedClaim(BaseModel):
    """One claim, as the extractor proposes it.

    Offsets index into `flattened_text` — the exact string the extractor was
    given — NOT into the raw source document. Resolution to the source happens
    in verify.py, step 2.
    """

    source_comment_id: str = Field(
        description="which comment inside the flattened thread this came from"
    )
    model_ref: ModelRef
    capability: str = Field(description="a key from contract/capabilities.yaml")

    polarity: Polarity
    severity: Severity | None = Field(
        default=None,
        description=(
            "PHRASE SELECTION ONLY. Never averaged, never summed. A float here "
            "would be fake precision, and it would invite someone to average it."
        ),
    )
    comparison_target: str | None = Field(
        default=None, description="set when the quote compares two models"
    )
    pain_points: list[str] = Field(default_factory=list)

    conditions: Conditions = Field(default_factory=Conditions)

    quote: str = Field(
        max_length=MAX_QUOTE_CHARS,
        description="VERBATIM text from the source. No paraphrase, no ellipsis, no repair.",
    )
    quote_offset: tuple[int, int] = Field(description="[start, end) into flattened_text")

    relevance: Relevance
    has_repro_steps: bool = False
    has_numbers: bool = False
    is_sarcastic: bool = Field(
        default=False,
        description=(
            "true DISCARDS the claim. Inverting sarcasm programmatically is "
            "unreliable; dropping it is honest."
        ),
    )

    @model_validator(mode="after")
    def _offsets_are_sane(self) -> ExtractedClaim:
        """The offset is a HINT, and the length no longer has to match.

        This required `end - start == len(quote)` and rejected the whole batch
        when it did not. The first live run failed here on five of six claims,
        by one to three characters each - because A LANGUAGE MODEL CANNOT COUNT
        CHARACTERS, and asking it to was a design error rather than a defect in
        its answer. The quotes themselves were correct.

        So the model identifies the quote and CODE locates it: `locate()` in
        the runner searches the flattened text and derives the true span. That
        is strictly more rule-1 compliant than before - the model no longer
        supplies a position anything trusts, and a span code computed is a span
        code verified.

        What remains checked here is only that the hint is not nonsense: a
        forward range at a plausible position. A wrong-by-two hint is fine and
        is exactly what arrives.
        """
        start, end = self.quote_offset
        if start < 0 or end <= start:
            raise ValueError(f"quote_offset {self.quote_offset} is not a forward range")
        return self


class ExtractionResult(BaseModel):
    """Everything the extractor returns for one flattened thread.

    A thread mentioning three models produces claims per model. A thread with
    nothing extractable returns an empty list and a reason — never an invented
    claim to fill the silence.
    """

    claims: list[ExtractedClaim] = Field(default_factory=list)
    no_claim_reason: str | None = Field(
        default=None,
        description="required when claims is empty: why this thread yielded nothing",
    )
    unclassified: list[str] = Field(
        default_factory=list,
        description=(
            "Quotes that clearly say something about a model but fit no capability "
            "in the vocabulary. These accumulate; a growing cluster is the signal "
            "that engineers are discussing something we do not yet track."
        ),
    )

    @model_validator(mode="after")
    def _silence_is_explained(self) -> ExtractionResult:
        if not self.claims and not self.no_claim_reason:
            raise ValueError(
                "empty extraction must state no_claim_reason — silence needs a reason, "
                "not an empty result that looks like a failure"
            )
        return self
