"""The launch verdict (judge/verdict.py, /verdict): a prototype, 2026-11-03.

Pinned without a database, through a connection that answers by query: the
contract loads and refuses windows that overlap or run backwards; an empty id
is refused before any query; an unknown model is said, not dropped; a model
with no release date has no windows and says why (rule 6); a window not yet
begun is not counted; the listing's words are not repeated (2026-11-03
review); one week is read the same way and a bad week is refused; and both
reads are public.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from judge import verdict

RELEASED = date(2026, 9, 22)


class FakeConn:
    def __init__(self, model_row):
        self.model_row = model_row
        self.queries: list[str] = []

    def execute(self, sql, params=()):
        self.queries.append(sql)
        self._sql = sql
        return self

    def fetchone(self):
        if "FROM model_version v WHERE" in self._sql:
            return self.model_row
        if "SELECT min(d.created_at)" in self._sql:
            return (datetime(2026, 9, 23, 8, tzinfo=UTC),)
        return (3, 2)  # posts, people

    def fetchall(self):
        if "be.name, be.section, be.polarity" in self._sql:
            return [("Coding agents", "best_for", "negative", 2),
                    ("Coding agents", "best_for", "positive", 1)]
        return [("positive", 1, 1), ("negative", 2, 2)]


@pytest.fixture(autouse=True)
def _no_feed_reports(monkeypatch):
    """The feed's reports are read through judge/feed/items.py; the window
    tests here pin the counts, and test_said_* below pin the examples."""
    monkeypatch.setattr(verdict, "_feed_reports", lambda conn, model_id: {})


def _row(released=RELEASED):
    return ("mv1", "p/m", "P: M", "p", released)


def test_the_contract_loads_with_every_value():
    r = verdict.rules()
    assert r["windows"] and r["top_topics"] >= 1 and r["quotes_per_side"] >= 1
    assert "metric" not in r["sections"], "a figure's quote means nothing on its own"
    starts = [w["from_day"] for w in r["windows"]]
    assert starts == sorted(starts)


def test_windows_that_overlap_are_refused(monkeypatch):
    from judge import config

    monkeypatch.setattr(config, "_read", lambda name: {
        "top_topics": 4, "quotes_per_side": 2, "sections": ["capability"],
        "windows": [{"key": "a", "label": "A", "from_day": 0, "to_day": 10},
                    {"key": "b", "label": "B", "from_day": 5, "to_day": 20}]})
    with pytest.raises(ValueError, match="without overlap"):
        verdict.rules()


def test_a_missing_contract_value_is_refused(monkeypatch):
    from judge import config

    monkeypatch.setattr(config, "_read", lambda name: {"top_topics": 4})
    with pytest.raises(ValueError, match="contract/verdict.yaml"):
        verdict.rules()


def test_an_empty_id_is_refused_before_any_query():
    conn = FakeConn(_row())
    with pytest.raises(verdict.VerdictRequestError):
        verdict.verdict(conn, "  ")
    assert conn.queries == []


def test_an_unknown_model_is_said():
    assert verdict.verdict(FakeConn(None), "p/nope") == {"model": None, "unknown": "p/nope"}


def test_no_release_date_means_no_windows_and_says_why():
    out = verdict.verdict(FakeConn(_row(released=None)), "p/m", today=date(2026, 11, 3))
    assert out["windows"] is None and "release date" in out["reason"]


def test_the_listing_words_are_not_repeated_here():
    """The model page shows its description once, at the top (2026-11-03 review)."""
    out = verdict.verdict(FakeConn(_row()), "p/m", today=date(2026, 11, 3))
    assert "listing" not in out


def test_one_week_is_counted_like_a_window():
    out = verdict.week(FakeConn(_row()), "p/m", date(2026, 9, 28), today=date(2026, 11, 3))
    assert (out["from"], out["to"], out["state"]) == ("2026-09-28", "2026-10-04", "closed")
    assert out["by_polarity"]["negative"] == {"posts": 2, "people": 2}
    future = verdict.week(FakeConn(_row()), "p/m", date(2026, 12, 7), today=date(2026, 11, 3))
    assert future["state"] == "not_yet" and "posts" not in future


def test_a_week_that_is_not_a_date_is_refused():
    assert verdict.parse_week("2026-09-28") == date(2026, 9, 28)
    with pytest.raises(verdict.VerdictRequestError):
        verdict.parse_week("last week")


def test_windows_after_release_are_counted_and_a_future_one_is_not():
    conn = FakeConn(_row())
    out = verdict.verdict(conn, "p/m", today=date(2026, 10, 1))  # day 9
    states = {w["key"]: w["state"] for w in out["windows"]}
    assert states == {"launch": "closed", "settling": "open", "lived_with": "not_yet"}
    launch = out["windows"][0]
    assert launch["by_polarity"]["negative"] == {"posts": 2, "people": 2}
    # A side nobody reported on is a zero count of posts, kept beside the others.
    assert launch["by_polarity"]["neutral"] == {"posts": 0, "people": 0}
    assert launch["topics"][0] == {"name": "Coding agents", "section": "best_for",
                                   "positive": 1, "negative": 2, "neutral": 0}
    assert launch["said"] == {"positive": [], "negative": []}
    assert "posts" not in out["windows"][2]
    assert out["first_problem_report"].startswith("2026-09-23")


def _entry(doc, source, polarity, quote, day=24):
    return {"section": "capability", "slug": "reasoning", "name": "Reasoning",
            "polarity": polarity, "quote": quote, "document_id": doc, "source": source,
            "url": f"https://example.com/{doc}", "posted_at": datetime(2026, 9, day, tzinfo=UTC)}


class ParaConn:
    """Answers the paraphrase and embed reads for test_said_*."""

    def __init__(self, paraphrases):
        self.paraphrases = paraphrases

    def execute(self, sql, params=()):
        self._rows = self.paraphrases if "feed_paraphrase" in sql else []
        return self

    def fetchall(self):
        return self._rows


def test_said_shows_paraphrases_never_quotes_and_reads_reddit_and_x_too():
    from judge.feed import items

    reports = {
        "hn1": [_entry("hn1", "hackernews", "negative", "it got lazier", day=25)],
        "x1": [_entry("x1", "x", "positive", "great at planning", day=24)],
    }
    conn = ParaConn([(d, f"paraphrase of {d}", items.excerpts_digest(es))
                     for d, es in reports.items()])
    out = verdict._said(conn, "mv1", reports, verdict.rules(), date(2026, 9, 22), date(2026, 9, 28))
    assert [x["text"] for x in out["negative"]] == ["paraphrase of hn1"]
    assert [x["text"] for x in out["positive"]] == ["paraphrase of x1"]
    assert out["negative"][0]["source"]["kind"] == "link"
    # X is cited only as its own embed, which lives in the feed - no link typed here.
    assert out["positive"][0]["source"]["kind"] != "link"
    assert "quote" not in out["negative"][0]


def test_said_skips_a_stale_paraphrase_and_a_held_source():
    reports = {
        "old": [_entry("old", "hackernews", "negative", "now different words")],
        "bsky": [_entry("bsky", "bluesky", "negative", "held source")],
    }
    conn = ParaConn([("old", "written from other excerpts", "not-the-digest"),
                     ("bsky", "should never show", "whatever")])
    out = verdict._said(conn, "mv1", reports, verdict.rules(), date(2026, 9, 22), date(2026, 9, 28))
    assert out == {"positive": [], "negative": []}


def test_the_page_is_a_public_read():
    from starlette.requests import Request

    from judge import gate

    for path in ("/verdict", "/verdict/week"):
        req = Request({"type": "http", "method": "GET", "path": path, "query_string": b"id=a",
                       "headers": []})
        assert gate.is_public_read(req)
