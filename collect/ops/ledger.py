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
# WHAT TWO PHASES STILL CANNOT SAY, AND IT NEEDS A CONTRACT DECISION.
# `harvest_run` has no `outcome` column - the eleven are id, source_id, query_key,
# started_at, finished_at, items_fetched, items_kept, http_errors, exhausted,
# truncated_by, pipeline_version. So three states share one shape once the row is
# closed:
#
#     refused by the terms gate before any request   items_fetched = 0
#     ran, and the platform returned nothing        items_fetched = 0
#     ran, and everything was filtered out          items_fetched > 0, kept = 0
#
# The third is distinguishable and the first two are not.
#
# DO NOT ADD A FIFTH `truncated_by` VALUE TO CLOSE THIS. It will look like the
# gap this column exists for, and it is a different gap:
#
#     truncated_by says A SWEEP STOPPED EARLY. Every value names something that
#     cut short a fetch that was happening - a budget we set, or a wall the
#     platform put up. The column's own comment splits them on exactly that
#     axis: "caps we chose" against "the platform stopping us".
#
#     A REFUSED SWEEP NEVER STARTED. Nothing was truncated, because nothing was
#     fetched. Filing it here would make the column mean two things - "cut short"
#     and "never begun" - and the coverage page renders it as the first.
#
# Nor may a refused sweep be left OPEN. `finished_at IS NULL` is how a killed
# process is recognised, and that is the one distinction the two phases exist to
# preserve.
#
# So until `harvest_run` gains a verdict column, A REFUSED RUN RECORDS ONLY THAT
# IT WAS ATTEMPTED, and that is the honest shape rather than a gap: the row
# exists, the counts are zero, and nothing claims to know why. The proposal is
# docs/proposals/harvest-run-outcome.md.
#
# So FR-10's "attempted and refused" is recordable only as far as the row's
# EXISTENCE, and `harvest_run_fields()` already carries an `outcome` key with
# nowhere to live. That is the proposal - a column, not a convention - and it is
# contract/, so it is flagged rather than taken.
#
# IT DEPENDS ON `source`, WHICH IS ITSELF UNWIRED. `harvest_run.source_id`
# REFERENCES `source(id)`, and `source` holds 0 rows on staging because
# `load_source_rows` has no caller either. So this writer refuses with a sentence
# rather than surfacing a foreign-key violation: the fix is upstream of here, and
# an opaque 23503 sends the reader to the wrong place.

#: Empty, and kept rather than deleted. `outcome`, `sieve_pass_rate`,
#: `pages_fetched` and `pages_stored` were all in here — carried by the adapters
#: and dropped by name because no column held them — and
#: `20260819T0915_harvest_run_columns.sql` gave all four a column.
#:
#: The set stays so a FIFTH homeless field has somewhere to be declared, with the
#: reason it has nowhere to live, instead of being filtered out silently. A
#: permissive `{k: v for k, v in fields.items() if k in COLUMNS}` is how the
#: first four would have vanished without anyone deciding.
_PROPOSED_NOT_IN_SCHEMA: frozenset[str] = frozenset()

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
    "outcome",
    "pages_fetched",
    "pages_stored",
    "sieve_pass_rate",
    "pipeline_version",
)


class UnknownSource(RuntimeError):
    """`harvest_run.source_id` names a `source` row that does not exist."""


@dataclass(frozen=True)
class OpenHarvest:
    """A `harvest_run` row that exists and has not finished. Mirrors `OpenRun`."""

    id: str
    source_id: str
    query_key: str
    started_at: datetime


def open_harvest_run(conn, fields: dict[str, Any]) -> OpenHarvest:
    """Insert the row BEFORE the fetch, with `finished_at` NULL.

    TWO PHASES, FOR THE REASON `job_run` HAS TWO. One statement at the end cannot
    represent the state that matters most: **a process that dies cannot write its
    own failure.** A killed sweep leaves `finished_at IS NULL`, and that absence is
    the only carrier of "started and never came back".

    It also settles the terms question. The row exists before the first request,
    so a sweep the terms gate refuses has a record saying it was ATTEMPTED — which
    FR-10 needs distinguishable from a sweep that ran and found nothing. A
    single-statement writer can express neither, because it never runs.

    Refuses when the `source` row is absent, upstream of the foreign key: `source`
    holds 0 rows because `load_source_rows` has no caller, and `23503` would name
    this writer instead of that loader.
    """
    _reject_unknown_keys(fields)
    source_id = fields["source_id"]
    if not conn.execute("SELECT 1 FROM source WHERE id = %s", (source_id,)).fetchone():
        raise UnknownSource(
            f"no source row for {source_id!r}, so this harvest cannot be "
            "recorded. `harvest_run.source_id` references `source(id)`, and "
            "`load_source_rows` is the loader that fills it — which has no "
            "caller yet. Wire that first; this refusal is upstream of a foreign "
            "key violation, not a substitute for one."
        )

    started_at = fields.get("started_at") or datetime.now(UTC)
    row = {
        "id": fields["id"],
        "source_id": source_id,
        "query_key": fields["query_key"],
        "started_at": started_at,
        "pipeline_version": fields.get("pipeline_version") or settings().pipeline_version,
    }
    conn.execute(
        "INSERT INTO harvest_run (id, source_id, query_key, started_at, pipeline_version) "
        "VALUES (%(id)s, %(source_id)s, %(query_key)s, %(started_at)s, %(pipeline_version)s) "
        "ON CONFLICT (id) DO NOTHING",
        row,
    )
    return OpenHarvest(
        id=row["id"], source_id=source_id, query_key=row["query_key"], started_at=started_at
    )


def close_harvest_run(
    conn, open_harvest: OpenHarvest, fields: dict[str, Any], *, outcome: str
) -> str:
    """Fill in what the sweep did. Only ever called by a process still alive.

    **`outcome` IS REQUIRED AND KEYWORD-ONLY, because the schema now refuses the
    alternative.** `harvest_run_finish_ck` asserts
    `(finished_at IS NULL) = (outcome IS NULL)`, so an update setting a finish
    time without a verdict is REJECTED rather than accepted — and that is the
    point of it. Engineer 2's argument, and it is better than the one I made:

        without the constraint, a close that forgets the verdict succeeds and
        leaves "finished, verdict unknown", which is indistinguishable from a
        schema that never recorded verdicts at all.

        with it, the update fails and the row stays both-NULL, which is
        job_run's own "did not finish" and is TRUE.

    So a half-written row is accurate rather than missing. Keyword-only and with
    no default so a caller cannot reach the failure by omission: the refusal
    happens in Python, at the call site, rather than as a 23514 from the database.

    **`items_fetched = 0` IS WRITTEN, NOT LEFT NULL.** Zero is a measurement — the
    sweep ran and the platform returned nothing — and NULL is reserved for the
    sweep that never came back. Same distinction as E4's `unavailable` against
    `not_applicable`, one table over.
    """
    _reject_unknown_keys(fields)
    if outcome not in (OK, REFUSED, ERROR):
        raise ValueError(
            f"outcome must be one of {OK!r}, {REFUSED!r}, {ERROR!r}, not "
            f"{outcome!r}. `harvest_run_outcome_ck` would refuse it, and this "
            "refusal names the vocabulary rather than the constraint."
        )
    row = {
        "id": open_harvest.id,
        "finished_at": fields.get("finished_at") or datetime.now(UTC),
        "items_fetched": fields.get("items_fetched") or 0,
        "items_kept": fields.get("items_kept") or 0,
        "http_errors": fields.get("http_errors") or 0,
        "exhausted": fields.get("exhausted"),
        "truncated_by": fields.get("truncated_by"),
        "outcome": outcome,
        "pages_fetched": fields.get("pages_fetched"),
        "pages_stored": fields.get("pages_stored"),
        "sieve_pass_rate": fields.get("sieve_pass_rate"),
    }
    conn.execute(
        "UPDATE harvest_run SET finished_at = %(finished_at)s, "
        "items_fetched = %(items_fetched)s, items_kept = %(items_kept)s, "
        "http_errors = %(http_errors)s, exhausted = %(exhausted)s, "
        "truncated_by = %(truncated_by)s, outcome = %(outcome)s, "
        "pages_fetched = %(pages_fetched)s, pages_stored = %(pages_stored)s, "
        "sieve_pass_rate = %(sieve_pass_rate)s WHERE id = %(id)s",
        row,
    )
    return open_harvest.id


#: ⚠ ANY DURATION FIGURE OVER `harvest_run` MUST CARRY THIS.
#:
#: A refused run has `finished_at` ≈ `started_at`, because a gate check is all
#: that happened between them. Averaging those in with real sweeps is not a small
#: bias: BOTH harvest commands refuse until their terms rulings land, so **the
#: first population of this table is entirely refusals** and the mean duration of
#: a sweep would be the mean duration of a gate check.
#:
#: Engineer 2's warning, and it lives here rather than in a document because the
#: person writing `avg(finished_at - started_at)` is reading this module, not
#: docs/proposals.
DURATION_FILTER = "outcome = 'ok'"


def _reject_unknown_keys(fields: dict[str, Any]) -> None:
    """A key that is neither a column nor a known proposal is a decision nobody made."""
    unknown = set(fields) - set(_HARVEST_RUN_COLUMNS) - _PROPOSED_NOT_IN_SCHEMA
    if unknown:
        raise ValueError(
            f"harvest_run_fields() carried {sorted(unknown)}, which is neither a "
            "column of harvest_run nor a known proposal. Add the column to "
            "contract/tables.sql, or add the key to _PROPOSED_NOT_IN_SCHEMA with "
            "the reason it has nowhere to live."
        )
