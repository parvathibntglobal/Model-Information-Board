"""Outreach's model spend: one row per paid call, and the daily cap.

Every model call outreach makes (phase 2: shortlist, draft) is recorded in
`kp_outreach_spend`, in outreach's OWN database (ARCHITECTURE.md decision #10,
2026-11-09). It is not in MIB's `spend_ledger`, so MIB's Admin -> API usage
does not show it; `spend_report.py` does.

THE CAP. `OUTREACH_DAILY_BUDGET_USD` is the most outreach may spend in one UTC
day, across every step, model and machine (this table is shared by everyone
pointing at the same database). `check()` runs BEFORE each call and raises
`BudgetReached` when the day is spent. A run that hits it stops; the threads
it had not reached wait for the next day and are never dropped.

The variable has NO DEFAULT (rule 12): unset or unreadable stops the run,
because "no cap configured" must never read as "no limit".

A CALL WITH NO REPORTED COST STOPS THE DAY TOO. `usd` is what OpenRouter
reported. When it reports none, the row's usd is NULL - not 0, an unpriced
call is not a free one (rule 6) - and from then until midnight UTC the day's
total is only a floor, so the cap can no longer be checked. `check()` refuses
rather than spend against a number it knows is too small.

The day boundary is UTC, as MIB's spend ledger does it: a local boundary would
move with the server's timezone.
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

BUDGET_ENV = "OUTREACH_DAILY_BUDGET_USD"
STEPS = ("shortlist", "draft")


class SpendError(RuntimeError):
    """The cap cannot be checked: no budget, or a bad one."""


class BudgetReached(RuntimeError):
    """Today's outreach budget is spent, or can no longer be known."""


def daily_budget() -> Decimal:
    raw = os.environ.get(BUDGET_ENV)
    if raw is None or not raw.strip():
        raise SpendError(
            f"{BUDGET_ENV} is not set. Set it in .env (decided 2026-11-09: 0.10); "
            "outreach makes no model call without a cap.")
    try:
        value = Decimal(raw.strip())
    except InvalidOperation:
        raise SpendError(f"{BUDGET_ENV} must be a number of US dollars, got {raw!r}") from None
    if not value.is_finite() or value <= 0:
        raise SpendError(f"{BUDGET_ENV} must be more than 0, got {raw!r}")
    return value


def day_start(now: datetime | None = None) -> datetime:
    """Midnight UTC of the day `now` falls in: where the cap resets."""
    return (now or datetime.now(UTC)).astimezone(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0)


def machine() -> str:
    """Which computer made the call. Not which person."""
    try:
        return socket.gethostname() or "unknown-host"
    except OSError:
        return "unknown-host"


INSERT = """
INSERT INTO kp_outreach_spend
  (step, model, thread_id, input_tokens, output_tokens, usd, machine)
VALUES (%s, %s, %s, %s, %s, %s, %s)
RETURNING id
"""


def record(conn: Any, *, step: str, model: str, thread_id: int | None,
           input_tokens: int | None, output_tokens: int | None,
           usd: Decimal | float | None) -> int:
    """Write one call, in its own transaction, and return its id.

    Call it AFTER the provider answers and BEFORE anything else can fail, so
    money spent is recorded even when the draft that follows is thrown away.
    `usd` None means the provider reported no cost; it is stored as NULL.
    """
    if step not in STEPS:
        raise ValueError(f"step must be one of {', '.join(STEPS)}, got {step!r}")
    if not model or not model.strip():
        raise ValueError("model is required")
    amount = None if usd is None else Decimal(str(usd))
    with conn.transaction():
        row = conn.execute(INSERT, (step, model.strip(), thread_id, input_tokens,
                                    output_tokens, amount, machine())).fetchone()
    return row[0]


@dataclass(frozen=True)
class Today:
    starts_at: datetime
    calls: int
    spent_usd: Decimal          # priced calls only
    unpriced_calls: int         # >0 makes spent_usd a floor

    @property
    def is_floor(self) -> bool:
        return self.unpriced_calls > 0


def today(conn: Any, now: datetime | None = None) -> Today:
    start = day_start(now)
    calls, spent, unpriced = conn.execute(
        "SELECT count(*), coalesce(sum(usd), 0), count(*) FILTER (WHERE usd IS NULL) "
        "FROM kp_outreach_spend WHERE at >= %s AND at < %s",
        (start, start + timedelta(days=1)),
    ).fetchone()
    return Today(starts_at=start, calls=int(calls), spent_usd=Decimal(spent),
                 unpriced_calls=int(unpriced))


def check(conn: Any, budget: Decimal, now: datetime | None = None) -> Today:
    """Raise BudgetReached unless another call may be made today."""
    t = today(conn, now)
    reset = (t.starts_at + timedelta(days=1)).strftime("%Y-%m-%d 00:00 UTC")
    if t.is_floor:
        raise BudgetReached(
            f"daily outreach budget cannot be checked: {t.unpriced_calls} call(s) today "
            f"had no reported cost, so ${t.spent_usd:.4f} is only a floor. No more calls "
            f"until {reset}.")
    if t.spent_usd >= budget:
        raise BudgetReached(
            f"daily outreach budget reached: ${t.spent_usd:.4f} of ${budget:.2f} in "
            f"{t.calls} call(s). Unprocessed threads wait until {reset}.")
    return t


@dataclass(frozen=True)
class DayRow:
    day: str                    # YYYY-MM-DD, UTC
    step: str
    model: str
    calls: int
    input_tokens: int           # over calls that reported tokens
    output_tokens: int
    unmetered_calls: int        # reported no tokens
    usd: Decimal                # over calls that reported a cost
    unpriced_calls: int         # >0 makes usd a floor
    machines: tuple[str, ...]


def by_day(conn: Any, days: int = 14, now: datetime | None = None) -> list[DayRow]:
    """Spend per UTC day, step and model, newest first. A day with no calls has
    no row: "nothing recorded", never a $0.00 row."""
    since = day_start(now) - timedelta(days=days - 1)
    rows = conn.execute(
        """
        SELECT to_char(at AT TIME ZONE 'UTC', 'YYYY-MM-DD') AS day, step, model,
               count(*), coalesce(sum(input_tokens), 0), coalesce(sum(output_tokens), 0),
               count(*) FILTER (WHERE input_tokens IS NULL OR output_tokens IS NULL),
               coalesce(sum(usd), 0), count(*) FILTER (WHERE usd IS NULL),
               array_agg(DISTINCT machine ORDER BY machine)
        FROM kp_outreach_spend
        WHERE at >= %s
        GROUP BY 1, 2, 3
        ORDER BY 1 DESC, 2, 8 DESC
        """,
        (since,),
    ).fetchall()
    return [DayRow(day, step, model, int(n), int(i), int(o), int(um), Decimal(u),
                   int(up), tuple(m)) for day, step, model, n, i, o, um, u, up, m in rows]
