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
import logging
import os
import socket
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from judge.ask.cost import Pricing
from judge.extract.budget import DEFAULT_PRICING

log = logging.getLogger(__name__)

LEDGER_PATH_ENV = "SPEND_LEDGER_PATH"
DEFAULT_LEDGER_PATH = Path("var") / "spend-ledger.jsonl"

#: A CLOSED set: a caller not named here is a rule-2 violation, and it should
#: surface as a rejected row rather than a new line on a chart nobody questions.
STAGE_EXTRACT = "extract"
STAGE_ASK = "ask"
#: THE STAGES THE DAILY CAP COVERS. Everything about "today" - the cap, the
#: hourly and daily series, today's per-stage and per-model figures - reads
#: these and only these.
STAGES = (STAGE_EXTRACT, STAGE_ASK)

#: THE BLOG GENERATOR, rule 2's third caller (CLAUDE.md, agreed 2026-10-06).
#: RECORDED HERE, OUTSIDE THE CAP: a blog run must never spend the extraction
#: budget, and its spend must still be visible beside it - all-time and by
#: month (`monthly`). Its usd is what OpenRouter REPORTED for the call, not a
#: rate multiplied out here; a call with no reported cost is `unpriced`.
STAGE_BLOG = "blog"
#: THE QUIZ QUESTION DRAFTER (2026-10-15, judge/quiz_bank.py): the blog's
#: pattern - a model drafts, a person approves - and recorded the same way,
#: outside the cap, with the cost OpenRouter reports for each call.
STAGE_QUIZ = "quiz"
#: THE EVIDENCE FEED (2026-10-21, PROPOSED, judge/feed/): a paraphrase per
#: report and a person-approved summary per model. Outside the cap, at the cost
#: OpenRouter reports, like the two above.
STAGE_FEED = "feed"
RECORDED_STAGES = (*STAGES, STAGE_BLOG, STAGE_QUIZ, STAGE_FEED)

STAGE_LABELS = {
    STAGE_EXTRACT: "Extraction (E5) — one call per thread, nightly batch",
    STAGE_ASK: "Ask box (Q1) — one call per submission, user-driven",
    STAGE_BLOG: "Blog drafts (generate_sample_blogs.py) — outside the daily cap",
    STAGE_QUIZ: "Quiz question drafts (judge/quiz_bank.py) — outside the daily cap",
    STAGE_FEED: "Evidence feed paraphrases and summaries (judge/feed/) — outside the daily cap",
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

    #: The part of `input_tokens` billed at the cache-read rate. NONE MEANS NOT
    #: RECORDED, not "no cache hit": file rows written before 2026-09-24 and
    #: every row read back from the `spend_ledger` TABLE, which has no column
    #: for it. `usd` already carries the discount on either path.
    #:
    #: DECLARED WRITE-ONLY (rule 9). Intended reader: the usage panel, showing
    #: the share of input served from cache. Nothing renders it yet, and the
    #: table cannot mirror it until a migration adds the column - which is
    #: `contract/`-adjacent schema work, not done in this change.
    cached_input_tokens: int | None = None

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
                "cached": self.cached_input_tokens,
                "unpriced": self.unpriced,
                "machine": self.machine,
                "run_id": self.run_id,
            },
            separators=(",", ":"),
        )


def cost_of(
    input_tokens: int,
    output_tokens: int,
    pricing: Pricing = DEFAULT_PRICING,
    cached_input_tokens: int = 0,
) -> float:
    from judge.extract.budget import cost_of_tokens

    return cost_of_tokens(pricing, input_tokens, output_tokens, cached_input_tokens)


def record(
    *,
    stage: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    pricing: Pricing | None = None,
    at: datetime | None = None,
    path: Path | None = None,
    run_id: str | None = None,
    to_database: bool = True,
    reported_usd: float | None = None,
    reported: bool = False,
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

    `reported=True` takes the PROVIDER'S figure, `reported_usd`, instead of a
    rate held here - the blog stage, which OpenRouter bills per call and whose
    model has no entry in `MODEL_PRICING`. A reported call with no figure is
    `unpriced` with usd 0.0: never priced on a guess, never read as free.
    """
    from judge.extract.budget import pricing_for

    if stage not in RECORDED_STAGES:
        raise ValueError(f"{stage!r} is not one of the stages permitted to call a model")

    if reported:
        rate, usd = None, float(reported_usd) if reported_usd is not None else 0.0
        unpriced = reported_usd is None
    else:
        rate = pricing if pricing is not None else pricing_for(model)
        usd = (cost_of(input_tokens, output_tokens, rate, cached_input_tokens)
               if rate is not None else 0.0)
        unpriced = rate is None
    call = Call(
        at=at or datetime.now(UTC),
        stage=stage,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        usd=usd,
        unmetered=input_tokens == 0 and output_tokens == 0,
        unpriced=unpriced,
        machine=machine(),
        run_id=run_id,
        cached_input_tokens=cached_input_tokens,
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


#: WHY A MIRROR DID NOT HAPPEN - five answers that used to be one `return 0`
#: (#393). The first three are "nothing was asked of the table"; the last two
#: are "a table was configured and these rows are not in it", and only those
#: are counted and logged. A missing DSN and a broken write returned the same
#: value, which is rule 12: the fallback succeeded on the wrong input.
MIRROR_WRITTEN = "written"
MIRROR_NOTHING_TO_SEND = "nothing_to_send"
MIRROR_NOT_CONFIGURED = "not_configured"   # no DSN: Report.db_readable says so
MIRROR_TEST_GUARD = "test_guard"           # pytest, not opted in
MIRROR_BACKING_OFF = "backing_off"         # a configured DSN failed < 30s ago
MIRROR_FAILED = "failed"                   # connect or insert raised just now
MIRROR_UNMIRRORED = (MIRROR_BACKING_OFF, MIRROR_FAILED)


@dataclass(frozen=True)
class Mirrored:
    """What `append_to_database` did. `sent` rows were offered; `written` of
    them were inserted or already present (ON CONFLICT DO NOTHING)."""

    status: str
    sent: int
    written: int = 0
    reason: str | None = None

    @property
    def unmirrored(self) -> int:
        """Rows a configured table should hold and does not. Zero for the
        not-asked statuses - those are a configuration, not a loss."""
        return self.sent - self.written if self.status in MIRROR_UNMIRRORED else 0


#: THIS PROCESS'S ROWS THAT A CONFIGURED TABLE DID NOT GET (#393). Read by the
#: log line in `append_to_database` (the running total) and by
#: `scripts/fetch_model.py`'s E5 stage line, which says so when a run moved it.
#: Per process, so NOT the machine's figure - `Report.unmirrored_rows`
#: reconciles this machine's whole file against the table for that.
_unmirrored_rows = 0

#: THE CALLS THEMSELVES, not only their count (2026-10-26), so the end of a run
#: can send them (`flush_unmirrored`). Measured that day: a feed run from a
#: laptop made 92 calls and the shared table got 35 - Railway's proxy often
#: takes longer than TELEMETRY_CONNECT_TIMEOUT to answer, and each miss starts
#: a 30-second pause in which every call is skipped.
_unmirrored_calls: list = []


def unmirrored_count() -> int:
    return _unmirrored_rows


#: How long the END-OF-RUN flush waits for the database. Not the per-call 2s:
#: the per-call wait runs before every model call and must stay short; this
#: runs once, after the money is spent, when waiting is cheap and a miss is not.
FLUSH_CONNECT_TIMEOUT = 15


def flush_unmirrored(dsn: str | None = None) -> Mirrored:
    """Send this process's unmirrored calls, once, with a patient connection.

    For the END of a run: `build_evidence_feed.py` and `fetch_model.py` call it
    so a slow connection during the run does not leave the shared cap short.
    It ignores the backoff - one deliberate attempt is what a backoff exists to
    make room for - and on success the calls leave the pending list and the
    count. Never raises. What it could not send stays pending and counted, and
    the caller says so; the rows are in the file either way.
    """
    global _unmirrored_rows
    pending = list(_unmirrored_calls)
    if not pending:
        return Mirrored(MIRROR_NOTHING_TO_SEND, 0)
    reset_telemetry_backoff()
    conn, status, reason = _telemetry_connect(dsn, timeout=FLUSH_CONNECT_TIMEOUT)
    if conn is None:
        return Mirrored(status, len(pending), 0, reason)
    try:
        with conn, conn.cursor() as cur:
            cur.executemany(
                "insert into spend_ledger "
                "(id, at, stage, model, input_tokens, output_tokens, usd, "
                " unpriced, machine, run_id) "
                "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "on conflict (id) do nothing",
                [(c.id, c.at, c.stage, c.model, c.input_tokens, c.output_tokens,
                  c.usd, c.unpriced, c.machine or machine(), c.run_id) for c in pending],
            )
    except Exception as exc:  # noqa: BLE001 - see append_to_database
        return Mirrored(MIRROR_FAILED, len(pending), 0, _describe(exc))
    finally:
        conn.close()
    del _unmirrored_calls[: len(pending)]
    _unmirrored_rows = max(0, _unmirrored_rows - len(pending))
    return Mirrored(MIRROR_WRITTEN, len(pending), len(pending))


def append_to_database(calls: Iterable[Call], *, dsn: str | None = None) -> Mirrored:
    """Mirror calls into `spend_ledger`. Never raises; no longer silent.

    SWALLOWING IS RIGHT HERE AND WRONG ALMOST EVERYWHERE ELSE. The same
    reasoning as the file write: this is telemetry recorded AFTER the money was
    already spent, so raising would turn an unreachable database into a failed
    extraction and lose the work as well as the record - and `record()` runs in
    `OpenRouterClient.complete()`'s `finally`, where a raise would also replace
    the provider's own exception. The row is not lost either - it is in the
    file, and `python scripts/backfill_telemetry.py --apply` puts it in the
    table.

    ⚠ BUT NOT RAISING USED TO MEAN NOT SAYING (#393). Three `return 0`s, and 61
      of one run's 203 file rows (one machine, e5.5 run 1, 2026-09-21) never reached
      the table with nothing in the log. Every other machine's cap reads the
      table, so a silent miss gives them headroom they do not have. A configured
      table that did not get its rows is now logged with the reason and counted
      (`unmirrored_count`); the result says which of the `MIRROR_*` cases this
      was instead of a bare 0.

    ON CONFLICT DO NOTHING, on a content id, so re-sending is free.
    """
    global _unmirrored_rows
    try:
        calls = list(calls)
        rows = [
            (
                c.id, c.at, c.stage, c.model, c.input_tokens, c.output_tokens,
                c.usd, c.unpriced, c.machine or machine(), c.run_id,
            )
            for c in calls
        ]
        if not rows:
            return Mirrored(MIRROR_NOTHING_TO_SEND, 0)
        conn, status, reason = _telemetry_connect(dsn)
        if conn is None:
            result = Mirrored(status, len(rows), 0, reason)
        else:
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
                return Mirrored(MIRROR_WRITTEN, len(rows), len(rows))
            except Exception as exc:  # noqa: BLE001 - see the docstring
                result = Mirrored(MIRROR_FAILED, len(rows), 0, _describe(exc))
            finally:
                conn.close()
        if result.unmirrored:
            _unmirrored_rows += result.unmirrored
            _unmirrored_calls.extend(calls)
            (log.error if result.status == MIRROR_FAILED else log.warning)(
                "spend_ledger: %d row(s) NOT mirrored to the shared table "
                "(%s: %s); %d so far in this process. They are in %s, and "
                "`python scripts/backfill_telemetry.py --apply` sends them - "
                "until then no other machine's daily cap can see this spend.",
                result.unmirrored, result.status, result.reason,
                _unmirrored_rows, ledger_path(),
            )
        return result
    except Exception as exc:  # noqa: BLE001 - the mirror must never raise
        return Mirrored(MIRROR_FAILED, 0, 0, _describe(exc))


def _describe(exc: BaseException) -> str:
    """The exception's type and text, never the DSN: this goes to a log."""
    return f"{type(exc).__name__}: {str(exc).strip()[:200]}"


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
#: The failure that started the current backoff, so a write skipped during it
#: can say why rather than only that it was skipped (#393).
_unreachable_reason: str | None = None


def _telemetry_connection(dsn: str | None):
    """A short-timeout connection, or None while the backoff is in force."""
    return _telemetry_connect(dsn)[0]


def _telemetry_connect(dsn: str | None, *, timeout: float = TELEMETRY_CONNECT_TIMEOUT):
    """`(connection | None, MIRROR_* status, reason)` - the WHY that
    `_telemetry_connection` drops and `append_to_database` must not (#393)."""
    global _unreachable_until, _unreachable_reason
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
        return None, MIRROR_TEST_GUARD, None
    if time.monotonic() < _unreachable_until:
        return None, MIRROR_BACKING_OFF, (
            f"skipped while backing off after {_unreachable_reason or 'an earlier failure'}"
        )
    url = dsn or os.getenv("DATABASE_URL")
    if not url:
        return None, MIRROR_NOT_CONFIGURED, None
    try:
        conn = psycopg.connect(url, connect_timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        _unreachable_until = time.monotonic() + TELEMETRY_RETRY_AFTER_SECONDS
        _unreachable_reason = _describe(exc)
        return None, MIRROR_FAILED, _unreachable_reason
    return conn, MIRROR_WRITTEN, None


def reset_telemetry_backoff() -> None:
    """Forget a past failure. For tests, and for a caller that has reason to
    believe the database is back — a backoff nobody can clear is a cache."""
    global _unreachable_until, _unreachable_reason
    _unreachable_until = 0.0
    _unreachable_reason = None


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
    merged, readable, _local, _unmirrored = _read_and_reconcile(path, dsn)
    return merged, readable


def _read_and_reconcile(
    path: Path | None, dsn: str | None
) -> tuple[list[Call], bool, int, int | None]:
    """`read_everywhere`, plus this machine's file row count and how many of
    those the table lacks - None when the table could not be read, because
    "unknown" is not 0 (rule 6). The reconciliation #393 asked for: file and
    table are the same rows, so when the table is short something says by how
    much."""
    local = read_all(path)
    shared = read_database(dsn)
    if shared is None:
        return local, False, len(local), None
    merged = {c.id: c for c in shared}
    unmirrored = 0
    for call in local:
        if call.id not in merged:
            unmirrored += 1
            merged[call.id] = call
    return list(merged.values()), True, len(local), unmirrored


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
                        # Absent on rows written before 2026-09-24: None, not 0.
                        cached_input_tokens=(
                            int(row["cached"]) if row.get("cached") is not None else None
                        ),
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
    # THE CAPPED STAGES ONLY: a blog run is recorded here and must not spend
    # the extraction budget (STAGE_BLOG).
    return sum(c.usd for c in calls if c.at >= since and c.stage in STAGES)


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
            or self.unpriced_today > 0
        )

    #: Calls today whose model has no published rate. Their TOKENS are real and
    #: their dollars are 0.0, so a total containing one understates the spend.
    unpriced_today: int = 0

    #: THIS MACHINE'S FILE ROWS THE SHARED TABLE DOES NOT HOLD (#393), out of
    #: `local_rows`, every stage. None when the table was unreadable - not 0.
    #: NOT a reason this report is a floor: the union above already holds them.
    #: It is what every OTHER machine's cap is missing. Read by
    #: `judge/app.py:admin_usage` (`basis.unmirrored_rows`).
    unmirrored_rows: int | None = None
    local_rows: int = 0

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
    everything, db_readable, local_rows, unmirrored = _read_and_reconcile(path, None)
    # THE CAP'S POPULATION: every figure in this report is about the daily cap,
    # so a blog call (STAGE_BLOG, outside it) is not in any of them. `monthly`
    # is where blog spend is reported.
    calls = [c for c in everything if c.stage in STAGES]
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
        machines=tuple(sorted({c.machine for c in everything if c.machine})),
        unpriced_today=sum(1 for c in today if c.unpriced),
        unmirrored_rows=unmirrored,
        local_rows=local_rows,
    )


@dataclass(frozen=True)
class MonthRow:
    month: str          # "YYYY-MM", UTC
    stage: str
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    usd: float          # a FLOOR when unpriced_calls > 0
    unpriced_calls: int
    unmetered_calls: int


def monthly(calls: Iterable[Call]) -> list[MonthRow]:
    """Spend by calendar month (UTC), stage and model - every stage, the blog
    stage included. Newest month first, then stage, then most spent.

    A ROW IS A FLOOR when it holds an unpriced or unmetered call; the counts are
    on the row so the page can say so (rule 7). A month with no calls has no
    row - that is "nothing recorded", which the page states with the ledger's
    `counting_since`, never a $0.00 row.
    """
    acc: dict[tuple[str, str, str], list] = {}
    for c in calls:
        key = (c.at.astimezone(UTC).strftime("%Y-%m"), c.stage, c.model)
        a = acc.setdefault(key, [0, 0, 0, 0.0, 0, 0])
        a[0] += 1
        a[1] += c.input_tokens
        a[2] += c.output_tokens
        a[3] += c.usd
        a[4] += 1 if c.unpriced else 0
        a[5] += 1 if c.unmetered else 0
    rows = [MonthRow(m, st, mo, *a) for (m, st, mo), a in acc.items()]
    order = {s: i for i, s in enumerate(RECORDED_STAGES)}
    rows.sort(key=lambda r: (-int(r.month.replace("-", "")), order.get(r.stage, 99), -r.usd))
    return rows
