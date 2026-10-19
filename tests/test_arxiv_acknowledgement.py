"""arXiv's acknowledgement travels with every served post that cites arXiv.

The undertaking's `arxiv_acknowledged: true` (contract/sources.yaml) is only
true if no post that cites an arXiv paper is served without it. Review of #535,
2026-10-19: six approved posts cited arXiv and none carried it, because only
the topic-post generator ever added the line. It is now attached where posts
are served (judge/publication.py `with_credits`, judge/blog_store.py).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from judge import blog_store, publication

ACK = "Thank you to arXiv for use of its open access interoperability."


def _post(*sources, **extra):
    return {"slug": "p", "title": "t", "sources": list(sources), **extra}


ARXIV = {
    "n": 1,
    "platform": "arXiv",
    "url": "https://arxiv.org/abs/2610.00001v1",
    "what": "A paper",
}
HN = {
    "n": 2,
    "platform": "Hacker News",
    "url": "https://news.ycombinator.com/item?id=1",
    "what": "discussion",
}


def test_the_contract_states_arxivs_own_wording():
    assert publication.arxiv_acknowledgement() == ACK


def test_a_post_citing_arxiv_is_served_with_the_acknowledgement():
    assert publication.with_credits(_post(HN, ARXIV))["acknowledgement"] == ACK


def test_an_arxiv_link_counts_even_when_the_platform_label_differs():
    other_label = {**ARXIV, "platform": "a paper"}
    assert publication.with_credits(_post(other_label))["acknowledgement"] == ACK


def test_a_post_with_no_arxiv_source_gets_nothing_added():
    assert "acknowledgement" not in publication.with_credits(_post(HN))


def test_a_post_that_carries_its_own_acknowledgement_keeps_it():
    own = "Thank you to arXiv for use of its open access interoperability. (own)"
    assert publication.with_credits(_post(ARXIV, acknowledgement=own))["acknowledgement"] == own


def test_a_missing_acknowledgement_refuses_rather_than_serving_without_it(monkeypatch):
    import judge.config

    publication.arxiv_acknowledgement.cache_clear()
    monkeypatch.setattr(judge.config, "_read", lambda name: {"credits": {}})
    try:
        with pytest.raises(publication.PublicationConfigError, match="arxiv_acknowledgement"):
            publication.with_credits(_post(ARXIV))
    finally:
        publication.arxiv_acknowledgement.cache_clear()


def test_both_store_reads_serve_it(monkeypatch):
    """The Blogs page (`published`) and Admin's preview (`for_review`)."""
    now = datetime.now(UTC)
    monkeypatch.setattr(
        blog_store,
        "_read",
        lambda conn, sql, params=(): (
            [(_post(ARXIV), now)]
            if "WHERE p.state = 'approved'" in sql
            else [(_post(ARXIV), "approved", None, now, None, now)]
        ),
    )
    assert blog_store.published(None)[0]["acknowledgement"] == ACK
    assert blog_store.for_review(None)[0]["acknowledgement"] == ACK


def test_the_public_read_carries_no_per_platform_split(monkeypatch):
    """`per_platform_counts_shown: false`: the public Blogs read keeps only the
    provenance the page renders; Admin's review read keeps everything."""
    now = datetime.now(UTC)
    prov = {
        "model": "m",
        "generated_at": "2026-10-18",
        "plan_key": "k",
        "platforms": {"arXiv": 4, "Reddit": 2},
        "documents": ["reddit:t3_x", "arxiv:2610.1"],
        "embedded": {"reddit": 1},
    }
    monkeypatch.setattr(
        blog_store,
        "_read",
        lambda conn, sql, params=(): (
            [(_post(ARXIV, provenance=prov), now)]
            if "WHERE p.state = 'approved'" in sql
            else [(_post(ARXIV, provenance=prov), "approved", None, now, None, now)]
        ),
    )
    public = blog_store.published(None)[0]["provenance"]
    assert public == {"model": "m", "generated_at": "2026-10-18", "plan_key": "k"}
    assert blog_store.for_review(None)[0]["provenance"]["platforms"] == {"arXiv": 4, "Reddit": 2}
