"""Content workspace phase 2: the AI writer (judge/content_workspace/writer.py).
No test calls a model: the call is replaced by a fake that returns a fixed
answer and the facts a real call would report."""

from __future__ import annotations

import psycopg
import pytest

from collect.db import apply_schema
from judge.content_workspace import settings, store, writer

S = settings.load()
# These tests exercise the API writer, which config switches off for now
# (proposals are written in Claude Code); turn it on for them only.
S_API = {**S, "writer": {**S["writer"], "api_enabled": True}}


@pytest.fixture(autouse=True)
def _api_writer_on(monkeypatch):
    monkeypatch.setattr(settings, "load", lambda: S_API)

SUGGESTION = {"id": "verdict:a/m1", "headline": "M1: what engineers reported since release",
              "detail": "Released 2026-11-12; 5 days ago.", "date": "2026-11-12",
              "evidence": ["Launch week: 71 posts from 63 people; positive 50, negative 24"],
              "links": [{"label": "Model page", "path": "/models/a/m1"},
                        {"label": "Source", "url": "https://vendor.example/blog/m1"}]}


def _fake(args, served="deepseek/deepseek-v4-flash", cost=0.0004):
    def call(**kw):
        call.seen = kw
        return args, {"served": served, "input_tokens": 900, "output_tokens": 120,
                      "cost": cost, "error": None if args else "no usable write_post answer"}
    return call


def _m():
    return writer.material({"suggestion": SUGGESTION, "topic_kind": "launch_verdict",
                            "title": None, "body": ""}, {}, S, None)


class TestTheWriterChecks:
    def test_numbers_from_the_material_pass(self):
        p = {"text": "50 of 71 posts from 63 people were positive in launch week.", "title": None}
        assert writer.check(p, _m()) == []

    def test_an_invented_number_is_refused(self):
        p = {"text": "70% of engineers love it, 50 of 71 posts.", "title": None}
        assert "70" in writer.check(p, _m())[0]

    def test_a_link_it_was_not_given_is_refused(self):
        ok = {"text": "Read more https://vendor.example/blog/m1", "title": None}
        assert writer.check(ok, _m()) == []
        bad = {"text": "Read more https://elsewhere.example/x and hype.ai", "title": None}
        reasons = writer.check(bad, _m())
        assert any("links not given" in r for r in reasons)
        assert any("hype.ai" in r for r in reasons)

    def test_a_handle_is_refused(self):
        p = {"text": "As @someone said, 50 of 71.", "title": None}
        assert any("handles" in r for r in writer.check(p, _m()))

    def test_an_empty_proposal_is_refused(self):
        assert writer.check({"text": "  ", "title": None}, _m()) == ["the proposal has no text"]


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.commit()
        apply_schema(c)
        c.commit()
        store.load_seed(c)
        yield c


def _draft(conn, platform="x", fmt="post"):
    return store.create_draft(conn, platform, {"format": fmt, "suggestion": SUGGESTION}, "a@b")


def _ok(text="50 of 71 posts were positive.", cost=0.0004):
    return _fake({"text": text, "title": None, "editor_note": "Led with the count."}, cost=cost)


class TestTheWriter:
    def test_a_platform_without_an_ai_writer_is_refused_before_any_call(self, conn):
        d = _draft(conn, "reddit", "text_post")
        call = _ok()
        with pytest.raises(store.WorkspaceRequestError, match="does not allow"):
            writer.propose(conn, d["id"], instructions=None, by=None, call=call)
        assert not hasattr(call, "seen")

    def test_a_passing_proposal_is_fit_checked_and_not_put_in_the_draft(self, conn):
        d = _draft(conn)
        call = _ok("M1 launch week: 50 of 71 posts from 63 people were positive.")
        r = writer.propose(conn, d["id"], instructions="lead with counts", by="a@b", call=call)
        assert r["state"] == "proposed" and r["fit"]["summary"]
        assert r["cost_usd"] == pytest.approx(0.0004)
        assert store.draft(conn, d["id"])["body"] == ""
        # The writer is given the platform's rules as they are in the workspace now.
        assert "Stay within the character limit" in call.seen["user"]
        assert "lead with counts" in call.seen["user"]

    def test_an_edited_rule_reaches_the_writer(self, conn):
        rule = next(n for n in store.notes(conn, "x")["rule"] if n["check_id"] == "hashtags")
        store.update_note(conn, rule["id"], {"body": "No hashtags at all, ever."}, "a@b")
        call = _ok()
        writer.propose(conn, _draft(conn)["id"], instructions=None, by=None, call=call)
        assert "No hashtags at all, ever." in call.seen["user"]

    def test_a_refused_proposal_is_kept_with_its_reasons_and_cannot_be_used(self, conn):
        d = _draft(conn)
        r = writer.propose(conn, d["id"], instructions=None, by=None, call=_ok("9 of 10 love it"))
        assert r["state"] == "refused" and "numbers" in r["reasons"][0]
        with pytest.raises(store.WorkspaceRequestError, match="refused"):
            writer.use(conn, r["id"], None)

    def test_an_unusable_answer_is_recorded_as_failed_with_its_cost(self, conn):
        r = writer.propose(conn, _draft(conn)["id"], instructions=None, by=None, call=_fake(None))
        assert r["state"] == "failed" and r["cost_usd"] == pytest.approx(0.0004)

    def test_a_substituted_model_is_refused(self, conn):
        def call(**kw):
            return None, {"served": "other/model", "input_tokens": 1, "output_tokens": 1,
                          "cost": 0.0001, "error": "asked for x, OpenRouter served 'other/model'"}

        r = writer.propose(conn, _draft(conn)["id"], instructions=None, by=None, call=call)
        assert r["state"] == "failed" and "served" in r["reasons"][0]

    def test_an_unreported_cost_is_null_not_zero(self, conn):
        r = writer.propose(conn, _draft(conn)["id"], instructions=None, by=None,
                           call=_ok(cost=None))
        assert r["cost_usd"] is None
        assert writer.spent_today(conn)["unreported_cost_calls"] == 1

    def test_the_daily_budget_stops_the_next_call(self, conn):
        d = _draft(conn)
        writer.propose(conn, d["id"], instructions=None, by=None, call=_ok(cost=5.0))
        call = _ok()
        with pytest.raises(store.WorkspaceRequestError, match="budget") as e:
            writer.propose(conn, d["id"], instructions=None, by=None, call=call)
        assert e.value.status == 429 and not hasattr(call, "seen")

    def test_using_a_proposal_marks_the_draft_and_keeps_the_old_text(self, conn):
        d = _draft(conn)
        store.update_draft(conn, d["id"], {"body": "my own notes"}, "a@b")
        r = writer.propose(conn, d["id"], instructions=None, by=None, call=_ok())
        after = writer.use(conn, r["id"], "a@b")
        assert after["body"] == "50 of 71 posts were positive." and after["ai_assisted"]
        kept = conn.execute("SELECT replaced FROM cw_writer_run WHERE id = %s",
                            (r["id"],)).fetchone()[0]
        assert kept["body"] == "my own notes"
        assert writer.runs(conn, d["id"])[0]["used_by"] == "a@b"
