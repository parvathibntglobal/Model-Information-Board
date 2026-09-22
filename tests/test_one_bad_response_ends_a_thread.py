"""A provider failure costs the thread, not the batch behind it (#397).

WHAT IT COST. `ExtractorUnavailable` escaped `run_all`, so a single 502 from
one upstream ended E5 - and with it E5c, E5b, E6 and E7. Measured over 33 run
logs: **7 runs died this way and 145 threads were never attempted**, several
of them on thread 1 or 2 of 23, after the documents had been harvested,
assembled, triaged and one model call paid for.

⚠ TWO FAILURES ARRIVE THROUGH ONE EXCEPTION AND WANT OPPOSITE HANDLING.

    502 from an upstream, 504 idle timeout, a stream that stopped
        -> another attempt is routed afresh and usually succeeds

    the provider rejecting OUR TOOL SCHEMA
        -> fails identically every time. Two of the seven runs died on
           `GenerateContentRequest...properties[quote_offset].items:
           missing field` - Gemini refusing an array with no item type.

Retrying the second is paying again for the same sentence, so `transient` is
set at the raise site rather than guessed from the message by a caller.
"""

from __future__ import annotations

import pathlib

from judge.extract.client import ExtractorUnavailable

ROOT = pathlib.Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "judge" / "pipeline.py"
CLIENT = ROOT / "judge" / "extract" / "client.py"
SCRIPT = ROOT / "scripts" / "fetch_model.py"


class TestTheExceptionSaysWhetherToTryAgain:
    def test_it_defaults_to_transient(self):
        """A new raise site that forgets to think about this should fail
        toward retrying, not toward giving up silently."""
        assert ExtractorUnavailable("anything").transient is True

    def test_a_rejection_of_our_own_request_is_permanent(self):
        assert ExtractorUnavailable("x", transient=False).transient is False

    def test_the_schema_rejection_is_classified_at_the_raise_site(self):
        """Not sniffed from the message by the caller: the place that knows
        which kind of failure this is, is the place that raises it."""
        src = CLIENT.read_text(encoding="utf-8")
        assert '"GenerateContentRequest" in text' in src
        assert '"function_declarations" in text' in src
        assert "transient=not permanent," in src


class TestTheBatchSurvivesTheThread:
    def test_the_loop_catches_it_rather_than_letting_it_escape(self):
        src = PIPELINE.read_text(encoding="utf-8")
        assert "except ExtractorUnavailable as exc:" in src

    def test_a_permanent_failure_is_not_retried(self):
        """Every attempt is a paid call. Re-sending a schema the upstream has
        already refused buys the same sentence twice."""
        src = PIPELINE.read_text(encoding="utf-8")
        body = src[src.index("except ExtractorUnavailable as exc:"):]
        body = body[:body.index("if result is None:")]
        assert 'if not getattr(exc, "transient", True):' in body
        # and it stops rather than falling through into the retry
        assert body.index('transient", True)') < body.index("self.retried_threads += 1")

    def test_the_retry_is_bounded(self):
        src = PIPELINE.read_text(encoding="utf-8")
        assert "EXTRACT_ATTEMPTS = max(1, int(os.getenv(" in src
        assert "for attempt in range(1, EXTRACT_ATTEMPTS + 1):" in src

    def test_the_cap_still_governs_a_retry(self):
        """An unbounded retry would turn a provider outage into a budget
        event; a bounded one still has to ask before spending again."""
        src = PIPELINE.read_text(encoding="utf-8")
        body = src[src.index("self.retried_threads += 1"):]
        body = body[:body.index("if result is None:")]
        assert "budget.check_before_call()" in body


class TestAThreadItCouldNotReadStaysUnread:
    def test_a_failed_thread_is_never_recorded_as_read(self):
        """⚠ THE ONE THAT WOULD LOSE EVIDENCE PERMANENTLY. `_ledger.record`
        marks a thread done and `already_extracted()` then skips it forever.
        A thread the provider would not answer for has not been read, so the
        `continue` must come before the ledger write - rule 4, and the
        exception's own docstring says the same thing."""
        # ⚠ CODE LINES ONLY, AND THE FIRST VERSION FAILED ON ITS OWN COMMENT.
        #   The comment beside the retry says "the `continue` below skips
        #   `self._ledger.record(...)`" - so a plain `.index()` found the
        #   MENTION 3,000 characters before the CALL and reported the
        #   ordering backwards. Fifth time this repository has hit
        #   mention-versus-use; the other four are written down in
        #   `test_the_board_drills_down.py` and `test_a_class_that_does_not_exist.py`.
        lines = [
            ln for ln in PIPELINE.read_text(encoding="utf-8").splitlines()
            if not ln.strip().startswith("#")
        ]
        loop = chr(10).join(lines)
        loop = loop[loop.index("for thread in threads:"):]
        gave_up = loop.index("if result is None:")
        recorded = loop.index("self._ledger.record(")
        assert gave_up < recorded, (
            "the give-up path falls through to the ledger, which would mark "
            "an unread thread as read and lose it permanently"
        )

    def test_the_run_says_how_many_it_could_not_read(self):
        """Rule 4 one level down from #327: a run that read 20 of 23 and one
        that read 23 must not report the same sentence."""
        src = SCRIPT.read_text(encoding="utf-8")
        assert "COULD NOT BE READ" in src
        assert "unread_threads=len(unread) or None," in src
        assert "retried_threads=retried or None," in src

    def test_the_counters_survive_the_call(self):
        """They are instance state, so the Pipeline has to be bound rather
        than constructed inline and thrown away."""
        src = SCRIPT.read_text(encoding="utf-8")
        assert "pipeline = Pipeline(" in src
        assert "results = pipeline.run_all(" in src
