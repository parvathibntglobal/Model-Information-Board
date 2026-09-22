"""Two rows with the same letters say so, rather than looking like a bug.

`exploit-bench` and `exploitbench` are one benchmark and two rows on the board
review, and a reviewer reading the list saw two identical-looking sections with
nothing to say they were the same word. Measured: six groups across three
pairs — `over-thinking`/`overthinking`, `exploit-bench`/`exploitbench`,
`exploit-gym`/`exploitgym`.

⚠ FLAGGED, NOT FOLDED, AND THE DISTINCTION IS THE WHOLE DESIGN.

  `board_sections` folds these on read, because the board is a rendering. This
  panel must not, for two reasons:

    1. A ruling is keyed on `(section, slug)`. A folded row that sent one slug
       would decline half the pair and leave the other live — worse than
       showing two rows.
    2. This is the surface where a person DECIDES. Pre-merging hides the
       decision the board is asking for, and `ruling_target` exists to record
       it.

  So the row names its twin and the merge box is offered pre-filled. The
  reviewer still presses merge, and still chooses which spelling survives by
  which row they act from.
"""

from __future__ import annotations

import pathlib

from judge.store.board_entries import spelling_key

ROOT = pathlib.Path(__file__).resolve().parents[1]
STORE = ROOT / "judge" / "store" / "board_entries.py"
PANEL = ROOT / "web" / "src" / "components" / "BoardReview.jsx"


class TestTheReviewNamesTheTwin:
    def test_the_payload_carries_look_alikes(self):
        src = STORE.read_text(encoding="utf-8")
        assert '"looks_like": looks_like or None,' in src

    def test_it_is_scoped_to_one_section(self):
        """A metric and a capability that share letters are not the same
        thing, and merging across sections is not something the review can
        even do — it groups by (section, slug)."""
        src = STORE.read_text(encoding="utf-8")
        assert "by_spelling.setdefault((r[0], spelling_key(r[1])), [])" in src

    def test_a_row_never_names_itself(self):
        src = STORE.read_text(encoding="utf-8")
        assert "if x != slug" in src

    def test_it_is_absent_rather_than_empty_on_a_normal_row(self):
        """Almost every row has no twin. `None` keeps the badge off rather
        than rendering an empty list."""
        src = STORE.read_text(encoding="utf-8")
        assert "looks_like or None" in src


class TestTheReviewStillMakesThePersonDecide:
    def test_the_panel_does_not_fold_the_rows(self):
        """If this ever starts folding, a ruling declines half a pair."""
        panel = PANEL.read_text(encoding="utf-8")
        assert "spelling_key" not in panel, (
            "the review is folding slugs; a ruling is keyed on (section, slug) "
            "so a folded row would rule on only one of them"
        )

    def test_the_row_names_the_other_spelling(self):
        panel = PANEL.read_text(encoding="utf-8")
        assert "also spelled {g.looks_like.join(', ')}" in panel

    def test_the_merge_is_offered_pre_filled_but_not_applied(self):
        """It fills the box. It does not rule — the reviewer still presses
        merge, and chooses which spelling survives by which row they use."""
        panel = PANEL.read_text(encoding="utf-8")
        assert "fold into {g.looks_like[0]}" in panel
        block = panel[panel.index("fold into {g.looks_like[0]}") - 700:]
        block = block[:block.index("fold into {g.looks_like[0]}") + 40]
        assert "setMergeInto" in block
        assert "ruleBoardEntry" not in block, (
            "the pre-fill button rules directly; it must only fill the box"
        )


class TestTheFoldItselfIsUnchanged:
    def test_separators_fold_and_versions_do_not(self):
        # The property the flag depends on. If `spelling_key` ever folded a
        # version, this panel would offer to merge two real benchmarks.
        assert spelling_key("exploit-bench") == spelling_key("exploitbench")
        assert spelling_key("osworld") != spelling_key("osworld-2")
        assert spelling_key("aime") != spelling_key("aime-2026")
