"""The compare page's second table: only the axes every model shares.

The table above it lists three models and compares none of them. Each cell
holds one model's own axes, so `coding-agent 7` and `coding-agent 3` sit at
different positions in two different lists and the reader aligns them by eye.
That view is kept — it is what each model was discussed on, in full — and the
comparison is a different question with its own table underneath.

⚠ EVERY MODEL, NOT MOST OF THEM, AND THAT IS THE DESIGN.

  An earlier attempt aligned on the slug across the WHOLE union and replaced
  the lists outright. It made most cells read "not reported", and an empty cell
  beside a 7 is the worst thing this page can render: a blank, a dash and a 0
  are all read as nought out of seven, when what is true is that nobody wrote
  about that model in those terms and for most axes nobody asked (rule 6).

  Restricting to axes every model carries means **every cell in this table is a
  count somebody reported**, and no cell needs a caveat. The axes held by
  some-but-not-all are counted in the note and live in the table above.

⚠ AN EMPTY TABLE HERE IS A FINDING ABOUT THE CORPUS, NOT THE MODELS. Nobody
  having written about three models on the same axis is a fact about what has
  been written. Rendering three empty columns would say "we compared them and
  found nothing", which is a different claim and a false one — so the zero case
  is a sentence instead of a table.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "web" / "src" / "routes" / "Compare.jsx"
CSS = ROOT / "web" / "src" / "styles" / "app.css"


def code() -> str:
    """The page with comments stripped.

    ⚠ THE COMMENTS DISCUSS EVERY STATE ASSERTED BELOW — "not reported", the
      empty table, the whole union — because they explain what was rejected.
      A raw search finds the reasoning and passes on a page that does the
      opposite. Sixteen times, this repository.
    """
    text = PAGE.read_text(encoding="utf-8")
    text = re.sub(r"/\*[\s\S]*?\*/", " ", text)
    return re.sub(r"//[^\n]*", " ", text)


def _common() -> str:
    """Just `CommonAxes`, where the cells are rendered."""
    src = code()
    start = src.index("function CommonAxes")
    return src[start:src.index("function Table", start)]


def _shared() -> str:
    """Just `sharedAxes`, where membership is decided."""
    src = code()
    start = src.index("function sharedAxes")
    return src[start:src.index("function CommonAxes", start)]


class TestTheOriginalViewIsStillThere:
    """⚠ THE FIRST ATTEMPT DELETED IT, and that was the wrong trade.
    `Listed` shows what one model was discussed on IN FULL, which no
    intersection can: an axis only one model carries vanishes from a shared
    table by construction, and for most models most axes are exactly that."""

    def test_the_per_model_lists_are_intact(self):
        code_ = code()
        assert "<Listed unit=\"job\"" in code_
        assert "<Listed unit=\"capability\"" in code_
        assert "<Listed unit=\"metric\"" in code_

    def test_the_plural_map_is_still_there(self):
        """"15 capabilitys" was on the page. `unit + "s"` is not English and
        the unit it breaks on is the one with the most rows."""
        assert "capability: 'capabilities'" in code()


class TestMembershipIsEveryModel:
    def test_an_axis_needs_every_model_to_qualify(self):
        body = _shared()
        assert "models.every((m) => r.per[m.model_version_id])" in body, (
            "membership is no longer 'every model'. At 'some' this table "
            "acquires empty cells, and an empty cell beside a count reads as "
            "a zero the board never measured."
        )

    def test_it_is_keyed_on_the_slug_not_the_name(self):
        """`name` is the extractor's phrasing and differs between models for
        one slug; the slug is what the store groups by, so a reviewer merging
        two slugs merges these rows with it."""
        assert "it.slug || it.name" in _shared()

    def test_no_cell_can_say_not_reported(self):
        """⚠ THE POINT OF THE WHOLE RESTRICTION, asserted directly. If this
        string ever appears, membership has loosened and the table has started
        rendering absences as data."""
        assert "not reported" not in code()


class TestTheCountsTravelWithTheirDenominator:
    def test_the_shared_count_is_shown_against_the_total(self):
        """Rule 7. "4 shared" means one thing out of 12 and another out of
        200, and this table's whole worth is which of those it is."""
        code_ = code()
        assert "{shared}" in code_ and "{named}" in code_

    def test_each_group_states_its_own_split(self):
        assert "{g.every.length} of {g.total} shared" in code()

    def test_a_figure_keeps_its_basis(self):
        """`stated` is the vendor's claim, `reported` is somebody's
        measurement, and a figure without its basis merges the two."""
        assert "{f.value} {f.basis}" in code()


class TestTheEmptyCaseIsASentence:
    def test_no_table_is_rendered_when_nothing_is_shared(self):
        code_ = code()
        assert "shared === 0 ?" in code_, (
            "the zero case no longer branches; three empty columns say 'we "
            "compared them and found nothing', which is false"
        )
        assert "No axis is shared by all" in code_

    def test_it_says_the_absence_is_about_the_writing(self):
        """⚠ RULE 6 AND RULE 4 IN ONE SENTENCE. "Nothing to compare" reads as
        a verdict on the models unless the page says whose absence it is."""
        assert "not about the models" in code()


class TestNoWinnerIsMarked:
    def test_no_cell_is_styled_from_a_comparison(self):
        """⚠ CHECKED AS A MECHANISM, NOT AS A WORD. Searching the page for
        "best" or "winner" finds `best_for`, the stored section key, and the
        sentence that PROMISES no winner is picked - so a word search fails on
        a correct page and would pass on one that highlighted the larger cell
        with a class called `.hi`.

        What marking a winner requires is comparing one model's count against
        another's inside the table, so that is what is refused.
        """
        body = _common()
        for shape in ("Math.max", "Math.min", ".sort((", "> other", ">= other"):
            assert shape not in body, (
                f"{shape} appears in the shared-axes table: a cell is being "
                f"compared against another model's, which is how a winner "
                f"gets marked. The counts are shown and not ranked."
            )

    def test_the_page_says_what_a_higher_count_is_not(self):
        """A bigger number is more reports. It tracks how widely something is
        used at least as much as how well it works, and the polarity of those
        reports is not on this table at all."""
        assert "A higher count is more reports, not a better model" in code()


class TestTheAxisNameCanWrap:
    def test_the_label_column_does_not_force_nowrap(self):
        """The fixed labels above are short and must not break, hence
        `tbody th{white-space:nowrap}`. An extractor-written axis name in that
        same column runs long — `unauthorized-data-exfiltration` — and left to
        nowrap it squeezes the model columns the table exists to compare."""
        css = CSS.read_text(encoding="utf-8").replace(" ", "")
        rule = re.search(r"\.cmp-tabletr\.cmp-axisth\{([^}]*)\}", css)
        assert rule, ".cmp-axis is gone from app.css"
        assert "white-space:normal" in rule.group(1)
