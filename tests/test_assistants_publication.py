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


def test_the_fetch_groups_and_the_page_groups_agree_on_every_tracked_agent():
    """#627 review: the agent fetch's `group` (tracked_agents.yaml) and the page's
    grouping (assistant_groups.yaml) are two files; whichever merged second adds
    this. Every tracked agent sits in the page group of the same key, and the
    fetch's turn order names exactly the page's groups."""
    from judge import config

    page = config.assistant_groups()["groups"]
    page_group = {m: g["key"] for g in page for m in g["members"]}
    for agent in config.tracked_agents():
        assert page_group.get(agent.registry) == agent.group, agent.registry
    assert set(config.agent_run_rule().group_turns) == {g["key"] for g in page}


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
