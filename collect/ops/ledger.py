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

# ── harvest_run: the sweep's own ledger ──────────────────────────────────
#
# THREE ADAPTERS BUILD THIS ROW AND NOTHING WROTE IT. `harvest_run_fields()`
# exists on the GitHub, blog and Reddit harvesters, is called only from tests,
# and `collect/ops/alerts.py` says so in its own docstring: "`harvest_run_fields()`
# dicts and nothing inserts them".
#
# That is why FR-10 read as a design question for weeks. It was not one — the
# data was prepared, shaped to the columns, and had no writer, so no yield figure
# could be computed, no budget stop could be told from an empty sweep, and
# `assert_no_phantom_sweeps` had a permanently-zero operand.
#
# IT DEPENDS ON `source`, WHICH IS ITSELF UNWIRED. `harvest_run.source_id`
# REFERENCES `source(id)`, and `source` holds 0 rows on staging because
# `load_source_rows` has no caller either. So this writer refuses with a sentence
# rather than surfacing a foreign-key violation: the fix is upstream of here, and
# an opaque 23503 sends the reader to the wrong place.

#: Keys `harvest_run_fields()` carries that `contract/tables.sql` has no column
#: for. Both are PROPOSED — see the adapters' docstrings — and both are dropped
#: here by name rather than by a permissive filter, so a third one added upstream
#: fails loudly instead of being silently discarded.
_PROPOSED_NOT_IN_SCHEMA = frozenset({"outcome", "sieve_pass_rate"})

#: Every column of `harvest_run` this writer sets. Named, so a new column in the
#: contract that nothing populates is visible here rather than defaulting quietly.
_HARVEST_RUN_COLUMNS = (
    "id",
    "source_id",
    "query_key",
    "started_at",
    "finished_at",
    "items_fetched",
    "items_kept",
    "http_errors",
    "exhausted",
    "truncated_by",
    "pipeline_version",
)


class UnknownSource(RuntimeError):
    """`harvest_run.source_id` names a `source` row that does not exist."""


def write_harvest_run(conn, fields: dict[str, Any]) -> str:
    """Insert one `harvest_run` row from any adapter's `harvest_run_fields()`.

    Takes the dict the adapters already build rather than their run objects, so
    one writer serves all three platforms and the shape stays their business.

    `ON CONFLICT DO NOTHING` on the id, which is derived from
    `(source_id, query_key, started_at)`: re-running a driver over the same
    completed sweep is a legitimate no-op, and a second row would double every
    yield figure computed off this table.

    Refuses rather than letting the foreign key fire, because `source` is
    currently empty and `23503 insert or update on table "harvest_run" violates
    foreign key constraint` reads as a bug in this writer rather than as a
    missing loader upstream.
    """
    unknown = set(fields) - set(_HARVEST_RUN_COLUMNS) - _PROPOSED_NOT_IN_SCHEMA
    if unknown:
        raise ValueError(
            f"harvest_run_fields() carried {sorted(unknown)}, which is neither a "
            f"column of harvest_run nor a known proposal. Add the column to "
            f"contract/tables.sql, or add the key to _PROPOSED_NOT_IN_SCHEMA "
            f"with the reason it has nowhere to live."
        )

    source_id = fields["source_id"]
    exists = conn.execute(
        "SELECT 1 FROM source WHERE id = %s", (source_id,)
    ).fetchone()
    if not exists:
        raise UnknownSource(
            f"no source row for {source_id!r}, so this harvest cannot be "
            "recorded. `harvest_run.source_id` references `source(id)`, and "
            "`load_source_rows` is the loader that fills it — which has no "
            "caller yet. Wire that first; this refusal is upstream of a foreign "
            "key violation, not a substitute for one."
        )

    row = {k: fields.get(k) for k in _HARVEST_RUN_COLUMNS}
    row.setdefault("pipeline_version", settings().pipeline_version)
    columns = ", ".join(_HARVEST_RUN_COLUMNS)
    placeholders = ", ".join(f"%({c})s" for c in _HARVEST_RUN_COLUMNS)
    conn.execute(
        f"INSERT INTO harvest_run ({columns}) VALUES ({placeholders}) "  # noqa: S608
        "ON CONFLICT (id) DO NOTHING",
        row,
    )
    return row["id"]

