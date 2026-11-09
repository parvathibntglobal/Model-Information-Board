"""The #602 admin routes are behind the gate, and the price fallback and the
seating bar answer only what they can know (#612 review, tests section).

No database for the gate and the fallback; the held-models route runs against
a fake connection so `meets_bar` is checked as the route computes it.
"""
from __future__ import annotations

import contextlib

import pytest
from fastapi.testclient import TestClient

from judge.app import app


@pytest.mark.parametrize("route", ["/admin/held-models", "/admin/sources", "/admin/settings"])
def test_the_new_admin_routes_need_a_token(monkeypatch, route):
    monkeypatch.setenv("API_TOKEN", "s3cret")
    assert TestClient(app).get(route).status_code == 401


def test_the_litellm_fallback_shows_only_where_openrouter_publishes_no_price():
    from judge.catalog import _fallback

    snap = {"google/veo-3.1": {"figures": [{"usd": 0.4}]}}
    assert _fallback(snap, "google/veo-3.1", None, None, {}) == snap["google/veo-3.1"]
    # OpenRouter prices it: LiteLLM's figure is history, never shown beside it.
    assert _fallback(snap, "google/veo-3.1", 1.0, 2.0, {"prompt": "0.000001"}) is None
    # Free on OpenRouter is a published answer too.
    assert _fallback(snap, "google/veo-3.1:free", None, None, {}) is None


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _HeldConn:
    """The two reads the held-models route makes."""

    def execute(self, sql, params=None):
        from datetime import datetime

        if "attributed_at IS NOT NULL" in sql:
            return _Rows([(5,)])
        at = datetime(2026, 11, 9)
        # surface, entries, authors, documents, first, last, spellings, names total
        return _Rows([
            ("Seedance 2.5", 48, 6, 30, at, at, ["Seedance 2.5", "seedance-2.5"], 2),
            ("Sora", 43, 1, 12, at, at, ["Sora"], 2),
        ])


def _held(monkeypatch, *, bar_text=None):
    import judge.app as app_mod

    @contextlib.contextmanager
    def conn():
        yield _HeldConn()

    monkeypatch.setattr(app_mod, "_conn", conn)
    if bar_text is not None:
        real = app_mod.Path.read_text

        def read_text(self, *a, **k):
            if self.name == "tracked_models.yaml":
                return bar_text
            return real(self, *a, **k)

        monkeypatch.setattr(app_mod.Path, "read_text", read_text)
    return app_mod.admin_held_models()


def test_meets_bar_needs_both_entries_and_authors(monkeypatch):
    d = _held(monkeypatch)
    by = {h["surface"]: h for h in d["held"]}
    assert by["Seedance 2.5"]["meets_bar"] is True   # 48 entries, 6 authors
    assert by["Sora"]["meets_bar"] is False          # 43 entries, but 1 author
    assert by["Seedance 2.5"]["spellings"] == ["Seedance 2.5", "seedance-2.5"]
    assert d["names_total"] == 2 and d["truncated"] is False


def test_an_unreadable_bar_is_unknown_not_unmet(monkeypatch):
    """#612 review, point 17: an unreadable bar read as "0 meet the bar"."""
    d = _held(monkeypatch, bar_text="models: [\n  - broken")
    assert d["bar_reason"] and all(h["meets_bar"] is None for h in d["held"])
