"""V2EX (2026-10-26): AI boards read nightly, a topic and its replies as one thread.

No network: a recorded API. What matters is that a topic is a thread ROOT, each
reply its own document and voice under that root, the numeric member id is the
author, prose reads both shapes in the original script, a held topic costs no
request, and an error object is an error - never an empty board.
"""

from __future__ import annotations

import json
import pathlib

import httpx
import pytest

from collect.adapters import v2ex
from collect.assemble.prose import NotAPayload, for_source, v2ex_prose
from collect.rawstore import RawStore
from collect.registry.assertions import assert_terms_reviewed
from collect.registry.sources import load_sources

ROOT = pathlib.Path(__file__).resolve().parents[1]

TOPICS = [
    {"id": 11, "title": "DeepSeek V4 本地部署速度", "content": "4090 上跑 V4 Flash 多少 tok/s？",
     "url": "https://www.v2ex.com/t/11", "created": 1792993952, "replies": 2,
     "member": {"id": 501, "username": "alice"}, "deleted": 0},
    {"id": 10, "title": "已读过的话题", "content": "旧", "url": "https://www.v2ex.com/t/10",
     "created": 1792990000, "replies": 0, "member": {"id": 502, "username": "bob"}},
]
REPLIES = [
    {"id": 9001, "content": "实测 V4 Flash 大约 68 tok/s", "created": 1792994000,
     "member": {"id": 601, "username": "carol"}},
    {"id": 9002, "content": "   ", "created": 1792994100, "member": {"id": 602}},
]


def _harvester(tmp_path, *, topics=TOPICS, seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(str(request.url))
        if request.url.path == v2ex.TOPICS_PATH:
            return httpx.Response(200, json=topics)
        if request.url.path == v2ex.REPLIES_PATH:
            assert request.url.params["topic_id"] == "11"
            return httpx.Response(200, json=REPLIES)
        return httpx.Response(404)

    class _NoWait:
        def wait(self, url):
            return 0.0

    return v2ex.V2exHarvester(client=httpx.Client(transport=httpx.MockTransport(handler)),
                              store=RawStore(tmp_path, remote=None), limiter=_NoWait())


def test_a_topic_is_a_root_and_each_reply_a_child_with_its_own_author(tmp_path):
    seen: list[str] = []
    h = _harvester(tmp_path, seen=seen)
    run = h.harvest(["deepseek"], held=frozenset({"t10"}), max_topics=5)
    assert run.listed == 2 and run.already_stored == 1
    assert not any("topic_id=10" in u for u in seen), "a held topic cost a request"
    [topic] = run.topics
    [reply] = run.replies  # the whitespace-only reply is not a document
    t, r = topic.draft(), reply.draft()
    assert (t.source, t.external_id, t.thread_root_external_id) == ("v2ex", "t11", None)
    assert t.author_external_id == "501", "the member id, never the username"
    assert t.lang is None, "a post's language is not measured, so it is unknown"
    assert (r.external_id, r.thread_root_external_id, r.parent_external_id) == \
        ("r9001", "t11", "t11")
    assert r.author_external_id == "601" and r.url == "https://www.v2ex.com/t/11#r_9001"
    topic_text = v2ex_prose(h._store.get(topic.ref).decode("utf-8"))
    assert topic_text.startswith("DeepSeek V4 本地部署速度")
    assert "68 tok/s" in v2ex_prose(h._store.get(reply.ref).decode("utf-8"))


def test_an_error_object_is_an_error_not_an_empty_board(tmp_path):
    h = _harvester(tmp_path, topics={"status": "error", "message": "rate limited"})
    run = h.harvest(["openai"], held=frozenset(), max_topics=5)
    assert run.http_errors == 1 and run.listed == 0 and not run.topics


def test_the_cap_defers_rather_than_drops(tmp_path):
    many = [dict(TOPICS[0], id=n, replies=0) for n in range(20, 26)]
    run = _harvester(tmp_path, topics=many).harvest(["openai"], held=frozenset(), max_topics=2)
    assert len(run.topics) == 2 and run.deferred == 4


def test_prose_refuses_what_is_not_a_topic_or_reply():
    with pytest.raises(NotAPayload):
        v2ex_prose(json.dumps({"kind": "board"}))
    with pytest.raises(NotAPayload):
        v2ex_prose(json.dumps({"kind": "v2ex_reply", "content": " "}))
    assert for_source("v2ex") is v2ex_prose


def test_the_contract_names_the_boards_and_the_gate_reads_it():
    contract = load_sources()
    src = next(s for s in contract.platforms if s["id"] == "v2ex")
    assert src["nodes"] == ["openai", "claude", "localllm", "gemini", "deepseek"]
    assert_terms_reviewed([src], rulings=contract.rulings,
                          observations={"v2ex": v2ex.observe_v2ex_use()})


def test_the_nightly_job_reads_v2ex_before_the_models():
    wf = (ROOT / ".github" / "workflows" / "scheduled-fetches.yml").read_text(encoding="utf-8")
    assert wf.index("python scripts/harvest_v2ex.py") < wf.index(
        "python -m scripts.run_scheduled_fetches")
