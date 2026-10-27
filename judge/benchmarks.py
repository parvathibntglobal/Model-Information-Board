"""The Benchmarks page (signed in): read the `bench_` tables, start a run.

`collect/benchmarks/` writes these tables; this module only reads them, and
never imports collect (the lane rule) - a run is started as a background
process, `python -m collect.cli benchmarks run`, the way /fetch/start starts
scripts/fetch_model.py. The run never executes inside the web request.

Values are shown RAW (Parvathi, 2026-10-22): each cell is `raw_text`, exactly
as the source printed it ("88.0", "0.9577", "1"), with its source, link and
date. No unit is added, nothing is rounded, and nothing here computes a rank, a
percentile or a score. The one-unit `value` the run stores for its checks is
not sent to the page.

WHICH DATABASE. `BENCHMARKS_DATABASE_URL` when set, else `DATABASE_URL`.
While the page is a local build it reads and writes the local database, and
the Run button refuses a target that is not on this machine.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from psycopg import errors

from judge.writeguard import is_local as writeguard_is_local

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "contract" / "benchmarks"
TRACKED_MODELS = REPO_ROOT / "contract" / "tracked_models.yaml"

#: The order setting rows are listed under their model.
SETTING_ORDER = (
    "max",
    "xhigh",
    "high",
    "medium",
    "low",
    "minimal",
    "none",
    "thinking",
    "120k-max",
    "120k-high",
    "120k-medium",
    "120k-low",
    "thinking-64k",
    "thinking-32k",
    "thinking-16k",
    "thinking-8k",
    "thinking-1k",
    "reasoning-beta",
    "refinement",
)
#: A change this recent carries the `new` / `changed` badge (doc 25.3).
RECENT_DAYS = 7
LOG_TAIL_BYTES = 200_000


class BenchmarksUnavailable(RuntimeError):
    """No database, or the bench_ tables are not migrated there."""


class RunRefused(RuntimeError):
    pass


def database_url() -> str | None:
    return os.environ.get("BENCHMARKS_DATABASE_URL") or os.environ.get("DATABASE_URL")


def is_local(dsn: str | None) -> bool:
    """The board's own check (judge/writeguard.py): only a postgres URL naming
    this machine is local. A keyword DSN ("host=... dbname=...") or anything
    else unreadable counts as REMOTE - it used to count as local when it had no
    URL hostname, which unlocked runs against Railway (PR #573 review)."""
    return bool(dsn) and writeguard_is_local(dsn)


@contextmanager
def connection():
    import psycopg

    dsn = database_url()
    if not dsn:
        raise BenchmarksUnavailable(
            "no database is configured (BENCHMARKS_DATABASE_URL / DATABASE_URL)"
        )
    try:
        conn = psycopg.connect(dsn, connect_timeout=5)
    except psycopg.Error as error:
        raise BenchmarksUnavailable(
            f"the benchmarks database is not reachable: {type(error).__name__}"
        ) from error
    try:
        exists = conn.execute("SELECT to_regclass('public.bench_cell') IS NOT NULL").fetchone()[0]
        if not exists:
            raise BenchmarksUnavailable(
                "the bench_ tables are not in this database yet - apply "
                "contract/migrations/20261022T1200_bench_tables.sql"
            )
        yield conn
        conn.commit()
    finally:
        conn.close()


def _yaml(name: str) -> Any:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


def _seeds() -> list[dict[str, str]]:
    raw = yaml.safe_load(TRACKED_MODELS.read_text(encoding="utf-8"))
    return [
        {"id": m["registry"], "name": m["name"]}
        for m in raw["models"]
        if m.get("kind") == "text" and m.get("registry")
    ]


def _columns() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    raw = _yaml("benchmarks.yaml")
    benches = sorted(
        raw["benchmarks"],
        key=lambda b: (b["category"], b["order"]),
    )
    sections = []
    by_key: dict[str, dict[str, Any]] = {}
    for cat in sorted(raw["categories"], key=lambda c: c["order"]):
        columns = []
        for b in (x for x in benches if x["category"] == cat["key"]):
            for metric in b["metrics"]:
                column = {
                    "key": f"{b['key']}_{metric}",
                    "benchmark": b["key"],
                    "label": b["label"] if metric == "score" else f"{b['label']} {metric}",
                    "metric": metric,
                    "better": "lower"
                    if metric == "rank"
                    else ("higher" if b["higher_is_better"] else "lower"),
                    "volatility": b["volatility"],
                    "benchmark_version": b.get("benchmark_version"),
                }
                columns.append(column)
                by_key[column["key"]] = column
        if columns:
            sections.append({"key": cat["key"], "label": cat["label"], "columns": columns})
    return sections, by_key


def _sources() -> dict[str, dict[str, Any]]:
    return {s["key"]: s for s in _yaml("sources.yaml")["sources"]}


# ── the table ────────────────────────────────────────────────────────────────


def table(conn) -> dict[str, Any]:
    sections, columns = _columns()
    sources = _sources()
    seeds = _seeds()
    rows = conn.execute(
        "SELECT row_id, host_model_id, setting, dated, display_label FROM bench_row"
    ).fetchall()
    # Under each model: its setting rows, then each dated release (with its own
    # setting rows after it). The model's own row is never a dated one.
    settings_by_model: dict[str, list[tuple[str, str | None, str, str | None]]] = {}
    base_labels: dict[str, str] = {}
    for row_id, model_id, setting, dated, label in rows:
        if setting or dated:
            settings_by_model.setdefault(model_id, []).append((row_id, setting, label, dated))
        else:
            base_labels[model_id] = label

    cells: dict[str, dict[str, Any]] = {}
    used_sources: set[str] = set()
    for (
        row_id,
        benchmark_key,
        metric,
        value,
        tied,
        rank_out_of,
        rank_board,
        variant,
        benchmark_version,
        source_key,
        url,
        raw_text,
        raw_model_name,
        source_date,
        setting_not_stated,
        collected_at,
        needs_review,
    ) in conn.execute(
        "SELECT row_id, benchmark_key, metric, value, tied, rank_out_of, rank_board, "
        "variant, benchmark_version, source_key, url, raw_text, raw_model_name, source_date, "
        "setting_not_stated, collected_at, needs_review FROM bench_cell"
    ).fetchall():
        key = f"{benchmark_key}_{metric}"
        if key not in columns:
            continue
        used_sources.add(source_key)
        source = sources.get(source_key, {})
        cells.setdefault(row_id, {})[key] = {
            "display": raw_text,
            # The value in one unit (0.912 and 91.2% are both 91.2): for SORTING a
            # column only - the page always shows `display` (2026-10-26).
            "sort": value,
            "tied": tied,
            "source": source_key,
            "source_label": source.get("label", source_key),
            "url": url,
            "variant": variant,
            "benchmark_version": benchmark_version,
            "raw_name": raw_model_name,
            "source_date": source_date,
            "collected_at": collected_at.isoformat() if collected_at else None,
            "rank_out_of": rank_out_of,
            "rank_board": rank_board,
            "setting_not_stated": setting_not_stated,
            "needs_review": needs_review,
            "badges": [],
        }

    since = datetime.now(UTC) - timedelta(days=RECENT_DAYS)
    first_run = conn.execute(
        "SELECT min(id) FROM bench_run WHERE NOT dry_run AND status <> 'running'"
    ).fetchone()[0]
    for row_id, benchmark_key, metric, change_type, direction, run_id in conn.execute(
        "SELECT row_id, benchmark_key, metric, change_type, direction, run_id FROM bench_change "
        "WHERE changed_at >= %s AND change_type IN ('added', 'updated', 'source_changed') "
        "ORDER BY id",
        (since,),
    ).fetchall():
        cell = cells.get(row_id, {}).get(f"{benchmark_key}_{metric}")
        if cell is None or run_id == first_run:
            continue  # the first import is not "new" (doc 12: collapse it)
        badge = "new" if change_type == "added" else "changed"
        cell["badges"] = [b for b in cell["badges"] if b not in ("new", "changed")] + [badge]
        if direction in ("better", "worse"):
            cell["direction"] = direction

    def ordered(entries):
        def key(e):
            setting, dated = e[1], e[3]
            rank = (
                -1
                if setting is None
                else (SETTING_ORDER.index(setting) if setting in SETTING_ORDER else 99)
            )
            return (dated is not None, dated or "", rank)

        return sorted(entries, key=key)

    def model_row(model_id: str, label: str, group: str) -> dict[str, Any]:
        # A setting or dated row with no value is not shown (the run removes
        # such rows too; this keeps the page right between runs).
        children = [
            {
                "row_id": row_id,
                "label": label,
                "setting": setting,
                "dated": dated,
                "cells": cells.get(row_id, {}),
            }
            for row_id, setting, label, dated in ordered(settings_by_model.get(model_id, []))
            if cells.get(row_id)
        ]
        return {
            "row_id": model_id,
            "label": label,
            "group": group,
            "cells": cells.get(model_id, {}),
            "children": children,
        }

    # The tracked models, in contract order, every one shown; then registry models
    # a source listed (rows exist only once matched), by name. A registry row with
    # no value left is not shown.
    out_rows = [model_row(seed["id"], seed["name"], "tracked") for seed in seeds]
    tracked_ids = {seed["id"] for seed in seeds}
    for model_id, label in sorted(base_labels.items(), key=lambda kv: kv[1].lower()):
        if model_id in tracked_ids:
            continue
        row = model_row(model_id, label, "registry")
        if row["cells"] or any(child["cells"] for child in row["children"]):
            out_rows.append(row)

    filled = sum(len(c) for c in cells.values())
    return {
        "sections": sections,
        "rows": out_rows,
        "last_run": _last_run(conn),
        # Attribution and licence live on the Sources tab only (2026-10-26);
        # `in_table` there marks the sources whose values the table shows.
        "sources": _sources_view(conn, sources, columns, used_sources),
        "counts": {
            "models": len(seeds),
            "registry_models": sum(r["group"] == "registry" for r in out_rows),
            "benchmarks": len({c["benchmark"] for c in columns.values()}),
            "setting_rows": sum(len(r["children"]) for r in out_rows),
            "filled_cells": filled,
            "columns": len(columns),
            # Sources with a saved copy: "Re-parse saved pages" needs at least one.
            "saved_pages": _saved_pages(conn),
        },
    }


def _saved_pages(conn) -> int:
    return conn.execute("SELECT count(DISTINCT source_key) FROM bench_snapshot").fetchone()[0]


#: How each method fetches, in words for the Sources tab. The libraries are the
#: ones collect/benchmarks/fetch.py and parse.py use.
FETCHERS = {
    "static": "Plain HTTP request (httpx, identifying User-Agent, robots.txt checked first)",
    "browser": "Headless browser (Playwright Chromium, same User-Agent, robots.txt checked first)",
}
READERS = {
    "html_table": "HTML table (BeautifulSoup + lxml)",
    "embedded_json": "Data block inside the page (<script> JSON)",
    "next_flight": "Data inside the page (Next.js page data)",
}


def _sources_view(
    conn,
    sources: dict[str, dict[str, Any]],
    columns: dict[str, dict[str, Any]],
    used: set[str],
):
    """Every configured source: its link, how it is fetched and read, what it fills,
    and what the last published run got from it."""
    last: dict[str, dict[str, Any]] = {}
    for run_id, finished, report in conn.execute(
        "SELECT id, finished_at, report FROM bench_run WHERE NOT dry_run AND status <> 'running' "
        "AND report IS NOT NULL ORDER BY id DESC LIMIT 30"
    ).fetchall():
        for key, entry in ((report or {}).get("sources") or {}).items():
            last.setdefault(key, {**entry, "run_id": run_id, "at": _iso(finished)})
    out = []
    for s in sources.values():
        fills, readers = [], []
        for table in s.get("tables") or []:
            readers.append(READERS.get(table["locate"]["type"], table["locate"]["type"]))
            targets = [f"{v['benchmark']}_{v['metric']}" for v in table["benchmark_map"].values()]
            if table.get("rank"):
                targets.append(f"{table['rank']['benchmark']}_rank")
            for c in targets:
                if c in columns and columns[c]["label"] not in fills:
                    fills.append(columns[c]["label"])
        if not s["enabled"]:
            state, why = "disabled", s.get("why_disabled")
        else:
            state, why = "enabled", None
        seen = last.get(s["key"])
        out.append(
            {
                "key": s["key"],
                "label": s["label"],
                "url": s.get("page_url") or s["url"],
                "state": state,
                "why": why,
                "kind": s["kind"],
                "priority": s["priority"],
                "fetcher": FETCHERS.get(s["method"], s["method"]),
                "readers": sorted(set(readers)),
                "fills": fills,
                "attribution": s.get("attribution"),
                "license": s.get("license"),
                "in_table": s["key"] in used,
                "last": None
                if seen is None
                else {
                    "run_id": seen["run_id"],
                    "at": seen["at"],
                    "status": seen.get("status"),
                    "http_status": seen.get("http_status"),
                    "rows": seen.get("rows_parsed"),
                    "values": seen.get("observations"),
                    "matched": seen.get("matched_names"),
                    "error": (seen.get("errors") or [None])[0],
                },
            }
        )
    return out


def _last_run(conn) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, status, started_at, finished_at FROM bench_run WHERE NOT dry_run "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return {"id": row[0], "status": row[1], "started_at": _iso(row[2]), "finished_at": _iso(row[3])}


def _iso(value) -> str | None:
    return value.isoformat() if value else None


# ── changelog and runs ───────────────────────────────────────────────────────


#: The Changelog's filter pills (2026-10-26). "score"/"rank": a value that moved
#: on the same source; "up"/"down": any change with a direction, including
#: another source taking the cell over. Fixed SQL only - never user text.
CHANGE_KINDS = {
    "score": "c.change_type = 'updated' AND c.metric <> 'rank'",
    "rank": "c.change_type = 'updated' AND c.metric = 'rank'",
    "up": "c.direction = 'better'",
    "down": "c.direction = 'worse'",
    "added": "c.change_type = 'added'",
    "removed": "c.change_type = 'removed'",
    "source_changed": "c.change_type = 'source_changed'",
    "variant_added": "c.change_type = 'variant_added'",
}


#: NEWS-WORTHY (Parvathi, 2026-10-26). A changelog entry is news when it says
#: something happened, not just that the board learned a value:
#:   debut  a value for a model released in the last debut_days (registry
#:          release date) - a new model showing up on a benchmark
#:   fresh  a new value the source itself dates within fresh_days of the run
#:          (an older model's new result, not a backfill)
#:   mover  a value that moved on the same source and the same release: any
#:          rank move, a score by mover_points or more, a rating by mover_rating
#: The numbers are contract/benchmarks/validation.yaml `news` (news_rules()).
#: Everything else - a source's FIRST read (its baseline: every value is new to
#: the board then), a value the board only now read, a source taking a cell
#: over, a new release resetting a board - is not news.
NEWS_KINDS = ("news", "debut", "fresh", "mover")


def news_rules() -> dict[str, float]:
    """The thresholds, from contract/benchmarks/validation.yaml `news` (rule 5)."""
    rules = _yaml("validation.yaml")["news"]
    return {
        k: float(rules[k]) for k in ("debut_days", "fresh_days", "mover_points", "mover_rating")
    }


def _day(text: Any) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10])
    except (TypeError, ValueError):
        return None


def _release_dates(conn) -> dict[str, date]:
    try:
        rows = conn.execute(
            "SELECT canonical_id, release_date FROM model_version WHERE release_date IS NOT NULL"
        ).fetchall()
    except errors.UndefinedTable:  # no registry here: no debuts. Other errors raise.
        conn.rollback()
        return {}
    return {model_id: released for model_id, released in rows}


def _baselines(conn) -> dict[str, int]:
    """Each source's first run that wrote a value: everything it added then is a
    first read, not news."""
    return dict(
        conn.execute(
            "SELECT new_source, min(run_id) FROM bench_change "
            "WHERE new_source IS NOT NULL GROUP BY new_source"
        ).fetchall()
    )


def _news(
    change: dict[str, Any],
    released: dict[str, date],
    baseline: dict[str, int],
    rules: dict[str, float],
) -> str | None:
    """Which kind of news one change is, or None."""
    on = _day(change["changed_at"])
    if change["type"] == "added" and baseline.get(change["new_source"]) == change["run_id"]:
        return None
    if change["type"] == "added" and on:
        model = change["row_id"].split(":")[0].split("@")[0]
        if model in released and 0 <= (on - released[model]).days <= rules["debut_days"]:
            return "debut"
        dated = _day(change["source_date"])
        if dated and 0 <= (on - dated).days <= rules["fresh_days"]:
            return "fresh"
        return None
    if change["type"] == "updated" and not (change["note"] or "").startswith("new release"):
        if change["metric"] == "rank":
            return "mover"
        if change["old_value"] is None or change["new_value"] is None:
            return None
        step = abs(change["new_value"] - change["old_value"])
        return (
            "mover"
            if step >= rules["mover_rating" if change["metric"] == "rating" else "mover_points"]
            else None
        )
    return None


def changelog(
    conn, *, limit: int = 300, run_id: int | None = None, kind: str | None = None
) -> dict[str, Any]:
    """The changelog, newest first, with each entry's news tag. `kind` is one of
    CHANGE_KINDS (filtered in SQL) or NEWS_KINDS (tagged, then filtered)."""
    _, columns = _columns()
    labels = {
        r[0]: r[1] for r in conn.execute("SELECT row_id, display_label FROM bench_row").fetchall()
    }
    names = {s["id"]: s["name"] for s in _seeds()}
    released = _release_dates(conn)
    baseline = _baselines(conn)
    rules = news_rules()
    conditions, params = [], []
    if run_id is not None:
        conditions.append("c.run_id = %s")
        params.append(run_id)
    if kind in CHANGE_KINDS:
        conditions.append(f"({CHANGE_KINDS[kind]})")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    # A news filter is decided per entry, so it reads the whole log and keeps
    # the newest `limit` that match; the SQL kinds are cut by the database.
    cap = "" if kind in NEWS_KINDS else "LIMIT %s"
    rows = conn.execute(
        "SELECT c.id, c.run_id, c.changed_at, c.row_id, c.benchmark_key, c.metric, c.change_type, "
        "c.old_value, c.new_value, c.old_raw, c.new_raw, c.old_source, c.new_source, "
        "c.rank_out_of_old, c.rank_out_of_new, c.source_date, "
        "c.direction, c.reason, c.actor, c.note, c.needs_review "
        f"FROM bench_change c {where} ORDER BY c.id DESC {cap}",  # noqa: S608
        (*params, limit) if cap else tuple(params),
    ).fetchall()
    entries = []
    for (
        cid,
        rid,
        at,
        row_id,
        bench,
        metric,
        change_type,
        old_value,
        new_value,
        old,
        new,
        old_src,
        new_src,
        out_of_old,
        out_of_new,
        source_date,
        direction,
        reason,
        actor,
        note,
        needs_review,
    ) in rows:
        column = columns.get(f"{bench}_{metric}") if bench else None
        entry = {
            "id": cid,
            "run_id": rid,
            "changed_at": _iso(at),
            "row_id": row_id,
            "row": labels.get(row_id) or names.get(row_id) or row_id,
            "column": column["label"] if column else None,
            "metric": metric,  # score | rank | rating: the Changelog filters on it
            "type": change_type,
            "old": old,
            "new": new,
            "old_value": old_value,
            "new_value": new_value,
            # A rank is a place among the models the board lists: "16 of 30".
            "old_out_of": out_of_old,
            "new_out_of": out_of_new,
            "source_date": source_date,
            "old_source": old_src,
            "new_source": new_src,
            "direction": direction,
            "reason": reason,
            "actor": actor,
            "note": note,
            "needs_review": needs_review,
        }
        entry["news"] = _news(entry, released, baseline, rules)
        # Read by the tagging above, not by the page (rule 9).
        for internal in ("metric", "old_value", "new_value"):
            del entry[internal]
        if kind in NEWS_KINDS and (entry["news"] is None or kind not in ("news", entry["news"])):
            continue
        entries.append(entry)
        if len(entries) >= limit:
            break
    total = conn.execute("SELECT count(*) FROM bench_change").fetchone()[0]
    counts = {
        key: conn.execute(f"SELECT count(*) FROM bench_change c WHERE {sql}").fetchone()[0]  # noqa: S608
        for key, sql in CHANGE_KINDS.items()
    }
    counts.update(_news_counts(conn, released, baseline, rules))
    return {
        "entries": entries,
        "total": total,
        "counts": counts,
        "kind": kind or "all",
        "news_rules": rules,
        # Runs that were some source's first read (all their values new to the
        # board): the page labels them "first import" (PR #573 review).
        "baseline_runs": sorted(set(baseline.values())),
    }


def _news_counts(
    conn, released: dict[str, date], baseline: dict[str, int], rules: dict[str, float]
) -> dict[str, int]:
    found = {k: 0 for k in NEWS_KINDS}
    for (
        run_id,
        source,
        row_id,
        metric,
        change_type,
        old_value,
        new_value,
        at,
        source_date,
        note,
    ) in conn.execute(
        "SELECT run_id, new_source, row_id, metric, change_type, old_value, new_value, "
        "changed_at, source_date, note FROM bench_change "
        "WHERE change_type IN ('added', 'updated')"
    ).fetchall():
        tag = _news(
            {
                "run_id": run_id,
                "new_source": source,
                "row_id": row_id,
                "metric": metric,
                "type": change_type,
                "old_value": old_value,
                "new_value": new_value,
                "changed_at": at,
                "source_date": source_date,
                "note": note,
            },
            released,
            baseline,
            rules,
        )
        if tag:
            found[tag] += 1
            found["news"] += 1
    return found


def runs(conn, *, limit: int = 30) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT id, request_id, trigger, scope, dry_run, status, started_at, finished_at, report "
        "FROM bench_run ORDER BY id DESC LIMIT %s",
        (limit,),
    ).fetchall()
    return {"runs": [_run_summary(r) for r in rows]}


def _run_summary(r) -> dict[str, Any]:
    rid, request_id, trigger, scope, dry_run, status, started, finished, report = r
    report = report or {}
    return {
        "id": rid,
        "request_id": request_id,
        "trigger": trigger,
        "scope": scope,
        "dry_run": dry_run,
        "status": status,
        "started_at": _iso(started),
        "finished_at": _iso(finished),
        "totals": report.get("totals"),
        "sources": {
            k: {"status": v.get("status"), "errors": v.get("errors")}
            for k, v in (report.get("sources") or {}).items()
        },
        "error": report.get("error"),
    }


def _running(conn) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, request_id, started_at FROM bench_run WHERE status = 'running' "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return {"id": row[0], "request_id": row[1], "started_at": _iso(row[2])} if row else None


def _log_dir() -> Path:
    return REPO_ROOT / _yaml("module_settings.yaml")["log_dir"]


def run_detail(conn, *, run_id: int | None = None, request_id: str | None = None) -> dict[str, Any]:
    """One run and its terminal output - live from the log file while it runs."""
    if run_id is not None:
        where, param = "id = %s", run_id
    else:
        where, param = "request_id = %s", request_id
    row = conn.execute(
        "SELECT id, request_id, trigger, scope, dry_run, status, started_at, finished_at, "
        "report, log_text "
        f"FROM bench_run WHERE {where} ORDER BY id DESC LIMIT 1",
        (param,),
    ).fetchone()
    if row is None:
        return {"found": False, "done": False, "log": "", "run": None}
    summary = _run_summary(row[:9])
    log_text = row[9] or ""
    # The same name collect/benchmarks/store.py log_file_name() gives the file.
    path = _log_dir() / f"run_{row[0]}_{row[6].astimezone(UTC):%Y%m%dT%H%M%S}.log"
    if row[5] == "running" and path.exists():
        data = path.read_bytes()[-LOG_TAIL_BYTES:]
        log_text = data.decode("utf-8", "replace")
    return {"found": True, "done": row[5] != "running", "run": summary, "log": log_text}


def unmatched(conn, *, limit: int = 300) -> dict[str, Any]:
    """Names of REGISTRY models the sources' latest reads listed and no row took.

    Only models in the registry are considered (Parvathi, 2026-10-26): a name
    whose model is not in the registry is not listed. So a group here is either
    a name very close to a registry name (similar_to: same numbers, only filler
    words like "Claude" or "Instruct" differ) for a person to confirm, or a known
    model whose setting or date could not be read - grouped by the name without
    its setting or date, with every source that listed it.
    """
    groups: dict[str, dict[str, Any]] = {}
    for source, raw, reason, base_name, base_key, similar_to, seen in conn.execute(
        "SELECT source_key, raw_name, reason, base_name, base_key, similar_to, seen_count "
        "FROM bench_unmatched WHERE reason <> 'unmatched'"
    ).fetchall():
        key = base_key or raw.lower()
        g = groups.setdefault(
            key,
            {
                "key": key,
                "name": base_name or raw,
                "raw_names": set(),
                "sources": set(),
                "reasons": set(),
                "similar_to": set(),
                "seen": 0,
            },
        )
        g["similar_to"].update(similar_to or ())
        g["raw_names"].add(raw)
        g["sources"].add(source)
        g["reasons"].add(reason)
        g["seen"] += seen
    decided = {
        key: {
            "key": key,
            "name": name,
            "action": action,
            "target": target,
            "actor": actor,
            "at": _iso(at),
        }
        for key, name, action, target, actor, at in conn.execute(
            "SELECT name_key, name, action, target_model_id, actor, created_at "
            "FROM bench_name_decision ORDER BY created_at DESC"
        ).fetchall()
    }
    targets = decision_targets(conn)
    names = {t["id"]: t["name"] for t in targets}
    ordered = sorted(
        (g for g in groups.values() if g["key"] not in decided),
        key=lambda g: (-len(g["sources"]), -g["seen"], g["name"].lower()),
    )
    return {
        "total": len(ordered),
        "groups": [
            {
                "key": g["key"],
                "name": g["name"],
                "raw_names": sorted(g["raw_names"])[:8],
                "sources": sorted(g["sources"]),
                "reasons": sorted(g["reasons"]),
                "similar_to": [{"id": i, "name": names.get(i, i)} for i in sorted(g["similar_to"])],
                # Only a name no model took can be decided; an unknown setting
                # word belongs to a known model and is a vocabulary question.
                "decidable": "similar_to_registry" in g["reasons"],
                "seen": g["seen"],
            }
            for g in ordered[:limit]
        ],
        "decisions": list(decided.values()),
        "targets": targets,
    }


def decision_targets(conn) -> list[dict[str, str]]:
    """The models "Same model as ..." may name: tracked first, then the registry."""
    out = [{"id": s["id"], "name": s["name"], "group": "tracked"} for s in _seeds()]
    tracked = {s["id"] for s in out}
    try:
        rows = conn.execute(
            "SELECT DISTINCT canonical_id, display_name FROM model_version ORDER BY 1"
        ).fetchall()
    except errors.UndefinedTable:  # no registry here: tracked models only. Others raise.
        conn.rollback()
        rows = []
    seen: set[str] = set()
    for model_id, name in rows:
        if model_id and model_id not in tracked and model_id not in seen:
            seen.add(model_id)
            out.append(
                {"id": model_id, "name": (name or model_id).split(": ", 1)[-1], "group": "registry"}
            )
    return out


#: "new_row" is no longer offered: only registry models get rows (2026-10-26).
ACTIONS = ("alias", "ignore")


class DecisionRefused(ValueError):
    pass


def refuse_unless_local() -> None:
    """Name decisions write, so like runs they are local-only while the page is
    being built: the configured database is the shared one by default
    (PR #573 review)."""
    if not is_local(database_url()):
        raise DecisionRefused(
            "name decisions are local-only while the Benchmarks page is being built: "
            "the benchmarks database is not on this machine"
        )


def decide(
    conn, *, key: str, name: str, action: str, target: str | None, actor: str = "admin"
) -> dict[str, Any]:
    """Record a person's decision about one unmatched name (replaces an earlier one)."""
    key, name = (key or "").strip(), (name or "").strip()
    if not key or not name:
        raise DecisionRefused("a name is required")
    if action not in ACTIONS:
        raise DecisionRefused(f"action must be one of {list(ACTIONS)}")
    if action == "alias":
        if not target or target not in {t["id"] for t in decision_targets(conn)}:
            raise DecisionRefused("choose a tracked or registry model this name is the same as")
    else:
        target = None
    conn.execute(
        "INSERT INTO bench_name_decision (name_key, name, action, target_model_id, actor) "
        "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (name_key) DO UPDATE SET "
        "name = EXCLUDED.name, action = EXCLUDED.action, "
        "target_model_id = EXCLUDED.target_model_id, actor = EXCLUDED.actor, created_at = now()",
        (key, name, action, target, actor),
    )
    return {
        "key": key,
        "action": action,
        "target": target,
        "applies": "on the next run, or Re-parse saved pages",
    }


def undo_decision(conn, *, key: str) -> dict[str, Any]:
    gone = conn.execute(
        "DELETE FROM bench_name_decision WHERE name_key = %s RETURNING name_key", (key,)
    ).fetchone()
    return {"key": key, "undone": gone is not None}


def review_items(conn, *, limit: int = 200) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT id, run_id, check_code, severity, source_key, row_id, benchmark_key, metric, "
        "message, "
        "status, created_at FROM bench_review_item WHERE status = 'open' ORDER BY id DESC LIMIT %s",
        (limit,),
    ).fetchall()
    return {
        "items": [
            {
                "id": i,
                "run_id": r,
                "check": c,
                "severity": sev,
                "source": s,
                "row": row,
                "column": f"{b}_{m}" if b else None,
                "message": msg,
                "status": st,
                "created_at": _iso(at),
            }
            for i, r, c, sev, s, row, b, m, msg, st, at in rows
        ]
    }


# ── starting a run ───────────────────────────────────────────────────────────


def start_run(conn, *, dry_run: bool, use_snapshot: bool) -> dict[str, Any]:
    """Spawn the run in the background and return the id the page polls by."""
    dsn = database_url()
    if not is_local(dsn):
        raise RunRefused(
            "runs are local-only while the Benchmarks page is being built: "
            "the benchmarks database is not on this machine"
        )
    running = _running(conn)
    if running is not None:
        raise RunRefused(f"run #{running['id']} is still running (one run at a time)")
    if use_snapshot and not _saved_pages(conn):
        raise RunRefused(
            "no page has been saved yet, so there is nothing to re-parse - "
            "make a real run first (Run now)"
        )
    request_id = uuid.uuid4().hex[:12]
    command = [
        sys.executable,
        "-m",
        "collect.cli",
        "benchmarks",
        "run",
        "--trigger",
        "page_button",
        "--request-id",
        request_id,
        "--actor",
        "admin",
    ]
    if dry_run:
        command.append("--dry-run")
    if use_snapshot:
        command.append("--use-snapshot")
    env = os.environ.copy()
    env["DATABASE_URL"] = dsn
    env.setdefault("PYTHONIOENCODING", "utf-8")
    # Inherited streams, detached, nothing read back - the run prints to the
    # backend's console and to its own log file, as /fetch/start does.
    subprocess.Popen(command, cwd=str(REPO_ROOT), env=env)
    return {"request_id": request_id, "dry_run": dry_run, "use_snapshot": use_snapshot}
