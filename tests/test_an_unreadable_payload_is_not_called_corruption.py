"""#303: the store called a missing blob corruption, and E5 skipped one silently.

Measured 2026-09-15, every `thread_context.flattened_text_ref` read against one
machine's raw store:

    thread_context rows 4,144    flattened text unreadable here 151   3.6%
    hackernews 58 · devto 56 · reddit 25 · huggingface 10 · blog 1

⚠ THE STORE CANNOT TELL CORRUPTION FROM A SYNC GAP, AND IT SAID CORRUPTION.
  Two very different states present as the same absent file:

      lost or deleted here                a broken NFR-4 guarantee
      written on another machine and      a sync gap, and the store is intact
        never synced to this one

  The second demonstrably exists: the 2026-09-15 dedupe stage reported **465
  payloads not on this machine**, and `fetch_model.py`'s selection already
  treats an unreadable payload as "not this fetch's thread" rather than as
  damage.

  There is no manifest to check against — no `raw_object`, `blob` or
  `tombstone` table exists, and nothing records which machine wrote which
  blob. So rule 6: an absence the code cannot explain must not be reported as
  a definite finding. What it CAN say is what it did — this store could not
  read this ref, and there is no tombstone, so the removal was not deliberate.
  That is true in both states.

⚠ AND THE SKIP LEFT NO TRACE, WHICH IS RULE 4 AT THE SELECTION STEP.
  `build_thread_inputs` caught the exception and `continue`d, so a fetch that
  skipped a third of its candidates reported identically to one that skipped
  none. 4 of the 20 threads behind the `cost.*` claims are in the unreadable
  set, so a re-extraction for #300 would have skipped them silently.

WHAT IS NOT DONE HERE, because it is not fixable from one machine: running the
same check on the other laptop (which would settle whether the 151 are a sync
gap), and whether a manifest is worth building. Both are on #303.
"""

from __future__ import annotations

import pathlib

import pytest

from collect.rawstore import PayloadMissing, RawStore

ROOT = pathlib.Path(__file__).resolve().parents[1]
FETCH = ROOT / "scripts" / "fetch_model.py"
STORE = ROOT / "collect" / "rawstore.py"


class TestTheStoreDoesNotClaimCorruption:
    def test_the_message_does_not_assert_which_of_the_two_it_is(self, tmp_path):
        store = RawStore(tmp_path)
        with pytest.raises(PayloadMissing) as caught:
            store.get("raw/sha256/ab/cd/abcdef")
        message = str(caught.value)
        assert "corrupt" not in message.lower()
        assert "deleted it directly" not in message

    def test_it_still_says_the_removal_was_not_deliberate(self, tmp_path):
        """⚠ THE HALF THAT MUST SURVIVE THE CORRECTION. "No tombstone" is a
        real finding and is true in both states — softening the message into
        saying nothing would lose the one thing the store does know."""
        store = RawStore(tmp_path)
        with pytest.raises(PayloadMissing) as caught:
            store.get("raw/sha256/ab/cd/abcdef")
        assert "tombstone" in str(caught.value)

    def test_it_names_this_machine_rather_than_the_world(self, tmp_path):
        store = RawStore(tmp_path)
        with pytest.raises(PayloadMissing) as caught:
            store.get("raw/sha256/ab/cd/abcdef")
        assert "this raw store" in str(caught.value)

    def test_the_requirement_id_survives_for_monitoring(self):
        """NFR-4 is the one token in the log line that will not be rephrased,
        so monitoring and tests key on it. Rewording the prose around it must
        not take it with them."""
        assert "NFR-4" in STORE.read_text(encoding="utf-8")

    def test_a_tombstoned_payload_is_still_a_different_exception(self, tmp_path):
        """⚠ THE DISTINCTION THIS CORRECTION MUST NOT BLUR. A takedown is
        deliberate and honoured; this is neither. Making the missing case
        vaguer must not make it indistinguishable from the case the store
        genuinely does know about."""
        from collect.rawstore import PayloadTombstoned

        assert PayloadTombstoned is not PayloadMissing
        assert not issubclass(PayloadMissing, PayloadTombstoned)


class TestTheRunSaysWhatItSkipped:
    def test_the_selector_counts_unreadable_payloads(self):
        source = FETCH.read_text(encoding="utf-8")
        assert "unreadable.append(tc_id)" in source

    def test_it_returns_them_rather_than_only_counting(self):
        """Returned as ids, like `oversized` beside it and for the same
        reason: "N were skipped" is only actionable if somebody can find out
        WHICH."""
        source = FETCH.read_text(encoding="utf-8")
        assert "oversized, unreadable, (named, from_own_harvest)" in source

    def test_the_stage_line_reports_it(self):
        source = FETCH.read_text(encoding="utf-8")
        assert "threads_unreadable_here=len(unreadable)" in source

    def test_the_stage_line_does_not_call_it_corruption_either(self):
        """⚠ THE SAME OVERCLAIM, ONE LAYER UP. This line knows strictly less
        than the store does, so it must not assert more."""
        source = FETCH.read_text(encoding="utf-8")
        note = source[source.index("unreadable_note = ("):]
        note = note[:note.index("prog.stage(")]
        assert "corrupt" not in note.lower()
        assert "nothing here can tell which" in note

    def test_it_is_said_only_when_it_happened(self):
        """A permanent "0 unreadable" on every run is furniture, and furniture
        stops being read — which is how the next non-zero one gets missed."""
        source = FETCH.read_text(encoding="utf-8")
        note = source[source.index("unreadable_note = ("):]
        note = note[:note.index("prog.stage(")]
        assert "if unreadable else" in note
