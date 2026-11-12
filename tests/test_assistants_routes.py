"""The AI assistants page is reachable (2026-11-12, PROPOSED): in the Models menu,
routed top-level, and public on the backend. Routing lives in JSX node cannot
render without React, so these pin the source, as the repo's other routing
tests do. No database."""
from __future__ import annotations

from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web" / "src"


def _read(rel: str) -> str:
    return (WEB / rel).read_text(encoding="utf-8")


def test_the_models_menu_links_the_page_with_its_label_and_note():
    nav = _read("components/Nav.jsx")
    assert "{ to: '/ai-assistants', label: 'AI assistants', " in nav
    assert "Assistants that work for you, with you, or code with you" in nav


def test_the_list_and_the_detail_are_one_top_level_route_before_the_catch_all():
    app = _read("App.jsx")
    route = '<Route path="/ai-assistants/*" element={<Assistants />} />'
    assert route in app
    assert app.index(route) < app.index('<Route path="*"')


def test_the_page_names_no_quote_field_and_links_the_signed_in_evidence():
    page = _read("routes/Assistants.jsx")
    assert "See the quoted evidence" in page
    assert "/models/${modelPath(" in page
    for word in ("quote.", ".quotes", ".url", ".score", ".rank"):
        assert word not in page, word
