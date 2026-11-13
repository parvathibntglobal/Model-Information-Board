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


def test_the_page_shows_sources_only_through_the_feeds_parts_and_links_the_signed_in_evidence():
    page = _read("routes/Assistants.jsx")
    assert "See the quoted evidence" in page
    assert "/models/${modelPath(" in page
    # a source is rendered by the feed's SourceLine (a link, or an embed loaded on
    # click); this page never builds an embed or a source link of its own
    assert "from '../evidence/parts'" in page and "<SourceLine" in page
    for word in ("dangerouslySetInnerHTML", "<iframe", "source.url", ".score", ".rank"):
        assert word not in page, word


def test_the_groups_are_tabs_whose_choice_is_in_the_address():
    page = _read("routes/Assistants.jsx")
    assert 'role="tablist"' in page and 'role="tab"' in page and 'role="tabpanel"' in page
    assert "useSearchParams" in page and "params.get('group')" in page
    assert "ArrowRight" in page and "ArrowLeft" in page
