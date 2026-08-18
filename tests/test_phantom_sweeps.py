"""`last_swept_at` set while nothing has ever swept.

The third instance of one shape, and the only cheaply checkable one. `in_window`
carried a schema default that read as computed; `author` carried 4,391 rows from
a hand-run that read as harvested; `last_swept_at` carried one row set by an
ad-hoc `mark_swept` call that read as swept.

What makes this one checkable is that it is a CONTRADICTION rather than an
absence — a swept model with no harvest behind it — and the other two are not.
See `docs/measurements/uncalled-writers.md` §3.
"""

from __future__ import annotations

import pytest

from collect.registry.assertions import (
    SweptWithoutASweepError,
    assert_no_phantom_sweeps,
)


class _Conn:
    """Answers the one query the assertion asks."""

    def __init__(self, swept: int, harvests: int) -> None:
        self._row = (swept, harvests)

    def execute(self, _sql, _params=None):
        return self

    def fetchone(self):
        return self._row


def test_a_swept_model_with_no_harvest_is_refused():
    """The state staging was in on 2026-08-18: one row, zero harvests."""
    with pytest.raises(SweptWithoutASweepError, match="last_swept_at"):
        assert_no_phantom_sweeps(_Conn(1, 0), environment="staging")


def test_the_refusal_says_what_it_costs():
    """A refusal that does not name the consequence gets overridden."""
    with pytest.raises(SweptWithoutASweepError) as excinfo:
        assert_no_phantom_sweeps(_Conn(3, 0), environment="production")
    message = str(excinfo.value)
    assert "rotation will skip" in message
    assert "coverage page" in message
    assert "NEVER SWEPT" in message


def test_sweeps_with_a_harvest_behind_them_pass():
    """The ordinary case once harvest runs. Not a ban on last_swept_at."""
    assert_no_phantom_sweeps(_Conn(40, 12), environment="staging")


def test_no_sweeps_at_all_passes():
    """NULL everywhere is the truthful state today, not a failure."""
    assert_no_phantom_sweeps(_Conn(0, 0), environment="staging")


def test_development_is_exempt():
    """Exercising `mark_swept` against a local database is how it should be
    tried. The exemption matches `assert_no_fixtures`."""
    assert_no_phantom_sweeps(_Conn(1, 0), environment="development")


def test_it_is_wired_into_preflight():
    """An assertion with no caller is the defect this file is about."""
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "collect" / "ops" / "preflight.py"
    ).read_text(encoding="utf-8")
    assert "assert_no_phantom_sweeps(" in source
