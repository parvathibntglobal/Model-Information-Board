"""The price changelog behind /price-changes (judge/price_changes.py).

Each flag is a fixed rule over two observed prices; these pin each one on a
small hand-made history, so a change to a rule shows up here.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from judge import gate, price_changes
from judge.app import app

NOW = datetime(2026, 10, 27, 12, tzinfo=UTC)


def at(hours_ago: float) -> datetime:
    return NOW - timedelta(hours=hours_ago)


class FakeConn:
    """Answers HISTORY_SQL with rows in its column order, sorted like the query."""

    def __init__(self, rows):
        self.rows = sorted(rows, key=lambda r: (r[0], r[1]))

    def execute(self, sql):
        assert sql == price_changes.HISTORY_SQL
        return self

    def fetchall(self):
        return self.rows


def row(mid, seen, pin, pout, *, provider="acme", polled=NOW, cached=None):
    return (mid, seen, None if pin is None else Decimal(str(pin)),
            None if pout is None else Decimal(str(pout)), cached,
            f"{provider}/{mid}", f"Acme: {mid}", provider, polled)


def run(rows, **kw):
    return price_changes.changes(FakeConn(rows), now=NOW, **kw)


def only(data):
    assert len(data["changes"]) == 1
    return data["changes"][0]


def test_the_contract_is_complete_and_sane():
    r = price_changes.rules()
    assert 0 < r["min_change_pct"] <= r["big_change_pct"]
    assert r["wave_min_models"] >= 2


def test_a_missing_threshold_is_refused_not_defaulted(monkeypatch):
    import judge.config

    monkeypatch.setattr(judge.config, "_read", lambda name: {"min_change_pct": 10})
    with pytest.raises(price_changes.PriceChangesContractError):
        price_changes.rules()


def test_a_first_observation_is_not_a_change():
    assert run([row("m", at(100), 1, 2)])["changes"] == []


def test_a_held_big_cut_is_newsworthy_and_unconfirmed():
    c = only(run([row("m", at(200), 1.0, 4.0), row("m", at(100), 0.5, 2.0)]))
    assert c["change_pct"]["price_in"] == -50.0 and c["largest_pct"] == -50.0
    assert c["flags"] == ["cut"]
    assert c["newsworthy"] is True
    assert c["confirmed"] is False and c["source"] == "openrouter"


def test_a_rise_is_flagged_on_the_larger_move():
    c = only(run([row("m", at(200), 1.0, 1.0), row("m", at(100), 1.05, 1.5)]))
    assert c["largest_pct"] == 50.0 and "rise" in c["flags"] and c["newsworthy"]


def test_a_small_move_is_listed_but_not_newsworthy():
    c = only(run([row("m", at(200), 1.0, 1.0), row("m", at(100), 0.95, 0.95)]))
    assert c["flags"] == [] and c["newsworthy"] is False


def test_a_change_not_yet_polled_for_the_hold_is_settling():
    c = only(run([row("m", at(200), 1.0, 1.0, polled=at(2)),
                  row("m", at(5), 0.5, 0.5, polled=at(2))]))
    assert "settling" in c["flags"] and c["newsworthy"] is False


def test_a_change_undone_within_the_bounce_window_is_bounced():
    data = run([row("m", at(300), 1.0, 1.0), row("m", at(200), 0.5, 0.5),
                row("m", at(100), 1.0, 1.0)])
    cut = next(c for c in data["changes"] if c["after"]["price_in"] == 0.5)
    assert "bounced" in cut["flags"] and cut["newsworthy"] is False


def test_going_free_has_no_percentage_from_nothing_and_is_flagged():
    c = only(run([row("m", at(200), 1.0, 2.0), row("m", at(100), 0, 0)]))
    assert "free" in c["flags"] and c["newsworthy"]
    back = only(run([row("m", at(200), 0, 0), row("m", at(100), 1.0, 2.0)]))
    assert back["change_pct"]["price_in"] is None and back["largest_pct"] is None
    assert back["newsworthy"] is False


def test_a_price_not_stated_has_no_percentage():
    c = only(run([row("m", at(200), None, 2.0), row("m", at(100), 1.0, 2.0)]))
    assert c["change_pct"]["price_in"] is None and c["change_pct"]["price_out"] == 0.0


def test_a_provider_wave_needs_enough_models_the_same_day():
    rows = []
    for m in ("a", "b", "c"):
        rows += [row(m, at(200), 1.0, 1.0), row(m, at(100), 0.88, 0.88)]
    data = run(rows)
    assert all("wave" in c["flags"] and c["newsworthy"] for c in data["changes"])
    two = run(rows[:4])
    assert not any("wave" in c["flags"] for c in two["changes"])


def test_the_window_is_clamped_to_the_contract():
    r = price_changes.rules()
    rows = [row("m", at(24 * 400), 1.0, 1.0), row("m", at(24 * 10), 0.5, 0.5)]
    assert run(rows, days=99999)["window_days"] == r["max_window_days"]
    assert run(rows, days=5)["changes"] == []
    assert run(rows)["window_days"] == r["default_window_days"]


def test_the_changelog_is_not_a_public_read():
    """Signed-in only, like the rest of Admin."""
    from starlette.requests import Request

    req = Request({"type": "http", "method": "GET", "path": "/admin/price-changes",
                   "query_string": b"", "headers": []})
    assert not gate.is_public_read(req)
    with pytest.MonkeyPatch.context() as m:
        m.setenv("API_TOKEN", "s3cret")
        assert TestClient(app).get("/admin/price-changes").status_code == 401
