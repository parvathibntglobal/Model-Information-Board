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
    """Answers HISTORY_SQL with rows in its column order, sorted like the query,
    and REGISTRY_SQL with the registry size and the newest poll of any model."""

    def __init__(self, rows, *, registry=10, newest_poll=NOW):
        self.rows = sorted(rows, key=lambda r: (r[0], r[1]))
        self.registry = (registry, newest_poll)
        self.last = None

    def execute(self, sql):
        assert sql in (price_changes.HISTORY_SQL, price_changes.REGISTRY_SQL)
        self.last = sql
        return self

    def fetchall(self):
        return self.rows

    def fetchone(self):
        assert self.last == price_changes.REGISTRY_SQL
        return self.registry


def row(mid, seen, pin, pout, *, provider="acme", polled=NOW, cached=None):
    return (mid, seen, None if pin is None else Decimal(str(pin)),
            None if pout is None else Decimal(str(pout)), cached,
            f"{provider}/{mid}", f"Acme: {mid}", provider, polled)


def run(rows, *, registry=10, newest_poll=NOW, **kw):
    conn = FakeConn(rows, registry=registry, newest_poll=newest_poll)
    return price_changes.changes(conn, now=NOW, **kw)


def only(data):
    assert len(data["changes"]) == 1
    return data["changes"][0]


def test_the_contract_is_complete_and_sane():
    r = price_changes.rules()
    assert r["big_change_pct"] > 0
    assert "min_change_pct" not in r
    assert r["wave_min_models"] >= 2
    assert r["unpolled_hours"] >= r["hold_hours"]


def test_a_missing_threshold_is_refused_not_defaulted(monkeypatch):
    import judge.config

    monkeypatch.setattr(judge.config, "_read", lambda name: {"big_change_pct": 20})
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
    assert all("wave" in c["flags"] and c["wave_size"] == 3 for c in data["changes"])
    two = run(rows[:4])
    assert not any("wave" in c["flags"] for c in two["changes"])
    assert all(c["wave_size"] is None for c in two["changes"])


def test_a_wave_is_a_label_never_a_reason_for_news():
    """Review on #579: a wave mostly measures OpenRouter repricing in bulk."""
    small, big = [], []
    for m in ("a", "b", "c"):
        small += [row(m, at(200), 1.0, 1.0), row(m, at(100), 0.88, 0.88)]
        big += [row(m, at(200), 1.0, 1.0), row(m, at(100), 0.5, 0.5)]
    assert not any(c["newsworthy"] for c in run(small)["changes"])
    assert all(c["newsworthy"] and "wave" in c["flags"] for c in run(big)["changes"])


def test_a_model_no_longer_polled_is_unpolled_not_settling():
    """Its newest change can never settle; it says why instead of waiting."""
    left = [row("m", at(200), 1.0, 1.0, polled=at(48)), row("m", at(50), 0.5, 0.5, polled=at(48))]
    c = only(run(left))
    assert "unpolled" in c["flags"] and "settling" not in c["flags"]
    assert c["newsworthy"] is False


def test_a_late_poll_run_does_not_make_every_model_unpolled():
    """Measured from the newest poll of any model, not from the clock."""
    late = [row("m", at(200), 1.0, 1.0, polled=at(48)), row("m", at(50), 0.5, 0.5, polled=at(48))]
    c = only(run(late, newest_poll=at(40)))
    assert "settling" in c["flags"] and "unpolled" not in c["flags"]


def test_the_counts_say_what_they_are_counted_over():
    """Rule 7: registry models with price history, of all registry models."""
    rows = [row("m", at(200), 1.0, 1.0), row("m", at(100), 0.5, 0.5), row("n", at(100), 1, 1)]
    data = run(rows, registry=277)
    assert data["population"] == {"models_with_history": 2, "registry_models": 277}
    assert data["newest_poll_at"] == NOW.isoformat()


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



# ── the settled price (2026-10-29) ────────────────────────────────────────────


def by_seen(data):
    return {c["seen_at"]: c for c in data["changes"]}


def test_a_rebound_to_the_usual_price_is_not_newsworthy():
    """$0.15 -> $0.045 -> $0.15: from the price just before, the last step is
    +233%; from the settled price nothing changed, and the cut did not last."""
    data = by_seen(run([row("m", at(400), 0.15, 0.5), row("m", at(120), 0.045, 0.14),
                        row("m", at(48), 0.15, 0.5)]))
    cut, back = data[at(120).isoformat()], data[at(48).isoformat()]
    assert "rise" in back["flags"] and back["largest_pct"] > 200  # the step, as before
    assert back["settled_pct"]["price_in"] == 0.0 and not back["newsworthy"]
    assert "reverted" in cut["flags"] and not cut["newsworthy"]


def test_a_price_that_keeps_flipping_is_unstable():
    rows = [row("m", at(h), p, 0.4) for h, p in ((400, 0.3), (300, 0.1), (200, 0.3), (100, 0.1))]
    newest = by_seen(run(rows))[at(100).isoformat()]
    assert "unstable" in newest["flags"] and not newest["newsworthy"]


def test_one_move_in_two_steps_is_told_by_the_later_step():
    data = by_seen(run([row("m", at(600), 0.14, 0.28), row("m", at(150), 0.03, 0.32),
                        row("m", at(60), 0.021, 0.32)]))
    first, later = data[at(150).isoformat()], data[at(60).isoformat()]
    assert "superseded" in first["flags"] and not first["newsworthy"]
    assert later["newsworthy"] and later["settled_before"]["price_in"] == 0.14


def test_a_newer_step_still_settling_does_not_hide_a_held_move():
    data = by_seen(run([row("m", at(600), 0.14, 0.28), row("m", at(150), 0.03, 0.28),
                        row("m", at(2), 0.029, 0.28)]))
    assert data[at(150).isoformat()]["newsworthy"], "the newer step is still settling"



def test_a_blip_to_paid_and_back_to_free_is_not_now_free():
    """#585 review: "now free" is judged from the settled price too."""
    data = by_seen(run([row("m", at(600), 0, 0), row("m", at(120), 0.2, 0.8),
                        row("m", at(48), 0, 0)]))
    back = data[at(48).isoformat()]
    assert "free" not in back["flags"] and not back["newsworthy"]


def test_a_later_price_not_stated_is_not_a_revert():
    """#585 review, rule 6: an unknown price is no evidence the move did not last."""
    data = by_seen(run([row("m", at(600), 1.0, 2.0), row("m", at(120), 0.4, 1.0),
                        row("m", at(60), None, 1.0)]))
    assert "reverted" not in data[at(120).isoformat()]["flags"]
