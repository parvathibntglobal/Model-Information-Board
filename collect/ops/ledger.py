"""`job_run` rows: what ran, when, and what it did. Written before the work.

WHY A TABLE AND NOT THE JSONL JOURNAL BESIDE IT. `Journal` records a night for
whoever reads that file; this records it in the database the rows are about. The
difference is that only one of them can be joined against, and every finding that
argued for this table was a join nobody could write:

    in_window at its schema default on 340 rows   has recompute_window run HERE?
    one last_swept_at from an ad-hoc mark_swept   has anything ever swept HERE?
    three writers greping as wired                has this caller ever run HERE?

Each cost a manual investigation. `assert_no_phantom_sweeps` is cheap only
because it can join `last_swept_at` against `harvest_run` — a contradiction is
checkable and an absence is not.

THE TWO STATES NOTHING READING THIS MAY COLLAPSE
------------------------------------------------
    finished_at IS NULL, outcome IS NULL     still running, or killed
    outcome = 'error'                        ran, and raised

A killed process cannot write its own failure, so the first has to be carried by
an absence. The repairs are opposite — one is "find out why the process died",
the other is "read the stage's own error" — and a reader showing both as red has
thrown away which one to do. `job_run_finish_ck` enforces that the pair moves
together, so a row can never claim an outcome without a finishing time.

`unfinished()` exists so that question has one implementation rather than being
re-derived by whoever needs it next.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from collect.config import settings
from collect.ids import stable_id

#: `collect/ops/chain.py`'s vocabulary, and `job_run_outcome_ck`'s. One set of
#: words for one concept — the first version of the CHECK said `failed` and
#: would have needed a translation layer here.
OK = "ok"
REFUSED = "refused"
ERROR = "error"


@dataclass(frozen=True)
class OpenRun:
    """A row that exists and has not concluded. Returned by `open_run`."""

    id: str
    stage: str
    started_at: datetime


def open_run(conn, stage: str, *, pipeline_version: str | None = None) -> OpenRun:
    """Write the row BEFORE the stage does its work.

    This ordering is the entire point of the table. A row written only on
    success leaves nothing behind when a process is killed, and a night with no
    rows is indistinguishable from a night that never started — which is the
    condition `docs/ops-nightly-chain.md` opens by refusing.

    Committed immediately rather than left in the caller's transaction: a stage
    that rolls back must still leave evidence that it ran.
    """
    started = datetime.now(UTC)
    run_id = stable_id("job_run", stage, started.isoformat())
    version = pipeline_version or settings().pipeline_version
    conn.execute(
        "INSERT INTO job_run (id, stage, started_at, pipeline_version) "
        "VALUES (%s, %s, %s, %s)",
        (run_id, stage, started, version),
    )
    conn.commit()
    return OpenRun(id=run_id, stage=stage, started_at=started)


def close_run(
    conn,
    run: OpenRun,
    *,
    outcome: str,
    detail: str = "",
    counts: dict[str, Any] | None = None,
) -> None:
    """Conclude the row. `outcome` must be one the CHECK allows.

    `items_in`/`items_out` are read from `counts` and stay NULL when absent —
    a stage that refused counted nothing, and 0 would assert it counted and
    found none (rule 6).
    """
    import json

    counts = counts or {}
    conn.execute(
        "UPDATE job_run SET finished_at = %s, outcome = %s, items_in = %s, "
        "items_out = %s, detail = %s WHERE id = %s",
        (
            datetime.now(UTC),
            outcome,
            counts.get("items_in"),
            counts.get("items_out"),
            json.dumps({"detail": detail, **counts}) if (detail or counts) else None,
            run.id,
        ),
    )
    conn.commit()


def unfinished(conn, *, older_than_minutes: int = 0) -> list[tuple[str, str, datetime]]:
    """Rows that started and never concluded. **Not the same as failures.**

    One implementation of the question, so nobody re-derives it as
    `outcome != 'ok'` and folds a killed process in with a stage that raised.
    Those need opposite repairs.
    """
    rows = conn.execute(
        "SELECT id, stage, started_at FROM job_run "
        "WHERE finished_at IS NULL "
        "  AND started_at < now() - make_interval(mins => %s) "
        "ORDER BY started_at",
        (older_than_minutes,),
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def last_run(conn, stage: str) -> tuple[datetime, str | None] | None:
    """When `stage` last started, and how it ended. None if it never has.

    **None is the answer the three findings needed** — "has this ever run
    against this database" — and it is a query rather than an audit only
    because the row exists whether or not the stage succeeded.
    """
    row = conn.execute(
        "SELECT started_at, outcome FROM job_run WHERE stage = %s "
        "ORDER BY started_at DESC LIMIT 1",
        (stage,),
    ).fetchone()
    return (row[0], row[1]) if row else None
