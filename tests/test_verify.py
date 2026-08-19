"""Quote verification — the guarantee everything else rests on.

If these tests fail, nothing on the board can be trusted, because a claim could
be displaying text the engineer never wrote.
"""

from __future__ import annotations

from judge.extract.schema import ExtractedClaim, ModelRef
from judge.extract.verify import (
    OffsetMapping,
    Rejection,
    VerificationFailure,
    VerifiedQuote,
    verify,
    verify_all,
)

# A flattened thread: root post plus one child, roles marked, emoji translated
# to a bracketed tag exactly as E3 emits it.
FLAT = (
    "[root by alice] Flash is great for bulk work.\n"
    "[reply by bob] Fine under ~50k. Past that we started silently missing things. "
    "[upside_down_face]"
)

RAW = {
    "doc_root": "Flash is great for bulk work.",
    "doc_reply": "Fine under ~50k. Past that we started silently missing things. \U0001f643",
}

# Segments, not whole comments. Normalisation rewrote the emoji, so the reply
# splits into an identity run and a substitution run — which is exactly what
# collect/ must emit, since one offset delta per comment cannot survive a
# length-changing substitution.
_REPLY_PREFIX = "Fine under ~50k. Past that we started silently missing things. "

OFFSET_MAP = [
    OffsetMapping(
        flat_start=FLAT.index("Flash is great"),
        flat_end=FLAT.index("Flash is great") + len(RAW["doc_root"]),
        document_id="doc_root",
        raw_start=0,
        raw_end=len(RAW["doc_root"]),
    ),
    # identity run: text unchanged, offsets shift linearly
    OffsetMapping(
        flat_start=FLAT.index(_REPLY_PREFIX),
        flat_end=FLAT.index(_REPLY_PREFIX) + len(_REPLY_PREFIX),
        document_id="doc_reply",
        raw_start=0,
        raw_end=len(_REPLY_PREFIX),
    ),
    # substitution run: "[upside_down_face]" (18 chars) stands in for the
    # emoji (1 char). Different lengths, so it is taken whole.
    OffsetMapping(
        flat_start=FLAT.index("[upside_down_face]"),
        flat_end=len(FLAT),
        document_id="doc_reply",
        raw_start=len(_REPLY_PREFIX),
        raw_end=len(RAW["doc_reply"]),
    ),
]


def make_claim(quote: str, offset: tuple[int, int], **kw) -> ExtractedClaim:
    defaults = dict(
        source_comment_id="doc_reply",
        model_ref=ModelRef(
            surface="Flash",
            resolved_version_id="google/gemini-2.5-flash",
            specificity="version",
            resolution_confidence=0.9,
        ),
        capability="summarization.fidelity",
        polarity="negative",
        quote=quote,
        quote_offset=offset,
        relevance="central",
    )
    return ExtractedClaim(**{**defaults, **kw})


def run(claim: ExtractedClaim):
    return verify(claim, flattened_text=FLAT, offset_map=OFFSET_MAP, raw_text_of=RAW)


class TestIntegrity:
    def test_exact_match_passes(self):
        quote = "Fine under ~50k."
        start = FLAT.index(quote)
        result = run(make_claim(quote, (start, start + len(quote))))
        assert isinstance(result, VerifiedQuote)
        assert result.document_id == "doc_reply"

    def test_fabricated_quote_is_rejected(self):
        """The whole point. A model that invents a plausible quote gets nothing."""
        quote = "Fine under ~90k."  # same length, never written
        start = FLAT.index("Fine under ~50k.")
        result = run(make_claim(quote, (start, start + len(quote))))
        assert isinstance(result, Rejection)
        assert result.reason is VerificationFailure.NOT_FOUND  # see _locate

    def test_offset_past_end_is_rejected(self):
        result = run(make_claim("x" * 10, (len(FLAT) - 2, len(FLAT) + 8)))
        assert isinstance(result, Rejection)
        assert result.reason is VerificationFailure.NOT_FOUND  # the offset is a hint now

    def test_the_schema_accepts_a_hint_that_does_not_match_the_length(self):
        """This asserted the schema REJECTED a length mismatch, and it did.

        The first live run failed on five of six claims that way, off by one to
        three characters each, because a language model cannot count characters.
        The quotes were correct every time; only the arithmetic was wrong, and
        rejecting the batch threw away good evidence over it.

        The offset is a hint now and `_locate` derives the true span, so a
        mismatched length is expected input rather than a violation.
        """
        quote = "silently missing things"
        claim = make_claim(quote, (0, len(quote) + 3))

        assert claim.quote_offset == (0, len(quote) + 3)

        # And it still verifies, because _locate finds the real span.
        result = verify(claim, flattened_text=FLAT, offset_map=OFFSET_MAP, raw_text_of=RAW)
        assert isinstance(result, VerifiedQuote), result


class TestAttribution:
    def test_resolves_to_the_right_comment(self):
        quote = "Flash is great"
        start = FLAT.index(quote)
        result = run(make_claim(quote, (start, start + len(quote))))
        assert isinstance(result, VerifiedQuote)
        assert result.document_id == "doc_root"
        assert RAW["doc_root"][slice(*result.raw_offset)] == quote

    def test_span_crossing_two_comments_is_rejected(self):
        """An unattributable quote cannot be displayed or counted as one voice."""
        start = FLAT.index("bulk work.")
        end = FLAT.index("Fine under") + len("Fine under")
        result = run(make_claim(FLAT[start:end], (start, end)))
        assert isinstance(result, Rejection)
        assert result.reason is VerificationFailure.SPAN_CROSSES_COMMENTS

    def test_unmapped_span_is_rejected(self):
        quote = "[root by alice]"
        start = FLAT.index(quote)
        result = run(make_claim(quote, (start, start + len(quote))))
        assert isinstance(result, Rejection)
        assert result.reason is VerificationFailure.UNMAPPED_SPAN


class TestDisplay:
    def test_display_text_is_the_raw_span_not_the_normalised_one(self):
        """`[upside_down_face]` is internal. It must never reach a page."""
        quote = "silently missing things. [upside_down_face]"
        start = FLAT.index(quote)
        result = run(make_claim(quote, (start, start + len(quote))))

        assert isinstance(result, VerifiedQuote)
        assert "[upside_down_face]" not in result.display_text
        assert "\U0001f643" in result.display_text


class TestSarcasm:
    def test_sarcastic_claims_are_discarded_not_inverted(self):
        quote = "Fine under ~50k."
        start = FLAT.index(quote)
        result = run(make_claim(quote, (start, start + len(quote)), is_sarcastic=True))
        assert isinstance(result, Rejection)
        assert result.reason is VerificationFailure.SARCASTIC


class TestRun:
    def test_failure_rate_is_reported(self):
        good_quote = "Fine under ~50k."
        good_start = FLAT.index(good_quote)
        good = make_claim(good_quote, (good_start, good_start + len(good_quote)))
        bad = make_claim("Fine under ~90k.", (good_start, good_start + 16))

        run_result = verify_all(
            [good, bad], flattened_text=FLAT, offset_map=OFFSET_MAP, raw_text_of=RAW
        )

        assert len(run_result.verified) == 1
        assert len(run_result.rejected) == 1
        assert run_result.failure_rate == 0.5  # alerts above 1% in production
