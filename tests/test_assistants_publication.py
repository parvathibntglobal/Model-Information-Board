"""`contract/publication.yaml` `assistants_page` (PROPOSED 2026-11-12, #625 review):
the rule the public AI assistants page follows is its own block, read strictly.

No database.
"""
from __future__ import annotations

import pytest

from judge import assistants, publication
from judge.config import _read as real_read


@pytest.fixture(autouse=True)
def _fresh():
    for fn in (publication.assistants_page_terms, publication.evidence_feed_terms,
               publication.withheld_sources):
        fn.cache_clear()
    yield
    for fn in (publication.assistants_page_terms, publication.evidence_feed_terms,
               publication.withheld_sources):
        fn.cache_clear()


def _with_page(monkeypatch, page):
    import judge.config as config

    def fake(name):
        raw = real_read(name)
        if name == "publication.yaml":
            raw = {**raw, "assistants_page": page}
            if page is None:
                raw.pop("assistants_page")
        return raw
    monkeypatch.setattr(config, "_read", fake)


def test_the_real_block_is_the_quote_form_with_reddit_and_x_embedded_and_bluesky_held():
    terms = publication.assistants_page_terms()
    assert terms == {"quote_form": "quote_with_credit_and_link",
                     "embed_only": ("reddit", "x"), "held": ("bluesky",)}


@pytest.mark.parametrize("source, how", [
    ("reddit", "embed"), ("x", "embed"),
    ("bluesky", "omit"), ("arxiv", "omit"), (None, "omit"),
    ("hackernews", "quote"), ("devto", "quote"),
])
def test_each_source_is_treated_by_the_block(source, how):
    assert assistants._treatment(source) == how


@pytest.mark.parametrize("page, says", [
    (None, "no `assistants_page` block"),
    ({"quote_form": "paraphrase_only", "embed_only": [], "held": []}, "needs code"),
    ({"embed_only": [], "held": []}, "quote_form"),
    ({"quote_form": "quote_with_credit_and_link", "held": []}, "embed_only"),
    ({"quote_form": "quote_with_credit_and_link", "embed_only": ["threads"], "held": []},
     "does not embed"),
])
def test_a_missing_or_unbuilt_setting_is_refused(monkeypatch, page, says):
    _with_page(monkeypatch, page)
    with pytest.raises(publication.PublicationConfigError, match=says):
        publication.assistants_page_terms()
