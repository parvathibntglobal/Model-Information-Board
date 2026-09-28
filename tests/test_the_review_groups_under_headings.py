"""The admin review list groups axes under the board's own headings.

Asked for after `contract/slug_parents.yaml` landed (#416, #420, #425): the
board renders parents, the review panel did not, and a reviewer hunting a
duplicate was reading a different arrangement from the one the board shows.

⚠ THE POINT IS THAT BOTH SURFACES READ ONE MAP. A pair of slugs that sits
  adjacent on the board and thirty rows apart in the review is a pair nobody
  finds — and finding duplicates is the only thing this panel is for.

⚠ AND A HEADING IS NOT A MERGE PROPOSAL, which matters more here than on the
  board because THIS IS THE PAGE WITH THE MERGE BUTTON. `osworld-2` and
  `osworld-verified` share a heading and are different measurements. The panel
  says so under every heading it draws.

Measured against staging 2026-09-23, which is also why the counts live in the
payload rather than in this file (rule 11):

    capability   8 headings over 179 of 202 axes, 23 unfiled
    metric       6 headings over 116 of 146 axes, 30 unfiled
    best_for     0 headings — deliberately unmapped, see #412
"""

from __future__ import annotations

import pathlib
import re

from judge.board_grouping import parent_of
from judge.config import parent_heading

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "judge" / "app.py"
PANEL = ROOT / "web" / "src" / "components" / "BoardReview.jsx"


def endpoint() -> str:
    src = APP.read_text(encoding="utf-8")
    start = src.index("def admin_board_entries()")
    return src[start:src.index("@app.post", start)]


class TestThePayloadCarriesTheSameMapTheBoardReads:
    def test_each_group_gets_its_parent_and_the_display_name(self):
        body = endpoint()
        assert 'g["parent"] = parent_of(g["slug"], section=g["section"])' in body
        assert 'g["parent_name"] = parent_heading(g["parent"]) if g["parent"] else None' in body

    def test_it_reads_the_shared_map_rather_than_its_own(self):
        """⚠ TWO MAPS WOULD DRIFT AND THE DRIFT WOULD BE INVISIBLE. The board
        and the review would each be right about their own arrangement and the
        reviewer would be comparing against a layout no reader sees."""
        body = endpoint()
        assert "from judge.board_grouping import coverage, parent_of" in body
        assert "from judge.config import parent_heading" in body

    def test_coverage_is_computed_per_request(self):
        """Rule 11. The proposal behind `slug_parents.yaml` went stale three
        times in 47 minutes, and this list grows with every extraction run."""
        body = endpoint()
        assert '"parent_coverage": {' in body
        assert "coverage([g for g in groups if g[\"section\"] == sec], section=sec)" in body

    def test_an_unmapped_slug_gets_none_and_not_a_catch_all(self):
        """Rule 6. `slug_parents.yaml` has no `other` parent on purpose: an
        unfiled slug is one nobody has filed, which is a different fact from
        one ruled to belong nowhere."""
        assert parent_of("a-slug-nobody-has-ever-filed", section="capability") is None

    def test_a_real_slug_resolves_to_a_display_heading(self):
        parent = parent_of("reasoning", section="capability")
        assert parent, "the map lost `reasoning`"
        heading = parent_heading(parent)
        assert heading and heading != parent, (
            "a heading rendered as its slug would read as machine text beside "
            "title-cased leaf names"
        )


class TestTheHeadingSaysItIsNotAMerge:
    def test_every_heading_carries_that_sentence(self):
        src = PANEL.read_text(encoding="utf-8")
        assert "never a proposal to merge what is under it" in src

    def test_the_unfiled_group_says_it_is_not_a_category(self):
        src = PANEL.read_text(encoding="utf-8")
        assert "Not under a heading" in src
        assert "not a category" in src

    def test_no_catch_all_parent_is_invented_in_the_ui(self):
        """⚠ THE ONE SHAPE THAT WOULD UNDO THE SERVER'S CARE. `parent_of`
        returns None and the panel must not turn that into a bucket named
        `Other` — `extraction.faithfulness` took twelve facial-recognition
        claims without complaint, and a catch-all is how that happens."""
        src = PANEL.read_text(encoding="utf-8")
        text = re.sub(r"/\*[\s\S]*?\*/", "", src)
        text = "\n".join(
            ln for ln in text.splitlines() if not ln.strip().startswith("//")
        )
        for banned in ("'Other'", '"Other"', "'Uncategorised'", "'Misc'"):
            assert banned not in text, f"a catch-all heading appeared: {banned}"


class TestTheHeadingsCountAxesAndNotVoices:
    def test_the_count_beside_a_heading_is_its_axis_count(self):
        """⚠ SUMMING THE AXES' REPORT COUNTS IS WRONG TWICE: it double-counts
        every document appearing under two of them, and it sums a figure that
        is already a floor."""
        src = PANEL.read_text(encoding="utf-8")
        assert "{p.rows.length} axis" in src

    def test_no_report_or_voice_total_is_rendered_on_a_heading(self):
        src = PANEL.read_text(encoding="utf-8")
        block = src[src.index("const headingRow ="):]
        block = block[:block.index("return (\n          <>")]
        for banned in ("reports", "voices", "documents", "n_eff"):
            assert banned not in block, f"a heading is summing {banned}"


class TestItDoesNotHideWhatItCannotOrganise:
    def test_a_section_with_no_headings_renders_flat(self):
        """`best_for` is deliberately unmapped (#412). Putting all 77 of its
        axes behind one dropdown with no sibling is not organisation, it is
        hiding — and it would be a regression against the list it replaced."""
        src = PANEL.read_text(encoding="utf-8")
        assert "if (!parents.length) return visible.map(renderAxis)" in src

    def test_one_axis_open_skips_the_headings_entirely(self):
        """Opening an axis replaces the list with a page about that axis. A
        heading above it would be furniture."""
        src = PANEL.read_text(encoding="utf-8")
        assert "if (openGroup) return renderAxis(openGroup)" in src

    def test_the_headings_count_what_the_filter_left(self):
        """⚠ A HEADING SAYING 33 OVER A FILTER SHOWING 4 WOULD BE TWO
        DIFFERENT POPULATIONS ON ONE ROW. The grouping runs over `visible`,
        which is already filtered."""
        src = PANEL.read_text(encoding="utf-8")
        grouping = src[src.index("const byParent = new Map()"):]
        grouping = grouping[:grouping.index("const parents =")]
        assert "visible.forEach" in grouping


class TestTheHeadingIsOperableFromAKeyboardAndAnnouncesItself:
    def test_it_is_a_button_with_aria_expanded(self):
        src = PANEL.read_text(encoding="utf-8")
        assert 'aria-expanded={isOpen}' in src
        assert 'type="button" className="axis-row"' in src
