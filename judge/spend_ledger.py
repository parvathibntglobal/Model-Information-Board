"""Every paid model call, on disk, under ONE $1/day cap shared by both stages.

Rule 2 permits exactly two stages to call a model, and both spend from the SAME
daily dollar:

    extract   judge/extract/  one call per thread, nightly batch
    ask       judge/ask/      Q1, one call per Ask-box submission

**$1/day is the total across both. Not $1 each.**

That was the requirement and the code did not do it. `judge/ask/spend.py` read
`EXTRACTION_DAILY_BUDGET_USD` into its own in-memory total and the pipeline's
`Budget` read the same variable into another. Neither could see the other, so
each stage got its own dollar and the real ceiling was $2 - plus a restart
zeroed it and `--workers N` multiplied it again. One shared durable total is
what makes $1 mean $1.

The split still matters under one cap: extraction is a predictable batch, the
ask box is bursty and user-driven, and a single total cannot say which ate the
day. So the LIMIT is one number and every USAGE figure is broken out by stage.

Three honesty properties, because absence and zero look identical here:

  * A stage that never recorded is not a stage that spent nothing -
    `stages_ever_recorded` separates a wiring failure from a quiet day.
  * The ledger starts when it starts, so any total covering a window that began
    earlier is a FLOOR. `covers_whole_window` says which case a reader has.
  * A deleted ledger reads as no spend, so `first_seen_at` is exposed and the
    page says "counting since 14:02" rather than "$0.00".

The day boundary is UTC: a local one moves with the server's timezone, and a cap
resetting at a different hour after a deploy is one nobody can reason about.

The durable home for this is Postgres. `contract/` is shared, so a table is
Engineer 1's to agree to - hence a `judge/`-owned append-only file, and the
table proposed rather than assumed. One append of a short line does not
interleave; this is not a transaction and claims not to be.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from judge.ask.cost import Pricing
from judge.extract.budget import DEFAULT_PRICING

LEDGER_PATH_ENV = "SPEND_LEDGER_PATH"
DEFAULT_LEDGER_PATH = Path("var") / "spend-ledger.jsonl"

#: A CLOSED set: a third caller here is a rule-2 violation, and it should
#: surface as a rejected row rather than a new line on a chart nobody questions.
STAGE_EXTRACT = "extract"
STAGE_ASK = "ask"
STAGES = (STAGE_EXTRACT, STAGE_ASK)

STAGE_LABELS = {
    STAGE_EXTRACT: "Extraction (E5) — one call per thread, nightly batch",
    STAGE_ASK: "Ask box (Q1) — one call per submission, user-driven",
}


def ledger_path() -> Path:
    raw = os.getenv(LEDGER_PATH_ENV)
    return Path(raw) if raw and raw.strip() else DEFAULT_LEDGER_PATH


@dataclass(frozen=True)
class Call:
    at: datetime
    stage: str
    model: str
    input_tokens: int
    output_tokens: int
    usd: float

    #: Provider reported no usage. Those calls cost money while charging zero,
    #: so a total containing them is a floor - why `Budget.unmetered_calls` exists.
    unmetered: bool

    def as_row(self) -> str:
        return json.dumps(
            {
                "at": self.at.isoformat(),
                "stage": self.stage,
                "model": self.model,
                "in": self.input_tokens,
                "out": self.output_tokens,
                "usd": round(self.usd, 8),
            },
            separators=(",", ":"),
        )


def cost_of(input_tokens: int, output_tokens: int, pricing: Pricing = DEFAULT_PRICING) -> float:
    return (input_tokens * pricing.price_in + output_tokens * pricing.price_out) / 1_000_000


def record(
    *,
    stage: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    pricing: Pricing = DEFAULT_PRICING,
    at: datetime | None = None,
    path: Path | None = None,
) -> Call:
    """Append one call. A write failure is swallowed: telemetry that kills the
    process when its disk fills is worse than a lost row."""
    if stage not in STAGES:
        raise ValueError(f"{stage!r} is not one of the two stages permitted to call a model")

    call = Call(
        at=at or datetime.now(UTC),
        stage=stage,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        usd=cost_of(input_tokens, output_tokens, pricing),
        unmetered=input_tokens == 0 and output_tokens == 0,
    )
    target = path or ledger_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(call.as_row() + "\n")
    except OSError:
        pass
    return call


def read_all(path: Path | None = None) -> list[Call]:
    """Every recorded call. A malformed line is skipped rather than fatal."""
    target = path or ledger_path()
    if not target.exists():
        return []
    calls: list[Call] = []
    with open(target, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                at = datetime.fromisoformat(row["at"])
                if at.tzinfo is None:
                    at = at.replace(tzinfo=UTC)
                inp, out = int(row["in"]), int(row["out"])
                calls.append(
                    Call(
                        at=at,
                        stage=str(row["stage"]),
                        model=str(row["model"]),
                        input_tokens=inp,
                        output_tokens=out,
                        usd=float(row["usd"]),
                        unmetered=inp == 0 and out == 0,
                    )
                )
            except (ValueError, KeyError, TypeError):
                continue
    return calls


def day_start(moment: datetime | None = None) -> datetime:
    """Midnight UTC of the day `moment` falls in - the cap's reset boundary."""
    return (moment or datetime.now(UTC)).astimezone(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def spent_today(path: Path | None = None, now: datetime | None = None) -> float:
    """TODAY'S TOTAL ACROSS BOTH STAGES - the figure the shared cap is checked
    against. Summing every stage here is what makes one dollar mean one dollar,
    and reading it from disk is what makes it survive a restart and be visible
    to every worker."""
    since = day_start(now)
    return sum(c.usd for c in read_all(path) if c.at >= since)


# ── the shape the admin page needs ────────────────────────────────────────


@dataclass(frozen=True)
class Bucket:
    label: str
    starts_at: datetime
    usd: float
    calls: int
    by_stage: dict[str, float]


@dataclass(frozen=True)
class Report:
    #: ONE limit for both stages together. `None` is "nobody configured a cap",
    #: never "unlimited is fine" (rule 6).
    daily_cap_usd: float | None
    spent_today_usd: float
    calls_today: int
    unmetered_today: int

    hourly: list[Bucket]
    daily: list[Bucket]

    #: The limit is one number; these say where it went.
    by_stage_usd: dict[str, float]
    by_stage_calls: dict[str, int]
    by_model_usd: dict[str, float]

    #: Stages that have EVER written a row. Missing here is a wiring fact, not
    #: a usage one.
    stages_ever_recorded: tuple[str, ...]

    pricing_in_per_million: float
    pricing_out_per_million: float
    estimated_call_usd: float

    first_seen_at: datetime | None
    total_rows: int
    day_starts_at: datetime

    @property
    def remaining_usd(self) -> float | None:
        if self.daily_cap_usd is None:
            return None
        return max(0.0, self.daily_cap_usd - self.spent_today_usd)

    @property
    def fraction_used(self) -> float | None:
        if not self.daily_cap_usd:
            return None
        return min(1.0, self.spent_today_usd / self.daily_cap_usd)

    @property
    def calls_remaining(self) -> int | None:
        """More calls the shared cap affords, at the measured per-call cost.
        Across both stages, because the cap is."""
        remaining = self.remaining_usd
        if remaining is None or self.estimated_call_usd <= 0:
            return None
        return int(remaining / self.estimated_call_usd)

    @property
    def unwired_stages(self) -> tuple[str, ...]:
        """No row in the ledger's whole history. Rendered as "not recording",
        never as zero: a flat line for a stage nothing writes to is the most
        confident kind of wrong this repo produces."""
        return tuple(s for s in STAGES if s not in self.stages_ever_recorded)

    @property
    def covers_whole_window(self) -> bool:
        """False when the ledger began after today did. A genuine $0.00 and a
        ledger that was not watching produce the same number."""
        return self.first_seen_at is not None and self.first_seen_at <= self.day_starts_at

    @property
    def usd_per_hour_recent(self) -> float | None:
        """`None` rather than `0.0` with no window: a rate needs one."""
        return self.hourly[-1].usd if self.hourly else None

    @property
    def hours_to_cap(self) -> float | None:
        rate = self.usd_per_hour_recent
        remaining = self.remaining_usd
        if not rate or remaining is None:
            return None
        return remaining / rate


def _buckets(
    calls: Iterable[Call], start: datetime, span: timedelta, count: int, fmt: str
) -> list[Bucket]:
    edges = [start + span * i for i in range(count)]
    totals = [0.0] * count
    counts = [0] * count
    stages: list[dict[str, float]] = [{} for _ in range(count)]
    for call in calls:
        offset = int((call.at - start) / span)
        if 0 <= offset < count:
            totals[offset] += call.usd
            counts[offset] += 1
            stages[offset][call.stage] = stages[offset].get(call.stage, 0.0) + call.usd
    return [
        Bucket(edges[i].strftime(fmt), edges[i], totals[i], counts[i], stages[i])
        for i in range(count)
    ]


def report(
    *,
    daily_cap_usd: float | None,
    estimated_call_usd: float,
    pricing: Pricing = DEFAULT_PRICING,
    path: Path | None = None,
    now: datetime | None = None,
    hours: int = 24,
    days: int = 14,
) -> Report:
    """Aggregate the ledger into what one page needs, in a single read."""
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    calls = read_all(path)
    today = [c for c in calls if c.at >= day_start(moment)]

    by_stage_usd: dict[str, float] = {}
    by_stage_calls: dict[str, int] = {}
    by_model_usd: dict[str, float] = {}
    for call in today:
        by_stage_usd[call.stage] = by_stage_usd.get(call.stage, 0.0) + call.usd
        by_stage_calls[call.stage] = by_stage_calls.get(call.stage, 0) + 1
        by_model_usd[call.model] = by_model_usd.get(call.model, 0.0) + call.usd

    hour_start = moment.replace(minute=0, second=0, microsecond=0) - timedelta(hours=hours - 1)
    return Report(
        daily_cap_usd=daily_cap_usd,
        spent_today_usd=sum(c.usd for c in today),
        calls_today=len(today),
        unmetered_today=sum(1 for c in today if c.unmetered),
        hourly=_buckets(calls, hour_start, timedelta(hours=1), hours, "%H:00"),
        daily=_buckets(
            calls, day_start(moment) - timedelta(days=days - 1), timedelta(days=1), days, "%m-%d"
        ),
        by_stage_usd=by_stage_usd,
        by_stage_calls=by_stage_calls,
        by_model_usd=by_model_usd,
        stages_ever_recorded=tuple(sorted({c.stage for c in calls})),
        pricing_in_per_million=pricing.price_in,
        pricing_out_per_million=pricing.price_out,
        estimated_call_usd=estimated_call_usd,
        first_seen_at=min((c.at for c in calls), default=None),
        total_rows=len(calls),
        day_starts_at=day_start(moment),
    )
