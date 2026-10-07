"""RapidAPI consumption across a quota reset is never negative.

Until 2026-10-07 `/admin/usage` read consumption as first-remaining minus
last-remaining. X's quota reset twice (98,770 -> 98,946 on 2026-09-18 and
98,890 -> 99,999 on 2026-09-29, same key), and the page showed -1,018 requests.
`_quota_consumption` sums reading to reading instead. No database.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from judge.app import _quota_consumption

LIMIT = 100_000


def _at(hours: int) -> datetime:
    return datetime(2026, 9, 17, tzinfo=UTC) + timedelta(hours=hours)


def test_no_reset_reads_exactly_as_first_minus_last():
    out = _quota_consumption([(_at(0), 999_951, 1_000_000), (_at(24), 999_621, 1_000_000)])
    assert out["consumed"] == 330 and out["resets"] == 0
    assert out["consumed_is_a_floor"] is False
    assert out["per_day"] == 330


def test_a_reset_counts_the_new_window_from_the_limit_and_is_a_floor():
    rows = [(_at(0), 98_949, LIMIT), (_at(10), 98_770, LIMIT),   # 179 used
            (_at(20), 98_946, LIMIT),                            # reset: 1,054 used since
            (_at(30), 98_890, LIMIT),                            # 56 used
            (_at(40), 99_999, LIMIT),                            # reset: 1 used since
            (_at(50), 99_967, LIMIT)]                            # 32 used
    out = _quota_consumption(rows)
    assert out["consumed"] == 179 + 1_054 + 56 + 1 + 32
    assert out["consumed"] > 0, "a reset must never read as negative consumption"
    assert out["resets"] == 2 and out["consumed_is_a_floor"] is True


def test_a_rise_with_no_limit_read_is_a_floor_not_a_guess():
    out = _quota_consumption([(_at(0), 500, None), (_at(1), 900, None), (_at(2), 850, None)])
    assert out["consumed"] == 50 and out["consumed_is_a_floor"] is True


def test_one_reading_has_no_rate():
    out = _quota_consumption([(_at(0), 500, LIMIT)])
    assert out["consumed"] is None and out["per_day"] is None and out["readings"] == 1
