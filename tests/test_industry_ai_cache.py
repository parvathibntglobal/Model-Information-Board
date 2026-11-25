"""judge/industry_ai/cache.py: the "AI in industries" pages kept for a few minutes,
never a wait on a refresh, and never keeping an error or an unreadable-tables answer."""

from __future__ import annotations

import threading

import pytest

from judge.industry_ai import cache


@pytest.fixture(autouse=True)
def _fresh():
    cache.clear()
    yield
    cache.clear()


def test_a_view_is_worked_out_once_then_kept_with_when_it_was_counted():
    calls = []

    def build():
        calls.append(1)
        return {"kept": 5}

    first = cache.cached(("summary",), build)
    second = cache.cached(("summary",), build)
    assert calls == [1]
    assert first is second
    assert first["kept"] == 5 and first["counted_at"].endswith("+00:00")


def test_each_view_is_kept_apart():
    a = cache.cached(("domain", "retail"), lambda: {"name": "Retail"})
    b = cache.cached(("domain", "personal"), lambda: {"name": "Personal"})
    assert (a["name"], b["name"]) == ("Retail", "Personal")


def _join_refreshes():
    for t in threading.enumerate():
        if t.name == "industry-ai-refresh":
            t.join(5)


def test_an_old_answer_is_sent_at_once_and_refreshed_in_the_background(monkeypatch):
    cache.cached(("summary",), lambda: {"v": 1})
    monkeypatch.setattr(cache, "TTL_SECONDS", 0)
    assert cache.cached(("summary",), lambda: {"v": 2})["v"] == 1, "the old answer, not a wait"
    _join_refreshes()
    monkeypatch.setattr(cache, "TTL_SECONDS", 600)
    assert cache.cached(("summary",), lambda: {"v": 3})["v"] == 2, "the refresh replaced it"


def test_a_failed_refresh_keeps_the_old_answer(monkeypatch):
    cache.cached(("summary",), lambda: {"v": 1})
    monkeypatch.setattr(cache, "TTL_SECONDS", 0)

    def broken():
        raise RuntimeError("database down")

    assert cache.cached(("summary",), broken)["v"] == 1
    _join_refreshes()
    assert cache.cached(("summary",), broken)["v"] == 1


def test_an_error_is_raised_and_never_kept():
    def bad():
        raise ValueError("bad filter")

    with pytest.raises(ValueError):
        cache.cached(("domain", "x"), bad)
    assert cache.cached(("domain", "x"), lambda: {"ok": True})["ok"] is True


def test_an_unreadable_tables_answer_is_never_kept():
    calls = []

    def unmigrated():
        calls.append(1)
        return {"domains": [], "reason": "the Industry AI tables could not be read"}

    cache.cached(("summary",), unmigrated)
    cache.cached(("summary",), unmigrated)
    assert calls == [1, 1], "asked again, so a migration shows on the next load"


def test_at_most_max_entries_are_kept_least_recently_read_first(monkeypatch):
    monkeypatch.setattr(cache, "MAX_ENTRIES", 2)
    cache.cached(("a",), lambda: {"v": "a"})
    cache.cached(("b",), lambda: {"v": "b"})
    cache.cached(("a",), lambda: {"v": "a2"})  # read: now the most recent
    cache.cached(("c",), lambda: {"v": "c"})  # drops b
    assert cache.cached(("a",), lambda: {"v": "new"})["v"] == "a"
    assert cache.cached(("b",), lambda: {"v": "b2"})["v"] == "b2"


def test_an_answer_older_than_max_age_is_recounted_while_the_visitor_waits(monkeypatch):
    cache.cached(("summary",), lambda: {"v": 1})
    monkeypatch.setattr(cache, "MAX_AGE_SECONDS", 0)
    assert cache.cached(("summary",), lambda: {"v": 2})["v"] == 2, "not the old answer"


def test_if_that_recount_fails_the_old_answer_is_sent(monkeypatch):
    cache.cached(("summary",), lambda: {"v": 1})
    monkeypatch.setattr(cache, "MAX_AGE_SECONDS", 0)

    def broken():
        raise RuntimeError("database down")

    assert cache.cached(("summary",), broken)["v"] == 1


def test_an_over_age_view_is_recounted_once_however_many_visitors_wait(monkeypatch):
    """#665, after merge: visitors arriving during a recount get the old answer, and
    only one recount runs."""
    cache.cached(("summary",), lambda: {"v": 1})
    monkeypatch.setattr(cache, "MAX_AGE_SECONDS", 0)
    started, release, calls = threading.Event(), threading.Event(), []

    def slow():
        calls.append(1)
        started.set()
        release.wait(5)
        return {"v": 2}

    first = []
    t = threading.Thread(target=lambda: first.append(cache.cached(("summary",), slow)))
    t.start()
    assert started.wait(5)
    others = [cache.cached(("summary",), slow)["v"] for _ in range(3)]
    release.set()
    t.join(5)
    assert others == [1, 1, 1], "the old answer while the recount runs"
    assert first[0]["v"] == 2 and calls == [1], "one recount, its answer kept"
