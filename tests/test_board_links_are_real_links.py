"""Every board link is a real link: an <a> with the href its click navigates to.

SEO item 3, 2026-10-08. The board's views emitted `data-go` and no `href`, so
`BoardView` turned clicks into routes and a crawler found no link at all: every
job, capability, metric and model page was reachable only by script, and
Ctrl-click, middle-click and "copy link" did nothing. Section cards and model
rows were not even anchors - they were `<div>`s.

Rendered through node from the real `setBoardData` and views, over a payload
built by the real grouper, as test_every_leaf_reaches_the_grid does.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "js" / "board_links.mjs"

MODEL = "anthropic/claude-opus-4.6"


def _item(slug: str, *, models=()) -> dict:
    return {
        "slug": slug, "name": slug.replace("-", " ").title(), "definition": f"What {slug} means.",
        "reports": 3, "voices": 2, "quotes": [], "figures": [], "suppressed_models": [],
        "unit": "%", "spelled_also": [],
        "models": [{"model_version_id": m, "model_label": m.split("/")[-1],
                    "reports": 2, "voices": 2} for m in models],
    }


@pytest.fixture(scope="module")
def links(tmp_path_factory) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is required to render the board; install it or fix PATH")
    payload = {
        "jobs": [_item("code-review", models=[MODEL, "mv_0123456789abcdef"])],
        "caps": [_item("tool-use", models=[MODEL]), _item("long-context")],
        "mets": [_item("cost-per-token", models=[MODEL])],
        "metrics_withheld": {}, "parent_coverage": {}, "posts": [],
    }
    path = tmp_path_factory.mktemp("board") / "payload.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    run = subprocess.run([node, str(PROBE), str(path), "tool-use", "cost-per-token", MODEL],
                         capture_output=True, text=True, encoding="utf-8", cwd=ROOT, check=False)
    if run.returncode != 0:
        pytest.fail(f"board_links.mjs failed:\n{run.stderr}")
    return json.loads(run.stdout)


def _all(links):
    return [(view, a) for view, items in links.items() for a in items]


def test_the_views_render_links_at_all(links):
    # Guards the rest: a probe that found nothing would pass every test below.
    assert len(_all(links)) >= 8
    assert any(a["cls"].startswith("icard") for _, a in _all(links))
    assert any("rank" in a["cls"] for _, a in _all(links))


def test_every_data_go_is_an_anchor_with_an_href(links):
    bad = [(v, a["tag"], a["go"]) for v, a in _all(links) if a["tag"] != "a" or not a["href"]]
    assert bad == []


def test_the_href_is_the_route_the_click_opens(links):
    # One mapping (board/links.js goPath) for both, so they cannot disagree.
    bad = [(v, a["go"], a["href"]) for v, a in _all(links) if a["href"] != a["expected"]]
    assert bad == []


def test_section_cards_and_model_rows_link_to_their_pages(links):
    hrefs = {a["href"] for _, a in _all(links)}
    assert "/board/jobs/code-review" in hrefs
    assert "/board/capabilities/tool-use" in hrefs
    assert "/board/metrics/cost-per-token" in hrefs
    assert f"/board/capabilities/tool-use/{MODEL}" in hrefs   # a model row, slash kept
    assert f"/models/{MODEL}" in hrefs                         # "everything said about"
