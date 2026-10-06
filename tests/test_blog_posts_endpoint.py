"""GET /blog-posts: drafts for the Blogs section, read from a directory.

No database. The assertions are the three states `judge/blog_posts.py`
promises, because "not configured" and "no drafts yet" rendering the same is
rule 4's failure on a smaller page.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from judge.app import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _open_api(monkeypatch):
    # Same reason as test_read_endpoints: a developer .env carries a real
    # API_TOKEN, and these tests are about the payload, not the gate.
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    # These tests are about reading the draft FILES. The review gate needs the
    # run history in a database (and fails closed without it - see
    # tests/test_blog_runs_db.py), so here it reports "nothing reviewed".
    import judge.app as app_mod

    monkeypatch.setattr(app_mod, "_blog_review_states", lambda _posts: {})


def _post(slug="a-post", **over):
    doc = {
        "slug": slug, "title": "T", "dek": "D", "tag": "Model deep dive", "by": "Draft",
        "lead": "L", "meta": ["01 October 2026"], "ev": [[1, "q", "Engineer report"]],
        "body": [["h2", "H"], ["p", "text {E1}"], ["table", {"cols": ["a"], "rows": [["b"]]}],
                 ["tree", {"question": "Q", "branches": []}],
                 ["code", {"label": "x", "source": "y"}]],
        "provenance": {"model": "openai/gpt-6-luna", "generated_at": "2026-10-01T06:00:00+00:00"},
    }
    doc.update(over)
    return doc


def test_unset_is_a_reason_not_an_empty_list(monkeypatch):
    monkeypatch.delenv("BLOG_POSTS_DIR", raising=False)
    body = client.get("/blog-posts").json()
    assert body["posts"] == []
    assert body["reason"] and "BLOG_POSTS_DIR" in body["reason"]


def test_missing_directory_is_a_reason(monkeypatch, tmp_path):
    monkeypatch.setenv("BLOG_POSTS_DIR", str(tmp_path / "nope"))
    body = client.get("/blog-posts").json()
    assert body["posts"] == [] and "does not exist" in body["reason"]


def test_empty_directory_is_no_drafts_and_no_reason(monkeypatch, tmp_path):
    monkeypatch.setenv("BLOG_POSTS_DIR", str(tmp_path))
    body = client.get("/blog-posts").json()
    assert body == {"posts": [], "skipped": [], "reason": None}


def test_a_valid_draft_is_served_whole(monkeypatch, tmp_path):
    (tmp_path / "a-post.json").write_text(json.dumps(_post()), encoding="utf-8")
    monkeypatch.setenv("BLOG_POSTS_DIR", str(tmp_path))
    body = client.get("/blog-posts").json()
    assert [p["slug"] for p in body["posts"]] == ["a-post"]
    assert body["posts"][0]["body"][2][0] == "table"


def test_a_broken_file_is_named_not_dropped(monkeypatch, tmp_path):
    (tmp_path / "good.json").write_text(json.dumps(_post("good")), encoding="utf-8")
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "short.json").write_text(json.dumps({"slug": "short"}), encoding="utf-8")
    (tmp_path / "odd.json").write_text(json.dumps(_post("odd", body=[["marquee", "x"]])),
                                       encoding="utf-8")
    monkeypatch.setenv("BLOG_POSTS_DIR", str(tmp_path))
    body = client.get("/blog-posts").json()
    assert [p["slug"] for p in body["posts"]] == ["good"]
    why = {s["file"]: s["why"] for s in body["skipped"]}
    assert set(why) == {"bad.json", "short.json", "odd.json"}
    assert "unreadable" in why["bad.json"]
    assert "missing" in why["short.json"]
    assert "body[0]" in why["odd.json"]


def test_featured_post_comes_first(monkeypatch, tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(_post("a", title="Alpha")), encoding="utf-8")
    (tmp_path / "z.json").write_text(json.dumps(_post("z", title="Zulu", feat=True)),
                                     encoding="utf-8")
    monkeypatch.setenv("BLOG_POSTS_DIR", str(tmp_path))
    assert [p["slug"] for p in client.get("/blog-posts").json()["posts"]] == ["z", "a"]


# ── POST/GET /blog-posts/generate ────────────────────────────────────────────

def test_generate_refuses_outside_development(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_TOKEN", "t")
    r = client.post("/blog-posts/generate", json={"count": 3},
                    headers={"Authorization": "Bearer t"})
    assert r.status_code == 403


def test_generate_refuses_a_bad_count():
    assert client.post("/blog-posts/generate", json={"count": 9}).status_code == 422


def test_generate_refuses_a_second_run(monkeypatch, tmp_path):
    from judge import blog_posts

    class Alive:
        def poll(self):
            return None

    monkeypatch.setattr(blog_posts, "_proc", Alive())
    assert client.post("/blog-posts/generate", json={"count": 3}).status_code == 409


def test_status_does_not_report_a_dead_run_as_running(monkeypatch, tmp_path):
    from judge import blog_posts

    f = tmp_path / "_ui_status.json"
    f.write_text(json.dumps({"state": "running", "updated_at": "2026-01-01T00:00:00+00:00"}),
                 encoding="utf-8")
    monkeypatch.setattr(blog_posts, "STATUS_FILE", f)
    monkeypatch.setattr(blog_posts, "_proc", None)
    body = client.get("/blog-posts/generate").json()
    assert body["state"] == "stalled" and body["alive"] is False
