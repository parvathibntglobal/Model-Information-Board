"""The detector that decides which contexts get deleted and rebuilt.

`looks_like_json` is the whole safety of `scripts/rebuild_platform_contexts.py`:
a false positive deletes a context holding good prose and rebuilds it for no
reason, and a false negative leaves a poisoned one in place.

IT PARSES RATHER THAN SNIFFS, and that is not fastidiousness. The github
rebuild recorded the measurement: a first-character check flagged 39 contexts
and EVERY ONE was prose, because the flattener renders emoji as shortcodes and
titles legitimately begin `[bar_chart] AI CLI Tools Digest`. A 100%
false-positive rate on real data.

THE SHAPE THIS ONE ADDS. The platform flattener joins several document payloads
with a `\n---\n` separator, so the file as a whole is NOT valid JSON even when
every part of it is. Parsing the whole thing returns "Extra data" and the
envelope reads as prose — which would have left every multi-document thread
poisoned, including the Hacker News one this was written for.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rebuild_platform_contexts.py"


def _module():
    spec = importlib.util.spec_from_file_location("rebuild_platform_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def looks_like_json():
    return _module().looks_like_json


class TestItParsesRatherThanSniffs:
    def test_a_title_in_square_brackets_is_prose(self):
        # The exact false positive the github rebuild measured.
        assert _module().looks_like_json("[bar_chart] AI CLI Tools Digest\n\nBody text.") is False

    def test_a_single_json_payload_is_an_envelope(self, looks_like_json):
        assert looks_like_json('{"author":"simplybeing1","children":[]}') is True

    def test_a_json_array_is_an_envelope(self, looks_like_json):
        assert looks_like_json('[{"id":1},{"id":2}]') is True

    def test_ordinary_prose_is_not(self, looks_like_json):
        assert looks_like_json("When no one is watching, the agent shot.") is False

    def test_empty_text_is_not(self, looks_like_json):
        assert looks_like_json("") is False


class TestTheSeparatorShapeThisScriptAdds:
    def test_several_payloads_joined_by_the_separator_are_an_envelope(self, looks_like_json):
        # Whole-file parsing raises "Extra data" here. Before the first-part
        # fallback, every multi-document thread read as prose and stayed
        # poisoned - which is most Hacker News threads.
        joined = '{"author":"a","children":[]}\n---\n{"author":"b","children":[]}'
        assert looks_like_json(joined) is True

    def test_prose_containing_a_separator_is_still_prose(self, looks_like_json):
        assert looks_like_json("A paragraph.\n---\nAnother paragraph.") is False


class TestTheScriptRefusesToTouchClaimedContexts:
    """Read off the source: the database work needs a live connection, but
    WHICH rows it excludes is a decision expressed in code."""

    @staticmethod
    def _src() -> str:
        return SCRIPT.read_text(encoding="utf-8")

    def test_claims_and_extractions_are_both_checked(self):
        src = self._src()
        assert "FROM claim WHERE thread_context_id = ANY(%s)" in src
        assert "FROM thread_extraction" in src

    def test_blocked_contexts_are_removed_from_the_rebuild_list(self):
        src = self._src()
        assert "rebuildable = [tc for tc in ids if tc not in blocked]" in src
        assert "DELETE FROM thread_context WHERE id = ANY(%s)" in src
        delete_line = src[src.index("DELETE FROM thread_context"):]
        delete_line = delete_line[: delete_line.index("\n")]
        assert "rebuildable" in src[src.index("DELETE FROM thread_context") - 200:], (
            "the delete must take the filtered list, never `ids`"
        )
        del delete_line

    def test_each_excluded_context_is_named_rather_than_counted(self):
        # "2 excluded" tells nobody which evidence is still wrong.
        assert "for tc in sorted(blocked):" in self._src()

    def test_it_says_why_they_cannot_simply_be_rebuilt(self):
        src = self._src()
        assert "offset cannot be recomputed" in src

    def test_dry_run_is_not_the_default_but_apply_is_explicit(self):
        src = self._src()
        assert "required=True" in src, "neither mode should be implicit"
        assert '"--dry-run"' in src and '"--apply"' in src

    def test_it_verifies_its_own_work_in_the_same_run(self):
        # A rebuild that reports success while leaving envelopes behind is the
        # defect wearing a green tick.
        src = self._src()
        assert "verify:" in src
        assert "unexpected" in src

    def test_it_assembles_only_the_sources_it_deleted_from(self):
        # Calling the assembler for every platform would create contexts for
        # documents nobody asked about, and each new context is work the next
        # fetch pays a model to read.
        src = self._src()
        assert "touched = sorted({src for tc, src in envelope if tc in set(rebuildable)})" in src


def test_the_docstring_states_it_spends_nothing():
    # The operator needs to know this before running it against a shared
    # database, and it is the first question anybody asks.
    doc = _module().__doc__ or ""
    assert "NO SPEND" in doc.upper()
