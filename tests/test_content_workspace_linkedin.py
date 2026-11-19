"""Content workspace: the LinkedIn drafter (a playbook of its own, the first
comment that carries the link, the model's listed price) and what it shares
with X."""

from __future__ import annotations

import json

import psycopg
import pytest

from judge.content_workspace import checks, db, recommend, settings, store, writer

S = settings.load()
S_API = {**S, "writer": {**S["writer"], "api_enabled": True}}


@pytest.fixture(autouse=True)
def _api_writer_on(monkeypatch):
    """The API writer is off in config for now; these tests exercise it."""
    monkeypatch.setattr(settings, "load", lambda: S_API)

SUGGESTION = {"id": "trajectory:a/m1:2026-09-22:4", "headline": "M1: its first 4 weeks",
              "detail": "Released 2026-09-22.", "date": "2026-09-22",
              "evidence": ["Week 1: 85 posts from 75 people"],
              "price": "It costs $5 per million input tokens and $25 per million output tokens",
              "proof": [{"side": "negative", "text": "Spent 128,000 tokens and wrote nothing.",
                         "on": ["Cost"], "date": "2026-09-28", "platform": "reddit",
                         "period": "Week 1"}],
              "links": [{"label": "Model page", "path": "/models/a/m1"}]}


def _fake(args):
    def call(**kw):
        call.seen = kw
        return args, {"served": "deepseek/deepseek-v4-flash", "input_tokens": 1,
                      "output_tokens": 1, "cost": 0.0001, "error": None}
    return call


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.commit()
        db.migrate(c)
        store.load_seed(c)
        yield c


def _draft(conn, platform="linkedin", fmt="post"):
    return store.create_draft(conn, platform, {"format": fmt, "suggestion": SUGGESTION}, "a@b")


class TestPlaybooks:
    def test_each_writer_platform_has_its_own_playbook(self):
        li, x = writer.prompt("linkedin"), writer.prompt("x")
        assert "LINKEDIN PLAYBOOK" in li and "X PLAYBOOK" not in li
        assert "X PLAYBOOK" in x and "LINKEDIN PLAYBOOK" not in x
        # Both start from the same hard rules.
        assert li.startswith(writer.PROMPT_FILE.read_text(encoding="utf-8").rstrip())

    def test_linkedin_is_written_as_the_team_talking_to_the_reader(self):
        li = writer.prompt("linkedin")
        flat = " ".join(li.split())
        assert "THE TEAM BEHIND THE BOARD" in flat and '"we", talking to "you"' in flat
        assert 'Never "I"' in li

    def test_the_linkedin_voice_is_a_note_people_can_see_and_edit(self):
        li = next(p for p in settings.seed()["platforms"] if p["key"] == "linkedin")
        note = next(n for n in li["philosophy"] if n["key"] == "li-phil-3")
        assert note["source"] == "anooj-2026-11-17" and "team behind the board" in note["text"]
        assert "glossary_explainer" in li["topics"]
        assert S["topic_kinds"]["glossary_explainer"]["link"] in S["site"]["paths"]

    def test_a_platform_without_a_playbook_is_refused_not_given_a_default(self):
        with pytest.raises(store.WorkspaceRequestError, match="no writer playbook") as e:
            writer.prompt("bluesky")
        assert e.value.status == 409

    def test_every_platform_that_allows_the_writer_has_a_playbook(self):
        for p in settings.seed()["platforms"]:
            if p["ai_writer_allowed"]:
                assert (writer.PLAYBOOKS / f"{p['key']}.md").exists(), p["key"]


class TestTheLinkedInDraft:
    def test_the_writer_is_given_linkedins_playbook_limits_and_price(self, conn):
        call = _fake({"text": "75 people reported on M1.", "title": None,
                      "first_comment": "Every report: /models/a/m1", "editor_note": ""})
        writer.propose(conn, _draft(conn)["id"], instructions=None, by=None, call=call)
        assert "LINKEDIN PLAYBOOK" in call.seen["system"]
        user = json.loads(call.seen["user"])
        assert {"check": "hook_length", "max_chars": 210,
                "formats": ["post", "document_carousel_text"]} in user["limits"]
        assert user["MATERIAL"]["suggestion"]["price"].startswith("It costs $5")
        assert user["MATERIAL"]["proof"][0]["text"].startswith("Spent 128,000")

    def test_the_first_comment_carries_the_link_and_is_kept_on_use(self, conn):
        d = _draft(conn)
        store.update_draft(conn, d["id"], {"first_comment": "old comment"}, "a@b")
        r = writer.propose(conn, d["id"], instructions=None, by=None, call=_fake({
            "text": "75 people reported on M1 in its first week. It costs $5 per million "
                    "input tokens.", "title": None,
            "first_comment": "Every report, week by week: /models/a/m1", "editor_note": ""}))
        assert r["state"] == "proposed", r["reasons"]
        after = writer.use(conn, r["id"], "a@b")
        assert after["first_comment"] == "Every report, week by week: /models/a/m1"
        kept = conn.execute("SELECT replaced FROM cw_writer_run WHERE id = %s",
                            (r["id"],)).fetchone()[0]
        assert kept["first_comment"] == "old comment"

    def test_the_first_comment_is_checked_like_the_post(self, conn):
        r = writer.propose(conn, _draft(conn)["id"], instructions=None, by=None, call=_fake({
            "text": "75 people reported on M1.", "title": None,
            "first_comment": "Thread: https://www.reddit.com/r/x/comments/1 and 47 more",
            "editor_note": ""}))
        assert r["state"] == "refused"
        assert any("links not given" in x for x in r["reasons"])
        assert any("numbers" in x for x in r["reasons"])

    def test_an_invented_price_is_refused(self, conn):
        r = writer.propose(conn, _draft(conn)["id"], instructions=None, by=None, call=_fake({
            "text": "It costs $3 per million input tokens.", "title": None,
            "first_comment": None, "editor_note": ""}))
        assert r["state"] == "refused"

    def test_a_carousel_gets_its_caption_in_title(self, conn):
        d = _draft(conn, fmt="document_carousel_text")
        r = writer.propose(conn, d["id"], instructions=None, by=None, call=_fake({
            "text": "M1: 75 people in week 1\n---\nOne engineer: 128,000 tokens, nothing written",
            "title": "M1's first month, in counts.", "first_comment": "/models/a/m1",
            "editor_note": ""}))
        after = writer.use(conn, r["id"], None)
        assert after["title"] == "M1's first month, in counts."
        assert after["body"].count("---") == 1


class TestWhatTheLiveRunsGotWrong:
    """Each case is a fault a live LinkedIn proposal made on 2026-11-17."""

    def _m(self):
        return writer.material({"suggestion": {
            "headline": "M1", "proof": SUGGESTION["proof"] + [{
                "side": "negative", "text": "Notes the model does literally anything asked.",
                "on": [], "date": "2026-10-12", "platform": "reddit", "period": "Week 3"}],
            "evidence": ["Week 1: 85 posts from 75 people; posts with a positive report 70, "
                         "negative 17, neutral 4 (a post can carry more than one). Most named: "
                         "Reasoning (15 positive, 4 negative)"]},
            "topic_kind": None, "title": None, "body": ""}, {}, S, None)

    @pytest.mark.parametrize("text", ["70 positive reports, 17 negative.",
                                      "Week 1: positive 70, negative 17.",
                                      "Positive: 70."])
    def test_post_counts_written_as_reports_or_a_split_are_refused(self, text):
        assert any("post counts" in r for r in writer.check({"text": text, "title": None},
                                                            self._m()))

    def test_the_right_wording_and_topic_report_counts_pass(self):
        ok = ("70 of the 85 posts had a positive report, 17 a negative one. "
              "Reasoning drew 15 positive and 4 negative reports.")
        assert writer.check({"text": ok, "title": None}, self._m()) == []

    def test_a_quoted_report_is_refused_and_a_restated_one_passes(self):
        quoted = {"text": 'One engineer said it "does literally anything asked".', "title": None}
        assert any("quotes a report" in r for r in writer.check(quoted, self._m()))
        restated = {"text": "One engineer found it does whatever it is asked, even when it "
                            "should stop.", "title": None}
        assert writer.check(restated, self._m()) == []

    def test_a_hashtags_digits_are_not_a_figure(self):
        assert writer.check({"text": "75 people in week 1. #ClaudeOpus55", "title": None},
                            self._m()) == []

    def test_people_summed_across_weeks_are_refused(self):
        assert writer.check({"text": "286 people reported.", "title": None}, self._m())


class TestModelPerPlatform:
    def test_a_platform_can_have_its_own_model(self):
        s = {**S, "writer": {**S["writer"], "model_by_platform": {"linkedin": "x/stronger"}}}
        assert writer.model_for("linkedin", s) == "x/stronger"
        assert writer.model_for("x", s) == S["writer"]["model"]

    def test_by_default_every_platform_uses_the_writers_model(self):
        assert writer.model_for("linkedin", S) == S["writer"]["model"]


class TestShape:
    WALK = {"text": "Week 1: 75 people. Week 2: busiest. Week 3: turned. Week 4: calm.",
            "title": None}

    def test_a_linkedin_post_that_walks_every_week_is_refused(self):
        reasons = writer.shape(self.WALK, "linkedin", "post", S)
        assert reasons and "weeks 1, 2, 3, 4" in reasons[0]

    def test_two_moments_pass(self):
        ok = {"text": "Week 2 was the busiest; by week 4 the complaints had moved to cost.",
              "title": None}
        assert writer.shape(ok, "linkedin", "post", S) == []

    def test_a_carousel_or_an_x_thread_may_walk_the_weeks(self):
        assert writer.shape(self.WALK, "linkedin", "document_carousel_text", S) == []
        assert writer.shape(self.WALK, "x", "thread", S) == []


class TestOneRetryWithTheReasons:
    def test_a_refused_attempt_is_retried_once_with_its_reasons(self, conn):
        answers = [{"text": "286 people reported.", "title": None, "first_comment": None,
                    "editor_note": ""},
                   {"text": "75 people reported in week 1.", "title": None,
                    "first_comment": None, "editor_note": ""}]
        seen = []

        def call(**kw):
            seen.append(json.loads(kw["user"]))
            return answers[len(seen) - 1], {"served": "deepseek/deepseek-v4-flash",
                                            "input_tokens": 1, "output_tokens": 1,
                                            "cost": 0.0001, "error": None}

        d = _draft(conn)
        r = writer.propose(conn, d["id"], instructions=None, by=None, call=call)
        assert r["state"] == "proposed" and len(seen) == 2
        assert "PREVIOUS_ATTEMPT" not in seen[0]
        assert "286" in seen[1]["PREVIOUS_ATTEMPT"]["refused_because"][0]
        assert [x["state"] for x in writer.runs(conn, d["id"])] == ["proposed", "refused"]

    def test_no_retry_once_the_budget_is_spent(self, conn):
        calls = []

        def call(**kw):
            calls.append(1)
            return ({"text": "286 people", "title": None, "first_comment": None,
                     "editor_note": ""},
                    {"served": "deepseek/deepseek-v4-flash", "input_tokens": 1,
                     "output_tokens": 1, "cost": 5.0, "error": None})

        r = writer.propose(conn, _draft(conn)["id"], instructions=None, by=None, call=call)
        assert r["state"] == "refused" and len(calls) == 1


class TestTheFitCheckReadsTheFirstComment:
    def _run(self, check_id, first_comment, **params):
        rule = {"id": 1, "platform_key": "linkedin", "body": "r", "check_id": check_id,
                "severity": "fail", "params": params, "formats": None}
        d = {"id": 1, "format": "post", "title": None, "body": "75 people reported.",
             "first_comment": first_comment, "tags": [], "ai_assisted": False}
        return checks.run(d, [rule], S)["results"][0]["outcome"]

    def test_a_post_link_in_the_first_comment_fails(self):
        assert self._run("no_post_links", "see https://x.com/a/status/1") == "fail"
        assert self._run("no_post_links", "Every report: /models/a/m1") == "pass"

    def test_a_link_in_the_first_comment_is_not_a_link_in_the_post(self):
        assert self._run("link_placement", "https://board.example/models/a",
                         mode="avoid") == "pass"

    def test_a_handle_in_the_first_comment_is_caught(self):
        assert self._run("handles", "thanks @someone") == "fail"

    def test_the_carousel_slide_rule_applies_per_slide(self):
        rule = next(r for p in settings.seed()["platforms"] if p["key"] == "linkedin"
                    for r in p["rules"] if r["key"] == "li-rule-slide")
        note = {"id": 1, "platform_key": "linkedin", "body": rule["text"],
                "check_id": rule["check"], "severity": rule["severity"],
                "params": rule["params"], "formats": rule["formats"]}
        d = {"id": 1, "format": "document_carousel_text", "title": None,
             "body": "short\n---\n" + "x" * 250, "tags": [], "ai_assisted": False}
        res = checks.run(d, [note], S)["results"][0]
        assert res["outcome"] == "warn" and "part 2" in res["detail"]


class TestPrice:
    def test_a_price_not_listed_stays_not_listed(self):
        class Conn:
            def execute(self, sql, args):
                class R:
                    def fetchone(self):
                        return ("a/m1", "M1", "a", None, None, None)
                return R()

        assert recommend._model(Conn(), "a/m1")["price"] == recommend.PRICE_NOT_LISTED
