"""A Reddit search hit too old for the extraction window keeps its post and
skips its comments request (2026-11-19, #610).

On 2026-11-18 OpenClaw's refresh spent 4 of its 5 comment requests on threads
whose newest post was 4 Mar to 14 Oct; the 14-day extraction window never read
them. These pin the rule's four edges: a stale post on a refresh is stored
WITHOUT a comments request and without using a comment slot; a first fetch
(which reads the backlog without the window) still fetches its comments; an
undated post is not an old one (rule 6); and the contract value cannot sit
inside the window it exists to serve.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

import collect.adapters.reddit as reddit
import collect.adapters.reddit_write as reddit_write
import collect.ops.sweep_reddit as sweep_reddit
import scripts.fetch_model as fm
from judge import scheduler

NOW = datetime.now(UTC)


def _post(pid, *, age_days):
    return SimpleNamespace(
        subreddit="LocalLLaMA", sieve_text="OpenClaw broke my workflow", external_id=pid,
        raw={"id": pid}, created_at=None if age_days is None else NOW - timedelta(days=age_days),
    )


class _Searcher:
    def __init__(self, posts):
        self.posts = posts
        self.comment_calls: list[str] = []

    def search(self, _variant):
        posts, self.posts = self.posts, []          # one variant returns them all
        return SimpleNamespace(posts=posts, quota_remaining=None, quota_limit=None,
                               adult_skipped=0)

    def fetch_comments(self, post):
        self.comment_calls.append(post.external_id)
        return SimpleNamespace(comments=[SimpleNamespace(external_id=f"{post.external_id}-c",
                                                         raw={"id": f"{post.external_id}-c"})],
                               not_a_thread=False, quota_remaining=None, quota_limit=None)


class _Client:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Conn:
    def commit(self):
        pass


@pytest.fixture()
def harness(monkeypatch, tmp_path):
    monkeypatch.setattr(fm, "FETCH_DIR", tmp_path)
    monkeypatch.setenv("FETCH_QUIET", "1")
    prog = fm.Progress("run-under-test", "mv_1")
    prog._mirror = False
    written: list[list[str]] = []

    def fake_write(conn, items, *, refs, retrieval_provenance):
        written.append([i.external_id for i in items])
        return {"documents_inserted": len(items)}

    class _Store:
        def __init__(self, *_a):
            pass

        def put(self, blob):
            return SimpleNamespace(ref=f"ref-{abs(hash(blob))}")

    monkeypatch.setattr(reddit, "build_client", lambda **_: _Client())
    monkeypatch.setattr(reddit_write, "write_documents", fake_write)
    monkeypatch.setattr(sweep_reddit, "_comments_already_read", lambda conn, post: False)
    monkeypatch.setattr(fm, "RawStore", _Store)
    monkeypatch.setattr(fm, "settings", lambda: SimpleNamespace(raw_store_path=str(tmp_path)))
    monkeypatch.setattr(fm, "load_sources", lambda: SimpleNamespace(sweep_subreddits={}))
    monkeypatch.setattr(fm, "_write_rapidapi_quota", lambda *a, **k: None)
    monkeypatch.setitem(fm.FIRST_FETCH, "window_off", False)

    def run(posts, *, max_threads=5):
        searcher = _Searcher(posts)
        monkeypatch.setattr(fm, "_gated_harvester", lambda *a, **k: (searcher, None))
        fm.harvest_reddit(_Conn(), prog, ["openclaw"], max_searches=1, max_threads=max_threads)
        text = prog.path.read_text(encoding="utf-8")
        lines = [json.loads(x) for x in text.splitlines() if x.strip()]
        (stage,) = [r for r in lines
                    if r.get("id") == "E2R" and r.get("status") != "running"]
        return searcher, written, stage

    return run


def test_a_stale_post_is_kept_without_a_comments_request(harness):
    searcher, written, stage = harness([_post("old", age_days=90), _post("new", age_days=2)])
    assert searcher.comment_calls == ["new"]
    assert ["old"] in written                       # the post itself is still stored
    assert stage["search_hits_stale"] == 1
    assert "older than the comments cutoff" in stage["detail"]


def test_a_stale_post_does_not_use_a_comment_slot(harness):
    searcher, _written, stage = harness(
        [_post("old", age_days=90), _post("new", age_days=2)], max_threads=1)
    assert searcher.comment_calls == ["new"]
    assert stage["threads_fetched"] == 1


def test_a_first_fetch_still_fetches_comments_for_an_old_post(harness, monkeypatch):
    monkeypatch.setitem(fm.FIRST_FETCH, "window_off", True)
    searcher, _written, stage = harness([_post("old", age_days=90)])
    assert searcher.comment_calls == ["old"]
    assert stage["search_hits_stale"] == 0


def test_an_undated_post_is_not_an_old_one(harness):
    searcher, _written, stage = harness([_post("undated", age_days=None)])
    assert searcher.comment_calls == ["undated"]
    assert stage["search_hits_stale"] == 0


def test_the_cutoff_is_read_from_the_contract_and_sits_outside_the_window():
    scheduler.reddit_comments_max_post_age_days.cache_clear()
    window = scheduler.policy().extraction_window_days
    assert scheduler.reddit_comments_max_post_age_days() >= window


@pytest.mark.parametrize("value", [None, 0, True, "30"])
def test_a_missing_or_bad_cutoff_refuses(monkeypatch, value):
    import judge.config as config

    real = config._read

    def fake(name):
        data = dict(real(name) or {})
        if name == "scheduler.yaml":
            data["reddit_comments_max_post_age_days"] = value
        return data

    monkeypatch.setattr(config, "_read", fake)
    scheduler.reddit_comments_max_post_age_days.cache_clear()
    try:
        with pytest.raises(scheduler.SchedulerPolicyError):
            scheduler.reddit_comments_max_post_age_days()
    finally:
        scheduler.reddit_comments_max_post_age_days.cache_clear()


def test_a_cutoff_inside_the_window_refuses(monkeypatch):
    import judge.config as config

    real = config._read

    def fake(name):
        data = dict(real(name) or {})
        if name == "scheduler.yaml":
            data["reddit_comments_max_post_age_days"] = data["extraction_window_days"] - 1
        return data

    monkeypatch.setattr(config, "_read", fake)
    scheduler.reddit_comments_max_post_age_days.cache_clear()
    try:
        with pytest.raises(scheduler.SchedulerPolicyError, match="inside"):
            scheduler.reddit_comments_max_post_age_days()
    finally:
        scheduler.reddit_comments_max_post_age_days.cache_clear()
