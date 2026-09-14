"""Mark a fetch run that stopped reporting, without claiming to know why.

THE DEFECT

A fetch run's state is not a column. `/fetch/runs` derives it from `fetch_log`:
a run is finished when some record has `kind == "end"`, and running otherwise.
So a run whose PROCESS ends without writing that record — killed, crashed, the
laptop shut — reads as running forever. Measured 2026-09-14: one had been
"running" for 70.5 hours, and `POST /fetch/stop` cannot help because there is no
process left to signal.

While that is true the fetch history cannot be read at all: "running" means
either "working now" or "died some time in the last three days", and nothing
distinguishes them.

WHY SILENCE AND NOT `finished_at IS NULL`

A run with no end record may be perfectly alive. When this was written, of six
runs without one, the newest had last spoken 13 minutes earlier from another
machine and was very likely mid-extract. Reaping on "has no end record" would
have declared a live run dead and, worse, done it to somebody else's run on a
shared database.

So the test is SILENCE: no new line for `silent_for`. A healthy run writes a
stage line per pipeline step and, through `on_thread`, one per extracted thread,
so the gaps are minutes. The default below is far longer than any measured gap.

WHY `abandoned` AND NOT `error`

We know the run stopped reporting. We do not know that it failed, and those are
different facts — a missing value must not become a definite one. The status
vocabulary already draws this distinction once: `web/src/components/FetchPanel.jsx`
keeps `stopped` apart from `error` because "a run somebody chose to abandon and a
run that broke are different facts". This is a third: nobody chose it and nothing
reported a break. The detail line says only what is known — the last thing the
run said, and when.

APPEND-ONLY

The reaper writes one new `fetch_log` row per dead run and changes nothing that
is already there. The run's own account of itself stays exactly as it left it.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from judge import spend_ledger

log = logging.getLogger(__name__)

#: How long a run may say nothing before it is presumed gone. Generous on
#: purpose: the cost of waiting is a stale row in a history nobody is reading
#: yet, and the cost of being wrong is declaring a live run — possibly another
#: machine's — dead while it is still writing to the same database.
DEFAULT_SILENT_FOR = datetime.timedelta(
    seconds=int(os.getenv("FETCH_ABANDONED_AFTER_SECONDS", str(45 * 60)))
)

#: The status this writes. Not in `FETCH_TONE`'s original three, and added to
#: the frontend alongside this.
ABANDONED = "abandoned"


@dataclass(frozen=True)
class ReapedRun:
    run_id: str
    machine: str | None
    last_at: datetime.datetime
    silent_for: datetime.timedelta
    last_said: str


def find_abandoned(
    conn: Any,
    *,
    now: datetime.datetime | None = None,
    silent_for: datetime.timedelta = DEFAULT_SILENT_FOR,
) -> list[ReapedRun]:
    """Runs with no `end` record that have said nothing for `silent_for`.

    READ ONLY. Split from the write so the set can be inspected before anything
    is appended, and so a caller can report "nothing to do" honestly.
    """
    now = now or datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - silent_for
    rows = conn.execute(
        "SELECT run_id, max(at) AS last_at, max(machine) AS machine "
        "FROM fetch_log GROUP BY run_id "
        # `kind` is a real column and agrees with payload->>'kind' on every row
        # (checked: 0 disagreements), so this does not have to open the JSON.
        "HAVING bool_or(kind = 'end') = false AND max(at) < %(cutoff)s "
        "ORDER BY max(at)",
        {"cutoff": cutoff},
    ).fetchall()
    out: list[ReapedRun] = []
    for run_id, last_at, machine in rows:
        said = conn.execute(
            "SELECT payload FROM fetch_log WHERE run_id = %s ORDER BY seq DESC LIMIT 1",
            (run_id,),
        ).fetchone()
        rec = said[0] if said else {}
        rec = rec if isinstance(rec, dict) else json.loads(rec or "{}")
        label = rec.get("name") or rec.get("id") or rec.get("kind") or "nothing"
        out.append(
            ReapedRun(
                run_id=str(run_id),
                machine=machine,
                last_at=last_at,
                silent_for=now - last_at,
                last_said=str(label),
            )
        )
    return out


def reap(
    conn: Any,
    *,
    now: datetime.datetime | None = None,
    silent_for: datetime.timedelta = DEFAULT_SILENT_FOR,
    dry_run: bool = False,
) -> list[ReapedRun]:
    """Append one `abandoned` end record per silent run. Returns what it marked.

    NEVER RAISES ON THE WRITE. The caller is a fetch about to start or a page
    about to render, and neither should fail because a tidy-up could not be
    recorded. A reaper that takes down the thing it was cleaning up for is worse
    than a stale row.
    """
    now = now or datetime.datetime.now(datetime.timezone.utc)
    dead = find_abandoned(conn, now=now, silent_for=silent_for)
    if dry_run or not dead:
        return dead
    marked: list[ReapedRun] = []
    for run in dead:
        minutes = run.silent_for.total_seconds() / 60
        rec = {
            "kind": "end",
            "status": ABANDONED,
            # ONLY WHAT IS KNOWN. Not "failed", not "timed out" - the run stopped
            # writing and that is the entire observation.
            "detail": (
                f"no progress recorded for {minutes:.0f} minutes; the last thing "
                f"this run reported was {run.last_said!r} at "
                f"{run.last_at.strftime('%Y-%m-%dT%H:%M:%SZ')}. Marked by the "
                f"reaper, not by the run — why it stopped is not recorded "
                f"anywhere and is not being guessed at here."
            ),
            "at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            # WHO SAID SO. The row keeps the RUN's machine, because the record
            # is about that run and the history groups by it — but this line was
            # not written by that machine, and on a shared database the
            # difference matters. #267 was somebody finding rows they could not
            # attribute; an end record appearing on another host's run with
            # nothing saying who added it is the same surprise.
            "reaped": True,
            "reaped_by": spend_ledger.machine(),
        }
        try:
            _append(conn, run_id=run.run_id, rec=rec)
            marked.append(run)
        except Exception:  # noqa: BLE001 - see the docstring
            log.warning("could not mark %s abandoned", run.run_id, exc_info=True)
    return marked


def _append(conn: Any, *, run_id: str, rec: dict) -> None:
    """One row, with the same id derivation `_mirror_fetch_line` uses.

    `seq` is one past the run's highest, so the record sorts last — the log is a
    SEQUENCE and several lines can share a second, so ordering by time alone
    would let the end record land mid-run.
    """
    payload = json.dumps(rec, sort_keys=True)
    row = conn.execute(
        "SELECT coalesce(max(seq), -1) + 1, max(machine), max(model_version_id) "
        "FROM fetch_log WHERE run_id = %s",
        (run_id,),
    ).fetchone()
    seq, machine, mv_id = row
    line_id = "fl_" + hashlib.sha256(f"{run_id}|{seq}|{payload}".encode()).hexdigest()[:24]
    conn.execute(
        "INSERT INTO fetch_log (id, run_id, seq, at, machine, payload, kind, "
        "model_version_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
        # Idempotent, so reaping twice is a no-op rather than a duplicate end.
        "ON CONFLICT (id) DO NOTHING",
        (line_id, run_id, seq, rec["at"], machine, payload, rec["kind"], mv_id),
    )
    conn.commit()
