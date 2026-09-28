"""Three tabs on the model page, and the property the stack was protecting.

Jobs, Capabilities and Metrics were three headings stacked down one panel. They
are now three tabs, which reads better and puts one guarantee at risk.

⚠ THE STACK MADE AN ABSENCE FREE TO SEE. Every section rendered, including the
  empty ones, because omitting an empty section made "nothing said about jobs
  yet" indistinguishable from "this board has no jobs section" — rule 4 applied
  to the page's own structure, and the panel's own comment says so.

  A TAB HIDES WHAT IT IS NOT SHOWING. Behind an unselected tab, an empty section
  and a section that does not exist look identical, and finding out costs a
  click the reader has no reason to make.

  `Metrics 0` on the tab is the whole fix, which is why these tests care about
  the count far more than about the tabs:

      Jobs 12    Capabilities 3    Metrics 0
                                          ^ the absence, before any click

  So the count must be unconditional. A count suppressed at zero — the obvious
  tidy-up, and the one somebody will make — restores exactly the defect the
  stacked version was built to avoid, while looking like a cleaner bar.

⚠ AND THE OPENING TAB IS CHOSEN FROM THE DATA. A fixed default lands a reader
  on "Nothing named here yet" for a model with 29 entries one tab across. That
  is safe ONLY because every count is already on the bar; the two rules hold
  each other up, so neither is checked alone here.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PANEL = ROOT / "web" / "src" / "components" / "ModelEvidence.jsx"


def _code() -> str:
    """The component with comments stripped.

    The file explains the tab change at length, quoting the states it is
    guarding against, so a raw search matches the reasoning rather than the
    render. Sixteen times, this repository.
    """
    text = PANEL.read_text(encoding="utf-8")
    text = re.sub(r"/\*[\s\S]*?\*/", " ", text)
    return re.sub(r"//[^\n]*", " ", text)


class TestTheThreeTabsAreTheThreeSections:
    def test_the_sections_and_their_labels(self):
        code = _code()
        for key, title in (("best_for", "Jobs"),
                           ("capabilities", "Capabilities"),
                           ("metrics", "Metrics")):
            assert re.search(rf"\['{key}',\s*'{title}'", code), (
                f"the {key} section is no longer labelled {title!r}. `best_for` "
                f"is the stored key everywhere and 'Jobs' is the word readers "
                f"see (#474); the two are deliberately different and both have "
                f"to stay."
            )

    def test_every_section_becomes_a_tab(self):
        """The bar is built from SECTIONS, not typed out. Typed tabs and a
        rendered body drift, and the drift shows as a tab that leads nowhere."""
        code = _code()
        assert re.search(r"tabs\s*=\s*SECTIONS\.map", code), (
            "the tab bar no longer derives from SECTIONS, so a section could "
            "exist with no tab to reach it"
        )


class TestTheCountIsNeverSuppressed:
    """⚠ THE LOAD-BEARING TEST IN THIS FILE."""

    def test_the_tab_renders_its_count(self):
        code = _code()
        assert re.search(r"<span className=\"x\">\{t\.items\.length\}</span>", code), (
            "the tab no longer shows its entry count. Without it an empty "
            "section is invisible until clicked, which is the defect the "
            "stacked version existed to prevent."
        )

    def test_the_count_is_not_conditional(self):
        """The tidy-up that reintroduces the bug: hiding a zero.

        `Metrics 0` looks like clutter and is the single most useful thing on
        the bar — it is the only place an absence is stated before a click.
        """
        code = _code()
        assert not re.search(r"t\.items\.length\s*>\s*0\s*&&\s*<span className=\"x\"", code), (
            "the tab count is now conditional on being non-zero, so a section "
            "with nothing in it renders identically to one that does not exist"
        )

    def test_an_empty_tab_still_explains_itself(self):
        code = _code()
        assert "Nothing named here yet." in code, (
            "a selected empty tab renders nothing at all, so a reader who "
            "clicks it cannot tell the panel apart from a broken one"
        )


class TestTheOverflowOpens:
    """⚠ A COUNT THAT NAMES WHAT IT WITHHOLDS AND OFFERS NO WAY IN is a dead
    end, and it was rejected in this same shape on the compare page. The quotes
    ARE this panel — every one verified by exact substring — so "+3 more" has
    to open."""

    def test_the_extra_quotes_are_reachable(self):
        code = _code()
        assert "<details>" in code, "the quote overflow is not openable"
        assert re.search(r"it\.quotes\.slice\(QUOTES_SHOWN\)", code), (
            "the disclosure does not render the remaining quotes"
        )

    def test_both_halves_render_through_one_component(self):
        """⚠ THE CONTROL ON THE TEST ABOVE. Two copies of the quote markup is
        how the opened half loses the source link — and a quote without its
        link is the one thing this panel cannot afford, since checking it
        against what the person wrote is the entire point."""
        code = _code()
        assert len(re.findall(r"<Quote key=\{i\} q=\{q\} />", code)) == 2, (
            "the first quotes and the overflow are no longer rendered by the "
            "same component"
        )
        assert code.count("open the source") == 1, (
            "the source link is written out more than once, so the two halves "
            "can drift"
        )
