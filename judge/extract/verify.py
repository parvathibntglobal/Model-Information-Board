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

import html
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from judge.extract.schema import ExtractedClaim


class VerificationFailure(StrEnum):
    """Why a claim was discarded. Every one of these is logged, never swallowed."""

    #: The quote appears nowhere in the text the extractor was given, even after
    #: normalisation. This is what a fabricated OR injected quote produces, and
    #: it is the failure rule 1 exists for - distinct from ENCODING_MISMATCH,
    #: which means the words ARE there in a different surface form.
    NOT_FOUND = "not_found"

    #: Absent by exact match but PRESENT after normalisation - HTML entities
    #: decoded (the trafilatura double-decode case, judge/CLAUDE.md), smart
    #: quotes and whitespace folded, case ignored. The model re-encoded what it
    #: was shown rather than inventing it: an encoding/fidelity miss, NOT
    #: fabrication. Split out because the two carry opposite meanings and,
    #: since `claim_verified_ck` forbids storing a failed quote, this reason is
    #: the ONLY record that a rejection was recoverable rather than invented -
    #: folding it into NOT_FOUND was the difference between the real fabrication
    #: rate and one twice as high. Still a rejection: rule 1 needs an exact span
    #: and step 3 renders the raw one, so an accept path is a separate decision.
    ENCODING_MISMATCH = "encoding_mismatch"
    OFFSET_OUT_OF_RANGE = "offset_out_of_range"
    TEXT_MISMATCH = "text_mismatch"
    UNMAPPED_SPAN = "unmapped_span"
    SPAN_CROSSES_COMMENTS = "span_crosses_comments"
    RAW_TEXT_MISSING = "raw_text_missing"
    SARCASTIC = "sarcastic"
    POLARITY_CONTRADICTION = "polarity_contradiction"

    def explain(self) -> str:
        """One line, for a reader who is not going to open this file.

        ⚠ BESIDE THE ENUM, NOT ON A PAGE. `/admin/stages` names the gates each
          stage runs and reads this, the same way it reads
          `RejectionTrigger.explain` and `GATE_MEANING`. A description written
          on the page instead would be true the day it was pasted and quietly
          wrong afterwards (rule 11) - and a rejection reason nobody outside
          this module can read is a rejection nobody can disagree with.
        """
        return _EXPLANATIONS[self]


_EXPLANATIONS = {
    VerificationFailure.NOT_FOUND: (
        "The quote appears nowhere in the text the extractor was given, even "
        "after normalisation. This is what a fabricated or injected quote "
        "produces, and it is the failure rule 1 exists for."
    ),
    VerificationFailure.ENCODING_MISMATCH: (
        "Absent by exact match but PRESENT after normalisation - HTML entities "
        "decoded, smart quotes and whitespace folded. The model re-encoded "
        "what it was shown rather than inventing it. Kept separate from "
        "not-found because folding the two together doubled the apparent "
        "fabrication rate."
    ),
    VerificationFailure.OFFSET_OUT_OF_RANGE: (
        "The character span points past the end of the text it was given."
    ),
    VerificationFailure.TEXT_MISMATCH: (
        "The span is inside the text, and the characters at it are not the "
        "quote the extractor claimed."
    ),
    VerificationFailure.UNMAPPED_SPAN: (
        "The span resolves to no source document in the offset map, so there "
        "is nobody to attribute the quote to."
    ),
    VerificationFailure.SPAN_CROSSES_COMMENTS: (
        "The quote runs across two people's comments. It cannot be displayed "
        "as anybody's words, and counting it would credit one voice with "
        "another's sentence."
    ),
    VerificationFailure.RAW_TEXT_MISSING: (
        "The document is not in this machine's raw store, so the quote cannot "
        "be shown in the form a human actually wrote it."
    ),
    VerificationFailure.SARCASTIC: (
        "The quote reads as sarcasm, so its plain meaning is the opposite of "
        "the claim filed against it. Discarded rather than flipped - we do not "
        "guess which reading to believe."
    ),
    VerificationFailure.POLARITY_CONTRADICTION: (
        "The extractor marked the claim positive while listing it as a pain "
        "point. The sign is contradictory, so the claim is discarded rather "
        "than flipped."
    ),
}


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


def _resolve_raw_span(segments: list[OffsetMapping], start: int, end: int) -> tuple[int, int]:
    """Translate a flattened span into source coordinates, piecewise.

    `segments` must be the overlapping segments, in flattened order, all from
    one document. An identity segment shifts linearly; a substitution segment
    is taken whole, because there is no meaningful position inside it.
    """
    first, last = segments[0], segments[-1]

    raw_start = (
        first.raw_start + (start - first.flat_start) if first.is_identity else first.raw_start
    )
    raw_end = last.raw_start + (end - last.flat_start) if last.is_identity else last.raw_end
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


#: Smart quotes, dashes and the non-breaking space, folded to ASCII. The
#: surface differences a faithful re-encoding introduces without changing a word.
_SMART = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
})


def _normalise(text: str) -> str:
    """Fold the surface differences a faithful re-encoding introduces.

    Deterministic and conservative: HTML entities decoded, NFKC unicode
    normalisation (full-width forms, ligatures, compatibility characters), smart
    quotes/dashes to ASCII, whitespace collapsed, casefolded. Enough to
    recognise a re-encoded quote; not so loose that a fabrication matches - it
    still has to be the same words in the same order. No model involved, so rule
    1 is intact: this only CLASSIFIES a rejection, it never accepts a quote, and
    the normalised match has no defensible offset so it can never reach a claim.

    NFKC is here because it is what E1's harness measured the 34/34 split with,
    so production reconciles with that number rather than reporting its own; the
    definition lives in this one function so any harness can share it.
    """
    folded = unicodedata.normalize("NFKC", html.unescape(text)).translate(_SMART)
    return re.sub(r"\s+", " ", folded).strip().casefold()


def _matching_flattened_span(quote_normalised: str, flattened_text: str) -> str | None:
    """The exact original flattened substring that normalises to the quote.

    DIAGNOSTIC ONLY, and it returns text rather than an offset for that reason:
    normalisation changes character positions, so this span has no defensible
    coordinate and must never reach a claim. It exists to SHOW the other side of
    an encoding mismatch - what the model quoted vs what was actually in the
    flattened text - so the accept-path call is made from the record.

    Brute force, because it runs only on the rare mismatch path: for each start,
    grow the window until its normalisation equals the quote's or overshoots it.
    Whitespace collapse can shrink a window, so the window is allowed to run a
    little past the quote length before giving up.
    """
    n = len(flattened_text)
    cap = len(quote_normalised) * 2 + 16
    for i in range(n):
        for j in range(i + 1, min(n, i + cap) + 1):
            window = _normalise(flattened_text[i:j])
            if window == quote_normalised:
                return flattened_text[i:j]
            if len(window) > len(quote_normalised):
                break
    return None


def _locate(quote: str, flattened_text: str, *, hint: int) -> tuple[int, int] | None:
    """Every occurrence of the quote, and the one nearest the hint.

    Returns None when the quote is absent, which is the case rule 1 exists to
    catch and the one a fabricated quote produces.
    """
    if not quote:
        return None
    positions: list[int] = []
    at = flattened_text.find(quote)
    while at != -1:
        positions.append(at)
        at = flattened_text.find(quote, at + 1)
    if not positions:
        return None
    best = min(positions, key=lambda p: abs(p - hint))
    return best, best + len(quote)


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
    if claim.polarity_contradicts_pain:
        # A claim marked positive while listing a pain point contradicts itself.
        # Dropped rather than flipped, on the same principle as sarcasm: we do
        # not guess which of two of the model's own answers to believe.
        return Rejection(
            claim,
            VerificationFailure.POLARITY_CONTRADICTION,
            "extractor marked the claim positive while listing a pain point; the sign "
            "is contradictory, so the claim is discarded rather than flipped",
        )

    # ── step 0: LOCATE. Code finds the quote; the model only named it. ───
    #
    # The offset the model supplies is a HINT. The first live run had five of
    # six claims off by one to three characters, because a language model
    # cannot count characters - and the quotes themselves were correct every
    # time. Trusting its arithmetic threw away good evidence.
    #
    # Searching for the quote is strictly stronger than checking a position it
    # gave us: the span is now something code computed, and step 1 still
    # confirms it. The model cannot supply a position anything trusts.
    #
    # The hint earns its place when a quote appears more than once: the
    # occurrence NEAREST the hint is taken, so a repeated sentence is
    # attributed to the comment the extractor was actually reading rather than
    # to the first one in the thread.
    located = _locate(claim.quote, flattened_text, hint=claim.quote_offset[0])
    if located is None:
        # ABSENT BY EXACT MATCH — but is it invented, or just re-encoded? The two
        # are opposite findings (fabrication vs a fidelity miss), and this is the
        # only place the distinction can be recorded, so split them here.
        normalised = _normalise(claim.quote)
        if normalised and normalised in _normalise(flattened_text):
            # RECORD BOTH SIDES. Deciding the accept path needs to know whether
            # this is the extractor reformatting punctuation or collect/'s
            # flattening introducing characters the model never saw - and that
            # is unanswerable from the model's quote alone. The flattened span
            # that matches under normalisation is the other side; captured here
            # so the call can be made from the logged rejection rather than by
            # re-running the corpus. Diagnostic only - it is never an offset.
            shown = _matching_flattened_span(normalised, flattened_text)
            shown_note = f"; flattened text there is {shown!r}" if shown is not None else ""
            return Rejection(
                claim,
                VerificationFailure.ENCODING_MISMATCH,
                "quote is absent by exact match but present after normalising "
                f"(entities/nfkc/quotes/whitespace/case): model quoted "
                f"{claim.quote!r}{shown_note} — a re-encoding of shown text, not "
                "a fabrication; still rejected, because rule 1 needs the exact "
                "span and step 3 renders the raw one",
            )
        return Rejection(
            claim,
            VerificationFailure.NOT_FOUND,
            f"quote does not appear in the flattened text at all: {claim.quote[:60]!r}",
        )
    start, end = located

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
        """All verification failures over all outcomes. Monitored; above 1% alerts.

        A blunt monitor: it moves for a fabrication, an offset-map bug and a
        re-encoded quote alike. `fabrication_rate` is the sharper signal inside
        it — the one that actually means the model invented or was injected.
        """
        total = len(self.verified) + len(self.rejected)
        return len(self.rejected) / total if total else 0.0

    def _count(self, reason: VerificationFailure) -> int:
        return sum(1 for r in self.rejected if r.reason == reason)

    @property
    def fabrication_rate(self) -> float:
        """NOT_FOUND over all outcomes — the injection/fabrication tripwire.

        A quote absent even after normalisation is invented or injected; a
        re-encoded one (ENCODING_MISMATCH) is neither. Folding the two together
        was the difference between the real rate and one twice as high, and since
        `claim_verified_ck` forbids storing a failed quote, this is the only
        place the fabrication rate can be known.
        """
        total = len(self.verified) + len(self.rejected)
        return self._count(VerificationFailure.NOT_FOUND) / total if total else 0.0

    @property
    def encoding_mismatch_rate(self) -> float:
        """ENCODING_MISMATCH over all outcomes — recoverable fidelity misses,
        not fabrications. Worth watching on its own: a rising one points at the
        normalisation chain (e.g. trafilatura), not at the model."""
        total = len(self.verified) + len(self.rejected)
        return self._count(VerificationFailure.ENCODING_MISMATCH) / total if total else 0.0


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
