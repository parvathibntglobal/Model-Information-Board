"""Content workspace: proposals written in Claude Code (anooj, 2026-11-17:
"stick to claude code (opus 5.5) for now"). The API writer is off; Claude
Code writes from `export`'s material and `ingest` runs the same checks."""

from __future__ import annotations

import psycopg
import pytest

from judge.content_workspace import db, settings, store, writer

S = settings.load()

SUGGESTION = {"id": "t", "headline": "M1: its first 4 weeks", "date": "2026-09-22",
              "evidence": ["Week 1 (2026-09-22 to 2026-09-28): 85 posts from 75 people; posts "
                           "with a positive report 70, negative 17, neutral 4 (a post can carry "
                           "more than one)"],
              "proof": [], "links": [{"label": "Model page", "path": "/models/a/m1"}]}


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.commit()
        db.migrate(c)
        store.load_seed(c)
        yield c


def _draft(conn, platform="linkedin"):
    return store.create_draft(conn, platform, {"format": "post", "suggestion": SUGGESTION}, None)


def test_the_api_writer_is_off_and_says_where_proposals_come_from(conn):
    assert S["writer"]["api_enabled"] is False
    d = _draft(conn)
    called = []
    with pytest.raises(store.WorkspaceRequestError, match="Claude Code") as e:
        writer.propose(conn, d["id"], instructions=None, by=None,
                       call=lambda **kw: called.append(1))
    assert e.value.status == 409 and not called


def test_export_is_the_api_writers_exact_input(conn):
    d = _draft(conn)
    out = writer.export(conn, d["id"], "lead with week 2")
    assert "LINKEDIN PLAYBOOK" in out["system"]
    assert out["request"]["MATERIAL"]["instructions"] == "lead with week 2"
    assert out["request"]["LINKS"] == [{"label": "Model page", "href": "/models/a/m1"}]
    assert set(out["answer_shape"]["required"]) == {"text", "title", "first_comment",
                                                     "editor_note"}


def test_a_platform_without_the_writer_cannot_be_exported(conn):
    d = store.create_draft(conn, "reddit", {"format": "text_post"}, None)
    with pytest.raises(store.WorkspaceRequestError, match="does not allow"):
        writer.export(conn, d["id"])


def test_an_ingested_proposal_gets_the_same_checks(conn):
    d = _draft(conn)
    bad = writer.ingest(conn, d["id"], {"text": "286 people loved it.", "title": None,
                                        "first_comment": None, "editor_note": ""},
                        author="claude-opus-5-5")
    assert bad["state"] == "refused" and "286" in bad["reasons"][0]
    good = writer.ingest(conn, d["id"], {
        "text": "70 of the 85 posts in its first week had a positive report.",
        "title": None, "first_comment": "We keep every report here: /models/a/m1",
        "editor_note": "Led with week 1."}, author="claude-opus-5-5", by="anooj")
    assert good["state"] == "proposed" and good["fit"]["summary"]
    assert good["model_asked"] == "claude-code/claude-opus-5-5" and good["cost_usd"] is None
    after = writer.use(conn, good["id"], "anooj")
    assert after["ai_assisted"] and after["first_comment"].endswith("/models/a/m1")


def test_claude_code_proposals_are_not_counted_as_unreported_cost(conn):
    d = _draft(conn)
    writer.ingest(conn, d["id"], {"text": "70 of the 85 posts.", "title": None,
                                  "first_comment": None, "editor_note": ""},
                  author="claude-opus-5-5")
    today = writer.spent_today(conn)
    assert today == {"usd": 0.0, "calls": 0, "unreported_cost_calls": 0,
                     "claude_code_proposals": 1}


def test_an_answer_without_text_is_refused_before_anything_is_recorded(conn):
    d = _draft(conn)
    with pytest.raises(store.WorkspaceRequestError, match="text"):
        writer.ingest(conn, d["id"], {"body": "x"}, author="claude-opus-5-5")
    assert writer.runs(conn, d["id"]) == []
