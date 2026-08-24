"""Platform tombstones, and the limit of rule 1 they expose.

`[removed]` is nine characters of real text. A quote of it is verbatim,
resolves to the right document and the right author, and says nothing. Rule 1
is about FIDELITY and this is a failure of CONTENT, so verification cannot see
it - there is no difference to see.
"""

from __future__ import annotations

import pytest

from judge.extract.placeholder import (
    PLACEHOLDER_BODIES,
    has_nothing_to_extract,
    is_placeholder_body,
    is_placeholder_status,
    readable_documents,
)
from judge.extract.runner import ThreadInput, extract


class NeverCalled:
    """A client that fails the test if the model is reached."""

    def complete(self, **kwargs):
        raise AssertionError("a model was called for a thread of placeholders")


class TestTheMatchIsExactNotSubstring:
    """A comment discussing removal is somebody's writing and belongs in the
    corpus. Dropping it would be the entity gate's word-boundary bug again."""

    @pytest.mark.parametrize("body", sorted(PLACEHOLDER_BODIES))
    def test_the_platform_placeholders_are_recognised(self, body):
        assert is_placeholder_body(body)
        assert is_placeholder_body(f"  {body}  "), "surrounding whitespace defeats it"

    def test_a_comment_mentioning_removal_is_kept(self):
        for real in (
            "the mod replaced it with [removed] which is unhelpful",
            "[removed] appears when a comment is deleted",
            "why does this say [deleted]?",
        ):
            assert not is_placeholder_body(real), real

    def test_ordinary_text_is_kept(self):
        assert not is_placeholder_body("gemini dropped the clause")


class TestTheStatusMarkIsPreferredWhereItExists:
    """`collect/` knows the platform wrote it; this lane cannot tell that from
    a person typing the same nine characters."""

    def test_the_mark_is_recognised(self):
        assert is_placeholder_status("removed")
        assert not is_placeholder_status("kept")
        assert not is_placeholder_status(None)

    def test_a_marked_document_is_dropped_even_with_ordinary_text(self):
        """The mark wins. That is the whole reason to prefer it."""
        kept = readable_documents({"d1": "gemini dropped the clause"}, status_of={"d1": "removed"})
        assert kept == {}

    def test_an_unmarked_placeholder_still_falls_back_to_the_text(self):
        """Which is everywhere today: document_status_ck permits
        kept|filtered|rejected|tombstoned, so 'removed' cannot be written."""
        assert readable_documents({"d1": "[removed]"}) == {}


class TestNoModelCallForAThreadOfTombstones:
    """Before the call rather than after. Cheaper, and it cannot be bypassed by
    a later caller the way a verification-time check can."""

    def test_an_all_placeholder_thread_makes_no_call(self):
        thread = ThreadInput(
            thread_context_id="tc1",
            flattened_text="[removed]\n[deleted]",
            offset_map=(),
            raw_text_of={"d1": "[removed]", "d2": "[deleted]"},
        )
        run = extract(thread, client=NeverCalled(), capability_keys=["x"])

        assert run.verified == []
        assert run.no_claim_reason is not None
        assert "nothing to quote" in run.no_claim_reason

    def test_the_reason_says_no_call_was_made(self):
        """Distinguishable from a thread the model read and found nothing in -
        the same distinction the extraction ledger draws one layer up."""
        thread = ThreadInput("tc1", "[removed]", (), {"d1": "[removed]"})
        run = extract(thread, client=NeverCalled(), capability_keys=["x"])

        assert "No model call was made" in run.no_claim_reason

    def test_a_thread_with_one_real_document_is_still_sent(self):
        """The skip is for threads with NOTHING to say, not for threads with a
        tombstone in them. A deleted comment beside four real ones is a normal
        thread."""
        assert not has_nothing_to_extract({"d1": "[removed]", "d2": "gemini dropped the clause"})

    def test_an_empty_raw_text_map_is_NOT_nothing_to_extract(self):
        """This asserted the opposite and the opposite broke a security check.

        `test_a_forged_block_marker_is_refused_not_sanitised` supplies
        `raw_text_of={}` with text forging a block marker. Returning True there
        fired the early return, `wrap_untrusted` never ran, and an ATTACK came
        back as "no claims found" - the exact distinction that test protects.

        An empty mapping is a thread whose documents were not supplied:
        malformed, not tombstoned, and it must still reach every check below.
        """
        assert not has_nothing_to_extract({})

    def test_it_is_a_reason_rather_than_an_exception(self):
        """A fact about the thread, not a failure. A batch must not stop on it."""
        thread = ThreadInput("tc1", "[removed]", (), {"d1": "[removed]"})
        run = extract(thread, client=NeverCalled(), capability_keys=["x"])
        assert run.thread_context_id == "tc1"


class TestTheGuardRunsBeforeAnythingElse:
    def test_it_precedes_the_untrusted_wrap_in_the_source(self):
        """A placeholder thread that also forged a marker would otherwise raise
        rather than skip, which is a different outcome for the same input."""
        import inspect

        source = inspect.getsource(extract)
        assert source.index("has_nothing_to_extract") < source.index("wrap_untrusted")
