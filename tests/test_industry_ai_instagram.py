"""The observer's Instagram arm (anooj, 2026-11-25): adapter, config, runner, gate.

NO DATABASE and NO NETWORK: a fake client answers, a fake store records. Every
caption here is invented.
"""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import yaml

from collect.adapters import instagram
from collect.industry_ai import config as iai_config
from collect.industry_ai import harvest as hv
from collect.industry_ai.config import IndustryAIConfigError
from collect.industry_ai.rules import Item, handle_of

CONTRACT = Path(__file__).resolve().parents[1] / "contract" / "industry_ai.yaml"
NOW = datetime(2026, 11, 25, 12, tzinfo=UTC)


def node(code, *, caption="We used an AI model to draft our weekly plan.", ts=None, owner="42"):
    edges = [{"node": {"text": caption}}] if caption is not None else []
    return {
        "shortcode": code,
        "taken_at_timestamp": int((ts or NOW).timestamp()),
        "edge_media_to_caption": {"edges": edges},
        "edge_media_preview_like": {"count": 7},
        "edge_media_to_comment": {"count": 2},
        "owner": {"id": owner, "username": "someone"},
    }


def page(nodes):
    edges = [{"node": n} for n in nodes]
    return {"data": {"user": {"edge_owner_to_timeline_media": {"edges": edges}}}}


class FakeStore:
    def __init__(self):
        self.puts = []

    def put(self, blob, namespace=None):
        self.puts.append(blob)
        return SimpleNamespace(ref=f"raw:{len(self.puts)}")


class FakeClient:
    """Answers queued (status, body, headers) in order and records each call."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append((url, dict(params or {})))
        status, body, hdrs = self.answers.pop(0)
        if isinstance(status, Exception):
            raise status
        return httpx.Response(status, content=json.dumps(body).encode(), headers=hdrs or {},
                              request=httpx.Request("GET", url))


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(instagram, "settings", lambda: SimpleNamespace(
        instagram_provider="instagram-looter2", instagram_rapidapi_key=None, rapidapi_key="k"))
    monkeypatch.setattr(instagram, "record_rapidapi_quota", lambda **kw: True)


def harvester(client, store=None):
    return instagram.InstagramHarvester(client=client, store=store or FakeStore(),
                                        limiter=SimpleNamespace(wait=lambda url: None),
                                        clock=lambda: NOW, sleeper=lambda s: None)


# ── the adapter ──────────────────────────────────────────────────────────────


def test_the_host_is_derived_and_never_defaulted(monkeypatch):
    assert instagram.host_for("instagram-looter2") == "instagram-looter2.p.rapidapi.com"
    monkeypatch.setattr(instagram, "settings", lambda: SimpleNamespace(instagram_provider=None))
    with pytest.raises(instagram.InstagramConfigError, match="INSTAGRAM_PROVIDER is not set"):
        instagram.host_for()
    with pytest.raises(instagram.InstagramConfigError, match="looks like a host"):
        instagram.host_for("instagram-looter2.p.rapidapi.com")


def test_a_feed_page_is_stored_before_it_is_read_and_parsed(configured):
    store = FakeStore()
    quota = {"x-ratelimit-requests-remaining": "14000", "x-ratelimit-requests-limit": "15000"}
    c = FakeClient([(200, page([node("A1"), node("A2", caption="")]), quota)])
    run = harvester(c, store).user_feed("42", query="ig:someone")
    assert len(store.puts) == 1 and run.discovery_ref == "raw:1"
    assert [n["shortcode"] for n in run.posts] == ["A1", "A2"]
    assert run.uncaptioned == 1
    assert (run.quota_remaining, run.quota_limit) == (14000, 15000)
    assert c.calls[0][1] == {"id": "42", "count": instagram.PER_PAGE}


def test_a_page_with_no_feed_is_empty_not_quiet(configured):
    run = harvester(FakeClient([(200, {"errorMessage": "x"}, {})])).user_feed("42")
    assert run.posts == [] and run.empty_response == 1


def test_a_passing_failure_is_retried_once_and_recorded(configured):
    run = harvester(FakeClient([(503, {}, {}), (200, page([node("B1")]), {})])).user_feed("42")
    assert run.http_errors == 1 and run.recovered == 1 and run.retries == 1
    assert hv.failure_of(run) is None
    assert len(run.posts) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_a_refusal_is_not_retried(configured, status):
    c = FakeClient([(status, {}, {})])
    run = harvester(c).user_feed("42")
    assert len(c.calls) == 1 and run.http_errors == 1
    assert hv.failure_of(run) == f"1 request(s) failed (HTTP {status})"


def test_a_spent_quota_is_not_retried(configured):
    c = FakeClient([(429, {}, {"x-ratelimit-requests-remaining": "0"})])
    run = harvester(c).user_feed("42")
    assert len(c.calls) == 1 and run.quota_exhausted


def test_an_unknown_name_has_no_id_and_a_failed_lookup_raises(configured):
    unknown = harvester(FakeClient([(200, {"errorMessage": "not found"}, {})]))
    assert unknown.user_id("nobody") is None
    assert harvester(FakeClient([(200, {"user_id": 123}, {})])).user_id("someone") == "123"
    with pytest.raises(RuntimeError, match="unknown, not 'no account'"):
        harvester(FakeClient([(403, {}, {})])).user_id("someone")


# ── the contract ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def raw():
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


@pytest.mark.parametrize("bad, says", [
    ({"a": "1"}, "list of"),                            # a mapping can hide a repeat
    ([["acct.one", "123"], ["acct.one", "456"]], "handle listed twice"),
    ([["acct.one", "123"], ["acct.two", "123"]], "id listed twice"),
    ([["acct.one", 123]], "pair of two strings"),       # an unquoted id is refused
    ([["acct.one", "12a"]], "numeric account id"),
    ([["bad name!", "123"]], "not a valid name"),
])
def test_the_instagram_list_is_strict(raw, bad, says):
    r = copy.deepcopy(raw)
    r["watch"]["instagram"] = bad
    with pytest.raises(IndustryAIConfigError, match=says):
        iai_config.parse(r)


def test_each_account_is_one_query_and_the_cap_covers_them(raw):
    cfg = iai_config.parse(copy.deepcopy(raw))
    ig = [q for p, q in cfg.watch_queries() if p == "instagram"]
    assert ig and all(q.startswith("ig:") for q in ig)
    assert set(cfg.instagram_ids()) == {q[3:] for q in ig}
    # One feed request per account per run (the id is in the contract).
    assert cfg.watch["max_requests"]["instagram"] >= len(ig)


# ── the runner ───────────────────────────────────────────────────────────────


class _FakeH:
    def __init__(self, nodes, failures=0):
        self.nodes, self.failures = nodes, failures

    def user_feed(self, uid, *, query=None):
        run = instagram.InstagramRun(query=query, started_at=NOW, calls=1,
                                     http_errors=self.failures, posts=self.nodes)
        run.uncaptioned = sum(not instagram.caption_of(n).strip() for n in self.nodes)
        return run


def runner(nodes, since=NOW - timedelta(days=7)):
    r = hv._Instagram.__new__(hv._Instagram)
    r.since, r.ids, r.h = since, {"someone": "42"}, _FakeH(nodes)
    return r


def test_the_runner_keeps_captioned_posts_in_the_window():
    old = node("OLD", ts=NOW - timedelta(days=30))
    nodes = [node("N1"), node("N2", caption=None), old]
    items, used, detail, failure = runner(nodes).run("ig:someone")
    assert [i.external_id for i in items] == ["N1"]
    assert used == 1 and failure is None
    assert "1 of 3 post(s) came back with no caption" in detail
    it = items[0]
    assert it.id == "instagram:N1" and it.platform == "instagram"
    assert it.url == "https://www.instagram.com/p/N1/" and it.author_id == "42"
    assert it.engagement == {"likes": 7, "comments": 2}


def test_a_page_with_no_caption_at_all_is_a_failure_not_a_quiet_account():
    nodes = [node("C1", caption=None), node("C2", caption="")]
    items, _, _, failure = runner(nodes).run("ig:someone")
    assert items == [] and "no post carried a caption" in failure


def test_the_handle_comes_from_the_watch_query():
    it = Item(id="instagram:N1", platform="instagram", external_id="N1",
              url="https://www.instagram.com/p/N1/", title="", body="b", created_at=NOW,
              author_id="42")
    it.query_keys = {"watch:instagram:ig:SomeOne"}
    assert handle_of(it) == "someone"


# ── the terms gate ───────────────────────────────────────────────────────────


def test_the_gate_passes_on_the_ruled_provider_and_refuses_a_swap(configured, monkeypatch):
    from collect.registry.sources import load_sources

    s = load_sources()
    row = next(p for p in s.platforms if p.get("id") == "instagram")
    obs = {"access_path": "rapidapi-reseller", "instagram_provider": "instagram-looter2",
           "credential_present": True, "credential_source": "RAPIDAPI_KEY",
           "use_basis": "public-derived-publication"}
    monkeypatch.setattr(instagram, "observe_instagram_use", lambda: obs)
    h = instagram.harvester_for_source(row, rulings=s.rulings, client=FakeClient([]),
                                       store=FakeStore())
    assert isinstance(h, instagram.InstagramHarvester)
    monkeypatch.setattr(instagram, "observe_instagram_use",
                        lambda: {**obs, "instagram_provider": "another-provider"})
    with pytest.raises(Exception, match="instagram_provider"):
        instagram.harvester_for_source(row, rulings=s.rulings, client=FakeClient([]),
                                       store=FakeStore())
