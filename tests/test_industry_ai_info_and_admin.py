"""The AI in industries Info view and its Admin section (#668, 2026-11-25).

Asked for on #668's review, point 7: neither read had a test, and one of them
holds a redaction (`_run_detail`) that a change to the run script's wording would
quietly undo. Also the route order, which only a comment held: `/industry-ai/info`
must answer the Info payload, never "no such domain 'info'".

The Admin read runs on the disposable test database; the rest needs none.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from judge import gate
from judge.industry_ai.view import (
    _requests_by_agent,
    _run_detail,
    industry_ai_admin,
    industry_ai_info,
)


@pytest.fixture(autouse=True)
def _open(monkeypatch):
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    gate._reset_for_tests()
    yield
    gate._reset_for_tests()


# ── the Info view ────────────────────────────────────────────────────────────


def test_the_info_route_is_not_read_as_a_domain_key():
    """Declared before `/industry-ai/{key}`: "info" is never a domain."""
    from judge.app import app

    r = TestClient(app).get("/industry-ai/info")
    assert r.status_code == 200
    body = r.json()
    assert body["domains"] and "rules_version" in body


def test_the_info_payload_carries_what_the_page_reads():
    info = industry_ai_info()
    # Every rules version the contract names is explained, the current one included.
    assert info["rules_version"] in info["versions"]
    assert all(v.strip() for v in info["versions"].values())
    # The excerpt length the page states, from the code that cuts the excerpts.
    from judge.industry_ai.view import EXCERPT_CHARS

    assert info["excerpt_chars"] == EXCERPT_CHARS
    assert set(info["retention"]) == {"clear_text_after_days", "dropped", "kept_domains"}
    # A domain is an industry or a role, so the page can count them apart.
    assert {d["kind"] for d in info["domains"]} <= {"industry", "function"}
    # The Bluesky DID is for the code: never in the payload.
    assert all("bluesky_did" not in p["handles"] for p in info["watch"]["people"])


# ── Admin: the redaction ─────────────────────────────────────────────────────


@pytest.mark.parametrize("detail, shown", [
    # scripts/run_industry_ai.py's own shapes: what was saved, then the exception.
    ("2 new item(s) SAVED before the error; labels not written (new rows wait as "
     "'pending' for the next run or --relabel). RuntimeError: boom at db.example.internal:5432",
     "2 new item(s) SAVED before the error; labels not written (new rows wait as "
     "'pending' for the next run or --relabel). RuntimeError"),
    ("nothing saved. OperationalError: connection to server at \"10.0.0.5\" failed",
     "nothing saved. OperationalError"),
    ("KeyError: 'secret_key_name'", "KeyError"),
    ("TermsNotReviewedError: platform reddit at /home/runner/work/x.yaml",
     "TermsNotReviewedError"),
    ("SystemExit: 2", "SystemExit"),
    ("HTTPStatusError: Client error '401 Unauthorized' for url 'https://api.example/v1?key=abc'",
     "HTTPStatusError"),
    # Nothing the script would write: a generic line, never the text.
    ("connection failed. host db.example.internal is down: refused",
     "error (the run log has the details)"),
])
def test_an_error_run_sends_only_what_the_script_wrote_and_the_exception_type(detail, shown):
    assert _run_detail("error", detail) == shown
    assert _run_detail("error", detail[:500]) == shown


def test_an_ok_run_sends_its_summary_as_written():
    assert _run_detail("ok", "3 new item(s); text cleared on 0 row(s)") == (
        "3 new item(s); text cleared on 0 row(s)")
    assert _run_detail("ok", None) is None


def test_requests_are_split_by_agent_and_add_up_to_the_run():
    split = _requests_by_agent(
        {"x": 222, "reddit": 54},
        [{"domain": "watch", "platform": "x", "requests": 30},
         {"domain": "retail", "platform": "x", "requests": 5},
         {"domain": "watch", "platform": "x", "requests": 2}],
    )
    assert split == {"requests_keyword": {"x": 190, "reddit": 54}, "requests_watch": {"x": 32}}


# ── Admin: the read, on the test database ────────────────────────────────────


@pytest.fixture
def conn(test_dsn):
    from collect.db import apply_schema, connect
    from tests.conftest import assert_disposable, assert_safe_target

    assert_safe_target(test_dsn)
    connection = connect(test_dsn)
    try:
        assert_disposable(connection, test_dsn)
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        apply_schema(connection)
        connection.commit()
        yield connection
    finally:
        connection.rollback()
        connection.close()


def test_the_admin_read_on_an_empty_store_and_after_two_runs(conn):
    from collect.industry_ai import store

    empty = industry_ai_admin(conn)
    assert empty["items"] == {"stored": 0, "kept": 0, "pending": 0, "text_cleared": 0,
                              "text_due": 0}
    assert empty["runs"] == [] and empty["versions"] == {}
    assert "pipeline_version" not in empty, "the field is `rules_version` (#668 review)"

    store.start_run(conn, "r-old", mode="harvest", domains=["retail"], platforms=["x"],
                    pipeline_version="iai-1")
    store.finish_run(conn, "r-old", status="error", requests={"x": 3}, quota={},
                     queries=[], counts={},
                     detail="nothing saved. OperationalError: host db.internal refused")
    store.start_run(conn, "r-new", mode="harvest", domains=["retail"], platforms=["x"],
                    pipeline_version="iai-4")
    store.finish_run(conn, "r-new", status="ok", requests={"x": 40}, quota={},
                     queries=[{"domain": "watch", "platform": "x", "requests": 10}],
                     counts={}, detail="2 new item(s); text cleared on 0 row(s)")
    # Newest first, by start time.
    conn.execute("UPDATE iai_run SET started_at = %s WHERE id = 'r-old'",
                 (datetime.now(UTC) - timedelta(hours=1),))
    conn.commit()

    out = industry_ai_admin(conn)
    new, old = out["runs"]
    assert new["rules_version"] == "iai-4" and new["status"] == "ok"
    assert new["requests_keyword"] == {"x": 30} and new["requests_watch"] == {"x": 10}
    assert new["detail"] == "2 new item(s); text cleared on 0 row(s)"
    assert old["detail"] == "nothing saved. OperationalError", "the message never leaves"
    assert "db.internal" not in str(out)
