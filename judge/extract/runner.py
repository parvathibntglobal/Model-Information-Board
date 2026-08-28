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
from judge.extract.placeholder import has_nothing_to_extract
from judge.extract.prompt import build_system_prompt, wrap_untrusted
from judge.extract.schema import MAX_QUOTE_CHARS, ExtractedClaim, ExtractionResult
from judge.extract.verify import (
    OffsetMapping,
    Rejection,
    VerificationFailure,
    VerifiedQuote,
    verify,
)

log = logging.getLogger(__name__)


class ExtractionRefused(Exception):
    """The document never reached the model, and why.

    Distinct from "the model returned nothing": a refusal means we declined to
    ask. Collapsing the two would make a forged block marker indistinguishable
    from a document with no claims in it, and only one of those is an attack.
    """


#: Why a document produced nothing. TWO ZEROS THAT ARE NOT THE SAME.
#:
#:   SILENT     the model read the document and proposed nothing. A real zero,
#:              and the expected outcome on most documents.
#:   UNSALVAGED every claim it proposed failed the schema. A zero about our
#:              plumbing, not about the corpus - and it read identically to the
#:              first one until 2026-08-21, which is how `qwen-38-27b` was
#:              recorded as a clean nothing while holding fourteen claims.
ZERO_SILENT = "silent"
ZERO_UNSALVAGED = "unsalvaged"


@dataclass
class Unsalvaged:
    """A claim the model proposed that could not be built. Recorded, not dropped.

    `rejected` holds `(ExtractedClaim, Rejection)` - a claim that exists and
    failed verification. This one never became an `ExtractedClaim` at all, so it
    has no object to pair, and dropping it silently is what made a 14-claim
    document look empty.

    `raw` is the model's own dict for that claim. Kept because the errors alone
    do not say what was lost: "quote too long" is not evidence, and the quote is.
    """

    index: int
    errors: tuple[str, ...]
    raw: dict


@dataclass
class ExtractionRun:
    """What one thread produced, including what it failed to produce."""

    thread_context_id: str
    verified: list[tuple[ExtractedClaim, VerifiedQuote]] = field(default_factory=list)
    rejected: list[tuple[ExtractedClaim, Rejection]] = field(default_factory=list)
    #: Quotes that say something about a model and fit no capability key.
    #:
    #: AN EMPTY LIST HERE IS NOT EVIDENCE THAT THE VOCABULARY IS COMPLETE, and
    #: it has already failed once in exactly the case it exists for. Measured
    #: 2026-08-21 on `deepseek-v4-pro-0813`: the extractor's `no_claim_reason`
    #: was that the observation was "too vague to map to a specific capability"
    #: and this list came back **empty**. The capability really is missing - the
    #: 12 keys contain one `ops` entry, `ops.latency_ttft`, and nothing for token
    #: spend or output length - so the signal designed to catch a missing
    #: capability failed on the missing capability.
    #:
    #: Three first-person token-efficiency reports are off the board for three
    #: different reasons and this is one of them.
    #: `docs/proposals/for-engineer-2-a-speaking-field-on-modelref.md` §0.
    unclassified: list[str] = field(default_factory=list)
    #: Claims the model proposed that could not be built. See `Unsalvaged`.
    unsalvaged: list[Unsalvaged] = field(default_factory=list)
    no_claim_reason: str | None = None
    #: `ZERO_SILENT` or `ZERO_UNSALVAGED`, set only when nothing was verified.
    #: A validation zero and a real zero are different findings and the first
    #: one masqueraded as the second for the whole project until 2026-08-21.
    zero_kind: str | None = None
    schema_retries: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def proposed(self) -> int:
        """Everything the model put forward, including what could not be built.

        `unsalvaged` is in the count on purpose. A document where the model
        proposed fourteen claims and none survived the schema has a rejection
        rate of 1.0, and reporting `proposed = 0` for it hid the loudest signal
        the run had.
        """
        return len(self.verified) + len(self.rejected) + len(self.unsalvaged)

    @property
    def rejection_rate(self) -> float | None:
        """None when nothing was proposed. Never 0.0.

        A run that proposed no claims has no rejection rate; 0.0 would assert
        that everything proposed survived, which is a different finding and the
        one an alert would act on.
        """
        return len(self.rejected) / self.proposed if self.proposed else None

    @property
    def fabricated(self) -> int:
        """Rejected quotes absent even after normalisation — invented or injected.

        The count the encoding/fabrication split is about. `claim_verified_ck`
        forbids storing a failed quote, so `rejected` is the only record it
        exists in at all, and separating this from a re-encoded quote
        (`encoding_mismatches`) is the difference between the real fabrication
        rate and one twice as high.
        """
        return sum(1 for _, rej in self.rejected if rej.reason == VerificationFailure.NOT_FOUND)

    @property
    def encoding_mismatches(self) -> int:
        """Rejected quotes present after normalisation — a re-encoding of shown
        text, not a fabrication. A fidelity signal, pointed at the normalisation
        chain rather than at the model."""
        return sum(
            1 for _, rej in self.rejected
            if rej.reason == VerificationFailure.ENCODING_MISMATCH
        )


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

    # BEFORE the model call. A thread of nothing but `[removed]` bodies costs a
    # call that can only produce a verbatim quote of a platform tombstone -
    # rule 1 holding perfectly over text that means nothing. Reported as a
    # no-claim reason rather than raised: it is a fact about the thread, not a
    # failure, and a batch must not stop on it.
    if has_nothing_to_extract(thread.raw_text_of):
        run.no_claim_reason = (
            "every document in this thread is a platform placeholder "
            "(`[removed]` or `[deleted]`), so there is nothing to quote. No "
            "model call was made."
        )
        return run

    try:
        user_message = wrap_untrusted(thread.flattened_text)
    except ValueError as exc:
        raise ExtractionRefused(str(exc)) from exc

    system = build_system_prompt(capability_keys)
    schema = tool_schema_for(ExtractionResult)

    result, completions, retries = _call_with_one_retry(
        client, system=system, user=user_message, schema=schema
    )
    run.schema_retries = retries
    # SUMMED ACROSS EVERY CALL. Counting the last one alone under-reported the
    # spend by one call per retry, in the flattering direction.
    run.input_tokens = sum(c.input_tokens for c in completions)
    run.output_tokens = sum(c.output_tokens for c in completions)

    if result is None:
        # SALVAGE. The envelope did not validate, which until 2026-08-21 ended the
        # document. `qwen-38-27b` was recorded as a clean zero while holding
        # fourteen claims, two of which had over-long quotes.
        # SALVAGE FROM THE BEST ANSWER, NOT THE NEWEST. A retry can be worse
        # than what it replaced, and taking the last completion threw away a
        # first answer that had eleven good claims in it.
        attempts = [salvage_claims(c.raw_arguments) for c in completions]
        best = max(range(len(attempts)), key=lambda i: len(attempts[i][0]))
        built, lost, envelope_error = attempts[best]
        if len(completions) > 1 and best != len(completions) - 1:
            log.info(
                "thread %s: salvaging from attempt %d of %d - a later retry "
                "yielded fewer claims than an earlier one",
                thread.thread_context_id,
                best + 1,
                len(completions),
            )
        run.unsalvaged = lost
        if envelope_error is not None:
            run.zero_kind = ZERO_UNSALVAGED
            run.no_claim_reason = (
                f"the extractor's answer could not be read at all: {envelope_error}. "
                "Nothing can be said about what it proposed."
            )
            return run
        if not built:
            run.zero_kind = ZERO_UNSALVAGED
            run.no_claim_reason = (
                f"all {len(lost)} proposed claim(s) failed the schema; none could "
                "be salvaged. This is a validation zero, not a document that said "
                "nothing."
            )
            return run
        log.warning(
            "thread %s: envelope failed the schema; SALVAGED %d of %d claims, "
            "%d unsalvageable. Reasons: %s",
            thread.thread_context_id,
            len(built),
            len(built) + len(lost),
            len(lost),
            "; ".join(e for u in lost for e in u.errors)[:300],
        )
        # `unclassified` and `no_claim_reason` live on the envelope and the
        # envelope is what failed, so they stay absent rather than guessed.
        claims_in = built
    else:
        run.unclassified = list(result.unclassified)
        run.no_claim_reason = result.no_claim_reason
        claims_in = list(result.claims)

    # `is_sarcastic` discards before verification rather than after. Verifying a
    # quote we have already decided to drop spends the work and, worse, would
    # put a verified-and-discarded claim in the same bucket as a fabricated one.
    # A polarity/pain-point contradiction is dropped here for the same reason:
    # it is a decision we have already made, not a fabrication to flag.
    keep = [
        claim
        for claim in claims_in
        if not claim.is_sarcastic and not claim.polarity_contradicts_pain
    ]
    sarcastic = sum(1 for c in claims_in if c.is_sarcastic)
    contradictory = sum(
        1 for c in claims_in if not c.is_sarcastic and c.polarity_contradicts_pain
    )
    if sarcastic:
        log.info(
            "thread %s: dropped %d sarcastic claim(s). Inverting sarcasm is "
            "unreliable; dropping it is honest.",
            thread.thread_context_id,
            sarcastic,
        )
    if contradictory:
        log.info(
            "thread %s: dropped %d claim(s) marked positive while listing a pain "
            "point. The sign is contradictory, so discarded rather than flipped.",
            thread.thread_context_id,
            contradictory,
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

    # A REAL ZERO AND A VALIDATION ZERO ARE DIFFERENT FINDINGS. Set here so the
    # distinction survives into whatever reads the run, rather than being
    # reconstructable only from a log line.
    if not run.verified and run.zero_kind is None:
        run.zero_kind = ZERO_UNSALVAGED if run.unsalvaged else ZERO_SILENT

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


def salvage_claims(raw_arguments: str) -> tuple[list[ExtractedClaim], list[Unsalvaged], str | None]:
    """Build each claim on its own. Keep what validates, record what does not.

    WHY THIS AND NOT A HIGHER RETRY CEILING. A ceiling trades one all-or-nothing
    for a slower all-or-nothing: the batch still stands or falls together, it
    just costs more calls first. Measured, the correction loop does converge -
    `qwen-38-27b` went from 5 validation errors to 1 on its retry - and
    converging is not the same as arriving. **Eleven good claims should not
    depend on the twelfth.**

    THE FAILURE SCALES WITH SUCCESS, which is the argument for fixing the shape
    rather than the rate. Before the quote limit went into the field description,
    2 of 30 documents lost everything to schema validation. After, when far more
    documents were producing claims at all, it was 5 of 30. A per-document
    failure mode gets worse as extraction gets better.

    WHAT IS NOT SALVAGED, and it is deliberate: anything outside `claims`.
    `unclassified` and `no_claim_reason` are read from the envelope only when the
    envelope parses. A malformed envelope is a different failure from a malformed
    claim, and guessing at one from the other is how a partial read becomes a
    silent one.

    Returns `(built, unsalvaged, envelope_error)`. `envelope_error` is set when
    the JSON or the outer shape is unusable, in which case both lists are empty
    and nothing can be said about what the model proposed.
    """
    try:
        payload = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        return [], [], f"arguments were not JSON: {exc}"
    if not isinstance(payload, dict):
        return [], [], f"arguments were {type(payload).__name__}, not an object"

    raw_claims = payload.get("claims")
    if raw_claims is None:
        return [], [], "no `claims` key in the arguments"
    if not isinstance(raw_claims, list):
        return [], [], f"`claims` was {type(raw_claims).__name__}, not a list"

    built: list[ExtractedClaim] = []
    lost: list[Unsalvaged] = []
    for index, item in enumerate(raw_claims):
        if not isinstance(item, dict):
            lost.append(Unsalvaged(index=index, errors=("claim was not an object",), raw={}))
            continue
        try:
            built.append(ExtractedClaim.model_validate(item))
        except ValidationError as exc:
            lost.append(
                Unsalvaged(
                    index=index,
                    errors=tuple(
                        f"{'.'.join(str(p) for p in e.get('loc') or ())}: {e.get('msg')}"
                        for e in exc.errors()
                    ),
                    raw=item,
                )
            )
    return built, lost, None


def _quote_length_correction(exc: ValidationError, raw: str) -> str | None:
    """A retry that names the claim, its length, and the limit. Or None.

    WHY THIS IS NOT A BIGGER CEILING AND NOT PER-CLAIM REJECTION.
    ------------------------------------------------------------
    `qwen-38-27b` proposed 14 claims and lost all 14 because two quotes were 15
    and 8 characters over. Measured, both had a sentence boundary well inside the
    limit:

        claim 11   215 chars, sentence ends at 63
                   "I've been getting around 15-30 tokens a second from LM
                    Studio." carries the whole measurement in 62.
        claim 12   208 chars, sentence ends at 51
                   but the PREFIX loses the number - the 72% is in the second
                   sentence, which is ~157 chars and fits on its own.

    So a compliant span existed in both cases and the model did not choose it.
    That is an instruction it was already given - *"Choose the SHORTEST span that
    carries the claim"* - being ignored, not a limit that is too tight. Raising
    the ceiling would admit a longer quote onto a page for no reason, and
    rejecting the claim throws away work that is correct apart from its span.

    AND THE FIX IS NOT TRUNCATION. Claim 12 is the counter-example: its prefix
    verifies, reads cleanly, and drops the measurement the claim is about. A
    silently shortened quote that passes verification is a true quote carrying a
    false claim.

    So: make the constraint checkable at the point it is violated. The retry
    stops being a schema complaint and becomes a specific instruction, which is
    the register this model has already shown it answers - it corrected an
    offset hint the moment `locate()` stopped asking it to count characters.

    Returns None when the failure is not about quote length, so the caller falls
    back to the verbatim error.
    """
    limit = MAX_QUOTE_CHARS
    offenders: list[tuple[int, int]] = []
    others: list[str] = []
    for error in exc.errors():
        loc = error.get("loc") or ()
        is_quote_length = (
            error.get("type") == "string_too_long"
            and len(loc) >= 3
            and loc[0] == "claims"
            and loc[-1] == "quote"
        )
        if not is_quote_length:
            # ADDITIVE, NOT ALL-OR-NOTHING, and the first version of this
            # function got that wrong in exactly the way it was written to fix.
            # A batch with four bad `conditions` and one long quote fell back to
            # the generic message and lost the specific instruction with it.
            others.append(f"  {'.'.join(str(p) for p in loc)}: {error.get('msg')}")
            continue
        try:
            index = int(loc[1])
        except (TypeError, ValueError):
            others.append(f"  {'.'.join(str(p) for p in loc)}: {error.get('msg')}")
            continue
        quote = error.get("input")
        offenders.append((index, len(quote) if isinstance(quote, str) else -1))

    if not offenders:
        return None

    lines = [
        f"{len(offenders)} of your quotes are longer than the {limit}-character "
        "limit. Nothing else about your answer was wrong, and every other claim "
        "was discarded only because these were rejected with them.",
        "",
    ]
    for index, length in offenders:
        over = length - limit if length > 0 else None
        lines.append(
            f"  claim {index}: the quote is {length} characters, "
            f"{over} over the limit."
            if over is not None
            else f"  claim {index}: the quote is over the limit."
        )
    if others:
        lines += [
            "",
            "These were also wrong, and are separate from the length problem:",
            *others,
        ]
    lines += [
        "",
        "CHOOSE A SHORTER SPAN, do not shorten the text. Re-read the document and "
        "pick a different, shorter run of characters that still carries the whole "
        "claim - it may be one sentence of the passage you chose, and it may be "
        "the SECOND sentence rather than the first. Do not trim, summarise or "
        "abbreviate what you quoted: the quote is checked against the source by "
        "exact substring match, so an edited quote fails and a truncated one can "
        "lose the part that carried the claim.",
        "",
        "If no span under the limit carries the claim, drop that claim and keep "
        "the others. Answer again with every claim you can still make.",
    ]
    return "\n".join(lines)


def _call_with_one_retry(
    client: ExtractionClient,
    *,
    system: str,
    user: str,
    schema: dict[str, object],
) -> tuple[ExtractionResult | None, list[Completion], int]:
    """Call, and on a schema violation say what was wrong and ask once more.

    The retry message carries the validation error verbatim, EXCEPT for the one
    failure that has cost real claims: an over-long quote gets a specific
    instruction naming the claim and its length instead. See
    `_quote_length_correction` for the measurement behind that.

    RETURNS EVERY COMPLETION, not the last one, and both reasons were defects:

      TOKENS. `run.input_tokens = completion.input_tokens` counted the final
      call only. The blog corpus run reported 75,985 input tokens across 30
      documents with 6 retries, so six calls were unbilled in our own figures -
      an under-count in the direction that flatters us.

      SALVAGE. A retry can be WORSE than the answer it replaces. Measured: a
      first answer with one over-long quote, retried, came back unreadable - and
      salvaging from the last completion threw away the eleven good claims in the
      first. The best answer is not always the newest one.
    """
    completion = client.complete(system=system, user=user, tool_schema=schema)
    completions = [completion]
    retries = 0

    for attempt in range(MAX_SCHEMA_RETRIES + 1):
        try:
            return _parse(completion), completions, retries
        except (ValidationError, json.JSONDecodeError) as exc:
            if attempt == MAX_SCHEMA_RETRIES:
                log.error("extraction failed the schema after %d attempts: %s", attempt + 1, exc)
                return None, completions, retries
            retries += 1
            correction = None
            if isinstance(exc, ValidationError):
                correction = _quote_length_correction(exc, completion.raw_arguments)
            if correction is None:
                correction = (
                    "Your previous answer did not satisfy the schema:\n"
                    f"{exc}\n\nAnswer again, correcting exactly that."
                )
            else:
                log.info(
                    "retrying with a quote-length correction rather than a schema "
                    "error: %s",
                    correction.splitlines()[0],
                )
            completion = client.complete(
                system=system,
                user=f"{user}\n\n{correction}",
                tool_schema=schema,
            )
            completions.append(completion)

    return None, completions, retries


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
