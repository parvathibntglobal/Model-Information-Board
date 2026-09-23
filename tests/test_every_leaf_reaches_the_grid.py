"""Every leaf reaches the grid, and lands where it belongs. #428.

WHY THIS FILE IS NOT IN `test_the_board_renders_its_parents.py`. Those 28 tests
search the SOURCE of `views.js`. They are the right tool for what a builder
says - that a heading carries `leaves` and no other count, that the tail is
`until-found` and not `display:none` - and the wrong tool for where a card ends
up, which is why all 28 passed over #428.

#428 in one line: `parentHead` returned `</div>...<div class="igrid">`, closing
the caller's grid and opening one nothing closed. So the grid a card landed in
was whichever heading had opened one last, and EVERY ungrouped leaf was drawn
inside the grid of the heading above it - 37 capability and 32 metric leaves on
2026-09-23, none at the top level, with 35 of the 37 under a single "Writing and
language" whose own heading printed a smaller leaf count directly above them.
The source line responsible for ungrouped leaves read `return draw(g.leaf)`
throughout and was never wrong.

⚠ AND THE OBVIOUS TEST DOES NOT CATCH IT, WHICH IS WHY THERE ARE TWO CLASSES
  BELOW. "Every leaf appears in the rendered grid exactly once" passed against
  the broken page: all 215 capability cards and all 120 metric cards were in the
  DOM exactly once the whole time. It is kept because it guards a real and
  different failure - `regroup` drops a leaf whose slug is not in the flat list,
  by design, and nothing else watches that - but the assertion that SEES #428 is
  containment: which grid, under which heading.

So this renders the real `vBoard` through `node` and parses the result.
`tests/js/board_render.mjs` does the rendering and the reporting; every
judgement about what the answer should be is here.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from judge import board_grouping

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "js" / "board_render.mjs"

#: A fixture map rather than `contract/slug_parents.yaml`, so this file does not
#: fail the day somebody re-files a slug. Leaves stand in their own rank BEFORE
#: the first heading, BETWEEN the two, and AFTER the last - because #428 was
#: harmless in the first position and fatal in the other two, and a fixture with
#: only a leading ungrouped leaf would have passed against the broken build.
PARENTS = {
    "capability": {
        # `alpha` deliberately carries more children than `LEAF_PREVIEW` (6), so
        # the folded tail is exercised: the tail and its button belong INSIDE
        # the heading's grid, and an ungrouped leaf after them does not.
        "a-1": "alpha", "a-2": "alpha", "a-3": "alpha", "a-4": "alpha",
        "a-5": "alpha", "a-6": "alpha", "a-7": "alpha", "a-8": "alpha",
        "b-1": "beta", "b-2": "beta",
    },
    "metric": {"m-1": "mu", "m-2": "mu"},
}
NAMES = {"alpha": "Alpha things", "beta": "Beta things", "mu": "Mu things"}

CAPS = ["free-1", "a-1", "a-2", "a-3", "a-4", "a-5", "a-6", "a-7", "a-8",
        "free-2", "b-1", "b-2", "free-3", "free-4"]
METS = ["n-1", "m-1", "m-2", "n-2"]


def _item(slug: str) -> dict:
    """One board row, carrying every field the adapter reads and no evidence."""
    return {
        "slug": slug,
        "name": slug.replace("-", " ").title(),
        "definition": f"What {slug} means.",
        "reports": 3,
        "voices": 2,
        "quotes": [],
        "models": [],
        "figures": [],
        "suppressed_models": [],
        "unit": "%",
        "spelled_also": [],
    }


@pytest.fixture(scope="module")
def rendered(tmp_path_factory) -> dict:
    """The real board, rendered by node, reported as cards-with-their-heading."""
    node = shutil.which("node")
    if node is None:
        # NOT A SKIP. CI runs `npx oxlint` against this same repo, so node is
        # present wherever this matters, and a skip on the one test that can see
        # a layout defect would read as success - the failure mode rule 4 names.
        pytest.fail("node is required to render the board; install it or fix PATH")

    sections = {
        "best_for": [],
        "capability": [_item(s) for s in CAPS],
        "metric": [_item(s) for s in METS],
    }
    # The REAL grouper over the fixture map, so the payload this renders is the
    # shape `judge/app.py` serves rather than one written out by hand here.
    orig_map, orig_name = board_grouping.slug_parents, board_grouping.parent_heading
    board_grouping.slug_parents = lambda: PARENTS
    board_grouping.parent_heading = lambda p: NAMES[p]
    try:
        grouped = {
            "jobs": board_grouping.group_section(sections["best_for"], section="best_for"),
            "caps": board_grouping.group_section(sections["capability"], section="capability"),
            "mets": board_grouping.group_section(sections["metric"], section="metric"),
        }
    finally:
        board_grouping.slug_parents, board_grouping.parent_heading = orig_map, orig_name

    payload = {
        "jobs": sections["best_for"],
        "caps": sections["capability"],
        "mets": sections["metric"],
        "grouped": grouped,
        "metrics_withheld": {},
        "parent_coverage": {},
        "posts": [],
    }
    path = tmp_path_factory.mktemp("board") / "payload.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    out = subprocess.run(
        [node, str(PROBE), str(path)],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )
    if out.returncode != 0:
        sys.stdout.write(out.stdout)
        pytest.fail(f"board_render.mjs failed:\n{out.stderr}")
    return json.loads(out.stdout)


def _drawn(pane: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for c in pane["cards"]:
        counts[c["slug"]] = counts.get(c["slug"], 0) + 1
    return counts


class TestEveryLeafReachesTheGrid:
    """The count. Kept although it did not catch #428 - see the module docstring.

    What it does catch is a leaf silently dropped between the flat list and the
    grid, which `regroup` is built to do on a slug the flat list does not carry.
    """

    @pytest.mark.parametrize("tab", ["cap", "met"])
    def test_every_leaf_is_drawn(self, rendered, tab):
        pane = rendered[tab]
        missing = sorted(set(pane["flat"]) - set(_drawn(pane)))
        assert not missing, f"{tab}: in the payload and not on the page: {missing}"

    @pytest.mark.parametrize("tab", ["cap", "met"])
    def test_no_leaf_is_drawn_twice(self, rendered, tab):
        twice = sorted(s for s, n in _drawn(rendered[tab]).items() if n > 1)
        assert not twice, f"{tab}: drawn more than once: {twice}"

    @pytest.mark.parametrize("tab", ["cap", "met"])
    def test_the_page_draws_nothing_the_payload_does_not_have(self, rendered, tab):
        pane = rendered[tab]
        extra = sorted(set(_drawn(pane)) - set(pane["flat"]))
        assert not extra, f"{tab}: on the page and not in the payload: {extra}"


class TestALeafLandsUnderItsOwnHeadingOrNone:
    """THE CLASS THAT SEES #428. Presence was never the question; grids were.

    Run against `78e7a1d` the first of these fails with 37 of 37 capability and
    32 of 32 metric leaves filed under a heading, while the count class above
    passes untouched.
    """

    @pytest.mark.parametrize("tab", ["cap", "met"])
    def test_an_ungrouped_leaf_is_under_no_heading(self, rendered, tab):
        pane = rendered[tab]
        ungrouped = set(pane["ungrouped"])
        assert ungrouped, f"{tab}: the fixture must carry ungrouped leaves to test"
        misfiled = {c["slug"]: c["under"] for c in pane["cards"]
                    if c["slug"] in ungrouped and c["under"] is not None}
        assert not misfiled, (
            f"{tab}: {len(misfiled)} of {len(ungrouped)} leaves with no parent were drawn "
            f"inside a heading's grid, which renders them as that heading's: {misfiled}"
        )

    @pytest.mark.parametrize("tab", ["cap", "met"])
    def test_a_grouped_leaf_is_under_its_own_heading(self, rendered, tab):
        pane = rendered[tab]
        owner = {slug: head for head, slugs in pane["grouped"].items() for slug in slugs}
        wrong = {c["slug"]: (c["under"], owner[c["slug"]]) for c in pane["cards"]
                 if c["slug"] in owner and c["under"] != owner[c["slug"]]}
        assert not wrong, f"{tab}: drawn under the wrong heading (got, wanted): {wrong}"

    def test_the_folded_tail_stays_inside_its_own_heading(self, rendered):
        """A parent longer than the preview keeps all its leaves, tail included.

        The tail is `hidden="until-found"` and still inside the heading's grid;
        an ungrouped leaf drawn after the fold button is not, and telling those
        two apart is the whole of this file.
        """
        pane = rendered["cap"]
        alpha = pane["grouped"]["Alpha things"]
        assert len(alpha) > 6, "the fixture must exceed LEAF_PREVIEW to fold"
        under = {c["slug"] for c in pane["cards"] if c["under"] == "Alpha things"}
        assert under == set(alpha), (
            f"folding changed what is under the heading: extra={under - set(alpha)}, "
            f"lost={set(alpha) - under}"
        )

    def test_only_a_heading_longer_than_the_preview_folds(self, rendered):
        """Eight leaves fold; two do not. Asserted by rendering, because the
        source-text version of this pinned a spelling and broke on #428's fix.

        `LEAF_PREVIEW` is not restated here - the fixture is 8, 2 and 2, which
        straddles any preview between 2 and 7, and a test naming the constant
        would only check that the constant equals itself.
        """
        pane = rendered["cap"]
        folded = set(pane["folds"])
        long_ones = {p for p, slugs in pane["grouped"].items() if len(slugs) > 6}
        assert long_ones == {"Alpha things"}, "the fixture changed shape"
        assert folded == {"alpha"}, (
            f"folded {sorted(folded)}; only headings longer than the preview should"
        )

    def test_a_tab_with_no_parents_renders_every_leaf_at_the_top_level(self, rendered):
        """`best_for` is deliberately unmapped (#412) and must stay ungrouped."""
        pane = rendered["best"]
        assert not pane["headings"], f"best_for grew headings: {pane['headings']}"
        assert all(c["under"] is None for c in pane["cards"])
