"""GET /models - the registry as a list, with advertised price.

The test worth having here is not "does it return rows". It is rule 6: a NULL
price must still be NULL by the time it reaches the caller. Five models in the
registry are routers with no rate of their own, and the cheapest thing a
serialiser can do to a missing number is turn it into 0.0 - which would put the
word "free" on five models that bill.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from judge.app import app
from judge.pages.roster import RosterReader


class _FakeConn:
    """Two queries, in the order RosterReader issues them."""

    def __init__(self, rows, observed_at=None):
        self._rows = rows
        self._observed_at = observed_at
        self.queries = []

    def execute(self, sql):
        self.queries.append(sql)
        if "pricing_history" in sql:
            return _Result([(self._observed_at,)])
        return _Result(self._rows)


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0]


def _row(name, price_in, price_out):
    return (
        f"mv_{name}", name, "vendor", f"vendor/{name}",
        price_in, price_out, None,
        128000, 4096,
        True, False, True, None, None,
    )


def test_null_price_stays_null_and_zero_stays_zero():
    """Rule 6. The router and the free model must not arrive identical."""
    conn = _FakeConn([_row("router", None, None), _row("free", 0, 0)])

    models = {m["display_name"]: m for m in RosterReader(conn).all().models}

    assert models["router"]["price_in"] is None
    assert models["router"]["price_out"] is None
    assert models["free"]["price_in"] == 0.0
    assert models["free"]["price_out"] == 0.0
    # The distinction is the whole point: if these compared equal, a UI could
    # not tell "no published rate" from "costs nothing".
    assert models["router"]["price_in"] != models["free"]["price_in"]


def test_summary_counts_the_unpriced_rather_than_hiding_them():
    conn = _FakeConn([_row("router", None, None), _row("paid", 1, 2)])
    assert "1 publish no rate at all" in RosterReader(conn).all().summary


def test_summary_omits_the_caveat_when_everything_is_priced():
    conn = _FakeConn([_row("paid", 1, 2)])
    assert "no rate at all" not in RosterReader(conn).all().summary


def test_ordered_by_name_not_by_price():
    """A default sort by cost would be a recommendation made without evidence."""
    conn = _FakeConn([])
    RosterReader(conn).all()
    assert "ORDER BY display_name" in conn.queries[0]
    assert "price" not in conn.queries[0].split("ORDER BY")[1]


def test_roster_503s_without_a_database(monkeypatch):
    """Same operational-state distinction every other read surface draws."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    response = TestClient(app).get("/models")

    assert response.status_code == 503
    assert "not the same as a board with nothing on it" in response.json()["detail"]


@pytest.mark.parametrize(
    "path",
    ["/models/mv1", "/models/google/gemini-2.5-flash"],
)
def test_the_detail_route_still_wins_for_ids(monkeypatch, path):
    """The literal /models must not swallow /models/{id:path}.

    A 503 proves the request reached the detail handler and stopped at the
    database; a 200 with a roster in it would mean the new route had eaten
    every model page.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)

    response = TestClient(app).get(path)

    assert response.status_code == 503
