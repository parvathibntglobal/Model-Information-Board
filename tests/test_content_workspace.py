"""The content workspace (judge/content_workspace/): seed, fit checks,
topic suggestions, the store and the endpoints."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime

import psycopg
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from collect.db import apply_schema
from judge import app as app_module
from judge import gate
from judge.app import app
from judge.content_workspace import checks, db, recommend, settings, store

S = settings.load()
SEED = settings.seed()


def _rule(check_id, severity="fail", params=None, formats=None, platform_key="x", rid=1):
    return {"id": rid, "platform_key": platform_key, "body": f"rule {rid}", "check_id": check_id,
            "severity": severity, "params": params or {}, "formats": formats}


def _draft(body="", fmt="post", title=None, ai=False):
    return {"id": 1, "format": fmt, "title": title, "body": body, "tags": [], "ai_assisted": ai}


def _one(d, rule, settings_=S):
    return checks.run(d, [rule], settings_)["results"][0]


# ── the seed file ────────────────────────────────────────────────────────────


class TestTheSeed:
    def test_the_eleven_platforms_anooj_listed(self):
        keys = [p["key"] for p in SEED["platforms"]]
        assert sorted(keys) == sorted(["instagram", "youtube", "bluesky", "x", "reddit", "linkedin",
                                       "hackernews", "substack", "medium", "github", "facebook"])

    def test_an_ai_writer_is_allowed_on_x_and_linkedin_only(self):
        assert {p["key"] for p in SEED["platforms"] if p["ai_writer_allowed"]} == {"x", "linkedin"}

    def test_no_platform_makes_video_yet(self):
        assert not any(p["video_creation"] for p in SEED["platforms"])

    def test_facebook_says_it_was_not_researched(self):
        fb = next(p for p in SEED["platforms"] if p["key"] == "facebook")
        assert fb["researched"] is False
        assert "NOT RESEARCHED" in fb["research"][0]["text"]

    def test_every_rule_names_a_coded_check_and_a_severity(self):
        rules = SEED["common"]["rules"] + [r for p in SEED["platforms"] for r in p["rules"]]
        for r in rules:
            assert r["check"] in checks.CHECKS, r["key"]
            assert r["severity"] in store.SEVERITIES, r["key"]

    def test_a_rule_lists_only_formats_its_platform_has(self):
        for p in SEED["platforms"]:
            for r in p["rules"]:
                assert set(r.get("formats") or []) <= set(p["formats"]), r["key"]

    def test_every_topic_kind_a_platform_uses_is_defined(self):
        for p in SEED["platforms"]:
            for k in p["topics"]:
                assert k in S["topic_kinds"], (p["key"], k)

    def test_seed_keys_are_unique(self):
        keys = []
        for block in [SEED["common"], *SEED["platforms"]]:
            for section in settings.SEED_SECTION_KEYS.values():
                keys += [n["key"] for n in block.get(section) or []]
        assert len(keys) == len(set(keys))

    def test_every_note_names_its_source(self):
        for block in [SEED["common"], *SEED["platforms"]]:
            for section in ("philosophy", "research", "recommendations"):
                for n in block.get(section) or []:
                    assert n.get("source"), n["key"]


# ── the fit checks ───────────────────────────────────────────────────────────


class TestTheChecks:
    def test_length_counts_each_part_of_a_thread(self):
        body = "a" * 100 + "\n---\n" + "b" * 300
        r = _one(_draft(body, "thread"), _rule("length", params={"max_chars": 280}))
        assert r["outcome"] == "fail"
        assert "part 2" in r["detail"]

    def test_a_link_counts_as_its_shortened_length_when_the_rule_says_so(self):
        body = "x" * 260 + " https://example.com/" + "y" * 80
        assert _one(_draft(body), _rule("length", params={"max_chars": 280}))["outcome"] == "fail"
        r = _one(_draft(body), _rule("length", params={"max_chars": 285, "url_chars": 23}))
        assert r["outcome"] == "pass"

    def test_a_rule_with_no_limit_is_not_checked_rather_than_passed(self):
        r = _one(_draft("short"), _rule("length"))
        assert r["outcome"] == "unchecked"

    def test_a_missing_title_misses_the_title_rule(self):
        r = _one(_draft("body", "text_post"), _rule("title_length", params={"max_chars": 300}))
        assert r["outcome"] == "fail" and "no title" in r["detail"]

    def test_the_hook_must_land_before_the_cut(self):
        long_first = "word " * 60 + ". Then the rest."
        assert _one(_draft(long_first), _rule("hook_length", "warn",
                                              {"max_chars": 210}))["outcome"] == "warn"
        assert _one(_draft("14 of 38 engineers said yes. More later."),
                    _rule("hook_length", "warn", {"max_chars": 210}))["outcome"] == "pass"

    @pytest.mark.parametrize("text,ok", [
        ("62% of engineers said it broke.", False),
        ("62% of 38 engineers said it broke.", True),
        ("14 of 38 engineers reported failures.", True),
        ("40 engineers reported failures.", False),
        ("It costs $0.40 per million tokens.", True),
        ("No figures at all.", True),
    ])
    def test_a_figure_needs_its_denominator(self, text, ok):
        r = _one(_draft(text), _rule("denominator", "warn"))
        assert (r["outcome"] == "pass") is ok, r["detail"]

    def test_a_question_title_warns_and_a_statement_passes(self):
        rule = _rule("title_question", "warn", formats=["text_post"])
        asked = _one(_draft("body", fmt="text_post", title="Is Opus 5.5 worth it?"), rule)
        said = _one(_draft("body", fmt="text_post", title="Opus 5.5: 63 reports in 3 weeks"), rule)
        assert asked["outcome"] == "warn" and "question" in asked["detail"]
        assert said["outcome"] == "pass"

    def test_no_title_is_unchecked_not_passed(self):
        r = _one(_draft("body", fmt="text_post"), _rule("title_question", "warn"))
        assert r["outcome"] == "unchecked"

    def test_hashtags_over_the_limit(self):
        r = _one(_draft("post #AI #LLM #models"), _rule("hashtags", params={"max": 2}))
        assert r["outcome"] == "fail" and "3 hashtags" in r["detail"]

    def test_a_number_sign_in_a_url_or_word_is_not_a_hashtag(self):
        r = _one(_draft("see https://x.com/a#frag and C# code"),
                 _rule("hashtags", params={"max": 0}))
        assert r["outcome"] == "pass"

    def test_link_modes(self):
        linked = _draft("read https://example.com/a")
        assert _one(linked, _rule("link_placement", "warn", {"mode": "avoid"}))["outcome"] == "warn"
        assert _one(linked, _rule("link_placement", "fail",
                                  {"mode": "not_clickable"}))["outcome"] == "fail"
        assert _one(linked, _rule("link_placement", "manual",
                                  {"mode": "record"}))["outcome"] == "manual"
        assert _one(_draft("link in bio"), _rule("link_placement", "fail",
                                                 {"mode": "not_clickable"}))["outcome"] == "pass"

    def test_a_long_quotation_is_flagged_for_a_person(self):
        r = _one(_draft('Someone said "this model is the best thing I have used all year".'),
                 _rule("verbatim_quote", "warn"))
        assert r["outcome"] == "warn"

    def test_handles_and_scores_and_hype(self):
        assert _one(_draft("thanks @someone"), _rule("handles", "warn"))["outcome"] == "warn"
        assert _one(_draft("mail me at a@b.com"), _rule("handles", "warn"))["outcome"] == "pass"
        assert _one(_draft("we rate it 8/10"), _rule("score_words", "warn"))["outcome"] == "warn"
        assert _one(_draft("14 out of 100 engineers"),
                    _rule("score_words", "warn"))["outcome"] == "pass"
        assert _one(_draft("A game-changer."), _rule("hype_words", "fail"))["outcome"] == "fail"
        assert _one(_draft("A steady release."), _rule("hype_words", "fail"))["outcome"] == "pass"

    def test_disclosure_and_data(self):
        assert _one(_draft("We built the board."), _rule("disclosure"))["outcome"] == "pass"
        assert _one(_draft("Look at this."), _rule("disclosure"))["outcome"] == "fail"
        table = "| model | GB |\n|---|---|\n| a | 8 |"
        assert _one(_draft(table), _rule("table_or_data", "warn"))["outcome"] == "pass"
        assert _one(_draft("words only"), _rule("table_or_data", "warn"))["outcome"] == "warn"

    def test_ai_assisted_text_misses_a_human_only_rule(self):
        assert _one(_draft("x", ai=True), _rule("ai_assisted"))["outcome"] == "fail"
        assert _one(_draft("x"), _rule("ai_assisted"))["outcome"] == "pass"

    def test_utm_is_not_checked_until_the_site_address_is_set(self):
        assert S["site"]["hosts"] == []
        d = _draft("https://board.example/x")
        r = checks.run(d, [_rule("utm", "warn")], S, environ={})["results"][0]
        assert r["outcome"] == "unchecked"
        env = {"SITE_URL": "https://www.board.example/"}
        assert checks.run(d, [_rule("utm", "warn")], S, environ=env)["results"][0][
            "outcome"] == "warn"
        tagged = _draft("https://board.example/x?utm_source=x")
        assert checks.run(tagged, [_rule("utm", "warn")], S, environ=env)["results"][0][
            "outcome"] == "pass"

    def test_an_unknown_check_is_said_not_passed(self):
        r = _one(_draft("x"), _rule("no_such_check"))
        assert r["outcome"] == "unchecked" and "no_such_check" in r["detail"]

    def test_a_rule_for_other_formats_is_counted_not_run(self):
        rep = checks.run(_draft("x", "comment"),
                         [_rule("title_length", params={"max_chars": 9}, formats=["text_post"])], S)
        assert rep["results"] == [] and rep["counts"]["not_for_this_format"] == 1

    def test_a_platform_rule_replaces_the_common_rule_on_the_same_check(self):
        common = _rule("hype_words", "warn", platform_key=None, rid=1)
        own = _rule("hype_words", "fail", platform_key="hackernews", rid=2)
        rep = checks.run(_draft("insane speed"), [common, own], S)
        assert [r["note_id"] for r in rep["results"]] == [2]
        assert rep["results"][0]["outcome"] == "fail"
        assert rep["counts"]["replaced_by_platform_rule"] == 1

    def test_the_summary_is_counts_with_a_denominator_not_a_score(self):
        rep = checks.run(_draft("62% agree #a #b #c"), [
            _rule("hashtags", params={"max": 2}, rid=1),
            _rule("denominator", "warn", rid=2),
            _rule("manual", "manual", rid=3),
            _rule("score_words", "warn", rid=4),
        ], S)
        assert rep["summary"].startswith("1 of 3 coded checks met")
        assert "%" not in rep["summary"] and "score" not in rep["summary"].lower()


# ── the recommender ──────────────────────────────────────────────────────────


NOW = datetime(2026, 11, 17, 12, tzinfo=UTC)


def _update(key, kind, day, models):
    return {"key": key, "kind": kind, "date": day, "models": models, "label": kind,
            "why": None, "styles": [{"headline": f"{key} headline", "detail": "d"}]}


def _readers(updates=(), news=(), verdicts=None, fail=None):
    def upd(conn, days, now):
        if fail == "updates":
            raise RuntimeError("relation does not exist")
        return list(updates)

    return {
        "updates": upd,
        "news": lambda conn, days, now: list(news),
        "verdict": lambda conn, model_id, today: (verdicts or {}).get(model_id, {"model": None}),
    }


def _platform(kinds):
    return {"key": "x", "topic_kinds": kinds}


class TestTheRecommender:
    def test_launches_and_price_moves_come_from_the_updates_list(self):
        rows = [_update("l1", "launch", "2026-11-16", ["a/m1"]),
                _update("p1", "price_cut", "2026-11-15", ["a/m2"]),
                _update("r1", "retiring", "2026-11-20", ["a/m3"])]
        kinds = ["release_reaction", "cheaper_alternative"]
        out = recommend.suggestions(object(), _platform(kinds), S, now=NOW,
                                    readers=_readers(rows))
        rel, cheap = out["kinds"]
        assert [i["id"] for i in rel["items"]] == ["update:l1"]
        assert [i["id"] for i in cheap["items"]] == ["update:p1"]
        assert rel["items"][0]["links"][0]["path"] == "/models/a/m1"

    def test_a_verdict_with_no_reports_says_wait_rather_than_praise(self):
        rows = [_update("l1", "launch", "2026-11-10", ["a/m1"])]
        verdicts = {"a/m1": {"model": {"name": "M1", "release_date": "2026-11-10"},
                             "days_since_release": 7,
                             "windows": [{"label": "Launch week", "from": "2026-11-10",
                                          "to": "2026-11-16", "state": "done", "posts": 0,
                                          "people": 0, "by_polarity": {}}]}}
        out = recommend.suggestions(object(), _platform(["launch_verdict"]), S, now=NOW,
                                    readers=_readers(rows, verdicts=verdicts))
        item = out["kinds"][0]["items"][0]
        assert item["ready"] is False and "silence is not praise" in item["why_not_ready"]

    def test_a_launch_too_young_for_a_verdict_is_left_out(self):
        rows = [_update("l1", "launch", "2026-11-17", ["a/m1"])]
        out = recommend.suggestions(object(), _platform(["launch_verdict"]), S, now=NOW,
                                    readers=_readers(rows))
        assert out["kinds"][0]["items"] == [] and "days old" in out["kinds"][0]["note"]

    def test_sponsored_news_is_left_out(self):
        news = [{"id": 1, "title": "t1", "url": "https://s/1", "source_key": "s",
                 "first_seen_at": "2026-11-17T00:00:00", "sponsored": ["Sponsored"]},
                {"id": 2, "title": "t2", "url": "https://s/2", "source_key": "s",
                 "first_seen_at": "2026-11-17T00:00:00", "sponsored": []}]
        out = recommend.suggestions(object(), _platform(["news_digest"]), S, now=NOW,
                                    readers=_readers(news=news))
        assert [i["id"] for i in out["kinds"][0]["items"]] == ["news:2"]

    def test_an_unreadable_source_is_said_never_shown_as_nothing(self):
        out = recommend.suggestions(object(), _platform(["release_reaction", "vram_answer"]), S,
                                    now=NOW, readers=_readers(fail="updates"))
        broken, evergreen = out["kinds"]
        assert broken["unreadable"] and "could not be read" in broken["note"]
        assert evergreen["items"] and not evergreen.get("unreadable")

    def test_no_board_connection_marks_board_kinds_unreadable(self):
        out = recommend.suggestions(None, _platform(["price_change", "method_post"]), S, now=NOW,
                                    readers=_readers(), board_error="DATABASE_URL is not set")
        assert out["kinds"][0]["unreadable"] and "DATABASE_URL" in out["kinds"][0]["note"]
        assert out["kinds"][1]["items"]

    def test_the_order_is_said_and_nothing_is_scored(self):
        out = recommend.suggestions(object(), _platform(["vram_answer"]), S, now=NOW,
                                    readers=_readers())
        assert "Nothing is scored" in out["order"]
        assert not any("score" in k for item in out["kinds"][0]["items"] for k in item)


# ── the database: the board's, since 2026-11-19 ──────────────────────────────


class TestTheDatabase:
    def test_the_workspace_connects_to_the_boards_database_url(self, monkeypatch):
        seen = {}
        monkeypatch.setenv("DATABASE_URL", "postgresql://example_user@db.example:5432/board")
        monkeypatch.setattr(psycopg, "connect",
                            lambda url, **k: seen.setdefault("url", url) and "board-conn")
        assert db.connect() == "board-conn"
        assert seen["url"] == "postgresql://example_user@db.example:5432/board"

    def test_a_missing_database_url_refuses_rather_than_guessing(self, monkeypatch):
        from judge.store.claims import DatabaseNotConfigured

        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(DatabaseNotConfigured, match="DATABASE_URL is unset"):
            db.connect()

    def test_the_workspace_tables_are_in_the_boards_schema(self):
        from collect.db import schema_sql

        sql = schema_sql()
        for table in db.TABLES:
            assert f"CREATE TABLE {table} (" in sql, table

    def test_the_write_commands_are_gated_and_the_reads_are_not(self, monkeypatch):
        from judge.content_workspace import __main__ as cli

        monkeypatch.setenv("ENVIRONMENT", "development")
        remote = "postgresql://example_user@db.example:5432/board"
        for cmd in cli.WRITE_COMMANDS:
            refused = cli.write_gate(cmd, False, remote)
            assert refused and "is not this machine" in refused, cmd
            assert cli.write_gate(cmd, True, remote) is None              # deliberate
            assert cli.write_gate(cmd, False, "postgresql://localhost/mib") is None
        for cmd in ("status", "material", "draft-json"):
            assert cli.write_gate(cmd, False, remote) is None


# ── the store, on a database ─────────────────────────────────────────────────


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.commit()
        apply_schema(c)
        c.commit()
        yield c


class TestTheStore:
    def test_the_boards_schema_holds_every_workspace_table(self, conn):
        assert db.missing_tables(conn) == []
        conn.execute("DROP TABLE cw_media")
        assert db.missing_tables(conn) == ["cw_media"]
        conn.rollback()

    def test_the_seed_loads_once_and_never_overwrites_an_edit(self, conn):
        first = store.load_seed(conn)
        assert first["platforms"] == 11 and first["notes"] > 100
        x_rule = store.notes(conn, "x")["rule"][0]
        store.update_note(conn, x_rule["id"], {"body": "edited by a person"}, "a@b")
        assert store.load_seed(conn) == {"platforms": 0, "notes": 0, "platform_lists": 0}
        assert store.note(conn, x_rule["id"])["body"] == "edited by a person"

    def test_an_edit_keeps_what_the_note_said_before(self, conn):
        store.load_seed(conn)
        n = store.notes(conn, "reddit")["philosophy"][0]
        store.update_note(conn, n["id"], {"body": "new words"}, "a@b")
        h = store.note_history(conn, n["id"])
        assert h[0]["before"]["body"] == n["body"] and h[0]["after"]["body"] == "new words"
        assert h[0]["edited_by"] == "a@b"

    def test_common_notes_show_on_every_platform(self, conn):
        store.load_seed(conn)
        for key in ("x", "facebook"):
            assert any(n["platform_key"] is None for n in store.notes(conn, key)["rule"])

    def test_a_rule_must_name_a_known_check(self, conn):
        store.load_seed(conn)
        with pytest.raises(store.WorkspaceRequestError, match="checks"):
            store.create_note(conn, platform_key="x", section="rule", body="b", source="s",
                              by=None, check_id="nope", severity="warn")
        with pytest.raises(store.WorkspaceRequestError, match="only a rule"):
            store.create_note(conn, platform_key="x", section="research", body="b", source="s",
                              by=None, check_id="length", severity="warn")

    def test_a_draft_uses_its_platforms_formats_and_topics(self, conn):
        store.load_seed(conn)
        with pytest.raises(store.WorkspaceRequestError, match="formats"):
            store.create_draft(conn, "youtube", {"format": "post"}, None)
        with pytest.raises(store.WorkspaceRequestError, match="topic"):
            store.create_draft(conn, "x", {"format": "post", "topic_kind": "vram_table"}, None)
        d = store.create_draft(conn, "youtube", {"format": "video_metadata", "title": "t"}, None)
        assert d["status"] == "draft"

    def test_ai_assisted_is_recorded_where_no_ai_writer_is_allowed(self, conn):
        store.load_seed(conn)
        d = store.create_draft(conn, "hackernews", {"format": "comment", "ai_assisted": True}, None)
        assert d["ai_assisted"] is True

    def test_posted_needs_where(self, conn):
        store.load_seed(conn)
        d = store.create_draft(conn, "x", {"format": "post", "body": "hi"}, None)
        with pytest.raises(store.WorkspaceRequestError, match="posted_url"):
            store.update_draft(conn, d["id"], {"status": "posted"}, None)
        done = store.update_draft(conn, d["id"], {"status": "posted",
                                                  "posted_url": "https://x.com/i/1"}, None)
        assert done["posted_at"]


# ── the endpoints ────────────────────────────────────────────────────────────


@pytest.fixture
def client(conn, monkeypatch):
    store.load_seed(conn)
    monkeypatch.setattr(app_module, "_cw_conn", lambda: contextlib.nullcontext(conn))
    return TestClient(app)


class TestTheEndpoints:
    def test_no_workspace_path_is_a_public_read(self):
        from starlette.requests import Request

        for path in ("/admin/content/platforms", "/admin/content/platforms/x",
                     "/admin/content/platforms/x/suggestions"):
            req = Request({"type": "http", "method": "GET", "path": path, "query_string": b"",
                           "headers": []})
            assert not gate.is_public_read(req)
        with pytest.MonkeyPatch.context() as m:
            m.setenv("API_TOKEN", "s3cret")
            assert TestClient(app).get("/admin/content/platforms").status_code == 401

    def test_the_platform_list(self, client):
        body = client.get("/admin/content/platforms").json()
        assert len(body["platforms"]) == 11
        assert "length" in body["checks"]

    def test_write_check_and_record(self, client):
        d = client.post("/admin/content/drafts", json={
            "platform_key": "x", "format": "post",
            "body": "62% of engineers call it a game-changer #a #b #c"}).json()
        rep = client.post(f"/admin/content/drafts/{d['id']}/check").json()
        assert rep["counts"]["fail"] >= 1 and rep["summary"]
        again = client.get("/admin/content/platforms/x").json()["drafts"][0]
        assert again["last_check"]["id"] == rep["id"]

    def test_a_refusal_is_a_400_with_the_reason(self, client):
        r = client.post("/admin/content/drafts", json={"platform_key": "x", "format": "reel"})
        assert r.status_code == 400 and "formats" in r.json()["detail"]
        assert client.get("/admin/content/platforms/myspace").status_code == 404

    def test_a_note_edit_round_trip(self, client):
        n = client.post("/admin/content/notes", json={
            "platform_key": "x", "section": "research", "body": "a finding",
            "source": "anooj", "topic": "hook"}).json()
        client.post(f"/admin/content/notes/{n['id']}", json={"body": "a better finding"})
        h = client.get(f"/admin/content/notes/{n['id']}/history").json()["edits"]
        assert h[0]["after"]["body"] == "a better finding"

    def test_suggestions_without_the_board_still_answer(self, client, monkeypatch):
        def no_board():
            raise HTTPException(status_code=503, detail="DATABASE_URL is not set")

        monkeypatch.setattr(app_module, "_conn", no_board)
        body = client.get("/admin/content/platforms/x/suggestions").json()
        board_kinds = [k for k in body["kinds"] if k["signal"] != "evergreen"]
        assert board_kinds and all(k.get("unreadable") for k in board_kinds)
        assert all(k["items"] for k in body["kinds"] if k["signal"] == "evergreen")
