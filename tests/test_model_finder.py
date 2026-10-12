"""The spec finder (web/src/routes/ModelFinder.jsx), 2026-10-12.

Its logic is web/src/finder/finder.js, run through node (tests/js/finder.mjs).
What is pinned is rule 6 at a filter: an unpublished value never counts as a
"no". A model is a match, an unknown (shown, naming what is missing) or ruled
out by a PUBLISHED value (counted by reason) - three outcomes, never two.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "js" / "finder.mjs"


@pytest.fixture(scope="module")
def out() -> dict:
    node = shutil.which("node")
    if node is None:
        # NOT A SKIP, as in test_seo_head_text: CI runs node.
        pytest.fail("node is required to run web/src/finder/finder.js")
    run = subprocess.run([node, str(PROBE)], capture_output=True, text=True, encoding="utf-8",
                         cwd=ROOT, check=False)
    if run.returncode != 0:
        pytest.fail(f"finder.mjs failed:\n{run.stderr}")
    return json.loads(run.stdout)


def test_no_filter_matches_everything(out):
    assert out["none"]["match"] == ["Alpha", "Bravo", "Charlie", "Delta"]
    assert out["none"]["out"] == 0


def test_an_unpublished_flag_is_unknown_not_no(out):
    t = out["tools"]
    assert t["match"] == ["Alpha", "Delta"]
    assert t["unknown"] == [["Charlie", ["Tool calling"]]]
    assert t["out"] == 1 and t["outBy"] == {"Tool calling": 1}     # Bravo published false


def test_unknown_names_every_missing_value(out):
    t = out["toolsCaching"]
    assert t["match"] == ["Alpha", "Delta"]
    assert t["unknown"] == [["Charlie", ["Tool calling", "Prompt caching"]]]
    assert t["outBy"] == {"Tool calling": 1}


def test_a_published_fail_beats_an_unknown(out):
    # Bravo: tools false (fails) and caching null - ruled out, not "might match"
    assert "Bravo" not in [n for n, _ in out["toolsCaching"]["unknown"]]


def test_context_and_price_ceilings(out):
    assert out["ctx"]["match"] == ["Alpha", "Delta"]
    assert out["ctx"]["unknown"] == [["Charlie", ["Context window"]]]
    assert out["cheap"]["match"] == ["Bravo", "Delta"]
    assert out["cheap"]["unknown"] == [["Charlie", ["Input rate"]]]
    assert out["cheap"]["outBy"] == {"Input rate": 1}


def test_reported_only_keeps_models_with_entries(out):
    # Delta carries no board summary: not counted as reported
    assert out["reported"]["match"] == ["Alpha", "Charlie"]


def test_sorts_put_unpublished_figures_last(out):
    assert out["byPrice"] == ["Bravo", "Delta", "Alpha", "Charlie"]
    assert out["byContext"] == ["Delta", "Alpha", "Bravo", "Charlie"]


def test_a_name_search_is_not_counted_as_ruling_out(out):
    q = out["query"]
    assert q["match"] == [] and q["out"] == 1   # only Delta was considered
