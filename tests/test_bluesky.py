"""Bluesky (2026-10-26): searched through the public AppView, stored per post.

No network: a recorded transport. What matters is that a post becomes a
document with its DID as the author, a payload `bluesky_post_prose` reads, a
search response refused as prose, and a failed search recorded as one - never
as "nobody posted".
"""

from __future__ import annotations

import json

import httpx
import pytest

from collect.adapters import bluesky
from collect.assemble.prose import NotAPayload, bluesky_post_prose, for_source
from collect.rawstore import RawStore
from collect.registry.assertions import TermsNotReviewedError, assert_terms_reviewed
from collect.registry.sources import load_sources

POSTS = [
    {"uri": "at://did:plc:abc/app.bsky.feed.post/3kxyz", "cid": "c1",
     "author": {"did": "did:plc:abc", "handle": "eng.example.com"},
     "record": {"text": "Ran DeepSeek V4 Flash on our eval: 68 tok/s, fine for summaries.",
                "createdAt": "2026-10-25T10:00:00Z", "langs": ["en"]},
     "likeCount": 3, "replyCount": 1},
    {"uri": "at://did:plc:def/app.bsky.feed.post/3kabc", "cid": "c2",
     "author": {"did": "did:plc:def", "handle": "other.bsky.social"},
     "record": {"text": "Flash photography tips", "createdAt": "2026-10-25T09:00:00Z"},
     "likeCount": 0, "replyCount": 0},
    {"uri": "at://did:plc:ghi/app.bsky.feed.post/3knotext", "record": {}},
]


class _NoWait:
    def wait(self, url):
        return 0.0


def _harvester(tmp_path, handler):
    return bluesky.BlueskyHarvester(client=httpx.Client(transport=httpx.MockTransport(handler)),
                                    store=RawStore(tmp_path, remote=None), limiter=_NoWait())


def _ok(request):
    assert request.url.host == "api.bsky.app", "public.api.bsky.app refuses search (403)"
    assert request.url.params["sort"] == "latest"
    return httpx.Response(200, json={"posts": POSTS, "hitsTotal": 3793, "cursor": "x"})


def test_a_post_naming_the_model_becomes_a_document_with_its_did(tmp_path):
    h = _harvester(tmp_path, _ok)
    run = h.harvest("DeepSeek V4 Flash")
    assert run.query == '"DeepSeek V4 Flash"'
    assert run.total_count == 3793
    assert run.items_fetched == 2, "a post with no text is not a hit"
    assert run.rejected == 1
    [stored] = run.stored
    draft = stored.draft()
    assert draft.source == "bluesky"
    assert draft.external_id == "at://did:plc:abc/app.bsky.feed.post/3kxyz"
    assert draft.url == "https://bsky.app/profile/did:plc:abc/post/3kxyz"
    assert draft.author_external_id == "did:plc:abc", "the DID, never the handle"
    assert draft.lang == "en"
    text = bluesky_post_prose(h._store.get(stored.ref).decode("utf-8"))
    assert text.startswith("Ran DeepSeek V4 Flash")


def test_a_failed_search_is_an_error_not_an_empty_result(tmp_path):
    run = _harvester(tmp_path, lambda r: httpx.Response(502)).harvest("DeepSeek V4 Flash")
    assert run.http_errors == 1 and run.total_count is None and not run.stored


def test_prose_refuses_a_search_response_and_an_empty_post():
    with pytest.raises(NotAPayload):
        bluesky_post_prose(json.dumps({"posts": POSTS}))
    with pytest.raises(NotAPayload):
        bluesky_post_prose(json.dumps({"record": {"text": "  "}}))
    assert for_source("bluesky") is bluesky_post_prose


def test_the_contract_rules_on_bluesky_and_the_gate_reads_it():
    contract = load_sources()
    src = next(s for s in contract.platforms if s["id"] == "bluesky")
    ruling = contract.rulings[src["terms_ruling"]]
    summary = " ".join(ruling.summary.split())  # a quote may wrap across lines
    # All three developer-guideline obligations, quoted (#567 review).
    assert "deleting content a user has requested to be deleted" in summary
    assert "email address that is regularly monitored" in summary
    assert "keep records of all reports" in summary
    # Quoted on purpose, credited as the platform with a link - no identity shown.
    assert "PUBLICATION, ON PURPOSE" in summary and "PLATFORM NAME" in summary
    assert_terms_reviewed([src], rulings=contract.rulings,
                          observations={"bluesky": bluesky.observe_bluesky_use()})
    wrong = dict(bluesky.observe_bluesky_use(), search_endpoint="/app.bsky.feed.getTimeline")
    with pytest.raises(TermsNotReviewedError):
        assert_terms_reviewed([src], rulings=contract.rulings, observations={"bluesky": wrong})


def test_the_fetch_runs_bluesky_as_a_uniform_platform():
    import scripts.fetch_model as fm

    assert ("bluesky", "E2K", "Harvest · Bluesky", 3) in fm.UNIFORM_PLATFORMS
    assert "bluesky" in fm.ALL_SOURCES and "bluesky" in fm.DEDUPE_SOURCES
    assert fm._harvester_factory("bluesky") is bluesky.harvester_for_source
