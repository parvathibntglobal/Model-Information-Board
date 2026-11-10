"""Kite Pulse outreach spend log and daily cap (common/spend.py). No database:
the cap's decision is checked against a fake connection that answers today()."""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

OUTREACH = Path(__file__).resolve().parent.parent / "web" / "src" / "kitepulse" / "outreach"
if str(OUTREACH) not in sys.path:
    sys.path.insert(0, str(OUTREACH))

from common import spend  # noqa: E402

BUDGET = Decimal("0.10")


# --- the budget has no default ---------------------------------------------

def test_an_unset_budget_stops_rather_than_meaning_no_limit(monkeypatch):
    monkeypatch.delenv(spend.BUDGET_ENV, raising=False)
    with pytest.raises(spend.SpendError, match="is not set"):
        spend.daily_budget()
    monkeypatch.setenv(spend.BUDGET_ENV, "  ")
    with pytest.raises(spend.SpendError, match="is not set"):
        spend.daily_budget()


@pytest.mark.parametrize("raw", ["abc", "0", "-1", "nan", "inf"])
def test_a_bad_budget_is_refused(monkeypatch, raw):
    monkeypatch.setenv(spend.BUDGET_ENV, raw)
    with pytest.raises(spend.SpendError):
        spend.daily_budget()


def test_the_decided_budget_reads_as_ten_cents(monkeypatch):
    monkeypatch.setenv(spend.BUDGET_ENV, "0.10")
    assert spend.daily_budget() == BUDGET


def test_env_example_carries_the_decided_budget():
    text = (OUTREACH.parents[3] / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^OUTREACH_DAILY_BUDGET_USD=0\.10$", text, re.M)


# --- the cap's decision -----------------------------------------------------

class _Conn:
    """Answers today()'s one query with (calls, usd sum, unpriced count)."""

    def __init__(self, calls, usd, unpriced):
        self.row = (calls, usd, unpriced)

    def execute(self, _sql, _params):
        row = self.row

        class _R:
            def fetchone(_self):
                return row
        return _R()


NOW = datetime(2026, 11, 9, 15, 30, tzinfo=UTC)


def test_under_the_cap_a_call_may_go_ahead():
    t = spend.check(_Conn(3, Decimal("0.0060"), 0), BUDGET, NOW)
    assert t.calls == 3 and not t.is_floor


def test_at_the_cap_the_run_stops_and_says_when_it_resets():
    with pytest.raises(spend.BudgetReached, match="2026-11-10 00:00 UTC"):
        spend.check(_Conn(50, Decimal("0.10"), 0), BUDGET, NOW)


def test_a_call_with_no_reported_cost_stops_the_day_instead_of_counting_as_free():
    with pytest.raises(spend.BudgetReached, match="only a floor"):
        spend.check(_Conn(2, Decimal("0.001"), 1), BUDGET, NOW)


def test_the_day_is_utc():
    late_in_india = datetime(2026, 11, 10, 3, 0, tzinfo=UTC)  # 08:30 IST on the 10th
    assert spend.day_start(late_in_india) == datetime(2026, 11, 10, tzinfo=UTC)


# --- what record() refuses before any SQL ----------------------------------

def test_only_the_two_phase_2_steps_may_record():
    with pytest.raises(ValueError, match="step must be one of"):
        spend.record(None, step="blog", model="m", thread_id=None,
                     input_tokens=1, output_tokens=1, usd=0.001)
    with pytest.raises(ValueError, match="model is required"):
        spend.record(None, step="draft", model=" ", thread_id=None,
                     input_tokens=1, output_tokens=1, usd=0.001)


def test_the_steps_in_code_are_the_steps_the_database_allows():
    sql = (OUTREACH / "migrations" / "20261109T1800_kp_outreach_spend.sql").read_text(
        encoding="utf-8")
    in_sql = set(re.findall(r"'(\w+)'", sql.split("kp_outreach_spend_step_ck")[1].split(")")[0]))
    assert in_sql == set(spend.STEPS)


def test_an_unpriced_call_is_stored_as_null_never_zero():
    sql = (OUTREACH / "migrations" / "20261109T1800_kp_outreach_spend.sql").read_text(
        encoding="utf-8")
    assert re.search(r"^\s+usd\s+numeric\(12, 8\),$", sql, re.M), "usd must be nullable"
    assert "DEFAULT 0" not in sql
