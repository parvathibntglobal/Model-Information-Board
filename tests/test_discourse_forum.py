"""Developer forums on Discourse (2026-10-26): read where robots.txt allows, nightly.

No network: a recorded forum. What matters is that robots.txt IS the permission -
observed on every run, a disallowed path is never requested and the terms gate
refuses - and that a topic becomes a `forum` document whose prose is its title
and the opening post's own markdown.
"""

from __future__ import annotations

import json
import pathlib

import httpx
import pytest

from collect.adapters.blog.robots import RobotsGate
from collect.adapters.discourse import DiscourseForum, forum_for_source
from collect.assemble.prose import NotAPayload, for_source, forum_topic_prose
from collect.rawstore import RawStore
from collect.registry.assertions import TermsNotReviewedError
from collect.registry.sources import load_sources

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = "https://discuss.ai.google.dev"
UA = "modelboard-test/0.1 (+https://example.com)"
ROBOTS = "User-agent: *\nDisallow: /search\nDisallow: /admin/\n"
LISTING = {"topic_list": {"topics": [
    {"id": 3, "slug": "flash-is-flawed", "title": "Flash 3.8 is deeply flawed",
     "created_at": "2026-10-26T06:00:00Z", "posts_count": 4, "archetype": "regular"},
    {"id": 2, "slug": "old", "title": "Already stored", "created_at": "2026-10-26T05:00:00Z",
     "posts_count": 1, "archetype": "regular"},
    {"id": 1, "slug": "quota", "title": "Gemini 429s", "created_at": "2026-10-26T04:00:00Z",
     "posts_count": 1, "archetype": "regular"},
]}}


def _site(robots: str = ROBOTS):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text=robots)
        if path == "/latest.json":
            assert request.url.params["order"] == "created"
            return httpx.Response(200, json=LISTING)
        if path.startswith("/t/"):
            tid = int(path.split("/")[2].removesuffix(".json"))
            return httpx.Response(200, json={"post_stream": {"posts": [
                {"post_number": 1, "user_id": 100 + tid, "created_at": "2026-10-26T06:00:00Z"}]}})
        if path.startswith("/raw/"):
            return httpx.Response(200, text="I caught it cheating in function calls.")
        return httpx.Response(404)

    return handler, seen


def _forum(tmp_path, robots: str = ROBOTS):
    handler, seen = _site(robots)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    gate = RobotsGate(client, user_agent=UA)

    class _NoWait:
        def wait(self, url, min_interval=None):
            return 0.0

    forum = DiscourseForum(BASE, client=client, store=RawStore(tmp_path, remote=None),
                           robots=gate, limiter=_NoWait())
    return forum, seen


def test_the_paths_it_uses_are_observed_against_robots(tmp_path):
    forum, _ = _forum(tmp_path)
    observed = forum.observe()
    assert observed["access_path"] == "discourse-json"
    assert observed["listing_path_allowed"] and observed["topic_path_allowed"]
    assert observed["raw_path_allowed"]


def test_new_topics_are_stored_and_held_ones_are_not_requested(tmp_path):
    forum, seen = _forum(tmp_path)
    run = forum.harvest(pages=1, held=frozenset({"discuss.ai.google.dev/t/2"}), max_new=1)
    assert run.listed == 3 and run.already_stored == 1 and run.deferred == 1
    [stored] = run.stored
    assert stored.external_id == "discuss.ai.google.dev/t/3"
    assert "/t/2.json" not in seen and "/raw/2/1" not in seen, "a held topic cost a request"
    draft = stored.draft()
    assert draft.source == "forum"
    assert draft.author_external_id == "discuss.ai.google.dev:103", "forum-qualified id"
    assert draft.url == f"{BASE}/t/flash-is-flawed/3"
    text = forum_topic_prose(forum._store.get(stored.ref).decode("utf-8"))
    assert text.startswith("Flash 3.8 is deeply flawed") and "caught it cheating" in text
    assert "/search" not in seen


def test_a_path_robots_disallows_is_never_requested_and_the_gate_refuses(tmp_path):
    forum, seen = _forum(tmp_path, robots=ROBOTS + "Disallow: /raw/\n")
    assert forum.observe()["raw_path_allowed"] is False
    run = forum.harvest(pages=1, held=frozenset(), max_new=5)
    assert not run.stored and run.robots_blocked >= 1
    assert not any(p.startswith("/raw/") for p in seen)

    contract = load_sources()
    src = next(s for s in contract.platforms if s["id"] == "forum:discuss.ai.google.dev")
    handler, _ = _site(ROBOTS + "Disallow: /raw/\n")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(TermsNotReviewedError):
        forum_for_source(src, rulings=contract.rulings, client=client,
                         store=RawStore(tmp_path / "s", remote=None),
                         robots=RobotsGate(client, user_agent=UA))


def test_the_gate_passes_on_the_real_rules():
    contract = load_sources()
    src = next(s for s in contract.platforms if s["id"] == "forum:discuss.ai.google.dev")
    handler, _ = _site()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    forum_for_source(src, rulings=contract.rulings, client=client,
                     store=RawStore(pathlib.Path("unused"), remote=None),
                     robots=RobotsGate(client, user_agent=UA))


def test_prose_refuses_a_listing():
    with pytest.raises(NotAPayload):
        forum_topic_prose(json.dumps(LISTING))
    assert for_source("forum") is forum_topic_prose


def test_the_nightly_job_reads_the_forums_before_the_models():
    wf = (ROOT / ".github" / "workflows" / "scheduled-fetches.yml").read_text(encoding="utf-8")
    forums = wf.index("python scripts/harvest_forums.py")
    models = wf.index("python -m scripts.run_scheduled_fetches")
    assert wf.index("python scripts/harvest_blogs.py") < forums < models
    src = (ROOT / "scripts" / "harvest_forums.py").read_text(encoding="utf-8")
    assert "SELECT id FROM source WHERE id = ANY(%s)" in src, "refuses an unloaded forum"
