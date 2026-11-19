"""Content workspace phase 3: coded templates (YouTube, Instagram), the YouTube
chapter and tag checks, the tracked link and the results log."""

from __future__ import annotations

import contextlib
import re
import string
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient

from judge.app import app
from judge.content_workspace import checks, db, results, settings, store, templates

S = settings.load()
T = templates.load()

SUGGESTION = {"id": "t", "headline": "M1: its first 4 weeks after release",
              "detail": "Released 2026-09-22.", "date": "2026-09-22",
              "evidence": ["Week 1: 85 posts from 75 people"],
              "price": "It costs $4.00 per million input tokens and $20.00 per million output "
                       "tokens",
              "proof": [{"side": "positive", "text": "Built a game with it.", "on": [],
                         "date": "2026-09-28", "platform": "Hacker News", "period": "Week 1"}],
              "links": [{"label": "Model page", "path": "/models/a/m1"}]}


def _rule(check_id, params, fmt=None):
    return {"id": 1, "platform_key": "youtube", "body": "r", "check_id": check_id,
            "severity": "warn", "params": params, "formats": fmt}


def _run(check_id, params, **draft):
    d = {"id": 1, "format": "video_metadata", "title": None, "body": "", "tags": [],
         "ai_assisted": False, **draft}
    return checks.run(d, [_rule(check_id, params)], S)["results"][0]


class TestTemplates:
    def test_every_template_is_for_a_format_its_platform_has(self):
        formats = {p["key"]: set(p["formats"]) for p in settings.seed()["platforms"]}
        for platform, by_format in T.items():
            assert set(by_format) <= formats[platform], platform

    def test_a_template_states_no_number_of_its_own(self):
        # Figures come only through placeholders. The one exception is the
        # chapter scaffold's 0:00, which YouTube requires.
        for platform, by_format in T.items():
            for fmt, t in by_format.items():
                for field in templates.FIELDS:
                    literal = "".join(text for text, _, _, _ in
                                      string.Formatter().parse(t.get(field) or ""))
                    literal = literal.replace("0:00", "")
                    assert not re.search(r"\d", literal), (platform, fmt, field)

    def test_an_unknown_placeholder_is_refused(self, tmp_path):
        bad = tmp_path / "t.yaml"
        bad.write_text("youtube:\n  comment:\n    body: '{views}'\n", encoding="utf-8")
        with pytest.raises(ValueError, match="views"):
            templates.load(bad)

    def test_a_youtube_description_is_filled_from_the_suggestion(self):
        d = {"id": 1, "format": "video_metadata", "suggestion": SUGGESTION,
             "topic_kind": "model_trajectory"}
        out = templates.fill(d, {"key": "youtube", "name": "YouTube"}, S, T)
        assert out["title"] == SUGGESTION["headline"]
        assert "- Week 1: 85 posts from 75 people" in out["body"]
        assert "- Week 1, Hacker News: Built a game with it." in out["body"]
        assert "/models/a/m1" in out["body"] and out["unfilled"] == []
        assert out["to_write"] >= 3   # the chapter lines and titles to write

    def test_a_missing_value_is_marked_not_dropped(self):
        d = {"id": 1, "format": "video_metadata", "topic_kind": None,
             "suggestion": {**SUGGESTION, "price": None, "proof": []}}
        out = templates.fill(d, {"key": "youtube", "name": "YouTube"}, S, T)
        assert "[no price in this suggestion]" in out["body"]
        assert out["unfilled"] == ["paraphrased report", "price"]

    def test_a_platform_format_without_a_template_says_so(self):
        d = {"id": 1, "format": "post", "suggestion": SUGGESTION, "topic_kind": None}
        with pytest.raises(store.WorkspaceRequestError, match="no template") as e:
            templates.fill(d, {"key": "x", "name": "X"}, S, T)
        assert e.value.status == 404


class TestYouTubeChecks:
    P = {"min_chapters": 3, "min_seconds": 10}

    @pytest.mark.parametrize("body,ok,why", [
        ("Intro\n0:00 Start\n1:10 Middle\n2:30 End", True, "3 chapters"),
        ("no timestamps at all", True, "no chapters"),
        ("0:05 Start\n1:10 Middle\n2:30 End", False, "0:00"),
        ("0:00 Start\n1:10 End", False, "at least 3"),
        ("0:00 Start\n0:05 Middle\n2:30 End", False, "shorter than 10"),
        ("0:00 Start\n2:30 Middle\n1:10 End", False, "not in order"),
        ("0:00 Start\n[m:ss] [Chapter]", False, "still to fill"),
        ("0:00 Start\n1:02:00 Later\n1:10:00 End", True, "3 chapters"),
    ])
    def test_chapters_follow_youtubes_rules(self, body, ok, why):
        r = _run("yt_chapters", self.P, body=body)
        assert (r["outcome"] == "pass") is ok and why in r["detail"], r["detail"]

    def test_the_tags_budget_counts_the_commas(self):
        assert _run("tags_budget", {"max_chars": 9}, tags=["abcd", "efgh"])["outcome"] == "pass"
        assert _run("tags_budget", {"max_chars": 8}, tags=["abcd", "efgh"])["outcome"] == "warn"

    def test_the_seeded_rules_name_these_checks(self):
        yt = next(p for p in settings.seed()["platforms"] if p["key"] == "youtube")
        checks_used = {r["check"] for r in yt["rules"]}
        assert {"yt_chapters", "tags_budget"} <= checks_used


class TestTrackedLink:
    def _d(self, **kw):
        return {"id": 7, "platform_key": "linkedin", "topic_kind": "model_trajectory",
                "suggestion": SUGGESTION, **kw}

    def test_the_link_names_platform_topic_and_draft(self, monkeypatch):
        monkeypatch.delenv("SITE_URL", raising=False)
        link = results.tracked_link(self._d(), S)
        assert link["url"] == ("/models/a/m1?utm_source=linkedin&utm_medium=social"
                               "&utm_campaign=model_trajectory&utm_content=draft-7")
        assert not link["complete"] and "SITE_URL" in link["note"]

    def test_with_the_site_address_it_is_complete(self, monkeypatch):
        monkeypatch.setenv("SITE_URL", "https://board.example/")
        link = results.tracked_link(self._d(topic_kind=None, suggestion=None), S)
        assert link["url"].startswith("https://board.example/?utm_source=linkedin")
        assert "utm_campaign=post" in link["url"] and link["complete"]


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.commit()
        db.migrate(c)
        store.load_seed(c)
        yield c


def _posted(conn, platform="youtube", fmt="video_metadata"):
    d = store.create_draft(conn, platform, {"format": fmt, "suggestion": SUGGESTION}, None)
    return store.update_draft(conn, d["id"], {"status": "posted",
                                              "posted_url": "https://example.com/v"}, None)


class TestResults:
    def test_results_wait_for_a_posted_draft(self, conn):
        d = store.create_draft(conn, "youtube", {"format": "video_metadata"}, None)
        with pytest.raises(store.WorkspaceRequestError, match="posted") as e:
            results.add(conn, d["id"], metric="views", value=1, source="Studio",
                        observed_at=None, note=None, by=None, s=S)
        assert e.value.status == 409

    @pytest.mark.parametrize("kw,why", [
        ({"metric": "impressions"}, "not recorded for youtube"),
        ({"value": -1}, "whole number"),
        ({"source": " "}, "where the number was read"),
        ({"observed_at": datetime.now(UTC) + timedelta(days=1)}, "future"),
    ])
    def test_refusals(self, conn, kw, why):
        d = _posted(conn)
        args = {"metric": "views", "value": 10, "source": "YouTube Studio",
                "observed_at": None, "note": None, "by": None, "s": S, **kw}
        with pytest.raises(store.WorkspaceRequestError, match=why):
            results.add(conn, d["id"], **args)

    def test_readings_are_kept_and_the_latest_shows(self, conn):
        d = _posted(conn)
        t0 = datetime.now(UTC) - timedelta(days=2)
        results.add(conn, d["id"], metric="views", value=120, source="Studio",
                    observed_at=t0, note=None, by="a", s=S)
        results.add(conn, d["id"], metric="views", value=340, source="Studio",
                    observed_at=t0 + timedelta(days=1), note=None, by="a", s=S)
        v = results.view(conn, d["id"], S)
        views = next(m for m in v["metrics"] if m["key"] == "views")
        assert views["latest"]["value"] == 340 and len(v["readings"]) == 2
        likes = next(m for m in v["metrics"] if m["key"] == "reactions")
        assert likes["latest"] is None          # not recorded, never zero
        assert v["site_visits"]["measured"] is False and "analytics" in v["site_visits"]["why"]


class TestEndpoints:
    @pytest.fixture
    def client(self, conn, monkeypatch):
        monkeypatch.setattr(db, "connect", lambda *a, **k: contextlib.nullcontext(conn))
        return TestClient(app)

    def test_template_and_results_round_trip(self, client, conn):
        d = _posted(conn, "instagram", "caption")
        t = client.get(f"/admin/content/drafts/{d['id']}/template").json()
        assert "link in bio" in t["body"]
        r = client.post(f"/admin/content/drafts/{d['id']}/results",
                        json={"metric": "reach", "value": 900, "source": "Instagram insights"})
        assert r.status_code == 200, r.text
        v = client.get(f"/admin/content/drafts/{d['id']}/results").json()
        assert next(m for m in v["metrics"] if m["key"] == "reach")["latest"]["value"] == 900
        meta = client.get("/admin/content/platforms").json()
        assert "caption" in meta["templates"]["instagram"]
