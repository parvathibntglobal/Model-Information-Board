"""The only module that runs SQL. `bench_` tables only (doc 0.3 rule 3, 16).

Every function takes an open connection; the runner owns the transactions.
Publishing (observations, cells, changes) happens in ONE transaction, so a
reader never sees half a run (doc 13).
"""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

#: One run at a time, across every process and machine using this database.
ADVISORY_LOCK = 724_201_022


#: Carried by every observation and published cell (CLAUDE.md: every derived row
#: carries pipeline_version). Bump it when parsing, matching, values or merging
#: change what a page turns into, so the change is re-runnable and diffable.
PIPELINE_VERSION = "benchmarks-1"


@dataclass
class StoredObservation:
    source_key: str
    row_id: str
    benchmark_key: str
    metric: str
    value: float
    rank_high: int | None
    tied: bool
    rank_out_of: int | None
    rank_board: str | None
    variant: str | None
    raw_text: str
    raw_model_name: str
    url: str
    source_date: str | None
    setting_not_stated: bool
    priority: int
    run_id: int
    collected_at: datetime
    stale: bool = False

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.row_id, self.benchmark_key, self.metric)


@dataclass
class StoredCell:
    row_id: str
    benchmark_key: str
    metric: str
    value: float
    rank_high: int | None
    tied: bool
    rank_out_of: int | None
    rank_board: str | None
    variant: str | None
    benchmark_version: str | None
    source_key: str
    url: str
    raw_text: str
    raw_model_name: str
    source_date: str | None
    setting_not_stated: bool
    collected_at: datetime
    needs_review: bool
    run_id: int

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.row_id, self.benchmark_key, self.metric)


# ── the lock and the run row ─────────────────────────────────────────────────


def try_lock(conn) -> bool:
    return bool(conn.execute("SELECT pg_try_advisory_lock(%s)", (ADVISORY_LOCK,)).fetchone()[0])


def unlock(conn) -> None:
    conn.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK,))


def close_abandoned_runs(conn, *, older_than_minutes: int) -> list[int]:
    """A `running` row whose process died would read as running forever."""
    rows = conn.execute(
        "UPDATE bench_run SET status = 'error', finished_at = now(), "
        "report = coalesce(report, '{}'::jsonb) || jsonb_build_object('abandoned', true) "
        "WHERE status = 'running' AND started_at < now() - make_interval(mins => %s) "
        "RETURNING id",
        (older_than_minutes,),
    ).fetchall()
    return [r[0] for r in rows]


def start_run(conn, *, trigger: str, scope: str, dry_run: bool, request_id: str | None) -> int:
    return conn.execute(
        "INSERT INTO bench_run (request_id, trigger, scope, dry_run, status) "
        "VALUES (%s, %s, %s, %s, 'running') RETURNING id",
        (request_id, trigger, scope, dry_run),
    ).fetchone()[0]


def log_file_name(conn, run_id: int) -> str:
    """`run_<id>_<started, UTC>.log`. The start time is in the name because run
    ids repeat across databases, and two databases' run #2 must not share a file.
    judge/benchmarks.py builds the same name to tail a running log."""
    row = conn.execute("SELECT started_at FROM bench_run WHERE id = %s", (run_id,)).fetchone()
    started = row[0]
    return f"run_{run_id}_{started.astimezone(UTC):%Y%m%dT%H%M%S}.log"


def finish_run(conn, run_id: int, *, status: str, report: dict[str, Any], log_text: str) -> None:
    conn.execute(
        "UPDATE bench_run SET status = %s, finished_at = now(), report = %s, log_text = %s "
        "WHERE id = %s",
        (status, json.dumps(report, default=str), log_text, run_id),
    )


def previous_source_reports(conn) -> dict[str, dict[str, Any]]:
    """Each source's most recent finished, published report entry that was taken
    (status OK), for the L3 row-count and release checks. A blocked read is not a
    baseline: run #44 recorded AA GPQA's blocked 27 rows, which would have let the
    next run through unchecked (2026-10-26)."""
    # However long ago it was: a source that kept failing for 20 runs used to
    # lose its baseline, and with it the guard (PR #573 review).
    return dict(
        conn.execute(
            "SELECT DISTINCT ON (s.key) s.key, s.value FROM bench_run r, "
            "jsonb_each(r.report -> 'sources') s "
            "WHERE r.status IN ('ok', 'partial') AND NOT r.dry_run AND r.report IS NOT NULL "
            "AND s.value ->> 'status' = 'OK' ORDER BY s.key, r.id DESC"
        ).fetchall()
    )


def recent_source_reads(conn, key: str, n: int) -> list[dict[str, Any]]:
    """The source's last `n` report entries from real runs, taken or blocked."""
    return [
        r[0]
        for r in conn.execute(
            "SELECT report -> 'sources' -> %s FROM bench_run "
            "WHERE NOT dry_run AND report IS NOT NULL AND (report -> 'sources') ? %s "
            "ORDER BY id DESC LIMIT %s",
            (key, key, n),
        ).fetchall()
    ]


# ── snapshots ────────────────────────────────────────────────────────────────


def save_snapshot(
    conn,
    *,
    run_id: int,
    source_key: str,
    method: str,
    url: str,
    final_url: str | None,
    http_status: int | None,
    content: bytes,
    content_hash: str,
) -> bool:
    """Keep the fetched page, once per distinct content (CLAUDE.md: raw payloads
    are immutable and content-hash addressed). A page unchanged since its last
    copy is not stored again; NO copy is ever deleted (PR #573 review: the old
    keep-10 pruning deleted raw pages). True when a new copy was stored."""
    last = last_snapshot_hash(conn, source_key)
    if last == content_hash:
        return False
    conn.execute(
        "INSERT INTO bench_snapshot (run_id, source_key, method, url, final_url, http_status, "
        "content_hash, size_bytes, body_gz) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            run_id,
            source_key,
            method,
            url,
            final_url,
            http_status,
            content_hash,
            len(content),
            gzip.compress(content),
        ),
    )
    return True


def last_snapshot(conn, source_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, run_id, method, url, final_url, http_status, content_hash, body_gz, fetched_at "
        "FROM bench_snapshot WHERE source_key = %s ORDER BY fetched_at DESC, id DESC LIMIT 1",
        (source_key,),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "run_id": row[1],
        "method": row[2],
        "url": row[3],
        "final_url": row[4],
        "http_status": row[5],
        "content_hash": row[6],
        "content": gzip.decompress(bytes(row[7])),
        "fetched_at": row[8],
    }


def last_snapshot_hash(conn, source_key: str) -> str | None:
    row = conn.execute(
        "SELECT content_hash FROM bench_snapshot WHERE source_key = %s "
        "ORDER BY fetched_at DESC, id DESC LIMIT 1",
        (source_key,),
    ).fetchone()
    return row[0] if row else None


# ── rows ─────────────────────────────────────────────────────────────────────


def existing_rows(conn) -> set[str]:
    return {r[0] for r in conn.execute("SELECT row_id FROM bench_row").fetchall()}


def ensure_row(
    conn,
    *,
    row_id: str,
    host_model_id: str,
    setting: str | None,
    label: str,
    auto_created: bool,
    source_key: str | None,
    dated: str | None = None,
) -> bool:
    """True when the row is new. An existing row takes the label it is given now,
    so a renamed model ("GPT-5.5 Codex" -> "GPT-5.5", 2026-10-26) is not left
    under its old name."""
    inserted = conn.execute(
        "INSERT INTO bench_row (row_id, host_model_id, setting, dated, display_label, "
        "auto_created, first_seen_source) VALUES (%s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (row_id) DO NOTHING RETURNING row_id",
        (row_id, host_model_id, setting, dated, label, auto_created, source_key),
    ).fetchone()
    if inserted is None:
        conn.execute(
            "UPDATE bench_row SET display_label = %s WHERE row_id = %s AND display_label <> %s",
            (label, row_id, label),
        )
    return inserted is not None


# ── observations and cells ───────────────────────────────────────────────────

_OBS_COLUMNS = (
    "source_key, row_id, benchmark_key, metric, value, rank_high, tied, rank_out_of, rank_board, "
    "variant, raw_text, raw_model_name, url, source_date, setting_not_stated, priority, run_id, "
    "collected_at, stale"
)


def load_observations(conn) -> list[StoredObservation]:
    rows = conn.execute(f"SELECT {_OBS_COLUMNS} FROM bench_observation").fetchall()
    return [StoredObservation(*r) for r in rows]


def replace_source_observations(
    conn, source_key: str, observations: list[StoredObservation]
) -> int:
    """The source's fresh observations; anything it no longer lists becomes stale.

    Stale rather than deleted (doc 10.5): the value stops competing in merge,
    and its history is kept.
    """
    keep = {o.key for o in observations}
    current = conn.execute(
        "SELECT row_id, benchmark_key, metric FROM bench_observation "
        "WHERE source_key = %s AND NOT stale",
        (source_key,),
    ).fetchall()
    gone = [k for k in (tuple(r) for r in current) if k not in keep]
    for row_id, benchmark_key, metric in gone:
        conn.execute(
            "UPDATE bench_observation SET stale = true WHERE source_key = %s AND row_id = %s "
            "AND benchmark_key = %s AND metric = %s",
            (source_key, row_id, benchmark_key, metric),
        )
    for o in observations:
        conn.execute(
            "INSERT INTO bench_observation (source_key, row_id, benchmark_key, metric, value, "
            "rank_high, tied, rank_out_of, rank_board, variant, raw_text, raw_model_name, url, "
            "source_date, setting_not_stated, priority, run_id, collected_at, stale, "
            "pipeline_version) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
            "false, %s) "
            "ON CONFLICT (source_key, row_id, benchmark_key, metric) DO UPDATE SET "
            "value = EXCLUDED.value, rank_high = EXCLUDED.rank_high, tied = EXCLUDED.tied, "
            "rank_out_of = EXCLUDED.rank_out_of, rank_board = EXCLUDED.rank_board, "
            "variant = EXCLUDED.variant, raw_text = EXCLUDED.raw_text, "
            "raw_model_name = EXCLUDED.raw_model_name, url = EXCLUDED.url, "
            "source_date = EXCLUDED.source_date, setting_not_stated = EXCLUDED.setting_not_stated, "
            "priority = EXCLUDED.priority, run_id = EXCLUDED.run_id, "
            "collected_at = EXCLUDED.collected_at, stale = false, "
            "pipeline_version = EXCLUDED.pipeline_version",
            (
                o.source_key,
                o.row_id,
                o.benchmark_key,
                o.metric,
                o.value,
                o.rank_high,
                o.tied,
                o.rank_out_of,
                o.rank_board,
                o.variant,
                o.raw_text,
                o.raw_model_name,
                o.url,
                o.source_date,
                o.setting_not_stated,
                o.priority,
                o.run_id,
                o.collected_at,
                PIPELINE_VERSION,
            ),
        )
    return len(gone)


_NO_VALUE_LEFT = (
    "r.auto_created "
    "AND NOT EXISTS (SELECT 1 FROM bench_observation o WHERE o.row_id = r.row_id AND NOT o.stale) "
    "AND NOT EXISTS (SELECT 1 FROM bench_cell x WHERE x.row_id = r.row_id)"
)


def prune_rows(conn) -> list[str]:
    """Rows a run created that no source lists any more are removed (2026-10-26).

    A registry model or a setting/dated row exists because a source once listed
    it; once every source has stopped (its values are all stale) it is only an
    empty line on the page. It is removed with those stale values and comes back
    the next time a source lists it. Tracked models' own rows are never removed
    (not auto_created), nor a model row that still has a setting row under it.
    The changelog keeps its history (bench_change has no link to the row).
    A source that FAILS a fetch keeps its values current, so a bad day never
    removes rows - only a source that really stopped listing a model does.
    """
    children = [
        r[0]
        for r in conn.execute(
            f"SELECT row_id FROM bench_row r WHERE r.row_id <> r.host_model_id AND {_NO_VALUE_LEFT}"
        ).fetchall()
    ]
    _delete_rows(conn, children)
    models = [
        r[0]
        for r in conn.execute(
            f"SELECT row_id FROM bench_row r WHERE r.row_id = r.host_model_id AND {_NO_VALUE_LEFT} "
            "AND NOT EXISTS (SELECT 1 FROM bench_row c "
            "WHERE c.host_model_id = r.row_id AND c.row_id <> r.row_id)"
        ).fetchall()
    ]
    _delete_rows(conn, models)
    return sorted(children + models)


def _delete_rows(conn, row_ids: list[str]) -> None:
    if row_ids:
        conn.execute("DELETE FROM bench_observation WHERE row_id = ANY(%s)", (row_ids,))
        conn.execute("DELETE FROM bench_row WHERE row_id = ANY(%s)", (row_ids,))


def mark_sources_stale(conn, source_keys: list[str]) -> int:
    """Every value from sources no longer read becomes stale (kept, not deleted)."""
    if not source_keys:
        return 0
    return conn.execute(
        "UPDATE bench_observation SET stale = true WHERE source_key = ANY(%s) AND NOT stale",
        (source_keys,),
    ).rowcount


_CELL_COLUMNS = (
    "row_id, benchmark_key, metric, value, rank_high, tied, rank_out_of, rank_board, variant, "
    "benchmark_version, source_key, url, raw_text, raw_model_name, source_date, "
    "setting_not_stated, "
    "collected_at, needs_review, run_id"
)


def load_cells(conn) -> dict[tuple[str, str, str], StoredCell]:
    rows = conn.execute(f"SELECT {_CELL_COLUMNS} FROM bench_cell").fetchall()
    cells = [StoredCell(*r) for r in rows]
    return {c.key: c for c in cells}


def publish_cells(conn, cells: dict[tuple[str, str, str], StoredCell]) -> None:
    """The new cell set replaces the old one (inside the caller's transaction)."""
    existing = {
        tuple(r)
        for r in conn.execute("SELECT row_id, benchmark_key, metric FROM bench_cell").fetchall()
    }
    for row_id, benchmark_key, metric in existing - set(cells):
        conn.execute(
            "DELETE FROM bench_cell WHERE row_id = %s AND benchmark_key = %s AND metric = %s",
            (row_id, benchmark_key, metric),
        )
    for c in cells.values():
        conn.execute(
            "INSERT INTO bench_cell (row_id, benchmark_key, metric, value, rank_high, tied, "
            "rank_out_of, rank_board, variant, benchmark_version, source_key, url, raw_text, "
            "raw_model_name, source_date, setting_not_stated, collected_at, needs_review, run_id, "
            "pipeline_version, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
            "%s, %s, %s, %s, %s, %s, %s, %s, %s, now()) "
            "ON CONFLICT (row_id, benchmark_key, metric) DO UPDATE SET "
            "value = EXCLUDED.value, rank_high = EXCLUDED.rank_high, tied = EXCLUDED.tied, "
            "rank_out_of = EXCLUDED.rank_out_of, rank_board = EXCLUDED.rank_board, "
            "variant = EXCLUDED.variant, benchmark_version = EXCLUDED.benchmark_version, "
            "source_key = EXCLUDED.source_key, url = EXCLUDED.url, raw_text = EXCLUDED.raw_text, "
            "raw_model_name = EXCLUDED.raw_model_name, source_date = EXCLUDED.source_date, "
            "setting_not_stated = EXCLUDED.setting_not_stated, "
            "collected_at = EXCLUDED.collected_at, "
            "needs_review = EXCLUDED.needs_review, run_id = EXCLUDED.run_id, "
            "pipeline_version = EXCLUDED.pipeline_version, updated_at = now()",
            (
                c.row_id,
                c.benchmark_key,
                c.metric,
                c.value,
                c.rank_high,
                c.tied,
                c.rank_out_of,
                c.rank_board,
                c.variant,
                c.benchmark_version,
                c.source_key,
                c.url,
                c.raw_text,
                c.raw_model_name,
                c.source_date,
                c.setting_not_stated,
                c.collected_at,
                c.needs_review,
                c.run_id,
                PIPELINE_VERSION,
            ),
        )


def write_changes(conn, run_id: int, changes: list[dict[str, Any]]) -> None:
    for ch in changes:
        conn.execute(
            "INSERT INTO bench_change (run_id, row_id, benchmark_key, metric, change_type, "
            "old_value, new_value, old_raw, new_raw, old_source, new_source, rank_out_of_old, "
            "rank_out_of_new, source_date, direction, reason, actor, note, needs_review) VALUES "
            "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                run_id,
                ch["row_id"],
                ch.get("benchmark_key"),
                ch.get("metric"),
                ch["change_type"],
                ch.get("old_value"),
                ch.get("new_value"),
                ch.get("old_raw"),
                ch.get("new_raw"),
                ch.get("old_source"),
                ch.get("new_source"),
                ch.get("rank_out_of_old"),
                ch.get("rank_out_of_new"),
                ch.get("source_date"),
                ch.get("direction"),
                ch["reason"],
                ch["actor"],
                ch.get("note"),
                bool(ch.get("needs_review")),
            ),
        )


def write_review_items(conn, run_id: int, items: list[dict[str, Any]]) -> int:
    """New items only: one already open with the same check, cell and message
    is the same problem seen again, not a second one. Returns how many were new."""
    written = 0
    for item in items:
        inserted = conn.execute(
            "INSERT INTO bench_review_item (run_id, check_code, severity, source_key, row_id, "
            "benchmark_key, metric, message) "
            "SELECT %s, %s, %s, %s, %s, %s, %s, %s WHERE NOT EXISTS ("
            "SELECT 1 FROM bench_review_item WHERE status = 'open' AND check_code = %s "
            "AND source_key IS NOT DISTINCT FROM %s AND row_id IS NOT DISTINCT FROM %s "
            "AND benchmark_key IS NOT DISTINCT FROM %s AND metric IS NOT DISTINCT FROM %s "
            "AND message = %s) RETURNING id",
            (
                run_id,
                item["check"],
                item.get("severity", "flag"),
                item.get("source_key"),
                item.get("row_id"),
                item.get("benchmark_key"),
                item.get("metric"),
                item["message"],
                item["check"],
                item.get("source_key"),
                item.get("row_id"),
                item.get("benchmark_key"),
                item.get("metric"),
                item["message"],
            ),
        ).fetchone()
        written += inserted is not None
    return written


def resolve_review_items(conn, raised: list[dict[str, Any]], read_sources: list[str]) -> int:
    """Open items for a source this run READ, that this run did not raise again,
    are `resolved`: the problem went away (an alias, a setting word, a decided
    duplicate). Items for sources not read this run are left as they are, and so
    is anything a person has already acted on. Returns how many were resolved."""
    if not read_sources:
        return 0
    still = {
        (
            i["check"],
            i.get("source_key"),
            i.get("row_id"),
            i.get("benchmark_key"),
            i.get("metric"),
            i["message"],
        )
        for i in raised
    }
    resolved = 0
    for item_id, *identity in conn.execute(
        "SELECT id, check_code, source_key, row_id, benchmark_key, metric, message "
        "FROM bench_review_item WHERE status = 'open' AND source_key = ANY(%s)",
        (read_sources,),
    ).fetchall():
        if tuple(identity) not in still:
            conn.execute(
                "UPDATE bench_review_item SET status = 'resolved' WHERE id = %s", (item_id,)
            )
            resolved += 1
    return resolved


def count_open_review_items(conn) -> int:
    return conn.execute("SELECT count(*) FROM bench_review_item WHERE status = 'open'").fetchone()[
        0
    ]


def replace_source_unmatched(conn, source_key: str, names: dict[str, dict[str, Any]]) -> None:
    """This source's unmatched names are what its latest read listed - no more.

    A name the source stopped listing, or that now matches a row (an alias or a
    decision was added), is removed, so the list never shows a name that is
    already in the table. `names`: raw name -> {reason, base_name, base_key, similar_to}.
    """
    for (raw_name,) in conn.execute(
        "SELECT raw_name FROM bench_unmatched WHERE source_key = %s", (source_key,)
    ).fetchall():
        if raw_name not in names:
            conn.execute(
                "DELETE FROM bench_unmatched WHERE source_key = %s AND raw_name = %s",
                (source_key, raw_name),
            )
    for raw_name, u in names.items():
        conn.execute(
            "INSERT INTO bench_unmatched "
            "(source_key, raw_name, reason, base_name, base_key, similar_to) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (source_key, raw_name) DO UPDATE SET "
            "reason = EXCLUDED.reason, base_name = EXCLUDED.base_name, "
            "base_key = EXCLUDED.base_key, similar_to = EXCLUDED.similar_to, "
            "seen_count = bench_unmatched.seen_count + 1, last_seen = now()",
            (
                source_key,
                raw_name,
                u["reason"],
                u.get("base_name"),
                u.get("base_key"),
                list(u.get("similar_to") or ()) or None,
            ),
        )


def load_name_decisions(conn) -> list[tuple[str, str, str, str | None]]:
    """A person's decisions from the Unmatched list: (name_key, name, action, target)."""
    return [
        tuple(r)
        for r in conn.execute(
            "SELECT name_key, name, action, target_model_id FROM bench_name_decision "
            "ORDER BY created_at"
        ).fetchall()
    ]
