"""A malformed offset hint cost 44 claims in one thread (Nano Banana 2 run).

MEASURED. `var/fetch/mv_de3e701e07b8bfa9-554826d4.jsonl`, 2026-09-23. The new
`unsalvaged_by_error` field named it on its first run:

    thread 4/4   0 verified, 44 unsalvaged, retry 1
       x44  Value error, quote_offset (0, 0) is not a forward range

**One shape, forty-four instances** — the extractor returned `(0, 0)` for every
claim in the thread, and `ExtractedClaim._offsets_are_sane` raised on each.
That thread used more input tokens than the other three in the run combined,
retried once and failed identically, cost $0.004608 (**64% of the whole run**)
and stored nothing.

⚠ THE VALUE IT REJECTED ON HAS NO READER.

    verify.py:322   _locate(claim.quote, flattened_text,
                            hint=claim.quote_offset[0])     <- start, advisory
    verify.py:352   start, end = located                    <- code's span, used
    nowhere         claim.quote_offset[1]                   <- NO READER AT ALL

`_locate` finds every occurrence of the quote itself and returns the one
nearest the hint, so `start=0` is a usable hint meaning "prefer the earliest
occurrence". The half the validator raised on — `end` — is read by nothing
outside an error message. A wrong-by-two hint was fine and a hint of zero was
fatal, under a docstring saying the model "no longer supplies a position
anything trusts".

⚠ AND RULE 1 IS UNTOUCHED, which is the only reason this is safe to remove.
  `verify()` still requires the quote to appear character for character in the
  text the model was shown; an invented quote is still NOT_FOUND. This removes
  a check that could only produce false alarms, not one that catches
  fabrication.
"""

from __future__ import annotations

import pathlib
import re

from judge.extract.schema import ExtractedClaim

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERIFY = ROOT / "judge" / "extract" / "verify.py"
SCHEMA = ROOT / "judge" / "extract" / "schema.py"


def claim(offset: tuple[int, int]) -> ExtractedClaim:
    return ExtractedClaim(
        source_comment_id="c1",
        model_ref={
            "surface": "Nano Banana 2", "specificity": "version",
            "resolution_confidence": 0.9, "speaking": "own-experience",
        },
        capability="image-editing",
        board_entries=[{
            "section": "capability", "slug": "image-editing",
            "name": "Image editing", "definition": "Whether edits land.",
        }],
        polarity="positive",
        quote="it is fast",
        relevance="central",
        quote_offset=offset,
    )


class TestTheClaimSurvivesAMalformedHint:
    def test_the_exact_shape_that_cost_forty_four_claims(self):
        """`(0, 0)`, forty-four times, in one thread of a four-thread run."""
        assert claim((0, 0)).quote_offset == (0, 0)

    def test_a_negative_hint_builds_too(self):
        """Nothing about a negative start makes the QUOTE less locatable, and
        the quote is the claim."""
        assert claim((-5, -1)).quote_offset == (-5, -1)

    def test_an_ordinary_hint_is_unaffected(self):
        assert claim((1200, 1250)).quote_offset == (1200, 1250)

    def test_the_validator_raises_on_nothing(self):
        """⚠ CODE LINES ONLY. The docstring above the validator explains at
        length what it used to raise and why, so a plain search of the file
        finds the explanation and reports the defect it documents. Ninth time
        this repository has met mention-versus-use."""
        lines = [
            ln for ln in SCHEMA.read_text(encoding="utf-8").splitlines()
            if not ln.strip().startswith("#")
        ]
        body = "\n".join(lines)
        body = body[body.index("def _offsets_are_sane"):]
        body = body[:body.index("\n    @property")]
        code = re.sub(r'"""(?:.|\n)*?"""', "", body)
        assert "raise" not in code, "the validator refuses something again"


class TestTheHintIsSanitisedWhereItIsRead:
    def test_a_negative_start_becomes_the_earliest_occurrence(self):
        """`_locate` takes the occurrence nearest the hint. A negative position
        cannot be one, so it means the same as no idea: prefer the earliest."""
        src = VERIFY.read_text(encoding="utf-8")
        assert "hint=max(0, claim.quote_offset[0])" in src

    def test_the_end_is_still_read_by_nothing(self):
        """⚠ THE WHOLE ARGUMENT RESTS ON THIS. If something starts reading
        `quote_offset[1]`, a malformed hint stops being harmless and this
        change needs revisiting."""
        readers = []
        for path in (ROOT / "judge").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            # ⚠ NINTH INSTANCE, AND IT LANDED IN THE TEST THAT WARNS ABOUT IT
            #   TWO METHODS ABOVE. The first version stripped comments and
            #   f-strings and not DOCSTRINGS, and the validator's own docstring
            #   explains at length that `quote_offset[1]` has no reader - so
            #   the sentence saying the field is unread was found and reported
            #   as the field being read.
            text = re.sub(r'"""[\s\S]*?"""', "", text)
            for i, ln in enumerate(text.splitlines(), 1):
                if ln.strip().startswith("#") or 'f"' in ln or "f'" in ln:
                    continue
                if "quote_offset[1]" in ln:
                    readers.append(f"{path.name}:{i}")
        assert not readers, f"quote_offset[1] now has a reader: {readers}"

    def test_the_integrity_checks_use_the_span_code_computed(self):
        """Not the model's. That is what makes the model's copy advisory."""
        src = VERIFY.read_text(encoding="utf-8")
        assert "start, end = located" in src


class TestRuleOneStillCatchesAFabricatedQuote:
    def test_the_substring_check_is_untouched(self):
        """The check that actually catches invention, and the reason removing
        the offset check costs nothing."""
        src = VERIFY.read_text(encoding="utf-8")
        assert "flattened_text.find(quote)" in src
        assert "NOT_FOUND" in src

    def test_a_quote_that_is_absent_is_still_rejected(self):
        from judge.extract.verify import _locate

        assert _locate("never written", "some other text", hint=0) is None

    def test_a_zero_hint_still_locates_a_quote_that_is_present(self):
        """The 44 claims would have been located, had they been built."""
        text = "before it. it is fast. after it."
        assert _l("it is fast", text, 0) == (text.index("it is fast"),
                                             text.index("it is fast") + 10)


def _l(quote, text, hint):
    from judge.extract.verify import _locate

    return _locate(quote, text, hint=hint)
