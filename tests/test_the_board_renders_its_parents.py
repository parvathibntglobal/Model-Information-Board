"""Parent headings on the board grid, and the three rulings made visible. #416.

    A parent groups for reading and never implies the leaves are the same
    measurement.  — contract/slug_parents.yaml

⚠ THE PROPERTY HAS TO BE VISIBLE, NOT MERELY TRUE OF THE DATA. A reader who
cannot see the leaves under a parent is reading a merge, whatever the data
says. So a parent is a HEADING on the grid and never a route: its leaves render
underneath it, without a click, as the same cards they are anywhere else.

That also keeps the drill-down at three levels — board -> category -> model. A
parent PAGE would add a fourth, and worse, it would read as a category: you
would click it, see leaves, click a leaf. That shape says the leaves are one
measurement however the prose denies it.

These tests read `web/src/board/views.js` and `db.js` as text, which is what
the rest of this suite does — there is no JS test runner in `web/`.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _views() -> str:
    return (ROOT / "web" / "src" / "board" / "views.js").read_text(encoding="utf-8")


def _db() -> str:
    return (ROOT / "web" / "src" / "board" / "db.js").read_text(encoding="utf-8")


def _fn(js: str, sig: str) -> str:
    body = js[js.index(sig) :]
    return body[: body.index(chr(10) + "}")]


class TestAHeadingCountsLeaves:
    """Ruling 1, and it is arithmetic before it is a rule: summing children
    double-counts every document under two leaves and sums a floor."""

    def test_the_heading_renders_leaves_and_no_other_count(self):
        head = _fn(_views(), "function parentHead(g){")
        assert "g.leaves" in head
        for forbidden in ("reports", "voices", "models", "quotes", "n_eff"):
            assert forbidden not in head, f"a heading carries {forbidden!r}"

    def test_the_heading_says_there_is_no_total(self):
        """A reader who wants a total should be told it does not exist rather
        than left hunting for one."""
        head = _fn(_views(), "function parentHead(g){")
        assert "no total" in head

    def test_leaves_is_what_will_be_drawn_not_what_the_payload_claimed(self):
        """If a leaf is dropped for having no flat entry, the heading must not
        still count it."""
        regroup = _fn(_db(), "  const regroup =")
        assert "leaves: children.length" in regroup


class TestTheLeavesAreVisible:
    """Her property, rendered. A reader who cannot see the leaves is reading a
    merge."""

    def test_a_parent_renders_its_children_immediately_after_the_heading(self):
        grid = _fn(_views(), "function groupedGrid(groups, flat, draw){")
        assert "parentHead(g) + g.children.map(draw).join('')" in grid

    def test_the_heading_says_the_leaves_are_not_merged(self):
        head = _fn(_views(), "function parentHead(g){")
        assert "its own measurement" in head
        assert "merged" in head

    def test_a_parent_with_no_children_is_not_rendered(self):
        """A heading over no cards claims something is there."""
        regroup = _fn(_db(), "  const regroup =")
        assert "if (!children.length) return []" in regroup


class TestAParentIsNotARoute:
    """Three levels, not four. Anything clickable reads as a category."""

    def test_the_heading_carries_no_navigation(self):
        head = _fn(_views(), "function parentHead(g){")
        assert "data-go" not in head, "a parent must not be clickable"
        assert "<a " not in head

    def test_no_route_was_added_for_a_parent(self):
        js = _views()
        assert "parent:" not in js.replace("r.parent", "").replace("g.parent", "")

    def test_a_leaf_keeps_its_own_route_under_a_heading(self):
        """Ruling 3: nothing about a leaf changes because it gained a heading.
        `groupedGrid` is handed the same `draw` the flat list uses."""
        js = _views()
        assert "groupedGrid(DB.capGroups, DB.caps, c=>card(c,'cap'))" in js
        assert "groupedGrid(DB.metGroups, DB.mets, m=>mcard(m))" in js


class TestParentsNeverRewriteLeaves:
    def test_the_flat_lists_stay_authoritative(self):
        """Every lookup on this board is by slug. A nested shape would mean two
        answers to 'what is a leaf'."""
        db = _db()
        assert "DB.caps = (d.caps || []).map(" in db
        assert "DB.mets = (d.mets || []).map(" in db

    def test_grouping_re_points_at_the_flat_objects_rather_than_copying(self):
        regroup = _fn(_db(), "  const regroup =")
        assert "bySlug.get(c.slug)" in regroup
        assert "new Map(flat.map((x) => [x.slug, x]))" in regroup

    def test_a_slug_absent_from_the_flat_list_is_dropped_not_invented(self):
        """Rendering the payload's own copy would be two leaves with one slug,
        which is the shape parents exist not to create."""
        regroup = _fn(_db(), "  const regroup =")
        assert ".filter(Boolean)" in regroup
        assert "return leaf ? [{ kind: 'leaf', leaf }] : []" in regroup


class TestUngroupedRendersAsItself:
    def test_an_ungrouped_leaf_is_drawn_with_the_same_card(self):
        grid = _fn(_views(), "function groupedGrid(groups, flat, draw){")
        assert "draw(g.leaf)" in grid

    def test_there_is_no_residual_heading(self):
        js = _views()
        for banned in (">Other<", ">Misc<", "Ungrouped</h3>", ">Everything else<"):
            assert banned not in js

    def test_an_older_payload_renders_exactly_as_before(self):
        """No `grouped` key means no groups, and the grid falls back to flat."""
        grid = _fn(_views(), "function groupedGrid(groups, flat, draw){")
        assert "if(!groups || !groups.length) return flat.map(draw).join('')" in grid


class TestCoverageIsReadNeverRemembered:
    """Rule 11. The ungrouped count read 19, 20 and 21 within one day."""

    def test_the_note_reads_the_payload(self):
        note = _fn(_views(), "function parentNote(key){")
        assert "DB.parentCoverage" in note
        for field in ("c.parents", "c.grouped", "c.leaves", "c.ungrouped"):
            assert field in note

    def test_no_coverage_figure_is_hardcoded(self):
        note = _fn(_views(), "function parentNote(key){")
        digits = re.findall(r"\b\d+\b", note)
        assert not digits, f"a literal count in the coverage note: {digits}"

    def test_the_note_is_absent_when_there_are_no_parents(self):
        """`best_for` is deliberately ungrouped; its tab must not grow a line
        about headings it does not have."""
        note = _fn(_views(), "function parentNote(key){")
        assert "if(!c || !c.parents) return ''" in note


class TestTheMetricDividerSentenceSurvived:
    """⚠ THE ONE THING THAT MUST NOT BE LOST in replacing `metGrid`.

    Parents group the metrics grid by subject; the old divider split it by
    whether an axis compares anything. Both cannot own one grid. The SPLIT is
    redundant — `mcard` has printed the model count on every card since
    2026-09-21 — but the SENTENCE is rule 4 content: an axis holding one model
    is a real recorded figure, not a comparison that failed.
    """

    def test_the_sentence_is_on_the_metrics_tab(self):
        js = _views()
        met = js[js.index("met: {intro:") :]
        met = met[: met.index("grid:")]
        assert "single model" in met
        assert "none of them is a comparison" in met

    def test_the_card_still_carries_the_model_count(self):
        """What makes the split redundant, and it is checked rather than
        assumed."""
        card = _fn(_views(), "function mcard(x){")
        assert "(x.mrows || []).length" in card
