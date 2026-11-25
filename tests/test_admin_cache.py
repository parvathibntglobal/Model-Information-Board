"""Admin sections are kept for a short while (judge/admin_cache.py, 2026-11-25).

Through the real app, with `/admin/schedules`' builder faked (no GitHub, no
database): a section is worked out once and kept; a successful write empties the
cache; `X-Recount: 1` (Admin's Refresh) works it out afresh; an error is never kept;
past its fresh time the kept answer is sent and recounted in the background.
"""

from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

from judge import admin_cache, gate
from judge.app import app


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    gate._reset_for_tests()
    # Off for the rest of the suite (tests/conftest.py); on here, where it is tested.
    monkeypatch.setattr(admin_cache, "ENABLED", True)
    admin_cache.clear()
    yield
    admin_cache.clear()
    gate._reset_for_tests()


@pytest.fixture
def counted(monkeypatch):
    """`/admin/schedules`, counting how often it is really worked out."""
    from judge import sections_status

    calls = {"n": 0, "fail": False}

    def schedules():
        calls["n"] += 1
        if calls["fail"]:
            raise RuntimeError("GitHub did not answer")
        return {"feeds": [], "n": calls["n"]}

    monkeypatch.setattr(sections_status, "schedules", schedules)
    return calls


def test_a_section_is_worked_out_once_and_kept(counted):
    c = TestClient(app)
    assert c.get("/admin/schedules").json()["n"] == 1
    assert c.get("/admin/schedules").json()["n"] == 1
    assert counted["n"] == 1


def test_refresh_works_it_out_afresh(counted):
    c = TestClient(app)
    c.get("/admin/schedules")
    assert c.get("/admin/schedules", headers={"X-Recount": "1"}).json()["n"] == 2
    # ...and that answer is the one kept now.
    assert c.get("/admin/schedules").json()["n"] == 2


def test_a_successful_write_empties_the_cache_and_a_refused_one_does_not(counted):
    """A throwaway write route on the real app, so the middleware itself is tested."""
    from fastapi import HTTPException

    def ok():
        return {"saved": True}

    def refused():
        raise HTTPException(status_code=409, detail="no")

    app.add_api_route("/admin/_test_write_ok", ok, methods=["POST"])
    app.add_api_route("/admin/_test_write_refused", refused, methods=["POST"])
    try:
        c = TestClient(app)
        c.get("/admin/schedules")
        assert c.post("/admin/_test_write_refused").status_code == 409
        assert c.get("/admin/schedules").json()["n"] == 1, "a refused write keeps the cache"
        assert c.post("/admin/_test_write_ok").status_code == 200
        assert c.get("/admin/schedules").json()["n"] == 2, "a successful write empties it"
    finally:
        app.router.routes[:] = [r for r in app.router.routes
                                if getattr(r, "path", "") not in
                                ("/admin/_test_write_ok", "/admin/_test_write_refused")]


def test_an_error_is_never_kept(counted):
    c = TestClient(app, raise_server_exceptions=False)
    counted["fail"] = True
    assert c.get("/admin/schedules").status_code == 500
    counted["fail"] = False
    assert c.get("/admin/schedules").json()["n"] == 2


def test_past_its_fresh_time_the_kept_answer_is_sent_and_recounted(monkeypatch):
    built = {"n": 0}
    done = threading.Event()

    def build():
        built["n"] += 1
        if built["n"] > 1:
            done.set()
        return {"n": built["n"]}

    key = ("t", ())
    assert admin_cache.get(key, build, fresh=0, max_age=60)["n"] == 1
    # fresh=0: already past its fresh time, so the kept answer comes back at once...
    assert admin_cache.get(key, build, fresh=0, max_age=60)["n"] == 1
    # ...and one background recount replaces it.
    assert done.wait(5)
    for t in list(threading.enumerate()):
        if t.name == "admin-cache-refresh":
            t.join(5)
    assert admin_cache.get(key, build, fresh=60, max_age=120)["n"] == 2


def test_past_its_max_age_it_is_recounted_while_the_visitor_waits():
    built = {"n": 0}

    def build():
        built["n"] += 1
        return {"n": built["n"]}

    key = ("old", ())
    admin_cache.get(key, build, fresh=0, max_age=0)
    assert admin_cache.get(key, build, fresh=0, max_age=0)["n"] == 2


def test_an_answer_that_could_not_read_its_data_is_not_kept(counted, monkeypatch):
    """`reason` / `unreadable` means a database or table was missing: try again next time."""
    from judge import sections_status

    answers = iter([{"feeds": [], "unreadable": "no database"}, {"feeds": [], "n": 2}])
    monkeypatch.setattr(sections_status, "schedules", lambda: next(answers))
    c = TestClient(app)
    assert c.get("/admin/schedules").json()["unreadable"] == "no database"
    assert c.get("/admin/schedules").json()["n"] == 2
