"""Blog generation history and post review, against a real (disposable) database.

`judge/blog_runs.py` records each Admin -> Blogs generation run and each review
decision. Nothing here calls a model: a run is simulated by writing the status
and log files the generator would, and one draft file with its timestamp.
Requires a database. See docs/dev-database.md.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from judge import blog_posts, blog_runs

SCHEMA = Path(__file__).resolve().parents[1] / "contract" / "tables.sql"
STARTED = "2026-10-06T10:00:00+00:00"


@pytest.fixture
def conn(test_dsn):
    with psycopg.connect(test_dsn, connect_timeout=10) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        connection.commit()
        yield connection


@pytest.fixture
def files(tmp_path, monkeypatch):
    """The generator's status and log files, and a drafts directory, all temporary."""
    posts = tmp_path / "posts"
    posts.mkdir()
    monkeypatch.setenv("BLOG_POSTS_DIR", str(posts))
    monkeypatch.setattr(blog_posts, "STATUS_FILE", tmp_path / "_ui_status.json")
    monkeypatch.setattr(blog_posts, "LOG_FILE", tmp_path / "_ui_run.log")
    monkeypatch.setattr(blog_posts, "_proc", None)
    return tmp_path


def _draft(dirpath: Path, slug: str, generated_at: str) -> None:
    doc = {"slug": slug, "title": slug, "dek": "d", "tag": "t", "by": "b", "lead": "l",
           "meta": [], "body": [["p", "x"]], "status": "draft",
           "provenance": {"model": "m", "generated_at": generated_at}}
    (dirpath / f"{slug}.json").write_text(json.dumps(doc), encoding="utf-8")


def _status(files: Path, **kw) -> None:
    blog_posts.STATUS_FILE.write_text(json.dumps({"started_at": STARTED, "items": [], **kw}),
                                      encoding="utf-8")


def _run(conn, files: Path) -> str:
    """A run that starts, writes one post, and finishes."""
    _status(files, state="starting", updated_at=STARTED)
    run_id = blog_runs.record_start(conn, 3, {"state": "starting", "started_at": STARTED})
    _draft(files / "posts", "old-draft", "2026-10-01T06:00:00+00:00")   # predates the run
    _draft(files / "posts", "new-post", "2026-10-06T10:05:00+00:00")
    blog_posts.LOG_FILE.write_text(
        "planned 1 of 3:\n"
        "  [new-post] wrote blog_posts/new-post.json - 2 call(s), cost $0.0412, "
        "tokens 18,204 in / 3,100 out\n"
        "Authorization: Bearer sk-or-v1-abcdef1234567890\n", encoding="utf-8")
    _status(files, state="partial", model="openai/gpt-6-luna", cost_usd=0.0412,
            message="1 written, 1 failed", finished_at="2026-10-06T10:09:00+00:00",
            updated_at="2026-10-06T10:09:00+00:00",
            items=[{"key": "new-post", "state": "done"}, {"key": "lost-post", "state": "failed"}])
    blog_runs.reconcile(conn)
    return run_id


def test_a_finished_run_is_recorded_with_its_cost_tokens_posts_and_log(conn, files):
    run_id = _run(conn, files)
    [row] = blog_runs.runs(conn)
    assert row["id"] == run_id
    assert row["state"] == "partial" and row["finished_at"]
    assert row["model"] == "openai/gpt-6-luna"
    assert row["cost_usd"] == pytest.approx(0.0412)
    assert (row["tokens_in"], row["tokens_out"]) == (18204, 3100)
    # Only the draft written inside the run's window is the run's.
    assert row["posts_written"] == ["new-post"]
    assert row["posts_failed"] == ["lost-post"]
    assert "sk-or-v1" not in row["log"] and "sk-***" in row["log"]


def test_a_run_still_in_progress_is_left_open(conn, files):
    # "Now", not a fixed time: a status older than STALE_AFTER_S is correctly
    # read as stalled, so a fixed timestamp made this test pass only on the day
    # it was written.
    now = datetime.now(UTC).isoformat(timespec="seconds")
    _status(files, state="running", started_at=now, updated_at=now)
    blog_runs.record_start(conn, 3, {"state": "running", "started_at": now})
    blog_runs.reconcile(conn)
    [row] = blog_runs.runs(conn)
    assert row["finished_at"] is None and row["posts_written"] == []


def test_review_is_append_only_and_the_latest_decision_wins(conn, files):
    _run(conn, files)
    assert blog_runs.public_state(conn) == {"new-post": "pending"}
    blog_runs.review(conn, "new-post", "rejected", "too thin")
    blog_runs.review(conn, "new-post", "approved", None)
    assert blog_runs.public_state(conn) == {"new-post": "approved"}
    blog_runs.review(conn, "new-post", "reopened", None)
    assert blog_runs.public_state(conn) == {"new-post": "pending"}
    n = conn.execute("SELECT count(*) FROM blog_post_review").fetchone()[0]
    assert n == 3  # every decision kept


def test_a_draft_no_run_wrote_cannot_be_reviewed(conn, files):
    _run(conn, files)
    with pytest.raises(blog_runs.ReviewRefused) as e:
        blog_runs.review(conn, "old-draft", "approved", None)
    assert e.value.status == 404


def test_an_unknown_decision_is_refused(conn, files):
    _run(conn, files)
    with pytest.raises(blog_runs.ReviewRefused) as e:
        blog_runs.review(conn, "new-post", "published", None)
    assert e.value.status == 422
