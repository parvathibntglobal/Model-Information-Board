"""The Discussions page: a reader's post is checked, stored pending, and shown
only once a person approves it (judge/discussions.py, 2026-10-20).

The store tests run against the disposable test database, built from
contract/tables.sql like the quiz bank's.
"""
from __future__ import annotations

import pathlib

import psycopg
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from judge import discussions, gate
from judge.app import app

SCHEMA = pathlib.Path(__file__).resolve().parents[1] / "contract" / "tables.sql"


def _post(**kw):
    out = {"topic": "coding", "title": "Opus 5 on a large refactor", "author_name": "Ann",
           "body": "Ran it across a 40-file refactor; it kept the plan and the tests passed."}
    out.update(kw)
    return out


def _req(method, path, query=b""):
    return Request({"type": "http", "method": method, "path": path,
                    "query_string": query, "headers": []})


# ── what may be posted ──────────────────────────────────────────────────────


class TestAPostIsCheckedBeforeAnythingIsStored:
    def test_the_contract_loads_with_topics_and_limits(self):
        cfg = discussions.settings()
        assert len(cfg["topics"]) >= 1
        assert all(t["slug"] and t["name"] for t in cfg["topics"])
        assert cfg["limits"]["posts_per_hour"] > 0

    def test_a_good_post_passes_cleaned(self):
        out = discussions.check(_post(title="  Opus 5   on a refactor  ", author_name="  ann "))
        assert out["title"] == "Opus 5 on a refactor"
        assert out["author_name"] == "ann"
        assert out["model_id"] is None

    def test_a_post_without_a_name_is_refused(self):
        """Every post is signed (2026-10-20): a missing or blank name refuses."""
        for name in (None, "", "   ", "a"):
            with pytest.raises(discussions.PostRefused, match="name"):
                discussions.check(_post(author_name=name))

    def test_an_unknown_topic_is_refused(self):
        with pytest.raises(discussions.PostRefused, match="topic"):
            discussions.check(_post(topic="not-a-topic"))

    def test_a_short_title_or_body_is_refused(self):
        with pytest.raises(discussions.PostRefused, match="title"):
            discussions.check(_post(title="hi"))
        with pytest.raises(discussions.PostRefused, match="post needs"):
            discussions.check(_post(body="too short"))

    def test_too_many_links_is_refused(self):
        body = "see https://a.example and https://b.example and https://c.example for more"
        with pytest.raises(discussions.PostRefused, match="links"):
            discussions.check(_post(body=body))

    def test_the_honeypot_refuses_without_saying_why(self):
        """A bot that fills every field fills this one; the reply teaches it
        nothing about which field gave it away."""
        with pytest.raises(discussions.PostRefused) as e:
            discussions.check(_post(website="https://spam.example"))
        assert "website" not in str(e.value).lower()

    def test_a_malformed_model_id_is_refused_and_a_real_one_kept(self):
        with pytest.raises(discussions.PostRefused, match="model"):
            discussions.check(_post(model_id="not an id"))
        assert discussions.check(_post(model_id="anthropic/claude-opus-5"))["model_id"] == \
            "anthropic/claude-opus-5"


# ── who may reach it ────────────────────────────────────────────────────────


class TestTheGateOpensOnlyThePublicHalf:
    def test_the_page_is_a_public_read_and_posting_the_one_public_write(self):
        assert gate.is_public_read(_req("GET", "/discussions"))
        assert gate.is_public_write(_req("POST", "/discussions/posts"))

    def test_the_review_queue_is_neither(self):
        for method in ("GET", "POST"):
            r = _req(method, "/discussions/review")
            assert not gate.is_public_read(r) and not gate.is_public_write(r)

    def test_posting_is_the_only_public_write(self):
        assert {"/discussions/posts"} == gate.PUBLIC_WRITE_PATHS
        assert not gate.is_public_write(_req("POST", "/blog-posts/review"))
        assert not gate.is_public_write(_req("GET", "/discussions/posts"))

    def test_delete_needs_a_token_and_is_no_public_write(self, monkeypatch):
        assert not gate.is_public_write(_req("POST", "/discussions/delete"))
        monkeypatch.setenv("API_TOKEN", "s3cret")
        assert TestClient(app).post("/discussions/delete", json={"id": "x"}).status_code == 401

    def test_review_needs_a_token(self, monkeypatch):
        monkeypatch.setenv("API_TOKEN", "s3cret")
        c = TestClient(app)
        assert c.get("/discussions/review").status_code == 401
        r = c.post("/discussions/review", json={"id": "x", "decision": "approved"})
        assert r.status_code == 401

    def test_a_refused_post_is_422_with_the_reason_and_needs_no_token(self, monkeypatch):
        """Checked before any database is touched, so this needs none."""
        monkeypatch.setenv("API_TOKEN", "s3cret")
        r = TestClient(app).post("/discussions/posts", json=_post(topic="nope"))
        assert r.status_code == 422
        assert "topic" in r.json()["detail"]

    def test_posting_is_rate_limited_per_address(self, monkeypatch):
        monkeypatch.setenv("API_TOKEN", "s3cret")
        monkeypatch.setenv("DISCUSSION_RATE_PER_HOUR", "2")
        gate._reset_for_tests()
        c = TestClient(app)
        bad = _post(topic="nope")
        codes = [c.post("/discussions/posts", json=bad).status_code for _ in range(3)]
        assert codes == [422, 422, 429]
        gate._reset_for_tests()

    def test_the_limit_keys_on_the_address_the_proxy_appended(self, monkeypatch):
        """Hosted, every request arrives from the proxy; the RIGHTMOST
        X-Forwarded-For entry is the reader. A forged entry to its left must
        not buy a fresh allowance."""
        monkeypatch.setenv("API_TOKEN", "s3cret")
        monkeypatch.setenv("DISCUSSION_RATE_PER_HOUR", "1")
        gate._reset_for_tests()
        c = TestClient(app)
        bad = _post(topic="nope")
        first = c.post("/discussions/posts", json=bad,
                       headers={"X-Forwarded-For": "203.0.113.1, 203.0.113.9"}).status_code
        forged = c.post("/discussions/posts", json=bad,
                        headers={"X-Forwarded-For": "203.0.113.2, 203.0.113.9"}).status_code
        other = c.post("/discussions/posts", json=bad,
                       headers={"X-Forwarded-For": "198.51.100.8"}).status_code
        assert (first, forged, other) == (422, 429, 422)
        gate._reset_for_tests()


# ── what is stored, and what is shown ───────────────────────────────────────


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as c:
        c.execute("DROP SCHEMA IF EXISTS public CASCADE")
        c.execute("CREATE SCHEMA public")
        c.execute(SCHEMA.read_text(encoding="utf-8"))
        c.commit()
        yield c


class TestNothingAppearsUnreviewed:
    def test_a_post_is_stored_pending_and_not_shown(self, conn):
        out = discussions.submit(conn, _post())
        assert out["state"] == "pending" and out["id"].startswith("dp_")
        view = discussions.public_view(conn)
        assert view["total"] == 0
        assert all(t["posts"] == [] for t in view["topics"])

    def test_every_topic_appears_even_with_no_posts(self, conn):
        view = discussions.public_view(conn)
        assert [t["slug"] for t in view["topics"]] == \
            [t["slug"] for t in discussions.settings()["topics"]]

    def test_an_approved_post_is_shown_without_its_moderation_fields(self, conn):
        pid = discussions.submit(conn, _post())["id"]
        discussions.review(conn, pid, "approved", "fine")
        topics = discussions.public_view(conn)["topics"]
        posts = next(t for t in topics if t["slug"] == "coding")["posts"]
        assert [p["id"] for p in posts] == [pid]
        assert "review_note" not in posts[0] and "state" not in posts[0]

    def test_a_rejected_post_is_not_shown_and_can_be_moved_back(self, conn):
        pid = discussions.submit(conn, _post())["id"]
        discussions.review(conn, pid, "rejected", "advertising")
        assert discussions.public_view(conn)["total"] == 0
        assert discussions.listing(conn, "rejected")["items"][0]["review_note"] == "advertising"
        discussions.review(conn, pid, "pending")
        assert discussions.listing(conn, "pending")["counts"]["pending"] == 1

    def test_an_unknown_id_is_none_and_a_bad_decision_refused(self, conn):
        assert discussions.review(conn, "dp_nope", "approved") is None
        with pytest.raises(ValueError):
            discussions.review(conn, "dp_nope", "maybe")


class TestDeleteRemovesForGood:
    def test_a_deleted_post_leaves_no_row(self, conn):
        pid = discussions.submit(conn, _post())["id"]
        discussions.review(conn, pid, "approved")
        assert discussions.delete(conn, pid) is True
        assert discussions.public_view(conn)["total"] == 0
        assert sum(discussions.listing(conn)["counts"].values()) == 0

    def test_deleting_an_unknown_id_is_false(self, conn):
        assert discussions.delete(conn, "dp_nope") is False


class TestRepliesAndOrder:
    def _approved(self, conn, **kw):
        pid = discussions.submit(conn, _post(**kw))["id"]
        discussions.review(conn, pid, "approved")
        return pid

    def test_the_newest_post_is_first(self, conn):
        first = self._approved(conn, title="The older post here")
        conn.execute(
            "UPDATE discussion_post SET created_at = now() - interval '1 day' WHERE id = %s",
            (first,),
        )
        conn.commit()
        second = self._approved(conn, title="The newer post here")
        coding = next(t for t in discussions.public_view(conn)["topics"] if t["slug"] == "coding")
        assert [p["id"] for p in coding["posts"]] == [second, first]

    def test_a_reply_is_held_for_review_then_shown_under_its_post(self, conn):
        pid = self._approved(conn)
        rid = discussions.submit(conn, {"parent_id": pid, "body": "Same on mine, held up fine.",
                                        "author_name": "Bo"})["id"]
        coding = next(t for t in discussions.public_view(conn)["topics"] if t["slug"] == "coding")
        assert coding["posts"][0]["replies"] == []
        discussions.review(conn, rid, "approved")
        coding = next(t for t in discussions.public_view(conn)["topics"] if t["slug"] == "coding")
        post = coding["posts"][0]
        assert [r["id"] for r in post["replies"]] == [rid]
        assert len(coding["posts"]) == 1, "a reply is not listed as a post of its own"
        assert discussions.listing(conn, "approved")["items"][0]["parent_title"] == post["title"]

    def test_a_reply_needs_an_approved_top_level_post(self, conn):
        pending = discussions.submit(conn, _post())["id"]
        with pytest.raises(discussions.PostRefused, match="cannot take replies"):
            discussions.submit(conn, {"parent_id": pending, "body": "A reply to nothing visible",
                                      "author_name": "Bo"})
        pid = self._approved(conn)
        rid = discussions.submit(conn, {"parent_id": pid, "body": "A first reply here",
                                        "author_name": "Bo"})["id"]
        discussions.review(conn, rid, "approved")
        with pytest.raises(discussions.PostRefused, match="cannot take replies"):
            discussions.submit(conn, {"parent_id": rid, "body": "A reply to a reply",
                                      "author_name": "Cy"})

    def test_a_reply_needs_a_name_and_a_body(self):
        with pytest.raises(discussions.PostRefused, match="name"):
            discussions.check({"parent_id": "dp_abc", "body": "long enough reply"})
        with pytest.raises(discussions.PostRefused, match="reply needs"):
            discussions.check({"parent_id": "dp_abc", "body": "short", "author_name": "Bo"})

    def test_deleting_a_post_takes_its_replies(self, conn):
        pid = self._approved(conn)
        discussions.submit(conn, {"parent_id": pid, "body": "A reply that goes too",
                                  "author_name": "Bo"})
        discussions.delete(conn, pid)
        assert sum(discussions.listing(conn)["counts"].values()) == 0
