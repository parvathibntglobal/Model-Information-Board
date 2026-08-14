"""Quote verification — the guarantee the whole product rests on.

No claim without a verbatim quote. The check is plain Python: deterministic,
100% coverage, and incapable of hallucinating. A model is never asked whether
another model told the truth.

THREE STEPS AGAINST THREE ARTEFACTS, because the string the extractor read is
not the string the reader sees:

    1  INTEGRITY    flattened_text[start:end] == quote
                    exact substring match, no model involved

    2  ATTRIBUTION  offset_map -> source document + raw span
                    which comment, by which author, on which platform

    3  DISPLAY      render the RAW span from the source document
                    never the normalised form

Getting this wrong is not a cosmetic bug. Verifying flattened offsets against
the raw document either fails on everything or SILENTLY PASSES AGAINST THE
WRONG TEXT — and this is also the prompt-injection backstop, because an
injected instruction cannot produce a verifiable span.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from judge.extract.schema import ExtractedClaim


class VerificationFailure(StrEnum):
    """Why a claim was discarded. Every one of these is logged, never swallowed."""

    OFFSET_OUT_OF_RANGE = "offset_out_of_range"
    TEXT_MISMATCH = "text_mismatch"
    UNMAPPED_SPAN = "unmapped_span"
    SPAN_CROSSES_COMMENTS = "span_crosses_comments"
    RAW_TEXT_MISSING = "raw_text_missing"
    SARCASTIC = "sarcastic"


@dataclass(frozen=True)
class OffsetMapping:
    """One SEGMENT of thread_context.offset_map.

    Maps a run of the flattened string back to the source a human wrote.
    Built by collect/ during normalisation, and IMPOSSIBLE to reconstruct
    afterwards — which is why it has a hard deadline before the first
    extraction run.

    SEGMENTS ARE NOT WHOLE COMMENTS. Normalisation rewrites text in place —
    an emoji becomes `[upside_down_face]`, 1 character becoming 18 — so a
    single offset delta per comment goes wrong the moment a quote spans a
    substitution, and produces a span that points at the wrong text or past
    the end of the document.

    So E3 emits one segment per contiguous run where flattened and raw
    correspond one-to-one, plus one segment per substitution. A substitution
    segment has different flat and raw lengths, and cannot be sub-indexed —
    a span touching it takes the whole substitution.
    """

    flat_start: int
    flat_end: int
    document_id: str
    raw_start: int
    raw_end: int

    @property
    def is_identity(self) -> bool:
        """True when this run was not rewritten, so offsets shift linearly."""
        return (self.flat_end - self.flat_start) == (self.raw_end - self.raw_start)

    def overlaps(self, start: int, end: int) -> bool:
        return self.flat_start < end and start < self.flat_end

    def contains(self, start: int, end: int) -> bool:
        return self.flat_start <= start and end <= self.flat_end


def _resolve_raw_span(
    segments: list[OffsetMapping], start: int, end: int
) -> tuple[int, int]:
    """Translate a flattened span into source coordinates, piecewise.

    `segments` must be the overlapping segments, in flattened order, all from
    one document. An identity segment shifts linearly; a substitution segment
    is taken whole, because there is no meaningful position inside it.
    """
    first, last = segments[0], segments[-1]

    raw_start = (
        first.raw_start + (start - first.flat_start)
        if first.is_identity
        else first.raw_start
    )
    raw_end = (
        last.raw_start + (end - last.flat_start) if last.is_identity else last.raw_end
    )
    return raw_start, raw_end


@dataclass(frozen=True)
class VerifiedQuote:
    """A quote that survived all three steps, ready to persist and display."""

    document_id: str
    flat_offset: tuple[int, int]
    raw_offset: tuple[int, int]
    display_text: str
    """The RAW span, as the engineer wrote it.

    Emoji were translated to bracketed tags during normalisation so sarcasm
    survives classification. `[upside_down_face]` is an internal
    representation and must never reach a page.
    """


@dataclass(frozen=True)
class Rejection:
    claim: ExtractedClaim
    reason: VerificationFailure
    detail: str


def verify(
    claim: ExtractedClaim,
    *,
    flattened_text: str,
    offset_map: Iterable[OffsetMapping],
    raw_text_of: dict[str, str],
) -> VerifiedQuote | Rejection:
    """Run the three steps. Returns a VerifiedQuote or a Rejection, never None.

    Args:
        claim: what the extractor proposed.
        flattened_text: the exact string the extractor was given.
        offset_map: from `thread_context.offset_map`.
        raw_text_of: document_id -> the untouched source text.
    """
    if claim.is_sarcastic:
        # Inverting sarcasm programmatically is unreliable. Dropping is honest.
        return Rejection(
            claim,
            VerificationFailure.SARCASTIC,
            "extractor flagged the quote as sarcastic; claim discarded rather than inverted",
        )

    start, end = claim.quote_offset

    # ── step 1: INTEGRITY ────────────────────────────────────────────────
    if end > len(flattened_text):
        return Rejection(
            claim,
            VerificationFailure.OFFSET_OUT_OF_RANGE,
            f"offset {claim.quote_offset} exceeds flattened text of {len(flattened_text)} chars",
        )

    actual = flattened_text[start:end]
    if actual != claim.quote:
        return Rejection(
            claim,
            VerificationFailure.TEXT_MISMATCH,
            f"flattened_text[{start}:{end}] is {actual!r}, extractor claimed {claim.quote!r}",
        )

    # ── step 2: ATTRIBUTION ──────────────────────────────────────────────
    # A span crossing two comments cannot be attributed to one author, so it
    # cannot be counted as one voice. Reject rather than guess.
    overlapping = sorted(
        (m for m in offset_map if m.overlaps(start, end)),
        key=lambda m: m.flat_start,
    )
    if not overlapping:
        return Rejection(
            claim,
            VerificationFailure.UNMAPPED_SPAN,
            f"span {claim.quote_offset} resolves to no source document in offset_map",
        )

    documents = {m.document_id for m in overlapping}
    if len(documents) > 1:
        return Rejection(
            claim,
            VerificationFailure.SPAN_CROSSES_COMMENTS,
            f"span {claim.quote_offset} spans {len(documents)} documents "
            f"({sorted(documents)}); an unattributable quote cannot be displayed "
            "or counted as a voice",
        )

    document_id = overlapping[0].document_id
    raw_start, raw_end = _resolve_raw_span(overlapping, start, end)

    # ── step 3: DISPLAY ──────────────────────────────────────────────────
    raw = raw_text_of.get(document_id)
    if raw is None:
        return Rejection(
            claim,
            VerificationFailure.RAW_TEXT_MISSING,
            f"document {document_id!r} not in the raw store",
        )
    if raw_end > len(raw):
        return Rejection(
            claim,
            VerificationFailure.OFFSET_OUT_OF_RANGE,
            f"raw span [{raw_start}:{raw_end}] exceeds document of {len(raw)} chars — "
            "offset_map is stale or was built against different source text",
        )

    return VerifiedQuote(
        document_id=document_id,
        flat_offset=(start, end),
        raw_offset=(raw_start, raw_end),
        display_text=raw[raw_start:raw_end],
    )


@dataclass
class VerificationRun:
    """Outcome of verifying one thread's worth of claims."""

    verified: list[tuple[ExtractedClaim, VerifiedQuote]]
    rejected: list[Rejection]

    @property
    def failure_rate(self) -> float:
        """Monitored. Above 1% alerts.

        It is both the fabrication detector and the injection tripwire — a
        planted instruction cannot produce a span that survives step 1.
        """
        total = len(self.verified) + len(self.rejected)
        return len(self.rejected) / total if total else 0.0


def verify_all(
    claims: Iterable[ExtractedClaim],
    *,
    flattened_text: str,
    offset_map: Iterable[OffsetMapping],
    raw_text_of: dict[str, str],
) -> VerificationRun:
    offset_map = list(offset_map)
    verified: list[tuple[ExtractedClaim, VerifiedQuote]] = []
    rejected: list[Rejection] = []

    for claim in claims:
        outcome = verify(
            claim,
            flattened_text=flattened_text,
            offset_map=offset_map,
            raw_text_of=raw_text_of,
        )
        if isinstance(outcome, Rejection):
            rejected.append(outcome)
        else:
            verified.append((claim, outcome))

    return VerificationRun(verified=verified, rejected=rejected)
