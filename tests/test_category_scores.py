"""The category score on Compare: CLAUDE.md rule 3's second exception.

The rule permits ONE visible score under six conditions. The arithmetic is
pinned here against judge/category_scores.py, the contract reader against
judge/config.py, and the conditions that live on the page against the source
of web/src/routes/Compare.jsx, the way the page's other tests read it.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from judge import config
from judge.category_scores import score_categories
from judge.store.board_entries import _wilson_lower

ROOT = pathlib.Path(__file__).resolve().parents[1]

LEAVES = {
    "best_for": {"coding": "software-development"},
    "capability": {"code-quality": "software-engineering", "hallucination": "safety-and-honesty"},
    "metric": {"swe-bench": "coding-benchmarks"},
}
CFG = {
    "min_sided_reports": 3,
    "scored_sections": frozenset({"best_for", "capability"}),
    "categories": [
        {"key": "coding", "name": "Coding and software"},
        {"key": "reliability", "name": "Reliability and safety"},
    ],
    "parent_to_category": {
        ("best_for", "software-development"): "coding",
        ("capability", "software-engineering"): "coding",
        ("metric", "coding-benchmarks"): "coding",
        ("capability", "safety-and-honesty"): "reliability",
    },
}


def _cat(rows, key="coding"):
    return next(c for c in score_categories(rows, CFG, LEAVES, 1.96) if c["key"] == key)


# ── the arithmetic ───────────────────────────────────────────────────────────


def test_three_positive_reports_score_the_wilson_bound():
    rows = [("capability", "code-quality", None, f"d{i}", "positive") for i in range(3)]
    c = _cat(rows)
    assert c["state"] == "scored" and c["score"] == round(100 * _wilson_lower(3, 3, 1.96)) == 44


def test_a_report_counts_once_however_many_entries_it_filed():
    rows = [
        ("capability", "code-quality", None, "d1", "positive"),
        ("best_for", "coding", None, "d1", "positive"),
        ("capability", "code-quality", None, "d2", "positive"),
        ("capability", "code-quality", None, "d3", "negative"),
    ]
    c = _cat(rows)
    assert (c["reports"], c["positive"], c["negative"], c["sided"]) == (3, 2, 1, 3)


def test_one_report_can_be_both_and_the_identity_holds():
    rows = [
        ("capability", "code-quality", None, "d1", "positive"),
        ("capability", "code-quality", None, "d1", "negative"),
        ("capability", "code-quality", None, "d2", "neutral"),
    ]
    c = _cat(rows)
    assert c["both"] == 1
    assert c["positive"] + c["negative"] - c["both"] + c["neutral"] == c["reports"]


def test_a_metric_rows_polarity_is_never_scored():
    """The contract: metric rows are shown as reports and move no score."""
    rows = [("metric", "swe-bench", None, f"d{i}", "positive") for i in range(5)]
    c = _cat(rows)
    assert (c["positive"], c["neutral"], c["state"], c["score"]) == (0, 5, "too_few", None)


def test_below_the_minimum_there_is_no_score_not_a_low_one():
    rows = [
        ("capability", "code-quality", None, "d1", "positive"),
        ("capability", "code-quality", None, "d2", "negative"),
    ]
    c = _cat(rows)
    assert c["state"] == "too_few" and c["score"] is None


def test_no_reports_is_its_own_state():
    c = _cat([])
    assert c["state"] == "none" and c["score"] is None and c["reports"] == 0


def test_a_leaf_with_no_contract_parent_uses_a_real_proposed_heading():
    rows = [("capability", "new-leaf", "safety-and-honesty", f"d{i}", "negative") for i in range(3)]
    assert _cat(rows, "reliability")["negative"] == 3
    junk = [("capability", "new-leaf", "not-a-heading", "d1", "negative")]
    assert _cat(junk, "reliability")["state"] == "none"


def test_categories_come_back_in_contract_order():
    assert [c["key"] for c in score_categories([], CFG, LEAVES, 1.96)] == ["coding", "reliability"]


# ── the contract reader ─────────────────────────────────────────────────────


def test_the_real_contract_covers_every_parent_once():
    config.category_scores.cache_clear()
    cfg = config.category_scores()
    parents = {(s, p) for s, m in config.slug_parents().items() for p in set(m.values())}
    assert set(cfg["parent_to_category"]) == parents
    assert len(cfg["categories"]) <= 8


def _with_contract(monkeypatch, data):
    real = config._read
    monkeypatch.setattr(config, "_read", lambda n: data if n == "category_scores.yaml" else real(n))
    config.category_scores.cache_clear()


@pytest.fixture(autouse=True)
def _fresh():
    yield
    config.category_scores.cache_clear()


def test_a_missing_minimum_is_refused(monkeypatch):
    _with_contract(monkeypatch, {"scored_sections": ["capability"], "categories": {"a": {}}})
    with pytest.raises(ValueError, match="min_sided_reports"):
        config.category_scores()


def test_a_parent_in_two_categories_is_refused(monkeypatch):
    twice = {"parents": {"capability": ["software-engineering"]}}
    _with_contract(
        monkeypatch,
        {
            "min_sided_reports": 3,
            "scored_sections": ["capability"],
            "categories": {"a": twice, "b": twice},
        },
    )
    with pytest.raises(ValueError, match="in both"):
        config.category_scores()


def test_a_parent_that_is_no_heading_is_refused(monkeypatch):
    _with_contract(
        monkeypatch,
        {
            "min_sided_reports": 3,
            "scored_sections": ["capability"],
            "categories": {"a": {"parents": {"capability": ["made-up"]}}},
        },
    )
    with pytest.raises(ValueError, match="not a capability heading"):
        config.category_scores()


# ── the page: rule 3's conditions that live in the markup ───────────────────

SRC = (ROOT / "web" / "src" / "routes" / "Compare.jsx").read_text(encoding="utf-8")
CODE = "\n".join(
    ln
    for ln in re.sub(r"/\*[\s\S]*?\*/", "", SRC).splitlines()
    if not ln.strip().startswith(("//", "*"))
)


def test_the_counts_sit_beside_every_score():
    cell = CODE.split("function ScoreCell")[1].split("\nfunction ")[0]
    assert "{c.positive} positive · {c.negative} negative · {c.neutral} neutral" in cell
    scored = cell.split("cs-score")[1]
    assert "{counts}" in scored


def test_too_few_and_none_read_differently():
    assert "Too few reports to score" in CODE and "No reports" in CODE


def test_the_page_says_what_the_score_is_and_is_not():
    assert "It is not a benchmark" in CODE
    assert "not comparable with each other" in CODE


def test_the_page_no_longer_says_never_scored():
    """@parvathibntglobal on #541: the wording changes with the scores."""
    assert "never scored" not in CODE.lower()


def test_the_minimum_is_read_from_the_payload_not_typed():
    assert "method.min_sided_reports" in CODE
    assert "Below 3 reports" not in CODE


def test_an_unpublished_spec_is_said_never_zero_or_no():
    specs = CODE.split("const SPEC_ROWS")[1].split("function PriceAndSpecs")[0]
    assert specs.count("'Not published'") >= 5
    assert "yesNo = (v) => (v == null ? 'Not published'" in CODE


def test_the_metrics_block_is_gone():
    assert "SameTest" not in CODE and "sameTests" not in CODE
    assert "CommonAxes" not in CODE


def test_no_cell_is_marked_the_winner():
    """Carried over from the shared-axes table's tests (removed with it,
    2026-10-19). CHECKED AS A MECHANISM, NOT A WORD: marking a winner needs one
    model's figure compared against another's inside the grid, so that is what
    is refused - in the score grid and in the specs grid alike."""
    # PriceAndSpecs, ScoreCell and CategoryScores, in file order.
    grids = CODE.split("const SPEC_ROWS")[1].split("function shortName")[0]
    assert "function PriceAndSpecs" in grids and "function CategoryScores" in grids
    for shape in ("Math.max", "Math.min", ".sort((", "> other", ">= other"):
        assert shape not in grids, f"{shape} in a comparison grid: a cell is being ranked"


def test_the_page_says_what_a_bigger_number_is_not():
    assert "A bigger number is more writing, not a better model" in CODE
    assert "not whether it was right" in CODE

