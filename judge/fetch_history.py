"""When a model was last fetched, per model, from the shared `fetch_log`.

For the model page's "last fetched" line, which has to exist before any
schedule can decide NOT to fetch a model: a model a schedule stopped fetching
reads exactly like a model nobody discusses (rule 4), unless the page says when
it was last looked at.

⚠ NOT `model_version.last_swept_at`. That column belongs to the nightly sweep;
  `scripts/fetch_model.py` never writes it. Measured 2026-09-28 on staging it
  was set on 6 of 242 models, the latest on 2026-08-24, and on 2 of the 27
  models with a per-model fetch - so it would have said "never" about 25 models
  that were fetched.

⚠ TWO FACTS, KEPT APART. The last fetch that ended `ok`, and the last attempt
  when it came LATER and ended any other way. Measured 2026-09-28: 34 of 87 runs
  ended `ok`, the rest `error`, `stopped` or `abandoned`, so "the last run" and
  "the last successful run" are different answers for most models.

⚠ AS RECORDED IN THE SHARED LOG, AND THE PAGE SAYS SO. A run writes its lines
  to its own machine's file first; one whose database write failed exists only
  there, the same shape as #393 for the spend ledger. So "no per-model fetch
  recorded" is a statement about the shared log, not about the world.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

#: The end status a finished run writes (`Progress.done("ok", ...)`).
OK = "ok"

#: A run with a `run` line and no `end` line. Still running, or it died and no
#: reaper has marked it yet - the log cannot say which, so neither is claimed.
NO_END = "no end recorded"


@dataclass(frozen=True)
class RunLine:
    run_id: str
    started_at: datetime
    status: str | None      # the latest `end` record's status, or None
    detail: str | None
    ended_at: datetime | None


def summarise(runs: list[RunLine]) -> dict[str, Any]:
    """`{succeeded, later_attempt, runs_recorded}` for one model.

    `succeeded` is the latest run that ended `ok`, by when it ended.
    `later_attempt` is the latest run, when it started after that success ended
    (or when there is no success at all) and did not itself end `ok`. Both are
    None when there is nothing to say; `runs_recorded` 0 means the shared log
    holds no run for this model.
    """
    ok = [r for r in runs if r.status == OK and r.ended_at is not None]
    succeeded = max(ok, key=lambda r: r.ended_at) if ok else None
    latest = max(runs, key=lambda r: r.started_at) if runs else None

    later = None
    if latest is not None and latest.status != OK and (
            succeeded is None or latest.started_at > succeeded.ended_at):
        later = latest

    return {
        "succeeded": None if succeeded is None else {
            "at": succeeded.ended_at.isoformat(), "run_id": succeeded.run_id},
        "later_attempt": None if later is None else {
            "at": (later.ended_at or later.started_at).isoformat(),
            "outcome": later.status or NO_END,
            "detail": later.detail,
            "run_id": later.run_id},
        "runs_recorded": len(runs),
    }


def read(conn, model_version_id: str) -> dict[str, Any]:
    """The summary for one model, from `fetch_log`. Raises on a read failure;
    the caller turns that into an explicit unknown, never into "none recorded".
    """
    rows = conn.execute(
        "SELECT r.run_id, r.at, e.payload->>'status', e.payload->>'detail', e.at "
        "FROM fetch_log r "
        "LEFT JOIN LATERAL ("
        "  SELECT payload, at FROM fetch_log e "
        "  WHERE e.run_id = r.run_id AND e.kind = 'end' "
        "  ORDER BY e.at DESC, e.seq DESC LIMIT 1"
        ") e ON true "
        "WHERE r.kind = 'run' AND r.model_version_id = %s",
        (model_version_id,),
    ).fetchall()
    return summarise([RunLine(*row) for row in rows])
