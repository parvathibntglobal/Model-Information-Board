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
            # REQUIRED since 2026-08-21. Every construction site must answer
            # whose claim it is; there is no default to fall through to.
            speaking="own-experience",
        ),
        capability="summarization.fidelity",
        # REQUIRED since the classifier landed — same reason as `speaking`:
        # every construction site answers which board surface the claim is for.
        board_entries=[{"section": "capability", "slug": "summarization-fidelity",
                        "name": "Summarization fidelity",
                        "definition": "Condenses long text without dropping a detail."}],
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


class TestPolarityContradictsPain:
    """A pain point makes a claim negative; any other sign contradicts it.

    Discarded, not flipped — the same principle as sarcasm: choosing which of
    two of the model's own answers to believe is a guess. This is the guard that
    would have caught "Claude Haiku 4.5 was the easiest to attack" (positive,
    pain_points=['security']) on the live board.
    """

    def _off(self):
        q = "Fine under ~50k."
        start = FLAT.index(q)
        return q, (start, start + len(q))

    def test_the_property_fires_when_a_pain_point_is_not_negative(self):
        q, off = self._off()

        def contradicts(polarity, pain):
            return make_claim(q, off, polarity=polarity, pain_points=pain).polarity_contradicts_pain

        assert contradicts("positive", ["security"])
        # neutral with a pain point is also a contradiction — a problem is not neutral
        assert contradicts("neutral", ["security"])
        # negative WITH a pain point is consistent, not a contradiction
        assert not contradicts("negative", ["security"])
        # any sign with NO pain point is fine
        assert not contradicts("positive", [])
        assert not contradicts("neutral", [])

    def test_a_positive_claim_naming_a_pain_point_is_discarded(self):
        q, off = self._off()
        result = run(make_claim(q, off, polarity="positive", pain_points=["security"]))
        assert isinstance(result, Rejection)
        assert result.reason is VerificationFailure.POLARITY_CONTRADICTION

    def test_a_neutral_claim_naming_a_pain_point_is_discarded(self):
        q, off = self._off()
        result = run(make_claim(q, off, polarity="neutral", pain_points=["verbosity"]))
        assert isinstance(result, Rejection)
        assert result.reason is VerificationFailure.POLARITY_CONTRADICTION

    def test_a_plain_neutral_claim_still_verifies(self):
        q, off = self._off()
        result = run(make_claim(q, off, polarity="neutral"))
        assert isinstance(result, VerifiedQuote)


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


class TestEncodingVersusFabrication:
    """A quote absent by exact match is one of two opposite things, and this is
    the only place the distinction can be recorded (claim_verified_ck forbids
    storing a failed quote). Fold them together and the fabrication rate doubles.
    """

    def _reject(self, quote: str):
        # offset is a hint only, so any in-range value reaches the locate step.
        return run(make_claim(quote, (30, 30 + len(quote))))

    def test_a_case_only_difference_is_encoding_not_fabrication(self):
        r = self._reject("fine under ~50k.")  # FLAT has "Fine"
        assert isinstance(r, Rejection)
        assert r.reason is VerificationFailure.ENCODING_MISMATCH

    def test_collapsed_whitespace_is_encoding(self):
        r = self._reject("Fine under  ~50k.")  # double space; FLAT has one
        assert r.reason is VerificationFailure.ENCODING_MISMATCH

    def test_an_html_entity_reencoding_is_encoding(self):
        r = self._reject("Flash is great&nbsp;for bulk")  # &nbsp; -> space
        assert r.reason is VerificationFailure.ENCODING_MISMATCH

    def test_an_nfkc_compatibility_form_is_encoding(self):
        r = self._reject("Fine under ~５０k.")  # full-width 5 0 -> NFKC "50"
        assert r.reason is VerificationFailure.ENCODING_MISMATCH

    def test_the_detail_records_both_sides(self):
        """The accept-path call needs the model's quote AND what was actually in
        the flattened text — recorded so it can be made without a re-run."""
        r = self._reject("fine under ~50k.")   # model's side: lowercased
        assert "fine under ~50k." in r.detail   # model quoted
        assert "Fine under ~50k." in r.detail   # flattened text there

    def test_a_genuinely_invented_quote_is_still_not_found(self):
        r = self._reject("Flash is terrible at absolutely everything")
        assert r.reason is VerificationFailure.NOT_FOUND

    def test_an_exact_match_still_verifies(self):
        quote = "Fine under ~50k."
        start = FLAT.index(quote)
        assert isinstance(run(make_claim(quote, (start, start + len(quote)))), VerifiedQuote)

    def test_the_rates_separate_the_two(self):
        good_start = FLAT.index("Fine under ~50k.")
        good = make_claim("Fine under ~50k.", (good_start, good_start + 16))
        encoded = make_claim("fine under ~50k.", (good_start, good_start + 16))   # case
        invented = make_claim("Fine under ~90k.", (good_start, good_start + 16))  # fabricated

        rr = verify_all(
            [good, encoded, invented],
            flattened_text=FLAT, offset_map=OFFSET_MAP, raw_text_of=RAW,
        )
        assert rr.failure_rate == 2 / 3          # both failures
        assert rr.fabrication_rate == 1 / 3      # only the invented one
        assert rr.encoding_mismatch_rate == 1 / 3

    def test_extraction_run_exposes_the_split(self):
        from judge.extract.runner import ExtractionRun

        c = make_claim("x", (0, 1))
        run_obj = ExtractionRun(
            thread_context_id="tc",
            rejected=[
                (c, Rejection(c, VerificationFailure.NOT_FOUND, "invented")),
                (c, Rejection(c, VerificationFailure.ENCODING_MISMATCH, "re-encoded")),
                (c, Rejection(c, VerificationFailure.SARCASTIC, "dropped")),
            ],
        )
        assert run_obj.fabricated == 1
        assert run_obj.encoding_mismatches == 1
