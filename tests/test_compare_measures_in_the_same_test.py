"""Compare shows metric figures only where one test measured several of the
models (2026-10-15), and no longer shows a quote per model.

A figure from one engineer's test and a figure from another's measured
different tasks, so lining them up reads as a comparison they are not. And a
figure a post only quotes from a provider is a claim, not a measurement. Both
rules live in `sameTests`; these checks pin them in the source, the same way
the page's other tests do.
"""

from __future__ import annotations

import pathlib
import re

SRC = (
    pathlib.Path(__file__).resolve().parents[1] / "web" / "src" / "routes" / "Compare.jsx"
).read_text(encoding="utf-8")
CODE = "\n".join(
    ln
    for ln in re.sub(r"/\*[\s\S]*?\*/", "", SRC).splitlines()
    if not ln.strip().startswith(("//", "*"))
)


def test_the_quote_per_model_is_gone():
    assert "FaceOff" not in CODE and "quoteFor" not in CODE
    assert "In their words" not in CODE


def test_only_measured_figures_are_lined_up():
    assert "f.basis === 'reported' ? byKey : quotedOnly" in CODE


def test_a_row_is_one_post_that_measured_at_least_two_of_the_models():
    assert "Object.keys(r.per).length >= 2" in CODE
    assert "`${it.slug}|${f.document_id}`" in CODE


def test_the_page_says_what_it_left_out():
    assert "Figures from separate tests are left out" in SRC
    assert "claims, not measurements" in SRC


def test_metrics_are_not_also_counted_in_the_shared_sections_table():
    assert "SECTIONS.filter(([section]) => section !== 'metrics')" in CODE
