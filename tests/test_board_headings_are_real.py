"""Every board page has one <h1>, real headings, and no skipped levels.

SEO item 4, 2026-10-09. The group headings on job, capability and metric pages
("Reported working", "Only neutral reports", ...) were `<p role="heading"
aria-level="3">`: a screen reader heard a heading and anything reading the tag
tree saw a paragraph, so the page's main structure was invisible to it. And
`aria-level="3"` sat straight under the <h1> on job pages, as did the job
page's "What counts here" <h3>.

Rendered through node from the real `setBoardData` and views
(tests/js/board_headings.mjs), as the other board tests do.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "js" / "board_headings.mjs"


@pytest.fixture(scope="module")
def pages() -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is required to render the board; install it or fix PATH")
    run = subprocess.run([node, str(PROBE)], capture_output=True, text=True, encoding="utf-8",
                         cwd=ROOT, check=False)
    if run.returncode != 0:
        pytest.fail(f"board_headings.mjs failed:\n{run.stderr}")
    return json.loads(run.stdout)


def test_the_probe_rendered_every_page_kind(pages):
    assert {"boardBest", "job1", "cap1", "met1", "jobModel", "capModel", "metModel"} <= set(pages)


def test_every_page_has_exactly_one_h1(pages):
    assert {k: v["levels"].count(1) for k, v in pages.items() if v["levels"].count(1) != 1} == {}


def test_no_heading_skips_a_level(pages):
    def skips(levels):
        return [(a, b) for a, b in zip(levels, levels[1:], strict=False) if b > a + 1]
    assert {k: skips(v["levels"]) for k, v in pages.items() if skips(v["levels"])} == {}


def test_no_pseudo_headings_remain(pages):
    assert {k: v["roleHeading"] for k, v in pages.items() if v["roleHeading"]} == {}


def test_groups_sit_at_the_level_their_page_needs(pages):
    # Jobs and capabilities: the list is straight under the <h1>, so groups are h2.
    assert pages["job1"]["levels"][:2] == [1, 2]
    assert pages["cap1"]["levels"] == [1, 2, 2]
    # Metrics: the list is inside "Who has been measured" (an h2), so groups are h3.
    assert pages["met1"]["levels"] == [1, 2, 3, 3]
