"""E5. One thread in, verified claims out.

    thread_context ──▶ prompt ──▶ model ──▶ schema ──▶ verify ──▶ claims
                                              │           │
                                          retry once   discard

THE ONLY THING THIS STAGE GUARANTEES

Every claim that leaves here carries a quote that provably exists in the text
the model was given, attributed to a real comment by a real author, and
rendered as the human wrote it rather than as the pipeline normalised it.

Nothing else is guaranteed. The model chose the capability, the polarity and
the conditions, and this stage does not check those - it cannot, and pretending
otherwise would be a model checking a model. What catches those is the golden
set, which is why a labelled set is not optional however good the prompt is.

WHY A REJECTION IS A RECORD RATHER THAN A LOG LINE

A discarded claim is the most interesting thing this stage produces. It is
either a model inventing a quote, or an injection attempt, or a bug in the
offset map - and all three are invisible in the output, which is the shape rule
6 exists for. `ExtractionRun` carries them out so a caller can count them.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field

from pydantic import ValidationError

from judge.extract.client import (
    MAX_SCHEMA_RETRIES,
    Completion,
    ExtractionClient,
    tool_schema_for,
)
from judge.extract.prompt import build_system_prompt, wrap_untrusted
from judge.extract.schema import ExtractedClaim, ExtractionResult
from judge.extract.verify import OffsetMapping, Rejection, VerifiedQuote, verify

log = logging.getLogger(__name__)


class ExtractionRefused(Exception):
    """The document never reached the model, and why.

    Distinct from "the model returned nothing": a refusal means we declined to
    ask. Collapsing the two would make a forged block marker indistinguishable
    from a document with no claims in it, and only one of those is an attack.
    """


@dataclass
class ExtractionRun:
    """What one thread produced, including what it failed to produce."""

    thread_context_id: str
    verified: list[tuple[ExtractedClaim, VerifiedQuote]] = field(default_factory=list)
    rejected: list[tuple[ExtractedClaim, Rejection]] = field(default_factory=list)
    unclassified: list[str] = field(default_factory=list)
    no_claim_reason: str | None = None
    schema_retries: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def proposed(self) -> int:
        return len(self.verified) + len(self.rejected)

    @property
    def rejection_rate(self) -> float | None:
        """None when nothing was proposed. Never 0.0.

        A run that proposed no claims has no rejection rate; 0.0 would assert
        that everything proposed survived, which is a different finding and the
        one an alert would act on.
        """
        return len(self.rejected) / self.proposed if self.proposed else None


@dataclass(frozen=True)
class ThreadInput:
    """Everything E5 needs about one thread. Read-only, from `collect/`."""

    thread_context_id: str
    flattened_text: str
    offset_map: tuple[OffsetMapping, ...]
    raw_text_of: dict[str, str]


def extract(
    thread: ThreadInput,
    *,
    client: ExtractionClient,
    capability_keys: list[str],
) -> ExtractionRun:
    """Run E5 over one thread.

    Raises `ExtractionRefused` when the document cannot be safely presented -
    which today means it forges a block marker. Everything else is reported in
    the returned run rather than raised, because a batch that stops on one bad
    document is a batch that never finishes.
    """
    run = ExtractionRun(thread_context_id=thread.thread_context_id)

    try:
        user_message = wrap_untrusted(thread.flattened_text)
    except ValueError as exc:
        raise ExtractionRefused(str(exc)) from exc

    system = build_system_prompt(capability_keys)
    schema = tool_schema_for(ExtractionResult)

    result, completion, retries = _call_with_one_retry(
        client, system=system, user=user_message, schema=schema
    )
    run.schema_retries = retries
    run.input_tokens = completion.input_tokens
    run.output_tokens = completion.output_tokens

    if result is None:
        run.no_claim_reason = "extractor returned nothing parseable against the schema"
        return run

    run.unclassified = list(result.unclassified)
    run.no_claim_reason = result.no_claim_reason

    # `is_sarcastic` discards before verification rather than after. Verifying a
    # quote we have already decided to drop spends the work and, worse, would
    # put a verified-and-discarded claim in the same bucket as a fabricated one.
    keep = [claim for claim in result.claims if not claim.is_sarcastic]
    dropped = len(result.claims) - len(keep)
    if dropped:
        log.info(
            "thread %s: dropped %d sarcastic claim(s). Inverting sarcasm is "
            "unreliable; dropping it is honest.",
            thread.thread_context_id,
            dropped,
        )

    # `verify` per claim rather than `verify_all`, which returns bare
    # Rejections. A rejection without the claim that produced it is much
    # weaker evidence: fabrication, an injection attempt and an offset-map bug
    # look identical until you can see what was proposed.
    offsets = list(thread.offset_map)
    for claim in keep:
        outcome = verify(
            claim,
            flattened_text=thread.flattened_text,
            offset_map=offsets,
            raw_text_of=thread.raw_text_of,
        )
        if isinstance(outcome, VerifiedQuote):
            run.verified.append((claim, outcome))
        else:
            run.rejected.append((claim, outcome))
            log.warning(
                "thread %s: claim discarded, %s. Document flagged.",
                thread.thread_context_id,
                outcome.reason,
            )

    return run


def extract_all(
    threads: Iterable[ThreadInput],
    *,
    client: ExtractionClient,
    capability_keys: list[str],
) -> list[ExtractionRun]:
    """A batch. A refused document is skipped, not fatal."""
    runs: list[ExtractionRun] = []
    for thread in threads:
        try:
            runs.append(extract(thread, client=client, capability_keys=capability_keys))
        except ExtractionRefused as exc:
            log.error("thread %s refused: %s", thread.thread_context_id, exc)
    return runs


def _call_with_one_retry(
    client: ExtractionClient,
    *,
    system: str,
    user: str,
    schema: dict[str, object],
) -> tuple[ExtractionResult | None, Completion, int]:
    """Call, and on a schema violation say what was wrong and ask once more.

    The retry message carries the validation error verbatim. A retry that just
    says "try again" is a second roll of the same dice; one that names the
    field is a correction.
    """
    completion = client.complete(system=system, user=user, tool_schema=schema)
    retries = 0

    for attempt in range(MAX_SCHEMA_RETRIES + 1):
        try:
            return _parse(completion), completion, retries
        except (ValidationError, json.JSONDecodeError) as exc:
            if attempt == MAX_SCHEMA_RETRIES:
                log.error("extraction failed the schema after %d attempts: %s", attempt + 1, exc)
                return None, completion, retries
            retries += 1
            completion = client.complete(
                system=system,
                user=(
                    f"{user}\n\nYour previous answer did not satisfy the schema:\n"
                    f"{exc}\n\nAnswer again, correcting exactly that."
                ),
                tool_schema=schema,
            )

    return None, completion, retries


def _parse(completion: Completion) -> ExtractionResult:
    if completion.is_empty:
        # An empty tool call is not an empty result. `ExtractionResult` requires
        # a reason when there are no claims, so silence gets explained rather
        # than passing as a clean nothing.
        raise ValidationError.from_exception_data(
            "ExtractionResult",
            [
                {
                    "type": "missing",
                    "loc": ("claims",),
                    "input": None,
                }
            ],
        )
    return ExtractionResult.model_validate_json(completion.raw_arguments)
