"""Admin -> Keywords: the snapshot loader and the endpoint that serves it."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from judge import gate, keywords_on_site
from judge.app import app


def test_a_missing_snapshot_says_so_instead_of_failing(tmp_path):
    data = keywords_on_site.load(tmp_path / "absent.json")
    assert data["available"] is False and data["rows"] == [] and data["tabs"] == []


def test_the_snapshot_is_served_as_written(tmp_path):
    f = tmp_path / "k.json"
    f.write_text(json.dumps({"tabs": [{"path": "/"}], "rows": [{"keyword": "rag", "path": "/"}], "placements": ["Title"]}),
                 encoding="utf-8")
    data = keywords_on_site.load(f)
    assert data["available"] is True and data["rows"][0]["keyword"] == "rag"


def test_the_committed_snapshot_leaves_out_the_two_excluded_columns():
    """Bookkeeping and the unmeasured demand guess never reach the dashboard."""
    if not keywords_on_site.PATH.exists():
        pytest.skip("no snapshot in this checkout")
    data = keywords_on_site.load()
    keys = {k for r in data["rows"] for k in r}
    assert not {"sheets", "demand"} & keys
    assert not any("Demand" in k or "Found in" in k for k in keys)
    assert all(r["path"] in {t["path"] for t in data["tabs"]} for r in data["rows"])


def test_the_dashboard_is_not_a_public_read():
    """It lives behind the sign-in, like the rest of Admin."""
    from starlette.requests import Request

    req = Request({"type": "http", "method": "GET", "path": "/admin/seo-keywords", "query_string": b"", "headers": []})
    assert not gate.is_public_read(req)
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        assert TestClient(app).get("/admin/seo-keywords").status_code == 401


def test_the_older_admin_keywords_route_is_left_alone():
    """`/admin/keywords` is the search terms each platform is sent; the dashboard
    has its own address and must not shadow it."""
    handlers = {r.path: r.endpoint.__name__ for r in app.routes if hasattr(r, "endpoint")}
    assert handlers["/admin/seo-keywords"] == "admin_seo_keywords"
    assert handlers["/admin/keywords"] != "admin_seo_keywords"
