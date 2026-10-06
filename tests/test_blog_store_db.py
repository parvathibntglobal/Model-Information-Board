"""The blog store: pending, approved, or a rejected tombstone - against a real
(disposable) database.

`judge/blog_store.py` and migration 20261006T1500. What these pin down:
  * the Blogs page reads APPROVED posts only;
  * rejecting DELETES the content and keeps the slug, plan key and decision -
    and the database refuses a rejected post that keeps its body;
  * a rejected post cannot be moved back, and the planner still sees its key;
  * storing never overwrites a stored post, whatever its state.
Requires a database. See docs/dev-database.md.
"""
from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

from judge import blog_store

SCHEMA = Path(__file__).resolve().parents[1] / "contract" / "tables.sql"


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        connection.commit()
        yield connection


def _post(slug: str, plan_key: str | None = None, **over) -> dict:
    doc = {"slug": slug, "title": slug.title(), "dek": "d", "tag": "t", "by": "b", "lead": "l",
           "meta": [], "body": [["p", "x"]],
           "provenance": {"model": "m", "generated_at": "2026-10-06T10:00:00+00:00",
                          "plan_key": plan_key}}
    doc.update(over)
    return doc


def test_stored_drafts_are_pending_and_not_published(conn):
    out = blog_store.store_drafts(conn, [_post("a"), _post("b")])
    assert out == {"stored": ["a", "b"], "already": [], "refused": []}
    assert blog_store.published(conn) == []
    assert {p["review"] for p in blog_store.for_review(conn)} == {"pending"}


def test_only_approved_posts_are_published(conn):
    blog_store.store_drafts(conn, [_post("a"), _post("b")])
    blog_store.decide(conn, "a", "approved", None)
    assert [p["slug"] for p in blog_store.published(conn)] == ["a"]


def test_rejecting_deletes_the_content_and_keeps_the_tombstone(conn):
    blog_store.store_drafts(conn, [_post("a", plan_key="field-report:anthropic/x")])
    blog_store.decide(conn, "a", "rejected", "too thin")
    doc, state, plan_key = conn.execute(
        "SELECT doc, state, plan_key FROM blog_post WHERE slug = 'a'").fetchone()
    assert (doc, state) == (None, "rejected")
    assert plan_key == "field-report:anthropic/x"
    [t] = blog_store.for_review(conn)
    assert t["review"] == "rejected" and t["review_reason"] == "too thin"
    assert "title" not in t and "body" not in t  # nothing of the post is left to read
    # The planner still sees it, so it is never written (and paid for) again.
    assert blog_store.planned_keys(conn) == {"field-report:anthropic/x"}


def test_an_approved_post_can_be_rejected_and_then_its_content_is_gone(conn):
    blog_store.store_drafts(conn, [_post("a")])
    blog_store.decide(conn, "a", "approved", None)
    blog_store.decide(conn, "a", "rejected", None)
    assert blog_store.published(conn) == []
    assert conn.execute("SELECT doc FROM blog_post WHERE slug = 'a'").fetchone()[0] is None


@pytest.mark.parametrize("decision", ["reopened", "approved", "rejected"])
def test_a_rejected_post_takes_no_further_decision(conn, decision):
    blog_store.store_drafts(conn, [_post("a")])
    blog_store.decide(conn, "a", "rejected", None)
    with pytest.raises(blog_store.DecisionRefused) as e:
        blog_store.decide(conn, "a", decision, None)
    assert e.value.status == 409


def test_a_decision_that_changes_nothing_is_refused(conn):
    blog_store.store_drafts(conn, [_post("a")])
    with pytest.raises(blog_store.DecisionRefused) as e:
        blog_store.decide(conn, "a", "reopened", None)  # already pending
    assert e.value.status == 409
    blog_store.decide(conn, "a", "approved", None)
    with pytest.raises(blog_store.DecisionRefused):
        blog_store.decide(conn, "a", "approved", None)


def test_storing_never_overwrites_a_stored_post(conn):
    blog_store.store_drafts(conn, [_post("a", title="First")])
    blog_store.decide(conn, "a", "approved", None)
    out = blog_store.store_drafts(conn, [_post("a", title="Second")])
    assert out["already"] == ["a"] and out["stored"] == []
    [p] = blog_store.published(conn)
    assert p["title"] == "First"


def test_storing_does_not_bring_a_rejected_post_back(conn):
    blog_store.store_drafts(conn, [_post("a")])
    blog_store.decide(conn, "a", "rejected", None)
    out = blog_store.store_drafts(conn, [_post("a")])  # the file is still on someone's disk
    assert out["already"] == ["a"]
    row = conn.execute("SELECT state, doc FROM blog_post WHERE slug = 'a'").fetchone()
    assert row == ("rejected", None)


def test_a_malformed_draft_is_refused_by_name(conn):
    out = blog_store.store_drafts(conn, [_post("good"), {"slug": "short"}])
    assert out["stored"] == ["good"]
    why = "missing title, dek, tag, by, lead, meta, body, provenance"
    assert out["refused"] == [{"slug": "short", "why": why}]


def test_the_database_refuses_a_rejected_post_that_keeps_its_body(conn):
    """The CHECK, not only the code: "rejected" and "no content" are one fact."""
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO blog_post (slug, state, doc, stored_at) "
                     "VALUES ('x', 'rejected', '{}'::jsonb, now())")
    conn.rollback()
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO blog_post (slug, state, doc, stored_at) "
                     "VALUES ('y', 'approved', NULL, now())")


def test_a_database_without_the_table_is_unreadable_not_empty(conn):
    """FAILS CLOSED, at the source: "no table" must not read as "no posts"."""
    conn.execute("DROP TABLE blog_post")
    with pytest.raises(blog_store.StoreUnreadable) as e:
        blog_store.published(conn)
    assert "migration" in str(e.value)


def test_a_decision_on_a_post_stored_from_files_is_recorded_without_a_run(conn):
    blog_store.store_drafts(conn, [_post("legacy")])  # stored from files: no run
    out = blog_store.decide(conn, "legacy", "approved", None)
    assert out["run_id"] is None
    row = conn.execute("SELECT run_id, decision FROM blog_post_review").fetchone()
    assert row == (None, "approved")


# ── through the routes, end to end ──────────────────────────────────────────

def test_store_approve_and_publish_through_the_routes(conn, test_dsn, monkeypatch, tmp_path):
    """Admin stores this machine's files, approves one; the public page shows
    that one only, and Admin sees the other as pending."""
    import contextlib
    import json

    from fastapi.testclient import TestClient

    import judge.app as app_module

    for slug in ("one", "two"):
        (tmp_path / f"{slug}.json").write_text(json.dumps(_post(slug)), encoding="utf-8")
    monkeypatch.setenv("BLOG_POSTS_DIR", str(tmp_path))
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")

    @contextlib.contextmanager
    def real_conn():
        with psycopg.connect(test_dsn) as c:
            yield c

    monkeypatch.setattr(app_module, "_conn", real_conn)
    client = TestClient(app_module.app, raise_server_exceptions=False)

    admin = client.get("/blog-posts?review=1").json()
    assert {u["slug"] for u in admin["unstored"]} == {"one", "two"}
    assert client.post("/blog-posts/store").json()["stored"] == ["one", "two"]
    def review(slug, decision, reason=None):
        body = {"slug": slug, "decision": decision, "reason": reason}
        return client.post("/blog-posts/review", json=body).status_code

    assert review("one", "approved") == 200

    public = client.get("/blog-posts").json()
    assert [p["slug"] for p in public["posts"]] == ["one"] and public["reason"] is None
    admin = client.get("/blog-posts?review=1").json()
    assert {p["slug"]: p["review"] for p in admin["posts"]} == {"one": "approved", "two": "pending"}
    assert admin["unstored"] == []

    assert review("two", "rejected", "off topic") == 200
    assert review("two", "reopened") == 409
    admin = client.get("/blog-posts?review=1").json()
    assert [t["slug"] for t in admin["rejected"]] == ["two"]


def test_the_planner_remembers_a_rejected_post(conn):
    """generate_sample_blogs reads stored plan keys - rejected ones included - so
    it never writes the same post again; with no table there is nothing to read."""
    from psycopg.rows import dict_row

    import generate_sample_blogs as g

    blog_store.store_drafts(conn, [_post("a", plan_key="cost-teardown:openai/x")])
    blog_store.decide(conn, "a", "rejected", None)
    conn.commit()
    cur = conn.cursor(row_factory=dict_row)
    assert "cost-teardown:openai/x" in g.existing_plan_keys(cur)
    conn.execute("DROP TABLE blog_post")
    assert g.stored_plan_keys(conn.cursor(row_factory=dict_row)) == set()
