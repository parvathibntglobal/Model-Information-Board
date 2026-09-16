"""What a metered API says it has left, recorded wherever it is seen.

THE TRACKING GAP THIS CLOSES. `var/rapidapi-quota.json` was written from ONE
place: the end of `scripts/fetch_model.py`'s Reddit arm, and later its X arm.
Every other metered call spent quota and recorded nothing —

  * the nightly Reddit sweep,
  * `scripts/unfiltered_sweep.py`,
  * any probe or one-off script,
  * and a fetch arm that ERRORED before reaching its write, which is precisely
    when the reading matters most.

So the panel's figure was not "the quota" but "the quota as of the last fetch
that finished its Reddit arm cleanly", and nothing on the page said so. The gap
was measured rather than theorised: a reading of 2026-08-31 said 998,076 of
1,000,000 remaining, and a single probe nine days later read 99,870 remaining —
which the stored file could not have shown, because nothing between those dates
had gone through the one writer.

WHERE THE WRITE BELONGS. In `_get`, next to the response that carried the
header. A quota reading is a property of a response, and the only place that
cannot forget it is the function that has one. Same reasoning as
`github.py`'s ledger: "an instrument that under-reports its own failures is
worse than no instrument".

`collect/` may write this: it is our own var/ file, not the judgement lane's
state, and nothing here imports `judge/`.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

#: The repo root — this file is `collect/usage.py`.
_ROOT = Path(__file__).resolve().parent.parent

#: Where the reading lives. `judge/app.py:_rapidapi_quota` reads exactly this.
QUOTA_PATH = _ROOT / "var" / "rapidapi-quota.json"

#: Same variable `judge/spend_ledger.py` reads, deliberately duplicated rather
#: than shared: `collect/` may not import `judge/` (enforced by
#: `tests/test_lane_boundary.py`), and four lines of hostname lookup is a
#: smaller price than a boundary that only holds when nobody needs it.
MACHINE_ENV = "MODELBOARD_MACHINE"


def machine() -> str:
    """Which host took the reading. NOT which person — there is one account.

    ⚠ AND NOT WHOSE QUOTA IT IS EITHER, WHICH IS WHAT THIS USED TO IMPLY.
      The counter belongs to a RapidAPI SUBSCRIPTION. The machine is provenance -
      who happened to observe it - and the panel above this once led with it, so
      a quota drawn down by anybody signed in to the hosted board rendered as
      though a laptop owned it. See `key_fingerprint`.
    """
    named = os.getenv(MACHINE_ENV)
    if named and named.strip():
        return named.strip()
    try:
        return socket.gethostname() or "unknown-host"
    except OSError:
        return "unknown-host"


def key_fingerprint(key: str | None) -> str | None:
    """WHICH SUBSCRIPTION a reading is of, without storing the key.

    `sha256(key)[:12]`. One-way, so this is safe in a shared table, in a log and
    on a page - and it is the only thing here that identifies the counter, which
    is what `meter` alone could not do.

    WHY IT IS NEEDED AT ALL, GIVEN `meter` IS THE PRIMARY KEY. `meter` says
    WHICH counter (reddit or x); it does not say whose. Every reading merged
    into one row is assumed to be of one subscription, and until now nothing
    could check that assumption:

        - the project is hosted, so a run can start from any browser;
        - `x.py:key_for` falls back `X_RAPIDAPI_KEY` then `RAPIDAPI_KEY`, so two
          hosts with different env can read DIFFERENT accounts on the same arm;
        - the readings merge by recency, so the fresher of two unrelated
          counters simply wins and the number moves for no visible reason.

    Measured 2026-09-16 and it is currently fine - reddit 1,000,000 and x
    100,000 on every host, decreasing monotonically, so one subscription each.
    That is a fact about today's `.env` files, not a property of the system, and
    it was unverifiable before this.

    ⚠ NEVER THE KEY. `x.py:key_for` already established the shape for this -
      it returns the VARIABLE NAME rather than the value, because "a key affords
      no such check ... it is 50 opaque characters". A fingerprint is the same
      move with an identity attached: it cannot be reversed and it can be
      compared.

    None when no key is set, which is not the same as a key that hashes to
    nothing: the caller has no credential at all, and a reading taken without
    one is not a reading of any subscription.
    """
    if not key or not str(key).strip():
        return None
    return hashlib.sha256(str(key).strip().encode("utf-8")).hexdigest()[:12]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def record_rapidapi_quota(
    *,
    remaining: int | None,
    limit: int | None,
    read_on: str,
    read_by: str = "harvest",
    run_id: str | None = None,
    api_key: str | None = None,
    reset_seconds: int | None = None,
    path: Path | None = None,
) -> bool:
    """Persist one quota HEADER reading. Returns whether anything was written.

    NEVER RAISES. It is called from inside a request path, and a harvest must
    not die because a metering file could not be written — the request has
    already been spent by then, so failing here loses the harvest AND the
    reading.

    A READING WITH NOTHING IN IT IS NOT WRITTEN. Both values absent means the
    response carried no quota header, which is not the same as a quota of zero,
    and blanking a good reading with it would be rule 6 in the one place the
    number is supposed to be trustworthy.

    `remaining` ALONE IS STILL WORTH RECORDING: a response can carry
    `-remaining` without `-limit`. Writing remaining with `limit: null` says
    "this much is left, against a denominator this reading did not state" —
    which is honest, and is what rule 7 asks for when only half a figure
    arrives. It does NOT inherit the previous limit, and the reason is now
    sharper than when this was written.

    ⚠ THE TWO ARMS DO NOT SHARE ONE KEY, AND THIS DOCSTRING SAID THEY DID.
      "the two arms share one key" was inherited from `.env.example`'s "THERE
      IS NO SECOND KEY" and is false on this project's own `.env`. Measured
      2026-09-10, four requests: the Reddit key returns 200 on `reddit34` and
      403 on `twitter241`; the X key does the reverse. Two accounts, two
      meters, two limits — Reddit 1,000,000 and X 100,000, both read off
      `x-ratelimit-requests-limit` that day.

      That also RETIRES THE PARADOX this docstring used to rest on. It read the
      998,076-of-1,000,000 and 99,870 readings as "mutually inconsistent"; they
      were never one meter — the second was `read_on="x"`, against a limit of
      100,000. The arithmetic was right and the conclusion wrong, because the
      denominator's IDENTITY was missing (rule 7). Non-inheritance is still
      correct, for the stronger reason: an inherited limit may be another
      meter's.

      `docs/measurements/quota-headers.jsonl` holds all of it.

    Args:
        remaining: `x-ratelimit-requests-remaining`, as read. None if absent.
        limit: `x-ratelimit-requests-limit`, as read. None if absent.
        read_on: which arm took the reading — `reddit` or `x`. NOT a courtesy
            label: the arms are separately metered, so this identifies WHICH
            METER the figure belongs to and a reading is not interpretable
            without it.
        read_by: what kind of caller. `harvest`, `sweep` or `probe`. A reading
            taken by a probe is as real as one taken by a fetch, and saying
            which prevents "the fetch must have run" being inferred from it.
        run_id: the run that spent it, where there is one.
        api_key: the credential the request was made with. Hashed on the way in
            by `key_fingerprint` and NEVER stored - it identifies WHICH
            subscription the counter belongs to, which `read_on` cannot. None
            where the caller has no key, which is a real state and not a
            default.
        path: override, for tests.
    """
    if remaining is None and limit is None:
        return False

    target = path or QUOTA_PATH
    record = {
        "quota_remaining": remaining,
        "quota_limit": limit,
        "at": _now(),
        "read_on": read_on,
        "read_by": read_by,
        "source_run_id": run_id,
        # WHOSE COUNTER, not whose machine. See `key_fingerprint`.
        "key_fingerprint": key_fingerprint(api_key),
        # SECONDS AS READ, NEVER A COMPUTED DATE. Both adapters have always
        # parsed `x-ratelimit-requests-reset`; until 2026-09-16 this function
        # took `remaining` and `limit` only, so the value died with the process
        # on every metered call (rule 9 - produced, carried, never consumed).
        #
        # It is the only field that can date the window. One reading gives
        # seconds remaining, which is NOT the period; two consecutive boundaries
        # are. The 2026-09-11 09:45 UTC boundary is already fixed by two
        # readings, so the next populated value closes it.
        #
        # Stored beside `at`, which is what it must be subtracted from. Keeping
        # the provider's own number rather than a date computed here is the same
        # ruling `tests/test_reddit_fetch.py` already pins on the adapter side.
        "quota_reset_seconds": reset_seconds,
    }
    # ONE RECORD PER METER, KEYED BY ARM. Until 2026-09-10 this file held ONE
    # record and every arm overwrote it, so a Reddit reading and an X reading
    # replaced one another and the panel rendered whichever landed last. That
    # was survivable while the arms were believed to share one key; they do
    # not - measured that day, Reddit's limit is 1,000,000 and X's is 100,000 -
    # so a single slot means one meter's figure is displayed under the other's
    # heading. `read_on` could say which; it could not stop it.
    #
    # ⚠ THE MERGE IS READ-MODIFY-WRITE AND IS NOT PROCESS-SAFE. Two arms
    #   writing in the same instant can lose one arm's record - the file stays
    #   valid, one arm's entry is simply the older one. Named rather than
    #   locked: the loss is self-healing on that arm's next metered call, and a
    #   lock file in a path that "never raises" would be a new failure mode in
    #   the one function that must not have any. The single-slot version lost a
    #   record on EVERY interleaving; this loses one on a collision.
    meters = read_rapidapi_meters(target)
    meters[read_on] = record
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        # Atomic: a concurrent reader never sees half a file. `NamedTemporaryFile`
        # in the same directory, because os.replace across filesystems is not.
        with tempfile.NamedTemporaryFile(
            "w", dir=str(target.parent), delete=False, encoding="utf-8", suffix=".tmp"
        ) as fh:
            json.dump({"meters": meters}, fh)
            tmp = fh.name
        os.replace(tmp, target)
        wrote = True
    except OSError:
        # Deliberately silent. See the docstring: the request is already spent,
        # and raising here would turn an unwritable file into a failed harvest.
        wrote = False

    # THE FILE FIRST, THE TABLE AFTER, both best-effort. The table is what makes
    # the figure a team figure; the file is what this machine still has when the
    # database is unreachable, which is the condition a quota reading is most
    # worth having in.
    _record_to_database(
        meter=read_on, remaining=remaining, limit=limit,
        read_at=record["at"], read_by=read_by, run_id=run_id,
        key_fp=record["key_fingerprint"],
        reset_seconds=reset_seconds,
    )
    # THE HISTORY, AFTER THE LATEST ROW AND INDEPENDENT OF IT. Same best-effort
    # contract: both are inside functions that never raise, and a metered
    # request is already paid for by the time either runs.
    #
    # Deliberately NOT conditional on the upsert having applied. The upsert
    # declines a reading older than the stored one (`read_at >`), and that
    # reading is still a real observation of the counter - dropping it here
    # would make the history agree with the latest row by throwing away exactly
    # the rows that disagree.
    _append_quota_reading(
        meter=read_on, remaining=remaining, limit=limit,
        read_at=record["at"], read_by=read_by, run_id=run_id,
        key_fp=record["key_fingerprint"], reset_seconds=reset_seconds,
    )
    return wrote


#: The same two constants and the same reasoning as
#: `judge/spend_ledger.py`'s, duplicated because the lane boundary forbids the
#: import. `record_rapidapi_quota` is called from inside `_get`, on EVERY
#: metered request, so an unreachable database without a backoff would add a
#: connect timeout to every harvest call — turning an outage into a latency tax
#: on the one path that must stay fast.
TELEMETRY_CONNECT_TIMEOUT = 2.0
TELEMETRY_RETRY_AFTER_SECONDS = 30.0

_unreachable_until = 0.0


def _telemetry_connection(url: str | None):
    """A short-timeout connection, or None while the backoff is in force."""
    global _unreachable_until
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
    dsn = url or os.getenv("DATABASE_URL")
    if not dsn:
        return None
    try:
        return psycopg.connect(dsn, connect_timeout=TELEMETRY_CONNECT_TIMEOUT)
    except Exception:
        _unreachable_until = time.monotonic() + TELEMETRY_RETRY_AFTER_SECONDS
        return None


def telemetry_connection(url: str | None = None):
    """The guarded, short-timeout connection every telemetry mirror must use.

    PUBLIC BECAUSE `scripts/fetch_model.py` NEEDS IT, and the day it reached for
    `collect.db.transaction()` instead is the day the fetch-log mirror escaped
    the test guard: a full suite run wrote 11 fixture lines into the shared
    table. That went unnoticed for one verification because the lines were
    already there from an earlier run and `on conflict do nothing` kept the row
    count flat — idempotence hid the leak. Every mirror goes through here so
    there is one place to guard rather than three to remember.
    """
    return _telemetry_connection(url)


def reset_telemetry_backoff() -> None:
    """Forget a past failure. For tests, and for a caller with reason to think
    the database is back — a backoff nobody can clear is a cache."""
    global _unreachable_until
    _unreachable_until = 0.0


def quota_reading_id(
    *, meter: str, machine_name: str, run_id: str | None, observed_at: str,
    remaining: int | None, limit: int | None, reset_seconds: int | None,
    key_fp: str | None,
) -> str:
    """A content id, so a replay is an append of nothing.

    MACHINE AND RUN ARE IN THE HASH, for `spend_ledger`'s reason: two hosts can
    read one shared counter in the same instant, and those are two real
    observations rather than a duplicate.

    `observed_at` RATHER THAN `read_at`, which is the deviation from
    `spend_ledger` and the whole reason this function exists. `_now()` is second
    resolution, so hashing `read_at` would give two calls in the same second
    carrying the same figures one id - and `on conflict do nothing` would drop
    the second. An unmoved counter between two calls is the consumption signal
    this table is for, so that is the one row that must not be lost.

    None is hashed as `-` rather than skipped: an absent limit and a limit of
    zero must not reach the same id (rule 6, in the id).
    """
    parts = "|".join((
        meter,
        machine_name or "unknown-host",
        run_id or "-",
        observed_at,
        "-" if remaining is None else str(remaining),
        "-" if limit is None else str(limit),
        "-" if reset_seconds is None else str(reset_seconds),
        key_fp or "-",
    ))
    return "rqr_" + hashlib.sha256(parts.encode("utf-8")).hexdigest()[:24]


def _append_quota_reading(
    *, meter: str, remaining: int | None, limit: int | None,
    read_at: str, read_by: str, run_id: str | None,
    key_fp: str | None = None, reset_seconds: int | None = None,
    url: str | None = None,
) -> bool:
    """Append one reading to the history. NEVER raises - same contract as above.

    APPEND-ONLY, AND `do nothing` RATHER THAN `do update`. The latest-row table
    resolves races by keeping the newest READING; this one keeps everything and
    lets the reader decide. A history that updates is not one.

    EVERY READING, INCLUDING ONES THE LATEST ROW REFUSED. See the caller: a
    reading older than the stored one is still a real observation.
    """
    if remaining is None and limit is None:
        return False
    conn = _telemetry_connection(url)
    if conn is None:
        return False
    try:
        # MICROSECONDS, AND GENERATED HERE RATHER THAN PASSED IN. `read_at` is
        # what the arm read and is second-resolution by design; this is when
        # this call recorded it, and it is the field that makes two same-second
        # readings two rows.
        observed_at = datetime.now(UTC).isoformat()
        mach = machine()
        row_id = quota_reading_id(
            meter=meter, machine_name=mach, run_id=run_id,
            observed_at=observed_at, remaining=remaining, limit=limit,
            reset_seconds=reset_seconds, key_fp=key_fp,
        )
        with conn:
            conn.execute(
                "insert into rapidapi_quota_reading "
                "(id, meter, quota_remaining, quota_limit, quota_reset_seconds, "
                " read_at, observed_at, read_by, source_run_id, machine, "
                " key_fingerprint) "
                "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "on conflict (id) do nothing",
                (row_id, meter, remaining, limit, reset_seconds, read_at,
                 observed_at, read_by, run_id, mach, key_fp),
            )
        return True
    except Exception:
        return False
    finally:
        conn.close()


def _record_to_database(
    *, meter: str, remaining: int | None, limit: int | None,
    read_at: str, read_by: str, run_id: str | None,
    key_fp: str | None = None, reset_seconds: int | None = None,
    url: str | None = None,
) -> bool:
    """Upsert one meter's reading. NEVER raises — same contract as the file write.

    NEWEST *READING* WINS, NOT NEWEST WRITE. Two machines reading a decreasing
    counter will race, and the row that arrives second can easily carry the
    figure that was read first — a later write with an older reading. Comparing
    `read_at` in the DO UPDATE clause is what stops the shared number walking
    backwards; comparing arrival order would not.

    THE LIMIT IS STILL NOT INHERITED. The upsert writes `excluded.quota_limit`
    verbatim, NULL included. A COALESCE here would quietly restore the exact
    behaviour the file writer refuses — and the arms are separately metered, so
    an inherited limit may belong to another meter entirely.
    """
    if remaining is None and limit is None:
        return False
    conn = _telemetry_connection(url)
    if conn is None:
        return False
    try:
        with conn:
            conn.execute(
                "insert into rapidapi_quota "
                "(meter, quota_remaining, quota_limit, read_at, read_by, "
                " source_run_id, machine, key_fingerprint, quota_reset_seconds) "
                "values (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "on conflict (meter) do update set "
                "  quota_remaining = excluded.quota_remaining, "
                "  quota_limit     = excluded.quota_limit, "
                "  read_at         = excluded.read_at, "
                "  read_by         = excluded.read_by, "
                "  source_run_id   = excluded.source_run_id, "
                "  machine         = excluded.machine, "
                "  key_fingerprint = excluded.key_fingerprint, "
                # MOVES WITH ITS READING, not independently. The whole row is
                # replaced by the newer READ (see the where clause), so this
                # cannot end up beside a `read_at` it was not read with - which
                # is the only way the subtraction that dates the boundary could
                # silently give a wrong answer.
                "  quota_reset_seconds = excluded.quota_reset_seconds, "
                "  recorded_at     = now() "
                "where excluded.read_at > rapidapi_quota.read_at",
                (meter, remaining, limit, read_at, read_by, run_id, machine(),
                 key_fp, reset_seconds),
            )
        return True
    except Exception:
        return False
    finally:
        conn.close()


def read_database_meters(url: str | None = None) -> dict[str, dict] | None:
    """Every machine's latest reading per meter, or None when unreadable.

    NONE IS NOT "NO READINGS". An unreachable database and a meter nobody has
    ever read produce the same empty mapping, and only one of them means the
    panel's figure is complete.
    """
    conn = _telemetry_connection(url)
    if conn is None:
        return None
    try:
        with conn:
            rows = conn.execute(
                "select meter, quota_remaining, quota_limit, read_at, read_by, "
                "       source_run_id, machine, key_fingerprint from rapidapi_quota"
            ).fetchall()
    except Exception:
        return None
    finally:
        conn.close()
    return {
        str(m): {
            "quota_remaining": rem,
            "quota_limit": lim,
            "at": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "read_on": str(m),
            "read_by": str(by),
            "source_run_id": run,
            "machine": str(mach),
            # WHOSE COUNTER. None on rows written before 2026-09-16, which is
            # "not recorded" and never "a different subscription".
            "key_fingerprint": kfp,
        }
        for m, rem, lim, at, by, run, mach, kfp in rows
    }


def read_rapidapi_meters(path: Path | None = None) -> dict[str, dict]:
    """Every arm's latest reading, keyed by `read_on`. `{}` when there is none.

    Never raises on a corrupt or absent file - same contract as the writer, and
    for the same reason: this is instrumentation, and instrumentation that can
    break a harvest is worse than none.

    IT NORMALISES THE OLD ONE-RECORD SHAPE rather than discarding it. A file
    written before 2026-09-10 is a bare record, and its `read_on` says which
    arm it belongs to - so it is filed under that arm. A record older than
    `read_on` itself has no arm to file it under and lands under
    `"unrecorded"`, which is honest: it means nobody recorded the path, NOT
    that no arm read it (rule 6, on our own instrumentation).
    """
    try:
        raw = json.loads((path or QUOTA_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    meters = raw.get("meters")
    if isinstance(meters, dict):
        return {k: v for k, v in meters.items() if isinstance(v, dict)}
    if "quota_remaining" in raw or "quota_limit" in raw:
        return {raw.get("read_on") or "unrecorded": raw}
    return {}


def read_rapidapi_quota(
    path: Path | None = None, *, read_on: str | None = None
) -> dict | None:
    """One arm's last reading, or None.

    `read_on` names the arm. WITHOUT IT this returns the most recent reading
    across arms, which is what the single-slot file used to mean and is kept so
    existing callers do not change behaviour - but it is the wrong thing to ask
    for now that the arms are separately metered, because "the latest reading"
    is not "this arm's reading". Prefer `read_rapidapi_meters()`, or pass
    `read_on`.
    """
    meters = read_rapidapi_meters(path)
    if not meters:
        return None
    if read_on is not None:
        return meters.get(read_on)
    # `at` is an ISO-8601 UTC string with a fixed width, so lexical order is
    # chronological order. A record missing `at` sorts first rather than
    # crashing the comparison.
    return max(meters.values(), key=lambda r: r.get("at") or "")
