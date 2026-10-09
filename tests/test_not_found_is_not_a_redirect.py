"""A missing page says "not found" at its own address (SEO item 7, 2026-10-09).

Every missing page used to be a SOFT 404: an unknown address redirected to the
landing, an unknown job/capability/metric slug rendered the board hub, an
unknown blog post rendered the blog index, and an unknown model showed only an
error notice. To a search engine each is a real page with somebody else's
content at an address that should not exist.

Routing lives in JSX that node cannot render without React, so these pin the
source, as the repo's other routing tests do. The rendered head of the
not-found page (title, noindex) is checked through node in
tests/test_seo_head_text.py.
"""
from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web" / "src"


def _read(rel: str) -> str:
    return (WEB / rel).read_text(encoding="utf-8")


def test_the_catch_all_route_is_not_a_redirect():
    app = _read("App.jsx")
    catch_all = re.search(r'<Route path="\*" element=\{([^}]*)\}', app)
    assert catch_all, "the catch-all route is gone"
    assert "<NotFound" in catch_all.group(1)
    assert "Navigate" not in catch_all.group(1)


def test_the_not_found_page_is_always_noindex():
    page = _read("components/NotFound.jsx")
    assert "useHead(PRIVATE.notFound)" in page
    pages = _read("seo/pages.js")
    assert "notFound: { title: fullTitle('Page not found'), noindex: true }" in pages


def test_an_unknown_section_is_not_found_not_the_hub():
    board = _read("routes/Board.jsx")
    assert "function sectionMissing(seg, slug)" in board
    assert "<NotFound what={what}" in board


def test_an_unknown_post_is_not_found_not_the_index():
    blogs = _read("routes/Blogs.jsx")
    assert '<NotFound what="post"' in blogs


def test_only_a_404_makes_a_model_not_found():
    # "This model does not exist" and "the API failed" are different pages.
    detail = _read("routes/ModelDetail.jsx")
    assert "e instanceof ApiError && e.status === 404" in detail
    assert '<NotFound what="model"' in detail


def test_a_page_that_hands_its_head_to_not_found_skips_its_own():
    # A child's effect runs before its parent's: without `false`, the parent
    # would reset the head NotFound just set.
    assert "if (head === false) return undefined" in _read("seo/head.js")
    for page in ("routes/Board.jsx", "routes/Blogs.jsx", "routes/ModelDetail.jsx"):
        assert "missing ? false" in _read(page), page
