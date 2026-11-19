"""Content workspace: proof in posts and a model's trajectory (anooj,
2026-11-17): counts backed by the board's paraphrased reports, no link to
anyone's post, the model page as the one link."""

from __future__ import annotations

from datetime import UTC, date, datetime

import psycopg
import pytest

from collect.db import apply_schema
from judge.content_workspace import checks, recommend, settings, store, writer

S = settings.load()
TODAY = date(2026, 11, 17)


def _said(pos=1, neg=1):
    def one(side, i):
        return {"id": f"d{side}{i}", "text": f"{side} report {i} about 128,000 tokens",
                "on": ["Reasoning"], "at": "2026-09-28T10:00:00+00:00",
                "source": {"kind": "post", "platform": "reddit",
                           "url": "https://www.reddit.com/r/x/comments/abc"}}
    return {"positive": [one("positive", i) for i in range(pos)],
            "negative": [one("negative", i) for i in range(neg)]}


def _week(people, said=None):
    return {"posts": people + 3, "people": people,
            "by_polarity": {"positive": {"posts": people, "people": people},
                            "negative": {"posts": 2, "people": 2},
                            "neutral": {"posts": 1, "people": 1}},
            "topics": [{"name": "Reasoning", "positive": 5, "negative": 1, "neutral": 0}],
            "said": said or {"positive": [], "negative": []}}


def _readers(weeks, release="2026-09-22"):
    seen = []

    def week(conn, model_id, start, today):
        seen.append(start)
        return weeks[len(seen) - 1]

    return {
        "model": lambda conn, mid: ({"id": mid, "name": "Claude Opus 5.5",
                                     "provider": "anthropic", "release_date": release}
                                    if mid == "anthropic/claude-opus-5.5" else None),
        "week": week,
    }, seen


class TestProof:
    def test_proof_keeps_the_paraphrase_and_drops_the_post_link(self):
        proof = recommend._proof(_said(), 2, "Week 1")
        assert [p["side"] for p in proof] == ["positive", "negative"]
        assert proof[0]["platform"] == "reddit" and proof[0]["date"] == "2026-09-28"
        assert "reddit.com" not in str(proof)

    def test_proof_is_capped_per_side(self):
        assert len(recommend._proof(_said(pos=3, neg=3), 1, "w")) == 2

    def test_a_verdict_carries_proof(self):
        rows = [{"key": "l1", "kind": "launch", "date": "2026-11-10", "models": ["a/m1"],
                 "label": "launch", "why": None, "styles": [{"headline": "h", "detail": "d"}]}]
        v = {"model": {"name": "M1", "release_date": "2026-11-10"}, "days_since_release": 7,
             "windows": [{"label": "Launch week", "from": "2026-11-10", "to": "2026-11-16",
                          "state": "done", **_week(9, _said())}]}
        out = recommend.suggestions(object(), {"key": "x", "topic_kinds": ["launch_verdict"]}, S,
                                    now=datetime(2026, 11, 17, tzinfo=UTC), readers={
                                        "updates": lambda c, d, n: rows,
                                        "news": lambda c, d, n: [],
                                        "verdict": lambda c, m, t: v,
                                        "model": lambda c, m: {"price": "It is free to use"}})
        item = out["kinds"][0]["items"][0]
        assert item["proof"] and item["proof"][0]["period"] == "Launch week"
        assert item["price"] == "It is free to use"


class TestTrajectory:
    def test_four_weeks_from_release_with_counts_topics_and_proof(self):
        readers, seen = _readers([_week(75, _said()), _week(20), _week(0), _week(4)])
        item = recommend.trajectory(None, "anthropic/claude-opus-5.5", S, today=TODAY,
                                    readers=readers)
        assert seen == [date(2026, 9, 22), date(2026, 9, 29), date(2026, 10, 6),
                        date(2026, 10, 13)]
        assert item["headline"] == "Claude Opus 5.5: its first 4 weeks after release"
        assert "75 people" in item["evidence"][0] and "Reasoning (5 positive" in item["evidence"][0]
        assert item["evidence"][2].endswith("nobody reported on it.")
        assert item["links"] == [{"label": "Model page",
                                  "path": "/models/anthropic/claude-opus-5.5"}]
        assert item["proof"][0]["period"] == "Week 1" and item["ready"]

    def test_a_start_date_and_a_week_count(self):
        readers, seen = _readers([_week(3)] * 2)
        item = recommend.trajectory(None, "anthropic/claude-opus-5.5", S, today=TODAY,
                                    start=date(2026, 11, 1), weeks=2, readers=readers)
        assert seen == [date(2026, 11, 1), date(2026, 11, 8)]
        assert item["headline"].endswith("2026-11-01 to 2026-11-14")

    def test_weeks_past_today_are_not_read_and_the_last_is_said_to_run(self):
        readers, seen = _readers([_week(3)] * 4)
        item = recommend.trajectory(None, "anthropic/claude-opus-5.5", S, today=TODAY,
                                    start=date(2026, 11, 10), readers=readers)
        assert len(seen) == 2 and "still running" in item["detail"]

    def test_silent_weeks_are_not_ready_and_say_why(self):
        readers, _ = _readers([_week(0)] * 4)
        item = recommend.trajectory(None, "anthropic/claude-opus-5.5", S, today=TODAY,
                                    readers=readers)
        assert not item["ready"] and "silence is not praise" in item["why_not_ready"]

    @pytest.mark.parametrize("kw,why", [
        ({"weeks": 0}, "between 1 and"),
        ({"weeks": 99}, "between 1 and"),
        ({"start": date(2027, 1, 1)}, "future"),
    ])
    def test_refusals(self, kw, why):
        readers, _ = _readers([_week(1)] * 8)
        with pytest.raises(recommend.TrajectoryRequestError, match=why):
            recommend.trajectory(None, "anthropic/claude-opus-5.5", S, today=TODAY,
                                 readers=readers, **kw)

    def test_an_unknown_model_and_a_missing_release_date(self):
        readers, _ = _readers([_week(1)] * 4, release=None)
        with pytest.raises(recommend.TrajectoryRequestError, match="no model"):
            recommend.trajectory(None, "nope/nope", S, today=TODAY, readers=readers)
        with pytest.raises(recommend.TrajectoryRequestError, match="release date"):
            recommend.trajectory(None, "anthropic/claude-opus-5.5", S, today=TODAY,
                                 readers=readers)


class TestNoPostLinks:
    def _run(self, body):
        rule = {"id": 1, "platform_key": None, "body": "r", "check_id": "no_post_links",
                "severity": "fail", "params": {}, "formats": None}
        d = {"id": 1, "format": "post", "title": None, "body": body, "tags": [],
             "ai_assisted": False}
        return checks.run(d, [rule], S)["results"][0]

    @pytest.mark.parametrize("url", ["https://www.reddit.com/r/x/comments/1",
                                     "https://x.com/someone/status/1",
                                     "https://bsky.app/profile/a/post/1",
                                     "https://news.ycombinator.com/item?id=1"])
    def test_a_link_to_somebodys_post_fails(self, url):
        assert self._run(f"see {url}")["outcome"] == "fail"

    def test_the_model_page_and_lookalike_hosts_pass(self):
        assert self._run("more at https://board.example/models/a/b")["outcome"] == "pass"
        assert self._run("see https://notreddit.com/x")["outcome"] == "pass"


class TestTheWriterGetsProof:
    def test_proof_is_in_the_material_and_its_numbers_may_be_used(self):
        proof = recommend._proof(_said(), 1, "Week 1")
        m = writer.material({"suggestion": {"headline": "h", "evidence": [], "proof": proof,
                                            "links": [{"label": "Model page",
                                                       "path": "/models/a/b"}]},
                             "topic_kind": "model_trajectory", "title": None, "body": ""},
                            {}, S, None)
        assert m["proof"] == proof and "reddit.com" not in str(m)
        ok = {"text": "One engineer reported it spent 128,000 tokens and wrote nothing.",
              "title": None}
        assert writer.check(ok, m) == []
        linked = {"text": "See https://www.reddit.com/r/x/comments/abc", "title": None}
        assert any("links not given" in r for r in writer.check(linked, m))

    def test_a_date_rewritten_without_its_leading_zero_is_not_a_new_number(self):
        m = writer.material({"suggestion": {"headline": "Week 2 (2026-09-29 to 2026-10-05)",
                                            "evidence": ["costs 0.40"]},
                             "topic_kind": None, "title": None, "body": ""}, {}, S, None)
        assert writer.check({"text": "Week 2 (Sep 29 to Oct 5)", "title": None}, m) == []
        # A shortened decimal is still a different figure as written.
        assert writer.check({"text": "costs 0.4", "title": None}, m)


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.commit()
        apply_schema(c)
        c.commit()
        yield c


class TestTheSeedAddsNewTopics:
    def test_a_rerun_adds_new_topic_kinds_to_existing_platforms(self, conn):
        data = settings.seed()
        old = {**data, "platforms": [{**p, "topics": [t for t in p["topics"]
                                                      if t != "model_trajectory"]}
                                     for p in data["platforms"]]}
        store.load_seed(conn, old)
        assert "model_trajectory" not in store.platform(conn, "x")["topic_kinds"]
        added = store.load_seed(conn, data)
        assert added["platforms"] == 0 and added["platform_lists"] >= 5
        assert "model_trajectory" in store.platform(conn, "x")["topic_kinds"]
        assert store.load_seed(conn, data)["platform_lists"] == 0

    def test_every_seeded_topic_kind_is_defined(self):
        for p in settings.seed()["platforms"]:
            assert set(p["topics"]) <= set(S["topic_kinds"])
