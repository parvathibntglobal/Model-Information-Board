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

THE TABLE IS NOW AGREED (2026-09-11, `spend_ledger`), and the file stays.
Every call is written to the FILE FIRST and to the database best-effort, so:

  * the total on the page is the TEAM's, across every machine, which is what
    makes one shared dollar mean one dollar when more than one person runs a
    fetch; and
  * a machine that cannot reach the database still records its own spend, and
    says that it did - `Report.db_readable` is False and the total is declared
    a floor rather than quietly shrinking to one laptop's view.

THE LEDGER HAD NO PRIMARY KEY, which is why the merge needed one before any
data moved. Rows were `{at, stage, model, in, out, usd, unpriced}` and two
machines can legitimately emit byte-identical ones. Deduplicating on content
alone would have silently DROPPED a real second call; deduplicating on nothing
would have double-counted it on every backfill. `Call.id` hashes the machine
and run in with the content, so identical calls from different machines stay
two rows, the same call recorded twice stays one, and a re-run of the backfill
changes nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
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


#: Overridable so a test does not depend on the host it runs on, and so a
#: container with a random hostname can be given a stable name.
MACHINE_ENV = "MODELBOARD_MACHINE"


def machine() -> str:
    """Which host recorded a call. NOT which person.

    This app has exactly one account - everyone signs in as the same
    AUTH_EMAIL - so who clicked is genuinely unknown. Naming this `user` would
    be rule 6 applied to ourselves: an absent value becoming a definite one.
    """
    named = os.getenv(MACHINE_ENV)
    if named and named.strip():
        return named.strip()
    try:
        return socket.gethostname() or "unknown-host"
    except OSError:
        return "unknown-host"


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

    #: NO PUBLISHED RATE FOR THIS MODEL, so `usd` is 0.0 and the tokens are the
    #: only real figure on the row. Distinct from `unmetered`, which is the
    #: provider reporting no tokens: here the tokens are known and the PRICE is
    #: not. Both make a dollar total a floor, and for different reasons a reader
    #: would want to tell apart.
    unpriced: bool = False

    #: WHICH HOST, not which person - see `machine()`. Defaulted so rows read
    #: back from a file written before 2026-09-11 still construct; they are
    #: attributed to the machine reading them, which is the only honest guess
    #: available and is true for every row that exists today.
    machine: str = ""

    #: The fetch run that spent it, where there is one. The ask box has none.
    run_id: str | None = None

    @property
    def id(self) -> str:
        """A content id, so a merge is an append and a backfill is idempotent.

        MACHINE AND RUN ARE IN THE HASH ON PURPOSE. Two machines can make the
        same call in the same microsecond with the same tokens; that is two
        real calls costing two real amounts, and hashing content alone would
        record one of them and lose the other's money.
        """
        parts = "|".join((
            self.machine or "unknown-host",
            self.run_id or "-",
            self.at.astimezone(UTC).isoformat(),
            self.stage,
            self.model,
            str(self.input_tokens),
            str(self.output_tokens),
        ))
        return "spd_" + hashlib.sha256(parts.encode("utf-8")).hexdigest()[:24]

    def as_row(self) -> str:
        return json.dumps(
            {
                "at": self.at.isoformat(),
                "stage": self.stage,
                "model": self.model,
                "in": self.input_tokens,
                "out": self.output_tokens,
                "usd": round(self.usd, 8),
                "unpriced": self.unpriced,
                "machine": self.machine,
                "run_id": self.run_id,
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
    pricing: Pricing | None = None,
    at: datetime | None = None,
    path: Path | None = None,
    run_id: str | None = None,
    to_database: bool = True,
) -> Call:
    """Append one call. A write failure is swallowed: telemetry that kills the
    process when its disk fills is worse than a lost row.

    `pricing` DEFAULTS TO THE MODEL'S OWN PUBLISHED RATE rather than to one
    constant. It used to default to Gemini 2.5 Flash's, which was correct while
    Gemini was the only model either stage called and became wrong the moment
    the extractor moved to DeepSeek. A model with no rate in `MODEL_PRICING`
    records its tokens with `usd: 0.0` and `unpriced: True` - the tokens are
    measured, the product is not available, and pretending otherwise puts an
    unauditable total on the page (rule 3).
    """
    from judge.extract.budget import pricing_for

    if stage not in STAGES:
        raise ValueError(f"{stage!r} is not one of the two stages permitted to call a model")

    rate = pricing if pricing is not None else pricing_for(model)
    call = Call(
        at=at or datetime.now(UTC),
        stage=stage,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        usd=cost_of(input_tokens, output_tokens, rate) if rate is not None else 0.0,
        unmetered=input_tokens == 0 and output_tokens == 0,
        unpriced=rate is None,
        machine=machine(),
        run_id=run_id,
    )
    # THE FILE FIRST, ALWAYS. It is the write that cannot fail for a reason
    # outside this machine, and it is what a run still has when the database
    # is unreachable.
    target = path or ledger_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(call.as_row() + "\n")
    except OSError:
        pass
    if to_database:
        append_to_database([call])
    return call


def append_to_database(calls: Iterable[Call], *, dsn: str | None = None) -> int:
    """Mirror calls into `spend_ledger`. Best-effort; never raises.

    SWALLOWING IS RIGHT HERE AND WRONG ALMOST EVERYWHERE ELSE. The same
    reasoning as the file write: this is telemetry recorded AFTER the money was
    already spent, so raising would turn an unreachable database into a failed
    extraction and lose the work as well as the record. The row is not lost
    either - it is in the file, and `backfill` puts it in the table later.

    ON CONFLICT DO NOTHING, on a content id, so re-sending is free.
    """
    rows = [
        (
            c.id, c.at, c.stage, c.model, c.input_tokens, c.output_tokens,
            c.usd, c.unpriced, c.machine or machine(), c.run_id,
        )
        for c in calls
    ]
    if not rows:
        return 0
    conn = _telemetry_connection(dsn)
    if conn is None:
        return 0
    try:
        with conn, conn.cursor() as cur:
            cur.executemany(
                "insert into spend_ledger "
                "(id, at, stage, model, input_tokens, output_tokens, usd, "
                " unpriced, machine, run_id) "
                "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "on conflict (id) do nothing",
                rows,
            )
        return len(rows)
    except Exception:
        return 0
    finally:
        conn.close()


#: TELEMETRY GETS A SHORTER FUSE THAN THE BOARD. `judge.store.claims` waits 10
#: seconds because a board read failing is a page the user cannot have. These
#: reads are a mirror of a file we already hold, so waiting is pure cost.
TELEMETRY_CONNECT_TIMEOUT = 2.0

#: ...AND STOPS ASKING FOR A WHILE AFTER A FAILURE. `spent_today()` is the cap
#: check that runs BEFORE EVERY MODEL CALL. Without this, a database that is
#: down adds a connect timeout to every one of them - measured at 2.66s per
#: attempt, which is how a 172-second test suite became a ten-minute one and
#: how an outage would have quietly become a per-call latency tax in
#: production. A database that is down stays down for longer than 30 seconds,
#: so re-probing more often than that buys nothing.
TELEMETRY_RETRY_AFTER_SECONDS = 30.0

_unreachable_until = 0.0


def _telemetry_connection(dsn: str | None):
    """A short-timeout connection, or None while the backoff is in force."""
    global _unreachable_until
    import time

    import psycopg

    # ⚠ NEVER MIRROR TO A REAL DATABASE FROM A TEST. This is why the guard is
    #   in the WRITER and not only in conftest.
    #
    #   Every other table in this repo is protected by the suite's disposable-
    #   database fixtures (`assert_safe_target`, `assert_disposable`, and the
    #   DROP SCHEMA each test runs). These writers bypassed all of it by reading
    #   DATABASE_URL straight from the environment — and a developer .env points
    #   that at the SHARED database. The first full run after they were wired
    #   put 110 test spend rows worth $0.30 into the team's ledger, 11 lines
    #   into its fetch log, and overwrote a genuine Reddit quota reading with a
    #   fixture's.
    #
    #   The conftest fixture that now backs telemetry off is a second layer, not
    #   this one: it can be cleared by any test that wants a real connection,
    #   and then the next person to write one repeats the whole thing. A test
    #   that genuinely means to exercise the mirror sets
    #   MODELBOARD_ALLOW_TEST_TELEMETRY and points DATABASE_URL at a disposable
    #   database itself.
    if os.getenv("PYTEST_CURRENT_TEST") and not os.getenv(
        "MODELBOARD_ALLOW_TEST_TELEMETRY"
    ):
        return None
    if time.monotonic() < _unreachable_until:
        return None
    url = dsn or os.getenv("DATABASE_URL")
    if not url:
        return None
    try:
        return psycopg.connect(url, connect_timeout=TELEMETRY_CONNECT_TIMEOUT)
    except Exception:
        _unreachable_until = time.monotonic() + TELEMETRY_RETRY_AFTER_SECONDS
        return None


def reset_telemetry_backoff() -> None:
    """Forget a past failure. For tests, and for a caller that has reason to
    believe the database is back — a backoff nobody can clear is a cache."""
    global _unreachable_until
    _unreachable_until = 0.0


def read_database(dsn: str | None = None) -> list[Call] | None:
    """Every call every machine recorded, or None when the table cannot be read.

    NONE IS NOT AN EMPTY LEDGER. A database that is unreachable and a team that
    spent nothing produce the same list, and only one of them means the total on
    the page is complete. Callers must be able to tell, so the failure is a
    distinct value rather than `[]` (rule 6).
    """
    conn = _telemetry_connection(dsn)
    if conn is None:
        return None
    try:
        with conn:
            rows = conn.execute(
                "select at, stage, model, input_tokens, output_tokens, usd, "
                "       unpriced, machine, run_id from spend_ledger"
            ).fetchall()
    except Exception:
        return None
    finally:
        conn.close()
    calls: list[Call] = []
    for at, stage, model, inp, out, usd, unpriced, mach, run in rows:
        moment = at if at.tzinfo else at.replace(tzinfo=UTC)
        calls.append(
            Call(
                at=moment, stage=str(stage), model=str(model),
                input_tokens=int(inp), output_tokens=int(out), usd=float(usd),
                unmetered=int(inp) == 0 and int(out) == 0,
                unpriced=bool(unpriced), machine=str(mach), run_id=run,
            )
        )
    return calls


def read_everywhere(
    path: Path | None = None, *, dsn: str | None = None
) -> tuple[list[Call], bool]:
    """The team's calls, and whether the database was readable.

    THE UNION, KEYED BY `Call.id`. The file is not a subset of the table: a
    machine that recorded while the database was down has rows the table has
    not got yet. Preferring one source would either lose those or lose every
    other machine's, so both are read and merged on the content id - which is
    exactly what that id was added for.
    """
    local = read_all(path)
    shared = read_database(dsn)
    if shared is None:
        return local, False
    merged = {c.id: c for c in shared}
    for call in local:
        merged.setdefault(call.id, call)
    return list(merged.values()), True


def read_all(path: Path | None = None) -> list[Call]:
    """Every call THIS MACHINE recorded. A malformed line is skipped, not fatal."""
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
                        # Absent on rows written before per-model pricing. False
                        # is right for those: they were all priced, at the one
                        # rate that then existed.
                        unpriced=bool(row.get("unpriced", False)),
                        unmetered=inp == 0 and out == 0,
                        # Absent on rows written before the table existed.
                        # Attributed to the machine READING them, which is
                        # where the file is, and is true for every such row.
                        machine=str(row.get("machine") or machine()),
                        run_id=row.get("run_id"),
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
    """TODAY'S TOTAL ACROSS BOTH STAGES AND EVERY MACHINE - the figure the
    shared cap is checked against.

    Summing every stage is what makes one dollar mean one dollar; reading it
    from disk is what makes it survive a restart and be visible to every
    worker; and reading it from the TABLE is what makes it survive being run
    from somebody else's laptop. The module's own argument always implied the
    last one - "$1/day is the total across both", not per process and not per
    person - it just could not reach past one filesystem until there was a
    table to reach into.

    A UNREACHABLE DATABASE MAKES THIS A FLOOR, and the cap then guards only
    this machine's share. That is the safe direction to fail: the number can be
    too small, never too large, so the cap can stop early but never overspend
    on a figure it believed was complete. `report()` says which case a reader
    is in; this returns the number the cap must compare.
    """
    since = day_start(now)
    calls, _ = read_everywhere(path)
    return sum(c.usd for c in calls if c.at >= since)


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

    #: WHETHER THE SHARED TABLE WAS READABLE. False means every figure here
    #: covers ONE MACHINE, and the page must say so rather than present a
    #: smaller number in the same type as a complete one.
    db_readable: bool = True

    #: Which hosts contributed. The denominator rule 7 asks for, applied to a
    #: total that is now a sum over machines: "$0.31" means something different
    #: from one machine than from four.
    machines: tuple[str, ...] = ()

    @property
    def total_is_a_floor(self) -> bool:
        """True when something is known to be missing from the total.

        Three independent reasons, deliberately collapsed into one flag the
        page can act on and three fields it can explain from: the shared table
        was unreadable, the ledger started after the window did, or a call was
        recorded with no published rate for its model.
        """
        return (
            not self.db_readable
            or not self.covers_whole_window
            or any(m for m in self.by_model_usd) and self.unpriced_today > 0
        )

    #: Calls today whose model has no published rate. Their TOKENS are real and
    #: their dollars are 0.0, so a total containing one understates the spend.
    unpriced_today: int = 0

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
    calls, db_readable = read_everywhere(path)
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
        db_readable=db_readable,
        machines=tuple(sorted({c.machine for c in calls if c.machine})),
        unpriced_today=sum(1 for c in today if c.unpriced),
    )
