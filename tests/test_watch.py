"""One model's pulse (judge/watch.py, /watch): a prototype, 2026-11-02.

What is pinned without a database: the contract loads with every key and
refuses a missing one; the reads count exactly what the verdict counts (one
shared clause, UTC weeks), so a week's bar and the week it opens agree (#597
review); "new since your last look" is new TO THE BOARD, whatever the post's
date; the response carries only what the page reads - no quote, no price, no
event (#597 review, rule 9); a list longer than the contract allows is refused
before any query; the last-look date parses or is refused; the page is a
public read.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from judge import verdict, watch


def test_the_contract_loads_with_every_value():
    r = watch.rules()
    assert set(r) == {"window_days", "max_models", "trend_weeks"}
    assert min(r.values()) >= 1


def test_a_missing_contract_value_is_refused(monkeypatch):
    from judge import config

    monkeypatch.setattr(config, "_read", lambda name: {"window_days": 30})
    with pytest.raises(ValueError, match="contract/watch.yaml"):
        watch.rules()


@pytest.mark.parametrize("make", [watch._counts_sql, watch._new_sql, watch._trend_sql])
def test_every_read_counts_what_the_verdict_counts(make):
    sql, _ = make()
    assert verdict.COUNTED in sql, "declined entries and other sections must not count here"
    assert "::date" not in sql.replace(verdict.POST_WEEK, ""), "a day or week is taken in UTC"


def test_the_trend_weeks_are_utc_weeks():
    sql, _ = watch._trend_sql()
    assert verdict.POST_WEEK in sql


def test_new_since_your_last_look_is_new_to_the_board_whatever_the_post_date():
    sql, _ = watch._new_sql()
    assert "be.created_at >= %s" in sql
    assert "d.created_at" not in sql


class FakeConn:
    def execute(self, sql, params=()):
        self._sql = sql
        return self

    def fetchall(self):
        if "FROM model_version" in self._sql:
            return [("mv1", "p/m", date(2026, 9, 22))]
        if "AS wk" in self._sql:
            return [("mv1", date(2026, 10, 26), "negative", 2)]
        return [("mv1", "positive", 5), ("mv1", "negative", 2)]


def test_the_response_carries_only_what_the_page_reads():
    out = watch.watch(FakeConn(), ["p/m", "p/unknown"], since=datetime(2026, 10, 30, tzinfo=UTC),
                      now=datetime(2026, 11, 3, 12, tzinfo=UTC))
    assert set(out) == {"models", "window_days"}
    (m,) = out["models"]
    assert set(m) == {"id", "release_date", "reports", "new_since", "trend"}
    assert m["reports"] == {"positive": 5, "negative": 2, "neutral": 0}
    assert len(m["trend"]) == watch.rules()["trend_weeks"]
    assert m["trend"][-2] == {"week": "2026-10-26", "positive": 0, "negative": 2, "neutral": 0}


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


def test_the_page_is_a_public_read():
    from starlette.requests import Request

    from judge import gate

    req = Request({"type": "http", "method": "GET", "path": "/watch", "query_string": b"ids=a",
                   "headers": []})
    assert gate.is_public_read(req)
