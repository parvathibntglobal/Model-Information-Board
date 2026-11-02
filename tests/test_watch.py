"""Watch my models (judge/watch.py, /watch): a prototype, 2026-11-02.

What is pinned without a database: the contract loads with every key and
refuses a missing one; a listed price prints as listed, and an unpublished one
stays None (rule 6); a list longer than the contract allows is refused before
any query; the last-look date parses or is refused; the page is a public read.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from judge import watch


def test_the_contract_loads_with_every_value():
    r = watch.rules()
    assert r["window_days"] >= 1 and r["max_models"] >= 1 and r["trend_weeks"] >= 1
    assert "metric" not in r["quote_sections"], "a figure's quote means nothing on its own"


def test_a_missing_contract_value_is_refused(monkeypatch):
    from judge import config

    monkeypatch.setattr(config, "_read", lambda name: {"window_days": 30})
    with pytest.raises(ValueError, match="contract/watch.yaml"):
        watch.rules()


@pytest.mark.parametrize(("raw", "shown"), [
    ("2", "$2.00"), ("0.075", "$0.075"), ("0.7505999999999999", "$0.7506"), ("15", "$15.00"),
    ("0", "$0.00"), (None, None), ("", None), ("not a number", None),
])
def test_a_listed_price_prints_as_listed_and_none_stays_none(raw, shown):
    assert watch._price(raw) == shown


def test_too_many_models_are_refused_before_any_query():
    class NoQuery:
        def execute(self, *_a, **_k):
            raise AssertionError("no query for a refused request")

    many = [f"p/m{i}" for i in range(watch.rules()["max_models"] + 1)]
    with pytest.raises(watch.WatchRequestError, match="at most"):
        watch.watch(NoQuery(), many)


def test_the_last_look_parses_or_is_refused():
    assert watch.parse_since(None) is None
    assert watch.parse_since("2026-11-01T10:00:00Z") == datetime(2026, 11, 1, 10, tzinfo=UTC)
    with pytest.raises(watch.WatchRequestError):
        watch.parse_since("last tuesday")


def test_a_price_event_lists_only_prices_and_keeps_unpublished_as_none():
    e = watch._event("price-change", datetime(2026, 11, 1, tzinfo=UTC), {
        "changed": ["price_in", "price_out", "context"],
        "from": {"price_in": "0.15", "price_out": None},
        "to": {"price_in": "0.075", "price_out": "0.3"}})
    assert e["changes"] == [{"field": "price_in", "from": "$0.15", "to": "$0.075"},
                            {"field": "price_out", "from": None, "to": "$0.30"}]


def test_the_page_is_a_public_read():
    from starlette.requests import Request

    from judge import gate

    req = Request({"type": "http", "method": "GET", "path": "/watch", "query_string": b"ids=a",
                   "headers": []})
    assert gate.is_public_read(req)
